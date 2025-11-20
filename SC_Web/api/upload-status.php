<?php
/**
 * Upload Status API Endpoint (Proxy)
 * Proxies upload status requests to the SCLib Upload API (FastAPI service)
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

    // Get job_id from URL path
    $requestUri = $_SERVER['REQUEST_URI'];
    $pathParts = explode('/', trim(parse_url($requestUri, PHP_URL_PATH), '/'));
    
    // Find 'upload-status' in path and get job_id after it
    $jobId = null;
    $foundIndex = false;
    for ($i = 0; $i < count($pathParts); $i++) {
        if ($pathParts[$i] === 'upload-status' && isset($pathParts[$i + 1])) {
            $jobId = $pathParts[$i + 1];
            $foundIndex = true;
            break;
        }
    }
    
    // Alternative: get from query parameter
    if (!$jobId) {
        $jobId = $_GET['job_id'] ?? null;
    }
    
    if (!$jobId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Job ID is required']);
        exit;
    }

    // Get SCLib Upload API URL from config
    // Try multiple environment variables and fallback to Docker service name
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
    
    // Build the status endpoint URL
    $statusEndpoint = rtrim($uploadApiUrl, '/') . '/api/upload/status/' . urlencode($jobId);

    // Forward request to SCLib Upload API
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $statusEndpoint);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: application/json'
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    $curlErrno = curl_errno($ch);
    curl_close($ch);
    
    ob_end_clean();

    if ($curlError || $curlErrno) {
        logMessage('ERROR', 'Failed to connect to upload status endpoint', [
            'job_id' => $jobId,
            'endpoint' => $statusEndpoint,
            'curl_error' => $curlError,
            'curl_errno' => $curlErrno,
            'upload_api_url' => $uploadApiUrl
        ]);
        
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to connect to upload service',
            'message' => $curlError ?: "Connection error (code: $curlErrno)",
            'endpoint' => $statusEndpoint
        ]);
        exit;
    }

    // Check HTTP status
    if ($httpCode >= 400) {
        // Log the error for debugging
        logMessage('ERROR', 'Upload status endpoint returned error', [
            'job_id' => $jobId,
            'http_code' => $httpCode,
            'endpoint' => $statusEndpoint,
            'response' => substr($response, 0, 500)
        ]);
        
        http_response_code($httpCode);
        // Try to parse error response
        $errorData = json_decode($response, true);
        if ($errorData) {
            echo json_encode([
                'success' => false,
                'error' => $errorData['detail'] ?? $errorData['error'] ?? 'Status check failed',
                'message' => $errorData['message'] ?? null,
                'http_code' => $httpCode
            ]);
        } else {
            echo json_encode([
                'success' => false,
                'error' => 'Status check failed',
                'message' => $response ? substr($response, 0, 200) : 'No response from server',
                'http_code' => $httpCode
            ]);
        }
        exit;
    }

    // Parse and return response
    $response = trim($response);
    $responseData = json_decode($response, true);
    
    if ($responseData === null) {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid JSON response from upload service',
            'raw_response_preview' => substr($response, 0, 200)
        ]);
        exit;
    }

    // Return the response from SCLib API
    echo json_encode($responseData);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get upload status', [
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

