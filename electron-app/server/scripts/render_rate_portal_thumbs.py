#!/usr/bin/env python3
"""Render thumbs for a rate portal."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.rate_portals_config import PORTALS
from scripts.spb_rate_portal_lib import render_thumbs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("portal", choices=list(PORTALS))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--all-catalog", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args()
    cfg = dict(PORTALS[args.portal])
    cfg["slug"] = args.portal
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    return render_thumbs(cfg, force=args.force, only=only, all_catalog=args.all_catalog, size=args.size, max_items=args.max)


if __name__ == "__main__":
    raise SystemExit(main())
