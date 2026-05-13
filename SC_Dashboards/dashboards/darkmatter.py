import matplotlib.colors as mcolors
import numpy as np
import sys
from typing import DefaultDict, List, Optional
import os
import atexit
from collections import defaultdict
import csv
import traceback
import re
import requests
from dotenv import load_dotenv
from botocore.client import Config
from boto3.session import Session
from bisect import bisect_left
from datetime import datetime, timezone

import OpenVisus as ov
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit
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
    if "/" not in no_scheme:
        return no_scheme, ""
    bucket, key = no_scheme.split("/", 1)
    return bucket, key


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
                "library; all-zero here usually means those GETs failed or paths do not match the gateway "
                "(not something this Python read loop can repair). Allow openvisus-resolved-idx "
                "(do not set SCLIB_DISABLE_OPENVISUS_RESOLVED_IDX=1 on SCLib) or fix OpenVisus + gateway "
                "so native s3:// LoadDataset is not empty."
            )
    if last_sample is not None:
        return last_sample
    return db.read(field=field)


# Resolved idx on disk uses ``visus.idx`` (matches ``openvisus-resolved-idx`` default / conversion output).
RESOLVED_IDX_S3_OUTPUT_NAME = "visus.idx"
RESOLVED_IDX_PROXY_OUTPUT_NAME = "visus_proxy.idx"


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
    """When true, never POST to openvisus-resolved-idx (pure HTTPS / no local resolved s3 idx materialization)."""
    return str(os.getenv("DARKMATTER_DISABLE_RESOLVED_IDX", "")).strip().lower() in ("1", "true", "yes", "on")


def _darkmatter_http_explicit_no_fallback() -> bool:
    """
    When true, http_explicit loads use only the primary linked HTTPS idx URL for OpenVisus
    (no resolved-idx API, no native s3:// LoadDataset, no materialized local .idx fallbacks).
    Set DARKMATTER_HTTP_EXPLICIT_NO_FALLBACK=1 to reproduce or debug gateway HTTPS behavior alone.
    """
    return str(os.getenv("DARKMATTER_HTTP_EXPLICIT_NO_FALLBACK", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


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

    Set DARKMATTER_DISABLE_RESOLVED_IDX=1 in the dashboard container to skip this entirely
    (e.g. testing linked HTTPS idx only without regenerating the resolved idx after deletes).
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

    # Prefer explicit converted idx recorded by background conversion.
    if converted_idx_path and os.path.isfile(converted_idx_path):
        ds = derive_dataset_from_local_dir(converted_idx_path)
        if ds is not None and (not has_remote_link or (os.path.isfile(ds["txt_path"]) and os.path.isfile(ds["csv_path"]))):
            ds["converted_idx_path"] = converted_idx_path
            print(
                f"[DarkMatter][DEBUG] resolved runtime_dataset from converted_idx_path: "
                f"mode={ds['mode']} mid={ds['mid_file']}"
            )
            return ds

    # Local dashboard contract: converted/<uuid> first, then upload/<uuid>.
    local_idx = resolve_local_idx_file(dataset_uuid) if resolve_local_idx_file else None
    if local_idx:
        ds = derive_dataset_from_local_dir(local_idx)
        if ds is not None and (not has_remote_link or (os.path.isfile(ds["txt_path"]) and os.path.isfile(ds["csv_path"]))):
            if "/converted/" in local_idx:
                ds["converted_idx_path"] = ds["idx_path"]
            print(
                f"[DarkMatter][DEBUG] resolved runtime_dataset from local resolver: "
                f"mode={ds['mode']} mid={ds['mid_file']} idx={ds['idx_path']}"
            )
            return ds
        if ds is not None and has_remote_link:
            print(
                f"[DarkMatter][DEBUG] local idx exists without DarkMatter sidecars; "
                f"using remote dataset metadata instead: idx={local_idx}"
            )

    # Prefer stored HTTPS object-gateway URL (google_drive_link for S3 uploads) over raw s3://.
    for field in ("google_drive_link", "source_path"):
        candidate = str(doc.get(field) or "").strip()
        if not candidate:
            continue
        ds = derive_dataset_from_local_dir(candidate)
        if ds is None:
            ds = derive_dataset_from_remote_uri(candidate, auth_override)
        if ds is not None:
            if auth_override.get("aws_access_key_id") and auth_override.get("aws_secret_access_key"):
                ds["auth_override"] = auth_override
            if converted_idx_path:
                ds["converted_idx_path"] = converted_idx_path
            ensure_http_gateway_credentials_on_dataset(ds)
            print(
                f"[DarkMatter][DEBUG] resolved runtime_dataset from dataset doc field={field}: "
                f"mode={ds['mode']} mid={ds['mid_file']}"
            )
            return ds

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
            preferred = os.path.join(dataset_root, "visus.idx")
            if os.path.isfile(preferred):
                idx_path = preferred
            else:
                idx_matches = []
                for current_root, _dirs, files in os.walk(dataset_root):
                    for filename in files:
                        if filename.lower().endswith(".idx"):
                            idx_matches.append(os.path.join(current_root, filename))
                if not idx_matches:
                    return None
                idx_path = sorted(idx_matches)[0]
            mid_file = os.path.splitext(os.path.basename(idx_path))[0]
            dataset_root = os.path.dirname(idx_path)
    else:
        return None

    txt_path = os.path.join(dataset_root, f"{mid_file}.txt")
    csv_path = os.path.join(dataset_root, f"{mid_file}.csv")

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
    """
    Fix local idx so OpenVisus can load ARCO tiles from disk.

    - filename_template vs real bin layout (flat, nested, or wrong timestep subdir).
    - (time) pattern expects e.g. .../00000/0000.bin but tiles are elsewhere -> neutralize to 0 0 ./
    - idx declares default_compression(zip) while tiles are uncompressed -> default_compression(raw).

    The segment name for template fixes is taken from the idx template line, not mid_file.

    Patched idx is written as *.sc_pathfix.idx (never *.resolved.idx — that suffix triggers OpenVisus
    ARCO internal filename layout and ignores a plain %04x.bin template).
    """
    try:
        with open(idx_path, "r") as f:
            lines = f.readlines()
    except Exception:
        return idx_path

    template_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == "(filename_template)" and i + 1 < len(lines):
            template_idx = i + 1
            break

    if template_idx == -1:
        return idx_path

    template = lines[template_idx].strip()
    seg_m = re.match(r"^\./([^/]+)/%04x\.bin\s*$", template)
    if not seg_m:
        return idx_path
    segment = seg_m.group(1).strip()
    if not segment:
        return idx_path

    dataset_dir = os.path.dirname(os.path.abspath(idx_path))
    expected_root = os.path.join(dataset_dir, segment)
    flat_bin = os.path.join(dataset_dir, "0000.bin")

    tile_root: Optional[str] = None
    if os.path.isdir(expected_root):
        tile_root = _find_arco_bin_directory_under(expected_root)
    if tile_root is None and os.path.isfile(flat_bin):
        tile_root = dataset_dir

    compression_fix = _local_idx_bins_need_raw_compression(idx_path)

    if tile_root is None and not compression_fix:
        return idx_path

    bin_probe_root = tile_root
    if bin_probe_root is None and os.path.isdir(expected_root) and os.path.isfile(
        os.path.join(expected_root, "0000.bin")
    ):
        bin_probe_root = expected_root

    time_line_i = _idx_line_index_after_section(lines, "(time)")
    time_neutralize = False
    if time_line_i is not None and bin_probe_root:
        tname = _expected_time_subdir_for_first_timestep(lines[time_line_i], 0)
        if tname:
            with_time = os.path.join(expected_root, tname, "0000.bin")
            if not os.path.isfile(with_time) and os.path.isfile(os.path.join(bin_probe_root, "0000.bin")):
                time_neutralize = True

    retarget_template = (
        bool(tile_root) and os.path.normpath(tile_root) != os.path.normpath(expected_root)
    )

    if not retarget_template and not time_neutralize and not compression_fix:
        return idx_path

    fixed_lines = list(lines)
    if retarget_template and tile_root:
        # Tiles flat next to the .idx need an absolute template; tiles under ./segment/... are reached
        # via the cache-dir symlink to ../<segment> and a relative ./<segment>/%04x.bin template.
        if os.path.normpath(tile_root) == os.path.normpath(dataset_dir):
            fixed_lines[template_idx] = f"{dataset_dir}/%04x.bin\n"
        else:
            fixed_lines[template_idx] = f"./{segment}/%04x.bin\n"
    if time_neutralize and time_line_i is not None:
        # Tiles live beside ./segment/ without the timestep subdirectory implied by %00000d/ etc.
        fixed_lines[time_line_i] = "0 0 ./\n"
    if compression_fix:
        fixed_lines = _fix_idx_field_compression_zip_to_raw(fixed_lines)

    # OpenVisus ARCO resolves companion tiles under <parent>/<idx_stem>/..., not only filename_template.
    # Writing foo.sc_pathfix.idx makes it look in foo.sc_pathfix/ (wrong). Keep the original .idx basename
    # inside a small cache dir and symlink <segment> -> ../<segment> so block paths match the real tree.
    stem = os.path.splitext(os.path.basename(idx_path))[0]
    cache_dir = os.path.join(dataset_dir, ".dm_openvisus_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cached_idx = os.path.join(cache_dir, f"{stem}.idx")
    seg_link = os.path.join(cache_dir, segment)
    try:
        if os.path.lexists(seg_link) or os.path.islink(seg_link):
            os.unlink(seg_link)
        rel_target = os.path.relpath(os.path.join(dataset_dir, segment), cache_dir)
        os.symlink(rel_target, seg_link)
    except OSError as ex:
        print(f"[DarkMatter][WARN] resolve_local_idx_path: segment symlink failed ({ex}); OpenVisus may still mis-resolve tiles")

    with open(cached_idx, "w") as f:
        f.writelines(fixed_lines)
    msg = [f"idx had filename_template {template!r}"]
    if retarget_template and tile_root:
        msg.append(f"bins at {tile_root}")
    if time_neutralize:
        msg.append("(time) neutralized to 0 0 ./ — tiles were not under timestep subdir")
    if compression_fix:
        msg.append("default_compression(zip) -> raw (tiles are uncompressed)")
    msg.append(f"loader idx -> {cached_idx}")
    print(f"[DarkMatter][DEBUG] resolve_local_idx_path: wrote {cached_idx} ({'; '.join(msg)})")
    return cached_idx


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
        for addr_style in ["path", "virtual"]:
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
        for addr_style in ("path", "virtual"):
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
        return None

    keys = _list_s3_idx_keys_at_prefix(bucket, prefix, merged)
    picked = _pick_idx_key_under_prefix(keys, prefix)
    if not picked:
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
        self.loading_dataset_spinner = Div(text="", visible=False, width=200)
        self.app_info_text = Div(text="")
        self.notification_div = Div(text="", visible=False, width=420)

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
                self.detector_to_channels = create_channel_metadata_map(
                    self.runtime_dataset["txt_path"]
                )
                self.event_to_metadata = create_event_metadata_map(
                    self.runtime_dataset["csv_path"]
                )
                print(f"[DarkMatter][DEBUG] LoadDataset input={idx_for_read}")
                # OpenVisus commonly resolves relative filename_template paths (e.g. ./%04x.bin)
                # against the process cwd, not the .idx directory — so `bokeh serve` must not
                # depend on the shell's working directory. Temporarily chdir to the dataset root.
                _dataset_root = os.path.dirname(os.path.abspath(idx_for_read))
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

                # Linked datasets (http_explicit): use the user's HTTPS idx URL first — one logical
                # descriptor with inline keys. Only if that fails or reads all zeros do we try
                # server-resolved idx, then materialized local copies (avoids competing visus.idx vs link).
                dataset_identifier = str(uuid or "").strip()
                last_load_err = None
                self.scene_data = None

                def _scene_is_all_zero(sample) -> bool:
                    arr = np.asarray(sample)
                    if not arr.size:
                        return False
                    return (
                        int(np.count_nonzero(arr)) == 0
                        and float(np.nanmin(arr)) == 0.0
                        and float(np.nanmax(arr)) == 0.0
                    )

                primary_read = str(idx_for_read or "").strip()
                http_no_fb = (
                    self.runtime_dataset["mode"] == "http_explicit"
                    and _darkmatter_http_explicit_no_fallback()
                )
                if http_no_fb:
                    print(
                        "[DarkMatter][DEBUG] DARKMATTER_HTTP_EXPLICIT_NO_FALLBACK=1 — "
                        "OpenVisus uses linked HTTPS idx only (no resolved idx / s3:// / materialized .idx)"
                    )
                if self.runtime_dataset["mode"] == "http_explicit" and primary_read.startswith(
                    ("http://", "https://")
                ):
                    try:
                        print(
                            f"[DarkMatter][DEBUG] primary LoadDataset (linked HTTPS idx): "
                            f"{_redact_url_secrets(primary_read)}"
                        )
                        self.scene_data = read_openvisus_field(primary_read)
                    except Exception as ex:
                        last_load_err = ex
                        print(f"[DarkMatter][WARN] linked HTTPS LoadDataset failed: {ex}")
                        self.scene_data = None

                need_resolved_or_local = self.scene_data is None
                if (
                    not need_resolved_or_local
                    and self.runtime_dataset["mode"] == "http_explicit"
                    and _scene_is_all_zero(self.scene_data)
                    and not http_no_fb
                ):
                    print(
                        "[DarkMatter][WARN] linked HTTPS idx read succeeded but scene is all-zero "
                        "(bins may not load with this template); trying resolved idx next"
                    )
                    need_resolved_or_local = True

                if (
                    not http_no_fb
                    and need_resolved_or_local
                    and self.runtime_dataset["mode"] == "http_explicit"
                    and _looks_like_dataset_uuid(dataset_identifier)
                    and not dataset_identifier.startswith(("http://", "https://", "s3://"))
                    and (self.s3_auth_override or {}).get("aws_access_key_id")
                ):
                    if _darkmatter_disable_resolved_idx_api():
                        print(
                            "[DarkMatter][DEBUG] Skipping openvisus-resolved-idx API "
                            "(DARKMATTER_DISABLE_RESOLVED_IDX) — pure HTTPS / no resolved s3 idx regeneration"
                        )
                    else:
                        try:
                            resolved_idx, _ = resolve_openvisus_resolved_idx_via_api(
                                dataset_identifier=dataset_identifier,
                                user_email=user_email,
                                auth_override=self.s3_auth_override or {},
                                output_filename=RESOLVED_IDX_S3_OUTPUT_NAME,
                                filename_template_mode="s3",
                                force_refresh=True,
                            )
                            if resolved_idx and os.path.isfile(resolved_idx):
                                trial = read_openvisus_field_with_dataset_cwd(resolved_idx)
                                if self.scene_data is None or not _scene_is_all_zero(trial):
                                    self.scene_data = trial
                                    print(f"[DarkMatter][DEBUG] LoadDataset using resolved s3 idx: {resolved_idx}")
                                else:
                                    print(
                                        "[DarkMatter][WARN] resolved s3 idx also all-zero; "
                                        "keeping prior scene_data if any"
                                    )
                        except Exception as ex:
                            last_load_err = ex
                            print(f"[DarkMatter][WARN] resolved s3 idx API / load failed: {ex}")

                    enable_proxy = str(
                        os.getenv("DARKMATTER_ENABLE_PROXY_RESOLVED_IDX", "false")
                    ).strip().lower() in ("1", "true", "yes", "on")
                    if (
                        enable_proxy
                        and self.scene_data is not None
                        and _scene_is_all_zero(self.scene_data)
                        and not _darkmatter_disable_resolved_idx_api()
                    ):
                        try:
                            resolved_proxy, _ = resolve_openvisus_resolved_idx_via_api(
                                dataset_identifier=dataset_identifier,
                                user_email=user_email,
                                auth_override=self.s3_auth_override or {},
                                output_filename=RESOLVED_IDX_PROXY_OUTPUT_NAME,
                                filename_template_mode="proxy",
                                force_refresh=True,
                            )
                            if resolved_proxy and os.path.isfile(resolved_proxy):
                                print(
                                    f"[DarkMatter][DEBUG] optional proxy resolved idx "
                                    f"(DARKMATTER_ENABLE_PROXY_RESOLVED_IDX): {resolved_proxy}"
                                )
                                proxy_scene = read_openvisus_field_with_dataset_cwd(resolved_proxy)
                                if not _scene_is_all_zero(proxy_scene):
                                    self.scene_data = proxy_scene
                                    print("[DarkMatter][DEBUG] proxy resolved idx produced non-zero scene data")
                        except Exception as pex:
                            print(f"[DarkMatter][WARN] proxy resolved idx failed: {pex}")

                # Docker OpenVisus often resolves HTTPS gateway bins as path-only (/bucket/key), producing all-zero
                # reads while laptop `bokeh serve --args https://...` works. Native s3:// + AWS keys matches the
                # upload registration path (s3://scientistcloud/...) and avoids broken gateway HTTP templates.
                if (
                    not http_no_fb
                    and self.runtime_dataset["mode"] == "http_explicit"
                    and (self.scene_data is None or _scene_is_all_zero(self.scene_data))
                    and (self.s3_auth_override or {}).get("aws_access_key_id")
                    and (self.s3_auth_override or {}).get("aws_secret_access_key")
                ):
                    idx_http = str(self.runtime_dataset.get("idx_uri") or "").strip()
                    s3_idx = http_object_url_to_s3_uri(idx_http)
                    if s3_idx:
                        try:
                            ov = self.s3_auth_override or {}
                            idx_parts_fb = urlsplit(idx_http)
                            gw_base = (
                                f"{idx_parts_fb.scheme}://{idx_parts_fb.netloc}"
                                if idx_parts_fb.scheme and idx_parts_fb.netloc
                                else ""
                            )
                            merged_ep = (str(ov.get("endpoint_url") or "").strip() or gw_base)
                            if merged_ep:
                                self.set_s3_auth_override(
                                    merged_ep,
                                    str(ov.get("aws_access_key_id") or ""),
                                    str(ov.get("aws_secret_access_key") or ""),
                                )
                            print(
                                f"[DarkMatter][DEBUG] OpenVisus LoadDataset fallback (native s3:// idx): "
                                f"{s3_idx}"
                            )
                            trial = read_openvisus_field(s3_idx)
                            if not _scene_is_all_zero(trial):
                                self.scene_data = trial
                                print(
                                    "[DarkMatter][DEBUG] native s3:// idx produced non-zero scene data "
                                    "(HTTPS gateway path was likely mis-resolved in this container)"
                                )
                            else:
                                print(
                                    "[DarkMatter][WARN] native s3:// idx read also all-zero "
                                    "(verify ENDPOINT_URL/credentials vs bucket)"
                                )
                        except Exception as s3_ld_exc:
                            print(f"[DarkMatter][WARN] native s3:// LoadDataset fallback failed: {s3_ld_exc}")

                if (
                    self.scene_data is None
                    and self.runtime_dataset["mode"] == "s3_explicit"
                    and _looks_like_dataset_uuid(dataset_identifier)
                    and not dataset_identifier.startswith(("http://", "https://", "s3://"))
                    and (self.s3_auth_override or {}).get("aws_access_key_id")
                ):
                    if _darkmatter_disable_resolved_idx_api():
                        print(
                            "[DarkMatter][DEBUG] Skipping openvisus-resolved-idx for s3_explicit "
                            "(DARKMATTER_DISABLE_RESOLVED_IDX)"
                        )
                    else:
                        try:
                            resolved_idx, _ = resolve_openvisus_resolved_idx_via_api(
                                dataset_identifier=dataset_identifier,
                                user_email=user_email,
                                auth_override=self.s3_auth_override or {},
                                output_filename=RESOLVED_IDX_S3_OUTPUT_NAME,
                                filename_template_mode="s3",
                                force_refresh=False,
                            )
                            if resolved_idx and os.path.isfile(resolved_idx):
                                self.scene_data = read_openvisus_field_with_dataset_cwd(resolved_idx)
                                print(f"[DarkMatter][DEBUG] LoadDataset s3_explicit resolved idx: {resolved_idx}")
                        except Exception as ex:
                            last_load_err = ex
                            print(f"[DarkMatter][WARN] s3_explicit resolved idx failed: {ex}")

                still_need_materialized = (
                    (need_resolved_or_local and self.scene_data is None) and not http_no_fb
                )
                if (
                    not still_need_materialized
                    and self.runtime_dataset["mode"] == "http_explicit"
                    and self.scene_data is not None
                    and _scene_is_all_zero(self.scene_data)
                    and not http_no_fb
                ):
                    still_need_materialized = True

                if still_need_materialized:
                    idx_candidates = []
                    cip = str(self.runtime_dataset.get("converted_idx_path") or "").strip()
                    if cip and os.path.isfile(cip):
                        idx_candidates.append(cip)
                    if has_args and save_dir:
                        sd = str(save_dir or "").strip()
                        for fname in ("visus.idx", f"{mid_file}.idx"):
                            lp = os.path.join(sd, fname)
                            if os.path.isfile(lp):
                                idx_candidates.append(lp)
                                break
                    # Local `bokeh serve --args https://...idx` (no portal paths): look in cwd for materialized idx.
                    if not has_args:
                        cwd = os.path.abspath(os.getcwd())
                        idx_uri_hint = str(self.runtime_dataset.get("idx_uri") or "").strip()
                        for fname in (f"{mid_file}.idx", "visus.idx"):
                            lp = os.path.join(cwd, fname)
                            if os.path.isfile(lp):
                                idx_candidates.append(lp)
                        for hint in sidecar_stem_hints_from_idx_uri(idx_uri_hint):
                            lp = os.path.join(cwd, f"{hint}.idx")
                            if os.path.isfile(lp):
                                idx_candidates.append(lp)
                        try:
                            ds_cwd = derive_dataset_from_local_dir(cwd)
                            if ds_cwd and ds_cwd.get("idx_path"):
                                idx_candidates.append(ds_cwd["idx_path"])
                        except Exception:
                            pass
                    if resolve_local_idx_file:
                        try:
                            rl = resolve_local_idx_file(str(uuid or "").strip())
                            rl = str(rl or "").strip()
                            if rl and os.path.isfile(rl):
                                idx_candidates.append(rl)
                        except Exception:
                            pass
                    deduped = []
                    for p in idx_candidates:
                        if p and p not in deduped:
                            deduped.append(p)
                    idx_candidates = deduped
                    last_zero_trial = None
                    for cand in idx_candidates:
                        try:
                            idx_stem = os.path.splitext(os.path.basename(cand))[0]
                            cand_fixed = resolve_local_idx_path(cand, idx_stem)
                            if cand_fixed != cand:
                                print(f"[DarkMatter][DEBUG] filename_template adjusted idx: {cand} -> {cand_fixed}")
                            trial = read_openvisus_field_with_dataset_cwd(cand_fixed)
                            if _scene_is_all_zero(trial):
                                last_zero_trial = trial
                                print(
                                    f"[DarkMatter][WARN] materialized idx read was all-zero for {cand_fixed!r} "
                                    f"(offline bins often missing under (filename_template) vs {cand_fixed}); "
                                    "sync ARCO blocks next to this .idx or use SCLib resolved-idx when online."
                                )
                                if has_args:
                                    continue
                                continue
                            self.scene_data = trial
                            print(f"[DarkMatter][DEBUG] LoadDataset fallback materialized idx: {cand_fixed}")
                            break
                        except Exception as ex:
                            last_load_err = ex
                            print(f"[DarkMatter][WARN] OpenVisus load failed for materialized idx {cand!r}: {ex}")

                    if self.scene_data is None and not has_args and last_zero_trial is not None:
                        self.scene_data = last_zero_trial
                        print(
                            "[DarkMatter][WARN] local bokeh: using last materialized idx read (all-zero) so "
                            "HTTPS sidecars can still load; plot will be flat until bins exist locally."
                        )

                if self.scene_data is None:
                    last_url = str(idx_for_read or "").strip()
                    if (
                        self.runtime_dataset["mode"] == "http_explicit"
                        and last_url.startswith(("http://", "https://"))
                    ):
                        base_err = last_load_err or RuntimeError("linked HTTPS idx did not load")
                        if http_no_fb:
                            raise RuntimeError(
                                "OpenVisus LoadDataset failed on the linked HTTPS idx only "
                                "(DARKMATTER_HTTP_EXPLICIT_NO_FALLBACK=1: resolved idx, native s3://, and materialized "
                                "local .idx are disabled). Visus often reports empty content when the idx URL is "
                                "wrong, truncated, or when the gateway binding cannot fetch that object. "
                                "Unset DARKMATTER_HTTP_EXPLICIT_NO_FALLBACK to allow fallbacks again, or fix the "
                                "HTTPS idx URL and gateway credentials."
                            ) from base_err
                        raise RuntimeError(
                            "OpenVisus could not load scene data from the linked HTTPS idx (empty content is typical "
                            "for gateway query-string URLs). For local `bokeh serve`, cd to the folder with your "
                            "materialized .idx and ensure ARCO bin files exist where (filename_template) points "
                            f"(often ./{mid_file}/ or a subdirectory named for the acquisition next to the idx). "
                            "Or start SCLib FastAPI and set SCLIB_DATASET_URL=http://127.0.0.1:5001 "
                            "(openvisus-resolved-idx)."
                        ) from base_err
                    print(
                        f"[DarkMatter][DEBUG] LoadDataset input (non-HTTPS or last resort)="
                        f"{_redact_url_secrets(str(idx_for_read))}"
                    )
                    self.scene_data = read_openvisus_field(idx_for_read)

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
        self.notification_div.text = f"<div style='color:{color}; font-weight:600;'>{text}</div>"
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

    def toggle_loading_spinner(self, state):
        self.loading_dataset_spinner.visible = state
        self.loading_dataset_spinner.text = "Loading dataset..." if state else ""

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

    runtime_info_section = row(app_state.loading_dataset_spinner, app_state.app_info_text)
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
        app_state.toggle_loading_spinner(True)
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
        input_event,
        event_controls,
        multichoice_detectors,
        checkbox_toggle_detectors,
        channels_grid,
        app_state.event_metadata_widget,
        app_state.notification_div,
        runtime_info_section,
        width=430,
    )
    header_banner = create_header_banner(
        dataset_name=name if name else "",
        dashboard_type="Nexus DM Dashboard",
    )
    main_layout = row(sidebar, app_state.fig, sizing_mode="stretch_both")
    curdoc().add_root(column(header_banner, s3_auth_panel, main_layout, sizing_mode="stretch_both"))
    if select_scene.value:
        update_events(select_scene.value)


main()
atexit.register(cleanup_mongodb)

# Test locally:
# bokeh serve darkmatter.py --port 8058 --allow-websocket-origin=localhost:8058 --args "/Users/amygooch/GIT/SCI/DATA/07180808_1558_F0001"

