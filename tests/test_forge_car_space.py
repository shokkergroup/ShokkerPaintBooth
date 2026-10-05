import numpy as np
from PIL import Image, ImageDraw, ImageOps

import _forge_car_space as car_space


def _profile(nose_right: bool) -> Image.Image:
    image = Image.new("RGB", (900, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.polygon([(35, 205), (150, 115), (310, 90), (410, 35), (650, 35), (780, 105), (865, 205)], fill="#17733b")
    if not nose_right:
        image = ImageOps.mirror(image)
        draw = ImageDraw.Draw(image)
    draw.ellipse((150, 135, 290, 275), fill="#111111", outline="#333333", width=5)
    draw.ellipse((610, 135, 750, 275), fill="#111111", outline="#333333", width=5)
    draw.rectangle((395, 48, 590, 105), fill="#141414")
    draw.line((300, 215, 600, 215), fill="#e4002b", width=8)
    return image


def test_detect_wheels_finds_separated_lower_pair() -> None:
    wheels, confidence = car_space.detect_wheels(_profile(True))
    assert len(wheels) == 2
    assert abs(wheels[0]["x"] - 220) < 25
    assert abs(wheels[1]["x"] - 680) < 25
    assert confidence >= 0.5


def test_detect_wheels_keeps_real_tire_near_circular_livery_decoy() -> None:
    image = _profile(True)
    draw = ImageDraw.Draw(image)
    # High-contrast circular artwork sits above and close to the rear tire's
    # x coordinate.  It must remain a separate hypothesis, not suppress the
    # darker and lower physical tire.
    draw.ellipse((585, 35, 705, 155), fill="white", outline="black", width=12)
    draw.ellipse((616, 66, 674, 124), fill="#f0c000", outline="black", width=5)
    wheels, confidence = car_space.detect_wheels(image)
    assert abs(wheels[0]["x"] - 220) < 25
    assert abs(wheels[1]["x"] - 680) < 25
    assert wheels[1]["y"] > 175
    assert confidence >= 0.5


def test_tire_appearance_prefers_dark_disc_over_outline_decoy() -> None:
    image = Image.new("L", (320, 180), 255)
    draw = ImageDraw.Draw(image)
    draw.ellipse((35, 55, 135, 155), fill=15)
    draw.ellipse((185, 55, 285, 155), fill=245, outline=10, width=8)
    gray = np.asarray(image, dtype=np.uint8)
    assert car_space._tire_appearance(gray, (85, 105), 50) > 0.9
    assert car_space._tire_appearance(gray, (235, 105), 50) < 0.2


def test_window_bbox_uses_enclosed_light_panes_not_lower_number_fill() -> None:
    image = Image.new("RGB", (900, 300), "white")
    draw = ImageDraw.Draw(image)
    # Enclosed cage with two neutral window voids.
    draw.rectangle((280, 20, 650, 145), fill="#111111")
    draw.polygon([(305, 40), (430, 40), (430, 115), (320, 115)], fill="white")
    draw.polygon([(455, 40), (620, 40), (610, 115), (455, 115)], fill="white")
    # Large white door-number fill sits lower and must not become a window.
    draw.rectangle((380, 155, 590, 270), fill="#111111")
    draw.rectangle((420, 170, 555, 250), fill="white")
    wheels = [{"x": 180.0}, {"x": 720.0}]
    bbox, confidence = car_space.window_bbox(image, wheels)
    assert bbox == [305, 40, 621, 116]
    assert confidence > 0.5


def test_car_point_normalizes_opposite_image_directions() -> None:
    rear = {"x": 100.0}
    front = {"x": 500.0}
    assert car_space._car_point(100, 200, rear, front, 240) == [0.0, 0.1]
    assert car_space._car_point(500, 200, rear, front, 240) == [1.0, 0.1]
    assert car_space._car_point(500, 200, front, rear, 240) == [0.0, 0.1]
    assert car_space._car_point(100, 200, front, rear, 240) == [1.0, 0.1]


def test_consistency_is_perfect_for_identical_feature_vectors() -> None:
    profile = {
        "wheelbase_over_crop_width": 0.5,
        "wheels": [
            {"role": "rear_wheel", "radius_over_wheelbase": 0.12, "radius": 60},
            {"role": "front_wheel", "radius_over_wheelbase": 0.12, "radius": 60},
        ],
        "window": {"car_space": {"x_min": 0.15, "x_max": 0.65, "y_bottom": 0.1, "y_top": 0.3}},
        "silhouette": {"car_space": {"x_min": -0.4, "x_max": 1.4, "y_bottom": -0.05, "y_top": 0.45}},
    }
    assert car_space.consistency(profile, profile)["score"] == 100.0


def test_single_profile_pack_is_valid_without_pair_consistency() -> None:
    pack = {"name": "single", "crops": [{"role": "left_profile"}]}
    original = car_space.analyze_profile
    try:
        car_space.analyze_profile = lambda crop: {"role": crop["role"]}
        result = car_space.analyze_pack(pack, None)
    finally:
        car_space.analyze_profile = original
    assert result["profile_count"] == 1
    assert result["left_right_consistency"] is None
