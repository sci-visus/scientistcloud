<?php
/**
 * Dashboard Loader Module for ScientistCloud Data Portal
 * Loads the appropriate dashboard based on user preferences and dataset
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/auth.php');
require_once(__DIR__ . '/dataset_manager.php');
require_once(__DIR__ . '/dashboard_manager.php');

// Get current user
$user = getCurrentUser();
if (!$user) {
    echo '<div class="alert alert-warning">Please log in to view dashboards.</div>';
    exit;
}

// Get dataset ID from request
$datasetId = $_GET['dataset_id'] ?? null;
$dashboardType = $_GET['dashboard'] ?? null;

if ($datasetId) {
    // Load specific dataset dashboard
    $dashboard = loadDashboard($datasetId, $dashboardType);
    
    if ($dashboard) {
        $dataset = $dashboard['dataset'];
        $viewerUrl = $dashboard['viewer_url'];
        $status = getDashboardStatus($datasetId, $dashboard['dashboard_type']);
        
        // Display dashboard based on status
        switch ($status) {
            case 'ready':
                displayReadyDashboard($dataset, $viewerUrl, $dashboard['dashboard_type']);
                break;
            case 'processing':
                displayProcessingDashboard($dataset);
                break;
            case 'unsupported':
                displayUnsupportedDashboard($dataset);
                break;
            default:
                displayErrorDashboard($dataset, 'Unknown error occurred');
        }
    } else {
        displayErrorDashboard(null, 'Failed to load dashboard');
    }
} else {
    // Display welcome screen
    displayWelcomeScreen($user);
}

/**
 * Display ready dashboard
 */
function displayReadyDashboard($dataset, $viewerUrl, $dashboardType) {
    ?>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h4><?php echo htmlspecialchars($dataset['name']); ?></h4>
        </div>
        <div class="dashboard-content">
            <iframe id="dashboardFrame" 
                    src="<?php echo htmlspecialchars($viewerUrl); ?>" 
                    width="100%" 
                    height="100%" 
                    frameborder="0"
                    onload="onDashboardLoad()"
                    onerror="onDashboardError()">
            </iframe>
        </div>
    </div>
    <?php
}

/**
 * Display processing dashboard
 */
function displayProcessingDashboard($dataset) {
    ?>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h4><?php echo htmlspecialchars($dataset['name']); ?></h4>
            <span class="badge bg-warning">Processing</span>
        </div>
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
                <button class="btn btn-primary mt-3" onclick="checkProcessingStatus('<?php echo $dataset['id']; ?>')">
                    Check Status
                </button>
            </div>
        </div>
    </div>
    <?php
}

/**
 * Display unsupported dashboard
 */
function displayUnsupportedDashboard($dataset) {
    ?>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h4><?php echo htmlspecialchars($dataset['name']); ?></h4>
            <span class="badge bg-secondary">Unsupported</span>
        </div>
        <div class="dashboard-content unsupported-content">
            <div class="text-center">
                <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                <h5>Dashboard not available</h5>
                <p class="text-muted">This dataset format is not supported by the current dashboard.</p>
                <div class="mt-3">
                    <h6>Available dashboards for this dataset:</h6>
                    <?php
                    $availableDashboards = getAvailableDashboards($dataset['id']);
                    if (empty($availableDashboards)) {
                        echo '<p class="text-muted">No dashboards available for this dataset.</p>';
                    } else {
                        echo '<div class="list-group">';
                        foreach ($availableDashboards as $dashboard) {
                            echo "<a href=\"javascript:loadDashboard('{$dataset['id']}', '{$dashboard['type']}')\" class=\"list-group-item list-group-item-action\">";
                            echo "<h6 class=\"mb-1\">{$dashboard['name']}</h6>";
                            echo "<p class=\"mb-1\">{$dashboard['description']}</p>";
                            echo "</a>";
                        }
                        echo '</div>';
                    }
                    ?>
                </div>
            </div>
        </div>
    </div>
    <?php
}

/**
 * Display error dashboard
 */
function displayErrorDashboard($dataset, $errorMessage) {
    ?>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h4><?php echo $dataset ? htmlspecialchars($dataset['name']) : 'Error'; ?></h4>
            <span class="badge bg-danger">Error</span>
        </div>
        <div class="dashboard-content error-content">
            <div class="text-center">
                <i class="fas fa-exclamation-circle fa-3x text-danger mb-3"></i>
                <h5>Error loading dashboard</h5>
                <p class="text-muted"><?php echo htmlspecialchars($errorMessage); ?></p>
                <button class="btn btn-primary mt-3" onclick="location.reload()">
                    <i class="fas fa-refresh"></i> Retry
                </button>
            </div>
        </div>
    </div>
    <?php
}

/**
 * Display welcome screen
 */
function displayWelcomeScreen($user) {
    $stats = getDatasetStats($user['id']);
    ?>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h4>Welcome, <?php echo htmlspecialchars($user['name']); ?>!</h4>
        </div>
        <div class="dashboard-content welcome-content">
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-chart-bar"></i> Your Statistics</h5>
                        </div>
                        <div class="card-body">
                            <div class="row text-center">
                                <div class="col-4">
                                    <h3 class="text-primary"><?php echo $stats['total_datasets']; ?></h3>
                                    <p class="text-muted">Datasets</p>
                                </div>
                                <div class="col-4">
                                    <h3 class="text-success"><?php echo formatFileSize($stats['total_size']); ?></h3>
                                    <p class="text-muted">Total Size</p>
                                </div>
                                <div class="col-4">
                                    <h3 class="text-info"><?php echo count($stats['status_counts']); ?></h3>
                                    <p class="text-muted">Status Types</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-upload"></i> Quick Actions</h5>
                        </div>
                        <div class="card-body">
                            <div class="d-grid gap-2">
                                <button class="btn btn-primary" onclick="showUploadModal()">
                                    <i class="fas fa-upload"></i> Upload Dataset
                                </button>
                                <button class="btn btn-outline-primary" onclick="showImportModal()">
                                    <i class="fas fa-download"></i> Import from URL
                                </button>
                                <button class="btn btn-outline-secondary" onclick="showSettingsModal()">
                                    <i class="fas fa-cog"></i> Settings
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-info-circle"></i> Getting Started</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-4">
                                    <h6><i class="fas fa-upload text-primary"></i> 1. Upload Data</h6>
                                    <p class="text-muted">Upload your scientific datasets in supported formats like TIFF, HDF5, or NetCDF.</p>
                                </div>
                                <div class="col-md-4">
                                    <h6><i class="fas fa-cog text-warning"></i> 2. Processing</h6>
                                    <p class="text-muted">Your data will be automatically processed and optimized for visualization.</p>
                                </div>
                                <div class="col-md-4">
                                    <h6><i class="fas fa-chart-line text-success"></i> 3. Visualize</h6>
                                    <p class="text-muted">Explore your data with interactive 3D visualizations and analysis tools.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <?php
}

/**
 * Format file size helper
 * Note: This function may already be defined in dataset_list.php
 */
if (!function_exists('formatFileSize')) {
    function formatFileSize($bytes) {
        if ($bytes == 0) return '0 B';
        
        $units = ['B', 'KB', 'MB', 'GB', 'TB'];
        $bytes = max($bytes, 0);
        $pow = floor(($bytes ? log($bytes) : 0) / log(1024));
        $pow = min($pow, count($units) - 1);
        
        $bytes /= pow(1024, $pow);
        
        return round($bytes, 2) . ' ' . $units[$pow];
    }
}
?>

<style>
.dashboard-container {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid var(--panel-border);
    background-color: var(--toolbar-bg);
}

.dashboard-content {
    flex: 1;
    padding: 1rem;
    overflow: auto;
}

.processing-content,
.unsupported-content,
.error-content,
.welcome-content {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
}

.welcome-content {
    align-items: flex-start;
    padding-top: 2rem;
}

.card {
    margin-bottom: 1rem;
}

.spinner-border {
    width: 3rem;
    height: 3rem;
}

.progress {
    height: 1rem;
}

.list-group-item {
    text-align: left;
}

.list-group-item h6 {
    margin-bottom: 0.25rem;
}

.list-group-item p {
    margin-bottom: 0;
    font-size: 0.9rem;
}
</style>

<script>
// Dashboard management functions
function loadDashboard(datasetId, dashboardType) {
    const url = new URL(window.location);
    url.searchParams.set('dataset_id', datasetId);
    if (dashboardType) {
        url.searchParams.set('dashboard', dashboardType);
    }
    window.location.href = url.toString();
}

function refreshDashboard() {
    const iframe = document.getElementById('dashboardFrame');
    if (iframe) {
        iframe.src = iframe.src;
    }
}

function checkProcessingStatus(datasetId) {
    // Implement status checking
    fetch(`/api/dataset-status.php?dataset_id=${datasetId}`)
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

function onDashboardLoad() {
    console.log('Dashboard loaded successfully');
}

function onDashboardError() {
    console.error('Dashboard failed to load');
    alert('Failed to load dashboard. Please try again.');
}
</script>
