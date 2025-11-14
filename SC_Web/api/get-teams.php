<?php
/**
 * Get Teams API Endpoint
 * Returns teams for the current user
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

    // Get teams for user using SCLib Sharing and Team API
    try {
        $sharingClient = getSCLibSharingClient();
        if (!$sharingClient) {
            throw new Exception('Failed to initialize sharing client');
        }
        
        $result = $sharingClient->getUserTeams($user['email']);
        
        // Log for debugging
        logMessage('DEBUG', 'Get teams API response', [
            'user_email' => $user['email'],
            'result' => $result
        ]);
        
        // Ensure result has the expected format
        if (!isset($result['success'])) {
            // If result doesn't have success field, wrap it
            $result = [
                'success' => true,
                'teams' => $result['teams'] ?? $result ?? []
            ];
        }
        
        // Ensure teams array exists
        if (!isset($result['teams'])) {
            $result['teams'] = [];
        }
        
        ob_end_clean();
        echo json_encode($result);
    } catch (Exception $apiException) {
        // Exception from API client (connection error, etc.)
        logMessage('ERROR', 'Get teams API call failed', [
            'user_email' => $user['email'],
            'error' => $apiException->getMessage(),
            'trace' => $apiException->getTraceAsString()
        ]);
        
        ob_end_clean();
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to connect to teams API: ' . $apiException->getMessage(),
            'teams' => []
        ]);
        exit;
    }

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get teams', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

