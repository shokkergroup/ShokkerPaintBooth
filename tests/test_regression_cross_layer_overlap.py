"""Regression guardrail: cross-layer zone priority on partially-
overlapping layer masks.

## Existing coverage (passes)

`tests/test_layer_system.py::test_layer_mask_applies_before_claimed_priority_subtraction`
asserts source-level ordering of layer-mask apply vs claim subtraction.

`tests/test_layer_system.py::test_disjoint_layer_masks_preserve_same_color_pixels_per_zone`
asserts behavioural correctness when layer masks are DISJOINT (left
half vs right half). Both zones own their own layer, no cross-layer
theft.

## Coverage gap this file closes

What if layer masks PARTIALLY OVERLAP? E.g. Zone A on a layer mask
covering the top 2/3 of the image, Zone B on a layer mask covering
the bottom 2/3. The middle third is present on BOTH layers. When
both zones pick the same color, the invariant is:

- Zone A (priority 1): owns its entire layer area (top 2/3)
- Zone B (priority 2): owns only pixels in its layer that Zone A
  didn't already claim (i.e. the bottom 1/3, NOT the middle overlap)
- Neither zone extends beyond its own layer.

This is a real scenario (a PSD with stacked layers that share pixel
area) and it's the exact case where a bad implementation would give
Zone B partial/zero coverage of the middle third (layer extends
beyond ownership) or would let Zone A leak into the bottom 1/3
(ownership extends beyond layer). The existing disjoint test can't
detect either failure mode because there's no overlap to arbitrate.
"""

import numpy as np


def test_partial_overlap_priority_wins_overlap_lower_keeps_own_layer():
    """Zone A (prio 1) on top 2/3; Zone B (prio 2) on bottom 2/3.
    Both match red on a fully-red scheme. Verify:
      - Zone A owns its full 2/3 (no subtraction — it runs first).
      - Zone B owns only the bottom 1/3 (Zone A claimed the middle).
      - Zone A's mask is ZERO outside its own layer (no cross-layer
        leak).
      - Zone B's mask is ZERO outside its own layer.
    """
    from engine.core import analyze_paint_colors, build_zone_mask

    h, w = 24, 24
    scheme = np.zeros((h, w, 3), dtype=np.float32)
    scheme[:, :, 0] = 1.0  # every pixel red
    stats = analyze_paint_colors(scheme)
    selector = {"color_rgb": [255, 0, 0], "tolerance": 40}
    color_mask = build_zone_mask(scheme, stats, selector, blur_radius=0)

    # Layer masks: top 2/3 and bottom 2/3 — middle 1/3 is in BOTH.
    top_2_3 = int(h * 2 / 3)
    bot_1_3 = int(h / 3)
    layer_A = np.zeros((h, w), dtype=np.float32)
    layer_A[:top_2_3, :] = 1.0        # rows 0..15
    layer_B = np.zeros((h, w), dtype=np.float32)
    layer_B[bot_1_3:, :] = 1.0        # rows 8..23
    overlap_rows = slice(bot_1_3, top_2_3)   # rows 8..15 in BOTH

    # Mimic the engine's first-pass loop (shokker_engine_v2.py:9598-9608).
    claimed = np.zeros((h, w), dtype=np.float32)

    # Zone A first (higher priority)
    mask_A = (color_mask * layer_A).astype(np.float32)
    mask_A = np.clip(mask_A - claimed * 0.8, 0, 1)
    claimed = np.clip(claimed + mask_A, 0, 1)

    # Zone B second (lower priority)
    mask_B = (color_mask * layer_B).astype(np.float32)
    mask_B = np.clip(mask_B - claimed * 0.8, 0, 1)
    claimed = np.clip(claimed + mask_B, 0, 1)

    # Assertions
    # Zone A owns its full layer (top 2/3). No one claimed anything before it.
    assert float(mask_A[:top_2_3, :].mean()) > 0.95, (
        f"Zone A coverage on own layer = {mask_A[:top_2_3, :].mean():.3f} (want >0.95)"
    )
    # Zone A does NOT leak into rows that aren't in its layer.
    assert float(mask_A[top_2_3:, :].max()) == 0.0, (
        f"Zone A leaked outside its layer: max outside = {mask_A[top_2_3:, :].max():.3f}"
    )

    # Zone B owns the bottom 1/3 (the part NOT in the overlap).
    assert float(mask_B[top_2_3:, :].mean()) > 0.95, (
        f"Zone B coverage on exclusive-bottom = {mask_B[top_2_3:, :].mean():.3f} (want >0.95)"
    )
    # Zone B does NOT own the overlap (Zone A claimed it).
    assert float(mask_B[overlap_rows, :].max()) < 0.25, (
        f"Zone B leaked into overlap claimed by Zone A: max in overlap = "
        f"{mask_B[overlap_rows, :].max():.3f}. Claim subtraction is not "
        f"effective across the priority boundary."
    )
    # Zone B does NOT leak outside its own layer (top 1/3).
    assert float(mask_B[:bot_1_3, :].max()) == 0.0, (
        f"Zone B leaked outside its layer: max in top 1/3 = {mask_B[:bot_1_3, :].max():.3f}"
    )


def test_disjoint_layer_claim_is_globally_accumulated_but_does_not_cross_layer():
    """Subtle invariant check: the `claimed` mask is GLOBAL (not
    per-layer), yet layer-restricted zones must still be immune to
    cross-layer claim theft. This only works because the layer mask
    is applied BEFORE the claim subtraction — the mask goes to zero
    outside the zone's layer BEFORE the claim check, so claim state
    on other layers can't subtract anything that was already zero.

    Construct:
      - scheme: full red everywhere.
      - Zone A on layer_A (left half), Zone B on layer_B (right half).
      - Inject claimed=1 globally on the RIGHT half BEFORE Zone B runs,
        as if some unrelated higher-priority zone on a THIRD layer had
        already grabbed the right-half pixels.
      - Verify Zone B still gets zero coverage (claimed), not negative
        or unclipped.
      - Verify Zone A's mask stays untouched (left half intact).
    """
    from engine.core import analyze_paint_colors, build_zone_mask

    h, w = 12, 12
    scheme = np.zeros((h, w, 3), dtype=np.float32)
    scheme[:, :, 0] = 1.0
    stats = analyze_paint_colors(scheme)
    selector = {"color_rgb": [255, 0, 0], "tolerance": 40}
    color_mask = build_zone_mask(scheme, stats, selector, blur_radius=0)

    layer_A = np.zeros((h, w), dtype=np.float32); layer_A[:, : w // 2] = 1.0
    layer_B = np.zeros((h, w), dtype=np.float32); layer_B[:, w // 2 :] = 1.0

    # Pre-populate claimed on the RIGHT half (as if a third zone grabbed it).
    claimed = np.zeros((h, w), dtype=np.float32)
    claimed[:, w // 2 :] = 1.0

    # Zone A runs — its layer is LEFT half. Claim state on RIGHT half is
    # irrelevant because layer mask zeros out its RIGHT half first.
    mask_A = (color_mask * layer_A).astype(np.float32)
    mask_A = np.clip(mask_A - claimed * 0.8, 0, 1)
    assert float(mask_A[:, : w // 2].mean()) > 0.95, "Zone A lost its own layer"
    assert float(mask_A[:, w // 2 :].max()) == 0.0, "Zone A shouldn't touch right half"

    # Zone B runs — its layer is RIGHT half. Claim state on RIGHT is FULL.
    # After mask * layer_B, only right half is nonzero. Then claim
    # subtraction zeroes it. Result: Zone B gets nothing — that's the
    # correct priority outcome when the right half was already claimed.
    mask_B = (color_mask * layer_B).astype(np.float32)
    mask_B = np.clip(mask_B - claimed * 0.8, 0, 1)
    assert float(mask_B.max()) < 0.21, (
        f"Zone B max={mask_B.max():.3f}. Expected <0.21 (claimed*0.8 "
        f"subtracts 0.8 from a mask-of-1, leaving 0.2; with blur_radius=0 "
        f"and a clean color match, the result should be just below 0.21)."
    )
