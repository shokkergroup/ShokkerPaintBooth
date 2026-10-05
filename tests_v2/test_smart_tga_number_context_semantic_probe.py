import numpy as np

from scripts.smart_tga_number_context_semantic_probe import _canonical_d4, _threshold


def test_canonical_d4_is_rotation_and_mirror_invariant():
    grid = np.arange(64, dtype=np.float64).reshape(8, 8)
    expected = _canonical_d4(grid)
    assert np.array_equal(expected, _canonical_d4(np.rot90(grid)))
    assert np.array_equal(expected, _canonical_d4(np.fliplr(grid)))


def test_threshold_is_above_every_oof_hard_negative():
    scores = np.asarray([0.9, 0.7, 0.4, 0.2])
    labels = np.asarray([1, 1, 0, 0])
    threshold, metrics = _threshold(scores, labels)
    assert threshold > 0.4
    assert metrics["false_positive"] == 0
    assert metrics["true_positive"] == 2
