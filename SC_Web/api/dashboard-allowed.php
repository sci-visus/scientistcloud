<?php
/**
 * Whether the signed-in user may open a dashboard.
 * Teams with no workflow assignment are allowed.
 */

if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

ini_set('display_errors', 0);
error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED);

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/portal_admin_store.php');

try {
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'allowed' => false, 'error' => 'Authentication required']);
        exit;
    }
    $user = getCurrentUser();
    $email = strtolower(trim((string) ($user['email'] ?? '')));
    if ($email === '') {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'allowed' => false, 'error' => 'User not authenticated']);
        exit;
    }
    $dashboardId = trim((string) ($_GET['dashboard_id'] ?? ''));
    $teamUuid = trim((string) ($_GET['team_uuid'] ?? ''));
    $result = portal_mongo_call([
        'op' => 'dashboard_allowed',
        'user_email' => $email,
        'dashboard_id' => $dashboardId,
        'team_uuid' => $teamUuid,
    ]);
    ob_end_clean();
    echo json_encode([
        'success' => true,
        'allowed' => !empty($result['allowed']),
        'reason' => $result['reason'] ?? '',
    ]);
} catch (Exception $e) {
    ob_end_clean();
    http_response_code(500);
    echo json_encode(['success' => false, 'allowed' => true, 'error' => $e->getMessage()]);
}
