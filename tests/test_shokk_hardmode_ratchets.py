"""HEENAN HARDMODE-GUARDRAIL-SHOKK — behavioral ratchets for headline claims.

The HARDMODE report claimed two things about SHOKK behavior that the code
did not actually implement:

  1. shokk_void: "rare 0.3% shimmer at strongest Perlin-edge crests" — the
     actual threshold marked ~55-58% of pixels as shimmer.
  2. shokk_dual: "Hard Chromatic Binary Flip" — the actual code was a
     continuous gradient producing 1200+ distinct rounded M values.

Both are now fixed. These ratchets make sure they STAY fixed: if a future
shift re-introduces a gradient where a binary flip should be, or lets
shimmer coverage drift above 1%, the tests fail.

Run: python -m pytest tests/test_shokk_hardmode_ratchets.py -v
"""

import numpy as np
import pytest

from engine.shokk_series import (
    spec_shokk_void,
    spec_shokk_dual,
    _void_shimmer_mask,
    _shokk_dual_binary_field,
)


# ─── shokk_void: 0.3% shimmer ratchet ──────────────────────────────────────

@pytest.mark.parametrize("seed", [1, 2, 3, 10, 42, 99])
@pytest.mark.parametrize("shape", [(256, 256), (512, 512), (1024, 1024)])
def test_shokk_void_shimmer_coverage_is_rare(seed, shape):
    """shokk_void shimmer must cover < 1% of pixels (target 0.3%).

    Regression: the original implementation used a fixed 0.85 threshold on
    a clipped gradient and marked 55-58% of pixels as shimmer, turning
    "rare edge shimmer" into a majority-coverage effect.
    """
    mask = _void_shimmer_mask(shape, seed)
    coverage = float(mask.mean())
    assert coverage < 0.01, (
        f"shokk_void shimmer coverage = {coverage*100:.2f}% at seed={seed}, "
        f"shape={shape}. Must stay below 1%. Target is 0.3%."
    )
    # And it must not be zero either — that would hide the effect entirely.
    assert coverage > 0.001, (
        f"shokk_void shimmer coverage = {coverage*100:.4f}% — too sparse; "
        f"painter won't see any glints."
    )


def test_shokk_void_spec_output_has_dark_majority():
    """The spec map should be overwhelmingly low-M (void absorption) with
    only rare high-M glints, across every tested shape/seed."""
    for seed in (1, 42, 99):
        for shape in ((256, 256), (512, 512)):
            M, R, CC = spec_shokk_void(shape, seed, 1.0, 0, 240)
            dark_frac = float((M < 10).mean())
            bright_frac = float((M > 200).mean())
            assert dark_frac > 0.98, (
                f"shokk_void dark coverage = {dark_frac*100:.2f}% — "
                f"expected >98% low-M (void)."
            )
            assert bright_frac < 0.01, (
                f"shokk_void bright coverage = {bright_frac*100:.2f}% — "
                f"expected <1% high-M shimmer glints."
            )


# ─── shokk_dual: actual binary flip ratchet ────────────────────────────────

@pytest.mark.parametrize("seed", [1, 42, 99])
@pytest.mark.parametrize("shape", [(256, 256), (512, 512)])
def test_shokk_dual_flip_is_binary_not_gradient(seed, shape):
    """shokk_dual must be a hard binary flip — the midzone between the two
    M values must stay below 5% of pixels. A continuous gradient would
    have ~100% of pixels in the midzone.

    Regression: the pre-fix implementation computed
        M = 80 + h_param * 175
    on a continuous h_param in [0,1], producing a smooth gradient with
    1200+ distinct rounded M values and no clear "side A" vs "side B".
    """
    M, _R, _CC = spec_shokk_dual(shape, seed, 1.0, 200, 30)
    # M should live near 255 (side A) or near 80 (side B); only a thin
    # seam (~2-3% of pixels) lives in between.
    side_a = float((M > 240).mean())
    side_b = float((M < 100).mean())
    midzone = float(((M >= 100) & (M <= 240)).mean())
    assert midzone < 0.05, (
        f"shokk_dual midzone = {midzone*100:.2f}% at seed={seed}, shape={shape}. "
        f"A hard binary flip should have <5% mid-transition pixels, not a "
        f"continuous gradient (side_a={side_a*100:.1f}%, side_b={side_b*100:.1f}%)."
    )
    assert side_a > 0.10 and side_b > 0.10, (
        f"shokk_dual is degenerate at seed={seed}, shape={shape}: side A = "
        f"{side_a*100:.1f}%, side B = {side_b*100:.1f}%. Both sides should "
        f"be present."
    )


def test_shokk_dual_binary_field_is_mostly_01():
    """_shokk_dual_binary_field must return values that are near-0 or
    near-1 for the vast majority of pixels (smoothstep seam only)."""
    flip = _shokk_dual_binary_field((512, 512), 42)
    crisp = float(((flip < 0.05) | (flip > 0.95)).mean())
    assert crisp > 0.97, (
        f"_shokk_dual_binary_field crispness = {crisp*100:.2f}%; "
        f"expected >97% of pixels to be near 0 or 1 with a narrow seam."
    )
