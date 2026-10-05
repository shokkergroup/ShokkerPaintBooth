#!/usr/bin/env python3
"""Demo: AI/user PNG → Import DNA preview (marketing / QA).

Usage:
  python scripts/demo_user_import_dna.py path/to/art.png [--name "My Finish"] [--out preview.png]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.paint_v2.user_imports_ingest import preview_import


def main() -> int:
    ap = argparse.ArgumentParser(description="Import DNA demo preview")
    ap.add_argument("image", type=Path, help="PNG/JPEG paint plate")
    ap.add_argument("--name", default="", help="Display name")
    ap.add_argument("--out", type=Path, default=None, help="Save preview PNG path")
    ap.add_argument("--vibe", default="", help="Optional vibe ref finish id")
    args = ap.parse_args()
    if not args.image.is_file():
        print(f"Not found: {args.image}", file=sys.stderr)
        return 1
    payload = preview_import(
        [(args.image.name, args.image)],
        display_name=args.name or args.image.stem,
        vibe_ref=args.vibe or None,
    )
    print(json.dumps(payload.get("dna", {}), indent=2))
    print(f"suggested_intent: {payload.get('suggested_intent')}")
    if args.out and payload.get("preview", "").startswith("data:image/png;base64,"):
        import base64
        raw = base64.b64decode(payload["preview"].split(",", 1)[1])
        args.out.write_bytes(raw)
        print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
