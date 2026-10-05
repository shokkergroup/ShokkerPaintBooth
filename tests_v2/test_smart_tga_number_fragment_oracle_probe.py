from scripts.smart_tga_number_fragment_oracle_probe import _greedy_oracle_members, probe


def _inspection(records):
    return [{
        "paint_label": "dirtlatemodel 358/car_num_test.tga",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "features": {"records": records}
        }}},
    }]


def _annotations():
    return {"instances": [{
        "paint_label": "dirtlatemodel 358/car_num_test.tga",
        "family_id": "number:23", "copy": "upper_side",
        "bbox": [100, 100, 100, 100], "status": "missing_final_number",
    }]}


def test_oracle_combines_contained_disjoint_fragments():
    records = [
        {"instance_id": "left", "bbox": [100, 100, 35, 100], "proposed_owners": ["brand_graphics"]},
        {"instance_id": "right", "bbox": [165, 100, 35, 100], "proposed_owners": ["sponsors"]},
        {"instance_id": "outside", "bbox": [300, 300, 50, 50], "proposed_owners": ["template"]},
    ]
    result = probe(_inspection(records), _annotations())
    assert result["single_complete_recall"] == 0.0
    assert result["oracle_assembled_complete_recall"] == 1.0
    assert result["oracle_envelope_complete_recall"] == 1.0
    assert result["records"][0]["oracle_member_ids"] == ["left", "right"]
    assert result["records"][0]["oracle_fragment_union_coverage"] == 0.7
    assert result["records"][0]["oracle_fragment_envelope_bbox"] == [100, 100, 100, 100]


def test_oracle_rejects_huge_containing_panel():
    records = [
        {"instance_id": "panel", "bbox": [0, 0, 400, 400], "proposed_owners": ["paint"]},
        {"instance_id": "digit", "bbox": [100, 100, 20, 80], "proposed_owners": ["brand_graphics"]},
    ]
    members, coverage = _greedy_oracle_members(records, [100, 100, 100, 100])
    assert [member["instance_id"] for member in members] == ["digit"]
    assert coverage == 0.16
