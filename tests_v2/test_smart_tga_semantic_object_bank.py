import cv2
import numpy as np

from engine.spec_sculpt.decal_instances import encode_instance_mask_rle
from scripts.smart_tga_semantic_object_bank import attach_reviews, build_bank


def test_semantic_object_bank_derives_exact_mask_shape_evidence_without_authority():
    mask = np.zeros((12, 20), bool)
    mask[1:5, 2:8] = True
    mask[7:11, 10:19] = True
    semantic_objects = {
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        "records": [{
            "object_id": "sdo:rectangles", "bbox": [0, 0, 20, 12],
            "object_kind": "singleton", "instance_ids": ["di:rectangles"],
            "mask_rle": encode_instance_mask_rle(mask),
        }],
    }
    inspection = [{"paint_label": "paint", "route_adjudicator_shadow": {
        "candidate_evidence": {"decal_instances": {
            "semantic_objects": semantic_objects,
            "features": {"records": [{
                "instance_id": "di:rectangles",
                "source_stages": ["appearance_quantized_raw"],
                "proposed_owners": ["unassigned"],
            }]},
        }},
    }}]
    bank = build_bank(inspection)
    record = bank["records"][0]
    assert bank["schema"] == "smart-tga-semantic-object-bank-v3"
    assert record["topology_component_count"] == 2
    assert record["topology_largest_component_fraction"] == 0.6
    assert record["topology_hole_count"] == 0
    assert record["topology_rectangular_component_fraction"] == 1.0
    assert len([key for key in record if key.startswith("geometry_hu_log_")]) == 7
    assert 0.0 < record["geometry_compactness"] <= 1.0
    assert 0.0 < record["geometry_solidity"] <= 1.0
    assert record["geometry_thickness_max"] >= record["geometry_thickness_mean"] > 0.0
    assert record["physical_group_indicator"] == 0.0
    assert record["candidate_member_ratio"] == 1.0
    assert record["candidate_member_excess"] == 0.0
    assert record["instance_origin_feature_available"] == 1.0
    assert record["appearance_quantized_instance_fraction"] == 1.0
    assert record["unassigned_instance_fraction"] == 1.0
    assert record["appearance_unassigned_instance_fraction"] == 1.0
    assert bank["casts_votes"] is False
    assert bank["ownership_authority"] is False


def test_semantic_object_bank_geometry_is_finite_for_fully_filled_tiny_mask():
    mask = np.ones((1, 3), bool)
    semantic_objects = {
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        "records": [{
            "object_id": "sdo:tiny", "bbox": [0, 0, 3, 1],
            "object_kind": "singleton", "mask_rle": encode_instance_mask_rle(mask),
        }],
    }
    bank = build_bank([{"paint_label": "paint", "route_adjudicator_shadow": {
        "candidate_evidence": {"decal_instances": {"semantic_objects": semantic_objects}},
    }}])
    record = bank["records"][0]
    geometry = [value for key, value in record.items() if key.startswith("geometry_")]
    assert geometry
    assert np.all(np.isfinite(geometry))


def test_semantic_object_bank_cross_copy_evidence_is_rotation_invariant_and_non_authoritative():
    first = np.zeros((12, 20), bool)
    first[1:11, 2:6] = True
    first[7:11, 6:17] = True
    second = np.rot90(first)
    unrelated = np.zeros((12, 20), bool)
    unrelated[2:10, 3:17] = True
    records = []
    for index, mask in enumerate((first, second, unrelated)):
        occupancy = [
            float(block.mean()) for block_row in np.array_split(mask, 4, axis=0)
            for block in np.array_split(block_row, 4, axis=1)
        ]
        records.append({
            "object_id": f"sdo:{index}", "bbox": [0, 0, mask.shape[1], mask.shape[0]],
            "object_kind": "singleton", "mask_rle": encode_instance_mask_rle(mask),
            "shape_occupancy": occupancy, "area_fraction": float(mask.mean()),
            "aspect_ratio": mask.shape[1] / mask.shape[0],
            "mean_perceptual_lightness": 0.7, "mean_perceptual_chroma": 0.2,
            "lightness_span": 0.6, "chroma_span": 0.3,
            "number_member_fraction": 1.0 if index == 0 else 0.0,
        })
    bank = build_bank([{"paint_label": "paint", "route_adjudicator_shadow": {
        "candidate_evidence": {"decal_instances": {"semantic_objects": {
            "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
            "records": records,
        }}},
    }}])
    first_record, second_record, _unrelated_record = bank["records"]
    assert first_record["cross_copy_shape_similarity"] > 0.99
    assert second_record["cross_copy_shape_similarity"] > 0.99
    assert first_record["cross_copy_max_similarity"] > 0.9
    assert second_record["cross_copy_number_anchor_max_similarity"] > 0.9
    assert bank["casts_votes"] is False
    assert bank["ownership_authority"] is False


def test_semantic_object_bank_links_atomic_and_group_reviews_without_authority():
    semantic_objects = {
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        "records": [
            {"object_id": "sdo:a", "physical_group_id": None, "bbox": [10, 10, 20, 30],
             "object_kind": "singleton", "number_member_fraction": 0.0},
            {"object_id": "sdo:b", "physical_group_id": "pdg:b", "bbox": [50, 50, 40, 20],
             "object_kind": "physical_group", "sponsor_member_fraction": 1.0},
        ],
    }
    inspection = [{
        "paint_label": "dirtlatemodel 350/car_num_x.tga",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "semantic_objects": semantic_objects,
            "physical_groups": {"features": {"records": [{
                "group_id": "pdg:b", "largest_member_fraction": 0.75,
                "smallest_member_fraction": 0.25,
            }]}},
        }}},
    }]
    components = [{"paint_label": "dirtlatemodel 350/car_num_x.tga", "component_labels": [{
        "layer": "numbers", "component_index": 0, "expected_bbox": [10, 10, 20, 30],
        "target_layer": "numbers", "family_id": "number:6", "label": "true_number",
    }]}]
    groups = [{"group_labels": [{
        "paint_label": "dirtlatemodel 350/car_num_x.tga", "group_id": "pdg:b",
        "target_layer": "sponsors",
    }]}]
    bank = attach_reviews(build_bank(inspection), components, groups)
    assert bank["summary"]["class_counts"] == {"numbers": 1, "sponsors": 1}
    assert bank["summary"]["casts_votes"] is False
    assert bank["summary"]["ownership_authority"] is False
    assert bank["source_content_count"] == 1
    assert {item["object_kind"] for item in bank["reviewed_objects"]} == {"singleton", "physical_group"}
    reviewed_by_kind = {item["object_kind"]: item for item in bank["reviewed_objects"]}
    assert reviewed_by_kind["singleton"]["review_label"] == "true_number"
    assert reviewed_by_kind["singleton"]["review_labels"] == ["true_number"]
    assert reviewed_by_kind["singleton"]["review_label_conflict"] is False
    assert reviewed_by_kind["physical_group"]["review_label"] is None
    assert reviewed_by_kind["singleton"]["review_target_proposal_fraction"] == 0.0
    assert reviewed_by_kind["singleton"]["review_target_proposal_support_state"] == "missing"
    assert reviewed_by_kind["physical_group"]["review_target_proposal_support_state"] == "supported"
    assert reviewed_by_kind["physical_group"]["physical_group_indicator"] == 1.0
    assert reviewed_by_kind["singleton"]["largest_member_fraction"] == 1.0
    assert reviewed_by_kind["physical_group"]["largest_member_fraction"] == 0.75
    assert reviewed_by_kind["physical_group"]["member_area_balance"] == 0.333333
    assert reviewed_by_kind["physical_group"]["member_fragmentation"] == 0.25
    assert reviewed_by_kind["singleton"]["group_completion_feature_available"] == 0.0
    assert reviewed_by_kind["singleton"]["group_largest_member_fraction"] == 0.0
    assert reviewed_by_kind["physical_group"]["group_completion_feature_available"] == 1.0
    assert reviewed_by_kind["physical_group"]["group_largest_member_fraction"] == 0.75
    assert reviewed_by_kind["physical_group"]["group_member_area_balance"] == 0.333333
    assert reviewed_by_kind["physical_group"]["group_member_fragmentation"] == 0.25
    assert bank["summary"]["review_label_counts"] == {"true_number": 1}
    assert bank["summary"]["review_target_proposal_support_counts"] == {
        "missing": 1, "supported": 1,
    }


def test_semantic_object_bank_ingests_exact_reviewed_singleton_instance_without_authority():
    semantic_objects = {
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        "records": [
            {"object_id": "sdo:singleton", "physical_group_id": None,
             "instance_ids": ["di:reviewed"], "bbox": [6, 8, 20, 12],
             "object_kind": "singleton"},
        ],
    }
    inspection = [{
        "paint_label": "paint",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "semantic_objects": semantic_objects,
        }}},
    }]
    reviews = [{"instance_labels": [{
        "paint_label": "paint", "instance_id": "di:reviewed", "bbox": [6, 8, 20, 12],
        "target_layer": "numbers", "family_id": "number:21", "label": "true_number",
    }]}]

    bank = attach_reviews(build_bank(inspection), reviews, [])

    assert bank["review_links"][0]["match_method"] == "exact_instance_id"
    assert bank["review_links"][0]["status"] == "matched_for_review"
    assert bank["reviewed_objects"][0]["review_target_layer"] == "numbers"
    assert bank["reviewed_objects"][0]["review_family_id"] == "number:21"
    assert bank["reviewed_objects"][0]["review_label"] == "true_number"
    assert bank["summary"]["casts_votes"] is False
    assert bank["summary"]["ownership_authority"] is False


def test_semantic_object_bank_prefers_exact_pixel_review_overlap(tmp_path):
    mask = np.zeros((40, 40), np.uint8)
    mask[10:20, 10:13] = 255
    mask[10:20, 17:20] = 255
    mask_path = tmp_path / "numbers.png"
    assert cv2.imwrite(str(mask_path), mask)
    left = np.ones((10, 3), bool)
    right = np.ones((10, 3), bool)
    semantic_objects = {
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        "records": [
            {"object_id": "sdo:left", "physical_group_id": None, "bbox": [10, 10, 3, 10],
             "object_kind": "singleton", "mask_rle": encode_instance_mask_rle(left)},
            {"object_id": "sdo:right", "physical_group_id": None, "bbox": [17, 10, 3, 10],
             "object_kind": "singleton", "mask_rle": encode_instance_mask_rle(right)},
        ],
    }
    inspection = [{
        "paint_label": "paint", "mask_paths": {"numbers": str(mask_path)},
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "semantic_objects": semantic_objects,
        }}},
    }]
    components = [{"paint_label": "paint", "component_labels": [{
        "layer": "numbers", "component_index": 0, "expected_bbox": [10, 10, 3, 10],
        "target_layer": "numbers",
    }]}]
    bank = attach_reviews(build_bank(inspection), components, [])
    link = bank["review_links"][0]
    assert link["object_id"] == "sdo:left"
    assert link["match_method"] == "exact_pixel_overlap"
    assert link["best_overlap_min"] == 1.0


def test_compact_group_review_resolves_exact_audit_order(tmp_path):
    audit = {"paints": [{"paint_label": "paint", "groups": [
        {"group_id": "pdg:a"}, {"group_id": "pdg:b"},
    ]}]}
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(__import__("json").dumps(audit), encoding="utf-8")
    objects = {
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        "records": [
            {"object_id": "sdo:a", "physical_group_id": "pdg:a", "bbox": [0, 0, 1, 1]},
            {"object_id": "sdo:b", "physical_group_id": "pdg:b", "bbox": [1, 0, 1, 1]},
        ],
    }
    inspection = [{"paint_label": "paint", "route_adjudicator_shadow": {
        "candidate_evidence": {"decal_instances": {"semantic_objects": objects}},
    }}]
    compact = {"physical_group_audit": str(audit_path), "paint_group_targets": {
        "paint": ["numbers", "sponsors"],
    }}
    bank = attach_reviews(build_bank(inspection), [], [compact])
    assert bank["summary"]["class_counts"] == {"numbers": 1, "sponsors": 1}
