<?php
/**
 * Zip and download an S3 folder for the public dataset S3 inspector session.
 */

declare(strict_types=1);

define('S3_INSPECTOR_SESSION_OVERRIDE', 'portal_public_s3_inspector');
define('S3_INSPECTOR_SKIP_PORTAL_AUTH', true);

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../includes/public_s3_dataset.php';
require_once __DIR__ . '/../includes/s3_inspector.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

$datasetId = trim((string) ($_GET['dataset'] ?? ''));
if ($datasetId !== '') {
    try {
        public_s3_bootstrap_session($datasetId);
    } catch (Throwable $e) {
        http_response_code(403);
        header('Content-Type: text/plain; charset=UTF-8');
        echo $e->getMessage();
        exit;
    }
}

require __DIR__ . '/s3-download-folder.php';
