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
    $folder = $_POST['folder'] ?? null;
    $teamUuid = $_POST['team_uuid'] ?? null;
    $tags = $_POST['tags'] ?? '';

    // Get SCLib Upload API URL from config
    $uploadApiUrl = getenv('SCLIB_UPLOAD_URL') ?: getenv('SCLIB_API_URL') ?: 'http://localhost:5001';
    
    // Prepare multipart form data for forwarding to SCLib API
    $filePath = $_FILES['file']['tmp_name'];
    $fileName = $_FILES['file']['name'];
    $fileSize = $_FILES['file']['size'];
    
    // Create CURLFile for file upload
    $cfile = new CURLFile($filePath, $_FILES['file']['type'], $fileName);
    
    // Prepare POST data
    $postData = [
        'file' => $cfile,
        'user_email' => $userEmail,
        'dataset_name' => $datasetName,
        'sensor' => $sensor,
        'convert' => $convert ? 'true' : 'false',
        'is_public' => $isPublic ? 'true' : 'false'
    ];
    
    if ($folder) {
        $postData['folder'] = $folder;
    }
    if ($teamUuid) {
        $postData['team_uuid'] = $teamUuid;
    }
    if ($tags) {
        $postData['tags'] = $tags;
    }

    // Forward request to SCLib Upload API
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $uploadApiUrl . '/api/upload/upload');
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: application/json'
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 300); // 5 minute timeout for large files
    curl_setopt($ch, CURLOPT_VERBOSE, false); // Set to true for debugging
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    $curlInfo = curl_getinfo($ch);
    curl_close($ch);
    
    // Log request details for debugging
    error_log("Upload API request: URL=" . $uploadApiUrl . '/api/upload/upload' . ", HTTP_CODE=$httpCode, Response length=" . strlen($response));

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

    // Check HTTP status
    if ($httpCode >= 400) {
        http_response_code($httpCode);
        // Try to parse error response
        $errorData = json_decode($response, true);
        if ($errorData) {
            echo json_encode([
                'success' => false,
                'error' => $errorData['detail'] ?? $errorData['error'] ?? 'Upload failed',
                'message' => $errorData['message'] ?? null
            ]);
        } else {
            echo json_encode([
                'success' => false,
                'error' => 'Upload failed',
                'message' => $response
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

