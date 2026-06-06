#!/bin/bash
#
# ScientistCloud 2.0 — deploy helper (SC-native; no VisusDataPortalPrivate / visstore_* images required)
#
# Usage:
#   ./allServicesStart.sh              Git pull (scientistCloudLib + scientistcloud) + env sync
#   ./allServicesStart.sh s w d x z    Git pull, then rebuild/restart each part
#   ./allServicesStart.sh swdx         Nginx + dozzle (z is included with x)
#   ./allServicesStart.sh swdxz        Same as swdx
#
# Modes (after git pull):
#   s   SCLib (auth, fastapi, background-service) — rebuild via scientistCloudLib/Docker/start.sh
#   w   SC_Web portal (scientistcloud-portal) — rebuild via SC_Docker/start.sh
#   d   All enabled dashboards — SC base images, init, build_dashboard.sh (staged context),
#       then docker-compose up. Do NOT run: docker compose -f dashboards-docker-compose.yml build
#       (that context lacks SCLib_Dashboards and requirements.txt).
#       Optional: scripts/sync_ornl_nsdf_dashboard.sh pulls/links external nsdf_dashboard if present.
#   x   SC edge nginx — scientistcloud-nginx, default.conf override, certs, dashboards, dozzle
#   z   Dozzle log UI (visstore_dozzle) — https://DOMAIN/dozzle/  (also runs with x)
#
# No manual nginx/dozzle steps needed when repo is up to date — mode x handles:
#   nginx/conf.d/default.conf, scientistcloud-server.conf.template, visstore_dozzle, cert paths
#
# Long flags (same modes):
#   -s, --sclib-only          SCLib rebuild
#   -w, --web-only            Portal rebuild
#   -sw, --sclib-web          Both
#   -x, --nginx-only          Nginx only (still runs git pull first)
#   -z, --dozzle-only         Dozzle only (container log viewer at /dozzle/)
#   -dm, -ovs, -vtk, -plotly  Single dashboard rebuild (uses build_dashboard.sh, then compose up)
#   --dashboards-only         Skip s/w; only dashboard pipeline (+ x if also passed)
#
# Examples:
#   ./allServicesStart.sh
#   ./allServicesStart.sh s w
#   ./allServicesStart.sh d x          # all enabled dashboards + nginx
#   ./allServicesStart.sh w d          # portal + all dashboards (auth/utils fixes in images)
#   ./allServicesStart.sh -dm          # Dark Matter only
#   ./allServicesStart.sh -ovs         # OpenVisusSlice only
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
        -ovs|--openvisus-only|--openvisusslice-only)
            GIT_PULL_ONLY=false; DO_DASHBOARDS=true
            DASHBOARD_ONLY_REGISTRY_KEY="OpenVisusSlice"
            DASHBOARD_ONLY_SERVICE="openvisusslice"
            DASHBOARD_ONLY_CONTAINER="dashboard_openvisusslice"
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

# Canonical deploy env (same as manual deploy):
#   cp $SC20_ROOT/SCLib_TryTest/env.scientistcloud $SC20_ROOT/scientistCloudLib/Docker/.env
#   cp $SC20_ROOT/SCLib_TryTest/env.scientistcloud $SC20_ROOT/scientistcloud/SC_Docker/.env
# Must run after git pull — git clean -fd may remove untracked Docker .env files.
sync_env_files() {
    local env_file="$SCLIB_TRYTEST_DIR/env.scientistcloud"
    local sclib_env="$SCLIB_DOCKER_DIR/.env"
    local portal_env="$PORTAL_DOCKER_DIR/.env"
    if [ ! -f "$env_file" ]; then
        echo "⚠️  No env.scientistcloud at $env_file (SCLib/portal compose may fail)"
        return 1
    fi
    mkdir -p "$SCLIB_DOCKER_DIR" "$PORTAL_DOCKER_DIR"
    echo "   cp $env_file $sclib_env"
    cp "$env_file" "$sclib_env"
    echo "   cp $env_file $portal_env"
    cp "$env_file" "$portal_env"
    echo "   ✅ env synced to SCLib Docker and SC_Docker"
    return 0
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
    sync_env_files || true
}

# Optional external ORNL/NSDF dashboard checkout (never fails deploy unless script uses --strict).
sync_ornl_nsdf_dashboard() {
    local helper="$SCRIPT_DIR/scripts/sync_ornl_nsdf_dashboard.sh"
    if [ ! -x "$helper" ]; then
        echo "   ℹ️  No $helper — skipping ORNL/NSDF dashboard sync"
        return 0
    fi
    SC20_ROOT="$SC20_ROOT" "$helper" || true
}

git_pull_all() {
    echo "════════════════════════════════════════"
    echo "📥 Git pull — ScientistCloud 2.0 repos"
    echo "════════════════════════════════════════"

    # SCLib_TryTest is not a deployed git repo on the server — env.scientistcloud lives
    # there locally and is synced to Docker .env files via sync_env_files().
    # if [ -d "$SCLIB_TRYTEST_DIR" ]; then
    #     echo "📦 SCLib_TryTest"
    #     pushd "$SCLIB_TRYTEST_DIR" >/dev/null
    #     local bak="/tmp/sc_env_scientistcloud_$$.bak"
    #     [ -f env.scientistcloud ] && cp env.scientistcloud "$bak"
    #     git fetch origin
    #     git reset --hard origin/main
    #     [ -f "$bak" ] && cp "$bak" env.scientistcloud && rm -f "$bak"
    #     popd >/dev/null
    # fi

    if [ -d "$SCLIB_CODE_DIR" ]; then
        echo "📦 scientistCloudLib (workingPrivateRepo)"
        pushd "$SCLIB_CODE_DIR" >/dev/null
        git remote get-url origin 2>/dev/null | grep -q sci-visus/scientistCloudLib || \
            git remote set-url origin https://github.com/sci-visus/scientistCloudLib.git 2>/dev/null || true
        git fetch origin
        git reset --hard HEAD 2>/dev/null || true
        git clean -fd 2>/dev/null || true
        git checkout -f workingPrivateRepo 2>/dev/null || git checkout -f -b workingPrivateRepo origin/workingPrivateRepo
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
        git fetch origin
        # Discard local edits to tracked files (e.g. generated dashboards-docker-compose.yml)
        # so checkout never aborts; deploy always matches GitHub.
        git reset --hard HEAD 2>/dev/null || true
        git clean -fd 2>/dev/null || true
        if git ls-remote --heads origin workingPrivateRepo 2>/dev/null | grep -q workingPrivateRepo; then
            git checkout -f -B workingPrivateRepo origin/workingPrivateRepo
            git reset --hard origin/workingPrivateRepo
        else
            git checkout -f -B main origin/main 2>/dev/null || git checkout -f origin/main
            git reset --hard origin/main 2>/dev/null || true
        fi
        git clean -fd 2>/dev/null || true
        popd >/dev/null
        if docker ps -a --format '{{.Names}}' | grep -q '^scientistcloud-portal$'; then
            docker start scientistcloud-portal 2>/dev/null || true
        fi
    fi
    sync_env_files || true
    sync_ornl_nsdf_dashboard
    # git clean -fd removes nginx/conf.d/default.conf; recreate before any compose mount
    ensure_sc_nginx_files || true
    echo "✅ Git pull complete"
}

ensure_docker_network() {
    if ! docker network inspect docker_visstore_web >/dev/null 2>&1; then
        echo "🌐 Creating docker_visstore_web network"
        docker network create docker_visstore_web || true
    fi
}

# Required SC nginx files (replaces manual default.conf / visstore_nginx steps)
ensure_sc_nginx_files() {
    local missing=0 f default_conf="$PORTAL_DOCKER_DIR/nginx/conf.d/default.conf"
    mkdir -p "$PORTAL_DOCKER_DIR/nginx/conf.d"

    if [ ! -f "$default_conf" ]; then
        echo "   📝 Creating nginx/conf.d/default.conf (disables stock nginx welcome server on :80)"
        cat > "$default_conf" <<'EOF'
# Overrides the stock nginx image welcome server on :80.
# ScientistCloud edge uses scientistcloud-server.conf (listen 80 default_server).

server {
    listen 127.0.0.1:41889;
    server_name _sc_disabled_default;
    location / {
        return 404;
    }
}
EOF
    fi

    for f in \
        nginx/templates/scientistcloud-server.conf.template \
        nginx/includes/scientistcloud-locations.conf \
        nginx/includes/scientistcloud-bokeh-static-map.conf \
        docker-compose.nginx.yml; do
        if [ ! -f "$PORTAL_DOCKER_DIR/$f" ]; then
            echo "❌ Missing SC_Docker/$f"
            missing=1
        fi
    done
    if [ -f "$PORTAL_DOCKER_DIR/nginx/nginx.conf" ] && \
        ! grep -q 'scientistcloud-bokeh-static-map.conf' "$PORTAL_DOCKER_DIR/nginx/nginx.conf"; then
        echo "❌ nginx/nginx.conf must include scientistcloud-bokeh-static-map.conf in http {}"
        missing=1
    fi
    if [ "$missing" -ne 0 ]; then
        echo "   Run: cd $SCIENTISTCLOUD_DIR && git pull && git checkout -B workingPrivateRepo origin/workingPrivateRepo"
        exit 1
    fi
}

# Reload edge nginx after dashboard deploy (map vars require http{} include in nginx.conf).
reload_sc_nginx() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
        echo "   ℹ️  $NGINX_CONTAINER not running — run: ./allServicesStart.sh x"
        return 0
    fi
    ensure_sc_nginx_files
    if docker exec "$NGINX_CONTAINER" nginx -t 2>&1; then
        docker exec "$NGINX_CONTAINER" nginx -s reload
        echo "✅ $NGINX_CONTAINER reloaded"
        verify_edge_nginx || true
        return 0
    fi
    echo "❌ $NGINX_CONTAINER config test failed (often: unknown sc_bokeh_static_host — recreate nginx)"
    echo "   Fix: ./allServicesStart.sh x"
    return 1
}

# Quick edge checks after nginx starts (replaces manual curl smoke tests)
verify_edge_nginx() {
    local domain="${DOMAIN_NAME:-scientistcloud.com}"
    if ! docker ps --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
        return 1
    fi
    docker exec "$NGINX_CONTAINER" nginx -t >/dev/null 2>&1 || return 1
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $domain" "http://127.0.0.1/portal/health" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo "   ✅ HTTP /portal/health → $code (Host: $domain)"
        return 0
    fi
    code=$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $domain" "https://127.0.0.1/portal/health" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo "   ✅ HTTPS /portal/health → $code"
    else
        echo "   ⚠️  /portal/health returned HTTP=$code (portal may still be starting)"
    fi
    # Bokeh dashboards load /static/js/bokeh.min.js from site root (not /dashboard/.../static/)
    local static_code
    static_code=$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $domain" \
        -H "Referer: https://${domain}/dashboard/3DVTK/" \
        "https://127.0.0.1/static/js/bokeh.min.js" 2>/dev/null || echo "000")
    if [ "$static_code" = "200" ]; then
        echo "   ✅ HTTPS /static/js/bokeh.min.js → $static_code"
    else
        echo "   ❌ HTTPS /static/js/bokeh.min.js → $static_code (run ./allServicesStart.sh x after git pull)"
    fi
    static_code=$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $domain" \
        "https://127.0.0.1/static/extensions/panel/panel.min.js" 2>/dev/null || echo "000")
    if [ "$static_code" = "200" ]; then
        echo "   ✅ HTTPS /static/extensions/panel/panel.min.js → $static_code"
    else
        echo "   ❌ HTTPS /static/extensions/panel/panel.min.js → $static_code"
    fi
    return 0
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
    sync_env_files || {
        echo "❌ Cannot start SCLib without $SCLIB_TRYTEST_DIR/env.scientistcloud"
        exit 1
    }
    pushd "$SCLIB_DOCKER_DIR" >/dev/null
    if [ ! -f .env ]; then
        echo "❌ Missing $SCLIB_DOCKER_DIR/.env after sync_env_files"
        exit 1
    fi
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
    sync_env_files || {
        echo "❌ Cannot start portal without $SCLIB_TRYTEST_DIR/env.scientistcloud"
        exit 1
    }
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
    echo "   Build: SC_Dashboards/scripts/build_dashboard.sh (copies SCLib_Dashboards + requirements.txt)"
    echo "   Not:   docker compose -f dashboards-docker-compose.yml build  ← wrong context, will fail"
    echo "════════════════════════════════════════"
    sync_ornl_nsdf_dashboard
    if [ ! -d "$DASHBOARDS_DIR" ]; then
        echo "❌ Missing $DASHBOARDS_DIR"
        exit 1
    fi
    ensure_docker_network
    sync_env_files || true
    pushd "$DASHBOARDS_DIR" >/dev/null

    if [ -x ./docker/bases/build-base-images.sh ]; then
        echo "🐳 SC dashboard base images (sc-bokeh / sc-plotly / sc-4d)..."
        ./docker/bases/build-base-images.sh 2>&1 | grep -E '(Building|✅|❌|sc-)' || true
    fi

    [ -f ./scripts/regenerate_registry.sh ] && ./scripts/regenerate_registry.sh 2>&1 | grep -E '(✅|⚠️|❌|Registering|Port registry)' || true
    if [ -f ./scripts/export_dashboard_list.sh ]; then
        if ! ./scripts/export_dashboard_list.sh; then
            echo "❌ export_dashboard_list.sh failed — /portal/api/dashboards.php may return errors"
        fi
    fi
    if [ -n "$DASHBOARD_ONLY_REGISTRY_KEY" ]; then
        export SC_DASHBOARD_BUILD_NO_CACHE=1
        echo "🔄 Single-dashboard rebuild: SC_DASHBOARD_BUILD_NO_CACHE=1"
    fi

    local dashboards
    if [ -n "$DASHBOARD_ONLY_REGISTRY_KEY" ]; then
        local enabled
        enabled=$(jq -r ".dashboards[\"$DASHBOARD_ONLY_REGISTRY_KEY\"].enabled // false" config/dashboard-registry.json 2>/dev/null || echo "false")
        [ "$enabled" = "true" ] || { echo "❌ $DASHBOARD_ONLY_REGISTRY_KEY not enabled in registry"; exit 1; }
        dashboards="$DASHBOARD_ONLY_REGISTRY_KEY"
    else
        dashboards=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' config/dashboard-registry.json 2>/dev/null || echo "")
    fi

    DASHBOARD_BUILD_FAILED=false
    if [ -n "$dashboards" ]; then
        while IFS= read -r name; do
            [ -n "$name" ] || continue
            echo "   📦 init $name"
            ./scripts/init_dashboard.sh "$name" --overwrite 2>&1 | grep -E '(✅|⚠️|❌|Generated)' || true
            echo "   🐳 build $name (staged context via build_dashboard.sh)"
            if ! ./scripts/build_dashboard.sh "$name"; then
                echo "   ❌ Docker build failed: $name"
                DASHBOARD_BUILD_FAILED=true
            fi
        done <<< "$dashboards"
    fi
    if [ "$DASHBOARD_BUILD_FAILED" = true ]; then
        echo "❌ One or more dashboard image builds failed — fix errors above before relying on containers"
        exit 1
    fi

    ./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml 2>&1 | tail -2 || true

    popd >/dev/null
    pushd "$PORTAL_DOCKER_DIR" >/dev/null
    local env_file=".env"
    [ -f "$env_file" ] || env_file=""

    if [ -n "$DASHBOARD_ONLY_CONTAINER" ]; then
        docker rm -f "$DASHBOARD_ONLY_CONTAINER" 2>/dev/null || true
        if [ -n "$env_file" ]; then
            docker-compose -f dashboards-docker-compose.yml --env-file "$env_file" up -d --force-recreate "$DASHBOARD_ONLY_SERVICE"
        else
            docker-compose -f dashboards-docker-compose.yml up -d --force-recreate "$DASHBOARD_ONLY_SERVICE"
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
    if ! ./scripts/setup_dashboards_nginx.sh sc; then
        echo "⚠️  setup_dashboards_nginx.sh had errors — continuing to start $NGINX_CONTAINER"
    fi
    popd >/dev/null

    ensure_docker_network
    ensure_sc_nginx_files
    discover_certbot_paths || {
        echo "❌ Cannot start $NGINX_CONTAINER without SSL certs (export SC_CERTBOT_CONF / SC_CERTBOT_WWW)"
        echo "   One-time: ./scripts/migrate-ssl-certs.sh /path/to/old/Docker/certbot"
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
        if ! reload_sc_nginx; then
            echo "   🔄 Recreating $NGINX_CONTAINER (pick up nginx.conf + map include + default.conf)..."
            pushd "$PORTAL_DOCKER_DIR" >/dev/null
            local nginx_compose
            nginx_compose="$(nginx_compose_files)"
            docker compose $nginx_compose up -d --force-recreate scientistcloud-nginx 2>&1 || \
                docker-compose $nginx_compose up -d --force-recreate scientistcloud-nginx 2>&1 || true
            popd >/dev/null
            reload_sc_nginx || true
        fi
    else
        echo "⚠️  $NGINX_CONTAINER not running — see NGINX.md or run: ./allServicesStart.sh x"
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
        reload_sc_nginx || echo "   ⚠️  Nginx not reloaded — run: ./allServicesStart.sh x"
    fi
fi

print_summary
