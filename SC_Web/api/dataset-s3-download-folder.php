<?php
/**
 * Zip and download an S3 folder for the authenticated dataset S3 inspector session.
 */

declare(strict_types=1);

define('S3_INSPECTOR_SESSION_OVERRIDE', 'portal_dataset_s3_inspector');
define('S3_INSPECTOR_SKIP_PORTAL_AUTH', true);

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/dataset_s3_inspector.php';
require_once __DIR__ . '/../includes/s3_inspector.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

$user = getCurrentUser();
if (!$user) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Forbidden';
    exit;
}

$userEmail = trim((string) ($user['email'] ?? $user['user_email'] ?? ''));
$datasetId = trim((string) ($_GET['dataset'] ?? ''));
if ($datasetId !== '' && $userEmail !== '') {
    try {
        dataset_s3_bootstrap_session($datasetId, $userEmail);
    } catch (Throwable $e) {
        http_response_code(403);
        header('Content-Type: text/plain; charset=UTF-8');
        echo $e->getMessage();
        exit;
    }
}

require __DIR__ . '/s3-download-folder.php';
