<?php
/**
 * Administrator dashboard data: resources, allocations, cost, access, workflows.
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

function admin_json(int $code, array $payload): void {
    ob_end_clean();
    http_response_code($code);
    echo json_encode($payload);
    exit;
}

try {
    if (!isAuthenticated()) {
        admin_json(401, ['success' => false, 'error' => 'Authentication required']);
    }
    $user = getCurrentUser();
    $email = strtolower(trim((string) ($user['email'] ?? '')));
    if ($email === '' || !isPortalAdmin($email)) {
        admin_json(403, ['success' => false, 'error' => 'Administrator access required']);
    }

    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $section = $_GET['section'] ?? 'resources';
        if ($section === 'resources') {
            $storage = portal_mongo_call(['op' => 'storage_summary']);
            admin_json(200, [
                'success' => true,
                'disk' => portal_disk_summary(),
                'users' => $storage['users'] ?? [],
                'teams' => $storage['teams'] ?? [],
            ]);
        }
        if ($section === 'allocations') {
            $listed = portal_mongo_call(['op' => 'allocations_list']);
            admin_json(200, ['success' => true, 'allocations' => $listed['allocations'] ?? []]);
        }
        if ($section === 'cost') {
            $month = trim((string) ($_GET['month'] ?? ''));
            if (!preg_match('/^\d{4}-\d{2}$/', $month)) {
                $month = gmdate('Y-m');
            }
            $from = $month . '-01T00:00:00+00:00';
            $end = (new DateTimeImmutable($from))->modify('first day of next month')->format('c');
            $report = portal_mongo_call([
                'op' => 'cost_report',
                'from' => $from,
                'to' => $end,
            ]);
            admin_json(200, ['success' => true, 'month' => $month] + $report);
        }
        if ($section === 'access') {
            $access = portal_mongo_call(['op' => 'access_summary']);
            admin_json(200, ['success' => true] + $access);
        }
        if ($section === 'workflows') {
            $flows = portal_mongo_call(['op' => 'workflows_list']);
            admin_json(200, [
                'success' => true,
                'dashboards' => portal_dashboard_catalog(),
                'teams' => $flows['teams'] ?? [],
                'workflows' => $flows['workflows'] ?? [],
            ]);
        }
        admin_json(400, ['success' => false, 'error' => 'Unknown section']);
    }

    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        admin_json(405, ['success' => false, 'error' => 'Method not allowed']);
    }

    $body = json_decode(file_get_contents('php://input') ?: '', true);
    if (!is_array($body)) {
        admin_json(400, ['success' => false, 'error' => 'Invalid JSON body']);
    }
    $action = $body['action'] ?? '';
    if ($action === 'save_allocation') {
        $saved = portal_mongo_call([
            'op' => 'allocation_save',
            'subject_type' => $body['subject_type'] ?? '',
            'subject_id' => $body['subject_id'] ?? '',
            'space_bytes' => $body['space_bytes'] ?? null,
            'seat_limit' => $body['seat_limit'] ?? null,
            'usd_per_gb_month' => $body['usd_per_gb_month'] ?? null,
            'usd_per_viewer_hour' => $body['usd_per_viewer_hour'] ?? null,
        ]);
        admin_json(200, ['success' => true] + $saved);
    }
    if ($action === 'save_workflows') {
        $saved = portal_mongo_call([
            'op' => 'workflow_save',
            'team_uuid' => $body['team_uuid'] ?? '',
            'restricted' => !empty($body['restricted']),
            'enabled' => $body['enabled'] ?? [],
        ]);
        admin_json(200, ['success' => true] + $saved);
    }
    admin_json(400, ['success' => false, 'error' => 'Unknown action']);
} catch (Exception $e) {
    admin_json(500, ['success' => false, 'error' => $e->getMessage()]);
}
