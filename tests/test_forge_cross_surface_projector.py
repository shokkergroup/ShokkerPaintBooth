from __future__ import annotations

import numpy as np
from PIL import Image

from _forge_cross_surface_projector import crop_fragments, project_crop


def test_crop_fragments_recomposes_exact_source_without_gap_or_overlap() -> None:
    image = Image.new("RGBA", (10, 4), (0, 0, 0, 0))
    for x in range(10):
        for y in range(4):
            image.putpixel((x, y), (x * 20, y * 30, 100, 255))
    fragments = [
        {"surface": "side", "source_x_fraction": [0.0, 0.7], "car_space_box": [0.7, 0.1, 1.0, 0.2]},
        {"surface": "fender", "source_x_fraction": [0.7, 1.0], "car_space_box": [1.0, 0.1, 1.2, 0.2]},
    ]
    crops, proof = crop_fragments(image, fragments)
    assert proof == {"gap_columns": 0, "overlap_columns": 0, "source_recomposition_differing_pixels": 0, "source_recomposition_max_channel_error": 0, "valid": True}
    assert [row["source_crop_box"] for row in crops] == [[0, 0, 7, 4], [7, 0, 10, 4]]


def test_project_crop_honors_owner_rotation_and_full_mask() -> None:
    crop = Image.new("RGBA", (6, 4), (255, 255, 255, 255))
    contract = {
        "bbox": [0, 0, 20, 10], "upright_rotation_deg": 180,
        "car_space_extent": {"x_min": 0.0, "x_max": 1.0, "y_bottom": 0.0, "y_top": 0.5},
    }
    allowed = np.ones((10, 20), dtype=bool)
    rendered, proof = project_crop(crop, {"car_space_box": [0.2, 0.1, 0.6, 0.4]}, contract, allowed)
    assert rendered.size == (20, 10)
    assert proof["rotation_deg"] == 180
    assert proof["outside_pixels"] == 0
    assert proof["valid"]


def test_project_crop_abstains_instead_of_clipping() -> None:
    crop = Image.new("RGBA", (6, 4), (255, 255, 255, 255))
    contract = {
        "bbox": [0, 0, 20, 10], "upright_rotation_deg": 0,
        "car_space_extent": {"x_min": 0.0, "x_max": 1.0, "y_bottom": 0.0, "y_top": 0.5},
    }
    allowed = np.ones((10, 20), dtype=bool); allowed[:, 10:] = False
    _rendered, proof = project_crop(crop, {"car_space_box": [0.2, 0.1, 0.8, 0.4]}, contract, allowed)
    assert proof["outside_pixels"] > 0
    assert not proof["valid"]
