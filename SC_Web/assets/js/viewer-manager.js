/**
 * Viewer Manager JavaScript
 * Handles viewer operations and dashboard management
 */

class ViewerManager {
    constructor() {
        this.currentViewer = null;
        this.viewers = {}; // Will be loaded from API
        this.defaultViewers = {
            'openvisus': {
                name: 'OpenVisus Explorer',
                type: 'openvisus',
                url_template: '/viewer/openvisus.php?dataset={uuid}&server={server}',
                supported_formats: ['tiff', 'hdf5', 'nexus'],
                description: 'Interactive 3D volume rendering with OpenVisus'
            }
        };
        this.initialize();
    }
    
    /**
     * Load dashboards from API
     */
    async loadDashboards() {
        try {
            const response = await fetch('/portal/api/dashboards.php');
            
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
                        this.viewers[dashboard.id] = {
                            name: dashboard.display_name || dashboard.name,
                            type: dashboard.type || dashboard.id,
                            url_template: dashboard.url_template || dashboard.nginx_path + '?dataset={uuid}&server={server}',
                            supported_formats: [], // Will be determined from dataset type
                            description: dashboard.description || dashboard.display_name,
                            nginx_path: dashboard.nginx_path,
                            port: dashboard.port
                        };
                    }
                });
                
                // Merge with default viewers (for backward compatibility)
                this.viewers = { ...this.defaultViewers, ...this.viewers };
                
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
        Object.values(this.viewers).forEach(viewer => {
            const option = document.createElement('option');
            option.value = viewer.type;
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

        // Dashboard selector change
        const dashboardSelector = document.getElementById('dashboardSelector');
        if (dashboardSelector) {
            dashboardSelector.addEventListener('change', (e) => {
                this.handleDashboardChange(e.target.value);
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
            viewerType: document.getElementById('viewerType')?.value || 'openvisus',
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
    async loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, dashboardType = 'openvisus') {
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
            // Check if dataset is ready
            const status = await this.checkDatasetStatus(datasetId);
            
            if (status === 'ready') {
                // Load the dashboard
                await this.loadDashboardContent(datasetId, datasetName, datasetUuid, datasetServer, dashboardType);
            } else if (status === 'processing') {
                this.showProcessingDashboard(datasetName);
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
    async checkDatasetStatus(datasetId) {
        try {
            const response = await fetch(`/api/dataset-status.php?dataset_id=${datasetId}`);
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

        const viewer = this.viewers[dashboardType];
        if (!viewer) {
            this.showErrorDashboard('Unknown viewer type');
            return;
        }

        // Generate viewer URL
        const viewerUrl = this.generateViewerUrl(datasetUuid, datasetServer, viewer.url_template);
        
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
        dashboardHeader.innerHTML = `
            <h4>${datasetName}</h4>
            <div class="dashboard-controls">
                <select id="dashboardSelector" class="form-select form-select-sm">
                    ${this.generateDashboardOptions(datasetId)}
                </select>
                <button class="btn btn-sm btn-outline-secondary" onclick="refreshDashboard()">
                    <i class="fas fa-refresh"></i>
                </button>
            </div>
        `;
        
        const dashboardContent = document.createElement('div');
        dashboardContent.className = 'dashboard-content';
        dashboardContent.appendChild(iframe);
        
        dashboardContainer.appendChild(dashboardHeader);
        dashboardContainer.appendChild(dashboardContent);
        
        viewerContainer.innerHTML = '';
        viewerContainer.appendChild(dashboardContainer);
        
        // Setup dashboard selector
        this.setupDashboardSelector(datasetId);
    }

    /**
     * Generate viewer URL
     */
    generateViewerUrl(datasetUuid, datasetServer, urlTemplate) {
        return urlTemplate
            .replace('{uuid}', datasetUuid)
            .replace('{server}', datasetServer);
    }

    /**
     * Generate dashboard options
     */
    generateDashboardOptions(datasetId) {
        let options = '';
        
        Object.values(this.viewers).forEach(viewer => {
            options += `<option value="${viewer.type}">${viewer.name}</option>`;
        });
        
        return options;
    }

    /**
     * Setup dashboard selector
     */
    setupDashboardSelector(datasetId) {
        const selector = document.getElementById('dashboardSelector');
        if (selector) {
            selector.addEventListener('change', (e) => {
                this.handleDashboardChange(e.target.value);
            });
        }
    }

    /**
     * Show processing dashboard
     */
    showProcessingDashboard(datasetName) {
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
            const response = await fetch(`/api/dataset-status.php?dataset_id=${datasetId}`);
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
