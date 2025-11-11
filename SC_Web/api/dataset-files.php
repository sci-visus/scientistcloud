<?php
/**
 * Dataset Files API Endpoint
 * Returns file and folder structure for a dataset UUID
 * Lists files from both upload/<uuid> and converted/<uuid> directories
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
require_once(__DIR__ . '/../includes/sclib_client.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get dataset UUID from request
    $datasetUuid = $_GET['dataset_uuid'] ?? null;
    if (!$datasetUuid) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset UUID is required']);
        exit;
    }

    // Validate UUID format
    if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $datasetUuid)) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Invalid UUID format']);
        exit;
    }

    // Get dataset to verify access
    $user = getCurrentUser();
    $dataset = getDatasetByUuid($datasetUuid);
    
    if (!$dataset) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    // Check if user has access to this dataset
    if ($dataset['user_id'] !== $user['id'] && 
        !in_array($user['id'], $dataset['shared_with'] ?? []) &&
        $dataset['team_id'] !== $user['team_id']) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Access denied']);
        exit;
    }

    // Get file listing from FastAPI service (not from local file system)
    // The PHP container doesn't have access to /mnt/visus_datasets - only the FastAPI container does
    $sclibClient = getSCLibClient();
    $userEmail = $user['email'] ?? null;
    
    $apiResponse = $sclibClient->listDatasetFiles($datasetUuid, $userEmail);
    
    if (!$apiResponse || !isset($apiResponse['success']) || !$apiResponse['success']) {
        $error = $apiResponse['error'] ?? 'Failed to retrieve files from API';
        ob_end_clean();
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => $error,
            'message' => 'Failed to retrieve files from FastAPI service'
        ]);
        exit;
    }
    
    // Return the API response directly (it already has the correct structure)
    $response = $apiResponse;

    // Clean output buffer and send response
    ob_end_clean();
    echo json_encode($response);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get dataset files', ['dataset_uuid' => $datasetUuid ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

