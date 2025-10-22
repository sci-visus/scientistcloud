<?php
/**
 * Simple MongoDB Test
 */

echo "<h1>Simple MongoDB Test</h1>";

echo "<h2>1. Extension Check</h2>";
if (extension_loaded('mongodb')) {
    echo "✅ MongoDB extension is loaded<br>";
} else {
    echo "❌ MongoDB extension is NOT loaded<br>";
}

echo "<h2>2. Class Check</h2>";
if (class_exists('MongoDB\Client')) {
    echo "✅ MongoDB\\Client class exists<br>";
} else {
    echo "❌ MongoDB\\Client class does NOT exist<br>";
}

echo "<h2>3. Manual Extension Loading</h2>";
if (!extension_loaded('mongodb')) {
    echo "Trying to load MongoDB extension manually...<br>";
    $ext_dirs = glob('/usr/local/lib/php/extensions/*/mongodb.so');
    if (!empty($ext_dirs)) {
        echo "Found extension files: " . implode(', ', $ext_dirs) . "<br>";
        foreach ($ext_dirs as $ext_file) {
            echo "Trying to load: $ext_file<br>";
            if (file_exists($ext_file)) {
                if (function_exists('dl')) {
                    if (dl($ext_file)) {
                        echo "✅ Successfully loaded: $ext_file<br>";
                        if (class_exists('MongoDB\Client')) {
                            echo "✅ MongoDB\\Client class now exists<br>";
                        } else {
                            echo "❌ MongoDB\\Client class still not available<br>";
                        }
                        break;
                    } else {
                        echo "❌ Failed to load: $ext_file<br>";
                    }
                } else {
                    echo "❌ dl() function not available<br>";
                }
            } else {
                echo "❌ File not found: $ext_file<br>";
            }
        }
    } else {
        echo "❌ No MongoDB extension files found<br>";
    }
} else {
    echo "MongoDB extension already loaded<br>";
}

echo "<h2>4. Final Test</h2>";
if (class_exists('MongoDB\Client')) {
    echo "✅ MongoDB\\Client class is available<br>";
    try {
        $client = new MongoDB\Client('mongodb://localhost:27017');
        echo "✅ MongoDB client created successfully<br>";
    } catch (Exception $e) {
        echo "❌ MongoDB client creation failed: " . $e->getMessage() . "<br>";
    }
} else {
    echo "❌ MongoDB\\Client class is NOT available<br>";
}

echo "<h2>5. Environment Variables</h2>";
echo "MONGO_URL: " . (getenv('MONGO_URL') ?: 'Not set') . "<br>";
echo "DB_NAME: " . (getenv('DB_NAME') ?: 'Not set') . "<br>";
?>
