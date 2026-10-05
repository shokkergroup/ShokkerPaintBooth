import numpy as np
import pytest

import _forge_delivery_comparison as comparison


def test_compare_rgba_counts_pixels_not_channels() -> None:
    first = np.zeros((3, 4, 4), dtype=np.uint8)
    second = first.copy()
    second[1, 2, :3] = (10, 20, 30)
    result = comparison.compare_rgba(first, second)
    assert result["different_pixels"] == 1
    assert result["different_fraction"] == pytest.approx(1 / 12)
    assert result["max_channel_error"] == 30


def test_compare_rgba_rejects_shape_mismatch() -> None:
    with pytest.raises(ValueError):
        comparison.compare_rgba(np.zeros((2, 2, 4), dtype=np.uint8), np.zeros((3, 2, 4), dtype=np.uint8))
