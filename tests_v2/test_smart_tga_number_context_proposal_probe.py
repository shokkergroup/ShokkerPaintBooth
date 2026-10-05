from scripts.smart_tga_number_context_proposal_probe import (
    _apply_prototype,
    _relative_transform,
    generate_context_proposals,
)


def test_relative_transform_reconstructs_review_bbox():
    seed = [100, 100, 20, 40]
    review = [80, 90, 80, 80]
    prototype = _relative_transform(seed, review)
    rebuilt = _apply_prototype(seed, prototype)
    assert rebuilt == review


def test_context_proposals_preserve_provenance_and_zero_authority():
    candidates = [{
        "instance_id": "di:seed", "bbox": [100, 100, 20, 40],
        "area_fraction": 0.001,
    }]
    proposals = generate_context_proposals(candidates, [[0.0, 0.0, 0.0, 0.0]])
    assert proposals == [{
        "bbox": [100, 100, 20, 40],
        "seed_instance_id": "di:seed",
        "prototype_index": 0,
        "source": "number_context_envelope_shadow",
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }]
