from scripts.smart_tga_missed_instance_candidate_probe import probe


def test_missed_instance_probe_separates_present_fragment_overbroad_and_absent_without_authority():
    inspections = [{
        "paint_label": "dirtlatemodel 358/car_num_x.tga",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "features": {"records": [
                {"instance_id": "di:whole", "bbox": [10, 10, 80, 80],
                 "proposed_owners": ["sponsors"], "source_stages": ["gpu_model"],
                 "edge_density": 0.25, "shape_occupancy": [0.5] * 16},
                {"instance_id": "di:fragment", "bbox": [210, 210, 40, 40],
                 "proposed_owners": ["paint"], "source_stages": ["raw"]},
                {"instance_id": "di:overbroad", "bbox": [300, 300, 200, 200],
                 "proposed_owners": ["paint"], "source_stages": ["raw"]},
            ]},
        }}}},
    ]
    annotations = {"instances": [
        {"paint_label": "dirtlatemodel 358/car_num_x.tga", "family_id": "number:12", "copy": "upper", "review_id": "whole", "bbox": [0, 0, 100, 100]},
        {"paint_label": "dirtlatemodel 358/car_num_x.tga", "family_id": "number:12", "copy": "lower", "review_id": "fragment", "bbox": [200, 200, 100, 100]},
        {"paint_label": "dirtlatemodel 358/car_num_x.tga", "family_id": "number:34", "copy": "upper", "review_id": "overbroad", "bbox": [350, 350, 20, 20]},
        {"paint_label": "dirtlatemodel 358/car_num_x.tga", "family_id": "number:34", "copy": "lower", "review_id": "absent", "bbox": [600, 600, 50, 50]},
    ]}
    report = probe(inspections, annotations)
    assert report["status_counts"] == {
        "candidate_present": 1, "candidate_fragment_only": 1,
        "candidate_overbroad": 1, "candidate_absent": 1,
    }
    by_id = {item["review_id"]: item for item in report["records"]}
    assert by_id["whole"]["best_instance_id"] == "di:whole"
    assert by_id["whole"]["best_proposed_owners"] == ["sponsors"]
    assert by_id["whole"]["best_instance_features"]["edge_density"] == 0.25
    assert by_id["whole"]["best_instance_features"]["shape_occupancy"] == [0.5] * 16
    assert by_id["fragment"]["best_review_coverage"] == 0.16
    assert by_id["overbroad"]["best_instance_id"] == "di:overbroad"
    assert by_id["overbroad"]["best_candidate_coverage"] == 0.01
    assert by_id["overbroad"]["best_candidate_to_review_area_ratio"] == 100.0
    assert by_id["absent"]["overlap_candidate_count"] == 0
    assert by_id["absent"]["best_instance_features"] == {}
    assert report["trainable_candidate_count"] == 3
    assert report["best_proposed_owner_path_counts"] == {"none": 1, "paint": 2, "sponsors": 1}
    assert report["best_source_stage_counts"] == {"gpu_model": 1, "raw": 2}
    assert report["reviewed_family_count"] == 2
    assert report["multi_copy_family_count"] == 2
    assert report["completion_supervision_ready_family_count"] == 1
    families = {item["family_id"]: item for item in report["family_records"]}
    assert families["number:12"]["copies"] == ["upper", "lower"]
    assert families["number:12"]["completion_supervision_ready"] is True
    assert families["number:34"]["completion_supervision_ready"] is False
    assert report["casts_votes"] is False
    assert report["ownership_authority"] is False
    assert report["adds_pixels"] is False
