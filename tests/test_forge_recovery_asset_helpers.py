from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_psd_leaf_export import resolve_layer_path
from _forge_readable_safe_placement import surface_contract
from _forge_promote_full_uv_adapter import solidify_wire_mesh_gaps
from _forge_surface_style_assets import JOB_SCHEMA, render_job


class _Layer:
    def __init__(self, name: str, *, group: bool = False, children: list["_Layer"] | None = None) -> None:
        self.name = name
        self._group = group
        self._children = children or []

    def is_group(self) -> bool:
        return self._group

    def __iter__(self):
        return iter(self._children)


def test_psd_leaf_path_requires_exact_group_and_leaf() -> None:
    leaf = _Layer("NUMBER COMPONENT 01")
    root = [_Layer("30 NUMBERS", group=True, children=[leaf])]
    assert resolve_layer_path(root, ["30 NUMBERS", "NUMBER COMPONENT 01"]) is leaf


def test_surface_style_asset_is_exactly_confined_to_adapter_mask(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir(exist_ok=True)
    mask = Image.new("L", (64, 64), 0)
    for y in range(14, 46):
        for x in range(10, 54):
            mask.putpixel((x, y), 255)
    mask.save(masks / "panel.png")
    adapter = {
        "canvas": [64, 64],
        "surfaces": {
            "panel": {
                "paintable": True,
                "bbox": [10, 14, 54, 46],
                "mask_path": "masks/panel.png",
            }
        },
    }
    (tmp_path / "adapter.json").write_text(json.dumps(adapter), encoding="utf-8")
    job = {
        "$schema": JOB_SCHEMA,
        "template_adapter": "adapter.json",
        "assets": [
            {
                "id": "burst",
                "surface": "panel",
                "style": "burst",
                "colors": ["#F3E4C5", "#E84A18"],
                "params": {"rays": 12, "cx": 0.8, "cy": 0.5},
            }
        ],
    }
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    report = render_job(job_path, tmp_path / "out", root=tmp_path)
    assert report["valid"]
    with Image.open(tmp_path / "out" / "burst.png") as opened:
        alpha = np.asarray(opened.convert("RGBA"))[:, :, 3]
    assert int(np.count_nonzero(alpha)) == 44 * 32
    assert int(alpha[0, 0]) == 0


def test_paint_uses_full_coverage_while_readable_art_uses_safe_mask(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir(exist_ok=True)
    coverage = np.zeros((64, 64), dtype=np.uint8)
    coverage[8:56, 6:58] = 255
    safe = np.zeros((64, 64), dtype=np.uint8)
    safe[18:46, 18:46] = 255
    Image.fromarray(coverage, "L").save(masks / "coverage.png")
    Image.fromarray(safe, "L").save(masks / "safe.png")
    adapter = {
        "canvas": [64, 64],
        "surfaces": {
            "panel": {
                "paintable": True,
                "bbox": [6, 8, 58, 56],
                "mask_path": "masks/coverage.png",
                "coverage_mask_path": "masks/coverage.png",
                "semantic_safe_mask_path": "masks/safe.png",
            }
        },
    }
    adapter_path = tmp_path / "adapter.json"
    adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
    job = {
        "$schema": JOB_SCHEMA,
        "template_adapter": "adapter.json",
        "assets": [{"id": "field", "surface": "panel", "style": "solid", "colors": ["#222222", "#eeeeee"]}],
    }
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    report = render_job(job_path, tmp_path / "out2", root=tmp_path)
    assert report["assets"][0]["alpha_pixels"] == int(np.count_nonzero(coverage))
    allowed, _keepout, _adapter = surface_contract(adapter_path, "panel")
    assert int(allowed.sum()) == int(np.count_nonzero(safe))


def test_solidify_wire_mesh_gaps_fills_grid_but_preserves_wheel_opening() -> None:
    mask = np.zeros((180, 260), dtype=bool)
    mask[20:160, 20:240] = True
    mask[40:150:20, 20:240] = False
    mask[20:160, 45:230:25] = False
    yy, xx = np.ogrid[:180, :260]
    wheel = (xx - 92) ** 2 + (yy - 105) ** 2 <= 32 ** 2
    mask[wheel] = False

    solid = solidify_wire_mesh_gaps(mask, gap_px=7)

    assert solid[40, 200]
    assert solid[100, 45]
    assert not solid[105, 92]
    assert not solid[5, 5]
