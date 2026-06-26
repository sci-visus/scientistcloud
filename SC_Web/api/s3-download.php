<?php
/**
 * Stream a single S3 object for the S3 inspector session.
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

$inspectorSessionKey = defined('S3_INSPECTOR_SESSION_OVERRIDE')
    ? (string) S3_INSPECTOR_SESSION_OVERRIDE
    : 'portal_s3_inspector';
$skipInspectorAuth = defined('S3_INSPECTOR_SKIP_PORTAL_AUTH') && S3_INSPECTOR_SKIP_PORTAL_AUTH;

if (!$skipInspectorAuth && defined('S3_REQUIRE_PORTAL_AUTH') && S3_REQUIRE_PORTAL_AUTH) {
    $user = getCurrentUser();
    if (!$user) {
        http_response_code(403);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'Forbidden';
        exit;
    }
}

$session = $_SESSION[$inspectorSessionKey] ?? [];
if (!s3_inspector_connected($session)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Open Inspect S3 and connect first.';
    exit;
}

$key = isset($_GET['k']) ? rawurldecode((string) $_GET['k']) : '';
$key = ltrim(str_replace('\\', '/', $key), '/');
if ($key === '') {
    http_response_code(400);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Missing object key.';
    exit;
}

$mode = isset($_GET['mode']) ? (string) $_GET['mode'] : '';
$shareMode = $mode === 'share_link';
$previewMode = $mode === 'preview_text';
$maxShareSeconds = defined('S3_SHARE_LINK_MAX_SECONDS') ? (int) S3_SHARE_LINK_MAX_SECONDS : 604800;
if ($maxShareSeconds < 60) {
    $maxShareSeconds = 60;
}
$expiresSeconds = isset($_GET['expires']) ? (int) $_GET['expires'] : 1800;
if ($expiresSeconds < 60) {
    $expiresSeconds = 60;
} elseif ($expiresSeconds > $maxShareSeconds) {
    $expiresSeconds = $maxShareSeconds;
}

$rootPrefix = (string) ($session['root_prefix'] ?? '');
if (!s3_inspector_key_allowed($key, $rootPrefix)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Key not under configured prefix.';
    exit;
}

try {
    // Download can take a long time for GB-scale files.
    @set_time_limit(0);
    @ini_set('max_execution_time', '0');
    s3_inspector_prepare_download_response();

    // Override default short timeout used by listing calls.
    $client = s3_inspector_create_client($session, [
        'timeout' => 0,
        'read_timeout' => 0,
    ]);
    $params = [
        'Bucket' => $session['bucket'],
        'Key' => $key,
    ];
    if ($previewMode) {
        // Keep previews fast and bounded. Some S3-compatible gateways return 206
        // for ranged reads in a way the SDK reports as an error, so avoid Range
        // for small text objects like .idx descriptors.
        $isIdxPreview = str_ends_with(strtolower(parse_url($key, PHP_URL_PATH) ?: $key), '.idx');
        try {
            $head = $client->headObject([
                'Bucket' => $session['bucket'],
                'Key' => $key,
            ]);
            $contentLength = isset($head['ContentLength']) ? (int) $head['ContentLength'] : 0;
            if ($contentLength > 262144) {
                $params['Range'] = 'bytes=0-262143'; // 256 KB
            }
        } catch (Throwable $e) {
            if (!$isIdxPreview) {
                $params['Range'] = 'bytes=0-262143'; // 256 KB fallback
            }
        }
    }
    $rangeHeader = isset($_SERVER['HTTP_RANGE']) ? trim((string) $_SERVER['HTTP_RANGE']) : '';
    if ($rangeHeader !== '' && preg_match('/^bytes=\d*-\d*$/', $rangeHeader)) {
        $params['Range'] = $rangeHeader;
    }

    $usePresignedRedirect = filter_var(
        getenv('S3_DOWNLOAD_PRESIGNED_REDIRECT') ?: 'false',
        FILTER_VALIDATE_BOOLEAN
    );

    // Optional direct-to-S3 redirect for very large files when the gateway supports presigned URLs.
    if (!$previewMode && !$shareMode && $usePresignedRedirect) {
        $cmd = $client->getCommand('GetObject', $params);
        $signed = $client->createPresignedRequest($cmd, '+' . $expiresSeconds . ' seconds');
        $signedUrl = (string) $signed->getUri();
        if ($signedUrl !== '') {
            header('Cache-Control: no-store');
            header('Location: ' . $signedUrl, true, 302);
            exit;
        }
    }

    if ($shareMode) {
        $cmd = $client->getCommand('GetObject', $params);
        $signed = $client->createPresignedRequest($cmd, '+' . $expiresSeconds . ' seconds');
        $signedUrl = (string) $signed->getUri();
        if ($signedUrl === '') {
            http_response_code(500);
            header('Content-Type: application/json; charset=UTF-8');
            echo json_encode(['ok' => false, 'error' => 'Could not create share link.']);
            exit;
        }
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode([
            'ok' => true,
            'url' => $signedUrl,
            'expires_in' => $expiresSeconds,
            'max_expires_in' => $maxShareSeconds,
        ], JSON_UNESCAPED_SLASHES);
        exit;
    }

    if ($previewMode) {
        // Bypass SDK response validation for preview reads. Some S3-compatible
        // gateways return "206 OK" for valid object reads, which the SDK reports
        // as an AwsException even though the body is usable.
        if (function_exists('curl_init')) {
            $signedParams = [
                'Bucket' => $session['bucket'],
                'Key' => $key,
            ];
            $cmd = $client->getCommand('GetObject', $signedParams);
            $signed = $client->createPresignedRequest($cmd, '+60 seconds');
            $signedUrl = (string) $signed->getUri();

            $chPreview = curl_init($signedUrl);
            if ($chPreview) {
                curl_setopt_array($chPreview, [
                    CURLOPT_RETURNTRANSFER => true,
                    CURLOPT_FOLLOWLOCATION => true,
                    CURLOPT_CONNECTTIMEOUT => 8,
                    CURLOPT_TIMEOUT => 25,
                    CURLOPT_USERAGENT => 'ScientistCloud-Portal/s3-preview',
                ]);
                if (isset($params['Range'])) {
                    curl_setopt($chPreview, CURLOPT_RANGE, '0-262143');
                }
                $content = curl_exec($chPreview);
                $httpCode = (int) curl_getinfo($chPreview, CURLINFO_HTTP_CODE);
                $curlError = curl_error($chPreview);
                curl_close($chPreview);

                if (is_string($content) && $content !== '' && in_array($httpCode, [200, 206], true)) {
                    $truncated = strlen($content) >= 262144 || $httpCode === 206;
                    header('Content-Type: application/json; charset=UTF-8');
                    echo json_encode([
                        'ok' => true,
                        'key' => $key,
                        'content' => $content,
                        'truncated' => $truncated,
                        'bytes' => strlen($content),
                    ], JSON_UNESCAPED_SLASHES);
                    exit;
                }

                http_response_code(400);
                header('Content-Type: application/json; charset=UTF-8');
                echo json_encode([
                    'ok' => false,
                    'error' => $curlError !== '' ? $curlError : 'Preview request failed with HTTP ' . $httpCode,
                ], JSON_UNESCAPED_SLASHES);
                exit;
            }
        }

        $result = $client->getObject($params);
        $body = $result['Body'];
        $content = is_resource($body) ? stream_get_contents($body) : (string) $body;
        $truncated = strlen($content) >= 262144;
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode([
            'ok' => true,
            'key' => $key,
            'content' => $content,
            'truncated' => $truncated,
            'bytes' => strlen($content),
        ], JSON_UNESCAPED_SLASHES);
        exit;
    }

    try {
        s3_inspector_stream_object_to_browser($session, $key, $rangeHeader !== '' ? $rangeHeader : null);
        exit;
    } catch (RuntimeException $e) {
        $status = $e->getCode() >= 400 ? (int) $e->getCode() : 500;
        http_response_code($status);
        header('Content-Type: text/plain; charset=UTF-8');
        echo $e->getMessage();
        exit;
    }
} catch (Aws\Exception\AwsException $e) {
    if ($previewMode) {
        http_response_code(400);
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode([
            'ok' => false,
            'error' => $e->getAwsErrorMessage() ?: $e->getMessage(),
        ], JSON_UNESCAPED_SLASHES);
        exit;
    }
    if ($shareMode) {
        http_response_code(400);
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode([
            'ok' => false,
            'error' => $e->getAwsErrorMessage() ?: $e->getMessage(),
        ], JSON_UNESCAPED_SLASHES);
        exit;
    }
    http_response_code(404);
    header('Content-Type: text/plain; charset=UTF-8');
    echo $e->getAwsErrorMessage() ?: $e->getMessage();
} catch (Throwable $e) {
    if ($previewMode) {
        http_response_code(500);
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode([
            'ok' => false,
            'error' => 'Preview failed.',
        ], JSON_UNESCAPED_SLASHES);
        exit;
    }
    if ($shareMode) {
        http_response_code(500);
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode([
            'ok' => false,
            'error' => 'Could not create share link.',
        ], JSON_UNESCAPED_SLASHES);
        exit;
    }
    http_response_code(500);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Download failed.';
}
