from __future__ import annotations

import json
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_adapter_exclusive_ownership import resolve_exclusive_ownership


def test_exclusive_resolver_preserves_union_and_removes_overlap(tmp_path: Path) -> None:
    root = tmp_path / uuid.uuid4().hex
    masks = root / "masks"
    masks.mkdir(parents=True)
    left = np.zeros((80, 100), dtype=np.uint8)
    right = np.zeros_like(left)
    left[10:65, 8:64] = 255
    right[25:74, 48:94] = 255
    Image.fromarray(left, "L").save(masks / "a.png")
    Image.fromarray(right, "L").save(masks / "b.png")
    before_union = (left > 0) | (right > 0)
    before_overlap = int(np.count_nonzero((left > 0) & (right > 0)))
    adapter = {
        "$schema": "shokk-forge.template-adapter/v1",
        "package_version": "2",
        "canvas": [100, 80],
        "surfaces": {
            "a": {"paintable": True, "mask_path": "masks/a.png", "bbox": [8, 10, 64, 65]},
            "b": {"paintable": True, "mask_path": "masks/b.png", "bbox": [48, 25, 94, 74]},
        },
    }
    path = root / "adapter.json"
    path.write_text(json.dumps(adapter), encoding="utf-8")

    report = resolve_exclusive_ownership(path)
    after_a = np.asarray(Image.open(masks / "a.png").convert("L")) > 0
    after_b = np.asarray(Image.open(masks / "b.png").convert("L")) > 0
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert report["overlap_pixels_before"] == before_overlap
    assert report["overlap_pixels_after"] == 0
    assert np.array_equal(after_a | after_b, before_union)
    assert not np.any(after_a & after_b)
    assert saved["package_version"] == "3"
    assert saved["surfaces"]["a"]["ownership_contract"] == "exclusive_nearest_unique_core/v1"
    assert saved["surfaces"]["b"]["ownership_contract"] == "exclusive_nearest_unique_core/v1"
