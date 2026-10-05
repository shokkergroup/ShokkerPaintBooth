import cv2
import numpy as np

from engine.spec_sculpt.number_object_segmentation import (
    INPUT_CHANNELS,
    MODEL_SIZE,
    build_tiny_unet,
    component_mask,
    image_feature_tensor,
    pooled_boxes,
    pooled_supervision,
    probability_region_proposals,
    project_local_support,
)


def test_features_are_bounded_and_owner_neutral():
    rgb = np.zeros((32, 48, 3), np.uint8)
    rgb[8:24, 12:36] = (240, 80, 20)
    features = image_feature_tensor(rgb)
    assert features.shape == (INPUT_CHANNELS, MODEL_SIZE, MODEL_SIZE)
    assert np.isfinite(features).all()
    assert 0.0 <= float(features.min()) <= float(features.max()) <= 1.0


def test_component_mask_selects_tight_component():
    mask = np.zeros((30, 40), bool)
    mask[2:8, 3:10] = True
    mask[15:25, 20:35] = True
    selected = component_mask(mask, [20, 15, 15, 10], 150)
    assert int(selected.sum()) == 150
    assert selected[20, 25]
    assert not selected[4, 5]


def test_supervision_preserves_unknown_and_weak_boxes():
    positive = np.zeros((32, 32), bool)
    negative = np.zeros((32, 32), bool)
    positive[2:6, 3:7] = True
    negative[20:25, 21:27] = True
    target, known = pooled_supervision(positive, negative, 16)
    weak = pooled_boxes([[8, 8, 8, 8]], positive.shape, 16)
    assert target.sum() > 0 and known.sum() > target.sum()
    assert known[8, 8] == 0
    assert weak[4:8, 4:8].all()


def test_supervision_keeps_subcell_reviewed_fragment():
    positive = np.zeros((1024, 1024), bool)
    positive[11, 17] = True
    target, known = pooled_supervision(positive, np.zeros_like(positive), 256)
    assert target.sum() == 1
    assert known.sum() == 1


def test_probability_regions_are_owner_neutral_nested_proposals():
    probability = np.zeros((16, 16), np.float32)
    probability[3:9, 4:10] = 0.7
    probability[5:8, 6:9] = 0.95
    proposals = probability_region_proposals(
        probability, (64, 64), quantiles=(0.8, 0.95), min_model_pixels=2,
    )
    assert proposals
    assert all(item["owner_neutral"] and not item["ownership_authority"] for item in proposals)
    assert {item["provenance"]["relative_quantile"] for item in proposals} == {0.8, 0.95}
    assert all(item["raw_support"].flags.writeable is False for item in proposals)


def test_local_support_projects_into_bbox_instead_of_stretching_over_canvas():
    local = np.ones((10, 20), bool)
    projected = project_local_support(local, [50, 20, 20, 10], (100, 100), 100)
    assert projected.sum() == 200
    assert projected[20:30, 50:70].all()
    assert not projected[:20].any()


def test_local_projection_matches_full_canvas_area_pooling_at_fractional_edges():
    local = np.zeros((3, 3), bool)
    local[0, 0] = True
    projected = project_local_support(local, [3, 3, 3, 3], (10, 10), 4)
    canvas = np.zeros((10, 10), np.float32)
    canvas[3, 3] = 1.0
    expected = cv2.resize(canvas, (4, 4), interpolation=cv2.INTER_AREA) > 0
    assert np.array_equal(projected, expected)


def test_tiny_unet_preserves_resolution():
    import torch
    model = build_tiny_unet(4)
    output = model(torch.zeros(1, INPUT_CHANNELS, 64, 64))
    assert tuple(output.shape) == (1, 1, 64, 64)
