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
$auth0_audience = getEnvVar('AUTH0_AUDIENCE', null);

use Auth0\SDK\Configuration\SdkConfiguration;

if (!isset($auth0)) {
    // Explicitly create HTTP factories before SdkConfiguration construction
    // This prevents the "Could not find a PSR-17 compatible request factory" error
    $httpRequestFactory = null;
    $httpResponseFactory = null;
    $httpStreamFactory = null;
    $httpClient = null;
    
    // Try multiple methods to find HTTP factories
    
    // Method 1: Try Guzzle HTTP factories (PSR-17 compatible) - guzzlehttp/psr7 v2.x
    if (class_exists('GuzzleHttp\Psr7\HttpFactory')) {
        try {
            $httpFactory = new \GuzzleHttp\Psr7\HttpFactory();
            $httpRequestFactory = $httpFactory;
            $httpResponseFactory = $httpFactory;
            $httpStreamFactory = $httpFactory;
            error_log("✅ Using GuzzleHttp\Psr7\HttpFactory");
        } catch (\Exception $e) {
            error_log("Failed to create GuzzleHttp\Psr7\HttpFactory: " . $e->getMessage());
        }
    }
    
    // Method 2: Try using php-http/discovery (should work if packages are installed)
    if (!$httpRequestFactory && class_exists('Http\Discovery\Psr17Factory')) {
        try {
            $httpFactory = new \Http\Discovery\Psr17Factory();
            $httpRequestFactory = $httpFactory;
            $httpResponseFactory = $httpFactory;
            $httpStreamFactory = $httpFactory;
            error_log("✅ Using Http\Discovery\Psr17Factory");
        } catch (\Exception $e) {
            error_log("Failed to create Http\Discovery\Psr17Factory: " . $e->getMessage());
        }
    }
    
    // Method 3: Try PSR discovery (psr-discovery/http-factory-implementations)
    if (!$httpRequestFactory && class_exists('Psr\Discovery\HttpFactoryDiscovery')) {
        try {
            $httpRequestFactory = \Psr\Discovery\HttpFactoryDiscovery::findRequestFactory();
            $httpResponseFactory = \Psr\Discovery\HttpFactoryDiscovery::findResponseFactory();
            $httpStreamFactory = \Psr\Discovery\HttpFactoryDiscovery::findStreamFactory();
            error_log("✅ Using PSR Discovery factories");
        } catch (\Exception $e) {
            error_log("PSR-17 factory discovery failed: " . $e->getMessage());
        }
    }
    
    // Try to use Guzzle HTTP client (PSR-18 compatible)
    // Try creating it directly - autoloader will load the class if it's installed
    try {
        // Check if Guzzle is available (class_exists will trigger autoload)
        if (class_exists('\GuzzleHttp\Client', true)) {
            $httpClient = new \GuzzleHttp\Client();
            error_log("✅ Using GuzzleHttp\Client");
        }
    } catch (\Error $e) {
        // Class not found or fatal error
        error_log("GuzzleHttp\Client not available: " . $e->getMessage());
    } catch (\Exception $e) {
        // Other exception
        error_log("Failed to create GuzzleHttp\Client: " . $e->getMessage());
    }
    
    // Try php-http/discovery HTTP client
    if (!$httpClient && class_exists('Http\Discovery\HttpClientDiscovery')) {
        try {
            $httpClient = \Http\Discovery\HttpClientDiscovery::find();
            error_log("✅ Using Http\Discovery\HttpClientDiscovery");
        } catch (\Exception $e) {
            error_log("Http\Discovery HTTP client discovery failed: " . $e->getMessage());
        }
    }
    
    // Try PSR Discovery HTTP client
    if (!$httpClient && class_exists('Psr\Discovery\HttpClientDiscovery')) {
        try {
            $httpClient = \Psr\Discovery\HttpClientDiscovery::find();
            error_log("✅ Using PSR Discovery HTTP client");
        } catch (\Exception $e) {
            error_log("PSR-18 client discovery failed: " . $e->getMessage());
        }
    }
    
    // Final check - if factories are still null, log warning
    if (!$httpRequestFactory) {
        error_log("❌ WARNING: Could not find any PSR-17 HTTP factory implementation!");
        error_log("   Checked: GuzzleHttp\Psr7\HttpFactory, Http\Discovery\Psr17Factory, PSR Discovery");
        error_log("   Make sure guzzlehttp/guzzle and guzzlehttp/psr7 are installed: composer install");
    }
    
    // Final check - if HTTP client is still null, we MUST have one for Auth0 SDK
    if (!$httpClient) {
        $errorMsg = "FATAL ERROR: Could not find any PSR-18 HTTP client implementation!\n";
        $errorMsg .= "Auth0 SDK requires a PSR-18 compatible HTTP client.\n";
        $errorMsg .= "Checked: GuzzleHttp\\Client, Http\\Discovery\\HttpClientDiscovery, PSR Discovery\n";
        $errorMsg .= "\n";
        $errorMsg .= "Solution: Install guzzlehttp/guzzle\n";
        $errorMsg .= "  Run in /var/www/html: composer require guzzlehttp/guzzle\n";
        $errorMsg .= "  Or ensure it's installed: composer install\n";
        $errorMsg .= "\n";
        $errorMsg .= "If composer is not available, check:\n";
        $errorMsg .= "  - Is vendor/autoload.php loading properly?\n";
        $errorMsg .= "  - Is guzzlehttp/guzzle actually installed in vendor/?\n";
        $errorMsg .= "  - Check composer.json and run: composer update";
        
        error_log($errorMsg);
        
        // Throw a user-friendly error instead of letting Auth0 SDK throw cryptic error
        throw new \RuntimeException(
            "Auth0 initialization failed: PSR-18 HTTP client not found. " .
            "Please install guzzlehttp/guzzle: composer require guzzlehttp/guzzle " .
            "or run composer install in " . __DIR__
        );
    }
    
    // Determine audience - use AUTH0_AUDIENCE if set, otherwise null (for simple auth without API access)
    // Only set audience if AUTH0_AUDIENCE is explicitly configured, as Auth0 requires the API to exist
    $audience = null;
    if ($auth0_audience && !empty($auth0_audience)) {
        $audience = [$auth0_audience];
    }
    
    // Create SdkConfiguration with explicit HTTP factories and client passed to constructor
    // This prevents the setupStateFactories() from trying to discover them (which fails)
    $config = new SdkConfiguration(
        strategy: SdkConfiguration::STRATEGY_REGULAR,
        domain: $auth0_domain,
        clientId: $auth0_client_id,
        clientSecret: $auth0_client_secret,
        redirectUri: SC_SERVER_URL . '/portal/auth/callback.php',
        audience: $audience,  // null if not using API access, or [AUTH0_AUDIENCE] if API exists
        scope: ['openid', 'profile', 'email', 'offline_access', 'https://www.googleapis.com/auth/drive'],
        cookieSecret: SECRET_KEY,
        persistIdToken: true,
        persistAccessToken: true,
        persistRefreshToken: true,
        httpRequestFactory: $httpRequestFactory,
        httpResponseFactory: $httpResponseFactory,
        httpStreamFactory: $httpStreamFactory,
        httpClient: $httpClient  // Must not be null - checked above
    );
    
    $auth0 = new Auth0($config);
}
?>
