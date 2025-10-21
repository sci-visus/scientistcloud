<?php
/**
 * Test Configuration for ScientistCloud Data Portal
 * This file provides mock configuration for testing without full scientistCloudLib setup
 */

// Mock environment variables for testing
$_ENV['MONGO_URL'] = 'mongodb://localhost:27017';
$_ENV['DB_NAME'] = 'scientistcloud_test';
$_ENV['AUTH0_DOMAIN'] = 'test.auth0.com';
$_ENV['AUTH0_CLIENT_ID'] = 'test_client_id';
$_ENV['AUTH0_CLIENT_SECRET'] = 'test_client_secret';
$_ENV['SECRET_KEY'] = 'test_secret_key';
$_ENV['SECRET_IV'] = 'test_secret_iv';

// Mock configuration class
class MockConfig {
    public $database;
    public $collections;
    public $server;
    public $auth;
    
    public function __construct() {
        $this->database = (object)[
            'mongo_url' => $_ENV['MONGO_URL'],
            'db_name' => $_ENV['DB_NAME']
        ];
        
        $this->collections = (object)[
            'visstoredatas' => 'visstoredatas',
            'user_profile' => 'user_profile',
            'teams' => 'teams',
            'shared_user' => 'shared_user'
        ];
        
        $this->server = (object)[
            'deploy_server' => 'http://localhost:8000',
            'domain_name' => 'localhost'
        ];
        
        $this->auth = (object)[
            'auth0_domain' => $_ENV['AUTH0_DOMAIN'],
            'auth0_client_id' => $_ENV['AUTH0_CLIENT_ID'],
            'auth0_client_secret' => $_ENV['AUTH0_CLIENT_SECRET'],
            'secret_key' => $_ENV['SECRET_KEY'],
            'secret_iv' => $_ENV['SECRET_IV']
        ];
    }
    
    public function get_database_name() {
        return $this->database->db_name;
    }
    
    public function get_collection_name($type) {
        return $this->collections->$type ?? 'unknown';
    }
    
    public function get_mongo_url() {
        return $this->database->mongo_url;
    }
}

// Mock MongoDB connection
class MockMongoConnection {
    public function selectDatabase($name) {
        return new MockDatabase();
    }
}

class MockDatabase {
    public function selectCollection($name) {
        return new MockCollection();
    }
}

class MockCollection {
    public function find($query = [], $options = []) {
        // Return mock dataset data
        return new MockCursor();
    }
    
    public function findOne($query = []) {
        // Return mock user data
        return (object)[
            '_id' => new MockObjectId('507f1f77bcf86cd799439011'),
            'email' => 'test@example.com',
            'name' => 'Test User',
            'preferred_dashboard' => 'openvisus',
            'team_id' => null,
            'permissions' => ['read', 'upload']
        ];
    }
    
    public function insertOne($document) {
        return (object)['insertedId' => new MockObjectId()];
    }
    
    public function updateOne($filter, $update, $options = []) {
        return (object)['modifiedCount' => 1];
    }
    
    public function deleteOne($filter) {
        return (object)['deletedCount' => 1];
    }
}

class MockCursor {
    public function toArray() {
        return [
            (object)[
                '_id' => new MockObjectId('507f1f77bcf86cd799439012'),
                'uuid' => 'test-uuid-1',
                'name' => 'Sample Dataset 1',
                'sensor' => 'TIFF',
                'status' => 'done',
                'compression_status' => 'compressed',
                'time' => '2025-01-20T10:00:00Z',
                'data_size' => 1024000,
                'dimensions' => '1024x1024x100',
                'google_drive_link' => null,
                'folder_uuid' => 'folder-1',
                'team_uuid' => '',
                'user_id' => '507f1f77bcf86cd799439011',
                'tags' => ['test', 'sample'],
                'created_at' => new MockUTCDateTime(),
                'updated_at' => new MockUTCDateTime()
            ],
            (object)[
                '_id' => new MockObjectId('507f1f77bcf86cd799439013'),
                'uuid' => 'test-uuid-2',
                'name' => 'Sample Dataset 2',
                'sensor' => 'HDF5',
                'status' => 'processing',
                'compression_status' => 'uncompressed',
                'time' => '2025-01-20T11:00:00Z',
                'data_size' => 2048000,
                'dimensions' => '512x512x200',
                'google_drive_link' => 'https://example.com/dataset2',
                'folder_uuid' => 'folder-2',
                'team_uuid' => '',
                'user_id' => '507f1f77bcf86cd799439011',
                'tags' => ['hdf5', 'scientific'],
                'created_at' => new MockUTCDateTime(),
                'updated_at' => new MockUTCDateTime()
            ]
        ];
    }
}

class MockObjectId {
    private $id;
    
    public function __construct($id = null) {
        $this->id = $id ?: bin2hex(random_bytes(12));
    }
    
    public function __toString() {
        return $this->id;
    }
}

class MockUTCDateTime {
    public function toDateTime() {
        return new DateTime();
    }
}

// Mock functions
function get_config() {
    return new MockConfig();
}

function get_mongo_connection() {
    return new MockMongoConnection();
}

function get_database_name() {
    return 'scientistcloud_test';
}

function get_collection_name($type) {
    $collections = [
        'visstoredatas' => 'visstoredatas',
        'user_profile' => 'user_profile',
        'teams' => 'teams',
        'shared_user' => 'shared_user'
    ];
    return $collections[$type] ?? 'unknown';
}

function logMessage($level, $message, $context = []) {
    echo "[$level] $message " . json_encode($context) . "\n";
}

// Mock authentication
function getCurrentUser() {
    return [
        'id' => '507f1f77bcf86cd799439011',
        'email' => 'test@example.com',
        'name' => 'Test User',
        'preferred_dashboard' => 'openvisus',
        'team_id' => null,
        'permissions' => ['read', 'upload']
    ];
}

function isAuthenticated() {
    return true; // Always authenticated in test mode
}

function getUserDatasets($userId) {
    $mongo = get_mongo_connection();
    $db = $mongo->selectDatabase(get_database_name());
    $collection = $db->selectCollection(get_collection_name('visstoredatas'));
    
    $datasets = $collection->find(['user_id' => $userId])->toArray();
    
    return array_map(function($dataset) {
        return [
            'id' => (string)$dataset->_id,
            'name' => $dataset->name,
            'uuid' => $dataset->uuid,
            'sensor' => $dataset->sensor,
            'status' => $dataset->status,
            'compression_status' => $dataset->compression_status,
            'time' => $dataset->time,
            'data_size' => $dataset->data_size,
            'dimensions' => $dataset->dimensions,
            'google_drive_link' => $dataset->google_drive_link,
            'folder_uuid' => $dataset->folder_uuid,
            'team_uuid' => $dataset->team_uuid,
            'user_id' => $dataset->user_id,
            'tags' => $dataset->tags,
            'created_at' => $dataset->created_at,
            'updated_at' => $dataset->updated_at
        ];
    }, $datasets);
}

function getDatasetById($datasetId) {
    $datasets = getUserDatasets('507f1f77bcf86cd799439011');
    foreach ($datasets as $dataset) {
        if ($dataset['id'] === $datasetId) {
            return $dataset;
        }
    }
    return null;
}

function getDatasetFolders($userId) {
    return [
        ['uuid' => 'folder-1', 'name' => 'Folder 1', 'count' => 1],
        ['uuid' => 'folder-2', 'name' => 'Folder 2', 'count' => 1]
    ];
}

function getDatasetStats($userId) {
    return [
        'total_datasets' => 2,
        'total_size' => 3072000,
        'status_counts' => ['done' => 1, 'processing' => 1]
    ];
}

function getUserPreferredDashboard($userId) {
    return 'openvisus';
}

function getDashboardStatus($datasetId, $dashboardType) {
    return 'ready';
}

function getAvailableDashboards($datasetId) {
    return [
        [
            'type' => 'openvisus',
            'name' => 'OpenVisus Explorer',
            'description' => 'Interactive 3D volume rendering with OpenVisus',
            'url' => '/viewer/openvisus.php?dataset=' . $datasetId
        ],
        [
            'type' => 'bokeh',
            'name' => 'Bokeh Dashboard',
            'description' => 'Interactive data visualization with Bokeh',
            'url' => '/viewer/bokeh.php?dataset=' . $datasetId
        ]
    ];
}

function loadDashboard($datasetId, $dashboardType = 'openvisus') {
    return [
        'dataset' => getDatasetById($datasetId),
        'dashboard_type' => $dashboardType,
        'viewer_url' => '/viewer/' . $dashboardType . '.php?dataset=' . $datasetId
    ];
}

function shareDataset($datasetId, $userId) {
    return true;
}

function deleteDataset($datasetId) {
    return true;
}

function updateUserPreferences($userId, $preferences) {
    return true;
}

// Constants
define('DB_NAME', get_database_name());
define('MONGO_URL', get_mongo_connection());
define('COLLECTION_DATASETS', get_collection_name('visstoredatas'));
define('COLLECTION_USERS', get_collection_name('user_profile'));
define('COLLECTION_TEAMS', get_collection_name('teams'));
define('COLLECTION_SHARED', get_collection_name('shared_user'));
define('SC_SERVER_URL', 'http://localhost:8000');
define('SC_DOMAIN', 'localhost');
define('DEFAULT_DASHBOARD', 'openvisus');
define('SUPPORTED_DASHBOARDS', ['openvisus', 'bokeh', 'jupyter', 'plotly', 'vtk']);

// Start session (only if not already started)
if (session_status() == PHP_SESSION_NONE) {
    @session_start();
}

// Set test user session
$_SESSION['user_id'] = '507f1f77bcf86cd799439011';
$_SESSION['user_email'] = 'test@example.com';
$_SESSION['user_name'] = 'Test User';
?>
