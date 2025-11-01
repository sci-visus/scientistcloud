<?php

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

require_once(__DIR__ . '/../config_auth0.php'); // Setup SDK
require_once(__DIR__ . '/../includes/sclib_client.php');

global $auth0;

try {
    $auth0->exchange();
    $userInfo = $auth0->getUser();

    if (!$userInfo || !isset($userInfo['email'])) {
        throw new Exception("User info not returned by Auth0");
    }

    $user_email = $userInfo['email'];
    $user_name = $userInfo['name'] ?? $userInfo['email'];
    $_SESSION['access_token'] = $auth0->getAccessToken();
    $_SESSION['token_expires_at'] = isset($userInfo['exp']) ? $userInfo['exp'] : (time() + 3600);

    // Get refresh token if available
    $refresh_token = method_exists($auth0, 'getRefreshToken') ? $auth0->getRefreshToken() : null;
    if ($refresh_token) {
        $_SESSION['refresh_token'] = $refresh_token;
    }

    logMessage('INFO', 'Auth0 login successful', [
        'email' => $user_email,
        'name' => $user_name
    ]);

    // Generate a user ID from email (consistent ID generation)
    $userId = 'user_' . str_replace(['@', '.'], '_', $user_email);
    
    // Set session variables for ScientistCloud
    // Note: User profile will be created/updated by SCLib when needed
    // For now, we store Auth0 user info in session
    $_SESSION['user_id'] = $userId;
    $_SESSION['user_email'] = $user_email;
    $_SESSION['user_name'] = $user_name;
    $_SESSION['auth0_id'] = $userInfo['sub'] ?? null;
    $_SESSION['auth0_user_info'] = $userInfo; // Store full Auth0 user info
    
    // Store Auth0 tokens for API access
    $_SESSION['auth0_access_token'] = $_SESSION['access_token'];
    if ($refresh_token) {
        $_SESSION['auth0_refresh_token'] = $refresh_token;
    }
    
    logMessage('INFO', 'User authenticated via Auth0', [
        'user_id' => $userId,
        'email' => $user_email,
        'name' => $user_name
    ]);

    // Redirect to main application (portal)
    header('Location: /portal/index.php');
    exit;
    
} catch (Exception $e) {
    logMessage('ERROR', 'Auth0 callback error', ['error' => $e->getMessage()]);
    echo "<h2>Login Error</h2><p>There was a problem signing you in. Please try again.</p>";
    echo "<p>Error: " . htmlspecialchars($e->getMessage()) . "</p>";
    echo "<p><a href='/portal/login.php'>Try again</a></p>";
}
?>
