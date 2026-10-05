#!/usr/bin/env python3
"""Summarize owner Candy & Pearl ratings for agent handoff.

When the owner says "check notes", run:
  python scripts/spb_read_candy_pearl_notes.py

Reads SPB_RATE_CANDY_PEARL.json and prints KEEP / MIXED / REBUILD queues
with ratings, failure-reason checkboxes, and free-text comments.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RATE_JSON = ROOT / "SPB_RATE_CANDY_PEARL.json"

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    if not RATE_JSON.exists():
        print(f"No ratings file yet: {RATE_JSON}")
        return 1
    data = json.loads(RATE_JSON.read_text(encoding="utf-8"))
    ratings = data.get("ratings", {})

    keep, mixed, rebuild, unrated = [], [], [], []
    for base_id, ent in sorted(ratings.items()):
        if not isinstance(ent, dict):
            continue
        v = ent.get("verdict")
        r = ent.get("rating")
        row = {
            "id": base_id,
            "rating": r,
            "verdict": v,
            "checkboxes": ent.get("checkboxes") or [],
            "comment": (ent.get("comment") or "").strip(),
            "submitted_at": ent.get("submitted_at"),
        }
        if not v and not r:
            continue
        if v == "KEEP":
            keep.append(row)
        elif v == "MIXED":
            mixed.append(row)
        elif v == "REBUILD":
            rebuild.append(row)

    print(f"=== Candy & Pearl owner notes ({RATE_JSON.name}) ===\n")
    print(f"KEEP ({len(keep)}):")
    for x in keep:
        print(f"  {x['id']:24s} {x['rating']}/10  {x['submitted_at'] or ''}")
        if x["checkboxes"]:
            print(f"    reasons: {x['checkboxes']}")
        if x["comment"]:
            print(f"    comment: {x['comment']}")

    print(f"\nMIXED ({len(mixed)}) — needs targeted fixes:")
    for x in mixed:
        print(f"  {x['id']:24s} {x['rating']}/10")
        if x["checkboxes"]:
            print(f"    reasons: {x['checkboxes']}")
        if x["comment"]:
            print(f"    comment: {x['comment']}")

    print(f"\nREBUILD ({len(rebuild)}) — full rework:")
    for x in rebuild:
        print(f"  {x['id']:24s} {x['rating']}/10")
        if x["checkboxes"]:
            print(f"    reasons: {x['checkboxes']}")
        if x["comment"]:
            print(f"    comment: {x['comment']}")

    # Failure reason frequency
    freq: dict[str, int] = {}
    for ent in ratings.values():
        if not isinstance(ent, dict):
            continue
        for reason in ent.get("checkboxes") or []:
            freq[reason] = freq.get(reason, 0) + 1
    if freq:
        print("\nFailure reason frequency:")
        for reason, n in sorted(freq.items(), key=lambda kv: -kv[1]):
            print(f"  {n}x  {reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
