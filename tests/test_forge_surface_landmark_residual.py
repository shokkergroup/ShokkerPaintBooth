from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

import _forge_layers
from _forge_surface_landmark_residual import car_space_x_span, car_space_y_span, detect_wheel_arch, load_exemplar, oriented_box_to_uv, safe_cap_band, trim_transparent, wheel_relative_x_span


def _side_mask(width: int, height: int, center: int, radius: int, arch_top: int) -> np.ndarray:
    mask = np.ones((height, width), dtype=bool)
    yy, xx = np.ogrid[:height, :width]
    wheel = ((xx - center) / radius) ** 2 + ((yy - (arch_top + radius)) / radius) ** 2 <= 1.0
    mask[wheel & (yy >= arch_top)] = False
    return mask


def test_wheel_arch_detection_is_surface_specific() -> None:
    left = detect_wheel_arch(_side_mask(300, 120, 185, 35, 48), (0.15, 0.85), 6.0)
    right = detect_wheel_arch(_side_mask(300, 120, 95, 30, 36), (0.15, 0.85), 6.0)
    assert abs(left["center_x"] - 185) <= 2
    assert abs(right["center_x"] - 95) <= 2
    assert abs(left["radius_x"] - 35) <= 5
    assert abs(right["radius_x"] - 30) <= 5
    assert left["arch_top"] >= 45
    assert right["arch_top"] >= 33


def test_rearward_selection_chooses_first_confident_arch() -> None:
    mask = _side_mask(360, 140, 70, 28, 45)
    yy, xx = np.ogrid[:140, :360]
    second = ((xx - 245) / 48) ** 2 + ((yy - 88) / 48) ** 2 <= 1.0
    mask[second & (yy >= 40)] = False
    rear = detect_wheel_arch(mask, (0.02, 0.90), 6.0, selection="rearward")
    deepest = detect_wheel_arch(mask, (0.02, 0.90), 6.0, selection="deepest")
    assert abs(rear["center_x"] - 70) <= 3
    assert abs(deepest["center_x"] - 245) <= 3


def test_oriented_box_maps_through_180_degree_island() -> None:
    normal = {"bbox": [10, 20, 110, 80], "upright_rotation_deg": 0}
    rotated = {"bbox": [10, 20, 110, 80], "upright_rotation_deg": 180}
    assert oriented_box_to_uv([20, 10, 50, 30], normal) == [30, 30, 60, 50]
    assert oriented_box_to_uv([20, 10, 50, 30], rotated) == [60, 50, 90, 70]


def test_wheel_relative_span_honors_surface_longitudinal_direction() -> None:
    assert wheel_relative_x_span(100, 20, -1.0, 2.0, 1.0) == (80, 140)
    assert wheel_relative_x_span(100, 20, -1.0, 2.0, -1.0) == (60, 120)


def test_car_space_span_uses_surface_extent_and_owner_rotation() -> None:
    normal = {"bbox": [0, 0, 200, 100], "upright_rotation_deg": 0, "car_space_extent": {"x_min": 0.0, "x_max": 1.0}}
    rotated = {**normal, "upright_rotation_deg": 180}
    box = [0.2, 0.0, 0.6, 1.0]
    assert car_space_x_span(box, normal) == (40, 120)
    assert car_space_x_span(box, rotated) == (80, 160)


def test_car_space_y_span_is_in_oriented_surface_coordinates() -> None:
    surface = {"bbox": [0, 0, 200, 100], "car_space_extent": {"y_bottom": 0.0, "y_top": 0.5}}
    assert car_space_y_span([0.0, 0.1, 1.0, 0.4], surface) == (20, 80)


def test_load_exemplar_reads_named_editable_psd_leaf(tmp_path: Path) -> None:
    image = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    image.putpixel((9, 8), (255, 255, 255, 255))
    psd_path = tmp_path / "candidate.psd"
    _forge_layers.write_grouped_psd([{"name": "NUMBERS", "layers": [("Door 13", image)]}], image, str(psd_path))
    loaded, source_path, label = load_exemplar(tmp_path, {"exemplar_psd": "candidate.psd", "exemplar_layer": "Door 13"})
    assert source_path == psd_path
    assert label.endswith("candidate.psd::Door 13")
    assert np.asarray(loaded)[:, :, 3].sum() == 255


def test_safe_cap_uses_shallowest_arch_boundary_across_art_span() -> None:
    mask = np.ones((100, 120), dtype=bool)
    mask[55:, 35:55] = False
    mask[38:, 55:80] = False
    top, bottom = safe_cap_band(mask, 35, 80, gap_run=6)
    assert top == 0
    assert bottom == 38


def test_safe_cap_ignores_tiny_disconnected_edge_sliver() -> None:
    mask = np.zeros((100, 60), dtype=bool)
    mask[:3, :] = True
    mask[20:58, :] = True
    top, bottom = safe_cap_band(mask, 5, 55, gap_run=6)
    assert (top, bottom) == (20, 58)


def test_safe_cap_prefers_dominant_body_over_qualifying_edge_sliver() -> None:
    mask = np.zeros((100, 60), dtype=bool)
    mask[:15, :] = True
    mask[20:80, :] = True
    assert safe_cap_band(mask, 5, 55, gap_run=6) == (20, 80)


def test_safe_cap_can_follow_evidence_derived_vertical_band() -> None:
    mask = np.zeros((100, 60), dtype=bool)
    mask[5:25, :] = True
    mask[60:95, :] = True
    assert safe_cap_band(mask, 5, 55, gap_run=6, run_selection="nearest_target", target_center=18) == (5, 25)
    assert safe_cap_band(mask, 5, 55, gap_run=6, run_selection="nearest_target", target_center=82) == (60, 95)


def test_trim_transparent_returns_visible_crop_and_provenance_bbox() -> None:
    image = Image.new("RGBA", (40, 30))
    image.putpixel((7, 9), (255, 255, 255, 255))
    image.putpixel((18, 20), (255, 255, 255, 255))
    trimmed, bbox = trim_transparent(image)
    assert bbox == [7, 9, 19, 21]
    assert trimmed.size == (12, 12)
