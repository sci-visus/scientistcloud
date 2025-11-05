#!/bin/bash
# Generate docker-compose service entries for all registered dashboards
# Usage: ./generate_docker_compose.sh [--output <file>] [--append]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"

# Default output file
OUTPUT_FILE=""
APPEND=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output|-o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --append)
            APPEND=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --output, -o <file>  Output file (default: stdout)"
            echo "  --append              Append to existing file (requires --output)"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Output to stdout"
            echo "  $0 --output docker-compose.yml       # Write to file"
            echo "  $0 --output docker-compose.yml --append  # Append to file"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Load dashboard registry
REGISTRY_FILE="$CONFIG_DIR/dashboard-registry.json"
if [ ! -f "$REGISTRY_FILE" ]; then
    echo "Error: Dashboard registry not found: $REGISTRY_FILE"
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed"
    exit 1
fi

# Generate docker-compose entries
COMPOSE_CONTENT=""
COMPOSE_CONTENT="# Dashboard Services - Auto-generated from dashboard-registry.json\n"
COMPOSE_CONTENT="${COMPOSE_CONTENT}# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_docker_compose.sh\n"
COMPOSE_CONTENT="${COMPOSE_CONTENT}# Generated: $(date)\n\n"

# Get all enabled dashboards
DASHBOARDS=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' "$REGISTRY_FILE" 2>/dev/null || echo "")

if [ -z "$DASHBOARDS" ]; then
    echo "No enabled dashboards found in registry"
    exit 0
fi

# Start services section
COMPOSE_CONTENT="${COMPOSE_CONTENT}services:\n"

# Generate service entry for each dashboard
while IFS= read -r DASHBOARD_NAME; do
    # Get dashboard info from registry
    DASHBOARD_INFO=$(jq -r ".dashboards[\"$DASHBOARD_NAME\"]" "$REGISTRY_FILE")
    CONFIG_FILE=$(echo "$DASHBOARD_INFO" | jq -r '.config_file // "unknown"')
    PORT=$(echo "$DASHBOARD_INFO" | jq -r '.port // 8050')
    DISPLAY_NAME=$(echo "$DASHBOARD_INFO" | jq -r '.display_name // "'"$DASHBOARD_NAME"'"')
    
    # Convert relative config_file path to absolute
    if [[ "$CONFIG_FILE" == "../dashboards/"* ]]; then
        CONFIG_FILE="$DASHBOARDS_DIR/${CONFIG_FILE#../dashboards/}"
    elif [[ "$CONFIG_FILE" != /* ]]; then
        CONFIG_FILE="$DASHBOARDS_DIR/$CONFIG_FILE"
    fi
    
    # Load full dashboard config
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Warning: Dashboard config not found: $CONFIG_FILE, skipping $DASHBOARD_NAME"
        continue
    fi
    
    DASHBOARD_CONFIG=$(cat "$CONFIG_FILE")
    
    # Extract values from config
    DOCKERFILE_NAME="${DASHBOARD_NAME}.Dockerfile"
    DOCKERFILE_PATH="$DASHBOARDS_DIR/$DOCKERFILE_NAME"
    
    # Check if Dockerfile exists
    if [ ! -f "$DOCKERFILE_PATH" ]; then
        echo "Warning: Dockerfile not found: $DOCKERFILE_PATH, skipping $DASHBOARD_NAME"
        continue
    fi
    
    BASE_IMAGE=$(echo "$DASHBOARD_CONFIG" | jq -r '.base_image // "python:3.10-slim"')
    BASE_IMAGE_TAG=$(echo "$DASHBOARD_CONFIG" | jq -r '.base_image_tag // "latest"')
    ENTRY_POINT=$(echo "$DASHBOARD_CONFIG" | jq -r '.entry_point // "'"$DASHBOARD_NAME"'.py"')
    ENTRY_POINT_TYPE=$(echo "$DASHBOARD_CONFIG" | jq -r '.entry_point_type // "python"')
    DASHBOARD_TYPE=$(echo "$DASHBOARD_CONFIG" | jq -r '.type // "dash"')
    
    # Get environment variables
    ENV_VARS=$(echo "$DASHBOARD_CONFIG" | jq -r '.environment_variables // {} | to_entries[] | "      - \(.key)=${\(.key)}"' || echo "")
    
    # Get volume mounts
    VOLUME_MOUNTS=$(echo "$DASHBOARD_CONFIG" | jq -r '.volume_mounts // [] | .[] | "      - \(.host):\(.container)"' || echo "")
    # Add default volumes if not specified
    if [ -z "$VOLUME_MOUNTS" ]; then
        VOLUME_MOUNTS="      - \${VISUS_DB}:/mnt/visus_db\n      - \${VISUS_DATASETS}:/mnt/visus_datasets"
    fi
    
    # Get build args
    BUILD_ARGS=$(echo "$DASHBOARD_CONFIG" | jq -r '.build_args // {} | to_entries[] | "        \(.key): ${\(.key)}"' || echo "")
    
    # Get health check path
    HEALTH_CHECK_PATH=$(echo "$DASHBOARD_CONFIG" | jq -r '.health_check_path // "/health"')
    
    # Get depends_on
    DEPENDS_ON=$(echo "$DASHBOARD_CONFIG" | jq -r '.depends_on // [] | .[]' | tr '\n' ' ' || echo "")
    
    # Generate service name (lowercase, replace special chars with underscore)
    SERVICE_NAME=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')
    CONTAINER_NAME="dashboard_${SERVICE_NAME}"
    
    # Build context - use relative path from docker-compose file location
    # docker-compose.yml is in SC_Docker, dashboards are in SC_Dashboards/dashboards
    # So relative path is ../SC_Dashboards/dashboards
    BUILD_CONTEXT="../SC_Dashboards/dashboards"
    
    # Generate docker-compose service entry
    COMPOSE_CONTENT="${COMPOSE_CONTENT}  # ${DISPLAY_NAME}\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}  ${SERVICE_NAME}:\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    container_name: ${CONTAINER_NAME}\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    platform: linux/amd64\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    image: ${SERVICE_NAME}:latest\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    build:\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      context: ${BUILD_CONTEXT}\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      dockerfile: ${DOCKERFILE_NAME}\n"
    
    # Add build args if any
    if [ -n "$BUILD_ARGS" ]; then
        COMPOSE_CONTENT="${COMPOSE_CONTENT}      args:\n"
        while IFS= read -r ARG; do
            if [ -n "$ARG" ]; then
                COMPOSE_CONTENT="${COMPOSE_CONTENT}${ARG}\n"
            fi
        done <<< "$BUILD_ARGS"
    fi
    
    # Environment variables
    if [ -n "$ENV_VARS" ]; then
        COMPOSE_CONTENT="${COMPOSE_CONTENT}    environment:\n"
        while IFS= read -r VAR; do
            if [ -n "$VAR" ]; then
                COMPOSE_CONTENT="${COMPOSE_CONTENT}${VAR}\n"
            fi
        done <<< "$ENV_VARS"
    else
        # Default environment variables
        COMPOSE_CONTENT="${COMPOSE_CONTENT}    environment:\n"
        COMPOSE_CONTENT="${COMPOSE_CONTENT}      - SECRET_KEY=\${SECRET_KEY}\n"
        COMPOSE_CONTENT="${COMPOSE_CONTENT}      - DEPLOY_SERVER=\${DEPLOY_SERVER}\n"
        COMPOSE_CONTENT="${COMPOSE_CONTENT}      - DB_NAME=\${DB_NAME}\n"
        COMPOSE_CONTENT="${COMPOSE_CONTENT}      - MONGO_URL=\${MONGO_URL}\n"
        COMPOSE_CONTENT="${COMPOSE_CONTENT}      - DOMAIN_NAME=\${DOMAIN_NAME}\n"
    fi
    
    # Networks
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    networks:\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      - docker_visstore_web\n"
    
    # Restart policy
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    restart: unless-stopped\n"
    
    # Volumes
    if [ -n "$VOLUME_MOUNTS" ]; then
        COMPOSE_CONTENT="${COMPOSE_CONTENT}    volumes:\n"
        while IFS= read -r VOL; do
            if [ -n "$VOL" ]; then
                COMPOSE_CONTENT="${COMPOSE_CONTENT}${VOL}\n"
            fi
        done <<< "$VOLUME_MOUNTS"
    fi
    
    # Health check
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    healthcheck:\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:${PORT}${HEALTH_CHECK_PATH}\"]\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      interval: 30s\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      timeout: 10s\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      retries: 3\n"
    COMPOSE_CONTENT="${COMPOSE_CONTENT}      start_period: 40s\n"
    
    # Init
    COMPOSE_CONTENT="${COMPOSE_CONTENT}    init: true\n"
    
    # Depends on
    if [ -n "$DEPENDS_ON" ]; then
        COMPOSE_CONTENT="${COMPOSE_CONTENT}    depends_on:\n"
        for dep in $DEPENDS_ON; do
            COMPOSE_CONTENT="${COMPOSE_CONTENT}      - ${dep}\n"
        done
    fi
    
    COMPOSE_CONTENT="${COMPOSE_CONTENT}\n"
    
done <<< "$DASHBOARDS"

# Add networks section at the end (docker_visstore_web is external)
COMPOSE_CONTENT="${COMPOSE_CONTENT}\n"
COMPOSE_CONTENT="${COMPOSE_CONTENT}networks:\n"
COMPOSE_CONTENT="${COMPOSE_CONTENT}  docker_visstore_web:\n"
COMPOSE_CONTENT="${COMPOSE_CONTENT}    external: true\n"

# Output
if [ -z "$OUTPUT_FILE" ]; then
    # Output to stdout
    echo -e "$COMPOSE_CONTENT"
else
    # Output to file
    if [ "$APPEND" = true ]; then
        echo -e "$COMPOSE_CONTENT" >> "$OUTPUT_FILE"
        echo "✅ Appended dashboard services to: $OUTPUT_FILE"
    else
        echo -e "$COMPOSE_CONTENT" > "$OUTPUT_FILE"
        echo "✅ Generated docker-compose services in: $OUTPUT_FILE"
    fi
fi

