import OpenVisus as ov
from dash import Dash, Input, Output, dcc, html, State
import os, sys
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"

import dash_vtk
from dash_vtk.utils import to_volume_state
import bokeh
import jwt
from urllib.parse import parse_qs, unquote
import numpy as np
import vtk
from vtk.util import numpy_support
from flask import Flask, redirect, request, jsonify

# Import shared MongoDB connection manager
from mongo_connection import get_mongo_client, close_all_connections

# load_dotenv(dotenv_path='.env')
key = os.getenv('SECRET_KEY')
deploy_server=os.getenv('DEPLOY_SERVER')
db_name=os.getenv('DB_NAME')

# Connect to MongoDB using shared connection manager
client = get_mongo_client()
mymongodb = client[db_name]
collection = mymongodb['visstoredatas']
collection1 = mymongodb['shared_user']
team_collection = mymongodb['teams']
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"

sys.path.append('/home/ViSOAR/dataportal/openvisuspy/src')

stored_uuid = None
stored_server = None
stored_name = None

def get_cookie(request, cookie_name):
    cookies = request.headers.get('Cookie')
    if cookies:
        for cookie in cookies.split(';'):
            key, value = cookie.split('=', 1)
            if key.strip() == cookie_name:
                return value.strip()
    return None

def numpy_to_vtk_image_data(numpy_array):    
    shape = numpy_array.shape
    image_data = vtk.vtkImageData()
    image_data.SetDimensions(shape)
    image_data.AllocateScalars(vtk.VTK_FLOAT, 1)
    flat_array = numpy_array.ravel(order='F')
    vtk_array = numpy_support.numpy_to_vtk(num_array=flat_array, deep=True, array_type=vtk.VTK_FLOAT)
    image_data.GetPointData().SetScalars(vtk_array)   
    return image_data

dataset_url = None
timesteps = None
server = Flask(__name__)
 

def get_params():
    global stored_uuid, stored_server, stored_name
    
    # Try Flask's built-in method first
    uuid = request.args.get('uuid')
    server = request.args.get('server')
    name = request.args.get('name')
    
    print(f"Flask args - uuid: {uuid}, server: {server}, name: {name}")
    
    # If we got valid parameters, store them
    if uuid and server and name:
        stored_uuid = uuid
        stored_server = server
        stored_name = name
        return uuid, server, name
    
    # If Flask args are empty, try environment method
    if not uuid or not server or not name:
        print("Flask args empty, trying environment method...")
        import urllib.parse
        from urllib.parse import unquote

        qs = os.environ.get('QUERY_STRING', '')
        print(f"Query string: {qs}")
        args = urllib.parse.parse_qs(qs)

        # Get parameters and decode them properly
        uuid = args.get('uuid', [''])[0]
        server = args.get('server', [''])[0]
        name = args.get('name', [''])[0]

        # Decode bytes to strings if needed
        if isinstance(uuid, bytes):
            uuid = uuid.decode('utf-8')
        if isinstance(server, bytes):
            server = server.decode('utf-8')
        if isinstance(name, bytes):
            name = name.decode('utf-8')

        # URL decode the parameters
        uuid = unquote(uuid)
        server = unquote(server)
        name = unquote(name)

        print(f'Environment method - uuid: {uuid} server:{server} name:{name}')
        
        # If we got valid parameters, store them
        if uuid and server and name:
            stored_uuid = uuid
            stored_server = server
            stored_name = name
            return uuid, server, name
    
    # If all else fails, return stored values
    if stored_uuid and stored_server and stored_name:
        print(f"Using stored values - uuid: {stored_uuid}, server: {stored_server}, name: {stored_name}")
        return stored_uuid, stored_server, stored_name
    
    # Handle empty or None values
    if not uuid:
        print("Warning: UUID parameter is missing or empty")
    if not server:
        print("Warning: Server parameter is missing or empty")
    if not name:
        print("Warning: Name parameter is missing or empty")
        
    return uuid, server, name

@server.route('/')
def index():
    auth_token = request.cookies.get('auth_token')
    uuid,server,name=get_params()
    
    print(f'Plotly Dashboard: Checking access for UUID: {uuid}, server: {server}, name: {name}')
    
    public_doc = collection.find_one({'$or': [{'uuid': uuid}, {'google_drive_link': uuid}], 'is_public': True})
    if server == 'true' or server=="%20true" or server==" true":
        document = collection.find_one({'uuid': uuid})
        if document and 'google_drive_link' in document:
            uuid = document['google_drive_link']
    
    if public_doc:
        print('Accessing public dataset')
        is_authorized=True
        # Don't close MongoDB connection here - it's needed for the app
        return app.index()
    
    print(f'Dataset is not public. Checking authentication...')
    print(f'Auth token present: {auth_token is not None}')
        
    if not auth_token:
        print('Token not found!')
        is_authorized=False
        return jsonify({'authorized': False})
    try:
        decoded = jwt.decode(auth_token, key, algorithms=["HS256"])
        user_email = decoded['user']
        user_with_uuid = collection.find_one({'$or': [{'uuid': uuid}, {'google_drive_link': uuid}], 'user': user_email})
        user_with_sharing = collection1.find_one({'$or': [{'uuid': uuid}, {'google_drive_link': uuid}], 'user': user_email})
  
        if user_with_uuid or user_with_sharing:
            print('User Authorized for this dataset')
            is_authorized=True
        else:
            teams = team_collection.find({'emails': user_email})
            team_names = [team['team_name'] for team in teams]

            shared_team = mymongodb['shared_team'].find_one({
                '$or': [{'uuid': uuid}, {'google_drive_link': uuid}],
                'team': {'$in': team_names}
            })
            is_authorized = shared_team is not None
            print(f'Is Authorized?: {is_authorized}')

    except Exception as e: 
        print(e)
        print('hit exception')
        is_authorized=False
    if is_authorized==False:
        return redirect(deploy_server)
    
    # Don't close MongoDB connection - it's needed for the app
    return app.index()  

app = Dash(__name__, server=server, routes_pathname_prefix='/plotly/', assets_url_path='/plotly/assets', requests_pathname_prefix="/plotly/")
app.config.suppress_callback_exceptions=True

@server.route('/check-auth')
def check_auth():

    auth_token = request.cookies.get('auth_token')
    uuid,server,name=get_params()
    
    print(f'Plotly Dashboard /check-auth: Checking access for UUID: {uuid}')
    
    public_doc = collection.find_one({'$or': [{'uuid': uuid}, {'google_drive_link': uuid}], 'is_public': True})
    if public_doc:
        print('Accessing public dataset')
        is_authorized=True
        
        return jsonify({'authorized': True})
    
    print(f'Dataset is not public. Checking authentication...')
    print(f'Auth token present: {auth_token is not None}')
    
    if not auth_token:
        print('Token not found!')
        return jsonify({'authorized': False})
    print('auth found')

    try:
        decoded = jwt.decode(auth_token, key, algorithms=["HS256"])
        print('decoded')
        user_email = decoded['user']
        user_with_uuid = collection.find_one({'$or': [{'uuid': uuid}, {'google_drive_link': uuid}], 'user': user_email})
        user_with_sharing = collection1.find_one({'$or': [{'uuid': uuid}, {'google_drive_link': uuid}], 'user': user_email})
  
        if user_with_uuid or user_with_sharing:
            print('User Authorized for this dataset')
            is_authorized=True
        else:
            teams = team_collection.find({'emails': user_email})
            team_names = [team['team_name'] for team in teams]

            shared_team = mymongodb['shared_team'].find_one({
                '$or': [{'uuid': uuid}, {'google_drive_link': uuid}],
                'team': {'$in': team_names}
            })
            is_authorized = shared_team is not None
    except Exception as e: 
        print(e)
        print('hit_exception')
        is_authorized=False
        return jsonify({'authorized': is_authorized})


# Global variables
dataset_url = None
timesteps = None

# Initialize layout dynamically
def serve_layout():
    global dataset_url, timesteps, stored_name
    if dataset_url and timesteps:
        db = ov.LoadDataset(dataset_url)
        dataset = db.read(time=timesteps[0], quality=-6)
        initial_volume_state = to_volume_state(numpy_to_vtk_image_data(dataset))

        return html.Div([
            html.H1(f'ScientistCloud Volume Rendering with Plotly: {stored_name} ', style={'textAlign': 'center', 'margin': '24px'}),
            dcc.Location(id='url', refresh=False),
            html.Div(style={"width": "100%", "height": "600px"}, children=[
                dash_vtk.View([
                    dash_vtk.VolumeRepresentation([
                        dash_vtk.VolumeController(),
                        dash_vtk.Volume(id='volume-rendering', state=initial_volume_state),
                    ]),
                ]),
            ]),
            html.Div([
                html.Label('Time'),
                dcc.Slider(
                    id='time-slider',
                    min=timesteps[0],
                    max=timesteps[-1],
                    value=timesteps[0],
                ),
                html.Label('Quality'),
                dcc.Slider(
                    id='quality-slider',
                    min=-10,
                    max=0,
                    value=-6,
                ),
            ]),
            html.Button('Info', id='info-button', n_clicks=0, style={'position': 'absolute', 'top': '10px', 'right': '10px'}),
            dcc.ConfirmDialog(
                id='info-dialog',
                message='',
            ),
            html.Div(id='info-output', style={'display': 'none'}),
        ])
    else:
        return html.Div("Loading...")

# Set the layout function
app.layout = html.Div("Initializing...")
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Interval(id='interval-component', interval=5*1000000, n_intervals=0),

    html.Div(id='dynamic-content', children=[
        html.Div(className='spinner'),  
        html.Div('Loading...', style={'marginTop': '10px'})
    ], style={'textAlign': 'center', 'margin': '24px'}),  

    html.Script('''
        function checkAuth() {
            fetch('/check-auth')
                .then(response => response.json())
                .then(data => {
                    if (!data.authorized) {
                        // Redirect to the login page if not authorized
                        window.location.href = '{deploy_server}}';
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        // Run the check immediately and then periodically
        checkAuth();
        setInterval(checkAuth, 5000); 
    ''')
])

@app.callback(
    Output('dynamic-content', 'children'),
    [Input('interval-component', 'n_intervals')],
    [State('url', 'search')],
)
def initialize_dataset(n_intervals,search):
    print('initialize_dataset triggered with search:', search)
    global dataset_url, timesteps
    query_params = parse_qs(unquote(search).lstrip('?'))
    uuid = query_params.get('uuid', [None])[0]
    server = query_params.get('server', [None])[0]
    name = query_params.get('name', [None])[0]
    
  

    if server and server.strip().lower() in ['true', '%20true', ' true']:
        document = collection.find_one({'uuid': uuid})
        if document and 'google_drive_link' in document:
            uuid = document['google_drive_link']
        print(f"Server is true, UUID modified to link: {uuid}")
    else:
        print(f"Server is not true, UUID remains: {uuid}")
    dataset_url=uuid
    if server=='true' or server=='%20true' or server==' true':
        print('loading server data...')
        db = ov.LoadDataset(dataset_url)
        timesteps = db.getTimesteps()
    if server=='false' or server=="%20false" or server ==' false':
        print('server false, dataset loading locally...')
        # Use host.docker.internal for Docker containers to access host localhost
        if deploy_server and 'localhost' in deploy_server:
            dataset_path = f"http://host.docker.internal/mod_visus?dataset={uuid}"
        else:
            dataset_path = f"{deploy_server}/mod_visus?dataset={uuid}"
        dataset_url=dataset_path
        if os.path.exists(dataset_path):
            print(f"Path exists: {dataset_path}")
        else:
            print(f"Path does not exist: {dataset_path}")
            dataset_url=f"/mnt/visus_datasets/converted/{uuid}/visus.idx"
            daataset_path = dataset_url
        db = ov.LoadDataset(dataset_path)
        timesteps = db.getTimesteps()
        print(timesteps)
    if dataset_url and timesteps:
        return serve_layout()
    else:
        return html.Div(
            style={'textAlign': 'center', 'margin': '24px'}, 
            children=[
                html.Div(style={
                    'border': '4px solid rgba(0, 0, 0, .1)',
                    'border-radius': '50%',
                    'border-top': '4px solid #007bff',
                    'width': '40px',
                    'height': '40px',
                    'animation': 'spin 2s linear infinite'
                }),
                html.Div('Loading...', style={'marginTop': '10px'})
            ]
        )

@app.callback(
    [Output('info-dialog', 'displayed'), Output('info-dialog', 'message')],
    [Input('info-button', 'n_clicks')],
    [State('url', 'search')]
)
def display_confirm(n_clicks, search):
    if n_clicks > 0:
        global dataset_url
        if dataset_url:
            query_params = parse_qs(unquote(search).lstrip('?'))
            name = query_params.get('name', [None])[0]
            db = ov.LoadDataset(dataset_url)
            dimensions = db.getLogicBox()
            timesteps = len(db.getTimesteps())
            info_text = f"URL: {dataset_url}\nName: {str(name)}\nDimensions: {str(dimensions[1])}\nNumber of Timesteps: {timesteps}"
            return True, info_text
    return False, ''



app.run(debug=True, port=8050,host='0.0.0.0') # Dont change the host here to 51.81..., its always LOCAL to the SERVER
