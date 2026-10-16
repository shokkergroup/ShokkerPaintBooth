#!/usr/bin/env python3
"""Build bounded reference boards from existing non-Wilds picker thumbnails."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(
    r"(cell|bio|mold|spore|bacter|membran|diatom|plank|coral|crystal|fract|"
    r"vein|mesh|web|branch|flow|vortex|foam|shell|scale|nacre|irides|growth|"
    r"reaction|attractor|quasi|penrose|hyperbol|recursive|fluid|finger|"
    r"lissajous|dendrite|caustic|truchet|moire|lattice|marble)", re.I
)


def build(output: Path, page_size: int = 48) -> None:
    manifest_path = ROOT / "thumbnails" / "picker_split" / "_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["finishes"]
    ids = [key for key in manifest
           if PATTERN.search(key)
           and not any(prefix in key for prefix in ("fpe_", "fbl_", "fmo_", "fc_"))
           and not key.startswith("monolithic:grad_")]
    output.mkdir(parents=True, exist_ok=True)
    cell, label_h, cols = 144, 34, 8
    font = ImageFont.load_default()
    rows = []
    for page_index in range(0, len(ids), page_size):
        page = ids[page_index:page_index + page_size]
        height = ((len(page) + cols - 1) // cols) * (cell + label_h)
        sheet = Image.new("RGB", (cols * cell, height), (7, 8, 10))
        draw = ImageDraw.Draw(sheet)
        for i, key in enumerate(page):
            lane, fid = key.split(":", 1)
            source = ROOT / "thumbnails" / "picker_split" / lane / f"{fid}.png"
            if not source.exists():
                continue
            image = Image.open(source).convert("L").resize((cell, cell), Image.Resampling.NEAREST)
            rgb = Image.merge("RGB", (image, image, image))
            x, y = (i % cols) * cell, (i // cols) * (cell + label_h)
            sheet.paste(rgb, (x, y))
            draw.text((x + 3, y + cell + 3), key[:35], fill=(235, 235, 235), font=font)
            rows.append(key)
        sheet.save(output / f"existing_topologies_{page_index // page_size + 1:02d}.png")
    (output / "ids.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} references across {(len(ids) + page_size - 1) // page_size} boards")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "_wilds_rejection_work" / "existing_topology_reference")
    parser.add_argument("--page-size", type=int, default=48)
    args = parser.parse_args()
    build(args.output.resolve(), args.page_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
