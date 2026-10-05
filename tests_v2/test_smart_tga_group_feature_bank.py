import pytest

from scripts.smart_tga_group_feature_bank import (
    build_bank,
    load_documents,
    load_review_documents,
)


def test_group_feature_bank_stays_non_authoritative_and_requires_coverage():
    inspection = [{
        "paint_label": "dirtlatemodel 350/car_num_x.tga",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "physical_groups": {"features": {"records": [{"group_id": "pdg:a", "fill_ratio": 0.4}]}}
        }}},
    }]
    review = {"group_labels": [{
        "paint_label": "dirtlatemodel 350/car_num_x.tga",
        "group_id": "pdg:a",
        "target_layer": "numbers",
    }]}
    bank = build_bank(inspection, review)
    assert bank["records"][0]["review_target_layer"] == "numbers"
    assert bank["summary"]["class_feature_means"]["numbers"]["fill_ratio"] == 0.4
    assert bank["summary"]["calibration_ready"] is False
    assert "minimum_review_coverage:numbers" in bank["summary"]["calibration_blockers"]
    assert bank["summary"]["casts_votes"] is False
    assert bank["summary"]["ownership_authority"] is False


def test_group_feature_bank_can_merge_corpus_shards(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text('[{"paint_label":"a"}]', encoding="utf-8")
    second.write_text('[{"paint_label":"b"}]', encoding="utf-8")
    assert [item["paint_label"] for item in load_documents([str(first), str(second)])] == ["a", "b"]

    labels = tmp_path / "labels.json"
    labels.write_text('{"group_labels":[{"paint_label":"a","group_id":"pdg:a"}]}', encoding="utf-8")
    assert load_documents([str(labels)], list_key="group_labels")[0]["group_id"] == "pdg:a"


def test_group_feature_bank_joins_audited_ordered_reviews(tmp_path):
    inspection = [{
        "paint_label": "dirtlatemodel 358/car_num_x.tga",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "physical_groups": {"features": {"records": [
                {"group_id": "pdg:a", "fill_ratio": 0.8},
                {"group_id": "pdg:b", "fill_ratio": 0.2},
            ]}}
        }}},
    }]
    labels = tmp_path / "ordered.json"
    labels.write_text(
        '{"casts_votes":false,"ownership_authority":false,'
        '"paint_group_targets":{"dirtlatemodel 358/car_num_x.tga":'
        '["numbers","paint"]}}',
        encoding="utf-8",
    )
    review = load_review_documents([str(labels)])
    bank = build_bank(inspection, review)
    assert [row["review_target_layer"] for row in bank["records"]] == ["numbers", "paint"]
    assert bank["summary"]["reviewed_record_count"] == 2
    assert bank["summary"]["casts_votes"] is False

    review["paint_group_targets"]["dirtlatemodel 358/car_num_x.tga"] = ["numbers"]
    with pytest.raises(ValueError, match="ordered review count mismatch"):
        build_bank(inspection, review)


def test_group_feature_bank_adds_owner_neutral_shape_topology():
    inspection = [{
        "paint_label": "dirtlatemodel 350/car_num_shape.tga",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "physical_groups": {"features": {"records": [
                {"group_id": "pdg:shape", "fill_ratio": 0.5},
            ]}},
            "semantic_objects": {"records": [{
                "physical_group_id": "pdg:shape",
                "shape_occupancy": [
                    0, 0, 0, 0,
                    0, 1, 1, 0,
                    0, 1, 1, 0,
                    0, 0, 0, 0,
                ],
            }]},
        }}},
    }]
    review = {"group_labels": [{
        "paint_label": "dirtlatemodel 350/car_num_shape.tga",
        "group_id": "pdg:shape", "target_layer": "numbers",
    }]}
    row = build_bank(inspection, review)["records"][0]
    assert row["shape_occupancy_mean"] == 0.25
    assert row["shape_horizontal_symmetry"] == 1.0
    assert row["shape_vertical_symmetry"] == 1.0
    assert row["shape_center_edge_delta"] == 1.0
    assert row["shape_adjacent_transition"] > 0
