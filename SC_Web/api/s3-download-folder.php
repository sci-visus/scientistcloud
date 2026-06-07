<?php
/**
 * Zip and download an S3 "folder" (prefix) for current inspector session.
 */

declare(strict_types=1);

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/s3_inspector.php';

if (!is_file(__DIR__ . '/../vendor/autoload.php')) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Composer dependencies missing.';
    exit;
}
require_once __DIR__ . '/../vendor/autoload.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

if (defined('S3_REQUIRE_PORTAL_AUTH') && S3_REQUIRE_PORTAL_AUTH) {
    $user = getCurrentUser();
    if (!$user) {
        http_response_code(403);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'Forbidden';
        exit;
    }
}

$session = $_SESSION['portal_s3_inspector'] ?? [];
if (!s3_inspector_connected($session)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Open Inspect S3 and connect first.';
    exit;
}

$rel = s3_inspector_sanitize_rel((string) ($_GET['rel'] ?? ''));
$rootPrefix = s3_inspector_normalize_root_prefix((string) ($session['root_prefix'] ?? ''));
$targetPrefix = $rootPrefix . $rel;

$maxFiles = defined('S3_FOLDER_DOWNLOAD_MAX_FILES') ? (int) S3_FOLDER_DOWNLOAD_MAX_FILES : 2000;
if ($maxFiles < 1) {
    $maxFiles = 1;
}
$maxBytes = defined('S3_FOLDER_DOWNLOAD_MAX_BYTES') ? (int) S3_FOLDER_DOWNLOAD_MAX_BYTES : (20 * 1024 * 1024 * 1024);
if ($maxBytes < 1) {
    $maxBytes = 1;
}

$tmpDir = sys_get_temp_dir() . '/s3zip_' . bin2hex(random_bytes(8));
$zipPath = $tmpDir . '/bundle.zip';
$tmpFiles = [];

try {
    @set_time_limit(0);
    @ini_set('max_execution_time', '0');
    @ini_set('zlib.output_compression', '0');
    while (ob_get_level() > 0) {
        @ob_end_clean();
    }

    if (!mkdir($tmpDir, 0700, true) && !is_dir($tmpDir)) {
        throw new RuntimeException('Could not create temp directory.');
    }

    $zip = new ZipArchive();
    if ($zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
        throw new RuntimeException('Could not initialize zip archive.');
    }

    $client = s3_inspector_create_client($session, [
        'timeout' => 0,
        'read_timeout' => 0,
    ]);

    $fileCount = 0;
    $totalBytes = 0;
    $continuation = null;

    do {
        $params = [
            'Bucket' => $session['bucket'],
            'Prefix' => $targetPrefix,
            'MaxKeys' => 1000,
        ];
        if ($continuation) {
            $params['ContinuationToken'] = $continuation;
        }
        $result = $client->listObjectsV2($params);

        foreach (($result['Contents'] ?? []) as $obj) {
            $key = (string) ($obj['Key'] ?? '');
            if ($key === '' || $key === $targetPrefix) {
                continue;
            }
            if (str_ends_with($key, '/') && ((int) ($obj['Size'] ?? 0) === 0)) {
                continue;
            }
            if (!s3_inspector_key_allowed($key, $rootPrefix)) {
                continue;
            }

            $relativeName = ltrim(substr($key, strlen($targetPrefix)), '/');
            if ($relativeName === '') {
                continue;
            }

            $size = (int) ($obj['Size'] ?? 0);
            $fileCount++;
            $totalBytes += $size;
            if ($fileCount > $maxFiles) {
                throw new RuntimeException('Folder has too many files for server-side zip (limit: ' . $maxFiles . ').');
            }
            if ($totalBytes > $maxBytes) {
                throw new RuntimeException('Folder is too large for server-side zip (limit: ' . $maxBytes . ' bytes).');
            }

            $localPath = $tmpDir . '/file_' . $fileCount;
            s3_inspector_download_object_to_file($client, $session['bucket'], $key, $localPath);
            $tmpFiles[] = $localPath;
            $zip->addFile($localPath, $relativeName);
        }

        $continuation = $result['NextContinuationToken'] ?? null;
    } while ($continuation);

    if ($fileCount === 0) {
        $zip->close();
        http_response_code(404);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'No files found in selected folder.';
        exit;
    }

    $zip->close();

    $folderName = trim(basename(rtrim($rel !== '' ? $rel : ($rootPrefix !== '' ? $rootPrefix : 'bucket'), '/')));
    if ($folderName === '') {
        $folderName = 'bucket';
    }
    $zipName = preg_replace('/[^A-Za-z0-9._-]+/', '_', $folderName) . '.zip';

    header('Content-Type: application/zip');
    header('Content-Disposition: attachment; filename="' . $zipName . '"');
    header('Content-Length: ' . (string) filesize($zipPath));
    header('Cache-Control: no-store');
    header('X-Accel-Buffering: no');
    readfile($zipPath);
} catch (Throwable $e) {
    if (!headers_sent()) {
        http_response_code(400);
        header('Content-Type: text/plain; charset=UTF-8');
    }
    echo 'Folder download failed: ' . $e->getMessage();
} finally {
    foreach ($tmpFiles as $f) {
        if (is_file($f)) {
            @unlink($f);
        }
    }
    if (is_file($zipPath)) {
        @unlink($zipPath);
    }
    if (is_dir($tmpDir)) {
        @rmdir($tmpDir);
    }
}

