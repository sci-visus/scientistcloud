<?php
/**
 * Set a short-lived dashboard cookie for the public portal.
 * Verifies the dataset is public, then nginx auth_request on /dashboard/* can succeed
 * without sending the iframe to Auth0 (which refuses to be framed).
 */

require_once(__DIR__ . '/../includes/session_cookie_params.php');

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

header('Content-Type: application/json');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

$datasetId = trim((string) ($_GET['dataset_id'] ?? $_GET['dataset_uuid'] ?? ''));
if ($datasetId === '') {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'dataset_id is required']);
    exit;
}

try {
    $sclib = getSCLibClient();
    $encoded = rawurlencode($datasetId);
    $response = $sclib->makeRequest("/api/v1/datasets/public/{$encoded}", 'GET');
    $ok = is_array($response) && !empty($response['success']) && !empty($response['dataset']);
    if (!$ok) {
        $msg = is_array($response) ? ($response['error'] ?? $response['message'] ?? 'Dataset is not public') : 'Dataset is not public';
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => $msg]);
        exit;
    }

    $uuid = (string) ($response['dataset']['uuid'] ?? $datasetId);

    if (!setPublicDashboardAuthCookie($uuid !== '' ? $uuid : $datasetId)) {
        http_response_code(500);
        echo json_encode(['success' => false, 'error' => 'Failed to set public dashboard cookie']);
        exit;
    }

    echo json_encode(['success' => true]);
} catch (Throwable $e) {
    error_log('public-dashboard-auth-token: ' . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Failed to authorize public dashboard']);
}
