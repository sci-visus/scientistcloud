<?php
/**
 * Get dataset dimension from nexus file
 * Returns the dimension (1, 2, 3, or 4) of a dataset by reading its nexus file
 */

require_once __DIR__ . '/../includes/config.php';
require_once __DIR__ . '/../includes/mongo_connection.php';

header('Content-Type: application/json');

try {
    // Get UUID from request
    $uuid = $_GET['uuid'] ?? null;
    
    if (!$uuid) {
        echo json_encode([
            'success' => false,
            'error' => 'UUID parameter required'
        ]);
        exit;
    }
    
    // Connect to MongoDB
    $mongo = getMongoConnection();
    $db = $mongo->selectDatabase(DB_NAME);
    $collection = $db->selectCollection('visstoredatas');
    
    // Find dataset
    $dataset = $collection->findOne(['uuid' => $uuid]);
    
    if (!$dataset) {
        echo json_encode([
            'success' => false,
            'error' => 'Dataset not found'
        ]);
        exit;
    }
    
    // Check if dimension is already stored in metadata
    if (isset($dataset['dimension']) && is_numeric($dataset['dimension'])) {
        echo json_encode([
            'success' => true,
            'dimension' => (int)$dataset['dimension']
        ]);
        exit;
    }
    
    // Try to determine dimension from nexus file
    $dimension = null;
    
    // Get dataset path
    $baseDir = VISUS_DATASETS . '/upload/' . $uuid;
    $convertedDir = VISUS_DATASETS . '/converted/' . $uuid;
    
    // Look for .nxs files
    $nxsFiles = [];
    if (is_dir($baseDir)) {
        $files = scandir($baseDir);
        foreach ($files as $file) {
            if (pathinfo($file, PATHINFO_EXTENSION) === 'nxs') {
                $nxsFiles[] = $baseDir . '/' . $file;
            }
        }
    }
    
    if (is_dir($convertedDir)) {
        $files = scandir($convertedDir);
        foreach ($files as $file) {
            if (pathinfo($file, PATHINFO_EXTENSION) === 'nxs') {
                $nxsFiles[] = $convertedDir . '/' . $file;
            }
        }
    }
    
    // Try to read dimension from first nexus file
    if (!empty($nxsFiles) && file_exists($nxsFiles[0])) {
        try {
            // Use h5py or nexus file reader to get dimension
            // For now, try to use a simple heuristic or call a Python script
            // This is a placeholder - you may want to implement actual nexus file reading
            
            // Try to use Python to read nexus file dimension
            $pythonScript = __DIR__ . '/../utils/get_nexus_dimension.py';
            if (file_exists($pythonScript)) {
                $command = escapeshellcmd('python3') . ' ' . escapeshellarg($pythonScript) . ' ' . escapeshellarg($nxsFiles[0]);
                $output = shell_exec($command . ' 2>&1');
                if ($output && is_numeric(trim($output))) {
                    $dimension = (int)trim($output);
                }
            }
            
            // Fallback: try to infer from file size or other heuristics
            // This is not reliable but better than nothing
            if ($dimension === null) {
                // Could try reading nexus file header, but that's complex
                // For now, return null and let frontend handle fallback
            }
        } catch (Exception $e) {
            error_log("Error reading nexus file dimension: " . $e->getMessage());
        }
    }
    
    if ($dimension !== null) {
        // Store dimension in dataset metadata for future use
        $collection->updateOne(
            ['uuid' => $uuid],
            ['$set' => ['dimension' => $dimension]]
        );
        
        echo json_encode([
            'success' => true,
            'dimension' => $dimension
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'error' => 'Could not determine dimension',
            'dimension' => null
        ]);
    }
    
} catch (Exception $e) {
    error_log("Error in get_dataset_dimension.php: " . $e->getMessage());
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
}

