<?php
/**
 * S3-compatible bucket browser (authenticated portal users).
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

$user = getCurrentUser();
if (!$user) {
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
    header('Location: ' . $loginPath);
    exit;
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

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$portalHome = $isLocal ? '/index.php' : '/portal/index.php';
$selfPath = $isLocal ? '/s3.php' : '/portal/s3.php';

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
            $list = s3_inspector_list_page($probe, null);
            if ($list['error'] !== null) {
                $err = 'Could not list bucket: ' . $list['error'];
            } else {
                s3_sess_save($probe);
                header('Location: ' . $selfPath);
                exit;
            }
        }
        // fall through to show form with error
        $_SESSION['s3_connect_error'] = $err;
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
} else {
    $list = null;
}

$pageTitle = 'Inspect S3';
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
    body { padding: 1.25rem; background: var(--bs-body-bg); }
    .breadcrumb { background: var(--bs-secondary-bg); }
    code.key { font-size: 0.85em; word-break: break-all; }
  </style>
</head>
<body>
  <div class="container-fluid" style="max-width: 960px;">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h1 class="h3 mb-0"><i class="fab fa-aws text-warning"></i> <?php echo htmlspecialchars($pageTitle); ?></h1>
      <a class="btn btn-outline-secondary btn-sm" href="<?php echo htmlspecialchars($portalHome); ?>"><i class="fas fa-arrow-left"></i> Portal</a>
    </div>
    <p class="text-muted small">Browse and download objects from an S3-compatible bucket. Credentials are kept in your server session only (not logged).</p>

    <?php if ($connectError): ?>
      <div class="alert alert-danger"><?php echo htmlspecialchars($connectError); ?></div>
    <?php endif; ?>

    <?php if (!$connected): ?>
      <div class="card shadow-sm">
        <div class="card-body">
          <h2 class="h5 card-title">Connect</h2>
          <form method="post" action="<?php echo htmlspecialchars($selfPath); ?>" autocomplete="off">
            <input type="hidden" name="action" value="connect">
            <div class="mb-2">
              <label class="form-label">Endpoint URL</label>
              <input type="url" name="endpoint_url" class="form-control" required placeholder="https://s3.us-east-1.wasabisys.com"
                     value="<?php echo htmlspecialchars((string) ($_POST['endpoint_url'] ?? 'https://s3.us-east-1.wasabisys.com')); ?>">
            </div>
            <div class="mb-2">
              <label class="form-label">Bucket name</label>
              <input type="text" name="bucket_name" class="form-control" required placeholder="my-bucket">
            </div>
            <div class="mb-2">
              <label class="form-label">Prefix (directory on S3)</label>
              <input type="text" name="prefix" class="form-control" placeholder="optional/path/prefix/">
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
            <button type="submit" class="btn btn-primary"><i class="fas fa-plug"></i> Connect</button>
          </form>
        </div>
      </div>
    <?php else: ?>
      <?php
        $root = $session['root_prefix'] ?? '';
        $rel = $session['rel'] ?? '';
        $full = s3_inspector_full_prefix($session);
        $apiDl = $isLocal ? '/api/s3-download.php' : '/portal/api/s3-download.php';
      ?>
      <div class="card shadow-sm mb-3">
        <div class="card-body py-2 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div class="small">
            <strong>Bucket:</strong> <code><?php echo htmlspecialchars($session['bucket']); ?></code>
            &nbsp;·&nbsp; <strong>Root prefix:</strong> <code><?php echo htmlspecialchars($root === '' ? '(bucket root)' : $root); ?></code>
          </div>
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
            <?php $href = $selfPath . '?rel=' . rawurlencode($rel . $folder['name'] . '/'); ?>
            <li class="list-group-item d-flex justify-content-between align-items-center">
              <a href="<?php echo htmlspecialchars($href); ?>"><i class="fas fa-folder text-warning"></i> <?php echo htmlspecialchars($folder['name']); ?>/</a>
            </li>
          <?php endforeach; ?>

          <?php foreach ($list['files'] as $file): ?>
            <?php
              $dl = $apiDl . '?k=' . rawurlencode($file['key']);
              $sz = $file['size'];
              $szLabel = $sz >= 1073741824
                ? number_format($sz / 1073741824, 2) . ' GB'
                : ($sz >= 1048576 ? number_format($sz / 1048576, 2) . ' MB' : ($sz >= 1024 ? number_format($sz / 1024, 1) . ' KB' : $sz . ' B'));
            ?>
            <li class="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2">
              <span><i class="fas fa-file text-secondary"></i> <?php echo htmlspecialchars($file['name']); ?></span>
              <span class="small text-muted"><?php echo htmlspecialchars($szLabel); ?><?php if (!empty($file['mtime'])): ?> · <?php echo htmlspecialchars($file['mtime']); ?><?php endif; ?></span>
              <a class="btn btn-sm btn-outline-primary" href="<?php echo htmlspecialchars($dl); ?>"><i class="fas fa-download"></i> Download</a>
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
</body>
</html>
