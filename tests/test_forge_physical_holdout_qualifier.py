import numpy as np
import pytest

from _forge_physical_holdout_qualifier import (
    car_space_x,
    physical_box_from_reference,
    qualify_source_domain,
    qualify_span,
)


def test_wheelbase_coordinates_are_orientation_independent():
    forward = car_space_x(np.array([100, 200]), 100, 200)
    reversed_view = car_space_x(np.array([200, 100]), 200, 100)
    assert np.allclose(forward, [0, 1])
    assert np.allclose(reversed_view, [0, 1])


def test_span_requires_real_evidence_on_both_sides_of_margin():
    proof = qualify_span(np.array([0.8] * 10 + [1.2] * 12), 1.0, 0.05, 10)
    assert proof["spans_seam"] and proof["pixels_below_seam_margin"] == 10
    near_only = qualify_span(np.array([0.99] * 20 + [1.01] * 20), 1.0, 0.05, 1)
    assert not near_only["spans_seam"]


def test_reference_box_uses_wheelbase_for_both_axes_without_view_guessing():
    left = physical_box_from_reference([40, 20, 81, 61], 100, 0, 60)
    right = physical_box_from_reference([20, 20, 61, 61], 0, 100, 60)
    assert left == [0.6, 0.0, 0.2, 0.4]
    assert right == [0.2, 0.0, 0.6, 0.4]
    assert sorted([left[0], left[2]]) == sorted([right[0], right[2]])


def test_empty_or_one_sided_evidence_abstains():
    assert not qualify_span(np.array([0.2, 0.3, 0.4]), 1.0, 0.01, 1)["spans_seam"]
    with pytest.raises(ValueError):
        car_space_x(np.array([1]), 10, 10)


def test_uv_layer_cannot_pose_as_physical_holdout():
    with pytest.raises(ValueError, match="direct physical evidence"):
        qualify_source_domain("uv_layer")
