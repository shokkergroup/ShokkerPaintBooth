import numpy as np

from _forge_dlm_staged_side_envelope_completion import complete_arrays


def test_side_completion_extends_only_inside_polygon_and_yields_to_other_owners():
    base = np.zeros((8, 8), dtype=np.uint8)
    base[4:7, 1:5] = 3
    base[2, 5] = 4
    official = np.ones((8, 8), dtype=bool)
    higher = np.zeros((8, 8), dtype=bool); higher[3, 5] = True
    specs = [{"surface_id": "left_side", "surface_index": 3, "uv_polygon_xy": [[1, 1], [6, 1], [6, 7], [1, 7]], "authority": "test"}]
    result, rows = complete_arrays(base, official, higher, specs)
    assert result[2, 5] == 4
    assert result[3, 5] == 0
    assert result[1, 1] == 3
    assert rows[0]["excluded_existing_owner_pixels"] == 1
    assert rows[0]["excluded_higher_authority_pixels"] == 1


def test_side_completion_preserves_native_pixels_outside_envelope():
    base = np.zeros((6, 6), dtype=np.uint8); base[0, 0] = 7
    official = np.ones((6, 6), dtype=bool); higher = np.zeros((6, 6), dtype=bool)
    specs = [{"surface_id": "right_side", "surface_index": 7, "uv_polygon_xy": [[2, 2], [5, 2], [5, 5], [2, 5]], "authority": "test"}]
    result, _ = complete_arrays(base, official, higher, specs)
    assert result[0, 0] == 7
