<?php
/**
 * Redact credential-like URL fragments before JSON/HTML responses to the browser.
 */

/**
 * @param string|null $url
 */
function sc_redact_url_secrets($url): string
{
    if ($url === null || $url === '') {
        return '';
    }
    $out = trim((string)$url);
    if ($out === '') {
        return '';
    }
    // s3://access_key:secret_key@bucket/key
    if (stripos($out, 's3://') === 0) {
        $rest = substr($out, 5);
        $atPos = strpos($rest, '@');
        if ($atPos !== false) {
            $userinfo = substr($rest, 0, $atPos);
            if (strpos($userinfo, ':') !== false) {
                $hostpath = substr($rest, $atPos + 1);
                $out = 's3://...@' . $hostpath;
            }
        }
    }
    $params = [
        'secret_key',
        'access_key',
        'secret_access_key',
        'access_key_id',
        'password',
        'token',
        'api_key',
        'apikey',
        'signature',
        'x-amz-signature',
        'x-amz-security-token',
        'x-amz-credential',
        'awsaccesskeyid',
    ];
    foreach ($params as $p) {
        $out = preg_replace('/([?&]' . preg_quote($p, '/') . '=)[^&]*/i', '$1...', $out);
    }
    return $out;
}

/**
 * @param array<string,mixed>|null $dataset
 * @return array<string,mixed>|null
 */
function sc_redact_dataset_urls_for_client($dataset)
{
    if ($dataset === null || !is_array($dataset)) {
        return $dataset;
    }
    $urlKeys = ['google_drive_link', 'source_path', 'viewer_url', 'download_url'];
    foreach ($urlKeys as $k) {
        if (!empty($dataset[$k]) && is_string($dataset[$k])) {
            $dataset[$k] = sc_redact_url_secrets($dataset[$k]);
        }
    }
    if (!empty($dataset['metadata']) && is_array($dataset['metadata'])) {
        foreach ($urlKeys as $k) {
            if (!empty($dataset['metadata'][$k]) && is_string($dataset['metadata'][$k])) {
                $dataset['metadata'][$k] = sc_redact_url_secrets($dataset['metadata'][$k]);
            }
        }
    }
    foreach (['s3_access_key_id', 's3_secret_access_key'] as $sk) {
        if (isset($dataset[$sk]) && (string)$dataset[$sk] !== '') {
            $dataset[$sk] = '...';
        }
    }
    return $dataset;
}
