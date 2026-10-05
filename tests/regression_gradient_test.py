"""MECHANICAL GATE for the gradients (owner mandate 2026-06-18) — fail-closed, like the flames.

Enforces the BINDING rules so a boring/duplicate gradient can't quietly land:
  1. UNIQUENESS  — every pair of gradient generators < MAX_GRAD_SIMILARITY (colour-AWARE fingerprint).
  2. NOT BORING  — every gradient has >= MIN_GRAD_STRUCTURE non-planar structure (warp/bands/mesh/grain);
                   a plain straight linear ramp scores ~0 and FAILS (owner: "ours, not boring").
  3. RENDER-TIME — each renders < 3s at 2048 (interleaved best-of-N, load-normalized budget — same as
                   tests/regression_flame_uniqueness_test.py, so a busy machine can't flake it).
Add new generators to gradient_math.GRADIENT_STRUCTURES; they auto-gate.

Run:  py -3 -m pytest tests/regression_gradient_test.py -q
"""
import itertools
import time

import numpy as np

from engine.paint_v2.gradient_math import (
    GRADIENT_STRUCTURES, gradient_similarity, gradient_structure,
    MAX_GRAD_SIMILARITY, MIN_GRAD_STRUCTURE,
)


def test_gradients_are_distinct():
    S = 256
    imgs = {n: np.asarray(fn((S, S), 7)) for n, fn in GRADIENT_STRUCTURES.items()}
    too_similar = []
    for a, b in itertools.combinations(sorted(imgs), 2):
        s = gradient_similarity(imgs[a], imgs[b])
        if s > MAX_GRAD_SIMILARITY:
            too_similar.append((a, b, round(s, 3)))
    assert not too_similar, (
        f"gradients exceed the {MAX_GRAD_SIMILARITY} uniqueness gate (redesign, don't recolour): {too_similar}")


def test_gradients_are_not_boring():
    S = 256
    flat = []
    for n, fn in GRADIENT_STRUCTURES.items():
        st = gradient_structure(np.asarray(fn((S, S), 7)))
        if st < MIN_GRAD_STRUCTURE:
            flat.append((n, round(st, 3)))
    assert not flat, (
        f"gradients below the {MIN_GRAD_STRUCTURE} anti-boring floor (too close to a flat linear ramp — "
        f"add warp/bands/mesh/grain): {flat}")


def test_gradients_render_under_3s():
    # interleaved best-of-N, load-normalized budget (same as the flame gate) — robust to a busy box.
    S = 2048
    TRIALS = 3
    RATIO = 8.0
    times = {n: float("inf") for n in GRADIENT_STRUCTURES}
    for _ in range(TRIALS):
        for n, fn in GRADIENT_STRUCTURES.items():
            t0 = time.time()
            out = np.asarray(fn((S, S), 7))
            dt = time.time() - t0
            assert out.shape == (S, S, 3), f"{n} bad shape {out.shape}"
            times[n] = min(times[n], dt)
    fastest = min(times.values())
    budget = max(3.0, RATIO * fastest)
    slow = [(n, round(t, 2)) for n, t in times.items() if t > budget]
    assert not slow, (
        f"gradients over the render-time doctrine at 2048 "
        f"(interleaved best of {TRIALS}, budget {budget:.1f}s): {slow}")
