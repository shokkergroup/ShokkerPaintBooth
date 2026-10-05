# -*- coding: utf-8 -*-
"""Assemble the IGNITION-doctrine rebuild drafts (2026-06-10) from docs/handoff/ign/:
  fable_<short>.json -> engine/paint_v2/fable_collection.py (append-override + FABLE_MONOLITHICS.update)
  rw_<cat>_<n>.json  -> engine/expansions/colorshift_rework_2026.py (REWORK_MONOLITHICS rebind via _rw_pair)
  lfr_fin_<n>.json   -> engine/paint_v2/cultural_let_freedom_ring.py (LFR_MONOLITHICS.update)
  lfr_ovl_<n>.json   -> engine/spec_patterns.py (redef + PATTERN_CATALOG.update at EOF — must stay after the
                        second PATTERN_CATALOG literal ~L32517)
  lfr_pat_<n>.json   -> engine/expansion_patterns.py (redef/alias _tex_lfr_* / _paint_lfr_* — the lfr
                        dispatchers resolve globals at call time, so a later binding wins)
Also refreshes descs in scripts/{fable,rework,lfr}_audit_meta.json. Idempotent: re-running replaces this
run's own marker section in each target file.
"""
import ast, glob, io, json, os, py_compile, re, sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
IGN = os.path.join(ROOT, "docs", "handoff", "ign")
MARK_A = "# === IGNITION REBUILD 2026-06-10 START ==="
MARK_B = "# === IGNITION REBUILD 2026-06-10 END ==="

problems, touched, assembled = [], [], {}


def jload(p):
    return json.load(io.open(p, encoding="utf-8"))


def code_ok(item, req_fns):
    try:
        ast.parse(item["code"])
    except SyntaxError as e:
        problems.append("SYNTAX %s: %s" % (item["id"], e))
        return False
    miss = [f for f in req_fns if ("def %s(" % f) not in item["code"]]
    if miss:
        problems.append("MISSING %s in %s" % (",".join(miss), item["id"]))
        return False
    return True


def splice(path, block):
    src = io.open(path, encoding="utf-8").read()
    src = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B) + r"\n?", "", src, flags=re.S)
    out = src.rstrip("\n") + "\n\n\n" + MARK_A + "\n" + block.rstrip("\n") + "\n" + MARK_B + "\n"
    io.open(path, "w", encoding="utf-8", newline="\n").write(out)
    touched.append(path)


def collect(pattern, listkey=None):
    items = []
    for p in sorted(glob.glob(os.path.join(IGN, pattern))):
        d = jload(p)
        items += d[listkey] if listkey else [d]
    return items


# ---------- FABLE (8) ----------
fab = [it for it in collect("fable_*.json")
       if code_ok(it, ["_spec_fable_" + it["id"].replace("fable_", ""),
                       "_paint_fable_" + it["id"].replace("fable_", "")])]
if fab:
    blocks, upd = [], []
    for it in fab:
        s = it["id"].replace("fable_", "")
        blocks.append("# --- IGNITION: %s ---\n%s" % (it["id"], it["code"]))
        upd.append('    "%s": (_spec_fable_%s, _paint_fable_%s),' % (it["id"], s, s))
    splice(os.path.join(ROOT, "engine", "paint_v2", "fable_collection.py"),
           "\n\n".join(blocks) + "\n\nFABLE_MONOLITHICS.update({\n" + "\n".join(upd) + "\n})")
    assembled["fable"] = [it["id"] for it in fab]

# ---------- CATEGORY REWORK (74) ----------
rw = [it for it in collect("rw_*.json", "finishes")
      if code_ok(it, ["_ign_%s_paint" % it["id"], "_ign_%s_spec" % it["id"]])]
if rw:
    blocks = ["# --- IGNITION: %s ---\n%s" % (it["id"], it["code"]) for it in rw]
    upd = ['REWORK_MONOLITHICS["{i}"] = _rw_pair("{i}", _ign_{i}_paint, _ign_{i}_spec)'.format(i=it["id"])
           for it in rw]
    splice(os.path.join(ROOT, "engine", "expansions", "colorshift_rework_2026.py"),
           "\n\n".join(blocks) + "\n\n" + "\n".join(upd))
    assembled["rework"] = [it["id"] for it in rw]

# ---------- LFR FINISHES (10) ----------
lf = []
for it in collect("lfr_fin_*.json", "finishes"):
    try:
        tree = ast.parse(it["code"])
    except SyntaxError as e:
        problems.append("SYNTAX %s: %s" % (it["id"], e))
        continue
    defs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    spec = next((d for d in defs if d.endswith("_spec")), None)
    pnt = next((d for d in defs if d.endswith("_paint")), None)
    if not spec or not pnt:
        problems.append("LFR-FIN %s: no *_spec/*_paint def in %s" % (it["id"], defs))
        continue
    it["_spec"], it["_paint"] = spec, pnt
    lf.append(it)
if lf:
    blocks, upd = [], []
    for it in lf:
        blocks.append("# --- IGNITION: %s ---\n%s" % (it["id"], it["code"]))
        upd.append('    "%s": (%s, %s),' % (it["id"], it["_spec"], it["_paint"]))
    splice(os.path.join(ROOT, "engine", "paint_v2", "cultural_let_freedom_ring.py"),
           "\n\n".join(blocks) + "\n\nLFR_MONOLITHICS.update({\n" + "\n".join(upd) + "\n})")
    assembled["lfr_finishes"] = [it["id"] for it in lf]

# ---------- LFR SPEC OVERLAYS (10) ----------
ov = [it for it in collect("lfr_ovl_*.json", "overlays") if code_ok(it, [it["id"]])]
for it in ov:
    if "_spb_concept_complete" not in it["code"]:
        it["code"] += "\n%s._spb_concept_complete = True\n" % it["id"]
if ov:
    blocks = ["# --- IGNITION: %s ---\n%s" % (it["id"], it["code"]) for it in ov]
    upd = "PATTERN_CATALOG.update({\n" + "\n".join('    "%s": %s,' % (it["id"], it["id"]) for it in ov) + "\n})"
    splice(os.path.join(ROOT, "engine", "spec_patterns.py"), "\n\n".join(blocks) + "\n\n" + upd)
    assembled["lfr_overlays"] = [it["id"] for it in ov]

# ---------- LFR PATTERNS (10) ----------
pat_items = []
for it in collect("lfr_pat_*.json", "patterns"):
    try:
        tree = ast.parse(it["code"])
    except SyntaxError as e:
        problems.append("SYNTAX %s: %s" % (it["id"], e))
        continue
    defs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    s = it["id"].replace("lfr_", "")
    tex = next((d for d in defs if d == "_tex_lfr_" + s), None) or \
        next((d for d in defs if "tex" in d.lower()), None)
    pnt = next((d for d in defs if d == "_paint_lfr_" + s), None) or \
        next((d for d in defs if "paint" in d.lower()), None)
    if not tex or not pnt:
        problems.append("PATTERN %s: cannot identify tex/paint defs in %s" % (it["id"], defs))
        continue
    pat_items.append({"id": it["id"], "code": it["code"], "desc": it.get("desc", ""),
                      "_tex": tex, "_pnt": pnt})
if pat_items:
    # New textures use the DISPATCH signature (shape, mask, seed, sm) and return the
    # standard _pack dict, so route them via dispatcher overrides (call-time global
    # lookup at L1241/L1739 makes the rebind effective) instead of aliasing the old
    # 2-arg _tex_lfr_* names.
    routes_t = "\n".join('    "%s": %s,' % (it["id"], it["_tex"]) for it in pat_items)
    routes_p = "\n".join('    "%s": %s,' % (it["id"], it["_pnt"]) for it in pat_items)
    override = (
        "_IGN_TEX_ROUTES = {\n%s\n}\n_IGN_PAINT_ROUTES = {\n%s\n}\n\n"
        "def _texture_lfr_dispatch(shape, mask, seed, sm, variant, _old=_texture_lfr_dispatch):\n"
        "    fn = _IGN_TEX_ROUTES.get(variant)\n"
        "    if fn is not None:\n"
        "        return fn(shape, mask, seed, sm)\n"
        "    return _old(shape, mask, seed, sm, variant)\n\n"
        "def _paint_lfr_dispatch(paint, shape, mask, seed, pm, bb, variant, _old=_paint_lfr_dispatch):\n"
        "    fn = _IGN_PAINT_ROUTES.get(variant)\n"
        "    if fn is not None:\n"
        "        return fn(paint, shape, mask, seed, pm, bb)\n"
        "    return _old(paint, shape, mask, seed, pm, bb, variant)\n"
    ) % (routes_t, routes_p)
    splice(os.path.join(ROOT, "engine", "expansion_patterns.py"),
           "\n\n".join("# --- IGNITION: %s ---\n%s" % (it["id"], it["code"]) for it in pat_items)
           + "\n\n" + override)
    assembled["lfr_patterns"] = [it["id"] for it in pat_items]

# ---------- audit meta desc refresh ----------
def refresh_meta(name, items):
    p = os.path.join(ROOT, "scripts", name)
    if not (os.path.exists(p) and items):
        return
    try:
        meta = jload(p)
        if not isinstance(meta, list):
            return
    except Exception as e:
        problems.append("META %s: %s" % (name, e))
        return
    by_id = {it["id"]: it for it in items}
    for m in meta:
        u = by_id.get(m.get("id"))
        if u:
            if u.get("desc"):
                m["desc"] = u["desc"]
            if u.get("ignition"):
                m["ignition"] = u["ignition"]
    io.open(p, "w", encoding="utf-8").write(json.dumps(meta, indent=1))


refresh_meta("fable_audit_meta.json", fab)
refresh_meta("rework_audit_meta.json", rw)
refresh_meta("lfr_audit_meta.json", lf + ov + [{"id": i["id"], "desc": i["desc"]} for i in pat_items])

# ---------- compile gate ----------
for f in touched:
    try:
        py_compile.compile(f, doraise=True)
        print("COMPILE OK", os.path.relpath(f, ROOT))
    except Exception as e:
        problems.append("COMPILE FAIL %s: %s" % (f, e))

print(json.dumps({"assembled": {k: len(v) for k, v in assembled.items()},
                  "ids": assembled, "problems": problems}, indent=1))
sys.exit(1 if problems else 0)
