from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

import _forge_layers
from _forge_surface_semantic_landmark_audit import measure_alpha, semantic_alpha


def test_measure_alpha_normalizes_longitudinal_direction() -> None:
    alpha = np.zeros((100, 100), dtype=bool)
    alpha[20:60, 25:65] = True
    contract = {"bbox": [0, 0, 100, 100], "upright_rotation_deg": 0}
    wheel = {"center_x": 20, "radius_x": 10.0}
    forward = measure_alpha(alpha, contract, wheel, 1.0)
    reverse = measure_alpha(alpha, contract, wheel, -1.0)
    assert forward["wheel_relative_x"] == [0.5, 4.5]
    assert reverse["wheel_relative_x"] == [-4.5, -0.5]
    assert forward["uv_height_over_wheel_radius_x"] == 4.0


def test_measure_alpha_inverts_calibrated_car_space_extent() -> None:
    alpha = np.zeros((100, 100), dtype=bool)
    alpha[20:60, 25:65] = True
    normal = {"bbox": [0, 0, 100, 100], "upright_rotation_deg": 0, "car_space_extent": {"x_min": -0.5, "x_max": 1.5}}
    rotated = {**normal, "upright_rotation_deg": 180}
    wheel = {"center_x": 20, "radius_x": 10.0}
    assert measure_alpha(alpha, normal, wheel, 1.0)["car_space_x"] == [0.0, 0.8]
    assert measure_alpha(alpha, rotated, wheel, -1.0)["car_space_x"] == [0.0, 0.8]


def test_measure_alpha_inverts_calibrated_vertical_car_space_extent() -> None:
    alpha = np.zeros((100, 100), dtype=bool)
    alpha[20:60, 25:65] = True
    contract = {
        "bbox": [0, 0, 100, 100],
        "upright_rotation_deg": 0,
        "car_space_extent": {"x_min": -0.5, "x_max": 1.5, "y_bottom": 0.0, "y_top": 0.5},
    }
    wheel = {"center_x": 20, "radius_x": 10.0}
    assert measure_alpha(alpha, contract, wheel, 1.0)["car_space_y"] == [0.2, 0.4]


def test_semantic_alpha_reads_named_psd_leaves(tmp_path: Path) -> None:
    image = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    for y in range(5, 11):
        for x in range(7, 15):
            image.putpixel((x, y), (255, 255, 255, 255))
    psd_path = tmp_path / "semantic.psd"
    _forge_layers.write_grouped_psd([{"name": "NUMBERS", "layers": [("Door 13", image)]}], image, str(psd_path))
    alpha = semantic_alpha(tmp_path, {"psd": "semantic.psd", "layer_names": ["Door 13"]}, (24, 24))
    assert int(alpha.sum()) == 48
