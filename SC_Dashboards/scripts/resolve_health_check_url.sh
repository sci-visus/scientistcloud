#!/bin/bash
# Resolve Docker health-check URL for a dashboard service.
# Usage: resolve_dashboard_health_url <port> <type> <entry_point> [health_check_path]

resolve_dashboard_health_url() {
    local port="$1"
    local dtype="$2"
    local entry="$3"
    local hpath="${4:-}"

    local app_base
    app_base="$(basename "$entry" .py)"
    app_base="$(basename "$app_base" .ipynb)"

    local is_bokeh_like=false
    if [ "$dtype" = "bokeh" ] || [ "$dtype" = "panel" ]; then
        is_bokeh_like=true
    fi

    if [ -z "$hpath" ] || [ "$hpath" = "null" ]; then
        if [ "$is_bokeh_like" = true ] && [ -n "$app_base" ]; then
            echo "http://localhost:${port}/${app_base}/"
        else
            echo "http://localhost:${port}/"
        fi
        return 0
    fi

    # Default "/health" in JSON: probe Bokeh *server* root, not /AppName/.
    # Hitting /AppName/ runs the full app script (auth, OpenVisus LoadDataset) every 30s.
    if [ "$is_bokeh_like" = true ] && [ "$hpath" = "/health" ]; then
        echo "http://localhost:${port}/"
        return 0
    fi

    # Dash/Plotly dashboards often have no /health route; probe the app root.
    if [ "$is_bokeh_like" = false ] && [ "$hpath" = "/health" ]; then
        echo "http://localhost:${port}/"
        return 0
    fi

    echo "http://localhost:${port}${hpath}"
}
