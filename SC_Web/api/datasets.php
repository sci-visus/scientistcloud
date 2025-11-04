<?php
/**
 * Datasets API Endpoint
 * Returns user's datasets in JSON format
 */

// Clean any existing output buffers
while (ob_get_level()) {
    ob_end_clean();
}

// Start fresh output buffering to prevent any output before JSON
ob_start();

// Set headers before any output
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    ob_end_clean(); // Clear any output
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        ob_end_flush();
        exit;
    }

    $user = getCurrentUser();
    if (!$user) {
        ob_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User not found']);
        ob_end_flush();
        exit;
    }

    // Get all datasets by email (my, shared, team) - queries MongoDB directly
    // Similar to old portal's getFullDatasets() function
    $allDatasets = getAllDatasetsByEmail($user['email']);
    
    // Extract folders from datasets
    $folders = [];
    $folderCounts = [];
    
    foreach ($allDatasets['my'] as $dataset) {
        $folderUuid = $dataset['folder_uuid'] ?: 'root';
        if (!isset($folderCounts[$folderUuid])) {
            $folderCounts[$folderUuid] = 0;
        }
        $folderCounts[$folderUuid]++;
    }
    
    foreach ($folderCounts as $folderUuid => $count) {
        $folders[] = [
            'uuid' => $folderUuid,
            'name' => $folderUuid === 'root' ? 'Root' : $folderUuid,
            'count' => $count
        ];
    }
    
    // Calculate stats
    $totalDatasets = count($allDatasets['my']) + count($allDatasets['shared']) + count($allDatasets['team']);
    $totalSize = 0;
    $statusCounts = [];
    
    foreach (array_merge($allDatasets['my'], $allDatasets['shared'], $allDatasets['team']) as $dataset) {
        $totalSize += $dataset['data_size'] ?? 0;
        $status = $dataset['status'] ?? 'unknown';
        $statusCounts[$status] = ($statusCounts[$status] ?? 0) + 1;
    }
    
    $stats = [
        'total_datasets' => $totalDatasets,
        'total_size' => $totalSize,
        'status_counts' => $statusCounts,
        'my_datasets_count' => count($allDatasets['my']),
        'shared_datasets_count' => count($allDatasets['shared']),
        'team_datasets_count' => count($allDatasets['team'])
    ];

    // Format response
    $response = [
        'success' => true,
        'datasets' => [
            'my' => $allDatasets['my'],
            'shared' => $allDatasets['shared'],
            'team' => $allDatasets['team']
        ],
        'folders' => $folders,
        'stats' => $stats,
        'user' => [
            'id' => $user['id'],
            'name' => $user['name'],
            'email' => $user['email']
        ]
    ];

    // Get any output that might have been generated (for debugging)
    $output = ob_get_contents();
    if (!empty($output) && trim($output) !== '') {
        // Log unexpected output for debugging
        error_log("Unexpected output before JSON in datasets.php: " . substr($output, 0, 200));
        // Clear it
        ob_clean();
    }
    
    // Output JSON with clean buffer
    $json = json_encode($response);
    
    // Ensure no output before JSON
    ob_clean();
    
    // Output JSON
    echo $json;
    
    // Flush and end output buffering
    ob_end_flush();
    exit;

} catch (Exception $e) {
    logMessage('ERROR', 'Failed to get datasets', ['error' => $e->getMessage()]);
    
    // Clear any output buffer
    ob_clean();
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    
    // Flush and end output buffering
    ob_end_flush();
    exit;
}
