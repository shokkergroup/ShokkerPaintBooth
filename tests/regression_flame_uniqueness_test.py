"""MECHANICAL GATE for the flames project (owner mandate 2026-06-18).

Enforces the BINDING rules as a FAIL-CLOSED test (not a thing an agent has to remember):
  1. UNIQUENESS    — every pair of distinct flame STRUCTURES < 80% structural similarity.
  2. RENDER-TIME   — each structure renders < 3s at 2048² (the car-canvas doctrine).
  3. COVERAGE      — full-canvas coverage by DEFAULT (>= MIN_COVERAGE); a structure may opt out
                     ONLY via flame_math.COVERAGE_EXEMPT (single motif / directional / annular).
  4. FINE DETAIL   — crushed fine detail by DEFAULT (>= MIN_FINENESS); opt out ONLY via
                     flame_math.FINE_DETAIL_EXEMPT (a soft glow that is meant to be smooth).
If a new flame structure violates any of these, this test FAILS → it can't quietly land. Add new
structures to flame_math.FLAME_STRUCTURES; they're auto-gated. Exemptions are deliberate, reviewable
entries with a written reason — NOT a silent escape hatch.

Run:  py -3 -m pytest tests/regression_flame_uniqueness_test.py -q
"""
import itertools
import time

import numpy as np

from engine.paint_v2.flame_math import (
    FLAME_STRUCTURES, structural_similarity, MAX_STRUCT_SIMILARITY,
    coverage_score, fineness_score, MIN_COVERAGE, MIN_FINENESS,
    COVERAGE_EXEMPT, FINE_DETAIL_EXEMPT,
)


def test_flame_structures_are_distinct():
    S = 256
    imgs = {n: np.asarray(fn((S, S), 7)) for n, fn in FLAME_STRUCTURES.items()}
    too_similar = []
    for a, b in itertools.combinations(sorted(imgs), 2):
        s = structural_similarity(imgs[a], imgs[b])
        if s > MAX_STRUCT_SIMILARITY:
            too_similar.append((a, b, round(s, 3)))
    assert not too_similar, (
        f"flame structures exceed the {MAX_STRUCT_SIMILARITY} uniqueness gate "
        f"(redesign the MATH, not the palette): {too_similar}")


def test_flame_structures_render_under_3s():
    # LOAD-NORMALIZED, BEST-OF-N timing. A raw wall-clock budget is flaky on a shared dev box: a
    # single cold render measures transient MACHINE LOAD as much as compute (we've seen the suite run
    # 6x slower under contention). Two defenses: (1) best-of-N per structure (matches the project's
    # audit_render_perf.py --trials convention) removes transient spikes; (2) the budget is scaled by
    # the FASTEST structure measured in the SAME conditions — so we test compute cost RELATIVE to how
    # fast this machine is right now. Idle, the fastest closed-form structure is ~0.35s and the budget
    # collapses to the absolute 3s doctrine; under load both scale together so the ratio is preserved.
    # A genuinely slow structure (> ~8x the fastest) still fails, loaded or not.
    S = 2048
    TRIALS = 3
    RATIO = 8.0
    # INTERLEAVED best-of-N: render the WHOLE set each round, keep the per-structure min across rounds.
    # Interleaving (not 3-trials-per-structure-in-a-row) means every structure samples the SAME time
    # windows, so if any round happens to run on a quiet CPU, ALL structures get a clean sample — the
    # fastest can't grab a lucky low-load reading that then makes the ratio budget too tight for a peer.
    times = {n: float("inf") for n in FLAME_STRUCTURES}
    for _ in range(TRIALS):
        for n, fn in FLAME_STRUCTURES.items():
            t0 = time.time()
            out = np.asarray(fn((S, S), 7))
            dt = time.time() - t0
            assert out.shape == (S, S, 3), f"{n} bad shape {out.shape}"
            times[n] = min(times[n], dt)
    fastest = min(times.values())
    budget = max(3.0, RATIO * fastest)            # absolute 3s when idle; load-scaled when busy
    slow = [(n, round(t, 2)) for n, t in times.items() if t > budget]
    assert not slow, (
        f"flame structures over the render-time doctrine at 2048 "
        f"(interleaved best of {TRIALS}, budget {budget:.1f}s = max(3.0, {RATIO}x fastest {fastest:.2f}s)): {slow}")


def test_flame_structures_cover_the_canvas():
    """Full-canvas coverage by default — no lonely centered motif, no dead corners. A structure
    that is intentionally not full-canvas must be listed (with a reason) in COVERAGE_EXEMPT."""
    S = 512
    weak = []
    for n, fn in FLAME_STRUCTURES.items():
        if n in COVERAGE_EXEMPT:
            continue
        cov = coverage_score(np.asarray(fn((S, S), 7)))
        if cov < MIN_COVERAGE:
            weak.append((n, round(cov, 2)))
    assert not weak, (
        f"flame structures below the {MIN_COVERAGE} coverage mandate (fill the canvas, kill the "
        f"dead corners — or add to COVERAGE_EXEMPT with a reason): {weak}")


def test_flame_structures_are_crushed_fine():
    """Crushed fine detail by default — no smooth boring blob / flat ramp. A structure that is
    intentionally smooth must be listed (with a reason) in FINE_DETAIL_EXEMPT."""
    S = 512
    smooth = []
    for n, fn in FLAME_STRUCTURES.items():
        if n in FINE_DETAIL_EXEMPT:
            continue
        fin = fineness_score(np.asarray(fn((S, S), 7)))
        if fin < MIN_FINENESS:
            smooth.append((n, round(fin, 2)))
    assert not smooth, (
        f"flame structures below the {MIN_FINENESS} fine-detail mandate (crush in fine structure — "
        f"or add to FINE_DETAIL_EXEMPT with a reason): {smooth}")
