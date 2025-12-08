#!/usr/bin/env python3
"""
4D Dashboard Lite - Using SCLib_Dashboards Library

This is a simplified version of the 4D dashboard that uses the new
SCLib_Dashboards library components for cleaner, more maintainable code.

Features:
- Session Management: Save and load complete dashboard sessions
- Undo/Redo: Track and revert UI changes with full state history
- State Persistence: All plot configurations are saved and can be restored
- Change Logging: Export change logs for user experience analysis
- Library Integration: Uses SCLib_Dashboards for plots, UI, and state management
"""

import numpy as np
import os
import time
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Div
from bokeh.plotting import figure
from bokeh.models import (
    ColorBar,
    LinearColorMapper,
    LogColorMapper,
    LogScale,
    LinearScale,
)

# Import DashboardBuilder class will be done after SCLib_Dashboards import

# Import SCLib_Dashboards components
import sys
# Try multiple paths to find SCLib_Dashboards
current_dir = os.path.dirname(os.path.abspath(__file__))
found_sclib = False

# Define all paths to try
docker_path = os.path.join(current_dir, 'SCLib_Dashboards')
parent_docker_path = os.path.join(os.path.dirname(current_dir), 'SCLib_Dashboards')
lib_path = os.path.join(os.path.dirname(__file__), '../../..', 'scientistCloudLib')
alt_path = os.path.join(os.path.dirname(__file__), '../../../scientistCloudLib')
server_paths = [
    '/app/SCLib_Dashboards',
    '/var/www/scientistCloudLib/SCLib_Dashboards',
    '/home/ViSOAR/dataportal/scientistCloudLib/SCLib_Dashboards',
]

# 1. Check if it's in the same directory as the script (Docker: /app/SCLib_Dashboards)
if os.path.exists(docker_path) and os.path.isdir(docker_path):
    # Check if it's a proper Python package (has __init__.py or Python files)
    try:
        has_py_files = any(f.endswith('.py') for f in os.listdir(docker_path) if os.path.isfile(os.path.join(docker_path, f)))
        if os.path.exists(os.path.join(docker_path, '__init__.py')) or has_py_files:
            sys.path.insert(0, current_dir)
            print(f"✅ Found SCLib_Dashboards in Docker path: {docker_path}")
            found_sclib = True
    except Exception:
        pass

# 2. Check if SCLib_Dashboards directory exists in parent of current dir
if not found_sclib and os.path.exists(parent_docker_path) and os.path.isdir(parent_docker_path):
    try:
        has_py_files = any(f.endswith('.py') for f in os.listdir(parent_docker_path) if os.path.isfile(os.path.join(parent_docker_path, f)))
        if os.path.exists(os.path.join(parent_docker_path, '__init__.py')) or has_py_files:
            sys.path.insert(0, os.path.dirname(current_dir))
            print(f"✅ Found SCLib_Dashboards in parent Docker path: {parent_docker_path}")
            found_sclib = True
    except Exception:
        pass

# 3. Try relative path from current file (local development)
if not found_sclib and os.path.exists(lib_path):
    sys.path.insert(0, lib_path)
    print(f"✅ Found SCLib_Dashboards in local path: {lib_path}")
    found_sclib = True

# 4. Try alternative relative path
if not found_sclib and os.path.exists(alt_path):
    sys.path.insert(0, alt_path)
    print(f"✅ Found SCLib_Dashboards in alternative path: {alt_path}")
    found_sclib = True

# 5. Try absolute paths (server environment)
if not found_sclib:
    for server_path in server_paths:
        if os.path.exists(server_path) and os.path.isdir(server_path):
            sys.path.insert(0, os.path.dirname(server_path))
            print(f"✅ Found SCLib_Dashboards in server path: {server_path}")
            found_sclib = True
            break

if not found_sclib:
    print(f"⚠️ WARNING: SCLib_Dashboards not found in any expected location")
    print(f"   Tried paths:")
    print(f"     - {docker_path}")
    print(f"     - {parent_docker_path}")
    print(f"     - {lib_path}")
    print(f"     - {alt_path}")
    for server_path in server_paths:
        print(f"     - {server_path}")
    print(f"   Current working directory: {os.getcwd()}")
    print(f"   Script directory: {current_dir}")
    print(f"   Script file: {__file__}")
    print(f"   sys.path: {sys.path}")

# Import all SCLib_Dashboards components (all required - no fallbacks)
try:
    from SCLib_Dashboards import (
    # Data processors
    Process4dNexus,
    # Plot classes
    MAP_2DPlot,
    PROBE_2DPlot,
    PROBE_1DPlot,
    PlotSession,
    ColorScale,
    RangeMode,
    PlotShapeMode,
    # Undo/Redo (core functionality)
    StateHistory,
    PlotStateHistory,
    SessionStateHistory,
    create_undo_redo_callbacks,
    # Base UI components
    create_select,
    create_slider,
    create_button,
    create_toggle,
    create_text_input,
    create_radio_button_group,
    create_div,
    create_label_div,
    # Plot controls
    create_range_inputs,
    create_range_section,
    create_range_section_with_toggle,
    create_color_scale_selector,
    create_color_scale_section,
    create_palette_selector,
    create_palette_section,
    create_plot_shape_controls,
    create_range_mode_toggle,
    # Dataset selectors
    create_dataset_selection_group,
    create_coordinate_selection_group,
    create_optional_plot_toggle,
    extract_dataset_path,
    extract_shape,
    # Layout builders
    create_tools_column,
    create_plot_column,
    create_plots_row,
    create_dashboard_layout,
    create_status_display,
    create_initialization_layout,
    # State synchronization
    sync_all_plot_ui,
    sync_plot_to_range_inputs,
    sync_range_inputs_to_plot,
    sync_plot_to_color_scale_selector,
    sync_color_scale_selector_to_plot,
    sync_plot_to_palette_selector,
    sync_palette_selector_to_plot,
)
except ImportError as e:
    error_msg = f"""
    ❌ CRITICAL ERROR: Failed to import SCLib_Dashboards module!
    
    Error: {str(e)}
    
    This module is required for the dashboard to function.
    Please ensure SCLib_Dashboards is available in one of these locations:
    1. /app/SCLib_Dashboards (Docker container)
    2. Relative path from script: ../../scientistCloudLib/SCLib_Dashboards
    3. Server path: /var/www/scientistCloudLib/SCLib_Dashboards
    
    Current sys.path:
    {chr(10).join('  - ' + p for p in sys.path)}
    """
    print(error_msg)
    # Create a simple error display for Bokeh
    from bokeh.models import Div
    error_div = Div(text=f"<h2 style='color: red;'>Module Import Error</h2><pre>{error_msg}</pre>", width=800)
    from bokeh.io import curdoc
    try:
        curdoc().add_root(error_div)
    except:
        pass
    raise ImportError(f"SCLib_Dashboards module not found: {e}")

# Import utility functions (if available)
try:
    from utils_bokeh_dashboard import initialize_dashboard
    from utils_bokeh_mongodb import cleanup_mongodb
    from utils_bokeh_auth import authenticate_user
    from utils_bokeh_param import parse_url_parameters, setup_directory_paths
except ImportError:
    # Fallback for local development
    def initialize_dashboard(request, callback):
        return {'success': True, 'auth_result': {'is_authorized': True}, 'params': {}}
    def cleanup_mongodb():
        pass

# Global variables
uuid = None
server = None
save_dir = None
base_dir = None
is_authorized = False
user_email = None
status_messages = []

DOMAIN_NAME = os.getenv('DOMAIN_NAME', '')
DATA_IS_LOCAL = (DOMAIN_NAME == 'localhost' or DOMAIN_NAME == '' or DOMAIN_NAME is None)
local_base_dir = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil11/"


def add_status_message(message):
    """Add a status message to the collection"""
    global status_messages
    status_messages.append(message)
    print(f"📝 {message}")


def create_status_display_widget():
    """Create a status display widget"""
    global status_messages
    if not status_messages:
        return None
    
    status_text = "<h3>Status Messages:</h3><ul>"
    for msg in status_messages:
        status_text += f"<li>{msg}</li>"
    status_text += "</ul>"
    
    return create_div(text=status_text, width=800)


def find_nxs_files(directory):
    """Find all .nxs files in a directory"""
    print(f"🔍 DEBUG: find_nxs_files() called with directory: {directory}")
    if directory is None:
        print("❌ DEBUG: directory is None, returning empty list")
        return []
    
    if not os.path.exists(directory):
        print(f"❌ DEBUG: directory does not exist: {directory}")
        return []
    
    if not os.path.isdir(directory):
        print(f"❌ DEBUG: directory is not a directory: {directory}")
        return []
    
    print(f"🔍 DEBUG: Walking directory: {directory}")
    nxs_files = []
    walk_count = 0
    for root, dirs, files in os.walk(directory):
        walk_count += 1
        if walk_count <= 3:  # Only print first few directories
            print(f"🔍 DEBUG:   Checking directory: {root} ({len(files)} files)")
        for file in files:
            if file.endswith('.nxs'):
                full_path = os.path.join(root, file)
                nxs_files.append(full_path)
                if len(nxs_files) <= 5:  # Only print first few files
                    print(f"🔍 DEBUG:   Found .nxs file: {full_path}")
    
    print(f"✅ DEBUG: find_nxs_files() found {len(nxs_files)} .nxs files total")
    return nxs_files


def find_nexus_and_mmap_files():
    """Find nexus and memmap files"""
    global base_dir, save_dir
    
    print("=" * 80)
    print("🔍 DEBUG: find_nexus_and_mmap_files() called")
    print(f"🔍 DEBUG: base_dir = {base_dir}")
    print(f"🔍 DEBUG: save_dir = {save_dir}")
    
    if base_dir is None:
        print("❌ DEBUG: base_dir is None, returning None, None")
        return None, None
    
    print(f"🔍 DEBUG: Checking if base_dir exists: {os.path.exists(base_dir)}")
    if not os.path.exists(base_dir):
        print(f"❌ DEBUG: base_dir does not exist: {base_dir}")
    else:
        print(f"🔍 DEBUG: base_dir is a directory: {os.path.isdir(base_dir)}")
    
    nxs_files = find_nxs_files(base_dir)
    print(f"🔍 DEBUG: Found {len(nxs_files)} .nxs files in base_dir")
    if nxs_files:
        print(f"🔍 DEBUG: First few .nxs files: {nxs_files[:3]}")
    
    if len(nxs_files) > 0:
        nexus_filename = nxs_files[0]
        mmap_filename = nexus_filename.replace('.nxs', '.float32.dat')
        print(f"✅ DEBUG: Using nexus file from base_dir: {nexus_filename}")
        print(f"🔍 DEBUG: Corresponding mmap file: {mmap_filename}")
        print(f"🔍 DEBUG: Checking if nexus file exists: {os.path.exists(nexus_filename)}")
        print(f"🔍 DEBUG: Checking if mmap file exists: {os.path.exists(mmap_filename)}")
        return nexus_filename, mmap_filename
    else:
        print(f"🔍 DEBUG: No .nxs files in base_dir, checking save_dir: {save_dir}")
        if save_dir:
            print(f"🔍 DEBUG: Checking if save_dir exists: {os.path.exists(save_dir)}")
            nxs_files = find_nxs_files(save_dir)
            print(f"🔍 DEBUG: Found {len(nxs_files)} .nxs files in save_dir")
            if nxs_files:
                print(f"🔍 DEBUG: First few .nxs files: {nxs_files[:3]}")
            if len(nxs_files) > 0:
                nexus_filename = nxs_files[0]
                mmap_filename = nexus_filename.replace('.nxs', '.float32.dat')
                print(f"✅ DEBUG: Using nexus file from save_dir: {nexus_filename}")
                print(f"🔍 DEBUG: Corresponding mmap file: {mmap_filename}")
                print(f"🔍 DEBUG: Checking if nexus file exists: {os.path.exists(nexus_filename)}")
                print(f"🔍 DEBUG: Checking if mmap file exists: {os.path.exists(mmap_filename)}")
                return nexus_filename, mmap_filename
    
    print("❌ DEBUG: No .nxs files found in base_dir or save_dir")
    print("=" * 80)
    return None, None


def create_tmp_dashboard(process_4dnexus):
    """Create initial dashboard with dataset selectors using SCLib UI components."""
    global status_messages
    
    print("🔍 DEBUG: create_tmp_dashboard() called")
    print(f"🔍 DEBUG: process_4dnexus.choices_done = {getattr(process_4dnexus, 'choices_done', 'N/A')}")
    
    # Get dataset choices from process_4dnexus
    print("🔍 DEBUG: Getting datasets by dimension...")
    try:
        datasets_2d = process_4dnexus.get_datasets_by_dimension(2)
        print(f"🔍 DEBUG: Found {len(datasets_2d)} 2D datasets")
        datasets_3d = process_4dnexus.get_datasets_by_dimension(3)
        print(f"🔍 DEBUG: Found {len(datasets_3d)} 3D datasets")
        datasets_4d = process_4dnexus.get_datasets_by_dimension(4)
        print(f"🔍 DEBUG: Found {len(datasets_4d)} 4D datasets")
        datasets_1d = process_4dnexus.get_datasets_by_dimension(1)
        print(f"🔍 DEBUG: Found {len(datasets_1d)} 1D datasets")
    except Exception as e:
        import traceback
        print(f"❌ DEBUG: ERROR getting datasets by dimension: {e}")
        traceback.print_exc()
        raise
    
    # Create CSS style
    css_style = create_div(text="""
        <style>
        h3 {
            color: #5716e5 !important;
            font-size: 24px !important;
        }
        h2 {
            font-size: 28px !important;
        }
        body, p, div, span, label, select, input, button {
            font-size: 16px !important;
        }
        .bk-input, .bk-select {
            font-size: 16px !important;
        }
        </style>
    """)
    
    # Create choices for selectors with size information
    plot1_h5_choices = [f"{dataset['path']} {dataset['shape']}" for dataset in datasets_2d]
    plot2_h5_choices = [f"{dataset['path']} {dataset['shape']}" for dataset in datasets_4d + datasets_3d]
    coord_choices = [f"{dataset['path']} {dataset['shape']}" for dataset in datasets_1d]
    
    # Helper function to find a choice by path prefix
    def find_choice_by_path(choices, path_prefix):
        for choice in choices:
            if choice.startswith(path_prefix):
                return choice
        return None
    
    # Set default values - try to find postsample and presample by name pattern
    def find_choice_by_name_pattern(choices, pattern):
        """Find a choice that contains the pattern in its path."""
        for choice in choices:
            if pattern.lower() in choice.lower():
                return choice
        return None
    
    # First try exact path match for numerator (postsample)
    default_numerator = find_choice_by_path(plot1_h5_choices, "map_mi_sic_0p33mm_002/scalar_data/postsample_intensity")
    if not default_numerator:
        # Try to find any dataset with "postsample" in the name
        default_numerator = find_choice_by_name_pattern(plot1_h5_choices, "postsample")
    if not default_numerator:
        # Fallback to first choice
        default_numerator = plot1_h5_choices[0] if plot1_h5_choices else "No 2D datasets"
    
    # First try exact path match for denominator (presample)
    default_denominator = find_choice_by_path(plot1_h5_choices, "map_mi_sic_0p33mm_002/scalar_data/presample_intensity")
    if not default_denominator:
        # Try to find any dataset with "presample" in the name
        default_denominator = find_choice_by_name_pattern(plot1_h5_choices, "presample")
    if not default_denominator:
        # Fallback to a different choice than numerator
        if len(plot1_h5_choices) > 1:
            # Try to find a choice that's different from numerator
            default_denominator = None
            for choice in plot1_h5_choices:
                if choice != default_numerator:
                    default_denominator = choice
                    break
            # If we couldn't find a different choice, use the second one (or first if only one exists)
            if default_denominator is None or default_denominator == default_numerator:
                default_denominator = plot1_h5_choices[1] if len(plot1_h5_choices) > 1 else plot1_h5_choices[0] if plot1_h5_choices else "No 2D datasets"
        else:
            default_denominator = plot1_h5_choices[0] if plot1_h5_choices else "No 2D datasets"
    default_plot2 = find_choice_by_path(plot2_h5_choices, "map_mi_sic_0p33mm_002/data/PIL11") or (plot2_h5_choices[0] if plot2_h5_choices else "No 3D/4D datasets")
    default_map_x = find_choice_by_path(coord_choices, "map_mi_sic_0p33mm_002/data/samx") or "Use Default"
    default_map_y = find_choice_by_path(coord_choices, "map_mi_sic_0p33mm_002/data/samz") or "Use Default"
    
    # Create Plot1 dataset selection group using SCLib UI
    plot1_mode_selector, plot1_single_selector, plot1_numerator_selector, plot1_denominator_selector = \
        create_dataset_selection_group(
            plot_label="Plot1",
            dataset_choices=plot1_h5_choices,
            default_dataset=default_numerator,
            default_mode=1,  # Ratio mode
        )
    
    # Set denominator to presample (different from numerator which is postsample)
    if default_denominator and default_denominator in plot1_denominator_selector.options:
        plot1_denominator_selector.value = default_denominator
    
    # Create Plot2 dataset selector
    plot2_selector = create_select(
        title="Plot2 Dataset (3D/4D):",
        value=default_plot2,
        options=plot2_h5_choices if plot2_h5_choices else ["No 3D/4D datasets"],
        width=300
    )
    
    # Create coordinate selectors using SCLib UI
    map_x_selector, map_y_selector, probe_x_selector, probe_y_selector = \
        create_coordinate_selection_group(
            coord_choices=coord_choices,
            default_map_x=default_map_x,
            default_map_y=default_map_y,
        )
    
    # Optional Plot1B controls
    enable_plot1b_toggle = create_toggle(
        label="Enable Plot1B (duplicate map)",
        active=False,
        width=250
    )
    
    # Plot1B dataset selection group (similar to Plot1)
    plot1b_mode_selector, plot1b_single_selector, plot1b_numerator_selector, plot1b_denominator_selector = \
        create_dataset_selection_group(
            plot_label="Plot1B",
            dataset_choices=plot1_h5_choices,
            default_dataset=default_numerator,
            default_mode=1,  # Ratio mode
        )
    
    # Set Plot1B denominator to presample (different from numerator which is postsample)
    if default_denominator and default_denominator in plot1b_denominator_selector.options:
        plot1b_denominator_selector.value = default_denominator
    
    # Initially hide all Plot1B selectors
    enable_plot1b_toggle.visible = True  # Toggle is always visible
    plot1b_mode_selector.visible = False
    plot1b_single_selector.visible = False
    plot1b_numerator_selector.visible = False
    plot1b_denominator_selector.visible = False
    
    # Optional Plot2B controls
    enable_plot2b_toggle = create_toggle(
        label="Enable Plot2B (duplicate probe)",
        active=False,
        width=250
    )
    
    plot2b_selector = create_select(
        title="Plot2B Dataset (3D/4D):",
        value=default_plot2,
        options=plot2_h5_choices if plot2_h5_choices else ["No 3D/4D datasets"],
        width=300
    )
    plot2b_selector.visible = False
    
    # Plot2B coordinate selectors
    probe_x_selector_b = create_select(
        title="Probe2B X Coordinates (1D):",
        value="Use Default",
        options=["Use Default"] + coord_choices,
        width=300
    )
    probe_y_selector_b = create_select(
        title="Probe2B Y Coordinates (1D):",
        value="Use Default",
        options=["Use Default"] + coord_choices,
        width=300
    )
    probe_x_selector_b.visible = False
    probe_y_selector_b.visible = False
    
    # Create initialize button
    initialize_button = create_button(
        label="Initialize Plots",
        button_type="primary",
        width=200
    )
    
    # Create session selector and load button
    # First, get list of available sessions
    def get_available_sessions():
        """Get list of available session files."""
        try:
            from pathlib import Path
            import os
            
            if DATA_IS_LOCAL:
                save_dir_path = Path(local_base_dir)
            else:
                save_dir_path = Path(save_dir) if save_dir else Path(local_base_dir)
            
            sessions_dir = save_dir_path / "sessions"
            
            if not sessions_dir.exists():
                return [], []
            
            # Get all session files, sorted by modification time (newest first)
            session_files = sorted(sessions_dir.glob("session_*.json"), key=os.path.getmtime, reverse=True)
            
            # Create display names with timestamp
            from datetime import datetime
            import json
            session_choices = []
            for filepath in session_files:
                # Extract timestamp from filename or use modification time
                try:
                    with open(filepath, 'r') as f:
                        session_data = json.load(f)
                    metadata = session_data.get("metadata", {})
                    timestamp = metadata.get("last_updated") or metadata.get("created_at", "")
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            mtime = os.path.getmtime(filepath)
                            timestamp_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        mtime = os.path.getmtime(filepath)
                        timestamp_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    # Fallback to file modification time
                    mtime = os.path.getmtime(filepath)
                    timestamp_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                display_name = f"{filepath.name} ({timestamp_str})"
                session_choices.append(display_name)
            
            return session_choices, session_files
        except Exception as e:
            print(f"Error getting available sessions: {e}")
            return [], []
    
    # Session loading UI (matching real dashboard)
    session_choices, session_files_list = get_available_sessions()
    load_session_select = create_select(
        title="Load Session:",
        value=session_choices[0] if session_choices else "No sessions available",
        options=session_choices if session_choices else ["No sessions available"],
        width=350
    )
    
    # Store session files list (will be updated by refresh)
    session_files_refresh = session_files_list
    
    # Refresh sessions callback
    def on_refresh_sessions():
        """Refresh the list of available sessions."""
        nonlocal session_files_refresh
        session_choices_new, session_files_new = get_available_sessions()
        session_files_refresh = session_files_new
        if session_choices_new:
            load_session_select.options = session_choices_new
            load_session_select.value = session_choices_new[0] if session_choices_new else "No sessions available"
        else:
            load_session_select.options = ["No sessions available"]
            load_session_select.value = "No sessions available"
    
    # Create refresh and load buttons
    refresh_sessions_button = create_button(
        label="Refresh Sessions",
        button_type="default",
        width=150
    )
    
    load_session_button = create_button(
        label="Load Selected Session",
        button_type="primary",
        width=150
    )
    
    refresh_sessions_button.on_click(lambda: on_refresh_sessions())
    
    # Placeholder plots
    plot1_placeholder = create_div(
        text="<h3>Plot1: Select a 2D dataset above and click 'Initialize Plots'</h3>",
        width=400,
        height=300
    )
    plot2_placeholder = create_div(
        text="<h3>Plot2: Select a 3D/4D dataset above and click 'Initialize Plots'</h3>",
        width=400,
        height=300
    )
    
    # Initialize callback
    def initialize_plots_callback():
        """Callback for when user clicks 'Initialize Plots' button."""
        print("Initializing plots with selected datasets...")
        
        try:
            # Get selected datasets
            plot2_selection = plot2_selector.value
            plot2_path = extract_dataset_path(plot2_selection)
            
            if plot2_path == "No 3D/4D datasets":
                print("ERROR: Please select valid datasets before initializing plots")
                return
            
            process_4dnexus.volume_picked = plot2_path
            
            # Determine Plot1 selection based on mode
            if plot1_mode_selector.active == 0:  # Single dataset mode
                plot1_selection = plot1_single_selector.value
                plot1_path = extract_dataset_path(plot1_selection)
                if plot1_path == "No 2D datasets":
                    print("Please select valid datasets before initializing plots")
                    return
                process_4dnexus.plot1_single_dataset_picked = plot1_path
                process_4dnexus.presample_picked = None
                process_4dnexus.postsample_picked = None
            else:  # Ratio mode
                numerator_path = extract_dataset_path(plot1_numerator_selector.value)
                denominator_path = extract_dataset_path(plot1_denominator_selector.value)
                if numerator_path == "No 2D datasets" or denominator_path == "No 2D datasets":
                    print("Please select valid datasets for numerator and denominator")
                    return
                process_4dnexus.plot1_single_dataset_picked = None
                process_4dnexus.presample_picked = numerator_path
                process_4dnexus.postsample_picked = denominator_path
            
            # Set coordinates
            map_x_coords = extract_dataset_path(map_x_selector.value)
            map_y_coords = extract_dataset_path(map_y_selector.value)
            probe_x_coords = extract_dataset_path(probe_x_selector.value)
            probe_y_coords = extract_dataset_path(probe_y_selector.value)
            
            if map_x_coords != "Use Default":
                process_4dnexus.x_coords_picked = map_x_coords
            else:
                process_4dnexus.x_coords_picked = "map_mi_sic_0p33mm_002/data/samx"
                
            if map_y_coords != "Use Default":
                process_4dnexus.y_coords_picked = map_y_coords
            else:
                process_4dnexus.y_coords_picked = "map_mi_sic_0p33mm_002/data/samz"
            
            process_4dnexus.probe_x_coords_picked = probe_x_coords if probe_x_coords != "Use Default" else None
            process_4dnexus.probe_y_coords_picked = probe_y_coords if probe_y_coords != "Use Default" else None
            
            # Handle optional Plot1B
            if enable_plot1b_toggle.active:
                if plot1b_mode_selector.active == 0:  # Single dataset mode
                    plot1b_selection = plot1b_single_selector.value
                    plot1b_path = extract_dataset_path(plot1b_selection)
                    if plot1b_path != "No 2D datasets":
                        process_4dnexus.plot1b_single_dataset_picked = plot1b_path
                        process_4dnexus.presample_picked_b = None
                        process_4dnexus.postsample_picked_b = None
                else:  # Ratio mode
                    numerator_b_path = extract_dataset_path(plot1b_numerator_selector.value)
                    denominator_b_path = extract_dataset_path(plot1b_denominator_selector.value)
                    if numerator_b_path != "No 2D datasets" and denominator_b_path != "No 2D datasets":
                        process_4dnexus.plot1b_single_dataset_picked = None
                        process_4dnexus.presample_picked_b = numerator_b_path
                        process_4dnexus.postsample_picked_b = denominator_b_path
            else:
                process_4dnexus.plot1b_single_dataset_picked = None
                process_4dnexus.presample_picked_b = None
                process_4dnexus.postsample_picked_b = None
            
            # Handle optional Plot2B
            if enable_plot2b_toggle.active:
                plot2b_selection = plot2b_selector.value
                plot2b_path = extract_dataset_path(plot2b_selection)
                if plot2b_path != "No 3D/4D datasets":
                    process_4dnexus.volume_picked_b = plot2b_path
                    
                    probe_x_coords_b = extract_dataset_path(probe_x_selector_b.value)
                    probe_y_coords_b = extract_dataset_path(probe_y_selector_b.value)
                    process_4dnexus.probe_x_coords_picked_b = probe_x_coords_b if probe_x_coords_b != "Use Default" else None
                    process_4dnexus.probe_y_coords_picked_b = probe_y_coords_b if probe_y_coords_b != "Use Default" else None
            else:
                process_4dnexus.volume_picked_b = None
                process_4dnexus.probe_x_coords_picked_b = None
                process_4dnexus.probe_y_coords_picked_b = None
            
            print("=" * 80)
            print("🔍 DEBUG: User Settings from tmp_dashboard:")
            print("=" * 80)
            print(f"  Plot1 Mode: {'Single Dataset' if plot1_mode_selector.active == 0 else 'Ratio'}")
            if plot1_mode_selector.active == 0:
                print(f"    Plot1 Single Dataset: {plot1_path}")
            else:
                print(f"    Plot1 Numerator: {numerator_path}")
                print(f"    Plot1 Denominator: {denominator_path}")
            print(f"  Plot2 Dataset: {plot2_path}")
            print(f"  Map X Coordinates: {map_x_coords}")
            print(f"  Map Y Coordinates: {map_y_coords}")
            print(f"  Probe X Coordinates: {probe_x_coords if probe_x_coords != 'Use Default' else 'None (Use Default)'}")
            print(f"  Probe Y Coordinates: {probe_y_coords if probe_y_coords != 'Use Default' else 'None (Use Default)'}")
            print(f"  Plot1B Enabled: {enable_plot1b_toggle.active}")
            if enable_plot1b_toggle.active:
                print(f"    Plot1B Mode: {'Single Dataset' if plot1b_mode_selector.active == 0 else 'Ratio'}")
                if plot1b_mode_selector.active == 0:
                    print(f"    Plot1B Single Dataset: {plot1b_path if 'plot1b_path' in locals() else 'N/A'}")
                else:
                    print(f"    Plot1B Numerator: {numerator_b_path if 'numerator_b_path' in locals() else 'N/A'}")
                    print(f"    Plot1B Denominator: {denominator_b_path if 'denominator_b_path' in locals() else 'N/A'}")
            print(f"  Plot2B Enabled: {enable_plot2b_toggle.active}")
            if enable_plot2b_toggle.active:
                print(f"    Plot2B Dataset: {plot2b_path}")
                print(f"    Plot2B Probe X Coordinates: {probe_x_coords_b if probe_x_coords_b != 'Use Default' else 'None (Use Default)'}")
                print(f"    Plot2B Probe Y Coordinates: {probe_y_coords_b if probe_y_coords_b != 'Use Default' else 'None (Use Default)'}")
            print("=" * 80)
            print("🔍 DEBUG: process_4dnexus settings after initialization:")
            print(f"  volume_picked: {process_4dnexus.volume_picked}")
            print(f"  plot1_single_dataset_picked: {process_4dnexus.plot1_single_dataset_picked}")
            print(f"  presample_picked: {process_4dnexus.presample_picked}")
            print(f"  postsample_picked: {process_4dnexus.postsample_picked}")
            print(f"  x_coords_picked: {process_4dnexus.x_coords_picked}")
            print(f"  y_coords_picked: {process_4dnexus.y_coords_picked}")
            print(f"  probe_x_coords_picked: {process_4dnexus.probe_x_coords_picked}")
            print(f"  probe_y_coords_picked: {process_4dnexus.probe_y_coords_picked}")
            print(f"  volume_picked_b: {process_4dnexus.volume_picked_b}")
            print(f"  plot1b_single_dataset_picked: {process_4dnexus.plot1b_single_dataset_picked}")
            print(f"  presample_picked_b: {process_4dnexus.presample_picked_b}")
            print(f"  postsample_picked_b: {process_4dnexus.postsample_picked_b}")
            print(f"  probe_x_coords_picked_b: {process_4dnexus.probe_x_coords_picked_b}")
            print(f"  probe_y_coords_picked_b: {process_4dnexus.probe_y_coords_picked_b}")
            print("=" * 80)
            
            # Build and swap to full dashboard
            from bokeh.io import curdoc as _curdoc
            loading = column(create_div(text="<h3>Loading full dashboard...</h3>"))
            _curdoc().clear()
            _curdoc().add_root(loading)
            
            def _build_and_swap():
                try:
                    full_dashboard = create_dashboard(process_4dnexus)
                    _curdoc().clear()
                    _curdoc().add_root(full_dashboard)
                except Exception as e:
                    import traceback
                    error_msg = f"Error creating dashboard: {str(e)}"
                    print(error_msg)
                    traceback.print_exc()
                    error_div = create_div(
                        text=f"<h3 style='color: red;'>Error Creating Dashboard</h3><p>{error_msg}</p><pre>{traceback.format_exc()}</pre>",
                        width=800
                    )
                    _curdoc().clear()
                    _curdoc().add_root(error_div)
            
            _curdoc().add_next_tick_callback(_build_and_swap)
            
        except Exception as e:
            import traceback
            error_msg = f"Error initializing plots: {str(e)}"
            print(error_msg)
            traceback.print_exc()
    
    initialize_button.on_click(initialize_plots_callback)
    
    # Load session callback
    def on_load_session():
        """Load selected session from file, restore dataset paths, and transition to real dashboard."""
        try:
            print("🔍 DEBUG: on_load_session() called")
            from pathlib import Path
            import os
            import json
            from datetime import datetime
            
            # Get selected session
            selected_session = load_session_select.value
            print(f"🔍 DEBUG: Selected session: {selected_session}")
            
            if not selected_session or selected_session == "No sessions available" or selected_session.startswith("No ") or selected_session.startswith("Error:"):
                status_display.text = "<span style='color: orange;'>Please select a valid session to load</span>"
                print("⚠️ DEBUG: No valid session selected")
                return
            
            # Refresh session list to ensure we have current files
            nonlocal session_files_refresh
            session_choices_refresh, session_files_refresh = get_available_sessions()
            
            if not session_files_refresh:
                status_display.text = "<span style='color: orange;'>No session files found. Please refresh.</span>"
                return
            
            # Extract filename from display name (format: "session_xxx.json (timestamp)")
            session_filename = selected_session.split(" (")[0] if " (" in selected_session else selected_session
            
            # Match selected filename to filepath
            filepath = None
            for fpath in session_files_refresh:
                if fpath.name == session_filename:
                    filepath = fpath
                    break
            
            # Fallback: try matching by index if filename match fails
            if filepath is None:
                for i, choice in enumerate(session_choices_refresh):
                    if choice == selected_session:
                        if i < len(session_files_refresh):
                            filepath = session_files_refresh[i]
                            break
            
            if filepath is None or not filepath.exists():
                status_display.text = f"<span style='color: red;'>Session file not found: {session_filename}</span>"
                print(f"❌ DEBUG: Could not find session file. Selected: {selected_session}, Filename: {session_filename}")
                return
            
            print(f"✅ DEBUG: Found session file: {filepath}")
            
            # Read session file to extract metadata (dataset paths)
            with open(filepath, 'r') as f:
                session_data = json.load(f)
            
            # Extract metadata which contains dataset paths
            metadata = session_data.get("metadata", {})
            print(f"🔍 DEBUG: Session metadata keys: {list(metadata.keys())}")
            
            # CRITICAL: Restore dataset paths to process_4dnexus BEFORE transitioning to dashboard
            # This ensures the correct data is loaded when the dashboard is created
            if metadata:
                # Restore main volume and Plot1 datasets
                if "volume_picked" in metadata and metadata["volume_picked"]:
                    process_4dnexus.volume_picked = metadata["volume_picked"]
                    print(f"✅ Restored volume_picked: {metadata['volume_picked']}")
                
                if "plot1_single_dataset_picked" in metadata:
                    process_4dnexus.plot1_single_dataset_picked = metadata["plot1_single_dataset_picked"]
                    print(f"✅ Restored plot1_single_dataset_picked: {metadata.get('plot1_single_dataset_picked')}")
                
                if "presample_picked" in metadata:
                    process_4dnexus.presample_picked = metadata["presample_picked"]
                    print(f"✅ Restored presample_picked: {metadata.get('presample_picked')}")
                
                if "postsample_picked" in metadata:
                    process_4dnexus.postsample_picked = metadata["postsample_picked"]
                    print(f"✅ Restored postsample_picked: {metadata.get('postsample_picked')}")
                
                # Restore coordinate datasets
                if "x_coords_picked" in metadata:
                    process_4dnexus.x_coords_picked = metadata["x_coords_picked"]
                    print(f"✅ Restored x_coords_picked: {metadata.get('x_coords_picked')}")
                
                if "y_coords_picked" in metadata:
                    process_4dnexus.y_coords_picked = metadata["y_coords_picked"]
                    print(f"✅ Restored y_coords_picked: {metadata.get('y_coords_picked')}")
                
                if "probe_x_coords_picked" in metadata:
                    process_4dnexus.probe_x_coords_picked = metadata["probe_x_coords_picked"]
                    print(f"✅ Restored probe_x_coords_picked: {metadata.get('probe_x_coords_picked')}")
                
                if "probe_y_coords_picked" in metadata:
                    process_4dnexus.probe_y_coords_picked = metadata["probe_y_coords_picked"]
                    print(f"✅ Restored probe_y_coords_picked: {metadata.get('probe_y_coords_picked')}")
                
                # Restore Plot1B and Plot2B datasets
                if "volume_picked_b" in metadata:
                    process_4dnexus.volume_picked_b = metadata["volume_picked_b"]
                    print(f"✅ Restored volume_picked_b: {metadata.get('volume_picked_b')}")
                
                if "plot1b_single_dataset_picked" in metadata:
                    process_4dnexus.plot1b_single_dataset_picked = metadata["plot1b_single_dataset_picked"]
                    print(f"✅ Restored plot1b_single_dataset_picked: {metadata.get('plot1b_single_dataset_picked')}")
                
                if "presample_picked_b" in metadata:
                    process_4dnexus.presample_picked_b = metadata["presample_picked_b"]
                    print(f"✅ Restored presample_picked_b: {metadata.get('presample_picked_b')}")
                
                if "postsample_picked_b" in metadata:
                    process_4dnexus.postsample_picked_b = metadata["postsample_picked_b"]
                    print(f"✅ Restored postsample_picked_b: {metadata.get('postsample_picked_b')}")
                
                if "probe_x_coords_picked_b" in metadata:
                    process_4dnexus.probe_x_coords_picked_b = metadata["probe_x_coords_picked_b"]
                    print(f"✅ Restored probe_x_coords_picked_b: {metadata.get('probe_x_coords_picked_b')}")
                
                if "probe_y_coords_picked_b" in metadata:
                    process_4dnexus.probe_y_coords_picked_b = metadata["probe_y_coords_picked_b"]
                    print(f"✅ Restored probe_y_coords_picked_b: {metadata.get('probe_y_coords_picked_b')}")
            
            # Store the session filepath for the dashboard to load
            # We'll pass this to the dashboard so it can load the session after creating the dashboard
            process_4dnexus._session_filepath_to_load = filepath
            
            # Transition to real dashboard (similar to initialize_plots_callback)
            from bokeh.io import curdoc as _curdoc
            loading = column(create_div(text="<h3>Loading dashboard with session...</h3>"))
            _curdoc().clear()
            _curdoc().add_root(loading)
            
            def _build_and_swap():
                try:
                    # Don't delete _session_filepath_to_load here - let create_dashboard() handle it
                    # create_dashboard() will check for it at the end and auto-load the session
                    full_dashboard = create_dashboard(process_4dnexus)
                    _curdoc().clear()
                    _curdoc().add_root(full_dashboard)
                    
                    # Session loading is now handled automatically by create_dashboard() via auto_load_session()
                    # The _session_filepath_to_load attribute is deleted inside create_dashboard() after it's used
                    print(f"✅ Dashboard created - session will be auto-loaded if present")
                except Exception as e:
                    import traceback
                    error_msg = f"Error creating dashboard: {str(e)}"
                    print(error_msg)
                    traceback.print_exc()
                    error_div = create_div(
                        text=f"<h3 style='color: red;'>Error Creating Dashboard</h3><p>{error_msg}</p><pre>{traceback.format_exc()}</pre>",
                        width=800
                    )
                    _curdoc().clear()
                    _curdoc().add_root(error_div)
            
            _curdoc().add_next_tick_callback(_build_and_swap)
            
            print(f"✅ Session paths restored, transitioning to dashboard...")
        except Exception as e:
            import traceback
            error_msg = f"Error loading session: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            status_display.text = f"<span style='color: red;'>{error_msg}</span>"
    
    load_session_button.on_click(on_load_session)
    
    # Set initial visibility for Plot1 selectors
    plot1_single_selector.visible = False
    plot1_numerator_selector.visible = True
    plot1_denominator_selector.visible = True
    
    # Mode change callback
    def on_mode_change(attr, old, new):
        if new == 0:  # Single dataset mode
            plot1_single_selector.visible = True
            plot1_numerator_selector.visible = False
            plot1_denominator_selector.visible = False
        else:  # Ratio mode
            plot1_single_selector.visible = False
            plot1_numerator_selector.visible = True
            plot1_denominator_selector.visible = True
    
    plot1_mode_selector.on_change("active", on_mode_change)
    
    # Plot1B enable/disable callback
    def on_enable_plot1b(attr, old, new):
        plot1b_mode_selector.visible = new
        if new:
            # Show selectors based on current mode
            if plot1b_mode_selector.active == 0:  # Single dataset mode
                plot1b_single_selector.visible = True
                plot1b_numerator_selector.visible = False
                plot1b_denominator_selector.visible = False
            else:  # Ratio mode
                plot1b_single_selector.visible = False
                plot1b_numerator_selector.visible = True
                plot1b_denominator_selector.visible = True
        else:
            plot1b_single_selector.visible = False
            plot1b_numerator_selector.visible = False
            plot1b_denominator_selector.visible = False
    
    # Plot1B mode change callback
    def on_plot1b_mode_change(attr, old, new):
        if enable_plot1b_toggle.active:
            if new == 0:  # Single dataset mode
                plot1b_single_selector.visible = True
                plot1b_numerator_selector.visible = False
                plot1b_denominator_selector.visible = False
            else:  # Ratio mode
                plot1b_single_selector.visible = False
                plot1b_numerator_selector.visible = True
                plot1b_denominator_selector.visible = True
    
    enable_plot1b_toggle.on_change("active", on_enable_plot1b)
    plot1b_mode_selector.on_change("active", on_plot1b_mode_change)
    
    # Plot2B enable/disable callback
    def on_enable_plot2b(attr, old, new):
        plot2b_selector.visible = new
        probe_x_selector_b.visible = new
        probe_y_selector_b.visible = new
    
    enable_plot2b_toggle.on_change("active", on_enable_plot2b)
    
    # Callback to auto-populate Map coordinates when Plot1 dataset is selected
    def on_plot1_single_dataset_change(attr, old, new):
        """Auto-populate Map X/Y when Plot1 single dataset is selected."""
        if plot1_mode_selector.active == 0:  # Single dataset mode
            plot1_shape = extract_shape(new)
            if plot1_shape:
                map_x_choice, map_y_choice = process_4dnexus.auto_populate_map_coords(plot1_shape)
                if map_x_choice and map_x_choice in map_x_selector.options:
                    map_x_selector.value = map_x_choice
                if map_y_choice and map_y_choice in map_y_selector.options:
                    map_y_selector.value = map_y_choice
    
    def on_plot1_numerator_change(attr, old, new):
        """Auto-populate Map X/Y when Plot1 numerator is selected."""
        if plot1_mode_selector.active == 1:  # Ratio mode
            plot1_shape = extract_shape(new)
            if plot1_shape:
                map_x_choice, map_y_choice = process_4dnexus.auto_populate_map_coords(plot1_shape)
                if map_x_choice and map_x_choice in map_x_selector.options:
                    map_x_selector.value = map_x_choice
                if map_y_choice and map_y_choice in map_y_selector.options:
                    map_y_selector.value = map_y_choice
    
    def on_plot1_denominator_change(attr, old, new):
        """Auto-populate Map X/Y when Plot1 denominator is selected."""
        if plot1_mode_selector.active == 1:  # Ratio mode
            plot1_shape = extract_shape(new)
            if plot1_shape:
                map_x_choice, map_y_choice = process_4dnexus.auto_populate_map_coords(plot1_shape)
                if map_x_choice and map_x_choice in map_x_selector.options:
                    map_x_selector.value = map_x_choice
                if map_y_choice and map_y_choice in map_y_selector.options:
                    map_y_selector.value = map_y_choice
    
    # Attach callbacks for Plot1
    plot1_single_selector.on_change("value", on_plot1_single_dataset_change)
    plot1_numerator_selector.on_change("value", on_plot1_numerator_change)
    plot1_denominator_selector.on_change("value", on_plot1_denominator_change)
    
    # Callback to auto-populate Probe coordinates when Plot2 dataset is selected
    def on_plot2_dataset_change(attr, old, new):
        """Auto-populate Probe X/Y when Plot2 dataset is selected."""
        plot2_path = extract_dataset_path(new)
        if plot2_path == "No 3D/4D datasets":
            return
        plot2_shape = extract_shape(new)
        if plot2_shape:
            probe_x_choice, probe_y_choice = process_4dnexus.auto_populate_probe_coords(plot2_path, plot2_shape)
            if probe_x_choice and probe_x_choice in probe_x_selector.options:
                probe_x_selector.value = probe_x_choice
            if probe_y_choice and probe_y_choice in probe_y_selector.options:
                probe_y_selector.value = probe_y_choice
                probe_y_selector.visible = True
            elif probe_y_choice is None and len(plot2_shape) == 3:
                # 3D dataset - hide Probe Y
                probe_y_selector.visible = False
            elif len(plot2_shape) == 4:
                # 4D dataset - show Probe Y
                probe_y_selector.visible = True
    
    # Attach callback for Plot2
    plot2_selector.on_change("value", on_plot2_dataset_change)
    
    # Callback to auto-populate Probe coordinates when Plot2B dataset is selected
    def on_plot2b_dataset_change(attr, old, new):
        """Auto-populate Probe2B X/Y when Plot2B dataset is selected."""
        plot2b_path = extract_dataset_path(new)
        if plot2b_path == "No 3D/4D datasets":
            return
        plot2b_shape = extract_shape(new)
        if plot2b_shape:
            probe_x_choice, probe_y_choice = process_4dnexus.auto_populate_probe_coords(plot2b_path, plot2b_shape)
            if probe_x_choice and probe_x_choice in probe_x_selector_b.options:
                probe_x_selector_b.value = probe_x_choice
            if probe_y_choice and probe_y_choice in probe_y_selector_b.options:
                probe_y_selector_b.value = probe_y_choice
                probe_y_selector_b.visible = True
            elif probe_y_choice is None and len(plot2b_shape) == 3:
                # 3D dataset - hide Probe Y
                probe_y_selector_b.visible = False
            elif len(plot2b_shape) == 4:
                # 4D dataset - show Probe Y
                probe_y_selector_b.visible = True
    
    # Attach callback for Plot2B
    plot2b_selector.on_change("value", on_plot2b_dataset_change)
    
    # Callbacks for Plot1B auto-population
    def on_plot1b_dataset_change(attr, old, new):
        """Auto-populate Map X/Y when Plot1B dataset is selected (uses same coordinates as Plot1)."""
        if plot1b_mode_selector.active == 0:  # Single dataset mode
            plot1b_shape = extract_shape(new)
            if plot1b_shape:
                map_x_choice, map_y_choice = process_4dnexus.auto_populate_map_coords(plot1b_shape)
                if map_x_choice and map_x_choice in map_x_selector.options:
                    map_x_selector.value = map_x_choice
                if map_y_choice and map_y_choice in map_y_selector.options:
                    map_y_selector.value = map_y_choice
    
    def on_plot1b_numerator_change(attr, old, new):
        """Auto-populate Map X/Y when Plot1B numerator is selected."""
        if plot1b_mode_selector.active == 1:  # Ratio mode
            plot1b_shape = extract_shape(new)
            if plot1b_shape:
                map_x_choice, map_y_choice = process_4dnexus.auto_populate_map_coords(plot1b_shape)
                if map_x_choice and map_x_choice in map_x_selector.options:
                    map_x_selector.value = map_x_choice
                if map_y_choice and map_y_choice in map_y_selector.options:
                    map_y_selector.value = map_y_choice
    
    def on_plot1b_denominator_change(attr, old, new):
        """Auto-populate Map X/Y when Plot1B denominator is selected."""
        if plot1b_mode_selector.active == 1:  # Ratio mode
            plot1b_shape = extract_shape(new)
            if plot1b_shape:
                map_x_choice, map_y_choice = process_4dnexus.auto_populate_map_coords(plot1b_shape)
                if map_x_choice and map_x_choice in map_x_selector.options:
                    map_x_selector.value = map_x_choice
                if map_y_choice and map_y_choice in map_y_selector.options:
                    map_y_selector.value = map_y_choice
    
    # Attach callbacks for Plot1B
    plot1b_single_selector.on_change("value", on_plot1b_dataset_change)
    plot1b_numerator_selector.on_change("value", on_plot1b_numerator_change)
    plot1b_denominator_selector.on_change("value", on_plot1b_denominator_change)
    
    # Create layout using SCLib layout builders
    plot1_section = column(
        create_label_div("Plot1 Configuration:", width=300),
        plot1_mode_selector,
        plot1_single_selector,
        plot1_numerator_selector,
        plot1_denominator_selector,
        map_x_selector,
        map_y_selector,
        create_div(text="<hr>", width=300),
        create_label_div("Optional Plot1B (duplicate map):", width=300),
        enable_plot1b_toggle,
        plot1b_mode_selector,
        plot1b_single_selector,
        plot1b_numerator_selector,
        plot1b_denominator_selector,
    )
    
    plot2_section = column(
        create_label_div("Plot2 Configuration:", width=300),
        plot2_selector,
        probe_x_selector,
        probe_y_selector,
        create_div(text="<hr>", width=300),
        create_label_div("Optional Plot2B (duplicate probe):", width=300),
        enable_plot2b_toggle,
        plot2b_selector,
        probe_x_selector_b,
        probe_y_selector_b,
        create_div(text="<hr>", width=300),
        create_label_div("Load Session:", width=300),
        load_session_select,
        row(refresh_sessions_button, load_session_button),
        create_div(text="<hr>", width=300),
        initialize_button,
    )
    
    status_display = create_status_display_widget()
    
    main_layout = create_initialization_layout(
        title="4D Dashboard - Dataset Selection",
        plot1_section=plot1_section,
        plot2_section=plot2_section,
        initialize_button=initialize_button,
        status_display=status_display
    )
    
    return column(css_style, main_layout)


def create_dashboard(process_4dnexus):
    """
    Create the full dashboard using SCLib components with session management and undo/redo.
    
    This function now uses the DashboardBuilder class to break down the massive
    function into smaller, manageable methods.
    """
    # Import DashboardBuilder using importlib to avoid parsing issues
    import sys
    import os
    import importlib.util
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    if _current_dir not in sys.path:
        sys.path.insert(0, _current_dir)
    
    # Dynamically import DashboardBuilder
    builder_file = os.path.join(_current_dir, '4d_dashboard_builder.py')
    if os.path.exists(builder_file):
        spec = importlib.util.spec_from_file_location("dashboard_builder", builder_file)
        builder_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder_module)
        DashboardBuilder = builder_module.DashboardBuilder
    else:
        raise ImportError(f"DashboardBuilder file not found: {builder_file}")
    
    # Use the new DashboardBuilder
    builder = DashboardBuilder(process_4dnexus)
    return builder.build()
def scientistCloudInitDashboard():
    """Initialize the dashboard."""
    global status_messages, curdoc, request, has_args
    global DATA_IS_LOCAL, uuid, server, name, is_authorized, auth_result
    global base_dir, save_dir, user_email
    
    print("=" * 80)
    print("🔍 DEBUG: scientistCloudInitDashboard() called")
    print("=" * 80)
    
    status_messages = []
    doc = curdoc()
    print(f"🔍 DEBUG: Got curdoc(): {doc}")
    
    # Check if running with URL arguments
    request = doc.session_context.request if hasattr(doc, 'session_context') and doc.session_context else None
    print(f"🔍 DEBUG: request = {request}")
    if request:
        print(f"🔍 DEBUG: request.arguments = {request.arguments}")
        print(f"🔍 DEBUG: request.url = {getattr(request, 'url', 'N/A')}")
        print(f"🔍 DEBUG: request.path = {getattr(request, 'path', 'N/A')}")
    
    has_args = request and request.arguments and len(request.arguments) > 0
    print(f"🔍 DEBUG: has_args = {has_args}")
    DATA_IS_LOCAL = not has_args
    print(f"🔍 DEBUG: DATA_IS_LOCAL = {DATA_IS_LOCAL}")
    print(f"🔍 DEBUG: local_base_dir = {local_base_dir}")
    
    # Initialize dashboard using utility
    print("🔍 DEBUG: Calling initialize_dashboard()...")
    init_result = initialize_dashboard(request, add_status_message)
    print(f"🔍 DEBUG: init_result = {init_result}")
    
    if not init_result['success']:
        error_msg = init_result.get('error', 'Unknown error')
        print(f"❌ DEBUG: Dashboard initialization failed: {error_msg}")
        add_status_message(f"❌ Dashboard initialization failed: {error_msg}")
        return
    
    if DATA_IS_LOCAL:
        save_dir = local_base_dir
        base_dir = local_base_dir
        print(f"🔍 DEBUG: Using LOCAL mode")
        print(f"🔍 DEBUG: save_dir = {save_dir}")
        print(f"🔍 DEBUG: base_dir = {base_dir}")
        print(f"🔍 DEBUG: Checking if base_dir exists: {os.path.exists(base_dir) if base_dir else False}")
        if base_dir and os.path.exists(base_dir):
            print(f"🔍 DEBUG: base_dir contents: {os.listdir(base_dir)[:10] if os.path.isdir(base_dir) else 'Not a directory'}")
    else:
        print(f"🔍 DEBUG: Using REMOTE mode")
        auth_result = init_result['auth_result']
        params = init_result['params']
        uuid = params.get('uuid', 'N/A')
        server = params.get('server', 'N/A')
        name = params.get('name', 'N/A')
        save_dir = params.get('save_dir', 'N/A')
        base_dir = params.get('base_dir', 'N/A')
        is_authorized = auth_result.get('is_authorized', False)
        user_email = auth_result.get('user_email', 'N/A')
        
        print(f"🔍 DEBUG: uuid = {uuid}")
        print(f"🔍 DEBUG: server = {server}")
        print(f"🔍 DEBUG: name = {name}")
        print(f"🔍 DEBUG: save_dir = {save_dir}")
        print(f"🔍 DEBUG: base_dir = {base_dir}")
        print(f"🔍 DEBUG: is_authorized = {is_authorized}")
        print(f"🔍 DEBUG: user_email = {user_email}")
        print(f"🔍 DEBUG: Checking if base_dir exists: {os.path.exists(base_dir) if base_dir else False}")
        if base_dir and os.path.exists(base_dir):
            print(f"🔍 DEBUG: base_dir contents: {os.listdir(base_dir)[:10] if os.path.isdir(base_dir) else 'Not a directory'}")
        
        if not is_authorized:
            error_message = auth_result.get('message', 'Access denied')
            print(f"❌ DEBUG: Access denied: {error_message}")
            error_div = create_div(
                text=f"""
                <div style="text-align: center; padding: 50px;">
                    <h2 style="color: #dc3545;">🚫 Access Denied</h2>
                    <p>{error_message}</p>
                </div>
                """,
                width=800
            )
            doc.add_root(error_div)
            return
    
    print("=" * 80)
    print("✅ DEBUG: scientistCloudInitDashboard() completed successfully")
    print("=" * 80)


# Main execution
if True:
    print("=" * 80)
    print("🚀 DEBUG: Starting main execution")
    print("=" * 80)
    
    scientistCloudInitDashboard()
    
    # All imports are required - if we get here, everything should be available
    print("🔍 DEBUG: Calling find_nexus_and_mmap_files()...")
    nexus_filename, mmap_filename = find_nexus_and_mmap_files()
    
    print(f"🔍 DEBUG: nexus_filename = {nexus_filename}")
    print(f"🔍 DEBUG: mmap_filename = {mmap_filename}")
    
    if nexus_filename is None:
        print("❌ DEBUG: No nexus file found! Cannot proceed.")
        error_div = create_div(
            text=f"""
            <div style="text-align: center; padding: 50px;">
                <h2 style="color: #dc3545;">❌ No Data File Found</h2>
                <p>Could not find any .nxs files in:</p>
                <ul style="text-align: left; display: inline-block;">
                    <li>base_dir: {base_dir}</li>
                    <li>save_dir: {save_dir}</li>
                </ul>
                <p>Please check the console for detailed debugging information.</p>
            </div>
            """,
            width=800
        )
        curdoc().add_root(error_div)
    else:
        print("🔍 DEBUG: Creating Process4dNexus object...")
        # Create the processor object
        process_4dnexus = Process4dNexus(
            nexus_filename,
            mmap_filename,
            cached_cast_float=True,
            status_callback=add_status_message
        )
        print("✅ DEBUG: Process4dNexus object created successfully")
        
        print("🔍 DEBUG: Calling get_choices() to discover datasets...")
        try:
            choices_success = process_4dnexus.get_choices()
            print(f"🔍 DEBUG: get_choices() returned: {choices_success}")
            print(f"🔍 DEBUG: choices_done = {getattr(process_4dnexus, 'choices_done', 'N/A')}")
            if hasattr(process_4dnexus, 'dimensions_categories'):
                print(f"🔍 DEBUG: dimensions_categories keys: {list(process_4dnexus.dimensions_categories.keys()) if process_4dnexus.dimensions_categories else 'None'}")
            if hasattr(process_4dnexus, 'names_categories'):
                print(f"🔍 DEBUG: names_categories keys: {list(process_4dnexus.names_categories.keys()) if process_4dnexus.names_categories else 'None'}")
        except Exception as e:
            import traceback
            print(f"❌ DEBUG: ERROR in get_choices(): {e}")
            traceback.print_exc()
            error_div = create_div(
                text=f"""
                <div style="text-align: center; padding: 50px;">
                    <h2 style="color: #dc3545;">❌ Error Loading File</h2>
                    <p>Error calling get_choices(): {str(e)}</p>
                    <pre>{traceback.format_exc()}</pre>
                </div>
                """,
                width=800
            )
            curdoc().add_root(error_div)
        else:
            print("🔍 DEBUG: Creating tmp_dashboard...")
            # Start with the temporary dashboard for dataset selection
            try:
                dashboard = create_tmp_dashboard(process_4dnexus)
                print("✅ DEBUG: tmp_dashboard created successfully")
                
                print("🔍 DEBUG: Adding dashboard to curdoc()...")
                curdoc().add_root(dashboard)
                print("✅ DEBUG: Dashboard added to curdoc()")
            except Exception as e:
                import traceback
                print(f"❌ DEBUG: ERROR creating tmp_dashboard: {e}")
                traceback.print_exc()
                error_div = create_div(
                    text=f"""
                    <div style="text-align: center; padding: 50px;">
                        <h2 style="color: #dc3545;">❌ Error Creating Dashboard</h2>
                        <p>Error: {str(e)}</p>
                        <pre>{traceback.format_exc()}</pre>
                    </div>
                    """,
                    width=800
                )
                curdoc().add_root(error_div)
    
    print("=" * 80)
    print("✅ DEBUG: Main execution completed")
    print("=" * 80)

# bokeh serve 4d_dashboardLiteImprove.py --port 5017 --allow-websocket-origin=localhost:5017
