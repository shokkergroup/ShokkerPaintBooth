import numpy as np

from engine.spec_sculpt.number_context_component_features import (
    FEATURE_NAMES, _d4_canonical_occupancy, component_feature_vector, component_probability,
)


def test_d4_occupancy_is_rotation_and_mirror_invariant():
    grid = np.arange(16, dtype=np.float32).reshape(4, 4) / 15.0
    expected = _d4_canonical_occupancy(grid.ravel())
    for turns in range(4):
        rotated = np.rot90(grid, turns)
        assert _d4_canonical_occupancy(rotated.ravel()) == expected
        assert _d4_canonical_occupancy(np.fliplr(rotated).ravel()) == expected


def test_component_vector_is_owner_and_absolute_position_neutral():
    rgb = np.zeros((48, 64, 3), np.uint8)
    rgb[10:30, 12:32] = (235, 80, 35)
    mask = np.zeros((20, 20), bool)
    mask[2:18, 4:16] = True
    first = component_feature_vector(rgb, (12, 10, 20, 20), mask, family_margin=0.2)

    shifted = np.zeros_like(rgb)
    shifted[20:40, 32:52] = (235, 80, 35)
    second = component_feature_vector(shifted, (32, 20, 20, 20), mask, family_margin=0.2)
    assert len(first) == len(FEATURE_NAMES)
    np.testing.assert_allclose(first, second, atol=1e-6)
    assert not first.flags.writeable


def test_probability_matches_zero_logit_midpoint():
    vector = np.ones(len(FEATURE_NAMES), np.float32)
    probability = component_probability(
        vector, np.ones_like(vector), np.ones_like(vector), np.ones_like(vector), 0.0,
    )
    assert probability == 0.5
