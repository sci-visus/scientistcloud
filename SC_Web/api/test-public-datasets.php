<?php
/**
 * Test endpoint to debug public datasets query
 * Access at: /portal/api/test-public-datasets.php
 */

require_once(__DIR__ . '/../config.php');

header('Content-Type: application/json');

try {
    // Get MongoDB connection
    $mongo_url = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: 'mongodb://localhost:27017');
    $db_name = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
    $collectionName = defined('COLLECTION_DATASETS') ? COLLECTION_DATASETS : 'visstoredatas';
    
    if (!class_exists('MongoDB\Client')) {
        echo json_encode([
            'error' => 'MongoDB PHP extension not available',
            'mongo_url' => $mongo_url,
            'db_name' => $db_name,
            'collection' => $collectionName
        ]);
        exit;
    }
    
    $mongo_client = new MongoDB\Client($mongo_url);
    $db = $mongo_client->selectDatabase($db_name);
    $datasets_collection = $db->selectCollection($collectionName);
    
    // Count total datasets
    $totalCount = $datasets_collection->countDocuments([]);
    
    // Count datasets with is_public field
    $withPublicField = $datasets_collection->countDocuments(['is_public' => ['$exists' => true]]);
    
    // Count public datasets (various formats)
    $publicTrue = $datasets_collection->countDocuments(['is_public' => true]);
    $publicString = $datasets_collection->countDocuments(['is_public' => 'true']);
    $publicOne = $datasets_collection->countDocuments(['is_public' => 1]);
    
    // Get sample datasets
    $sampleDatasets = [];
    $cursor = $datasets_collection->find([])->limit(5);
    foreach ($cursor as $doc) {
        $sampleDatasets[] = [
            'name' => $doc['name'] ?? 'N/A',
            'uuid' => $doc['uuid'] ?? 'N/A',
            'is_public' => $doc['is_public'] ?? 'NOT SET',
            'is_public_type' => gettype($doc['is_public'] ?? null)
        ];
    }
    
    // Query for public datasets
    $query = [
        '$or' => [
            ['is_public' => true],
            ['is_public' => 'true'],
            ['is_public' => 'True'],
            ['is_public' => 1],
            ['is_public' => '1']
        ]
    ];
    
    $publicDatasets = [];
    $cursor = $datasets_collection->find($query)->limit(10);
    foreach ($cursor as $doc) {
        if (is_object($doc) && method_exists($doc, 'toArray')) {
            $publicDatasets[] = $doc->toArray();
        } else {
            $publicDatasets[] = json_decode(json_encode($doc), true);
        }
    }
    
    echo json_encode([
        'success' => true,
        'mongo_url' => $mongo_url,
        'db_name' => $db_name,
        'collection' => $collectionName,
        'stats' => [
            'total_datasets' => $totalCount,
            'datasets_with_is_public_field' => $withPublicField,
            'is_public_true' => $publicTrue,
            'is_public_string_true' => $publicString,
            'is_public_one' => $publicOne
        ],
        'sample_datasets' => $sampleDatasets,
        'public_datasets_found' => count($publicDatasets),
        'public_datasets' => array_map(function($ds) {
            return [
                'name' => $ds['name'] ?? 'N/A',
                'uuid' => $ds['uuid'] ?? 'N/A',
                'is_public' => $ds['is_public'] ?? 'N/A',
                'is_public_type' => gettype($ds['is_public'] ?? null)
            ];
        }, $publicDatasets)
    ], JSON_PRETTY_PRINT);
    
} catch (Exception $e) {
    echo json_encode([
        'error' => $e->getMessage(),
        'trace' => $e->getTraceAsString()
    ], JSON_PRETTY_PRINT);
}
?>

