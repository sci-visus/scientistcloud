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
 * Clear Auth0 SDK / portal cookies (legacy Visus logout pattern).
 */
function clearAuth0Cookies() {
    $secure = isHttpsRequest();
    $names = [
        'auth0.is.authenticated',
        'auth0_session',
        'auth0_session_0',
        'auth0_session_1',
        'auth0_session_2',
        'auth_token',
        'session_token',
    ];
    foreach ($names as $name) {
        setcookie($name, '', [
            'expires' => time() - 3600,
            'path' => '/',
            'secure' => $secure,
            'httponly' => true,
            'samesite' => 'Lax',
        ]);
    }
}

/**
 * Portal path prefix: '' on localhost, '/portal' on production host.
 */
function scPortalPathPrefix() {
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false
        || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    return $isLocal ? '' : '/portal';
}

/**
 * URL shown after Auth0 logout — must NOT auto-start login (unlike login.php).
 */
function getPostLogoutUrl() {
    $base = rtrim(SC_SERVER_URL, '/');
    if (strpos($base, '/portal') !== false) {
        $base = str_replace('/portal', '', $base);
    }
    return $base . scPortalPathPrefix() . '/logged_out.php';
}

/**
 * Logout user
 */
function logoutUser() {
    clearDashboardAuthCookie();
    clearAuth0Cookies();

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
    require_once(__DIR__ . '/../config_auth0.php');
    global $auth0;

    clearDashboardAuthCookie();
    clearAuth0Cookies();

    // Auth0 SDK clears its session store; return URL must not be login.php (that auto-starts OAuth).
    $returnUrl = getPostLogoutUrl();
    try {
        $logoutUrl = $auth0->logout($returnUrl, ['federated' => '']);
    } catch (Throwable $e) {
        error_log('Auth0 logout failed: ' . $e->getMessage());
        logoutUser();
        header('Location: ' . $returnUrl);
        exit;
    }

    logoutUser();
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

/**
 * Whether the current request is served over HTTPS (direct or via proxy).
 */
function isHttpsRequest() {
    if (!empty($_SERVER['HTTPS']) && strtolower((string) $_SERVER['HTTPS']) !== 'off') {
        return true;
    }
    return strtolower((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https';
}

/**
 * Allowed post-login redirect targets (dashboard share links and portal pages).
 */
function isSafeLoginReturnToUrl($url) {
    $url = trim((string) $url);
    if ($url === '') {
        return false;
    }
    $parts = parse_url($url);
    if ($parts === false || empty($parts['host'])) {
        return false;
    }
    $host = strtolower($parts['host']);
    $allowedHosts = ['localhost', '127.0.0.1', 'scientistcloud.com', 'www.scientistcloud.com'];
    $deployHost = parse_url(SC_SERVER_URL, PHP_URL_HOST);
    if ($deployHost && !in_array(strtolower($deployHost), $allowedHosts, true)) {
        $allowedHosts[] = strtolower($deployHost);
    }
    if (!in_array($host, $allowedHosts, true)) {
        return false;
    }
    $path = $parts['path'] ?? '/';
    if (strpos($path, '/dashboard/') === 0) {
        return true;
    }
    if (SC_PORTAL_PREFIX !== '' && strpos($path, SC_PORTAL_PREFIX . '/') === 0) {
        return true;
    }
    if (SC_PORTAL_PREFIX === '' && ($path === '/index.php' || $path === '/' || strpos($path, '/index.php') === 0)) {
        return true;
    }
    return false;
}

/**
 * Remember where to send the user after login (dashboard share link, etc.).
 */
function storeLoginReturnTo($url) {
    $url = trim((string) $url);
    if ($url !== '' && isSafeLoginReturnToUrl($url)) {
        $_SESSION['login_return_to'] = $url;
    }
}

/**
 * Return stored post-login URL and clear it from the session.
 */
function consumeLoginReturnTo() {
    $url = $_SESSION['login_return_to'] ?? null;
    unset($_SESSION['login_return_to']);
    if ($url && isSafeLoginReturnToUrl($url)) {
        return $url;
    }
    return null;
}

/**
 * Default portal landing page after login when no return URL is stored.
 */
function getDefaultPostLoginUrl() {
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $indexPath = $isLocal ? '/index.php' : '/portal/index.php';
    return rtrim(SC_SERVER_URL, '/') . $indexPath;
}

/**
 * Resolve redirect target after successful authentication.
 */
function getPostLoginRedirectUrl() {
    return consumeLoginReturnTo() ?? getDefaultPostLoginUrl();
}

function dashboardJwtBase64UrlEncode($data) {
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

/**
 * Create HS256 JWT for Bokeh dashboards (matches SCLib_JWTManager payload shape).
 */
function createDashboardAuthToken($email, $userId = null, $expiresHours = null) {
    $email = trim((string) $email);
    if ($email === '') {
        return null;
    }
    $hours = $expiresHours ?? (int) (getenv('JWT_EXPIRY_HOURS') ?: 24);
    $now = time();
    // Bokeh dashboards always expect aud=sclib-api (not Auth0 API audience from AUTH0_AUDIENCE).
    $audience = 'sclib-api';
    $payload = [
        'email' => $email,
        'user' => $email,
        'iat' => $now,
        'exp' => $now + ($hours * 3600),
        'jti' => bin2hex(random_bytes(16)),
        'iss' => 'sclib-auth',
        'aud' => $audience,
        'type' => 'access',
    ];
    if ($userId) {
        $payload['user_id'] = $userId;
    }
    $header = dashboardJwtBase64UrlEncode(json_encode(['typ' => 'JWT', 'alg' => 'HS256']));
    $body = dashboardJwtBase64UrlEncode(json_encode($payload));
    $signature = dashboardJwtBase64UrlEncode(hash_hmac('sha256', $header . '.' . $body, SECRET_KEY, true));
    return $header . '.' . $body . '.' . $signature;
}

/**
 * Set auth_token cookie so /dashboard/* Bokeh apps can authenticate the user.
 */
function setDashboardAuthCookie($email, $userId = null) {
    $token = createDashboardAuthToken($email, $userId);
    if (!$token) {
        return false;
    }
    $hours = (int) (getenv('JWT_EXPIRY_HOURS') ?: 24);
    $secure = isHttpsRequest();
    setcookie('auth_token', $token, [
        'expires' => time() + ($hours * 3600),
        'path' => '/',
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    return true;
}

/**
 * Set dashboard auth cookie from the current PHP session, if logged in.
 */
function setDashboardAuthCookieFromSession() {
    if (empty($_SESSION['user_email'])) {
        return false;
    }
    return setDashboardAuthCookie($_SESSION['user_email'], $_SESSION['user_id'] ?? null);
}

/**
 * Clear dashboard auth cookie on logout.
 */
function clearDashboardAuthCookie() {
    $secure = isHttpsRequest();
    setcookie('auth_token', '', [
        'expires' => time() - 3600,
        'path' => '/',
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}

/**
 * True if the request has a valid portal session or auth_token cookie.
 */
function hasDashboardAccess() {
    // Fast path: portal session from Auth0 callback (no SCLib round-trip)
    if (!empty($_SESSION['user_email'])) {
        return true;
    }
    if (empty($_COOKIE['auth_token'])) {
        return false;
    }
    try {
        $sclib = getSCLibAuthClient();
        $result = $sclib->validateAuthToken($_COOKIE['auth_token']);
        return !empty($result['success']) && !empty($result['valid']);
    } catch (Exception $e) {
        error_log('hasDashboardAccess: ' . $e->getMessage());
        return false;
    }
}
?>