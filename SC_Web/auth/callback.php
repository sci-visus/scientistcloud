<?php

require_once(__DIR__ . '/../includes/session_cookie_params.php');

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

require_once(__DIR__ . '/../config_auth0.php'); // Setup SDK
require_once(__DIR__ . '/../includes/sclib_client.php'); // Includes getSCLibAuthClient()
require_once(__DIR__ . '/../includes/auth.php');

global $auth0;

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$loginPath = $isLocal ? '/login.php' : '/portal/login.php';
$verifiedLandingPath = $isLocal ? '/login_verification_sent.php' : '/portal/login_verification_sent.php';

if (!empty($_GET['error'])) {
    $errDesc = $_GET['error_description'] ?? '';
    if (scAuth0ErrorIsUnverifiedEmail($_GET['error'], $errDesc)) {
        $errEmail = isset($_GET['email']) ? trim((string) $_GET['email']) : '';
        scRedirectToEmailVerificationPage($errEmail !== '' ? $errEmail : null);
    }
    logMessage('WARNING', 'Auth callback OAuth error', [
        'error' => $_GET['error'],
        'description' => $errDesc,
    ]);
    header('Location: ' . rtrim(SC_SERVER_URL, '/') . $loginPath);
    exit;
}

// Auth0 email-verification link redirect (success=true&code=success) — not an OAuth callback.
if (
    isset($_GET['success']) && $_GET['success'] === 'true'
    && isset($_GET['code']) && $_GET['code'] === 'success'
) {
    $email = isset($_GET['email']) ? trim((string) $_GET['email']) : '';
    if ($email !== '') {
        scClearPendingEmailVerification();
    }
    $query = http_build_query(array_filter([
        'verified' => '1',
        'email' => $email !== '' ? $email : null,
    ]));
    header('Location: ' . rtrim(SC_SERVER_URL, '/') . $verifiedLandingPath . '?' . $query);
    exit;
}

// Real OAuth callbacks must include an authorization code (not the literal "success").
if (!isset($_GET['code']) || $_GET['code'] === 'success') {
    logMessage('WARNING', 'Auth callback hit without OAuth authorization code', [
        'query' => $_GET,
    ]);
    header('Location: ' . rtrim(SC_SERVER_URL, '/') . $loginPath);
    exit;
}

try {
    $auth0->exchange();
    $userInfo = $auth0->getUser();

    if (!$userInfo || !isset($userInfo['email'])) {
        throw new Exception("User info not returned by Auth0");
    }

    $user_email = $userInfo['email'];
    $auth0_sub = $userInfo['sub'] ?? '';
    $email_verified = !empty($userInfo['email_verified']);
    $is_database_user = (str_starts_with($auth0_sub, 'auth0|'));

    if ($is_database_user && !$email_verified) {
        scRedirectToEmailVerificationPage($user_email);
    }
    scClearPendingEmailVerification();
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
    $auth0_sub = $auth0_sub !== '' ? $auth0_sub : $userId;
    
    // Create or update user in SCLib using user_profile collection
    try {
        // Use auth client for auth endpoints (port 8001)
        $sclib = getSCLibAuthClient();
        
        // Check if API is accessible before attempting to create user
        logMessage('INFO', 'Checking SCLib Auth API health', ['email' => $user_email]);
        $healthCheck = $sclib->healthCheck();
        if (!$healthCheck) {
            logMessage('WARNING', 'SCLib Auth API health check failed', ['email' => $user_email]);
            // Continue anyway - might be temporary
        }
        
        // Prepare user data for SCLib
        $userData = [
            'email' => $user_email,
            'name' => $user_name,
            'auth0_id' => $auth0_sub,
            'sub' => $auth0_sub,
            'picture' => $userInfo['picture'] ?? null,
            'email_verified' => $userInfo['email_verified'] ?? false,
            'auth0_metadata' => $userInfo
        ];
        
        logMessage('INFO', 'Attempting to create user in SCLib', ['email' => $user_email]);
        
        // Create or update user in SCLib
        $createResult = $sclib->createUser($userData);
        
        if (!$createResult || !isset($createResult['success']) || !$createResult['success']) {
            $errorMsg = $createResult['error'] ?? 'Unknown error';
            logMessage('ERROR', 'Failed to create user in SCLib', [
                'email' => $user_email,
                'error' => $errorMsg
            ]);
            throw new Exception("Failed to create user in SCLib: " . $errorMsg);
        }
        
        logMessage('INFO', 'User created/updated in SCLib', [
            'email' => $user_email,
            'user_id' => $createResult['user_id'] ?? $userId
        ]);
        
        // Use the user_id from SCLib if provided
        if (isset($createResult['user_id'])) {
            $userId = $createResult['user_id'];
        }
        
    } catch (Exception $e) {
        logMessage('ERROR', 'SCLib user creation error', [
            'email' => $user_email,
            'error' => $e->getMessage()
        ]);
        // Re-throw to show error to user
        throw new Exception("Authentication service error: " . $e->getMessage());
    }
    
    // Set session variables for ScientistCloud
    $_SESSION['user_id'] = $userId;
    $_SESSION['user_email'] = $user_email;
    $_SESSION['user_name'] = $user_name;
    $_SESSION['auth0_id'] = $auth0_sub;
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

    setDashboardAuthCookie($user_email, $userId);

    header('Location: ' . getPostLoginRedirectUrl());
    exit;
    
} catch (Exception $e) {
    logMessage('ERROR', 'Auth0 callback error', ['error' => $e->getMessage()]);
    echo "<h2>Login Error</h2><p>There was a problem signing you in. Please try again.</p>";
    echo "<p>Error: " . htmlspecialchars($e->getMessage()) . "</p>";
    echo "<p><a href='" . $loginPath . "'>Try again</a></p>";
}
?>
