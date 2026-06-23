<?php
/**
 * Public S3 browser for is_public datasets (server-side credentials).
 * URL: /portal/public/s3.php?dataset=<uuid>
 */

declare(strict_types=1);

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../includes/public_s3_dataset.php';
require_once __DIR__ . '/../includes/s3_inspector.php';

if (!is_file(__DIR__ . '/../vendor/autoload.php')) {
    die('Run <code>composer install</code> in SC_Web (aws/aws-sdk-php required).');
}
require_once __DIR__ . '/../vendor/autoload.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$portalHomeHref = $isLocal ? '/public/index.php' : '/portal/public/index.php';
$selfPath = $isLocal ? '/public/s3.php' : '/portal/public/s3.php';
$apiDl = $isLocal ? '/api/public-s3-download.php' : '/portal/api/public-s3-download.php';
$apiFolderDl = $isLocal ? '/api/public-s3-download-folder.php' : '/portal/api/public-s3-download-folder.php';
$embedMode = !empty($_GET['embed']);

$datasetId = trim((string) ($_GET['dataset'] ?? ''));
$bootstrapError = null;
$session = [];

if ($datasetId !== '') {
    try {
        $session = public_s3_bootstrap_session($datasetId);
    } catch (Throwable $e) {
        $bootstrapError = $e->getMessage();
    }
} else {
    $session = public_s3_get_session();
    if (s3_inspector_connected($session)) {
        $datasetId = (string) ($session['dataset_uuid'] ?? '');
    }
}

$connected = s3_inspector_connected($session) && $bootstrapError === null;
$list = null;

if ($connected) {
    $rel = s3_inspector_sanitize_rel((string) ($_GET['rel'] ?? ''));
    $session['rel'] = $rel;
    $_SESSION[PUBLIC_S3_SESS_KEY] = $session;

    $continuation = isset($_GET['continuation']) ? (string) $_GET['continuation'] : null;
    $list = s3_inspector_list_page($session, $continuation ?: null);
}

$pageTitle = 'Public Dataset Storage';
$portalHomeLabel = 'Public Portal';
$shareMaxSeconds = defined('S3_SHARE_LINK_MAX_SECONDS') ? (int) S3_SHARE_LINK_MAX_SECONDS : 604800;
if ($shareMaxSeconds < 60) {
    $shareMaxSeconds = 60;
}
$shareDurationOptions = [
    900 => '15m',
    3600 => '1h',
    86400 => '24h',
    604800 => '7d',
];
$shareDurationOptions = array_filter(
    $shareDurationOptions,
    static fn (int $seconds): bool => $seconds <= $shareMaxSeconds,
    ARRAY_FILTER_USE_KEY
);
if ($shareDurationOptions === []) {
    $shareDurationOptions = [$shareMaxSeconds => (string) $shareMaxSeconds . 's'];
}
$defaultShareSeconds = 3600;
if ($defaultShareSeconds > $shareMaxSeconds) {
    $keys = array_keys($shareDurationOptions);
    $defaultShareSeconds = (int) end($keys);
}

$queryBase = '?';
if ($datasetId !== '') {
    $queryBase .= 'dataset=' . rawurlencode($datasetId);
}
if ($embedMode) {
    $queryBase .= ($queryBase === '?' ? '' : '&') . 'embed=1';
}

$browserShareUrl = $datasetId !== '' ? public_s3_browser_share_url($datasetId) : '';
$showStorageMetadata = false;

require __DIR__ . '/../includes/s3_inspector_embed_render.php';
