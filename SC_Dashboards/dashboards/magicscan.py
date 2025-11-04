import os
import sys
from urllib.parse import parse_qs
from bokeh.io import curdoc
from bokeh.models.widgets import Div
from bokeh.layouts import column, row
from bokeh.models import CustomJS, Button
from bokeh.events import ButtonClick
from dotenv import load_dotenv
import jwt

# Set environment variables for OpenVisus and Bokeh
os.environ["PYTHONPATH"] = "/home/ViSOAR/dataportal/openvisuspy/src"
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"
os.environ["BOKEH_LOG_LEVEL"] = "debug"
os.environ["VISUS_CPP_VERBOSE"] = "1"
os.environ["VISUS_NETSERVICE_VERBOSE"] = "1"
os.environ["VISUS_VERBOSE_DISKACCESS"] = "0"
os.environ["VISUS_CACHE"] = "/tmp/visus-cache"

# Import utility modules
from utils_bokeh_dashboard import initialize_dashboard
from utils_bokeh_mongodb import connect_to_mongodb, cleanup_mongodb
from utils_bokeh_auth import authenticate_user, check_dataset_access
from utils_bokeh_param import parse_url_parameters, setup_directory_paths

import panel as pn

# How to run as local CLI
#   python -m bokeh serve magicscan/magicscan.py --port 5033 --allow-websocket-origin=localhost:5033

    # #set PYTHONPATH=C:\projects\OpenVisus\build\RelWithDebInfo;.\src
    # set BOKEH_ALLOW_WS_ORIGIN=*
    # set BOKEH_LOG_LEVEL=debug
    # set VISUS_CPP_VERBOSE=1
    # set VISUS_NETSERVICE_VERBOSE=1
    # set VISUS_VERBOSE_DISKACCESS=0
    # #set VISUS_CACHE=c:/tmp/visus-cache

# Set environment variables and paths
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"
sys.path.append('/home/ViSOAR/dataportal/openvisuspy/src')

# Load environment variables
sec_key = os.getenv('SECRET_KEY')
deploy_server = os.getenv('DEPLOY_SERVER')
db_name = os.getenv('DB_NAME')

# Connect to MongoDB using utility function
client, mymongodb, collection, collection1, team_collection, shared_team_collection = connect_to_mongodb()

# Getting URL parameters in Bokeh
# In Bokeh, we can access URL parameters through curdoc().session_context.request
has_args = False
request_args = {}

# Try to get URL parameters from Bokeh's request
try:
    from bokeh.io import curdoc
    doc = curdoc()
    if hasattr(doc, 'session_context') and doc.session_context and hasattr(doc.session_context, 'request'):
        request = doc.session_context.request
        if hasattr(request, 'arguments') and request.arguments:
            request_args = request.arguments
            has_args = len(request_args) > 0
except:
    # Fallback: try to get from environment or use local mode
    has_args = False

DATA_IS_LOCAL = not has_args
 
local_base_dir = f'/Users/amygooch/GIT/SCI/DATA/2kbit1'
# Load environment variables
load_dotenv()

# Global variables
uuid = None
server = None
name = None
file_path = None
save_dir = None
base_dir = None
first_folder = None
is_authorized = False
user_email = None
mymongodb = None
collection = None
collection1 = None
team_collection = None
selected_values = None
dataset_url = None
 


if not has_args:
    # Local mode - skip all the complex setup
    print("🏠 Running in local mode - skipping auth and MongoDB")
    
    # Set up local parameters directly
    uuid = 'local'
    server = 'false'
    name = '4D_probe_IDX_dashboard LOCAL TEST'
    base_dir = local_base_dir
    save_dir = local_base_dir
    is_authorized = True
    user_email = None
    
    # No MongoDB needed for local
    mymongodb = None
    collection = None
    collection1 = None
    team_collection = None
    
    print(f"base_dir: {base_dir}")
    print(f"save_dir: {save_dir}")
    print("✅ Local dashboard initialization successful")
    
else:
    # Production mode - use utility initialization
 
    # Get the real Bokeh request object that has cookies
    from bokeh.io import curdoc
    doc = curdoc()
    real_request = doc.session_context.request
    
    # Create a request object that combines URL args with the real request (which has cookies)
    class RequestWithArgs:
        def __init__(self, real_request, args_dict):
            # Copy all attributes from the real request (including cookies)
            for attr in dir(real_request):
                if not attr.startswith('_'):
                    setattr(self, attr, getattr(real_request, attr))
            
            # Override arguments with our parsed URL args
            self.arguments = {}
            for key, value in args_dict.items():
                if isinstance(value, list):
                    self.arguments[key] = value
                else:
                    self.arguments[key] = [value]
    
    request_with_args = RequestWithArgs(real_request, request_args)
    
    # Initialize dashboard using utility with the real request object
    init_result = initialize_dashboard(request_with_args, print)
    
    if not init_result['success']:
        print(f"❌ Dashboard initialization failed: {init_result['error']}")
        # Create error layout using Bokeh
        error_div = Div(text=f"<h2>❌ Error: {init_result['error']}</h2>",
                       styles={'color': 'red', 'font-size': '14px'})
        doc.add_root(error_div)
        # Set a flag to skip the rest of the initialization
        init_failed = True
    else:
        init_failed = False
    
    if not init_failed:
        # Extract initialization results
        auth_result = init_result['auth_result']
        mongodb = init_result['mongodb']
        params = init_result['params']
        
        # Set global variables from initialization
        uuid = params['uuid']
        server = params['server']
        name = params['name']
        base_dir = params['base_dir']
        save_dir = params['save_dir']
        is_authorized = auth_result['is_authorized']
        user_email = auth_result['user_email']
        
        # Set MongoDB variables if available
        if mongodb:
            mymongodb = mongodb['mymongodb']
            collection = mongodb['collection']
            collection1 = mongodb['collection1']
            team_collection = mongodb['team_collection']

        print(f"uuid: {uuid}, server: {server}, name: {name}")
        print(f"base_dir: {base_dir}, save_dir: {save_dir}")
        print(f"is_authorized: {is_authorized}, user_email: {user_email}")
   

# # Redirect to home if not authorized
# def button_redirect():
#     button = Button(label="VisStore Home", button_type="success")
#     button.js_on_event(ButtonClick, CustomJS(code=f"window.location.href = '{deploy_server}';"))
#     return button

# home_button = button_redirect()

# def redirect():
#     if not is_authorized:
#         button = Button(label="Redirecting...", button_type="success", visible=False)
#         button.js_on_event(ButtonClick, CustomJS(code=f"window.location.href = '{deploy_server}';"))
#         js_click = CustomJS(args=dict(button=button), code="button.click();")
#         layout = column(button, js_click)
#         curdoc().add_root(layout)

# redirect()

# # Add the info button and Div for instructions
# info_button = Button(label="Info", button_type="warning")
# instructions_div = Div(text="", visible=False)

# def show_instructions(event):
#     global dataset_url, uuid, server, name, deploy_server


    # Use host.docker.internal for Docker containers to access host localhost
    # if deploy_server and 'localhost' in deploy_server:
    #     dataset_url = f"http://host.docker.internal/mod_visus?dataset={uuid}"
    # else:
    #     dataset_url = f"{deploy_server}/mod_visus?dataset={uuid}"


#     db = LoadDataset(url)
#     dimensions = db.getLogicBox()
#     timesteps = len(db.getTimesteps())
#     info_text = f"""
#         <h3>Dataset Information</h3>
#         <p><strong>URL:</strong> {url}</p>
#         <p><strong>Name:</strong> {str(name)}</p>
#         <p><strong>Dimensions:</strong> {str(dimensions[1])}</p>
#         <p><strong>Number of Timesteps:</strong> {timesteps}</p>
#     """
#     instructions_div.text = info_text
#     instructions_div.visible = not instructions_div.visible

# info_button.on_click(show_instructions)
# curdoc().add_root(column(row(home_button, info_button), instructions_div))

from OpenVisus import *

from openvisuspy import Slice




# Panel application entry point
#if __name__.startswith('panel') or __name__ == '__main__':
if __name__.startswith('bokeh'):
    # Only proceed with dashboard creation if initialization succeeded
    if not has_args:
        # For local mode, use the directory containing the visus.idx file
        dataset_url = f"{local_base_dir}/visus.idx"
    elif init_failed:
        # If initialization failed, don't proceed
        pass
    elif server in ['true', '%20true', ' true']:
        if not DATA_IS_LOCAL and collection is not None:
            print(f"🔍 DEBUG: Looking for dataset with uuid: {uuid}")
            document = collection.find_one({'uuid': uuid})
            print(f"🔍 DEBUG: Document found: {document is not None}")
            if document:
                print(f"🔍 DEBUG: Document keys: {list(document.keys())}")
                print(f"🔍 DEBUG: Has google_drive_link: {'google_drive_link' in document}")
                if 'google_drive_link' in document:
                    old_uuid = uuid
                    uuid = document['google_drive_link']
                    print(f"🔍 DEBUG: Replaced uuid '{old_uuid}' with google_drive_link '{uuid}'")
                else:
                    print(f"🔍 DEBUG: No google_drive_link field found")
            else:
                print(f"🔍 DEBUG: No document found with uuid: {uuid}")
                # Try alternative lookup - maybe the uuid is actually the google_drive_link
                alt_document = collection.find_one({'google_drive_link': uuid})
                if alt_document:
                    print(f"🔍 DEBUG: Found document with google_drive_link matching uuid")
                    print(f"🔍 DEBUG: Document keys: {list(alt_document.keys())}")
                else:
                    print(f"🔍 DEBUG: No document found with google_drive_link: {uuid}")
        dataset_url = uuid
        print(f'🔍 DEBUG: Final dataset_url: {dataset_url}')
        print('loading server data...')
    else:
        # Use the local converted dataset file
        dataset_url = f"{save_dir}/visus.idx"
    print(f"dataset_url: {dataset_url}")
    print(f"uuid: {uuid}")
    
    # Only create dashboard if initialization succeeded
    if not init_failed:
        # Create the Slice component
        try:
            view = Slice()
            view.setShowOptions({
                "top": [
                ["datasets", "direction", "offset", "palette", "field", "resolution", "num_refinements", "colormapper_type"],
                ["palette_range_mode", "palette_range_vmin", "palette_range_vmax"]
                ]
            })
            
            view.load(dataset_url)
            main_layout = view.getMainLayout()
            main_layout.servable()
            print("Dashboard created and served successfully")
        except Exception as e:
            print(f"Error creating dashboard: {e}")
            error_panel = pn.pane.HTML(f"<h1>Error loading dashboard</h1><p>{str(e)}</p>")
            error_panel.servable()
        
# Register cleanup function to run when application exits
import atexit
atexit.register(cleanup_mongodb)