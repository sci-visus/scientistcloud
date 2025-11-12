<?php
/**
 * Jobs API Endpoint
 * Returns list of jobs for the current user
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
header('Access-Control-Allow-Methods: GET, OPTIONS');
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

    $userEmail = $user['email'];
    
    // Get query parameters
    $status = $_GET['status'] ?? null;
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    $offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;

    // Get jobs from MongoDB (FastAPI jobs endpoint may not be available)
    // This is more reliable for now
    $jobs = getJobsFromMongoDB($userEmail, $status, $limit, $offset);

    // Also get conversion jobs from job queue
    try {
        $conversionJobs = getConversionJobs($userEmail, $limit);
        // Merge conversion jobs with upload jobs
        $jobs = array_merge($jobs, $conversionJobs);
    } catch (Exception $e) {
        error_log("Error getting conversion jobs: " . $e->getMessage());
    }

    // Sort by created_at (most recent first)
    usort($jobs, function($a, $b) {
        $timeA = isset($a['created_at']) ? strtotime($a['created_at']) : 0;
        $timeB = isset($b['created_at']) ? strtotime($b['created_at']) : 0;
        return $timeB - $timeA;
    });

    ob_end_clean();
    echo json_encode([
        'success' => true,
        'jobs' => $jobs,
        'total' => count($jobs)
    ]);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get jobs', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    exit;
} catch (Error $e) {
    ob_end_clean();
    logMessage('ERROR', 'Fatal error getting jobs', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => 'A fatal error occurred while getting jobs'
    ]);
    exit;
}

/**
 * Get jobs from MongoDB directly (fallback)
 */
function getJobsFromMongoDB($userEmail, $status = null, $limit = 50, $offset = 0) {
    try {
        // Get MongoDB connection from config
        $mongo_url = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: 'mongodb://localhost:27017');
        $db_name = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
        
        // Check if MongoDB extension is available
        if (!class_exists('MongoDB\Client')) {
            error_log("MongoDB PHP extension not available");
            return [];
        }
        
        // Use MongoDB PHP extension
        $mongo_client = new MongoDB\Client($mongo_url);
        $db = $mongo_client->selectDatabase($db_name);
        $jobs_collection = $db->selectCollection('jobs');
        
        $query = ['user_email' => $userEmail];
        if ($status) {
            $query['status'] = $status;
        }
        
        $jobs = $jobs_collection->find($query)
            ->sort(['created_at' => -1])
            ->limit($limit)
            ->skip($offset)
            ->toArray();
        
        // Convert MongoDB documents to arrays
        $result = [];
        foreach ($jobs as $job) {
            $result[] = [
                'job_id' => $job['job_id'] ?? null,
                'id' => $job['job_id'] ?? null,
                'job_type' => $job['job_type'] ?? 'unknown',
                'status' => $job['status'] ?? 'unknown',
                'dataset_uuid' => $job['dataset_uuid'] ?? null,
                'dataset_name' => $job['dataset_name'] ?? null,
                'created_at' => isset($job['created_at']) ? $job['created_at']->toDateTime()->format('c') : null,
                'updated_at' => isset($job['updated_at']) ? $job['updated_at']->toDateTime()->format('c') : null,
                'completed_at' => isset($job['completed_at']) ? $job['completed_at']->toDateTime()->format('c') : null,
                'progress_percentage' => $job['progress_percentage'] ?? 0,
                'error' => $job['error'] ?? null
            ];
        }
        
        return $result;
    } catch (Exception $e) {
        error_log("Error getting jobs from MongoDB: " . $e->getMessage());
        return [];
    }
}

/**
 * Get conversion jobs from job queue
 */
function getConversionJobs($userEmail, $limit = 50) {
    try {
        // Get MongoDB connection from config
        $mongo_url = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: 'mongodb://localhost:27017');
        $db_name = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
        
        // Check if MongoDB extension is available
        if (!class_exists('MongoDB\Client')) {
            error_log("MongoDB PHP extension not available");
            return [];
        }
        
        // Use MongoDB PHP extension
        $mongo_client = new MongoDB\Client($mongo_url);
        $db = $mongo_client->selectDatabase($db_name);
        $jobs_collection = $db->selectCollection('jobs');
        $datasets_collection = $db->selectCollection('visstoredatas');
        
        // Get conversion jobs for datasets owned by this user
        $userDatasets = $datasets_collection->find(['user_id' => $userEmail])->toArray();
        $datasetUuids = array_map(function($ds) {
            return $ds['uuid'] ?? null;
        }, $userDatasets);
        $datasetUuids = array_filter($datasetUuids);
        
        if (empty($datasetUuids)) {
            return [];
        }
        
        $conversionJobs = $jobs_collection->find([
            'job_type' => 'dataset_conversion',
            'dataset_uuid' => ['$in' => array_values($datasetUuids)]
        ])
        ->sort(['created_at' => -1])
        ->limit($limit)
        ->toArray();
        
        $result = [];
        foreach ($conversionJobs as $job) {
            $result[] = [
                'job_id' => $job['job_id'] ?? null,
                'id' => $job['job_id'] ?? null,
                'job_type' => 'dataset_conversion',
                'status' => $job['status'] ?? 'unknown',
                'dataset_uuid' => $job['dataset_uuid'] ?? null,
                'created_at' => isset($job['created_at']) ? $job['created_at']->toDateTime()->format('c') : null,
                'updated_at' => isset($job['updated_at']) ? $job['updated_at']->toDateTime()->format('c') : null,
                'completed_at' => isset($job['completed_at']) ? $job['completed_at']->toDateTime()->format('c') : null,
                'progress_percentage' => $job['progress_percentage'] ?? 0,
                'error' => $job['error'] ?? null
            ];
        }
        
        return $result;
    } catch (Exception $e) {
        error_log("Error getting conversion jobs: " . $e->getMessage());
        return [];
    }
}
?>

