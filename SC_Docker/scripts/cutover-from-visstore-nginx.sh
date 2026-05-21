#!/usr/bin/env bash
# Replace visstore_nginx with scientistcloud-nginx (SC 2.0 edge).
# Run on the deployment host from scientistcloud/SC_Docker.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SC_DOCKER="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SC_DOCKER"

DOMAIN_NAME="${DOMAIN_NAME:-scientistcloud.com}"
export DOMAIN_NAME

echo "== ScientistCloud nginx cutover (DOMAIN_NAME=$DOMAIN_NAME) =="

echo "1) Dashboard nginx configs → conf.d/dashboards/"
cd "$SC_DOCKER/../SC_Dashboards/scripts"
./setup_dashboards_nginx.sh sc

cd "$SC_DOCKER"

echo "2) Start scientistcloud-nginx (reuse existing certbot volumes if set)"
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d scientistcloud-nginx

echo "3) Verify config inside container"
docker exec scientistcloud-nginx nginx -t

echo "4) Smoke checks (adjust host if needed)"
curl -sf -o /dev/null -w "portal health HTTP %{http_code}\n" "http://127.0.0.1/portal/health" || true
curl -sfk -o /dev/null -w "portal health HTTPS %{http_code}\n" "https://127.0.0.1/portal/health" || true

read -r -p "Stop legacy visstore_nginx / visstore_bg_service / visstore_user? [y/N] " ans
if [[ "${ans,,}" == "y" ]]; then
  docker stop visstore_nginx visstore_bg_service visstore_user 2>/dev/null || true
  echo "Legacy containers stopped."
else
  echo "Skipped legacy stop. Stop visstore_nginx manually after you confirm SC nginx on :80/:443."
fi

echo "Done. Primary UI: https://${DOMAIN_NAME}/portal/"
