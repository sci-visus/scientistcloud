<?php
/**
 * Session cookie scope for /portal and /dashboard on the same host.
 * Must run before session_start() on every entry point.
 */
if (session_status() !== PHP_SESSION_ACTIVE) {
    $_sc_https = (!empty($_SERVER['HTTPS']) && strtolower((string) $_SERVER['HTTPS']) !== 'off')
        || (strtolower((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'secure' => $_sc_https,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}
