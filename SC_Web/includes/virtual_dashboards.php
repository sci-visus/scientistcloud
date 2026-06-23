<?php
/**
 * Virtual dashboards that are rendered inside the portal (not separate Bokeh/Plotly services).
 */

declare(strict_types=1);

/**
 * @return array<string, mixed>
 */
function sc_get_s3_browser_dashboard_entry(): array
{
    return [
        'id' => 'S3Browser',
        'name' => 'S3Browser',
        'display_name' => 'S3 Browser',
        'type' => 'S3Browser',
        'enabled' => true,
        'virtual' => true,
        'description' => 'Browse and download files from linked S3 storage',
        'url_template' => '',
        'nginx_path' => '',
    ];
}

/**
 * @param list<array<string, mixed>> $dashboards
 * @return list<array<string, mixed>>
 */
function sc_append_virtual_dashboards(array $dashboards): array
{
    $ids = [];
    foreach ($dashboards as $dashboard) {
        $id = (string) ($dashboard['id'] ?? '');
        if ($id !== '') {
            $ids[$id] = true;
        }
    }

    if (!isset($ids['S3Browser'])) {
        $dashboards[] = sc_get_s3_browser_dashboard_entry();
    }

    return array_values($dashboards);
}
