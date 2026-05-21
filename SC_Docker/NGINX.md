# ScientistCloud nginx (replaces `visstore_nginx`)

Edge routing for ScientistCloud 2.0 lives under **`scientistcloud/SC_Docker/nginx/`**. The **`scientistcloud-nginx`** container replaces **`visstore_nginx`** from VisusDataPortalPrivate.

**Legacy reference:** `VisusDataPortalPrivate/Docker/nginx/conf.d/default.conf.https` — that file defined what worked (portal API, `/static/`, `/static/extensions/panel/`, per-dashboard Bokeh/Plotly paths, Dozzle, SCLib). SC configs should preserve those patterns; only container names and URL prefixes changed (`/dataExplorer/` → `/dashboard/OpenVisusSlice/`, `visstore_bokeh` → `dashboard_openvisusslice`, etc.).

## Layout

```
SC_Docker/nginx/
├── nginx.conf
├── templates/
│   └── scientistcloud-server.conf.template   # → conf.d/scientistcloud-server.conf (envsubst)
├── includes/
│   └── scientistcloud-locations.conf         # portal, SCLib, dozzle, dashboards
└── conf.d/
    ├── README.md
    ├── dashboard_auth_gate.conf              # source (setup copies to dashboards/)
    ├── *_dashboard.conf                      # source (generate script output)
    └── dashboards/                           # mounted into container; location blocks only
```

## What the SC edge serves

| Path | Backend |
|------|---------|
| `/` | 301 → `/portal/` |
| `/portal/` | `scientistcloud-portal` |
| `/api/v1/`, `/api/upload/`, `/api/auth/` | SCLib |
| `/dashboard/*` | `dashboard_*` (via `dashboards/*_dashboard.conf`) |
| `/dozzle/` | `visstore_dozzle` (optional) |
| `/static/extensions/panel/` | `dashboard_3dvtk:8051` (same as `default.conf.https`) |
| `/static/js/`, `/static/css/`, … | `dashboard_openvisusslice:8054` (replaces `visstore_bokeh:5006/static/`) |

**Literal `proxy_pass` only** on `/static/` blocks — do not use `$variables` in `proxy_pass` for these paths (see `default.conf.https` lines 404–422).

**Omitted** (legacy, not needed for SC 2.0): `visstore_user` at `/`, `visstore_bokeh` container, `/dataExplorer/` root path (use `/dashboard/OpenVisusSlice/`), old `/plotly/` root (use `/dashboard/…`), `/Visus/`, `visstore_bg_service`.

## Environment

In `SCLib_TryTest/env.scientistcloud` (adjust `SC20_HOME` per host):

```bash
SC20_HOME=/home/amy/ScientistCloud2.0
SC_CERTBOT_CONF=${SC20_HOME}/scientistcloud/SC_Docker/certbot/conf
SC_CERTBOT_WWW=${SC20_HOME}/scientistcloud/SC_Docker/certbot/www
DOMAIN_NAME=scientistcloud.com
```

Certs live under **`scientistcloud/SC_Docker/certbot/`** — no dependency on VisusDataPortalPrivate paths.

## Cutover on the server

```bash
cd scientistcloud/SC_Docker
# One-time copy from legacy visus certbot (current server only):
./scripts/migrate-ssl-certs.sh /path/to/old/Docker/certbot

./scripts/cutover-from-visstore-nginx.sh
# or manually:
cd ../SC_Dashboards/scripts && ./setup_dashboards_nginx.sh sc
cd ../../SC_Docker
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d scientistcloud-nginx
docker exec scientistcloud-nginx nginx -t
docker stop visstore_nginx visstore_bg_service visstore_user
```

Then refresh the stack:

```bash
./allServicesStart.sh swdx
```

## Deploy script

```bash
./allServicesStart.sh x      # nginx + setup_dashboards_nginx.sh sc
./allServicesStart.sh swdx   # SCLib + portal + dashboards + nginx
```

## Legacy containers to stop

| Container | Reason |
|-----------|--------|
| `visstore_nginx` | Replaced by `scientistcloud-nginx` |
| `visstore_user` | Old PHP dataportal at `/` |
| `visstore_bg_service` | `backgroundService.py` + run_slampy |

Conversion for linked remote IDX: **`sclib_background_service`** only.
