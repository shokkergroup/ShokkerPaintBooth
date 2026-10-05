#!/usr/bin/env python
"""Remove known root-level temp junk files.

This is intentionally narrow. It only deletes files in the repository root
that match the accidental artifact signature seen on 2026-04-24:

* file, not directory
* extensionless 8-character name made from [A-Za-z0-9_]
* exactly 4 bytes
* content exactly "blat"

Use:
    python scripts/cleanup-root-temp-junk.py --dry-run
    python scripts/cleanup-root-temp-junk.py --delete
"""

from __future__ import annotations

import argparse
from pathlib import Path


ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def is_root_temp_junk(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix:
        return False
    if len(path.name) != 8:
        return False
    if any(ch not in ALLOWED_CHARS for ch in path.name):
        return False
    if path.stat().st_size != 4:
        return False
    try:
        return path.read_text(encoding="utf-8") == "blat"
    except UnicodeDecodeError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="delete matching files")
    parser.add_argument("--dry-run", action="store_true", help="list matching files")
    args = parser.parse_args()

    if not args.delete and not args.dry_run:
        parser.error("choose --dry-run or --delete")

    root = Path(__file__).resolve().parent.parent
    victims = sorted((p for p in root.iterdir() if is_root_temp_junk(p)), key=lambda p: p.name)

    for path in victims:
        print(path.name)
        if args.delete:
            path.unlink()

    action = "deleted" if args.delete else "matched"
    print(f"{action}={len(victims)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
