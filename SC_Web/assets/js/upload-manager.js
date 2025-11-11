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
        this.initialize();
    }

    /**
     * Initialize the upload manager
     */
    initialize() {
        this.setupEventListeners();
        this.createProgressWidget();
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
                    <select class="form-select" name="folder_uuid">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
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
                    <select class="form-select" name="folder_uuid">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
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
                    <select class="form-select" name="folder_uuid">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
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
                    <select class="form-select" name="folder_uuid">
                        <option value="">-- No Folder --</option>
                        ${folders.map(f => `<option value="${this.escapeHtml(f.uuid)}">${this.escapeHtml(f.name)}</option>`).join('')}
                        <option value="__CREATE__">+ Create New Folder</option>
                    </select>
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
        const uploadData = {
            dataset_name: formData.get('name'),
            sensor: formData.get('sensor'),
            convert: formData.get('convert') === 'on',
            is_public: formData.get('is_public') === 'on',
            folder: formData.get('folder_uuid') || null,
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

            // Generate a single UUID for all files to group them in the same dataset
            const datasetUuid = this.generateUUID();
            console.log(`Grouping ${files.length} file(s) under dataset UUID: ${datasetUuid}`);
            
            const uploadPromises = [];
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                
                const uploadFormData = new FormData();
                uploadFormData.append('file', file);
                uploadFormData.append('user_email', userEmail);
                uploadFormData.append('dataset_name', uploadData.dataset_name); // Use same name for all files
                uploadFormData.append('sensor', uploadData.sensor);
                uploadFormData.append('convert', uploadData.convert);
                uploadFormData.append('is_public', uploadData.is_public);
                if (uploadData.folder) uploadFormData.append('folder', uploadData.folder);
                if (uploadData.team_uuid) uploadFormData.append('team_uuid', uploadData.team_uuid);
                if (uploadData.tags) uploadFormData.append('tags', uploadData.tags);
                
                // Group files under the same dataset UUID
                uploadFormData.append('dataset_identifier', datasetUuid);
                if (i > 0) {
                    // For files after the first, add to existing dataset
                    uploadFormData.append('add_to_existing', 'true');
                }

                // Build upload URL
                const uploadUrl = `${getUploadApiBasePath()}/upload-dataset.php`;
                console.log(`Uploading file ${i + 1}/${files.length} to: ${uploadUrl}`);
                if (i > 0) {
                    console.log(`  Adding to existing dataset: ${datasetUuid}`);
                }
                
                uploadPromises.push(
                    fetch(uploadUrl, {
                        method: 'POST',
                        body: uploadFormData
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
                            
                            return JSON.parse(cleanedText);
                        } catch (e) {
                            console.error('JSON parse error:', e);
                            console.error('Full response:', text);
                            throw new Error('Invalid JSON response: ' + e.message + '. Response preview: ' + text.substring(0, 200));
                        }
                    }).catch(error => {
                        console.error('Upload fetch error:', error);
                        throw error;
                    })
                );
            }

            const results = await Promise.all(uploadPromises);
            const successful = results.filter(r => r.job_id);
            const failed = results.filter(r => !r.job_id);

            // Track successful uploads
            successful.forEach(result => {
                this.trackUpload(result.job_id, uploadData.dataset_name);
            });

            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;

            if (successful.length > 0) {
                const message = successful.length === 1 
                    ? `Upload started! Job ID: ${successful[0].job_id}\nYou can continue using the app. Check the progress widget.`
                    : `${successful.length} upload(s) started!\nYou can continue using the app. Check the progress widget.`;
                
                if (failed.length > 0) {
                    alert(message + `\n\n${failed.length} file(s) failed to upload.`);
                } else {
                    alert(message);
                }
                
                this.closeUploadInterface();
            } else {
                throw new Error('All uploads failed');
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
                folder: formData.get('folder_uuid') || null,
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
                folder: formData.get('folder_uuid') || null,
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
                folder: formData.get('folder_uuid') || null,
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

