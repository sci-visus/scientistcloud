<?php
/**
 * Dataset File Serve Endpoint
 * Serves image files from dataset directories
 */

if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED);

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        http_response_code(401);
        header('Content-Type: text/plain');
        echo 'Authentication required';
        exit;
    }

    // Get parameters
    $datasetUuid = $_GET['dataset_uuid'] ?? null;
    $filePath = $_GET['file_path'] ?? null;
    $directory = $_GET['directory'] ?? null;
    
    if (!$datasetUuid || !$filePath || !$directory) {
        http_response_code(400);
        header('Content-Type: text/plain');
        echo 'Missing required parameters';
        exit;
    }

    // Validate UUID format
    if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $datasetUuid)) {
        http_response_code(400);
        header('Content-Type: text/plain');
        echo 'Invalid UUID format';
        exit;
    }

    // Validate directory
    if ($directory !== 'upload' && $directory !== 'converted') {
        http_response_code(400);
        header('Content-Type: text/plain');
        echo 'Invalid directory';
        exit;
    }

    // Get dataset to verify access
    $user = getCurrentUser();
    if (!$user) {
        http_response_code(401);
        header('Content-Type: text/plain');
        echo 'User not authenticated';
        exit;
    }
    
    // Note: We'll skip dataset verification here and let FastAPI handle access control
    // This avoids potential issues with getDatasetDetails returning HTML errors
    // FastAPI will verify access when we request the file

    // Get file from FastAPI service (which has access to /mnt/visus_datasets)
    // We'll proxy the file through FastAPI
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
    
    // Build the file serve endpoint URL
    $serveEndpoint = rtrim($apiUrl, '/') . '/api/v1/datasets/' . urlencode($datasetUuid) . '/file-serve';
    $params = [
        'file_path' => $filePath,
        'directory' => $directory,
        'user_email' => $user['email'] ?? null
    ];
    $queryString = http_build_query($params);
    $fullUrl = $serveEndpoint . '?' . $queryString;
    
    // Forward request to FastAPI
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $fullUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $contentType = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
    $curlError = curl_error($ch);
    curl_close($ch);
    
    if ($curlError || $httpCode >= 400) {
        logMessage('ERROR', 'Failed to serve file', [
            'dataset_uuid' => $datasetUuid,
            'file_path' => $filePath,
            'directory' => $directory,
            'curl_error' => $curlError,
            'http_code' => $httpCode
        ]);
        
        http_response_code($httpCode ?: 500);
        header('Content-Type: text/plain');
        echo $curlError ?: 'Failed to serve file';
        exit;
    }

    // Set appropriate headers
    if ($contentType) {
        header('Content-Type: ' . $contentType);
    }
    header('Content-Length: ' . strlen($response));
    header('Cache-Control: private, max-age=3600');
    
    // Output file content
    echo $response;

} catch (Exception $e) {
    http_response_code(500);
    header('Content-Type: text/plain');
    echo 'Internal server error';
    logMessage('ERROR', 'Failed to serve file', ['error' => $e->getMessage()]);
}
?>

