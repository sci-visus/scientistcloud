# ScientistCloud nginx (replaces `visstore_nginx`)

Edge routing for ScientistCloud 2.0 lives under **`scientistcloud/SC_Docker/nginx/`**. The **`scientistcloud-nginx`** container replaces **`visstore_nginx`** from VisusDataPortalPrivate.

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
| `/static/extensions/panel/` | `dashboard_3dvtk` |

**Omitted** (legacy): `visstore_user` at `/`, `visstore_bokeh_*`, `dataExplorer`, old `/plotly/`, `/Visus/`, `visstore_bg_service` routes.

## Environment

In `env.scientistcloud` or shell:

```bash
export DOMAIN_NAME=scientistcloud.com
# Reuse existing Let's Encrypt dirs from Visus deploy:
export SC_CERTBOT_CONF=/path/to/Docker/certbot/conf
export SC_CERTBOT_WWW=/path/to/Docker/certbot/www
```

## Cutover on the server

```bash
cd scientistcloud/SC_Docker
export DOMAIN_NAME=scientistcloud.com
export SC_CERTBOT_CONF=...   # same paths visstore_nginx used
export SC_CERTBOT_WWW=...

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
