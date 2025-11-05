/**
 * Dataset Manager JavaScript
 * Handles dataset operations and interactions
 */

class DatasetManager {
    constructor() {
        this.currentDataset = null;
        this.datasets = [];
        this.folders = [];
        this.initialize();
    }

    /**
     * Initialize the dataset manager
     */
    initialize() {
        this.setupEventListeners();
        // Only load datasets if PHP hasn't already rendered them
        // Check if PHP has already rendered the dataset list (look for folder-details elements)
        const existingFolders = document.querySelectorAll('.folder-details').length;
        const existingDatasets = document.querySelectorAll('.dataset-link').length;
        
        if (existingFolders > 0 || existingDatasets > 0) {
            console.log(`Using PHP-rendered dataset list (${existingFolders} folders, ${existingDatasets} datasets)`);
            // Don't load/replace PHP content - just attach event listeners
            this.attachEventListenersToExisting();
        } else {
            // No PHP content found, load datasets via JavaScript
            console.log('No PHP-rendered content found, loading datasets via JavaScript');
            this.loadDatasets();
        }
    }

    /**
     * Attach event listeners to existing PHP-rendered dataset list
     */
    attachEventListenersToExisting() {
        // Event listeners are already set up by setupEventListeners()
        // The click handlers in main.js and dataset_list.php should handle this
        // Just ensure we have access to datasets for other operations
        console.log('Event listeners attached to PHP-rendered dataset list');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Dataset selection
        document.addEventListener('click', (e) => {
            if (e.target.closest('.dataset-link')) {
                e.preventDefault();
                this.handleDatasetSelection(e.target.closest('.dataset-link'));
            }
        });

        // Dataset actions
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="view"]')) {
                e.preventDefault();
                this.viewDataset(e.target.closest('[data-action="view"]').dataset.datasetId);
            }
            
            if (e.target.closest('[data-action="share"]')) {
                e.preventDefault();
                this.shareDataset(e.target.closest('[data-action="share"]').dataset.datasetId);
            }
            
            if (e.target.closest('[data-action="delete"]')) {
                e.preventDefault();
                this.deleteDataset(e.target.closest('[data-action="delete"]').dataset.datasetId);
            }
        });

        // Search functionality
        const searchInput = document.getElementById('datasetSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterDatasets(e.target.value);
            });
        }

        // Sort functionality
        const sortSelect = document.getElementById('datasetSort');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.sortDatasets(e.target.value);
            });
        }
    }

    /**
     * Load datasets from server
     */
    async loadDatasets() {
        try {
            const response = await fetch('/portal/api/datasets.php');
            
            // Get response text first to check for errors
            const responseText = await response.text();
            
            // Check if response is valid JSON
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (jsonError) {
                console.error('Invalid JSON response:', responseText.substring(0, 200));
                console.error('JSON parse error:', jsonError);
                throw new Error('Invalid JSON response from server: ' + jsonError.message);
            }
            
            if (data.success) {
                // Handle the new structure: datasets.my, datasets.shared, datasets.team
                if (data.datasets && typeof data.datasets === 'object') {
                    // Flatten the datasets structure for easier access
                    this.datasets = {
                        my: data.datasets.my || [],
                        shared: data.datasets.shared || [],
                        team: data.datasets.team || []
                    };
                } else {
                    // Fallback for old structure
                    this.datasets = {
                        my: Array.isArray(data.datasets) ? data.datasets : [],
                        shared: [],
                        team: []
                    };
                }
                
                // Debug logging
                console.log('Datasets loaded:', {
                    my: this.datasets.my.length,
                    shared: this.datasets.shared.length,
                    team: this.datasets.team.length,
                    total: this.datasets.my.length + this.datasets.shared.length + this.datasets.team.length
                });
                
                if (this.datasets.my.length > 0) {
                    console.log('First my dataset:', this.datasets.my[0]);
                }
                
                this.folders = data.folders || [];
                this.renderDatasets();
            } else {
                console.error('Failed to load datasets:', data.error);
                this.showError('Failed to load datasets: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error loading datasets:', error);
            this.showError('Error loading datasets: ' + error.message);
        }
    }

    /**
     * Render datasets in the UI
     */
    renderDatasets() {
        // Try to find the dataset-list container
        let container = document.querySelector('.dataset-list');
        
        // Fallback: try to find the nav.panel-content or any container in the sidebar
        if (!container) {
            const sidebar = document.querySelector('#folderSidebar');
            if (sidebar) {
                container = sidebar.querySelector('nav.panel-content') || sidebar.querySelector('.panel-content');
            }
        }
        
        if (!container) {
            console.error('Dataset list container not found! Looked for .dataset-list, nav.panel-content, or .panel-content');
            // Try to create one
            const sidebar = document.querySelector('#folderSidebar');
            if (sidebar) {
                const nav = sidebar.querySelector('nav');
                if (nav) {
                    container = document.createElement('div');
                    container.className = 'dataset-list';
                    nav.innerHTML = '';
                    nav.appendChild(container);
                    console.log('Created dataset-list container');
                }
            }
        }
        
        if (!container) {
            console.error('Could not create or find dataset list container!');
            return;
        }
        
        console.log('Rendering datasets:', {
            my: this.datasets.my?.length || 0,
            shared: this.datasets.shared?.length || 0,
            team: this.datasets.team?.length || 0
        });

        // Group datasets by folder
        const groupedDatasets = this.groupDatasetsByFolder();
        
        let html = '';
        
        // My Datasets
        html += this.renderDatasetGroup('My Datasets', groupedDatasets['my'], 'myDatasets');
        
        // Shared Datasets
        html += this.renderDatasetGroup('Shared with Me', groupedDatasets['shared'], 'sharedDatasets');
        
        // Team Datasets
        const teamRootCount = groupedDatasets['team'].root?.length || 0;
        const teamFolderCount = Object.values(groupedDatasets['team'].folders || {}).reduce((sum, arr) => sum + arr.length, 0);
        if (teamRootCount > 0 || teamFolderCount > 0) {
            html += this.renderDatasetGroup('Team Datasets', groupedDatasets['team'], 'teamDatasets');
        }
        
        container.innerHTML = html;
    }

    /**
     * Group datasets by folder
     * Returns datasets grouped by folder_uuid for each category (my, shared, team)
     */
    groupDatasetsByFolder() {
        const result = {
            'my': { folders: {}, root: [] },
            'shared': { folders: {}, root: [] },
            'team': { folders: {}, root: [] }
        };

        // Process each category
        ['my', 'shared', 'team'].forEach(category => {
            const datasets = this.datasets[category] || [];
            
            datasets.forEach(dataset => {
                if (!dataset) return;
                
                // Extract folder_uuid - check both direct field and metadata
                const folderUuid = dataset.folder_uuid || 
                                   (dataset.metadata && dataset.metadata.folder_uuid) || 
                                   null;
                
                // Normalize empty/null values - treat as root level
                if (folderUuid === null || folderUuid === '' || 
                    folderUuid === 'No_Folder_Selected' || folderUuid === 'root') {
                    result[category].root.push(dataset);
                } else {
                    // Group by folder_uuid
                    if (!result[category].folders[folderUuid]) {
                        result[category].folders[folderUuid] = [];
                    }
                    result[category].folders[folderUuid].push(dataset);
                }
            });
        });

        return result;
    }

    /**
     * Render a dataset group with folder support
     */
    renderDatasetGroup(title, groupedData, id) {
        // groupedData is { folders: {}, root: [] }
        const rootDatasets = groupedData.root || [];
        const folders = groupedData.folders || {};
        const totalCount = rootDatasets.length + Object.values(folders).reduce((sum, arr) => sum + arr.length, 0);

        if (totalCount === 0) {
            console.log(`No datasets to render for ${title} (id: ${id})`);
            return `
                <div class="dataset-section">
                    <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#${id}">
                        <span class="arrow-icon" id="arrow-${id}">&#9656;</span>${title} (0)
                    </a>
                    <div class="collapse ps-4 w-100" id="${id}">
                        <p class="text-muted">No datasets found.</p>
                    </div>
                </div>
            `;
        }

        let html = `
            <div class="dataset-section">
                <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#${id}">
                    <span class="arrow-icon" id="arrow-${id}">&#9656;</span>${title} (${totalCount})
                </a>
                <div class="collapse show ps-4 w-100" id="${id}">
        `;

        // Render root level datasets (no folder)
        rootDatasets.forEach((dataset, index) => {
            if (!dataset) {
                console.warn(`Root dataset at index ${index} is null or undefined`);
                return;
            }
            html += `<div class="dataset-item" data-dataset-id="${dataset.id || dataset.uuid || 'unknown'}">`;
            html += this.renderDatasetItem(dataset);
            html += `</div>`;
        });

        // Render folder groups
        Object.keys(folders).forEach(folderUuid => {
            const folderDatasets = folders[folderUuid];
            if (!folderDatasets || folderDatasets.length === 0) return;

            html += `
                <div class="folder-group">
                    <details class="folder-details" open>
                        <summary class="folder-summary">
                            <span class="arrow-icon">&#9656;</span>
                            <span class="folder-name">${this.escapeHtml(folderUuid)}</span>
                            <span class="badge bg-secondary ms-2">${folderDatasets.length}</span>
                        </summary>
                        <ul class="nested folder-datasets">
            `;

            folderDatasets.forEach((dataset, index) => {
                if (!dataset) {
                    console.warn(`Folder dataset at index ${index} is null or undefined`);
                    return;
                }
                html += `<li class="dataset-item" data-dataset-id="${dataset.id || dataset.uuid || 'unknown'}">`;
                html += this.renderDatasetItem(dataset);
                html += `</li>`;
            });

            html += `
                        </ul>
                    </details>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;

        return html;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Render a single dataset item
     */
    renderDatasetItem(dataset) {
        // Defensive checks for required fields
        if (!dataset) {
            console.error('renderDatasetItem: dataset is null or undefined');
            return '';
        }
        
        const datasetId = dataset.id || dataset.uuid || 'unknown';
        const datasetName = dataset.name || 'Unnamed Dataset';
        const datasetUuid = dataset.uuid || dataset.id || '';
        const status = dataset.status || 'unknown';
        const sensor = dataset.sensor || 'Unknown';
        
        // Determine server flag: true if link includes 'http' but is NOT a Google Drive link
        // Check download_url, viewer_url, or google_drive_link
        const link = dataset.download_url || dataset.viewer_url || dataset.google_drive_link || '';
        const datasetServer = (link.includes('http') && !link.includes('drive.google.com')) ? 'true' : 'false';
        
        const statusColor = this.getStatusColor(status);
        const fileIcon = this.getFileIcon(sensor);
        
        return `
            <div class="dataset-item" data-dataset-id="${datasetId}">
                <a class="nav-link dataset-link" href="javascript:void(0)" 
                   data-dataset-id="${datasetId}"
                   data-dataset-name="${datasetName}"
                   data-dataset-uuid="${datasetUuid}"
                   data-dataset-server="${datasetServer}">
                    <i class="${fileIcon} me-2"></i>
                    <span class="dataset-name">${datasetName}</span>
                    <span class="badge bg-${statusColor} ms-2">${status}</span>
                </a>
            </div>
        `;
    }

    /**
     * Handle dataset selection
     */
    handleDatasetSelection(datasetLink) {
        const datasetId = datasetLink.dataset.datasetId;
        const datasetName = datasetLink.dataset.datasetName;
        const datasetUuid = datasetLink.dataset.datasetUuid;
        const datasetServer = datasetLink.dataset.datasetServer;

        // Update active state
        document.querySelectorAll('.dataset-link').forEach(link => {
            link.classList.remove('active');
        });
        datasetLink.classList.add('active');

        // Store current dataset
        this.currentDataset = {
            id: datasetId,
            name: datasetName,
            uuid: datasetUuid,
            server: datasetServer
        };

        // Load dataset details
        this.loadDatasetDetails(datasetId);

        // Load dashboard
        this.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);

        console.log('Dataset selected:', this.currentDataset);
    }

    /**
     * Load dataset details
     */
    async loadDatasetDetails(datasetId) {
        const detailsContainer = document.getElementById('datasetDetails');
        if (!detailsContainer) return;

        // Show loading state
        detailsContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading details...</p>
            </div>
        `;

        try {
            const response = await fetch(`/api/dataset-details.php?dataset_id=${datasetId}`);
            const data = await response.json();

            if (data.success) {
                this.displayDatasetDetails(data.dataset);
            } else {
                this.displayErrorDetails(data.error);
            }
        } catch (error) {
            console.error('Error loading dataset details:', error);
            this.displayErrorDetails('Failed to load dataset details');
        }
    }

    /**
     * Display dataset details
     */
    displayDatasetDetails(dataset) {
        const detailsContainer = document.getElementById('datasetDetails');
        if (!detailsContainer) return;

        const html = `
            <div class="dataset-details">
                <h6><i class="fas fa-info-circle"></i> ${dataset.name}</h6>
                <div class="details-grid">
                    <div class="detail-item">
                        <span class="detail-label">UUID:</span>
                        <span class="detail-value">${dataset.uuid}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Size:</span>
                        <span class="detail-value">${this.formatFileSize(dataset.data_size)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Status:</span>
                        <span class="badge bg-${this.getStatusColor(dataset.status)}">${dataset.status}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Sensor:</span>
                        <span class="detail-value">${dataset.sensor}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">${this.formatDate(dataset.created_at)}</span>
                    </div>
                    ${dataset.dimensions ? `
                    <div class="detail-item">
                        <span class="detail-label">Dimensions:</span>
                        <span class="detail-value">${dataset.dimensions}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="dataset-actions mt-3">
                    <button class="btn btn-sm btn-primary" data-action="view" data-dataset-id="${dataset.id}">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" data-action="share" data-dataset-id="${dataset.id}">
                        <i class="fas fa-share"></i> Share
                    </button>
                    <button class="btn btn-sm btn-outline-danger" data-action="delete" data-dataset-id="${dataset.id}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;

        detailsContainer.innerHTML = html;
    }

    /**
     * Display error details
     */
    displayErrorDetails(error) {
        const detailsContainer = document.getElementById('datasetDetails');
        if (!detailsContainer) return;

        detailsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i>
                <strong>Error:</strong> ${error}
            </div>
        `;
    }

    /**
     * Load dashboard
     */
    loadDashboard(datasetId, datasetName, datasetUuid, datasetServer) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5 class="mt-3">Loading Dashboard</h5>
                <p class="text-muted">Preparing visualization for ${datasetName}</p>
            </div>
        `;

        // Load dashboard
        const url = new URL(window.location);
        url.searchParams.set('dataset_id', datasetId);
        url.searchParams.set('dashboard', 'openvisus'); // Default dashboard

        fetch(url.toString())
            .then(response => response.text())
            .then(html => {
                // Extract the dashboard content
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const dashboardContent = doc.querySelector('.dashboard-content');

                if (dashboardContent) {
                    viewerContainer.innerHTML = dashboardContent.outerHTML;
                } else {
                    viewerContainer.innerHTML = html;
                }
            })
            .catch(error => {
                console.error('Error loading dashboard:', error);
                viewerContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle"></i>
                        <strong>Error:</strong> Failed to load dashboard
                    </div>
                `;
            });
    }

    /**
     * View dataset
     */
    viewDataset(datasetId) {
        if (this.currentDataset) {
            this.loadDashboard(this.currentDataset.id, this.currentDataset.name, this.currentDataset.uuid, this.currentDataset.server);
        }
    }

    /**
     * Share dataset
     */
    async shareDataset(datasetId) {
        try {
            const response = await fetch('/portal/api/share-dataset.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ dataset_id: datasetId })
            });

            const data = await response.json();

            if (data.success) {
                alert('Dataset shared successfully');
            } else {
                alert('Error sharing dataset: ' + data.error);
            }
        } catch (error) {
            console.error('Error sharing dataset:', error);
            alert('Error sharing dataset');
        }
    }

    /**
     * Delete dataset
     */
    async deleteDataset(datasetId) {
        if (confirm('Are you sure you want to delete this dataset? This action cannot be undone.')) {
            try {
                const response = await fetch('/portal/api/delete-dataset.php', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ dataset_id: datasetId })
                });

                const data = await response.json();

                if (data.success) {
                    alert('Dataset deleted successfully');
                    location.reload();
                } else {
                    alert('Error deleting dataset: ' + data.error);
                }
            } catch (error) {
                console.error('Error deleting dataset:', error);
                alert('Error deleting dataset');
            }
        }
    }

    /**
     * Filter datasets
     */
    filterDatasets(searchTerm) {
        const datasetItems = document.querySelectorAll('.dataset-item');
        
        datasetItems.forEach(item => {
            const datasetName = item.querySelector('.dataset-name').textContent.toLowerCase();
            const matches = datasetName.includes(searchTerm.toLowerCase());
            
            item.style.display = matches ? 'block' : 'none';
        });
    }

    /**
     * Sort datasets
     */
    sortDatasets(sortBy) {
        // Implement sorting logic
        console.log('Sorting datasets by:', sortBy);
    }

    /**
     * Get status color
     */
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

    /**
     * Get file icon
     */
    getFileIcon(sensor) {
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

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes == 0) return '0 B';
        
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        bytes = Math.max(bytes, 0);
        let pow = Math.floor((bytes ? Math.log(bytes) : 0) / Math.log(1024));
        pow = Math.min(pow, units.length - 1);
        
        bytes = bytes / Math.pow(1024, pow);
        
        return Math.round(bytes * 100) / 100 + ' ' + units[pow];
    }

    /**
     * Format date
     */
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error(message);
        // You can implement a toast notification or alert here
        alert(message);
    }
}

// Initialize dataset manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.datasetManager = new DatasetManager();
});
