<?php
/**
 * Authentication Module for ScientistCloud Data Portal
 * Handles user authentication and session management
 */

require_once(__DIR__ . '/../config.php');

/**
 * Get current authenticated user
 */
function getCurrentUser() {
    if (!isset($_SESSION['user_id'])) {
        return null;
    }
    
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('users'));
        
        $user = $collection->findOne(['_id' => new MongoDB\BSON\ObjectId($_SESSION['user_id'])]);
        
        if ($user) {
            return [
                'id' => (string)$user['_id'],
                'email' => $user['email'] ?? '',
                'name' => $user['name'] ?? '',
                'preferred_dashboard' => $user['preferred_dashboard'] ?? DEFAULT_DASHBOARD,
                'team_id' => $user['team_id'] ?? null,
                'permissions' => $user['permissions'] ?? []
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
        // Validate Auth0 token
        $auth0 = new Auth0\SDK\Auth0([
            'domain' => AUTH0_DOMAIN,
            'clientId' => AUTH0_CLIENT_ID,
            'clientSecret' => AUTH0_CLIENT_SECRET,
            'redirectUri' => SC_SERVER_URL . '/callback.php'
        ]);
        
        $userInfo = $auth0->getUser();
        
        if (!$userInfo) {
            return false;
        }
        
        // Get or create user in database
        $user = getUserByEmail($userInfo['email']);
        if (!$user) {
            $user = createUser($userInfo);
        }
        
        // Set session
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user_email'] = $user['email'];
        $_SESSION['user_name'] = $user['name'];
        
        return $user;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Authentication failed', ['error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Get user by email
 */
function getUserByEmail($email) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('users'));
        
        $user = $collection->findOne(['email' => $email]);
        
        if ($user) {
            return [
                'id' => (string)$user['_id'],
                'email' => $user['email'],
                'name' => $user['name'] ?? '',
                'preferred_dashboard' => $user['preferred_dashboard'] ?? DEFAULT_DASHBOARD,
                'team_id' => $user['team_id'] ?? null,
                'permissions' => $user['permissions'] ?? []
            ];
        }
        
        return null;
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get user by email', ['email' => $email, 'error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Create new user
 */
function createUser($userInfo) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('users'));
        
        $user = [
            'email' => $userInfo['email'],
            'name' => $userInfo['name'] ?? $userInfo['email'],
            'preferred_dashboard' => DEFAULT_DASHBOARD,
            'team_id' => null,
            'permissions' => ['read', 'upload'],
            'created_at' => new MongoDB\BSON\UTCDateTime(),
            'updated_at' => new MongoDB\BSON\UTCDateTime()
        ];
        
        $result = $collection->insertOne($user);
        
        return [
            'id' => (string)$result->getInsertedId(),
            'email' => $user['email'],
            'name' => $user['name'],
            'preferred_dashboard' => $user['preferred_dashboard'],
            'team_id' => $user['team_id'],
            'permissions' => $user['permissions']
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
    
    return in_array($permission, $user['permissions']);
}

/**
 * Logout user
 */
function logoutUser() {
    session_destroy();
    session_start();
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return getCurrentUser() !== null;
}

/**
 * Require authentication
 */
function requireAuth() {
    if (!isAuthenticated()) {
        header('Location: login.php');
        exit;
    }
}

/**
 * Get user's team
 */
function getUserTeam($userId) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('teams'));
        
        $team = $collection->findOne(['members' => $userId]);
        
        if ($team) {
            return [
                'id' => (string)$team['_id'],
                'name' => $team['name'],
                'description' => $team['description'] ?? '',
                'members' => $team['members'] ?? []
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
function updateUserPreferences($userId, $preferences) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('users'));
        
        $updateData = array_merge($preferences, [
            'updated_at' => new MongoDB\BSON\UTCDateTime()
        ]);
        
        $result = $collection->updateOne(
            ['_id' => new MongoDB\BSON\ObjectId($userId)],
            ['$set' => $updateData]
        );
        
        return $result->getModifiedCount() > 0;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to update user preferences', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return false;
    }
}
?>
