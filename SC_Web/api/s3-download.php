<?php
/**
 * Stream a single S3 object for the authenticated S3 inspector session.
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

$user = getCurrentUser();
if (!$user) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Forbidden';
    exit;
}

$session = $_SESSION['portal_s3_inspector'] ?? [];
if (!s3_inspector_connected($session)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Open Inspect S3 and connect first.';
    exit;
}

$key = isset($_GET['k']) ? (string) $_GET['k'] : '';
if ($key === '') {
    http_response_code(400);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Missing object key.';
    exit;
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
    @ini_set('zlib.output_compression', '0');
    while (ob_get_level() > 0) {
        @ob_end_clean();
    }

    // Override default short timeout used by listing calls.
    $client = s3_inspector_create_client($session, [
        'timeout' => 0,
        'read_timeout' => 0,
    ]);
    $params = [
        'Bucket' => $session['bucket'],
        'Key' => $key,
    ];
    $rangeHeader = isset($_SERVER['HTTP_RANGE']) ? trim((string) $_SERVER['HTTP_RANGE']) : '';
    if ($rangeHeader !== '' && preg_match('/^bytes=\d*-\d*$/', $rangeHeader)) {
        $params['Range'] = $rangeHeader;
    }
    $result = $client->getObject($params);

    $filename = basename($key);
    $contentType = $result['ContentType'] ?? 'application/octet-stream';
    header('Content-Type: ' . $contentType);
    header('Content-Disposition: attachment; filename="' . str_replace('"', '', $filename) . '"');
    header('Accept-Ranges: bytes');
    if (isset($result['ContentRange'])) {
        http_response_code(206);
        header('Content-Range: ' . $result['ContentRange']);
    }
    if (isset($result['ContentLength'])) {
        header('Content-Length: ' . (int) $result['ContentLength']);
    }
    if (isset($result['ETag'])) {
        header('ETag: ' . $result['ETag']);
    }

    $body = $result['Body'];
    if (is_resource($body)) {
        fpassthru($body);
    } else {
        while (!$body->eof()) {
            echo $body->read(65536);
            @flush();
        }
    }
} catch (Aws\Exception\AwsException $e) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=UTF-8');
    echo $e->getAwsErrorMessage() ?: $e->getMessage();
} catch (Throwable $e) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Download failed.';
}
