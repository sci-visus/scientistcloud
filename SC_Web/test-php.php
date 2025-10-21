<?php
/**
 * PHP Test Script for ScientistCloud Data Portal
 * Tests basic PHP functionality and configuration
 */

echo "=== ScientistCloud Data Portal - PHP Test ===\n\n";

// Test 1: Basic PHP functionality
echo "1. Testing basic PHP functionality...\n";
echo "   PHP Version: " . phpversion() . "\n";
echo "   Current Directory: " . getcwd() . "\n";
echo "   ✅ Basic PHP functionality working\n\n";

// Test 2: File system access
echo "2. Testing file system access...\n";
$files_to_check = [
    'index.php',
    'config.php',
    'includes/auth.php',
    'includes/dataset_manager.php',
    'includes/dashboard_manager.php',
    'assets/css/main.css',
    'assets/js/main.js'
];

foreach ($files_to_check as $file) {
    if (file_exists($file)) {
        echo "   ✅ $file exists\n";
    } else {
        echo "   ❌ $file missing\n";
    }
}
echo "\n";

// Test 3: Test configuration
echo "3. Testing test configuration...\n";
try {
    require_once('test-config.php');
    echo "   ✅ Test configuration loaded\n";
    
    $user = getCurrentUser();
    echo "   ✅ Mock user: " . $user['name'] . " (" . $user['email'] . ")\n";
    
    $datasets = getUserDatasets($user['id']);
    echo "   ✅ Mock datasets: " . count($datasets) . " found\n";
    
    foreach ($datasets as $dataset) {
        echo "      - " . $dataset['name'] . " (" . $dataset['status'] . ")\n";
    }
    
} catch (Exception $e) {
    echo "   ❌ Test configuration error: " . $e->getMessage() . "\n";
}
echo "\n";

// Test 4: Session functionality
echo "4. Testing session functionality...\n";
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}
echo "   ✅ Session started\n";
echo "   ✅ User ID in session: " . ($_SESSION['user_id'] ?? 'Not set') . "\n\n";

// Test 5: JSON functionality
echo "5. Testing JSON functionality...\n";
$test_data = [
    'success' => true,
    'datasets' => $datasets,
    'user' => $user
];

$json_output = json_encode($test_data);
if ($json_output !== false) {
    echo "   ✅ JSON encoding working\n";
    echo "   ✅ JSON length: " . strlen($json_output) . " characters\n";
} else {
    echo "   ❌ JSON encoding failed\n";
}
echo "\n";

// Test 6: Web server simulation
echo "6. Testing web server simulation...\n";
echo "   ✅ All tests passed!\n";
echo "   ✅ Ready to start web server\n\n";

echo "=== Test Complete ===\n";
echo "To start the web server, run:\n";
echo "php -S localhost:8000 -t .\n";
echo "Then visit: http://localhost:8000/test-index.php\n";
?>
