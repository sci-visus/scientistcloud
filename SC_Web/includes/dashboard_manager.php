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
 */
function getDashboardConfig($dashboardType) {
    $configs = [
        'openvisus' => [
            'name' => 'OpenVisus Explorer',
            'type' => 'openvisus',
            'url_template' => '/viewer/openvisus.php?dataset={uuid}&server={server}',
            'supported_formats' => ['tiff', 'hdf5', 'nexus'],
            'description' => 'Interactive 3D volume rendering with OpenVisus'
        ],
        'bokeh' => [
            'name' => 'Bokeh Dashboard',
            'type' => 'bokeh',
            'url_template' => '/viewer/bokeh.php?dataset={uuid}&server={server}',
            'supported_formats' => ['tiff', 'hdf5', 'csv', 'json'],
            'description' => 'Interactive data visualization with Bokeh'
        ],
        'jupyter' => [
            'name' => 'Jupyter Notebook',
            'type' => 'jupyter',
            'url_template' => '/viewer/jupyter.php?dataset={uuid}&server={server}',
            'supported_formats' => ['tiff', 'hdf5', 'csv', 'json', 'nexus'],
            'description' => 'Interactive data analysis with Jupyter'
        ],
        'plotly' => [
            'name' => 'Plotly Dashboard',
            'type' => 'plotly',
            'url_template' => '/viewer/plotly.php?dataset={uuid}&server={server}',
            'supported_formats' => ['tiff', 'hdf5', 'csv', 'json'],
            'description' => 'Interactive 3D plotting with Plotly'
        ],
        'vtk' => [
            'name' => 'VTK Explorer',
            'type' => 'vtk',
            'url_template' => '/viewer/vtk.php?dataset={uuid}&server={server}',
            'supported_formats' => ['tiff', 'hdf5', 'nexus'],
            'description' => '3D visualization with VTK'
        ]
    ];
    
    return $configs[$dashboardType] ?? null;
}

/**
 * Generate viewer URL
 */
function generateViewerUrl($dataset, $dashboardType) {
    $config = getDashboardConfig($dashboardType);
    if (!$config) {
        return null;
    }
    
    $server = 'false';
    if ($dataset['google_drive_link'] && strpos($dataset['google_drive_link'], 'http') !== false) {
        $server = 'true';
    }
    
    $url = str_replace(
        ['{uuid}', '{server}'],
        [$dataset['uuid'], $server],
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
        
        foreach (SUPPORTED_DASHBOARDS as $dashboardType) {
            $config = getDashboardConfig($dashboardType);
            if ($config && isDatasetSupported($dataset, $config)) {
                $availableDashboards[] = [
                    'type' => $dashboardType,
                    'name' => $config['name'],
                    'description' => $config['description'],
                    'url' => generateViewerUrl($dataset, $dashboardType)
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
 */
function isDatasetSupported($dataset, $config) {
    $sensor = strtolower($dataset['sensor'] ?? '');
    $supportedFormats = $config['supported_formats'] ?? [];
    
    foreach ($supportedFormats as $format) {
        if (strpos($sensor, $format) !== false) {
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
