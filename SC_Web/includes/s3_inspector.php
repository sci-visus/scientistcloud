<?php
/**
 * S3 inspector helpers — S3-compatible endpoints (AWS, Wasabi, MinIO, etc.)
 */

declare(strict_types=1);

use Aws\S3\S3Client;
use Aws\Exception\AwsException;

/**
 * Normalize root prefix: empty string or "path/to/" (no leading slash).
 */
function s3_inspector_normalize_root_prefix(string $prefix): string
{
    $p = trim(str_replace('\\', '/', $prefix));
    $p = ltrim($p, '/');
    if ($p === '') {
        return '';
    }
    return rtrim($p, '/') . '/';
}

/**
 * Relative browse path under root prefix: "" or "foo/bar/" only safe segments.
 */
function s3_inspector_sanitize_rel(string $rel): string
{
    $rel = str_replace('\\', '/', $rel);
    $parts = array_filter(explode('/', $rel), static function ($p) {
        return $p !== '' && $p !== '.' && $p !== '..';
    });
    if ($parts === []) {
        return '';
    }
    return implode('/', $parts) . '/';
}

/**
 * Full S3 key prefix for listing = root + rel.
 */
function s3_inspector_full_prefix(array $session): string
{
    return ($session['root_prefix'] ?? '') . ($session['rel'] ?? '');
}

function s3_inspector_connected(array $session): bool
{
    return !empty($session['endpoint'])
        && !empty($session['bucket'])
        && !empty($session['access_key'])
        && !empty($session['secret_key']);
}

function s3_inspector_create_client(array $session, array $httpOverrides = []): S3Client
{
    $endpoint = rtrim(trim($session['endpoint']), '/');
    $region = trim($session['region'] ?? 'us-east-1') ?: 'us-east-1';
    $usePathStyle = !empty($session['path_style']);

    $http = array_merge([
        'verify' => true,
        'connect_timeout' => 8,
        'timeout' => 25,
    ], $httpOverrides);

    return new S3Client([
        'version' => 'latest',
        'region' => $region,
        'endpoint' => $endpoint,
        'credentials' => [
            'key' => $session['access_key'],
            'secret' => $session['secret_key'],
        ],
        'use_path_style_endpoint' => $usePathStyle,
        'scheme' => 'https',
        // Default is tuned for interactive listing. Download endpoints can override.
        'http' => $http,
        'retries' => 1,
    ]);
}

/**
 * @return array{folders: list<array{name:string,prefix:string}>, files: list<array{key:string,name:string,size:int,mtime:?string}>, error: ?string}
 */
function s3_inspector_list_page(array $session, ?string $continuationToken = null): array
{
    $started = microtime(true);
    $debug = [];
    $out = ['folders' => [], 'files' => [], 'error' => null, 'next_token' => null, 'debug' => []];
    if (!s3_inspector_connected($session)) {
        $out['error'] = 'Not connected.';
        $out['debug'][] = '[error] Session is not connected (missing credentials).';
        return $out;
    }

    $bucket = $session['bucket'];
    $prefix = s3_inspector_full_prefix($session);
    $endpoint = (string) ($session['endpoint'] ?? '');
    $region = (string) ($session['region'] ?? 'us-east-1');
    $pathStyle = !empty($session['path_style']) ? 'true' : 'false';
    $debug[] = sprintf(
        '[start] listObjectsV2 endpoint=%s bucket=%s prefix=%s region=%s path_style=%s',
        $endpoint,
        $bucket,
        $prefix,
        $region,
        $pathStyle
    );

    try {
        $client = s3_inspector_create_client($session);
        $params = [
            'Bucket' => $bucket,
            'Prefix' => $prefix,
            'Delimiter' => '/',
            'MaxKeys' => 1000,
        ];
        if ($continuationToken !== null && $continuationToken !== '') {
            $params['ContinuationToken'] = $continuationToken;
            $debug[] = '[request] Using continuation token';
        }

        $result = $client->listObjectsV2($params);
        $debug[] = '[response] listObjectsV2 returned successfully';

        foreach ($result->get('CommonPrefixes') ?? [] as $cp) {
            $p = $cp['Prefix'] ?? '';
            if ($p === '') {
                continue;
            }
            $name = substr($p, strlen($prefix));
            $name = rtrim($name, '/');
            if ($name !== '') {
                $out['folders'][] = ['name' => $name, 'prefix' => $p];
            }
        }

        foreach ($result->get('Contents') ?? [] as $obj) {
            $key = $obj['Key'] ?? '';
            if ($key === '' || $key === $prefix) {
                continue;
            }
            // Skip "directory placeholder" keys
            if (str_ends_with($key, '/') && ($obj['Size'] ?? 0) == 0) {
                continue;
            }
            $name = substr($key, strlen($prefix));
            if ($name === '' || str_contains($name, '/')) {
                continue;
            }
            $mtime = isset($obj['LastModified']) ? $obj['LastModified']->format('c') : null;
            $out['files'][] = [
                'key' => $key,
                'name' => $name,
                'size' => (int) ($obj['Size'] ?? 0),
                'mtime' => $mtime,
            ];
        }

        $out['next_token'] = $result->get('NextContinuationToken');
        $debug[] = sprintf(
            '[done] folders=%d files=%d truncated=%s',
            count($out['folders']),
            count($out['files']),
            $out['next_token'] ? 'yes' : 'no'
        );
    } catch (AwsException $e) {
        $out['error'] = $e->getAwsErrorMessage() ?: $e->getMessage();
        $debug[] = '[aws-error] ' . $out['error'];
    } catch (Throwable $e) {
        $out['error'] = $e->getMessage();
        $debug[] = '[error] ' . $out['error'];
    }

    $elapsedMs = (int) round((microtime(true) - $started) * 1000);
    $debug[] = '[timing] elapsed_ms=' . $elapsedMs;
    $out['debug'] = $debug;

    return $out;
}

/**
 * Key must be under configured root prefix (prevents downloading arbitrary objects).
 */
function s3_inspector_key_allowed(string $key, string $rootPrefix): bool
{
    $root = s3_inspector_normalize_root_prefix($rootPrefix);
    if ($root === '') {
        return $key !== '';
    }
    return str_starts_with($key, $root);
}

/**
 * Stream an S3 object to the browser (proxy download).
 * Tries authenticated SDK streaming first, then presigned+curl for picky gateways.
 *
 * @throws RuntimeException with code 404 when the object is missing
 */
function s3_inspector_stream_object_to_browser(array $session, string $key, ?string $rangeHeader = null): void
{
    $client = s3_inspector_create_client($session, [
        'timeout' => 0,
        'read_timeout' => 0,
    ]);
    $bucket = (string) $session['bucket'];

    try {
        $head = $client->headObject([
            'Bucket' => $bucket,
            'Key' => $key,
        ]);
    } catch (AwsException $e) {
        $code = ($e->getAwsErrorCode() === 'NoSuchKey' || $e->getStatusCode() === 404) ? 404 : 500;
        throw new RuntimeException($e->getAwsErrorMessage() ?: 'Object not found.', $code);
    }

    $filename = basename($key);
    $contentType = $head['ContentType'] ?? 'application/octet-stream';
    header('Content-Type: ' . $contentType);
    header('Content-Disposition: attachment; filename="' . str_replace('"', '', $filename) . '"');
    header('Accept-Ranges: bytes');
    header('X-Accel-Buffering: no');
    if (isset($head['ContentLength'])) {
        header('Content-Length: ' . (int) $head['ContentLength']);
    }
    if (isset($head['ETag'])) {
        header('ETag: ' . $head['ETag']);
    }

    $getParams = [
        'Bucket' => $bucket,
        'Key' => $key,
    ];
    if ($rangeHeader !== null && $rangeHeader !== '' && preg_match('/^bytes=\d*-\d*$/', $rangeHeader)) {
        $getParams['Range'] = $rangeHeader;
    }

    try {
        $result = $client->getObject($getParams);
        if (isset($result['ContentRange'])) {
            http_response_code(206);
            header('Content-Range: ' . $result['ContentRange']);
        }
        if (isset($result['ContentLength'])) {
            header('Content-Length: ' . (int) $result['ContentLength']);
        }
        $body = $result['Body'];
        if (is_resource($body)) {
            fpassthru($body);
        } else {
            while (!$body->eof()) {
                echo $body->read(65536);
                @flush();
            }
        }
        return;
    } catch (AwsException $e) {
        // Fall through to presigned curl streaming below.
    }

    if (function_exists('curl_init')) {
        $cmd = $client->getCommand('GetObject', $getParams);
        $signed = $client->createPresignedRequest($cmd, '+600 seconds');
        $signedUrl = (string) $signed->getUri();
        if ($signedUrl !== '') {
            $ch = curl_init($signedUrl);
            curl_setopt_array($ch, [
                CURLOPT_WRITEFUNCTION => static function ($curl, string $data): int {
                    echo $data;
                    @flush();
                    return strlen($data);
                },
                CURLOPT_FOLLOWLOCATION => true,
                CURLOPT_CONNECTTIMEOUT => 30,
                CURLOPT_TIMEOUT => 0,
                CURLOPT_USERAGENT => 'ScientistCloud-Portal/s3-download',
            ]);
            if (isset($getParams['Range'])) {
                curl_setopt($ch, CURLOPT_RANGE, preg_replace('/^bytes=/', '', $getParams['Range']));
            }
            $ok = curl_exec($ch);
            $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $curlError = curl_error($ch);
            curl_close($ch);
            if ($ok && in_array($httpCode, [200, 206], true)) {
                return;
            }
            throw new RuntimeException(
                'Download failed: HTTP ' . $httpCode . ($curlError !== '' ? ' (' . $curlError . ')' : '')
            );
        }
    }

    throw new RuntimeException('Download failed.');
}

/**
 *
 * Ceph/RGW and similar gateways often return HTTP 200/206 bodies that the AWS SDK
 * rejects on GetObject+SaveAs ("AWS HTTP error: (server): 200 OK"). Presigned URL
 * + curl matches s3-download.php preview handling and works on those endpoints.
 */
function s3_inspector_download_object_to_file(
    S3Client $client,
    string $bucket,
    string $key,
    string $localPath
): void {
    if (function_exists('curl_init')) {
        $cmd = $client->getCommand('GetObject', [
            'Bucket' => $bucket,
            'Key' => $key,
        ]);
        $signed = $client->createPresignedRequest($cmd, '+600 seconds');
        $signedUrl = (string) $signed->getUri();
        if ($signedUrl === '') {
            throw new RuntimeException('Could not create presigned download URL for ' . $key);
        }

        $fp = fopen($localPath, 'wb');
        if ($fp === false) {
            throw new RuntimeException('Could not open temp file for ' . $key);
        }

        $ch = curl_init($signedUrl);
        curl_setopt_array($ch, [
            CURLOPT_FILE => $fp,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_CONNECTTIMEOUT => 30,
            CURLOPT_TIMEOUT => 0,
            CURLOPT_USERAGENT => 'ScientistCloud-Portal/s3-folder-zip',
        ]);
        $ok = curl_exec($ch);
        $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlError = curl_error($ch);
        curl_close($ch);
        fclose($fp);

        if (!$ok || !in_array($httpCode, [200, 206], true)) {
            @unlink($localPath);
            throw new RuntimeException(
                'Download failed for ' . $key . ': HTTP ' . $httpCode
                . ($curlError !== '' ? ' (' . $curlError . ')' : '')
            );
        }
        return;
    }

    $client->getObject([
        'Bucket' => $bucket,
        'Key' => $key,
        'SaveAs' => $localPath,
    ]);
}
