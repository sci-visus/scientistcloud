#!/bin/bash
# List all registered dashboards
# Usage: ./list_dashboards.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
REGISTRY_FILE="$CONFIG_DIR/dashboard-registry.json"

if [ ! -f "$REGISTRY_FILE" ]; then
    echo "No dashboard registry found. Run add_dashboard.sh to add dashboards."
    exit 1
fi

echo "Registered Dashboards:"
echo "======================"
echo ""

jq -r '.dashboards | to_entries | .[] | 
  "Name: \(.value.name)
  Display: \(.value.display_name)
  Port: \(.value.port)
  Path: \(.value.nginx_path)
  Enabled: \(.value.enabled)
  Config: \(.value.config_file)
  ---"' "$REGISTRY_FILE"

echo ""
echo "Total: $(jq '.dashboards | length' "$REGISTRY_FILE") dashboard(s)"


