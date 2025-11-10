<?php
/**
 * Delete Dataset API Endpoint
 * Deletes a dataset entry from the database (using SCLib API)
 * Note: File cleanup will be handled by a separate maintenance script
 */

// Start output buffering IMMEDIATELY
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

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    $datasetId = $input['dataset_id'] ?? $input['dataset_uuid'] ?? null;
    
    if (!$datasetId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset ID is required']);
        exit;
    }

    // Get dataset details to verify access
    $dataset = getDatasetById($datasetId);
    if (!$dataset) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    // Check if user has permission to delete this dataset
    $user = getCurrentUser();
    if (!$user) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User not authenticated']);
        exit;
    }
    
    // Check ownership (use email as primary identifier)
    if ($dataset['user_id'] !== $user['email'] && $dataset['user_id'] !== $user['id']) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Only the dataset owner can delete it']);
        exit;
    }

    // Delete dataset - returns result array with success/error
    $result = deleteDataset($datasetId);
    
    if ($result['success'] ?? false) {
        // Note: Only database entry is deleted for now
        // File cleanup will be handled by a separate maintenance script in the future
        
        logMessage('INFO', 'Dataset deleted successfully', [
            'dataset_id' => $datasetId,
            'user_email' => $user['email']
        ]);
        
        ob_end_clean();
        echo json_encode([
            'success' => true,
            'message' => 'Dataset deleted successfully'
        ]);
    } else {
        ob_end_clean();
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => $result['error'] ?? 'Failed to delete dataset'
        ]);
    }

} catch (Exception $e) {
    logMessage('ERROR', 'Failed to delete dataset', ['dataset_id' => $datasetId ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>
