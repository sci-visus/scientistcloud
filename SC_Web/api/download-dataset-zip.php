<?php
/**
 * Download Dataset Zip Endpoint
 * Downloads a dataset directory (upload or converted) as a zip file
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
require_once(__DIR__ . '/../includes/dataset_manager.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get parameters
    $datasetUuid = $_GET['dataset_uuid'] ?? null;
    $directory = $_GET['directory'] ?? null;
    $forceRecreate = isset($_GET['force_recreate']) ? filter_var($_GET['force_recreate'], FILTER_VALIDATE_BOOLEAN) : false;
    
    if (!$datasetUuid || !$directory) {
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Missing required parameters: dataset_uuid and directory']);
        exit;
    }

    // Validate UUID format
    if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $datasetUuid)) {
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Invalid UUID format']);
        exit;
    }

    // Validate directory
    if ($directory !== 'upload' && $directory !== 'converted') {
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Invalid directory. Must be "upload" or "converted"']);
        exit;
    }

    // Get dataset to verify access
    $user = getCurrentUser();
    if (!$user) {
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'User not authenticated']);
        exit;
    }
    
    // Get dataset details
    $dataset = getDatasetById($datasetUuid);
    if (!$dataset) {
        http_response_code(404);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }
    
    // Check access permissions
    $userEmail = $user['email'];
    $isOwner = ($dataset['user_id'] === $userEmail || $dataset['user_id'] === $user['id']);
    $isPublic = $dataset['is_public'] ?? false;
    $isPublicDownloadable = $dataset['is_public_downloadable'] ?? false;
    
    // Allow access if:
    // 1. User is owner, OR
    // 2. Dataset is public AND downloadable
    if (!$isOwner) {
        if (!$isPublic || !$isPublicDownloadable) {
            http_response_code(403);
            header('Content-Type: application/json');
            echo json_encode(['success' => false, 'error' => 'Access denied. Dataset is not publicly downloadable.']);
            exit;
        }
    }

    // Get FastAPI URL
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
    
    // Build the download zip endpoint URL
    $downloadEndpoint = rtrim($apiUrl, '/') . '/api/v1/datasets/' . urlencode($datasetUuid) . '/download-zip';
    $params = [
        'directory' => $directory,
        'user_email' => $userEmail
    ];
    if ($forceRecreate) {
        $params['force_recreate'] = 'true';
    }
    $queryString = http_build_query($params);
    $fullUrl = $downloadEndpoint . '?' . $queryString;
    
    // Forward request to FastAPI and stream the response
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $fullUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, false);  // Stream response
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 3600);  // 1 hour timeout for large zips
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 30);
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($ch, $data) {
        echo $data;
        flush();
        return strlen($data);
    });
    
    // Get headers from FastAPI response
    $headers = [];
    curl_setopt($ch, CURLOPT_HEADERFUNCTION, function($ch, $header) use (&$headers) {
        $len = strlen($header);
        $header = explode(':', $header, 2);
        if (count($header) == 2) {
            $headers[strtolower(trim($header[0]))] = trim($header[1]);
        }
        return $len;
    });
    
    $result = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);
    
    if ($curlError || $httpCode >= 400) {
        logMessage('ERROR', 'Failed to download zip', [
            'dataset_uuid' => $datasetUuid,
            'directory' => $directory,
            'curl_error' => $curlError,
            'http_code' => $httpCode
        ]);
        
        http_response_code($httpCode ?: 500);
        header('Content-Type: application/json');
        echo json_encode([
            'success' => false,
            'error' => $curlError ?: 'Failed to download zip file'
        ]);
        exit;
    }
    
    // If we get here, the zip was streamed successfully
    // Headers should have been set by FastAPI response
    exit;

} catch (Exception $e) {
    http_response_code(500);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    logMessage('ERROR', 'Failed to download zip', [
        'dataset_uuid' => $datasetUuid ?? 'unknown',
        'error' => $e->getMessage()
    ]);
    exit;
}
?>

