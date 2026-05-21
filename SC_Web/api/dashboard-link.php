<?php
/**
 * Dashboard share link API — returns a copy/open URL with full remote credentials when
 * the dataset stores them (never redacted). For display in the UI, dataset-details still redacts.
 */

if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');
require_once(__DIR__ . '/../includes/dashboard_share_link.php');

try {
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    $datasetId = $_GET['dataset_id'] ?? null;
    if (!$datasetId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset ID is required']);
        exit;
    }

    if (!canAccessDataset($datasetId)) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Access denied']);
        exit;
    }

    $dataset = getDatasetForDashboardLink($datasetId);
    if (!$dataset) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    $dashboardType = trim((string)($_GET['dashboard'] ?? ''));
    if ($dashboardType === '') {
        $dashboardType = trim((string)($dataset['preferred_dashboard'] ?? ''));
    }
    if ($dashboardType === '') {
        $dashboardType = sc_dataset_is_ornl_chess_strain($dataset) ? 'ORNL_CHESS_strain' : 'OpenVisusSlice';
    }

    $origin = null;
    if (!empty($_GET['origin'])) {
        $origin = rtrim((string)$_GET['origin'], '/');
    }

    $url = sc_build_dashboard_share_url($dataset, $dashboardType, $origin);
    $dashboardDestination = sc_build_dashboard_destination_url($dataset, $dashboardType, $origin, false);

    $containsSecrets = (bool) preg_match(
        '/([?&](access_key|secret_key|secret_access_key|access_key_id)=)/i',
        $dashboardDestination
    );
    $hasPlaceholderCreds = (bool) preg_match(
        '/([?&](access_key|secret_key|secret_access_key|access_key_id)=\.\.\.)/i',
        $dashboardDestination
    );

    if ($hasPlaceholderCreds) {
        ob_end_clean();
        http_response_code(409);
        echo json_encode([
            'success' => false,
            'error' => 'Stored data link has redacted credentials and no S3 keys were found on the dataset. '
                . 'Re-register the dataset with S3 access/secret keys, or update the data link with a full gateway URL.',
        ]);
        exit;
    }

    ob_end_clean();
    echo json_encode([
        'success' => true,
        'url' => $url,
        'dashboard_url' => $dashboardDestination,
        'dashboard' => normalizeDashboardType($dashboardType) ?? $dashboardType,
        'contains_credentials' => $containsSecrets,
        'notice' => $containsSecrets
            ? 'Recipients sign in first; gateway credentials are not embedded in this share link when possible.'
            : 'Recipients sign in at the portal, then open the dashboard with this dataset.',
    ]);
} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to build dashboard share link', [
        'dataset_id' => $datasetId ?? 'unknown',
        'error' => $e->getMessage(),
    ]);
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage(),
    ]);
}
