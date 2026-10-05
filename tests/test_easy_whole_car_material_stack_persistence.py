"""Regression coverage for Easy Whole Car material-stack state round-trips."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "paint-booth-2-state-zones.js"


def _section(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin)]


def test_active_state_allowlists_keep_whole_car_material_stack() -> None:
    source = STATE.read_text(encoding="utf-8")
    assert "function _cloneMaterialStackState(zone)" in source

    sections = {
        "built-in preset": _section(source, "function _applyPresetById", "// ===== TOAST"),
        "config save": _section(source, "function getConfig()", "function loadConfigFromObj"),
        "config load": _section(source, "function loadConfigFromObj", "function getSessionConfig"),
        "preset export": _section(source, "function exportPreset()", "function buildPresetDescription"),
        "preset import": _section(source, "function _applyPresetFromObject", "function loadConfig()"),
    }
    required = (
        "materialStack:",
        "materialStackMode:",
        "materialStackAmount:",
        "materialScale:",
    )
    for label, body in sections.items():
        for needle in required:
            assert needle in body, f"{label} drops {needle}"

    export_body = _section(source, "function exportJSON()", "// ===== MODAL")
    for needle in ("entry.materialStack", "entry.materialStackMode", "entry.materialStackAmount", "entry.materialScale"):
        assert needle in export_body


def test_extracted_config_and_preset_helpers_round_trip_snake_and_falsy_values() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for the live JS persistence contract")

    map_module = json.dumps((ROOT / "js/zones/zone-config-zone-map-controls.js").as_posix())
    preset_module = json.dumps((ROOT / "js/zones/zone-config-preset-controls.js").as_posix())
    script = f"""
const assert = require('assert');
require({map_module});
const maps = globalThis.SPBZoneConfigZoneMapControls.install();
const original = {{
  name: 'Whole Car',
  material_stack: [
    {{id: 'chrome', registry_type: 'base', weight: 35}},
    {{id: 'candy', registry_type: 'monolithic', weight: 65}}
  ],
  material_stack_mode: 'auto_trace',
  material_stack_amount: 0,
  material_scale: 0
}};
const saved = maps.serializeZones([original])[0];
assert.deepStrictEqual(saved.materialStack, original.material_stack);
assert.strictEqual(saved.materialStackMode, 'auto_trace');
assert.strictEqual(saved.materialStackAmount, 0);
assert.strictEqual(saved.materialScale, 0);
saved.materialStack[0].id = 'mutated';
assert.strictEqual(original.material_stack[0].id, 'chrome');
const restored = maps.hydrateZones([maps.serializeZones([original])[0]])[0];
assert.deepStrictEqual(restored.materialStack, original.material_stack);
assert.strictEqual(restored.materialStackAmount, 0);
assert.strictEqual(restored.materialScale, 0);

require({preset_module});
let applied = null;
globalThis.SPBZoneConfigPresetControls.install({{
  document: {{getElementById: () => null}},
  setZones: value => {{ applied = value; }},
  setSelectedZoneIndex: () => {{}},
  newZoneId: () => 'zone_test',
  sanitizeZones: () => {{}},
  confirm: () => true,
  renderZones: () => {{}},
  triggerPreviewRender: () => {{}},
  autoSave: () => {{}},
  showToast: () => {{}}
}});
globalThis._applyPresetFromObject({{
  name: 'Material Mix',
  zones: [original],
  settings: null
}});
assert.ok(applied && applied.length === 1);
assert.deepStrictEqual(applied[0].materialStack, original.material_stack);
assert.strictEqual(applied[0].materialStackMode, 'auto_trace');
assert.strictEqual(applied[0].materialStackAmount, 0);
assert.strictEqual(applied[0].materialScale, 0);
"""
    result = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "relative",
    (
        "paint-booth-2-state-zones.js",
        "js/zones/zone-config-zone-map-controls.js",
        "js/zones/zone-config-preset-controls.js",
        "js/zones/zone-preset-gallery-controls.js",
        "js/zones/export-script-controls.js",
    ),
)
def test_runtime_copy_matches_source(relative: str) -> None:
    assert (ROOT / relative).read_bytes() == (ROOT / "electron-app/server" / relative).read_bytes()
