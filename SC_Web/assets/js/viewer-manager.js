/**
 * Viewer Manager JavaScript
 * Handles viewer operations and dashboard management
 */

class ViewerManager {
    constructor() {
        this.currentViewer = null;
        this.viewers = {}; // Will be loaded from API
        // No default viewers - all should come from API to avoid duplicates
        this.defaultViewers = {};
        this.initialize();
    }
    
    /**
     * Load dashboards from API
     */
    async loadDashboards() {
        try {
            // Helper function to get API base path (detects local vs server)
            const getApiBasePath = () => {
                const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                return isLocal ? '/api' : '/portal/api';
            };
            const response = await fetch(`${getApiBasePath()}/dashboards.php`, {
                credentials: 'include'  // Include cookies for authentication
            });
            
            if (!response.ok) {
                console.warn('Failed to load dashboards from API, using defaults');
                this.viewers = this.defaultViewers;
                this.populateViewerSelector();
                return;
            }
            
            const data = await response.json();
            
            if (data.success && data.dashboards) {
                // Convert API response to viewer format
                this.viewers = {};
                data.dashboards.forEach(dashboard => {
                    if (dashboard.enabled) {
                        // Use dashboard.id as the key (e.g., "3DPlotly", "3DVTK")
                        const dashboardId = dashboard.id;
                        // Ensure url_template is set correctly
                        let urlTemplate = dashboard.url_template;
                        if (!urlTemplate && dashboard.nginx_path) {
                            urlTemplate = dashboard.nginx_path + '?uuid={uuid}&server={server}&name={name}';
                        }
                        
                        this.viewers[dashboardId] = {
                            id: dashboardId,
                            name: dashboard.display_name || dashboard.name,
                            type: dashboard.type || dashboardId, // Use type for compatibility, fallback to id
                            url_template: urlTemplate,
                            supported_formats: [], // Will be determined from dataset type
                            description: dashboard.description || dashboard.display_name,
                            nginx_path: dashboard.nginx_path,
                            port: dashboard.port
                        };
                    }
                });
                
                // No need to merge defaults - all dashboards should come from API
                // This prevents duplicates
                
                console.log('Loaded dashboards from API:', Object.keys(this.viewers).length);
            } else {
                console.warn('Invalid dashboard API response, using defaults');
                this.viewers = this.defaultViewers;
            }
            
            this.populateViewerSelector();
            
        } catch (error) {
            console.error('Error loading dashboards:', error);
            // Fallback to default viewers
            this.viewers = this.defaultViewers;
            this.populateViewerSelector();
        }
    }
    
    /**
     * Populate viewer selector dropdown
     */
    populateViewerSelector() {
        const viewerType = document.getElementById('viewerType');
        if (!viewerType) {
            console.warn('Viewer selector not found');
            return;
        }
        
        // Clear existing options (except first empty one if exists)
        viewerType.innerHTML = '';
        
        // Add options from loaded viewers
        // Use dashboard id as value for consistency
        Object.entries(this.viewers).forEach(([viewerKey, viewer]) => {
            const option = document.createElement('option');
            // Use id if available, otherwise use the key or type
            option.value = viewer.id || viewerKey || viewer.type;
            option.textContent = viewer.name;
            viewerType.appendChild(option);
        });
        
        // Set default viewer if available
        if (viewerType.options.length > 0) {
            viewerType.value = viewerType.options[0].value;
        }
        
        console.log('Populated viewer selector with', viewerType.options.length, 'dashboards');
    }

    /**
     * Initialize the viewer manager
     */
    async initialize() {
        this.setupEventListeners();
        await this.loadDashboards(); // Load dashboards from API first
        this.loadViewerSettings();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Viewer type change
        const viewerType = document.getElementById('viewerType');
        if (viewerType) {
            viewerType.addEventListener('change', (e) => {
                this.handleViewerTypeChange(e.target.value);
            });
        }


        // Refresh button
        const refreshButton = document.querySelector('[onclick="refreshDashboard()"]');
        if (refreshButton) {
            refreshButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.refreshDashboard();
            });
        }

        // Annotation tools
        document.querySelectorAll('.viewer-toolbar .btn').forEach(button => {
            button.addEventListener('click', (e) => {
                this.handleAnnotationTool(e.target.closest('.btn'));
            });
        });
    }

    /**
     * Load viewer settings
     */
    loadViewerSettings() {
        const settings = localStorage.getItem('viewerSettings');
        if (settings) {
            try {
                const parsedSettings = JSON.parse(settings);
                this.applyViewerSettings(parsedSettings);
            } catch (error) {
                console.error('Error loading viewer settings:', error);
            }
        }
    }

    /**
     * Apply viewer settings
     */
    applyViewerSettings(settings) {
        if (settings.viewerType) {
            const viewerType = document.getElementById('viewerType');
            if (viewerType) {
                viewerType.value = settings.viewerType;
            }
        }
    }

    /**
     * Save viewer settings
     */
    saveViewerSettings() {
        const settings = {
            viewerType: document.getElementById('viewerType')?.value || 'OpenVisusSlice',
            theme: document.body.classList.contains('light-theme') ? 'light' : 'dark'
        };
        
        localStorage.setItem('viewerSettings', JSON.stringify(settings));
    }

    /**
     * Handle viewer type change
     */
    handleViewerTypeChange(viewerType) {
        console.log('Viewer type changed to:', viewerType);
        
        // Update dashboard based on viewer type
        if (window.datasetManager && window.datasetManager.currentDataset) {
            this.loadDashboard(
                window.datasetManager.currentDataset.id,
                window.datasetManager.currentDataset.name,
                window.datasetManager.currentDataset.uuid,
                window.datasetManager.currentDataset.server,
                viewerType
            );
        }
        
        this.saveViewerSettings();
    }

    /**
     * Handle dashboard change
     */
    handleDashboardChange(dashboardType) {
        console.log('Dashboard changed to:', dashboardType);
        
        if (window.datasetManager && window.datasetManager.currentDataset) {
            this.loadDashboard(
                window.datasetManager.currentDataset.id,
                window.datasetManager.currentDataset.name,
                window.datasetManager.currentDataset.uuid,
                window.datasetManager.currentDataset.server,
                dashboardType
            );
        }
    }

    /**
     * Load dashboard
     */
    async loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, dashboardType = 'OpenVisusSlice') {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5 class="mt-3">Loading Dashboard</h5>
                <p class="text-muted">Preparing ${this.viewers[dashboardType]?.name || 'visualization'} for ${datasetName}</p>
            </div>
        `;

        try {
            // Check if dataset is ready (pass dashboard type for proper status check)
            const status = await this.checkDatasetStatus(datasetId, dashboardType);
            
            if (status === 'ready') {
                // Load the dashboard
                await this.loadDashboardContent(datasetId, datasetName, datasetUuid, datasetServer, dashboardType);
            } else if (status === 'processing') {
                this.showProcessingDashboard(datasetId, datasetName);
            } else if (status === 'unsupported') {
                this.showUnsupportedDashboard(datasetId, datasetName);
            } else {
                this.showErrorDashboard('Unknown error occurred');
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showErrorDashboard('Failed to load dashboard');
        }
    }

    /**
     * Check dataset status
     */
    async checkDatasetStatus(datasetId, dashboardType = null) {
        try {
            // Helper function to get API base path
            const getApiBasePath = () => {
                const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                return isLocal ? '/api' : '/portal/api';
            };
            let url = `${getApiBasePath()}/dataset-status.php?dataset_id=${datasetId}`;
            if (dashboardType) {
                url += `&dashboard=${encodeURIComponent(dashboardType)}`;
            }
            const response = await fetch(url, {
                credentials: 'include'  // Include cookies for authentication
            });
            
            // Handle authentication errors
            if (response.status === 401) {
                console.error('Authentication required for dataset status check');
                return 'error';
            }
            
            if (!response.ok) {
                console.error(`Error checking dataset status: ${response.status} ${response.statusText}`);
                return 'error';
            }
            
            const data = await response.json();
            return data.status || 'unknown';
        } catch (error) {
            console.error('Error checking dataset status:', error);
            return 'error';
        }
    }

    /**
     * Load dashboard content
     */
    async loadDashboardContent(datasetId, datasetName, datasetUuid, datasetServer, dashboardType) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Map common aliases to actual dashboard IDs
        // Note: 'openvisus' is kept as a separate fallback viewer, but aliases map to 'OpenVisusSlice' from API
        const dashboardAliases = {
            'openvisus': 'OpenVisusSlice',  // Map lowercase alias to the API dashboard
            'OpenVisus': 'OpenVisusSlice',
            'openvisusslice': 'OpenVisusSlice'
        };
        
        // Resolve dashboard type to actual ID
        const resolvedDashboardType = dashboardAliases[dashboardType] || dashboardType;
        
        // Find viewer by id, type, or key (try multiple lookup strategies)
        let viewer = this.viewers[resolvedDashboardType] || this.viewers[dashboardType];
        
        if (!viewer) {
            // Try to find by matching id or type (case-insensitive)
            const normalizedType = resolvedDashboardType.toLowerCase();
            viewer = Object.values(this.viewers).find(v => {
                const vId = (v.id || '').toLowerCase();
                const vType = (v.type || '').toLowerCase();
                return vId === normalizedType || 
                       vType === normalizedType ||
                       vId === dashboardType.toLowerCase() ||
                       vType === dashboardType.toLowerCase();
            });
        }
        
        // Fallback to default viewers if not found
        if (!viewer) {
            viewer = this.defaultViewers[resolvedDashboardType] || this.defaultViewers[dashboardType];
        }
        
        if (!viewer) {
            console.error('Unknown dashboard type:', dashboardType, 'Resolved:', resolvedDashboardType, 'Available viewers:', Object.keys(this.viewers));
            this.showErrorDashboard('Unknown dashboard type: ' + dashboardType);
            return;
        }

        // Validate url_template exists
        if (!viewer.url_template) {
            console.error('Viewer missing url_template:', viewer, 'Dashboard type:', dashboardType);
            // Try to construct from nginx_path
            if (viewer.nginx_path) {
                viewer.url_template = viewer.nginx_path + '?uuid={uuid}&server={server}&name={name}';
            } else if (viewer.id || resolvedDashboardType) {
                // Fallback: construct from dashboard ID
                const dashboardId = viewer.id || resolvedDashboardType;
                viewer.url_template = '/dashboard/' + dashboardId.toLowerCase().replace(/_/g, '') + '?uuid={uuid}&server={server}&name={name}';
                console.warn('Constructed url_template from dashboard ID:', viewer.url_template);
            } else {
                this.showErrorDashboard('Dashboard configuration error: missing URL template');
                return;
            }
        }

        // Ensure url_template is a valid string
        if (typeof viewer.url_template !== 'string' || viewer.url_template.trim() === '') {
            console.error('Invalid url_template:', viewer.url_template);
            this.showErrorDashboard('Dashboard configuration error: invalid URL template');
            return;
        }

        // Generate viewer URL using the url_template
        const viewerUrl = this.generateViewerUrl(datasetUuid, datasetServer, datasetName, viewer.url_template);
        
        console.log('Loading dashboard:', {
            dashboardType,
            resolvedDashboardType,
            viewerId: viewer.id,
            viewerName: viewer.name,
            urlTemplate: viewer.url_template,
            generatedUrl: viewerUrl
        });
        
        // Create iframe
        const iframe = document.createElement('iframe');
        iframe.id = 'dashboardFrame';
        iframe.src = viewerUrl;
        iframe.width = '100%';
        iframe.height = '100%';
        iframe.frameBorder = '0';
        iframe.onload = () => this.onDashboardLoad();
        iframe.onerror = () => this.onDashboardError();

        // Create dashboard container
        const dashboardContainer = document.createElement('div');
        dashboardContainer.className = 'dashboard-container';
        
        const dashboardHeader = document.createElement('div');
        dashboardHeader.className = 'dashboard-header';
        dashboardHeader.innerHTML = `<h4>${datasetName}</h4>`;
        
        const dashboardContent = document.createElement('div');
        dashboardContent.className = 'dashboard-content';
        dashboardContent.appendChild(iframe);
        
        dashboardContainer.appendChild(dashboardHeader);
        dashboardContainer.appendChild(dashboardContent);
        
        viewerContainer.innerHTML = '';
        viewerContainer.appendChild(dashboardContainer);
    }

    /**
     * Generate viewer URL with uuid, server, and name parameters
     */
    generateViewerUrl(datasetUuid, datasetServer, datasetName, urlTemplate) {
        if (!urlTemplate || typeof urlTemplate !== 'string') {
            console.error('generateViewerUrl: urlTemplate is empty or invalid:', urlTemplate);
            return '#';
        }
        
        // Trim whitespace
        urlTemplate = urlTemplate.trim();
        
        // Detect local development mode
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        // If urlTemplate doesn't start with / or http, it's likely just an ID - construct proper path
        if (!urlTemplate.startsWith('/') && !urlTemplate.startsWith('http')) {
            console.warn('generateViewerUrl: urlTemplate appears to be just an ID, constructing path:', urlTemplate);
            // Convert to lowercase and replace underscores/dashes with nothing for URL path
            const pathId = urlTemplate.toLowerCase().replace(/[_-]/g, '');
            urlTemplate = '/dashboard/' + pathId + '?uuid={uuid}&server={server}&name={name}';
        }
        
        // Replace all three placeholders: {uuid}, {server}, {name}
        let url = urlTemplate
            .replace(/{uuid}/g, encodeURIComponent(datasetUuid))
            .replace(/{server}/g, encodeURIComponent(datasetServer || 'false'))
            .replace(/{name}/g, encodeURIComponent(datasetName || ''));
        
        // For local development, convert /dashboard/ paths to direct port access
        if (isLocal && url.startsWith('/dashboard/')) {
            // Get the dashboard name from the URL path (e.g., /dashboard/OpenVisusSlice/?uuid=...)
            const match = url.match(/\/dashboard\/([^/?]+)/);
            const dashboardPathName = match?.[1];
            
            if (dashboardPathName && this.viewers) {
                // Find the dashboard by matching:
                // 1. Exact ID match (case-insensitive)
                // 2. nginx_path contains the path name
                // 3. Name contains the path name
                const dashboard = Object.values(this.viewers).find(v => {
                    const vId = (v.id || '').toLowerCase();
                    const vNginxPath = (v.nginx_path || '').toLowerCase();
                    const vName = (v.name || '').toLowerCase();
                    const pathNameLower = dashboardPathName.toLowerCase();
                    
                    return vId === pathNameLower ||
                           vNginxPath.includes(pathNameLower) ||
                           vNginxPath.endsWith('/' + pathNameLower) ||
                           vName.includes(pathNameLower);
                });
                
                if (dashboard && dashboard.port) {
                    // Extract the path after /dashboard/name
                    // For OpenVisusSlice, the app expects /OpenVisusSlice/?uuid=...
                    // So we need to construct: http://localhost:PORT/OpenVisusSlice/?uuid=...
                    const pathAfterDashboard = url.replace(/^\/dashboard\/[^/?]+/, '');
                    // Use the dashboard ID as the app path (e.g., /OpenVisusSlice/)
                    const appPath = '/' + dashboard.id + (pathAfterDashboard || '/');
                    url = `http://localhost:${dashboard.port}${appPath}`;
                    console.log(`Local dev: Using direct port access for ${dashboard.id}: ${url}`);
                } else {
                    console.warn(`Local dev: Could not find dashboard for path "${dashboardPathName}". Available:`, Object.keys(this.viewers));
                }
            }
        }
        
        return url;
    }


    /**
     * Show processing dashboard
     */
    showProcessingDashboard(datasetId, datasetName) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        viewerContainer.innerHTML = `
            <div class="dashboard-container">
                <div class="dashboard-header">
                    <h4>${datasetName}</h4>
                    <span class="badge bg-warning">Processing</span>
                </div>
                <div class="dashboard-content processing-content">
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <h5 class="mt-3">Dataset is being processed</h5>
                        <p class="text-muted">Please wait while we prepare your data for visualization.</p>
                        <div class="progress mt-3" style="width: 300px; margin: 0 auto;">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                 role="progressbar" style="width: 100%"></div>
                        </div>
                        <button class="btn btn-primary mt-3" onclick="checkProcessingStatus('${datasetId}')">
                            Check Status
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show unsupported dashboard
     */
    showUnsupportedDashboard(datasetId, datasetName) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        viewerContainer.innerHTML = `
            <div class="dashboard-container">
                <div class="dashboard-header">
                    <h4>${datasetName}</h4>
                    <span class="badge bg-secondary">Unsupported</span>
                </div>
                <div class="dashboard-content unsupported-content">
                    <div class="text-center">
                        <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                        <h5>Dashboard not available</h5>
                        <p class="text-muted">This dataset format is not supported by the current dashboard.</p>
                        <div class="mt-3">
                            <h6>Available dashboards for this dataset:</h6>
                            <div class="list-group">
                                ${this.generateAvailableDashboards(datasetId)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Generate available dashboards
     */
    generateAvailableDashboards(datasetId) {
        let html = '';
        
        Object.values(this.viewers).forEach(viewer => {
            html += `
                <a href="javascript:loadDashboard('${datasetId}', '${viewer.type}')" class="list-group-item list-group-item-action">
                    <h6 class="mb-1">${viewer.name}</h6>
                    <p class="mb-1">${viewer.description}</p>
                </a>
            `;
        });
        
        return html;
    }

    /**
     * Show error dashboard
     */
    showErrorDashboard(errorMessage) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        viewerContainer.innerHTML = `
            <div class="dashboard-container">
                <div class="dashboard-header">
                    <h4>Error</h4>
                    <span class="badge bg-danger">Error</span>
                </div>
                <div class="dashboard-content error-content">
                    <div class="text-center">
                        <i class="fas fa-exclamation-circle fa-3x text-danger mb-3"></i>
                        <h5>Error loading dashboard</h5>
                        <p class="text-muted">${errorMessage}</p>
                        <button class="btn btn-primary mt-3" onclick="location.reload()">
                            <i class="fas fa-refresh"></i> Retry
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Refresh dashboard
     */
    refreshDashboard() {
        const iframe = document.getElementById('dashboardFrame');
        if (iframe) {
            iframe.src = iframe.src;
        }
    }

    /**
     * Handle annotation tool
     */
    handleAnnotationTool(button) {
        const tool = button.querySelector('i').className;
        console.log('Annotation tool selected:', tool);
        
        // Implement annotation tool functionality
        // This would depend on the specific viewer being used
    }

    /**
     * On dashboard load
     */
    onDashboardLoad() {
        console.log('Dashboard loaded successfully');
        this.currentViewer = 'loaded';
    }

    /**
     * On dashboard error
     */
    onDashboardError() {
        console.error('Dashboard failed to load');
        this.showErrorDashboard('Failed to load dashboard. Please try again.');
    }

    /**
     * Check processing status
     */
    async checkProcessingStatus(datasetId) {
        try {
            // Helper function to get API base path
            const getApiBasePath = () => {
                const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                return isLocal ? '/api' : '/portal/api';
            };
            const response = await fetch(`${getApiBasePath()}/dataset-status.php?dataset_id=${datasetId}`, {
                credentials: 'include'  // Include cookies for authentication
            });
            
            if (!response.ok) {
                console.error(`Error checking dataset status: ${response.status} ${response.statusText}`);
                return;
            }
            
            const data = await response.json();
            
            if (data.status === 'ready') {
                location.reload();
            } else {
                alert('Dataset is still processing. Please wait.');
            }
        } catch (error) {
            console.error('Error checking status:', error);
            alert('Error checking status. Please try again.');
        }
    }
}

// Initialize viewer manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.viewerManager = new ViewerManager();
});

// Export functions for global access
window.loadDashboard = function(datasetId, dashboardType) {
    if (window.viewerManager && window.datasetManager && window.datasetManager.currentDataset) {
        window.viewerManager.loadDashboard(
            window.datasetManager.currentDataset.id,
            window.datasetManager.currentDataset.name,
            window.datasetManager.currentDataset.uuid,
            window.datasetManager.currentDataset.server,
            dashboardType
        );
    }
};

window.refreshDashboard = function() {
    if (window.viewerManager) {
        window.viewerManager.refreshDashboard();
    }
};

window.checkProcessingStatus = function(datasetId) {
    if (window.viewerManager) {
        window.viewerManager.checkProcessingStatus(datasetId);
    }
};
