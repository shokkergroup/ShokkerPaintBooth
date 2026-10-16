"""Render the existing procedural-math arsenal for Wilds redesign selection.

SPB-WILDS-REJECTION-2026-08-24, tick WR-2. This is a source-design inventory,
not a release gate. It makes the many genuinely different mathematical
construction grammars visible before any is assigned to a Wilds finish.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.paint_v2 import exotic_engines_2026 as exotic  # noqa: E402


def _robust_u8(field: np.ndarray) -> np.ndarray:
    a = np.nan_to_num(np.asarray(field, np.float32), nan=0.0, posinf=1.0, neginf=0.0)
    lo, hi = np.percentile(a, (1.0, 99.0))
    if float(hi - lo) < 1e-7:
        return np.zeros(a.shape, np.uint8)
    return np.clip((a - lo) * (255.0 / float(hi - lo)), 0.0, 255.0).astype(np.uint8)


def _contact(items: list[tuple[str, np.ndarray, float]], target: Path, cols: int = 6) -> None:
    if not items:
        return
    tile = items[0][1].shape[0]
    label_h = 42
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), (8, 10, 14))
    draw = ImageDraw.Draw(sheet)
    for index, (name, image, elapsed) in enumerate(items):
        x = (index % cols) * tile
        y = (index // cols) * (tile + label_h)
        rgb = np.repeat(image[:, :, None], 3, axis=2)
        sheet.paste(Image.fromarray(rgb), (x, y))
        draw.text((x + 4, y + tile + 4), name, fill=(240, 242, 246))
        draw.text((x + 4, y + tile + 20), f"{elapsed:.3f}s", fill=(160, 205, 255))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def build(output: Path, size: int) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    image_dir = output / "fields"
    image_dir.mkdir(exist_ok=True)
    items = []
    failures = []
    rows = []
    for index, name in enumerate(exotic.names(), 1):
        started = time.perf_counter()
        try:
            field = exotic.field(name, size, size, 20260824 + index * 7919)
            elapsed = time.perf_counter() - started
            image = _robust_u8(field)
            # A restrained unsharp pass exposes the engine's own construction;
            # it does not add texture or change topology.
            blurred = cv2.GaussianBlur(image, (0, 0), 0.8)
            image = cv2.addWeighted(image, 1.35, blurred, -0.35, 0)
            Image.fromarray(image).save(image_dir / f"{name}.png")
            items.append((name, image, elapsed))
            rows.append({
                "name": name,
                "seconds": round(elapsed, 6),
                "std": round(float(image.std()), 6),
                "unique": int(np.unique(image).size),
            })
            print(f"[wilds-exotic-inventory] {index:03d}/{len(exotic.names())} {name} {elapsed:.3f}s", flush=True)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            failures.append({"name": name, "seconds": round(elapsed, 6), "error": str(exc)})
            print(f"[wilds-exotic-inventory] ERROR {name}: {exc}", flush=True)
    _contact(items, output / "exotic_source_contact.png")
    report = {
        "schema": 1,
        "ticket": "SPB-WILDS-REJECTION-2026-08-24 WR-2",
        "count": len(rows),
        "failures": failures,
        "resolution": size,
        "engines": rows,
    }
    (output / "exotic_source_inventory.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=160)
    args = parser.parse_args()
    if args.size < 96 or args.size > 256:
        parser.error("--size must be between 96 and 256")
    report = build(args.output.resolve(), args.size)
    print(json.dumps({key: value for key, value in report.items() if key != "engines"}, indent=2))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
