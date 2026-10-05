"""Regression guardrail: source-layer-restricted `remaining` stays layer-local.

The painter report here is specific: a zone restricted to the Numbers layer
with `color: "remaining"` should still find the remaining Number pixels. It
must not collapse just because an earlier unrestricted/global zone claimed the
same canvas coordinates on the flattened composite.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def test_remainder_zone_ignores_unrestricted_global_claims_inside_source_layer(engine_module):
    """A source-layer remainder zone should use that layer's claim space."""
    h, w = 16, 16
    numbers_mask = np.zeros((h, w), dtype=np.float32)
    numbers_mask[:, 4:12] = 1.0

    zones = [
        {"name": "Body", "color": "everything", "finish": "gloss"},
        {
            "name": "Numbers Remaining",
            "color": "remaining",
            "finish": "gloss",
            "source_layer_mask": numbers_mask,
        },
    ]
    zone_masks = [np.ones((h, w), dtype=np.float32), None]
    claimed_hard = np.ones((h, w), dtype=np.float32)

    result = engine_module._build_remainder_zone_mask(
        zones[1], 1, zones, zone_masks, claimed_hard, sigma=0.0
    )

    assert float(result[:, 4:12].mean()) > 0.95, (
        "Numbers-layer remainder collapsed even though the only earlier claim "
        "was unrestricted/global. The source-layer-local remainder contract is broken."
    )
    assert float(result[:, :4].max()) == 0.0
    assert float(result[:, 12:].max()) == 0.0


def test_same_resolution_source_mask_is_normalized_to_binary_ownership(engine_module):
    """Binary ownership is an engine invariant, not a client assumption."""
    source = np.array([[0.0, 0.49, 0.5, 1.0]], dtype=np.float32)
    normalized = engine_module._normalize_source_layer_mask(source, source.shape)
    assert np.array_equal(
        normalized,
        np.array([[0.0, 0.0, 1.0, 1.0]], dtype=np.float32),
    )


def test_invalid_present_source_mask_fails_closed(engine_module):
    """A malformed restriction must never degrade into unrestricted paint."""
    zone = {
        "name": "Broken Restriction",
        "source_layer_mask": {"width": 4, "height": 4, "runs": [[255, 2]]},
    }
    normalized = engine_module._cached_source_layer_mask(zone, (4, 4), 0)
    assert normalized is not None
    assert normalized.shape == (4, 4)
    assert float(normalized.sum()) == 0.0


def test_remainder_zone_still_respects_earlier_claims_on_the_same_source_layer(engine_module):
    """Earlier same-layer zones should still subtract from later remainder."""
    h, w = 16, 16
    numbers_mask = np.zeros((h, w), dtype=np.float32)
    numbers_mask[:, 4:12] = 1.0

    earlier_numbers_claim = np.zeros((h, w), dtype=np.float32)
    earlier_numbers_claim[:, 4:8] = 1.0

    zones = [
        {
            "name": "Numbers Blue",
            "color": "blue",
            "finish": "gloss",
            "source_layer_mask": numbers_mask,
        },
        {
            "name": "Numbers Remaining",
            "color": "remaining",
            "finish": "gloss",
            "source_layer_mask": numbers_mask,
        },
    ]
    zone_masks = [earlier_numbers_claim, None]
    claimed_hard = earlier_numbers_claim.copy()

    result = engine_module._build_remainder_zone_mask(
        zones[1], 1, zones, zone_masks, claimed_hard, sigma=0.0
    )

    assert float(result[:, 4:8].max()) == 0.0, (
        "Later remainder reclaimed pixels already owned by an earlier zone on the same source layer."
    )
    assert float(result[:, 8:12].mean()) > 0.95, (
        "Unclaimed pixels on the same source layer did not survive into the remainder mask."
    )
    assert float(result[:, :4].max()) == 0.0
    assert float(result[:, 12:].max()) == 0.0


def test_final_render_keeps_source_local_remainder_after_global_claim(tmp_path, engine_module):
    """The final effective-mask pass must not erase a layer-local remainder.

    This deliberately crosses the full ``build_multi_zone`` boundary.  The
    helper-only tests above stayed green while the later global
    ``prior_claimed`` subtraction reduced this zone to zero active pixels.
    ``export_layers`` gives us the exact mask that reached paint/spec compose.
    """
    h, w = 16, 16
    source = np.zeros((h, w, 4), dtype=np.uint8)
    source[:, :, :3] = (32, 96, 160)
    source[:, :, 3] = 255
    source_path = tmp_path / "source.png"
    Image.fromarray(source, "RGBA").save(source_path)

    numbers_mask = np.zeros((h, w), dtype=np.float32)
    numbers_mask[:, 4:12] = 1.0
    zones = [
        {
            "name": "Global Body",
            "color": "remaining",
            "base": "gloss",
            "hard_edge": True,
        },
        {
            "name": "Numbers Remaining",
            "color": "remaining",
            "base": "matte",
            "source_layer_mask": numbers_mask,
            # Intentionally false: source ownership itself must force the
            # binary hard invariant through every downstream path.
            "hard_edge": False,
        },
    ]

    _paint, _spec, export_layers = engine_module.build_multi_zone(
        str(source_path),
        str(tmp_path),
        zones,
        preview_mode=True,
        export_layers=True,
    )
    by_index = {layer["zone_index"]: layer for layer in export_layers}

    assert 1 in by_index, (
        "The source-layer remainder was built locally, then erased by the "
        "final global prior-claim subtraction and never reached compose."
    )
    effective = by_index[1]["mask"]
    assert np.array_equal(effective, numbers_mask), (
        "The final compose mask must be the exact binary source-local "
        "remainder, independent of earlier unrestricted/global claims."
    )
