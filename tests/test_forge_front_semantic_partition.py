import numpy as np

from _forge_front_semantic_partition import infer_seam_row, partition_front_elements


def test_seam_row_is_inferred_from_strongest_corridor_edge():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[55:] = 220
    evidence = infer_seam_row(image, 50, 40, 40, 70)
    assert evidence["row_y_px"] in (54, 55)
    assert evidence["peak_to_median_ratio"] > 2


def test_disjoint_hood_and_nose_with_supported_seam_passes():
    elements = [
        {"id": "valance", "physical_instance_id": "front_valance", "surface": "nose", "placement_top_y_px": 500, "placement_bottom_y_px": 550},
        {"id": "logo", "physical_instance_id": "hood_logo", "surface": "hood", "placement_top_y_px": 250, "placement_bottom_y_px": 450},
    ]
    proof = partition_front_elements(elements, 550, 500, 475)
    assert proof["valid"]
    assert proof["cross_surface_overlaps"] == []


def test_duplicate_instance_or_overlap_rejects_partition():
    elements = [
        {"id": "a", "physical_instance_id": "same_art", "surface": "nose", "placement_top_y_px": 450, "placement_bottom_y_px": 550},
        {"id": "b", "physical_instance_id": "same_art", "surface": "hood", "placement_top_y_px": 250, "placement_bottom_y_px": 470},
    ]
    proof = partition_front_elements(elements, 550, 500, 460)
    assert not proof["valid"]
    assert proof["duplicate_physical_instance_ids"] == ["same_art"]
    assert proof["cross_surface_overlaps"]
