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

# Import SCLib_Dashboards components
import sys
# Add the scientistCloudLib directory to the path
lib_path = os.path.join(os.path.dirname(__file__), '../../..', 'scientistCloudLib')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)
else:
    # Try alternative path
    alt_path = os.path.join(os.path.dirname(__file__), '../../../scientistCloudLib')
    if os.path.exists(alt_path):
        sys.path.insert(0, alt_path)

# Import all SCLib_Dashboards components (all required - no fallbacks)
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
)

# Import UI components (required - all components must be available)
from SCLib_Dashboards import (
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
                return []
            
            # Get all session files, sorted by modification time (newest first)
            session_files = sorted(sessions_dir.glob("session_*.json"), key=os.path.getmtime, reverse=True)
            
            # Create display names with timestamp
            session_choices = []
            for filepath in session_files:
                # Extract timestamp from filename or use modification time
                try:
                    import json
                    with open(filepath, 'r') as f:
                        session_data = json.load(f)
                    metadata = session_data.get("metadata", {})
                    timestamp = metadata.get("last_updated") or metadata.get("created_at", "")
                    if timestamp:
                        from datetime import datetime
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            timestamp_str = os.path.getmtime(filepath)
                            timestamp_str = datetime.fromtimestamp(timestamp_str).strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        timestamp_str = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    timestamp_str = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
                
                display_name = f"{filepath.name} ({timestamp_str})"
                session_choices.append(display_name)
            
            return session_choices, session_files
        except Exception as e:
            print(f"Error getting available sessions: {e}")
            return [], []
    
    session_choices, session_files_list = get_available_sessions()
    session_selector = create_select(
        title="Select Session to Load:",
        value=session_choices[0] if session_choices else "No sessions available",
        options=session_choices if session_choices else ["No sessions available"],
        width=400
    )
    
    # Create load session button
    load_session_button = create_button(
        label="Load Selected Session",
        button_type="default",
        width=200
    )
    
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
        """Load selected session from file and populate selectors with saved dataset paths."""
        try:
            from pathlib import Path
            import os
            import json
            from datetime import datetime
            
            # Get selected session
            selected_session = session_selector.value
            
            if selected_session == "No sessions available":
                status_display.text = "<span style='color: orange;'>No sessions available to load</span>"
                return
            
            # Find the filepath corresponding to the selected session
            # Refresh session list to ensure we have current files
            session_choices_refresh, session_files_refresh = get_available_sessions()
            
            if not session_files_refresh:
                status_display.text = "<span style='color: orange;'>No session files found</span>"
                return
            
            # Match selected display name to filepath
            filepath = None
            for i, choice in enumerate(session_choices_refresh):
                if choice == selected_session:
                    if i < len(session_files_refresh):
                        filepath = session_files_refresh[i]
                        break
            
            if filepath is None or not filepath.exists():
                status_display.text = f"<span style='color: red;'>Session file not found: {selected_session}</span>"
                return
            with open(filepath, 'r') as f:
                session_data = json.load(f)
            
            # Extract metadata which should contain dataset paths
            metadata = session_data.get("metadata", {})
            
            # Extract dataset paths from metadata
            volume_path = metadata.get("dataset_path") or metadata.get("volume_picked")
            plot1_single = metadata.get("plot1_single_dataset_picked")
            presample = metadata.get("presample_picked")
            postsample = metadata.get("postsample_picked")
            x_coords = metadata.get("x_coords_picked")
            y_coords = metadata.get("y_coords_picked")
            probe_x = metadata.get("probe_x_coords_picked")
            probe_y = metadata.get("probe_y_coords_picked")
            volume_b = metadata.get("volume_picked_b")
            plot1b_single = metadata.get("plot1b_single_dataset_picked")
            presample_b = metadata.get("presample_picked_b")
            postsample_b = metadata.get("postsample_picked_b")
            probe_x_b = metadata.get("probe_x_coords_picked_b")
            probe_y_b = metadata.get("probe_y_coords_picked_b")
            plot1_mode = metadata.get("plot1_mode", "ratio")  # "single" or "ratio"
            plot1b_mode = metadata.get("plot1b_mode", "ratio")
            plot1b_enabled = metadata.get("plot1b_enabled", False)
            plot2b_enabled = metadata.get("plot2b_enabled", False)
            
            # Helper function to find matching choice
            def find_matching_choice(choices, path):
                if not path:
                    return None
                # Try exact match first
                for choice in choices:
                    if choice.startswith(path):
                        return choice
                return None
            
            # Populate Plot2 selector
            if volume_path:
                plot2_choice = find_matching_choice(plot2_h5_choices, volume_path)
                if plot2_choice:
                    plot2_selector.value = plot2_choice
            
            # Populate Plot1 selectors based on mode
            if plot1_mode == "single" and plot1_single:
                plot1_mode_selector.active = 0  # Single dataset mode
                plot1_choice = find_matching_choice(plot1_h5_choices, plot1_single)
                if plot1_choice:
                    plot1_single_selector.value = plot1_choice
            elif presample and postsample:
                plot1_mode_selector.active = 1  # Ratio mode
                numerator_choice = find_matching_choice(plot1_h5_choices, postsample)
                denominator_choice = find_matching_choice(plot1_h5_choices, presample)
                if numerator_choice:
                    plot1_numerator_selector.value = numerator_choice
                if denominator_choice:
                    plot1_denominator_selector.value = denominator_choice
            
            # Populate coordinate selectors
            if x_coords:
                map_x_choice = find_matching_choice(coord_choices, x_coords)
                if map_x_choice:
                    map_x_selector.value = map_x_choice
            if y_coords:
                map_y_choice = find_matching_choice(coord_choices, y_coords)
                if map_y_choice:
                    map_y_selector.value = map_y_choice
            if probe_x:
                probe_x_choice = find_matching_choice(coord_choices, probe_x)
                if probe_x_choice:
                    probe_x_selector.value = probe_x_choice
            else:
                probe_x_selector.value = "Use Default"
            if probe_y:
                probe_y_choice = find_matching_choice(coord_choices, probe_y)
                if probe_y_choice:
                    probe_y_selector.value = probe_y_choice
            else:
                probe_y_selector.value = "Use Default"
            
            # Populate Plot1B if enabled
            if plot1b_enabled:
                enable_plot1b_toggle.active = True
                if plot1b_mode == "single" and plot1b_single:
                    plot1b_mode_selector.active = 0
                    plot1b_choice = find_matching_choice(plot1_h5_choices, plot1b_single)
                    if plot1b_choice:
                        plot1b_single_selector.value = plot1b_choice
                elif presample_b and postsample_b:
                    plot1b_mode_selector.active = 1
                    numerator_b_choice = find_matching_choice(plot1_h5_choices, postsample_b)
                    denominator_b_choice = find_matching_choice(plot1_h5_choices, presample_b)
                    if numerator_b_choice:
                        plot1b_numerator_selector.value = numerator_b_choice
                    if denominator_b_choice:
                        plot1b_denominator_selector.value = denominator_b_choice
            
            # Populate Plot2B if enabled
            if plot2b_enabled:
                enable_plot2b_toggle.active = True
                if volume_b:
                    plot2b_choice = find_matching_choice(plot2_h5_choices, volume_b)
                    if plot2b_choice:
                        plot2b_selector.value = plot2b_choice
                if probe_x_b:
                    probe_x_b_choice = find_matching_choice(coord_choices, probe_x_b)
                    if probe_x_b_choice:
                        probe_x_selector_b.value = probe_x_b_choice
                else:
                    probe_x_selector_b.value = "Use Default"
                if probe_y_b:
                    probe_y_b_choice = find_matching_choice(coord_choices, probe_y_b)
                    if probe_y_b_choice:
                        probe_y_selector_b.value = probe_y_b_choice
                else:
                    probe_y_selector_b.value = "Use Default"
            
            # Update session selector options to refresh list
            session_choices_new, session_files_new = get_available_sessions()
            if session_choices_new:
                session_selector.options = session_choices_new
                # Keep current selection
                session_selector.value = selected_session
            
            status_display.text = f"<span style='color: green;'>Session loaded from {filepath.name}. Click 'Initialize Plots' to restore.</span>"
            print(f"✅ Session loaded from {filepath.name}")
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
        row(initialize_button, load_session_button),
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
    """Create the full dashboard using SCLib components with session management and undo/redo."""
    try:
        t0 = time.time()
        print("[TIMING] create_dashboard(): start")
        
        # Load the data
        volume, presample, postsample, x_coords, y_coords, preview = process_4dnexus.load_nexus_data()
        print(f"[TIMING] after load_nexus_data: {time.time()-t0:.3f}s")
        
        print(f"Successfully loaded data:")
        print(f"  Volume shape: {volume.shape}")
        print(f"  X coords shape: {x_coords.shape}")
        print(f"  Y coords shape: {y_coords.shape}")
        
        # Check if volume is 3D or 4D
        is_3d_volume = len(volume.shape) == 3
        print(f"  Volume dimensionality: {'3D (1D probe plot)' if is_3d_volume else '4D (2D probe plot)'}")
        
        # Import datetime
        from datetime import datetime
        
        # Create PlotSession for state management
        # Include all dataset paths in metadata so they can be restored when loading session
        session = PlotSession(
            session_id=f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            metadata={
                "dataset_path": getattr(process_4dnexus, 'volume_picked', 'unknown'),
                "volume_picked": getattr(process_4dnexus, 'volume_picked', None),
                "plot1_single_dataset_picked": getattr(process_4dnexus, 'plot1_single_dataset_picked', None),
                "presample_picked": getattr(process_4dnexus, 'presample_picked', None),
                "postsample_picked": getattr(process_4dnexus, 'postsample_picked', None),
                "x_coords_picked": getattr(process_4dnexus, 'x_coords_picked', None),
                "y_coords_picked": getattr(process_4dnexus, 'y_coords_picked', None),
                "probe_x_coords_picked": getattr(process_4dnexus, 'probe_x_coords_picked', None),
                "probe_y_coords_picked": getattr(process_4dnexus, 'probe_y_coords_picked', None),
                "volume_picked_b": getattr(process_4dnexus, 'volume_picked_b', None),
                "plot1b_single_dataset_picked": getattr(process_4dnexus, 'plot1b_single_dataset_picked', None),
                "presample_picked_b": getattr(process_4dnexus, 'presample_picked_b', None),
                "postsample_picked_b": getattr(process_4dnexus, 'postsample_picked_b', None),
                "probe_x_coords_picked_b": getattr(process_4dnexus, 'probe_x_coords_picked_b', None),
                "probe_y_coords_picked_b": getattr(process_4dnexus, 'probe_y_coords_picked_b', None),
                "plot1_mode": "single" if getattr(process_4dnexus, 'plot1_single_dataset_picked', None) else "ratio",
                "plot1b_mode": "single" if getattr(process_4dnexus, 'plot1b_single_dataset_picked', None) else "ratio",
                "plot1b_enabled": bool(getattr(process_4dnexus, 'plot1b_single_dataset_picked', None) or getattr(process_4dnexus, 'presample_picked_b', None)),
                "plot2b_enabled": bool(getattr(process_4dnexus, 'volume_picked_b', None)),
                "user_email": user_email if 'user_email' in globals() else None,
            }
        )
        
        # Create SessionStateHistory for undo/redo
        # NOTE: State history saves with include_data=False, so it only stores UI settings,
        # not data arrays. This keeps undo/redo fast and memory-efficient.
        # Reduced max_history from 100 to 20 for better performance (fewer deep copies)
        session_history = SessionStateHistory(session, max_history=20)
        
        # Import Bokeh components
        from bokeh.models import (
            Slider, Toggle, TapTool, CustomJS, HoverTool,
            ColorBar, LinearColorMapper, LogColorMapper, TextInput,
            LogScale, LinearScale, FileInput, BoxSelectTool, BoxEditTool
        )
        from bokeh.transform import linear_cmap
        import matplotlib.colors as colors
        
        # Rectangle class for selection areas and crosshairs
        class Rectangle:
            """Helper class to manage selection rectangles and crosshairs."""
            def __init__(self, min_x=0, min_y=0, max_x=0, max_y=0):
                self.min_x = min_x
                self.min_y = min_y
                self.max_x = max_x
                self.max_y = max_y
                self.h1line = None  # Horizontal line 1 (for crosshairs)
                self.h2line = None  # Horizontal line 2 (for crosshairs)
                self.v1line = None  # Vertical line 1 (for crosshairs)
                self.v2line = None  # Vertical line 2 (for crosshairs)
            
            def swap_if_needed(self):
                """Swap min/max if needed (for 4D volumes with proper rectangle selection)."""
                if not is_3d_volume:
                    if self.min_x > self.max_x:
                        self.min_x, self.max_x = self.max_x, self.min_x
                    if self.min_y > self.max_y:
                        self.min_y, self.max_y = self.max_y, self.min_y
            
            def set(self, min_x=None, min_y=None, max_x=None, max_y=None):
                """Set rectangle coordinates."""
                if min_x is not None:
                    self.min_x = min_x
                if min_y is not None:
                    self.min_y = min_y
                if max_x is not None:
                    self.max_x = max_x
                if max_y is not None:
                    self.max_y = max_y
                self.swap_if_needed()
        
        # Initialize rectangles for selection areas
        # rect1: For Plot1 crosshairs (X, Y indices)
        rect1 = Rectangle(0, 0, volume.shape[0] - 1, volume.shape[1] - 1)
        rect1.h1line = None  # Initialize crosshair line attributes
        rect1.v1line = None
        rect1b = None  # Will be initialized if Plot1B exists
        
        # rect2: For Plot2A selection (Z, U dimensions for 4D or Z for 3D)
        if is_3d_volume:
            rect2 = Rectangle(0, 0, volume.shape[2] - 1, volume.shape[2] - 1)  # 1D probe
        else:
            rect2 = Rectangle(0, 0, volume.shape[2] - 1, volume.shape[3] - 1)  # Z, U
        
        rect2b = None  # Will be initialized if Plot2B exists
        
        # rect3: For Plot3 selection (X, Y dimensions)
        rect3 = Rectangle(0, 0, volume.shape[0] - 1, volume.shape[1] - 1)
        
        # Set initial probe positions to middle of the data range
        x_index = volume.shape[0] // 2
        y_index = volume.shape[1] // 2
        
        # Detect if map coordinates need flipping
        print("=" * 80)
        print("🔍 DEBUG: Map Flip Detection for Plot1:")
        print(f"  preview.shape: {preview.shape if preview is not None else 'None'}")
        map_x_coord_size = None
        map_y_coord_size = None
        if hasattr(process_4dnexus, 'x_coords_picked') and process_4dnexus.x_coords_picked:
            map_x_coord_size = process_4dnexus.get_dataset_size_from_path(process_4dnexus.x_coords_picked)
            print(f"  x_coords_picked: {process_4dnexus.x_coords_picked}")
            print(f"  map_x_coord_size: {map_x_coord_size}")
        if hasattr(process_4dnexus, 'y_coords_picked') and process_4dnexus.y_coords_picked:
            map_y_coord_size = process_4dnexus.get_dataset_size_from_path(process_4dnexus.y_coords_picked)
            print(f"  y_coords_picked: {process_4dnexus.y_coords_picked}")
            print(f"  map_y_coord_size: {map_y_coord_size}")
        
        plot1_needs_flip = False
        if preview is not None and len(preview.shape) == 2:
            plot1_needs_flip = process_4dnexus.detect_map_flip_needed(
                preview.shape,
                map_x_coord_size,
                map_y_coord_size
            )
            print(f"  plot1_needs_flip: {plot1_needs_flip}")
        print("=" * 80)
        
        # Store original coordinate paths for axis labels
        # NOTE: Pass ORIGINAL labels to MAP_2DPlot - it will handle swapping via get_flipped_x_axis_label()
        # If we swap here AND use get_flipped_x_axis_label(), we'd swap twice!
        original_map_x_label = getattr(process_4dnexus, 'x_coords_picked', 'X Position')
        original_map_y_label = getattr(process_4dnexus, 'y_coords_picked', 'Y Position')
        
        # Create Plot1 (Map view) using SCLib MAP_2DPlot class
        # Pass original labels - the plot object will handle flipping via its methods
        map_plot = MAP_2DPlot(
            title="Plot1 - Map View",
            data=preview,
            x_coords=x_coords,
            y_coords=y_coords,
            palette="Viridis256",
            color_scale=ColorScale.LINEAR,
            range_mode=RangeMode.DYNAMIC,
            crosshairs_enabled=True,
            x_axis_label=original_map_x_label,  # Original label - will be swapped by get_flipped_x_axis_label() if needed
            y_axis_label=original_map_y_label,  # Original label - will be swapped by get_flipped_y_axis_label() if needed
            needs_flip=plot1_needs_flip,
            track_changes=True,
        )
        
        # Add plot to session
        session.add_plot("plot1", map_plot)
        
        # Create plot history for undo/redo
        # Reduced max_history from 50 to 20 for better performance
        plot1_history = PlotStateHistory(map_plot, max_history=20)
        
        # Get flipped data and coordinates for Bokeh plot - ALWAYS use flipped methods
        # This ensures consistency - if needs_flip is True, these return flipped versions
        plot1_data = map_plot.get_flipped_data()
        plot1_x_coords = map_plot.get_flipped_x_coords()
        plot1_y_coords = map_plot.get_flipped_y_coords()
        
        print("🔍 DEBUG: Plot1 Data and Coordinates:")
        print(f"  map_plot.needs_flip: {map_plot.needs_flip}")
        print(f"  Original preview.shape: {preview.shape if preview is not None else 'None'}")
        print(f"  plot1_data.shape: {plot1_data.shape if plot1_data is not None else 'None'}")
        print(f"  Original x_coords length: {len(x_coords) if x_coords is not None else 'None'}")
        print(f"  Original y_coords length: {len(y_coords) if y_coords is not None else 'None'}")
        print(f"  plot1_x_coords length: {len(plot1_x_coords) if plot1_x_coords is not None else 'None'}")
        print(f"  plot1_y_coords length: {len(plot1_y_coords) if plot1_y_coords is not None else 'None'}")
        print(f"  plot1_x_coords range: [{np.min(plot1_x_coords):.2f}, {np.max(plot1_x_coords):.2f}]" if plot1_x_coords is not None else "  plot1_x_coords: None")
        print(f"  plot1_y_coords range: [{np.min(plot1_y_coords):.2f}, {np.max(plot1_y_coords):.2f}]" if plot1_y_coords is not None else "  plot1_y_coords: None")
        print(f"  X axis label: {map_plot.get_flipped_x_axis_label()}")
        print(f"  Y axis label: {map_plot.get_flipped_y_axis_label()}")
        print(f"  Data shape matches coords: data.shape[1]={plot1_data.shape[1] if plot1_data is not None else 'N/A'} == len(plot1_x_coords)={len(plot1_x_coords) if plot1_x_coords is not None else 'N/A'}, data.shape[0]={plot1_data.shape[0] if plot1_data is not None else 'N/A'} == len(plot1_y_coords)={len(plot1_y_coords) if plot1_y_coords is not None else 'N/A'}")
        if plot1_data is not None and plot1_x_coords is not None and plot1_y_coords is not None:
            # Bokeh image() interprets data as (rows, cols) = (height, width)
            # So data.shape[1] (columns) should match x_coords (width)
            # And data.shape[0] (rows) should match y_coords (height)
            if plot1_data.shape[1] != len(plot1_x_coords) or plot1_data.shape[0] != len(plot1_y_coords):
                print(f"  ⚠️ WARNING: Data shape {plot1_data.shape} does NOT match coordinate lengths!")
                print(f"     Expected: data.shape[1]={plot1_data.shape[1]} == len(x_coords)={len(plot1_x_coords)}")
                print(f"     Expected: data.shape[0]={plot1_data.shape[0]} == len(y_coords)={len(plot1_y_coords)}")
            else:
                print(f"  ✅ Data shape matches coordinate lengths")
                print(f"     data.shape[1]={plot1_data.shape[1]} == len(x_coords)={len(plot1_x_coords)} (columns/width)")
                print(f"     data.shape[0]={plot1_data.shape[0]} == len(y_coords)={len(plot1_y_coords)} (rows/height)")
        print(f"  X axis label (from get_flipped_x_axis_label): {map_plot.get_flipped_x_axis_label()}")
        print(f"  Y axis label (from get_flipped_y_axis_label): {map_plot.get_flipped_y_axis_label()}")
        print(f"  X ticks will show values from: plot1_x_coords (first few: {plot1_x_coords[:3] if len(plot1_x_coords) >= 3 else plot1_x_coords})")
        print(f"  Y ticks will show values from: plot1_y_coords (first few: {plot1_y_coords[:3] if len(plot1_y_coords) >= 3 else plot1_y_coords})")
        # Check if data orientation matches what we expect
        if plot1_data is not None and preview is not None and map_plot.needs_flip:
            print(f"  🔄 FLIPPED: Checking data orientation...")
            print(f"     Original data.shape: {preview.shape}")
            print(f"     Transposed data.shape: {plot1_data.shape}")
            print(f"     Original data[0,0]={preview[0,0]}, Transposed data[0,0]={plot1_data[0,0]} (should be original[0,0] if no transpose)")
            print(f"     Original data[-1,-1]={preview[-1,-1]}, Transposed data[-1,-1]={plot1_data[-1,-1]} (should be original[-1,-1] if no transpose)")
            print(f"     Original data[0,-1]={preview[0,-1]}, Transposed data[0,-1]={plot1_data[0,-1]} (should be original[-1,0] if transposed)")
            print(f"     Original data[-1,0]={preview[-1,0]}, Transposed data[-1,0]={plot1_data[-1,0]} (should be original[0,-1] if transposed)")
            # Verify transpose: transposed[i,j] should equal original[j,i]
            if plot1_data[0,0] == preview[0,0] and plot1_data[-1,-1] == preview[-1,-1]:
                print(f"     ⚠️ WARNING: Data might not be transposed! Corner values match original.")
            if plot1_data[0,-1] == preview[-1,0] and plot1_data[-1,0] == preview[0,-1]:
                print(f"     ✅ Data appears to be correctly transposed")
            # Check coordinate mapping
            print(f"     Original x_coords (px, length {len(x_coords)}): first={x_coords[0]:.2f}, last={x_coords[-1]:.2f}")
            print(f"     Original y_coords (py, length {len(y_coords)}): first={y_coords[0]:.2f}, last={y_coords[-1]:.2f}")
            print(f"     Flipped x_coords (length {len(plot1_x_coords)}): first={plot1_x_coords[0]:.2f}, last={plot1_x_coords[-1]:.2f} (ALWAYS px, goes on x-axis)")
            print(f"     Flipped y_coords (length {len(plot1_y_coords)}): first={plot1_y_coords[0]:.2f}, last={plot1_y_coords[-1]:.2f} (ALWAYS py, goes on y-axis)")
            print(f"     X axis label: {map_plot.get_flipped_x_axis_label()} (swapped if data transposed)")
            print(f"     Y axis label: {map_plot.get_flipped_y_axis_label()} (swapped if data transposed)")
            # Verify coordinate-to-data mapping
            # IMPORTANT: px (x_coords) ALWAYS goes on x-axis, py (y_coords) ALWAYS goes on y-axis
            # We only transpose the DATA if dimensions don't match, but coordinates never swap
            print(f"     🔍 Coordinate-to-Data Mapping Verification:")
            print(f"        Logic: px (x_coords) ALWAYS on x-axis, py (y_coords) ALWAYS on y-axis")
            print(f"        Data.shape[1]={plot1_data.shape[1]} (x-axis/width) should match len(plot1_x_coords)={len(plot1_x_coords)} (px)")
            print(f"        Data.shape[0]={plot1_data.shape[0]} (y-axis/height) should match len(plot1_y_coords)={len(plot1_y_coords)} (py)")
            if plot1_data.shape[1] == len(plot1_x_coords) and plot1_data.shape[0] == len(plot1_y_coords):
                print(f"        ✅ Coordinate lengths match data dimensions")
            else:
                print(f"        ⚠️ WARNING: Coordinate lengths DO NOT match data dimensions!")
                print(f"           This will cause misalignment between data and axes!")
        
        # Calculate initial range values from 1st and 99th percentiles
        map_min_val = float(np.percentile(plot1_data[~np.isnan(plot1_data)], 1))
        map_max_val = float(np.percentile(plot1_data[~np.isnan(plot1_data)], 99))
        
        # Set initial range values in map_plot
        map_plot.range_min = map_min_val
        map_plot.range_max = map_max_val
        
        # Create color mapper (store in variable for later updates)
        color_mapper1 = LinearColorMapper(palette=map_plot.palette, low=map_min_val, high=map_max_val)
        
        # Calculate initial plot dimensions from map_plot
        initial_width, initial_height = map_plot.calculate_plot_dimensions()
        
        # Create Bokeh figure for Plot1 (use calculated dimensions)
        plot1 = figure(
            title="Plot1 - Map View",
            x_range=(float(np.min(plot1_x_coords)), float(np.max(plot1_x_coords))),
            y_range=(float(np.min(plot1_y_coords)), float(np.max(plot1_y_coords))),
            tools="pan,wheel_zoom,box_zoom,reset,tap",
            match_aspect=True,
            width=initial_width,
            height=initial_height,
        )
        
        # Set axis labels (already swapped in map_plot if needed)
        plot1.xaxis.axis_label = map_plot.get_flipped_x_axis_label()
        plot1.yaxis.axis_label = map_plot.get_flipped_y_axis_label()
        
        # Create tick arrays from FLIPPED coordinate arrays for Plot1
        # Always use flipped coordinates - they're already swapped if needed
        dx, dy = 15, 15  # Sample every 15th coordinate for ticks
        x_ticks, my_xticks = [], []
        for i in range(0, len(plot1_x_coords), dx):
            x_ticks.append(plot1_x_coords[i])
            my_xticks.append(f"{plot1_x_coords[i]:.1f}")
        
        y_ticks, my_yticks = [], []
        for i in range(0, len(plot1_y_coords), dy):
            y_ticks.append(plot1_y_coords[i])
            my_yticks.append(f"{plot1_y_coords[i]:.1f}")
        
        # Set ticks on Plot1 - use flipped coordinates directly (no swap needed)
        # The coordinates are already in the correct order from get_flipped_x_coords/y_coords
            plot1.xaxis.ticker = x_ticks
            plot1.yaxis.ticker = y_ticks
            plot1.xaxis.major_label_overrides = dict(zip(x_ticks, my_xticks))
            plot1.yaxis.major_label_overrides = dict(zip(y_ticks, my_yticks))
        
        # VERIFICATION: Bokeh image() expects data as (rows, cols) = (height, width)
        # Standard NumPy convention: array[row, col] where:
        # - shape[0] = number of rows = vertical dimension = y-axis (height) → should match y_coords length
        # - shape[1] = number of columns = horizontal dimension = x-axis (width) → should match x_coords length
        # This is why data.shape[1] maps to x-axis (width) and data.shape[0] maps to y-axis (height)
        print("🔍 VERIFICATION: Bokeh image() data format expectations:")
        print(f"   NumPy convention: array[row, col] → shape[0]=rows (y-axis/height), shape[1]=cols (x-axis/width)")
        print(f"   Bokeh interprets: data.shape[0] = rows = y-axis (height)")
        print(f"   Bokeh interprets: data.shape[1] = cols = x-axis (width)")
        print(f"   Our data.shape: {plot1_data.shape if plot1_data is not None else 'None'}")
        print(f"   Our x_coords length: {len(plot1_x_coords) if plot1_x_coords is not None else 'None'} (should match data.shape[1])")
        print(f"   Our y_coords length: {len(plot1_y_coords) if plot1_y_coords is not None else 'None'} (should match data.shape[0])")
        if plot1_data is not None and plot1_x_coords is not None and plot1_y_coords is not None:
            if plot1_data.shape[1] == len(plot1_x_coords) and plot1_data.shape[0] == len(plot1_y_coords):
                print(f"   ✅ VERIFIED: Data format matches Bokeh expectations!")
                print(f"      data.shape[1]={plot1_data.shape[1]} == len(x_coords)={len(plot1_x_coords)} (x-axis/width)")
                print(f"      data.shape[0]={plot1_data.shape[0]} == len(y_coords)={len(plot1_y_coords)} (y-axis/height)")
            else:
                print(f"   ❌ ERROR: Data format does NOT match Bokeh expectations!")
                print(f"      data.shape[1]={plot1_data.shape[1]} != len(x_coords)={len(plot1_x_coords)}")
                print(f"      data.shape[0]={plot1_data.shape[0]} != len(y_coords)={len(plot1_y_coords)}")
                print(f"      This will cause misalignment between data and axes!")
        
        # Create data source for Plot1
        source1 = ColumnDataSource(
            data={
                "image": [plot1_data],
                "x": [float(np.min(plot1_x_coords))],
                "y": [float(np.min(plot1_y_coords))],
                "dw": [float(np.max(plot1_x_coords) - np.min(plot1_x_coords))],
                "dh": [float(np.max(plot1_y_coords) - np.min(plot1_y_coords))],
            }
        )
        
        # Add image renderer
        try:
            image_renderer1 = plot1.image(
                "image", source=source1, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper1
            )
            print("✅ Plot1 image renderer created successfully")
        except Exception as e:
            print(f"⚠️ ERROR creating Plot1 image renderer: {e}")
            import traceback
            traceback.print_exc()
        
        # Create colorbar
        try:
            colorbar1 = ColorBar(color_mapper=color_mapper1, title="Plot1 Intensity", location=(0, 0))
            plot1.add_layout(colorbar1, "below")
            print("✅ Plot1 colorbar added successfully")
        except Exception as e:
            print(f"⚠️ ERROR adding Plot1 colorbar: {e}")
            import traceback
            traceback.print_exc()
        
        # Add TapTool to Plot1 for crosshair positioning
        try:
            tap_tool1 = TapTool()
            plot1.add_tools(tap_tool1)
            print("✅ Plot1 TapTool added successfully")
        except Exception as e:
            print(f"⚠️ ERROR adding Plot1 TapTool: {e}")
            import traceback
            traceback.print_exc()
        
        # Function to draw crosshairs on Plot1
        def draw_cross1():
            """Draw crosshairs on Plot1 based on current slider values."""
            try:
                x_index = get_x_index()
                y_index = get_y_index()
                
                # Get coordinates using flipped coordinate arrays
                # These are already in the correct order for the plot
                if plot1_x_coords is None or plot1_y_coords is None:
                    print("⚠️ WARNING: plot1_x_coords or plot1_y_coords is None in draw_cross1()")
                    return
                    
                plot_x_coord = plot1_x_coords[x_index] if x_index < len(plot1_x_coords) else plot1_x_coords[-1]
                plot_y_coord = plot1_y_coords[y_index] if y_index < len(plot1_y_coords) else plot1_y_coords[-1]
            except Exception as e:
                print(f"⚠️ ERROR in draw_cross1(): {e}")
                import traceback
                traceback.print_exc()
                return
            
            plot1_x_min = plot1.x_range.start
            plot1_x_max = plot1.x_range.end
            plot1_y_min = plot1.y_range.start
            plot1_y_max = plot1.y_range.end
            
            # Initialize crosshair lines if they don't exist
            if rect1.h1line is None:
                rect1.h1line = plot1.line(
                    x=[plot1_x_min, plot1_x_max], 
                    y=[plot_y_coord, plot_y_coord], 
                    line_color="yellow", 
                    line_width=2
                )
            if rect1.v1line is None:
                rect1.v1line = plot1.line(
                    x=[plot_x_coord, plot_x_coord], 
                    y=[plot1_y_min, plot1_y_max], 
                    line_color="yellow", 
                    line_width=2
                )
            
            # Update crosshair positions (Bokeh automatically updates when data is changed)
            rect1.h1line.data_source.data = {
                "x": [plot1_x_min, plot1_x_max],
                "y": [plot_y_coord, plot_y_coord],
            }
            rect1.v1line.data_source.data = {
                "x": [plot_x_coord, plot_x_coord],
                "y": [plot1_y_min, plot1_y_max],
            }
            
            # Also update Plot1B crosshairs if it exists
            try:
                if plot1b is not None and rect1b is not None:
                    draw_cross1b()
            except (NameError, AttributeError):
                pass  # Plot1B not created yet
        
        # Function to draw crosshairs on Plot1B (synchronized with Plot1)
        def draw_cross1b():
            """Draw crosshairs on Plot1B using the same coordinates as Plot1."""
            if 'plot1b' not in locals() or plot1b is None or rect1b is None or map_plot_b is None:
                return
            
            x_index = get_x_index()
            y_index = get_y_index()
            
            # Get coordinates using Plot1B's flipped coordinate arrays
            plot1b_x_coords = map_plot_b.get_flipped_x_coords()
            plot1b_y_coords = map_plot_b.get_flipped_y_coords()
            plot_x_coord = plot1b_x_coords[x_index] if x_index < len(plot1b_x_coords) else plot1b_x_coords[-1]
            plot_y_coord = plot1b_y_coords[y_index] if y_index < len(plot1b_y_coords) else plot1b_y_coords[-1]
            
            plot1b_x_min = plot1b.x_range.start
            plot1b_x_max = plot1b.x_range.end
            plot1b_y_min = plot1b.y_range.start
            plot1b_y_max = plot1b.y_range.end
            
            # Initialize crosshair lines if they don't exist
            if rect1b.h1line is None:
                rect1b.h1line = plot1b.line(
                    x=[plot1b_x_min, plot1b_x_max], 
                    y=[plot_y_coord, plot_y_coord], 
                    line_color="yellow", 
                    line_width=2
                )
            if rect1b.v1line is None:
                rect1b.v1line = plot1b.line(
                    x=[plot_x_coord, plot_x_coord], 
                    y=[plot1b_y_min, plot1b_y_max], 
                    line_color="yellow", 
                    line_width=2
                )
            
            # Update crosshair positions (Bokeh automatically updates when data is changed)
            rect1b.h1line.data_source.data = {
                "x": [plot1b_x_min, plot1b_x_max],
                "y": [plot_y_coord, plot_y_coord],
            }
            rect1b.v1line.data_source.data = {
                "x": [plot_x_coord, plot_x_coord],
                "y": [plot1b_y_min, plot1b_y_max],
            }
        
        # Note: Tap handler for Plot1 will be defined after sliders are created
        # Note: UI update function and undo/redo callbacks will be set up after all UI elements are created
        
        # Create Plot2 (Probe view) using SCLib plot classes
        initial_slice_1d = None
        initial_slice = None
        
        if is_3d_volume:
            # 1D plot for 3D volume
            initial_slice_1d = volume[volume.shape[0]//2, volume.shape[1]//2, :]
            
            # Create PROBE_1DPlot
            probe_1d_plot = PROBE_1DPlot(
                title="Plot2 - 1D Probe View",
                data=initial_slice_1d,
                x_coords=np.arange(len(initial_slice_1d)),
                palette="Viridis256",
                color_scale=ColorScale.LINEAR,
                range_mode=RangeMode.DYNAMIC,
                track_changes=True,
            )
            
            # Add to session
            session.add_plot("plot2", probe_1d_plot)
            # Reduced max_history from 50 to 20 for better performance
            plot2_history = PlotStateHistory(probe_1d_plot, max_history=20)
            
            # Create Bokeh figure (smaller size: 300x300)
            plot2 = figure(
                title="Plot2 - 1D Probe View",
                tools="pan,wheel_zoom,box_zoom,reset,tap",
                width=300,
                height=300,
            )
            source2 = ColumnDataSource(data={"x": np.arange(len(initial_slice_1d)), "y": initial_slice_1d})
            plot2.line("x", "y", source=source2, line_width=2, line_color="blue")
        else:
            # 2D plot for 4D volume
            initial_slice = volume[volume.shape[0]//2, volume.shape[1]//2, :, :]
            
            # Detect if probe coordinates need flipping
            print("=" * 80)
            print("🔍 DEBUG: Probe Flip Detection for Plot2:")
            print(f"  volume.shape: {volume.shape}")
            probe_x_coord_size = None
            probe_y_coord_size = None
            if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                probe_x_coord_size = process_4dnexus.get_dataset_size_from_path(process_4dnexus.probe_x_coords_picked)
                print(f"  probe_x_coords_picked: {process_4dnexus.probe_x_coords_picked}")
                print(f"  probe_x_coord_size: {probe_x_coord_size}")
            if hasattr(process_4dnexus, 'probe_y_coords_picked') and process_4dnexus.probe_y_coords_picked:
                probe_y_coord_size = process_4dnexus.get_dataset_size_from_path(process_4dnexus.probe_y_coords_picked)
                print(f"  probe_y_coords_picked: {process_4dnexus.probe_y_coords_picked}")
                print(f"  probe_y_coord_size: {probe_y_coord_size}")
            
            plot2_needs_flip = process_4dnexus.detect_probe_flip_needed(
                volume.shape,
                probe_x_coord_size,
                probe_y_coord_size
            )
            print(f"  plot2_needs_flip: {plot2_needs_flip}")
            print("=" * 80)
            
            # Store original coordinate paths for axis labels
            # NOTE: Pass ORIGINAL labels to PROBE_2DPlot - it will handle swapping via get_flipped_x_axis_label()
            original_probe_x_label = getattr(process_4dnexus, 'probe_x_coords_picked', 'Probe X')
            original_probe_y_label = getattr(process_4dnexus, 'probe_y_coords_picked', 'Probe Y')
            
            # Extract just the dataset name for labels
            if '/' in str(original_probe_x_label):
                original_probe_x_label = str(original_probe_x_label).split('/')[-1]
            if '/' in str(original_probe_y_label):
                original_probe_y_label = str(original_probe_y_label).split('/')[-1]
            
            # Load actual probe coordinate arrays (cache them for future use)
            # Check if cached coordinates match current path - if not, clear cache and reload
            cached_x_path = getattr(process_4dnexus, '_cached_probe_x_coords_path', None)
            cached_y_path = getattr(process_4dnexus, '_cached_probe_y_coords_path', None)
            current_x_path = getattr(process_4dnexus, 'probe_x_coords_picked', None)
            current_y_path = getattr(process_4dnexus, 'probe_y_coords_picked', None)
            
            # Clear cache if path has changed
            if cached_x_path != current_x_path:
                process_4dnexus._cached_probe_x_coords = None
                process_4dnexus._cached_probe_x_coords_path = None
            if cached_y_path != current_y_path:
                process_4dnexus._cached_probe_y_coords = None
                process_4dnexus._cached_probe_y_coords_path = None
            
            probe_x_coords_array = getattr(process_4dnexus, '_cached_probe_x_coords', None)
            probe_y_coords_array = getattr(process_4dnexus, '_cached_probe_y_coords', None)
            
            if probe_x_coords_array is None and hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                try:
                    probe_x_coords_array = process_4dnexus.load_dataset_by_path(process_4dnexus.probe_x_coords_picked)
                    if probe_x_coords_array is not None and probe_x_coords_array.ndim == 1:
                        probe_x_coords_array = np.array(probe_x_coords_array)
                        process_4dnexus._cached_probe_x_coords = probe_x_coords_array  # Cache for future use
                        process_4dnexus._cached_probe_x_coords_path = process_4dnexus.probe_x_coords_picked  # Cache path
                except:
                    probe_x_coords_array = None
            if probe_y_coords_array is None and hasattr(process_4dnexus, 'probe_y_coords_picked') and process_4dnexus.probe_y_coords_picked:
                try:
                    probe_y_coords_array = process_4dnexus.load_dataset_by_path(process_4dnexus.probe_y_coords_picked)
                    if probe_y_coords_array is not None and probe_y_coords_array.ndim == 1:
                        probe_y_coords_array = np.array(probe_y_coords_array)
                        process_4dnexus._cached_probe_y_coords = probe_y_coords_array  # Cache for future use
                        process_4dnexus._cached_probe_y_coords_path = process_4dnexus.probe_y_coords_picked  # Cache path
                except:
                    probe_y_coords_array = None
            
            # Map probe coordinates to slice dimensions
            # initial_slice has shape (z_size, u_size) from volume[x, y, :, :]
            # - initial_slice.shape[0] = z (from volume.shape[2])
            # - initial_slice.shape[1] = u (from volume.shape[3])
            # 
            # IMPORTANT: px (x_coords) ALWAYS goes on x-axis, py (y_coords) ALWAYS goes on y-axis
            # We only transpose the DATA if dimensions don't match, but coordinates never swap
            # 
            # The detect_probe_flip_needed() function determines if we need to transpose:
            # - If px matches z and py matches u: no transpose (data stays (z, u))
            # - If px matches u and py matches z: transpose needed (data becomes (u, z))
            # 
            # So we simply pass px and py directly - the flip logic will handle transposing the data
            if probe_x_coords_array is not None and probe_y_coords_array is not None:
                # px always goes on x-axis, py always goes on y-axis
                plot2_x_coords_for_plot = probe_x_coords_array  # px → x-axis
                plot2_y_coords_for_plot = probe_y_coords_array  # py → y-axis
            else:
                # Fallback to indices if coordinate arrays not available
                plot2_x_coords_for_plot = np.arange(initial_slice.shape[1])  # u dimension
                plot2_y_coords_for_plot = np.arange(initial_slice.shape[0])  # z dimension
            
            # Create PROBE_2DPlot (data will be transposed for display)
            # Pass original labels - the plot object will handle flipping via its methods
            probe_2d_plot = PROBE_2DPlot(
                title="Plot2 - 2D Probe View",
                data=initial_slice,
                x_coords=plot2_x_coords_for_plot,
                y_coords=plot2_y_coords_for_plot,
                palette="Viridis256",
                color_scale=ColorScale.LINEAR,
                range_mode=RangeMode.DYNAMIC,
                x_axis_label=original_probe_x_label,  # Original label - will be swapped by get_flipped_x_axis_label() if needed
                y_axis_label=original_probe_y_label,  # Original label - will be swapped by get_flipped_y_axis_label() if needed
                needs_flip=plot2_needs_flip,
                track_changes=True,
            )
            
            # Add to session
            session.add_plot("plot2", probe_2d_plot)
            # Reduced max_history from 50 to 20 for better performance
            plot2_history = PlotStateHistory(probe_2d_plot, max_history=20)
            
            # Prepare data and coordinates for Bokeh plot using PROBE_2DPlot flipped methods
            # The probe_2d_plot object handles all flipping logic internally
            plot2_data = probe_2d_plot.get_flipped_data()
            plot2_x_coords = probe_2d_plot.get_flipped_x_coords()
            plot2_y_coords = probe_2d_plot.get_flipped_y_coords()
            
            # If flipped methods return None, fall back to manual calculation
            if plot2_data is None:
                plot2_data = np.transpose(initial_slice)  # Always transpose for Bokeh
            if plot2_x_coords is None:
                plot2_x_coords = np.arange(plot2_data.shape[1])
            if plot2_y_coords is None:
                plot2_y_coords = np.arange(plot2_data.shape[0])
            
            # Create Bokeh figure (smaller size: 300x300)
            plot2 = figure(
                title="Plot2 - 2D Probe View",
                tools="pan,wheel_zoom,box_zoom,reset,tap",
                x_range=(float(np.min(plot2_x_coords)), float(np.max(plot2_x_coords))),
                y_range=(float(np.min(plot2_y_coords)), float(np.max(plot2_y_coords))),
                match_aspect=True,
                width=300,
                height=300,
            )
            
            # Set axis labels using flipped methods from probe_2d_plot
            plot2.xaxis.axis_label = probe_2d_plot.get_flipped_x_axis_label() or original_probe_x_label
            plot2.yaxis.axis_label = probe_2d_plot.get_flipped_y_axis_label() or original_probe_y_label
            
            # VERIFICATION: For 4D volume (x, y, z, u), Plot2 shows slice (z, u)
            # - initial_slice = volume[:, :, :, :] gives shape (z, u) = (volume.shape[2], volume.shape[3])
            # - User expectation: z should be on x-axis, u should be on y-axis
            # - px (x_coords) should map to z dimension, py (y_coords) should map to u dimension
            # - User says: data.shape[0] should match x_coords (z on x-axis)
            # - This means: data.shape[0] = z, and z should be on x-axis
            # - But Bokeh interprets: data.shape[0] = y-axis, data.shape[1] = x-axis
            # - So if data.shape[0] = z and we want z on x-axis, we need data.shape[1] = z
            # - This means we need to transpose: (z, u) → (u, z) so z becomes shape[1] (x-axis)
            print("🔍 VERIFICATION: Plot2 data and coordinate mapping:")
            print(f"   For 4D volume (x, y, z, u): slice has shape (z, u) = (volume.shape[2], volume.shape[3])")
            print(f"   Volume dimensions: z={volume.shape[2]}, u={volume.shape[3]}")
            print(f"   User expectation: z on x-axis, u on y-axis")
            print(f"   Our data.shape: {plot2_data.shape if plot2_data is not None else 'None'} (after flip if needed)")
            print(f"   px (x_coords) length: {len(plot2_x_coords) if plot2_x_coords is not None else 'None'} (should map to z)")
            print(f"   py (y_coords) length: {len(plot2_y_coords) if plot2_y_coords is not None else 'None'} (should map to u)")
            print(f"   User requirement: data.shape[0] should match x_coords (z on x-axis)")
            print(f"   Bokeh interprets: data.shape[0] = y-axis, data.shape[1] = x-axis")
            if plot2_data is not None and plot2_x_coords is not None and plot2_y_coords is not None:
                # User requirement: data.shape[0] should match x_coords (z dimension)
                # User requirement: data.shape[1] should match y_coords (u dimension)
                shape0_matches_x = plot2_data.shape[0] == len(plot2_x_coords)
                shape1_matches_y = plot2_data.shape[1] == len(plot2_y_coords)
                
                if shape0_matches_x and shape1_matches_y:
                    print(f"   ✅ VERIFIED: Data and coordinates match user expectation!")
                    print(f"      data.shape[0]={plot2_data.shape[0]} == len(px)={len(plot2_x_coords)} (z dimension)")
                    print(f"      data.shape[1]={plot2_data.shape[1]} == len(py)={len(plot2_y_coords)} (u dimension)")
                    print(f"      Note: Bokeh interprets shape[0] as y-axis and shape[1] as x-axis")
                else:
                    print(f"   ❌ ERROR: Data and coordinates do NOT match user expectation!")
                    print(f"      data.shape[0]={plot2_data.shape[0]}, data.shape[1]={plot2_data.shape[1]}")
                    print(f"      len(px)={len(plot2_x_coords)}, len(py)={len(plot2_y_coords)}")
                    if not shape0_matches_x:
                        print(f"      data.shape[0]={plot2_data.shape[0]} != len(px)={len(plot2_x_coords)} (z should match x_coords)")
                    if not shape1_matches_y:
                        print(f"      data.shape[1]={plot2_data.shape[1]} != len(py)={len(plot2_y_coords)} (u should match y_coords)")
                    print(f"      This will cause misalignment between data and axes!")
            
            source2 = ColumnDataSource(
                data={
                    "image": [plot2_data],
                    "x": [float(np.min(plot2_x_coords))],
                    "y": [float(np.min(plot2_y_coords))],
                    "dw": [float(np.max(plot2_x_coords) - np.min(plot2_x_coords))],
                    "dh": [float(np.max(plot2_y_coords) - np.min(plot2_y_coords))],
                }
            )
            probe_min_val = float(np.percentile(plot2_data[~np.isnan(plot2_data)], 1))
            probe_max_val = float(np.percentile(plot2_data[~np.isnan(plot2_data)], 99))
            color_mapper2 = LinearColorMapper(palette="Viridis256", low=probe_min_val, high=probe_max_val)
            image_renderer2 = plot2.image(
                "image", source=source2, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper2
            )
            colorbar2 = ColorBar(color_mapper=color_mapper2, title="Plot2 Intensity", location=(0, 0))
            plot2.add_layout(colorbar2, "below")
        
        # Helper functions for coordinate/index conversion (needed before Plot2B creation)
        # Note: These functions will be redefined after sliders are created to use slider values
        def get_x_index(coord=None):
            """Get X index from coordinate or slider value."""
            if coord is None:
                # Try to get from slider if it exists, otherwise use middle value
                try:
                    coord = x_slider.value
                except (NameError, AttributeError):
                    coord = float(np.min(x_coords) + (np.max(x_coords) - np.min(x_coords)) / 2)
            # Find closest index
            idx = np.argmin(np.abs(x_coords - coord))
            return max(0, min(idx, len(x_coords) - 1))
        
        def get_y_index(coord=None):
            """Get Y index from coordinate or slider value."""
            if coord is None:
                # Try to get from slider if it exists, otherwise use middle value
                try:
                    coord = y_slider.value
                except (NameError, AttributeError):
                    coord = float(np.min(y_coords) + (np.max(y_coords) - np.min(y_coords)) / 2)
            # Find closest index
            idx = np.argmin(np.abs(y_coords - coord))
            return max(0, min(idx, len(y_coords) - 1))
        
        # Create Plot2B if enabled
        plot2b = None
        source2b = None
        color_mapper2b = None
        image_renderer2b = None
        colorbar2b = None
        probe_2d_plot_b = None
        plot2b_is_2d = False
        probe2b_min_val = None
        probe2b_max_val = None
        initial_slice_1d_b = None
        
        if hasattr(process_4dnexus, 'volume_picked_b') and process_4dnexus.volume_picked_b:
            try:
                # Load Plot2B volume - check cache first
                if (hasattr(process_4dnexus, '_cached_volume_b') and 
                    hasattr(process_4dnexus, '_cached_volume_b_path') and
                    process_4dnexus._cached_volume_b_path == process_4dnexus.volume_picked_b):
                    volume_b = process_4dnexus._cached_volume_b
                    print(f"✅ Using cached volume_b for {process_4dnexus.volume_picked_b}")
                else:
                    # Load and cache volume_b
                    volume_b = process_4dnexus.load_dataset_by_path(process_4dnexus.volume_picked_b)
                    if volume_b is not None:
                        process_4dnexus._cached_volume_b = volume_b
                        process_4dnexus._cached_volume_b_path = process_4dnexus.volume_picked_b
                        print(f"✅ Loaded and cached volume_b for {process_4dnexus.volume_picked_b} (type: {type(volume_b).__name__})")
                
                if volume_b is not None:
                    plot2b_is_2d = len(volume_b.shape) == 4
                    
                    # Get initial slice
                    x_idx = get_x_index()
                    y_idx = get_y_index()
                    
                    if plot2b_is_2d:
                        # 4D volume: 2D probe plot
                        initial_slice_b = volume_b[x_idx, y_idx, :, :]
                        
                        # Detect flip for Plot2B
                        plot2b_probe_x_coord_size = None
                        plot2b_probe_y_coord_size = None
                        if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                            plot2b_probe_x_coord_size = process_4dnexus.get_dataset_size_from_path(process_4dnexus.probe_x_coords_picked_b)
                        if hasattr(process_4dnexus, 'probe_y_coords_picked_b') and process_4dnexus.probe_y_coords_picked_b:
                            plot2b_probe_y_coord_size = process_4dnexus.get_dataset_size_from_path(process_4dnexus.probe_y_coords_picked_b)
                        
                        plot2b_needs_flip = process_4dnexus.detect_probe_flip_needed(
                            volume_b.shape,
                            plot2b_probe_x_coord_size,
                            plot2b_probe_y_coord_size
                        )
                        
                        # Get axis labels for Plot2B
                        # NOTE: Pass ORIGINAL labels to PROBE_2DPlot - it will handle swapping via get_flipped_x_axis_label()
                        original_plot2b_x_label = "Probe X"
                        original_plot2b_y_label = "Probe Y"
                        if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                            original_plot2b_x_label = process_4dnexus.probe_x_coords_picked_b.split('/')[-1] if '/' in process_4dnexus.probe_x_coords_picked_b else process_4dnexus.probe_x_coords_picked_b
                        if hasattr(process_4dnexus, 'probe_y_coords_picked_b') and process_4dnexus.probe_y_coords_picked_b:
                            original_plot2b_y_label = process_4dnexus.probe_y_coords_picked_b.split('/')[-1] if '/' in process_4dnexus.probe_y_coords_picked_b else process_4dnexus.probe_y_coords_picked_b
                        
                        # Load actual probe coordinate arrays for Plot2B (cache them for future use)
                        # Check if cached coordinates match current path - if not, clear cache and reload
                        cached_x_path_b = getattr(process_4dnexus, '_cached_probe_x_coords_path_b', None)
                        cached_y_path_b = getattr(process_4dnexus, '_cached_probe_y_coords_path_b', None)
                        current_x_path_b = getattr(process_4dnexus, 'probe_x_coords_picked_b', None)
                        current_y_path_b = getattr(process_4dnexus, 'probe_y_coords_picked_b', None)
                        
                        # Clear cache if path has changed
                        if cached_x_path_b != current_x_path_b:
                            process_4dnexus._cached_probe_x_coords_b = None
                            process_4dnexus._cached_probe_x_coords_path_b = None
                        if cached_y_path_b != current_y_path_b:
                            process_4dnexus._cached_probe_y_coords_b = None
                            process_4dnexus._cached_probe_y_coords_path_b = None
                        
                        plot2b_probe_x_coords_array = getattr(process_4dnexus, '_cached_probe_x_coords_b', None)
                        plot2b_probe_y_coords_array = getattr(process_4dnexus, '_cached_probe_y_coords_b', None)
                        
                        if plot2b_probe_x_coords_array is None and hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                            try:
                                plot2b_probe_x_coords_array = process_4dnexus.load_dataset_by_path(process_4dnexus.probe_x_coords_picked_b)
                                if plot2b_probe_x_coords_array is not None and plot2b_probe_x_coords_array.ndim == 1:
                                    plot2b_probe_x_coords_array = np.array(plot2b_probe_x_coords_array)
                                    process_4dnexus._cached_probe_x_coords_b = plot2b_probe_x_coords_array  # Cache for future use
                                    process_4dnexus._cached_probe_x_coords_path_b = process_4dnexus.probe_x_coords_picked_b  # Cache path
                            except:
                                plot2b_probe_x_coords_array = None
                        if plot2b_probe_y_coords_array is None and hasattr(process_4dnexus, 'probe_y_coords_picked_b') and process_4dnexus.probe_y_coords_picked_b:
                            try:
                                plot2b_probe_y_coords_array = process_4dnexus.load_dataset_by_path(process_4dnexus.probe_y_coords_picked_b)
                                if plot2b_probe_y_coords_array is not None and plot2b_probe_y_coords_array.ndim == 1:
                                    plot2b_probe_y_coords_array = np.array(plot2b_probe_y_coords_array)
                                    process_4dnexus._cached_probe_y_coords_b = plot2b_probe_y_coords_array  # Cache for future use
                                    process_4dnexus._cached_probe_y_coords_path_b = process_4dnexus.probe_y_coords_picked_b  # Cache path
                            except:
                                plot2b_probe_y_coords_array = None
                        
                        # Map probe coordinates to slice dimensions for Plot2B
                        # initial_slice_b has shape (z_size, u_size) from volume_b[x, y, :, :]
                        # Dimension 0 (rows, z) = z_size, Dimension 1 (cols, u) = u_size
                        # For PROBE_2DPlot: x_coords maps to columns (dimension 1), y_coords maps to rows (dimension 0)
                        if plot2b_probe_x_coords_array is not None and plot2b_probe_y_coords_array is not None:
                            # IMPORTANT: px (x_coords) ALWAYS goes on x-axis, py (y_coords) ALWAYS goes on y-axis
                            # We only transpose the DATA if dimensions don't match, but coordinates never swap
                            # The detect_probe_flip_needed() function determines if we need to transpose the data
                            # px always goes on x-axis, py always goes on y-axis
                            plot2b_x_coords_for_plot = plot2b_probe_x_coords_array  # px → x-axis
                            plot2b_y_coords_for_plot = plot2b_probe_y_coords_array  # py → y-axis
                        else:
                            # Fallback to indices if coordinate arrays not available
                            plot2b_x_coords_for_plot = np.arange(initial_slice_b.shape[1])
                            plot2b_y_coords_for_plot = np.arange(initial_slice_b.shape[0])
                        
                        # Create PROBE_2DPlot for Plot2B
                        # Pass original labels - the plot object will handle flipping via its methods
                        probe_2d_plot_b = PROBE_2DPlot(
                            title="Plot2B - 2D Probe View",
                            data=initial_slice_b,
                            x_coords=plot2b_x_coords_for_plot,
                            y_coords=plot2b_y_coords_for_plot,
                            palette="Viridis256",
                            color_scale=ColorScale.LINEAR,
                            range_mode=RangeMode.DYNAMIC,
                            x_axis_label=original_plot2b_x_label,  # Original label - px label always goes on x-axis
                            y_axis_label=original_plot2b_y_label,  # Original label - py label always goes on y-axis
                            needs_flip=plot2b_needs_flip,
                            track_changes=True,
                        )
                        
                        # Prepare data and coordinates for Bokeh plot using PROBE_2DPlot flipped methods
                        plot2b_data = probe_2d_plot_b.get_flipped_data()
                        plot2b_x_coords = probe_2d_plot_b.get_flipped_x_coords()
                        plot2b_y_coords = probe_2d_plot_b.get_flipped_y_coords()
                        
                        # If flipped methods return None, fall back to manual calculation
                        if plot2b_data is None:
                            plot2b_data = np.transpose(initial_slice_b)  # Always transpose for Bokeh
                        if plot2b_x_coords is None:
                            plot2b_x_coords = np.arange(plot2b_data.shape[1])
                        if plot2b_y_coords is None:
                            plot2b_y_coords = np.arange(plot2b_data.shape[0])
                        
                        # Create Bokeh figure (smaller size: 300x300)
                        plot2b = figure(
                            title="Plot2B - 2D Probe View",
                            tools="pan,wheel_zoom,box_zoom,reset,tap",
                            x_range=(float(np.min(plot2b_x_coords)), float(np.max(plot2b_x_coords))),
                            y_range=(float(np.min(plot2b_y_coords)), float(np.max(plot2b_y_coords))),
                            match_aspect=True,
                            width=300,
                            height=300,
                        )
                        
                        # Set axis labels using flipped methods from probe_2d_plot_b
                        plot2b.xaxis.axis_label = probe_2d_plot_b.get_flipped_x_axis_label() or original_plot2b_x_label
                        plot2b.yaxis.axis_label = probe_2d_plot_b.get_flipped_y_axis_label() or original_plot2b_y_label
                        
                        # Plot2B uses Bokeh's default auto-ticker (same as Plot2)
                        # This provides intelligent tick spacing based on plot size and data range
                        # No manual tick settings needed - Bokeh will automatically choose appropriate spacing
                        
                        # VERIFICATION: For 4D volume (x, y, z, u), Plot2B shows slice (z, u)
                        # - initial_slice_b = volume_b[:, :, :, :] gives shape (z, u) = (volume_b.shape[2], volume_b.shape[3])
                        # - We CANNOT assume data.shape[0] = y-axis and data.shape[1] = x-axis
                        # - Instead: z is from volume_b.shape[2], u is from volume_b.shape[3]
                        # - Bokeh image() interprets: data.shape[0] = rows = y-axis (height), data.shape[1] = cols = x-axis (width)
                        # - So we need to ensure z and u are correctly mapped to y and x axes based on coordinate arrays
                        print("🔍 VERIFICATION: Plot2B Bokeh image() data format expectations:")
                        print(f"   For 4D volume (x, y, z, u): slice has shape (z, u) = (volume_b.shape[2], volume_b.shape[3])")
                        print(f"   Bokeh interprets: data.shape[0] = rows = y-axis (height)")
                        print(f"   Bokeh interprets: data.shape[1] = cols = x-axis (width)")
                        print(f"   Our data.shape: {plot2b_data.shape if plot2b_data is not None else 'None'} (after flip if needed)")
                        if 'volume_b' in locals() or 'volume_b' in globals():
                            print(f"   Volume dimensions: z={volume_b.shape[2]}, u={volume_b.shape[3]}")
                        print(f"   Our x_coords (px) length: {len(plot2b_x_coords) if plot2b_x_coords is not None else 'None'} (should match data.shape[1])")
                        print(f"   Our y_coords (py) length: {len(plot2b_y_coords) if plot2b_y_coords is not None else 'None'} (should match data.shape[0])")
                        if plot2b_data is not None and plot2b_x_coords is not None and plot2b_y_coords is not None:
                            if plot2b_data.shape[1] == len(plot2b_x_coords) and plot2b_data.shape[0] == len(plot2b_y_coords):
                                print(f"   ✅ VERIFIED: Plot2B data format matches Bokeh expectations!")
                                print(f"      data.shape[1]={plot2b_data.shape[1]} == len(x_coords)={len(plot2b_x_coords)} (x-axis/width)")
                                print(f"      data.shape[0]={plot2b_data.shape[0]} == len(y_coords)={len(plot2b_y_coords)} (y-axis/height)")
                            else:
                                print(f"   ❌ ERROR: Plot2B data format does NOT match Bokeh expectations!")
                                print(f"      data.shape[1]={plot2b_data.shape[1]} != len(x_coords)={len(plot2b_x_coords)}")
                                print(f"      data.shape[0]={plot2b_data.shape[0]} != len(y_coords)={len(plot2b_y_coords)}")
                                print(f"      This will cause misalignment between data and axes!")
                        
                        source2b = ColumnDataSource(
                            data={
                                "image": [plot2b_data],
                                "x": [float(np.min(plot2b_x_coords))],
                                "y": [float(np.min(plot2b_y_coords))],
                                "dw": [float(np.max(plot2b_x_coords) - np.min(plot2b_x_coords))],
                                "dh": [float(np.max(plot2b_y_coords) - np.min(plot2b_y_coords))],
                            }
                        )
                        probe2b_min_val = float(np.percentile(plot2b_data[~np.isnan(plot2b_data)], 1))
                        probe2b_max_val = float(np.percentile(plot2b_data[~np.isnan(plot2b_data)], 99))
                        # Store for later use in range controls
                        color_mapper2b = LinearColorMapper(palette="Viridis256", low=probe2b_min_val, high=probe2b_max_val)
                        image_renderer2b = plot2b.image(
                            "image", source=source2b, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper2b
                        )
                        colorbar2b = ColorBar(color_mapper=color_mapper2b, title="Plot2B Intensity", location=(0, 0))
                        plot2b.add_layout(colorbar2b, "below")
                        
                        # Initialize rect2b for Plot2B selection
                        rect2b = Rectangle(0, 0, volume_b.shape[2] - 1, volume_b.shape[3] - 1)
                    else:
                        # 3D volume: 1D probe plot
                        initial_slice_1d_b = volume_b[x_idx, y_idx, :]
                        # Store for later use in range controls
                        probe2b_min_val = float(np.percentile(initial_slice_1d_b[~np.isnan(initial_slice_1d_b)], 1))
                        probe2b_max_val = float(np.percentile(initial_slice_1d_b[~np.isnan(initial_slice_1d_b)], 99))
                        probe_1d_plot_b = PROBE_1DPlot(
                            title="Plot2B - 1D Probe View",
                            data=initial_slice_1d_b,
                            x_coords=np.arange(len(initial_slice_1d_b)),
                            palette="Viridis256",
                            color_scale=ColorScale.LINEAR,
                            range_mode=RangeMode.DYNAMIC,
                            track_changes=True,
                        )
                        
                        # Create Bokeh figure for 1D plot (smaller size: 300x300)
                        plot2b = figure(
                            title="Plot2B - 1D Probe View",
                            tools="pan,wheel_zoom,box_zoom,reset,tap",
                            x_range=(0, len(initial_slice_1d_b)),
                            y_range=(float(np.min(initial_slice_1d_b)), float(np.max(initial_slice_1d_b))),
                            width=300,
                            height=300,
                        )
                        
                        # Set axis labels for 1D Plot2B
                        if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                            try:
                                probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                                if probe_coords_b is not None:
                                    plot2b.xaxis.axis_label = process_4dnexus.probe_x_coords_picked_b
                                else:
                                    plot2b.xaxis.axis_label = "Probe Index"
                            except:
                                plot2b.xaxis.axis_label = "Probe Index"
                        else:
                            plot2b.xaxis.axis_label = "Probe Index"
                        plot2b.yaxis.axis_label = "Intensity"
                        
                        source2b = ColumnDataSource(data={"x": np.arange(len(initial_slice_1d_b)), "y": initial_slice_1d_b})
                        plot2b.line("x", "y", source=source2b, line_width=2)
                        
                        # Initialize rect2b for Plot2B selection (1D)
                        rect2b = Rectangle(0, 0, volume_b.shape[2] - 1, volume_b.shape[2] - 1)
            except Exception as e:
                import traceback
                print(f"Failed to create Plot2B: {e}")
                traceback.print_exc()
        
        # Create Plot3 (Additional view) - empty initially, populated from Plot2 selections
        # Plot3 should match Plot1's orientation (respects flip) (smaller size: 300x300)
        # Use flipped coordinates from map_plot to ensure consistency
        plot3_x_coords = map_plot.get_flipped_x_coords()
        plot3_y_coords = map_plot.get_flipped_y_coords()
        
        plot3 = figure(
            title="Plot3 - Additional View",
            tools="pan,wheel_zoom,box_zoom,reset,tap",
            x_range=(float(np.min(plot3_x_coords)), float(np.max(plot3_x_coords))),
            y_range=(float(np.min(plot3_y_coords)), float(np.max(plot3_y_coords))),
            width=300,
            height=300,
        )
        plot3.xaxis.axis_label = map_plot.get_flipped_x_axis_label()
        plot3.yaxis.axis_label = map_plot.get_flipped_y_axis_label()
        
        # Create empty source3; Plot3 will be populated on demand
        source3 = ColumnDataSource(
            data={
                "image": [],
                "x": [],
                "y": [],
                "dw": [],
                "dh": [],
            }
        )
        
        # Create color mapper for Plot3
        color_mapper3 = LinearColorMapper(palette="Viridis256", low=0.0, high=1.0)
        image_renderer3 = plot3.image(
            "image", source=source3, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper3
        )
        colorbar3 = ColorBar(color_mapper=color_mapper3, title="Plot3 Intensity", location=(0, 0))
        plot3.add_layout(colorbar3, "below")
        
        # Create sliders using SCLib UI
        x_slider = create_slider(
            title="X",
            start=float(np.min(x_coords)),
            end=float(np.max(x_coords)),
            value=float(np.min(x_coords) + (np.max(x_coords) - np.min(x_coords)) / 2),
            step=0.01,
            width=200
        )
        
        y_slider = create_slider(
            title="Y",
            start=float(np.min(y_coords)),
            end=float(np.max(y_coords)),
            value=float(np.min(y_coords) + (np.max(y_coords) - np.min(y_coords)) / 2),
            step=0.01,
            width=200
        )
        
        # Function to update Plot2 based on crosshair position
        def show_slice():
            """Update Plot2 based on current crosshair position (x_index, y_index)."""
            x_idx = get_x_index()
            y_idx = get_y_index()
            
            if is_3d_volume:
                # For 3D: update 1D line plot
                slice_1d = volume[x_idx, y_idx, :]
                # Try to use probe coordinates if available
                if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                    try:
                        probe_coords = process_4dnexus.load_probe_coordinates()
                        if probe_coords is not None and len(probe_coords) == len(slice_1d):
                            x_coords_1d = probe_coords
                        else:
                            x_coords_1d = np.arange(len(slice_1d))
                    except:
                        x_coords_1d = np.arange(len(slice_1d))
                else:
                    x_coords_1d = np.arange(len(slice_1d))
                
                source2.data = {"x": x_coords_1d, "y": slice_1d}
                plot2.x_range.start = float(np.min(x_coords_1d))
                plot2.x_range.end = float(np.max(x_coords_1d))
                
                # Update y-range based on mode
                if 'range2_min_input' in locals() and range2_min_input is not None and not range2_min_input.disabled:
                    # User Specified mode - use input values
                    try:
                        min_val = float(range2_min_input.value) if range2_min_input.value else float(np.min(slice_1d))
                        max_val = float(range2_max_input.value) if range2_max_input.value else float(np.max(slice_1d))
                        plot2.y_range.start = min_val
                        plot2.y_range.end = max_val
                    except:
                        # Fallback to data range if input is invalid
                        plot2.y_range.start = float(np.min(slice_1d))
                        plot2.y_range.end = float(np.max(slice_1d))
                else:
                    # Dynamic mode - recompute from current slice
                    probe_min = float(np.percentile(slice_1d[~np.isnan(slice_1d)], 1))
                    probe_max = float(np.percentile(slice_1d[~np.isnan(slice_1d)], 99))
                    plot2.y_range.start = probe_min
                    plot2.y_range.end = probe_max
                    # Update range inputs if they exist
                    if 'range2_min_input' in locals() and range2_min_input is not None:
                        range2_min_input.value = str(probe_min)
                        range2_max_input.value = str(probe_max)
            else:
                # For 4D: update 2D image plot
                slice_2d = volume[x_idx, y_idx, :, :]  # This is (z, u)
                
                # Update probe_2d_plot's data and use its flipped methods
                probe_2d_plot.data = slice_2d
                
                # Get flipped data and coordinates from probe_2d_plot
                flipped_slice = probe_2d_plot.get_flipped_data()
                x_coords = probe_2d_plot.get_flipped_x_coords()
                y_coords = probe_2d_plot.get_flipped_y_coords()
                
                # Fallback if flipped methods return None
                if flipped_slice is None:
                    flipped_slice = np.transpose(slice_2d)  # Always transpose for Bokeh
                if x_coords is None:
                    x_coords = np.arange(flipped_slice.shape[1])
                if y_coords is None:
                    y_coords = np.arange(flipped_slice.shape[0])
                
                # Calculate dimensions
                dw = float(np.max(x_coords) - np.min(x_coords)) if len(x_coords) > 0 else float(flipped_slice.shape[1])
                dh = float(np.max(y_coords) - np.min(y_coords)) if len(y_coords) > 0 else float(flipped_slice.shape[0])
                
                source2.data = {
                    "image": [flipped_slice],
                    "x": [float(np.min(x_coords))],
                    "y": [float(np.min(y_coords))],
                    "dw": [dw],
                    "dh": [dh],
                }
                
                # Update plot ranges to match coordinate arrays
                plot2.x_range.start = float(np.min(x_coords))
                plot2.x_range.end = float(np.max(x_coords))
                plot2.y_range.start = float(np.min(y_coords))
                plot2.y_range.end = float(np.max(y_coords))
                # Update color mapper range (only if in Dynamic mode)
                # If in User Specified mode, keep the user-set values
                # Check if range2_min_input exists and is not disabled (User Specified mode)
                if 'range2_min_input' in locals() and range2_min_input is not None and not range2_min_input.disabled:
                    # User Specified mode - use input values
                    try:
                        min_val = float(range2_min_input.value) if range2_min_input.value else probe_min
                        max_val = float(range2_max_input.value) if range2_max_input.value else probe_max
                        color_mapper2.low = min_val
                        color_mapper2.high = max_val
                    except:
                        # Fallback to percentile if input is invalid
                        probe_min = float(np.percentile(flipped_slice[~np.isnan(flipped_slice)], 1))
                        probe_max = float(np.percentile(flipped_slice[~np.isnan(flipped_slice)], 99))
                        color_mapper2.low = probe_min
                        color_mapper2.high = probe_max
                else:
                    # Dynamic mode - recompute from current slice
                    probe_min = float(np.percentile(flipped_slice[~np.isnan(flipped_slice)], 1))
                    probe_max = float(np.percentile(flipped_slice[~np.isnan(flipped_slice)], 99))
                    color_mapper2.low = probe_min
                    color_mapper2.high = probe_max
                    # Update range inputs if they exist
                    if 'range2_min_input' in locals() and range2_min_input is not None:
                        range2_min_input.value = str(probe_min)
                        range2_max_input.value = str(probe_max)
        
        # Function to update Plot2B based on crosshair position
        def show_slice_b():
            """Update Plot2B based on current crosshair position (x_index, y_index)."""
            if plot2b is None:
                return
            
            x_idx = get_x_index()
            y_idx = get_y_index()
            
            if plot2b_is_2d:
                # 4D volume: update 2D image plot
                if hasattr(process_4dnexus, 'volume_picked_b') and process_4dnexus.volume_picked_b and probe_2d_plot_b is not None:
                    try:
                        # Use cached volume_b if available
                        if (hasattr(process_4dnexus, '_cached_volume_b') and 
                            hasattr(process_4dnexus, '_cached_volume_b_path') and
                            process_4dnexus._cached_volume_b_path == process_4dnexus.volume_picked_b):
                            volume_b = process_4dnexus._cached_volume_b
                        else:
                            # Load and cache volume_b
                            volume_b = process_4dnexus.load_dataset_by_path(process_4dnexus.volume_picked_b)
                            if volume_b is not None:
                                process_4dnexus._cached_volume_b = volume_b
                                process_4dnexus._cached_volume_b_path = process_4dnexus.volume_picked_b
                        
                        if volume_b is not None:
                            new_slice_b = volume_b[x_idx, y_idx, :, :]
                            
                            # Update probe_2d_plot_b's data and use its flipped methods
                            probe_2d_plot_b.data = new_slice_b
                            
                            # Get flipped data and coordinates from probe_2d_plot_b
                            flipped_slice_b = probe_2d_plot_b.get_flipped_data()
                            x_coords_b = probe_2d_plot_b.get_flipped_x_coords()
                            y_coords_b = probe_2d_plot_b.get_flipped_y_coords()
                            
                            # Fallback if flipped methods return None
                            if flipped_slice_b is None:
                                flipped_slice_b = np.transpose(new_slice_b)  # Always transpose for Bokeh
                            if x_coords_b is None:
                                x_coords_b = np.arange(flipped_slice_b.shape[1])
                            if y_coords_b is None:
                                y_coords_b = np.arange(flipped_slice_b.shape[0])
                            
                            # Calculate dimensions
                            dw_b = float(np.max(x_coords_b) - np.min(x_coords_b)) if len(x_coords_b) > 0 else float(flipped_slice_b.shape[1])
                            dh_b = float(np.max(y_coords_b) - np.min(y_coords_b)) if len(y_coords_b) > 0 else float(flipped_slice_b.shape[0])
                            
                            source2b.data = {
                                "image": [flipped_slice_b],
                                "x": [float(np.min(x_coords_b))],
                                "y": [float(np.min(y_coords_b))],
                                "dw": [dw_b],
                                "dh": [dh_b],
                            }
                            
                            # Update plot ranges to match coordinate arrays
                            plot2b.x_range.start = float(np.min(x_coords_b))
                            plot2b.x_range.end = float(np.max(x_coords_b))
                            plot2b.y_range.start = float(np.min(y_coords_b))
                            plot2b.y_range.end = float(np.max(y_coords_b))
                            
                            # Plot2B uses Bokeh's default auto-ticker (same as Plot2)
                            # No manual tick updates needed - Bokeh will automatically adjust ticks when data changes
                            
                            # Update range dynamically if in Dynamic mode
                            if 'range2b_min_input' in locals() and range2b_min_input is not None:
                                if range2b_min_input.disabled:  # Dynamic mode
                                    probe2b_min = float(np.percentile(flipped_slice_b[~np.isnan(flipped_slice_b)], 1))
                                    probe2b_max = float(np.percentile(flipped_slice_b[~np.isnan(flipped_slice_b)], 99))
                                    range2b_min_input.value = str(probe2b_min)
                                    range2b_max_input.value = str(probe2b_max)
                                    color_mapper2b.low = probe2b_min
                                    color_mapper2b.high = probe2b_max
                                else:  # User Specified mode
                                    try:
                                        min_val = float(range2b_min_input.value) if range2b_min_input.value else probe2b_min
                                        max_val = float(range2b_max_input.value) if range2b_max_input.value else probe2b_max
                                        color_mapper2b.low = min_val
                                        color_mapper2b.high = max_val
                                    except:
                                        pass
                    except Exception as e:
                        print(f"Error updating Plot2B: {e}")
            else:
                # 3D volume: update 1D line plot
                if hasattr(process_4dnexus, 'volume_picked_b') and process_4dnexus.volume_picked_b:
                    try:
                        # Use cached volume_b if available
                        if (hasattr(process_4dnexus, '_cached_volume_b') and 
                            hasattr(process_4dnexus, '_cached_volume_b_path') and
                            process_4dnexus._cached_volume_b_path == process_4dnexus.volume_picked_b):
                            volume_b = process_4dnexus._cached_volume_b
                        else:
                            # Load and cache volume_b
                            volume_b = process_4dnexus.load_dataset_by_path(process_4dnexus.volume_picked_b)
                            if volume_b is not None:
                                process_4dnexus._cached_volume_b = volume_b
                                process_4dnexus._cached_volume_b_path = process_4dnexus.volume_picked_b
                        
                        if volume_b is not None:
                            slice_1d_b = volume_b[x_idx, y_idx, :]
                            
                            # Try to use probe coordinates if available
                            if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                                try:
                                    probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                                    if probe_coords_b is not None and len(probe_coords_b) == len(slice_1d_b):
                                        x_coords_1d_b = probe_coords_b
                                    else:
                                        x_coords_1d_b = np.arange(len(slice_1d_b))
                                except:
                                    x_coords_1d_b = np.arange(len(slice_1d_b))
                            else:
                                x_coords_1d_b = np.arange(len(slice_1d_b))
                            
                            source2b.data = {"x": x_coords_1d_b, "y": slice_1d_b}
                            plot2b.x_range.start = float(np.min(x_coords_1d_b))
                            plot2b.x_range.end = float(np.max(x_coords_1d_b))
                            
                            # Update range dynamically if in Dynamic mode
                            if 'range2b_min_input' in locals() and range2b_min_input is not None:
                                if range2b_min_input.disabled:  # Dynamic mode
                                    probe2b_min = float(np.percentile(slice_1d_b[~np.isnan(slice_1d_b)], 1))
                                    probe2b_max = float(np.percentile(slice_1d_b[~np.isnan(slice_1d_b)], 99))
                                    range2b_min_input.value = str(probe2b_min)
                                    range2b_max_input.value = str(probe2b_max)
                                    plot2b.y_range.start = probe2b_min
                                    plot2b.y_range.end = probe2b_max
                                else:  # User Specified mode
                                    try:
                                        min_val = float(range2b_min_input.value) if range2b_min_input.value else float(np.min(slice_1d_b))
                                        max_val = float(range2b_max_input.value) if range2b_max_input.value else float(np.max(slice_1d_b))
                                        plot2b.y_range.start = min_val
                                        plot2b.y_range.end = max_val
                                    except:
                                        plot2b.y_range.start = float(np.min(slice_1d_b))
                                        plot2b.y_range.end = float(np.max(slice_1d_b))
                    except Exception as e:
                        print(f"Error updating Plot2B: {e}")
        
        # Slider callbacks to update crosshairs and Plot2
        def on_x_slider_change(attr, old, new):
            try:
                draw_cross1()
                show_slice()
                # Update Plot1 range dynamically if in Dynamic mode
                if map_plot.range_mode == RangeMode.DYNAMIC:
                    update_plot1_range_dynamic()
                # Update Plot2 range dynamically if in Dynamic mode
                if 'range2_min_input' in locals() and range2_min_input is not None and range2_min_input.disabled:
                    update_plot2_range_dynamic()
                # Update Plot2B if it exists
                show_slice_b()
            except Exception as e:
                print(f"⚠️ ERROR in on_x_slider_change(): {e}")
                import traceback
                traceback.print_exc()
        
        def on_y_slider_change(attr, old, new):
            try:
                draw_cross1()
                show_slice()
                # Update Plot1 range dynamically if in Dynamic mode
                if map_plot.range_mode == RangeMode.DYNAMIC:
                    update_plot1_range_dynamic()
                # Update Plot2 range dynamically if in Dynamic mode
                if 'range2_min_input' in locals() and range2_min_input is not None and range2_min_input.disabled:
                    update_plot2_range_dynamic()
                # Update Plot2B if it exists
                show_slice_b()
            except Exception as e:
                print(f"⚠️ ERROR in on_y_slider_change(): {e}")
                import traceback
                traceback.print_exc()
        
        # Connect slider callbacks
        try:
            x_slider.on_change("value", on_x_slider_change)
            y_slider.on_change("value", on_y_slider_change)
            print("✅ Sliders connected successfully")
        except Exception as e:
            print(f"⚠️ ERROR connecting sliders: {e}")
            import traceback
            traceback.print_exc()
        
        # Tap handler for Plot1 to update crosshairs (defined after sliders are created)
        def on_plot1_tap(event):
            """Handle tap events on Plot1 to update crosshair position."""
            # Bokeh tap events have x and y attributes
            # The plot axes are already in flipped order, so we need to convert back to original indices
            if hasattr(event, 'x') and hasattr(event, 'y'):
                # Find closest indices in the flipped coordinate arrays
                x_idx = np.argmin(np.abs(plot1_x_coords - event.x))
                y_idx = np.argmin(np.abs(plot1_y_coords - event.y))
                
                # Convert back to original coordinate space for sliders
                # Sliders use original x_coords and y_coords (not flipped)
                if map_plot.needs_flip:
                    # When flipped: plot1_x_coords is actually y_coords, plot1_y_coords is actually x_coords
                    x_slider.value = y_coords[y_idx] if y_idx < len(y_coords) else y_coords[-1]
                    y_slider.value = x_coords[x_idx] if x_idx < len(x_coords) else x_coords[-1]
                else:
                    # Not flipped: plot1_x_coords is x_coords, plot1_y_coords is y_coords
                    x_slider.value = x_coords[x_idx] if x_idx < len(x_coords) else x_coords[-1]
                    y_slider.value = y_coords[y_idx] if y_idx < len(y_coords) else y_coords[-1]
                # Note: Setting slider.value will trigger on_x_slider_change/on_y_slider_change
                # which will call draw_cross1() and show_slice()
        
        # Draw initial crosshairs
        try:
            draw_cross1()
            print("✅ Initial crosshairs drawn successfully")
        except Exception as e:
            print(f"⚠️ ERROR drawing initial crosshairs: {e}")
            import traceback
            traceback.print_exc()
        
        # Create Plot1B if enabled
        plot1b = None
        source1b = None
        color_mapper1b = None
        image_renderer1b = None
        colorbar1b = None
        map_plot_b = None
        map1b_min_val = None
        map1b_max_val = None
        
        if hasattr(process_4dnexus, 'plot1b_single_dataset_picked') and process_4dnexus.plot1b_single_dataset_picked:
            try:
                # Load Plot1B dataset
                single_dataset_b = process_4dnexus.load_dataset_by_path(process_4dnexus.plot1b_single_dataset_picked)
                if single_dataset_b is not None:
                    # Flatten if needed and reshape
                    if single_dataset_b.ndim > 1:
                        single_dataset_b_flat = single_dataset_b.flatten()
                    else:
                        single_dataset_b_flat = single_dataset_b
                    
                    if single_dataset_b_flat.size == len(x_coords) * len(y_coords):
                        preview_b_rect = np.reshape(single_dataset_b_flat, (len(x_coords), len(y_coords)))
                        # Clean and normalize
                        preview_b = np.nan_to_num(preview_b_rect, nan=0.0, posinf=0.0, neginf=0.0)
                        if np.max(preview_b) > np.min(preview_b):
                            preview_b = (preview_b - np.min(preview_b)) / (np.max(preview_b) - np.min(preview_b))
                        preview_b = preview_b.astype(np.float32)
                        
                        # Detect flip for Plot1B
                        plot1b_needs_flip = process_4dnexus.detect_map_flip_needed(
                            preview_b.shape,
                            process_4dnexus.get_dataset_size_from_path(process_4dnexus.x_coords_picked) if process_4dnexus.x_coords_picked else None,
                            process_4dnexus.get_dataset_size_from_path(process_4dnexus.y_coords_picked) if process_4dnexus.y_coords_picked else None
                        )
                        
                        # Create Plot1B using MAP_2DPlot
                        # Use original_map_x_label and original_map_y_label (same as Plot1)
                        # The plot object will handle flipping via its methods
                        map_plot_b = MAP_2DPlot(
                            title="Plot1B - Map View (Duplicate)",
                            data=preview_b,
                            x_coords=x_coords,
                            y_coords=y_coords,
                            palette="Viridis256",
                            color_scale=ColorScale.LINEAR,
                            range_mode=RangeMode.DYNAMIC,
                            crosshairs_enabled=True,
                            x_axis_label=original_map_x_label,  # Original label - will be swapped by get_flipped_x_axis_label() if needed
                            y_axis_label=original_map_y_label,  # Original label - will be swapped by get_flipped_y_axis_label() if needed
                            needs_flip=plot1b_needs_flip,
                            track_changes=True,
                        )
                        
                        # Get flipped data and coordinates
                        plot1b_data = map_plot_b.get_flipped_data() if map_plot_b.needs_flip else preview_b
                        plot1b_x_coords = map_plot_b.get_flipped_x_coords() if map_plot_b.needs_flip else x_coords
                        plot1b_y_coords = map_plot_b.get_flipped_y_coords() if map_plot_b.needs_flip else y_coords
                        
                        # Calculate initial plot dimensions from map_plot_b
                        initial_width_b, initial_height_b = map_plot_b.calculate_plot_dimensions()
                        
                        # Create Bokeh figure for Plot1B (use calculated dimensions)
                        plot1b = figure(
                            title="Plot1B - Map View (Duplicate)",
                            x_range=(float(np.min(plot1b_x_coords)), float(np.max(plot1b_x_coords))),
                            y_range=(float(np.min(plot1b_y_coords)), float(np.max(plot1b_y_coords))),
                            tools="pan,wheel_zoom,box_zoom,reset,tap",
                            match_aspect=True,
                            width=initial_width_b,
                            height=initial_height_b,
                        )
                        
                        plot1b.xaxis.axis_label = map_plot_b.get_flipped_x_axis_label()
                        plot1b.yaxis.axis_label = map_plot_b.get_flipped_y_axis_label()
                        
                        source1b = ColumnDataSource(
                            data={
                                "image": [plot1b_data],
                                "x": [float(np.min(plot1b_x_coords))],
                                "y": [float(np.min(plot1b_y_coords))],
                                "dw": [float(np.max(plot1b_x_coords) - np.min(plot1b_x_coords))],
                                "dh": [float(np.max(plot1b_y_coords) - np.min(plot1b_y_coords))],
                            }
                        )
                        
                        map1b_min_val = float(np.percentile(plot1b_data[~np.isnan(plot1b_data)], 1))
                        map1b_max_val = float(np.percentile(plot1b_data[~np.isnan(plot1b_data)], 99))
                        # Store for later use in range controls
                        color_mapper1b = LinearColorMapper(palette="Viridis256", low=map1b_min_val, high=map1b_max_val)
                        image_renderer1b = plot1b.image(
                            "image", source=source1b, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper1b
                        )
                        colorbar1b = ColorBar(color_mapper=color_mapper1b, title="Plot1B Intensity", location=(0, 0))
                        plot1b.add_layout(colorbar1b, "below")
                        
                        # Initialize rect1b for Plot1B crosshairs
                        rect1b = Rectangle(0, 0, volume.shape[0] - 1, volume.shape[1] - 1)
                        
                        # Tap handler for Plot1B (updates sliders, which updates both Plot1 and Plot1B crosshairs)
                        def on_plot1b_tap(event):
                            """Handle tap events on Plot1B to update crosshair position."""
                            if hasattr(event, 'x') and hasattr(event, 'y'):
                                # Find closest indices in Plot1B's flipped coordinate arrays
                                plot1b_x_coords = map_plot_b.get_flipped_x_coords()
                                plot1b_y_coords = map_plot_b.get_flipped_y_coords()
                                x_idx = np.argmin(np.abs(plot1b_x_coords - event.x))
                                y_idx = np.argmin(np.abs(plot1b_y_coords - event.y))
                                
                                # Convert back to original coordinate space for sliders
                                if map_plot_b.needs_flip:
                                    x_slider.value = y_coords[y_idx] if y_idx < len(y_coords) else y_coords[-1]
                                    y_slider.value = x_coords[x_idx] if x_idx < len(x_coords) else x_coords[-1]
                                else:
                                    x_slider.value = x_coords[x_idx] if x_idx < len(x_coords) else x_coords[-1]
                                    y_slider.value = y_coords[y_idx] if y_idx < len(y_coords) else y_coords[-1]
                                draw_cross1()  # This will also update Plot1B crosshairs
                                show_slice()
                        
                        # Add TapTool to Plot1B and connect handler
                        tap_tool1b = TapTool()
                        plot1b.add_tools(tap_tool1b)
                        plot1b.on_event("tap", on_plot1b_tap)
                        
                        # Draw initial crosshairs on Plot1B
                        draw_cross1b()
            except Exception as e:
                import traceback
                print(f"Failed to create Plot1B: {e}")
                traceback.print_exc()
        elif hasattr(process_4dnexus, 'presample_picked_b') and hasattr(process_4dnexus, 'postsample_picked_b') and \
             process_4dnexus.presample_picked_b and process_4dnexus.postsample_picked_b:
            try:
                # Ratio mode for Plot1B
                presample_b = process_4dnexus.load_dataset_by_path(process_4dnexus.presample_picked_b)
                postsample_b = process_4dnexus.load_dataset_by_path(process_4dnexus.postsample_picked_b)
                if presample_b is not None and postsample_b is not None:
                    epsilon = 1e-10
                    presample_b = np.where(presample_b == 0, epsilon, presample_b)
                    postsample_b = np.where(postsample_b == 0, epsilon, postsample_b)
                    presample_b = presample_b.reshape(len(x_coords), len(y_coords))
                    postsample_b = postsample_b.reshape(len(x_coords), len(y_coords))
                    preview_b = presample_b / postsample_b
                    preview_b = np.nan_to_num(preview_b, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)
                    if np.max(preview_b) > np.min(preview_b):
                        preview_b = (preview_b - np.min(preview_b)) / (np.max(preview_b) - np.min(preview_b))
                    
                    # Detect flip for Plot1B
                    plot1b_needs_flip = process_4dnexus.detect_map_flip_needed(
                        preview_b.shape,
                        process_4dnexus.get_dataset_size_from_path(process_4dnexus.x_coords_picked) if process_4dnexus.x_coords_picked else None,
                        process_4dnexus.get_dataset_size_from_path(process_4dnexus.y_coords_picked) if process_4dnexus.y_coords_picked else None
                    )
                    
                    # Create Plot1B using MAP_2DPlot
                    # Use original_map_x_label and original_map_y_label (same as Plot1)
                    # The plot object will handle flipping via its methods
                    map_plot_b = MAP_2DPlot(
                        title="Plot1B - Map View (Duplicate)",
                        data=preview_b,
                        x_coords=x_coords,
                        y_coords=y_coords,
                        palette="Viridis256",
                        color_scale=ColorScale.LINEAR,
                        range_mode=RangeMode.DYNAMIC,
                        crosshairs_enabled=True,
                        x_axis_label=original_map_x_label,  # Original label - will be swapped by get_flipped_x_axis_label() if needed
                        y_axis_label=original_map_y_label,  # Original label - will be swapped by get_flipped_y_axis_label() if needed
                        needs_flip=plot1b_needs_flip,
                        track_changes=True,
                    )
                    
                    # Get flipped data and coordinates
                    plot1b_data = map_plot_b.get_flipped_data() if map_plot_b.needs_flip else preview_b
                    plot1b_x_coords = map_plot_b.get_flipped_x_coords() if map_plot_b.needs_flip else x_coords
                    plot1b_y_coords = map_plot_b.get_flipped_y_coords() if map_plot_b.needs_flip else y_coords
                    
                    # Calculate initial plot dimensions from map_plot_b
                    initial_width_b, initial_height_b = map_plot_b.calculate_plot_dimensions()
                    
                    # Create Bokeh figure for Plot1B (use calculated dimensions)
                    plot1b = figure(
                        title="Plot1B - Map View (Duplicate)",
                        x_range=(float(np.min(plot1b_x_coords)), float(np.max(plot1b_x_coords))),
                        y_range=(float(np.min(plot1b_y_coords)), float(np.max(plot1b_y_coords))),
                        tools="pan,wheel_zoom,box_zoom,reset,tap",
                        match_aspect=True,
                        width=initial_width_b,
                        height=initial_height_b,
                    )
                    
                    plot1b.xaxis.axis_label = map_plot_b.get_flipped_x_axis_label()
                    plot1b.yaxis.axis_label = map_plot_b.get_flipped_y_axis_label()
                    
                    source1b = ColumnDataSource(
                        data={
                            "image": [plot1b_data],
                            "x": [float(np.min(plot1b_x_coords))],
                            "y": [float(np.min(plot1b_y_coords))],
                            "dw": [float(np.max(plot1b_x_coords) - np.min(plot1b_x_coords))],
                            "dh": [float(np.max(plot1b_y_coords) - np.min(plot1b_y_coords))],
                        }
                    )
                    
                    map1b_min_val = float(np.percentile(plot1b_data[~np.isnan(plot1b_data)], 1))
                    map1b_max_val = float(np.percentile(plot1b_data[~np.isnan(plot1b_data)], 99))
                    color_mapper1b = LinearColorMapper(palette="Viridis256", low=map1b_min_val, high=map1b_max_val)
                    image_renderer1b = plot1b.image(
                        "image", source=source1b, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper1b
                    )
                    colorbar1b = ColorBar(color_mapper=color_mapper1b, title="Plot1B Intensity", location=(0, 0))
                    plot1b.add_layout(colorbar1b, "below")
                    
                    # Initialize rect1b for Plot1B crosshairs
                    rect1b = Rectangle(0, 0, volume.shape[0] - 1, volume.shape[1] - 1)
                    
                    # Tap handler for Plot1B
                    def on_plot1b_tap(event):
                        """Handle tap events on Plot1B to update crosshair position."""
                        if hasattr(event, 'x') and hasattr(event, 'y'):
                            # Find closest indices in Plot1B's flipped coordinate arrays
                            plot1b_x_coords = map_plot_b.get_flipped_x_coords()
                            plot1b_y_coords = map_plot_b.get_flipped_y_coords()
                            x_idx = np.argmin(np.abs(plot1b_x_coords - event.x))
                            y_idx = np.argmin(np.abs(plot1b_y_coords - event.y))
                            
                            # Convert back to original coordinate space for sliders
                            if map_plot_b.needs_flip:
                                x_slider.value = y_coords[y_idx] if y_idx < len(y_coords) else y_coords[-1]
                                y_slider.value = x_coords[x_idx] if x_idx < len(x_coords) else x_coords[-1]
                            else:
                                x_slider.value = x_coords[x_idx] if x_idx < len(x_coords) else x_coords[-1]
                                y_slider.value = y_coords[y_idx] if y_idx < len(y_coords) else y_coords[-1]
                            draw_cross1()  # This will also update Plot1B crosshairs
                            show_slice()
                    
                    # Add TapTool to Plot1B and connect handler
                    tap_tool1b = TapTool()
                    plot1b.add_tools(tap_tool1b)
                    plot1b.on_event("tap", on_plot1b_tap)
                    
                    # Draw initial crosshairs on Plot1B
                    draw_cross1b()
            except Exception as e:
                import traceback
                print(f"Failed to create Plot1B (ratio mode): {e}")
                traceback.print_exc()
        
        # Helper function to draw selection rectangles on plots
        def draw_rect(p, r, x1, x2, y1, y2, line_color="yellow", line_width=2):
            """Draw a rectangle on a plot using lines."""
            # Clear existing rectangle lines
            if r.h1line is not None:
                try:
                    p.renderers.remove(r.h1line)
                except:
                    pass
            if r.h2line is not None:
                try:
                    p.renderers.remove(r.h2line)
                except:
                    pass
            if r.v1line is not None:
                try:
                    p.renderers.remove(r.v1line)
                except:
                    pass
            if r.v2line is not None:
                try:
                    p.renderers.remove(r.v2line)
                except:
                    pass
            
            # Draw new rectangle
            r.h1line = p.line(x=[x1, x2], y=[y1, y1], line_color=line_color, line_width=line_width)
            r.h2line = p.line(x=[x1, x2], y=[y2, y2], line_color=line_color, line_width=line_width)
            r.v1line = p.line(x=[x1, x1], y=[y1, y2], line_color=line_color, line_width=line_width)
            r.v2line = p.line(x=[x2, x2], y=[y1, y2], line_color=line_color, line_width=line_width)
        
        def clear_rect(p, r):
            """Clear rectangle from plot."""
            if r.h1line is not None:
                try:
                    p.renderers.remove(r.h1line)
                except:
                    pass
                r.h1line = None
            if r.h2line is not None:
                try:
                    p.renderers.remove(r.h2line)
                except:
                    pass
                r.h2line = None
            if r.v1line is not None:
                try:
                    p.renderers.remove(r.v1line)
                except:
                    pass
                r.v1line = None
            if r.v2line is not None:
                try:
                    p.renderers.remove(r.v2line)
                except:
                    pass
                r.v2line = None
        
        # Add TapTool to Plot2 for region selection (Plot2 should NOT have crosshairs)
        tap_tool2 = TapTool()
        plot2.add_tools(tap_tool2)
        
        # Tap handler for Plot2 to set selection region
        def on_plot2_tap(event):
            """Handle tap events on Plot2 to set selection region."""
            if is_3d_volume:
                # For 3D: only use x-coordinate
                if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                    try:
                        probe_coords = process_4dnexus.load_probe_coordinates()
                        if probe_coords is not None:
                            z_index = int(np.argmin(np.abs(probe_coords - event.x)))
                        else:
                            z_index = int(event.x)
                    except:
                        z_index = int(event.x)
                else:
                    z_index = int(event.x)
                
                if event.modifiers.get("shift", False):
                    rect2.set(min_x=z_index, min_y=z_index)
                elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta', False) or event.modifiers.get('cmd', False):
                    rect2.set(max_x=z_index, max_y=z_index)
                else:
                    # Regular click: set both to same value
                    rect2.set(min_x=z_index, min_y=z_index, max_x=z_index, max_y=z_index)
                    clear_rect(plot2, rect2)
                    draw_rect(plot2, rect2, z_index, z_index, 0, plot2.y_range.end)
            else:
                # For 4D: use both x and y coordinates
                # Plot2 uses flipped coordinates, so we need to convert event coordinates to indices
                # using the flipped coordinate arrays
                plot2_x_coords = probe_2d_plot.get_flipped_x_coords()
                plot2_y_coords = probe_2d_plot.get_flipped_y_coords()
                
                # Find closest indices in flipped coordinate arrays
                click_u_idx = int(np.argmin(np.abs(plot2_x_coords - event.x))) if plot2_x_coords is not None else int(event.x)
                click_z_idx = int(np.argmin(np.abs(plot2_y_coords - event.y))) if plot2_y_coords is not None else int(event.y)
                
                # Convert back to original coordinate space (rect2 stores original indices)
                # The flipped coordinates correspond to swapped dimensions
                if probe_2d_plot.needs_flip:
                    # When flipped: plot2_x_coords is actually probe_y (u), plot2_y_coords is actually probe_x (z)
                    click_z = click_z_idx  # This is actually the z dimension index
                    click_u = click_u_idx  # This is actually the u dimension index
                else:
                    # Not flipped: plot2_x_coords is probe_x (z), plot2_y_coords is probe_y (u)
                    click_z = click_u_idx  # This is the z dimension index
                    click_u = click_z_idx  # This is the u dimension index
                
                if event.modifiers.get("shift", False):
                    rect2.set(min_x=click_z, min_y=click_u)
                elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta', False) or event.modifiers.get('cmd', False):
                    rect2.set(max_x=click_z, max_y=click_u)
                else:
                    # Regular click: set both to same value
                    rect2.set(min_x=click_z, min_y=click_u, max_x=click_z, max_y=click_u)
                    clear_rect(plot2, rect2)
                    draw_rect(plot2, rect2, click_z, click_z, click_u, click_u)
        
        # Double-tap handler for Plot2 (sets max coordinates)
        def on_plot2_doubletap(event):
            """Handle double-tap events on Plot2 to set max coordinates."""
            if is_3d_volume:
                if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                    try:
                        probe_coords = process_4dnexus.load_probe_coordinates()
                        if probe_coords is not None:
                            z_index = int(np.argmin(np.abs(probe_coords - event.x)))
                        else:
                            z_index = int(event.x)
                    except:
                        z_index = int(event.x)
                else:
                    z_index = int(event.x)
                rect2.set(max_x=z_index, max_y=z_index)
            else:
                # For 4D: use both x and y coordinates
                # Plot2 uses flipped coordinates, so we need to convert event coordinates to indices
                plot2_x_coords = probe_2d_plot.get_flipped_x_coords()
                plot2_y_coords = probe_2d_plot.get_flipped_y_coords()
                
                # Find closest indices in flipped coordinate arrays
                click_u_idx = int(np.argmin(np.abs(plot2_x_coords - event.x))) if plot2_x_coords is not None else int(event.x)
                click_z_idx = int(np.argmin(np.abs(plot2_y_coords - event.y))) if plot2_y_coords is not None else int(event.y)
                
                # Convert back to original coordinate space
                if probe_2d_plot.needs_flip:
                    click_z = click_z_idx
                    click_u = click_u_idx
                else:
                    click_z = click_u_idx
                    click_u = click_z_idx
                rect2.set(max_x=click_z, max_y=click_u)
        
        # Function to draw rect2 on Plot2
        def draw_rect2():
            """Draw selection rectangle on Plot2."""
            if is_3d_volume:
                plot_x1 = rect2.min_x
                plot_x2 = rect2.max_x
                plot_y1 = 0
                plot_y2 = plot2.y_range.end
            else:
                plot2_needs_flip = probe_2d_plot.needs_flip if hasattr(probe_2d_plot, 'needs_flip') else False
                if plot2_needs_flip:
                    plot_x1 = rect2.min_y  # u min -> plot x
                    plot_x2 = rect2.max_y  # u max -> plot x
                    plot_y1 = rect2.min_x  # z min -> plot y
                    plot_y2 = rect2.max_x  # z max -> plot y
                else:
                    plot_x1 = rect2.min_x  # z min -> plot x
                    plot_x2 = rect2.max_x  # z max -> plot x
                    plot_y1 = rect2.min_y  # u min -> plot y
                    plot_y2 = rect2.max_y  # u max -> plot y
            draw_rect(plot2, rect2, plot_x1, plot_x2, plot_y1, plot_y2)
        
        # Add Plot2B tap handlers if Plot2B exists
        if plot2b is not None:
            tap_tool2b = TapTool()
            plot2b.add_tools(tap_tool2b)
            
            # Function to draw rect2b on Plot2B
            def draw_rect2b():
                """Draw selection rectangle on Plot2B."""
                if not plot2b_is_2d:
                    # 1D plot
                    plot_x1 = rect2b.min_x
                    plot_x2 = rect2b.max_x
                    plot_y1 = 0
                    plot_y2 = plot2b.y_range.end
                else:
                    # 2D plot
                    plot2b_needs_flip = probe_2d_plot_b.needs_flip if hasattr(probe_2d_plot_b, 'needs_flip') else False
                    if plot2b_needs_flip:
                        plot_x1 = rect2b.min_y  # u min -> plot x
                        plot_x2 = rect2b.max_y  # u max -> plot x
                        plot_y1 = rect2b.min_x  # z min -> plot y
                        plot_y2 = rect2b.max_x  # z max -> plot y
                    else:
                        plot_x1 = rect2b.min_x  # z min -> plot x
                        plot_x2 = rect2b.max_x  # z max -> plot x
                        plot_y1 = rect2b.min_y  # u min -> plot y
                        plot_y2 = rect2b.max_y  # u max -> plot y
                draw_rect(plot2b, rect2b, plot_x1, plot_x2, plot_y1, plot_y2)
            
            # Tap handler for Plot2B
            def on_plot2b_tap(event):
                """Handle tap events on Plot2B to set selection region."""
                if not plot2b_is_2d:
                    # 1D plot
                    if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                        try:
                            probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                            if probe_coords_b is not None:
                                z_index = int(np.argmin(np.abs(probe_coords_b - event.x)))
                            else:
                                z_index = int(event.x)
                        except:
                            z_index = int(event.x)
                    else:
                        z_index = int(event.x)
                    
                    if hasattr(event, 'modifiers') and event.modifiers.get("shift", False):
                        rect2b.set(min_x=z_index, min_y=z_index)
                    elif hasattr(event, 'modifiers') and (event.modifiers.get("ctrl", False) or event.modifiers.get('meta', False) or event.modifiers.get('cmd', False)):
                        rect2b.set(max_x=z_index, max_y=z_index)
                    else:
                        rect2b.set(min_x=z_index, min_y=z_index, max_x=z_index, max_y=z_index)
                        clear_rect(plot2b, rect2b)
                        draw_rect(plot2b, rect2b, z_index, z_index, 0, plot2b.y_range.end)
                else:
                    # 2D plot
                    plot2b_needs_flip = probe_2d_plot_b.needs_flip if hasattr(probe_2d_plot_b, 'needs_flip') else False
                    if plot2b_needs_flip:
                        click_z = int(event.y)
                        click_u = int(event.x)
                    else:
                        click_z = int(event.x)
                        click_u = int(event.y)
                    
                    if hasattr(event, 'modifiers') and event.modifiers.get("shift", False):
                        rect2b.set(min_x=click_z, min_y=click_u)
                        draw_rect2b()
                    elif hasattr(event, 'modifiers') and (event.modifiers.get("ctrl", False) or event.modifiers.get('meta', False) or event.modifiers.get('cmd', False)):
                        rect2b.set(max_x=click_z, max_y=click_u)
                        draw_rect2b()
                    else:
                        clear_rect(plot2b, rect2b)
                        rect2b.set(min_x=click_z, min_y=click_u, max_x=click_z, max_y=click_u)
                        draw_rect(plot2b, rect2b, click_z, click_z, click_u, click_u)
            
            # Double-tap handler for Plot2B
            def on_plot2b_doubletap(event):
                """Handle double-tap events on Plot2B to set max coordinates."""
                if not plot2b_is_2d:
                    if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                        try:
                            probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                            if probe_coords_b is not None:
                                z_index = int(np.argmin(np.abs(probe_coords_b - event.x)))
                            else:
                                z_index = int(event.x)
                        except:
                            z_index = int(event.x)
                    else:
                        z_index = int(event.x)
                    rect2b.set(max_x=z_index, max_y=z_index)
                else:
                    plot2b_needs_flip = probe_2d_plot_b.needs_flip if hasattr(probe_2d_plot_b, 'needs_flip') else False
                    if plot2b_needs_flip:
                        click_z = int(event.y)
                        click_u = int(event.x)
                    else:
                        click_z = int(event.x)
                        click_u = int(event.y)
                    rect2b.set(max_x=click_z, max_y=click_u)
                    draw_rect2b()
        
        # Create buttons to compute Plot3 from Plot2 selections
        compute_plot3_button = create_button(
            label="Show Plot3 from Plot2a ->",
            button_type="success",
            width=200
        )
        
        compute_plot3_from_plot2b_button = None
        if plot2b is not None:
            compute_plot3_from_plot2b_button = create_button(
                label="Show Plot3 from Plot2b ->",
                button_type="success",
                width=200
            )
        
        # Create undo/redo buttons first (needed for callbacks)
        undo_button = create_button(
            label="Undo",
            button_type="default",
            width=100
        )
        
        redo_button = create_button(
            label="Redo",
            button_type="default",
            width=100
        )
        
        # Create undo/redo status display
        undo_redo_status = create_div(text="State 1 of 1", width=200)
        
        # Set up undo/redo callbacks
        undo_redo_callbacks = create_undo_redo_callbacks(
            session_history,
            undo_button,
            redo_button,
            undo_redo_status
        )
        
        # Debouncing for state saves - only save after user stops making changes
        # This prevents excessive state saves during rapid UI interactions
        _state_save_timer = None
        _pending_state_save = False
        
        def debounced_save_state(description: str, update_undo_redo: bool = True, delay: float = 0.5):
            """
            Save state with debouncing to avoid excessive saves during rapid changes.
            
            Args:
                description: Description of the state change
                update_undo_redo: Whether to update undo/redo buttons (can skip for frequent operations)
                delay: Delay in seconds before actually saving (default 0.5s)
            """
            nonlocal _state_save_timer, _pending_state_save
            
            def do_save():
                nonlocal _pending_state_save
                if _pending_state_save:
                    plot1_history.save_state(description)
                    session_history.save_state(description)
                    if update_undo_redo:
                        undo_redo_callbacks["update"]()
                    _pending_state_save = False
            
            # Cancel any pending save
            if _state_save_timer is not None:
                try:
                    curdoc().remove_timeout_callback(_state_save_timer)
                except:
                    pass
            
            _pending_state_save = True
            _state_save_timer = curdoc().add_timeout_callback(do_save, delay)
        
        # Create UI update function (defined after color_mapper1 is created)
        def update_ui_after_state_change():
            """Update UI widgets after state change (undo/redo/load)."""
            sync_plot_to_range_inputs(map_plot, range1_min_input, range1_max_input)
            sync_plot_to_color_scale_selector(map_plot, color_scale_selector)
            sync_plot_to_palette_selector(map_plot, palette_selector)
            # Update Bokeh color mapper if needed
            if hasattr(map_plot, 'range_min') and hasattr(map_plot, 'range_max'):
                color_mapper1.low = map_plot.range_min
                color_mapper1.high = map_plot.range_max
            if map_plot.palette != color_mapper1.palette:
                color_mapper1.palette = map_plot.palette
        
        # Create custom undo/redo callbacks that also update UI
        def on_undo():
            """Undo callback with UI update."""
            if session_history.undo():
                update_ui_after_state_change()
                undo_redo_callbacks["update"]()
                if 'status_div' in locals():
                    status_div.text = "Undo successful"
            else:
                if 'status_div' in locals():
                    status_div.text = "Cannot undo - already at initial state"
        
        def on_redo():
            """Redo callback with UI update."""
            if session_history.redo():
                update_ui_after_state_change()
                undo_redo_callbacks["update"]()
                if 'status_div' in locals():
                    status_div.text = "Redo successful"
            else:
                if 'status_div' in locals():
                    status_div.text = "Cannot redo - already at latest state"
        
        # Override with custom callbacks that update UI
        undo_button.on_click(on_undo)
        redo_button.on_click(on_redo)
        
        # Create session management buttons
        save_session_button = create_button(
            label="Save Session",
            button_type="success",
            width=150
        )
        
        load_session_button = create_button(
            label="Load Session",
            button_type="primary",
            width=150
        )
        
        # Create button to go back to dataset selection
        back_to_selection_button = create_button(
            label="Back to Dataset Selection",
            button_type="default",
            width=200
        )
        
        # Create range inputs using SCLib UI
        def on_range_change(attr, old, new):
            """Handle range input changes."""
            if sync_range_inputs_to_plot(map_plot, range1_min_input, range1_max_input):
                # Update Bokeh color mapper immediately
                color_mapper1.low = map_plot.range_min
                color_mapper1.high = map_plot.range_max
                # Save state with debouncing to avoid excessive saves
                debounced_save_state("Range changed", update_undo_redo=True)
        
        range1_min_input, range1_max_input = create_range_inputs(
            min_title="Map Range Min:",
            max_title="Map Range Max:",
            min_value=map_min_val,
            max_value=map_max_val,
            width=120,
            min_callback=on_range_change,
            max_callback=on_range_change,
        )
        
        # Sync initial state from plot
        sync_plot_to_range_inputs(map_plot, range1_min_input, range1_max_input)
        
        # Function to update Plot1 range dynamically based on current data
        def update_plot1_range_dynamic():
            """Update Plot1 range to 1st and 99th percentiles of current data."""
            if map_plot.range_mode == RangeMode.DYNAMIC:
                # Update toggle label to show "Dynamic" while recalculating
                if 'range1_mode_toggle' in locals() and range1_mode_toggle is not None:
                    range1_mode_toggle.label = "Dynamic"
                
                # Get current data (may have changed with crosshair position)
                current_data = plot1_data  # This will be updated when crosshairs change
                if current_data is not None and current_data.size > 0:
                    new_min = float(np.percentile(current_data[~np.isnan(current_data)], 1))
                    new_max = float(np.percentile(current_data[~np.isnan(current_data)], 99))
                    map_plot.range_min = new_min
                    map_plot.range_max = new_max
                    # Update UI inputs
                    range1_min_input.value = str(new_min)
                    range1_max_input.value = str(new_max)
                    # Update color mapper
                    color_mapper1.low = new_min
                    color_mapper1.high = new_max
        
        # Create range section with toggle for Plot1
        def on_plot1_range_mode_change(attr, old, new):
            """Handle Plot1 range mode toggle (User Specified vs Dynamic)."""
            if new:  # Dynamic mode
                map_plot.range_mode = RangeMode.DYNAMIC
                range1_min_input.disabled = True
                range1_max_input.disabled = True
                # Update toggle label to "Dynamic"
                if 'range1_mode_toggle' in locals() and range1_mode_toggle is not None:
                    range1_mode_toggle.label = "Dynamic"
                # Recompute range from current data
                update_plot1_range_dynamic()
            else:  # User specified mode
                map_plot.range_mode = RangeMode.USER_SPECIFIED
                range1_min_input.disabled = False
                range1_max_input.disabled = False
                # Update toggle label to "User Specified"
                if 'range1_mode_toggle' in locals() and range1_mode_toggle is not None:
                    range1_mode_toggle.label = "User Specified"
            # Save state immediately for mode changes (important state, not frequent)
            from bokeh.io import curdoc
            def save_state_async():
                plot1_history.save_state("Range mode changed")
                session_history.save_state("Range mode changed")
                undo_redo_callbacks["update"]()
            curdoc().add_next_tick_callback(save_state_async)
        
        # Set initial label based on range mode
        plot1_initial_label = "User Specified" if map_plot.range_mode == RangeMode.USER_SPECIFIED else "Dynamic"
        range1_section, range1_mode_toggle = create_range_section_with_toggle(
            label="Plot1 Range:",
            min_title="Range Min:",
            max_title="Range Max:",
            min_value=map_min_val,
            max_value=map_max_val,
            width=120,
            toggle_label=plot1_initial_label,
            toggle_active=(map_plot.range_mode == RangeMode.USER_SPECIFIED),
            toggle_callback=on_plot1_range_mode_change,
            min_callback=on_range_change,
            max_callback=on_range_change,
        )
        
        # Add toggle to the section so it's visible
        range1_section.children.append(range1_mode_toggle)
        
        # Create color scale and palette selectors using SCLib UI
        def on_color_scale_change(attr, old, new):
            """Handle color scale change."""
            sync_color_scale_selector_to_plot(map_plot, color_scale_selector)
            # Note: Bokeh color mapper update would need to recreate renderer for log/linear switch
            # Save state immediately for color scale changes (important state, not frequent)
            from bokeh.io import curdoc
            def save_state_async():
                plot1_history.save_state("Color scale changed")
                session_history.save_state("Color scale changed")
                undo_redo_callbacks["update"]()
            curdoc().add_next_tick_callback(save_state_async)
        
        def on_palette_change(attr, old, new):
            """Handle palette change."""
            sync_palette_selector_to_plot(map_plot, palette_selector)
            # Update Bokeh color mapper immediately
            color_mapper1.palette = map_plot.palette
            # Save state asynchronously
            from bokeh.io import curdoc
            def save_state_async():
                plot1_history.save_state("Palette changed")
                session_history.save_state("Palette changed")
                undo_redo_callbacks["update"]()
            curdoc().add_next_tick_callback(save_state_async)
        
        color_scale_selector = create_color_scale_selector(
            active=0,
            width=200,
            callback=on_color_scale_change
        )
        sync_plot_to_color_scale_selector(map_plot, color_scale_selector)
        
        color_scale_section = create_color_scale_section(
            label="Map Color Scale:",
            active=0,
            width=200,
            callback=on_color_scale_change
        )
        
        palette_selector = create_palette_selector(
            value="Viridis256",
            width=200,
            callback=on_palette_change
        )
        sync_plot_to_palette_selector(map_plot, palette_selector)
        
        palette_section = create_palette_section(
            label="Color Palette:",
            value="Viridis256",
            width=200,
            callback=on_palette_change
        )
        
        # Create plot shape controls for Plot1
        def on_plot1_shape_change(attr, old, new):
            """Handle Plot1 shape mode change."""
            if new == 0:  # Square
                map_plot.plot_shape_mode = PlotShapeMode.SQUARE
            elif new == 1:  # Custom
                map_plot.plot_shape_mode = PlotShapeMode.CUSTOM
            elif new == 2:  # Aspect Ratio
                map_plot.plot_shape_mode = PlotShapeMode.ASPECT_RATIO
            # Update plot dimensions
            width, height = map_plot.calculate_plot_dimensions()
            plot1.width = width
            plot1.height = height
            # Also update Plot1B if it exists
            if plot1b is not None and map_plot_b is not None:
                map_plot_b.plot_shape_mode = map_plot.plot_shape_mode
                map_plot_b.plot_width = map_plot.plot_width
                map_plot_b.plot_height = map_plot.plot_height
                map_plot_b.plot_scale = map_plot.plot_scale
                map_plot_b.plot_min_size = map_plot.plot_min_size
                map_plot_b.plot_max_size = map_plot.plot_max_size
                width_b, height_b = map_plot_b.calculate_plot_dimensions()
                plot1b.width = width_b
                plot1b.height = height_b
            # Save state asynchronously
            from bokeh.io import curdoc
            def save_state_async():
                plot1_history.save_state("Plot shape changed")
                session_history.save_state("Plot shape changed")
                undo_redo_callbacks["update"]()
            curdoc().add_next_tick_callback(save_state_async)
        
        def on_plot1_custom_width_change(attr, old, new):
            """Handle Plot1 custom width change."""
            try:
                map_plot.plot_width = int(float(new))
                width, height = map_plot.calculate_plot_dimensions()
                plot1.width = width
                plot1.height = height
                # Also update Plot1B if it exists
                if plot1b is not None and map_plot_b is not None:
                    map_plot_b.plot_width = map_plot.plot_width
                    width_b, height_b = map_plot_b.calculate_plot_dimensions()
                    plot1b.width = width_b
                    plot1b.height = height_b
                # Save state asynchronously
                from bokeh.io import curdoc
                def save_state_async():
                    plot1_history.save_state("Plot width changed")
                    session_history.save_state("Plot width changed")
                    undo_redo_callbacks["update"]()
                curdoc().add_next_tick_callback(save_state_async)
            except:
                pass
        
        def on_plot1_custom_height_change(attr, old, new):
            """Handle Plot1 custom height change."""
            try:
                map_plot.plot_height = int(float(new))
                width, height = map_plot.calculate_plot_dimensions()
                plot1.width = width
                plot1.height = height
                # Also update Plot1B if it exists
                if plot1b is not None and map_plot_b is not None:
                    map_plot_b.plot_height = map_plot.plot_height
                    width_b, height_b = map_plot_b.calculate_plot_dimensions()
                    plot1b.width = width_b
                    plot1b.height = height_b
                # Save state asynchronously
                from bokeh.io import curdoc
                def save_state_async():
                    plot1_history.save_state("Plot height changed")
                    session_history.save_state("Plot height changed")
                    undo_redo_callbacks["update"]()
                curdoc().add_next_tick_callback(save_state_async)
            except:
                pass
        
        def on_plot1_scale_change(attr, old, new):
            """Handle Plot1 scale change."""
            try:
                map_plot.plot_scale = float(new)
                width, height = map_plot.calculate_plot_dimensions()
                plot1.width = width
                plot1.height = height
                # Also update Plot1B if it exists
                if plot1b is not None and map_plot_b is not None:
                    map_plot_b.plot_scale = map_plot.plot_scale
                    width_b, height_b = map_plot_b.calculate_plot_dimensions()
                    plot1b.width = width_b
                    plot1b.height = height_b
                # Save state asynchronously
                from bokeh.io import curdoc
                def save_state_async():
                    plot1_history.save_state("Plot scale changed")
                    session_history.save_state("Plot scale changed")
                    undo_redo_callbacks["update"]()
                curdoc().add_next_tick_callback(save_state_async)
            except:
                pass
        
        def on_plot1_min_size_change(attr, old, new):
            """Handle Plot1 min size change."""
            try:
                map_plot.plot_min_size = int(float(new))
                width, height = map_plot.calculate_plot_dimensions()
                plot1.width = width
                plot1.height = height
                # Also update Plot1B if it exists
                if plot1b is not None and map_plot_b is not None:
                    map_plot_b.plot_min_size = map_plot.plot_min_size
                    width_b, height_b = map_plot_b.calculate_plot_dimensions()
                    plot1b.width = width_b
                    plot1b.height = height_b
                # Save state asynchronously
                from bokeh.io import curdoc
                def save_state_async():
                    plot1_history.save_state("Plot min size changed")
                    session_history.save_state("Plot min size changed")
                    undo_redo_callbacks["update"]()
                curdoc().add_next_tick_callback(save_state_async)
            except:
                pass
        
        def on_plot1_max_size_change(attr, old, new):
            """Handle Plot1 max size change."""
            try:
                map_plot.plot_max_size = int(float(new))
                width, height = map_plot.calculate_plot_dimensions()
                plot1.width = width
                plot1.height = height
                # Also update Plot1B if it exists
                if plot1b is not None and map_plot_b is not None:
                    map_plot_b.plot_max_size = map_plot.plot_max_size
                    width_b, height_b = map_plot_b.calculate_plot_dimensions()
                    plot1b.width = width_b
                    plot1b.height = height_b
                # Save state asynchronously
                from bokeh.io import curdoc
                def save_state_async():
                    plot1_history.save_state("Plot max size changed")
                    session_history.save_state("Plot max size changed")
                    undo_redo_callbacks["update"]()
                curdoc().add_next_tick_callback(save_state_async)
            except:
                pass
        
        # Get initial shape mode
        initial_shape_mode = 0  # Square
        if map_plot.plot_shape_mode == PlotShapeMode.CUSTOM:
            initial_shape_mode = 1
        elif map_plot.plot_shape_mode == PlotShapeMode.ASPECT_RATIO:
            initial_shape_mode = 2
        
        plot1_shape_selector, plot1_custom_width_input, plot1_custom_height_input, \
        plot1_scale_input, plot1_min_size_input, plot1_max_size_input, \
        plot1_custom_controls, plot1_aspect_controls, plot1_size_limits_controls = create_plot_shape_controls(
            active=initial_shape_mode,
            width=200,
            shape_callback=on_plot1_shape_change,
            custom_width=map_plot.plot_width,
            custom_height=map_plot.plot_height,
            custom_width_callback=on_plot1_custom_width_change,
            custom_height_callback=on_plot1_custom_height_change,
            scale=map_plot.plot_scale,
            scale_callback=on_plot1_scale_change,
            min_size=map_plot.plot_min_size,
            max_size=map_plot.plot_max_size,
            min_size_callback=on_plot1_min_size_change,
            max_size_callback=on_plot1_max_size_change,
        )
        
        # Connect min/max size input callbacks
        plot1_min_size_input.on_change("value", on_plot1_min_size_change)
        plot1_max_size_input.on_change("value", on_plot1_max_size_change)
        
        # Create plot shape section
        plot1_shape_section = column(
            create_label_div("Plot1 Shape:", width=200),
            plot1_shape_selector,
            plot1_custom_controls,
            plot1_aspect_controls,
            plot1_size_limits_controls,
        )
        
        # Create range controls for Plot1B if it exists
        range1b_section = None
        if plot1b is not None and map_plot_b is not None and map1b_min_val is not None and map1b_max_val is not None:
            def on_range1b_change(attr, old, new):
                """Handle Plot1B range input changes."""
                if sync_range_inputs_to_plot(map_plot_b, range1b_min_input, range1b_max_input):
                    color_mapper1b.low = map_plot_b.range_min
                    color_mapper1b.high = map_plot_b.range_max
            
            range1b_min_input, range1b_max_input = create_range_inputs(
                min_title="Range Min:",
                max_title="Range Max:",
                min_value=map1b_min_val,
                max_value=map1b_max_val,
                width=120,
                min_callback=on_range1b_change,
                max_callback=on_range1b_change,
            )
            sync_plot_to_range_inputs(map_plot_b, range1b_min_input, range1b_max_input)
            
            def on_plot1b_range_mode_change(attr, old, new):
                """Handle Plot1B range mode toggle."""
                # Note: toggle_active=True means User Specified, toggle_active=False means Dynamic
                if new:  # Toggle is active = User Specified mode
                    map_plot_b.range_mode = RangeMode.USER_SPECIFIED
                    range1b_min_input.disabled = False
                    range1b_max_input.disabled = False
                    # Update toggle label to "User Specified"
                    if 'range1b_mode_toggle' in locals() and range1b_mode_toggle is not None:
                        range1b_mode_toggle.label = "User Specified"
                else:  # Toggle is inactive = Dynamic mode
                    map_plot_b.range_mode = RangeMode.DYNAMIC
                    range1b_min_input.disabled = True
                    range1b_max_input.disabled = True
                    # Update toggle label to "Dynamic"
                    if 'range1b_mode_toggle' in locals() and range1b_mode_toggle is not None:
                        range1b_mode_toggle.label = "Dynamic"
            
            # Set initial label based on range mode
            plot1b_initial_label = "User Specified" if map_plot_b.range_mode == RangeMode.USER_SPECIFIED else "Dynamic"
            range1b_section, range1b_mode_toggle = create_range_section_with_toggle(
                label="Plot1B Range:",
                min_title="Range Min:",
                max_title="Range Max:",
                min_value=map1b_min_val,
                max_value=map1b_max_val,
                width=120,
                toggle_label=plot1b_initial_label,
                toggle_active=(map_plot_b.range_mode == RangeMode.USER_SPECIFIED),
                toggle_callback=on_plot1b_range_mode_change,
                min_callback=on_range1b_change,
                max_callback=on_range1b_change,
            )
            
            # Add toggle to the section so it's visible
            if range1b_mode_toggle not in range1b_section.children:
                range1b_section.children.append(range1b_mode_toggle)
        
        # Create range controls for Plot2
        range2_section = None
        if is_3d_volume:
            # 1D plot
            probe_min_val = float(np.percentile(initial_slice_1d[~np.isnan(initial_slice_1d)], 1))
            probe_max_val = float(np.percentile(initial_slice_1d[~np.isnan(initial_slice_1d)], 99))
        else:
            # 2D plot
            probe_min_val = float(np.percentile(plot2_data[~np.isnan(plot2_data)], 1))
            probe_max_val = float(np.percentile(plot2_data[~np.isnan(plot2_data)], 99))
        
        # Function to update Plot2 range dynamically
        def update_plot2_range_dynamic():
            """Update Plot2 range to 1st and 99th percentiles of current slice."""
            if is_3d_volume:
                # For 1D plots, get current slice data
                x_idx = get_x_index()
                y_idx = get_y_index()
                current_slice = volume[x_idx, y_idx, :]
                if current_slice is not None and current_slice.size > 0:
                    new_min = float(np.percentile(current_slice[~np.isnan(current_slice)], 1))
                    new_max = float(np.percentile(current_slice[~np.isnan(current_slice)], 99))
                    range2_min_input.value = str(new_min)
                    range2_max_input.value = str(new_max)
                    plot2.y_range.start = new_min
                    plot2.y_range.end = new_max
            else:
                # For 2D plots, get current slice data
                x_idx = get_x_index()
                y_idx = get_y_index()
                current_slice = volume[x_idx, y_idx, :, :]
                if plot2_needs_flip:
                    current_slice = np.transpose(current_slice)
                if current_slice is not None and current_slice.size > 0:
                    new_min = float(np.percentile(current_slice[~np.isnan(current_slice)], 1))
                    new_max = float(np.percentile(current_slice[~np.isnan(current_slice)], 99))
                    range2_min_input.value = str(new_min)
                    range2_max_input.value = str(new_max)
                    color_mapper2.low = new_min
                    color_mapper2.high = new_max
        
        def on_range2_change(attr, old, new):
            """Handle Plot2 range input changes."""
            try:
                min_val = float(range2_min_input.value) if range2_min_input.value else probe_min_val
                max_val = float(range2_max_input.value) if range2_max_input.value else probe_max_val
                if is_3d_volume:
                    plot2.y_range.start = min_val
                    plot2.y_range.end = max_val
                else:
                    color_mapper2.low = min_val
                    color_mapper2.high = max_val
            except:
                pass
        
        range2_min_input, range2_max_input = create_range_inputs(
            min_title="Range Min:",
            max_title="Range Max:",
            min_value=probe_min_val,
            max_value=probe_max_val,
            width=120,
            min_callback=on_range2_change,
            max_callback=on_range2_change,
        )
        
        def on_plot2_range_mode_change(attr, old, new):
            """Handle Plot2 range mode toggle."""
            # Note: toggle_active=False means Dynamic mode, toggle_active=True means User Specified
            # But the callback receives new=True when toggle is active (User Specified), new=False when inactive (Dynamic)
            if new:  # Toggle is active = User Specified mode
                range2_min_input.disabled = False
                range2_max_input.disabled = False
                # Update toggle label to "User Specified"
                if 'range2_mode_toggle' in locals() and range2_mode_toggle is not None:
                    range2_mode_toggle.label = "User Specified"
            else:  # Toggle is inactive = Dynamic mode
                range2_min_input.disabled = True
                range2_max_input.disabled = True
                # Update toggle label to "Dynamic"
                if 'range2_mode_toggle' in locals() and range2_mode_toggle is not None:
                    range2_mode_toggle.label = "Dynamic"
                # Recompute range from current data
                update_plot2_range_dynamic()
        
        range2_section, range2_mode_toggle = create_range_section_with_toggle(
            label="Plot2 Range:",
            min_title="Range Min:",
            max_title="Range Max:",
            min_value=probe_min_val,
            max_value=probe_max_val,
            width=120,
            toggle_label="Dynamic",  # Default to Dynamic mode
            toggle_active=False,  # Default to Dynamic (False = Dynamic, True = User Specified)
            toggle_callback=on_plot2_range_mode_change,
            min_callback=on_range2_change,
            max_callback=on_range2_change,
        )
        
        # Add toggle to the section so it's visible
        range2_section.children.append(range2_mode_toggle)
        
        # Create range controls for Plot2B if it exists
        range2b_section = None
        if plot2b is not None:
            # Get range values based on Plot2B type
            if probe2b_min_val is not None and probe2b_max_val is not None:
                plot2b_min_val = probe2b_min_val
                plot2b_max_val = probe2b_max_val
            else:
                # Fallback values
                plot2b_min_val = 0.0
                plot2b_max_val = 1.0
            
            def on_range2b_change(attr, old, new):
                """Handle Plot2B range input changes."""
                try:
                    min_val = float(range2b_min_input.value) if range2b_min_input.value else plot2b_min_val
                    max_val = float(range2b_max_input.value) if range2b_max_input.value else plot2b_max_val
                    if plot2b_is_2d:
                        if color_mapper2b is not None:
                            color_mapper2b.low = min_val
                            color_mapper2b.high = max_val
                    else:
                        plot2b.y_range.start = min_val
                        plot2b.y_range.end = max_val
                except:
                    pass
            
            range2b_min_input, range2b_max_input = create_range_inputs(
                min_title="Range Min:",
                max_title="Range Max:",
                min_value=plot2b_min_val,
                max_value=plot2b_max_val,
                width=120,
                min_callback=on_range2b_change,
                max_callback=on_range2b_change,
            )
            
            def on_plot2b_range_mode_change(attr, old, new):
                """Handle Plot2B range mode toggle."""
                # Note: toggle_active=True means User Specified, toggle_active=False means Dynamic
                if new:  # Toggle is active = User Specified mode
                    range2b_min_input.disabled = False
                    range2b_max_input.disabled = False
                    # Update toggle label to "User Specified"
                    if 'range2b_mode_toggle' in locals() and range2b_mode_toggle is not None:
                        range2b_mode_toggle.label = "User Specified"
                else:  # Toggle is inactive = Dynamic mode
                    range2b_min_input.disabled = True
                    range2b_max_input.disabled = True
                    # Update toggle label to "Dynamic"
                    if 'range2b_mode_toggle' in locals() and range2b_mode_toggle is not None:
                        range2b_mode_toggle.label = "Dynamic"
                    # Recompute range from current data
                    x_idx = get_x_index()
                    y_idx = get_y_index()
                    if plot2b_is_2d:
                        if hasattr(process_4dnexus, 'volume_picked_b') and process_4dnexus.volume_picked_b:
                            try:
                                # Use cached volume_b if available
                                if (hasattr(process_4dnexus, '_cached_volume_b') and 
                                    hasattr(process_4dnexus, '_cached_volume_b_path') and
                                    process_4dnexus._cached_volume_b_path == process_4dnexus.volume_picked_b):
                                    volume_b = process_4dnexus._cached_volume_b
                                else:
                                    # Load and cache volume_b
                                    volume_b = process_4dnexus.load_dataset_by_path(process_4dnexus.volume_picked_b)
                                    if volume_b is not None:
                                        process_4dnexus._cached_volume_b = volume_b
                                        process_4dnexus._cached_volume_b_path = process_4dnexus.volume_picked_b
                                
                                if volume_b is not None:
                                    current_slice = volume_b[x_idx, y_idx, :, :]
                                    # Get coordinate sizes for flip detection
                                    plot2b_probe_x_coord_size_local = None
                                    plot2b_probe_y_coord_size_local = None
                                    if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                                        plot2b_probe_x_coord_size_local = process_4dnexus.get_dataset_size_from_path(process_4dnexus.probe_x_coords_picked_b)
                                    if hasattr(process_4dnexus, 'probe_y_coords_picked_b') and process_4dnexus.probe_y_coords_picked_b:
                                        plot2b_probe_y_coord_size_local = process_4dnexus.get_dataset_size_from_path(process_4dnexus.probe_y_coords_picked_b)
                                    
                                    plot2b_needs_flip_local = process_4dnexus.detect_probe_flip_needed(
                                        volume_b.shape,
                                        plot2b_probe_x_coord_size_local,
                                        plot2b_probe_y_coord_size_local
                                    )
                                    if plot2b_needs_flip_local:
                                        current_slice = np.transpose(current_slice)
                                    else:
                                        current_slice = np.transpose(current_slice)
                                    if current_slice is not None and current_slice.size > 0:
                                        new_min = float(np.percentile(current_slice[~np.isnan(current_slice)], 1))
                                        new_max = float(np.percentile(current_slice[~np.isnan(current_slice)], 99))
                                        range2b_min_input.value = str(new_min)
                                        range2b_max_input.value = str(new_max)
                                        color_mapper2b.low = new_min
                                        color_mapper2b.high = new_max
                            except:
                                pass
                    else:
                        # 1D plot
                        if hasattr(process_4dnexus, 'volume_picked_b') and process_4dnexus.volume_picked_b:
                            try:
                                # Use cached volume_b if available
                                if (hasattr(process_4dnexus, '_cached_volume_b') and 
                                    hasattr(process_4dnexus, '_cached_volume_b_path') and
                                    process_4dnexus._cached_volume_b_path == process_4dnexus.volume_picked_b):
                                    volume_b = process_4dnexus._cached_volume_b
                                else:
                                    # Load and cache volume_b
                                    volume_b = process_4dnexus.load_dataset_by_path(process_4dnexus.volume_picked_b)
                                    if volume_b is not None:
                                        process_4dnexus._cached_volume_b = volume_b
                                        process_4dnexus._cached_volume_b_path = process_4dnexus.volume_picked_b
                                
                                if volume_b is not None:
                                    current_slice = volume_b[x_idx, y_idx, :]
                                    if current_slice is not None and current_slice.size > 0:
                                        new_min = float(np.percentile(current_slice[~np.isnan(current_slice)], 1))
                                        new_max = float(np.percentile(current_slice[~np.isnan(current_slice)], 99))
                                        range2b_min_input.value = str(new_min)
                                        range2b_max_input.value = str(new_max)
                                        plot2b.y_range.start = new_min
                                        plot2b.y_range.end = new_max
                            except:
                                pass
            
            range2b_section, range2b_mode_toggle = create_range_section_with_toggle(
                label="Plot2B Range:",
                min_title="Range Min:",
                max_title="Range Max:",
                min_value=plot2b_min_val,
                max_value=plot2b_max_val,
                width=120,
                toggle_label="Dynamic",  # Default to Dynamic mode
                toggle_active=False,  # Default to Dynamic (False = Dynamic, True = User Specified)
                toggle_callback=on_plot2b_range_mode_change,
                min_callback=on_range2b_change,
                max_callback=on_range2b_change,
            )
            
            # Add toggle to the section so it's visible
            if range2b_mode_toggle not in range2b_section.children:
                range2b_section.children.append(range2b_mode_toggle)
        
        # Create range controls for Plot3
        range3_section = None
        plot3_min_val = 0.0
        plot3_max_val = 1.0
        
        def on_range3_change(attr, old, new):
            """Handle Plot3 range input changes."""
            try:
                min_val = float(range3_min_input.value) if range3_min_input.value else plot3_min_val
                max_val = float(range3_max_input.value) if range3_max_input.value else plot3_max_val
                color_mapper3.low = min_val
                color_mapper3.high = max_val
            except:
                pass
        
        range3_min_input, range3_max_input = create_range_inputs(
            min_title="Range Min:",
            max_title="Range Max:",
            min_value=plot3_min_val,
            max_value=plot3_max_val,
            width=120,
            min_callback=on_range3_change,
            max_callback=on_range3_change,
        )
        
        def on_plot3_range_mode_change(attr, old, new):
            """Handle Plot3 range mode toggle."""
            if new:  # Dynamic mode
                range3_min_input.disabled = True
                range3_max_input.disabled = True
            else:  # User specified mode
                range3_min_input.disabled = False
                range3_max_input.disabled = False
        
        range3_section, range3_mode_toggle = create_range_section_with_toggle(
            label="Plot3 Range:",
            min_title="Range Min:",
            max_title="Range Max:",
            min_value=plot3_min_val,
            max_value=plot3_max_val,
            width=120,
            toggle_label="User Specified",
            toggle_active=False,  # Default to Dynamic (False = Dynamic, True = User Specified)
            toggle_callback=on_plot3_range_mode_change,
            min_callback=on_range3_change,
            max_callback=on_range3_change,
        )
        
        # Add toggle to the section so it's visible
        range3_section.children.append(range3_mode_toggle)
        
        # Save session callback
        def on_save_session():
            """Save current session to file.
            
            NOTE: This saves ONLY UI settings (ranges, colors, palettes, plot shapes, etc.)
            NOT data arrays. Data is loaded fresh from the dataset files when the session is loaded.
            This keeps session files small and fast to save/load.
            """
            try:
                from pathlib import Path
                import os
                
                # Determine save directory
                if DATA_IS_LOCAL:
                    save_dir_path = Path(local_base_dir)
                else:
                    save_dir_path = Path(save_dir) if save_dir else Path(local_base_dir)
                
                # Create sessions subdirectory
                sessions_dir = save_dir_path / "sessions"
                sessions_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate filename
                filename = f"session_{session.session_id}.json"
                filepath = sessions_dir / filename
                
                # Save session - include_data=False means NO data arrays, only UI settings
                session.save_session(filepath, include_data=False)
                
                # Save state to history (but don't create a new history entry for the save action itself)
                # The save action is logged in session_changes, but we don't want to undo/redo the save
                undo_redo_callbacks["update"]()
                
                status_div.text = f"Session saved to {filepath}"
                print(f"✅ Session saved to {filepath}")
            except Exception as e:
                import traceback
                error_msg = f"Error saving session: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                status_div.text = f"<span style='color: red;'>{error_msg}</span>"
        
        # Load session callback
        def on_load_session():
            """Load session from file.
            
            NOTE: This loads ONLY UI settings (ranges, colors, palettes, plot shapes, etc.)
            NOT data arrays. Data is loaded fresh from the dataset files.
            restore_data=False ensures no data arrays are restored.
            """
            try:
                from pathlib import Path
                import os
                
                # For Bokeh, we'll use a text input for file path
                # In a full implementation, you might use a file picker widget
                # For now, we'll look in the sessions directory
                if DATA_IS_LOCAL:
                    save_dir_path = Path(local_base_dir)
                else:
                    save_dir_path = Path(save_dir) if save_dir else Path(local_base_dir)
                
                sessions_dir = save_dir_path / "sessions"
                
                if not sessions_dir.exists():
                    status_div.text = f"<span style='color: orange;'>No sessions directory found at {sessions_dir}</span>"
                    return
                
                # Find most recent session file
                session_files = sorted(sessions_dir.glob("session_*.json"), key=os.path.getmtime, reverse=True)
                
                if not session_files:
                    status_div.text = f"<span style='color: orange;'>No session files found in {sessions_dir}</span>"
                    return
                
                # Load the most recent session
                filepath = session_files[0]
                session.load_session(filepath, restore_data=False)
                
                # Restore plot states from loaded session
                if hasattr(session, '_loaded_plot_states'):
                    for plot_id, plot_state in session._loaded_plot_states.items():
                        plot = session.get_plot(plot_id)
                        plot_type = plot_state.get("plot_type", None)
                        
                        if plot:
                            # Plot exists in session, restore its state
                            plot.load_state(plot_state, restore_data=False)
                        elif plot_id == "plot1":
                            # Restore map_plot state (plot may not be in session yet)
                            map_plot.load_state(plot_state, restore_data=False)
                            # Re-add to session if not already there
                            if "plot1" not in session.plots:
                                session.add_plot("plot1", map_plot)
                        elif plot_id == "plot2":
                            # Restore probe plot state based on plot type
                            if plot_type == "PROBE_1DPlot" or (is_3d_volume and hasattr(plot2_history, 'plot')):
                                if hasattr(plot2_history, 'plot'):
                                    plot2_history.plot.load_state(plot_state, restore_data=False)
                                    if "plot2" not in session.plots:
                                        session.add_plot("plot2", plot2_history.plot)
                            elif plot_type == "PROBE_2DPlot" or (not is_3d_volume and hasattr(plot2_history, 'plot')):
                                if hasattr(plot2_history, 'plot'):
                                    plot2_history.plot.load_state(plot_state, restore_data=False)
                                    if "plot2" not in session.plots:
                                        session.add_plot("plot2", plot2_history.plot)
                
                # Update UI to reflect loaded state using the update function
                update_ui_after_state_change()
                
                # Clear and rebuild history with loaded state
                session_history.clear()
                session_history.save_state("Session loaded")
                undo_redo_callbacks["update"]()
                
                status_div.text = f"Session loaded from {filepath.name}"
                print(f"✅ Session loaded from {filepath}")
            except Exception as e:
                import traceback
                error_msg = f"Error loading session: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                status_div.text = f"<span style='color: red;'>{error_msg}</span>"
        
        save_session_button.on_click(on_save_session)
        load_session_button.on_click(on_load_session)
        
        # Callback to go back to dataset selection
        def on_back_to_selection():
            """Return to the dataset selection dashboard."""
            from bokeh.io import curdoc as _curdoc
            try:
                # Recreate the tmp_dashboard
                tmp_dashboard = create_tmp_dashboard(process_4dnexus)
                _curdoc().clear()
                _curdoc().add_root(tmp_dashboard)
            except Exception as e:
                import traceback
                error_msg = f"Error returning to dataset selection: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                error_div = create_div(
                    text=f"<h3 style='color: red;'>Error</h3><p>{error_msg}</p><pre>{traceback.format_exc()}</pre>",
                    width=800
                )
                _curdoc().clear()
                _curdoc().add_root(error_div)
        
        back_to_selection_button.on_click(on_back_to_selection)
        
        # Create export change log button (needed before session_section)
        export_log_button = create_button(
            label="Export Change Log",
            button_type="default",
            width=150
        )
        
        def on_export_log():
            """Export change log to file."""
            try:
                from pathlib import Path
                
                # Determine save directory
                if DATA_IS_LOCAL:
                    save_dir_path = Path(local_base_dir)
                else:
                    save_dir_path = Path(save_dir) if save_dir else Path(local_base_dir)
                
                # Create sessions subdirectory
                sessions_dir = save_dir_path / "sessions"
                sessions_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate filename
                filename = f"changelog_{session.session_id}.json"
                filepath = sessions_dir / filename
                
                # Export change log
                session.export_change_log(filepath, format="json")
                
                status_div.text = f"Change log exported to {filepath}"
                print(f"✅ Change log exported to {filepath}")
            except Exception as e:
                import traceback
                error_msg = f"Error exporting change log: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                status_div.text = f"<span style='color: red;'>{error_msg}</span>"
        
        export_log_button.on_click(on_export_log)
        
        # Create session management section (moved here before tools_items)
        session_section = column(
            create_label_div("Session Management:", width=200),
            row(save_session_button, load_session_button),
            create_div(text="<hr>", width=400),
            row(back_to_selection_button),
            export_log_button,
            create_label_div("Undo/Redo:", width=200),
            row(undo_button, redo_button, undo_redo_status),
        )
        
        # Create status display
        status_text = f"""
        <h3>{'3D' if is_3d_volume else '4D'} Data Explorer Dashboard</h3>
        <p><b>Instructions:</b></p>
        <ul>
            <li><b>Plot1:</b> 2D map view - click to select position</li>
            <li><b>Plot2:</b> {'1D probe data' if is_3d_volume else '2D probe data'}</li>
        </ul>
        <p>Ready to explore data...</p>
        """
        # Create status display with constrained height to prevent overlap
        status_div = create_div(
            text=status_text,
            width=400,  # Match tools column width
            height=300,  # Set max height
            styles={
                "overflow-y": "auto",
                "overflow-x": "hidden",
                "max-height": "300px"
            }
        )
        
        # Note: export_log_button and session_section are already created above
        # Build tools items list (needed for layout)
        # Note: Range inputs are now above each plot, not in tools column
        tools_items = [
            session_section,
            create_div(text="<hr>", width=400),
            x_slider,
            y_slider,
            color_scale_section,
            palette_section,
            plot1_shape_section,
            create_div(text="<hr>", width=400),
            create_label_div("Plot2 -> Plot3:", width=200),
            compute_plot3_button,
        ]
        
        # Add Plot2B button if it exists
        if compute_plot3_from_plot2b_button is not None:
            tools_items.append(compute_plot3_from_plot2b_button)
        
        tools_items.extend([
            create_div(text="<hr>", width=400),
            status_div,
        ])
        
        # Function to compute Plot3 from Plot2 selection
        def compute_plot3_from_plot2():
            """Compute Plot3 image by summing over selected Z,U range in Plot2."""
            try:
                if is_3d_volume:
                    # For 3D: sum over Z dimension for selected range
                    # rect2 stores indices, not coordinates
                    z1, z2 = rect2.min_x, rect2.max_x
                    z_lo, z_hi = (int(z1), int(z2)) if z1 <= z2 else (int(z2), int(z1))
                    z_lo = max(0, min(z_lo, volume.shape[2]-1))
                    z_hi = max(0, min(z_hi, volume.shape[2]-1))
                    if z_hi <= z_lo:
                        z_hi = min(z_lo + 1, volume.shape[2])
                    
                    piece = volume[:, :, z_lo:z_hi]
                    img = np.sum(piece, axis=2)  # sum over Z dimension
                else:
                    # For 4D: sum over Z and U dimensions
                    # rect2 stores indices (z, u), not coordinates
                    plot2_needs_flip = probe_2d_plot.needs_flip if hasattr(probe_2d_plot, 'needs_flip') else False
                    if plot2_needs_flip:
                        z1, z2 = rect2.min_x, rect2.max_x
                        u1, u2 = rect2.min_y, rect2.max_y
                    else:
                        z1, z2 = rect2.min_x, rect2.max_x
                        u1, u2 = rect2.min_y, rect2.max_y
                    
                    z_lo, z_hi = (int(z1), int(z2)) if z1 <= z2 else (int(z2), int(z1))
                    u_lo, u_hi = (int(u1), int(u2)) if u1 <= u2 else (int(u2), int(u1))
                    z_lo = max(0, min(z_lo, volume.shape[2]-1))
                    z_hi = max(0, min(z_hi, volume.shape[2]-1))
                    u_lo = max(0, min(u_lo, volume.shape[3]-1))
                    u_hi = max(0, min(u_hi, volume.shape[3]-1))
                    if z_hi <= z_lo:
                        z_hi = min(z_lo + 1, volume.shape[2])
                    if u_hi <= u_lo:
                        u_hi = min(u_lo + 1, volume.shape[3])
                    
                    piece = volume[:, :, z_lo:z_hi, u_lo:u_hi]
                    img = np.sum(piece, axis=(2, 3))  # sum over Z and U
                
                # Normalize to [0,1]
                img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
                vmin = float(np.min(img))
                vmax = float(np.max(img))
                if vmax > vmin:
                    img = (img - vmin) / (vmax - vmin)
                else:
                    img = np.zeros_like(img)
                
                # Apply Plot1's flip state to match Plot1's orientation
                if plot1_needs_flip:
                    img = np.transpose(img)
                
                source3.data = {
                    "image": [img],
                    "x": [plot3.x_range.start],
                    "dw": [plot3.x_range.end - plot3.x_range.start],
                    "y": [plot3.y_range.start],
                    "dh": [plot3.y_range.end - plot3.y_range.start],
                }
                
                color_mapper3.low = 0.0
                color_mapper3.high = 1.0
            except Exception as e:
                import traceback
                print(f"Error computing Plot3: {e}")
                traceback.print_exc()
        
        compute_plot3_button.on_click(lambda: compute_plot3_from_plot2())
        
        # Function to compute Plot3 from Plot2B selection
        def compute_plot3_from_plot2b():
            """Compute Plot3 image by summing over selected Z,U range in Plot2B."""
            if not plot2b_is_2d:
                # For 3D: sum over Z dimension
                z1, z2 = rect2b.min_x, rect2b.max_x
                z_lo, z_hi = (int(z1), int(z2)) if z1 <= z2 else (int(z2), int(z1))
                z_lo = max(0, min(z_lo, volume_b.shape[2]-1))
                z_hi = max(0, min(z_hi, volume_b.shape[2]-1))
                if z_hi <= z_lo:
                    z_hi = min(z_lo + 1, volume_b.shape[2])
                
                piece = volume_b[:, :, z_lo:z_hi]
                img = np.sum(piece, axis=2)
            else:
                # For 4D: sum over Z and U dimensions
                plot2b_needs_flip = probe_2d_plot_b.needs_flip if hasattr(probe_2d_plot_b, 'needs_flip') else False
                if plot2b_needs_flip:
                    z1, z2 = rect2b.min_x, rect2b.max_x
                    u1, u2 = rect2b.min_y, rect2b.max_y
                else:
                    z1, z2 = rect2.min_x, rect2.max_x
                    u1, u2 = rect2.min_y, rect2.max_y
                
                z_lo, z_hi = (int(z1), int(z2)) if z1 <= z2 else (int(z2), int(z1))
                u_lo, u_hi = (int(u1), int(u2)) if u1 <= u2 else (int(u2), int(u1))
                z_lo = max(0, min(z_lo, volume_b.shape[2]-1))
                z_hi = max(0, min(z_hi, volume_b.shape[2]-1))
                u_lo = max(0, min(u_lo, volume_b.shape[3]-1))
                u_hi = max(0, min(u_hi, volume_b.shape[3]-1))
                if z_hi <= z_lo:
                    z_hi = min(z_lo + 1, volume_b.shape[2])
                if u_hi <= u_lo:
                    u_hi = min(u_lo + 1, volume_b.shape[3])
                
                piece = volume_b[:, :, z_lo:z_hi, u_lo:u_hi]
                img = np.sum(piece, axis=(2, 3))
            
            # Normalize to [0,1]
            img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
            vmin = float(np.min(img))
            vmax = float(np.max(img))
            if vmax > vmin:
                img = (img - vmin) / (vmax - vmin)
            else:
                img = np.zeros_like(img)
            
            # Apply Plot1's flip state to match Plot1's orientation
            if plot1_needs_flip:
                img = np.transpose(img)
            
            source3.data = {
                "image": [img],
                "x": [plot3.x_range.start],
                "dw": [plot3.x_range.end - plot3.x_range.start],
                "y": [plot3.y_range.start],
                "dh": [plot3.y_range.end - plot3.y_range.start],
            }
            
            color_mapper3.low = 0.0
            color_mapper3.high = 1.0
        
        if compute_plot3_from_plot2b_button is not None:
            compute_plot3_from_plot2b_button.on_click(lambda: compute_plot3_from_plot2b())
        
        # Add TapTool to Plot3 for region selection
        tap_tool3 = TapTool()
        plot3.add_tools(tap_tool3)
        
        # Tap handler for Plot3 to set selection region
        def on_plot3_tap(event):
            """Handle tap events on Plot3 to set selection region."""
            x_coord = event.x
            y_coord = event.y
            
            if plot1_needs_flip:
                # When flipped, swap coordinates
                temp_x = y_coord
                temp_y = x_coord
                x_coord = temp_x
                y_coord = temp_y
            
            if event.modifiers.get("shift", False):
                # Shift+click: Set min values only
                rect3.set(min_x=x_coord, min_y=y_coord)
            elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta', False) or event.modifiers.get('cmd', False):
                # Ctrl/Cmd+click: Set max values only
                rect3.set(max_x=x_coord, max_y=y_coord)
            else:
                # Regular click: Clear and set both min and max to same value
                clear_rect(plot3, rect3)
                rect3.set(min_x=x_coord, min_y=y_coord, max_x=x_coord, max_y=y_coord)
                draw_rect(plot3, rect3, x_coord, x_coord, y_coord, y_coord)
            
            # Compute Plot2 from Plot3 selection
            compute_plot2_from_plot3()
        
        # Function to draw rect3 on Plot3
        def draw_rect3():
            """Draw selection rectangle on Plot3."""
            draw_rect(plot3, rect3, rect3.min_x, rect3.max_x, rect3.min_y, rect3.max_y)
        
        # Function to compute Plot2 from Plot3 selection
        def compute_plot2_from_plot3():
            """Compute Plot2 by summing over selected X,Y region in Plot3."""
            # Convert coordinates to indices
            x1 = get_x_index(rect3.min_x)
            y1 = get_y_index(rect3.min_y)
            x2 = max(x1 + 1, get_x_index(rect3.max_x))
            y2 = max(y1 + 1, get_y_index(rect3.max_y))
            
            if is_3d_volume:
                # For 3D: sum over X,Y dimensions
                piece = volume[x1:x2, y1:y2, :]
                slice = np.sum(piece, axis=(0, 1)) / ((x2-x1)*(y2-y1))
                
                # Update 1D plot
                if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                    try:
                        probe_coords = process_4dnexus.load_probe_coordinates()
                        if probe_coords is not None and len(probe_coords) == len(slice):
                            x_coords_1d = probe_coords
                        else:
                            x_coords_1d = np.arange(len(slice))
                    except:
                        x_coords_1d = np.arange(len(slice))
                else:
                    x_coords_1d = np.arange(len(slice))
                
                source2.data = {"x": x_coords_1d, "y": slice}
                plot2.x_range.start = float(np.min(x_coords_1d))
                plot2.x_range.end = float(np.max(x_coords_1d))
                plot2.y_range.start = float(np.min(slice))
                plot2.y_range.end = float(np.max(slice))
            else:
                # For 4D: sum over X,Y dimensions
                piece = volume[x1:x2, y1:y2, :, :]
                slice = np.sum(piece, axis=(0, 1)) / ((x2-x1)*(y2-y1))
                
                # Update probe_2d_plot's data and use its flipped methods
                probe_2d_plot.data = slice
                
                # Get flipped data and coordinates from probe_2d_plot
                flipped_slice = probe_2d_plot.get_flipped_data()
                x_coords_slice = probe_2d_plot.get_flipped_x_coords()
                y_coords_slice = probe_2d_plot.get_flipped_y_coords()
                
                # Fallback if flipped methods return None
                if flipped_slice is None:
                    flipped_slice = np.transpose(slice)  # Always transpose for Bokeh
                if x_coords_slice is None:
                    x_coords_slice = np.arange(flipped_slice.shape[1])
                if y_coords_slice is None:
                    y_coords_slice = np.arange(flipped_slice.shape[0])
                
                # Calculate dimensions
                dw = float(np.max(x_coords_slice) - np.min(x_coords_slice)) if len(x_coords_slice) > 0 else float(flipped_slice.shape[1])
                dh = float(np.max(y_coords_slice) - np.min(y_coords_slice)) if len(y_coords_slice) > 0 else float(flipped_slice.shape[0])
                
                source2.data = {
                    "image": [flipped_slice],
                    "x": [float(np.min(x_coords_slice))],
                    "y": [float(np.min(y_coords_slice))],
                    "dw": [dw],
                    "dh": [dh],
                }
                # Update color mapper
                probe_min = float(np.percentile(flipped_slice[~np.isnan(flipped_slice)], 1))
                probe_max = float(np.percentile(flipped_slice[~np.isnan(flipped_slice)], 99))
                color_mapper2.low = probe_min
                color_mapper2.high = probe_max
        
        # Connect Plot3 selection to Plot2 computation
        # This will be triggered when user selects a region in Plot3
        def on_plot3_selection_change(attr, old, new):
            """Handle Plot3 selection change to compute Plot2."""
            if new and len(new) > 0:
                compute_plot2_from_plot3()
        
        # Note: BoxSelectTool selection is handled via JavaScript callback
        # We'll need to set up a proper callback mechanism
        
        # Create tools column using SCLib layout builder
        # Put status_div at the bottom of the tools column
        # Set max_height to prevent overflow and enable scrolling
        tools = create_tools_column(tools_items, width=400, max_height=800)  # Set max height to prevent overlap
        
        # Create plot columns with range inputs above each plot
        # Plot1 column
        plot1_items = []
        if range1_section is not None:
            plot1_items.append(range1_section)
        plot1_items.append(plot1)
        if plot1b is not None:
            if range1b_section is not None:
                plot1_items.append(range1b_section)
            plot1_items.append(plot1b)
        plot1_col = create_plot_column(plot1_items)
        
        # Plot2 column
        plot2_items = []
        if range2_section is not None:
            plot2_items.append(range2_section)
        plot2_items.append(plot2)
        if plot2b is not None:
            if range2b_section is not None:
                plot2_items.append(range2b_section)
            plot2_items.append(plot2b)
        plot2_col = create_plot_column(plot2_items)
        
        # Plot3 column
        plot3_items = []
        if range3_section is not None:
            plot3_items.append(range3_section)
        plot3_items.append(plot3)
        plot3_col = create_plot_column(plot3_items)
        
        # Create plots row - include Plot3
        plots = create_plots_row([plot1_col, plot2_col, plot3_col])
        
        # Connect tap event handlers
        plot1.on_event("tap", on_plot1_tap)
        plot2.on_event("tap", on_plot2_tap)
        plot2.on_event("doubletap", on_plot2_doubletap)
        plot3.on_event("tap", on_plot3_tap)
        
        # Note: Plot1B tap handler is already connected when Plot1B is created
        
        # Connect Plot2B tap handlers if it exists
        if plot2b is not None:
            plot2b.on_event("tap", on_plot2b_tap)
            plot2b.on_event("doubletap", on_plot2b_doubletap)
        
        # Draw initial rectangles if needed
        if not is_3d_volume:
            # Initialize rect2 to cover full range for 4D volumes
            rect2.set(
                min_x=0, max_x=volume.shape[2]-1,
                min_y=0, max_y=volume.shape[3]-1
            )
            draw_rect2()
        
        # Initialize rect3 to cover full range (use original coordinates, not flipped)
        # rect3 stores original coordinate values, not plot coordinates
        rect3.set(
            min_x=float(np.min(x_coords)), max_x=float(np.max(x_coords)),
            min_y=float(np.min(y_coords)), max_y=float(np.max(y_coords))
        )
        
        # Create main dashboard layout
        # Don't pass status_display separately since it's already in the tools column
        dashboard = create_dashboard_layout(
            tools_column=tools,
            plots_row=plots
        )
        
        # Start background memmap cache creation after dashboard is created
        # This allows the dashboard to display immediately while memmap is computed in background
        from bokeh.io import curdoc
        def start_background_memmap():
            """Start memmap cache creation in background after dashboard is rendered."""
            try:
                process_4dnexus.create_memmap_cache_background()
                if hasattr(process_4dnexus, 'volume_picked') and process_4dnexus.volume_picked:
                    process_4dnexus.create_memmap_cache_background_for(process_4dnexus.volume_picked)
                if hasattr(process_4dnexus, 'volume_picked_b') and process_4dnexus.volume_picked_b:
                    process_4dnexus.create_memmap_cache_background_for(process_4dnexus.volume_picked_b)
                print("✅ Background memmap cache creation started")
            except Exception as e:
                print(f"⚠️ Warning: failed to start background memmap caching: {e}")
        
        # Schedule background memmap creation after the dashboard is rendered
        curdoc().add_next_tick_callback(start_background_memmap)
        
        return dashboard
        
    except Exception as e:
        import traceback
        error_msg = str(e) if e else "Unknown error"
        print(f"Error in create_dashboard: {error_msg}")
        traceback.print_exc()
        return create_div(text=f"<h2>Error Loading Dashboard</h2><p>Error: {error_msg}</p><pre>{traceback.format_exc()}</pre>")


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

# bokeh serve 4d_dashboardLite.py --port 5017 --allow-websocket-origin=localhost:5017
