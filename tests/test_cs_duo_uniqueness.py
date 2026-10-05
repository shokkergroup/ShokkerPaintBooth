"""HEENAN HARDMODE-R3-MICRO — cs_* duo uniqueness ratchet.

The 73 CS Duo micro-flake monolithics used to share identical noise-seed
offsets (7/107/207/307) inside spec_micro_flake, so the flake PATTERN
was pixel-identical across all of them and only the metallic baseline
differed with average colour brightness. After HARDMODE-R3-MICRO each
pair gets a unique seed_offset plus per-pair sparkle-density and
r_range derived from hue distance.

This test asserts that three probed pairs produce meaningfully different
spec maps at the pixel level. Regression would show if someone removed
the per-pair seed_offset.
"""

import numpy as np
import pytest

from engine.micro_flake_shift import CS_DUO_MICRO_MONOLITHICS


PROBE_PAIRS = ["cs_fire_ice", "cs_pink_purple", "cs_crimson_jade",
               "cs_sunset_ocean", "cs_copper_teal", "cs_burgundy_gold"]


def _render_spec(fid, shape=(128, 128), seed=42):
    spec_fn, _paint_fn = CS_DUO_MICRO_MONOLITHICS[fid]
    mask = np.ones(shape, dtype=np.float32)
    return spec_fn(shape, mask, seed, 1.0)


@pytest.mark.parametrize("fid", PROBE_PAIRS)
def test_cs_duo_spec_renders_without_error(fid):
    spec = _render_spec(fid)
    assert spec.shape == (128, 128, 4)
    assert spec.dtype == np.uint8


def test_cs_duo_pairs_have_distinct_pixel_fields():
    """Every probed cs_* pair must differ from every other probed pair
    by at least 5 M-units mean-absolute-difference at the pixel level."""
    specs = {fid: _render_spec(fid)[:, :, 0].astype(np.int32) for fid in PROBE_PAIRS}
    for i, a_id in enumerate(PROBE_PAIRS):
        for b_id in PROBE_PAIRS[i + 1:]:
            diff = float(np.abs(specs[a_id] - specs[b_id]).mean())
            assert diff >= 5.0, (
                f"cs_* duo pair {a_id} vs {b_id}: mean-abs M-diff = {diff:.1f}. "
                f"Expected >= 5.0 (pre-HARDMODE-R3-MICRO, identical pairs had diff=0). "
                f"Someone may have removed the per-pair seed_offset in "
                f"build_cs_duo_micro_shifts()."
            )


def test_cs_duo_total_count_is_stable():
    """The CS Duo bank has 73 entries; test_layer_system.py already
    ratchets specific structural properties, but a sudden drop in count
    would indicate a regression in build_cs_duo_micro_shifts()."""
    assert 60 <= len(CS_DUO_MICRO_MONOLITHICS) <= 80, (
        f"CS_DUO_MICRO_MONOLITHICS has {len(CS_DUO_MICRO_MONOLITHICS)} entries; "
        f"expected 60-80."
    )
