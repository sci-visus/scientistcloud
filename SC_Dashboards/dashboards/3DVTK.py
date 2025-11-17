#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os

# this may be dangerous, only for local testing/debugging
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"

# if you want more debug info
if False:
    os.environ["BOKEH_LOG_LEVEL"] = "debug"

import bokeh
import bokeh.io
import bokeh.models.widgets
import bokeh.core.validation
import bokeh.plotting
import bokeh.core.validation.warnings
import bokeh.layouts
from bokeh.models import Select, Slider
from bokeh.models.widgets import Div, Button
from bokeh.plotting import curdoc
bokeh.core.validation.silence(bokeh.core.validation.warnings.EMPTY_LAYOUT, True)
from bokeh.models import CustomJS
from bokeh.models import Div
from bokeh.events import ButtonClick
from bokeh.layouts import column, row
from dotenv import load_dotenv
from OpenVisus import *
load_dotenv()  # Load environment variables from .env file

# Import utility modules
from utils_bokeh_dashboard import initialize_dashboard
from utils_bokeh_mongodb import cleanup_mongodb
from utils_bokeh_auth import authenticate_user
from utils_bokeh_param import parse_url_parameters, setup_directory_paths


# Run it via: 
#    bokeh serve Docker/bokeh/Visus.py --port 5033 --allow-websocket-origin=localhost:5033


deploy_server = os.getenv('DEPLOY_SERVER')

# Initialize dashboard using utility functions
# Check if running locally - if no URL args, we're in local mode
from bokeh.plotting import curdoc
doc = curdoc()
request = doc.session_context.request if hasattr(doc, 'session_context') and doc.session_context else None
has_url_args = request and request.arguments and len(request.arguments) > 0
DATA_IS_LOCAL = not has_url_args

local_base_dir = f'/Users/amygooch/GIT/SCI/DATA/turbine/turbin_visus'
 

if DATA_IS_LOCAL:
    # Local mode - skip all the complex setup
    print("🏠 Running in local mode - skipping auth and MongoDB")
    
    # Set up local parameters directly
    uuid = 'local'
    server = 'false'
    name = 'ScientistCloud VTK Dashboard LOCAL TEST'
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
    request = doc.session_context.request if hasattr(doc, 'session_context') and doc.session_context else None
    
    # Initialize dashboard using utility
    init_result = initialize_dashboard(request, print)
    
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

print(f'ScientistCloud VTK Dashboard: UUID: {uuid}, server: {server}, name: {name}')

def button_redirect():
    button = Button(label="ScientistCloud Home", button_type="success")
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

# Add the info button and Div for dataset information
info_button = Button(label="Info", button_type="warning")
info_div = Div(text="", visible=False)

def show_info(event):
    global uuid, server, name, deploy_server

    if server == 'true' or server == '%20true':
        url = uuid
    else:
        url = f"{deploy_server}/mod_visus?dataset={uuid}"
        if os.path.exists(url):
            print(f"Path exists: {url}")
        else:
            url = find_visus_idx_file(uuid);
            print(f"Path may exist: {url}")
            if (not os.path.exists(url)):
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
    info_div.text = info_text
    info_div.visible = not info_div.visible

info_button.on_click(show_info)
curdoc().add_root(column(row(home_button, info_button), info_div))


# In[ ]:


import OpenVisus as  ov
os.environ["VISUS_NETSERVICE_VERBOSE"]="0"

import panel as pn
import numpy as np

# Set up headless rendering environment
import os
os.environ['PYVISTA_OFF_SCREEN'] = 'true'
os.environ['PYVISTA_USE_PANEL'] = 'true'

# Try to import PyVista, but handle X11 library errors gracefully
PYVISTA_AVAILABLE = False
try:
    import pyvista as pv
    from pyvista.plotting.plotter import Plotter
    PYVISTA_AVAILABLE = True
    print("✅ PyVista imported successfully")
except ImportError as e:
    print(f"⚠️ PyVista not available: {e}")
    PYVISTA_AVAILABLE = False
except Exception as e:
    print(f"⚠️ PyVista import failed (likely missing X11 libraries): {e}")
    print("🔄 Falling back to Panel's native VTK volume rendering")
    PYVISTA_AVAILABLE = False

# Enable PyVista for Panel
pn.extension('vtk')


# In[ ]:


import json
uuid_ref = ["None" ]
uuid_names = ["None"]
uuid_opts =None
uuid_arg="neuroOrig"

myTitle = pn.pane.Markdown(f'''
# ScientistCloud Explorer: {name}
''')
myTitlePanel=pn.panel(myTitle, name='header')

# Initialize PyVista plotter
plotter = pv.Plotter(notebook=True, off_screen=True)
plotter.set_background('black')

# Create volume and slice placeholders
volume_pane = pn.pane.Markdown('### Volume loading...')
slice_pane = pn.pane.Markdown('### Slices loading...')
Tools = pn.pane.Markdown('### Tools placeholder...')
Viz =  pn.pane.Markdown('### Viz placeholder...')

# Global variables to hold the current panel objects
current_volume_pane = None
current_viz_layout = None

# Global variables for volume data
volume_data = None
volume_resolution = None

# Simple counter to trigger updates
volume_update_counter = 0

# Global variables for PyVista data
current_volume = None
current_data = None

def create_pyvista_volume(data, spacing=(1, 1, 1)):
    """Create a PyVista volume with proper aspect ratio"""
    global current_volume, current_data
    
    if not PYVISTA_AVAILABLE:
        raise ImportError("PyVista not available")
    
    # Convert numpy array to PyVista volume
    if len(data.shape) == 3:
        # 3D volume data
        volume = pv.wrap(data)
        volume.spacing = spacing
        current_data = data
    else:
        # Handle other data types
        volume = pv.wrap(data)
        current_data = data
    
    current_volume = volume
    return volume

def create_volume_rendering(volume, opacity='linear', cmap='viridis'):
    """Create volume rendering with PyVista"""
    if not PYVISTA_AVAILABLE:
        raise ImportError("PyVista not available")
        
    plotter = pv.Plotter(notebook=True, off_screen=True)
    plotter.set_background('black')
    
    # Add volume rendering
    plotter.add_volume(volume, opacity=opacity, cmap=cmap, 
                      show_scalar_bar=True, scalar_bar_args={'title': 'Intensity'})
    
    # Set proper camera position
    plotter.camera_position = 'iso'
    plotter.enable_parallel_projection()
    
    return plotter

def create_orthogonal_slices(volume, slice_indices=None):
    """Create orthogonal slices through the volume"""
    if not PYVISTA_AVAILABLE:
        raise ImportError("PyVista not available")
        
    if slice_indices is None:
        # Use middle slices
        dims = volume.dimensions
        slice_indices = [dims[0]//2, dims[1]//2, dims[2]//2]
    
    plotter = pv.Plotter(notebook=True, off_screen=True)
    plotter.set_background('white')
    
    # Create orthogonal slices
    slices = volume.slice_orthogonal(x=slice_indices[0], y=slice_indices[1], z=slice_indices[2])
    
    # Add each slice with different colors
    colors = ['red', 'green', 'blue']
    for i, slice_mesh in enumerate(slices):
        plotter.add_mesh(slice_mesh, cmap=colors[i], opacity=0.8, 
                        show_scalar_bar=False, name=f'slice_{i}')
    
    plotter.camera_position = 'iso'
    return plotter

def calculate_proper_spacing(data_shape):
    """Calculate proper spacing to maintain aspect ratio"""
    # Get the maximum dimension to normalize spacing
    max_dim = max(data_shape)
    
    # Calculate spacing that maintains aspect ratio
    spacing = (max_dim / data_shape[0], max_dim / data_shape[1], max_dim / data_shape[2])
    
    print(f"Data shape: {data_shape}")
    print(f"Calculated spacing: {spacing}")
    
    return spacing

def update_volume_visualization(data, resolution_val):
    """Update the volume visualization with new data"""
    global current_volume, current_data
    
    print("🔄 Creating VTK volume with proper aspect ratio and resolution handling")
    
    # Calculate proper spacing for aspect ratio
    spacing = calculate_proper_spacing(data.shape)
    
    # Create Panel VTK volume with proper aspect ratio handling
    volume = pn.panel(
        data, 
        sizing_mode='stretch_both', 
        min_height=400,
        orientation_widget=True,
        display_slices=True,
        spacing=spacing,  # Use calculated spacing for proper aspect ratio
        controller_expanded=False
    )
    
    # Store the current data for reference
    current_data = data
    current_volume = volume
    
    print(f"✅ Created volume with shape: {data.shape}, resolution: {resolution_val}")
    print(f"✅ Set spacing={spacing} for proper aspect ratio")
    
    return volume, volume

def create_volume_pane():
    """Create a volume pane with current data"""
    global volume_data, volume_resolution
    
    if volume_data is not None:
        print(f"🔄 Creating volume pane with shape: {volume_data.shape}, resolution: {volume_resolution}")
        
        # Calculate proper spacing for aspect ratio
        spacing = calculate_proper_spacing(volume_data.shape)
        
        # Create Panel VTK volume with proper aspect ratio handling
        volume = pn.panel(
            volume_data, 
            sizing_mode='stretch_both', 
            min_height=400,
            orientation_widget=True,
            display_slices=True,
            spacing=spacing,  # Use calculated spacing for proper aspect ratio
            controller_expanded=False
        )
        
        return volume
    else:
        return pn.pane.Markdown('### No volume data loaded')

# Simple function to create volume pane with current data
def get_current_volume_pane():
    """Get the current volume pane with latest data"""
    global volume_data, volume_resolution, volume_update_counter
    
    if volume_data is not None:
        print(f"🔄 Creating volume pane with shape: {volume_data.shape}, resolution: {volume_resolution}, counter: {volume_update_counter}")
        
        # Calculate proper spacing for aspect ratio
        spacing = calculate_proper_spacing(volume_data.shape)
        
        # Create Panel VTK volume with proper aspect ratio handling
        volume = pn.panel(
            volume_data, 
            sizing_mode='stretch_both', 
            min_height=400,
            orientation_widget=True,
            display_slices=True,
            spacing=spacing,  # Use calculated spacing for proper aspect ratio
            controller_expanded=False
        )
        
        return volume
    else:
        return pn.pane.Markdown('### No volume data loaded')

#uuid_input = TextInput(value="", title="Dataset name on server")
uuid_reload_button = Button(label='Reload')
#text_banner = Paragraph(text='Log goes here', width=200, height=100)
notifications = Div(text='Log:')#, name=name, width=width, height=height)
resolution_slider  = None

# ViSOARhelp_button = Button(label='Help')
# helpText = 'Welcome to the ViSOAR Bokeh Jupyter Notebook.\n  In the viewer you can: \n\tPan by Shift+Click; \tRotate by Alt+Click\n\n'


#UI Elements
UI_INIT_DONE = False
UI_VOL_CTRLS = 4
UI_NOTIFICATIONS = 5


# In[ ]:


def emptySelection():
    uuid_ref = ["None" ]
    uuid_names = ["None"]
    uuid_opts ={}
    uuid_arg="neuroOrig"

def loadDefaults():
    emptySelection()
    # Parameters
    uuid_arg='e68184df-e562-46d8-8e18-9a8a21002570' #2d
    uuid_arg='042fbaff-d032-454e-90d4-716908689dbb' #neuro
    uuid_arg='neuroOrigArco'

    uuid_ref = ["None" ]
    uuid_names = ["None"]
    uuid_arg='ag-test'
    uuid_names.append(uuid_arg)
    uuid_ref.append(uuid_arg)
    uuid_arg='neuroOrig'
    uuid_names.append(uuid_arg)
    uuid_ref.append(uuid_arg)
    uuid_arg='neuroOrigArco'
    uuid_names.append(uuid_arg)
    uuid_ref.append(uuid_arg)
  

    uuid_opts = {k:v for k,v in zip(uuid_names, uuid_ref)}
    return uuid_ref, uuid_names, uuid_opts;

def loadFromFile():
    emptySelection()
    with open ('datasets.json') as file:
        ListODatasets = json.load(file)
        #print(ListODatasets)
    USE_JSON_FILE = True
    if (USE_JSON_FILE):
       
        for json_object in ListODatasets:
            entry = ListODatasets[json_object]
            entry['time']
            entry['uuid']
            uuid_names.append(json_object)
            uuid_ref.append(entry['uuid'])
        uuid_arg="1030a2ae-c575-41b0-b431-8981143ff8f2" #ag 
        uuid_arg="neuroOrig"
        uuid_opts = {k:v for k,v in zip(uuid_names, uuid_ref)}
        print(uuid_opts)
        return uuid_ref, uuid_names, uuid_opts;
    
def load_from_url():
    # Fetch URL parameters
    args = curdoc().session_context.request.arguments

    # Create uuid_ref, uuid_names, and uuid_opts lists similar to loadFromFile()
    uuid_ref = [uuid]
    uuid_names = [name]
    uuid_opts = {name: uuid}

    return uuid_ref,uuid_names, uuid_opts


# In[ ]:


def get_name_for_uuid(val):
    for key, value in uuid_opts.items():
        if val == value:
            return key
    return "key doesn't exist"

def get_nth_key(dictionary, n=0):
    print(dictionary)
    if n < 0:
        n += len(dictionary)
    for i, key in enumerate(dictionary.keys()):
        print(i)
        print(key)
        print(n)
        if i == n:
            return key
    raise IndexError("dictionary index out of range") 

def replace_plot(attr, old, new):
    for ref in pnl._models:
        _, _, doc, comm = pn.state._views[ref]
        doc.hold()
        pnl[0] = 1
        push(doc, comm)
    for ref in pnl._models:
        _, _, doc, comm = pn.state._views[ref]
        doc.unhold()

def help_callback(*args):
    #try:
    notifications.text  = helpText+notifications.text 


# In[ ]:


def getDataset(attr, old, new):
    global Viz, Tools
    print('getDataset: ')
    print(new)
    uuid_name =  new
    uuid = uuid_opts[uuid_name]

    if (uuid != old):
        notifications.text += '</br>Get New Dataset: '+uuid_name + ' ' + uuid
        print(notifications.text)

        myTitle = pn.pane.Markdown(f'''
        # ScientistCloud Explorer: {name}
        ''')
        myTitlePanel=pn.panel(myTitle, name='header')

        print('Displaying : ',uuid)
        print(server)
        if DATA_IS_LOCAL:
            dataset_path = f"{local_base_dir}/visus.idx"
            MicroCT = ov.LoadDataset(dataset_path)
        elif server=="false" or server=="%20false" or server==" false":
            dataset_path = f"/mnt/visus_datasets/converted/{uuid}/visus.idx"
            if os.path.exists(dataset_path):
                print(f"Path exists: {dataset_path}")
            else:
                print(f"Path does not exist: {dataset_path}")
            MicroCT = ov.LoadDataset(dataset_path)
        else:
            MicroCT=ov.LoadDataset(uuid)
        resolution_max =  MicroCT.getMaxResolution()
        resolution_slider.end = int(resolution_max)
        resolution_val= int(resolution_slider.value)
        if (resolution_val >resolution_max):
            resolution_val =  int(resolution_max)/3
        print(resolution_max)
        print(resolution_val)
        vol=MicroCT.read(max_resolution=resolution_val)
        print(f'Loaded volume with shape: {vol.shape}, resolution: {resolution_val}')
        
        # Update the global volume data
        global volume_data, volume_resolution, volume_update_counter
        volume_data = vol
        volume_resolution = resolution_val
        volume_update_counter += 1
        
        # Create new volume pane with updated data
        new_volume_pane = get_current_volume_pane()
        
        # Force page refresh with new resolution parameter
        try:
            print("🔄 Refreshing page with new resolution...")
            
            # Add notification with refresh link (preserve existing URL parameters)
            current_url = pn.state.location.href if hasattr(pn.state, 'location') else ""
            if current_url:
                # Add or update resolution parameter
                if 'resolution=' in current_url:
                    new_url = current_url.split('resolution=')[0] + f'resolution={resolution_val}'
                else:
                    separator = '&' if '?' in current_url else '?'
                    new_url = current_url + f'{separator}resolution={resolution_val}'
                notifications.text += f'</br>🔄 <a href="{new_url}" target="_self" style="background-color: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block;">Click to load resolution {resolution_val}</a>'
            else:
                notifications.text += f'</br>🔄 <a href="?resolution={resolution_val}" target="_self" style="background-color: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block;">Click to load resolution {resolution_val}</a>'
            
            print("✅ Page refresh mechanism added")
                
        except Exception as e:
            print(f"⚠️ Error setting up page refresh: {e}")
            print("🔄 Using fallback notification method...")
            
            # Fallback: Just show a notification with manual refresh instruction
            notifications.text += f'</br>🔄 Resolution changed to {resolution_val}. Please refresh the page to see the new volume.'
        
        # Add notification about the change
        notifications.text += f'</br>✅ Dataset loaded at resolution {resolution_val} (shape: {vol.shape})'
        
        print("✅ Dataset loaded - volume data updated")
        
        print("✅ Dataset loaded - volume data updated")
    #Viz
    return vol 


# In[ ]:


def reloadButtonF():
#     try:
    uuid_ref, uuid_names, uuid_opts = load_from_url()
    uuid_selection.options = uuid_names
    notifications.text += '</br> reload file with names: '+', '.join(uuid_names)


# In[ ]:


def volResolutionChange(attr, old, new):
    global Viz, Tools
    if (new != old):
        notifications.text += '</br> Resolution change to '+str(new)
        uuid_name =  str(uuid_selection.value)
        print(f"Resolution change: {old} -> {new}")
        uuid = uuid_opts[uuid_name]
        
        if DATA_IS_LOCAL:
            dataset_path = f"{local_base_dir}/visus.idx"
            MicroCT = ov.LoadDataset(dataset_path)
        elif server=="false" or server=="%20false" or server==" false":
            dataset_path = f"/mnt/visus_datasets/converted/{uuid}/visus.idx"
            if os.path.exists(dataset_path):
                print(f"Path exists: {dataset_path}")
            else:
                print(f"Path does not exist: {dataset_path}")
            MicroCT = ov.LoadDataset(dataset_path)
        else:
            MicroCT=ov.LoadDataset(uuid)

        resolution_max =  MicroCT.getMaxResolution()
        resolution_slider.end = int(resolution_max)
        resolution_val= int(resolution_slider.value)
        if (resolution_val >resolution_max):
            resolution_val =  int(resolution_max) /3
        print(f"Resolution max: {resolution_max}, using: {resolution_val}")

        vol=MicroCT.read(max_resolution=resolution_val)
        print(f'Loaded volume with shape: {vol.shape}')
        
        # Update the global volume data
        global volume_data, volume_resolution, volume_update_counter
        volume_data = vol
        volume_resolution = resolution_val
        volume_update_counter += 1
        
        # Create new volume pane with updated data
        new_volume_pane = get_current_volume_pane()
        
        # Force page refresh with new resolution parameter
        try:
            print("🔄 Refreshing page with new resolution...")
            
            # Add notification with refresh link (preserve existing URL parameters)
            current_url = pn.state.location.href if hasattr(pn.state, 'location') else ""
            if current_url:
                # Add or update resolution parameter
                if 'resolution=' in current_url:
                    new_url = current_url.split('resolution=')[0] + f'resolution={resolution_val}'
                else:
                    separator = '&' if '?' in current_url else '?'
                    new_url = current_url + f'{separator}resolution={resolution_val}'
                notifications.text += f'</br>🔄 <a href="{new_url}" target="_self" style="background-color: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block;">Click to load resolution {resolution_val}</a>'
            else:
                notifications.text += f'</br>🔄 <a href="?resolution={resolution_val}" target="_self" style="background-color: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block;">Click to load resolution {resolution_val}</a>'
            
            print("✅ Page refresh mechanism added")
                
        except Exception as e:
            print(f"⚠️ Error setting up page refresh: {e}")
            print("🔄 Using fallback notification method...")
            
            # Fallback: Just show a notification with manual refresh instruction
            notifications.text += f'</br>🔄 Resolution changed to {resolution_val}. Please refresh the page to see the new volume.'
        
        # Add notification about the change
        notifications.text += f'</br>✅ Volume updated to resolution {resolution_val} (shape: {vol.shape})'
        
        print("✅ Resolution change applied - volume data updated")
        
        print("✅ Resolution change applied - volume data updated")


# In[ ]:


##################### MAIN ####################

uuid_ref, uuid_names, uuid_opts = load_from_url()

# Get resolution from URL parameters if available
resolution_from_url = None
if not DATA_IS_LOCAL:
    try:
        request = curdoc().session_context.request if hasattr(curdoc(), 'session_context') and curdoc().session_context else None
        if request and request.arguments:
            resolution_from_url = request.arguments.get('resolution', [None])[0]
            if resolution_from_url:
                resolution_from_url = int(resolution_from_url)
                print(f"📊 Resolution from URL: {resolution_from_url}")
    except Exception as e:
        print(f"⚠️ Error reading resolution from URL: {e}")

max_resolution=40
resolution_slider = Slider(start=0, end=int(max_resolution), value=int(max_resolution/3), step=1, title="Resolution")

# Use resolution from URL if available
if resolution_from_url is not None:
    resolution_slider.value = resolution_from_url
    print(f"✅ Set slider value to {resolution_from_url} from URL")

uuid_name = get_nth_key(uuid_opts,0)
uuid = uuid_opts[uuid_name]

notifications.text += '</br> getDataset: ' +uuid_name + ' with uuid '+uuid
print(notifications.text)
myTitle = pn.pane.Markdown(f'''
# ScientistCloud Explorer: {name}
''')
myTitlePanel=pn.panel(myTitle, name='header')

print('Displaying : '+ uuid_name+ ' '+uuid)

#UPdate UI:
uuid_selection = Select(title="Dataset Selection", value=uuid_name, options=uuid_names )
uuid_selection.on_change("value", getDataset)
uuid_reload_button.on_click(reloadButtonF)
# ViSOARhelp_button.on_click(help_callback)
resolution_slider.on_change('value', volResolutionChange)

UI_INIT_DONE = True
if DATA_IS_LOCAL:
    dataset_path = f"{local_base_dir}/visus.idx"
    MicroCT = ov.LoadDataset(dataset_path)
elif server=='false' or server=="%20false" or server==" false":
    dataset_path = f"/mnt/visus_datasets/converted/{uuid}/visus.idx"
    if os.path.exists(dataset_path):
        print(f"Path exists: {dataset_path}")
    else:
        print(f"Path does not exist: {dataset_path}")
    MicroCT = ov.LoadDataset(dataset_path)
else:
    MicroCT=ov.LoadDataset(uuid)
resolution_max =  MicroCT.getMaxResolution()
resolution_slider.end = int(resolution_max)
resolution_val= int(resolution_slider.value)
if (resolution_val >resolution_max):
    resolution_val =  int(resolution_max)/3
print(resolution_max)
print(resolution_val)

vol=MicroCT.read(max_resolution=resolution_val)

# Initialize the volume data
volume_data = vol
volume_resolution = resolution_val
volume_update_counter = 0

# Create the initial volume pane
initial_volume = get_current_volume_pane()

# Create control widgets for the volume
volumeCtrls = initial_volume.controls(jslink=True, parameters=[
    'display_volume', 'display_slices',
    'slice_i', 'slice_j', 'slice_k', 'rescale'
])

# Create the initial layout
Tools = pn.Column( myTitlePanel, uuid_selection, uuid_reload_button, resolution_slider, volumeCtrls, notifications )
Viz = pn.Row( Tools, pn.Row( initial_volume, name=uuid_arg)).servable()


# In[ ]:


Viz

# Register cleanup function to run when application exits
import atexit
atexit.register(cleanup_mongodb)

# Add health check endpoint for Docker health checks
# Bokeh doesn't easily support adding routes at runtime, so we'll use a workaround:
# Create a simple health check by adding it to the document's server context
try:
    from tornado.web import RequestHandler
    import json
    from datetime import datetime
    
    # Create a health check handler
    class HealthHandler(RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({
                "status": "healthy",
                "service": "3DVTK Dashboard",
                "timestamp": datetime.now().isoformat()
            }))
    
    # Try to add the health endpoint to the Bokeh server
    # This needs to be done via the server's tornado application
    doc = curdoc()
    
    # Use a callback that runs after the server is fully initialized
    def add_health_route():
        try:
            # Access the server context and add the route
            if hasattr(doc, 'server_context') and doc.server_context:
                server_context = doc.server_context
                if hasattr(server_context, 'application'):
                    app = server_context.application
                    # Add the health endpoint route
                    # Note: Bokeh's tornado app uses a specific structure
                    # We need to add it to the handlers
                    if hasattr(app, '_handlers'):
                        # Add to existing handlers
                        app._handlers.append((r"/health", HealthHandler))
                        print("✅ Health endpoint added at /health")
                    elif hasattr(app, 'add_handlers'):
                        app.add_handlers(r".*", [(r"/health", HealthHandler)])
                        print("✅ Health endpoint added at /health")
        except Exception as e:
            print(f"⚠️ Could not add health endpoint: {e}")
            print("   Health checks may fail, but dashboard will still work")
    
    # Try to add immediately (may not work if server not ready)
    add_health_route()
    
    # Also try on next tick (after server is ready)
    from bokeh.io import curdoc as _curdoc
    _curdoc().add_next_tick_callback(add_health_route)
    
except Exception as e:
    print(f"⚠️ Error setting up health endpoint: {e}")
    print("   Health checks may fail, but dashboard will still work")

