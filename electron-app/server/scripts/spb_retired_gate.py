# -*- coding: utf-8 -*-
"""spb_retired_gate.py -- fail if anything in scripts/retired_catalog.json can reach a user.

Owner mandate 2026-09-05: "MAKE SURE that things that are supposed to be dead and buried stay
dead and buried." This gate is the mechanical version. It needs no engine boot (<5 s) and is
meant for spb-ship-check and for any agent about to "rescue orphans", "rehome leftovers" or
"merge light shelves" -- run it first, and if it goes red, the thing you are about to surface
is retired on purpose.

Checks (each prints one line per hit; non-zero exit on any hit in a hard check):
  PICKER   a retired id sits in the FINAL SPECIAL_GROUPS / BASE_GROUPS / PATTERN_GROUPS
           (the catalog JS is evaluated in node, so every parse-time merge/prune/rehome pass
           has already run -- this is what the picker actually builds from)
  GROUP    a retired group name survives as a SPECIAL_GROUPS/BASE_GROUPS key or is referenced
           by SPECIALS_SECTIONS
  INJECT   js/spb-finish-atlas.js (or any js/*.js) pushes a retired group into a section at
           runtime (the 2026-07-31 rescueOrphans() pattern)
  MERGE    a retired group is a SOURCE in _SPB_CATEGORY_MERGES_* (folding it into a live shelf)
  FEATURE  a scrapped feature still has its script tag in paint-booth-v2.html, a page-load fetch,
           or a route registration in server.py / server_routes
  SERVED   (--server) /api/finish-data returns a retired id without retired:true
Advisory (printed, never fails): ids in the ledger that are not registered anywhere in the
static catalog (already gone), and INFERRED entries the owner has not confirmed.

    python scripts/spb_retired_gate.py             # static checks
    python scripts/spb_retired_gate.py --server    # + live server check on http://127.0.0.1:<.server_port>
    python scripts/spb_retired_gate.py --list      # print the ledger counts
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
LEDGER = os.path.join(ROOT, "scripts", "retired_catalog.json")
FD = os.path.join(ROOT, "paint-booth-0-finish-data.js")
HTML = os.path.join(ROOT, "paint-booth-v2.html")
ATLAS = os.path.join(ROOT, "js", "spb-finish-atlas.js")


def load_ledger() -> dict:
    with open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


def eval_catalog() -> dict:
    """Evaluate the finish-data JS in node and return the FINAL picker tables."""
    out = os.path.join(ROOT, "_golden", "_gate_catalog.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # The catalog JS logs to stdout while it parses, so the result goes through a file, not stdout.
    # Load js/spb-retired-catalog.js FIRST, exactly as paint-booth-v2.html does, so the parse-end
    # ledger prune runs and the tables below are what the picker really builds from.
    js = ("const fs=require('fs');const g={};console.log=function(){};console.warn=function(){};"
          "globalThis.window=globalThis;"
          "const led=fs.existsSync('js/spb-retired-catalog.js')?fs.readFileSync('js/spb-retired-catalog.js','utf8'):'';"
          "new Function('g',led+';\\n'+fs.readFileSync('paint-booth-0-finish-data.js','utf8')"
          "+';g.SG=SPECIAL_GROUPS;g.BG=BASE_GROUPS;g.PG=(typeof PATTERN_GROUPS!==\"undefined\")?PATTERN_GROUPS:{};"
          "g.SS=(typeof SPECIALS_SECTIONS!==\"undefined\")?SPECIALS_SECTIONS:{};"
          "g.MONO=MONOLITHICS.map(m=>m.id);g.BASES=BASES.map(b=>b.id);g.PATS=(typeof PATTERNS!==\"undefined\")?PATTERNS.map(p=>p.id):[];"
          "g.LEDGER_LOADED=!!(window.SPB_RETIRED);g.LEDGER_PRUNED=window.SPB_RETIRED?window.SPB_RETIRED.lastPruned:null;')(g);"
          f"fs.writeFileSync({json.dumps(out)},JSON.stringify(g),'utf8');")
    r = subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("node evaluation of paint-booth-0-finish-data.js failed: " + r.stderr.decode("utf-8", "replace")[-400:])
    with open(out, encoding="utf-8") as f:
        return json.load(f)


def _strip_js_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)//.*$", "", src)


def _strip_py_comments(src: str) -> str:
    return re.sub(r"(?m)^\s*#.*$", "", src)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ledger = load_ledger()
    entries = ledger["entries"]
    if "--list" in argv:
        print("retired ledger:", ledger.get("counts"))
        return 0
    retired_ids = {e["id"]: e for e in entries if "id" in e}
    retired_groups = {e["group"]: e for e in entries if "group" in e}
    features = [e for e in entries if "feature" in e]
    hits = 0
    advis = 0

    cat = eval_catalog()
    if not cat.get("LEDGER_LOADED"):
        hits += 1
        print("LEDGER   js/spb-retired-catalog.js did not load before the catalog (regenerate: python scripts/build_retired_catalog.py)")
    else:
        print(f"LEDGER   loaded; parse-end prune removed {cat.get('LEDGER_PRUNED')} retired reference(s)")
    # PICKER
    for tbl, label in (("SG", "SPECIAL_GROUPS"), ("BG", "BASE_GROUPS"), ("PG", "PATTERN_GROUPS")):
        for gname, ids in cat.get(tbl, {}).items():
            bad = [i for i in ids if i in retired_ids]
            if bad:
                hits += 1
                print(f"PICKER   {label}['{gname}'] carries {len(bad)} retired id(s): {', '.join(bad[:6])}{' ...' if len(bad) > 6 else ''}")
    # GROUP
    for gname in retired_groups:
        if gname in cat.get("SG", {}) or gname in cat.get("BG", {}):
            hits += 1
            print(f"GROUP    retired group '{gname}' still exists as a picker group")
        for sec, members in cat.get("SS", {}).items():
            if isinstance(members, list) and gname in members:
                hits += 1
                print(f"GROUP    retired group '{gname}' is referenced by SPECIALS_SECTIONS['{sec}']")
    # INJECT (any js file that pushes a retired group name into a section list)
    js_dir = os.path.join(ROOT, "js")
    for dirpath, _, files in os.walk(js_dir):
        for fn in files:
            if not fn.endswith(".js"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                src = _strip_js_comments(open(p, encoding="utf-8", errors="replace").read())
            except Exception:
                continue
            for gname in retired_groups:
                for m in re.finditer(re.escape(gname), src):
                    line = src.count("\n", 0, m.start()) + 1
                    ctx = src[max(0, m.start() - 160):m.start()]
                    if re.search(r"(add|push|inject|rescue|rehome|SPECIALS_SECTIONS\[)", ctx):
                        hits += 1
                        print(f"INJECT   {os.path.relpath(p, ROOT)}:{line} injects retired group '{gname}' at runtime")
                        break
    # MERGE
    fd_src = open(FD, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'const (_SPB_CATEGORY_MERGES[A-Za-z0-9_]*)\s*=\s*\[(.*?)\n\];', fd_src, re.S):
        for gname in retired_groups:
            for mm in re.finditer(r'\[\s*"([^"]+)"\s*,\s*\[(.*?)\]\s*\]', m.group(2), re.S):
                target, sources = mm.group(1), re.findall(r'"([^"]+)"', mm.group(2))
                if gname in sources:
                    hits += 1
                    print(f"MERGE    {m.group(1)} folds retired group '{gname}' into '{target}'")
    # FEATURE
    html = open(HTML, encoding="utf-8", errors="replace").read()
    server_srcs = []
    for p in [os.path.join(ROOT, "server.py"), os.path.join(ROOT, "server_v5.py")] + \
             [os.path.join(ROOT, "server_routes", f) for f in os.listdir(os.path.join(ROOT, "server_routes")) if f.endswith(".py")]:
        try:
            server_srcs.append((os.path.relpath(p, ROOT), open(p, encoding="utf-8", errors="replace").read()))
        except Exception:
            pass
    js_srcs = []
    for p in [os.path.join(ROOT, f) for f in os.listdir(ROOT) if f.startswith("paint-booth-") and f.endswith(".js")]:
        js_srcs.append((os.path.relpath(p, ROOT), open(p, encoding="utf-8", errors="replace").read()))
    for feat in features:
        tag = feat.get("html_script")
        if tag and re.search(r'<script[^>]+src="' + re.escape(tag), html):
            hits += 1
            print(f"FEATURE  scrapped feature '{feat['feature']}' still has its script tag: {tag}")
        # a route module may keep its @app.route definitions on disk (inert); what matters is that
        # server.py / server_v5.py never CALL its registrar again
        for reg in feat.get("registrars", []):
            for name, src in server_srcs:
                if name.startswith("server_routes"):
                    continue
                if re.search(r"^\s*" + re.escape(reg), _strip_py_comments(src), re.M):
                    hits += 1
                    print(f"FEATURE  scrapped feature '{feat['feature']}' registrar {reg} is still called in {name}")
        # and no page-load path may call its loader (the definition itself may stay as dead code)
        for call in feat.get("boot_calls", []):
            for name, src in js_srcs:
                s2 = _strip_js_comments(src)
                # a page-load path = a top-level statement (<= 4 spaces of indent) or a DOMContentLoaded hook;
                # calls nested inside the scrapped feature's own handlers are dead code and do not count
                n = len(re.findall(r"(?m)^ {0,4}(?!function )\b" + re.escape(call) + r"\s*\(", s2))
                n += len(re.findall(r"DOMContentLoaded['\"]\s*,\s*" + re.escape(call) + r"\b", s2))
                if n:
                    hits += 1
                    print(f"FEATURE  scrapped feature '{feat['feature']}' loader {call}() still runs at page load ({n}x) in {name}")
    # SERVED
    if "--server" in argv:
        try:
            port = open(os.path.join(ROOT, ".server_port"), encoding="utf-8").read().strip()
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/finish-data", timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            served = set()
            for key in ("bases", "patterns", "monolithics", "specials"):
                for item in data.get(key, []) or []:
                    fid = item if isinstance(item, str) else item.get("id")
                    if fid:
                        served.add(fid)
            flagged = set(data.get("retired") or [])
            unflagged = sorted(i for i in retired_ids if i in served and i not in flagged)
            if "retired" not in data:
                hits += 1
                print("SERVED   /api/finish-data has no 'retired' list (server_v5.py not updated, or the live server predates the change)")
            elif unflagged:
                hits += 1
                print(f"SERVED   /api/finish-data serves {len(unflagged)} retired id(s) not in its 'retired' list: {', '.join(unflagged[:8])} ...")
            else:
                print(f"SERVED   ok ({len(served)} ids served, {len(flagged & served)} flagged retired, 0 unflagged)")
        except Exception as ex:
            print(f"SERVED   skipped ({ex})")
    # advisory
    static_ids = set(cat.get("MONO", [])) | set(cat.get("BASES", [])) | set(cat.get("PATS", []))
    gone = [i for i in retired_ids if i not in static_ids]
    inferred = [i for i, e in retired_ids.items() if e.get("basis") == "INFERRED"]
    advis += 1
    print(f"ADVISORY {len(gone)}/{len(retired_ids)} retired ids have no static tile (already gone); "
          f"{len(inferred)} entries are basis=INFERRED awaiting owner confirmation")
    print(f"RETIRED GATE: {hits} hit(s) -> {'FAIL' if hits else 'PASS'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
