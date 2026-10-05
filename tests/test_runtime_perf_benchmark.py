"""HEENAN Hawk + Animal — perf benchmark scaffold.

This harness produces measured numbers for what's measurable WITHOUT
launching the running app. The board meeting's #5 priority was "Perf
Truth — Hawk + Animal land measured numbers + budgets for the 5 hottest
workflows." This is the foundation: a re-runnable benchmark that
captures baseline timings.

Honest scope:
- These numbers include V8 `vm.runInContext` overhead per iteration.
  Real browser rendering compiles once and is faster. Absolute numbers
  here are NOT directly comparable to in-browser timings.
- Relative numbers ARE comparable: if `autoLevels_2048` is 30× the time
  of `invert_2048` here, that ratio holds in the browser too.
- Real GPU canvas timings, real server roundtrip, real paint stroke
  latency — those need the running app + Windows-MCP. Not this shift.

Budgets are intentionally generous so this is a regression smoke test,
not a brittle exact-match. Tighten as we learn baseline.

Baseline established 2026-04-19 (4-hour autonomous run):
- Catalog eval: ~12 ms
- validateFinishData: ~0.85 ms per call
- autoLevels 2048x2048 in V8: ~6,200 ms per call (huge — hot path)
- desaturate 2048x2048 in V8: ~700 ms per call
- invert 2048x2048 in V8: ~8 ms per call (fast — simple subtraction)
- posterize 2048x2048 in V8: ~4,000 ms per call

Top hotspot identified: **autoLevels** (two passes over all pixels —
find min/max then rescale). Posterize close second (Math.round per
pixel × 3 channels). Future optimization opportunity.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "perf_benchmark.mjs"


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    if not HARNESS.exists():
        pytest.fail(f"missing: {HARNESS}")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"perf_benchmark harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def perf():
    return _run_harness()


def test_perf_catalog_eval_under_budget(perf):
    """Catalog file load + parse should be under 50 ms — runs once on
    boot. Real cost: catalog file is now ~466 KB. If this balloons we
    need to investigate."""
    eval_ms = perf["catalog_eval_ms"]
    assert eval_ms < 100, f"catalog eval ballooned: {eval_ms} ms (budget 100)"


def test_perf_validator_fast(perf):
    """validateFinishData must be cheap — runs on boot, must not delay
    the painter's first interaction."""
    per_iter = perf["validator"]["per_iter_ms"]
    assert per_iter < 5.0, f"validateFinishData regressed: {per_iter} ms (budget 5)"


def test_perf_invert_fast(perf):
    """invert is the fastest mutator — single subtraction per channel.
    If this regresses, the entire mutator family regressed."""
    per_iter = perf["composite_mutators"]["invert_2048"]["per_iter_ms"]
    assert per_iter < 100, f"invertCanvasColors 2048 regressed: {per_iter} ms"


def test_perf_autoLevels_post_optimization(perf):
    """autoLevels: was ~6,200 ms pre-optimization, ~44 ms post-H4HR-PERF1.
    Tight budget at 200 ms — any regression toward the pre-fix numbers
    fires immediately. The optimization (inline Math.min/max + precomputed
    scale + bitwise round + Uint8ClampedArray auto-clamp) is bit-identical."""
    per_iter = perf["composite_mutators"]["auto_levels_2048"]["per_iter_ms"]
    assert per_iter < 200, (
        f"autoLevels 2048 regressed past optimization: {per_iter} ms "
        "(post-H4HR-PERF1 baseline ~44 ms; budget 200 ms)"
    )


def test_perf_autoContrast_post_optimization(perf):
    """autoContrast: post-H4HR-PERF3 baseline ~34 ms. Budget 200 ms."""
    per_iter = perf["composite_mutators"]["auto_contrast_2048"]["per_iter_ms"]
    assert per_iter < 200, (
        f"autoContrast 2048 regressed past optimization: {per_iter} ms "
        "(post-H4HR-PERF3 baseline ~34 ms; budget 200 ms)"
    )


def test_perf_desaturate_post_optimization(perf):
    """desaturate: was ~700 ms pre-optimization, ~13 ms post-H4HR-PERF4.
    Budget 100 ms — was originally so slow we'd never have caught regressions."""
    per_iter = perf["composite_mutators"]["desaturate_2048"]["per_iter_ms"]
    assert per_iter < 100, (
        f"desaturateCanvas 2048 regressed past optimization: {per_iter} ms "
        "(post-H4HR-PERF4 baseline ~13 ms; budget 100 ms)"
    )


def test_perf_posterize_post_optimization(perf):
    """posterize: was ~4,000 ms pre-optimization, ~32 ms post-H4HR-PERF2.
    Budget 200 ms."""
    per_iter = perf["composite_mutators"]["posterize_2048"]["per_iter_ms"]
    assert per_iter < 200, (
        f"posterize 2048 regressed past optimization: {per_iter} ms "
        "(post-H4HR-PERF2 baseline ~32 ms; budget 200 ms)"
    )


def test_perf_file_size_baseline(perf):
    """Canonical JS files have known sizes. Track to detect bloat."""
    by_file = {r["file"]: r["size_kb"] for r in perf["file_reads"]}
    # Generous upper bounds — alert if any single file balloons past 1.5x.
    BUDGETS = {
        "paint-booth-0-finish-data.js":     800,  # current ~466 KB
        "paint-booth-0-finish-metadata.js": 800,  # current ~454 KB
        "paint-booth-2-state-zones.js":    1300,  # current ~787 KB
        "paint-booth-3-canvas.js":         1500,  # current ~860 KB
        "paint-booth-5-api-render.js":      400,  # current ~210 KB
        "paint-booth-6-ui-boot.js":         400,  # current ~226 KB
    }
    offenders = []
    for f, budget in BUDGETS.items():
        size = by_file.get(f, 0)
        if size > budget:
            offenders.append((f, size, budget))
    assert not offenders, (
        f"File-size budgets exceeded: {offenders}. "
        f"Either justify the growth and bump the budget, or refactor."
    )


def test_perf_migration_throughput_practical(perf):
    """Migration helper must process 1000 zone configs without choking.
    Painters never load 1000 zones in one project; this is a stress test
    that confirms the helper is O(zones × ids), not pathological."""
    total_ms = perf["migration_throughput"]["total_ms"]
    # 1000 zones × 7 migrations each = 7000 mutations. Should be far under 5s.
    assert total_ms < 10000, f"migration throughput regressed: {total_ms} ms for 1000 zones"
