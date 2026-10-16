"""Lane S - UI panel shots with numbered callouts. Group: ui (the Pro window; Easy mode is never shown)."""
import enc_screens as E
from enc_screens import shot, emit


def crop(c, sid, title, caption, arts, region, marks, labels, alt, pad=0, maxw=1200, kind="ui"):
    im = c.grab(region, marks, pad=pad)
    return emit(sid, title, caption, kind, arts, im, alt, labels, maxw=maxw)


@shot("ui", "ui_window_tour")
def ui_window_tour(c):
    E.tidy(c, 0)
    marks = [(1, "#iracingIdContainer", {"dy": 24}), (2, "#spbModePill"), (3, "#spbTopToolbar", {"at": "tr", "dx": -24, "dy": 14}),
             (4, "#leftPanel", {"at": "tr", "dx": -8, "dy": 14}), (5, "#zoneEditorFloat"), (6, "#btnRender"), (7, "#previewTopStrip"),
             (8, "#splitSource"), (9, "#splitPreview"), (10, "#rightPanel")]
    crop(c, "ui_window_tour", "The whole window, labelled", "The Pro window with a layered paint loaded and four zones set up.",
         ["ui_shell.window_tour", "workflows.what_is_shokker", "workflows.one_flat_sheet", "workflows.first_paint"],
         [0, 0, 1700, 1000], marks,
         ["Header: iRacing User ID, Source Paint, car folder", "PRO / CHAT pill", "Tool row", "ZONES column", "Zone popout panel", "RENDER button",
          "Spec channel strip (COMBINED, R METAL, G ROUGH, B COAT)", "SOURCE paint", "LIVE PREVIEW", "Right column: layers"],
         "The full Shokker Paint Booth window with ten numbered callouts.", maxw=1400)


@shot("ui", "ui_header_rows")
def ui_header_rows(c):
    marks = [(1, "#iracingId"), (2, "#useCustomNumberCheckbox", {"at": "r", "dx": 72}), (3, "#useSimStampedCheckbox", {"at": "r", "dx": 72}),
             (4, "#paintFile"), (5, "button::tga/png/jpeg"), (6, "button::psd/xcf/ora"), (7, "#outputDir"), (8, "#carPickBtn")]
    crop(c, "ui_header_rows", "Header: User ID, Source Paint, car folder", "The top boxes that tell the app who you are, which paint to load and where your iRacing car folder is.",
         ["ui_shell.source_paint", "ui_shell.car_folder", "ui_shell.number_modes", "workflows.user_id_and_folder", "workflows.loading_paint"],
         [200, 0, 800, 56], marks,
         ["iRacing User ID", "CUSTOM NUMBER checkbox", "SIM-STAMPED NUMBER checkbox", "SOURCE PAINT box", "TGA/PNG/JPEG button", "PSD/XCF/ORA button", "IRACING CAR FOLDER box", "Pick detected iRacing car arrow"],
         "The header rows with eight numbered callouts on the User ID, number checkboxes, Source Paint and car folder boxes.")


@shot("ui", "ui_mode_pill")
def ui_mode_pill(c):
    marks = [(1, "#spbModeProBtn"), (2, "#spbModeChatBtn"), (3, "#uiScaleLabel", {"at": "b", "dy": 2})]
    crop(c, "ui_mode_pill", "The PRO / CHAT pill", "Pick your door: PRO is the full paint shop, CHAT is the guided front door.",
         ["ui_shell.mode_pill", "workflows.pro_or_chat"], [200, 52, 270, 48], marks,
         ["PRO", "CHAT", "UI size (percent)"], "The PRO and CHAT buttons with the interface size control beside them.")


@shot("ui", "ui_top_bar_buttons")
def ui_top_bar_buttons(c):
    marks = [(1, ".header-command-btn::spec sculpt"), (2, ".header-command-btn::shokk drop"), (3, "#btnSpbEncyclopedia"), (4, "#btnFractureThisPaint")]
    crop(c, "ui_top_bar_buttons", "Top-bar buttons", "The row of big buttons under the header: Spec Sculpt, Shokk Drop, Encyclopedia and Fracture This Paint.",
         ["ui_shell.top_bar_buttons", "shokk_drop.fracture_this_paint"], [430, 52, 560, 48], marks,
         ["SPEC SCULPT", "Shokk Drop", "Encyclopedia", "FRACTURE THIS PAINT"], "Four header buttons with numbered callouts.")


@shot("ui", "ui_toolbar_tools")
def ui_toolbar_tools(c):
    marks, labels = c.auto("#vtModeLayerMove, #vtModePickItem, #vtModeEyedropper, #vtModeWand, #vtModeLasso, #vtModeRect, #vtModeBrush, #vtModeFill, #vtModeErase", 9, at="b", dy=-2)
    crop(c, "ui_toolbar_tools", "The tool buttons", "The tool row: Move, Pick, Color, Wand, Lasso, Rect, Brush, Fill and Erase.",
         ["tools.select_shapes", "tools.eyedropper_pick", "tools.brush_eraser", "tools.fill_bucket", "tools.move_transform", "zones.add_pick_colour"],
         [204, 96, 450, 60], marks, ["Move", "Pick", "Color (eyedropper)", "Wand", "Lasso", "Rect", "Brush", "Fill", "Erase"], "Nine tool buttons numbered in a row.")


@shot("ui", "ui_toolbar_menus")
def ui_toolbar_menus(c):
    marks = [(1, "#spbTopToolbar summary::history"), (2, "#spbTopToolbar summary::select"), (3, "#spbRetouchMenu"), (4, "#spbTopToolbar summary::mask"),
             (5, "#spbTopToolbar summary::transform"), (6, "#spbTopToolbar summary::adjust"), (7, "#toolbarEditModeGroup"), (8, "#spbRenderHistMenu")]
    crop(c, "ui_toolbar_menus", "Toolbar menus and ZONE / LAYER", "The menus on the tool row, and the ZONE / LAYER switch that decides what your tools edit.",
         ["tools.mask_vs_layer", "tools.undo_redo", "tools.retouch", "tools.refine_selection", "ui_shell.tool_options_bar", "preview_render.render_history_stats"],
         [650, 96, 800, 60], marks, ["HISTORY", "SELECT", "RETOUCH", "MASK", "TRANSFORM", "ADJUST", "ZONE / LAYER switch", "RENDER HISTORY"],
         "The toolbar menus with eight numbered callouts.", pad=0)


@shot("ui", "ui_toolbar_right")
def ui_toolbar_right(c):
    marks = [(1, "#spbGuideToggle"), (2, "#settingsGearBtn"), (3, "#spbProjectsButton"), (4, "button::import recipe")]
    crop(c, "ui_toolbar_right", "Tutorial, Settings, Save / Open", "The right end of the top bar: Tutorial, Settings, Save / Open and Import Recipe.",
         ["ui_shell.save_open_projects", "settings.overview", "workflows.tutorial_quests"], [1430, 24, 270, 130], marks,
         ["TUTORIAL", "SETTINGS", "Save / Open", "Import Recipe"], "Four buttons at the top right with numbered callouts.")


@shot("ui", "ui_zones_column")
def ui_zones_column(c):
    E.tidy(c, 0)
    marks = [(1, "#zoneCount", {"at": "r", "dx": 4}), (2, "#zone-card-0"), (3, "#zone-card-3"), (4, "#zone-card-4"), (5, "button::add zone"),
             (6, "button::reset all zones"), (7, ".zone-more-btn")]
    crop(c, "ui_zones_column", "The ZONES column", "Every zone is a card. The top card wins where zones overlap.",
         ["zones.what_is_a_zone", "zones.priority", "zones.everything_else", "zones.card_controls"], "#leftPanel", marks,
         ["Zone count", "Zone 1 (top priority)", "Zone 4", "Everything Else (catch-all, last)", "+ Add Zone", "Reset All Zones", "More menu"],
         "The left column listing five zones with numbered callouts.", pad=0)


@shot("ui", "ui_zone_card")
def ui_zone_card(c):
    marks = [(1, "#zone-card-0 .zone-drag-handle", {"at": "l", "dx": -6}), (2, "#zone-card-0 .zone-number"), (3, "#zone-card-0 .zone-name-input", {"at": "tr"}),
             (4, "#zone-card-0 .zone-mute-btn"), (5, "#zone-card-0 .zone-move-btn::⧉"), (6, "#zone-card-0 .zone-move-btn::☍"), (7, "#zone-card-0 .zone-delete-btn")]
    crop(c, "ui_zone_card", "One zone card", "The small buttons on a zone card.",
         ["zones.card_controls", "zones.priority", "zones.what_is_a_zone"], "#zone-card-0", marks,
         ["Drag handle (reorder)", "Zone number (priority)", "Zone name", "Eye: switch the zone off or on", "Duplicate", "Link to another zone", "Delete"],
         "A single zone card with seven numbered callouts.", pad=10)
