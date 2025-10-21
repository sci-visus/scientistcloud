<?php
/**
 * Simple Test Page for ScientistCloud Data Portal
 * Basic functionality test
 */

echo "<!DOCTYPE html>";
echo "<html><head><title>ScientistCloud Test</title></head><body>";
echo "<h1>🎉 ScientistCloud Data Portal - Test Page</h1>";
echo "<p><strong>Status:</strong> Server is running successfully!</p>";

echo "<h2>📊 Test Results:</h2>";
echo "<ul>";
echo "<li>✅ PHP Version: " . phpversion() . "</li>";
echo "<li>✅ Current Directory: " . getcwd() . "</li>";
echo "<li>✅ Server Time: " . date('Y-m-d H:i:s') . "</li>";
echo "<li>✅ Files Loaded: " . count(glob('*.php')) . " PHP files</li>";
echo "</ul>";

echo "<h2>🔗 Test Links:</h2>";
echo "<ul>";
echo "<li><a href='test-index.php' target='_blank'>📱 Main Test Page (Full Website)</a></li>";
echo "<li><a href='sc_index.html' target='_blank'>🎨 Original HTML Design</a></li>";
echo "<li><a href='test-php.php' target='_blank'>🔧 PHP Test Script</a></li>";
echo "</ul>";

echo "<h2>🌐 Server Information:</h2>";
echo "<ul>";
echo "<li><strong>Server:</strong> " . $_SERVER['SERVER_SOFTWARE'] . "</li>";
echo "<li><strong>Host:</strong> " . $_SERVER['HTTP_HOST'] . "</li>";
echo "<li><strong>Port:</strong> " . $_SERVER['SERVER_PORT'] . "</li>";
echo "<li><strong>Document Root:</strong> " . $_SERVER['DOCUMENT_ROOT'] . "</li>";
echo "</ul>";

echo "<h2>📁 File Structure:</h2>";
echo "<pre>";
$files = glob('*');
foreach($files as $file) {
    if(is_dir($file)) {
        echo "📁 $file/\n";
    } else {
        echo "📄 $file\n";
    }
}
echo "</pre>";

echo "<h2>✅ Ready to Test!</h2>";
echo "<p>Click the links above to test different parts of the website.</p>";
echo "<p><strong>Main Test URL:</strong> <a href='test-index.php'>test-index.php</a></p>";

echo "</body></html>";
?>
