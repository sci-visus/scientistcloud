# ScientistCloud dashboard base images

Replaces legacy images from `VisusDataPortalPrivate/Docker/`:

| Legacy (Visus) | SC 2.0 |
|----------------|--------|
| `visstore-bokeh-dashboard-base` | `sc-bokeh-dashboard-base` |
| `visstore-plotly-dashboard-base` | `sc-plotly-dashboard-base` |
| `visstore-4d-dashboard-base` | `sc-4d-dashboard-base` |

## Build

```bash
cd scientistcloud/SC_Dashboards/docker/bases
./build-base-images.sh
```

Or one base:

```bash
./build-base-images.sh --only bokeh
```

`allServicesStart.sh d` and `build_dashboard.sh` run this automatically when a base image is missing.

## Dashboard mapping

- **sc-bokeh-dashboard-base**: 3DVTK, OpenVisusSlice, darkmatter, magicscan, ORNL_CHESS_strain
- **sc-plotly-dashboard-base**: 3DPlotly
- **sc-4d-dashboard-base**: 4d_dashboardopt

OpenVisus C++ is from PyPI (`OpenVisus==2.2.141`). **openvisuspy** is installed from git @ `c1c8340` (editable), matching legacy `visstore-bokeh-dashboard-base` — PyPI `1.0.71` alone breaks OpenVisusSlice (`GetBackend`, `Slices`).
