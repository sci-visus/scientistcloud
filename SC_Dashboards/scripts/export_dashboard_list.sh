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
      "description": .value.display_name,
      "port": .value.port,
      "nginx_path": .value.nginx_path,
      "url_template": ((.value.nginx_path | if endswith("/") then . else . + "/" end) + "?uuid={uuid}&server={server}&name={name}"),
      "enabled": .value.enabled,
      "config_file": .value.config_file
    }
  ]
} | .dashboards |= map(select(.enabled == true))' \
"$REGISTRY_FILE" > "$OUTPUT_FILE.tmp"

# Enrich entries from per-dashboard JSON (description, type, etc.)
export DASHBOARDS_DIR CONFIG_DIR OUTPUT_FILE
python3 <<'PY'
import json
import os

tmp = os.path.join(os.environ["CONFIG_DIR"], "dashboards-list.json.tmp")
out = os.environ.get("OUTPUT_FILE", os.path.join(os.environ["CONFIG_DIR"], "dashboards-list.json"))
dashboards_dir = os.environ["DASHBOARDS_DIR"]

with open(tmp, encoding="utf-8") as f:
    data = json.load(f)

for entry in data.get("dashboards", []):
    dash_id = entry.get("id") or ""
    path = os.path.join(dashboards_dir, f"{dash_id}.json")
    if not os.path.isfile(path):
        entry.setdefault("description", f"Dashboard for {entry.get('display_name', dash_id)}")
        continue
    with open(path, encoding="utf-8") as jf:
        extra = json.load(jf)
    if extra.get("description"):
        entry["description"] = extra["description"]
    if extra.get("type"):
        entry["type"] = extra["type"]
    entry.setdefault("description", f"Dashboard for {entry.get('display_name', dash_id)}")

with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

rm -f "$OUTPUT_FILE.tmp"

echo "✅ Exported dashboard list to: $OUTPUT_FILE"
echo "   Total dashboards: $(jq '.dashboards | length' "$OUTPUT_FILE")"

