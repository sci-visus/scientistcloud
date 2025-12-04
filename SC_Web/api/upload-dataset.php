<?php
/**
 * Upload Dataset API Endpoint (Proxy)
 * Proxies file uploads to the SCLib Upload API (FastAPI service)
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
error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED);

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

// Verify PHP upload settings (these should be set in .htaccess or php.ini)
// Note: ini_set() cannot change post_max_size or upload_max_filesize (PHP_INI_SYSTEM)
$post_max_size = ini_get('post_max_size');
$upload_max_filesize = ini_get('upload_max_filesize');

// Log current settings for debugging
error_log("PHP upload settings - post_max_size: $post_max_size, upload_max_filesize: $upload_max_filesize");

// Check if Content-Length exceeds post_max_size
if (isset($_SERVER['CONTENT_LENGTH'])) {
    $content_length = intval($_SERVER['CONTENT_LENGTH']);
    $post_max_bytes = parse_size($post_max_size);
    
    if ($content_length > $post_max_bytes) {
        ob_end_clean();
        http_response_code(413);
        echo json_encode([
            'success' => false,
            'error' => "File too large. Content-Length ($content_length bytes) exceeds post_max_size ($post_max_size = $post_max_bytes bytes). Please check PHP configuration."
        ]);
        exit;
    }
}

// Helper function to parse size strings like "2T", "10G", "100M"
function parse_size($size) {
    $size = trim($size);
    $last = strtolower($size[strlen($size)-1]);
    $value = floatval($size);
    
    switch($last) {
        case 't': $value *= 1024;
        case 'g': $value *= 1024;
        case 'm': $value *= 1024;
        case 'k': $value *= 1024;
    }
    
    return intval($value);
}

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    $user = getCurrentUser();
    if (!$user) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User not authenticated']);
        exit;
    }

    // Check if file was uploaded
    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'No file uploaded or upload error occurred',
            'upload_error' => $_FILES['file']['error'] ?? 'No file'
        ]);
        exit;
    }

    // Get form data
    $userEmail = $_POST['user_email'] ?? $user['email'];
    $datasetName = $_POST['dataset_name'] ?? 'Unnamed Dataset';
    $sensor = $_POST['sensor'] ?? 'OTHER';
    $convert = isset($_POST['convert']) ? filter_var($_POST['convert'], FILTER_VALIDATE_BOOLEAN) : true;
    $isPublic = isset($_POST['is_public']) ? filter_var($_POST['is_public'], FILTER_VALIDATE_BOOLEAN) : false;
    $folder = $_POST['folder'] ?? null;  // UI organization metadata only, NOT for file system structure
    $relativePath = $_POST['relative_path'] ?? null;  // For preserving directory structure in directory uploads
    $teamUuid = $_POST['team_uuid'] ?? null;
    $tags = $_POST['tags'] ?? '';
    $datasetIdentifier = $_POST['dataset_identifier'] ?? null;
    $addToExisting = isset($_POST['add_to_existing']) ? filter_var($_POST['add_to_existing'], FILTER_VALIDATE_BOOLEAN) : false;

    // Get SCLib Upload API URL from config
    // Priority: SCLIB_UPLOAD_URL (from env) > SCLIB_API_URL > EXISTING_API_URL > fallback
    // SCLIB_UPLOAD_URL should be set in docker-compose.yml to use IP address for reliability
    $uploadApiUrl = getenv('SCLIB_UPLOAD_URL') 
        ?: getenv('SCLIB_API_URL') 
        ?: getenv('EXISTING_API_URL')
        ?: (getenv('DOCKER_ENV') ? 'http://sclib_fastapi:5001' : 'http://localhost:5001')
        ?: 'http://localhost:5001';
    
    // Log the API URL being used (for debugging)
    error_log("Upload API URL: " . $uploadApiUrl);
    
    // OPTIMIZATION: Reduce file copies by using path-based upload when possible
    // Strategy:
    // 1. For large files (>100MB): Use chunked uploads (writes directly to final destination)
    // 2. For smaller files: Move PHP temp to shared location and use path-based endpoint
    // This eliminates the FastAPI temp copy, reducing from 3 copies to 2 copies
    
    $filePath = $_FILES['file']['tmp_name'];
    $fileName = $_FILES['file']['name'];
    $fileSize = $_FILES['file']['size'];
    $fileSizeMB = $fileSize / (1024 * 1024);
    $fileSizeGB = $fileSize / (1024 * 1024 * 1024);
    
    // Large file threshold (100MB) - use chunked uploads which write directly to destination
    $LARGE_FILE_THRESHOLD = 100 * 1024 * 1024; // 100MB
    
    // Shared temp directory that both PHP and FastAPI can access
    $sharedTempDir = '/mnt/visus_datasets/tmp';
    
    // For files > 100MB, we'll use chunked uploads (handled by frontend)
    // For smaller files, optimize by using path-based upload
    $usePathBasedUpload = false;
    $sharedTempPath = null;
    
    if ($fileSize < $LARGE_FILE_THRESHOLD && is_dir($sharedTempDir) && is_writable($sharedTempDir)) {
        // Move PHP temp file to shared location for path-based upload
        // This eliminates FastAPI's temp copy
        $sharedTempPath = $sharedTempDir . '/' . uniqid('upload_', true) . '_' . basename($fileName);
        
        if (move_uploaded_file($filePath, $sharedTempPath)) {
            $usePathBasedUpload = true;
            error_log("Optimization: Moved file to shared temp for path-based upload: $sharedTempPath");
        } else {
            error_log("Warning: Failed to move file to shared temp, falling back to content upload");
            $sharedTempPath = null;
        }
    }
    
    if ($usePathBasedUpload) {
        // Use path-based upload endpoint (eliminates FastAPI temp copy)
        $uploadEndpoint = rtrim($uploadApiUrl, '/') . '/api/upload/upload-path';
        error_log("Using optimized path-based upload endpoint: $uploadEndpoint");
        
        $postData = [
            'file_path' => $sharedTempPath,
            'original_filename' => $fileName,  // Pass original filename to preserve it
            'user_email' => $userEmail,
            'dataset_name' => $datasetName,
            'sensor' => $sensor,
            'convert' => $convert ? 'true' : 'false',
            'is_public' => $isPublic ? 'true' : 'false'
        ];
    } else {
        // Fallback to content-based upload (for large files or if shared temp unavailable)
        $uploadEndpoint = rtrim($uploadApiUrl, '/') . '/api/upload/upload';
        error_log("Using content-based upload endpoint: $uploadEndpoint");
        
        // Create CURLFile for file upload
        $cfile = new CURLFile($filePath, $_FILES['file']['type'], $fileName);
        
        $postData = [
            'file' => $cfile,
            'user_email' => $userEmail,
            'dataset_name' => $datasetName,
            'sensor' => $sensor,
            'convert' => $convert ? 'true' : 'false',
            'is_public' => $isPublic ? 'true' : 'false'
        ];
    }
    
    // Add optional parameters
    if ($folder) {
        $postData['folder'] = $folder;  // Metadata only - for UI organization
    }
    if ($relativePath) {
        $postData['relative_path'] = $relativePath;  // For preserving directory structure
    }
    if ($teamUuid) {
        $postData['team_uuid'] = $teamUuid;
    }
    if ($tags) {
        $postData['tags'] = $tags;
    }
    if ($datasetIdentifier) {
        $postData['dataset_identifier'] = $datasetIdentifier;
    }
    if ($addToExisting) {
        $postData['add_to_existing'] = 'true';
    }

    // Forward request to SCLib Upload API
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $uploadEndpoint);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: application/json'
    ]);
    // Calculate timeout based on file size
    // For very large files (TB+), use very long timeouts
    // Base timeout: 5 minutes, plus 2 seconds per MB
    // For files > 1GB, use longer timeout (up to 2 hours for very large files)
    $fileSizeMB = $fileSize / (1024 * 1024);
    $fileSizeGB = $fileSize / (1024 * 1024 * 1024);
    
    if ($fileSizeGB > 1.0) {
        // For files > 1GB: 10 minutes base + 1 minute per GB, capped at 2 hours
        $calculatedTimeout = min(max(600, intval($fileSizeGB * 60)), 7200); // 10 min to 2 hours
    } else {
        // For smaller files: 5 minutes base + 2 seconds per MB
        $calculatedTimeout = min(max(300, intval($fileSizeMB * 2)), 600); // 5 min to 10 min
    }
    
    curl_setopt($ch, CURLOPT_TIMEOUT, $calculatedTimeout);
    error_log("Upload timeout set to {$calculatedTimeout}s for file size: {$fileSizeMB} MB ({$fileSizeGB} GB)");
    curl_setopt($ch, CURLOPT_VERBOSE, false); // Set to true for debugging
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    $curlInfo = curl_getinfo($ch);
    curl_close($ch);
    
    // Log request details for debugging
    error_log("Upload API request: URL=$uploadEndpoint, HTTP_CODE=$httpCode, Response length=" . strlen($response));
    if ($httpCode >= 400) {
        error_log("Upload API error response: " . substr($response, 0, 500));
    }

    ob_end_clean();

    if ($curlError) {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to connect to upload service',
            'message' => $curlError
        ]);
        exit;
    }

    // Clean up shared temp file if we used path-based upload and there was an error
    if ($usePathBasedUpload && $sharedTempPath && file_exists($sharedTempPath)) {
        if ($httpCode >= 400) {
            // Error occurred, clean up temp file
            @unlink($sharedTempPath);
            error_log("Cleaned up shared temp file after error: $sharedTempPath");
        }
        // Note: If successful, FastAPI will handle cleanup when it moves the file to final destination
    }
    
    // Check HTTP status
    if ($httpCode >= 400) {
        // Log detailed error information
        error_log("Upload API error - HTTP Code: $httpCode, URL: $uploadEndpoint, Response: " . substr($response, 0, 500));
        
        http_response_code($httpCode);
        // Try to parse error response
        $errorData = json_decode($response, true);
        if ($errorData) {
            echo json_encode([
                'success' => false,
                'error' => $errorData['detail'] ?? $errorData['error'] ?? 'Upload failed',
                'message' => $errorData['message'] ?? null,
                'http_code' => $httpCode,
                'api_url' => $uploadEndpoint
            ]);
        } else {
            echo json_encode([
                'success' => false,
                'error' => 'Upload failed',
                'message' => $response ? substr($response, 0, 200) : 'No response from server',
                'http_code' => $httpCode,
                'api_url' => $uploadEndpoint
            ]);
        }
        exit;
    }

    // Parse and return response
    // Clean any whitespace/control characters that might be before/after JSON
    $response = trim($response);
    
    // Find the JSON portion (might have extra content before/after)
    $jsonStart = strpos($response, '{');
    $jsonStartAlt = strpos($response, '[');
    
    if ($jsonStart === false && $jsonStartAlt === false) {
        // No JSON found - might be HTML error page
        error_log("Upload API returned non-JSON response (first 500 chars): " . substr($response, 0, 500));
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid response from upload service',
            'message' => 'Response does not appear to be JSON',
            'raw_response_preview' => substr($response, 0, 200)
        ]);
        exit;
    }
    
    // Extract JSON portion (from first { or [ to matching closing bracket)
    $startPos = ($jsonStart !== false) ? $jsonStart : $jsonStartAlt;
    $jsonString = substr($response, $startPos);
    
    // Find the matching closing bracket
    $openChar = $jsonString[0];
    $closeChar = ($openChar === '{') ? '}' : ']';
    $depth = 0;
    $endPos = -1;
    
    for ($i = 0; $i < strlen($jsonString); $i++) {
        if ($jsonString[$i] === $openChar) {
            $depth++;
        } elseif ($jsonString[$i] === $closeChar) {
            $depth--;
            if ($depth === 0) {
                $endPos = $i + 1;
                break;
            }
        }
    }
    
    if ($endPos > 0) {
        $jsonString = substr($jsonString, 0, $endPos);
    }
    
    // Try to parse the extracted JSON
    $responseData = json_decode($jsonString, true);
    if ($responseData === null) {
        // Response is not valid JSON - log it for debugging
        $jsonError = json_last_error_msg();
        error_log("Upload API returned invalid JSON. Error: $jsonError. Response (first 500 chars): " . substr($response, 0, 500));
        error_log("Extracted JSON string (first 500 chars): " . substr($jsonString, 0, 500));
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid JSON response from upload service',
            'json_error' => $jsonError,
            'raw_response_preview' => substr($response, 0, 200)
        ]);
        exit;
    }

    // Return the response from SCLib API
    echo json_encode($responseData);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to upload dataset', [
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

