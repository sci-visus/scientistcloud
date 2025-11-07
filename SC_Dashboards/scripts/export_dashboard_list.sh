#!/bin/bash
# Export dashboard list in a format the portal can consume
# Usage: ./export_dashboard_list.sh [output_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
REGISTRY_FILE="$CONFIG_DIR/dashboard-registry.json"

if [ -z "$1" ]; then
    OUTPUT_FILE="$CONFIG_DIR/dashboards-list.json"
else
    OUTPUT_FILE="$1"
fi

if [ ! -f "$REGISTRY_FILE" ]; then
    echo "Error: Dashboard registry not found: $REGISTRY_FILE"
    exit 1
fi

# Generate dashboard list with full configuration
# Use the registry key (which matches the filename) as the id
jq '{
  "version": "1.0.0",
  "last_updated": .last_updated,
  "dashboards": [
    .dashboards | to_entries | .[] | 
    {
      "id": .key,
      "name": .value.display_name,
      "type": (if (.value.config_file | test("plotly|Plotly")) then "plotly" elif (.value.config_file | test("bokeh|Bokeh")) then "bokeh" elif (.value.config_file | test("jupyter|Jupyter|notebook")) then "jupyter" elif (.value.config_file | test("vtk|VTK")) then "vtk" else "dash" end),
      "display_name": .value.display_name,
      "description": (try (.value.config_file | . as $config | input | .description) catch "Dashboard description"),
      "port": .value.port,
      "nginx_path": .value.nginx_path,
      "url_template": ((.value.nginx_path | if endswith("/") then . else . + "/" end) + "?uuid={uuid}&server={server}&name={name}"),
      "enabled": .value.enabled,
      "config_file": .value.config_file
    }
  ]
} | .dashboards |= map(select(.enabled == true))' \
"$REGISTRY_FILE" > "$OUTPUT_FILE.tmp"

# Load full configs from individual dashboard.json files (flat structure: {name}.json)
# Pass DASHBOARDS_DIR as environment variable to jq
export DASHBOARDS_DIR
jq --arg dashboards_dir "$DASHBOARDS_DIR" '.dashboards = (.dashboards | map(
  .config_file as $config_file |
  ($config_file | gsub("^\\.\\./dashboards/"; "")) as $config_rel |
  ($config_rel | gsub("\\.json$"; "")) as $dashboard_name |
  ($dashboard_name | split("/") | .[0]) as $dashboard_name_clean |
  (. + (try (($dashboards_dir + "/" + $dashboard_name_clean + ".json") | @json | fromjson) catch {})) |
  .description //= "Dashboard for " + .display_name
))' "$OUTPUT_FILE.tmp" > "$OUTPUT_FILE"

rm -f "$OUTPUT_FILE.tmp"

echo "✅ Exported dashboard list to: $OUTPUT_FILE"
echo "   Total dashboards: $(jq '.dashboards | length' "$OUTPUT_FILE")"

