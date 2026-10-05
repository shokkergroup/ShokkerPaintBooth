from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from _forge_dlm_render_pair_census import classify_image, decide_pair, pixel_sha256, sha256_file


def _structured_square() -> Image.Image:
    image = Image.new("RGB", (1024, 1024), "#19263a")
    draw = ImageDraw.Draw(image)
    for index in range(16):
        x = 20 + index * 60
        draw.rectangle((x, 100, x + 30, 920), fill=(20 + index * 10, 200 - index * 6, 70 + index * 5))
    draw.ellipse((250, 250, 750, 750), outline="white", width=22)
    return image


def _structured_wide() -> Image.Image:
    image = Image.new("RGB", (1280, 720), "#d7d9dd")
    draw = ImageDraw.Draw(image)
    draw.polygon([(100, 520), (250, 250), (980, 210), (1190, 520)], fill="#173a68")
    draw.rectangle((280, 300, 980, 520), fill="#e4472f")
    draw.ellipse((240, 440, 450, 650), fill="#121212", outline="white", width=8)
    draw.ellipse((850, 440, 1060, 650), fill="#121212", outline="white", width=8)
    for x in range(330, 930, 45):
        draw.line((x, 310, x + 80, 510), fill="white", width=7)
    return image


def test_flat_and_render_classification_comes_from_pixels_and_dimensions() -> None:
    flat = classify_image(_structured_square())
    render = classify_image(_structured_wide())
    assert flat["classification"] == "flat_uv_candidate"
    assert flat["confidence"] >= 0.94
    assert render["classification"] == "physical_render_candidate"
    assert render["confidence"] >= 0.91


def test_classification_is_unchanged_by_filename(tmp_path: Path) -> None:
    image = _structured_wide()
    first = tmp_path / "sponsor-car-name.jpg"
    second = tmp_path / "unrelated-label.jpg"
    image.save(first, quality=95)
    image.save(second, quality=95)
    with Image.open(first) as one, Image.open(second) as two:
        assert classify_image(one) == classify_image(two)


def test_low_confidence_or_ambiguous_pair_abstains() -> None:
    base = {
        "match_fraction": 0.06,
        "palette_similarity": 0.70,
        "combined_score": 0.75,
        "render_descriptor_count": 500,
        "flat_descriptor_count": 500,
    }
    result = decide_pair(
        [
            {"candidate_id": "a", "good_matches": 70, **base},
            {"candidate_id": "b", "good_matches": 66, **{**base, "combined_score": 0.72}},
        ]
    )
    assert result["decision"] == "ABSTAIN"
    assert "best_candidate_not_unique" in result["reasons"]
    assert "combined_score_margin_below_gate" in result["reasons"]


def test_insufficient_local_evidence_abstains_even_with_palette_match() -> None:
    result = decide_pair(
        [
            {
                "candidate_id": "only",
                "good_matches": 12,
                "match_fraction": 0.02,
                "palette_similarity": 0.95,
                "combined_score": 0.36,
                "render_descriptor_count": 500,
                "flat_descriptor_count": 500,
            }
        ]
    )
    assert result["decision"] == "ABSTAIN"
    assert "local_match_count_below_gate" in result["reasons"]


def test_file_and_decoded_pixel_hashes_are_deterministic(tmp_path: Path) -> None:
    image = _structured_square().resize((256, 256))
    first = tmp_path / "one.png"
    second = tmp_path / "two.png"
    image.save(first, compress_level=0)
    image.save(second, compress_level=9)
    assert sha256_file(first) == sha256_file(first)
    assert sha256_file(first) != sha256_file(second)
    with Image.open(first) as one, Image.open(second) as two:
        assert pixel_sha256(one) == pixel_sha256(two)
