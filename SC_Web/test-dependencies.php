<?php
/**
 * Test script to check if Auth0 dependencies are properly installed
 */

echo "<h1>Auth0 Dependencies Test</h1>";

// Check if composer autoloader exists
if (file_exists(__DIR__ . '/vendor/autoload.php')) {
    echo "<p style='color: green;'>✓ Composer autoloader found</p>";
    require_once __DIR__ . '/vendor/autoload.php';
} else {
    echo "<p style='color: red;'>✗ Composer autoloader not found</p>";
    echo "<p>Current directory: " . __DIR__ . "</p>";
    echo "<p>Files in directory:</p><ul>";
    foreach (scandir(__DIR__) as $file) {
        echo "<li>$file</li>";
    }
    echo "</ul>";
    exit;
}

// Check PSR-17 HTTP Factory
if (class_exists('GuzzleHttp\Psr7\HttpFactory')) {
    echo "<p style='color: green;'>✓ PSR-17 HTTP Factory (GuzzleHttp\\Psr7\\HttpFactory) available</p>";
} else {
    echo "<p style='color: red;'>✗ PSR-17 HTTP Factory not found</p>";
}

// Check PSR-18 HTTP Client
if (class_exists('GuzzleHttp\Client')) {
    echo "<p style='color: green;'>✓ PSR-18 HTTP Client (GuzzleHttp\\Client) available</p>";
} else {
    echo "<p style='color: red;'>✗ PSR-18 HTTP Client not found</p>";
}

// Check Auth0 SDK
if (class_exists('Auth0\SDK\Auth0')) {
    echo "<p style='color: green;'>✓ Auth0 SDK available</p>";
} else {
    echo "<p style='color: red;'>✗ Auth0 SDK not found</p>";
}

// List installed packages
echo "<h2>Installed Composer Packages:</h2>";
if (file_exists(__DIR__ . '/vendor/composer/installed.json')) {
    $installed = json_decode(file_get_contents(__DIR__ . '/vendor/composer/installed.json'), true);
    echo "<ul>";
    foreach ($installed['packages'] as $package) {
        echo "<li>{$package['name']} - {$package['version']}</li>";
    }
    echo "</ul>";
} else {
    echo "<p style='color: red;'>No composer packages found</p>";
}

echo "<h2>Vendor Directory Contents:</h2>";
if (is_dir(__DIR__ . '/vendor')) {
    echo "<ul>";
    foreach (scandir(__DIR__ . '/vendor') as $item) {
        if ($item != '.' && $item != '..') {
            echo "<li>$item</li>";
        }
    }
    echo "</ul>";
} else {
    echo "<p style='color: red;'>Vendor directory not found</p>";
}
?>
