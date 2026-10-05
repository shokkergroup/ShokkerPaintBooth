"""Regression guardrail (iter 7, 2026-04-20 sweep) — base changes on
zone-restricted layers must NOT spill across the canvas.

## What iter 4/5 and ``test_regression_base_layer_isolation.py`` proved

* iter 4 pinned the order ``zone_mask = layer_mask * color_mask - claimed``
  (built from `source_layer_mask` and the per-zone color-pick + the
  canvas-cumulative claim subtraction).
* ``test_regression_base_layer_isolation.py`` already pins the
  *write-pattern* invariant in isolation:

  - paint:  ``paint[c] = paint[c] * (1 - mask) + effect * mask``
  - spec:   ``combined_spec = np.where(mask3d > 0.01, zone_spec,
            combined_spec)``

## What iter 7 still needs

The synthetic-pattern test does NOT prove that a *real* base actually
goes through that pattern when invoked end-to-end through
``compose_paint_mod`` and the engine's PATH 1 spec gate. A mis-wired
base could:

  - Mutate the paint array in-place from inside the registry's
    ``paint_fn`` *before* the multiplicative blend is applied (e.g.
    write to ``paint[:]`` instead of ``paint[mask>0]``).
  - Or skip the spec-combiner gate entirely on a code path that
    forgets ``np.where(mask3d > 0.01, ...)``.

This file probes a real, painter-visible Foundation Base
(``f_metallic`` — the one the painter saw spilling) end-to-end and
asserts the OUTSIDE-of-mask pixels of the resulting paint and spec
are bit-for-bit unchanged from a fingerprint baseline.

Failure mode this protects against: the painter selects Metallic on a
small zone (logo, sponsor patch) and metallic flake / spec changes
appear on the whole canvas instead of just the zone.
"""

import io
import contextlib

import numpy as np
import pytest


# A 32x32 fingerprint paint canvas: 4 distinct quadrants so any spill
# is easy to detect with `np.array_equal`.
def _make_fingerprint_paint(h=32, w=32):
    paint = np.zeros((h, w, 3), dtype=np.float32)
    paint[: h // 2, : w // 2, :] = (0.13, 0.27, 0.41)  # TL
    paint[: h // 2, w // 2 :, :] = (0.59, 0.71, 0.83)  # TR
    paint[h // 2 :, : w // 2, :] = (0.32, 0.06, 0.94)  # BL
    paint[h // 2 :, w // 2 :, :] = (0.88, 0.55, 0.22)  # BR
    return paint


def _make_box_mask(h=32, w=32):
    """Mask covers the top-left 8x8 box only. Everything else is OUT."""
    mask = np.zeros((h, w), dtype=np.float32)
    mask[2:10, 2:10] = 1.0
    return mask


@pytest.fixture(scope="module")
def compose_mod():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine import compose
    return compose


def test_compose_paint_mod_does_not_spill_outside_zone_mask(compose_mod):
    """``compose_paint_mod("f_metallic", ...)`` may write the metallic
    paint effect inside the mask, but pixels OUTSIDE the mask must be
    bit-for-bit identical to what was passed in.

    If this fires: a base's ``paint_fn`` (or one of the v6 base
    overlay branches at lines 3300+) is mutating paint pixels outside
    ``hard_mask``. The painter will see the foundation finish bleed
    into adjacent zones / unmasked canvas.
    """
    h, w = 32, 32
    paint_in = _make_fingerprint_paint(h, w)
    mask = _make_box_mask(h, w)

    paint_before_outside = paint_in.copy()
    paint_before_outside[mask > 0.1] = -999  # sentinel; we only check OUT pixels

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        paint_out = compose_mod.compose_paint_mod(
            "f_metallic", "none",
            paint_in.copy(), (h, w), mask,
            seed=4242, pm=1.0, bb=1.0,
        )
    paint_out = np.asarray(paint_out)

    # Every pixel where mask <= 0.1 must equal the original input.
    out_mask = mask <= 0.1  # boolean (h, w)
    if paint_out.shape[2] == 4:
        paint_out_rgb = paint_out[:, :, :3]
    else:
        paint_out_rgb = paint_out

    diff = np.abs(paint_out_rgb - paint_in[:, :, :3])
    spilled = (diff[..., 0] + diff[..., 1] + diff[..., 2]) > 1e-6
    spilled_outside = spilled & out_mask

    n_spilled = int(spilled_outside.sum())
    n_outside = int(out_mask.sum())
    assert n_spilled == 0, (
        f"compose_paint_mod('f_metallic', ...) spilled into {n_spilled} of "
        f"{n_outside} OUTSIDE-the-zone-mask pixels. The painter would see "
        f"Metallic foundation paint on adjacent / unmasked regions of the "
        f"canvas. Likely cause: a paint_fn or v6 base overlay is writing "
        f"to paint[:] instead of paint[hard_mask>0]."
    )


def test_spec_combiner_gate_holds_with_real_compose_finish(compose_mod):
    """End-to-end at the spec layer: feed a real f_metallic spec into
    the canonical combiner gate from shokker_engine_v2.py PATH 1
    (lines 10789-10801) and assert that the OUTSIDE-of-mask pixels of
    ``combined_spec`` are unchanged from baseline.

    This catches: a future restructure that replaces the
    ``np.where(mask3d > 0.01, zone_spec, ...)`` gate with something
    looser (e.g. an additive blend, or the wrong threshold direction).
    """
    h, w = 32, 32
    mask = _make_box_mask(h, w)

    # Baseline combined_spec — distinct sentinel values per channel
    combined_spec = np.zeros((h, w, 4), dtype=np.float32)
    combined_spec[:, :, 0] = 17    # M sentinel
    combined_spec[:, :, 1] = 89    # R sentinel
    combined_spec[:, :, 2] = 33    # CC sentinel
    combined_spec[:, :, 3] = 255   # A
    baseline = combined_spec.copy()

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        zone_spec = compose_mod.compose_finish(
            "f_metallic", "none", (h, w), mask, seed=4242, sm=1.0,
        )
    zone_spec = np.asarray(zone_spec).astype(np.float32)
    assert zone_spec.shape == (h, w, 4)

    # Apply the engine's canonical PATH 1 gate (matches lines 10789-10801)
    mask3d = mask[:, :, np.newaxis]
    strong = mask3d > 0.5
    soft = (mask3d > 0.05) & ~strong
    blended = np.clip(
        zone_spec * mask3d + combined_spec * (1 - mask3d),
        0, 255,
    )
    combined_spec = np.where(strong, zone_spec, np.where(soft, blended, combined_spec))

    out_mask = (mask <= 0.05)
    for ch_idx, ch_name in enumerate(("M", "R", "CC", "A")):
        ch_after = combined_spec[:, :, ch_idx][out_mask]
        ch_before = baseline[:, :, ch_idx][out_mask]
        assert np.array_equal(ch_after, ch_before), (
            f"Spec channel {ch_name} changed in OUTSIDE-of-mask pixels "
            f"after compose_finish('f_metallic', ...) was passed through "
            f"the canonical combiner gate. Either compose_finish returned "
            f"an unexpected shape/value or the gate logic was inverted."
        )


def test_compose_paint_mod_color_override_writes_inside_only(compose_mod):
    """Sanity counter-test: prove that when SOMETHING does mutate the
    paint inside the mask, the spill-test above is non-trivial.

    Foundation-Base ``f_*`` paint_fns are intentionally no-ops (per
    iter 1 of this regression sweep — Foundation Bases must not
    affect paint, only spec). So we exercise the
    ``base_color_mode='solid'`` override path on the same
    ``compose_paint_mod`` call: that path is *guaranteed* to recolor
    the in-mask region to the requested color, and therefore proves
    that:

      (a) at least one in-mask pixel is mutated (no-op trap), AND
      (b) every out-mask pixel is unchanged.

    If (b) ever fires, the painter would see the override color
    bleed into adjacent zones. If (a) fires, it means
    _apply_base_color_override stopped writing (regression).
    """
    h, w = 32, 32
    paint_in = _make_fingerprint_paint(h, w)
    mask = _make_box_mask(h, w)
    OVERRIDE = (0.0, 1.0, 0.0)  # bright green — won't collide with any quadrant

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        paint_out = compose_mod.compose_paint_mod(
            "f_metallic", "none",
            paint_in.copy(), (h, w), mask,
            seed=4242, pm=1.0, bb=1.0,
            base_color_mode="solid",
            base_color=list(OVERRIDE),
            base_color_strength=1.0,
        )
    paint_out = np.asarray(paint_out)
    if paint_out.shape[2] == 4:
        paint_out = paint_out[:, :, :3]

    in_mask = mask > 0.1
    out_mask = mask <= 0.1

    # (a) at least one in-mask pixel was actually changed
    diff_in = np.abs(paint_out - paint_in[:, :, :3])
    changed_inside = ((diff_in[..., 0] + diff_in[..., 1] + diff_in[..., 2]) > 1e-6) & in_mask
    assert int(changed_inside.sum()) > 0, (
        "compose_paint_mod base_color_mode='solid' wrote 0 in-mask "
        "pixels. _apply_base_color_override appears broken — sanity "
        "guard for the spill test is not exercising any write."
    )

    # (b) every out-mask pixel is byte-for-byte identical to baseline
    delta_out = np.abs(paint_out - paint_in[:, :, :3])
    spilled_outside = ((delta_out[..., 0] + delta_out[..., 1] + delta_out[..., 2]) > 1e-6) & out_mask
    n_spilled = int(spilled_outside.sum())
    assert n_spilled == 0, (
        f"compose_paint_mod base color override spilled into "
        f"{n_spilled} OUTSIDE-the-zone-mask pixels. The painter "
        f"would see the zone color bleed onto unmasked regions."
    )

def test_solid_base_color_is_opaque_replacement_not_psd_tint(compose_mod):
    """Solid base color must replace source art, not tint its luminance.

    Repro: PSD source loaded, Metallic foundation selected, Red solid color
    selected, Remaining clicked for Zone 1. The render showed a translucent red
    wash with PSD logos still visible. Solid means the zone gets a new paint
    substrate; source pixels must not ghost through it.
    """
    h, w = 48, 48
    source_a = _make_fingerprint_paint(h, w)
    source_b = 1.0 - source_a
    full_mask = np.ones((h, w), dtype=np.float32)
    red = [1.0, 0.0, 0.0]

    paths = [
        (
            "single",
            lambda src: compose_mod.compose_paint_mod(
                "f_metallic", "none",
                src.copy(), (h, w), full_mask,
                seed=9001, pm=1.0, bb=1.0,
                base_color_mode="solid",
                base_color=red,
                base_color_strength=1.0,
            ),
        ),
        (
            "stacked",
            lambda src: compose_mod.compose_paint_mod_stacked(
                "f_metallic", [],
                src.copy(), (h, w), full_mask,
                seed=9001, pm=1.0, bb=1.0,
                base_color_mode="solid",
                base_color=red,
                base_color_strength=1.0,
            ),
        ),
    ]

    for label, render in paths:
        out_a = np.asarray(render(source_a)[:, :, :3], dtype=np.float32)
        out_b = np.asarray(render(source_b)[:, :, :3], dtype=np.float32)

        assert float(np.abs(out_a - out_b).max()) < 1e-6, (
            f"{label}: solid base color output changed when only the PSD/source "
            "art changed. That means source luminance is still leaking into "
            "the replacement base."
        )
        assert float(out_a[:, :, 0].min()) > 0.999, label
        assert float(out_a[:, :, 1].max()) < 1e-6, label
        assert float(out_a[:, :, 2].max()) < 1e-6, label
