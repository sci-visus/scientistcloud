import os
import sys
import re
from urllib.parse import parse_qs, urlsplit, urlunsplit
from bokeh.io import curdoc
from bokeh.models.widgets import Div
from bokeh.layouts import column, row
from bokeh.models import CustomJS, Button, TextInput, PasswordInput
from bokeh.events import ButtonClick
from dotenv import load_dotenv
import requests
import time

# Import utility modules
from utils_bokeh_dashboard import initialize_dashboard
from utils_bokeh_mongodb import cleanup_mongodb
from utils_bokeh_auth import authenticate_user
from utils_bokeh_param import parse_url_parameters, setup_directory_paths

# Import header banner from SCLib_Dashboards
try:
    from SCLib_Dashboards import create_header_banner
except ImportError:
    # Fallback if SCLib_Dashboards not available
    def create_header_banner(dataset_name="", dashboard_type="Dashboard"):
        from bokeh.models import Div
        sc_blue = "#4E477F"
        title_text = f"ScientistCloud | {dashboard_type}: {dataset_name}" if dataset_name else f"ScientistCloud | {dashboard_type}"
        return Div(
            text=f'<div class="dashboard-header-banner" style="background-color: {sc_blue}; padding: 10px 20px; display: flex; align-items: center; border-radius: 0;"><img src="https://scientistcloud.com/portal/assets/images/scientistCloudLogo_noText.png" style="height: 40px; margin-right: 15px;"><span style="color: white; font-family: sans-serif; font-size: 1.5em; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">{title_text}</span></div>',
            sizing_mode="stretch_width",
            styles={"width": "100vw", "max-width": "100vw", "margin": "0", "padding": "0", "position": "relative", "background-color": sc_blue, "border-bottom": "3px solid #75c0de", "margin-bottom": "20px"}
        )


# Run it via: 
#    bokeh serve Docker/bokeh/dataExplorer.py --port 5032 --allow-websocket-origin=localhost:5032
#  panel serve Docker/bokeh/dataExplorer.py --port 5032 --allow-websocket-origin=localhost:5032

# Initialize dashboard using utility functions
# Check if running with URL arguments - if no args, we're in local mode
from bokeh.plotting import curdoc
doc = curdoc()
request = doc.session_context.request if hasattr(doc, 'session_context') and doc.session_context else None

# Debug logging for request arguments
print(f"🔍 DEBUG: request = {request}")
request_args = {}
if request:
    print(f"🔍 DEBUG: request.arguments = {request.arguments}")
    print(f"🔍 DEBUG: request.arguments type = {type(request.arguments)}")
    if hasattr(request, 'query_string'):
        print(f"🔍 DEBUG: request.query_string = {request.query_string}")
    if hasattr(request, 'url'):
        print(f"🔍 DEBUG: request.url = {request.url}")
    
    # Try to get arguments from request.arguments first
    if hasattr(request, 'arguments') and request.arguments:
        request_args = request.arguments
    # If arguments is empty, try to parse from query_string or url
    elif hasattr(request, 'query_string') and request.query_string:
        print(f"🔍 DEBUG: Parsing query_string: {request.query_string}")
        request_args = parse_qs(request.query_string)
        # Convert values from lists to single values (Bokeh format)
        for key in list(request_args.keys()):
            if isinstance(request_args[key], list) and len(request_args[key]) > 0:
                request_args[key] = [request_args[key][0].decode('utf-8') if isinstance(request_args[key][0], bytes) else request_args[key][0]]
    elif hasattr(request, 'url') and request.url:
        print(f"🔍 DEBUG: Parsing URL: {request.url}")
        from urllib.parse import urlparse
        parsed_url = urlparse(request.url)
        if parsed_url.query:
            request_args = parse_qs(parsed_url.query)
            # Convert values from lists to single values (Bokeh format)
            for key in list(request_args.keys()):
                if isinstance(request_args[key], list) and len(request_args[key]) > 0:
                    request_args[key] = [request_args[key][0].decode('utf-8') if isinstance(request_args[key][0], bytes) else request_args[key][0]]

has_args = request and len(request_args) > 0
print(f"🔍 DEBUG: has_args = {has_args}, request_args = {request_args}")
DATA_IS_LOCAL = not has_args
local_base_dir = f'/Users/amygooch/GIT/SCI/DATA/turbine/turbin_visus'


# Set environment variables and paths
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"
if not has_args:
    sys.path.insert(0, '/Users/amygooch/GIT/VisusDataPortalPrivate/openvisuspy/src')
else:
    sys.path.insert(0, '/home/ViSOAR/dataportal/openvisuspy/src')
# Load environment variables
deploy_server = os.getenv('DEPLOY_SERVER')

def is_s3_uri(url):
    return isinstance(url, str) and url.strip().lower().startswith("s3://")

def is_remote_link(url):
    if not isinstance(url, str):
        return False
    value = url.strip().lower()
    return value.startswith("s3://") or value.startswith("http://") or value.startswith("https://") or value.startswith("pelican://")

def normalize_remote_dataset_url(url):
    if not isinstance(url, str):
        return url

    candidate = url.strip()
    if not candidate:
        return candidate

    lower = candidate.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return candidate
    parts = urlsplit(candidate)
    # Preserve any explicitly provided IDX filename (do not rewrite it to visus.idx).
    provided_name = os.path.basename(parts.path or "").strip()
    if re.search(r"\.idx$", provided_name, re.IGNORECASE):
        return candidate

    # Only guess visus.idx when no idx filename was provided.
    normalized_path = (parts.path or "").rstrip("/") + "/visus.idx"
    normalized = urlunsplit((parts.scheme, parts.netloc, normalized_path, parts.query, parts.fragment))
    print(f"[OpenVisusSlice][DEBUG] normalized remote URL to visus.idx: {normalized}")
    return normalized

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

def resolve_s3_dataset_url_via_api(
    s3_uri,
    access_key,
    secret_key,
    endpoint_url="",
    region_name="us-east-1",
    path_style=True,
    dataset_identifier=None,
    user_email=None,
    cache_credentials=True,
    use_cached_credentials=True
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
        "endpoint_url": endpoint_url or None,
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
    return data["url"], data


def http_object_url_to_s3_uri(url: str) -> str:
    parts = urlsplit(str(url or "").strip())
    if parts.scheme not in ("http", "https"):
        return ""
    path_parts = [segment for segment in (parts.path or "").split("/") if segment]
    if len(path_parts) < 2:
        return ""
    bucket_name = path_parts[0]
    key = "/".join(path_parts[1:])
    return f"s3://{bucket_name}/{key}"


def resolve_openvisus_resolved_idx_via_api(
    *,
    dataset_identifier=None,
    s3_uri=None,
    user_email=None,
    access_key="",
    secret_key="",
    endpoint_url="",
    region_name="us-east-1",
    cache_credentials=True,
    use_cached_credentials=True,
):
    dataset_api_base = (
        os.getenv("SCLIB_DATASET_URL")
        or os.getenv("SCLIB_API_URL")
        or "http://sclib_fastapi:5001"
    ).rstrip("/")
    endpoint = f"{dataset_api_base}/api/v1/datasets/s3/openvisus-resolved-idx"
    payload = {
        "dataset_identifier": dataset_identifier,
        "s3_uri": s3_uri,
        "user_email": _valid_email_or_none(user_email),
        "access_key_id": access_key or None,
        "secret_access_key": secret_key or None,
        "endpoint_url": endpoint_url or None,
        "region_name": region_name or "us-east-1",
        "path_style": True,
        "cache_credentials": bool(cache_credentials),
        "use_cached_credentials": bool(use_cached_credentials),
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
        status = str(data.get("status") or "").lower()
        if data.get("success") and resolved_idx_path:
            return resolved_idx_path, data
        if status == "pending" and resolved_idx_path:
            time.sleep(1.0)
            continue
        last_detail = str(data.get("detail") or last_detail)
        break
    raise RuntimeError(last_detail)



if not has_args:
    # Local mode - skip all the complex setup
    print("🏠 Running in local mode - skipping auth and MongoDB")
    
    # Set up local parameters directly
    uuid = 'local'
    server = 'false'
    name = 'Data Explorer LOCAL TEST'
    is_authorized = True
    user_email = None
    
    # No MongoDB needed for local
    mymongodb = None
    collection = None
    collection1 = None
    team_collection = None
    
    print("✅ Local dashboard initialization successful")
    
else:
    # Production mode - use utility initialization
    doc = curdoc()
    real_request = doc.session_context.request if hasattr(doc, 'session_context') and doc.session_context else None
    
    # Create a request object that combines URL args with the real request (which has cookies)
    class RequestWithArgs:
        def __init__(self, real_request, args_dict):
            # Copy all attributes from the real request (including cookies)
            for attr in dir(real_request):
                if not attr.startswith('_'):
                    try:
                        setattr(self, attr, getattr(real_request, attr))
                    except:
                        pass
            
            # Override arguments with our parsed URL args
            self.arguments = {}
            for key, value in args_dict.items():
                if isinstance(value, list):
                    self.arguments[key] = value
                else:
                    self.arguments[key] = [value]
    
    request_with_args = RequestWithArgs(real_request, request_args)
    
    # Initialize dashboard using utility with the request object that has arguments
    init_result = initialize_dashboard(request_with_args, print)
    
    if not init_result['success']:
        print(f"❌ Dashboard initialization failed: {init_result['error']}")
        # Create error layout
        error_div = Div(text=f"<h2>❌ Error: {init_result['error']}</h2>", 
                       styles={'color': 'red', 'font-size': '14px'})
        curdoc().add_root(error_div)
        exit()
    
    # Extract initialization results
    auth_result = init_result['auth_result']
    mongodb = init_result['mongodb']
    params = init_result['params']
    
    # Set global variables from initialization
    uuid = params['uuid']
    server = params['server']
    name = params['name']
    base_dir = params.get('base_dir')
    save_dir = params.get('save_dir')
    is_authorized = auth_result['is_authorized']
    user_email = auth_result['user_email']
    
    # Set MongoDB variables if available
    if mongodb:
        mymongodb = mongodb['mymongodb']
        collection = mongodb['collection']
        collection1 = mongodb['collection1']
        team_collection = mongodb['team_collection']
    else:
        mymongodb = None
        collection = None
        collection1 = None
        team_collection = None
    
if has_args:
    print(f"base_dir: {base_dir}")
    print(f"save_dir: {save_dir}")

# Set dataset URL
if not has_args:
    # For local mode, use the directory containing the visus.idx file
    dataset_url = f"{local_base_dir}"
elif server in ['true', '%20true', ' true']:
    # When server=true, the uuid parameter is already the google_drive_link (or remote URL)
    # This is set by the frontend when google_drive_link exists and doesn't contain 'google.com'
    # So we can use it directly as the dataset_url
    if not DATA_IS_LOCAL and collection is not None:
        # Check if uuid looks like a URL (contains http)
        if uuid and 'http' in uuid:
            # UUID is already the link, use it directly
            print(f"🔍 DEBUG: UUID is already a URL/link: {uuid}")
            dataset_url = uuid
        else:
            # UUID is not a URL, try to look up the document to get google_drive_link
            print(f"🔍 DEBUG: Looking for dataset with uuid: {uuid}")
            document = collection.find_one({'uuid': uuid})
            print(f"🔍 DEBUG: Document found: {document is not None}")
            if document:
                print(f"🔍 DEBUG: Document keys: {list(document.keys())}")
                print(f"🔍 DEBUG: Has google_drive_link: {'google_drive_link' in document}")
                source_path = str(document.get('source_path') or '').strip()
                source_type = str(document.get('source_type') or '').strip().lower()
                google_drive_link = str(document.get('google_drive_link') or '').strip()

                # Prefer stored HTTPS Data Link (google_drive_link) over raw s3:// source_path.
                if google_drive_link.startswith(('http://', 'https://')):
                    old_uuid = uuid
                    uuid = google_drive_link
                    dataset_url = uuid
                    print(f"🔍 DEBUG: Replaced uuid '{old_uuid}' with google_drive_link (HTTPS) '{uuid}'")
                elif source_type == 's3' and is_s3_uri(source_path):
                    old_uuid = uuid
                    uuid = source_path
                    dataset_url = uuid
                    print(f"🔍 DEBUG: Replaced uuid '{old_uuid}' with source_path S3 URI '{uuid}'")
                elif is_s3_uri(name):
                    old_uuid = uuid
                    uuid = name.strip()
                    dataset_url = uuid
                    print(f"🔍 DEBUG: Using S3 URI from name, replaced uuid '{old_uuid}' with '{uuid}'")
                elif google_drive_link:
                    old_uuid = uuid
                    uuid = google_drive_link
                    dataset_url = uuid
                    print(f"🔍 DEBUG: Replaced uuid '{old_uuid}' with google_drive_link '{uuid}'")
                else:
                    print(f"🔍 DEBUG: No remote link in document, using uuid as dataset_url")
                    dataset_url = uuid
            else:
                print(f"🔍 DEBUG: No document found with uuid: {uuid}")
                # Try alternative lookup - maybe the uuid is actually the google_drive_link
                alt_document = collection.find_one({'google_drive_link': uuid})
                if alt_document:
                    print(f"🔍 DEBUG: Found document with google_drive_link matching uuid")
                    print(f"🔍 DEBUG: Document keys: {list(alt_document.keys())}")
                    dataset_url = uuid
                else:
                    print(f"🔍 DEBUG: No document found with google_drive_link: {uuid}, using uuid as dataset_url")
                    dataset_url = uuid
    else:
        # Local mode or no collection - use uuid directly (should already be the link)
        dataset_url = uuid
        print(f'🔍 DEBUG: Using uuid directly as dataset_url (local mode or no collection): {dataset_url}')
    
    print(f'🔍 DEBUG: Final dataset_url: {dataset_url}')
    print('loading server data...')
else:
    # When server='false', use direct file path to the IDX file
    # OpenVisus needs a direct path to the visus.idx file, not just the directory
    dataset_url = None

    # Defensive fallback: if UI passes server=false but name indicates remote source,
    # resolve the actual remote link from Mongo (or use name directly).
    if is_remote_link(name):
        if not DATA_IS_LOCAL and collection is not None and uuid and not is_remote_link(uuid):
            try:
                remote_doc = collection.find_one({'uuid': uuid})
                if remote_doc and remote_doc.get('google_drive_link'):
                    dataset_url = str(remote_doc.get('google_drive_link')).strip()
                    print(f"⚠️ server=false with remote name; using google_drive_link from Mongo: {dataset_url}")
                else:
                    dataset_url = name
                    print(f"⚠️ server=false with remote name; no Mongo link found, using name: {dataset_url}")
            except Exception as ex:
                dataset_url = name
                print(f"⚠️ server=false remote fallback failed ({ex}); using name: {dataset_url}")
        else:
            dataset_url = uuid if is_remote_link(uuid) else name
            print(f"⚠️ server=false with remote hint; using remote dataset URL: {dataset_url}")

    if dataset_url is not None:
        dataset_url = dataset_url.strip()
    elif save_dir:
        # Construct full path to visus.idx file in the converted directory
        idx_path = os.path.join(save_dir, 'visus.idx')
        if os.path.exists(idx_path):
            dataset_url = idx_path
            print(f'Using converted IDX file: {dataset_url}')
        else:
            # If visus.idx doesn't exist, try using the directory (OpenVisus might find it)
            dataset_url = save_dir
            print(f'⚠️ visus.idx not found in {save_dir}, using directory path: {dataset_url}')
    elif base_dir:
        # Construct full path to visus.idx file in the converted directory
        idx_path = os.path.join(base_dir, 'visus.idx')
        if os.path.exists(idx_path):
            dataset_url = idx_path
            print(f'Using converted IDX file: {dataset_url}')
        else:
            # If visus.idx doesn't exist, try using the directory (OpenVisus might find it)
            dataset_url = base_dir
            print(f'⚠️ visus.idx not found in {save_dir}, using directory path: {dataset_url}')
    else:
        # Fallback: construct path from UUID
        converted_path = f"/mnt/visus_datasets/converted/{uuid}"
        idx_path = os.path.join(converted_path, 'visus.idx')
        if os.path.exists(idx_path):
            dataset_url = idx_path
            print(f'Using constructed converted IDX path: {dataset_url}')
        elif os.path.exists(converted_path):
            dataset_url = converted_path
            print(f'Using constructed converted directory: {dataset_url}')
        else:
            # Last resort: try mod_visus URL (may not work in Docker)
            if deploy_server and 'localhost' in deploy_server:
                dataset_url = f"http://host.docker.internal/mod_visus?dataset={uuid}"
            else:
                dataset_url = f"{deploy_server}/mod_visus?dataset={uuid}"
            print(f'⚠️ Converted directory not found, using mod_visus URL: {dataset_url}')
            print(f'⚠️ Note: Dataset may need to be converted first')

print(f'Data Explorer: UUID: {uuid}, server: {server}, name: {name}')

# Redirect to home if not authorized
def button_redirect():
    button = Button(label="VisStore Home", button_type="success")
    button.js_on_event(ButtonClick, CustomJS(code=f"window.location.href = '{deploy_server}';"))
    return button

home_button = button_redirect()

def redirect():
    if not is_authorized:
        button = Button(label="Redirecting...", button_type="success", visible=False)
        button.js_on_event(ButtonClick, CustomJS(code=f"window.location.href = '{deploy_server}';"))
        js_click = CustomJS(args=dict(button=button), code="button.click();")
        layout = column(button, js_click)
        curdoc().add_root(layout)

redirect()

# Add the info button and Div for instructions
info_button = Button(label="Info", button_type="warning")
instructions_div = Div(text="", visible=False)

def show_instructions(event):
    global dataset_url, uuid, server, name, deploy_server

    if server == 'true' or server == '%20true':
        url = uuid
    else:
        url = f"{deploy_server}/mod_visus?dataset={uuid}"
        if os.path.exists(url):
            print(f"Path exists: {url}")
        else:
            print(f"Path does not exist: {url}")

    db = LoadDataset(url)
    dimensions = db.getLogicBox()
    timesteps = len(db.getTimesteps())
    info_text = f"""
        <h3>Dataset Information</h3>
        <p><strong>URL:</strong> {url}</p>
        <p><strong>Name:</strong> {str(name)}</p>
        <p><strong>Dimensions:</strong> {str(dimensions[1])}</p>
        <p><strong>Number of Timesteps:</strong> {timesteps}</p>
    """
    instructions_div.text = info_text
    instructions_div.visible = not instructions_div.visible

info_button.on_click(show_instructions)
# Create header banner
header_banner = create_header_banner(dataset_name=name if 'name' in globals() else "", dashboard_type="OpenVisusSlice")
curdoc().add_root(column(header_banner, row(home_button, info_button), instructions_div))

# Getting the current document
if __name__.startswith('bokeh'):
    from openvisuspy import SetupLogger, IsPanelServe, GetBackend, Slices
    from OpenVisus import *
    from openvisuspy.probes import ProbeTool

    # logger = SetupLogger()
    # logger.info(f"GetBackend()={GetBackend()}")

    is_panel = IsPanelServe()
    if is_panel:
        import panel as pn

        doc = None
    else:
        import bokeh

        doc = bokeh.io.curdoc()
        doc.theme = 'light_minimal'

    if False:
        view = Slice(doc=doc, is_panel=is_panel)
        view.setShowOptions([
            "datasets", "direction", "offset", "palette", "field", "resolution", "num_refinements", "colormapper_type",
            "palette_range_mode", "palette_range_vmin", "palette_range_vmax"
        ])
    else:
        view = Slices(doc=doc, is_panel=is_panel, cls=ProbeTool)
        view.setShowOptions([
            ["datasets", "palette", "resolution", "view_dep", "num_refinements", "colormapper_type", "show_metadata"],
            ["datasets", "direction", "offset", "colormapper_type", "palette_range_mode", "palette_range_vmin",
             "palette_range_vmax", "show-probe"]
        ])

    if is_s3_uri(dataset_url):
        # First, try loading without prompting:
        # 1) public datasets via direct URL, or
        # 2) private datasets via server-side cached credentials.
        s3_auto_loaded = False
        try:
            resolved_idx_path, response_meta = resolve_openvisus_resolved_idx_via_api(
                dataset_identifier=uuid if uuid and not is_remote_link(uuid) else None,
                s3_uri=dataset_url,
                user_email=user_email,
                endpoint_url=os.getenv("S3_ENDPOINT_URL", ""),
                region_name="us-east-1",
                cache_credentials=False,
                use_cached_credentials=True
            )
            print(f"[OpenVisusSlice][DEBUG] setDataset input={resolved_idx_path}")
            view.setDataset(resolved_idx_path)
            s3_auto_loaded = True
            s3_status_message = "<span style='color: green;'><b>S3 dataset loaded.</b> Using resolved converted idx.</span>"
        except Exception:
            s3_status_message = "<b>Private S3 dataset detected.</b> Provide runtime credentials to load this dashboard dataset."

        if s3_auto_loaded:
            s3_status = Div(text=s3_status_message, styles={"margin-bottom": "6px"})
            s3_auth_panel = column(s3_status, sizing_mode="stretch_width")
        else:
            s3_status = Div(
                text=s3_status_message,
                styles={"margin-bottom": "6px"}
            )
            s3_endpoint = TextInput(title="S3 Endpoint URL (optional)", value=os.getenv("S3_ENDPOINT_URL", ""))
            s3_region = TextInput(title="Region", value="us-east-1")
            s3_access = TextInput(title="Access Key", value="")
            s3_secret = PasswordInput(title="Secret Key", value="")
            s3_connect = Button(label="Load S3 Dataset", button_type="primary")

            def _connect_s3_dataset():
                try:
                    resolved_idx_path, _response_meta = resolve_openvisus_resolved_idx_via_api(
                        dataset_identifier=uuid if uuid and not is_remote_link(uuid) else None,
                        s3_uri=dataset_url,
                        user_email=user_email,
                        access_key=s3_access.value.strip(),
                        secret_key=s3_secret.value,
                        endpoint_url=s3_endpoint.value.strip(),
                        region_name=s3_region.value.strip() or "us-east-1",
                        cache_credentials=True,
                        use_cached_credentials=True
                    )
                    print(f"[OpenVisusSlice][DEBUG] setDataset input={resolved_idx_path}")
                    view.setDataset(resolved_idx_path)
                    s3_status.text = "<span style='color: green;'><b>S3 connection ready.</b> Dataset loaded. Credentials cached for reuse.</span>"
                except Exception as ex:
                    s3_status.text = f"<span style='color: red;'>Failed to load S3 dataset: {ex}</span>"

            s3_connect.on_click(_connect_s3_dataset)
            s3_auth_panel = column(s3_status, s3_endpoint, s3_region, s3_access, s3_secret, s3_connect, sizing_mode="stretch_width")
    elif is_remote_link(dataset_url):
        s3_auth_panel = None
        try:
            resolved_idx_path, _meta = resolve_openvisus_resolved_idx_via_api(
                dataset_identifier=uuid if uuid and not is_remote_link(uuid) else None,
                s3_uri=http_object_url_to_s3_uri(dataset_url),
                user_email=user_email,
                endpoint_url=os.getenv("S3_ENDPOINT_URL", ""),
                region_name="us-east-1",
                cache_credentials=False,
                use_cached_credentials=True,
            )
            print(f"[OpenVisusSlice][DEBUG] setDataset input={resolved_idx_path}")
            view.setDataset(resolved_idx_path)
        except Exception as ex:
            dataset_url = normalize_remote_dataset_url(dataset_url)
            print(f"[OpenVisusSlice][WARN] resolved idx unavailable ({ex}), falling back to direct remote URL")
            print(f"[OpenVisusSlice][DEBUG] setDataset input={dataset_url}")
            view.setDataset(dataset_url)
    else:
        s3_auth_panel = None
        dataset_url = normalize_remote_dataset_url(dataset_url)
        print(f"[OpenVisusSlice][DEBUG] setDataset input={dataset_url}")
        view.setDataset(dataset_url)

    if is_panel:
        main_layout = view.getMainLayout()
        use_template = True
        if use_template:
            template = pn.template.MaterialTemplate(title='ScientistCloud Dashboard')
            if s3_auth_panel is not None:
                template.main.append(s3_auth_panel)
            template.main.append(main_layout)
            template.servable()
        else:
            if s3_auth_panel is not None:
                s3_auth_panel.servable()
            main_layout.servable()
    else:
        main_layout = view.getMainLayout()
        if s3_auth_panel is not None:
            doc.add_root(s3_auth_panel)
        doc.add_root(main_layout)

# Register cleanup function to run when application exits
import atexit
atexit.register(cleanup_mongodb)
