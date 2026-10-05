#!/usr/bin/env python3
"""
SPB-74 path 3 — re-bake thumbnails for spec-driven finishes from the SPEC channel.

The standard `rebuild_thumbnails.py` renders the PAINT channel. For
spec-driven finishes (Foundation, Enhanced Foundation, Enhanced Foundation
Exotic, Ghost Geometry, Clearcoat) paint is intentionally flat by design,
so every paint-only thumbnail in those categories bakes to identical gray
— the SPB-74 587-megaclone problem (M8 = 0 for 631 catalog finishes).

This script renders the SPEC channel instead, using the pattern proven in
`bake_efx_spec_previews.py`. Decides per finish via the canonical
`engine.paint_v2.surface_intent.is_spec_driven()` API.

USAGE
-----

    # Dry run (default): report what WOULD be re-baked, no writes
    python scripts/bake_spec_driven_thumbnails.py

    # Test mode: bake to thumbnails/_spb74_test/<id>.png (safe to compare)
    python scripts/bake_spec_driven_thumbnails.py --test

    # Apply: OVERWRITE thumbnails/base/<id>.png. DESTRUCTIVE.
    python scripts/bake_spec_driven_thumbnails.py --apply

    # Limit to one category for incremental rollout:
    python scripts/bake_spec_driven_thumbnails.py --apply --category Foundation

POST-RUN
--------

After successful --apply, re-run:
    python scripts/spb_workbook_compute_m1.py    # rehash thumbnails
    python scripts/spb_workbook_compute_m7.py    # composite
    python scripts/spb_workbook_compute_m8.py    # thumbnail visibility

M8 mean for spec-driven categories should jump from ~0 to 30-70+ depending
on each finish's actual spec variation.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))

THUMBS_BASE = V5_ROOT / "thumbnails" / "base"
TEST_OUT = V5_ROOT / "thumbnails" / "_spb74_test"
SCORECARD = V5_ROOT / "paint-booth-0-catalog-scorecard.js"
FINISH_DATA = V5_ROOT / "paint-booth-0-finish-data.js"


# ============================================================================
# Spec → preview RGB (matches bake_efx_spec_previews.py)
# ============================================================================

def spec_to_rgb_preview(M, R, CC, swatch_hex: str) -> np.ndarray:
    """Compose RGB preview from M/R/CC with a mild swatch tint.

    High M = bright (metallic flash). Low R = bright (polished). High CC
    = depth contribution. Normalized against per-image dynamic range so
    dim finishes still show their structure.
    """
    sb = (M * 1.0 + (255.0 - R) * 0.6 + CC * 0.3) / 1.9
    sb = np.clip(sb, 0, 255)
    lo, hi = sb.min(), sb.max()
    if hi - lo > 2.0:
        sb = (sb - lo) / (hi - lo) * 255.0
    sb = np.clip(sb, 0, 255).astype(np.uint8)

    s = swatch_hex.lstrip("#")
    if len(s) == 6:
        tr, tg, tb = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    else:
        tr = tg = tb = 128

    tint = 0.30
    base = sb.astype(np.float32)
    r = base * (1.0 - tint) + (base * (tr / 255.0)) * tint
    g = base * (1.0 - tint) + (base * (tg / 255.0)) * tint
    b = base * (1.0 - tint) + (base * (tb / 255.0)) * tint
    return np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8] if path.is_file() else "—"


def parse_scorecard_categories() -> dict[str, str]:
    """Return {fid: category} from the scorecard JS."""
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(r'"([a-z_]+:[a-z0-9_]+)":\s*\{[^{}]*?"category":\s*"([^"]+)"', txt, flags=re.S):
        out[m.group(1)] = m.group(2)
    return out


def parse_swatches() -> dict[str, str]:
    """Return {stem: swatch_hex} from finish-data.js."""
    txt = FINISH_DATA.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r'id:\s*"([a-z_][a-z0-9_]*)"[^}]*?swatch:\s*"(#[0-9a-fA-F]{6})"', txt):
        out[m.group(1)] = m.group(2)
    return out


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--apply", action="store_true",
                    help="Overwrite thumbnails/base/<id>.png. DESTRUCTIVE.")
    ap.add_argument("--test", action="store_true",
                    help="Bake to thumbnails/_spb74_test/<id>.png instead of overwriting.")
    ap.add_argument("--category", type=str, default=None,
                    help="Limit to a single category (e.g. 'Foundation').")
    ap.add_argument("--render", type=int, default=2048,
                    help="Render resolution (default 2048 = real car-body scale).")
    ap.add_argument("--thumb", type=int, default=256,
                    help="Output thumbnail size (default 256).")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N finishes (default 0 = unlimited).")
    args = ap.parse_args()

    mode = "apply" if args.apply else "test" if args.test else "dry-run"
    print(f"[spb74-bake] mode={mode}  render={args.render}  thumb={args.thumb}")

    from engine.paint_v2.surface_intent import is_spec_driven, get_intent  # noqa: E402

    import shokker_engine_v2 as eng  # noqa: F401 — triggers BASE_REGISTRY build
    base = eng.BASE_REGISTRY
    print(f"[spb74-bake] BASE_REGISTRY entries: {len(base)}")

    categories = parse_scorecard_categories()
    swatches = parse_swatches()
    print(f"[spb74-bake] scorecard categories: {len(categories)}  swatches: {len(swatches)}")

    mono = getattr(eng, "MONOLITHIC_REGISTRY", {})
    print(f"[spb74-bake] MONOLITHIC_REGISTRY entries: {len(mono)}")

    # Build the work list: finishes in spec-driven categories with a callable
    # spec_fn. Covers both `base:` (BASE_REGISTRY entries) and `monolithic:`
    # (MONOLITHIC_REGISTRY entries). The two have different signatures:
    #   base spec_fn:        (shape, seed, sm, M, R) -> (M_arr, R_arr, CC_arr)
    #   monolithic spec_fn:  (shape, mask, seed, sm) -> (H, W, 4) ndarray
    work = []  # (surface, stem, category, callable, kind)
    seen_categories = {}
    for fid_with_prefix, category in categories.items():
        if args.category and category != args.category:
            continue
        if not is_spec_driven(category):
            continue
        surface, _, stem = fid_with_prefix.partition(":")
        if surface == "base":
            entry = base.get(stem)
            if not entry or not callable(entry.get("base_spec_fn")):
                continue
            work.append(("base", stem, category, entry, "base"))
        elif surface == "monolithic":
            entry = mono.get(stem)
            if not entry or not (isinstance(entry, tuple) and len(entry) >= 1 and callable(entry[0])):
                continue
            work.append(("monolithic", stem, category, entry, "monolithic"))
        else:
            continue
        seen_categories[category] = seen_categories.get(category, 0) + 1
        if args.limit and len(work) >= args.limit:
            break

    print(f"[spb74-bake] {len(work)} spec-driven finishes will be re-baked")
    for cat, n in sorted(seen_categories.items(), key=lambda r: -r[1]):
        print(f"  {n:4d}  {cat}")

    if mode == "dry-run":
        print()
        print("[spb74-bake] DRY RUN — no files written. Run with --test or --apply to bake.")
        return 0

    out_dir = TEST_OUT if mode == "test" else THUMBS_BASE
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[spb74-bake] output → {out_dir}")
    print()

    diffs = []  # (stem, before_hash, after_hash, render_seconds)
    for i, (surface, stem, category, entry, kind) in enumerate(work, 1):
        before_hash = file_hash(THUMBS_BASE / f"{stem}.png")
        seed = hash(stem) & 0x7FFFFFFF
        t0 = time.time()
        try:
            if kind == "monolithic":
                # monolithic: (spec_fn, paint_fn); spec_fn(shape, mask, seed, sm) -> (H,W,4)
                spec_fn = entry[0]
                full_mask = np.ones((args.render, args.render), dtype=np.float32)
                arr = spec_fn((args.render, args.render), full_mask, seed, 1.0)
                if arr.ndim != 3 or arr.shape[2] < 3:
                    raise ValueError(f"monolithic spec_fn returned unexpected shape {arr.shape}")
                M  = arr[:, :, 0].astype(np.float32, copy=False)
                R  = arr[:, :, 1].astype(np.float32, copy=False)
                CC = arr[:, :, 2].astype(np.float32, copy=False)
            else:
                # base: (shape, seed, sm, M, R) -> (M, R) or (M, R, CC)
                result = entry["base_spec_fn"]((args.render, args.render), seed, 1.0,
                                                entry.get("M", 128), entry.get("R", 80))
                if len(result) == 2:
                    M, R = result
                    CC = np.full_like(M, max(16.0, float(entry.get("CC", 16))), dtype=np.float32)
                else:
                    M, R, CC = result
        except Exception as exc:
            print(f"  [{i:4d}/{len(work)}]  FAIL  {stem}: {exc}")
            continue
        rgb_full = spec_to_rgb_preview(M, R, CC, swatches.get(stem, "#808080"))
        img = Image.fromarray(rgb_full).resize((args.thumb, args.thumb), Image.LANCZOS)
        out_path = out_dir / f"{stem}.png"
        img.save(out_path)
        after_hash = file_hash(out_path)
        dt = time.time() - t0
        changed = "✓" if before_hash != after_hash else "—"
        if i <= 20 or i % 50 == 0 or i == len(work):
            print(f"  [{i:4d}/{len(work)}]  {dt:4.1f}s  {changed}  {stem:38s} before={before_hash} after={after_hash}")
        diffs.append((stem, before_hash, after_hash, dt))

    total_changed = sum(1 for s, b, a, _ in diffs if b != a)
    total_time = sum(d for _, _, _, d in diffs)
    print()
    print(f"[spb74-bake] done. {len(diffs)} baked, {total_changed} changed hash, {total_time:.1f}s total")
    print(f"[spb74-bake] output: {out_dir}")
    if mode == "test":
        print(f"[spb74-bake] compare: open thumbnails/base/<id>.png vs thumbnails/_spb74_test/<id>.png side by side")
    if mode == "apply":
        print(f"[spb74-bake] NEXT: re-run M1 + M7 + M8 to see the catalog-level improvement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
