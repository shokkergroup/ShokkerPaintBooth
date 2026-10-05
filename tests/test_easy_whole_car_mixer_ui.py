"""Focused UI/runtime contracts for Easy Whole Car's 1-4 material mixer.

These tests execute the shipping mix math and material-lighting preview directly
from ``js/spb-easy-mode.js``.  Structural assertions cover the surrounding DOM
workflow that is intentionally not exposed as a public JavaScript module.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
EASY_JS = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ui_runtime() -> dict:
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; Whole Car UI harness requires Node 18+")
    harness = ROOT / "tests" / "_runtime_harness" / "easy_whole_car_mix_ui.mjs"
    proc = subprocess.run(
        ["node", str(harness)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.fail(
            "Whole Car UI runtime harness failed "
            f"(exit {proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def _weights(rows: list[dict]) -> list[int]:
    return [row["weight"] for row in rows]


def _assert_exact_blend(rows: list[dict]) -> None:
    weights = _weights(rows)
    assert sum(weights) == 100
    assert all(weight >= 1 for weight in weights)


def test_one_through_four_additions_always_form_one_exact_100_percent_mix(
    ui_runtime: dict,
) -> None:
    additions = ui_runtime["additions"]
    assert [_weights(rows) for rows in additions] == [
        [100],
        [50, 50],
        [34, 33, 33],
        [25, 25, 25, 25],
    ]
    for rows in additions:
        _assert_exact_blend(rows)


def test_normalization_is_deterministic_and_preserves_relative_recipe(
    ui_runtime: dict,
) -> None:
    normalized = ui_runtime["normalizations"]
    assert _weights(normalized["one"]) == [100]
    assert _weights(normalized["two"]) == [70, 30]
    assert _weights(normalized["three_tie"]) == [34, 33, 33]
    assert _weights(normalized["four"]) == [25, 25, 25, 25]
    for rows in normalized.values():
        _assert_exact_blend(rows)


def test_moving_one_mix_slider_rebalances_the_others_to_exactly_100(
    ui_runtime: dict,
) -> None:
    rebalanced = ui_runtime["rebalances"]
    assert _weights(rebalanced["proportional"]) == [80, 12, 8]
    assert _weights(rebalanced["two_clamped"]) == [99, 1]
    assert _weights(rebalanced["four_clamped"]) == [1, 1, 97, 1]
    for rows in rebalanced.values():
        _assert_exact_blend(rows)


def test_master_strength_and_detail_size_are_independent_controls(
    ui_runtime: dict,
) -> None:
    controls = ui_runtime["controls"]
    initial = controls["initial"]
    after_strength = controls["afterStrength"]
    after_detail = controls["afterDetail"]

    assert initial["materialStackAmount"] == pytest.approx(0.4)
    assert initial["materialScale"] == pytest.approx(0.55)
    assert _weights(initial["materialStack"]) == [65, 35]

    assert after_strength["materialStackAmount"] == pytest.approx(0.15)
    assert after_strength["materialScale"] == initial["materialScale"]
    assert after_strength["materialStack"] == initial["materialStack"]

    assert after_detail["materialScale"] == pytest.approx(0.3)
    assert after_detail["materialStackAmount"] == after_strength["materialStackAmount"]
    assert after_detail["materialStack"] == initial["materialStack"]

    assert "FINISH STRENGTH" in EASY_JS
    assert "DETAIL SIZE" in EASY_JS
    assert 'id="spbEasyWholeAmount"' in EASY_JS
    assert 'id="spbEasyWholeScale"' in EASY_JS


def test_active_zone_hydration_wins_over_stale_remembered_ui_state(
    ui_runtime: dict,
) -> None:
    hydration = ui_runtime["hydration"]
    assert hydration["hydrated"] is True
    state = hydration["state"]
    assert _weights(state["wholeStack"]) == [20, 80]
    assert state["wholeAmount"] == 0
    assert state["wholeScale"] == pytest.approx(0.35)

    rail = EASY_JS[
        EASY_JS.index("function renderWholeRail") : EASY_JS.index("function wholeStackHtml")
    ]
    assert rail.index("readWholeMaterialPlan()") < rail.index("hydrateWholeState(activePlan)")


def test_opening_whole_car_is_navigation_and_cannot_repaint_from_local_storage() -> None:
    rail = EASY_JS[
        EASY_JS.index("function renderWholeRail") : EASY_JS.index("function wholeStackHtml")
    ]
    before_markup = rail[: rail.index("els.rail.innerHTML")]
    assert "readWholeMaterialPlan()" in before_markup
    assert "hydrateWholeState(activePlan)" in before_markup
    assert "state.wholeStack = [];" in before_markup
    assert "applyWholeStack(" not in before_markup
    assert "kickPreview(" not in before_markup
    assert "zones =" not in before_markup

    fork = EASY_JS[
        EASY_JS.index("function renderFork") : EASY_JS.index("// --- WHOLE CAR")
    ]
    assert "state.view = 'whole'; renderRail();" in fork
    assert "applyWholeStack(" not in fork


def test_legacy_one_finish_design_is_visible_but_upgrades_before_an_explicit_save() -> None:
    rail = EASY_JS[
        EASY_JS.index("function renderWholeRail") : EASY_JS.index("function wholeStackHtml")
    ]
    save_flow = EASY_JS[
        EASY_JS.index("function onSaveClick") : EASY_JS.index("function startProgressMirror")
    ]
    assert "readWholeMaterialPlan() || readLegacyWholeMaterialPlan()" in rail
    assert "readLegacyWholeMaterialPlan()" in save_flow
    assert "hydrateWholeState(legacyWhole)" in save_flow
    assert "applyWholeStack(true, false, true)" in save_flow
    assert save_flow.index("applyWholeStack(true, false, true)") < save_flow.index("safeDoRender()")


def test_material_preview_is_driven_by_actual_m_r_cc_pixels_without_mutating_source(
    ui_runtime: dict,
) -> None:
    bright = ui_runtime["preview"]["bright"]
    dark = ui_runtime["preview"]["dark"]
    assert bright["source"] == [100, 120, 140, 255]
    assert dark["source"] == bright["source"]
    assert bright["rendered"] != dark["rendered"]
    assert bright["rendered"] != bright["source"]
    assert dark["rendered"] != dark["source"]
    assert bright["canvasHidden"] is False
    assert bright["imageHidden"] is True

    preview = EASY_JS[
        EASY_JS.index("function renderWholeMaterialPreview") : EASY_JS.index(
            "function ensureSourceCanvas"
        )
    ]
    for channel_access in (
        "specPixels[i] / 255",
        "specPixels[i + 1] / 255",
        "specPixels[i + 2] / 255",
    ):
        assert channel_access in preview
    assert "drawImage(els.sourceCanvas" in preview
    assert "putImageData(paintPixels" in preview


def test_material_preview_has_no_fake_or_moving_spotlight() -> None:
    preview = EASY_JS[
        EASY_JS.index("function renderWholeMaterialPreview") : EASY_JS.index(
            "function ensureSourceCanvas"
        )
    ]
    forbidden = (
        "createLinearGradient",
        "createRadialGradient",
        "requestAnimationFrame",
        "setInterval",
        "setTimeout",
        "translate(",
        "rotate(",
    )
    for token in forbidden:
        assert token not in preview
    assert "var x" not in preview and "var y" not in preview
    assert "Material lighting proof — no spotlight, no recolor" in EASY_JS


def test_empty_whole_car_still_shows_the_loaded_source_instead_of_a_black_hero() -> None:
    stage = EASY_JS[
        EASY_JS.index("function syncStage") : EASY_JS.index("function openPaint")
    ]
    assert "var sourceOnly" in stage
    assert "state.view === 'whole' && !wholeProof" in stage
    assert "sourceOnly ? 'YOUR PAINT'" in stage
    assert "wholeProof || sourceOnly || (byColor && !byColorHasMaterial)" in stage


def test_whole_material_search_never_hides_an_active_filter_or_traps_starter_shelf() -> None:
    rail = EASY_JS[
        EASY_JS.index("function renderWholeRail") : EASY_JS.index("function wholeStackHtml")
    ]
    assert 'id="spbEasySearch" value="' in rail
    assert "if (_catalogMode || _searchText)" in rail
    assert "_searchText = '';" in rail
    assert "els.search.value = '';" in rail
