"""Read the owner's Spec Sculpt audit verdicts and correlate them with finishes.

Joins ``_audit/spec_sculpt_audit.json`` against the current presets so you can see,
per preset: verdict / rating / mapped finish id / category / reasons / notes — plus
roll-ups (verdict counts, rating histogram, reason counts), the not-KEEP list, the
cultural-family finishes, and everything flagged 'big' (pattern too large).

Run:  python scripts/spb_spec_sculpt_audit_summary.py
"""
import sys, os, json
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from engine.spec_sculpt.presets import SPEC_SCULPT_PRESETS, PRESET_CATALOG_BY_ID

AUDIT = os.path.join(ROOT, "_audit", "spec_sculpt_audit.json")
with open(AUDIT, "r", encoding="utf-8") as f:
    data = json.load(f)
entries = data.get("entries", {})

meta = {}
for p in SPEC_SCULPT_PRESETS:
    pid = str(p["id"])
    fid = (PRESET_CATALOG_BY_ID.get(pid) or [("", 0)])[0][0]
    meta[pid] = {"label": p.get("label"), "cat": p.get("category"), "fid": fid}

rated = {pid: e for pid, e in entries.items() if e and e.get("verdict")}
print(f"audit updated: {data.get('updated')} | entries={len(entries)} rated={len(rated)}")
print("verdicts:", dict(Counter(e.get('verdict') for e in rated.values())))
ratings = [e.get("rating") for e in rated.values() if e.get("rating")]
if ratings:
    print(f"rating n={len(ratings)} avg={sum(ratings)/len(ratings):.1f} hist={dict(sorted(Counter(ratings).items()))}")
print("reasons:", dict(Counter(r for e in rated.values() for r in (e.get('reasons') or []))))

CULT = ("vm_", "rs_", "fd_", "uj_", "cc_", "gd_", "ms_")
print("\n=== NOT-KEEP ===")
for pid, e in sorted(rated.items(), key=lambda kv: kv[1].get('verdict')):
    if e.get("verdict") == "keep":
        continue
    m = meta.get(pid, {})
    nt = (e.get("notes") or "").replace("\n", " ")[:80]
    print(f"  [{e.get('verdict'):7}] r{e.get('rating') or '-':>2} {pid:30} fid={m.get('fid','?'):34} "
          f"{m.get('cat','')[:14]:14} reasons={','.join(e.get('reasons') or [])} {('| '+nt) if nt else ''}")

print("\n=== flagged 'big' (pattern too large) ===")
big = [(pid, meta.get(pid, {})) for pid, e in rated.items() if "big" in (e.get("reasons") or [])]
for pid, m in sorted(big, key=lambda kv: kv[1].get('cat', '')):
    print(f"  {pid:30} fid={m.get('fid','?'):34} {m.get('cat','')}")
print(f"  total big = {len(big)}")
