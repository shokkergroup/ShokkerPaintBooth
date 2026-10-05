import numpy as np

from engine.spec_sculpt.number_context_semantics import context_feature_mapping


def test_context_features_keep_singleton_proposals_finite():
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    seed = {"bbox": [3, 3, 1, 1]}
    for bbox in ([3, 3, 1, 1], [2, 3, 4, 1], [3, 2, 1, 4]):
        features = context_feature_mapping(
            rgb,
            {"bbox": bbox, "prototype_index": 0},
            seed,
        )
        assert len(features) == 177
        assert all(np.isfinite(value) for value in features.values())
        assert features["crop_edge_mean"] == 0.0
