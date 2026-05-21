<?php
/**
 * Store the dashboard URL the user wanted, then send them to login.
 * Used by nginx when auth_request fails on /dashboard/* (avoids encoding long query strings in redirects).
 */

require_once(__DIR__ . '/../includes/session_cookie_params.php');

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');

$target = isset($_GET['target']) ? (string) $_GET['target'] : '';
if ($target === '' || $target[0] !== '/') {
    $target = '/';
}

$returnTo = rtrim(SC_SERVER_URL, '/') . $target;
storeLoginReturnTo($returnTo);

if (isAuthenticated()) {
    setDashboardAuthCookieFromSession();
    header('Location: ' . getPostLoginRedirectUrl());
    exit;
}

header('Location: ' . SC_PORTAL_LOGIN_URL);
exit;
