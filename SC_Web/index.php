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
    header('Location: /portal/login.php');
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
    <h5>Datasets</h5>
    <nav class="w-100 panel-content">
      <?php include 'includes/dataset_list.php'; ?>
    </nav>
    <button class="collapse-btn left" id="toggleFolder">&#9664;</button>
    <button class="theme-toggle" id="themeToggle"><i class="fas fa-adjust"></i></button>
  </aside>

  <!-- Main Content -->
  <section class="main">
    <div class="toolbar-wrapper">
      <div class="viewer-toolbar">
        <label for="viewerType">Viewer:</label>
        <select id="viewerType" class="form-select form-select-sm">
          <option value="openvisus">OpenVisus</option>
          <option value="bokeh">Bokeh</option>
          <option value="jupyter">Jupyter notebook</option>
          <option value="plotly">Plotly</option>
        </select>
        <div class="btn-group" role="group" aria-label="Annotation tools">
          <button type="button" class="btn btn-outline-light"><i class="fas fa-search-plus"></i></button>
          <button type="button" class="btn btn-outline-light"><i class="fas fa-pen"></i></button>
          <button type="button" class="btn btn-outline-light"><i class="fas fa-mouse-pointer"></i></button>
          <button type="button" class="btn btn-outline-light"><i class="fas fa-filter"></i></button>
        </div>
      </div>
    </div>
    <div class="viewer-container" id="viewerContainer">
      <?php include 'includes/dashboard_loader.php'; ?>
    </div>
  </section>

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
</body>
</html>
