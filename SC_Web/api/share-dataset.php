<?php
/**
 * Share Dataset API Endpoint
 * Shares a dataset with users or teams using SCLib Sharing API
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

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

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

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    $datasetUuid = $input['dataset_uuid'] ?? $input['dataset_id'] ?? null;
    $userEmail = $input['user_email'] ?? null;
    $teamName = $input['team_name'] ?? null;
    $teamUuid = $input['team_uuid'] ?? null;
    
    if (!$datasetUuid) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset UUID is required']);
        exit;
    }

    $user = getCurrentUser();
    if (!$user) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User not authenticated']);
        exit;
    }

    $ownerEmail = $user['email'];
    $googleDriveLink = $input['google_drive_link'] ?? '';

    // Get sharing client
    $sharingClient = getSCLibSharingClient();

    // Share with user or team
    if ($userEmail) {
        // Share with user
        $result = $sharingClient->shareDatasetWithUser($datasetUuid, $userEmail, $ownerEmail, $googleDriveLink);
    } elseif ($teamName) {
        // Share with team
        $result = $sharingClient->shareDatasetWithTeam($datasetUuid, $teamName, $ownerEmail, $teamUuid, $googleDriveLink);
    } else {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Either user_email or team_name is required']);
        exit;
    }
    
    ob_end_clean();
    echo json_encode($result);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to share dataset', ['dataset_uuid' => $datasetUuid ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>
