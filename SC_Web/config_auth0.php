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
    // Check if vendor directory and Guzzle actually exist before trying to use it
    $guzzlePath = __DIR__ . '/vendor/guzzlehttp/guzzle/src/Client.php';
    $vendorAutoload = __DIR__ . '/vendor/autoload.php';
    
    if (file_exists($vendorAutoload) && file_exists($guzzlePath)) {
        // Files exist, try to load via autoloader
        try {
            // Ensure autoloader is loaded
            if (!class_exists('\Composer\Autoload\ClassLoader', false)) {
                require_once $vendorAutoload;
            }
            
            // Check if Guzzle is available (class_exists will trigger autoload)
            if (class_exists('\GuzzleHttp\Client', true)) {
                $httpClient = new \GuzzleHttp\Client();
                error_log("✅ Using GuzzleHttp\Client");
            } else {
                error_log("⚠️ Guzzle files exist but class not found - autoloader may need refresh");
                // Try to manually require the class file
                if (file_exists($guzzlePath)) {
                    require_once $guzzlePath;
                    $httpClient = new \GuzzleHttp\Client();
                    error_log("✅ Using GuzzleHttp\Client (manually loaded)");
                }
            }
        } catch (\Error $e) {
            // Class not found or fatal error
            error_log("GuzzleHttp\Client not available: " . $e->getMessage());
            error_log("   Guzzle path exists: " . (file_exists($guzzlePath) ? 'Yes' : 'No'));
            error_log("   Vendor autoload exists: " . (file_exists($vendorAutoload) ? 'Yes' : 'No'));
        } catch (\Exception $e) {
            // Other exception
            error_log("Failed to create GuzzleHttp\Client: " . $e->getMessage());
        }
    } else {
        error_log("⚠️ Guzzle not found - vendor path: " . (file_exists($vendorAutoload) ? 'exists' : 'missing') . 
                  ", guzzle path: " . (file_exists($guzzlePath) ? 'exists' : 'missing'));
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
    
    // Final check - if HTTP client is still null, try to auto-install dependencies in Docker
    if (!$httpClient) {
        // Check if we're in Docker and if composer dependencies might need installation
        $isDocker = file_exists('/.dockerenv') || getenv('APACHE_RUN_USER') !== false;
        $composerJsonExists = file_exists(__DIR__ . '/composer.json');
        $vendorAutoloadExists = file_exists(__DIR__ . '/vendor/autoload.php');
        $guzzleDirExists = is_dir(__DIR__ . '/vendor/guzzlehttp/guzzle');
        $composerExists = file_exists('/usr/bin/composer') || file_exists('/usr/local/bin/composer');
        
        $errorMsg = "FATAL ERROR: Could not find any PSR-18 HTTP client implementation!\n";
        $errorMsg .= "Auth0 SDK requires a PSR-18 compatible HTTP client.\n";
        $errorMsg .= "Checked: GuzzleHttp\\Client, Http\\Discovery\\HttpClientDiscovery, PSR Discovery\n";
        $errorMsg .= "\n";
        $errorMsg .= "Diagnostics:\n";
        $errorMsg .= "  - Running in Docker: " . ($isDocker ? "Yes" : "No") . "\n";
        $errorMsg .= "  - composer.json exists: " . ($composerJsonExists ? "Yes" : "No") . "\n";
        $errorMsg .= "  - vendor/autoload.php exists: " . ($vendorAutoloadExists ? "Yes" : "No") . "\n";
        $errorMsg .= "  - vendor/guzzlehttp/guzzle exists: " . ($guzzleDirExists ? "Yes" : "No") . "\n";
        $errorMsg .= "  - composer binary exists: " . ($composerExists ? "Yes" : "No") . "\n";
        
        error_log($errorMsg);
        
        // Try auto-installation in Docker environment if composer is available
        if ($isDocker && $composerJsonExists && !$guzzleDirExists && $composerExists) {
            error_log("🔧 Attempting automatic dependency installation...");
            try {
                $composerCmd = file_exists('/usr/bin/composer') ? '/usr/bin/composer' : '/usr/local/bin/composer';
                $workDir = escapeshellarg(__DIR__);
                
                // First, update composer.json to ensure promises is included
                $composerJsonPath = __DIR__ . '/composer.json';
                if (file_exists($composerJsonPath)) {
                    $composerJson = json_decode(file_get_contents($composerJsonPath), true);
                    if (!isset($composerJson['require']['guzzlehttp/promises'])) {
                        error_log("📝 Adding guzzlehttp/promises to composer.json...");
                        $composerJson['require']['guzzlehttp/promises'] = '^2.0';
                        file_put_contents($composerJsonPath, json_encode($composerJson, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
                    }
                }
                
                // Update composer to ensure all dependencies are resolved
                $updateCmd = "cd $workDir && " . 
                            escapeshellarg($composerCmd) . 
                            " update --no-dev --optimize-autoloader --no-interaction --prefer-dist 2>&1";
                
                error_log("Running: $updateCmd");
                $output = [];
                $returnCode = 0;
                exec($updateCmd, $output, $returnCode);
                
                $updateOutput = implode("\n", $output);
                error_log("Composer update output:\n" . $updateOutput);
                
                // If update failed or didn't install, try install
                if ($returnCode !== 0 || !file_exists(__DIR__ . '/vendor/guzzlehttp/promises')) {
                    $installCmd = "cd $workDir && " . 
                                 escapeshellarg($composerCmd) . 
                                 " install --no-dev --optimize-autoloader --no-interaction --prefer-dist 2>&1";
                    
                    error_log("Running install as fallback: $installCmd");
                    exec($installCmd, $output, $returnCode);
                    $installOutput = implode("\n", $output);
                    error_log("Composer install output:\n" . $installOutput);
                }
                
                if ($returnCode === 0 || file_exists(__DIR__ . '/vendor/guzzlehttp/promises')) {
                    // Regenerate autoloader to ensure all classes are properly mapped
                    $dumpCmd = "cd $workDir && " . 
                              escapeshellarg($composerCmd) . 
                              " dump-autoload --optimize --no-interaction 2>&1";
                    exec($dumpCmd, $dumpOutput, $dumpReturnCode);
                    error_log("Composer dump-autoload output:\n" . implode("\n", $dumpOutput));
                    
                    // Verify promises is installed
                    $promisesPath = __DIR__ . '/vendor/guzzlehttp/promises';
                    $traitPath = __DIR__ . '/vendor/guzzlehttp/guzzle/src/ClientTrait.php';
                    error_log("Checking dependencies - promises: " . (is_dir($promisesPath) ? 'exists' : 'missing') . 
                              ", ClientTrait: " . (file_exists($traitPath) ? 'exists' : 'missing'));
                    
                    error_log("✅ Automatic dependency installation succeeded!");
                    
                    // Clear any opcode cache that might be holding old class definitions
                    if (function_exists('opcache_reset')) {
                        opcache_reset();
                    }
                    
                    // Reload the autoloader
                    if (file_exists(__DIR__ . '/vendor/autoload.php')) {
                        // Unset any existing autoloader
                        spl_autoload_unregister('spl_autoload');
                        require_once __DIR__ . '/vendor/autoload.php';
                        
                        // Wait a moment for filesystem to sync
                        usleep(200000); // 200ms
                        
                        // Try to load Guzzle again after installation
                        if (class_exists('\GuzzleHttp\Client', true)) {
                            $httpClient = new \GuzzleHttp\Client();
                            error_log("✅ GuzzleHttp\Client loaded after auto-installation");
                            // Success! Continue without throwing error
                            goto skip_error;
                        } else {
                            error_log("⚠️ GuzzleHttp\Client still not loadable after installation");
                            // Try to manually require the trait file
                            if (file_exists($traitPath)) {
                                require_once $traitPath;
                                if (class_exists('\GuzzleHttp\Client', true)) {
                                    $httpClient = new \GuzzleHttp\Client();
                                    error_log("✅ GuzzleHttp\Client loaded after manual trait load");
                                    goto skip_error;
                                }
                            }
                        }
                    }
                    error_log("⚠️ Installation succeeded but Guzzle still not loadable");
                } else {
                    error_log("❌ Automatic dependency installation failed with return code: $returnCode");
                }
            } catch (\Exception $e) {
                error_log("❌ Automatic dependency installation exception: " . $e->getMessage());
            }
        }
        
        $errorMsg .= "\n";
        $errorMsg .= "Solution:\n";
        
        if ($isDocker && $composerJsonExists && !$guzzleDirExists) {
            // In Docker and composer.json exists but dependencies not installed
            $errorMsg .= "  Run inside the container:\n";
            $errorMsg .= "    docker exec -it scientistcloud-portal composer install --no-dev --optimize-autoloader\n";
            $errorMsg .= "  Or restart the container (startup script should install dependencies automatically)\n";
        } else if ($composerJsonExists) {
            $errorMsg .= "  Run in " . __DIR__ . ":\n";
            $errorMsg .= "    composer install --no-dev --optimize-autoloader\n";
            $errorMsg .= "    OR\n";
            $errorMsg .= "    composer require guzzlehttp/guzzle:^7.0\n";
        } else {
            $errorMsg .= "  composer.json is missing - dependencies cannot be installed automatically\n";
            $errorMsg .= "  Please ensure composer.json exists in " . __DIR__ . "\n";
        }
        
        error_log($errorMsg);
        
        // Throw a user-friendly error with actionable steps
        $userMessage = "Auth0 initialization failed: PSR-18 HTTP client not found. ";
        if ($isDocker && $composerJsonExists && !$guzzleDirExists) {
            $userMessage .= "Docker container detected but dependencies not installed. " .
                           "Run: docker exec -it scientistcloud-portal composer install --no-dev --optimize-autoloader";
        } else if ($composerJsonExists) {
            $userMessage .= "Please install dependencies: composer install --no-dev --optimize-autoloader in " . __DIR__;
        } else {
            $userMessage .= "composer.json not found. Please ensure composer.json exists and run: composer install";
        }
        
        throw new \RuntimeException($userMessage);
        
        skip_error: // Label to skip error if auto-installation succeeded
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
        scope: ['openid', 'profile', 'email', 'offline_access', 'https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/gmail.send'],
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
