import matplotlib.colors as mcolors
import numpy as np
import sys
from html import escape
from typing import Any, DefaultDict, List, Optional, Tuple
import os
import atexit
from collections import defaultdict
import csv
import json
import time
import traceback
import re
import requests
from dotenv import load_dotenv
from botocore.client import Config
from boto3.session import Session
from bisect import bisect_left
from datetime import datetime, timezone

import OpenVisus as ov
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlsplit, urlunsplit
from bokeh.io import curdoc
from bokeh.models.widgets import Div
from bokeh.plotting import figure
from bokeh.layouts import row, column, gridplot
from bokeh.models import Button, AutocompleteInput, MultiChoice, Checkbox, CustomJS, TextInput, PasswordInput
from bokeh.models import (
    GlyphRenderer,
    HoverTool,
    BoxZoomTool,
    PanTool,
    ResetTool,
    SaveTool,
    WheelZoomTool,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
SHARED_UTILS_DIR = os.path.join(PROJECT_ROOT, "scientistCloudLib", "SCLib_Dashboards")
if SHARED_UTILS_DIR not in sys.path and os.path.isdir(SHARED_UTILS_DIR):
    sys.path.insert(0, SHARED_UTILS_DIR)

from utils_bokeh_dashboard import initialize_dashboard
from utils_bokeh_mongodb import cleanup_mongodb
from utils_bokeh_param import parse_remote_dataset_uri
from utils_darkmatter import get_aws_bucket, check_if_key_exists, PREFIX
try:
    from SCLib_Dashboards import create_header_banner, resolve_local_idx_file
except Exception:
    try:
        from SCDash_dataset_resolver import resolve_local_idx_file
    except Exception:
        resolve_local_idx_file = None
    def create_header_banner(dataset_name: str = "", dashboard_type: str = "Dashboard"):
        sc_blue = "#4E477F"
        title_text = (
            f"ScientistCloud | {dashboard_type}: {dataset_name}"
            if dataset_name
            else f"ScientistCloud | {dashboard_type}"
        )
        return Div(
            text=(
                f'<div class="dashboard-header-banner" style="background-color: {sc_blue}; '
                'padding: 10px 20px; display: flex; align-items: center; border-radius: 0; '
                '">'
                '<img src="https://scientistcloud.com/portal/assets/images/scientistCloudLogo_noText.png" '
                'style="height: 40px; margin-right: 15px;">'
                f'<span style="color: white; font-family: sans-serif; font-size: 1.5em; '
                f'font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">{title_text}</span>'
                '</div>'
            ),
            sizing_mode="stretch_width",
            styles={
                "width": "100vw",
                "max-width": "100vw",
                "margin": "0",
                "padding": "0",
                "position": "relative",
                "background-color": sc_blue,
                "border-bottom": "3px solid #75c0de",
                "margin-bottom": "20px",
            },
        )


# detectors_map = {'10000_2_Phonon4096': False, '10000_1_Phonon4096': False}
# channel_to_renderer = {'10000_2_Phonon4096_C1': GlyphRender(), '10000_1_Phonon4096_C1': GlyphRenderer()}

INFO = "INFO"
ERROR = "ERROR"
SUCCESS = "SUCCESS"


def _valid_email_or_none(value):
    if not value:
        return None
    candidate = str(value).strip()
    if not candidate:
        return None
    # Avoid sending placeholders like "auth0_session_user" to strict API validators.
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", candidate):
        return candidate
    return None


def _looks_like_dataset_uuid(value: str) -> bool:
    """Portal mode passes a real UUID; local `bokeh serve` leaves uuid as 'local'."""
    s = str(value or "").strip().lower()
    if not s or s in ("local", "none"):
        return False
    return bool(
        re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", s)
    )


LEFT_ARROW = """
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
</svg>
"""

RIGHT_ARROW = """
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
  <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
</svg>
"""

LEFT_DOUBLE_ARROW = """
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
  <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 4.5-7.5 7.5 7.5 7.5m-6-15L5.25 12l7.5 7.5" />
</svg>
"""

RIGHT_DOUBLE_ARROW = """
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
  <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 4.5 7.5 7.5-7.5 7.5m6-15 7.5 7.5-7.5 7.5" />
</svg>
"""

FILES_VOLUME = "./idx/"
COLORS = [
    "#ff0000",  # Red
    "#ffff00",  # Yellow
    "#0000ff",  # Blue
    "#ff00ff",  # Magenta
    "#00ff00",  # Green
    "#800080",  # Purple
    "#00ffff",  # Cyan
]


def get_request_args():
    doc = curdoc()
    request = doc.session_context.request if hasattr(doc, "session_context") and doc.session_context else None
    if not request:
        return None, {}

    request_args = {}
    if hasattr(request, "arguments") and request.arguments:
        request_args = request.arguments
    elif hasattr(request, "query_string") and request.query_string:
        request_args = parse_qs(request.query_string)
        for key in list(request_args.keys()):
            if isinstance(request_args[key], list) and len(request_args[key]) > 0:
                value = request_args[key][0]
                request_args[key] = [value.decode("utf-8") if isinstance(value, bytes) else value]
    return request, request_args


request, request_args = get_request_args()
has_args = request is not None and len(request_args) > 0
deploy_server = os.getenv("DEPLOY_SERVER", "")

# Global context populated by dashboard initialization.
uuid = "local"
server = "false"
name = "Nexus DM Dashboard"
base_dir = None
save_dir = None
is_authorized = True
user_email = None
mymongodb = None
collection = None
collection1 = None
team_collection = None
shared_team_collection = None
init_failed = False

if has_args:
    class RequestWithArgs:
        def __init__(self, real_request, args_dict):
            for attr in dir(real_request):
                if not attr.startswith("_"):
                    try:
                        setattr(self, attr, getattr(real_request, attr))
                    except Exception:
                        pass

            self.arguments = {}
            for key, value in args_dict.items():
                self.arguments[key] = value if isinstance(value, list) else [value]

    request_with_args = RequestWithArgs(request, request_args)
    init_result = initialize_dashboard(request_with_args, print)

    if not init_result["success"]:
        init_failed = True
        error_div = Div(
            text=f"<h2>❌ Error: {init_result['error']}</h2>",
            styles={"color": "red", "font-size": "14px"},
        )
        curdoc().add_root(error_div)
    else:
        auth_result = init_result["auth_result"]
        mongodb = init_result["mongodb"]
        params = init_result["params"]

        uuid = params["uuid"]
        server = params["server"]
        name = params["name"]
        base_dir = params.get("base_dir")
        save_dir = params.get("save_dir")
        is_authorized = auth_result["is_authorized"]
        user_email = auth_result["user_email"]

        if mongodb:
            mymongodb = mongodb["mymongodb"]
            collection = mongodb["collection"]
            collection1 = mongodb["collection1"]
            team_collection = mongodb["team_collection"]
            shared_team_collection = mongodb.get("shared_team_collection")


class EventMetadata:
    def __init__(self):
        self.trigger_type = "Unknown"
        self.readout_type = "None"
        self.global_timestamp = "None"

    def extract(self, headers: List[str], metadata: List[str]):
        for i, h in enumerate(headers):
            key = h.strip()
            if key == "trigger_type":
                self.trigger_type = metadata[i].strip()
            elif key == "readout_type":
                self.readout_type = metadata[i].strip()
            elif key == "global_timestamp":
                dt = datetime.fromtimestamp(int(metadata[i].strip()), tz=timezone.utc)
                self.global_timestamp = dt.strftime('%A, %B %d, %Y %I:%M:%S %p UTC')

def create_channel_metadata_map(filepath: str) -> DefaultDict[str, List]:
    mp = defaultdict(list)
    with open(filepath, "r") as f:
        for line in f:
            channel_name, lo, hi = line.split(" ")
            mp[channel_name].append(int(lo))
            mp[channel_name].append(int(hi))
    f.close()
    return mp


def create_channel_metadata_map_from_lines(lines: List[str]) -> DefaultDict[str, List]:
    mp = defaultdict(list)
    for raw in lines:
        line = str(raw).strip()
        if not line:
            continue
        channel_name, lo, hi = line.split(" ")
        mp[channel_name].append(int(lo))
        mp[channel_name].append(int(hi))
    return mp


def create_event_metadata_map(filepath: str) -> DefaultDict[str, EventMetadata]:
    mp = defaultdict(EventMetadata)
    i = 0
    headers = []
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        for line in reader:
            if i == 0:
                headers = line
            else:
                evt_metadata = EventMetadata()
                evt_metadata.extract(headers, line)
                mp[line[0]] = evt_metadata
            i += 1
    f.close()
    return mp


def create_event_metadata_map_from_lines(lines: List[str]) -> DefaultDict[str, EventMetadata]:
    mp = defaultdict(EventMetadata)
    reader = csv.reader(lines)
    headers = []
    for i, line in enumerate(reader):
        if i == 0:
            headers = line
            continue
        evt_metadata = EventMetadata()
        evt_metadata.extract(headers, line)
        mp[line[0]] = evt_metadata
    return mp


def generate_palette(hex_color, steps=8):
    """Generate a palette of 20 colors from a given hex color"""
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "gradient", [hex_color, "#FFFFFF"], N=steps
    )
    palette = [mcolors.to_hex(cmap(i)) for i in range(steps)]
    return palette


def get_mid_files(remote_url: str):
    mid_files = []
    if remote_url != "":
        uploaded_files_path = "./uploaded_files.txt"
        if os.path.exists(uploaded_files_path):
            with open(uploaded_files_path) as f:
                for line in f:
                    mid_file = line.strip()
                    if mid_file:
                        mid_files.append(mid_file)
    else:
        for filename in os.listdir(FILES_VOLUME):
            if filename.endswith(".mid") or filename.endswith(".mid.gz"):
                mid_files.append(filename.split(".")[0])
    return mid_files


def parse_s3_uri(uri: str):
    candidate = str(uri or "").strip()
    if not candidate.startswith("s3://"):
        return None, None
    no_scheme = candidate[len("s3://"):]
    # Support OpenVisus-style credentials: s3://access_key:secret_key@bucket/key
    if "@" in no_scheme.split("/", 1)[0]:
        _userinfo, _, no_scheme = no_scheme.partition("@")
    if "/" not in no_scheme:
        return no_scheme, ""
    bucket, key = no_scheme.split("/", 1)
    return bucket, key


def s3_uri_with_embedded_credentials(s3_uri: str, access_key: str, secret_key: str) -> str:
    """
    Embed credentials in an s3:// URL the way OpenVisus expects:
    ``s3://access_key:secret_key@bucket/key`` (keys URL-encoded for special characters).
    """
    bucket, key = parse_s3_uri(s3_uri)
    ak = str(access_key or "").strip()
    sk = str(secret_key or "").strip()
    if not bucket or not ak or not sk:
        return str(s3_uri or "").strip()
    userinfo = f"{quote(ak, safe='')}:{quote(sk, safe='')}"
    return f"s3://{userinfo}@{bucket}/{key}" if key else f"s3://{userinfo}@{bucket}"


def gateway_endpoint_requires_path_style(endpoint_url: str) -> bool:
    """
    True for custom S3 gateways (FTH, MinIO, Wasabi-style) where virtual-host URLs like
    ``https://bucket.endpoint/...`` break TLS (cert is issued for the gateway host only).

    OpenVisus often turns ``s3://bucket/key`` into that virtual-host form when
    ``AWS_ENDPOINT_URL`` points at a custom gateway — producing hostnames such as
    ``scientistcloud.us-east-1.gw.future-tech-holdings.com``. Prefer path-style HTTPS.
    """
    host = (urlsplit(str(endpoint_url or "").strip()).netloc or str(endpoint_url or "")).lower()
    if not host:
        return True
    if "amazonaws.com" in host:
        return False
    return True


def _s3_addressing_styles_for_endpoint(endpoint_url: Optional[str] = None) -> tuple:
    """Path-only on custom gateways; path+virtual on real AWS."""
    if gateway_endpoint_requires_path_style(endpoint_url or ""):
        return ("path",)
    return ("path", "virtual")


def _redact_url_secrets(url: str) -> str:
    """Mask credential-like query params and s3:// userinfo for logs (values become '...')."""
    out = str(url or "").strip()
    if not out:
        return out
    # s3://access_key:secret_key@bucket/key
    if out.lower().startswith("s3://"):
        rest = out[5:]
        if "@" in rest:
            userinfo, _, hostpath = rest.partition("@")
            if ":" in userinfo:
                out = f"s3://...@{hostpath}"
    # Common query-string secrets (gateway, AWS, generic)
    for param in (
        "secret_key",
        "access_key",
        "secret_access_key",
        "access_key_id",
        "password",
        "token",
        "api_key",
        "apikey",
        "signature",
        "x-amz-signature",
        "x-amz-security-token",
        "x-amz-credential",
        "awsaccesskeyid",
    ):
        out = re.sub(
            rf"([?&]{re.escape(param)}=)[^&]*",
            r"\1...",
            out,
            flags=re.I,
        )
    return out


def _patch_access_stub_idx_for_openvisus(idx_path: str) -> str:
    """No-op: never rewrite idx content (arco / compression / filename_template)."""
    return idx_path


def _probe_openvisus_block0_http(block_url: str) -> None:
    """Log whether OpenVisus's block0 HTTPS URL is reachable (auth / hairpin diagnosis)."""
    u = str(block_url or "").strip()
    if not u.startswith(("http://", "https://")):
        return
    try:
        resp = requests.get(u, timeout=30)
        body = resp.content or b""
        sample = body[:16].hex() if body else ""
        nonzero = sum(1 for b in body[:4096] if b != 0)
        print(
            f"[DarkMatter][DEBUG] block0 HTTP probe status={resp.status_code} "
            f"bytes={len(body)} nonzero_in_first_4k={nonzero} sample16={sample} "
            f"url={_redact_url_secrets(u)[:400]}"
        )
    except Exception as ex:
        print(f"[DarkMatter][WARN] block0 HTTP probe failed: {ex}")


def _log_openvisus_block0_url_for_diagnostics(db_outer, field_name: str) -> None:
    """When reads are all-zero, log where OpenVisus expects block 0 (helps HTTPS vs local idx issues in Dozzle)."""
    try:
        inner = getattr(db_outer, "db", db_outer)
        access = inner.createAccessForBlockQuery()
        fobj = inner.getField(field_name)
        ts = inner.getTimesteps()
        t0 = float(ts.getDefault())
        fn = str(access.getFilename(fobj, t0, 0))
        safe = _redact_url_secrets(fn)
        print(f"[DarkMatter][DEBUG] OpenVisus block0 target: {safe[:1200]}")
        _probe_openvisus_block0_http(fn)
    except Exception as ex:
        print(f"[DarkMatter][DEBUG] OpenVisus block0 path diagnostic failed: {ex}")


def read_openvisus_field(idx_url_or_path: str, field: str = "data"):
    """
    ``LoadDataset(uri)`` then ``read`` for field ``data`` (by default).

    The multi-step ``read`` attempts exist because **local multiresolution ARCO** idx files
    often return an all-zero array from a single ``read(field=...)`` unless ``max_resolution``
    / timestep are chosen carefully (same class of issue as other ScientistCloud Bokeh apps).

    **Remote HTTPS** tile reads are handled inside OpenVisus (C++); if those GETs fail or map
    to the wrong path, every Python-side ``read`` variant can still be all zeros — that is
    not fixed by simplifying this function. Use a resolved idx / working ``s3://`` binding,
    or set ``DARKMATTER_OPENVISUS_SIMPLE_READ=1`` to force the minimal ``read(field=...)`` only
    when comparing behavior.
    """
    if str(os.getenv("DARKMATTER_OPENVISUS_SIMPLE_READ", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        db = ov.LoadDataset(idx_url_or_path)
        out = db.read(field=field)
        print(
            "[DarkMatter][DEBUG] OpenVisus simple read path "
            "(DARKMATTER_OPENVISUS_SIMPLE_READ=1): LoadDataset + read(field) only"
        )
        return out

    db = ov.LoadDataset(idx_url_or_path)
    mr = None
    try:
        gmr = getattr(db, "getMaxResolution", None)
        if callable(gmr):
            raw = gmr()
            mr = int(raw) if raw is not None else None
    except Exception:
        mr = None

    try:
        mr_cap = max(0, int(os.getenv("DARKMATTER_MAX_RESOLUTION", "15")))
    except ValueError:
        mr_cap = 15
    mr_read = min(mr, mr_cap) if mr is not None else None
    if mr is not None and mr_read is not None and mr_read != mr:
        print(f"[DarkMatter][DEBUG] OpenVisus max_resolution capped: dataset_max={mr} read_max={mr_read} (DARKMATTER_MAX_RESOLUTION={mr_cap})")

    def _nonzero_count(sample) -> int:
        arr = np.asarray(sample)
        return int(np.count_nonzero(arr)) if arr.size else 0

    # Nexus-style idx: multi-timestep datasets often need an explicit time= on read().
    time_bases: List[dict] = [{}]
    try:
        gts = getattr(db, "getTimesteps", None)
        if callable(gts):
            ts = list(gts())
            if len(ts) > 1:
                time_bases = [{"time": ts[0]}, {}]
                print(f"[DarkMatter][DEBUG] OpenVisus getTimesteps count={len(ts)} first={ts[0]!r}")
            elif len(ts) == 1:
                time_bases = [{}, {"time": ts[0]}]
    except Exception:
        pass

    # Try several resolution levels; keep the finest successful read (largest pixel count). Coarser
    # levels often decode first when the cap is below dataset max, but the dashboard needs full logic size.
    res_to_try: List[int] = []
    if mr_read is not None:
        res_to_try = sorted({0, min(5, mr_read), min(10, mr_read), mr_read})
        res_to_try = list(dict.fromkeys(res_to_try))

    kwargs_order: List[tuple] = []
    for tkw in time_bases:
        for r in res_to_try:
            kwargs_order.append(
                (
                    {**tkw, "field": field, "max_resolution": r},
                    f"time={tkw.get('time', 'default')} max_resolution={r}",
                )
            )
            kwargs_order.append(
                (
                    {**tkw, "max_resolution": r, "field": field},
                    f"time={tkw.get('time', 'default')} max_resolution={r} (alt arg order)",
                )
            )
        kwargs_order.append(({**tkw, "field": field}, f"time={tkw.get('time', 'default')} default field read"))

    def _pixel_count(sample) -> int:
        arr = np.asarray(sample)
        return int(arr.size) if arr.size else 0

    best_sample = None
    best_pixels = -1
    best_label = ""
    last_sample = None
    for kwargs, label in kwargs_order:
        try:
            sample = db.read(**kwargs)
        except TypeError:
            continue
        last_sample = sample
        nz = _nonzero_count(sample)
        if nz > 0:
            px = _pixel_count(sample)
            if px > best_pixels:
                best_pixels = px
                best_sample = sample
                best_label = label

    # Cap can block full-resolution reads; try dataset max once and prefer it if larger / denser.
    if mr is not None and mr_read is not None and mr_read < mr:
        for tkw in time_bases:
            for kwargs, label in (
                ({**tkw, "field": field, "max_resolution": mr}, f"time={tkw.get('time', 'default')} max_resolution={mr} uncapped"),
                ({**tkw, "max_resolution": mr, "field": field}, f"time={tkw.get('time', 'default')} max_resolution={mr} uncapped alt order"),
            ):
                try:
                    sample = db.read(**kwargs)
                except TypeError:
                    continue
                nz = _nonzero_count(sample)
                if nz > 0:
                    px = _pixel_count(sample)
                    if px > best_pixels:
                        best_pixels = px
                        best_sample = sample
                        best_label = label

    if best_sample is not None:
        print(
            f"[DarkMatter][DEBUG] OpenVisus read ({best_label}) nonzero={_nonzero_count(best_sample)} "
            f"pixels={best_pixels}"
        )
        return best_sample

    if last_sample is not None and _nonzero_count(last_sample) == 0:
        _log_openvisus_block0_url_for_diagnostics(db, field)
        print(
            "[DarkMatter][WARN] OpenVisus read returned all zeros for tried time/resolution combinations; "
            "returning last sample for upstream diagnostics (verify ARCO .bin files match filename_template "
            "next to the .idx)"
        )
        u = str(idx_url_or_path or "").strip()
        if u.startswith(("http://", "https://")):
            print(
                "[DarkMatter][WARN] HTTPS idx: OpenVisus fetches tiles over HTTP inside the Visus "
                "library; all-zero here usually means those GETs failed or the remote .idx bin layout "
                "does not match objects on the gateway (not something this Python read loop can repair)."
            )
    if last_sample is not None:
        return last_sample
    return db.read(field=field)


# Resolved idx on disk uses ``visus.idx`` (matches ``openvisus-resolved-idx`` default / conversion output).
RESOLVED_IDX_S3_OUTPUT_NAME = "visus.idx"
RESOLVED_IDX_PROXY_OUTPUT_NAME = "visus_proxy.idx"


def _darkmatter_resolved_idx_filename_template_mode() -> str:
    """SCLib ``openvisus-resolved-idx`` rewrite mode for ``(filename_template)``.

    Default ``proxy`` serves ARCO bins via ``/api/v1/datasets/s3/object-proxy/...`` URLs.
    OpenVisus in Docker often returns all-zero / ``empty content`` with raw ``s3://``
    templates or gateway-misresolved HTTPS bin paths (see logs for ``/scientistcloud/...``).

    Set ``DARKMATTER_RESOLVED_IDX_FILENAME_TEMPLATE_MODE`` to ``s3`` or ``https`` if your
    OpenVisus build reads those reliably.
    """
    raw = (os.getenv("DARKMATTER_RESOLVED_IDX_FILENAME_TEMPLATE_MODE") or "").strip().lower()
    if raw in ("s3", "proxy", "https"):
        return raw
    return "proxy"


def read_openvisus_field_with_dataset_cwd(idx_url_or_path: str, field: str = "data"):
    """
    OpenVisus resolves relative filename_template paths against cwd, not the .idx directory.
    For filesystem idx paths, chdir to the idx parent before LoadDataset/read.
    """
    p = str(idx_url_or_path or "").strip()
    if not p:
        raise RuntimeError("empty idx path for OpenVisus load")
    if p.startswith(("http://", "https://", "s3://")):
        return read_openvisus_field(p, field=field)
    abs_p = os.path.abspath(p)
    abs_p = _patch_access_stub_idx_for_openvisus(abs_p)
    root = os.path.dirname(abs_p)
    prev = os.getcwd()
    try:
        os.chdir(root)
        print(f"[DarkMatter][DEBUG] cwd for OpenVisus load={root}")
        return read_openvisus_field(abs_p, field=field)
    finally:
        try:
            os.chdir(prev)
        except OSError:
            pass


def _darkmatter_disable_resolved_idx_api() -> bool:
    """Hard-off: never POST to openvisus-resolved-idx from the dashboard (overrides allow-launch)."""
    return str(os.getenv("DARKMATTER_DISABLE_RESOLVED_IDX", "")).strip().lower() in ("1", "true", "yes", "on")


def _darkmatter_may_post_openvisus_resolved_idx_on_launch() -> bool:
    """Never POST openvisus-resolved-idx from the dashboard (rewrites filename_template)."""
    return False


def _darkmatter_http_explicit_no_fallback() -> bool:
    """
    Linked (http_explicit): LoadDataset(HTTPS idx) only — no local mirrors, no idx rewrite.

    Default ON.
    """
    v = str(os.getenv("DARKMATTER_HTTP_EXPLICIT_NO_FALLBACK", "1")).strip().lower()
    return v not in ("0", "false", "no", "off")


def _darkmatter_may_use_object_proxy_for_linked() -> bool:
    """Never rewrite idx via object-proxy access stubs. Linked loads use LoadDataset(HTTPS) only."""
    return False


def _darkmatter_may_use_cached_resolved_idx_http() -> bool:
    """Never POST openvisus-resolved-idx (that rewrites filename_template)."""
    return False


def _materialized_resolved_visus_idx_path(
    runtime_dataset: Optional[dict],
    dataset_uuid: str,
    save_dir_hint: str = "",
) -> str:
    """Return path to converted/<uuid>/visus.idx (or visus_proxy.idx) when present on disk."""
    cip = str((runtime_dataset or {}).get("converted_idx_path") or "").strip()
    if cip and os.path.isfile(cip):
        return cip
    candidates: List[str] = []
    sd = str(save_dir_hint or "").strip()
    if sd:
        candidates.append(sd)
    if dataset_uuid:
        for root in (
            "/mnt/visus_datasets/converted",
            str(globals().get("save_dir") or "").strip(),
        ):
            if root:
                candidates.append(os.path.join(root, str(dataset_uuid)))
    seen = set()
    for base in candidates:
        if not base or base in seen:
            continue
        seen.add(base)
        for fname in ("visus.idx", "visus_proxy.idx"):
            p = os.path.join(base, fname)
            if os.path.isfile(p):
                return p
    return ""


def _materialized_resolved_visus_idx_missing(
    runtime_dataset: Optional[dict],
    dataset_uuid: str,
    save_dir_hint: str = "",
) -> bool:
    """True when converted/<uuid>/visus.idx is not on disk (background conversion not finished)."""
    return not bool(
        _materialized_resolved_visus_idx_path(runtime_dataset, dataset_uuid, save_dir_hint)
    )


def _try_resolve_and_load_openvisus_idx(
    *,
    dataset_identifier: str,
    user_email: Optional[str],
    auth_override: Optional[dict],
    force_refresh: bool,
    log_label: str,
) -> Optional[Any]:
    """POST openvisus-resolved-idx (generate if missing) and LoadDataset via resolved HTTP URL."""
    resolved_idx, resolved_http = resolve_openvisus_resolved_idx_via_api(
        dataset_identifier=dataset_identifier,
        user_email=user_email,
        auth_override=auth_override or {},
        output_filename=RESOLVED_IDX_S3_OUTPUT_NAME,
        filename_template_mode=_darkmatter_resolved_idx_filename_template_mode(),
        force_refresh=bool(force_refresh),
    )
    if not resolved_idx and not resolved_http:
        return None
    http_u = (resolved_http or "").strip()
    if http_u.startswith(("http://", "https://")):
        print(
            f"[DarkMatter][DEBUG] {log_label} LoadDataset via resolved-idx HTTP: "
            f"{_redact_url_secrets(http_u)}"
        )
        return read_openvisus_field(http_u)
    if resolved_idx and os.path.isfile(resolved_idx):
        print(f"[DarkMatter][DEBUG] {log_label} LoadDataset local resolved idx: {resolved_idx}")
        return read_openvisus_field_with_dataset_cwd(resolved_idx)
    return None


def resolve_openvisus_resolved_idx_via_api(
    *,
    dataset_identifier: Optional[str],
    user_email: Optional[str],
    auth_override: Optional[dict] = None,
    output_filename: str = "visus.idx",
    filename_template_mode: str = "proxy",
    force_refresh: bool = False,
    region_name: str = "us-east-1",
):
    """
    Ask SCLib fastapi to generate (and cache) a local resolved idx under
    /mnt/visus_datasets/converted/<dataset_uuid>/ for OpenVisus.

    The API will also convert to ARCO when the source idx has (arco) == 0.

    **Dashboard policy:** background ``SCLib_BackgroundService`` should run this once after upload.
    If ``converted/<uuid>/visus.idx`` is missing, Dark Matter POSTs here with ``force_refresh=False`` to
    generate it (unless ``DARKMATTER_DISABLE_RESOLVED_IDX=1``). Set
    ``DARKMATTER_ALLOW_RESOLVED_IDX_API_ON_LAUNCH=1`` only to force regeneration when a file already exists.
    """
    # Docker Compose uses sclib_fastapi; local `bokeh serve` has no that DNS name — default to loopback.
    _default_api = (
        "http://sclib_fastapi:5001"
        if globals().get("has_args")
        else "http://127.0.0.1:5001"
    )
    dataset_api_base = (
        os.getenv("SCLIB_DATASET_URL")
        or os.getenv("SCLIB_API_URL")
        or os.getenv("SCLIB_FASTAPI_URL")
        or _default_api
    ).rstrip("/")
    endpoint = f"{dataset_api_base}/api/v1/datasets/s3/openvisus-resolved-idx"

    override = auth_override or {}
    payload = {
        "dataset_identifier": dataset_identifier,
        "s3_uri": None,
        "user_email": _valid_email_or_none(user_email),
        "access_key_id": override.get("aws_access_key_id") or None,
        "secret_access_key": override.get("aws_secret_access_key") or None,
        "endpoint_url": override.get("endpoint_url") or None,
        "region_name": override.get("region_name") or region_name,
        "path_style": True,
        "cache_credentials": True,
        "use_cached_credentials": True,
        "output_filename": output_filename,
        "filename_template_mode": filename_template_mode,
        "force_refresh": bool(force_refresh),
        "background": False,
    }

    try:
        timeout_s = max(60, int(os.getenv("DARKMATTER_RESOLVED_IDX_HTTP_TIMEOUT", "600")))
    except ValueError:
        timeout_s = 600
    resp = requests.post(endpoint, json=payload, timeout=timeout_s)
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        raise RuntimeError(detail or f"HTTP {resp.status_code}")

    data = resp.json() or {}
    resolved_idx_path = str(data.get("resolved_idx_path") or "").strip()
    if not data.get("success") or not resolved_idx_path:
        raise RuntimeError(data.get("detail") or "Resolved idx endpoint returned no path")

    return resolved_idx_path, data.get("resolved_idx_http_url")


def derive_dataset_from_remote_uri(remote_uri: str, auth_override: Optional[dict] = None):
    """
    Resolve http(s):// or s3:// dataset from either a direct ``*.idx`` URL or a prefix
    (directory) URL: the latter lists keys under the prefix and picks a ``*.idx``.
    """
    ds = parse_remote_dataset_uri(remote_uri)
    if ds is not None:
        return ds
    try:
        return discover_remote_dataset_from_prefix(remote_uri, auth_override)
    except Exception as ex:
        print(f"[DarkMatter][WARN] remote dataset prefix discovery failed: {ex}")
        return None


def _darkmatter_sidecar_paths(idx_path: str, mid_file: str) -> Tuple[str, str]:
    """
    Locate ``{mid}.txt`` / ``{mid}.csv`` near an idx.

    Download/cache layouts often put the idx under ``.dm_openvisus_cache/`` (or a nested
    folder) while sidecars stay in ``upload/<uuid>/``. Proxy ``visus.idx`` under converted/
    also has no ``visus.txt`` — look for a real stem's sidecars in the uuid root.
    """
    idx_path = os.path.abspath(str(idx_path or "").strip())
    mid_file = str(mid_file or "").strip()
    idx_dir = os.path.dirname(idx_path)
    search_roots: List[str] = []
    for root in (idx_dir, os.path.dirname(idx_dir), os.path.dirname(os.path.dirname(idx_dir))):
        root = os.path.abspath(root) if root else ""
        if root and root not in search_roots and os.path.isdir(root):
            search_roots.append(root)

    if mid_file and mid_file.lower() != "visus":
        for root in search_roots:
            txt = os.path.join(root, f"{mid_file}.txt")
            csv = os.path.join(root, f"{mid_file}.csv")
            if os.path.isfile(txt) and os.path.isfile(csv):
                return txt, csv

    # visus.idx / mismatched stem: any matching *.txt+*.csv pair under search roots.
    for root in search_roots:
        try:
            names = os.listdir(root)
        except OSError:
            continue
        stems = {
            os.path.splitext(n)[0]
            for n in names
            if n.lower().endswith(".txt") and os.path.isfile(os.path.join(root, n))
        }
        for stem in sorted(stems):
            if not stem or stem.lower() == "visus":
                continue
            txt = os.path.join(root, f"{stem}.txt")
            csv = os.path.join(root, f"{stem}.csv")
            if os.path.isfile(txt) and os.path.isfile(csv):
                return txt, csv

    txt_fallback = os.path.join(idx_dir, f"{mid_file}.txt") if mid_file else ""
    csv_fallback = os.path.join(idx_dir, f"{mid_file}.csv") if mid_file else ""
    return txt_fallback, csv_fallback


def _darkmatter_idx_is_proxy_stub(idx_path: str) -> bool:
    """True for converted/<uuid>/visus.idx object-proxy stubs (not a downloaded native package)."""
    p = os.path.abspath(str(idx_path or "")).replace("\\", "/")
    base = os.path.basename(p).lower()
    return base == "visus.idx" and "/converted/" in p


def _upload_has_native_darkmatter_idx(dataset_uuid: str) -> bool:
    """True when upload/<uuid> already has a real .idx — do not write converted/visus.idx."""
    uuid_str = str(dataset_uuid or "").strip()
    if not uuid_str:
        return False
    upload_root = os.path.join(
        str(os.getenv("JOB_IN_DATA_DIR") or "/mnt/visus_datasets/upload").rstrip("/"),
        uuid_str,
    )
    if not os.path.isdir(upload_root):
        return False
    for current_root, _dirs, files in os.walk(upload_root):
        if os.path.basename(current_root) == ".dm_openvisus_cache":
            continue
        for filename in files:
            if not filename.lower().endswith(".idx"):
                continue
            if filename.lower() == "visus.idx":
                continue
            return True
    return False


def _find_local_darkmatter_package(dataset_uuid: str) -> Optional[dict]:
    """
    Prefer a complete DarkMatter package under upload/<uuid>, then converted/<uuid>.

    Never treat converted/.../visus.idx (object-proxy stub) as the package when upload
    already has a native idx+txt+csv — that stub caused remote fallback + re-write loops.
    """
    uuid_str = str(dataset_uuid or "").strip()
    if not uuid_str:
        return None
    upload_root = os.path.join(
        str(os.getenv("JOB_IN_DATA_DIR") or "/mnt/visus_datasets/upload").rstrip("/"),
        uuid_str,
    )
    converted_root = os.path.join(
        str(os.getenv("JOB_OUT_DATA_DIR") or "/mnt/visus_datasets/converted").rstrip("/"),
        uuid_str,
    )

    def _complete(ds: Optional[dict]) -> bool:
        if not ds:
            return False
        return bool(
            os.path.isfile(str(ds.get("idx_path") or ""))
            and os.path.isfile(str(ds.get("txt_path") or ""))
            and os.path.isfile(str(ds.get("csv_path") or ""))
        )

    def _score_idx(path: str) -> Tuple[int, str]:
        """Prefer native stems in upload over cache/proxy stubs."""
        p = path.replace("\\", "/")
        score = 0
        if "/.dm_openvisus_cache/" in p:
            score += 100
        if os.path.basename(p).lower() == "visus.idx":
            score += 50
        if "/converted/" in p:
            score += 10
        return (score, p)

    for root in (upload_root, converted_root):
        if not os.path.isdir(root):
            continue
        idx_matches: List[str] = []
        for current_root, _dirs, files in os.walk(root):
            for filename in files:
                if filename.lower().endswith(".idx"):
                    idx_matches.append(os.path.join(current_root, filename))
        for idx_path in sorted(idx_matches, key=_score_idx):
            if _darkmatter_idx_is_proxy_stub(idx_path) and _upload_has_native_darkmatter_idx(uuid_str):
                continue
            ds = derive_dataset_from_local_dir(idx_path)
            if _complete(ds):
                if "/converted/" in idx_path.replace("\\", "/"):
                    ds["converted_idx_path"] = ds["idx_path"]
                print(
                    f"[DarkMatter][DEBUG] local DarkMatter package: "
                    f"mode={ds['mode']} mid={ds['mid_file']} idx={ds['idx_path']}"
                )
                return ds
    return None


def derive_dataset_from_uuid(dataset_uuid: str):
    """
    Resolve runtime dataset from Mongo metadata when dashboard receives a UUID.
    This is the standard ScientistCloud served flow for remote-link datasets.
    """
    dataset_uuid = str(dataset_uuid or "").strip()
    if not dataset_uuid or collection is None:
        return None

    try:
        doc = collection.find_one({"uuid": dataset_uuid})
    except Exception as ex:
        print(f"[DarkMatter][WARN] failed to query dataset doc for uuid={dataset_uuid}: {ex}")
        return None

    if not doc:
        print(f"[DarkMatter][WARN] derive_dataset_from_uuid: no Mongo document for uuid={dataset_uuid}")
        return None

    auth_override = {
        "endpoint_url": str(doc.get("s3_endpoint_url") or "").strip() or None,
        "aws_access_key_id": str(doc.get("s3_access_key_id") or "").strip() or None,
        "aws_secret_access_key": str(doc.get("s3_secret_access_key") or "").strip() or None,
        "region_name": str(doc.get("s3_region_name") or "us-east-1").strip() or "us-east-1",
    }
    converted_idx_path = str(doc.get("converted_idx_path") or "").strip()
    has_remote_link = any(
        str(doc.get(field) or "").strip().startswith(("http://", "https://", "s3://"))
        for field in ("google_drive_link", "source_path")
    )

    # Downloaded packages live under upload/<uuid>/ (idx+txt+csv). Prefer those over
    # converted/<uuid>/visus.idx proxy stubs and over google_drive_link.
    local_pkg = _find_local_darkmatter_package(dataset_uuid)
    if local_pkg is not None:
        return local_pkg

    # Mongo converted_idx_path only if it is a complete package (not a lone proxy visus.idx).
    if (
        converted_idx_path
        and os.path.isfile(converted_idx_path)
        and not (
            _darkmatter_idx_is_proxy_stub(converted_idx_path)
            and _upload_has_native_darkmatter_idx(dataset_uuid)
        )
    ):
        ds = derive_dataset_from_local_dir(converted_idx_path)
        if (
            ds
            and os.path.isfile(str(ds.get("txt_path") or ""))
            and os.path.isfile(str(ds.get("csv_path") or ""))
        ):
            ds["converted_idx_path"] = converted_idx_path
            print(
                f"[DarkMatter][DEBUG] resolved runtime_dataset from converted_idx_path: "
                f"mode={ds['mode']} mid={ds['mid_file']}"
            )
            return ds

    # Link-only (or incomplete local): use google_drive_link / source_path.
    for field in ("google_drive_link", "source_path"):
        candidate = str(doc.get(field) or "").strip()
        if not candidate.startswith(("http://", "https://", "s3://")):
            continue
        ds = derive_dataset_from_remote_uri(candidate, auth_override)
        if ds is not None:
            if auth_override.get("aws_access_key_id") and auth_override.get("aws_secret_access_key"):
                ds["auth_override"] = auth_override
            ensure_http_gateway_credentials_on_dataset(ds)
            # Mark so load path skips writing converted/visus.idx when upload already has idx.
            if _upload_has_native_darkmatter_idx(dataset_uuid):
                ds["skip_converted_resolved_idx"] = True
                print(
                    "[DarkMatter][DEBUG] upload already has native .idx; "
                    "will not POST openvisus-resolved-idx into converted/"
                )
            print(
                f"[DarkMatter][DEBUG] resolved runtime_dataset from dataset doc field={field}: "
                f"mode={ds['mode']} mid={ds['mid_file']}"
            )
            return ds
        if not candidate.lower().endswith(".idx"):
            has_creds = bool(
                auth_override.get("aws_access_key_id") and auth_override.get("aws_secret_access_key")
            )
            if not has_creds:
                print(
                    f"[DarkMatter][WARN] dataset doc field {field} is a remote prefix/folder URL but "
                    "s3_access_key_id / s3_secret_access_key are missing — cannot list bucket to find .idx."
                )
            elif candidate.startswith(("http://", "https://")) and not http_object_url_to_s3_uri(candidate):
                print(
                    f"[DarkMatter][WARN] dataset doc field {field} is HTTPS but not path-style "
                    "(https://host/bucket/key) — cannot convert to s3:// for listing."
                )

    if has_remote_link:
        print(
            "[DarkMatter][WARN] derive_dataset_from_uuid: remote link present but could not resolve "
            "http_explicit/s3_explicit dataset"
        )
        return None

    return None


def derive_dataset_from_local_dir(dataset_dir: str):
    path = os.path.abspath(str(dataset_dir or "").strip())
    idx_path = ""
    mid_file = ""
    dataset_root = ""

    # Support both dataset directory and direct .idx file arguments.
    if os.path.isfile(path) and path.lower().endswith(".idx"):
        idx_path = path
        mid_file = os.path.splitext(os.path.basename(path))[0]
        dataset_root = os.path.dirname(path)
    elif os.path.isdir(path):
        dataset_root = path
        mid_file = os.path.basename(path.rstrip("/"))
        idx_path = os.path.join(dataset_root, f"{mid_file}.idx")
        if not os.path.exists(idx_path):
            # Prefer a native stem .idx over proxy visus.idx (converted stub).
            idx_matches: List[str] = []
            for current_root, _dirs, files in os.walk(dataset_root):
                for filename in files:
                    if filename.lower().endswith(".idx"):
                        idx_matches.append(os.path.join(current_root, filename))
            if not idx_matches:
                return None

            def _pick_key(p: str) -> Tuple[int, str]:
                pl = p.replace("\\", "/")
                score = 0
                if "/.dm_openvisus_cache/" in pl:
                    score += 100
                if os.path.basename(pl).lower() == "visus.idx":
                    score += 50
                return (score, pl)

            idx_path = sorted(idx_matches, key=_pick_key)[0]
            mid_file = os.path.splitext(os.path.basename(idx_path))[0]
            dataset_root = os.path.dirname(idx_path)
        else:
            mid_file = os.path.splitext(os.path.basename(idx_path))[0]
    else:
        return None

    txt_path, csv_path = _darkmatter_sidecar_paths(idx_path, mid_file)
    # If sidecars used a different stem than visus.idx, adopt that mid for channels/events.
    if mid_file.lower() == "visus" and txt_path and os.path.isfile(txt_path):
        mid_file = os.path.splitext(os.path.basename(txt_path))[0]

    return {
        "mode": "local_explicit",
        "mid_file": mid_file,
        "idx_path": idx_path,
        "txt_path": txt_path,
        "csv_path": csv_path,
    }


_ARCO_HEX_BIN = re.compile(r"^[0-9a-f]{4}\.bin$", re.IGNORECASE)


def _arco_bin_tile_count(dir_path: str) -> int:
    """How many %04x.bin-style tiles are in dir_path; 0 if 0000.bin is missing."""
    try:
        names = os.listdir(dir_path)
    except OSError:
        return 0
    if "0000.bin" not in names:
        return 0
    return sum(1 for n in names if _ARCO_HEX_BIN.match(n))


def _find_arco_bin_directory_under(segment_root: str) -> Optional[str]:
    """
    Prefer segment_root when it already holds ARCO tiles; otherwise the descendant
    directory with the most matching tiles (handles extra data/0000/... nesting).
    """
    if not os.path.isdir(segment_root):
        return None
    if _arco_bin_tile_count(segment_root) >= 4:
        return segment_root
    best_dir: Optional[str] = None
    best_n = 0
    for root, _dirs, files in os.walk(segment_root):
        if "0000.bin" not in files:
            continue
        n = sum(1 for fn in files if _ARCO_HEX_BIN.match(fn))
        if n > best_n and n >= 4:
            best_n = n
            best_dir = root
    return best_dir


def _idx_line_index_after_section(lines: List[str], section: str) -> Optional[int]:
    for i, line in enumerate(lines):
        if line.strip() == section and i + 1 < len(lines):
            return i + 1
    return None


def _fix_idx_field_compression_zip_to_raw(lines: List[str]) -> List[str]:
    """Replace default_compression(zip) with raw in the (fields) section (first occurrence only)."""
    out: List[str] = []
    i = 0
    replaced = False
    section_hdr = re.compile(r"^\s*\([a-z_ ]+\)\s*$")
    while i < len(lines):
        line = lines[i]
        if line.strip() == "(fields)":
            out.append(line)
            i += 1
            while i < len(lines):
                fl = lines[i]
                if section_hdr.match(fl):
                    break
                if (not replaced) and "default_compression(zip)" in fl:
                    fl = fl.replace("default_compression(zip)", "default_compression(raw)", 1)
                    replaced = True
                out.append(fl)
                i += 1
            continue
        out.append(line)
        i += 1
    return out


def _local_idx_bins_need_raw_compression(idx_path: str) -> bool:
    """
    True when ARCO tiles are stored uncompressed but the idx declares default_compression(zip).
    OpenVisus then zip-decodes, fails, and returns all zeros.
    """
    abs_idx = os.path.abspath(idx_path)
    root = os.path.dirname(abs_idx)
    prev = os.getcwd()
    try:
        os.chdir(root)
        pd = ov.LoadDataset(abs_idx)
        db = pd.db
        access = db.createAccessForBlockQuery()
        field = db.getField()
        t = float(db.getTimesteps().getDefault())
        fn = str(access.getFilename(field, t, 0))
        if not os.path.isfile(fn):
            return False
        raw = ov.LoadBinaryDocument(fn)
        s = db.getBlockQuerySamples(0)
        ns = s.nsamples
        dims = ov.PointNi([int(ns[j]) for j in range(ns.getPointDim())])
        dtype = ov.DType.fromString(field.dtype.toString())
        if ov.Decode("zip", dims, dtype, raw) is not None:
            return False
        return int(raw.c_size()) == int(dtype.getByteSize(dims))
    except Exception:
        return False
    finally:
        try:
            os.chdir(prev)
        except OSError:
            pass


def _expected_time_subdir_for_first_timestep(time_content_line: str, t0: int = 0) -> Optional[str]:
    """
    Parse idx (time) content line like '0 0 %00000d/' -> directory name OpenVisus uses for t0 (no slashes).
    Supports Visus-style '%00000d' (width = number of zeros) and standard '%04d', '%0Nd'.
    """
    m = re.match(r"^\s*\d+\s+\d+\s+(.+?)\s*$", time_content_line.strip())
    if not m:
        return None
    pat = m.group(1).strip()
    if not pat.endswith("/"):
        return None
    core = pat[:-1]
    m_visus = re.fullmatch(r"%(0+)d", core)
    if m_visus:
        width = len(m_visus.group(1))
        return f"{t0:0{width}d}"
    m_std = re.fullmatch(r"%0(\d+)d", core)
    if m_std:
        width = int(m_std.group(1))
        return f"{t0:0{width}d}"
    return None


def resolve_local_idx_path(idx_path: str, mid_file: str) -> str:
    """Return idx_path unchanged — never rewrite (filename_template) or other idx fields."""
    _ = mid_file
    return idx_path


# def download_s3_uri_to_file(s3_uri: str, dst: str):
#     bucket_name, key = parse_s3_uri(s3_uri)
#     if not bucket_name or not key:
#         raise RuntimeError(f"Invalid s3 uri: {s3_uri}")
#     os.makedirs(os.path.dirname(dst), exist_ok=True)
#     bucket = get_aws_bucket()
#     default_bucket_name = getattr(bucket, "name", None)

#     if default_bucket_name and bucket_name == default_bucket_name:
#         bucket.download_file(key, dst)
#         return

#     # Fallback for cross-bucket/object access using the underlying client.
#     bucket.meta.client.download_file(bucket_name, key, dst)


def read_s3_text_lines(s3_uri: str, auth_override=None) -> List[str]:
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key:
        raise RuntimeError(f"Invalid s3 uri: {s3_uri}")

    # Load credentials/config from common project locations for local runs.
    dotenv_candidates = [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(PROJECT_ROOT, "SC_Docker", ".env"),
        os.path.join(PROJECT_ROOT, "SC_Docker", "env.scientistcloud.com"),
        os.path.join(PROJECT_ROOT, "..", "VisusDataPortalPrivate", "Docker", ".env"),
    ]
    load_dotenv()
    for dotenv_path in dotenv_candidates:
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path, override=False)

    endpoint_url = os.getenv("ENDPOINT_URL")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_S3_REGION", "us-east-1")
    if auth_override:
        endpoint_url = auth_override.get("endpoint_url") or endpoint_url
        aws_access_key_id = auth_override.get("aws_access_key_id") or aws_access_key_id
        aws_secret_access_key = auth_override.get("aws_secret_access_key") or aws_secret_access_key
        region_name = auth_override.get("region_name") or region_name

    if not aws_access_key_id or not aws_secret_access_key:
        raise RuntimeError(
            "Missing AWS credentials for S3 read. "
            "Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY in environment or .env."
        )

    endpoint_candidates = []
    for candidate in [
        endpoint_url,
        os.getenv("S3_ENDPOINT_URL"),
        os.getenv("S3_PUBLIC_ENDPOINT_URL"),
        os.getenv("ENDPOINT_URL"),
        None,
    ]:
        if candidate not in endpoint_candidates:
            endpoint_candidates.append(candidate)

    last_error = None
    for candidate_endpoint in endpoint_candidates:
        for addr_style in _s3_addressing_styles_for_endpoint(candidate_endpoint or endpoint_url):
            try:
                config = Config(
                    signature_version="s3v4",
                    s3={"addressing_style": addr_style},
                )
                s3_client = Session().client(
                    "s3",
                    endpoint_url=candidate_endpoint,
                    region_name=region_name,
                    config=config,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
                resp = s3_client.get_object(Bucket=bucket_name, Key=key)
                body = resp["Body"].read().decode("utf-8")
                if candidate_endpoint:
                    print(
                        f"[DarkMatter][DEBUG] sidecar S3 read succeeded with endpoint={candidate_endpoint} "
                        f"addressing_style={addr_style}"
                    )
                else:
                    print(
                        f"[DarkMatter][DEBUG] sidecar S3 read succeeded with default AWS endpoint "
                        f"addressing_style={addr_style}"
                    )
                return body.splitlines()
            except Exception as exc:
                last_error = exc
                continue

    if last_error:
        raise last_error
    raise RuntimeError("Failed to read S3 sidecar text lines")


def _s3_object_exists(s3_uri: str, auth_override=None) -> bool:
    """True if the S3 object exists (HeadObject), using the same endpoint/style probing as reads."""
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key:
        return False
    load_dotenv()
    endpoint_url = os.getenv("ENDPOINT_URL")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_S3_REGION", "us-east-1")
    if auth_override:
        endpoint_url = auth_override.get("endpoint_url") or endpoint_url
        aws_access_key_id = auth_override.get("aws_access_key_id") or aws_access_key_id
        aws_secret_access_key = auth_override.get("aws_secret_access_key") or aws_secret_access_key
        region_name = auth_override.get("region_name") or region_name
    if not aws_access_key_id or not aws_secret_access_key:
        return False
    for candidate_endpoint in [endpoint_url, os.getenv("S3_ENDPOINT_URL"), None]:
        for addr_style in _s3_addressing_styles_for_endpoint(candidate_endpoint or endpoint_url):
            try:
                config = Config(
                    signature_version="s3v4",
                    s3={"addressing_style": addr_style},
                )
                s3_client = Session().client(
                    "s3",
                    endpoint_url=candidate_endpoint,
                    region_name=region_name,
                    config=config,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
                s3_client.head_object(Bucket=bucket_name, Key=key)
                return True
            except Exception:
                continue
    return False


def _zero_arco_block_in_idx_lines(lines: List[str]) -> List[str]:
    """Force (arco) to 0 so OpenVisus uses (filename_template) instead of ARCO disk layout."""
    out: List[str] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = (raw or "").strip()
        if s.lower().startswith("(arco)"):
            # Keep header line; normalize value to 0 on same line or following value line.
            same = s[len("(arco)") :].strip()
            nl = "\n" if raw.endswith("\n") else ""
            if same:
                out.append(f"(arco) 0{nl}" if not raw.endswith("\n") else "(arco) 0\n")
                i += 1
                continue
            out.append(raw if raw.endswith("\n") else raw + "\n")
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if (nxt or "").strip() == "":
                    out.append(nxt if nxt.endswith("\n") else nxt + "\n")
                    i += 1
                    continue
                out.append("0\n")
                i += 1
                break
            continue
        out.append(raw if raw.endswith("\n") else raw + "\n")
        i += 1
    return out


def materialize_remote_idx_for_openvisus(
    runtime_dataset: dict,
    *,
    template_kind: str = "https",
) -> Optional[str]:
    """Disabled: never rewrite (filename_template) or materialize a local idx stub."""
    _ = (runtime_dataset, template_kind)
    return None



def _s3_client_candidates(auth_override=None):
    """Yield (endpoint, addressing_style, s3_client) combinations for custom gateways."""
    load_dotenv()
    endpoint_url = os.getenv("ENDPOINT_URL")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_S3_REGION", "us-east-1")
    if auth_override:
        endpoint_url = auth_override.get("endpoint_url") or endpoint_url
        aws_access_key_id = auth_override.get("aws_access_key_id") or aws_access_key_id
        aws_secret_access_key = auth_override.get("aws_secret_access_key") or aws_secret_access_key
        region_name = auth_override.get("region_name") or region_name
    if not aws_access_key_id or not aws_secret_access_key:
        return
    # Path-style only on custom gateways — virtual host is bucket.endpoint and breaks TLS.
    styles = _s3_addressing_styles_for_endpoint(endpoint_url or "")
    for candidate_endpoint in [endpoint_url, os.getenv("S3_ENDPOINT_URL"), None]:
        for addr_style in styles:
            try:
                config = Config(
                    signature_version="s3v4",
                    s3={"addressing_style": addr_style},
                )
                s3_client = Session().client(
                    "s3",
                    endpoint_url=candidate_endpoint,
                    region_name=region_name,
                    config=config,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
                yield candidate_endpoint, addr_style, s3_client
            except Exception:
                continue


def _list_s3_hex_bin_keys(
    bucket: str,
    key_prefix: str,
    auth_override=None,
    max_items: int = 4096,
) -> List[str]:
    """List ``NNN.bin`` / ``%04x.bin``-style object keys under prefix (basename is 4 hex digits)."""
    prefix = str(key_prefix or "")
    hex_bin = re.compile(r"^[0-9a-fA-F]{4}\.bin$")
    last_error = None
    for _ep, _style, s3_client in _s3_client_candidates(auth_override):
        try:
            keys: List[str] = []
            token = None
            while True:
                kwargs: dict = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
                if token:
                    kwargs["ContinuationToken"] = token
                resp = s3_client.list_objects_v2(**kwargs)
                for obj in resp.get("Contents") or []:
                    k = str(obj.get("Key") or "")
                    if hex_bin.match(os.path.basename(k)):
                        keys.append(k)
                        if len(keys) > max_items:
                            return keys
                if not resp.get("IsTruncated"):
                    break
                token = resp.get("NextContinuationToken")
            return keys
        except Exception as ex:
            last_error = ex
            continue
    if last_error:
        print(f"[DarkMatter][WARN] _list_s3_hex_bin_keys failed: {last_error}")
    return []


def _download_s3_object_to_file(s3_uri: str, dest_path: str, auth_override=None) -> None:
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key:
        raise ValueError(f"Invalid s3 uri: {s3_uri}")
    last_error = None
    for _ep, _style, s3_client in _s3_client_candidates(auth_override):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
            s3_client.download_file(bucket_name, key, dest_path)
            return
        except Exception as ex:
            last_error = ex
            continue
    raise RuntimeError(f"Failed to download {s3_uri}: {last_error}")

def read_text_lines_from_url(url: str) -> List[str]:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text.splitlines()


# Nexus-style acquisition folder names often appear in S3 paths while the .idx link uses a
# generic name (e.g. .../07180827_0000_F0001/arco/arco.idx with sidecars 07180827_0000_F0001.txt).
_ACQUISITION_STEM_RE = re.compile(r"^\d{8}_\d{4}_F\d+$")


def sidecar_stem_hints_from_idx_uri(idx_uri: str) -> List[str]:
    """Path segments that look like acquisition IDs — likely real .txt/.csv stems."""
    path = urlsplit(str(idx_uri or "").strip()).path or ""
    parts = [p for p in path.split("/") if p]
    out: List[str] = []
    for p in parts:
        if _ACQUISITION_STEM_RE.match(p) and p not in out:
            out.append(p)
    return out


def sidecar_http_urls_for_basename(txt_uri: str, csv_uri: str, base: str) -> tuple:
    """Same query string as the originals; only the filename stem before .txt/.csv changes."""
    base = str(base or "").strip()
    if not base:
        return "", ""
    t = urlsplit(str(txt_uri or "").strip())
    c = urlsplit(str(csv_uri or "").strip())
    dir_t = (t.path or "").rsplit("/", 1)[0]
    dir_c = (c.path or "").rsplit("/", 1)[0]
    if not dir_t or not dir_c:
        return "", ""
    new_t = f"{dir_t}/{base}.txt"
    new_c = f"{dir_c}/{base}.csv"
    return (
        urlunsplit((t.scheme, t.netloc, new_t, t.query, t.fragment)),
        urlunsplit((c.scheme, c.netloc, new_c, c.query, c.fragment)),
    )


def try_read_darkmatter_sidecars_from_disk(
    mid_file: str,
    runtime_dataset: dict,
    save_dir: Optional[str],
    uuid_str: str,
) -> Optional[tuple]:
    """
    If .txt and .csv exist next to a materialized idx (converted/ or upload/), use them.
    Tries <mid>.{txt,csv} then visus.{txt,csv} so IDX packages that use visus.* still work
    when the linked URL basename is different (e.g. arco.idx).
    """
    roots: List[str] = []
    sd = (save_dir or "").strip()
    if sd and os.path.isdir(sd):
        roots.append(os.path.abspath(sd))
    cip = str((runtime_dataset or {}).get("converted_idx_path") or "").strip()
    if cip and os.path.isfile(cip):
        roots.append(os.path.dirname(os.path.abspath(cip)))
    if resolve_local_idx_file and uuid_str:
        try:
            rl = resolve_local_idx_file(str(uuid_str).strip())
            rl = str(rl or "").strip()
            if rl and os.path.isfile(rl):
                roots.append(os.path.dirname(os.path.abspath(rl)))
        except Exception:
            pass
    seen = set()
    ordered_roots: List[str] = []
    for r in roots:
        if r and r not in seen:
            seen.add(r)
            ordered_roots.append(r)
    bases: List[str] = []
    mf = str(mid_file or "").strip()
    idx_uri = str((runtime_dataset or {}).get("idx_uri") or "").strip()
    for hint in sidecar_stem_hints_from_idx_uri(idx_uri):
        if hint not in bases:
            bases.append(hint)
    if mf and mf not in bases:
        bases.append(mf)
    if not any(b.lower() == "visus" for b in bases):
        bases.append("visus")
    for root in ordered_roots:
        for base in bases:
            tp = os.path.join(root, f"{base}.txt")
            cp = os.path.join(root, f"{base}.csv")
            if os.path.isfile(tp) and os.path.isfile(cp):
                with open(tp, "r", encoding="utf-8", errors="replace") as tf:
                    txt_lines = tf.read().splitlines()
                with open(cp, "r", encoding="utf-8", errors="replace") as cf:
                    csv_lines = cf.read().splitlines()
                print(f"[DarkMatter][DEBUG] sidecar metadata read from disk: {tp} + {cp}")
                return txt_lines, csv_lines
    return None


def load_http_explicit_sidecar_lines(
    txt_uri: str,
    csv_uri: str,
    auth_override: Optional[dict],
) -> tuple:
    """
    Match prior behavior: prefer S3 API when credentials + s3:// mapping exist,
    else HTTP GET, with the original no-auth branch ordering preserved.
    """
    txt_s3_uri = http_object_url_to_s3_uri(txt_uri)
    csv_s3_uri = http_object_url_to_s3_uri(csv_uri)
    has_keys = bool((auth_override or {}).get("aws_access_key_id") and (auth_override or {}).get("aws_secret_access_key"))
    if has_keys and txt_s3_uri and csv_s3_uri:
        try:
            tl = read_s3_text_lines(txt_s3_uri, auth_override=auth_override)
            cl = read_s3_text_lines(csv_s3_uri, auth_override=auth_override)
            print("[DarkMatter][DEBUG] sidecar metadata read via S3 API (skipped gateway HTTP)")
            return tl, cl
        except Exception as s3_sidecar_exc:
            try:
                tl = read_text_lines_from_url(txt_uri)
                cl = read_text_lines_from_url(csv_uri)
                return tl, cl
            except Exception as http_sidecar_exc:
                raise RuntimeError(
                    f"S3 sidecar read failed ({s3_sidecar_exc}); HTTP read failed ({http_sidecar_exc})"
                ) from http_sidecar_exc
    try:
        return read_text_lines_from_url(txt_uri), read_text_lines_from_url(csv_uri)
    except Exception as http_sidecar_exc:
        if not txt_s3_uri or not csv_s3_uri:
            raise RuntimeError(
                "DarkMatter requires .txt/.csv metadata files, and HTTP sidecar URLs "
                "could not be converted to s3:// URIs for fallback reads."
            ) from http_sidecar_exc
        tl = read_s3_text_lines(txt_s3_uri, auth_override=auth_override)
        cl = read_s3_text_lines(csv_s3_uri, auth_override=auth_override)
        print("[DarkMatter][DEBUG] sidecar metadata read via S3 API after HTTP failure")
        return tl, cl


def http_object_url_to_s3_uri(url: str) -> str:
    """
    Convert path-style HTTP object URL to s3://bucket/key when possible.
    Example: https://host/bucket/prefix/file.idx -> s3://bucket/prefix/file.idx
    """
    parts = urlsplit(str(url or "").strip())
    if parts.scheme not in ("http", "https"):
        return ""
    path_parts = [segment for segment in (parts.path or "").split("/") if segment]
    if len(path_parts) < 2:
        return ""
    bucket_name = path_parts[0]
    key = "/".join(path_parts[1:])
    return f"s3://{bucket_name}/{key}"


def _merge_auth_from_https_gateway_uri(uri: str, auth_override: Optional[dict]) -> dict:
    """Merge Mongo/env S3 auth with credentials embedded in an HTTPS gateway URL query."""
    merged = dict(auth_override or {})
    u = str(uri or "").strip()
    if not u.startswith(("http://", "https://")):
        return merged
    parts = urlsplit(u)
    q = parse_qs(parts.query or "")
    ak = (q.get("access_key") or [""])[0].strip()
    sk = (q.get("secret_key") or [""])[0].strip()
    if ak and not str(merged.get("aws_access_key_id") or "").strip():
        merged["aws_access_key_id"] = ak
    if sk and not str(merged.get("aws_secret_access_key") or "").strip():
        merged["aws_secret_access_key"] = sk
    gw = f"{parts.scheme}://{parts.netloc}" if (parts.scheme and parts.netloc) else ""
    if gw and not str(merged.get("endpoint_url") or "").strip():
        merged["endpoint_url"] = gw
    return merged


def _pick_idx_key_under_prefix(keys: List[str], prefix: str) -> Optional[str]:
    """Prefer the shallowest *.idx key under prefix; tie-break by shortest key then name."""
    idx_keys = [k for k in keys if k.lower().endswith(".idx")]
    if not idx_keys:
        return None
    if len(idx_keys) == 1:
        return idx_keys[0]
    pref = prefix.rstrip("/") + "/" if prefix else ""

    def depth(k: str) -> int:
        if pref and k.startswith(pref):
            rel = k[len(pref) :]
        else:
            rel = k
        return rel.count("/")

    idx_keys.sort(key=lambda k: (depth(k), len(k), k))
    return idx_keys[0]


def _list_s3_idx_keys_at_prefix(
    bucket: str,
    prefix: str,
    auth_override: dict,
    max_items: int = 500,
) -> List[str]:
    """List object keys under prefix that end with .idx (path-style gateway compatible)."""
    dotenv_candidates = [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(PROJECT_ROOT, "SC_Docker", ".env"),
        os.path.join(PROJECT_ROOT, "SC_Docker", "env.scientistcloud.com"),
        os.path.join(PROJECT_ROOT, "..", "VisusDataPortalPrivate", "Docker", ".env"),
    ]
    load_dotenv()
    for dotenv_path in dotenv_candidates:
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path, override=False)

    endpoint_url = os.getenv("ENDPOINT_URL")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_S3_REGION", "us-east-1")
    if auth_override:
        endpoint_url = auth_override.get("endpoint_url") or endpoint_url
        aws_access_key_id = auth_override.get("aws_access_key_id") or aws_access_key_id
        aws_secret_access_key = auth_override.get("aws_secret_access_key") or aws_secret_access_key
        region_name = auth_override.get("region_name") or region_name

    if not aws_access_key_id or not aws_secret_access_key:
        return []

    endpoint_candidates: List[Optional[str]] = []
    for candidate in [
        endpoint_url,
        os.getenv("S3_ENDPOINT_URL"),
        os.getenv("S3_PUBLIC_ENDPOINT_URL"),
        os.getenv("ENDPOINT_URL"),
        None,
    ]:
        if candidate not in endpoint_candidates:
            endpoint_candidates.append(candidate)

    last_error: Optional[Exception] = None
    for candidate_endpoint in endpoint_candidates:
        for addr_style in _s3_addressing_styles_for_endpoint(candidate_endpoint or endpoint_url):
            try:
                config = Config(
                    signature_version="s3v4",
                    s3={"addressing_style": addr_style},
                )
                s3_client = Session().client(
                    "s3",
                    endpoint_url=candidate_endpoint,
                    region_name=region_name,
                    config=config,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
                paginator = s3_client.get_paginator("list_objects_v2")
                batch: List[str] = []
                for page in paginator.paginate(
                    Bucket=bucket,
                    Prefix=prefix,
                    PaginationConfig={"PageSize": 200, "MaxItems": max_items},
                ):
                    for obj in page.get("Contents", []) or []:
                        k = obj.get("Key")
                        if k and k.lower().endswith(".idx"):
                            batch.append(str(k))
                    if len(batch) >= max_items:
                        break
                if batch:
                    if candidate_endpoint:
                        print(
                            f"[DarkMatter][DEBUG] S3 list under prefix={prefix!r} found {len(batch)} "
                            f".idx key(s) (endpoint={candidate_endpoint} addressing_style={addr_style})"
                        )
                    else:
                        print(
                            f"[DarkMatter][DEBUG] S3 list under prefix={prefix!r} found {len(batch)} "
                            f".idx key(s) (default endpoint addressing_style={addr_style})"
                        )
                    return batch
            except Exception as exc:
                last_error = exc
                continue
    if last_error:
        print(f"[DarkMatter][WARN] S3 list_objects under {prefix!r} failed: {last_error}")
    return []


def discover_remote_dataset_from_prefix(
    remote_uri: str,
    auth_override: Optional[dict] = None,
) -> Optional[dict]:
    """
    When remote_uri is a bucket prefix (HTTPS path-style or s3://) without a trailing .idx
    file, list keys under that prefix and build http_explicit / s3_explicit dataset dict
    from the chosen *.idx (shallowest under the prefix).
    """
    uri = str(remote_uri or "").strip()
    if not uri:
        return None

    merged = _merge_auth_from_https_gateway_uri(uri, auth_override)
    bucket = ""
    key_prefix = ""

    if uri.lower().startswith("s3://"):
        bucket, key_prefix = parse_s3_uri(uri)
    elif uri.startswith(("http://", "https://")):
        s3_equiv = http_object_url_to_s3_uri(uri)
        if not s3_equiv:
            print(
                "[DarkMatter][WARN] discover_remote_dataset_from_prefix: HTTPS URL is not path-style "
                f"(expected https://host/bucket/prefix/...); cannot map to s3:// for listing. uri={_redact_url_secrets(uri)}"
            )
            return None
        bucket, key_prefix = parse_s3_uri(s3_equiv)
    else:
        return None

    if not bucket:
        return None
    pk = (key_prefix or "").strip()
    if pk.lower().endswith(".idx"):
        return None

    prefix = pk.rstrip("/") + "/" if pk else ""
    if not merged.get("aws_access_key_id") or not merged.get("aws_secret_access_key"):
        print(
            "[DarkMatter][WARN] discover_remote_dataset_from_prefix: missing S3 credentials "
            "(need s3_access_key_id + s3_secret_access_key on dataset document, or access_key/secret_key "
            f"in HTTPS URL query) to list prefix under bucket={bucket!r}. uri={_redact_url_secrets(uri)}"
        )
        return None

    keys = _list_s3_idx_keys_at_prefix(bucket, prefix, merged)
    picked = _pick_idx_key_under_prefix(keys, prefix)
    if not picked:
        print(
            "[DarkMatter][WARN] discover_remote_dataset_from_prefix: no *.idx keys found under "
            f"prefix={prefix!r} in bucket={bucket!r} (listed up to cap). uri={_redact_url_secrets(uri)}"
        )
        return None

    if uri.lower().startswith("s3://"):
        out = parse_remote_dataset_uri(f"s3://{bucket}/{picked}")
        if out:
            print(
                f"[DarkMatter][DEBUG] discovered idx under prefix s3://{bucket}/{prefix!r} -> "
                f"s3://{bucket}/{picked}"
            )
        return out

    parts = urlsplit(uri)
    path = f"/{bucket}/{picked}"
    idx_uri = urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    base_path = path[:-4]
    txt_uri = urlunsplit((parts.scheme, parts.netloc, f"{base_path}.txt", parts.query, parts.fragment))
    csv_uri = urlunsplit((parts.scheme, parts.netloc, f"{base_path}.csv", parts.query, parts.fragment))
    mid_file = os.path.splitext(os.path.basename(picked))[0]
    print(
        f"[DarkMatter][DEBUG] discovered idx under prefix {prefix!r} -> "
        f"{_redact_url_secrets(idx_uri)}"
    )
    return {
        "mode": "http_explicit",
        "mid_file": mid_file,
        "idx_uri": idx_uri,
        "txt_uri": txt_uri,
        "csv_uri": csv_uri,
    }


def with_query_params(url: str, params: dict) -> str:
    parts = urlsplit(str(url or "").strip())
    existing = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in (params or {}).items():
        if value is None:
            continue
        value_str = str(value).strip()
        if value_str:
            existing[key] = value_str
    query = urlencode(existing, doseq=False)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def _http_gateway_query_credentials_need_merge(uri: str) -> bool:
    """True if HTTPS gateway URLs lack real access_key/secret_key (missing, redacted, or empty)."""
    u = str(uri or "").strip()
    if not u.startswith("http://") and not u.startswith("https://"):
        return False
    qs = parse_qs(urlsplit(u).query or "", keep_blank_values=True)
    ak = (qs.get("access_key") or [""])[0].strip()
    sk = (qs.get("secret_key") or [""])[0].strip()
    if not ak or not sk:
        return True
    if ak == "..." or sk == "...":
        return True
    return False


def ensure_http_gateway_credentials_on_dataset(ds: Optional[dict]) -> bool:
    """
    For http_explicit datasets loaded from Mongo: OpenVisus and sidecar HTTP reads need
    gateway query credentials on idx/txt/csv URLs. If google_drive_link was redacted in DB
    or stored without query params while s3_access_key_id / s3_secret_access_key exist on
    the document, merge those keys into the three URIs. No-op for CLI `bokeh serve --args https://...`
    when URLs already carry real credentials.
    Returns True if any URI was updated.
    """
    if not ds or ds.get("mode") != "http_explicit":
        return False
    override = ds.get("auth_override") or {}
    ak = str(override.get("aws_access_key_id") or "").strip()
    sk = str(override.get("aws_secret_access_key") or "").strip()
    if not ak or not sk:
        return False
    region = str(override.get("region_name") or "us-east-1").strip() or "us-east-1"
    changed = False
    for uri_key in ("idx_uri", "txt_uri", "csv_uri"):
        u = str(ds.get(uri_key) or "").strip()
        if not u.startswith("http://") and not u.startswith("https://"):
            continue
        if not _http_gateway_query_credentials_need_merge(u):
            continue
        parts = urlsplit(u)
        base = urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))
        ds[uri_key] = with_query_params(
            base,
            {"access_key": ak, "secret_key": sk, "region_name": region},
        )
        changed = True
    if changed:
        print(
            "[DarkMatter][DEBUG] merged dataset-document S3 keys into HTTPS gateway URLs "
            "(idx/txt/csv had missing or redacted query credentials)"
        )
    return changed


def get_s3_http_gateway_base() -> str:
    # Prefer public gateway for object URLs; fall back to configured S3 endpoint.
    endpoint = (
        os.getenv("S3_PUBLIC_ENDPOINT_URL")
        or os.getenv("S3_ENDPOINT_URL")
        or os.getenv("ENDPOINT_URL")
        or ""
    ).strip()
    if not endpoint:
        return ""
    if endpoint.endswith("/"):
        endpoint = endpoint[:-1]
    return endpoint


def s3_uri_to_http_url(s3_uri: str, endpoint_base: str) -> str:
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key or not endpoint_base:
        return ""
    # Path-style URL expected by current object gateway deployment.
    return f"{endpoint_base}/{bucket_name}/{key}"


# def materialize_idx_for_s3(idx_uri: str, mid_file: str) -> str:
#     """
#     OpenVisus local builds may fail to open s3://...idx directly.
#     Workaround: fetch idx metadata text from S3, write local idx, and force
#     filename_template to point at S3 bin objects.
#     """
#     lines = read_s3_text_lines(idx_uri)
#     fixed_lines = [f"{line}\n" for line in lines]

#     template_idx = -1
#     for i, line in enumerate(lines):
#         if line.strip() == "(filename_template)" and i + 1 < len(lines):
#             template_idx = i + 1
#             break

#     # Prefer HTTP(S) gateway templates for OpenVisus data blocks when available.
#     # Keep s3:// candidates as fallback.
#     base_uri = idx_uri[:-4] if idx_uri.endswith(".idx") else idx_uri
#     parent_uri = base_uri.rsplit("/", 1)[0] if "/" in base_uri else base_uri
#     s3_candidates = [f"{base_uri}/%04x.bin", f"{parent_uri}/%04x.bin"]
#     candidate_templates = []
#     gateway_base = get_s3_http_gateway_base()
#     if gateway_base:
#         for tmpl in s3_candidates:
#             as_http = s3_uri_to_http_url(tmpl, gateway_base)
#             if as_http:
#                 candidate_templates.append(as_http)
#     candidate_templates.extend(s3_candidates)

#     s3_bin_template = candidate_templates[0]
#     for tmpl in candidate_templates:
#         probe_uri = tmpl.replace("%04x", "0000")
#         exists = http_url_exists(probe_uri) if probe_uri.startswith("http") else s3_key_exists(probe_uri)
#         if exists:
#             s3_bin_template = tmpl
#             break
#     if template_idx != -1:
#         fixed_lines[template_idx] = f"{s3_bin_template}\n"
#     else:
#         fixed_lines.extend(["(filename_template)\n", f"{s3_bin_template}\n"])

#     os.makedirs(FILES_VOLUME, exist_ok=True)
#     local_idx_path = os.path.join(FILES_VOLUME, f"{mid_file}.s3.resolved.idx")
#     with open(local_idx_path, "w") as f:
#         f.writelines(fixed_lines)
#     return local_idx_path


# def download_processed_files(midfile: str):
#     """
#     Download processed files from storage (idx, channel metadata, event metadata)
#     -----------------------------------------------------------------------------
#     Parameters
#     ----------
#     file(str): the mid file to download in the the format 07180808_1558_F0001
#     """
#     s3 = get_aws_bucket()

#     filenames = [f"{midfile}.idx", f"0000.bin",
#                  f"{midfile}.txt", f"{midfile}.csv"]
#     download_files = [
#         os.path.join(PREFIX, midfile, filenames[0]),
#         os.path.join(PREFIX, midfile, filenames[1]),
#         os.path.join(PREFIX, midfile, filenames[2]),
#         os.path.join(PREFIX, midfile, filenames[3]),
#     ]

#     for i, file in enumerate(download_files):
#         dst = os.path.join(FILES_VOLUME, midfile, filenames[i])
#         if filenames[i].split(".")[1] == "bin":
#             dst = os.path.join(FILES_VOLUME, midfile, midfile, filenames[i])

#         if not os.path.exists(dst):
#             if check_if_key_exists(file, True):
#                 os.makedirs(os.path.dirname(dst), exist_ok=True)
#                 s3.download_file(file, dst)
#             else:
#                 raise FileNotFoundError(f"{midfile} not in storage")


class AppState:
    def __init__(self, url, runtime_dataset=None):
        self.palettes = {color: generate_palette(color) for color in COLORS}
        self.gradient_idx = 0
        self.mid_files = []
        self.scene_data: np.ndarray = np.array([])
        self.event_idx = 0
        self.events = []
        self.detectors = []
        self.detectors_map = {}
        self.channels_data = []
        self.channel_to_renderer = defaultdict(GlyphRenderer)
        self.figure_title = ""
        self.detector_to_channels = defaultdict(List)
        self.event_to_metadata = defaultdict(EventMetadata)
        self.event_metadata: EventMetadata
        self.runtime_dataset = runtime_dataset
        self.s3_auth_override = None
        # Preload dataset-scoped S3 credentials from Mongo when available.
        if self.runtime_dataset and isinstance(self.runtime_dataset, dict):
            override = self.runtime_dataset.get("auth_override") or {}
            if override.get("aws_access_key_id") and override.get("aws_secret_access_key"):
                self.set_s3_auth_override(
                    override.get("endpoint_url") or "",
                    override.get("aws_access_key_id") or "",
                    override.get("aws_secret_access_key") or "",
                )
                if override.get("region_name"):
                    os.environ["AWS_DEFAULT_REGION"] = str(override.get("region_name"))
                print("[DarkMatter][DEBUG] loaded S3 auth override from dataset document")
        # widgets
        self.fig = self.new_fig("")
        self.load_mid_files(url)

        self.prev_event_button = Button(label="<", button_type="primary", width=48)
        self.next_event_button = Button(label=">", button_type="primary", width=48)
        self.first_event_button = Button(label="<<", button_type="success", width=56)
        self.last_event_button = Button(label=">>", button_type="success", width=56)
        self.event_metadata_widget = Div(text="<b>Event Information</b>")
        self.loading_dataset_spinner = Div(
            text="",
            visible=False,
            width=400,
            sizing_mode="stretch_width",
        )
        # Full-width banner above the plot — stays visible for the whole OpenVisus load (often 1+ min).
        self.loading_progress_banner = Div(
            text="",
            visible=False,
            sizing_mode="stretch_width",
            height=88,
            styles={"margin": "0 0 8px 0"},
        )
        self._loading_started_at = None
        self._loading_tick_cb = None
        self._loading_label = "Dark Matter dataset"
        # Hidden signal for portal postMessage (Bokeh Div HTML does not reliably run <script>).
        self._loading_portal_signal = TextInput(value="0", visible=False, width=1, height=1)
        self._loading_portal_signal.js_on_change(
            "value",
            CustomJS(
                code="""
                try {
                  const raw = (cb_obj.value || "");
                  const parts = raw.split("\\x1e");
                  const loading = parts[0] === "1";
                  const label = parts[1] || "Dark Matter dataset";
                  if (window.parent && window.parent !== window) {
                    window.parent.postMessage({
                      source: "scientistcloud-darkmatter",
                      type: "darkmatter-loading",
                      loading: loading,
                      label: label
                    }, "*");
                  }
                } catch (e) {}
                """
            ),
        )
        self.app_info_text = Div(text="", sizing_mode="stretch_width")
        self.notification_div = Div(text="", visible=False, width=420, sizing_mode="stretch_width")

    def has_scene_data(self) -> bool:
        return isinstance(self.scene_data, np.ndarray) and self.scene_data.size > 0

    def set_s3_auth_override(self, endpoint_url: str, access_key: str, secret_key: str):
        endpoint = str(endpoint_url or "").strip()
        access = str(access_key or "").strip()
        secret = str(secret_key or "").strip()
        region = os.getenv("AWS_S3_REGION", "us-east-1")
        self.s3_auth_override = {
            "endpoint_url": endpoint if endpoint else None,
            "aws_access_key_id": access if access else None,
            "aws_secret_access_key": secret if secret else None,
            "region_name": region,
        }
        # Make runtime credentials available to OpenVisus (native S3 path).
        if access:
            os.environ["AWS_ACCESS_KEY_ID"] = access
        if secret:
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret
        if endpoint:
            os.environ["ENDPOINT_URL"] = endpoint
            os.environ["S3_ENDPOINT_URL"] = endpoint
            # OpenVisus / AWS SDK for C++ and boto3/botocore read this name; ENDPOINT_URL alone
            # often leaves native s3:// LoadDataset with "empty content" on custom gateways.
            os.environ["AWS_ENDPOINT_URL"] = endpoint
            # Path-style matches Inspect S3 / MinIO-style gateways (bucket in URL path, not subdomain).
            if "amazonaws.com" not in endpoint.lower():
                os.environ["AWS_USE_PATH_STYLE_ENDPOINT"] = "true"
        if region:
            os.environ["AWS_DEFAULT_REGION"] = region

    def reset_gradient_idx(self):
        self.gradient_idx = 0

    def update_event_idx(self, idx):
        self.event_idx = idx

    def new_fig(self, mid_file):
        fig = figure(
            title=mid_file,
            x_axis_label="Time (20ns intervals)",
            y_axis_label="Amplitude (ADC Channels)",
            tools=[
                PanTool(),
                BoxZoomTool(),
                WheelZoomTool(),
                SaveTool(),
                ResetTool(),
                HoverTool(
                    tooltips=[("x", "@x"), ("y", "@y"), ("Channel", "$name")],
                ),
            ],
            sizing_mode="stretch_both",
        )

        fig.title.text_font_size = '22pt'
        fig.xaxis.axis_label_text_font_size = "22pt"
        fig.yaxis.axis_label_text_font_size = "22pt"
        fig.xaxis.major_label_text_font_size = '22px'
        fig.yaxis.major_label_text_font_size = '22px'

        fig.toolbar.active_scroll = fig.select_one(WheelZoomTool)
        return fig

    def load_mid_files(self, remote_url):
        if self.runtime_dataset:
            self.mid_files = [self.runtime_dataset["mid_file"]]
            return
        self.mid_files = get_mid_files(remote_url)

    def load_scene_data(self, mid_file):
        if self.runtime_dataset:
            if mid_file != self.runtime_dataset["mid_file"]:
                raise RuntimeError(f"Unknown dataset '{mid_file}'")

            if self.runtime_dataset["mode"] == "local_explicit":
                print(f"[DarkMatter][DEBUG] local_explicit mid={mid_file}")
                print(f"[DarkMatter][DEBUG] idx={self.runtime_dataset['idx_path']}")
                print(f"[DarkMatter][DEBUG] txt={self.runtime_dataset['txt_path']}")
                print(f"[DarkMatter][DEBUG] csv={self.runtime_dataset['csv_path']}")
                idx_for_read = resolve_local_idx_path(self.runtime_dataset["idx_path"], str(mid_file))
                if idx_for_read != self.runtime_dataset["idx_path"]:
                    print(f"[DarkMatter][DEBUG] local_explicit using template-resolved idx: {idx_for_read}")
                _dataset_root = os.path.dirname(os.path.abspath(idx_for_read))
                disk_sidecars = try_read_darkmatter_sidecars_from_disk(
                    mid_file,
                    self.runtime_dataset,
                    _dataset_root,
                    str(getattr(self, "uuid", "") or ""),
                )
                if disk_sidecars is not None:
                    txt_lines, csv_lines = disk_sidecars
                    self.detector_to_channels = create_channel_metadata_map_from_lines(txt_lines)
                    self.event_to_metadata = create_event_metadata_map_from_lines(csv_lines)
                elif os.path.isfile(self.runtime_dataset["txt_path"]) and os.path.isfile(self.runtime_dataset["csv_path"]):
                    self.detector_to_channels = create_channel_metadata_map(
                        self.runtime_dataset["txt_path"]
                    )
                    self.event_to_metadata = create_event_metadata_map(
                        self.runtime_dataset["csv_path"]
                    )
                else:
                    raise RuntimeError(
                        f"Dark Matter requires {mid_file}.txt and {mid_file}.csv next to the .idx in "
                        f"{_dataset_root}. Upload the metadata sidecars with the dataset."
                    )
                print(f"[DarkMatter][DEBUG] LoadDataset input={idx_for_read}")
                # OpenVisus commonly resolves relative filename_template paths (e.g. ./%04x.bin)
                # against the process cwd, not the .idx directory — so `bokeh serve` must not
                # depend on the shell's working directory. Temporarily chdir to the dataset root.
                _prev_cwd = os.getcwd()
                try:
                    os.chdir(_dataset_root)
                    print(f"[DarkMatter][DEBUG] cwd for OpenVisus load={_dataset_root}")
                    self.scene_data = read_openvisus_field(idx_for_read)
                finally:
                    try:
                        os.chdir(_prev_cwd)
                    except OSError:
                        pass
                arr = np.asarray(self.scene_data)
                arr_sample = arr[0, :16].tolist() if arr.ndim == 2 and arr.shape[0] > 0 else []
                nonzero_count = int(np.count_nonzero(arr)) if arr.size else 0
                print(
                    f"[DarkMatter][DEBUG] local scene_data dtype={arr.dtype} shape={arr.shape} "
                    f"min={np.nanmin(arr)} max={np.nanmax(arr)}"
                )
                print(
                    f"[DarkMatter][DEBUG] local nonzero_count={nonzero_count} "
                    f"sample_first_row_16={arr_sample}"
                )
                print(
                    f"[DarkMatter][DEBUG] local channels={len(self.detector_to_channels)} "
                    f"events={len(self.event_to_metadata)}"
                )
                return

            if self.runtime_dataset["mode"] in ("s3_explicit", "http_explicit"):
                # Remote: OpenVisus LoadDataset(idx_url) — prefer HTTPS idx URL with gateway query keys.
                print(f"[DarkMatter][DEBUG] {self.runtime_dataset['mode']} mid={mid_file}")
                print(f"[DarkMatter][DEBUG] idx_uri={_redact_url_secrets(self.runtime_dataset['idx_uri'])}")
                print(f"[DarkMatter][DEBUG] txt_uri={_redact_url_secrets(self.runtime_dataset['txt_uri'])}")
                print(f"[DarkMatter][DEBUG] csv_uri={_redact_url_secrets(self.runtime_dataset['csv_uri'])}")
                if self.runtime_dataset["mode"] == "http_explicit" and not self.s3_auth_override:
                    idx_parts = urlsplit(self.runtime_dataset["idx_uri"])
                    idx_query = parse_qs(idx_parts.query or "")
                    access_from_query = (idx_query.get("access_key", [""])[0] or "").strip()
                    secret_from_query = (idx_query.get("secret_key", [""])[0] or "").strip()
                    endpoint_from_query = f"{idx_parts.scheme}://{idx_parts.netloc}" if idx_parts.scheme and idx_parts.netloc else ""
                    if access_from_query and secret_from_query:
                        self.set_s3_auth_override(endpoint_from_query, access_from_query, secret_from_query)
                        print("[DarkMatter][DEBUG] loaded S3 auth override from idx URL query credentials")

                idx_for_read = self.runtime_dataset["idx_uri"]
                if str(idx_for_read).startswith("s3://"):
                    override = self.s3_auth_override or {}
                    gateway_base = override.get("endpoint_url") or get_s3_http_gateway_base()
                    http_idx = s3_uri_to_http_url(idx_for_read, gateway_base) if gateway_base else ""
                    if http_idx:
                        idx_for_read = with_query_params(
                            http_idx,
                            {
                                "access_key": override.get("aws_access_key_id", ""),
                                "secret_key": override.get("aws_secret_access_key", ""),
                                "region_name": override.get("region_name", "us-east-1"),
                            },
                        )
                        print("[DarkMatter][DEBUG] LoadDataset uses HTTPS idx URL built from s3:// with inline credentials")
                    else:
                        print(
                            "[DarkMatter][WARN] No S3 gateway base URL in env; "
                            "LoadDataset may fail on raw s3:// idx_uri"
                        )

                # Linked / remote: notebook-style only — LoadDataset(HTTPS idx with keys) + read.
                # Never rewrite (filename_template), never object-proxy stubs, never materialize.
                dataset_identifier = str(uuid or "").strip()
                last_load_err = None
                self.scene_data = None
                primary_read = str(idx_for_read or "").strip()
                print(
                    "[DarkMatter][DEBUG] remote LoadDataset (OpenVisus fetches bins; no idx rewrite): "
                    f"{_redact_url_secrets(primary_read)}"
                )
                try:
                    self.scene_data = read_openvisus_field(primary_read)
                except Exception as ex:
                    last_load_err = ex
                    print(f"[DarkMatter][WARN] remote HTTPS/s3 LoadDataset failed: {ex}")
                    self.scene_data = None

                if self.scene_data is None:
                    base_err = last_load_err or RuntimeError("OpenVisus LoadDataset returned no scene data")
                    raise RuntimeError(
                        "OpenVisus could not load linked/remote DarkMatter scene data via "
                        f"LoadDataset({_redact_url_secrets(primary_read)!r}). "
                        "No idx template rewrite or object-proxy fallback is used; "
                        "fix the remote .idx / gateway so OpenVisus can fetch bins itself "
                        "(same as LoadDataset(https://…idx?access_key&secret_key) + read())."
                    ) from base_err

                direct_arr = np.asarray(self.scene_data)
                if self.runtime_dataset["mode"] == "http_explicit":
                    orig_txt_uri = self.runtime_dataset["txt_uri"]
                    orig_csv_uri = self.runtime_dataset["csv_uri"]
                    disk_sidecars = try_read_darkmatter_sidecars_from_disk(
                        mid_file,
                        self.runtime_dataset,
                        str(save_dir) if has_args else "",
                        str(uuid or ""),
                    )
                    if disk_sidecars is not None:
                        txt_lines, csv_lines = disk_sidecars
                    else:
                        stem_bases: List[str] = []
                        mf = str(mid_file or "").strip()
                        idx_uri_rt = str(self.runtime_dataset.get("idx_uri") or "").strip()
                        for hint in sidecar_stem_hints_from_idx_uri(idx_uri_rt):
                            if hint not in stem_bases:
                                stem_bases.append(hint)
                        if mf and mf not in stem_bases:
                            stem_bases.append(mf)
                        if not any(b.lower() == "visus" for b in stem_bases):
                            stem_bases.append("visus")
                        last_sidecar_err: Optional[BaseException] = None
                        txt_lines = []
                        csv_lines = []
                        for base in stem_bases:
                            tu, cu = sidecar_http_urls_for_basename(orig_txt_uri, orig_csv_uri, base)
                            if not tu or not cu:
                                continue
                            try:
                                txt_lines, csv_lines = load_http_explicit_sidecar_lines(
                                    tu, cu, self.s3_auth_override
                                )
                                if base != mf:
                                    print(
                                        f"[DarkMatter][DEBUG] sidecars loaded using alternate basename {base!r} "
                                        f"(mid_file={mf!r})"
                                    )
                                break
                            except Exception as exc:
                                last_sidecar_err = exc
                                print(f"[DarkMatter][WARN] sidecar load failed for basename {base!r}: {exc}")
                        if not txt_lines or not csv_lines:
                            raise RuntimeError(
                                "DarkMatter requires .txt/.csv metadata files; "
                                "disk, S3, and HTTP reads failed for all tried basenames "
                                f"({stem_bases})."
                            ) from last_sidecar_err
                else:
                    txt_lines = read_s3_text_lines(self.runtime_dataset["txt_uri"], auth_override=self.s3_auth_override)
                    csv_lines = read_s3_text_lines(self.runtime_dataset["csv_uri"], auth_override=self.s3_auth_override)
                self.detector_to_channels = create_channel_metadata_map_from_lines(txt_lines)
                self.event_to_metadata = create_event_metadata_map_from_lines(csv_lines)
                arr = np.asarray(self.scene_data)
                arr_min = np.nanmin(arr) if arr.size else np.nan
                arr_max = np.nanmax(arr) if arr.size else np.nan
                arr_sample = arr[0, :16].tolist() if arr.ndim == 2 and arr.shape[0] > 0 else []
                nonzero_count = int(np.count_nonzero(arr)) if arr.size else 0
                print(
                    f"[DarkMatter][DEBUG] s3 scene_data dtype={arr.dtype} shape={arr.shape} "
                    f"min={arr_min} max={arr_max}"
                )
                print(
                    f"[DarkMatter][DEBUG] s3 nonzero_count={nonzero_count} "
                    f"sample_first_row_16={arr_sample}"
                )
                print(
                    f"[DarkMatter][DEBUG] s3 txt_lines={len(txt_lines)} csv_lines={len(csv_lines)} "
                    f"channels={len(self.detector_to_channels)} events={len(self.event_to_metadata)}"
                )
                # All-zero scene_data can be legitimate or indicate bin read issues; do not
                # raise (that triggered a misleading S3 credential UI). Logs carry the signal.
                if self.runtime_dataset["mode"] == "s3_explicit" and arr.size and arr_min == 0 and arr_max == 0:
                    print(
                        "[DarkMatter][WARN] scene_data min=0 max=0 for s3_explicit; "
                        "continuing (verify HTTPS idx URL / OpenVisus load if plot is empty)."
                    )
                if self.runtime_dataset["mode"] == "http_explicit" and arr.size and arr_min == 0 and arr_max == 0:
                    print("[DarkMatter][WARN] scene_data min=0 max=0 for http_explicit; continuing (may be valid dataset values).")
                return

        # In ScientistCloud-served mode we should never download/copy data locally.
        # Require an explicit local or s3 dataset resolution.
        if has_args:
            raise RuntimeError(
                "No explicit dataset source resolved for served mode. "
                "Expected local folder or s3://... dataset URL."
            )

        cached_files = os.listdir(FILES_VOLUME)
        if cached_files and len(cached_files) > 20:
            os.remove(os.path.join(FILES_VOLUME, cached_files[0]))

        if mid_file not in cached_files:
            download_processed_files(mid_file)

        self.detector_to_channels = create_channel_metadata_map(
            os.path.join(FILES_VOLUME, mid_file, f"{mid_file}.txt")
        )
        self.event_to_metadata = create_event_metadata_map(
            os.path.join(FILES_VOLUME, mid_file, f"{mid_file}.csv")
        )
        idx_for_read = os.path.join(FILES_VOLUME, mid_file, f"{mid_file}.idx")
        print(f"[DarkMatter][DEBUG] LoadDataset input={idx_for_read}")
        self.scene_data = read_openvisus_field(idx_for_read)

    def load_events(self):
        if self.has_scene_data():
            st = set()
            for k in self.detector_to_channels.keys():
                evt = k.split("_")[0]
                if evt not in st:
                    st.add(evt)
            events = list(st)
            events.sort()
            self.events = events

    def load_detectors(self, event_id):
        if self.has_scene_data():
            detectors, detectors_map = [], defaultdict(bool)
            for k in self.detector_to_channels.keys():
                if event_id in k:
                    multichoice_detectors = k.split("_")[1]
                    detectors.append(f"D{multichoice_detectors}")
                    detectors_map[f"{event_id}_{multichoice_detectors}_Phonon_4096"] = (
                        True
                    )

            self.detectors, self.detectors_map = detectors, detectors_map

    def update_detectors_map(self, detectors):
        detectors = set([d[1] for d in detectors])
        for k in self.detectors_map.keys():
            if k.split("_")[1] not in detectors:
                self.detectors_map[k] = False
            else:
                self.detectors_map[k] = True

    def load_channel_data(self, detectors):
        if self.has_scene_data() and len(detectors) > 0:
            channels = []
            for k in self.detectors_map.keys():
                lo, hi = self.detector_to_channels[k]
                data = self.scene_data[lo:hi]
                channels.append((k, data))
            self.channels_data = channels
        else:
            self.channels_data = []

    def load_event_metadata(self, eventID):
        self.event_metadata = self.event_to_metadata[eventID]

    def add_channel(self, channel_name, line: GlyphRenderer):
        self.channel_to_renderer[channel_name] = line

    def send_notification(self, ntype, text):
        colors = {
            SUCCESS: "#2e7d32",
            ERROR: "#c62828",
            INFO: "#1565c0",
        }
        color = colors.get(ntype, "#333333")
        self.notification_div.text = (
            f"<div style='color:{color}; font-weight:600; padding:8px 10px; "
            f"border:1px solid {color}33; background:{color}14; border-radius:6px;'>{escape(str(text))}</div>"
        )
        self.notification_div.visible = True

    def handle_channel_selection(self, channel_name, state):
        """
        Parameters
        ----------
        channel_name (str): the name of the channel (C1, C2, ..., Cn).
        state (bool): the visibility state to transition to.
        """
        for k in self.channel_to_renderer.keys():
            if channel_name in k and self.detectors_map[k.split("_C")[0]]:
                self.channel_to_renderer[k].visible = state

    def fig_deep_clean(self):
        for renderer in self.channel_to_renderer.values():
            self.fig.renderers.remove(renderer)
        self.channel_to_renderer = defaultdict(GlyphRenderer)

    def clean_channels(self):
        for renderer in self.channel_to_renderer.values():
            renderer.visible = False

    def toggle_event_controls(self, state):
        self.first_event_button.disabled = state
        self.prev_event_button.disabled = state
        self.next_event_button.disabled = state
        self.last_event_button.disabled = state

    def toggle_loading_spinner(self, state, label: Optional[str] = None):
        """Show/hide loading UI for the long OpenVisus + sidecar fetch."""
        self.loading_dataset_spinner.visible = bool(state)
        self.loading_progress_banner.visible = bool(state)
        if label:
            self._loading_label = str(label)

        if state:
            self._loading_started_at = datetime.now(timezone.utc)
            self._ensure_loading_tick()
            self.loading_dataset_spinner.text = (
                "<div style='display:flex; align-items:center; gap:10px; padding:10px 12px; "
                "border:1px solid #b6d0fe; background:#eef5ff; border-radius:8px;'>"
                "<span style='display:inline-block; width:16px; height:16px; border:2px solid #2f6fed; "
                "border-top-color:transparent; border-radius:50%; "
                "animation:dmspin 0.8s linear infinite;'></span>"
                f"<span style='font-weight:600; color:#1d4ed8;'>Loading {escape(self._loading_label)}…</span>"
                "</div>"
                "<style>@keyframes dmspin {{ to {{ transform: rotate(360deg); }} }}</style>"
            )
            self.loading_progress_banner.text = self._loading_banner_html(0)
            self._loading_portal_signal.value = f"1\x1e{self._loading_label}\x1e{time.time()}"
        else:
            self._stop_loading_tick()
            self._loading_started_at = None
            self.loading_dataset_spinner.text = ""
            self.loading_progress_banner.text = ""
            self.loading_progress_banner.visible = False
            self._loading_portal_signal.value = f"0\x1e\x1e{time.time()}"

    def _loading_banner_html(self, elapsed_s: int) -> str:
        label = escape(self._loading_label or "dataset")
        mins, secs = divmod(max(0, int(elapsed_s)), 60)
        elapsed = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
        hint = (
            "Fetching OpenVisus tiles and channel metadata. "
            "Linked remote data often takes one minute or more."
        )
        return (
            "<div style='padding:12px 14px; border:1px solid #93c5fd; background:linear-gradient(180deg,#eff6ff,#dbeafe);"
            "border-radius:10px; box-shadow:0 1px 2px rgba(15,23,42,0.06);'>"
            f"<div style='font-weight:700; color:#1e3a8a; margin-bottom:4px;'>Loading {label}</div>"
            f"<div style='font-size:13px; color:#1e40af; margin-bottom:10px;'>{hint}</div>"
            "<div style='height:10px; background:#bfdbfe; border-radius:999px; overflow:hidden; margin-bottom:8px;'>"
            "<div style='height:100%; width:40%; background:#2563eb; border-radius:999px; "
            "animation:dmbar 1.4s ease-in-out infinite;'></div></div>"
            f"<div style='font-size:12px; color:#334155;'>Elapsed: <b>{elapsed}</b> — please keep this tab open.</div>"
            "</div>"
            "<style>"
            "@keyframes dmbar { 0% { transform: translateX(-100%); } 50% { transform: translateX(160%); } "
            "100% { transform: translateX(400%); } }"
            "@keyframes dmspin { to { transform: rotate(360deg); } }"
            "</style>"
        )

    def _refresh_loading_progress_ui(self, force_elapsed: Optional[int] = None):
        if not self.loading_progress_banner.visible:
            return
        if force_elapsed is not None:
            elapsed = force_elapsed
        elif self._loading_started_at is not None:
            elapsed = int((datetime.now(timezone.utc) - self._loading_started_at).total_seconds())
        else:
            elapsed = 0
        self.loading_progress_banner.text = self._loading_banner_html(elapsed)

    def _ensure_loading_tick(self):
        if self._loading_tick_cb is not None:
            return
        try:
            self._loading_tick_cb = curdoc().add_periodic_callback(self._on_loading_tick, 1000)
        except Exception as ex:
            print(f"[DarkMatter][WARN] could not start loading progress tick: {ex}")
            self._loading_tick_cb = None

    def _stop_loading_tick(self):
        cb = self._loading_tick_cb
        self._loading_tick_cb = None
        if cb is None:
            return
        try:
            curdoc().remove_periodic_callback(cb)
        except Exception:
            pass

    def _on_loading_tick(self):
        if not self.loading_progress_banner.visible:
            self._stop_loading_tick()
            return
        self._refresh_loading_progress_ui()

    def add_line_glyph(self, data, label):
        d_num = label.split("_")[1]
        y = np.asarray(data, dtype=float)

        self.add_channel(
            label,
            self.fig.line(
                x=list(range(len(y))),
                y=y,
                name=label,
                color=self.palettes[COLORS[int(d_num)]][self.gradient_idx],
                line_width=3,
            ),
        )
        self.gradient_idx += 1 if self.gradient_idx + 1 < 20 else 0

    def render_legend_glyph(self):
        # Reset legend entries each time detectors change.
        if self.fig.legend:
            self.fig.legend.items = []
        for d in self.detectors_map.keys():
            d_num = d.split("_")[1]
            self.fig.line(
                x=[0, 1],
                y=[0, 0],
                legend_label=f"D{d_num}",
                line_color=COLORS[int(d_num)],
                line_width=3,
                visible=False,
            )
            self.fig.legend.label_text_font_size = '18pt'

    def render_event_metadata(self):
        self.event_metadata_widget.text = f"""
       <style>
       .title {{
            text-align: center;
            font-size: 22px;
            font-weight: 500;
       }}
        .styled-table {{
            width: 100%;
            margin: 0 auto;
            border-collapse: collapse;
            font-size: 16px;
        }}
        .styled-table th, .styled-table td {{
            padding: 4px;
            text-align: center;
        }}
        .styled-table th {{
            background-color: #0072b5;
            color: #ffffff;
            border: black solid 1px;
        }}
        </style>
        <div class="title">Event Metadata</div>
        <table class="styled-table">
            <thead>
                <tr>
                    <th>Trigger Type</th>
                    <th>Readout Type</th>
                    <th>Global Timestamp</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{self.event_metadata.trigger_type}</td>
                    <td>{self.event_metadata.readout_type}</td>
                    <td>{self.event_metadata.global_timestamp}</td>
                </tr>
            </tbody>
        </table>
    """

    def render_app_info_text(self, text: str):
        self.app_info_text.text = f"""
       <style>
       .title {{
            text-align: center;
            font-size: 16px;
            font-weight: 400;
       }}
        </style>
        <div class="title">{text}</div>
        """

    def render_channels(self, detectors):
        detectors = set([d[1] for d in detectors])
        # create renderers for new detectors, if any
        for channel in self.channels_data:
            channel_name, datarows = channel
            self.reset_gradient_idx()
            for i, data in enumerate(datarows):
                channel_ID = f"{channel_name}_C{str(i+1)}"
                if channel_ID not in self.channel_to_renderer:
                    self.add_line_glyph(data, channel_ID)
                else:
                    self.channel_to_renderer[channel_ID].visible = True

        # check any deselected detectors that are currently shown in the plot, hide them
        if len(detectors) > 0:
            for d in self.channel_to_renderer.keys():
                if d.split("_")[1] not in detectors:
                    self.channel_to_renderer[d].visible = False
        else:
            self.clean_channels()


def main():
    runtime_remote_url = "s3"
    runtime_dataset = None
    if len(sys.argv) == 2:
        arg = sys.argv[1].strip()
        runtime_dataset = derive_dataset_from_local_dir(arg)
        if runtime_dataset is None:
            runtime_dataset = derive_dataset_from_remote_uri(arg)
        # Keep slac.py legacy behavior when arg is not an explicit local/remote dataset.
        runtime_remote_url = arg

    # ScientistCloud-served mode: auto-resolve dataset from init params
    # (save_dir/base_dir/uuid) so renderer data is loaded on first paint.
    if runtime_dataset is None and has_args and uuid:
        runtime_dataset = _find_local_darkmatter_package(str(uuid).strip())
        if runtime_dataset is not None:
            runtime_remote_url = str(uuid).strip()

    if runtime_dataset is None and has_args:
        for candidate in [save_dir, base_dir, uuid]:
            candidate = str(candidate or "").strip()
            if not candidate:
                continue
            ds = derive_dataset_from_local_dir(candidate)
            if ds is not None:
                # Linked S3 IDX often materializes only visus.idx under converted/<uuid> while
                # visus.txt / visus.csv remain on object storage. Do not lock in local_explicit here
                # or we skip derive_dataset_from_uuid(), which falls back to google_drive_link.
                # Also ignore converted proxy stubs when upload already has a native package.
                if _darkmatter_idx_is_proxy_stub(str(ds.get("idx_path") or "")) and _upload_has_native_darkmatter_idx(
                    str(uuid or "").strip()
                ):
                    print(
                        f"[DarkMatter][DEBUG] ignoring converted proxy stub {ds['idx_path']!r}; "
                        "prefer upload package"
                    )
                    continue
                if os.path.isfile(ds["txt_path"]) and os.path.isfile(ds["csv_path"]):
                    runtime_dataset = ds
                    runtime_remote_url = candidate
                    print(
                        f"[DarkMatter][DEBUG] resolved runtime_dataset from init params: "
                        f"mode={ds['mode']} mid={ds['mid_file']}"
                    )
                    break
                print(
                    f"[DarkMatter][DEBUG] init params path {candidate!r} has idx but missing "
                    f"txt/csv sidecars; continuing resolution"
                )
            ds = derive_dataset_from_remote_uri(candidate)
            if ds is not None:
                runtime_dataset = ds
                runtime_remote_url = candidate
                print(
                    f"[DarkMatter][DEBUG] resolved runtime_dataset from init params: "
                    f"mode={ds['mode']} mid={ds['mid_file']}"
                )
                break

    # UUID-only launches for remote-link datasets usually need Mongo lookup
    # (source_path/google_drive_link) to map to explicit s3/http dataset URIs.
    if runtime_dataset is None and has_args:
        runtime_dataset = derive_dataset_from_uuid(uuid)
        if runtime_dataset is not None:
            runtime_remote_url = str(uuid or "").strip() or runtime_remote_url

    if init_failed:
        return

    if has_args and not is_authorized:
        error_text = "Authentication failed. Please sign in through ScientistCloud and reopen this dashboard."
        if deploy_server:
            error_text = (
                "Authentication failed. Please sign in through ScientistCloud and reopen this dashboard. "
                f"[Open ScientistCloud]({deploy_server})"
            )
        curdoc().add_root(
            column(
                Div(text="<h2>Access denied</h2>"),
                Div(text=f"<p>{error_text}</p>"),
            )
        )
        return

    if has_args and runtime_dataset is None and _looks_like_dataset_uuid(str(uuid)):
        hint = (
            "<h2>Dataset could not be loaded</h2>"
            f"<p>No OpenVisus dataset resolved for UUID <code>{escape(str(uuid))}</code>. "
            "Check container logs for lines starting with <code>[DarkMatter]</code>.</p>"
            "<p><b>Remote-linked data (common fixes)</b></p><ul>"
            "<li><b>Folder / prefix URL</b> (no <code>.idx</code> in the link): the Mongo document needs "
            "<code>s3_access_key_id</code> and <code>s3_secret_access_key</code> (and usually "
            "<code>s3_endpoint_url</code>) so the dashboard can list the bucket and pick an <code>.idx</code>.</li>"
            "<li><b>HTTPS gateway links</b> must be <b>path-style</b>: "
            "<code>https://&lt;host&gt;/&lt;bucket&gt;/path/to/prefix/</code> — not "
            "<code>https://bucket.host/...</code> unless you use <code>s3://</code> directly.</li>"
            "<li>Alternatively put <code>access_key</code> / <code>secret_key</code> (and optional "
            "<code>region_name</code>) in the link query string for the object gateway.</li>"
            "<li>Direct <code>*.idx</code> URLs still need reachable <code>.txt</code> and <code>.csv</code> "
            "sidecars (same stem) or materialized files under <code>/mnt/visus_datasets/converted/&lt;uuid&gt;/</code>.</li>"
            "</ul>"
        )
        curdoc().add_root(column(Div(text=hint, width_policy="max", styles={"max-width": "960px"})))
        return

    app_state = AppState(runtime_remote_url, runtime_dataset=runtime_dataset)

    # ---------------- WIDGETS ---------------------------
    select_scene = AutocompleteInput(
        name="Mid File",
        restrict=True,
        completions=app_state.mid_files,
        placeholder="Search Mid File",
        value=app_state.mid_files[0] if app_state.mid_files else "",
    )

    event_controls_tooltip = Div(text="<small>first event, prev event, next event, last event</small>")

    input_event = AutocompleteInput(
        name="Event ID",
        restrict=True,
        completions=[],
        placeholder="Search Event",
        value="",
    )

    event_controls = row(
        Div(text="", width=30),
        app_state.first_event_button,
        app_state.prev_event_button,
        app_state.next_event_button,
        app_state.last_event_button,
        event_controls_tooltip,
    )

    multichoice_detectors = MultiChoice(
        name="Detectors",
        options=[],
        value=[],
    )

    checkbox_toggle_detectors = Checkbox(
        name="Select/Deselect All Detectors", disabled=True
    )

    cite_button = Button(label="Cite", button_type="success")
    cite_button.js_on_event(
        "button_click",
        CustomJS(code="""
        const w = window.open("https://nsdf-fabric.github.io/nsdf-slac/citations/", "_blank", "noopener,noreferrer");
        if (w) w.opener = null;
        """),
    )

    s3_auth_status = Div(text="", visible=False, width=420)
    s3_endpoint_input = TextInput(
        title="S3 Endpoint URL",
        value=os.getenv("ENDPOINT_URL", ""),
        width=420,
    )
    s3_access_input = TextInput(title="AWS Access Key ID", value="", width=420)
    s3_secret_input = PasswordInput(title="AWS Secret Access Key", value="", width=420)
    s3_apply_button = Button(label="Apply Credentials & Retry", button_type="warning", width=220)
    s3_auth_panel = column(
        Div(
            text=(
                "<div style='font-weight:700; color:#7a3e00; margin-bottom:6px;'>"
                "S3 authorization required"
                "</div>"
                "<div style='margin-bottom:8px;'>"
                "Remote metadata could not be read. Enter runtime credentials and retry."
                "</div>"
            )
        ),
        s3_auth_status,
        s3_endpoint_input,
        s3_access_input,
        s3_secret_input,
        s3_apply_button,
        visible=False,
        width=860,
        sizing_mode="stretch_width",
        styles={
            "border": "2px solid #d98e2b",
            "background-color": "#fff7ec",
            "padding": "12px",
            "margin-bottom": "10px",
        },
    )

    # ------------------- REACTIVITY ---------------------
    def toggle_all_component_interactivity(state: bool):
        select_scene.disabled = state
        input_event.disabled = state
        multichoice_detectors.disabled = state
        checkbox_toggle_detectors.disabled = state
        app_state.toggle_event_controls(state)

    def filter_channels(button):
        state = True if button.button_type == "primary" else False
        channel_name = button.label
        app_state.handle_channel_selection(channel_name, not state)
        button.button_type = (
            "default" if button.button_type == "primary" else "primary"
        )

    def update_events(mid_file):
        app_state.toggle_loading_spinner(True, label=str(mid_file))
        app_state.render_app_info_text(f"Loading {mid_file}...")
        toggle_all_component_interactivity(True)
        load_ok = False
        try:
            app_state.load_scene_data(mid_file)
            load_ok = True
            app_state.send_notification(SUCCESS, f"Loaded {mid_file} successfully")

            app_state.load_events()
            input_event.completions = app_state.events
            # needs to transition from empty to trigger update_detectors
            input_event.value = ""
            if input_event.completions:
                input_event.value = input_event.completions[0]
            else:
                app_state.send_notification(INFO, f"No events found for {mid_file}")
        except Exception as exc:
            print(f"[DarkMatter][ERROR] update_events failed for {mid_file}: {exc}")
            traceback.print_exc()
            app_state.send_notification(ERROR, str(exc))
            app_state.render_app_info_text(f"Failed to load {mid_file}")
            error_text = str(exc)
            auth_failed = (
                "403" in error_text
                or "forbidden" in error_text.lower()
                or "missing aws credentials" in error_text.lower()
                or "unable to locate credentials" in error_text.lower()
                or "access denied" in error_text.lower()
            )
            # ScientistCloud portal passes no user secrets; S3 access is server-side (Mongo + proxy).
            # Only show manual credential UI for local/dev runs without URL args.
            if auth_failed and not has_args:
                s3_auth_panel.visible = True
                s3_auth_status.text = "<span style='color:#b35c00;'>Authorization failed. Enter credentials and retry.</span>"
                s3_auth_status.visible = True
            input_event.completions = []
            input_event.value = ""
        finally:
            toggle_all_component_interactivity(False)
            app_state.toggle_loading_spinner(False)
            if load_ok:
                app_state.render_app_info_text("")

    def update_detectors(eventID):
        if eventID != "":
            app_state.fig_deep_clean()
            app_state.load_detectors(eventID)
            app_state.render_legend_glyph()
            app_state.load_event_metadata(eventID)
            app_state.render_event_metadata()
            multichoice_detectors.options = app_state.detectors
            checkbox_toggle_detectors.disabled = False

            # update event index on search (options is sorted)
            idx = bisect_left(input_event.completions, eventID)
            if idx >= 0 and idx < len(input_event.completions):
                app_state.update_event_idx(idx)
            # needs to transition from empty to trigger update_fig
            multichoice_detectors.value = []
            multichoice_detectors.value = app_state.detectors
            checkbox_toggle_detectors.active = True

    def toggle_detectors(state):
        multichoice_detectors.value = app_state.detectors if state else []

    def update_fig(detectors):
        app_state.toggle_event_controls(True)
        app_state.update_detectors_map(detectors)
        app_state.load_channel_data(detectors)
        disable_buttons()
        app_state.render_channels(detectors)
        app_state.toggle_event_controls(False)

    def update_event_to_first(_=None):
        if not input_event.completions:
            return
        input_event.value = input_event.completions[0]
        app_state.event_idx = 0

    def update_event_to_last(_=None):
        if not input_event.completions:
            return
        input_event.value = input_event.completions[-1]
        app_state.event_idx = len(app_state.events) - 1

    def update_event_to_next(_=None):
        if not input_event.completions:
            return
        app_state.event_idx = (
            app_state.event_idx
            if app_state.event_idx + 1 >= len(app_state.events)
            else app_state.event_idx + 1
        )
        input_event.value = input_event.completions[app_state.event_idx]

    def update_event_to_prev(_=None):
        if not input_event.completions:
            return
        app_state.event_idx = (
            0 if app_state.event_idx - 1 < 0 else app_state.event_idx - 1
        )
        input_event.value = input_event.completions[app_state.event_idx]

    def apply_s3_credentials_and_retry(_=None):
        app_state.set_s3_auth_override(
            s3_endpoint_input.value,
            s3_access_input.value,
            s3_secret_input.value,
        )
        s3_auth_status.text = "<span style='color:#1f7a1f;'>Credentials applied. Retrying...</span>"
        s3_auth_status.visible = True
        target_mid = select_scene.value.strip() if select_scene.value else ""
        if target_mid:
            update_events(target_mid)
        if app_state.has_scene_data():
            s3_auth_panel.visible = False

    app_state.first_event_button.on_click(update_event_to_first)
    app_state.prev_event_button.on_click(update_event_to_prev)
    app_state.next_event_button.on_click(update_event_to_next)
    app_state.last_event_button.on_click(update_event_to_last)
    s3_apply_button.on_click(apply_s3_credentials_and_retry)
    select_scene.on_change("value", lambda attr, old, new: update_events(new))
    input_event.on_change("value", lambda attr, old, new: update_detectors(new))
    checkbox_toggle_detectors.on_change("active", lambda attr, old, new: toggle_detectors(bool(new)))
    multichoice_detectors.on_change("value", lambda attr, old, new: update_fig(new))
    # ---------------------------------------------------

    channel_buttons = [Button(label=f"C{i+1}", button_type="primary", width=70) for i in range(20)]
    for btn in channel_buttons:
        btn.on_click(lambda b=btn: filter_channels(b))
    channels_grid = gridplot([channel_buttons[i:i + 5] for i in range(0, 20, 5)], merge_tools=False)

    def disable_buttons():
        """
        Disable buttons up to max channel count (e.g. if D1 has the most detectors at 4 disable 5-20)
        """
        limit = 0
        for _, arr in app_state.channels_data:
            limit = max(limit, len(arr))
        for i in range(20):
            channel_buttons[i].disabled = False if i < limit else True

    sidebar = column(
        cite_button,
        select_scene,
        app_state.loading_dataset_spinner,
        app_state.notification_div,
        app_state.app_info_text,
        input_event,
        event_controls,
        multichoice_detectors,
        checkbox_toggle_detectors,
        channels_grid,
        app_state.event_metadata_widget,
        app_state._loading_portal_signal,
        width=430,
    )
    header_banner = create_header_banner(
        dataset_name=name if name else "",
        dashboard_type="Nexus DM Dashboard",
    )
    plot_column = column(
        app_state.loading_progress_banner,
        app_state.fig,
        sizing_mode="stretch_both",
    )
    main_layout = row(sidebar, plot_column, sizing_mode="stretch_both")
    curdoc().add_root(column(header_banner, s3_auth_panel, main_layout, sizing_mode="stretch_both"))
    if select_scene.value:
        # Defer heavy OpenVisus load so the loading notification paints first.
        initial_mid = select_scene.value
        app_state.toggle_loading_spinner(True, label=str(initial_mid))
        app_state.render_app_info_text(f"Loading {initial_mid}…")
        app_state.send_notification(
            INFO,
            "Loading Dark Matter data — OpenVisus tile fetch can take a minute or more.",
        )
        curdoc().add_next_tick_callback(lambda: update_events(initial_mid))


main()
atexit.register(cleanup_mongodb)

# Test locally:
# bokeh serve darkmatter.py --port 8058 --allow-websocket-origin=localhost:8058 --args "/Users/amygooch/GIT/SCI/DATA/07180808_1558_F0001"

