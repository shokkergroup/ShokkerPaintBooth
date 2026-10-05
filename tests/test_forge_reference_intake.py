from pathlib import Path

from PIL import Image

import _forge_reference_intake as intake


def test_ocr_classification_extracts_multiple_view_evidence() -> None:
    primary, tags = intake.classify_ocr("PAGE 10 REAR VIEW / SPOILER / COLOR GUIDE LEFT SIDE VIEW TOP VIEW")
    assert primary == "left_profile"
    assert "rear_view" in tags
    assert "top_view" in tags
    assert "placement_guide" in tags


def test_ocr_classification_accepts_hyphenated_side_labels() -> None:
    assert intake.classify_ocr("LEFT-SIDE ORTHOGRAPHIC MASTER")[0] == "left_profile"
    assert intake.classify_ocr("RIGHT-SIDE VIEW MASTER")[0] == "right_profile"


def test_ocr_classification_handles_numbered_package_and_panel_graphics() -> None:
    assert intake.classify_ocr("PAGE 6 NUMBER 12 PACKAGE")[0] == "number_sheet"
    assert intake.classify_ocr("RIGHT-SIDE / HOOD / ROOF GRAPHICS")[0] == "panel_art_sheet"


def test_difference_hash_is_stable_and_visual() -> None:
    first = Image.new("RGB", (30, 20), "white")
    second = first.copy()
    for x in range(15, 30):
        for y in range(20):
            second.putpixel((x, y), (0, 0, 0))
    assert intake.difference_hash(first) == intake.difference_hash(first.copy())
    assert intake.difference_hash(first) != intake.difference_hash(second)


def test_palette_comparison_reports_exact_coverage() -> None:
    reference = [
        {"rgb": [200, 0, 0], "hex": "#C80000", "weight": 0.7},
        {"rgb": [0, 100, 20], "hex": "#006414", "weight": 0.3},
    ]
    delivered = [
        {"rgb": [200, 0, 0], "hex": "#C80000", "weight": 0.5},
        {"rgb": [0, 100, 20], "hex": "#006414", "weight": 0.5},
    ]
    result = intake.compare_palettes(reference, delivered)
    assert result["coverage_percent"] == 100.0
    assert result["weighted_mean_delta_e76"] == 0.0


def test_chromatic_palette_excludes_white_sheet_background() -> None:
    image = Image.new("RGB", (100, 100), "white")
    for x in range(20, 80):
        for y in range(30, 70):
            image.putpixel((x, y), (190, 10, 20))
    palette = intake.extract_palette([intake._chromatic_pixels(image, remove_border_background=True)], colors=2)
    assert palette
    assert palette[0]["rgb"][0] > 150
    assert palette[0]["rgb"][1] < 50


def test_blind_holdout_intake_does_not_require_or_open_delivery(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "blind_reference_pack"
    root.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 40), (180, 20, 30)).save(root / "ChatGPT Image 1.png")
    monkeypatch.setattr(intake, "_ocr", lambda _image: ("LEFT SIDE VIEW", 90.0))
    pack = intake.ingest_pack("blind_case", root, None)
    assert pack["blind_holdout"] is True
    assert pack["output_root"] is None
    assert pack["palette_match"]["checked"] is False
    assert pack["palette_match"]["reason"] == "blind_holdout_candidate_not_built"
    assert pack["source_count"] == 1


def test_intake_uses_supported_image_content_not_filename_prefix(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "mixed_export_names"
    root.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 40), (20, 70, 55)).save(root / "635692e4-4025-4143-801b-d5818cd8bb07.png")
    Image.new("RGB", (80, 40), (90, 20, 25)).save(root / "artist-reference.jpg")
    (root / "notes.txt").write_text("not an image", encoding="utf-8")
    monkeypatch.setattr(intake, "_ocr", lambda _image: ("TOP VIEW", 90.0))
    pack = intake.ingest_pack("arbitrary_names", root, None)
    assert pack["source_count"] == 2
    assert {row["filename"] for row in pack["sources"]} == {
        "635692e4-4025-4143-801b-d5818cd8bb07.png",
        "artist-reference.jpg",
    }


def test_composite_sheet_cannot_satisfy_direct_physical_view_coverage() -> None:
    composite = intake.qualify_view_evidence(
        "left_profile",
        ["left_profile", "right_profile", "front_view", "rear_view", "top_view"],
    )
    assert composite["direct_physical_view"] is None
    assert composite["evidence_scope"] == "composite_multiview_sheet"
    coverage = intake.summarize_view_coverage(
        [
            {
                "filename": "presentation.png",
                "evidence_tags": composite["core_view_tags"],
                **composite,
            }
        ]
    )
    assert coverage["mentioned_count"] == 5
    assert coverage["direct_count"] == 0


def test_dedicated_view_is_projection_qualified() -> None:
    qualified = intake.qualify_view_evidence("right_profile", ["right_profile", "brand_sheet"])
    assert qualified["direct_physical_view"] == "right_profile"
    assert qualified["projection_confidence"] == 1.0
