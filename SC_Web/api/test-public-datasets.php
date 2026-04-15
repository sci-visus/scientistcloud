<?php
/**
 * Test endpoint to debug public datasets query via SCLib
 * Access at: /portal/api/test-public-datasets.php
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

header('Content-Type: application/json');

try {
    $sclib = getSCLibClient();
    
    // Test SCLib connection
    $healthCheck = false;
    try {
        $healthResponse = $sclib->makeRequest('/health', 'GET');
        $healthCheck = isset($healthResponse['status']) && $healthResponse['status'] === 'healthy';
    } catch (Exception $e) {
        $healthError = $e->getMessage();
    }
    
    // Get public datasets from SCLib
    $publicDatasetsResponse = null;
    $publicDatasetsError = null;
    try {
        $publicDatasetsResponse = $sclib->makeRequest('/api/v1/datasets/public', 'GET');
    } catch (Exception $e) {
        $publicDatasetsError = $e->getMessage();
    }
    
    // Get API base URL info
    $apiUrl = getenv('SCLIB_DATASET_URL') ?: getenv('SCLIB_API_URL') ?: 'http://localhost:5001';
    if (file_exists('/.dockerenv') || getenv('DOCKER_CONTAINER')) {
        $apiUrl = getenv('SCLIB_DATASET_URL') ?: getenv('SCLIB_API_URL') ?: 'http://sclib_fastapi:5001';
    }
    
    $result = [
        'success' => true,
        'sclib_api_url' => $apiUrl,
        'health_check' => [
            'status' => $healthCheck ? 'healthy' : 'unhealthy',
            'error' => $healthError ?? null
        ],
        'public_datasets_api' => [
            'endpoint' => '/api/v1/datasets/public',
            'status' => $publicDatasetsResponse ? 'success' : 'failed',
            'error' => $publicDatasetsError ?? null,
            'response' => $publicDatasetsResponse
        ]
    ];
    
    if ($publicDatasetsResponse) {
        $datasets = $publicDatasetsResponse['datasets'] ?? [];
        $result['stats'] = [
            'total_public_datasets' => count($datasets),
            'folders_count' => count($publicDatasetsResponse['folders'] ?? []),
            'total_size' => $publicDatasetsResponse['stats']['total_size'] ?? 0
        ];
        
        if (count($datasets) > 0) {
            $result['sample_datasets'] = array_map(function($ds) {
                return [
                    'name' => $ds['name'] ?? 'N/A',
                    'uuid' => $ds['uuid'] ?? 'N/A',
                    'is_public' => $ds['is_public'] ?? 'N/A',
                    'is_downloadable' => $ds['is_downloadable'] ?? 'N/A',
                    'status' => $ds['status'] ?? 'N/A'
                ];
            }, array_slice($datasets, 0, 5));
        }
    }
    
    echo json_encode($result, JSON_PRETTY_PRINT);
    
} catch (Exception $e) {
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage(),
        'trace' => $e->getTraceAsString()
    ], JSON_PRETTY_PRINT);
}
?>

