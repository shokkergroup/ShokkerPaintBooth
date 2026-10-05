"""Final extension: queue EVERY remaining un-rated, non-KEEP spec pattern.

Owner explicitly said 'REBUILD all SPEC BASES that need them - until they can
at least get to 75%. We STRIVE for 90+%'. Tonight is overnight loop time.

This script:
1. Reads the targeted tracker (currently 111 queued + 0 rebuilt)
2. Reads SPB_RATE_10.json for protected KEEPs (rating >=7 OR verdict==KEEP)
3. Pulls the full PATTERN_CATALOG name list
4. Adds every catalog name NOT in protected and NOT in tracker -> queue
5. Saves the extended tracker

Each new pattern gets a GENERIC_QUALITY brief: enforce doctrine + push the
specific identity hard enough to clear an owner-eye 75% bar.
"""
import json, time, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 1) Load tracker
TRACKER_PATH = ROOT / "_loop_state" / "targeted_round5_tracker.json"
t = json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
existing = set(t["pending"]) | set(t["rebuilt"])

# 2) Identify owner-protected patterns (rating >=7 OR verdict==KEEP)
PROTECTED = set()
ratings = json.loads((ROOT / "SPB_RATE_10.json").read_text(encoding="utf-8")).get("ratings", {})
for name, e in ratings.items():
    # check top-level (round 5) first
    top_keep = e.get("verdict") == "KEEP" or (e.get("rating") or 0) >= 7
    r3 = e.get("round3", {})
    r3_keep = r3.get("verdict") == "KEEP" or (r3.get("rating") or 0) >= 7
    r1 = e.get("round1", {})
    r1_keep = r1.get("verdict") == "KEEP" or (r1.get("rating") or 0) >= 7
    if top_keep or r3_keep or r1_keep:
        PROTECTED.add(name)

# 3) Get all PATTERN_CATALOG names (without loading the whole engine)
import re
src = (ROOT / "engine" / "spec_patterns.py").read_text(encoding="utf-8", errors="replace")
m = re.search(r"PATTERN_CATALOG\s*=\s*\{(.*?)^\}", src, re.MULTILINE | re.DOTALL)
ALL = set()
if m:
    for nm in re.findall(r"['\"]([a-zA-Z_][a-zA-Z0-9_]*)['\"]\s*:", m.group(1)):
        ALL.add(nm)

# 4) Compute new candidates
new_candidates = sorted(ALL - existing - PROTECTED)

# 5) Bake briefs
new_briefs = {}
for n in new_candidates:
    new_briefs[n] = {
        "kind": "NEIGHBOR",
        "theme": "QUALITY_FLOOR",
        "brief": (
            "OWNER WANTS THIS AT 75% MINIMUM, STRIVING FOR 90%. The function already has "
            "an 'identity:' docstring from a prior tick (structural doctrine pass), but "
            "owner feedback has shown structural compliance alone doesnt guarantee an "
            "owner-eye pass. Recurring complaints to actively check against: (1) too sparse / "
            "looks like confetti -> increase density 5x, no blank substrate; "
            "(2) features too large -> 8-32 px only, no macro/panel-scale; "
            "(3) preview better than render -> match the identity description exactly, no shortcuts; "
            "(4) too similar to siblings -> lean into THIS names specific differentiator; "
            "(5) no depth -> stronger M-channel contrast, multi-tier feature stacking; "
            "(6) wrong execution of right idea -> read the name literally and deliver THAT specific look. "
            "Per-feature INDEPENDENT M/R/CC continuous uniforms mandatory. 3+ stacked feature types. "
            "Full canvas coverage. Render time <200 ms at 256². NO 8-tier palette."
        ),
    }

# 6) Save
t["pending"].extend(sorted(new_briefs.keys()))
t["total"] = len(t["pending"]) + len(t["rebuilt"])
t["briefs"].update(new_briefs)
t["_full_sweep_extended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
TRACKER_PATH.write_text(json.dumps(t, indent=2), encoding="utf-8")

print(f"Catalog total: {len(ALL)}")
print(f"Owner-protected (KEEP/high): {len(PROTECTED)}")
print(f"  Protected names: {sorted(PROTECTED)}")
print(f"Already in tracker: {len(existing)}")
print(f"Added this run: {len(new_candidates)}")
print(f"")
print(f"Tracker now: {len(t['pending'])} pending, {len(t['rebuilt'])} rebuilt, {t['total']} total")
overnight_min = len(t['pending']) // 12 * 10
print(f"At 12/tick every 10 min: ~{overnight_min} min ({overnight_min // 60}h{overnight_min % 60}m) of overnight work")
