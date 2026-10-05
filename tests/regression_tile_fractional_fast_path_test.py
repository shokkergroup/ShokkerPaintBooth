# -*- coding: utf-8 -*-
"""Regression guard: the _tile_fractional fast paths must stay BIT-IDENTICAL.

[SPB-PERF 2026-08-06] _tile_fractional used to materialise np.tile(arr, (reps, reps))
-- up to 100x the source array -- and then let cv2 INTER_LINEAR read at most 2 taps per
axis out of it. It now takes one of two exact shortcuts (a pure gather when every tap
lands on an integer row/col, otherwise a separable one-axis-at-a-time tile+resize).

Both are meant to be EXACT REWRITES, not approximations. This test pins that: it keeps a
verbatim copy of the original implementation and asserts np.array_equal over a matrix of
shapes, factors and target dims -- including the awkward non-integer factors (0.15, 1/3),
targets that differ from the source, and sub-1 factors where reps clamps to 2.

If this fails, the fast path drifted from the reference and Spec Scale / Base Scale
renders are no longer pixel-for-pixel what the owner signed off on. Fix the fast path or
set SPB_TILE_FAST=0 -- do not relax the equality to a tolerance.
"""
import math
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.core import _resize_array, _tile_fractional


def _tile_fractional_reference(arr, factor, target_h, target_w):
    """Verbatim pre-2026-08-06 implementation -- the pixel contract to match."""
    h, w = arr.shape[:2]
    reps = min(10, max(2, int(math.ceil(factor))))
    tiled = np.tile(arr, (reps, reps))
    crop_h = min(tiled.shape[0], max(4, int(round(h * factor))))
    crop_w = min(tiled.shape[1], max(4, int(round(w * factor))))
    tiled = tiled[:crop_h, :crop_w]
    return _resize_array(tiled, target_h, target_w)


def _cases():
    # scale sliders the UI actually produces (factor = 1 / scale)
    for (h, w) in [(512, 512), (256, 384), (333, 257)]:
        for scale in (0.2, 0.25, 0.15, 0.5, 1.0 / 3.0, 0.1, 0.05, 0.75, 0.9, 0.6):
            yield (h, w, 1.0 / scale, h, w)
    # callers that pass a tile count straight in (compose.py ~1392)
    for factor in (2.0, 3.0, 4.0, 5.0, 6.5, 7.0, 9.0, 10.0, 12.0, 1.5):
        yield (512, 512, factor, 512, 512)
    # target dims that differ from the incoming array
    for (h, w, th, tw) in [(128, 128, 512, 512), (512, 512, 128, 128),
                           (256, 128, 512, 256), (150, 225, 256, 256),
                           (513, 255, 512, 512)]:
        for factor in (2.0, 3.0, 4.0, 5.0, 6.667, 1.25, 8.0, 10.0):
            yield (h, w, factor, th, tw)
    # degenerate / sub-1 factors -- reps clamps to 2
    for factor in (0.5, 0.9, 1.0, 1.01, 0.05):
        yield (256, 256, factor, 256, 256)
        yield (256, 256, factor, 512, 512)
    # PRODUCTION canvas. Slower, but these are the exact sizes/scales the render button
    # hits, and cv2's float32 coefficient precision degrades with the crop extent (at
    # scale 0.15 the crop is 13653 px wide) -- so 512^2 passing does not imply 2048^2 does.
    for scale in (0.2, 0.25, 0.15, 0.5, 1.0 / 3.0, 0.1):
        yield (2048, 2048, 1.0 / scale, 2048, 2048)


def test_tile_fractional_is_bit_identical_to_reference():
    assert os.environ.get("SPB_TILE_FAST", "1") != "0", (
        "run this test with the fast path ENABLED -- it exists to prove the fast path"
    )
    rng = np.random.default_rng(20260806)
    mismatches = []
    checked = 0
    for (h, w, factor, th, tw) in _cases():
        arr = rng.random((h, w), dtype=np.float32)
        ref = _tile_fractional_reference(arr, factor, th, tw)
        got = _tile_fractional(arr, factor, th, tw)
        checked += 1
        label = f"{h}x{w} factor={factor:.4g} -> {th}x{tw}"
        if got.shape != ref.shape:
            mismatches.append(f"{label}: shape {got.shape} != {ref.shape}")
        elif got.dtype != ref.dtype:
            mismatches.append(f"{label}: dtype {got.dtype} != {ref.dtype}")
        elif not np.array_equal(got, ref):
            worst = float(np.abs(got.astype(np.float64) - ref.astype(np.float64)).max())
            mismatches.append(f"{label}: max abs diff {worst:.3e}")
    assert checked >= 90, f"case matrix shrank to {checked} -- keep the coverage"
    assert not mismatches, (
        f"_tile_fractional fast path drifted from the reference in "
        f"{len(mismatches)}/{checked} cases:\n  " + "\n  ".join(mismatches[:20])
    )


def test_tile_fractional_never_aliases_its_input():
    """The result must be fresh memory -- callers stack/mutate it in place."""
    rng = np.random.default_rng(7)
    for factor in (5.0, 4.0, 6.667, 1.5):
        arr = rng.random((256, 256), dtype=np.float32)
        before = arr.copy()
        out = _tile_fractional(arr, factor, 256, 256)
        out[:] = -1.0
        assert np.array_equal(arr, before), (
            f"factor={factor}: writing to the result mutated the source array"
        )


def test_tile_fractional_decimate_path_actually_fires():
    """Guard the shortcut that carries the win -- a silent fallback is a perf regression."""
    arr = np.random.default_rng(3).random((512, 512), dtype=np.float32)
    # factor 5 (spec_scale 0.20) at target == source is the odd-integer-ratio case
    ref = _tile_fractional_reference(arr, 5.0, 512, 512)
    got = _tile_fractional(arr, 5.0, 512, 512)
    assert np.array_equal(got, ref)
    # every tap has zero fractional part, so the result is a plain gather: each output
    # pixel must appear verbatim in the source, not as a blend of neighbours.
    assert np.isin(got[::37, ::41], arr).all(), (
        "factor-5 result is not a pure decimation -- the gather fast path stopped firing"
    )


if __name__ == "__main__":
    test_tile_fractional_is_bit_identical_to_reference()
    test_tile_fractional_never_aliases_its_input()
    test_tile_fractional_decimate_path_actually_fires()
    print("OK: _tile_fractional fast paths are bit-identical to the reference")
