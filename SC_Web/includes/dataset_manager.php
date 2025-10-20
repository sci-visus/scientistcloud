<?php
/**
 * Dataset Manager Module for ScientistCloud Data Portal
 * Handles dataset operations using scientistCloudLib
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/auth.php');

/**
 * Get user's datasets
 */
function getUserDatasets($userId) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        // Get user's own datasets
        $userDatasets = $collection->find([
            'user_id' => $userId
        ])->toArray();
        
        // Get shared datasets
        $sharedDatasets = $collection->find([
            'shared_with' => $userId
        ])->toArray();
        
        // Get team datasets
        $user = getCurrentUser();
        if ($user && $user['team_id']) {
            $teamDatasets = $collection->find([
                'team_id' => $user['team_id']
            ])->toArray();
        } else {
            $teamDatasets = [];
        }
        
        // Combine and format datasets
        $allDatasets = array_merge($userDatasets, $sharedDatasets, $teamDatasets);
        
        // Remove duplicates and format
        $uniqueDatasets = [];
        foreach ($allDatasets as $dataset) {
            $id = (string)$dataset['_id'];
            if (!isset($uniqueDatasets[$id])) {
                $uniqueDatasets[$id] = formatDataset($dataset);
            }
        }
        
        return array_values($uniqueDatasets);
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get user datasets', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return [];
    }
}

/**
 * Get dataset by ID
 */
function getDatasetById($datasetId) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        $dataset = $collection->findOne(['_id' => new MongoDB\BSON\ObjectId($datasetId)]);
        
        if ($dataset) {
            return formatDataset($dataset);
        }
        
        return null;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset by ID', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return null;
    }
}

/**
 * Format dataset for display
 */
function formatDataset($dataset) {
    return [
        'id' => (string)$dataset['_id'],
        'name' => $dataset['name'] ?? 'Unnamed Dataset',
        'uuid' => $dataset['uuid'] ?? '',
        'sensor' => $dataset['sensor'] ?? 'Unknown',
        'status' => $dataset['status'] ?? 'unknown',
        'compression_status' => $dataset['compression_status'] ?? 'unknown',
        'time' => $dataset['time'] ?? null,
        'data_size' => $dataset['data_size'] ?? 0,
        'dimensions' => $dataset['dimensions'] ?? '',
        'google_drive_link' => $dataset['google_drive_link'] ?? null,
        'folder_uuid' => $dataset['folder_uuid'] ?? '',
        'team_uuid' => $dataset['team_uuid'] ?? '',
        'user_id' => $dataset['user_id'] ?? '',
        'tags' => $dataset['tags'] ?? [],
        'created_at' => $dataset['created_at'] ?? null,
        'updated_at' => $dataset['updated_at'] ?? null
    ];
}

/**
 * Get datasets by folder
 */
function getDatasetsByFolder($folderUuid) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        $datasets = $collection->find([
            'folder_uuid' => $folderUuid
        ])->toArray();
        
        return array_map('formatDataset', $datasets);
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get datasets by folder', ['folder_uuid' => $folderUuid, 'error' => $e->getMessage()]);
        return [];
    }
}

/**
 * Get dataset folders
 */
function getDatasetFolders($userId) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        // Get unique folder UUIDs for user's datasets
        $pipeline = [
            ['$match' => ['user_id' => $userId]],
            ['$group' => ['_id' => '$folder_uuid', 'count' => ['$sum' => 1]]],
            ['$sort' => ['_id' => 1]]
        ];
        
        $folders = $collection->aggregate($pipeline)->toArray();
        
        $folderList = [];
        foreach ($folders as $folder) {
            if ($folder['_id']) {
                $folderList[] = [
                    'uuid' => $folder['_id'],
                    'name' => $folder['_id'], // You might want to store folder names separately
                    'count' => $folder['count']
                ];
            }
        }
        
        return $folderList;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset folders', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return [];
    }
}

/**
 * Update dataset status
 */
function updateDatasetStatus($datasetId, $status) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        $result = $collection->updateOne(
            ['_id' => new MongoDB\BSON\ObjectId($datasetId)],
            [
                '$set' => [
                    'status' => $status,
                    'updated_at' => new MongoDB\BSON\UTCDateTime()
                ]
            ]
        );
        
        return $result->getModifiedCount() > 0;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to update dataset status', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Share dataset with user
 */
function shareDataset($datasetId, $userId) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        $result = $collection->updateOne(
            ['_id' => new MongoDB\BSON\ObjectId($datasetId)],
            [
                '$addToSet' => ['shared_with' => $userId],
                '$set' => ['updated_at' => new MongoDB\BSON\UTCDateTime()]
            ]
        );
        
        return $result->getModifiedCount() > 0;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to share dataset', ['dataset_id' => $datasetId, 'user_id' => $userId, 'error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Delete dataset
 */
function deleteDataset($datasetId) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        $result = $collection->deleteOne(['_id' => new MongoDB\BSON\ObjectId($datasetId)]);
        
        return $result->getDeletedCount() > 0;
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to delete dataset', ['dataset_id' => $datasetId, 'error' => $e->getMessage()]);
        return false;
    }
}

/**
 * Get dataset statistics
 */
function getDatasetStats($userId) {
    try {
        $mongo = getMongoConnection();
        $db = $mongo->selectDatabase(getDatabaseName());
        $collection = $db->selectCollection(getCollectionName('datasets'));
        
        $pipeline = [
            ['$match' => ['user_id' => $userId]],
            ['$group' => [
                '_id' => null,
                'total_datasets' => ['$sum' => 1],
                'total_size' => ['$sum' => '$data_size'],
                'status_counts' => ['$push' => '$status']
            ]]
        ];
        
        $result = $collection->aggregate($pipeline)->toArray();
        
        if (empty($result)) {
            return [
                'total_datasets' => 0,
                'total_size' => 0,
                'status_counts' => []
            ];
        }
        
        $stats = $result[0];
        $statusCounts = array_count_values($stats['status_counts']);
        
        return [
            'total_datasets' => $stats['total_datasets'],
            'total_size' => $stats['total_size'],
            'status_counts' => $statusCounts
        ];
        
    } catch (Exception $e) {
        logMessage('ERROR', 'Failed to get dataset stats', ['user_id' => $userId, 'error' => $e->getMessage()]);
        return [
            'total_datasets' => 0,
            'total_size' => 0,
            'status_counts' => []
        ];
    }
}
?>
