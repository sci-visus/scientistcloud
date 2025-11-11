/**
 * Dataset Manager JavaScript
 * Handles dataset operations and interactions
 */

// Helper function to get API base path (detects local vs server)
function getApiBasePath() {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    return isLocal ? '/api' : '/portal/api';
}

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
            const response = await fetch(`${getApiBasePath()}/datasets.php`);
            
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
        
        // Attach event listeners after rendering
        this.attachDatasetEventListeners();
    }
    
    /**
     * Attach event listeners for dataset interactions
     * Uses event delegation to handle dynamically rendered elements
     */
    attachDatasetEventListeners() {
        // Use event delegation on the container to handle dynamically added elements
        const container = document.querySelector('.dataset-list');
        if (!container) return;
        
        // Remove existing listeners if any (by checking for a data attribute)
        if (container.dataset.listenersAttached === 'true') {
            return; // Already attached
        }
        container.dataset.listenersAttached = 'true';
        
        // Handle dataset clicks using event delegation
        container.addEventListener('click', (e) => {
            const link = e.target.closest('.dataset-link');
            if (link) {
                e.preventDefault();
                
                const datasetId = link.getAttribute('data-dataset-id');
                const datasetName = link.getAttribute('data-dataset-name');
                const datasetUuid = link.getAttribute('data-dataset-uuid');
                const datasetServer = link.getAttribute('data-dataset-server');
                
                console.log('Dataset clicked:', { datasetId, datasetName, datasetUuid, datasetServer });
                
                // Update active state
                document.querySelectorAll('.dataset-link').forEach((l) => {
                    l.classList.remove('active');
                });
                link.classList.add('active');
                
                // Validate required fields
                if (!datasetUuid) {
                    console.error('Dataset UUID is missing! Cannot load dashboard.');
                    alert('Error: Dataset UUID is missing. Please contact support.');
                    return;
                }
                
                // Store current dataset
                this.currentDataset = {
                    id: datasetId,
                    name: datasetName,
                    uuid: datasetUuid,
                    server: datasetServer
                };
                
                // Load dataset details
                if (typeof loadDatasetDetails === 'function') {
                    loadDatasetDetails(datasetId);
                }
                
                // Load dashboard using viewer manager
                if (window.viewerManager) {
                    const viewerType = document.getElementById('viewerType');
                    const dashboardType = viewerType ? viewerType.value : (Object.keys(window.viewerManager.viewers)[0] || 'OpenVisusSlice');
                    
                    console.log('Loading dashboard with UUID:', datasetUuid, 'dashboard type:', dashboardType);
                    window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, dashboardType);
                } else if (typeof loadDashboard === 'function') {
                    console.log('Using fallback loadDashboard with UUID:', datasetUuid);
                    loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
                } else {
                    console.error('No dashboard loader available');
                    alert('Error: Dashboard loader not available. Please refresh the page.');
                }
            }
            
            // Handle dataset files toggle using event delegation
            const toggleButton = e.target.closest('.dataset-files-toggle');
            if (toggleButton) {
                e.stopPropagation(); // Prevent dataset selection
                
                const datasetUuid = toggleButton.getAttribute('data-dataset-uuid');
                const filesContainer = document.getElementById('files-' + datasetUuid);
                
                if (!filesContainer) return;
                
                const isExpanded = filesContainer.style.display !== 'none';
                
                if (isExpanded) {
                    // Collapse
                    filesContainer.style.display = 'none';
                    toggleButton.classList.remove('expanded');
                    const chevron = toggleButton.querySelector('i');
                    if (chevron) {
                        chevron.style.transform = 'rotate(0deg)';
                    }
                } else {
                    // Expand
                    filesContainer.style.display = 'block';
                    toggleButton.classList.add('expanded');
                    const chevron = toggleButton.querySelector('i');
                    if (chevron) {
                        chevron.style.transform = 'rotate(90deg)';
                    }
                    
                    // Load files if not already loaded
                    const content = filesContainer.querySelector('.dataset-files-content');
                    if (content && (content.innerHTML.includes('Loading files') || content.innerHTML.trim() === '')) {
                        this.loadDatasetFilesIntoContainer(datasetUuid, content);
                    }
                }
            }
        });
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
            <div class="dataset-item" data-dataset-id="${datasetId}" data-dataset-uuid="${datasetUuid}">
                <div class="dataset-header">
                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                       data-dataset-id="${datasetId}"
                       data-dataset-name="${datasetName}"
                       data-dataset-uuid="${datasetUuid}"
                       data-dataset-server="${datasetServer}">
                        <i class="${fileIcon} me-2"></i>
                        <span class="dataset-name">${datasetName}</span>
                        <span class="badge bg-${statusColor} ms-2">${status}</span>
                    </a>
                    <button class="dataset-files-toggle" data-dataset-uuid="${datasetUuid}" title="Toggle files">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
                <div class="dataset-files" id="files-${datasetUuid}" style="display: none;">
                    <div class="dataset-files-content">
                        <p class="text-muted small">Loading files...</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Load dataset files structure into a specific container
     */
    async loadDatasetFilesIntoContainer(datasetUuid, container) {
        if (!datasetUuid || !container) {
            return;
        }

        // Show loading state
        container.innerHTML = `
            <div class="text-center py-2">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;

        try {
            const response = await fetch(`${getApiBasePath()}/dataset-files.php?dataset_uuid=${datasetUuid}`);
            const data = await response.json();

            if (data.success) {
                container.innerHTML = this.renderDatasetFilesInline(data);
            } else {
                container.innerHTML = `<p class="text-muted small">${data.error || 'Failed to load files'}</p>`;
            }
        } catch (error) {
            console.error('Error loading dataset files:', error);
            container.innerHTML = `<p class="text-muted small">Error loading files</p>`;
        }
    }

    /**
     * Load dataset files structure (legacy method for separate files section)
     */
    async loadDatasetFiles(datasetUuid) {
        if (!datasetUuid) {
            return;
        }

        const filesContainer = document.getElementById('datasetFiles');
        if (!filesContainer) {
            return;
        }

        // Show loading state
        filesContainer.innerHTML = `
            <div class="text-center py-2">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;

        try {
            const response = await fetch(`${getApiBasePath()}/dataset-files.php?dataset_uuid=${datasetUuid}`);
            const data = await response.json();

            if (data.success) {
                this.displayDatasetFiles(data);
            } else {
                filesContainer.innerHTML = `<p class="text-muted small">${data.error || 'Failed to load files'}</p>`;
            }
        } catch (error) {
            console.error('Error loading dataset files:', error);
            filesContainer.innerHTML = `<p class="text-muted small">Error loading files</p>`;
        }
    }

    /**
     * Render dataset files inline (for dataset list integration)
     * Shows upload and converted directories separately
     */
    renderDatasetFilesInline(data) {
        let html = '<div class="dataset-files-sections">';
        let hasFiles = false;
        
        // Upload directory section
        if (data.directories.upload.exists && data.directories.upload.files.length > 0) {
            hasFiles = true;
            const uploadId = 'upload-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            html += '<div class="file-directory-section mb-2">';
            html += `<button class="dataset-file-toggle" data-bs-toggle="collapse" data-bs-target="#${uploadId}" style="background: none; border: none; color: var(--fg-color); cursor: pointer; padding: 0.25rem 0.5rem; display: flex; align-items: center; width: 100%; font-weight: 500;">`;
            html += `<i class="fas fa-chevron-right me-2 file-chevron" style="font-size: 0.75rem; transition: transform 0.2s;"></i>`;
            html += `<i class="fas fa-upload me-2"></i>`;
            html += `<span>Upload</span>`;
            html += `<span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">${this.countFiles(data.directories.upload.files)}</span>`;
            html += `</button>`;
            html += `<div class="collapse" id="${uploadId}">`;
            html += '<ul class="dataset-files-list" style="list-style: none; padding-left: 0;">';
            html += this.renderFileTreeInline(data.directories.upload.files, 'upload', 0);
            html += '</ul>';
            html += `</div>`;
            html += '</div>';
        }
        
        // Converted directory section
        if (data.directories.converted.exists && data.directories.converted.files.length > 0) {
            hasFiles = true;
            const convertedId = 'converted-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            html += '<div class="file-directory-section mb-2">';
            html += `<button class="dataset-file-toggle" data-bs-toggle="collapse" data-bs-target="#${convertedId}" style="background: none; border: none; color: var(--fg-color); cursor: pointer; padding: 0.25rem 0.5rem; display: flex; align-items: center; width: 100%; font-weight: 500;">`;
            html += `<i class="fas fa-chevron-right me-2 file-chevron" style="font-size: 0.75rem; transition: transform 0.2s;"></i>`;
            html += `<i class="fas fa-cog me-2"></i>`;
            html += `<span>Converted</span>`;
            html += `<span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">${this.countFiles(data.directories.converted.files)}</span>`;
            html += `</button>`;
            html += `<div class="collapse" id="${convertedId}">`;
            html += '<ul class="dataset-files-list" style="list-style: none; padding-left: 0;">';
            html += this.renderFileTreeInline(data.directories.converted.files, 'converted', 0);
            html += '</ul>';
            html += `</div>`;
            html += '</div>';
        }
        
        if (!hasFiles) {
            html += '<p class="text-muted small">No files found</p>';
        }
        
        html += '</div>';
        return html;
    }
    
    /**
     * Count total files in a file tree (recursive)
     */
    countFiles(items) {
        let count = 0;
        for (const item of items) {
            if (item.type === 'file') {
                count++;
            } else if (item.type === 'directory' && item.children) {
                count += this.countFiles(item.children);
            }
        }
        return count;
    }

    /**
     * Render file tree inline with collapsible folders
     */
    renderFileTreeInline(items, basePath = '', level = 0) {
        let html = '';
        const uniqueId = 'files-' + basePath.replace(/[^a-zA-Z0-9]/g, '-') + '-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        
        for (const item of items) {
            if (item.type === 'directory') {
                const dirId = uniqueId + '-dir-' + item.path.replace(/[^a-zA-Z0-9]/g, '-');
                html += `<li class="dataset-file-item dataset-file-dir" style="padding-left: ${level * 1.5}rem;">`;
                html += `<button class="dataset-file-toggle" data-bs-toggle="collapse" data-bs-target="#${dirId}" style="background: none; border: none; color: var(--fg-color); cursor: pointer; padding: 0.25rem 0.5rem; display: flex; align-items: center; width: 100%;">`;
                html += `<i class="fas fa-chevron-right me-2 file-chevron" style="font-size: 0.75rem; transition: transform 0.2s;"></i>`;
                html += `<i class="fas fa-folder me-2"></i>`;
                html += `<span>${this.escapeHtml(item.name)}</span>`;
                if (item.children && item.children.length > 0) {
                    html += `<span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">${item.children.length}</span>`;
                }
                html += `</button>`;
                html += `<div class="collapse" id="${dirId}">`;
                if (item.children && item.children.length > 0) {
                    html += '<ul class="dataset-files-list" style="list-style: none; padding-left: 0;">';
                    html += this.renderFileTreeInline(item.children, basePath, level + 1);
                    html += '</ul>';
                }
                html += `</div>`;
                html += '</li>';
            } else {
                html += `<li class="dataset-file-item dataset-file-file" style="padding-left: ${(level + 1) * 1.5}rem;">`;
                html += `<i class="fas fa-file me-2"></i>`;
                html += `<span>${this.escapeHtml(item.name)}</span>`;
                if (item.size) {
                    html += `<span class="text-muted small ms-2">(${this.formatFileSize(item.size)})</span>`;
                }
                html += '</li>';
            }
        }
        
        return html;
    }

    /**
     * Display dataset files structure
     */
    displayDatasetFiles(data) {
        const filesContainer = document.getElementById('datasetFiles');
        if (!filesContainer) return;

        let html = '';

        // Upload directory
        if (data.directories.upload.exists && data.directories.upload.files.length > 0) {
            html += `<div class="file-directory mb-2">`;
            html += `<div class="file-dir-header" data-bs-toggle="collapse" data-bs-target="#uploadFiles">`;
            html += `<i class="fas fa-folder me-2"></i><strong>Upload</strong>`;
            html += `<span class="badge bg-secondary ms-2">${this.countFiles(data.directories.upload.files)}</span>`;
            html += `</div>`;
            html += `<div class="collapse" id="uploadFiles">`;
            html += this.renderFileTree(data.directories.upload.files, 'upload');
            html += `</div>`;
            html += `</div>`;
        }

        // Converted directory
        if (data.directories.converted.exists && data.directories.converted.files.length > 0) {
            html += `<div class="file-directory mb-2">`;
            html += `<div class="file-dir-header" data-bs-toggle="collapse" data-bs-target="#convertedFiles">`;
            html += `<i class="fas fa-folder me-2"></i><strong>Converted</strong>`;
            html += `<span class="badge bg-secondary ms-2">${this.countFiles(data.directories.converted.files)}</span>`;
            html += `</div>`;
            html += `<div class="collapse" id="convertedFiles">`;
            html += this.renderFileTree(data.directories.converted.files, 'converted');
            html += `</div>`;
            html += `</div>`;
        }

        if (!html) {
            html = `<p class="text-muted small">No files found</p>`;
        }

        filesContainer.innerHTML = html;
    }

    /**
     * Count total files (recursive)
     */
    countFiles(items) {
        let count = 0;
        for (const item of items) {
            if (item.type === 'file') {
                count++;
            } else if (item.type === 'directory' && item.children) {
                count += this.countFiles(item.children);
            }
        }
        return count;
    }

    /**
     * Render file tree recursively
     */
    renderFileTree(items, basePath = '', level = 0) {
        let html = '<ul class="file-tree" style="list-style: none; padding-left: ' + (level * 1.5) + 'rem;">';
        
        for (const item of items) {
            if (item.type === 'directory') {
                const uniqueId = 'dir-' + basePath + '-' + item.path.replace(/[^a-zA-Z0-9]/g, '-');
                html += `<li class="file-tree-item">`;
                html += `<div class="file-tree-dir" data-bs-toggle="collapse" data-bs-target="#${uniqueId}">`;
                html += `<i class="fas fa-folder me-1"></i>`;
                html += `<span>${this.escapeHtml(item.name)}</span>`;
                if (item.children && item.children.length > 0) {
                    html += `<span class="badge bg-secondary ms-2">${item.children.length}</span>`;
                }
                html += `</div>`;
                html += `<div class="collapse" id="${uniqueId}">`;
                if (item.children && item.children.length > 0) {
                    html += this.renderFileTree(item.children, basePath, level + 1);
                }
                html += `</div>`;
                html += `</li>`;
            } else {
                html += `<li class="file-tree-item">`;
                html += `<div class="file-tree-file">`;
                html += `<i class="fas fa-file me-1"></i>`;
                html += `<span>${this.escapeHtml(item.name)}</span>`;
                if (item.size) {
                    html += `<span class="text-muted small ms-2">(${this.formatFileSize(item.size)})</span>`;
                }
                html += `</div>`;
                html += `</li>`;
            }
        }
        
        html += '</ul>';
        return html;
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Handle dataset selection
     */
    async handleDatasetSelection(datasetLink) {
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

        // Determine appropriate dashboard and update dropdown
        // First check if we can determine from dataset details
        try {
            const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
            const data = await response.json();
            if (data.success && data.dataset) {
                const dimensions = data.dataset.dimensions || '';
                // If dataset is 4D, select 4D_Dashboard in dropdown
                if (dimensions && dimensions.toUpperCase().includes('4D')) {
                    const viewerTypeSelect = document.getElementById('viewerType');
                    if (viewerTypeSelect) {
                        // Try to find 4D_Dashboard option
                        const option4D = Array.from(viewerTypeSelect.options).find(opt => 
                            opt.value === '4D_Dashboard' || 
                            opt.value.toLowerCase() === '4d_dashboard' ||
                            opt.text.toLowerCase().includes('4d')
                        );
                        if (option4D) {
                            viewerTypeSelect.value = option4D.value;
                        }
                    }
                }
            }
        } catch (error) {
            console.warn('Could not determine dashboard from dimensions:', error);
        }

        // Load dashboard (will use selected dashboard from dropdown or determine from dimensions)
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
            const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
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

        // Format tags for display/editing
        const tagsValue = Array.isArray(dataset.tags) ? dataset.tags.join(', ') : (dataset.tags || '');
        
        // Dashboard options (you may want to load these dynamically)
        const dashboardOptions = [
            'OpenVisusSlice',
            '4D_Dashboard',
            '3DVTK',
            'magicscan',
            'openvisus'
        ];
        
        const html = `
            <div class="dataset-details">
                <h6><i class="fas fa-info-circle"></i> Dataset Details</h6>
                
                <form id="datasetDetailsForm" class="dataset-details-form">
                    <input type="hidden" name="dataset_id" value="${dataset.id || dataset.uuid}">
                    
                    <!-- Editable Fields -->
                    <div class="editable-fields mb-3">
                        <h6 class="text-primary"><i class="fas fa-edit"></i> Editable Fields</h6>
                        
                        <div class="mb-2">
                            <label class="form-label small">Name:</label>
                            <input type="text" class="form-control form-control-sm" name="name" 
                                   value="${this.escapeHtml(dataset.name || '')}" 
                                   placeholder="Dataset name">
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label small">Tags:</label>
                            <input type="text" class="form-control form-control-sm" name="tags" 
                                   value="${this.escapeHtml(tagsValue)}" 
                                   placeholder="Comma-separated tags">
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label small">Folder:</label>
                            <input type="text" class="form-control form-control-sm" name="folder_uuid" 
                                   value="${this.escapeHtml(dataset.folder_uuid || '')}" 
                                   placeholder="Folder UUID">
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label small">Group:</label>
                            <input type="text" class="form-control form-control-sm" name="team_uuid" 
                                   value="${this.escapeHtml(dataset.team_uuid || '')}" 
                                   placeholder="Team/Group UUID">
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label small">Dimensions:</label>
                            <input type="text" class="form-control form-control-sm" name="dimensions" 
                                   value="${this.escapeHtml(dataset.dimensions || '')}" 
                                   placeholder="e.g., 1024x1024x100">
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label small">Dashboard Preferred:</label>
                            <select class="form-select form-select-sm" name="preferred_dashboard">
                                ${dashboardOptions.map(opt => 
                                    `<option value="${opt}" ${(dataset.preferred_dashboard || '').toLowerCase() === opt.toLowerCase() ? 'selected' : ''}>${opt}</option>`
                                ).join('')}
                            </select>
                        </div>
                        
                        <button type="submit" class="btn btn-sm btn-primary mt-2">
                            <i class="fas fa-save"></i> Save Changes
                        </button>
                    </div>
                    
                    <!-- Non-editable Fields -->
                    <div class="readonly-fields">
                        <h6 class="text-secondary"><i class="fas fa-info"></i> Other Data</h6>
                        
                        <div class="detail-item mb-1">
                            <span class="detail-label">Size:</span>
                            <span class="detail-value">${this.formatFileSize(dataset.data_size || 0)}</span>
                        </div>
                        
                        <div class="detail-item mb-1">
                            <span class="detail-label">Created:</span>
                            <span class="detail-value">${this.formatDate(dataset.created_at || dataset.time)}</span>
                        </div>
                        
                        <div class="detail-item mb-1">
                            <span class="detail-label">Sensor:</span>
                            <span class="detail-value">${this.escapeHtml(dataset.sensor || 'Unknown')}</span>
                        </div>
                        
                        <div class="detail-item mb-1">
                            <span class="detail-label">Status:</span>
                            <span class="badge bg-${this.getStatusColor(dataset.status)}">${this.escapeHtml(dataset.status || 'unknown')}</span>
                        </div>
                        
                        <div class="detail-item mb-1">
                            <span class="detail-label">Compression Status:</span>
                            <span class="badge bg-${this.getStatusColor(dataset.compression_status)}">${this.escapeHtml(dataset.compression_status || 'unknown')}</span>
                        </div>
                        
                        <div class="detail-item mb-1">
                            <span class="detail-label">UUID:</span>
                            <span class="detail-value small text-muted">${this.escapeHtml(dataset.uuid || '')}</span>
                        </div>
                    </div>
                    
                    <div class="dataset-actions mt-3 pt-3 border-top">
                        <button type="button" class="btn btn-sm btn-outline-secondary" data-action="share" data-dataset-id="${dataset.id || dataset.uuid}">
                            <i class="fas fa-share"></i> Share
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger" data-action="delete" data-dataset-id="${dataset.id || dataset.uuid}">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </form>
            </div>
        `;

        detailsContainer.innerHTML = html;
        
        // Attach form submit handler
        const form = detailsContainer.querySelector('#datasetDetailsForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveDatasetChanges(form, dataset.id || dataset.uuid);
            });
        }
    }
    
    /**
     * Save dataset changes
     */
    async saveDatasetChanges(form, datasetId) {
        const formData = new FormData(form);
        const updateData = {
            dataset_id: datasetId,
            name: formData.get('name'),
            tags: formData.get('tags'),
            folder_uuid: formData.get('folder_uuid'),
            team_uuid: formData.get('team_uuid'),
            dimensions: formData.get('dimensions'),
            preferred_dashboard: formData.get('preferred_dashboard')
        };
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        try {
            const response = await fetch(`${getApiBasePath()}/update-dataset.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show success message
                const alert = document.createElement('div');
                alert.className = 'alert alert-success alert-dismissible fade show mt-2';
                alert.innerHTML = `
                    <i class="fas fa-check-circle"></i> Dataset updated successfully!
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                form.insertBefore(alert, form.firstChild);
                
                // Reload dataset details to show updated data
                setTimeout(() => {
                    this.loadDatasetDetails(datasetId);
                }, 1000);
            } else {
                throw new Error(data.error || 'Failed to update dataset');
            }
        } catch (error) {
            console.error('Error saving dataset changes:', error);
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger alert-dismissible fade show mt-2';
            alert.innerHTML = `
                <i class="fas fa-exclamation-circle"></i> Error: ${this.escapeHtml(error.message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            form.insertBefore(alert, form.firstChild);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
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
    async loadDashboard(datasetId, datasetName, datasetUuid, datasetServer) {
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

        // Determine appropriate dashboard
        // First, try to get the selected dashboard from the dropdown
        let selectedDashboard = null;
        const viewerTypeSelect = document.getElementById('viewerType');
        if (viewerTypeSelect && viewerTypeSelect.value) {
            selectedDashboard = viewerTypeSelect.value;
        }
        
        // If no dashboard selected, try to determine from dataset dimensions
        if (!selectedDashboard && this.currentDataset) {
            // Get dataset details to check dimensions
            try {
                const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
                const data = await response.json();
                if (data.success && data.dataset) {
                    const dimensions = data.dataset.dimensions || '';
                    // If dataset is 4D, default to 4D_Dashboard
                    if (dimensions && dimensions.toUpperCase().includes('4D')) {
                        selectedDashboard = '4D_Dashboard';
                    }
                }
            } catch (error) {
                console.warn('Could not determine dashboard from dimensions:', error);
            }
        }
        
        // Fallback to OpenVisusSlice if nothing else selected
        if (!selectedDashboard) {
            selectedDashboard = 'OpenVisusSlice';
        }
        
        // Load dashboard using viewer manager
        if (window.viewerManager) {
            window.viewerManager.loadDashboard(
                datasetId,
                datasetName,
                datasetUuid,
                datasetServer,
                selectedDashboard
            );
            return;
        }
        
        // Fallback: Load dashboard via URL
        const url = new URL(window.location);
        url.searchParams.set('dataset_id', datasetId);
        url.searchParams.set('dashboard', selectedDashboard);

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
     * Share dataset - shows share interface
     */
    async shareDataset(datasetId) {
        const datasetUuid = this.currentDataset?.uuid || datasetId;
        const datasetName = this.currentDataset?.name || 'Dataset';
        
        // Show share interface in viewerContainer
        this.showShareInterface(datasetUuid, datasetName);
    }
    
    /**
     * Show share interface
     */
    async showShareInterface(datasetUuid, datasetName) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;
        
        // Show loading state
        viewerContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading share options...</p>
            </div>
        `;
        
        // Load teams
        let teams = [];
        try {
            const teamsResponse = await fetch(`${getApiBasePath()}/get-teams.php`);
            const teamsData = await teamsResponse.json();
            if (teamsData.success && teamsData.teams) {
                teams = teamsData.teams;
            }
        } catch (error) {
            console.warn('Could not load teams:', error);
        }
        
        // Build share interface HTML
        const html = `
            <div class="share-interface container mt-4">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-share-alt"></i> Share Dataset: ${this.escapeHtml(datasetName)}
                        </h5>
                    </div>
                    <div class="card-body">
                        <input type="hidden" id="share-dataset-uuid" value="${this.escapeHtml(datasetUuid)}">
                        
                        <!-- Share with Users Section -->
                        <div class="mb-4">
                            <h6 class="text-primary">
                                <i class="fas fa-user"></i> Share with Users
                            </h6>
                            <p class="text-muted small">Enter email addresses to share this dataset with individual users.</p>
                            
                            <div id="user-email-entries">
                                <div class="email-entry mb-2">
                                    <div class="input-group">
                                        <input type="email" class="form-control form-control-sm user-email-input" 
                                               placeholder="user@example.com" 
                                               data-entry-index="1">
                                        <button type="button" class="btn btn-sm btn-outline-danger remove-email-btn" 
                                                onclick="datasetManager.removeEmailEntry(1)" 
                                                style="display: none;">
                                            <i class="fas fa-times"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                            
                            <button type="button" class="btn btn-sm btn-outline-secondary mt-2" 
                                    onclick="datasetManager.addEmailEntry()">
                                <i class="fas fa-plus"></i> Add Another Email
                            </button>
                            
                            <button type="button" class="btn btn-sm btn-primary mt-2 ms-2" 
                                    onclick="datasetManager.shareWithUsers()">
                                <i class="fas fa-share"></i> Share with Users
                            </button>
                        </div>
                        
                        <hr>
                        
                        <!-- Share with Teams Section -->
                        <div class="mb-4">
                            <h6 class="text-primary">
                                <i class="fas fa-users"></i> Share with Teams
                            </h6>
                            <p class="text-muted small">Select a team to share this dataset with all team members.</p>
                            
                            ${teams.length > 0 ? `
                                <div class="mb-3">
                                    <label class="form-label">Select Team:</label>
                                    <select class="form-select" id="share-team-select">
                                        <option value="">-- Select a Team --</option>
                                        ${teams.map(team => `
                                            <option value="${this.escapeHtml(team.team_name)}" 
                                                    data-team-uuid="${this.escapeHtml(team.uuid || '')}">
                                                ${this.escapeHtml(team.team_name)} ${team.is_owner ? '(Owner)' : ''}
                                            </option>
                                        `).join('')}
                                    </select>
                                </div>
                                
                                <button type="button" class="btn btn-sm btn-primary" 
                                        onclick="datasetManager.shareWithTeam()">
                                    <i class="fas fa-share"></i> Share with Team
                                </button>
                            ` : `
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle"></i> You are not a member of any teams. 
                                    Create a team first to share datasets with teams.
                                </div>
                            `}
                        </div>
                        
                        <hr>
                        
                        <!-- Actions -->
                        <div class="d-flex justify-content-between">
                            <button type="button" class="btn btn-secondary" 
                                    onclick="datasetManager.closeShareInterface()">
                                <i class="fas fa-times"></i> Close
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        viewerContainer.innerHTML = html;
    }
    
    /**
     * Add email entry
     */
    addEmailEntry() {
        const container = document.getElementById('user-email-entries');
        if (!container) return;
        
        const entries = container.querySelectorAll('.email-entry');
        const nextIndex = entries.length + 1;
        
        const newEntry = document.createElement('div');
        newEntry.className = 'email-entry mb-2';
        newEntry.innerHTML = `
            <div class="input-group">
                <input type="email" class="form-control form-control-sm user-email-input" 
                       placeholder="user@example.com" 
                       data-entry-index="${nextIndex}">
                <button type="button" class="btn btn-sm btn-outline-danger remove-email-btn" 
                        onclick="datasetManager.removeEmailEntry(${nextIndex})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        container.appendChild(newEntry);
        this.updateEmailEntryButtons();
    }
    
    /**
     * Remove email entry
     */
    removeEmailEntry(index) {
        const entry = document.querySelector(`.email-entry input[data-entry-index="${index}"]`)?.closest('.email-entry');
        if (entry) {
            entry.remove();
            this.updateEmailEntryButtons();
        }
    }
    
    /**
     * Update email entry buttons visibility
     */
    updateEmailEntryButtons() {
        const entries = document.querySelectorAll('.email-entry');
        entries.forEach((entry, idx) => {
            const removeBtn = entry.querySelector('.remove-email-btn');
            if (removeBtn) {
                removeBtn.style.display = entries.length > 1 ? 'block' : 'none';
            }
        });
    }
    
    /**
     * Share with users
     */
    async shareWithUsers() {
        const datasetUuid = document.getElementById('share-dataset-uuid')?.value;
        if (!datasetUuid) {
            alert('Dataset UUID not found');
            return;
        }
        
        // Get all email inputs
        const emailInputs = document.querySelectorAll('.user-email-input');
        const emails = Array.from(emailInputs)
            .map(input => input.value.trim())
            .filter(email => email && this.isValidEmail(email));
        
        if (emails.length === 0) {
            alert('Please enter at least one valid email address');
            return;
        }
        
        // Share with each user
        const results = [];
        for (const email of emails) {
            try {
                const response = await fetch(`${getApiBasePath()}/share-dataset.php`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        dataset_uuid: datasetUuid,
                        user_email: email
                    })
                });
                
                const data = await response.json();
                results.push({ email, success: data.success, error: data.error });
            } catch (error) {
                results.push({ email, success: false, error: error.message });
            }
        }
        
        // Show results
        const successCount = results.filter(r => r.success).length;
        const failCount = results.filter(r => !r.success).length;
        
        let message = `Sharing completed:\n`;
        message += `✓ Successfully shared with ${successCount} user(s)\n`;
        if (failCount > 0) {
            message += `✗ Failed to share with ${failCount} user(s)\n\n`;
            message += 'Errors:\n';
            results.filter(r => !r.success).forEach(r => {
                message += `  • ${r.email}: ${r.error || 'Unknown error'}\n`;
            });
        }
        
        alert(message);
        
        // Close interface if all successful
        if (failCount === 0) {
            this.closeShareInterface();
        }
    }
    
    /**
     * Share with team
     */
    async shareWithTeam() {
        const datasetUuid = document.getElementById('share-dataset-uuid')?.value;
        const teamSelect = document.getElementById('share-team-select');
        
        if (!datasetUuid) {
            alert('Dataset UUID not found');
            return;
        }
        
        if (!teamSelect || !teamSelect.value) {
            alert('Please select a team');
            return;
        }
        
        const teamName = teamSelect.value;
        const selectedOption = teamSelect.options[teamSelect.selectedIndex];
        const teamUuid = selectedOption ? selectedOption.getAttribute('data-team-uuid') : null;
        
        try {
            const response = await fetch(`${getApiBasePath()}/share-dataset.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    dataset_uuid: datasetUuid,
                    team_name: teamName,
                    team_uuid: teamUuid
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert(`Dataset shared successfully with team: ${teamName}`);
                this.closeShareInterface();
            } else {
                alert(`Error sharing dataset: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error sharing dataset with team:', error);
            alert('Error sharing dataset with team: ' + error.message);
        }
    }
    
    /**
     * Close share interface
     */
    closeShareInterface() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (viewerContainer && this.currentDataset) {
            // Reload the dashboard/viewer
            this.loadDashboard(
                this.currentDataset.id,
                this.currentDataset.name,
                this.currentDataset.uuid,
                this.currentDataset.server
            );
        }
    }
    
    /**
     * Validate email
     */
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    /**
     * Delete dataset
     */
    async deleteDataset(datasetId) {
        if (confirm('Are you sure you want to delete this dataset? This action cannot be undone.')) {
            try {
                const response = await fetch(`${getApiBasePath()}/delete-dataset.php`, {
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
     * Input is assumed to be in GB (as a float/numeric value from database)
     * Converts and displays in the most appropriate unit (KB, MB, GB, TB)
     */
    formatFileSize(sizeGb) {
        if (!sizeGb || sizeGb == 0) return '0 B';
        
        // Ensure it's a number
        const size = parseFloat(sizeGb);
        if (isNaN(size) || size <= 0) return '0 B';
        
        // Convert GB to bytes for calculation
        const bytes = size * 1024 * 1024 * 1024;
        
        // Determine the best unit to display
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let pow = Math.floor((bytes ? Math.log(bytes) : 0) / Math.log(1024));
        pow = Math.min(pow, units.length - 1);
        
        // Convert to the appropriate unit
        const value = bytes / Math.pow(1024, pow);
        
        // Format with appropriate decimal places
        let decimals = 2;
        if (pow === 0) decimals = 0; // Bytes - no decimals
        else if (pow === 1) decimals = 1; // KB - 1 decimal
        else if (pow >= 2) decimals = 2; // MB, GB, TB - 2 decimals
        
        return value.toFixed(decimals) + ' ' + units[pow];
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
