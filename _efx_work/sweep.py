#!/usr/bin/env python3
"""Per-row spec composition sweep (the DARK CITY method), measured with the law's axes.

For each id: try bands x micro x chips at --res, keep settings that pass FOLLOW/SCALE
with margin, choose the RICHEST (richness_eff) among them. Writes _efx_work/speckw.json
and embeds the table into the module between the SPECKW-BEGIN/END markers.

    python _efx_work/sweep.py --ids a,b            # or all rows when --ids is empty
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_efx_work"))
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import verify as V  # noqa: E402
X = V.X

GRID = [dict(bands=b, micro=m, chips=c) for b in ("quantile", "linear") for m in (None, "paint") for c in (0.34, 0.15)]
MARGIN = dict(fine=0.22, follow=0.38)


def best_for(fid, res):
    results = []
    for kw in GRID:
        X.SPECKW[fid] = {k: v for k, v in kw.items() if v is not None}
        try:
            row, _, _ = V.judge(fid, res)
        except Exception as ex:                                  # noqa: BLE001
            print(f"  {fid} {kw} ERROR {ex!r}"[:160])
            continue
        passing = row["fine"] >= MARGIN["fine"] and row["follow"] >= MARGIN["follow"] and row["dead"] <= 0.70
        results.append((passing, row["rich"], row["follow"], row["fine"], kw))
        print(f"  {fid:22s} {str(kw):58s} follow={row['follow']:.3f} fine={row['fine']:.3f} rich={row['rich']:.1f} {'pass' if passing else '----'}")
    X.SPECKW.pop(fid, None)
    if not results:
        return None, None
    passing = [r for r in results if r[0]]
    pool = passing if passing else results
    # richest among passing; if nothing passes, the best FOLLOW (so the next round has a base)
    pool.sort(key=(lambda r: (-r[1], -r[2])) if passing else (lambda r: (-r[2], -r[1])))
    return pool[0][4], bool(passing)


def embed(table):
    p = ROOT / "engine/paint_v2/foundation_efx_2026.py"
    raw = p.read_bytes().decode("utf-8")
    a = raw.index("# SPECKW-BEGIN\n") + len("# SPECKW-BEGIN\n")
    b = raw.index("# SPECKW-END")
    body = "SPECKW = {\n" + "".join("    %r: %r,\n" % (k, v) for k, v in sorted(table.items())) + "}\n"
    p.write_bytes((raw[:a] + body + raw[b:]).encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--res", type=int, default=768)
    a = ap.parse_args()
    ids = [s for s in a.ids.split(",") if s] or [r["fid"] for r in X.ROWS]
    jp = ROOT / "_efx_work" / "speckw.json"
    table = json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else {}
    table = {k: v for k, v in table.items() if k in X.BY_ID}
    for fid in ids:
        t0 = time.perf_counter()
        kw, ok = best_for(fid, a.res)
        if kw is None:
            continue
        table[fid] = {k: v for k, v in kw.items() if v is not None}
        print(f"CHOSEN {fid:24s} {table[fid]} {'PASS' if ok else 'still failing'} ({time.perf_counter() - t0:.0f}s)")
        jp.write_text(json.dumps(table, indent=1), encoding="utf-8")
    embed(table)
    print("EMBEDDED", len(table), "rows into SPECKW")


if __name__ == "__main__":
    main()
