# -*- coding: utf-8 -*-
"""Assemble the crush-rework drafts:
1. FABLE rebuilds (rw_fableA/B/C.json) -> APPEND-OVERRIDE into
   engine/paint_v2/fable_collection.py (later defs rebind the names; then
   FABLE_MONOLITHICS.update re-points the registry tuples). Keepers
   (velvet_eclipse FAB_9, wovenlight FAB_10) remain on their optimized blocks.
2. Category rework (rw_insects/anime/neon/chameleon/prizmA/prizmB.json) ->
   append blocks + REWORK_MONOLITHICS dict to
   engine/expansions/colorshift_rework_2026.py.
3. Writes scripts/rework_audit_meta.json (per-category) + updates
   scripts/fable_audit_meta.json names/descs for rebuilt ids.
Idempotent via markers."""
import ast, io, json, os, re, sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
H = os.path.join(ROOT, "docs", "handoff")

def load(name):
    p = os.path.join(H, name)
    if not os.path.exists(p):
        print("MISSING DRAFT:", p)
        return None
    return json.load(open(p, encoding="utf-8"))["finishes"]

problems = []
def validate(items, expect_prefix_fns):
    out = []
    for it in items:
        try:
            ast.parse(it["code"])
        except SyntaxError as e:
            problems.append("SYNTAX %s: %s" % (it["id"], e)); continue
        ok = True
        for fn in expect_prefix_fns(it["id"]):
            if ("def %s(" % fn) not in it["code"]:
                problems.append("MISSING %s in %s" % (fn, it["id"])); ok = False
        if ok:
            out.append(it)
    return out

# ---------- FABLE ----------
FABLE = os.path.join(ROOT, "engine", "paint_v2", "fable_collection.py")
MARKER_F = "=== FABLE CRUSH-REBUILD 2026-06-09 (round 2) START ==="
fab_items = []
for n in ("rw_fableA.json", "rw_fableB.json", "rw_fableC.json"):
    d = load(n)
    if d: fab_items += d
fab_items = validate(fab_items, lambda i: ("_spec_fable_%s" % i.replace("fable_", ""),
                                           "_paint_fable_%s" % i.replace("fable_", "")))
src = io.open(FABLE, encoding="utf-8").read()
if MARKER_F in src:
    print("FABLE already assembled")
elif not fab_items:
    problems.append("FABLE drafts: none valid")
else:
    print("FABLE: assembling %d/18 (salvage mode — missing ones keep their old code + stay hidden)" % len(fab_items))
    fabmap = {}
    for it in fab_items:
        m = re.search(r"^(FAB_(\d+))\s*=", it["code"], re.M)
        if not m:
            problems.append("NO FAB const in %s" % it["id"]); continue
        fabmap[it["id"]] = int(m.group(2))
    parts = ["", "", "# " + MARKER_F,
             "# Owner round-1 verdicts: 17 rebuild + 1 replace, all 'Too blobby / macro'.",
             "# Later defs REBIND the finish fns; the .update below re-points the registry.",
             "# Keepers velvet_eclipse / wovenlight stay on their original optimized blocks."]
    for it in fab_items:
        parts += ["", "", it["code"].rstrip()]
    parts += ["", "", "FABLE_MONOLITHICS.update({"]
    for it in fab_items:
        key = it["id"].replace("fable_", "")
        parts.append("    FAB_%d:  (_spec_fable_%s, _paint_fable_%s)," % (fabmap[it["id"]], key, key))
    parts += ["})", "# === FABLE CRUSH-REBUILD 2026-06-09 (round 2) END ===", ""]
    io.open(FABLE, "a", encoding="utf-8", newline="\n").write("\n".join(parts))
    print("FABLE: appended %d rebuilt blocks" % len(fab_items))
    # update fable meta names/descs
    mp = os.path.join(ROOT, "scripts", "fable_audit_meta.json")
    meta = json.load(open(mp, encoding="utf-8"))
    bynew = {it["id"]: it for it in fab_items}
    for m in meta:
        if m["id"] in bynew:
            m["name"] = bynew[m["id"]]["name"]
            m["desc"] = bynew[m["id"]]["desc"]
            m["technique"] = bynew[m["id"]].get("technique", m.get("technique", ""))
    json.dump(meta, open(mp, "w", encoding="utf-8"), indent=1)

# ---------- CATEGORY REWORK ----------
RW = os.path.join(ROOT, "engine", "expansions", "colorshift_rework_2026.py")
MARKER_R = "REWORK_MONOLITHICS = {"
CATS = {"rw_insects.json": "insects", "rw_anime.json": "anime", "rw_neon.json": "neonunderground",
        "rw_chameleon.json": "chameleon", "rw_prizmA.json": "prizm", "rw_prizmB.json": "prizm"}
EXPECT = {"insects": 10, "anime": 10, "neonunderground": 10, "chameleon": 15, "prizm": 29}
rw_items, cat_of = [], {}
for n, cat in CATS.items():
    d = load(n)
    if d:
        for it in d:
            cat_of[it["id"]] = cat
        rw_items += d
rw_items = validate(rw_items, lambda i: ("_spec_rw_%s" % i, "_paint_rw_%s" % i))
src = io.open(RW, encoding="utf-8").read()
if MARKER_R in src:
    print("REWORK already assembled")
else:
    counts = {}
    for it in rw_items:
        counts[cat_of[it["id"]]] = counts.get(cat_of[it["id"]], 0) + 1
    missing = {c: EXPECT[c] - counts.get(c, 0) for c in EXPECT if counts.get(c, 0) != EXPECT[c]}
    if missing:
        problems.append("REWORK counts off: %s (have %s)" % (missing, counts))
    else:
        parts = []
        for it in rw_items:
            parts += ["", "", it["code"].rstrip()]
        parts += ["", "", "# " + "-" * 75,
                  "# REGISTRY EXPORT - applied via shokker_engine_v2._spb_apply_colorshift_rework_2026",
                  "# " + "-" * 75, "REWORK_MONOLITHICS = {"]
        for it in rw_items:
            parts.append('    "%s": (_spec_rw_%s, _paint_rw_%s),' % (it["id"], it["id"], it["id"]))
        parts += ["}", ""]
        io.open(RW, "a", encoding="utf-8", newline="\n").write("\n".join(parts))
        print("REWORK: appended %d blocks (%s)" % (len(rw_items), counts))
        meta = [{"id": it["id"], "name": it["name"], "desc": it["desc"], "kind": "finish",
                 "technique": it.get("technique", ""), "category": cat_of[it["id"]]} for it in rw_items]
        json.dump(meta, open(os.path.join(ROOT, "scripts", "rework_audit_meta.json"), "w", encoding="utf-8"), indent=1)

if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems:
        print(" -", p)
print("ASSEMBLY DONE (assembled fable ids: %s)" % ",".join(it["id"] for it in fab_items))
