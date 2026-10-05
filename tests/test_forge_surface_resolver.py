from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import _forge_surface_resolver as resolver


def _save_shape(path: Path, size: tuple[int, int], points: list[tuple[int, int]]) -> None:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(image).polygon(points, fill=(180, 20, 30, 255))
    image.save(path)


def _asset(path: Path, asset_id: str, bbox: list[float]) -> dict:
    with Image.open(path) as opened:
        size = list(opened.size)
    return {
        "id": asset_id,
        "path": str(path),
        "sha256": resolver._sha256(path),
        "size": size,
        "area_pixels": size[0] * size[1],
        "usable_for_projection": True,
        "sheet_role": "panel_art_1",
        "source_bbox_normalized": bbox,
    }


def _defs() -> dict:
    rows = {
        "left_strip": (1310, 430, "side_strip", "left", 180),
        "right_strip": (1310, 310, "side_strip", "right", 0),
        "left_front_fender": (326, 450, "front_fender", "left", 180),
        "right_front_fender": (380, 410, "front_fender", "right", 0),
        "hood": (330, 570, "top_surface", "center", 90),
        "nose": (300, 640, "top_surface", "center", 90),
        "rear_deck_lid": (490, 720, "top_surface", "center", 90),
        "roof": (425, 480, "top_surface", "center", 0),
        "spoiler_inside": (670, 85, "spoiler", "center", 180),
        "spoiler_outside": (670, 75, "spoiler", "center", 0),
    }
    return {surface: {"surface": surface, "family": family, "side": side, "width": w, "height": h, "area": w * h, "long_aspect": max(w / h, h / w), "orientation_deg": orientation, "bbox": [0, 0, w, h], "stored": None} for surface, (w, h, family, side, orientation) in rows.items()}


def test_strong_left_right_exemplars_accept_family_but_not_exact_surface(tmp_path: Path) -> None:
    path = tmp_path / "side.png"
    _save_shape(path, (420, 100), [(4, 80), (390, 10), (416, 90), (10, 98)])
    asset = _asset(path, "source-01", [0.0, 0.0, 0.9, 0.3])
    match = {
        "fields": {"role": {"value": "decal"}},
        "neighbors": [
            {"metadata": {"surface": "left_strip"}, "local_good_matches": 24, "confidence": 0.91, "exemplar_id": "left"},
            {"metadata": {"surface": "right_strip"}, "local_good_matches": 22, "confidence": 0.90, "exemplar_id": "right"},
        ],
    }
    _, geometry = resolver._alpha_canvas(path)
    result = resolver.resolve_source(asset, geometry, _defs(), 0.27, match, None, None)
    assert result["accepted_family"] == "side_strip"
    assert result["accepted_surface"] is None
    assert result["side_options"] == ["left", "right"]
    assert result["orientation_options"] == [0, 180]


def test_largest_mirrored_pair_accepts_joint_side_family(tmp_path: Path) -> None:
    first_path, second_path = tmp_path / "a.png", tmp_path / "b.png"
    points = [(3, 50), (380, 5), (410, 48), (10, 58)]
    _save_shape(first_path, (420, 60), points)
    _save_shape(second_path, (420, 60), [(420 - x, y) for x, y in points])
    assets = [_asset(first_path, "source-a", [0.0, 0.0, 0.95, 0.3]), _asset(second_path, "source-b", [0.0, 0.4, 0.95, 0.7])]
    features = {asset["id"]: resolver._alpha_canvas(Path(asset["path"])) for asset in assets}
    pairs, by_id = resolver._find_pairs(assets, features)
    assert len(pairs) == 1
    assert pairs[0]["largest_panel_pair"]
    assert pairs[0]["accepted_family"] == "side_strip"
    assert len(pairs[0]["joint_surface_assignments"]) == 2
    result = resolver.resolve_source(assets[0], features["source-a"][1], _defs(), 0.285, None, None, by_id["source-a"])
    assert result["accepted_family"] == "side_strip"
    assert result["accepted_surface"] is None


def test_geometry_alone_ranks_but_does_not_promote(tmp_path: Path) -> None:
    path = tmp_path / "geometry.png"
    _save_shape(path, (260, 120), [(5, 100), (120, 5), (255, 95), (140, 115)])
    asset = _asset(path, "source-01", [0.1, 0.1, 0.5, 0.4])
    _, geometry = resolver._alpha_canvas(path)
    result = resolver.resolve_source(asset, geometry, _defs(), 0.4, None, None, None)
    assert result["surface_candidates"]
    assert result["accepted_family"] is None
    assert result["accepted_surface"] is None
    assert result["abstention"]


def test_dossier_owner_orientation_law_is_loaded(tmp_path: Path) -> None:
    truth = {}
    for surface, definition in _defs().items():
        truth[surface] = {"bbox": definition["bbox"], "stored": "test"}
    path = tmp_path / "panel_map.json"
    path.write_text(__import__("json").dumps({"template_truth": truth}), encoding="utf-8")
    definitions = resolver.load_surface_defs(path)
    assert definitions["left_strip"]["orientation_deg"] == 180
    assert definitions["right_strip"]["orientation_deg"] == 0
    assert definitions["hood"]["orientation_deg"] == 90
    assert definitions["rear_deck_lid"]["orientation_deg"] == 90
    assert definitions["roof"]["orientation_deg"] == 0
