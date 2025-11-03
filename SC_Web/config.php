<?php
/**
 * ScientistCloud Data Portal Configuration
 * Integrates with scientistCloudLib configuration
 */

// Set error reporting
// In production, don't display errors to prevent headers being sent
// Errors will still be logged, but won't output to browser
error_reporting(E_ALL);
// Only display errors if we're in a development environment
// Check for a DEV environment variable or set this appropriately for production
ini_set('display_errors', getenv('PHP_DISPLAY_ERRORS') === '1' ? 1 : 0);
ini_set('log_errors', 1);
ini_set('error_log', __DIR__ . '/logs/php_errors.log');

// Define paths
define('SC_WEB_ROOT', __DIR__);
define('SC_LIB_ROOT', '/var/www/scientistCloudLib');
define('SC_CONFIG_PATH', SC_LIB_ROOT . '/SCLib_JobProcessing');

// Include scientistCloudLib PHP files only
require_once(SC_CONFIG_PATH . '/SCLib_Config.php');

// Initialize configuration
try {
    $config = get_config();
    // No direct MongoDB connection needed - SCLib handles all database operations
} catch (Exception $e) {
    error_log("Configuration error: " . $e->getMessage());
    die("Configuration error. Please check your environment settings.");
}

// Database configuration - handled by SCLib API
define('DB_NAME', $config['database_name']);
define('MONGO_URL', $config['mongo_url']); // Not used directly - SCLib handles this

// Collection names
define('COLLECTION_DATASETS', get_collection_name('visstoredatas'));
define('COLLECTION_USERS', get_collection_name('user_profile'));
define('COLLECTION_TEAMS', get_collection_name('teams'));
define('COLLECTION_SHARED', get_collection_name('shared_user'));

// Server configuration
define('SC_SERVER_URL', $config['server']['deploy_server']);
define('SC_DOMAIN', $config['server']['domain_name']);

// Job processing configuration
$job_config = $config['job_processing'];
define('JOB_IN_DATA_DIR', $job_config['in_data_dir']);
define('JOB_OUT_DATA_DIR', $job_config['out_data_dir']);
define('JOB_SYNC_DATA_DIR', $job_config['sync_data_dir']);
define('JOB_AUTH_DATA_DIR', $job_config['auth_dir']);

// Authentication configuration
define('AUTH0_DOMAIN', $config['auth']['auth0_domain']);
define('AUTH0_CLIENT_ID', $config['auth']['auth0_client_id']);
define('AUTH0_CLIENT_SECRET', $config['auth']['auth0_client_secret']);

// Security settings
define('SECRET_KEY', $config['auth']['secret_key']);
define('SECRET_IV', $config['auth']['secret_iv']);

// Dashboard configuration
define('DEFAULT_DASHBOARD', 'openvisus');
define('SUPPORTED_DASHBOARDS', ['openvisus', 'bokeh', 'jupyter', 'plotly', 'vtk']);

// File upload settings
define('MAX_UPLOAD_SIZE', 500 * 1024 * 1024); // 500MB
define('ALLOWED_EXTENSIONS', ['tiff', 'tif', 'hdf5', 'nc', 'nexus', 'json', 'csv']);

// Viewer settings
define('VIEWER_TIMEOUT', 300); // 5 minutes
define('VIEWER_REFRESH_INTERVAL', 30); // 30 seconds

// Logging
define('LOG_LEVEL', 'INFO');
define('LOG_FILE', SC_WEB_ROOT . '/logs/app.log');

// Create logs directory if it doesn't exist
// Note: Suppress warnings to prevent "headers already sent" errors
if (!file_exists(dirname(LOG_FILE))) {
    @mkdir(dirname(LOG_FILE), 0775, true);
    @chmod(dirname(LOG_FILE), 0775);
}
// Ensure logs directory is writable (suppress errors if permission denied)
if (file_exists(dirname(LOG_FILE))) {
    // Try to make writable, but don't fail if permissions are restricted
    @chmod(dirname(LOG_FILE), 0777);
    // If chmod failed, at least ensure the directory exists and log it
    if (!is_writable(dirname(LOG_FILE))) {
        // Log to error_log instead of outputting warning
        error_log("Warning: Cannot set permissions on logs directory: " . dirname(LOG_FILE));
    }
}

// Helper functions - SCLib handles all database operations
function getMongoConnection() {
    // Deprecated - use SCLib API instead
    throw new Exception("Direct MongoDB access not supported. Use SCLib API instead.");
}

function getDatabaseName() {
    return DB_NAME;
}

function getCollectionName($type) {
    switch ($type) {
        case 'datasets':
            return COLLECTION_DATASETS;
        case 'users':
            return COLLECTION_USERS;
        case 'teams':
            return COLLECTION_TEAMS;
        case 'shared':
            return COLLECTION_SHARED;
        default:
            throw new Exception("Unknown collection type: $type");
    }
}

function logMessage($level, $message, $context = []) {
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$level] $message";
    
    if (!empty($context)) {
        $logEntry .= " " . json_encode($context);
    }
    
    $logEntry .= PHP_EOL;
    
    file_put_contents(LOG_FILE, $logEntry, FILE_APPEND | LOCK_EX);
}

function getConfig() {
    global $config;
    return $config;
}

// Initialize session
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// Set timezone
date_default_timezone_set('UTC');

// Set memory limit for large datasets
ini_set('memory_limit', '2G');
ini_set('max_execution_time', 300);

// CORS headers for API requests
if (isset($_SERVER['HTTP_ORIGIN'])) {
    header("Access-Control-Allow-Origin: {$_SERVER['HTTP_ORIGIN']}");
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Max-Age: 86400');
}

if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    if (isset($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_METHOD']))
        header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS");
    if (isset($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']))
        header("Access-Control-Allow-Headers: {$_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']}");
    exit(0);
}
?>
