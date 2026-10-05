"""Regression guardrail — spec-only Foundation Bases must return
the input paint byte-for-byte.

## Context (2026-04-21 painter report)

Painter observed "gray/silver overlay" on Metallic, Chrome, and
Frozen foundations when applying them over coloured paint. Root
cause: the `paint_enh_*` functions for these three bases were ADDING
brightness / desaturation / cool-bias to the RGB channels. Over a
saturated red, the brightness-add reads as "washed-out red" (i.e.,
the painter's red gets tinted with gray). Over any colour, the
frozen desat reads as "icy-gray".

These are material-property foundations, not paint tints. The
metallic / chrome / frozen character must come entirely from the
matching `spec_enh_*` helper (which modulates M/R/CC channels to
set reflectivity, roughness, and clearcoat depth). The paint
channel should be untouched.

## What this test does

For each of the three spec-only foundations, feeds a saturated-red
paint and a dark-navy paint through the paint function and asserts
the output is byte-for-byte identical to the input across the
masked region. A single-ULP delta would still be a clearer signal
than the broad hue-drift threshold used in the earlier `iter 1`
foundation-neutrality test (which only caught hue SHIFTS, not
brightness/desat additions that moved all channels together).

## Why the older iter-1 test missed this

`tests/test_regression_foundation_neutrality.py` measured
`max(|dR-dG|, |dG-dB|, |dR-dB|)` and required < 0.05. That's
hue-drift detection on a neutral-gray input. Uniform brightness
added to all three channels on a colour input moves the channels
together (low hue drift) while visibly washing out the paint.
This stricter bit-for-bit test catches both classes.
"""

import numpy as np
import pytest


SPEC_ONLY_FOUNDATIONS = [
    "paint_enh_metallic",
    "paint_enh_chrome",
    "paint_enh_frozen",
]


@pytest.fixture(scope="module")
def foundation_module():
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import engine.paint_v2.foundation_enhanced as fe
    return fe


@pytest.mark.parametrize("fn_name", SPEC_ONLY_FOUNDATIONS)
@pytest.mark.parametrize("paint_label,paint_rgb", [
    ("saturated_red", (0.90, 0.10, 0.10)),
    ("dark_navy",     (0.05, 0.05, 0.30)),
    ("bright_yellow", (0.95, 0.85, 0.05)),
    ("mid_grey",      (0.50, 0.50, 0.50)),
])
def test_spec_only_foundation_is_paint_identity(
    foundation_module, fn_name, paint_label, paint_rgb
):
    """The painter's input paint must survive the foundation call
    byte-for-byte. Any non-zero delta on any pixel is a regression.
    """
    fn = getattr(foundation_module, fn_name)
    shape = (64, 64)
    mask = np.ones(shape, dtype=np.float32)
    paint_in = np.zeros((64, 64, 3), dtype=np.float32)
    paint_in[:, :, 0] = paint_rgb[0]
    paint_in[:, :, 1] = paint_rgb[1]
    paint_in[:, :, 2] = paint_rgb[2]

    paint_out = fn(paint_in.copy(), shape, mask, 42, 1.0, 0.0)

    # Strict byte-for-byte equality on the RGB slice.
    if not np.array_equal(paint_in[:, :, :3], paint_out[:, :, :3]):
        max_abs = float(np.abs(paint_in[:, :, :3] - paint_out[:, :, :3]).max())
        pytest.fail(
            f"{fn_name} modified the paint channel on {paint_label} "
            f"(in={paint_rgb}). Max per-pixel delta = {max_abs:.6f}. "
            f"Spec-only foundations must return paint unchanged; the "
            f"metallic/chrome/frozen character belongs in the spec_enh_* "
            f"helper, not in the paint function."
        )


@pytest.mark.parametrize("fn_name", SPEC_ONLY_FOUNDATIONS)
def test_spec_only_foundation_still_has_spec_helper(
    foundation_module, fn_name
):
    """Each spec-only foundation must still have its matching
    `spec_enh_*` module-level value. If someone removes the spec
    helper during a refactor, the material look disappears entirely
    and the foundation becomes a no-op.
    """
    spec_name = fn_name.replace("paint_enh_", "spec_enh_")
    assert hasattr(foundation_module, spec_name), (
        f"{fn_name} was converted to spec-only identity but the "
        f"matching `{spec_name}` helper is missing. Without it there "
        f"is no material-property output at all — the foundation "
        f"produces no effect."
    )
