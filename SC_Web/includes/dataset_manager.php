<?php
/**
 * Dataset Manager Module for ScientistCloud Data Portal
 * Delegates ALL operations to SCLib API - no direct MongoDB access
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/auth.php');
require_once(__DIR__ . '/dataset_local_files.php');
// SCLib client is conditionally included - only when needed
if (!function_exists('getSCLibClient')) {
    require_once(__DIR__ . '/sclib_client.php');
}

/**
 * Get user's datasets
 * Note: Now uses user_email internally for correct querying (datasets use 'user' or 'user_email' fields, not 'user_id')
 */
function getUserDatasets($userId) {
    try {
        $sclib = getSCLibClient();
        // getUserDatasets() now automatically uses user_email if available
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
 * Dataset row for dashboard share links — includes stored S3 credentials (never sent to browser UI APIs).
 *
 * @return array<string,mixed>|null
 */
function getDatasetForDashboardLink($datasetId) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return null;
        }

        $sclib = getSCLibClient();
        $raw = $sclib->getDatasetDetails($datasetId, $user['id']);
        if (!$raw || !is_array($raw)) {
            return null;
        }

        $formatted = formatDataset($raw);
        foreach (['s3_access_key_id', 's3_secret_access_key', 's3_endpoint_url', 's3_region_name', 's3_path_style'] as $field) {
            if (array_key_exists($field, $raw)) {
                $formatted[$field] = $raw[$field];
            }
        }
        foreach (['accesskey', 'secretkey'] as $legacy) {
            if (!empty($raw[$legacy]) && empty($formatted['s3_access_key_id'])) {
                if ($legacy === 'accesskey') {
                    $formatted['s3_access_key_id'] = $raw[$legacy];
                } else {
                    $formatted['s3_secret_access_key'] = $raw[$legacy];
                }
            }
        }

        return $formatted;
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset for dashboard link', [
            'dataset_id' => $datasetId,
            'error' => $e->getMessage(),
        ]);
        return null;
    }
}

/**
 * Get dataset by UUID
 */
function getDatasetByUuid($datasetUuid) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return null;
        }
        
        $sclib = getSCLibClient();
        // Try to get dataset by UUID (identifier)
        $dataset = $sclib->getDatasetDetails($datasetUuid, $user['id']);
        
        if ($dataset) {
            return formatDataset($dataset);
        }
        
        return null;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset by UUID', ['dataset_uuid' => $datasetUuid, 'error' => $e->getMessage()]);
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
 * Resolve dataset size in gigabytes for display (multiple Mongo fields / units).
 * Treats 0 as unset so a stale data_size does not hide raw_size in bytes.
 */
function resolveDatasetDataSizeGb(array $dataset): float {
    $meta = (isset($dataset['metadata']) && is_array($dataset['metadata'])) ? $dataset['metadata'] : [];

    $positiveFloat = static function ($v): ?float {
        if ($v === null || $v === '') {
            return null;
        }
        if (!is_numeric($v)) {
            return null;
        }
        $f = (float) $v;
        return $f > 0 ? $f : null;
    };

    foreach (['data_size', 'total_size'] as $key) {
        foreach ([$dataset, $meta] as $src) {
            $g = $positiveFloat($src[$key] ?? null);
            if ($g !== null) {
                return $g;
            }
        }
    }

    foreach (['raw_size', 'total_size_bytes', 'file_size', 'size_bytes'] as $key) {
        foreach ([$dataset, $meta] as $src) {
            $b = $positiveFloat($src[$key] ?? null);
            if ($b !== null) {
                return $b / pow(1024, 3);
            }
        }
    }

    foreach (['data_size', 'total_size'] as $key) {
        $raw = $dataset[$key] ?? null;
        if (!is_string($raw)) {
            continue;
        }
        $sizeStr = strtoupper(trim($raw));
        if ($sizeStr === '') {
            continue;
        }
        if (preg_match('/^([\d.]+)\s*([KMGT]?B?)$/', $sizeStr, $matches)) {
            $number = (float) $matches[1];
            $unit = $matches[2] ?? 'B';
            switch ($unit) {
                case 'KB':
                case 'K':
                    return $number / (1024 * 1024);
                case 'MB':
                case 'M':
                    return $number / 1024;
                case 'GB':
                case 'G':
                    return $number;
                case 'TB':
                case 'T':
                    return $number * 1024;
                default:
                    return $number / (1024 * 1024 * 1024);
            }
        }
    }

    return 0.0;
}

/**
 * Format dataset for display
 * Handles both MongoDB document format and API response format
 */
function formatDataset($dataset) {
    // Normalize tags - handle both array and string formats
    $tags = $dataset['tags'] ?? $dataset['metadata']['tags'] ?? [];
    if (is_string($tags)) {
        // If tags is a string, try to parse it (could be comma-separated or JSON)
        if (strpos($tags, '[') === 0) {
            $tags = json_decode($tags, true) ?? [];
        } else {
            $tags = array_filter(array_map('trim', explode(',', $tags)));
        }
    }
    if (!is_array($tags)) {
        $tags = [];
    }
    
    // Size in GB: never let a literal 0 block fallbacks (API may send data_size: 0 while raw_size is set)
    $data_size = resolveDatasetDataSizeGb($dataset);
    
    // Get created date - check multiple possible fields
    $created_at = $dataset['time'] ?? $dataset['date_imported'] ?? $dataset['created_at'] ?? null;
    
    // Get is_public - handle both boolean and string values
    $is_public = $dataset['is_public'] ?? $dataset['metadata']['is_public'] ?? false;
    if (is_string($is_public)) {
        $is_public = filter_var($is_public, FILTER_VALIDATE_BOOLEAN);
    }

    // Folder label for sidebar grouping — Mongo may use folder_uuid or legacy `folder`
    $resolvedFolder = '';
    foreach (['folder_uuid', 'folder'] as $fk) {
        if (!empty($dataset[$fk])) {
            $resolvedFolder = trim((string)$dataset[$fk]);
            break;
        }
    }
    if ($resolvedFolder === '' && isset($dataset['metadata']) && is_array($dataset['metadata'])) {
        foreach (['folder_uuid', 'folder'] as $fk) {
            if (!empty($dataset['metadata'][$fk])) {
                $resolvedFolder = trim((string)$dataset['metadata'][$fk]);
                break;
            }
        }
    }
    
    $status = $dataset['status'] ?? $dataset['processing_status'] ?? 'unknown';
    $canonicalState = $dataset['canonical_state'] ?? null;
    $statusMessage = $dataset['status_message'] ?? null;
    $errorMessage = $dataset['error_message'] ?? null;
    $conversionLastError = $dataset['conversion_last_error'] ?? null;
    $uploadInterrupted = $dataset['upload_interrupted'] ?? false;
    $terminalReadyStatuses = ['done', 'ready', 'completed', 'uploaded'];
    $statusLower = strtolower(trim((string)$status));
    $canonicalLower = strtolower(trim((string)$canonicalState));
    $staleUploadWaitMessage = stripos((string)$statusMessage . ' ' . (string)$errorMessage, 'Waiting for the rest of the selected local files') !== false;
    if (!$uploadInterrupted && $staleUploadWaitMessage && (in_array($statusLower, $terminalReadyStatuses, true) || $canonicalLower === 'ready')) {
        $statusMessage = null;
        $errorMessage = null;
    }

    $hasLocalFiles = sc_dataset_has_local_dashboard_files($dataset);
    $serverFlag = sc_dataset_server_flag($dataset);

    // Base dataset structure
    $formatted = [
        'id' => $dataset['uuid'] ?? $dataset['id'] ?? '',
        'name' => $dataset['name'] ?? 'Unnamed Dataset',
        'uuid' => $dataset['uuid'] ?? $dataset['id'] ?? '',
        'sensor' => $dataset['sensor'] ?? $dataset['metadata']['sensor'] ?? 'Unknown',
        'status' => $status,
        'compression_status' => $dataset['compression_status'] ?? $dataset['metadata']['compression_status'] ?? 'unknown',
        'time' => $created_at,
        'data_size' => $data_size,
        'dimensions' => $dataset['dimensions'] ?? $dataset['metadata']['dimensions'] ?? '',
        'google_drive_link' => $dataset['google_drive_link'] ?? $dataset['metadata']['google_drive_link'] ?? null,
        'folder_uuid' => $resolvedFolder,
        'team_uuid' => $dataset['team_uuid'] ?? $dataset['team_id'] ?? '',
        'user_id' => $dataset['user'] ?? $dataset['user_email'] ?? $dataset['user_id'] ?? '',
        'tags' => $tags,
        'preferred_dashboard' => $dataset['preferred_dashboard'] ?? $dataset['metadata']['preferred_dashboard'] ?? '',
        'is_public' => $is_public,
        'created_at' => $created_at,
        'updated_at' => $dataset['date_updated'] ?? $dataset['updated_at'] ?? null,
        'viewer_url' => $dataset['viewer_url'] ?? '',
        'download_url' => $dataset['download_url'] ?? '',
        'source_path' => $dataset['source_path'] ?? $dataset['metadata']['source_path'] ?? '',
        'has_local_files' => $hasLocalFiles,
        'server' => $serverFlag,
        'canonical_state' => $canonicalState,
        'error_message' => $errorMessage,
        'status_message' => $statusMessage,
        'conversion_last_error' => $conversionLastError,
        'upload_interrupted' => $uploadInterrupted,
        'interrupted_at' => $dataset['interrupted_at'] ?? null,
        'is_downloadable' => $dataset['is_downloadable'] ?? 'only owner',
        'team_name' => $dataset['team_name'] ?? '',
        'is_owner' => $dataset['is_owner'] ?? null,
        'can_download' => $dataset['can_download'] ?? null,
    ];
    
    return $formatted;
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
            $folderUuid = $dataset['folder_uuid'] ?? $dataset['folder'] ?? null;
            if (!$folderUuid && isset($dataset['metadata']) && is_array($dataset['metadata'])) {
                $folderUuid = $dataset['metadata']['folder_uuid'] ?? $dataset['metadata']['folder'] ?? null;
            }
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
 * Update dataset - delegate to SCLib
 */
function updateDataset($datasetId, $updateData) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return ['success' => false, 'error' => 'User not authenticated'];
        }
        
        $sclib = getSCLibClient();
        $result = $sclib->updateDataset($datasetId, $updateData, $user['email']);
        
        return $result;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to update dataset', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return ['success' => false, 'error' => $e->getMessage()];
    }
}

/**
 * Delete dataset - delegate to SCLib
 */
function deleteDataset($datasetId) {
    try {
        $user = getCurrentUser();
        if (!$user) {
            return ['success' => false, 'error' => 'User not authenticated'];
        }
        
        $sclib = getSCLibClient();
        $result = $sclib->deleteDataset($datasetId, $user['email']);
        
        return $result;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to delete dataset', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return ['success' => false, 'error' => $e->getMessage()];
    }
}

/**
 * Get dataset statistics - delegate to SCLib
 * Uses user_email to query datasets (datasets are stored with 'user' or 'user_email' fields, not 'user_id')
 */
function getDatasetStats($userId) {
    try {
        // Get current user to access email
        $user = getCurrentUser();
        if (!$user || !isset($user['email'])) {
            logMessage('WARNING', 'Cannot get dataset stats: user email not available', ['user_id' => $userId]);
            return [
                'total_datasets' => 0,
                'total_size' => 0,
                'status_counts' => []
            ];
        }
        
        $userEmail = $user['email'];
        $sclib = getSCLibClient();
        
        // Use the correct endpoint that queries by user_email
        // This endpoint correctly queries for {'$or': [{'user': user_email}, {'user_email': user_email}]}
        $response = $sclib->makeRequest('/api/v1/datasets/by-user', 'GET', null, ['user_email' => $userEmail]);
        
        // Combine all datasets (my, shared, team) for statistics
        $allDatasets = [];
        if (isset($response['datasets'])) {
            $allDatasets = array_merge(
                $response['datasets']['my'] ?? [],
                $response['datasets']['shared'] ?? [],
                $response['datasets']['team'] ?? []
            );
        }
        
        $totalDatasets = count($allDatasets);
        $totalSize = 0;
        $statusCounts = [];
        
        foreach ($allDatasets as $dataset) {
            // Format dataset to ensure consistent field names
            $formatted = formatDataset($dataset);
            
            // Use data_size from formatted dataset (handles multiple field name variations)
            // Note: data_size is stored in GB (float), not bytes
            $dataSizeGb = $formatted['data_size'] ?? 0;
            // Ensure it's numeric before arithmetic operation
            if (!is_numeric($dataSizeGb)) {
                $dataSizeGb = 0;
            } else {
                $dataSizeGb = (float)$dataSizeGb;
            }
            $totalSize += $dataSizeGb;
            
            // Get status from formatted dataset
            $status = $formatted['status'] ?? 'unknown';
            $statusCounts[$status] = ($statusCounts[$status] ?? 0) + 1;
        }
        
        // Convert total_size from GB to bytes for formatFileSize() function
        // data_size is stored in GB, but formatFileSize() expects bytes
        // Ensure totalSize is numeric before multiplication
        if (!is_numeric($totalSize)) {
            $totalSize = 0;
        }
        $totalSizeBytes = (float)$totalSize * (1024 ** 3); // GB to bytes
        
        return [
            'total_datasets' => $totalDatasets,
            'total_size' => $totalSizeBytes, // Return in bytes for formatFileSize()
            'total_size_gb' => $totalSize, // Also return in GB for reference
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

/**
 * Get all public datasets (no authentication required)
 * Uses SCLib API to query for public datasets
 * 
 * @return array Array of formatted public datasets
 */
function getPublicDatasets() {
    try {
        logMessage('INFO', 'Getting public datasets via SCLib API');
        
        // Ensure SCLib client is available
        if (!function_exists('getSCLibClient')) {
            require_once(__DIR__ . '/sclib_client.php');
        }
        
        $sclib = getSCLibClient();
        
        // Call SCLib API endpoint for public datasets
        try {
            $response = $sclib->makeRequest('/api/v1/datasets/public', 'GET');
            
            if (isset($response['success']) && $response['success']) {
                $datasets = $response['datasets'] ?? [];
                
                logMessage('INFO', 'Retrieved public datasets from SCLib', [
                    'count' => count($datasets)
                ]);
                
                // Format datasets using formatDataset function
                $formattedDatasets = [];
                foreach ($datasets as $dataset) {
                    try {
                        $formattedDatasets[] = formatDataset($dataset);
                    } catch (Exception $e) {
                        logMessage('ERROR', 'Failed to format dataset', [
                            'dataset_uuid' => $dataset['uuid'] ?? 'unknown',
                            'error' => $e->getMessage()
                        ]);
                    }
                }
                
                return $formattedDatasets;
            } else {
                logMessage('WARNING', 'SCLib API returned unsuccessful response', [
                    'response' => $response
                ]);
                return [];
            }
            
        } catch (Exception $e) {
            logMessage('ERROR', 'Failed to call SCLib API for public datasets', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            return [];
        }
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get public datasets', [
            'error' => $e->getMessage(),
            'trace' => $e->getTraceAsString()
        ]);
        return [];
    }
}
?>