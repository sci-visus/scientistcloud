#!/bin/bash
# Entrypoint: ensure mounted upload dataset dirs are group-writable, then drop to dashboard user.
# Used when dashboard JSON sets visus_dataset_write (catalog.json, sessions, etc.).

set -e

RUN_USER="${DASHBOARD_RUN_USER:-bokehuser}"

fix_dir_permissions() {
    local dir="$1"
    if [ -d "$dir" ]; then
        chgrp www-data "$dir" 2>/dev/null || true
        chmod g+w "$dir" 2>/dev/null || echo "⚠️  Could not add group write on $dir"
    fi
}

if [ -d "/mnt/visus_datasets/upload" ]; then
    echo "🔧 Ensuring /mnt/visus_datasets/upload dataset dirs are group-writable..."
    find /mnt/visus_datasets/upload -mindepth 1 -maxdepth 1 -type d | while read -r dataset_dir; do
        fix_dir_permissions "$dataset_dir"
        sessions_dir="${dataset_dir}/sessions"
        if [ ! -d "$sessions_dir" ]; then
            mkdir -p "$sessions_dir" 2>/dev/null || true
        fi
        fix_dir_permissions "$sessions_dir"
    done
fi

drop_privileges() {
    local cmd=("$@")
    if [ "${#cmd[@]}" -eq 0 ]; then
        echo "❌ No command provided to entrypoint"
        exit 1
    fi
    if command -v gosu >/dev/null 2>&1; then
        exec gosu "$RUN_USER" "${cmd[@]}"
    fi
    if command -v runuser >/dev/null 2>&1; then
        exec runuser -u "$RUN_USER" -- "${cmd[@]}"
    fi
    if command -v su >/dev/null 2>&1; then
        exec su -s /bin/sh "$RUN_USER" -c "$(printf '%q ' "${cmd[@]}")"
    fi
    echo "❌ Cannot drop privileges to $RUN_USER (install gosu)"
    exit 1
}

drop_privileges "$@"
