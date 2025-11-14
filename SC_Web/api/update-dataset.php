<?php
/**
 * Update Dataset API Endpoint
 * Updates editable fields for a dataset
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
header('Access-Control-Allow-Methods: PUT, POST, OPTIONS');
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

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get request body
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (!$data) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Invalid JSON data']);
        exit;
    }

    // Get dataset ID from request
    $datasetId = $data['dataset_id'] ?? $_GET['dataset_id'] ?? null;
    if (!$datasetId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset ID is required']);
        exit;
    }

    // Get dataset to verify access
    $dataset = getDatasetById($datasetId);
    if (!$dataset) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    // Check if user has access to this dataset
    $user = getCurrentUser();
    if ($dataset['user_id'] !== $user['email'] && 
        !in_array($user['email'], $dataset['shared_with'] ?? []) &&
        $dataset['team_uuid'] !== $user['team_id']) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Access denied']);
        exit;
    }

    // Prepare update data - only include editable fields
    $updateData = [];
    
    if (isset($data['name'])) {
        $updateData['name'] = $data['name'];
    }
    if (isset($data['tags'])) {
        $updateData['tags'] = $data['tags'];
    }
    if (isset($data['folder_uuid'])) {
        $updateData['folder_uuid'] = $data['folder_uuid'];
    }
    if (isset($data['team_uuid'])) {
        $updateData['team_uuid'] = $data['team_uuid'];
    }
    if (isset($data['dimensions'])) {
        $updateData['dimensions'] = $data['dimensions'];
    }
    if (isset($data['preferred_dashboard'])) {
        $updateData['preferred_dashboard'] = $data['preferred_dashboard'];
    }
    if (isset($data['google_drive_link'])) {
        $updateData['google_drive_link'] = $data['google_drive_link'];
    }

    if (empty($updateData)) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'No fields to update']);
        exit;
    }

    // Update dataset
    $result = updateDataset($datasetId, $updateData);
    
    if ($result['success'] ?? false) {
        // Get updated dataset
        $updatedDataset = getDatasetById($datasetId);
        
        ob_end_clean();
        echo json_encode([
            'success' => true,
            'message' => 'Dataset updated successfully',
            'dataset' => $updatedDataset
        ]);
    } else {
        ob_end_clean();
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => $result['error'] ?? 'Failed to update dataset'
        ]);
    }

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to update dataset', ['dataset_id' => $datasetId ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

