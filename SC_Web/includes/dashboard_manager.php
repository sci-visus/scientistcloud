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
        if (!in_array($dashboard, SUPPORTED_DASHBOARDS)) {
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
                            
                            return [
                                'name' => $dashboard_info['display_name'] ?? $name,
                                'type' => $dashboard_info['type'] ?? $dashboardType,
                                'url_template' => ($dashboard_info['nginx_path'] ?? '/dashboard/' . strtolower($name)) . '?uuid={uuid}&server={server}&name={name}',
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
    
    // Fallback to default configurations
    $default_configs = [
        'openvisus' => [
            'name' => 'OpenVisus Explorer',
            'type' => 'openvisus',
            'url_template' => '/dashboard/openvisus?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => ['tiff', 'hdf5', 'nexus'],
            'description' => 'Interactive 3D volume rendering with OpenVisus'
        ],
        'bokeh' => [
            'name' => 'Bokeh Dashboard',
            'type' => 'bokeh',
            'url_template' => '/dashboard/bokeh?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => ['tiff', 'hdf5', 'csv', 'json'],
            'description' => 'Interactive data visualization with Bokeh'
        ],
        'jupyter' => [
            'name' => 'Jupyter Notebook',
            'type' => 'jupyter',
            'url_template' => '/dashboard/jupyter?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => ['tiff', 'hdf5', 'csv', 'json', 'nexus'],
            'description' => 'Interactive data analysis with Jupyter'
        ],
        'plotly' => [
            'name' => 'Plotly Dashboard',
            'type' => 'plotly',
            'url_template' => '/dashboard/plotly?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => ['tiff', 'hdf5', 'csv', 'json'],
            'description' => 'Interactive 3D plotting with Plotly'
        ],
        'vtk' => [
            'name' => 'VTK Explorer',
            'type' => 'vtk',
            'url_template' => '/dashboard/vtk?uuid={uuid}&server={server}&name={name}',
            'supported_formats' => ['tiff', 'hdf5', 'nexus'],
            'description' => '3D visualization with VTK'
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
                            
                            $dashboards[] = [
                                'id' => $dashboardId,
                                'name' => $dashboard_info['display_name'] ?? $dashboard_info['name'] ?? $dashboardId,
                                'type' => $full_config['type'] ?? $dashboard_info['type'] ?? 'dash',
                                'display_name' => $dashboard_info['display_name'] ?? $dashboard_info['name'] ?? $dashboardId,
                                'description' => $full_config['description'] ?? $dashboard_info['description'] ?? 'Dashboard',
                                'nginx_path' => $dashboard_info['nginx_path'] ?? '/dashboard/' . strtolower($dashboardId),
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
    
    // Fallback to defaults
    return [
        ['id' => 'openvisus', 'name' => 'OpenVisus Explorer', 'type' => 'openvisus', 'display_name' => 'OpenVisus Explorer'],
        ['id' => 'plotly', 'name' => 'Plotly Dashboard', 'type' => 'plotly', 'display_name' => 'Plotly Dashboard'],
        ['id' => 'bokeh', 'name' => 'Bokeh Dashboard', 'type' => 'bokeh', 'display_name' => 'Bokeh Dashboard']
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
 * Check if dataset is supported by dashboard
 * If no supported_formats are specified, assume dashboard supports all datasets
 */
function isDatasetSupported($dataset, $config) {
    $supportedFormats = $config['supported_formats'] ?? [];
    
    // If no supported_formats specified, assume dashboard supports all datasets
    if (empty($supportedFormats)) {
        return true;
    }
    
    $sensor = strtolower($dataset['sensor'] ?? '');
    
    // If sensor is empty, assume dataset is supported (let dashboard handle it)
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

/**
 * Get dashboard status
 */
function getDashboardStatus($datasetId, $dashboardType) {
    try {
        $dataset = getDatasetById($datasetId);
        if (!$dataset) {
            return 'error';
        }
        
        // Check if dataset is ready
        if ($dataset['status'] !== 'done' && $dataset['status'] !== 'Ready') {
            return 'processing';
        }
        
        // Check if dashboard is available
        $availableDashboards = getAvailableDashboards($datasetId);
        foreach ($availableDashboards as $dashboard) {
            if ($dashboard['type'] === $dashboardType) {
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
