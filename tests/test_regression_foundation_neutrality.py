"""Regression guardrail: HARDMODE-tuned enh_* finishes must not inject hue.

The HARDMODE autonomous loop widened the spec-side (M/R/CC) amplitudes
for 11 ★ Enhanced Foundation entries. This regression test proves that
their PAINT functions still produce near-neutral output on a neutral-
gray input canvas — i.e. the spec widening did not accidentally
propagate into a paint-side hue shift.

If a future edit re-introduces hue coupling (e.g. by sharing a seeded
field between spec and paint where one gains a chromatic bias), this
test will fail.

Rule: max |R_drift - G_drift|, |G_drift - B_drift|, |R_drift - B_drift|
must stay below 0.05 on neutral-gray input. That's about ±13 8-bit
levels of chromatic difference — well above paint noise floor but far
below anything a painter would perceive as tint.

Note: this test does NOT assert brightness stays neutral. Finishes
like `enh_piano_black` are supposed to darken the input. The test
only asserts that when they do move, they move all three channels
together (brightness) rather than one or two channels (hue).
"""

import numpy as np
import pytest

HARDMODE_TUNED_ENH = [
    ("enh_wet_look",      "paint_enh_wet_look"),
    ("enh_ceramic_glaze", "paint_enh_ceramic_glaze"),
    ("enh_gel_coat",      "paint_enh_gel_coat"),
    ("enh_baked_enamel",  "paint_enh_baked_enamel"),
    ("enh_gloss",         "paint_enh_gloss"),
    ("enh_piano_black",   "paint_enh_piano_black"),
    ("enh_soft_gloss",    "paint_enh_soft_gloss"),
    ("enh_semi_gloss",    "paint_enh_semi_gloss"),
    ("enh_carbon_fiber",  "paint_enh_carbon_fiber"),
    ("enh_pearl",         "paint_enh_pearl"),
    ("enh_metallic",      "paint_enh_metallic"),
]


@pytest.mark.parametrize("finish_id,paint_fn_name", HARDMODE_TUNED_ENH)
@pytest.mark.parametrize("seed", [1, 42, 99])
@pytest.mark.parametrize("shape", [(64, 64), (128, 128)])
def test_enh_paint_fn_no_hue_injection_on_neutral_gray(finish_id, paint_fn_name, seed, shape):
    """Each HARDMODE-tuned enh_* paint_fn must produce near-neutral
    chromatic output on a neutral-gray input canvas.

    Hue drift = max |dR-dG|, |dG-dB|, |dR-dB|. Must stay <0.05.
    If this test starts failing, the finish has developed a tint
    coupling between its spec and paint functions (or the paint
    function itself has changed). Investigate before committing.
    """
    from engine.paint_v2 import foundation_enhanced as fe
    pfn = getattr(fe, paint_fn_name, None)
    assert pfn is not None, f"paint function {paint_fn_name} not found on foundation_enhanced"

    # Neutral gray input
    paint = np.full((*shape, 4), 0.5, dtype=np.float32)
    paint[..., 3] = 1.0
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    out = pfn(paint, shape, mask, seed, 1.0, bb)
    rgb = out[..., :3]

    dR = float(rgb[..., 0].mean() - 0.5)
    dG = float(rgb[..., 1].mean() - 0.5)
    dB = float(rgb[..., 2].mean() - 0.5)

    # Hue drift: differences between channel drifts (brightness-only
    # changes move all three channels together, so these differences
    # stay small).
    hue_drift = max(abs(dR - dG), abs(dG - dB), abs(dR - dB))
    assert hue_drift < 0.05, (
        f"{finish_id} injected hue on neutral-gray input "
        f"(dR={dR:+.3f}, dG={dG:+.3f}, dB={dB:+.3f}, drift={hue_drift:.3f}). "
        f"Foundation bases are supposed to be spec-only; the paint path "
        f"should only move brightness, not tint."
    )
