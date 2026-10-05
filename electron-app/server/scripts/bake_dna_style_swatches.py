"""Build-time bake of all DNA-style picker swatches (SPB 2026-06-08).

The SHOKK DROP "Choose DNA style" picker has ~75 tiles, each previously rendered LIVE by
the engine on first open (a full 2048x2048 Viva spec-plate bake apiece) into an empty
%APPDATA% cache — so a fresh install showed blank tiles for minutes while it baked them
one by one. This script bakes all of them ONCE and writes the 128px PNGs into a SHIPPABLE
location (<repo>/thumbnails/dna_style_swatches/<id>_v<VERSION>.png) that the installer
copies and that ensure_dna_style_swatch() now prefers — turning the cold open into instant
static-file reads.

Run before packaging (and re-run on any SWATCH_VERSION bump), from the repo root, with a
Python that has the engine deps (the bundled one works):
    electron-app\\server\\python\\python.exe scripts\\bake_dna_style_swatches.py
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.paint_v2.import_dna_style_catalog import DNA_STYLES  # noqa: E402
from engine.paint_v2 import dna_style_swatches as dss  # noqa: E402


def main() -> int:
    out_dir = dss._BUNDLED_SWATCH_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean slate for this version so we always bake fresh and never short-circuit on a
    # stale bundled swatch (ensure_dna_style_swatch prefers bundled files if present).
    for f in out_dir.glob(f"*_v{dss.SWATCH_VERSION}.png"):
        try:
            f.unlink()
        except Exception:
            pass

    styles = sorted(DNA_STYLES)
    total = len(styles)
    print(f"Baking {total} DNA-style swatches (v{dss.SWATCH_VERSION}) -> {out_dir}")
    t0 = time.time()
    ok = fail = 0
    for i, sid in enumerate(styles, 1):
        try:
            # bundled dir is empty for this id -> ensure_dna_style_swatch bakes via the exact
            # production path into %APPDATA%, returns that path; we copy it to the shipped dir.
            src = dss.ensure_dna_style_swatch(sid)
            dst = dss.bundled_swatch_path_for(sid)
            if Path(src).resolve() != dst.resolve():
                shutil.copy2(src, dst)
            ok += 1
            print(f"  [{i:>3}/{total}] OK   {sid} -> {dst.name}")
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"  [{i:>3}/{total}] FAIL {sid}: {e}")

    dt = time.time() - t0
    shipped = len(list(out_dir.glob(f"*_v{dss.SWATCH_VERSION}.png")))
    print(f"\nDONE in {dt:.1f}s — baked {ok}, failed {fail}, {shipped} swatches in {out_dir}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
