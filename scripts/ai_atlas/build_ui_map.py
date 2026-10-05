#!/usr/bin/env python
"""Generate docs/ai_knowledge/07_ui_map_generated.md from the REAL paint-booth-v2.html (SPB-AI 2026-09-30).

Why: the shipped tutorials describe menu paths (File -> Import as Layer, View -> Channel Inspector ...) from an older layout that the current UI does not have, and a copilot that
repeats them sends buyers hunting for buttons that do not exist (one real example: it told buyers to drag a PNG onto the canvas "to add a logo", which actually REPLACES the paint file).
This file lists what is really on screen: every top-bar menu with its items and their tooltips, header commands, and the Layers-panel actions. build_ai_knowledge.py turns it into chunks.
Usage: python scripts/ai_atlas/build_ui_map.py
"""
import html as H
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'paint-booth-v2.html'
DST = REPO / 'docs' / 'ai_knowledge' / '07_ui_map_generated.md'

def text_of(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = H.unescape(s)
    s = re.sub(r'[←-⇿⌀-⏿■-➿\U0001f300-\U0001faff️]+', '', s)
    return re.sub(r'\s+', ' ', s).strip(' ·-')

def attr(tag, name):
    m = re.search(r'\b' + name + r'="([^"]*)"', tag)
    return H.unescape(m.group(1)).strip() if m else ''

def buttons(block):
    out = []
    for m in re.finditer(r'<button\b([^>]*)>(.*?)</button>', block, flags=re.S):
        tag, inner = m.group(1), m.group(2)
        label = text_of(inner) or attr(tag, 'aria-label')
        title = attr(tag, 'title')
        if not label or label in ('x', '×', '+', '-'): continue
        if re.search(r'display\s*:\s*none', tag) and not title: continue
        tip = title if title and title.lower().strip(' .…') != label.lower().strip(' .…') else ''
        out.append((label, tip))
    seen, res = set(), []
    for l, t in out:
        if l in seen: continue
        seen.add(l); res.append((l, t))
    return res

def main_md():
    h = SRC.read_text(encoding='utf-8')
    L = ['# Where things are in the app RIGHT NOW (AI knowledge card, generated from the real UI)', '',
         'IMPORTANT: the tutorials mention menus like File, View and Layer with paths such as "File -> Import as Layer" or "View -> Channel Inspector". The current app does NOT have those menus. '
         'Describe buttons only by the names listed here (top toolbar menus, header buttons, Layers panel). Dropping an image file onto the centre canvas LOADS IT AS THE WHOLE PAINT FILE (it replaces the paint), it does not add a logo layer.', '']
    # top bar menus
    for m in re.finditer(r'<details class="spb-tb-menu[^"]*"[^>]*>(.*?)</details>', h, flags=re.S):
        block = m.group(1)
        sm = re.search(r'<summary[^>]*>(.*?)</summary>', block, flags=re.S)
        name = text_of(sm.group(1)) if sm else ''
        name = re.sub(r'\s*▾.*$', '', name).strip()
        if not name: continue
        items = buttons(re.sub(r'<summary.*?</summary>', '', block, flags=re.S))
        if not items: continue
        L.append('## Top toolbar menu: %s' % name)
        for lab, tip in items: L.append('- **%s**%s' % (lab, (' — ' + tip) if tip else ''))
        L.append('')
    # header command buttons
    hdr = []
    for m in re.finditer(r'<button\b([^>]*class="[^"]*header-command-btn[^"]*"[^>]*)>(.*?)</button>', h, flags=re.S):
        lab = text_of(m.group(2)); tip = attr(m.group(1), 'title')
        if lab: hdr.append((lab, tip if tip.lower() != lab.lower() else ''))
    if hdr:
        L.append('## Header command buttons (top of the window)')
        for lab, tip in hdr: L.append('- **%s**%s' % (lab, (' — ' + tip) if tip else ''))
        L.append('')
    # Layers panel
    i = h.find('id="rpLayersContent"')
    if i > 0:
        j = h.find('id="rpTab', i + 50)
        seg = h[i:i + 9000]
        bl = buttons(seg)
        if bl:
            L.append('## Layers panel (right column, LAYERS tab) buttons')
            for lab, tip in bl[:40]: L.append('- **%s**%s' % (lab, (' — ' + tip) if tip else ''))
            L.append('')
    L.append('## Saving your work and coming back later')
    L.append('Press **Save / Open** (header row, top right of the tool row): SPB Projects saves or loads a complete workflow in one file - the open paint (PSD included), every zone, and all layer settings. '
             '**Import Recipe** / **Share Recipe** move just the zone recipe (colours, finishes, effects) as a .shokkerrecipe file, which works across cars. There is no File menu; Ctrl+S is not documented for projects, so point to the **Save / Open** button.')
    L.append('')
    L.append('## Adding a logo or an image')
    L.append('Use the Layers panel (right column, LAYERS tab): **+ Layer** adds a PNG / JPG / WebP / GIF as a new image layer; **Open Layered** imports a whole PSD / XCF / ORA template. '
             'Spec Stamps (**Import Stamp**) take a transparent PNG whose alpha marks an area that only changes the spec map. The copilot itself cannot import files.')
    L.append('')
    DST.write_text('\n'.join(L), encoding='utf-8', newline='\n')
    print('wrote', DST, len(L), 'lines')



# ======================================================================================================
# SELF-MAP (2026-10-03): the machine-readable UI map  ->  scripts/ai_atlas/ui_map.json
# Sources: (1) paint-booth-v2.html (static DOM, parsed here), (2) the Pro zone editor + Easy rail, which are BUILT BY
# JAVASCRIPT at run time (tables below were read from the live DOM on the test server), (3) curated buyer-words
# knowledge keyed by control (CUR table), (4) scripts/ai_atlas/app_controls.json (control ids / ranges).
# Re-run:  python scripts/ai_atlas/build_ui_map.py --json
# ======================================================================================================
from html.parser import HTMLParser
import json

JSON_DST = REPO / 'scripts' / 'ai_atlas' / 'ui_map.json'
CTRL_SRC = REPO / 'scripts' / 'ai_atlas' / 'app_controls.json'
VOID = {'input', 'br', 'img', 'meta', 'link', 'hr', 'source', 'col', 'area', 'base', 'wbr', 'embed', 'param', 'track'}


class _P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.stack, s.items, s.cur = [], [], None

    def handle_starttag(s, tag, attrs):
        a = dict(attrs)
        ln = s.getpos()[0]
        if tag not in VOID:
            s.stack.append((tag, a))
        if tag in ('button', 'input', 'select', 'textarea', 'summary') or a.get('role') == 'tab' or (tag == 'a' and a.get('onclick')):
            if tag == 'input' and a.get('type') == 'hidden':
                return
            it = dict(tag=tag, a=a, line=ln, text='', ids=[x[1].get('id') for x in s.stack[:-1] if x[1].get('id')])
            if tag in VOID:
                s.items.append(it)
            else:
                s.cur = it

    def handle_endtag(s, tag):
        if s.cur and s.cur['tag'] == tag:
            s.items.append(s.cur)
            s.cur = None
        for i in range(len(s.stack) - 1, -1, -1):
            if s.stack[i][0] == tag:
                del s.stack[i:]
                break

    def handle_data(s, d):
        if s.cur:
            s.cur['text'] += d


def _clean(s):
    s = re.sub(r'[←-⯿\U0001f300-\U0001faff️]+', '', s or '')
    return re.sub(r'\s+', ' ', s).strip(' ·-')


def _slug(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')[:40] or 'x'


# container DOM id -> (panel key, "where" path). Anything not listed falls back to panel "misc".
PANEL_MAP = {
    'spbUpdateBanner': ('pro.header', 'Pro > banner under the title bar (update available)'),
    'iracingIdContainer': ('pro.header', 'Pro > top row > iRacing User ID'),
    'spbModePill': ('pro.modes', 'Any mode > top row > PRO / CHAT / EASY pill'),
    'licenseSection': ('pro.settings', 'Pro > Settings (gear) > License'),
    'licenseInputRow': ('pro.settings', 'Pro > Settings (gear) > License'),
    'licenseActiveRow': ('pro.settings', 'Pro > Settings (gear) > License'),
    'settingsDropdown': ('pro.settings', 'Pro > Settings (gear) dropdown'),
    'spbTopToolbar': ('pro.toolbar', 'Pro > top toolbar (tool row)'),
    'spbToolClusterSelect': ('pro.toolbar', 'Pro > top toolbar > selection tools'),
    'spbRetouchMenu': ('pro.toolbar', 'Pro > top toolbar > RETOUCH menu'),
    'spbRetouchGate': ('pro.toolbar', 'Pro > top toolbar > RETOUCH menu'),
    'toolbarEditModeGroup': ('pro.toolbar', 'Pro > top toolbar > ZONE | LAYER switch'),
    'spbRenderHistMenu': ('pro.toolbar', 'Pro > top toolbar > RENDER HISTORY'),
    'leftPanel': ('pro.zones', 'Pro > left column (ZONES)'),
    'fleetBody': ('pro.zones', 'Pro > left column > Fleet batch'),
    'seasonBody': ('pro.zones', 'Pro > left column > Season batch'),
    'specmapModeContent': ('pro.zones', 'Pro > left column > ZONES list'),
    'zoneMoreMenu': ('pro.zones_more', 'Pro > left column > ZONES > More (three-dot) menu'),
    'thumbnailWarningBanner': ('pro.zones', 'Pro > left column'),
    'paintPreviewEmpty2': ('pro.center', 'Pro > centre > empty canvas'),
    'paintPreviewEmptyBig': ('pro.center', 'Pro > centre > empty canvas (no paint loaded yet)'),
    'toolSpecificOptions': ('pro.tool_options', 'Pro > centre > tool options bar (changes with the active tool)'),
    'toolOptionsBar': ('pro.tool_options', 'Pro > centre > tool options bar'),
    'dodgeBurnOptions': ('pro.tool_options', 'Pro > centre > tool options bar (Dodge / Burn)'),
    'textToolOptions': ('pro.tool_options', 'Pro > centre > tool options bar (Text tool)'),
    'shapeToolOptions': ('pro.tool_options', 'Pro > centre > tool options bar (Shape tool)'),
    'colorBrushOptions': ('pro.tool_options', 'Pro > centre > tool options bar (Color Brush)'),
    'layerPaintSourceOptions': ('pro.tool_options', 'Pro > centre > tool options bar (layer Brush / Fill source)'),
    'penToolOptions': ('pro.tool_options', 'Pro > centre > tool options bar (Pen)'),
    'cloneToolOptions': ('pro.tool_options', 'Pro > centre > tool options bar (Clone)'),
    'healingToolOptions': ('pro.tool_options', 'Pro > centre > tool options bar (Healing Brush)'),
    'historyToolOptions': ('pro.tool_options', 'Pro > centre > tool options bar (History Brush)'),
    'advancedToolbar': ('pro.selection_bar', 'Pro > centre > selection / mask bar under the canvas'),
    'centerPanel': ('pro.center', 'Pro > centre column'),
    'sourcePreviewControls': ('pro.center', 'Pro > centre > source canvas corner buttons'),
    'placement-tools-bar': ('pro.placement', 'Pro > centre > placement bar (shows while placing a pattern / base by hand)'),
    'layerTransformQuickbar': ('pro.transform', 'Pro > centre > transform bar (shows during Transform)'),
    'specChannelDock': ('pro.preview', 'Pro > centre > spec channel strip under the preview'),
    'splitPreview': ('pro.preview', 'Pro > centre > split preview'),
    'previewSpecPane': ('pro.preview', 'Pro > centre > spec pane of the preview'),
    'renderFloat': ('pro.render', 'Pro > centre > RENDER button'),
    'zoomControls': ('pro.center', 'Pro > centre > zoom / view buttons'),
    'canvasDisplayModeGroup': ('pro.center', 'Pro > centre > SOURCE | CAR | SPLIT view switch'),
    'renderResultsPanel': ('pro.render', 'Pro > after RENDER > recipe card window'),
    'renderDeployRow': ('pro.render', 'Pro > after RENDER > recipe card > deploy row'),
    'deployRowInner': ('pro.render', 'Pro > after RENDER > recipe card > deploy row'),
    'eyedropperZoneControls': ('pro.eyedropper', 'Pro > centre > Color (eyedropper) tool bar'),
    'rightPanel': ('pro.right', 'Pro > right column'),
    'rightPanelTabs': ('pro.right', 'Pro > right column > tabs'),
    'rpLayersContent': ('pro.layers', 'Pro > right column > LAYERS tab'),
    'layerActionsMenu': ('pro.layers', 'Pro > right column > LAYERS tab > Actions menu'),
    'rpFinishesContent': ('pro.finish_library', 'Pro > FINISHES library (full-screen)'),
    'fineTuningPanel': ('pro.finish_library', 'Pro > FINISHES library > fine tuning'),
    'scriptModal': ('pro.dialogs', 'Pro > Script export dialog'),
    'specMapInspectorModal': ('pro.spec_tools', 'Pro > Spec Tools > Material Sampler'),
    'specMapInspectorContent': ('pro.spec_tools', 'Pro > Spec Tools > Material Sampler'),
    'decalRescueOverlay': ('pro.spec_tools', 'Pro > top toolbar > Spec Tools > Decal Rescue Kit'),
    'specLightingMaskOverlay': ('pro.spec_tools', 'Pro > top toolbar > Spec Tools > Lighting Mask'),
    'specMaterialRemapOverlay': ('pro.spec_tools', 'Pro > top toolbar > Spec Tools > Range Remapper'),
    'presetGalleryOverlay': ('pro.zones_more', 'Pro > ZONES > More > Presets Gallery'),
    'finishBrowserTitle': ('pro.finish_browser', 'Pro > Finish catalog browser'),
    'finishBrowserOverlay': ('pro.finish_browser', 'Pro > Finish catalog browser'),
    'finishBrowserFilters': ('pro.finish_browser', 'Pro > Finish catalog browser > filters'),
    'finishCompareOverlay': ('pro.finish_browser', 'Pro > Finish catalog browser > compare'),
    'dualShiftOverlay': ('pro.dialogs', 'Pro > custom dual colour-shift dialog'),
    'tmplNameOverlay': ('pro.zones_more', 'Pro > ZONES > More > Save as Template'),
    'filePickerOverlay': ('pro.dialogs', 'Pro > Shokker file browser dialog'),
    'undoHistoryPanel': ('pro.history', 'Pro > Undo History panel'),
    'swatchPopup': ('pro.finish_picker', 'Pro > zone editor > Base Material picker (popup)'),
    'swatchPopupFilterRow': ('pro.finish_picker', 'Pro > zone editor > Base Material picker (popup)'),
    'swatchPopupEmpty': ('pro.finish_picker', 'Pro > zone editor > Base Material picker (popup)'),
    'swatchStage': ('pro.finish_picker', 'Pro > Base Material picker > On-Car Stage'),
    'swatchPreviewModal': ('pro.finish_picker', 'Pro > Base Material picker > See on paint'),
    'shokkLibraryModal': ('pro.shokk_library', 'Pro > ZONES > More > LOAD SHOKK FILE'),
    'saveShokkModal': ('pro.shokk_library', 'Pro > ZONES > More > SAVE SHOKK'),
    'exportToPhotoshopModal': ('pro.layers', 'Pro > LAYERS > Actions > Photoshop round-trip'),
    'previewLightbox': ('pro.preview', 'Pro > centre > full-size preview window'),
    'renderStatsOverlay': ('pro.render', 'Pro > render statistics panel'),
    'layerEffectsDialog': ('pro.layers', 'Pro > LAYERS > double-click a layer > Layer Effects'),
    'shortcutOverlay': ('pro.settings', 'Pro > Settings > Keyboard Shortcuts'),
    'spbEasyRoot': ('easy', 'Easy mode'),
}

KIND_OF = {'range': 'slider', 'checkbox': 'toggle', 'color': 'picker', 'text': 'text input', 'number': 'number input',
           'search': 'search box', 'file': 'file input', 'radio': 'toggle'}


KEY_ALIAS = {
    'pro.header.browse_iracing_car_folder_in_windows_fil': 'pro.header.browse_car_folder',
    'pro.spec_tools.flat_vinyl_neutralizes_chrome_or_candy_b': 'pro.spec_tools.decal_flat_vinyl',
    'pro.spec_tools.satin_decal_keeps_printed_vinyl_readable': 'pro.spec_tools.decal_satin',
    'pro.spec_tools.gloss_decal_adds_clean_printed_gloss_wit': 'pro.spec_tools.decal_gloss',
    'pro.spec_tools.use_source_alpha_remove_spb_s_override_a': 'pro.spec_tools.lighting_use_source',
    'pro.spec_tools.full_lighting_force_normal_lighting_and_': 'pro.spec_tools.lighting_full',
    'pro.spec_tools.reduced_lighting_half_strength_response_': 'pro.spec_tools.lighting_reduced',
    'pro.spec_tools.kill_lighting_suppress_spec_and_environm': 'pro.spec_tools.lighting_kill',
    'pro.spec_tools.original': 'pro.spec_tools.remap_original', 'pro.spec_tools.metallic_texture': 'pro.spec_tools.remap_metallic',
    'pro.spec_tools.printed_vinyl': 'pro.spec_tools.remap_vinyl', 'pro.spec_tools.matte_texture': 'pro.spec_tools.remap_matte',
    'pro.spec_tools.gloss_texture': 'pro.spec_tools.remap_gloss', 'pro.spec_tools.restore_original': 'pro.spec_tools.remap_restore',
    'pro.spec_tools.apply_remap': 'pro.spec_tools.remap_apply','pro.header.x': 'pro.header.ui_larger', 'pro.header.make_ui_chrome_smaller': 'pro.header.ui_smaller'}


def _static_items():
    h = SRC.read_text(encoding='utf-8')
    h = re.sub(r'<script\b.*?</script>', '', h, flags=re.S)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)
    p = _P()
    p.feed(h)
    out, seen = [], {}
    for it in p.items:
        a, tag = it['a'], it['tag']
        pan = None
        for cid in reversed(it['ids']):
            if cid in PANEL_MAP:
                pan = cid
                break
        if a.get('id') in PANEL_MAP and not pan:
            pan = a['id']
        lab = _clean(it['text']) or _clean(a.get('aria-label', '')) or _clean(a.get('placeholder', ''))
        title = _clean(a.get('title', ''))
        if tag == 'select' and it['text']:
            opts = [o for o in re.split(r'\s{2,}', it['text'].strip()) if o]
        if tag == 'select':
            lab = _clean(a.get('aria-label', '')) or title
        if not (lab or title or a.get('id')):
            continue
        typ = a.get('type', '')
        kind = {'button': 'button', 'select': 'dropdown', 'summary': 'menu', 'textarea': 'text input', 'a': 'link'}.get(tag) \
            or KIND_OF.get(typ, 'input')
        if a.get('role') == 'tab':
            kind = 'tab'
        panel, where = PANEL_MAP[pan] if pan else (('pro.header', 'Pro > top of the window (header rows)') if not it['ids'] else ('misc', 'Pro > ' + it['ids'][-1]))
        base = a.get('id') or (panel + '.' + _slug(lab or title))
        n = seen.get(base, 0)
        seen[base] = n + 1
        key = base if n == 0 else '%s~%d' % (base, n + 1)
        key = KEY_ALIAS.get(key, key)
        helptxt = title if title and title.lower() != lab.lower() else ''
        fn = re.search(r'([A-Za-z_][\w.]*)\(', a.get('onclick') or a.get('onchange') or a.get('oninput') or '')
        out.append(dict(id=key, label=lab or title, where=where, panel=panel, kind=kind, help_text=helptxt,
                        handler=fn.group(1) if fn else '', dom_id=a.get('id', '')))
    return out


# ----------------------------------------------------------------------------------------------------
# CURATED KNOWLEDGE (buyer words). Vocabulary for `needs`: paint (a paint file is loaded) / psd (a layered PSD is loaded)
# / zone (a zone is selected) / parts (the car's parts are known) / render (a render has been done) / car_folder / none
# ----------------------------------------------------------------------------------------------------
MODES = [
    dict(id='mode.pro', label='PRO', where='Top row > PRO / CHAT / EASY pill (left of SPEC SCULPT)', kind='mode',
         does='The full paint shop: zones, finishes, layers, masks, spec tools, every slider. Everything else is a friendlier front door onto this.',
         when='A buyer wants exact control, or something Chat cannot do (hand-drawn masks, spec sliders, layers, patterns).',
         needs='none', mistakes='New buyers feel lost here - point them at CHAT or EASY first, or at the Tutorial (Training Wheels).',
         related='mode.chat,mode.easy,spbGuideToggle', help_text='PRO - the full paint shop: every tool, layers, masks, zones, Spec Sculpt.'),
    dict(id='mode.chat', label='CHAT', where='Top row > PRO / CHAT / EASY pill', kind='mode',
         does='Talk to Shokker in plain words ("make the hood matte black", "retro red white and blue stripes") and watch the car change. Works with no key; a key or Claude/ChatGPT makes it smarter.',
         when='A buyer does not know which control to use, or just knows the look they want.',
         needs='paint', mistakes='Chat cannot import files, export, or hand-paint. It changes zones and layer settings, and every change has an Undo button.',
         related='ai.panel,ai.input,ai.undo,mode.pro', help_text="CHAT - talk to Shokker: say what you want and watch your car change. Works without any key; an AI key makes it smarter."),
    dict(id='mode.easy', label='EASY', where='Top row > PRO / CHAT / EASY pill', kind='mode',
         does='Paint-by-numbers: Shokker finds the colour parts of your paint, gives each a finish, and you tap a part to change it, then SAVE TO iRACING.',
         when='A buyer wants a finished look fast without learning zones, or wants to restyle each colour / layer of an existing livery.',
         needs='paint', mistakes='Easy and Pro share the same paint and zones; "PRO MODE" in Easy keeps the paint open. Easy builds on the colours it can find - a flat one-colour paint gives one big part.',
         related='easy.rail,easy.tell_input,easy.save,easy.pro_btn', help_text='EASY - paint by numbers.'),
]

PANELS = [
    ('pro.header', 'Pro', 'Header rows', 'Top of the window: iRacing User ID, Number type, Source Paint (TGA / PSD) and iRacing Car Folder. These decide WHAT is painted and WHERE the files go.', 'none'),
    ('pro.modes', 'Any', 'PRO / CHAT / EASY pill', 'Switches between the full shop and the talk-to-Shokker front door. The paint and zones carry across.', 'none'),
    ('pro.toolbar', 'Pro', 'Top toolbar', 'Tool row (Move, Pick, Color, Wand, Lasso, Rect, Brush, Fill, Erase), the HISTORY / SELECT / RETOUCH / MASK / SPEC TOOLS / TRANSFORM / ADJUST menus, the ZONE / LAYER target switch, RENDER HISTORY, Save / Open and Import Recipe.', 'paint'),
    ('pro.settings', 'Pro', 'Settings (gear)', 'Licence key, Keyboard Shortcuts, ZIP export, Live Link / auto-deploy, imported spec map, Training Wheels, file picker style.', 'none'),
    ('pro.zones', 'Pro', 'ZONES (left column)', 'The list of zones, top = highest priority. Each card shows what it covers. + Add Zone, Reset All Zones, More menu. Click a card to open its ZONE POPOUT PANEL.', 'paint'),
    ('pro.zones_more', 'Pro', 'ZONES > More menu', 'Presets Gallery, randomise, Apply Finish to All, Shokker Library, Undo History, templates, SHOKK files, PNG channel export.', 'paint'),
    ('pro.zone_editor', 'Pro', 'ZONE POPOUT PANEL', 'Where one zone is edited: COLOR (which pixels), APPLY AREA (box / lasso), BASE (finish + colour + strengths + spec sliders), SPEC OVERLAYS, PATTERN, OVERLAYS (2nd to 5th base).', 'zone'),
    ('pro.center', 'Pro', 'Centre column', 'The paint (SOURCE) and the LIVE PREVIEW of the finished car, zoom buttons, the RENDER button and the spec channel strip.', 'paint'),
    ('pro.tool_options', 'Pro', 'Tool options bar', 'Appears under the toolbar; its sliders change with the tool you picked (brush size, wand tolerance, text font ...).', 'paint'),
    ('pro.selection_bar', 'Pro', 'Selection / mask bar', 'Under the canvas: Include / Exclude brushes, Undo / Redo, Deselect, Invert, Grow / Shrink / Feather / Smooth, Copy / Mirror mask, Zoom to selection.', 'paint,zone'),
    ('pro.preview', 'Pro', 'Preview and spec channels', 'LIVE PREVIEW of the render plus COMBINED / R METAL / G ROUGH / B COAT views of the spec map.', 'paint'),
    ('pro.render', 'Pro', 'RENDER and recipe card', 'RENDER makes the finished paint + spec TGAs; the recipe card afterwards offers Copy Card, Save Card PNG, Share Recipe, Copy TP Desc, Save to keep, Deploy.', 'paint'),
    ('pro.right', 'Pro', 'Right column', 'Tabs: FINISHES (library) and LAYERS (PSD layers).', 'none'),
    ('pro.layers', 'Pro', 'LAYERS tab', 'The layer list of a PSD / XCF / ORA: eye, name, opacity, blend, lock, ... plus Open Layered, + Layer, Actions, filter box.', 'psd'),
    ('pro.finish_library', 'Pro', 'FINISHES library', 'Full-screen browser of the whole catalogue (about 4,800 looks) with search, filters and favourites.', 'none'),
    ('pro.finish_picker', 'Pro', 'Base Material picker', 'Popup opened from a zone BASE section: search, #hashtag chips (#carbon, #chrome ...), On-Car Stage, Surprise me, See on paint, Color Lock.', 'zone'),
    ('pro.spec_tools', 'Pro', 'Spec Tools', 'Decal Rescue Kit, Lighting Mask, Material Sampler (read M/R/CC of any pixel), Range Remapper. For spec-map fixing.', 'paint'),
    ('pro.dialogs', 'Pro', 'Dialogs', 'Small windows: file browser, dual colour-shift, script export.', 'none'),
    ('pro.history', 'Pro', 'Undo History', 'List of recent actions with Undo / Redo / Clear.', 'paint'),
    ('pro.shokk_library', 'Pro', 'SHOKK files', 'Save or load a whole session (zones + finishes, optionally the paint) as a .shokk file.', 'paint'),
    ('pro.ai', 'Pro / Chat', 'Shokker AI panel', 'The "AI" button (bottom right) opens the copilot: type what you want, it changes zones; each answer has Undo. Gear = key, model, Claude / ChatGPT connection.', 'paint'),
    ('easy', 'Easy', 'Easy mode', 'Full-screen simple view: Tell-Shokker bar, SOURCE and LIVE PREVIEW, the colour-parts rail (tap a part), layer list, WHERE IT GOES drawer and the SAVE TO iRACING button.', 'paint'),
    ('easy.part_panel', 'Easy', 'Part panel (after you tap a part)', 'COLOR REACH slider, Merge with, FINISH picker (Top picks / Categories), ADJUST (blend, size, colour), COLOR choice and PUT IT ON.', 'paint'),
    ('chat', 'Chat', 'Chat mode', 'Pro screen plus the AI copilot opened for talking; same zones, same Undo.', 'paint'),
]

ZE = 'Pro > ZONE POPOUT PANEL (click a zone card in the left column; E shows / hides the panel)'
# key|label|kind|where|does|when|needs|mistakes|related|control_id   (NEW rows: the Pro zone editor is built by JavaScript, read from the live DOM)
ROWS_ZONE = """
zone.reset|Reset Zone|button|{ZE} > top|Puts this one zone back to its defaults (finish, colour, patterns, sliders).|The zone is a mess and you want a clean start for it only.|zone|It resets the zone, not the whole car - Reset All Zones in the left column does that.|pro.zones.reset_all_zones|
zone.section_color|COLOR (section)|section|{ZE} > COLOR|Decides WHICH PIXELS of the paint this zone owns: by clicked colour, by PSD layer, or as catch-all (Remaining).|A buyer says "only the red parts" or "only the numbers".|zone,paint|A zone with no colour, layer or box set does nothing ("No color or region set yet" warning).|zone.restrict_layers,zone.pick_color_from_car,zone.remaining,zone.hex,zone.tolerance|zone_region_scope
zone.restrict_layers|RESTRICT TO LAYERS (checkboxes per PSD layer)|toggle|{ZE} > COLOR > RESTRICT TO LAYERS|Tick a layer (Car Paint, Sponsors, Numbers, Tape ...) and the zone only covers pixels that exist on that layer.|Put a finish on just the numbers / sponsors / tape, or only the body paint, with no colour bleed.|zone,psd|Layers named Mask / Wire / Car_Mandatory are template layers - do not restrict to them. Unticking everything (All layers) removes the restriction.|zone.section_color,layer.eye,zone.pick_color_from_car|zone_region_scope
zone.pick_color_from_car|PICK COLOR FROM CAR|button|{ZE} > COLOR|Arms an eyedropper: click a colour on the car and this zone grabs every pixel of that colour. Each further click ADDS another colour.|Select one colour area (the red stripe, the green body) without drawing anything.|zone,paint|Anti-aliased edges need tolerance; if edges are left over raise tolerance. Colours that also appear on logos need a layer or box restriction.|zone.tolerance,zone.hex,vtModeEyedropper|zone_region_colours
zone.remaining|Remaining|button|{ZE} > COLOR|Makes this zone the catch-all: it gets every pixel no zone above it claims.|The classic body zone - "everything else".|zone|Put it at the BOTTOM of the zone list; higher zones win overlaps.|zone.order|zone_order_priority
zone.hex|HEX (colour box and colour wheel) + Apply|text input|{ZE} > COLOR|Type or pick a colour to select by (with Apply), or use the wheel which applies live.|You know the exact colour of the area you want to select.|zone,paint|This chooses which paint pixels to catch, it does not recolour them. To RECOLOUR use BASE > Base Color > Use solid color.|zone.base_color_mode,zone.tolerance|zone_region_colours
zone.tolerance|Colour tolerance (sliders next to the colour chips)|slider|{ZE} > COLOR|How close a pixel must be to the picked colour to belong to the zone (about 30-50 normal; 6 = exact shade, 100 = loose).|The edges of the area look chewed (raise it) or neighbours get caught (lower it).|zone,paint|Too high grabs neighbouring colours; too low leaves fringes around lettering.|zone.pick_color_from_car|zone_region_colours
zone.hard_edge|Hard Edge|toggle|{ZE} > COLOR|Cuts the zone edge sharp instead of softly anti-aliased.|Crisp lettering and thin lines are getting fuzzy edges.|zone|Hard edges can look jagged on diagonal lines.|zone.section_color|
zone.section_apply_area|APPLY AREA (section)|section|{ZE} > APPLY AREA|Limits the zone to a drawn shape (box or lasso) or a refined colour area, on top of the colour/layer choice.|Only the hood, only the left side, only the bottom half.|zone,paint|"Draw box" boxes are on the flat unwrapped sheet; one box may cover several car panels.|zone.draw_box,zone.lasso,zone.refine_color,zone.activate_area,zone.clear_area|zone_region_scope
zone.draw_box|Draw box|button|{ZE} > APPLY AREA|Click, then drag a rectangle on the paint; the zone only affects what is inside it.|Quick way to restrict a zone to one panel.|zone,paint|The box is on the flat sheet - the hood and the roof are different rectangles, not one.|zone.lasso,zone.clear_area|zone_region_scope
zone.lasso|Lasso (apply area)|button|{ZE} > APPLY AREA|Draw a free-hand outline; the zone only affects what is inside.|The area to restrict is not a rectangle.|zone,paint|Close the shape by returning near the start point.|zone.draw_box|zone_region_scope
zone.refine_color|Refine color|button|{ZE} > APPLY AREA|Keeps the colour selection but lets you paint a green brush to limit it to places you choose.|The colour also shows up where you do not want it.|zone,paint|Needs a colour already set on the zone.|zone.pick_color_from_car,vtModeSpatialInclude|
zone.activate_area|Activate (apply area)|button|{ZE} > APPLY AREA|Turns the stored apply area on again after you cleared or paused it.|You drew an area earlier and it is no longer limiting the zone.|zone|-|zone.clear_area|
zone.clear_area|Clear (apply area)|button|{ZE} > APPLY AREA|Removes the drawn box / lasso so the zone is back to colour/layer only.|The zone is only showing in a box you drew by mistake.|zone|-|zone.draw_box|
zone.fit_into_area|Fit pattern/base swatch into box|toggle|{ZE} > APPLY AREA|Instead of tiling across the sheet, fit one copy of the pattern / base texture into the drawn box.|One big logo-like pattern placed in one area.|zone,paint|Only base + pattern are fitted, not spec overlays.|zone.draw_box|
zone.section_base|BASE (section)|section|{ZE} > BASE|Everything about the surface look: finish, colour source, hue / saturation / brightness, strengths, scale, rotation, spec sliders.|A buyer says "make it chrome / matte / candy / shinier".|zone|Without picking a finish the zone shows source paint unchanged.|zone.base_material,zone.base_color_mode|
zone.base_material|Base Material (finish picker button)|picker|{ZE} > BASE|Opens the finish picker popup: bases (gloss, matte, satin, chrome, candy, pearl, metallic ...) and special looks. Shows the current finish name.|Choose or change the finish of this zone.|zone|Foundation (f_*) finishes change only the spec when colour = Use source paint; bases like chrome / candy repaint the zone.|pro.finish_picker,swatchSearchInput,zone.base_color_mode|
zone.lock_base_color|Lock (Base Color lock)|toggle|{ZE} > BASE > Base Color|When on, switching finish keeps your zone colour instead of auto-adopting the finish's default colour.|Auto colour change keeps overwriting the colour you chose.|zone|-|swatchColorLockBtn|
zone.base_color_mode|BASE COLOR dropdown|dropdown|{ZE} > BASE > Base Color|Where the zone colour comes from: Use finish's own color / Use source paint (spec only) / Use solid color / From special / Custom gradient.|"Keep my colours, change only the shine" (source), "make it exactly this colour" (solid), "fade" (gradient).|zone|Solid colour on a finish that brings its own colours (carbon, camo, holographic ...) flattens it to one colour and loses the pattern: use Hue Shift instead. If a colour 'will not apply', check this dropdown first.|zone.solid_color,zone.hue_shift,zone.gradient|zone_base_colour_mode
zone.solid_color|Solid colour swatch / hex (appears with Use solid color)|picker|{ZE} > BASE > Base Color|Paints the zone this exact colour with the finish's shine on top.|The buyer names an exact colour.|zone|Only used when BASE COLOR = Use solid color.|zone.base_color_mode|zone_solid_colour
zone.gradient|Custom gradient (stops + direction)|section|{ZE} > BASE > Base Color (after choosing Custom gradient)|2 to 10 colour stops fading across the zone in a chosen direction.|"Fade from red to black".|zone|Direction runs on the flat sheet, so each car side may fade differently - use one zone per side to control it.|zone.base_color_mode|zone_gradient
zone.hue_shift|Hue Shift|slider|{ZE} > BASE|Rotates every colour around the colour wheel (-180 to +180). Keeps the finish's structure.|Recolour a finish that brings its own colours, or tweak a colour a bit.|zone|Shift = target hue minus current hue; +150 on green gives purple, not pink.|zone.saturation,zone.brightness|zone_hue_shift
zone.saturation|Saturation|slider|{ZE} > BASE|How vivid or grey the colour is (-100 to +100).|Colours look washed out or too loud.|zone|-|zone.hue_shift|zone_saturation
zone.brightness|Brightness|slider|{ZE} > BASE|Lighter or darker (-100 to +200).|Make a colour darker or lighter without changing the finish.|zone|-|zone.hue_shift|zone_brightness
zone.base_strength|Base Strength|slider|{ZE} > BASE|Fades the whole base look over the source paint: 0 = original paint, 100 = full finish.|A subtle hint of the finish instead of full coverage.|zone|This also reduces colour changes; for shine only use Spec Strength.|zone.spec_strength|zone_base_strength
zone.spec_strength|Spec Strength|slider|{ZE} > BASE|Overall strength of the spec map (shine / metal / coat) of this zone.|Make the finish less (or more) reflective without moving the colour.|zone|-|zone.base_strength,zone.spec_sliders|zone_base_spec_strength
zone.base_scale|Base Scale|slider|{ZE} > BASE|Size of the finish's texture inside this zone (0.05x to 5.0x; 1.00x is normal). Smaller = finer, more repeats.|Texture too coarse or too fine (carbon, flake, camo look huge on the whole car).|zone|Scales the texture, NOT the colours or the whole car; spec follows it unless Independent Spec is ticked.|zone.spec_scale,zone.base_rotation|zone_base_scale
zone.base_rotation|Base Rotation|slider|{ZE} > BASE|Rotates the finish's texture in 5 degree steps.|Weave or brushed grain runs the wrong way.|zone|-|zone.base_scale|zone_base_rotation
zone.color_depth|Color Depth|slider|{ZE} > BASE|For candy / tinted finishes: 0 = no tint, 15 = glaze, 65 = rich, 100 = deepest.|Candy looks pale or too dark.|zone|Only shows on candy-like finishes.|zone.color_flip|zone_colour_depth_flip_underglow
zone.color_flip|Color Flip|slider|{ZE} > BASE|Adds a second hue that appears at an angle (0 = off, 90 = neighbour, 180 = opposite).|Colour-shifting paint.|zone|Only on finishes that support it.|zone.underglow|zone_colour_depth_flip_underglow
zone.underglow|Underglow|slider|{ZE} > BASE|How much of the ground coat burns through the brights.|More glow in highlights on candy / flip paints.|zone|-|zone.color_depth|zone_colour_depth_flip_underglow
zone.independent_spec|Independent Spec (checkbox by Spec Scale)|toggle|{ZE} > BASE|Lets Spec Scale differ from Base Scale; otherwise spec follows the base size.|Want the shine texture finer or coarser than the colour texture.|zone|-|zone.spec_scale|zone_spec_scale_rotation
zone.spec_scale|Spec Scale|slider|{ZE} > BASE|Size of the shine / metal texture (0.05x-5.0x) when independent.|Fine shine detail under a coarse colour pattern.|zone|Ignored until Independent Spec is ticked.|zone.base_scale,zone.independent_spec|zone_spec_scale_rotation
zone.spec_rotation|Spec Rotation|slider|{ZE} > BASE|Rotates the spec channels in 5 degree steps.|Brushed grain in the shine runs the wrong way.|zone|-|zone.spec_scale|zone_spec_scale_rotation
zone.spec_blend|Spec Blend|dropdown|{ZE} > BASE|How a pattern changes this base's optics: Normal, Ghost Carve, Chrome Inlay, Frost Etch, Angle Flip, Ember Gate, Depth Press, and legacy Multiply / Screen / Overlay modes.|Pattern should alter shine / metal rather than just brightness.|zone|-|zone.pattern|zone_spec_channel_shift
zone.spec_sliders|Spec Sliders (R Metal, G Rough, B Coat)|section|{ZE} > BASE > Spec Sliders|Three sliders (-127 to +127) that push the whole zone's spec map: R = metal, G = roughness (low = mirror), B = clearcoat.|Make the zone shinier / more metallic / matte without changing the finish: "make the spec shinier only".|zone|B Coat is inverted in iRacing terms - the number moves clearcoat strength, see the tooltip. Spec only changes in the spec map and in iRacing; the flat colour preview may look unchanged.|zone.r_metal,zone.g_rough,zone.b_coat,zone.auto_pop,zone.spec_preset|zone_spec_channel_shift
zone.auto_pop|Auto-Pop|button|{ZE} > BASE > Spec Sliders|One click nudges the three spec sliders toward glossier (more metal flash, less rough, deeper clearcoat) so the zone pops on track.|Fast "make it shinier" without thinking about channels.|zone|It nudges from where the sliders are; press repeatedly for more, Reset arrows to go back.|zone.spec_sliders|zone_spec_channel_shift
zone.spec_preset|Spec preset... dropdown|dropdown|{ZE} > BASE > Spec Sliders|Applies a named spec feel (Wet Candy, Track Flash, Chrome Mirror, Deep Gloss, Soft Pearl, Satin Matte) to the R/G/B sliders.|You want a known shine character.|zone|-|zone.spec_sliders|zone_spec_channel_shift
zone.save_spec_preset|Save spec preset (disk icon)|button|{ZE} > BASE > Spec Sliders|Saves this zone's R/G/B spec shifts under a name you can reuse.|You found a shine you like.|zone|-|zone.spec_preset|
zone.r_metal|R Metal|slider|{ZE} > BASE > Spec Sliders|Pushes the METAL channel (-127 to +127). More metal = the body colour flashes harder.|Metal looks too weak or too much.|zone|-|zone.spec_sliders|zone_spec_channel_shift
zone.g_rough|G Rough|slider|{ZE} > BASE > Spec Sliders|Pushes ROUGHNESS (-127 to +127). Lower = sharper mirror flashes, higher = soft satin glow.|Too shiny or too dull.|zone|-|zone.spec_sliders|zone_spec_channel_shift
zone.b_coat|B Coat|slider|{ZE} > BASE > Spec Sliders|Pushes CLEARCOAT (-127 to +127). 16 is max gloss: minus = glossier (stops at 16), plus = duller.|Wants a glassier or flatter clearcoat.|zone|-|zone.spec_sliders|zone_spec_channel_shift
zone.section_spec_overlays|SPEC OVERLAYS + ADD SPEC OVERLAY|section|{ZE} > BASE > SPEC OVERLAYS|Stack spec-only textures on top of the base: they change shine / metal / roughness patterns, never the colour.|Brushed metal, hammered, scratched or carbon-weave SHINE under flat colour.|zone|Colour preview will not show them; look at the spec channel views.|zone.add_spec_overlay,pro.preview|zone_spec_pattern_stack
zone.add_spec_overlay|+ ADD SPEC OVERLAY|button|{ZE} > BASE > SPEC OVERLAYS|Opens the spec-overlay picker to add one more spec texture layer.|Add a shine texture.|zone|Up to 5 layers on the primary base.|zone.section_spec_overlays|zone_spec_pattern_stack
zone.section_pattern|PATTERN (section)|section|{ZE} > PATTERN|Adds a visible pattern (carbon, camo, flames, stripes ...) on this zone, with Paint mode, Opacity, Strength, Hue, Saturation, Spec amount, Scale, Rotate and Position.|A buyer wants a pattern on the paint.|zone|-|zone.pattern,zone.pattern_scale,zone.pattern_paint_mode|zone_pattern_id
zone.pattern|Pattern 1 picker (name + dropdown arrow)|picker|{ZE} > PATTERN|Choose the pattern from the catalogue; "None" (x) removes it.|Add or remove a pattern.|zone|-|zone.section_pattern|zone_pattern_id
zone.add_pattern_layer|+ Add Layer (pattern)|button|{ZE} > PATTERN|Adds a second / third pattern layer to the zone.|Combine patterns.|zone|-|zone.pattern|zone_pattern_layers
zone.pattern_paint_mode|Paint mode (Overlay / Blend)|dropdown|{ZE} > PATTERN|Overlay = the pattern paints its own colours over the paint; Blend = it keeps the underlying paint colour.|The pattern covers the colour you chose (use Blend), or will not take your colour.|zone|In Overlay the pattern's own colours win, so the base colour is hidden - use Blend or Hue to recolour.|zone.pattern_hue,zone.pattern|zone_pattern_paint_mode
zone.pattern_opacity|Opacity (pattern)|slider|{ZE} > PATTERN|How visible the pattern is, 0-100%.|Pattern too loud.|zone|-|zone.pattern_strength|zone_pattern_opacity
zone.pattern_strength|Strength (pattern)|slider|{ZE} > PATTERN|Pattern paint strength in 5% steps; spec amount is separate.|-|zone|-|zone.pattern_opacity|zone_pattern_strength
zone.pattern_hue|Hue / Saturation (pattern)|slider|{ZE} > PATTERN|Recolours only the pattern artwork (hue -180..180, saturation -100..100). Overlay mode uses this colour.|Pattern has the wrong colour but the base colour is right.|zone|-|zone.pattern_paint_mode|zone_pattern_hue_sat
zone.pattern_spec_amount|Spec amount (pattern)|slider|{ZE} > PATTERN|Starts at 0% so your base shine stays; raise to reveal the pattern's own metal / rough / coat.|Pattern should also change the shine.|zone|Spec starts at 0 on purpose.|zone.spec_sliders|zone_pattern_strength
zone.pattern_scale|Scale (pattern)|slider|{ZE} > PATTERN|Size of the pattern: smaller = more repeats, larger = zoomed in (0.1x to 4x).|"Crush the pattern finer", or make it bigger.|zone|On a whole-car canvas a normal-size pattern looks huge: go below 1.0x for fine detail.|zone.pattern_rotation,zone.base_scale|zone_pattern_scale
zone.pattern_rotation|Rotate (pattern)|slider|{ZE} > PATTERN|Rotates the pattern 0-359 degrees (also a number box).|Stripes / weave at the wrong angle.|zone|-|zone.pattern_scale|zone_pattern_rotation
zone.pattern_placement|Pattern placement: Full Canvas / Fit to Zone / Edit on Template|button|{ZE} > PATTERN|Choose how the pattern is placed: tiled over the sheet, fitted to the zone, or dragged by hand on the template.|Place a pattern on one spot.|zone,paint|-|zone.pattern_position|zone_pattern_placement
zone.pattern_position|Advanced Pattern Control Panel (Position X / Y, Flip H / V, Strength Map)|section|{ZE} > PATTERN > Advanced Pattern Control Panel|Slide the pattern left/right and up/down, flip it, or paint where it is strong versus weak.|Fine placement.|zone|-|zone.pattern_placement|zone_pattern_placement
zone.section_overlays|OVERLAYS (2nd to 5th base)|section|{ZE} > OVERLAYS|Stack extra base finishes over the first with blend modes.|Chrome flake over candy, matte clear on gloss, etc.|zone|-|zone.second_base|zone_second_base
zone.second_base|2nd Base (picker) + Add 3rd overlay|picker|{ZE} > OVERLAYS|Pick a second finish blended on top of the primary base; "+ Add 3rd overlay" shows the next slot.|Two-layer looks.|zone|-|zone.section_overlays|zone_second_base
zone.order|Zone order (drag handle and priority)|section|Pro > left column > zone cards (drag the handle)|Top zone wins where two zones select the same pixels.|"Why is my zone not showing?" - another zone above it already claims those pixels.|zone|Remaining belongs at the bottom.|pro.zones|zone_order_priority
zone.mute|Zone eye / duplicate / link / x icons on each zone card|button|Pro > left column > zone card|Eye hides a zone for testing, the copy icon duplicates, the x deletes it.|Temporarily see the car without a zone; copy a zone to reuse its look.|zone|x removes the zone (undoable with Ctrl+Z).|pro.zones|zone_mute
"""

ROWS_LAYERS = """
layer.eye|Layer eye icon|toggle|Pro > LAYERS tab > layer row|Shows / hides the layer. Alt+click isolates that layer.|Turn template layers (Mask, Wire, Car_Mandatory) OFF before export; hide a sponsor to see the paint under it.|psd|Leaving Mask / Wire / Car_Mandatory on paints them into the car.|pro.render,layer.search|
layer.opacity|Layer opacity|slider|Pro > LAYERS tab > layer row|Fades the layer 0-100% (drag, or type an exact number).|A sponsor or decal is too strong.|psd|-|layer.blend|
layer.blend|Layer blend mode|dropdown|Pro > LAYERS tab > layer row|How the layer mixes with those below (Normal, Multiply, Screen, Overlay ...).|Wants a shadow / glow effect.|psd|-|layer.opacity|
layer.lock|Layer lock|toggle|Pro > LAYERS tab > layer row|Locks the layer so it cannot be painted or changed.|Protect finished art.|psd|The Shokker AI cannot edit locked layers - unlock first.|layer.eye|
layer.make_zone|Create a zone restricted to this layer|button|Pro > LAYERS tab > layer row (zone icon)|One click makes a zone that only covers this layer's pixels; then give it a finish.|"Make the numbers chrome": the quickest exact way.|psd|-|zone.restrict_layers|
layer.lock_zone|Lock the active zone to this layer (Ctrl+L)|button|Pro > LAYERS tab > layer row|Restricts the currently selected zone to this layer.|You already have the zone and want it limited to one layer.|psd,zone|-|zone.restrict_layers|
layer.rename|Rename / duplicate / delete / merge / flip / rotate / effects icons|button|Pro > LAYERS tab > layer row|Standard layer housekeeping: rename, duplicate (Shift = offset copy), delete, merge into the layer below, flip, rotate 90 degrees, Layer Effects (drop shadow, glow, stroke, colour overlay, bevel).|Fix or reuse art.|psd|Delete removes the layer art from the document; use the eye to just hide it.|layerActionsMenuBtn|
layer.search|Filter layers box|text input|Pro > LAYERS tab > top right|Type part of a layer name or group to narrow a long list; Escape clears.|A PSD with dozens of layers.|psd|There is no sort-by-colour: the list is in PSD order. To work BY COLOUR use a zone with PICK COLOR FROM CAR.|zone.pick_color_from_car|
layer.row_select|Layer name (click) / Ctrl+click / double-click|button|Pro > LAYERS tab > layer row|Click selects the layer; Ctrl+click moves it on the canvas; double-click opens Layer Effects.|Edit just that layer.|psd|-|layer.eye|
"""

ROWS_EASY = """
easy.tell_input|Tell Shokker what you want... bar|text input|Easy > bar above the car|Type a sentence like "make the brown carbon", "numbers gold chrome", "everything matte black"; Enter or Do it applies.|Fastest way to restyle a part or the whole car.|paint|It understands colour-part names Shokker found on this paint ("the brown", "the numbers"). If unsure it asks or uses the AI when one is on.|easy.tell_go,easy.tell_help,easy.tell_dice|
easy.tell_go|Do it|button|Easy > Tell bar|Runs what you typed.|-|paint|-|easy.tell_input|
easy.tell_dice|Dice (Surprise me)|button|Easy > Tell bar|Makes a whole new random look.|Wants ideas.|paint|-|easy.tell_input|
easy.tell_help|? (What can I say?)|button|Easy > Tell bar|Shows example sentences you can type.|Not sure what to say.|none|-|easy.tell_input|
easy.tell_ai|AI toggle (in the Tell bar)|toggle|Easy > Tell bar|Lets an AI step in when the built-in parser is unsure.|Odd requests.|paint|Needs a key or Claude connection set in the gear of the AI panel.|ai.gear|
easy.undo|UNDO / REDO|button|Easy > top right|Takes back or repeats the last Easy change (also Ctrl+Z / Ctrl+Y).|Did something you did not like.|paint|-|easy.start_over|
easy.start_over|START OVER|button|Easy > top right|Clears every finish and colour you picked for this car.|You want a blank slate.|paint|It clears finishes, it does not unload the paint.|easy.undo|
easy.pro_btn|PRO MODE ->|button|Easy > top right|Opens the full Pro editor with the same paint still open.|Easy cannot do what the buyer needs.|paint|-|mode.pro|
easy.source|SOURCE (untouched paint) with INSPECT|panel|Easy > left of the stage|Your original paint exactly as loaded; INSPECT zooms to the real pixels.|Compare before and after.|paint|-|easy.live|
easy.live|LIVE PREVIEW (AS PAINTED / IN THE LIGHT)|panel|Easy > right of the stage|The finished car as Shokker will render it; IN THE LIGHT shows how the spec map lights it.|Judging the look.|paint|If it does not change after an edit, press Refresh in Pro or re-apply; flat-TGA previews can lag.|easy.channels|
easy.channels|COMBINED SPEC / RED METAL / GREEN ROUGH / BLUE COAT strip|panel|Easy > under the stage|The four spec-map views: brighter red = more metal, darker green = sharper mirror, darker blue = glassier coat.|Understanding why a finish shines the way it does.|paint|-|pro.preview|
easy.rail|Colour-parts rail ("YOUR CAR - BUILT FOR YOU")|panel|Easy > right rail|Shokker found the colours of your paint and gave each one a finish. Tap a part (or tap the car) to change its finish.|Restyle one colour area of a livery.|paint|One part = one colour; the same colour on body and sponsor is one part (use layers below, or Pro layer restriction).|easy.part_panel,easy.pick_color,easy.rebuild|
easy.try_a_look|TRY A LOOK (Show car, Subtle OEM, Candy shop, Matte & chrome)|button|Easy > right rail|One-click whole-car style recipes applied to all the colour parts.|Wants a quick complete look.|paint|Overwrites the finishes you chose per part (Undo brings them back).|easy.undo|
easy.pick_color|Pick a color off the car|button|Easy > right rail|Click any colour on the car to make it its own part.|A colour was missed or merged.|paint|-|easy.rebuild|
easy.rebuild|Find the parts again|button|Easy > right rail|Re-reads the paint and rebuilds the colour parts.|Parts look wrong after changing the paint.|paint|Finish choices for matching parts are kept.|easy.rail|
easy.hints|Hide the helper hints|toggle|Easy > right rail|Shows or hides the small written hints under controls.|-|none|-|easy.rail|
easy.template_guides|Template guides are on - Turn off|button|Easy > right rail warning|Hides the template layers (Car Mandatory, Mask, Wire) that would otherwise be painted into your car.|The warning is showing before SAVE.|psd|The save button asks you to turn them off first.|layer.eye|
easy.part_back|PARTS (back)|button|Easy part panel|Returns from one part to the list of parts.|-|paint|-|easy.rail|
easy.color_reach|COLOR REACH|slider|Easy part panel|How many shades of this colour belong to the part: right catches shadows, gradients and anti-aliased edges; the orange highlight on the car shows exactly what it catches.|Part leaves bits behind (raise) or grabs neighbours (lower).|paint|This is the same idea as Pro colour tolerance.|zone.tolerance|zone_region_colours
easy.merge_with|Merge with (another colour...)|dropdown|Easy part panel|Merges this colour part into another so they share a finish.|Two shades should be one part.|paint|-|easy.rail|
easy.finish_picker|FINISH (Top picks / Categories cards)|picker|Easy part panel|Cards with a real thumbnail for each finish; COLOR and SHINE chips on each card say what it changes. Tap one to apply it to the part.|Choose a finish.|paint|Cards marked COLOR bring their own colours; SHINE-only cards keep your paint colour.|easy.color_choice,easy.put_it_on|
easy.adjust|ADJUST (blend, size, colour)|section|Easy part panel|BLEND mixes the finish with the existing paint, SIZE changes how big its texture reads on the car, COLOR shifts its colour.|Finish too strong / too coarse / wrong colour.|paint|-|zone.base_strength,zone.base_scale,zone.hue_shift|zone_base_strength
easy.color_choice|COLOR (Finish's color / Keep <colour> / Pick...)|dropdown|Easy part panel|Choose where the part's colour comes from: the finish's own colours, keep the colour you already have, or pick a new one.|The colour is not what you expect after choosing a finish.|paint|A solid pick on a finish that brings its own colours flattens it; keep the finish's colour and use ADJUST > COLOR.|zone.base_color_mode|zone_base_colour_mode
easy.put_it_on|PUT IT ON (This part / Every color / Shine only - whole car)|button|Easy part panel|Where to apply the finish: just this part, all colour parts, or a spec-only shine on the whole car that leaves colours alone.|Apply one finish everywhere, or only change shine.|paint|-|easy.finish_picker|
easy.layers|LAYERS list (tap a layer to style, sparkle button to tell Shokker)|panel|Easy > right rail bottom|One row per PSD layer. Tap to pick a finish for only that layer; the sparkle button lets you type what you want for it.|Style the numbers or sponsors on their own.|psd|Needs a layered PSD; a flat TGA shows no layers.|layer.eye|
easy.where_it_goes|WHERE IT GOES (car, number type, customer ID)|section|Easy > right rail|Choose your iRacing car folder, Custom or Sim-stamped number, and iRacing customer ID.|Files must land where iRacing looks.|none|Wrong customer ID or wrong car folder = paint does not show in iRacing.|easy.save,pro.header|
easy.readiness|READY TO RACE? checklist|panel|Easy > right rail|Green ticks for paint, customer ID, car chosen, finish picked; arrows show what is missing.|SAVE is greyed out and the buyer does not know why.|paint|-|easy.save|
easy.save|SAVE TO iRACING (shows CHOOSE AN iRACING CAR until ready)|button|Easy > bottom of rail|Renders at full size and writes the paint and spec TGAs into the iRacing car folder.|Finishing and getting the paint into the sim.|paint,car_folder|Say what it is waiting for: pick the car, enter the ID, turn template guides off.|pro.render,easy.where_it_goes|
easy.bigger_picture|BIGGER PICTURE|button|Easy > rail edge|Folds the controls away so the car fills the window.|Judging the look.|paint|-|easy.rail|
"""

ROWS_AI = """
ai.fab|AI button (bottom right)|button|Pro > bottom right corner|Opens the Shokker AI panel (the copilot).|Wants to talk to the app.|paint|-|ai.panel|
ai.panel|Shokker AI panel|panel|Pro / Chat > bottom right|Chat window: type what you want, the copilot changes zones and layers. Works with no key for common requests (colours, matte / gloss / chrome, stripes, spec looks).|"Make the hood matte black", "retro red white and blue".|paint|It cannot import files, export, or hand-paint; it can only tell the buyer where to click.|ai.input,ai.undo,ai.gear|
ai.input|Tell me what you want... box|text input|Shokker AI panel|Type your request; Enter sends, Shift+Enter adds a line.|-|paint|-|ai.panel|
ai.attach|Attach a picture|button|Shokker AI panel|Attach a livery you like, a logo or a flag; the AI can copy its design or colours (needs an AI key).|Copy the style of a picture.|paint|Cheap models cannot read UV sheets; results may need correcting.|ai.panel|
ai.undo|Undo (under each answer)|button|Shokker AI panel|Puts everything back the way it was before that answer (all zones and layer changes of that answer).|The change was wrong.|paint|-|ai.panel|
ai.another|Another take / Refine / Ask the AI|button|Shokker AI panel|Another try with a different idea; Refine looks at the preview and fixes what is off; Ask the AI undoes and lets the AI have a go.|Not happy with the first answer.|paint|-|ai.undo|
ai.gear|Gear (key, model, daily cap, Claude / ChatGPT connection)|button|Shokker AI panel > top|Settings: your OpenRouter key and model (one model only), a daily spending cap, and "Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth" with Install in Claude Desktop / Connect ChatGPT.|Wants a smarter copilot, or to use their own Claude / ChatGPT plan.|none|The gear MODEL only applies to the in-app copilot; Claude Desktop uses its own model. Use Take over in SPB before asking the in-app copilot while an external assistant has control.|mcp.claude,mcp.chatgpt|
mcp.claude|Use Claude Desktop through MCP|toggle|Shokker AI panel > gear|Install Shokker into Claude Desktop, then ask Claude "Using Shokker Paint Booth, give me a Gulf-style livery". Changes appear in the AI panel with Undo.|Wants Claude to design the livery with the buyer's own plan.|paint|Restart Claude Desktop after installing; Shokker must be open.|ai.gear|
mcp.chatgpt|Connect ChatGPT / Codex|toggle|Shokker AI panel > gear > bridge settings|Add SPB to Codex settings, restart Codex and sign in with ChatGPT.|Wants ChatGPT / Codex to drive Shokker.|paint|Your subscription limits apply.|ai.gear|
"""

# static overlay: key|does|when|needs|mistakes|related   (only where the DOM title is not already buyer-friendly)
CUR = """
paintFile|The paint file Shokker works on (a flat TGA / PNG / JPEG, or a PSD): type or paste a path, or use the buttons beside it.|Start of every job; "I loaded my paint and nothing happened".|none|Pasting a folder path here does not load a paint. A flat TGA has no layers; a PSD does.|pro.header.tga_png_jpeg,pro.header.psd_xcf_ora,onboardingImportPsdBtn
pro.header.tga_png_jpeg|Browse for a flat paint picture (TGA / PNG / JPEG / BMP) and load it as the paint.|You have a single flat paint file.|none|Dropping an image on the canvas also REPLACES the paint; it does not add a logo (use + Layer for that).|paintFile,pro.header.psd_xcf_ora
pro.header.psd_xcf_ora|Browse for a layered PSD / XCF / ORA template so every layer (body, numbers, sponsors, tape) stays separate.|You want layer-level control: numbers only, sponsors only.|none|Make sure the template layers (Mask, Wire, Car_Mandatory) are OFF before exporting.|onboardingImportPsdBtn,pro.layers.open_layered
outputDir|The iRacing car folder the finished paint and spec files are written to.|Paint is not showing in iRacing, or choosing which car.|none|Point to the car FOLDER, not a TGA file. It sets the file names car_num_ID.tga or car_ID.tga and car_spec_ID.tga.|carPickBtn,iracingId
carPickBtn|Pick your car from the list of iRacing cars Shokker detected (most recently painted first).|Faster than browsing for the folder.|none|If your car is missing, paint it once in iRacing or browse for the folder.|outputDir
iracingId|Your iRacing customer number (4-7 digits); it is part of the saved file names.|First setup; paint does not show in iRacing.|none|A wrong ID means iRacing ignores the files.|outputDir
useCustomNumberCheckbox|Custom Number: the number is part of your paint and iRacing will not add one.|You drew your own number.|none|Needs Settings > Graphics > Hide Car Numbers ON in iRacing to load car_num_.|useSimStampedCheckbox
useSimStampedCheckbox|Sim-Stamped Number: iRacing stamps your number on the car in the series font.|You want iRacing to place the number.|none|Do not also paint a number on the template.|useCustomNumberCheckbox
spbModeProBtn|Switch to the full Pro shop.|-|none|-|mode.pro
spbModeChatBtn|Switch to Chat (talk to Shokker).|-|none|-|mode.chat
spbModeEasyBtn|Switch to Easy (paint by numbers).|-|none|-|mode.easy
spbGuideToggle|Training Wheels: step-by-step quests that teach the app as you use it (load, zone, finish, render, then patterns, spec, overlays), plus a hint chip for your next move.|A buyer says "I'm lost" or "what now".|none|Toggle it any time; it is also a checkbox in Settings.|trainingWheelsCheckbox
btnFractureThisPaint|One click puts a Soul Core Emerald / Pink Flash finish into the selected zone's base (and its colour unless Color Lock is on).|A quick dramatic look.|zone|Changes the zone's colour too unless the Lock is on.|zone.lock_base_color
settingsGearBtn|Opens Settings: licence, keyboard shortcuts, ZIP export, spec map import, Live Link, Training Wheels.|Licence problems, auto-copy to iRacing.|none|-|liveLinkCheckbox,exportZipCheckbox
liveLinkCheckbox|Auto-deploy: copies every render to your iRacing car folder automatically.|Paint is not reaching iRacing.|car_folder|Only matters when the car folder is empty; with a car folder set, files are copied after each render anyway.|outputDir
exportZipCheckbox|Bundles paint TGA, spec TGA and preview into a ZIP on every render.|Share or archive.|none|-|btnRender
pro.settings.import_tga|Import an existing spec map TGA to merge under your render.|You made a spec map elsewhere.|paint|Use Clear to go back to the default spec.|btnClearSpecMap
vtModeLayerMove|Move tool (V): in Layer mode click a sponsor / number to drag it; Alt forces the whole layer.|Move or resize a number or logo.|psd|Switch ZONE / LAYER to LAYER first.|btnToolbarModeLayer
vtModePickItem|Pick Item (Y): pick one sponsor / number inside a layer for independent move / rotate.|Move a single logo on a crowded layer.|psd|-|vtModeLayerPick
vtModeEyedropper|Color (P): click a colour on the paint to select by it. In Pro zone mode it feeds the selected zone's colour list.|Select a colour area for a zone.|zone,paint|-|zone.pick_color_from_car,eyedropperAddColorBtn
vtModeWand|Magic Wand (W): click to select similar colour; Shift adds, Alt subtracts; Tolerance sets how similar.|Select an area by colour on the canvas.|paint|-|wandTolerance
vtModeLasso|Lasso (L): draw a free-hand selection.|Select an odd-shaped area.|paint|Enter closes the shape.|vtModeRect
vtModeRect|Rectangle select (O): drag a box selection.|Select a panel.|paint|-|vtModeLasso
vtModeBrush|Brush (B): paint the zone's mask, or the selected layer's pixels.|Hand-draw where a zone applies.|paint|ZONE mode paints a mask; LAYER mode paints pixels.|btnToolbarModeZone,brushSize
vtModeFill|Fill bucket (K): fill a region of the zone mask or the layer.|Fill a closed area.|paint|-|vtModeBrush
vtModeErase|Eraser (E): erase zone mask or layer pixels.|Fix an overpaint.|paint|-|vtModeBrush
vtModeGrabObject|Grab Object (G): click inside a number or logo and its whole outline is selected.|Select the numbers on a flat TGA.|paint|Works best on clear solid shapes.|vtModeSelectAll
vtModeSelectAll|Select All Color (A): select every pixel of the sampled colour across the whole paint.|Select all of one colour.|paint|-|vtModeWand
vtModeEdge|Smart Region Fill: click inside an edge-bounded area to select it.|Select a stripe or panel bounded by lines.|paint|-|wandTolerance
vtModeZonePick|Zone Pick: click a spec pattern / base piece to move, rotate and resize it independently.|Adjust one pattern piece.|zone|-|vtModePickItem
vtModeColorBrush|Color Brush (C): paint solid colour or a pattern brush onto the selected layer.|Retouch artwork.|psd|Needs a blank paintable layer (use + Blank layer).|pro.layers.blank_layer
vtModeRecolor|Recolor (R): paint a new hue over a sampled colour on the selected layer.|Recolour a sponsor.|psd|-|pro.toolbar.color_replace
btnToolbarModeZone|ZONE mode: toolbar tools edit zones and masks.|Making areas for finishes.|paint|Tools behave differently in ZONE vs LAYER mode - check this switch if a tool "does nothing".|btnToolbarModeLayer
btnToolbarModeLayer|LAYER mode: toolbar tools edit the selected layer's pixels.|Moving / painting artwork.|psd|-|btnToolbarModeZone
pro.toolbar.undo_ctrl_z|Undo the last stroke, transform or layer action (Ctrl+Z).|Any mistake.|paint|-|pro.toolbar.redo_ctrl_y,pro.history.undo
pro.toolbar.redo_ctrl_y|Redo (Ctrl+Y or Ctrl+Shift+Z).|-|paint|-|pro.toolbar.undo_ctrl_z
pro.toolbar.undo_history|Opens the recent-actions list so you can jump back several steps.|Undo more than one step.|paint|-|pro.history.undo
spbProjectsButton|Save / Open: saves or loads a complete workflow in one file (paint incl. PSD, every zone, all layer settings).|Come back to a project later.|paint|There is no File menu; this is the save.|pro.toolbar.import_recipe
pro.toolbar.import_recipe|Imports a .shokkerrecipe (yours or shared) and restores the recipe (colours, finishes, effects) on this car.|Use a shared look.|paint|-|spbProjectsButton
pro.toolbar.decal_rescue_kit|Puts a flat / satin / gloss NON-metallic spec under sim-stamped numbers and sponsors so they read cleanly.|Numbers or sponsors look wrong under chrome or candy.|paint|-|pro.toolbar.lighting_mask
pro.toolbar.lighting_mask|Controls the spec alpha channel (fake holes, grille openings, recessed vents).|Fake a vent or grille.|paint|Advanced.|pro.toolbar.material_sampler
pro.toolbar.material_sampler|Click the compiled spec map to read exact Metallic / Roughness / Clearcoat values and copy them to a zone.|Measure what the spec map really says.|render|-|pro.preview
pro.toolbar.range_remapper|Retunes Metallic / Roughness / Clearcoat ranges inside the active zone while keeping the texture.|Make a spec texture subtler or stronger overall.|zone|-|zone.spec_sliders
pro.toolbar.hue_saturation|Shifts hue and saturation of the selected layer or paint.|Recolour artwork.|psd|Applies to pixels, unlike zone Hue Shift which is a render setting.|zone.hue_shift
pro.toolbar.color_replace|Replaces one colour with another everywhere on the layer or paint.|Recolour the numbers or a stripe.|paint|This edits pixels; for finishes use a zone.|pro.toolbar.hue_saturation
pro.toolbar.recent|Recent Renders: recall one of your last 10 saved renders and restore its recipe.|Go back to an earlier look.|render|-|pro.toolbar.gallery
pro.zones.add_zone|Adds an empty zone at the top.|A new look for a new area.|paint|A new zone does nothing until you give it a colour / layer / box AND a finish.|pro.zones.reset_all_zones
pro.zones.reset_all_zones|Resets to the default set of zones (confirmed, undoable).|Start over with finishes.|paint|-|pro.zones.add_zone
pro.zones.more|Opens the More menu (presets, randomise, apply to all, library, templates, SHOKK files, channel PNG export).|Less common tools.|paint|-|pro.zones_more.presets_gallery
pro.zones_more.presets_gallery|Browse ready-made zone layouts / looks and apply one.|Quick starting look.|paint|-|pro.zones_more.shokker_library
pro.zones_more.apply_finish_to_all|Gives the same finish to every zone.|Uniform finish.|paint|-|pro.zones_more.rand_all_zones
pro.zones_more.save_shokk|Saves the zones and finishes (and optionally the paint) as a .shokk file.|Share or back up a setup.|paint|-|pro.zones_more.load_shokk_file
pro.zones_more.png_channels_export|Exports the paint and the spec channels as PNG pictures for inspection or Photoshop.|Check or edit the spec in another app.|render|-|pro.preview
btnRender|RENDER (Ctrl+R): builds the finished paint TGA and the spec TGA and writes them to the iRacing car folder.|When the look is right and you want it in iRacing.|paint,car_folder|It will not start if the paint, customer ID or car folder is missing, or template layers are still on.|pro.render,easy.save
btnPreviewRefresh|Refresh preview (F5): aborts a stuck render and re-runs the live preview.|Preview is stale, blank or not changing.|paint|-|pro.preview
btnBeforeAfter|Before / After (B): compare the last preview with the current one.|See what a change did.|render|-|btnCompare
btnSpecMapInspector|Channels inspector: spec map channels with numeric values.|Understand the shine.|render|-|pro.preview
btnSourceFocus|Edit Big: hide the live preview and edit the source canvas larger.|Precise selection work.|paint|-|btnCanvasViewSource
btnCanvasViewSource|SOURCE view: the original paint canvas where tools work.|-|paint|-|btnCanvasViewRendered
btnCanvasViewRendered|CAR view: show the rendered car under the canvas while tools stay active.|Judge the look.|paint|-|btnSplitView
btnSplitView|SPLIT view (Shift+V): source and live preview side by side.|Compare while editing.|paint|-|btnCanvasViewSource
pro.preview.r_metal|Red channel of the spec map: Metallic (brighter = more metal).|Check metal.|render|-|pro.preview.g_rough
pro.preview.g_rough|Green channel: Roughness (darker = mirror, lighter = matte).|Check shine.|render|-|pro.preview.b_coat
pro.preview.b_coat|Blue channel: Clearcoat (16 = max gloss, 255 = dull).|Check coat.|render|-|pro.preview.r_metal
pro.render.copy_card|Copies the recipe card picture to the clipboard (paste into Discord).|Share the look.|render|-|pro.render.save_card_png
pro.render.share_recipe|Downloads this look as a .shokkerrecipe file with preview.|Share the recipe.|render|-|pro.toolbar.import_recipe
btnSaveToKeep|Copies this render to a subfolder so the next render does not overwrite it.|Keep a version.|render|-|pro.render.recent_renders
rpTabFinishes|FINISHES tab: opens the full-screen finish library.|Browse looks without a zone.|none|-|pro.finish_library
rpTabLayers|LAYERS tab: PSD layer list.|-|psd|-|pro.layers
pro.layers.open_layered|Import a layered PSD / XCF / ORA with its layer tree.|You have a layered template.|none|-|onboardingImportPsdBtn
pro.layers.layer|+ Layer: adds a PNG / JPG / WebP / GIF as a NEW image layer on top (a logo, a sponsor).|Add a logo.|psd|Dropping a file on the canvas instead REPLACES the paint.|layer.rename
layerActionsMenuBtn|Actions: + Blank layer, Flatten document, Merge visible, Photoshop round-trip, Thumbnail size.|Document-wide layer operations.|psd|Flatten discards layer separation.|pro.layers.open_layered
finishSearch|Search the finish library by name, description or #tag.|Find a look by words.|none|Try plain words ("gold chrome") or hashtags (#carbon).|swatchSearchInput
swatchSearchInput|Search finishes in the base picker by name, idea or #tag.|Find a finish for the zone.|zone|-|swatchDiceBtn
swatchColorLockBtn|Color Lock: when ON, picking a finish keeps your current colour instead of adopting the finish's default.|Colour keeps changing when you change finish.|zone|-|zone.lock_base_color
swatchDiceBtn|Surprise me: rolls a high-ranked finish onto the On-Car Stage; confirm with Enter / click.|Want ideas.|zone|-|swatchStageUseBtn
swatchStageUseBtn|USE IT: applies the previewed finish to this zone.|-|zone|-|swatchDiceBtn
swatchSeeOnPaintBtn|See on paint: previews the selected finish on your paint file.|Check before applying.|paint|-|swatchStageUseBtn
fbSearch|Search the catalogue browser.|-|none|-|fbFilterType
brushSize|Brush / eraser size in pixels (1-300); [ and ] keys change it.|-|paint|-|brushHardness
wandTolerance|How different a colour can be and still get picked (higher = more colours).|Wand picks too little or too much.|paint|-|vtModeWand
overlayOpacity|Zone overlay opacity: how strongly the zone colour overlay shows on the canvas (default 50%).|Overlay hides the paint.|zone|-|vtModeSpatialInclude
eyedropperAddColorBtn|+ Add Color: adds the clicked colour to the chosen zone.|Select several colours in one zone.|zone,paint|-|zone.pick_color_from_car
eyedropperSetBtn|Set: replaces the zone's colour with this single colour.|-|zone|-|eyedropperAddColorBtn
useRegionBtn|Use Region: gives the current selection (rect / lasso / brush) to the zone selected on the left.|Select by shape instead of colour.|zone,paint|-|vtModeLasso
onboardingImportPsdBtn|Import PSD: load a Photoshop template to get editable layers.|Get layers.|none|-|pro.header.psd_xcf_ora
pro.center.load_tga|Load TGA: load a flat paint picture (no layers).|-|none|-|paintFile
pro.center.blank_canvas|Blank Canvas: start from plain white to design from scratch.|No paint file yet.|none|-|paintFile
"""

ROWS_MISC = """
leftCollapseBtn|Collapse arrow (left column)|button|Pro > left column edge|Collapses or expands the ZONES column.|More room for the canvas.|none|-|rightCollapseBtn|
rightCollapseBtn|Collapse arrow (right column)|button|Pro > right column edge|Collapses or expands the FINISHES / LAYERS column.|More room for the canvas.|none|-|leftCollapseBtn|
zoneFloatExpandTab|Zone editor tab (E)|button|Pro > left of the canvas|Shows or hides the floating ZONE POPOUT PANEL (press E).|The zone controls vanished or are in the way.|zone|-|zone.section_base|
"""

CUR2 = """
spbUpdateBannerDownload|Downloads the new Shokker version.|The update banner shows.|none|Save your project first; installing restarts the app.|spbUpdateBannerSnooze
spbUpdateBannerSnooze|Hides the update banner for now.|You are mid-job.|none|-|spbUpdateBannerDownload
pro.header.browse_car_folder|Browse for the iRacing car folder in Windows.|You cannot find your car in the list.|none|Pick the car's own folder inside Documents/iRacing/paint, not a TGA file.|outputDir,carPickBtn
pro.toolbar.history|HISTORY menu: Undo, Redo, Undo History.|Take back changes.|paint|-|pro.toolbar.undo_ctrl_z
pro.toolbar.select|SELECT menu: Select All Color, Grab Object, Smart Region Fill, Move Selection Border, Pick Layer Element, Zone Pick, Elliptical Marquee.|Selecting areas or elements.|paint|-|vtModeSelectAll,vtModeGrabObject
pro.toolbar.retouch|RETOUCH menu: Color Brush, Recolor, Healing Brush, Smudge, Burn - pixel retouching on the selected layer.|Fix or paint artwork.|psd|Grey until a blank layer exists: use the Add blank for Color Brush button.|vtModeColorBrush
pro.toolbar.add_blank_for_color_brush|Adds a blank layer so the Color Brush has somewhere to paint.|Color Brush is greyed out.|psd|-|pro.toolbar.retouch
pro.toolbar.mask|MASK menu: Grow / Shrink / Fill Holes / Feather / Smooth / Invert / Copy / Mirror a zone's area, plus Include / Exclude Region.|Clean up where a zone applies.|zone|-|pro.toolbar.grow_1_px
pro.toolbar.spec_tools|SPEC TOOLS menu: Decal Rescue Kit, Lighting Mask, Material Sampler, Range Remapper.|Fixing the spec (shine) map.|paint|-|pro.toolbar.decal_rescue_kit
pro.toolbar.transform|TRANSFORM menu: Transform (Ctrl+T) and Fit Layer to Zone Selection.|Resize or rotate artwork.|psd|-|vtModeLayerTransform
pro.toolbar.adjust|ADJUST menu: Brightness/Contrast, Hue/Saturation, Color Replace, Invert, Grayscale, Gradient Map, Vibrance, Color Temperature.|Change the colours of the actual pixels.|paint|These edit the paint pixels; finishes and zone Hue Shift are render settings.|pro.toolbar.hue_saturation
pro.zones_more.rand_current_zone|Randomises the finish of the selected zone.|Ideas.|zone|Ctrl+Z undoes.|pro.zones_more.rand_all_zones
pro.zones_more.rand_all_zones|Randomises every zone.|Ideas.|paint|Overwrites your finishes (undoable).|smartRandomize
pro.zones_more.shokker_library|Opens the Shokker Library of saved looks.|Reuse a saved setup.|paint|-|pro.zones_more.load_shokk_file
pro.zones_more.undo_history|Opens the Undo History list.|Jump back several steps.|paint|-|pro.history.undo
pro.zones_more.save_as_template|Saves the current zone layout as a named template.|Reuse a layout on another paint.|zone|-|templateSelect
templateSelect|Dropdown of your saved zone templates; choosing one loads it.|Load a saved layout.|paint|-|pro.zones_more.save_as_template
pro.zones_more.load_shokk_file|Loads a saved .shokk session.|Reopen a saved setup.|paint|-|pro.zones_more.save_shokk
leftPanelPsExportFolder|Folder where PNG channel exports are written.|-|render|-|pro.zones_more.png_channels_export
pro.zones_more.browse_folder|Choose the export folder in Explorer.|-|render|-|leftPanelPsExportFolder
smartRandomize|Smart Randomize: picks good-looking combinations instead of pure chance.|-|paint|-|pro.zones_more.rand_all_zones
selectionMode|How a new selection combines with the existing one: Add (+), Replace, Subtract.|Wand or lasso adds when you wanted to replace.|paint|-|vtModeWand
brushShape|Shape of the brush tip: round, square, diamond, slash, noise.|-|paint|-|brushSize
patternBrushSelect|Paint with a texture instead of a solid colour.|-|psd|-|vtModeColorBrush
eraserMode|Eraser style: soft brush, hard block, or clear the whole layer / zone mask.|-|paint|-|vtModeErase
gradientType|Shape of the gradient tool: linear, reflected, radial, angular, diamond.|-|paint|-|gradientReverse
gradientReverse|Flips the gradient direction.|-|paint|-|gradientType
gradientFgToTransparent|Fade the foreground colour to transparent instead of to the background colour.|-|paint|-|gradientType
textFont|Font for text options.|-|psd|There is no Text button in the main tool row; add lettering as a PNG layer.|hdi.add_text
textBold|Bold text option.|-|psd|-|textFont
textItalic|Italic text option.|-|psd|-|textFont
textTransform|Text case: as typed, UPPERCASE, lowercase, Capitalize.|-|psd|-|textFont
textEffect|Text effect: drop shadow, outer glow, emboss and more.|-|psd|-|textFont
shapeType|Shape for the shape tool: rectangle, rounded rectangle, ellipse, triangle, polygon, star, line.|-|psd|-|shapeFilled
shapeFilled|Fill the shape with the fill colour.|-|psd|-|shapeType
shapeStrokeColor|Outline colour of a shape.|-|psd|-|shapeType
lineStartCap|Line start cap: flat, round, arrow.|-|psd|-|lineEndCap
lineEndCap|Line end cap: flat, round, arrow.|-|psd|-|lineStartCap
lineDashStyle|Line style: solid, dashed, dotted, dash-dot.|-|psd|-|lineEndCap
fgColorPicker|Foreground (paint) colour for brushes and fills; X swaps with background.|Choose the colour to paint with.|paint|-|fgHexInput
layerPaintSourceMode|Brush / Fill source on a layer: solid colour or a baked Special finish.|Paint with a finish instead of flat colour.|psd|-|layerSpecialPickerBtn
cloneAligned|Aligned clone: the source moves with the brush.|-|psd|-|cloneOpacity
healingAligned|Aligned healing source.|-|psd|-|pro.tool_options.set_source
wandContiguous|Contiguous: only select touching pixels of that colour (off = everywhere).|The wand grabs far-away bits or misses them.|paint|-|vtModeWand
wandSampleSize|Sample area for the wand: single point or an average of 3x3 / 5x5 / 11x11 pixels.|Wand is too fussy on noisy paint.|paint|-|wandTolerance
wandAntiAlias|Smooths the wand selection edge.|-|paint|-|vtModeWand
deployCarSelect|Pick another iRacing car to also copy this render to.|Same paint on a second car.|render|-|pro.render.deploy_now
pro.render.deploy_now|Copies this render to the chosen car's iRacing folder.|-|render|-|deployCarSelect
specMaterialSampleSize|Sample size for the Material Sampler: exact pixel or local median.|-|render|-|pro.toolbar.material_sampler
btnCopySpecSample|Copies the M / R / CC / A values you sampled.|-|render|-|pro.toolbar.material_sampler
btnSelectConnectedMaterial|Selects the connected area with the same material values.|-|render|-|pro.toolbar.material_sampler
btnSelectAllMaterial|Selects every pixel with similar material values.|-|render|-|pro.toolbar.material_sampler
btnApplySpecSample|Gives the active zone the sampled material values.|-|zone,render|-|pro.toolbar.material_sampler
pro.spec_tools.clear_zone_override|Removes the sampled override from the zone.|-|zone|-|btnApplySpecSample
pro.spec_tools.decal_flat_vinyl|Flat vinyl spec under numbers / sponsors: neutralises chrome or candy beneath.|Decals sparkle or vanish under metal.|paint|-|pro.toolbar.decal_rescue_kit
pro.spec_tools.decal_satin|Satin decal spec: keeps printed vinyl readable.|-|paint|-|pro.toolbar.decal_rescue_kit
pro.spec_tools.decal_gloss|Gloss decal spec: clean printed gloss.|-|paint|-|pro.toolbar.decal_rescue_kit
pro.spec_tools.lighting_use_source|Lighting mask: use the source file's alpha, removing Shokker's override.|-|paint|-|pro.toolbar.lighting_mask
pro.spec_tools.lighting_full|Lighting mask: force normal lighting.|-|paint|-|pro.toolbar.lighting_mask
pro.spec_tools.lighting_reduced|Lighting mask: half-strength lighting response.|-|paint|-|pro.toolbar.lighting_mask
pro.spec_tools.lighting_kill|Lighting mask: suppress spec and environment (fake a hole or dead-dark vent).|-|paint|-|pro.toolbar.lighting_mask
pro.spec_tools.remap_original|Range Remapper preset: original values.|-|zone|-|pro.toolbar.range_remapper
pro.spec_tools.remap_metallic|Range Remapper preset: metallic texture.|-|zone|-|pro.toolbar.range_remapper
pro.spec_tools.remap_vinyl|Range Remapper preset: printed vinyl.|-|zone|-|pro.toolbar.range_remapper
pro.spec_tools.remap_matte|Range Remapper preset: matte texture.|-|zone|-|pro.toolbar.range_remapper
pro.spec_tools.remap_gloss|Range Remapper preset: gloss texture.|-|zone|-|pro.toolbar.range_remapper
specRemapMLow|Metallic range low end (0-255).|-|zone|-|specRemapMHigh
specRemapMHigh|Metallic range high end.|-|zone|-|specRemapMLow
specRemapRLow|Roughness range low end.|-|zone|-|specRemapRHigh
specRemapRHigh|Roughness range high end.|-|zone|-|specRemapRLow
specRemapCCLow|Clearcoat range low end.|-|zone|-|specRemapCCHigh
specRemapCCHigh|Clearcoat range high end.|-|zone|-|specRemapCCLow
pro.spec_tools.remap_restore|Puts the zone's original spec ranges back.|-|zone|-|pro.toolbar.range_remapper
pro.spec_tools.remap_apply|Applies the remapped ranges to the active zone.|-|zone|-|pro.toolbar.range_remapper
pro.finish_picker.clear_search|Clears the search so the whole list shows again.|No results.|zone|-|swatchSearchInput
swatchPreviewOnPaintBtn|Applies the preview of the selected finish on your paint.|-|paint|-|swatchSeeOnPaintBtn
pro.shokk_library.close_shokk_library|Closes the SHOKK library.|-|none|-|pro.zones_more.save_shokk
shokkSaveName|Name for the .shokk file.|-|paint|-|pro.zones_more.save_shokk
shokkSaveAuthor|Your name (optional) stored in the file.|-|paint|-|pro.zones_more.save_shokk
shokkSaveDesc|Short description of the recipe.|-|paint|-|pro.zones_more.save_shokk
psExportCarFileName|Name for the exported car file in the Photoshop round trip.|-|psd|-|btnDoExportToPs
psExportExchangeFolder|Folder shared with Photoshop for the round trip.|-|psd|-|btnDoExportToPs
btnDoExportToPs|Exports layers to the exchange folder for Photoshop editing; bring the TGA back afterwards.|You prefer editing in Photoshop.|psd|-|layerActionsMenuBtn
pro.layers.clear_all|Clears all layer effects (Layer Effects dialog).|-|psd|-|pro.layers.apply
pro.layers.apply|Applies the layer effects.|-|psd|-|pro.layers.clear_all
"""
CUR = CUR + CUR2.replace('hdi.add_text', 'pro.layers.layer')

ROWS_ZONE = ROWS_ZONE + """
zone.color_scale_rotation|Color Scale / Color Rotation|slider|{ZE} > BASE (only with From special or Custom gradient)|Zooms and rotates the colour art (gradient or borrowed special colours) without touching the material texture.|The gradient or borrowed colours are too big, small or at the wrong angle.|zone|Solid colours have nothing to scale; these only appear for From special / Custom gradient.|zone.gradient,zone.base_color_mode|zone_base_colour_scale_rotation
zone.intensity|Intensity (zone strength, legacy preset buttons)|slider|{ZE} > zone header (if shown on your build)|Overall strength of the zone's effect: lower = closer to the original paint and a calmer spec.|Finish is too loud overall.|zone|Not seen in the live panel of build 10.0.3 (listed in app_controls.json); prefer Base Strength / Spec Strength.|zone.base_strength,zone.spec_strength|zone_intensity
zone.wear|Wear / weathering|slider|{ZE} > wear slider (if shown on your build)|Scuffs and ages the finish (chips, dulling).|A worn / used look.|zone|Not seen in the live panel of build 10.0.3; check for a Wear control or ask Chat for a weathered finish.|zone.base_strength|zone_wear
"""


# ---------------------------------------------------------------- how_do_i index + app_map.md
HDI_SRC = REPO / 'docs' / 'ai_knowledge' / 'how_do_i.md'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import enc_hidden as EH   # the ONE list of hidden features: scripts/ai_atlas/enc_hidden_features.json
APP_MAP_DST = REPO / 'docs' / 'ai_knowledge' / 'app_map.md'


def _how_do_i(valid_ids):
    txt = EH.scrub_md(HDI_SRC.read_text(encoding='utf-8').replace('\r\n', '\n'))   # owner rule 2026-10-04: hidden features never reach the map
    out, bad = [], []
    for blk in re.split(r'\n(?=## )', txt):
        if not blk.startswith('## '):
            continue
        head, _, body = blk.partition('\n')
        m = re.match(r'\[(hdi\.[\w]+)\s*\|\s*([^|]*)\|\s*needs:\s*([^|]*)\|\s*ui:\s*([^\]]*)\]', body.strip())
        if not m:
            bad.append(head)
            continue
        steps = re.findall(r'^\d+\.\s+(.*)$', body, flags=re.M)
        ui = [x.strip() for x in m.group(4).split(',') if x.strip()]
        out.append(dict(id=m.group(1), title=head[3:].strip(), mode=m.group(2).strip(), needs=_needs(m.group(3).strip().replace(' ', '')),
                        ui=ui, steps=steps))
    dangling = sorted({(h['id'], u) for h in out for u in h['ui'] if u not in valid_ids})
    return out, bad, dangling


def _write_app_map(items, panel_nodes):
    L = ['# Where everything is: the app map (AI knowledge card, generated from scripts/ai_atlas/ui_map.json)', '',
         'Use these names exactly. Modes: PRO (full shop), CHAT (talk to Shokker). The Pro zone editor is the ZONE POPOUT PANEL that opens when a zone card is clicked. '
         'There is no File menu: saving a project is the "Save / Open" button. Dropping a picture on the canvas replaces the paint; "+ Layer" adds a logo.', '']
    skip_panels = {'pro.dialogs', 'pro.modes', 'misc'}
    for p in panel_nodes:
        if p['id'] in skip_panels and p['id'] != 'pro.modes':
            continue
        its = [i for i in items if i['panel'] == p['id'] and not i['id'].startswith('mode.') and not i.get('retired')]
        cur = [i for i in its if i['curated']]
        auto = [i for i in its if not i['curated'] and (i['help_text'] or '').strip() and not i['id'].startswith('pro.finish_picker.')
                and i['kind'] not in ('section', 'panel')]
        title = '%s: %s' % (p['mode'].title() if p['mode'] != 'any' else 'Any mode', p['label'])
        head = '%s Where: %s.' % (p['does'], p['where'])
        lines = []
        for i in cur + auto:
            d = (i['does'] or '').strip()
            if len(d) > 170:
                d = d[:167].rsplit(' ', 1)[0] + '...'
            extra = ''
            if i.get('mistakes') and i['curated']:
                mm = i['mistakes']
                extra = ' Watch out: ' + (mm if len(mm) < 110 else mm[:107].rsplit(' ', 1)[0] + '...')
            lines.append('- **%s** (%s): %s%s' % (i['label'], i['kind'], d, extra))
        # split into chunks of <= 1400 chars so build_ai_knowledge keeps each whole
        part, n, buf = 1, 0, [head]
        size = len(head)
        chunks = []
        for ln in lines:
            if size + len(ln) > 1380 and len(buf) > 1:
                chunks.append(buf)
                buf, size = [], 0
            buf.append(ln)
            size += len(ln) + 1
        if buf:
            chunks.append(buf)
        for ci, c in enumerate(chunks):
            L.append('## %s%s' % (title, '' if len(chunks) == 1 else ' (%d of %d)' % (ci + 1, len(chunks))))
            L.extend(c)
            L.append('')
    ret = [i for i in items if i.get('retired')]
    if ret:
        # RETIRED controls (2026-10-05): a buyer must never be sent to a button that cannot be reached. One honest chunk instead of live bullets.
        modes = sorted({i['retired_mode'] for i in ret})
        L.append('## Retired controls (not in this build)')
        L.append('%s %s retired in this booth build: the panel stays hidden, nothing opens it, and the buttons only show a "disabled" message. '
                 'Do not send a buyer to them. Render one car at a time with the normal RENDER button.' % (' and '.join(m[:1].upper() + m[1:] for m in modes), 'is' if len(modes) == 1 else 'are'))
        L.append('- **%s** (retired buttons): they cannot be clicked. For a worn look pick a worn Base Material and lower Base Strength (see the Wear article).'
                 % ', '.join(sorted({re.sub(r'^[+\s]+', '', i['label']) for i in ret})))
        L.append('')
    APP_MAP_DST.write_text('\n'.join(L), encoding='utf-8', newline='\n')
    return sum(1 for x in L if x.startswith('## '))


# ---------------------------------------------------------------- assemble ui_map.json
_SKIP_LABELS = {'x', '×', 'cancel', 'close', 'esc'}


def _split(tbl, n):
    rows = []
    for ln in tbl.strip().split('\n'):
        if not ln.strip():
            continue
        f = ln.split('|')
        if len(f) != n:
            raise SystemExit('bad row (%d fields, want %d): %s' % (len(f), n, ln[:110]))
        rows.append([x.strip() for x in f])
    return rows


def _nz(s):
    return '' if s in ('-', '') else s


def _csv(s):
    return [x for x in (s or '').split(',') if x]


def _needs(s):
    return [x for x in (s or '').replace('/', ',').split(',') if x and x != 'none'] or ['none']


def _mode_of(panel):
    if panel.startswith('easy'):
        return 'easy'
    if panel in ('pro.ai', 'chat'):
        return 'pro+chat'
    return 'pro'


LABEL_FIX = {
    'iracingId': 'IRACING USER ID box', 'useCustomNumberCheckbox': 'CUSTOM NUMBER', 'useSimStampedCheckbox': 'SIM-STAMPED NUMBER',
    'paintFile': 'SOURCE PAINT box', 'outputDir': 'IRACING CAR FOLDER box', 'licenseKeyInput': 'Licence key box',
    'finishSearch': 'Finish library search box', 'swatchSearchInput': 'Finish picker search box', 'fbSearch': 'Catalog search box',
    'layerSearchInput': 'Layers filter box', 'templateSelect': 'Load Template... dropdown', 'smartRandomize': 'Smart Randomize checkbox',
    'leftPanelPsExportFolder': 'Export folder box (PNG channels)', 'trainingWheelsCheckbox': 'Training Wheels checkbox',
    'exportZipCheckbox': 'ZIP export checkbox', 'liveLinkCheckbox': 'Auto-deploy (Live Link) checkbox',
    'selectionMode': 'Selection mode dropdown (Add / Replace / Subtract)', 'brushShape': 'Brush shape dropdown',
}
PANEL_WHERE = {'pro.header': 'Pro > top of the window, first rows (iRacing User ID, Source Paint, iRacing Car Folder)'}


def _camel_label(i):
    pre = ''
    for p, nice in (('fx', 'Layer Effects: '), ('specRemap', 'Range Remapper: '), ('btn', '')):
        if i.startswith(p):
            pre, i = nice, i[len(p):]
            break
    words = re.sub(r'([a-z])([A-Z])', lambda m: m.group(1) + ' ' + m.group(2), i).replace('Cc', 'Coat').strip()
    return pre + words[:1].upper() + words[1:]


def build_json():
    ctrl_meta = json.loads(CTRL_SRC.read_text(encoding='utf-8'))
    ctrl_ids = {c['id'] for c in ctrl_meta['controls']}
    items, by_id = [], {}

    def add(it):
        by_id[it['id']] = it
        items.append(it)

    cur = {}
    for k, does, when, needs, mist, rel in _split(CUR, 6):
        cur[k] = dict(does=_nz(does), when=_nz(when), needs=_needs(needs), mistakes=_nz(mist), related=_csv(rel))

    # 1. static DOM items from paint-booth-v2.html
    for it in _static_items():
        lab = it['label']
        if lab.lower() in _SKIP_LABELS and not it['dom_id']:
            continue
        if lab in ('+', '-', '1', '90', '180') and it['help_text']:
            lab = it['help_text'].split(' - ')[0].split(' — ')[0]
        lab = LABEL_FIX.get(it['id'], lab)
        if not lab:
            if it['id'].startswith('mode'):
                continue                      # hidden per-tool option wrappers, not controls
            lab = _camel_label(it['id'])
        h = it['help_text']
        base_does = re.sub(r'^[^—]{0,60}—\s*', '', h) if h else ''
        c = cur.get(it['id'], {})
        rec = dict(id=it['id'], label=lab, mode=_mode_of(it['panel']), panel=it['panel'], where=it['where'], kind=it['kind'],
                   does=c.get('does') or base_does or ('Control labelled "%s".' % lab), when=c.get('when', ''),
                   needs=c.get('needs', ['paint'] if it['panel'] not in ('pro.header', 'pro.settings', 'pro.modes') else ['none']),
                   mistakes=c.get('mistakes', ''), related=c.get('related', []), help_text=h, control_id='',
                   dom_id=it['dom_id'], source='html', curated=bool(c))
        if not c and it['id'].startswith('fx'):
            m = re.match(r'fx(DropShadow|OuterGlow|Stroke|ColorOverlay|Bevel)(\w+)', it['id'])
            if m:
                eff = re.sub(r'([a-z])([A-Z])', lambda x: x.group(1) + ' ' + x.group(2), m.group(1))
                prop = re.sub(r'([a-z])([A-Z])', lambda x: x.group(1) + ' ' + x.group(2), m.group(2))
                rec['does'] = ('Layer Effects: turns the %s effect on or off for the layer.' % eff) if prop == 'Enabled' else ('Layer Effects > %s: %s setting.' % (eff, prop.lower()))
                rec['when'] = 'Add a shadow, glow, outline, tint or bevel to a logo / number layer without editing its pixels.'
                rec['needs'] = ['psd']
                rec['where'] = 'Pro > LAYERS tab > double-click a layer > Layer Effects dialog'
                rec['related'] = ['pro.layers.apply']
        add(rec)
    missing_cur = [k for k in cur if k not in by_id]

    # 2. rows built by JavaScript at run time (zone editor, layers, easy, ai)
    def rows(tbl, panel_of, source):
        for r in _split(tbl.replace('{ZE}', ZE), 10):
            key, lab, kind, where, does, when, needs, mist, rel, ctl = r
            panel = panel_of(key)
            if ctl and ctl not in ctrl_ids:
                missing_ctl.append((key, ctl))
                ctl = ''
            add(dict(id=key, label=lab, mode=_mode_of(panel), panel=panel, where=where, kind=kind, does=_nz(does),
                     when=_nz(when), needs=_needs(needs), mistakes=_nz(mist), related=_csv(rel), help_text='',
                     control_id=ctl, dom_id='', source=source, curated=True))
    missing_ctl = []
    rows(ROWS_ZONE, lambda k: 'pro.zone_editor' if k.startswith('zone.') else 'pro.zones', 'js:renderZoneDetail')
    rows(ROWS_LAYERS, lambda k: 'pro.layers', 'js:renderLayerPanel')
    rows(ROWS_EASY, lambda k: 'easy.part_panel' if k.split('.')[1] in (
        'part_back', 'color_reach', 'merge_with', 'finish_picker', 'adjust', 'color_choice', 'put_it_on') else 'easy', 'js:spb-easy-*.js')
    rows(ROWS_MISC, lambda k: 'pro.right' if k == 'rightCollapseBtn' else 'pro.zones', 'html:div')
    rows(ROWS_AI, lambda k: 'pro.ai', 'js:spb-pro-ai.js')

    # 3. modes + panels as map nodes
    for m in MODES:
        m = dict(m)
        m.update(panel='pro.modes', mode=m['id'].split('.')[1], needs=_needs(m['needs']), related=_csv(m['related']), control_id='',
                 dom_id={'pro': 'spbModeProBtn', 'chat': 'spbModeChatBtn', 'easy': 'spbModeEasyBtn'}[m['id'].split('.')[1]],
                 source='html', curated=True)
        add(m)
    panel_nodes = []
    for pid, mode, label, does, needs in PANELS:
        where = [PANEL_WHERE[pid]] if pid in PANEL_WHERE else [v[1] for k, v in PANEL_MAP.items() if v[0] == pid][:1]
        panel_nodes.append(dict(id=pid, label=label, mode=mode.lower(), kind='panel', where=where[0] if where else mode + ' > ' + label,
                                does=does, needs=_needs(needs), items=[i['id'] for i in items if i.get('panel') == pid]))

    # 3b. RETIRED controls (2026-10-05). Evidence comes from the code, not from a list kept here: enc_stale_refs_check.retired_code_evidence() finds
    # the functions that only show _showRetiredBatchModeToast(...) (toggleFleetMode / doFleetRender / toggleSeasonMode / doSeasonRender) and the hidden
    # panel in paint-booth-v2.html that they close. Every control inside that panel is marked retired here, so app_map.md, the self-help UI_DATA and
    # the AI knowledge cards stop listing Add Car / Render All Cars / Add Race / Quick: Wear Ramp / Render All Races as live buttons.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from enc_stale_refs_check import retired_code_evidence
    RC = retired_code_evidence()
    for it in items:
        word = RC['by_dom'].get(it.get('dom_id')) or RC['by_dom'].get(it['id']) or RC['by_label'].get(re.sub(r'^[+\s]+', '', it['label']).strip())
        if not word:
            continue
        mode = next((m for m in RC['modes'] if m.lower().startswith(word)), word + ' mode')
        it['retired'] = True
        it['retired_mode'] = mode
        it['where'] = 'Retired: the %s panel is hidden and nothing opens it' % word
        it['does'] = ('Retired: %s is disabled in this booth build, so this control cannot be reached. Use the normal single-car paint workflow instead.' % mode
                      + (' For a worn look pick a worn Base Material and lower Base Strength.' if word == 'season' else ''))
        it['when'] = ''
        it['mistakes'] = 'Retired: it cannot be clicked in this build.'
        it['related'] = []
        it['needs'] = ['none']
    # 3c. HIDDEN FEATURES (owner rule 2026-10-04): the hidden feature's items / panels / mode are dropped from every output, and its names are
    # scrubbed out of the text of the rest (list: scripts/ai_atlas/enc_hidden_features.json; un-hide = remove it there and re-run this script).
    if EH._ON:
        hid = {i['id'] for i in items if EH.is_hidden_item(i)}
        items = [i for i in items if i['id'] not in hid]
        by_id = {k: v for k, v in by_id.items() if k not in hid}
        panel_nodes = [p for p in panel_nodes if not EH.is_hidden_item(p)]
        for i in items:
            for k in ('label', 'where', 'does', 'when', 'mistakes', 'help_text'):
                i[k] = EH.scrub(i.get(k) or '', True)
            i['related'] = [r for r in i.get('related', []) if not EH.is_hidden_id(r) and r not in hid]
        for p in panel_nodes:
            for k in ('label', 'where', 'does'):
                p[k] = EH.scrub(p.get(k) or '', True)
            p['items'] = [x for x in p.get('items', []) if x not in hid]
    # 4. integrity: related ids that point nowhere
    all_ids = set(by_id) | {p['id'] for p in panel_nodes}
    dangling = sorted({(i['id'], r) for i in items for r in i['related'] if r not in all_ids})
    by_kind, by_mode, by_panel = {}, {}, {}
    for i in items:
        by_kind[i['kind']] = by_kind.get(i['kind'], 0) + 1
        by_mode[i['mode']] = by_mode.get(i['mode'], 0) + 1
        by_panel[i['panel']] = by_panel.get(i['panel'], 0) + 1
    out = dict(
        meta=dict(version=1, built='2026-10-03', work_package='SELF-MAP',
                  purpose='Complete map of the Shokker Paint Booth UI for the helper (offline brain, Chat copilot, MCP clients) to reason with.',
                  schema=dict(id='stable key (DOM id, or <panel>.<slug>, or zone.* / layer.* / ai.* for JS-built controls)',
                              label='what the UI shows', mode='pro | chat | pro+chat', panel='key into panels[]', where='how to get there',
                              kind='button|slider|dropdown|toggle|picker|text input|number input|search box|menu|tab|section|panel|mode|input|link',
                              does='one buyer-words sentence', when='when a buyer wants it', needs='list: paint|psd|zone|parts|render|car_folder|none',
                              mistakes='what people get wrong', related='ids', help_text='tooltip already in the HTML', control_id='id in scripts/ai_atlas/app_controls.json',
                              curated='false = auto-generated from the HTML tooltip only', source='html | js:<where the control is built>'),
                  counts=dict(items=len(items), curated=sum(1 for i in items if i['curated']), panels=len(panel_nodes), by_kind=by_kind, by_mode=by_mode, by_panel=by_panel),
                  caveats=['Fleet and Season batch controls are RETIRED (items with retired=true): hidden panel, nothing opens it, the handlers only show a disabled toast.',
                           'Pro zone editor / layer rows / AI panel are built by JavaScript: read from the live DOM on 2026-10-03 (test server) and curated by hand.',
                           'There is NO sort/group-by-colour in the Layers panel (Smart Separate was withdrawn); colour work is done via zone colour picking.']),
        modes=[i for i in items if i['id'].startswith('mode.')],
        panels=panel_nodes, items=[i for i in items if not i['id'].startswith('mode.')],
        unmatched_curation_keys=missing_cur, unknown_control_ids=missing_ctl, dangling_related=[list(x) for x in dangling],
    )
    hdi, hdi_bad, hdi_dangling = _how_do_i(all_ids)
    out['how_do_i'] = hdi
    out['meta']['counts']['how_do_i'] = len(hdi)
    out['how_do_i_dangling_ui'] = [list(x) for x in hdi_dangling]
    n_app = _write_app_map(items, panel_nodes)
    JSON_DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    c = out['meta']['counts']
    print('wrote', JSON_DST.name, 'items', c['items'], 'curated', c['curated'], 'panels', c['panels'])
    print('by_kind', by_kind)
    print('by_mode', by_mode)
    if missing_cur: print('UNMATCHED CUR KEYS', missing_cur)
    if missing_ctl: print('UNKNOWN CONTROL IDS', missing_ctl)
    print('how_do_i entries', len(hdi), 'app_map chunks', n_app)
    if hdi_bad: print('HDI entries with bad tag line:', hdi_bad)
    if hdi_dangling: print('HDI ui ids not in map:', len(hdi_dangling), hdi_dangling[:40])
    if dangling: print('DANGLING related:', len(dangling), dangling[:25])


def main():
    if '--md' in sys.argv:
        return main_md()
    build_json()


if __name__ == '__main__':
    sys.exit(main())
