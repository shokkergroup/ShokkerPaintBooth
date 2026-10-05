"""Bake JPG runtime derivatives for image-authored Cultural packs.

The source PNG plates stay untouched until an explicit archive/move step. This
writes 2048x2048 JPG derivatives into each pack's ``jpg_2048`` folder so retail
runtime assets can be much smaller while keeping the authoring masters isolated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PACK_DIRS = {
    "union_jacked": ROOT / "assets" / "reference_textures" / "cultural" / "union_jacked",
    "rising_sun": ROOT / "assets" / "reference_textures" / "cultural" / "rising_sun",
    "viva_mexico": ROOT / "assets" / "reference_textures" / "cultural" / "viva_mexico",
    "grunge_fun": ROOT / "assets" / "reference_textures" / "grunge_fun",
}
TARGET_SIZE = (2048, 2048)
JPG_QUALITY = 92


def _save_jpg(src: Path, dst: Path) -> int:
    img = Image.open(src).convert("RGB")
    if img.size != TARGET_SIZE:
        img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        img.save(
            dst,
            "JPEG",
            quality=JPG_QUALITY,
            optimize=True,
            progressive=False,
            subsampling=0,
        )
    except OSError:
        img.save(
            dst,
            "JPEG",
            quality=JPG_QUALITY,
            optimize=False,
            progressive=False,
            subsampling=0,
        )
    return dst.stat().st_size


def _manifest_ids(pack_dir: Path) -> list[str]:
    manifest_path = pack_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [str(item["id"]) for item in manifest.get("finishes", []) if item.get("id")]


def bake_pack(pack: str, pack_dir: Path) -> dict[str, int]:
    out_dir = pack_dir / "jpg_2048"
    total_png = 0
    total_jpg = 0
    converted = 0
    for finish_id in _manifest_ids(pack_dir):
        for suffix in ("", "_spec"):
            src = pack_dir / f"{finish_id}{suffix}.png"
            if not src.exists():
                continue
            dst = out_dir / f"{finish_id}{suffix}.jpg"
            total_png += src.stat().st_size
            total_jpg += _save_jpg(src, dst)
            converted += 1
    print(f"{pack}: converted {converted} PNG plates/specs to JPG.")
    print(f"{pack}: PNG source bytes: {total_png:,}")
    print(f"{pack}: JPG runtime bytes: {total_jpg:,}")
    if total_png:
        print(f"{pack}: JPG is {total_jpg / total_png:.1%} of PNG size.")
    print(f"{pack}: output: {out_dir}")
    return {"converted": converted, "png_bytes": total_png, "jpg_bytes": total_jpg}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "packs",
        nargs="*",
        choices=sorted(PACK_DIRS),
        default=sorted(PACK_DIRS),
        help="Cultural pack(s) to bake. Defaults to all.",
    )
    args = parser.parse_args()
    totals = {"converted": 0, "png_bytes": 0, "jpg_bytes": 0}
    for pack in args.packs:
        stats = bake_pack(pack, PACK_DIRS[pack])
        for key, value in stats.items():
            totals[key] += value
    print("TOTAL converted:", totals["converted"])
    print("TOTAL PNG source bytes:", f"{totals['png_bytes']:,}")
    print("TOTAL JPG runtime bytes:", f"{totals['jpg_bytes']:,}")
    if totals["png_bytes"]:
        print("TOTAL JPG ratio:", f"{totals['jpg_bytes'] / totals['png_bytes']:.1%}")


if __name__ == "__main__":
    main()
