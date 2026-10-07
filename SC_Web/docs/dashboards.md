# Dashboards

ScientistCloud opens a visualization dashboard when you select a dataset. The same dashboards are available on the [public portal](https://scientistcloud.com/portal/public/) and the account portal.

## Open a Dashboard

1. Select a dataset in the left sidebar
2. The center pane loads the preferred dashboard for that dataset
3. Use the **Dashboard** dropdown in the toolbar to switch viewers

If a dashboard is still loading, wait for the spinner. A mismatch (for example VTK on a 2D slide) can show an empty pane; switch back to a viewer that matches the data.

## Available Dashboards

The toolbar lists the dashboards deployed on the server. Typical options:

| Dashboard | Best for |
|-----------|----------|
| **OpenVisus Slice** | 2D/3D IDX volumes, TIFF stacks, HDF5, NetCDF, RGB slides. Pan, zoom, slice, colormap, probe |
| **3D Plotly** | Interactive 3D volumes with transfer-function and quality/time controls |
| **3D VTK** | Volume rendering and orthogonal slices, with a resolution slider |
| **4D Dashboard** | Time-varying / 4D scans |
| **MagicScan** | Whole-slide / MAGICSCAN pathology |
| **Dark Matter** | Nexus detector events, channel traces, and event metadata |
| **ORNL CHESS Strain** | Strain-mapping workflows: samples, predicted field, uncertainty, Play through snapshots |

The portal picks a default from the dataset sensor and **preferred dashboard** setting. You can change the preferred dashboard when you edit the dataset or when you connect data from Inspect S3.

## Explore in OpenVisus Slice

- Pan and zoom; resolution refines as you zoom
- Change **Palette** / colormap and min/max range
- Use the direction / offset slider to walk through a volume
- **Probe** reads a sample at the cursor

You do not download the full file. The viewer streams the resolution it needs.

## Share a View

On the account portal, dataset details include **Copy Dashboard Link**. That copies a URL for the current (or preferred) dashboard so a collaborator can open the same view.

Sharing the dataset with a user or team also lets them open dashboards from the portal. See [Sharing and Teams](?page=sharing).

## Public vs Account

Public-portal visitors can use dashboards on public datasets. They cannot upload, change preferred dashboard, or share. Sign in to the [account portal](https://scientistcloud.com/portal/index.php) for those actions.
