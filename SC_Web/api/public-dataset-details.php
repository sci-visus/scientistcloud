<?php
/**
 * Public Dataset Details API Endpoint
 * Returns detailed information about a public dataset (no authentication required)
 */

// Start output buffering IMMEDIATELY to catch any output from included files
if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

// Disable error display to prevent output
ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);

// Start session (for any session-based features, but no auth required)
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');
require_once(__DIR__ . '/../includes/sclib_client.php');
require_once(__DIR__ . '/../includes/url_redact.php');

try {
    // Get dataset ID from request
    $datasetId = $_GET['dataset_id'] ?? null;
    if (!$datasetId) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset ID is required']);
        exit;
    }

    // Use SCLib API to get public dataset details
    $sclib = getSCLibClient();
    
    try {
        $sclibResponse = $sclib->makeRequest("/api/v1/datasets/public/{$datasetId}", 'GET');
        
        if (isset($sclibResponse['success']) && $sclibResponse['success']) {
            $dataset = $sclibResponse['dataset'] ?? null;
            
            if (!$dataset) {
                ob_end_clean();
                http_response_code(404);
                echo json_encode(['success' => false, 'error' => 'Dataset not found']);
                exit;
            }
            
            // Format dataset using formatDataset function for consistency
            try {
                $formattedDataset = formatDataset($dataset);
            } catch (Exception $e) {
                logMessage('ERROR', 'Failed to format dataset', [
                    'dataset_uuid' => $dataset['uuid'] ?? 'unknown',
                    'error' => $e->getMessage()
                ]);
                // Use dataset as-is if formatting fails
                $formattedDataset = $dataset;
            }
            
            // Remove sensitive user information (should already be removed by SCLib, but ensure it)
            unset($formattedDataset['user_id']);
            unset($formattedDataset['user']);
            unset($formattedDataset['user_email']);
            unset($formattedDataset['shared_with']);
            unset($formattedDataset['team_id']);

            $formattedDataset = sc_redact_dataset_urls_for_client($formattedDataset);

            require_once(__DIR__ . '/../includes/public_s3_dataset.php');
            $datasetUuid = (string) ($formattedDataset['uuid'] ?? $formattedDataset['id'] ?? '');
            if ($datasetUuid !== '') {
                $formattedDataset['public_portal_url'] = public_s3_portal_share_url($datasetUuid);
                [$isRemoteLinked] = public_s3_dataset_is_remote_linked($formattedDataset);
                $serverFlag = strtolower(trim((string) ($formattedDataset['server'] ?? ''))) === 'true';
                if ($isRemoteLinked || $serverFlag) {
                    $formattedDataset['has_s3_browser'] = true;
                    $formattedDataset['public_s3_browse_url'] = public_s3_browser_share_url($datasetUuid);
                } else {
                    $formattedDataset['has_s3_browser'] = false;
                }
            }
            
            $response = [
                'success' => true,
                'dataset' => $formattedDataset
            ];
            
        } else {
            $errorMsg = $sclibResponse['detail'] ?? $sclibResponse['error'] ?? 'Failed to get dataset';
            $statusCode = 404;
            if (strpos($errorMsg, 'not public') !== false || strpos($errorMsg, '403') !== false) {
                $statusCode = 403;
            }
            
            ob_end_clean();
            http_response_code($statusCode);
            echo json_encode(['success' => false, 'error' => $errorMsg]);
            exit;
        }
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get public dataset from SCLib', [
            'dataset_id' => $datasetId,
            'error' => $e->getMessage()
        ]);
        
        ob_end_clean();
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Internal server error',
            'message' => $e->getMessage()
        ]);
        exit;
    }

    // Clean output buffer and send response
    ob_end_clean();
    echo json_encode($response, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get public dataset details', ['dataset_id' => $datasetId ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
}
?>

