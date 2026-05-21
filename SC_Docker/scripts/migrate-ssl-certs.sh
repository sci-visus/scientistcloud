#!/usr/bin/env bash
# One-time: copy Let's Encrypt material from a legacy certbot dir into SC_Docker/certbot.
# Usage: ./scripts/migrate-ssl-certs.sh [/path/to/legacy/Docker/certbot]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SC_DOCKER="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST_ROOT="$SC_DOCKER/certbot"
SRC_ROOT="${1:-}"

if [ -z "$SRC_ROOT" ]; then
    echo "Usage: $0 /path/to/legacy/Docker/certbot"
    echo "Example: $0 /home/amy/VisStoreClone/visus-dataportal-private/Docker/certbot"
    exit 1
fi

if [ ! -d "$SRC_ROOT/conf" ]; then
    echo "❌ Missing $SRC_ROOT/conf"
    exit 1
fi

mkdir -p "$DEST_ROOT/conf" "$DEST_ROOT/www"
echo "Copying $SRC_ROOT → $DEST_ROOT"
rsync -a --delete "${SRC_ROOT}/conf/" "$DEST_ROOT/conf/"
if [ -d "${SRC_ROOT}/www" ]; then
    rsync -a "${SRC_ROOT}/www/" "$DEST_ROOT/www/"
fi

DOMAIN="${DOMAIN_NAME:-scientistcloud.com}"
if [ -f "$DEST_ROOT/conf/live/${DOMAIN}/fullchain.pem" ]; then
    echo "✅ Certs present: $DEST_ROOT/conf/live/${DOMAIN}/fullchain.pem"
    echo "Set in env.scientistcloud:"
    echo "  SC_CERTBOT_CONF=$DEST_ROOT/conf"
    echo "  SC_CERTBOT_WWW=$DEST_ROOT/www"
else
    echo "⚠️  No fullchain.pem for $DOMAIN under $DEST_ROOT/conf/live/"
    ls -la "$DEST_ROOT/conf/live/" 2>/dev/null || true
    exit 1
fi
