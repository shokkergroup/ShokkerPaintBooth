from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families


def test_nested_hypotheses_become_one_owner_neutral_family_without_mutation():
    proposals = [
        {"proposal_id": "outer", "proposal_bbox": [10, 10, 40, 30], "provenance": {"q": 0.9}},
        {"proposal_id": "inner", "proposal_bbox": [14, 14, 30, 20], "provenance": {"q": 0.98}},
        {"proposal_id": "distant", "proposal_bbox": [100, 80, 20, 20], "provenance": {"q": 0.95}},
    ]
    before = [dict(item) for item in proposals]
    families = assemble_nested_proposal_families(proposals)
    assert len(families) == 2
    nested = next(item for item in families if item["member_count"] == 2)
    assert nested["member_ids"] == ("inner", "outer")
    assert nested["owner_neutral"] and not nested["casts_votes"] and not nested["ownership_authority"]
    assert proposals == before


def test_invalid_containment_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        assemble_nested_proposal_families([], 0.0)
