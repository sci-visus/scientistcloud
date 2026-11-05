<?php
/**
 * Signed-in viewer usage.
 * POST records a stay (start, dashboard, heartbeat, end). Identity comes from the session.
 * GET is portal-admin only.
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
require_once(__DIR__ . '/../includes/portal_admin_store.php');

function usage_json(int $code, array $payload): void {
    ob_end_clean();
    http_response_code($code);
    echo json_encode($payload);
    exit;
}

try {
    if (!isAuthenticated()) {
        usage_json(401, ['success' => false, 'error' => 'Authentication required']);
    }
    $user = getCurrentUser();
    $email = strtolower(trim((string) ($user['email'] ?? '')));
    if ($email === '') {
        usage_json(401, ['success' => false, 'error' => 'User not authenticated']);
    }

    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        if (!isPortalAdmin($email)) {
            usage_json(403, ['success' => false, 'error' => 'Administrator access required']);
        }
        $result = portal_mongo_call([
            'op' => 'usage_query',
            'user_email' => trim((string) ($_GET['user_email'] ?? '')),
            'dataset' => trim((string) ($_GET['dataset'] ?? '')),
            'dashboard' => trim((string) ($_GET['dashboard'] ?? '')),
            'from' => trim((string) ($_GET['from'] ?? '')),
            'to' => trim((string) ($_GET['to'] ?? '')),
            'limit' => $_GET['limit'] ?? 100,
        ]);
        usage_json(200, ['success' => true] + $result);
    }

    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        usage_json(405, ['success' => false, 'error' => 'Method not allowed']);
    }

    $body = json_decode(file_get_contents('php://input') ?: '', true);
    if (!is_array($body)) {
        usage_json(400, ['success' => false, 'error' => 'Invalid JSON body']);
    }
    $action = $body['action'] ?? '';
    $map = [
        'start' => 'usage_start',
        'dashboard' => 'usage_dashboard',
        'heartbeat' => 'usage_heartbeat',
        'end' => 'usage_end',
    ];
    if (!isset($map[$action])) {
        usage_json(400, ['success' => false, 'error' => 'Unknown action']);
    }
    $result = portal_mongo_call([
        'op' => $map[$action],
        'user_email' => $email,
        'stay_id' => $body['stay_id'] ?? '',
        'dataset_id' => $body['dataset_id'] ?? '',
        'dataset_uuid' => $body['dataset_uuid'] ?? '',
        'dataset_name' => $body['dataset_name'] ?? '',
        'dashboard_id' => $body['dashboard_id'] ?? '',
        'load_ms' => $body['load_ms'] ?? null,
    ]);
    usage_json(200, ['success' => true] + $result);
} catch (Exception $e) {
    usage_json(500, ['success' => false, 'error' => $e->getMessage()]);
}
