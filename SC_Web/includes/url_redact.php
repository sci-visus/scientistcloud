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
 * Return a copy of $dataset with URL fields redacted for JSON/HTML only.
 * Never mutates the input array (callers may reuse the same row from Mongo/SCLib in-process).
 *
 * @param array<string,mixed>|null $dataset
 * @return array<string,mixed>|null
 */
function sc_redact_dataset_urls_for_client($dataset)
{
    if ($dataset === null || !is_array($dataset)) {
        return $dataset;
    }
    $out = array_merge([], $dataset);
    if (isset($out['metadata']) && is_array($out['metadata'])) {
        $out['metadata'] = array_merge([], $out['metadata']);
    }
    $urlKeys = ['google_drive_link', 'source_path', 'viewer_url', 'download_url'];
    foreach ($urlKeys as $k) {
        if (!empty($out[$k]) && is_string($out[$k])) {
            $out[$k] = sc_redact_url_secrets($out[$k]);
        }
    }
    if (!empty($out['metadata']) && is_array($out['metadata'])) {
        foreach ($urlKeys as $k) {
            if (!empty($out['metadata'][$k]) && is_string($out['metadata'][$k])) {
                $out['metadata'][$k] = sc_redact_url_secrets($out['metadata'][$k]);
            }
        }
    }
    foreach (['s3_access_key_id', 's3_secret_access_key'] as $sk) {
        if (isset($out[$sk]) && (string)$out[$sk] !== '') {
            $out[$sk] = '...';
        }
    }
    return $out;
}
