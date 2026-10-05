"""SPB-93 Pass 30: iRacing spec-alpha Lighting Mask contract."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_pure_zone_module_presets_are_clamped_and_touch_only_alpha_setting():
    script = r"""
const api = require('./js/canvas/zone/spec-lighting-mask.js');
const zone = { regionMask: new Uint8Array([0, 255, 2]), base: 'chrome', marker: 9 };
const applied = api.applyPatchToZone(zone, 'kill');
process.stdout.write(JSON.stringify({
  keys: Object.keys(api.PRESETS),
  count: api.countSelected(zone.regionMask),
  applied,
  value: zone.specLightingMask,
  base: zone.base,
  marker: zone.marker,
  low: api.normalizeValue(-12),
  high: api.normalizeValue(999),
  source: api.buildZonePatch('source'),
  invalid: api.buildZonePatch('bogus')
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True
    )
    payload = json.loads(result.stdout)
    assert payload == {
        "keys": ["source", "full", "reduced", "kill"],
        "count": 2,
        "applied": True,
        "value": 0,
        "base": "chrome",
        "marker": 9,
        "low": 0,
        "high": 255,
        "source": {"specLightingMask": None},
        "invalid": None,
    }


def test_tool_is_discoverable_truthful_and_loaded_before_canvas():
    html = read("paint-booth-v2.html")
    assert 'onclick="openSpecLightingMask()"' in html
    assert "It is not a shortcut for matte vinyl" in html
    assert "spec TGA alpha channel" in html
    assert "paint RGB or the Metallic, Roughness, and Clearcoat channels" in html
    module = 'js/canvas/zone/spec-lighting-mask.js'
    assert html.index(module) < html.index('<script src="paint-booth-3-canvas.js')
    assert module in json.loads(read("scripts/runtime-sync-manifest.json"))["files"]
    css = read("paint-booth-v2.css")
    assert ".lighting-mask-alpha" in css
    assert ".lighting-mask-kill" in css


def test_zone_config_round_trip_persists_nullable_lighting_mask():
    source = read("js/zones/zone-config-zone-map-controls.js")
    assert source.count("specLightingMask: z.specLightingMask ?? null") == 2


def test_every_render_payload_builder_carries_zero_alpha_override():
    source = read("paint-booth-5-api-render.js")
    assert "z.specLightingMask == null" in source
    assert "zoneObj.spec_lighting_mask" in source
    # Shared core plus Fleet, Season, and canonical preview/full/PS builder.
    assert source.count("_applySpecLightingMask(zoneObj, z);") == 4


def test_preview_adapter_preserves_explicit_zero():
    source = read("server.py")
    assert 'if z.get("spec_lighting_mask") is not None:' in source
    assert 'zone_obj["spec_lighting_mask"] = int(round(_clamp(' in source


def test_engine_override_changes_only_alpha_and_clamps():
    import shokker_engine_v2 as engine

    source = np.zeros((3, 4, 4), dtype=np.uint8)
    source[:, :, 0] = 17
    source[:, :, 1] = 123
    source[:, :, 2] = 44
    source[:, :, 3] = np.arange(12, dtype=np.uint8).reshape(3, 4)

    untouched = engine._apply_zone_spec_lighting_mask(source, {})
    assert untouched is source

    killed = engine._apply_zone_spec_lighting_mask(source, {"spec_lighting_mask": 0})
    np.testing.assert_array_equal(killed[:, :, :3], source[:, :, :3])
    assert np.all(killed[:, :, 3] == 0)
    np.testing.assert_array_equal(source[:, :, 3], np.arange(12, dtype=np.uint8).reshape(3, 4))

    high = engine._apply_zone_spec_lighting_mask(source, {"spec_lighting_mask": 999})
    assert np.all(high[:, :, 3] == 255)


def test_iron_rules_and_32bit_tga_export_preserve_killed_alpha(tmp_path: Path):
    import shokker_engine_v2 as engine

    source = np.zeros((4, 5, 4), dtype=np.uint8)
    source[:, :, 0] = 20
    source[:, :, 1] = 100
    source[:, :, 2] = 30
    source[:, :, 3] = 255
    killed = engine._apply_zone_spec_lighting_mask(source, {"spec_lighting_mask": 0})
    safe = engine._enforce_iron_rules(killed)
    out = tmp_path / "car_spec_12345.tga"
    engine.write_tga_32bit(str(out), safe)
    decoded = np.asarray(Image.open(out).convert("RGBA"))
    np.testing.assert_array_equal(decoded[:, :, :3], safe[:, :, :3])
    assert np.all(decoded[:, :, 3] == 0)


def test_build_multi_zone_applies_alpha_only_inside_exact_region(tmp_path: Path):
    import shokker_engine_v2 as engine

    size = 64
    paint = np.full((size, size, 3), (70, 110, 180), dtype=np.uint8)
    paint_path = tmp_path / "paint.png"
    Image.fromarray(paint, mode="RGB").save(paint_path)
    region = np.zeros((size, size), dtype=np.float32)
    region[12:52, 18:46] = 1.0
    base_zone = {
        "name": "Grille cutout",
        "color": "everything",
        "intensity": "100",
        "base": "gloss",
        "base_color_mode": "source",
        "region_mask": region,
    }

    _, normal = engine.build_multi_zone(
        str(paint_path), str(tmp_path / "normal"), [dict(base_zone)], seed=93, preview_mode=True
    )
    killed_zone = dict(base_zone)
    killed_zone["spec_lighting_mask"] = 0
    _, killed = engine.build_multi_zone(
        str(paint_path), str(tmp_path / "killed"), [killed_zone], seed=93, preview_mode=True
    )

    np.testing.assert_array_equal(killed[:, :, :3], normal[:, :, :3])
    assert np.all(killed[12:52, 18:46, 3] == 0)
    outside = np.ones((size, size), dtype=bool)
    outside[12:52, 18:46] = False
    assert np.all(killed[outside, 3] == normal[outside, 3])
