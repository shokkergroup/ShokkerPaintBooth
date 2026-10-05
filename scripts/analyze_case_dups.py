# -*- coding: utf-8 -*-
"""Determine, for each PATTERN case-collision pair, which case is the LIVE tile (referenced
by finish-data) vs the DUP, and whether the dup is scanner-minted (skippable in registry.py)
or curated. Outputs the precise dup-case SKIP-SET for the registry guard — never guessing.

Run: python -B scripts/analyze_case_dups.py
"""
import os, sys, json
from collections import defaultdict

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.environ.setdefault("SHOKKER_SKIP_SPEC_PREBAKE", "1")
os.environ.setdefault("SHOKKER_NO_CLEAN", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, ROOT)

import server
preg = server.engine.PATTERN_REGISTRY
fd = open(os.path.join(ROOT, "paint-booth-0-finish-data.js"), encoding="utf-8", errors="replace").read()


def in_fd(pid):
    return ('"' + pid + '"') in fd


def is_scanner(pid):
    e = preg.get(pid)
    if not isinstance(e, dict):
        return False
    return "patternexamples" in str(e.get("image_path", ""))


low = defaultdict(list)
for k in preg:
    low[k.lower()].append(k)

skip_set, keep_both, curated_dups, registry_only = [], [], [], []
for lk, variants in low.items():
    vs = sorted(set(variants))
    if len(vs) < 2:
        continue
    live = [v for v in vs if in_fd(v)]
    dup = [v for v in vs if not in_fd(v)]
    if len(live) >= 2:
        keep_both.append(vs)            # distinct finishes both referenced (art_deco case)
    elif len(live) == 1:
        for d in dup:
            (skip_set if is_scanner(d) else curated_dups).append((d, live[0]))
    else:
        registry_only.append(vs)        # neither in finish-data — registry-only collision

print("=== CASE-COLLISION ANALYSIS (%d pattern ids) ===" % len(preg))
print("\nKEEP BOTH (distinct, both in finish-data) — %d:" % len(keep_both))
for vs in keep_both:
    print("   ", vs)
print("\nSKIP in scanner (scanner-minted dup; live twin kept) — %d:" % len(skip_set))
for d, liv in skip_set:
    print("    skip %-24s (live: %s)" % (d, liv))
print("\nCURATED dups (NOT scanner-minted; need finish-data/registry-data removal, not a scanner guard) — %d:" % len(curated_dups))
for d, liv in curated_dups:
    e = preg.get(d) or {}
    print("    %-24s (live: %s)  entry-keys=%s" % (d, liv, list(e.keys()) if isinstance(e, dict) else type(e).__name__))
print("\nREGISTRY-ONLY collisions (neither in finish-data) — %d:" % len(registry_only))
for vs in registry_only:
    print("   ", vs)

out = {"skip_set": [d for d, _ in skip_set], "keep_both": keep_both,
       "curated_dups": [[d, l] for d, l in curated_dups], "registry_only": registry_only}
open(os.path.join(ROOT, "_overnight_audit", "case_dup_plan.json"), "w", encoding="utf-8").write(json.dumps(out, indent=1))
print("\nwrote _overnight_audit/case_dup_plan.json")
