<?php
/**
 * Detect materialized dashboard files on the server (upload/converted).
 * Shared by portal server flag, viewer URLs, and SCLib-aligned policy.
 */

/**
 * @param array<string, mixed> $dataset
 */
function sc_dataset_has_local_dashboard_files($dataset) {
    $uuid = trim((string)($dataset['uuid'] ?? $dataset['id'] ?? ''));
    if ($uuid === '') {
        return false;
    }

    $roots = [
        rtrim(getenv('JOB_OUT_DATA_DIR') ?: '/mnt/visus_datasets/converted', '/') . '/' . $uuid,
        rtrim(getenv('JOB_IN_DATA_DIR') ?: '/mnt/visus_datasets/upload', '/') . '/' . $uuid,
    ];

    foreach ($roots as $root) {
        if (!is_dir($root)) {
            continue;
        }
        try {
            $iterator = new RecursiveIteratorIterator(
                new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS)
            );
            foreach ($iterator as $fileInfo) {
                if (!$fileInfo->isFile()) {
                    continue;
                }
                $ext = strtolower($fileInfo->getExtension());
                if (in_array($ext, ['idx', 'nxs', 'h5', 'hdf5'], true)) {
                    return true;
                }
            }
        } catch (Exception $e) {
            continue;
        }
    }

    return false;
}

/**
 * Portal server= flag: remote link only when no local materialized data.
 *
 * @param array<string, mixed> $dataset
 */
function sc_dataset_server_flag($dataset) {
    $explicit = strtolower(trim((string)($dataset['server'] ?? '')));
    if ($explicit === 'true' || $explicit === 'false') {
        if ($explicit === 'true' && sc_dataset_has_local_dashboard_files($dataset)) {
            return 'false';
        }
        return $explicit;
    }

    if (sc_dataset_has_local_dashboard_files($dataset)) {
        return 'false';
    }

    $link = $dataset['google_drive_link'] ?? $dataset['download_url'] ?? $dataset['viewer_url'] ?? '';
    $linkLower = strtolower(trim((string)$link));
    $remoteSchemes = ['s3://', 'http://', 'https://', 'pelican://'];
    foreach ($remoteSchemes as $scheme) {
        if (strpos($linkLower, $scheme) === 0 && strpos($linkLower, 'google.com') === false) {
            return 'true';
        }
    }

    return 'false';
}
