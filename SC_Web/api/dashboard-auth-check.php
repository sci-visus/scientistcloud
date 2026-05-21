<?php
/**
 * Internal auth check for nginx auth_request on /dashboard/* routes.
 * Returns 200 when the user has a portal session or valid auth_token cookie.
 */

require_once(__DIR__ . '/../includes/session_cookie_params.php');

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

header('Content-Type: text/plain');
header('Cache-Control: no-store');

try {
    require_once(__DIR__ . '/../config.php');
    require_once(__DIR__ . '/../includes/auth.php');

    if (hasDashboardAccess()) {
        if (!empty($_SESSION['user_email'])) {
            setDashboardAuthCookieFromSession();
            header('X-SC-User-Email: ' . $_SESSION['user_email']);
        }
        http_response_code(200);
        echo 'ok';
        exit;
    }

    http_response_code(401);
    echo 'unauthorized';
} catch (Throwable $e) {
    error_log('dashboard-auth-check: ' . $e->getMessage());
    // Never return 500 to auth_request — treat errors as unauthenticated
    http_response_code(401);
    echo 'unauthorized';
}
