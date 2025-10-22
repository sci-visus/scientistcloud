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
    if (!isset($_SESSION['user_id'])) {
        return null;
    }
    
    try {
        $sclib = getSCLibClient();
        $user = $sclib->getUserProfile($_SESSION['user_id']);
        
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
        // Validate Auth0 token using SCLib
        $sclib = getSCLibClient();
        $authResult = $sclib->validateAuthToken($auth0_token);
        
        if (!$authResult['success'] || !$authResult['valid']) {
            return false;
        }
        
        $userId = $authResult['user_id'];
        
        // Get user profile from SCLib
        $user = $sclib->getUserProfile($userId);
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
 * Get user by email - delegate to SCLib
 */
function getUserByEmail($email) {
    try {
        // SCLib should provide an endpoint to get user by email
        // For now, we'll use a mock implementation
        $sclib = getSCLibClient();
        
        // TODO: Implement get user by email in SCLib API
        // This would be a new endpoint: /api/auth/user-by-email?email=...
        
        // For now, return null to indicate user not found
        return null;
        
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
    return isset($_SESSION['user_id']) && !empty($_SESSION['user_id']);
}

/**
 * Logout user
 */
function logoutUser() {
    session_destroy();
    session_start();
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