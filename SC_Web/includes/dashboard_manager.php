<?php
/**
 * Dashboard Manager Module for ScientistCloud Data Portal
 * Handles dashboard loading and viewer management
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/auth.php');

/**
 * Get user's preferred dashboard
 */
function getUserPreferredDashboard($userId) {
    try {
        $user = getCurrentUser();
        if ($user && isset($user['preferred_dashboard'])) {
            return $user['preferred_dashboard'];
        }
        
        return DEFAULT_DASHBOARD;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get user preferred dashboard', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return DEFAULT_DASHBOARD;
    }
}

/**
 * Set user's preferred dashboard
 */
function setUserPreferredDashboard($userId, $dashboard) {
    try {
        // Get actual dashboards from registry instead of using old SUPPORTED_DASHBOARDS constant
        $allDashboards = getAllDashboards();
        $validDashboards = array_map(function($d) { return $d['id']; }, $allDashboards);
        
        // Also check against SUPPORTED_DASHBOARDS for backward compatibility
        $validDashboards = array_merge($validDashboards, SUPPORTED_DASHBOARDS);
        
        if (!in_array($dashboard, $validDashboards)) {
            return false;
        }
        
        return updateUserPreferences($userId, ['preferred_dashboard' => $dashboard]);
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to set user preferred dashboard', ['user_id' => $userId, 'dashboard' => $dashboard, 'error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Load dashboard for dataset
 */
function loadDashboard($datasetId, $dashboardType = null) {
    try {
        $dataset = getDatasetById($datasetId);
        if (!$dataset) {
            return null;
        }
        
        if (!$dashboardType) {
            $dashboardType = getUserPreferredDashboard($dataset['user_id']);
        }
        
        $dashboardConfig = getDashboardConfig($dashboardType);
        if (!$dashboardConfig) {
            return null;
        }
        
        return [
            'dataset' => $dataset,
            'dashboard_type' => $dashboardType,
            'config' => $dashboardConfig,
            'viewer_url' => generateViewerUrl($dataset, $dashboardType)
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to load dashboard', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Get dashboard configuration
 * Fetches from dashboard registry, with fallback to defaults
 */
function getDashboardConfig($dashboardType) {
    // Try to load from dashboard registry
    $possible_paths = [
        __DIR__ . '/../../SC_Dashboards/config/dashboard-registry.json',
        __DIR__ . '/../../SC_Dashboards/config/dashboards-list.json',
        getenv('SC_DASHBOARDS_CONFIG') ?: null,
        '/var/www/SC_Dashboards/config/dashboard-registry.json',
        '/var/www/SC_Dashboards/config/dashboards-list.json'
    ];
    
    foreach ($possible_paths as $path) {
        if ($path && file_exists($path)) {
            try {
                $registry = json_decode(file_get_contents($path), true);
                
                // Look for dashboard in registry
                if (isset($registry['dashboards'])) {
                    foreach ($registry['dashboards'] as $name => $dashboard_info) {
                        // Check if this dashboard matches the requested type
                        if (strtolower($name) === strtolower($dashboardType) || 
                            strtolower($dashboard_info['display_name'] ?? '') === strtolower($dashboardType) ||
                            (isset($dashboard_info['type']) && strtolower($dashboard_info['type']) === strtolower($dashboardType))) {
                            
                            // Try to load full config (flat structure: {name}.json)
                            $config_file = $dashboard_info['config_file'] ?? null;
                            $full_config = null;
                            
                            if ($config_file && file_exists($config_file)) {
                                $full_config = json_decode(file_get_contents($config_file), true);
                            } else {
                                // Try flat structure: {name}.json in dashboards directory
                                $config_dir = dirname($path);
                                $possible_config = $config_dir . '/../dashboards/' . $name . '.json';
                                if (file_exists($possible_config)) {
                                    $full_config = json_decode(file_get_contents($possible_config), true);
                                }
                            }
                            
                            // Use url_template from dashboard_info if available, otherwise construct it
                            $url_template = $dashboard_info['url_template'] ?? null;
                            if (!$url_template) {
                                // Fallback: construct from nginx_path
                                $url_template = ($dashboard_info['nginx_path'] ?? '/dashboard/' . strtolower($name)) . '?uuid={uuid}&server={server}&name={name}';
                            }
                            
                            return [
                                'name' => $dashboard_info['display_name'] ?? $name,
                                'type' => $dashboard_info['type'] ?? $dashboardType,
                                'url_template' => $url_template,
                                'supported_dimensions' => $full_config['supported_dimensions'] ?? [],
                                'supported_formats' => $full_config['supported_formats'] ?? ['tiff', 'hdf5', 'csv', 'json', 'nexus'],
                                'description' => $full_config['description'] ?? $dashboard_info['display_name'] ?? 'Dashboard',
                                'nginx_path' => $dashboard_info['nginx_path'] ?? '/dashboard/' . strtolower($name),
                                'port' => $dashboard_info['port'] ?? 0
                            ];
                        }
                    }
                }
            } catch (Exception $e) {
                error_log("Error reading dashboard registry: " . $e->getMessage());
                continue;
            }
        }
    }
    
    // Fallback to default configurations (only actual dashboards from dashboards-list.json)
    // These should match the dashboards in SC_Dashboards/config/dashboards-list.json
    $default_configs = [
        // Alias for backward compatibility
        'openvisus' => [
            'name' => 'OpenVisus Slice Explorer',
            'type' => 'openvisus',
            'url_template' => '/dashboard/openvisusslice?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => [], // Use supported_dimensions instead
            'description' => 'Interactive 3D volume rendering with OpenVisus'
        ],
        // Actual dashboards from dashboards-list.json
        'OpenVisusSlice' => [
            'name' => 'OpenVisus Slice Explorer',
            'type' => 'dash',
            'url_template' => '/dashboard/openvisusslice?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => [],
            'description' => 'Interactive 3D volume rendering with OpenVisus'
        ],
        '3DPlotly' => [
            'name' => '3D Plotly Dashboard',
            'type' => 'plotly',
            'url_template' => '/dashboard/plotly?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => [],
            'description' => 'Interactive 3D visualization using Plotly and Dash'
        ],
        '3DVTK' => [
            'name' => '3D VTK Dashboard',
            'type' => 'vtk',
            'url_template' => '/dashboard/vtk?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => [],
            'description' => 'Interactive 3D visualization using VTK'
        ],
        '4D_Dashboard' => [
            'name' => '4D Dashboard',
            'type' => 'dash',
            'url_template' => '/dashboard/4d?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => [],
            'description' => 'Interactive 4D visualization using 4D Nexus files'
        ],
        'Magicscan' => [
            'name' => 'MagicScan Dashboard',
            'type' => 'dash',
            'url_template' => '/dashboard/magicscan?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => [],
            'description' => 'Interactive MagicScan visualization using OpenVisus'
        ]
    ];
    
    return $default_configs[$dashboardType] ?? null;
}

/**
 * Get all available dashboards
 */
function getAllDashboards() {
    $dashboards = [];
    
    // Try to load from dashboard registry
    $possible_paths = [
        __DIR__ . '/../../SC_Dashboards/config/dashboard-registry.json',
        __DIR__ . '/../../SC_Dashboards/config/dashboards-list.json',
        getenv('SC_DASHBOARDS_CONFIG') ?: null,
        '/var/www/SC_Dashboards/config/dashboard-registry.json',
        '/var/www/SC_Dashboards/config/dashboards-list.json'
    ];
    
    foreach ($possible_paths as $path) {
        if ($path && file_exists($path)) {
            try {
                $registry = json_decode(file_get_contents($path), true);
                
                if (isset($registry['dashboards'])) {
                    // Handle both associative array (dashboard-registry.json) and numeric array (dashboards-list.json)
                    foreach ($registry['dashboards'] as $key => $dashboard_info) {
                        // For numeric arrays, use 'id' field; for associative arrays, use key
                        $dashboardId = $dashboard_info['id'] ?? $key;
                        
                        if (!isset($dashboard_info['enabled']) || $dashboard_info['enabled'] === true) {
                            // Try to load full config from flat structure
                            $config_file = $dashboard_info['config_file'] ?? null;
                            $full_config = null;
                            
                            if ($config_file && file_exists($config_file)) {
                                $full_config = json_decode(file_get_contents($config_file), true);
                            } else {
                                // Try relative path: {name}.json
                                $config_dir = dirname($path);
                                $possible_config = $config_dir . '/../dashboards/' . $dashboardId . '.json';
                                if (file_exists($possible_config)) {
                                    $full_config = json_decode(file_get_contents($possible_config), true);
                                }
                            }
                            
                            // Use url_template from dashboard_info if available, otherwise construct it
                            $url_template = $dashboard_info['url_template'] ?? null;
                            if (!$url_template) {
                                // Fallback: construct from nginx_path
                                $url_template = ($dashboard_info['nginx_path'] ?? '/dashboard/' . strtolower($dashboardId)) . '?uuid={uuid}&server={server}&name={name}';
                            }
                            
                            $dashboards[] = [
                                'id' => $dashboardId,
                                'name' => $dashboard_info['display_name'] ?? $dashboard_info['name'] ?? $dashboardId,
                                'type' => $full_config['type'] ?? $dashboard_info['type'] ?? 'dash',
                                'display_name' => $dashboard_info['display_name'] ?? $dashboard_info['name'] ?? $dashboardId,
                                'description' => $full_config['description'] ?? $dashboard_info['description'] ?? 'Dashboard',
                                'nginx_path' => $dashboard_info['nginx_path'] ?? '/dashboard/' . strtolower($dashboardId),
                                'url_template' => $url_template,
                                'port' => $dashboard_info['port'] ?? 0,
                                'enabled' => $dashboard_info['enabled'] ?? true
                            ];
                        }
                    }
                    return $dashboards;
                }
            } catch (Exception $e) {
                error_log("Error reading dashboard registry: " . $e->getMessage());
                continue;
            }
        }
    }
    
    // Fallback to defaults (only actual dashboards from dashboards-list.json)
    return [
        ['id' => 'OpenVisusSlice', 'name' => 'OpenVisus Slice Explorer', 'type' => 'dash', 'display_name' => 'OpenVisus Slice Explorer'],
        ['id' => '3DPlotly', 'name' => '3D Plotly Dashboard', 'type' => 'plotly', 'display_name' => '3D Plotly Dashboard'],
        ['id' => '3DVTK', 'name' => '3D VTK Dashboard', 'type' => 'vtk', 'display_name' => '3D VTK Dashboard'],
        ['id' => '4D_Dashboard', 'name' => '4D Dashboard', 'type' => 'dash', 'display_name' => '4D Dashboard'],
        ['id' => 'Magicscan', 'name' => 'MagicScan Dashboard', 'type' => 'dash', 'display_name' => 'MagicScan Dashboard']
    ];
}

/**
 * Generate viewer URL
 */
function generateViewerUrl($dataset, $dashboardType) {
    $config = getDashboardConfig($dashboardType);
    if (!$config) {
        return null;
    }
    
    // Determine server flag: true if link includes 'http' but is NOT a Google Drive link
    // Check download_url, viewer_url, or google_drive_link
    $link = $dataset['download_url'] ?? $dataset['viewer_url'] ?? $dataset['google_drive_link'] ?? '';
    $server = (!empty($link) && strpos($link, 'http') !== false && strpos($link, 'drive.google.com') === false) ? 'true' : 'false';
    
    $datasetName = $dataset['name'] ?? '';
    
    $url = str_replace(
        ['{uuid}', '{server}', '{name}'],
        [$dataset['uuid'], $server, urlencode($datasetName)],
        $config['url_template']
    );
    
    return SC_SERVER_URL . $url;
}

/**
 * Get available dashboards for dataset
 */
function getAvailableDashboards($datasetId) {
    try {
        $dataset = getDatasetById($datasetId);
        if (!$dataset) {
            return [];
        }
        
        $availableDashboards = [];
        
        // Use new dashboard list instead of old SUPPORTED_DASHBOARDS constant
        $allDashboards = getAllDashboards();
        
        foreach ($allDashboards as $dashboardInfo) {
            $dashboardId = $dashboardInfo['id'] ?? null;
            $dashboardType = $dashboardInfo['type'] ?? $dashboardId;
            
            if (!$dashboardId) {
                continue;
            }
            
            // Try to get config using dashboard ID or type
            $config = getDashboardConfig($dashboardId);
            if (!$config) {
                // Fallback to type
                $config = getDashboardConfig($dashboardType);
            }
            
            if ($config && isDatasetSupported($dataset, $config)) {
                $availableDashboards[] = [
                    'type' => $dashboardId,
                    'name' => $config['name'] ?? $dashboardInfo['display_name'] ?? $dashboardInfo['name'] ?? $dashboardId,
                    'description' => $config['description'] ?? $dashboardInfo['description'] ?? '',
                    'url' => generateViewerUrl($dataset, $dashboardId)
                ];
            }
        }
        
        return $availableDashboards;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get available dashboards', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return [];
    }
}

/**
 * Check if dataset is supported by dashboard based on dimensions
 * Dashboards specify supported_dimensions (e.g., ["4D", "3D", "2D", "1D"])
 * Datasets have a dimensions field (e.g., "4D", "3D", "2D", "1D")
 */
function isDatasetSupported($dataset, $config) {
    // Get supported dimensions from config (prefer supported_dimensions over supported_formats for backward compatibility)
    $supportedDimensions = $config['supported_dimensions'] ?? [];
    
    // If no supported_dimensions specified, check for legacy supported_formats
    if (empty($supportedDimensions)) {
        $supportedFormats = $config['supported_formats'] ?? [];
        // If neither is specified, assume dashboard supports all datasets
        if (empty($supportedFormats)) {
            return true;
        }
        // Legacy format checking (for backward compatibility)
        $sensor = strtolower($dataset['sensor'] ?? '');
        if (empty($sensor)) {
            return true;
        }
        foreach ($supportedFormats as $format) {
            if (strpos($sensor, strtolower($format)) !== false) {
                return true;
            }
        }
        return false;
    }
    
    // Get dataset dimensions
    $datasetDimensions = $dataset['dimensions'] ?? $dataset['metadata']['dimensions'] ?? '';
    
    // If dimensions are empty, assume dataset is supported (let dashboard handle it)
    if (empty($datasetDimensions)) {
        return true;
    }
    
    // Normalize dimensions: extract "4D", "3D", "2D", "1D" from the string
    // Handle formats like "4D", "4-D", "4 D", "4d", etc.
    $normalizedDatasetDim = preg_replace('/[^0-9D]/i', '', strtoupper($datasetDimensions));
    if (empty($normalizedDatasetDim)) {
        // Try to extract just the number and add "D"
        if (preg_match('/(\d+)/', $datasetDimensions, $matches)) {
            $normalizedDatasetDim = $matches[1] . 'D';
        } else {
            return true; // Can't determine dimension, let dashboard handle it
        }
    }
    
    // Normalize supported dimensions
    $normalizedSupported = array_map(function($dim) {
        $normalized = preg_replace('/[^0-9D]/i', '', strtoupper($dim));
        if (empty($normalized) && preg_match('/(\d+)/', $dim, $matches)) {
            $normalized = $matches[1] . 'D';
        }
        return $normalized;
    }, $supportedDimensions);
    
    // Check if dataset dimension matches any supported dimension
    foreach ($normalizedSupported as $supportedDim) {
        if ($normalizedDatasetDim === $supportedDim) {
            return true;
        }
    }
    
    return false;
}

/**
 * Get dashboard status
 */
function getDashboardStatus($datasetId, $dashboardType) {
    try {
        $dataset = getDatasetById($datasetId);
        if (!$dataset) {
            return 'error';
        }
        
        // Check if dataset is explicitly processing
        // Only return 'processing' if status explicitly indicates processing
        $status = strtolower(trim($dataset['status'] ?? ''));
        if (in_array($status, ['processing', 'pending', 'converting', 'uploading', 'queued'])) {
            return 'processing';
        }
        
        // If status is empty, null, or 'done'/'ready', assume ready
        // Most datasets should be ready to view even if status is not explicitly set
        
        // If no dashboard type specified, assume ready (let dashboard handle it)
        if (empty($dashboardType)) {
            return 'ready';
        }
        
        // Check if dashboard is available - use flexible matching
        $availableDashboards = getAvailableDashboards($datasetId);
        
        // Normalize dashboard type for comparison
        $normalizedType = strtolower(trim($dashboardType));
        
        foreach ($availableDashboards as $dashboard) {
            $dashboardId = strtolower($dashboard['type'] ?? '');
            $dashboardName = strtolower($dashboard['name'] ?? '');
            
            // Match by ID, type, or name (case-insensitive)
            if ($dashboardId === $normalizedType || 
                $dashboardName === $normalizedType ||
                strpos($dashboardId, $normalizedType) !== false ||
                strpos($normalizedType, $dashboardId) !== false) {
                return 'ready';
            }
        }
        
        // If no dashboards are available but we have a dashboard type, 
        // assume it's ready (let the dashboard handle format checking)
        if (empty($availableDashboards)) {
            // Try to get dashboard config to verify it exists
            $config = getDashboardConfig($dashboardType);
            if ($config) {
                return 'ready';
            }
        }
        
        return 'unsupported';
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dashboard status', ['dataset_id' => $datasetId, 'dashboard_type' => $dashboardType, 'error' => $e->getMessage()]);
        return 'error';
    }
}

/**
 * Get viewer configuration
 */
function getViewerConfig($datasetId, $dashboardType) {
    try {
        $dataset = getDatasetById($datasetId);
        if (!$dataset) {
            return null;
        }
        
        $config = getDashboardConfig($dashboardType);
        if (!$config) {
            return null;
        }
        
        return [
            'dataset' => $dataset,
            'dashboard' => $config,
            'viewer_url' => generateViewerUrl($dataset, $dashboardType),
            'status' => getDashboardStatus($datasetId, $dashboardType),
            'timeout' => VIEWER_TIMEOUT,
            'refresh_interval' => VIEWER_REFRESH_INTERVAL
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get viewer config', ['dataset_id' => $datasetId, 'dashboard_type' => $dashboardType, 'error' => $e->getMessage()]);
        return null;
    }
}
?>
