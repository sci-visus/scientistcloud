<?php
/**
 * Login Page for ScientistCloud Data Portal
 * Handles user authentication via Auth0
 */

require_once(__DIR__ . '/includes/session_cookie_params.php');

// Start session after cookie params (path=/ for /portal and /dashboard)
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

// Remember dashboard (or other) URL to open after login
if (!empty($_GET['return_to'])) {
    storeLoginReturnTo($_GET['return_to']);
}

$chooseAccount = shouldPromptAccountSelection();
$googleConnection = isset($_GET['connection']) && $_GET['connection'] === 'google-oauth2';

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$verifiedLandingPath = $isLocal ? '/login_verification_sent.php' : '/portal/login_verification_sent.php';

// Auth0 blocked login (unverified email) — stay on portal instead of looping back to Auth0.
if (!empty($_GET['error']) && scAuth0ErrorIsUnverifiedEmail($_GET['error'], $_GET['error_description'] ?? '')) {
    $errEmail = isset($_GET['email']) ? trim((string) $_GET['email']) : '';
    scRedirectToEmailVerificationPage($errEmail !== '' ? $errEmail : null);
}

// Check if user is already authenticated (skip when switching accounts)
if (isAuthenticated() && !$chooseAccount) {
    setDashboardAuthCookieFromSession();
    header('Location: ' . getPostLoginRedirectUrl());
    exit;
}

if ($chooseAccount && isAuthenticated()) {
    $savedReturnTo = $_SESSION['login_return_to'] ?? null;
    scClearLocalAuthState(true);
    if ($savedReturnTo) {
        storeLoginReturnTo($savedReturnTo);
    }
    try {
        $auth0->clear();
    } catch (Throwable $e) {
        error_log('Auth0 clear before account switch: ' . $e->getMessage());
    }
}

if ($chooseAccount || $googleConnection) {
    scClearPendingEmailVerification();
}

// Email verification complete (Auth0 Redirect To should be login.php, not callback.php)
if (isset($_GET['success']) && $_GET['success'] === 'true' && isset($_GET['code']) && $_GET['code'] === 'success') {
    $email = isset($_GET['email']) ? trim((string) $_GET['email']) : '';
    scClearPendingEmailVerification();
    $query = http_build_query(array_filter([
        'verified' => '1',
        'email' => $email !== '' ? $email : null,
    ]));
    header('Location: ' . rtrim(SC_SERVER_URL, '/') . $verifiedLandingPath . '?' . $query);
    exit;
}

// OAuth authorization code (long string) — forward to callback; not email verification (code=success)
$hasOAuthCode = isset($_GET['code']) && $_GET['code'] !== '' && $_GET['code'] !== 'success';

// Do not auto-redirect to Auth0 while email verification is still pending (prevents login loop).
if (!$hasOAuthCode && scHasPendingEmailVerification() && !$chooseAccount && !$googleConnection && empty($_GET['verification_retry'])) {
    scRedirectToEmailVerificationPage((string) $_SESSION['pending_verification_email']);
}

if (!empty($_GET['verification_retry']) && $_GET['verification_retry'] === '1') {
    scClearPendingEmailVerification();
}

if (!$hasOAuthCode) {
    // Not coming from callback, redirect to Auth0
    try {
        // Determine callback URL based on environment
        // For local development (localhost), use /auth/callback.php (no /portal/ prefix)
        // For server, use /portal/auth/callback.php
        $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
        $callbackPath = $isLocal ? '/auth/callback.php' : '/portal/auth/callback.php';
        $callbackUrl = rtrim(SC_SERVER_URL, '/') . $callbackPath;
        
        // Do not force prompt=consent on every login — it breaks some database sign-up flows.
        // Google Drive consent is requested when needed via connection=google-oauth2.
        // choose_account=1 shows Auth0 / Google account picker (see logged_out.php).
        $loginUrl = $auth0->login(
            $callbackUrl,
            buildAuth0LoginParams($chooseAccount, $googleConnection ? 'google-oauth2' : null)
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
