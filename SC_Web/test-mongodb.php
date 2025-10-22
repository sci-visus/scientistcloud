<?php
/**
 * MongoDB Connection Test
 * This script tests MongoDB connectivity and extension availability
 */

// Enable error reporting
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "<h1>MongoDB Connection Test</h1>";

// Check if MongoDB extension is loaded
echo "<h2>1. MongoDB Extension Check</h2>";
if (extension_loaded('mongodb')) {
    echo "✅ MongoDB extension is loaded<br>";
    echo "MongoDB version: " . phpversion('mongodb') . "<br>";
} else {
    echo "❌ MongoDB extension is NOT loaded<br>";
    echo "Available extensions: " . implode(', ', get_loaded_extensions()) . "<br>";
    
    // Check if extension file exists
    $extension_path = "/usr/local/lib/php/extensions/no-debug-non-zts-20220829/mongodb.so";
    if (file_exists($extension_path)) {
        echo "MongoDB extension file exists at: $extension_path<br>";
    } else {
        echo "MongoDB extension file NOT found at: $extension_path<br>";
        echo "Looking for extension files...<br>";
        $ext_dir = "/usr/local/lib/php/extensions/";
        if (is_dir($ext_dir)) {
            $dirs = scandir($ext_dir);
            foreach ($dirs as $dir) {
                if ($dir != '.' && $dir != '..') {
                    $mongodb_file = $ext_dir . $dir . "/mongodb.so";
                    if (file_exists($mongodb_file)) {
                        echo "Found MongoDB extension at: $mongodb_file<br>";
                    }
                }
            }
        }
    }
    
    // Check PHP configuration
    echo "<br>PHP Configuration:<br>";
    echo "PHP version: " . phpversion() . "<br>";
    echo "PHP SAPI: " . php_sapi_name() . "<br>";
    echo "Configuration file: " . php_ini_loaded_file() . "<br>";
    echo "Additional ini files: " . implode(', ', php_ini_scanned_files()) . "<br>";
    
    exit(1);
}

// Test MongoDB connection
echo "<h2>2. MongoDB Connection Test</h2>";
try {
    // Include the SCLib configuration
    require_once('/var/www/scientistCloudLib/SCLib_JobProcessing/SCLib_Config.php');
    
    // Get MongoDB connection
    $database = get_mongo_connection();
    echo "✅ MongoDB connection successful<br>";
    
    // Test a simple query
    $collections = $database->listCollections();
    $collection_names = [];
    foreach ($collections as $collection) {
        $collection_names[] = $collection->getName();
    }
    
    echo "Available collections: " . implode(', ', $collection_names) . "<br>";
    
    // Test visstoredatas collection
    $visstoredatas = $database->selectCollection('visstoredatas');
    $count = $visstoredatas->countDocuments();
    echo "Documents in visstoredatas: $count<br>";
    
} catch (Exception $e) {
    echo "❌ MongoDB connection failed: " . $e->getMessage() . "<br>";
    echo "Error details: " . $e->getTraceAsString() . "<br>";
}

echo "<h2>3. PHP Configuration</h2>";
echo "PHP version: " . phpversion() . "<br>";
echo "Loaded extensions: " . implode(', ', get_loaded_extensions()) . "<br>";

echo "<h2>4. Environment Variables</h2>";
echo "MONGO_URL: " . (getenv('MONGO_URL') ?: 'Not set') . "<br>";
echo "DB_NAME: " . (getenv('DB_NAME') ?: 'Not set') . "<br>";

?>
