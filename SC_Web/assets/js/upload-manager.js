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
        this.initialize();
    }

    /**
     * Initialize the upload manager
     */
    initialize() {
        this.setupEventListeners();
        this.createProgressWidget();
        this.createUploadModal();
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

        // Create Team button
        const createTeamBtn = document.getElementById('createTeamBtn');
        if (createTeamBtn) {
            createTeamBtn.addEventListener('click', () => {
                this.showCreateTeamInterface();
            });
        }
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
                    <input type="text" class="form-control" name="name" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Local Source (file, folder, or zip): <span class="text-danger">*</span></label>
                    <input type="file" class="form-control" id="localFileInput" 
                           name="files" multiple webkitdirectory directory>
                    <small class="form-text text-muted">
                        Select files, a folder, or a zip file. For folders, use the folder picker.
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
                    <select class="form-select" name="dimensions">
                        <option value="">-- Select Dimensions --</option>
                        <option value="2D">2D</option>
                        <option value="3D">3D</option>
                        <option value="4D">4D</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select" name="preferred_dashboard">
                        <option value="OpenVisusSlice">OpenVisusSlice</option>
                        <option value="4D_Dashboard">4D_Dashboard</option>
                        <option value="3DVTK">3DVTK</option>
                        <option value="magicscan">magicscan</option>
                        <option value="openvisus">openvisus</option>
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
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="convert" id="localConvert" checked>
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
                    <label class="form-label">Google Drive File ID: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="file_id" 
                           placeholder="Enter Google Drive file ID" required>
                    <small class="form-text text-muted">
                        Get the file ID from the Google Drive file URL
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
                    <select class="form-select" name="dimensions">
                        <option value="">-- Select Dimensions --</option>
                        <option value="2D">2D</option>
                        <option value="3D">3D</option>
                        <option value="4D">4D</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select" name="preferred_dashboard">
                        <option value="OpenVisusSlice">OpenVisusSlice</option>
                        <option value="4D_Dashboard">4D_Dashboard</option>
                        <option value="3DVTK">3DVTK</option>
                        <option value="magicscan">magicscan</option>
                        <option value="openvisus">openvisus</option>
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
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="convert" id="googleConvert" checked>
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
        return `
            <form id="s3UploadForm">
                <div class="mb-3">
                    <label class="form-label">Name: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="name" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Endpoint URL: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="endpoint_url" 
                           placeholder="https://s3.amazonaws.com" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Bucket: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="bucket" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Prefix (directory on S3):</label>
                    <input type="text" class="form-control" name="prefix" 
                           placeholder="path/to/files/">
                </div>

                <div class="mb-3">
                    <label class="form-label">Access Key: <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" name="access_key" required>
                </div>

                <div class="mb-3">
                    <label class="form-label">Secret Key: <span class="text-danger">*</span></label>
                    <input type="password" class="form-control" name="secret_key" required>
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
                    <select class="form-select" name="dimensions">
                        <option value="">-- Select Dimensions --</option>
                        <option value="2D">2D</option>
                        <option value="3D">3D</option>
                        <option value="4D">4D</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select" name="preferred_dashboard">
                        <option value="OpenVisusSlice">OpenVisusSlice</option>
                        <option value="4D_Dashboard">4D_Dashboard</option>
                        <option value="3DVTK">3DVTK</option>
                        <option value="magicscan">magicscan</option>
                        <option value="openvisus">openvisus</option>
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
                    <i class="fas fa-upload"></i> Upload from S3
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
                    <select class="form-select" name="dimensions">
                        <option value="">-- Select Dimensions --</option>
                        <option value="2D">2D</option>
                        <option value="3D">3D</option>
                        <option value="4D">4D</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="form-label">Preferred Dashboard:</label>
                    <select class="form-select" name="preferred_dashboard">
                        <option value="OpenVisusSlice">OpenVisusSlice</option>
                        <option value="4D_Dashboard">4D_Dashboard</option>
                        <option value="3DVTK">3DVTK</option>
                        <option value="magicscan">magicscan</option>
                        <option value="openvisus">openvisus</option>
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

    /**
     * Initialize local file input
     */
    initializeLocalFileInput() {
        const fileInput = document.getElementById('localFileInput');
        if (fileInput) {
            // Allow both file and directory selection
            fileInput.addEventListener('change', (e) => {
                const files = e.target.files;
                if (files.length > 0) {
                    console.log(`Selected ${files.length} file(s) for upload`);
                }
            });
        }

        // Setup folder dropdown listeners
        this.setupFolderDropdownListeners();

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
        }

        const s3Form = document.getElementById('s3UploadForm');
        if (s3Form) {
            s3Form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleS3Upload(s3Form);
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
        const files = document.getElementById('localFileInput').files;

        if (!files || files.length === 0) {
            alert('Please select at least one file');
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
        
        const uploadData = {
            dataset_name: formData.get('name'),
            sensor: formData.get('sensor'),
            convert: formData.get('convert') === 'on',
            is_public: formData.get('is_public') === 'on',
            folder: folderValue,
            team_uuid: formData.get('team_uuid') || null,
            tags: formData.get('tags') || '',
            dimensions: formData.get('dimensions') || null,
            preferred_dashboard: formData.get('preferred_dashboard') || 'OpenVisusSlice'
        };

        // Upload files - handle multiple files by uploading them sequentially
        // For directories, the browser will provide all files
        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

            // Show upload progress modal
            this.showUploadModal(uploadData.dataset_name, files.length);

            // Generate a single UUID for all files to group them in the same dataset
            const datasetUuid = this.generateUUID();
            console.log(`Grouping ${files.length} file(s) under dataset UUID: ${datasetUuid}`);
            
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
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                
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
                
                // Mark file as queued
                this.updateUploadModalFile(fileIndex, fileName, 'queued');
                
                uploadPromises.push(
                    fetch(uploadUrl, {
                        method: 'POST',
                        body: uploadFormData
                    }).then(async response => {
                        // Mark file as uploading
                        this.updateUploadModalFile(fileIndex, fileName, 'uploading');
                        
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
                        const errorMsg = error.message || 'Network error';
                        this.updateUploadModalFile(fileIndex, fileName, 'failed', null, errorMsg);
                        throw error;
                    })
                );
            }

            // Wait for all uploads to complete (or fail)
            const results = await Promise.allSettled(uploadPromises);
            const successful = results.filter(r => r.status === 'fulfilled' && r.value && r.value.job_id).map(r => r.value);
            
            // Map failed results back to their file indices
            const failedFiles = [];
            results.forEach((result, index) => {
                if (result.status === 'rejected' || !result.value || !result.value.job_id) {
                    failedFiles.push({
                        fileIndex: index,
                        file: files[index],
                        error: result.status === 'rejected' ? result.reason?.message : 'Upload failed',
                        result: result.value
                    });
                }
            });

            // Track successful uploads
            successful.forEach(result => {
                this.trackUpload(result.job_id, uploadData.dataset_name);
            });

            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;

            // Update status message - uploads are queued
            if (this.currentUploadSession) {
                const statusText = document.getElementById('uploadModalStatusText');
                if (statusText) {
                    if (successful.length > 0) {
                        statusText.textContent = `✅ ${successful.length} file(s) queued successfully. Uploads continue in background. Safe to close.`;
                        document.getElementById('uploadModalStatusMessage').className = 'flex-grow-1 text-success small';
                    }
                }
            }

            // Retry failed uploads automatically (in background)
            if (failedFiles.length > 0) {
                // Don't await - let retries happen in background
                this.retryFailedUploads(failedFiles, uploadData, userEmail, datasetUuid, isDirectoryUpload, baseDirectoryName)
                    .catch(error => {
                        console.error('Error during retry process:', error);
                    });
            }

            // Don't close upload interface automatically - let user see the modal
            // The modal will show all results and allow user to close when ready
            // Refresh dataset list if any uploads succeeded
            if (successful.length > 0 && window.datasetManager) {
                window.datasetManager.loadDatasets();
            }
        } catch (error) {
            console.error('Error uploading file:', error);
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

        const fileId = formData.get('file_id');
        if (!fileId) {
            alert('Google Drive File ID is required');
            return;
        }

        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initiating...';

            // Use SCLib Upload API initiate endpoint for Google Drive
            const requestData = {
                source_type: 'google_drive',
                source_config: {
                    file_id: fileId,
                    service_account_file: '' // TODO: Get from config or user settings
                },
                user_email: userEmail,
                dataset_name: formData.get('name'),
                sensor: formData.get('sensor'),
                convert: formData.get('convert') === 'on',
                is_public: formData.get('is_public') === 'on',
                folder: this.getFolderValue(form),
                team_uuid: formData.get('team_uuid') || null
            };

            const response = await fetch(`${getUploadApiBasePath()}/api/upload/initiate`, {
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
                this.trackUpload(data.job_id, requestData.dataset_name);
                alert(`Google Drive upload started! Job ID: ${data.job_id}\nYou can continue using the app. Check the progress widget.`);
                this.closeUploadInterface();
            } else {
                throw new Error(data.error || data.detail || 'Upload failed');
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

        const bucket = formData.get('bucket');
        const prefix = formData.get('prefix') || '';
        const accessKey = formData.get('access_key');
        const secretKey = formData.get('secret_key');

        if (!bucket || !accessKey || !secretKey) {
            alert('Bucket, Access Key, and Secret Key are required');
            return;
        }

        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initiating...';

            // Use SCLib Upload API initiate endpoint for S3
            const requestData = {
                source_type: 's3',
                source_config: {
                    bucket_name: bucket,
                    object_key: prefix,
                    access_key_id: accessKey,
                    secret_access_key: secretKey
                },
                user_email: userEmail,
                dataset_name: formData.get('name'),
                sensor: formData.get('sensor'),
                convert: formData.get('convert') === 'on',
                is_public: formData.get('is_public') === 'on',
                folder: this.getFolderValue(form),
                team_uuid: formData.get('team_uuid') || null
            };

            const response = await fetch(`${getUploadApiBasePath()}/api/upload/initiate`, {
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
                this.trackUpload(data.job_id, requestData.dataset_name);
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
                submitBtn.innerHTML = '<i class="fas fa-upload"></i> Upload from S3';
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
                folder: this.getFolderValue(form),
                team_uuid: formData.get('team_uuid') || null
            };

            const response = await fetch(`${getUploadApiBasePath()}/api/upload/initiate`, {
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
                this.trackUpload(data.job_id, requestData.dataset_name);
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
     * Track upload progress
     */
    trackUpload(jobId, datasetName) {
        this.activeUploads.set(jobId, {
            job_id: jobId,
            dataset_name: datasetName,
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
        const maxAttempts = 600; // Poll for up to 10 minutes (1 second intervals)
        let attempts = 0;

        const poll = async () => {
            if (attempts >= maxAttempts) {
                return;
            }

            try {
                // Use PHP proxy for status polling
                const response = await fetch(`${getApiBasePath()}/upload-status.php?job_id=${encodeURIComponent(jobId)}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const data = await response.json();

                if (data.job_id) {
                    const upload = this.activeUploads.get(jobId);
                    if (upload) {
                        upload.status = data.status;
                        upload.progress = data.progress_percentage || 0;
                        upload.message = data.message;
                        
                        this.updateProgressWidget();

                        // Continue polling if not completed or failed
                        if (data.status !== 'completed' && data.status !== 'failed') {
                            setTimeout(poll, 1000);
                        } else {
                            // Upload finished
                            if (data.status === 'completed') {
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
            }

            attempts++;
        };

        poll();
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
        if (!progressList) return;

        if (this.activeUploads.size === 0) {
            progressList.innerHTML = '<p class="text-muted small">No active uploads</p>';
            return;
        }

        let html = '';
        this.activeUploads.forEach((upload, jobId) => {
            const statusColor = upload.status === 'completed' ? 'success' : 
                              upload.status === 'failed' ? 'danger' : 'primary';
            
            html += `
                <div class="upload-progress-item mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="small">${this.escapeHtml(upload.dataset_name)}</span>
                        <span class="badge bg-${statusColor}">${upload.status}</span>
                    </div>
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
                </div>
            `;
        });

        progressList.innerHTML = html;
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
                            <i class="fas fa-info-circle"></i> <span id="uploadModalStatusText">Uploads are queued and will continue in the background. You can safely close this window.</span>
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
            retryDelay: 2000 // 2 seconds between retries
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
        document.getElementById('uploadModalCloseBtn').disabled = false; // Allow closing - uploads continue in background
        document.getElementById('uploadModalViewJobsBtn').style.display = 'none';
        document.getElementById('uploadModalStatusText').textContent = 'Preparing uploads...';
        document.getElementById('uploadModalStatusMessage').className = 'flex-grow-1 text-muted small';

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
                statusText.textContent = '✅ All uploads completed successfully!';
                statusMessage.className = 'flex-grow-1 text-success small';
            }
        } else if (inProgress > 0) {
            // Uploads still in progress
            const retrying = session.files.filter(f => f.status === 'retrying').length;
            if (retrying > 0) {
                statusText.textContent = `🔄 Retrying ${retrying} file(s)... Uploads continue in background. Safe to close.`;
                statusMessage.className = 'flex-grow-1 text-warning small';
            } else {
                statusText.textContent = `📤 ${inProgress} upload(s) in progress. Uploads continue in background. Safe to close.`;
                statusMessage.className = 'flex-grow-1 text-info small';
            }
            document.getElementById('uploadModalCloseBtn').disabled = false; // Always allow closing
        } else {
            // Initial state or all queued
            statusText.textContent = '✅ Uploads are queued and will continue in the background. You can safely close this window.';
            statusMessage.className = 'flex-grow-1 text-success small';
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
                        this.trackUpload(result.job_id, uploadData.dataset_name);
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
        
        if (!teamName) {
            alert('Team name is required');
            return;
        }

        // Get email entries
        const emailInputs = document.querySelectorAll('#team-email-entries input[type="email"]');
        const emails = Array.from(emailInputs)
            .map(input => input.value.trim())
            .filter(email => email && this.isValidEmail(email));

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
                    owner_email: userEmail
                })
            });

            const data = await response.json();

            if (data.success) {
                alert(`Team "${teamName}" created successfully!`);
                this.closeUploadInterface();
                // Refresh teams list if needed
            } else {
                alert(`Error creating team: ${data.error || 'Unknown error'}`);
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

