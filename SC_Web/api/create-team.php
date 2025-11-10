<?php
/**
 * Create Team API Endpoint
 * Creates a new team using the SCLib Sharing and Team API
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
header('Access-Control-Allow-Methods: POST, OPTIONS');
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

    $user = getCurrentUser();
    if (!$user) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'User not authenticated']);
        exit;
    }

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    $teamName = $input['team_name'] ?? null;
    $emails = $input['emails'] ?? [];
    $ownerEmail = $input['owner_email'] ?? $user['email'];
    
    if (!$teamName) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Team name is required']);
        exit;
    }

    // Create team using SCLib Sharing and Team API
    $sharingClient = getSCLibSharingClient();
    $result = $sharingClient->createTeam($teamName, $ownerEmail, $emails);
    
    if ($result['success'] ?? false) {
        logMessage('INFO', 'Team created successfully', [
            'team_name' => $teamName,
            'owner_email' => $ownerEmail,
            'user_email' => $user['email']
        ]);
        
        ob_end_clean();
        echo json_encode([
            'success' => true,
            'message' => 'Team created successfully',
            'team' => $result['team'] ?? null
        ]);
    } else {
        ob_end_clean();
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => $result['error'] ?? 'Failed to create team'
        ]);
    }

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to create team', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

