<?php
/**
 * Update Team API Endpoint
 * Updates a team using the SCLib Sharing and Team API
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
    $teamName = $input['team_name'] ?? $input['newName'] ?? null;
    $newMemberEmail = $input['new_member_email'] ?? $input['newMemberEmail'] ?? null;
    $emails = $input['emails'] ?? null;
    
    if (!$teamUuid) {
        ob_end_clean();
        http_response_code(400);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Team UUID is required']);
        exit;
    }

    // Get current team to add member to existing emails
    $sharingClient = getSCLibSharingClient();
    if (!$sharingClient) {
        throw new Exception('Failed to initialize sharing client');
    }
    
    // Get current team data
    $currentTeam = $sharingClient->makeRequest("/api/v1/teams/$teamUuid", 'GET', null, ['user_email' => $user['email']]);
    if (!isset($currentTeam['team'])) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Team not found']);
        exit;
    }
    
    $currentEmails = $currentTeam['team']['emails'] ?? [];
    
    // Prepare update data
    $updateData = [];
    
    if ($teamName !== null && trim($teamName) !== '') {
        $updateData['team_name'] = trim($teamName);
    }
    
    // Handle emails update
    if ($emails !== null) {
        // If emails array is provided, use it directly
        $updateData['emails'] = $emails;
    } elseif ($newMemberEmail !== null && trim($newMemberEmail) !== '') {
        // If new member email is provided, add it to existing emails
        $newEmail = trim($newMemberEmail);
        if (!in_array($newEmail, $currentEmails)) {
            $currentEmails[] = $newEmail;
        }
        $updateData['emails'] = $currentEmails;
    }
    
    if (empty($updateData)) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'No fields to update']);
        exit;
    }

    // Update team using SCLib Sharing and Team API
    try {
        $result = $sharingClient->updateTeam($teamUuid, $user['email'], 
            $updateData['team_name'] ?? null,
            $updateData['emails'] ?? null,
            null
        );
        
        // Log the result for debugging
        logMessage('DEBUG', 'Team update API response', [
            'team_uuid' => $teamUuid,
            'user_email' => $user['email'],
            'result' => $result
        ]);
        
        // Check if the API call was successful
        if (isset($result['success']) && $result['success'] === true) {
            logMessage('INFO', 'Team updated successfully', [
                'team_uuid' => $teamUuid,
                'user_email' => $user['email']
            ]);
            
            ob_end_clean();
            echo json_encode([
                'success' => true,
                'message' => $result['message'] ?? 'Team updated successfully',
                'team' => $result['team'] ?? null
            ]);
            exit;
        } else {
            // API returned an error
            $errorMessage = $result['error'] ?? $result['detail'] ?? $result['message'] ?? 'Failed to update team';
            logMessage('ERROR', 'Team update failed', [
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
        logMessage('ERROR', 'Team update API call failed', [
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
    logMessage('ERROR', 'Failed to update team', ['error' => $e->getMessage(), 'trace' => $e->getTraceAsString()]);
    
    http_response_code(500);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    exit;
} catch (Error $e) {
    ob_end_clean();
    logMessage('ERROR', 'Fatal error updating team', ['error' => $e->getMessage(), 'trace' => $e->getTraceAsString()]);
    
    http_response_code(500);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => false,
        'error' => 'Fatal error',
        'message' => $e->getMessage()
    ]);
    exit;
}
?>

