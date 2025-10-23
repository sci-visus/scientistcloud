<?php
/**
 * Manual dependency installer for Auth0
 */

echo "<h1>Installing Missing Auth0 Dependencies</h1>";

// Check if we're in the right directory
echo "<p>Current directory: " . __DIR__ . "</p>";
echo "<p>Composer.json exists: " . (file_exists(__DIR__ . '/composer.json') ? 'Yes' : 'No') . "</p>";

// Try to install the missing dependency
echo "<h2>Installing guzzlehttp/guzzle...</h2>";

$output = [];
$return_code = 0;

// Run composer require command
exec('composer require guzzlehttp/guzzle:^7.0 --no-dev --optimize-autoloader 2>&1', $output, $return_code);

echo "<h3>Composer Output:</h3>";
echo "<pre>";
foreach ($output as $line) {
    echo htmlspecialchars($line) . "\n";
}
echo "</pre>";

echo "<h3>Return Code: $return_code</h3>";

if ($return_code === 0) {
    echo "<p style='color: green;'>✓ Dependencies installed successfully!</p>";
} else {
    echo "<p style='color: red;'>✗ Failed to install dependencies</p>";
}

// Check if Guzzle is now available
echo "<h2>Checking Installation:</h2>";
if (class_exists('GuzzleHttp\Client')) {
    echo "<p style='color: green;'>✓ GuzzleHttp\\Client is now available</p>";
} else {
    echo "<p style='color: red;'>✗ GuzzleHttp\\Client still not available</p>";
}

// List vendor directory
echo "<h2>Vendor Directory Contents:</h2>";
if (is_dir(__DIR__ . '/vendor')) {
    echo "<ul>";
    foreach (scandir(__DIR__ . '/vendor') as $item) {
        if ($item != '.' && $item != '..') {
            echo "<li>$item</li>";
        }
    }
    echo "</ul>";
}

echo "<p><a href='test-dependencies.php'>Test Dependencies Again</a></p>";
echo "<p><a href='login.php'>Test Auth0 Login</a></p>";
?>
