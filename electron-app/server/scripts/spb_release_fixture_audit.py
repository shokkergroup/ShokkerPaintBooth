#!/usr/bin/env python3
"""Fail closed when the release-gauntlet PSD fixture changes or loses structure."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from psd_tools import PSDImage


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ID = "spb-chevy-truck-2048-v1"
FIXTURE = ROOT / "assets/defaults/shokker_paint_booth_chevy_truck.psd"
EXPECTED_SHA256 = "06ba09a83edca88c0fa8a2f98c02a921949e405807ea8cbf7c74e6c89aa2f4b9"
REQUIRED_LEAVES = {
    "Car Paint", "Sponsors", "Numbers", "Tape", "Pitbox Colors",
    "Color Change Logos", "Car_decal", "Windshield Banner",
    "Car_Mandatory", "Mask", "Wire",
}


def walk(nodes, groups, leaves):
    for node in nodes:
        if node.is_group():
            groups.append(str(node.name))
            walk(node, groups, leaves)
        else:
            leaves.append(str(node.name))


def main() -> int:
    failures = []
    actual_hash = hashlib.sha256(FIXTURE.read_bytes()).hexdigest() if FIXTURE.is_file() else None
    if actual_hash != EXPECTED_SHA256:
        failures.append("fixture SHA-256 changed or the PSD is missing")
    groups, leaves, size = [], [], None
    try:
        psd = PSDImage.open(FIXTURE)
        size = list(psd.size)
        walk(psd, groups, leaves)
    except Exception as error:  # pragma: no cover - exercised as release failure
        failures.append(f"fixture could not be parsed: {error}")
    if size != [2048, 2048]:
        failures.append(f"fixture size is {size}, expected [2048, 2048]")
    missing = sorted(REQUIRED_LEAVES.difference(leaves))
    if missing or len(leaves) < 8 or len(groups) < 2:
        failures.append(f"fixture layer structure is incomplete; missing={missing}")
    result = {
        "schemaVersion": 1,
        "fixtureId": FIXTURE_ID,
        "path": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "sha256": actual_hash,
        "size": size,
        "groups": groups,
        "leaves": leaves,
        "ok": not failures,
        "failures": failures,
    }
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    elif failures:
        for failure in failures:
            print(f"FAIL  {failure}", file=sys.stderr)
    else:
        print(f"PASS  {FIXTURE_ID}: {size[0]}x{size[1]}, {len(leaves)} leaves, {len(groups)} groups")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
