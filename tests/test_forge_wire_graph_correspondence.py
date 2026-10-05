from __future__ import annotations

import math

import cv2
import numpy as np

from _forge_wire_graph_correspondence import (
    GraphNode,
    MatchConfig,
    canonical_sha256,
    extract_graph_nodes,
    match_piecewise_graphs,
)


def _node(prefix: str, index: int, xy, component: int, *, signature=None, kind="junction", degree=4):
    if signature is None:
        signature = (1.0, degree / 8.0, 0.08 * index, 0.04 * index, 0.02 * index, 0.01 * index)
    return GraphNode(f"{prefix}{index}", float(xy[0]), float(xy[1]), kind, degree, component, tuple(signature), 1.0)


def _warp(points, matrix):
    points = np.asarray(points, np.float64)
    homogeneous = np.c_[points, np.ones(len(points))]
    mapped = homogeneous @ np.asarray(matrix, np.float64).T
    return mapped[:, :2] / mapped[:, 2:3]


def test_extracts_endpoint_and_junction_nodes():
    skeleton = np.zeros((80, 80), np.uint8)
    cv2.line(skeleton, (10, 40), (70, 40), 1, 1)
    cv2.line(skeleton, (40, 10), (40, 40), 1, 1)
    nodes = extract_graph_nodes(skeleton, max_nodes=20, min_component_pixels=8)
    assert any(node.kind == "junction" for node in nodes)
    assert sum(node.kind == "endpoint" for node in nodes) >= 3


def test_known_piecewise_perspective_recovers_held_out_nodes():
    base_a = [(10, 10), (70, 12), (68, 55), (12, 58), (42, 35), (28, 28)]
    base_b = [(120, 20), (175, 18), (180, 70), (118, 72), (148, 44), (162, 52)]
    h_a = [[1.2, 0.08, 24], [0.03, 0.95, 13], [0.0005, 0.0002, 1]]
    h_b = [[0.9, -0.05, 40], [0.08, 1.1, 5], [0.0002, 0.0004, 1]]
    target_a = _warp(base_a, h_a)
    target_b = _warp(base_b, h_b)
    source = []
    target = []
    for component, (base, mapped) in enumerate(((base_a, target_a), (base_b, target_b)), 1):
        for index, (src_xy, dst_xy) in enumerate(zip(base, mapped)):
            # First four are unique topology seeds; final two intentionally share
            # a signature and must be recovered by geometric consensus.
            component_offset = component * 0.65
            signature = (
                (1.0, 0.5, component_offset + index * 0.18, index * 0.11, index * 0.07, index * 0.03)
                if index < 4
                else (1.0, 0.5, 0.77, 0.77, 0.77, 0.77)
            )
            source.append(_node(f"s{component}_", index, src_xy, component, signature=signature))
            target.append(_node(f"t{component}_", index, dst_xy, component + 10, signature=signature))
    result = match_piecewise_graphs(source, target, MatchConfig(projection_radius=2.0, min_projection_margin=0.4))
    assert result["accepted_match_count"] == 12
    held_out = [match for match in result["matches"] if match["source_node"].endswith(("4", "5"))]
    assert len(held_out) == 4
    assert max(match["residual"] for match in held_out) < 0.01
    assert all(component["status"] == "ACCEPT_SPARSE_HYPOTHESIS" for component in result["components"])


def test_repeated_ambiguous_graph_abstains():
    signature = (1.0, 0.5, 0.2, 0.2, 0.2, 0.2)
    source = [_node("s", i, (i * 10, 0), 1, signature=signature) for i in range(6)]
    target = [_node("t", i, (i * 10 + 5, 20), 2, signature=signature) for i in range(6)]
    result = match_piecewise_graphs(source, target)
    assert result["accepted_match_count"] == 0
    assert result["seed_count"] == 0
    assert result["components"][0]["reason"] == "NO_UNIQUE_TOPOLOGY_SEEDS"


def test_reflected_mapping_is_rejected():
    points = [(10, 10), (70, 10), (70, 60), (10, 60), (40, 30)]
    source = [_node("s", i, xy, 1) for i, xy in enumerate(points)]
    reflected = [(110 - x, y + 20) for x, y in points]
    target = [_node("t", i, xy, 2) for i, xy in enumerate(reflected)]
    result = match_piecewise_graphs(source, target)
    assert result["accepted_match_count"] == 0
    assert result["components"][0]["reason"] == "REFLECTION_OR_DEGENERATE"


def test_high_residual_mapping_abstains():
    points = [(0, 0), (100, 0), (100, 100), (0, 100), (50, 50), (25, 75)]
    target_points = [(0, 0), (100, 0), (100, 100), (0, 100), (85, 20), (10, 95)]
    source = [_node("s", i, xy, 1) for i, xy in enumerate(points)]
    target = [_node("t", i, xy, 2) for i, xy in enumerate(target_points)]
    cfg = MatchConfig(ransac_reprojection_threshold=100.0, max_median_residual=1.0, max_residual=2.0)
    result = match_piecewise_graphs(source, target, cfg)
    assert result["accepted_match_count"] == 0
    assert result["components"][0]["reason"] == "HIGH_RESIDUAL"


def test_output_hash_is_deterministic_and_claims_stay_false():
    points = [(0, 0), (30, 0), (30, 30), (0, 30), (15, 15)]
    source = [_node("s", i, xy, 1) for i, xy in enumerate(points)]
    target = [_node("t", i, (xy[0] + 7, xy[1] + 11), 2) for i, xy in enumerate(points)]
    first = match_piecewise_graphs(source, target)
    second = match_piecewise_graphs(source, target)
    assert first == second
    assert first["deterministic_hash"] == second["deterministic_hash"]
    assert first["deterministic_hash"] == canonical_sha256({key: value for key, value in first.items() if key != "deterministic_hash"})
    assert not any(first["claims"].values())

