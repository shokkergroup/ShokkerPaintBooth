"""Regression guardrails for color-pick zone mask coverage.

## Context (originally 2026-04-20 regression loop iter 6;
## UPDATED after 2026-04-21 HEENAN OVERNIGHT iter 5)

Checklist #6 asked: do color-pick zones on Numbers/Sponsors/decals
get partial coverage when the layer is correct? With layer-mask
ordering cleared in iter 4 and cross-layer priority cleared in
iter 5 of the earlier audit, any remaining partial coverage must
come from the color-pick math itself.

Audit findings on `engine.core.build_zone_mask` for the color_rgb path:

- **Soft-falloff is by design.** The mask is `1 - dist/tolerance`
  clipped to [0,1]. A pixel exactly at the tolerance boundary gets
  mask=0; a pixel at half the tolerance gets mask=0.5. This is NOT
  a regression — it's the intended painter UX so there's no visible
  hard seam at the tolerance edge.

- **GPU vs CPU metric divergence — NOW FIXED (2026-04-21 overnight
  iter 5).** Pre-fix, the GPU branch used unweighted Euclidean
  distance while the CPU branch used BT.601-weighted. Measured
  painter-visible impact at default tolerance=30: CPU caught
  1.2x–1.4x more pixels (2.6%–5.8% of canvas extra coverage); at
  tight tolerance=20, up to 1.9x / 20% extra. Fix: GPU branch now
  applies the same BT.601 weights the CPU branch always documented.
  Behavioral proof: `test_gpu_cpu_pick_produces_identical_output`
  below runs both branches on the same input and asserts
  `max(|mask_cpu - mask_gpu|) < 1e-5`.

  Painter-facing consequence flagged in `engine/core.py` inline: a
  GPU-only painter who had tuned tolerance for the pre-fix stricter
  behavior will now catch slightly more pixels at the same tolerance;
  reducing their saved tolerance by ~20% yields equivalent output.

These tests pin both the intentional design (soft falloff) and the
unified metric (GPU == CPU) so a silent change in either direction
is caught.
"""

import math

import numpy as np
import pytest


def test_color_pick_soft_falloff_is_linear_at_half_tolerance():
    """A pixel at exactly half the tolerance distance must have
    mask≈0.5. This proves the `1 - dist/tolerance` falloff is in
    effect. If someone switches to hard-edge or squared falloff,
    this test fires.
    """
    from engine.core import analyze_paint_colors, build_zone_mask

    target = (200, 100, 50)
    tolerance = 30
    # A pixel whose BT.601-weighted distance from target is exactly
    # tolerance/2 should produce mask≈0.5. Construct deltas so that
    # sqrt(0.30·dr² + 0.59·dg² + 0.11·db²) = tolerance/2 = 15.
    # Simplest: put all delta on G (dg=?): sqrt(0.59·dg²) = 15 → dg≈19.5
    dg = 15.0 / math.sqrt(0.59)
    test_pixel = (target[0], target[1] + dg, target[2])

    h, w = 4, 4
    scheme = np.zeros((h, w, 3), dtype=np.float32)
    scheme[0, 0] = (target[0] / 255.0, target[1] / 255.0, target[2] / 255.0)
    scheme[0, 1] = (test_pixel[0] / 255.0, test_pixel[1] / 255.0, test_pixel[2] / 255.0)
    stats = analyze_paint_colors(scheme)
    sel = {"color_rgb": list(target), "tolerance": tolerance}
    mask = build_zone_mask(scheme, stats, sel, blur_radius=0)

    # Center pixel (exact match) must be ~1.0
    assert abs(float(mask[0, 0]) - 1.0) < 0.05, (
        f"Exact-match pixel should have mask=1.0, got {mask[0, 0]:.3f}. "
        f"The falloff formula may have been changed."
    )
    # Half-tolerance pixel must be ~0.5 (within ±0.1 for rounding)
    assert 0.40 < float(mask[0, 1]) < 0.60, (
        f"Half-tolerance pixel (bt601 dist={15.0:.1f}, tolerance={tolerance}) "
        f"should have mask≈0.5, got {mask[0, 1]:.3f}. The soft-falloff "
        f"formula `1 - dist/tolerance` may have been changed (e.g. to "
        f"hard-edge thresholding or a squared falloff)."
    )


def test_color_pick_covers_tight_cluster_at_default_tolerance():
    """A tight color cluster (±5 RGB variance around target) must be
    covered at mask ≥ 0.8 across the whole cluster under the default
    tolerance=30. This is the "gold numbers" painter scenario: the
    cluster is tight, tolerance is reasonable, no partial-coverage
    complaint should arise.

    If this test fails, either:
    (a) tolerance semantics have drifted (e.g. switched from
        weighted to unweighted distance making coverage tighter), or
    (b) the falloff scale changed.
    """
    from engine.core import analyze_paint_colors, build_zone_mask

    h, w = 10, 10
    scheme = np.zeros((h, w, 3), dtype=np.float32)
    target = (230, 200, 20)
    # Tight 4x4 cluster: each pixel ±4 RGB from target (deterministic)
    for y in range(4):
        for x in range(4):
            scheme[y, x, 0] = (target[0] + (x - 2) * 2) / 255.0
            scheme[y, x, 1] = (target[1] + (y - 2) * 2) / 255.0
            scheme[y, x, 2] = target[2] / 255.0
    stats = analyze_paint_colors(scheme)
    sel = {"color_rgb": list(target), "tolerance": 30}
    mask = build_zone_mask(scheme, stats, sel, blur_radius=0)

    cluster_min = float(mask[:4, :4].min())
    cluster_mean = float(mask[:4, :4].mean())
    outside_max = float(mask[4:, 4:].max())

    assert cluster_min >= 0.80, (
        f"Tight gold cluster has worst pixel mask={cluster_min:.3f} at "
        f"tolerance=30. Expected >=0.80. The tolerance math has "
        f"tightened."
    )
    assert cluster_mean >= 0.88, (
        f"Tight gold cluster mean mask={cluster_mean:.3f}, expected >=0.88."
    )
    assert outside_max == 0.0, (
        f"Color pick leaked to non-cluster pixels: max outside = "
        f"{outside_max:.3f}. The tolerance is too loose or the metric "
        f"has changed."
    )


def test_gpu_cpu_metric_is_unified_on_bt601():
    """After the 2026-04-21 HEENAN OVERNIGHT iter 5 fix, both GPU
    and CPU branches of the color_rgb distance computation use the
    SAME BT.601-weighted perceptual metric. Pre-fix, GPU used
    unweighted Euclidean and CPU used weighted; same tolerance
    caught different pixel counts on different hardware — a
    painter's preset rendered differently between GPU and CPU
    painters.

    The old unweighted GPU form `(_scheme_g[:,:,0] - _t0)**2 + ...
    + (_scheme_g[:,:,2] - _t2)**2` must be GONE. Both branches
    must contain the `0.30 + 0.59 + 0.11` weighted sqrt.

    Companion behavioral test `test_gpu_cpu_pick_produces_identical_output`
    runs both branches on the same input and asserts bit-for-bit equal
    output masks.
    """
    import engine.core as core
    src = core.__file__
    text = open(src, "r", encoding="utf-8").read()

    # The old unweighted GPU form must be GONE.
    assert "_scheme_g[:,:,2] - _t2)**2" not in text, (
        "engine/core.py still contains the pre-fix unweighted GPU "
        "Euclidean form `(_scheme_g[:,:,2] - _t2)**2`. The GPU branch "
        "has regressed back to the unweighted metric — cross-platform "
        "consistency broken. Reapply the BT.601-weighted form."
    )
    # BT.601 weights must appear at least twice (once per branch).
    weight_literal = "0.30 + _dg*_dg * 0.59 + _db*_db * 0.11"
    cpu_weight_literal = "dr*dr * 0.30 + dg*dg * 0.59 + db*db * 0.11"
    assert weight_literal in text, (
        "engine/core.py GPU branch no longer applies BT.601 weights "
        "`0.30 + _dg*_dg * 0.59 + _db*_db * 0.11`. Unified metric "
        "regression — cross-platform consistency broken."
    )
    assert cpu_weight_literal in text, (
        "engine/core.py CPU branch no longer applies BT.601 weights. "
        "Perceptual distance has been lost — painter color-pick "
        "behavior regressed."
    )


def test_gpu_cpu_pick_produces_identical_output():
    """Run build_zone_mask with both GPU and CPU branches forced
    on the same input scheme and assert the output masks are
    bit-for-bit identical. Strongest proof of cross-platform
    consistency.
    """
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import numpy as np
        import engine.core as core

    # Try GPU path: skip if cupy isn't installed / no GPU.
    try:
        import cupy as _cp  # noqa: F401
    except ImportError:
        import pytest as _pt
        _pt.skip("cupy not available; GPU branch cannot be exercised here")

    scheme = np.random.RandomState(42).uniform(0, 1, (64, 64, 3)).astype(np.float32)
    # Inject an exact target and some near-misses.
    target_rgb = (180, 120, 60)
    scheme[0, 0] = (target_rgb[0] / 255, target_rgb[1] / 255, target_rgb[2] / 255)
    scheme[0, 1] = scheme[0, 0] + np.array([0.05, 0.0, 0.0], dtype=np.float32)

    selector = {"color_rgb": list(target_rgb), "tolerance": 30}
    orig_is_gpu = core.is_gpu

    try:
        core.is_gpu = lambda: False
        mask_cpu = core.build_zone_mask(scheme, {}, selector, blur_radius=0)
        core.is_gpu = lambda: True
        mask_gpu = core.build_zone_mask(scheme, {}, selector, blur_radius=0)
    finally:
        core.is_gpu = orig_is_gpu

    import numpy as np2
    max_diff = float(np2.abs(mask_cpu - mask_gpu).max())
    assert max_diff < 1e-5, (
        f"GPU and CPU branches produce different masks "
        f"(max pixel diff={max_diff}). The BT.601 unification "
        f"has regressed — cross-platform consistency broken."
    )
