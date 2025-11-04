<?php
/**
 * Dataset Manager Module for ScientistCloud Data Portal
 * Delegates ALL operations to SCLib API - no direct MongoDB access
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/auth.php');
require_once(__DIR__ . '/sclib_client.php');

/**
 * Get user's datasets
 */
function getUserDatasets($userId) {
    try {
        $sclib = getSCLibClient();
        $datasets = $sclib->getUserDatasets($userId);
        
        // Format datasets for portal
        $formattedDatasets = [];
        foreach ($datasets as $dataset) {
            $formattedDatasets[] = formatDataset($dataset);
        }
        
        return $formattedDatasets;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get user datasets', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return [];
    }
}

/**
 * Get dataset by ID
 */
function getDatasetById($datasetId) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return null;
        }
        
        $sclib = getSCLibClient();
        $dataset = $sclib->getDatasetDetails($datasetId, $user['id']);
        
        if ($dataset) {
            return formatDataset($dataset);
        }
        
        return null;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset by ID', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Get dataset status
 */
function getDatasetStatus($datasetId) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return ['success' => false, 'error' => 'User not authenticated'];
        }
        
        $sclib = getSCLibClient();
        return $sclib->getDatasetStatus($datasetId, $user['id']);
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset status', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return ['success' => false, 'error' => $e->getMessage()];
    }
}

/**
 * Format dataset for display
 * Handles both MongoDB document format and API response format
 */
function formatDataset($dataset) {
    // Handle MongoDB document format (from SCLib_DatasetAPI)
    if (isset($dataset['uuid'])) {
        // Already in API format, but may need some adjustments
        return [
            'id' => $dataset['uuid'] ?? $dataset['id'] ?? '',
            'name' => $dataset['name'] ?? 'Unnamed Dataset',
            'uuid' => $dataset['uuid'] ?? $dataset['id'] ?? '',
            'sensor' => $dataset['sensor'] ?? $dataset['metadata']['sensor'] ?? 'Unknown',
            'status' => $dataset['status'] ?? $dataset['processing_status'] ?? 'unknown',
            'compression_status' => $dataset['compression_status'] ?? $dataset['metadata']['compression_status'] ?? 'unknown',
            'time' => $dataset['date_imported'] ?? $dataset['created_at'] ?? null,
            'data_size' => $dataset['total_size'] ?? $dataset['raw_size'] ?? $dataset['file_size'] ?? 0,
            'dimensions' => $dataset['dimensions'] ?? $dataset['metadata']['dimensions'] ?? '',
            'google_drive_link' => $dataset['google_drive_link'] ?? $dataset['metadata']['google_drive_link'] ?? null,
            'folder_uuid' => $dataset['folder_uuid'] ?? $dataset['metadata']['folder_uuid'] ?? '',
            'team_uuid' => $dataset['team_uuid'] ?? $dataset['team_id'] ?? '',
            'user_id' => $dataset['user'] ?? $dataset['user_id'] ?? '',
            'tags' => $dataset['tags'] ?? $dataset['metadata']['tags'] ?? [],
            'created_at' => $dataset['date_imported'] ?? $dataset['created_at'] ?? null,
            'updated_at' => $dataset['date_updated'] ?? $dataset['updated_at'] ?? null,
            'viewer_url' => $dataset['viewer_url'] ?? '',
            'download_url' => $dataset['download_url'] ?? ''
        ];
    }
    
    // Handle legacy format (from old API)
    return [
        'id' => $dataset['id'] ?? $dataset['uuid'] ?? '',
        'name' => $dataset['name'] ?? 'Unnamed Dataset',
        'uuid' => $dataset['uuid'] ?? $dataset['id'] ?? '',
        'sensor' => $dataset['sensor'] ?? $dataset['metadata']['sensor'] ?? 'Unknown',
        'status' => $dataset['status'] ?? $dataset['processing_status'] ?? 'unknown',
        'compression_status' => $dataset['compression_status'] ?? $dataset['metadata']['compression_status'] ?? 'unknown',
        'time' => $dataset['created_at'] ?? $dataset['date_imported'] ?? null,
        'data_size' => $dataset['file_size'] ?? $dataset['total_size'] ?? $dataset['raw_size'] ?? 0,
        'dimensions' => $dataset['dimensions'] ?? $dataset['metadata']['dimensions'] ?? '',
        'google_drive_link' => $dataset['google_drive_link'] ?? $dataset['metadata']['google_drive_link'] ?? null,
        'folder_uuid' => $dataset['folder_uuid'] ?? $dataset['metadata']['folder_uuid'] ?? '',
        'team_uuid' => $dataset['team_uuid'] ?? $dataset['team_id'] ?? '',
        'user_id' => $dataset['user'] ?? $dataset['user_id'] ?? '',
        'tags' => $dataset['tags'] ?? $dataset['metadata']['tags'] ?? [],
        'created_at' => $dataset['created_at'] ?? $dataset['date_imported'] ?? null,
        'updated_at' => $dataset['updated_at'] ?? $dataset['date_updated'] ?? null,
        'viewer_url' => $dataset['viewer_url'] ?? '',
        'download_url' => $dataset['download_url'] ?? ''
    ];
}

/**
 * Get datasets by folder - delegate to SCLib
 */
function getDatasetsByFolder($folderUuid) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return [];
        }
        
        $sclib = getSCLibClient();
        $datasets = $sclib->getUserDatasets($user['id']);
        
        // Filter by folder
        $folderDatasets = [];
        foreach ($datasets as $dataset) {
            if (isset($dataset['metadata']['folder_uuid']) && $dataset['metadata']['folder_uuid'] === $folderUuid) {
                $folderDatasets[] = formatDataset($dataset);
            }
        }
        
        return $folderDatasets;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get datasets by folder', ['folder_uuid' => $folderUuid, 'error' => $e->getMessage()]);
        return [];
    }
}

/**
 * Get dataset folders - delegate to SCLib
 */
function getDatasetFolders($userId) {
    try {
        $sclib = getSCLibClient();
        $datasets = $sclib->getUserDatasets($userId);
        
        // Extract unique folder UUIDs
        $folders = [];
        $folderCounts = [];
        
        foreach ($datasets as $dataset) {
            $folderUuid = $dataset['metadata']['folder_uuid'] ?? null;
            if ($folderUuid) {
                if (!isset($folderCounts[$folderUuid])) {
                    $folderCounts[$folderUuid] = 0;
                }
                $folderCounts[$folderUuid]++;
            }
        }
        
        foreach ($folderCounts as $folderUuid => $count) {
            $folders[] = [
                'uuid' => $folderUuid,
                'name' => $folderUuid, // SCLib should provide folder names
                'count' => $count
            ];
        }
        
        return $folders;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset folders', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return [];
    }
}

/**
 * Update dataset status - delegate to SCLib
 */
function updateDatasetStatus($datasetId, $status) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return false;
        }
        
        // SCLib should handle status updates through its job processing system
        // For now, we'll just log the request
        logMessage('INFO', 'Dataset status update requested', [
            'dataset_id' => $datasetId,
            'status' => $status,
            'user_id' => $user['id']
        ]);
        
        return true;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to update dataset status', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Share dataset - delegate to SCLib
 */
function shareDataset($datasetId, $userId) {
    try {
        $currentUser = getCurrentUser();
        if (!$currentUser) {
            return false;
        }
        
        $sclib = getSCLibClient();
        $result = $sclib->shareDataset($datasetId, $currentUser['id'], [$userId]);
        
        return $result['success'] ?? false;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to share dataset', ['dataset_id' => $datasetId, 'user_id' => $userId, 'error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Delete dataset - delegate to SCLib
 */
function deleteDataset($datasetId) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return false;
        }
        
        $sclib = getSCLibClient();
        $result = $sclib->deleteDataset($datasetId, $user['id']);
        
        return $result['success'] ?? false;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to delete dataset', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Get dataset statistics - delegate to SCLib
 */
function getDatasetStats($userId) {
    try {
        $sclib = getSCLibClient();
        $datasets = $sclib->getUserDatasets($userId);
        
        $totalDatasets = count($datasets);
        $totalSize = 0;
        $statusCounts = [];
        
        foreach ($datasets as $dataset) {
            $totalSize += $dataset['file_size'] ?? 0;
            $status = $dataset['status'] ?? 'unknown';
            $statusCounts[$status] = ($statusCounts[$status] ?? 0) + 1;
        }
        
        return [
            'total_datasets' => $totalDatasets,
            'total_size' => $totalSize,
            'status_counts' => $statusCounts
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset stats', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return [
            'total_datasets' => 0,
            'total_size' => 0,
            'status_counts' => []
        ];
    }
}

/**
 * Get all datasets for a user (my, shared, team) - uses SCLib API
 * Similar to old portal's getFullDatasets() function
 * 
 * @param string $userEmail User's email address
 * @return array [my_datasets, shared_datasets, team_datasets]
 */
function getAllDatasetsByEmail($userEmail) {
    try {
        logMessage('INFO', 'Getting datasets for user', ['user_email' => $userEmail]);
        
        $sclib = getSCLibClient();
        
        // Use the new SCLib Dataset Management API endpoint
        // The endpoint should be at /api/v1/datasets/by-user?user_email={email}
        try {
            logMessage('INFO', 'Calling SCLib API endpoint', ['endpoint' => '/api/v1/datasets/by-user', 'user_email' => $userEmail]);
            $response = $sclib->makeRequest('/api/v1/datasets/by-user', 'GET', null, ['user_email' => $userEmail]);
            logMessage('INFO', 'SCLib API response received', ['response_keys' => array_keys($response), 'has_success' => isset($response['success'])]);
        } catch (Exception $e) {
            // If endpoint doesn't exist, fall back to basic list
            logMessage('WARNING', 'Dataset by-user endpoint not available, trying basic list', ['error' => $e->getMessage(), 'trace' => $e->getTraceAsString()]);
            try {
                $response = $sclib->makeRequest('/api/v1/datasets', 'GET', null, ['user_email' => $userEmail]);
                // Transform basic list response to organized format
                if (isset($response['success']) && $response['success']) {
                    $datasets = $response['datasets'] ?? [];
                    logMessage('INFO', 'Using fallback endpoint, found datasets', ['count' => count($datasets)]);
                    // Format each dataset
                    $formattedDatasets = [];
                    foreach ($datasets as $dataset) {
                        $formattedDatasets[] = formatDataset($dataset);
                    }
                    return [
                        'my' => $formattedDatasets,
                        'shared' => [],
                        'team' => []
                    ];
                }
            } catch (Exception $e2) {
                logMessage('ERROR', 'Fallback endpoint also failed', ['error' => $e2->getMessage()]);
            }
            throw $e;
        }
        
        if (isset($response['success']) && $response['success']) {
            $datasets = $response['datasets'] ?? [
                'my' => [],
                'shared' => [],
                'team' => []
            ];
            
            logMessage('INFO', 'Processing datasets from API', [
                'my_count' => isset($datasets['my']) && is_array($datasets['my']) ? count($datasets['my']) : 0,
                'shared_count' => isset($datasets['shared']) && is_array($datasets['shared']) ? count($datasets['shared']) : 0,
                'team_count' => isset($datasets['team']) && is_array($datasets['team']) ? count($datasets['team']) : 0
            ]);
            
            // Format datasets for each category
            $formatted = [
                'my' => [],
                'shared' => [],
                'team' => []
            ];
            
            // Format my datasets
            if (isset($datasets['my']) && is_array($datasets['my'])) {
                foreach ($datasets['my'] as $dataset) {
                    $formatted['my'][] = formatDataset($dataset);
                }
            }
            
            // Format shared datasets
            if (isset($datasets['shared']) && is_array($datasets['shared'])) {
                foreach ($datasets['shared'] as $dataset) {
                    $formatted['shared'][] = formatDataset($dataset);
                }
            }
            
            // Format team datasets
            if (isset($datasets['team']) && is_array($datasets['team'])) {
                foreach ($datasets['team'] as $dataset) {
                    $formatted['team'][] = formatDataset($dataset);
                }
            }
            
            logMessage('INFO', 'Formatted datasets', [
                'my_count' => count($formatted['my']),
                'shared_count' => count($formatted['shared']),
                'team_count' => count($formatted['team'])
            ]);
            
            return $formatted;
        }
        
        logMessage('WARNING', 'SCLib API returned unsuccessful response', ['response' => $response, 'response_keys' => array_keys($response)]);
        return [
            'my' => [],
            'shared' => [],
            'team' => []
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get all datasets from SCLib API', [
            'user_email' => $userEmail, 
            'error' => $e->getMessage(),
            'trace' => $e->getTraceAsString()
        ]);
        return [
            'my' => [],
            'shared' => [],
            'team' => []
        ];
    }
}
?>