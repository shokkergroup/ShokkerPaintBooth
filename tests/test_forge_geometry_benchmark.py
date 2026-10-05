import _forge_geometry_benchmark as geometry
import _forge_compose as compose
import numpy as np


def _panel_map():
    return {
        "orientation_deg": {
            "side_panel_upper": 180,
            "side_panel_lower": 0,
            "top_deck_interior": 90,
            "nose_front": 90,
            "rear_deck_lid": -90,
            "roof_number": 0,
        },
        "mined_orientation": {
            "place_upright_art_rotate": {"hood": 90, "nose": 90, "deck": 90, "roof": 0}
        },
        "decal_keepouts": {
            "right_strip_door_visible_x": [590, 1130],
            "left_strip_door_visible_upright_x": [180, 1310],
        },
        "template_truth": {
            "left_strip": {"bbox": [0, 285, 1310, 715]},
            "right_strip": {"bbox": [0, 1445, 1310, 1755]},
        },
    }


def test_dossier_contradiction_finds_stale_deck_rotation() -> None:
    rows = geometry.dossier_orientation_contradictions(_panel_map())
    assert rows == [
        {
            "orientation_key": "rear_deck_lid",
            "configured_deg": 270,
            "mined_deg": 90,
            "evidence": "mined_orientation.place_upright_art_rotate",
        }
    ]


def test_readable_keepout_converts_left_rot180_coordinates() -> None:
    panel_map = _panel_map()
    assert geometry.readable_front_keepout_x(panel_map, "right_strip") == 1130
    assert geometry.readable_front_keepout_x(panel_map, "left_strip") == 1130
    assert geometry.readable_front_keepout_x(panel_map, "roof") is None


def test_expected_surface_rotation_uses_mined_top_surface_truth() -> None:
    panel_map = _panel_map()
    assert geometry.expected_surface_rotation(panel_map, "left_strip") == 180
    assert geometry.expected_surface_rotation(panel_map, "right_strip") == 0
    assert geometry.expected_surface_rotation(panel_map, "rear_deck_lid") == 90
    assert geometry.expected_surface_rotation(panel_map, "unmapped_template_island") is None


def test_front_keepout_clips_readable_art_but_not_paint() -> None:
    panel_map = _panel_map()
    readable = np.full((5, 200, 4), 255, dtype=np.uint8)
    graphic = {"semantic": {"role": "decal", "surface": "right_strip"}}
    result = compose.clip_readable_front_keepout(readable.copy(), (1000, 1400), graphic, panel_map)
    assert np.all(result[:, :130, 3] == 255)
    assert np.all(result[:, 130:, 3] == 0)
    paint = {"semantic": {"role": "paint_shape", "surface": "right_strip"}}
    untouched = compose.clip_readable_front_keepout(readable.copy(), (1000, 1400), paint, panel_map)
    assert np.all(untouched[:, :, 3] == 255)
