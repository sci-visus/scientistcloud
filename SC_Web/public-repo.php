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

// Public repository - no authentication required
// Set user type to public_repo for UI behavior
$_SESSION['user_type'] = 'public_repo';
$_SESSION['public_repo_access'] = true;

// Try to get user if logged in (optional - for share functionality)
$user = getCurrentUser();

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
  <?php
  // Load Google Analytics tracking ID from settings
  $settingsFile = __DIR__ . '/logs/settings.json';
  $gaTrackingId = '';
  if (file_exists($settingsFile)) {
      $settings = json_decode(file_get_contents($settingsFile), true);
      $gaTrackingId = $settings['ga_tracking_id'] ?? '';
  }
  
  // Add Google Analytics if tracking ID is configured
  if ($gaTrackingId): ?>
  <!-- Google Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=<?php echo htmlspecialchars($gaTrackingId); ?>"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', '<?php echo htmlspecialchars($gaTrackingId); ?>', {
      'page_path': window.location.pathname + window.location.search
    });
  </script>
  <?php endif; ?>
</head>
<body class="public-repo">
  <!-- Left Sidebar -->
  <aside class="sidebar d-flex flex-column align-items-center" id="folderSidebar">
    <img src="assets/images/scientistcloud-logo.png" class="logo" alt="ScientistCloud Logo">
    <div class="d-flex align-items-center justify-content-between w-100 px-2 mb-2">
      <h5 class="mb-0" style="color: var(--fg-color);">
        <i class="fas fa-globe me-2" style="color: var(--primary-color);"></i>Public Datasets
      </h5>
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
        <div class="d-flex align-items-center me-3">
          <span class="badge bg-primary me-2" style="background-color: var(--primary-color) !important; font-size: 0.75rem; padding: 0.35rem 0.65rem;">
            <i class="fas fa-globe me-1"></i>PUBLIC REPOSITORY
          </span>
        </div>
        <label for="viewerType">Dashboard:</label>
        <select id="viewerType" class="form-select form-select-sm">
          <!-- Options will be populated dynamically by viewer-manager.js -->
          <option value="">Loading dashboards...</option>
        </select>
        <div class="btn-group ms-auto" role="group" aria-label="User actions">
          <button type="button" class="btn btn-outline-light" id="shareBtn" title="Share Repository Link">
            <i class="fas fa-share-alt"></i> Share Link
          </button>
          <?php if ($user): ?>
          <a href="index.php" class="btn btn-outline-light" title="Back to Portal">
            <i class="fas fa-arrow-left"></i> Back to Portal
          </a>
          <button type="button" class="btn btn-outline-light" id="logoutBtn" title="Logout">
            <i class="fas fa-sign-out-alt"></i> Logout
          </button>
          <?php else: ?>
          <a href="login.php" class="btn btn-outline-light" title="Login">
            <i class="fas fa-sign-in-alt"></i> Login
          </a>
          <?php endif; ?>
        </div>
      </div>
    </div>
    <!-- Error Display Banner -->
    <div id="errorBanner" class="alert alert-danger alert-dismissible fade show" role="alert" style="display: none; margin: 10px; position: sticky; top: 0; z-index: 1000;">
      <strong>Error:</strong> <span id="errorMessage"></span>
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
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

  <!-- Share Modal -->
  <div class="modal fade" id="shareModal" tabindex="-1" aria-labelledby="shareModalLabel" aria-hidden="true">
    <div class="modal-dialog">
      <div class="modal-content" style="background-color: var(--panel-bg); border-color: var(--panel-border); color: var(--fg-color);">
        <div class="modal-header" style="border-bottom-color: var(--panel-border);">
          <h5 class="modal-title" id="shareModalLabel" style="color: var(--fg-color);">
            <i class="fas fa-share-alt me-2"></i>Share Public Repository
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" style="filter: invert(1);"></button>
        </div>
        <div class="modal-body">
          <p class="text-muted" style="color: var(--fg-color); opacity: 0.7;">
            Generate a shareable link to a specific folder or team's public datasets.
          </p>
          
          <div class="mb-3">
            <label for="shareType" class="form-label" style="color: var(--fg-color);">Share Type:</label>
            <select class="form-select" id="shareType" style="background-color: var(--bg-color); border-color: var(--panel-border); color: var(--fg-color);">
              <option value="folder">Folder</option>
              <option value="team">Team</option>
            </select>
          </div>
          
          <div class="mb-3" id="folderSelectContainer">
            <label for="shareFolder" class="form-label" style="color: var(--fg-color);">Select Folder:</label>
            <select class="form-select" id="shareFolder" style="background-color: var(--bg-color); border-color: var(--panel-border); color: var(--fg-color);">
              <option value="">Loading folders...</option>
            </select>
          </div>
          
          <div class="mb-3" id="teamSelectContainer" style="display: none;">
            <label for="shareTeam" class="form-label" style="color: var(--fg-color);">Select Team:</label>
            <select class="form-select" id="shareTeam" style="background-color: var(--bg-color); border-color: var(--panel-border); color: var(--fg-color);">
              <option value="">Loading teams...</option>
            </select>
          </div>
          
          <div class="mb-3" id="shareLinkContainer" style="display: none;">
            <label for="shareLink" class="form-label" style="color: var(--fg-color);">Shareable Link:</label>
            <div class="input-group">
              <input type="text" class="form-control" id="shareLink" readonly style="background-color: var(--bg-color); border-color: var(--panel-border); color: var(--fg-color);">
              <button class="btn btn-outline-secondary" type="button" id="copyLinkBtn" style="border-color: var(--panel-border); color: var(--fg-color);">
                <i class="fas fa-copy"></i> Copy
              </button>
            </div>
            <small class="form-text text-muted" style="color: var(--fg-color); opacity: 0.7;">
              Share this link to show only datasets from the selected folder or team.
            </small>
          </div>
        </div>
        <div class="modal-footer" style="border-top-color: var(--panel-border);">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" style="background-color: var(--panel-bg); border-color: var(--panel-border); color: var(--fg-color);">Close</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="assets/js/main.js"></script>
  <script src="assets/js/dataset-manager.js"></script>
  <script src="assets/js/viewer-manager.js"></script>
  <script>
    // Global error handler to display errors visibly
    window.showError = function(message) {
      console.error('🚨 ERROR:', message);
      const banner = document.getElementById('errorBanner');
      const messageEl = document.getElementById('errorMessage');
      if (banner && messageEl) {
        messageEl.textContent = message;
        banner.style.display = 'block';
        // Auto-hide after 10 seconds
        setTimeout(() => {
          if (banner) banner.style.display = 'none';
        }, 10000);
      }
    };
    
    // Catch all unhandled errors
    window.addEventListener('error', function(event) {
      showError('JavaScript Error: ' + (event.message || 'Unknown error') + ' at ' + (event.filename || 'unknown') + ':' + (event.lineno || '?'));
    });
    
    // Catch unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {
      showError('Unhandled Promise Rejection: ' + (event.reason?.message || event.reason || 'Unknown error'));
    });
    
    // Debug: Verify scripts loaded - this should ALWAYS show up
    console.log('🔍 PUBLIC-REPO.PHP SCRIPT LOADED');
    console.log('🔍 Script loading check:');
    console.log('  - window.viewerManager:', typeof window.viewerManager);
    console.log('  - window.datasetManager:', typeof window.datasetManager);
    console.log('  - viewerType element:', !!document.getElementById('viewerType'));
    
    // Set global flag for public repo user
    window.isPublicRepoUser = true;
    
    // Force populate dropdown after a delay if viewerManager exists
    setTimeout(() => {
      console.log('⏰ 3 second check - viewerManager state:');
      console.log('  - window.viewerManager exists:', !!window.viewerManager);
      if (window.viewerManager) {
        console.log('  - viewers count:', Object.keys(window.viewerManager.viewers || {}).length);
        console.log('  - viewers:', Object.keys(window.viewerManager.viewers || {}));
        
        const viewerType = document.getElementById('viewerType');
        if (viewerType) {
          console.log('  - dropdown options:', viewerType.options.length);
          if (viewerType.options.length <= 1) {
            console.log('⚠️ Dropdown still empty, forcing populateViewerSelector...');
            if (window.viewerManager.populateViewerSelector) {
              window.viewerManager.populateViewerSelector();
            }
            // Also try manual load
            if (window.viewerManager.loadDashboards) {
              console.log('🔄 Manually calling loadDashboards...');
              window.viewerManager.loadDashboards();
            }
          }
        }
      }
    }, 3000);
    
    // Test if we can manually call the API - try both paths
    setTimeout(() => {
      console.log('🧪 Testing manual API call...');
      
      // Try /portal/api first (what the code uses)
      const apiUrl1 = '/portal/api/dashboards.php';
      console.log('🧪 Trying:', apiUrl1);
      fetch(apiUrl1, { credentials: 'include' })
        .then(r => {
          console.log('🧪 Path 1 response:', r.status, r.statusText, r.url);
          if (r.ok) {
            return r.json();
          } else {
            throw new Error(`HTTP ${r.status}: ${r.statusText}`);
          }
        })
        .then(data => {
          console.log('✅ Path 1 SUCCESS! Data:', data);
          console.log('✅ Dashboards found:', data.dashboards?.length || 0);
        })
        .catch(err => {
          const errorMsg = 'API Path 1 failed: ' + (err.message || err);
          console.error('❌', errorMsg, err);
          if (window.showError) {
            window.showError(errorMsg);
          }
          
          // Try /api as fallback
          const apiUrl2 = '/api/dashboards.php';
          console.log('🧪 Trying fallback:', apiUrl2);
          fetch(apiUrl2, { credentials: 'include' })
            .then(r => {
              console.log('🧪 Path 2 response:', r.status, r.statusText, r.url);
              return r.json();
            })
            .then(data => {
              console.log('✅ Path 2 SUCCESS! Data:', data);
              console.log('✅ Dashboards found:', data.dashboards?.length || 0);
            })
            .catch(err2 => {
              const errorMsg2 = 'API Path 2 also failed: ' + (err2.message || err2);
              console.error('❌', errorMsg2, err2);
              if (window.showError) {
                window.showError(errorMsg2);
              }
            });
        });
    }, 1000);
    
    // Force dashboard load after a short delay if not already loaded
    setTimeout(() => {
      const viewerType = document.getElementById('viewerType');
      if (viewerType && viewerType.options.length === 1 && viewerType.options[0].textContent.includes('Loading')) {
        console.log('⚠️ Dashboards still loading after 2 seconds, forcing reload...');
        if (window.viewerManager && typeof window.viewerManager.loadDashboards === 'function') {
          console.log('🔄 Manually calling loadDashboards()...');
          window.viewerManager.loadDashboards().then(() => {
            console.log('✅ Manual loadDashboards() completed');
          }).catch(err => {
            const errorMsg = 'Manual loadDashboards() failed: ' + (err.message || err);
            console.error('❌', errorMsg, err);
            if (window.showError) {
              window.showError(errorMsg);
            }
          });
        } else {
          const errorMsg = 'viewerManager not available for manual load';
          console.error('❌', errorMsg);
          if (window.showError) {
            window.showError(errorMsg);
          }
        }
      }
    }, 2000);
    
    // Helper function to get API base path
    function getApiBasePath() {
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      return isLocal ? '/api' : '/portal/api';
    }

    // Share functionality
    let shareModal = null;
    let folders = [];
    let teams = [];

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
      // Initialize Bootstrap modal
      shareModal = new bootstrap.Modal(document.getElementById('shareModal'));
      
      // Share button handler
      const shareBtn = document.getElementById('shareBtn');
      if (shareBtn) {
        shareBtn.addEventListener('click', () => {
          <?php if ($user): ?>
          // User is logged in - show folder/team selection modal
          loadShareOptions();
          shareModal.show();
          <?php else: ?>
          // No login - just copy current page URL
          const currentUrl = window.location.href;
          copyUrlToClipboard(currentUrl);
          <?php endif; ?>
        });
      }
      
      // Share type change handler
      document.getElementById('shareType')?.addEventListener('change', (e) => {
        const shareType = e.target.value;
        document.getElementById('folderSelectContainer').style.display = shareType === 'folder' ? 'block' : 'none';
        document.getElementById('teamSelectContainer').style.display = shareType === 'team' ? 'block' : 'none';
        document.getElementById('shareLinkContainer').style.display = 'none';
      });
      
      // Folder/Team select handlers
      document.getElementById('shareFolder')?.addEventListener('change', generateShareLink);
      document.getElementById('shareTeam')?.addEventListener('change', generateShareLink);
      
      // Copy link button handler
      document.getElementById('copyLinkBtn')?.addEventListener('click', copyShareLink);
      
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
      
      // Copy URL to clipboard helper (for non-logged-in users)
      async function copyUrlToClipboard(url) {
        try {
          await navigator.clipboard.writeText(url);
          const shareBtn = document.getElementById('shareBtn');
          if (shareBtn) {
            const originalHTML = shareBtn.innerHTML;
            shareBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            shareBtn.classList.add('btn-success');
            shareBtn.classList.remove('btn-outline-light');
            
            setTimeout(() => {
              shareBtn.innerHTML = originalHTML;
              shareBtn.classList.remove('btn-success');
              shareBtn.classList.add('btn-outline-light');
            }, 2000);
          }
        } catch (error) {
          console.error('Failed to copy URL:', error);
          alert('Failed to copy link. Please copy manually: ' + url);
        }
      }
    });
    
    // Load folders and teams for sharing
    async function loadShareOptions() {
      try {
        const response = await fetch(`${getApiBasePath()}/get-public-folders-teams.php`, {
          credentials: 'include'
        });
        
        if (!response.ok) {
          throw new Error('Failed to load share options');
        }
        
        const data = await response.json();
        
        if (data.success) {
          folders = data.folders || [];
          teams = data.teams || [];
          
          // Populate folder dropdown
          const folderSelect = document.getElementById('shareFolder');
          if (folderSelect) {
            folderSelect.innerHTML = '<option value="">Select a folder...</option>';
            if (folders.length === 0) {
              folderSelect.innerHTML += '<option value="" disabled>No folders with public datasets</option>';
            } else {
              folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.uuid;
                option.textContent = folder.name;
                folderSelect.appendChild(option);
              });
            }
          }
          
          // Populate team dropdown
          const teamSelect = document.getElementById('shareTeam');
          if (teamSelect) {
            teamSelect.innerHTML = '<option value="">Select a team...</option>';
            if (teams.length === 0) {
              teamSelect.innerHTML += '<option value="" disabled>No teams with public datasets</option>';
            } else {
              teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team.uuid;
                option.textContent = team.name;
                teamSelect.appendChild(option);
              });
            }
          }
        }
      } catch (error) {
        console.error('Error loading share options:', error);
        alert('Failed to load folders and teams. Please try again.');
      }
    }
    
    // Generate shareable link
    function generateShareLink() {
      const shareType = document.getElementById('shareType').value;
      const shareLinkContainer = document.getElementById('shareLinkContainer');
      const shareLinkInput = document.getElementById('shareLink');
      
      let link = window.location.origin + window.location.pathname;
      let selectedValue = '';
      
      if (shareType === 'folder') {
        selectedValue = document.getElementById('shareFolder').value;
        if (selectedValue) {
          link += `?folder=${encodeURIComponent(selectedValue)}`;
        }
      } else if (shareType === 'team') {
        selectedValue = document.getElementById('shareTeam').value;
        if (selectedValue) {
          link += `?team=${encodeURIComponent(selectedValue)}`;
        }
      }
      
      if (selectedValue) {
        shareLinkInput.value = link;
        shareLinkContainer.style.display = 'block';
      } else {
        shareLinkContainer.style.display = 'none';
      }
    }
    
    // Copy share link to clipboard
    async function copyShareLink() {
      const shareLinkInput = document.getElementById('shareLink');
      const copyBtn = document.getElementById('copyLinkBtn');
      
      try {
        await navigator.clipboard.writeText(shareLinkInput.value);
        const originalHTML = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
        copyBtn.classList.add('btn-success');
        copyBtn.classList.remove('btn-outline-secondary');
        
        setTimeout(() => {
          copyBtn.innerHTML = originalHTML;
          copyBtn.classList.remove('btn-success');
          copyBtn.classList.add('btn-outline-secondary');
        }, 2000);
      } catch (error) {
        console.error('Failed to copy link:', error);
        // Fallback: select text
        shareLinkInput.select();
        shareLinkInput.setSelectionRange(0, 99999);
        document.execCommand('copy');
        alert('Link copied to clipboard!');
      }
    }
  </script>
</body>
</html>
