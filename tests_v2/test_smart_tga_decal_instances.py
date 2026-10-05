from __future__ import annotations

import numpy as np
import pytest

from engine.spec_sculpt import decal_instances
from engine.spec_sculpt.candidate_evidence import capture_candidate_snapshot


def _synthetic_instances():
    cv2 = decal_instances.cv2
    canvas = np.full((420, 520, 3), 34, np.uint8)
    patch = np.full((90, 180, 3), 18, np.uint8)
    cv2.putText(patch, "24", (12, 72), cv2.FONT_HERSHEY_DUPLEX, 2.5, (245, 220, 30), 7, cv2.LINE_AA)
    cv2.rectangle(patch, (4, 4), (175, 85), (30, 170, 245), 3)
    cv2.line(patch, (8, 82), (170, 8), (245, 60, 40), 4)
    canvas[40:130, 35:215] = patch
    transform = cv2.getRotationMatrix2D((90, 45), 17.0, 0.78)
    transformed = cv2.warpAffine(patch, transform, (180, 90), borderValue=(34, 34, 34))
    canvas[270:360, 300:480] = transformed
    return canvas


def test_visual_instance_match_finds_transformed_copy_without_assigning_owner():
    if decal_instances.cv2 is None or not hasattr(decal_instances.cv2, "SIFT_create"):
        pytest.skip("SIFT unavailable")
    match = decal_instances.find_visual_instance_match(_synthetic_instances(), (35, 40, 180, 90))
    assert match is not None
    assert match.inlier_count >= 6
    assert match.inlier_ratio >= 0.55
    x, y, width, height = match.bbox
    assert x < 480 and x + width > 300
    assert y < 360 and y + height > 270
    assert not hasattr(match, "owner")


def test_visual_feature_index_is_read_only_and_reusable():
    if decal_instances.cv2 is None or not hasattr(decal_instances.cv2, "SIFT_create"):
        pytest.skip("SIFT unavailable")
    canvas = _synthetic_instances()
    index = decal_instances.build_visual_feature_index(canvas)
    assert index is not None
    assert index.gray.flags.writeable is False
    assert index.descriptors.flags.writeable is False
    match = decal_instances.find_visual_instance_match(
        canvas, (35, 40, 180, 90), feature_index=index
    )
    assert match is not None
    with pytest.raises(ValueError, match="shapes differ"):
        decal_instances.find_visual_instance_match(
            canvas[:300], (35, 40, 180, 90), feature_index=index
        )


def test_visual_match_maps_geometry_to_existing_components_without_owner():
    match = decal_instances.VisualInstanceMatch(
        source_bbox=(2, 2, 12, 12),
        polygon=((20.0, 20.0), (50.0, 20.0), (50.0, 40.0), (20.0, 40.0)),
        good_match_count=9,
        inlier_count=8,
        inlier_ratio=0.888889,
        projected_area_ratio=1.0,
    )
    component_map = np.full((64, 80), -1, np.int32)
    component_map[20:41, 20:36] = 4
    component_map[20:41, 36:51] = 9
    overlaps = decal_instances.visual_match_component_overlaps(
        match, component_map, min_pixels=10
    )
    assert [item.component_index for item in overlaps] == [4, 9]
    assert sum(item.matched_pixels for item in overlaps) == 31 * 21
    assert all(item.component_fraction == 1.0 for item in overlaps)
    assert all(not hasattr(item, "owner") for item in overlaps)


def test_visual_instance_match_abstains_on_flat_panel():
    if decal_instances.cv2 is None or not hasattr(decal_instances.cv2, "SIFT_create"):
        pytest.skip("SIFT unavailable")
    canvas = np.full((240, 320, 3), 40, np.uint8)
    canvas[20:80, 20:160] = 210
    assert decal_instances.find_visual_instance_match(canvas, (20, 20, 140, 60)) is None


def test_candidate_instances_preserve_conflicting_owner_hypotheses_without_authority():
    shape = (80, 100)
    number = np.zeros(shape, np.uint8)
    sponsor = np.zeros(shape, np.uint8)
    number[20:50, 25:60] = 255
    sponsor[24:48, 28:63] = 255
    snapshot = capture_candidate_snapshot(
        {"numbers": number, "sponsors": sponsor},
        source_stage="raw_detector",
        source="synthetic_overlap",
    )
    instances = decal_instances.assemble_candidate_instances(snapshot)
    assert len(instances) == 1
    instance = instances[0]
    assert len(instance.candidate_ids) == 2
    assert [item.proposed_owner for item in instance.owner_hypotheses] == ["numbers", "sponsors"]
    assert instance.local_mask.flags.writeable is False
    assert not hasattr(instance, "owner")
    telemetry = decal_instances.candidate_instance_telemetry(snapshot)
    assert telemetry["multi_owner_conflict_count"] == 1
    assert telemetry["ownership_authority"] is False
    assert telemetry["casts_votes"] is False


def test_candidate_instances_do_not_join_nearby_non_overlapping_logos():
    shape = (80, 120)
    left = np.zeros(shape, np.uint8)
    right = np.zeros(shape, np.uint8)
    left[20:42, 20:45] = 255
    right[20:42, 48:73] = 255
    snapshot = capture_candidate_snapshot(
        {"numbers": left, "sponsors": right},
        source_stage="raw_detector",
        source="synthetic_nearby",
    )
    instances = decal_instances.assemble_candidate_instances(snapshot)
    assert len(instances) == 2
    assert all(len(item.owner_hypotheses) == 1 for item in instances)


def test_candidate_instance_features_are_intrinsic_perceptual_and_ocr_aware():
    shape = (96, 128)
    proposal = np.zeros(shape, np.uint8)
    proposal[22:70, 30:94] = 255
    snapshot = capture_candidate_snapshot(
        {"numbers": proposal}, source_stage="raw_detector", source="synthetic_35"
    )
    instances = decal_instances.assemble_candidate_instances(snapshot)
    rgb = np.full((*shape, 3), 18, np.uint8)
    rgb[22:70, 30:94] = (225, 35, 45)
    rgb[28:64:4, 34:90] = (250, 220, 35)
    features = decal_instances.extract_candidate_instance_features(
        rgb,
        instances,
        ocr_regions=[{"bbox": [32, 24, 58, 42], "text": "35"}],
    )
    assert len(features) == 1
    item = features[0]
    assert len(item.shape_occupancy) == 16
    assert item.bbox_normalized == pytest.approx(
        (30 / 128, 22 / 96, 64 / 128, 48 / 96), abs=1e-6
    )
    assert item.border_distance_fraction >= 0.0
    assert item.perceptual_chroma > 0.10
    assert item.palette_role == "chromatic"
    assert item.texture_entropy > 0.0
    assert item.ocr_digit_coverage > 0.5
    assert item.ocr_alpha_coverage == 0.0
    assert item.proposed_owners == ("numbers",)
    assert item.proposal_conflict is False
    assert not hasattr(item, "owner")


def test_candidate_feature_telemetry_remains_shadow_only():
    shape = (72, 96)
    number = np.zeros(shape, np.uint8)
    sponsor = np.zeros(shape, np.uint8)
    number[18:54, 20:62] = 255
    sponsor[20:52, 23:65] = 255
    snapshot = capture_candidate_snapshot(
        {"numbers": number, "sponsors": sponsor},
        source_stage="raw_detector",
        source="synthetic_conflict",
    )
    rgb = np.full((*shape, 3), (40, 180, 230), np.uint8)
    telemetry = decal_instances.candidate_instance_telemetry(snapshot, rgb=rgb)
    feature_telemetry = telemetry["features"]
    assert feature_telemetry["feature_count"] == 1
    assert feature_telemetry["casts_votes"] is False
    assert feature_telemetry["ownership_authority"] is False
    assert feature_telemetry["conflict_samples"][0]["proposal_conflict"] is True
    assert "records" not in feature_telemetry
    assert "semantic_objects" not in telemetry
    exported_telemetry = decal_instances.candidate_instance_telemetry(
        snapshot, rgb=rgb, include_feature_records=True
    )
    exported = exported_telemetry["features"]
    assert len(exported["records"]) == exported["feature_count"] == 1
    assert exported["records"][0]["proposed_owners"] == ["numbers", "sponsors"]
    assert exported["records"][0]["bbox"] == [20, 18, 45, 36]
    assert len(exported["records"][0]["candidate_ids"]) == 2
    semantic = exported_telemetry["semantic_objects"]
    assert semantic["singleton_object_count"] == 1
    assert semantic["partitioned_instance_count"] == 1
    assert semantic["casts_votes"] is False
    assert semantic["ownership_authority"] is False
    encoded = exported["records"][0]["mask_rle"]
    decoded = decal_instances.decode_instance_mask_rle(encoded)
    instance = decal_instances.assemble_candidate_instances(snapshot)[0]
    assert np.array_equal(decoded, instance.local_mask)
    assert decoded.flags.writeable is False


def test_instance_mask_rle_roundtrips_sparse_and_border_touching_shapes():
    mask = np.zeros((17, 23), bool)
    mask[0, :4] = True
    mask[3:9, 5:16] = True
    mask[16, 22] = True
    encoded = decal_instances.encode_instance_mask_rle(mask)
    assert encoded["encoding"] == "binary-rle-row-major-v1"
    assert encoded["shape"] == [17, 23]
    assert sum(encoded["counts"]) == mask.size
    decoded = decal_instances.decode_instance_mask_rle(encoded)
    assert np.array_equal(decoded, mask)


def test_instance_mask_rle_rejects_corrupt_pixel_count():
    with pytest.raises(ValueError, match="pixel count"):
        decal_instances.decode_instance_mask_rle({
            "encoding": "binary-rle-row-major-v1",
            "shape": [2, 3],
            "counts": [2, 2],
        })
