<?php
/**
 * Start Auth0 username/password (database) signup — not Google social login.
 * Use this URL instead of "Sign up" on the login screen when database signup fails
 * or when you need the Username-Password connection explicitly.
 */
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/config_auth0.php');
require_once(__DIR__ . '/includes/auth.php');

global $auth0;

if (isAuthenticated()) {
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    header('Location: ' . ($isLocal ? '/index.php' : '/portal/index.php'));
    exit;
}

try {
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $callbackPath = $isLocal ? '/auth/callback.php' : '/portal/auth/callback.php';
    $callbackUrl = rtrim(SC_SERVER_URL, '/') . $callbackPath;

    $loginUrl = $auth0->login(
        $callbackUrl,
        [
            'screen_hint' => 'signup',
            'connection' => 'Username-Password-Authentication',
            'scope' => 'openid profile email offline_access https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.send',
        ]
    );

    if (!$loginUrl) {
        throw new RuntimeException('Auth0 did not return a signup URL');
    }

    header('Location: ' . $loginUrl);
    exit;
} catch (Throwable $e) {
    error_log('signup.php Auth0 error: ' . $e->getMessage());
    $loginPath = (strpos(SC_SERVER_URL, 'localhost') !== false) ? '/login.php' : '/portal/login.php';
    http_response_code(500);
    echo '<h2>Sign up unavailable</h2>';
    echo '<p>' . htmlspecialchars($e->getMessage()) . '</p>';
    echo '<p><a href="' . htmlspecialchars($loginPath) . '">Back to login</a></p>';
}
