# Port Conflict Analysis

## Old Dashboard Ports (Currently Running)

From `/Users/amygooch/GIT/VisusDataPortalPrivate/Docker/docker-compose.yaml`:

- **visstore_plotly**: 8050 ❌ CONFLICT with new 3DPlotly
- **visstore_bokeh_dashboard**: 5008
- **visstore_chess_dashboard** (4D): 5009
- **visstore_magicscan_dashboard**: 5010
- **visstore_convert4d_bokeh**: 5004
- **visstore_bokeh**: 5006

## New Dashboard Ports (Assigned)

From `config/dashboard-registry.json`:

- **3DPlotly**: 8050 ❌ CONFLICT with visstore_plotly:8050
- **3DVTK**: 8051 ✅ Safe
- **4D_Dashboard**: 8052 ✅ Safe
- **Magicscan**: 8053 ✅ Safe
- **OpenVisusSlice**: 8054 ✅ Safe

## Recommended Port Changes

Since both systems are running simultaneously, we need to avoid port conflicts:

- **3DPlotly**: Change from 8050 → **8060** (to avoid conflict with visstore_plotly:8050)
- **3DVTK**: 8051 ✅ (no conflict)
- **4D_Dashboard**: 8052 ✅ (no conflict)
- **Magicscan**: 8053 ✅ (no conflict)
- **OpenVisusSlice**: 8054 ✅ (no conflict)

## Port Range Safe Zones

- **5000-5003**: Reserved for old services
- **5004**: visstore_convert4d_bokeh
- **5005**: (unused)
- **5006**: visstore_bokeh
- **5007**: (unused)
- **5008**: visstore_bokeh_dashboard
- **5009**: visstore_chess_dashboard
- **5010**: visstore_magicscan_dashboard
- **5011-8049**: Available for future use
- **8050**: ❌ CONFLICT - visstore_plotly (old) and 3DPlotly (new)
- **8051-8054**: ✅ Safe for new dashboards
- **8055-8999**: ✅ Safe for new dashboards

## Nginx Configuration Pattern

### Old System (Embedded in default.conf)

Old dashboards were added **inside the server blocks** in `default.conf.https` and `default.conf.template`:

```nginx
server {
    listen 443 ssl;
    # ... other config ...
    
    # /plotly to visstore_plotly
    location /plotly/ {
        proxy_pass http://visstore_plotly:8050/plotly/;
        # ... headers ...
    }
    
    # /magicscan to visstore_magicscan_dashboard
    location /magicscan/ {
        proxy_pass http://visstore_magicscan_dashboard:5010/magicscan/;
        # ... headers ...
    }
}
```

### New System (Separate conf.d files)

New dashboards use **separate .conf files** in `nginx/conf.d/`:

```nginx
# File: 3DPlotly_dashboard.conf
location /dashboard/plotly {
    proxy_pass http://dashboard_3dplotly:8060;
    # ... headers ...
}
```

These files are automatically included by nginx's `include /etc/nginx/conf.d/*.conf;` directive.

## Action Required

1. **Update 3DPlotly port** from 8050 to 8060 in:
   - `config/dashboard-registry.json`
   - `config/port-registry.json`
   - `dashboards/3DPlotly.json`
   - Regenerate Dockerfile and nginx config

2. **Verify no other conflicts** before deploying

