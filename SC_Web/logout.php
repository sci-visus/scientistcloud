<?php
/**
 * Logout Page for ScientistCloud Data Portal
 * Handles user logout via Auth0
 */

// Start session
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth.php');

// Use Auth0 logout
logoutUserWithAuth0();
?>
