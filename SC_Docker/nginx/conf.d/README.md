# conf.d layout

| Path | Role |
|------|------|
| `../templates/scientistcloud-server.conf.template` | Rendered to `scientistcloud-server.conf` at container start |
| `dashboards/*_dashboard.conf` | Location blocks only (copied by `setup_dashboards_nginx.sh sc`) |
| `dashboards/dashboard_auth_gate.conf` | Dashboard login gate |
| `*_dashboard.conf` (this directory root) | **Source** for generate script; not loaded by `scientistcloud-nginx` |

Do not place `*_dashboard.conf` at the `conf.d/` root on the running container — nginx would load them at `http` level and fail.
