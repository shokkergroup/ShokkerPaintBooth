from types import SimpleNamespace

import numpy as np

from engine.spec_sculpt.number_context_position import (
    POSITION_FEATURE_NAMES, position_feature_mapping,
)
from engine.spec_sculpt.number_context_shadow import number_context_shadow_telemetry


def _feature():
    return SimpleNamespace(
        instance_id="di:seed", area_fraction=0.001, fill_ratio=0.5,
        edge_density=0.1, texture_entropy=0.2, strong_gradient_fraction=0.1,
        perceptual_lightness=0.5, perceptual_chroma=0.2,
        ocr_alpha_coverage=0.0, ocr_digit_coverage=0.0, ocr_max_coverage=0.0,
    )


def test_position_features_are_normalized_and_complete():
    features = position_feature_mapping([256, 512, 128, 64])
    assert tuple(features) == POSITION_FEATURE_NAMES
    assert features["center_x"] == 0.3125
    assert features["center_y"] == 0.53125
    assert all(np.isfinite(value) for value in features.values())


def test_position_corroboration_remains_zero_authority_shadow():
    result = number_context_shadow_telemetry(
        [SimpleNamespace(instance_id="di:seed", bbox=(100, 100, 20, 40))],
        [_feature()], rgb=np.zeros((1024, 1024, 3), dtype=np.uint8),
        score_semantics=True, score_position=True, export_full=True,
    )
    position = result["position"]
    assert position["model_version"] == "cycle699-dlm-context-position-v1"
    assert position["role"] == "corroboration_only"
    assert position["casts_votes"] is False
    assert position["ownership_authority"] is False
    assert position["adds_pixels"] is False
    assert all("position_status" in item for item in result["proposal_records"])
