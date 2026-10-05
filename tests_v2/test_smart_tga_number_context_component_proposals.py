import numpy as np

from engine.spec_sculpt.number_context_component_proposals import component_area_fraction, component_proposal_candidates


def test_component_adapter_is_layer_neutral_immutable_and_deterministic():
    masks = {"numbers": np.zeros((12, 14), bool), "template": np.zeros((12, 14), bool)}
    masks["numbers"][2:8, 3:9] = True
    masks["template"][7:11, 8:13] = True
    components = [
        {"layer": "template", "component_index": 2, "bbox": [8, 7, 5, 4]},
        {"layer": "numbers", "component_index": 1, "bbox": [3, 2, 6, 6]},
    ]
    first = component_proposal_candidates((12, 14), masks, components, min_pixels=10)
    second = component_proposal_candidates((12, 14), masks, components, min_pixels=10)
    assert len(first) == 2
    assert [item["proposal_id"] for item in first] == [item["proposal_id"] for item in second]
    assert {item["provenance"]["source_layer"] for item in first} == {"numbers", "template"}
    assert all(item["owner_neutral"] and not item["ownership_authority"] for item in first)
    assert all(item["raw_support"].flags.writeable is False for item in first)
    assert component_area_fraction(first[1]["raw_support"], (12, 14)) == 36 / (12 * 14)


def test_component_adapter_does_not_absorb_a_neighbor_inside_its_bbox():
    mask = np.zeros((16, 16), bool)
    mask[2:10, 2:10] = True
    mask[3:9, 3:9] = False
    mask[5:7, 5:7] = True
    components = [{
        "layer": "numbers", "component_index": 0,
        "bbox": [2, 2, 8, 8], "area_px": 28,
    }]
    proposal = component_proposal_candidates(
        mask.shape, {"numbers": mask}, components, min_pixels=1,
    )[0]
    assert proposal["raw_support"].shape == (8, 8)
    assert proposal["raw_support"].sum() == 28
    assert proposal["provenance"]["component_pixels"] == 28
