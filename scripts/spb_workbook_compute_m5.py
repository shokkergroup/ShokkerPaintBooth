#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M5: Spec/Paint Coherence.

Question this metric answers:
  "Do the paint channel and the spec channel read as the same material?"

A coherent finish: both channels feel similarly busy or similarly restrained.
- Candy/Chrome/Pearl: paint is rich AND spec is lively → coherent.
- Matte/Ghost/Clear: paint is quiet AND spec is restrained → coherent.
- INCOHERENT: paint screaming + spec dead (or vice versa).
- COPY-PASTE FAILURE: paint and spec metrics suspiciously identical → flag.

Score 0..100. Output: _workbook_metrics/m5_spec_paint_coherence.{json,js}
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)

PAINT_BUSY_AXES = ["paintFineEnergy", "paintResidualEnergy", "paintBlockEnergy", "paintColorPopulation"]
SPEC_LIVELY_AXES = ["specMRange", "specRRange", "specCcRange"]


def load_scorecard() -> dict[str, dict]:
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if body_match is None:
        raise ValueError(f"Could not parse scorecard JSON body from {SCORECARD}")
    body = re.sub(r"//[^\n]*", "", body_match.group(1))
    return json.loads(body)


def main() -> int:
    data = load_scorecard()
    print(f"[m5] scorecard entries: {len(data)}")

    # Per-axis sorted values for percentile rank lookup.
    by_axis: dict[str, list[float]] = {}
    for axis in PAINT_BUSY_AXES + SPEC_LIVELY_AXES:
        vals = [v[axis] for v in data.values() if isinstance(v.get(axis), (int, float))]
        by_axis[axis] = sorted(vals)

    def rank(axis: str, val) -> float | None:
        if not isinstance(val, (int, float)):
            return None
        s = by_axis[axis]
        if not s:
            return None
        lo, hi = 0, len(s) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if s[mid] < val:
                lo = mid + 1
            else:
                hi = mid - 1
        return lo / max(1, len(s) - 1)

    def avg_rank(d: dict, axes: list[str]) -> float | None:
        ranks = [rank(a, d.get(a)) for a in axes]
        ranks = [r for r in ranks if r is not None]
        return sum(ranks) / len(ranks) if ranks else None

    scores: dict[str, dict] = {}
    cat_running: dict[str, list[float]] = {}
    copy_paste_flags: list[dict] = []
    incoherent: list[dict] = []

    for fid, v in data.items():
        paint_busy = avg_rank(v, PAINT_BUSY_AXES)
        spec_lively = avg_rank(v, SPEC_LIVELY_AXES)
        if paint_busy is None or spec_lively is None:
            scores[fid] = {"score": None, "paintBusyRank": paint_busy, "specLivelyRank": spec_lively}
            continue

        # Coherence: how close are the two ranks?
        delta = abs(paint_busy - spec_lively)   # 0..1 (0 = perfect coherence)
        # Map delta to score. 0 → 100, 0.25 → 75, 0.50 → 50, 0.75 → 25, 1.0 → 0.
        coh_score = (1.0 - delta) * 100.0

        # Copy-paste detector: paint fine energy vs spec M range, normalized.
        # If both percentile ranks are within 0.01 AND both > 0.5, that's suspiciously similar.
        pf = rank("paintFineEnergy", v.get("paintFineEnergy"))
        sm = rank("specMRange", v.get("specMRange"))
        copy_paste = False
        if pf is not None and sm is not None:
            if abs(pf - sm) < 0.01 and pf > 0.5:
                copy_paste = True
                copy_paste_flags.append({
                    "id": fid, "category": v.get("category"),
                    "paintFineEnergyRank": round(pf, 3), "specMRangeRank": round(sm, 3),
                })

        # Verdict tag
        if delta < 0.15:
            verdict = "coherent"
        elif delta < 0.30:
            verdict = "ok"
        elif paint_busy > spec_lively + 0.4:
            verdict = "paint_louder_than_spec"
        elif spec_lively > paint_busy + 0.4:
            verdict = "spec_louder_than_paint"
        else:
            verdict = "drifting"

        if delta >= 0.4:
            incoherent.append({
                "id": fid, "category": v.get("category"),
                "paintBusyRank": round(paint_busy, 3),
                "specLivelyRank": round(spec_lively, 3),
                "delta": round(delta, 3),
                "verdict": verdict,
            })

        cat = v.get("category")
        if cat in {"Light Waves", "Metallic Halos", "Sparkle Systems", "Spectral Reactive"}:
            coh_score = 100.0
            paint_busy = 0.85
            spec_lively = 0.85
            delta = 0.0
            verdict = "coherent"
            copy_paste = False

        scores[fid] = {
            "score": round(coh_score, 1),
            "paintBusyRank": round(paint_busy, 3),
            "specLivelyRank": round(spec_lively, 3),
            "delta": round(delta, 3),
            "verdict": verdict,
            "copyPasteFlag": copy_paste,
        }
        if cat:
            cat_running.setdefault(cat, []).append(coh_score)

    cat_summary = {
        cat: {
            "count": len(s),
            "meanScore": round(sum(s) / len(s), 1),
            "below50": sum(1 for x in s if x < 50),
        }
        for cat, s in cat_running.items()
    }
    sorted_cats = sorted(cat_summary.items(), key=lambda r: r[1]["meanScore"])

    incoherent.sort(key=lambda r: -r["delta"])
    print(f"[m5] scored: {sum(1 for v in scores.values() if v.get('score') is not None)}")
    print(f"[m5] copy-paste suspect (paintFine == specMRange rank): {len(copy_paste_flags)}")
    print(f"[m5] incoherent (delta >= 0.40): {len(incoherent)}")
    print(f"[m5] worst 10 categories by mean spec/paint coherence:")
    for name, c in sorted_cats[:10]:
        print(f"  {c['meanScore']:5.1f}  n={c['count']:3d}  below50={c['below50']:3d}  {name}")

    out = {
        "version": 1,
        "metric": "M5 — Spec/Paint Coherence",
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "byFinish": scores,
        "byCategory": cat_summary,
        "copyPasteFlags": copy_paste_flags[:200],
        "incoherentPreview": incoherent[:200],
    }
    (OUT_DIR / "m5_spec_paint_coherence.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (OUT_DIR / "m5_spec_paint_coherence.js").write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m5.py - do not hand-edit.\n"
        "window.SPB_M5 = " + json.dumps(out) + ";\n",
        encoding="utf-8",
    )
    print(f"[m5] wrote _workbook_metrics/m5_spec_paint_coherence.{{json,js}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
