<?php
/**
 * Get Public Folders and Teams API Endpoint
 * Returns folders and teams that have public datasets for the current user
 */

if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');

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

    // Get user's datasets to extract folders and teams with public datasets
    $sclib = getSCLibClient();
    
    // Get all user's datasets
    $response = null;
    try {
        $response = $sclib->makeRequest('/api/v1/datasets/by-user', 'GET', null, ['user_email' => $user['email']]);
    } catch (Exception $e) {
        logMessage('WARNING', 'by-user endpoint failed, trying regular endpoint', ['error' => $e->getMessage()]);
        try {
            $response = $sclib->makeRequest('/api/v1/datasets', 'GET', null, ['user_email' => $user['email']]);
        } catch (Exception $e2) {
            logMessage('ERROR', 'Failed to get datasets', ['error' => $e2->getMessage()]);
            throw $e2;
        }
    }
    
    $folders = [];
    $teams = [];
    $folderSet = [];
    $teamSet = [];
    $datasets = [];
    
    // Handle different response formats
    if (isset($response['success']) && $response['success']) {
        if (isset($response['datasets']['my'])) {
            // Format from by-user endpoint - check all categories
            $datasets = array_merge(
                $response['datasets']['my'] ?? [],
                $response['datasets']['shared'] ?? [],
                $response['datasets']['team'] ?? []
            );
        } elseif (isset($response['datasets']) && is_array($response['datasets'])) {
            // Format from regular endpoint (array of datasets)
            $datasets = $response['datasets'];
        }
    } elseif (isset($response['datasets']) && is_array($response['datasets'])) {
        // Response might not have success field
        $datasets = $response['datasets'];
    }
    
    // Extract folders and teams that have public datasets
    foreach ($datasets as $dataset) {
        $isPublic = $dataset['is_public'] ?? false;
        if (!$isPublic) continue; // Only include public datasets
        
        // Extract folder
        $folderUuid = $dataset['folder_uuid'] ?? $dataset['metadata']['folder_uuid'] ?? $dataset['folder'] ?? '';
        if ($folderUuid && $folderUuid !== '' && $folderUuid !== 'No_Folder_Selected' && !in_array($folderUuid, $folderSet)) {
            $folderSet[] = $folderUuid;
            $folders[] = [
                'uuid' => $folderUuid,
                'name' => $folderUuid
            ];
        }
        
        // Extract team
        $teamUuid = $dataset['team_uuid'] ?? '';
        if ($teamUuid && $teamUuid !== '' && !in_array($teamUuid, $teamSet)) {
            $teamSet[] = $teamUuid;
            $teams[] = [
                'uuid' => $teamUuid,
                'name' => $teamUuid
            ];
        }
    }
    
    ob_end_clean();
    echo json_encode([
        'success' => true,
        'folders' => $folders,
        'teams' => $teams
    ]);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get public folders and teams', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

