<?php
/**
 * Test Index for ScientistCloud Data Portal
 * Uses mock configuration for testing without full scientistCloudLib setup
 */

// Include test configuration
require_once(__DIR__ . '/test-config.php');

// Get user information
$user = getCurrentUser();
$datasets = getUserDatasets($user['id']);
$preferredDashboard = getUserPreferredDashboard($user['id']);

?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ScientistCloud Data Portal - Test Mode</title>
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- FontAwesome Icons -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <!-- Custom CSS -->
  <link href="assets/css/main.css" rel="stylesheet">
</head>
<body>
  <!-- Test Mode Banner -->
  <div class="alert alert-info text-center mb-0" style="position: fixed; top: 0; left: 0; right: 0; z-index: 9999;">
    <i class="fas fa-flask"></i> <strong>TEST MODE</strong> - Using mock data for testing
  </div>
  
  <!-- Add top margin to account for banner -->
  <div style="margin-top: 60px;">
    <!-- Left Sidebar -->
    <aside class="sidebar d-flex flex-column align-items-center" id="folderSidebar">
      <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMjAiIGZpbGw9IiMwMDdiZmYiLz4KPHN2ZyB4PSI4IiB5PSI4IiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJMMTMuMDkgOC4yNkwyMCA5TDEzLjA5IDE1Ljc0TDEyIDIyTDEwLjkxIDE1Ljc0TDQgOUwxMC45MSA4LjI2TDEyIDJaIiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4KPC9zdmc+" class="logo" alt="ScientistCloud Logo">
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
  </div>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="assets/js/main.js"></script>
  <script src="assets/js/dataset-manager.js"></script>
  <script src="assets/js/viewer-manager.js"></script>
</body>
</html>
