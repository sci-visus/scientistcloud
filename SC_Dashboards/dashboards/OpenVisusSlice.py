import os
import sys
from urllib.parse import parse_qs, unquote
from bokeh.io import curdoc
from bokeh.models.widgets import Div
from bokeh.layouts import column, row
from bokeh.models import CustomJS, Button, TextInput, PasswordInput
from bokeh.events import ButtonClick
from dotenv import load_dotenv

# Import utility modules
from utils_bokeh_dashboard import initialize_dashboard
from utils_bokeh_mongodb import cleanup_mongodb

# SCLib: shared OpenVisus load resolution (dashboards only pass uuid/server/name)
try:
    from SCLib_Dashboards import (
        create_header_banner,
        is_remote_dataset_identifier,
        is_s3_uri,
        openvisus_set_dataset,
        prefer_direct_remote_openvisus,
        resolve_openvisus_load_target,
        resolve_openvisus_resolved_idx_via_api,
    )
except ImportError:
    from SCDash_openvisus_load import (
        openvisus_set_dataset,
        prefer_direct_remote_openvisus,
        resolve_openvisus_load_target,
        resolve_openvisus_resolved_idx_via_api,
    )

    def create_header_banner(dataset_name="", dashboard_type="Dashboard"):
        sc_blue = "#4E477F"
        title_text = (
            f"ScientistCloud | {dashboard_type}: {dataset_name}"
            if dataset_name
            else f"ScientistCloud | {dashboard_type}"
        )
        return Div(
            text=f'<div class="dashboard-header-banner" style="background-color: {sc_blue}; padding: 10px 20px; display: flex; align-items: center;"><span style="color: white;">{title_text}</span></div>',
            sizing_mode="stretch_width",
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
# Local dev only when explicitly enabled — bare /OpenVisusSlice/ hits (Docker health, WS) must not load Mac paths.
DATA_IS_LOCAL = os.getenv('SC_DASHBOARD_LOCAL_DEV', '').lower() in ('1', 'true', 'yes')
SKIP_DATASET_LOAD = not has_args and not DATA_IS_LOCAL
local_base_dir = os.getenv('LOCAL_BASE_DIR', '/Users/amygooch/GIT/SCI/DATA/turbine/turbin_visus')


# Set environment variables and paths
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"
if not has_args:
    sys.path.insert(0, '/Users/amygooch/GIT/VisusDataPortalPrivate/openvisuspy/src')
else:
    sys.path.insert(0, '/home/ViSOAR/dataportal/openvisuspy/src')
# Load environment variables
deploy_server = os.getenv('DEPLOY_SERVER')
openvisus_load_target = None
portal_uuid_param = None


if DATA_IS_LOCAL:
    # Explicit local dev only (SC_DASHBOARD_LOCAL_DEV=1)
    print("🏠 Running in local mode - skipping auth and MongoDB")
    
    # Set up local parameters directly
    uuid = 'local'
    portal_uuid_param = None  # original ?uuid= from portal (for resolved-idx API)
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

elif SKIP_DATASET_LOAD:
    uuid = ''
    server = 'false'
    name = ''
    portal_uuid_param = None
    user_email = None
    is_authorized = True
    mymongodb = None
    collection = None
    collection1 = None
    team_collection = None
    base_dir = save_dir = None

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
    # Keep portal dataset UUID for OpenVisus resolved-idx API (do not overwrite when swapping in google_drive_link).
    portal_uuid_param = str(params.get('uuid') or '').strip()
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

# Resolve load target via SCLib (Mongo, remote HTTPS, local idx — one policy for all dashboards)
if SKIP_DATASET_LOAD:
    openvisus_load_target = None
    dataset_url = None
else:
    openvisus_load_target = resolve_openvisus_load_target(
        portal_uuid=portal_uuid_param or uuid,
        server=server,
        name=name,
        collection=collection,
        save_dir=save_dir if 'save_dir' in globals() else None,
        base_dir=base_dir if 'base_dir' in globals() else None,
        deploy_server=deploy_server,
        local_dev_path=local_base_dir if DATA_IS_LOCAL else None,
        log=print,
    )
    dataset_url = openvisus_load_target.load_url
    print(f'🔍 DEBUG: Final dataset_url (SCLib): {dataset_url}')

print(f'Data Explorer: UUID: {uuid}, server: {server}, name: {name}')

# Redirect to home if not authorized
def button_redirect():
    button = Button(label="VisStore Home", button_type="success")
    button.js_on_event(ButtonClick, CustomJS(code=f"window.location.href = '{deploy_server}';"))
    return button

home_button = button_redirect()

def redirect():
    if SKIP_DATASET_LOAD:
        return
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
    from openvisuspy import SetupLogger, IsPanelServe, Slices
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

    if SKIP_DATASET_LOAD:
        placeholder = Div(
            text="<h3>OpenVisus Slice</h3><p>Open a dataset from the ScientistCloud portal.</p>",
            styles={'padding': '20px'},
        )
        curdoc().add_root(placeholder)
        s3_auth_panel = None
    elif (
        openvisus_load_target
        and openvisus_load_target.is_s3
        and not openvisus_load_target.prefer_direct_remote
    ):
        s3_auto_loaded = False
        try:
            resolved_idx_path, _response_meta = resolve_openvisus_resolved_idx_via_api(
                dataset_identifier=openvisus_load_target.portal_uuid
                if not is_remote_dataset_identifier(openvisus_load_target.portal_uuid)
                else None,
                s3_uri=openvisus_load_target.load_url,
                user_email=user_email,
                endpoint_url=os.getenv("S3_ENDPOINT_URL", ""),
                region_name="us-east-1",
                cache_credentials=False,
                use_cached_credentials=True,
            )
            view.setDataset(resolved_idx_path)
            s3_auto_loaded = True
            s3_status_message = "<span style='color: green;'><b>S3 dataset loaded.</b> Using resolved converted idx.</span>"
        except Exception:
            s3_status_message = "<b>Private S3 dataset detected.</b> Provide runtime credentials to load this dashboard dataset."

        if s3_auto_loaded:
            s3_status = Div(text=s3_status_message, styles={"margin-bottom": "6px"})
            s3_auth_panel = column(s3_status, sizing_mode="stretch_width")
        else:
            s3_status = Div(text=s3_status_message, styles={"margin-bottom": "6px"})
            s3_endpoint = TextInput(title="S3 Endpoint URL (optional)", value=os.getenv("S3_ENDPOINT_URL", ""))
            s3_region = TextInput(title="Region", value="us-east-1")
            s3_access = TextInput(title="Access Key", value="")
            s3_secret = PasswordInput(title="Secret Key", value="")
            s3_connect = Button(label="Load S3 Dataset", button_type="primary")

            def _connect_s3_dataset():
                try:
                    resolved_idx_path, _response_meta = resolve_openvisus_resolved_idx_via_api(
                        dataset_identifier=openvisus_load_target.portal_uuid
                        if not is_remote_dataset_identifier(openvisus_load_target.portal_uuid)
                        else None,
                        s3_uri=openvisus_load_target.load_url,
                        user_email=user_email,
                        access_key=s3_access.value.strip(),
                        secret_key=s3_secret.value,
                        endpoint_url=s3_endpoint.value.strip(),
                        region_name=s3_region.value.strip() or "us-east-1",
                        cache_credentials=True,
                        use_cached_credentials=True,
                    )
                    view.setDataset(resolved_idx_path)
                    s3_status.text = "<span style='color: green;'><b>S3 connection ready.</b> Dataset loaded.</span>"
                except Exception as ex:
                    s3_status.text = f"<span style='color: red;'>Failed to load S3 dataset: {ex}</span>"

            s3_connect.on_click(_connect_s3_dataset)
            s3_auth_panel = column(s3_status, s3_endpoint, s3_region, s3_access, s3_secret, s3_connect, sizing_mode="stretch_width")
    else:
        s3_auth_panel = None
        openvisus_set_dataset(view, openvisus_load_target, user_email=user_email, log=print)

    if not SKIP_DATASET_LOAD:
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
