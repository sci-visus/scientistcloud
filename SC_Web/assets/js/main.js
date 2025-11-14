/**
 * ScientistCloud Data Portal - Main JavaScript
 * Handles UI interactions and theme management
 */

// Helper function to get API base path (detects local vs server)
function getApiBasePath() {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    return isLocal ? '/api' : '/portal/api';
}

// Global state
const AppState = {
    currentDataset: null,
    currentDashboard: null,
    theme: localStorage.getItem('theme') || 'dark',
    sidebarCollapsed: false,
    detailsCollapsed: false
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadTheme();
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
    // Sidebar toggle
    const toggleFolder = document.getElementById('toggleFolder');
    if (toggleFolder) {
        toggleFolder.addEventListener('click', toggleSidebar);
    }
    
    // Details sidebar toggle
    const toggleDetail = document.getElementById('toggleDetail');
    if (toggleDetail) {
        toggleDetail.addEventListener('click', toggleDetails);
    }
    
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
        console.log('Theme toggle button event listener attached');
        
        // Set initial icon based on current theme
        if (AppState.theme === 'light') {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>'; // Moon icon for light mode
        } else {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>'; // Sun icon for dark mode
        }
    }
    
    // Initialize resize handles
    initializeResizeHandles();
    
    // Dataset selection
    document.addEventListener('click', function(e) {
        if (e.target.closest('.dataset-link')) {
            e.preventDefault();
            handleDatasetSelection(e.target.closest('.dataset-link'));
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
    
    // Quick action buttons (from welcome screen)
    const quickUploadBtn = document.getElementById('quickUploadBtn');
    if (quickUploadBtn) {
        quickUploadBtn.addEventListener('click', function() {
            const uploadBtn = document.getElementById('uploadDatasetBtn');
            if (uploadBtn) uploadBtn.click();
        });
    }
    
    const quickViewJobsBtn = document.getElementById('quickViewJobsBtn');
    if (quickViewJobsBtn) {
        quickViewJobsBtn.addEventListener('click', function() {
            const viewJobsBtn = document.getElementById('viewJobsBtn');
            if (viewJobsBtn) viewJobsBtn.click();
        });
    }
    
    const quickCreateTeamBtn = document.getElementById('quickCreateTeamBtn');
    if (quickCreateTeamBtn) {
        quickCreateTeamBtn.addEventListener('click', function() {
            const createTeamBtn = document.getElementById('createTeamBtn');
            if (createTeamBtn) createTeamBtn.click();
        });
    }
    
    const quickSettingsBtn = document.getElementById('quickSettingsBtn');
    if (quickSettingsBtn) {
        quickSettingsBtn.addEventListener('click', function() {
            const settingsBtn = document.getElementById('settingsBtn');
            if (settingsBtn && !settingsBtn.disabled) {
                // Settings not implemented yet
                alert('Settings feature coming soon!');
            }
        });
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
    console.log('toggleTheme called, current theme:', AppState.theme);
    
    AppState.theme = AppState.theme === 'dark' ? 'light' : 'dark';
    document.body.classList.toggle('light-theme');
    localStorage.setItem('theme', AppState.theme);
    
    // Update button icon/state if needed
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        if (AppState.theme === 'light') {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>'; // Moon icon for light mode (switch to dark)
        } else {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>'; // Sun icon for dark mode (switch to light)
        }
    }
    
    console.log('Theme changed to:', AppState.theme);
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
    
    // Load dashboard
    loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
    
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
                    <span class="detail-value">${formatFileSize(dataset.data_size)}</span>
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
function loadDashboard(datasetId, datasetName, datasetUuid, datasetServer) {
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
        loadDashboard(AppState.currentDataset.id, AppState.currentDataset.name, AppState.currentDataset.uuid, AppState.currentDataset.server, viewerType);
    }
}

/**
 * View dataset
 */
function viewDataset(datasetId) {
    if (AppState.currentDataset) {
        loadDashboard(AppState.currentDataset.id, AppState.currentDataset.name, AppState.currentDataset.uuid, AppState.currentDataset.server);
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
        loadDashboard(AppState.currentDataset.id, AppState.currentDataset.name, AppState.currentDataset.uuid, AppState.currentDataset.server);
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
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });
    
    // Right sidebar resize
    resizeHandleRight.addEventListener('mousedown', (e) => {
        if (details.classList.contains('collapsed')) return;
        
        isResizingRight = true;
        startX = e.clientX;
        startWidth = details.offsetWidth;
        resizeHandleRight.classList.add('resizing');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });
    
    // Mouse move handler
    document.addEventListener('mousemove', (e) => {
        if (!isResizingLeft && !isResizingRight) return;
        
        if (isResizingLeft) {
            const diff = startX - e.clientX; // Inverted because we're dragging left
            const newWidth = Math.max(200, Math.min(startWidth + diff, window.innerWidth * 0.8));
            saveSidebarWidth(newWidth);
        }
        
        if (isResizingRight) {
            const diff = e.clientX - startX;
            const newWidth = Math.max(200, Math.min(startWidth + diff, window.innerWidth * 0.8));
            saveDetailsWidth(newWidth);
        }
    });
    
    // Mouse up handler
    document.addEventListener('mouseup', () => {
        if (isResizingLeft) {
            isResizingLeft = false;
            resizeHandleLeft.classList.remove('resizing');
        }
        if (isResizingRight) {
            isResizingRight = false;
            resizeHandleRight.classList.remove('resizing');
        }
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    });
}

// Export functions for global access
window.loadDashboard = loadDashboard;
window.refreshDashboard = refreshDashboard;
window.checkProcessingStatus = checkProcessingStatus;
window.showUploadModal = showUploadModal;
window.showImportModal = showImportModal;
window.showSettingsModal = showSettingsModal;
window.viewDataset = viewDataset;
window.shareDataset = shareDataset;
window.deleteDataset = deleteDataset;
