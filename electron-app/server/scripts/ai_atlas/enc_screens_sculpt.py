"""Lane S pass 2 - the Spec Sculpt Lab (/spec-sculpt.html).  Group: sculpt.

Opens the lab on the TEST server in its own tab, hides the hidden-feature button (CSS, never clicked), sets the
member id to the neutral placeholder 123456, loads the bundled example paint, then shoots one real screen per topic.
The lab is a second page of the same app; the shots here never touch the main app tab.
"""
import os

import enc_screens as E
from enc_screens import shot
from enc_screens_ui import crop

EXAMPLE_PSD = str(E.ROOT / "SPB Chevy Truck Starting Example PSD.psd")
NEUTRAL_NAME = "SPB Chevy Truck Starting Example PSD.psd"
BASE = "http://127.0.0.1:59879/spec-sculpt.html"
PRIVACY_CSS = "#btnEasyMode,#easyModeHint{display:none!important} #toast{display:none!important} .tour-pop,#tourPop{display:none!important}"


def lab(c, mode="advanced"):
    """Ctx on the lab tab (created once, kept on the enc_screens module so reloads keep it)."""
    sp = getattr(E, "_LAB", None)
    if sp is not None:
        try:
            sp.evaluate("1")
        except Exception:
            sp = None
    if sp is None:
        sp = c.pg.context.new_page()
        sp.set_viewport_size({"width": 1700, "height": 1000})
        sp.goto(BASE, wait_until="load")
        sp.wait_for_timeout(2500)
        try:
            sp.click("#tourSkip", timeout=1500)
        except Exception:
            pass
        sp.add_style_tag(content=PRIVACY_CSS)
        sp.evaluate("""() => { const i = document.getElementById('iracingId'); if (i) { i.value = '123456'; i.dispatchEvent(new Event('input', {bubbles: true})); i.dispatchEvent(new Event('change', {bubbles: true})); }
                              const d = document.getElementById('btnDismissRestored'); if (d && d.offsetParent) d.click(); document.getElementById('btnTryExample').click(); return 1; }""")
        sp.wait_for_timeout(14000)
        # load the bundled example as a LAYERED psd so the layer picker (Smart Separate) has real layers
        sp.evaluate("(p) => window.loadPsd(p)", EXAMPLE_PSD)
        sp.wait_for_timeout(9000)
        E._LAB = sp
    sp.evaluate("""(n) => { const i = document.getElementById('pathInput'); if (i && i.value) i.value = n;
                           const m = document.getElementById('iracingId'); if (m && m.value !== '123456') m.value = '123456'; return 1; }""", NEUTRAL_NAME)
    L = E.Ctx(sp, c.ro)
    want = "#uiModeAdvanced" if mode == "advanced" else "#uiModeSimple"
    L.js("(s) => { const b = document.querySelector(s); if (b) b.click(); return 1; }", want)
    L.wait(900)
    L.js("() => { document.querySelectorAll('aside, main').forEach(e => e.scrollTop = 0); window.scrollTo(0, 0); return 1; }")
    return L


CARD_JS = """(a) => { const txt = a[0].toLowerCase(), pos = a[1];
  const hs = Array.from(document.querySelectorAll('h3,summary,.mc-title,h2')).filter(e => (e.innerText || '').trim().toLowerCase().startsWith(txt));
  if (!hs.length) return null; const card = hs[0].closest('.card, details') || hs[0];
  card.scrollIntoView({ block: pos }); const r = card.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }"""


def card(L, text, pos="start"):
    r = L.js(CARD_JS, [text, pos])
    L.wait(500)
    if not r:
        raise RuntimeError("lab card not found: " + text)
    return L.js("(a) => { const hs = Array.from(document.querySelectorAll('h3,summary,.mc-title,h2')).filter(e => (e.innerText || '').trim().toLowerCase().startsWith(a)); const c = hs[0].closest('.card, details') || hs[0]; const r = c.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }", text.lower())


@shot("sculpt", "sculpt_overview")
def sculpt_overview(c):
    L = lab(c, "simple")
    marks = [(1, "h1", {"at": "r", "dx": 6}), (2, "#uiModeSwitch"), (3, ".card::source image", {"at": "tr", "dx": -30, "dy": 12}),
             (4, ".card::identity & deploy", {"at": "tr", "dx": -30, "dy": 12}), (5, "#specDock", {"at": "tl", "dx": 6, "dy": 6}),
             (6, "#btnPaintBooth"), (7, ".card::style gallery", {"at": "tl", "dx": 6, "dy": 6})]
    crop(L, "sculpt_overview", "The Spec Sculpt Lab", "A separate page that builds the shine map for a finished paint: pick the paint on the left, pick a look, build.",
         ["spec_sculpt.what_is_spec_sculpt", "spec_sculpt.recipes"], [0, 0, 1700, 1000], marks,
         ["Lab title", "Simple / Advanced switch", "SOURCE IMAGE: your paint file", "IDENTITY & DEPLOY: member id and car folder",
          "Live channel strip: source, spec, metal, rough, coat", "Back to Paint Booth", "STYLE GALLERY: one-click looks"],
         "The Spec Sculpt Lab in Simple view with seven numbered callouts.", maxw=1400)


@shot("sculpt", "sculpt_three_modes")
def sculpt_three_modes(c):
    L = lab(c)
    r = card(L, "look blend")
    marks = [(1, "#lookBlendCard .mc-title::scratch", {"at": "l", "dx": -10}), (2, "#lookBlendCard .mc-title::catalog", {"at": "l", "dx": -10}),
             (3, "#lookBlendCard .mc-title::fusion", {"at": "l", "dx": -10}), (4, "#lookBlendCard .mc-title::fracture", {"at": "l", "dx": -10}),
             (5, "#lookBlendCard .mc-title::candy depth", {"at": "l", "dx": -10})]
    crop(L, "sculpt_three_modes", "LOOK BLEND: Scratch, Catalog, Fusion", "Three ways to build the shine: from scratch on your paint, from real Paint Booth materials, or both blended. Fracture and Candy Depth are extras.",
         ["spec_sculpt.three_modes", "spec_sculpt.what_is_spec_sculpt"], [r[0] - 6, r[1], r[2] + 12, min(r[3], 560)], marks,
         ["Scratch: procedural styles tuned to your paint", "Catalog: real Paint Booth materials", "Fusion: blend the two", "FRACTURE: colour-flipping glass look", "CANDY DEPTH: wet-candy gloss"],
         "The LOOK BLEND card with five mode tiles numbered.")


@shot("sculpt", "sculpt_scratch_presets")
def sculpt_scratch_presets(c):
    L = lab(c)
    L.scroll_to("#lookBlendCard .preset-cat-title::chrome", "center")
    L.wait(500)
    box = L.items("#lookBlendCard input[type=checkbox]", 12, 8)
    chk = [b for b in box if b["r"][1] > 330][:1]
    reg = L.rect("#lookBlendCard")
    marks = [(1, "#presetQuickWet", {"at": "t", "dy": -14}), (2, "#presetQuickMatte", {"at": "t", "dy": -14}), (3, ".preset-cat-title::chrome", {"at": "tl", "dx": -6, "dy": -2})]
    labels = ["Quick path: Wet + pearl", "Quick path: Matte duo", "Preset group heading (six groups)"]
    if chk:
        marks.append((4, chk[0]["r"], {"at": "l", "dx": -10}))
        labels.append("Tick boxes stack up to five presets")
    y0 = 105
    crop(L, "sculpt_scratch_presets", "Style presets and stacks", "125 presets in six groups plus Designer sets; tick up to five to stack them, with a weight each.",
         ["spec_sculpt.scratch_presets", "spec_sculpt.recipes"], [reg[0] - 6, y0, reg[2] + 12, 850], marks, labels,
         "The preset list in the lab with group headings and tick boxes.")


@shot("sculpt", "sculpt_paint_response")
def sculpt_paint_response(c):
    L = lab(c)
    L.js("() => { const d = document.getElementById('paintResponseDetails'); if (d) d.open = true; return 1; }")
    r = card(L, "paint response", "start")
    L.wait(400)
    reg = L.rect("#paintResponseDetails")
    marks = [(1, "#paintResponseDetails summary", {"at": "tr", "dx": -30, "dy": 6})]
    crop(L, "sculpt_paint_response", "Paint response", "Tie the shine to the colours in your paint: more gloss on the bright areas, or on one hue.",
         ["spec_sculpt.paint_response"], [reg[0] - 16, reg[1] - 22, reg[2] + 30, min(reg[3] + 30, 800)], marks, ["Paint response (optional) section"],
         "The Paint response section opened in the lab.")


@shot("sculpt", "sculpt_generation_dna")
def sculpt_generation_dna(c):
    L = lab(c)
    L.scroll_to("#dnaPresetShipped", "center")
    L.js("() => { const d = document.querySelector('#dnaPresetShipped').closest('.card').querySelector('details.tune'); if (d) d.open = true; return 1; }")
    L.wait(500)
    L.scroll_to("#dnaPresetShipped", "center")
    reg = L.union(["#dnaPresetShipped", "#dnaPresetInk", "#dnaPresetShipped::catalog signature"], 0)
    marks = [(1, "#dnaPresetShipped", {"at": "t", "dy": 2}), (2, "#dnaPresetRich", {"at": "t", "dy": 2}), (3, "#dnaPresetSoft", {"at": "t", "dy": 2}), (4, "#dnaPresetInk", {"at": "t", "dy": 2}),
             (5, ".slider-head::procedural detail", {"at": "tl", "dx": 0, "dy": 0})]
    crop(L, "sculpt_generation_dna", "Generation DNA", "Four one-click DNA presets, the detail slider above them, and the advanced void and flatten sliders below.",
         ["spec_sculpt.generation_dna"], [reg[0] - 14, reg[1] - 150, 400, 400], marks,
         ["Catalog signature (the shipped look)", "Rich detail", "Softer", "Ink-heavy panels", "Procedural detail intensity"],
         "The Generation DNA presets and detail slider.")


@shot("sculpt", "sculpt_smart_separate")
def sculpt_smart_separate(c):
    L = lab(c)
    L.js("() => { const c = document.getElementById('psdLayerCard'); return c ? c.style.display : null; }")
    L.scroll_to("#psdLayerCard", "start")
    L.js("() => { document.querySelector('main').scrollTop -= 190; return 1; }")
    L.wait(500)
    reg = L.rect("#psdLayerCard")
    if not reg:
        raise RuntimeError("psdLayerCard not visible (PSD layers not loaded)")
    marks = [(1, "#psdSelAll", {"at": "t", "dy": -12}), (2, "#psdSelNone", {"at": "t", "dy": -12}), (3, "#psdSelInvert", {"at": "t", "dy": -12}),
             (4, "#psdLayerList select", {"at": "tl", "dx": 14, "dy": 0}), (5, "#psdMaskPreview", {"at": "tr", "dx": -6, "dy": 6}), (6, "#maskGrow", {"at": "t", "dy": -4})]
    crop(L, "sculpt_smart_separate", "PSD layers: pick what to sculpt", "Checked layers get the shine; unchecked ones (numbers, sponsors) stay flat. The green map shows what is protected.",
         ["spec_sculpt.smart_separate", "spec_sculpt.auto_protect"], [reg[0] - 6, reg[1] - 6, reg[2] + 12, min(reg[3] + 12, 800)], marks,
         ["All: sculpt every layer", "None: protect every layer", "Invert the ticks", "One row per layer: its tick box and its own finish", "Sculpt map: green = stays flat", "Protect edge (grow or shrink the flat area)"],
         "The PSD layer picker with a layer list and a protection map.")


@shot("sculpt", "sculpt_auto_protect")
def sculpt_auto_protect(c):
    L = lab(c)
    L.js("() => { const a = document.getElementById('autoProtect'); if (a && !a.checked) a.click(); return 1; }")
    L.wait(700)
    L.scroll_to("#autoProtect", "center")
    reg = L.rect("#autoProtect")
    p = L.rect("#autoProtectPanel") or reg
    marks = [(1, "#autoProtect", {"at": "l", "dx": -12}), (2, "#autoProtectPanel", {"at": "tr", "dx": -6, "dy": 4})]
    crop(L, "sculpt_auto_protect", "Auto-detect decals", "Tick it for a flat paint with no layers: the lab finds numbers and sponsors itself and keeps them out of the heavy shine.",
         ["spec_sculpt.auto_protect"], [0, max(0, reg[1] - 170), 400, 420], marks,
         ["Auto-detect decals (no PSD needed)", "Detection strength and edge controls"],
         "The Auto-detect decals tick box and its strength controls.")
    L.js("() => { const a = document.getElementById('autoProtect'); if (a && a.checked) a.click(); return 1; }")


@shot("sculpt", "sculpt_diagnostics")
def sculpt_diagnostics(c):
    L = lab(c)
    L.scroll_to("#matReadout", "start")
    L.js("() => { document.querySelector('main').scrollTop -= 190; return 1; }")
    L.wait(500)
    marks = [(1, "#dockSrc", {"at": "tr", "dx": -4, "dy": 4}), (2, "#dockC", {"at": "tr", "dx": -4, "dy": 4}), (3, "#dockM", {"at": "tr", "dx": -4, "dy": 4}),
             (4, "#dockR", {"at": "tr", "dx": -4, "dy": 4}), (5, "#dockCc", {"at": "tr", "dx": -4, "dy": 4}), (6, "#matReadout", {"at": "tl", "dx": 6, "dy": 6})]
    reg = L.union(["#specDock", "#matReadout"], 8)
    crop(L, "sculpt_diagnostics", "Diagnostics: the spec in false colour", "The strip packs M/R/Cc into colour and tints each channel; the box below reads the whole map back as gloss, metal and matte.",
         ["spec_sculpt.diagnostics", "spec.reading_by_colour"], reg, marks,
         ["Source paint", "Spec map in false colour (red=metal, green=rough, blue=coat)", "Metallic channel (red tint)", "Roughness channel (green tint)", "Clearcoat channel (blue tint)", "What this spec reads as: gloss / metal / matte shares and averages"],
         "The channel strip and the What this spec reads as readout.")


@shot("sculpt", "sculpt_iron_safe_export")
def sculpt_iron_safe_export(c):
    L = lab(c)
    L.scroll_to("#ironBadge", "center")
    r = L.rect("#ironBadge")
    bar = L.rect("#matReadout") or r
    reg = [max(0, r[0] - 40), max(0, r[1] - 190), 1290, 400]
    marks = [(1, "#ironBadge", {"at": "tl", "dx": 2, "dy": -6})]
    crop(L, "sculpt_iron_safe_export", "The Physically valid badge", "Every build is checked against the iron rules; this badge turns green when the spec map is legal and warns when it is not.",
         ["spec_sculpt.iron_safe_export", "spec.iron_rules"], reg, marks, ["Physically valid: the iron-rule check on the current spec"],
         "The Physically valid badge under the material summary bar.")


@shot("sculpt", "sculpt_power_features")
def sculpt_power_features(c):
    L = lab(c)
    L.scroll_to("h3::favorites", "start")
    reg = L.rect("aside")
    marks = [(1, "#btnFavCurrent", {"at": "t", "dy": 2}), (2, "#btnSaveRecipe", {"at": "t", "dy": 2}), (3, "h3::actions", {"at": "tr", "dx": -6, "dy": 2})]
    crop(L, "sculpt_power_features", "Favorites, saved looks and actions", "Star a look to keep it, save the whole setup under a name, then build from the ACTIONS card.",
         ["spec_sculpt.power_features"], [reg[0], 108, reg[2], 880], marks, ["Favorite this look", "Save a named look", "ACTIONS card"],
         "The left column showing favorites, saved looks and actions.")


@shot("sculpt", "sculpt_controls_reference")
def sculpt_controls_reference(c):
    L = lab(c)
    L.scroll_to("#btnBrush", "center")
    r = L.rect("#btnBrush")
    reg = L.union(["#btnAutoSculpt", "#btnGradient", "#btnSpotlight"], 14)
    marks = [(1, "#btnAutoSculpt", {"at": "t", "dy": 2}), (2, "#btnAutoZone", {"at": "t", "dy": 2}), (3, "#btnSmartVariant", {"at": "t", "dy": 2}), (4, "#btnShokkWorld", {"at": "t", "dy": 2}),
             (5, "#btnSpotlight", {"at": "t", "dy": 2}), (6, "#btnHueMap", {"at": "t", "dy": 2}), (7, "#btnToneMap", {"at": "t", "dy": 2}), (8, "#btnBrush", {"at": "t", "dy": 2}), (9, "#btnGradient", {"at": "t", "dy": 2})]
    crop(L, "sculpt_controls_reference", "The sculpting tool buttons", "Auto-Sculpt, Auto-Zone, a smart variation, Shokk the World and the spotlight, colour, tone, brush and gradient tools.",
         ["spec_sculpt.controls_reference", "spec_sculpt.power_features"], reg, marks,
         ["Auto-Sculpt: read my paint", "Auto-Zone: a material per region", "Another Smart Look", "Shokk the World: 20 smart looks", "Material Spotlight", "Colour to Material", "Tone to Material", "Region Brush", "Material Gradient"],
         "A row of sculpting tool buttons numbered one to nine.")
