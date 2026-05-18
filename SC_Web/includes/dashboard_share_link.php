<?php
/**
 * Build dashboard URLs for copy/share with full remote credentials when stored on the dataset.
 * Display APIs use sc_redact_dataset_urls_for_client(); this module uses raw Mongo/SCLib fields.
 */

require_once(__DIR__ . '/dashboard_manager.php');

/**
 * @param string $value
 */
function sc_url_credential_is_placeholder($value): bool
{
    $v = trim((string)$value);
    if ($v === '') {
        return true;
    }
    if ($v === '...') {
        return true;
    }
    return (bool) preg_match('/^\.{2,}$/', $v);
}

/**
 * @param array<string,mixed> $dataset
 * @return array{0: string, 1: string}
 */
function sc_extract_s3_credentials_from_dataset(array $dataset): array
{
    $access = trim((string)($dataset['s3_access_key_id'] ?? $dataset['accesskey'] ?? ''));
    $secret = trim((string)($dataset['s3_secret_access_key'] ?? $dataset['secretkey'] ?? ''));
    if (sc_url_credential_is_placeholder($access)) {
        $access = '';
    }
    if (sc_url_credential_is_placeholder($secret)) {
        $secret = '';
    }
    return [$access, $secret];
}

/**
 * Inject or replace gateway query credentials on an https URL.
 */
function sc_apply_gateway_credentials_to_url(string $url, string $accessKey, string $secretKey): string
{
    $url = trim($url);
    $accessKey = trim($accessKey);
    $secretKey = trim($secretKey);
    if ($url === '' || $accessKey === '' || $secretKey === '') {
        return $url;
    }
    if (!preg_match('#^https?://#i', $url)) {
        return $url;
    }

    $parts = parse_url($url);
    if ($parts === false) {
        return $url;
    }

    $query = [];
    if (!empty($parts['query'])) {
        parse_str($parts['query'], $query);
    }

    foreach (['access_key', 'access_key_id', 'secret_key', 'secret_access_key'] as $key) {
        if (!isset($query[$key]) || sc_url_credential_is_placeholder((string)$query[$key])) {
            unset($query[$key]);
        }
    }
    $query['access_key'] = $accessKey;
    $query['secret_key'] = $secretKey;

    $scheme = $parts['scheme'] ?? 'https';
    $host = $parts['host'] ?? '';
    $port = isset($parts['port']) ? ':' . $parts['port'] : '';
    $userinfo = isset($parts['user']) ? $parts['user'] . (isset($parts['pass']) ? ':' . $parts['pass'] : '') . '@' : '';
    $path = $parts['path'] ?? '';
    $fragment = isset($parts['fragment']) ? '#' . $parts['fragment'] : '';
    $newQuery = http_build_query($query, '', '&', PHP_QUERY_RFC3986);

    return $scheme . '://' . $userinfo . $host . $port . $path
        . ($newQuery !== '' ? '?' . $newQuery : '')
        . $fragment;
}

/**
 * @param array<string,mixed> $dataset
 */
function sc_pick_strain_json_remote_link(array $dataset): string
{
    $fields = ['viewer_url', 'download_url', 'google_drive_link', 'source_path'];
    foreach ($fields as $field) {
        $u = trim((string)($dataset[$field] ?? ''));
        if ($u === '') {
            continue;
        }
        $low = strtolower($u);
        if (
            str_ends_with($low, '.json')
            || str_contains($low, '.json?')
            || str_starts_with($low, 's3://')
            || str_starts_with($low, 'http://')
            || str_starts_with($low, 'https://')
        ) {
            return $u;
        }
    }
    return '';
}

/**
 * Remote strain JSON URL with real gateway credentials when stored on the dataset document.
 *
 * @param array<string,mixed> $dataset
 */
function sc_resolve_strain_json_remote_link(array $dataset): string
{
    $link = sc_pick_strain_json_remote_link($dataset);
    if ($link === '') {
        return '';
    }

    [$accessKey, $secretKey] = sc_extract_s3_credentials_from_dataset($dataset);
    if ($accessKey === '' || $secretKey === '') {
        return $link;
    }

    $low = strtolower($link);
    if (str_starts_with($low, 'http://') || str_starts_with($low, 'https://')) {
        return sc_apply_gateway_credentials_to_url($link, $accessKey, $secretKey);
    }

    return $link;
}

/**
 * @param array<string,mixed> $dataset
 */
function sc_dataset_is_remote_linked(array $dataset): bool
{
    $explicit = strtolower(trim((string)($dataset['server'] ?? ''))) === 'true';
    if ($explicit) {
        return true;
    }
    $link = trim((string)($dataset['google_drive_link'] ?? $dataset['download_url'] ?? $dataset['viewer_url'] ?? ''));
    if ($link === '') {
        return false;
    }
    return (bool) preg_match('#^(s3|https?)://#i', $link);
}

/**
 * @param array<string,mixed> $dataset
 */
function sc_resolve_dashboard_connection(array $dataset): array
{
    $link = trim((string)($dataset['google_drive_link'] ?? $dataset['download_url'] ?? $dataset['viewer_url'] ?? ''));
    $sensor = strtoupper(trim((string)($dataset['sensor'] ?? '')));
    $isRemote = sc_dataset_is_remote_linked($dataset);
    $datasetServer = $isRemote ? 'true' : 'false';
    $uuid = trim((string)($dataset['uuid'] ?? $dataset['id'] ?? ''));
    if ($sensor === 'IDX' && $link !== '' && preg_match('#^https?://#i', $link) && stripos($link, 'mod_visus') !== false) {
        $uuid = $link;
    }
    return [
        'dataset_uuid' => $uuid,
        'dataset_server' => $datasetServer,
        'link' => $link,
    ];
}

/**
 * @param array<string,mixed> $dataset
 */
function sc_dataset_is_ornl_chess_strain(array $dataset): bool
{
    $norm = strtoupper(preg_replace('/\s+/', '_', trim((string)($dataset['sensor'] ?? ''))));
    return $norm === 'ORNL_CHESS_STRAIN';
}

/**
 * @return array<string,mixed>|null
 */
function sc_find_dashboard_config(string $dashboardType): ?array
{
    $normalized = normalizeDashboardType($dashboardType) ?? trim($dashboardType);
    if ($normalized === '') {
        return null;
    }
    foreach (getAllDashboards() as $dash) {
        $id = (string)($dash['id'] ?? '');
        if ($id === $normalized || strcasecmp($id, $normalized) === 0) {
            return $dash;
        }
    }
    return null;
}

/**
 * Build an absolute dashboard URL (may include gateway credentials in query params).
 *
 * @param array<string,mixed> $dataset Dataset from getDatasetForDashboardLink().
 */
function sc_build_dashboard_share_url(array $dataset, string $dashboardType, ?string $origin = null): string
{
    if (sc_dataset_is_ornl_chess_strain($dataset)) {
        $dashboardType = 'ORNL_CHESS_strain';
    }

    $dash = sc_find_dashboard_config($dashboardType);
    $urlTemplate = null;
    if ($dash) {
        $urlTemplate = $dash['url_template'] ?? null;
        if (!$urlTemplate && !empty($dash['nginx_path'])) {
            $urlTemplate = rtrim((string)$dash['nginx_path'], '/') . '/?uuid={uuid}&server={server}&name={name}';
        }
    }
    if (!$urlTemplate) {
        $pathId = preg_replace('/[^a-zA-Z0-9_]/', '', $dashboardType) ?: 'OpenVisusSlice';
        $urlTemplate = '/dashboard/' . $pathId . '/?uuid={uuid}&server={server}&name={name}';
    }

    $conn = sc_resolve_dashboard_connection($dataset);
    $name = (string)($dataset['name'] ?? '');

    $path = str_replace(
        ['{uuid}', '{server}', '{name}'],
        [rawurlencode($conn['dataset_uuid']), rawurlencode($conn['dataset_server']), rawurlencode($name)],
        $urlTemplate
    );

    $dashId = strtolower((string)($dash['id'] ?? $dashboardType));
    if ($dashId === 'ornl_chess_strain' || sc_dataset_is_ornl_chess_strain($dataset)) {
        $strainLink = sc_resolve_strain_json_remote_link($dataset);
        if ($strainLink !== '') {
            $low = strtolower(trim($strainLink));
            if (str_starts_with($low, 'http://') || str_starts_with($low, 'https://')) {
                $path .= (str_contains($path, '?') ? '&' : '?') . 'strain_json_url=' . rawurlencode($strainLink);
            } else {
                $path .= (str_contains($path, '?') ? '&' : '?') . 'strain_json_path=' . rawurlencode($strainLink);
            }
        }
    }

    if (!str_starts_with($path, '/')) {
        return $path;
    }

    if ($origin === null || $origin === '') {
        $scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
        $host = $_SERVER['HTTP_HOST'] ?? 'localhost';
        $origin = $scheme . '://' . $host;
    }

    return rtrim($origin, '/') . $path;
}
