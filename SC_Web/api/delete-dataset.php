<?php
/**
 * Delete Dataset API Endpoint
 * Deletes a dataset and associated files
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    $datasetId = $input['dataset_id'] ?? null;
    
    if (!$datasetId) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset ID is required']);
        exit;
    }

    // Get dataset details
    $dataset = getDatasetById($datasetId);
    if (!$dataset) {
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    // Check if user has permission to delete this dataset
    $user = getCurrentUser();
    if ($dataset['user_id'] !== $user['id']) {
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Access denied']);
        exit;
    }

    // Delete dataset
    $success = deleteDataset($datasetId);
    
    if ($success) {
        // TODO: Delete associated files from storage
        // This would involve removing files from the upload and converted directories
        
        logMessage('INFO', 'Dataset deleted successfully', [
            'dataset_id' => $datasetId,
            'user_id' => $user['id']
        ]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Dataset deleted successfully'
        ]);
    } else {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to delete dataset'
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
