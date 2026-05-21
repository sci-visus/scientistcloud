<?php
/**
 * Get dataset dimension for smart dashboard selection.
 * Uses SCLib via dataset_manager (no direct MongoDB).
 */

if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);

require_once __DIR__ . '/../includes/session_cookie_params.php';
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

header('Content-Type: application/json');

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/dataset_manager.php';

/**
 * Parse "3D", "4D", or numeric dimension from dataset metadata.
 */
function sc_parse_dimension_from_dataset(array $dataset): ?int {
    if (isset($dataset['dimension']) && is_numeric($dataset['dimension'])) {
        $d = (int) $dataset['dimension'];
        return ($d >= 1 && $d <= 4) ? $d : null;
    }

    $raw = trim((string) ($dataset['dimensions'] ?? ''));
    if ($raw === '') {
        return null;
    }
    if (is_numeric($raw)) {
        $d = (int) $raw;
        return ($d >= 1 && $d <= 4) ? $d : null;
    }
    if (preg_match('/(\d)\s*D/i', $raw, $m)) {
        return (int) $m[1];
    }
    return null;
}

try {
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    $uuid = trim((string) ($_GET['uuid'] ?? ''));
    if ($uuid === '') {
        ob_end_clean();
        echo json_encode(['success' => false, 'error' => 'UUID parameter required']);
        exit;
    }

    $dataset = getDatasetByUuid($uuid);
    if (!$dataset) {
        ob_end_clean();
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    $dimension = sc_parse_dimension_from_dataset($dataset);
    ob_end_clean();

    if ($dimension !== null) {
        echo json_encode(['success' => true, 'dimension' => $dimension]);
    } else {
        echo json_encode([
            'success' => false,
            'error' => 'Could not determine dimension',
            'dimension' => null,
        ]);
    }
} catch (Throwable $e) {
    ob_end_clean();
    error_log('get_dataset_dimension.php: ' . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
