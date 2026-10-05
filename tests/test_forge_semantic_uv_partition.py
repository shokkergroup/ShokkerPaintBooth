from pathlib import Path

import numpy as np
from PIL import Image

from _forge_semantic_uv_partition import (
    bbox_mask,
    connected_color_mask,
    connected_light_mask,
    partition_source,
    validate_reference_evidence,
)


def test_bbox_mask_rejects_out_of_canvas_box() -> None:
    try:
        bbox_mask((10, 10), [[0, 0, 11, 5]])
    except ValueError as error:
        assert "outside source canvas" in str(error)
    else:
        raise AssertionError("invalid semantic bbox was accepted")


def test_connected_light_selects_two_large_digits_and_dilates_outline() -> None:
    rgba = np.zeros((80, 120, 4), dtype=np.uint8)
    rgba[10:70, 5:115, 3] = 255
    rgba[20:60, 20:45, :3] = 245
    rgba[20:60, 70:95, :3] = 245
    rgba[20:60, 20:45, 3] = 255
    rgba[20:60, 70:95, 3] = 255
    selected = connected_light_mask(
        rgba,
        {"bboxes": [[0, 0, 120, 80]], "min_component_area": 100, "keep_largest": 2, "dilate_px": 3},
    )
    assert selected[30, 30]
    assert selected[30, 80]
    assert selected[30, 17]
    assert not selected[5, 5]


def test_partition_recomposes_exactly(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    array = np.zeros((24, 32, 4), dtype=np.uint8)
    array[:, :, :] = (10, 30, 80, 255)
    array[4:18, 8:14, :3] = 240
    Image.fromarray(array, "RGBA").save(source)
    report = partition_source(
        source,
        {
            "id": "side",
            "regions": [{"id": "number", "semantic_group": "numbers", "selector": "bbox", "bboxes": [[6, 2, 16, 20]]}],
        },
        tmp_path / "out",
    )
    assert report["recomposition_differing_pixels"] == 0
    assert report["claimed_pixels"] == 180


def test_connected_color_component_envelopes_capture_decal_tiles_not_background() -> None:
    rgba = np.zeros((100, 160, 4), dtype=np.uint8)
    rgba[10:90, 10:150] = (235, 190, 15, 255)
    rgba[30:65, 35:50, :3] = 5
    rgba[30:65, 80:98, :3] = 5
    selected = connected_color_mask(
        rgba,
        {
            "bboxes": [[20, 20, 120, 75]],
            "max_rgb": 30,
            "min_component_area": 200,
            "max_component_area": 800,
            "keep_largest": 2,
            "envelope_padding_px": 5,
        },
    )
    assert selected[28, 32]
    assert selected[60, 100]
    assert not selected[25, 115]


def test_connected_color_can_reject_long_paint_stripes_by_aspect_ratio() -> None:
    rgba = np.zeros((80, 180, 4), dtype=np.uint8)
    rgba[5:75, 5:175] = (230, 185, 15, 255)
    rgba[20:24, 15:165, :3] = 5
    rgba[35:60, 50:68, :3] = 5
    rgba[35:60, 90:110, :3] = 5
    selected = connected_color_mask(
        rgba,
        {
            "bboxes": [[5, 5, 175, 75]],
            "max_rgb": 30,
            "min_component_area": 30,
            "max_component_aspect_ratio": 6.0,
        },
    )
    assert not selected[21, 40]
    assert selected[45, 58]
    assert selected[45, 100]


def test_partition_reports_overlapping_semantic_claims(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (20, 20), (20, 30, 40, 255)).save(source)
    report = partition_source(
        source,
        {
            "id": "overlap",
            "regions": [
                {"id": "first", "semantic_group": "numbers", "bboxes": [[0, 0, 12, 12]]},
                {"id": "second", "semantic_group": "sponsors", "bboxes": [[8, 8, 20, 20]]},
            ],
        },
        tmp_path / "out",
    )
    assert report["recomposition_differing_pixels"] == 0
    assert report["semantic_overlap_pixels"] == 16


def test_reference_evidence_is_hashed_and_never_used_as_artwork(tmp_path: Path) -> None:
    evidence = tmp_path / "brand.png"
    Image.new("RGB", (30, 20), "yellow").save(evidence)
    records = validate_reference_evidence(
        {
            "semantic_group": "sponsors",
            "reference_evidence": [{"source": "brand.png", "crop": [2, 3, 18, 15], "role": "brand wordmark"}],
        },
        tmp_path,
    )
    assert records[0]["source_size"] == [30, 20]
    assert len(records[0]["source_sha256"]) == 64
    assert records[0]["usage"] == "classification evidence only; pixels are not imported"


def test_reference_evidence_rejects_out_of_bounds_crop(tmp_path: Path) -> None:
    Image.new("RGB", (10, 10), "white").save(tmp_path / "brand.png")
    try:
        validate_reference_evidence(
            {"semantic_group": "sponsors", "reference_evidence": [{"source": "brand.png", "crop": [0, 0, 11, 5]}]},
            tmp_path,
        )
    except ValueError as error:
        assert "crop outside source" in str(error)
    else:
        raise AssertionError("out-of-bounds reference evidence crop was accepted")
