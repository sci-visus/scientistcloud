<?php
/**
 * Authenticated dataset S3 inspector — server-side credentials for portal users.
 */

declare(strict_types=1);

const DATASET_S3_SESS_KEY = 'portal_dataset_s3_inspector';

/**
 * @return array<string, mixed>
 */
function dataset_s3_get_session(): array
{
    return $_SESSION[DATASET_S3_SESS_KEY] ?? [];
}

/**
 * Fetch inspector session from SCLib for an authenticated user.
 *
 * @return array<string, mixed>
 */
function dataset_s3_fetch_inspector_config(string $datasetId, string $userEmail): array
{
    if (!function_exists('getSCLibClient')) {
        require_once __DIR__ . '/sclib_client.php';
    }

    $datasetId = trim($datasetId);
    $userEmail = trim($userEmail);
    if ($datasetId === '') {
        throw new InvalidArgumentException('Dataset identifier is required.');
    }
    if ($userEmail === '') {
        throw new InvalidArgumentException('User email is required.');
    }

    $sclib = getSCLibClient();
    $encoded = rawurlencode($datasetId);
    $response = $sclib->makeRequest(
        "/api/v1/datasets/{$encoded}/s3-inspector-config",
        'GET',
        null,
        ['user_email' => $userEmail]
    );

    if (empty($response['success']) || empty($response['session']) || !is_array($response['session'])) {
        $message = is_string($response['detail'] ?? null)
            ? $response['detail']
            : (is_string($response['error'] ?? null) ? $response['error'] : 'Could not load S3 configuration for this dataset');
        throw new RuntimeException($message);
    }

    return $response['session'];
}

/**
 * @return array<string, mixed>
 */
function dataset_s3_bootstrap_session(string $datasetId, string $userEmail): array
{
    if (!function_exists('s3_inspector_connected')) {
        require_once __DIR__ . '/s3_inspector.php';
    }

    $datasetId = trim($datasetId);
    $existing = dataset_s3_get_session();
    if (
        $datasetId !== ''
        && s3_inspector_connected($existing)
        && (string) ($existing['dataset_uuid'] ?? '') === $datasetId
    ) {
        return $existing;
    }

    $config = dataset_s3_fetch_inspector_config($datasetId, $userEmail);
    $session = [
        'dataset_uuid' => (string) ($config['dataset_uuid'] ?? $datasetId),
        'dataset_name' => (string) ($config['dataset_name'] ?? ''),
        'endpoint' => (string) ($config['endpoint'] ?? ''),
        'bucket' => (string) ($config['bucket'] ?? ''),
        'root_prefix' => s3_inspector_normalize_root_prefix((string) ($config['root_prefix'] ?? '')),
        'access_key' => (string) ($config['access_key'] ?? ''),
        'secret_key' => (string) ($config['secret_key'] ?? ''),
        'region' => (string) ($config['region'] ?? 'us-east-1'),
        'path_style' => !empty($config['path_style']),
        'download_enabled' => !empty($config['download_enabled']),
        'rel' => '',
    ];

    if (!s3_inspector_connected($session)) {
        throw new RuntimeException('S3 session is missing required connection fields.');
    }

    $_SESSION[DATASET_S3_SESS_KEY] = $session;
    return $session;
}

function dataset_s3_embed_url(string $datasetUuid): string
{
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $base = rtrim(SC_SERVER_URL, '/');
    $path = $isLocal ? '/s3-embed.php' : '/portal/s3-embed.php';
    return $base . $path . '?dataset=' . rawurlencode($datasetUuid);
}
