import os
import sys
from urllib.parse import parse_qs
from bokeh.io import curdoc
from bokeh.models.widgets import Div
from bokeh.layouts import column, row
from bokeh.models import CustomJS, Button
from bokeh.events import ButtonClick
from dotenv import load_dotenv

# Import utility modules
from utils_bokeh_dashboard import initialize_dashboard
from utils_bokeh_mongodb import cleanup_mongodb
from utils_bokeh_auth import authenticate_user
from utils_bokeh_param import parse_url_parameters, setup_directory_paths


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
                if 'google_drive_link' in document and document['google_drive_link']:
                    old_uuid = uuid
                    uuid = document['google_drive_link']
                    dataset_url = uuid
                    print(f"🔍 DEBUG: Replaced uuid '{old_uuid}' with google_drive_link '{uuid}'")
                else:
                    print(f"🔍 DEBUG: No google_drive_link field found, using uuid as dataset_url")
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
    if save_dir:
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
curdoc().add_root(column(row(home_button, info_button), instructions_div))

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

    view.setDataset(dataset_url)

    if is_panel:
        main_layout = view.getMainLayout()
        use_template = True
        if use_template:
            template = pn.template.MaterialTemplate(title='ScientistCloud Dashboard')
            template.main.append(main_layout)
            template.servable()
        else:
            main_layout.servable()
    else:
        main_layout = view.getMainLayout()
        doc.add_root(main_layout)

# Register cleanup function to run when application exits
import atexit
atexit.register(cleanup_mongodb)
