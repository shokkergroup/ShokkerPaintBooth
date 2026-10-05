import numpy as np

from engine.spec_sculpt.decal_instances import DecalCandidateInstance, DecalInstanceFeatures, OwnerHypothesis
from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
from engine.spec_sculpt.decal_semantic_objects import (
    derive_semantic_decal_objects,
    extract_semantic_decal_object_features,
    semantic_decal_object_telemetry,
)


def _instance(name, bbox, *, source_stage="test", candidate_ids=None):
    width, height = bbox[2:]
    mask = np.ones((height, width), bool)
    return DecalCandidateInstance(
        instance_id=name, bbox=bbox, area=int(mask.sum()), local_mask=mask,
        candidate_ids=tuple(candidate_ids or (name,)), source_stages=(source_stage,), sources=("test",),
        owner_hypotheses=(OwnerHypothesis("numbers", (name,), 1, 1.0, int(mask.sum())),),
    )


def _features(name):
    return DecalInstanceFeatures(
        instance_id=name, area_fraction=0.01, bbox_normalized=(0.0, 0.0, 0.1, 0.1),
        border_distance_fraction=0.1, fill_ratio=1.0, aspect_ratio=0.5,
        shape_occupancy=(1.0,) * 16, edge_density=0.2, strong_gradient_fraction=0.1,
        texture_entropy=0.3, mean_rgb=(200.0, 200.0, 200.0), std_rgb=(20.0, 20.0, 20.0),
        perceptual_lightness=0.8, perceptual_chroma=0.01, perceptual_hue_degrees=0.0,
        palette_role="light_neutral", ocr_max_coverage=0.2, ocr_alpha_coverage=0.0,
        ocr_digit_coverage=0.2, ocr_token_count=1, proposed_owners=("numbers",),
        proposal_conflict=False,
    )


def test_semantic_objects_partition_groups_and_atomic_instances_exactly_once():
    instances = (
        _instance("a", (10, 10, 8, 24)),
        _instance("b", (22, 10, 8, 24)),
        _instance("atomic-number", (50, 40, 18, 30)),
    )
    features = tuple(_features(item.instance_id) for item in instances)
    objects = derive_semantic_decal_objects(instances, features, image_shape=(100, 100))
    assert sorted(item.object_kind for item in objects) == ["physical_group", "singleton"]
    assert sorted(value for item in objects for value in item.instance_ids) == ["a", "atomic-number", "b"]
    assert sum(len(item.instance_ids) for item in objects) == len(instances)
    atomic = next(item for item in objects if item.object_kind == "singleton")
    assert atomic.instance_ids == ("atomic-number",)
    assert atomic.area == instances[2].area

    records = extract_semantic_decal_object_features(
        objects, instances, features, image_shape=(100, 100),
    )
    atomic_features = next(item for item in records if item.object_kind == "singleton")
    assert atomic_features.member_count == 1
    assert atomic_features.number_member_fraction == 1.0
    assert len(atomic_features.shape_occupancy) == 16
    assert atomic_features.bbox_x_fraction == 0.5
    assert atomic_features.bbox_y_fraction == 0.4
    assert atomic_features.bbox_width_fraction == 0.18
    assert atomic_features.bbox_height_fraction == 0.3
    assert atomic_features.border_distance_fraction == 0.3
    assert atomic_features.candidate_count == 1
    assert atomic_features.source_stage_count == 1
    assert atomic_features.source_count == 1
    assert atomic_features.merge_reason_count == 0
    assert atomic_features.gpu_model_member_fraction == 0.0
    assert atomic_features.template_raw_member_fraction == 0.0
    assert atomic_features.multi_proposal_member_fraction == 0.0
    assert atomic_features.mean_strong_gradient_fraction == 0.1
    assert atomic_features.max_strong_gradient_fraction == 0.1
    assert atomic_features.max_ocr_alpha_coverage == 0.0
    assert atomic_features.max_ocr_token_count == 1
    assert atomic_features.mean_perceptual_lightness == 0.8
    assert atomic_features.mean_perceptual_chroma == 0.01

    telemetry = semantic_decal_object_telemetry(
        instances, features, image_shape=(100, 100), include_feature_records=True,
    )
    assert telemetry["schema"] == "smart-tga-semantic-decal-objects-v3"
    assert telemetry["partitioned_instance_count"] == 3
    assert telemetry["singleton_object_count"] == 1
    assert telemetry["adds_pixels"] is False
    assert telemetry["casts_votes"] is False
    assert telemetry["ownership_authority"] is False
    atomic_record = next(item for item in telemetry["records"] if item["object_kind"] == "singleton")
    assert np.array_equal(decode_instance_mask_rle(atomic_record["mask_rle"]), atomic.local_mask)


def test_semantic_object_features_preserve_proposal_provenance_without_authority():
    instances = (
        _instance("a", (10, 10, 8, 24), source_stage="gpu_model_raw", candidate_ids=("a", "a2")),
        _instance("b", (22, 10, 8, 24), source_stage="template_raw"),
    )
    records = extract_semantic_decal_object_features(
        derive_semantic_decal_objects(instances, tuple(_features(item.instance_id) for item in instances), image_shape=(100, 100)),
        instances, tuple(_features(item.instance_id) for item in instances), image_shape=(100, 100),
    )
    grouped = records[0]
    assert grouped.object_kind == "physical_group"
    assert grouped.candidate_count == 3
    assert grouped.source_stage_count == 2
    assert grouped.gpu_model_member_fraction == 0.5
    assert grouped.template_raw_member_fraction == 0.5
    assert grouped.multi_proposal_member_fraction == 0.5
