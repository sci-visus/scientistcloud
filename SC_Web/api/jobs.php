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
    $isAdmin = isPortalAdmin($userEmail);

    $status = $_GET['status'] ?? null;
    $limit = isset($_GET['limit']) ? max(1, min(intval($_GET['limit']), 200)) : 50;
    $offset = isset($_GET['offset']) ? max(0, intval($_GET['offset'])) : 0;
    $scope = $_GET['scope'] ?? 'active';
    $adminView = $isAdmin && isset($_GET['admin']) && $_GET['admin'] === '1';
    $filterUser = $adminView ? trim((string) ($_GET['user_email'] ?? '')) : '';

    $jobs = [];
    try {
        if ($adminView) {
            $jobs = getAdminPortalJobs($filterUser, $scope, $limit);
        } else {
            $jobs = getUserPortalJobs($userEmail, $scope, $limit, $status);
        }
        $mongoJobs = getJobsFromMongoDB($adminView && $filterUser !== '' ? $filterUser : $userEmail, $status, $limit, $offset);
        $jobs = mergePortalJobs($jobs, $mongoJobs);
    } catch (Exception $e) {
        error_log("Error getting jobs: " . $e->getMessage());
    }

    usort($jobs, function ($a, $b) {
        $timeA = isset($a['updated_at']) ? strtotime($a['updated_at']) : (isset($a['created_at']) ? strtotime($a['created_at']) : 0);
        $timeB = isset($b['updated_at']) ? strtotime($b['updated_at']) : (isset($b['created_at']) ? strtotime($b['created_at']) : 0);
        return $timeB - $timeA;
    });
    $jobs = array_slice($jobs, $offset, $limit);

    ob_end_clean();
    echo json_encode([
        'success' => true,
        'jobs' => $jobs,
        'total' => count($jobs),
        'is_admin' => $isAdmin,
        'admin_view' => $adminView,
        'scope' => $scope,
        'viewer_email' => $userEmail,
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
            // Map job status: 'pending' -> 'queued', 'running' -> 'processing'
            $jobStatus = $job['status'] ?? 'unknown';
            if ($jobStatus === 'pending') {
                $jobStatus = 'queued';
            } elseif ($jobStatus === 'running') {
                $jobStatus = 'processing';
            }
            
            $result[] = [
                'job_id' => $job['job_id'] ?? null,
                'id' => $job['job_id'] ?? null,
                'job_type' => $job['job_type'] ?? 'unknown',
                'status' => $jobStatus,
                'dataset_uuid' => $job['dataset_uuid'] ?? null,
                'dataset_name' => $job['dataset_name'] ?? null,
                'created_at' => isset($job['created_at']) ? (is_object($job['created_at']) ? $job['created_at']->toDateTime()->format('c') : $job['created_at']) : null,
                'updated_at' => isset($job['updated_at']) ? (is_object($job['updated_at']) ? $job['updated_at']->toDateTime()->format('c') : $job['updated_at']) : null,
                'completed_at' => isset($job['completed_at']) ? (is_object($job['completed_at']) ? $job['completed_at']->toDateTime()->format('c') : $job['completed_at']) : null,
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
        // Note: Dataset uses 'user' field (email), not 'user_id'
        $userDatasets = $datasets_collection->find([
            '$or' => [
                ['user' => $userEmail],  // Primary field name
                ['user_id' => $userEmail]  // Fallback for compatibility
            ]
        ])->toArray();
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
            // Map job status: 'pending' -> 'queued', 'running' -> 'processing'
            $jobStatus = $job['status'] ?? 'unknown';
            if ($jobStatus === 'pending') {
                $jobStatus = 'queued';
            } elseif ($jobStatus === 'running') {
                $jobStatus = 'processing';
            }
            
            $result[] = [
                'job_id' => $job['job_id'] ?? null,
                'id' => $job['job_id'] ?? null,
                'job_type' => 'dataset_conversion',
                'status' => $jobStatus,
                'dataset_uuid' => $job['dataset_uuid'] ?? null,
                'created_at' => isset($job['created_at']) ? (is_object($job['created_at']) ? $job['created_at']->toDateTime()->format('c') : $job['created_at']) : null,
                'updated_at' => isset($job['updated_at']) ? (is_object($job['updated_at']) ? $job['updated_at']->toDateTime()->format('c') : $job['updated_at']) : null,
                'completed_at' => isset($job['completed_at']) ? (is_object($job['completed_at']) ? $job['completed_at']->toDateTime()->format('c') : $job['completed_at']) : null,
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

/**
 * Get datasets with "conversion queued" status (jobs may not exist in jobs collection yet)
 */
function getQueuedConversionDatasets($userEmail, $limit = 50) {
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
        $datasets_collection = $db->selectCollection('visstoredatas');
        
        // Find datasets owned by user with "conversion queued" status
        // Note: Dataset uses 'user' field (email), not 'user_id'
        $datasets = $datasets_collection->find([
            '$or' => [
                ['user' => $userEmail],  // Primary field name
                ['user_id' => $userEmail]  // Fallback for compatibility
            ],
            'status' => ['$in' => ['conversion queued', 'converting']]
        ])
        ->sort(['created_at' => -1])
        ->limit($limit)
        ->toArray();
        
        return $datasets;
    } catch (Exception $e) {
        error_log("Error getting queued conversion datasets: " . $e->getMessage());
        return [];
    }
}

function portalJobActiveStatuses() {
    return ['uploading', 'processing', 'converting', 'conversion queued', 'queued', 'pending', 'running'];
}

function portalJobTerminalStatuses() {
    return ['done', 'completed', 'ready', 'uploaded', 'failed', 'error', 'conversion failed', 'cancelled', 'canceled'];
}

function formatMongoTimestamp($value) {
    if ($value === null || $value === '') {
        return null;
    }
    if (is_object($value) && method_exists($value, 'toDateTime')) {
        return $value->toDateTime()->format('c');
    }
    return is_string($value) ? $value : null;
}

function datasetOwnerEmail($dataset) {
    return $dataset['user'] ?? $dataset['user_email'] ?? $dataset['user_id'] ?? null;
}

function mapDatasetToPortalJob($dataset, $jobType = 'upload') {
    $state = $dataset['canonical_state'] ?? $dataset['status'] ?? 'unknown';
    $uuid = $dataset['uuid'] ?? null;
    $jobId = $dataset['job_id'] ?? null;
    if (!$jobId && $jobType === 'upload' && $uuid) {
        $jobId = 'upload_' . $uuid;
    }
    if (!$jobId && $uuid) {
        $jobId = 'dataset_' . $uuid;
    }
    $progress = $dataset['progress_percentage'] ?? $dataset['progress'] ?? 0;
    return [
        'job_id' => $jobId,
        'id' => $jobId,
        'job_type' => $jobType,
        'status' => $state,
        'canonical_state' => $state,
        'dataset_uuid' => $uuid,
        'dataset_name' => $dataset['name'] ?? 'Unnamed Dataset',
        'owner_email' => datasetOwnerEmail($dataset),
        'team_uuid' => $dataset['team_uuid'] ?? $dataset['team_id'] ?? null,
        'folder' => $dataset['folder'] ?? null,
        'sensor' => $dataset['sensor'] ?? null,
        'message' => $dataset['status_message'] ?? $dataset['message'] ?? null,
        'created_at' => formatMongoTimestamp($dataset['created_at'] ?? null),
        'updated_at' => formatMongoTimestamp($dataset['updated_at'] ?? null),
        'completed_at' => formatMongoTimestamp($dataset['completed_at'] ?? null),
        'progress_percentage' => is_numeric($progress) ? floatval($progress) : 0,
        'bytes_uploaded' => $dataset['bytes_uploaded'] ?? $dataset['total_size_bytes'] ?? null,
        'bytes_total' => $dataset['bytes_total'] ?? $dataset['total_size_bytes'] ?? null,
        'error' => $dataset['conversion_last_error'] ?? $dataset['error_message'] ?? $dataset['error'] ?? null,
    ];
}

function mergePortalJobs($primary, $secondary) {
    $seen = [];
    $merged = [];
    foreach (array_merge($primary, $secondary) as $job) {
        $key = ($job['job_id'] ?? '') . '|' . ($job['dataset_uuid'] ?? '');
        if ($key === '|' || isset($seen[$key])) {
            continue;
        }
        $seen[$key] = true;
        $merged[] = $job;
    }
    return $merged;
}

function getUserPortalJobs($userEmail, $scope = 'active', $limit = 50, $statusFilter = null) {
    $jobs = [];
    $statuses = portalJobActiveStatuses();
    if ($scope === 'all') {
        $statuses = array_values(array_unique(array_merge($statuses, portalJobTerminalStatuses())));
    }
    if ($statusFilter) {
        $statuses = [$statusFilter];
    }

    foreach (getQueuedConversionDatasets($userEmail, $limit) as $dataset) {
        $jobs[] = mapDatasetToPortalJob($dataset, 'dataset_conversion');
    }
    foreach (getQueuedUploadDatasets($userEmail, $limit) as $dataset) {
        $jobs[] = mapDatasetToPortalJob($dataset, 'upload');
    }
    foreach (getUserDatasetsByStatuses($userEmail, $statuses, $limit) as $dataset) {
        $jobType = ($dataset['status'] ?? '') === 'uploading' ? 'upload' : 'dataset_conversion';
        $jobs[] = mapDatasetToPortalJob($dataset, $jobType);
    }
    return $jobs;
}

function getAdminPortalJobs($filterUserEmail = '', $scope = 'active', $limit = 100) {
    $statuses = portalJobActiveStatuses();
    if ($scope === 'all') {
        $statuses = array_values(array_unique(array_merge($statuses, portalJobTerminalStatuses())));
    }
    return getDatasetsByStatuses($filterUserEmail, $statuses, $limit);
}

function getUserDatasetsByStatuses($userEmail, $statuses, $limit = 50) {
    $jobs = [];
    try {
        if (!class_exists('MongoDB\Client')) {
            return [];
        }
        $mongo_url = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: 'mongodb://localhost:27017');
        $db_name = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
        $mongo_client = new MongoDB\Client($mongo_url);
        $collection = $mongo_client->selectDatabase($db_name)->selectCollection('visstoredatas');
        $datasets = $collection->find([
            '$and' => [
                ['$or' => [['user' => $userEmail], ['user_id' => $userEmail], ['user_email' => $userEmail]]],
                ['status' => ['$in' => array_values($statuses)]],
            ],
        ])->sort(['updated_at' => -1])->limit($limit)->toArray();
        foreach ($datasets as $dataset) {
            $jobType = ($dataset['status'] ?? '') === 'uploading' ? 'upload' : 'dataset_conversion';
            $jobs[] = mapDatasetToPortalJob($dataset, $jobType);
        }
    } catch (Exception $e) {
        error_log('getUserDatasetsByStatuses: ' . $e->getMessage());
    }
    return $jobs;
}

function getDatasetsByStatuses($filterUserEmail, $statuses, $limit = 100) {
    $jobs = [];
    try {
        if (!class_exists('MongoDB\Client')) {
            return [];
        }
        $mongo_url = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: 'mongodb://localhost:27017');
        $db_name = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
        $mongo_client = new MongoDB\Client($mongo_url);
        $collection = $mongo_client->selectDatabase($db_name)->selectCollection('visstoredatas');
        $query = ['status' => ['$in' => array_values($statuses)]];
        if ($filterUserEmail !== '') {
            $query['$or'] = [
                ['user' => $filterUserEmail],
                ['user_id' => $filterUserEmail],
                ['user_email' => $filterUserEmail],
            ];
        }
        $datasets = $collection->find($query)->sort(['updated_at' => -1])->limit($limit)->toArray();
        foreach ($datasets as $dataset) {
            $jobType = ($dataset['status'] ?? '') === 'uploading' ? 'upload' : 'dataset_conversion';
            $jobs[] = mapDatasetToPortalJob($dataset, $jobType);
        }
    } catch (Exception $e) {
        error_log('getDatasetsByStatuses: ' . $e->getMessage());
    }
    return $jobs;
}

/**
 * Get datasets with "uploading" status (status-based upload jobs)
 */
function getQueuedUploadDatasets($userEmail, $limit = 50) {
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
        $datasets_collection = $db->selectCollection('visstoredatas');
        
        // Find datasets owned by user with "uploading" status
        // Note: Dataset uses 'user' field (email), not 'user_id'
        $datasets = $datasets_collection->find([
            '$or' => [
                ['user' => $userEmail],  // Primary field name
                ['user_id' => $userEmail]  // Fallback for compatibility
            ],
            'status' => 'uploading'
        ])
        ->sort(['created_at' => -1])
        ->limit($limit)
        ->toArray();
        
        return $datasets;
    } catch (Exception $e) {
        error_log("Error getting queued upload datasets: " . $e->getMessage());
        return [];
    }
}
?>

