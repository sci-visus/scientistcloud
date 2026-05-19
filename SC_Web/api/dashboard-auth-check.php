<?php
/**
 * Internal auth check for nginx auth_request on /dashboard/* routes.
 * Returns 200 when the user has a portal session or valid auth_token cookie.
 */

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');

header('Content-Type: text/plain');
header('Cache-Control: no-store');

if (hasDashboardAccess()) {
    if (isAuthenticated()) {
        setDashboardAuthCookieFromSession();
    }
    http_response_code(200);
    echo 'ok';
    exit;
}

http_response_code(401);
echo 'unauthorized';
