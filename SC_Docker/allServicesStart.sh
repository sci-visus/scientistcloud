#!/bin/bash
#
# ScientistCloud 2.0 — deploy helper (SC-native; no VisusDataPortalPrivate required)
#
# Usage:
#   ./allServicesStart.sh              Git pull only (all repos + env sync)
#   ./allServicesStart.sh s w d x z    Git pull, then rebuild/restart each part
#   ./allServicesStart.sh swdx         Nginx + dozzle (z is included with x)
#   ./allServicesStart.sh swdxz        Same as swdx
#
# Modes (after git pull):
#   s   SCLib (auth, fastapi, background-service) — rebuild via scientistCloudLib/Docker/start.sh
#   w   SC_Web portal (scientistcloud-portal) — rebuild via SC_Docker/start.sh
#   d   All enabled dashboards — init, build, docker-compose up, nginx configs
#   x   SC edge nginx — scientistcloud-nginx + setup_dashboards_nginx.sh sc (+ dozzle)
#   z   Dozzle log UI (visstore_dozzle) — https://DOMAIN/dozzle/
#
# Long flags (same modes):
#   -s, --sclib-only          SCLib rebuild
#   -w, --web-only            Portal rebuild
#   -sw, --sclib-web          Both
#   -x, --nginx-only          Nginx only (still runs git pull first)
#   -z, --dozzle-only         Dozzle only (container log viewer at /dozzle/)
#   -dm, -vtk, -plotly        Single dashboard (d subset)
#   --dashboards-only         Skip s/w; only dashboard pipeline (+ x if also passed)
#
# Examples:
#   ./allServicesStart.sh
#   ./allServicesStart.sh s w
#   ./allServicesStart.sh d x
#   ./allServicesStart.sh -dm
#   ./allServicesStart.sh --dashboards-only -dm

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DO_SCLIB=false
DO_WEB=false
DO_DASHBOARDS=false
DO_NGINX=false
DO_DOZZLE=false
REBUILD_SCLIB=false
REBUILD_WEB=false
DASHBOARD_ONLY_REGISTRY_KEY=""
DASHBOARD_ONLY_SERVICE=""
DASHBOARD_ONLY_CONTAINER=""
GIT_PULL_ONLY=true

usage() {
    sed -n '3,28p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

parse_letter_mode() {
    local letters="$1"
    local i c
    for ((i = 0; i < ${#letters}; i++)); do
        c="${letters:i:1}"
        case "$c" in
            s|S) GIT_PULL_ONLY=false; DO_SCLIB=true; REBUILD_SCLIB=true ;;
            w|W) GIT_PULL_ONLY=false; DO_WEB=true; REBUILD_WEB=true ;;
            d|D) GIT_PULL_ONLY=false; DO_DASHBOARDS=true ;;
            x|X) GIT_PULL_ONLY=false; DO_NGINX=true; DO_DOZZLE=true ;;
            z|Z) GIT_PULL_ONLY=false; DO_DOZZLE=true ;;
            h|H) usage 0 ;;
            *) echo "❌ Unknown mode letter: $c (use s w d x z)"; usage 1 ;;
        esac
    done
}

for arg in "$@"; do
    case "$arg" in
        -h|--help|help) usage 0 ;;
        -s|--sclib-only)
            GIT_PULL_ONLY=false; DO_SCLIB=true; REBUILD_SCLIB=true
            ;;
        -w|--web-only)
            GIT_PULL_ONLY=false; DO_WEB=true; REBUILD_WEB=true
            ;;
        -sw|--sclib-web|--both)
            GIT_PULL_ONLY=false; DO_SCLIB=true; DO_WEB=true
            REBUILD_SCLIB=true; REBUILD_WEB=true
            ;;
        -x|--nginx-only)
            GIT_PULL_ONLY=false; DO_NGINX=true; DO_DOZZLE=true
            ;;
        -z|--dozzle-only)
            GIT_PULL_ONLY=false; DO_DOZZLE=true
            ;;
        --dashboards-only|--only-dashboards)
            GIT_PULL_ONLY=false; DO_DASHBOARDS=true
            ;;
        -dm|--darkmatter-only)
            GIT_PULL_ONLY=false; DO_DASHBOARDS=true
            DASHBOARD_ONLY_REGISTRY_KEY="darkmatter"
            DASHBOARD_ONLY_SERVICE="darkmatter"
            DASHBOARD_ONLY_CONTAINER="dashboard_darkmatter"
            ;;
        -vtk|--vtk-only|--3dvtk-only)
            GIT_PULL_ONLY=false; DO_DASHBOARDS=true
            DASHBOARD_ONLY_REGISTRY_KEY="3DVTK"
            DASHBOARD_ONLY_SERVICE="3dvtk"
            DASHBOARD_ONLY_CONTAINER="dashboard_3dvtk"
            ;;
        -plotly|--plotly-only|--3dplotly-only)
            GIT_PULL_ONLY=false; DO_DASHBOARDS=true
            DASHBOARD_ONLY_REGISTRY_KEY="3DPlotly"
            DASHBOARD_ONLY_SERVICE="3dplotly"
            DASHBOARD_ONLY_CONTAINER="dashboard_3dplotly"
            ;;
        --skip-main|--portal-only)
            : # no-op; legacy Visus main stack is not started
            ;;
        *)
            if [[ "$arg" =~ ^- ]]; then
                echo "❌ Unknown option: $arg"
                usage 1
            elif [[ "$arg" =~ ^[swdxzSWDXZ]+$ ]]; then
                parse_letter_mode "$arg"
            else
                echo "❌ Unknown argument: $arg"
                usage 1
            fi
            ;;
    esac
done

# Multiple single-letter args: s w d x
if [ "$#" -gt 0 ] && [ "$GIT_PULL_ONLY" = true ]; then
    for arg in "$@"; do
        if [[ "$arg" =~ ^[swdxzSWDXZ]$ ]]; then
            parse_letter_mode "$arg"
        fi
    done
fi

if [ "$#" -gt 0 ]; then
    GIT_PULL_ONLY=false
fi

# --- paths ---
SC20_ROOT=""
for _c in "$HOME/ScientistCloud2.0" "$HOME/ScientistCloud_2.0"; do
    if [ -d "$_c/scientistcloud" ] || [ -d "$_c/scientistCloudLib" ]; then
        SC20_ROOT="$_c"
        break
    fi
done
[ -n "$SC20_ROOT" ] || SC20_ROOT="$HOME/ScientistCloud2.0"

SCLIB_TRYTEST_DIR="$SC20_ROOT/SCLib_TryTest"
SCLIB_CODE_DIR="$SC20_ROOT/scientistCloudLib"
SCLIB_DOCKER_DIR="$SC20_ROOT/scientistCloudLib/Docker"
PORTAL_DOCKER_DIR="$SCRIPT_DIR"
SCIENTISTCLOUD_DIR="$SC20_ROOT/scientistcloud"
DASHBOARDS_DIR="$SCIENTISTCLOUD_DIR/SC_Dashboards"
NGINX_CONTAINER="${SC_NGINX_CONTAINER:-scientistcloud-nginx}"

discover_certbot_paths() {
    local domain="${DOMAIN_NAME:-scientistcloud.com}"
    local cert_root cert_conf
    if [ -n "${SC_CERTBOT_CONF:-}" ] && [ -f "${SC_CERTBOT_CONF}/live/${domain}/fullchain.pem" ]; then
        SC_CERTBOT_WWW="${SC_CERTBOT_WWW:-$(dirname "$SC_CERTBOT_CONF")/www}"
        export SC_CERTBOT_CONF SC_CERTBOT_WWW
        echo "   🔒 SSL certs: $SC_CERTBOT_CONF"
        return 0
    fi
    for cert_root in \
        "$PORTAL_DOCKER_DIR/certbot" \
        "${SC20_HOME:-$HOME/ScientistCloud2.0}/scientistcloud/SC_Docker/certbot"; do
        cert_conf="$cert_root/conf"
        if [ -f "$cert_conf/live/${domain}/fullchain.pem" ]; then
            export SC_CERTBOT_CONF="$cert_conf"
            export SC_CERTBOT_WWW="$cert_root/www"
            echo "   🔒 SSL certs (auto): $SC_CERTBOT_CONF"
            return 0
        fi
    done
    echo "   ⚠️  No Let's Encrypt certs for $domain — set SC_CERTBOT_CONF before mode x"
    return 1
}

load_env() {
    local env_file="$SCLIB_TRYTEST_DIR/env.scientistcloud"
    if [ -f "$env_file" ]; then
        echo "📋 Loading $env_file"
        set -o allexport
        # shellcheck source=/dev/null
        source "$env_file"
        set +o allexport
    else
        echo "⚠️  No env.scientistcloud at $env_file"
    fi
    discover_certbot_paths || true
    if [ -f "$SCLIB_TRYTEST_DIR/env.scientistcloud" ]; then
        cp "$SCLIB_TRYTEST_DIR/env.scientistcloud" "$PORTAL_DOCKER_DIR/.env"
    fi
}

git_pull_all() {
    echo "════════════════════════════════════════"
    echo "📥 Git pull — ScientistCloud 2.0 repos"
    echo "════════════════════════════════════════"

    if [ -d "$SCLIB_TRYTEST_DIR" ]; then
        echo "📦 SCLib_TryTest"
        pushd "$SCLIB_TRYTEST_DIR" >/dev/null
        local bak="/tmp/sc_env_scientistcloud_$$.bak"
        [ -f env.scientistcloud ] && cp env.scientistcloud "$bak"
        git fetch origin
        git reset --hard origin/main
        [ -f "$bak" ] && cp "$bak" env.scientistcloud && rm -f "$bak"
        if [ -f env.scientistcloud ]; then
            cp env.scientistcloud "$SCLIB_DOCKER_DIR/.env"
            cp env.scientistcloud "$PORTAL_DOCKER_DIR/.env"
            echo "   ✅ env → scientistCloudLib/Docker/.env and SC_Docker/.env"
        fi
        popd >/dev/null
    fi

    if [ -d "$SCLIB_CODE_DIR" ]; then
        echo "📦 scientistCloudLib (workingPrivateRepo)"
        pushd "$SCLIB_CODE_DIR" >/dev/null
        git remote get-url origin 2>/dev/null | grep -q sci-visus/scientistCloudLib || \
            git remote set-url origin https://github.com/sci-visus/scientistCloudLib.git 2>/dev/null || true
        git fetch origin
        git checkout workingPrivateRepo 2>/dev/null || git checkout -b workingPrivateRepo origin/workingPrivateRepo
        git reset --hard origin/workingPrivateRepo
        popd >/dev/null
    fi

    if [ -d "$SCIENTISTCLOUD_DIR" ]; then
        echo "📦 scientistcloud (portal + dashboards)"
        if [ -d "$SCIENTISTCLOUD_DIR/SC_Web/vendor" ]; then
            sudo chown -R "$(whoami):$(whoami)" "$SCIENTISTCLOUD_DIR/SC_Web/vendor" 2>/dev/null || true
            if docker ps --format '{{.Names}}' | grep -q '^scientistcloud-portal$'; then
                docker stop scientistcloud-portal 2>/dev/null || true
                sleep 1
            fi
        fi
        pushd "$SCIENTISTCLOUD_DIR" >/dev/null
        local env_bak=""
        if [ -f SC_Docker/.env ]; then
            env_bak="$(mktemp)"
            cp SC_Docker/.env "$env_bak"
        fi
        git fetch origin
        git clean -fd 2>/dev/null || true
        if [ -n "$env_bak" ] && [ -f "$env_bak" ]; then
            mkdir -p SC_Docker
            cp "$env_bak" SC_Docker/.env
            rm -f "$env_bak"
        fi
        if git ls-remote --heads origin workingPrivateRepo 2>/dev/null | grep -q workingPrivateRepo; then
            # -B: attach to branch from detached HEAD; avoids "branch already exists"
            git checkout -B workingPrivateRepo origin/workingPrivateRepo
            git reset --hard origin/workingPrivateRepo
        else
            git checkout -B main origin/main 2>/dev/null || git checkout -f origin/main
            git reset --hard origin/main 2>/dev/null || true
        fi
        popd >/dev/null
        if [ -f "$SCLIB_TRYTEST_DIR/env.scientistcloud" ]; then
            cp "$SCLIB_TRYTEST_DIR/env.scientistcloud" "$PORTAL_DOCKER_DIR/.env"
        fi
        if docker ps -a --format '{{.Names}}' | grep -q '^scientistcloud-portal$'; then
            docker start scientistcloud-portal 2>/dev/null || true
        fi
    fi
    echo "✅ Git pull complete"
}

ensure_docker_network() {
    if ! docker network inspect docker_visstore_web >/dev/null 2>&1; then
        echo "🌐 Creating docker_visstore_web network"
        docker network create docker_visstore_web || true
    fi
}

# Compose files for edge nginx + optional dozzle (SC-native)
nginx_compose_files() {
    local files="-f docker-compose.yml -f docker-compose.nginx.yml"
    if [ -f "$PORTAL_DOCKER_DIR/docker-compose.dozzle.yml" ]; then
        files="$files -f docker-compose.dozzle.yml"
    fi
    echo "$files"
}

mode_dozzle() {
    echo "════════════════════════════════════════"
    echo "🔄 Mode z — Dozzle (visstore_dozzle → /dozzle/)"
    echo "════════════════════════════════════════"
    ensure_docker_network
    pushd "$PORTAL_DOCKER_DIR" >/dev/null
    local compose_files
    compose_files="$(nginx_compose_files)"
    if [ -f docker-compose.dozzle.yml ]; then
        if ! docker compose $compose_files up -d visstore_dozzle 2>&1; then
            docker-compose $compose_files up -d visstore_dozzle 2>&1 || {
                echo "❌ Failed to start visstore_dozzle"
                exit 1
            }
        fi
    else
        echo "⚠️  docker-compose.dozzle.yml missing — starting dozzle via docker run"
        docker rm -f visstore_dozzle 2>/dev/null || true
        docker run -d --name visstore_dozzle --restart unless-stopped \
            --network docker_visstore_web \
            -v /var/run/docker.sock:/var/run/docker.sock:ro \
            amir20/dozzle:latest
    fi
    popd >/dev/null
    if docker ps --format '{{.Names}}' | grep -q '^visstore_dozzle$'; then
        echo "✅ Dozzle: https://${DOMAIN_NAME:-scientistcloud.com}/dozzle/"
    else
        echo "⚠️  visstore_dozzle not running"
    fi
}

mode_sclib() {
    echo "════════════════════════════════════════"
    echo "📦 Mode s — SCLib services"
    echo "════════════════════════════════════════"
    if [ ! -d "$SCLIB_DOCKER_DIR" ]; then
        echo "❌ Missing $SCLIB_DOCKER_DIR"
        exit 1
    fi
    ensure_docker_network
    pushd "$SCLIB_DOCKER_DIR" >/dev/null
    if [ "$REBUILD_SCLIB" = true ]; then
        echo "🔨 Rebuild SCLib (clean + up)"
        ./start.sh clean
        ./start.sh up
    else
        ./start.sh restart || ./start.sh up
    fi
    popd >/dev/null
    echo "✅ SCLib done"
}

mode_web() {
    echo "════════════════════════════════════════"
    echo "🌐 Mode w — SC_Web portal"
    echo "════════════════════════════════════════"
    ensure_docker_network
    pushd "$PORTAL_DOCKER_DIR" >/dev/null
    if [ "$REBUILD_WEB" = true ]; then
        echo "🔨 Rebuild portal"
        ./start.sh clean
        ./start.sh rebuild
    else
        ./start.sh restart || ./start.sh start
    fi
    popd >/dev/null
    echo "✅ Portal done"
}

mode_dashboards() {
    echo "════════════════════════════════════════"
    echo "📊 Mode d — dashboards"
    echo "════════════════════════════════════════"
    if [ ! -d "$DASHBOARDS_DIR" ]; then
        echo "❌ Missing $DASHBOARDS_DIR"
        exit 1
    fi
    ensure_docker_network
    pushd "$DASHBOARDS_DIR" >/dev/null

    [ -f ./scripts/regenerate_registry.sh ] && ./scripts/regenerate_registry.sh 2>&1 | grep -E '(✅|⚠️|❌|Registering|Port registry)' || true
    [ -f ./scripts/export_dashboard_list.sh ] && ./scripts/export_dashboard_list.sh 2>&1 | grep -E '(✅|⚠️|❌|Total)' || true

    local dashboards
    if [ -n "$DASHBOARD_ONLY_REGISTRY_KEY" ]; then
        local enabled
        enabled=$(jq -r ".dashboards[\"$DASHBOARD_ONLY_REGISTRY_KEY\"].enabled // false" config/dashboard-registry.json 2>/dev/null || echo "false")
        [ "$enabled" = "true" ] || { echo "❌ $DASHBOARD_ONLY_REGISTRY_KEY not enabled in registry"; exit 1; }
        dashboards="$DASHBOARD_ONLY_REGISTRY_KEY"
    else
        dashboards=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' config/dashboard-registry.json 2>/dev/null || echo "")
    fi

    if [ -n "$dashboards" ]; then
        while IFS= read -r name; do
            [ -n "$name" ] || continue
            echo "   📦 init $name"
            ./scripts/init_dashboard.sh "$name" --overwrite 2>&1 | grep -E '(✅|⚠️|❌|Generated)' || true
            echo "   🐳 build $name"
            ./scripts/build_dashboard.sh "$name" 2>&1 | tail -3 || true
        done <<< "$dashboards"
    fi

    ./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml 2>&1 | tail -2 || true

    popd >/dev/null
    pushd "$PORTAL_DOCKER_DIR" >/dev/null
    local env_file=".env"
    [ -f "$env_file" ] || env_file=""

    if [ -n "$DASHBOARD_ONLY_CONTAINER" ]; then
        docker rm -f "$DASHBOARD_ONLY_CONTAINER" 2>/dev/null || true
        if [ -n "$env_file" ]; then
            docker-compose -f dashboards-docker-compose.yml --env-file "$env_file" up -d "$DASHBOARD_ONLY_SERVICE"
        else
            docker-compose -f dashboards-docker-compose.yml up -d "$DASHBOARD_ONLY_SERVICE"
        fi
    else
        docker ps -a --filter 'name=dashboard_' --format '{{.Names}}' | while read -r c; do
            [ -n "$c" ] && docker rm -f "$c" 2>/dev/null || true
        done
        docker-compose -f dashboards-docker-compose.yml down 2>/dev/null || true
        if [ -n "$env_file" ]; then
            docker-compose -f dashboards-docker-compose.yml --env-file "$env_file" up -d
        else
            docker-compose -f dashboards-docker-compose.yml up -d
        fi
    fi
    docker-compose -f dashboards-docker-compose.yml ps 2>/dev/null || true
    popd >/dev/null

    echo "✅ Dashboards done"
}

mode_nginx() {
    echo "════════════════════════════════════════"
    echo "🔄 Mode x — SC nginx ($NGINX_CONTAINER)"
    echo "════════════════════════════════════════"
    if [ ! -d "$DASHBOARDS_DIR" ]; then
        echo "❌ Missing $DASHBOARDS_DIR"
        exit 1
    fi

    pushd "$DASHBOARDS_DIR" >/dev/null
    [ -f ./scripts/regenerate_registry.sh ] && ./scripts/regenerate_registry.sh 2>&1 | grep -E '(✅|⚠️|❌)' || true
    local dashboards
    dashboards=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' config/dashboard-registry.json 2>/dev/null || echo "")
    if [ -n "$dashboards" ]; then
        while IFS= read -r name; do
            [ -n "$name" ] || continue
            ./scripts/generate_nginx_config.sh "$name" 2>&1 | grep -E '(✅|⚠️|❌|Generated)' || true
        done <<< "$dashboards"
    fi
    ./scripts/setup_dashboards_nginx.sh sc
    popd >/dev/null

    ensure_docker_network
    discover_certbot_paths || {
        echo "❌ Cannot start $NGINX_CONTAINER without SSL certs (export SC_CERTBOT_CONF / SC_CERTBOT_WWW)"
        exit 1
    }
    pushd "$PORTAL_DOCKER_DIR" >/dev/null
    local nginx_compose
    nginx_compose="$(nginx_compose_files)"
    if [ -f docker-compose.nginx.yml ]; then
        if ! docker compose $nginx_compose up -d scientistcloud-nginx 2>&1; then
            docker-compose $nginx_compose up -d scientistcloud-nginx 2>&1 || {
                echo "❌ Failed to start $NGINX_CONTAINER (check cert paths SC_CERTBOT_CONF / SC_CERTBOT_WWW and port 80/443)"
                docker ps -a --filter "name=$NGINX_CONTAINER" --format '{{.Names}} {{.Status}}' 2>/dev/null || true
                exit 1
            }
        fi
    fi
    popd >/dev/null

    if docker ps --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
        docker exec "$NGINX_CONTAINER" nginx -t && docker exec "$NGINX_CONTAINER" nginx -s reload
        echo "✅ $NGINX_CONTAINER reloaded"
    else
        echo "⚠️  $NGINX_CONTAINER not running — add scientistcloud-server.conf (see NGINX.md) then:"
        echo "   cd $PORTAL_DOCKER_DIR && docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d"
    fi

    mode_dozzle
}

print_summary() {
    echo ""
    echo "🕒 Finished: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    if [ "$GIT_PULL_ONLY" = true ]; then
        echo "   (git pull only — use: ./allServicesStart.sh s w d x z)"
        return
    fi
    echo ""
    echo "Modes run:"
    $DO_SCLIB && echo "  s — SCLib"
    $DO_WEB && echo "  w — portal"
    $DO_DASHBOARDS && echo "  d — dashboards"
    $DO_NGINX && echo "  x — nginx (+ dozzle)"
    $DO_DOZZLE && ! $DO_NGINX && echo "  z — dozzle"
    echo ""
    echo "  Portal: https://${DOMAIN_NAME:-scientistcloud.com}/portal/"
    $DO_DOZZLE && echo "  Dozzle: https://${DOMAIN_NAME:-scientistcloud.com}/dozzle/"
    if [ -f "$DASHBOARDS_DIR/config/dashboard-registry.json" ]; then
        local base="https://${DOMAIN_NAME:-scientistcloud.com}"
        jq -r --arg b "$base" '.dashboards | to_entries[] | select(.value.enabled == true) | "  \(.key): \($b)\(.value.nginx_path // "")"' \
            "$DASHBOARDS_DIR/config/dashboard-registry.json" 2>/dev/null || true
    fi
}

# --- main ---
load_env
git_pull_all

if [ "$GIT_PULL_ONLY" = true ]; then
    print_summary
    exit 0
fi

$DO_SCLIB && mode_sclib
$DO_WEB && mode_web
$DO_DASHBOARDS && mode_dashboards
# Nginx after dashboards so conf.d/dashboards/ exists
$DO_NGINX && mode_nginx
$DO_DOZZLE && ! $DO_NGINX && mode_dozzle
# If only dashboards, still refresh nginx configs when d without x? Optional: run setup nginx after d
if $DO_DASHBOARDS && ! $DO_NGINX; then
    if [ -d "$DASHBOARDS_DIR" ]; then
        pushd "$DASHBOARDS_DIR" >/dev/null
        ./scripts/setup_dashboards_nginx.sh sc 2>&1 | grep -E '(✅|⚠️|❌|Copied)' || true
        popd >/dev/null
        if docker ps --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
            docker exec "$NGINX_CONTAINER" nginx -s reload 2>/dev/null || true
        fi
    fi
fi

print_summary
