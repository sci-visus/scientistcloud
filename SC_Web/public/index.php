<?php
/**
 * ScientistCloud Data Portal - Public Portal
 * Public-facing version that displays only public datasets without requiring authentication
 */

// Include configuration (no auth.php - no authentication required)
require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');
require_once(__DIR__ . '/../includes/dashboard_manager.php');

// Start session if not already started (for any session-based features, but no auth required)
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// Get public datasets
$publicDatasets = getPublicDatasets();

?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ScientistCloud Public Data Portal</title>
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- FontAwesome Icons -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <!-- Custom CSS -->
  <link href="../assets/css/main.css" rel="stylesheet">
  <link href="../assets/css/public.css" rel="stylesheet">
</head>
<body class="public-portal">
  <!-- Left Sidebar -->
  <aside class="sidebar d-flex flex-column align-items-center" id="folderSidebar">
    <img src="../assets/images/scientistcloud-logo.png" class="logo" alt="ScientistCloud Logo">
    <div class="d-flex align-items-center justify-content-between w-100 px-2 mb-2">
      <h5 class="mb-0">Public Datasets</h5>
      <button class="btn btn-sm btn-outline-light" id="refreshDatasetsBtn" title="Refresh Datasets">
        <i class="fas fa-sync-alt"></i>
      </button>
    </div>
    <nav class="w-100 panel-content">
      <div class="dataset-list" id="publicDatasetList">
        <p class="text-center text-muted">Loading public datasets...</p>
      </div>
    </nav>
    <button class="collapse-btn left" id="toggleFolder">&#9664;</button>
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
        <div class="btn-group ms-3" role="group" aria-label="Portal actions">
          <a href="../index.php" class="btn btn-outline-light" title="Sign In to Upload">
            <i class="fas fa-sign-in-alt"></i> Sign In to Upload
          </a>
        </div>
        <div class="btn-group ms-auto" role="group" aria-label="User actions">
          <a href="../docs.php" class="btn btn-outline-light" title="Documentation" target="_blank">
            <i class="fas fa-book"></i> Docs
          </a>
        </div>
      </div>
    </div>
    <div class="viewer-container" id="viewerContainer">
      <div class="dashboard-container">
        <div class="dashboard-content welcome-content">
          <div class="text-center">
            <h4>Welcome to the Public Data Portal</h4>
            <p class="text-muted">Select a dataset from the sidebar to view it in a dashboard.</p>
          </div>
        </div>
      </div>
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
  <script>
    // Set public portal mode
    window.IS_PUBLIC_PORTAL = true;
    window.API_BASE_PATH = '../api';
  </script>
  <script src="../assets/js/main.js"></script>
  <script src="../assets/js/public-dataset-manager.js"></script>
  <script src="../assets/js/viewer-manager.js"></script>
</body>
</html>

