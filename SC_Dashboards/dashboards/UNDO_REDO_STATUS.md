# Undo/Redo Status for 4D Dashboard

## Currently Tracked (Can be Undone/Redone)

### Plot Configuration Changes
1. **Range Mode Changes** (Dynamic/User Specified)
   - Location: `on_range1_mode_change()` 
   - Saves: `plot1_history.save_state("Range mode changed")` and `session_history.save_state()`
   - Status: ✅ Tracked

2. **Range Value Changes** (Min/Max inputs)
   - Location: `on_range1_min_change()` and `on_range1_max_change()`
   - Saves: `debounced_save_state("Range changed")` (0.5s debounce)
   - Status: ✅ Tracked

3. **Color Scale Changes** (Linear/Log)
   - Location: `on_color_scale_change()`
   - Saves: `plot1_history.save_state("Color scale changed")` and `session_history.save_state()`
   - Status: ✅ Tracked for Plot1, Plot1B, Plot2, Plot2B, Plot3

4. **Palette Changes**
   - Location: `on_palette_change()`
   - Saves: `plot1_history.save_state("Palette changed")` and `session_history.save_state()`
   - Status: ✅ Tracked for Plot1, Plot1B, Plot2, Plot2B, Plot3

5. **Plot Shape Changes**
   - Location: `on_plot1_shape_change()`
   - Saves: `plot1_history.save_state("Plot shape changed")` and `session_history.save_state()`
   - Status: ✅ Tracked

6. **Plot Size Changes** (Width, Height, Scale, Min Size, Max Size)
   - Locations: `on_plot1_custom_width_change()`, `on_plot1_custom_height_change()`, etc.
   - Saves: Individual state saves for each property
   - Status: ✅ Tracked

## Currently NOT Tracked (Cannot be Undone/Redone)

### Data Navigation
1. **X/Y Slider Changes**
   - Location: `on_x_slider_change()` and `on_y_slider_change()`
   - Current behavior: Updates crosshairs and slices, but does NOT save state
   - Status: ❌ NOT tracked
   - Impact: Users cannot undo slider movements to return to previous slice

2. **Plot Click/Tap Events**
   - Location: `on_plot1_tap()` and similar handlers
   - Current behavior: Updates sliders and crosshairs, but does NOT save state
   - Status: ❌ NOT tracked
   - Impact: Users cannot undo clicking on a plot to change the slice

3. **Plot Range Changes** (Zoom/Pan)
   - Location: `on_plot1_range_change()` and `on_plot1b_range_change()`
   - Current behavior: Updates sliders, but does NOT save state
   - Status: ❌ NOT tracked
   - Impact: Users cannot undo zoom/pan operations

### Data Selection and Computation
4. **BoxSelectTool Selections**
   - Location: BoxSelectTool event handlers for Plot2, Plot2B, Plot3
   - Current behavior: Updates data selection, but does NOT save state
   - Status: ❌ NOT tracked
   - Impact: Users cannot undo region selections

5. **Compute Plot3 from Plot2**
   - Location: `compute_plot3_button` click handler
   - Current behavior: Computes new Plot3 data, but does NOT save state
   - Status: ❌ NOT tracked
   - Impact: Users cannot undo computing Plot3 from a Plot2 selection

6. **Compute Plot2 from Plot3**
   - Location: Similar handler for reverse computation
   - Current behavior: Computes new Plot2 data, but does NOT save state
   - Status: ❌ NOT tracked
   - Impact: Users cannot undo computing Plot2 from a Plot3 selection

7. **Reset Plot2/Plot2B**
   - Location: `reset_plot2_button` and `reset_plot2b_button` click handlers
   - Current behavior: Resets to original data, but does NOT save state
   - Status: ❌ NOT tracked
   - Impact: Users cannot undo reset operations

### Session Management
8. **Session Load**
   - Location: `on_load_session()`
   - Current behavior: Clears history and saves "Session loaded" state
   - Status: ⚠️ Partially tracked (clears history, so previous states are lost)
   - Impact: Loading a session wipes undo history

## State Management Details

### History Objects
- **`plot1_history`**: `PlotStateHistory` for Plot1 (map_plot)
- **`session_history`**: `SessionStateHistory` for entire session (all plots)
- **Max History**: 20 states (configured in `SessionStateHistory(session, max_history=20)`)

### Debouncing
- Range value changes use `debounced_save_state()` with 0.5s delay
- Other changes save immediately via `save_state_async()`

### What Gets Saved
- Plot configuration (ranges, colors, palettes, shapes, sizes)
- Session metadata
- Plot states (via `plot.get_state(include_data=False)`)
- Session state (via `session.get_session_state(include_data=False)`)

### What Does NOT Get Saved
- Data arrays (explicitly excluded with `include_data=False`)
- Slider positions
- Current slice indices
- Box selection regions
- Computed plot data (Plot2, Plot3)

## Recommendations for Improvement

### High Priority
1. **Track Slider Changes**: Add state save to `on_x_slider_change()` and `on_y_slider_change()`
   - Use debounced save (0.5s) to avoid excessive saves during dragging
   - Save current slice indices (x_index, y_index) in session state

2. **Track BoxSelectTool Selections**: Add state save when selection changes
   - Save selection geometry (min/max x/y) in plot state
   - Restore selection box when undoing

3. **Track Compute Operations**: Add state save when Plot2/Plot3 are computed
   - Save which plot was computed from which selection
   - May need to save computed data or at least metadata about the computation

### Medium Priority
4. **Track Plot Clicks**: Add state save to `on_plot1_tap()` handlers
   - Similar to slider changes, use debounced save

5. **Track Zoom/Pan**: Add state save to range change handlers
   - May want to debounce this heavily (1-2s) as it's very frequent during panning

6. **Preserve History on Session Load**: Don't clear history when loading
   - Instead, add loaded state to history
   - Allow undoing back to pre-load state

### Low Priority
7. **Track Reset Operations**: Add state save before reset
   - Save current state before resetting, so undo can restore it

## Implementation Notes

### Adding State Saves
To add undo/redo for a new operation:

1. **For frequent operations** (sliders, clicks):
   ```python
   debounced_save_state("Description", update_undo_redo=True)
   ```

2. **For infrequent operations** (mode changes, button clicks):
   ```python
   from bokeh.io import curdoc
   def save_state_async():
       plot1_history.save_state("Description")
       session_history.save_state("Description")
       undo_redo_callbacks["update"]()
   curdoc().add_next_tick_callback(save_state_async)
   ```

3. **For operations that need to save additional state**:
   - Update plot state before saving (e.g., `map_plot.select_region_min_x = ...`)
   - Or add to session metadata before saving

### State Restoration
- State is restored via `plot.load_state()` and `session.load_session_state()`
- UI widgets need to be updated after restore via `update_ui_after_state_change()`
- This function syncs all UI widgets to match the restored state
