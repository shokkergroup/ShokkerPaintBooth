#!/usr/bin/env python3
"""Write ``{id}_spec.png`` for each Union Jacked finish (same channel semantics as VM).

Scratch-built RGBA at 2048×2048 — runtime loads this file like Viva Mexico ``*_spec.png``,
then applies ``_pre_adjust_viva_mexico_spec`` / mask / ``sm`` / ``_post_adjust``.

Run after ``process_union_jacked_assets.py``:
  python scripts/bake_union_jacked_specs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.paint_v2.cultural_union_jacked import bake_union_jacked_scratch_spec_u8  # noqa: E402

_MANIFEST = ROOT / "assets" / "reference_textures" / "cultural" / "union_jacked" / "manifest.json"
_ASSET_DIR = _MANIFEST.parent


def main() -> None:
    data = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    finishes = data.get("finishes") or []
    for f in finishes:
        fid = str(f["id"])
        tex_path = _ASSET_DIR / f"{fid}.png"
        if not tex_path.exists():
            print("skip missing paint", fid, flush=True)
            continue
        out_path = _ASSET_DIR / f"{fid}_spec.png"
        arr_u8 = bake_union_jacked_scratch_spec_u8(fid)
        Image.fromarray(arr_u8, mode="RGBA").save(out_path, optimize=True)
        print("wrote", out_path.name, flush=True)


if __name__ == "__main__":
    main()
