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
    getRemoteLinkSchemes() {
        return ['s3://', 'http://', 'https://', 'pelican://'];
    }

    isRemoteLinkedDataset(link) {
        const normalizedLink = (link || '').trim().toLowerCase();
        if (!normalizedLink) return false;
        if (normalizedLink.includes('google.com')) return false;
        return this.getRemoteLinkSchemes().some((scheme) => normalizedLink.startsWith(scheme));
    }

    isModVisusHttpLink(link) {
        const normalizedLink = (link || '').trim().toLowerCase();
        return (
            (normalizedLink.startsWith('http://') || normalizedLink.startsWith('https://')) &&
            normalizedLink.includes('mod_visus')
        );
    }

    constructor() {
        this.currentDataset = null;
        this.datasets = [];
        this.folders = [];
        this.isSelectingDataset = false;
        this.focusedFolder = this.getFolderFromUrl();
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

            const focusBack = e.target.closest('.folder-focus-back');
            if (focusBack && focusBack.closest('#folderSidebar')) {
                e.preventDefault();
                this.clearFolderFocus();
                return;
            }
            const focusCopy = e.target.closest('.folder-focus-copy');
            if (focusCopy && focusCopy.closest('#folderSidebar')) {
                e.preventDefault();
                this.copyFolderFocusLink(focusCopy);
            }
        });

        document.addEventListener('dblclick', (e) => {
            const summary = e.target.closest('.folder-summary');
            if (!summary || !summary.closest('#folderSidebar')) return;
            e.preventDefault();
            const group = summary.closest('.folder-group');
            const folderId = (
                group?.getAttribute('data-folder-id') ||
                summary.querySelector('.folder-name')?.textContent ||
                ''
            ).trim();
            if (folderId) {
                this.focusFolder(folderId);
            }
        });

        document.addEventListener('click', (e) => {
            const summary = e.target.closest('.folder-summary');
            if (summary && summary.closest('#folderSidebar') && e.detail > 1) {
                e.preventDefault();
            }
        }, true);

        window.addEventListener('popstate', () => {
            const folder = this.getFolderFromUrl();
            if ((folder || null) === (this.focusedFolder || null)) return;
            this.focusedFolder = folder;
            this.renderDatasetList();
            this.selectInitialDatasetFromUrl();
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
            this.datasets = data.datasets?.public || [];
            this.folders = data.folders || [];
            
            console.log(`Loaded ${this.datasets.length} public datasets`, data);
            
            if (this.datasets.length === 0) {
                console.warn('No public datasets found. This could mean:');
                console.warn('1. No datasets are marked as public (is_public = true)');
                console.warn('2. There are no datasets in the database');
                console.warn('3. There was an error querying the database');
            }
            
            // Render dataset list
            this.renderDatasetList();
            this.selectInitialDatasetFromUrl();
            
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
     * Open a dataset from ?dataset=<uuid> deep links.
     */
    selectInitialDatasetFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const initialDataset = (params.get('dataset') || window.INITIAL_DATASET_ID || '').trim();
        if (!initialDataset) {
            return;
        }

        const escaped = (typeof CSS !== 'undefined' && CSS.escape)
            ? CSS.escape(initialDataset)
            : initialDataset.replace(/["\\]/g, '\\$&');
        const link = document.querySelector(
            `.dataset-link[data-dataset-id="${escaped}"], .dataset-link[data-dataset-uuid="${escaped}"]`
        );
        if (link) {
            link.click();
        }
    }

    getFolderFromUrl() {
        try {
            const folder = new URLSearchParams(window.location.search).get('folder');
            return folder && folder.trim() ? folder.trim() : null;
        } catch (e) {
            return null;
        }
    }

    getFolderFocusUrl(folderId) {
        const url = new URL(window.location.href);
        if (folderId) {
            url.searchParams.set('folder', folderId);
        } else {
            url.searchParams.delete('folder');
        }
        return url.toString();
    }

    syncFolderUrl(folderId, { replace = false } = {}) {
        const url = this.getFolderFocusUrl(folderId);
        const state = { ...(history.state || {}), folder: folderId || null };
        if (replace) {
            history.replaceState(state, '', url);
        } else {
            history.pushState(state, '', url);
        }
    }

    focusFolder(folderId, { updateHistory = true } = {}) {
        const next = (folderId || '').trim();
        if (!next) return;
        if (this.focusedFolder === next) {
            if (updateHistory) this.syncFolderUrl(next, { replace: true });
            return;
        }
        this.focusedFolder = next;
        if (updateHistory) this.syncFolderUrl(next);
        this.renderDatasetList();
    }

    clearFolderFocus({ updateHistory = true } = {}) {
        if (!this.focusedFolder) return;
        this.focusedFolder = null;
        if (updateHistory) this.syncFolderUrl(null);
        this.renderDatasetList();
    }

    renderFolderFocusBar(folderId) {
        return `
            <div class="folder-focus-bar" role="navigation" aria-label="Focused folder">
                <button type="button" class="folder-focus-back" title="Back to all folders" aria-label="Back to all folders">
                    <i class="fas fa-arrow-left" aria-hidden="true"></i>
                </button>
                <span class="folder-focus-name" title="${this.escapeHtml(folderId)}">${this.escapeHtml(folderId)}</span>
                <button type="button" class="folder-focus-copy" title="Copy link to this folder" aria-label="Copy folder link">
                    <i class="fas fa-link" aria-hidden="true"></i>
                </button>
            </div>
        `;
    }

    async copyFolderFocusLink(buttonEl) {
        const text = this.getFolderFocusUrl(this.focusedFolder);
        const original = buttonEl.innerHTML;
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
            } else {
                const input = document.createElement('textarea');
                input.value = text;
                document.body.appendChild(input);
                input.select();
                document.execCommand('copy');
                input.remove();
            }
            buttonEl.innerHTML = '<i class="fas fa-check" aria-hidden="true"></i>';
            setTimeout(() => {
                buttonEl.innerHTML = original;
            }, 1500);
        } catch (error) {
            console.error('Failed to copy folder link:', error);
            alert('Failed to copy link. Please copy it from the address bar.');
        }
    }

    getPublicPortalShareUrl(datasetUuid) {
        const url = new URL(window.location.href);
        url.search = '';
        url.searchParams.set('dataset', datasetUuid);
        // Keep folder focus when sharing a dataset from a focused view.
        if (this.focusedFolder) {
            url.searchParams.set('folder', this.focusedFolder);
        }
        return url.toString();
    }

    getPublicS3BrowserUrl(datasetUuid) {
        const url = new URL(window.location.href);
        const path = url.pathname.replace(/index\.php$/i, '').replace(/\/?$/, '/');
        url.pathname = `${path}s3.php`;
        url.search = '';
        url.searchParams.set('dataset', datasetUuid);
        return url.toString();
    }

    async copyShareLink(text, buttonEl) {
        const original = buttonEl.innerHTML;
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
            } else {
                const input = document.createElement('textarea');
                input.value = text;
                document.body.appendChild(input);
                input.select();
                document.execCommand('copy');
                input.remove();
            }
            buttonEl.innerHTML = '<i class="fas fa-check"></i> Copied';
            setTimeout(() => {
                buttonEl.innerHTML = original;
            }, 1500);
        } catch (error) {
            console.error('Failed to copy share link:', error);
            alert('Failed to copy link. Please copy it manually.');
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

        const focused = this.focusedFolder;
        const visibleRoot = focused ? [] : rootDatasets;
        const visibleFolders = focused
            ? (groupedDatasets[focused] ? { [focused]: groupedDatasets[focused] } : {})
            : groupedDatasets;
        
        let html = '';
        if (focused) {
            html += this.renderFolderFocusBar(focused);
        }

        html += '<div class="dataset-section">';
        html += '<a class="nav-link" data-bs-toggle="collapse" data-bs-target="#publicDatasets">';
        html += '<span class="arrow-icon" id="arrow-public">&#9656;</span>Public Datasets</a>';
        html += '<div class="collapse show ps-4 w-100" id="publicDatasets">';
        
        // Root level datasets
        visibleRoot.forEach(dataset => {
            html += this.renderDatasetItem(dataset);
        });
        
        // Folder grouped datasets
        Object.keys(visibleFolders).forEach(folderUuid => {
            html += `<div class="folder-group" data-folder-id="${this.escapeHtml(folderUuid)}">`;
            html += `<details class="folder-details" open>`;
            html += `<summary class="folder-summary" title="Double-click to focus this folder">`;
            html += `<span class="arrow-icon">&#9656;</span>`;
            html += `<span class="folder-name">${this.escapeHtml(folderUuid)}</span>`;
            html += `<span class="badge bg-secondary ms-2">${visibleFolders[folderUuid].length}</span>`;
            html += `</summary>`;
            html += `<ul class="nested folder-datasets">`;
            visibleFolders[folderUuid].forEach(dataset => {
                html += `<li>${this.renderDatasetItem(dataset)}</li>`;
            });
            html += `</ul>`;
            html += `</details>`;
            html += `</div>`;
        });

        if (focused && visibleRoot.length === 0 && Object.keys(visibleFolders).length === 0) {
            html += `<p class="text-muted">No public datasets found in this folder.</p>`;
        }
        
        html += '</div></div>';
        
        listContainer.innerHTML = html;
    }

    /**
     * Render a single dataset item
     */
    renderDatasetItem(dataset) {
        const statusColor = this.getStatusColor(dataset.status);
        const fileIcon = this.getDatasetListIcon(dataset);
        const datasetId = dataset.id || dataset.uuid;
        const connection = this.resolveDatasetConnection(dataset);
        
        return `
            <div class="dataset-item" data-dataset-id="${this.escapeHtml(datasetId)}">
                <div class="dataset-header">
                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                       data-dataset-id="${this.escapeHtml(datasetId)}"
                       data-dataset-name="${this.escapeHtml(dataset.name || '')}"
                       data-dataset-uuid="${this.escapeHtml(connection.effectiveUuid || dataset.uuid || datasetId)}"
                       data-dataset-server="${this.escapeHtml(connection.datasetServer)}">
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
            const datasetDetails = await this.loadDatasetDetails(datasetId);
            this.currentDataset = datasetDetails;
            const resolvedConnection = this.resolveDatasetConnection(datasetDetails || {});
            const effectiveUuid = resolvedConnection.effectiveUuid || datasetUuid;
            const effectiveServer = resolvedConnection.datasetServer || datasetServer || 'false';
            
            // Load dashboard
            if (window.viewerManager) {
                window.viewerManager.currentDataset = {
                    id: datasetId,
                    name: datasetName,
                    uuid: effectiveUuid,
                    server: effectiveServer,
                    details: datasetDetails
                };
                
                const viewerType = document.getElementById('viewerType');
                const selectedDashboardType = this.selectDashboardForPublicDataset(datasetDetails);
                if (viewerType && selectedDashboardType) {
                    viewerType.value = selectedDashboardType;
                }
                
                window.viewerManager.loadDashboard(
                    datasetId,
                    datasetName,
                    effectiveUuid,
                    effectiveServer,
                    selectedDashboardType || (viewerType ? viewerType.value : (Object.keys(window.viewerManager.viewers)[0] || 'OpenVisusSlice'))
                );
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
            return data.dataset;
            
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
            return null;
        }
    }

    /**
     * Select best-fit dashboard for public datasets using dataset details.
     * Mirrors private behavior loosely by prioritizing preferred_dashboard, then dimensions.
     *
     * @param {object|null} dataset
     * @returns {string|null} Dashboard id
     */
    selectDashboardForPublicDataset(dataset) {
        try {
            if (!dataset) return null;

            const viewers = window.viewerManager?.viewers || {};

            // Parse a dimension number from strings like "4D", "4d", "2D", "4 D", etc.
            const parseDimension = (value) => {
                const str = (value ?? '').toString();
                const match = str.toUpperCase().match(/([1-4])\s*D/);
                if (!match) return null;
                const dim = parseInt(match[1], 10);
                return Number.isFinite(dim) ? dim : null;
            };

            const select4D = () => {
                // Prefer the "2x2" dashboard variant if both exist.
                if (viewers['4d_dashboard'] !== undefined) return '4d_dashboard';
                if (viewers['4d_dashboardLite'] !== undefined) return '4d_dashboardLite';
                if (viewers['4d_dashboardopt'] !== undefined) return '4d_dashboardopt';

                // Best-effort: pick any enabled viewer that looks like a 4D dashboard.
                const any4d = Object.keys(viewers).find(k => (k || '').toLowerCase().includes('4d_dashboard'));
                return any4d || '4d_dashboardLite';
            };

            const dimensionFromDimensions = parseDimension(dataset.dimensions);
            const dimensionFromSensor = parseDimension(dataset.sensor);
            const effectiveDimension = dimensionFromDimensions ?? dimensionFromSensor;

            // 1) preferred_dashboard (most reliable signal)
            const preferred = (dataset.preferred_dashboard || '').toString().trim();
            if (preferred) {
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
                    'OpenVisus Slice Dashboard': 'OpenVisusSlice',
                    'openvisus slice dashboard': 'OpenVisusSlice',
                    'OpenVisus Slice': 'OpenVisusSlice',
                    'openvisus slice': 'OpenVisusSlice',
                    'OpenVisusSlice': 'OpenVisusSlice',
                    'magicscan': 'magicscan',
                    'MagicScan Dashboard': 'magicscan',
                    'magicscan dashboard': 'magicscan',
                    'S3 Browser': 'S3Browser',
                    's3 browser': 'S3Browser',
                    'S3Browser': 'S3Browser',
                    's3_browser': 'S3Browser'
                };

                const mapped =
                    dashboardNameToId[preferred] ||
                    dashboardNameToId[preferred.toLowerCase()] ||
                    (viewers[preferred] ? preferred : null) ||
                    (window.viewerManager?.resolveDashboardId
                        ? window.viewerManager.resolveDashboardId(preferred)
                        : null);

                if (mapped && viewers[mapped] !== undefined) {
                    // If dataset is 4D, do not allow a non-4D preferred dashboard to override it.
                    if (effectiveDimension === 4 && mapped !== 'S3Browser') {
                        if (mapped === '4d_dashboard' || mapped === '4d_dashboardLite' || mapped === '4d_dashboardopt') {
                            return mapped;
                        }
                        return select4D();
                    }

                    return mapped;
                }
            }

            if (this.isS3DirectoryOnlyDataset(dataset) && viewers['S3Browser'] !== undefined) {
                return 'S3Browser';
            }

            // 2) dimensions
            if (effectiveDimension === 4) {
                return select4D();
            }
            if (effectiveDimension === 3) {
                // Prefer 3DPlotly if available; otherwise fall back to OpenVisusSlice.
                return viewers['3DPlotly'] !== undefined ? '3DPlotly' : 'OpenVisusSlice';
            }
            if (effectiveDimension === 2 || effectiveDimension === 1) {
                if (this.isS3DirectoryOnlyDataset(dataset) && viewers['S3Browser'] !== undefined) {
                    return 'S3Browser';
                }
                return 'OpenVisusSlice';
            }

            // 3) sensor fallbacks (light-touch)
            const sensorStr = (dataset.sensor || '').toString().toUpperCase();
            if (dimensionFromSensor === 4) {
                return select4D();
            }
            if (sensorStr.includes('MAGIC')) {
                return viewers['magicscan'] !== undefined ? 'magicscan' : 'magicscan';
            }
            if (sensorStr.includes('NEXUS') && viewers['OpenVisusSlice'] !== undefined) {
                return 'OpenVisusSlice';
            }

            // 4) default
            if (this.isS3DirectoryOnlyDataset(dataset) && viewers['S3Browser'] !== undefined) {
                return 'S3Browser';
            }
            if (viewers['OpenVisusSlice'] !== undefined) return 'OpenVisusSlice';
            return Object.keys(viewers)[0] || 'OpenVisusSlice';
        } catch (error) {
            console.error('Error selecting public dashboard:', error);
            return null;
        }
    }

    /**
     * Linked S3 folder registrations (not a single .idx / .json visualization target).
     */
    isS3DirectoryOnlyDataset(dataset) {
        if (!dataset) {
            return false;
        }
        if (dataset.has_s3_browser !== true) {
            const connection = this.resolveDatasetConnection(dataset);
            const isRemote = String(dataset.server || '').toLowerCase() === 'true'
                || connection.datasetServer === 'true'
                || this.isRemoteLinkedDataset(connection.link);
            if (!isRemote) {
                return false;
            }
        }

        const tagsText = Array.isArray(dataset.tags)
            ? dataset.tags.join(' ').toLowerCase()
            : String(dataset.tags || '').toLowerCase();
        if (tagsText.includes('link to s3')) {
            return true;
        }

        const link = String(
            dataset.google_drive_link || dataset.download_url || dataset.viewer_url || ''
        ).toLowerCase();
        if (link) {
            const leaf = link.split('/').pop().split('?')[0];
            if (leaf && !leaf.includes('.idx') && !leaf.endsWith('.json')) {
                return true;
            }
        }

        return Number(dataset.data_size || 0) === 0;
    }

    /**
     * Display dataset details (read-only, no edit/delete/retry)
     */
    displayDatasetDetails(dataset) {
        const detailsContainer = document.getElementById('datasetDetails');
        if (!detailsContainer) return;
        
        // Check if dataset is publicly downloadable
        const isDownloadable = dataset.is_downloadable === 'public';
        const datasetUuid = dataset.uuid || dataset.id;
        const connection = this.resolveDatasetConnection(dataset);
        const isRemoteS3 = dataset.has_s3_browser === true
            || String(dataset.server || '').toLowerCase() === 'true'
            || connection.datasetServer === 'true'
            || this.isRemoteLinkedDataset(connection.link);
        const portalShareUrl = dataset.public_portal_url || this.getPublicPortalShareUrl(datasetUuid);
        const s3BrowserUrl = dataset.public_s3_browse_url || this.getPublicS3BrowserUrl(datasetUuid);
        
        const html = `
            <div class="dataset-details">
                <h6><i class="fas fa-info-circle"></i> Dataset Details</h6>
                
                <div class="mb-2">
                    <h6 class="text-primary mb-2">${this.escapeHtml(dataset.name || 'Unnamed Dataset')}</h6>
                </div>
                
                <div class="dataset-actions mb-3 pb-2 border-bottom">
                    <div class="d-flex flex-wrap gap-2 mb-2">
                        <button type="button" class="btn btn-sm btn-outline-secondary flex-grow-1"
                                data-action="copy-portal-link"
                                data-share-url="${this.escapeHtml(portalShareUrl)}"
                                title="Copy link to this dataset on the public portal">
                            <i class="fas fa-link"></i> Share Portal Link
                        </button>
                        ${isRemoteS3 ? `
                        <button type="button" class="btn btn-sm btn-outline-info flex-grow-1"
                                data-action="copy-s3-link"
                                data-share-url="${this.escapeHtml(s3BrowserUrl)}"
                                title="Copy link to browse this dataset's files on S3">
                            <i class="fas fa-share-alt"></i> Share S3 Link
                        </button>
                        ` : ''}
                    </div>
                    <div class="d-flex flex-wrap gap-2">
                        <button type="button" class="btn btn-sm btn-outline-primary flex-grow-1" 
                                data-action="open-dashboard-link"
                                data-dataset-id="${dataset.id || dataset.uuid}"
                                data-dataset-uuid="${dataset.uuid || dataset.id}"
                                data-dataset-name="${this.escapeHtml(dataset.name || '')}"
                                data-dataset-server="${this.escapeHtml(dataset.server || 'false')}"
                                title="Open this dataset's dashboard in a new tab">
                            <i class="fas fa-external-link-alt"></i> Open Dashboard
                        </button>
                        
                        ${isRemoteS3 ? `
                        <a href="${this.escapeHtml(s3BrowserUrl)}" target="_blank" rel="noopener"
                           class="btn btn-sm btn-info flex-grow-1 text-white"
                           title="Browse and download files from S3 (no credentials required)">
                            <i class="fas fa-folder-open"></i> Browse on S3
                        </a>
                        ` : ''}
                        
                        ${isDownloadable ? `
                        <button type="button" class="btn btn-sm btn-primary flex-grow-1" data-action="download" data-dataset-id="${dataset.id || dataset.uuid}">
                            <i class="fas fa-download"></i> Download Dataset
                        </button>
                        ` : ''}
                    </div>
                </div>
                
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

        this.currentDatasetDetails = dataset;
        
        // Attach download button handler
        const downloadBtn = detailsContainer.querySelector('[data-action="download"]');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.downloadDataset(dataset.id || dataset.uuid, dataset);
            });
        }

        detailsContainer.querySelectorAll('[data-action="copy-portal-link"], [data-action="copy-s3-link"]').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const shareUrl = btn.getAttribute('data-share-url');
                if (shareUrl) {
                    this.copyShareLink(shareUrl, btn);
                }
            });
        });

        // Attach open-dashboard button handler (opens the currently loaded dashboard in a new tab)
        const openDashboardBtn = detailsContainer.querySelector('[data-action="open-dashboard-link"]');
        if (openDashboardBtn) {
            openDashboardBtn.addEventListener('click', (e) => {
                e.preventDefault();

                // Prefer using the iframe that viewer-manager already created.
                const iframe = document.getElementById('dashboardFrame');
                if (iframe && iframe.src) {
                    window.open(iframe.src, '_blank');
                    return;
                }

                // Fallback: generate a URL from the currently selected dashboard type.
                try {
                    if (window.viewerManager && window.viewerManager.viewers) {
                        const datasetUuid = dataset.uuid || dataset.id;
                        const datasetName = dataset.name || 'Dataset';
                        const connection = this.resolveDatasetConnection(dataset || {});
                        const effectiveUuid = connection.effectiveUuid || datasetUuid;
                        const datasetServer = connection.datasetServer || dataset.server || 'false';

                        const viewerType = document.getElementById('viewerType');
                        const dashboardType = viewerType ? viewerType.value : (window.viewerManager.currentDashboard || 'OpenVisusSlice');

                        const viewer = window.viewerManager.viewers[dashboardType];
                        if (viewer && viewer.url_template) {
                            const dashboardUrl = window.viewerManager.generateViewerUrl(
                                effectiveUuid,
                                datasetServer,
                                datasetName,
                                viewer.url_template
                            );
                            window.open(dashboardUrl, '_blank');
                            return;
                        }
                    }
                } catch (err) {
                    console.error('Failed to generate dashboard URL:', err);
                }

                alert('Dashboard is still loading. Please try again in a moment.');
            });
        }
    }

    /**
     * Download dataset (if publicly downloadable).
     * S3-linked datasets zip the dataset root via the public S3 download API.
     */
    async downloadDataset(datasetId, dataset = null) {
        try {
            const resolved = dataset || this.currentDatasetDetails;
            const isS3Dataset = resolved && (
                resolved.has_s3_browser === true
                || this.isS3DirectoryOnlyDataset(resolved)
            );

            if (isS3Dataset) {
                const url = `${getApiBasePath()}/public-s3-download-folder.php?rel=&dataset=${encodeURIComponent(datasetId)}`;
                window.open(url, '_blank', 'noopener');
                return;
            }

            alert(
                'This dataset is stored remotely. Use the S3 Browser to download individual files or folders, '
                + 'or contact the dataset owner for bulk export.'
            );
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
        if (typeof formatPortalDate === 'function') {
            return formatPortalDate(dateString, 'N/A');
        }
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

    /**
     * Sidebar icon: cloud for S3-linked datasets, otherwise sensor/format icon.
     */
    isS3LinkedDataset(dataset) {
        if (!dataset) {
            return false;
        }
        if (dataset.has_s3_browser === true) {
            return true;
        }

        const link = String(
            dataset.google_drive_link || dataset.download_url || dataset.viewer_url || ''
        ).trim().toLowerCase();
        if (link.startsWith('s3://')) {
            return true;
        }

        const tagsText = Array.isArray(dataset.tags)
            ? dataset.tags.join(' ').toLowerCase()
            : String(dataset.tags || '').toLowerCase();
        if (tagsText.includes('link to s3')) {
            return true;
        }

        return this.isS3DirectoryOnlyDataset(dataset);
    }

    getDatasetListIcon(dataset) {
        if (this.isS3LinkedDataset(dataset)) {
            return 'fas fa-cloud text-info';
        }
        return this.getFileFormatIcon(dataset?.sensor);
    }

    /**
     * Resolve dataset UUID/server for remote links.
     * Mirrors private-portal logic so public portal can load s3:// and other URI schemes.
     */
    resolveDatasetConnection(dataset) {
        const link = dataset?.google_drive_link || dataset?.download_url || dataset?.viewer_url || '';
        const sensor = String(dataset?.sensor || '').trim().toUpperCase();
        const explicitServer = String(dataset?.server || '').trim().toLowerCase() === 'true';
        const datasetServer = (explicitServer || this.isRemoteLinkedDataset(link)) ? 'true' : 'false';
        // Keep legacy behavior only for mod_visus HTTP IDX links.
        const useRemoteLinkAsUuid = sensor === 'IDX' && this.isModVisusHttpLink(link);
        const effectiveUuid = useRemoteLinkAsUuid ? link : (dataset?.uuid || dataset?.id || '');
        return { datasetServer, effectiveUuid, link };
    }
}

// Initialize public dataset manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.IS_PUBLIC_PORTAL) {
        window.publicDatasetManager = new PublicDatasetManager();
        console.log('Public Dataset Manager initialized');
    }
});

