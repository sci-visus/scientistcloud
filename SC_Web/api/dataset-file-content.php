<?php
/**
 * Dataset File Content API Endpoint
 * Returns file content for text files or image URLs for image files
 */

if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED);

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
require_once(__DIR__ . '/../includes/sclib_client.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get parameters
    $datasetUuid = $_GET['dataset_uuid'] ?? null;
    $filePath = $_GET['file_path'] ?? null;
    $directory = $_GET['directory'] ?? null; // 'upload' or 'converted'
    
    if (!$datasetUuid || !$filePath || !$directory) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Missing required parameters: dataset_uuid, file_path, directory']);
        exit;
    }

    // Validate UUID format
    if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $datasetUuid)) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Invalid UUID format']);
        exit;
    }

    // Validate directory
    if ($directory !== 'upload' && $directory !== 'converted') {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Directory must be "upload" or "converted"']);
        exit;
    }

    // Get dataset to verify access
    $user = getCurrentUser();
    if (!$user) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User not authenticated']);
        exit;
    }
    
    // Use SCLib client to get dataset details (which handles access control)
    $sclibClient = getSCLibClient();
    
    // Get dataset details to verify it exists and user has access
    // The FastAPI endpoint will handle access control
    // We'll just verify the dataset exists by calling the API
    // Note: We'll skip this check and let FastAPI handle access control
    // This avoids potential issues with getDatasetDetails returning HTML errors
    // FastAPI will verify access when we request the file content

    // Call FastAPI endpoint to get file content
    // The FastAPI service has access to /mnt/visus_datasets
    $apiUrl = getenv('SCLIB_DATASET_URL') ?: getenv('SCLIB_API_URL') ?: getenv('EXISTING_API_URL');
    
    // If running in Docker, use service name; otherwise use localhost
    if (!$apiUrl) {
        // Check if we're in Docker
        if (file_exists('/.dockerenv') || getenv('DOCKER_CONTAINER')) {
            $apiUrl = 'http://sclib_fastapi:5001';
        } else {
            $apiUrl = 'http://localhost:5001';
        }
    }
    
    // Build the file content endpoint URL
    $contentEndpoint = rtrim($apiUrl, '/') . '/api/v1/datasets/' . urlencode($datasetUuid) . '/file-content';
    $userEmail = $user['email'] ?? null;
    $params = [
        'file_path' => $filePath,
        'directory' => $directory,
        'user_email' => $userEmail
    ];
    $queryString = http_build_query($params);
    $fullUrl = $contentEndpoint . '?' . $queryString;
    
    // Forward request to FastAPI
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $fullUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: application/json'
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    $curlErrno = curl_errno($ch);
    curl_close($ch);
    
    ob_end_clean();

    if ($curlError || $curlErrno) {
        logMessage('ERROR', 'Failed to get file content', [
            'dataset_uuid' => $datasetUuid,
            'file_path' => $filePath,
            'directory' => $directory,
            'curl_error' => $curlError,
            'curl_errno' => $curlErrno
        ]);
        
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to connect to file service',
            'message' => $curlError ?: "Connection error (code: $curlErrno)"
        ]);
        exit;
    }

    // Check HTTP status
    if ($httpCode >= 400) {
        http_response_code($httpCode);
        $errorData = json_decode($response, true);
        if ($errorData) {
            echo json_encode([
                'success' => false,
                'error' => $errorData['detail'] ?? $errorData['error'] ?? 'Failed to get file content'
            ]);
        } else {
            echo json_encode([
                'success' => false,
                'error' => 'Failed to get file content',
                'message' => $response ? substr($response, 0, 200) : 'No response from server'
            ]);
        }
        exit;
    }

    // Parse and return response
    $response = trim($response);
    
    // Check if response starts with HTML (error page)
    if (strpos($response, '<') === 0 || strpos($response, '<br') !== false) {
        logMessage('ERROR', 'File service returned HTML instead of JSON', [
            'dataset_uuid' => $datasetUuid,
            'file_path' => $filePath,
            'directory' => $directory,
            'response_preview' => substr($response, 0, 500)
        ]);
        
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'File service returned invalid response',
            'message' => 'The server returned an error page instead of file content'
        ]);
        exit;
    }
    
    $responseData = json_decode($response, true);
    
    if ($responseData === null) {
        logMessage('ERROR', 'Invalid JSON response from file service', [
            'dataset_uuid' => $datasetUuid,
            'file_path' => $filePath,
            'directory' => $directory,
            'response_preview' => substr($response, 0, 500)
        ]);
        
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid JSON response from file service',
            'message' => 'The server returned an invalid response'
        ]);
        exit;
    }

    // Return the response from FastAPI
    echo json_encode($responseData);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get file content', [
        'error' => $e->getMessage(),
        'trace' => $e->getTraceAsString()
    ]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

