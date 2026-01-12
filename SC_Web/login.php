<?php
/**
 * Login Page for ScientistCloud Data Portal
 * Handles user authentication via Auth0
 */

// Start session VERY FIRST
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

// Load configuration and Auth0 initialization
require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/config_auth0.php'); // Setup SDK
require_once(__DIR__ . '/includes/auth.php');

global $auth0;

if (!isset($_SESSION['CREATED'])) {
    $_SESSION['CREATED'] = time();
} else if (time() - $_SESSION['CREATED'] > 1600) {
    session_regenerate_id(true);
    $_SESSION['CREATED'] = time();
}

// Check if this is a public repository login request
$isPublicRepo = isset($_GET['public_repo']) || isset($_SESSION['public_repo_requested']);

// Check if user is already authenticated
// isAuthenticated() now verifies getCurrentUser(), so this should be safe
if (isAuthenticated()) {
    // If public repo requested, set session flag
    if ($isPublicRepo) {
        $_SESSION['user_type'] = 'public_repo';
        $_SESSION['public_repo_access'] = true;
        $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
        $publicRepoPath = $isLocal ? '/public-repo.php' : '/portal/public-repo.php';
        header('Location: ' . $publicRepoPath);
        exit;
    }
    
    // User is authenticated, redirect to index
    // For local development, use /index.php (no /portal/ prefix)
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $indexPath = $isLocal ? '/index.php' : '/portal/index.php';
    header('Location: ' . $indexPath);
    exit;
}

// Store public repo request in session for callback
if ($isPublicRepo) {
    $_SESSION['public_repo_requested'] = true;
}

// Always redirect to Auth0 login (don't check getUser first, as it might be empty after callback)
// Check if we're coming back from Auth0 callback (has code parameter)
if (!isset($_GET['code'])) {
    // Not coming from callback, redirect to Auth0
    try {
        // Determine callback URL based on environment
        // For local development (localhost), use /auth/callback.php (no /portal/ prefix)
        // For server, use /portal/auth/callback.php
        $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
        $callbackPath = $isLocal ? '/auth/callback.php' : '/portal/auth/callback.php';
        $callbackUrl = SC_SERVER_URL . $callbackPath;
        
        $loginUrl = $auth0->login(
            $callbackUrl,
            [
                'prompt' => 'consent',
                'access_type' => 'offline',
                'scope' => 'openid profile email offline_access https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.send'
            ]
        );
        
        if ($loginUrl) {
            header('Location: ' . $loginUrl);
            exit;
        } else {
            error_log("Auth0 login() returned empty URL");
            throw new Exception("Failed to generate Auth0 login URL");
        }
    } catch (Exception $e) {
        error_log("Auth0 login error: " . $e->getMessage());
        $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
        $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
        echo "<h2>Login Error</h2><p>Failed to redirect to Auth0: " . htmlspecialchars($e->getMessage()) . "</p>";
        echo "<p><a href='" . $loginPath . "'>Try again</a></p>";
        exit;
    }
} else {
    // We have a code parameter, might be from Auth0 callback
    // Redirect to callback handler
    // For local development, use /auth/callback.php (no /portal/ prefix)
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $callbackPath = $isLocal ? '/auth/callback.php' : '/portal/auth/callback.php';
    header('Location: ' . $callbackPath . '?' . $_SERVER['QUERY_STRING']);
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - ScientistCloud Data Portal</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- FontAwesome Icons -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 1rem;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            padding: 2rem;
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .login-header h1 {
            color: #333;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .login-header p {
            color: #666;
            margin-bottom: 0;
        }
        
        .spinner {
            width: 3rem;
            height: 3rem;
            border: 0.3rem solid #f3f3f3;
            border-top: 0.3rem solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .login-footer {
            text-align: center;
            margin-top: 2rem;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1><i class="fas fa-cloud"></i> ScientistCloud</h1>
            <p>Data Portal Login</p>
        </div>
        
        <div class="spinner"></div>
        <p>Redirecting to secure login...</p>
        <p class="text-muted">You will be redirected to Auth0 for authentication.</p>
        
        <div class="login-footer">
            <p>If you are not redirected automatically, <a href="#" onclick="window.location.reload()">click here</a></p>
        </div>
    </div>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
