<?php
/**
 * Cancel Job API Endpoint
 * Cancels a running or queued job
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

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    $jobId = $input['job_id'] ?? null;
    
    if (!$jobId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Job ID is required']);
        exit;
    }

    // Use SCLib client to cancel job via FastAPI
    $sclib = getSCLibClient();
    
    try {
        $apiUrl = getenv('SCLIB_API_URL') ?: getenv('EXISTING_API_URL') ?: 'http://localhost:5001';
        $cancelUrl = rtrim($apiUrl, '/') . '/api/upload/cancel/' . urlencode($jobId);
        
        $response = $sclib->makeRequest('/api/upload/cancel/' . urlencode($jobId), 'POST');
        
        if ($response && isset($response['success']) && $response['success']) {
            ob_end_clean();
            echo json_encode([
                'success' => true,
                'message' => 'Job cancelled successfully'
            ]);
        } else {
            ob_end_clean();
            http_response_code(500);
            echo json_encode([
                'success' => false,
                'error' => $response['error'] ?? 'Failed to cancel job'
            ]);
        }
    } catch (Exception $e) {
        // If FastAPI fails, try MongoDB directly
        error_log("FastAPI cancel endpoint failed, trying MongoDB: " . $e->getMessage());
        
        $result = cancelJobInMongoDB($jobId, $user['email']);
        
        if ($result['success']) {
            ob_end_clean();
            echo json_encode([
                'success' => true,
                'message' => 'Job cancelled successfully'
            ]);
        } else {
            ob_end_clean();
            http_response_code(500);
            echo json_encode([
                'success' => false,
                'error' => $result['error'] ?? 'Failed to cancel job'
            ]);
        }
    }

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to cancel job', ['job_id' => $jobId ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    exit;
} catch (Error $e) {
    ob_end_clean();
    logMessage('ERROR', 'Fatal error cancelling job', ['job_id' => $jobId ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => 'A fatal error occurred while cancelling the job'
    ]);
    exit;
}

/**
 * Cancel job in MongoDB directly (fallback)
 */
function cancelJobInMongoDB($jobId, $userEmail) {
    try {
        // Get MongoDB connection from config
        $mongo_url = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: 'mongodb://localhost:27017');
        $db_name = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
        
        // Check if MongoDB extension is available
        if (!class_exists('MongoDB\Client')) {
            return ['success' => false, 'error' => 'MongoDB PHP extension not available'];
        }
        
        // Use MongoDB PHP extension
        $mongo_client = new MongoDB\Client($mongo_url);
        $db = $mongo_client->selectDatabase($db_name);
        $jobs_collection = $db->selectCollection('jobs');
        $datasets_collection = $db->selectCollection('visstoredatas');
        
        // Find job and verify ownership
        $job = $jobs_collection->findOne(['job_id' => $jobId]);
        if (!$job) {
            return ['success' => false, 'error' => 'Job not found'];
        }
        
        // Verify user owns the dataset
        if (isset($job['dataset_uuid'])) {
            $datasets_collection = $db->visstoredatas;
            $dataset = $datasets_collection->findOne(['uuid' => $job['dataset_uuid']]);
            if ($dataset && ($dataset['user_id'] !== $userEmail && $dataset['user_id'] !== $userEmail)) {
                return ['success' => false, 'error' => 'You do not have permission to cancel this job'];
            }
        }
        
        // Update job status to cancelled
        $result = $jobs_collection->updateOne(
            ['job_id' => $jobId],
            [
                '$set' => [
                    'status' => 'cancelled',
                    'updated_at' => new MongoDB\BSON\UTCDateTime()
                ]
            ]
        );
        
        if ($result->getModifiedCount() > 0) {
            return ['success' => true];
        } else {
            return ['success' => false, 'error' => 'Job could not be cancelled'];
        }
    } catch (Exception $e) {
        error_log("Error cancelling job in MongoDB: " . $e->getMessage());
        return ['success' => false, 'error' => $e->getMessage()];
    }
}
?>

