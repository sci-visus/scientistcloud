<?php
/**
 * Public Repository Page
 * Allows public users to browse and download publicly shared datasets
 * Uses the same layout structure as the main portal
 */

// Include configuration
require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth.php');
require_once(__DIR__ . '/includes/dataset_manager.php');

// Start session if not already started
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// Check if user is authenticated (required for public repo access)
$user = getCurrentUser();
if (!$user) {
    // Redirect to login
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $loginPath = $isLocal ? '/login.php?public_repo=1' : '/portal/login.php?public_repo=1';
    header('Location: ' . $loginPath);
    exit;
}

// Set user type to public_repo if coming from public login
if (isset($_GET['public_repo']) || isset($_SESSION['public_repo_access'])) {
    $_SESSION['user_type'] = 'public_repo';
    $_SESSION['public_repo_access'] = true;
}

// Get filter parameters from URL
$folderFilter = isset($_GET['folder']) ? trim($_GET['folder']) : null;
$teamFilter = isset($_GET['team']) ? trim($_GET['team']) : null;

// Get public datasets with optional filters
$publicDatasets = getPublicDatasets($folderFilter, $teamFilter);

// Group datasets by folder (similar to main portal)
$groupedDatasets = [];
$rootDatasets = [];
foreach ($publicDatasets as $dataset) {
    $folderUuid = $dataset['folder_uuid'] ?? $dataset['metadata']['folder_uuid'] ?? null;
    if ($folderUuid === null || $folderUuid === '' || $folderUuid === 'No_Folder_Selected' || $folderUuid === 'root') {
        $rootDatasets[] = $dataset;
    } else {
        if (!isset($groupedDatasets[$folderUuid])) {
            $groupedDatasets[$folderUuid] = [];
        }
        $groupedDatasets[$folderUuid][] = $dataset;
    }
}

?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Public Data Repository - ScientistCloud</title>
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- FontAwesome Icons -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <!-- Custom CSS -->
  <link href="assets/css/main.css" rel="stylesheet">
</head>
<body>
  <!-- Left Sidebar -->
  <aside class="sidebar d-flex flex-column align-items-center" id="folderSidebar">
    <img src="assets/images/scientistcloud-logo.png" class="logo" alt="ScientistCloud Logo">
    <div class="d-flex align-items-center justify-content-between w-100 px-2 mb-2">
      <h5 class="mb-0" style="color: var(--fg-color);">Public Datasets</h5>
      <button class="btn btn-sm btn-outline-secondary" id="refreshDatasetsBtn" title="Refresh Datasets" style="border-color: var(--panel-border); color: var(--fg-color);">
        <i class="fas fa-sync-alt"></i>
      </button>
    </div>
    <?php if ($folderFilter || $teamFilter): ?>
      <div class="w-100 px-2 mb-2">
        <div class="alert alert-info mb-2" style="background-color: var(--info-color, rgba(181, 174, 223, 0.2)); border-color: var(--info-color, #B5AEDF); color: var(--fg-color); padding: 0.5rem; font-size: 0.85rem;">
          <i class="fas fa-filter"></i> <strong>Filtered View:</strong><br>
          <?php if ($folderFilter): ?>
            <span class="badge bg-primary me-1">Folder: <?php echo htmlspecialchars($folderFilter); ?></span>
            <a href="?<?php echo $teamFilter ? 'team=' . urlencode($teamFilter) : ''; ?>" class="text-decoration-none" style="color: var(--fg-color);">
              <i class="fas fa-times-circle"></i>
            </a>
          <?php endif; ?>
          <?php if ($teamFilter): ?>
            <span class="badge bg-primary me-1">Team: <?php echo htmlspecialchars($teamFilter); ?></span>
            <a href="?<?php echo $folderFilter ? 'folder=' . urlencode($folderFilter) : ''; ?>" class="text-decoration-none" style="color: var(--fg-color);">
              <i class="fas fa-times-circle"></i>
            </a>
          <?php endif; ?>
          <br><a href="public-repo.php" class="text-decoration-none small" style="color: var(--fg-color);">Clear all filters</a>
        </div>
      </div>
    <?php endif; ?>
    <nav class="w-100 panel-content" style="overflow-y: auto; flex: 1;">
      <div class="dataset-list">
        <div class="dataset-section">
          <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#publicDatasets">
            <span class="arrow-icon" id="arrow-public">&#9656;</span>
            <?php if ($folderFilter || $teamFilter): ?>
              Filtered Datasets (<?php echo count($publicDatasets); ?>)
            <?php else: ?>
              Public Datasets (<?php echo count($publicDatasets); ?>)
            <?php endif; ?>
          </a>
          <div class="collapse ps-4 w-100 show" id="publicDatasets">
            <?php if (empty($publicDatasets)): ?>
              <p class="small" style="color: var(--fg-color); opacity: 0.7;">No public datasets available at this time.</p>
            <?php else: ?>
              <!-- Root level datasets (no folder) -->
              <?php foreach ($rootDatasets as $dataset): ?>
                <div class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id'] ?? $dataset['uuid']); ?>" data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>">
                  <div class="dataset-header">
                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                       data-dataset-id="<?php echo htmlspecialchars($dataset['id'] ?? $dataset['uuid']); ?>"
                       data-dataset-name="<?php echo htmlspecialchars($dataset['name'] ?? 'Unnamed Dataset'); ?>"
                       data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>"
                       data-dataset-server="false"
                       style="color: var(--fg-color);">
                      <i class="fas fa-database me-2"></i>
                      <span class="dataset-name"><?php echo htmlspecialchars($dataset['name'] ?? 'Unnamed Dataset'); ?></span>
                      <?php if ($dataset['is_public_downloadable'] ?? false): ?>
                        <span class="badge bg-success ms-2" style="font-size: 0.65rem;">
                          <i class="fas fa-download"></i> Downloadable
                        </span>
                      <?php else: ?>
                        <span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">
                          <i class="fas fa-eye"></i> View Only
                        </span>
                      <?php endif; ?>
                    </a>
                  </div>
                </div>
              <?php endforeach; ?>
              
              <!-- Foldered datasets -->
              <?php foreach ($groupedDatasets as $folderUuid => $folderDatasets): ?>
                <details class="folder-details">
                  <summary class="folder-summary" style="color: var(--fg-color);">
                    <i class="fas fa-folder me-2"></i>
                    <span><?php echo htmlspecialchars($folderUuid); ?></span>
                    <span class="badge bg-secondary ms-2" style="font-size: 0.65rem;"><?php echo count($folderDatasets); ?></span>
                  </summary>
                  <ul class="nested folder-datasets">
                    <?php foreach ($folderDatasets as $dataset): ?>
                      <li class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id'] ?? $dataset['uuid']); ?>" data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>">
                        <div class="dataset-header">
                          <a class="nav-link dataset-link" href="javascript:void(0)" 
                             data-dataset-id="<?php echo htmlspecialchars($dataset['id'] ?? $dataset['uuid']); ?>"
                             data-dataset-name="<?php echo htmlspecialchars($dataset['name'] ?? 'Unnamed Dataset'); ?>"
                             data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>"
                             data-dataset-server="false"
                             style="color: var(--fg-color);">
                            <i class="fas fa-database me-2"></i>
                            <span class="dataset-name"><?php echo htmlspecialchars($dataset['name'] ?? 'Unnamed Dataset'); ?></span>
                            <?php if ($dataset['is_public_downloadable'] ?? false): ?>
                              <span class="badge bg-success ms-2" style="font-size: 0.65rem;">
                                <i class="fas fa-download"></i> Downloadable
                              </span>
                            <?php else: ?>
                              <span class="badge bg-secondary ms-2" style="font-size: 0.65rem;">
                                <i class="fas fa-eye"></i> View Only
                              </span>
                            <?php endif; ?>
                          </a>
                        </div>
                      </li>
                    <?php endforeach; ?>
                  </ul>
                </details>
              <?php endforeach; ?>
            <?php endif; ?>
          </div>
        </div>
      </div>
    </nav>
    <button class="collapse-btn left" id="toggleFolder">&#9664;</button>
    <button class="theme-toggle" id="themeToggle"><i class="fas fa-adjust"></i></button>
  </aside>
  
  <!-- Left Sidebar Resize Handle -->
  <div class="resize-handle resize-handle-left" id="resizeHandleLeft"></div>

  <!-- Main Content -->
  <section class="main">
    <div class="toolbar-wrapper">
      <div class="viewer-toolbar">
        <label for="viewerType">Dashboard:</label>
        <select id="viewerType" class="form-select form-select-sm">
          <!-- Options will be populated dynamically by viewer-manager.js -->
          <option value="">Loading dashboards...</option>
        </select>
        <div class="btn-group ms-auto" role="group" aria-label="User actions">
          <a href="index.php" class="btn btn-outline-light" title="Back to Portal">
            <i class="fas fa-arrow-left"></i> Back to Portal
          </a>
          <button type="button" class="btn btn-outline-light" id="logoutBtn" title="Logout">
            <i class="fas fa-sign-out-alt"></i> Logout
          </button>
        </div>
      </div>
    </div>
    <div class="viewer-container" id="viewerContainer">
      <?php include 'includes/dashboard_loader.php'; ?>
    </div>
  </section>

  <!-- Right Sidebar Resize Handle -->
  <div class="resize-handle resize-handle-right" id="resizeHandleRight"></div>
  
  <!-- Right Sidebar -->
  <aside class="details d-flex flex-column px-3 py-3" id="detailSidebar">
    <h5 style="color: var(--fg-color);">Dataset Details</h5>
    <div class="panel-content" id="datasetDetails" style="overflow-y: auto; flex: 1;">
      <p style="color: var(--fg-color); opacity: 0.7;">Select a dataset to view details</p>
    </div>
    <button class="collapse-btn right" id="toggleDetail">&#9654;</button>
  </aside>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="assets/js/main.js"></script>
  <script src="assets/js/dataset-manager.js"></script>
  <script src="assets/js/viewer-manager.js"></script>
  <script>
    // Set global flag for public repo user
    window.isPublicRepoUser = true;
    
    // Helper function to get API base path
    function getApiBasePath() {
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      return isLocal ? '/api' : '/portal/api';
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
      // Hide upload/team buttons for public repo users
      const uploadBtn = document.getElementById('uploadDatasetBtn');
      const createTeamBtn = document.getElementById('createTeamBtn');
      const viewJobsBtn = document.getElementById('viewJobsBtn');
      const settingsBtn = document.getElementById('settingsBtn');
      
      if (uploadBtn) uploadBtn.style.display = 'none';
      if (createTeamBtn) createTeamBtn.style.display = 'none';
      if (viewJobsBtn) viewJobsBtn.style.display = 'none';
      if (settingsBtn) settingsBtn.style.display = 'none';
      
      // Wait for managers to initialize
      setTimeout(() => {
        if (window.datasetManager) {
          console.log('Dataset manager initialized for public repo');
        }
        if (window.viewerManager) {
          console.log('Viewer manager initialized for public repo');
        }
      }, 500);
      
      // Refresh button handler
      document.getElementById('refreshDatasetsBtn')?.addEventListener('click', () => {
        window.location.reload();
      });
      
      // Logout handler
      document.getElementById('logoutBtn')?.addEventListener('click', () => {
        window.location.href = 'logout.php';
      });
    });
  </script>
</body>
</html>
