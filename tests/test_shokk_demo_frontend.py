from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "demo" / "frontend"
HTML = FRONTEND / "paint-booth-v2.html"
APP = FRONTEND / "js" / "app.js"
API = FRONTEND / "js" / "api.js"
CANVAS = FRONTEND / "js" / "canvas.js"
PREVIEW_INTERACTIONS = FRONTEND / "js" / "preview-interactions.js"
MANIFEST = ROOT / "demo" / "product-manifest.json"
ELECTRON_MAIN = ROOT / "electron-demo" / "src" / "main.js"


def test_frontend_is_dedicated_and_csp_safe() -> None:
    html = HTML.read_text(encoding="utf-8")
    assert "Content-Security-Policy" in html
    assert "paint-booth-0-finish-data.js" not in html
    assert "paint-booth-2-state-zones.js" not in html
    assert "shokker_engine_v2" not in html
    assert not re.search(r"\son(?:click|input|change|load|error)=", html, re.I)


def test_only_pick_and_exclude_tools_are_exposed() -> None:
    html = HTML.read_text(encoding="utf-8")
    assert len(re.findall(r'class="tool(?:\s|\")', html)) == 2
    assert 'id="pickTool"' in html
    assert 'id="excludeTool"' in html
    for forbidden in ("brushTool", "fillTool", "wandTool", "lassoTool", "rectTool", "eraseTool"):
        assert forbidden not in html


def test_demo_has_no_pattern_or_extra_base_controls() -> None:
    html = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    for forbidden in (
        "sectionPattern",
        "sectionSpecPatterns",
        "secondBaseStrength",
        "thirdBaseStrength",
        "fourthBaseStrength",
        "fifthBaseStrength",
    ):
        assert forbidden not in html
        assert forbidden not in app


def test_all_promised_zone_controls_are_present() -> None:
    app = APP.read_text(encoding="utf-8")
    expected = {
        "baseHueOffset", "baseSaturationAdjust", "baseBrightnessAdjust",
        "baseStrength", "baseSpecStrength", "baseScale", "baseRotation",
        "baseColorScale", "baseColorRotation", "baseColorDepth",
        "baseColorFlip", "baseColorUnderglow", "specScale", "specRotation",
        "specShiftR", "specShiftG", "specShiftB",
    }
    assert expected.issubset(set(re.findall(r"key: '([^']+)'", app)))
    assert "specBlendMode" in app
    assert "source_data_url" in app


def test_spec_strength_ui_and_payload_use_the_real_300_percent_range() -> None:
    app = APP.read_text(encoding="utf-8")
    definition = re.search(
        r"\{ key: 'baseSpecStrength'.*?max: MAX_SPEC_STRENGTH_PERCENT.*?reset: 100.*?\}",
        app,
    )
    assert definition
    assert "const MAX_SPEC_STRENGTH_PERCENT = 300;" in app
    assert "normalizeSpecStrengthPercent(zone.baseSpecStrength) / 100" in app
    assert "baseSpecStrength," in app
    assert "base_spec_strength: baseSpecStrength" in app


def test_source_picker_advertises_only_formats_the_demo_can_open() -> None:
    html = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    electron = ELECTRON_MAIN.read_text(encoding="utf-8")

    assert 'accept=".psd,.psb,.tga,.png,.jpg,.jpeg"' in html
    assert "['psd', 'psb'].includes(extension)" in app
    assert "extensions: ['psd', 'psb', 'tga', 'png', 'jpg', 'jpeg']" in electron
    for unsupported in (".xcf", ".ora"):
        assert unsupported not in html
    assert "'xcf'" not in electron
    assert "'ora'" not in electron


def test_five_zone_startup_and_remaining_gloss_contract() -> None:
    app = APP.read_text(encoding="utf-8")
    assert "function createDefaultZones()" in app
    defaults = app[app.index("function createDefaultZones()") : app.index("function activeZone()")]
    assert defaults.count("createZone(") == 5
    assert "name: 'Everything Else'" in defaults
    assert "finishId: 'gloss'" in defaults
    assert "coverageMode: 'remaining'" in defaults
    assert "baseColorMode: 'source'" in defaults
    assert "intensity: 80" not in defaults
    assert "intensity: 50" not in defaults
    assert "state.zones = createDefaultZones()" in app
    assert "shokk_demo_session_v2" in app


def test_zone_coverage_layer_and_independent_base_color_ui_contract() -> None:
    app = APP.read_text(encoding="utf-8")
    for required in (
        "WHAT PIXELS DOES THIS ZONE COVER?",
        "RESTRICT TO LAYERS",
        "data-zone-layer",
        "data-color-tolerance",
        "coverageMode",
        "source_layer_mask",
        "lockBaseColor",
        "Use finish's own color",
        "Use source paint (spec only)",
        "Use solid color",
        "From special",
        "Custom gradient",
        "gradient_stops",
        "gradient_direction",
    ):
        assert required in app
    assert "encodeSourceLayerScope" in app
    assert "source_layer_rgb_png" in app
    assert "source_layer_scopes" in app
    assert "source_layer_scope_id" in app
    assert "sourceLayerRgbPng:" not in app


def test_large_browser_image_caches_are_bounded_and_reset_per_source() -> None:
    app = APP.read_text(encoding="utf-8")
    canvas = CANVAS.read_text(encoding="utf-8")
    assert "const IMAGE_CACHE_LIMIT = 24" in canvas
    assert "while (imageCache.size > IMAGE_CACHE_LIMIT)" in canvas
    assert "export function clearImageCache()" in canvas
    assert "clearImageCache();" in app


def test_source_and_live_have_independent_zoom_controls_and_wheel_zoom() -> None:
    html = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    for kind in ("source", "live"):
        assert f'id="{kind}ZoomOut"' in html
        assert f'id="{kind}ZoomValue"' in html
        assert f'id="{kind}ZoomIn"' in html
        assert f'id="{kind}ZoomFit"' in html
        assert f"state.viewportZoom.{kind}" in app
    assert 'id="zoomValue"' not in html
    assert "viewportZoom: { source: 1, live: 1 }" in app
    assert "addEventListener('wheel'" in app
    assert "{ passive: false }" in app
    assert "wheelViewportZoom(state.viewportZoom[kind], event.deltaY)" in app
    assert "calculateViewportAnchor" in app
    assert "canvasPoint(event, displayCanvas, state.source.width, state.source.height)" in app


def test_viewport_zoom_math_is_bounded_and_cursor_centered() -> None:
    script = r"""
import { readFileSync } from 'node:fs';
const source = readFileSync(process.argv[1], 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const { clampViewportZoom, wheelViewportZoom, calculateViewportAnchor } = await import(moduleUrl);
const anchor = calculateViewportAnchor(
  { left: 100, top: 50, width: 400, height: 200 },
  { left: 50, top: 25, width: 800, height: 400 },
  300,
  150,
);
process.stdout.write(JSON.stringify({
  min: clampViewportZoom(-10),
  max: clampViewportZoom(100),
  wheelIn: wheelViewportZoom(1, -120),
  wheelOut: Number(wheelViewportZoom(1, 120).toFixed(6)),
  boundedIn: wheelViewportZoom(6, -120),
  boundedOut: wheelViewportZoom(.5, 120),
  anchor,
}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(PREVIEW_INTERACTIONS)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result == {
        "min": 0.5,
        "max": 6,
        "wheelIn": 1.2,
        "wheelOut": 0.833333,
        "boundedIn": 6,
        "boundedOut": 0.5,
        "anchor": {"localX": 200, "localY": 100, "imageX": 0.3125, "imageY": 0.3125},
    }


def test_material_channels_hover_live_and_click_fullscreen_contract() -> None:
    html = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    assert len(re.findall(r'class="map-card(?:\s[^\"]*)?"[^>]+data-map=', html)) == 4
    assert "card.addEventListener('mouseenter'" in app
    assert "card.addEventListener('mouseleave'" in app
    assert "setHoveredMap('')" in app
    assert "renderLiveViewport" in app
    assert "HOVER PREVIEW" in app
    assert "card.addEventListener('click', () => openChannelInspector" in app
    assert 'id="channelInspectDialog"' in html
    assert 'id="channelInspectTitle"' in html
    assert 'id="channelInspectCanvas"' in html
    assert 'id="closeChannelInspect"' in html
    assert "dialog.showModal()" in app
    assert "addEventListener('close'" in app
    assert "'cancel'" in app
    assert "['Escape', 'Esc', 'ESC'].includes(event.key)" in app
    assert ".channel-inspect-dialog" in css
    assert "width: calc(100vw - 24px)" in css


def test_finish_picker_preserves_two_up_paint_and_spec_thumbnail_ratio() -> None:
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    rule = css[css.index(".finish-card img, .finish-card canvas") :]
    rule = rule[: rule.index("}")]
    assert "aspect-ratio: 2 / 1" in rule
    assert "object-fit: contain" in rule


def test_color_lab_is_opt_in_for_new_and_restored_sessions() -> None:
    app = APP.read_text(encoding="utf-8")
    create_zone = app[app.index("function createZone("):app.index("function createDefaultZones(")]
    active = app[app.index("function colorLabActive("):app.index("function renderColorChips(")]
    restore = app[app.index("function restoreControls("):app.index("function renderZones(")]
    script = "const crypto = { randomUUID: () => 'zone' }; const manifestFinish = () => null; const normalizeSpecStrengthPercent = n => n; const isSingleFlatSource = () => false; const state = {zones:[], manifest:{baseColorSources:[]}}; const MAX_ZONES=64; const $=()=>({}); const normalizeGradientStops=z=>z.gradientStops;\n" + create_zone + active + restore + """
const legacy = createZone(0, {baseColorMode:'solid', baseColorDepth:65, baseColorFlip:180, intensity:50, baseColorStrength:50, baseStrength:75});
const opted = createZone(0, JSON.parse(JSON.stringify({...legacy, baseColorLabEnabled:true})));
const off = createZone(0, JSON.parse(JSON.stringify({...opted, baseColorLabEnabled:false})));
restoreControls({zones:[{...legacy, intensity:50, baseColorStrength:50}]});
console.log(JSON.stringify([colorLabActive(legacy), colorLabActive(opted), colorLabActive(off), colorLabActive({...opted, baseColorMode:'finish'}), legacy.intensity, legacy.baseColorStrength, legacy.baseStrength, state.zones[0].intensity, state.zones[0].baseColorStrength]));
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == [False, True, False, False, 100, 100, 75, 100, 100]
    assert 'id="baseColorLabEnabled"' in app
    assert "<fieldset class=\"color-lab-controls\"${colorLabActive(zone) ? '' : ' disabled'}" in app
    assert "base_color_depth: colorLabActive(zone) ? Number(zone.baseColorDepth) / 100 : null" in app


def test_material_and_color_source_pickers_are_separate() -> None:
    app = APP.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")
    assert "state.manifest.finishes.length !== 29" in app
    assert "state.manifest.baseColorSources.length !== 30" in app
    assert "finishPickerMode === 'special'" in app
    assert "zone.baseColorSource = finish.id" in app
    assert "zone.finishId = finish.id" in app
    assert "base_color_sources" in api
    fracture_handler = app[app.index("$('#fractureButton').addEventListener") :]
    assert "chooseFinish(fracture, { useFinishColor: true });" in fracture_handler[:1000]
    assert "forceFinishColor: true" not in fracture_handler[:800]


def test_finish_images_are_versioned_so_rebuilt_thumbnails_cannot_go_stale() -> None:
    app = APP.read_text(encoding="utf-8")
    assert "function versionedAssetUrl(url)" in app
    assert "state.manifest.version || 'demo'" in app
    assert app.count("image.src = versionedAssetUrl(url);") == 2


def test_source_layer_union_rle_uses_visible_selected_layers() -> None:
    script = r"""
import { readFileSync } from 'node:fs';
const source = readFileSync(process.argv[1], 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const { encodeSourceLayerUnion } = await import(moduleUrl);
const unionData = new Uint8ClampedArray(4 * 4);
globalThis.document = {
  createElement: () => {
    const canvas = { width: 0, height: 0 };
    const ctx = {
      globalAlpha: 1,
      globalCompositeOperation: 'source-over',
      save() {}, restore() {},
      drawImage(surface) {
        surface.alpha.forEach((value, index) => {
          if (value) unionData[index * 4 + 3] = Math.max(unionData[index * 4 + 3], value * this.globalAlpha);
        });
      },
      getImageData: () => ({ data: unionData }),
    };
    canvas.getContext = () => ctx;
    return canvas;
  },
};
const surface = (alpha) => ({
  getContext: () => ({
    getImageData: () => ({ data: Uint8ClampedArray.from(alpha.flatMap((value) => [0, 0, 0, value])) }),
  }),
});
const surfaceA = surface([255, 0, 0, 0]);
const surfaceB = surface([0, 255, 0, 0]);
const hidden = surface([0, 0, 255, 0]);
const mask = await encodeSourceLayerUnion([
  { id: 'a', visible: true, opacity: 1, rasterUrl: 'a', _surface: surfaceA },
  { id: 'b', visible: true, opacity: 1, rasterUrl: 'b', _surface: surfaceB },
  { id: 'hidden', visible: false, opacity: 1, rasterUrl: 'h', _surface: hidden },
], ['a', 'b', 'hidden'], 4, 1);
process.stdout.write(JSON.stringify(mask));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(CANVAS)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    mask = json.loads(completed.stdout)
    assert mask == {"width": 4, "height": 1, "runs": [[255, 2], [0, 2]]}


def test_lower_restricted_layer_does_not_repaint_visible_art_above_it() -> None:
    script = r"""
import { readFileSync } from 'node:fs';
const source = readFileSync(process.argv[1], 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const { encodeSourceLayerUnion } = await import(moduleUrl);
const surface = (alpha) => ({
  getContext: () => ({
    getImageData: () => ({ data: Uint8ClampedArray.from(alpha.flatMap((value) => [0, 0, 0, value])) }),
  }),
});
const mask = await encodeSourceLayerUnion([
  { id: 'logo', name: 'Logo', visible: true, opacity: 1, rasterUrl: 'logo', _surface: surface([0,255,0,0]) },
  { id: 'base', name: 'BASE01', visible: true, opacity: 1, rasterUrl: 'base', _surface: surface([255,255,255,255]) },
], ['base'], 4, 1);
process.stdout.write(JSON.stringify(mask));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(CANVAS)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    mask = json.loads(completed.stdout)
    assert mask == {"width": 4, "height": 1, "runs": [[255, 1], [0, 1], [255, 2]]}


def test_restricted_layer_rgb_comes_from_the_layer_that_owns_the_mask_pixel() -> None:
    script = r"""
import { readFileSync } from 'node:fs';
const source = readFileSync(process.argv[1], 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const { encodeSourceLayerScope } = await import(moduleUrl);
let written = null;
globalThis.document = {
  createElement: () => {
    const context = {
      createImageData: (width, height) => ({ data: new Uint8ClampedArray(width * height * 4) }),
      putImageData: (imageData) => { written = [...imageData.data]; },
    };
    return { width: 0, height: 0, getContext: () => context, toDataURL: () => 'data:image/png;base64,AA==' };
  },
};
const surface = (rgba) => ({
  getContext: () => ({ getImageData: () => ({ data: Uint8ClampedArray.from(rgba) }) }),
});
const scope = await encodeSourceLayerScope([
  { id: 'blue', name: 'Blue', visible: true, opacity: .4, rasterUrl: 'blue', _surface: surface([0,0,255,255]) },
  { id: 'red', name: 'Red', visible: true, opacity: 1, rasterUrl: 'red', _surface: surface([255,0,0,255]) },
], ['blue', 'red'], 1, 1);
process.stdout.write(JSON.stringify({ mask: scope.mask, rgba: written }));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(CANVAS)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    scope = json.loads(completed.stdout)
    assert scope["mask"] == {"width": 1, "height": 1, "runs": [[255, 1]]}
    assert scope["rgba"] == [255, 0, 0, 255]


def test_catalog_and_hidden_fracture_contract() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    visible = [item["id"] for item in manifest["finishes"] if item.get("visible")]
    hidden = [item["id"] for item in manifest["finishes"] if not item.get("visible")]
    assert len(visible) == 29
    assert len(set(visible)) == 29
    assert hidden == ["fs_core_emerald"]
    assert manifest["capabilities"]["tools"] == ["pick", "exclude"]
    assert manifest["capabilities"]["patterns"] is False
    assert manifest["capabilities"]["spec_patterns"] is False
    assert manifest["capabilities"]["extra_base_overlays"] == 0


def test_external_links_match_electron_allowlist() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    api = API.read_text(encoding="utf-8")
    assert manifest["branding"]["payhip_url"] == "https://payhip.com/b/AHgpV"
    assert manifest["branding"]["discord_url"] == "https://discord.gg/GwXxyhwtDu"
    assert "https://payhip.com/b/AHgpV" in api
    assert "https://discord.gg/GwXxyhwtDu" in api


def test_javascript_parses() -> None:
    for script in (APP, API, CANVAS, PREVIEW_INTERACTIONS):
        subprocess.run(["node", "--check", str(script)], cwd=ROOT, check=True, capture_output=True, text=True)


def test_psd_layer_stack_is_top_first_and_composites_from_base_up() -> None:
    script = r"""
import { readFileSync } from 'node:fs';
const source = readFileSync(process.argv[1], 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const { flattenLayerTree, layersInCompositeOrder, hitTestLayers } = await import(moduleUrl);
const rawPsdOrder = [
  {
    name: 'Paintable Area',
    is_group: true,
    children: [
      { layer_key: '0.0', name: 'Base Paint' },
      { layer_key: '0.1', name: 'Logos' },
      { layer_key: '0.2', name: 'Numbers' },
    ],
  },
  {
    name: 'Export Guides',
    is_group: true,
    children: [
      { layer_key: '1.0', name: 'Mask' },
      { layer_key: '1.1', name: 'Wire' },
    ],
  },
];
const panel = flattenLayerTree(rawPsdOrder);
const composite = layersInCompositeOrder(panel);
const opaqueSurface = {
  width: 1,
  height: 1,
  getContext: () => ({ getImageData: () => ({ data: [0, 0, 0, 255] }) }),
};
const top = { id: 'top', visible: true, _surface: opaqueSurface };
const bottom = { id: 'bottom', visible: true, _surface: opaqueSurface };
const pickedTop = hitTestLayers([top, bottom], 0, 0)?.id;
top.visible = false;
const pickedFallback = hitTestLayers([top, bottom], 0, 0)?.id;
process.stdout.write(JSON.stringify({
  panel: panel.map((layer) => layer.name),
  panelKeys: panel.map((layer) => layer.key),
  composite: composite.map((layer) => layer.name),
  pickedTop,
  pickedFallback,
}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(CANVAS)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    order = json.loads(completed.stdout)
    assert order["panel"] == ["Wire", "Mask", "Numbers", "Logos", "Base Paint"]
    assert order["panelKeys"] == ["1.1", "1.0", "0.2", "0.1", "0.0"]
    assert order["composite"] == ["Base Paint", "Logos", "Numbers", "Mask", "Wire"]
    assert order["pickedTop"] == "top"
    assert order["pickedFallback"] == "bottom"
