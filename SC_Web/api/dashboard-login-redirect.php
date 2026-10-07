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

$dest = strtolower((string) ($_SERVER['HTTP_SEC_FETCH_DEST'] ?? ''));
$referer = (string) ($_SERVER['HTTP_REFERER'] ?? '');
$fromPublicPortal = str_contains($referer, '/public/');
$inIframe = ($dest === 'iframe' || $dest === 'embed' || $fromPublicPortal);

// Auth0 sets X-Frame-Options: deny. Never send an iframe there — the public portal
// would show "refused to connect" instead of the dashboard.
if ($inIframe && !isAuthenticated()) {
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $publicHome = $isLocal ? '/public/' : '/portal/public/';
    http_response_code(401);
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-store');
    $safeHome = htmlspecialchars($publicHome, ENT_QUOTES, 'UTF-8');
    echo '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Dashboard sign-in</title></head><body style="font-family:sans-serif;padding:2rem;text-align:center;color:#334">';
    echo '<p>This dashboard could not load in the public portal viewer.</p>';
    echo '<p><a href="' . $safeHome . '" target="_top">Return to the public portal</a></p>';
    echo '</body></html>';
    exit;
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
