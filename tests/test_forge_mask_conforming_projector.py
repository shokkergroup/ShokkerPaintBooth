from __future__ import annotations

import numpy as np
from PIL import Image

from _forge_mask_conforming_projector import conform_columns


def _contract(rotation: int = 0) -> dict:
    return {"bbox": [0, 0, 20, 12], "upright_rotation_deg": rotation}


def test_column_mesh_moves_pixels_inside_without_changing_pixel_multiset() -> None:
    image = Image.new("RGBA", (20, 12), (0, 0, 0, 0))
    for x in range(5, 15):
        for y in range(7, 10): image.putpixel((x, y), (x * 5, y * 9, 120, 255))
    allowed = np.ones((12, 20), dtype=bool); allowed[7:, 8:12] = False
    output, proof = conform_columns(image, _contract(), allowed, max_shift=6, max_adjacent_delta=3)
    assert proof["valid"]
    assert proof["outside_pixels"] == 0
    assert proof["pixel_multiset_equal"]
    assert np.asarray(output)[:, :, 3].astype(bool).sum() == 30


def test_column_mesh_abstains_when_no_contained_translation_exists() -> None:
    image = Image.new("RGBA", (20, 12), (255, 255, 255, 255))
    allowed = np.zeros((12, 20), dtype=bool); allowed[:2] = True
    _output, proof = conform_columns(image, _contract(), allowed, max_shift=4, max_adjacent_delta=3)
    assert not proof["valid"]
    assert proof["failed_columns"]


def test_column_mesh_honors_180_degree_stored_orientation() -> None:
    image = Image.new("RGBA", (20, 12), (0, 0, 0, 0)); image.putpixel((2, 8), (255, 0, 0, 255))
    allowed = np.ones((12, 20), dtype=bool); allowed[8:, 2] = False
    _output, proof = conform_columns(image, _contract(180), allowed, max_shift=6, max_adjacent_delta=3)
    assert proof["valid"]
    assert proof["pixel_multiset_equal"]
