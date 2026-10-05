"""Render thumbnails for SPB_RATE_CANDY_PEARL.html.

Reads `_candy_pearl_thumbs/audit_queue.json` and renders per base:
  - {id}_paint.png   paint RGB (what the car color reads as)
  - {id}.png         spec RGB composite (M/R/CC normalized 0-1)
  - {id}_M.png       M channel
  - {id}_R.png       R channel
  - {id}_CC.png      CC channel

Uses swatch from finish-data as the incoming paint color when available.

Run:
  python scripts/generate_candy_pearl_audit_queue.py
  python scripts/render_candy_pearl_thumbs.py
  python scripts/render_candy_pearl_thumbs.py --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

THUMB_DIR = REPO / "_candy_pearl_thumbs"
QUEUE_PATH = THUMB_DIR / "audit_queue.json"
FINISH_DATA = REPO / "paint-booth-0-finish-data.js"
DEFAULT_SIZE = 512
SEED = 7777

TINT_M = (1.00, 0.30, 0.30)
TINT_R = (0.30, 1.00, 0.30)
TINT_CC = (0.30, 0.50, 1.00)


def hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    s = (hex_color or "#888899").lstrip("#")
    if len(s) != 6:
        return 0.18, 0.18, 0.20
    return int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0


def load_swatch_map() -> dict[str, str]:
    src = FINISH_DATA.read_text(encoding="utf-8", errors="replace")
    out: dict[str, str] = {}
    for m in re.finditer(
        r'id:\s*"([a-zA-Z_][a-zA-Z0-9_]*)".*?swatch:\s*"([^"]+)"',
        src,
        re.DOTALL,
    ):
        out[m.group(1)] = m.group(2)
    return out


def tint_channel(field2d: np.ndarray, color: tuple[float, float, float]) -> np.ndarray:
    arr = np.clip(field2d, 0, 1)
    rgb = np.stack([arr * color[0], arr * color[1], arr * color[2]], axis=-1)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def needs_render(name: str, source_mtime: float, force: bool) -> bool:
    if force:
        return True
    for suffix in ("_paint", "", "_M", "_R", "_CC"):
        p = THUMB_DIR / f"{name}{suffix}.png"
        if not p.exists() or p.stat().st_mtime < source_mtime:
            return True
    return False


def import_engine():
    import shokker_engine_v2 as eng

    if hasattr(eng, "_ensure_expansions_loaded"):
        eng._ensure_expansions_loaded()
    return eng


def render_base(eng, base_id: str, size: int, seed: int, swatch: str):
    from scripts.spb_visual_workbench import _render_item, _spec_array

    shape = (size, size)
    r, g, b = hex_to_rgb01(swatch)
    meta = {"swatch": swatch}
    rgb, spec_u8, kind = _render_item(eng, base_id, "base", size, seed, meta)
    # Re-render with swatch-tinted substrate for candy bases
    entry = eng.BASE_REGISTRY.get(base_id)
    if entry:
        mask = np.ones(shape, dtype=np.float32)
        bb = np.zeros(shape, dtype=np.float32)
        paint_in = np.full((size, size, 3), [r, g, b], dtype=np.float32)
        if entry.get("paint_fn"):
            rgb = np.clip(entry["paint_fn"](paint_in, shape, mask, seed, 1.0, bb)[:, :, :3], 0, 1)
        if entry.get("base_spec_fn"):
            spec_raw = entry["base_spec_fn"](
                shape, seed, 1.0, float(entry.get("M", 120)), float(entry.get("R", 80))
            )
            spec_u8 = _spec_array(spec_raw, shape)
    if spec_u8 is None:
        spec_u8 = np.zeros((size, size, 3), dtype=np.uint8)
    return rgb.astype(np.float32), spec_u8


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated base ids")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE)
    ap.add_argument("--all-catalog", action="store_true", help="render full Candy & Pearl group, not just visible queue")
    args = ap.parse_args()

    swatches = load_swatch_map()

    if args.all_catalog:
        from scripts.generate_candy_pearl_audit_queue import load_group_ids, load_base_meta

        ids = load_group_ids()
        meta = load_base_meta()
        queue_bases = [
            {"id": i, "swatch": meta.get(i, {}).get("swatch", swatches.get(i, "#888899"))}
            for i in ids
        ]
    else:
        if not QUEUE_PATH.exists():
            print("Run scripts/generate_candy_pearl_audit_queue.py first.")
            return 2
        queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        queue_bases = queue.get("bases", [])

    only_set = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None
    if only_set:
        queue_bases = [b for b in queue_bases if b["id"] in only_set]

    try:
        import cv2

        HAS_CV2 = True
    except Exception:
        HAS_CV2 = False

    def write_png(rgb_uint8: np.ndarray, path: Path) -> None:
        if HAS_CV2:
            bgr = rgb_uint8[:, :, [2, 1, 0]]
            cv2.imwrite(str(path), bgr)
        else:
            from PIL import Image

            Image.fromarray(rgb_uint8, mode="RGB").save(path)

    source_mtime = max(
        (REPO / "engine" / "base_registry_data.py").stat().st_mtime,
        (REPO / "shokker_engine_v2.py").stat().st_mtime,
        FINISH_DATA.stat().st_mtime if FINISH_DATA.exists() else 0.0,
    )

    eng = import_engine()
    size = int(args.size)
    manifest_path = THUMB_DIR / "manifest.json"
    existing: dict[str, dict] = {}
    if manifest_path.exists():
        try:
            for p in json.loads(manifest_path.read_text(encoding="utf-8")).get("bases", []):
                existing[p.get("id")] = p
        except Exception:
            pass

    results: list[dict] = []
    rendered = skipped = missing = 0
    t0_all = time.perf_counter()

    print(f"render candy-pearl: {len(queue_bases)} bases at {size}x{size}")

    for entry in queue_bases:
        base_id = entry["id"]
        swatch = entry.get("swatch") or swatches.get(base_id, "#888899")
        if base_id not in eng.BASE_REGISTRY:
            print(f"  MISSING registry: {base_id}")
            missing += 1
            continue
        if not needs_render(base_id, source_mtime, args.force):
            if base_id in existing:
                results.append(existing[base_id])
                skipped += 1
                continue

        t0 = time.perf_counter()
        try:
            paint_rgb, spec_u8 = render_base(eng, base_id, size, SEED, swatch)
        except Exception as exc:
            print(f"  FAIL {base_id}: {exc!r}")
            continue
        dt_ms = (time.perf_counter() - t0) * 1000.0

        spec_f = spec_u8.astype(np.float32) / 255.0
        M_arr = spec_f[:, :, 0]
        R_arr = spec_f[:, :, 1]
        CC_arr = spec_f[:, :, 2]
        spec_rgb = (spec_f * 255).astype(np.uint8)
        paint_u8 = (np.clip(paint_rgb, 0, 1) * 255).astype(np.uint8)

        write_png(paint_u8, THUMB_DIR / f"{base_id}_paint.png")
        write_png(spec_rgb, THUMB_DIR / f"{base_id}.png")
        write_png(tint_channel(M_arr, TINT_M), THUMB_DIR / f"{base_id}_M.png")
        write_png(tint_channel(R_arr, TINT_R), THUMB_DIR / f"{base_id}_R.png")
        write_png(tint_channel(CC_arr, TINT_CC), THUMB_DIR / f"{base_id}_CC.png")

        rendered += 1
        print(f"  [{rendered:2d}] {base_id:24s} {dt_ms:7.1f}ms")

        results.append({
            "id": base_id,
            "ms": round(dt_ms, 1),
            "swatch": swatch,
            "thumb_paint": f"_candy_pearl_thumbs/{base_id}_paint.png",
            "thumb_spec": f"_candy_pearl_thumbs/{base_id}.png",
            "thumb_M": f"_candy_pearl_thumbs/{base_id}_M.png",
            "thumb_R": f"_candy_pearl_thumbs/{base_id}_R.png",
            "thumb_CC": f"_candy_pearl_thumbs/{base_id}_CC.png",
            "M_mean": round(float(M_arr.mean()), 3),
            "M_std": round(float(M_arr.std()), 3),
            "R_mean": round(float(R_arr.mean()), 3),
            "R_std": round(float(R_arr.std()), 3),
            "CC_mean": round(float(CC_arr.mean()), 3),
            "CC_std": round(float(CC_arr.std()), 3),
        })

    manifest = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "group": "Candy & Pearl",
        "render_size": size,
        "bases": results,
    }
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    elapsed = time.perf_counter() - t0_all
    print(
        f"done: rendered={rendered} skipped={skipped} missing={missing} "
        f"in {elapsed:.1f}s -> {manifest_path.relative_to(REPO)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
