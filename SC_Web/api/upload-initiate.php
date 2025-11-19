<?php
/**
 * Upload Initiate API Endpoint (Proxy)
 * Proxies upload initiation requests to the SCLib Upload API (FastAPI service)
 * Used for Google Drive, S3, and URL uploads
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
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

try {
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get request body
    $input = file_get_contents('php://input');
    $requestData = json_decode($input, true);
    
    if (!$requestData) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Invalid JSON in request body']);
        exit;
    }

    // Get SCLib Upload API URL from config
    $uploadApiUrl = getenv('SCLIB_UPLOAD_URL') ?: getenv('SCLIB_API_URL') ?: getenv('SCLIB_DATASET_URL') ?: getenv('EXISTING_API_URL');
    
    // If running in Docker, use service name; otherwise use localhost
    if (!$uploadApiUrl) {
        // Check if we're in Docker (check for common Docker indicators)
        if (file_exists('/.dockerenv') || getenv('DOCKER_CONTAINER')) {
            $uploadApiUrl = 'http://sclib_fastapi:5001';
        } else {
            $uploadApiUrl = 'http://localhost:5001';
        }
    }
    
    // Build the initiate endpoint URL
    $initiateEndpoint = rtrim($uploadApiUrl, '/') . '/api/upload/initiate';

    // Forward request to SCLib Upload API
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $initiateEndpoint);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($requestData));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Accept: application/json'
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);
    
    // Clear output buffer
    ob_clean();
    
    if ($curlError) {
        http_response_code(502);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to connect to upload service',
            'detail' => $curlError
        ]);
        ob_end_flush();
        exit;
    }
    
    // Set HTTP status code from FastAPI response
    http_response_code($httpCode);
    
    // Return the response from FastAPI
    echo $response;
    
    ob_end_flush();
    exit;
    
} catch (Exception $e) {
    ob_clean();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    ob_end_flush();
    exit;
}

