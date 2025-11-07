# Local Development Setup

This guide explains how to set up and test the ScientistCloud Portal and Dashboards locally.

## Quick Start

### 1. Create Local Environment File

```bash
cd ~/GIT/ScientistCloud_2.0/scientistcloud/SC_Docker
cp .env .env.local
```

Edit `.env.local` and set:
```bash
DOMAIN_NAME=localhost
DEPLOY_SERVER=http://localhost
```

### 2. Start Local Development Environment

```bash
./local-dev.sh start
```

This will:
- Start the portal on `http://localhost:8080`
- Build and start all enabled dashboards
- Show status of all services

### 3. Access Services

- **Portal**: http://localhost:8080
- **Dashboards** (direct port access):
  - 3DPlotly: http://localhost:8060
  - 3DVTK: http://localhost:8051
  - 4D Dashboard: http://localhost:8052
  - Magicscan: http://localhost:8053
  - OpenVisusSlice: http://localhost:8054

## Common Commands

### Start Everything
```bash
./local-dev.sh start
```

### Start Only Portal
```bash
./local-dev.sh portal
```

### Start Only Dashboards
```bash
./local-dev.sh dashboards
```

### Start Specific Dashboard
```bash
./local-dev.sh dashboard 3DPlotly
./local-dev.sh dashboard OpenVisusSlice
```

### View Logs
```bash
# Portal logs
./local-dev.sh logs portal

# Dashboard logs
./local-dev.sh logs 3dplotly
./local-dev.sh logs openvisusslice
```

### Check Status
```bash
./local-dev.sh status
```

### Stop Everything
```bash
./local-dev.sh stop
```

### Restart Everything
```bash
./local-dev.sh restart
```

## Testing Dashboard URLs

For local testing, you can access dashboards in two ways:

### 1. Direct Port Access (Recommended for Local Dev)
```
http://localhost:8051/3DVTK?uuid=<uuid>&server=false&name=<name>
http://localhost:8060/3DPlotly?uuid=<uuid>&server=false&name=<name>
```

### 2. Via Portal (if nginx is configured)
```
http://localhost:8080/dashboard/vtk?uuid=<uuid>&server=false&name=<name>
http://localhost:8080/dashboard/plotly?uuid=<uuid>&server=false&name=<name>
```

## Debugging

### Check if Services are Running
```bash
docker ps | grep -E "(scientistcloud-portal|dashboard_)"
```

### View Container Logs
```bash
# Portal
docker logs -f scientistcloud-portal

# Specific dashboard
docker logs -f dashboard_3dplotly
docker logs -f dashboard_openvisusslice
```

### Test Dashboard Health
```bash
curl http://localhost:8051/health
curl http://localhost:8060/health
```

### Test Dashboard with Parameters
```bash
curl "http://localhost:8051/3DVTK?uuid=test-uuid&server=false&name=TestDataset"
```

## Troubleshooting

### Port Already in Use
If a port is already in use, the script will warn you. Stop the existing container:
```bash
docker ps | grep <port>
docker stop <container_name>
```

### Dashboard Not Starting
1. Check logs: `./local-dev.sh logs <dashboard_name>`
2. Verify dashboard config exists: `ls ../SC_Dashboards/dashboards/<name>.json`
3. Rebuild dashboard: `cd ../SC_Dashboards && ./scripts/build_dashboard.sh <name>`

### Portal Can't Connect to Dashboards
1. Verify dashboard containers are running: `docker ps | grep dashboard_`
2. Check network: `docker network inspect docker_visstore_web`
3. Test direct access: `curl http://localhost:<port>/health`

## Environment Variables

The script uses `.env.local` for local development. Key variables:

- `DOMAIN_NAME=localhost` - Domain for local testing
- `DEPLOY_SERVER=http://localhost` - Server URL
- `MONGO_URL=mongodb://localhost:27017` - MongoDB connection
- `DB_NAME=scientistcloud` - Database name
- `SECRET_KEY=local-dev-secret` - Secret key (use a real one in production)

## Next Steps

1. Start local environment: `./local-dev.sh start`
2. Open portal: http://localhost:8080
3. Test dashboard loading with a dataset
4. Check browser console for errors
5. View logs for debugging: `./local-dev.sh logs portal`

## Notes

- Local development uses direct port access (no nginx proxy needed)
- Dashboards run in separate containers on their own ports
- The portal container can access dashboards via Docker network
- For production-like testing, you can set up local nginx (see `./local-dev.sh nginx`)


