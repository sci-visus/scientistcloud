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

    // Use SCLib to handle user authentication and profile management
    try {
        $sclib = getSCLibClient();
        
        // Check if user exists in SCLib system
        $existingUser = $sclib->getUserProfileByEmail($user_email);
        
        if (!$existingUser) {
            // Create new user in SCLib system
            $newUser = [
                'email' => $user_email,
                'name' => $user_name,
                'auth0_id' => $userInfo['sub'] ?? null,
                'preferences' => [
                    'preferred_dashboard' => DEFAULT_DASHBOARD
                ],
                'permissions' => ['read', 'upload'],
                'created_at' => date('Y-m-d H:i:s'),
                'last_logged_in' => date('Y-m-d H:i:s')
            ];
            
            $userResult = $sclib->createUser($newUser);
            if (!$userResult['success']) {
                throw new Exception("Failed to create user in SCLib: " . $userResult['error']);
            }
            
            $userId = $userResult['user_id'];
            logMessage('INFO', 'New user created', ['user_id' => $userId, 'email' => $user_email]);
        } else {
            // Update existing user's last login
            $userId = $existingUser['id'];
            $sclib->updateUserLastLogin($userId);
            logMessage('INFO', 'Existing user logged in', ['user_id' => $userId, 'email' => $user_email]);
        }
        
        // Set session variables for ScientistCloud
        $_SESSION['user_id'] = $userId;
        $_SESSION['user_email'] = $user_email;
        $_SESSION['user_name'] = $user_name;
        $_SESSION['auth0_id'] = $userInfo['sub'] ?? null;
        
        // Store Auth0 tokens for API access
        $_SESSION['auth0_access_token'] = $_SESSION['access_token'];
        if ($refresh_token) {
            $_SESSION['auth0_refresh_token'] = $refresh_token;
        }
        
    } catch (Exception $e) {
        logMessage('ERROR', 'SCLib authentication failed', [
            'email' => $user_email,
            'error' => $e->getMessage()
        ]);
        throw new Exception("Authentication service error: " . $e->getMessage());
    }

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
