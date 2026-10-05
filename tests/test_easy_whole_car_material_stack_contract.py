"""Regression contract for Easy Mode's Whole Car material stack.

The Whole Car path is intentionally *material only*: one through four typed
Paint Booth finishes may shape the iRacing M/R/Cc map, while the source paint
pixels remain byte-identical.  These tests exercise the public renderer so a
future UI/payload refactor cannot accidentally reintroduce the old "full look"
paint mutation or silently drop a layer/slider change.

Production contract (2026-07-22):

* ``zone["material_stack"]`` contains 1..4 ``{id, registry_type, weight}``
  rows, with ``registry_type`` explicitly ``base`` or ``monolithic``.
* ``material_stack_mode="auto_trace"`` uses the paint-aware Spec Sculpt
  compositor for spec only.
* ``material_scale`` changes material feature scale, never diffuse paint.
* invalid depth, IDs, or typed-registry mismatches fail loudly.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image


@pytest.fixture(scope="module")
def engine():
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        import shokker_engine_v2 as runtime_engine

        runtime_engine._ensure_expansions_loaded()
    return runtime_engine


@pytest.fixture(scope="module")
def source_paint(tmp_path_factory) -> tuple[Path, np.ndarray]:
    """A non-flat RGB paint that makes accidental recoloring easy to detect."""
    root = tmp_path_factory.mktemp("whole_car_material_stack")
    path = root / "source.png"
    yy, xx = np.indices((64, 64), dtype=np.uint16)
    rgb = np.empty((64, 64, 3), dtype=np.uint8)
    rgb[..., 0] = ((xx * 7 + yy * 3) % 256).astype(np.uint8)
    rgb[..., 1] = ((xx * 2 + yy * 11 + 29) % 256).astype(np.uint8)
    rgb[..., 2] = ((xx * 13 + yy * 5 + 71) % 256).astype(np.uint8)
    Image.fromarray(rgb, "RGB").save(path)
    return path, rgb


def _row(finish_id: str, registry_type: str, weight: float) -> dict:
    return {
        "id": finish_id,
        "registry_type": registry_type,
        "weight": weight,
    }


STACKS = {
    1: [_row("chrome", "base", 100)],
    2: [
        _row("chrome", "base", 55),
        _row("acid_etched_glass", "monolithic", 45),
    ],
    4: [
        _row("chrome", "base", 35),
        _row("acid_etched_glass", "monolithic", 25),
        _row("matte", "base", 20),
        _row("acid_trip", "monolithic", 20),
    ],
}


def _zone(
    stack: list[dict],
    *,
    material_scale: float = 1.0,
    material_stack_amount: float | None = None,
) -> dict:
    zone = {
        "name": "Whole Car Material Mix",
        "color": "everything",
        "colorMode": "special",
        "pattern": "none",
        "intensity": "100",
        "material_stack": [dict(item) for item in stack],
        "material_stack_mode": "auto_trace",
        "material_scale": material_scale,
    }
    if material_stack_amount is not None:
        zone["material_stack_amount"] = material_stack_amount
    return zone


def _clear_zone_cache(engine) -> None:
    cache = getattr(engine.build_multi_zone, "_zone_cache", None)
    if isinstance(cache, dict):
        cache.clear()


def _render(
    engine,
    source_paint: tuple[Path, np.ndarray],
    stack: list[dict],
    *,
    seed: int = 7731,
    clear_cache: bool = False,
    stack_amount: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if clear_cache:
        _clear_zone_cache(engine)
    paint_path, _source_rgb = source_paint
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        paint, spec = engine.build_multi_zone(
            str(paint_path),
            None,
            [_zone(stack, material_stack_amount=stack_amount)],
            seed=seed,
            preview_mode=True,
        )
    return np.asarray(paint), np.asarray(spec)


def _assert_iracing_safe_spec(spec: np.ndarray) -> None:
    assert spec.shape == (64, 64, 4)
    assert spec.dtype == np.uint8
    assert np.all(spec[..., 3] == 255), "material stack must export opaque iRacing spec alpha"

    non_chrome = spec[..., 0] < 240
    assert np.all(spec[..., 1][non_chrome] >= 15), (
        "non-chrome material pixels violated iRacing's roughness floor"
    )
    assert np.all(spec[..., 2] >= 16), (
        "Whole Car material stacks are generated materials, so clearcoat must "
        "honor the standard iRacing floor"
    )

    neutral = np.asarray([5, 100, 16], dtype=np.int16)
    response_delta = np.abs(spec[..., :3].astype(np.int16) - neutral).mean()
    assert float(response_delta) >= 3.0, (
        "material_stack produced the untouched neutral spec plate; the stack "
        "was accepted but never dispatched to the paint-aware compositor"
    )


@pytest.mark.parametrize("stack_size", [1, 2, 4])
def test_one_two_and_four_typed_materials_preserve_paint_byte_identical(
    engine, source_paint, stack_size
):
    paint, spec = _render(
        engine,
        source_paint,
        STACKS[stack_size],
        clear_cache=True,
    )
    _source_path, source_rgb = source_paint

    assert paint.dtype == np.uint8
    assert paint.shape == source_rgb.shape
    assert np.array_equal(paint, source_rgb), (
        f"{stack_size}-material Whole Car mix changed diffuse paint bytes. "
        "Easy Whole Car is spec/material-only; colors, numbers, and decals must stay."
    )
    _assert_iracing_safe_spec(spec)


def test_same_seed_and_stack_are_deterministic_without_cache_help(engine, source_paint):
    _paint_a, spec_a = _render(
        engine, source_paint, STACKS[4], seed=99127, clear_cache=True
    )
    _paint_b, spec_b = _render(
        engine, source_paint, STACKS[4], seed=99127, clear_cache=True
    )

    assert np.array_equal(spec_a, spec_b), (
        "identical Whole Car material stacks changed between uncached renders"
    )


def test_weight_change_changes_spec_and_invalidates_zone_cache(engine, source_paint):
    chrome_heavy = [
        _row("chrome", "base", 90),
        _row("matte", "base", 10),
    ]
    matte_heavy = [
        _row("chrome", "base", 10),
        _row("matte", "base", 90),
    ]

    _paint_a, spec_a = _render(
        engine, source_paint, chrome_heavy, seed=419, clear_cache=True
    )
    # Deliberately keep the cache warm. This catches a material_stack omission
    # from the renderer's zone-cache key—the exact failure a live slider causes.
    _paint_b, spec_b = _render(
        engine, source_paint, matte_heavy, seed=419, clear_cache=False
    )

    assert not np.array_equal(spec_a, spec_b), (
        "changing material weights reused a stale spec; material_stack must be "
        "part of the zone cache identity"
    )
    mean_delta = np.abs(
        spec_a[..., :3].astype(np.float32).mean(axis=(0, 1))
        - spec_b[..., :3].astype(np.float32).mean(axis=(0, 1))
    )
    assert float(mean_delta.max()) >= 8.0, (
        f"90/10 versus 10/90 barely changed the material response: {mean_delta.tolist()}"
    )


def test_fourth_material_is_rendered_instead_of_accepted_then_ignored(engine, source_paint):
    common = [
        _row("chrome", "base", 25),
        _row("matte", "base", 25),
        _row("gloss", "base", 25),
    ]
    with_acid_trip = common + [_row("acid_trip", "monolithic", 25)]
    with_etched_glass = common + [
        _row("acid_etched_glass", "monolithic", 25)
    ]

    _paint_a, spec_a = _render(
        engine, source_paint, with_acid_trip, seed=6203, clear_cache=True
    )
    _paint_b, spec_b = _render(
        engine, source_paint, with_etched_glass, seed=6203, clear_cache=True
    )

    assert not np.array_equal(spec_a, spec_b), (
        "changing only material slot four had no effect; the UI may show four "
        "slots while the engine renders fewer"
    )


def test_independent_slider_total_controls_overall_material_amount(engine, source_paint):
    stack = [
        _row("chrome", "base", 60),
        _row("acid_trip", "monolithic", 40),
    ]
    paint_full, spec_full = _render(
        engine,
        source_paint,
        stack,
        seed=873,
        clear_cache=True,
        stack_amount=1.0,
    )
    # Keep cache warm so amount must be part of the renderer cache identity.
    paint_quiet, spec_quiet = _render(
        engine,
        source_paint,
        stack,
        seed=873,
        clear_cache=False,
        stack_amount=0.25,
    )
    _source_path, source_rgb = source_paint

    assert np.array_equal(paint_full, source_rgb)
    assert np.array_equal(paint_quiet, source_rgb)
    assert not np.array_equal(spec_full, spec_quiet)
    neutral = np.asarray([0.0, 160.0, 255.0], dtype=np.float32)
    full_distance = np.abs(spec_full[..., :3].astype(np.float32) - neutral).mean()
    quiet_distance = np.abs(spec_quiet[..., :3].astype(np.float32) - neutral).mean()
    assert quiet_distance < full_distance * 0.45, (
        "25% overall material amount did not move the result substantially "
        "toward the quiet iRacing material response"
    )


def test_fifth_material_is_rejected_instead_of_silently_truncated(engine):
    too_many = STACKS[4] + [_row("gloss", "base", 10)]
    with pytest.raises(ValueError):
        engine._validate_zone_render_ids(_zone(too_many), 0)


def test_unknown_material_id_is_rejected(engine):
    with pytest.raises(ValueError):
        engine._validate_zone_render_ids(
            _zone([_row("definitely_not_a_shipping_finish", "base", 100)]),
            0,
        )


@pytest.mark.parametrize(
    "bad_row",
    [
        _row("chrome", "monolithic", 100),
        _row("acid_trip", "base", 100),
    ],
)
def test_typed_registry_mismatch_is_rejected(engine, bad_row):
    with pytest.raises(ValueError):
        engine._validate_zone_render_ids(_zone([bad_row]), 0)


def _run_js_payload_harness() -> dict:
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; Whole Car payload harness requires Node 18+")
    repo = Path(__file__).resolve().parent.parent
    harness = (
        repo
        / "tests"
        / "_runtime_harness"
        / "easy_whole_car_material_stack_payload.mjs"
    )
    proc = subprocess.run(
        ["node", str(harness)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            "Whole Car JS payload harness failed "
            f"(exit {proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def js_payload() -> dict:
    return _run_js_payload_harness()


def test_js_normalizer_keeps_explicit_types_and_normalizes_weights(js_payload):
    assert js_payload["normalized"] == [
        {"id": "chrome", "registry_type": "base", "weight": 0.6},
        {"id": "acid_trip", "registry_type": "monolithic", "weight": 0.4},
    ]


def test_js_payload_keeps_stack_only_zone_and_emits_material_contract(js_payload):
    assert len(js_payload["payload"]) == 1, (
        "stack-only Whole Car zone was filtered out before reaching Python"
    )
    zone = js_payload["payload"][0]
    assert zone["material_stack"] == js_payload["normalized"]
    assert zone["material_stack_mode"] == "auto_trace"
    assert zone["material_stack_amount"] == pytest.approx(0.5), (
        "the separate 50% master strength must survive the browser payload"
    )
    assert zone["material_scale"] == pytest.approx(0.5)
    assert "base" not in zone and "finish" not in zone, (
        "material-only Whole Car payload must not invent a paint-mutating base/finish"
    )


def test_js_payload_rejects_fifth_layer_and_typed_mismatch(js_payload):
    assert js_payload["over_four_error"], (
        "client silently truncated a fifth Whole Car material"
    )
    assert js_payload["typed_mismatch_error"], (
        "client accepted a base id while labeling it monolithic"
    )


def test_js_payload_keeps_quarter_and_full_master_strengths_separate(js_payload):
    assert js_payload["quarter_amount_payload"]["material_stack_amount"] == pytest.approx(0.25)
    assert js_payload["full_amount_payload"]["material_stack_amount"] == pytest.approx(1.0)


def test_js_payload_keeps_legacy_pre_master_mix_strength_compatible(js_payload):
    assert js_payload["legacy_inferred_payload"]["material_stack_amount"] == pytest.approx(0.5)
