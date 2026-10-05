#!/usr/bin/env python3
"""Audit COLORSHOXX paint vs catalog description — flags identity mismatches."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.spb_rate_portal_lib import load_finish_meta, load_group_ids, render_finish


def _hue(rgb):
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    if mx - mn < 0.04:
        return None
    d = mx - mn
    if mx == r:
        h = (g - b) / d
    elif mx == g:
        h = 2 + (b - r) / d
    else:
        h = 4 + (r - g) / d
    return (h * 60) % 360


def _dominant_colors(paint: np.ndarray, k: int = 2):
    flat = paint.reshape(-1, 3)
    flat = flat[(flat.max(axis=1) - flat.min(axis=1)) > 0.06]
    if len(flat) < 64:
        return []
    qs = np.linspace(0.1, 0.9, k)
    out = []
    for q in qs:
        t = np.quantile(flat, q, axis=0)
        out.append(tuple(np.round(t, 3)))
    return out


def _parse_desc_colors(desc: str) -> list[str]:
    d = desc.lower()
    keys = []
    for word in (
        "crimson", "red", "blue", "gold", "green", "teal", "purple", "violet",
        "orange", "pink", "black", "white", "silver", "chrome", "cyan", "magenta",
        "yellow", "copper", "bronze", "burgundy", "obsidian", "ice", "fire",
    ):
        if word in d:
            keys.append(word)
    return keys


def main() -> int:
    import shokker_engine_v2 as eng

    eng._ensure_expansions_loaded()
    meta = load_finish_meta()
    ids = load_group_ids("★ COLORSHOXX")
    fails = []
    for fid in ids:
        m = meta.get(fid, {})
        desc = m.get("desc") or ""
        swatch = m.get("swatch", "#888899")
        try:
            paint, spec = render_finish(eng, fid, 512, "base", swatch)
        except Exception as exc:
            fails.append((fid, f"render error: {exc!r}"))
            continue
        dom = _dominant_colors(paint)
        spec_m = float(spec[:, :, 0].mean()) * 255
        if spec_m < 8:
            fails.append((fid, f"spec M mean ~0 (black channel bug?)"))
        expected = _parse_desc_colors(desc)
        if not expected or not dom:
            continue
        hues = [_hue(c) for c in dom if _hue(c) is not None]
        # chrome/black finishes should have low average luma in one cluster + high in other
        if "chrome" in expected and "black" in expected:
            lumas = [0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] for c in dom]
            if max(lumas) < 0.55 or min(lumas) > 0.35:
                fails.append((fid, f"chrome/black contrast weak lumas={[round(x,2) for x in lumas]}"))
        if "red" in expected and "blue" in expected and hues:
            has_warm = any(h < 40 or h > 320 for h in hues)
            has_cool = any(180 < h < 260 for h in hues)
            if not (has_warm and has_cool):
                fails.append((fid, f"red/blue not both present hues={[round(h,0) for h in hues]}"))
    out = ROOT / "_loop_state" / "colorshoxx_desc_audit.json"
    out.write_text(json.dumps({"fails": [{"id": a, "reason": b} for a, b in fails]}, indent=2), encoding="utf-8")
    print(f"audited {len(ids)} — failures {len(fails)} -> {out}")
    for a, b in fails[:20]:
        print(f"  {a}: {b}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
