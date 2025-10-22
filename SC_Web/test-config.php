<?php
/**
 * Test configuration loading
 */

// Set error reporting
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "<h1>ScientistCloud Configuration Test</h1>";

// Test 1: Check if SCLib files exist
echo "<h2>1. File Path Tests</h2>";

$sc_lib_root = '/var/www/scientistCloudLib';
$sc_config_path = $sc_lib_root . '/SCLib_JobProcessing';
$config_file = $sc_config_path . '/SCLib_Config.php';

echo "<p>SC_LIB_ROOT: $sc_lib_root</p>";
echo "<p>SC_CONFIG_PATH: $sc_config_path</p>";
echo "<p>Config file: $config_file</p>";

if (file_exists($sc_lib_root)) {
    echo "<p style='color: green;'>✓ SCLib root directory exists</p>";
} else {
    echo "<p style='color: red;'>✗ SCLib root directory missing</p>";
}

if (file_exists($sc_config_path)) {
    echo "<p style='color: green;'>✓ SCLib_JobProcessing directory exists</p>";
} else {
    echo "<p style='color: red;'>✗ SCLib_JobProcessing directory missing</p>";
}

if (file_exists($config_file)) {
    echo "<p style='color: green;'>✓ SCLib_Config.php exists</p>";
} else {
    echo "<p style='color: red;'>✗ SCLib_Config.php missing</p>";
}

// Test 2: Try to include config
echo "<h2>2. Configuration Loading Test</h2>";

try {
    require_once($config_file);
    echo "<p style='color: green;'>✓ SCLib_Config.php loaded successfully</p>";
    
    // Test if functions are available
    if (function_exists('get_config')) {
        echo "<p style='color: green;'>✓ get_config() function available</p>";
    } else {
        echo "<p style='color: red;'>✗ get_config() function not available</p>";
    }
    
    if (function_exists('get_mongo_connection')) {
        echo "<p style='color: green;'>✓ get_mongo_connection() function available</p>";
    } else {
        echo "<p style='color: red;'>✗ get_mongo_connection() function not available</p>";
    }
    
} catch (Exception $e) {
    echo "<p style='color: red;'>✗ Error loading config: " . $e->getMessage() . "</p>";
}

// Test 3: Environment variables
echo "<h2>3. Environment Variables Test</h2>";

$env_vars = [
    'MONGO_URL',
    'DB_NAME', 
    'AUTH0_DOMAIN',
    'AUTH0_CLIENT_ID',
    'SECRET_KEY'
];

foreach ($env_vars as $var) {
    $value = getenv($var);
    if ($value) {
        echo "<p style='color: green;'>✓ $var: " . (strlen($value) > 20 ? substr($value, 0, 20) . '...' : $value) . "</p>";
    } else {
        echo "<p style='color: red;'>✗ $var: Not set</p>";
    }
}

// Test 4: Directory listing
echo "<h2>4. Directory Structure Test</h2>";

if (file_exists($sc_lib_root)) {
    echo "<h3>SCLib Root Contents:</h3>";
    $contents = scandir($sc_lib_root);
    echo "<ul>";
    foreach ($contents as $item) {
        if ($item != '.' && $item != '..') {
            $path = $sc_lib_root . '/' . $item;
            $type = is_dir($path) ? 'DIR' : 'FILE';
            echo "<li>$item ($type)</li>";
        }
    }
    echo "</ul>";
}

echo "<h2>Test Complete</h2>";
echo "<p><a href='index.php'>Back to Portal</a></p>";
?>