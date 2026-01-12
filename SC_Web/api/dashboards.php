<?php
/**
 * Dashboards API Endpoint
 * Returns list of available dashboards from dashboards-list.json
 */

// Set error handler to catch any PHP errors/warnings
set_error_handler(function($errno, $errstr, $errfile, $errline) {
    error_log("PHP Error in dashboards.php: [$errno] $errstr in $errfile:$errline");
    // Don't output error to response, just log it
    return true;
}, E_ALL);

header('Content-Type: application/json');

// Start output buffering IMMEDIATELY to catch any output from included files
if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

// Enable error logging but don't display (to catch issues)
ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
ini_set('log_errors', 1);
error_reporting(E_ALL);

// Start session BEFORE including config.php to ensure session is available
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');

// Dashboards list is public - no authentication required
// Anyone can see what dashboards are available

// Path to dashboards-list.json
// Try multiple possible paths (container paths and host paths)
$possiblePaths = [
    // Mounted volume path (preferred)
    '/var/www/SC_Dashboards/config/dashboards-list.json',
    // Relative paths from SC_Web/api/ (inside container)
    __DIR__ . '/../../SC_Dashboards/config/dashboards-list.json',
    __DIR__ . '/../../../scientistcloud/SC_Dashboards/config/dashboards-list.json',
    // Server absolute paths (if SC_Dashboards is accessible from container)
    '/home/amy/ScientistCloud2.0/scientistcloud/SC_Dashboards/config/dashboards-list.json',
    '/home/amy/ScientistCloud_2.0/scientistcloud/SC_Dashboards/config/dashboards-list.json',
    getenv('HOME') . '/ScientistCloud2.0/scientistcloud/SC_Dashboards/config/dashboards-list.json',
    getenv('HOME') . '/ScientistCloud_2.0/scientistcloud/SC_Dashboards/config/dashboards-list.json',
];

$dashboardsListPath = null;
foreach ($possiblePaths as $path) {
    if (file_exists($path)) {
        $dashboardsListPath = $path;
        break;
    }
}

// Check if file exists
if (!$dashboardsListPath || !file_exists($dashboardsListPath)) {
    ob_end_clean();
    http_response_code(404);
    echo json_encode([
        'success' => false,
        'error' => 'Dashboards list not found',
        'dashboards' => [],
        'searched_paths' => $possiblePaths
    ]);
    exit;
}

// Read and parse JSON
$jsonContent = file_get_contents($dashboardsListPath);
if ($jsonContent === false) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Failed to read dashboards list file',
        'file_path' => $dashboardsListPath,
        'dashboards' => []
    ]);
    exit;
}

$dashboardsData = json_decode($jsonContent, true);

if (json_last_error() !== JSON_ERROR_NONE) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Failed to parse dashboards list: ' . json_last_error_msg(),
        'json_error_code' => json_last_error(),
        'file_path' => $dashboardsListPath,
        'file_size' => filesize($dashboardsListPath),
        'dashboards' => []
    ]);
    exit;
}

// Check if dashboards key exists
if (!isset($dashboardsData['dashboards']) || !is_array($dashboardsData['dashboards'])) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Invalid dashboards list format: missing or invalid "dashboards" array',
        'file_path' => $dashboardsListPath,
        'data_keys' => array_keys($dashboardsData),
        'dashboards' => []
    ]);
    exit;
}

// Clean output buffer and send response
ob_end_clean();

// Return only enabled dashboards
$allDashboards = $dashboardsData['dashboards'] ?? [];
$enabledDashboards = array_filter($allDashboards, function($dashboard) {
    return ($dashboard['enabled'] ?? false) === true;
});

// Re-index array
$enabledDashboards = array_values($enabledDashboards);

// Log for debugging
error_log("Dashboards API: Found " . count($allDashboards) . " total dashboards, " . count($enabledDashboards) . " enabled");

$response = [
    'success' => true,
    'dashboards' => $enabledDashboards,
    'total' => count($enabledDashboards),
    'total_all' => count($allDashboards),
    'version' => $dashboardsData['version'] ?? '1.0.0',
    'last_updated' => $dashboardsData['last_updated'] ?? null,
    'file_path' => $dashboardsListPath
];

echo json_encode($response, JSON_PRETTY_PRINT);