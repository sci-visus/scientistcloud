<?php
/**
 * Dataset Status API Endpoint
 * Returns the current status of a dataset
 */

// Start output buffering IMMEDIATELY to catch any output from included files
if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

// Disable error display to prevent output
ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);

// Start session BEFORE including config.php to ensure session is available
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');
require_once(__DIR__ . '/../includes/dashboard_manager.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get dataset ID from request
    $datasetId = $_GET['dataset_id'] ?? null;
    if (!$datasetId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset ID is required']);
        exit;
    }

    // Get dataset details
    $dataset = getDatasetById($datasetId);
    if (!$dataset) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    // Check if user has access to this dataset
    $user = getCurrentUser();
    if ($dataset['user_id'] !== $user['id'] && 
        !in_array($user['id'], $dataset['shared_with'] ?? []) &&
        $dataset['team_id'] !== $user['team_id']) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Access denied']);
        exit;
    }

    // Get dashboard status
    $dashboardType = $_GET['dashboard'] ?? 'OpenVisusSlice';
    $status = getDashboardStatus($datasetId, $dashboardType);

    // Format response
    $response = [
        'success' => true,
        'status' => $status,
        'dataset' => [
            'id' => $dataset['id'],
            'name' => $dataset['name'],
            'status' => $dataset['status'],
            'compression_status' => $dataset['compression_status']
        ],
        'dashboard' => [
            'type' => $dashboardType,
            'status' => $status
        ]
    ];

    // Clean output buffer and send response
    ob_end_clean();
    echo json_encode($response);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get dataset status', ['dataset_id' => $datasetId ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>
