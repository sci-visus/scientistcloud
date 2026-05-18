<?php
/**
 * Auth0 Management API helpers (verification email resend, user lookup).
 */

function auth0_management_token(): ?string
{
    $domain = getenv('AUTH0_DOMAIN') ?: (defined('AUTH0_DOMAIN') ? AUTH0_DOMAIN : null);
    $clientId = getenv('AUTH0_MANAGEMENT_CLIENT_ID');
    $clientSecret = getenv('AUTH0_MANAGEMENT_CLIENT_SECRET');

    if (!$domain || !$clientId || !$clientSecret) {
        error_log('Auth0 Management API credentials not configured');
        return null;
    }

    $url = "https://{$domain}/oauth/token";
    $payload = json_encode([
        'client_id' => $clientId,
        'client_secret' => $clientSecret,
        'audience' => "https://{$domain}/api/v2/",
        'grant_type' => 'client_credentials',
    ]);

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
    ]);
    $response = curl_exec($ch);
    $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode !== 200 || !$response) {
        error_log("Auth0 Management token failed HTTP {$httpCode}: {$response}");
        return null;
    }

    $data = json_decode($response, true);
    return $data['access_token'] ?? null;
}

function auth0_user_id_by_email(string $email, string $managementToken): ?string
{
    $domain = getenv('AUTH0_DOMAIN') ?: AUTH0_DOMAIN;
    $url = 'https://' . $domain . '/api/v2/users-by-email?email=' . urlencode($email);

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $managementToken],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
    ]);
    $response = curl_exec($ch);
    $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode !== 200 || !$response) {
        error_log("Auth0 users-by-email failed HTTP {$httpCode} for {$email}");
        return null;
    }

    $users = json_decode($response, true);
    if (!is_array($users) || $users === []) {
        return null;
    }

    foreach ($users as $user) {
        if (!empty($user['user_id']) && str_starts_with($user['user_id'], 'auth0|')) {
            return $user['user_id'];
        }
    }

    return $users[0]['user_id'] ?? null;
}

function auth0_resend_verification_email(string $email): array
{
    $token = auth0_management_token();
    if (!$token) {
        return ['ok' => false, 'message' => 'Email service is not configured on this server.'];
    }

    $userId = auth0_user_id_by_email($email, $token);
    if (!$userId) {
        return ['ok' => false, 'message' => 'No account found for that email. Sign up first or check the address.'];
    }

    $domain = getenv('AUTH0_DOMAIN') ?: AUTH0_DOMAIN;
    $url = "https://{$domain}/api/v2/jobs/verification-email";
    $payload = json_encode(['user_id' => $userId]);

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $token,
        ],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
    ]);
    $response = curl_exec($ch);
    $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode >= 200 && $httpCode < 300) {
        return ['ok' => true, 'message' => 'Verification email sent. Check your inbox and spam folder.'];
    }

    error_log("Auth0 verification-email job failed HTTP {$httpCode}: {$response}");
    return ['ok' => false, 'message' => 'Could not send verification email. Try again in a few minutes.'];
}
