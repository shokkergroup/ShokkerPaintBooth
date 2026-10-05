from __future__ import annotations

import numpy as np

from _forge_surface_pixel_repair import partition_support, preserve_surface_boundary, preserve_surface_edges


def test_semantic_repair_partition_is_disjoint_and_complete() -> None:
    support = np.ones((5, 8), dtype=bool)
    number = np.zeros((5, 8), dtype=np.uint8); number[:, :2] = 255
    sponsor = np.zeros((5, 8), dtype=np.uint8); sponsor[:, 1:5] = 255
    output = partition_support(support, number, sponsor, ["paint", "sponsor", "number"])
    assert output["number"].sum() == 10
    assert output["sponsor"].sum() == 15
    assert output["paint"].sum() == 15
    assert np.all(sum(mask.astype(np.uint8) for mask in output.values()) == 1)


def test_paint_only_surface_keeps_all_supported_pixels_editable() -> None:
    support = np.eye(6, dtype=bool)
    output = partition_support(support, np.zeros((6, 6), np.uint8), np.zeros((6, 6), np.uint8), ["paint"])
    assert np.array_equal(output["paint"], support)
    assert not output["number"].any()
    assert not output["sponsor"].any()


def test_optional_boundary_preservation_protects_shared_seam_band() -> None:
    surface = np.zeros((11, 13), dtype=bool)
    surface[1:10, 2:12] = True
    support = surface.copy()
    protected = preserve_surface_boundary(support, surface, 2)
    assert protected.sum() == 5 * 6
    assert not protected[1:3].any()
    assert not protected[:, 2:4].any()


def test_zero_boundary_preservation_keeps_original_support() -> None:
    surface = np.ones((4, 7), dtype=bool)
    support = np.eye(4, 7, dtype=bool)
    assert np.array_equal(preserve_surface_boundary(support, surface, 0), support)


def test_declared_uv_edge_preservation_does_not_erase_other_edges() -> None:
    surface = np.zeros((8, 10), dtype=bool)
    surface[1:7, 2:9] = True
    protected = preserve_surface_edges(surface, surface, [{"edge": "top", "width_px": 2}])
    assert not protected[1:3, 2:9].any()
    assert protected[3:7, 2:9].all()
