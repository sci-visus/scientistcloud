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
        this.loadDatasets();
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
            const response = await fetch('/api/datasets.php');
            const data = await response.json();
            
            if (data.success) {
                this.datasets = data.datasets;
                this.folders = data.folders;
                this.renderDatasets();
            } else {
                console.error('Failed to load datasets:', data.error);
                this.showError('Failed to load datasets');
            }
        } catch (error) {
            console.error('Error loading datasets:', error);
            this.showError('Error loading datasets');
        }
    }

    /**
     * Render datasets in the UI
     */
    renderDatasets() {
        const container = document.querySelector('.dataset-list');
        if (!container) return;

        // Group datasets by folder
        const groupedDatasets = this.groupDatasetsByFolder();
        
        let html = '';
        
        // My Datasets
        html += this.renderDatasetGroup('My Datasets', groupedDatasets['my'], 'myDatasets');
        
        // Shared Datasets
        html += this.renderDatasetGroup('Shared with Me', groupedDatasets['shared'], 'sharedDatasets');
        
        // Team Datasets
        if (groupedDatasets['team'].length > 0) {
            html += this.renderDatasetGroup('Team Datasets', groupedDatasets['team'], 'teamDatasets');
        }
        
        container.innerHTML = html;
    }

    /**
     * Group datasets by folder
     */
    groupDatasetsByFolder() {
        const grouped = {
            'my': [],
            'shared': [],
            'team': []
        };

        this.datasets.forEach(dataset => {
            if (dataset.shared_with) {
                grouped.shared.push(dataset);
            } else if (dataset.team_id) {
                grouped.team.push(dataset);
            } else {
                grouped.my.push(dataset);
            }
        });

        return grouped;
    }

    /**
     * Render a dataset group
     */
    renderDatasetGroup(title, datasets, id) {
        if (datasets.length === 0) {
            return `
                <div class="dataset-section">
                    <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#${id}">
                        <span class="arrow-icon" id="arrow-${id}">&#9656;</span>${title}
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
                    <span class="arrow-icon" id="arrow-${id}">&#9656;</span>${title}
                </a>
                <div class="collapse ps-4 w-100" id="${id}">
        `;

        datasets.forEach(dataset => {
            html += this.renderDatasetItem(dataset);
        });

        html += `
                </div>
            </div>
        `;

        return html;
    }

    /**
     * Render a single dataset item
     */
    renderDatasetItem(dataset) {
        const statusColor = this.getStatusColor(dataset.status);
        const fileIcon = this.getFileIcon(dataset.sensor);
        
        return `
            <div class="dataset-item" data-dataset-id="${dataset.id}">
                <a class="nav-link dataset-link" href="javascript:void(0)" 
                   data-dataset-id="${dataset.id}"
                   data-dataset-name="${dataset.name}"
                   data-dataset-uuid="${dataset.uuid}"
                   data-dataset-server="${dataset.google_drive_link ? 'true' : 'false'}">
                    <i class="${fileIcon} me-2"></i>
                    <span class="dataset-name">${dataset.name}</span>
                    <span class="badge bg-${statusColor} ms-2">${dataset.status}</span>
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
            const response = await fetch('/api/share-dataset.php', {
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
                const response = await fetch('/api/delete-dataset.php', {
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
        const bytes = Math.max(bytes, 0);
        const pow = Math.floor((bytes ? Math.log(bytes) : 0) / Math.log(1024));
        const pow = Math.min(pow, units.length - 1);
        
        const bytes = bytes / Math.pow(1024, pow);
        
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
