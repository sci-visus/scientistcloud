/**
 * Public Dataset Manager JavaScript
 * Handles public dataset operations (read-only, no authentication required)
 */

// Helper function to get API base path
function getApiBasePath() {
    if (window.API_BASE_PATH) {
        return window.API_BASE_PATH;
    }
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    return isLocal ? '/api' : '/portal/api';
}

class PublicDatasetManager {
    constructor() {
        this.currentDataset = null;
        this.datasets = [];
        this.folders = [];
        this.isSelectingDataset = false;
        this.initialize();
    }

    /**
     * Initialize the public dataset manager
     */
    initialize() {
        this.setupEventListeners();
        this.loadDatasets();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Refresh datasets button
        const refreshBtn = document.getElementById('refreshDatasetsBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                const icon = refreshBtn.querySelector('i');
                if (icon) {
                    icon.classList.add('fa-spin');
                }
                refreshBtn.disabled = true;
                try {
                    await this.loadDatasets();
                    console.log('✅ Public datasets refreshed');
                } catch (error) {
                    console.error('Error refreshing public datasets:', error);
                } finally {
                    if (icon) {
                        icon.classList.remove('fa-spin');
                    }
                    refreshBtn.disabled = false;
                }
            });
        }

        // Dataset selection
        document.addEventListener('click', (e) => {
            if (e.target.closest('.dataset-link')) {
                e.preventDefault();
                const datasetLink = e.target.closest('.dataset-link');
                this.handleDatasetSelection(datasetLink);
            }
        });
    }

    /**
     * Load public datasets from server
     */
    async loadDatasets() {
        try {
            const cacheBuster = new Date().getTime();
            const response = await fetch(`${getApiBasePath()}/public-datasets.php?t=${cacheBuster}`, {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });
            
            const responseText = await response.text();
            
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (e) {
                console.error('Invalid JSON response:', responseText.substring(0, 500));
                throw new Error('Invalid response from server');
            }
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load public datasets');
            }
            
            // Public datasets are in data.datasets.public
            this.datasets = data.datasets.public || [];
            this.folders = data.folders || [];
            
            console.log(`Loaded ${this.datasets.length} public datasets`);
            
            // Render dataset list
            this.renderDatasetList();
            
        } catch (error) {
            console.error('Error loading public datasets:', error);
            const listContainer = document.getElementById('publicDatasetList');
            if (listContainer) {
                listContainer.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle"></i> 
                        Failed to load public datasets: ${this.escapeHtml(error.message)}
                    </div>
                `;
            }
        }
    }

    /**
     * Render dataset list
     */
    renderDatasetList() {
        const listContainer = document.getElementById('publicDatasetList');
        if (!listContainer) return;
        
        if (this.datasets.length === 0) {
            listContainer.innerHTML = `
                <div class="dataset-section">
                    <p class="text-center text-muted">No public datasets available.</p>
                </div>
            `;
            return;
        }
        
        // Group datasets by folder
        const groupedDatasets = {};
        const rootDatasets = [];
        
        this.datasets.forEach(dataset => {
            const folderUuid = dataset.folder_uuid || 'root';
            if (folderUuid === 'root' || !folderUuid) {
                rootDatasets.push(dataset);
            } else {
                if (!groupedDatasets[folderUuid]) {
                    groupedDatasets[folderUuid] = [];
                }
                groupedDatasets[folderUuid].push(dataset);
            }
        });
        
        let html = '<div class="dataset-section">';
        html += '<a class="nav-link" data-bs-toggle="collapse" data-bs-target="#publicDatasets">';
        html += '<span class="arrow-icon" id="arrow-public">&#9656;</span>Public Datasets</a>';
        html += '<div class="collapse show ps-4 w-100" id="publicDatasets">';
        
        // Root level datasets
        rootDatasets.forEach(dataset => {
            html += this.renderDatasetItem(dataset);
        });
        
        // Folder grouped datasets
        Object.keys(groupedDatasets).forEach(folderUuid => {
            html += `<div class="folder-group">`;
            html += `<details class="folder-details" open>`;
            html += `<summary class="folder-summary">`;
            html += `<span class="arrow-icon">&#9656;</span>`;
            html += `<span class="folder-name">${this.escapeHtml(folderUuid)}</span>`;
            html += `<span class="badge bg-secondary ms-2">${groupedDatasets[folderUuid].length}</span>`;
            html += `</summary>`;
            html += `<ul class="nested folder-datasets">`;
            groupedDatasets[folderUuid].forEach(dataset => {
                html += `<li>${this.renderDatasetItem(dataset)}</li>`;
            });
            html += `</ul>`;
            html += `</details>`;
            html += `</div>`;
        });
        
        html += '</div></div>';
        
        listContainer.innerHTML = html;
    }

    /**
     * Render a single dataset item
     */
    renderDatasetItem(dataset) {
        const statusColor = this.getStatusColor(dataset.status);
        const fileIcon = this.getFileFormatIcon(dataset.sensor);
        const datasetId = dataset.id || dataset.uuid;
        
        return `
            <div class="dataset-item" data-dataset-id="${this.escapeHtml(datasetId)}">
                <div class="dataset-header">
                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                       data-dataset-id="${this.escapeHtml(datasetId)}"
                       data-dataset-name="${this.escapeHtml(dataset.name || '')}"
                       data-dataset-uuid="${this.escapeHtml(dataset.uuid || datasetId)}"
                       data-dataset-server="${dataset.server || 'false'}">
                        <i class="${fileIcon} me-2"></i>
                        <span class="dataset-name">${this.escapeHtml(dataset.name || 'Unnamed Dataset')}</span>
                        <span class="badge bg-${statusColor} ms-2">${this.escapeHtml(dataset.status || 'unknown')}</span>
                    </a>
                </div>
            </div>
        `;
    }

    /**
     * Handle dataset selection
     */
    async handleDatasetSelection(datasetLink) {
        if (this.isSelectingDataset) {
            console.log('⏭️ Dataset selection already in progress');
            return;
        }
        
        this.isSelectingDataset = true;
        
        try {
            const datasetId = datasetLink.dataset?.datasetId;
            const datasetName = datasetLink.dataset?.datasetName;
            const datasetUuid = datasetLink.dataset?.datasetUuid;
            const datasetServer = datasetLink.dataset?.datasetServer;
            
            if (!datasetId) {
                console.error('Dataset ID is missing');
                return;
            }
            
            // Update active state
            document.querySelectorAll('.dataset-link').forEach(link => {
                link.classList.remove('active');
            });
            datasetLink.classList.add('active');
            
            // Load dataset details
            await this.loadDatasetDetails(datasetId);
            
            // Load dashboard
            if (window.viewerManager) {
                window.viewerManager.currentDataset = {
                    id: datasetId,
                    name: datasetName,
                    uuid: datasetUuid,
                    server: datasetServer
                };
                
                const viewerType = document.getElementById('viewerType');
                const dashboardType = viewerType ? viewerType.value : (Object.keys(window.viewerManager.viewers)[0] || 'OpenVisusSlice');
                
                window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, dashboardType);
            }
            
        } catch (error) {
            console.error('Error selecting dataset:', error);
        } finally {
            this.isSelectingDataset = false;
        }
    }

    /**
     * Load dataset details
     */
    async loadDatasetDetails(datasetId) {
        try {
            const response = await fetch(`${getApiBasePath()}/public-dataset-details.php?dataset_id=${encodeURIComponent(datasetId)}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load dataset details');
            }
            
            this.displayDatasetDetails(data.dataset);
            
        } catch (error) {
            console.error('Error loading dataset details:', error);
            const detailsContainer = document.getElementById('datasetDetails');
            if (detailsContainer) {
                detailsContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle"></i> 
                        Failed to load dataset details: ${this.escapeHtml(error.message)}
                    </div>
                `;
            }
        }
    }

    /**
     * Display dataset details (read-only, no edit/delete/retry)
     */
    displayDatasetDetails(dataset) {
        const detailsContainer = document.getElementById('datasetDetails');
        if (!detailsContainer) return;
        
        // Check if dataset is publicly downloadable
        const isDownloadable = dataset.is_downloadable === 'public';
        
        const html = `
            <div class="dataset-details">
                <h6><i class="fas fa-info-circle"></i> Dataset Details</h6>
                
                <div class="mb-2">
                    <h6 class="text-primary mb-2">${this.escapeHtml(dataset.name || 'Unnamed Dataset')}</h6>
                </div>
                
                ${isDownloadable ? `
                <div class="dataset-actions mb-3 pb-2 border-bottom">
                    <button type="button" class="btn btn-sm btn-primary w-100" data-action="download" data-dataset-id="${dataset.id || dataset.uuid}">
                        <i class="fas fa-download"></i> Download Dataset
                    </button>
                </div>
                ` : ''}
                
                <div class="dataset-view-mode">
                    <div class="detail-item mb-2">
                        <span class="detail-label">Name:</span>
                        <span class="detail-value">${this.escapeHtml(dataset.name || '')}</span>
                    </div>
                    
                    ${dataset.tags ? `
                    <div class="detail-item mb-2">
                        <span class="detail-label">Tags:</span>
                        <span class="detail-value">${this.escapeHtml(Array.isArray(dataset.tags) ? dataset.tags.join(', ') : dataset.tags)}</span>
                    </div>
                    ` : ''}
                    
                    ${dataset.dimensions ? `
                    <div class="detail-item mb-2">
                        <span class="detail-label">Dimensions:</span>
                        <span class="detail-value">${this.escapeHtml(dataset.dimensions)}</span>
                    </div>
                    ` : ''}
                    
                    <div class="detail-item mb-2">
                        <span class="detail-label">Size:</span>
                        <span class="detail-value">${this.formatFileSize(dataset.data_size || 0)}</span>
                    </div>
                    
                    ${dataset.created_at || dataset.time ? `
                    <div class="detail-item mb-2">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">${this.formatDate(dataset.created_at || dataset.time)}</span>
                    </div>
                    ` : ''}
                    
                    ${dataset.sensor ? `
                    <div class="detail-item mb-2">
                        <span class="detail-label">Sensor:</span>
                        <span class="detail-value">${this.escapeHtml(dataset.sensor)}</span>
                    </div>
                    ` : ''}
                    
                    <div class="detail-item mb-2">
                        <span class="detail-label">Status:</span>
                        <span class="badge bg-${this.getStatusColor(dataset.status)}">${this.escapeHtml(dataset.status || 'unknown')}</span>
                    </div>
                    
                    ${dataset.description ? `
                    <div class="detail-item mb-2">
                        <span class="detail-label">Description:</span>
                        <span class="detail-value">${this.escapeHtml(dataset.description)}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        detailsContainer.innerHTML = html;
        
        // Attach download button handler
        const downloadBtn = detailsContainer.querySelector('[data-action="download"]');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.downloadDataset(dataset.id || dataset.uuid);
            });
        }
    }

    /**
     * Download dataset (if publicly downloadable)
     */
    async downloadDataset(datasetId) {
        try {
            // Redirect to download endpoint
            window.location.href = `${getApiBasePath()}/dataset-file-serve.php?dataset_id=${encodeURIComponent(datasetId)}&action=download`;
        } catch (error) {
            console.error('Error downloading dataset:', error);
            alert('Failed to download dataset. Please try again.');
        }
    }

    /**
     * Helper functions
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatFileSize(bytes) {
        if (bytes == 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const pow = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, pow) * 100) / 100 + ' ' + units[Math.min(pow, units.length - 1)];
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    getStatusColor(status) {
        const colors = {
            'done': 'success',
            'Ready': 'success',
            'processing': 'warning',
            'error': 'danger',
            'pending': 'info'
        };
        return colors[status] || 'secondary';
    }

    getFileFormatIcon(sensor) {
        const icons = {
            'TIFF': 'fas fa-image',
            'TIFF_RGB': 'fas fa-image',
            'NETCDF': 'fas fa-database',
            'HDF5': 'fas fa-database',
            '4D_NEXUS': 'fas fa-cube',
            'RGB DRONE': 'fas fa-drone',
            'MapIR DRONE': 'fas fa-drone'
        };
        return icons[sensor] || 'fas fa-file';
    }
}

// Initialize public dataset manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.IS_PUBLIC_PORTAL) {
        window.publicDatasetManager = new PublicDatasetManager();
        console.log('Public Dataset Manager initialized');
    }
});

