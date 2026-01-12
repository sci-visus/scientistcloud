<?php
/**
 * Admin Portal for ScientistCloud Data Portal
 * Manages system settings, analytics, and administrative functions
 */

require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth.php');
require_once(__DIR__ . '/includes/dataset_manager.php');

// Helper function for admin emails
if (!function_exists('getAdminEmails')) {
    function getAdminEmails() {
        // For now, use environment variable or hardcoded list
        // In production, this should be in a database or config file
        $adminList = getenv('ADMIN_EMAILS');
        if ($adminList) {
            return array_map('trim', explode(',', $adminList));
        }
        
        // Default admin emails (can be overridden by environment variable)
        return [
            'admin@scientistcloud.com',
            'amy@visus.net'
        ];
    }
}

// Start session if not already started
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// Check authentication and admin permissions
$user = getCurrentUser();
if (!$user) {
    // Redirect to login
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
    header('Location: ' . $loginPath . '?redirect=' . urlencode($_SERVER['REQUEST_URI']));
    exit;
}

// Check if user has admin permissions
// For now, check if user email is in admin list (can be moved to database later)
$adminEmails = getAdminEmails();
if (!in_array($user['email'], $adminEmails)) {
    http_response_code(403);
    die('Access denied. Admin privileges required.');
}

// Handle form submissions
$message = '';
$messageType = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['action'])) {
        switch ($_POST['action']) {
            case 'update_analytics':
                $gaTrackingId = trim($_POST['ga_tracking_id'] ?? '');
                if (updateSetting('ga_tracking_id', $gaTrackingId)) {
                    $message = 'Google Analytics tracking ID updated successfully.';
                    $messageType = 'success';
                } else {
                    $message = 'Failed to update Google Analytics tracking ID.';
                    $messageType = 'danger';
                }
                break;
                
            case 'update_settings':
                // Add more settings here as needed
                $message = 'Settings updated successfully.';
                $messageType = 'success';
                break;
        }
    }
}

// Get current settings
$gaTrackingId = getSetting('ga_tracking_id', '');

?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Portal - ScientistCloud</title>
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- FontAwesome Icons -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <!-- Custom CSS -->
  <link href="assets/css/main.css" rel="stylesheet">
</head>
<body>
  <div class="container-fluid p-4">
    <div class="row">
      <div class="col-12">
        <div class="d-flex justify-content-between align-items-center mb-4">
          <h1><i class="fas fa-cog me-2"></i>Admin Portal</h1>
          <div>
            <a href="index.php" class="btn btn-outline-secondary">
              <i class="fas fa-arrow-left"></i> Back to Portal
            </a>
            <a href="logout.php" class="btn btn-outline-danger ms-2">
              <i class="fas fa-sign-out-alt"></i> Logout
            </a>
          </div>
        </div>

        <?php if ($message): ?>
        <div class="alert alert-<?php echo $messageType; ?> alert-dismissible fade show" role="alert">
          <?php echo htmlspecialchars($message); ?>
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        <?php endif; ?>

        <div class="row">
          <!-- Analytics Settings -->
          <div class="col-md-6 mb-4">
            <div class="card">
              <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-chart-line me-2"></i>Google Analytics</h5>
              </div>
              <div class="card-body">
                <p class="text-muted">Configure Google Analytics tracking for the public repository.</p>
                <form method="POST" action="">
                  <input type="hidden" name="action" value="update_analytics">
                  <div class="mb-3">
                    <label for="ga_tracking_id" class="form-label">Google Analytics Tracking ID</label>
                    <input type="text" 
                           class="form-control" 
                           id="ga_tracking_id" 
                           name="ga_tracking_id" 
                           value="<?php echo htmlspecialchars($gaTrackingId); ?>"
                           placeholder="G-XXXXXXXXXX or UA-XXXXXXXXX-X">
                    <small class="form-text text-muted">
                      Enter your Google Analytics 4 (G-XXXXXXXXXX) or Universal Analytics (UA-XXXXXXXXX-X) tracking ID.
                      Leave empty to disable tracking.
                    </small>
                  </div>
                  <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save"></i> Save Settings
                  </button>
                </form>
              </div>
            </div>
          </div>

          <!-- System Information -->
          <div class="col-md-6 mb-4">
            <div class="card">
              <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-info-circle me-2"></i>System Information</h5>
              </div>
              <div class="card-body">
                <dl class="row">
                  <dt class="col-sm-5">Current User:</dt>
                  <dd class="col-sm-7"><?php echo htmlspecialchars($user['email']); ?></dd>
                  
                  <dt class="col-sm-5">PHP Version:</dt>
                  <dd class="col-sm-7"><?php echo PHP_VERSION; ?></dd>
                  
                  <dt class="col-sm-5">Server:</dt>
                  <dd class="col-sm-7"><?php echo htmlspecialchars(SC_SERVER_URL); ?></dd>
                  
                  <dt class="col-sm-5">SCLib API:</dt>
                  <dd class="col-sm-7">
                    <?php
                    try {
                        $sclib = getSCLibClient();
                        $health = $sclib->makeRequest('/health', 'GET');
                        echo '<span class="badge bg-success">Connected</span>';
                    } catch (Exception $e) {
                        echo '<span class="badge bg-danger">Disconnected</span>';
                    }
                    ?>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <!-- Future Admin Sections -->
        <div class="row">
          <div class="col-12">
            <div class="card">
              <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-list me-2"></i>Additional Admin Functions</h5>
              </div>
              <div class="card-body">
                <p class="text-muted">Additional administrative functions will be added here:</p>
                <ul>
                  <li>User management</li>
                  <li>System logs</li>
                  <li>Dataset statistics</li>
                  <li>Storage management</li>
                  <li>API key management</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>

<?php
/**
 * Get a setting value
 */
function getSetting($key, $default = '') {
    $settingsFile = __DIR__ . '/config/settings.json';
    
    if (file_exists($settingsFile)) {
        $settings = json_decode(file_get_contents($settingsFile), true);
        return $settings[$key] ?? $default;
    }
    
    return $default;
}

/**
 * Update a setting value
 */
function updateSetting($key, $value) {
    $settingsDir = __DIR__ . '/config';
    $settingsFile = $settingsDir . '/settings.json';
    
    // Create config directory if it doesn't exist
    if (!is_dir($settingsDir)) {
        mkdir($settingsDir, 0755, true);
    }
    
    // Load existing settings
    $settings = [];
    if (file_exists($settingsFile)) {
        $settings = json_decode(file_get_contents($settingsFile), true) ?? [];
    }
    
    // Update setting
    $settings[$key] = $value;
    
    // Save settings
    return file_put_contents($settingsFile, json_encode($settings, JSON_PRETTY_PRINT)) !== false;
}
?>

