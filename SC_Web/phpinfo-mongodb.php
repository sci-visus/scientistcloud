<?php
/**
 * PHP Info for MongoDB Extension Debugging
 */

// Enable error reporting
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "<h1>PHP MongoDB Extension Debug</h1>";

echo "<h2>1. PHP Version and SAPI</h2>";
echo "PHP Version: " . phpversion() . "<br>";
echo "PHP SAPI: " . php_sapi_name() . "<br>";

echo "<h2>2. Loaded Extensions</h2>";
$extensions = get_loaded_extensions();
sort($extensions);
echo "Total extensions: " . count($extensions) . "<br>";
echo "Extensions: " . implode(', ', $extensions) . "<br>";

echo "<h2>3. MongoDB Extension Check</h2>";
if (extension_loaded('mongodb')) {
    echo "✅ MongoDB extension is loaded<br>";
    echo "MongoDB version: " . phpversion('mongodb') . "<br>";
} else {
    echo "❌ MongoDB extension is NOT loaded<br>";
}

echo "<h2>4. PHP Configuration Files</h2>";
echo "Loaded ini file: " . php_ini_loaded_file() . "<br>";
echo "Scanned ini files: " . implode(', ', php_ini_scanned_files()) . "<br>";

echo "<h2>5. Extension Directory Check</h2>";
$ext_dir = "/usr/local/lib/php/extensions/";
if (is_dir($ext_dir)) {
    echo "Extension directory exists: $ext_dir<br>";
    $dirs = scandir($ext_dir);
    foreach ($dirs as $dir) {
        if ($dir != '.' && $dir != '..') {
            echo "Found extension directory: $dir<br>";
            $mongodb_file = $ext_dir . $dir . "/mongodb.so";
            if (file_exists($mongodb_file)) {
                echo "✅ MongoDB extension found at: $mongodb_file<br>";
            } else {
                echo "❌ MongoDB extension NOT found in: $dir<br>";
            }
        }
    }
} else {
    echo "❌ Extension directory not found: $ext_dir<br>";
}

echo "<h2>6. Composer Check</h2>";
if (file_exists('/var/www/html/vendor/autoload.php')) {
    echo "✅ Composer autoload found<br>";
    if (file_exists('/var/www/html/vendor/mongodb/mongodb')) {
        echo "✅ MongoDB Composer library found<br>";
    } else {
        echo "❌ MongoDB Composer library NOT found<br>";
    }
} else {
    echo "❌ Composer autoload NOT found<br>";
}

echo "<h2>7. Class Existence Check</h2>";
if (class_exists('MongoDB\Client')) {
    echo "✅ MongoDB\\Client class exists<br>";
} else {
    echo "❌ MongoDB\\Client class does NOT exist<br>";
}

echo "<h2>8. Full PHP Info</h2>";
echo "<a href='?full=1'>Click here for full phpinfo()</a><br>";

if (isset($_GET['full'])) {
    echo "<hr>";
    phpinfo();
}
?>
