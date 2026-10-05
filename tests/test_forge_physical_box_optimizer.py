import numpy as np
import pytest

from _forge_physical_box_optimizer import qualify_source_domain, search_translation


def test_already_covered_asset_stays_at_zero_without_resize():
    source = np.ones((4, 5), bool)
    result, _supports, _routed = search_translation(
        source, [0.0, 0.0, 1.0, 1.0], lambda _box: [np.ones_like(source)], 0.1, 0.1, 0.1
    )
    assert result["translation"] == [0.0, 0.0]
    assert result["placement_ready"] and not result["resized"]


def test_translation_recovers_support_without_shrinking_source():
    source = np.ones((3, 4), bool)

    def support(box):
        mask = np.zeros_like(source)
        if box[0] >= 0.1 - 1e-8:
            mask[:] = True
        return [mask]

    result, _supports, _routed = search_translation(
        source, [0.0, 0.0, 1.0, 1.0], support, 0.1, 0.0, 0.1
    )
    assert result["translation"] == [0.1, 0.0]
    assert result["placement_ready"] and not result["resized"]
    assert result["baseline_proof"]["gap_pixels"] == 12
    assert result["best_proof"]["gap_pixels"] == 0


def test_uv_derived_source_is_rejected_before_calibration():
    with pytest.raises(ValueError, match="direct physical evidence"):
        qualify_source_domain("uv_layer")
