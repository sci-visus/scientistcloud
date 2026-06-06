#!/usr/bin/env bash
#
# Optional pull + symlink for the external ORNL/NSDF dashboard package (nsdf_dashboard).
#
# Used at deploy/build time so SCLib_Dashboards/nsdf_dashboard points at a checkout of
# https://github.com/nsdf-fabric/scientist-cloud-dashboards (or a fork).
#
# Safe by default: missing repo, failed pull, or failed link does NOT fail the deploy
# unless --strict is passed.
#
# Configure in SCLib_TryTest/env.scientistcloud (optional):
#   NSDF_DASHBOARD_HOME=/path/to/ORNL_CHESS_UTK_UTAH_2026
#   NSDF_DASHBOARD_GIT_URL=https://github.com/nsdf-fabric/scientist-cloud-dashboards
#   NSDF_DASHBOARD_BRANCH=main
#   NSDF_DASHBOARD_SKIP_PULL=1    # link only, no git pull
#
# Usage:
#   ./sync_ornl_nsdf_dashboard.sh
#   SC20_ROOT=/home/amy/ScientistCloud2.0 ./sync_ornl_nsdf_dashboard.sh
#   ./sync_ornl_nsdf_dashboard.sh --strict

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SC_DOCKER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STRICT=false

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage 0 ;;
        --strict) STRICT=true; shift ;;
        --sc20-root)
            [ $# -ge 2 ] || { echo "❌ --sc20-root requires a path"; exit 1; }
            SC20_ROOT="$2"
            shift 2
            ;;
        *) echo "❌ Unknown argument: $1"; usage 1 ;;
    esac
done

warn() { echo "⚠️  $*"; }
info() { echo "ℹ️  $*"; }
ok() { echo "✅ $*"; }

finish() {
    local code="$1"
    if [ "$code" -ne 0 ] && [ "$STRICT" = true ]; then
        exit "$code"
    fi
    exit 0
}

discover_sc20_root() {
    if [ -n "${SC20_ROOT:-}" ] && [ -d "$SC20_ROOT/scientistCloudLib" ]; then
        return 0
    fi
    if [ -n "${SC20_HOME:-}" ] && [ -d "$SC20_HOME/scientistCloudLib" ]; then
        SC20_ROOT="$SC20_HOME"
        return 0
    fi
    local _c
    for _c in "$HOME/ScientistCloud2.0" "$HOME/ScientistCloud_2.0"; do
        if [ -d "$_c/scientistCloudLib" ] || [ -d "$_c/scientistcloud" ]; then
            SC20_ROOT="$_c"
            return 0
        fi
    done
    SC20_ROOT="${SC20_ROOT:-$HOME/ScientistCloud2.0}"
}

load_deploy_env() {
    local env_file=""
    for env_file in \
        "${SCLIB_TRYTEST_DIR:-}/env.scientistcloud" \
        "$SC20_ROOT/SCLib_TryTest/env.scientistcloud" \
        "$SC20_ROOT/env.scientistcloud" \
        "$SC_DOCKER_DIR/env.scientistcloud"; do
        if [ -f "$env_file" ]; then
            echo "📋 Loading deploy env: $env_file"
            set -o allexport
            # shellcheck source=/dev/null
            source "$env_file" || warn "Could not source $env_file — continuing with defaults"
            set +o allexport
            return 0
        fi
    done
    info "No env.scientistcloud found — using defaults"
}

discover_nsdf_dashboard_home() {
    if [ -n "${NSDF_DASHBOARD_HOME:-}" ]; then
        return 0
    fi
    local candidate=""
    for candidate in \
        "${SC20_ROOT:+$(cd "$SC20_ROOT/.." 2>/dev/null && pwd)/NSDF/ORNL_CHESS_UTK_UTAH_2026}" \
        "$HOME/NSDF/ORNL_CHESS_UTK_UTAH_2026" \
        "$HOME/ORNL_CHESS_UTK_UTAH_2026" \
        "$HOME/GIT/NSDF/ORNL_CHESS_UTK_UTAH_2026"; do
        if [ -n "$candidate" ] && [ -d "$candidate/.git" ]; then
            NSDF_DASHBOARD_HOME="$candidate"
            return 0
        fi
    done
    # Default install location when unset (may not exist yet)
    NSDF_DASHBOARD_HOME="${NSDF_DASHBOARD_HOME:-$HOME/NSDF/ORNL_CHESS_UTK_UTAH_2026}"
}

pull_nsdf_dashboard_repo() {
    local repo_home="$1"
    local branch="${NSDF_DASHBOARD_BRANCH:-main}"

    if [ ! -d "$repo_home/.git" ]; then
        info "NSDF dashboard repo not found at $repo_home — skipping pull/link"
        info "Clone manually, e.g.: git clone ${NSDF_DASHBOARD_GIT_URL:-https://github.com/nsdf-fabric/scientist-cloud-dashboards} $repo_home"
        return 2
    fi

    if [ "${NSDF_DASHBOARD_SKIP_PULL:-0}" = "1" ]; then
        info "NSDF_DASHBOARD_SKIP_PULL=1 — link only"
        return 0
    fi

    echo "📥 NSDF dashboard git pull — $repo_home"
    pushd "$repo_home" >/dev/null
    if ! git fetch origin 2>&1; then
        warn "NSDF dashboard git fetch failed — will try to link existing checkout"
        popd >/dev/null
        return 1
    fi
    if git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
        git checkout -f "$branch" 2>/dev/null || git checkout -f -B "$branch" "origin/$branch"
        if ! git pull --ff-only origin "$branch" 2>&1; then
            warn "NSDF dashboard fast-forward pull failed — using current checkout"
        fi
    else
        warn "Remote branch origin/$branch not found — using current checkout"
    fi
    popd >/dev/null
    ok "NSDF dashboard repo updated (or left at current commit)"
    return 0
}

link_nsdf_dashboard_package() {
    local repo_home="$1"
    local sclib_dashboards="$2"
    local package_dir="$repo_home/src/nsdf_dashboard"

    if [ ! -d "$package_dir" ]; then
        warn "Missing package directory: $package_dir"
        warn "Expected layout: <repo>/src/nsdf_dashboard/ (scientist-cloud-dashboards)"
        return 1
    fi

    mkdir -p "$sclib_dashboards"
    local abs_pkg
    abs_pkg="$(cd "$package_dir" && pwd)"

    ln -sfn "$abs_pkg" "$sclib_dashboards/nsdf_dashboard"
    ln -sfn nsdf_dashboard/ornl_chess_strain_lib.py "$sclib_dashboards/ornl_chess_strain_lib.py"

    if [ -L "$sclib_dashboards/nsdf_dashboard" ] && [ -f "$sclib_dashboards/nsdf_dashboard/ORNL_CHESS_strain.py" ]; then
        ok "Linked $sclib_dashboards/nsdf_dashboard → $abs_pkg"
        return 0
    fi

    warn "Symlink created but ORNL_CHESS_strain.py not found under $abs_pkg"
    return 1
}

main() {
    discover_sc20_root
    SCLIB_TRYTEST_DIR="${SCLIB_TRYTEST_DIR:-$SC20_ROOT/SCLib_TryTest}"
    load_deploy_env
    discover_nsdf_dashboard_home

    SCLIB_DASHBOARDS="${SCLIB_DASHBOARDS:-$SC20_ROOT/scientistCloudLib/SCLib_Dashboards}"
    NSDF_DASHBOARD_GIT_URL="${NSDF_DASHBOARD_GIT_URL:-https://github.com/nsdf-fabric/scientist-cloud-dashboards}"

    echo "════════════════════════════════════════"
    echo "📊 ORNL/NSDF dashboard sync (optional)"
    echo "   repo:  ${NSDF_DASHBOARD_HOME}"
    echo "   link:  ${SCLIB_DASHBOARDS}/nsdf_dashboard"
    echo "════════════════════════════════════════"

    pull_status=0
    pull_nsdf_dashboard_repo "$NSDF_DASHBOARD_HOME" || pull_status=$?

    if [ "$pull_status" -eq 2 ]; then
        info "ORNL_CHESS_strain will use whatever is already in SCLib_Dashboards (if any)"
        finish 0
    fi

    if ! link_nsdf_dashboard_package "$NSDF_DASHBOARD_HOME" "$SCLIB_DASHBOARDS"; then
        warn "Could not link nsdf_dashboard — ORNL_CHESS_strain build may use stale or bundled code"
        finish 1
    fi

    finish 0
}

main "$@"
