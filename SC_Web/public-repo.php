<?php
/**
 * Public Repository Page
 * Allows public users to browse and download publicly shared datasets
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

// Get public datasets
$publicDatasets = getPublicDatasets();

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
  <style>
    .public-repo-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 2rem 0;
      margin-bottom: 2rem;
    }
    .dataset-card {
      transition: transform 0.2s, box-shadow 0.2s;
      margin-bottom: 1rem;
    }
    .dataset-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .download-badge {
      background-color: #28a745;
      color: white;
      padding: 0.25rem 0.5rem;
      border-radius: 0.25rem;
      font-size: 0.75rem;
    }
    .view-only-badge {
      background-color: #6c757d;
      color: white;
      padding: 0.25rem 0.5rem;
      border-radius: 0.25rem;
      font-size: 0.75rem;
    }
  </style>
</head>
<body>
  <!-- Header -->
  <div class="public-repo-header">
    <div class="container">
      <div class="row align-items-center">
        <div class="col-md-8">
          <h1><i class="fas fa-database"></i> Public Data Repository</h1>
          <p class="mb-0">Browse and download publicly shared scientific datasets</p>
        </div>
        <div class="col-md-4 text-end">
          <a href="index.php" class="btn btn-light me-2">
            <i class="fas fa-arrow-left"></i> Back to Portal
          </a>
          <button type="button" class="btn btn-outline-light" id="logoutBtn">
            <i class="fas fa-sign-out-alt"></i> Logout
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Main Content -->
  <div class="container">
    <div class="row mb-3">
      <div class="col-md-6">
        <h2>Public Datasets</h2>
        <p class="text-muted"><?php echo count($publicDatasets); ?> public dataset(s) available</p>
      </div>
      <div class="col-md-6 text-end">
        <button class="btn btn-primary" id="refreshBtn">
          <i class="fas fa-sync-alt"></i> Refresh
        </button>
      </div>
    </div>

    <!-- Dataset List -->
    <div class="row" id="datasetList">
      <?php if (empty($publicDatasets)): ?>
        <div class="col-12">
          <div class="alert alert-info">
            <i class="fas fa-info-circle"></i> No public datasets available at this time.
          </div>
        </div>
      <?php else: ?>
        <?php foreach ($publicDatasets as $dataset): ?>
          <div class="col-md-6 col-lg-4">
            <div class="card dataset-card">
              <div class="card-body">
                <h5 class="card-title">
                  <?php echo htmlspecialchars($dataset['name'] ?? 'Unnamed Dataset'); ?>
                  <?php if ($dataset['is_public_downloadable'] ?? false): ?>
                    <span class="download-badge ms-2">
                      <i class="fas fa-download"></i> Downloadable
                    </span>
                  <?php else: ?>
                    <span class="view-only-badge ms-2">
                      <i class="fas fa-eye"></i> View Only
                    </span>
                  <?php endif; ?>
                </h5>
                <p class="card-text">
                  <small class="text-muted">
                    <i class="fas fa-user"></i> <?php echo htmlspecialchars($dataset['user_id'] ?? 'Unknown'); ?><br>
                    <i class="fas fa-tag"></i> <?php echo htmlspecialchars($dataset['sensor'] ?? 'Unknown'); ?><br>
                    <?php if (isset($dataset['data_size']) && $dataset['data_size'] > 0): ?>
                      <i class="fas fa-hdd"></i> <?php echo number_format($dataset['data_size'], 2); ?> GB
                    <?php endif; ?>
                  </small>
                </p>
                <div class="btn-group w-100" role="group">
                  <button type="button" class="btn btn-sm btn-primary view-dataset-btn" 
                          data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>"
                          data-dataset-name="<?php echo htmlspecialchars($dataset['name'] ?? ''); ?>">
                    <i class="fas fa-eye"></i> View
                  </button>
                  <?php if ($dataset['is_public_downloadable'] ?? false): ?>
                    <button type="button" class="btn btn-sm btn-success download-menu-btn dropdown-toggle dropdown-toggle-split" 
                            data-bs-toggle="dropdown"
                            data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>"
                            data-dataset-name="<?php echo htmlspecialchars($dataset['name'] ?? ''); ?>">
                      <i class="fas fa-download"></i> Download
                    </button>
                    <ul class="dropdown-menu">
                      <li>
                        <a class="dropdown-item download-folder-link" href="#" 
                           data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>"
                           data-directory="upload">
                          <i class="fas fa-file-archive"></i> Upload Folder (ZIP)
                        </a>
                      </li>
                      <li>
                        <a class="dropdown-item download-folder-link" href="#" 
                           data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid'] ?? $dataset['id']); ?>"
                           data-directory="converted">
                          <i class="fas fa-file-archive"></i> Converted Folder (ZIP)
                        </a>
                      </li>
                    </ul>
                  <?php endif; ?>
                </div>
              </div>
            </div>
          </div>
        <?php endforeach; ?>
      <?php endif; ?>
    </div>
  </div>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    // Set global flag for public repo user
    window.isPublicRepoUser = true;
    
    // Helper function to get API base path
    function getApiBasePath() {
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      return isLocal ? '/api' : '/portal/api';
    }

    // Logout handler
    document.getElementById('logoutBtn')?.addEventListener('click', () => {
      window.location.href = 'logout.php';
    });

    // Refresh handler
    document.getElementById('refreshBtn')?.addEventListener('click', () => {
      window.location.reload();
    });

    // View dataset handler
    document.querySelectorAll('.view-dataset-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const datasetUuid = btn.getAttribute('data-dataset-uuid');
        const datasetName = btn.getAttribute('data-dataset-name');
        // Open dataset in main portal
        window.location.href = `index.php?dataset=${datasetUuid}`;
      });
    });

    // Download folder handler
    document.querySelectorAll('.download-folder-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const datasetUuid = link.getAttribute('data-dataset-uuid');
        const directory = link.getAttribute('data-directory');
        const downloadUrl = `${getApiBasePath()}/download-dataset-zip.php?dataset_uuid=${encodeURIComponent(datasetUuid)}&directory=${encodeURIComponent(directory)}`;
        window.location.href = downloadUrl;
      });
    });
  </script>
</body>
</html>

