#!/usr/bin/env python3
"""List SPB pattern IDs vs on-disk assets (image_path) and engine registry.

Use this after moving/restoring pattern art under ``assets/patterns`` or
``basespatterns_examples/patternexamples``. Surfaces missing files and duplicate
IDs (procedural registry vs image scan).

Run from repo root:
  python scripts/pattern_inventory.py
  python scripts/pattern_inventory.py --category "Skate & Surf"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

FINISH_JS = REPO / "paint-booth-0-finish-data.js"


def _parse_pattern_groups(js_text: str) -> dict[str, list[str]]:
    m = re.search(r"const\s+PATTERN_GROUPS\s*=\s*\{", js_text)
    if not m:
        return {}
    depth = 0
    start = m.end() - 1
    i = start
    while i < len(js_text):
        if js_text[i] == "{":
            depth += 1
        elif js_text[i] == "}":
            depth -= 1
            if depth == 0:
                block = js_text[start + 1 : i]
                break
        i += 1
    else:
        return {}
    out: dict[str, list[str]] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith('"'):
            continue
        idx = line.index('":')
        name = line[1:idx]
        rest = line[idx + 2 :].strip()
        if not rest.startswith("["):
            continue
        inner = rest[1:]
        if inner.endswith("],"):
            inner = inner[:-2]
        elif inner.endswith("]"):
            inner = inner[:-1]
        ids = [x.strip().strip('"') for x in inner.split(",") if x.strip()]
        out[name] = ids
    return out


def _find_pattern_file(root: Path, pid: str) -> str | None:
    """Return relative path from repo root if any ``{pid}.png|jpg|jpeg`` exists under assets."""
    patterns_root = root / "assets" / "patterns"
    if not patterns_root.is_dir():
        return None
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        for p in patterns_root.rglob(f"{pid}{ext}"):
            try:
                return p.relative_to(root).as_posix()
            except ValueError:
                return str(p)
    ex = root / "basespatterns_examples" / "patternexamples"
    if ex.is_dir():
        for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
            for p in ex.rglob(f"{pid}{ext}"):
                try:
                    return p.relative_to(root).as_posix()
                except ValueError:
                    return str(p)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="SPB pattern asset inventory")
    ap.add_argument(
        "--category",
        help='Only list IDs in this PATTERN_GROUPS bucket (e.g. "Skate & Surf")',
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON lines for tooling")
    args = ap.parse_args()

    if not FINISH_JS.is_file():
        print(f"Missing {FINISH_JS}", file=sys.stderr)
        return 1
    js = FINISH_JS.read_text(encoding="utf-8", errors="replace")
    groups = _parse_pattern_groups(js)

    from engine.registry import PATTERN_REGISTRY as pattern_reg

    if not isinstance(pattern_reg, dict):
        print("Registry did not return pattern dict", file=sys.stderr)
        return 1

    if args.category:
        ids = groups.get(args.category)
        if not ids:
            print(f"Unknown category {args.category!r}. Known: {sorted(groups.keys())}", file=sys.stderr)
            return 1
        scan_ids = list(ids)
    else:
        scan_ids = sorted(set(pattern_reg.keys()))

    rows = []
    for pid in scan_ids:
        meta = pattern_reg.get(pid) or {}
        image_path = meta.get("image_path")
        has_tex = callable(meta.get("texture_fn"))
        disk = _find_pattern_file(REPO, pid)
        resolved = image_path or disk
        missing = bool(resolved) and not (REPO / str(resolved).replace("/", os.sep)).is_file()
        rows.append(
            {
                "id": pid,
                "registry": "yes" if pid in pattern_reg else "no",
                "image_path": image_path,
                "texture_fn": has_tex,
                "disk_guess": disk,
                "missing_file": missing,
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"Repo: {REPO}")
    if args.category:
        print(f"Category: {args.category} ({len(rows)} ids)\n")
    else:
        print(f"All pattern registry keys: {len(rows)}\n")

    for r in rows:
        ip = r["image_path"] or r["disk_guess"] or "(no path)"
        flag = " MISSING_FILE" if r["missing_file"] else ""
        proc = " procedural" if r["texture_fn"] else ""
        print(f"  {r['id']}: {ip}{flag}{proc}")

    n_miss = sum(1 for r in rows if r["missing_file"])
    if n_miss:
        print(f"\n{n_miss} patterns reference paths that are not on disk under this clone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
