<?php
/**
 * Lightweight S3 credential/endpoint check for the upload UI (S3 tab).
 * Requires portal session auth; does not persist credentials.
 */

declare(strict_types=1);

if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

ini_set('display_errors', '0');
ini_set('display_startup_errors', '0');
error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED);

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json; charset=UTF-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/s3_inspector.php';

if (!is_file(__DIR__ . '/../vendor/autoload.php')) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Composer dependencies missing (aws/aws-sdk-php).']);
    exit;
}
require_once __DIR__ . '/../vendor/autoload.php';

try {
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['ok' => false, 'error' => 'Authentication required']);
        exit;
    }

    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        ob_end_clean();
        http_response_code(405);
        echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
        exit;
    }

    $raw = file_get_contents('php://input');
    $input = json_decode((string) $raw, true);
    if (!is_array($input)) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => 'Invalid JSON body']);
        exit;
    }

    $endpoint = trim((string) ($input['endpoint_url'] ?? ''));
    $bucket = trim((string) ($input['bucket_name'] ?? ''));
    $prefix = s3_inspector_normalize_root_prefix((string) ($input['prefix'] ?? ''));
    $access = trim((string) ($input['access_key'] ?? ''));
    $secret = trim((string) ($input['secret_key'] ?? ''));
    $region = trim((string) ($input['region'] ?? 'us-east-1')) ?: 'us-east-1';
    $pathStyle = !empty($input['path_style']);

    if ($endpoint === '' || $bucket === '' || $access === '' || $secret === '') {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => 'endpoint_url, bucket_name, access_key, and secret_key are required']);
        exit;
    }

    $probe = [
        'endpoint' => $endpoint,
        'bucket' => $bucket,
        'root_prefix' => $prefix,
        'rel' => '',
        'access_key' => $access,
        'secret_key' => $secret,
        'region' => $region,
        'path_style' => $pathStyle,
    ];

    $list = s3_inspector_list_page($probe, null);

    ob_end_clean();
    if ($list['error'] !== null) {
        http_response_code(400);
        echo json_encode([
            'ok' => false,
            'error' => $list['error'],
        ], JSON_UNESCAPED_SLASHES);
        exit;
    }

    echo json_encode([
        'ok' => true,
        'message' => 'Connection OK — can list objects under the given prefix.',
        'folders' => count($list['folders']),
        'files' => count($list['files']),
        'has_more' => !empty($list['next_token']),
    ], JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Test failed']);
}
