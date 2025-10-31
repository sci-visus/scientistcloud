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
    // Explicitly create HTTP factories before SdkConfiguration construction
    // This prevents the "Could not find a PSR-17 compatible request factory" error
    $httpRequestFactory = null;
    $httpResponseFactory = null;
    $httpStreamFactory = null;
    $httpClient = null;
    
    // Try to use Guzzle HTTP factories (PSR-17 compatible)
    if (class_exists('\GuzzleHttp\Psr7\HttpFactory')) {
        $httpFactory = new \GuzzleHttp\Psr7\HttpFactory();
        $httpRequestFactory = $httpFactory;
        $httpResponseFactory = $httpFactory;
        $httpStreamFactory = $httpFactory;
    }
    
    // Try to use Guzzle HTTP client (PSR-18 compatible)
    if (class_exists('\GuzzleHttp\Client')) {
        $httpClient = new \GuzzleHttp\Client();
    }
    
    // If Guzzle is not available, try PSR discovery
    if (!$httpRequestFactory && class_exists('\Psr\Discovery\HttpFactoryDiscovery')) {
        try {
            $httpRequestFactory = \Psr\Discovery\HttpFactoryDiscovery::findRequestFactory();
            $httpResponseFactory = \Psr\Discovery\HttpFactoryDiscovery::findResponseFactory();
            $httpStreamFactory = \Psr\Discovery\HttpFactoryDiscovery::findStreamFactory();
        } catch (\Exception $e) {
            error_log("PSR-17 factory discovery failed: " . $e->getMessage());
        }
    }
    
    if (!$httpClient && class_exists('\Psr\Discovery\HttpClientDiscovery')) {
        try {
            $httpClient = \Psr\Discovery\HttpClientDiscovery::find();
        } catch (\Exception $e) {
            error_log("PSR-18 client discovery failed: " . $e->getMessage());
        }
    }
    
    // Create SdkConfiguration with explicit HTTP factories passed to constructor
    // This prevents the setupStateFactories() from trying to discover them (which fails)
    $config = new SdkConfiguration(
        strategy: SdkConfiguration::STRATEGY_REGULAR,
        domain: $auth0_domain,
        clientId: $auth0_client_id,
        clientSecret: $auth0_client_secret,
        redirectUri: SC_SERVER_URL . '/auth/callback.php',
        audience: [SC_SERVER_URL],
        scope: ['openid', 'profile', 'email', 'offline_access', 'https://www.googleapis.com/auth/drive'],
        cookieSecret: SECRET_KEY,
        persistIdToken: true,
        persistAccessToken: true,
        persistRefreshToken: true,
        httpRequestFactory: $httpRequestFactory,
        httpResponseFactory: $httpResponseFactory,
        httpStreamFactory: $httpStreamFactory,
        httpClient: $httpClient
    );
    
    $auth0 = new Auth0($config);
}
?>
