import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_paired_surface_lock import lock_pair, physical_box_to_uv, uv_box_to_physical


def test_orientation_aware_boxes_roundtrip_and_mirror() -> None:
    right = {"bbox": [0, 100, 100, 200], "upright_rotation_deg": 0}
    left = {"bbox": [0, 0, 100, 100], "upright_rotation_deg": 180}
    physical = uv_box_to_physical([20, 110, 60, 130], right)
    assert physical == [0.2, 0.1, 0.6, 0.3]
    assert physical_box_to_uv(physical, left) == [40, 70, 80, 90]


def test_joint_lock_emits_same_physical_box_on_both_surfaces(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir(exist_ok=True)
    full = Image.fromarray(np.full((200, 100), 255, dtype=np.uint8), "L")
    full.save(masks / "left.png")
    full.save(masks / "right.png")
    adapter = {
        "surfaces": {
            "left": {"bbox": [0, 0, 100, 100], "upright_rotation_deg": 180, "mask_path": "masks/left.png"},
            "right": {"bbox": [0, 100, 100, 200], "upright_rotation_deg": 0, "mask_path": "masks/right.png"},
        },
        "semantic_visibility": {},
    }
    (tmp_path / "adapter.json").write_text(json.dumps(adapter), encoding="utf-8")
    Image.new("RGBA", (40, 20), (255, 200, 0, 255)).save(tmp_path / "asset.png")
    job = {
        "adapter": "adapter.json",
        "exemplar": "asset.png",
        "anchor": {"surface": "right", "bbox": [20, 110, 60, 130]},
        "surfaces": [
            {"id": "l", "surface": "left", "output": "left.png"},
            {"id": "r", "surface": "right", "output": "right.png"},
        ],
        "search": {"min_scale": 1.0, "scale_step": 0.1, "max_shift_normalized": 0.0, "shift_step_normalized": 0.01, "acceptance_min_scale": 1.0},
    }
    report = lock_pair(job, tmp_path, tmp_path / "out")
    assert report["valid"]
    assert report["surfaces"][0]["uv_bbox"] == [40, 70, 80, 90]
    assert report["surfaces"][1]["uv_bbox"] == [20, 110, 60, 130]
    assert report["totals"] == {"outside_pixels": 0, "keepout_pixels": 0, "collision_pixels": 0}


def test_anchor_priority_prefers_shrink_without_landmark_drift(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir(exist_ok=True)
    allowed = np.zeros((200, 100), dtype=np.uint8)
    allowed[:, :70] = 255
    Image.fromarray(allowed, "L").save(masks / "left.png")
    Image.fromarray(allowed, "L").save(masks / "right.png")
    adapter = {
        "surfaces": {
            "left": {"bbox": [0, 0, 100, 100], "upright_rotation_deg": 0, "mask_path": "masks/left.png"},
            "right": {"bbox": [0, 100, 100, 200], "upright_rotation_deg": 0, "mask_path": "masks/right.png"},
        },
        "semantic_visibility": {},
    }
    (tmp_path / "adapter.json").write_text(json.dumps(adapter), encoding="utf-8")
    Image.new("RGBA", (40, 20), (255, 200, 0, 255)).save(tmp_path / "asset.png")
    job = {
        "adapter": "adapter.json",
        "exemplar": "asset.png",
        "anchor": {"surface": "right", "bbox": [40, 110, 80, 130]},
        "surfaces": [
            {"id": "l", "surface": "left", "output": "left.png"},
            {"id": "r", "surface": "right", "output": "right.png"},
        ],
        "search": {
            "min_scale": 0.5,
            "scale_step": 0.5,
            "max_shift_normalized": 0.1,
            "shift_step_normalized": 0.1,
            "acceptance_min_scale": 0.5,
            "objective_priority": "anchor_then_scale",
        },
    }
    report = lock_pair(job, tmp_path, tmp_path / "out")
    assert report["valid"]
    assert report["joint_scale"] == 0.5
    assert report["joint_shift"] == [0.0, 0.0]
    assert report["objective_priority"] == "anchor_then_scale"


def test_independent_aspect_preserves_width_while_fitting_shallow_uv_band(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir(exist_ok=True)
    allowed = np.zeros((200, 100), dtype=np.uint8)
    allowed[115:126, :] = 255
    Image.fromarray(allowed, "L").save(masks / "right.png")
    adapter = {
        "surfaces": {
            "right": {"bbox": [0, 100, 100, 200], "upright_rotation_deg": 0, "mask_path": "masks/right.png"},
        },
        "semantic_visibility": {},
    }
    (tmp_path / "adapter.json").write_text(json.dumps(adapter), encoding="utf-8")
    Image.new("RGBA", (40, 20), (255, 200, 0, 255)).save(tmp_path / "asset.png")
    job = {
        "adapter": "adapter.json",
        "exemplar": "asset.png",
        "anchor": {"surface": "right", "bbox": [20, 110, 60, 130]},
        "surfaces": [{"id": "r", "surface": "right", "output": "right.png"}],
        "search": {
            "min_scale": 0.5,
            "scale_step": 0.5,
            "min_scale_y": 0.5,
            "scale_step_y": 0.5,
            "aspect_mode": "independent",
            "max_shift_normalized": 0.0,
            "shift_step_normalized": 0.01,
            "acceptance_min_scale": 0.5,
            "acceptance_min_scale_y": 0.5,
            "objective_priority": "anchor_then_scale",
        },
    }
    report = lock_pair(job, tmp_path, tmp_path / "out")
    assert report["valid"]
    assert report["joint_scale_xy"] == [1.0, 0.5]
    assert report["joint_shift"] == [0.0, 0.0]
