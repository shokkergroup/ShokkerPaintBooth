"""Lane S - UI shots, part 3: dropdown menus, pickers, dialogs, layer cards, chat. Group: ui."""
import re

import enc_screens as E
from enc_screens import shot
from enc_screens_ui import crop


def clean(labels):
    return [re.sub(r"^[^\w(+]+", "", l).strip() for l in labels]


def pad_union(c, sels, pad=10):
    return c.union(sels, pad)


def menu_shot(c, sid, summary, title, caption, arts, alt):
    E.tidy(c, 0)
    c.click(summary, 700)
    pop = "details[open] .spb-tb-pop"
    marks, labels = c.auto(pop + " button", 12, at="l", dx=-9)
    region = c.union([summary, pop], 12)
    crop(c, sid, title, caption, arts, region, marks, clean(labels), alt)
    c.click(summary, 400)


@shot("ui", "ui_menu_history")
def ui_menu_history(c):
    menu_shot(c, "ui_menu_history", "#spbTopToolbar summary::history", "The HISTORY menu", "Undo, Redo and the Undo History panel.",
              ["tools.undo_redo"], "The HISTORY menu open with numbered items.")


@shot("ui", "ui_menu_select")
def ui_menu_select(c):
    menu_shot(c, "ui_menu_select", "#spbTopToolbar summary::select", "The SELECT menu", "More ways to pick pixels: Select All Color, Select Object, Smart Region Fill and more.",
              ["tools.select_shapes", "tools.selection_modes", "tools.refine_selection"], "The SELECT menu open with numbered items.")


@shot("ui", "ui_menu_mask")
def ui_menu_mask(c):
    menu_shot(c, "ui_menu_mask", "#spbTopToolbar summary::mask", "The MASK menu", "Select material area, paint area, exclude area and the mask stroke tools.",
              ["tools.mask_vs_layer", "tools.refine_selection", "zones.exclude_set_use_region"], "The MASK menu open with numbered items.")


@shot("ui", "ui_menu_transform")
def ui_menu_transform(c):
    menu_shot(c, "ui_menu_transform", "#spbTopToolbar summary::transform", "The TRANSFORM menu", "Free transform, rotate 90 degrees, flip and fit a layer to a selection.",
              ["tools.move_transform", "tools.mirror_symmetry"], "The TRANSFORM menu open with numbered items.")


@shot("ui", "ui_menu_adjust")
def ui_menu_adjust(c):
    menu_shot(c, "ui_menu_adjust", "#spbTopToolbar summary::adjust", "The ADJUST menu", "Brightness, hue, colour replace, invert, grayscale, gradient map and more.",
              ["layers.opacity_blend", "tools.retouch"], "The ADJUST menu open with numbered items.")


@shot("ui", "ui_zones_more_menu")
def ui_zones_more_menu(c):
    E.tidy(c, 0)
    c.click(".zone-more-btn", 700)
    marks, labels = c.auto("#zoneMoreMenu button", 10, at="l", dx=-8)
    region = c.union(["#zoneMoreMenu", ".zone-more-btn"], 10)
    crop(c, "ui_zones_more_menu", "Zones: the More menu", "Presets gallery, randomise, apply one finish to all zones, save as template and load a SHOKK file.",
         ["ui_shell.zones_more_menu", "zones.presets_templates", "shokk_drop.shokk_library_files"], region, marks, clean(labels),
         "The zone More menu open with numbered items.")
    c.click(".zone-more-btn", 400)


@shot("ui", "ui_settings_menu")
def ui_settings_menu(c):
    E.tidy(c, 0)
    c.js("() => { ['rightPanel', 'leftPanel'].forEach(i => { const e = document.getElementById(i); if (e) e.style.visibility = 'hidden'; }); return 1; }")   # the dropdown is translucent: show it over a clean backdrop
    c.click("#settingsGearBtn", 900)
    D = "#settingsDropdown "
    marks = [(1, D + "*::license", {"at": "l", "dx": -10}), (2, "#looksGrid"), (3, D + "select"), (4, D + "*::export zip package", {"at": "l", "dx": -10}),
             (5, D + "*::training wheels", {"at": "l", "dx": -10}), (6, D + "button::report a problem"), (7, D + "button::keyboard shortcuts"), (8, D + "button::import tga")]
    region = c.union(["#settingsDropdown"], 4)
    crop(c, "ui_settings_menu", "The SETTINGS dropdown", "Licence, looks, file picker and the other app settings.",
         ["settings.overview", "settings.looks_training_wheels", "settings.file_picker", "settings.activation_license"], region, marks,
         ["LICENSE", "LOOKS: pick your shop vibe", "File Picker (Shokker Browser or Windows File Explorer)", "Export ZIP Package", "Training Wheels", "Report a Problem", "Keyboard Shortcuts", "Import TGA (spec map)"],
         "The Settings dropdown with eight numbered callouts.")
    c.click("#settingsGearBtn", 400)
    c.js("() => { ['rightPanel', 'leftPanel'].forEach(i => { const e = document.getElementById(i); if (e) e.style.visibility = ''; }); return 1; }")


@shot("ui", "ui_finish_picker")
def ui_finish_picker(c):
    E.tidy(c, 0)
    c.scroll_to("#sectionBase0", "start")
    c.click("#sectionBase0 .swatch-trigger", 7000)
    marks = [(1, "#swatchPopup input[type=text], #swatchPopup input[type=search], #swatchPopup input"), (2, "#swatchPopup button::favorites"),
             (3, "#swatchPopup button::grouped"), (4, "#swatchPopup button::my rating"), (5, "#swatchPopup button::surprise me"), (6, "#swatchPopup button::close", {"at": "bl"})]
    crop(c, "ui_finish_picker", "The finish picker (SEARCH FINISHES)", "Click the base material and this full-screen picker opens: search, filter, then click a finish.",
         ["finishes.picker_library_browser", "finishes.catalogue_overview", "finishes.finish_cards"], [0, 0, 1700, 330], marks,
         ["Search box (names, ids, tags)", "Favorites", "Grouped (by shelf)", "My Rating", "Surprise Me", "Close"],
         "The top of the full-screen finish picker with six numbered callouts.", maxw=1400)
    try:
        c.click("#swatchPopup button::close", 600)
    except Exception:
        c.esc()


@shot("ui", "ui_finish_picker_cards")
def ui_finish_picker_cards(c):
    E.tidy(c, 0)
    c.scroll_to("#sectionBase0", "start")
    c.click("#sectionBase0 .swatch-trigger", 4000)
    c.click("#swatchPopup *::astra", 6500)
    marks = [(1, "#swatchPopup button::all categories"), (2, "*::abyssal lanterns", {"at": "b", "dy": 4}), (3, "#swatchPopup button::+", {"at": "bl"}),
             (4, "#swatchPopup input[type=range]", {"at": "l", "dx": -6})]
    crop(c, "ui_finish_picker_cards", "Inside a shelf: finish cards", "Open a shelf and every finish is a card: the left half of the swatch is the paint, the right half its spec map.",
         ["finishes.finish_cards", "finishes.picker_library_browser", "finishes.astra", "spec.what_is_spec_map"], [0, 0, 1700, 1000], marks,
         ["ALL CATEGORIES (back to the shelves)", "A finish card: name, shelf and a one-line look", "Add button (stack it as another layer)", "Strength slider on the card"],
         "The picker inside the ASTRA shelf showing finish cards with paint and spec swatches.", maxw=1400)
    try:
        c.click("#swatchPopup button::close", 600)
    except Exception:
        c.esc()


@shot("ui", "ui_layer_card_open")
def ui_layer_card_open(c):
    E.tidy(c, 0)
    c.click(".layer-row::tape", 900)
    marks = [(1, ".layer-row.selected"), (2, ".layer-row-details *::opacity", {"at": "l", "dx": -15}), (3, ".layer-row-details *::blend", {"at": "l", "dx": -15}),
             (4, ".layer-row-details *::hue", {"at": "l", "dx": -15}), (5, ".layer-row-details *::overlay", {"at": "l", "dx": -15}), (6, ".layer-row-details button::dupe"),
             (7, ".layer-row-details button::make zone"), (8, ".layer-row-details button::solo"), (9, ".layer-row-details button::lock zone"), (10, ".layer-row-details button::done")]
    region = c.union([".layer-row.selected", ".layer-row-details"], 8)
    crop(c, "ui_layer_card_open", "A layer card, opened", "Click a layer and its card opens with opacity, blend, colour tuning and action buttons.",
         ["layers.card_buttons", "layers.opacity_blend", "layers.lock_zone_to_layer", "layers.effects"], region, marks,
         ["Layer row", "Opacity", "Blend mode", "Hue / Sat / Bright", "Overlay colour", "DUPE (duplicate layer)", "MAKE ZONE", "SOLO", "LOCK ZONE", "DONE"],
         "An opened layer card with ten numbered callouts.")
    try:
        c.click(".layer-row-details button::done", 500)
    except Exception:
        pass


@shot("ui", "ui_layer_groups")
def ui_layer_groups(c):
    E.tidy(c, 0)
    marks = [(1, ".layer-group-header::turn off before", {"at": "tr", "dx": -14}), (2, ".layer-row::wire"), (3, ".layer-row::mask"), (4, ".layer-row::car mandatory"),
             (5, ".layer-group-header::paintable area", {"at": "tr", "dx": -14})]
    region = c.union([".layer-group-header::turn off before", ".layer-row::car mandatory", ".layer-group-header::paintable area"], 8)
    crop(c, "ui_layer_groups", "The template layers group", "Wire, Mask and Car Mandatory live in the Turn Off Before Exporting TGA group; your paintable layers are in the group below.",
         ["layers.turn_off_before_export", "layers.wire_mask_mandatory", "ui_shell.template_layer_views", "layers.paintable_area"], region, marks,
         ["Group: Turn Off Before Exporting TGA", "Wire", "Mask", "Car Mandatory", "Group: Paintable Area"],
         "The Wire, Mask and Car Mandatory layers shown switched off, with the Paintable Area group below.")


@shot("ui", "ui_chat_mode")
def ui_chat_mode(c):
    E.tidy(c, 0)
    c.click("#spbModeChatBtn", 4000)
    CS = "#spbChatStudio "
    marks = [(1, "#spbProAI", {"at": "tr", "dx": -14, "dy": 14}), (2, [880, 10, 270, 34]), (3, "#spbCsFrame", {"at": "tl"}), (4, "#spbCsStrip", {"at": "tl"}),
             (5, "#spbCsLayers", {"at": "tl"}), (6, "#spbCsChips", {"at": "tl"}), (7, CS + "button::render & save"), (8, CS + "button::full editor")]
    crop(c, "ui_chat_mode", "CHAT mode", "CHAT is the guided front door: the AI copilot on the left, your car in the middle, your layers on the right.",
         ["workflows.pro_or_chat", "ui_shell.mode_pill", "ai_copilot.chat_mode"], [0, 0, 1700, 1000], marks,
         ["AI copilot panel (type what you want)", "Paint / Shine (spec) / Car parts tabs", "The car", "SOURCE, LIVE PREVIEW and channel views", "LAYERS", "Your zones as chips", "Render & save", "Full editor (back to PRO)"],
         "CHAT mode with eight numbered callouts.", maxw=1400)
    c.click(CS + "button::full editor", 3500)
