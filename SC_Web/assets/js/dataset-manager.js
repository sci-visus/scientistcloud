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
        this.isSelectingDataset = false; // Flag to prevent multiple simultaneous selections
        this.pendingSelection = null; // Store pending selection if one is already in progress
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
            // Auto-refresh datasets on page load to ensure team/shared datasets are up-to-date
            // Use a small delay to avoid race conditions with other initialization
            setTimeout(() => {
                this.loadDatasets();
            }, 500);
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
                    console.log('✅ Datasets refreshed');
                } catch (error) {
                    console.error('Error refreshing datasets:', error);
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
                const datasetId = datasetLink.dataset?.datasetId;
                
                // Prevent duplicate clicks on the same dataset within 500ms
                if (datasetId && this.currentDataset?.id === datasetId && this.lastLoadTime && (Date.now() - this.lastLoadTime) < 500) {
                    console.log('⏭️ Ignoring rapid duplicate click on same dataset');
                    return;
                }
                
                this.handleDatasetSelection(datasetLink);
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
                const deleteButton = e.target.closest('[data-action="delete"]');
                const datasetId = deleteButton.dataset.datasetId || deleteButton.getAttribute('data-dataset-id');
                if (datasetId) {
                    this.deleteDataset(datasetId);
                } else {
                    console.error('Could not find dataset ID for delete button');
                }
            }
            
            if (e.target.closest('[data-action="copy-dashboard-link"]')) {
                e.preventDefault();
                const button = e.target.closest('[data-action="copy-dashboard-link"]');
                const datasetId = button.dataset.datasetId || button.getAttribute('data-dataset-id');
                const datasetUuid = button.dataset.datasetUuid || button.getAttribute('data-dataset-uuid');
                const datasetName = button.dataset.datasetName || button.getAttribute('data-dataset-name');
                const datasetServer = button.dataset.datasetServer || button.getAttribute('data-dataset-server');
                if (datasetId) {
                    this.copyDashboardLink(datasetId, {
                        uuid: datasetUuid,
                        name: datasetName,
                        server: datasetServer
                    });
                } else {
                    console.error('Could not find dataset ID for copy dashboard link button');
                }
            }
            
            if (e.target.closest('[data-action="open-dashboard-link"]')) {
                e.preventDefault();
                const button = e.target.closest('[data-action="open-dashboard-link"]');
                const datasetId = button.dataset.datasetId || button.getAttribute('data-dataset-id');
                const datasetUuid = button.dataset.datasetUuid || button.getAttribute('data-dataset-uuid');
                const datasetName = button.dataset.datasetName || button.getAttribute('data-dataset-name');
                const datasetServer = button.dataset.datasetServer || button.getAttribute('data-dataset-server');
                if (datasetId) {
                    this.openDashboardLink(datasetId, {
                        uuid: datasetUuid,
                        name: datasetName,
                        server: datasetServer
                    });
                } else {
                    console.error('Could not find dataset ID for open dashboard link button');
                }
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
            // Add cache-busting parameter to prevent stale data
            const cacheBuster = new Date().getTime();
            const response = await fetch(`${getApiBasePath()}/datasets.php?t=${cacheBuster}`, {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });
            
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
                
                // Log sample datasets from each category for debugging
                if (this.datasets.my.length > 0) {
                    console.log('First my dataset:', this.datasets.my[0]);
                }
                if (this.datasets.shared.length > 0) {
                    console.log('First shared dataset:', this.datasets.shared[0]);
                } else {
                    console.log('⚠️ No shared datasets found in response');
                }
                if (this.datasets.team.length > 0) {
                    console.log('First team dataset:', this.datasets.team[0]);
                } else {
                    console.log('⚠️ No team datasets found in response');
                }
                
                // Log full response structure for debugging
                if (this.datasets.shared.length === 0 && this.datasets.team.length === 0) {
                    console.log('Full API response structure:', {
                        has_datasets: !!data.datasets,
                        datasets_type: typeof data.datasets,
                        datasets_keys: data.datasets ? Object.keys(data.datasets) : [],
                        full_response: data
                    });
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
        
        // Shared Datasets - Always show, even if empty
        html += this.renderDatasetGroup('Shared with Me', groupedDatasets['shared'], 'sharedDatasets');
        
        // Team Datasets - Always show, even if empty
        html += this.renderDatasetGroup('Team Datasets', groupedDatasets['team'], 'teamDatasets');
        
        container.innerHTML = html;
        
        // Initialize Bootstrap collapse components and set up arrow icon updates
        setTimeout(() => {
            // Set up collapse event listeners for arrow icon updates
            container.querySelectorAll('.collapse').forEach(collapseEl => {
                const collapseId = collapseEl.id;
                const arrowIcon = document.getElementById(`arrow-${collapseId}`);
                
                if (arrowIcon && typeof bootstrap !== 'undefined') {
                    // Update arrow when section expands/collapses
                    collapseEl.addEventListener('show.bs.collapse', () => {
                        arrowIcon.textContent = '▼'; // Down arrow when expanded
                        arrowIcon.classList.add('open');
                    });
                    
                    collapseEl.addEventListener('hide.bs.collapse', () => {
                        arrowIcon.textContent = '▶'; // Right arrow when collapsed
                        arrowIcon.classList.remove('open');
                    });
                    
                    // If section starts expanded (has 'show' class), update arrow immediately
                    if (collapseEl.classList.contains('show')) {
                        arrowIcon.textContent = '▼';
                        arrowIcon.classList.add('open');
                    }
                }
            });
        }, 50);
        
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
        container.addEventListener('click', async (e) => {
            const link = e.target.closest('.dataset-link');
            if (link) {
                e.preventDefault();
                
                const datasetId = link.getAttribute('data-dataset-id');
                const datasetName = link.getAttribute('data-dataset-name');
                const datasetUuid = link.getAttribute('data-dataset-uuid');
                const datasetServer = link.getAttribute('data-dataset-server');
                
                console.log('Dataset clicked:', { datasetId, datasetName, datasetUuid, datasetServer });
                
                // Prevent duplicate processing
                if (this.isSelectingDataset && this.currentDataset?.id === datasetId) {
                    console.log('⏭️ Already selecting this dataset, skipping duplicate click');
                    return;
                }
                
                // Show immediate loading state in right column to prevent flashing
                const detailsContainer = document.getElementById('datasetDetails');
                if (detailsContainer) {
                    detailsContainer.innerHTML = `
                        <div class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2">Loading ${datasetName}...</p>
                        </div>
                    `;
                }
                
                // Show immediate loading state in middle column (dashboard area)
                const viewerContainer = document.getElementById('viewerContainer');
                if (viewerContainer) {
                    viewerContainer.innerHTML = `
                        <div class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <h5 class="mt-3">Loading Dashboard</h5>
                            <p class="text-muted">Preparing visualization for ${datasetName}</p>
                        </div>
                    `;
                }
                
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
                
                // Create a dataset link element to pass to handleDatasetSelection
                // This consolidates all logic in one place to prevent flashing
                const fakeLink = {
                    dataset: {
                        datasetId: datasetId,
                        datasetName: datasetName,
                        datasetUuid: datasetUuid,
                        datasetServer: datasetServer
                    }
                };
                this.handleDatasetSelection(fakeLink);
            }
            
            // Handle retry conversion button using event delegation
            const retryButton = e.target.closest('.retry-conversion-btn');
            if (retryButton) {
                e.stopPropagation(); // Prevent dataset selection
                
                const datasetUuid = retryButton.getAttribute('data-dataset-uuid');
                const datasetName = retryButton.getAttribute('data-dataset-name');
                
                if (datasetUuid) {
                    this.retryConversion(datasetUuid, datasetName, retryButton);
                }
                return;
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
                        // Try to get dataset details from the dataset item element
                        const datasetItem = toggleButton.closest('.dataset-item');
                        let dataset = null;
                        
                        // Get dataset details from currentDataset if available
                        if (this.currentDataset?.details && 
                            (this.currentDataset.uuid === datasetUuid || this.currentDataset.id === datasetUuid)) {
                            dataset = this.currentDataset.details;
                        } else if (datasetItem) {
                            // Try to get dataset ID from the dataset item
                            const datasetId = datasetItem.getAttribute('data-dataset-id');
                            if (datasetId) {
                                try {
                                    const datasetResponse = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
                                    if (datasetResponse.ok) {
                                        const datasetData = await datasetResponse.json();
                                        if (datasetData.success) {
                                            dataset = datasetData.dataset;
                                        }
                                    }
                                } catch (error) {
                                    console.warn('Could not fetch dataset details for permission check:', error);
                                }
                            }
                        }
                        
                        this.loadDatasetFilesIntoContainer(datasetUuid, content, dataset);
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
            // Still show the section, but expanded on first load so user knows it's empty
            return `
                <div class="dataset-section">
                    <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#${id}">
                        <span class="arrow-icon" id="arrow-${id}">▼</span>${title} (0)
                    </a>
                    <div class="collapse show ps-4 w-100" id="${id}" data-bs-parent=".dataset-list">
                        <p class="text-muted">No datasets found.</p>
                    </div>
                </div>
            `;
        }

        let html = `
            <div class="dataset-section">
                <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#${id}">
                    <span class="arrow-icon" id="arrow-${id}">▼</span>${title} (${totalCount})
                </a>
                <div class="collapse show ps-4 w-100" id="${id}" data-bs-parent=".dataset-list">
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
        
        // Determine server flag: true if google_drive_link exists and includes 'http' but is NOT a Google Drive link
        // Logic: if google_drive_link exists and contains 'http' but not 'google.com', then server=true
        // The link itself will be used as the dataset UUID for remote loading
        const link = dataset.google_drive_link || dataset.download_url || dataset.viewer_url || '';
        const containsHttp = link ? link.includes('http') : false;
        const containsGoogle = link ? link.includes('google.com') : false;
        const datasetServer = (containsHttp && !containsGoogle) ? 'true' : 'false';
        
        // When server=true, use the link as the UUID for remote loading
        // Otherwise use the dataset UUID
        const effectiveUuid = (datasetServer === 'true' && link) ? link : datasetUuid;
        
        const statusColor = this.getStatusColor(status);
        const fileIcon = this.getFileIcon(sensor);
        
        // Determine if retry button should be shown
        // Show retry for: failed, conversion failed, or any status containing "failed" or "error"
        const showRetry = status && (
            status.toLowerCase().includes('failed') || 
            status.toLowerCase().includes('error') ||
            status === 'conversion failed'
        );
        
        return `
            <div class="dataset-item" data-dataset-id="${datasetId}" data-dataset-uuid="${datasetUuid}">
                <div class="dataset-header d-flex align-items-center">
                    <a class="nav-link dataset-link flex-grow-1" href="javascript:void(0)" 
                       data-dataset-id="${datasetId}"
                       data-dataset-name="${datasetName}"
                       data-dataset-uuid="${effectiveUuid}"
                       data-dataset-server="${datasetServer}">
                        <i class="${fileIcon} me-2"></i>
                        <span class="dataset-name">${datasetName}</span>
                    </a>
                    <div class="dataset-actions d-flex align-items-center gap-2 ms-2">
                        <span class="badge bg-${statusColor}">${status}</span>
                        ${showRetry ? `
                            <button class="btn btn-sm btn-warning retry-conversion-btn" 
                                    data-dataset-uuid="${datasetUuid}"
                                    data-dataset-name="${datasetName}"
                                    title="Retry conversion">
                                Retry
                            </button>
                        ` : ''}
                        <button class="btn btn-sm btn-link dataset-files-toggle p-0" data-dataset-uuid="${datasetUuid}" title="Toggle files">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                    </div>
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
    async loadDatasetFilesIntoContainer(datasetUuid, container, dataset = null) {
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
            // Get dataset details if not provided to check download permissions
            if (!dataset) {
                try {
                    const datasetResponse = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetUuid}`);
                    if (datasetResponse.ok) {
                        const datasetData = await datasetResponse.json();
                        if (datasetData.success) {
                            dataset = datasetData.dataset;
                        }
                    }
                } catch (error) {
                    console.warn('Could not fetch dataset details for permission check:', error);
                }
            }

            // Check download permissions
            let canDownload = true;
            if (dataset) {
                canDownload = await this.canDownloadDataset(dataset);
            }

            const response = await fetch(`${getApiBasePath()}/dataset-files.php?dataset_uuid=${datasetUuid}`);
            const data = await response.json();

            console.log('Dataset files API response:', data);

            if (data.success) {
                // If user can't download, show restricted message instead of files
                if (!canDownload) {
                    container.innerHTML = `
                        <div class="alert alert-info small mb-0">
                            <i class="fas fa-info-circle me-2"></i>
                            File access is restricted. Only ${dataset?.is_downloadable === 'only owner' ? 'the owner' : dataset?.is_downloadable === 'only team' ? 'team members' : 'authorized users'} can download files from this dataset.
                        </div>
                    `;
                    return;
                }

                // Log detailed information for debugging
                const uploadDir = data.directories?.upload;
                const convertedDir = data.directories?.converted;
                const uploadCount = uploadDir?.files?.length || 0;
                const convertedCount = convertedDir?.files?.length || 0;
                
                console.log(`Files found - Upload: ${uploadCount}, Converted: ${convertedCount}`);
                console.log(`Upload directory exists: ${uploadDir?.exists}, readable: ${uploadDir?.readable}, path: ${uploadDir?.path}`);
                console.log(`Converted directory exists: ${convertedDir?.exists}, readable: ${convertedDir?.readable}, path: ${convertedDir?.path}`);
                
                if (uploadCount === 0 && uploadDir?.exists) {
                    console.warn('Upload directory exists but no files found. Check if files are in subdirectories or excluded.');
                }
                
                container.innerHTML = this.renderDatasetFilesInline(data, datasetUuid);
                
                // Attach click handlers for clickable files
                this.attachFileClickHandlers(container, datasetUuid);
            } else {
                console.error('Failed to load files:', data.error);
                container.innerHTML = `<p class="text-muted small">${data.error || 'Failed to load files'}</p>`;
            }
        } catch (error) {
            console.error('Error loading dataset files:', error);
            container.innerHTML = `<p class="text-muted small">Error loading files: ${error.message}</p>`;
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
            // Get dataset details to check download permissions
            let dataset = this.currentDataset?.details || null;
            if (!dataset) {
                try {
                    const datasetResponse = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetUuid}`);
                    if (datasetResponse.ok) {
                        const datasetData = await datasetResponse.json();
                        if (datasetData.success) {
                            dataset = datasetData.dataset;
                        }
                    }
                } catch (error) {
                    console.warn('Could not fetch dataset details for permission check:', error);
                }
            }

            // Check download permissions
            let canDownload = true;
            if (dataset) {
                canDownload = await this.canDownloadDataset(dataset);
            }

            const response = await fetch(`${getApiBasePath()}/dataset-files.php?dataset_uuid=${datasetUuid}`);
            const data = await response.json();

            if (data.success) {
                // If user can't download, show restricted message
                if (!canDownload) {
                    filesContainer.innerHTML = `
                        <div class="alert alert-info small mb-0">
                            <i class="fas fa-info-circle me-2"></i>
                            File access is restricted. Only ${dataset?.is_downloadable === 'only owner' ? 'the owner' : dataset?.is_downloadable === 'only team' ? 'team members' : 'authorized users'} can download files from this dataset.
                        </div>
                    `;
                    return;
                }

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
     * Attach click handlers for clickable files
     */
    attachFileClickHandlers(container, datasetUuid) {
        const clickableFiles = container.querySelectorAll('.clickable-file');
        clickableFiles.forEach(fileItem => {
            fileItem.addEventListener('click', async (e) => {
                e.stopPropagation();
                const filePath = fileItem.getAttribute('data-file-path');
                const fileName = fileItem.getAttribute('data-file-name');
                const fileType = fileItem.getAttribute('data-file-type');
                
                // Get directory from data attribute (set during rendering)
                const directory = fileItem.getAttribute('data-directory') || 'upload';
                
                if (fileType === 'text') {
                    await this.displayTextFile(datasetUuid, filePath, fileName, directory);
                } else if (fileType === 'image') {
                    await this.displayImageFile(datasetUuid, filePath, fileName, directory);
                }
            });
        });
    }

    /**
     * Display text file content in center panel
     */
    async displayTextFile(datasetUuid, filePath, fileName, directory) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) {
            console.error('Viewer container not found');
            return;
        }

        // Check download permissions before allowing file viewing
        let dataset = this.currentDataset?.details || null;
        if (!dataset) {
            try {
                const datasetResponse = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetUuid}`);
                if (datasetResponse.ok) {
                    const datasetData = await datasetResponse.json();
                    if (datasetData.success) {
                        dataset = datasetData.dataset;
                    }
                }
            } catch (error) {
                console.warn('Could not fetch dataset details for permission check:', error);
            }
        }

        if (dataset) {
            const canDownload = await this.canDownloadDataset(dataset);
            if (!canDownload) {
                viewerContainer.innerHTML = `
                    <div class="container-fluid p-4">
                        <div class="alert alert-warning">
                            <i class="fas fa-lock me-2"></i>
                            File access is restricted. Only ${dataset.is_downloadable === 'only owner' ? 'the owner' : dataset.is_downloadable === 'only team' ? 'team members' : 'authorized users'} can access files from this dataset.
                        </div>
                    </div>
                `;
                return;
            }
        }

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="container-fluid p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5><i class="fas fa-file-alt me-2"></i>${this.escapeHtml(fileName)}</h5>
                    <button class="btn btn-sm btn-outline-secondary" onclick="window.datasetManager.clearFileView()">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
        `;

        try {
            const response = await fetch(`${getApiBasePath()}/dataset-file-content.php?dataset_uuid=${encodeURIComponent(datasetUuid)}&file_path=${encodeURIComponent(filePath)}&directory=${encodeURIComponent(directory)}`);
            const data = await response.json();

            if (data.success && data.type === 'text') {
                // Display text content with syntax highlighting for JSON
                const isJson = fileName.toLowerCase().endsWith('.json');
                const content = data.content;
                
                let contentHtml = '';
                if (isJson) {
                    try {
                        const jsonObj = JSON.parse(content);
                        contentHtml = `<pre class="file-text-content p-3 rounded"><code>${this.escapeHtml(JSON.stringify(jsonObj, null, 2))}</code></pre>`;
                    } catch (e) {
                        // Not valid JSON, display as plain text
                        contentHtml = `<pre class="file-text-content p-3 rounded" style="white-space: pre-wrap; word-wrap: break-word;"><code>${this.escapeHtml(content)}</code></pre>`;
                    }
                } else {
                    contentHtml = `<pre class="file-text-content p-3 rounded" style="white-space: pre-wrap; word-wrap: break-word;"><code>${this.escapeHtml(content)}</code></pre>`;
                }

                viewerContainer.innerHTML = `
                    <div class="container-fluid p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5><i class="fas fa-file-alt me-2"></i>${this.escapeHtml(fileName)}</h5>
                            <button class="btn btn-sm btn-outline-secondary" onclick="window.datasetManager.clearFileView()">
                                <i class="fas fa-times"></i> Close
                            </button>
                        </div>
                        <div class="file-content-viewer" style="max-height: calc(100vh - 200px); overflow-y: auto;">
                            ${contentHtml}
                        </div>
                    </div>
                `;
            } else {
                viewerContainer.innerHTML = `
                    <div class="container-fluid p-4">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Failed to load file: ${data.error || 'Unknown error'}
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading text file:', error);
            viewerContainer.innerHTML = `
                <div class="container-fluid p-4">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error loading file: ${error.message}
                    </div>
                </div>
            `;
        }
    }

    /**
     * Display image file in center panel
     */
    async displayImageFile(datasetUuid, filePath, fileName, directory) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) {
            console.error('Viewer container not found');
            return;
        }

        // Check download permissions before allowing file viewing
        let dataset = this.currentDataset?.details || null;
        if (!dataset) {
            try {
                const datasetResponse = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetUuid}`);
                if (datasetResponse.ok) {
                    const datasetData = await datasetResponse.json();
                    if (datasetData.success) {
                        dataset = datasetData.dataset;
                    }
                }
            } catch (error) {
                console.warn('Could not fetch dataset details for permission check:', error);
            }
        }

        if (dataset) {
            const canDownload = await this.canDownloadDataset(dataset);
            if (!canDownload) {
                viewerContainer.innerHTML = `
                    <div class="container-fluid p-4">
                        <div class="alert alert-warning">
                            <i class="fas fa-lock me-2"></i>
                            File access is restricted. Only ${dataset.is_downloadable === 'only owner' ? 'the owner' : dataset.is_downloadable === 'only team' ? 'team members' : 'authorized users'} can access files from this dataset.
                        </div>
                    </div>
                `;
                return;
            }
        }

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="container-fluid p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5><i class="fas fa-image me-2"></i>${this.escapeHtml(fileName)}</h5>
                    <button class="btn btn-sm btn-outline-secondary" onclick="window.datasetManager.clearFileView()">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
        `;

        try {
            const response = await fetch(`${getApiBasePath()}/dataset-file-content.php?dataset_uuid=${encodeURIComponent(datasetUuid)}&file_path=${encodeURIComponent(filePath)}&directory=${encodeURIComponent(directory)}`);
            const data = await response.json();

            if (data.success && data.type === 'image') {
                // Build full URL for image
                const imageUrl = `${getApiBasePath()}/dataset-file-serve.php?dataset_uuid=${encodeURIComponent(datasetUuid)}&file_path=${encodeURIComponent(filePath)}&directory=${encodeURIComponent(directory)}`;
                
                viewerContainer.innerHTML = `
                    <div class="container-fluid p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5><i class="fas fa-image me-2"></i>${this.escapeHtml(fileName)}</h5>
                            <button class="btn btn-sm btn-outline-secondary" onclick="window.datasetManager.clearFileView()">
                                <i class="fas fa-times"></i> Close
                            </button>
                        </div>
                        <div class="image-viewer text-center" style="max-height: calc(100vh - 200px); overflow-y: auto;">
                            <img src="${imageUrl}" 
                                 alt="${this.escapeHtml(fileName)}" 
                                 class="img-fluid" 
                                 style="max-width: 100%; height: auto;"
                                 onerror="this.parentElement.innerHTML='<div class=\\'alert alert-danger\\'><i class=\\'fas fa-exclamation-triangle me-2\\'></i>Failed to load image</div>'">
                        </div>
                    </div>
                `;
            } else {
                viewerContainer.innerHTML = `
                    <div class="container-fluid p-4">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Failed to load image: ${data.error || 'Unknown error'}
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading image file:', error);
            viewerContainer.innerHTML = `
                <div class="container-fluid p-4">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error loading image: ${error.message}
                    </div>
                </div>
            `;
        }
    }

    /**
     * Clear file view and restore default content
     */
    clearFileView() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (viewerContainer && window.viewerManager) {
            // Restore the default welcome screen or current dashboard
            if (window.viewerManager.currentDashboard) {
                window.viewerManager.loadDashboard(window.viewerManager.currentDashboard);
            } else {
                // Load welcome screen
                fetch(`${getApiBasePath()}/../includes/dashboard_loader.php`)
                    .then(response => response.text())
                    .then(html => {
                        viewerContainer.innerHTML = html;
                    })
                    .catch(error => {
                        console.error('Error loading welcome screen:', error);
                        viewerContainer.innerHTML = '<p>Select a dataset to view</p>';
                    });
            }
        }
    }

    /**
     * Render dataset files inline (for dataset list integration)
     * Shows upload and converted directories separately
     */
    renderDatasetFilesInline(data, datasetUuid = null) {
        let html = '<div class="dataset-files-sections">';
        let hasFiles = false;
        
        // Upload directory section
        // Show section if directory exists, even if empty (user can see the structure)
        if (data.directories.upload.exists) {
            hasFiles = true;
            const uploadId = 'upload-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            html += '<div class="file-directory-section mb-2">';
            html += `<button class="dataset-file-toggle" data-bs-toggle="collapse" data-bs-target="#${uploadId}" style="background: none; border: none; color: var(--fg-color); cursor: pointer; padding: 0.25rem 0.5rem; display: flex; align-items: center; width: 100%; font-weight: 500;">`;
            html += `<i class="fas fa-chevron-right me-2 file-chevron" style="font-size: 0.75rem; transition: transform 0.2s;"></i>`;
            html += `<span>Upload</span>`;
            html += `<span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">${this.countFiles(data.directories.upload.files)}</span>`;
            html += `</button>`;
            html += `<div class="collapse" id="${uploadId}">`;
            html += '<ul class="dataset-files-list" style="list-style: none; padding-left: 0;">';
            if (data.directories.upload.files.length > 0) {
                html += this.renderFileTreeInline(data.directories.upload.files, 'upload', 0, 'upload');
            } else {
                html += '<li class="text-muted small">No files in upload directory</li>';
            }
            html += '</ul>';
            html += `</div>`;
            html += '</div>';
        }
        
        // Converted directory section
        // Show section if directory exists, even if empty
        if (data.directories.converted.exists) {
            hasFiles = true;
            const convertedId = 'converted-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            html += '<div class="file-directory-section mb-2">';
            html += `<button class="dataset-file-toggle" data-bs-toggle="collapse" data-bs-target="#${convertedId}" style="background: none; border: none; color: var(--fg-color); cursor: pointer; padding: 0.25rem 0.5rem; display: flex; align-items: center; width: 100%; font-weight: 500;">`;
            html += `<i class="fas fa-chevron-right me-2 file-chevron" style="font-size: 0.75rem; transition: transform 0.2s;"></i>`;
            html += `<span>Converted</span>`;
            html += `<span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">${this.countFiles(data.directories.converted.files)}</span>`;
            html += `</button>`;
            html += `<div class="collapse" id="${convertedId}">`;
            html += '<ul class="dataset-files-list" style="list-style: none; padding-left: 0;">';
            if (data.directories.converted.files.length > 0) {
                html += this.renderFileTreeInline(data.directories.converted.files, 'converted', 0, 'converted');
            } else {
                html += '<li class="text-muted small">No files in converted directory</li>';
            }
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
    renderFileTreeInline(items, basePath = '', level = 0, directory = 'upload') {
        let html = '';
        const uniqueId = 'files-' + basePath.replace(/[^a-zA-Z0-9]/g, '-') + '-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        
        for (const item of items) {
            if (item.type === 'directory') {
                const dirId = uniqueId + '-dir-' + item.path.replace(/[^a-zA-Z0-9]/g, '-');
                const hasChildren = item.children && item.children.length > 0;
                const hasExcludedFiles = item.has_excluded_files || false;
                const excludedCount = item.excluded_file_count || 0;
                
                html += `<li class="dataset-file-item dataset-file-dir" style="padding-left: ${level * 1.5}rem;">`;
                html += `<button class="dataset-file-toggle" data-bs-toggle="collapse" data-bs-target="#${dirId}" style="background: none; border: none; color: var(--fg-color); cursor: pointer; padding: 0.25rem 0.5rem; display: flex; align-items: center; width: 100%;">`;
                html += `<i class="fas fa-chevron-right me-2 file-chevron" style="font-size: 0.75rem; transition: transform 0.2s;"></i>`;
                html += `<i class="fas fa-folder me-2"></i>`;
                html += `<span>${this.escapeHtml(item.name)}</span>`;
                if (hasChildren) {
                    html += `<span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">${item.children.length}</span>`;
                }
                // Show indicator if directory has excluded files (like .bin files)
                if (hasExcludedFiles && excludedCount > 0) {
                    html += `<span class="text-muted small ms-2" title="${excludedCount} hidden file(s) (e.g., .bin files)">(${excludedCount} hidden)</span>`;
                }
                html += `</button>`;
                html += `<div class="collapse" id="${dirId}">`;
                if (hasChildren) {
                    html += '<ul class="dataset-files-list" style="list-style: none; padding-left: 0;">';
                    html += this.renderFileTreeInline(item.children, basePath, level + 1, directory);
                    html += '</ul>';
                } else if (hasExcludedFiles) {
                    // Show message if directory only has excluded files
                    html += '<ul class="dataset-files-list" style="list-style: none; padding-left: 0;">';
                    html += `<li class="text-muted small" style="padding-left: ${(level + 1) * 1.5}rem; font-style: italic; padding-top: 0.25rem;">Contains ${excludedCount} hidden file(s) (e.g., .bin files)</li>`;
                    html += '</ul>';
                }
                html += `</div>`;
                html += '</li>';
            } else {
                // Determine file type for click handling
                const fileName = item.name.toLowerCase();
                const textExtensions = ['.txt', '.json', '.idx', '.log', '.xml', '.csv', '.md', '.yaml', '.yml', '.ini', '.conf', '.cfg'];
                const imageExtensions = ['.tiff', '.tif', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];
                
                const isTextFile = textExtensions.some(ext => fileName.endsWith(ext));
                const isImageFile = imageExtensions.some(ext => fileName.endsWith(ext));
                const isClickable = isTextFile || isImageFile;
                
                // Build file path (relative to directory)
                const filePath = item.path || item.name;
                
                html += `<li class="dataset-file-item dataset-file-file ${isClickable ? 'clickable-file' : ''}" 
                             style="padding-left: ${(level + 1) * 1.5}rem; ${isClickable ? 'cursor: pointer;' : ''}"
                             ${isClickable ? `data-file-path="${this.escapeHtml(filePath)}" data-file-name="${this.escapeHtml(item.name)}" data-file-type="${isTextFile ? 'text' : 'image'}" data-directory="${directory}"` : ''}>`;
                html += `<i class="fas ${isTextFile ? 'fa-file-alt' : isImageFile ? 'fa-image' : 'fa-file'} me-2"></i>`;
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
     * Check if current user can download a dataset based on is_downloadable setting
     * @param {Object} dataset - Dataset object with is_downloadable, user, user_email, team_uuid fields
     * @param {string} currentUserEmail - Current user's email (optional, will fetch if not provided)
     * @param {string} currentUserTeamId - Current user's team ID (optional, will fetch if not provided)
     * @returns {boolean} - True if user can download, false otherwise
     */
    async canDownloadDataset(dataset, currentUserEmail = null, currentUserTeamId = null) {
        // Default to "only owner" if not set
        const isDownloadable = dataset.is_downloadable || 'only owner';
        
        // If public, anyone can download
        if (isDownloadable === 'public') {
            return true;
        }
        
        // Get current user info if not provided
        if (!currentUserEmail) {
            try {
                const userResponse = await fetch(`${getApiBasePath()}/user-info.php`);
                if (userResponse.ok) {
                    const userData = await userResponse.json();
                    if (userData.success) {
                        // Support both old format (direct fields) and new format (user object)
                        currentUserEmail = userData.user?.email || userData.email || userData.user?.id || userData.id;
                        currentUserTeamId = currentUserTeamId || userData.user?.team_id || userData.team_id;
                    }
                }
            } catch (error) {
                console.warn('Could not get user info for download check:', error);
                return false; // If we can't get user info, deny download
            }
        }
        
        if (!currentUserEmail) {
            return false; // No user email, can't download
        }
        
        // Check if user is the owner
        const isOwner = dataset.user === currentUserEmail || 
                       dataset.user_email === currentUserEmail || 
                       dataset.user_id === currentUserEmail;
        
        if (isDownloadable === 'only owner') {
            return isOwner;
        }
        
        if (isDownloadable === 'only team') {
            // Owner can always download
            if (isOwner) {
                return true;
            }
            // Check if user is in the same team
            if (dataset.team_uuid) {
                // Get user's team if not provided
                if (!currentUserTeamId) {
                    try {
                        const userResponse = await fetch(`${getApiBasePath()}/user-info.php`);
                        if (userResponse.ok) {
                            const userData = await userResponse.json();
                            if (userData.success) {
                                currentUserTeamId = userData.user?.team_id || userData.team_id;
                            }
                        }
                    } catch (error) {
                        console.warn('Could not get user team info:', error);
                    }
                }
                // Compare team IDs
                if (currentUserTeamId && dataset.team_uuid) {
                    return currentUserTeamId === dataset.team_uuid;
                }
            }
            return false;
        }
        
        // Default: only owner
        return isOwner;
    }

    /**
     * Select dataset - public method that can be called directly
     * This is an alias for handleDatasetSelection that accepts parameters directly
     */
    async selectDataset(datasetId, datasetName, datasetUuid, datasetServer) {
        // Create a fake dataset link object to pass to handleDatasetSelection
        const fakeLink = {
            dataset: {
                datasetId: datasetId,
                datasetName: datasetName,
                datasetUuid: datasetUuid,
                datasetServer: datasetServer
            }
        };
        return this.handleDatasetSelection(fakeLink);
    }

    /**
     * Select dataset - public method that can be called directly
     * This is an alias for handleDatasetSelection that accepts parameters directly
     */
    async selectDataset(datasetId, datasetName, datasetUuid, datasetServer) {
        // Create a fake dataset link object to pass to handleDatasetSelection
        const fakeLink = {
            dataset: {
                datasetId: datasetId,
                datasetName: datasetName,
                datasetUuid: datasetUuid,
                datasetServer: datasetServer
            }
        };
        return this.handleDatasetSelection(fakeLink);
    }

    /**
     * Handle dataset selection
     */
    async handleDatasetSelection(datasetLink) {
        const datasetId = datasetLink.dataset.datasetId;
        const datasetName = datasetLink.dataset.datasetName;
        const datasetUuid = datasetLink.dataset.datasetUuid;
        const datasetServer = datasetLink.dataset.datasetServer;
        
        // Check if we just loaded this dataset (prevent rapid re-clicks within 1 second)
        const currentId = this.currentDataset?.id;
        if (currentId === datasetId && this.lastLoadTime && (Date.now() - this.lastLoadTime) < 1000) {
            console.log('⏭️ Same dataset was just loaded, ignoring rapid re-click');
            return;
        }
        
        // Prevent multiple simultaneous selections
        if (this.isSelectingDataset) {
            // Check if it's the same dataset
            if (currentId === datasetId) {
                console.log('⏭️ Same dataset already being selected, ignoring duplicate click');
                return;
            }
            // Different dataset - queue it
            console.log('⏭️ Dataset selection already in progress, queuing this selection');
            this.pendingSelection = datasetLink;
            return;
        }
        
        // Mark as selecting (do this early to prevent duplicate calls)
        this.isSelectingDataset = true;
        
        try {
            // Update active state (only if datasetLink is a real DOM element)
            if (datasetLink && datasetLink.classList) {
                document.querySelectorAll('.dataset-link').forEach(link => {
                    link.classList.remove('active');
                });
                datasetLink.classList.add('active');
            }

        // Store current dataset
        this.currentDataset = {
            id: datasetId,
            name: datasetName,
            uuid: datasetUuid,
            server: datasetServer
        };

        // Fetch dataset details once and reuse for both details display and dashboard selection
        let datasetDetails = null;
        try {
            const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
            const data = await response.json();
            if (data.success && data.dataset) {
                datasetDetails = data.dataset;
                // Store full dataset details in currentDataset
                this.currentDataset.details = datasetDetails;
                
                // Handle google_drive_link for remote datasets
                const googleDriveLink = datasetDetails.google_drive_link || '';
                if (googleDriveLink) {
                    const containsHttp = googleDriveLink.includes('http');
                    const containsGoogle = googleDriveLink.includes('google.com');
                    
                    if (containsHttp && !containsGoogle) {
                        // Use the link as the UUID for remote loading
                        this.currentDataset.uuid = googleDriveLink;
                        this.currentDataset.server = 'true';
                        console.log('Using google_drive_link as UUID:', googleDriveLink);
                    }
                }
                
                console.log('Dataset details fetched:', {
                    preferred_dashboard: datasetDetails.preferred_dashboard,
                    has_preferred: !!datasetDetails.preferred_dashboard,
                    preferred_type: typeof datasetDetails.preferred_dashboard
                });
                
                // Update viewer-toolbar dropdown to match preferred_dashboard if it exists
                if (datasetDetails.preferred_dashboard && datasetDetails.preferred_dashboard.trim() !== '') {
                    const viewerTypeSelect = document.getElementById('viewerType');
                    if (viewerTypeSelect) {
                        // Try to find matching option (case-insensitive)
                        const preferredDashboard = datasetDetails.preferred_dashboard.trim();
                        console.log('Looking for preferred_dashboard in dropdown:', preferredDashboard);
                        console.log('Available options:', Array.from(viewerTypeSelect.options).map(opt => ({ value: opt.value, text: opt.text })));
                        
                        const option = Array.from(viewerTypeSelect.options).find(opt => 
                            opt.value === preferredDashboard || 
                            opt.value.toLowerCase() === preferredDashboard.toLowerCase() ||
                            opt.text.toLowerCase() === preferredDashboard.toLowerCase() ||
                            opt.text.toLowerCase().includes(preferredDashboard.toLowerCase())
                        );
                        if (option) {
                            viewerTypeSelect.value = option.value;
                            console.log('✅ Updated viewer-toolbar to match preferred_dashboard:', preferredDashboard, '->', option.value);
                        } else {
                            console.warn('⚠️ Could not find viewer-toolbar option for preferred_dashboard:', preferredDashboard);
                        }
                    }
                } else {
                    console.log('No preferred_dashboard set for this dataset');
                }
            }
        } catch (error) {
            console.warn('Could not fetch dataset details:', error);
        }

        // Load dataset details for display
        if (datasetDetails) {
            this.displayDatasetDetails(datasetDetails);
        } else {
            this.loadDatasetDetails(datasetId);
        }

        // Use smart dashboard selection FIRST, before loading
        // This ensures we get the best dashboard based on dimension, not the toolbar value
        // Use currentDataset.uuid which may have been updated with google_drive_link
        const effectiveUuid = this.currentDataset?.uuid || datasetUuid;
        const effectiveServer = this.currentDataset?.server || datasetServer;
        
        let selectedDashboard = null;
        if (window.viewerManager && this.selectDashboardForDataset) {
            try {
                selectedDashboard = await this.selectDashboardForDataset(
                    datasetId,
                    effectiveUuid,
                    datasetDetails?.preferred_dashboard || this.currentDataset?.preferred_dashboard || null
                );
                
                // Update toolbar selector to match the auto-selected dashboard
                if (window.viewerManager && typeof window.viewerManager.updateViewerSelector === 'function') {
                    window.viewerManager.updateViewerSelector(selectedDashboard);
                }
                
                console.log('✅ Smart selection complete. Selected dashboard:', selectedDashboard);
            } catch (error) {
                console.error('Error in smart dashboard selection:', error);
                // Fall back to loadDashboard's own selection logic
            }
        }

        // Load dashboard with the smart-selected dashboard (or let it use its own logic if selection failed)
        // Use effectiveUuid and effectiveServer which may have been updated
        await this.loadDashboard(datasetId, datasetName, effectiveUuid, effectiveServer, selectedDashboard, datasetDetails);

        // Record load time to prevent rapid re-clicks
        this.lastLoadTime = Date.now();

        console.log('Dataset selected:', this.currentDataset);
        
        } finally {
            // Clear selection flag
            this.isSelectingDataset = false;
            
            // Process any pending selection ONLY if it's different from what we just loaded
            if (this.pendingSelection) {
                const pending = this.pendingSelection;
                const pendingId = pending.dataset?.datasetId;
                this.pendingSelection = null;
                
                // Only process if it's a different dataset
                if (pendingId && pendingId !== this.currentDataset?.id) {
                    console.log('🔄 Processing pending dataset selection for different dataset:', pendingId);
                    // Use setTimeout to avoid recursion issues
                    setTimeout(() => {
                        this.handleDatasetSelection(pending);
                    }, 100);
                } else {
                    console.log('⏭️ Skipping pending selection - same dataset or invalid');
                }
            }
        }
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
    async displayDatasetDetails(dataset) {
        const detailsContainer = document.getElementById('datasetDetails');
        if (!detailsContainer) return;

        // Show loading state
        detailsContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="small text-muted mt-2">Loading folder options...</p>
            </div>
        `;

        // Load folders
        let folders = [];
        try {
            const foldersResponse = await fetch(`${getApiBasePath()}/get-folders.php`);
            const foldersData = await foldersResponse.json();
            if (foldersData.success) {
                folders = foldersData.folders || [];
            }
        } catch (error) {
            console.warn('Could not load folders:', error);
        }

        // Format tags for display/editing
        const tagsValue = Array.isArray(dataset.tags) ? dataset.tags.join(', ') : (dataset.tags || '');
        
        // Load dashboard options from API
        let dashboardOptions = [];
        let dashboardMap = {}; // Map dashboard ID to display name
        try {
            const dashResponse = await fetch(`${getApiBasePath()}/dashboards.php`);
            if (dashResponse.ok) {
                const dashData = await dashResponse.json();
                if (dashData.success && dashData.dashboards) {
                    // Filter enabled dashboards and remove duplicates
                    const seen = new Set();
                    dashboardOptions = dashData.dashboards
                        .filter(d => d.enabled && !seen.has(d.id))
                        .map(d => {
                            seen.add(d.id);
                            // Store mapping of ID to display name
                            // Also create reverse mapping: display_name -> id for preference matching
                            const displayName = d.display_name || d.name || d.id;
                            dashboardMap[d.id] = displayName;
                            // Also map display name variations to ID for preference matching
                            dashboardMap[displayName] = d.id;
                            dashboardMap[displayName.toLowerCase()] = d.id;
                            if (d.name && d.name !== displayName) {
                                dashboardMap[d.name] = d.id;
                                dashboardMap[d.name.toLowerCase()] = d.id;
                            }
                            return d.id;
                        });
                }
            }
        } catch (error) {
            console.warn('Could not load dashboards from API, using fallback:', error);
        }
        
        // Fallback if API fails
        if (dashboardOptions.length === 0) {
            dashboardOptions = [
                'OpenVisusSlice',
                '3DPlotly',
                '4D_Dashboard',
                '3DVTK',
                'magicscan'
            ];
            // Create fallback map
            dashboardOptions.forEach(id => {
                dashboardMap[id] = id; // Use ID as fallback display name
            });
        }
        
        // Get preferred dashboard display name
        const preferredDashboardId = dataset.preferred_dashboard || '';
        let preferredDashboardDisplayName = 'Default';
        
        if (preferredDashboardId) {
            // Try to get display name from dashboardMap first
            if (dashboardMap[preferredDashboardId]) {
                preferredDashboardDisplayName = dashboardMap[preferredDashboardId];
            } else if (window.viewerManager && window.viewerManager.viewers) {
                // Fallback to viewerManager if available
                const viewer = window.viewerManager.viewers[preferredDashboardId];
                if (viewer && viewer.name) {
                    preferredDashboardDisplayName = viewer.name;
                } else {
                    // Try case-insensitive match
                    const normalizedId = preferredDashboardId.toLowerCase();
                    const matchingViewer = Object.values(window.viewerManager.viewers).find(v => {
                        const vId = (v.id || '').toLowerCase();
                        const vType = (v.type || '').toLowerCase();
                        return vId === normalizedId || vType === normalizedId;
                    });
                    if (matchingViewer && matchingViewer.name) {
                        preferredDashboardDisplayName = matchingViewer.name;
                    } else {
                        preferredDashboardDisplayName = preferredDashboardId;
                    }
                }
            } else {
                preferredDashboardDisplayName = preferredDashboardId;
            }
        }
        
        // Build folder options HTML
        const folderOptions = `
            <option value="">-- No Folder --</option>
            ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}" ${(dataset.folder_uuid || '') === f.uuid ? 'selected' : ''}>${this.escapeHtml(f.name)}</option>`).join('')}
            <option value="__CREATE__">+ Create New Folder</option>
        `;
        
        // Get folder name for display
        const folderName = folders.find(f => f.uuid === dataset.folder_uuid)?.name || (dataset.folder_uuid || 'None');
        
        const html = `
            <div class="dataset-details">
                <h6><i class="fas fa-info-circle"></i> Dataset Details</h6>
                
                <!-- Dataset Name -->
                <div class="mb-2">
                    <h6 class="text-primary mb-2">${this.escapeHtml(dataset.name || 'Unnamed Dataset')}</h6>
                </div>
                
                <!-- Action Buttons (Share, Delete, Edit, Retry, Copy Dashboard Link) -->
                <div class="dataset-actions mb-3 pb-2 border-bottom">
                    <div class="btn-group btn-group-sm w-100" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" data-action="share" data-dataset-id="${dataset.id || dataset.uuid}">
                            <i class="fas fa-share"></i> Share
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-action="delete" data-dataset-id="${dataset.id || dataset.uuid}">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" id="editDatasetBtn" data-dataset-id="${dataset.id || dataset.uuid}">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary retry-conversion-details-btn" 
                                data-dataset-uuid="${dataset.uuid || dataset.id}"
                                data-dataset-name="${this.escapeHtml(dataset.name || 'Dataset')}">
                            <i class="fas fa-redo"></i> Retry
                        </button>
                    </div>
                    <div class="mt-2 d-flex gap-2">
                        <button type="button" class="btn btn-sm btn-outline-primary flex-grow-1" data-action="copy-dashboard-link" 
                                data-dataset-id="${dataset.id || dataset.uuid}"
                                data-dataset-uuid="${dataset.uuid || dataset.id}"
                                data-dataset-name="${this.escapeHtml(dataset.name || '')}"
                                data-dataset-server="${this.escapeHtml(dataset.server || '')}"
                                title="Copy direct link to open this dataset's dashboard in a new window">
                            <i class="fas fa-link"></i> Copy Dashboard Link
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-action="open-dashboard-link" 
                                data-dataset-id="${dataset.id || dataset.uuid}"
                                data-dataset-uuid="${dataset.uuid || dataset.id}"
                                data-dataset-name="${this.escapeHtml(dataset.name || '')}"
                                data-dataset-server="${this.escapeHtml(dataset.server || '')}"
                                title="Open this dataset's dashboard in a new tab">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                    </div>
                </div>
                
                <form id="datasetDetailsForm" class="dataset-details-form">
                    <input type="hidden" name="dataset_id" value="${dataset.id || dataset.uuid}">
                    
                    <!-- View Mode (Read-only) -->
                    <div id="datasetViewMode" class="dataset-view-mode">
                        <div class="detail-item mb-2">
                            <span class="detail-label">Name:</span>
                            <span class="detail-value">${this.escapeHtml(dataset.name || '')}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Tags:</span>
                            <span class="detail-value">${this.escapeHtml(tagsValue || 'None')}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Folder:</span>
                            <span class="detail-value">${this.escapeHtml(folderName)}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Team/Group:</span>
                            <span class="detail-value">${this.escapeHtml(dataset.team_uuid || 'None')}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Dimensions:</span>
                            <span class="detail-value">${this.escapeHtml(dataset.dimensions || 'N/A')}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Preferred Dashboard:</span>
                            <span class="detail-value">${this.escapeHtml(preferredDashboardDisplayName)}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Size:</span>
                            <span class="detail-value">${this.formatFileSize(dataset.data_size || 0)}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Created:</span>
                            <span class="detail-value">${this.formatDate(dataset.created_at || dataset.time)}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Sensor:</span>
                            <span class="detail-value">${this.escapeHtml(dataset.sensor || 'Unknown')}</span>
                        </div>
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">Status:</span>
                            <span class="badge bg-${this.getStatusColor(dataset.status)}">${this.escapeHtml(dataset.status || 'unknown')}</span>
                        </div>
                        
                        ${dataset.compression_status ? `
                        <div class="detail-item mb-2">
                            <span class="detail-label">Compression Status:</span>
                            <span class="badge bg-${this.getStatusColor(dataset.compression_status)}">${this.escapeHtml(dataset.compression_status || 'unknown')}</span>
                        </div>
                        ` : ''}
                        
                        ${dataset.google_drive_link ? `
                        <div class="detail-item mb-2">
                            <span class="detail-label">Data Link:</span>
                            <span class="detail-value small text-muted" style="word-break: break-all;">${this.escapeHtml(dataset.google_drive_link)}</span>
                        </div>
                        ` : ''}
                        
                        ${dataset.is_public !== undefined ? `
                        <div class="detail-item mb-2">
                            <span class="detail-label">Public:</span>
                            <span class="detail-value">
                                <span class="badge bg-${dataset.is_public ? 'success' : 'secondary'}">
                                    ${dataset.is_public ? 'Yes' : 'No'}
                                </span>
                            </span>
                        </div>
                        ` : ''}
                        
                        <div class="detail-item mb-2">
                            <span class="detail-label">UUID:</span>
                            <span class="detail-value small text-muted" style="word-break: break-all;">${this.escapeHtml(dataset.uuid || '')}</span>
                        </div>
                    </div>
                    
                    <!-- Edit Mode (Editable Fields) -->
                    <div id="datasetEditMode" class="dataset-edit-mode" style="display: none;">
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
                            <select class="form-select form-select-sm" name="folder_uuid" id="datasetFolderSelect">
                                ${folderOptions}
                            </select>
                            <div id="datasetNewFolderInput" class="mt-2" style="display: none;">
                                <input type="text" class="form-control form-control-sm" name="new_folder_name" 
                                       placeholder="Enter new folder name" id="datasetNewFolderName">
                            </div>
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label small">Team/Group:</label>
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
                                ${dashboardOptions.map(opt => {
                                    // Use dashboard ID as value, but display name as text
                                    const displayName = dashboardMap[opt] || opt;
                                    // Check if this option matches the saved preferred_dashboard
                                    // Try both ID and display name matching
                                    const isSelected = (dataset.preferred_dashboard || '').toLowerCase() === opt.toLowerCase() ||
                                                      (dataset.preferred_dashboard || '').toLowerCase() === displayName.toLowerCase();
                                    return `<option value="${opt}" ${isSelected ? 'selected' : ''}>${displayName}</option>`;
                                }).join('')}
                            </select>
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label small">Data Link (Google Drive/Remote):</label>
                            <input type="url" class="form-control form-control-sm" name="google_drive_link" 
                                   value="${this.escapeHtml(dataset.google_drive_link || '')}" 
                                   placeholder="http://example.com/mod_visus?dataset=...">
                            <small class="form-text text-muted">Link to remote data (e.g., S3, external server). If provided and not a Google Drive link, data will be loaded remotely.</small>
                        </div>
                        
                        <div class="mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="is_public" id="datasetIsPublic" 
                                       ${dataset.is_public ? 'checked' : ''}>
                                <label class="form-check-label" for="datasetIsPublic">
                                    Public
                                </label>
                                <small class="form-text text-muted d-block">Make this dataset publicly accessible</small>
                            </div>
                        </div>
                        
                        <div class="mb-2">
                            <label class="form-label">Download Permission:</label>
                            <select class="form-select form-select-sm" name="is_downloadable" id="datasetIsDownloadable">
                                <option value="only owner" ${(dataset.is_downloadable || 'only owner') === 'only owner' ? 'selected' : ''}>Only Owner</option>
                                <option value="only team" ${dataset.is_downloadable === 'only team' ? 'selected' : ''}>Only Team</option>
                                <option value="public" ${dataset.is_downloadable === 'public' ? 'selected' : ''}>Public</option>
                            </select>
                            <small class="form-text text-muted d-block">Who can download this dataset</small>
                        </div>
                        
                        <div class="mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="convert_to_idx" id="datasetConvertToIdx">
                                <label class="form-check-label" for="datasetConvertToIdx">
                                    Convert to IDX
                                </label>
                                <small class="form-text text-muted d-block">Queue this dataset for conversion to IDX format</small>
                            </div>
                        </div>
                        
                        <div class="d-flex gap-2 mt-3">
                            <button type="submit" class="btn btn-sm btn-primary">
                                <i class="fas fa-save"></i> Save Changes
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-secondary" id="cancelEditBtn">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        `;

        detailsContainer.innerHTML = html;
        
        // Store dataset data for edit mode toggle
        this.currentDatasetDetails = dataset;
        
        // Attach edit mode toggle
        const editBtn = detailsContainer.querySelector('#editDatasetBtn');
        const cancelBtn = detailsContainer.querySelector('#cancelEditBtn');
        const viewMode = detailsContainer.querySelector('#datasetViewMode');
        const editMode = detailsContainer.querySelector('#datasetEditMode');
        
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                if (viewMode) viewMode.style.display = 'none';
                if (editMode) editMode.style.display = 'block';
                editBtn.style.display = 'none'; // Hide edit button when in edit mode
            });
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                if (viewMode) viewMode.style.display = 'block';
                if (editMode) editMode.style.display = 'none';
                if (editBtn) editBtn.style.display = 'block'; // Show edit button when back to view mode
            });
        }
        
        // Attach folder dropdown event listener
        const folderSelect = detailsContainer.querySelector('#datasetFolderSelect');
        const newFolderInput = detailsContainer.querySelector('#datasetNewFolderInput');
        if (folderSelect && newFolderInput) {
            folderSelect.addEventListener('change', (e) => {
                if (e.target.value === '__CREATE__') {
                    newFolderInput.style.display = 'block';
                } else {
                    newFolderInput.style.display = 'none';
                }
            });
        }
        
        // Attach form submit handler
        const form = detailsContainer.querySelector('#datasetDetailsForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveDatasetChanges(form, dataset.id || dataset.uuid);
            });
        }
        
        // Attach retry button handler
        const retryBtn = detailsContainer.querySelector('.retry-conversion-details-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const datasetUuid = retryBtn.getAttribute('data-dataset-uuid');
                const datasetName = retryBtn.getAttribute('data-dataset-name');
                this.retryConversion(datasetUuid, datasetName, retryBtn);
            });
        }
    }
    
    /**
     * Save dataset changes
     */
    async saveDatasetChanges(form, datasetId) {
        const formData = new FormData(form);
        
        // Handle folder creation if needed
        // When __CREATE__ is selected, use the folder name as the folder_uuid
        // (folders are identified by their name/UUID in the system)
        let folderUuid = formData.get('folder_uuid');
        if (folderUuid === '__CREATE__') {
            const newFolderName = formData.get('new_folder_name');
            if (!newFolderName || !newFolderName.trim()) {
                alert('Please enter a folder name');
                return;
            }
            // Use the folder name as the UUID (folders are identified by name)
            folderUuid = newFolderName.trim();
        }
        
        // Get checkbox values
        const isPublic = formData.get('is_public') === 'on';
        const convertToIdx = formData.get('convert_to_idx') === 'on';
        const isDownloadable = formData.get('is_downloadable') || 'only owner';
        
        const updateData = {
            dataset_id: datasetId,
            name: formData.get('name'),
            tags: formData.get('tags'),
            folder_uuid: folderUuid || null, // Allow null to remove folder
            team_uuid: formData.get('team_uuid'),
            dimensions: formData.get('dimensions'),
            preferred_dashboard: formData.get('preferred_dashboard'),
            google_drive_link: formData.get('google_drive_link') || null,
            is_public: isPublic,
            is_downloadable: isDownloadable
        };
        
        // If convert_to_idx is checked, set status to "conversion queued"
        if (convertToIdx) {
            updateData.status = 'conversion queued';
        }
        
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
    async loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, dashboardTypeOverride = null, datasetDetails = null) {
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
        // Priority order:
        // 1. Explicit override (if provided)
        // 2. Dataset's preferred_dashboard field (from visstoredatas collection)
        // 3. Selected dashboard from viewer-toolbar dropdown
        // 4. Determine from dataset dimensions (if 4D)
        // 5. Fallback to OpenVisusSlice
        
        let selectedDashboard = dashboardTypeOverride;
        
        // If no override, check dataset's preferred_dashboard field
        if (!selectedDashboard) {
            let dataset = datasetDetails;
            
            // If dataset details not provided, try to get from currentDataset or fetch
            if (!dataset && this.currentDataset && this.currentDataset.details) {
                dataset = this.currentDataset.details;
            }
            
            // If still no dataset, fetch it
            if (!dataset) {
                try {
                    const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
                    const data = await response.json();
                    if (data.success && data.dataset) {
                        dataset = data.dataset;
                        // Cache it in currentDataset
                        if (this.currentDataset) {
                            this.currentDataset.details = dataset;
                        }
                    }
                } catch (error) {
                    console.warn('Could not fetch dataset details for dashboard selection:', error);
                }
            }
            
            // Check preferred_dashboard field (must be non-empty string)
            if (dataset && dataset.preferred_dashboard && dataset.preferred_dashboard.trim() !== '') {
                let preferredValue = dataset.preferred_dashboard.trim();
                
                // Normalize the preferred_dashboard value to match dashboard options
                // Map common variations to standard names
                const dashboardNormalizations = {
                    '4d_dashboard': '4D_Dashboard',
                    '4D_dashboard': '4D_Dashboard',
                    '4d_Dashboard': '4D_Dashboard',
                    'openvisus': 'OpenVisusSlice',
                    'OpenVisus': 'OpenVisusSlice',
                    'openvisusslice': 'OpenVisusSlice',
                    '3d_plotly': '3DPlotly',  // Map to ID, not display name
                    '3D Plotly': '3DPlotly',
                    'plotly': '3DPlotly',
                    '3D Plotly Explorer': '3DPlotly',  // User might have selected this variation
                    '3d plotly explorer': '3DPlotly'
                };
                
                // Check if we need to normalize
                const normalized = dashboardNormalizations[preferredValue.toLowerCase()] || preferredValue;
                
                // Try to find matching dashboard in viewer-manager if available
                if (window.viewerManager && window.viewerManager.viewers) {
                    // Check if normalized value exists in viewers
                    const matchingViewer = Object.values(window.viewerManager.viewers).find(v => {
                        const vId = (v.id || '').toLowerCase();
                        const vType = (v.type || '').toLowerCase();
                        const vName = (v.name || '').toLowerCase();
                        const preferredLower = normalized.toLowerCase();
                        return vId === preferredLower || 
                               vType === preferredLower ||
                               vName === preferredLower ||
                               vId === preferredValue.toLowerCase() ||
                               vType === preferredValue.toLowerCase() ||
                               vName === preferredValue.toLowerCase();
                    });
                    
                    if (matchingViewer) {
                        selectedDashboard = matchingViewer.id || matchingViewer.type || normalized;
                        console.log('✅ Using preferred_dashboard (normalized):', preferredValue, '->', selectedDashboard);
                    } else {
                        selectedDashboard = normalized;
                        console.log('✅ Using preferred_dashboard (as-is):', selectedDashboard);
                    }
                } else {
                    selectedDashboard = normalized;
                    console.log('✅ Using preferred_dashboard (normalized, no viewer-manager):', preferredValue, '->', selectedDashboard);
                }
            } else if (dataset) {
                console.log('Dataset has no preferred_dashboard or it is empty:', dataset.preferred_dashboard);
            }
        }
        
        // If still no dashboard, check viewer-toolbar dropdown
        if (!selectedDashboard) {
            const viewerTypeSelect = document.getElementById('viewerType');
            if (viewerTypeSelect && viewerTypeSelect.value) {
                selectedDashboard = viewerTypeSelect.value;
                console.log('Using dashboard from viewer-toolbar:', selectedDashboard);
            }
        }
        
        // If still no dashboard, try to determine from dataset dimensions
        if (!selectedDashboard) {
            let dataset = datasetDetails || (this.currentDataset && this.currentDataset.details);
            if (dataset && dataset.dimensions) {
                const dimensions = dataset.dimensions || '';
                // If dataset is 4D, default to 4D_Dashboard
                if (dimensions.toUpperCase().includes('4D')) {
                    selectedDashboard = '4D_Dashboard';
                    console.log('Using 4D_Dashboard based on dimensions');
                }
            }
        }
        
        // Fallback to OpenVisusSlice if nothing else selected
        if (!selectedDashboard) {
            selectedDashboard = 'OpenVisusSlice';
            console.log('Using default dashboard: OpenVisusSlice');
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
     * Smart dashboard selection based on dataset dimension and user preferences
     * 
     * PRIORITY ORDER:
     * 1. Dataset dimension compatibility (filter dashboards by supported_dimensions)
     * 2. Single compatible dashboard (if only one matches dimension, use it)
     * 3. User's preferred_dashboard (if compatible with dimension)
     * 4. OpenVisusSlice (most general dashboard, works with all dimensions)
     * 5. First available compatible dashboard (as last resort)
     * 
     * @param {string} datasetId - Dataset ID
     * @param {string} datasetUuid - Dataset UUID
     * @param {string} preferredDashboardId - User's preferred dashboard ID (optional)
     * @returns {Promise<string>} Selected dashboard ID
     */
    async selectDashboardForDataset(datasetId, datasetUuid, preferredDashboardId = null) {
        try {
            // Step 1: Get dataset dimension
            const datasetDimension = await this.getDatasetDimension(datasetId, datasetUuid);
            console.log(`📊 Dataset dimension: ${datasetDimension}D`);
            
            if (!datasetDimension) {
                console.warn('⚠️ Could not determine dataset dimension, using OpenVisusSlice as default/general dashboard');
                // OpenVisusSlice is the most general dashboard - use it as default
                if (window.viewerManager && window.viewerManager.viewers && window.viewerManager.viewers['OpenVisusSlice']) {
                    return 'OpenVisusSlice';
                }
                // Fallback to toolbar selector or first available
                const viewerType = document.getElementById('viewerType');
                return viewerType ? viewerType.value : (Object.keys(window.viewerManager.viewers)[0] || 'OpenVisusSlice');
            }
            
            // Step 2: Get all dashboards and filter by supported dimensions
            const compatibleDashboards = await this.getCompatibleDashboards(datasetDimension);
            console.log(`✅ Found ${compatibleDashboards.length} compatible dashboard(s) for ${datasetDimension}D:`, compatibleDashboards.map(d => d.id));
            
            if (compatibleDashboards.length === 0) {
                console.warn(`⚠️ No dashboards found for ${datasetDimension}D, using OpenVisusSlice as default/general dashboard`);
                // OpenVisusSlice is the most general dashboard - use it as default
                if (window.viewerManager && window.viewerManager.viewers && window.viewerManager.viewers['OpenVisusSlice']) {
                    return 'OpenVisusSlice';
                }
                // Fallback to toolbar selector or first available
                const viewerType = document.getElementById('viewerType');
                return viewerType ? viewerType.value : (Object.keys(window.viewerManager.viewers)[0] || 'OpenVisusSlice');
            }
            
            // Step 3: If only one compatible dashboard, use it
            if (compatibleDashboards.length === 1) {
                console.log(`✅ Only one compatible dashboard, selecting: ${compatibleDashboards[0].id}`);
                return compatibleDashboards[0].id;
            }
            
            // Step 4: Multiple dashboards - check user preference
            if (preferredDashboardId) {
                // Map old dashboard names and display names to dashboard IDs for backwards compatibility
                // This should match what users see in the upload dropdown
                const dashboardNameMapping = {
                    // Old dashboard IDs
                    '4D_Dashboard': '4d_dashboardLite',
                    '4d_dashboard': '4d_dashboardLite',
                    '4D_dashboard': '4d_dashboardLite',
                    'Magicscan': 'magicscan',
                    'magicscan': 'magicscan',
                    // Display names to IDs (from dashboards-list.json)
                    '3D Plotly Explorer': '3DPlotly',
                    '3D Plotly Dashboard': '3DPlotly',
                    '3d plotly explorer': '3DPlotly',
                    '3d plotly dashboard': '3DPlotly',
                    '3D Plotly': '3DPlotly',
                    '3d plotly': '3DPlotly',
                    'plotly': '3DPlotly',
                    '3D VTK Dashboard': '3DVTK',
                    '3d vtk dashboard': '3DVTK',
                    '3D VTK': '3DVTK',
                    '3d vtk': '3DVTK',
                    '4D Dashboard (New)': '4d_dashboardLite',
                    '4D Dashboard': '4d_dashboardLite',
                    '4d dashboard (new)': '4d_dashboardLite',
                    '4d dashboard': '4d_dashboardLite',
                    'OpenVisus Slice Dashboard': 'OpenVisusSlice',
                    'openvisus slice dashboard': 'OpenVisusSlice',
                    'OpenVisus Slice': 'OpenVisusSlice',
                    'openvisus slice': 'OpenVisusSlice',
                    'MagicScan Dashboard': 'magicscan',
                    'magicscan dashboard': 'magicscan',
                    'MagicScan': 'magicscan',
                    'magicscan': 'magicscan'
                };
                
                // Try mapped name first (check both original and lowercase)
                let mappedName = dashboardNameMapping[preferredDashboardId];
                if (!mappedName) {
                    mappedName = dashboardNameMapping[preferredDashboardId.toLowerCase()];
                }
                if (!mappedName) {
                    mappedName = preferredDashboardId;
                }
                
                // Try multiple matching strategies
                const preferredDashboard = compatibleDashboards.find(d => {
                    const dId = (d.id || '').toLowerCase();
                    const dName = (d.name || '').toLowerCase();
                    const dDisplayName = (d.display_name || '').toLowerCase();
                    const preferredLower = preferredDashboardId.toLowerCase();
                    const mappedLower = mappedName.toLowerCase();
                    
                    // Try exact ID match
                    if (dId === mappedLower || dId === preferredLower) {
                        return true;
                    }
                    // Try name match
                    if (dName === preferredLower || dName === mappedLower) {
                        return true;
                    }
                    // Try display name match
                    if (dDisplayName === preferredLower || dDisplayName === mappedLower) {
                        return true;
                    }
                    // Try partial match (e.g., "3D Plotly Explorer" contains "plotly")
                    if (preferredLower.includes('plotly') && (dId.includes('plotly') || dId === '3dplotly')) {
                        return true;
                    }
                    if (preferredLower.includes('vtk') && dId.includes('vtk')) {
                        return true;
                    }
                    if ((preferredLower.includes('4d') || preferredLower.includes('4 d')) && dId.includes('dashboard')) {
                        return true;
                    }
                    if ((preferredLower.includes('openvisus') || preferredLower.includes('slice')) && dId.includes('openvisus')) {
                        return true;
                    }
                    if ((preferredLower.includes('magic') || preferredLower.includes('scan')) && dId.includes('magic')) {
                        return true;
                    }
                    return false;
                });
                
                if (preferredDashboard) {
                    console.log(`✅ User preference found and compatible: ${preferredDashboardId} -> ${preferredDashboard.id}`);
                    return preferredDashboard.id;
                } else {
                    console.log(`⚠️ User preferred dashboard (${preferredDashboardId}) not found in compatible dashboards for ${datasetDimension}D, selecting from available options`);
                }
            }
            
            // Step 5: No preference or preference not compatible - prioritize OpenVisusSlice as the most general dashboard
            // Priority order:
            // 1. OpenVisusSlice (most general, works with all dimensions)
            // 2. Other compatible dashboards that exist in viewerManager
            // 3. First compatible dashboard as last resort
            
            // First, try to find OpenVisusSlice in compatible dashboards
            let selectedDashboard = compatibleDashboards.find(d => {
                const dashboardId = (d.id || '').toLowerCase();
                return dashboardId === 'openvisusslice' || dashboardId === 'openvisus' || dashboardId === 'openvisusslice';
            });
            
            // If OpenVisusSlice is compatible and available, use it
            if (selectedDashboard) {
                // Verify it exists in viewerManager
                if (window.viewerManager && window.viewerManager.viewers) {
                    if (window.viewerManager.viewers[selectedDashboard.id]) {
                        console.log(`✅ Selected OpenVisusSlice as general/default dashboard: ${selectedDashboard.id}`);
                        return selectedDashboard.id;
                    }
                } else {
                    // viewerManager not available, but we found it in compatible list
                    console.log(`✅ Selected OpenVisusSlice as general/default dashboard: ${selectedDashboard.id}`);
                    return selectedDashboard.id;
                }
            }
            
            // If OpenVisusSlice not compatible or not found, pick first available compatible dashboard
            // Validate that the selected dashboard actually exists in viewerManager
            selectedDashboard = compatibleDashboards.find(d => {
                // Check if dashboard exists in viewerManager
                if (window.viewerManager && window.viewerManager.viewers) {
                    return window.viewerManager.viewers[d.id] !== undefined;
                }
                return true;  // If viewerManager not available, assume it exists
            }) || compatibleDashboards[0];  // Fallback to first if none found in viewerManager
            
            if (selectedDashboard) {
                console.log(`✅ Selected dashboard: ${selectedDashboard.id} (${selectedDashboard.display_name})`);
                return selectedDashboard.id;
            } else {
                console.warn(`⚠️ No valid dashboard found in viewerManager, using first compatible`);
                return compatibleDashboards[0].id;
            }
            
        } catch (error) {
            console.error('❌ Error in smart dashboard selection:', error);
            // Fallback to OpenVisusSlice as the most general/default dashboard
            if (window.viewerManager && window.viewerManager.viewers && window.viewerManager.viewers['OpenVisusSlice']) {
                console.log('✅ Using OpenVisusSlice as fallback default dashboard');
                return 'OpenVisusSlice';
            }
            // Last resort: toolbar selector or first available
            const viewerType = document.getElementById('viewerType');
            return viewerType ? viewerType.value : (Object.keys(window.viewerManager.viewers)[0] || 'OpenVisusSlice');
        }
    }

    /**
     * Get dataset dimension by checking nexus file or dataset metadata
     * @param {string} datasetId - Dataset ID
     * @param {string} datasetUuid - Dataset UUID
     * @returns {Promise<number|null>} Dataset dimension (1, 2, 3, or 4) or null if cannot determine
     */
    async getDatasetDimension(datasetId, datasetUuid) {
        try {
            // Try to get dimension from dataset details using dataset_id (not uuid)
            console.log(`🔍 Fetching dimension for dataset_id: ${datasetId}, uuid: ${datasetUuid}`);
            const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
            
            if (!response.ok) {
                console.warn(`⚠️ dataset-details.php returned status ${response.status}`);
                return null;
            }
            
            const data = await response.json();
            console.log('🔍 Raw API response:', data);
            console.log('🔍 Response success:', data.success);
            console.log('🔍 Response has dataset:', !!data.dataset);
            
            if (data.success && data.dataset) {
                // Debug: log what's in the dataset object
                console.log('🔍 Dataset object keys:', Object.keys(data.dataset));
                console.log('🔍 Dataset dimensions field:', data.dataset.dimensions, 'type:', typeof data.dataset.dimensions);
                console.log('🔍 Full dataset object:', JSON.stringify(data.dataset, null, 2));
                
                // Check if dimensions is stored in metadata (field is "dimensions" plural, format is "4D", "3D", etc.)
                if (data.dataset.dimensions) {
                    // Parse dimensions string (e.g., "4D", "3D", "2D", "1D") to extract number
                    const dimensionsStr = String(data.dataset.dimensions).trim().toUpperCase();
                    console.log('🔍 Parsing dimensions string:', dimensionsStr);
                    const dimensionMatch = dimensionsStr.match(/(\d+)D?/);
                    if (dimensionMatch && dimensionMatch[1]) {
                        const dimension = parseInt(dimensionMatch[1]);
                        if (dimension >= 1 && dimension <= 4) {
                            console.log(`✅ Found dimension from dataset.dimensions: ${dimensionsStr} -> ${dimension}D`);
                            return dimension;
                        } else {
                            console.warn(`⚠️ Dimension out of range: ${dimension} (expected 1-4)`);
                        }
                    } else {
                        console.warn(`⚠️ Could not parse dimension from: ${dimensionsStr}`);
                    }
                } else {
                    console.log('⚠️ Dataset.dimensions field is missing or empty');
                }
                
                // Also check for singular "dimension" field (for backwards compatibility)
                if (data.dataset.dimension) {
                    const dim = parseInt(data.dataset.dimension);
                    if (dim >= 1 && dim <= 4) {
                        console.log(`✅ Found dimension from dataset.dimension: ${dim}D`);
                        return dim;
                    }
                }
                
                // Try to get dimension from API endpoint that can read nexus file
                try {
                    console.log(`🔍 Trying get_dataset_dimension.php for uuid: ${datasetUuid}`);
                    const dimensionResponse = await fetch(`${getApiBasePath()}/get_dataset_dimension.php?uuid=${datasetUuid}`);
                    if (dimensionResponse.ok) {
                        const dimensionData = await dimensionResponse.json();
                        console.log('🔍 get_dataset_dimension.php response:', dimensionData);
                        if (dimensionData.success && dimensionData.dimension) {
                            const dim = parseInt(dimensionData.dimension);
                            if (dim >= 1 && dim <= 4) {
                                console.log(`✅ Found dimension from get_dataset_dimension.php: ${dim}D`);
                                return dim;
                            }
                        }
                    } else {
                        console.warn(`⚠️ get_dataset_dimension.php returned status ${dimensionResponse.status}`);
                    }
                } catch (dimError) {
                    // API endpoint might not exist yet, continue with other methods
                    console.log('⚠️ Dimension API endpoint error:', dimError.message);
                }
                
                // Try to infer from file structure or names
                // This is a fallback - ideally dimension should be stored in metadata
                if (data.dataset.files && Array.isArray(data.dataset.files)) {
                    // Look for .nxs files
                    const nxsFiles = data.dataset.files.filter(f => f.name && f.name.endsWith('.nxs'));
                    if (nxsFiles.length > 0) {
                        // Could try to read nexus file header, but that's expensive
                        // For now, return null and let system use default
                    }
                }
            } else {
                console.warn('⚠️ API response missing success or dataset:', { success: data.success, hasDataset: !!data.dataset });
            }
            
            return null;
        } catch (error) {
            console.error('Error getting dataset dimension:', error);
            return null;
        }
    }

    /**
     * Get dashboards compatible with a given dimension
     * @param {number} dimension - Dataset dimension (1, 2, 3, or 4)
     * @returns {Promise<Array>} Array of compatible dashboard objects
     */
    async getCompatibleDashboards(dimension) {
        try {
            // Load dashboard registry
            const dashResponse = await fetch(`${getApiBasePath()}/dashboards.php`);
            const dashData = await dashResponse.json();
            
            if (!dashData.success) {
                console.warn('⚠️ Could not load dashboard registry');
                return [];
            }
            
            // dashData.dashboards might be an array or object
            const dashboards = Array.isArray(dashData.dashboards) 
                ? dashData.dashboards 
                : Object.entries(dashData.dashboards || {}).map(([id, dash]) => ({ id, ...dash }));
            
            const dimensionStr = `${dimension}D`;
            const compatibleDashboards = [];
            
            // Check each dashboard's supported_dimensions
            for (const dashboard of dashboards) {
                const dashboardId = dashboard.id || dashboard.name;
                if (!dashboardId || !dashboard.enabled) {
                    continue; // Skip disabled dashboards or those without ID
                }
                
                // IMPORTANT: Only include dashboards that actually exist in viewerManager
                // This ensures backwards compatibility - old dashboards won't be selected
                if (window.viewerManager && window.viewerManager.viewers) {
                    if (!window.viewerManager.viewers[dashboardId]) {
                        // Dashboard not in viewerManager - skip it (it's been removed/renamed)
                        console.log(`⚠️ Skipping ${dashboardId} - not found in viewerManager (may have been removed)`);
                        continue;
                    }
                }
                
                // Check supported_dimensions from the dashboard registry response
                // The dashboards.php API should already include this info in the dashboard object
                // If not available, we'll include all dashboards that are in viewerManager
                // (fallback for dashboards without explicit dimension restrictions)
                const supportedDimensions = dashboard.supported_dimensions || dashboard.config?.supported_dimensions || [];
                
                // If no supported_dimensions specified, assume dashboard supports all dimensions
                // Otherwise, check if it supports the dataset dimension
                if (supportedDimensions.length === 0 || supportedDimensions.includes(dimensionStr)) {
                    compatibleDashboards.push({
                        id: dashboardId,
                        name: dashboard.name || dashboardId,
                        display_name: dashboard.display_name || dashboard.name || dashboardId,
                        config: dashboard.config || null,
                        supported_dimensions: supportedDimensions
                    });
                } else {
                    console.log(`⚠️ Dashboard ${dashboardId} does not support ${dimensionStr} (supports: ${supportedDimensions.join(', ')})`);
                }
            }
            
            // Sort by display name for consistent ordering
            compatibleDashboards.sort((a, b) => a.display_name.localeCompare(b.display_name));
            
            return compatibleDashboards;
            
        } catch (error) {
            console.error('Error getting compatible dashboards:', error);
            return [];
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
     * Copy dashboard link to clipboard
     */
    async copyDashboardLink(datasetId, buttonData = {}) {
        try {
            // Get dataset details
            let dataset = this.currentDataset?.details || this.currentDataset;
            
            // If we don't have full details, fetch them
            if (!dataset || !dataset.uuid) {
                // Use button data if available
                if (buttonData.uuid) {
                    dataset = {
                        uuid: buttonData.uuid,
                        name: buttonData.name || 'Dataset',
                        server: buttonData.server || '',
                        preferred_dashboard: this.currentDataset?.details?.preferred_dashboard
                    };
                } else {
                    const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
                    const data = await response.json();
                    if (data.success && data.dataset) {
                        dataset = data.dataset;
                    } else {
                        throw new Error('Failed to fetch dataset details');
                    }
                }
            }
            
            const datasetUuid = dataset.uuid || buttonData.uuid || datasetId;
            const datasetName = dataset.name || buttonData.name || 'Dataset';
            const datasetServer = dataset.server || buttonData.server || '';
            
            // Determine the default dashboard
            // Priority: 1. Currently loaded dashboard (from viewerManager), 2. Toolbar selector, 3. dataset.preferred_dashboard, 4. smart selection, 5. OpenVisusSlice
            let dashboardType = null;
            
            // First, try to get the currently loaded dashboard from viewerManager
            if (window.viewerManager && window.viewerManager.currentDashboard) {
                dashboardType = window.viewerManager.currentDashboard;
                console.log('Using dashboard from viewerManager.currentDashboard:', dashboardType);
            }
            
            // If not available, try the toolbar selector
            if (!dashboardType) {
                const viewerTypeSelect = document.getElementById('viewerType');
                if (viewerTypeSelect && viewerTypeSelect.value) {
                    dashboardType = viewerTypeSelect.value;
                    console.log('Using dashboard from toolbar selector:', dashboardType);
                }
            }
            
            // If not available, try preferred_dashboard (but normalize it to dashboard ID)
            if (!dashboardType && dataset.preferred_dashboard && dataset.preferred_dashboard.trim() !== '') {
                const preferredValue = dataset.preferred_dashboard.trim();
                console.log('Using preferred_dashboard:', preferredValue);
                
                // Normalize preferred_dashboard display name to dashboard ID
                // Map display names to dashboard IDs
                const dashboardNameToId = {
                    '3D Plotly Explorer': '3DPlotly',
                    '3D Plotly Dashboard': '3DPlotly',
                    '3d plotly explorer': '3DPlotly',
                    '3d plotly dashboard': '3DPlotly',
                    '3D Plotly': '3DPlotly',
                    '3d plotly': '3DPlotly',
                    'plotly': '3DPlotly',
                    '3D VTK Dashboard': '3DVTK',
                    '3d vtk dashboard': '3DVTK',
                    '3D VTK': '3DVTK',
                    '3d vtk': '3DVTK',
                    '4D Dashboard (New)': '4d_dashboardLite',
                    '4D Dashboard': '4d_dashboardLite',
                    '4d dashboard (new)': '4d_dashboardLite',
                    '4d dashboard': '4d_dashboardLite',
                    '4D Dashboard': '4d_dashboardLite',
                    '4d_dashboardLite': '4d_dashboardLite',  // Direct ID match
                    '4D_dashboardLite': '4d_dashboardLite',
                    'OpenVisus Slice Dashboard': 'OpenVisusSlice',
                    'openvisus slice dashboard': 'OpenVisusSlice',
                    'OpenVisus Slice': 'OpenVisusSlice',
                    'openvisus slice': 'OpenVisusSlice',
                    'OpenVisusSlice': 'OpenVisusSlice',  // Direct ID match
                    'MagicScan Dashboard': 'magicscan',
                    'magicscan dashboard': 'magicscan',
                    'MagicScan': 'magicscan',
                    'magicscan': 'magicscan',
                    'magicscan': 'magicscan'  // Direct ID match
                };
                
                // Try direct mapping first (exact match, then case-insensitive)
                dashboardType = dashboardNameToId[preferredValue] || dashboardNameToId[preferredValue.toLowerCase()];
                
                // If still not found and preferredValue looks like a dashboard ID, use it directly
                if (!dashboardType && (preferredValue.includes('_') || preferredValue.match(/^[A-Z][a-zA-Z0-9_]+$/))) {
                    dashboardType = preferredValue;
                    console.log('Using preferred_dashboard as direct dashboard ID:', dashboardType);
                }
                
                // If not found, try to find in viewerManager by name
                if (!dashboardType && window.viewerManager && window.viewerManager.viewers) {
                    const preferredLower = preferredValue.toLowerCase();
                    const matchingViewer = Object.values(window.viewerManager.viewers).find(v => {
                        const vId = (v.id || '').toLowerCase();
                        const vName = (v.name || '').toLowerCase();
                        const vDisplayName = (v.display_name || '').toLowerCase();
                        // Try exact match first
                        if (vName === preferredLower || vDisplayName === preferredLower) {
                            return true;
                        }
                        // Try partial match
                        if (vName.includes(preferredLower) || preferredLower.includes(vName) ||
                            vDisplayName.includes(preferredLower) || preferredLower.includes(vDisplayName)) {
                            return true;
                        }
                        // Try matching "plotly" to "3DPlotly", "3d plotly" to "3DPlotly", etc.
                        if (preferredLower.includes('plotly') && (vId.includes('plotly') || vId === '3dplotly')) {
                            return true;
                        }
                        return false;
                    });
                    
                    if (matchingViewer) {
                        dashboardType = matchingViewer.id;
                        console.log('Found matching viewer by name:', preferredValue, '->', dashboardType);
                    }
                }
            }
            
            // If still no dashboard, use smart selection
            if (!dashboardType) {
                try {
                    dashboardType = await this.selectDashboardForDataset(datasetId, datasetUuid, null);
                    console.log('Using smart-selected dashboard:', dashboardType);
                } catch (error) {
                    console.warn('Smart selection failed, using default:', error);
                    dashboardType = 'OpenVisusSlice';
                }
            }
            
            // Final fallback
            if (!dashboardType) {
                dashboardType = 'OpenVisusSlice';
            }
            
            console.log('Final dashboard type for URL generation:', dashboardType);
            
            // Generate the dashboard URL using the same logic as viewer-manager
            const dashboardUrl = await this.generateDashboardUrl(datasetUuid, datasetServer, datasetName, dashboardType);
            
            // Copy to clipboard
            await navigator.clipboard.writeText(dashboardUrl);
            
            // Show success feedback
            const button = document.querySelector(`[data-action="copy-dashboard-link"][data-dataset-id="${datasetId}"]`);
            if (button) {
                const originalHTML = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check"></i> Copied!';
                button.classList.remove('btn-outline-info');
                button.classList.add('btn-success');
                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.classList.remove('btn-success');
                    button.classList.add('btn-outline-info');
                }, 2000);
            }
            
            // Also show a toast/alert
            console.log('Dashboard link copied to clipboard:', dashboardUrl);
        } catch (error) {
            console.error('Error copying dashboard link:', error);
            alert('Failed to copy dashboard link. Please try again.');
        }
    }
    
    /**
     * Open dashboard link in a new tab
     */
    async openDashboardLink(datasetId, buttonData = {}) {
        try {
            // Get dataset details
            let dataset = this.currentDataset?.details || this.currentDataset;
            
            // If we don't have full details, fetch them
            if (!dataset || !dataset.uuid) {
                // Use button data if available
                if (buttonData.uuid) {
                    dataset = {
                        uuid: buttonData.uuid,
                        name: buttonData.name || 'Dataset',
                        server: buttonData.server || '',
                        preferred_dashboard: this.currentDataset?.details?.preferred_dashboard
                    };
                } else {
                    const response = await fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`);
                    const data = await response.json();
                    if (data.success && data.dataset) {
                        dataset = data.dataset;
                    } else {
                        throw new Error('Failed to fetch dataset details');
                    }
                }
            }
            
            const datasetUuid = dataset.uuid || buttonData.uuid || datasetId;
            const datasetName = dataset.name || buttonData.name || 'Dataset';
            const datasetServer = dataset.server || buttonData.server || '';
            
            // Determine the default dashboard (same logic as copyDashboardLink)
            let dashboardType = null;
            
            // First, try to get the currently loaded dashboard from viewerManager
            if (window.viewerManager && window.viewerManager.currentDashboard) {
                dashboardType = window.viewerManager.currentDashboard;
            }
            
            // If not available, try the toolbar selector
            if (!dashboardType) {
                const viewerTypeSelect = document.getElementById('viewerType');
                if (viewerTypeSelect && viewerTypeSelect.value) {
                    dashboardType = viewerTypeSelect.value;
                }
            }
            
            // If not available, try preferred_dashboard
            if (!dashboardType && dataset.preferred_dashboard && dataset.preferred_dashboard.trim() !== '') {
                const preferredValue = dataset.preferred_dashboard.trim();
                
                // Normalize preferred_dashboard display name to dashboard ID
                const dashboardNameToId = {
                    '3D Plotly Explorer': '3DPlotly',
                    '3D Plotly Dashboard': '3DPlotly',
                    '3d plotly explorer': '3DPlotly',
                    '3d plotly dashboard': '3DPlotly',
                    '3D Plotly': '3DPlotly',
                    '3d plotly': '3DPlotly',
                    'plotly': '3DPlotly',
                    '3D VTK Dashboard': '3DVTK',
                    '3d vtk dashboard': '3DVTK',
                    '3D VTK': '3DVTK',
                    '3d vtk': '3DVTK',
                    '4D Dashboard (New)': '4d_dashboardLite',
                    '4D Dashboard': '4d_dashboardLite',
                    '4d dashboard (new)': '4d_dashboardLite',
                    '4d dashboard': '4d_dashboardLite',
                    '4D Dashboard': '4d_dashboardLite',
                    '4d_dashboardLite': '4d_dashboardLite',
                    '4D_dashboardLite': '4d_dashboardLite',
                    'OpenVisus Slice Dashboard': 'OpenVisusSlice',
                    'openvisus slice dashboard': 'OpenVisusSlice',
                    'OpenVisus Slice': 'OpenVisusSlice',
                    'openvisus slice': 'OpenVisusSlice',
                    'OpenVisusSlice': 'OpenVisusSlice',
                };
                
                dashboardType = dashboardNameToId[preferredValue] || dashboardNameToId[preferredValue.toLowerCase()];
                
                // If still not found, try to match with viewerManager viewers
                if (!dashboardType && window.viewerManager && window.viewerManager.viewers) {
                    const matchingViewer = Object.values(window.viewerManager.viewers).find(v => {
                        const vName = (v.name || '').toLowerCase();
                        const vId = (v.id || '').toLowerCase();
                        return vName === preferredValue.toLowerCase() || vId === preferredValue.toLowerCase();
                    });
                    
                    if (matchingViewer) {
                        dashboardType = matchingViewer.id;
                    }
                }
            }
            
            // If still no dashboard, use smart selection
            if (!dashboardType) {
                try {
                    dashboardType = await this.selectDashboardForDataset(datasetId, datasetUuid, null);
                } catch (error) {
                    console.warn('Smart selection failed, using default:', error);
                    dashboardType = 'OpenVisusSlice';
                }
            }
            
            // Final fallback
            if (!dashboardType) {
                dashboardType = 'OpenVisusSlice';
            }
            
            // Generate the dashboard URL using the same logic as viewer-manager
            const dashboardUrl = await this.generateDashboardUrl(datasetUuid, datasetServer, datasetName, dashboardType);
            
            // Open in new tab
            window.open(dashboardUrl, '_blank');
            
            console.log('Dashboard link opened in new tab:', dashboardUrl);
        } catch (error) {
            console.error('Error opening dashboard link:', error);
            alert('Failed to open dashboard link. Please try again.');
        }
    }
    
    /**
     * Generate dashboard URL (similar to viewer-manager's generateViewerUrl)
     */
    async generateDashboardUrl(datasetUuid, datasetServer, datasetName, dashboardType) {
        // Get dashboard configuration from viewer-manager or API
        let viewer = null;
        
        if (window.viewerManager && window.viewerManager.viewers) {
            // Try to find viewer by dashboard type
            viewer = window.viewerManager.viewers[dashboardType];
            
            // If not found, try case-insensitive match
            if (!viewer) {
                const normalizedType = dashboardType.toLowerCase();
                viewer = Object.values(window.viewerManager.viewers).find(v => {
                    const vId = (v.id || '').toLowerCase();
                    const vType = (v.type || '').toLowerCase();
                    return vId === normalizedType || vType === normalizedType;
                });
            }
        }
        
        // If viewer not found, try to load from API
        if (!viewer) {
            try {
                const dashResponse = await fetch(`${getApiBasePath()}/dashboards.php`);
                if (dashResponse.ok) {
                    const dashData = await dashResponse.json();
                    if (dashData.success && dashData.dashboards) {
                        const dashboard = dashData.dashboards.find(d => 
                            d.enabled && (
                                d.id === dashboardType || 
                                d.id.toLowerCase() === dashboardType.toLowerCase() ||
                                d.type === dashboardType ||
                                d.type?.toLowerCase() === dashboardType.toLowerCase() ||
                                d.name === dashboardType ||
                                d.name?.toLowerCase() === dashboardType.toLowerCase() ||
                                d.display_name === dashboardType ||
                                d.display_name?.toLowerCase() === dashboardType.toLowerCase()
                            )
                        );
                        
                        if (dashboard) {
                            let urlTemplate = dashboard.url_template;
                            if (!urlTemplate && dashboard.nginx_path) {
                                urlTemplate = dashboard.nginx_path + '?uuid={uuid}&server={server}&name={name}';
                            }
                            
                            viewer = {
                                id: dashboard.id,
                                url_template: urlTemplate,
                                nginx_path: dashboard.nginx_path,
                                port: dashboard.port
                            };
                        }
                    }
                }
            } catch (error) {
                console.warn('Could not load dashboard from API:', error);
            }
        }
        
        // If still no viewer, try to find by display name or construct default URL
        let urlTemplate;
        if (viewer && viewer.url_template) {
            urlTemplate = viewer.url_template;
        } else {
            // Try to find viewer by display name match
            if (window.viewerManager && window.viewerManager.viewers) {
                const matchingViewer = Object.values(window.viewerManager.viewers).find(v => {
                    const vName = (v.name || '').toLowerCase();
                    const vDisplayName = (v.display_name || '').toLowerCase();
                    const dashboardTypeLower = dashboardType.toLowerCase();
                    return vName === dashboardTypeLower || 
                           vDisplayName === dashboardTypeLower ||
                           vName.includes(dashboardTypeLower) ||
                           dashboardTypeLower.includes(vName);
                });
                
                if (matchingViewer && matchingViewer.url_template) {
                    viewer = matchingViewer;
                    urlTemplate = matchingViewer.url_template;
                    console.log('Found viewer by display name match:', dashboardType, '->', matchingViewer.id);
                }
            }
            
            // If still no viewer, construct URL from dashboard ID (not display name)
            if (!urlTemplate) {
                // Use the viewer ID if we found one, otherwise try to extract ID from dashboardType
                let pathId;
                if (viewer && viewer.nginx_path) {
                    // Extract from nginx_path (e.g., "/dashboard/plotly" -> "plotly")
                    const match = viewer.nginx_path.match(/\/dashboard\/([^/?]+)/);
                    if (match) {
                        pathId = match[1]; // Use the path as-is (e.g., "plotly", "3DVTK")
                    } else {
                        // If nginx_path doesn't match pattern, use viewer ID
                        pathId = viewer.id ? viewer.id.toLowerCase().replace(/[_-]/g, '') : 'plotly';
                    }
                } else if (viewer && viewer.id) {
                    // If no nginx_path, try to construct from ID
                    // Map dashboard IDs to their nginx paths
                    const idToPath = {
                        '3dplotly': 'plotly',
                        '3dvtk': '3DVTK',
                        '4ddashboardlite': '4d_dashboardLite',
                        'openvisusslice': 'OpenVisusSlice',
                        'magicscan': 'magicscan'
                    };
                    const normalizedId = viewer.id.toLowerCase().replace(/[_-]/g, '');
                    pathId = idToPath[normalizedId] || normalizedId;
                } else {
                    // Last resort: try to map display name to nginx path
                    const displayNameToPath = {
                        '3d plotly explorer': 'plotly',
                        '3d plotly dashboard': 'plotly',
                        '3d plotly': 'plotly',
                        'plotly': 'plotly',
                        '3d vtk dashboard': '3DVTK',
                        '3d vtk': '3DVTK',
                        '4d dashboard (new)': '4d_dashboardLite',
                        '4d dashboard': '4d_dashboard',
                        'openvisus slice dashboard': 'OpenVisusSlice',
                        'openvisus slice': 'OpenVisusSlice',
                        'magicscan dashboard': 'magicscan',
                        'magicscan': 'magicscan'
                    };
                    const normalizedName = dashboardType.toLowerCase().trim();
                    pathId = displayNameToPath[normalizedName];
                    
                    // If still not found, try to extract from "3D Plotly Explorer" -> "plotly"
                    if (!pathId) {
                        if (normalizedName.includes('plotly')) {
                            pathId = 'plotly';
                        } else if (normalizedName.includes('vtk')) {
                            pathId = '3DVTK';
                        } else if (normalizedName.includes('4d') || normalizedName.includes('4 d')) {
                            pathId = '4d_dashboardLite';
                        } else if (normalizedName.includes('openvisus') || normalizedName.includes('slice')) {
                            pathId = 'OpenVisusSlice';
                        } else if (normalizedName.includes('magicscan') || normalizedName.includes('magic')) {
                            pathId = 'magicscan';
                        } else {
                            // Last resort: remove spaces and special chars
                            pathId = dashboardType.toLowerCase().replace(/[^a-z0-9]/g, '');
                        }
                    }
                }
                urlTemplate = `/dashboard/${pathId}?uuid={uuid}&server={server}&name={name}`;
                console.warn('Constructed URL from dashboard type (fallback):', urlTemplate);
            }
        }
        
        // Replace placeholders
        let url = urlTemplate
            .replace(/{uuid}/g, encodeURIComponent(datasetUuid))
            .replace(/{server}/g, encodeURIComponent(datasetServer || 'false'))
            .replace(/{name}/g, encodeURIComponent(datasetName || ''));
        
        // For local development, convert /dashboard/ paths to direct port access
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        if (isLocal && url.startsWith('/dashboard/') && viewer && viewer.port) {
            const match = url.match(/\/dashboard\/([^/?]+)/);
            const dashboardPathName = match?.[1];
            
            if (dashboardPathName && viewer) {
                const pathAfterDashboard = url.replace(/^\/dashboard\/[^/?]+/, '');
                const appPath = '/' + (viewer.id || dashboardPathName) + (pathAfterDashboard || '/');
                url = `http://localhost:${viewer.port}${appPath}`;
            }
        }
        
        // Make it an absolute URL if it's relative
        if (url.startsWith('/')) {
            const baseUrl = window.location.origin;
            // Dashboards are served from root, not under /portal
            // Only add /portal for portal-specific paths (which dashboards are not)
            // Dashboard paths like /dashboard/... should be at root level
            if (url.startsWith('/dashboard/')) {
                // Dashboard URLs are at root, not under /portal
                url = baseUrl + url;
            } else {
                // For other paths, check if we're in portal context
                const portalPath = isLocal ? '' : '/portal';
                url = baseUrl + portalPath + url;
            }
        }
        
        return url;
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
     * Retry conversion for a failed dataset
     */
    async retryConversion(datasetUuid, datasetName, buttonElement) {
        if (!datasetUuid) {
            alert('Dataset UUID not found');
            return;
        }

        // Confirm retry (message will be updated based on dataset type)
        if (!confirm(`Retry processing for "${datasetName}"?\n\nThis will reset the status and the background service will process it again.`)) {
            return;
        }

        // Disable button and show loading state
        const originalHTML = buttonElement.innerHTML;
        buttonElement.disabled = true;
        buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Retrying...';

        try {
            const response = await fetch(`${getApiBasePath()}/retry-conversion.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ dataset_uuid: datasetUuid })
            });

            // Check if response is OK before trying to parse JSON
            if (!response.ok) {
                const text = await response.text();
                console.error('Retry failed with status:', response.status, 'Response:', text);
                throw new Error(`Server error: ${response.status}`);
            }

            // Try to parse JSON, but handle HTML error responses
            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (parseError) {
                console.error('Failed to parse JSON response:', text);
                throw new Error('Server returned invalid response. Check console for details.');
            }

            if (data.success) {
                // Show success message (different for Google Drive vs regular conversion)
                const message = data.message || (data.status === 'submitted' 
                    ? `Google Drive upload retry triggered successfully!\n\nDataset "${datasetName}" status set to "submitted". The background service will process the Google Drive upload shortly.`
                    : `Conversion retry triggered successfully!\n\nDataset "${datasetName}" has been queued for conversion. The background service will process it shortly.`);
                alert(message);
                
                // Reload datasets to show updated status
                this.loadDatasets();
            } else {
                alert('Error retrying conversion: ' + (data.error || data.message || 'Unknown error'));
                // Restore button
                buttonElement.disabled = false;
                buttonElement.innerHTML = originalHTML;
            }
        } catch (error) {
            console.error('Error retrying conversion:', error);
            alert('Error retrying conversion: ' + error.message);
            // Restore button
            buttonElement.disabled = false;
            buttonElement.innerHTML = originalHTML;
        }
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

                // Check if response is OK before trying to parse JSON
                if (!response.ok) {
                    const text = await response.text();
                    console.error('Delete failed with status:', response.status, 'Response:', text);
                    throw new Error(`Server error: ${response.status}`);
                }

                // Try to parse JSON, but handle HTML error responses
                const text = await response.text();
                let data;
                try {
                    data = JSON.parse(text);
                } catch (parseError) {
                    console.error('Failed to parse JSON response:', text);
                    throw new Error('Server returned invalid response. Check console for details.');
                }

                if (data.success) {
                    alert('Dataset deleted successfully');
                    location.reload();
                } else {
                    alert('Error deleting dataset: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error deleting dataset:', error);
                alert('Error deleting dataset: ' + error.message);
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
        if (!status) return 'secondary';
        
        const statusLower = status.toLowerCase();
        
        // Success statuses
        if (statusLower === 'done' || statusLower === 'ready' || statusLower === 'completed') {
            return 'success';
        }
        
        // Warning/processing statuses
        if (statusLower.includes('processing') || 
            statusLower.includes('converting') || 
            statusLower.includes('queued') ||
            statusLower === 'pending' ||
            statusLower === 'uploading') {
            return 'warning';
        }
        
        // Error/failed statuses
        if (statusLower.includes('failed') || 
            statusLower.includes('error') ||
            statusLower === 'error') {
            return 'danger';
        }
        
        // Info statuses
        if (statusLower === 'info' || statusLower === 'pending') {
            return 'info';
        }
        
        return 'secondary';
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
