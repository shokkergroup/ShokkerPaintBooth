from pathlib import Path

import numpy as np
from PIL import Image

import _forge_side_projection as projection


def _profile(role: str, score: float, *, accepted: bool, inliers: int = 20, support: float = 0.8, rmse: float = 1.0) -> dict:
    return {
        "profile_role": role,
        "score": score,
        "localization": {"accepted": accepted, "inliers": inliers, "inlier_ratio": support, "reprojection_rmse": rmse},
    }


def test_direct_side_requires_geometric_winner_and_margin() -> None:
    result = projection.choose_direct_side([_profile("left_profile", 0.92, accepted=True), _profile("right_profile", 0.42, accepted=False)])
    assert result["accepted"]
    assert result["surface"] == "left_strip"
    assert result["rotation_deg"] == 180


def test_color_only_winner_cannot_promote_side() -> None:
    result = projection.choose_direct_side([_profile("left_profile", 0.70, accepted=False), _profile("right_profile", 0.20, accepted=False)])
    assert not result["accepted"]
    assert result["surface"] is None


def test_sheet_consensus_propagates_only_from_direct_winner() -> None:
    direct = projection.choose_direct_side([_profile("left_profile", 0.90, accepted=True), _profile("right_profile", 0.30, accepted=False)])
    rows = [
        {"sheet_role": "sheet-a", "source_component_id": "leader", "resolution": direct},
        {"sheet_role": "sheet-a", "source_component_id": "follower", "resolution": {"accepted": False}},
        {"sheet_role": "sheet-b", "source_component_id": "other", "resolution": {"accepted": False}},
    ]
    projection.propagate_sheet_consensus(rows)
    assert rows[1]["resolution"]["accepted"]
    assert rows[1]["resolution"]["surface"] == "left_strip"
    assert rows[1]["resolution"]["basis"] == "same-sheet direct-winner consensus"
    assert not rows[2]["resolution"]["accepted"]


def test_projection_rotates_left_without_mirroring_and_clips_mandatory(tmp_path: Path) -> None:
    source = np.zeros((10, 20, 4), dtype=np.uint8)
    source[1:4, 1:5] = (255, 0, 0, 255)
    path = tmp_path / "source.png"
    Image.fromarray(source, "RGBA").save(path)
    car_surface = np.ones((40, 60), dtype=bool)
    mandatory = np.zeros((40, 60), dtype=bool)
    # The 180-degree projection moves the asymmetric red mark into the
    # lower-right quadrant of this synthetic side-strip bbox.
    mandatory[17:30, 35:50] = True
    output = tmp_path / "left.png"
    record = projection.project_to_surface(path, "left_strip", [10, 10, 50, 30], 180, car_surface, mandatory, output)
    assert record["rotation_deg"] == 180
    assert not record["mirror_applied"]
    assert record["mandatory_overlap_after_clip"] == 0
    assert record["mandatory_clipped_pixels"] > 0
