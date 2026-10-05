#!/usr/bin/env python3
"""FOUNDATION ONE — flat BASES shelf distinctness gate (owner 2026-09-03).

The Foundation BASES shelf is a set of FLAT material cells: each finish is a constant
(M, Rough, Cc) triple with no paint of its own. Two cells that sit next to each other in
the material cube read as the same paint on the car, which is exactly the redundancy the
owner flagged ("Living Matte, Matte, and some others look VERY similar").

RULE (fitted to the owner's own verdicts, not invented):
    Two cells are DISTINCT when at least one holds:
        |dM|  >= 40             (metalness is a linear response)
        |log2(R1/R2)| >= 0.5     (roughness is perceived on a log scale: highlight width
                                  scales with roughness^2, so 15 vs 30 is a full octave while
                                  190 vs 200 is nothing)
        |dCc| >= 40             (coat lobe strength)
    Calibration:
        Living Matte 0/190/140 vs Matte 0/200/160 -> owner: "VERY similar"
            dM 0, 0.07 octave, dCc 20   -> FAILS all three  (correct: duplicate)
        Wet Look 0/15/16 vs Gloss 0/30/16 -> owner keeps both
            1.0 octave                  -> PASSES           (correct: distinct)
        Silk 0/85/60 vs Satin 0/95/70 -> 0.16 octave, dCc 10 -> FAILS (merged into Satin)

Reads the shelf from paint-booth-0-finish-data.js (BASE_GROUPS["Foundation"]) and the
cells from engine/base_registry_data.py with regexes — no engine boot, runs in <1s.

    python scripts/spb_foundation_ladder_gate.py            # gate the live shelf
    python scripts/spb_foundation_ladder_gate.py --all      # also list every pair's margin

Non-zero exit = a pair is not distinct = the shelf is not done.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "paint-booth-0-finish-data.js"
PY = ROOT / "engine" / "base_registry_data.py"

M_MIN = 40.0
R_OCTAVES_MIN = 0.5
CC_MIN = 40.0


def read_shelf() -> list[str]:
    src = JS.read_bytes().decode("utf-8", errors="surrogateescape")
    m = re.search(r'^\s*"Foundation":\s*\[([^\]]*)\]', src, re.M)
    if not m:
        raise SystemExit("BASE_GROUPS[\"Foundation\"] not found in finish-data")
    return re.findall(r'"([^"]+)"', m.group(1))


def read_cells(ids: list[str]) -> dict[str, tuple[int, int, int]]:
    src = PY.read_bytes().decode("utf-8", errors="surrogateescape")
    cells = {}
    for bid in ids:
        m = re.search(r'^\s*"%s":\s*\{[^\n]*?"M":\s*(\d+)[^\n]*?"R":\s*(\d+)[^\n]*?"CC":\s*(\d+)' % re.escape(bid), src, re.M)
        if not m:
            raise SystemExit(f"registry cell not found for {bid}")
        cells[bid] = tuple(int(x) for x in m.groups())
    return cells


def margins(a: tuple[int, int, int], b: tuple[int, int, int]) -> tuple[float, float, float]:
    dm = abs(a[0] - b[0])
    r1, r2 = max(a[1], 1), max(b[1], 1)
    octaves = abs(math.log2(r1 / r2))
    dcc = abs(a[2] - b[2])
    return dm, octaves, dcc


def distinct(a, b) -> bool:
    dm, octv, dcc = margins(a, b)
    return dm >= M_MIN or octv >= R_OCTAVES_MIN or dcc >= CC_MIN


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="print every pair with its margins")
    args = ap.parse_args()
    ids = read_shelf()
    cells = read_cells(ids)
    fails = []
    rows = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            dm, octv, dcc = margins(cells[a], cells[b])
            ok = distinct(cells[a], cells[b])
            rows.append((ok, a, b, dm, octv, dcc))
            if not ok:
                fails.append((a, b, dm, octv, dcc))
    print(f"FOUNDATION BASES shelf: {len(ids)} cells, {len(rows)} pairs, rule dM>={M_MIN:g} | dR>={R_OCTAVES_MIN:g} oct | dCc>={CC_MIN:g}")
    for bid in ids:
        m, r, cc = cells[bid]
        print(f"  {bid:18s} {m:3d}/{r:3d}/{cc:3d}")
    if args.all:
        for ok, a, b, dm, octv, dcc in sorted(rows, key=lambda t: (t[0], -max(t[3] / M_MIN, t[4] / R_OCTAVES_MIN, t[5] / CC_MIN))):
            print(f"  {'ok  ' if ok else 'FAIL'} {a:18s} {b:18s} dM={dm:3.0f} dR={octv:.2f}oct dCc={dcc:3.0f}")
    if fails:
        print(f"FAIL: {len(fails)} pair(s) not distinct:")
        for a, b, dm, octv, dcc in fails:
            print(f"  {a} ~ {b}  dM={dm:.0f} dR={octv:.2f}oct dCc={dcc:.0f}")
        return 1
    print("PASS: every pair on the BASES shelf is a distinct material cell")
    return 0


if __name__ == "__main__":
    sys.exit(main())
