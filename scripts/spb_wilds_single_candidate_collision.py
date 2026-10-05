# -*- coding: utf-8 -*-
"""Compare one isolated `_authored()` Wilds candidate to current survivors."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.fractured_wilds_accepted_2026 import ACCEPTED_IDS, _accepted_authored
from scripts.spb_wilds_accepted_collision_audit import (_corr, _paint_features,
                                                        _spec_features, _spec_similarity)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("module")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    module = importlib.import_module(args.module)
    paint, spec = module._authored()
    candidate = {"paint": _paint_features(paint), "spec": _spec_features(spec)}
    rows = []
    for fid in ACCEPTED_IDS:
        # A candidate can be temporarily runtime-wired while its replacement
        # evidence is refreshed. Comparing it to the same ID is a tautology,
        # not a collision, and previously made every such re-audit fail.
        if fid == module.ID:
            continue
        other_paint, other_spec = _accepted_authored(fid)
        other_p = _paint_features(other_paint)
        low = abs(_corr(candidate["paint"][0], other_p[0]))
        edge = abs(_corr(candidate["paint"][1], other_p[1]))
        paint_score = .55 * low + .45 * edge
        spec_score, perm, rank, spec_edge = _spec_similarity(candidate["spec"], _spec_features(other_spec))
        rows.append({"candidate": module.ID, "other": fid,
                     "paint_structure": round(paint_score, 6), "paint_low": round(low, 6),
                     "paint_edge": round(edge, 6), "spec_topology": round(spec_score, 6),
                     "spec_rank": round(rank, 6), "spec_edge": round(spec_edge, 6),
                     "spec_permutation": list(perm)})
    rows.sort(key=lambda row: max(row["paint_structure"], row["spec_topology"]), reverse=True)
    payload = {"candidate": module.ID, "survivor_count": len(ACCEPTED_IDS),
               "paint_threshold": .85, "spec_threshold": .85,
               "actionable": [r for r in rows if r["paint_structure"] >= .85 or r["spec_topology"] >= .85],
               "max_paint": max(rows, key=lambda r: r["paint_structure"]),
               "max_spec": max(rows, key=lambda r: r["spec_topology"]), "pairs": rows}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("candidate", "survivor_count", "actionable", "max_paint", "max_spec")}, indent=2))
    return 1 if payload["actionable"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
