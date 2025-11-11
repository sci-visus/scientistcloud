<?php
/**
 * Dataset Files API Endpoint
 * Returns file and folder structure for a dataset UUID
 * Lists files from both upload/<uuid> and converted/<uuid> directories
 */

// Start output buffering IMMEDIATELY to catch any output from included files
if (ob_get_level() > 0) {
    while (ob_get_level()) {
        ob_end_clean();
    }
}
ob_start();

// Disable error display to prevent output
ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);

// Start session BEFORE including config.php to ensure session is available
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    http_response_code(200);
    exit;
}

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/dataset_manager.php');

/**
 * Check if a file should be excluded based on configured patterns
 */
function shouldExcludeFile($filename) {
    $excludedPatterns = defined('EXCLUDED_FILE_PATTERNS') ? EXCLUDED_FILE_PATTERNS : ['.bin'];
    
    foreach ($excludedPatterns as $pattern) {
        // Handle wildcard patterns (e.g., '*.tmp')
        if (strpos($pattern, '*') !== false) {
            if (fnmatch($pattern, $filename, FNM_CASEFOLD)) {
                return true;
            }
        } else {
            // Handle extension patterns (e.g., '.bin' or 'bin')
            // Normalize pattern: ensure it starts with a dot
            $normalizedPattern = (substr($pattern, 0, 1) === '.') ? $pattern : '.' . $pattern;
            
            // Check if filename ends with the pattern (case-insensitive)
            $filenameLower = strtolower($filename);
            $patternLower = strtolower($normalizedPattern);
            
            if (substr($filenameLower, -strlen($patternLower)) === $patternLower) {
                return true;
            }
        }
    }
    
    return false;
}

/**
 * Recursively scan directory and return file structure
 * Excludes files matching patterns defined in EXCLUDED_FILE_PATTERNS
 */
function scanDirectory($dir, $basePath = '') {
    $result = [];
    
    if (!is_dir($dir)) {
        error_log("scanDirectory: Not a directory: $dir");
        return $result;
    }
    
    if (!is_readable($dir)) {
        error_log("scanDirectory: Directory not readable: $dir");
        return $result;
    }
    
    $items = scandir($dir);
    if ($items === false) {
        error_log("scanDirectory: scandir failed for: $dir");
        return $result;
    }
    
    error_log("scanDirectory: Found " . count($items) . " items in $dir");
    
    foreach ($items as $item) {
        if ($item === '.' || $item === '..') {
            continue;
        }
        
        $fullPath = $dir . '/' . $item;
        $relativePath = $basePath ? $basePath . '/' . $item : $item;
        
        if (is_dir($fullPath)) {
            // Recursively scan directory
            $children = scanDirectory($fullPath, $relativePath);
            // Only include directory if it has children (after filtering)
            if (count($children) > 0) {
                $result[] = [
                    'name' => $item,
                    'type' => 'directory',
                    'path' => $relativePath,
                    'children' => $children
                ];
            }
        } else {
            // Check if file should be excluded
            if (shouldExcludeFile($item)) {
                error_log("scanDirectory: Excluding file: $item");
                continue; // Skip this file
            }
            
            // Log file being added
            error_log("scanDirectory: Adding file: $item (path: $relativePath)");
            
            $result[] = [
                'name' => $item,
                'type' => 'file',
                'path' => $relativePath,
                'size' => filesize($fullPath),
                'modified' => filemtime($fullPath)
            ];
        }
    }
    
    // Sort: directories first, then files, both alphabetically
    usort($result, function($a, $b) {
        if ($a['type'] !== $b['type']) {
            return $a['type'] === 'directory' ? -1 : 1;
        }
        return strcmp($a['name'], $b['name']);
    });
    
    return $result;
}

try {
    // Check authentication
    if (!isAuthenticated()) {
        ob_end_clean();
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Authentication required']);
        exit;
    }

    // Get dataset UUID from request
    $datasetUuid = $_GET['dataset_uuid'] ?? null;
    if (!$datasetUuid) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Dataset UUID is required']);
        exit;
    }

    // Validate UUID format
    if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $datasetUuid)) {
        ob_end_clean();
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Invalid UUID format']);
        exit;
    }

    // Get dataset to verify access
    $user = getCurrentUser();
    $dataset = getDatasetByUuid($datasetUuid);
    
    if (!$dataset) {
        ob_end_clean();
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Dataset not found']);
        exit;
    }

    // Check if user has access to this dataset
    if ($dataset['user_id'] !== $user['id'] && 
        !in_array($user['id'], $dataset['shared_with'] ?? []) &&
        $dataset['team_id'] !== $user['team_id']) {
        ob_end_clean();
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'Access denied']);
        exit;
    }

    // Get directory paths from config
    $uploadDir = JOB_IN_DATA_DIR . '/' . $datasetUuid;
    $convertedDir = JOB_OUT_DATA_DIR . '/' . $datasetUuid;

    // Log directory paths for debugging
    error_log("Dataset files API - Upload dir: $uploadDir, exists: " . (is_dir($uploadDir) ? 'yes' : 'no'));
    error_log("Dataset files API - Converted dir: $convertedDir, exists: " . (is_dir($convertedDir) ? 'yes' : 'no'));

    // Scan both directories
    $uploadFiles = scanDirectory($uploadDir, 'upload');
    $convertedFiles = scanDirectory($convertedDir, 'converted');
    
    // Log scan results for debugging
    error_log("Dataset files API - Upload files count: " . count($uploadFiles));
    error_log("Dataset files API - Converted files count: " . count($convertedFiles));

    // Format response
    $response = [
        'success' => true,
        'dataset_uuid' => $datasetUuid,
        'directories' => [
            'upload' => [
                'path' => $uploadDir,
                'exists' => is_dir($uploadDir),
                'readable' => is_readable($uploadDir),
                'files' => $uploadFiles,
                'file_count' => count($uploadFiles)
            ],
            'converted' => [
                'path' => $convertedDir,
                'exists' => is_dir($convertedDir),
                'readable' => is_readable($convertedDir),
                'files' => $convertedFiles,
                'file_count' => count($convertedFiles)
            ]
        ]
    ];

    // Clean output buffer and send response
    ob_end_clean();
    echo json_encode($response);

} catch (Exception $e) {
    ob_end_clean();
    logMessage('ERROR', 'Failed to get dataset files', ['dataset_uuid' => $datasetUuid ?? 'unknown', 'error' => $e->getMessage()]);
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ]);
}
?>

