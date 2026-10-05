import hashlib
from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_seeded_component_propagation import (
    build_component_graph,
    json_sha256,
    propagate_seeded_components,
    verify_file,
)


RULES = {
    "max_wire_gap_px": 3.0,
    "minimum_shared_boundary_support_px": 3,
    "minimum_component_candidate_fraction": 0.95,
    "minimum_competing_seed_cost_margin": 3.0,
    "maximum_propagation_cost": 20.0,
    "boundary_support_penalty": 3.0,
}


def _three_components():
    labels = np.zeros((24, 42), dtype=np.uint16)
    labels[6:18, 2:10] = 1
    labels[6:18, 12:20] = 2
    labels[6:18, 28:36] = 3
    return labels


def _graph(labels):
    return build_component_graph(
        labels,
        max_wire_gap_px=RULES["max_wire_gap_px"],
        minimum_shared_boundary_support_px=RULES["minimum_shared_boundary_support_px"],
        boundary_support_penalty=RULES["boundary_support_penalty"],
    )


def test_supported_small_gap_propagates_but_large_island_gap_stops():
    labels = _three_components()
    candidate = np.isin(labels, [1, 2, 3])
    result = propagate_seeded_components(labels, _graph(labels), {"surface_a": candidate}, {"surface_a": [1]}, RULES)
    assert result["assignments"][1]["status"] == "SEED"
    assert result["assignments"][2]["status"] == "PROPAGATED"
    assert result["assignments"][3] == {"status": "ABSTAIN", "reason": "unseeded_or_disconnected"}


def test_no_cross_surface_leakage_even_when_graph_has_an_edge():
    labels = np.zeros((24, 36), dtype=np.uint16)
    labels[6:18, 2:10] = 1
    labels[6:18, 12:20] = 2
    labels[6:18, 22:30] = 3
    left = np.isin(labels, [1])
    right = np.isin(labels, [2, 3])
    result = propagate_seeded_components(
        labels, _graph(labels), {"left": left, "right": right}, {"left": [1], "right": [3]}, RULES
    )
    assert result["assignments"][1]["surface_id"] == "left"
    assert result["assignments"][2]["surface_id"] == "right"
    assert result["assignments"][2]["status"] == "PROPAGATED"
    assert all(
        assignment.get("surface_id") != "left"
        for value, assignment in result["assignments"].items() if value != 1
    )


def test_surface_overlap_and_seed_conflict_abstain():
    labels = _three_components()
    both = np.isin(labels, [1, 2])
    result = propagate_seeded_components(
        labels, _graph(labels), {"surface_a": both, "surface_b": both},
        {"surface_a": [1], "surface_b": [1]}, RULES,
    )
    assert result["assignments"][1] == {"status": "ABSTAIN", "reason": "seed_surface_conflict"}
    assert result["assignments"][2] == {"status": "ABSTAIN", "reason": "candidate_surface_overlap"}
    assert result["accepted_seeds"] == {"surface_a": set(), "surface_b": set()}


def test_weak_boundary_support_does_not_create_edge():
    labels = np.zeros((18, 24), dtype=np.uint16)
    labels[2:12, 2:10] = 1
    labels[13:15, 11:13] = 2
    graph = build_component_graph(
        labels, max_wire_gap_px=3.0, minimum_shared_boundary_support_px=4, boundary_support_penalty=3.0
    )
    assert graph["edges"] == []
    assert graph["metrics"]["rejected_weak_support_pair_count"] >= 1


def test_missing_and_hash_mismatch_fail_closed(tmp_path: Path):
    owner = tmp_path / "job.json"
    owner.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="topology_file_missing"):
        verify_file(owner, {"path": "none.json", "sha256": "0" * 64}, "topology")
    source = tmp_path / "topology.json"
    source.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="topology_sha256_mismatch"):
        verify_file(owner, {"path": source.name, "sha256": "0" * 64}, "topology")
    correct = hashlib.sha256(source.read_bytes()).hexdigest()
    assert verify_file(owner, {"path": source.name, "sha256": correct}, "topology") == source


def test_deterministic_graph_propagation_and_hash():
    labels = _three_components()
    candidate = np.isin(labels, [1, 2, 3])
    first_graph = _graph(labels)
    second_graph = _graph(labels.copy())
    assert first_graph["edges"] == second_graph["edges"]
    first = propagate_seeded_components(labels, first_graph, {"surface_a": candidate}, {"surface_a": [1]}, RULES)
    second = propagate_seeded_components(labels.copy(), second_graph, {"surface_a": candidate.copy()}, {"surface_a": [1]}, dict(RULES))
    comparable_first = {"assignments": first["assignments"], "dropped": first["dropped_seeds"]}
    comparable_second = {"dropped": second["dropped_seeds"], "assignments": second["assignments"]}
    assert comparable_first == comparable_second
    assert json_sha256(comparable_first) == json_sha256(comparable_second)
