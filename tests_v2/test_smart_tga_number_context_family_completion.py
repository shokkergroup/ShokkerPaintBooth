import numpy as np

from engine.spec_sculpt.number_context_family_completion import family_completion_candidates


def test_nearby_fragments_assemble_without_owner_authority():
    numbers = np.zeros((64, 64), bool)
    sponsors = np.zeros_like(numbers)
    numbers[20:35, 10:18] = True
    sponsors[20:35, 22:30] = True
    components = [
        {"layer": "numbers", "component_index": 4, "bbox": [10, 20, 8, 15]},
        {"layer": "sponsors", "component_index": 9, "bbox": [22, 20, 8, 15]},
    ]
    proposals = family_completion_candidates(
        numbers.shape, {"numbers": numbers, "sponsors": sponsors}, components,
        min_atom_pixels=10, min_group_pixels=20,
    )
    assert proposals
    proposal = proposals[0]
    assert proposal["proposal_bbox"] == [10, 20, 20, 15]
    assert proposal["member_count"] == 2
    assert {item["source_layer"] for item in proposal["member_provenance"]} == {"numbers", "sponsors"}
    assert proposal["owner_neutral"] is True
    assert proposal["ownership_authority"] is False
    assert proposal["assembly_authority"] is False
    assert proposal["raw_support"].flags.writeable is False


def test_distant_atoms_do_not_form_a_family():
    mask = np.zeros((128, 128), bool)
    mask[5:15, 5:15] = True
    mask[100:110, 100:110] = True
    components = [
        {"layer": "numbers", "component_index": 0, "bbox": [5, 5, 10, 10]},
        {"layer": "numbers", "component_index": 1, "bbox": [100, 100, 10, 10]},
    ]
    assert family_completion_candidates(
        mask.shape, {"numbers": mask}, components, min_atom_pixels=10, min_group_pixels=20,
    ) == ()
