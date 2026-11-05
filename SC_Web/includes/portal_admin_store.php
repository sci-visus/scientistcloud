<?php
/**
 * Portal administrator dashboard storage.
 * Talks to Mongo through includes/portal_mongo.py (PyMongo is installed in the
 * portal image; the PHP MongoDB extension is not).
 */

function portal_mongo_call(array $command): array {
    $script = __DIR__ . '/portal_mongo.py';
    if (!is_file($script)) {
        throw new RuntimeException('portal_mongo.py is missing');
    }
    $python = 'python3';
    $descriptors = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];
    $env = [];
    foreach ($_SERVER as $key => $value) {
        if (is_string($key) && is_string($value)) {
            $env[$key] = $value;
        }
    }
    $env['MONGO_URL'] = defined('MONGO_URL') ? MONGO_URL : (getenv('MONGO_URL') ?: '');
    $env['PORTAL_DB_NAME'] = defined('DB_NAME') ? DB_NAME : (getenv('DB_NAME') ?: 'scientistcloud');
    $env['PATH'] = getenv('PATH') ?: '/usr/local/bin:/usr/bin:/bin';

    $process = proc_open([$python, $script], $descriptors, $pipes, __DIR__, $env);
    if (!is_resource($process)) {
        throw new RuntimeException('Could not start portal_mongo.py');
    }
    fwrite($pipes[0], json_encode($command));
    fclose($pipes[0]);
    $stdout = stream_get_contents($pipes[1]);
    $stderr = stream_get_contents($pipes[2]);
    fclose($pipes[1]);
    fclose($pipes[2]);
    $exit = proc_close($process);
    $decoded = json_decode($stdout ?: '', true);
    if (!is_array($decoded) || empty($decoded['ok'])) {
        $detail = is_array($decoded) ? ($decoded['error'] ?? '') : trim((string) $stderr);
        throw new RuntimeException($detail !== '' ? $detail : 'Mongo helper failed (exit ' . $exit . ')');
    }
    return $decoded['result'] ?? [];
}

function portal_data_directory(): ?string {
    $candidates = [
        getenv('VISUS_DATASETS') ?: '',
        getenv('VISUS_SERVER') ?: '',
        '/mnt/visus_datasets',
    ];
    foreach ($candidates as $path) {
        $path = rtrim((string) $path, "/");
        if ($path !== '' && is_dir($path)) {
            return $path;
        }
    }
    return null;
}

function portal_disk_summary(): array {
    $path = portal_data_directory();
    if ($path === null) {
        return [
            'path' => null,
            'total_bytes' => null,
            'free_bytes' => null,
            'used_bytes' => null,
        ];
    }
    $total = @disk_total_space($path);
    $free = @disk_free_space($path);
    $total = $total === false ? null : (int) $total;
    $free = $free === false ? null : (int) $free;
    $used = ($total !== null && $free !== null) ? max(0, $total - $free) : null;
    return [
        'path' => $path,
        'total_bytes' => $total,
        'free_bytes' => $free,
        'used_bytes' => $used,
    ];
}

function portal_dashboard_catalog(): array {
    $possiblePaths = [
        '/var/www/SC_Dashboards/config/dashboards-list.json',
        __DIR__ . '/../../SC_Dashboards/config/dashboards-list.json',
        __DIR__ . '/../../../scientistcloud/SC_Dashboards/config/dashboards-list.json',
        getenv('HOME') . '/ScientistCloud2.0/scientistcloud/SC_Dashboards/config/dashboards-list.json',
    ];
    $path = null;
    foreach ($possiblePaths as $candidate) {
        if ($candidate && is_file($candidate)) {
            $path = $candidate;
            break;
        }
    }
    $dashboards = [];
    if ($path) {
        $decoded = json_decode((string) file_get_contents($path), true);
        foreach (($decoded['dashboards'] ?? []) as $dashboard) {
            if (($dashboard['enabled'] ?? false) !== true) {
                continue;
            }
            $id = $dashboard['id'] ?? $dashboard['key'] ?? '';
            if ($id === '') {
                continue;
            }
            $dashboards[] = [
                'id' => $id,
                'name' => $dashboard['name'] ?? $id,
            ];
        }
    }
    $dashboards[] = ['id' => 'S3Browser', 'name' => 'S3 Browser'];
    return $dashboards;
}

function portal_space_denial(string $email, ?string $teamUuid, int $incomingBytes): ?string {
    $result = portal_mongo_call([
        'op' => 'space_check',
        'user_email' => $email,
        'team_uuid' => $teamUuid ?: '',
        'incoming_bytes' => $incomingBytes,
    ]);
    if (!empty($result['ok'])) {
        return null;
    }
    return $result['message'] ?? 'Storage allocation exceeded.';
}

function portal_seat_denial(string $teamUuid, array $emails): ?string {
    $result = portal_mongo_call([
        'op' => 'seat_check',
        'team_uuid' => $teamUuid,
        'emails' => array_values($emails),
    ]);
    if (!empty($result['ok'])) {
        return null;
    }
    return $result['message'] ?? 'Team seat limit exceeded.';
}
