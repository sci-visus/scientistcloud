#!/bin/bash
# Build ScientistCloud dashboard base images (no VisusDataPortalPrivate dependency).
# Usage: ./build-base-images.sh [--only bokeh|plotly|4d]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"
ONLY="${1:-}"

build_one() {
    local name="$1"
    local dockerfile="$2"
    local tag="$3"
    echo "════════════════════════════════════════"
    echo "🐳 Building $tag"
    echo "════════════════════════════════════════"
    docker build \
        --platform "$PLATFORM" \
        -f "$dockerfile" \
        -t "$tag" \
        .
    echo "✅ $tag"
}

if [ "$ONLY" = "--only" ] && [ -n "${2:-}" ]; then
    case "$2" in
        bokeh) build_one "bokeh" Dockerfile.bokeh-dashboard-base sc-bokeh-dashboard-base:latest ;;
        plotly) build_one "plotly" Dockerfile.plotly-dashboard-base sc-plotly-dashboard-base:latest ;;
        4d) build_one "4d" Dockerfile.4d-dashboard-base sc-4d-dashboard-base:latest ;;
        *) echo "Unknown: $2 (use bokeh, plotly, or 4d)"; exit 1 ;;
    esac
    exit 0
fi

build_one "bokeh" Dockerfile.bokeh-dashboard-base sc-bokeh-dashboard-base:latest
build_one "plotly" Dockerfile.plotly-dashboard-base sc-plotly-dashboard-base:latest
build_one "4d" Dockerfile.4d-dashboard-base sc-4d-dashboard-base:latest

echo ""
echo "✅ All SC dashboard base images built:"
docker images --format '  {{.Repository}}:{{.Tag}}' | grep -E '^  sc-(bokeh|plotly|4d)-dashboard-base:' || true
