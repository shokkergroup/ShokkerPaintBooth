from pathlib import Path

import numpy as np
from PIL import Image

import _forge_semantic_partition as semantic


def _localization(*, accepted: bool = True, inliers: int = 12, support: float = 0.6, rmse: float = 1.0, fraction: float = 0.1) -> dict:
    return {
        "accepted": accepted,
        "reason": None if accepted else "weak_ransac_support",
        "inliers": inliers,
        "inlier_ratio": support,
        "reprojection_rmse": rmse,
        "selected_pixels": 100,
        "selected_fraction": fraction,
    }


def test_acceptance_has_strong_and_number_only_geometry_lanes() -> None:
    assert semantic.acceptance_reason(_localization(), "decal") is None
    assert semantic.acceptance_reason(_localization(inliers=7, support=0.52, rmse=0.5), "number") is None
    assert semantic.acceptance_reason(_localization(inliers=7, support=0.52, rmse=0.5), "decal") is not None
    assert semantic.acceptance_reason(_localization(fraction=0.4), "decal") is not None


def test_cluster_keeps_best_same_role_mask() -> None:
    mask = np.zeros((20, 20), dtype=bool)
    mask[4:12, 5:13] = True
    rows = []
    for identity, quality in (("weak", 4.0), ("strong", 9.0)):
        rows.append(
            {
                "accepted": True,
                "exemplar": {"id": identity, "role": "decal"},
                "localization": {"_mask": mask.copy(), "quality": quality},
            }
        )
    winners, rejected = semantic.cluster_candidates(rows)
    assert [row["exemplar"]["id"] for row in winners] == ["strong"]
    assert rejected[0]["exemplar_id"] == "weak"


def test_partition_primary_is_raw_and_visibly_exact() -> None:
    target = np.zeros((20, 30, 4), dtype=np.uint8)
    target[2:18, 3:27] = (20, 120, 220, 255)
    first = np.zeros((20, 30), dtype=bool)
    second = np.zeros_like(first)
    first[4:9, 5:11] = True
    second[10:16, 18:25] = True
    winners = [{"localization": {"_mask": first}}, {"localization": {"_mask": second}}]
    layers, remainder, proof = semantic.partition_primary(target, winners)
    assert len(layers) == 2
    assert proof["raw_rgba_different_pixels"] == 0
    assert proof["visible_composite_different_pixels"] == 0
    assert proof["mask_overlap_pixels_before_partition"] == 0
    assert proof["isolated_semantic_pixels"] == int(first.sum() + second.sum())
    assert int((remainder[:, :, 3] > 8).sum()) + proof["isolated_semantic_pixels"] == int((target[:, :, 3] > 8).sum())


def test_number_first_partition_keeps_overlap_in_number_layer() -> None:
    target = np.zeros((12, 12, 4), dtype=np.uint8)
    target[1:11, 1:11] = (255, 255, 255, 255)
    number = np.zeros((12, 12), dtype=bool)
    decal = np.zeros_like(number)
    number[3:9, 3:9] = True
    decal[5:11, 5:11] = True
    winners = [
        {"exemplar": {"role": "number"}, "localization": {"_mask": number}},
        {"exemplar": {"role": "decal"}, "localization": {"_mask": decal}},
    ]
    layers, _remainder, proof = semantic.partition_primary(target, winners)
    assert int((layers[0][:, :, 3] > 8).sum()) == int(number.sum())
    assert proof["raw_rgba_different_pixels"] == 0


def test_duplicate_overlay_suppression_requires_identity_and_uv_overlap(tmp_path: Path) -> None:
    rgba = np.zeros((30, 30, 4), dtype=np.uint8)
    rgba[5:20, 7:22] = (255, 255, 255, 255)
    first, second = tmp_path / "first.png", tmp_path / "second.png"
    Image.fromarray(rgba, "RGBA").save(first)
    Image.fromarray(rgba, "RGBA").save(second)
    inherited = [
        {
            "layer_id": "old",
            "candidate_route": {"visible": True, "group": "40 SPONSORS & BRAND MARKS", "basis": "old"},
            "projection": {"path": str(first)},
        }
    ]
    stage = {"old": {"evidence": {"primary_exemplar": {"id": "same"}}}}
    new = [{"layer_id": "new", "semantic_identity": "same", "projection": {"path": str(second)}}]
    result = semantic.suppress_duplicate_overlays(inherited, stage, new)
    assert not result[0]["candidate_route"]["visible"]
    assert result[0]["duplicate_suppression"]["uv_alpha_iou"] == 1.0
