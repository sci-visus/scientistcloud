<?php
/**
 * Update Team Name API Endpoint
 * Updates only the team name using the SCLib Sharing and Team API
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
    $rawInput = file_get_contents('php://input');
    if (empty($rawInput)) {
        ob_end_clean();
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'No request data provided']);
        exit;
    }
    
    $input = json_decode($rawInput, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        ob_end_clean();
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Invalid JSON: ' . json_last_error_msg()]);
        exit;
    }
    
    $teamUuid = $input['team_uuid'] ?? $input['teamId'] ?? null;
    $newName = $input['team_name'] ?? $input['newName'] ?? null;
    
    if (!$teamUuid) {
        ob_end_clean();
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Team UUID is required']);
        exit;
    }
    
    if (!$newName || trim($newName) === '') {
        ob_end_clean();
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Team name is required']);
        exit;
    }

    // Update team name using SCLib Sharing and Team API
    try {
        $sharingClient = getSCLibSharingClient();
        if (!$sharingClient) {
            throw new Exception('Failed to initialize sharing client');
        }
        
        $result = $sharingClient->updateTeam($teamUuid, $user['email'], trim($newName), null, null);
        
        // Log the result for debugging
        logMessage('DEBUG', 'Team name update API response', [
            'team_uuid' => $teamUuid,
            'new_name' => $newName,
            'user_email' => $user['email'],
            'result' => $result
        ]);
        
        // Check if the API call was successful
        if (isset($result['success']) && $result['success'] === true) {
            logMessage('INFO', 'Team name updated successfully', [
                'team_uuid' => $teamUuid,
                'new_name' => $newName,
                'user_email' => $user['email']
            ]);
            
            ob_end_clean();
            echo json_encode([
                'success' => true,
                'message' => $result['message'] ?? 'Team name updated successfully',
                'team' => $result['team'] ?? null
            ]);
            exit;
        } else {
            // API returned an error
            $errorMessage = $result['error'] ?? $result['detail'] ?? $result['message'] ?? 'Failed to update team name';
            logMessage('ERROR', 'Team name update failed', [
                'team_uuid' => $teamUuid,
                'user_email' => $user['email'],
                'error' => $errorMessage,
                'api_response' => $result
            ]);
            
            ob_end_clean();
            http_response_code(500);
            echo json_encode([
                'success' => false,
                'error' => $errorMessage
            ]);
            exit;
        }
    } catch (Exception $apiException) {
        // Exception from API client (connection error, etc.)
        logMessage('ERROR', 'Team name update API call failed', [
            'team_uuid' => $teamUuid,
            'user_email' => $user['email'],
            'error' => $apiException->getMessage()
        ]);
        
        ob_end_clean();
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to connect to team API: ' . $apiException->getMessage()
        ]);
        exit;
    }

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to update team name', ['error' => $e->getMessage(), 'trace' => $e->getTraceAsString()]);
    
    http_response_code(500);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    exit;
}
?>

