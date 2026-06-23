<?php
/**
 * Authenticated S3 browser embedded from the private portal (dataset-scoped).
 * URL: /portal/s3-embed.php?dataset=<uuid>&embed=1
 */

declare(strict_types=1);

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/dataset_s3_inspector.php';
require_once __DIR__ . '/includes/s3_inspector.php';

if (!is_file(__DIR__ . '/vendor/autoload.php')) {
    die('Run <code>composer install</code> in SC_Web (aws/aws-sdk-php required).');
}
require_once __DIR__ . '/vendor/autoload.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

$user = getCurrentUser();
if (!$user) {
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
    header('Location: ' . $loginPath);
    exit;
}

$userEmail = trim((string) ($user['email'] ?? $user['user_email'] ?? ''));
if ($userEmail === '') {
    http_response_code(403);
    echo 'Could not determine signed-in user.';
    exit;
}

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$portalHomeHref = $isLocal ? '/index.php' : '/portal/index.php';
$selfPath = $isLocal ? '/s3-embed.php' : '/portal/s3-embed.php';
$apiDl = $isLocal ? '/api/dataset-s3-download.php' : '/portal/api/dataset-s3-download.php';
$apiFolderDl = $isLocal ? '/api/dataset-s3-download-folder.php' : '/portal/api/dataset-s3-download-folder.php';
$embedMode = !empty($_GET['embed']);

$datasetId = trim((string) ($_GET['dataset'] ?? ''));
$bootstrapError = null;
$session = [];

if ($datasetId !== '') {
    try {
        $session = dataset_s3_bootstrap_session($datasetId, $userEmail);
    } catch (Throwable $e) {
        $bootstrapError = $e->getMessage();
    }
} else {
    $session = dataset_s3_get_session();
    if (s3_inspector_connected($session)) {
        $datasetId = (string) ($session['dataset_uuid'] ?? '');
    }
}

$connected = s3_inspector_connected($session) && $bootstrapError === null;
$list = null;

if ($connected) {
    $rel = s3_inspector_sanitize_rel((string) ($_GET['rel'] ?? ''));
    $session['rel'] = $rel;
    $_SESSION[DATASET_S3_SESS_KEY] = $session;

    $continuation = isset($_GET['continuation']) ? (string) $_GET['continuation'] : null;
    $list = s3_inspector_list_page($session, $continuation ?: null);
}

$pageTitle = 'Dataset S3 Browser';
$portalHomeLabel = 'Portal';
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
if ($queryBase === '?') {
    $queryBase = '?';
}

$browserShareUrl = $datasetId !== '' ? dataset_s3_embed_url($datasetId) : '';

require __DIR__ . '/includes/s3_inspector_embed_render.php';
