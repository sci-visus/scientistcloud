#!/usr/bin/env python3
"""
4D Dashboard with Dataset Selectors
Clean version with ratio selector functionality
"""

import numpy as np
import h5py
from bokeh.io import curdoc
import re
import time
from bokeh.layouts import column, row
from bokeh.models import (
    Button,
    ColumnDataSource,
    Div, 
    Select, 
    Slider,
    TextInput, 
    RadioButtonGroup,
    Toggle,
    LogScale,
    LinearScale,
    CustomJS
)
from bokeh.plotting import figure
from process_4dnexus import Process4dNexus

from utils_bokeh_dashboard import initialize_dashboard
from utils_bokeh_mongodb import cleanup_mongodb
from utils_bokeh_auth import authenticate_user
from utils_bokeh_param import parse_url_parameters, setup_directory_paths

# //////////////////////////////////////////////////////////////////////////
# Global variables for local testing and loading parameters from the URL 
import os
DOMAIN_NAME = os.getenv('DOMAIN_NAME', '')
DATA_IS_LOCAL = (DOMAIN_NAME == 'localhost' or DOMAIN_NAME == '' or DOMAIN_NAME is None)
 
local_base_dir = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil5/"
# base_dir = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil5/"
# save_dir = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil5/"
# nexus_filename    = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil5/mi_sic_0p33mm_002_PIL5_saxs_structured.nxs"
# mmap_filename     = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil5/mi_sic_0p33mm_002_PIL5_saxs_structured.float32.dat"

local_base_dir = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil11/"
# base_dir = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil11/"
# save_dir = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil11/"
# nexus_filename    = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil11/mi_sic_0p33mm_002_PIL9_PIL11_structured.nxs"
# mmap_filename     = f"/Users/amygooch/GIT/SCI/DATA/waxs/pil11/mi_sic_0p33mm_002_PIL9_PIL11_structured.float32.dat"
# cake = True
# azimuthal = False

# Select configuration based on filename and conditions
# if nexus_filename.endswith("PIL5_saxs_structured.nxs") and cake:
#     volume_path = "saxs_cake/data/I"
#     x_coords_path = "map_mi_sic_0p33mm_002/data/samx"
#     y_coords_path = "map_mi_sic_0p33mm_002/data/samz"
#     presample_path = "map_mi_sic_0p33mm_002/scalar_data/presample_intensity"
#     postsample_path = "map_mi_sic_0p33mm_002/scalar_data/postsample_intensity"
# elif nexus_filename.endswith("PIL9_PIL11_structured.nxs") and cake:
#     # Default for PIL9_PIL11 - can be customized below
#     volume_path = "saxs_cake/data/I"
#     x_coords_path = "map_mi_sic_0p33mm_002/data/samx"
#     y_coords_path = "map_mi_sic_0p33mm_002/data/samz"
#     presample_path = "map_mi_sic_0p33mm_002/scalar_data/presample_intensity"
#     postsample_path = "map_mi_sic_0p33mm_002/scalar_data/postsample_intensity"

# elif nexus_filename.endswith("PIL5_saxs_structured.nxs") and azimuthal:
#     volume_path = "waxs_azimuthal/data/I"
#     x_coords_path = "map_mi_sic_0p33mm_002/data/samx"
#     y_coords_path = "map_mi_sic_0p33mm_002/data/samz"
#     # probe_x_coords_path = "waxs_azimuthal/data/q_A^-1"
#     # probe_y_coords_path = "waxs_azimuthal/data/chi_deg"
#     presample_path = "map_mi_sic_0p33mm_002/scalar_data/presample_intensity"
#     postsample_path = "map_mi_sic_0p33mm_002/scalar_data/postsample_intensity"
# else:
#     # Default configuration
#     volume_path = "map_mi_sic_0p33mm_002/data/PIL11"
#     x_coords_path = "map_mi_sic_0p33mm_002/data/samx"
#     y_coords_path = "map_mi_sic_0p33mm_002/data/samz"
#     presample_path = "map_mi_sic_0p33mm_002/scalar_data/presample_intensity"
#     postsample_path = "map_mi_sic_0p33mm_002/scalar_data/postsample_intensity"

#local_base_dir = f'/Users/amygooch/GIT/SCI/DATA/4D_From_V'

# JWT secret key
sec_key = os.getenv('SECRET_KEY')

# Global variables
uuid = None
server = None
save_dir = None
base_dir = None
is_authorized = False
user_email = None
client = None
db = None
mymongodb = None
collection = None
collection1 = None
team_collection = None

status_div = None
status_messages = []  # Collect status messages instead of adding them as separate roots
realtime_status_div = None  # Real-time status display
DATA_IS_LOCAL = True

#//////////////////////////////////////////////////////////////////////////

def add_status_message(message):
    """Add a status message to the collection"""
    global status_messages
    status_messages.append(message)
    print(f"📝 {message}")

def create_status_display():
    """Create a single status display with all collected messages"""
    global status_messages
    if not status_messages:
        return None
    
    status_text = "<h3>Status Messages:</h3><ul>"
    for msg in status_messages:
        status_text += f"<li>{msg}</li>"
    status_text += "</ul>"
    
    return column(Div(text=status_text))

 

# //////////////////////////////////////////////////////////////////////////
def create_tmp_dashboard(process_4dnexus):
    """Create initial dashboard with dataset selectors only."""
    global status_display
    # Create status display
    status_display = create_status_display()
    
    # Get dataset choices from process_4dnexus
    datasets_2d = process_4dnexus.get_datasets_by_dimension(2)
    datasets_3d = process_4dnexus.get_datasets_by_dimension(3)
    datasets_4d = process_4dnexus.get_datasets_by_dimension(4)
    datasets_1d = process_4dnexus.get_datasets_by_dimension(1)

    css_style = Div(text="""
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
        """Find the first choice that starts with the given path"""
        for choice in choices:
            if choice.startswith(path_prefix):
                return choice
        return None
    
    # Set default values - find matching choices with shapes
    default_numerator = find_choice_by_path(plot1_h5_choices, "map_mi_sic_0p33mm_002/scalar_data/postsample_intensity") or (plot1_h5_choices[0] if plot1_h5_choices else "No 2D datasets")
    default_denominator = find_choice_by_path(plot1_h5_choices, "map_mi_sic_0p33mm_002/scalar_data/presample_intensity") or (plot1_h5_choices[1] if len(plot1_h5_choices) > 1 else plot1_h5_choices[0] if plot1_h5_choices else "No 2D datasets")
    default_plot2 = find_choice_by_path(plot2_h5_choices, "map_mi_sic_0p33mm_002/data/PIL11") or (plot2_h5_choices[0] if plot2_h5_choices else "No 3D/4D datasets")
    default_map_x = find_choice_by_path(coord_choices, "map_mi_sic_0p33mm_002/data/samx") or "Use Default"
    default_map_y = find_choice_by_path(coord_choices, "map_mi_sic_0p33mm_002/data/samz") or "Use Default"
    
    # Create mode selector for Plot1
    plot1_mode_selector = RadioButtonGroup(
        labels=["Single Dataset", "Ratio (Numerator/Denominator)"],
        active=1,
        width=400
    )

    # Create single dataset selector for Plot1
    plot1_h5_selector = Select(
        title="Plot1 Dataset (2D):",
        value=plot1_h5_choices[0] if plot1_h5_choices else "No 2D datasets",
        options=plot1_h5_choices if plot1_h5_choices else ["No 2D datasets"],
        width=300
    )
    
    # Create ratio selectors for Plot1
    plot1_h5_selector_numerator = Select(
        title="Plot1 Numerator (2D):",
        value=default_numerator,
        options=plot1_h5_choices if plot1_h5_choices else ["No 2D datasets"],
        width=300
    )
    
    plot1_h5_selector_denominator = Select(
        title="Plot1 Denominator (2D):",
        value=default_denominator,
        options=plot1_h5_choices if plot1_h5_choices else ["No 2D datasets"],
        width=300
    )


    # Optional Plot1B controls
    enable_plot1b_toggle = Toggle(label="Enable Plot1B (duplicate map)", active=False, width=250)
    
    # Plot1B mode selector (similar to Plot1)
    plot1b_mode_selector = RadioButtonGroup(
        labels=["Single Dataset", "Ratio (Numerator/Denominator)"],
        active=1,  # Default to ratio mode
        width=400
    )
    
    # Plot1B single dataset selector
    plot1b_h5_selector = Select(
        title="Plot1B Dataset (2D):",
        value=plot1_h5_choices[0] if plot1_h5_choices else "No 2D datasets",
        options=plot1_h5_choices if plot1_h5_choices else ["No 2D datasets"],
        width=300
    )
    
    # Plot1B ratio selectors
    plot1b_h5_selector_numerator = Select(
        title="Plot1B Numerator (2D):",
        value=default_numerator,
        options=plot1_h5_choices if plot1_h5_choices else ["No 2D datasets"],
        width=300
    )
    plot1b_h5_selector_denominator = Select(
        title="Plot1B Denominator (2D):",
        value=default_denominator,
        options=plot1_h5_choices if plot1_h5_choices else ["No 2D datasets"],
        width=300
    )
    
    # Initially hide all Plot1B selectors
    plot1b_mode_selector.visible = False
    plot1b_h5_selector.visible = False
    plot1b_h5_selector_numerator.visible = False
    plot1b_h5_selector_denominator.visible = False
    
    def on_enable_plot1b(attr, old, new):
        plot1b_mode_selector.visible = new
        if new:
            # Show selectors based on current mode
            if plot1b_mode_selector.active == 0:  # Single dataset mode
                plot1b_h5_selector.visible = True
                plot1b_h5_selector_numerator.visible = False
                plot1b_h5_selector_denominator.visible = False
            else:  # Ratio mode
                plot1b_h5_selector.visible = False
                plot1b_h5_selector_numerator.visible = True
                plot1b_h5_selector_denominator.visible = True
        else:
            plot1b_h5_selector.visible = False
            plot1b_h5_selector_numerator.visible = False
            plot1b_h5_selector_denominator.visible = False
    
    def on_plot1b_mode_change(attr, old, new):
        if enable_plot1b_toggle.active:
            if new == 0:  # Single dataset mode
                plot1b_h5_selector.visible = True
                plot1b_h5_selector_numerator.visible = False
                plot1b_h5_selector_denominator.visible = False
            else:  # Ratio mode
                plot1b_h5_selector.visible = False
                plot1b_h5_selector_numerator.visible = True
                plot1b_h5_selector_denominator.visible = True
    
    enable_plot1b_toggle.on_change("active", on_enable_plot1b)
    plot1b_mode_selector.on_change("active", on_plot1b_mode_change)

    # Optional Plot2B controls
    enable_plot2b_toggle = Toggle(label="Enable Plot2B (duplicate probe)", active=False, width=250)
    plot2b_h5_selector = Select(
        title="Plot2B Dataset (3D/4D):",
        value=default_plot2,
        options=plot2_h5_choices if plot2_h5_choices else ["No 3D/4D datasets"],
        width=300
    )
    plot2b_h5_selector.visible = False
    def on_enable_plot2b(attr, old, new):
        plot2b_h5_selector.visible = new
        probe_x_coords_selector_b.visible = new
        probe_y_coords_selector_b.visible = new
    enable_plot2b_toggle.on_change("active", on_enable_plot2b)

    plot2_h5_selector = Select(
        title="Plot2 Dataset (3D/4D):",
        value=default_plot2,
        options=plot2_h5_choices if plot2_h5_choices else ["No 3D/4D datasets"],
        width=300
    )
    
    # Create coordinate selectors (optional) - all populated with 1D datasets
    map_x_coords_selector = Select(
        title="Map X Coordinates (1D):",
        value=default_map_x,
        options=["Use Default"] + coord_choices,
        width=300
    )
    
    map_y_coords_selector = Select(
        title="Map Y Coordinates (1D):",
        value=default_map_y,
        options=["Use Default"] + coord_choices,
        width=300
    )
    
    probe_x_coords_selector = Select(
        title="Probe X Coordinates (1D):",
        value="Use Default",
        options=["Use Default"] + coord_choices,
        width=300
    )
    
    probe_y_coords_selector = Select(
        title="Probe Y Coordinates (1D):",
        value="Use Default",
        options=["Use Default"] + coord_choices,
        width=300
    )
    
    # Plot2B coordinate selectors (optional)
    probe_x_coords_selector_b = Select(
        title="Probe2B X Coordinates (1D):",
        value="Use Default",
        options=["Use Default"] + coord_choices,
        width=300
    )
    
    probe_y_coords_selector_b = Select(
        title="Probe2B Y Coordinates (1D):",
        value="Use Default",
        options=["Use Default"] + coord_choices,
        width=300
    )
    probe_x_coords_selector_b.visible = False
    probe_y_coords_selector_b.visible = False
    
    # Create placeholder plots that will be populated after user selection
    plot1_placeholder = Div(text="<h3>Plot1: Select a 2D dataset above and click 'Initialize Plots'</h3>", width=400, height=300)
    plot2_placeholder = Div(text="<h3>Plot2: Select a 3D/4D dataset above and click 'Initialize Plots'</h3>", width=400, height=300)
    plot3_placeholder = Div(text="<h3>Plot3: Will be created after plot initialization</h3>", width=400, height=300)
   
    # Create a button to initialize plots after selection
    initialize_plots_button = Button(label="Initialize Plots", button_type="primary")
   
    # Helper function to extract dataset path from selection (removes shape info)
    def extract_dataset_path(selection_with_shape):
        """Extract just the dataset path from 'path shape' format."""
        if selection_with_shape in ["No 2D datasets", "No 3D/4D datasets", "Use Default"]:
            return selection_with_shape
        
        # Find the last occurrence of ' (' to separate path from shape
        # Shape format is like: "path (shape1, shape2, shape3, shape4)"
        last_paren = selection_with_shape.rfind(' (')
        if last_paren != -1:
            return selection_with_shape[:last_paren]
        else:
            # Fallback: if no shape found, return as-is
            return selection_with_shape

    def initialize_plots_callback(process_4dnexus):
        """Callback for when user clicks 'Initialize Plots' button."""
        print("Initializing plots with selected datasets...")
        
        # Get the selected datasets
        plot2_selection = plot2_h5_selector.value
        plot2_path = extract_dataset_path(plot2_selection)
        
        if plot2_path == "No 3D/4D datasets":
            print("Please select valid datasets before initializing plots")
            return
        else:
            process_4dnexus.volume_picked = plot2_path

        try:
            # Determine Plot1 selection based on mode
            if plot1_mode_selector.active == 0:  # Single dataset mode
                plot1_selection = plot1_h5_selector.value
                plot1_path = extract_dataset_path(plot1_selection)
                if plot1_path == "No 2D datasets":
                    print("Please select valid datasets before initializing plots")
                    return
                print(f"Plot1 mode: Single dataset - {plot1_path}")
                # Set single dataset
                process_4dnexus.plot1_single_dataset_picked = plot1_path  # Store single dataset path
                process_4dnexus.presample_picked = None  # No ratio calculation
                process_4dnexus.postsample_picked = None
            else:  # Ratio mode
                numerator_selection = plot1_h5_selector_numerator.value
                denominator_selection = plot1_h5_selector_denominator.value
                numerator_path = extract_dataset_path(numerator_selection)
                denominator_path = extract_dataset_path(denominator_selection)
                if numerator_path == "No 2D datasets" or denominator_path == "No 2D datasets":
                    print("Please select valid datasets for numerator and denominator")
                    return
                print(f"Plot1 mode: Ratio - {numerator_path} / {denominator_path}")
                # Set ratio datasets
                process_4dnexus.plot1_single_dataset_picked = None  # Clear single dataset when in ratio mode
                process_4dnexus.presample_picked = numerator_path
                process_4dnexus.postsample_picked = denominator_path
            
            # Optional Plot1B (supports both single dataset and ratio modes)
            if enable_plot1b_toggle.active:
                if plot1b_mode_selector.active == 0:  # Single dataset mode
                    plot1b_selection = plot1b_h5_selector.value
                    plot1b_path = extract_dataset_path(plot1b_selection)
                    if plot1b_path != "No 2D datasets":
                        process_4dnexus.plot1b_single_dataset_picked = plot1b_path
                        process_4dnexus.presample_picked_b = None
                        process_4dnexus.postsample_picked_b = None
                        print(f"  Plot1B: {plot1b_path} (single dataset)")
                    else:
                        process_4dnexus.plot1b_single_dataset_picked = None
                        process_4dnexus.presample_picked_b = None
                        process_4dnexus.postsample_picked_b = None
                else:  # Ratio mode
                    numerator_b_selection = plot1b_h5_selector_numerator.value
                    denominator_b_selection = plot1b_h5_selector_denominator.value
                    numerator_b_path = extract_dataset_path(numerator_b_selection)
                    denominator_b_path = extract_dataset_path(denominator_b_selection)
                    if numerator_b_path != "No 2D datasets" and denominator_b_path != "No 2D datasets":
                        process_4dnexus.plot1b_single_dataset_picked = None
                        process_4dnexus.presample_picked_b = numerator_b_path
                        process_4dnexus.postsample_picked_b = denominator_b_path
                        print(f"  Plot1B: {numerator_b_path} / {denominator_b_path}")
                    else:
                        process_4dnexus.plot1b_single_dataset_picked = None
                        process_4dnexus.presample_picked_b = None
                        process_4dnexus.postsample_picked_b = None
            else:
                process_4dnexus.plot1b_single_dataset_picked = None
                process_4dnexus.presample_picked_b = None
                process_4dnexus.postsample_picked_b = None

            # Set coordinate datasets based on user selection
            map_x_coords_selection = map_x_coords_selector.value
            map_y_coords_selection = map_y_coords_selector.value
            probe_x_coords_selection = probe_x_coords_selector.value
            probe_y_coords_selection = probe_y_coords_selector.value
            
            map_x_coords = extract_dataset_path(map_x_coords_selection)
            map_y_coords = extract_dataset_path(map_y_coords_selection)
            probe_x_coords = extract_dataset_path(probe_x_coords_selection)
            probe_y_coords = extract_dataset_path(probe_y_coords_selection)
            
            # Set map coordinates
            if map_x_coords != "Use Default":
                process_4dnexus.x_coords_picked = map_x_coords
            else:
                process_4dnexus.x_coords_picked = "map_mi_sic_0p33mm_002/data/samx"
                
            if map_y_coords != "Use Default":
                process_4dnexus.y_coords_picked = map_y_coords
            else:
                process_4dnexus.y_coords_picked = "map_mi_sic_0p33mm_002/data/samz"
            
            # Store probe coordinates for later use (if needed)
            process_4dnexus.probe_x_coords_picked = probe_x_coords if probe_x_coords != "Use Default" else None
            process_4dnexus.probe_y_coords_picked = probe_y_coords if probe_y_coords != "Use Default" else None
            
            # Optional Plot2B (duplicate volume)
            if enable_plot2b_toggle.active:
                plot2b_selection = plot2b_h5_selector.value
                plot2b_path = extract_dataset_path(plot2b_selection)
                if plot2b_path != "No 3D/4D datasets":
                    process_4dnexus.volume_picked_b = plot2b_path
                    print(f"  Plot2B: {plot2b_path}")
                    
                    # Store Plot2B probe coordinates
                    probe_x_coords_selection_b = probe_x_coords_selector_b.value
                    probe_y_coords_selection_b = probe_y_coords_selector_b.value
                    probe_x_coords_b = extract_dataset_path(probe_x_coords_selection_b)
                    probe_y_coords_b = extract_dataset_path(probe_y_coords_selection_b)
                    process_4dnexus.probe_x_coords_picked_b = probe_x_coords_b if probe_x_coords_b != "Use Default" else None
                    process_4dnexus.probe_y_coords_picked_b = probe_y_coords_b if probe_y_coords_b != "Use Default" else None
                    print(f"  Plot2B Probe X coords: {probe_x_coords_b}")
                    print(f"  Plot2B Probe Y coords: {probe_y_coords_b}")
                else:
                    process_4dnexus.volume_picked_b = None
                    process_4dnexus.probe_x_coords_picked_b = None
                    process_4dnexus.probe_y_coords_picked_b = None
            else:
                process_4dnexus.volume_picked_b = None
                process_4dnexus.probe_x_coords_picked_b = None
                process_4dnexus.probe_y_coords_picked_b = None

            print(f"Successfully initialized plots with:")
            if plot1_mode_selector.active == 0:
                print(f"  Plot1: {plot1_path} (single dataset)")
            else:
                print(f"  Plot1: {numerator_path} / {denominator_path} (ratio)")
            print(f"  Plot2: {plot2_path}")
            print(f"  Map X coords: {map_x_coords}")
            print(f"  Map Y coords: {map_y_coords}")
            print(f"  Probe X coords: {probe_x_coords}")
            print(f"  Probe Y coords: {probe_y_coords}")
            
            # Immediately show a lightweight loading view, then build dashboard next tick
            from bokeh.io import curdoc as _curdoc
            loading = column(Div(text="<h3>Loading full dashboard...</h3>"))
            _curdoc().clear()
            _curdoc().add_root(loading)

            def _build_and_swap():
                try:
                    full_dashboard = create_dashboard(process_4dnexus)
                    _curdoc().clear()
                    _curdoc().add_root(full_dashboard)
                finally:
                    # After render, kick off background memmap caching
                    try:
                        process_4dnexus.create_memmap_cache_background()
                        if getattr(process_4dnexus, 'volume_picked', None):
                            process_4dnexus.create_memmap_cache_background_for(process_4dnexus.volume_picked)
                        if getattr(process_4dnexus, 'volume_picked_b', None):
                            process_4dnexus.create_memmap_cache_background_for(process_4dnexus.volume_picked_b)
                    except Exception as e_mem:
                        print(f"Warning: failed to start background memmap caching: {e_mem}")

            _curdoc().add_next_tick_callback(_build_and_swap)
            
        except Exception as e:
            print(f"Error initializing plots: {e}")
    
    # Add callback for mode selector to show/hide appropriate selectors
    def on_mode_change(attr, old, new):
        """Show/hide selectors based on mode selection"""
        if new == 0:  # Single dataset mode
            plot1_h5_selector.visible = True
            plot1_h5_selector_numerator.visible = False
            plot1_h5_selector_denominator.visible = False
        else:  # Ratio mode
            plot1_h5_selector.visible = False
            plot1_h5_selector_numerator.visible = True
            plot1_h5_selector_denominator.visible = True
    
    plot1_mode_selector.on_change("active", on_mode_change)
    
    # Set initial visibility
    on_mode_change("active", 0, 0)  # Initialize with single dataset mode
    
    # Add callback for initialize button
    initialize_plots_button.on_click(lambda: initialize_plots_callback(process_4dnexus))
    
        #Set defaults 
    plot1_h5_selector.visible = False
    plot1_h5_selector_numerator.visible = True
    plot1_h5_selector_denominator.visible = True

    plot2_tmp_spacer = Div(text="", height=60)  # Spacer to align with Plot2's toggle + button row
 
    # Create the main layout
    main_layout = column(
        css_style,
        # Dataset selection section
        Div(text="<h2>4D Dashboard - Dataset Selection</h2>"),
        row(
            column(
                # ========== Plot 1 Configuration ==========
                Div(text="<h3>Plot1 Configuration:</h3>"),
                plot1_mode_selector,
                Div(text="<br>"),
                
                # Plot1 selectors (conditional based on mode)
                row(
                    column(plot1_h5_selector, width=300, name="single_dataset_selector"),
                    column(plot1_h5_selector_numerator, width=300, name="numerator_selector"),
                    column(plot1_h5_selector_denominator, width=300, name="denominator_selector"),
                    sizing_mode="stretch_width"
                ),
                
                # Plot1 coordinate selectors
                row(
                    column(map_x_coords_selector, width=300),
                    column(map_y_coords_selector, width=300),
                    sizing_mode="stretch_width"
                ),
                
                # Plot1B (optional duplicate)
                Div(text="<h3>Optional Plot1B (duplicate map):</h3>"),
                row(
                    column(
                        enable_plot1b_toggle,
                        plot1b_mode_selector,
                        plot1b_h5_selector,
                        plot1b_h5_selector_numerator,
                        plot1b_h5_selector_denominator,
                        width=320
                    ),
                ),
                
                Div(text="<hr>"),
            ),
            column(
            # ========== Plot 2 Configuration ==========
            Div(text="<h3>Plot2 Configuration:</h3>"),
            row(
                column(plot2_h5_selector, width=300),
                sizing_mode="stretch_width"
            ),
            
            # Plot2 coordinate selectors
            row(
                column(probe_x_coords_selector, width=300),
                column(probe_y_coords_selector, width=300),
                sizing_mode="stretch_width"
            ),
            
            # Plot2B (optional duplicate)
            plot2_tmp_spacer,
            Div(text="<h3>Optional Plot2B (duplicate probe):</h3>"),
            row(
                column(enable_plot2b_toggle, plot2b_h5_selector, width=320),
            ),
            
            # Plot2B coordinate selectors
            row(
                column(probe_x_coords_selector_b, width=300),
                column(probe_y_coords_selector_b, width=300),
                sizing_mode="stretch_width"
            ),
            
            Div(text="<hr>"),
            
            column(initialize_plots_button, width=200),
            Div(text="<hr>"),
            ),
        ),
        row(status_display, sizing_mode="stretch_both"),
		sizing_mode="stretch_both"
    )
    
    return main_layout

# //////////////////////////////////////////////////////////////////////////
def update_1d_plot(volume, x_index, y_index, source2, plot2, process_4dnexus=None, use_b=False):
    """Update 1D plot for 3D volume datasets
    
    Args:
        volume: The volume data
        x_index: X index position
        y_index: Y index position
        source2: Bokeh ColumnDataSource to update
        plot2: Bokeh plot to update
        process_4dnexus: Process4dNexus instance
        use_b: If True, use Plot2B coordinates (probe_x_coords_picked_b), otherwise use Plot2A coordinates
    """
    try:
        plot_name = "Plot2B" if use_b else "Plot2"
        print(f"📊 Updating {plot_name} 1D plot for 3D volume at position ({x_index}, {y_index})")
        
        # Store original axis labels to preserve them
        original_x_label = plot2.xaxis.axis_label if hasattr(plot2.xaxis, 'axis_label') else None
        original_y_label = plot2.yaxis.axis_label if hasattr(plot2.yaxis, 'axis_label') else None
        
        # For 3D volume: volume[x_index, y_index, :] gives us the 1D data
        if len(volume.shape) == 3:
            # Extract 1D data slice
            plot_data_1d = volume[x_index, y_index, :]
            
            # Use probe coordinates if available - check for Plot2B vs Plot2A
            coord_attr = 'probe_x_coords_picked_b' if use_b else 'probe_x_coords_picked'
            if process_4dnexus and getattr(process_4dnexus, coord_attr, None):
                try:
                    probe_coords = process_4dnexus.load_probe_coordinates(use_b=use_b)
                    if probe_coords is not None and len(probe_coords) == len(plot_data_1d):
                        x_coords_1d = probe_coords
                        print(f"Using {plot_name} probe coordinates for update: {len(probe_coords)} points")
                    else:
                        x_coords_1d = np.arange(len(plot_data_1d))
                        print(f"{plot_name} probe coordinates not available for update, using indices")
                except:
                    x_coords_1d = np.arange(len(plot_data_1d))
                    print(f"Failed to load {plot_name} probe coordinates for update, using indices")
            else:
                x_coords_1d = np.arange(len(plot_data_1d))
                print(f"No {plot_name} probe coordinates for update, using indices")
            
            # Update the 1D data source
            source2.data = {
                'x': x_coords_1d,
                'y': plot_data_1d
            }
            
            # Update the plot ranges to fit the new data
            plot2.x_range.start = x_coords_1d.min()
            plot2.x_range.end = x_coords_1d.max()
            
            # For y-axis, handle log scale if enabled
            if hasattr(plot2, 'y_scale') and isinstance(plot2.y_scale, LogScale):
                # For log scale, only use positive values
                positive_data = plot_data_1d[plot_data_1d > 0]
                if positive_data.size > 0:
                    y_min = max(np.min(positive_data), 0.001)
                    y_max = np.max(positive_data)
                    plot2.y_range.start = y_min
                    plot2.y_range.end = y_max
                else:
                    # No positive values, use small default range
                    plot2.y_range.start = 0.001
                    plot2.y_range.end = 1.0
            else:
                # Linear scale - use all data
                plot2.y_range.start = plot_data_1d.min()
                plot2.y_range.end = plot_data_1d.max()
            
            # Restore axis labels if they were set
            if original_x_label:
                plot2.xaxis.axis_label = original_x_label
            if original_y_label:
                plot2.yaxis.axis_label = original_y_label
            
            print(f"✅ {plot_name} 1D plot updated with {len(plot_data_1d)} points")
            print(f"   1D data range: {plot_data_1d.min():.3f} to {plot_data_1d.max():.3f}")
            print(f"   X coordinate range: {x_coords_1d.min():.3f} to {x_coords_1d.max():.3f}")
            
        else:
            print(f"❌ update_1d_plot called but volume is not 3D")
            
    except Exception as e:
        print(f"❌ Error in update_1d_plot: {str(e)}")

# //////////////////////////////////////////////////////////////////////////
# Lightweight reusable plot classes to allow multiple instances of map/probe plots
class MapPlot:
    def __init__(self, x_coords, y_coords, image_2d, title="Plot1 - Map View"):
        from bokeh.plotting import figure
        from bokeh.models import ColumnDataSource
        import numpy as np

        # Build figure
        self.figure = figure(
            title=title,
            x_range=(float(np.min(x_coords)), float(np.max(x_coords))),
            y_range=(float(np.min(y_coords)), float(np.max(y_coords))),
            tools="pan,wheel_zoom,box_zoom,reset,tap",
        )

        # Populate source
        self.source = ColumnDataSource(
            data={
                "image": [image_2d],
                "x": [float(np.min(x_coords))],
                "y": [float(np.min(y_coords))],
                "dw": [float(np.max(x_coords) - np.min(x_coords))],
                "dh": [float(np.max(y_coords) - np.min(y_coords))],
            }
        )

    def get_components(self):
        return self.figure, self.source


class ProbePlot:
    def __init__(self, volume, process_4dnexus=None, title_1d="Plot2 - 1D Probe View", title_2d="Plot2 - 2D Probe View", use_b=False):
        from bokeh.plotting import figure
        from bokeh.models import ColumnDataSource
        import numpy as np

        self.is_3d = len(volume.shape) == 3
        if self.is_3d:
            initial_slice_1d = volume[volume.shape[0]//2, volume.shape[1]//2, :]
            # Try probe coordinates
            coord_attr = 'probe_x_coords_picked_b' if use_b else 'probe_x_coords_picked'
            if process_4dnexus and getattr(process_4dnexus, coord_attr, None):
                try:
                    probe_coords = process_4dnexus.load_probe_coordinates(use_b=use_b)
                    coord_path = getattr(process_4dnexus, coord_attr)
                    if probe_coords is not None and len(probe_coords) == len(initial_slice_1d):
                        x_coords_1d = probe_coords
                        x_label = f"Probe Coordinate ({coord_path.split('/')[-1]})"
                    else:
                        x_coords_1d = np.arange(len(initial_slice_1d))
                        x_label = "Probe Index"
                except Exception:
                    x_coords_1d = np.arange(len(initial_slice_1d))
                    x_label = "Probe Index"
            else:
                x_coords_1d = np.arange(len(initial_slice_1d))
                x_label = "Probe Index"

            self.figure = figure(
                title=title_1d,
                tools="pan,wheel_zoom,box_zoom,reset,tap",
                x_range=(float(np.min(x_coords_1d)), float(np.max(x_coords_1d))),
                y_range=(float(np.min(initial_slice_1d)), float(np.max(initial_slice_1d))),
            )
            self.figure.xaxis.axis_label = x_label
            self.figure.yaxis.axis_label = "Intensity"
            self.source = ColumnDataSource(data={"x": x_coords_1d, "y": initial_slice_1d})
        else:
            # 4D: make a 2D image from center slice
            initial_slice = volume[volume.shape[0]//2, volume.shape[1]//2, :, :]
            self.figure = figure(
                title=title_2d,
                tools="pan,wheel_zoom,box_zoom,reset,tap",
                x_range=(0, volume.shape[2]),
                y_range=(0, volume.shape[3]),
                match_aspect=True,
            )
            self.source = ColumnDataSource(
                data={
                    "image": [initial_slice],
                    "x": [0],
                    "y": [0],
                    "dw": [volume.shape[2]],
                    "dh": [volume.shape[3]],
                }
            )

    def get_components(self):
        return self.figure, self.source


def create_dashboard(process_4dnexus):
    global status_display
    try:
        # Font size variables - change these to adjust all font sizes throughout the dashboard
        FONT_SIZE_PLOT_TITLE = "14px"          # Plot titles
        FONT_SIZE_AXIS_LABEL = "14px"          # Axis labels (x, y labels)
        FONT_SIZE_AXIS_TICKS = "14px"          # Axis tick labels
        FONT_SIZE_COLORBAR_TITLE = "14px"      # Colorbar titles
        FONT_SIZE_COLORBAR_LABELS = "14px"     # Colorbar tick labels
        
        t0 = time.time()
        print("[TIMING] create_dashboard(): start")
        # Load the data first
        volume, presample, postsample, x_coords, y_coords, preview = process_4dnexus.load_nexus_data()
        print(f"[TIMING] after load_nexus_data: {time.time()-t0:.3f}s")
        
        print(f"Successfully loaded data:")
        print(f"  Volume shape: {volume.shape}")
        print(f"  X coords shape: {x_coords.shape}")
        print(f"  Y coords shape: {y_coords.shape}")
        print(f"  Preview shape: {preview.shape}")
        
        # Start background memmap cache creation (deferred to after initial render)
        
        # Check if volume is 3D (for 1D probe plot) or 4D (for 2D probe plot)
        is_3d_volume = len(volume.shape) == 3
        print(f"  Volume dimensionality: {'3D (1D probe plot)' if is_3d_volume else '4D (2D probe plot)'}")
        
        # Import additional Bokeh components needed for the full dashboard
        from bokeh.models import (
            Slider, Toggle, TapTool, CustomJS, HoverTool, 
            ColorBar, LinearColorMapper, LogColorMapper, TextInput,
            LogScale, LinearScale
        )
        from bokeh.transform import linear_cmap
        import matplotlib.colors as colors
        t1 = time.time()
        print(f"[TIMING] after imports: {t1-t0:.3f}s")
        
        # Color palettes
        palettes = [
            "Viridis256", "Plasma256", "Inferno256", "Magma256", 
            "Cividis256", "Turbo256", "Greys256", "Blues256"
        ]
        
        # Rectangle class for selection areas
        class Rectangle:
            def __init__(self, min_x=0, min_y=0, max_x=0, max_y=0):
                self.min_x = min_x
                self.min_y = min_y
                self.max_x = max_x
                self.max_y = max_y
                self.h1line = None
                self.h2line = None
                self.v1line = None
                self.v2line = None

            def swap_if_needed(self):
                # For 3D volumes, we don't want to swap min/max automatically
                # because we're setting them independently (min via shift+click, max via ctrl+click/double-click)
                # Only swap for 4D volumes where we have proper rectangle selection
                if not is_3d_volume:
                    if self.min_x > self.max_x:
                        self.min_x, self.max_x = self.max_x, self.min_x
                    if self.min_y > self.max_y:
                        self.min_y, self.max_y = self.max_y, self.min_y

            def set(self, min_x=None, min_y=None, max_x=None, max_y=None):
                if min_x != None:
                    self.min_x = min_x
                if min_y != None:
                    self.min_y = min_y
                if max_x != None:
                    self.max_x = max_x
                if max_y != None:
                    self.max_y = max_y
                self.swap_if_needed()

            # Initialize rectangles for selection areas
        rect1 = Rectangle(0, 0, volume.shape[0] - 1, volume.shape[1] - 1)  # X,Y
        # rect1b will be initialized after Plot1B is created
        rect1b = None
        if is_3d_volume:
            # For 3D volume: rect2 represents the 1D probe dimension
            rect2 = Rectangle(0, 0, volume.shape[2] - 1, volume.shape[2] - 1)  # 1D probe
        else:
            # For 4D volume: rect2 represents Z,Y dimensions
            rect2 = Rectangle(0, 0, volume.shape[2] - 1, volume.shape[3] - 1)  # Z,Y
        rect3 = Rectangle(0, 0, volume.shape[0] - 1, volume.shape[1] - 1)  # X,Y

        # Set probe positions to middle of the data range
        x_index = volume.shape[0] // 2
        y_index = volume.shape[1] // 2

        # Create tick arrays for axis labels
        dx, dy = 15, 15
        x_ticks, my_xticks = [], []
        for i in range(0, len(x_coords), dx):
            x_ticks.append(x_coords[i])
            my_xticks.append(f"{x_coords[i]:.1f}")

        y_ticks, my_yticks = [], []
        for i in range(0, len(y_coords), dy):
            y_ticks.append(y_coords[i])
            my_yticks.append(f"{y_coords[i]:.1f}")

        # Helper functions to generate meaningful plot titles
        def get_plot1_title():
            if getattr(process_4dnexus, 'plot1_single_dataset_picked', None):
                return f"Plot1: {process_4dnexus.plot1_single_dataset_picked}"
            elif getattr(process_4dnexus, 'postsample_picked', None) and getattr(process_4dnexus, 'presample_picked', None):
                return f"Plot1: {process_4dnexus.postsample_picked} / {process_4dnexus.presample_picked}"
            else:
                return "Plot1 - Map View"
        
        def get_plot1b_title():
            if getattr(process_4dnexus, 'plot1b_single_dataset_picked', None):
                return f"Plot1B: {process_4dnexus.plot1b_single_dataset_picked}"
            elif getattr(process_4dnexus, 'postsample_picked_b', None) and getattr(process_4dnexus, 'presample_picked_b', None):
                return f"Plot1B: {process_4dnexus.postsample_picked_b} / {process_4dnexus.presample_picked_b}"
            else:
                return "Plot1B - Map View"
        
        def get_plot2_title():
            if getattr(process_4dnexus, 'volume_picked', None):
                return f"Plot2: {process_4dnexus.volume_picked}"
            else:
                return "Plot2 - Probe View"
        
        def get_plot2b_title():
            if getattr(process_4dnexus, 'volume_picked_b', None):
                return f"Plot2B: {process_4dnexus.volume_picked_b}"
            else:
                return "Plot2B - Probe View"
        
        # Get axis labels from process_4dnexus
        plot1_x_label = getattr(process_4dnexus, 'x_coords_picked', 'X Position')
        plot1_y_label = getattr(process_4dnexus, 'y_coords_picked', 'Y Position')
        # Extract just the coordinate name if it's a path
        if '/' in plot1_x_label:
            plot1_x_label = plot1_x_label.split('/')[-1]
        if '/' in plot1_y_label:
            plot1_y_label = plot1_y_label.split('/')[-1]

        # Create Plot1 (Map view) using reusable class
        map_plot = MapPlot(x_coords, y_coords, preview, title=get_plot1_title())
        plot1, source1 = map_plot.get_components()
        plot1.xaxis.ticker = x_ticks
        plot1.yaxis.ticker = y_ticks
        plot1.xaxis.major_label_overrides = dict(zip(x_ticks, my_xticks))
        plot1.yaxis.major_label_overrides = dict(zip(y_ticks, my_yticks))
        plot1.xaxis.axis_label = plot1_x_label
        plot1.yaxis.axis_label = plot1_y_label
        # Set font sizes
        plot1.title.text_font_size = FONT_SIZE_PLOT_TITLE
        plot1.xaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
        plot1.yaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
        plot1.xaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
        plot1.yaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
        print(f"[TIMING] plot1 built: {time.time()-t0:.3f}s")

        # Create Plot2 (Probe view) - show actual volume slice
        # Create Plot2 (Probe view) using reusable class
        plot2_title = get_plot2_title()
        probe_plot = ProbePlot(volume, process_4dnexus, title_1d=plot2_title, title_2d=plot2_title)
        plot2, source2 = probe_plot.get_components()
        
        # Update Plot2 axis labels if available
        if is_3d_volume:
            # For 1D plots, x-axis is already set in ProbePlot, but update y-axis if needed
            plot2_probe_x = getattr(process_4dnexus, 'probe_x_coords_picked', None)
            if plot2_probe_x:
                plot2_x_label = plot2_probe_x.split('/')[-1] if '/' in plot2_probe_x else plot2_probe_x
                plot2.xaxis.axis_label = plot2_x_label
            plot2_probe_y = getattr(process_4dnexus, 'probe_y_coords_picked', None)
            if plot2_probe_y:
                plot2_y_label = plot2_probe_y.split('/')[-1] if '/' in plot2_probe_y else plot2_probe_y
                plot2.yaxis.axis_label = plot2_y_label
        else:
            # For 2D plots, set both axes
            plot2_probe_x = getattr(process_4dnexus, 'probe_x_coords_picked', None)
            plot2_probe_y = getattr(process_4dnexus, 'probe_y_coords_picked', None)
            if plot2_probe_x:
                plot2_x_label = plot2_probe_x.split('/')[-1] if '/' in plot2_probe_x else plot2_probe_x
                plot2.xaxis.axis_label = plot2_x_label
            else:
                plot2.xaxis.axis_label = "Probe X"
            if plot2_probe_y:
                plot2_y_label = plot2_probe_y.split('/')[-1] if '/' in plot2_probe_y else plot2_probe_y
                plot2.yaxis.axis_label = plot2_y_label
            else:
                plot2.yaxis.axis_label = "Probe Y"
        # Set font sizes
        plot2.title.text_font_size = FONT_SIZE_PLOT_TITLE
        plot2.xaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
        plot2.yaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
        plot2.xaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
        plot2.yaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
        # Capture initial slices for defaults and overlays
        initial_slice = None
        initial_slice_1d = None
        if not is_3d_volume:
            try:
                if isinstance(source2.data, dict) and 'image' in source2.data and len(source2.data['image']) > 0:
                    initial_slice = source2.data['image'][0]
            except Exception:
                initial_slice = None
        else:
            try:
                if isinstance(source2.data, dict) and 'y' in source2.data and len(source2.data['y']) > 0:
                    import numpy as _np
                    initial_slice_1d = _np.asarray(source2.data['y'])
            except Exception:
                initial_slice_1d = None
        if len(volume.shape) == 3:
            range_overlay_source = ColumnDataSource(data={"x": [], "y": [], "width": [], "height": []})
        print(f"[TIMING] plot2 built: {time.time()-t0:.3f}s")

        # Create Plot3 (Additional view) - works for both 3D and 4D volumes
        plot3 = figure(
            title="Plot3 - Additional View",
            tools="pan,wheel_zoom,box_zoom,reset,tap",
            x_range=(x_coords.min(), x_coords.max()),
            y_range=(y_coords.min(), y_coords.max()),
        )

        plot3.x_range.start = x_coords.min()
        plot3.x_range.end = x_coords.max()
        plot3.y_range.start = y_coords.min()
        plot3.y_range.end = y_coords.max()
        plot3.xaxis.ticker = x_ticks
        plot3.yaxis.ticker = y_ticks
        plot3.xaxis.major_label_overrides = dict(zip(x_ticks, my_xticks))
        plot3.yaxis.major_label_overrides = dict(zip(y_ticks, my_yticks))
        plot3.xaxis.axis_label = plot1_x_label
        plot3.yaxis.axis_label = plot1_y_label
        # Set font sizes
        plot3.title.text_font_size = FONT_SIZE_PLOT_TITLE
        plot3.xaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
        plot3.yaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
        plot3.xaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
        plot3.yaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
        print(f"[TIMING] plot3 built: {time.time()-t0:.3f}s")

        # Create an empty source3; Plot3 will be populated on demand via Compute Plot3
        source3 = ColumnDataSource(
            data={
                "image": [],
                "x": [],
                "y": [],
                "dw": [],
                "dh": [],
            }
        )
        print(f"[TIMING] source3 built: {time.time()-t0:.3f}s")

        # Optionally create Plot1B below Plot1 if specified
        plot1b = None
        # Check for single dataset mode first
        if getattr(process_4dnexus, 'plot1b_single_dataset_picked', None):
            try:
                single_dataset_b = process_4dnexus.load_dataset_by_path(process_4dnexus.plot1b_single_dataset_picked)
                if single_dataset_b is not None:
                    # Flatten if needed and reshape
                    if single_dataset_b.ndim > 1:
                        single_dataset_b_flat = single_dataset_b.flatten()
                    else:
                        single_dataset_b_flat = single_dataset_b
                    
                    if single_dataset_b_flat.size == len(x_coords) * len(y_coords):
                        preview_b_rect = np.reshape(single_dataset_b_flat, (len(x_coords), len(y_coords)))
                        # Clean the data
                        preview_b = np.nan_to_num(preview_b_rect, nan=0.0, posinf=0.0, neginf=0.0)
                        # Normalize
                        if np.max(preview_b) > np.min(preview_b):
                            preview_b = (preview_b - np.min(preview_b)) / (np.max(preview_b) - np.min(preview_b))
                        preview_b = preview_b.astype(np.float32)
                        map_plot_b = MapPlot(x_coords, y_coords, preview_b, title=get_plot1b_title())
                        plot1b, source1b = map_plot_b.get_components()
                        plot1b.xaxis.ticker = x_ticks
                        plot1b.yaxis.ticker = y_ticks
                        plot1b.xaxis.major_label_overrides = dict(zip(x_ticks, my_xticks))
                        plot1b.yaxis.major_label_overrides = dict(zip(y_ticks, my_yticks))
                        plot1b.xaxis.axis_label = plot1_x_label
                        plot1b.yaxis.axis_label = plot1_y_label
                        # Set font sizes
                        plot1b.title.text_font_size = FONT_SIZE_PLOT_TITLE
                        plot1b.xaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
                        plot1b.yaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
                        plot1b.xaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
                        plot1b.yaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
                    else:
                        print(f"Failed to build Plot1B: single dataset size mismatch ({single_dataset_b_flat.size} vs {len(x_coords) * len(y_coords)})")
            except Exception as e:
                print(f"Failed to build Plot1B (single dataset mode): {e}")
                import traceback
                traceback.print_exc()
        # Check for ratio mode
        elif getattr(process_4dnexus, 'presample_picked_b', None) and getattr(process_4dnexus, 'postsample_picked_b', None):
            try:
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
                    map_plot_b = MapPlot(x_coords, y_coords, preview_b, title=get_plot1b_title())
                    plot1b, source1b = map_plot_b.get_components()
                    plot1b.xaxis.ticker = x_ticks
                    plot1b.yaxis.ticker = y_ticks
                    plot1b.xaxis.major_label_overrides = dict(zip(x_ticks, my_xticks))
                    plot1b.yaxis.major_label_overrides = dict(zip(y_ticks, my_yticks))
                    plot1b.xaxis.axis_label = plot1_x_label
                    plot1b.yaxis.axis_label = plot1_y_label
                    # Set font sizes
                    plot1b.title.text_font_size = FONT_SIZE_PLOT_TITLE
                    plot1b.xaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
                    plot1b.yaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
                    plot1b.xaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
                    plot1b.yaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
            except Exception as e:
                print(f"Failed to build Plot1B (ratio mode): {e}")
                import traceback
                traceback.print_exc()

        print(f"[TIMING] preview b built: {time.time()-t0:.3f}s")
        
        # Initialize rect1b for Plot1B crosshairs if Plot1B exists
        if 'plot1b' in locals() and plot1b is not None:
            rect1b = Rectangle(0, 0, volume.shape[0] - 1, volume.shape[1] - 1)  # X,Y for Plot1B

        # Optionally create Plot2B below Plot2 if specified
        plot2b = None
        rect2b = None
        if getattr(process_4dnexus, 'volume_picked_b', None):
            try:
                # Use the already-open HDF5 dataset reference when available
                volume_b = getattr(process_4dnexus, 'volume_dataset_b', None)
                if volume_b is not None:
                    plot2b_title = get_plot2b_title()
                    probe_plot_b = ProbePlot(volume_b, process_4dnexus, title_1d=plot2b_title, title_2d=plot2b_title, use_b=True)
                    plot2b, source2b = probe_plot_b.get_components()
                    
                    # Update Plot2B axis labels if available
                    is_3d_volume_b = len(volume_b.shape) == 3
                    if is_3d_volume_b:
                        # For 1D plots
                        plot2b_probe_x = getattr(process_4dnexus, 'probe_x_coords_picked_b', None)
                        if plot2b_probe_x:
                            plot2b_x_label = plot2b_probe_x.split('/')[-1] if '/' in plot2b_probe_x else plot2b_probe_x
                            plot2b.xaxis.axis_label = plot2b_x_label
                        plot2b_probe_y = getattr(process_4dnexus, 'probe_y_coords_picked_b', None)
                        if plot2b_probe_y:
                            plot2b_y_label = plot2b_probe_y.split('/')[-1] if '/' in plot2b_probe_y else plot2b_probe_y
                            plot2b.yaxis.axis_label = plot2b_y_label
                    else:
                        # For 2D plots
                        plot2b_probe_x = getattr(process_4dnexus, 'probe_x_coords_picked_b', None)
                        plot2b_probe_y = getattr(process_4dnexus, 'probe_y_coords_picked_b', None)
                        if plot2b_probe_x:
                            plot2b_x_label = plot2b_probe_x.split('/')[-1] if '/' in plot2b_probe_x else plot2b_probe_x
                            plot2b.xaxis.axis_label = plot2b_x_label
                        else:
                            plot2b.xaxis.axis_label = "Probe X"
                        if plot2b_probe_y:
                            plot2b_y_label = plot2b_probe_y.split('/')[-1] if '/' in plot2b_probe_y else plot2b_probe_y
                            plot2b.yaxis.axis_label = plot2b_y_label
                        else:
                            plot2b.yaxis.axis_label = "Probe Y"
                    # Set font sizes
                    plot2b.title.text_font_size = FONT_SIZE_PLOT_TITLE
                    plot2b.xaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
                    plot2b.yaxis.axis_label_text_font_size = FONT_SIZE_AXIS_LABEL
                    plot2b.xaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
                    plot2b.yaxis.major_label_text_font_size = FONT_SIZE_AXIS_TICKS
                    
                    # Initialize independent selection rectangle for Plot2B
                    if len(volume_b.shape) == 3:
                        rect2b = Rectangle(0, 0, volume_b.shape[2] - 1, volume_b.shape[2] - 1)
                    else:
                        rect2b = Rectangle(0, 0, volume_b.shape[2] - 1, volume_b.shape[3] - 1)
                else:
                    print("WARNING: volume_dataset_b not available; skipping Plot2B initial build")
            except Exception as e:
                print(f"Failed to build Plot2B: {e}")

        print(f"[TIMING] plot2b built: {time.time()-t0:.3f}s")

        # Color mappers will be created after range variables are defined

        def create_colorbar(color_mapper, title):
            return ColorBar(
                color_mapper=color_mapper,
                title=title,
                title_text_font_size=FONT_SIZE_COLORBAR_TITLE,
                title_text_align="center",
                title_standoff=10,
                major_label_text_font_size=FONT_SIZE_COLORBAR_LABELS,
                major_tick_line_color="black",
                major_tick_line_width=1,
                minor_tick_line_color="black",
                minor_tick_line_width=1,
                bar_line_color="black",
                bar_line_width=1,
                location=(0, 0),
                orientation="horizontal",
            )

        # Image renderers and colorbars will be created after color mappers are defined

        # Create sliders
        x_min = x_coords.min()
        x_max = x_coords.max()
        x_start = min(x_min, x_max)
        x_end = max(x_min, x_max)
        x_value = x_start + (x_end - x_start) / 2
        x_slider = Slider(
            title="X", start=x_start, end=x_end, value=x_value, step=0.01, width=200
        )

        y_min = y_coords.min()
        y_max = y_coords.max()
        y_start = min(y_min, y_max)
        y_end = max(y_min, y_max)
        y_value = y_start + (y_end - y_start) / 2
        y_slider = Slider(
            title="Y", start=y_start, end=y_end, value=y_value, step=0.01, width=200
        )

            # Create color scale selectors
        map1_color_scale_selector = RadioButtonGroup(
            labels=["Linear", "Log"], active=0, width=200
        )
        map2_color_scale_selector = RadioButtonGroup(
            labels=["Linear", "Log"], active=0, width=200
        )
        map3_color_scale_selector = RadioButtonGroup(
            labels=["Linear", "Log"], active=0, width=200
        )

        # Create palette selector
        palette_selector = Select(
            title="Color Palette:", value="Viridis256", options=palettes, width=200
        )

        # Create map shape selector (Square, Custom Dimensions, Aspect Ratio)
        map_shape_selector = RadioButtonGroup(
            labels=["Square", "Custom", "Aspect Ratio"],
            active=0,  # Default to Square
            width=200
        )
        
        # Create custom map size inputs
        custom_map_width_input = TextInput(
            title="Custom Width:",
            value="400",
            width=100
        )
        
        custom_map_height_input = TextInput(
            title="Custom Height:",
            value="400",
            width=100
        )
        
        # Create map scale input for aspect ratio mode (percentage)
        map_scale_input = TextInput(
            title="Map Scale (%):",
            value="100",
            width=100
        )
        
        # Create plot size controls
        plotmin_input = TextInput(
            title="Min Map Size (px):",
            value="200",
            width=150
        )
        
        plotmax_input = TextInput(
            title="Max Map Size (px):",
            value="400", 
            width=150
        )
        
        # Create separate containers for custom map and aspect ratio controls
        # (Created early so they can be used in callbacks and initial state setup)
        custom_map_controls = column(
            Div(text="<b>Custom Map Size:</b>", width=200),
            row(custom_map_width_input, custom_map_height_input),
        )
        
        aspect_ratio_controls = column(
            Div(text="<b>Map Scale:</b>", width=200),
            map_scale_input,
        )
        
        # Create container for Map Size Limits
        map_size_limits_controls = column(
            Div(text="<b>Map Size Limits:</b>", width=200),
            row(plotmin_input, plotmax_input),
        )

        # Helper function to calculate percentile-based ranges
        def get_percentile_range(data):
            """Calculate 1st and 99th percentiles for data range"""
            if data is None or data.size == 0:
                return 0.0, 1.0
            data_flat = data.flatten() if data.ndim > 1 else data
            data_flat = data_flat[~np.isnan(data_flat)]  # Remove NaN values
            if data_flat.size == 0:
                return 0.0, 1.0
            p1 = float(np.percentile(data_flat, 1))
            p99 = float(np.percentile(data_flat, 99))
            return p1, p99
        
        # Create color range controls with percentile-based ranges
        map_min_val, map_max_val = get_percentile_range(preview)
        print(f"Map data range (1st-99th percentile): {map_min_val:.3f} to {map_max_val:.3f}")
        
        range1_min_input = TextInput(
            title="Map Range Min:", value=str(map_min_val), width=120
        )
        range1_max_input = TextInput(
            title="Map Range Max:", value=str(map_max_val), width=120
        )

        print(f"[TIMING] other sliders built: {time.time()-t0:.3f}s")

        # Create range inputs for Plot2 based on volume dimensionality
        if is_3d_volume:
            # For 1D plots, use the initial 1D slice data with percentiles
            if initial_slice_1d is not None:
                p2_min, p2_max = get_percentile_range(initial_slice_1d)
            else:
                p2_min, p2_max = 0.0, 1.0
            range2_min_input = TextInput(
                title="Probe Range Min:", value=str(p2_min), width=120
            )
            range2_max_input = TextInput(
                title="Probe Range Max:", value=str(p2_max), width=120
            )
        else:
            # For 2D plots, use the initial 2D slice data with percentiles
            if initial_slice is not None:
                p2_min, p2_max = get_percentile_range(initial_slice)
            else:
                p2_min, p2_max = 0.0, 1.0
            range2_min_input = TextInput(title="Probe Range Min:", value=str(p2_min), width=120)
            range2_max_input = TextInput(title="Probe Range Max:", value=str(p2_max), width=120)

        print(f"[TIMING] range 2 min/max built: {time.time()-t0:.3f}s")

        # Add toggle for Plot2 range mode (user set vs dynamic)
        plot2_range_mode_toggle = Toggle(label="User Specified", active=False, width=150)
        
        def on_plot2_range_mode_change(attr, old, new):
            """Enable/disable range inputs based on toggle state"""
            if new:  # Dynamic mode enabled
                plot2_range_mode_toggle.label = "Dynamic Range"
                range2_min_input.disabled = True
                range2_max_input.disabled = True
            else:  # User set mode
                plot2_range_mode_toggle.label = "User Specified"
                range2_min_input.disabled = False
                range2_max_input.disabled = False
        
        plot2_range_mode_toggle.on_change("active", on_plot2_range_mode_change)
        
        # If Plot2B exists, add its own range inputs and toggle
        range2b_min_input = None
        range2b_max_input = None
        plot2b_range_mode_toggle = None
        if 'plot2b' in locals() and plot2b is not None and 'source2b' in locals():
            # Create toggle for Plot2B (works for both 1D and 2D)
            plot2b_range_mode_toggle = Toggle(label="User Specified", active=False, width=150)
            
            def on_plot2b_range_mode_change(attr, old, new):
                """Enable/disable range inputs based on toggle state"""
                if new:  # Dynamic mode enabled
                    plot2b_range_mode_toggle.label = "Dynamic Range"
                    if range2b_min_input is not None and range2b_max_input is not None:
                        range2b_min_input.disabled = True
                        range2b_max_input.disabled = True
                else:  # User set mode
                    plot2b_range_mode_toggle.label = "User Specified"
                    if range2b_min_input is not None and range2b_max_input is not None:
                        range2b_min_input.disabled = False
                        range2b_max_input.disabled = False
            
            plot2b_range_mode_toggle.on_change("active", on_plot2b_range_mode_change)
            
            # For 2D plots, also create range inputs
            if isinstance(source2b.data, dict) and 'image' in source2b.data:
                try:
                    img_b = source2b.data["image"][0]
                    p2b_min, p2b_max = get_percentile_range(img_b)
                    range2b_min_input = TextInput(
                        title="Probe2B Range Min:", value=str(p2b_min), width=120
                    )
                    range2b_max_input = TextInput(
                        title="Probe2B Range Max:", value=str(p2b_max), width=120
                    )
                except Exception:
                    pass

        print(f"[TIMING] range 2b min/max built: {time.time()-t0:.3f}s")
        
        # Create range inputs for Plot1B if it exists (2D map)
        range1b_min_input = None
        range1b_max_input = None
        if 'plot1b' in locals() and plot1b is not None and 'source1b' in locals():
            try:
                img1b = source1b.data["image"][0]
                p1b_min, p1b_max = get_percentile_range(img1b)
                range1b_min_input = TextInput(
                    title="Map1B Range Min:", value=str(p1b_min), width=120
                )
                range1b_max_input = TextInput(
                    title="Map1B Range Max:", value=str(p1b_max), width=120
                )
            except Exception:
                pass

        # Create range inputs for Plot3 (summed data)
        # Initialize with zeros since Plot3 starts empty
        range3_min_input = TextInput(
            title="Plot3 Range Min:", value="0", width=120
        )
        range3_max_input = TextInput(
            title="Plot3 Range Max:", value="100", width=120
        )

        # Create color mappers with percentile-based ranges (independent per plot)
        color_mapper1a = LinearColorMapper(
            palette="Viridis256", low=map_min_val, high=map_max_val
        )
        
        # Create color mapper for Plot2 (only for 2D plots)
        if is_3d_volume:
            # For 1D plots, we don't need a color mapper
            color_mapper2a = None
        else:
            # For 2D plots, create color mapper based on initial slice with percentiles
            if initial_slice is not None:
                p2_min, p2_max = get_percentile_range(initial_slice)
            else:
                p2_min, p2_max = 0.0, 1.0
            color_mapper2a = LinearColorMapper(
                palette="Viridis256", low=p2_min, high=p2_max
            )
            
        # Create color mapper for Plot3 (works for both 3D and 4D volumes)
        color_mapper3 = LinearColorMapper(palette="Viridis256", low=1, high=100)

        # Create colorbars
        colorbar1 = create_colorbar(color_mapper1a, "Plot1 Intensity")
        
        # Only create colorbar for Plot2 if it's a 2D plot
        if is_3d_volume:
            colorbar2 = None  # No colorbar for 1D plots
        else:
            colorbar2 = create_colorbar(color_mapper2a, "Plot2 Intensity")
            
        # Create colorbar for Plot3 (works for both 3D and 4D volumes)
        colorbar3 = create_colorbar(color_mapper3, "Plot3 Intensity")

        print(f"[TIMING] colorbars built: {time.time()-t0:.3f}s")

        # Add image renderers
        image_renderer1 = plot1.image(
            "image", source=source1, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper1a,
        )
        
        # Add renderer for Plot2 (either line or image depending on volume dimensionality)
        if is_3d_volume:
            # For 3D volume: create line renderer
            line_renderer2 = plot2.line(
                "x", "y", source=source2, line_width=2, line_color="blue"
            )
            image_renderer2 = None  # No image renderer for 1D plots
            
            # Add range overlay renderer for 3D volumes
            range_overlay_renderer = plot2.vbar(
                x="x", top="height", width="width", source=range_overlay_source,
                fill_color="red", fill_alpha=0.3, line_color="red", line_alpha=0.8
            )
        else:
            # For 4D volume: create image renderer
            image_renderer2 = plot2.image(
                "image", source=source2, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper2a,
            )
            line_renderer2 = None  # No line renderer for 2D plots
            range_overlay_renderer = None  # No range overlay for 2D plots
            
        # If Plot1B exists, add its image renderer using same color mapper as Plot1
        image_renderer1b = None
        color_mapper1b = None
        if 'plot1b' in locals() and plot1b is not None:
            # Initialize Plot1B mapper with its own data range using percentiles
            try:
                img1b = source1b.data["image"][0]
                cm_low, cm_high = get_percentile_range(img1b)
            except Exception:
                cm_low, cm_high = map_min_val, map_max_val
            color_mapper1b = LinearColorMapper(palette=color_mapper1a.palette, low=cm_low, high=cm_high)
            image_renderer1b = plot1b.image(
                "image", source=source1b, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper1b,
            )

        # If Plot2B exists, add appropriate renderer (line for 3D, image for 4D)
        image_renderer2b = None
        line_renderer2b = None
        color_mapper2b = None
        plot2b_is_2d = False
        if 'plot2b' in locals() and plot2b is not None and 'source2b' in locals():
            # Determine Plot2B dimensionality and prepare overlay source only if Plot2B is 3D
            plot2b_is_2d = isinstance(source2b.data, dict) and 'image' in source2b.data
            range_overlay_source_b = ColumnDataSource(data={"x": [], "y": [], "width": [], "height": []}) if not plot2b_is_2d else None
            if plot2b_is_2d:
                # 4D dataset → 2D image
                try:
                    img2b = source2b.data["image"][0]
                    cm2_low, cm2_high = get_percentile_range(img2b)
                except Exception:
                    if not is_3d_volume and initial_slice is not None:
                        cm2_low, cm2_high = get_percentile_range(initial_slice)
                    else:
                        cm2_low, cm2_high = 0.0, 1.0
                color_mapper2b = LinearColorMapper(palette=(color_mapper2a.palette if color_mapper2a is not None else "Viridis256"), low=cm2_low, high=cm2_high)
                image_renderer2b = plot2b.image("image", source=source2b, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper2b)
            else:
                # 3D dataset → 1D line
                line_renderer2b = plot2b.line("x", "y", source=source2b, line_width=2, line_color="green")
                # Add independent range overlay for Plot2B (3D)
                if range_overlay_source_b is not None:
                    range_overlay_renderer_b = plot2b.vbar(
                        x="x", top="height", width="width", source=range_overlay_source_b,
                        fill_color="green", fill_alpha=0.25, line_color="green", line_alpha=0.7
                    )

        # Add renderer for Plot3 (works for both 3D and 4D volumes)
        image_renderer3 = plot3.image(
            "image", source=source3, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper3,
        )
        print(f"[TIMING] renderers added: {time.time()-t0:.3f}s")

        # Create buttons
        reset_ranges_button = Button(
            label="Reset Range Values",
            button_type="primary",
            width=200,
        )
            
        compute_plot3_image_button = Button(label="Show Plot3 from Plot2a ->", button_type="success")
        plot3_status_div_a = Div(text="", width=220)
        compute_plot2_image_button = Button(label="<- Compute Plot2a", button_type="success")
        plot2_status_div = Div(text="", width=220)
        # Buttons and status for Plot2B
        compute_plot2b_image_button = Button(label="<- Compute Plot2b", button_type="success")
        plot2b_status_div = Div(text="", width=220)
        # Plot2B-specific trigger to compute Plot3 using rect2b
        compute_plot3_from_plot2b_button = Button(label="Show Plot3 from Plot2b ->", button_type="success")
        plot3_status_div_b = Div(text="", width=220)
        back_to_selection_button = Button(label="Back to Dataset Selection", button_type="warning", width=200)

        # Prepare reset buttons for Plot2A and Plot2B

        # Reset buttons for Plot2A and Plot2B
        reset_plot2a_button = Button(label="Reset Plot2a", button_type="warning")
        reset_plot2b_button = Button(label="Reset Plot2b", button_type="warning")

        # Create status display with instructions
        if is_3d_volume:
            status_text = f"""
            <h3>3D Data Explorer Dashboard</h3>
            <p><b>Instructions for 3D volumes:</b></p>
            <ul>
                <li><b>Plot1:</b> 2D map view - click to select position</li>
                <li><b>Plot2:</b> 1D probe data - <b>Shift+click</b> to set z_min, <b>Ctrl/Cmd+click</b> or <b>double-click</b> to set z_max</li>
                <li><b>Plot3:</b> Summed data over selected z range - click "Show Plot3 ->" after selecting range</li>
            </ul>
            <p>Ready to explore data...</p>
            """
        else:
            status_text = f"""
            <h3>4D Data Explorer Dashboard</h3>
            <p><b>Instructions for 4D volumes:</b></p>
            <ul>
                <li><b>Plot1:</b> 2D map view - click to select position</li>
                <li><b>Plot2:</b> 2D probe data - <b>Shift+click</b> to set min corner, <b>Ctrl+click</b> to set max corner</li>
                <li><b>Plot3:</b> Summed data over selected region - click "Show Plot3 ->" after selecting region</li>
            </ul>
            <p>Ready to explore data...</p>
            """
        
        status_div = Div(
            text=status_text,
            width=800,
        )
        
        # Create z-range display for 3D volumes
        if is_3d_volume:
            z_range_display = Div(
                text="<b>Z Range Selection:</b><br>z_min: 0, z_max: 0<br><small>Shift+click in Plot2 to set z_min, Ctrl/Cmd+click or double-click to set z_max</small>",
                width=300,
                styles={'background-color': '#f0f0f0', 'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px'}
            )
        else:
            z_range_display = None

            # Configure plots
        plot1.match_aspect = True
        plot1.sizing_mode = "fixed"
        plot1.add_layout(colorbar1, "below")
        # Add a colorbar for Plot1B if present (shares title but independent range)
        if image_renderer1b is not None:
            colorbar1b = create_colorbar(color_mapper1b, "Plot1B Intensity")
            plot1b.match_aspect = True
            plot1b.sizing_mode = "fixed"
            plot1b.add_layout(colorbar1b, "below")
        # Only set match_aspect for 2D plots (not for 1D line plots)
        if not is_3d_volume:
            plot2.match_aspect = True  # 1:1 aspect ratio for 2D plots
        plot2.sizing_mode = "scale_width"  # Allow width scaling to match column
        
        # Only add colorbar to Plot2 if it's a 2D plot
        if not is_3d_volume and colorbar2 is not None:
            plot2.add_layout(colorbar2, "below")
            if image_renderer2b is not None and plot2b_is_2d:
                colorbar2b = create_colorbar(color_mapper2b, "Plot2B Intensity")
                plot2b.match_aspect = True
                plot2b.sizing_mode = "scale_width"  # Match Plot2A sizing
                plot2b.add_layout(colorbar2b, "below")
        
        # Set Plot2B sizing_mode for 1D plots (3D volumes) as well
        if 'plot2b' in locals() and plot2b is not None and not plot2b_is_2d:
            plot2b.sizing_mode = "scale_width"  # Match Plot2A sizing
            
        # Configure Plot3 (works for both 3D and 4D volumes)
        plot3.match_aspect = True
        plot3.sizing_mode = "fixed"
        plot3.add_layout(colorbar3, "below")

        # Add callback functions
        def get_x_index(x_coord=None):
            if x_coord is None:
                x_coord = x_slider.value
            return np.argmin(np.abs(x_coords - x_coord))
        
        def get_y_index(y_coord=None):
            if y_coord is None:
                y_coord = y_slider.value
            return np.argmin(np.abs(y_coords - y_coord))
        
        def clear_rect(p, r):
            """Clear existing rectangle lines from the plot"""
            if hasattr(r, 'h1line') and r.h1line is not None:
                try:
                    p.renderers.remove(r.h1line)
                except ValueError:
                    pass  # Line not in renderers list
            if hasattr(r, 'h2line') and r.h2line is not None:
                try:
                    p.renderers.remove(r.h2line)
                except ValueError:
                    pass  # Line not in renderers list
            if hasattr(r, 'v1line') and r.v1line is not None:
                try:
                    p.renderers.remove(r.v1line)
                except ValueError:
                    pass  # Line not in renderers list
            if hasattr(r, 'v2line') and r.v2line is not None:
                try:
                    p.renderers.remove(r.v2line)
                except ValueError:
                    pass  # Line not in renderers list
        
        def draw_rect(p, r, x1, x2, y1, y2, line_color="yellow", line_width=2):
            # Clear existing rectangle first
            clear_rect(p, r)
            
            # Draw new rectangle
            r.h1line = p.line(
                x=[x1, x2], y=[y1, y1], line_color=line_color, line_width=line_width
            )
            r.h2line = p.line(
                x=[x1, x2], y=[y2, y2], line_color=line_color, line_width=line_width
            )
            r.v1line = p.line(
                x=[x1, x1], y=[y1, y2], line_color=line_color, line_width=line_width
            )
            r.v2line = p.line(
                x=[x2, x2], y=[y1, y2], line_color=line_color, line_width=line_width
            )
        
        def draw_cross1():
            x_index = get_x_index()
            x_coord = x_coords[x_index]
            y_index = get_y_index()
            y_coord = y_coords[y_index]

            # Initialize crosshair lines for Plot1 if they don't exist
            if rect1.h1line is None:
                rect1.h1line = plot1.line(x=[x_coords.min(), x_coords.max()], y=[y_coord, y_coord], line_color="yellow", line_width=2)
            if rect1.h2line is None:
                rect1.h2line = plot1.line(x=[x_coords.min(), x_coords.max()], y=[y_coord, y_coord], line_color="yellow", line_width=2)
            if rect1.v1line is None:
                rect1.v1line = plot1.line(x=[x_coord, x_coord], y=[y_coords.min(), y_coords.max()], line_color="yellow", line_width=2)
            if rect1.v2line is None:
                rect1.v2line = plot1.line(x=[x_coord, x_coord], y=[y_coords.min(), y_coords.max()], line_color="yellow", line_width=2)

            rect1.h1line.data_source.data = {
                "x": [x_coords.min(), x_coords.max()],
                "y": [y_coord, y_coord],
            }
            rect1.h2line.data_source.data = {
                "x": [x_coords.min(), x_coords.max()],
                "y": [y_coord, y_coord],
            }
            rect1.v1line.data_source.data = {
                "x": [x_coord, x_coord],
                "y": [y_coords.min(), y_coords.max()],
            }
            rect1.v2line.data_source.data = {
                "x": [x_coord, x_coord],
                "y": [y_coords.min(), y_coords.max()],
            }
            
            # Also update Plot1B crosshairs if it exists
            if rect1b is not None and 'plot1b' in locals() and plot1b is not None:
                draw_cross1b()
        
        def draw_cross1b():
            """Draw crosshairs on Plot1B using the same coordinates as Plot1"""
            if rect1b is None or 'plot1b' not in locals() or plot1b is None:
                return
            x_index = get_x_index()
            x_coord = x_coords[x_index]
            y_index = get_y_index()
            y_coord = y_coords[y_index]

            # Initialize crosshair lines if they don't exist
            if rect1b.h1line is None:
                rect1b.h1line = plot1b.line(x=[x_coords.min(), x_coords.max()], y=[y_coord, y_coord], line_color="yellow", line_width=2)
            if rect1b.h2line is None:
                rect1b.h2line = plot1b.line(x=[x_coords.min(), x_coords.max()], y=[y_coord, y_coord], line_color="yellow", line_width=2)
            if rect1b.v1line is None:
                rect1b.v1line = plot1b.line(x=[x_coord, x_coord], y=[y_coords.min(), y_coords.max()], line_color="yellow", line_width=2)
            if rect1b.v2line is None:
                rect1b.v2line = plot1b.line(x=[x_coord, x_coord], y=[y_coords.min(), y_coords.max()], line_color="yellow", line_width=2)
            
            # Update crosshair positions
            rect1b.h1line.data_source.data = {
                "x": [x_coords.min(), x_coords.max()],
                "y": [y_coord, y_coord],
            }
            rect1b.h2line.data_source.data = {
                "x": [x_coords.min(), x_coords.max()],
                "y": [y_coord, y_coord],
            }
            rect1b.v1line.data_source.data = {
                "x": [x_coord, x_coord],
                "y": [y_coords.min(), y_coords.max()],
            }
            rect1b.v2line.data_source.data = {
                "x": [x_coord, x_coord],
                "y": [y_coords.min(), y_coords.max()],
            }
        
        def set_colormap_range(plot, colorbar, color_mapper, min_val, max_val):
            color_mapper.low = min_val
            color_mapper.high = max_val
            if hasattr(plot, 'renderers') and len(plot.renderers) > 0:
                # Only update color_mapper if the renderer is an image renderer (has color_mapper attribute)
                # Line renderers don't have color_mapper
                renderer = plot.renderers[0]
                if hasattr(renderer, 'glyph') and hasattr(renderer.glyph, 'color_mapper'):
                    renderer.glyph.color_mapper = color_mapper
        
        def update_plot1_dimensions():
            """Update plot1 dimensions based on map shape selector"""
            try:
                # Get plotmin and plotmax values
                plotmin = int(plotmin_input.value) if plotmin_input.value.isdigit() else 200
                plotmax = int(plotmax_input.value) if plotmax_input.value.isdigit() else 400
                
                # Check which mode is selected
                if map_shape_selector.active == 0:  # Square mode
                    # Force square dimensions - use plotmax for both width and height
                    map_width = plotmax
                    map_height = plotmax
                    
                    # Ensure both dimensions are at least plotmin
                    if map_width < plotmin or map_height < plotmin:
                        map_width = plotmin
                        map_height = plotmin
                    
                    print(f"Square map dimensions: {map_width}x{map_height}")
                    
                elif map_shape_selector.active == 1:  # Custom Dimensions mode
                    # Get custom dimensions from inputs
                    try:
                        width_val = custom_map_width_input.value if custom_map_width_input else "400"
                        height_val = custom_map_height_input.value if custom_map_height_input else "400"
                        
                        map_width = int(width_val) if width_val else 400
                        map_height = int(height_val) if height_val else 400
                    except (ValueError, AttributeError) as e:
                        print(f"Error parsing custom dimensions: {e}")
                        map_width = 400
                        map_height = 400
                    
                    # Ensure both dimensions are at least plotmin
                    if map_width < plotmin or map_height < plotmin:
                        scale_factor = max(plotmin / map_width, plotmin / map_height)
                        map_width = int(map_width * scale_factor)
                        map_height = int(map_height * scale_factor)
                    
                    print(f"Custom map dimensions: {map_width}x{map_height}")
                    
                elif map_shape_selector.active == 2:  # Aspect Ratio mode
                    # Get scale from map scale input (convert percentage to decimal)
                    try:
                        scale_percentage = float(map_scale_input.value) if map_scale_input.value else 100.0
                        map_scale = scale_percentage / 100.0  # Convert percentage to decimal
                    except (ValueError, AttributeError):
                        map_scale = 1.0
                    
                    # Calculate aspect ratio from actual data dimensions
                    aspect_ratio = (y_coords.max() - y_coords.min()) / (x_coords.max() - x_coords.min())
                    
                    base_size = plotmax * map_scale
                    
                    if aspect_ratio > 1:  # Taller than wide
                        map_height = int(base_size)
                        map_width = int(base_size / aspect_ratio)
                    else:  # Wider than tall or square
                        map_width = int(base_size)
                        map_height = int(base_size * aspect_ratio)
                    
                    # Ensure both dimensions are at least plotmin, but respect the scale
                    min_size = int(plotmin * map_scale)  # Scale the minimum size too
                    if map_width < min_size or map_height < min_size:
                        scale_factor = max(min_size / map_width, min_size / map_height)
                        map_width = int(map_width * scale_factor)
                        map_height = int(map_height * scale_factor)
                    
                    print(f"Map scale: {scale_percentage:.0f}%, aspect ratio: {aspect_ratio:.2f}, size: {map_width}x{map_height}")
                else:
                    # Fallback mode - use square size (default)
                    map_width = plotmax
                    map_height = plotmax
                
                # Update plot1 dimensions
                plot1.width = map_width
                plot1.height = map_height
                
                # Also update Plot1B if it exists
                if 'plot1b' in locals() and plot1b is not None:
                    plot1b.width = map_width
                    plot1b.height = map_height
                
                # Also update Plot3 to match Plot1 dimensions
                if 'plot3' in locals() and plot3 is not None:
                    plot3.width = map_width
                    plot3.height = map_height
                    print(f"Plot3 dimensions updated to match Plot1: {map_width}x{map_height}")
                    
            except Exception as e:
                print(f"Error updating plot1 dimensions: {e}")
        
        def on_map_shape_change(attr, old, new):
            """Handle map shape selector change (Square, Custom Dimensions, Aspect Ratio)"""
            try:
                shape_modes = ["Square", "Custom", "Aspect Ratio"]
                shape_mode = shape_modes[new] if new < len(shape_modes) else "Unknown"
                print(f"Map shape changed to: {shape_mode}")
                
                # Hide/show control containers based on map shape choice
                if new == 0:  # Square
                    # Hide both custom map and aspect ratio controls
                    custom_map_controls.visible = False
                    aspect_ratio_controls.visible = False
                    # Disable all inputs
                    custom_map_width_input.disabled = True
                    custom_map_height_input.disabled = True
                    map_scale_input.disabled = True
                    # Show Map Size Limits (needed for Square mode)
                    map_size_limits_controls.visible = True
                    plotmin_input.disabled = False
                    plotmax_input.disabled = False
                elif new == 1:  # Custom Dimensions
                    # Show custom map controls, hide aspect ratio controls
                    custom_map_controls.visible = True
                    aspect_ratio_controls.visible = False
                    # Enable custom map inputs, disable scale input
                    custom_map_width_input.disabled = False
                    custom_map_height_input.disabled = False
                    map_scale_input.disabled = True
                    # Hide Map Size Limits (not needed in Custom mode - user sets exact dimensions)
                    map_size_limits_controls.visible = False
                    plotmin_input.disabled = True
                    plotmax_input.disabled = True
                else:  # Aspect Ratio (new == 2)
                    # Hide custom map controls, show aspect ratio controls
                    custom_map_controls.visible = False
                    aspect_ratio_controls.visible = True
                    # Disable custom map inputs, enable scale input
                    custom_map_width_input.disabled = True
                    custom_map_height_input.disabled = True
                    map_scale_input.disabled = False
                    # Show Map Size Limits (needed for Aspect Ratio mode)
                    map_size_limits_controls.visible = True
                    plotmin_input.disabled = False
                    plotmax_input.disabled = False
                
                # Update plot dimensions
                update_plot1_dimensions()
                
            except Exception as e:
                print(f"Error changing map shape: {e}")
        
        def on_custom_map_width_change(attr, old, new):
            """Handle custom map width input change"""
            if map_shape_selector.active == 1:  # Custom Dimensions mode
                update_plot1_dimensions()
        
        def on_custom_map_height_change(attr, old, new):
            """Handle custom map height input change"""
            if map_shape_selector.active == 1:  # Custom Dimensions mode
                update_plot1_dimensions()
        
        def on_map_scale_change(attr, old, new):
            """Handle map scale input change"""
            if map_shape_selector.active == 2:  # Aspect Ratio mode
                update_plot1_dimensions()
        
        def on_plot_size_change(attr, old, new):
            """Handle plotmin/plotmax input change"""
            update_plot1_dimensions()
        
        def update_plot2_range_dynamic():
            """Update Plot2 range dynamically based on current data"""
            if not plot2_range_mode_toggle.active:
                return
            
            try:
                if is_3d_volume:
                    # For 1D plots, update y_range based on current data
                    if 'y' in source2.data and len(source2.data['y']) > 0:
                        data = np.array(source2.data['y'])
                        p2_min, p2_max = get_percentile_range(data)
                        plot2.y_range.start = float(p2_min)
                        plot2.y_range.end = float(p2_max)
                        # Also update range inputs to reflect current range
                        range2_min_input.value = str(p2_min)
                        range2_max_input.value = str(p2_max)
                else:
                    # For 2D plots, update color mapper range
                    if 'image' in source2.data and len(source2.data['image']) > 0:
                        img = source2.data['image'][0]
                        p2_min, p2_max = get_percentile_range(img)
                        # Only update color mapper if it exists (2D plots only)
                        if 'color_mapper2a' in locals() and color_mapper2a is not None:
                            set_colormap_range(plot2, colorbar2, color_mapper2a, p2_min, p2_max)
                        # Also update range inputs to reflect current range
                        range2_min_input.value = str(p2_min)
                        range2_max_input.value = str(p2_max)
            except Exception as e:
                print(f"Error updating Plot2 dynamic range: {e}")
                import traceback
                traceback.print_exc()
        
        def update_plot2b_range_dynamic():
            """Update Plot2B range dynamically based on current data"""
            nonlocal colorbar2b
            if plot2b_range_mode_toggle is None or not plot2b_range_mode_toggle.active:
                return
            if 'plot2b' not in locals() or plot2b is None or 'source2b' not in locals():
                return
            
            try:
                plot2b_is_2d_local = 'plot2b_is_2d' in locals() and plot2b_is_2d
                if not plot2b_is_2d_local:
                    # For 1D plots, update y_range based on current data
                    if 'y' in source2b.data and len(source2b.data['y']) > 0:
                        data = np.array(source2b.data['y'])
                        p2b_min, p2b_max = get_percentile_range(data)
                        plot2b.y_range.start = float(p2b_min)
                        plot2b.y_range.end = float(p2b_max)
                        # Also update range inputs to reflect current range
                        if range2b_min_input is not None:
                            range2b_min_input.value = str(p2b_min)
                        if range2b_max_input is not None:
                            range2b_max_input.value = str(p2b_max)
                else:
                    # For 2D plots, update color mapper range
                    if 'image' in source2b.data and len(source2b.data['image']) > 0:
                        img = source2b.data['image'][0]
                        p2b_min, p2b_max = get_percentile_range(img)
                        if 'color_mapper2b' in locals() and color_mapper2b is not None:
                            if 'colorbar2b' in locals() and colorbar2b is not None:
                                set_colormap_range(plot2b, colorbar2b, color_mapper2b, p2b_min, p2b_max)
                            else:
                                # Update mapper without colorbar if colorbar doesn't exist
                                color_mapper2b.low = p2b_min
                                color_mapper2b.high = p2b_max
                                if len(plot2b.renderers) > 0:
                                    plot2b.renderers[0].glyph.color_mapper = color_mapper2b
                        # Also update range inputs to reflect current range
                        if range2b_min_input is not None:
                            range2b_min_input.value = str(p2b_min)
                        if range2b_max_input is not None:
                            range2b_max_input.value = str(p2b_max)
            except Exception as e:
                print(f"Error updating Plot2B dynamic range: {e}")
                import traceback
                traceback.print_exc()
        
        def show_slice():
            x_index = get_x_index()
            y_index = get_y_index()
            
            # Update Plot2 with new slice
            if is_3d_volume:
                # For 3D volume: update 1D line plot
                update_1d_plot(volume, x_index, y_index, source2, plot2, process_4dnexus)
            else:
                # For 4D volume: update 2D image plot
                # Store original axis labels to preserve them
                original_x_label_2 = plot2.xaxis.axis_label if hasattr(plot2.xaxis, 'axis_label') else None
                original_y_label_2 = plot2.yaxis.axis_label if hasattr(plot2.yaxis, 'axis_label') else None
                
                new_slice = volume[x_index, y_index, :, :]
                source2.data = {
                    "image": [new_slice],
                    "x": [0],
                    "y": [0],
                    "dw": [volume.shape[2]],
                    "dh": [volume.shape[3]],
                }
                
                # Restore axis labels if they were set
                if original_x_label_2:
                    plot2.xaxis.axis_label = original_x_label_2
                if original_y_label_2:
                    plot2.yaxis.axis_label = original_y_label_2
            
            # Update crosshairs (this will also update Plot1B crosshairs)
            draw_cross1()
            
            # Update range dynamically if enabled
            update_plot2_range_dynamic()
        
        def show_slice_b():
            """Update Plot2B based on Plot1B crosshair position"""
            if 'plot2b' not in locals() or plot2b is None:
                return
            # Get volume_b from process_4dnexus
            volume_b_local = getattr(process_4dnexus, 'volume_dataset_b', None)
            if volume_b_local is None:
                return
            x_index = get_x_index()
            y_index = get_y_index()
            
            # Update Plot2B with new slice
            if len(volume_b_local.shape) == 3:
                # For 3D volume: update 1D line plot - use use_b=True to get Plot2B coordinates
                update_1d_plot(volume_b_local, x_index, y_index, source2b, plot2b, process_4dnexus, use_b=True)
            else:
                # For 4D volume: update 2D image plot
                # Store original axis labels to preserve them
                original_x_label_b = plot2b.xaxis.axis_label if hasattr(plot2b.xaxis, 'axis_label') else None
                original_y_label_b = plot2b.yaxis.axis_label if hasattr(plot2b.yaxis, 'axis_label') else None
                
                new_slice_b = volume_b_local[x_index, y_index, :, :]
                source2b.data = {
                    "image": [new_slice_b],
                    "x": [0],
                    "y": [0],
                    "dw": [volume_b_local.shape[2]],
                    "dh": [volume_b_local.shape[3]],
                }
                
                # Restore axis labels if they were set
                if original_x_label_b:
                    plot2b.xaxis.axis_label = original_x_label_b
                if original_y_label_b:
                    plot2b.yaxis.axis_label = original_y_label_b
            
            # Update range dynamically if enabled
            update_plot2b_range_dynamic()
        
        def on_plot1_tap(event):
            x_index = get_x_index(event.x)
            y_index = get_y_index(event.y)
            
            if event.modifiers.get("shift", False):
                rect1.set(min_x=x_index, min_y=y_index)
                print(f"on_plot1_tap rect1={rect1} (shift pressed)")
                schedule_show_slice()
            elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta',False) or event.modifiers.get('cmd',False):
                rect1.set(max_x=x_index, max_y=y_index)
                print(f"on_plot1_tap rect1={rect1} (ctrl pressed)")
                schedule_show_slice()
            elif event.modifiers.get("alt", False):
                rect1.set(
                    min_x=0, max_x=volume.shape[0] - 1, min_y=0, max_y=volume.shape[1] - 1
                )
                print(f"on_plot1_tap rect1={rect1} (alt pressed)")
                schedule_show_slice()
            else:
                # Clear existing rectangle and set new position
                clear_rect(plot1, rect1)
                rect1.set(min_x=x_index, min_y=y_index, max_x=x_index, max_y=y_index)
                draw_rect(plot1, rect1, x_index, x_index, y_index, y_index)
                
                x_slider.value = x_coords[x_index]
                y_slider.value = y_coords[y_index]
                print(f"on_plot1_tap x_index={x_index}/{x_slider.value} y_index={y_index}/{y_slider.value}")
                # This will trigger draw_cross1() which also updates Plot1B crosshairs
        
        def on_plot1b_tap(event):
            """Handle clicks on Plot1B - update crosshairs and Plot2B"""
            if rect1b is None or 'plot1b' not in locals() or plot1b is None:
                return
            x_index = get_x_index(event.x)
            y_index = get_y_index(event.y)
            
            # Update sliders (which will update both Plot1 and Plot1B crosshairs)
            x_slider.value = x_coords[x_index]
            y_slider.value = y_coords[y_index]
            
            # Update Plot2B
            if 'plot2b' in locals() and plot2b is not None:
                show_slice_b()
            
            print(f"on_plot1b_tap x_index={x_index}/{x_slider.value} y_index={y_index}/{y_slider.value}")
        
        def on_plot2_tap(event):
            if is_3d_volume:
                # For 3D volumes: Plot2 is a 1D line plot, only use x-coordinate
                # Convert from plot coordinates to data indices
                if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                    try:
                        probe_coords = process_4dnexus.load_probe_coordinates()
                        if probe_coords is not None:
                            # Find the closest probe coordinate index
                            z_index = np.argmin(np.abs(probe_coords - event.x))
                            print(f"on_plot2_tap: plot_x={event.x:.3f}, closest probe_coord={probe_coords[z_index]:.3f}, z_index={z_index}")
                        else:
                            z_index = int(event.x)
                            print(f"on_plot2_tap: no probe coords, using plot_x={event.x:.3f}, z_index={z_index}")
                    except:
                        z_index = int(event.x)
                        print(f"on_plot2_tap: failed to load probe coords, using plot_x={event.x:.3f}, z_index={z_index}")
                else:
                    z_index = int(event.x)
                    print(f"on_plot2_tap: no probe coords specified, using plot_x={event.x:.3f}, z_index={z_index}")
                
                print(f"DEBUG: Event modifiers: {event.modifiers}")
                print(f"DEBUG: ctrl={event.modifiers.get('ctrl', False)}, meta={event.modifiers.get('meta', False)}, cmd={event.modifiers.get('cmd', False)}")
                print(f"DEBUG: shift={event.modifiers.get('shift', False)}")
                
                # Check for Ctrl/Cmd/Meta keys (try different approaches)
                has_ctrl = (event.modifiers.get("ctrl", False) or 
                           event.modifiers.get('meta', False) or 
                           event.modifiers.get('cmd', False) or
                           'ctrl' in str(event.modifiers).lower() or
                           'meta' in str(event.modifiers).lower() or
                           'cmd' in str(event.modifiers).lower())
                
                if event.modifiers.get("shift", False):
                    # Shift+click: Set min value only
                    rect2.set(min_x=z_index, min_y=z_index)  # Use z_index for both min_x and min_y
                    print(f"on_plot2_tap rect2={rect2} (shift pressed) - 3D volume, z_index={z_index}")
                    draw_rect2()
                    update_z_range_display()
                    update_range_overlay()
                elif has_ctrl:
                    # Ctrl/Cmd+click: Set max value only
                    print(f"DEBUG: Ctrl/Cmd+click detected, setting max_x={z_index}")
                    print(f"DEBUG: Before rect2.set, rect2.min_x={rect2.min_x}, rect2.max_x={rect2.max_x}")
                    rect2.set(max_x=z_index, max_y=z_index)  # Use z_index for both max_x and max_y
                    print(f"DEBUG: After rect2.set, rect2.min_x={rect2.min_x}, rect2.max_x={rect2.max_x}")
                    print(f"on_plot2_tap rect2={rect2} (ctrl/cmd pressed) - 3D volume, z_index={z_index}")
                    draw_rect2()
                    update_z_range_display()
                    update_range_overlay()
                else:
                    # Regular click: Clear any old rect lines and update overlay only
                    clear_rect(plot2, rect2)
                    rect2.set(min_x=z_index, min_y=z_index, max_x=z_index, max_y=z_index)
                    print(f"on_plot2_tap z_index={z_index} - 3D volume")
                    update_z_range_display()
                    update_range_overlay()
            else:
                # For 4D volumes: Plot2 is a 2D image plot, use both x and y coordinates
                print(f"DEBUG: 4D volume tap - x={event.x}, y={event.y}")
                print(f"DEBUG: Event modifiers: {event.modifiers}")
                print(f"DEBUG: shift={event.modifiers.get('shift', False)}, ctrl={event.modifiers.get('ctrl', False)}")
                
                if event.modifiers.get("shift", False):
                    # Shift+click: Set min values only
                    print(f"DEBUG: Shift+click detected for 4D volume, setting min_x={int(event.x)}, min_y={int(event.y)}")
                    rect2.set(min_x=int(event.x), min_y=int(event.y))
                    print(f"on_plot2_tap rect2={rect2} (shift pressed) - 4D volume")
                    draw_rect2()
                elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta',False) or event.modifiers.get('cmd',False):
                    # Ctrl/Cmd+click: Set max values only
                    print(f"DEBUG: Ctrl/Cmd+click detected for 4D volume, setting max_x={int(event.x)}, max_y={int(event.y)}")
                    rect2.set(max_x=int(event.x), max_y=int(event.y))
                    print(f"on_plot2_tap rect2={rect2} (ctrl/cmd pressed) - 4D volume")
                    draw_rect2()
                else:
                    # Regular click: Clear and set both min and max to same value
                    print(f"DEBUG: Regular click detected for 4D volume, clearing and setting both min/max")
                    clear_rect(plot2, rect2)
                    rect2.set(min_x=int(event.x), min_y=int(event.y), max_x=int(event.x), max_y=int(event.y))
                    draw_rect(plot2, rect2, int(event.x), int(event.x), int(event.y), int(event.y))
                    print(f"on_plot2_tap x={event.x} y={event.y} - 4D volume")
        
        # Explicit Plot2A wrappers for clarity and independent wiring
        def on_plot2a_tap(event):
            return on_plot2_tap(event)
        
        def _parse_float_safe(value_str):
            if value_str is None:
                return None
            try:
                cleaned = re.sub(r"[^0-9eE+\-.]", "", str(value_str))
                if cleaned == '' or cleaned in ['-', '+', '.', 'e', 'E']:
                    return None
                return float(cleaned)
            except Exception:
                return None

        def on_range1_input_change():
            min_val = _parse_float_safe(range1_min_input.value)
            max_val = _parse_float_safe(range1_max_input.value)
            if min_val is None or max_val is None:
                return
            if min_val >= max_val:
                return
            set_colormap_range(plot1, colorbar1, color_mapper1a, min_val, max_val)
        
        def on_range1b_input_change():
            """Handle Plot1B range input changes"""
            if 'range1b_min_input' not in locals() or range1b_min_input is None:
                return
            if 'plot1b' not in locals() or plot1b is None or 'color_mapper1b' not in locals() or color_mapper1b is None:
                return
            min_val = _parse_float_safe(range1b_min_input.value)
            max_val = _parse_float_safe(range1b_max_input.value)
            if min_val is None or max_val is None:
                return
            if min_val >= max_val:
                return
            # Update Plot1B mapper range
            try:
                color_mapper1b.low = min_val
                color_mapper1b.high = max_val
                # Keep renderer in sync
                if len(plot1b.renderers) > 0:
                    plot1b.renderers[0].glyph.color_mapper = color_mapper1b
                # Update colorbar if created
                if 'colorbar1b' in locals() and colorbar1b is not None:
                    colorbar1b.color_mapper = color_mapper1b
            except Exception:
                pass
        
        def on_range2_input_change():
            min_val = _parse_float_safe(range2_min_input.value)
            max_val = _parse_float_safe(range2_max_input.value)
            if min_val is None or max_val is None:
                return
            if min_val >= max_val:
                return
            set_colormap_range(plot2, colorbar2, color_mapper2a, min_val, max_val)
        
        def on_range2b_input_change():
            # Only apply if Plot2B exists and is a 2D image plot
            if 'range2b_min_input' not in locals() or range2b_min_input is None:
                return
            if 'image_renderer2b' not in locals() or image_renderer2b is None:
                return
            if 'color_mapper2b' not in locals() or color_mapper2b is None:
                return
            min_val = _parse_float_safe(range2b_min_input.value)
            max_val = _parse_float_safe(range2b_max_input.value)
            if min_val is None or max_val is None:
                return
            if min_val >= max_val:
                return
            # Update Plot2B mapper range
            try:
                color_mapper2b.low = min_val
                color_mapper2b.high = max_val
                # Keep renderer in sync
                plot2b.renderers[0].glyph.color_mapper = color_mapper2b
                # Update colorbar if created
                if 'colorbar2b' in locals() and colorbar2b is not None:
                    colorbar2b.color_mapper = color_mapper2b
            except Exception:
                pass

        def on_range3_input_change():
            min_val = _parse_float_safe(range3_min_input.value)
            max_val = _parse_float_safe(range3_max_input.value)
            if min_val is None or max_val is None:
                return
            if min_val >= max_val:
                return
            set_colormap_range(plot3, colorbar3, color_mapper3, min_val, max_val)
        
        def on_map1_color_scale_change(attr, old, new):
            """Handle Map color scale change (Linear vs Log) for Plot1 and Plot1B"""
            nonlocal color_mapper1a, color_mapper1b, image_renderer1, image_renderer1b
            try:
                # Get current data from source1
                if 'image' not in source1.data or len(source1.data['image']) == 0:
                    print("Warning: No image data in source1 for color scale change")
                    return
                
                current_data = np.array(source1.data["image"][0])
                if current_data.size == 0:
                    print("Warning: Empty image data for color scale change")
                    return
                
                # For log scale, we need to handle zeros/negatives
                if new == 1:  # Log scale selected
                    # Filter out zeros and negatives, use a small epsilon for minimum
                    positive_data = current_data[current_data > 0]
                    if positive_data.size == 0:
                        print("Warning: No positive values for log scale, using linear scale")
                        new_cls = LinearColorMapper
                        # Use current ranges or defaults
                        low1a = color_mapper1a.low if color_mapper1a.low > 0 else 0.001
                        high1a = color_mapper1a.high if color_mapper1a.high > 0 else 1.0
                    else:
                        new_cls = LogColorMapper
                        # Use current ranges if they're positive, otherwise use data-based ranges
                        low1a = color_mapper1a.low if color_mapper1a.low > 0 else max(np.min(positive_data), 0.001)
                        high1a = color_mapper1a.high if color_mapper1a.high > 0 else np.max(positive_data)
                else:  # Linear scale
                    new_cls = LinearColorMapper
                # Preserve current ranges
                    low1a = color_mapper1a.low
                    high1a = color_mapper1a.high
                
                # Recreate mapper for Plot1
                color_mapper1a = new_cls(palette=color_mapper1a.palette, low=low1a, high=high1a)
                if len(plot1.renderers) > 0 and image_renderer1 is not None:
                    # Remove the old renderer
                    plot1.renderers.remove(plot1.renderers[0])
                    # Re-add the renderer with the new color mapper
                    image_renderer1 = plot1.image(
                        "image", source=source1, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper1a,
                    )
                # Update colorbar if it exists
                if 'colorbar1' in locals() and colorbar1 is not None:
                    colorbar1.color_mapper = color_mapper1a
                
                # Update Plot1B if it exists
                if 'plot1b' in locals() and plot1b is not None and image_renderer1b is not None and 'color_mapper1b' in locals() and color_mapper1b is not None:
                    if new == 1:  # Log scale
                        low1b = color_mapper1b.low if color_mapper1b.low > 0 else max(np.min(positive_data), 0.001)
                        high1b = color_mapper1b.high if color_mapper1b.high > 0 else np.max(positive_data)
                    else:  # Linear scale
                        low1b = color_mapper1b.low
                        high1b = color_mapper1b.high
                    color_mapper1b = new_cls(palette=color_mapper1a.palette, low=low1b, high=high1b)
                    if len(plot1b.renderers) > 0 and image_renderer1b is not None:
                        # Remove the old renderer
                        plot1b.renderers.remove(plot1b.renderers[0])
                        # Re-add the renderer with the new color mapper
                        image_renderer1b = plot1b.image(
                            "image", source=source1b, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper1b,
                        )
                    # Update colorbar if it exists
                    if 'colorbar1b' in locals() and colorbar1b is not None:
                        colorbar1b.color_mapper = color_mapper1b
                        
            except Exception as e:
                print(f"Error in on_map1_color_scale_change: {e}")
                import traceback
                traceback.print_exc()
        
        def on_map2_color_scale_change(attr, old, new):
            """Handle Probe color scale change (Linear vs Log) for Plot2 and Plot2B"""
            nonlocal color_mapper2a, color_mapper2b, colorbar2, colorbar2b, image_renderer2, image_renderer2b
            try:
                new_cls = LogColorMapper if new == 1 else LinearColorMapper
                
                # Handle Plot2 (2D plots only - 4D volumes)
                if not is_3d_volume and color_mapper2a is not None:
                    # Get current data from source2
                    if 'image' in source2.data and len(source2.data['image']) > 0:
                        current_data = np.array(source2.data["image"][0])
                        
                        if new == 1:  # Log scale
                            # Filter out zeros and negatives
                            positive_data = current_data[current_data > 0]
                            if positive_data.size == 0:
                                print("Warning: No positive values for log scale in Plot2, using linear scale")
                                new_cls = LinearColorMapper
                                low2a = color_mapper2a.low if color_mapper2a.low > 0 else 0.001
                                high2a = color_mapper2a.high if color_mapper2a.high > 0 else 1.0
                            else:
                                # Use current ranges if positive, otherwise use data-based ranges
                                low2a = color_mapper2a.low if color_mapper2a.low > 0 else max(np.min(positive_data), 0.001)
                                high2a = color_mapper2a.high if color_mapper2a.high > 0 else np.max(positive_data)
                        else:  # Linear scale
                            low2a = color_mapper2a.low
                            high2a = color_mapper2a.high
                    else:
                        # No image data, use current ranges
                        low2a = color_mapper2a.low
                        high2a = color_mapper2a.high
                    
                    color_mapper2a = new_cls(palette=color_mapper2a.palette, low=low2a, high=high2a)
                    if len(plot2.renderers) > 0 and image_renderer2 is not None:
                        # Remove the old renderer
                        plot2.renderers.remove(plot2.renderers[0])
                        # Re-add the renderer with the new color mapper
                        image_renderer2 = plot2.image(
                            "image", source=source2, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper2a,
                        )
                    # Update colorbar if it exists
                    if colorbar2 is not None:
                        colorbar2.color_mapper = color_mapper2a
                
                # Handle Plot2B (2D plots only)
                if 'plot2b' in locals() and plot2b is not None and plot2b_is_2d and image_renderer2b is not None and 'color_mapper2b' in locals() and color_mapper2b is not None:
                    # Get current data from source2b
                    if 'image' in source2b.data and len(source2b.data['image']) > 0:
                        current_data_b = np.array(source2b.data["image"][0])
                        
                        if new == 1:  # Log scale
                            positive_data_b = current_data_b[current_data_b > 0]
                            if positive_data_b.size == 0:
                                print("Warning: No positive values for log scale in Plot2B, using linear scale")
                                new_cls = LinearColorMapper
                                low2b = color_mapper2b.low if color_mapper2b.low > 0 else 0.001
                                high2b = color_mapper2b.high if color_mapper2b.high > 0 else 1.0
                            else:
                                low2b = color_mapper2b.low if color_mapper2b.low > 0 else max(np.min(positive_data_b), 0.001)
                                high2b = color_mapper2b.high if color_mapper2b.high > 0 else np.max(positive_data_b)
                        else:  # Linear scale
                            low2b = color_mapper2b.low
                            high2b = color_mapper2b.high
                    else:
                        # No image data, use current ranges
                        low2b = color_mapper2b.low
                        high2b = color_mapper2b.high
                    
                    color_mapper2b = new_cls(palette=(color_mapper2a.palette if color_mapper2a is not None else "Viridis256"), low=low2b, high=high2b)
                    if len(plot2b.renderers) > 0 and image_renderer2b is not None:
                        # Remove the old renderer
                        plot2b.renderers.remove(plot2b.renderers[0])
                        # Re-add the renderer with the new color mapper
                        image_renderer2b = plot2b.image(
                            "image", source=source2b, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper2b,
                        )
                    # Update colorbar if it exists
                    if colorbar2b is not None:
                        colorbar2b.color_mapper = color_mapper2b
                
                # Handle 1D plots (3D volumes) - apply log scale to y-axis
                if is_3d_volume:
                    if new == 1:  # Log scale selected
                        # Set y-axis to log scale
                        plot2.y_scale = LogScale()
                        # Ensure y-axis range is positive for log scale
                        if 'y' in source2.data and len(source2.data['y']) > 0:
                            y_data = np.array(source2.data['y'])
                            positive_y = y_data[y_data > 0]
                            if positive_y.size > 0:
                                y_min = max(np.min(positive_y), 0.001)
                                y_max = np.max(positive_y)
                                plot2.y_range.start = y_min
                                plot2.y_range.end = y_max
                            else:
                                # No positive values, set safe default
                                plot2.y_range.start = 0.001
                                plot2.y_range.end = 1.0
                    else:  # Linear scale selected
                        plot2.y_scale = LinearScale()
                        # Reset y-range to include all data (including negatives/zeros)
                        if 'y' in source2.data and len(source2.data['y']) > 0:
                            y_data = np.array(source2.data['y'])
                            plot2.y_range.start = float(np.min(y_data))
                            plot2.y_range.end = float(np.max(y_data))
                    
                    # Force plot update for 1D plots by updating data source
                    if 'x' in source2.data and 'y' in source2.data:
                        source2.data = {
                            'x': source2.data['x'],
                            'y': source2.data['y']
                        }
                    
                    # Handle Plot2B 1D plots
                    if 'plot2b' in locals() and plot2b is not None and not plot2b_is_2d:
                        if new == 1:  # Log scale
                            plot2b.y_scale = LogScale()
                            if 'y' in source2b.data and len(source2b.data['y']) > 0:
                                y_data_b = np.array(source2b.data['y'])
                                positive_y_b = y_data_b[y_data_b > 0]
                                if positive_y_b.size > 0:
                                    y_min_b = max(np.min(positive_y_b), 0.001)
                                    y_max_b = np.max(positive_y_b)
                                    plot2b.y_range.start = y_min_b
                                    plot2b.y_range.end = y_max_b
                                else:
                                    plot2b.y_range.start = 0.001
                                    plot2b.y_range.end = 1.0
                        else:  # Linear scale
                            plot2b.y_scale = LinearScale()
                            if 'y' in source2b.data and len(source2b.data['y']) > 0:
                                y_data_b = np.array(source2b.data['y'])
                                plot2b.y_range.start = float(np.min(y_data_b))
                                plot2b.y_range.end = float(np.max(y_data_b))
                        # Force Plot2B update by updating data source
                        if 'source2b' in locals() and source2b is not None and 'x' in source2b.data and 'y' in source2b.data:
                            source2b.data = {
                                'x': source2b.data['x'],
                                'y': source2b.data['y']
                            }
                        
            except Exception as e:
                print(f"Error in on_map2_color_scale_change: {e}")
                import traceback
                traceback.print_exc()
        
        def on_map3_color_scale_change(attr, old, new):
            """Handle Plot3 color scale change (Linear vs Log)"""
            nonlocal color_mapper3, image_renderer3
            try:
                # Get current data from source3
                if 'image' not in source3.data or len(source3.data['image']) == 0:
                    print("Warning: No image data in source3 for color scale change")
                    return
                
                current_data = np.array(source3.data["image"][0])
                if current_data.size == 0:
                    print("Warning: Empty image data for color scale change")
                    return
                
                # For log scale, we need to handle zeros/negatives
                if new == 1:  # Log scale selected
                    # Filter out zeros and negatives, use a small epsilon for minimum
                    positive_data = current_data[current_data > 0]
                    if positive_data.size == 0:
                        print("Warning: No positive values for log scale in Plot3, using linear scale")
                        new_cls = LinearColorMapper
                        # Use current ranges or defaults
                        low3 = color_mapper3.low if color_mapper3.low > 0 else 0.001
                        high3 = color_mapper3.high if color_mapper3.high > 0 else 1.0
                    else:
                        new_cls = LogColorMapper
                        # Use current ranges if they're positive, otherwise use data-based ranges
                        low3 = color_mapper3.low if color_mapper3.low > 0 else max(np.min(positive_data), 0.001)
                        high3 = color_mapper3.high if color_mapper3.high > 0 else np.max(positive_data)
                else:  # Linear scale
                    new_cls = LinearColorMapper
                    # Preserve current ranges
                    low3 = color_mapper3.low
                    high3 = color_mapper3.high
                
                # Recreate mapper for Plot3
                color_mapper3 = new_cls(palette=color_mapper3.palette, low=low3, high=high3)
                if len(plot3.renderers) > 0 and image_renderer3 is not None:
                    # Remove the old renderer
                    plot3.renderers.remove(plot3.renderers[0])
                    # Re-add the renderer with the new color mapper
                    image_renderer3 = plot3.image(
                        "image", source=source3, x="x", y="y", dw="dw", dh="dh", color_mapper=color_mapper3,
                    )
                # Update colorbar if it exists
                if 'colorbar3' in locals() and colorbar3 is not None:
                    colorbar3.color_mapper = color_mapper3
                        
            except Exception as e:
                print(f"Error in on_map3_color_scale_change: {e}")
                import traceback
                traceback.print_exc()
        
        def set_palette(value):
            nonlocal colorbar1, colorbar2, colorbar3
            # Update color mappers and their corresponding colorbars
            color_mapper1a.palette = value
            # Update colorbar1 to reflect the new palette
            if colorbar1 is not None:
                colorbar1.color_mapper = color_mapper1a
            
            if 'color_mapper1b' in locals() and color_mapper1b is not None:
                color_mapper1b.palette = value
                # Update colorbar1b if it exists
                if 'colorbar1b' in locals() and colorbar1b is not None:
                    colorbar1b.color_mapper = color_mapper1b
            
            if not is_3d_volume and color_mapper2a is not None:
                color_mapper2a.palette = value
                # Update colorbar2 if it exists (only for 2D plots)
                if colorbar2 is not None:
                    colorbar2.color_mapper = color_mapper2a
            
            if 'color_mapper2b' in locals() and color_mapper2b is not None:
                color_mapper2b.palette = value
                # Update colorbar2b if it exists
                if 'colorbar2b' in locals() and colorbar2b is not None:
                    colorbar2b.color_mapper = color_mapper2b
            
            color_mapper3.palette = value
            # Update colorbar3 to reflect the new palette
            if colorbar3 is not None:
                colorbar3.color_mapper = color_mapper3
        
        def schedule_show_slice():
            from bokeh.io import curdoc
            curdoc().add_next_tick_callback(show_slice)
        
        def draw_rect2():
            if is_3d_volume:
                # 3D handled via overlay, nothing to draw here
                pass
            else:
                # 4D: draw only on Plot2
                draw_rect(plot2, rect2, rect2.min_x, rect2.max_x, rect2.min_y, rect2.max_y)

        def draw_rect2b():
            if 'plot2b' in locals() and plot2b is not None:
                # Use Plot2B's own dimensionality: draw only if Plot2B is 2D image
                if 'plot2b_is_2d' in locals() and plot2b_is_2d and 'rect2b' in locals() and rect2b is not None:
                    draw_rect(plot2b, rect2b, rect2b.min_x, rect2b.max_x, rect2b.min_y, rect2b.max_y)
            
        def update_z_range_display():
            """Update the z-range display for 3D volumes"""
            if is_3d_volume and z_range_display is not None:
                z_min = rect2.min_x
                z_max = rect2.max_x
                z_range_display.text = f"""
                <b>Z Range Selection:</b><br>
                z_min: {z_min}, z_max: {z_max}<br>
                <small>Shift+click in Plot2 to set z_min, Ctrl/Cmd+click or double-click to set z_max</small>
                """
        
        def update_range_overlay():
            """Update the range overlay visualization for 3D volumes"""
            print(f"DEBUG: update_range_overlay called, is_3d_volume={is_3d_volume}, range_overlay_renderer={range_overlay_renderer is not None}")
            if is_3d_volume and range_overlay_renderer is not None:
                z_min = rect2.min_x
                z_max = rect2.max_x
                print(f"DEBUG: z_min={z_min}, z_max={z_max}")
                
                if z_min != z_max:  # Only show overlay if range is selected
                    # Get current plot ranges
                    y_min = plot2.y_range.start
                    y_max = plot2.y_range.end
                    print(f"DEBUG: Plot ranges - y_min={y_min}, y_max={y_max}")
                    
                    # Calculate overlay position and size
                    if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                        try:
                            probe_coords = process_4dnexus.load_probe_coordinates()
                            if probe_coords is not None:
                                x_min_coord = probe_coords[z_min] if z_min < len(probe_coords) else probe_coords[-1]
                                x_max_coord = probe_coords[z_max] if z_max < len(probe_coords) else probe_coords[-1]
                                x_center = (x_min_coord + x_max_coord) / 2
                                x_width = abs(x_max_coord - x_min_coord)
                            else:
                                x_center = (z_min + z_max) / 2
                                x_width = abs(z_max - z_min)
                        except:
                            x_center = (z_min + z_max) / 2
                            x_width = abs(z_max - z_min)
                    else:
                        x_center = (z_min + z_max) / 2
                        x_width = abs(z_max - z_min)
                    
                    print(f"DEBUG: Overlay calculation - x_center={x_center}, x_width={x_width}")
                    
                    # Update overlay data
                    range_overlay_source.data = {
                        "x": [x_center],
                        "y": [y_min],
                        "width": [x_width],
                        "height": [y_max - y_min]
                    }
                    print(f"Range overlay updated: x={x_center:.3f}, width={x_width:.3f}, height={y_max-y_min:.3f}")
                else:
                    # Clear overlay if no range selected
                    range_overlay_source.data = {
                        "x": [],
                        "y": [],
                        "width": [],
                        "height": []
                    }
                    print("Range overlay cleared")

        def update_range_overlay_b():
            # Update Plot2B overlay only if Plot2B is 3D
            if not ('plot2b' in locals() and plot2b is not None and 'rect2b' in locals() and rect2b is not None and 'range_overlay_source_b' in locals() and range_overlay_source_b is not None):
                return
            z_min = rect2b.min_x
            z_max = rect2b.max_x
            if z_min != z_max:
                y_min = plot2b.y_range.start
                y_max = plot2b.y_range.end
                if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and getattr(process_4dnexus, 'probe_x_coords_picked_b', False):
                    try:
                        probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                        if probe_coords_b is not None:
                            x_min_coord = probe_coords_b[z_min] if z_min < len(probe_coords_b) else probe_coords_b[-1]
                            x_max_coord = probe_coords_b[z_max] if z_max < len(probe_coords_b) else probe_coords_b[-1]
                            x_center = (x_min_coord + x_max_coord) / 2
                            x_width = abs(x_max_coord - x_min_coord)
                        else:
                            x_center = (z_min + z_max) / 2
                            x_width = abs(z_max - z_min)
                    except Exception:
                        x_center = (z_min + z_max) / 2
                        x_width = abs(z_max - z_min)
                else:
                    x_center = (z_min + z_max) / 2
                    x_width = abs(z_max - z_min)
                range_overlay_source_b.data = {"x": [x_center], "y": [y_min], "width": [x_width], "height": [y_max - y_min]}
            else:
                range_overlay_source_b.data = {"x": [], "y": [], "width": [], "height": []}
        
        def draw_rect3():
            draw_rect(plot3, rect3, rect3.min_x, rect3.max_x, rect3.min_y, rect3.max_y)
        
        def on_plot2_doubletap(event):
            """Handle double-tap events on plot2 for max coordinates"""
            print("plot2 double-tap event:", event, event.x, event.y)
            
            try:
                print("Double-tap - setting max coordinates")
                if event.x is not None and event.y is not None:
                    if is_3d_volume:
                        # For 3D volumes: only use x-coordinate, convert to data index
                        if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                            try:
                                probe_coords = process_4dnexus.load_probe_coordinates()
                                if probe_coords is not None:
                                    z_index = np.argmin(np.abs(probe_coords - event.x))
                                    print(f"on_plot2_doubletap: plot_x={event.x:.3f}, closest probe_coord={probe_coords[z_index]:.3f}, z_index={z_index}")
                                else:
                                    z_index = int(event.x)
                                    print(f"on_plot2_doubletap: no probe coords, using plot_x={event.x:.3f}, z_index={z_index}")
                            except:
                                z_index = int(event.x)
                                print(f"on_plot2_doubletap: failed to load probe coords, using plot_x={event.x:.3f}, z_index={z_index}")
                        else:
                            z_index = int(event.x)
                            print(f"on_plot2_doubletap: no probe coords specified, using plot_x={event.x:.3f}, z_index={z_index}")
                        
                        # Double-click: Set max value only
                        rect2.set(max_x=z_index, max_y=z_index)
                        print(f"DEBUG: Double-click detected, setting max_x={z_index}")
                        print(f"DEBUG: Before rect2.set, rect2.min_x={rect2.min_x}, rect2.max_x={rect2.max_x}")
                        print(f"DEBUG: After rect2.set, rect2.min_x={rect2.min_x}, rect2.max_x={rect2.max_x}")
                        print(f"on_plot2_doubletap rect2={rect2} - 3D volume, z_index={z_index}")
                        draw_rect2()
                        update_z_range_display()
                        update_range_overlay()
                    else:
                        # For 4D volumes: use both x and y coordinates
                        print(f"DEBUG: Double-click detected for 4D volume, setting max_x={int(event.x)}, max_y={int(event.y)}")
                        print(f"DEBUG: Before rect2.set, rect2.min_x={rect2.min_x}, rect2.max_x={rect2.max_x}, rect2.min_y={rect2.min_y}, rect2.max_y={rect2.max_y}")
                        rect2.set(max_x=int(event.x), max_y=int(event.y))
                        print(f"DEBUG: After rect2.set, rect2.min_x={rect2.min_x}, rect2.max_x={rect2.max_x}, rect2.min_y={rect2.min_y}, rect2.max_y={rect2.max_y}")
                        print(f"on_plot2_doubletap rect2={rect2} - 4D volume")
                        draw_rect2()
            except Exception as e:
                print(f"Double-tap event error: {e}")

        def on_plot2a_doubletap(event):
            return on_plot2_doubletap(event)

        # Plot2B independent handlers
        def on_plot2b_tap(event):
            print(f"DEBUG: on_plot2b_tap received, x={event.x}, y={event.y}, plot2b_is_2d={plot2b_is_2d}")
            if not ('plot2b' in locals() and plot2b is not None and 'rect2b' in locals() and rect2b is not None):
                print("DEBUG: on_plot2b_tap early return: plot2b or rect2b missing")
                return
            # Use Plot2B's own dimensionality instead of primary volume
            if not plot2b_is_2d:
                if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and getattr(process_4dnexus, 'probe_x_coords_picked_b', False):
                    try:
                        probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                        if probe_coords_b is not None:
                            z_index = int(np.argmin(np.abs(probe_coords_b - event.x)))
                        else:
                            z_index = int(event.x)
                    except Exception:
                        z_index = int(event.x)
                else:
                    z_index = int(event.x)
                if event.modifiers.get("shift", False):
                    rect2b.set(min_x=z_index, min_y=z_index)
                elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta',False) or event.modifiers.get('cmd',False):
                    rect2b.set(max_x=z_index, max_y=z_index)
                else:
                    rect2b.set(min_x=z_index, min_y=z_index, max_x=z_index, max_y=z_index)
                update_range_overlay_b()
            else:
                if event.modifiers.get("shift", False):
                    rect2b.set(min_x=int(event.x), min_y=int(event.y))
                    draw_rect2b()
                elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta',False) or event.modifiers.get('cmd',False):
                    rect2b.set(max_x=int(event.x), max_y=int(event.y))
                    draw_rect2b()
                else:
                    clear_rect(plot2b, rect2b)
                    rect2b.set(min_x=int(event.x), min_y=int(event.y), max_x=int(event.x), max_y=int(event.y))
                    draw_rect(plot2b, rect2b, int(event.x), int(event.x), int(event.y), int(event.y))
                print(f"DEBUG: on_plot2b_tap updated rect2b: min=({rect2b.min_x},{rect2b.min_y}) max=({rect2b.max_x},{rect2b.max_y})")

        def on_plot2b_doubletap(event):
            print(f"DEBUG: on_plot2b_doubletap received, x={getattr(event,'x',None)}, y={getattr(event,'y',None)}, plot2b_is_2d={plot2b_is_2d}")
            if not ('plot2b' in locals() and plot2b is not None and 'rect2b' in locals() and rect2b is not None):
                print("DEBUG: on_plot2b_doubletap early return: plot2b or rect2b missing")
                return
            try:
                if not plot2b_is_2d:
                    if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and getattr(process_4dnexus, 'probe_x_coords_picked_b', False):
                        try:
                            probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                            if probe_coords_b is not None:
                                z_index = int(np.argmin(np.abs(probe_coords_b - event.x)))
                            else:
                                z_index = int(event.x)
                        except Exception:
                            z_index = int(event.x)
                    else:
                        z_index = int(event.x)
                    rect2b.set(max_x=z_index, max_y=z_index)
                    update_range_overlay_b()
                else:
                    rect2b.set(max_x=int(event.x), max_y=int(event.y))
                    draw_rect2b()
            except Exception as e:
                print(f"Plot2B Double-tap event error: {e}")
        
        def on_plot3_tap(event):
            x_index = get_x_index(event.x)
            x_coord = x_coords[x_index]
            y_index = get_y_index(event.y)
            y_coord = y_coords[y_index]

            print(f"DEBUG: Plot3 tap - x_coord={x_coord}, y_coord={y_coord}")
            print(f"DEBUG: Event modifiers: {event.modifiers}")
            print(f"DEBUG: shift={event.modifiers.get('shift', False)}, ctrl={event.modifiers.get('ctrl', False)}")

            if event.modifiers.get("shift", False):
                # Shift+click: Set min values only
                print(f"DEBUG: Shift+click detected for Plot3, setting min_x={x_coord}, min_y={y_coord}")
                rect3.set(min_x=x_coord, min_y=y_coord)
                print(f"on_plot3_tap rect3={rect3} (shift pressed)")
                draw_rect3()
            elif event.modifiers.get("ctrl", False) or event.modifiers.get('meta',False) or event.modifiers.get('cmd',False):
                # Ctrl/Cmd+click: Set max values only
                print(f"DEBUG: Ctrl/Cmd+click detected for Plot3, setting max_x={x_coord}, max_y={y_coord}")
                rect3.set(max_x=x_coord, max_y=y_coord)
                print(f"on_plot3_tap rect3={rect3} (ctrl/cmd pressed)")
                draw_rect3()
            else:
                # Regular click: Clear and set both min and max to same value
                print(f"DEBUG: Regular click detected for Plot3, clearing and setting both min/max")
                clear_rect(plot3, rect3)
                rect3.set(min_x=x_coord, min_y=y_coord, max_x=x_coord, max_y=y_coord)
                draw_rect(plot3, rect3, x_coord, x_coord, y_coord, y_coord)
                print(f"on_plot3_tap x_coord={x_coord} y_coord={y_coord}")
        
        def on_plot3_doubletap(event):
            """Handle double-tap events on plot3 for max coordinates"""
            x_index = get_x_index(event.x)
            x_coord = x_coords[x_index]
            y_index = get_y_index(event.y)
            y_coord = y_coords[y_index]
            print("plot3 double-tap event:", event, event.x, event.y)
            
            try:
                print("Double-tap - setting max coordinates")
                if event.x is not None and event.y is not None:
                    print(f"DEBUG: Double-click detected for Plot3, setting max_x={x_coord}, max_y={y_coord}")
                    print(f"DEBUG: Before rect3.set, rect3.min_x={rect3.min_x}, rect3.max_x={rect3.max_x}, rect3.min_y={rect3.min_y}, rect3.max_y={rect3.max_y}")
                    rect3.set(max_x=x_coord, max_y=y_coord)
                    print(f"DEBUG: After rect3.set, rect3.min_x={rect3.min_x}, rect3.max_x={rect3.max_x}, rect3.min_y={rect3.min_y}, rect3.max_y={rect3.max_y}")
                    print(f"on_plot3_doubletap rect3={rect3}")
                    draw_rect3()
            except Exception as e:
                print(f"Double-tap event error: {e}")
        
        def _compute_plot3_image_work():
            t_plot3 = time.time()
            if is_3d_volume:
                # For 3D volumes: sum over Z dimension for selected range
                z1, z2 = rect2.min_x, rect2.max_x
                # Normalize and clamp to valid non-empty range
                try:
                    z_lo, z_hi = (int(z1), int(z2)) if z1 <= z2 else (int(z2), int(z1))
                    z_lo = max(0, min(z_lo, volume.shape[2]-1))
                    z_hi = max(0, min(z_hi, volume.shape[2]-1))
                    if z_hi <= z_lo:
                        z_hi = min(z_lo + 1, volume.shape[2])
                except Exception:
                    z_lo, z_hi = 0, min(1, volume.shape[2])
                print("# compute_plot3_image (3D)", z_lo, z_hi)
                piece = volume[:, :, z_lo:z_hi]
                img = np.sum(piece, axis=2)  # sum over Z dimension
                # Normalize to [0,1]
                img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
                vmin = float(np.min(img))
                vmax = float(np.max(img))
                if vmax > vmin:
                    img = (img - vmin) / (vmax - vmin)
                else:
                    img = np.zeros_like(img)
                
                source3.data = dict(
                    image=[img],
                    x=[plot3.x_range.start],
                    dw=[plot3.x_range.end - plot3.x_range.start],
                    y=[plot3.y_range.start],
                    dh=[plot3.y_range.end - plot3.y_range.start],
                )
                
                set_colormap_range(plot3, colorbar3, color_mapper3, 0.0, 1.0)
                
                # Update Plot3 range inputs with actual data range
                range3_min_input.value = "0"
                range3_max_input.value = "1"
            else:
                # For 4D volumes: sum over Z and U dimensions
                z1, z2, u1, u2 = rect2.min_x, rect2.max_x, rect2.min_y, rect2.max_y
                # Normalize, clamp, and ensure non-empty spans
                try:
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
                except Exception:
                    z_lo, z_hi, u_lo, u_hi = 0, min(1, volume.shape[2]), 0, min(1, volume.shape[3])
                print("# compute_plot3_image (4D)", z_lo, z_hi, u_lo, u_hi)
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

                source3.data = dict(
                    image=[img],
                    x=[plot3.x_range.start],
                    dw=[plot3.x_range.end - plot3.x_range.start],
                    y=[plot3.y_range.start],
                    dh=[plot3.y_range.end - plot3.y_range.start],
                )

                set_colormap_range(plot3, colorbar3, color_mapper3, 0.0, 1.0)
                
                # Update Plot3 range inputs with actual data range
                range3_min_input.value = "0"
                range3_max_input.value = "1"
            # Done status
            try:
                dt = time.time() - t_plot3
                shape_txt = f"{source3.data['image'][0].shape[1]}x{source3.data['image'][0].shape[0]}" if source3.data.get('image') else ""
                plot3_status_div_a.text = f"Done ({shape_txt}) in {dt:.2f}s"
                compute_plot3_image_button.disabled = False
                compute_plot3_image_button.label = "Show Plot3 from Plot2a ->"
            except Exception:
                try:
                    compute_plot3_image_button.disabled = False
                    compute_plot3_image_button.label = "Show Plot3 from Plot2a ->"
                except Exception:
                    pass

        def compute_plot3_image(evt=None):
            try:
                compute_plot3_image_button.disabled = True
                compute_plot3_image_button.label = "Computing…"
                plot3_status_div_a.text = "Computing Plot3…"
            except Exception:
                pass
            from bokeh.io import curdoc as _curdoc
            _curdoc().add_next_tick_callback(_compute_plot3_image_work)

        # Reset Plot2A to fresh data from process_4dnexus
        def on_reset_plot2a():
            try:
                print("DEBUG: on_reset_plot2a invoked")
                if is_3d_volume:
                    # 3D volume → 1D line at center
                    x_mid = volume.shape[0] // 2
                    y_mid = volume.shape[1] // 2
                    line = np.array(volume[x_mid, y_mid, :])
                    if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                        try:
                            probe_coords = process_4dnexus.load_probe_coordinates()
                            xvals = probe_coords if probe_coords is not None and len(probe_coords) == len(line) else np.arange(len(line))
                        except Exception:
                            xvals = np.arange(len(line))
                    else:
                        xvals = np.arange(len(line))
                    source2.data = {"x": xvals, "y": line}
                    plot2.x_range.start = float(np.min(xvals))
                    plot2.x_range.end = float(np.max(xvals))
                    plot2.y_range.start = float(np.min(line))
                    plot2.y_range.end = float(np.max(line))
                    # Reset numeric range inputs to percentile-based data range
                    try:
                        p2_min, p2_max = get_percentile_range(line)
                        range2_min_input.value = str(p2_min)
                        range2_max_input.value = str(p2_max)
                    except Exception:
                        pass
                    # Clear 3D overlay selection and status
                    if 'range_overlay_source' in locals():
                        range_overlay_source.data = {"x": [], "y": [], "width": [], "height": []}
                    if 'z_range_display' in locals() and z_range_display is not None:
                        z_range_display.text = "<b>Z Range Selection:</b><br>z_min: 0, z_max: 0"
                else:
                    # 4D volume → 2D image at center x,y
                    x_mid = volume.shape[0] // 2
                    y_mid = volume.shape[1] // 2
                    img = np.array(volume[x_mid, y_mid, :, :])
                    # Match original ProbePlot orientation: dw=shape[2], dh=shape[3]
                    source2.data = {"image": [img], "x": [0], "y": [0], "dw": [img.shape[0]], "dh": [img.shape[1]]}
                    try:
                        p2_min, p2_max = get_percentile_range(img)
                        set_colormap_range(plot2, colorbar2, color_mapper2a, p2_min, p2_max)
                        # Reset numeric range inputs to percentile-based data range
                        range2_min_input.value = str(p2_min)
                        range2_max_input.value = str(p2_max)
                    except Exception:
                        pass
                    # Clear any rectangle lines on Plot2
                    clear_rect(plot2, rect2)
                plot2_status_div.text = "Reset"
            except Exception as _e:
                print(f"Reset Plot2a failed: {_e}")

        # Compute Plot3 based on Plot2B's selection (rect2b)
        def _compute_plot3_image_work_from_plot2b():
            t_plot3b = time.time()
            vb = getattr(process_4dnexus, 'volume_dataset_b', None)
            if vb is None:
                try:
                    compute_plot3_from_plot2b_button.disabled = False
                    compute_plot3_from_plot2b_button.label = "Show Plot3 from Plot2b ->"
                except Exception:
                    pass
                return
             
            if len(vb.shape) == 3:
                z1, z2 = rect2b.min_x, rect2b.max_x
                # normalize and clamp bounds
                try:
                    z_lo, z_hi = (int(z1), int(z2)) if z1 <= z2 else (int(z2), int(z1))
                    z_lo = max(0, min(z_lo, vb.shape[2]-1))
                    z_hi = max(0, min(z_hi, vb.shape[2]-1))
                    if z_hi <= z_lo:
                        z_hi = min(z_lo + 1, vb.shape[2])
                except Exception:
                    z_lo, z_hi = 0, min(1, vb.shape[2])
                print(f"DEBUG _compute_plot3_image_work_from_plot2b: z1 {z_lo}, z2 {z_hi}"  )
                piece = vb[:, :, z_lo:z_hi]
                img = np.sum(piece, axis=2)
                img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
                vmin = float(np.min(img))
                vmax = float(np.max(img))
                img = (img - vmin) / (vmax - vmin) if vmax > vmin else np.zeros_like(img)
                source3.data = dict(
                    image=[img],
                    x=[plot3.x_range.start],
                    dw=[plot3.x_range.end - plot3.x_range.start],
                    y=[plot3.y_range.start],
                    dh=[plot3.y_range.end - plot3.y_range.start],
                )
                set_colormap_range(plot3, colorbar3, color_mapper3, 0.0, 1.0)
                range3_min_input.value = "0"
                range3_max_input.value = "1"
            else:
                z1, z2, u1, u2 = rect2b.min_x, rect2b.max_x, rect2b.min_y, rect2b.max_y
                # normalize and clamp 4D bounds
                try:
                    z_lo, z_hi = (int(z1), int(z2)) if z1 <= z2 else (int(z2), int(z1))
                    u_lo, u_hi = (int(u1), int(u2)) if u1 <= u2 else (int(u2), int(u1))
                    z_lo = max(0, min(z_lo, vb.shape[2]-1))
                    z_hi = max(0, min(z_hi, vb.shape[2]-1))
                    u_lo = max(0, min(u_lo, vb.shape[3]-1))
                    u_hi = max(0, min(u_hi, vb.shape[3]-1))
                    if z_hi <= z_lo:
                        z_hi = min(z_lo + 1, vb.shape[2])
                    if u_hi <= u_lo:
                        u_hi = min(u_lo + 1, vb.shape[3])
                except Exception:
                    z_lo, z_hi, u_lo, u_hi = 0, min(1, vb.shape[2]), 0, min(1, vb.shape[3])
                print(f"DEBUG _compute_plot3_image_work_from_plot2b: z1 {z_lo}, z2 {z_hi}, u1 {u_lo}, u2 {u_hi}"  )
                piece = vb[:, :, z_lo:z_hi, u_lo:u_hi]
                img = np.sum(piece, axis=(2, 3))
                img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
                vmin = float(np.min(img))
                vmax = float(np.max(img))
                img = (img - vmin) / (vmax - vmin) if vmax > vmin else np.zeros_like(img)
                source3.data = dict(
                    image=[img],
                    x=[plot3.x_range.start],
                    dw=[plot3.x_range.end - plot3.x_range.start],
                    y=[plot3.y_range.start],
                    dh=[plot3.y_range.end - plot3.y_range.start],
                )
                set_colormap_range(plot3, colorbar3, color_mapper3, 0.0, 1.0)
                range3_min_input.value = "0"
                range3_max_input.value = "1"
            try:
                dt = time.time() - t_plot3b
                shape_txt = f"{source3.data['image'][0].shape[1]}x{source3.data['image'][0].shape[0]}" if source3.data.get('image') else ""
                plot3_status_div_b.text = f"Done ({shape_txt}) in {dt:.2f}s"
                compute_plot3_from_plot2b_button.disabled = False
                compute_plot3_from_plot2b_button.label = "Show Plot3 from Plot2b ->"
            except Exception:
                try:
                    compute_plot3_from_plot2b_button.disabled = False
                    compute_plot3_from_plot2b_button.label = "Show Plot3 from Plot2b ->"
                except Exception:
                    pass

        def compute_plot3_image_from_plot2b(evt=None):
            try:
                compute_plot3_from_plot2b_button.disabled = True
                compute_plot3_from_plot2b_button.label = "Computing…"
                plot3_status_div_b.text = "Computing Plot3…"
            except Exception:
                pass
            from bokeh.io import curdoc as _curdoc
            _curdoc().add_next_tick_callback(_compute_plot3_image_work_from_plot2b)

        # Reset Plot2B to fresh data from process_4dnexus
        def on_reset_plot2b():
            try:
                if 'source2b' in locals() and plot2b is not None:
                    volume_b_local = getattr(process_4dnexus, 'volume_dataset_b', None)
                    if volume_b_local is None:
                        return
                    if plot2b_is_2d:
                        # 4D dataset → 2D image at center x,y
                        xb = volume_b_local.shape[0] // 2
                        yb = volume_b_local.shape[1] // 2
                        img = np.array(volume_b_local[xb, yb, :, :])
                        # Match original ProbePlot orientation
                        source2b.data = {"image": [img], "x": [0], "y": [0], "dw": [img.shape[0]], "dh": [img.shape[1]]}
                        if 'color_mapper2b' in locals() and color_mapper2b is not None and 'colorbar2b' in locals():
                            try:
                                p2b_min, p2b_max = get_percentile_range(img)
                                set_colormap_range(plot2b, colorbar2b, color_mapper2b, p2b_min, p2b_max)
                            except Exception:
                                pass
                        # Reset Plot2B range inputs if present (percentile-based)
                        if 'range2b_min_input' in locals() and range2b_min_input is not None:
                            try:
                                p2b_min, p2b_max = get_percentile_range(img)
                                range2b_min_input.value = str(p2b_min)
                                range2b_max_input.value = str(p2b_max)
                            except Exception:
                                pass
                    else:
                        # 3D dataset → 1D line at center
                        xb = volume_b_local.shape[0] // 2
                        yb = volume_b_local.shape[1] // 2
                        line_b = np.array(volume_b_local[xb, yb, :])
                        xvals_b = np.arange(len(line_b))
                        source2b.data = {"x": xvals_b, "y": line_b}
                        plot2b.x_range.start = float(np.min(xvals_b))
                        plot2b.x_range.end = float(np.max(xvals_b))
                        plot2b.y_range.start = float(np.min(line_b))
                        plot2b.y_range.end = float(np.max(line_b))
            except Exception as _e:
                print(f"Reset Plot2b failed: {_e}")
        
        def _compute_plot2_image_work():
            t_plot2 = time.time()
            if is_3d_volume:
                # For 3D volumes: sum over X,Y dimensions for selected region in Plot3
                x1 = get_x_index(rect3.min_x)
                y1 = get_y_index(rect3.min_y)
                x2 = max(x1 + 1, get_x_index(rect3.max_x))
                y2 = max(y1 + 1, get_y_index(rect3.max_y))
                
                print("#############################################################################")
                print("# compute_plot2_image (3D)", x1, x2, y1, y2)
                piece = volume[x1:x2, y1:y2, :]
                slice = np.sum(piece, axis=(0, 1)) / ((x2-x1)*(y2-y1))  # sum over X and Y
                
                print(">>>>>>>>>>>>>>>>", np.min(slice), np.max(slice))
                print("#############################################################################")
                
                # Update the 1D line plot with proper coordinates
                if hasattr(process_4dnexus, 'probe_x_coords_picked') and process_4dnexus.probe_x_coords_picked:
                    try:
                        probe_coords = process_4dnexus.load_probe_coordinates()
                        if probe_coords is not None and len(probe_coords) == len(slice):
                            x_coords_1d = probe_coords
                            print(f"Using probe coordinates for compute_plot2_image: {len(probe_coords)} points")
                        else:
                            x_coords_1d = np.arange(len(slice))
                            print(f"Probe coordinates not available for compute_plot2_image, using indices")
                    except:
                        x_coords_1d = np.arange(len(slice))
                        print(f"Failed to load probe coordinates for compute_plot2_image, using indices")
                else:
                    x_coords_1d = np.arange(len(slice))
                    print(f"No probe coordinates for compute_plot2_image, using indices")
                
                source2.data = {
                    "x": x_coords_1d,
                    "y": slice
                }
                
                # Update plot ranges
                plot2.x_range.start = x_coords_1d.min()
                plot2.x_range.end = x_coords_1d.max()
                plot2.y_range.start = slice.min()
                plot2.y_range.end = slice.max()
                # Update numeric range inputs to percentile-based data range
                try:
                    p2_min, p2_max = get_percentile_range(slice)
                    range2_min_input.value = str(p2_min)
                    range2_max_input.value = str(p2_max)
                except Exception:
                    pass
            else:
                # For 4D volumes: sum over X,Y dimensions for selected region in Plot3
                x1 = get_x_index(rect3.min_x)
                y1 = get_y_index(rect3.min_y)

                x2 = max(x1 + 1, get_x_index(rect3.max_x))
                y2 = max(y1 + 1, get_y_index(rect3.max_y))

                print("#############################################################################")
                print("# compute_plot2_image (4D)", x1, x2, y1, y2)
                piece = volume[x1:x2, y1:y2, :, :]
                slice = np.sum(piece, axis=(0, 1)) / ((x2-x1)*(y2-y1))  # sum over X and Y

                print(">>>>>>>>>>>>>>>>", np.min(slice), np.max(slice))
                print("#############################################################################")

                assert slice.shape[0] == volume.shape[2]  # After flipud: shape[2] stays shape[0]
                assert slice.shape[1] == volume.shape[3]  # After flipud: shape[3] stays shape[1]

                source2.data = dict(
                    image=[slice], x=[0], y=[0], dw=[slice.shape[0]], dh=[slice.shape[1]]  # Revert dw/dh
                )
                
                p2_min, p2_max = get_percentile_range(slice)
                set_colormap_range(plot2, colorbar2, color_mapper2a, p2_min, p2_max)
                # Update numeric range inputs to percentile-based data range
                try:
                    range2_min_input.value = str(p2_min)
                    range2_max_input.value = str(p2_max)
                except Exception:
                    pass
            # Done status
            try:
                dt = time.time() - t_plot2
                if is_3d_volume:
                    length_txt = f"{len(slice)} pts" if 'slice' in locals() else ""
                    plot2_status_div.text = f"Done ({length_txt}) in {dt:.2f}s"
                else:
                    shape_txt = f"{source2.data['image'][0].shape[1]}x{source2.data['image'][0].shape[0]}" if source2.data.get('image') else ""
                    plot2_status_div.text = f"Done ({shape_txt}) in {dt:.2f}s"
                compute_plot2_image_button.disabled = False
                compute_plot2_image_button.label = "<- Compute Plot2a"
            except Exception:
                try:
                    compute_plot2_image_button.disabled = False
                    compute_plot2_image_button.label = "<- Compute Plot2a"
                except Exception:
                    pass

        def _compute_plot2b_image_work():
            t_plot2b = time.time()
            # Use secondary dataset if available
            volume_b_local = getattr(process_4dnexus, 'volume_dataset_b', None)
            if volume_b_local is None:
                plot2b_status_div.text = "No Plot2B dataset"
                try:
                    compute_plot2b_image_button.disabled = False
                    compute_plot2b_image_button.label = "<- Compute Plot2b"
                except Exception:
                    pass
                return
            if len(volume_b_local.shape) == 3:
                # 3D: produce 1D line
                x1 = get_x_index(rect3.min_x)
                y1 = get_y_index(rect3.min_y)
                x2 = max(x1 + 1, get_x_index(rect3.max_x))
                y2 = max(y1 + 1, get_y_index(rect3.max_y))
                piece = volume_b_local[x1:x2, y1:y2, :]
                slice_b = np.sum(piece, axis=(0, 1)) / ((x2-x1)*(y2-y1))
                if hasattr(process_4dnexus, 'probe_x_coords_picked_b') and process_4dnexus.probe_x_coords_picked_b:
                    try:
                        probe_coords_b = process_4dnexus.load_probe_coordinates(use_b=True)
                        x_coords_1d_b = probe_coords_b if (probe_coords_b is not None and len(probe_coords_b) == len(slice_b)) else np.arange(len(slice_b))
                    except:
                        x_coords_1d_b = np.arange(len(slice_b))
                else:
                    x_coords_1d_b = np.arange(len(slice_b))
                # Update Plot2B source (line)
                if 'source2b' in locals():
                    source2b.data = {"x": x_coords_1d_b, "y": slice_b}
                    plot2b.x_range.start = x_coords_1d_b.min()
                    plot2b.x_range.end = x_coords_1d_b.max()
                    plot2b.y_range.start = slice_b.min()
                    plot2b.y_range.end = slice_b.max()
                    # Update Plot2B numeric range inputs if present (percentile-based)
                    if 'range2b_min_input' in locals() and range2b_min_input is not None:
                        try:
                            p2b_min, p2b_max = get_percentile_range(slice_b)
                            range2b_min_input.value = str(p2b_min)
                            range2b_max_input.value = str(p2b_max)
                        except Exception:
                            pass
            else:
                # 4D: produce 2D image
                x1 = get_x_index(rect3.min_x)
                y1 = get_y_index(rect3.min_y)
                x2 = max(x1 + 1, get_x_index(rect3.max_x))
                y2 = max(y1 + 1, get_y_index(rect3.max_y))
                piece = volume_b_local[x1:x2, y1:y2, :, :]
                slice_b = np.sum(piece, axis=(0, 1)) / ((x2-x1)*(y2-y1))
                if 'source2b' in locals():
                    source2b.data = dict(image=[slice_b], x=[0], y=[0], dw=[slice_b.shape[0]], dh=[slice_b.shape[1]])
                if 'color_mapper2b' in locals() and color_mapper2b is not None and 'colorbar2b' in locals():
                    p2b_min, p2b_max = get_percentile_range(slice_b)
                    set_colormap_range(plot2b, colorbar2b, color_mapper2b, p2b_min, p2b_max)
                # Update Plot2B numeric range inputs if present (percentile-based)
                if 'range2b_min_input' in locals() and range2b_min_input is not None:
                    try:
                        p2b_min, p2b_max = get_percentile_range(slice_b)
                        range2b_min_input.value = str(p2b_min)
                        range2b_max_input.value = str(p2b_max)
                    except Exception:
                        pass
            # Done status
            try:
                dt = time.time() - t_plot2b
                if len(volume_b_local.shape) == 3:
                    txt = f"{len(slice_b)} pts"
                else:
                    txt = f"{slice_b.shape[1]}x{slice_b.shape[0]}"
                plot2b_status_div.text = f"Done ({txt}) in {dt:.2f}s"
                compute_plot2b_image_button.disabled = False
                compute_plot2b_image_button.label = "<- Compute Plot2b"
            except Exception:
                try:
                    compute_plot2b_image_button.disabled = False
                    compute_plot2b_image_button.label = "<- Compute Plot2b"
                except Exception:
                    pass

        def compute_plot2b_image(evt=None):
            try:
                compute_plot2b_image_button.disabled = True
                compute_plot2b_image_button.label = "Computing…"
                plot2b_status_div.text = "Computing Plot2B…"
            except Exception:
                pass
            from bokeh.io import curdoc as _curdoc
            _curdoc().add_next_tick_callback(_compute_plot2b_image_work)

        def compute_plot2_image(evt=None):
            try:
                compute_plot2_image_button.disabled = True
                compute_plot2_image_button.label = "Computing…"
                plot2_status_div.text = "Computing Plot2…"
            except Exception:
                pass
            from bokeh.io import curdoc as _curdoc
            _curdoc().add_next_tick_callback(_compute_plot2_image_work)
        
        def on_reset_ranges_click():
            # Reset to percentile-based data ranges
            map_min, map_max = get_percentile_range(preview)
            range1_min_input.value = str(map_min)
            range1_max_input.value = str(map_max)
            set_colormap_range(plot1, colorbar1, color_mapper1a, map_min, map_max)
            
            # Reset Plot1B range if it exists
            if 'range1b_min_input' in locals() and range1b_min_input is not None and 'source1b' in locals():
                try:
                    img1b = source1b.data["image"][0]
                    p1b_min, p1b_max = get_percentile_range(img1b)
                    range1b_min_input.value = str(p1b_min)
                    range1b_max_input.value = str(p1b_max)
                    if 'color_mapper1b' in locals() and color_mapper1b is not None:
                        set_colormap_range(plot1b, colorbar1b, color_mapper1b, p1b_min, p1b_max)
                except Exception:
                    pass
            
            if is_3d_volume:
                # For 3D volumes: use initial 1D slice data with percentiles
                if initial_slice_1d is not None:
                    p2_min, p2_max = get_percentile_range(initial_slice_1d)
                    range2_min_input.value = str(p2_min)
                    range2_max_input.value = str(p2_max)
                # No color mapper for 1D plots
            else:
                # For 4D volumes: use initial 2D slice data with percentiles
                if initial_slice is not None:
                    p2_min, p2_max = get_percentile_range(initial_slice)
                    range2_min_input.value = str(p2_min)
                    range2_max_input.value = str(p2_max)
                    set_colormap_range(plot2, colorbar2, color_mapper2a, p2_min, p2_max)
            
            # Reset Plot2B range if it exists and is 2D
            if 'range2b_min_input' in locals() and range2b_min_input is not None and 'source2b' in locals() and plot2b_is_2d:
                try:
                    img2b = source2b.data["image"][0]
                    p2b_min, p2b_max = get_percentile_range(img2b)
                    range2b_min_input.value = str(p2b_min)
                    range2b_max_input.value = str(p2b_max)
                    if 'color_mapper2b' in locals() and color_mapper2b is not None:
                        set_colormap_range(plot2b, colorbar2b, color_mapper2b, p2b_min, p2b_max)
                except Exception:
                    pass
        
        def on_back_to_selection_click():
            # Clear the current dashboard and show the temporary dashboard
            from bokeh.io import curdoc
            doc = curdoc()
            doc.clear()
            
            # Recreate the temporary dashboard
            tmp_layout = create_tmp_dashboard(process_4dnexus)
            doc.add_root(tmp_layout)
        
        # Draw initial rectangles and crosshairs
        draw_rect(plot1, rect1, 0, volume.shape[0], 0, volume.shape[1])
        if is_3d_volume:
            # For 3D volume: do not draw rectangle on the 1D plot; use overlay only
            pass
        else:
            # For 4D volume: rect2 represents Z,Y dimensions
            draw_rect(plot2, rect2, 0, volume.shape[2], 0, volume.shape[3])
        
        # Draw rect3 for both 3D and 4D volumes
        draw_rect(plot3, rect3, 0, volume.shape[0], 0, volume.shape[1])
        draw_cross1()

        # Add callbacks
        def on_slider_change(attr, old, new):
            """Handle slider changes - update both Plot1/Plot2 and Plot1B/Plot2B"""
            schedule_show_slice()  # This updates Plot1 crosshairs (which also updates Plot1B) and Plot2
            # Also update Plot2B if it exists
            if 'plot2b' in locals() and plot2b is not None:
                show_slice_b()
        
        x_slider.on_change("value", on_slider_change)
        y_slider.on_change("value", on_slider_change)
        map1_color_scale_selector.on_change("active", on_map1_color_scale_change)
        map2_color_scale_selector.on_change("active", on_map2_color_scale_change)
        map3_color_scale_selector.on_change("active", on_map3_color_scale_change)
        palette_selector.on_change("value", lambda attr, old, new: set_palette(new))
        map_shape_selector.on_change("active", on_map_shape_change)
        custom_map_width_input.on_change("value", on_custom_map_width_change)
        custom_map_height_input.on_change("value", on_custom_map_height_change)
        map_scale_input.on_change("value", on_map_scale_change)
        plotmin_input.on_change("value", on_plot_size_change)
        plotmax_input.on_change("value", on_plot_size_change)
        
        # Set initial state (Square is default, so disable all inputs)
        custom_map_width_input.disabled = True
        custom_map_height_input.disabled = True
        map_scale_input.disabled = True
        # Hide custom and aspect ratio controls initially (Square mode is default)
        custom_map_controls.visible = False
        aspect_ratio_controls.visible = False
        # Show Map Size Limits initially (needed for Square mode)
        map_size_limits_controls.visible = True
        
        # Initialize plot1 dimensions
        update_plot1_dimensions()
        range1_min_input.on_change("value", lambda attr, old, new: on_range1_input_change())
        range1_max_input.on_change("value", lambda attr, old, new: on_range1_input_change())
        # Plot1B range handlers if present
        if 'range1b_min_input' in locals() and range1b_min_input is not None:
            range1b_min_input.on_change("value", lambda attr, old, new: on_range1b_input_change())
            range1b_max_input.on_change("value", lambda attr, old, new: on_range1b_input_change())
        range2_min_input.on_change("value", lambda attr, old, new: on_range2_input_change())
        range2_max_input.on_change("value", lambda attr, old, new: on_range2_input_change())
        range3_min_input.on_change("value", lambda attr, old, new: on_range3_input_change())
        range3_max_input.on_change("value", lambda attr, old, new: on_range3_input_change())
        reset_ranges_button.on_click(on_reset_ranges_click)

        # Plot2B range handlers if present
        if 'range2b_min_input' in locals() and range2b_min_input is not None:
            range2b_min_input.on_change("value", lambda attr, old, new: on_range2b_input_change())
            range2b_max_input.on_change("value", lambda attr, old, new: on_range2b_input_change())

        plot1.on_event("tap", on_plot1_tap)
        # Add tap handler for Plot1B if it exists
        if 'plot1b' in locals() and plot1b is not None:
            plot1b.on_event("tap", on_plot1b_tap)
        plot2.on_event("tap", on_plot2a_tap)
        plot2.on_event("doubletap", on_plot2a_doubletap)
        # Independent selection interactions on Plot2B if present
        if 'plot2b' in locals() and plot2b is not None:
            plot2b.on_event("tap", on_plot2b_tap)
            plot2b.on_event("doubletap", on_plot2b_doubletap)
        plot3.on_event("tap", on_plot3_tap)
        plot3.on_event("doubletap", on_plot3_doubletap)

        compute_plot2_image_button.on_click(compute_plot2_image)
        compute_plot2b_image_button.on_click(compute_plot2b_image)
        compute_plot3_image_button.on_click(compute_plot3_image)
        compute_plot3_from_plot2b_button.on_click(compute_plot3_image_from_plot2b)
        reset_plot2a_button.on_click(lambda: on_reset_plot2a())
        reset_plot2b_button.on_click(lambda: on_reset_plot2b())
        back_to_selection_button.on_click(on_back_to_selection_click)

        # Create tools column with conditional z-range display (range inputs moved above plots)
        tools_items = [
            x_slider,
            y_slider,
            Div(text="<b>Map Shape:</b>", width=200),
            map_shape_selector,
            custom_map_controls,
            aspect_ratio_controls,
            map_size_limits_controls,
            Div(text="<b>Map Color Scale:</b>", width=200),
            map1_color_scale_selector,
            Div(text="<b>Probe Color Scale:</b>", width=200),
            map2_color_scale_selector,
            Div(text="<b>Plot3 Color Scale:</b>", width=200),
            map3_color_scale_selector,
            status_div,
        ]
        
        # Add z-range display for 3D volumes
        if is_3d_volume and z_range_display is not None:
            tools_items.append(z_range_display)
            
        tools_items.extend([
            Div(text="<b>Color Palette:</b>", width=200),
            palette_selector,
            reset_ranges_button,
            back_to_selection_button,
        ])
        
        tools = column(*tools_items, width=400)
        
        # Create range input sections for each plot
        # Plot1 range inputs
        plot1_range_section = column(
            Div(text="<b>Map Range:</b>", width=200),
            row(range1_min_input, range1_max_input),
            sizing_mode="stretch_width"
        )
        
        # Plot1B range inputs (if exists)
        plot1b_range_section = None
        if 'range1b_min_input' in locals() and range1b_min_input is not None:
            plot1b_range_section = column(
                Div(text="<b>Map1B Range:</b>", width=200),
                row(range1b_min_input, range1b_max_input),
                sizing_mode="stretch_width"
            )
        
        # Plot2 range inputs
        plot2_range_section = column(
            Div(text="<b>Probe Range:</b>", width=200),
            plot2_range_mode_toggle,
            row(range2_min_input, range2_max_input),
            sizing_mode="stretch_width"
        )
        
        # Plot2B range inputs (if exists)
        plot2b_range_section = None
        if 'range2b_min_input' in locals() and range2b_min_input is not None:
            plot2b_range_section = column(
                Div(text="<b>Probe2B Range:</b>", width=200),
                plot2b_range_mode_toggle if plot2b_range_mode_toggle is not None else Div(text=""),
                row(range2b_min_input, range2b_max_input),
                sizing_mode="stretch_width"
            )
        elif plot2b_range_mode_toggle is not None:
            # Plot2B exists but is 1D (no range inputs), still show toggle
            plot2b_range_section = column(
                Div(text="<b>Probe2B Range:</b>", width=200),
                plot2b_range_mode_toggle,
                sizing_mode="stretch_width"
            )
        
        # Plot3 range inputs
        plot3_range_section = column(
            Div(text="<b>Plot3 Range:</b>", width=200),
            row(range3_min_input, range3_max_input),
            sizing_mode="stretch_width"
        )
        
        # Stack optional Plot1B under Plot1 and Plot2B under Plot2
        # Add spacers to align plot tops - Plot2 has toggle + button row, so it needs less spacer
        # Plot1 and Plot3 need spacers to match Plot2's header height
        # Approximate heights: range section ~60px, toggle ~30px, button row ~40px
        plot1_spacer = Div(text="", height=70)  # Spacer to align with Plot2's toggle + button row
        plot3_spacer = Div(text="", height=70)  # Spacer to align with Plot2's toggle + button row
        
        # Add spacers to align Plot1B and Plot2B
        # Plot1B comes after plot1, Plot2B comes after plot2 + button row
        # To align them, Plot1B needs a spacer to match Plot2's button row height before Plot2B
        plot1b_spacer = Div(text="", height=100)  # Spacer to align Plot1B with Plot2B (matches button row height)
        
        # Build Plot1 column with range inputs above
        plot1_column_items = [plot1_range_section, plot1_spacer, plot1]
        if 'plot1b' in locals() and plot1b is not None:
            plot1_column_items.append(plot1b_spacer)  # Add spacer before Plot1B to align with Plot2B
            if plot1b_range_section:
                plot1_column_items.append(plot1b_range_section)
            plot1_column_items.append(plot1b)
        plot1_column = column(*plot1_column_items, sizing_mode="scale_width")
        # Build Plot2 column with range inputs above and append Plot2B controls if present
        if 'plot2b' in locals() and plot2b is not None:
            plot2_column_items = [
                plot2_range_section,
                row(compute_plot3_image_button, reset_plot2a_button, plot3_status_div_a),
                plot2,
            ]
            if plot2b_range_section:
                plot2_column_items.append(plot2b_range_section)
            plot2_column_items.extend([
                row(compute_plot3_from_plot2b_button, reset_plot2b_button, plot3_status_div_b),
                plot2b,
            ])
            plot2_column = column(*plot2_column_items, sizing_mode="scale_width")
        else:
            plot2_column = column(
                plot2_range_section,
                row(compute_plot3_image_button, reset_plot2a_button, plot3_status_div_a),
                plot2,
                sizing_mode="scale_width",
            )
        
        # Build Plot3 column with range inputs above
        # Note: Plot3's button row is positioned after the plot, so we need a smaller spacer
        # Plot2 has: range + toggle + button_row before plot
        # Plot3 has: range + button_row before plot (button_row is actually after plot in original, but we'll move it)
        # For alignment, Plot3 needs spacer to match Plot2's toggle height (~30px)
        plot3_spacer_adjusted = Div(text="", height=30)  # Just to match the toggle height
        plot3_column = column(
            plot3_range_section,
            plot3_spacer_adjusted,
            row(compute_plot2_image_button, plot2_status_div),
            plot3,
            row(compute_plot2b_image_button, plot2b_status_div),
            sizing_mode="scale_width",
        )
        
        # Create the layout - Three columns for Plot1, Plot2, and Plot3
        plots_row = row(
                    plot1_column,
                    plot2_column,
                    plot3_column,
                    sizing_mode="stretch_both",
        )
        dashboard_layout = column(
            row(
                tools,
                plots_row,
                sizing_mode="stretch_width",
            ), 
            status_display,  
        )

        return dashboard_layout
        
    except Exception as e:
        import traceback
        error_msg = str(e) if e else "Unknown error"
        print(f"Error in create_dashboard: {error_msg}")
        print("Full traceback:")
        traceback.print_exc()
        return Div(text=f"<h2>Error Loading Dashboard</h2><p>Error: {error_msg}</p><pre>{traceback.format_exc()}</pre>")

def find_nxs_files(directory):
    print(f"🔍 DEBUG: find_nxs_files() called with directory: {directory}")
    print(f"🔍 DEBUG: directory type: {type(directory)}")
    
    if directory is None:
        print("❌ ERROR: directory is None!")
        return []
    
    print(f"🔍 DEBUG: Starting os.walk on: {directory}")
    nxs_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.nxs'):
                nxs_files.append(os.path.join(root, file))
    return nxs_files

def find_nexus_and_mmap_files():
    global base_dir
    print(f"🔍 DEBUG: find_nexus_and_mmap_files() called")
    print(f"🔍 DEBUG: base_dir = {base_dir}")
    print(f"🔍 DEBUG: base_dir type = {type(base_dir)}")
    
    if base_dir is None:
        print("❌ ERROR: base_dir is None!")
        return None, None
    
    print(f"🔍 DEBUG: Searching for .nxs files in: {base_dir}")
    nxs_files = find_nxs_files(base_dir)
    print(f"🔍 DEBUG: Found {len(nxs_files)} .nxs files")
    
    if len(nxs_files) > 0:
        nexus_filename = nxs_files[0]
        mmap_filename = nexus_filename.replace('.nxs', '.float32.dat')
    else:
        nxs_files = find_nxs_files(save_dir)
        if len(nxs_files) > 0:
            nexus_filename = nxs_files[0]
            mmap_filename = nexus_filename.replace('.nxs', '.float32.dat')
        else:
            nxs_files = find_nxs_files(save_dir)
        print("No Nexus files found")
        return None, None
   
    print(f"🔍 DEBUG: nexus_filename = {nexus_filename}")
    print(f"🔍 DEBUG: mmap_filename = {mmap_filename}")

    return nexus_filename, mmap_filename

def scientistCloudInitDashboard():
    """Initialize the dashboard."""
  # Clear status messages
    global status_messages, curdoc,  request, has_args
    global DATA_IS_LOCAL, uuid, server, name, is_authorized, auth_result
    global base_dir, save_dir, user_email, mymongodb, collection, collection1, team_collection
    
    status_messages = []
    doc = curdoc()
    
    # Check if running with URL arguments - if no args, we're in local mode
    request = doc.session_context.request if hasattr(doc, 'session_context') and doc.session_context else None
    has_args = request and request.arguments and len(request.arguments) > 0
    DATA_IS_LOCAL = not has_args
    

    # Production mode - use utility initialization
    # Initialize dashboard using utility
    init_result = initialize_dashboard(request, add_status_message)
    
    if not init_result['success']:
        add_status_message(f"❌ Dashboard initialization failed: {init_result['error']}")
        return
    
    if (DATA_IS_LOCAL):
        save_dir = local_base_dir
        base_dir = local_base_dir
    else:
        # Extract initialization results
        auth_result = init_result['auth_result']
        mongodb = init_result['mongodb']
        params = init_result['params']
        
        # Set global variables from initialization
        uuid = params['uuid']
        server = params['server']
        name = params['name']
        save_dir = params['save_dir']
        base_dir = params['base_dir']
        is_authorized = auth_result['is_authorized']
        user_email = auth_result['user_email']

        print(f"🔍 DEBUG: scientistCloudInitDashboard() called")
        print(f"🔍 DEBUG: uuid = {uuid}")
        print(f"🔍 DEBUG: server = {server}")
        print(f"🔍 DEBUG: name = {name}")
        print(f"🔍 DEBUG: save_dir = {save_dir}")
        print(f"🔍 DEBUG: base_dir = {base_dir}")
        print(f"🔍 DEBUG: is_authorized = {is_authorized}")
        print(f"🔍 DEBUG: user_email = {user_email}")
        
        # Check if user is authorized
        if not is_authorized:
            error_message = auth_result.get('message', 'Access denied')
            print(f"❌ Authorization failed: {error_message}")
            error_div = Div(text=f"""
                <div style="text-align: center; padding: 50px; background-color: #f8f9fa; border: 2px solid #dc3545; border-radius: 10px; margin: 20px;">
                    <h2 style="color: #dc3545;">🚫 Access Denied</h2>
                    <p style="font-size: 16px; color: #6c757d;">{error_message}</p>
                    <p style="font-size: 14px; color: #6c757d; margin-top: 20px;">
                        If you believe you should have access to this dataset, please contact the dataset owner.
                    </p>
                </div>
            """, styles={'width': '100%', 'height': '100%'})
            return error_div
        
        # Set MongoDB variables if available
        if mongodb:
            mymongodb = mongodb['mymongodb']
            collection = mongodb['collection']
            collection1 = mongodb['collection1']
            team_collection = mongodb['team_collection']


# ////////////////////////////////////////////////////////////////
if True:  
    # bokeh serve bokeh/4d_dashboard.py --port 5016 --allow-websocket-origin=localhost:5016
    scientistCloudInitDashboard()

    nexus_filename, mmap_filename = find_nexus_and_mmap_files(  )

    # Create the processor object (but don't load data yet)
    process_4dnexus = Process4dNexus(nexus_filename, mmap_filename, cached_cast_float=True, status_callback=add_status_message)
    #process_4dnexus.status_message = status_messages
    # Start with the temporary dashboard for dataset selection
    dashboard = create_tmp_dashboard(process_4dnexus)
    curdoc().add_root(dashboard)
