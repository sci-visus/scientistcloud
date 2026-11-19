"""
Volume Explorer.

One OpenVisus dataset, one transfer-function window:
- a 2D slice at the chosen direction, offset, and time
- a histogram range brush that hides scalars outside the window
- a coarse vtk.js volume using that same window as opacity
- a depth image under a line drawn on the slice
- streamlines when the IDX has a velocity field, seeded on that line
"""
from __future__ import annotations

import os
import traceback
from urllib.parse import parse_qs, unquote

import numpy as np
from dash import Dash, Input, Output, Patch, State, ctx, dcc, html, no_update
from flask import Flask, jsonify, request
import plotly.graph_objects as go

from SCLib_Dashboards.SCDash_openvisus_load import (
    load_dataset_view_prefs,
    resolve_openvisus_load_target,
    save_dataset_view_prefs,
)
from SCLib_Dashboards.SCDash_volume_explorer import (
    PALETTES,
    apply_opacity_window,
    compute_streamlines,
    default_scalar_field,
    downsample_2d,
    field_descriptors,
    find_velocity,
    AXIS_NAMES,
    PLANE_NAMES,
    clamp_layer,
    finite_minmax,
    fraction_point,
    initial_window,
    layer_count,
    logic_shape_from_db,
    map_offset,
    mask_to_window,
    orthogonal_axes,
    palette_family,
    palette_record,
    polydata_mesh_state,
    read_coarse_volume,
    read_depth_columns,
    plane_from_volume,
    read_plane,
    read_vector_volume,
    scalar_histogram,
    seeds_for_streamlines,
    sample_curtain,
    volume_mesh_state,
)

try:
    import OpenVisus as ov
except ImportError:
    from OpenVisus import LoadDataset as _load_dataset

    class _OpenVisusModule:
        LoadDataset = staticmethod(_load_dataset)

    ov = _OpenVisusModule()

try:
    import dash_vtk
except ImportError:
    dash_vtk = None

try:
    from mongo_connection import get_mongo_client
except ImportError:
    get_mongo_client = None


PORT = int(os.environ.get("DASHBOARD_PORT", "8065"))
# The slice follows the quality slider. The 3D read stays at this level:
# coarser than -6 collapses the depth axis and those samples miss the value window.
VOLUME_QUALITY = -6
DEPLOY_SERVER = os.getenv("DEPLOY_SERVER") or ""
DB_NAME = os.getenv("DB_NAME")
COLLECTION = None
if get_mongo_client and DB_NAME:
    try:
        COLLECTION = get_mongo_client()[DB_NAME]["visstoredatas"]
    except Exception as mongo_ex:
        print(f"[VolumeExplorer] Mongo unavailable: {mongo_ex}")


class _Cache:
    def __init__(self):
        self.url = None
        self.db = None
        self.logic_shape = ()
        self.timesteps = [0]
        self.fields = []
        self.velocity = None
        self.scalar_field = None
        self.volumes = {}
        self.vectors = {}
        self.curtains = {}
        self.plane = None


CACHE = _Cache()
server = Flask(__name__)
app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix="/VolumeExplorer/",
    requests_pathname_prefix="/dashboard/VolumeExplorer/",
)
app.config.suppress_callback_exceptions = True
app.title = "Volume Explorer"


def current_user_email():
    email = (request.headers.get("X-SC-User-Email") or "").strip()
    if "@" in email:
        return email
    token = request.cookies.get("auth_token") or request.cookies.get("dashboard_auth_token")
    secret = os.getenv("SECRET_KEY")
    if not token or not secret:
        return None
    try:
        import jwt
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None
    found = decoded.get("user") or decoded.get("email")
    if isinstance(found, str) and "@" in found:
        return found
    return None


def _query(search):
    params = parse_qs(unquote(search or "").lstrip("?"))
    return (
        (params.get("uuid") or [None])[0],
        (params.get("server") or ["false"])[0],
        (params.get("name") or [""])[0],
    )


def _timesteps(db):
    try:
        steps = list(db.getTimesteps())
    except Exception:
        steps = []
    cleaned = []
    for step in steps:
        try:
            cleaned.append(int(step))
        except (TypeError, ValueError):
            continue
    return cleaned or [0]


def _open_dataset(search):
    uuid, server_flag, name = _query(search)
    if not uuid:
        raise RuntimeError("Open a dataset from the ScientistCloud portal.")
    target = resolve_openvisus_load_target(
        portal_uuid=uuid,
        server=server_flag or "false",
        name=name or "",
        collection=COLLECTION,
        deploy_server=DEPLOY_SERVER,
        log=print,
    )
    if CACHE.url != target.load_url or CACHE.db is None:
        CACHE.url = target.load_url
        CACHE.db = ov.LoadDataset(target.load_url)
        CACHE.logic_shape = logic_shape_from_db(CACHE.db)
        CACHE.timesteps = _timesteps(CACHE.db)
        CACHE.fields = field_descriptors(CACHE.db)
        CACHE.velocity = find_velocity(CACHE.fields)
        CACHE.scalar_field = default_scalar_field(CACHE.fields, CACHE.velocity)
        CACHE.volumes = {}
        CACHE.vectors = {}
        CACHE.curtains = {}
        print(
            f"[VolumeExplorer] loaded shape={CACHE.logic_shape} "
            f"timesteps={CACHE.timesteps} velocity={CACHE.velocity}"
        )
    prefs = load_dataset_view_prefs(COLLECTION, uuid) or {}
    return uuid, name or "", prefs


def _volume_key(timestep, quality):
    return (int(timestep), int(quality), CACHE.scalar_field)


def _get_volume(timestep, quality):
    key = _volume_key(timestep, quality)
    if key not in CACHE.volumes:
        volume, step, raw_shape = read_coarse_volume(
            CACHE.db,
            CACHE.logic_shape,
            timestep,
            quality,
            field=CACHE.scalar_field,
        )
        vectors = None
        if CACHE.velocity:
            try:
                vectors = read_vector_volume(
                    CACHE.db,
                    CACHE.logic_shape,
                    CACHE.velocity,
                    timestep,
                    quality,
                    step,
                    volume.shape,
                )
            except Exception as ex:
                print(f"[VolumeExplorer] velocity read failed: {ex}")
                vectors = None
        CACHE.volumes[key] = volume
        CACHE.vectors[key] = vectors
    return CACHE.volumes[key], CACHE.vectors.get(key)


def _empty_figure(title):
    fig = go.Figure()
    fig.update_layout(title=title, margin=dict(l=40, r=20, t=40, b=30), height=360)
    return fig


def _heatmap(image, title, colorscale, vmin, vmax, height=460, x_title="column", y_title="row", zoom=False):
    fig = go.Figure(data=go.Heatmap(
        z=image,
        colorscale=colorscale,
        zmin=vmin,
        zmax=vmax,
        colorbar=dict(title="value", len=0.8),
        hovertemplate=f"{x_title} %{{x}}<br>{y_title} %{{y}}<br>%{{z}}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        margin=dict(l=40, r=20, t=40, b=30),
        height=height,
        xaxis_title=x_title,
        yaxis_title=y_title,
        dragmode="zoom",
    )
    if zoom:
        # Same data unit on X and Y. A long zoom box stays long; it is not
        # stretched to fill the plot. uirevision keeps that view when a line
        # point is added. It changes only for Reset zoom.
        token = str(zoom)
        fig.update_layout(uirevision=token)
        fig.update_xaxes(uirevision=token, constrain="domain")
        fig.update_yaxes(
            uirevision=token,
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
        )
    return fig


def _histogram_figure(values, vmin, vmax):
    counts, edges = scalar_histogram(values)
    centers = ((edges[:-1] + edges[1:]) / 2.0).tolist()
    fig = go.Figure(data=go.Bar(x=centers, y=counts.tolist(), marker_color="#6c63b5"))
    fig.add_vrect(x0=vmin, x1=vmax, fillcolor="rgba(255, 196, 64, 0.25)", line_width=0)
    fig.update_layout(
        title="Scalar range — drag across the bars to set the slice window",
        margin=dict(l=40, r=20, t=40, b=30),
        height=240,
        bargap=0,
        xaxis_title="value",
        yaxis_title="count",
        showlegend=False,
        dragmode="select",
        selectdirection="h",
    )
    return fig


def _volume_view(volume, vectors, vmin, vmax, seeds, show_lines, preset, depth_axis=2):
    if dash_vtk is None:
        return html.Div("vtk.js is not installed in this dashboard image.")
    data_min, data_max = finite_minmax(volume)
    inside = np.isfinite(volume) & (volume >= vmin) & (volume <= vmax)
    print(
        f"[VolumeExplorer] volume shape={tuple(volume.shape)} "
        f"data=[{data_min:.6g}, {data_max:.6g}] window=[{float(vmin):.6g}, {float(vmax):.6g}] "
        f"inside={int(np.count_nonzero(inside))}"
    )
    if not np.any(inside):
        return html.Div(
            f"No voxels inside the value range {float(vmin):.4g}–{float(vmax):.4g}. "
            f"This volume spans {data_min:.4g}–{data_max:.4g}.",
            style={"color": "#a33", "padding": "12px"},
        )
    windowed, _nodata = apply_opacity_window(volume, vmin, vmax)
    # A new id makes vtk.js rebuild the view. Without it the pane stays on the
    # first frame when the value range or the volume changes.
    token = (
        f"{volume.shape[0]}_{volume.shape[1]}_{volume.shape[2]}_"
        f"{int(round(float(vmin) * 1000))}_{int(round(float(vmax) * 1000))}"
    )
    # scalarOpacityUnitDistance is (component, distance). A bare float is ignored,
    # and the default distance of 1 paints the grid as a solid black box.
    # VolumeController installs an opacity curve on the actual scalars.
    # rescaleColorMap stays off so the color scale remains the value range.
    unit = max(float(np.mean(volume.shape[:3])) / 40.0, 1.0)
    children = [
        dash_vtk.VolumeRepresentation(
            [
                dash_vtk.VolumeController(rescaleColorMap=False, size=[240, 72]),
                dash_vtk.Volume(id=f"volume-data-{token}", state=volume_mesh_state(windowed, depth_axis)),
            ],
            id=f"volume-rep-{token}",
            colorMapPreset=preset,
            colorDataRange=[float(vmin), float(vmax)],
            property={"scalarOpacityUnitDistance": [0, unit]},
        )
    ]
    note = ""
    if show_lines:
        if vectors is None:
            note = "This dataset has no velocity field, so streamlines stay off."
        else:
            try:
                polydata = compute_streamlines(vectors, seeds)
                if polydata is None:
                    note = "Streamlines did not leave the seed rake. Try another line or a lower quality."
                else:
                    children.append(dash_vtk.GeometryRepresentation(
                        [dash_vtk.Mesh(state=polydata_mesh_state(polydata))],
                        property={"color": [1, 1, 1], "lineWidth": 2},
                    ))
            except Exception as ex:
                print(f"[VolumeExplorer] streamlines failed: {ex}")
                traceback.print_exc()
                note = f"Streamlines failed: {ex}"
    # Default camera looks straight down the thin axis, so the volume reads as a slice.
    # An oblique position is reframed by vtk.js onto the dataset center.
    up = [0.0, 0.0, 0.0]
    up[int(depth_axis) if int(depth_axis) in (0, 1, 2) else 2] = 1.0
    view = dash_vtk.View(
        id=f"volume-view-{token}",
        children=children,
        background=[0.04, 0.04, 0.06],
        cameraPosition=[1.5, -1.7, 1.2],
        cameraViewUp=up,
    )
    return html.Div([
        html.Div(view, style={"height": "460px", "width": "100%"}),
        html.Div(
            f"One timestep from the Time slider. The vertical axis is {AXIS_NAMES[int(depth_axis) if int(depth_axis) in (0, 1, 2) else 2]} "
            "depth, the same axis Offset moves through, not a stack of times. Color uses the value range.",
            style={"color": "#666", "fontSize": "13px", "marginTop": "6px"},
        ),
        html.Div(note, style={"color": "#666", "fontSize": "13px"}),
    ])


def _banner(name):
    title = f"ScientistCloud | Volume Explorer: {name}" if name else "ScientistCloud | Volume Explorer"
    return html.Div(title, style={
        "background": "#4E477F",
        "color": "white",
        "padding": "10px 16px",
        "fontWeight": "600",
    })


app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="meta"),
    dcc.Store(id="transect-points"),
    dcc.Store(id="line-draw", data=0),
    dcc.Store(id="slice-revision", data=0),
    html.Div(id="banner"),
    html.Div(id="status", style={"margin": "8px 16px", "color": "#444"}),
    html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "12px", "alignItems": "end", "margin": "0 16px 8px"}, children=[
        html.Div([
            html.Label("Direction"),
            dcc.Dropdown(
                id="direction",
                options=[{"label": "X", "value": 0}, {"label": "Y", "value": 1}, {"label": "Z", "value": 2}],
                value=2,
                clearable=False,
                style={"width": "90px"},
            ),
        ]),
        html.Div([
            html.Label("Depth axis"),
            dcc.Dropdown(
                id="depth-axis",
                options=[{"label": "X", "value": 0}, {"label": "Y", "value": 1}, {"label": "Z", "value": 2}],
                value=2,
                clearable=False,
                style={"width": "90px"},
            ),
        ]),
        html.Div([
            html.Label("Offset"),
            dcc.Slider(
                id="offset",
                min=0,
                max=1,
                step=1,
                value=0,
                marks={0: "0", 1: "1"},
                tooltip={"placement": "bottom", "always_visible": True},
                updatemode="mouseup",
            ),
            html.Div(id="offset-caption", style={"color": "#666", "fontSize": "12px", "marginTop": "2px"}),
        ], style={"minWidth": "240px", "flex": "1"}),
        html.Div([
            html.Label("Time"),
            dcc.Slider(id="time", min=0, max=0, step=1, value=0),
        ], style={"minWidth": "180px", "flex": "1"}),
        html.Div([
            html.Label("Quality"),
            dcc.Slider(id="quality", min=-8, max=0, step=1, value=-6, marks={-8: "-8", -6: "-6", -3: "-3", 0: "0"}),
        ], style={"minWidth": "160px"}),
        html.Div([
            html.Label("Palette"),
            dcc.Dropdown(
                id="palette",
                options=[{"label": name, "value": name} for name in PALETTES],
                value="Viridis",
                clearable=False,
                style={"width": "140px"},
            ),
        ]),
        html.Div([
            html.Button("Save as default view", id="save-view", n_clicks=0, style={"display": "none"}),
            html.Span(id="save-status", style={"marginLeft": "8px"}),
        ]),
    ]),
    html.Div(style={"margin": "0 16px 12px"}, children=[
        html.Label("Value range — drag the slider, or brush a span on the scalar-range plot"),
        dcc.RangeSlider(id="window", min=0, max=1, value=[0, 1], step=0.01, allowCross=False),
    ]),
    html.Div(style={"display": "grid", "gridTemplateColumns": "1.3fr 1fr", "gap": "8px", "margin": "0 8px"}, children=[
        dcc.Graph(
            id="slice-graph",
            figure=_empty_figure("Slice"),
            config={"displaylogo": False, "scrollZoom": True, "doubleClick": False},
        ),
        html.Div(id="volume-pane"),
    ]),
    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "8px", "margin": "0 8px"}, children=[
        dcc.Graph(
            id="hist-graph",
            figure=_empty_figure("Scalar range"),
            config={"displaylogo": False, "scrollZoom": False},
        ),
        dcc.Graph(id="transect-graph", figure=_empty_figure("Depth transect"), config={"displaylogo": False}),
    ]),
    html.Div(style={"margin": "4px 16px 16px"}, children=[
        dcc.Checklist(
            id="streamlines",
            options=[{"label": " Streamlines from the drawn line (or a center rake)", "value": "on"}],
            value=[],
        ),
        html.Div(id="stream-note", style={"color": "#666", "fontSize": "13px"}),
        html.Button("Clear line", id="clear-line", n_clicks=0, style={"marginTop": "6px", "marginRight": "8px"}),
        html.Button("Reset zoom", id="reset-zoom", n_clicks=0, style={"marginTop": "6px"}),
        dcc.Checklist(
            id="depth-zero-top",
            options=[{"label": " Depth 0 at top", "value": "top"}],
            value=["top"],
            style={"marginTop": "6px"},
        ),
        html.Div(
            "Click to add corners. The depth plot runs from the start of the line on the left to the end on the right. Its vertical axis is the depth axis: offset 0 at the top when that box is checked, and the last offset at the bottom. Reset zoom clears a stuck slice view.",
            style={"color": "#666", "fontSize": "13px", "marginTop": "4px"},
        ),
    ]),
])


@server.route("/health")
@server.route("/VolumeExplorer/health")
def health():
    return "ok"

@server.route("/")
def root():
    return "ok"


@server.route("/VolumeExplorer/check-auth")
def check_auth():
    return jsonify({"authorized": True})


@app.callback(
    Output("meta", "data"),
    Output("banner", "children"),
    Output("status", "children"),
    Output("direction", "value"),
    Output("time", "min"),
    Output("time", "max"),
    Output("time", "value"),
    Output("time", "disabled"),
    Output("palette", "value"),
    Output("window", "min"),
    Output("window", "max"),
    Output("window", "step"),
    Output("window", "value"),
    Output("save-view", "style"),
    Output("stream-note", "children"),
    Input("url", "search"),
)
def load_dataset(search):
    hidden = {"display": "none"}
    try:
        uuid, name, prefs = _open_dataset(search)
    except Exception as ex:
        print(f"[VolumeExplorer] load failed: {ex}")
        traceback.print_exc()
        banner = _banner("")
        return (
            None, banner, str(ex),
            2,
            0, 0, 0, True,
            "Viridis",
            0, 1, 0.01, [0, 1],
            hidden,
            "",
        )
    direction = int(prefs.get("direction", 2)) if int(prefs.get("direction", 2) or 2) in (0, 1, 2) else 2
    if len(CACHE.logic_shape) < 3:
        direction = 0
    full_len = layer_count(CACHE.logic_shape, direction)
    offset = clamp_layer(prefs.get("offset", (full_len - 1) / 2), full_len)
    timesteps = CACHE.timesteps
    timestep = int(prefs["timestep"]) if prefs.get("timestep") in timesteps else timesteps[0]
    family = palette_family(prefs.get("palette") or "Viridis")
    try:
        sample, _vectors = _get_volume(timestep, -6) if len(CACHE.logic_shape) >= 3 else (None, None)
        if sample is None:
            sample = np.squeeze(np.asarray(CACHE.db.read(time=timestep, quality=-6)))
        data_min, data_max = finite_minmax(sample)
    except Exception as ex:
        print(f"[VolumeExplorer] sample failed: {ex}")
        data_min, data_max = 0.0, 1.0
    vmin, vmax = initial_window(prefs, data_min, data_max)
    slider_min = min(data_min, vmin)
    slider_max = max(data_max, vmax)
    if slider_min == slider_max:
        slider_max = slider_min + 1.0
    step = max((slider_max - slider_min) / 200.0, 1e-6)
    can_save = False
    if COLLECTION is not None:
        try:
            document = COLLECTION.find_one({"uuid": uuid}, {"user": 1, "user_email": 1, "owner": 1, "user_id": 1})
            from SCLib_Dashboards.SCDash_openvisus_load import user_owns_dataset
            can_save = user_owns_dataset(document, current_user_email())
        except Exception as ex:
            print(f"[VolumeExplorer] owner check failed: {ex}")
    velocity_note = ""
    if not CACHE.velocity:
        velocity_note = "Streamlines need a velocity field (a vector field, or u, v, and w). This dataset is scalar only."
    meta = {
        "uuid": uuid,
        "name": name,
        "logic_shape": list(CACHE.logic_shape),
        "saved_offset": offset,
        "scalar_field": CACHE.scalar_field,
        "has_velocity": bool(CACHE.velocity),
        "can_save": can_save,
    }
    return (
        meta,
        _banner(name),
        "Click to add corners of a line. The depth plot is the curtain under that path.",
        direction,
        timesteps[0],
        timesteps[-1],
        timestep,
        len(timesteps) < 2,
        family,
        slider_min,
        slider_max,
        step,
        [vmin, vmax],
        {} if can_save else hidden,
        velocity_note,
    )


@app.callback(
    Output("offset", "min"),
    Output("offset", "max"),
    Output("offset", "value"),
    Output("offset", "marks"),
    Output("offset-caption", "children"),
    Input("meta", "data"),
    Input("direction", "value"),
    State("offset", "value"),
)
def sync_offset(meta, direction, current):
    """Offset is the layer index on the chosen axis: 0 .. slices-1."""
    direction = int(direction) if int(direction or 0) in (0, 1, 2) else 2
    shape = (meta or {}).get("logic_shape") or []
    length = layer_count(shape, direction)
    last = length - 1
    if ctx.triggered_id == "meta":
        raw = (meta or {}).get("saved_offset", last // 2)
    else:
        raw = last // 2 if current is None else current
    value = clamp_layer(raw, length)
    axis = AXIS_NAMES[direction]
    caption = f"{axis} layer {value} of 0–{last} · {PLANE_NAMES[direction]} plane"
    marks = {0: "0", last: str(last)} if last else {0: "0"}
    return 0, last, value, marks, caption


def _window_from_selection(selected, lower, upper):
    """Local copy so the dashboard starts if the shared library is one commit behind."""
    if not isinstance(selected, dict):
        return None
    span = (selected.get("range") or {}).get("x")
    if not span or len(span) < 2:
        xs = []
        for point in selected.get("points") or []:
            if isinstance(point, dict) and point.get("x") is not None:
                try:
                    xs.append(float(point["x"]))
                except (TypeError, ValueError):
                    continue
        if not xs:
            return None
        span = [min(xs), max(xs)]
    try:
        lo = float(min(float(span[0]), float(span[1])))
        hi = float(max(float(span[0]), float(span[1])))
    except (TypeError, ValueError):
        return None
    if lower is not None:
        lo = max(lo, float(lower))
    if upper is not None:
        hi = min(hi, float(upper))
    if hi <= lo:
        return None
    return [lo, hi]


@app.callback(
    Output("window", "value", allow_duplicate=True),
    Input("hist-graph", "selectedData"),
    State("window", "min"),
    State("window", "max"),
    prevent_initial_call=True,
)
def window_from_histogram(selected, lower, upper):
    span = _window_from_selection(selected, lower, upper)
    if span is None:
        return no_update
    return span


def _line_vertices(points):
    if not isinstance(points, dict):
        return []
    vertices = list(points.get("points") or [])
    if len(vertices) < 2 and points.get("p0") and points.get("p1"):
        vertices = [points["p0"], points["p1"]]
    return [pt for pt in vertices if isinstance(pt, dict) and "row" in pt and "col" in pt]


@app.callback(
    Output("transect-points", "data"),
    Input("slice-graph", "clickData"),
    Input("clear-line", "n_clicks"),
    State("transect-points", "data"),
    prevent_initial_call=True,
)
def collect_transect(click, _clear_clicks, current):
    if ctx.triggered_id == "clear-line":
        return {"points": []}
    if not click or not click.get("points"):
        return current or {"points": []}
    point = click["points"][0]
    if "x" not in point or "y" not in point:
        return current or {"points": []}
    stored = {"row": float(point["y"]), "col": float(point["x"])}
    vertices = _line_vertices(current)
    if vertices:
        last = vertices[-1]
        if abs(last["row"] - stored["row"]) < 0.5 and abs(last["col"] - stored["col"]) < 0.5:
            return {"points": vertices}
    vertices.append(stored)
    return {"points": vertices}


@app.callback(
    Output("slice-graph", "figure", allow_duplicate=True),
    Output("transect-graph", "figure", allow_duplicate=True),
    Output("hist-graph", "figure"),
    Output("volume-pane", "children"),
    Input("meta", "data"),
    Input("direction", "value"),
    Input("offset", "value"),
    Input("time", "value"),
    Input("quality", "value"),
    Input("palette", "value"),
    Input("window", "value"),
    State("transect-points", "data"),
    Input("streamlines", "value"),
    Input("depth-axis", "value"),
    Input("depth-zero-top", "value"),
    Input("slice-revision", "data"),
    prevent_initial_call="initial_duplicate",
)
def render_views(meta, direction, offset, timestep, quality, palette, window, points, streamlines, depth_axis, zero_top, revision):
    if not meta or CACHE.db is None:
        return (
            _empty_figure("Slice"),
            _empty_figure("Depth transect"),
            _empty_figure("Scalar range"),
            html.Div("Load a dataset to render the volume."),
        )
    direction = int(direction) if int(direction or 0) in (0, 1, 2) else 2
    depth_axis = int(depth_axis) if int(depth_axis if depth_axis is not None else direction) in (0, 1, 2) else direction
    zero_at_top = "top" in (zero_top or [])
    timestep = int(timestep or 0)
    quality = int(quality if quality is not None else -6)
    axis_u, axis_v = orthogonal_axes(direction)
    # OpenVisus order: rows are axis_v, columns are axis_u. Plotly draws
    # columns across and rows up, so the horizontal title is axis_u.
    x_title, y_title = AXIS_NAMES[axis_u], AXIS_NAMES[axis_v]
    vmin, vmax = (window or [0, 1])[:2]
    record = palette_record(palette)
    colorscale = record["plotly"]
    show_lines = "on" in (streamlines or [])
    logic_shape = tuple(meta.get("logic_shape") or CACHE.logic_shape or ())
    try:
        if len(logic_shape) < 3:
            image = np.squeeze(np.asarray(CACHE.db.read(time=timestep, quality=quality)))
            if image.ndim != 2:
                raise RuntimeError(f"Expected a 2D dataset, got shape {image.shape}")
            data_min, data_max = finite_minmax(image)
            shown, step = downsample_2d(mask_to_window(image, vmin, vmax))
            slice_fig = _heatmap(shown, "Slice", colorscale, vmin, vmax)
            _draw_line(slice_fig, points)
            hist = _histogram_figure(image, vmin, vmax)
            transect = _transect_from_points(image, points, step, colorscale, vmin, vmax, depth=False)
            volume = html.Div("This dataset is 2D, so there is no volume to raycast.")
            return slice_fig, transect, hist, volume

        layer = clamp_layer(offset, layer_count(logic_shape, direction))
        plane = None
        try:
            # One IDX plane at the quality slider. This is the interactive view.
            plane = read_plane(
                CACHE.db,
                logic_shape,
                direction,
                layer,
                timestep,
                field=CACHE.scalar_field,
                quality=quality,
            )
        except Exception as ex:
            print(f"[VolumeExplorer] plane query failed: {ex}")
            plane = None
        volume = vectors = None
        if plane is None:
            volume, vectors = _get_volume(timestep, VOLUME_QUALITY)
            coarse_offset = map_offset(float(layer), layer_count(logic_shape, direction), volume.shape[direction])
            plane = plane_from_volume(volume, direction, coarse_offset)
        shown, step = downsample_2d(mask_to_window(np.asarray(plane), vmin, vmax))
        CACHE.plane = {
            "direction": direction,
            "layer": int(layer),
            "timestep": timestep,
            "quality": quality,
            "step": int(step),
            "plane_shape": tuple(int(v) for v in np.asarray(plane).shape),
            "logic_shape": tuple(logic_shape),
        }
        slice_fig = _heatmap(
            shown,
            f"{PLANE_NAMES[direction]} plane · {AXIS_NAMES[direction]} = {layer}",
            colorscale,
            vmin,
            vmax,
            x_title=x_title,
            y_title=y_title,
            zoom=f"slice-{direction}-{int(revision or 0)}",
        )
        _draw_line(slice_fig, points)
        hist = _histogram_figure(np.asarray(plane), vmin, vmax)
        try:
            if volume is None:
                volume, vectors = _get_volume(timestep, VOLUME_QUALITY)
            coarse_offset = map_offset(float(layer), layer_count(logic_shape, direction), volume.shape[direction])
            transect = _transect_from_points(
                volume, points, step, colorscale, vmin, vmax,
                depth=True, direction=direction, plane_shape=plane.shape,
                depth_axis=depth_axis, logic_shape=logic_shape,
                zero_at_top=zero_at_top, slice_layer=layer,
                volume_layer=coarse_offset, timestep=timestep,
            )
            seeds = _seeds(volume.shape, direction, coarse_offset, points, step, plane.shape)
            volume_pane = _volume_view(
                volume, vectors, float(vmin), float(vmax), seeds, show_lines, record["vtk"], depth_axis,
            )
        except Exception as ex:
            print(f"[VolumeExplorer] coarse volume failed: {ex}")
            traceback.print_exc()
            transect = _empty_figure("Depth transect")
            volume_pane = html.Div(str(ex), style={"color": "#a33", "padding": "12px"})
        return slice_fig, transect, hist, volume_pane
    except Exception as ex:
        print(f"[VolumeExplorer] render failed: {ex}")
        traceback.print_exc()
        return (
            _empty_figure("Slice"),
            _empty_figure("Depth transect"),
            _empty_figure("Scalar range"),
            html.Div(str(ex), style={"color": "#a33", "padding": "12px"}),
        )


def _line_xy(points):
    vertices = _line_vertices(points)
    return [pt["col"] for pt in vertices], [pt["row"] for pt in vertices]


def _draw_line(fig, points):
    """Trace 1 is always the line, so a later click can update it in place."""
    xs, ys = _line_xy(points)
    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="lines+markers",
        line=dict(color="white", width=2),
        marker=dict(color="white", size=8),
        hoverinfo="skip",
        showlegend=False,
        uid="slice-line",
    ))


@app.callback(
    Output("slice-graph", "figure", allow_duplicate=True),
    Output("line-draw", "data"),
    Input("transect-points", "data"),
    State("line-draw", "data"),
    prevent_initial_call=True,
)
def draw_line_on_slice(points, seq):
    """Add the corner to the slice that is already on screen, zoom included."""
    xs, ys = _line_xy(points)
    patch = Patch()
    patch["data"][1]["x"] = xs
    patch["data"][1]["y"] = ys
    return patch, int(seq or 0) + 1


@app.callback(
    Output("transect-graph", "figure", allow_duplicate=True),
    Input("line-draw", "data"),
    State("transect-points", "data"),
    State("meta", "data"),
    State("direction", "value"),
    State("offset", "value"),
    State("time", "value"),
    State("quality", "value"),
    State("palette", "value"),
    State("window", "value"),
    State("depth-axis", "value"),
    State("depth-zero-top", "value"),
    prevent_initial_call=True,
)
def update_depth_after_line(
    _seq, points, meta, direction, offset, timestep, quality, palette, window, depth_axis, zero_top,
):
    """The depth plot follows the line. It runs after the line is on the slice."""
    if not meta or CACHE.db is None:
        return _empty_figure("Depth transect")
    try:
        return _transect_for_line(
            points, direction, offset, timestep, quality, palette, window, depth_axis, zero_top,
            tuple(meta.get("logic_shape") or CACHE.logic_shape or ()),
        )
    except Exception as ex:
        print(f"[VolumeExplorer] depth update failed: {ex}")
        traceback.print_exc()
        return _empty_figure("Depth transect")


def _transect_for_line(
    points, direction, offset, timestep, quality, palette, window, depth_axis, zero_top, logic_shape,
):
    direction = int(direction) if int(direction or 0) in (0, 1, 2) else 2
    depth_axis = int(depth_axis) if int(depth_axis if depth_axis is not None else direction) in (0, 1, 2) else direction
    zero_at_top = "top" in (zero_top or [])
    timestep = int(timestep or 0)
    quality = int(quality if quality is not None else -6)
    vmin, vmax = (window or [0, 1])[:2]
    colorscale = palette_record(palette)["plotly"]
    logic_shape = tuple(logic_shape or ())
    if len(logic_shape) < 3:
        image = np.squeeze(np.asarray(CACHE.db.read(time=timestep, quality=quality)))
        _shown, step = downsample_2d(mask_to_window(image, vmin, vmax))
        return _transect_from_points(image, points, step, colorscale, vmin, vmax, depth=False)

    layer = clamp_layer(offset, layer_count(logic_shape, direction))
    remembered = CACHE.plane or {}
    same = (
        remembered.get("direction") == direction
        and remembered.get("layer") == int(layer)
        and remembered.get("timestep") == timestep
        and remembered.get("quality") == quality
        and tuple(remembered.get("logic_shape") or ()) == logic_shape
    )
    if same:
        step = int(remembered["step"])
        plane_shape = remembered["plane_shape"]
    else:
        plane = read_plane(
            CACHE.db, logic_shape, direction, layer, timestep,
            field=CACHE.scalar_field, quality=quality,
        )
        if plane is None:
            volume, _vectors = _get_volume(timestep, VOLUME_QUALITY)
            coarse_offset = map_offset(float(layer), layer_count(logic_shape, direction), volume.shape[direction])
            plane = plane_from_volume(volume, direction, coarse_offset)
        _shown, step = downsample_2d(np.asarray(plane))
        plane_shape = tuple(int(v) for v in np.asarray(plane).shape)
    volume, _vectors = _get_volume(timestep, VOLUME_QUALITY)
    coarse_offset = map_offset(float(layer), layer_count(logic_shape, direction), volume.shape[direction])
    return _transect_from_points(
        volume, points, step, colorscale, vmin, vmax,
        depth=True, direction=direction, plane_shape=plane_shape,
        depth_axis=depth_axis, logic_shape=logic_shape,
        zero_at_top=zero_at_top, slice_layer=layer,
        volume_layer=coarse_offset, timestep=timestep,
    )


def _polyline_xyz(points, step, plane_shape, volume_shape, direction, layer):
    """Line vertices as volume indices. The slice offset is the fixed coordinate."""
    uv = _polyline_uv(points, step, plane_shape, volume_shape, direction)
    if len(uv) < 2:
        return []
    axis_u, axis_v = orthogonal_axes(int(direction))
    fixed = float(np.clip(layer, 0, volume_shape[int(direction)] - 1))
    samples = []
    for u, v in uv:
        point = [0.0, 0.0, 0.0]
        point[axis_u] = float(u)
        point[axis_v] = float(v)
        point[int(direction)] = fixed
        samples.append(tuple(point))
    return samples


def _polyline_uv(points, step, plane_shape, volume_shape, direction):
    vertices = _line_vertices(points)
    if len(vertices) < 2:
        return []
    step = max(int(step or 1), 1)
    uv = []
    for pt in vertices:
        along_u = min(max(float(pt["row"]) * step, 0), plane_shape[0] - 1)
        along_v = min(max(float(pt["col"]) * step, 0), plane_shape[1] - 1)
        uv.append(fraction_point((along_u, along_v), plane_shape, volume_shape, direction))
    return uv


def _logic_line(points, step, plane_shape, logic_shape, direction, slice_layer, count=72):
    """Polyline corners in logic coordinates, resampled along the drawn path."""
    vertices = _line_vertices(points)
    if len(vertices) < 2 or len(logic_shape) < 3:
        return []
    axis_u, axis_v = orthogonal_axes(int(direction))
    step = max(int(step or 1), 1)
    corners = []
    for pt in vertices:
        row = min(max(float(pt["row"]) * step, 0.0), max(plane_shape[0] - 1, 0))
        col = min(max(float(pt["col"]) * step, 0.0), max(plane_shape[1] - 1, 0))
        point = [0.0, 0.0, 0.0]
        point[axis_v] = row / max(plane_shape[0] - 1, 1) * max(logic_shape[axis_v] - 1, 0)
        point[axis_u] = col / max(plane_shape[1] - 1, 1) * max(logic_shape[axis_u] - 1, 0)
        point[int(direction)] = float(slice_layer)
        corners.append(point)
    lengths = [float(np.linalg.norm(np.subtract(b, a))) for a, b in zip(corners, corners[1:])]
    total = float(sum(lengths))
    if total < 1e-3:
        return [tuple(corners[0]), tuple(corners[-1])]
    budget = max(2, int(count))
    samples = []
    for (start, end), length in zip(zip(corners, corners[1:]), lengths):
        steps = max(2, int(round(budget * max(length, 1e-6) / total)))
        for index, t in enumerate(np.linspace(0.0, 1.0, steps)):
            if samples and index == 0:
                continue
            point = [float(start[axis]) + (float(end[axis]) - float(start[axis])) * float(t) for axis in range(3)]
            samples.append(tuple(point))
    return samples


def _full_depth_curtain(points, step, plane_shape, logic_shape, direction, slice_layer, depth_axis, timestep):
    """Curtain from full-depth IDX columns. None when that read is unavailable."""
    if CACHE.db is None or len(logic_shape) < 3:
        return None, None
    samples = _logic_line(points, step, plane_shape, logic_shape, direction, slice_layer, count=48)
    if len(samples) < 2:
        return None, None
    key = (
        int(timestep or 0),
        CACHE.scalar_field,
        int(depth_axis),
        tuple(tuple(round(float(value), 1) for value in point) for point in samples),
    )
    if key not in CACHE.curtains:
        try:
            curtain = read_depth_columns(
                CACHE.db,
                logic_shape,
                depth_axis,
                samples,
                int(timestep or 0),
                field=CACHE.scalar_field,
                quality=0,
            )
        except Exception as ex:
            print(f"[VolumeExplorer] depth columns failed: {ex}")
            curtain = None
        CACHE.curtains[key] = curtain
        if curtain is not None:
            print(
                f"[VolumeExplorer] depth columns shape={tuple(curtain.shape)} "
                f"logic depth={layer_count(logic_shape, depth_axis)}"
            )
    image = CACHE.curtains.get(key)
    if image is None:
        return None, None
    others = [axis for axis in range(3) if axis != int(depth_axis)]
    distance = [0.0]
    for start, end in zip(samples, samples[1:]):
        step_len = float(np.hypot(end[others[0]] - start[others[0]], end[others[1]] - start[others[1]]))
        distance.append(distance[-1] + step_len)
    if len(distance) != image.shape[1]:
        distance = np.linspace(0, distance[-1] if distance else 1, image.shape[1])
    return image, np.asarray(distance, dtype=np.float32)


def _transect_from_points(
    source, points, step, colorscale, vmin, vmax, depth,
    direction=2, plane_shape=None, depth_axis=2, logic_shape=(),
    zero_at_top=True, slice_layer=0, volume_layer=None, timestep=0,
):
    plane_shape = plane_shape or getattr(source, "shape", (1, 1))
    if not depth:
        vertices = _line_vertices(points)
        if len(vertices) < 2:
            return _empty_figure("Depth transect — click to add corners of a line")
        step = max(int(step or 1), 1)
        values = []
        for start, end in zip(vertices, vertices[1:]):
            p0 = (min(max(float(start["row"]) * step, 0), source.shape[0] - 1),
                  min(max(float(start["col"]) * step, 0), source.shape[1] - 1))
            p1 = (min(max(float(end["row"]) * step, 0), source.shape[0] - 1),
                  min(max(float(end["col"]) * step, 0), source.shape[1] - 1))
            count = max(2, int(round(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))))
            for row, col in zip(np.linspace(p0[0], p1[0], count), np.linspace(p0[1], p1[1], count)):
                r = int(np.clip(round(row), 0, source.shape[0] - 1))
                c = int(np.clip(round(col), 0, source.shape[1] - 1))
                values.append(source[r, c])
        fig = go.Figure(data=go.Scatter(y=values, mode="lines", line=dict(color="#4E477F")))
        fig.update_layout(title="Line sample", margin=dict(l=40, r=20, t=40, b=30), height=280, yaxis_title="value")
        return fig
    depth_axis = int(depth_axis) if int(depth_axis or 0) in (0, 1, 2) else int(direction)
    fixed = slice_layer if volume_layer is None else volume_layer
    samples = _polyline_xyz(points, step, plane_shape, source.shape, direction, fixed)
    if len(samples) < 2:
        return _empty_figure("Depth transect — click to add corners of a line")
    image, distance = _full_depth_curtain(
        points, step, plane_shape, logic_shape, direction, slice_layer, depth_axis, timestep,
    )
    if image is None:
        curtain = sample_curtain(source, depth_axis, samples)
        if curtain is None:
            return _empty_figure("Depth transect")
        image, distance = curtain
    shown = mask_to_window(image, vmin, vmax)
    if not np.isfinite(shown).any():
        data_min, data_max = finite_minmax(image)
        return _empty_figure(
            f"Depth transect — no samples inside {float(vmin):.4g}–{float(vmax):.4g} "
            f"(line spans {data_min:.4g}–{data_max:.4g})"
        )
    length = layer_count(logic_shape, depth_axis) if logic_shape else image.shape[0]
    last = max(int(length) - 1, 0)
    offsets = np.linspace(0, last, image.shape[0])
    fig = go.Figure(data=go.Heatmap(
        z=shown,
        x=np.asarray(distance),
        y=offsets,
        colorscale=colorscale,
        zmin=vmin,
        zmax=vmax,
        colorbar=dict(title="value", len=0.8),
        hovertemplate=(
            "along line %{x:.0f}<br>"
            f"{AXIS_NAMES[depth_axis]} offset %{{y:.0f}}<br>"
            "%{z}<extra></extra>"
        ),
    ))
    y_range = [float(offsets[-1]), float(offsets[0])] if zero_at_top else [float(offsets[0]), float(offsets[-1])]
    fig.update_layout(
        title=f"Depth under the line · {AXIS_NAMES[depth_axis]}",
        margin=dict(l=40, r=20, t=40, b=30),
        height=280,
        xaxis_title="along the line (start → end)",
        yaxis_title=f"{AXIS_NAMES[depth_axis]} offset",
    )
    fig.update_yaxes(range=y_range, autorange=False)
    if depth_axis == int(direction):
        fig.add_hline(y=float(slice_layer), line_width=1, line_dash="dot", line_color="white")
    return fig


def _seeds(volume_shape, direction, offset, points, step, plane_shape):
    uv = _polyline_uv(points, step, plane_shape, volume_shape, direction)
    if len(uv) < 2:
        return seeds_for_streamlines(volume_shape, direction, offset)
    seeds = []
    for start, end in zip(uv, uv[1:]):
        seeds.extend(seeds_for_streamlines(volume_shape, direction, offset, start, end, rake=3))
    return seeds


@app.callback(
    Output("depth-axis", "value"),
    Input("direction", "value"),
)
def follow_slice_axis(direction):
    """The curtain starts on the same axis as the slice. The dropdown can override it."""
    return int(direction) if int(direction or 0) in (0, 1, 2) else 2


@app.callback(
    Output("slice-revision", "data"),
    Input("reset-zoom", "n_clicks"),
    State("slice-revision", "data"),
    prevent_initial_call=True,
)
def refresh_slice_zoom(n_clicks, revision):
    """Reset zoom rebuilds the slice. A click that adds a line corner does not."""
    if not n_clicks:
        return no_update
    return int(revision or 0) + 1


@app.callback(
    Output("save-status", "children"),
    Input("save-view", "n_clicks"),
    State("meta", "data"),
    State("direction", "value"),
    State("offset", "value"),
    State("time", "value"),
    State("quality", "value"),
    State("palette", "value"),
    State("window", "value"),
    prevent_initial_call=True,
)
def save_default(n_clicks, meta, direction, offset, timestep, quality, palette, window):
    if not n_clicks or not meta:
        return no_update
    record = palette_record(palette)
    vmin, vmax = (window or [None, None])[:2]
    prefs = {
        "direction": int(direction if direction is not None else 2),
        "offset": float(offset or 0),
        "timestep": int(timestep or 0),
        "palette": record["openvisus"],
        "colormap": "linear",
        "range_mode": "user",
        "range_min": float(vmin),
        "range_max": float(vmax),
        "auto_res": True,
        "field": meta.get("scalar_field"),
        "transfer_function": {
            "palette": record["openvisus"],
            "window": [float(vmin), float(vmax)],
            "opacity": [[0.0, 0.0], [0.15, 0.25], [1.0, 0.85]],
        },
    }
    ok, message = save_dataset_view_prefs(COLLECTION, meta.get("uuid"), prefs, current_user_email())
    return message


if __name__ == "__main__":
    app.run(debug=False, port=PORT, host="0.0.0.0", use_reloader=False)
