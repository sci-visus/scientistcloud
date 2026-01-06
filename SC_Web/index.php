<?php
/**
 * ScientistCloud Data Portal - Main Index
 * Integrates with scientistCloudLib for data access and user management
 */

// Include configuration and authentication
require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth.php');
require_once(__DIR__ . '/includes/dataset_manager.php');
require_once(__DIR__ . '/includes/dashboard_manager.php');

// Start session if not already started
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// Get user information
$user = getCurrentUser();
if (!$user) {
    // Clear any stale session data that might cause loops
    if (isset($_SESSION['user_email'])) {
        unset($_SESSION['user_email']);
        unset($_SESSION['user_id']);
        unset($_SESSION['user_name']);
    }
    
    // Redirect to login if not authenticated
    // For local development, use /login.php (no /portal/ prefix)
    // For server, use /portal/login.php
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
    header('Location: ' . $loginPath);
    exit;
}

// Get user's datasets
$datasets = getUserDatasets($user['id']);
$preferredDashboard = getUserPreferredDashboard($user['id']);

?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ScientistCloud Data Portal</title>
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
      <h5 class="mb-0">Datasets</h5>
      <button class="btn btn-sm btn-outline-secondary" id="refreshDatasetsBtn" title="Refresh Datasets">
        <i class="fas fa-sync-alt"></i>
      </button>
    </div>
    <nav class="w-100 panel-content">
      <?php include 'includes/dataset_list.php'; ?>
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
        <div class="btn-group ms-3" role="group" aria-label="Dataset actions">
          <button type="button" class="btn btn-outline-light" id="uploadDatasetBtn" title="Upload Dataset">
            <i class="fas fa-upload"></i> Upload Dataset
          </button>
          <button type="button" class="btn btn-outline-light" id="viewJobsBtn" title="View Jobs" style="display: none;">
            <i class="fas fa-tasks"></i> View Jobs
          </button>
          <button type="button" class="btn btn-outline-light" id="createTeamBtn" title="Create Team">
            <i class="fas fa-users"></i> Create Team
          </button>
          <button type="button" class="btn btn-outline-light" id="settingsBtn" title="Settings" disabled style="display: none;">
            <i class="fas fa-cog"></i> Settings
          </button>
        </div>
        <div class="btn-group ms-auto" role="group" aria-label="User actions">
          <a href="docs.php" class="btn btn-outline-light" title="Documentation" target="_blank">
            <i class="fas fa-book"></i> Docs
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
    <h5>Dataset Details</h5>
    <div class="panel-content" id="datasetDetails">
      <p>Select a dataset to view details</p>
    </div>
    <button class="collapse-btn right" id="toggleDetail">&#9654;</button>
  </aside>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="assets/js/main.js"></script>
  <script src="assets/js/dataset-manager.js"></script>
  <script src="assets/js/viewer-manager.js"></script>
  <script src="assets/js/upload-manager.js"></script>
  <script src="assets/js/job-manager.js"></script>
</body>
</html>
