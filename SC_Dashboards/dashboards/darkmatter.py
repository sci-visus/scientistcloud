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
import zlib
import requests
import time
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
    from SCLib_Dashboards import create_header_banner
except Exception:
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


def _valid_email_or_none(value):
    if not value:
        return None
    candidate = str(value).strip()
    if not candidate:
        return None
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", candidate):
        return candidate
    return None


def resolve_s3_url_via_api(
    s3_uri: str,
    access_key="",
    secret_key="",
    endpoint_url="",
    region_name="us-east-1",
    path_style=True,
    dataset_identifier=None,
    user_email=None,
    cache_credentials=False,
    use_cached_credentials=True,
):
    dataset_api_base = (
        os.getenv("SCLIB_DATASET_URL")
        or os.getenv("SCLIB_API_URL")
        or "http://sclib_fastapi:5001"
    ).rstrip("/")
    endpoint = f"{dataset_api_base}/api/v1/datasets/s3/presign"
    payload = {
        "s3_uri": s3_uri,
        "access_key_id": access_key or None,
        "secret_access_key": secret_key or None,
        "endpoint_url": endpoint_url or os.getenv("S3_ENDPOINT_URL", "") or None,
        "region_name": region_name or "us-east-1",
        "path_style": bool(path_style),
        "expires_in": 3600,
        "dataset_identifier": dataset_identifier,
        "user_email": _valid_email_or_none(user_email),
        "cache_credentials": bool(cache_credentials),
        "use_cached_credentials": bool(use_cached_credentials),
    }
    response = requests.post(endpoint, json=payload, timeout=20)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = response.text
        raise RuntimeError(detail or f"HTTP {response.status_code}")
    data = response.json()
    if not data.get("success") or not data.get("url"):
        raise RuntimeError(data.get("detail") or "Presign endpoint returned no URL")
    return data["url"]


def resolve_openvisus_idx_via_api(
    s3_uri: str,
    dataset_identifier: Optional[str] = None,
    user_email: Optional[str] = None,
    auth_override=None,
):
    dataset_api_base = (
        os.getenv("SCLIB_DATASET_URL")
        or os.getenv("SCLIB_API_URL")
        or "http://sclib_fastapi:5001"
    ).rstrip("/")
    endpoint = f"{dataset_api_base}/api/v1/datasets/s3/openvisus-resolved-idx"
    override = auth_override or {}
    payload = {
        "s3_uri": s3_uri,
        "dataset_identifier": dataset_identifier,
        "user_email": _valid_email_or_none(user_email),
        "access_key_id": override.get("aws_access_key_id", ""),
        "secret_access_key": override.get("aws_secret_access_key", ""),
        "endpoint_url": override.get("endpoint_url", "") or os.getenv("S3_ENDPOINT_URL", "") or None,
        "region_name": override.get("region_name", "us-east-1"),
        "path_style": True,
        "cache_credentials": bool(override.get("aws_access_key_id") and override.get("aws_secret_access_key")),
        "use_cached_credentials": True,
        "output_filename": "visus.idx",
    }
    last_detail = "Resolved idx endpoint returned no path"
    for _ in range(15):
        response = requests.post(endpoint, json=payload, timeout=30)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail")
            except Exception:
                detail = response.text
            raise RuntimeError(detail or f"HTTP {response.status_code}")
        data = response.json()
        resolved_idx_path = str(data.get("resolved_idx_path") or "").strip()
        resolved_idx_http_url = str(data.get("resolved_idx_http_url") or "").strip()
        status = str(data.get("status") or "").lower()
        if data.get("success") and resolved_idx_path:
            return resolved_idx_path, resolved_idx_http_url
        if status == "pending" and resolved_idx_path:
            time.sleep(1.0)
            continue
        last_detail = str(data.get("detail") or last_detail)
        break
    raise RuntimeError(last_detail)


def _read_filename_template_line(local_idx_path: str) -> str:
    """Return the filename_template line from a resolved visus.idx on disk (may be HTTPS URL)."""
    try:
        with open(local_idx_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [ln.rstrip("\n") for ln in f]
    except Exception:
        return ""
    for i, line in enumerate(lines):
        if line.strip() == "(filename_template)" and i + 1 < len(lines):
            return lines[i + 1].strip()
    return ""


def _s3_uri_first_block_bin(idx_s3_uri: str) -> str:
    """Map dataset idx s3:// URI to sibling 0000.bin under the same folder."""
    bucket, key = parse_s3_uri(idx_s3_uri)
    if not bucket or not key or "/" not in key:
        return ""
    parent = key.rsplit("/", 1)[0]
    return f"s3://{bucket}/{parent}/0000.bin"


def read_s3_object_range_bytes(s3_uri: str, byte_range: str, auth_override=None) -> Optional[bytes]:
    """
    Fetch the first matching byte span via S3 API (same credential discovery as read_s3_text_lines).
    byte_range example: 'bytes=0-4095'
    """
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key:
        return None

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
        return None

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
                resp = s3_client.get_object(
                    Bucket=bucket_name, Key=key, Range=byte_range
                )
                return resp["Body"].read()
            except Exception as exc:
                last_error = exc
                continue
    if last_error:
        raise last_error
    return None


def _darkmatter_sniff_zip_block_bytes(label: str, body: bytes) -> None:
    """
    visus idx often has default_compression(zip); .bin data is not a raw uint16 array.
    Try zlib/gzip/deflate on typical skips so logs distinguish compressed payloads from bad proxy reads.
    """
    if not body or len(body) < 2:
        return
    print(
        f"[DarkMatter][DIAG] {label} compression sniff: first8_hex={body[:8].hex()} "
        "(if idx uses zip compression, raw uint16 min/max above are not decoded samples)"
    )
    for skip in (0, 1, 2, 4, 8, 16, 32, 64, 128, 256):
        if skip >= len(body):
            break
        chunk = body[skip:]
        for wbits in (
            zlib.MAX_WBITS,  # zlib header (often starts with 78 xx)
            -zlib.MAX_WBITS,  # raw deflate
            zlib.MAX_WBITS | 16,  # gzip wrapper (31)
            32,  # zlib or gzip header autodetect (Python 3)
        ):
            try:
                dec = zlib.decompress(chunk, wbits)
                if len(dec) < 2:
                    continue
                u2 = np.frombuffer(dec[: len(dec) - (len(dec) % 2)], dtype=np.uint16)
                print(
                    f"[DarkMatter][DIAG] {label} zlib decompress ok: skip={skip} wbits={wbits} "
                    f"out_len={len(dec)} uint16_min={int(u2.min())} uint16_max={int(u2.max())} "
                    f"uint16_nonzero={int(np.count_nonzero(u2))}"
                )
                return
            except Exception:
                continue
    print(f"[DarkMatter][DIAG] {label} zlib sniff: no decompress succeeded (per-block layout may need larger Range)")


def diagnose_darkmatter_zero_scene(
    idx_s3_uri: str,
    resolved_local_idx_path: str,
    auth_override,
) -> None:
    """
    When OpenVisus scene_data is all zeros, compare:
    (1) HTTP GET of block 0 via the same object-proxy URL as in resolved visus.idx
    (2) S3 get_object Range on 0000.bin

    If (2) is non-zero but (1) fails or is zero → proxy/OpenVisus HTTP path.
    If both are zero → object may be empty at head (or wrong key).
    Set DARKMATTER_DISABLE_ZERO_DIAG=1 to skip.
    """
    if str(os.getenv("DARKMATTER_DISABLE_ZERO_DIAG", "") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return

    tpl = ""
    if resolved_local_idx_path and os.path.isfile(resolved_local_idx_path):
        tpl = _read_filename_template_line(resolved_local_idx_path)

    sniff_body: Optional[bytes] = None

    if tpl.startswith("http://") or tpl.startswith("https://"):
        bin_url = tpl.replace("%04x", "0000").replace("%04X", "0000")
        try:
            r = requests.get(
                bin_url,
                headers={"Range": "bytes=0-4095"},
                timeout=35,
            )
            body = r.content
            sniff_body = body
            aligned = body[: len(body) - (len(body) % 2)]
            u16 = np.frombuffer(aligned, dtype=np.uint16) if len(aligned) >= 2 else np.array([], dtype=np.uint16)
            print(
                "[DarkMatter][DIAG] object-proxy bin 0000 (HTTP Range): "
                f"status={r.status_code} nbytes={len(body)} "
                f"content_range={r.headers.get('Content-Range')!r} "
                f"uint16_min={int(u16.min()) if u16.size else 'n/a'} "
                f"uint16_max={int(u16.max()) if u16.size else 'n/a'} "
                f"uint16_nonzero={int(np.count_nonzero(u16)) if u16.size else 0} "
                f"head_hex={body[:32].hex()}"
            )
        except Exception as exc:
            print(f"[DarkMatter][DIAG] object-proxy HTTP probe failed: {exc}")

    if idx_s3_uri.startswith("s3://"):
        bin_uri = _s3_uri_first_block_bin(idx_s3_uri)
        if bin_uri:
            try:
                raw = read_s3_object_range_bytes(
                    bin_uri, "bytes=0-4095", auth_override=auth_override
                )
                if raw is None:
                    print("[DarkMatter][DIAG] S3 direct probe skipped (no credentials)")
                else:
                    if sniff_body is None:
                        sniff_body = raw
                    aligned = raw[: len(raw) - (len(raw) % 2)]
                    u16 = (
                        np.frombuffer(aligned, dtype=np.uint16)
                        if len(aligned) >= 2
                        else np.array([], dtype=np.uint16)
                    )
                    print(
                        "[DarkMatter][DIAG] S3 direct bin 0000 (Range): "
                        f"nbytes={len(raw)} uri={bin_uri} "
                        f"uint16_min={int(u16.min()) if u16.size else 'n/a'} "
                        f"uint16_max={int(u16.max()) if u16.size else 'n/a'} "
                        f"uint16_nonzero={int(np.count_nonzero(u16)) if u16.size else 0} "
                        f"head_hex={raw[:32].hex()}"
                    )
            except Exception as exc:
                print(f"[DarkMatter][DIAG] S3 direct probe failed: {exc}")

    if sniff_body:
        _darkmatter_sniff_zip_block_bytes("bin0000 first 4KiB", sniff_body)


def read_openvisus_field(idx_url_or_path: str, field: str = "data"):
    """
    Read an OpenVisus field using full dataset resolution when the binding supports it
    (same pattern as 3DVTK: getMaxResolution + read(max_resolution=...)). Without that,
    multiresolution idx can yield an all-zero coarse slice from read(field=...) alone.
    """
    db = ov.LoadDataset(idx_url_or_path)
    mr = None
    try:
        gmr = getattr(db, "getMaxResolution", None)
        if callable(gmr):
            raw = gmr()
            mr = int(raw) if raw is not None else None
    except Exception:
        mr = None
    if mr is not None:
        for kwargs in (
            {"field": field, "max_resolution": mr},
            {"max_resolution": mr, "field": field},
        ):
            try:
                print(f"[DarkMatter][DEBUG] OpenVisus read using max_resolution={mr}")
                return db.read(**kwargs)
            except TypeError:
                continue
    return db.read(field=field)


def derive_dataset_from_remote_uri(remote_uri: str):
    return parse_remote_dataset_uri(remote_uri)


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

    for field in ("source_path", "google_drive_link"):
        candidate = str(doc.get(field) or "").strip()
        if not candidate:
            continue
        ds = derive_dataset_from_local_dir(candidate)
        if ds is None:
            ds = derive_dataset_from_remote_uri(candidate)
        if ds is not None:
            if auth_override.get("aws_access_key_id") and auth_override.get("aws_secret_access_key"):
                ds["auth_override"] = auth_override
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
            return None
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


def resolve_local_idx_path(idx_path: str, mid_file: str) -> str:
    """
    Fix local idx filename_template when it incorrectly duplicates the dataset folder.
    Example buggy template: ./07180808_1558_F0001/%04x.bin while 0000.bin is in same folder as .idx
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
    flat_bin = os.path.join(os.path.dirname(idx_path), "0000.bin")
    nested_bin = os.path.join(os.path.dirname(idx_path), mid_file, "0000.bin")

    needs_fix = template == f"./{mid_file}/%04x.bin" and os.path.exists(flat_bin) and not os.path.exists(nested_bin)
    if not needs_fix:
        return idx_path

    fixed_lines = list(lines)
    dataset_dir = os.path.dirname(idx_path)
    fixed_lines[template_idx] = f"{dataset_dir}/%04x.bin\n"

    fixed_path = os.path.join(os.path.dirname(idx_path), f"{mid_file}.resolved.idx")
    with open(fixed_path, "w") as f:
        f.writelines(fixed_lines)
    return fixed_path


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


def materialize_http_idx_for_openvisus(idx_url: str, mid_file: str) -> str:
    """
    Build a local idx file with an authenticated HTTP filename_template.
    This ensures OpenVisus block reads (%04x.bin) use the same query credentials.
    """
    try:
        response = requests.get(idx_url, timeout=20)
        response.raise_for_status()
        lines = [f"{line}\n" for line in response.text.splitlines()]
    except Exception as http_idx_exc:
        # Some gateways deny direct HTTP idx download even with query keys.
        # Fall back to S3 API read using provided runtime credentials.
        s3_idx_uri = http_object_url_to_s3_uri(idx_url)
        if not s3_idx_uri:
            raise RuntimeError(
                f"HTTP idx fetch failed and URL could not be converted to s3:// URI: {idx_url}"
            ) from http_idx_exc
        print(
            "[DarkMatter][WARN] HTTP idx fetch failed; attempting S3 fallback for idx materialization: "
            f"{http_idx_exc}"
        )
        idx_lines = read_s3_text_lines(s3_idx_uri)
        lines = [f"{line}\n" for line in idx_lines]

    parts = urlsplit(idx_url)
    idx_path = (parts.path or "").rstrip("/")
    base_path = idx_path[:-4] if idx_path.lower().endswith(".idx") else idx_path
    parent_path = base_path.rsplit("/", 1)[0] if "/" in base_path else base_path

    def _build_candidate(path_value: str) -> str:
        return urlunsplit((parts.scheme, parts.netloc, path_value, parts.query, parts.fragment))

    # Try both common layouts for 0000.bin relative to idx.
    template_candidates = [
        _build_candidate(f"{base_path}/%04x.bin"),
        _build_candidate(f"{parent_path}/%04x.bin"),
    ]
    s3_template_candidates = [
        http_object_url_to_s3_uri(_build_candidate(f"{base_path}/%04x.bin")),
        http_object_url_to_s3_uri(_build_candidate(f"{parent_path}/%04x.bin")),
    ]

    # Prefer resolving the original idx filename_template when present.
    source_template = ""
    template_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == "(filename_template)" and i + 1 < len(lines):
            template_idx = i + 1
            source_template = lines[template_idx].strip()
            break

    if source_template and "%04x" in source_template:
        if source_template.startswith("http://") or source_template.startswith("https://"):
            src_parts = urlsplit(source_template)
            src_query = src_parts.query or parts.query
            template_candidates.insert(
                0,
                urlunsplit((src_parts.scheme, src_parts.netloc, src_parts.path, src_query, src_parts.fragment)),
            )
            s3_from_http = http_object_url_to_s3_uri(
                urlunsplit((src_parts.scheme, src_parts.netloc, src_parts.path, "", src_parts.fragment))
            )
            if s3_from_http:
                s3_template_candidates.insert(0, s3_from_http)
        elif source_template.startswith("s3://"):
            gateway_base = f"{parts.scheme}://{parts.netloc}"
            as_http = s3_uri_to_http_url(source_template, gateway_base)
            if as_http:
                if parts.query:
                    src_http_parts = urlsplit(as_http)
                    as_http = urlunsplit(
                        (
                            src_http_parts.scheme,
                            src_http_parts.netloc,
                            src_http_parts.path,
                            parts.query,
                            src_http_parts.fragment,
                        )
                    )
                template_candidates.insert(0, as_http)
            s3_template_candidates.insert(0, source_template)
        else:
            relative = source_template.lstrip("./")
            rel_path = f"{parent_path}/{relative}" if relative else f"{parent_path}/%04x.bin"
            template_candidates.insert(0, _build_candidate(rel_path))
            s3_rel = http_object_url_to_s3_uri(_build_candidate(rel_path))
            if s3_rel:
                s3_template_candidates.insert(0, s3_rel)

    selected_template = template_candidates[0]
    for candidate in template_candidates:
        probe = candidate.replace("%04x", "0000")
        if http_url_exists(probe):
            selected_template = candidate
            break
    else:
        for s3_candidate in s3_template_candidates:
            if not s3_candidate:
                continue
            probe = s3_candidate.replace("%04x", "0000")
            if s3_key_exists(probe):
                selected_template = s3_candidate
                break

    if template_idx >= 0:
        lines[template_idx] = f"{selected_template}\n"
    else:
        lines.extend(["(filename_template)\n", f"{selected_template}\n"])

    os.makedirs(FILES_VOLUME, exist_ok=True)
    local_idx_path = os.path.join(FILES_VOLUME, f"{mid_file}.http.resolved.idx")
    with open(local_idx_path, "w") as fp:
        fp.writelines(lines)
    return local_idx_path


def s3_key_exists(s3_uri: str) -> bool:
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key:
        return False

    load_dotenv()
    endpoint_url = os.getenv("ENDPOINT_URL")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    config = Config(signature_version="s3v4")
    s3_client = Session().client(
        "s3",
        endpoint_url=endpoint_url,
        config=config,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    try:
        s3_client.head_object(Bucket=bucket_name, Key=key)
        return True
    except Exception:
        return False


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


def http_url_exists(url: str) -> bool:
    if not url:
        return False
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        if resp.status_code < 400:
            return True
        # Some gateways block HEAD; fallback to lightweight GET.
        resp = requests.get(url, timeout=10, stream=True)
        return resp.status_code < 400
    except Exception:
        return False


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
                idx_for_read = self.runtime_dataset["idx_path"]
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
                # For HTTP datasets we may rewrite idx locally so block URLs carry auth query.
                print(f"[DarkMatter][DEBUG] {self.runtime_dataset['mode']} mid={mid_file}")
                print(f"[DarkMatter][DEBUG] idx_uri={self.runtime_dataset['idx_uri']}")
                print(f"[DarkMatter][DEBUG] txt_uri={self.runtime_dataset['txt_uri']}")
                print(f"[DarkMatter][DEBUG] csv_uri={self.runtime_dataset['csv_uri']}")
                idx_for_read = self.runtime_dataset["idx_uri"]
                if self.runtime_dataset["mode"] == "http_explicit" and not self.s3_auth_override:
                    idx_parts = urlsplit(self.runtime_dataset["idx_uri"])
                    idx_query = parse_qs(idx_parts.query or "")
                    access_from_query = (idx_query.get("access_key", [""])[0] or "").strip()
                    secret_from_query = (idx_query.get("secret_key", [""])[0] or "").strip()
                    endpoint_from_query = f"{idx_parts.scheme}://{idx_parts.netloc}" if idx_parts.scheme and idx_parts.netloc else ""
                    if access_from_query and secret_from_query:
                        self.set_s3_auth_override(endpoint_from_query, access_from_query, secret_from_query)
                        print("[DarkMatter][DEBUG] loaded S3 auth override from idx URL query credentials")
                dataset_identifier = None
                if uuid:
                    uuid_str = str(uuid).strip().lower()
                    if not (uuid_str.startswith("s3://") or uuid_str.startswith("http://") or uuid_str.startswith("https://")):
                        dataset_identifier = uuid

                # Stable server pattern: ask backend to generate/store resolved idx at converted/<uuid>/visus.idx.
                s3_idx_for_resolve = (
                    self.runtime_dataset["idx_uri"]
                    if self.runtime_dataset["idx_uri"].startswith("s3://")
                    else http_object_url_to_s3_uri(self.runtime_dataset["idx_uri"])
                )
                resolved_local_idx_path = ""
                if s3_idx_for_resolve:
                    try:
                        resolved_idx_path, resolved_idx_http_url = resolve_openvisus_idx_via_api(
                            s3_uri=s3_idx_for_resolve,
                            dataset_identifier=dataset_identifier,
                            user_email=user_email,
                            auth_override=self.s3_auth_override,
                        )
                        resolved_local_idx_path = str(resolved_idx_path or "").strip()
                        preferred = str(resolved_idx_http_url or "").strip()
                        # Dataset-relative ./%04x.bin loads work locally because OpenVisus opens the idx
                        # from disk and reads bins beside it. Here, resolved visus.idx still lists full
                        # HTTPS object-proxy URLs in (filename_template)—bins are remote either way.
                        # Prefer the local file path when mounted (e.g. /mnt/visus_datasets/converted/.../visus.idx)
                        # so LoadDataset uses the same filesystem idx semantics as a working local workflow;
                        # object-proxy Range reads are unchanged (they come from the template lines).
                        # Set DARKMATTER_PREFER_HTTPS_RESOLVED_IDX=1 to use the HTTPS idx URL first instead.
                        prefer_https_idx = str(
                            os.getenv("DARKMATTER_PREFER_HTTPS_RESOLVED_IDX", "0")
                        ).strip().lower() in ("1", "true", "yes", "on")
                        local_idx_ok = bool(
                            resolved_local_idx_path
                            and os.path.isfile(resolved_local_idx_path)
                        )
                        if prefer_https_idx and preferred:
                            idx_for_read = preferred
                        elif local_idx_ok:
                            idx_for_read = resolved_local_idx_path
                        elif preferred:
                            idx_for_read = preferred
                        else:
                            idx_for_read = resolved_local_idx_path
                        print(
                            f"[DarkMatter][DEBUG] using resolved idx from API: {idx_for_read} "
                            f"(local={resolved_local_idx_path}, prefer_https_idx={prefer_https_idx})"
                        )
                    except Exception as resolved_idx_exc:
                        print(f"[DarkMatter][WARN] openvisus resolved idx unavailable, using direct URL: {resolved_idx_exc}")

                # Preserve HTTPS datasets as HTTPS.
                # For s3:// datasets, build HTTPS URL with inline credentials so
                # OpenVisus can use the same auth context for bin reads.
                s3_idx_uri = self.runtime_dataset["idx_uri"] if self.runtime_dataset["idx_uri"].startswith("s3://") else ""
                if s3_idx_uri and idx_for_read == self.runtime_dataset["idx_uri"]:
                    override = self.s3_auth_override or {}
                    gateway_base = (
                        override.get("endpoint_url")
                        or get_s3_http_gateway_base()
                    )
                    http_idx = s3_uri_to_http_url(s3_idx_uri, gateway_base) if gateway_base else ""
                    if http_idx:
                        idx_for_read = with_query_params(
                            http_idx,
                            {
                                "access_key": override.get("aws_access_key_id", ""),
                                "secret_key": override.get("aws_secret_access_key", ""),
                                "region_name": override.get("region_name", "us-east-1"),
                            },
                        )
                        print("[DarkMatter][DEBUG] using HTTPS idx URL with inline credentials for OpenVisus")
                    try:
                        signed_idx = resolve_s3_url_via_api(
                            s3_idx_uri,
                            access_key=override.get("aws_access_key_id", ""),
                            secret_key=override.get("aws_secret_access_key", ""),
                            endpoint_url=override.get("endpoint_url", ""),
                            region_name=override.get("region_name", "us-east-1"),
                            path_style=True,
                            dataset_identifier=dataset_identifier,
                            user_email=user_email,
                            cache_credentials=bool(override.get("aws_access_key_id") and override.get("aws_secret_access_key")),
                            use_cached_credentials=True,
                        )
                        idx_for_read = signed_idx
                        print("[DarkMatter][DEBUG] using presigned URL for OpenVisus dataset load")
                    except Exception as presign_exc:
                        print(f"[DarkMatter][DEBUG] dataset presign unavailable, using direct URL: {presign_exc}")

                if self.runtime_dataset["mode"] == "http_explicit" and idx_for_read == self.runtime_dataset["idx_uri"]:
                    # Primary path must stay full HTTPS idx URL (with query keys).
                    idx_for_read = self.runtime_dataset["idx_uri"]
                    print(f"[DarkMatter][DEBUG] using HTTPS idx URL for OpenVisus: {idx_for_read}")

                print(f"[DarkMatter][DEBUG] LoadDataset input={idx_for_read}")
                self.scene_data = read_openvisus_field(idx_for_read)
                # If we used the server-generated resolved idx (local path and/or HTTPS serve URL),
                # optionally retry with presigned / gateway idx when the first load is all zeros.
                # Default is OFF so we can observe pure object-proxy behavior first.
                enable_cmip6_fallback = str(
                    os.getenv("DARKMATTER_ENABLE_CMIP6_FALLBACK", "0")
                ).strip().lower() in ("1", "true", "yes", "on")
                if (
                    self.runtime_dataset["mode"] == "s3_explicit"
                    and resolved_local_idx_path
                ):
                    try:
                        arr0 = np.asarray(self.scene_data)
                        if (
                            arr0.size
                            and int(np.count_nonzero(arr0)) == 0
                            and float(np.nanmin(arr0)) == 0.0
                            and float(np.nanmax(arr0)) == 0.0
                        ):
                            override = self.s3_auth_override or {}
                            s3_idx_uri = (
                                self.runtime_dataset["idx_uri"]
                                if self.runtime_dataset["idx_uri"].startswith("s3://")
                                else ""
                            )
                            if s3_idx_uri and not enable_cmip6_fallback:
                                print(
                                    "[DarkMatter][WARN] resolved idx load returned all zeros; "
                                    "CMIP6 fallback is DISABLED (DARKMATTER_ENABLE_CMIP6_FALLBACK=0). "
                                    "Keeping object-proxy result for this test."
                                )
                            elif s3_idx_uri:
                                print(
                                    "[DarkMatter][WARN] resolved idx load returned all zeros "
                                    f"(LoadDataset input was {'HTTP' if str(idx_for_read).startswith(('http://', 'https://')) else 'local'}); "
                                    "retrying OpenVisus with presigned HTTPS idx URL (CMIP6-style fallback)"
                                )
                                try:
                                    print(
                                        f"[DarkMatter][DEBUG] fallback candidate source s3_idx_uri={s3_idx_uri}"
                                    )
                                    signed_idx = resolve_s3_url_via_api(
                                        s3_idx_uri,
                                        access_key=override.get("aws_access_key_id", ""),
                                        secret_key=override.get("aws_secret_access_key", ""),
                                        endpoint_url=override.get("endpoint_url", ""),
                                        region_name=override.get("region_name", "us-east-1"),
                                        path_style=True,
                                        dataset_identifier=dataset_identifier,
                                        user_email=user_email,
                                        cache_credentials=bool(
                                            override.get("aws_access_key_id")
                                            and override.get("aws_secret_access_key")
                                        ),
                                        use_cached_credentials=True,
                                    )
                                    print(f"[DarkMatter][DEBUG] LoadDataset fallback (presign) input={signed_idx}")
                                    print(
                                        f"[DarkMatter][DEBUG] fallback presign endpoint={urlsplit(signed_idx).scheme}://{urlsplit(signed_idx).netloc}"
                                    )
                                    self.scene_data = read_openvisus_field(signed_idx)
                                except Exception as presign_fb_exc:
                                    gateway_base = (
                                        override.get("endpoint_url")
                                        or get_s3_http_gateway_base()
                                    )
                                    http_idx = (
                                        s3_uri_to_http_url(s3_idx_uri, gateway_base)
                                        if gateway_base
                                        else ""
                                    )
                                    if not http_idx:
                                        raise
                                    http_idx = with_query_params(
                                        http_idx,
                                        {
                                            "access_key": override.get("aws_access_key_id", ""),
                                            "secret_key": override.get("aws_secret_access_key", ""),
                                            "region_name": override.get("region_name", "us-east-1"),
                                        },
                                    )
                                    print(
                                        f"[DarkMatter][DEBUG] presign fallback failed ({presign_fb_exc}); "
                                        f"LoadDataset fallback (inline gateway) input={http_idx}"
                                    )
                                    print(
                                        f"[DarkMatter][DEBUG] fallback inline endpoint={urlsplit(http_idx).scheme}://{urlsplit(http_idx).netloc}"
                                    )
                                    self.scene_data = read_openvisus_field(http_idx)
                    except Exception as fallback_exc:
                        print(
                            f"[DarkMatter][WARN] OpenVisus CMIP6-style fallback failed: {fallback_exc}"
                        )
                if self.runtime_dataset["mode"] == "http_explicit":
                    try:
                        txt_lines = read_text_lines_from_url(self.runtime_dataset["txt_uri"])
                        csv_lines = read_text_lines_from_url(self.runtime_dataset["csv_uri"])
                    except Exception as http_sidecar_exc:
                        print(f"[DarkMatter][WARN] HTTP sidecar fetch failed; attempting S3 fallback: {http_sidecar_exc}")
                        txt_s3_uri = http_object_url_to_s3_uri(self.runtime_dataset["txt_uri"])
                        csv_s3_uri = http_object_url_to_s3_uri(self.runtime_dataset["csv_uri"])
                        if not txt_s3_uri or not csv_s3_uri:
                            raise RuntimeError(
                                "DarkMatter requires .txt/.csv metadata files, and HTTP sidecar URLs "
                                "could not be converted to s3:// URIs for fallback reads."
                            ) from http_sidecar_exc
                        txt_lines = read_s3_text_lines(txt_s3_uri, auth_override=self.s3_auth_override)
                        csv_lines = read_s3_text_lines(csv_s3_uri, auth_override=self.s3_auth_override)
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
                if (
                    self.runtime_dataset["mode"] == "s3_explicit"
                    and arr.size
                    and nonzero_count == 0
                ):
                    diagnose_darkmatter_zero_scene(
                        self.runtime_dataset["idx_uri"],
                        resolved_local_idx_path,
                        self.s3_auth_override,
                    )
                # All-zero scene_data can be legitimate or indicate bin read issues; do not
                # raise (that triggered a misleading S3 credential UI). Logs carry the signal.
                if self.runtime_dataset["mode"] == "s3_explicit" and arr.size and arr_min == 0 and arr_max == 0:
                    print(
                        "[DarkMatter][WARN] scene_data min=0 max=0 for s3_explicit; "
                        "continuing (bins use resolved idx / object-proxy; verify OpenVisus load if plot is empty)."
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
            if ds is None:
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
