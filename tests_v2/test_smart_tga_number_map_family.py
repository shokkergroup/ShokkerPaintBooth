import numpy as np

from engine.spec_sculpt.decal_subinstances import IntrinsicSubinstance
from engine.spec_sculpt import number_local_copy_proposals as local_copy_module
from engine.spec_sculpt.number_local_copy_proposals import (
    local_contrast_probability_proposals,
    palette_panel_local_copy_proposals,
)
from engine.spec_sculpt.number_map_family_features import (
    FAMILY_FEATURE_NAMES,
    map_family_feature_vector,
    map_family_ocr_features,
    map_family_owner_corroboration_features,
    map_family_relationship_features,
    map_family_template_position_features,
    map_proposal_feature_vector,
)
from scripts.smart_tga_number_map_family_probe import _zero_negative_operating_point
from engine.spec_sculpt.number_map_family_model import (
    SCALAR_FEATURE_NAMES,
    frozen_candidate_inference,
)
from engine.spec_sculpt.number_map_family_shadow import (
    _accepted_global_family_boxes,
    _annotate_local_wordmark_evidence,
    _apply_local_copy_adjudication,
    _proposal_conflict_features,
    _support_purity_features,
)


def _proposal(rgb, probability, bbox, foundation, quantile):
    _x, _y, width, height = bbox
    mask = np.zeros((height, width), bool)
    mask[2:-2, 3:-3] = True
    provenance = {
        "relative_quantile": quantile, "threshold": 0.7,
        "mean_probability": 0.82, "max_probability": 0.96,
        "model_pixels": int(mask.sum()),
    }
    vector = map_proposal_feature_vector(
        rgb, bbox, mask, probability, provenance, foundation,
    )
    return {
        "proposal_bbox": bbox, "provenance": provenance,
        "foundation_probability": foundation, "vector": vector,
    }


def test_map_proposal_features_are_position_and_owner_neutral():
    rgb = np.full((80, 100, 3), 48, np.uint8)
    probability = np.full((80, 100), 0.2, np.float32)
    first = (8, 10, 20, 24)
    second = (62, 46, 20, 24)
    for x, y, width, height in (first, second):
        rgb[y + 2:y + height - 2, x + 3:x + width - 3] = (225, 80, 30)
        probability[y:y + height, x:x + width] = 0.84
    left = _proposal(rgb, probability, first, 0.91, 0.9)["vector"]
    right = _proposal(rgb, probability, second, 0.91, 0.9)["vector"]
    np.testing.assert_allclose(left, right, atol=1e-6)


def test_family_features_capture_nested_stability_without_votes():
    rgb = np.full((80, 100, 3), 60, np.uint8)
    probability = np.full((80, 100), 0.8, np.float32)
    members = [
        _proposal(rgb, probability, (10, 12, 30, 28), 0.90, 0.90),
        _proposal(rgb, probability, (12, 14, 24, 22), 0.95, 0.98),
    ]
    vector = map_family_feature_vector(members)
    assert vector.shape == (len(FAMILY_FEATURE_NAMES),)
    assert np.isfinite(vector).all()
    assert vector.flags.writeable is False


def test_zero_negative_operating_point_prefers_recall_inside_precision_gate():
    probability = np.asarray([0.92, 0.81, 0.76, 0.71, 0.61], np.float32)
    truth = np.asarray([True, True, False, True, False])
    hits, _precision, _threshold_sort, threshold, summary = _zero_negative_operating_point(
        probability, truth,
    )
    assert hits == 2
    assert threshold == float(probability[1])
    assert summary["accepted_hard_negative_families"] == 0


def test_peer_features_reward_repeated_d4_shape_without_semantic_votes():
    embeddings = np.asarray([
        [1.0, 0.0, 1.0, 0.0],
        [0.99, 0.01, 0.98, 0.02],
        [0.0, 1.0, 0.0, 1.0],
    ], np.float32)
    features = map_family_relationship_features(embeddings, [100, 110, 95])
    assert features.shape[0] == 3
    assert features[0, 0] > 0.99
    assert features[0, 3] > 0.99
    assert features[2, 0] < 0.1


def test_ocr_features_separate_alpha_and_digit_overlap_without_authority():
    alpha = map_family_ocr_features((10, 10, 40, 20), [{
        "bbox": [12, 12, 30, 12], "text": "VALVOLINE", "confidence": 0.9,
        "text_quality": 1.0,
    }])
    digit = map_family_ocr_features((10, 10, 40, 20), [{
        "bbox": [12, 12, 30, 12], "text": "52", "confidence": 0.8,
        "text_quality": 0.7,
    }])
    assert alpha[2] > 0 and alpha[3] == 0
    assert digit[3] > 0 and digit[2] == 0


def test_legacy_owner_features_use_exact_support_not_bbox_authority():
    support = np.zeros((6, 8), bool)
    support[1:5, 2:6] = True
    numbers = np.zeros((20, 20), bool)
    sponsors = np.zeros((20, 20), bool)
    numbers[6:10, 7:11] = True
    sponsors[5, 5] = True  # inside bbox but outside exact proposal support
    features = map_family_owner_corroboration_features(
        (5, 5, 8, 6), support, {"numbers": numbers, "sponsors": sponsors},
    )
    assert features[0] == 1.0
    assert features[1] == 0.0


def test_template_position_features_are_scaled_exact_and_non_authoritative():
    support = np.ones((20, 20), bool)
    panel_map = {
        "template": "generic-test", "space": "100x100",
        "number_blocks": [{"name": "door", "bbox": [20, 20, 20, 20]}],
        "sponsor_blocks": [{"name": "rear", "bbox": [60, 20, 20, 20]}],
    }
    number = map_family_template_position_features(
        (40, 40, 20, 20), support, (200, 200), panel_map,
    )
    sponsor = map_family_template_position_features(
        (120, 40, 20, 20), support, (200, 200), panel_map,
    )
    assert number[0] == 1.0 and number[1] == 0.0
    assert sponsor[0] == 0.0 and sponsor[1] == 1.0
    assert number.flags.writeable is False


def test_frozen_holdout_inference_requires_visual_plus_position_or_legacy_number():
    scalar = np.zeros((3, len(SCALAR_FEATURE_NAMES)), np.float32)
    scalar[0, SCALAR_FEATURE_NAMES.index("clip_digit_similarity_max")] = 0.31
    scalar[0, SCALAR_FEATURE_NAMES.index("template_number_fraction")] = 0.8
    scalar[1, SCALAR_FEATURE_NAMES.index("legacy_number_overlap")] = 0.7
    scalar[2, SCALAR_FEATURE_NAMES.index("clip_digit_similarity_max")] = 0.31
    embeddings = np.zeros((3, 4), np.float32)
    candidate = {
        "feature_names": np.asarray(SCALAR_FEATURE_NAMES),
        "pca_mean": np.zeros(4, np.float32),
        "pca_components": np.zeros((1, 4), np.float32),
        "mean": np.zeros(len(SCALAR_FEATURE_NAMES) + 1, np.float32),
        "scale": np.ones(len(SCALAR_FEATURE_NAMES) + 1, np.float32),
        "coefficient": np.zeros(len(SCALAR_FEATURE_NAMES) + 1, np.float32),
        "intercept": np.asarray([0.0], np.float32),
        "threshold": np.asarray([0.4], np.float32),
        "digit_threshold": np.asarray([0.24], np.float32),
        "number_overlap_threshold": np.asarray([0.4], np.float32),
        "template_number_threshold": np.asarray([0.3], np.float32),
    }
    probability, accepted = frozen_candidate_inference(scalar, embeddings, candidate)
    np.testing.assert_allclose(probability, 0.5)
    assert accepted.tolist() == [True, True, False]


def test_local_contrast_proposals_are_immutable_owner_neutral_observations():
    probability = np.zeros((32, 32), np.float32)
    probability[12:16, 14:18] = 1.0
    original = probability.copy()
    proposals = local_contrast_probability_proposals(
        probability, (64, 64), window_size=9, z_scores=(0.5,),
    )
    np.testing.assert_array_equal(probability, original)
    assert proposals
    assert all(item["owner_neutral"] for item in proposals)
    assert not any(item["ownership_authority"] for item in proposals)
    assert all(item["raw_support"].flags.writeable is False for item in proposals)


def test_palette_panel_proposals_are_bounded_without_casting_votes(monkeypatch):
    probability = np.zeros((32, 32), np.float32)
    probability[10:20, 10:20] = 0.9
    rgb = np.full((64, 64, 3), 40, np.uint8)

    def fake_subinstances(_crop, parent, **_kwargs):
        height, width = parent.shape
        if height < 3 or width < 3:
            return ()
        mask = np.zeros_like(parent, dtype=bool)
        y = min(height - 2, max(0, height // 3))
        x = min(width - 2, max(0, width // 3))
        mask[y:y + 2, x:x + 2] = True
        return (IntrinsicSubinstance(
            hypothesis="test-palette", source_role="ink", local_mask=mask,
            bbox=(x, y, 2, 2), area=4,
            parent_fraction=4.0 / float(parent.size), component_count=1,
        ),)

    monkeypatch.setattr(local_copy_module, "derive_intrinsic_subinstances", fake_subinstances)
    proposals = palette_panel_local_copy_proposals(
        rgb, probability,
        {"number_blocks": [{"name": "all", "bbox": [0, 0, 1024, 1024]}]},
        maximum_per_number_block=1,
    )
    assert len(proposals) == 1
    assert all(item["owner_neutral"] for item in proposals)
    assert not any(item["ownership_authority"] for item in proposals)


def test_local_copy_adjudication_only_removes_uncorroborated_acceptances():
    rows = [
        {"accepted": True, "clip_digit_minus_all_negative_margin": -0.019},
        {"accepted": True, "clip_digit_minus_all_negative_margin": -0.021},
        {"accepted": False, "clip_digit_minus_all_negative_margin": 0.2},
    ]
    _apply_local_copy_adjudication(rows)
    assert [row["accepted"] for row in rows] == [True, False, False]
    assert [row["frozen_scorer_accepted"] for row in rows] == [True, True, False]


def test_local_copy_adjudication_rejects_intrinsically_stripe_like_support():
    rows = [
        {
            "accepted": True,
            "clip_digit_minus_all_negative_margin": 0.1,
            "intrinsic_log_orientation_free_aspect": float(np.log(3.9)),
        },
        {
            "accepted": True,
            "clip_digit_minus_all_negative_margin": 0.1,
            "intrinsic_log_orientation_free_aspect": float(np.log(4.1)),
        },
    ]
    _apply_local_copy_adjudication(rows)
    assert [row["accepted"] for row in rows] == [True, False]
    assert [row["local_shape_corroborated"] for row in rows] == [True, False]


def test_purity_feature_schema_stays_owner_and_position_neutral():
    purity_names = {
        "fill_ratio", "log_orientation_free_aspect", "edge_density",
        "strong_gradient_fraction", "texture_entropy",
        "family_log_member_count", "family_shape_instability",
        "family_texture_instability", "family_palette_instability",
    }
    assert purity_names.issubset(set(SCALAR_FEATURE_NAMES))
    assert not any(
        "legacy" in name or "template" in name or "bbox" in name
        for name in purity_names
    )


def test_support_purity_counts_disconnected_visual_components():
    support = np.zeros((20, 30), bool)
    support[2:8, 2:8] = True
    support[11:17, 20:27] = True
    features = _support_purity_features(support)
    assert np.isclose(features["support_log_component_count"], np.log1p(2))
    assert 0.5 < features["support_largest_component_fraction"] < 0.6
    assert features["support_component_area_entropy"] > 0.9


def test_proposal_conflict_is_directional_and_position_neutral():
    families = [
        {"family_bbox": [100, 200, 200, 100]},
        {"family_bbox": [120, 220, 100, 50]},
        {"family_bbox": [500, 600, 80, 40]},
    ]
    outer = _proposal_conflict_features(families, 0)
    inner = _proposal_conflict_features(families, 1)
    assert outer["proposal_smaller_peer_containment"] == 1.0
    assert outer["proposal_smaller_peer_area_ratio"] == 0.25
    assert outer["proposal_overlap_count_log"] == np.log1p(1)
    assert inner["proposal_smaller_peer_containment"] == 0.0


def test_local_copy_retry_is_suppressed_only_by_accepted_global_families():
    families = [{"family_bbox": [1, 2, 3, 4]}, {"family_bbox": [5, 6, 7, 8]}]
    rows = [{"accepted": False}, {"accepted": True}]
    assert _accepted_global_family_boxes(families, rows) == ([5, 6, 7, 8],)


class _FakeLocalOcrReader:
    def __init__(self, detections):
        self.detections = detections

    def readtext(self, _crop, **_kwargs):
        return self.detections


def test_local_candidate_wordmark_ocr_can_only_veto_strong_alpha_words():
    image = np.zeros((40, 50, 3), np.uint8)
    families = [{"family_bbox": [5, 6, 20, 18]}]
    rows = [{"accepted": True, "clip_digit_minus_all_negative_margin": 0.0}]
    reader = _FakeLocalOcrReader([
        (None, "APPAREL", 0.99), (None, "49", 0.98),
    ])
    _annotate_local_wordmark_evidence(image, families, rows, reader=reader)
    _apply_local_copy_adjudication(rows)
    assert rows[0]["local_wordmark_veto"] is True
    assert rows[0]["accepted"] is False
    assert rows[0]["frozen_scorer_accepted"] is True


def test_local_candidate_wordmark_ocr_preserves_digits_and_short_noise():
    image = np.zeros((40, 50, 3), np.uint8)
    families = [{"family_bbox": [5, 6, 20, 18]}]
    rows = [{"accepted": True, "clip_digit_minus_all_negative_margin": 0.0}]
    reader = _FakeLocalOcrReader([
        (None, "44", 0.99), (None, "ces", 0.91),
    ])
    _annotate_local_wordmark_evidence(image, families, rows, reader=reader)
    _apply_local_copy_adjudication(rows)
    assert rows[0]["local_wordmark_veto"] is False
    assert rows[0]["accepted"] is True
