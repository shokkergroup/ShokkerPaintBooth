"""Build one owner-eye paint and A/B material proof for all 110 Wilds finishes.

The paired views reuse the exact same RGB paint and differ only in the
M/R/Cc lighting weights. This makes the FRACTURED color exchange inspectable
without claiming that a proxy is an in-game screenshot.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.registry import MONOLITHIC_REGISTRY
from scripts.spb_wilds_110_bake import _install_and_ids
from scripts.spb_wilds_audit import ANGLE_A_WEIGHTS, ANGLE_B_WEIGHTS, _save_sheet
from scripts.spb_wilds_owner_eye_visuals import _angle_view, _u8


def _render(finish_id: str, size: int = 256):
    spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_id][:2]
    shape = (size, size)
    mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), 0.18, np.float32)
    base_boost = np.zeros(shape, np.float32)
    paint = paint_fn(source, shape, mask, 20260823, 1.0, base_boost)
    spec = spec_fn(shape, mask, 20260823, 1.0)
    return paint, spec


def _paired_grid(items, target: Path, *, pairs_per_row: int = 5) -> None:
    tile, label_h = 128, 34
    cell_w, cell_h = tile * 2, tile + label_h
    rows = (len(items) + pairs_per_row - 1) // pairs_per_row
    sheet = Image.new("RGB", (pairs_per_row * cell_w, rows * cell_h), (12, 14, 18))
    draw = ImageDraw.Draw(sheet)
    for index, (finish_id, angle_a, angle_b) in enumerate(items):
        x = (index % pairs_per_row) * cell_w
        y = (index // pairs_per_row) * cell_h
        a = Image.fromarray(angle_a).resize((tile, tile), Image.Resampling.NEAREST)
        b = Image.fromarray(angle_b).resize((tile, tile), Image.Resampling.NEAREST)
        sheet.paste(a, (x, y))
        sheet.paste(b, (x + tile, y))
        draw.text((x + 4, y + tile + 4), f"{finish_id}  A | B", fill=(238, 241, 245))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def build(output: Path) -> dict:
    lanes, finish_ids = _install_and_ids()
    output.mkdir(parents=True, exist_ok=True)
    paint_dir = output / "paint"
    angle_dir = output / "angle_ab"
    paint_dir.mkdir(exist_ok=True)
    angle_dir.mkdir(exist_ok=True)

    paint_items = []
    paired_items = []
    for index, finish_id in enumerate(finish_ids, 1):
        paint, spec = _render(finish_id)
        paint_u8 = _u8(paint)
        angle_a = _u8(_angle_view(paint, spec, ANGLE_A_WEIGHTS))
        angle_b = _u8(_angle_view(paint, spec, ANGLE_B_WEIGHTS))
        Image.fromarray(paint_u8).save(paint_dir / f"{finish_id}.png")
        Image.fromarray(angle_a).save(angle_dir / f"{finish_id}_angle_a.png")
        Image.fromarray(angle_b).save(angle_dir / f"{finish_id}_angle_b.png")
        paint_items.append((finish_id, paint_u8))
        paired_items.append((finish_id, angle_a, angle_b))
        print(f"[wilds-110-visual] {index:03d}/110 {finish_id}", flush=True)

    _save_sheet(paint_items, output / "wilds_110_paint_contact.png")
    _paired_grid(paired_items, output / "wilds_110_angle_ab_grid.png")
    report = {
        "schema": 1,
        "ticket": "SPB-WILDS 2026-08-23 final owner-eye proof",
        "count": len(finish_ids),
        "lanes": {name: len(ids) for name, ids in lanes.items()},
        "resolution": 256,
        "angleAWeights": list(ANGLE_A_WEIGHTS),
        "angleBWeights": list(ANGLE_B_WEIGHTS),
        "angleNote": (
            "A and B reuse identical paint RGB and exposure; only metallic, "
            "inverse-roughness, and clearcoat response weights change."
        ),
        "paintContact": "wilds_110_paint_contact.png",
        "angleGrid": "wilds_110_angle_ab_grid.png",
    }
    (output / "visual_manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "_wilds_work" / "wilds_110_visual_final",
    )
    args = parser.parse_args()
    report = build(args.output.resolve())
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
