<?php
/**
 * Authentication Module for ScientistCloud Data Portal
 * Delegates ALL authentication operations to SCLib API - no direct MongoDB access
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/sclib_client.php');

/**
 * Get current authenticated user
 */
function getCurrentUser() {
    // First try to authenticate from Auth0 session
    $user = authenticateUserFromSession();
    if ($user) {
        return $user;
    }
    
        // Fallback to legacy session check - use email as primary identifier
        if (!isset($_SESSION['user_email'])) {
            return null;
        }
        
        try {
            // Use auth client for auth endpoints (port 8001)
            $sclib = getSCLibAuthClient();
            $user = $sclib->getUserProfileByEmail($_SESSION['user_email']);
        
        if ($user) {
            return [
                'id' => $user['id'],
                'email' => $user['email'],
                'name' => $user['name'],
                'preferred_dashboard' => $user['preferences']['preferred_dashboard'] ?? DEFAULT_DASHBOARD,
                'team_id' => $user['team_id'],
                'permissions' => $user['permissions'] ?? ['read', 'upload']
            ];
        }
        
        return null;
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get current user', ['error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Authenticate user with Auth0
 */
function authenticateUser($auth0_token) {
    try {
        // Validate Auth0 token using SCLib Auth API (port 8001)
        $sclib = getSCLibAuthClient();
        $authResult = $sclib->validateAuthToken($auth0_token);
        
        if (!$authResult['success'] || !$authResult['valid']) {
            return false;
        }
        
        $userEmail = $authResult['email'] ?? null;
        if (!$userEmail) {
            return false;
        }
        
        // Get user profile from SCLib using email (primary identifier)
        $user = $sclib->getUserProfileByEmail($userEmail);
        if (!$user) {
            return false;
        }
        
        // Set session
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user_email'] = $user['email'];
        $_SESSION['user_name'] = $user['name'];
        
        return [
            'id' => $user['id'],
            'email' => $user['email'],
            'name' => $user['name'],
            'preferred_dashboard' => $user['preferences']['preferred_dashboard'] ?? DEFAULT_DASHBOARD,
            'team_id' => $user['team_id'],
            'permissions' => $user['permissions'] ?? ['read', 'upload']
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Authentication failed', ['error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Authenticate user with Auth0 session
 */
function authenticateUserFromSession() {
    try {
        // Check if we have Auth0 session data - email is primary identifier
        if (!isset($_SESSION['user_email'])) {
            return null;
        }
        
        // If we have session data from callback, create a minimal user object
        // This avoids API calls during the redirect loop
        if (isset($_SESSION['user_email']) && isset($_SESSION['user_id']) && isset($_SESSION['user_name'])) {
            // Return user from session if we have all required data
            // This allows the callback redirect to work even if API is slow
            return [
                'id' => $_SESSION['user_id'],
                'email' => $_SESSION['user_email'],
                'name' => $_SESSION['user_name'],
                'preferred_dashboard' => $_SESSION['preferred_dashboard'] ?? DEFAULT_DASHBOARD,
                'team_id' => $_SESSION['team_id'] ?? null,
                'permissions' => $_SESSION['permissions'] ?? ['read', 'upload']
            ];
        }
        
        $userEmail = $_SESSION['user_email'];
        
        // Get user profile from SCLib Auth API using email (primary identifier)
        $sclib = getSCLibAuthClient();
        $user = $sclib->getUserProfileByEmail($userEmail);
        
        if (!$user) {
            return false;
        }
        
        return [
            'id' => $user['id'],
            'email' => $user['email'],
            'name' => $user['name'],
            'preferred_dashboard' => $user['preferences']['preferred_dashboard'] ?? DEFAULT_DASHBOARD,
            'team_id' => $user['team_id'],
            'permissions' => $user['permissions'] ?? ['read', 'upload']
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Session authentication failed', ['error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Get user by email - delegate to SCLib
 */
function getUserByEmail($email) {
    try {
        // SCLib Auth API provides endpoint to get user by email
        $sclib = getSCLibAuthClient();
        $user = $sclib->getUserProfileByEmail($email);
        return $user;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get user by email', ['email' => $email, 'error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Create new user - delegate to SCLib
 */
function createUser($userInfo) {
    try {
        // SCLib should handle user creation through its user management system
        // For now, we'll use a mock implementation
        
        // TODO: Implement create user in SCLib API
        // This would be a new endpoint: /api/auth/create-user
        
        // For now, return a mock user
        return [
            'id' => 'mock-user-' . time(),
            'email' => $userInfo['email'],
            'name' => $userInfo['name'] ?? $userInfo['email'],
            'preferred_dashboard' => DEFAULT_DASHBOARD,
            'team_id' => null,
            'permissions' => ['read', 'upload']
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to create user', ['error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Check if user has permission
 */
function hasPermission($permission) {
    $user = getCurrentUser();
    if (!$user) {
        return false;
    }
    
    return in_array($permission, $user['permissions'] ?? []);
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    // Use email as primary identifier for authentication
    if (!isset($_SESSION['user_email']) || empty($_SESSION['user_email'])) {
        return false;
    }
    
    // Verify user actually exists - don't just check session
    // This prevents redirect loops when session exists but user doesn't
    try {
        $user = getCurrentUser();
        return $user !== null;
    } catch (Exception $e) {
        error_log("isAuthenticated check failed: " . $e->getMessage());
        return false;
    }
}

/**
 * Logout user
 */
function logoutUser() {
    // Clear all session variables
    $_SESSION = array();
    
    // Destroy the session cookie
    if (ini_get("session.use_cookies")) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000,
            $params["path"], $params["domain"],
            $params["secure"], $params["httponly"]
        );
    }
    
    // Destroy the session
    session_destroy();
    
    // Start a new session
    session_start();
}

/**
 * Logout user with Auth0
 */
function logoutUserWithAuth0() {
    // Clear session first
    logoutUser();
    
    // Redirect to Auth0 logout
    require_once(__DIR__ . '/../config_auth0.php');
    global $auth0;
    
    // Determine login path based on environment (same logic as login.php)
    // For remote server, always use /portal/login.php
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
    
    // Build return URL - ensure SC_SERVER_URL doesn't already include /portal
    $baseUrl = rtrim(SC_SERVER_URL, '/');
    // Remove /portal if it's already in the base URL to avoid double /portal/portal
    if (strpos($baseUrl, '/portal') !== false) {
        $baseUrl = str_replace('/portal', '', $baseUrl);
    }
    $returnUrl = $baseUrl . $loginPath;
    
    $logoutUrl = $auth0->logout($returnUrl);
    header('Location: ' . $logoutUrl);
    exit;
}

/**
 * Require authentication
 */
function requireAuth() {
    if (!isAuthenticated()) {
        header('Location: /login.php');
        exit;
    }
}

/**
 * Require specific permission
 */
function requirePermission($permission) {
    requireAuth();
    
    if (!hasPermission($permission)) {
        http_response_code(403);
        die('Access denied. Insufficient permissions.');
    }
}

/**
 * Check if user is a public repository user (read-only access)
 */
function isPublicRepoUser() {
    return isset($_SESSION['user_type']) && $_SESSION['user_type'] === 'public_repo';
}

/**
 * Get user permissions
 */
function getUserPermissions() {
    $user = getCurrentUser();
    if (!$user) {
        return [];
    }
    
    // If public repo user, return limited permissions
    if (isPublicRepoUser()) {
        return ['read', 'download'];
    }
    
    // Regular users get permissions from user profile
    return $user['permissions'] ?? ['read', 'upload', 'edit', 'delete'];
}

/**
 * Check if user has a specific permission
 */
function hasPermission($permission) {
    $permissions = getUserPermissions();
    return in_array($permission, $permissions);
}

/**
 * Get user's team information
 */
function getUserTeam($userId = null) {
    if (!$userId) {
        $user = getCurrentUser();
        if (!$user) {
            return null;
        }
        $userId = $user['id'];
    }
    
    try {
        $sclib = getSCLibClient();
        $user = $sclib->getUserProfile($userId);
        
        if ($user && $user['team_id']) {
            // TODO: Implement get team by ID in SCLib API
            // This would be a new endpoint: /api/teams/{team_id}
            
            // For now, return mock team info
            return [
                'id' => $user['team_id'],
                'name' => 'Team ' . $user['team_id'],
                'description' => 'Team description'
            ];
        }
        
        return null;
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get user team', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Update user preferences
 */
function updateUserPreferences($preferences) {
    $user = getCurrentUser();
    if (!$user) {
        return false;
    }
    
    try {
        // TODO: Implement update user preferences in SCLib API
        // This would be a new endpoint: /api/auth/update-preferences
        
        // For now, just log the request
        logMessage('INFO', 'User preferences update requested', [
            'user_id' => $user['id'],
            'preferences' => $preferences
        ]);
        
        return true;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to update user preferences', ['error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Get user's dashboard preferences
 */
function getUserDashboardPreferences() {
    $user = getCurrentUser();
    if (!$user) {
        return ['preferred_dashboard' => DEFAULT_DASHBOARD];
    }
    
    return [
        'preferred_dashboard' => $user['preferred_dashboard'] ?? DEFAULT_DASHBOARD,
        'dashboard_settings' => $user['preferences']['dashboard_settings'] ?? []
    ];
}

/**
 * Check if user can access dataset
 */
function canAccessDataset($datasetId, $userId = null) {
    if (!$userId) {
        $user = getCurrentUser();
        if (!$user) {
            return false;
        }
        $userId = $user['id'];
    }
    
    try {
        $sclib = getSCLibClient();
        $dataset = $sclib->getDatasetDetails($datasetId, $userId);
        
        return $dataset !== null;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to check dataset access', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return false;
    }
}
?>