"""Real-file QA visual-diff regression (2026-06-26).

Compares a fresh _qa_diag.jsonl (produced by _specsculpt_qa_harness.py over C:/1Shokker Paint Car Examples)
against a saved baseline and flags any file whose spec STATS drifted materially — so a future engine edit
that changes real-car rendering is caught, with the file + channel named.

Usage:
    # 1. baseline the current good state:
    python _specsculpt_qa_harness.py scratch 0     # writes _qa_diag.jsonl
    python scripts/spec_sculpt_qa_diff.py --save-baseline
    # 2. after an engine change, re-render + diff:
    python _specsculpt_qa_harness.py scratch 0
    python scripts/spec_sculpt_qa_diff.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAG = os.path.join(ROOT, "_qa_diag.jsonl")
BASE = os.path.join(ROOT, "_qa_diag_baseline.json")
KEYS = ["M_mean", "R_mean", "Cc_mean", "M_std", "R_std", "Cc_std", "corr_MR", "corr_MCc", "corr_RCc"]
TOL = {"corr_MR": 0.12, "corr_MCc": 0.12, "corr_RCc": 0.12}   # corr drift tolerance; others use ABS_TOL
ABS_TOL = 14.0


def _rows(mode="scratch"):
    out = {}
    if not os.path.exists(DIAG):
        return out
    for line in open(DIAG, encoding="utf-8"):
        r = json.loads(line)
        if r.get("mode") == mode and "M_mean" in r:
            out[r["file"]] = {k: r.get(k) for k in KEYS}
    return out


def main():
    cur = _rows()
    if "--save-baseline" in sys.argv:
        json.dump(cur, open(BASE, "w"), indent=0)
        print(f"saved baseline: {len(cur)} files -> {os.path.basename(BASE)}")
        return
    if not os.path.exists(BASE):
        print("no baseline — run with --save-baseline first"); return
    base = json.load(open(BASE))
    drift = []
    for f, cv in cur.items():
        if f not in base:
            drift.append(f"{f}: NEW"); continue
        bad = []
        for k in KEYS:
            a, b = cv.get(k), base[f].get(k)
            if a is None or b is None:
                continue
            tol = TOL.get(k, ABS_TOL)
            if abs(a - b) > tol:
                bad.append(f"{k} {b:+.1f}->{a:+.1f}")
        if bad:
            drift.append(f"{f}: " + ", ".join(bad))
    if drift:
        print(f"DRIFT in {len(drift)}/{len(cur)} files:")
        for d in drift:
            print("  " + d)
        sys.exit(1)
    print(f"OK — all {len(cur)} files within tolerance of baseline.")


if __name__ == "__main__":
    main()
