# 4D Dashboard Refactoring Plan

## Overview
The `create_dashboard` function is ~6000 lines long and difficult to maintain. This document outlines the refactoring plan to break it into manageable pieces.

## What Has Been Created

### 1. `DashboardBuilder` Class (`4d_dashboard_builder.py`)
A new class that encapsulates dashboard creation logic:

- **`load_data()`** - Loads data from nexus file
- **`create_session()`** - Creates plot session and state history
- **`create_plot1()`** - Creates Plot1 using `MAP_2DPlot`
- **`create_plot2()`** - Creates Plot2 using `PROBE_1DPlot` or `PROBE_2DPlot`
- **`create_plot3()`** - Creates Plot3 using `MAP_2DPlot` or `PROBE_2DPlot`
- **`setup_callbacks()`** - Sets up all inter-plot callbacks
- **`create_controls()`** - Creates all UI controls
- **`create_layout()`** - Creates the final layout
- **`build()`** - Main entry point that orchestrates all steps

### 2. Integration Point
Updated `4d_dashboardLiteImprove.py` to import `DashboardBuilder` with a TODO comment showing how to use it.

## What Should Be Pushed to Specialized Plots

### Current State
The specialized plot classes (`MAP_2DPlot`, `PROBE_2DPlot`, `PROBE_1DPlot`) currently:
- ✅ Manage plot state (data, coordinates, ranges, colors, etc.)
- ✅ Provide state serialization (save/load JSON)
- ✅ Handle coordinate flipping logic
- ❌ Do NOT create Bokeh figures directly

### Recommended Additions to Specialized Plots

#### 1. Bokeh Figure Creation Methods
Add methods to `BasePlot` or specialized classes to create Bokeh figures:

```python
# In BasePlot or specialized classes
def create_bokeh_figure(self) -> Tuple[Figure, ColumnDataSource, ColorMapper]:
    """
    Create a Bokeh figure, data source, and color mapper from plot state.
    
    Returns:
        Tuple of (figure, source, color_mapper)
    """
    # Implementation would:
    # 1. Create Bokeh figure with appropriate tools
    # 2. Create ColumnDataSource from data
    # 3. Create ColorMapper based on range_mode, color_scale, palette
    # 4. Add image/line glyphs based on data_mode
    # 5. Configure axes, labels, ticks
    # 6. Add crosshairs if enabled
    # 7. Add selection regions if enabled
    pass

def update_bokeh_figure(self, figure, source, color_mapper):
    """
    Update existing Bokeh figure components when plot state changes.
    """
    pass
```

#### 2. Callback Helper Methods
Add methods to handle common callback patterns:

```python
# In specialized classes
def create_range_update_callback(self, range_inputs):
    """
    Create callback for updating plot range from UI inputs.
    """
    pass

def create_data_update_callback(self, new_data):
    """
    Create callback for updating plot data.
    """
    pass
```

#### 3. Inter-Plot Communication
Consider adding methods for plot-to-plot interactions:

```python
# In specialized classes
def get_selection_region(self) -> Optional[Tuple[float, float, float, float]]:
    """
    Get current selection region coordinates (x_min, x_max, y_min, y_max).
    """
    pass

def set_crosshair_position(self, x: float, y: float):
    """
    Update crosshair position (for Plot1 -> Plot2 interaction).
    """
    pass
```

## Migration Strategy

### Phase 1: Structure (Current)
- ✅ Created `DashboardBuilder` class structure
- ✅ Identified methods to extract
- ✅ Created integration point in Improve file

### Phase 2: Plot Creation
- [ ] Implement `create_plot1()` using `MAP_2DPlot`
- [ ] Implement `create_plot2()` using `PROBE_1DPlot`/`PROBE_2DPlot`
- [ ] Implement `create_plot3()` using `MAP_2DPlot`/`PROBE_2DPlot`
- [ ] Add Bokeh figure creation methods to specialized plots OR
- [ ] Create helper functions in builder to convert plot state to Bokeh

### Phase 3: Callbacks
- [ ] Extract Plot1 click callback → `_setup_plot1_callbacks()`
- [ ] Extract Plot2 selection callback → `_setup_plot2_callbacks()`
- [ ] Extract Plot3 selection callback → `_setup_plot3_callbacks()`
- [ ] Extract inter-plot callbacks → `_setup_inter_plot_callbacks()`
- [ ] Extract slider callbacks → `_setup_slider_callbacks()`
- [ ] Extract range input callbacks → `_setup_range_callbacks()`

### Phase 4: Controls
- [ ] Extract control creation → `_create_sliders()`
- [ ] Extract control creation → `_create_range_inputs()`
- [ ] Extract control creation → `_create_color_controls()`
- [ ] Extract control creation → `_create_action_buttons()`

### Phase 5: Layout
- [ ] Extract layout creation → `_create_plot_layouts()`
- [ ] Extract layout creation → `_create_control_layouts()`
- [ ] Extract layout creation → `_assemble_final_layout()`

### Phase 6: Testing & Cleanup
- [ ] Test refactored version matches old behavior
- [ ] Remove old implementation
- [ ] Update documentation

## Benefits

1. **Easier to Edit**: Small, focused methods instead of 6000-line function
2. **Less Indentation Errors**: Smaller code blocks = fewer indentation mistakes
3. **Better Testing**: Each method can be tested independently
4. **Reusability**: Methods can be reused or overridden
5. **Maintainability**: Clear separation of concerns

## Next Steps

1. **For Demo (30 min)**: Keep old implementation working, builder structure is ready
2. **After Demo**: Start Phase 2 - implement plot creation methods
3. **Gradual Migration**: Move functionality piece by piece, test after each change

## Notes

- The specialized plot classes are state management classes, not UI classes
- The builder creates the actual Bokeh UI and syncs it with plot state
- This separation allows plot state to be saved/loaded independently of UI
- Consider adding a `PlotRenderer` class that handles Bokeh figure creation from plot state





