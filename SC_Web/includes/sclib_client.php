<?php
/**
 * SCLib API Client
 * Handles communication with SCLib API endpoints instead of direct MongoDB access
 */

class SCLibClient {
    private $api_base_url;
    private $timeout;
    
    public function __construct($api_base_url = 'http://localhost:5001', $timeout = 30) {
        $this->api_base_url = rtrim($api_base_url, '/');
        $this->timeout = $timeout;
    }
    
    /**
     * Make HTTP request to SCLib API
     */
    public function makeRequest($endpoint, $method = 'GET', $data = null, $params = []) {
        $url = $this->api_base_url . $endpoint;
        
        // Add query parameters
        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }
        
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $this->timeout);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'Accept: application/json'
        ]);
        
        if ($method === 'POST') {
            curl_setopt($ch, CURLOPT_POST, true);
            if ($data) {
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            }
        } elseif ($method === 'PUT') {
            curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
            if ($data) {
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            }
        } elseif ($method === 'DELETE') {
            curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
        }
        
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curl_error = curl_error($ch);
        $curl_errno = curl_errno($ch);
        curl_close($ch);
        
        // Log request details for debugging
        error_log("API Request: $method $url");
        error_log("HTTP Code: $http_code");
        if ($curl_error) {
            error_log("cURL Error: $curl_error (errno: $curl_errno)");
        }
        if ($response) {
            error_log("Response (first 500 chars): " . substr($response, 0, 500));
        }
        
        if ($curl_error) {
            throw new Exception("cURL error: $curl_error");
        }
        
        // Handle empty response
        if (empty($response)) {
            throw new Exception("Empty response from API (HTTP $http_code)");
        }
        
        $decoded_response = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            error_log("JSON decode error: " . json_last_error_msg());
            error_log("Raw response: " . $response);
            throw new Exception("Invalid JSON response: " . json_last_error_msg() . " (HTTP $http_code)");
        }
        
        if ($http_code >= 400) {
            $error_message = $decoded_response['detail'] ?? $decoded_response['error'] ?? $decoded_response['message'] ?? 'Unknown error';
            throw new Exception("API error ($http_code): $error_message");
        }
        
        return $decoded_response;
    }
    
    /**
     * Health check
     */
    public function healthCheck() {
        try {
            // Try /health endpoint first (FastAPI standard)
            $response = $this->makeRequest('/health');
            return isset($response['status']) && $response['status'] === 'healthy';
        } catch (Exception $e) {
            error_log("SCLib health check failed: " . $e->getMessage());
            // Try alternative endpoint
            try {
                $response = $this->makeRequest('/api/health');
                return isset($response['status']) && $response['status'] === 'healthy';
            } catch (Exception $e2) {
                error_log("SCLib health check (alternative) failed: " . $e2->getMessage());
                return false;
            }
        }
    }
    
    /**
     * Get user's datasets
     */
    public function getUserDatasets($userId) {
        try {
            $response = $this->makeRequest('/api/datasets', 'GET', null, ['user_id' => $userId]);
            return $response['datasets'] ?? [];
        } catch (Exception $e) {
            error_log("Failed to get user datasets: " . $e->getMessage());
            return [];
        }
    }
    
    /**
     * Get dataset details
     */
    public function getDatasetDetails($datasetId, $userId = null) {
        try {
            // Use the correct FastAPI endpoint: /api/v1/datasets/{identifier}
            // Pass user_email as query parameter (FastAPI expects user_email, not user_id)
            $userEmail = null;
            if (function_exists('getCurrentUser')) {
                $user = getCurrentUser();
                $userEmail = $user['email'] ?? null;
            }
            
            $params = [];
            if ($userEmail) {
                $params['user_email'] = $userEmail;
            }
            
            $response = $this->makeRequest("/api/v1/datasets/$datasetId", 'GET', null, $params);
            return $response['dataset'] ?? null;
        } catch (Exception $e) {
            error_log("Failed to get dataset details: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Get dataset status
     */
    public function getDatasetStatus($datasetId, $userId = null) {
        try {
            // Use the correct FastAPI endpoint: /api/v1/datasets/{identifier}/status
            $userEmail = null;
            if (function_exists('getCurrentUser')) {
                $user = getCurrentUser();
                $userEmail = $user['email'] ?? null;
            }
            
            $params = [];
            if ($userEmail) {
                $params['user_email'] = $userEmail;
            }
            
            $response = $this->makeRequest("/api/v1/datasets/$datasetId/status", 'GET', null, $params);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to get dataset status: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Delete dataset
     */
    public function deleteDataset($datasetId, $userEmail) {
        try {
            // Use the SCLib Dataset Management API endpoint: DELETE /api/v1/datasets/{identifier}
            $params = [];
            if ($userEmail) {
                $params['user_email'] = $userEmail;
            }
            
            $response = $this->makeRequest("/api/v1/datasets/$datasetId", 'DELETE', null, $params);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to delete dataset: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Update dataset
     */
    public function updateDataset($datasetId, $updateData, $userEmail = null) {
        try {
            $params = [];
            if ($userEmail) {
                $params['user_email'] = $userEmail;
            }
            
            // Use PUT method for updates
            $response = $this->makeRequest("/api/v1/datasets/$datasetId", 'PUT', $updateData, $params);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to update dataset: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Share dataset
     */
    public function shareDataset($datasetId, $userId, $sharedWith) {
        try {
            $data = ['shared_with' => $sharedWith];
            $response = $this->makeRequest("/api/dataset/$datasetId/share", 'POST', $data, ['user_id' => $userId]);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to share dataset: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Get user profile by email - uses existing SCLib Auth service
     * Note: email is the primary identifier for authentication
     */
    public function getUserProfile($email) {
        try {
            // Use the user-by-email endpoint since email is primary identifier
            $response = $this->makeRequest('/api/auth/user-by-email', 'GET', null, ['email' => $email]);
            return $response['user'] ?? null;
        } catch (Exception $e) {
            error_log("Failed to get user profile: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Get user profile by email
     */
    public function getUserProfileByEmail($email) {
        try {
            $response = $this->makeRequest('/api/auth/user-by-email', 'GET', null, ['email' => $email]);
            return $response['user'] ?? null;
        } catch (Exception $e) {
            error_log("Failed to get user profile by email: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Create new user
     */
    public function createUser($userData) {
        try {
            $url = $this->api_base_url . '/api/auth/create-user';
            error_log("Creating user at: $url");
            error_log("User data: " . json_encode($userData));
            
            $response = $this->makeRequest('/api/auth/create-user', 'POST', $userData);
            
            error_log("Create user response: " . json_encode($response));
            
            if (isset($response['success']) && $response['success']) {
                return [
                    'success' => true,
                    'user_id' => $response['user_id'] ?? $response['user']['id'] ?? null
                ];
            }
            return ['success' => false, 'error' => $response['error'] ?? 'Unknown error'];
        } catch (Exception $e) {
            error_log("Failed to create user: " . $e->getMessage());
            error_log("API base URL: " . $this->api_base_url);
            error_log("Full URL would be: " . $this->api_base_url . '/api/auth/create-user');
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Update user's last login time - uses email as identifier
     */
    public function updateUserLastLogin($email) {
        try {
            // URL encode email to handle special characters
            $encodedEmail = urlencode($email);
            $response = $this->makeRequest("/api/auth/user/$encodedEmail/update-last-login", 'POST');
            return $response['success'] ?? false;
        } catch (Exception $e) {
            error_log("Failed to update user last login: " . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Validate authentication token
     */
    public function validateAuthToken($token) {
        try {
            $data = ['token' => $token];
            $response = $this->makeRequest('/api/auth/validate', 'POST', $data);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to validate auth token: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Authenticate user login
     */
    public function authenticateUser($email, $password) {
        try {
            $data = ['email' => $email, 'password' => $password];
            $response = $this->makeRequest('/api/auth/login', 'POST', $data);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to authenticate user: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Share dataset with user
     */
    public function shareDatasetWithUser($datasetUuid, $userEmail, $ownerEmail, $googleDriveLink = '') {
        try {
            $data = [
                'dataset_uuid' => $datasetUuid,
                'user_email' => $userEmail,
                'google_drive_link' => $googleDriveLink
            ];
            $response = $this->makeRequest('/api/v1/share/user', 'POST', $data, ['owner_email' => $ownerEmail]);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to share dataset with user: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Share dataset with team
     */
    public function shareDatasetWithTeam($datasetUuid, $teamName, $ownerEmail, $teamUuid = null, $googleDriveLink = '') {
        try {
            $data = [
                'dataset_uuid' => $datasetUuid,
                'team_name' => $teamName,
                'google_drive_link' => $googleDriveLink
            ];
            if ($teamUuid) {
                $data['team_uuid'] = $teamUuid;
            }
            $response = $this->makeRequest('/api/v1/share/team', 'POST', $data, ['owner_email' => $ownerEmail]);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to share dataset with team: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Get user teams
     */
    public function getUserTeams($userEmail) {
        try {
            $response = $this->makeRequest('/api/v1/teams/by-user', 'GET', null, ['user_email' => $userEmail]);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to get user teams: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage(), 'teams' => []];
        }
    }
    
    /**
     * Create a new team
     */
    public function createTeam($teamName, $ownerEmail, $emails = []) {
        try {
            $data = [
                'team_name' => $teamName,
                'emails' => $emails
            ];
            $response = $this->makeRequest('/api/v1/teams/create', 'POST', $data, ['owner_email' => $ownerEmail]);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to create team: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
}

// Global SCLib client instance
$sclib_client = null;

function getSCLibClient() {
    global $sclib_client;
    if ($sclib_client === null) {
        // Get API URL from configuration
        // Dataset management endpoints use SCLIB_API_URL (port 5001) or SCLIB_DATASET_URL
        // Auth endpoints use SCLIB_AUTH_URL (port 8001)
        $api_url = getenv('SCLIB_DATASET_URL') ?: getenv('SCLIB_API_URL') ?: getenv('EXISTING_AUTH_URL') ?: 'http://localhost:5001';
        $sclib_client = new SCLibClient($api_url);
    }
    return $sclib_client;
}

/**
 * Get SCLib client for sharing and team endpoints (port 5003)
 */
function getSCLibSharingClient() {
    static $sharing_client = null;
    if ($sharing_client === null) {
        // Sharing endpoints use SCLIB_SHARING_URL (port 5003)
        $sharing_url = getenv('SCLIB_SHARING_URL') ?: 'http://localhost:5003';
        $sharing_client = new SCLibClient($sharing_url);
    }
    return $sharing_client;
}

/**
 * Get SCLib client for authentication endpoints (port 8001)
 */
function getSCLibAuthClient() {
    static $auth_client = null;
    if ($auth_client === null) {
        // Auth endpoints use SCLIB_AUTH_URL (port 8001)
        $auth_url = getenv('SCLIB_AUTH_URL') ?: getenv('EXISTING_AUTH_URL') ?: 'http://localhost:8001';
        $auth_client = new SCLibClient($auth_url);
    }
    return $auth_client;
}

?>
