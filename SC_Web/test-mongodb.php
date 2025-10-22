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
