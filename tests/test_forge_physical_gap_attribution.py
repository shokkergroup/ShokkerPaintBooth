import numpy as np

from _forge_physical_gap_attribution import attribute_gap, compare_pair


def test_gap_causes_are_disjoint_and_recompose_the_full_gap():
    source = np.ones((2, 6), bool)
    support = np.zeros_like(source)
    support[:, :2] = True
    x_ok = np.zeros_like(source)
    x_ok[:, :5] = True
    rect_ok = np.zeros_like(source)
    rect_ok[:, :4] = True
    proof, masks = attribute_gap(source, [support], x_ok, rect_ok)
    assert proof["longitudinal_extent_gap_pixels"] == 2
    assert proof["vertical_extent_gap_pixels"] == 2
    assert proof["interior_contour_gap_pixels"] == 4
    assert proof["gap_pixels"] == 8 and proof["gap_accounting_exact"]
    assert np.array_equal(masks["longitudinal"] | masks["vertical"] | masks["contour"], source & ~support)


def test_fully_supported_asset_has_zero_attributed_gap():
    source = np.array([[1, 0], [1, 1]], bool)
    full = np.ones_like(source)
    proof, _masks = attribute_gap(source, [full], full, full)
    assert proof["supported_pixels"] == 3
    assert proof["gap_pixels"] == 0 and proof["valid"]


def test_paired_cause_gate_accepts_matching_sides_and_rejects_asymmetry():
    left = {"source_pixels": 100, "supported_pixels": 60, "longitudinal_extent_gap_pixels": 20, "vertical_extent_gap_pixels": 15, "interior_contour_gap_pixels": 5}
    close = {"source_pixels": 200, "supported_pixels": 118, "longitudinal_extent_gap_pixels": 42, "vertical_extent_gap_pixels": 30, "interior_contour_gap_pixels": 10}
    far = {"source_pixels": 100, "supported_pixels": 20, "longitudinal_extent_gap_pixels": 60, "vertical_extent_gap_pixels": 15, "interior_contour_gap_pixels": 5}
    assert compare_pair(left, close, 0.03)["valid"]
    assert not compare_pair(left, far, 0.10)["valid"]
