/**
 * Upload Manager JavaScript
 * Handles dataset uploads with multiple source types
 */

// Helper function to get API base path
function getUploadApiBasePath() {
    // Use the same API base path as other endpoints (PHP proxy)
    return getApiBasePath();
}

class UploadManager {
    constructor() {
        this.activeUploads = new Map(); // job_id -> upload info
        this.progressWidget = null;
        this.uploadModal = null; // Upload progress modal
        this.currentUploadSession = null; // Current upload session data
        this.dashboards = []; // Cached dashboard list from API
        this.localBrowserUploadInProgress = false;
        this.initialize();
    }
    
    /**
     * Load dashboards from API (cached)
     */
    async loadDashboards() {
        if (this.dashboards.length > 0) {
            return this.dashboards; // Return cached
        }
        
        try {
            const response = await fetch(`${getApiBasePath()}/dashboards.php`);
            if (!response.ok) {
                console.warn('Failed to load dashboards from API, using fallback');
                // Fallback to minimal list
                this.dashboards = [
                    { id: 'OpenVisusSlice', display_name: 'OpenVisus Slice Dashboard' },
                    { id: '3DPlotly', display_name: '3D Plotly Dashboard' },
                    { id: '4D_Dashboard', display_name: '4D Dashboard' },
                    { id: '3DVTK', display_name: '3D VTK Dashboard' },
                    { id: 'magicscan', display_name: 'MagicScan Dashboard' }
                ];
                return this.dashboards;
            }
            
            const data = await response.json();
            if (data.success && data.dashboards) {
                // Filter to only enabled dashboards and remove duplicates
                const seen = new Set();
                this.dashboards = data.dashboards
                    .filter(d => d.enabled && !seen.has(d.id))
                    .map(d => {
                        seen.add(d.id);
                        return {
                            id: d.id,
                            display_name: d.display_name || d.name || d.id
                        };
                    });
                return this.dashboards;
            }
        } catch (error) {
            console.error('Error loading dashboards:', error);
        }
        
        // Fallback
        this.dashboards = [
            { id: 'OpenVisusSlice', display_name: 'OpenVisus Slice Dashboard' },
            { id: '3DPlotly', display_name: '3D Plotly Dashboard' },
            { id: '4D_Dashboard', display_name: '4D Dashboard' },
            { id: '3DVTK', display_name: '3D VTK Dashboard' },
            { id: 'magicscan', display_name: 'MagicScan Dashboard' }
        ];
        return this.dashboards;
    }
    
    /**
     * Generate dashboard options HTML for select dropdown
     */
    async getDashboardOptionsHTML(selectedValue = '') {
        const dashboards = await this.loadDashboards();
        return dashboards.map(d => {
            const selected = (selectedValue && selectedValue.toLowerCase() === d.id.toLowerCase()) ? 'selected' : '';
            return `<option value="${this.escapeHtml(d.id)}" ${selected}>${this.escapeHtml(d.display_name)}</option>`;
        }).join('');
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
     * Populate all dashboard dropdowns in the upload interface
     */
    async populateDashboardDropdowns() {
        const dashboards = await this.loadDashboards();
        const selects = document.querySelectorAll('.dashboard-select');
        selects.forEach(select => {
            select.innerHTML = '<option value="">-- Select Dashboard --</option>';
            dashboards.forEach(d => {
                const option = document.createElement('option');
                option.value = d.id;
                option.textContent = d.display_name;
                select.appendChild(option);
            });
        });
    }

    /**
     * Initialize the upload manager
     */
    initialize() {
        this.setupEventListeners();
        this.createProgressWidget();
        this.createUploadModal();
        this.bootstrapUploadFromUrl();
        // Restore active uploads from server (in case page was refreshed)
        this.restoreActiveUploads();
    }

    /**
     * Track an upload that was initiated from another page, such as Inspect S3.
     */
    bootstrapUploadFromUrl() {
        const params = new URLSearchParams(window.location.search || '');
        const jobId = params.get('job_id');
        if (!jobId) {
            return;
        }

        const datasetUuid = params.get('dataset_id') || params.get('dataset_uuid') || null;
        const datasetName = params.get('dataset_name') || 'S3 Dataset';
        const willConvert = ['1', 'true', 'yes', 'on'].includes(String(params.get('convert') || '').toLowerCase());

        this.trackUpload(jobId, datasetName, datasetName, willConvert, datasetUuid);
        console.log(`✅ Tracking upload from URL: ${jobId}`);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Upload Dataset button
        const uploadBtn = document.getElementById('uploadDatasetBtn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                this.showUploadInterface();
            });
        }

        // Create Team button - load team management page in viewer container
        const createTeamBtn = document.getElementById('createTeamBtn');
        if (createTeamBtn) {
            // Remove any existing listeners first
            const newBtn = createTeamBtn.cloneNode(true);
            createTeamBtn.parentNode.replaceChild(newBtn, createTeamBtn);
            
            newBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                await this.showCreateTeamPage();
            });
        }

        window.addEventListener('beforeunload', (event) => {
            if (!this.localBrowserUploadInProgress) {
                return;
            }
            event.preventDefault();
            event.returnValue = 'A local upload is still sending files. Leaving now may interrupt the upload.';
        });
    }

    /**
     * Show upload interface
     */
    async showUploadInterface() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading upload options...</p>
            </div>
        `;

        // Load folders and teams
        let folders = [];
        let teams = [];
        
        try {
            const foldersResponse = await fetch(`${getApiBasePath()}/get-folders.php`);
            const foldersData = await foldersResponse.json();
            if (foldersData.success) {
                folders = foldersData.folders || [];
            }
        } catch (error) {
            console.warn('Could not load folders:', error);
        }

        try {
            const teamsResponse = await fetch(`${getApiBasePath()}/get-teams.php`);
            if (!teamsResponse.ok) {
                throw new Error(`HTTP ${teamsResponse.status}: ${teamsResponse.statusText}`);
            }
            
            const teamsData = await teamsResponse.json();
            if (teamsData.success && teamsData.teams) {
                teams = teamsData.teams;
                console.log(`Loaded ${teams.length} team(s) for user`);
            } else {
                console.warn('Teams API returned unsuccessful response:', teamsData);
                teams = [];
            }
        } catch (error) {
            console.error('Could not load teams:', error);
            teams = []; // Default to empty array on error
        }

        // Build upload interface HTML
        const html = `
            <div class="upload-interface container mt-4">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-upload"></i> Upload Dataset
                        </h5>
                    </div>
                    <div class="card-body">
                        <!-- Tabs for different upload methods -->
                        <ul class="nav nav-tabs mb-3" id="uploadTabs" role="tablist">
                            <li class="nav-item" role="presentation">
                                <button class="nav-link active" id="local-tab" data-bs-toggle="tab" 
                                        data-bs-target="#local-upload" type="button" role="tab">
                                    <i class="fas fa-folder-open"></i> Local Upload
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="googledrive-tab" data-bs-toggle="tab" 
                                        data-bs-target="#googledrive-upload" type="button" role="tab">
                                    <i class="fab fa-google-drive"></i> Google Drive
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="s3-tab" data-bs-toggle="tab" 
                                        data-bs-target="#s3-upload" type="button" role="tab">
                                    <i class="fab fa-aws"></i> S3
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="remote-tab" data-bs-toggle="tab" 
                                        data-bs-target="#remote-upload" type="button" role="tab">
                                    <i class="fas fa-link"></i> Remote Server
                                </button>
                            </li>
                        </ul>

                        <!-- Tab content -->
                        <div class="tab-content" id="uploadTabContent">
                            <!-- Local Upload Tab -->
                            <div class="tab-pane fade show active" id="local-upload" role="tabpanel">
                                ${this.renderLocalUploadForm(folders, teams)}
                            </div>

                            <!-- Google Drive Upload Tab -->
                            <div class="tab-pane fade" id="googledrive-upload" role="tabpanel">
                                ${this.renderGoogleDriveUploadForm(folders, teams)}
                            </div>

                            <!-- S3 Upload Tab -->
                            <div class="tab-pane fade" id="s3-upload" role="tabpanel">
                                ${this.renderS3UploadForm(folders, teams)}
                            </div>

                            <!-- Remote Server Upload Tab -->
                            <div class="tab-pane fade" id="remote-upload" role="tabpanel">
                                ${this.renderRemoteUploadForm(folders, teams)}
                            </div>
                        </div>

                        <hr>

                        <!-- Actions -->
                        <div class="d-flex justify-content-between">
                            <button type="button" class="btn btn-secondary" onclick="uploadManager.closeUploadInterface()">
                                <i class="fas fa-times"></i> Close
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        viewerContainer.innerHTML = html;

        // Populate dashboard dropdowns from API
        this.populateDashboardDropdowns();

        // Initialize file input for local upload
        this.initializeLocalFileInput();
    }

    /**
     * Render local upload form
     */
    renderLocalUploadForm(folders, teams) {
        return `
            <form id="localUploadForm">
                <div class="mb-3">
                    <label class="form-label">Name: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="name" value="s3 nasa Test" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Local Source (file, folder, or zip): <span class="text-danger">*</span></label>
                    <div class="d-flex gap-2 mb-2">
                        <button type="button" class="btn btn-sm btn-outline-secondary" id="toggleFileModeBtn" title="Switch to directory selection">
                            <i class="fas fa-exchange-alt"></i> Mode: Select Files
                        </button>
                        <span class="align-self-center small text-muted" id="fileModeIndicator">Current mode: files</span>
                    </div>
                    <div class="input-group mb-2">
                        <button type="button" class="btn btn-outline-secondary" id="openFilePickerBtn">
                            Choose Files
                        </button>
                        <input type="text" class="form-control" id="localFileSelectionLabel" value="No file chosen" readonly>
                    </div>
                    <input type="file" class="form-control" id="localFileInput" 
                           name="files" multiple style="display:none;">
                    <small class="form-text text-muted">
                        Select files or a folder. Use the button above to switch between file and folder selection.
                    </small>
                </div>

                <div class="mb-3">
                    <label class="form-label">Sensor: <span class="text-danger">*</span></label>
                    <select class="form-select" name="sensor" required>
                        <option value="">-- Select Sensor --</option>
                        <option value="IDX">IDX</option>
                        <option value="TIFF">TIFF</option>
                        <option value="TIFF RGB">TIFF RGB</option>
                        <option value="NETCDF">NETCDF</option>
                        <option value="HDF5">HDF5</option>
                        <option value="4D_NEXUS">4D_NEXUS</option>
                        <option value="ORNL_CHESS_STRAIN">ORNL CHESS strain (JSON)</option>
                        <option value="RGB">RGB</option>
                        <option value="MAPIR">MAPIR</option>
                        <option value="OTHER">OTHER</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Metadata/Tags:</label>
                    <input type="text" class="form-control" name="tags" 
                           placeholder="Comma-separated tags">
                </div>

                <div class="mb-3">
                    <label class="form-label">Folder:</label>
                    <select class="form-select" name="folder_uuid" id="localFolderSelect">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
                    <div id="localNewFolderInput" class="mt-2" style="display: none;">
                        <input type="text" class="form-control" name="new_folder_name" 
                               placeholder="Enter new folder name" id="localNewFolderName">
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Team:</label>
                    <select class="form-select" name="team_uuid">
                        <option value="">-- No Team --</option>
                        ${teams.map(t => `<option value="${this.escapeHtml(t.team_name)}">${this.escapeHtml(t.team_name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Team</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Dimensions:</label>
                    <input type="text" class="form-control" name="dimensions" 
                           placeholder="e.g., 2D, 3D, 4D">
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select dashboard-select" name="preferred_dashboard">
                        <option value="">Loading dashboards...</option>
                    </select>
                </div>

                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="is_public" id="localIsPublic">
                        <label class="form-check-label" for="localIsPublic">
                            Public Data Access Granted
                        </label>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Download Permission:</label>
                    <select class="form-select" name="is_downloadable" id="localIsDownloadable">
                        <option value="only owner" selected>Only Owner</option>
                        <option value="only team">Only Team</option>
                        <option value="public">Public</option>
                    </select>
                    <small class="form-text text-muted">Who can download this dataset</small>
                </div>

                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="convert" id="localConvert">
                        <label class="form-check-label" for="localConvert">
                            Convert To IDX
                        </label>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-upload"></i> Upload
                </button>
            </form>
        `;
    }

    /**
     * Render Google Drive upload form
     */
    renderGoogleDriveUploadForm(folders, teams) {
        return `
            <form id="googleDriveUploadForm">
                <div class="mb-3">
                    <label class="form-label">Name: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="name" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Google Drive File or Folder: <span class="text-danger">*</span></label>
                    <div class="input-group mb-2">
                        <span class="input-group-text">Input Type</span>
                        <select class="form-select" id="googleDriveInputType" style="max-width: 150px;">
                            <option value="drive_id">Google Drive ID</option>
                            <option value="folder_link">Full URL</option>
                        </select>
                    </div>
                    <input type="text" class="form-control mb-2" name="drive_id" id="googleDriveId" 
                           placeholder="Enter Google Drive ID (works for both files and folders)" required>
                    <input type="text" class="form-control mb-2" name="folder_link" id="googleDriveFolderLink" 
                           placeholder="Enter full Google Drive URL (e.g., https://drive.google.com/drive/folders/...)" style="display: none;">
                    <small class="form-text text-muted">
                        <span id="googleDriveHelpText">Enter the Google Drive ID from the URL. Works for both files and folders - the system will automatically detect which it is, or</span>
                        <a href="#" id="googleDriveSwitchLink" class="text-decoration-none">paste the full URL instead</a>
                        <br>
                        <strong>Note:</strong> If you provide a folder ID or URL, it will be synced recursively (all files and subfolders will be downloaded).
                    </small>
                </div>

                <div class="mb-3">
                    <label class="form-label">Sensor: <span class="text-danger">*</span></label>
                    <select class="form-select" name="sensor" required>
                        <option value="">-- Select Sensor --</option>
                        <option value="IDX">IDX</option>
                        <option value="TIFF">TIFF</option>
                        <option value="TIFF RGB">TIFF RGB</option>
                        <option value="NETCDF">NETCDF</option>
                        <option value="HDF5">HDF5</option>
                        <option value="4D_NEXUS">4D_NEXUS</option>
                        <option value="ORNL_CHESS_STRAIN">ORNL CHESS strain (JSON)</option>
                        <option value="RGB">RGB</option>
                        <option value="MAPIR">MAPIR</option>
                        <option value="OTHER">OTHER</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Metadata/Tags:</label>
                    <input type="text" class="form-control" name="tags" 
                           placeholder="Comma-separated tags">
                </div>

                <div class="mb-3">
                    <label class="form-label">Folder:</label>
                    <select class="form-select" name="folder_uuid" id="googleDriveFolderSelect">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
                    <div id="googleDriveNewFolderInput" class="mt-2" style="display: none;">
                        <input type="text" class="form-control" name="new_folder_name" 
                               placeholder="Enter new folder name" id="googleDriveNewFolderName">
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Team:</label>
                    <select class="form-select" name="team_uuid">
                        <option value="">-- No Team --</option>
                        ${teams.map(t => `<option value="${this.escapeHtml(t.team_name)}">${this.escapeHtml(t.team_name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Team</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Dimensions:</label>
                    <input type="text" class="form-control" name="dimensions" 
                           placeholder="e.g., 1024x1024x100 or 2D, 3D, 4D">
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select dashboard-select" name="preferred_dashboard">
                        <option value="">Loading dashboards...</option>
                    </select>
                </div>

                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="is_public" id="googleIsPublic">
                        <label class="form-check-label" for="googleIsPublic">
                            Public Data Access Granted
                        </label>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Download Permission:</label>
                    <select class="form-select" name="is_downloadable" id="googleIsDownloadable">
                        <option value="only owner" selected>Only Owner</option>
                        <option value="only team">Only Team</option>
                        <option value="public">Public</option>
                    </select>
                    <small class="form-text text-muted">Who can download this dataset</small>
                </div>

                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="convert" id="googleConvert">
                        <label class="form-check-label" for="googleConvert">
                            Convert To IDX
                        </label>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-upload"></i> Upload from Google Drive
                </button>
            </form>
        `;
    }

    /**
     * Render S3 upload form
     */
    renderS3UploadForm(folders, teams) {
        const defaultBucket = (window.S3_DEFAULT_BUCKET || '').toString().trim();
        const defaultPrefix = (window.S3_DEFAULT_PREFIX || '').toString().trim();
        const defaultEndpoint = (window.S3_DEFAULT_ENDPOINT || '').toString().trim();
        const defaultAccessKey = (window.S3_DEFAULT_ACCESS_KEY || '').toString().trim();
        const defaultSecretKey = (window.S3_DEFAULT_SECRET_KEY || '').toString();
        const defaultRegion = (window.S3_DEFAULT_REGION || 'us-east-1').toString().trim() || 'us-east-1';
        const defaultPathStyle = window.S3_DEFAULT_PATH_STYLE !== false;
        const defaultLink = defaultBucket
            ? `s3://${defaultBucket}${defaultPrefix ? `/${defaultPrefix}` : ''}`
            : '';
        return `
            <form id="s3UploadForm">
                <div class="mb-3">
                    <label class="form-label">Name: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="name" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">S3 Source Input Mode:</label>
                    <select class="form-select" name="s3_source_mode" id="s3SourceMode">
                        <option value="link">Single S3/HTTP Link</option>
                        <option value="fields">Endpoint + Bucket + Prefix</option>
                    </select>
                </div>

                <div class="mb-3" id="s3LinkGroup">
                    <label class="form-label">S3 Dataset Link:</label>
                    <input type="text" class="form-control" name="s3_link" 
                           placeholder="https://us-east-1.gw.future-tech-holdings.com/nasa-t0/nex-gddp-cmip6/nex-gddp-cmip6.idx"
                           value="${this.escapeHtml(defaultLink)}">
                    <small class="form-text text-muted">You can also use <code>s3://bucket/prefix/...</code> links.</small>
                </div>

                <div id="s3FieldsGroup" style="display:none;">
                <div class="mb-3">
                    <label class="form-label">Endpoint URL:</label>
                    <input type="text" class="form-control" name="endpoint_url" 
                           placeholder="https://s3.amazonaws.com"
                           value="${this.escapeHtml(defaultEndpoint)}">
                </div>

                <div class="mb-3">
                    <label class="form-label">Bucket: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="bucket" value="${this.escapeHtml(defaultBucket)}" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Prefix (directory on S3):</label>
                    <input type="text" class="form-control" name="prefix" 
                           placeholder="path/to/files/"
                           value="${this.escapeHtml(defaultPrefix)}">
                </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Access Key: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="access_key" value="${this.escapeHtml(defaultAccessKey)}" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Secret Key: <span class="text-danger">*</span></label>
                    <input type="password" class="form-control" name="secret_key" value="${this.escapeHtml(defaultSecretKey)}" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Region</label>
                    <input type="text" class="form-control" name="region" value="${this.escapeHtml(defaultRegion)}" placeholder="us-east-1">
                </div>

                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" name="path_style" id="s3UploadPathStyle" ${defaultPathStyle ? 'checked' : ''}>
                    <label class="form-check-label" for="s3UploadPathStyle">Path-style addressing (recommended for Wasabi / MinIO / many S3-compatible gateways)</label>
                </div>

                <div class="mb-3 d-flex flex-wrap align-items-center gap-2">
                    <button type="button" class="btn btn-outline-secondary btn-sm" id="s3TestConnectionBtn">
                        <i class="fas fa-plug"></i> Test S3 connection
                    </button>
                    <span id="s3TestConnectionResult" class="small text-muted"></span>
                </div>

                <div class="mb-3">
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="checkbox" name="convert" id="s3ConvertIdx">
                        <label class="form-check-label" for="s3ConvertIdx">
                            Download dataset from S3 to the server and run full conversion (mirror + IDX → ARCO when applicable)
                        </label>
                    </div>
                    <small class="form-text text-muted d-block">
                        Unchecked: keep data in S3 only; for <strong>sensor IDX</strong> paths ending in <code>.idx</code>, the server still queues background work to write a resolved <code>visus.idx</code> under converted/ (no tile mirror). Check this box when you want a full local copy under upload/ as well.
                    </small>
                </div>

                <div class="mb-3">
                    <label class="form-label">Sensor: <span class="text-danger">*</span></label>
                    <select class="form-select" name="sensor" required>
                        <option value="">-- Select Sensor --</option>
                        <option value="IDX">IDX</option>
                        <option value="TIFF">TIFF</option>
                        <option value="TIFF RGB">TIFF RGB</option>
                        <option value="NETCDF">NETCDF</option>
                        <option value="HDF5">HDF5</option>
                        <option value="4D_NEXUS">4D_NEXUS</option>
                        <option value="ORNL_CHESS_STRAIN">ORNL CHESS strain (JSON)</option>
                        <option value="RGB">RGB</option>
                        <option value="MAPIR">MAPIR</option>
                        <option value="OTHER">OTHER</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Metadata/Tags:</label>
                    <input type="text" class="form-control" name="tags" 
                           placeholder="Comma-separated tags">
                </div>

                <div class="mb-3">
                    <label class="form-label">Folder:</label>
                    <select class="form-select" name="folder_uuid" id="s3FolderSelect">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
                    <div id="s3NewFolderInput" class="mt-2" style="display: none;">
                        <input type="text" class="form-control" name="new_folder_name" 
                               placeholder="Enter new folder name" id="s3NewFolderName">
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Team:</label>
                    <select class="form-select" name="team_uuid">
                        <option value="">-- No Team --</option>
                        ${teams.map(t => `<option value="${this.escapeHtml(t.team_name)}">${this.escapeHtml(t.team_name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Team</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Dimensions:</label>
                    <input type="text" class="form-control" name="dimensions" 
                           placeholder="e.g., 1024x1024x100 or 2D, 3D, 4D">
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select dashboard-select" name="preferred_dashboard">
                        <option value="">Loading dashboards...</option>
                    </select>
                </div>

                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="is_public" id="s3IsPublic">
                        <label class="form-check-label" for="s3IsPublic">
                            Public Data Access Granted
                        </label>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-plug"></i> Connect to Data Portal
                </button>
            </form>
        `;
    }

    /**
     * Render remote server upload form
     */
    renderRemoteUploadForm(folders, teams) {
        return `
            <form id="remoteUploadForm">
                <div class="mb-3">
                    <label class="form-label">Name: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="name" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Server Link: <span class="text-danger">*</span></label>
                    <input type="url" class="form-control" name="server_link" 
                           placeholder="https://server.com/mod_visus?dataset=..." required>
                    <small class="form-text text-muted">
                        Enter the URL to the remote server data (S3 or HTTP Visus served data)
                    </small>
                </div>

                <div class="mb-3">
                    <label class="form-label">Sensor: <span class="text-danger">*</span></label>
                    <select class="form-select" name="sensor" required>
                        <option value="">-- Select Sensor --</option>
                        <option value="IDX">IDX</option>
                        <option value="TIFF">TIFF</option>
                        <option value="TIFF RGB">TIFF RGB</option>
                        <option value="NETCDF">NETCDF</option>
                        <option value="HDF5">HDF5</option>
                        <option value="4D_NEXUS">4D_NEXUS</option>
                        <option value="ORNL_CHESS_STRAIN">ORNL CHESS strain (JSON)</option>
                        <option value="RGB">RGB</option>
                        <option value="MAPIR">MAPIR</option>
                        <option value="OTHER">OTHER</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Metadata/Tags:</label>
                    <input type="text" class="form-control" name="tags" 
                           placeholder="Comma-separated tags">
                </div>

                <div class="mb-3">
                    <label class="form-label">Folder:</label>
                    <select class="form-select" name="folder_uuid" id="remoteFolderSelect">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
                    <div id="remoteNewFolderInput" class="mt-2" style="display: none;">
                        <input type="text" class="form-control" name="new_folder_name" 
                               placeholder="Enter new folder name" id="remoteNewFolderName">
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Team:</label>
                    <select class="form-select" name="team_uuid">
                        <option value="">-- No Team --</option>
                        ${teams.map(t => `<option value="${this.escapeHtml(t.team_name)}">${this.escapeHtml(t.team_name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Team</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Dimensions:</label>
                    <input type="text" class="form-control" name="dimensions" 
                           placeholder="e.g., 1024x1024x100 or 2D, 3D, 4D">
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select dashboard-select" name="preferred_dashboard">
                        <option value="">Loading dashboards...</option>
                    </select>
                </div>

                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="is_public" id="remoteIsPublic">
                        <label class="form-check-label" for="remoteIsPublic">
                            Is data public
                        </label>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-link"></i> Link Remote Server Data
                </button>
            </form>
        `;
    }

    /**
     * Setup team dropdown event listeners
     */
    setupTeamDropdownListeners() {
        // Get all team dropdowns in upload forms
        const teamSelects = document.querySelectorAll('select[name="team_uuid"]');
        
        console.log(`Setting up team dropdown listeners for ${teamSelects.length} dropdown(s)`);
        
        teamSelects.forEach((select, index) => {
            // Remove any existing listeners to avoid duplicates
            const newSelect = select.cloneNode(true);
            select.parentNode.replaceChild(newSelect, select);
            
            newSelect.addEventListener('change', async (e) => {
                console.log('Team dropdown changed:', e.target.value);
                if (e.target.value === '__CREATE__') {
                    // Reset to empty to prevent form submission issues
                    e.target.value = '';
                    
                    console.log('Opening create team modal...');
                    // Show create team modal
                    try {
                        const createdTeam = await this.showCreateTeamModal();
                        
                        if (createdTeam) {
                            console.log('Team created successfully:', createdTeam);
                            // Refresh teams in all dropdowns and select the new team
                            await this.refreshTeamDropdowns(createdTeam.team_name);
                        } else {
                            console.log('Team creation cancelled or failed');
                        }
                    } catch (error) {
                        console.error('Error in create team modal:', error);
                        alert('Error opening create team dialog: ' + error.message);
                    }
                }
            });
        });
    }

    /**
     * Show create team modal (returns created team info or null)
     */
    async showCreateTeamModal() {
        return new Promise(async (resolve) => {
            // Fetch teams for parent selection
            let teams = [];
            try {
                const teamsResponse = await fetch(`${getApiBasePath()}/get-teams.php`);
                if (teamsResponse.ok) {
                    const teamsData = await teamsResponse.json();
                    if (teamsData.success && teamsData.teams) {
                        const userEmail = await this.getUserEmail();
                        teams = teamsData.teams.filter(team => team.is_owner || team.owner === userEmail);
                    }
                }
            } catch (error) {
                console.warn('Could not load teams for parent selection:', error);
            }

            // Create modal HTML
            const modalHtml = `
                <div class="modal fade" id="createTeamModal" tabindex="-1" aria-labelledby="createTeamModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title" id="createTeamModalLabel">
                                    <i class="fas fa-users"></i> Create New Team
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <form id="createTeamModalForm">
                                    <div class="mb-3">
                                        <label class="form-label">Team Name: <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" name="team_name" required>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label class="form-label">Parent Team: <span class="text-muted">(optional)</span></label>
                                        <select class="form-select" name="team_parent" id="team_parent_modal">
                                            <option value="">Select Parent Team (optional)</option>
                                            ${teams.map(team => `<option value="${team.uuid}">${this.escapeHtml(team.team_name)}</option>`).join('')}
                                        </select>
                                        <small class="form-text text-muted">Select a parent team if this team should be under another team</small>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label class="form-label">Member Emails:</label>
                                        <div id="team-email-entries-modal">
                                            <div class="email-entry mb-2">
                                                <input type="email" class="form-control form-control-sm" 
                                                       placeholder="member@example.com" 
                                                       data-entry-index="1">
                                            </div>
                                        </div>
                                        <button type="button" class="btn btn-sm btn-outline-secondary mt-2" 
                                                onclick="uploadManager.addTeamEmailEntryModal()">
                                            <i class="fas fa-plus"></i> Add Email
                                        </button>
                                    </div>
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" id="createTeamModalSubmit">
                                    <i class="fas fa-plus"></i> Create Team
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Remove existing modal if any
            const existingModal = document.getElementById('createTeamModal');
            if (existingModal) {
                existingModal.remove();
            }

            // Add modal to body
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // Initialize Bootstrap modal
            const modalElement = document.getElementById('createTeamModal');
            if (!modalElement) {
                console.error('Modal element not found after insertion');
                resolve(null);
                return;
            }
            
            // Check if Bootstrap is available
            if (typeof bootstrap === 'undefined') {
                console.error('Bootstrap is not available. Make sure bootstrap.bundle.min.js is loaded.');
                alert('Error: Bootstrap library not loaded. Please refresh the page.');
                resolve(null);
                return;
            }
            
            // Wait for DOM to be ready
            setTimeout(() => {
                try {
                    const modal = new bootstrap.Modal(modalElement, {
                        backdrop: 'static',
                        keyboard: false
                    });
                    
                    // Setup form handler
                    const form = document.getElementById('createTeamModalForm');
                    const submitBtn = document.getElementById('createTeamModalSubmit');
                    
                    if (!form || !submitBtn) {
                        console.error('Form elements not found in modal');
                        resolve(null);
                        return;
                    }
                    
                    const handleSubmit = async () => {
                        const createdTeam = await this.handleCreateTeamModal(form);
                        if (createdTeam) {
                            modal.hide();
                            // Wait for modal to hide before removing
                            setTimeout(() => {
                                modalElement.remove();
                            }, 300);
                            resolve(createdTeam);
                        }
                    };

                    submitBtn.addEventListener('click', handleSubmit);
                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        await handleSubmit();
                    });

                    // Handle modal close
                    modalElement.addEventListener('hidden.bs.modal', () => {
                        modalElement.remove();
                        resolve(null);
                    });

                    // Show modal
                    modal.show();
                    console.log('Create team modal shown');
                } catch (error) {
                    console.error('Error initializing modal:', error);
                    alert('Error opening create team dialog: ' + error.message);
                    resolve(null);
                }
            }, 10);
        });
    }

    /**
     * Handle create team from modal
     */
    async handleCreateTeamModal(form) {
        const formData = new FormData(form);
        const teamName = formData.get('team_name');
        const parentTeamUuid = formData.get('team_parent');
        
        if (!teamName) {
            alert('Team name is required');
            return null;
        }

        // Get email entries
        const emailInputs = document.querySelectorAll('#team-email-entries-modal input[type="email"]');
        const emails = Array.from(emailInputs)
            .map(input => input.value.trim())
            .filter(email => email && this.isValidEmail(email));

        // Get parent team UUID(s) - convert to array format
        const parents = parentTeamUuid ? [parentTeamUuid] : [];

        const userEmail = await this.getUserEmail();
        if (!userEmail) {
            alert('User not authenticated');
            return null;
        }

        try {
            const response = await fetch(`${getApiBasePath()}/create-team.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    team_name: teamName,
                    emails: emails,
                    parents: parents,
                    owner_email: userEmail
                })
            });

            // Check if response is ok
            if (!response.ok) {
                // Try to get error message from response
                let errorMessage = `Server error: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (e) {
                    // If response is not JSON, try to get text
                    try {
                        const errorText = await response.text();
                        if (errorText) {
                            errorMessage = errorText;
                        }
                    } catch (e2) {
                        // Ignore
                    }
                }
                console.error('Team creation failed:', errorMessage);
                alert(`Error creating team: ${errorMessage}`);
                return null;
            }

            const data = await response.json();
            console.log('Team creation response:', data);

            if (data.success) {
                return {
                    team_name: teamName,
                    team: data.team
                };
            } else {
                const errorMessage = data.error || data.message || 'Unknown error';
                console.error('Team creation failed:', errorMessage);
                alert(`Error creating team: ${errorMessage}`);
                return null;
            }
        } catch (error) {
            console.error('Error creating team:', error);
            alert('Error creating team: ' + error.message);
            return null;
        }
    }

    /**
     * Add team email entry in modal
     */
    addTeamEmailEntryModal() {
        const container = document.getElementById('team-email-entries-modal');
        if (!container) return;

        const entries = container.querySelectorAll('.email-entry');
        const nextIndex = entries.length + 1;

        const newEntry = document.createElement('div');
        newEntry.className = 'email-entry mb-2';
        newEntry.innerHTML = `
            <div class="input-group">
                <input type="email" class="form-control form-control-sm" 
                       placeholder="member@example.com" 
                       data-entry-index="${nextIndex}">
                <button type="button" class="btn btn-sm btn-outline-danger" 
                        onclick="this.closest('.email-entry').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        container.appendChild(newEntry);
    }

    /**
     * Refresh team dropdowns in all upload forms
     */
    async refreshTeamDropdowns(selectedTeamName = null) {
        try {
            const teamsResponse = await fetch(`${getApiBasePath()}/get-teams.php`);
            if (!teamsResponse.ok) {
                throw new Error(`HTTP ${teamsResponse.status}: ${teamsResponse.statusText}`);
            }
            
            const teamsData = await teamsResponse.json();
            if (teamsData.success && teamsData.teams) {
                const teams = teamsData.teams;
                
                // Update all team dropdowns
                const teamSelects = document.querySelectorAll('select[name="team_uuid"]');
                teamSelects.forEach(select => {
                    // Store current value
                    const currentValue = select.value;
                    
                    // Clear and rebuild options
                    select.innerHTML = `
                        <option value="">-- No Team --</option>
                        ${teams.map(t => `<option value="${this.escapeHtml(t.team_name)}">${this.escapeHtml(t.team_name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Team</option>
                    `;
                    
                    // Restore selection or select new team
                    if (selectedTeamName) {
                        select.value = selectedTeamName;
                    } else if (currentValue && currentValue !== '__CREATE__') {
                        select.value = currentValue;
                    }
                });
            }
        } catch (error) {
            console.error('Error refreshing team dropdowns:', error);
        }
    }

    /**
     * Setup folder dropdown event listeners
     */
    setupFolderDropdownListeners() {
        // Local upload form
        const localFolderSelect = document.getElementById('localFolderSelect');
        const localNewFolderInput = document.getElementById('localNewFolderInput');
        if (localFolderSelect && localNewFolderInput) {
            localFolderSelect.addEventListener('change', (e) => {
                if (e.target.value === '__CREATE__') {
                    localNewFolderInput.style.display = 'block';
                } else {
                    localNewFolderInput.style.display = 'none';
                }
            });
        }

        // Google Drive upload form
        const googleDriveFolderSelect = document.getElementById('googleDriveFolderSelect');
        const googleDriveNewFolderInput = document.getElementById('googleDriveNewFolderInput');
        if (googleDriveFolderSelect && googleDriveNewFolderInput) {
            googleDriveFolderSelect.addEventListener('change', (e) => {
                if (e.target.value === '__CREATE__') {
                    googleDriveNewFolderInput.style.display = 'block';
                } else {
                    googleDriveNewFolderInput.style.display = 'none';
                }
            });
        }

        // S3 upload form
        const s3FolderSelect = document.getElementById('s3FolderSelect');
        const s3NewFolderInput = document.getElementById('s3NewFolderInput');
        if (s3FolderSelect && s3NewFolderInput) {
            s3FolderSelect.addEventListener('change', (e) => {
                if (e.target.value === '__CREATE__') {
                    s3NewFolderInput.style.display = 'block';
                } else {
                    s3NewFolderInput.style.display = 'none';
                }
            });
        }

        // Remote upload form
        const remoteFolderSelect = document.getElementById('remoteFolderSelect');
        const remoteNewFolderInput = document.getElementById('remoteNewFolderInput');
        if (remoteFolderSelect && remoteNewFolderInput) {
            remoteFolderSelect.addEventListener('change', (e) => {
                if (e.target.value === '__CREATE__') {
                    remoteNewFolderInput.style.display = 'block';
                } else {
                    remoteNewFolderInput.style.display = 'none';
                }
            });
        }
    }

    /**
     * Get folder value from form (handles both existing folder UUID and new folder name)
     */
    getFolderValue(form) {
        const formData = new FormData(form);
        const folderUuid = formData.get('folder_uuid');
        
        if (folderUuid === '__CREATE__') {
            // User wants to create a new folder - get the name from the input
            const newFolderName = formData.get('new_folder_name');
            if (newFolderName && newFolderName.trim()) {
                return newFolderName.trim();
            }
            return null; // No folder name provided
        }
        
        return folderUuid || null;
    }

    setupS3SourceMode(form) {
        const modeSelect = form.querySelector('#s3SourceMode');
        const linkGroup = form.querySelector('#s3LinkGroup');
        const fieldsGroup = form.querySelector('#s3FieldsGroup');
        if (!modeSelect || !linkGroup || !fieldsGroup) return;

        const applyMode = () => {
            const mode = modeSelect.value || 'link';
            if (mode === 'fields') {
                linkGroup.style.display = 'none';
                fieldsGroup.style.display = 'block';
            } else {
                linkGroup.style.display = 'block';
                fieldsGroup.style.display = 'none';
            }
        };

        modeSelect.addEventListener('change', applyMode);
        applyMode();
    }

    resolveS3Source(formData) {
        const normalizeDatasetPrefix = (value) => {
            const raw = (value || '').toString().trim();
            if (!raw) return '';
            // Keep the exact object key (including `.../something.idx`). The backend derives
            // the recursive download prefix from the parent folder when the key ends in `.idx`.
            if (raw.endsWith('/')) return raw;
            const leaf = raw.split('/').pop() || '';
            if (leaf.includes('.')) return raw;
            return `${raw}/`;
        };

        const mode = (formData.get('s3_source_mode') || 'link').toString();
        if (mode === 'fields') {
            const bucket = (formData.get('bucket') || '').toString().trim();
            const prefix = normalizeDatasetPrefix(formData.get('prefix'));
            const endpointUrl = (formData.get('endpoint_url') || '').toString().trim();
            return { bucket, prefix, endpointUrl, rawLink: '' };
        }

        const rawLink = (formData.get('s3_link') || '').toString().trim();
        if (!rawLink) {
            return { error: 'S3 dataset link is required when using link mode.' };
        }

        if (rawLink.startsWith('s3://')) {
            const noScheme = rawLink.slice(5);
            const slash = noScheme.indexOf('/');
            const bucket = slash === -1 ? noScheme : noScheme.slice(0, slash);
            const prefix = slash === -1 ? '' : normalizeDatasetPrefix(noScheme.slice(slash + 1));
            if (!bucket) return { error: 'Invalid s3:// link (missing bucket).' };
            return { bucket, prefix, endpointUrl: '', rawLink };
        }

        try {
            const u = new URL(rawLink);
            const segments = (u.pathname || '').split('/').filter(Boolean);
            if (segments.length < 2) {
                return { error: 'HTTP S3 link must include bucket and object path.' };
            }
            const bucket = segments[0];
            const prefix = normalizeDatasetPrefix(segments.slice(1).join('/'));
            const endpointUrl = `${u.protocol}//${u.host}`;
            return { bucket, prefix, endpointUrl, rawLink };
        } catch (_e) {
            return { error: 'Invalid S3 link. Use s3://bucket/path or https://endpoint/bucket/path.' };
        }
    }

    /**
     * Initialize local file input
     */
    initializeLocalFileInput() {
        const fileInput = document.getElementById('localFileInput');
        const toggleBtn = document.getElementById('toggleFileModeBtn');
        const modeIndicator = document.getElementById('fileModeIndicator');
        const openPickerBtn = document.getElementById('openFilePickerBtn');
        const selectionLabel = document.getElementById('localFileSelectionLabel');
        let isDirectoryMode = false;

        const updatePickerUi = () => {
            if (isDirectoryMode) {
                fileInput.setAttribute('webkitdirectory', '');
                fileInput.setAttribute('directory', '');
                if (toggleBtn) {
                    toggleBtn.innerHTML = '<i class="fas fa-exchange-alt"></i> Mode: Select Folder';
                    toggleBtn.title = 'Switch to file selection mode';
                }
                if (modeIndicator) {
                    modeIndicator.textContent = 'Current mode: folder';
                }
                if (openPickerBtn) {
                    openPickerBtn.textContent = 'Choose Folder';
                }
            } else {
                fileInput.removeAttribute('webkitdirectory');
                fileInput.removeAttribute('directory');
                if (toggleBtn) {
                    toggleBtn.innerHTML = '<i class="fas fa-exchange-alt"></i> Mode: Select Files';
                    toggleBtn.title = 'Switch to folder selection mode';
                }
                if (modeIndicator) {
                    modeIndicator.textContent = 'Current mode: files';
                }
                if (openPickerBtn) {
                    openPickerBtn.textContent = 'Choose Files';
                }
            }

            if (selectionLabel) {
                selectionLabel.value = 'No file chosen';
            }
        };

        // Setup toggle button to switch between file and directory modes
        if (toggleBtn && fileInput) {
            toggleBtn.addEventListener('click', () => {
                isDirectoryMode = !isDirectoryMode;

                // Clear current selection
                fileInput.value = '';
                updatePickerUi();
            });
        }

        if (openPickerBtn && fileInput) {
            openPickerBtn.addEventListener('click', () => {
                fileInput.click();
            });
        }

        if (fileInput) {
            // Allow both file and directory selection
            fileInput.addEventListener('change', (e) => {
                const files = e.target.files;
                if (files.length > 0) {
                    if (selectionLabel) {
                        if (isDirectoryMode) {
                            const rootName = (files[0].webkitRelativePath || '').split('/')[0] || 'folder';
                            selectionLabel.value = `${rootName} (${files.length} files)`;
                        } else if (files.length === 1) {
                            selectionLabel.value = files[0].name;
                        } else {
                            selectionLabel.value = `${files.length} files selected`;
                        }
                    }
                    console.log(`Selected ${files.length} file(s) for upload`);
                    // Log file types to help debug
                    const fileTypes = Array.from(files).map(f => ({
                        name: f.name,
                        type: f.type,
                        extension: f.name.split('.').pop().toLowerCase()
                    }));
                    console.log('File details:', fileTypes);
                    
                    // Check for .nxs files only if sensor contains NEXUS
                    const form = fileInput.closest('form');
                    if (form) {
                        const sensorSelect = form.querySelector('select[name="sensor"]');
                        if (sensorSelect) {
                            const sensor = sensorSelect.value;
                            if (sensor && sensor.toUpperCase().includes('NEXUS')) {
                                const nxsFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.nxs'));
                                if (nxsFiles.length > 0) {
                                    console.log(`✅ Found ${nxsFiles.length} .nxs file(s) for NEXUS sensor:`, nxsFiles.map(f => f.name));
                                } else {
                                    console.warn(`⚠️  No .nxs files found in selection for NEXUS sensor type: ${sensor}`);
                                }
                            }
                        }
                    }
                }
            });
        }

        updatePickerUi();

        // Setup sensor change listener to check for .nxs files when NEXUS is selected
        const sensorSelect = document.querySelector('select[name="sensor"]');
        if (sensorSelect) {
            sensorSelect.addEventListener('change', (e) => {
                const sensor = e.target.value;
                const fileInput = document.getElementById('localFileInput');
                if (fileInput && fileInput.files && fileInput.files.length > 0 && sensor && sensor.toUpperCase().includes('NEXUS')) {
                    const files = Array.from(fileInput.files);
                    const nxsFiles = files.filter(f => f.name.toLowerCase().endsWith('.nxs'));
                    if (nxsFiles.length > 0) {
                        console.log(`✅ Found ${nxsFiles.length} .nxs file(s) for NEXUS sensor:`, nxsFiles.map(f => f.name));
                    } else {
                        console.warn(`⚠️  No .nxs files found in selection for NEXUS sensor type: ${sensor}`);
                    }
                }
            });
        }

        // Setup folder dropdown listeners
        this.setupFolderDropdownListeners();

        // Setup team dropdown listeners
        this.setupTeamDropdownListeners();

        // Setup form submission handlers
        const localForm = document.getElementById('localUploadForm');
        if (localForm) {
            localForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLocalUpload(localForm);
            });
        }

        const googleForm = document.getElementById('googleDriveUploadForm');
        if (googleForm) {
            googleForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleGoogleDriveUpload(googleForm);
            });
            
            // Handle input type switching (Google Drive ID vs folder link)
            const inputTypeSelect = document.getElementById('googleDriveInputType');
            const driveIdInput = document.getElementById('googleDriveId');
            const folderLinkInput = document.getElementById('googleDriveFolderLink');
            const helpText = document.getElementById('googleDriveHelpText');
            const switchLink = document.getElementById('googleDriveSwitchLink');
            
            if (inputTypeSelect && driveIdInput && folderLinkInput) {
                // Function to toggle between Google Drive ID and folder link inputs
                const toggleInputType = (isDriveId) => {
                    driveIdInput.style.display = isDriveId ? 'block' : 'none';
                    driveIdInput.required = isDriveId;
                    folderLinkInput.style.display = isDriveId ? 'none' : 'block';
                    folderLinkInput.required = !isDriveId;
                    
                    // Clear the hidden input when switching
                    if (isDriveId) {
                        folderLinkInput.value = '';
                    } else {
                        driveIdInput.value = '';
                    }
                    
                    if (helpText) {
                        helpText.textContent = isDriveId 
                            ? 'Enter the Google Drive ID from the URL. Works for both files and folders - the system will automatically detect which it is, or '
                            : 'Enter the full Google Drive URL (works for both files and folders), or ';
                    }
                    if (switchLink) {
                        switchLink.textContent = isDriveId ? 'paste the full URL instead' : 'use a Google Drive ID instead';
                    }
                };
                
                // Handle dropdown change
                inputTypeSelect.addEventListener('change', (e) => {
                    toggleInputType(e.target.value === 'drive_id');
                });
                
                // Handle switch link click
                if (switchLink) {
                    switchLink.addEventListener('click', (e) => {
                        e.preventDefault();
                        const newValue = inputTypeSelect.value === 'drive_id' ? 'folder_link' : 'drive_id';
                        inputTypeSelect.value = newValue;
                        toggleInputType(newValue === 'drive_id');
                    });
                }
            }
        }

        const s3Form = document.getElementById('s3UploadForm');
        if (s3Form) {
            s3Form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleS3Upload(s3Form);
            });
            this.setupS3SourceMode(s3Form);
        }
        const s3TestBtn = document.getElementById('s3TestConnectionBtn');
        if (s3TestBtn && s3Form) {
            s3TestBtn.addEventListener('click', () => {
                this.testS3UploadConnection(s3Form);
            });
        }

        const remoteForm = document.getElementById('remoteUploadForm');
        if (remoteForm) {
            remoteForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleRemoteUpload(remoteForm);
            });
        }
    }

    /**
     * Generate a UUID v4
     */
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Handle local file upload
     */
    async handleLocalUpload(form) {
        const formData = new FormData(form);
        const rawFiles = document.getElementById('localFileInput').files;
        const files = Array.from(rawFiles || []).filter((file) => {
            const name = String(file?.name || '').trim();
            return name && name !== '.DS_Store';
        });

        if (!files || files.length === 0) {
            alert('Please select at least one file (excluding .DS_Store)');
            return;
        }

        // Get user email
        const userEmail = await this.getUserEmail();
        if (!userEmail) {
            alert('User not authenticated');
            return;
        }

        // Prepare upload data
        const folderValue = this.getFolderValue(form);
        console.log('Folder value from form:', folderValue);

        const sensorUpper = String(formData.get('sensor') || '').trim().toUpperCase();
        const uploadData = {
            dataset_name: formData.get('name'),
            sensor: formData.get('sensor'),
            convert: formData.get('convert') === 'on',
            is_public: formData.get('is_public') === 'on',
            is_downloadable: formData.get('is_downloadable') || 'only owner',
            folder: folderValue,
            team_uuid: formData.get('team_uuid') || null,
            tags: formData.get('tags') || '',
            dimensions: formData.get('dimensions') || null,
            preferred_dashboard:
                formData.get('preferred_dashboard') ||
                (sensorUpper === 'IDX' ? 'DarkMatter' : 'OpenVisusSlice'),
        };

        const selectedExtensions = files.map(f => (f.name.split('.').pop() || '').toLowerCase());
        const selectedExtensionSet = new Set(selectedExtensions);

        if (sensorUpper === 'IDX' && (selectedExtensionSet.has('tif') || selectedExtensionSet.has('tiff')) && !selectedExtensionSet.has('idx')) {
            const proceed = confirm(
                'The selected files look like TIFF data, but Sensor is set to IDX.\n\n' +
                'You can still upload raw data to ScientistCloud. Choose Sensor = TIFF if you want the selection labeled as TIFF, or continue if IDX is intentional.'
            );
            if (!proceed) {
                return;
            }
        }

        // Upload files - handle multiple files by uploading them sequentially
        // For directories, the browser will provide all files
        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            this.localBrowserUploadInProgress = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading - keep this page open';

            // Show upload progress modal
            this.showUploadModal(uploadData.dataset_name, files.length);
            
            // Store convert flag in session for completion message
            if (this.currentUploadSession) {
                this.currentUploadSession.willConvert = uploadData.convert;
            }

            // Generate a single UUID for all files to group them in the same dataset
            const datasetUuid = this.generateUUID();
            console.log(`Grouping ${files.length} file(s) under dataset UUID: ${datasetUuid}`);
            if (this.currentUploadSession) {
                this.currentUploadSession.datasetUuid = datasetUuid;
            }
            
            const uploadPromises = [];
            
            // Check if this is a directory upload (files have webkitRelativePath)
            const isDirectoryUpload = files.length > 0 && files[0].webkitRelativePath && files[0].webkitRelativePath.includes('/');
            let baseDirectoryName = null;
            
            if (isDirectoryUpload) {
                // Extract the base directory name from the first file's path
                // e.g., "Sampad/file1.tif" -> base is "Sampad"
                const firstPath = files[0].webkitRelativePath;
                baseDirectoryName = firstPath.split('/')[0];
                console.log(`Directory upload detected. Base directory: ${baseDirectoryName}`);
            }

            const expectedFiles = files.map((file) => {
                let relativePath = file.name;
                if (isDirectoryUpload && file.webkitRelativePath) {
                    const fullPath = file.webkitRelativePath;
                    relativePath = fullPath.startsWith(baseDirectoryName + '/')
                        ? fullPath.substring(baseDirectoryName.length + 1)
                        : fullPath;
                }
                return {
                    relative_path: relativePath.replace(/^\/+/, ''),
                    name: file.name,
                    size: file.size || 0,
                    last_modified: file.lastModified || null,
                    type: file.type || ''
                };
            });
            const expectedFilesJson = JSON.stringify(expectedFiles);
            uploadData.expected_files_json = expectedFilesJson;
            
            // Log all files being processed
            console.log(`Processing ${files.length} file(s) for upload`);
            console.log('File extensions:', [...selectedExtensionSet]);
            
            // Check for .nxs files only if sensor contains NEXUS
            const isNexusSensor = uploadData.sensor && uploadData.sensor.toUpperCase().includes('NEXUS');
            if (isNexusSensor) {
                const nxsFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.nxs'));
                if (nxsFiles.length > 0) {
                    console.log(`✅ Processing ${nxsFiles.length} .nxs file(s) for NEXUS sensor:`, nxsFiles.map(f => f.name));
                } else {
                    console.warn(`⚠️  No .nxs files found in selection for NEXUS sensor type: ${uploadData.sensor}`);
                }
            }
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                
                // Log .nxs files specifically only for NEXUS sensors
                if (isNexusSensor && file.name.toLowerCase().endsWith('.nxs')) {
                    console.log(`📦 Processing .nxs file ${i + 1}/${files.length}: ${file.name}`);
                }
                
                // For directory uploads, extract the relative path without the base directory
                // e.g., "Sampad/subdir/file.tif" -> "subdir/file.tif"
                let relativePath = null;
                if (isDirectoryUpload && file.webkitRelativePath) {
                    const fullPath = file.webkitRelativePath;
                    // Remove the base directory name from the path
                    if (fullPath.startsWith(baseDirectoryName + '/')) {
                        relativePath = fullPath.substring(baseDirectoryName.length + 1);
                        // If relativePath is empty or just the filename, set to null (file goes in root)
                        if (!relativePath || relativePath === file.name) {
                            relativePath = null;
                        } else {
                            // Remove the filename from the path to get just the directory structure
                            const pathParts = relativePath.split('/');
                            pathParts.pop(); // Remove filename
                            relativePath = pathParts.length > 0 ? pathParts.join('/') : null;
                        }
                    }
                }
                
                const uploadFormData = new FormData();
                uploadFormData.append('file', file);
                uploadFormData.append('user_email', userEmail);
                uploadFormData.append('dataset_name', uploadData.dataset_name); // Use same name for all files
                uploadFormData.append('sensor', uploadData.sensor);
                uploadFormData.append('convert', uploadData.convert);
                uploadFormData.append('is_public', uploadData.is_public);
                uploadFormData.append('expected_files', expectedFilesJson);
                
                // Folder is ONLY for UI organization (metadata from dropdown), NOT for file system structure
                // For directory uploads, directory structure is preserved via the relative path mechanism
                // which is handled separately by the backend
                if (uploadData.folder) {
                    // Only use folder from dropdown - this is metadata for UI organization only
                    uploadFormData.append('folder', uploadData.folder);
                    console.log(`File ${i + 1}: Using folder for UI organization: ${uploadData.folder}`);
                }
                
                // For directory uploads, preserve structure by including relative path in a separate parameter
                // Note: This is separate from 'folder' which is only for UI organization
                if (isDirectoryUpload && relativePath) {
                    // The backend will use this to preserve directory structure in the file system
                    // This is different from 'folder' which is metadata only
                    uploadFormData.append('relative_path', relativePath);
                    console.log(`File ${i + 1}: Directory upload - preserving structure with relative path: ${relativePath}`);
                }
                
                if (uploadData.team_uuid) uploadFormData.append('team_uuid', uploadData.team_uuid);
                if (uploadData.tags) uploadFormData.append('tags', uploadData.tags);
                
                // Group files under the same dataset UUID
                // For directory uploads, use the same dataset_identifier for all files
                // The backend will use the identifier as the UUID directly (without add_to_existing)
                // This avoids race conditions where the dataset doesn't exist yet
                uploadFormData.append('dataset_identifier', datasetUuid);
                // Don't use add_to_existing for directory uploads - the backend handles it automatically
                // when dataset_identifier is provided without add_to_existing

                // Build upload URL
                const uploadUrl = `${getUploadApiBasePath()}/upload-dataset.php`;
                console.log(`Uploading file ${i + 1}/${files.length} to: ${uploadUrl}`);
                console.log(`  Using dataset UUID: ${datasetUuid}`);
                
                // Track file upload with index
                const fileIndex = i;
                const fileName = file.name;
                
                // The browser starts sending bytes as soon as fetch begins. Apache/PHP
                // logs often appear only after the full request body is received.
                this.updateUploadModalFile(fileIndex, fileName, 'uploading');
                
                uploadPromises.push(
                    fetch(uploadUrl, {
                        method: 'POST',
                        body: uploadFormData,
                        // Add timeout: 5 minutes for small files, up to 10 minutes for larger files
                        signal: AbortSignal.timeout(Math.min(600000, 300000 + (file.size / 1024 / 1024) * 1000)) // 5-10 min based on file size
                    }).then(async response => {
                        const text = await response.text();
                        
                        // Log response for debugging
                        console.log('Upload response status:', response.status);
                        console.log('Upload response preview:', text.substring(0, 200));
                        
                        // Check if response is empty
                        if (!text || text.trim().length === 0) {
                            throw new Error('Empty response from server');
                        }
                        
                        // Try to parse JSON
                        try {
                            // Remove any leading/trailing whitespace
                            const cleanedText = text.trim();
                            
                            // Check if it looks like JSON
                            if (cleanedText[0] !== '{' && cleanedText[0] !== '[') {
                                console.error('Response does not start with JSON:', cleanedText.substring(0, 200));
                                throw new Error('Response is not valid JSON. Server may have returned an error page.');
                            }
                            
                            const result = JSON.parse(cleanedText);

                            if (!response.ok) {
                                const errorMsg = result.error || result.message || `Upload rejected by server (HTTP ${response.status})`;
                                this.updateUploadModalFile(fileIndex, fileName, 'failed', null, errorMsg);
                                const uploadError = new Error(errorMsg);
                                uploadError.nonRetryable = response.status >= 400 && response.status < 500 && response.status !== 408 && response.status !== 429;
                                throw uploadError;
                            }
                            
                            // Check if upload was successful
                            if (result.job_id && response.status === 200) {
                                // Mark file as completed
                                this.updateUploadModalFile(fileIndex, fileName, 'completed', result.job_id);
                                return result;
                            } else {
                                // Mark file as failed
                                const errorMsg = result.error || result.message || 'Upload failed';
                                this.updateUploadModalFile(fileIndex, fileName, 'failed', null, errorMsg);
                                return result;
                            }
                        } catch (e) {
                            console.error('JSON parse error:', e);
                            console.error('Full response:', text);
                            const errorMsg = 'Invalid JSON response: ' + e.message;
                            this.updateUploadModalFile(fileIndex, fileName, 'failed', null, errorMsg);
                            throw new Error(errorMsg + '. Response preview: ' + text.substring(0, 200));
                        }
                    }).catch(error => {
                        console.error('Upload fetch error:', error);
                        // Mark file as failed
                        let errorMsg = error.message || 'Network error';
                        
                        // Handle specific error types
                        if (error.name === 'AbortError' || error.name === 'TimeoutError') {
                            errorMsg = 'Upload timeout - the server took too long to respond. The upload may still be processing in the background.';
                        } else if (error.message && error.message.includes('Failed to fetch')) {
                            errorMsg = 'Connection failed - unable to reach the upload server. Please check your connection and try again.';
                        }
                        
                        this.updateUploadModalFile(fileIndex, fileName, 'failed', null, errorMsg);
                        throw error;
                    })
                );
            }

            // Wait for all uploads to complete (or fail)
            const results = await Promise.allSettled(uploadPromises);
            
            // Debug: Log all results to understand what we're getting
            console.log(`Upload results: ${results.length} total`);
            results.forEach((result, index) => {
                if (result.status === 'fulfilled') {
                    console.log(`Result ${index + 1}:`, {
                        hasValue: !!result.value,
                        hasJobId: !!(result.value && result.value.job_id),
                        jobId: result.value?.job_id,
                        keys: result.value ? Object.keys(result.value) : [],
                        fullResult: result.value
                    });
                } else {
                    console.error(`Result ${index + 1} rejected:`, result.reason);
                }
            });
            
            const successful = results.filter(r => r.status === 'fulfilled' && r.value && r.value.job_id).map(r => r.value);
            
            // Map failed results back to their file indices
            const failedFiles = [];
            results.forEach((result, index) => {
                if (result.status === 'rejected' || !result.value || !result.value.job_id) {
                    // Log why it's being marked as failed
                    if (result.status === 'fulfilled' && result.value && !result.value.job_id) {
                        console.warn(`Upload ${index + 1} succeeded but missing job_id:`, result.value);
                    }
                    failedFiles.push({
                        fileIndex: index,
                        file: files[index],
                        error: result.status === 'rejected' ? result.reason?.message : 'Upload failed',
                        nonRetryable: result.status === 'rejected' ? !!result.reason?.nonRetryable : false,
                        result: result.value
                    });
                }
            });

            // Track successful uploads with file names
            console.log(`Tracking ${successful.length} successful upload(s) in activeUploads`);
            successful.forEach((result, idx) => {
                // Find the file name for this result by matching job_id in the upload session
                let fileName = uploadData.dataset_name; // fallback to dataset name
                const fileInfo = this.currentUploadSession?.files.find(f => f.jobId === result.job_id);
                if (fileInfo) {
                    fileName = fileInfo.name;
                } else if (files[idx]) {
                    // Fallback: use file from array if we can match by index
                    fileName = files[idx].name;
                }
                console.log(`Adding to activeUploads: job_id=${result.job_id}, file=${fileName}, dataset=${uploadData.dataset_name}`);
                this.trackUpload(result.job_id, uploadData.dataset_name, fileName, uploadData.convert, datasetUuid);
                // Note: trackUpload() already calls pollUploadProgress() automatically
            });
            
            // Refresh dataset list immediately to show new upload
            if (window.datasetManager && successful.length > 0) {
                setTimeout(() => {
                    window.datasetManager.loadDatasets();
                    console.log('✅ Dataset list refreshed after upload');
                }, 1000); // Small delay to ensure MongoDB entry is visible
            }
            
            // Log if any uploads were successful but not tracked
            if (successful.length < results.filter(r => r.status === 'fulfilled').length) {
                const untracked = results.filter(r => 
                    r.status === 'fulfilled' && 
                    r.value && 
                    !r.value.job_id
                );
                if (untracked.length > 0) {
                    console.warn(`⚠️ ${untracked.length} upload(s) succeeded but are missing job_id and won't be tracked in Active Uploads`);
                }
            }

            // Update status message - uploads are queued
            if (this.currentUploadSession) {
                const statusText = document.getElementById('uploadModalStatusText');
                if (statusText) {
                    if (successful.length > 0) {
                        statusText.textContent = `✅ ${successful.length} file(s) reached the server. You can navigate away after all selected files are listed as completed.`;
                        document.getElementById('uploadModalStatusMessage').className = 'flex-grow-1 text-success small';
                    }
                }
            }

            // Retry failed uploads automatically (in background)
            if (failedFiles.length > 0) {
                const retryableFailedFiles = failedFiles.filter(file => !file.nonRetryable);
                if (retryableFailedFiles.length === 0) {
                    this.localBrowserUploadInProgress = false;
                    const statusText = document.getElementById('uploadModalStatusText');
                    if (statusText) {
                        statusText.textContent = 'Upload was rejected by the server. Check the error above and try again after fixing it.';
                        document.getElementById('uploadModalStatusMessage').className = 'flex-grow-1 text-danger small';
                    }
                } else {
                // Don't await - let retries happen in background
                this.retryFailedUploads(retryableFailedFiles, uploadData, userEmail, datasetUuid, isDirectoryUpload, baseDirectoryName)
                    .finally(() => {
                        this.localBrowserUploadInProgress = false;
                    })
                    .catch(error => {
                        console.error('Error during retry process:', error);
                    });
                }
            } else {
                this.localBrowserUploadInProgress = false;
            }

            // Reset button after browser-to-server upload requests have settled.
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;

            // Don't close upload interface automatically - let user see the modal
            // The modal will show all results and allow user to close when ready
            // Refresh dataset list if any uploads succeeded
            if (successful.length > 0 && window.datasetManager) {
                window.datasetManager.loadDatasets();
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            this.localBrowserUploadInProgress = false;
            alert('Error uploading file: ' + error.message);
            
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-upload"></i> Upload';
            }
        }
    }

    /**
     * Handle Google Drive upload
     */
    async handleGoogleDriveUpload(form) {
        const formData = new FormData(form);
        const userEmail = await this.getUserEmail();
        
        if (!userEmail) {
            alert('User not authenticated');
            return;
        }

        // Get either drive_id (Google Drive ID) or folder_link
        const inputType = document.getElementById('googleDriveInputType')?.value || 'drive_id';
        const driveId = formData.get('drive_id');
        const folderLink = formData.get('folder_link');
        
        if (!driveId && !folderLink) {
            alert('Google Drive ID or Folder Link is required');
            return;
        }

        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initiating...';

            // Build source_config for OAuth-based upload
            const sourceConfig = {
                use_oauth: true  // Use OAuth tokens from MongoDB
            };
            
            if (folderLink) {
                sourceConfig.folder_link = folderLink;
            } else if (driveId) {
                // Backend expects 'file_id' parameter (works for both files and folders)
                sourceConfig.file_id = driveId;
            }

            // Use SCLib Upload API initiate endpoint for Google Drive (OAuth-based)
            const requestData = {
                source_type: 'google_drive',
                source_config: sourceConfig,
                user_email: userEmail,
                dataset_name: formData.get('name'),
                sensor: formData.get('sensor'),
                convert: formData.get('convert') === 'on',
                is_public: formData.get('is_public') === 'on',
                folder: this.getFolderValue(form),
                team_uuid: formData.get('team_uuid') || null,
                preferred_dashboard: formData.get('preferred_dashboard') || null,
                dimensions: formData.get('dimensions') || null
            };

            console.log('Initiating OAuth-based Google Drive upload:', {
                user_email: userEmail,
                has_drive_id: !!driveId,
                has_folder_link: !!folderLink,
                dataset_name: requestData.dataset_name
            });

            const response = await fetch(`${getUploadApiBasePath()}/upload-initiate.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
                throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            
            console.log('Upload initiate response:', data);

            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;

            // Check for job_id in various possible locations
            const jobId = data.job_id || data.jobId || data.id;
            
            if (jobId) {
                console.log(`✅ Using job_id from response: ${jobId}`);
                // Use dataset name instead of generic "Google Drive Folder"
                // If dataset name is not available, fall back to generic name
                const fileName = requestData.dataset_name || (folderLink ? 'Google Drive Folder' : (driveId || 'Google Drive File/Folder'));
                this.trackUpload(jobId, requestData.dataset_name, fileName, requestData.convert);
                
                const uploadType = folderLink ? 'folder' : 'file/folder';
                alert(`Google Drive ${uploadType} upload started! Job ID: ${jobId}\nYou can continue using the app. Check the progress widget.`);
                this.closeUploadInterface();
            } else {
                console.error('❌ No job_id in response:', data);
                throw new Error(data.error || data.detail || 'Upload failed - no job_id returned');
            }
        } catch (error) {
            console.error('Error initiating Google Drive upload:', error);
            alert('Error initiating Google Drive upload: ' + error.message);
            
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-upload"></i> Upload from Google Drive';
            }
        }
    }

    /**
     * Handle S3 upload
     */
    async handleS3Upload(form) {
        const formData = new FormData(form);
        const userEmail = await this.getUserEmail();
        
        if (!userEmail) {
            alert('User not authenticated');
            return;
        }

        const s3Source = this.resolveS3Source(formData);
        if (s3Source.error) {
            alert(s3Source.error);
            return;
        }
        const bucket = s3Source.bucket;
        const prefix = s3Source.prefix || '';
        const endpointUrl = s3Source.endpointUrl || '';
        const accessKey = formData.get('access_key');
        const secretKey = formData.get('secret_key');
        const region = (formData.get('region') || 'us-east-1').toString().trim() || 'us-east-1';
        const pathStyle = formData.get('path_style') === 'on';

        if (!bucket) {
            alert('Bucket is required');
            return;
        }
        if (!accessKey || !secretKey) {
            alert('Access key and secret key are required for S3 upload.');
            return;
        }

        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initiating...';

            const sensorUpper = String(formData.get('sensor') || '').trim().toUpperCase();
            const dims = (formData.get('dimensions') || '').toString().trim();
            const tags = (formData.get('tags') || '').toString().trim();
            const preferredPick =
                (formData.get('preferred_dashboard') || '').toString().trim() ||
                (sensorUpper === 'IDX' ? 'DarkMatter' : 'OpenVisusSlice');

            // Use SCLib Upload API initiate endpoint for S3
            const requestData = {
                source_type: 's3',
                source_config: {
                    endpoint_url: endpointUrl,
                    bucket_name: bucket,
                    object_key: prefix,
                    access_key_id: accessKey,
                    secret_access_key: secretKey,
                    region_name: region,
                    path_style: pathStyle,
                    original_link: s3Source.rawLink || ''
                },
                user_email: userEmail,
                dataset_name: formData.get('name'),
                sensor: formData.get('sensor'),
                convert: formData.get('convert') === 'on',
                is_public: formData.get('is_public') === 'on',
                is_downloadable: formData.get('is_downloadable') || 'only owner',
                folder: this.getFolderValue(form),
                team_uuid: formData.get('team_uuid') || null,
                preferred_dashboard: preferredPick,
                dimensions: dims || null,
                tags: tags || undefined
            };
            if (!requestData.tags) {
                delete requestData.tags;
            }
            if (!requestData.dimensions) {
                delete requestData.dimensions;
            }

            const response = await fetch(`${getUploadApiBasePath()}/upload-initiate.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;

            if (data.job_id) {
                this.trackUpload(data.job_id, requestData.dataset_name, null, requestData.convert);
                alert(`S3 upload started! Job ID: ${data.job_id}\nYou can continue using the app. Check the progress widget.`);
                this.closeUploadInterface();
            } else {
                throw new Error(data.error || data.detail || 'Upload failed');
            }
        } catch (error) {
            console.error('Error initiating S3 upload:', error);
            alert('Error initiating S3 upload: ' + error.message);
            
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-plug"></i> Connect to Data Portal';
            }
        }
    }

    /**
     * Test S3 credentials + endpoint before enqueueing an upload job.
     */
    async testS3UploadConnection(form) {
        const formData = new FormData(form);
        const resultEl = document.getElementById('s3TestConnectionResult');
        const btn = document.getElementById('s3TestConnectionBtn');

        const s3Source = this.resolveS3Source(formData);
        if (s3Source.error) {
            if (resultEl) {
                resultEl.textContent = s3Source.error;
                resultEl.className = 'small text-danger';
            } else {
                alert(s3Source.error);
            }
            return;
        }
        const endpointUrl = (s3Source.endpointUrl || '').toString().trim();
        const bucket = (s3Source.bucket || '').toString().trim();
        const prefix = (s3Source.prefix || '').toString();
        const accessKey = (formData.get('access_key') || '').toString().trim();
        const secretKey = (formData.get('secret_key') || '').toString();
        const region = (formData.get('region') || 'us-east-1').toString().trim() || 'us-east-1';
        const pathStyle = formData.get('path_style') === 'on';

        if (!endpointUrl || !bucket || !accessKey || !secretKey) {
            if (resultEl) {
                resultEl.textContent = 'Test requires endpoint + bucket + access key + secret key.';
                resultEl.className = 'small text-danger';
            } else {
                alert('Test requires endpoint + bucket + access key + secret key.');
            }
            return;
        }

        const original = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        }
        if (resultEl) {
            resultEl.textContent = '';
            resultEl.className = 'small text-muted';
        }

        try {
            const response = await fetch(`${getUploadApiBasePath()}/s3-test-connection.php`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    endpoint_url: endpointUrl,
                    bucket_name: bucket,
                    prefix,
                    access_key: accessKey,
                    secret_key: secretKey,
                    region,
                    path_style: pathStyle
                })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || !data.ok) {
                const msg = data.error || data.detail || `HTTP ${response.status}`;
                throw new Error(msg);
            }
            const extra = typeof data.folders === 'number'
                ? ` (${data.folders} folders, ${data.files} files at this level${data.has_more ? ', more available' : ''})`
                : '';
            if (resultEl) {
                resultEl.textContent = (data.message || 'Connection OK.') + extra;
                resultEl.className = 'small text-success';
            } else {
                alert((data.message || 'Connection OK.') + extra);
            }
        } catch (err) {
            const msg = err && err.message ? err.message : 'Test failed';
            if (resultEl) {
                resultEl.textContent = msg;
                resultEl.className = 'small text-danger';
            } else {
                alert(msg);
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = original || '<i class="fas fa-plug"></i> Test S3 connection';
            }
        }
    }

    /**
     * Handle remote server upload
     */
    async handleRemoteUpload(form) {
        const formData = new FormData(form);
        const userEmail = await this.getUserEmail();
        
        if (!userEmail) {
            alert('User not authenticated');
            return;
        }

        const serverLink = formData.get('server_link');
        if (!serverLink) {
            alert('Server Link is required');
            return;
        }

        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Linking...';

            const sensorUpper = String(formData.get('sensor') || '').trim().toUpperCase();
            const dims = (formData.get('dimensions') || '').toString().trim();
            const tags = (formData.get('tags') || '').toString().trim();
            const preferredPick =
                (formData.get('preferred_dashboard') || '').toString().trim() ||
                (sensorUpper === 'IDX' ? 'DarkMatter' : 'OpenVisusSlice');

            // Use SCLib Upload API initiate endpoint for URL/remote server
            const requestData = {
                source_type: 'url',
                source_config: {
                    url: serverLink
                },
                user_email: userEmail,
                dataset_name: formData.get('name'),
                sensor: formData.get('sensor'),
                convert: false, // Remote server links typically don't need conversion
                is_public: formData.get('is_public') === 'on',
                is_downloadable: formData.get('is_downloadable') || 'only owner',
                folder: this.getFolderValue(form),
                team_uuid: formData.get('team_uuid') || null,
                preferred_dashboard: preferredPick,
                dimensions: dims || null,
                tags: tags || undefined
            };
            if (!requestData.tags) {
                delete requestData.tags;
            }
            if (!requestData.dimensions) {
                delete requestData.dimensions;
            }

            const response = await fetch(`${getUploadApiBasePath()}/upload-initiate.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;

            if (data.job_id) {
                this.trackUpload(data.job_id, requestData.dataset_name, null, requestData.convert);
                alert(`Remote server link created! Job ID: ${data.job_id}\nYou can continue using the app. Check the progress widget.`);
                this.closeUploadInterface();
            } else {
                throw new Error(data.error || data.detail || 'Link creation failed');
            }
        } catch (error) {
            console.error('Error creating remote server link:', error);
            alert('Error creating remote server link: ' + error.message);
            
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-link"></i> Link Remote Server Data';
            }
        }
    }

    /**
     * Get user email from session
     */
    async getUserEmail() {
        // Try to get from a user info endpoint or session
        try {
            const response = await fetch(`${getApiBasePath()}/user-info.php`);
            const data = await response.json();
            return data.email || null;
        } catch (error) {
            console.warn('Could not get user email:', error);
            return null;
        }
    }

    /**
     * Restore active uploads from server (called on page load)
     * This ensures uploads continue to be tracked even after page refresh
     */
    async restoreActiveUploads() {
        try {
            console.log('🔄 Restoring active uploads from server...');
            
            // Get active jobs from the server
            // Note: jobs.php accepts status as query param, but we need to get all active statuses
            // We'll filter client-side since the API may not support multiple status values
            const response = await fetch(`${getApiBasePath()}/jobs.php?limit=100`);
            if (!response.ok) {
                console.warn('⚠️ Could not fetch active jobs:', response.status);
                return;
            }
            
            const data = await response.json();
            if (!data.success || !data.jobs) {
                console.warn('⚠️ No active jobs found or API error');
                return;
            }
            
            // Filter for upload jobs (not conversion jobs) that are still active
            const activeStatuses = ['queued', 'uploading', 'processing', 'initializing', 'pending', 'running'];
            const uploadJobs = data.jobs.filter(job => {
                const jobType = job.job_type || '';
                const status = (job.status || 'unknown').toLowerCase();
                
                // Must be an upload job (not conversion)
                const isUploadJob = jobType.includes('upload') || jobType === 'upload' || 
                                   (!jobType.includes('conversion') && !jobType.includes('dataset_conversion'));
                
                // Must be in an active status
                const isActive = activeStatuses.some(activeStatus => status.includes(activeStatus));
                
                return isUploadJob && isActive;
            });
            
            console.log(`📥 Found ${uploadJobs.length} active upload job(s) to restore`);
            
            // Restore each upload job
            for (const job of uploadJobs) {
                const jobId = job.job_id || job.id;
                if (!jobId) {
                    console.warn('⚠️ Job missing job_id:', job);
                    continue;
                }
                
                const status = job.status || 'unknown';
                
                // Get dataset name from job or use default
                const datasetName = job.dataset_name || job.name || 'Unknown Dataset';
                const fileName = job.file_name || datasetName;
                
                // Track the upload (will start polling)
                this.trackUpload(
                    jobId,
                    datasetName,
                    fileName,
                    false, // We don't know if conversion was requested from job data
                    job.dataset_uuid || job.datasetUuid || job.uuid || null
                );
                
                // Update with current status and progress from server
                const upload = this.activeUploads.get(jobId);
                if (upload) {
                    upload.status = status;
                    upload.progress = job.progress_percentage || 0;
                    upload.message = job.message || job.error || null;
                }
            }
            
            // Update widget to show restored uploads
            this.updateProgressWidget();
            
            console.log(`✅ Restored ${this.activeUploads.size} active upload(s)`);
        } catch (error) {
            console.error('❌ Error restoring active uploads:', error);
        }
    }

    /**
     * Track upload progress
     * @param {string} jobId - The job ID from the upload API
     * @param {string} datasetName - The dataset name
     * @param {string} fileName - The individual file name (optional, defaults to dataset name)
     * @param {boolean} willConvert - Whether conversion was requested (optional)
     */
    trackUpload(jobId, datasetName, fileName = null, willConvert = false, datasetUuid = null) {
        // Don't duplicate if already tracking
        if (this.activeUploads.has(jobId)) {
            console.log(`ℹ️ Already tracking upload: ${jobId}`);
            return;
        }
        
        this.activeUploads.set(jobId, {
            job_id: jobId,
            dataset_name: datasetName,
            dataset_uuid: datasetUuid || null,
            file_name: fileName || datasetName, // Use file name if provided, otherwise dataset name
            will_convert: willConvert,
            status: 'queued',
            progress: 0
        });

        // Start polling for progress
        this.pollUploadProgress(jobId);
        
        // Update progress widget
        this.updateProgressWidget();
    }

    /**
     * Poll upload progress
     */
    async pollUploadProgress(jobId) {
        const maxAttempts = 2400; // Allows multi-hour jobs with adaptive backoff
        let attempts = 0;
        let delayMs = 1000;
        const maxDelayMs = 30000;

        const poll = async () => {
            if (attempts >= maxAttempts) {
                return;
            }

            try {
                // Use PHP proxy for status polling
                const response = await fetch(`${getApiBasePath()}/upload-status.php?job_id=${encodeURIComponent(jobId)}`);
                if (!response.ok) {
                    // If 404, the job might not exist yet or job_id is wrong
                    if (response.status === 404) {
                        console.warn(`⚠️ Job ${jobId} not found (404). It may not have been created yet or job_id is incorrect.`);
                        // Continue polling - job might be created shortly
                        attempts++;
                        delayMs = Math.min(maxDelayMs, Math.floor(delayMs * 1.25));
                        setTimeout(poll, delayMs);
                        return;
                    }
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const data = await response.json();

                if (data.job_id) {
                    const upload = this.activeUploads.get(jobId);
                    if (upload) {
                        upload.status = data.canonical_state || data.status;
                        upload.progress = data.progress_percentage || 0;
                        upload.message = data.message;
                        if (!upload.dataset_uuid && data.dataset_uuid) {
                            upload.dataset_uuid = data.dataset_uuid;
                        }
                        
                        this.updateProgressWidget();

                        // Continue polling only while status is active/in-progress.
                        const status = String(data.canonical_state || data.status || '').toLowerCase();
                        const terminalStatuses = new Set(['ready', 'uploaded', 'completed', 'done', 'failed', 'error', 'cancelled', 'canceled']);
                        if (!terminalStatuses.has(status)) {
                            // Back off for long-running uploads/conversions to reduce API load.
                            delayMs = Math.min(maxDelayMs, Math.floor(delayMs * 1.2));
                            setTimeout(poll, delayMs);
                        } else {
                            // Upload finished
                            if (['ready', 'uploaded', 'completed', 'done'].includes(status)) {
                                upload.progress = 100;
                                upload.status = status === 'uploaded' ? 'completed' : status;
                                this.markCurrentSessionJobComplete(jobId);
                                // Update widget to show completion message
                                this.updateProgressWidget();
                                
                                // Refresh dataset list
                                if (window.datasetManager) {
                                    window.datasetManager.loadDatasets();
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('Error polling upload progress:', error);
                delayMs = Math.min(maxDelayMs, Math.floor(delayMs * 1.3));
                setTimeout(poll, delayMs);
                attempts++;
                return;
            }

            attempts++;
        };

        poll();
    }

    markCurrentSessionJobComplete(jobId) {
        if (!this.currentUploadSession || !jobId) return;
        const fileInfo = this.currentUploadSession.files.find(file => file.jobId === jobId);
        if (!fileInfo || fileInfo.status === 'completed') return;
        this.updateUploadModalFile(fileInfo.index, fileInfo.name, 'completed', jobId);
        if (this.currentUploadSession.completedFiles + this.currentUploadSession.failedFiles >= this.currentUploadSession.totalFiles) {
            this.localBrowserUploadInProgress = false;
        }
    }

    /**
     * Create progress widget
     */
    createProgressWidget() {
        // Create a floating progress widget
        const widget = document.createElement('div');
        widget.id = 'uploadProgressWidget';
        widget.className = 'upload-progress-widget';
        widget.innerHTML = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-upload"></i> Active Uploads
                        <button type="button" class="btn btn-sm btn-outline-light float-end" 
                                onclick="uploadManager.toggleProgressWidget()">
                            <i class="fas fa-chevron-down"></i>
                        </button>
                    </h6>
                </div>
                <div class="card-body" id="uploadProgressList">
                    <p class="text-muted small">No active uploads</p>
                </div>
            </div>
        `;
        
        document.body.appendChild(widget);
        this.progressWidget = widget;
    }

    /**
     * Update progress widget
     */
    updateProgressWidget() {
        const progressList = document.getElementById('uploadProgressList');
        if (!progressList) {
            console.warn('⚠️ uploadProgressList element not found - widget may not be initialized');
            return;
        }

        const renderItems = [];

        // 1) Tracked jobs (have job_id and polling status)
        this.activeUploads.forEach((upload, jobId) => {
            renderItems.push({
                key: `job:${jobId}`,
                job_id: jobId,
                dataset_name: upload.dataset_name,
                dataset_uuid: upload.dataset_uuid || null,
                file_name: upload.file_name || upload.dataset_name,
                will_convert: !!upload.will_convert,
                status: upload.status || 'queued',
                progress: Number(upload.progress || 0),
                message: upload.message || ''
            });
        });

        // 2) Current modal session files (queued/uploading rows often appear here first)
        // Include them so closing the modal does not make file list "disappear".
        if (this.currentUploadSession && Array.isArray(this.currentUploadSession.files)) {
            const sessionDataset = this.currentUploadSession.datasetName || 'Current upload';
            const sessionWillConvert = !!this.currentUploadSession.willConvert;
            const sessionDatasetUuid = this.currentUploadSession.datasetUuid || null;
            this.currentUploadSession.files.forEach((file, idx) => {
                const jobId = file.jobId || '';
                // If we already track this job in activeUploads, avoid duplicate row.
                if (jobId && this.activeUploads.has(jobId)) return;

                const fileStatus = String(file.status || 'queued').toLowerCase();
                let inferredProgress = 0;
                if (fileStatus === 'completed' || fileStatus === 'done' || fileStatus === 'ready') {
                    inferredProgress = 100;
                } else if (fileStatus === 'uploading' || fileStatus === 'processing' || fileStatus === 'retrying') {
                    inferredProgress = 50;
                }

                renderItems.push({
                    key: `session:${idx}:${file.name || 'file'}`,
                    job_id: jobId || null,
                    dataset_name: sessionDataset,
                    dataset_uuid: sessionDatasetUuid,
                    file_name: file.name || sessionDataset,
                    will_convert: sessionWillConvert,
                    status: fileStatus || 'queued',
                    progress: inferredProgress,
                    message: file.error || ''
                });
            });
        }

        console.log(`🔄 updateProgressWidget called: ${renderItems.length} render item(s), ${this.activeUploads.size} tracked job(s)`);

        if (renderItems.length === 0) {
            progressList.innerHTML = '<p class="text-muted small">No active uploads</p>';
            return;
        }

        let html = '';
        renderItems.forEach((upload) => {
            console.log(`  Rendering upload: key=${upload.key}, file=${upload.file_name}, dataset=${upload.dataset_name}, status=${upload.status}, progress=${upload.progress}`);
            const rawStatus = String(upload.status || '').toLowerCase();
            const isUploadComplete = rawStatus === 'completed' || rawStatus === 'done' || rawStatus === 'ready';
            const conversionInProgress = !!upload.will_convert && isUploadComplete;

            // "completed" previously looked like the whole pipeline was done.
            // For IDX flows, upload completion is only phase 1; conversion follows.
            const displayStatus = conversionInProgress ? 'uploaded' : (upload.status || 'queued');
            const statusColor = conversionInProgress ? 'info' :
                              rawStatus === 'completed' || rawStatus === 'done' || rawStatus === 'ready' ? 'success' :
                              rawStatus === 'failed' || rawStatus === 'error' ? 'danger' : 'primary';
            
            // Show file name (preferred) or dataset name as fallback
            const displayName = upload.file_name || upload.dataset_name;
            
            // Add completion message if upload is done
            let completionMessage = '';
            if (isUploadComplete) {
                if (upload.will_convert) {
                    completionMessage = '<small class="text-info d-block mt-1"><i class="fas fa-sync-alt"></i> Upload complete. Conversion in progress...</small>';
                } else {
                    completionMessage = '<small class="text-success d-block mt-1"><i class="fas fa-check-circle"></i> Ready to view</small>';
                }
            }
            
            html += `
                <div class="upload-progress-item mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="small" title="${this.escapeHtml(upload.dataset_name)}">${this.escapeHtml(displayName)}</span>
                        <span class="badge bg-${statusColor}">${this.escapeHtml(displayStatus)}</span>
                    </div>
                    ${upload.dataset_uuid ? `<small class="text-muted d-block">Dataset UUID: ${this.escapeHtml(upload.dataset_uuid)}</small>` : ''}
                    ${upload.job_id ? `<small class="text-muted d-block">Job ID: ${this.escapeHtml(upload.job_id)}</small>` : ''}
                    <div class="progress mt-1" style="height: 5px;">
                        <div class="progress-bar bg-${statusColor}" 
                             role="progressbar" 
                             style="width: ${upload.progress}%"
                             aria-valuenow="${upload.progress}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                        </div>
                    </div>
                    ${upload.message ? `<small class="text-muted">${this.escapeHtml(upload.message)}</small>` : ''}
                    ${completionMessage}
                </div>
            `;
        });

        progressList.innerHTML = html;
        console.log(`✅ Progress widget updated with ${renderItems.length} item(s)`);
    }

    /**
     * Toggle progress widget visibility
     */
    toggleProgressWidget() {
        if (this.progressWidget) {
            const body = this.progressWidget.querySelector('.card-body');
            if (body) {
                body.style.display = body.style.display === 'none' ? 'block' : 'none';
            }
        }
    }

    /**
     * Create upload progress modal
     */
    createUploadModal() {
        const modal = document.createElement('div');
        modal.id = 'uploadProgressModal';
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-labelledby', 'uploadProgressModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        modal.innerHTML = `
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title" id="uploadProgressModalLabel">
                            <i class="fas fa-upload"></i> Upload Progress
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span><strong>Dataset:</strong> <span id="uploadModalDatasetName">-</span></span>
                                <span class="badge bg-info" id="uploadModalOverallStatus">Initializing...</span>
                            </div>
                            <div class="progress" style="height: 25px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" 
                                     id="uploadModalOverallProgress"
                                     style="width: 0%"
                                     aria-valuenow="0" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100">
                                    <span id="uploadModalProgressText">0%</span>
                                </div>
                            </div>
                            <div class="mt-2 small text-muted">
                                <span id="uploadModalFileCount">0</span> of <span id="uploadModalTotalFiles">0</span> files completed
                            </div>
                        </div>
                        <hr>
                        <div class="upload-file-list" id="uploadModalFileList" style="max-height: 400px; overflow-y: auto;">
                            <p class="text-muted text-center">No files uploaded yet...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <div class="flex-grow-1 text-muted small" id="uploadModalStatusMessage">
                            <i class="fas fa-info-circle"></i> <span id="uploadModalStatusText">Keep this browser tab open until all selected files finish sending to the server.</span>
                        </div>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="uploadModalCloseBtn">
                            Close
                        </button>
                        <button type="button" class="btn btn-primary" onclick="uploadManager.closeUploadInterface()" id="uploadModalViewJobsBtn" style="display: none;">
                            View Jobs
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        this.uploadModal = new bootstrap.Modal(modal);
    }

    /**
     * Show upload progress modal
     */
    showUploadModal(datasetName, totalFiles) {
        if (!this.uploadModal) {
            this.createUploadModal();
        }

        // Initialize session data
        this.currentUploadSession = {
            datasetName: datasetName,
            totalFiles: totalFiles,
            completedFiles: 0,
            failedFiles: 0,
            files: [],
            maxRetries: 5,
            retryDelay: 2000, // 2 seconds between retries
            willConvert: false // Will be set when upload starts
        };

        // Update modal content
        document.getElementById('uploadModalDatasetName').textContent = datasetName;
        document.getElementById('uploadModalTotalFiles').textContent = totalFiles;
        document.getElementById('uploadModalFileCount').textContent = '0';
        document.getElementById('uploadModalOverallProgress').style.width = '0%';
        document.getElementById('uploadModalProgressText').textContent = '0%';
        document.getElementById('uploadModalOverallStatus').textContent = 'Initializing...';
        document.getElementById('uploadModalOverallStatus').className = 'badge bg-info';
        document.getElementById('uploadModalFileList').innerHTML = '<p class="text-muted text-center">Preparing uploads...</p>';
        document.getElementById('uploadModalCloseBtn').disabled = false; // Closing the dialog is ok; leaving the page is not.
        document.getElementById('uploadModalViewJobsBtn').style.display = 'none';
        document.getElementById('uploadModalStatusText').textContent = 'Preparing uploads... Keep this page open until every selected file is completed.';
        document.getElementById('uploadModalStatusMessage').className = 'flex-grow-1 text-warning small';

        // Show modal
        this.uploadModal.show();
    }

    /**
     * Update upload modal with file progress
     */
    updateUploadModalFile(fileIndex, fileName, status, jobId = null, error = null, retryCount = 0) {
        if (!this.currentUploadSession) return;

        const fileInfo = {
            index: fileIndex,
            name: fileName,
            status: status, // 'queued', 'uploading', 'completed', 'failed', 'retrying'
            jobId: jobId,
            error: error,
            retryCount: retryCount
        };

        // Find existing file info before updating
        const existingIndex = this.currentUploadSession.files.findIndex(f => f.index === fileIndex);
        const existingFile = existingIndex >= 0 ? this.currentUploadSession.files[existingIndex] : null;

        // Update counts (decrement old status if it was completed/failed)
        if (existingFile) {
            if (existingFile.status === 'completed') {
                this.currentUploadSession.completedFiles--;
            } else if (existingFile.status === 'failed') {
                // Only decrement if moving away from failed state
                if (status !== 'failed') {
                    this.currentUploadSession.failedFiles--;
                }
            }
            // Preserve retry count if not explicitly set
            if (retryCount === 0 && existingFile.retryCount) {
                fileInfo.retryCount = existingFile.retryCount;
            }
        }
        
        // Update or add file info
        if (existingIndex >= 0) {
            this.currentUploadSession.files[existingIndex] = fileInfo;
        } else {
            this.currentUploadSession.files.push(fileInfo);
        }
        
        // Increment new status count (only for final states)
        if (status === 'completed') {
            this.currentUploadSession.completedFiles++;
        } else if (status === 'failed') {
            this.currentUploadSession.failedFiles++;
        }
        // Note: 'retrying' and 'uploading' are intermediate states, not counted separately

        // Update modal display
        this.renderUploadModal();
        // Keep the lower-right widget in sync immediately, even when modal is closed.
        this.updateProgressWidget();
    }

    /**
     * Render upload modal content
     */
    renderUploadModal() {
        if (!this.currentUploadSession) return;

        const session = this.currentUploadSession;
        const total = session.totalFiles;
        const completed = session.completedFiles;
        const failed = session.failedFiles;
        const inProgress = session.files.filter(f => f.status === 'uploading' || f.status === 'queued' || f.status === 'retrying').length;
        
        // Calculate overall progress
        const progress = total > 0 ? Math.round(((completed + failed) / total) * 100) : 0;
        
        // Update overall progress bar
        const progressBar = document.getElementById('uploadModalOverallProgress');
        const progressText = document.getElementById('uploadModalProgressText');
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        progressText.textContent = `${progress}%`;

        // Update file count
        document.getElementById('uploadModalFileCount').textContent = completed + failed;

        // Update status badge
        const statusBadge = document.getElementById('uploadModalOverallStatus');
        if (failed === total && total > 0) {
            statusBadge.textContent = 'All Failed';
            statusBadge.className = 'badge bg-danger';
        } else if (completed === total && total > 0) {
            statusBadge.textContent = 'Completed';
            statusBadge.className = 'badge bg-success';
        } else if (inProgress > 0) {
            const retrying = session.files.filter(f => f.status === 'retrying').length;
            if (retrying > 0) {
                statusBadge.textContent = `Retrying (${retrying} files)`;
                statusBadge.className = 'badge bg-warning';
            } else {
                statusBadge.textContent = `Uploading (${inProgress} active)`;
                statusBadge.className = 'badge bg-primary';
            }
        } else {
            statusBadge.textContent = 'Processing...';
            statusBadge.className = 'badge bg-info';
        }

        // Render file list
        const fileList = document.getElementById('uploadModalFileList');
        if (session.files.length === 0) {
            fileList.innerHTML = '<p class="text-muted text-center">Preparing uploads...</p>';
        } else {
            let html = '<div class="list-group">';
            session.files.sort((a, b) => a.index - b.index).forEach(file => {
                const statusColor = file.status === 'completed' ? 'success' :
                                  file.status === 'failed' ? 'danger' :
                                  file.status === 'retrying' ? 'warning' :
                                  file.status === 'uploading' ? 'primary' : 'secondary';
                const statusIcon = file.status === 'completed' ? 'fa-check-circle' :
                                 file.status === 'failed' ? 'fa-times-circle' :
                                 file.status === 'retrying' ? 'fa-redo fa-spin' :
                                 file.status === 'uploading' ? 'fa-spinner fa-spin' : 'fa-clock';
                
                const retryInfo = file.retryCount > 0 ? ` (retry ${file.retryCount}/${session.maxRetries})` : '';
                
                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="d-flex align-items-center">
                                    <i class="fas ${statusIcon} text-${statusColor} me-2"></i>
                                    <span class="small">${this.escapeHtml(file.name)}</span>
                                </div>
                                ${file.jobId ? `<small class="text-muted d-block mt-1">Job ID: ${file.jobId}</small>` : ''}
                                ${file.error ? `<small class="text-danger d-block mt-1">Error: ${this.escapeHtml(file.error)}${retryInfo}</small>` : ''}
                                ${file.status === 'retrying' ? `<small class="text-warning d-block mt-1">Retrying... (attempt ${file.retryCount}/${session.maxRetries})</small>` : ''}
                            </div>
                            <span class="badge bg-${statusColor}">${file.status}${retryInfo}</span>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            fileList.innerHTML = html;
        }

        // Update status message based on current state
        const statusMessage = document.getElementById('uploadModalStatusMessage');
        const statusText = document.getElementById('uploadModalStatusText');
        
        if (completed + failed === total && total > 0) {
            // All uploads finished (completed or failed)
            document.getElementById('uploadModalCloseBtn').disabled = false;
            document.getElementById('uploadModalViewJobsBtn').style.display = 'inline-block';
            
            if (failed > 0) {
                statusText.textContent = `⚠️ ${failed} file(s) failed after ${session.maxRetries} retries. Check errors above.`;
                statusMessage.className = 'flex-grow-1 text-warning small';
                
                // Show warning in file list
                const fileList = document.getElementById('uploadModalFileList');
                // Remove existing warning if any
                const existingWarning = fileList.querySelector('.alert-warning');
                if (!existingWarning) {
                    const warningHtml = `
                        <div class="alert alert-warning mt-3" role="alert">
                            <i class="fas fa-exclamation-triangle"></i>
                            <strong>Warning:</strong> ${failed} file(s) failed to upload after ${session.maxRetries} retry attempts.
                            Please check the errors above and try uploading those files again.
                        </div>
                    `;
                    fileList.insertAdjacentHTML('beforeend', warningHtml);
                }
            } else {
                // All uploads completed successfully - check if conversion was requested
                const willConvert = session.willConvert || false;
                
                if (willConvert) {
                    statusText.textContent = '✅ All uploads completed! Files are being converted and will be available shortly.';
                } else {
                    statusText.textContent = '✅ All uploads completed! Your dataset is ready to view.';
                }
                statusMessage.className = 'flex-grow-1 text-success small';
            }
        } else if (inProgress > 0) {
            // Uploads still in progress
            const retrying = session.files.filter(f => f.status === 'retrying').length;
            if (retrying > 0) {
                statusText.textContent = `🔄 Retrying ${retrying} file(s)... Keep this page open until retries finish.`;
                statusMessage.className = 'flex-grow-1 text-warning small';
            } else {
                statusText.textContent = `📤 ${inProgress} file(s) still sending. Do not navigate away or reload this page yet.`;
                statusMessage.className = 'flex-grow-1 text-warning small';
            }
            document.getElementById('uploadModalCloseBtn').disabled = false; // Dialog can close; browser tab must stay open.
        } else {
            // Initial state or all queued
            statusText.textContent = 'Preparing upload requests. Keep this page open until files are marked completed.';
            statusMessage.className = 'flex-grow-1 text-warning small';
            document.getElementById('uploadModalCloseBtn').disabled = false;
        }
    }

    /**
     * Retry failed uploads automatically
     */
    async retryFailedUploads(failedFiles, uploadData, userEmail, datasetUuid, isDirectoryUpload, baseDirectoryName) {
        if (!this.currentUploadSession || failedFiles.length === 0) return;

        const maxRetries = this.currentUploadSession.maxRetries;
        const retryDelay = this.currentUploadSession.retryDelay;

        // Group files by retry attempt
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            // Get files that still need retrying
            const filesToRetry = failedFiles.filter(f => {
                const fileInfo = this.currentUploadSession.files.find(fi => fi.index === f.fileIndex);
                return fileInfo && fileInfo.status === 'failed' && fileInfo.retryCount < attempt;
            });

            if (filesToRetry.length === 0) break;

            // Update status to retrying
            filesToRetry.forEach(f => {
                const fileInfo = this.currentUploadSession.files.find(fi => fi.index === f.fileIndex);
                if (fileInfo) {
                    this.updateUploadModalFile(f.fileIndex, fileInfo.name, 'retrying', null, null, attempt);
                }
            });

            // Wait before retrying
            if (attempt > 1) {
                await new Promise(resolve => setTimeout(resolve, retryDelay));
            }

            // Retry each file
            const retryPromises = filesToRetry.map(async (failedFile) => {
                const file = failedFile.file;
                const fileIndex = failedFile.fileIndex;
                const fileName = file.name;

                try {
                    // Prepare upload form data (same as original upload)
                    const uploadFormData = new FormData();
                    uploadFormData.append('file', file);
                    uploadFormData.append('user_email', userEmail);
                    uploadFormData.append('dataset_name', uploadData.dataset_name);
                    uploadFormData.append('sensor', uploadData.sensor);
                    uploadFormData.append('convert', uploadData.convert);
                    uploadFormData.append('is_public', uploadData.is_public);
                    if (uploadData.expected_files_json) {
                        uploadFormData.append('expected_files', uploadData.expected_files_json);
                    }
                    
                    if (uploadData.folder) {
                        uploadFormData.append('folder', uploadData.folder);
                    }
                    
                    // Handle directory uploads
                    if (isDirectoryUpload && file.webkitRelativePath) {
                        const fullPath = file.webkitRelativePath;
                        let relativePath = null;
                        if (fullPath.startsWith(baseDirectoryName + '/')) {
                            relativePath = fullPath.substring(baseDirectoryName.length + 1);
                            if (!relativePath || relativePath === file.name) {
                                relativePath = null;
                            } else {
                                const pathParts = relativePath.split('/');
                                pathParts.pop();
                                relativePath = pathParts.length > 0 ? pathParts.join('/') : null;
                            }
                        }
                        if (relativePath) {
                            uploadFormData.append('relative_path', relativePath);
                        }
                    }
                    
                    if (uploadData.team_uuid) uploadFormData.append('team_uuid', uploadData.team_uuid);
                    if (uploadData.tags) uploadFormData.append('tags', uploadData.tags);
                    uploadFormData.append('dataset_identifier', datasetUuid);

                    const uploadUrl = `${getUploadApiBasePath()}/upload-dataset.php`;
                    
                    // Mark as uploading
                    this.updateUploadModalFile(fileIndex, fileName, 'uploading', null, null, attempt);

                    const response = await fetch(uploadUrl, {
                        method: 'POST',
                        body: uploadFormData
                    });

                    const text = await response.text();
                    
                    if (!text || text.trim().length === 0) {
                        throw new Error('Empty response from server');
                    }

                    const cleanedText = text.trim();
                    if (cleanedText[0] !== '{' && cleanedText[0] !== '[') {
                        throw new Error('Response is not valid JSON');
                    }

                    const result = JSON.parse(cleanedText);

                    if (result.job_id && response.status === 200) {
                        // Success!
                        this.updateUploadModalFile(fileIndex, fileName, 'completed', result.job_id, null, attempt);
                        this.trackUpload(result.job_id, uploadData.dataset_name, fileName, uploadData.convert, datasetUuid);
                        return { success: true, fileIndex, result };
                    } else {
                        // Still failed
                        const errorMsg = result.error || result.message || 'Upload failed';
                        this.updateUploadModalFile(fileIndex, fileName, 'failed', null, errorMsg, attempt);
                        return { success: false, fileIndex, error: errorMsg };
                    }
                } catch (error) {
                    const errorMsg = error.message || 'Network error';
                    this.updateUploadModalFile(fileIndex, fileName, 'failed', null, errorMsg, attempt);
                    return { success: false, fileIndex, error: errorMsg };
                }
            });

            // Wait for all retries to complete
            await Promise.all(retryPromises);

            // Check if all files are now successful
            const stillFailed = failedFiles.filter(f => {
                const fileInfo = this.currentUploadSession.files.find(fi => fi.index === f.fileIndex);
                return fileInfo && fileInfo.status === 'failed';
            });

            if (stillFailed.length === 0) {
                // All files succeeded!
                break;
            }
        }

        // Refresh dataset list after retries
        if (window.datasetManager) {
            window.datasetManager.loadDatasets();
        }
    }

    /**
     * Show create team interface
     */
    async showCreateTeamInterface() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading teams...</p>
            </div>
        `;

        // Fetch teams for parent selection
        let teams = [];
        try {
            const teamsResponse = await fetch(`${getApiBasePath()}/get-teams.php`);
            if (teamsResponse.ok) {
                const teamsData = await teamsResponse.json();
                if (teamsData.success && teamsData.teams) {
                    // Filter to only show teams owned by the user (for parent selection)
                    const userEmail = await this.getUserEmail();
                    teams = teamsData.teams.filter(team => team.is_owner || team.owner === userEmail);
                }
            }
        } catch (error) {
            console.warn('Could not load teams for parent selection:', error);
        }

        // Show create team interface (similar to share interface)
        viewerContainer.innerHTML = `
            <div class="create-team-interface container mt-4">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-users"></i> Create Team
                        </h5>
                    </div>
                    <div class="card-body">
                        <form id="createTeamForm">
                            <div class="mb-3">
                                <label class="form-label">Team Name: <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" name="team_name" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Parent Team: <span class="text-muted">(optional)</span></label>
                                <select class="form-select" name="team_parent" id="team_parent">
                                    <option value="">Select Parent Team (optional)</option>
                                    ${teams.map(team => `<option value="${team.uuid}">${this.escapeHtml(team.team_name)}</option>`).join('')}
                                </select>
                                <small class="form-text text-muted">Select a parent team if this team should be under another team</small>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Member Emails:</label>
                                <div id="team-email-entries">
                                    <div class="email-entry mb-2">
                                        <input type="email" class="form-control form-control-sm" 
                                               placeholder="member@example.com" 
                                               data-entry-index="1">
                                    </div>
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-secondary mt-2" 
                                        onclick="uploadManager.addTeamEmailEntry()">
                                    <i class="fas fa-plus"></i> Add Email
                                </button>
                            </div>

                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-plus"></i> Create Team
                            </button>
                            <button type="button" class="btn btn-secondary ms-2" 
                                    onclick="uploadManager.closeUploadInterface()">
                                Cancel
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `;

        // Setup form handler
        const form = document.getElementById('createTeamForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCreateTeam(form);
            });
        }
    }

    /**
     * Handle create team
     */
    async handleCreateTeam(form) {
        const formData = new FormData(form);
        const teamName = formData.get('team_name');
        const parentTeamUuid = formData.get('team_parent');
        
        if (!teamName) {
            alert('Team name is required');
            return;
        }

        // Get email entries
        const emailInputs = document.querySelectorAll('#team-email-entries input[type="email"]');
        const emails = Array.from(emailInputs)
            .map(input => input.value.trim())
            .filter(email => email && this.isValidEmail(email));

        // Get parent team UUID(s) - convert to array format
        const parents = parentTeamUuid ? [parentTeamUuid] : [];

        const userEmail = await this.getUserEmail();
        if (!userEmail) {
            alert('User not authenticated');
            return;
        }

        try {
            const response = await fetch(`${getApiBasePath()}/create-team.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    team_name: teamName,
                    emails: emails,
                    parents: parents,
                    owner_email: userEmail
                })
            });

            const data = await response.json();

            if (data.success) {
                alert(`Team "${teamName}" created successfully!`);
                this.closeUploadInterface();
                // Refresh teams list if needed
                return {
                    team_name: teamName,
                    team: data.team
                };
            } else {
                alert(`Error creating team: ${data.error || 'Unknown error'}`);
                return null;
            }
        } catch (error) {
            console.error('Error creating team:', error);
            alert('Error creating team: ' + error.message);
        }
    }

    /**
     * Add team email entry
     */
    addTeamEmailEntry() {
        const container = document.getElementById('team-email-entries');
        if (!container) return;

        const entries = container.querySelectorAll('.email-entry');
        const nextIndex = entries.length + 1;

        const newEntry = document.createElement('div');
        newEntry.className = 'email-entry mb-2';
        newEntry.innerHTML = `
            <div class="input-group">
                <input type="email" class="form-control form-control-sm" 
                       placeholder="member@example.com" 
                       data-entry-index="${nextIndex}">
                <button type="button" class="btn btn-sm btn-outline-danger" 
                        onclick="this.closest('.email-entry').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        container.appendChild(newEntry);
    }

    /**
     * Close upload interface
     */
    closeUploadInterface() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (viewerContainer) {
            // Show default content or reload dashboard
            viewerContainer.innerHTML = `
                <div class="text-center mt-5">
                    <i class="fas fa-cloud-upload-alt fa-3x text-muted mb-3"></i>
                    <h5>No dataset selected</h5>
                    <p class="text-muted">Select a dataset from the sidebar to view it here</p>
                </div>
            `;
        }
    }

    /**
     * Show create team page in viewer container
     */
    async ensureTeamManagementScript(assetsBase) {
        if (typeof scInitTeamManagement === 'function') {
            return;
        }
        const src = `${assetsBase}/js/team-management.js`;
        const existing = document.querySelector(`script[src="${src}"]`);
        if (existing) {
            await new Promise((resolve, reject) => {
                if (typeof scInitTeamManagement === 'function') {
                    resolve();
                    return;
                }
                existing.addEventListener('load', resolve);
                existing.addEventListener('error', () => reject(new Error('team-management.js failed to load')));
            });
            return;
        }
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error('team-management.js failed to load'));
            document.head.appendChild(script);
        });
    }

    async showCreateTeamPage() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading team management...</p>
            </div>
        `;

        try {
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const portalBase = typeof getPortalBasePath === 'function' ? getPortalBasePath() : (isLocal ? '' : '/portal');
            const apiBase = typeof getApiBasePath === 'function' ? getApiBasePath() : (isLocal ? '/api' : '/portal/api');
            const assetsBase = portalBase === '' ? '/assets' : `${portalBase}/assets`;
            window.SC_PORTAL_API_BASE = apiBase;
            window.SC_PORTAL_ASSETS_BASE = assetsBase;

            const url = `${portalBase}/createTeam/index.php`;
            
            // Fetch the page content
            const response = await fetch(url, { credentials: 'same-origin' });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            let html = await response.text();
            html = html
                .replace(/\.\.\/api\//g, `${apiBase}/`)
                .replace(/\.\.\/assets\//g, `${assetsBase}/`);
            
            // Extract body content and styles from the HTML
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            let bodyContent = doc.body.innerHTML;
            bodyContent = bodyContent
                .replace(/\.\.\/api\//g, `${apiBase}/`)
                .replace(/\.\.\/assets\//g, `${assetsBase}/`);
            
            // Extract styles from head
            const styles = doc.head.querySelectorAll('style, link[rel="stylesheet"]');
            let stylesHTML = '';
            styles.forEach(style => {
                if (style.tagName === 'STYLE') {
                    stylesHTML += `<style>${style.innerHTML}</style>`;
                } else if (style.tagName === 'LINK') {
                    let linkHtml = style.outerHTML;
                    linkHtml = linkHtml
                        .replace(/\.\.\/assets\//g, `${assetsBase}/`)
                        .replace(/href="\/assets\//g, `href="${assetsBase}/`);
                    stylesHTML += linkHtml;
                }
            });
            
            // Apply current theme class
            const currentTheme = localStorage.getItem('theme') || 'light';
            const themeClass = currentTheme === 'light' ? 'light-theme' : '';
            
            // Load content into viewer container with styles
            viewerContainer.innerHTML = `
                ${stylesHTML}
                <div class="create-team-page-wrapper ${themeClass}" style="height: 100%; overflow-y: auto; padding: 20px;">
                    ${bodyContent}
                </div>
            `;

            // Run inline config scripts only (skip external src — loaded explicitly below)
            const scripts = viewerContainer.querySelectorAll('script');
            scripts.forEach(oldScript => {
                if (oldScript.src) {
                    oldScript.remove();
                    return;
                }
                const newScript = document.createElement('script');
                newScript.textContent = oldScript.textContent;
                oldScript.parentNode.replaceChild(newScript, oldScript);
            });

            await this.ensureTeamManagementScript(assetsBase);

            const ownerEl = viewerContainer.querySelector('[data-sc-owner-email]');
            const ownerEmail = ownerEl ? (ownerEl.getAttribute('data-sc-owner-email') || '') : '';
            if (typeof scInitTeamManagement === 'function') {
                scInitTeamManagement(ownerEmail);
            }
            
        } catch (error) {
            console.error('Error loading create team page:', error);
            viewerContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <h5><i class="fas fa-exclamation-triangle"></i> Error Loading Team Management</h5>
                    <p>Failed to load team management page: ${error.message}</p>
                    <button class="btn btn-primary" onclick="window.uploadManager.showCreateTeamPage()">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        }
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
     * Validate email
     */
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
}

// Initialize upload manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.uploadManager = new UploadManager();
});

