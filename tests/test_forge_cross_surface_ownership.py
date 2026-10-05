from __future__ import annotations

from _forge_cross_surface_ownership import split_box


SURFACES = {
    "side": {"car_space_extent": {"x_min": -0.6, "x_max": 1.01, "y_bottom": 0.0, "y_top": 0.30}},
    "fender": {"car_space_extent": {"x_min": 0.70, "x_max": 1.32, "y_bottom": 0.04, "y_top": 0.40}},
}
OWNERS = [{"surface": "side", "x_min": -0.6, "x_max": 1.0}, {"surface": "fender", "x_min": 1.0, "x_max": 1.32}]


def test_split_is_disjoint_and_recomposes_source_fraction() -> None:
    result = split_box([0.7, 0.05, 1.2, 0.25], OWNERS, SURFACES)
    assert result["valid"]
    assert [row["surface"] for row in result["fragments"]] == ["side", "fender"]
    assert result["gap_fraction"] == 0
    assert result["overlap_fraction"] == 0
    assert result["source_fraction_sum"] == 1
    assert result["fragments"][0]["source_x_fraction"] == [0.0, 0.6]
    assert result["fragments"][1]["source_x_fraction"] == [0.6, 1.0]


def test_split_abstains_on_topology_gap() -> None:
    owners = [{"surface": "side", "x_min": -0.6, "x_max": 0.9}, {"surface": "fender", "x_min": 1.0, "x_max": 1.32}]
    result = split_box([0.7, 0.05, 1.2, 0.25], owners, SURFACES)
    assert not result["valid"]
    assert result["gap_fraction"] == 0.2


def test_split_abstains_on_overlapping_ownership() -> None:
    owners = [{"surface": "side", "x_min": -0.6, "x_max": 1.1}, {"surface": "fender", "x_min": 1.0, "x_max": 1.32}]
    result = split_box([0.7, 0.05, 1.2, 0.25], owners, SURFACES)
    assert not result["valid"]
    assert result["overlap_fraction"] == 0.2


def test_split_abstains_when_adapter_cannot_contain_vertical_fragment() -> None:
    result = split_box([0.7, 0.01, 1.2, 0.25], OWNERS, SURFACES)
    assert not result["valid"]
    assert result["extent_failures"][0]["surface"] == "fender"
