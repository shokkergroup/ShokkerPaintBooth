"""Lane S pass 2 - spec tools, layer actions, selection / placement / panels / banner, zone area, zone spec rows. Group: ui."""
import enc_screens as E
from enc_screens import shot
from enc_screens_ui import crop
from enc_screens_ui3 import menu_shot, clean

FULL = [0, 0, 1700, 1000]


def make_sel(c, fx=0.35, fy=0.35, w=120, h=90):
    """Drag a Rect selection on the SOURCE canvas so the active zone has a region (the spec helpers need one)."""
    c.click("#vtModeRect", 500)
    r = c.need("#paintCanvas")
    x0, y0 = r[0] + r[2] * fx, r[1] + r[3] * fy
    c.pg.mouse.move(x0, y0)
    c.pg.mouse.down()
    c.pg.mouse.move(x0 + w, y0 + h, steps=8)
    c.pg.mouse.up()
    c.wait(700)


def drop_sel(c):
    c.esc()
    c.js("() => { try { clearZoneRegions(0, true); } catch (e) {} try { deselectRegion(); } catch (e) {} return 1; }")
    c.click("#vtModePickItem", 300)
    c.pg.mouse.move(900, 990)
    c.wait(500)


def overlay_shot(c, sid, opener, title, caption, arts, marks, labels, alt, sel=True):
    E.tidy(c, 0)
    if sel:
        make_sel(c)
    c.js("() => { %s; return 1; }" % opener)
    c.wait(2500)
    dlg = c.rect(".modal-overlay.active > div") or c.rect("[role=dialog] > div")
    region = [dlg[0] - 12, dlg[1] - 12, dlg[2] + 24, dlg[3] + 24] if dlg else FULL
    crop(c, sid, title, caption, arts, region, marks, labels, alt, maxw=1400)
    c.esc()
    c.js("() => { document.querySelectorAll('.modal-overlay.active').forEach(o => o.classList.remove('active')); return 1; }")
    c.wait(500)
    if sel:
        drop_sel(c)


@shot("ui", "ui_menu_spec_tools")
def ui_menu_spec_tools(c):
    """In this build the four spec helpers sit under MASK > More (the old stand-alone SPEC TOOLS menu was folded in)."""
    E.tidy(c, 0)
    c.click("#spbTopToolbar summary::mask", 700)
    c.js("() => { const e = document.querySelector('[onclick*=\"openDecalRescueKit\"]'); const m = e.closest('details.spb-tool-more'); m.open = true; return 1; }")
    c.wait(700)
    pop = "details[open] .spb-tb-pop"
    marks = [(1, "button::decal rescue", {"at": "l", "dx": -9}), (2, "button::lighting mask", {"at": "l", "dx": -9}), (3, "button::material sampler", {"at": "l", "dx": -9}), (4, "button::range remapper", {"at": "l", "dx": -9})]
    region = c.union(["#spbTopToolbar summary::mask", pop], 12)
    crop(c, "ui_menu_spec_tools", "The spec helpers: MASK menu, Advanced spec utilities",
         "Decal Rescue, Lighting Mask, Material Sampler and the Material Range Remapper (the four SPEC TOOLS) open from the MASK menu, under Advanced spec utilities.",
         ["spec_sculpt.spec_tools_menu", "spec.material_override_remap_lighting", "spec.inspector", "layers.decal_rescue", "spec.channel_a_mask"], region, marks,
         ["Decal Rescue Kit", "iRacing Lighting Mask", "Material Sampler", "Material Range Remapper"],
         "The MASK menu open with the Advanced spec utilities list of four spec helper buttons.")
    c.click("#spbTopToolbar summary::mask", 400)


@shot("ui", "ui_spec_inspector")
def ui_spec_inspector(c):
    marks = [(1, "#specMapInspectorTitle", {"at": "r", "dx": 10}), (2, "#specMapInspectorStage", {"at": "tl"}), (3, "#specMapInspectorValues", {"at": "tl"}), (4, "#specMapInspectorHint", {"at": "tl"})]
    overlay_shot(c, "ui_spec_inspector", "openSpecMapInspector()", "The Material Sampler (Spec Map Inspector)",
                 "Look at the spec channels one at a time and read the exact numbers from any spot on the car.",
                 ["spec.inspector", "spec_sculpt.spec_tools_menu", "spec.reading_by_colour", "spec.material_override_remap_lighting"], marks,
                 ["Title and channel views", "The compiled spec map (click to sample)", "Exact Metal / Rough / Coat / Alpha values", "Hint line"],
                 "The Spec Map Inspector with the spec map and value readout.", sel=False)


@shot("ui", "ui_spec_lighting_mask")
def ui_spec_lighting_mask(c):
    marks = [(1, "#specLightingMaskTitle", {"at": "r", "dx": 10}), (2, "#specLightingMaskSelectionSummary", {"at": "tl"})]
    overlay_shot(c, "ui_spec_lighting_mask", "openSpecLightingMask()", "The Lighting Mask (alpha channel)",
                 "Switch iRacing lighting on or off for chosen spots: grille openings, vents, fake holes.",
                 ["spec.channel_a_mask", "spec.material_override_remap_lighting", "spec_sculpt.spec_tools_menu"], marks,
                 ["Lighting Mask title", "Selection summary"], "The Lighting Mask tool open over the window.")


@shot("ui", "ui_spec_remap")
def ui_spec_remap(c):
    marks = [(1, "#specMaterialRemapTitle", {"at": "r", "dx": 10}), (2, "#specRemapMBar", {"at": "tl"}), (3, "#specRemapRBar", {"at": "tl"}),
             (4, "#specRemapCCBar", {"at": "tl"}), (5, "#specMaterialRemapSelectionSummary", {"at": "tl"})]
    overlay_shot(c, "ui_spec_remap", "openSpecMaterialRemap()", "The Material Range Remapper",
                 "Squeeze the Metal, Rough or Coat channel of the active zone into a new low-to-high range.",
                 ["spec.material_override_remap_lighting", "spec_sculpt.spec_tools_menu", "spec.channel_sliders"], marks,
                 ["Remapper title", "Metal range bar", "Roughness range bar", "Clearcoat range bar", "Selection summary"],
                 "The Material Range Remapper with three range bars.")


@shot("ui", "ui_decal_rescue")
def ui_decal_rescue(c):
    marks = [(1, "#decalRescueTitle", {"at": "r", "dx": 10}), (2, "#decalRescueSelectionSummary", {"at": "tl"}), (3, "#decalRescueRestrictionNote", {"at": "tl"})]
    overlay_shot(c, "ui_decal_rescue", "openDecalRescueKit()", "The Decal Rescue kit",
                 "Give numbers and sponsors a vinyl-like spec (flat, satin or gloss) so they do not shine like the paint.",
                 ["layers.decal_rescue", "spec_sculpt.spec_tools_menu", "ui_shell.number_modes"], marks,
                 ["Decal Rescue title", "Selection summary", "Restriction note"], "The Decal Rescue kit open over the window.")


@shot("ui", "ui_layer_actions_menu")
def ui_layer_actions_menu(c):
    E.tidy(c, 0)
    c.js("() => { setToolbarEditMode('layer'); return 1; }")
    c.wait(800)
    c.js("() => { const s = document.createElement('style'); s.id = 'encMenuOverflow'; s.textContent = '#rightPanel, #rightPanel * { overflow: visible !important; }'; document.head.appendChild(s); return 1; }")   # the 276 px panel clips the menu's left edge: show it whole
    c.click("#layerActionsMenuBtn", 800)
    marks, labels = c.auto("#layerActionsMenu button", 8, at="l", dx=-9)
    region = c.union(["#layerActionsMenu", "#layerActionsMenuBtn", "button::open layered"], 8)
    crop(c, "ui_layer_actions_menu", "The layer Actions menu", "Blank layer, merge visible, flatten, the Photoshop round trip and thumbnail size.",
         ["layers.merge", "layers.export_photoshop", "layers.open_psd", "layers.panel"], region, marks, clean(labels),
         "The layer Actions menu open with numbered items.")
    c.click("#layerActionsMenuBtn", 400)
    c.js("() => { const s = document.getElementById('encMenuOverflow'); if (s) s.remove(); return 1; }")
    c.js("() => { setToolbarEditMode('zone'); return 1; }")


@shot("ui", "ui_selection_bar")
def ui_selection_bar(c):
    E.tidy(c, 0)
    make_sel(c)
    marks = [(1, "#toolOptionsBar select", {"at": "t", "dy": -14}), (2, "#toolOptionsBar input", {"at": "t", "dy": -14}),
             (3, "#toolOptionsBar button::erase", {"at": "t", "dy": -14}), (4, "#toolOptionsBar button::move border", {"at": "t", "dy": -14}),
             (5, "#toolOptionsBar button::transform base", {"at": "t", "dy": -14})]
    reg = c.union(["#toolOptionsBar"], 6)
    reg = [reg[0], reg[1] - 40, reg[2], reg[3] + 46]
    crop(c, "ui_selection_bar", "The selection bar under the canvas", "After you drag a selection, this bar sets how it combines (Mode), feathers it, and offers Erase, Move Border and Transform Base.",
         ["ui_shell.selection_bar", "tools.refine_selection", "tools.select_shapes", "tools.selection_modes"], reg, marks,
         ["Mode: Replace, Add, Subtract, Intersect", "Feather (soft edge)", "Erase the selection", "Move Border", "Transform Base"],
         "The bar under the canvas with five numbered controls for a selection.", pad=0)
    drop_sel(c)


@shot("ui", "ui_menu_mask_refine")
def ui_menu_mask_refine(c):
    E.tidy(c, 0)
    c.click("#spbTopToolbar summary::mask", 700)
    c.js("() => { const d = Array.from(document.querySelectorAll('details.spb-tool-more')).find(d => /refine edges/i.test(d.querySelector('summary').innerText)); if (d) d.open = true; return 1; }")
    c.wait(700)
    pop = "details[open] .spb-tb-pop"
    marks, labels = c.auto(pop + " details[open] button", 8, at="l", dx=-9)
    region = c.union(["#spbTopToolbar summary::mask", pop], 12)
    crop(c, "ui_menu_mask_refine", "MASK menu: Refine edges and advanced masks", "Grow, shrink, smooth, feather and fill the edge of a selection from the MASK menu's refine list.",
         ["ui_shell.selection_bar", "tools.refine_selection", "tools.mask_menu"], region, marks, clean(labels),
         "The MASK menu with the refine-edges list open and numbered items.")
    c.click("#spbTopToolbar summary::mask", 400)


@shot("ui", "ui_placement_mode")
def ui_placement_mode(c):
    E.tidy(c, 0)
    c.js("() => { setPlacementMode(0, 'base', 'manual'); try { updatePlacementBanner(); } catch (e) {} return 1; }")
    c.wait(1200)
    marks = [(1, "#placementBanner", {"at": "tl"}), (2, "#placementMapOverlay", {"at": "tl"})]
    crop(c, "ui_placement_mode", "Placement mode", "Placement mode lets you drag a base or pattern around on the template; the blue banner says what you are moving.",
         ["ui_shell.placement_overlay", "finishes.base_scale_rotation", "patterns.layers_and_stacking"], FULL, marks,
         ["Placement banner", "The template you drag on"], "The window in placement mode with the blue banner above the canvas.", maxw=1400)
    c.js("() => { setPlacementMode(0, 'base', 'normal'); try { updatePlacementBanner(); } catch (e) {} return 1; }")


@shot("ui", "ui_ui_size_box")
def ui_ui_size_box(c):
    """Only the UI-size box is pictured: in the clean skin the fold tabs are hidden and folding a column has no visible effect (reported, not hidden)."""
    E.tidy(c, 0)
    marks = [(1, ".ui-scale-btn[onclick*='-1']", {"at": "b", "dy": 12}), (2, "#uiScaleLabel", {"at": "b", "dy": 12}), (3, ".ui-scale-btn[onclick*='(1)']", {"at": "b", "dy": 12})]
    crop(c, "ui_ui_size_box", "The UI size box", "The minus / percent / plus box in the header makes the toolbars and panels smaller or larger without zooming the canvas.",
         ["ui_shell.panels_and_ui_size", "ui_shell.window_tour"], [205, 55, 360, 95], marks, ["UI smaller", "Current UI size", "UI larger"],
         "The UI size box with minus, percent and plus numbered.", pad=0)


@shot("ui", "ui_update_banner")
def ui_update_banner(c):
    E.tidy(c, 0)
    c.js("() => { const b = document.getElementById('spbUpdateBanner'); document.getElementById('spbUpdateBannerVersion').textContent = ' A new version is ready (test message).'; b.style.display = 'block'; return 1; }")
    c.wait(600)
    marks = [(1, "#spbUpdateBannerText", {"at": "tl"}), (2, "#spbUpdateBannerDownload"), (3, "#spbUpdateBannerSnooze")]
    crop(c, "ui_update_banner", "The update banner", "When a newer Shokker is ready this banner appears under the title bar. Download now or be reminded later (test message shown).",
         ["ui_shell.update_banner", "workflows.install_update"], [0, 0, 1700, 200], marks, ["What is new", "Download Update", "Remind Me Later"],
         "The update banner under the title bar with two buttons.", maxw=1400)
    c.js("() => { document.getElementById('spbUpdateBanner').style.display = 'none'; return 1; }")


@shot("ui", "ui_zone_apply_area")
def ui_zone_apply_area(c):
    E.tidy(c, 0)
    c.js("() => { const h = document.querySelector('#sectionApplyArea0 .section-header'); if (h) h.click(); return 1; }")
    c.wait(900)
    c.scroll_to("#sectionApplyArea0", "start")
    marks = [(1, "#sectionApplyArea0 .section-header"), (2, "#sectionApplyArea0 button::draw box"), (3, "#sectionApplyArea0 button::lasso"), (4, "#sectionApplyArea0 button::clear")]
    crop(c, "ui_zone_apply_area", "APPLY AREA: draw a box or lasso", "Limit a zone to an area you draw, on top of its colour or layer choice.",
         ["zones.regions", "zones.how_pixels_picked", "zones.popout_panel", "zones.recipe_split_car"], [192, 150, 470, 830], marks,
         ["APPLY AREA section", "Draw box", "Lasso", "Clear"], "The APPLY AREA section of the zone popout with box and lasso buttons.")
    c.js("() => { const h = document.querySelector('#sectionApplyArea0 .section-header'); if (h) h.click(); return 1; }")


@shot("ui", "ui_zone_spec_row")
def ui_zone_spec_row(c):
    E.tidy(c, 0)
    c.scroll_to("#sectionBase0 *::spec blend", "center")
    marks = [(1, "button::auto-pop"), (2, "#zoneEditorFloat select::spec preset"), (3, "#zoneEditorFloat *::r metal", {"at": "l", "dx": -12}), (4, "#zoneEditorFloat *::spec sliders", {"at": "l", "dx": -12})]
    crop(c, "ui_zone_spec_row", "Auto-Pop and spec presets (Feels)", "Under Spec Sliders: one click of Auto-Pop for a safe boost of shine, and the Feels preset list.",
         ["spec.auto_pop", "spec.presets_feels", "spec.channel_sliders"], [192, 150, 470, 830], marks,
         ["Auto-Pop", "Spec preset (Feels)", "R Metal slider", "Spec Sliders heading"], "The Auto-Pop button and spec preset list in the zone popout.")


@shot("ui", "ui_zone_spec_strength")
def ui_zone_spec_strength(c):
    E.tidy(c, 0)
    c.scroll_to("#sectionBase0 *::base strength", "start")
    marks = [(1, "#sectionBase0 *::spec strength", {"at": "l", "dx": -12}), (2, "#sectionBase0 *::spec scale", {"at": "l", "dx": -12}),
             (3, "#sectionBase0 *::spec rotation", {"at": "l", "dx": -12}), (4, "#sectionBase0 *::base strength", {"at": "l", "dx": -12})]
    crop(c, "ui_zone_spec_strength", "Spec Strength and independent spec scale",
         "Spec Strength fades the spec toward neutral; the Spec Scale box lets the spec have its own size apart from the paint.",
         ["spec.strength_and_independent", "spec.scale_rotation", "finishes.base_colour_tuning"], [192, 150, 470, 830], marks,
         ["Spec Strength", "Spec Scale (tick to make it independent)", "Spec Rotation", "Base Strength (paint side)"],
         "Spec Strength and Spec Scale controls in the zone popout.")


@shot("ui", "ui_zone_sections_overview")
def ui_zone_sections_overview(c):
    E.tidy(c, 0)
    c.scroll_to("#sectionSpecPatterns0", "start")
    marks = [(1, "#sectionSpecPatterns0 .section-header", {"at": "tr", "dx": -30}),
             (2, "#sectionPattern0 .section-header", {"at": "tr", "dx": -30}), (3, "#sectionOverlays0 .section-header", {"at": "tr", "dx": -30})]
    crop(c, "ui_zone_sections_overview", "How base, pattern and spec stack in one zone",
         "Every zone builds from BASE first, then SPEC OVERLAYS and PATTERN on top, then the OVERLAYS stack.",
         ["spec.how_layers_combine", "spec.overlays_stack", "zones.popout_panel", "finishes.second_base_overlays"], [192, 150, 470, 830], marks,
         ["SPEC OVERLAYS (detail in the shine, on top of BASE above)", "PATTERN (shape on top)", "OVERLAYS (second base and more)"],
         "The zone popout sections BASE, SPEC OVERLAYS, PATTERN and OVERLAYS in order.")


@shot("ui", "ui_chat_car_parts")
def ui_chat_car_parts(c):
    E.tidy(c, 0)
    c.click("#spbModeChatBtn", 4000)
    c.click("#spbChatStudio button::car parts", 3000)
    marks = [(1, "#spbChatStudio button::car parts", {"at": "b", "dy": 4}), (2, "#spbCsFrame", {"at": "tl", "dx": 6, "dy": 6}), (3, "#spbProAI *::I know this car", {"at": "tl", "dx": -4, "dy": -2})]
    crop(c, "ui_chat_car_parts", "Named car parts in CHAT mode", "Car parts shows the parts Shokker knows on this car (front bumper, hood, roof, left and right side, trunk, spoiler) so you can say 'carbon on the roof'.",
         ["zones.named_parts", "ai_copilot.chat_mode", "zones.regions"], [0, 0, 1700, 1000], marks,
         ["Car parts tab", "The car sheet with each named part outlined and labelled", "The helper knows the parts and uses them when you type a request"],
         "CHAT mode with the Car parts tab on: the sheet shows the named parts.", maxw=1400)
    c.click("#spbChatStudio button::paint", 800)
    c.click("#spbChatStudio button::full editor", 3500)


@shot("ui", "ui_zone_empty_message")
def ui_zone_empty_message(c):
    E.tidy(c, 0)
    c.click("button::add zone", 1200)
    n = c.js("() => (typeof zones !== 'undefined') ? zones.length : 0")
    card = "#zone-card-%d" % (n - 1)
    c.click(card, 800)
    marks = [(1, card + " .zone-overlay-dot", {"at": "r", "dx": 12}), (2, "#zoneEditorFloat *::pick a base material", {"at": "tl", "dx": -8, "dy": -2}),
             (3, "#zoneEditorFloat *::no color or region set yet", {"at": "tl", "dx": -8, "dy": -2})]
    crop(c, "ui_zone_empty_message", "A zone that shows nothing", "A brand-new zone has no finish and no way to pick pixels yet; the card badge and the popout both say so until you give it both.",
         ["zones.not_showing", "zones.what_is_a_zone", "zones.card_controls"], [0, 150, 700, 560], marks,
         ["Grey dot on the card: no colour picked yet", "The popout asks for a base material and a colour", "No colour or region set yet: nothing for this zone to cover"],
         "The ZONES column with an empty Zone 3 and its popout asking for a colour.")
    c.js("() => { try { if (typeof deleteZone === 'function') deleteZone(%d); else if (typeof removeZone === 'function') removeZone(%d); } catch (e) {} return 1; }" % (n - 1, n - 1))
    c.wait(500)


# ---------------------------------------------------------------- finish-family and wear pictures
import enc_screens_pairs as P      # noqa: E402
import enc_screens_spec as S       # noqa: E402

S.four("spec_ghost_hex", "Spec map of a Ghost Geometry finish", "Ghost Hex Grid keeps the paint colour as it was; the hexagon grid lives only in the shine channels, so it shows when light hits the car.",
       "monolithic::ghost_hex", "source", ["finishes.ghost_geometry_clearcoat", "finishes.surface_intent", "spec.how_layers_combine"],
       "Four views of the spec map for a Ghost Hex Grid finish: combined, metal, rough and coat.", "Ghost Hex")
S.four("spec_ghost_stripes", "Spec map of Ghost Stripes", "Ghost Stripes hides its stripes in the spec map; the paint stays plain.",
       "monolithic::ghost_stripes", "source", ["finishes.ghost_geometry_clearcoat", "finishes.surface_intent"],
       "Four views of the spec map for a Ghost Stripes finish.", "Ghost Stripes")


def spec_wear(c):
    from PIL import Image, ImageDraw
    import enc_callouts as C
    P.clear(c); P.add(c, name="Worn chrome", finish="base::chrome", color="finish"); P.tweak(c, 0, wear=80); P.shotpic(c)
    S.open_viewer(c)
    W = 400
    tiles = [S.tile(c, a).resize((W, W), Image.LANCZOS) for a, _ in S.CH]
    S.close_viewer(c)
    P.tweak(c, 0, wear=0)
    im = Image.new("RGB", (W * 4 + 36, W + 62), (11, 14, 23)); d = ImageDraw.Draw(im)
    for i, (t, (_, lab)) in enumerate(zip(tiles, S.CH)):
        x = i * (W + 12); im.paste(t, (x, 0)); d.text((x + W // 2, W + 20), lab.split(":")[0], font=C._font(17), fill=(245, 118, 26), anchor="mm")
        if ":" in lab:
            d.text((x + W // 2, W + 44), lab.split(":")[1].strip(), font=C._font(14), fill=(220, 226, 238), anchor="mm")
    E.emit("spec_wear", "Spec map of a worn Chrome zone", "Chrome with Wear at 80: chips and dulling are drawn into the metal, rough and coat channels (compare the clean Chrome spec map).",
           "spec_view", ["finishes.wear", "finishes.base_colour_tuning"], im, "Four views of the spec map for a Chrome zone with strong wear.", maxw=1600, meta={"finish_key": "base::chrome", "wear": 80})


E.REG["spec_wear"] = ("spec", spec_wear); E.ORDER.append("spec_wear")


@shot("ui", "ui_export_photoshop")
def ui_export_photoshop(c):
    E.tidy(c, 0)
    c.js("() => { openExportToPhotoshopModal(); return 1; }")
    c.wait(1800)
    c.js("() => { const i = document.getElementById('psExportExchangeFolder'); if (i) i.value = 'C:/Users/You/Documents/ShokkerPaintBooth/PhotoshopExchange'; return 1; }")   # privacy: no user name in the picture
    dlg = c.rect(".modal-overlay.active > div") or c.rect("[role=dialog] > div")
    if not dlg:
        raise RuntimeError("photoshop modal not visible")
    txt = c.js("() => Array.from(document.querySelectorAll('.modal-overlay.active input, .modal-overlay.active textarea')).map(i => i.id + '=' + (i.value || '').slice(0, 80)).join(' | ')")
    print("   photoshop modal fields:", txt)
    region = [dlg[0] - 12, dlg[1] - 12, dlg[2] + 24, dlg[3] + 24]
    marks, labels = c.auto(".modal-overlay.active button", 6, at="tl", dx=-4, dy=-4)
    crop(c, "ui_export_photoshop", "The Photoshop round trip", "Save the paint and spec as named TGA files for Photoshop, then bring the edited files back.",
         ["layers.export_photoshop", "layers.merge"], region, marks, clean(labels), "The Export to Photoshop dialog.", maxw=1400)
    c.esc()
    c.js("() => { document.querySelectorAll('.modal-overlay.active').forEach(o => o.classList.remove('active')); return 1; }")
