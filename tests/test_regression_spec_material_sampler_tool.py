"""SPB-93 Pass 31: point M/R/CC/A Material Sampler contract."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_pure_sampler_reads_exact_pixel_maps_display_coordinates_and_builds_patch():
    script = r"""
const api = require('./js/canvas/zone/spec-material-sampler.js');
const image = {width: 2, height: 2, data: new Uint8ClampedArray([
  1,2,3,4, 10,20,30,40,
  50,60,70,80, 90,100,110,120
])};
const sampled = api.sampleAt(image, 1, 0);
process.stdout.write(JSON.stringify({
  sampled,
  mapped: api.mapClientToPixel(75, 25, {left: 0, top: 0, width: 100, height: 100}, 2048, 2048),
  outside: api.mapClientToPixel(120, 20, {left: 0, top: 0, width: 100, height: 100}, 10, 10),
  patch: api.buildZonePatch(sampled),
  equal: api.samplesEqual(sampled, {m:10,r:20,cc:30,a:40}),
  text: api.sampleText(sampled)
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True
    )
    payload = json.loads(result.stdout)
    assert payload == {
        "sampled": {"x": 1, "y": 0, "m": 10, "r": 20, "cc": 30, "a": 40},
        "mapped": {"x": 1536, "y": 512},
        "outside": None,
        "patch": {"specMaterialOverride": {"m": 10, "r": 20, "cc": 30, "a": 40}, "specLightingMask": None},
        "equal": True,
        "text": "M 10 / R 20 / CC 30 / A 40",
    }


def test_inspector_exposes_crosshair_readout_copy_apply_and_clear_actions():
    html = read("paint-booth-v2.html")
    assert "Material Sampler…" in html
    assert 'id="specMapInspectorStage"' in html
    assert 'onclick="sampleSpecMaterialAtEvent(event)"' in html
    assert 'id="specMaterialSampleMarker"' in html
    assert 'id="btnApplySpecSample"' in html
    assert "intentionally replaces the Zone's generated M/R/CC/A structure" in html
    module = "js/canvas/zone/spec-material-sampler.js"
    assert html.index(module) < html.index('<script src="paint-booth-3-canvas.js')
    assert module in json.loads(read("scripts/runtime-sync-manifest.json"))["files"]
    css = read("paint-booth-v2.css")
    assert ".spec-material-sample-marker" in css
    assert "cursor: crosshair" in css


def test_inspector_data_is_exposed_and_stale_sample_resets_on_render():
    source = read("js/zones/preview-controls.js")
    assert "global.getSpecMapInspectorImageData" in source
    assert "global.resetSpecMaterialSampleDisplay" in source
    assert "Click any UV point to read or transfer its exact material values" in source


def test_sampler_owns_a_cached_visible_map_fallback_and_selection_reuses_it():
    sampler = read("js/canvas/zone/spec-material-sampler.js")
    selector = read("js/canvas/zone/spec-material-select.js")
    assert "function readInspectorImageData()" in sampler
    assert "context.drawImage(image, 0, 0, width, height)" in sampler
    assert "fallbackImageData && fallbackImageElement === image" in sampler
    assert "const imageData = readInspectorImageData();" in sampler
    assert "sampler.readInspectorImageData()" in selector


def test_zone_config_and_every_payload_builder_persist_sampled_material():
    config = read("js/zones/zone-config-zone-map-controls.js")
    assert config.count("specMaterialOverride: z.specMaterialOverride ?? null") == 2
    payload = read("paint-booth-5-api-render.js")
    assert "zoneObj.spec_material_override = values" in payload
    assert payload.count("_applySpecMaterialOverride(zoneObj, z);") == 4


def test_preview_adapter_sanitizes_sampled_material_channels():
    source = read("server.py")
    assert '_sampled_spec = z.get("spec_material_override")' in source
    assert 'for key in ("m", "r", "cc", "a")' in source


def test_zone_tool_never_writes_psd_layer_pixels():
    source = read("js/canvas/zone/spec-material-sampler.js")
    assert "Object.assign(zone, buildZonePatch(sample))" in source
    assert "pushZoneUndo('Apply sampled spec material')" in source
    assert "_psdLayers" not in source
    assert "putImageData" not in source


def test_actual_apply_replaces_conflicting_lighting_alpha_in_one_undo():
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const api=require('./js/canvas/zone/spec-material-sampler.js');
const source=fs.readFileSync('./js/canvas/zone/spec-material-sampler.js','utf8');
const start=source.indexOf('function applySampleToActiveZone()');
const end=source.indexOf('function clearActiveZoneOverride()',start);
const sample={m:0,r:29,cc:16,a:255},mask=new Uint8Array([0,255,128]);
const zone={specMaterialOverride:{...sample},specLightingMask:0,regionMask:mask};
const snapshots=[];
const c={...api,lastSample:sample,getActiveZone:()=>zone,showMessage:()=>{},kickLivePreview:()=>{},
 pushZoneUndo:()=>snapshots.push(JSON.parse(JSON.stringify(zone)))};
vm.createContext(c);vm.runInContext(source.slice(start,end),c);
assert.equal(c.applySampleToActiveZone(),true);
assert.equal(zone.specLightingMask,null);assert.deepEqual(zone.specMaterialOverride,sample);
assert.equal(zone.regionMask,mask);assert.equal(snapshots.length,1);assert.equal(snapshots[0].specLightingMask,0);
assert.equal(c.applySampleToActiveZone(),false);assert.equal(snapshots.length,1);
process.stdout.write('pass');
"""
    assert subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True) == 'pass'


def test_engine_sample_override_changes_all_four_channels_without_mutating_input():
    import shokker_engine_v2 as engine

    source = np.arange(4 * 5 * 4, dtype=np.uint8).reshape(4, 5, 4)
    sample = {"m": 200, "r": 80, "cc": 40, "a": 32}
    out = engine._apply_zone_spec_material_override(source, {"spec_material_override": sample})
    assert out is not source
    for channel, value in enumerate((200, 80, 40, 32)):
        assert np.all(out[:, :, channel] == value)
    assert not np.all(source[:, :, 0] == 200)
    assert engine._apply_zone_spec_material_override(source, {}) is source


def test_build_multi_zone_confines_flat_sample_and_lighting_mask_wins_alpha(tmp_path: Path):
    import shokker_engine_v2 as engine

    size = 64
    paint = np.full((size, size, 3), (200, 70, 30), dtype=np.uint8)
    paint_path = tmp_path / "paint.png"
    Image.fromarray(paint, mode="RGB").save(paint_path)
    region = np.zeros((size, size), dtype=np.float32)
    region[8:40, 16:48] = 1.0
    zone = {
        "name": "Material repair",
        "color": "everything",
        "intensity": "100",
        "base": "gloss",
        "base_color_mode": "source",
        "region_mask": region,
        "spec_material_override": {"m": 200, "r": 80, "cc": 40, "a": 32},
    }
    rendered_paint, sampled = engine.build_multi_zone(
        str(paint_path), str(tmp_path / "sampled"), [dict(zone)], seed=31, preview_mode=True
    )
    np.testing.assert_array_equal(rendered_paint[:, :, :3], paint)
    inside = sampled[8:40, 16:48]
    for channel, value in enumerate((200, 80, 40, 32)):
        assert np.all(inside[:, :, channel] == value)

    killed_zone = dict(zone)
    killed_zone["spec_lighting_mask"] = 0
    _, killed = engine.build_multi_zone(
        str(paint_path), str(tmp_path / "killed"), [killed_zone], seed=31, preview_mode=True
    )
    np.testing.assert_array_equal(killed[:, :, :3], sampled[:, :, :3])
    assert np.all(killed[8:40, 16:48, 3] == 0)
    outside = np.ones((size, size), dtype=bool)
    outside[8:40, 16:48] = False
    np.testing.assert_array_equal(killed[outside, 3], sampled[outside, 3])
