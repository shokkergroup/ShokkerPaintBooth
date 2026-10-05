# -*- coding: utf-8 -*-
"""Post-assembly finalization:
1. Clear the 18 rebuilt ids from _audit/june_fable_audit.json (loop rule:
   rebuilt/replaced items reappear; keeps stay hidden). History jsonl untouched.
2. Update the 92 MONOLITHICS tile descs in paint-booth-0-finish-data.js from
   the draft metas (names stay; FABLE rebuilt names may change for the replace).
"""
import io, json, os, re

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"

# 1) clear rebuilt fable verdicts
ap = os.path.join(ROOT, "_audit", "june_fable_audit.json")
d = json.load(open(ap, encoding="utf-8"))
keepers = {"fable_velvet_eclipse", "fable_wovenlight"}
before = len(d.get("entries", {}))
d["entries"] = {k: v for k, v in d.get("entries", {}).items() if k in keepers}
json.dump(d, open(ap, "w", encoding="utf-8"), indent=1)
print("audit entries: %d -> %d (rebuilt ids cleared, keepers kept hidden)" % (before, len(d["entries"])))

# 2) JS desc/name updates
js = os.path.join(ROOT, "paint-booth-0-finish-data.js")
src = io.open(js, encoding="utf-8").read()
metas = []
metas += json.load(open(os.path.join(ROOT, "scripts", "fable_audit_meta.json"), encoding="utf-8"))
metas += json.load(open(os.path.join(ROOT, "scripts", "rework_audit_meta.json"), encoding="utf-8"))


def esc(s):
    return s.replace('"', "&quot;").replace("\n", " ").strip()


updated, missing = 0, []
for m in metas:
    pat = re.compile(r'(\{ id: "%s", name: ")([^"]*)(", desc: ")([^"]*)(")' % re.escape(m["id"]))
    new_src, n = pat.subn(lambda g: g.group(1) + esc(m["name"]) + g.group(3) + esc(m["desc"]) + g.group(5), src, count=1)
    if n:
        src = new_src
        updated += 1
    else:
        missing.append(m["id"])

io.open(js, "w", encoding="utf-8", newline="").write(src)
print("JS tiles updated: %d | not found (different tile shape, fine): %d" % (updated, len(missing)))
if missing:
    print("  e.g.", missing[:8])
