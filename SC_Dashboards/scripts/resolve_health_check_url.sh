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

    # Default "/health" in JSON targets server root; Bokeh/Panel apps mount under /AppName/.
    # Most dashboards have no /AppName/health route — probe the app index (same as darkmatter/ORNL).
    if [ "$is_bokeh_like" = true ] && [ "$hpath" = "/health" ] && [ -n "$app_base" ]; then
        echo "http://localhost:${port}/${app_base}/"
        return 0
    fi

    # Dash/Plotly dashboards often have no /health route; probe the app root.
    if [ "$is_bokeh_like" = false ] && [ "$hpath" = "/health" ]; then
        echo "http://localhost:${port}/"
        return 0
    fi

    echo "http://localhost:${port}${hpath}"
}
