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
    private function makeRequest($endpoint, $method = 'GET', $data = null, $params = []) {
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
        } elseif ($method === 'DELETE') {
            curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
        }
        
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);
        
        if ($error) {
            throw new Exception("cURL error: " . $error);
        }
        
        $decoded_response = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new Exception("Invalid JSON response: " . json_last_error_msg());
        }
        
        if ($http_code >= 400) {
            $error_message = $decoded_response['error'] ?? 'Unknown error';
            throw new Exception("API error ($http_code): " . $error_message);
        }
        
        return $decoded_response;
    }
    
    /**
     * Health check
     */
    public function healthCheck() {
        try {
            $response = $this->makeRequest('/api/health');
            return $response['status'] === 'healthy';
        } catch (Exception $e) {
            error_log("SCLib health check failed: " . $e->getMessage());
            return false;
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
    public function getDatasetDetails($datasetId, $userId) {
        try {
            $response = $this->makeRequest("/api/dataset/$datasetId", 'GET', null, ['user_id' => $userId]);
            return $response['dataset'] ?? null;
        } catch (Exception $e) {
            error_log("Failed to get dataset details: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Get dataset status
     */
    public function getDatasetStatus($datasetId, $userId) {
        try {
            $response = $this->makeRequest("/api/dataset/$datasetId/status", 'GET', null, ['user_id' => $userId]);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to get dataset status: " . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
    
    /**
     * Delete dataset
     */
    public function deleteDataset($datasetId, $userId) {
        try {
            $response = $this->makeRequest("/api/dataset/$datasetId", 'DELETE', null, ['user_id' => $userId]);
            return $response;
        } catch (Exception $e) {
            error_log("Failed to delete dataset: " . $e->getMessage());
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
     * Get user profile
     */
    public function getUserProfile($userId) {
        try {
            $response = $this->makeRequest('/api/auth/user', 'GET', null, ['user_id' => $userId]);
            return $response['user'] ?? null;
        } catch (Exception $e) {
            error_log("Failed to get user profile: " . $e->getMessage());
            return null;
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
}

// Global SCLib client instance
$sclib_client = null;

function getSCLibClient() {
    global $sclib_client;
    if ($sclib_client === null) {
        // Get API URL from configuration
        $api_url = getenv('SCLIB_API_URL') ?: 'http://localhost:5001';
        $sclib_client = new SCLibClient($api_url);
    }
    return $sclib_client;
}

?>
