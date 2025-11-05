<?php
/**
 * Dashboards API Endpoint
 * Returns list of available dashboards from dashboards-list.json
 */

header('Content-Type: application/json');

// Start output buffering IMMEDIATELY to catch any output from included files
if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

// Disable error display to prevent output
ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);

// Start session BEFORE including config.php to ensure session is available
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');

// Check authentication
$user = getCurrentUser();
if (!$user) {
    ob_end_clean();
    http_response_code(401);
    echo json_encode([
        'success' => false,
        'error' => 'Unauthorized'
    ]);
    exit;
}

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
if (!file_exists($dashboardsListPath)) {
    ob_end_clean();
    http_response_code(404);
    echo json_encode([
        'success' => false,
        'error' => 'Dashboards list not found',
        'dashboards' => []
    ]);
    exit;
}

// Read and parse JSON
$jsonContent = file_get_contents($dashboardsListPath);
$dashboardsData = json_decode($jsonContent, true);

if (json_last_error() !== JSON_ERROR_NONE) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Failed to parse dashboards list: ' . json_last_error_msg(),
        'dashboards' => []
    ]);
    exit;
}

// Clean output buffer and send response
ob_end_clean();

// Return only enabled dashboards
$enabledDashboards = array_filter($dashboardsData['dashboards'] ?? [], function($dashboard) {
    return ($dashboard['enabled'] ?? false) === true;
});

// Re-index array
$enabledDashboards = array_values($enabledDashboards);

echo json_encode([
    'success' => true,
    'dashboards' => $enabledDashboards,
    'total' => count($enabledDashboards),
    'version' => $dashboardsData['version'] ?? '1.0.0',
    'last_updated' => $dashboardsData['last_updated'] ?? null
]);