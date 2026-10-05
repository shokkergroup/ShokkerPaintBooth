"""Render thumbnails for SPEC_OVERLAY_DEFINITIVE_AUDIT.html."""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

THUMB_DIR = ROOT / "_spec_overlay_definitive"
CATALOG_PATH = THUMB_DIR / "catalog.json"
MANIFEST_PATH = THUMB_DIR / "manifest.json"
DEFAULT_SIZE = 448
SEED = 52950

TINT_M = (1.00, 0.30, 0.30)
TINT_R = (0.30, 1.00, 0.30)
TINT_CC = (0.30, 0.50, 1.00)


def tint_channel(field2d: np.ndarray, color: tuple[float, float, float]) -> np.ndarray:
    arr = np.clip(field2d, 0, 1)
    rgb = np.stack([arr * color[0], arr * color[1], arr * color[2]], axis=-1)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def placeholder(title: str, error: str, size: int) -> np.ndarray:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (size, size), (20, 18, 18))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size - 1, size - 1], outline=(190, 55, 55), width=4)
    draw.text((18, 22), "RENDER FAILED", fill=(255, 140, 140))
    draw.text((18, 52), title[:34], fill=(238, 238, 238))
    draw.text((18, 82), error[:68], fill=(210, 160, 160))
    return np.asarray(img, dtype=np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE)
    args = ap.parse_args()

    if not CATALOG_PATH.exists():
        print(f"Missing {CATALOG_PATH.relative_to(ROOT)}. Run generate_spec_overlay_definitive_catalog.py first.")
        return 2

    queue = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    all_patterns = queue.get("patterns", [])
    patterns = list(all_patterns)
    only = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None
    if only:
        patterns = [p for p in patterns if p.get("id") in only]

    import engine.spec_patterns as sp

    try:
        import cv2
        has_cv2 = True
    except Exception:
        has_cv2 = False

    def write_png(rgb_uint8: np.ndarray, path: Path) -> None:
        if has_cv2:
            cv2.imwrite(str(path), rgb_uint8[:, :, [2, 1, 0]])
        else:
            from PIL import Image
            Image.fromarray(rgb_uint8, mode="RGB").save(path)

    source_py = ROOT / "engine" / "spec_pattern_families" / "definitive_replacements.py"
    source_mtime = source_py.stat().st_mtime if source_py.exists() else 0.0
    existing: dict[str, dict] = {}
    if MANIFEST_PATH.exists():
        try:
            for item in json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("patterns", []):
                if item.get("name"):
                    existing[item["name"]] = item
        except Exception:
            existing = {}

    def needs_render(identifier: str) -> bool:
        if args.force:
            return True
        for suffix in ("", "_M", "_R", "_CC"):
            p = THUMB_DIR / f"{identifier}{suffix}.png"
            if not p.exists() or p.stat().st_mtime < source_mtime:
                return True
        return identifier not in existing

    size = int(args.size)
    shape = (size, size)
    manifest: list[dict] = []
    manifest_by_name: dict[str, dict] = {}
    rendered = skipped = failed = 0
    started = time.perf_counter()
    print(f"render definitive spec thumbnails: {len(patterns)} patterns at {size}x{size}")

    for idx, entry in enumerate(patterns, start=1):
        identifier = entry["id"]
        if not needs_render(identifier):
            manifest.append(existing[identifier])
            skipped += 1
            continue
        t0 = time.perf_counter()
        try:
            fn = sp.PATTERN_CATALOG[identifier]
            arr = np.clip(np.asarray(fn(shape, SEED, 1.0), dtype=np.float32), 0, 1)
            if arr.ndim == 2:
                arr = np.stack([arr, arr, arr], axis=-1)
                channels_observed = 1
            elif arr.ndim == 3 and arr.shape[2] >= 3:
                arr = arr[:, :, :3]
                channels_observed = 3
            else:
                raise ValueError(f"bad renderer shape {arr.shape}")
        except Exception as exc:
            failed += 1
            channels_observed = 0
            full_rgb = placeholder(entry.get("title") or identifier, repr(exc), size)
            arr = full_rgb.astype(np.float32) / 255.0
        else:
            full_rgb = (arr * 255).astype(np.uint8)

        m_arr = arr[:, :, 0]
        r_arr = arr[:, :, 1]
        cc_arr = arr[:, :, 2]
        write_png(full_rgb, THUMB_DIR / f"{identifier}.png")
        write_png(tint_channel(m_arr, TINT_M), THUMB_DIR / f"{identifier}_M.png")
        write_png(tint_channel(r_arr, TINT_R), THUMB_DIR / f"{identifier}_R.png")
        write_png(tint_channel(cc_arr, TINT_CC), THUMB_DIR / f"{identifier}_CC.png")

        ms = (time.perf_counter() - t0) * 1000.0
        rendered += 1
        if rendered % 10 == 0 or idx == len(patterns):
            print(f"  [{idx:2d}/{len(patterns):2d}] {identifier:34s} {ms:7.1f}ms")

        manifest_item = {
            "name": identifier,
            "ms": round(ms, 1),
            "channels_observed": channels_observed,
            "thumb": f"_spec_overlay_definitive/{identifier}.png",
            "thumb_M": f"_spec_overlay_definitive/{identifier}_M.png",
            "thumb_R": f"_spec_overlay_definitive/{identifier}_R.png",
            "thumb_CC": f"_spec_overlay_definitive/{identifier}_CC.png",
            "M_mean": round(float(m_arr.mean()), 3),
            "M_std": round(float(m_arr.std()), 3),
            "R_mean": round(float(r_arr.mean()), 3),
            "R_std": round(float(r_arr.std()), 3),
            "CC_mean": round(float(cc_arr.mean()), 3),
            "CC_std": round(float(cc_arr.std()), 3),
        }
        manifest.append(manifest_item)
        manifest_by_name[identifier] = manifest_item

    if only:
        # Focused rebuilds should update selected rows without shrinking the
        # audit manifest away from the full definitive 50-card collection.
        manifest_by_name = {**existing, **manifest_by_name}
        manifest = []
        for entry in all_patterns:
            identifier = entry["id"]
            item = manifest_by_name.get(identifier)
            if item is None:
                item = {
                    "name": identifier,
                    "ms": None,
                    "channels_observed": 0,
                    "thumb": entry["thumb"],
                    "thumb_M": entry["thumb_M"],
                    "thumb_R": entry["thumb_R"],
                    "thumb_CC": entry["thumb_CC"],
                }
            manifest.append(item)

    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "render_size": size,
        "totals": queue.get("totals", {}),
        "patterns": manifest,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    elapsed = time.perf_counter() - started
    print(f"done: rendered={rendered} skipped={skipped} failed={failed} manifest={len(manifest)} in {elapsed:.1f}s")
    print(f" -> {MANIFEST_PATH.relative_to(ROOT)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
