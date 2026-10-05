#!/usr/bin/env python3
"""Merge pattern weakness signals into one rework queue + category priorities.

Inputs (refresh independently):
  - _workbook_metrics/m7_composite.json          (pattern:* M7 tiers)
  - audit/pattern_quality/*/report.json          (audit_pattern_quality.py)
  - _workbook_metrics/m_pattern_paint_chroma.json (audit_pattern_paint_chroma.py)

Outputs:
  - _workbook_metrics/m_pattern_weakness_rollup.json
  - _workbook_metrics/m_pattern_weakness_rollup.js  (window.SPB_PATTERN_WEAKNESS)

USAGE
-----
    python scripts/audit_pattern_quality.py
    python scripts/audit_pattern_paint_chroma.py
    python scripts/spb_pattern_weakness_rollup.py
    python scripts/build_category_workbench.py --from-rollup
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
METRICS = REPO / "_workbook_metrics"
SCORECARD = REPO / "paint-booth-0-catalog-scorecard.js"

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _latest_audit_report() -> Path | None:
    root = REPO / "audit" / "pattern_quality"
    if not root.is_dir():
        return None
    dirs = sorted([p for p in root.iterdir() if p.is_dir()], reverse=True)
    for d in dirs:
        report = d / "report.json"
        if report.exists():
            return report
    return None


def _tier_penalty(tier: str) -> float:
    return {
        "keeper": 0,
        "ok": 8,
        "watch": 22,
        "fix": 38,
        "critical": 55,
    }.get(tier or "watch", 25)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=str(METRICS / "m_pattern_weakness_rollup.json"))
    args = ap.parse_args()

    m7 = _load_json(METRICS / "m7_composite.json") or {}
    m7_by = m7.get("byFinish") or {}
    chroma = _load_json(METRICS / "m_pattern_paint_chroma.json") or {}
    chroma_by = {r["id"]: r for r in chroma.get("results") or [] if r.get("id")}

    audit_path = _latest_audit_report()
    audit = _load_json(audit_path) if audit_path else None
    audit_by = {}
    if audit:
        for row in audit.get("rows") or []:
            audit_by[row["id"]] = row

    scorecard = {}
    if SCORECARD.exists():
        scorecard_txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"=\s*(\{.*\});", scorecard_txt, flags=re.S)
        if m:
            body = re.sub(r"//[^\n]*", "", m.group(1))
            scorecard = json.loads(body)

    rows = []
    for fid, sc in scorecard.items():
        if not fid.startswith("pattern:"):
            continue
        pid = fid.split(":", 1)[1]
        cat = sc.get("category") or "Ungrouped"
        m7row = m7_by.get(fid) or {}
        arow = audit_by.get(pid) or {}
        crow = chroma_by.get(pid) or {}

        quality = float(arow.get("score") or 0)
        m7_comp = float(m7row.get("composite") or 0)
        tier = m7row.get("tier") or "watch"

        flags = list(arow.get("flags") or [])
        if crow.get("chroma_baked"):
            flags.append("CHROMA_BAKED")
        if arow.get("rebuild_required"):
            flags.append("AUDIT_REBUILD")

        # Rework score: higher = worse (needs attention first)
        rework = 0.0
        if quality > 0:
            rework += max(0.0, 100.0 - quality) * 0.45
        rework += _tier_penalty(tier)
        if crow.get("chroma_baked"):
            rework += 25.0
        if "BROKEN_RENDER" in flags:
            rework += 40.0
        if m7_comp > 0 and m7_comp < 50:
            rework += 15.0

        action = "keeper"
        if rework >= 55 or tier == "critical" or "AUDIT_REBUILD" in flags:
            action = "total_rework"
        elif rework >= 35 or tier in ("fix", "watch") or crow.get("chroma_baked"):
            action = "engine_or_chroma_fix"
        elif quality >= 88 and not crow.get("chroma_baked"):
            action = "keeper"

        rows.append({
            "fid": fid,
            "id": pid,
            "category": cat,
            "m7_composite": round(m7_comp, 1) if m7_comp else None,
            "m7_tier": tier,
            "audit_score": round(quality, 1) if quality else None,
            "mean_cosine": crow.get("mean_cosine"),
            "chroma_baked": bool(crow.get("chroma_baked")),
            "flags": flags,
            "rework_score": round(rework, 1),
            "action": action,
        })

    rows.sort(key=lambda r: (-r["rework_score"], r["id"]))

    cat_stats: dict[str, dict] = {}
    for r in rows:
        c = r["category"]
        bucket = cat_stats.setdefault(c, {"count": 0, "total_rework": 0, "rework_scores": []})
        bucket["count"] += 1
        bucket["rework_scores"].append(r["rework_score"])
        if r["action"] == "total_rework":
            bucket["total_rework"] += 1

    cat_summary = []
    for cat, st in cat_stats.items():
        scores = st["rework_scores"]
        cat_summary.append({
            "category": cat,
            "count": st["count"],
            "total_rework": st["total_rework"],
            "mean_rework_score": round(float(sum(scores) / len(scores)), 1) if scores else 0,
        })
    cat_summary.sort(key=lambda x: (-x["mean_rework_score"], x["category"]))

    payload = {
        "metric": "Pattern weakness rollup",
        "audit_report": str(audit_path) if audit_path else None,
        "n_patterns": len(rows),
        "n_total_rework": sum(1 for r in rows if r["action"] == "total_rework"),
        "n_chroma_baked": sum(1 for r in rows if r["chroma_baked"]),
        "category_priority": [c["category"] for c in cat_summary[:20]],
        "byCategory": cat_summary,
        "rework_queue": rows[:120],
        "all": rows,
    }

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out.with_suffix(".js").write_text(
        "window.SPB_PATTERN_WEAKNESS = " + json.dumps(payload) + ";\n",
        encoding="utf-8",
    )

    print(f"[rollup] {len(rows)} patterns | total_rework={payload['n_total_rework']} | chroma_baked={payload['n_chroma_baked']}")
    print(f"[rollup] wrote {out}")
    if cat_summary:
        print("Top categories by mean rework score:")
        for c in cat_summary[:12]:
            print(f"  {c['mean_rework_score']:5.1f}  {c['total_rework']:2d}/{c['count']:2d} rework  {c['category']}")
    print("\nTop 15 pattern rework candidates:")
    for r in rows[:15]:
        print(f"  {r['rework_score']:5.1f}  {r['action']:18s}  {r['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
