# Differences: allServicesStart.sh vs local-dev.sh

## allServicesStart.sh (Production/Server)
- ✅ Pulls latest code from GitHub (`git reset --hard origin/main`)
- ✅ Sets up nginx configurations (portal + dashboards)
- ✅ Starts main VisusDataPortalPrivate services (if not skipped)
- ✅ Handles SSL certificates
- ✅ Sets up dashboard nginx configs in `conf.d/`
- ✅ Performs final nginx reload
- ✅ Uses production environment variables from `env.scientistcloud`
- ✅ Accesses services via nginx proxy (https://scientistcloud.com/portal/)

## local-dev.sh (Local Development)
- ❌ Does NOT pull from GitHub (uses local code)
- ❌ Does NOT set up nginx (assumes direct port access)
- ❌ Does NOT start main VisusDataPortalPrivate services
- ❌ Does NOT handle SSL
- ❌ Does NOT set up dashboard nginx configs
- ✅ Uses `.env.local` with `DOMAIN_NAME=localhost`
- ✅ Accesses services directly on ports:
  - Portal: http://localhost:8080
  - Dashboards: http://localhost:8051, 8060, etc.

## When to Use Each

### Use `allServicesStart.sh` for:
- Production deployment on scientistcloud.com
- Server environment where nginx is needed
- When you want to test the full production setup

### Use `local-dev.sh` for:
- Local development on your machine
- Quick testing without nginx
- When you want to test code changes without git pull

## Key Missing in local-dev.sh

The main thing `local-dev.sh` doesn't do is **nginx setup**. This means:
- Portal routes work via direct port access (http://localhost:8080)
- Dashboard routes work via direct port access (http://localhost:8051, etc.)
- No SSL/HTTPS
- No reverse proxy routing

If you need nginx for local testing, you can manually run:
```bash
# From VisusDataPortalPrivate/Docker directory
./setup_portal_nginx.sh
./setup_dashboards_nginx.sh  # If it exists
```

