<?php
/**
 * Shared S3 inspector browse UI (public + authenticated embed).
 *
 * Expects variables from the including script:
 * $pageTitle, $portalHomeLabel, $portalHomeHref, $selfPath, $apiDl, $apiFolderDl,
 * $datasetId, $bootstrapError, $connected, $session, $list, $shareDurationOptions,
 * $defaultShareSeconds, $queryBase, $embedMode, $browserShareUrl
 */

declare(strict_types=1);

if (!function_exists('s3_embed_format_duration')) {
    function s3_embed_format_duration(int $seconds): string
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
}

if (!function_exists('s3_embed_object_url')) {
    function s3_embed_object_url(array $session, string $key): string
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
}

$embedMode = !empty($embedMode);
$datasetName = $connected ? (string) ($session['dataset_name'] ?? 'Dataset') : '';
$assetsPrefix = $embedMode ? 'assets' : '../assets';
$logoPath = $embedMode ? 'assets/images/scientistcloud-logo.png' : '../assets/images/scientistcloud-logo.png';
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?php echo htmlspecialchars($pageTitle); ?> — ScientistCloud</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <?php if (!$embedMode && str_contains($selfPath, '/public/')): ?>
  <link href="../assets/css/public.css" rel="stylesheet">
  <?php endif; ?>
  <style>
    body { padding: <?php echo $embedMode ? '0.75rem' : '1.25rem'; ?>; background: #f7faff; color: #1b2b52; }
    .sc-title { color: #1f3c88; font-weight: 700; display: inline-flex; align-items: center; }
    .sc-logo { height: <?php echo $embedMode ? '48px' : '72px'; ?>; width: <?php echo $embedMode ? '48px' : '72px'; ?>; object-fit: contain; margin-right: 10px; }
    code.key { font-size: 0.85em; word-break: break-all; }
    .s3-file-list-scroll { max-height: min(55vh, 520px); overflow-y: auto; }
    .s3-preview pre { margin: 0; max-height: 360px; overflow: auto; font-size: 12px; white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e2e8f0; border-radius: 6px; padding: 10px; }
    .s3-preview { border: 1px solid #c9daf8; border-radius: 6px; background: #f8fbff; padding: 0.75rem; display: none; }
  </style>
</head>
<body>
  <div class="container-fluid" style="max-width: 1260px;">
    <?php if (!$embedMode): ?>
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <h1 class="h3 mb-0 sc-title">
        <img src="<?php echo htmlspecialchars($logoPath); ?>" alt="" class="sc-logo" role="presentation">
        <?php echo htmlspecialchars($pageTitle); ?>
      </h1>
      <div class="d-flex gap-2">
        <?php if ($datasetId !== '' && !empty($browserShareUrl)): ?>
          <button type="button" class="btn btn-outline-primary btn-sm" id="copyBrowserShareLink" title="Copy link to this S3 browser">
            <i class="fas fa-link"></i> Copy Share Link
          </button>
        <?php endif; ?>
        <a class="btn btn-outline-secondary btn-sm" href="<?php echo htmlspecialchars($portalHomeHref); ?>">
          <i class="fas fa-arrow-left"></i> <?php echo htmlspecialchars($portalHomeLabel); ?>
        </a>
      </div>
    </div>
    <?php endif; ?>

    <?php if ($bootstrapError): ?>
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-circle"></i>
        <?php echo htmlspecialchars($bootstrapError); ?>
      </div>
    <?php elseif (!$connected): ?>
      <div class="alert alert-info">
        Add <code>?dataset=&lt;dataset-uuid&gt;</code> to open S3 storage for a dataset.
      </div>
    <?php else: ?>
      <?php
        $root = $session['root_prefix'] ?? '';
        $rel = $session['rel'] ?? '';
        $full = s3_inspector_full_prefix($session);
        $relQuery = $datasetId !== '' ? ('dataset=' . rawurlencode($datasetId)) : '';
        if ($embedMode) {
            $relQuery .= ($relQuery !== '' ? '&' : '') . 'embed=1';
        }
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
            <?php if (!$embedMode): ?>
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
            <?php endif; ?>
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
                  <?php if (!$embedMode): ?>
                  <button type="button" class="btn btn-sm btn-outline-secondary js-copy-share-link" data-share-base="<?php echo htmlspecialchars($apiDl . '?mode=share_link&' . $dlParams); ?>">
                    <i class="fas fa-link"></i> Copy Link
                  </button>
                  <?php endif; ?>
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
      const browserShareUrl = <?php echo json_encode($browserShareUrl ?? ''); ?>;
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
