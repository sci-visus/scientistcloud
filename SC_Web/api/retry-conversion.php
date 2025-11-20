<?php
/**
 * Retry Conversion API Endpoint
 * Retries a failed dataset conversion by setting status back to "conversion queued"
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

// MongoDB classes for direct status update
use MongoDB\Driver\Manager;
use MongoDB\Driver\BulkWrite;
use MongoDB\BSON\UTCDateTime;

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    $dataset_uuid = $input['dataset_uuid'] ?? $_POST['dataset_uuid'] ?? $_GET['dataset_uuid'] ?? null;

    if (!$dataset_uuid) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'dataset_uuid is required']);
        exit;
    }

    // Get user email from session or current user
    $user = getCurrentUser();
    $user_email = $_SESSION['user_email'] ?? ($user ? $user['email'] : null);

    if (!$user_email) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User email not found in session']);
        exit;
    }

    // Determine FastAPI URL (Docker vs local)
    $fastapi_url = getenv('FASTAPI_URL');
    if (!$fastapi_url) {
        // Check if we're in Docker (check for docker-compose service name)
        if (file_exists('/.dockerenv') || getenv('DOCKER_CONTAINER')) {
            $fastapi_url = 'http://sclib_fastapi:5001';
        } else {
            $fastapi_url = 'http://localhost:5001';
        }
    }

    // Get dataset details to check if it has a Google Drive link
    $dataset_url = rtrim($fastapi_url, '/') . '/api/v1/datasets/' . urlencode($dataset_uuid) . '?user_email=' . urlencode($user_email);
    $ch_dataset = curl_init($dataset_url);
    curl_setopt_array($ch_dataset, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
        ],
        CURLOPT_TIMEOUT => 10,
        CURLOPT_CONNECTTIMEOUT => 5
    ]);
    
    $dataset_response = curl_exec($ch_dataset);
    $dataset_http_code = curl_getinfo($ch_dataset, CURLINFO_HTTP_CODE);
    curl_close($ch_dataset);
    
    $has_google_drive_link = false;
    if ($dataset_http_code === 200) {
        $dataset_data = json_decode($dataset_response, true);
        if ($dataset_data && isset($dataset_data['dataset'])) {
            $dataset = $dataset_data['dataset'];
            $google_drive_link = $dataset['google_drive_link'] ?? '';
            // Check if google_drive_link contains "google" (case-insensitive)
            if (!empty($google_drive_link) && stripos($google_drive_link, 'google') !== false) {
                $has_google_drive_link = true;
            }
        }
    }
    
    // If dataset has Google Drive link, set status to "submitted" instead of calling convert
    if ($has_google_drive_link) {
        // Use SCLib client to directly update dataset status in MongoDB
        require_once(__DIR__ . '/../includes/sclib_client.php');
        
        try {
            $sclibClient = getSCLibClient();
            
            // Directly update the dataset status using the updateDataset method
            // We'll use a workaround: call the update endpoint, but we need to update status directly
            // Since the update endpoint doesn't support status, we'll use makeRequest to update via FastAPI
            // Actually, let's use the dataset manager to update status directly in MongoDB
            
            // Get MongoDB connection from config
            $mongo_url = MONGO_URL;
            $db_name = DB_NAME;
            
            // Use MongoDB driver to directly update status
            $mongo = new Manager($mongo_url);
            $bulk = new BulkWrite();
            
            $bulk->update(
                ['uuid' => $dataset_uuid],
                ['$set' => [
                    'status' => 'submitted',
                    'updated_at' => new UTCDateTime()
                ]],
                ['multi' => false]
            );
            
            $result = $mongo->executeBulkWrite($db_name . '.visstoredatas', $bulk);
            
            ob_end_clean();
            
            if ($result->getModifiedCount() > 0 || $result->getMatchedCount() > 0) {
                http_response_code(200);
                echo json_encode([
                    'success' => true,
                    'message' => 'Google Drive upload retry triggered successfully. Status set to "submitted". The background service will process it shortly.',
                    'status' => 'submitted',
                    'dataset_uuid' => $dataset_uuid
                ]);
                exit;
            } else {
                http_response_code(404);
                echo json_encode([
                    'success' => false,
                    'error' => 'Dataset not found or status not updated',
                    'dataset_uuid' => $dataset_uuid
                ]);
                exit;
            }
        } catch (Exception $e) {
            ob_end_clean();
            logMessage('ERROR', 'Failed to update dataset status for Google Drive retry', [
                'dataset_uuid' => $dataset_uuid,
                'error' => $e->getMessage()
            ]);
            http_response_code(500);
            echo json_encode([
                'success' => false,
                'error' => 'Failed to update dataset status',
                'message' => $e->getMessage()
            ]);
            exit;
        }
    }

    // For non-Google Drive datasets, call the convert endpoint as before
    // FastAPI expects user_email as a query parameter for POST endpoints with simple types
    $url = rtrim($fastapi_url, '/') . '/api/v1/datasets/' . urlencode($dataset_uuid) . '/convert?user_email=' . urlencode($user_email);
    
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
        ],
        CURLOPT_POSTFIELDS => '{}', // Empty JSON body since user_email is in query string
        CURLOPT_TIMEOUT => 30,
        CURLOPT_CONNECTTIMEOUT => 10
    ]);

    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curl_error = curl_error($ch);
    curl_close($ch);

    ob_end_clean();

    if ($curl_error) {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to connect to conversion service',
            'message' => $curl_error
        ]);
        exit;
    }

    if ($http_code >= 200 && $http_code < 300) {
        $response_data = json_decode($response, true);
        if ($response_data && isset($response_data['success']) && $response_data['success']) {
            http_response_code(200);
            echo json_encode([
                'success' => true,
                'message' => 'Conversion retry triggered successfully',
                'status' => $response_data['status'] ?? 'conversion queued',
                'dataset_uuid' => $dataset_uuid
            ]);
        } else {
            http_response_code($http_code);
            echo json_encode([
                'success' => false,
                'error' => 'Conversion retry failed',
                'message' => $response_data['detail'] ?? $response_data['error'] ?? 'Unknown error'
            ]);
        }
    } else {
        http_response_code($http_code);
        $error_data = json_decode($response, true);
        echo json_encode([
            'success' => false,
            'error' => 'Conversion retry failed',
            'message' => $error_data['detail'] ?? $error_data['error'] ?? 'Unknown error',
            'http_code' => $http_code
        ]);
    }
    exit;

} catch (Error $e) {
    // Handle fatal errors in PHP 7+
    ob_end_clean();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    exit;
} catch (Exception $e) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    exit;
}

