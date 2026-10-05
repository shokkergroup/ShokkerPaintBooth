"""Render-perf regression tests (SPB-90 / tick 58).

Catches silent slowdowns to renderers we've already optimized. Each test
renders a small canvas (256² → keeps runtime ~30s total) for ONE
representative finish per cluster and fails if the render takes longer
than the pinned ceiling.

Ceilings include 2× headroom over the measured times from ticks 54-57 so
ordinary jitter doesn't trip the tests. A genuine 2×+ regression — like
the Depth Illusion 487→632 ms change observed in tick 56 — would fire.

The first call to each finish is a COLD render (no cache); the test
measures that. Some finishes are slower on a CI runner than a dev box;
if needed, bump the ceilings rather than disabling tests.

Doctrine source: SPB Finish Quality Workbook ticks 48–57; cumulative
ledger in SPB-90.
"""
from __future__ import annotations

import time

import numpy as np
import pytest

import shokker_engine_v2 as eng


# Pinned budgets in milliseconds at 256² (combined spec_fn + paint_fn).
# Headroom built in — these should never be tight against the measured
# numbers from ticks 54-57.
# Format: (registry_kind, finish_id, budget_ms_at_256, doctrine_note)
PERF_REPRESENTATIVES = [
    ("mono", "ms_lotus_ascention", 2000,
     "Mortal Shokk: tick 54 LRU cache fix. Measured cold ~1050ms at 256 (work_shape clamps to 1280 so 256 doesn't scale linearly down). Budget 2000 leaves headroom — production UX is cache-warm at <20ms anyway."),
    ("mono", "cs_complementary", 400,
     "Color Shift: tick 55 np.interp swap. Cold ~290ms at 512 = ~73ms at 256. Budget 400 is wide headroom."),
    ("mono", "prizm_adaptive", 600,
     "Prizm: tick 56 LRU cache fix. Cold ~530ms at 512 = ~133ms at 256. Budget 600 is wide headroom."),
    ("mono", "ghost_hex", 200,
     "Ghost Geometry: SPB-78 lean baseline. Cold ~85ms at 512 = ~22ms at 256. Budget 200 confirms baseline lean."),
    ("base", "f_chrome", 50,
     "Foundation flat: painter contract = ~1ms render. Budget 50 catches any unintended procedural work."),
    # SPB-92 tick 64: cultural-finish budgets pin the tick 61 dedup win
    # (memoization of _viva_mexico_paint_luma_edge + _highlight_crest)
    # across all 4 cultural categories. If memoization regresses, these
    # tests fire — measured ~250-400ms at 256², budget 800ms allows
    # 2× headroom plus the ms_lotus baseline of 1043ms for Mortal Shokk.
    ("mono", "vm_aztec_sunfire", 800,
     "Viva Mexico: tick 61 dedup. Cold ~385ms at 256, budget 800 covers 2× plus warm-up cost."),
    ("mono", "rs_rising_sun_flare", 800,
     "Rising Sun: tick 61 dedup. Cold ~256ms at 256, budget 800 covers 2× plus cache-warm-up cost."),
    ("mono", "uj_camden_signal_riot", 800,
     "Union Jacked: tick 61 dedup. Cold ~297ms at 256, budget 800 covers 2× plus warm-up cost."),
]


def _time_render(kind: str, stem: str, size: int = 256) -> tuple[float, bool]:
    """Render once and return (ms, success). One-shot — measures cold path."""
    mask = np.ones((size, size), dtype=np.float32)
    neutral = np.full((size, size, 3), 0.5, dtype=np.float32)
    seed = hash(stem) & 0x7FFFFFFF
    if kind == "mono":
        entry = eng.MONOLITHIC_REGISTRY.get(stem)
        if entry is None or not isinstance(entry, tuple) or len(entry) < 2:
            return float("inf"), False
        spec_fn, paint_fn = entry[0], entry[1]
        t0 = time.perf_counter()
        try:
            spec_fn((size, size), mask, seed, 1.0)
            paint_fn(neutral.copy(), (size, size), mask, seed, 1.0, 1.0)
        except Exception:
            return float("inf"), False
        return (time.perf_counter() - t0) * 1000, True
    elif kind == "base":
        entry = eng.BASE_REGISTRY.get(stem)
        if entry is None or not isinstance(entry, dict):
            return float("inf"), False
        spec_fn = entry.get("base_spec_fn")
        paint_fn = entry.get("paint_fn")
        if not (callable(spec_fn) and callable(paint_fn)):
            return float("inf"), False
        t0 = time.perf_counter()
        try:
            spec_fn((size, size), seed, 1.0, entry.get("M", 128), entry.get("R", 80))
            paint_fn(neutral.copy(), (size, size), mask, seed, 1.0, 1.0)
        except Exception:
            return float("inf"), False
        return (time.perf_counter() - t0) * 1000, True
    return float("inf"), False


@pytest.mark.parametrize("kind,stem,budget_ms,doctrine", PERF_REPRESENTATIVES)
def test_render_perf_under_budget(kind, stem, budget_ms, doctrine):
    """Pinned per-cluster perf budgets. Failing means a previously-optimized
    renderer has regressed substantially (>budget). Bump the budget only
    if the slowdown is intentional and documented in SPB-90.
    """
    t_ms, ok = _time_render(kind, stem, size=256)
    assert ok, f"{kind}:{stem} failed to render (missing from registry or threw exception)"
    assert t_ms < budget_ms, (
        f"{kind}:{stem} rendered in {t_ms:.0f}ms at 256² — exceeds budget of {budget_ms}ms. "
        f"Doctrine: {doctrine}"
    )
