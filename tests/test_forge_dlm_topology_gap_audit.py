import numpy as np
import pytest

from _forge_dlm_topology_gap_audit import TopologyGapAuditError, analyze_arrays


def test_gap_audit_reports_unowned_official_pixels_and_component_order():
    labels = np.array([[1, 1, 2], [1, 3, 2], [4, 4, 2]], dtype=np.uint16)
    official = np.ones((3, 3), dtype=bool)
    first = np.array([[1, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=np.uint8)
    second = np.array([[0, 0, 0], [0, 2, 0], [0, 0, 0]], dtype=np.uint8)
    result = analyze_arrays(labels, official, [first, second])
    assert result["covered_official_pixels"] == 4
    assert result["missing_official_pixels"] == 5
    assert result["cross_registry_overlap_pixels"] == 0
    assert [row["component_id"] for row in result["missing_components"]] == [2, 4]
    assert result["missing_components"][0]["missing_official_pixels"] == 3


def test_gap_audit_counts_cross_registry_overlap():
    labels = np.ones((2, 2), dtype=np.uint16)
    official = np.ones((2, 2), dtype=bool)
    a = np.array([[1, 0], [0, 0]], dtype=np.uint8)
    b = np.array([[2, 0], [0, 0]], dtype=np.uint8)
    result = analyze_arrays(labels, official, [a, b])
    assert result["cross_registry_overlap_pixels"] == 1


def test_gap_audit_rejects_mismatched_shapes():
    with pytest.raises(TopologyGapAuditError, match="index_shape_mismatch"):
        analyze_arrays(np.zeros((2, 2)), np.zeros((2, 2), dtype=bool), [np.zeros((3, 3))])
