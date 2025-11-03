<?php
/**
 * Datasets API Endpoint
 * Returns user's datasets in JSON format
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

try {
    // Check authentication
    if (!isAuthenticated()) {
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    $user = getCurrentUser();
    if (!$user) {
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User not found']);
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

    echo json_encode($response);

} catch (Exception $e) {
    logMessage('ERROR', 'Failed to get datasets', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>
