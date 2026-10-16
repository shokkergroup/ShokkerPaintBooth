"""Lane S - UI shots, part 2: zone popout sections, centre column, layers, menus, pickers. Group: ui."""
import enc_screens as E
from enc_screens import shot
from enc_screens_ui import crop

L = {"at": "l", "dx": -12}
POP = [192, 150, 470, 830]      # the zone popout panel (header + scrolling body)


def popout(c, sid, title, caption, arts, scroll, block, marks, labels, alt):
    E.tidy(c, 0)
    c.scroll_to(scroll, block)
    crop(c, sid, title, caption, arts, POP, marks, labels, alt)


@shot("ui", "ui_zone_popout_color")
def ui_zone_popout_color(c):
    popout(c, "ui_zone_popout_color", "Zone popout: COLOR and APPLY AREA", "The top of the zone popout panel: which pixels this zone covers.",
           ["zones.popout_panel", "zones.how_pixels_picked", "zones.add_pick_colour", "zones.restrict_layers", "zones.tolerance"],
           "#sectionColor0", "start",
           [(1, "button::reset zone"), (2, "#sectionColor0 .section-header"), (3, "#sectionColor0 *::restrict to layers"), (4, "button::pick color from car"),
            (5, "#zoneEditorFloat input[placeholder*='FF3366' i]"), (6, "label::hard edge"), (7, "#sectionApplyArea0 .section-header")],
           ["Reset Zone", "COLOR section", "RESTRICT TO LAYERS list", "PICK COLOR FROM CAR", "HEX box", "Hard Edge", "APPLY AREA section"],
           "The top of the zone popout panel with seven numbered callouts.")


@shot("ui", "ui_zone_base_material")
def ui_zone_base_material(c):
    popout(c, "ui_zone_base_material", "Zone popout: BASE material and colour sliders", "The BASE section: the material, where its colour comes from, and the colour sliders.",
           ["finishes.base_colour_tuning", "finishes.colour_source_modes", "finishes.foundation_shine_only", "finishes.picker_library_browser", "zones.popout_panel"],
           "#sectionBase0", "start",
           [(1, "#sectionBase0 .swatch-trigger"), (2, "#sectionBase0 select"), (3, "#sectionBase0 *::hue shift", L), (4, "#sectionBase0 *::saturation", L),
            (5, "#sectionBase0 *::brightness", L), (6, "#sectionBase0 *::base strength", L), (7, "#sectionBase0 *::spec strength", L), (8, "#sectionBase0 *::base scale", L), (9, "#sectionBase0 *::base rotation", L)],
           ["Base material (click to choose a finish)", "BASE COLOR source (here: Use source paint, spec only)", "Hue Shift", "Saturation", "Brightness", "Base Strength", "Spec Strength", "Base Scale", "Base Rotation"],
           "The BASE section of the zone popout with nine numbered callouts.")


@shot("ui", "ui_zone_base_more")
def ui_zone_base_more(c):
    popout(c, "ui_zone_base_more", "Zone popout: depth, flip, underglow, spec scale", "The lower BASE controls: Color Depth, Color Flip, Underglow, Spec Scale, Spec Rotation and Spec Blend.",
           ["finishes.gradients_flip_depth_underglow", "spec.scale_rotation", "spec.blend_modes", "finishes.base_scale_rotation"],
           "#sectionBase0 *::spec scale", "center",
           [(1, "#sectionBase0 *::color de", L), (2, "#sectionBase0 *::color flip", L), (3, "#sectionBase0 *::underglow", L), (4, "#sectionBase0 *::spec scale", L),
            (5, "#sectionBase0 *::spec rotation", L), (6, "#sectionBase0 *::spec blend", L)],
           ["Color Depth", "Color Flip", "Underglow", "Spec Scale", "Spec Rotation", "Spec Blend (how the spec combines)"],
           "The lower BASE controls with six numbered callouts.")


@shot("ui", "ui_zone_rgb_sliders")
def ui_zone_rgb_sliders(c):
    popout(c, "ui_zone_rgb_sliders", "Zone popout: R, G and B channel sliders", "Push the metal, roughness and clearcoat channels of a zone up or down.",
           ["spec.channel_sliders", "spec.channel_r_metallic", "spec.channel_g_roughness", "spec.channel_b_clearcoat"],
           "#zoneEditorFloat *::r metal", "center",
           [(1, "#zoneEditorFloat *::r metal", L), (2, "#zoneEditorFloat *::g rough", L), (3, "#zoneEditorFloat *::b coat", L)],
           ["R Metal slider", "G Rough slider", "B Coat slider"], "The three channel sliders R Metal, G Rough and B Coat with numbered callouts.")


@shot("ui", "ui_zone_spec_overlays")
def ui_zone_spec_overlays(c):
    popout(c, "ui_zone_spec_overlays", "Zone popout: spec overlays and pattern", "Add a spec overlay (detail in how the surface reflects) or a paint pattern.",
           ["spec.overlays_stack", "spec.pattern_groups", "patterns.what_is_a_pattern", "patterns.layers_and_stacking"],
           "#sectionSpecPatterns0", "start",
           [(1, "#sectionSpecPatterns0 *::spec overlays"), (2, "button::add spec overlay"), (3, "#sectionPattern0 .section-header"), (4, "#sectionPattern0 button::add layer")],
           ["SPEC OVERLAYS (up to 5)", "+ ADD SPEC OVERLAY", "PATTERN section", "+ Add Layer (pattern)"], "Spec overlays and pattern sections with four numbered callouts.")


@shot("ui", "ui_zone_overlays")
def ui_zone_overlays(c):
    popout(c, "ui_zone_overlays", "Zone popout: second base and overlays", "The OVERLAYS section: a second base material blended over the first.",
           ["finishes.second_base_overlays", "zones.priority"],
           "#sectionOverlays0 *::add 3rd overlay", "end",
           [(1, "#sectionOverlays0 .section-header"), (2, "#sectionOverlays0 *::2nd base overlay"), (3, "button::add 3rd overlay")],
           ["OVERLAYS (5-layer material stack)", "2ND BASE OVERLAY", "+ Add 3rd overlay"],
           "The OVERLAYS section with four numbered callouts.")


@shot("ui", "ui_render_bar")
def ui_render_bar(c):
    E.tidy(c, 0)
    marks = [(1, "#btnRender"), (2, "#eyedropperSwatch"), (3, "#eyedropperAddColorBtn"), (4, "#eyedropperExcludeBtn"), (5, "#eyedropperSetBtn"),
             (6, "#useRegionBtn"), (7, "#zoomLevel"), (8, "#btnSourceFocus")]
    crop(c, "ui_render_bar", "The RENDER bar", "The RENDER button, the colour picker readout and the zoom controls above the preview.",
         ["preview_render.render_button", "zones.add_pick_colour", "zones.exclude_set_use_region", "tools.zoom_pan"], "#previewBottomBar", marks,
         ["RENDER", "Colour picked from the car", "+ Add Color", "Exclude", "Set", "Use Region", "Zoom", "Edit Big"], "The render bar with eight numbered callouts.")


@shot("ui", "ui_spec_strip")
def ui_spec_strip(c):
    d = c.need("#specChannelDock")
    w = d[2] / 4
    marks = [(i + 1, [d[0] + i * w + 4, d[1], w - 8, d[3]], {"at": "tl"}) for i in range(4)]
    crop(c, "ui_spec_strip", "The spec channel strip", "Four small views of the same car: the combined picture and the R METAL, G ROUGH and B COAT channels.",
         ["ui_shell.preview_channel_views", "spec.what_is_spec_map", "spec.reading_by_colour", "spec.channel_r_metallic"], "#previewTopStrip", marks,
         ["COMBINED (all channels as colour)", "R METAL (brighter = more metal)", "G ROUGH (brighter = rougher)", "B COAT (brighter = duller clearcoat)"],
         "The four spec channel views under the preview.", kind="spec_view")


@shot("ui", "ui_source_and_live")
def ui_source_and_live(c):
    marks = [(1, "#splitSource", {"at": "tl"}), (2, "#splitPreview", {"at": "tl"}), (3, "#btnPreviewRefresh"), (4, "#zoomControls")]
    crop(c, "ui_source_and_live", "SOURCE and LIVE PREVIEW", "Left is your paint as loaded; right is what the zones do to it.",
         ["ui_shell.canvas_overlays", "preview_render.preview_vs_render", "workflows.one_flat_sheet"], "#previewSquaresRow", marks,
         ["SOURCE (your loaded paint)", "LIVE PREVIEW (with your zones applied)", "Refresh", "Zoom controls"], "Source paint and live preview side by side.")


@shot("ui", "ui_tool_options")
def ui_tool_options(c):
    E.tidy(c, 0)
    c.click("#vtModeBrush", 900)
    names = ["size:", "opacity:", "hard:", "flow:", "spacing:"]
    marks = [(i + 1, "#toolOptionsBar *::" + n, {"at": "b", "dy": 6, "box": False}) for i, n in enumerate(names)]
    labels = ["Size", "Opacity", "Hardness", "Flow", "Spacing"]
    crop(c, "ui_tool_options", "The tool options bar", "The strip under the preview changes with the tool you pick. This is the Brush: size, hardness, opacity and more.",
         ["ui_shell.tool_options_bar", "tools.brush_eraser"], "#toolOptionsBar", marks, labels, "The tool options bar for the Brush tool with numbered callouts.", pad=6)
    c.click("#vtModePickItem", 500)


@shot("ui", "ui_layers_column")
def ui_layers_column(c):
    marks = [(1, "button::open layered"), (2, "button::+ layer"), (3, "#layerActionsMenuBtn"), (4, "#layerSearchInput"), (5, ".layer-group-header::turn off before"),
             (6, ".layer-row::wire"), (7, ".layer-group-header::paintable area"), (8, ".layer-row::tape")]
    crop(c, "ui_layers_column", "The LAYERS column", "Every layer of the loaded template, grouped.",
         ["layers.panel", "layers.roles", "layers.turn_off_before_export", "layers.paintable_area"], "#rightPanel", marks,
         ["Open Layered (load a PSD)", "+ Layer", "Actions menu", "Layer filter", "Group: Turn Off Before Exporting TGA", "Wire layer (template guide)", "Group: Paintable Area", "A paintable layer (Tape)"],
         "The right column showing the layers with eight numbered callouts.")
