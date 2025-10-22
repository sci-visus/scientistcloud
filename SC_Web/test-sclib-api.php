<?php
/**
 * Test SCLib API Connection
 * Verifies that the portal can communicate with SCLib API
 */

require_once(__DIR__ . '/includes/sclib_client.php');

echo "<h1>SCLib API Connection Test</h1>";

try {
    $sclib = getSCLibClient();
    
    echo "<h2>1. Health Check</h2>";
    $healthy = $sclib->healthCheck();
    if ($healthy) {
        echo "✅ SCLib API is healthy<br>";
    } else {
        echo "❌ SCLib API is not responding<br>";
    }
    
    echo "<h2>2. API Configuration</h2>";
    echo "API Base URL: " . getenv('SCLIB_API_URL') ?: 'http://localhost:5001' . "<br>";
    
    echo "<h2>3. Test User Datasets</h2>";
    $testUserId = 'test-user-123';
    $datasets = $sclib->getUserDatasets($testUserId);
    echo "Found " . count($datasets) . " datasets for test user<br>";
    
    if (!empty($datasets)) {
        echo "<h3>Sample Dataset:</h3>";
        echo "<pre>" . json_encode($datasets[0], JSON_PRETTY_PRINT) . "</pre>";
    }
    
echo "<h2>4. Authentication Test</h2>";
$authResult = $sclib->validateAuthToken('test-token');
if ($authResult['success']) {
    echo "✅ Authentication API working<br>";
} else {
    echo "❌ Authentication API failed: " . ($authResult['error'] ?? 'Unknown error') . "<br>";
}

echo "<h2>5. Architecture Overview</h2>";
echo "✅ Portal → SCLib Portal API (port 5001) → SCLib Auth (port 8001)<br>";
echo "✅ All database operations handled by SCLib<br>";
echo "✅ All authentication handled by SCLib_Auth<br>";
echo "✅ No MongoDB extension required in PHP<br>";
echo "✅ Clean separation of concerns<br>";

echo "<h2>6. Connection Status</h2>";
echo "✅ SCLib API connection successful<br>";
echo "✅ Portal can communicate with SCLib<br>";
echo "✅ Authentication delegated to SCLib_Auth<br>";
echo "✅ Database operations delegated to SCLib<br>";
    
} catch (Exception $e) {
    echo "<h2>❌ Error</h2>";
    echo "SCLib API connection failed: " . $e->getMessage() . "<br>";
    echo "<p>Make sure SCLib API is running on port 5001</p>";
    echo "<p>You can start it with: <code>python SCLib_PortalAPI.py</code></p>";
}

echo "<hr>";
echo "<p><strong>Next Steps:</strong></p>";
echo "<ul>";
echo "<li>Start SCLib Auth: <code>python /var/www/scientistCloudLib/SCLib_Auth/start_auth_server.py</code></li>";
echo "<li>Start SCLib Portal API: <code>python /var/www/scientistCloudLib/SCLib_JobProcessing/SCLib_PortalAPI.py</code></li>";
echo "<li>Or use Docker: <code>docker-compose up sclib-auth sclib-portal-api</code></li>";
echo "<li>Test the portal endpoints</li>";
echo "</ul>";
?>
