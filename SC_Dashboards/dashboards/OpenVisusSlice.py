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
        apply_openvisus_view_prefs,
        create_header_banner,
        load_dataset_view_prefs,
        openvisus_set_dataset,
        resolve_openvisus_load_target,
        save_dataset_view_prefs,
        user_owns_dataset,
    )
except ImportError:
    from SCDash_openvisus_load import (
        apply_openvisus_view_prefs,
        load_dataset_view_prefs,
        openvisus_set_dataset,
        resolve_openvisus_load_target,
        save_dataset_view_prefs,
        user_owns_dataset,
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
        error_div = Div(
            text=f"<h2>❌ Error: {init_result['error']}</h2>",
            styles={'color': 'red', 'font-size': '14px'},
        )
        curdoc().add_root(error_div)
        # Do not exit() — kills the Bokeh session and nginx returns 502 Bad Gateway
        SKIP_DATASET_LOAD = True
        is_authorized = False
        uuid = ''
        server = 'false'
        name = ''
        portal_uuid_param = None
        user_email = None
        openvisus_load_target = None
        dataset_url = None
        mymongodb = None
        collection = None
        collection1 = None
        team_collection = None
        base_dir = save_dir = None
    else:
        # Extract initialization results
        auth_result = init_result['auth_result']
        mongodb = init_result['mongodb']
        params = init_result['params']

        uuid = params['uuid']
        # Portal MongoDB uuid for auth, resolved-idx API, and upload/converted paths.
        portal_uuid_param = str(params.get('portal_uuid') or params.get('uuid') or '').strip()
        server = params['server']
        name = params['name']
        base_dir = params.get('base_dir')
        save_dir = params.get('save_dir')
        is_authorized = auth_result['is_authorized']
        user_email = auth_result['user_email']

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
view_prefs = None
can_save_view = False
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
    view_prefs = load_dataset_view_prefs(collection if 'collection' in globals() else None, portal_uuid_param or uuid)
    try:
        owner_doc = None
        if 'collection' in globals() and collection is not None and (portal_uuid_param or uuid):
            owner_doc = collection.find_one(
                {"uuid": portal_uuid_param or uuid},
                {"user": 1, "user_email": 1, "owner": 1, "user_id": 1},
            )
        can_save_view = user_owns_dataset(owner_doc, user_email if 'user_email' in globals() else None)
    except Exception as owner_ex:
        print(f"[OpenVisusSlice] owner check failed: {owner_ex}")
        can_save_view = False
    try:
        from SCLib_Dashboards import redact_url_secrets as _redact_url
    except ImportError:
        try:
            from SCDash_openvisus_load import redact_url_secrets as _redact_url
        except ImportError:
            _redact_url = lambda u: u
    print(f'🔍 DEBUG: Final dataset_url (SCLib): {_redact_url(dataset_url)}')
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

    def _configure_slice_widgets(include_time):
        top = ["datasets", "palette", "resolution", "view_dep", "num_refinements", "colormapper_type", "show_metadata"]
        if include_time:
            top.insert(1, "timestep")
        view.setShowOptions([
            top,
            ["datasets", "direction", "offset", "colormapper_type", "palette_range_mode", "palette_range_vmin",
             "palette_range_vmax", "show-probe"],
        ])

    def _has_multiple_timesteps(slice_view):
        try:
            start = int(slice_view.widgets.timestep.start)
            end = int(slice_view.widgets.timestep.end)
            return end > start
        except Exception:
            return False

    def _capture_slice_prefs(slice_view):
        children = getattr(slice_view, "children", None) or []
        active = children[0] if children else slice_view
        captured = {}
        readers = (
            ("direction", active, "getDirection", int),
            ("offset", active, "getOffset", float),
            ("timestep", slice_view, "getTimestep", int),
            ("palette", slice_view, "getPalette", str),
            ("colormap", slice_view, "getColorMapperType", str),
            ("range_mode", active, "getPaletteRangeMode", str),
            ("resolution", slice_view, "getResolution", int),
            ("field", slice_view, "getField", str),
            ("num_refinements", slice_view, "getNumberOfRefinements", int),
        )
        for key, obj, method, cast in readers:
            fn = getattr(obj, method, None)
            if not callable(fn):
                continue
            try:
                captured[key] = cast(fn())
            except Exception as ex:
                print(f"[OpenVisusSlice] skip {key}: {ex}")
        if hasattr(slice_view, "isViewDependent"):
            try:
                captured["auto_res"] = bool(slice_view.isViewDependent())
            except Exception as ex:
                print(f"[OpenVisusSlice] skip auto_res: {ex}")
        if captured.get("range_mode") == "user" and hasattr(active, "getPaletteRange"):
            try:
                vmin, vmax = active.getPaletteRange()
                captured["range_min"] = float(vmin)
                captured["range_max"] = float(vmax)
                captured["transfer_function"] = {
                    "palette": captured.get("palette") or "Viridis256",
                    "window": [float(vmin), float(vmax)],
                    "opacity": [[0.0, 0.0], [0.15, 0.25], [1.0, 0.85]],
                }
            except Exception as ex:
                print(f"[OpenVisusSlice] skip range: {ex}")
        return captured

    if SKIP_DATASET_LOAD:
        _configure_slice_widgets(False)
        placeholder = Div(
            text="<h3>OpenVisus Slice</h3><p>Open a dataset from the ScientistCloud portal.</p>",
            styles={'padding': '20px'},
        )
        curdoc().add_root(placeholder)
        s3_auth_panel = None
    else:
        # Always LoadDataset the resolved URL (local upload/converted, or remote HTTPS idx).
        # Never POST openvisus-resolved-idx / create converted/visus.idx proxy stubs.
        s3_auth_panel = None
        openvisus_set_dataset(
            view,
            openvisus_load_target,
            user_email=user_email,
            view_prefs=view_prefs,
            log=print,
        )
        _configure_slice_widgets(_has_multiple_timesteps(view))

    if not SKIP_DATASET_LOAD:
        save_status = Div(text="")

        def _save_default_view(_event):
            ok, message = save_dataset_view_prefs(
                collection if 'collection' in globals() else None,
                portal_uuid_param or uuid,
                _capture_slice_prefs(view),
                user_email,
            )
            save_status.text = message
            print(f"[OpenVisusSlice] save default view: {message}")

        save_controls = None
        if can_save_view:
            save_button = Button(label="Save as default view", button_type="primary")
            save_button.on_click(_save_default_view)
            save_controls = row(save_button, save_status)

        if is_panel:
            main_layout = view.getMainLayout()
            apply_openvisus_view_prefs(view, view_prefs, log=print)
            if save_controls is not None:
                main_layout = column(save_controls, main_layout)
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
            apply_openvisus_view_prefs(view, view_prefs, log=print)
            if save_controls is not None:
                main_layout = column(save_controls, main_layout, sizing_mode="stretch_width")
            if s3_auth_panel is not None:
                doc.add_root(s3_auth_panel)
            doc.add_root(main_layout)

# Register cleanup function to run when application exits
import atexit
atexit.register(cleanup_mongodb)
