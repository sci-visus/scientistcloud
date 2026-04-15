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

function s3_inspector_create_client(array $session): S3Client
{
    $endpoint = rtrim(trim($session['endpoint']), '/');
    $region = trim($session['region'] ?? 'us-east-1') ?: 'us-east-1';
    $usePathStyle = !empty($session['path_style']);

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
        // Keep calls responsive so the UI does not appear to spin forever.
        'http' => [
            'verify' => true,
            'connect_timeout' => 8,
            'timeout' => 25,
        ],
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
