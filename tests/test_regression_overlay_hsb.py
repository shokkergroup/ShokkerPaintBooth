# -*- coding: utf-8 -*-
"""Regression guard: 2nd-5th base overlay HSB sliders must actually move pixels.

Owner report 2026-06-12: "Overlay HSB sliders for 2nd-5th layers do nothing."
Full-chain audit proved every link healthy (JS payload -> /preview-render ->
build_multi_zone -> _apply_hsb_adjustments); the visible symptom was collateral
from the dead-live-preview bug. THIS test pins the engine half of the contract
so a real regression can never hide behind a UI bug again: a hue/brightness
shift on an overlay layer MUST change the rendered paint.
"""
import os
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SIZE = 384
MIN_DELTA = 1.0  # mean |paint diff| in 0-255 units; healthy values are 10-25


@pytest.fixture(scope="module")
def engine_env():
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY
    import shokker_engine_v2 as eng
    eng.BASE_REGISTRY = BASE_REGISTRY
    eng.PATTERN_REGISTRY = PATTERN_REGISTRY
    eng.MONOLITHIC_REGISTRY = MONOLITHIC_REGISTRY
    # NOTE: this suite's conftest patches tempfile.mkdtemp to a fixed path —
    # use an explicit harness dir instead.
    tmp = os.path.join(ROOT, "tests", "_runtime_harness", "overlay_hsb")
    os.makedirs(tmp, exist_ok=True)
    src = os.path.join(tmp, "p.png")
    Image.fromarray(np.full((SIZE, SIZE, 3), 140, dtype=np.uint8)).save(src)
    outd = os.path.join(tmp, "o")
    os.makedirs(outd, exist_ok=True)
    return eng, src, outd


def _render(eng, src, outd, extra):
    zone = {
        "name": "Z", "color": "remaining", "base": "metallic", "intensity": "100",
        "paint_color": [0.6, 0.15, 0.2], "base_color_mode": "solid",
        "base_color": [0.6, 0.15, 0.2], "base_color_strength": 0.35,
        "second_base": "mono:fm_dragon_scale", "second_base_strength": 0.8,
    }
    zone.update(extra)
    out = eng.build_multi_zone(src, outd, [zone], seed=42, preview_mode=True)
    return np.asarray(out[0], np.float32)


@pytest.mark.parametrize("field,value", [
    ("second_base_hue_shift", -105),
    ("second_base_brightness", 65),
    ("second_base_saturation", -80),
])
def test_second_overlay_hsb_moves_pixels(engine_env, field, value):
    eng, src, outd = engine_env
    base = _render(eng, src, outd, {})
    shifted = _render(eng, src, outd, {field: value})
    delta = float(np.abs(shifted - base).mean())
    assert delta > MIN_DELTA, (
        f"{field}={value} produced mean paint delta {delta:.2f} <= {MIN_DELTA} — "
        "overlay HSB is dead in the engine (check _apply_hsb_adjustments wiring "
        "in compose_paint_mod / compose_paint_mod_stacked)"
    )


@pytest.mark.parametrize("field,value", [
    ("second_base_hue_shift", -115),
    ("second_base_brightness", 45),
    ("second_base_saturation", -80),
])
def test_overlay_hsb_on_MONOLITHIC_primary_base(engine_env, field, value):
    """THE owner-reported case (2026-06-12): zones whose PRIMARY base is a
    monolithic (FM finishes etc.) take a different overlay branch in
    shokker_engine_v2 than classic bases — overlay HSB was dead there while
    the compositing path worked. Exact config from the owner's server log."""
    eng, src, outd = engine_env
    cfg = {
        "base": "fm_frost_lace",
        "second_base": "mono:singularity", "second_base_strength": 1.0,
        "second_base_color_source": "mono:pp_holographic_oil_circuit",
        "second_base_blend_mode": "tint",
    }
    base = _render(eng, src, outd, dict(cfg))
    shifted = _render(eng, src, outd, dict(cfg, **{field: value}))
    delta = float(np.abs(shifted - base).mean())
    assert delta > MIN_DELTA, (
        f"MONO-path {field}={value} produced mean paint delta {delta:.2f} <= {MIN_DELTA} — "
        "the monolithic-primary overlay branch dropped HSB again (shokker_engine_v2 "
        "'2nd base overlay: MONO' block)"
    )


@pytest.mark.parametrize("tier", ["third_base", "fourth_base", "fifth_base"])
def test_3rd_to_5th_overlays_work_on_MONOLITHIC_primary(engine_env, tier):
    """Owner 2026-06-12: 'they should work exactly the same.' 3rd-5th overlay
    tiers used to be silent no-ops on monolithic-primary zones (only the 2nd
    was implemented inline). All four tiers now run the SAME extracted
    implementation (_apply_mono_path_base_overlay)."""
    eng, src, outd = engine_env
    cfg_base = {"base": "fm_frost_lace"}
    base = _render(eng, src, outd, dict(cfg_base))
    ov = dict(cfg_base, **{
        tier: "mono:singularity", tier + "_strength": 1.0,
        tier + "_color_source": "mono:pp_holographic_oil_circuit",
        tier + "_blend_mode": "tint",
    })
    applied = _render(eng, src, outd, ov)
    delta_apply = float(np.abs(applied - base).mean())
    assert delta_apply > MIN_DELTA, (
        f"{tier} overlay on a monolithic primary moved pixels by {delta_apply:.2f} "
        f"<= {MIN_DELTA} — the tier is a no-op again on the mono path"
    )
    shifted = _render(eng, src, outd, dict(ov, **{tier + "_hue_shift": -115}))
    delta_hsb = float(np.abs(shifted - applied).mean())
    assert delta_hsb > MIN_DELTA, (
        f"{tier}_hue_shift=-115 on a monolithic primary moved pixels by {delta_hsb:.2f} <= {MIN_DELTA}"
    )


@pytest.mark.parametrize("mode", ["ghost_carve", "angle_flip"])
def test_physical_spec_blend_works_WITHOUT_pattern(engine_env, mode):
    """Owner 2026-06-12: physical spec blends 'should NOT be dependent on
    having a pattern — it should effect the ZONE as-is.' With no pattern the
    zone's own art/structure drives the blend (build_multi_zone common point)."""
    eng, src, outd = engine_env
    import numpy as _np

    def _spec(extra):
        # NOTE 2026-06-12: FM finishes now ship RAILED (soul retune, M252/B255)
        # leaving no modulation headroom — use a mid-range monolithic so the
        # blend hook itself is what's under test, not the finish's rails.
        zone = {"name": "Z", "color": "remaining", "intensity": "100", "base": "singularity"}
        zone.update(extra)
        out = eng.build_multi_zone(src, outd, [zone], seed=51, preview_mode=True)
        return _np.asarray(out[1], _np.float32)

    base = _spec({})
    blended = _spec({"base_spec_blend_mode": mode})
    delta = float(_np.abs(blended - base).mean())
    assert delta > MIN_DELTA, (
        f"pattern-less {mode} moved the spec by {delta:.2f} <= {MIN_DELTA} — "
        "the pattern-less physical blend hook in build_multi_zone is dead"
    )


def test_spec_channel_sliders_shift_channels(engine_env):
    """Owner 2026-06-12: per-zone SPEC CHANNEL SLIDERS (R=metal, G=rough,
    B=clearcoat) must shift the baked spec universally on every path."""
    eng, src, outd = engine_env
    import numpy as _np

    def _spec(extra):
        # NOTE 2026-06-12: FM finishes now ship RAILED (soul retune, M252/B255)
        # so a +60 shift has no headroom there — use a mid-range monolithic so
        # the slider hook itself is what's under test, not the finish's rails.
        zone = {"name": "Z", "color": "remaining", "intensity": "100", "base": "singularity"}
        zone.update(extra)
        out = eng.build_multi_zone(src, outd, [zone], seed=51, preview_mode=True)
        return _np.asarray(out[1], _np.float32)

    a = _spec({})
    b = _spec({"spec_channel_shift": [60, -40, 25]})
    dm = float(b[:, :, 0].mean() - a[:, :, 0].mean())
    dg = float(b[:, :, 1].mean() - a[:, :, 1].mean())
    db = float(b[:, :, 2].mean() - a[:, :, 2].mean())
    # lower bound is clip-aware: bright baselines absorb part of +60 at the
    # 255 rail — a DEAD hook reads ~0, which is what this guard must catch
    assert 25 < dm < 65, f"R(metal) shift +60 moved mean by {dm:.1f}"
    assert -45 < dg < -25, f"G(rough) shift -40 moved mean by {dg:.1f}"
    assert 5 < db < 30, f"B(coat) shift +25 moved mean by {db:.1f}"


def test_third_overlay_hsb_moves_pixels(engine_env):
    eng, src, outd = engine_env
    stack = {"third_base": "mono:pp_holographic_oil_circuit", "third_base_strength": 0.7}
    base = _render(eng, src, outd, dict(stack))
    shifted = _render(eng, src, outd, dict(stack, third_base_brightness=-70))
    delta = float(np.abs(shifted - base).mean())
    assert delta > MIN_DELTA, (
        f"third_base_brightness=-70 produced mean paint delta {delta:.2f} <= {MIN_DELTA}"
    )
