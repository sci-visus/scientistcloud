#!/bin/bash
# Build a dashboard Docker image
# Usage: ./build_dashboard.sh <dashboard_name> [tag]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"

# Try multiple possible paths for SCLib_Dashboards
SCLIB_DASHBOARDS_DIR=""
POSSIBLE_PATHS=(
    "$SCRIPT_DIR/../../scientistCloudLib/SCLib_Dashboards"
    "$SCRIPT_DIR/../../../scientistCloudLib/SCLib_Dashboards"
    "/Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards"
    "$(cd "$SCRIPT_DIR/../.." && pwd)/scientistCloudLib/SCLib_Dashboards"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        SCLIB_DASHBOARDS_DIR="$(cd "$path" && pwd)"
        break
    fi
done

if [ -z "$SCLIB_DASHBOARDS_DIR" ]; then
    echo "Warning: SCLib_Dashboards directory not found. Shared utilities will not be copied."
    echo "   Tried paths:"
    for path in "${POSSIBLE_PATHS[@]}"; do
        echo "     - $path"
    done
    SCLIB_DASHBOARDS_DIR=""
fi

if [ -z "$1" ]; then
    echo "Usage: $0 <dashboard_name> [tag]"
    exit 1
fi

DASHBOARD_NAME="$1"
TAG="${2:-latest}"

# Flat structure: {name}.json in dashboards directory
# Try exact name first, then try lowercase/underscore variants
CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.json"
if [ ! -f "$CONFIG_FILE" ]; then
    # Try lowercase with underscores (e.g., 4D_Dashboard -> 4d_dashboard)
    DASHBOARD_NAME_LOWER=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')
    CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME_LOWER}.json"
    if [ -f "$CONFIG_FILE" ]; then
        DASHBOARD_NAME="$DASHBOARD_NAME_LOWER"
    fi
fi
DASHBOARD_DIR="$DASHBOARDS_DIR"
DOCKERFILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.Dockerfile"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Dashboard configuration not found: $CONFIG_FILE"
    exit 1
fi

if [ ! -f "$DOCKERFILE" ]; then
    echo "Generating Dockerfile first..."
    "$SCRIPT_DIR/generate_dockerfile.sh" "$DASHBOARD_NAME"
fi

# Load configuration
BASE_IMAGE=$(jq -r '.base_image' "$CONFIG_FILE")
BASE_IMAGE_TAG=$(jq -r '.base_image_tag // "latest"' "$CONFIG_FILE")
IMAGE_NAME=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')
BUILD_ARGS=$(jq -r '.build_args // {} | to_entries | map("--build-arg \(.key)=\(.value)") | join(" ")' "$CONFIG_FILE")

# Handle empty BUILD_ARGS (jq returns empty string if no build_args)
if [ -z "$BUILD_ARGS" ] || [ "$BUILD_ARGS" = "null" ]; then
    BUILD_ARGS=""
fi

# Build Docker image
echo "Building dashboard image: $IMAGE_NAME:$TAG"
echo "Base image: $BASE_IMAGE:$BASE_IMAGE_TAG"

# Detect platform - base images are amd64, so we need to build for amd64 on ARM Macs
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    PLATFORM="linux/amd64"
    echo "Detected ARM architecture, building for linux/amd64 to match base images"
else
    PLATFORM="linux/amd64"  # Base images are amd64, so always use that
fi

# Build context includes dashboard directory and shared utilities
BUILD_CONTEXT=$(mktemp -d)
trap "rm -rf $BUILD_CONTEXT" EXIT

# Copy dashboard files (flat structure)
ENTRY_POINT=$(jq -r '.entry_point' "$CONFIG_FILE")
REQUIREMENTS_FILE=$(jq -r '.requirements_file // empty' "$CONFIG_FILE")

# Copy entry point
if [ -f "$DASHBOARDS_DIR/$ENTRY_POINT" ]; then
    cp "$DASHBOARDS_DIR/$ENTRY_POINT" "$BUILD_CONTEXT/$ENTRY_POINT"
elif [ -f "$DASHBOARDS_DIR/${DASHBOARD_NAME}.py" ]; then
    cp "$DASHBOARDS_DIR/${DASHBOARD_NAME}.py" "$BUILD_CONTEXT/${DASHBOARD_NAME}.py"
    ENTRY_POINT="${DASHBOARD_NAME}.py"
elif [ -f "$DASHBOARDS_DIR/${DASHBOARD_NAME}.ipynb" ]; then
    cp "$DASHBOARDS_DIR/${DASHBOARD_NAME}.ipynb" "$BUILD_CONTEXT/${DASHBOARD_NAME}.ipynb"
    ENTRY_POINT="${DASHBOARD_NAME}.ipynb"
fi

# Copy requirements if exists
# Try multiple naming patterns for requirements file
REQUIREMENTS_COPIED=false
if [ -n "$REQUIREMENTS_FILE" ] && [ -f "$DASHBOARDS_DIR/$REQUIREMENTS_FILE" ]; then
    cp "$DASHBOARDS_DIR/$REQUIREMENTS_FILE" "$BUILD_CONTEXT/requirements.txt"
    REQUIREMENTS_COPIED=true
elif [ -f "$DASHBOARDS_DIR/${DASHBOARD_NAME}_requirements.txt" ]; then
    cp "$DASHBOARDS_DIR/${DASHBOARD_NAME}_requirements.txt" "$BUILD_CONTEXT/requirements.txt"
    REQUIREMENTS_COPIED=true
elif [ -f "$DASHBOARDS_DIR/requirements.txt" ]; then
    cp "$DASHBOARDS_DIR/requirements.txt" "$BUILD_CONTEXT/requirements.txt"
    REQUIREMENTS_COPIED=true
fi

# If no requirements file found, generate one from additional_requirements if available
if [ "$REQUIREMENTS_COPIED" = false ]; then
    ADDITIONAL_REQUIREMENTS=$(jq -r '.additional_requirements // [] | .[]' "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$ADDITIONAL_REQUIREMENTS" ]; then
        # Write additional requirements one per line to requirements.txt
        > "$BUILD_CONTEXT/requirements.txt"  # Clear/create file
        while IFS= read -r req; do
            if [ -n "$req" ]; then
                echo "$req" >> "$BUILD_CONTEXT/requirements.txt"
            fi
        done <<< "$ADDITIONAL_REQUIREMENTS"
        echo "Generated requirements.txt from additional_requirements"
        REQUIREMENTS_COPIED=true
    else
        echo "Warning: No requirements.txt file found for $DASHBOARD_NAME"
        echo "   Tried: $REQUIREMENTS_FILE"
        echo "   Tried: ${DASHBOARD_NAME}_requirements.txt"
        echo "   Tried: requirements.txt"
        echo "   Creating empty requirements.txt"
        touch "$BUILD_CONTEXT/requirements.txt"
    fi
fi

# Ensure requirements.txt always exists (even if empty) for Dockerfile COPY
if [ ! -f "$BUILD_CONTEXT/requirements.txt" ]; then
    touch "$BUILD_CONTEXT/requirements.txt"
fi

# Verify requirements.txt exists and log its contents for debugging
if [ -f "$BUILD_CONTEXT/requirements.txt" ]; then
    REQUIREMENTS_SIZE=$(wc -l < "$BUILD_CONTEXT/requirements.txt" 2>/dev/null || echo "0")
    echo "📄 Created requirements.txt in build context ($REQUIREMENTS_SIZE lines)"
    if [ "$REQUIREMENTS_SIZE" -gt 0 ]; then
        echo "   First few lines:"
        head -3 "$BUILD_CONTEXT/requirements.txt" | sed 's/^/      /' || true
    else
        echo "   (empty file - will skip pip install)"
    fi
else
    echo "❌ ERROR: requirements.txt not created in build context!"
    exit 1
fi

# Copy shared utilities
if [ -n "$SCLIB_DASHBOARDS_DIR" ] && [ -d "$SCLIB_DASHBOARDS_DIR" ]; then
    mkdir -p "$BUILD_CONTEXT/SCLib_Dashboards"
    cp -r "$SCLIB_DASHBOARDS_DIR"/* "$BUILD_CONTEXT/SCLib_Dashboards/" 2>/dev/null || true
fi

# Copy Dockerfile
if [ -f "$DOCKERFILE" ]; then
    cp "$DOCKERFILE" "$BUILD_CONTEXT/Dockerfile"
    echo "📋 Copied Dockerfile to build context"
else
    echo "Error: Dockerfile not found: $DOCKERFILE"
    echo "   Run: ./scripts/generate_dockerfile.sh $DASHBOARD_NAME"
    exit 1
fi

# List build context contents for debugging
echo "📦 Build context contents:"
ls -la "$BUILD_CONTEXT" | grep -E "(requirements|Dockerfile|\.py|\.ipynb)" | sed 's/^/   /' || true

# Build image with platform specification to match base images (amd64)
if [ -n "$BUILD_ARGS" ]; then
    docker build \
        --platform "$PLATFORM" \
        -f "$BUILD_CONTEXT/Dockerfile" \
        -t "${IMAGE_NAME}:${TAG}" \
        $BUILD_ARGS \
        "$BUILD_CONTEXT"
else
    docker build \
        --platform "$PLATFORM" \
        -f "$BUILD_CONTEXT/Dockerfile" \
        -t "${IMAGE_NAME}:${TAG}" \
        "$BUILD_CONTEXT"
fi

echo "✅ Built dashboard image: $IMAGE_NAME:$TAG"

