"""SPB-93 Pass 34: texture-preserving Zone M/R/CC range remapper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return json.loads(result.stdout)


def test_pure_remap_math_preserves_alpha_and_channel_variation():
    payload = run_node(r"""
const api=require('./js/canvas/zone/spec-material-remap.js');
const remap={m:{low:100,high:200},r:{low:10,high:110},cc:{low:20,high:220}};
const source=new Uint8ClampedArray([0,128,255,7, 255,64,0,9]);
process.stdout.write(JSON.stringify({
  out:Array.from(api.remapRgba(source,remap)),
  source:Array.from(source),
  byte:api.remapByte(128,{low:20,high:220}),
  normalized:api.normalizeRemap(remap),
  identity:api.isIdentity(api.IDENTITY),
  invalid:api.normalizeRemap({m:{low:20,high:10},r:{low:0,high:255},cc:{low:0,high:255}})
}));
""")
    assert payload == {
        "out": [100, 60, 220, 7, 200, 35, 20, 9],
        "source": [0, 128, 255, 7, 255, 64, 0, 9],
        "byte": 120,
        "normalized": {
            "m": {"low": 100, "high": 200},
            "r": {"low": 10, "high": 110},
            "cc": {"low": 20, "high": 220},
        },
        "identity": True,
        "invalid": None,
    }


def test_masked_live_preview_reprojects_prior_range_and_leaves_unselected_pixels_exact():
    payload = run_node(r"""
const api=require('./js/canvas/zone/spec-material-remap.js');
const metallic={m:{low:205,high:255},r:{low:8,high:90},cc:{low:8,high:55}};
const source=new Uint8ClampedArray([205,90,55,13, 255,128,64,99]);
const mask=new Uint8ClampedArray([255,0]);
process.stdout.write(JSON.stringify({
  out:Array.from(api.remapRgbaMasked(source,metallic,api.IDENTITY,mask,2,1,2,1)),
  source:Array.from(source)
}));
""")
    assert payload == {
        "out": [0, 255, 255, 13, 255, 128, 64, 99],
        "source": [205, 90, 55, 13, 255, 128, 64, 99],
    }


def test_region_rle_reports_mask_dimensions_truthfully_after_source_size_change():
    payload = run_node(r"""
require('./js/zones/strength-map-controls.js');
globalThis.SPBZoneStrengthMapControls.install({});
const rle=globalThis.encodeRegionMaskRLE(new Uint8Array(16).fill(255),2,2);
process.stdout.write(JSON.stringify({
  width:rle.width,
  height:rle.height,
  covered:rle.runs.reduce((total,run)=>total+run[1],0),
  runs:rle.runs
}));
""")
    assert payload == {"width": 4, "height": 4, "covered": 16, "runs": [[255, 16]]}
    html = read("paint-booth-v2.html")
    assert "strength-map-controls.js?v=spb93-mask-rle-truth-20260809a" in html
    legacy = read("paint-booth-2-state-zones.js")
    encoder = legacy[legacy.index("function encodeRegionMaskRLE"):legacy.index("function decodeRegionMaskRLE")]
    assert "encodedWidth * encodedHeight !== mask.length" in encoder
    assert "width: encodedWidth, height: encodedHeight" in encoder


def test_full_2048_remap_stays_interactive():
    payload = run_node(r"""
const {performance}=require('perf_hooks');
const api=require('./js/canvas/zone/spec-material-remap.js');
const data=new Uint8ClampedArray(2048*2048*4);
for(let i=0;i<data.length;i+=4){data[i]=i%256;data[i+1]=(i/4)%256;data[i+2]=200;data[i+3]=77;}
const t=performance.now();
const out=api.remapRgba(data,{m:{low:180,high:255},r:{low:20,high:120},cc:{low:8,high:40}});
process.stdout.write(JSON.stringify({ms:performance.now()-t,alpha:out[3],length:out.length}));
""")
    assert payload["length"] == 2048 * 2048 * 4
    assert payload["alpha"] == 77
    assert payload["ms"] < 750


def test_ui_exposes_presets_ranges_truthful_precedence_and_module_order():
    html = read("paint-booth-v2.html")
    assert "Range Remapper…" in html
    assert 'id="specMaterialRemapOverlay"' in html
    for input_id in (
        "specRemapMLow", "specRemapMHigh", "specRemapRLow",
        "specRemapRHigh", "specRemapCCLow", "specRemapCCHigh",
    ):
        assert f'id="{input_id}"' in html
    assert "applying this clears a flat Material Sampler override" in html
    assert "paint RGB + alpha locked" in html
    module = "js/canvas/zone/spec-material-remap.js"
    assert html.index(module) < html.index('<script src="paint-booth-3-canvas.js')
    assert "spec-material-remap.js?v=spb93-spec-tools-live-preview-20260809c" in html
    assert module in json.loads(read("scripts/runtime-sync-manifest.json"))["files"]
    css = read("paint-booth-v2.css")
    assert ".material-remap-row" in css
    assert ".material-remap-bar" in css


def test_controller_is_selection_scoped_locked_noop_safe_and_clears_flat_override_once():
    source = read("js/canvas/zone/spec-material-remap.js")
    assert "countSelected(zone && zone.regionMask)" in source
    assert "zone.lockIntensity" in source
    noop_at = source.index("if (remapsEqual(beforeRemap, next)")
    history_at = source.index("pushZoneUndo('Remap spec material ranges')")
    assign_at = source.index("zone.specMaterialRemap = next", history_at)
    clear_flat_at = source.index("zone.specMaterialOverride = null", assign_at)
    assert noop_at < history_at < assign_at < clear_flat_at
    assert "_psdLayers" not in source
    assert "paintImageData" not in source
    assert "session.previewContext.putImageData" in source


def test_private_live_preview_restores_on_cancel_and_snapshots_baseline_before_apply():
    source = read("js/canvas/zone/spec-material-remap.js")
    assert "function scheduleLivePreview()" in source
    assert "previewSession.zone.specMaterialRemap" in source
    assert "history and autosave remain untouched until Apply" in source
    assert "endPreviewSession(true);" in source
    assert "renderLocalSpecPreview(remap)" in source
    assert "root.__spbSpecSig = ''" in source
    assert "root.__spbSpecSig = session.previewSpecSig" in source
    restore_at = source.index("zone.specMaterialRemap = beforeRemap")
    history_at = source.index("pushZoneUndo('Remap spec material ranges')")
    commit_at = source.index("zone.specMaterialRemap = next")
    assert restore_at < history_at < commit_at


def test_spec_tool_family_uses_the_public_live_preview_bridge():
    for relative in (
        "js/canvas/zone/decal-rescue.js",
        "js/canvas/zone/spec-lighting-mask.js",
        "js/canvas/zone/spec-material-sampler.js",
        "js/canvas/zone/spec-material-select.js",
        "js/canvas/zone/spec-material-remap.js",
    ):
        source = read(relative)
        assert "root.spbKickLivePreview" in source
        assert "kickLivePreview();" in source
    canvas = read("paint-booth-3-canvas.js")
    hash_start = canvas.index("function getZoneConfigHash()")
    hash_end = canvas.index("function triggerPreviewRender", hash_start)
    hash_source = canvas[hash_start:hash_end]
    for field in ("specLightingMask", "specMaterialOverride", "specMaterialRemap"):
        assert f"{field}: z.{field}" in hash_source
    bridge_start = canvas.index("window.spbKickLivePreview = function")
    bridge = canvas[bridge_start:canvas.index("async function _renderLatestInteractivePreview", bridge_start)]
    assert "window.__spbPreviewBodyMemo = null" in bridge


def test_config_payload_and_preview_adapter_share_one_remap_contract():
    config = read("js/zones/zone-config-zone-map-controls.js")
    assert config.count("specMaterialRemap: z.specMaterialRemap ?? null") == 2
    payload = read("paint-booth-5-api-render.js")
    assert "zoneObj.spec_material_remap = normalized" in payload
    assert payload.count("_applySpecMaterialRemap(zoneObj, z);") == 4
    assert payload.index("_applySpecMaterialRemap(zoneObj, z);") < payload.index("_applySpecMaterialOverride(zoneObj, z);")
    server = read("server.py")
    assert '_material_remap = z.get("spec_material_remap")' in server
    assert 'for _channel in ("m", "r", "cc")' in server


def test_engine_remap_changes_only_first_three_channels_and_does_not_mutate_input():
    import shokker_engine_v2 as engine

    source = np.arange(4 * 5 * 4, dtype=np.uint8).reshape(4, 5, 4)
    remap = {
        "m": {"low": 100, "high": 200},
        "r": {"low": 10, "high": 110},
        "cc": {"low": 20, "high": 220},
    }
    out = engine._apply_zone_spec_material_remap(source, {"spec_material_remap": remap})
    assert out is not source
    for channel, (low, high) in enumerate(((100, 200), (10, 110), (20, 220))):
        expected = np.rint(low + source[:, :, channel].astype(np.float32) / 255 * (high - low)).astype(np.uint8)
        np.testing.assert_array_equal(out[:, :, channel], expected)
    np.testing.assert_array_equal(out[:, :, 3], source[:, :, 3])
    assert engine._apply_zone_spec_material_remap(source, {}) is source


def test_real_multi_zone_render_preserves_imported_texture_and_confines_exact_footprint(tmp_path: Path):
    import shokker_engine_v2 as engine

    size = 64
    paint = np.full((size, size, 3), (185, 65, 25), dtype=np.uint8)
    paint_path = tmp_path / "paint.png"
    Image.fromarray(paint, mode="RGB").save(paint_path)

    yy, xx = np.mgrid[0:size, 0:size]
    imported = np.empty((size, size, 4), dtype=np.uint8)
    imported[:, :, 0] = (xx * 4 + yy) % 256
    imported[:, :, 1] = (yy * 4 + xx) % 256
    imported[:, :, 2] = (xx * 3 + yy * 2) % 256
    imported[:, :, 3] = 220
    spec_path = tmp_path / "imported.png"
    Image.fromarray(imported, mode="RGBA").save(spec_path)

    region = np.zeros((size, size), dtype=np.float32)
    region[8:40, 16:48] = 1.0
    zone = {
        "name": "Imported texture tune",
        "color": "everything",
        "region_mask": region,
        "zone_spec_map": str(spec_path),
        "zone_spec_map_strength": 1.0,
        "hard_edge": True,
    }
    baseline_paint, baseline = engine.build_multi_zone(
        str(paint_path), str(tmp_path / "baseline"), [dict(zone)], seed=34, preview_mode=True
    )
    remap = {
        "m": {"low": 100, "high": 200},
        "r": {"low": 50, "high": 150},
        "cc": {"low": 10, "high": 60},
    }
    tuned_zone = dict(zone)
    tuned_zone["spec_material_remap"] = remap
    tuned_paint, tuned = engine.build_multi_zone(
        str(paint_path), str(tmp_path / "tuned"), [tuned_zone], seed=34, preview_mode=True
    )
    np.testing.assert_array_equal(baseline_paint[:, :, :3], paint)
    np.testing.assert_array_equal(tuned_paint[:, :, :3], paint)

    inside = np.zeros((size, size), dtype=bool)
    inside[8:40, 16:48] = True
    outside = ~inside
    for channel, key in enumerate(("m", "r", "cc")):
        low, high = remap[key]["low"], remap[key]["high"]
        expected = np.rint(low + baseline[:, :, channel].astype(np.float32) / 255 * (high - low)).astype(tuned.dtype)
        np.testing.assert_array_equal(tuned[inside, channel], expected[inside])
        assert np.unique(tuned[inside, channel]).size > 8
        np.testing.assert_array_equal(tuned[outside, channel], baseline[outside, channel])
    np.testing.assert_array_equal(tuned[:, :, 3], baseline[:, :, 3])


def test_flat_sample_and_lighting_alpha_have_explicit_precedence_after_remap():
    source = read("shokker_engine_v2.py")
    common = source.index("zone_spec = _apply_zone_spec_material_remap(zone_spec, zone)", source.index("# SPB-93 tick 30"))
    flat = source.index("zone_spec = _apply_zone_spec_material_override(zone_spec, zone)", common)
    alpha = source.index("zone_spec = _apply_zone_spec_lighting_mask(zone_spec, zone)", flat)
    assert common < flat < alpha
