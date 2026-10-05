#!/usr/bin/env python3
"""Read owner notes for any rate portal."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.rate_portals_config import PORTALS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--portal", required=True, choices=list(PORTALS))
    args = ap.parse_args()
    cfg = PORTALS[args.portal]
    path = ROOT / cfg["rate_json"]
    if not path.exists():
        print(f"No ratings yet — {path.name}")
        return 0
    data = json.loads(path.read_text(encoding="utf-8") or "{}")
    ratings = data.get("ratings") or {}
    buckets: dict[str, list] = {"REPLACE": [], "REBUILD": [], "MIXED": [], "KEEP": [], "UNRATED": []}
    for fid, entry in sorted(ratings.items()):
        v = (entry or {}).get("verdict") or "UNRATED"
        buckets.setdefault(v, []).append((fid, entry))
    print(f"=== {cfg['title']} ({path.name}) ===\n")
    for verdict in ("REPLACE", "REBUILD", "MIXED", "KEEP", "UNRATED"):
        items = buckets.get(verdict) or []
        if not items:
            continue
        print(f"--- {verdict} ({len(items)}) ---")
        for fid, entry in items:
            print(f"  {fid}  rating={entry.get('rating', '?')}")
            if entry.get("failures"):
                print(f"    failures: {', '.join(entry['failures'])}")
            if (entry.get("comment") or "").strip():
                print(f"    comment: {entry['comment'].strip()}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
