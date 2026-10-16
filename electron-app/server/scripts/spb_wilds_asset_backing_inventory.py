#!/usr/bin/env python3
"""Inventory asset-backed accepted Wilds sources for full-canvas review.

Asset backing is not itself a failure.  The report deliberately combines it
with the 2048 runtime diagnostics only to prioritize human visual review of
possible photographic grain/border candidates; it never labels a finish bad
from a scalar measurement or authorizes a noise/blur "repair".
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPANSIONS = ROOT / "engine" / "expansions"
ADAPTER = EXPANSIONS / "fractured_wilds_accepted_2026.py"
AUDIT = ROOT / "_wilds_fullres_progress_20260824" / "accepted_runtime_rollout" / "full_canvas_runtime_audit.json"
OUT = ROOT / "_wilds_fullres_progress_20260824" / "accepted_runtime_rollout" / "asset_backing_inventory.json"


def _mapping() -> dict[str, str]:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if not (isinstance(test.left, ast.Name) and test.left.id == "fid" and test.comparators):
            continue
        candidate = test.comparators[0]
        if not isinstance(candidate, ast.Constant) or not isinstance(candidate.value, str):
            continue
        for child in node.body:
            if isinstance(child, ast.ImportFrom) and child.level == 1 and child.names:
                result[candidate.value] = child.names[0].name
    return result


def main() -> int:
    diagnostics = {}
    if AUDIT.exists():
        payload = json.loads(AUDIT.read_text(encoding="utf-8"))
        diagnostics = {row["id"]: row["diagnostics"] for row in payload.get("rows", [])}
    rows = []
    for finish_id, module in sorted(_mapping().items()):
        path = EXPANSIONS / f"{module}.py"
        source = path.read_text(encoding="utf-8")
        if not all(token in source for token in ("assets", "generated", "wilds")):
            continue
        assets = sorted(set(re.findall(r"[A-Za-z0-9_./-]+\\.png", source)))
        diag = diagnostics.get(finish_id, {})
        fine = float(diag.get("fine_energy", 0.0))
        border = float(diag.get("border_to_interior_std_ratio", 0.0))
        priority = "screen-first" if fine >= .04 else "screen"
        if border >= 1.04:
            priority += "+border-check"
        rows.append({
            "id": finish_id,
            "module": f"engine/expansions/{module}.py",
            "asset_literals": assets,
            "priority": priority,
            "runtime_2048_diagnostics": diag,
        })
    report = {
        "schema": "spb-wilds-asset-backing-inventory/1",
        "purpose": "human native-canvas review queue, never an automated rejection list",
        "accepted_asset_backed_count": len(rows),
        "rows": sorted(rows, key=lambda row: (
            row["priority"].split("+")[0] != "screen-first",
            -float(row["runtime_2048_diagnostics"].get("fine_energy", 0.0)),
            row["id"],
        )),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"asset-backed accepted Wilds: {len(rows)}; report: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
