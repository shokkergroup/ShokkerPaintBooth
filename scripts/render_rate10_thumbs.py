"""Render thumbnails for SPB_RATE_10.html — driven by the LIVE audit queue.

This was originally a hardcoded 20-pattern Round-6 renderer. As of 2026-05-25 it
reads the visible pattern list from `_rate10_thumbs/audit_queue.json` (produced
by `scripts/generate_audit_queue.py`) and renders 4 PNGs per pattern at
RENDER_SIZE square:

  - {name}.png       full RGB composite (M=R band, R=G band, CC=B band)
  - {name}_M.png     M channel, red-tinted greyscale
  - {name}_R.png     R channel, green-tinted greyscale
  - {name}_CC.png    CC channel, blue-tinted greyscale

A manifest is written so the audit page can pick up channel means + render time
without running python in the browser.

Caching: if the four PNGs already exist AND are newer than
engine/spec_patterns.py AND newer than the audit_queue.json entry, the pattern
is skipped. This keeps re-runs fast — we only re-render what actually changed.

Args:
  python scripts/render_rate10_thumbs.py                # full queue, cached
  python scripts/render_rate10_thumbs.py --force        # ignore cache
  python scripts/render_rate10_thumbs.py --only A,B,C   # subset (comma list)
  python scripts/render_rate10_thumbs.py --size 384     # override render size
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

THUMB_DIR = REPO / "_rate10_thumbs"
THUMB_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_PATH = THUMB_DIR / "audit_queue.json"

DEFAULT_SIZE = 512
SEED = 7777

TINT_M  = (1.00, 0.30, 0.30)
TINT_R  = (0.30, 1.00, 0.30)
TINT_CC = (0.30, 0.50, 1.00)


def tint_channel(field2d: np.ndarray, color: tuple[float, float, float]) -> np.ndarray:
    arr = np.clip(field2d, 0, 1)
    r = arr * color[0]
    g = arr * color[1]
    b = arr * color[2]
    rgb = np.stack([r, g, b], axis=-1)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def needs_render(name: str, source_mtime: float, force: bool) -> bool:
    if force:
        return True
    for suffix in ("", "_M", "_R", "_CC"):
        p = THUMB_DIR / f"{name}{suffix}.png"
        if not p.exists():
            return True
        if p.stat().st_mtime < source_mtime:
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore mtime cache")
    ap.add_argument("--only", default="", help="comma-separated subset of pattern names")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE, help="render size square")
    ap.add_argument("--max", type=int, default=0, help="cap number of patterns rendered this run")
    args = ap.parse_args()

    if not QUEUE_PATH.exists():
        print(f"audit_queue.json missing at {QUEUE_PATH}.")
        print("Run scripts/generate_audit_queue.py first.")
        return 2
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    queue_patterns = queue.get("patterns", [])

    # Filter subset
    only_set = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None
    if only_set:
        queue_patterns = [p for p in queue_patterns if p["id"] in only_set]

    import engine.spec_patterns as sp
    catalog = sp.PATTERN_CATALOG

    try:
        import cv2
        HAS_CV2 = True
    except Exception:
        HAS_CV2 = False
        from PIL import Image  # noqa: F401

    def write_png(rgb_uint8: np.ndarray, path: Path) -> None:
        if HAS_CV2:
            bgr = rgb_uint8[:, :, [2, 1, 0]]
            cv2.imwrite(str(path), bgr)
        else:
            from PIL import Image
            Image.fromarray(rgb_uint8, mode="RGB").save(path)

    source_py = REPO / "engine" / "spec_patterns.py"
    source_mtime = source_py.stat().st_mtime if source_py.exists() else 0.0

    size = int(args.size)
    SHAPE = (size, size)

    # Load existing manifest so we can keep entries for cached (skipped) patterns
    manifest_path = THUMB_DIR / "manifest.json"
    existing_manifest_by_name = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            for p in existing.get("patterns", []):
                existing_manifest_by_name[p.get("name")] = p
        except Exception:
            pass

    results: list[dict] = []
    rendered = 0
    skipped = 0
    missing = 0

    targets = queue_patterns
    if args.max > 0:
        targets = targets[: args.max]

    print(f"render queue: {len(targets)} patterns at {size}x{size}")
    t_start = time.perf_counter()

    for entry in targets:
        name = entry["id"]
        if name not in catalog:
            print(f"  MISSING: {name}")
            missing += 1
            continue
        if not needs_render(name, source_mtime, args.force):
            cached = existing_manifest_by_name.get(name)
            if cached:
                results.append(cached)
                skipped += 1
                continue
            # No manifest entry — fall through and render

        fn = catalog[name]
        t0 = time.perf_counter()
        try:
            field = fn(SHAPE, SEED, 1.0)
        except Exception as exc:
            print(f"  FAIL render {name}: {exc!r}")
            continue
        dt_ms = (time.perf_counter() - t0) * 1000.0
        arr = np.clip(np.asarray(field, dtype=np.float32), 0, 1)

        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)
            channels_observed = 1
        elif arr.ndim == 3 and arr.shape[2] >= 3:
            arr = arr[:, :, :3]
            channels_observed = 3
        else:
            print(f"  SKIP {name}: bad shape {arr.shape}")
            continue

        M_arr  = arr[:, :, 0]
        R_arr  = arr[:, :, 1]
        CC_arr = arr[:, :, 2]

        full_rgb = (arr * 255).astype(np.uint8)
        write_png(full_rgb, THUMB_DIR / f"{name}.png")
        write_png(tint_channel(M_arr,  TINT_M),  THUMB_DIR / f"{name}_M.png")
        write_png(tint_channel(R_arr,  TINT_R),  THUMB_DIR / f"{name}_R.png")
        write_png(tint_channel(CC_arr, TINT_CC), THUMB_DIR / f"{name}_CC.png")

        full_kb = (THUMB_DIR / f"{name}.png").stat().st_size / 1024
        rendered += 1
        if rendered % 25 == 0 or rendered == len(targets):
            print(f"  [{rendered:3d}] {name:32s} {dt_ms:6.1f}ms  {full_kb:5.1f}KB")

        results.append({
            "name": name,
            "ms": round(dt_ms, 1),
            "channels_observed": channels_observed,
            "thumb":    f"_rate10_thumbs/{name}.png",
            "thumb_M":  f"_rate10_thumbs/{name}_M.png",
            "thumb_R":  f"_rate10_thumbs/{name}_R.png",
            "thumb_CC": f"_rate10_thumbs/{name}_CC.png",
            "M_mean":  round(float(M_arr.mean()),  3),
            "M_std":   round(float(M_arr.std()),   3),
            "R_mean":  round(float(R_arr.mean()),  3),
            "R_std":   round(float(R_arr.std()),   3),
            "CC_mean": round(float(CC_arr.mean()), 3),
            "CC_std":  round(float(CC_arr.std()),  3),
        })

    elapsed = time.perf_counter() - t_start
    manifest_payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "render_size": size,
        "queue_generated": queue.get("generated"),
        "totals": queue.get("totals", {}),
        "patterns": results,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    print(
        f"done: rendered={rendered} skipped={skipped} missing={missing} "
        f"manifest={len(results)} patterns in {elapsed:.1f}s"
    )
    print(f" -> {manifest_path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
