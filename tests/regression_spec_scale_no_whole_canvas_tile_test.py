# -*- coding: utf-8 -*-
"""Regression guard: the INDEPENDENT Spec Scale post-pass (spec_scale != base_scale,
the 🔓 Spec Scale slider) at scale < 1 must tile ONLY the zone's own spec material,
never the whole zone-shaped spec plate.

Owner report 2026-07-05: "when I SPEC SCALE down below 1.00 that friggin whole
canvas scale bug happens... This bug KEEPS coming up." The paint side got the
TRUE root-cause cure on 2026-06-17 (_apply_base_transform_to_zone_paint_only:
strong-in-zone tiling source, mean-fill soft edges, composite through the soft
mask); the spec post-pass (_transform_spec_for_base_controls) kept handing the
FINISHED zone-shaped plate to the global placement transform — hall of mirrors
on M/R/CC. If this test fails, someone re-widened the spec post-pass back into
whole-plate tiling. Tile the ZONE MATERIAL, not the PLATE.
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import shokker_engine_v2 as eng


def _scene():
    """Zone spec plate: neutral outside, striped material inside a soft-edged zone,
    plus a unique FOREIGN spec marker outside the zone (another zone's chrome blob)."""
    H = W = 128
    spec = np.zeros((H, W, 4), dtype=np.uint8)
    spec[:, :, 0] = 32    # neutral M outside
    spec[:, :, 1] = 128   # neutral R
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255

    # Soft-edged zone: box in the bottom-right quadrant with a 4px soft rim.
    mask = np.zeros((H, W), dtype=np.float32)
    mask[72:120, 72:120] = 1.0
    try:
        import cv2
        mask = cv2.GaussianBlur(mask, (9, 9), 2.0)
    except Exception:
        pass

    # Zone material: fine M stripes inside the zone (what Spec Scale should refine).
    stripe_rows = ((np.arange(H)[:, None] // 4) % 2 == 0)
    stripe_full = np.where(np.broadcast_to(stripe_rows, (H, W)), 200.0, 90.0)
    in_zone = mask > 0.5
    m = spec[:, :, 0].astype(np.float32)
    m = np.where(in_zone, stripe_full, m)
    spec[:, :, 0] = m.astype(np.uint8)

    # FOREIGN marker: chrome blob far outside the zone (top-left).
    spec[8:24, 8:24, 0] = 255
    spec[8:24, 8:24, 1] = 2
    return spec, mask, (H, W)


def _run(spec, mask, shape, scale):
    out = eng._transform_spec_for_base_controls(
        spec.copy(), shape, scale, 0.5, 0.5, 0.0, False, False, zone_mask=mask)
    return np.asarray(out)


def test_spec_scale_down_outside_zone_untouched():
    spec, mask, shape = _scene()
    out = _run(spec, mask, shape, 0.5)
    outside = mask <= 0.001
    diff = float(np.max(np.abs(out[outside][:, :3] - spec[outside][:, :3].astype(np.float32))))
    assert diff <= 1.0, (
        f"spec_scale<1 modified the plate OUTSIDE the zone (max delta {diff}); "
        f"the post-pass tiled the whole canvas again")


def test_spec_scale_down_does_not_import_foreign_spec():
    spec, mask, shape = _scene()
    out = _run(spec, mask, shape, 0.5)
    in_zone = mask > 0.5
    # The foreign chrome marker is M=255/R=2. In-zone material tops out at M=200,
    # and the mean-fill can only produce values inside [90, 200]. Any near-chrome
    # pixel inside the zone means the whole plate (incl. the marker) was tiled in.
    m_in = out[:, :, 0][in_zone]
    r_in = out[:, :, 1][in_zone]
    foreign = int(np.sum((m_in > 240) & (r_in < 20)))
    assert foreign == 0, (
        f"{foreign} chrome-marker pixels appeared INSIDE the zone — the spec post-pass "
        f"replicated foreign plate content (hall of mirrors)")


def test_spec_scale_down_still_scales_zone_material():
    spec, mask, shape = _scene()
    out1 = _run(spec, mask, shape, 1.0)
    out05 = _run(spec, mask, shape, 0.5)
    in_zone = mask > 0.5
    diff = float(np.mean(np.abs(out1[:, :, 0][in_zone].astype(np.float32)
                                - out05[:, :, 0][in_zone].astype(np.float32))))
    assert diff > 1.0, (
        f"in-zone spec unchanged between scale 1.0 and 0.5 (diff={diff:.3f}); "
        f"the fix disabled spec scaling instead of just removing whole-plate tiling")


def test_post_pass_guard_skips_matched_scales():
    # spec_scale matching base_scale must NOT trigger the post-pass at all
    # (PATH 1 handles it inline in compose_finish).
    assert eng._spec_placement_post_pass_needed({"base_scale": 0.5, "spec_scale": 0.5}) is False
    assert eng._spec_placement_post_pass_needed({}) is False
    assert eng._spec_placement_post_pass_needed({"base_scale": 1.0, "spec_scale": 0.5}) is True


def test_all_soft_mask_fallback_does_not_crash():
    spec, mask, shape = _scene()
    soft = np.clip(mask, 0.0, 0.4)  # no strong pixels anywhere
    out = _run(spec, soft, shape, 0.5)
    assert out.shape == spec.shape
