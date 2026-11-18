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
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
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
    opacity_nodes,
    palette_family,
    palette_record,
    polydata_mesh_state,
    read_coarse_volume,
    read_plane,
    read_vector_volume,
    scalar_histogram,
    seeds_for_streamlines,
    slice_from_volume,
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


def _heatmap(image, title, colorscale, vmin, vmax, height=460, x_title="column", y_title="row"):
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
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
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


def _volume_view(volume, vectors, vmin, vmax, seeds, show_lines, preset):
    if dash_vtk is None:
        return html.Div("vtk.js is not installed in this dashboard image.")
    windowed, nodata = apply_opacity_window(volume, vmin, vmax)
    children = [
        dash_vtk.VolumeRepresentation(
            [dash_vtk.Volume(state=volume_mesh_state(windowed))],
            colorMapPreset=preset,
            colorDataRange=[float(vmin), float(vmax)],
            property={
                "scalarOpacityUnitDistance": 1.0,
                "scalarOpacity": opacity_nodes(nodata, vmin, vmax),
            },
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
    view = dash_vtk.View(
        children,
        background=[0.04, 0.04, 0.06],
    )
    return html.Div([
        html.Div(view, style={"height": "460px", "width": "100%"}),
        html.Div(note, style={"color": "#666", "fontSize": "13px", "marginTop": "6px"}),
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
        dcc.Graph(id="slice-graph", figure=_empty_figure("Slice"), config={"displaylogo": False}),
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
        html.Div(
            "Click two points on the slice to draw a line. The lower-right image is the depth under that line.",
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
        "Click two points on the slice to sample depth along that line.",
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


@app.callback(
    Output("transect-points", "data"),
    Input("slice-graph", "clickData"),
    State("transect-points", "data"),
)
def collect_transect(click, current):
    if not click or not click.get("points"):
        return current or {}
    point = click["points"][0]
    if "x" not in point or "y" not in point:
        return current or {}
    stored = {"row": float(point["y"]), "col": float(point["x"])}
    current = current or {}
    if not current.get("p0") or current.get("p1"):
        return {"p0": stored, "p1": None}
    return {"p0": current["p0"], "p1": stored}


@app.callback(
    Output("slice-graph", "figure"),
    Output("transect-graph", "figure"),
    Output("hist-graph", "figure"),
    Output("volume-pane", "children"),
    Input("meta", "data"),
    Input("direction", "value"),
    Input("offset", "value"),
    Input("time", "value"),
    Input("quality", "value"),
    Input("palette", "value"),
    Input("window", "value"),
    Input("transect-points", "data"),
    Input("streamlines", "value"),
)
def render_views(meta, direction, offset, timestep, quality, palette, window, points, streamlines):
    if not meta or CACHE.db is None:
        return (
            _empty_figure("Slice"),
            _empty_figure("Depth transect"),
            _empty_figure("Scalar range"),
            html.Div("Load a dataset to render the volume."),
        )
    direction = int(direction) if int(direction or 0) in (0, 1, 2) else 2
    timestep = int(timestep or 0)
    quality = int(quality if quality is not None else -6)
    axis_u, axis_v = (0, 1) if direction == 2 else ((0, 2) if direction == 1 else (1, 2))
    # The plane array is (axis_u, axis_v). Plotly draws columns across and rows up,
    # so the horizontal axis is axis_v and the vertical axis is axis_u.
    x_title, y_title = AXIS_NAMES[axis_v], AXIS_NAMES[axis_u]
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
            hist = _histogram_figure(image, vmin, vmax)
            transect = _transect_from_points(image, points, step, colorscale, vmin, vmax, depth=False)
            volume = html.Div("This dataset is 2D, so there is no volume to raycast.")
            return slice_fig, transect, hist, volume

        volume, vectors = _get_volume(timestep, quality)
        layer = clamp_layer(offset, layer_count(logic_shape, direction))
        plane = None
        try:
            plane = read_plane(
                CACHE.db,
                logic_shape,
                direction,
                layer,
                timestep,
                field=CACHE.scalar_field,
                quality=min(quality + 3, 0),
            )
        except Exception as ex:
            print(f"[VolumeExplorer] plane query failed: {ex}")
            plane = None
        coarse_offset = map_offset(
            float(layer),
            layer_count(logic_shape, direction),
            volume.shape[direction],
        )
        if plane is None:
            plane = slice_from_volume(volume, direction, coarse_offset)
        shown, step = downsample_2d(mask_to_window(np.asarray(plane), vmin, vmax))
        slice_fig = _heatmap(
            shown,
            f"{PLANE_NAMES[direction]} plane · {AXIS_NAMES[direction]} = {layer}",
            colorscale,
            vmin,
            vmax,
            x_title=x_title,
            y_title=y_title,
        )
        _draw_line(slice_fig, points)
        hist = _histogram_figure(volume, vmin, vmax)
        transect = _transect_from_points(
            volume, points, step, colorscale, vmin, vmax,
            depth=True, direction=direction, plane_shape=plane.shape,
        )
        seeds = _seeds(volume.shape, direction, coarse_offset, points, step, plane.shape)
        volume_pane = _volume_view(volume, vectors, float(vmin), float(vmax), seeds, show_lines, record["vtk"])
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


def _draw_line(fig, points):
    if not points or not points.get("p0"):
        return
    p0 = points["p0"]
    p1 = points.get("p1") or p0
    fig.add_trace(go.Scatter(
        x=[p0["col"], p1["col"]],
        y=[p0["row"], p1["row"]],
        mode="lines+markers",
        line=dict(color="white", width=2),
        marker=dict(color="white", size=8),
        hoverinfo="skip",
        showlegend=False,
    ))


def _plane_points(points, step, plane_shape, transposed=False):
    if not points or not points.get("p0") or not points.get("p1"):
        return None
    step = max(int(step or 1), 1)

    def one(pt):
        # The Z view is transposed so X runs horizontally. Clicks then have
        # col = first in-plane axis and row = second.
        if transposed:
            along_u = float(pt["col"]) * step
            along_v = float(pt["row"]) * step
        else:
            along_u = float(pt["row"]) * step
            along_v = float(pt["col"]) * step
        along_u = min(max(along_u, 0), plane_shape[0] - 1)
        along_v = min(max(along_v, 0), plane_shape[1] - 1)
        return along_u, along_v

    return one(points["p0"]), one(points["p1"])


def _transect_from_points(source, points, step, colorscale, vmin, vmax, depth, direction=2, plane_shape=None, transposed=False):
    plane_shape = plane_shape or getattr(source, "shape", (1, 1))
    picked = _plane_points(points, step, plane_shape, transposed=transposed)
    if not picked:
        return _empty_figure("Depth transect — click two points on the slice")
    p0, p1 = picked
    if not depth:
        count = 200
        rows = np.linspace(p0[0], p1[0], count)
        cols = np.linspace(p0[1], p1[1], count)
        values = []
        for row, col in zip(rows, cols):
            r = int(np.clip(round(row), 0, source.shape[0] - 1))
            c = int(np.clip(round(col), 0, source.shape[1] - 1))
            values.append(source[r, c])
        fig = go.Figure(data=go.Scatter(y=values, mode="lines", line=dict(color="#4E477F")))
        fig.update_layout(title="Line sample", margin=dict(l=40, r=20, t=40, b=30), height=280, yaxis_title="value")
        return fig
    u0, v0 = fraction_point(p0, plane_shape, source.shape, direction)
    u1, v1 = fraction_point(p1, plane_shape, source.shape, direction)
    from SCLib_Dashboards.SCDash_volume_explorer import transect_image
    image = transect_image(source, direction, (u0, v0), (u1, v1))
    image = mask_to_window(image, vmin, vmax)
    fig = _heatmap(image, "Depth under the line", colorscale, vmin, vmax, height=280)
    fig.update_layout(xaxis_title="distance along line", yaxis_title="depth")
    fig.update_yaxes(scaleanchor=None, autorange="reversed")
    return fig


def _seeds(volume_shape, direction, offset, points, step, plane_shape, transposed=False):
    picked = _plane_points(points, step, plane_shape, transposed=transposed)
    if not picked:
        return seeds_for_streamlines(volume_shape, direction, offset)
    p0, p1 = picked
    u0, v0 = fraction_point(p0, plane_shape, volume_shape, direction)
    u1, v1 = fraction_point(p1, plane_shape, volume_shape, direction)
    return seeds_for_streamlines(volume_shape, direction, offset, (u0, v0), (u1, v1))


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
