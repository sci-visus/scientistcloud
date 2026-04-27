import matplotlib.colors as mcolors
import numpy as np
import sys
from typing import DefaultDict, List
import os
import atexit
from collections import defaultdict
import csv
from bisect import bisect_left
from datetime import datetime, timezone

import OpenVisus as ov
from urllib.parse import parse_qs
from bokeh.io import curdoc
from bokeh.models.widgets import Div
from bokeh.plotting import figure
from bokeh.layouts import row, column, gridplot
from bokeh.models import Button, AutocompleteInput, MultiChoice, Checkbox, CustomJS
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


def derive_dataset_from_s3_uri(s3_uri: str):
    uri = str(s3_uri or "").strip()
    if not uri.startswith("s3://"):
        return None

    if uri.endswith("/"):
        uri = uri[:-1]

    if uri.endswith(".idx"):
        idx_uri = uri
        base_uri = uri[:-4]
    else:
        mid_name = uri.split("/")[-1]
        base_uri = f"{uri}/{mid_name}"
        idx_uri = f"{base_uri}.idx"

    mid_file = base_uri.split("/")[-1]
    return {
        "mode": "s3_explicit",
        "mid_file": mid_file,
        "idx_uri": idx_uri,
        "txt_uri": f"{base_uri}.txt",
        "csv_uri": f"{base_uri}.csv",
    }


def derive_dataset_from_local_dir(dataset_dir: str):
    path = os.path.abspath(str(dataset_dir or "").strip())
    if not os.path.isdir(path):
        return None

    mid_file = os.path.basename(path.rstrip("/"))
    idx_path = os.path.join(path, f"{mid_file}.idx")
    txt_path = os.path.join(path, f"{mid_file}.txt")
    csv_path = os.path.join(path, f"{mid_file}.csv")
    if not os.path.exists(idx_path):
        return None

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


def download_s3_uri_to_file(s3_uri: str, dst: str):
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key:
        raise RuntimeError(f"Invalid s3 uri: {s3_uri}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    bucket = get_aws_bucket()
    default_bucket_name = getattr(bucket, "name", None)

    if default_bucket_name and bucket_name == default_bucket_name:
        bucket.download_file(key, dst)
        return

    # Fallback for cross-bucket/object access using the underlying client.
    bucket.meta.client.download_file(bucket_name, key, dst)


def read_s3_text_lines(s3_uri: str) -> List[str]:
    bucket_name, key = parse_s3_uri(s3_uri)
    if not bucket_name or not key:
        raise RuntimeError(f"Invalid s3 uri: {s3_uri}")

    bucket = get_aws_bucket()
    default_bucket_name = getattr(bucket, "name", None)

    if default_bucket_name and bucket_name == default_bucket_name:
        obj = bucket.Object(key)
        body = obj.get()["Body"].read().decode("utf-8")
        return body.splitlines()

    resp = bucket.meta.client.get_object(Bucket=bucket_name, Key=key)
    body = resp["Body"].read().decode("utf-8")
    return body.splitlines()


def download_processed_files(midfile: str):
    """
    Download processed files from storage (idx, channel metadata, event metadata)
    -----------------------------------------------------------------------------
    Parameters
    ----------
    file(str): the mid file to download in the the format 07180808_1558_F0001
    """
    s3 = get_aws_bucket()

    filenames = [f"{midfile}.idx", f"0000.bin",
                 f"{midfile}.txt", f"{midfile}.csv"]
    download_files = [
        os.path.join(PREFIX, midfile, filenames[0]),
        os.path.join(PREFIX, midfile, filenames[1]),
        os.path.join(PREFIX, midfile, filenames[2]),
        os.path.join(PREFIX, midfile, filenames[3]),
    ]

    for i, file in enumerate(download_files):
        dst = os.path.join(FILES_VOLUME, midfile, filenames[i])
        if filenames[i].split(".")[1] == "bin":
            dst = os.path.join(FILES_VOLUME, midfile, midfile, filenames[i])

        if not os.path.exists(dst):
            if check_if_key_exists(file, True):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                s3.download_file(file, dst)
            else:
                raise FileNotFoundError(f"{midfile} not in storage")


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
                idx_for_read = resolve_local_idx_path(self.runtime_dataset["idx_path"], mid_file)
                if idx_for_read != self.runtime_dataset["idx_path"]:
                    print(f"[DarkMatter][DEBUG] fixed local idx filename_template -> {idx_for_read}")
                self.detector_to_channels = create_channel_metadata_map(
                    self.runtime_dataset["txt_path"]
                )
                self.event_to_metadata = create_event_metadata_map(
                    self.runtime_dataset["csv_path"]
                )
                self.scene_data = ov.LoadDataset(
                    idx_for_read
                ).read(field="data")
                arr = np.asarray(self.scene_data)
                print(
                    f"[DarkMatter][DEBUG] local scene_data dtype={arr.dtype} shape={arr.shape} "
                    f"min={np.nanmin(arr)} max={np.nanmax(arr)}"
                )
                print(
                    f"[DarkMatter][DEBUG] local channels={len(self.detector_to_channels)} "
                    f"events={len(self.event_to_metadata)}"
                )
                return

            if self.runtime_dataset["mode"] == "s3_explicit":
                # Load dataset directly from S3 idx URL so sidecar bin paths resolve from source.
                print(f"[DarkMatter][DEBUG] s3_explicit mid={mid_file}")
                print(f"[DarkMatter][DEBUG] idx_uri={self.runtime_dataset['idx_uri']}")
                print(f"[DarkMatter][DEBUG] txt_uri={self.runtime_dataset['txt_uri']}")
                print(f"[DarkMatter][DEBUG] csv_uri={self.runtime_dataset['csv_uri']}")
                self.scene_data = ov.LoadDataset(
                    self.runtime_dataset["idx_uri"]
                ).read(field="data")
                txt_lines = read_s3_text_lines(self.runtime_dataset["txt_uri"])
                csv_lines = read_s3_text_lines(self.runtime_dataset["csv_uri"])
                self.detector_to_channels = create_channel_metadata_map_from_lines(txt_lines)
                self.event_to_metadata = create_event_metadata_map_from_lines(csv_lines)
                arr = np.asarray(self.scene_data)
                print(
                    f"[DarkMatter][DEBUG] s3 scene_data dtype={arr.dtype} shape={arr.shape} "
                    f"min={np.nanmin(arr)} max={np.nanmax(arr)}"
                )
                print(
                    f"[DarkMatter][DEBUG] s3 txt_lines={len(txt_lines)} csv_lines={len(csv_lines)} "
                    f"channels={len(self.detector_to_channels)} events={len(self.event_to_metadata)}"
                )
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
        self.scene_data = ov.LoadDataset(
            os.path.join(FILES_VOLUME, mid_file, f"{mid_file}.idx")
        ).read(field="data")

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
            runtime_dataset = derive_dataset_from_s3_uri(arg)
        # Keep slac.py legacy behavior when arg is not an explicit local/s3 dataset.
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
                ds = derive_dataset_from_s3_uri(candidate)
            if ds is not None:
                runtime_dataset = ds
                runtime_remote_url = candidate
                print(
                    f"[DarkMatter][DEBUG] resolved runtime_dataset from init params: "
                    f"mode={ds['mode']} mid={ds['mid_file']}"
                )
                break

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
            app_state.send_notification(ERROR, str(exc))
            app_state.render_app_info_text(f"Failed to load {mid_file}")
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

    app_state.first_event_button.on_click(update_event_to_first)
    app_state.prev_event_button.on_click(update_event_to_prev)
    app_state.next_event_button.on_click(update_event_to_next)
    app_state.last_event_button.on_click(update_event_to_last)
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
    curdoc().add_root(column(header_banner, main_layout, sizing_mode="stretch_both"))
    if select_scene.value:
        update_events(select_scene.value)


main()
atexit.register(cleanup_mongodb)

# Test locally:
# bokeh serve darkmatter.py --port 8058 --allow-websocket-origin=localhost:8058 --args "/Users/amygooch/GIT/SCI/DATA/07180808_1558_F0001"
