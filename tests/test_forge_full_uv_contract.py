from __future__ import annotations

import numpy as np

from _forge_full_uv_contract import (
    assign_full_uv_surfaces,
    audit_full_uv_coverage,
    derive_official_wire_regions,
    validate_front_artwork_authority,
)


def _wire_canvas() -> np.ndarray:
    wire = np.zeros((24, 32, 4), dtype=np.uint8)
    # Green outer UV boundary.
    wire[4, 5:20] = (0, 255, 0, 255)
    wire[16, 5:20] = (0, 255, 0, 255)
    wire[4:17, 5] = (0, 255, 0, 255)
    wire[4:17, 19] = (0, 255, 0, 255)
    # White internal mesh must not split the physical UV region.
    wire[5:16, 12] = (255, 255, 255, 255)
    return wire


def test_official_regions_use_green_outer_wire_not_white_mesh():
    official, labels, regions = derive_official_wire_regions(
        _wire_canvas(), minimum_region_pixels=4
    )
    assert len(regions) == 1
    assert official[8, 8]
    assert official[8, 16]
    assert official[8, 12]  # white mesh stays inside coverage
    assert not official[2, 2]
    assert labels.shape == official.shape


def test_coverage_audit_exposes_missing_and_outside_pixels():
    official, labels, regions = derive_official_wire_regions(
        _wire_canvas(), minimum_region_pixels=4
    )
    adapter = np.zeros_like(official)
    adapter[5:16, 6:12] = True
    adapter[0:2, 0:2] = True
    report = audit_full_uv_coverage(
        official, labels, regions, adapter, large_region_pixels=4
    )
    assert 0.0 < report["official_coverage_recall"] < 1.0
    assert report["missing_official_pixels"] > 0
    assert report["outside_official_pixels"] == 4
    assert report["large_wire_region_status_counts"]["partial"] == 1


def test_front_authority_rejects_duplicate_hidden_behind_distinct_physical_ids():
    duplicate = validate_front_artwork_authority(
        [
            {"id": "hood_brand", "surface": "hood", "physical_instance_id": "p1", "semantic_authority_id": "front_brand"},
            {"id": "nose_brand", "surface": "nose", "physical_instance_id": "p2", "semantic_authority_id": "front_brand"},
        ]
    )
    assert not duplicate["valid"]
    assert duplicate["invalid_cross_surface_authorities"][0]["semantic_authority_id"] == "front_brand"


def test_front_authority_allows_one_declared_cross_surface_split():
    split = validate_front_artwork_authority(
        [
            {"id": "hood_fragment", "surface": "hood", "semantic_authority_id": "front_brand", "split_group_id": "front_brand_seam", "placement_mode": "cross_surface_split"},
            {"id": "nose_fragment", "surface": "nose", "semantic_authority_id": "front_brand", "split_group_id": "front_brand_seam", "placement_mode": "cross_surface_split"},
        ]
    )
    assert split["valid"]


def test_surface_assignment_expands_only_within_same_official_region():
    official = np.zeros((12, 24), dtype=bool)
    official[2:10, 2:11] = True
    official[2:10, 14:22] = True
    authority = {
        "$schema": "shokk-forge.dlm-surface-authority/v1",
        "coordinate_space": [24, 12],
        "surfaces": {
            "first": {"official_label": "FIRST", "label_seed_bbox": [3, 3, 5, 5], "envelope_bbox": [2, 2, 6, 10], "stored_orientation": "normal"},
            "second": {"official_label": "SECOND", "label_seed_bbox": [15, 3, 17, 5], "envelope_bbox": [14, 2, 18, 10], "stored_orientation": "normal"},
        },
    }
    surfaces, _, report = assign_full_uv_surfaces(official, authority)
    assert report["assigned_official_fraction"] == 1.0
    assert surfaces["first"][8, 10]
    assert not surfaces["first"][8, 20]
    assert surfaces["second"][8, 20]
    assert report["post_resolution_surface_overlap_pixels"] == 0
