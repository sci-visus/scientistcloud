<?php
/**
 * Ensure auth_token cookie is set for /dashboard/* Bokeh apps.
 * Call from the portal (credentials: include) immediately before loading a dashboard iframe.
 */

require_once(__DIR__ . '/../includes/session_cookie_params.php');

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

header('Content-Type: application/json');
header('Cache-Control: no-store');

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');

if (!isAuthenticated()) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Authentication required']);
    exit;
}

if (!setDashboardAuthCookieFromSession()) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Failed to set dashboard auth cookie']);
    exit;
}

echo json_encode(['success' => true]);
