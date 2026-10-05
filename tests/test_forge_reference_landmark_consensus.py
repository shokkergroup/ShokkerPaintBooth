from _forge_reference_landmark_consensus import consensus, measure, project_uv


def test_opposite_side_directions_produce_same_wheel_relative_box() -> None:
    right = measure({"id": "r", "rear_wheel_bbox": [100, 100, 200, 200], "art_bbox": [90, 80, 210, 120], "forward_direction": 1, "body_top_y": 50, "rocker_y": 220})
    left = measure({"id": "l", "rear_wheel_bbox": [300, 100, 400, 200], "art_bbox": [290, 80, 410, 120], "forward_direction": -1, "body_top_y": 50, "rocker_y": 220})
    assert right["wheel_relative_box"] == left["wheel_relative_box"]
    combined = consensus([right, left], {"max_wheel_relative_x_spread": 0.1, "max_wheel_relative_z_spread": 0.1})
    assert combined["valid"]
    assert combined["body_fraction_box"] == right["body_fraction_box"]
    assert combined["body_fraction_spreads"] == [0.0, 0.0]


def test_consensus_projects_to_uv_wheel_anchor() -> None:
    box = [-1.0, 0.5, 1.5, 1.5]
    assert project_uv(box, {"wheel_center": [400, 1600], "wheel_radius": 100, "forward_direction": 1}) == [300, 1450, 550, 1550]


def test_measure_recovers_same_car_space_box_from_opposite_sides() -> None:
    right = measure({"id": "r", "rear_wheel_bbox": [90, 80, 110, 100], "front_wheel_bbox": [290, 80, 310, 100], "art_bbox": [140, 40, 240, 80], "forward_direction": 1, "body_top_y": 20, "rocker_y": 100})
    left = measure({"id": "l", "rear_wheel_bbox": [290, 80, 310, 100], "front_wheel_bbox": [90, 80, 110, 100], "art_bbox": [160, 40, 260, 80], "forward_direction": -1, "body_top_y": 20, "rocker_y": 100})
    assert right["car_space_box"] == left["car_space_box"]


def test_consensus_rejects_disagreeing_car_space_even_when_wheel_boxes_agree() -> None:
    base = {"id": "a", "wheel_relative_box": [0.0, 0.0, 1.0, 1.0], "body_fraction_box": [0.1, 0.9], "car_space_box": [0.2, 0.1, 0.5, 0.3]}
    shifted = {**base, "id": "b", "car_space_box": [0.5, 0.1, 0.8, 0.3]}
    result = consensus([base, shifted], {"max_car_space_x_spread": 0.1})
    assert not result["valid"]
