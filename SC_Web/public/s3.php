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

function public_s3_object_url(array $session, string $key): string
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

function public_s3_format_duration(int $seconds): string
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
$publicPortalHome = $isLocal ? '/public/index.php' : '/portal/public/index.php';
$selfPath = $isLocal ? '/public/s3.php' : '/portal/public/s3.php';
$apiDl = $isLocal ? '/api/public-s3-download.php' : '/portal/api/public-s3-download.php';
$apiFolderDl = $isLocal ? '/api/public-s3-download-folder.php' : '/portal/api/public-s3-download-folder.php';

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
$datasetName = $connected ? (string) ($session['dataset_name'] ?? 'Dataset') : '';
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
    $shareDurationOptions = [$shareMaxSeconds => public_s3_format_duration($shareMaxSeconds)];
}
$defaultShareSeconds = 3600;
if ($defaultShareSeconds > $shareMaxSeconds) {
    $keys = array_keys($shareDurationOptions);
    $defaultShareSeconds = (int) end($keys);
}

$queryBase = $datasetId !== '' ? ('?dataset=' . rawurlencode($datasetId)) : '?';
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?php echo htmlspecialchars($pageTitle); ?> — ScientistCloud</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <link href="../assets/css/public.css" rel="stylesheet">
  <style>
    body { padding: 1.25rem; background: #f7faff; color: #1b2b52; }
    .sc-title { color: #1f3c88; font-weight: 700; display: inline-flex; align-items: center; }
    .sc-logo { height: 72px; width: 72px; object-fit: contain; margin-right: 10px; }
    code.key { font-size: 0.85em; word-break: break-all; }
    .s3-file-list-scroll { max-height: min(55vh, 520px); overflow-y: auto; }
    .s3-preview pre { margin: 0; max-height: 360px; overflow: auto; font-size: 12px; white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e2e8f0; border-radius: 6px; padding: 10px; }
    .s3-preview { border: 1px solid #c9daf8; border-radius: 6px; background: #f8fbff; padding: 0.75rem; display: none; }
  </style>
</head>
<body>
  <div class="container-fluid" style="max-width: 1260px;">
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <h1 class="h3 mb-0 sc-title">
        <img src="../assets/images/scientistcloud-logo.png" alt="" class="sc-logo" role="presentation">
        <?php echo htmlspecialchars($pageTitle); ?>
      </h1>
      <div class="d-flex gap-2">
        <?php if ($datasetId !== ''): ?>
          <button type="button" class="btn btn-outline-primary btn-sm" id="copyBrowserShareLink" title="Copy link to this S3 browser">
            <i class="fas fa-link"></i> Copy Share Link
          </button>
        <?php endif; ?>
        <a class="btn btn-outline-secondary btn-sm" href="<?php echo htmlspecialchars($publicPortalHome . ($datasetId !== '' ? ('?dataset=' . rawurlencode($datasetId)) : '')); ?>">
          <i class="fas fa-arrow-left"></i> Public Portal
        </a>
      </div>
    </div>

    <?php if ($bootstrapError): ?>
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-circle"></i>
        <?php echo htmlspecialchars($bootstrapError); ?>
      </div>
      <p class="text-muted">Open a dataset from the <a href="<?php echo htmlspecialchars($publicPortalHome); ?>">public data portal</a> and use <strong>Browse S3 Data</strong>, or add <code>?dataset=&lt;uuid&gt;</code> to this URL.</p>
    <?php elseif (!$connected): ?>
      <div class="alert alert-info">
        Select a public dataset with remote S3 storage. Example:
        <code><?php echo htmlspecialchars($selfPath); ?>?dataset=&lt;dataset-uuid&gt;</code>
      </div>
    <?php else: ?>
      <?php
        $root = $session['root_prefix'] ?? '';
        $rel = $session['rel'] ?? '';
        $full = s3_inspector_full_prefix($session);
        $relQuery = $datasetId !== '' ? ('dataset=' . rawurlencode($datasetId)) : '';
        $currentFolderDl = $apiFolderDl . '?rel=' . rawurlencode($rel) . ($datasetId !== '' ? ('&dataset=' . rawurlencode($datasetId)) : '');
      ?>
      <div class="card shadow-sm mb-3">
        <div class="card-body py-2">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div>
              <strong><?php echo htmlspecialchars($datasetName); ?></strong>
              <div class="small text-muted mt-1">
                <strong>Bucket:</strong> <code><?php echo htmlspecialchars((string) $session['bucket']); ?></code>
                &nbsp;·&nbsp;
                <strong>Root prefix:</strong> <code><?php echo htmlspecialchars($root === '' ? '(bucket root)' : $root); ?></code>
              </div>
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
            </div>
          </div>
        </div>
      </div>

      <?php if ($list['error']): ?>
        <div class="alert alert-danger"><?php echo htmlspecialchars($list['error']); ?></div>
      <?php else: ?>
        <nav aria-label="breadcrumb" class="mb-2">
          <ol class="breadcrumb mb-0">
            <li class="breadcrumb-item">
              <a href="<?php echo htmlspecialchars($selfPath . $queryBase); ?>">
                <i class="fas fa-home"></i> <?php echo htmlspecialchars($root === '' ? 'bucket' : $root); ?>
              </a>
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
                        $href = $selfPath . '?' . $relQuery . ($relQuery !== '' ? '&' : '') . 'rel=' . rawurlencode($acc);
                        echo '<li class="breadcrumb-item"><a href="' . htmlspecialchars($href) . '">' . htmlspecialchars($seg) . '</a></li>';
                    }
                }
            }
            ?>
          </ol>
        </nav>

        <div class="mb-2 text-end">
          <a class="btn btn-sm btn-outline-primary" href="<?php echo htmlspecialchars($currentFolderDl); ?>">
            <i class="fas fa-file-archive"></i> Download Current Folder
          </a>
        </div>

        <div class="s3-file-list-scroll shadow-sm">
          <ul class="list-group">
            <?php if ($rel !== ''): ?>
              <?php
                $parentRel = '';
                $parts = array_filter(explode('/', rtrim($rel, '/')));
                if (count($parts) > 0) {
                    array_pop($parts);
                    $parentRel = $parts === [] ? '' : implode('/', $parts) . '/';
                }
                $upHref = $selfPath . '?' . $relQuery . ($parentRel === '' ? '' : ('&rel=' . rawurlencode($parentRel)));
              ?>
              <li class="list-group-item"><a href="<?php echo htmlspecialchars($upHref); ?>"><i class="fas fa-level-up-alt"></i> ..</a></li>
            <?php endif; ?>

            <?php foreach ($list['folders'] as $folder): ?>
              <?php
                $folderRel = $rel . $folder['name'] . '/';
                $href = $selfPath . '?' . $relQuery . '&rel=' . rawurlencode($folderRel);
                $folderDl = $apiFolderDl . '?rel=' . rawurlencode($folderRel) . ($datasetId !== '' ? ('&dataset=' . rawurlencode($datasetId)) : '');
              ?>
              <li class="list-group-item d-flex justify-content-between align-items-center">
                <a href="<?php echo htmlspecialchars($href); ?>"><i class="fas fa-folder text-warning"></i> <?php echo htmlspecialchars($folder['name']); ?>/</a>
                <a class="btn btn-sm btn-outline-primary" href="<?php echo htmlspecialchars($folderDl); ?>"><i class="fas fa-file-archive"></i> Download Folder</a>
              </li>
            <?php endforeach; ?>

            <?php foreach ($list['files'] as $file): ?>
              <?php
                $dlParams = 'k=' . rawurlencode($file['key']) . ($datasetId !== '' ? ('&dataset=' . rawurlencode($datasetId)) : '');
                $dl = $apiDl . '?' . $dlParams;
                $preview = $apiDl . '?mode=preview_text&' . $dlParams;
                $sourceLink = public_s3_object_url($session, (string) $file['key']);
                $lowerName = strtolower((string) $file['name']);
                $isTextPreviewable = str_ends_with($lowerName, '.idx')
                  || str_ends_with($lowerName, '.txt')
                  || str_ends_with($lowerName, '.csv')
                  || str_ends_with($lowerName, '.json');
                $sz = $file['size'];
                $szLabel = $sz >= 1073741824
                  ? number_format($sz / 1073741824, 2) . ' GB'
                  : ($sz >= 1048576 ? number_format($sz / 1048576, 2) . ' MB' : ($sz >= 1024 ? number_format($sz / 1024, 1) . ' KB' : $sz . ' B'));
              ?>
              <li class="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2">
                <span><i class="fas fa-file text-secondary"></i> <?php echo htmlspecialchars($file['name']); ?></span>
                <span class="small text-muted"><?php echo htmlspecialchars($szLabel); ?><?php if (!empty($file['mtime'])): ?> · <?php echo htmlspecialchars($file['mtime']); ?><?php endif; ?></span>
                <span class="d-inline-flex gap-1 flex-wrap">
                  <?php if ($isTextPreviewable): ?>
                    <button type="button" class="btn btn-sm btn-outline-info js-preview-idx" data-preview-url="<?php echo htmlspecialchars($preview); ?>" data-file-name="<?php echo htmlspecialchars((string) $file['name']); ?>">
                      <i class="fas fa-eye"></i> Preview
                    </button>
                  <?php endif; ?>
                  <a class="btn btn-sm btn-outline-primary" href="<?php echo htmlspecialchars($dl); ?>"><i class="fas fa-download"></i> Download</a>
                  <button type="button" class="btn btn-sm btn-outline-secondary js-copy-share-link" data-share-base="<?php echo htmlspecialchars($apiDl . '?mode=share_link&' . $dlParams); ?>">
                    <i class="fas fa-link"></i> Copy Link
                  </button>
                </span>
              </li>
            <?php endforeach; ?>

            <?php if ($list['folders'] === [] && $list['files'] === []): ?>
              <li class="list-group-item text-muted">This folder is empty (under prefix <code class="key"><?php echo htmlspecialchars($full); ?></code>).</li>
            <?php endif; ?>
          </ul>
        </div>

        <?php if (!empty($list['next_token'])): ?>
          <div class="mt-2">
            <?php
              $moreHref = $selfPath . '?' . $relQuery . '&rel=' . rawurlencode($rel) . '&continuation=' . rawurlencode((string) $list['next_token']);
            ?>
            <a class="btn btn-outline-secondary btn-sm" href="<?php echo htmlspecialchars($moreHref); ?>">Load more</a>
          </div>
        <?php endif; ?>

        <div id="idxPreviewPanel" class="s3-preview mt-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong id="idxPreviewTitle">Text Preview</strong>
            <button type="button" id="idxPreviewClose" class="btn btn-sm btn-outline-secondary">Close</button>
          </div>
          <pre id="idxPreviewContent">Select a text file and click Preview.</pre>
        </div>
      <?php endif; ?>
    <?php endif; ?>
  </div>

  <script>
    (function () {
      const browserShareUrl = <?php echo json_encode($datasetId !== '' ? public_s3_browser_share_url($datasetId) : ''); ?>;
      const copyBtn = document.getElementById('copyBrowserShareLink');
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
      if (copyBtn && browserShareUrl) {
        copyBtn.addEventListener('click', async function () {
          const original = copyBtn.innerHTML;
          try {
            await copyText(browserShareUrl);
            copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied';
            setTimeout(function () { copyBtn.innerHTML = original; }, 1300);
          } catch (err) {
            alert('Failed to copy share link.');
          }
        });
      }

      const shareExpiresSelect = document.getElementById('shareLinkExpires');
      document.querySelectorAll('.js-copy-share-link').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          const base = btn.getAttribute('data-share-base');
          if (!base) return;
          const expires = shareExpiresSelect ? parseInt(shareExpiresSelect.value || '3600', 10) : 3600;
          const endpoint = base + '&expires=' + encodeURIComponent(String(expires));
          const original = btn.innerHTML;
          btn.disabled = true;
          try {
            const res = await fetch(endpoint, { credentials: 'same-origin' });
            const json = await res.json();
            if (!res.ok || !json.ok || !json.url) {
              throw new Error((json && json.error) ? json.error : 'Could not create link');
            }
            await copyText(json.url);
            btn.innerHTML = '<i class="fas fa-check"></i> Copied';
            setTimeout(function () { btn.innerHTML = original; btn.disabled = false; }, 1300);
          } catch (err) {
            alert('Failed to create/copy share link: ' + (err && err.message ? err.message : 'Unknown error'));
            btn.innerHTML = original;
            btn.disabled = false;
          }
        });
      });

      const previewPanel = document.getElementById('idxPreviewPanel');
      const previewTitle = document.getElementById('idxPreviewTitle');
      const previewContent = document.getElementById('idxPreviewContent');
      const previewClose = document.getElementById('idxPreviewClose');
      if (previewClose && previewPanel) {
        previewClose.addEventListener('click', function () { previewPanel.style.display = 'none'; });
      }
      document.querySelectorAll('.js-preview-idx').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          if (!previewPanel || !previewContent || !previewTitle) return;
          const endpoint = btn.getAttribute('data-preview-url');
          const fileName = btn.getAttribute('data-file-name') || 'file';
          const original = btn.innerHTML;
          btn.disabled = true;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Loading...';
          previewPanel.style.display = 'block';
          previewTitle.textContent = 'Preview — ' + fileName;
          previewContent.textContent = 'Loading...';
          try {
            const res = await fetch(endpoint, { credentials: 'same-origin' });
            const json = await res.json();
            if (!res.ok || !json.ok) {
              throw new Error((json && json.error) ? json.error : 'Preview failed');
            }
            previewContent.textContent = json.content || '(empty file)';
          } catch (err) {
            previewContent.textContent = 'Preview failed: ' + (err && err.message ? err.message : 'Unknown error');
          } finally {
            btn.innerHTML = original;
            btn.disabled = false;
          }
        });
      });
    })();
  </script>
</body>
</html>
