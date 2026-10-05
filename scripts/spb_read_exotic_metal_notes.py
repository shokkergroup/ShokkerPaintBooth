#!/usr/bin/env python3
"""Summarize owner Exotic Metal ratings for agent handoff.

Run:
  python scripts/spb_read_exotic_metal_notes.py

Reads SPB_RATE_EXOTIC_METAL.json and prints KEEP / MIXED / REBUILD queues
with failure reasons and comments for agent rebuild work.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RATE_JSON = ROOT / "SPB_RATE_EXOTIC_METAL.json"


def main() -> int:
    if not RATE_JSON.exists():
        print(f"No ratings yet — {RATE_JSON.name} missing.")
        return 0

    data = json.loads(RATE_JSON.read_text(encoding="utf-8") or "{}")
    ratings = data.get("ratings", {}) if isinstance(data, dict) else {}

    buckets: dict[str, list[tuple[str, dict]]] = {
        "KEEP": [],
        "MIXED": [],
        "REBUILD": [],
        "UNRATED": [],
    }

    for base_id, entry in sorted(ratings.items()):
        if not isinstance(entry, dict):
            continue
        v = entry.get("verdict") or "UNRATED"
        if v not in buckets:
            v = "UNRATED"
        buckets[v].append((base_id, entry))

    print(f"=== Exotic Metal owner notes ({RATE_JSON.name}) ===\n")

    for verdict in ("REBUILD", "MIXED", "KEEP", "UNRATED"):
        items = buckets[verdict]
        if not items:
            continue
        print(f"--- {verdict} ({len(items)}) ---")
        for base_id, entry in items:
            rating = entry.get("rating", "?")
            comment = (entry.get("comment") or "").strip()
            fails = entry.get("failures") or []
            print(f"  {base_id}  rating={rating}")
            if fails:
                print(f"    failures: {', '.join(fails)}")
            if comment:
                print(f"    comment: {comment}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
