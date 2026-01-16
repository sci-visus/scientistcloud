<?php
/**
 * Public Dataset Details API Endpoint
 * Returns detailed information about a public dataset (no authentication required)
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

// Start session (for any session-based features, but no auth required)
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
require_once(__DIR__ . '/../includes/dataset_manager.php');

try {
    // Get dataset ID from request
    $datasetId = $_GET['dataset_id'] ?? null;
    if (!$datasetId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset ID is required']);
        exit;
    }

    // Get MongoDB connection to verify dataset is public
    $mongo_url = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: 'mongodb://localhost:27017');
    $db_name = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
    
    // Check if MongoDB extension is available
    if (!class_exists('MongoDB\Client')) {
        ob_end_clean();
        http_response_code(500);
        echo json_encode(['success' => false, 'error' => 'Database connection not available']);
        exit;
    }
    
    // Use MongoDB PHP extension
    $mongo_client = new MongoDB\Client($mongo_url);
    $db = $mongo_client->selectDatabase($db_name);
    $datasets_collection = $db->selectCollection(COLLECTION_DATASETS);
    
    // Find dataset by UUID or ID
    $dataset = $datasets_collection->findOne([
        '$or' => [
            ['uuid' => $datasetId],
            ['_id' => new MongoDB\BSON\ObjectId($datasetId)]
        ]
    ]);
    
    if (!$dataset) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }
    
    // Convert MongoDB document to array
    $datasetArray = $dataset->toArray();
    
    // Verify dataset is public
    $is_public = $datasetArray['is_public'] ?? false;
    if (is_string($is_public)) {
        $is_public = filter_var($is_public, FILTER_VALIDATE_BOOLEAN);
    }
    
    if (!$is_public && $is_public !== 'true' && $is_public !== 'True' && $is_public !== 1) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Dataset is not public']);
        exit;
    }
    
    // Format dataset (keep UUID for dashboard loading, but remove user info)
    $formattedDataset = formatDataset($datasetArray);
    
    // Remove sensitive user information for public access (keep UUID for dashboard functionality)
    unset($formattedDataset['user_id']);
    unset($formattedDataset['user']);
    unset($formattedDataset['user_email']);
    unset($formattedDataset['shared_with']);
    unset($formattedDataset['team_id']);
    
    // Format response
    $response = [
        'success' => true,
        'dataset' => $formattedDataset
    ];

    // Clean output buffer and send response
    ob_end_clean();
    echo json_encode($response, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get public dataset details', ['dataset_id' => $datasetId ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
}
?>

