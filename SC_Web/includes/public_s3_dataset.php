<?php
/**
 * Public dataset S3 inspector — server-side credentials for is_public datasets.
 */

declare(strict_types=1);

const PUBLIC_S3_SESS_KEY = 'portal_public_s3_inspector';

/**
 * @return array<string, mixed>
 */
function public_s3_get_session(): array
{
    return $_SESSION[PUBLIC_S3_SESS_KEY] ?? [];
}

function public_s3_clear_session(): void
{
    unset($_SESSION[PUBLIC_S3_SESS_KEY]);
}

/**
 * Fetch inspector session from SCLib (includes credentials; server-side only).
 *
 * @return array<string, mixed>
 */
function public_s3_fetch_inspector_config(string $datasetId): array
{
    if (!function_exists('getSCLibClient')) {
        require_once __DIR__ . '/sclib_client.php';
    }

    $datasetId = trim($datasetId);
    if ($datasetId === '') {
        throw new InvalidArgumentException('Dataset identifier is required.');
    }

    $sclib = getSCLibClient();
    $encoded = rawurlencode($datasetId);
    $response = $sclib->makeRequest("/api/v1/datasets/public/{$encoded}/s3-inspector-config", 'GET');

    if (empty($response['success']) || empty($response['session']) || !is_array($response['session'])) {
        $message = is_string($response['detail'] ?? null)
            ? $response['detail']
            : (is_string($response['error'] ?? null) ? $response['error'] : 'Could not load public S3 configuration');
        throw new RuntimeException($message);
    }

    return $response['session'];
}

/**
 * Bootstrap or refresh the public S3 inspector PHP session for a dataset.
 *
 * @return array<string, mixed>
 */
function public_s3_bootstrap_session(string $datasetId): array
{
    if (!function_exists('s3_inspector_connected')) {
        require_once __DIR__ . '/s3_inspector.php';
    }

    $datasetId = trim($datasetId);
    $existing = public_s3_get_session();
    if (
        $datasetId !== ''
        && s3_inspector_connected($existing)
        && (string) ($existing['dataset_uuid'] ?? '') === $datasetId
    ) {
        return $existing;
    }

    $config = public_s3_fetch_inspector_config($datasetId);
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
        throw new RuntimeException('Public S3 session is missing required connection fields.');
    }

    $_SESSION[PUBLIC_S3_SESS_KEY] = $session;
    return $session;
}

/**
 * @return array{0: bool, 1: string}
 */
function public_s3_dataset_is_remote_linked(array $dataset): array
{
    $link = trim((string) ($dataset['google_drive_link'] ?? $dataset['download_url'] ?? $dataset['viewer_url'] ?? ''));
    if ($link === '') {
        return [false, ''];
    }
    if (stripos($link, 'google.com') !== false) {
        return [false, $link];
    }
    if (preg_match('#^(s3|https?)://#i', $link)) {
        return [true, $link];
    }
    return [false, $link];
}

function public_s3_portal_share_url(string $datasetUuid): string
{
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $base = rtrim(SC_SERVER_URL, '/');
    $path = $isLocal ? '/public/index.php' : '/portal/public/index.php';
    return $base . $path . '?dataset=' . rawurlencode($datasetUuid);
}

function public_s3_browser_share_url(string $datasetUuid): string
{
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $base = rtrim(SC_SERVER_URL, '/');
    $path = $isLocal ? '/public/s3.php' : '/portal/public/s3.php';
    return $base . $path . '?dataset=' . rawurlencode($datasetUuid);
}
