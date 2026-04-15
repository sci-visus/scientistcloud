<?php
/**
 * User Info API Endpoint
 * Returns current user information
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

    ob_end_clean();
    echo json_encode([
        'success' => true,
        'user' => [
            'email' => $user['email'] ?? '',
            'id' => $user['id'] ?? '',
            'name' => $user['name'] ?? '',
            'team_id' => $user['team_id'] ?? null
        ],
        'email' => $user['email'] ?? '',  // Keep for backward compatibility
        'id' => $user['id'] ?? '',  // Keep for backward compatibility
        'name' => $user['name'] ?? '',  // Keep for backward compatibility
        'team_id' => $user['team_id'] ?? null  // Keep for backward compatibility
    ]);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get user info', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

