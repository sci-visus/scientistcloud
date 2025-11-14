<?php
/**
 * Conversion Logs API Endpoint
 * Returns conversion logs for a specific dataset
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
error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED);

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
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

    // Get dataset UUID from query parameter
    $datasetUuid = $_GET['dataset_uuid'] ?? null;
    if (!$datasetUuid) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'dataset_uuid parameter required']);
        exit;
    }

    // Verify user has access to this dataset
    require_once(__DIR__ . '/../includes/sclib_client.php');
    $sclib = getSCLibClient();
    $datasets = $sclib->getUserDatasets($user['id']);
    
    $hasAccess = false;
    foreach ($datasets as $dataset) {
        if (($dataset['uuid'] ?? $dataset['id'] ?? '') === $datasetUuid) {
            $hasAccess = true;
            break;
        }
    }
    
    if (!$hasAccess) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Access denied to this dataset']);
        exit;
    }

    // Get conversion logs from multiple sources
    $logs = '';
    $logSources = [];
    
    // 1. Try to get logs from converted directory (if conversion has started)
    $visusDatasets = getenv('VISUS_DATASETS') ?: '/mnt/visus_datasets';
    $convertedDir = $visusDatasets . '/converted/' . $datasetUuid;
    
    if (is_dir($convertedDir)) {
        // Check for conversion log files
        $logFiles = [
            $convertedDir . '/conversion.log',
            $convertedDir . '/convert.log',
            $convertedDir . '/~progress.txt',
            $convertedDir . '/run_conversion.log'
        ];
        
        foreach ($logFiles as $logFile) {
            if (file_exists($logFile) && is_readable($logFile)) {
                $fileContent = file_get_contents($logFile);
                if ($fileContent) {
                    // Get last 100 lines to avoid huge logs
                    $lines = explode("\n", $fileContent);
                    $recentLines = array_slice($lines, -100);
                    $logs .= "=== " . basename($logFile) . " (last 100 lines) ===\n" . implode("\n", $recentLines) . "\n\n";
                    $logSources[] = basename($logFile);
                }
            }
        }
    }
    
    // 2. Try to get logs from background service Docker container
    // This requires Docker to be accessible from PHP
    $dockerContainer = getenv('BACKGROUND_SERVICE_CONTAINER') ?: 'sclib_background_service';
    
    // Try to get recent logs from Docker (last 50 lines containing this dataset UUID)
    if (function_exists('shell_exec') && !empty(shell_exec('which docker'))) {
        $dockerLogs = @shell_exec("docker logs --tail 200 {$dockerContainer} 2>&1 | grep -i '{$datasetUuid}' | tail -50");
        if ($dockerLogs && !empty(trim($dockerLogs))) {
            $logs .= "=== Background Service Logs (Docker) ===\n" . trim($dockerLogs) . "\n\n";
            $logSources[] = 'docker_logs';
        }
    }
    
    // 3. If no logs found, provide helpful message
    if (empty($logs)) {
        $logs = "No conversion logs available yet.\n\n";
        $logs .= "The conversion may still be in progress or hasn't started yet.\n";
        $logs .= "Status: Check the job status above for current state.\n\n";
        $logs .= "To view background service logs manually:\n";
        $logs .= "  docker logs {$dockerContainer} | grep {$datasetUuid}\n\n";
        $logs .= "Or check the converted directory:\n";
        $logs .= "  {$convertedDir}";
    }
    
    ob_end_clean();
    echo json_encode([
        'success' => true,
        'logs' => $logs,
        'sources' => $logSources
    ]);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get conversion logs', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
    exit;
} catch (Error $e) {
    ob_end_clean();
    logMessage('ERROR', 'Fatal error getting conversion logs', ['error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => 'A fatal error occurred while getting conversion logs'
    ]);
    exit;
}
?>

