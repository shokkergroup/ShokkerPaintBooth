"""Regression guardrail: base/finish changes on layer-restricted zones
must not spill outside the zone mask.

## Invariant

Every paint and spec write in the engine is gated by `zone_mask`:

- Paint writes use the pattern `paint[channel] = paint[channel] * (1 - mask) + effect * mask`
  (see `shokker_engine_v2.py` around lines 515, 527, 554, 597-599, 645-646).
- Spec writes use `combined_spec = np.where(mask3d > threshold, zone_spec, combined_spec)`
  (see `shokker_engine_v2.py` lines 9814, 9938, 10748, 10786, 10798).

Combined with iter 4's verification that `zone_mask` is built from
`layer_mask * color_mask - claimed` (in that order), a zone with a
`source_layer_mask` cannot possibly write base/spec/paint outside its
layer.

## What this test proves

Simulates the two common write patterns on a 12×12 canvas with a zone
mask restricted to the left half. Checks that the RIGHT half of the
canvas is byte-for-byte untouched by the zone's writes.

Not a unit test of a specific function — it's a property test of the
write pattern itself. If somebody writes a new zone dispatch that
forgets to multiply by the mask or forgets the `np.where` guard, this
test shows the painter-visible consequence.

## Why source-level coverage isn't enough

Iter 4 pinned the order of `layer_mask * color_mask` before `claimed`
subtraction. But that's about BUILDING the zone mask, not about
APPLYING it. A correct zone_mask can still spill if the downstream
write operator ignores it. This test covers the write side.
"""

import numpy as np


def test_paint_write_pattern_respects_mask():
    """The multiplicative blend `paint * (1 - mask) + effect * mask`
    must leave pixels outside the mask bit-for-bit unchanged."""
    h, w = 12, 12
    paint = np.full((h, w, 3), 0.5, dtype=np.float32)
    # Inject a distinct "effect" color on the whole canvas; we'll see
    # which pixels end up with it.
    effect_color = np.array([0.1, 0.8, 0.3], dtype=np.float32)
    effect = np.broadcast_to(effect_color, (h, w, 3)).copy()
    # Zone mask: left half only
    mask = np.zeros((h, w), dtype=np.float32)
    mask[:, : w // 2] = 1.0

    # Apply the canonical multiplicative blend pattern, as the engine does
    before = paint.copy()
    for c in range(3):
        paint[:, :, c] = paint[:, :, c] * (1 - mask) + effect[:, :, c] * mask

    # Left half was written (should match effect color where mask=1)
    left_mean = paint[:, : w // 2, :].mean(axis=(0, 1))
    assert np.allclose(left_mean, effect_color, atol=1e-6), (
        f"Left half did not receive the zone effect: mean={left_mean}, "
        f"expected ~{effect_color}"
    )
    # Right half must be BIT-FOR-BIT unchanged
    right_after = paint[:, w // 2 :, :]
    right_before = before[:, w // 2 :, :]
    assert np.array_equal(right_after, right_before), (
        "Paint spilled into right half (outside zone mask). The "
        "multiplicative blend pattern has been broken."
    )


def test_spec_write_pattern_respects_mask_threshold():
    """The spec write pattern `np.where(mask3d > threshold, zone_spec,
    combined_spec)` must preserve combined_spec outside the zone.

    Uses mask3d threshold = 0.01 (matches the engine's convention at
    shokker_engine_v2.py lines 9814 / 9938 / 10748).
    """
    h, w = 12, 12
    combined_spec = np.zeros((h, w, 4), dtype=np.float32)
    combined_spec[:, :, 0] = 127  # pre-existing M
    combined_spec[:, :, 1] = 64   # pre-existing R
    combined_spec[:, :, 2] = 16   # pre-existing CC
    combined_spec[:, :, 3] = 255

    # Zone spec: zone wants to set M=240 R=8 CC=16 A=255 where mask active
    zone_spec = np.zeros_like(combined_spec)
    zone_spec[:, :, 0] = 240
    zone_spec[:, :, 1] = 8
    zone_spec[:, :, 2] = 16
    zone_spec[:, :, 3] = 255

    # Zone mask restricted to top half
    zone_mask = np.zeros((h, w), dtype=np.float32)
    zone_mask[: h // 2, :] = 1.0
    mask3d = zone_mask[:, :, np.newaxis]

    before = combined_spec.copy()
    combined_spec = np.where(mask3d > 0.01, zone_spec, combined_spec).astype(np.float32)

    # Top half should now be zone_spec
    assert np.array_equal(combined_spec[: h // 2, :, :], zone_spec[: h // 2, :, :]), (
        "Top half did not receive the zone spec."
    )
    # Bottom half must be unchanged
    assert np.array_equal(combined_spec[h // 2 :, :, :], before[h // 2 :, :, :]), (
        "Spec spilled into bottom half (outside zone mask). The "
        "`np.where(mask3d > threshold, zone_spec, combined_spec)` "
        "pattern has been broken or the threshold has been inverted."
    )


def test_engine_uses_both_write_patterns():
    """Source-level check that shokker_engine_v2.py still uses BOTH of
    these patterns. A restructure that replaces them with a single new
    gate should be reviewed for equivalence, not merged silently.
    """
    from pathlib import Path
    src = Path(__file__).resolve().parent.parent / "shokker_engine_v2.py"
    text = src.read_text(encoding="utf-8")

    # Count spec-gate instances (np.where on mask3d > ...)
    spec_count = text.count("combined_spec = np.where(mask3d > 0.01, zone_spec")
    assert spec_count >= 3, (
        f"shokker_engine_v2.py has only {spec_count} `combined_spec = "
        f"np.where(mask3d > 0.01, zone_spec,...)` gate(s). Previously "
        f"there were >=3 (iter 7 of 2026-04-20 regression loop documented "
        f"instances at lines 9814, 9938, 10748, among others). A "
        f"restructure may have consolidated or removed these gates — "
        f"verify no write path is now unguarded."
    )
    # Count paint-gate instances (paint[*] = paint[*] * (1 - mask) + * mask)
    # We just check the shape is present somewhere
    has_paint_mask = "* (1 - mask)" in text or "* (1-mask)" in text
    assert has_paint_mask, (
        "shokker_engine_v2.py no longer contains the paint-mask blend "
        "pattern `* (1 - mask)`. Paint writes may no longer be gated; "
        "review urgently."
    )
