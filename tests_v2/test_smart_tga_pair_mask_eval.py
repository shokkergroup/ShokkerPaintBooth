import numpy as np

from scripts.smart_tga_pair_mask_eval import score_masks


def test_pair_mask_metrics_are_exact():
    predicted = np.array([[1, 1, 0], [0, 1, 0]], dtype=bool)
    expected = np.array([[1, 0, 0], [0, 1, 1]], dtype=bool)
    result = score_masks(predicted, expected)
    assert result["true_positive_pixels"] == 2
    assert result["false_positive_pixels"] == 1
    assert result["false_negative_pixels"] == 1
    assert result["precision"] == 0.666667
    assert result["recall"] == 0.666667
    assert result["iou"] == 0.5


def test_empty_masks_do_not_divide_by_zero():
    result = score_masks(np.zeros((2, 2), bool), np.zeros((2, 2), bool))
    assert result["true_positive_pixels"] == 0
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
