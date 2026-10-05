"""Runtime proof for overlay-only zones reaching the renderer.

This guards the painter-facing failure where a zone restricted to a source
layer (for example Numbers) looked like it covered nothing because the JS
payload builders only treated `base` / `finish` as renderable material.
An active Base Overlay Layer without a primary base was silently dropped
before preview/render/export ever reached the engine.

The fix keeps overlay-only zones renderable by giving them a neutral gloss
anchor in the payload. That lets the overlay tint/spec logic respond to the
zone mask instead of disappearing as "empty".
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "overlay_only_zone_payload.mjs"
CANVAS_SRC = REPO / "paint-booth-3-canvas.js"


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"overlay_only_zone_payload harness failed (exit {proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_overlay_only_zone_survives_payload_build(harness):
    zones = harness["overlay_only"]
    assert len(zones) == 1, "overlay-only zone was dropped before render"
    zone = zones[0]
    assert zone["base"] == "gloss", (
        "overlay-only zone did not get the neutral gloss anchor needed for "
        "compose_finish/compose_paint_mod"
    )
    assert zone["pattern"] == "none"
    assert zone["second_base"] == "gloss"
    assert zone["second_base_color_source"] == "overlay"
    assert zone["second_base_strength"] == 1.0


def test_overlay_color_source_only_zone_survives_payload_build(harness):
    zones = harness["overlay_color_source_only"]
    assert len(zones) == 1, (
        "zone with only secondBaseColorSource active was still treated as empty"
    )
    zone = zones[0]
    assert zone["base"] == "gloss"
    assert zone["pattern"] == "none"
    assert "second_base" not in zone, (
        "color-source-only overlay should keep the neutral base anchor separate "
        "from the optional explicit overlay base id"
    )
    assert zone["second_base_color_source"] == "overlay"
    assert zone["second_base_strength"] == 1.0


def test_scoped_white_zone_keeps_intentional_special_overlay(harness):
    zones = harness["scoped_white_special_overlay"]
    assert len(zones) == 1
    zone = zones[0]
    assert zone["second_base"] == "mono:firefly_glow"
    assert zone["second_base_color_source"] == "overlay"
    assert zone["second_base_strength"] == 1.0


def test_special_overlay_base_can_use_explicit_solid_color(harness):
    zone = harness["special_overlay_solid_color"][0]
    assert zone["second_base"] == "mono:firefly_glow"
    assert zone["second_base_color_source"] == "solid"
    assert zone["second_base_color"] == pytest.approx([0x22 / 255, 0x44 / 255, 1.0])


def test_legacy_null_color_source_on_special_overlay_serializes_as_same_overlay_special(harness):
    zone = harness["legacy_special_overlay_solid_color"][0]
    assert zone["second_base"] == "mono:firefly_glow"
    assert zone["second_base_color_source"] == "overlay"
    assert zone["second_base_color"] == pytest.approx([0x22 / 255, 0x44 / 255, 1.0])


def test_regular_overlay_base_can_use_special_color_source(harness):
    zone = harness["regular_overlay_special_color"][0]
    assert zone["second_base"] == "f_metallic"
    assert zone["second_base_color_source"] == "mono:firefly_glow"


def test_pattern_reactive_overlay_defaults_to_primary_pattern(harness):
    zone = harness["pattern_reactive_overlay"][0]
    assert zone["pattern"] == "speed_lines"
    assert zone["second_base"] == "pf_bright_orchid_pulse"
    assert zone["second_base_blend_mode"] == "pattern-vivid"
    assert zone["second_base_pattern"] == ""


def test_fifth_overlay_layer_uses_same_special_color_contract(harness):
    zone = harness["fifth_layer_special_color"][0]
    assert zone["fifth_base"] == "f_metallic"
    assert zone["fifth_base_color_source"] == "mono:firefly_glow"
    assert zone["fifth_base_strength"] == 0.75


def test_truly_empty_zone_stays_excluded(harness):
    assert harness["empty_zone_count"] == 0


def test_preview_hash_and_filters_use_renderable_material_helper():
    src = CANVAS_SRC.read_text(encoding="utf-8")
    assert src.count("_zoneHasRenderableMaterialClient(z)") >= 4, (
        "preview/script filters still look only at z.base || z.finish in at least "
        "one critical client path"
    )
    assert "body.zone_hashes = zones.filter(z => !z.muted && _zoneHasRenderableMaterialClient(z)).map(" in src
