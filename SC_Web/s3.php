<?php
/**
 * S3-compatible bucket browser.
 * URL: /portal/s3.php
 */

declare(strict_types=1);

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/s3_inspector.php';

if (!is_file(__DIR__ . '/vendor/autoload.php')) {
    die('Run <code>composer install</code> in SC_Web (aws/aws-sdk-php required).');
}
require_once __DIR__ . '/vendor/autoload.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

$requirePortalAuth = defined('S3_REQUIRE_PORTAL_AUTH') && S3_REQUIRE_PORTAL_AUTH;
if ($requirePortalAuth) {
    $user = getCurrentUser();
    if (!$user) {
        $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
        $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
        header('Location: ' . $loginPath);
        exit;
    }
}

const S3_SESS_KEY = 'portal_s3_inspector';

/** @return array<string, mixed> */
function s3_sess(): array
{
    return $_SESSION[S3_SESS_KEY] ?? [];
}

/** @param array<string, mixed> $data */
function s3_sess_save(array $data): void
{
    $_SESSION[S3_SESS_KEY] = $data;
}

function s3_sess_clear(): void
{
    unset($_SESSION[S3_SESS_KEY]);
}

function s3_public_object_url(array $session, string $key): string
{
    $endpoint = rtrim((string) ($session['endpoint'] ?? ''), '/');
    $bucket = trim((string) ($session['bucket'] ?? ''));
    $pathStyle = !empty($session['path_style']);

    $encodedKey = implode('/', array_map('rawurlencode', array_filter(explode('/', ltrim($key, '/')), static function ($seg) {
        return $seg !== '';
    })));

    $parsed = parse_url($endpoint);
    if ($parsed === false || empty($parsed['scheme']) || empty($parsed['host'])) {
        return $endpoint . '/' . rawurlencode($bucket) . '/' . $encodedKey;
    }

    $scheme = $parsed['scheme'];
    $host = $parsed['host'];
    $port = isset($parsed['port']) ? ':' . $parsed['port'] : '';
    $basePath = isset($parsed['path']) ? rtrim($parsed['path'], '/') : '';

    if ($pathStyle) {
        return $scheme . '://' . $host . $port . $basePath . '/' . rawurlencode($bucket) . '/' . $encodedKey;
    }

    return $scheme . '://' . $bucket . '.' . $host . $port . $basePath . '/' . $encodedKey;
}

function s3_dataset_source_link(array $session, string $key): string
{
    $bucket = trim((string) ($session['bucket'] ?? ''));
    $normalizedKey = ltrim($key, '/');
    if ($bucket === '' || $normalizedKey === '') {
        return '';
    }
    return 's3://' . $bucket . '/' . $normalizedKey;
}

function s3_format_duration(int $seconds): string
{
    if ($seconds % 86400 === 0) {
        return (string) ($seconds / 86400) . 'd';
    }
    if ($seconds % 3600 === 0) {
        return (string) ($seconds / 3600) . 'h';
    }
    if ($seconds % 60 === 0) {
        return (string) ($seconds / 60) . 'm';
    }
    return (string) $seconds . 's';
}

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$portalHome = $isLocal ? '/index.php' : '/portal/index.php';
$selfPath = $isLocal ? '/s3.php' : '/portal/s3.php';
$debugLog = $_SESSION['s3_debug_log'] ?? [];
unset($_SESSION['s3_debug_log']);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    if ($action === 'disconnect') {
        s3_sess_clear();
        header('Location: ' . $selfPath);
        exit;
    }
    if ($action === 'connect') {
        $endpoint = trim((string) ($_POST['endpoint_url'] ?? ''));
        $bucket = trim((string) ($_POST['bucket_name'] ?? ''));
        $rootPrefix = s3_inspector_normalize_root_prefix((string) ($_POST['prefix'] ?? ''));
        $access = trim((string) ($_POST['access_key'] ?? ''));
        $secret = trim((string) ($_POST['secret_key'] ?? ''));
        $region = trim((string) ($_POST['region'] ?? 'us-east-1')) ?: 'us-east-1';
        $pathStyle = isset($_POST['path_style']);

        $err = null;
        if ($endpoint === '' || $bucket === '' || $access === '' || $secret === '') {
            $err = 'Endpoint, bucket, access key, and secret key are required.';
        }

        if ($err === null) {
            $probe = [
                'endpoint' => $endpoint,
                'bucket' => $bucket,
                'root_prefix' => $rootPrefix,
                'rel' => '',
                'access_key' => $access,
                'secret_key' => $secret,
                'region' => $region,
                'path_style' => $pathStyle,
            ];
            $debugLog = [];
            $debugLog[] = '[connect] attempting connection test';
            $debugLog[] = sprintf(
                '[connect] endpoint=%s bucket=%s prefix=%s region=%s path_style=%s',
                $endpoint,
                $bucket,
                $rootPrefix,
                $region,
                $pathStyle ? 'true' : 'false'
            );
            $list = s3_inspector_list_page($probe, null);
            if (!empty($list['debug']) && is_array($list['debug'])) {
                $debugLog = array_merge($debugLog, $list['debug']);
            }
            if ($list['error'] !== null) {
                $err = 'Could not list bucket: ' . $list['error'];
                $debugLog[] = '[connect] failed';
            } else {
                $debugLog[] = '[connect] success';
                s3_sess_save($probe);
                $_SESSION['s3_debug_log'] = $debugLog;
                header('Location: ' . $selfPath);
                exit;
            }
        }
        // fall through to show form with error
        $_SESSION['s3_connect_error'] = $err;
        $_SESSION['s3_debug_log'] = $debugLog;
        header('Location: ' . $selfPath . '?connect_error=1');
        exit;
    }
}

$connectError = null;
if (!empty($_GET['connect_error']) && isset($_SESSION['s3_connect_error'])) {
    $connectError = $_SESSION['s3_connect_error'];
    unset($_SESSION['s3_connect_error']);
}

$session = s3_sess();
$connected = s3_inspector_connected($session);

if ($connected) {
    $rel = s3_inspector_sanitize_rel((string) ($_GET['rel'] ?? ''));
    $session['rel'] = $rel;
    s3_sess_save($session);

    $continuation = isset($_GET['continuation']) ? (string) $_GET['continuation'] : null;
    $list = s3_inspector_list_page($session, $continuation ?: null);
    if (!empty($list['debug']) && is_array($list['debug'])) {
        $debugLog = array_merge($debugLog, $list['debug']);
    }
} else {
    $list = null;
}

$pageTitle = 'Inspect S3';
$shareMaxSeconds = defined('S3_SHARE_LINK_MAX_SECONDS') ? (int) S3_SHARE_LINK_MAX_SECONDS : 604800;
if ($shareMaxSeconds < 60) {
    $shareMaxSeconds = 60;
}
$showPublicUrlButton = defined('S3_ENABLE_PUBLIC_URL_BUTTON') && S3_ENABLE_PUBLIC_URL_BUTTON;
$defaultBucket = defined('S3_DEFAULT_BUCKET') ? (string) S3_DEFAULT_BUCKET : '';
$defaultPrefix = defined('S3_DEFAULT_PREFIX') ? (string) S3_DEFAULT_PREFIX : '';
$defaultEndpoint = defined('S3_DEFAULT_ENDPOINT') ? (string) S3_DEFAULT_ENDPOINT : '';
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
    $shareDurationOptions = [$shareMaxSeconds => s3_format_duration($shareMaxSeconds)];
}
$defaultShareSeconds = 3600;
if ($defaultShareSeconds > $shareMaxSeconds) {
    $keys = array_keys($shareDurationOptions);
    $defaultShareSeconds = (int) end($keys);
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?php echo htmlspecialchars($pageTitle); ?> — ScientistCloud</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <style>
    :root {
      --sc-primary: #1f3c88;
      --sc-accent: #2f7de1;
      --sc-soft: #eaf2ff;
      --sc-border: #c9daf8;
    }
    body { padding: 1.25rem; background: #f7faff; color: #1b2b52; }
    .breadcrumb { background: var(--bs-secondary-bg); }
    code.key { font-size: 0.85em; word-break: break-all; }
    .sc-title {
      color: var(--sc-primary);
      font-weight: 700;
      display: inline-flex;
      align-items: center;
    }
    .sc-logo {
      height: 100px;
      width: 100px;
      object-fit: contain;
      margin-right: 8px;
    }
    .card {
      border-color: var(--sc-border);
    }
    .card-header {
      background: var(--sc-soft);
      color: var(--sc-primary);
      border-bottom-color: var(--sc-border);
    }
    .btn-primary {
      background-color: var(--sc-primary);
      border-color: var(--sc-primary);
    }
    .btn-primary:hover,
    .btn-primary:focus {
      background-color: var(--sc-accent);
      border-color: var(--sc-accent);
    }
    .btn-outline-primary {
      color: var(--sc-primary);
      border-color: var(--sc-primary);
    }
    .btn-outline-primary:hover {
      background-color: var(--sc-primary);
      border-color: var(--sc-primary);
    }
    .list-group-item a {
      color: var(--sc-primary);
      text-decoration: none;
    }
    .list-group-item a:hover {
      color: var(--sc-accent);
    }
    .debug-window {
      max-height: 220px;
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      white-space: pre-wrap;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 6px;
      padding: 10px;
    }
    .s3-file-actions {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      flex-wrap: wrap;
    }
  </style>
</head>
<body>
  <div class="container-fluid" style="max-width: 960px;">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h1 class="h3 mb-0 sc-title"><img src="../logos/scientistCloudLogo_512.png" alt="ScientistCloud" class="sc-logo"> <?php echo htmlspecialchars($pageTitle); ?></h1>
      <a class="btn btn-outline-secondary btn-sm" href="<?php echo htmlspecialchars($portalHome); ?>"><i class="fas fa-arrow-left"></i> Portal</a>
    </div>
    <p class="text-muted small">Browse and download objects from an S3-compatible bucket. Credentials are kept in your server session only (not logged).</p>
    <p class="text-muted small">
      Use <strong>Copy Link</strong> for private, time-limited sharing.
      <?php if ($showPublicUrlButton): ?>
      Use <strong>Copy Public URL</strong> for publishing permanently public files (requires bucket/object public-read policy).
      <?php endif; ?>
    </p>

    <?php if ($connectError): ?>
      <div class="alert alert-danger"><?php echo htmlspecialchars($connectError); ?></div>
    <?php endif; ?>

    <?php if (!empty($debugLog)): ?>
      <div class="card shadow-sm mb-3">
        <div class="card-header py-2"><strong><i class="fas fa-terminal"></i> Debug Log</strong></div>
        <div class="card-body p-2">
          <div class="debug-window"><?php echo htmlspecialchars(implode("\n", $debugLog)); ?></div>
        </div>
      </div>
    <?php endif; ?>

    <?php if (!$connected): ?>
      <div class="card shadow-sm">
        <div class="card-body">
          <h2 class="h5 card-title">Connect</h2>
          <form method="post" action="<?php echo htmlspecialchars($selfPath); ?>" autocomplete="off" id="connectForm">
            <input type="hidden" name="action" value="connect">
            <div class="mb-2">
              <label class="form-label">Endpoint URL</label>
              <input type="url" name="endpoint_url" class="form-control" required placeholder="https://us-east-1.gw.future-tech-holdings.com"
                     value="<?php echo htmlspecialchars((string) ($_POST['endpoint_url'] ?? $defaultEndpoint)); ?>">
            </div>
            <div class="mb-2">
              <label class="form-label">Bucket name</label>
              <input type="text" name="bucket_name" class="form-control" required placeholder="scientistcloud"
                     value="<?php echo htmlspecialchars((string) ($_POST['bucket_name'] ?? $defaultBucket)); ?>">
            </div>
            <div class="mb-2">
              <label class="form-label">Prefix (directory on S3)</label>
              <input type="text" name="prefix" class="form-control" placeholder="utk"
                     value="<?php echo htmlspecialchars((string) ($_POST['prefix'] ?? $defaultPrefix)); ?>">
            </div>
            <div class="row g-2">
              <div class="col-md-6 mb-2">
                <label class="form-label">Access key</label>
                <input type="text" name="access_key" class="form-control" required autocomplete="off">
              </div>
              <div class="col-md-6 mb-2">
                <label class="form-label">Secret key</label>
                <input type="password" name="secret_key" class="form-control" required autocomplete="off">
              </div>
            </div>
            <div class="mb-2">
              <label class="form-label">Region</label>
              <input type="text" name="region" class="form-control" value="us-east-1">
            </div>
            <div class="form-check mb-3">
              <input class="form-check-input" type="checkbox" name="path_style" id="path_style" checked>
              <label class="form-check-label" for="path_style">Path-style addressing (recommended for Wasabi / MinIO)</label>
            </div>
            <button type="submit" class="btn btn-primary" id="connectBtn"><i class="fas fa-plug"></i> Connect</button>
          </form>
        </div>
      </div>
    <?php else: ?>
      <?php
        $root = $session['root_prefix'] ?? '';
        $rel = $session['rel'] ?? '';
        $full = s3_inspector_full_prefix($session);
        $apiDl = $isLocal ? '/api/s3-download.php' : '/portal/api/s3-download.php';
        $apiFolderDl = $isLocal ? '/api/s3-download-folder.php' : '/portal/api/s3-download-folder.php';
        $currentFolderDl = $apiFolderDl . '?rel=' . rawurlencode($rel);
      ?>
      <div class="card shadow-sm mb-3">
        <div class="card-body py-2 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div class="small">
            <strong>Bucket:</strong> <code><?php echo htmlspecialchars($session['bucket']); ?></code>
            &nbsp;·&nbsp; <strong>Root prefix:</strong> <code><?php echo htmlspecialchars($root === '' ? '(bucket root)' : $root); ?></code>
          </div>
          <div class="d-flex align-items-center gap-2">
            <label for="shareLinkExpires" class="small text-muted mb-0">Share link duration</label>
            <select id="shareLinkExpires" class="form-select form-select-sm" style="width:auto;">
              <?php foreach ($shareDurationOptions as $sec => $label): ?>
                <option value="<?php echo (int) $sec; ?>"<?php echo ((int) $sec === $defaultShareSeconds) ? ' selected' : ''; ?>>
                  <?php echo htmlspecialchars($label); ?>
                </option>
              <?php endforeach; ?>
            </select>
            <span class="small text-muted">max <?php echo htmlspecialchars(s3_format_duration($shareMaxSeconds)); ?></span>
          </div>
          <a class="btn btn-sm btn-outline-primary" href="<?php echo htmlspecialchars($currentFolderDl); ?>" title="Download the current folder as a zip archive">
            <i class="fas fa-file-archive"></i> Download Current Folder
          </a>
          <form method="post" action="<?php echo htmlspecialchars($selfPath); ?>" class="m-0">
            <input type="hidden" name="action" value="disconnect">
            <button type="submit" class="btn btn-sm btn-outline-danger">Disconnect</button>
          </form>
        </div>
      </div>

      <?php if ($list['error']): ?>
        <div class="alert alert-danger"><?php echo htmlspecialchars($list['error']); ?></div>
      <?php else: ?>
        <nav aria-label="breadcrumb">
          <ol class="breadcrumb mb-2">
            <li class="breadcrumb-item">
              <a href="<?php echo htmlspecialchars($selfPath); ?>"><i class="fas fa-home"></i> <?php echo htmlspecialchars($root === '' ? 'bucket' : $root); ?></a>
            </li>
            <?php
            if ($rel !== '') {
                $acc = '';
                $segments = array_filter(explode('/', rtrim($rel, '/')));
                foreach ($segments as $i => $seg) {
                    $acc .= $seg . '/';
                    $isLast = $i === count($segments) - 1;
                    if ($isLast) {
                        echo '<li class="breadcrumb-item active" aria-current="page">' . htmlspecialchars($seg) . '</li>';
                    } else {
                        $href = $selfPath . '?rel=' . rawurlencode($acc);
                        echo '<li class="breadcrumb-item"><a href="' . htmlspecialchars($href) . '">' . htmlspecialchars($seg) . '</a></li>';
                    }
                }
            }
            ?>
          </ol>
        </nav>

        <ul class="list-group shadow-sm">
          <?php if ($rel !== ''): ?>
            <?php
              $parentRel = '';
              $parts = array_filter(explode('/', rtrim($rel, '/')));
              if (count($parts) > 0) {
                  array_pop($parts);
                  $parentRel = $parts === [] ? '' : implode('/', $parts) . '/';
              }
              $upHref = $selfPath . ($parentRel === '' ? '' : ('?rel=' . rawurlencode($parentRel)));
            ?>
            <li class="list-group-item">
              <a href="<?php echo htmlspecialchars($upHref); ?>"><i class="fas fa-level-up-alt"></i> ..</a>
            </li>
          <?php endif; ?>

          <?php foreach ($list['folders'] as $folder): ?>
            <?php
              $folderRel = $rel . $folder['name'] . '/';
              $href = $selfPath . '?rel=' . rawurlencode($folderRel);
              $folderDl = $apiFolderDl . '?rel=' . rawurlencode($folderRel);
            ?>
            <li class="list-group-item d-flex justify-content-between align-items-center">
              <a href="<?php echo htmlspecialchars($href); ?>"><i class="fas fa-folder text-warning"></i> <?php echo htmlspecialchars($folder['name']); ?>/</a>
              <a class="btn btn-sm btn-outline-primary" href="<?php echo htmlspecialchars($folderDl); ?>" title="Download this folder as a zip archive">
                <i class="fas fa-file-archive"></i> Download Folder
              </a>
            </li>
          <?php endforeach; ?>

          <?php foreach ($list['files'] as $file): ?>
            <?php
              $dl = $apiDl . '?k=' . rawurlencode($file['key']);
              $datasetSourceLink = s3_dataset_source_link($session, (string) $file['key']);
              $publicUrl = $showPublicUrlButton ? s3_public_object_url($session, (string) $file['key']) : '';
              $sz = $file['size'];
              $szLabel = $sz >= 1073741824
                ? number_format($sz / 1073741824, 2) . ' GB'
                : ($sz >= 1048576 ? number_format($sz / 1048576, 2) . ' MB' : ($sz >= 1024 ? number_format($sz / 1024, 1) . ' KB' : $sz . ' B'));
            ?>
            <li class="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2">
              <span><i class="fas fa-file text-secondary"></i> <?php echo htmlspecialchars($file['name']); ?></span>
              <span class="small text-muted"><?php echo htmlspecialchars($szLabel); ?><?php if (!empty($file['mtime'])): ?> · <?php echo htmlspecialchars($file['mtime']); ?><?php endif; ?></span>
              <span class="s3-file-actions">
                <a class="btn btn-sm btn-outline-primary" href="<?php echo htmlspecialchars($dl); ?>"><i class="fas fa-download"></i> Download</a>
                <button
                  type="button"
                  class="btn btn-sm btn-outline-dark js-copy-source-link"
                  data-source-link="<?php echo htmlspecialchars($datasetSourceLink); ?>"
                  title="Copy dataset source link for Upload Dataset -> S3">
                  <i class="fas fa-copy"></i> Copy S3/HTTP Link
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-outline-secondary js-copy-share-link"
                  data-share-base="<?php echo htmlspecialchars($apiDl . '?mode=share_link&k=' . rawurlencode($file['key'])); ?>"
                  title="Copy a time-limited direct download link">
                  <i class="fas fa-link"></i> Copy Link
                </button>
                <?php if ($showPublicUrlButton): ?>
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-success js-copy-public-link"
                    data-public-link="<?php echo htmlspecialchars($publicUrl); ?>"
                    title="Copy permanent public URL (if object is public)">
                    <i class="fas fa-globe"></i> Copy Public URL
                  </button>
                <?php endif; ?>
              </span>
            </li>
          <?php endforeach; ?>

          <?php if ($list['folders'] === [] && $list['files'] === []): ?>
            <li class="list-group-item text-muted">This folder is empty (under prefix <code class="key"><?php echo htmlspecialchars($full); ?></code>).</li>
          <?php endif; ?>
        </ul>

        <?php if (!empty($list['next_token'])): ?>
          <div class="mt-2">
            <a class="btn btn-outline-secondary btn-sm" href="<?php echo htmlspecialchars($selfPath . '?rel=' . rawurlencode($rel) . '&continuation=' . rawurlencode($list['next_token'])); ?>">Load more</a>
          </div>
        <?php endif; ?>
      <?php endif; ?>
    <?php endif; ?>
  </div>
  <script>
    (function () {
      const form = document.getElementById('connectForm');
      const btn = document.getElementById('connectBtn');
      if (form && btn) {
        form.addEventListener('submit', function () {
          // Promote placeholders into values for required inputs so browser
          // validation does not block when defaults are shown as placeholders.
          form.querySelectorAll('input[required], textarea[required], select[required]').forEach(function (field) {
            const hasValue = typeof field.value === 'string' && field.value.trim() !== '';
            if (!hasValue && typeof field.placeholder === 'string' && field.placeholder.trim() !== '') {
              field.value = field.placeholder.trim();
            }
            if (typeof field.value === 'string') {
              field.value = field.value.trim();
            }
          });
          btn.disabled = true;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Connecting...';
        });
      }
      const shareExpiresSelect = document.getElementById('shareLinkExpires');
      async function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          return;
        }
        const input = document.createElement('textarea');
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        input.remove();
      }

      const shareButtons = document.querySelectorAll('.js-copy-share-link');
      shareButtons.forEach(function (btn) {
        btn.addEventListener('click', async function () {
          const base = btn.getAttribute('data-share-base');
          if (!base) return;
          const expires = shareExpiresSelect ? parseInt(shareExpiresSelect.value || '3600', 10) : 3600;
          const endpoint = base + '&expires=' + encodeURIComponent(String(expires));
          const original = btn.innerHTML;
          btn.disabled = true;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>Link...';
          try {
            const res = await fetch(endpoint, { credentials: 'same-origin' });
            const json = await res.json();
            if (!res.ok || !json.ok || !json.url) {
              throw new Error((json && json.error) ? json.error : 'Could not create link');
            }
            await copyText(json.url);
            btn.innerHTML = '<i class="fas fa-check"></i> Copied';
            setTimeout(function () {
              btn.innerHTML = original;
              btn.disabled = false;
            }, 1300);
          } catch (err) {
            alert('Failed to create/copy share link: ' + (err && err.message ? err.message : 'Unknown error'));
            btn.innerHTML = original;
            btn.disabled = false;
          }
        });
      });

      const publicButtons = document.querySelectorAll('.js-copy-public-link');
      publicButtons.forEach(function (btn) {
        btn.addEventListener('click', async function () {
          const link = btn.getAttribute('data-public-link');
          if (!link) return;
          const original = btn.innerHTML;
          btn.disabled = true;
          try {
            await copyText(link);
            btn.innerHTML = '<i class="fas fa-check"></i> Copied';
            setTimeout(function () {
              btn.innerHTML = original;
              btn.disabled = false;
            }, 1300);
          } catch (err) {
            alert('Failed to copy public URL.');
            btn.innerHTML = original;
            btn.disabled = false;
          }
        });
      });

      const sourceButtons = document.querySelectorAll('.js-copy-source-link');
      sourceButtons.forEach(function (btn) {
        btn.addEventListener('click', async function () {
          const sourceLink = btn.getAttribute('data-source-link');
          if (!sourceLink) return;
          const original = btn.innerHTML;
          btn.disabled = true;
          try {
            await copyText(sourceLink);
            btn.innerHTML = '<i class="fas fa-check"></i> Copied';
            setTimeout(function () {
              btn.innerHTML = original;
              btn.disabled = false;
            }, 1300);
          } catch (err) {
            alert('Failed to copy dataset source link.');
            btn.innerHTML = original;
            btn.disabled = false;
          }
        });
      });
    })();
  </script>
</body>
</html>
