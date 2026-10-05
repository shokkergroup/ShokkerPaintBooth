#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M8: Thumbnail-Scale Visibility.

Owner-driven discovery (2026-05-15): a generator can have rich high-frequency
content at 2048 (octaves 512/1024/2048) but show as a flat smear in the
picker thumbnail because the 8× downsample averages those bands into mush.

M8 measures the std of mean-pooled blocks at the thumbnail scale. Specifically:
- Read each finish's thumbnail (256×256)
- Compute mean intensity per 32-pixel block (8×8 grid of block-means)
- Std of those means = how much VISIBLE-SCALE structure the finish has

Threshold-based scoring:
- macro_std < 2:    0 (flat smear, owner will reject)
- macro_std < 5:   30 (weak, struggling to read as structured)
- macro_std < 10:  60 (acceptable, has visible character)
- macro_std < 20:  85 (strong, clear cellular/zoned/banded structure)
- macro_std >= 20: 100 (very strong, premium finish territory)

Output: _workbook_metrics/m8_thumb_visibility.{json,js}

NOT included in M7 composite yet — needs owner sign-off that it tracks
their actual visual judgment. But the metric is computed for every finish
so the workbook can surface "thumbnail-flat" finishes regardless.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
from PIL import Image  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)
THUMBS = PROJECT_ROOT / "thumbnails"


def macro_std_blocks(arr: np.ndarray, block_size: int = 32) -> float:
    """Std of block-mean intensities. Captures structure visible at block scale."""
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    h, w = arr.shape
    bh, bw = h // block_size, w // block_size
    if bh < 2 or bw < 2:
        return float(arr.std())
    b = arr[:bh * block_size, :bw * block_size].reshape(bh, block_size, bw, block_size)
    return float(b.mean(axis=(1, 3)).std())


def score(macro_std: float) -> float:
    if macro_std < 2:    return 0.0
    if macro_std < 5:    return 30.0 + (macro_std - 2) / 3 * 30
    if macro_std < 10:   return 60.0 + (macro_std - 5) / 5 * 25
    if macro_std < 20:   return 85.0 + (macro_std - 10) / 10 * 15
    return 100.0


def main() -> int:
    import re
    sc_text = (PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8")
    sc_ids = re.findall(r'"([a-z_]+:[a-z0-9_]+)"\s*:\s*\{', sc_text)
    # Also include efx_* finishes that aren't in scorecard yet (SPB-84 pending).
    efx_files = sorted((THUMBS / "base").glob("efx_*.png"))
    efx_ids = [f"base:{p.stem}" for p in efx_files]
    all_ids = list(dict.fromkeys(sc_ids + efx_ids))

    out_scores = {}
    cat_running = {}
    flat_finishes = []  # M8 < 30 — "thumbnail flat" red flags
    print(f"[m8] scoring {len(all_ids)} finishes")
    for fid in all_ids:
        if ":" not in fid:
            continue
        prefix, stem = fid.split(":", 1)
        # Map scorecard prefix to thumbnail folder
        folder = {"base": "base", "monolithic": "monolithic", "pattern": "pattern",
                  "spec_pattern": "spec_patterns"}.get(prefix, "base")
        path = THUMBS / folder / f"{stem}.png"
        if not path.is_file():
            out_scores[fid] = {"score": None, "macroStd": None, "reason": "no thumbnail"}
            continue
        try:
            arr = np.array(Image.open(path))
            ms = macro_std_blocks(arr, block_size=32)
            s = score(ms)
            out_scores[fid] = {"score": round(s, 1), "macroStd": round(ms, 2)}
            if s < 30:
                flat_finishes.append({"id": fid, "macroStd": round(ms, 2), "score": round(s, 1)})
            # Pull category from scorecard text (greedy entry match then cat extract).
            entry_match = re.search(r'"' + re.escape(fid) + r'":\s*\{[^{}]+\}', sc_text, flags=re.S)
            if entry_match:
                cm = re.search(r'"category":\s*"([^"]+)"', entry_match.group(0))
                if cm:
                    cat = cm.group(1)
                    cat_running.setdefault(cat, []).append(s)
        except Exception as exc:
            out_scores[fid] = {"score": None, "macroStd": None, "reason": str(exc)}

    cat_summary = {
        c: {"count": len(v), "meanScore": round(sum(v) / len(v), 1),
             "below30": sum(1 for x in v if x < 30)}
        for c, v in cat_running.items()
    }
    flat_finishes.sort(key=lambda r: r["macroStd"])
    sorted_cats = sorted(cat_summary.items(), key=lambda r: r[1]["meanScore"])
    scored_count = sum(1 for v in out_scores.values() if v.get("score") is not None)
    print(f"[m8] scored: {scored_count}")
    print(f"[m8] thumbnail-flat finishes (M8 < 30): {len(flat_finishes)}")
    print(f"[m8] worst 10 categories:")
    for name, c in sorted_cats[:10]:
        print(f"  {c['meanScore']:5.1f}  n={c['count']:3d}  below30={c['below30']:3d}  {name}")

    out = {
        "version": 1,
        "metric": "M8 — Thumbnail-Scale Visibility",
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "scoring": "Std of mean-pooled 32px blocks of thumbnail. Sub-2 = flat, >=20 = strong.",
        "byFinish": out_scores,
        "byCategory": cat_summary,
        "flatFinishesPreview": flat_finishes[:200],
    }
    (OUT_DIR / "m8_thumb_visibility.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (OUT_DIR / "m8_thumb_visibility.js").write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m8.py — do not hand-edit.\n"
        "window.SPB_M8 = " + json.dumps(out) + ";\n",
        encoding="utf-8",
    )
    print(f"[m8] wrote _workbook_metrics/m8_thumb_visibility.{{json,js}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
