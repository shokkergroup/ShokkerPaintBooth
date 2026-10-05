from pathlib import Path

import numpy as np
from PIL import Image

from _forge_wire_gap_continuity_audit import _union


def test_adapter_union_prefers_coverage_mask(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir(exist_ok=True)
    coverage = np.zeros((16, 16), dtype=np.uint8)
    coverage[2:14, 3:13] = 255
    safe = np.zeros_like(coverage)
    safe[6:10, 6:10] = 255
    Image.fromarray(coverage, "L").save(masks / "coverage.png")
    Image.fromarray(safe, "L").save(masks / "safe.png")
    adapter = {
        "canvas": [16, 16],
        "surfaces": {
            "panel": {
                "paintable": True,
                "mask_path": "masks/safe.png",
                "coverage_mask_path": "masks/coverage.png",
            }
        },
    }
    path = tmp_path / "adapter.json"
    path.write_text(__import__("json").dumps(adapter), encoding="utf-8")
    assert int(_union(path).sum()) == 120
