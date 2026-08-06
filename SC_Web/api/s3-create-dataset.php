<?php
/**
 * Create a remote S3 dataset entry from Inspect S3 session context.
 */
declare(strict_types=1);

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/s3_inspector.php';

if (!isAuthenticated()) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Authentication required']);
    exit;
}

$user = getCurrentUser();
if (!$user || empty($user['email'])) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'User not authenticated']);
    exit;
}

$session = $_SESSION['portal_s3_inspector'] ?? [];
if (!s3_inspector_connected($session)) {
    http_response_code(403);
    echo json_encode(['success' => false, 'error' => 'S3 inspector is not connected']);
    exit;
}

$raw = file_get_contents('php://input');
$input = json_decode($raw ?: '{}', true);
if (!is_array($input)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid JSON body']);
    exit;
}

$key = trim((string)($input['key'] ?? ''));
$datasetName = trim((string)($input['dataset_name'] ?? ''));
$sensor = trim((string)($input['sensor'] ?? 'IDX'));
$tags = trim((string)($input['tags'] ?? ''));
$folder = trim((string)($input['folder'] ?? ''));
$teamUuid = trim((string)($input['team_uuid'] ?? ''));
$dimensions = trim((string)($input['dimensions'] ?? ''));
$preferredDashboard = trim((string)($input['preferred_dashboard'] ?? ''));
$isPublic = !empty($input['is_public']);
$isDownloadable = trim((string)($input['is_downloadable'] ?? 'only owner'));
// Download (materialize to upload/) and convert are independent.
// Legacy: if only convert is sent, convert still implies download (handled by upload API when download omitted).
$convert = array_key_exists('convert', $input) ? !empty($input['convert']) : false;
$download = array_key_exists('download', $input) ? !empty($input['download']) : null;

if ($key === '' || $datasetName === '') {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Missing required fields: key, dataset_name']);
    exit;
}

$rootPrefix = (string)($session['root_prefix'] ?? '');
if (!s3_inspector_key_allowed($key, $rootPrefix)) {
    http_response_code(403);
    echo json_encode(['success' => false, 'error' => 'Key not under configured prefix']);
    exit;
}

$bucket = trim((string)($session['bucket'] ?? ''));
$endpoint = trim((string)($session['endpoint'] ?? ''));
$region = trim((string)($session['region'] ?? 'us-east-1')) ?: 'us-east-1';
$pathStyle = !empty($session['path_style']);
$access = trim((string)($session['access_key'] ?? ''));
$secret = trim((string)($session['secret_key'] ?? ''));

if ($bucket === '' || $endpoint === '' || $access === '' || $secret === '') {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Incomplete S3 session credentials']);
    exit;
}

$originalLink = 's3://' . $bucket . '/' . ltrim($key, '/');
$requestData = [
    'source_type' => 's3',
    'source_config' => [
        'endpoint_url' => $endpoint,
        'bucket_name' => $bucket,
        'object_key' => $key,
        'access_key_id' => $access,
        'secret_access_key' => $secret,
        'region_name' => $region,
        'path_style' => $pathStyle,
        'original_link' => $originalLink,
    ],
    'user_email' => $user['email'],
    'dataset_name' => $datasetName,
    'sensor' => $sensor,
    'convert' => $convert,
    'is_public' => $isPublic,
    'folder' => $folder !== '' ? $folder : null,
    'team_uuid' => $teamUuid !== '' ? $teamUuid : null,
    'is_downloadable' => $isDownloadable,
];

if ($download !== null) {
    $requestData['download'] = $download;
}
if ($tags !== '') {
    // UploadRequest accepts comma-separated tags; keep this as a string for API compatibility.
    $requestData['tags'] = $tags;
}
if ($dimensions !== '') {
    $requestData['dimensions'] = $dimensions;
}
if ($preferredDashboard !== '') {
    $requestData['preferred_dashboard'] = $preferredDashboard;
}

$uploadApiUrl = getenv('SCLIB_UPLOAD_URL') ?: getenv('SCLIB_API_URL') ?: getenv('SCLIB_DATASET_URL') ?: getenv('EXISTING_API_URL');
if (!$uploadApiUrl) {
    if (file_exists('/.dockerenv') || getenv('DOCKER_CONTAINER')) {
        $uploadApiUrl = 'http://sclib_fastapi:5001';
    } else {
        $uploadApiUrl = 'http://localhost:5001';
    }
}
$initiateEndpoint = rtrim($uploadApiUrl, '/') . '/api/upload/initiate';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $initiateEndpoint);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($requestData));
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json', 'Accept: application/json']);
curl_setopt($ch, CURLOPT_TIMEOUT, 30);
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError = curl_error($ch);
curl_close($ch);

if ($curlError) {
    http_response_code(502);
    echo json_encode(['success' => false, 'error' => 'Failed to connect to upload service', 'detail' => $curlError]);
    exit;
}

http_response_code($httpCode > 0 ? $httpCode : 500);
if (!$response) {
    echo json_encode(['success' => false, 'error' => 'Empty response from upload service']);
    exit;
}
echo $response;

