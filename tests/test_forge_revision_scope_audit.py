import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_revision_scope_audit import audit


def _save(path: Path, array: np.ndarray) -> None:
    Image.fromarray(array, "RGBA").save(path)


def _fixture(tmp_path: Path, after: np.ndarray, *, base_reveal_gate: dict | None = None) -> Path:
    before = np.zeros((12, 16, 4), dtype=np.uint8)
    before[:, :] = (20, 30, 40, 255)
    _save(tmp_path / "before.png", before)
    _save(tmp_path / "after.png", after)
    mask = np.zeros((12, 16), dtype=np.uint8)
    mask[2:10, 3:13] = 255
    Image.fromarray(mask, "L").save(tmp_path / "side.png")
    (tmp_path / "adapter.json").write_text(
        json.dumps({"surfaces": {"side": {"mask_path": "side.png"}}}), encoding="utf-8"
    )
    job = {
        "root": str(tmp_path),
        "before": "before.png",
        "after": "after.png",
        "adapter": "adapter.json",
        "allowed_surfaces": ["side"],
        "max_outside_change_pixels": 0,
    }
    if base_reveal_gate:
        job["base_reveal_gate"] = base_reveal_gate
    path = tmp_path / "job.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    return path


def test_revision_scope_accepts_changes_inside_declared_surface(tmp_path: Path) -> None:
    after = np.zeros((12, 16, 4), dtype=np.uint8)
    after[:, :] = (20, 30, 40, 255)
    after[4:7, 5:9, :3] = (220, 30, 40)
    report = audit(_fixture(tmp_path, after), tmp_path / "report.json")
    assert report["valid"]
    assert report["changed_pixels"] == 12
    assert report["outside_allowed_pixels"] == 0


def test_revision_scope_rejects_collateral_change(tmp_path: Path) -> None:
    after = np.zeros((12, 16, 4), dtype=np.uint8)
    after[:, :] = (20, 30, 40, 255)
    after[0, 0, :3] = (220, 30, 40)
    report = audit(_fixture(tmp_path, after), tmp_path / "report.json")
    assert not report["valid"]
    assert report["outside_allowed_pixels"] == 1


def test_revision_scope_rejects_large_base_color_reveal(tmp_path: Path) -> None:
    after = np.zeros((12, 16, 4), dtype=np.uint8)
    after[:, :] = (20, 30, 40, 255)
    after[3:8, 5:11, :3] = (240, 190, 10)
    report = audit(
        _fixture(
            tmp_path,
            after,
            base_reveal_gate={
                "base_rgb": [240, 190, 10],
                "tolerance": 2,
                "min_before_distance": 40,
                "max_component_pixels": 10,
            },
        ),
        tmp_path / "report.json",
    )
    assert not report["valid"]
    assert report["base_reveal_gate"]["largest_component_pixels"] == 30
