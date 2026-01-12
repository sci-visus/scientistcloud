/**
 * Viewer Manager JavaScript
 * Handles viewer operations and dashboard management
 */

console.log('📦 viewer-manager.js loaded');
console.log('📦 Script location:', document.currentScript?.src || 'inline');
console.log('📦 Document ready state:', document.readyState);
console.log('📦 Current URL:', window.location.href);

class ViewerManager {
    constructor() {
        this.currentViewer = null;
        this.viewers = {}; // Will be loaded from API
        // No default viewers - all should come from API to avoid duplicates
        this.defaultViewers = {};
        this.isLoading = false; // Flag to prevent double loading
        this.currentLoadingKey = null; // Track what's currently loading
        this.currentDashboard = null; // Track the currently loaded dashboard type
        // Initialize asynchronously - don't await in constructor
        this.initialize().catch(error => {
            console.error('Failed to initialize ViewerManager:', error);
            // Still try to populate selector even if initialization fails
            this.populateViewerSelector();
        });
    }
    
    /**
     * Load dashboards from API
     */
    async loadDashboards() {
        console.log('📡 loadDashboards() called');
        console.log('📡 Current URL:', window.location.href);
        console.log('📡 Hostname:', window.location.hostname);
        try {
            // Helper function to get API base path (detects local vs server)
            const getApiBasePath = () => {
                const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                const basePath = isLocal ? '/api' : '/portal/api';
                console.log('📡 API base path:', basePath, '(isLocal:', isLocal, ')');
                return basePath;
            };
            
            const apiUrl = `${getApiBasePath()}/dashboards.php`;
            console.log('🌐 Loading dashboards from:', apiUrl);
            console.log('🌐 Full URL will be:', window.location.origin + apiUrl);
            
            const fetchStartTime = Date.now();
            console.log('⏱️ Starting fetch at:', new Date().toISOString());
            
            // Add timeout to prevent hanging
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Fetch timeout after 10 seconds')), 10000);
            });
            
            const fetchPromise = fetch(apiUrl, {
                credentials: 'include',  // Include cookies for authentication
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            const response = await Promise.race([fetchPromise, timeoutPromise]);
            
            const fetchDuration = Date.now() - fetchStartTime;
            console.log('⏱️ Fetch completed in', fetchDuration, 'ms');
            console.log('📡 Response status:', response.status, response.statusText);
            console.log('📡 Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                console.warn(`Failed to load dashboards from API (${response.status} ${response.statusText})`);
                // Try to parse error response
                try {
                    const errorData = await response.json();
                    console.error('API error response:', errorData);
                } catch (e) {
                    console.error('Could not parse error response');
                }
                // Don't use defaults - show error in selector
                this.viewers = {};
                this.populateViewerSelector();
                return;
            }
            
            let data;
            let responseText;
            try {
                responseText = await response.text();
                console.log('📡 Raw response text (first 500 chars):', responseText.substring(0, 500));
                data = JSON.parse(responseText);
                console.log('✅ Parsed JSON successfully');
            } catch (parseError) {
                console.error('❌ Failed to parse JSON response:', parseError);
                console.error('❌ Response text:', responseText || 'Could not read response');
                this.viewers = {};
                this.populateViewerSelector();
                return;
            }
            
            console.log('📊 Dashboards API response:', data);
            console.log('📊 Response keys:', Object.keys(data));
            console.log('📊 data.success:', data.success);
            console.log('📊 data.dashboards type:', typeof data.dashboards, Array.isArray(data.dashboards));
            console.log('📊 data.dashboards length:', data.dashboards?.length);
            
            if (data.success && data.dashboards && Array.isArray(data.dashboards) && data.dashboards.length > 0) {
                // Convert API response to viewer format
                this.viewers = {};
                data.dashboards.forEach(dashboard => {
                    if (dashboard.enabled) {
                        // Use dashboard.id as the key (e.g., "3DPlotly", "3DVTK")
                        const dashboardId = dashboard.id;
                        // Ensure url_template is set correctly
                        let urlTemplate = dashboard.url_template;
                        if (!urlTemplate && dashboard.nginx_path) {
                            urlTemplate = dashboard.nginx_path + '?uuid={uuid}&server={server}&name={name}';
                        }
                        
                        this.viewers[dashboardId] = {
                            id: dashboardId,
                            name: dashboard.display_name || dashboard.name,
                            type: dashboard.type || dashboardId, // Use type for compatibility, fallback to id
                            url_template: urlTemplate,
                            supported_formats: [], // Will be determined from dataset type
                            description: dashboard.description || dashboard.display_name,
                            nginx_path: dashboard.nginx_path,
                            port: dashboard.port
                        };
                    }
                });
                
                // No need to merge defaults - all dashboards should come from API
                // This prevents duplicates
                
                console.log('✅ Loaded dashboards from API:', Object.keys(this.viewers).length, 'dashboards:', Object.keys(this.viewers));
                console.log('✅ Dashboard IDs:', Object.keys(this.viewers));
            } else {
                console.warn('⚠️ Invalid dashboard API response:', data);
                if (!data.success) {
                    console.error('❌ API returned success=false:', data.error || 'Unknown error');
                }
                if (!data.dashboards) {
                    console.error('❌ data.dashboards is missing');
                } else if (!Array.isArray(data.dashboards)) {
                    console.error('❌ data.dashboards is not an array, type:', typeof data.dashboards);
                } else if (data.dashboards.length === 0) {
                    console.error('❌ data.dashboards array is empty');
                }
                this.viewers = {};
            }
            
            // Always populate the selector, even if empty
            console.log('📋 Calling populateViewerSelector() with', Object.keys(this.viewers).length, 'viewers...');
            this.populateViewerSelector();
            console.log('✅ populateViewerSelector() completed');
            
        } catch (error) {
            console.error('❌ Error loading dashboards:', error);
            console.error('Error details:', error.message, error.stack);
            // Fallback to default viewers
            this.viewers = this.defaultViewers;
            console.log('📋 Calling populateViewerSelector() after error...');
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
        
        // Clear existing options
        viewerType.innerHTML = '';
        
        // Check if we have any viewers loaded
        const viewerCount = Object.keys(this.viewers).length;
        console.log('Populating viewer selector with', viewerCount, 'viewer(s)');
        
        if (viewerCount === 0) {
            // No dashboards loaded - show error message
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No dashboards available';
            option.disabled = true;
            viewerType.appendChild(option);
            console.warn('No dashboards available to populate selector');
            return;
        }
        
        // Add options from loaded viewers
        // Use dashboard id as value for consistency
        Object.entries(this.viewers).forEach(([viewerKey, viewer]) => {
            const option = document.createElement('option');
            // Use id if available, otherwise use the key or type
            option.value = viewer.id || viewerKey || viewer.type;
            option.textContent = viewer.name || viewer.id || viewerKey;
            viewerType.appendChild(option);
            console.log('Added dashboard option:', option.value, '-', option.textContent);
        });
        
        // Set default viewer if available
        if (viewerType.options.length > 0) {
            viewerType.value = viewerType.options[0].value;
            console.log('Set default dashboard to:', viewerType.value);
        }
        
        console.log('✅ Populated viewer selector with', viewerType.options.length, 'dashboards');
    }

    /**
     * Update the viewer toolbar selector to match the selected dashboard
     * @param {string} dashboardId - The dashboard ID to set in the selector
     */
    updateViewerSelector(dashboardId) {
        // Store the current dashboard type
        this.currentDashboard = dashboardId;
        
        const viewerType = document.getElementById('viewerType');
        if (!viewerType || !dashboardId) {
            return;
        }

        // Try to find an option that matches the dashboard ID
        // Check by value, id, or case-insensitive match
        const normalizedId = dashboardId.toLowerCase();
        let matchingOption = null;

        // First, try exact match
        matchingOption = Array.from(viewerType.options).find(opt => 
            opt.value === dashboardId || opt.value.toLowerCase() === normalizedId
        );

        // If not found, try matching by dashboard ID in viewerManager
        if (!matchingOption && window.viewerManager && window.viewerManager.viewers) {
            const viewer = window.viewerManager.viewers[dashboardId];
            if (viewer) {
                // Try to find by viewer id or type
                matchingOption = Array.from(viewerType.options).find(opt => {
                    const optValue = opt.value.toLowerCase();
                    const viewerId = (viewer.id || '').toLowerCase();
                    const viewerType = (viewer.type || '').toLowerCase();
                    return optValue === viewerId || optValue === viewerType || optValue === normalizedId;
                });
            }
        }

        // If still not found, try case-insensitive partial match
        if (!matchingOption) {
            matchingOption = Array.from(viewerType.options).find(opt => {
                const optValue = opt.value.toLowerCase();
                return optValue.includes(normalizedId) || normalizedId.includes(optValue);
            });
        }

        if (matchingOption) {
            viewerType.value = matchingOption.value;
            console.log(`✅ Updated viewer-toolbar selector to: ${matchingOption.value} (from auto-detected: ${dashboardId})`);
        } else {
            console.warn(`⚠️ Could not find viewer-toolbar option for auto-detected dashboard: ${dashboardId}`);
            console.log('Available options:', Array.from(viewerType.options).map(opt => opt.value));
        }
    }

    /**
     * Initialize the viewer manager
     */
    async initialize() {
        console.log('🔧 ViewerManager.initialize() called');
        try {
            this.setupEventListeners();
            console.log('📡 Calling loadDashboards()...');
            await this.loadDashboards(); // Load dashboards from API first
            console.log('✅ loadDashboards() completed');
            this.loadViewerSettings();
        } catch (error) {
            console.error('❌ Error in ViewerManager.initialize():', error);
            // Ensure selector is populated even on error
            this.populateViewerSelector();
        }
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
            viewerType: (document.getElementById('viewerType') && document.getElementById('viewerType').value) || 'OpenVisusSlice',
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
    async loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, dashboardType = 'OpenVisusSlice', triedDashboards = new Set()) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Validate dashboardType - it should be a dashboard ID, not a dataset name
        // If dashboardType looks like a dataset name (contains spaces, is too long, etc.), use default
        if (!dashboardType || 
            dashboardType === datasetName || 
            dashboardType.length > 50 || 
            (dashboardType.includes(' ') && !this.viewers[dashboardType])) {
            console.warn(`⚠️ Invalid dashboardType detected: "${dashboardType}" (looks like dataset name: "${datasetName}"). Using default.`);
            dashboardType = 'OpenVisusSlice';
        }
        
        // Ensure dashboardType exists in viewers
        if (!this.viewers[dashboardType]) {
            console.warn(`⚠️ Dashboard "${dashboardType}" not found in viewers. Available: ${Object.keys(this.viewers).join(', ')}. Using default.`);
            dashboardType = Object.keys(this.viewers)[0] || 'OpenVisusSlice';
        }

        // Create a unique key for this load operation
        const loadKey = `${datasetId}-${dashboardType}`;
        
        // If we're loading a different dataset, clear the loading state and viewer container first
        if (this.isLoading && this.currentLoadingKey && !this.currentLoadingKey.startsWith(datasetId)) {
            const previousDatasetId = this.currentLoadingKey.split('-')[0];
            console.log(`🔄 Switching from dataset ${previousDatasetId} to ${datasetId}, clearing previous load`);
            // Clear the viewer container to stop the old dashboard from loading
            if (viewerContainer) {
                viewerContainer.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <h5 class="mt-3">Switching Dataset</h5>
                        <p class="text-muted">Loading ${datasetName}...</p>
                    </div>
                `;
            }
            this.isLoading = false;
            this.currentLoadingKey = null;
        }
        
        // Prevent double loading - if we're already loading the same dashboard, skip
        if (this.isLoading && this.currentLoadingKey === loadKey) {
            console.log(`⏭️ Already loading ${dashboardType} for dataset ${datasetId}, skipping duplicate request`);
            return;
        }

        // Prevent infinite loops by tracking which dashboards we've already tried
        if (triedDashboards.has(dashboardType)) {
            console.error(`❌ Already tried dashboard ${dashboardType}, preventing infinite loop`);
            this.showErrorDashboard('No compatible dashboard found for this dataset');
            return;
        }
        triedDashboards.add(dashboardType);
        
        // Set loading flag
        this.isLoading = true;
        this.currentLoadingKey = loadKey;

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
            // Check if dataset is ready (pass dashboard type for proper status check)
            const status = await this.checkDatasetStatus(datasetId, dashboardType);
            
            if (status === 'ready') {
                // Update toolbar selector to match the dashboard being loaded
                this.updateViewerSelector(dashboardType);
                
                // Load the dashboard
                try {
                    await this.loadDashboardContent(datasetId, datasetName, datasetUuid, datasetServer, dashboardType);
                } finally {
                    // Clear loading flag after loadDashboardContent completes (success or error)
                    this.isLoading = false;
                    this.currentLoadingKey = null;
                }
            } else if (status === 'processing') {
                this.showProcessingDashboard(datasetId, datasetName);
                // Clear loading flag
                this.isLoading = false;
                this.currentLoadingKey = null;
            } else if (status === 'unsupported') {
                // Instead of showing error, automatically find and load a compatible dashboard
                console.log(`⚠️ Dashboard ${dashboardType} is not supported for this dataset. Automatically selecting compatible dashboard...`);
                
                // Use smart dashboard selection to find a compatible dashboard
                if (window.datasetManager && window.datasetManager.selectDashboardForDataset) {
                    try {
                        // Get preferred dashboard from current dataset if available
                        const preferredDashboard = window.datasetManager.currentDataset?.preferred_dashboard || null;
                        
                        // Automatically select the best compatible dashboard
                        // selectDashboardForDataset returns a dashboard ID (string)
                        const selectedDashboardId = await window.datasetManager.selectDashboardForDataset(
                            datasetId,
                            datasetUuid,
                            preferredDashboard
                        );
                        
                        if (selectedDashboardId && typeof selectedDashboardId === 'string') {
                            console.log(`✅ Auto-selected compatible dashboard: ${selectedDashboardId}`);
                            // Update toolbar selector to match the auto-selected dashboard
                            this.updateViewerSelector(selectedDashboardId);
                            
                            // Recursively load the selected dashboard (pass triedDashboards to prevent loops)
                            if (selectedDashboardId !== dashboardType) {
                                // Clear current loading flag before recursive call
                                this.isLoading = false;
                                this.currentLoadingKey = null;
                                await this.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, selectedDashboardId, triedDashboards);
                            } else {
                                // If we somehow got the same dashboard, show error
                                this.isLoading = false;
                                this.currentLoadingKey = null;
                                this.showErrorDashboard('No compatible dashboard found for this dataset');
                            }
                        } else {
                            console.error('❌ No compatible dashboard found');
                            this.isLoading = false;
                            this.currentLoadingKey = null;
                            this.showErrorDashboard('No compatible dashboard found for this dataset');
                        }
                    } catch (selectionError) {
                        console.error('Error selecting compatible dashboard:', selectionError);
                        this.isLoading = false;
                        this.currentLoadingKey = null;
                        this.showErrorDashboard('Failed to find compatible dashboard');
                    }
                } else {
                    // Fallback if datasetManager is not available
                    console.error('DatasetManager not available for smart dashboard selection');
                    this.isLoading = false;
                    this.currentLoadingKey = null;
                    this.showErrorDashboard('Dashboard not available and cannot auto-select alternative');
                }
            } else {
                this.isLoading = false;
                this.currentLoadingKey = null;
                this.showErrorDashboard('Unknown error occurred');
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.isLoading = false;
            this.currentLoadingKey = null;
            this.showErrorDashboard('Failed to load dashboard');
        }
    }

    /**
     * Check dataset status
     */
    async checkDatasetStatus(datasetId, dashboardType = null) {
        try {
            // Helper function to get API base path
            const getApiBasePath = () => {
                const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                return isLocal ? '/api' : '/portal/api';
            };
            let url = `${getApiBasePath()}/dataset-status.php?dataset_id=${datasetId}`;
            if (dashboardType) {
                url += `&dashboard=${encodeURIComponent(dashboardType)}`;
            }
            const response = await fetch(url, {
                credentials: 'include'  // Include cookies for authentication
            });
            
            // Handle authentication errors
            if (response.status === 401) {
                console.error('Authentication required for dataset status check');
                return 'error';
            }
            
            if (!response.ok) {
                console.error(`Error checking dataset status: ${response.status} ${response.statusText}`);
                return 'error';
            }
            
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

        // Map common aliases to actual dashboard IDs
        // Note: 'openvisus' is kept as a separate fallback viewer, but aliases map to 'OpenVisusSlice' from API
        // Also map old dashboard names to new ones for backwards compatibility
        const dashboardAliases = {
            'openvisus': 'OpenVisusSlice',  // Map lowercase alias to the API dashboard
            'OpenVisus': 'OpenVisusSlice',
            'openvisusslice': 'OpenVisusSlice',
            // Map old dashboard names to new ones
            '4D_Dashboard': '4d_dashboardLite',  // Old 4D dashboard -> new one
            '4d_dashboard': '4d_dashboardLite',  // Alternative spelling
            '4D_dashboard': '4d_dashboardLite',
            'Magicscan': 'magicscan',  // Normalize case
            'magicscan': 'magicscan'
        };
        
        // Resolve dashboard type to actual ID
        let resolvedDashboardType = dashboardAliases[dashboardType] || dashboardType;
        
        // Store the current dashboard type for reference (e.g., for copy dashboard link)
        this.currentDashboard = resolvedDashboardType;
        
        // Find viewer by id, type, or key (try multiple lookup strategies)
        let viewer = this.viewers[resolvedDashboardType] || this.viewers[dashboardType];
        
        if (!viewer) {
            // Try to find by matching id or type (case-insensitive)
            const normalizedType = resolvedDashboardType.toLowerCase();
            viewer = Object.values(this.viewers).find(v => {
                const vId = (v.id || '').toLowerCase();
                const vType = (v.type || '').toLowerCase();
                return vId === normalizedType || 
                       vType === normalizedType ||
                       vId === dashboardType.toLowerCase() ||
                       vType === dashboardType.toLowerCase();
            });
        }
        
        // Fallback to default viewers if not found
        if (!viewer) {
            viewer = this.defaultViewers[resolvedDashboardType] || this.defaultViewers[dashboardType];
        }
        
        // If still not found, try smart selection based on dataset dimension
        if (!viewer && datasetUuid) {
            console.warn(`⚠️ Dashboard "${dashboardType}" not found, attempting smart selection based on dataset dimension...`);
            try {
                // Use smart selection to find a compatible dashboard
                if (window.datasetManager && typeof window.datasetManager.selectDashboardForDataset === 'function') {
                    const smartSelected = await window.datasetManager.selectDashboardForDataset(
                        datasetId || datasetUuid, 
                        datasetUuid, 
                        null  // Don't use preference since it's invalid
                    );
                    if (smartSelected && this.viewers[smartSelected]) {
                        console.log(`✅ Smart selection found compatible dashboard: ${smartSelected}`);
                        viewer = this.viewers[smartSelected];
                        // Update dashboardType and resolvedDashboardType for the rest of the function
                        dashboardType = smartSelected;
                        resolvedDashboardType = smartSelected;
                        // Update toolbar selector to match the smart-selected dashboard
                        this.updateViewerSelector(smartSelected);
                    }
                }
            } catch (smartError) {
                console.warn('Smart selection failed:', smartError);
            }
        }
        
        if (!viewer) {
            console.error('Unknown dashboard type:', dashboardType, 'Resolved:', resolvedDashboardType, 'Available viewers:', Object.keys(this.viewers));
            this.showErrorDashboard('Unknown dashboard type: ' + dashboardType);
            return;
        }

        // Validate url_template exists
        if (!viewer.url_template) {
            console.error('Viewer missing url_template:', viewer, 'Dashboard type:', dashboardType);
            // Try to construct from nginx_path
            if (viewer.nginx_path) {
                viewer.url_template = viewer.nginx_path + '?uuid={uuid}&server={server}&name={name}';
            } else if (viewer.id || resolvedDashboardType) {
                // Fallback: construct from dashboard ID
                const dashboardId = viewer.id || resolvedDashboardType;
                viewer.url_template = '/dashboard/' + dashboardId.toLowerCase().replace(/_/g, '') + '?uuid={uuid}&server={server}&name={name}';
                console.warn('Constructed url_template from dashboard ID:', viewer.url_template);
            } else {
                this.showErrorDashboard('Dashboard configuration error: missing URL template');
                return;
            }
        }

        // Ensure url_template is a valid string
        if (typeof viewer.url_template !== 'string' || viewer.url_template.trim() === '') {
            console.error('Invalid url_template:', viewer.url_template);
            this.showErrorDashboard('Dashboard configuration error: invalid URL template');
            return;
        }

        // Generate viewer URL using the url_template
        const viewerUrl = this.generateViewerUrl(datasetUuid, datasetServer, datasetName, viewer.url_template);
        
        console.log('Loading dashboard:', {
            dashboardType,
            resolvedDashboardType,
            viewerId: viewer.id,
            viewerName: viewer.name,
            urlTemplate: viewer.url_template,
            generatedUrl: viewerUrl
        });
        
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
        
        const dashboardContent = document.createElement('div');
        dashboardContent.className = 'dashboard-content';
        dashboardContent.appendChild(iframe);
        
        dashboardContainer.appendChild(dashboardContent);
        
        viewerContainer.innerHTML = '';
        viewerContainer.appendChild(dashboardContainer);
    }

    /**
     * Generate viewer URL with uuid, server, and name parameters
     */
    generateViewerUrl(datasetUuid, datasetServer, datasetName, urlTemplate) {
        if (!urlTemplate || typeof urlTemplate !== 'string') {
            console.error('generateViewerUrl: urlTemplate is empty or invalid:', urlTemplate);
            return '#';
        }
        
        // Trim whitespace
        urlTemplate = urlTemplate.trim();
        
        // Detect local development mode
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        // Get current theme from AppState or localStorage (declare once at function start)
        const currentTheme = window.AppState?.theme || localStorage.getItem('theme') || 'dark';
        
        // If urlTemplate doesn't start with / or http, it's likely just an ID - construct proper path
        if (!urlTemplate.startsWith('/') && !urlTemplate.startsWith('http')) {
            console.warn('generateViewerUrl: urlTemplate appears to be just an ID, constructing path:', urlTemplate);
            // Convert to lowercase and replace underscores/dashes with nothing for URL path
            const pathId = urlTemplate.toLowerCase().replace(/[_-]/g, '');
            urlTemplate = '/dashboard/' + pathId + '?uuid={uuid}&server={server}&name={name}';
        }
        
        // Replace all three placeholders: {uuid}, {server}, {name}
        let url = urlTemplate
            .replace(/{uuid}/g, encodeURIComponent(datasetUuid))
            .replace(/{server}/g, encodeURIComponent(datasetServer || 'false'))
            .replace(/{name}/g, encodeURIComponent(datasetName || ''));
        
        // For local development, convert /dashboard/ paths to direct port access
        if (isLocal && url.startsWith('/dashboard/')) {
            // Get the dashboard name from the URL path (e.g., /dashboard/OpenVisusSlice/?uuid=...)
            const match = url.match(/\/dashboard\/([^/?]+)/);
            const dashboardPathName = match?.[1];
            
            if (dashboardPathName && this.viewers) {
                // Find the dashboard by matching:
                // 1. Exact ID match (case-insensitive)
                // 2. nginx_path contains the path name
                // 3. Name contains the path name
                const dashboard = Object.values(this.viewers).find(v => {
                    const vId = (v.id || '').toLowerCase();
                    const vNginxPath = (v.nginx_path || '').toLowerCase();
                    const vName = (v.name || '').toLowerCase();
                    const pathNameLower = dashboardPathName.toLowerCase();
                    
                    return vId === pathNameLower ||
                           vNginxPath.includes(pathNameLower) ||
                           vNginxPath.endsWith('/' + pathNameLower) ||
                           vName.includes(pathNameLower);
                });
                
                if (dashboard && dashboard.port) {
                    // Extract the path after /dashboard/name
                    // For OpenVisusSlice, the app expects /OpenVisusSlice/?uuid=...
                    // So we need to construct: http://localhost:PORT/OpenVisusSlice/?uuid=...
                    const pathAfterDashboard = url.replace(/^\/dashboard\/[^/?]+/, '');
                    // Use the dashboard ID as the app path (e.g., /OpenVisusSlice/)
                    const appPath = '/' + dashboard.id + (pathAfterDashboard || '/');
                    url = `http://localhost:${dashboard.port}${appPath}`;
                    console.log(`Local dev: Using direct port access for ${dashboard.id}: ${url}`);
                } else {
                    console.warn(`Local dev: Could not find dashboard for path "${dashboardPathName}". Available:`, Object.keys(this.viewers));
                }
            }
        }
        
        // Add theme parameter to URL to help dashboards adapt to dark/light mode
        // Check if URL already has query parameters
        const separator = url.includes('?') ? '&' : '?';
        // Use currentTheme already declared at function start (line 692)
        url += `${separator}theme=${encodeURIComponent(currentTheme)}`;
        
        return url;
    }


    /**
     * Show processing dashboard
     */
    showProcessingDashboard(datasetId, datasetName) {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        viewerContainer.innerHTML = `
            <div class="dashboard-container">
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
            // Helper function to get API base path
            const getApiBasePath = () => {
                const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                return isLocal ? '/api' : '/portal/api';
            };
            const response = await fetch(`${getApiBasePath()}/dataset-status.php?dataset_id=${datasetId}`, {
                credentials: 'include'  // Include cookies for authentication
            });
            
            if (!response.ok) {
                console.error(`Error checking dataset status: ${response.status} ${response.statusText}`);
                return;
            }
            
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
    console.log('🚀 DOMContentLoaded: Initializing ViewerManager...');
    console.log('🚀 Document ready state:', document.readyState);
    console.log('🚀 Current URL:', window.location.href);
    
    // Check if viewerType element exists
    const viewerType = document.getElementById('viewerType');
    if (!viewerType) {
        console.error('❌ viewerType element not found in DOM!');
        console.error('❌ Available elements with id:', Array.from(document.querySelectorAll('[id]')).map(el => el.id));
        return;
    }
    console.log('✅ viewerType element found:', viewerType);
    console.log('✅ viewerType current value:', viewerType.value);
    console.log('✅ viewerType current options:', viewerType.options.length);
    
    try {
        console.log('🔧 Creating ViewerManager instance...');
        window.viewerManager = new ViewerManager();
        console.log('✅ ViewerManager instance created:', window.viewerManager);
        
        // Fallback: If dashboards aren't loaded after 5 seconds, try again and show error
        setTimeout(() => {
            const checkViewerType = document.getElementById('viewerType');
            if (checkViewerType && checkViewerType.options.length <= 1) {
                const firstOption = checkViewerType.options[0];
                if (firstOption && (firstOption.textContent.includes('Loading') || firstOption.value === '')) {
                    console.warn('⚠️ Dashboards still not loaded after 5 seconds, retrying...');
                    if (window.viewerManager && typeof window.viewerManager.loadDashboards === 'function') {
                        window.viewerManager.loadDashboards().catch(err => {
                            console.error('❌ Retry failed:', err);
                            // Show error in selector
                            checkViewerType.innerHTML = '<option value="">Error: Could not load dashboards</option>';
                        });
                    } else {
                        console.error('❌ viewerManager or loadDashboards not available');
                        checkViewerType.innerHTML = '<option value="">Error: ViewerManager not initialized</option>';
                    }
                }
            }
        }, 5000);
    } catch (error) {
        console.error('❌ Failed to create ViewerManager:', error);
        console.error('Error stack:', error.stack);
        // Try to populate selector with fallback even if initialization fails
        if (viewerType) {
            viewerType.innerHTML = '<option value="">Error loading dashboards</option>';
        }
    }
});

// Also try to initialize immediately if DOM is already loaded (in case script loads after DOMContentLoaded)
if (document.readyState === 'loading') {
    // DOM is still loading, wait for DOMContentLoaded (handled above)
    console.log('⏳ DOM still loading, waiting for DOMContentLoaded...');
} else {
    // DOM is already loaded, initialize immediately
    console.log('✅ DOM already loaded, initializing ViewerManager immediately...');
    try {
        const viewerType = document.getElementById('viewerType');
        if (viewerType) {
            console.log('✅ viewerType element found (immediate init)');
            if (!window.viewerManager) {
                window.viewerManager = new ViewerManager();
                console.log('✅ ViewerManager instance created (immediate init)');
            } else {
                console.log('✅ ViewerManager already exists, calling loadDashboards()...');
                window.viewerManager.loadDashboards().catch(err => {
                    console.error('❌ loadDashboards failed:', err);
                });
            }
        } else {
            console.warn('⚠️ viewerType element not found (immediate init)');
        }
    } catch (error) {
        console.error('❌ Failed to create ViewerManager (immediate init):', error);
        console.error('Error details:', error.message, error.stack);
    }
}

// Fallback: If ViewerManager didn't initialize, try to manually load dashboards after a delay
setTimeout(function() {
    const viewerType = document.getElementById('viewerType');
    if (viewerType && viewerType.options.length <= 1 && viewerType.options[0]?.textContent.includes('Loading')) {
        console.warn('⚠️ Fallback: ViewerManager may not have initialized, manually loading dashboards...');
        
        // Helper function to get API base path
        const getApiBasePath = () => {
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            return isLocal ? '/api' : '/portal/api';
        };
        
        // Manually fetch and populate
        fetch(`${getApiBasePath()}/dashboards.php`, { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.dashboards) {
                    viewerType.innerHTML = '';
                    data.dashboards.forEach(dashboard => {
                        if (dashboard.enabled) {
                            const option = document.createElement('option');
                            option.value = dashboard.id;
                            option.textContent = dashboard.display_name || dashboard.name;
                            viewerType.appendChild(option);
                        }
                    });
                    if (viewerType.options.length > 0) {
                        viewerType.value = viewerType.options[0].value;
                    }
                    console.log('✅ Fallback: Manually populated', viewerType.options.length, 'dashboards');
                }
            })
            .catch(err => {
                console.error('❌ Fallback: Failed to load dashboards:', err);
                viewerType.innerHTML = '<option value="">Error loading dashboards</option>';
            });
    }
}, 2000);

// Export functions for global access
// Legacy function - use viewerManager.loadDashboard instead
// This function signature is incorrect - it should take (datasetId, datasetName, datasetUuid, datasetServer, dashboardType)
// WARNING: This function is deprecated. Use datasetManager.selectDataset() or viewerManager.loadDashboard() instead.
window.loadDashboard = function(datasetId, dashboardType) {
    console.warn('⚠️ Using legacy loadDashboard function. This may have incorrect parameters.');
    console.warn('⚠️ Consider using datasetManager.selectDataset() or viewerManager.loadDashboard() instead.');
    
    // Validate parameters - if dashboardType looks like a dataset name, it's probably wrong
    if (dashboardType && (dashboardType.length > 50 || dashboardType.includes(' '))) {
        console.error('❌ Invalid dashboardType detected in legacy loadDashboard:', dashboardType);
        console.error('❌ This looks like a dataset name, not a dashboard ID. Ignoring this call.');
        return;
    }
    
    // Try to get dataset info from currentDataset if available
    if (window.datasetManager && window.datasetManager.currentDataset) {
        const dataset = window.datasetManager.currentDataset;
        // Only proceed if the datasetId matches the current dataset
        if (datasetId === dataset.id || datasetId === dataset.uuid) {
            if (window.viewerManager) {
                window.viewerManager.loadDashboard(
                    dataset.id,
                    dataset.name || 'Dataset',
                    dataset.uuid || datasetId,
                    dataset.server || 'false',
                    dashboardType || 'OpenVisusSlice'
                );
            }
        } else {
            console.warn('⚠️ Legacy loadDashboard called with different datasetId than currentDataset. Ignoring.');
        }
    } else {
        // Fallback - use default values, but only if dashboardType is valid
        if (window.viewerManager && dashboardType && !dashboardType.includes(' ')) {
            window.viewerManager.loadDashboard(datasetId, 'Dataset', datasetId, 'false', dashboardType);
        } else {
            console.warn('⚠️ Legacy loadDashboard called without valid parameters. Ignoring.');
        }
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
