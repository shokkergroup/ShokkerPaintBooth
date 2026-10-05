from pathlib import Path

import numpy as np
from PIL import Image

from _forge_semantic_stack_partition import flatten_stack, load_job, partition_stack


def _save(path: Path, array: np.ndarray) -> None:
    Image.fromarray(array, "RGBA").save(path)


def test_flatten_stack_obeys_bottom_to_top_order(tmp_path: Path) -> None:
    bottom = np.zeros((12, 16, 4), dtype=np.uint8)
    bottom[2:10, 2:14] = (200, 20, 20, 255)
    top = np.zeros_like(bottom)
    top[4:8, 6:10] = (20, 40, 220, 255)
    _save(tmp_path / "bottom.png", bottom)
    _save(tmp_path / "top.png", top)
    merged = np.asarray(flatten_stack([tmp_path / "bottom.png", tmp_path / "top.png"], (16, 12)))
    assert tuple(merged[3, 3]) == (200, 20, 20, 255)
    assert tuple(merged[5, 7]) == (20, 40, 220, 255)


def test_partition_stack_is_lossless_and_keeps_stationary_pixels(tmp_path: Path) -> None:
    canvas = np.zeros((20, 30, 4), dtype=np.uint8)
    canvas[2:18, 2:28] = (40, 50, 60, 255)
    canvas[6:12, 8:18] = (240, 210, 20, 255)
    _save(tmp_path / "mixed.png", canvas)
    report = partition_stack(
        {
            "id": "side",
            "sources": ["mixed.png"],
            "max_semantic_fraction": 0.40,
            "regions": [
                {
                    "id": "logo",
                    "semantic_group": "sponsors",
                    "boxes": [[8, 6, 18, 12]],
                    "min_visible_pixels": 50,
                }
            ],
        },
        tmp_path / "out",
        tmp_path,
    )
    assert report["valid"]
    assert report["partition_rgba_exact"]
    assert report["recomposition_differing_pixels"] == 0
    assert report["selected_semantic_pixels"] == 60
    assert report["stationary_pixels"] == 356


def test_partition_stack_rejects_semantic_region_that_consumes_panel(tmp_path: Path) -> None:
    canvas = np.full((10, 20, 4), (20, 30, 40, 255), dtype=np.uint8)
    _save(tmp_path / "panel.png", canvas)
    report = partition_stack(
        {
            "id": "side",
            "sources": ["panel.png"],
            "max_semantic_fraction": 0.25,
            "regions": [
                {"id": "too_broad", "semantic_group": "sponsors", "boxes": [[0, 0, 15, 10]]}
            ],
        },
        tmp_path / "out",
        tmp_path,
    )
    assert not report["valid"]
    assert report["semantic_fraction"] == 0.75
    assert report["recomposition_differing_pixels"] == 0


def test_partition_stack_rejects_overlapping_semantic_boxes(tmp_path: Path) -> None:
    canvas = np.full((10, 20, 4), (20, 30, 40, 255), dtype=np.uint8)
    _save(tmp_path / "panel.png", canvas)
    report = partition_stack(
        {
            "id": "side",
            "sources": ["panel.png"],
            "max_semantic_fraction": 0.90,
            "regions": [
                {"id": "one", "semantic_group": "sponsors", "boxes": [[0, 0, 8, 8]]},
                {"id": "two", "semantic_group": "sponsors", "boxes": [[6, 6, 14, 10]]},
            ],
        },
        tmp_path / "out",
        tmp_path,
    )
    assert not report["valid"]
    assert report["regions"][1]["rejected_overlap_pixels"] == 4


def test_connected_color_selector_keeps_panel_background_stationary(tmp_path: Path) -> None:
    canvas = np.zeros((30, 50, 4), dtype=np.uint8)
    canvas[2:28, 2:48] = (235, 190, 20, 255)
    canvas[8:22, 12:18, :3] = 5
    canvas[8:22, 28:35, :3] = 5
    _save(tmp_path / "wordmark.png", canvas)
    report = partition_stack(
        {
            "id": "side",
            "sources": ["wordmark.png"],
            "max_semantic_fraction": 0.25,
            "regions": [
                {
                    "id": "dark_glyphs",
                    "semantic_group": "sponsors",
                    "selector": "connected_color",
                    "boxes": [[5, 5, 42, 25]],
                    "max_rgb": 30,
                    "min_component_area": 40,
                }
            ],
        },
        tmp_path / "out",
        tmp_path,
    )
    assert report["valid"]
    assert report["selected_semantic_pixels"] == 182
    assert report["stationary_pixels"] == (26 * 46) - 182


def test_ring_median_recovers_occluded_panel_without_changing_canonical_composite(tmp_path: Path) -> None:
    canvas = np.full((40, 60, 4), (12, 14, 18, 255), dtype=np.uint8)
    canvas[12:28, 20:40] = (230, 40, 30, 255)
    _save(tmp_path / "decal.png", canvas)
    report = partition_stack(
        {
            "id": "side",
            "sources": ["decal.png"],
            "max_semantic_fraction": 0.25,
            "background_recovery": {
                "mode": "ring_median",
                "ring_px": 5,
                "min_samples": 20,
                "max_channel_mad": 5,
            },
            "regions": [
                {"id": "tile", "semantic_group": "sponsors", "boxes": [[20, 12, 40, 28]]}
            ],
        },
        tmp_path / "out",
        tmp_path,
    )
    assert report["valid"]
    assert report["partition_rgba_exact"]
    assert report["recomposition_differing_pixels"] == 0
    assert report["background_recovery_valid"]
    assert report["background_recovered_pixels"] == 320
    stationary = np.asarray(Image.open(report["stationary_remainder"]["path"]).convert("RGBA"))
    assert tuple(stationary[18, 30]) == (12, 14, 18, 255)


def test_load_job_applies_stack_override_by_stable_id(tmp_path: Path) -> None:
    (tmp_path / "base.json").write_text(
        '{"stacks":[{"id":"left","surface":"left_strip","regions":[{"id":"wordmark","semantic_group":"sponsors"}]}]}', encoding="utf-8"
    )
    (tmp_path / "revision.json").write_text(
        '{"extends":"base.json","stack_overrides":{"left":{"background_recovery":{"mode":"ring_median"},"region_overrides":{"wordmark":{"semantic_group":"incomplete_fragments"}}}}}',
        encoding="utf-8",
    )
    loaded = load_job(tmp_path / "revision.json", tmp_path)
    assert loaded["stacks"][0]["surface"] == "left_strip"
    assert loaded["stacks"][0]["background_recovery"]["mode"] == "ring_median"
    assert loaded["stacks"][0]["regions"][0]["semantic_group"] == "incomplete_fragments"
