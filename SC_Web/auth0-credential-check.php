<?php
/**
 * Temporary Auth0 credential diagnostic — delete after login is fixed.
 * Shows lengths and md5 hashes only (never the secret itself).
 * Access: https://scientistcloud.com/portal/auth0-credential-check.php
 */
declare(strict_types=1);

header('Content-Type: application/json');

require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/config_auth0.php');

function secretFingerprint(?string $value): array {
    $value = $value ?? '';
    return [
        'len' => strlen($value),
        'md5' => $value === '' ? '' : md5($value),
    ];
}

$fromGetenv = getenv('AUTH0_CLIENT_SECRET');
$fromServer = $_SERVER['AUTH0_CLIENT_SECRET'] ?? null;
$fromConst = defined('AUTH0_CLIENT_SECRET') ? AUTH0_CLIENT_SECRET : '';

$pythonSecret = '';
try {
    require_once('/var/www/scientistCloudLib/SCLib_JobProcessing/SCLib_Config.php');
    $cfg = get_config();
    $pythonSecret = (string) ($cfg['auth']['auth0_client_secret'] ?? '');
} catch (Throwable $e) {
    $pythonSecret = '';
}

$usedSecret = getEnvVar('AUTH0_CLIENT_SECRET', AUTH0_CLIENT_SECRET);
$usedClientId = getEnvVar('AUTH0_CLIENT_ID', AUTH0_CLIENT_ID);

echo json_encode([
    'sapi' => php_sapi_name(),
    'client_id' => $usedClientId,
    'redirect_uri' => rtrim(SC_SERVER_URL, '/') . SC_PORTAL_PREFIX . '/auth/callback.php',
    'auth0_domain' => getEnvVar('AUTH0_DOMAIN', AUTH0_DOMAIN),
    'fingerprints' => [
        'getenv_AUTH0_CLIENT_SECRET' => secretFingerprint($fromGetenv !== false ? $fromGetenv : ''),
        'server_AUTH0_CLIENT_SECRET' => secretFingerprint(is_string($fromServer) ? $fromServer : ''),
        'constant_AUTH0_CLIENT_SECRET' => secretFingerprint($fromConst),
        'python_config_auth0_client_secret' => secretFingerprint($pythonSecret),
        'config_auth0_uses' => secretFingerprint($usedSecret),
    ],
    'match' => [
        'getenv_equals_config_auth0' => ($fromGetenv !== false && $fromGetenv === $usedSecret),
        'const_equals_config_auth0' => ($fromConst === $usedSecret),
        'python_equals_config_auth0' => ($pythonSecret === $usedSecret),
    ],
    'hint' => 'All md5 values for the secret should match each other and match: '
        . 'grep AUTH0_CLIENT_SECRET ~/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud | sed "s/^AUTH0_CLIENT_SECRET=//" | md5sum',
], JSON_PRETTY_PRINT);
