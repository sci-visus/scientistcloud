<?php
require_once(__DIR__ . '/config.php');

// auth0
require 'vendor/autoload.php';
global $auth0;

use Auth0\SDK\Auth0;

// Robust function to get environment variables with multiple fallbacks
function getEnvVar($name, $default = null) {
    // Try getenv() first
    $value = getenv($name);
    if ($value !== false && $value !== '') {
        return $value;
    }
    
    // Try $_ENV as fallback
    if (isset($_ENV[$name]) && $_ENV[$name] !== '') {
        return $_ENV[$name];
    }
    
    // Try $_SERVER as fallback
    if (isset($_SERVER[$name]) && $_SERVER[$name] !== '') {
        return $_SERVER[$name];
    }
    
    // Return default if nothing found
    return $default;
}

// Get Auth0 credentials from environment variables with fallbacks
$auth0_client_id = getEnvVar('AUTH0_CLIENT_ID', AUTH0_CLIENT_ID);
$auth0_client_secret = getEnvVar('AUTH0_CLIENT_SECRET', AUTH0_CLIENT_SECRET);
$auth0_domain = getEnvVar('AUTH0_DOMAIN', AUTH0_DOMAIN);

use Auth0\SDK\Configuration\SdkConfiguration;

if (!isset($auth0)) {
     $config = new SdkConfiguration(
         strategy: SdkConfiguration::STRATEGY_REGULAR,  // <- Use REGULAR for stateful login flows
         domain: $auth0_domain,
         clientId: $auth0_client_id,
         clientSecret: $auth0_client_secret,
         redirectUri: SC_SERVER_URL . '/auth/callback.php',
         audience: [SC_SERVER_URL],   // Your API audience
         scope: ['openid', 'profile', 'email', 'offline_access', 'https://www.googleapis.com/auth/drive'],  // scopes as array
         cookieSecret: SECRET_KEY,  // must be a secure random string
         persistIdToken: true,
         persistAccessToken: true,
         persistRefreshToken: true
     );
    
    // Explicitly set HTTP factory and client if available
    if (class_exists('GuzzleHttp\Psr7\HttpFactory')) {
        $config->setHttpRequestFactory(new \GuzzleHttp\Psr7\HttpFactory());
    }
    
    if (class_exists('GuzzleHttp\Client')) {
        $config->setHttpClient(new \GuzzleHttp\Client());
    }
    
    // Alternative: Use PSR-18 discovery if Guzzle not available
    if (!class_exists('GuzzleHttp\Client') && class_exists('Http\Discovery\HttpClientDiscovery')) {
        $config->setHttpClient(\Http\Discovery\HttpClientDiscovery::find());
    }
    
    $auth0 = new Auth0($config);
}
?>
