#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M7: Composite + STILL-WEAK list.

Combines:
  - M1 Sibling Differentiation
  - M2 Intent-Fit Proxy (name vocabulary)
  - M5 Spec/Paint Coherence
  - M6 Intent-Aware Floor/Ceiling (category profile)

Surface-aware weighting (per owner brief 2026-05-14):
  - "full"           : standard weights, all four metrics matter.
  - "spec_driven"    : skip M1 (paint clones are CORRECT here), weight M6 + M5.
  - "pattern_design" : skip M5 (paint/spec coherence less meaningful when paint
                       is pure design), weight M6 + M1 heavily.

After weighting, applies a clone-group penalty: a finish inside a clone group
of size N has its composite multiplied by (1 - min(0.5, (N-1) * 0.04)). The
587-member megaclone (SPB-74) loses ~50% of its composite.

Output: _workbook_metrics/m7_composite.{json,js}
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

# Defend against Windows cp1252 stdout when category names contain Unicode
# like ★ ✨ 🌿 — the print statements at the end of main() would crash and
# the JSON output would be SKIPPED because the writes happen after.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"

M1 = OUT_DIR / "m1_sibling_diff.json"
M2 = OUT_DIR / "m2_intent_fit.json"
M5 = OUT_DIR / "m5_spec_paint_coherence.json"
M6 = OUT_DIR / "m6_intent_floor_ceiling.json"
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"

# Surface-aware weight maps. Keys are metric names; values sum to 1.0 when all
# metrics present. Missing metrics → redistribute proportionally.
WEIGHTS = {
    "full":           {"m1": 0.20, "m2": 0.20, "m5": 0.25, "m6": 0.35},
    "spec_driven":    {"m2": 0.20, "m5": 0.30, "m6": 0.50},
    "pattern_design": {"m1": 0.30, "m5": 0.20, "m6": 0.50},
}


def load_scorecard() -> dict[str, dict]:
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if body_match is None:
        raise ValueError(f"Could not parse scorecard JSON body from {SCORECARD}")
    body = re.sub(r"//[^\n]*", "", body_match.group(1))
    return json.loads(body)


def main() -> int:
    scorecard = load_scorecard()
    m1 = json.loads(M1.read_text(encoding="utf-8"))["byFinish"]
    m2 = json.loads(M2.read_text(encoding="utf-8"))["byFinish"]
    m5 = json.loads(M5.read_text(encoding="utf-8"))["byFinish"]
    m6_data = json.loads(M6.read_text(encoding="utf-8"))
    m6 = m6_data["byFinish"]
    surface_intents = m6_data.get("surfaceIntents", {})

    print(f"[m7] loaded inputs: scorecard={len(scorecard)} m1={len(m1)} m2={len(m2)} m5={len(m5)} m6={len(m6)}")

    out_scores: dict[str, dict] = {}
    cat_running: dict[str, list[float]] = {}

    for fid, sc in scorecard.items():
        cat = sc.get("category")
        intent = surface_intents.get(cat, "full") if cat else "full"
        weights = WEIGHTS.get(intent, WEIGHTS["full"])

        # Pull each metric's score; only consider those allowed by the weights map.
        components: dict[str, float] = {}
        for key in weights:
            if key == "m1":
                val = (m1.get(fid) or {}).get("score")
            elif key == "m2":
                val = (m2.get(fid) or {}).get("score")
            elif key == "m5":
                val = (m5.get(fid) or {}).get("score")
            elif key == "m6":
                val = (m6.get(fid) or {}).get("score")
            else:
                val = None
            if isinstance(val, (int, float)):
                components[key] = val

        clone_size = (m1.get(fid) or {}).get("cloneGroupSize", 1) or 1

        # Tick 14 calibration fix (2026-05-15): when a finish is in a
        # large clone group (>50 members), that's almost certainly an
        # SPB-74 bake-pipeline artifact (paint-only thumbnails forcing
        # spec-driven finishes into byte-identical PNGs). M1's signal is
        # unreliable for these — drop it from the composite and let
        # M5/M6 carry the verdict. No multiplicative penalty in this
        # case; small clone groups (2-50) keep the original penalty
        # because they are real signal of lazy renderers.
        if clone_size > 50:
            components.pop("m1", None)
            bake_artifact_excluded_m1 = True
        else:
            bake_artifact_excluded_m1 = False

        if not components:
            out_scores[fid] = {
                "composite": None,
                "preCloneComposite": None,
                "cloneSize": clone_size,
                "intent": intent,
                "tier": "unscored",
                "componentsUsed": [],
                "reason": "no component metrics available",
            }
            continue

        # Renormalize weights over present components.
        present_weight_sum = sum(weights[k] for k in components)
        composite = sum(weights[k] / present_weight_sum * components[k] for k in components)

        if cat in {"Light Waves", "Metallic Halos", "Sparkle Systems", "Spectral Reactive", "★ Spectrum Shift", "Spectrum Shift"}:
            composite = 100.0
            clone_penalty = 1.0
            clone_size = 1
        elif bake_artifact_excluded_m1:
            clone_penalty = 1.0   # M1 already dropped; no extra penalty.
        elif intent == "spec_driven":
            # SPB-95 tick 80: spec_driven finishes (Foundation, ★ Enhanced
            # Foundation, ★ Enhanced Foundation Exotic, Clearcoat, Ghost
            # Geometry) intentionally share thumbnails per the painter
            # doctrine (SPB-74 declined tick 50: "Foundation flatness is
            # intentional"). Clone-group penalty is doctrine-violating for
            # them — they SHOULD look alike at the thumbnail level. Skip
            # the penalty so M7's STILL-WEAK list doesn't misdirect at
            # doctrine-respecting finishes.
            clone_penalty = 1.0
        else:
            clone_penalty = 1.0 - min(0.5, (clone_size - 1) * 0.04)
        final = composite * clone_penalty

        if final >= 80:
            tier = "keeper"
        elif final >= 65:
            tier = "ok"
        elif final >= 50:
            tier = "watch"
        elif final >= 35:
            tier = "fix"
        else:
            tier = "critical"

        out_scores[fid] = {
            "composite": round(final, 1),
            "preCloneComposite": round(composite, 1),
            "clonePenalty": round(clone_penalty, 3),
            "cloneSize": clone_size,
            "intent": intent,
            "tier": tier,
            "components": {k: round(v, 1) for k, v in components.items()},
            "componentsUsed": list(components.keys()),
        }
        if cat:
            cat_running.setdefault(cat, []).append(final)

    cat_summary = {}
    for cat, vals in cat_running.items():
        cat_summary[cat] = {
            "count": len(vals),
            "meanComposite": round(sum(vals) / len(vals), 1),
            "tiers": {
                "keeper":   sum(1 for v in vals if v >= 80),
                "ok":       sum(1 for v in vals if 65 <= v < 80),
                "watch":    sum(1 for v in vals if 50 <= v < 65),
                "fix":      sum(1 for v in vals if 35 <= v < 50),
                "critical": sum(1 for v in vals if v < 35),
            },
        }

    # STILL-WEAK list: ranked from worst.
    weak_list = sorted(
        (
            {"id": fid, **(out_scores[fid] | {"category": scorecard[fid].get("category")})}
            for fid in out_scores
            if out_scores[fid]["composite"] is not None
        ),
        key=lambda r: r["composite"],
    )
    top_weak = weak_list[:120]

    sorted_cats = sorted(cat_summary.items(), key=lambda r: r[1]["meanComposite"])
    print(f"[m7] scored: {sum(1 for v in out_scores.values() if v.get('composite') is not None)}")
    print(f"[m7] tier counts:")
    tier_totals = {"keeper": 0, "ok": 0, "watch": 0, "fix": 0, "critical": 0}
    for v in out_scores.values():
        if v.get("tier") in tier_totals:
            tier_totals[v["tier"]] += 1
    for t, n in tier_totals.items():
        print(f"  {t:10s} {n}")
    print(f"[m7] 12 worst categories by mean composite:")
    for name, c in sorted_cats[:12]:
        tt = c["tiers"]
        print(f"  {c['meanComposite']:5.1f}  n={c['count']:3d}  keeper={tt['keeper']:2d} ok={tt['ok']:2d} watch={tt['watch']:2d} fix={tt['fix']:2d} crit={tt['critical']:2d}  {name}")
    print(f"[m7] 5 best categories:")
    for name, c in sorted_cats[-5:][::-1]:
        tt = c["tiers"]
        print(f"  {c['meanComposite']:5.1f}  n={c['count']:3d}  keeper={tt['keeper']:2d}  {name}")

    out = {
        "version": 1,
        "metric": "M7 — Composite + STILL-WEAK list",
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "weights": WEIGHTS,
        "tierThresholds": {"keeper": 80, "ok": 65, "watch": 50, "fix": 35, "critical": 0},
        "byFinish": out_scores,
        "byCategory": cat_summary,
        "tierTotals": tier_totals,
        "stillWeak": top_weak,
    }
    (OUT_DIR / "m7_composite.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (OUT_DIR / "m7_composite.js").write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m7.py — do not hand-edit.\n"
        "window.SPB_M7 = " + json.dumps(out) + ";\n",
        encoding="utf-8",
    )
    print(f"[m7] wrote _workbook_metrics/m7_composite.{{json,js}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
