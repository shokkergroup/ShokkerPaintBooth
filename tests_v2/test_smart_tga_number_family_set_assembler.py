import numpy as np

from scripts.smart_tga_number_family_set_assembler import (
    _assemble, _assemble_from_reviewed_anchor,
)


def _rows():
    return [
        {
            "paint": "p", "block": "upper", "candidate_index": offset,
            "proposal_id": f"proposal-{offset}",
            "placement_fingerprint_for_instance_dedupe": fingerprint,
            "support_area_for_metrics_only": 10,
            "anchor_review_code": "A0",
            "semantic": semantic, "complete_copy": complete,
        }
        for offset, (fingerprint, semantic, complete) in enumerate((
            ("seed", "Number", True),
            ("fragment", "Number", False),
            ("fragment", "Number", False),
            ("weak-false", "Sponsor", None),
        ))
    ]


def _data():
    return {
        "keys": np.asarray(["p|upper"] * 4),
        "family_score": np.asarray([0.99, 0.96, 0.95, 0.80]),
    }


def test_family_assembly_preserves_baseline_and_adds_independently_nominated_fragment():
    baseline = np.asarray([True, False, False, False])
    complete_probability = np.asarray([0.95, 0.20, 0.10, 0.05])
    accepted, sets = _assemble(
        _rows(), np.arange(4), _data(), baseline, complete_probability,
        seed_complete_threshold=0.90, fragment_score_threshold=0.90,
        fragment_cap=4,
    )
    # The duplicate proposal support is one immutable placed instance, and the
    # weak Sponsor cannot be admitted by relationship alone.
    assert accepted.tolist() == [True, True, False, False]
    assert np.all(accepted[baseline])
    assert len(sets) == 1
    assert sets[0]["fragments"] == [1]


def test_relationship_cannot_create_family_without_baseline_complete_seed():
    baseline = np.asarray([False, False, False, False])
    complete_probability = np.asarray([0.99, 0.20, 0.10, 0.05])
    accepted, sets = _assemble(
        _rows(), np.arange(4), _data(), baseline, complete_probability,
        seed_complete_threshold=0.90, fragment_score_threshold=0.90,
        fragment_cap=4,
    )
    assert not accepted.any()
    assert sets == []


def test_low_completeness_baseline_candidate_cannot_seed_fragment_expansion():
    baseline = np.asarray([True, False, False, False])
    complete_probability = np.asarray([0.70, 0.20, 0.10, 0.05])
    accepted, sets = _assemble(
        _rows(), np.arange(4), _data(), baseline, complete_probability,
        seed_complete_threshold=0.90, fragment_score_threshold=0.90,
        fragment_cap=4,
    )
    assert accepted.tolist() == baseline.tolist()
    assert sets == []


def test_direct_reviewed_cross_block_anchor_can_group_only_independently_nominated_fragments():
    baseline = np.asarray([True, False, False, False])
    complete_probability = np.asarray([0.95, 0.20, 0.10, 0.05])
    accepted, sets = _assemble_from_reviewed_anchor(
        _rows(), np.arange(4), _data(), baseline, complete_probability,
        fragment_score_threshold=0.90, fragment_complete_max=0.50,
        fragment_cap=4,
    )
    assert accepted.tolist() == [True, True, False, False]
    assert sets[0]["anchor_review_code"] == "A0"
    assert sets[0]["fragments"] == [1]


def test_cross_block_anchor_cannot_rescue_fragment_below_frozen_family_threshold():
    baseline = np.asarray([True, False, False, False])
    complete_probability = np.asarray([0.95, 0.20, 0.10, 0.05])
    accepted, sets = _assemble_from_reviewed_anchor(
        _rows(), np.arange(4), _data(), baseline, complete_probability,
        fragment_score_threshold=0.97, fragment_complete_max=0.50,
        fragment_cap=4,
    )
    assert accepted.tolist() == baseline.tolist()
    assert sets == []


def test_review_certainty_is_veto_only_for_new_anchor_nominated_members():
    baseline = np.asarray([True, False, False, False])
    complete_probability = np.asarray([0.95, 0.20, 0.10, 0.05])
    certainty_probability = np.asarray([0.10, 0.85, 0.40, 0.99])
    accepted, _ = _assemble_from_reviewed_anchor(
        _rows(), np.arange(4), _data(), baseline, complete_probability,
        fragment_score_threshold=0.90, fragment_complete_max=0.50,
        fragment_cap=4, certainty_probability=certainty_probability,
        certainty_min=0.80,
    )
    # The low-certainty duplicate and weak semantic false stay out; the low
    # baseline certainty cannot revoke the already-safe seed.
    assert accepted.tolist() == [True, True, False, False]
