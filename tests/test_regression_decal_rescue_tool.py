import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "js/canvas/zone/decal-rescue.js"
MODULE = MODULE_PATH.read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
CSS = (ROOT / "paint-booth-v2.css").read_text(encoding="utf-8", errors="replace")
BASES = (ROOT / "engine/base_registry_data.py").read_text(encoding="utf-8", errors="replace")
STATE = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_decal_rescue_presets_are_flat_source_paint_zone_recipes():
    script = r"""
const m = require('./js/canvas/zone/decal-rescue.js');
const region = new Uint8Array([0,255,128,0]);
const spatial = new Uint8Array([1,2,0,0]);
const zone = {
  name:'Number footprint', regionMask:region, spatialMask:spatial,
  sourceLayer:'psd_4', base:'chrome', pattern:'carbon_fiber', finish:'candy',
  patternStack:[{pattern:'hex'}], specPatternStack:[{pattern:'scratch'}],
  thirdBase:'pearl', fourthBase:'chrome', fifthBase:'matte', wear:60,
  color:'red', colorMode:'quick', colors:['red'], customSpec:2
};
const beforeRegion = zone.regionMask;
const ok = m.applyPatchToZone(zone, 'satin_decal');
process.stdout.write(JSON.stringify({
  presets:m.PRESETS,
  ok,
  count:m.countSelected(region),
  sameRegion:zone.regionMask===beforeRegion,
  region:Array.from(zone.regionMask),
  sourceLayer:zone.sourceLayer,
  zone:{
    base:zone.base, baseColorMode:zone.baseColorMode,
    baseSpecStrength:zone.baseSpecStrength, baseStrength:zone.baseStrength,
    pattern:zone.pattern, finish:zone.finish, intensity:zone.intensity,
    patternStack:zone.patternStack, specPatternStack:zone.specPatternStack,
    thirdBase:zone.thirdBase, fourthBase:zone.fourthBase, fifthBase:zone.fifthBase,
    spatialMask:zone.spatialMask, color:zone.color, colorMode:zone.colorMode,
    useRegion:zone.useRegion, wear:zone.wear
  }
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["count"] == 2
    assert data["sameRegion"] is True
    assert data["region"] == [0, 255, 128, 0]
    assert data["sourceLayer"] is None
    assert {
        key: (value["base"], value["metallic"], value["roughness"], value["clearcoat"])
        for key, value in data["presets"].items()
    } == {
        "flat_vinyl": ("f_vinyl_wrap", 0, 100, 110),
        "satin_decal": ("f_clear_satin", 0, 100, 75),
        "gloss_decal": ("f_soft_gloss", 0, 42, 22),
    }
    assert data["zone"] == {
        "base": "f_clear_satin",
        "baseColorMode": "source",
        "baseSpecStrength": 1,
        "baseStrength": 1,
        "pattern": "none",
        "finish": None,
        "intensity": "100",
        "patternStack": [],
        "specPatternStack": [],
        "thirdBase": None,
        "fourthBase": None,
        "fifthBase": None,
        "spatialMask": None,
        "color": None,
        "colorMode": "none",
        "useRegion": True,
        "wear": 0,
    }


def test_decal_rescue_uses_engine_verified_foundation_channel_values():
    expected = {
        "f_vinyl_wrap": (0, 100, 110),
        "f_clear_satin": (0, 100, 75),
        "f_soft_gloss": (0, 42, 22),
    }
    for base_id, values in expected.items():
        match = re.search(
            rf'"{base_id}"\s*:\s*\{{[^\n]*"M"\s*:\s*(\d+),\s*"R"\s*:\s*(\d+),\s*"CC"\s*:\s*(\d+)',
            BASES,
        )
        assert match, f"missing flat Foundation base {base_id}"
        assert tuple(map(int, match.groups())) == values


def test_decal_rescue_is_zone_only_one_config_undo_and_one_preview():
    apply_start = MODULE.index("function applyActiveZone")
    apply_source = MODULE[apply_start:MODULE.index("if (root && typeof document", apply_start)]
    assert apply_source.index("pushZoneUndo") < apply_source.index("applyPatchToZone")
    assert apply_source.count("pushZoneUndo(") == 1
    assert apply_source.count("kickLivePreview()") == 1
    assert "zone.regionMask" in MODULE
    assert "selectedZoneIndex" in MODULE
    assert "selectedLayer" not in MODULE
    assert "_psdLayers" not in MODULE
    assert "putImageData" not in MODULE
    assert "canvasMode" not in MODULE


def test_decal_rescue_ui_is_discoverable_truthful_and_packaged():
    module_tag = "js/canvas/zone/decal-rescue.js?v=spb-rescue-flat-material-20260908"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "Decal Rescue Kit…" in HTML
    assert "Sim-stamped numbers and sponsors inherit the spec map underneath them" in HTML
    assert "One Undo restores the prior Zone recipe" in HTML
    assert "M</b> 0 <b>R</b> 100 <b>CC</b> 110" in HTML
    assert "decal-rescue-grid" in CSS
    assert "js/canvas/zone/decal-rescue.js" in MANIFEST["files"]
    for relative in (
        "paint-booth-v2.html",
        "paint-booth-v2.css",
        "paint-booth-2-state-zones.js",
        "js/canvas/zone/decal-rescue.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()


def test_zone_recipe_undo_redo_and_history_jump_refresh_compiled_preview():
    undo = STATE[STATE.index("function undoZoneChange"):STATE.index("function redoZoneChange")]
    redo = STATE[STATE.index("function redoZoneChange"):STATE.index("function jumpToUndoState")]
    jump = STATE[STATE.index("function jumpToUndoState"):STATE.index("function renderUndoHistoryPanel")]
    for source in (undo, redo, jump):
        assert source.index("renderZones()") < source.index("_requestZoneLivePreview()")
        assert source.count("_requestZoneLivePreview()") == 1
    assert "window.spbKickLivePreview" in STATE
    assert 'src="paint-booth-2-state-zones.js?v=' in HTML


def test_rescue_replaces_prior_material_mapping_and_uses_exact_advertised_channels():
    import numpy as np
    import shokker_engine_v2 as engine

    script = r"""
const api = require('./js/canvas/zone/decal-rescue.js');
const output = Object.keys(api.PRESETS).map(id => {
  const mask = new Uint8Array([0,255,128,0]);
  const zone = {regionMask:mask, specLightingMask:0,
    specMaterialRemap:{m:{low:20,high:100},r:{low:80,high:160},cc:{low:150,high:220}},
    specMaterialOverride:{m:255,r:2,cc:16,a:255}, specShiftR:80,specShiftG:-30,specShiftB:90,
    sourceLayer:'psd_1',sourceLayers:['psd_1','psd_2'],sourceLayerBindings:{psd_1:{label:'Number'}}};
  api.applyPatchToZone(zone,id);
  return {preset:api.PRESETS[id],zone,sameMask:zone.regionMask===mask};
});
process.stdout.write(JSON.stringify(output));
"""
    rows = json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True))
    texture = np.arange(4 * 5 * 4, dtype=np.uint8).reshape(4, 5, 4)
    for row in rows:
        z, preset = row["zone"], row["preset"]
        assert row["sameMask"] and z["useRegion"]
        assert z["specMaterialRemap"] is None
        assert z["sourceLayer"] is None and z["sourceLayers"] == [] and z["sourceLayerBindings"] == {}
        assert [z[k] for k in ("specShiftR", "specShiftG", "specShiftB")] == [0, 0, 0]
        payload = {"spec_material_override": z["specMaterialOverride"], "spec_lighting_mask": z["specLightingMask"]}
        actual = engine._apply_zone_spec_lighting_mask(engine._apply_zone_spec_material_override(texture, payload), payload)
        expected = [preset["metallic"], preset["roughness"], preset["clearcoat"], 0]
        np.testing.assert_array_equal(actual, np.broadcast_to(expected, texture.shape))
