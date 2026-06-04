<?php
/**
 * Logout Page for ScientistCloud Data Portal
 * Handles user logout via Auth0
 */

require_once(__DIR__ . '/includes/session_cookie_params.php');
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth.php');

// ?federated=1 also signs out of Google (shows accounts.google.com); default stays on ScientistCloud.
$federatedLogout = isset($_GET['federated']) && $_GET['federated'] === '1';
logoutUserWithAuth0($federatedLogout);
?>
