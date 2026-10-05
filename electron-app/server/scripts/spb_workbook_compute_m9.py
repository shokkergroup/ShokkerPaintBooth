#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M9: Owner Concordance.

The owner has explicitly said the existing metric stack (M1-M8 / M7 composite,
catalog scorecard, perf budget) is NOT an effective judge of actual finish
quality. M9 quantifies HOW WRONG those metrics are, by joining them against
real owner ground-truth ratings from SPB_RATE_10.json and the sparse picker
overrides in paint-booth-0-picker-owner-ratings.js.

For each owner-rated finish we compute:
  - owner_score  : rating × 10 on a 0-100 scale (or status→score for picker)
  - m7_composite : the existing best-effort score (or None if unscored)
  - disagreement : m7_composite − owner_score
                   (positive = metric over-rates a finish the owner disliked)
                   (negative = metric under-rates a finish the owner loved)
  - bucket       :
       "metric_over"  → disagreement ≥ +20 AND owner verdict REBUILD/MIXED/reject
       "metric_under" → disagreement ≤ −20 AND owner verdict KEEP/keeper
       "agree"        → |disagreement| < 15 OR no clear over/under failure
       "blind"        → owner rated but no M7 score at all

A category rollup highlights families where the metric is systematically wrong
in one direction — those are the families whose intent profile most needs to
be rewritten.

Output: _workbook_metrics/m9_owner_concordance.{json,js}
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)

RATE10 = PROJECT_ROOT / "SPB_RATE_10.json"
PICKER = PROJECT_ROOT / "paint-booth-0-picker-owner-ratings.js"
M7     = OUT_DIR / "m7_composite.json"
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"

# Candidate prefixes to try when mapping a bare pattern id → scorecard key.
PREFIXES = ("pattern:", "spec_pattern:", "monolithic:", "base:")

# Owner-verdict → severity sign for inferring whether the metric is "too high".
VERDICT_KEEP = {"KEEP", "keeper"}
VERDICT_FAIL = {"REBUILD", "reject", "rework", "rework_spec"}
VERDICT_MIXED = {"MIXED", "watch"}

STATUS_TO_SCORE = {
    "keeper": 85,
    "watch": 60,
    "rework_spec": 40,
    "rework": 35,
    "reject": 15,
}


def load_m7() -> tuple[dict, dict]:
    if not M7.exists():
        return {}, {}
    data = json.loads(M7.read_text(encoding="utf-8"))
    return data.get("byFinish", {}) or {}, data.get("tierThresholds", {}) or {}


def load_scorecard_category_map() -> dict[str, str]:
    """Build finish_id → category by parsing the scorecard JS."""
    if not SCORECARD.exists():
        return {}
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if not body_match:
        return {}
    # Cheap parser: find every `"<id>": { ... "category": "<cat>"` block.
    pat = re.compile(
        r'"(?P<id>[^"\n]+?)"\s*:\s*\{[^}]*?"category"\s*:\s*"(?P<cat>[^"]+)"',
        flags=re.S,
    )
    return {m.group("id"): m.group("cat") for m in pat.finditer(body_match.group(1))}


def resolve_finish_id(bare: str, m7: dict, scorecard: dict) -> str | None:
    """A pattern key in SPB_RATE_10 is bare ('spec_oil_film_thick'); the
    scorecard / M7 keys are prefixed ('spec_pattern:spec_oil_film_thick')."""
    if bare in m7 or bare in scorecard:
        return bare
    for p in PREFIXES:
        cand = p + bare
        if cand in m7 or cand in scorecard:
            return cand
    return None


def parse_picker_overrides() -> list[dict]:
    """Read paint-booth-0-picker-owner-ratings.js, return list of owner entries."""
    if not PICKER.exists():
        return []
    txt = PICKER.read_text(encoding="utf-8", errors="replace")
    # Each entry: "<key>": { status: "...", notes: "...", scores: { overall: N } }
    entry_re = re.compile(
        r'"(?P<key>[a-z_]+:[a-z0-9_]+)"\s*:\s*\{(?P<body>[^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
        flags=re.S,
    )
    status_re = re.compile(r'status\s*:\s*"([^"]+)"')
    overall_re = re.compile(r'overall\s*:\s*(\d+)')
    notes_re = re.compile(r'notes\s*:\s*"([^"]+)"')
    src_re = re.compile(r'source\s*:\s*"([^"]+)"')
    out = []
    for m in entry_re.finditer(txt):
        body = m.group("body")
        sm = status_re.search(body)
        om = overall_re.search(body)
        nm = notes_re.search(body)
        srcm = src_re.search(body)
        if not sm:
            continue
        status = sm.group(1)
        owner_score = int(om.group(1)) if om else STATUS_TO_SCORE.get(status, 50)
        out.append({
            "key": m.group("key"),
            "verdict": status,
            "owner_score": owner_score,
            "rating": None,
            "checkboxes": [],
            "notes": nm.group(1) if nm else "",
            "source": srcm.group(1) if srcm else "picker_owner_ratings",
            "round_label": "picker",
            "submitted_at": "",
        })
    return out


def parse_rate10() -> list[dict]:
    """Return latest-round owner rating per pattern from SPB_RATE_10.json.

    SPB_RATE_10 schema (loose):
      ratings: {
        "<pattern_id>": {
          "rating": N, "verdict": "...", "checkboxes": [...], "comment": "...",
          "submitted_at": "...",
          # OR
          "round5": { ...same... },
          "round3": { ...same... },
          "round1": { ...same... },
        }
      }
    Top-level fields (when present) are the LATEST round. Otherwise we pick the
    highest-numbered round_<N> sub-object.
    """
    if not RATE10.exists():
        return []
    data = json.loads(RATE10.read_text(encoding="utf-8"))
    ratings = data.get("ratings", {})
    out = []
    for pid, entry in ratings.items():
        # Prefer top-level fields (those are the live latest values).
        latest = None
        round_label = None
        if isinstance(entry, dict) and ("rating" in entry or "verdict" in entry):
            latest = entry
            round_label = "live"
        else:
            # Scan round_N sub-objects, pick highest N.
            rounds = []
            for k, v in entry.items():
                if isinstance(v, dict) and k.startswith("round"):
                    try:
                        n = int(k.replace("round", ""))
                        rounds.append((n, k, v))
                    except ValueError:
                        continue
            if rounds:
                rounds.sort(key=lambda t: t[0], reverse=True)
                _, round_label, latest = rounds[0]
        if not latest:
            continue
        rating = latest.get("rating")
        verdict = latest.get("verdict", "")
        if rating is None and not verdict:
            continue
        owner_score = (rating * 10) if isinstance(rating, (int, float)) else STATUS_TO_SCORE.get(verdict, 50)
        out.append({
            "key": pid,                   # bare (no prefix) — resolved later
            "verdict": verdict,
            "owner_score": float(owner_score),
            "rating": rating,
            "checkboxes": latest.get("checkboxes", []) or [],
            "notes": latest.get("comment", "") or "",
            "source": "SPB_RATE_10",
            "round_label": round_label,
            "submitted_at": latest.get("submitted_at", ""),
        })
    return out


def bucket_for(disagreement: float | None, verdict: str) -> str:
    if disagreement is None:
        return "blind"
    if disagreement >= 20 and verdict in (VERDICT_FAIL | VERDICT_MIXED):
        return "metric_over"
    if disagreement <= -20 and verdict in VERDICT_KEEP:
        return "metric_under"
    return "agree"


def main() -> int:
    m7_by_finish, _ = load_m7()
    scorecard_cat = load_scorecard_category_map()

    rate10 = parse_rate10()
    picker = parse_picker_overrides()
    all_entries = rate10 + picker

    per_finish = []
    for raw in all_entries:
        resolved = resolve_finish_id(raw["key"], m7_by_finish, scorecard_cat)
        category = scorecard_cat.get(resolved or "", "")
        m7_score = None
        m7_tier = None
        if resolved and resolved in m7_by_finish:
            m7_score = m7_by_finish[resolved].get("composite")
            m7_tier = m7_by_finish[resolved].get("tier")
        disagreement = (m7_score - raw["owner_score"]) if (m7_score is not None) else None
        b = bucket_for(disagreement, raw["verdict"])
        per_finish.append({
            "id": raw["key"],
            "resolvedId": resolved,
            "category": category,
            "verdict": raw["verdict"],
            "rating": raw["rating"],
            "ownerScore": round(raw["owner_score"], 1),
            "m7Composite": (round(m7_score, 1) if m7_score is not None else None),
            "m7Tier": m7_tier,
            "disagreement": (round(disagreement, 1) if disagreement is not None else None),
            "absDisagreement": (round(abs(disagreement), 1) if disagreement is not None else None),
            "bucket": b,
            "checkboxes": raw["checkboxes"],
            "notes": raw["notes"],
            "source": raw["source"],
            "round": raw["round_label"],
            "submittedAt": raw["submitted_at"],
        })

    # De-dupe: prefer SPB_RATE_10 entry over picker if both exist for the same resolved id.
    seen = {}
    for e in per_finish:
        key = e["resolvedId"] or e["id"]
        if key not in seen or (e["source"] == "SPB_RATE_10" and seen[key]["source"] != "SPB_RATE_10"):
            seen[key] = e
    per_finish = list(seen.values())

    # Sort by abs disagreement desc, then bucket priority.
    bucket_order = {"metric_over": 0, "metric_under": 1, "blind": 2, "agree": 3}
    per_finish.sort(key=lambda e: (
        bucket_order.get(e["bucket"], 9),
        -(e["absDisagreement"] or -1),
    ))

    # Category rollup.
    by_cat: dict[str, dict] = {}
    for e in per_finish:
        cat = e["category"] or "(uncategorized)"
        bucket = by_cat.setdefault(cat, {
            "count": 0,
            "agree": 0,
            "metric_over": 0,
            "metric_under": 0,
            "blind": 0,
            "ownerMean": 0.0,
            "m7Mean": 0.0,
            "m7Coverage": 0,
            "disagreementSum": 0.0,
            "absDisagreementSum": 0.0,
        })
        bucket["count"] += 1
        bucket[e["bucket"]] += 1
        bucket["ownerMean"] += e["ownerScore"]
        if e["m7Composite"] is not None:
            bucket["m7Mean"] += e["m7Composite"]
            bucket["m7Coverage"] += 1
            bucket["disagreementSum"] += e["disagreement"]
            bucket["absDisagreementSum"] += e["absDisagreement"]

    for cat, b in by_cat.items():
        n = max(b["count"], 1)
        b["ownerMean"] = round(b["ownerMean"] / n, 1)
        if b["m7Coverage"]:
            b["m7Mean"] = round(b["m7Mean"] / b["m7Coverage"], 1)
            b["meanDisagreement"] = round(b["disagreementSum"] / b["m7Coverage"], 1)
            b["meanAbsDisagreement"] = round(b["absDisagreementSum"] / b["m7Coverage"], 1)
        else:
            b["m7Mean"] = None
            b["meanDisagreement"] = None
            b["meanAbsDisagreement"] = None
        # Round running sums for readability.
        b["disagreementSum"] = round(b["disagreementSum"], 1)
        b["absDisagreementSum"] = round(b["absDisagreementSum"], 1)

    # Totals.
    total = len(per_finish)
    totals = {
        "totalRated": total,
        "metric_over": sum(1 for e in per_finish if e["bucket"] == "metric_over"),
        "metric_under": sum(1 for e in per_finish if e["bucket"] == "metric_under"),
        "agree": sum(1 for e in per_finish if e["bucket"] == "agree"),
        "blind": sum(1 for e in per_finish if e["bucket"] == "blind"),
        "withM7": sum(1 for e in per_finish if e["m7Composite"] is not None),
    }
    if totals["withM7"]:
        ds = [e["disagreement"] for e in per_finish if e["disagreement"] is not None]
        ads = [e["absDisagreement"] for e in per_finish if e["absDisagreement"] is not None]
        totals["meanDisagreement"] = round(sum(ds) / len(ds), 1)
        totals["meanAbsDisagreement"] = round(sum(ads) / len(ads), 1)
        # Pearson correlation (rough — guards against degenerate small-N).
        owner_vals = [e["ownerScore"] for e in per_finish if e["m7Composite"] is not None]
        m7_vals = [e["m7Composite"] for e in per_finish if e["m7Composite"] is not None]
        n = len(owner_vals)
        if n >= 3:
            mx = sum(owner_vals) / n
            my = sum(m7_vals) / n
            sxy = sum((x - mx) * (y - my) for x, y in zip(owner_vals, m7_vals))
            sxx = sum((x - mx) ** 2 for x in owner_vals) ** 0.5
            syy = sum((y - my) ** 2 for y in m7_vals) ** 0.5
            denom = sxx * syy
            totals["pearson"] = round(sxy / denom, 3) if denom else None
        else:
            totals["pearson"] = None
    else:
        totals["meanDisagreement"] = None
        totals["meanAbsDisagreement"] = None
        totals["pearson"] = None

    payload = {
        "version": 1,
        "metric": "M9 — Owner Concordance (ground-truth vs M7)",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "thresholds": {
            "agreeBand": 15,
            "majorBand": 20,
        },
        "totals": totals,
        "byFinish": per_finish,
        "byCategory": by_cat,
        "notes": (
            "Owner ground-truth ratings come from SPB_RATE_10.json (live R6 + "
            "earlier rounds) and paint-booth-0-picker-owner-ratings.js (sparse "
            "monolithic overrides). owner_score = rating × 10, or status → score "
            "map for picker entries. Disagreement = m7 − owner. A finish where "
            "owner verdict is REBUILD/MIXED but M7 ≥ owner+20 surfaces a metric "
            "FALSE-POSITIVE; a finish where owner KEEPs but M7 ≤ owner−20 "
            "surfaces a FALSE-NEGATIVE."
        ),
    }

    json_path = OUT_DIR / "m9_owner_concordance.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    js_path = OUT_DIR / "m9_owner_concordance.js"
    js_path.write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m9.py — do not hand-edit.\n"
        "window.SPB_M9 = " + json.dumps(payload) + ";\n",
        encoding="utf-8",
    )

    print(f"M9 — Owner Concordance generated for {total} owner-rated finishes")
    print(f"  metric_over:  {totals['metric_over']:3d}  (M7 over-rates a finish owner dislikes)")
    print(f"  metric_under: {totals['metric_under']:3d}  (M7 under-rates a finish owner loves)")
    print(f"  agree:        {totals['agree']:3d}")
    print(f"  blind:        {totals['blind']:3d}  (rated but no M7 score)")
    if totals["pearson"] is not None:
        print(f"  pearson(M7, owner): {totals['pearson']}")
        print(f"  meanAbsDisagreement: {totals['meanAbsDisagreement']}")
    print(f"  -> {json_path.relative_to(PROJECT_ROOT)}")
    print(f"  -> {js_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
