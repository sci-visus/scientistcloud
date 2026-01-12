/**
 * ScientistCloud Data Portal - Main JavaScript
 * Handles UI interactions and theme management
 */

// Helper function to get API base path (detects local vs server)
function getApiBasePath() {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    return isLocal ? '/api' : '/portal/api';
}

/**
 * Format file size from GB (as stored in database) to human-readable format
 * data_size is stored in GB (float), but formatFileSize expects bytes
 */
function formatFileSizeFromGb(sizeGb) {
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

// Global state
const AppState = {
    currentDataset: null,
    currentDashboard: null,
    theme: localStorage.getItem('theme') || 'light',
    sidebarCollapsed: false,
    detailsCollapsed: false
};

// Initialize application with error handling
document.addEventListener('DOMContentLoaded', function() {
    try {
        console.log('🚀 DOMContentLoaded - Starting initialization...');
        initializeApp();
        setupEventListeners();
        loadTheme();
        console.log('✅ Initialization complete');
    } catch (error) {
        console.error('❌ Fatal error during initialization:', error);
        console.error('Stack trace:', error.stack);
        // Show error to user
        if (window.showError) {
            window.showError('Failed to initialize portal: ' + error.message);
        } else {
            alert('Failed to initialize portal: ' + error.message);
        }
    }
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('Initializing ScientistCloud Data Portal...');
    
    // Set initial theme
    if (AppState.theme === 'light') {
        document.body.classList.add('light-theme');
    }
    
    // Initialize sidebar collapse states
    AppState.sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    AppState.detailsCollapsed = localStorage.getItem('detailsCollapsed') === 'true';
    
    if (AppState.sidebarCollapsed) {
        document.getElementById('folderSidebar').classList.add('collapsed');
        document.getElementById('toggleFolder').innerHTML = '&#9654;';
    }
    
    if (AppState.detailsCollapsed) {
        const details = document.getElementById('detailSidebar');
        const resizeHandleRight = document.getElementById('resizeHandleRight');
        details.classList.add('collapsed');
        document.getElementById('toggleDetail').innerHTML = '&#9664;';
        if (resizeHandleRight) {
            resizeHandleRight.style.display = 'none';
        }
    }
    
    // Load saved sidebar widths
    loadSidebarWidths();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    try {
        // Sidebar toggle
        const toggleFolder = document.getElementById('toggleFolder');
        if (toggleFolder) {
            toggleFolder.addEventListener('click', toggleSidebar);
            console.log('✅ Sidebar toggle listener attached');
        } else {
            console.warn('⚠️ toggleFolder button not found');
        }
        
        // Details sidebar toggle
        const toggleDetail = document.getElementById('toggleDetail');
        if (toggleDetail) {
            toggleDetail.addEventListener('click', toggleDetails);
            console.log('✅ Details toggle listener attached');
        } else {
            console.warn('⚠️ toggleDetail button not found');
        }
        
        // Theme toggle
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                try {
                    toggleTheme();
                } catch (error) {
                    console.error('❌ Error in theme toggle:', error);
                    if (window.showError) {
                        window.showError('Failed to toggle theme: ' + error.message);
                    }
                }
            });
            console.log('✅ Theme toggle button event listener attached');
            
            // Set initial icon based on current theme
            if (AppState.theme === 'light') {
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>'; // Moon icon for light mode
            } else {
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>'; // Sun icon for dark mode
            }
        } else {
            console.warn('⚠️ themeToggle button not found');
        }
    
        // Initialize resize handles
        initializeResizeHandles();
        
        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function() {
                // Determine logout path based on current URL path
                // If we're at /portal/index.php, use /portal/logout.php
                // Otherwise use /logout.php
                const currentPath = window.location.pathname;
                const logoutPath = currentPath.includes('/portal/') ? '/portal/logout.php' : '/logout.php';
                window.location.href = logoutPath;
            });
        }
        
        // Dataset selection - ONLY handle if datasetManager is not available
        // dataset-manager.js already has its own handler, so we avoid duplicate processing
        document.addEventListener('click', function(e) {
        if (e.target.closest('.dataset-link')) {
            // If datasetManager exists and has handleDatasetClick, let it handle everything
            // Only use main.js handler as absolute fallback
            if (!window.datasetManager) {
                e.preventDefault();
                handleDatasetSelection(e.target.closest('.dataset-link'));
            }
            // Otherwise, dataset-manager.js will handle it via its own event listener
        }
    });
    
    // Viewer type change
    const viewerType = document.getElementById('viewerType');
    if (viewerType) {
        viewerType.addEventListener('change', handleViewerTypeChange);
    }
    
    // Handle collapse/expand for folders
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(function(trigger) {
        trigger.addEventListener('click', function() {
            const target = document.querySelector(this.dataset.bsTarget);
            const arrow = document.querySelector('#arrow-' + this.dataset.bsTarget.replace('#', ''));
            
            if (target && arrow) {
                target.addEventListener('show.bs.collapse', function() {
                    arrow.classList.add('open');
                });
                target.addEventListener('hide.bs.collapse', function() {
                    arrow.classList.remove('open');
                });
            }
        });
    });
    
    // Quick action buttons (from welcome screen) - use event delegation
    // These buttons should trigger the same actions as the toolbar buttons
    document.addEventListener('click', function(e) {
        // Upload button - trigger upload manager
        if (e.target && (e.target.id === 'quickUploadBtn' || e.target.closest('#quickUploadBtn'))) {
            e.preventDefault();
            e.stopPropagation();
            if (window.uploadManager) {
                window.uploadManager.showUploadInterface();
            } else {
                // Fallback: try to click the toolbar button
                const uploadBtn = document.getElementById('uploadDatasetBtn');
                if (uploadBtn) {
                    uploadBtn.click();
                } else {
                    console.warn('Upload manager and button not found');
                }
            }
        }
        
        // View Jobs button - trigger job manager
        if (e.target && (e.target.id === 'quickViewJobsBtn' || e.target.closest('#quickViewJobsBtn'))) {
            e.preventDefault();
            e.stopPropagation();
            if (window.jobManager) {
                window.jobManager.showJobsInterface();
            } else {
                // Fallback: try to click the toolbar button
                const viewJobsBtn = document.getElementById('viewJobsBtn');
                if (viewJobsBtn) {
                    viewJobsBtn.click();
                } else {
                    console.warn('Job manager and button not found');
                }
            }
        }
        
        // Create Team button - trigger upload manager
        if (e.target && (e.target.id === 'quickCreateTeamBtn' || e.target.closest('#quickCreateTeamBtn'))) {
            e.preventDefault();
            e.stopPropagation();
            if (window.uploadManager) {
                window.uploadManager.showCreateTeamInterface();
            } else {
                // Fallback: try to click the toolbar button
                const createTeamBtn = document.getElementById('createTeamBtn');
                if (createTeamBtn) {
                    createTeamBtn.click();
                } else {
                    console.warn('Upload manager and create team button not found');
                }
            }
        }
        
        // Settings button
        if (e.target && (e.target.id === 'quickSettingsBtn' || e.target.closest('#quickSettingsBtn'))) {
            e.preventDefault();
            e.stopPropagation();
            const settingsBtn = document.getElementById('settingsBtn');
            if (settingsBtn && !settingsBtn.disabled) {
                // Settings not implemented yet
                alert('Settings feature coming soon!');
            } else if (settingsBtn && settingsBtn.disabled) {
                alert('Settings feature is not yet available');
            }
        }
    });
    } catch (error) {
        console.error('❌ Error setting up event listeners:', error);
        if (window.showError) {
            window.showError('Failed to set up event listeners: ' + error.message);
        }
    }
}

/**
 * Toggle sidebar
 */
function toggleSidebar() {
    const sidebar = document.getElementById('folderSidebar');
    const button = document.getElementById('toggleFolder');
    const resizeHandleLeft = document.getElementById('resizeHandleLeft');
    
    sidebar.classList.toggle('collapsed');
    AppState.sidebarCollapsed = sidebar.classList.contains('collapsed');
    
    // Hide/show resize handle (CSS handles this, but ensure it's hidden)
    if (resizeHandleLeft) {
        resizeHandleLeft.style.display = AppState.sidebarCollapsed ? 'none' : 'block';
    }
    
    if (AppState.sidebarCollapsed) {
        button.innerHTML = '&#9654;';
    } else {
        button.innerHTML = '&#9664;';
    }
    
    localStorage.setItem('sidebarCollapsed', AppState.sidebarCollapsed);
}

/**
 * Toggle details sidebar
 */
function toggleDetails() {
    const details = document.getElementById('detailSidebar');
    const button = document.getElementById('toggleDetail');
    const resizeHandleRight = document.getElementById('resizeHandleRight');
    
    details.classList.toggle('collapsed');
    AppState.detailsCollapsed = details.classList.contains('collapsed');
    
    // Hide/show resize handle
    if (resizeHandleRight) {
        resizeHandleRight.style.display = AppState.detailsCollapsed ? 'none' : 'block';
    }
    
    if (AppState.detailsCollapsed) {
        button.innerHTML = '&#9664;';
    } else {
        button.innerHTML = '&#9654;';
    }
    
    localStorage.setItem('detailsCollapsed', AppState.detailsCollapsed);
}

/**
 * Toggle theme
 */
function toggleTheme() {
    try {
        console.log('🎨 toggleTheme called, current theme:', AppState.theme);
        
        // Toggle theme state
        const oldTheme = AppState.theme;
        AppState.theme = AppState.theme === 'dark' ? 'light' : 'dark';
        
        // Toggle the light-theme class (light-theme = light mode, no class = dark mode)
        document.body.classList.toggle('light-theme');
        
        // Save to localStorage
        localStorage.setItem('theme', AppState.theme);
        
        // Update button icon/state
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            if (AppState.theme === 'light') {
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>'; // Moon icon for light mode (switch to dark)
            } else {
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>'; // Sun icon for dark mode (switch to light)
            }
            console.log('✅ Theme toggle button updated');
        } else {
            console.warn('⚠️ themeToggle button not found when toggling');
        }
        
        console.log('✅ Theme changed from', oldTheme, 'to', AppState.theme);
    } catch (error) {
        console.error('❌ Error in toggleTheme:', error);
        throw error; // Re-throw so caller can handle it
    }
}

/**
 * Load theme from localStorage
 */
function loadTheme() {
    if (AppState.theme === 'light') {
        document.body.classList.add('light-theme');
    }
}

/**
 * Handle dataset selection
 */
function handleDatasetSelection(datasetLink) {
    // If datasetManager is available, it handles everything - don't duplicate
    // The dataset-manager.js has its own click handler that will call handleDatasetSelection
    // So this function should only run as a fallback if datasetManager is not available
    if (window.datasetManager && typeof window.datasetManager.handleDatasetSelection === 'function') {
        // Let datasetManager handle it - it has its own event listener
        return;
    }
    
    const datasetId = datasetLink.dataset.datasetId;
    const datasetName = datasetLink.dataset.datasetName;
    const datasetUuid = datasetLink.dataset.datasetUuid;
    const datasetServer = datasetLink.dataset.datasetServer;
    
    // Update active state
    document.querySelectorAll('.dataset-link').forEach(function(link) {
        link.classList.remove('active');
    });
    datasetLink.classList.add('active');
    
    // Store current dataset
    AppState.currentDataset = {
        id: datasetId,
        name: datasetName,
        uuid: datasetUuid,
        server: datasetServer
    };
    
    // Load dataset details
    loadDatasetDetails(datasetId);
    
    // Use dataset manager's selectDataset method instead of direct loadDashboard
    // This ensures smart dashboard selection happens first
    if (window.datasetManager && typeof window.datasetManager.selectDataset === 'function') {
        window.datasetManager.selectDataset(datasetId, datasetName, datasetUuid, datasetServer);
    } else if (window.viewerManager && typeof window.viewerManager.loadDashboard === 'function') {
        // Fallback: use viewer manager directly with smart selection
        // First, let dataset manager do smart selection
        if (window.datasetManager && typeof window.datasetManager.selectDashboardForDataset === 'function') {
            window.datasetManager.selectDashboardForDataset(datasetId, datasetUuid, null)
                .then(selectedDashboard => {
                    if (window.viewerManager) {
                        window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, selectedDashboard);
                    }
                })
                .catch(error => {
                    console.error('Error in smart dashboard selection:', error);
                    // Fallback to default
                    if (window.viewerManager) {
                        window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
                    }
                });
        } else {
            // No smart selection available, use default
            window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
        }
    } else {
        // Last resort: use legacy loadDashboard
        loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
    }
    
    console.log('Dataset selected:', AppState.currentDataset);
}

/**
 * Load dataset details
 */
function loadDatasetDetails(datasetId) {
    const detailsContainer = document.getElementById('datasetDetails');
    if (!detailsContainer) return;
    
    // Show loading state
    detailsContainer.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading details...</p></div>';
    
    // Fetch dataset details
    fetch(`${getApiBasePath()}/dataset-details.php?dataset_id=${datasetId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayDatasetDetails(data.dataset);
            } else {
                displayErrorDetails(data.error);
            }
        })
        .catch(error => {
            console.error('Error loading dataset details:', error);
            displayErrorDetails('Failed to load dataset details');
        });
}

/**
 * Display dataset details
 */
function displayDatasetDetails(dataset) {
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
                    <span class="detail-value">${formatFileSizeFromGb(dataset.data_size)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Status:</span>
                    <span class="badge bg-${getStatusColor(dataset.status)}">${dataset.status}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Sensor:</span>
                    <span class="detail-value">${dataset.sensor}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Created:</span>
                    <span class="detail-value">${formatDate(dataset.created_at)}</span>
                </div>
                ${dataset.dimensions ? `
                <div class="detail-item">
                    <span class="detail-label">Dimensions:</span>
                    <span class="detail-value">${dataset.dimensions}</span>
                </div>
                ` : ''}
            </div>
            <div class="dataset-actions mt-3">
                <button class="btn btn-sm btn-primary" onclick="viewDataset('${dataset.id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="shareDataset('${dataset.id}')">
                    <i class="fas fa-share"></i> Share
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteDataset('${dataset.id}')">
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
function displayErrorDetails(error) {
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
// DEPRECATED: This function is kept for backwards compatibility but should not be used
// Use datasetManager.selectDataset() or viewerManager.loadDashboard() instead
function loadDashboard(datasetId, datasetName, datasetUuid, datasetServer) {
    console.warn('⚠️ Using deprecated loadDashboard function from main.js. Consider using datasetManager.selectDataset() instead.');
    
    // Redirect to use dataset manager if available
    if (window.datasetManager && typeof window.datasetManager.selectDataset === 'function') {
        console.log('✅ Redirecting to datasetManager.selectDataset()');
        window.datasetManager.selectDataset(datasetId, datasetName, datasetUuid, datasetServer);
        return;
    }
    
    // Fallback to viewer manager if dataset manager not available
    if (window.viewerManager && typeof window.viewerManager.loadDashboard === 'function') {
        console.log('✅ Using viewerManager.loadDashboard() as fallback');
        // Use smart selection if available
        if (window.datasetManager && typeof window.datasetManager.selectDashboardForDataset === 'function') {
            window.datasetManager.selectDashboardForDataset(datasetId, datasetUuid, null)
                .then(selectedDashboard => {
                    window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer, selectedDashboard);
                })
                .catch(error => {
                    console.error('Error in smart selection:', error);
                    window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
                });
        } else {
            window.viewerManager.loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
        }
        return;
    }
    
    // Last resort: old fetch-based method (deprecated)
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
    url.searchParams.set('dashboard', 'OpenVisusSlice'); // Default dashboard
    
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
 * Handle viewer type change
 */
function handleViewerTypeChange(event) {
    const viewerType = event.target.value;
    console.log('Viewer type changed to:', viewerType);
    
    // Update dashboard based on viewer type
    if (AppState.currentDataset) {
        // Use viewer manager directly with the selected viewer type
        if (window.viewerManager && typeof window.viewerManager.loadDashboard === 'function') {
            window.viewerManager.loadDashboard(
                AppState.currentDataset.id,
                AppState.currentDataset.name,
                AppState.currentDataset.uuid,
                AppState.currentDataset.server,
                viewerType
            );
        } else {
            // Use dataset manager if available
            if (window.datasetManager && typeof window.datasetManager.selectDataset === 'function') {
                window.datasetManager.selectDataset(
                    AppState.currentDataset.id,
                    AppState.currentDataset.name,
                    AppState.currentDataset.uuid,
                    AppState.currentDataset.server
                );
            } else if (window.viewerManager && typeof window.viewerManager.loadDashboard === 'function') {
                window.viewerManager.loadDashboard(
                    AppState.currentDataset.id,
                    AppState.currentDataset.name,
                    AppState.currentDataset.uuid,
                    AppState.currentDataset.server
                );
            } else {
                loadDashboard(AppState.currentDataset.id, AppState.currentDataset.name, AppState.currentDataset.uuid, AppState.currentDataset.server);
            }
        }
    }
}

/**
 * View dataset
 */
function viewDataset(datasetId) {
    if (AppState.currentDataset) {
        // Use dataset manager if available
        if (window.datasetManager && typeof window.datasetManager.selectDataset === 'function') {
            window.datasetManager.selectDataset(
                AppState.currentDataset.id,
                AppState.currentDataset.name,
                AppState.currentDataset.uuid,
                AppState.currentDataset.server
            );
        } else if (window.viewerManager && typeof window.viewerManager.loadDashboard === 'function') {
            window.viewerManager.loadDashboard(
                AppState.currentDataset.id,
                AppState.currentDataset.name,
                AppState.currentDataset.uuid,
                AppState.currentDataset.server
            );
        } else {
            loadDashboard(AppState.currentDataset.id, AppState.currentDataset.name, AppState.currentDataset.uuid, AppState.currentDataset.server);
        }
    }
}

/**
 * Share dataset
 */
function shareDataset(datasetId) {
    // Implement sharing functionality
    console.log('Sharing dataset:', datasetId);
    alert('Share functionality not yet implemented');
}

/**
 * Delete dataset
 */
function deleteDataset(datasetId) {
    if (confirm('Are you sure you want to delete this dataset? This action cannot be undone.')) {
        fetch(`${getApiBasePath()}/delete-dataset.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ dataset_id: datasetId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Dataset deleted successfully');
                location.reload();
            } else {
                alert('Error deleting dataset: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error deleting dataset:', error);
            alert('Error deleting dataset');
        });
    }
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
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
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Get status color
 */
function getStatusColor(status) {
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
 * Refresh dashboard
 */
function refreshDashboard() {
    if (AppState.currentDataset) {
        // Use dataset manager if available
        if (window.datasetManager && typeof window.datasetManager.selectDataset === 'function') {
            window.datasetManager.selectDataset(
                AppState.currentDataset.id,
                AppState.currentDataset.name,
                AppState.currentDataset.uuid,
                AppState.currentDataset.server
            );
        } else if (window.viewerManager && typeof window.viewerManager.loadDashboard === 'function') {
            window.viewerManager.loadDashboard(
                AppState.currentDataset.id,
                AppState.currentDataset.name,
                AppState.currentDataset.uuid,
                AppState.currentDataset.server
            );
        } else {
            loadDashboard(AppState.currentDataset.id, AppState.currentDataset.name, AppState.currentDataset.uuid, AppState.currentDataset.server);
        }
    }
}

/**
 * Check processing status
 */
function checkProcessingStatus(datasetId) {
    fetch(`${getApiBasePath()}/dataset-status.php?dataset_id=${datasetId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ready') {
                location.reload();
            } else {
                alert('Dataset is still processing. Please wait.');
            }
        })
        .catch(error => {
            console.error('Error checking status:', error);
            alert('Error checking status. Please try again.');
        });
}

/**
 * Show upload modal
 */
function showUploadModal() {
    alert('Upload functionality not yet implemented');
}

/**
 * Show import modal
 */
function showImportModal() {
    alert('Import functionality not yet implemented');
}

/**
 * Show settings modal
 */
function showSettingsModal() {
    alert('Settings functionality not yet implemented');
}

/**
 * Load saved sidebar widths from localStorage
 */
function loadSidebarWidths() {
    const savedSidebarWidth = localStorage.getItem('sidebarWidth');
    const savedDetailsWidth = localStorage.getItem('detailsWidth');
    
    if (savedSidebarWidth) {
        document.documentElement.style.setProperty('--sidebar-width', savedSidebarWidth + 'px');
    }
    
    if (savedDetailsWidth) {
        document.documentElement.style.setProperty('--details-width', savedDetailsWidth + 'px');
    }
}

/**
 * Save sidebar width to localStorage
 */
function saveSidebarWidth(width) {
    localStorage.setItem('sidebarWidth', width);
    document.documentElement.style.setProperty('--sidebar-width', width + 'px');
}

/**
 * Save details sidebar width to localStorage
 */
function saveDetailsWidth(width) {
    localStorage.setItem('detailsWidth', width);
    document.documentElement.style.setProperty('--details-width', width + 'px');
}

/**
 * Initialize resize handles for sidebars
 */
function initializeResizeHandles() {
    const resizeHandleLeft = document.getElementById('resizeHandleLeft');
    const resizeHandleRight = document.getElementById('resizeHandleRight');
    const sidebar = document.getElementById('folderSidebar');
    const details = document.getElementById('detailSidebar');
    
    if (!resizeHandleLeft || !resizeHandleRight || !sidebar || !details) {
        console.warn('Resize handles or sidebars not found');
        return;
    }
    
    let isResizingLeft = false;
    let isResizingRight = false;
    let startX = 0;
    let startWidth = 0;
    
    // Left sidebar resize
    resizeHandleLeft.addEventListener('mousedown', (e) => {
        if (sidebar.classList.contains('collapsed')) return;
        
        isResizingLeft = true;
        startX = e.clientX;
        startWidth = sidebar.offsetWidth;
        resizeHandleLeft.classList.add('resizing');
        sidebar.classList.add('resizing'); // Add class to disable transition
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
        e.stopPropagation();
    });
    
    // Right sidebar resize
    resizeHandleRight.addEventListener('mousedown', (e) => {
        if (details.classList.contains('collapsed')) return;
        
        isResizingRight = true;
        startX = e.clientX;
        startWidth = details.offsetWidth;
        resizeHandleRight.classList.add('resizing');
        details.classList.add('resizing'); // Add class to disable transition
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
        e.stopPropagation();
    });
    
    // Mouse move handler - use a single handler for better performance
    let rafId = null;
    const handleMouseMove = (e) => {
        if (!isResizingLeft && !isResizingRight) {
            if (rafId) {
                cancelAnimationFrame(rafId);
                rafId = null;
            }
            return;
        }
        
        // Cancel any pending animation frame
        if (rafId) {
            cancelAnimationFrame(rafId);
        }
        
        // Use requestAnimationFrame for smoother resizing
        rafId = requestAnimationFrame(() => {
            if (isResizingLeft) {
                // When dragging right (e.clientX > startX), diff is positive, sidebar should grow
                // When dragging left (e.clientX < startX), diff is negative, sidebar should shrink
                const diff = e.clientX - startX;
                const newWidth = Math.max(200, Math.min(startWidth + diff, window.innerWidth * 0.8));
                // Apply width directly to element during resize for immediate feedback
                sidebar.style.width = newWidth + 'px';
                // Update CSS variable for persistence
                document.documentElement.style.setProperty('--sidebar-width', newWidth + 'px');
                saveSidebarWidth(newWidth);
            }
            
            if (isResizingRight) {
                const diff = startX - e.clientX; // Inverted for right sidebar (dragging right = negative diff)
                const newWidth = Math.max(200, Math.min(startWidth + diff, window.innerWidth * 0.8));
                // Apply width directly to element during resize for immediate feedback
                details.style.width = newWidth + 'px';
                // Update CSS variable for persistence
                document.documentElement.style.setProperty('--details-width', newWidth + 'px');
                saveDetailsWidth(newWidth);
            }
            rafId = null;
        });
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    
    // Mouse up handler
    const stopResizing = (e) => {
        if (!isResizingLeft && !isResizingRight) return;
        
        if (isResizingLeft) {
            isResizingLeft = false;
            resizeHandleLeft.classList.remove('resizing');
            sidebar.classList.remove('resizing'); // Remove class to re-enable transition
            // Keep the width but ensure CSS variable is set
            const finalWidth = sidebar.offsetWidth;
            document.documentElement.style.setProperty('--sidebar-width', finalWidth + 'px');
            sidebar.style.width = ''; // Clear inline style to use CSS variable
        }
        if (isResizingRight) {
            isResizingRight = false;
            resizeHandleRight.classList.remove('resizing');
            details.classList.remove('resizing'); // Remove class to re-enable transition
            // Keep the width but ensure CSS variable is set
            const finalWidth = details.offsetWidth;
            document.documentElement.style.setProperty('--details-width', finalWidth + 'px');
            details.style.width = ''; // Clear inline style to use CSS variable
        }
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    };
    
    document.addEventListener('mouseup', stopResizing);
    
    // Also stop resizing if mouse leaves the window
    document.addEventListener('mouseleave', stopResizing);
    
    // Stop resizing on window blur (user switches tabs/windows)
    window.addEventListener('blur', stopResizing);
}

// Export functions for global access
// Don't overwrite window.loadDashboard - viewer-manager.js already defines it
// If we need to expose the local function, use a different name
// window.loadDashboard = loadDashboard; // DEPRECATED - use datasetManager.selectDataset() instead
window.refreshDashboard = refreshDashboard;
window.checkProcessingStatus = checkProcessingStatus;
window.showUploadModal = showUploadModal;
window.showImportModal = showImportModal;
window.showSettingsModal = showSettingsModal;
window.viewDataset = viewDataset;
window.shareDataset = shareDataset;
window.deleteDataset = deleteDataset;
