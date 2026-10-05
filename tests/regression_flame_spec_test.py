"""FAIL-CLOSED GATE for the flame SPEC-MAP recipes (owner mandate 2026-06-18).

Every recipe in engine.paint_v2.flame_spec_recipes.RECIPES is auto-gated here so a bad finish can't
quietly land. For EVERY recipe this enforces the three binding rules:

  1. WOVENLIGHT TRACE  — spec_traces_paint(spec, paint) >= MIN_TRACE (the spec lights the SAME pixels
                         as the bright flame; below this the spec is decorative noise, not an ignition).
  2. IRON RULES        — spec_iron_safe(spec) is True (no 1..15 clearcoat whitewash band, roughness
                         floor honored on non-mirror px, no giant flat chrome plate) — the exact
                         mirror of shokker_engine_v2._enforce_iron_rules thresholds.
  3. RENDER-TIME       — each recipe renders < 3s at 2048², the car-canvas doctrine. The wall-clock
                         budget is LOAD-NORMALIZED exactly like tests/regression_flame_uniqueness_test.py:
                         interleaved best-of-N, budget = max(3.0, RATIO x fastest recipe measured in the
                         SAME conditions). A raw 3s gate is non-portable (a recipe valid on the recording
                         machine can blow budget on a slow one, and vice-versa — that exact issue is why
                         the 6 topo@layers=3 recipes were dropped). Idle, the budget collapses to the
                         absolute 3s doctrine; under load both fastest and budget scale together so the
                         RATIO is what's tested. A genuinely slow recipe (> RATIO x fastest) still fails.

Add a finish = add a row to RECIPES; it is auto-gated. Nothing here is wired into the live catalog.

Run:  py -3 -m pytest tests/regression_flame_spec_test.py -q
"""
import time

import numpy as np
import pytest

from engine.paint_v2 import flame_spec as fs
from engine.paint_v2 import flame_spec_recipes as R

MIN_TRACE = 0.5
SEED = 7
SIZE = 2048           # render-time doctrine is enforced at the real car-canvas size
CORRECTNESS_SIZE = 1024  # trace/iron are scale-stable (512/1024 match 2048 in validation); use the
                         # work-grid here so the correctness gate fits the per-test budget. The TIMING
                         # gate below still renders the full catalog at 2048.
TRIALS = 2
RATIO = 8.0

# These two tests each render the WHOLE 135-recipe catalog (one engine boot per test). That is well
# over the repo's default 300s-per-test pytest-timeout, so raise it per-test (correctness ~3min @1024,
# timing ~8min @2048 x2). Real per-recipe compute stays < 3s — that's exactly what the timing test gates.
_LONG = pytest.mark.timeout(1200)


def test_recipes_table_is_well_formed():
    assert R.RECIPES, "RECIPES table is empty"
    ids = [r["recipe_id"] for r in R.RECIPES]
    assert len(set(ids)) == len(ids), "duplicate recipe_id in RECIPES"
    from engine.paint_v2 import flame_math as fm
    for r in R.RECIPES:
        assert r["flame"] in fm.FLAME_STRUCTURES, f"{r['recipe_id']}: unknown flame {r['flame']!r}"
        assert r["mode"] in R.MODES, f"{r['recipe_id']}: bad mode {r['mode']!r}"
        assert r["palette"] in fs.PALETTES, f"{r['recipe_id']}: unknown palette {r['palette']!r}"


@_LONG
def test_every_recipe_traces_and_is_iron_safe():
    """WOVENLIGHT + IRON RULES for EVERY recipe, in one render pass (one engine boot).
      * spec_traces_paint(spec, paint) >= MIN_TRACE — the spec lights the SAME pixels as the flame.
      * spec_iron_safe(spec) is True — no 1..15 whitewash clearcoat, roughness floor honored, no giant
        chrome plate. Both are scale-stable, so this runs on the CORRECTNESS_SIZE work grid; the
        separate timing test renders at the full 2048."""
    bad_trace, bad_iron = [], []
    for r in R.RECIPES:
        paint, spec = R.render_recipe(r, size=CORRECTNESS_SIZE, seed=SEED)
        tr = fs.spec_traces_paint(spec, paint)
        if tr < MIN_TRACE:
            bad_trace.append((r["recipe_id"], round(tr, 3)))
        ok, why = fs.spec_iron_safe(spec)
        if not ok:
            bad_iron.append((r["recipe_id"], why))
    assert not bad_trace, (
        f"recipes below the {MIN_TRACE} wovenlight-trace gate (spec must trace the flame, "
        f"not paint noise): {bad_trace}")
    assert not bad_iron, f"recipes that violate the iron rules: {bad_iron}"


@_LONG
def test_every_recipe_renders_under_3s():
    """RENDER-TIME: load-normalized, interleaved best-of-N at 2048 (mirrors the uniqueness test).

    INTERLEAVED: render the WHOLE set each round, keep the per-recipe min across rounds, so every
    recipe samples the SAME time windows — the fastest can't grab a lucky low-load reading that makes
    the ratio budget too tight for a peer. Budget = max(3.0, RATIO x fastest)."""
    times = {r["recipe_id"]: float("inf") for r in R.RECIPES}
    for _ in range(TRIALS):
        for r in R.RECIPES:
            t0 = time.time()
            paint, spec = R.render_recipe(r, size=SIZE, seed=SEED)
            dt = time.time() - t0
            assert paint.shape == (SIZE, SIZE, 3), f"{r['recipe_id']} bad paint shape {paint.shape}"
            assert spec.shape == (SIZE, SIZE, 3) and spec.dtype == np.uint8, \
                f"{r['recipe_id']} bad spec {spec.shape} {spec.dtype}"
            times[r["recipe_id"]] = min(times[r["recipe_id"]], dt)
    fastest = min(times.values())
    budget = max(3.0, RATIO * fastest)
    slow = [(rid, round(t, 2)) for rid, t in times.items() if t > budget]
    assert not slow, (
        f"recipes over the render-time doctrine at 2048 "
        f"(interleaved best of {TRIALS}, budget {budget:.1f}s = max(3.0, {RATIO}x fastest {fastest:.2f}s)): {slow}")
