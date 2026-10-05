from PIL import Image, ImageDraw

import _forge_evidence_cropper as cropper


def test_phrase_anchor_requires_words_on_same_ocr_line() -> None:
    words = [
        {"text": "top", "confidence": 90, "bbox": [10, 40, 30, 50], "line": (1, 1, 1)},
        {"text": "view", "confidence": 80, "bbox": [35, 40, 60, 50], "line": (1, 1, 1)},
        {"text": "top", "confidence": 90, "bbox": [10, 60, 30, 70], "line": (1, 1, 2)},
        {"text": "view", "confidence": 80, "bbox": [35, 80, 60, 90], "line": (1, 1, 3)},
    ]
    anchors = cropper.phrase_anchors(words, "top_view")
    assert len(anchors) == 1
    assert anchors[0]["phrase"] == "top view"


def test_three_quarter_phrase_is_a_distinct_auxiliary_role() -> None:
    words = [
        {"text": "front", "confidence": 96, "bbox": [10, 40, 42, 52], "line": (1, 1, 1)},
        {"text": "34", "confidence": 94, "bbox": [46, 40, 62, 52], "line": (1, 1, 1)},
        {"text": "view", "confidence": 95, "bbox": [66, 40, 96, 52], "line": (1, 1, 1)},
    ]
    anchors = cropper.phrase_anchors(words, "front_three_quarter")
    assert len(anchors) == 1
    assert anchors[0]["phrase"] == "front 34 view"


def test_dlm_profile_side_uses_low_nose_and_tall_rear(monkeypatch) -> None:
    image = Image.new("RGB", (600, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.polygon([(20, 165), (110, 120), (490, 70), (585, 55), (585, 215), (20, 215)], fill="#e6be00")
    draw.ellipse((100, 160, 190, 250), fill="black")
    draw.ellipse((420, 160, 510, 250), fill="black")
    monkeypatch.setattr(
        "_forge_car_space.detect_wheels",
        lambda _image: ([{"x": 145.0}, {"x": 465.0}], 0.9),
    )
    role, confidence = cropper.infer_dlm_profile_role(image)
    assert role == "left_profile"
    assert confidence >= 0.5


def test_dominant_profile_crop_prefers_wide_car_over_small_detail() -> None:
    image = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 120, 560, 230), fill="#17652c")
    draw.ellipse((120, 190, 190, 260), fill="black")
    draw.ellipse((430, 190, 500, 260), fill="black")
    draw.rectangle((50, 300, 170, 360), fill="#d71920")
    result = cropper.dominant_view_bbox(image, "left_profile")
    assert result is not None
    bbox, confidence = result
    assert bbox[0] < 60 and bbox[2] > 540
    assert bbox[1] < 130 and bbox[3] > 240
    assert confidence >= 0.5


def test_orthographic_master_search_can_exclude_lower_detail_panels() -> None:
    image = Image.new("RGB", (600, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((35, 120, 565, 230), fill="#17652c")
    draw.ellipse((120, 190, 190, 260), fill="black")
    draw.ellipse((430, 190, 500, 260), fill="black")
    draw.rectangle((0, 390, 600, 600), fill="#101820")
    result = cropper.dominant_view_bbox(image, "right_profile", search_fraction=0.62)
    assert result is not None
    bbox, _confidence = result
    assert bbox[1] < 140
    assert bbox[3] < 300


def test_normalized_bbox_uses_xyxy_coordinates() -> None:
    assert cropper._normalized_bbox([10, 20, 60, 70], (100, 100)) == [0.1, 0.2, 0.6, 0.7]
