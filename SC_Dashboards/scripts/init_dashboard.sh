#!/bin/bash
# Initialize a dashboard - generates Dockerfile, nginx config, and optionally builds
# Usage: ./init_dashboard.sh <dashboard_name> [--overwrite] [--build] [--skip-build]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
DASHBOARD_NAME=""
OVERWRITE=false
BUILD_IMAGE=false
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --overwrite)
            OVERWRITE=true
            shift
            ;;
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <dashboard_name> [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --overwrite    Overwrite existing files (Dockerfile, nginx config)"
            echo "  --build        Build Docker image after generating files"
            echo "  --skip-build   Skip Docker image build (default)"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 3DPlotly                    # Generate files, skip build"
            echo "  $0 3DPlotly --overwrite        # Overwrite existing files"
            echo "  $0 3DPlotly --build            # Generate files and build image"
            echo "  $0 3DPlotly --overwrite --build # Overwrite and build"
            exit 0
            ;;
        *)
            if [ -z "$DASHBOARD_NAME" ]; then
                DASHBOARD_NAME="$1"
            else
                echo -e "${RED}Error: Unknown option or multiple dashboard names: $1${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$DASHBOARD_NAME" ]; then
    echo -e "${RED}Error: Dashboard name is required${NC}"
    echo "Usage: $0 <dashboard_name> [--overwrite] [--build] [--skip-build]"
    echo "Run '$0 --help' for more information"
    exit 1
fi

# Check if dashboard config exists
# Try exact name first, then try lowercase/underscore variants
CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.json"
if [ ! -f "$CONFIG_FILE" ]; then
    # Try lowercase with underscores (e.g., 4D_Dashboard -> 4d_dashboard)
    DASHBOARD_NAME_LOWER=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')
    CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME_LOWER}.json"
    if [ ! -f "$CONFIG_FILE" ]; then
        # Try original lowercase without transformation
        CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.json"
        echo -e "${RED}Error: Dashboard configuration not found: $CONFIG_FILE${NC}"
        echo "   Tried: $DASHBOARDS_DIR/${DASHBOARD_NAME}.json"
        echo "   Tried: $DASHBOARDS_DIR/${DASHBOARD_NAME_LOWER}.json"
        echo "Please create the dashboard.json file first or run add_dashboard.sh"
        exit 1
    else
        # Found it with lowercase name, update DASHBOARD_NAME for rest of script
        echo -e "${YELLOW}⚠️  Found config with lowercase name: ${DASHBOARD_NAME_LOWER}.json${NC}"
        DASHBOARD_NAME="$DASHBOARD_NAME_LOWER"
    fi
fi

echo -e "${BLUE}=== Initializing Dashboard: $DASHBOARD_NAME ===${NC}"
echo ""

# Step 1: Generate Dockerfile
DOCKERFILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.Dockerfile"
if [ -f "$DOCKERFILE" ] && [ "$OVERWRITE" = false ]; then
    echo -e "${YELLOW}⚠️  Dockerfile already exists: $DOCKERFILE${NC}"
    echo -e "${YELLOW}   Skipping... (use --overwrite to regenerate)${NC}"
else
    echo -e "${GREEN}📝 Step 1: Generating Dockerfile...${NC}"
    if "$SCRIPT_DIR/generate_dockerfile.sh" "$DASHBOARD_NAME"; then
        echo -e "${GREEN}✅ Dockerfile generated: $DOCKERFILE${NC}"
    else
        echo -e "${RED}❌ Failed to generate Dockerfile${NC}"
        exit 1
    fi
fi
echo ""

# Step 2: Generate nginx configuration
# First, try to find existing nginx config
NGINX_CONFIG=""
POSSIBLE_NGINX_PATHS=(
    "$SCRIPT_DIR/../SC_Docker/nginx/conf.d/${DASHBOARD_NAME}_dashboard.conf"
    "$SCRIPT_DIR/../../SC_Docker/nginx/conf.d/${DASHBOARD_NAME}_dashboard.conf"
    "$SCRIPT_DIR/../../../scientistcloud/SC_Docker/nginx/conf.d/${DASHBOARD_NAME}_dashboard.conf"
    "$SCRIPT_DIR/../nginx/conf.d/${DASHBOARD_NAME}_dashboard.conf"
    "/Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Docker/nginx/conf.d/${DASHBOARD_NAME}_dashboard.conf"
)

for path in "${POSSIBLE_NGINX_PATHS[@]}"; do
    if [ -f "$path" ]; then
        NGINX_CONFIG="$path"
        break
    fi
done

# If not found, use first path as potential location for checking
if [ -z "$NGINX_CONFIG" ]; then
    NGINX_CONFIG="${POSSIBLE_NGINX_PATHS[0]}"
fi

if [ -f "$NGINX_CONFIG" ] && [ "$OVERWRITE" = false ]; then
    echo -e "${YELLOW}⚠️  Nginx config already exists: $NGINX_CONFIG${NC}"
    echo -e "${YELLOW}   Skipping... (use --overwrite to regenerate)${NC}"
else
    echo -e "${GREEN}📝 Step 2: Generating nginx configuration...${NC}"
    if "$SCRIPT_DIR/generate_nginx_config.sh" "$DASHBOARD_NAME"; then
        # Find the actual generated file
        NGINX_CONFIG=""
        for path in "${POSSIBLE_NGINX_PATHS[@]}"; do
            if [ -f "$path" ]; then
                NGINX_CONFIG="$path"
                echo -e "${GREEN}✅ Nginx config generated: $NGINX_CONFIG${NC}"
                break
            fi
        done
        if [ -z "$NGINX_CONFIG" ] || [ ! -f "$NGINX_CONFIG" ]; then
            echo -e "${YELLOW}⚠️  Nginx config generated but location not found${NC}"
            echo -e "${YELLOW}   Check: ${POSSIBLE_NGINX_PATHS[*]}${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to generate nginx configuration${NC}"
        exit 1
    fi
fi
echo ""

# Step 3: Build Docker image (optional)
if [ "$SKIP_BUILD" = true ]; then
    echo -e "${YELLOW}⏭️  Step 3: Skipping Docker image build (--skip-build)${NC}"
elif [ "$BUILD_IMAGE" = true ]; then
    echo -e "${GREEN}🐳 Step 3: Building Docker image...${NC}"
    if "$SCRIPT_DIR/build_dashboard.sh" "$DASHBOARD_NAME"; then
        echo -e "${GREEN}✅ Docker image built successfully${NC}"
    else
        echo -e "${RED}❌ Failed to build Docker image${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⏭️  Step 3: Skipping Docker image build (use --build to build)${NC}"
fi
echo ""

# Step 4: Export dashboard list for portal
echo -e "${GREEN}📋 Step 4: Exporting dashboard list for portal...${NC}"
if "$SCRIPT_DIR/export_dashboard_list.sh"; then
    echo -e "${GREEN}✅ Dashboard list exported${NC}"
else
    echo -e "${YELLOW}⚠️  Failed to export dashboard list (non-fatal)${NC}"
fi
echo ""

# Step 5: Generate docker-compose entries (optional)
DOCKER_COMPOSE_FILE=""
POSSIBLE_COMPOSE_PATHS=(
    "$SCRIPT_DIR/../SC_Docker/docker-compose.yml"
    "$SCRIPT_DIR/../../SC_Docker/docker-compose.yml"
    "$SCRIPT_DIR/../../../scientistcloud/SC_Docker/docker-compose.yml"
    "/Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Docker/docker-compose.yml"
)

for path in "${POSSIBLE_COMPOSE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        DOCKER_COMPOSE_FILE="$path"
        break
    fi
done

if [ -n "$DOCKER_COMPOSE_FILE" ]; then
    echo -e "${GREEN}📦 Step 5: Generating docker-compose entries...${NC}"
    echo -e "${BLUE}   Main docker-compose: $DOCKER_COMPOSE_FILE${NC}"
    echo -e "${YELLOW}   Note: Dashboard services generated separately.${NC}"
    echo -e "${YELLOW}   To integrate, run:${NC}"
    echo -e "${YELLOW}     ./scripts/generate_docker_compose.sh --output dashboards-docker-compose.yml${NC}"
    echo -e "${YELLOW}     Then merge or use: docker-compose -f docker-compose.yml -f dashboards-docker-compose.yml${NC}"
else
    echo -e "${YELLOW}⏭️  Step 5: Skipping docker-compose generation (file not found)${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
echo -e "${GREEN}✅ Dashboard initialization complete: $DASHBOARD_NAME${NC}"
echo ""
echo "Generated files:"
if [ -f "$DOCKERFILE" ]; then
    echo -e "  ${GREEN}✓${NC} Dockerfile: $DOCKERFILE"
else
    echo -e "  ${RED}✗${NC} Dockerfile: Not generated"
fi

if [ -n "$NGINX_CONFIG" ] && [ -f "$NGINX_CONFIG" ]; then
    echo -e "  ${GREEN}✓${NC} Nginx config: $NGINX_CONFIG"
else
    echo -e "  ${YELLOW}?${NC} Nginx config: Location unknown"
fi

if [ -f "$CONFIG_DIR/dashboards-list.json" ]; then
    echo -e "  ${GREEN}✓${NC} Dashboard list: $CONFIG_DIR/dashboards-list.json"
fi

echo ""
echo "Next steps:"
if [ "$BUILD_IMAGE" = false ]; then
    echo "  1. Build Docker image: ./scripts/build_dashboard.sh $DASHBOARD_NAME"
fi
if [ -n "$DOCKER_COMPOSE_FILE" ]; then
    echo "  2. Generate docker-compose entries:"
    echo "     ./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml"
    echo "  3. Integrate into docker-compose.yml (or use separate file)"
    echo "  4. Restart services: docker-compose up -d"
else
    echo "  2. Generate docker-compose entries:"
    echo "     ./scripts/generate_docker_compose.sh --output dashboards-docker-compose.yml"
    echo "  3. Update docker-compose.yml to include dashboard services"
    echo "  4. Restart services: docker-compose up -d"
fi

# Get nginx path from config
NGINX_PATH=$(jq -r '.nginx_path' "$CONFIG_FILE" 2>/dev/null || echo "/dashboard/$DASHBOARD_NAME")
echo "  5. Test dashboard: https://scientistcloud.com${NGINX_PATH}"
echo ""

