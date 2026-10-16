# -*- coding: utf-8 -*-
"""build_retired_catalog.py -- regenerate scripts/retired_catalog.json from the source records.

Owner mandate 2026-09-05: "MAKE SURE that things that are supposed to be dead and buried stay
dead and buried." Retirement in this repo was scattered across JS comments, a scrub script, a
docs page and group-deletion loops, so agents kept "rescuing" retired finishes (Atlas
rescueOrphans 07-31, category merges 08-23, the leftover-bucket rehome 08-09). This file makes
retirement ONE machine-readable ledger that scripts/spb_retired_gate.py enforces.

Policy (docs/RETIRED_SHELVES_2026-09-05.md, owner call): retire = HIDE from every picker surface
and from /api/finish-data visibility; the engine keeps the renderer so saved cars still paint.
Every entry records where the decision is written down. Nothing here is invented: each list is
parsed from its record at build time, so re-running this script after a record changes keeps
the ledger honest. Hand-edit the ledger only through this script's SOURCES table.

    python scripts/build_retired_catalog.py            # rewrite scripts/retired_catalog.json
    python scripts/build_retired_catalog.py --print    # summary only
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
LEDGER = os.path.join(ROOT, "scripts", "retired_catalog.json")
FD = os.path.join(ROOT, "paint-booth-0-finish-data.js")
JS = open(FD, encoding="utf-8", errors="replace").read()


def _group_ids(name: str) -> list[str]:
    """Ids of a `"<name>": [ ... ]` array in the finish-data file (first definition)."""
    m = re.search(r'"' + re.escape(name) + r'"\s*:\s*\[(.*?)\]', JS, re.S)
    return re.findall(r'"([A-Za-z0-9_]+)"', m.group(1)) if m else []


def _retired_group_names() -> list[str]:
    m = re.search(r'for \(const _retired of \[(.*?)\]\)', JS, re.S)
    if not m:
        return []
    names = re.findall(r'"((?:\\u[0-9a-fA-F]{4}|[^"\\])*)"', m.group(1))
    return [json.loads('"' + n + '"') for n in names]


def _scrub_orphans() -> list[str]:
    src = open(os.path.join(ROOT, "scripts", "scrub_orphan_finishes.py"), encoding="utf-8", errors="replace").read()
    m = re.search(r'ORPHANS\s*=\s*\[(.*?)\]', src, re.S)
    return re.findall(r'"([a-z0-9_]+)"', m.group(1)) if m else []


def _old_decades() -> list[str]:
    src = open(os.path.join(ROOT, "engine", "pattern_expansion.py"), encoding="utf-8", errors="replace").read()
    head = src[:src.find("def ")] if "def " in src else src
    return sorted(set(re.findall(r'"(decade_[a-z0-9_]+)"', head)))


def _live_decade_shelf_ids() -> set[str]:
    ids: set[str] = set()
    for label in ("Decades 50s-80s", "90s, Skate & Surf"):
        m = re.search(r'"[^"\n]*' + re.escape(label) + r'"\s*:\s*\[(.*?)\]', JS, re.S)
        if m:
            ids.update(re.findall(r'"([A-Za-z0-9_]+)"', m.group(1)))
    return ids


def _retired_shelves() -> tuple[dict, list[str]]:
    doc = open(os.path.join(ROOT, "docs", "RETIRED_SHELVES_2026-09-05.md"), encoding="utf-8", errors="replace").read()
    full = doc[doc.find("## The full 104"):]
    shelves: dict = {}
    for m in re.finditer(r'### (.+?) \((\d+)\)\s*\n\s*\n(.*?)(?=\n### |\Z)', full, re.S):
        shelves[m.group(1).strip()] = re.findall(r'`([a-z0-9_]+)`', m.group(3))
    return shelves, sorted({i for v in shelves.values() for i in v})


def _groups_json() -> dict:
    p = os.path.join(ROOT, "_golden", "_groups.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {"SG": {}, "BG": {}, "PG": {}}


def build() -> dict:
    entries: list[dict] = []

    def add(kind, key, since, record, verdict, **extra):
        e = {"kind": kind, "policy": "hide", "since": since, "record": record, "owner_verdict": verdict}
        e["id" if kind in ("monolithic", "base", "pattern") else ("group" if kind.endswith("_group") else "feature")] = key
        e.update(extra)
        entries.append(e)

    # 1. Aurora & Chromatic Flow + Chromatic Flake -- owner 2026-06-03 (B5) + owner 2026-09-05 "hide both"
    aurora = _group_ids("Aurora & Chromatic Flow")
    cf = _group_ids("Chromatic Flake")
    for gname, ids in (("Aurora & Chromatic Flow", aurora), ("Chromatic Flake", cf)):
        add("special_group", gname, "2026-06-03",
            "paint-booth-0-finish-data.js:2171 (B5 pulled from SPECIALS_SECTIONS); wiki archive 2026-06-03",
            "Owner 2026-09-05: 'hide both'. Resurrected by js/spb-finish-atlas.js rescueOrphans() (07-31) and "
            "_SPB_CATEGORY_MERGES_2026_08_23 (Aurora -> Prizm); both must go.")
        for i in ids:
            add("monolithic", i, "2026-06-03", f"SPECIAL_GROUPS['{gname}']", "Owner 2026-09-05: hide", family=gname)

    # 2. Atelier -- Ultra Detail (unwired, pulled with B5)
    atelier = _group_ids("Atelier — Ultra Detail") or _group_ids("Atelier — Ultra Detail")
    add("special_group", "Atelier — Ultra Detail", "2026-06-03",
        "paint-booth-0-finish-data.js:2010; B5 2026-06-03; boot prints '[Atelier] Module not found'",
        "Renderers never wired; Atlas rescueOrphans() re-adds the group to SHOKKER -- must go.")
    for i in atelier:
        add("monolithic", i, "2026-06-03", "SPECIAL_GROUPS['Atelier — Ultra Detail']", "hide (unwired)", family="Atelier")

    # 3. 2026-06-03 owner-directed orphan scrub (55 monolithics) + dynamic mc_* (25)
    #    The scrub's SAFETY NET deliberately kept three ids whose "id" appeared more than once
    #    (aurora, rust, carbon_3k_weave -- wiki log 2026-06-03). They are NOT retired.
    SCRUB_PROTECTED = {"aurora", "rust", "carbon_3k_weave", "worn_chrome", "weathered_paint", "acid_rain_drip"}
    static_tiles = set(re.findall(r'\{\s*id:\s*"([A-Za-z0-9_]+)"', JS)) | set(re.findall(r'\{"id":"([A-Za-z0-9_]+)"', JS))
    for i in _scrub_orphans():
        if i in SCRUB_PROTECTED or i in static_tiles:
            continue  # kept by the scrub's safety net (still has a tile) -> live, not retired
        add("monolithic", i, "2026-06-03", "scripts/scrub_orphan_finishes.py ORPHANS (owner-directed scrub)",
            "Scrubbed tiles; re-homed as dangling refs by _SPECIALS_UNGROUPED_2026_08 (08-09) -- keep hidden.",
            family="orphan-scrub-2026-06-03")
    mc = _group_ids("Multi-Color Sets")
    add("special_group", "Multi-Color Sets", "2026-06-03",
        "paint-booth-0-finish-data.js:6113 (MC_DEFS emptied 2026-06-03); _SPECIALS_UNGROUPED_2026_08 re-created the group name",
        "25 dynamic mc_* tiles scrubbed 2026-06-03; group name must not come back.")
    for i in mc:
        add("monolithic", i, "2026-06-03", "MC_DEFS emptied (paint-booth-0-finish-data.js:6113-6118)", "hide", family="Multi-Color Sets")
    # "Horror & Occult" / "Optical & Light" (S20, 2026-08-09) are MIXED: scrubbed ids plus live ones
    # (e.g. gd_lyons_black_rainbow_holo_x). Their scrubbed members are retired above; the group names are not.

    # 4. Old generic decade_* patterns -- retired 2026-08-31, rebuilt as the decade shelves
    live = _live_decade_shelf_ids()
    for i in _old_decades():
        if i in live:
            continue  # six old ids were deliberately kept in the rebuilt shelves
        add("pattern", i, "2026-08-31",
            "paint-booth-0-finish-data.js:5696/5708 ('retired 2026-08-31 -- rebuilt as the decade shelves below'); "
            "engine/registry.py:78-81 deletes decade_* at build; engine/pattern_expansion.py re-adds at lazy load",
            "hide (rebuilt shelves supersede)", family="decades-generic-2026-04")

    # 5. Twelve retired special groups (FRACTURED RELICS 08-30, Atmosphere 08-31, ...)
    for g in _retired_group_names():
        add("special_group", g, "2026-08-31", "paint-booth-0-finish-data.js:2398-2408 `_retired` loop",
            "Owner: combinatorial grids / category ditched. Ids stay engine-resolvable for saved projects.")

    # 6. Six legacy base shelves, 104 ids -- owner 2026-09-05
    shelves, shelf_ids = _retired_shelves()
    for sname, ids in shelves.items():
        add("base_group", sname, "2026-09-05", "docs/RETIRED_SHELVES_2026-09-05.md", "Owner call 2026-09-05.")
        for i in ids:
            add("base", i, "2026-09-05", f"docs/RETIRED_SHELVES_2026-09-05.md ({sname})", "hide; renderer kept", family=sname)

    # 7. Earlier group removals with ids left in place (ids cross-referenced elsewhere)
    add("base_group", "Racing Heritage", "2026-05-18", "paint-booth-0-finish-data.js ~5710 ('Racing Heritage base group REMOVED')",
        "Owner mandate 2026-05-18; the 11 ids stay in BASES for cross-references.")
    add("special_group", "Carbon & Weave", "2026-04-23", "paint-booth-0-finish-data.js:2024-2028 (painter-truth cleanup)",
        "Retired from the shipping special-monolithic surface.")

    # 8. Scrapped feature
    add("feature", "finish_mixer", "2026-09-05",
        "Owner 2026-09-05: 'the custom finishes - we scrapped that part of the app'. Button removed earlier; "
        "js/zones/finish-mixer-controls.js, paint-booth-2-state-zones.js:20101-20650, server_routes/custom_finish_routes.py, "
        "server_routes/custom_finish_mixer_routes.py, /api/custom-finishes page-load fetch",
        "Scrapped. No script tag, no routes, no page-load fetch, no custom finishes pushed into BASES.",
        html_script="js/zones/finish-mixer-controls.js",
        routes=["/api/custom-finishes", "/api/save-custom-finish", "/api/delete-custom-finish", "/api/mix-preview", "/api/mix-paint-preview"],
        registrars=["register_custom_finish_routes(", "register_custom_finish_mixer_routes(",
                    "from server_routes.custom_finish_routes import", "from server_routes.custom_finish_mixer_routes import"],
        boot_calls=["_loadCustomFinishes"])

    # 9. Ungrouped lazy-only monolithics (24K Arsenal etc.) -- hidden by being in no group.
    #    Owner 2026-09-05: "the ones not showing up ... were told to be removed". Recorded so a rehome pass
    #    cannot resurrect them; basis marked INFERRED for the owner's review.
    lazy_path = os.path.join(ROOT, "_golden", "lazy_only_ids.json")
    lazy = json.load(open(lazy_path, encoding="utf-8")) if os.path.exists(lazy_path) else {"mono": [], "pat": []}
    groups = _groups_json()
    grouped_specials = {i for v in groups.get("SG", {}).values() for i in v}
    grouped_patterns = {i for v in groups.get("PG", {}).values() for i in v}
    grouped_any = grouped_specials | grouped_patterns | {i for v in groups.get("BG", {}).values() for i in v}
    known = {e.get("id") for e in entries}
    for i in sorted(lazy.get("mono", [])):
        if i in known or i in grouped_any:
            continue
        add("monolithic", i, "2026-06-03",
            "INFERRED: registered only by the lazy expansion load (shokker_24k_expansion / color monolithics) and in no picker group "
            "since the 2026-05-18 / 2026-06-03 section removals",
            "Owner 2026-09-05: not-showing == removed. Review basis=INFERRED.", family="lazy-only-ungrouped", basis="INFERRED")
    for i in sorted(lazy.get("pat", [])):
        if i in known or i in grouped_any or i in live:
            continue
        add("pattern", i, "2026-08-31", "INFERRED: lazy-only pattern in no PATTERN_GROUPS entry",
            "Owner 2026-09-05: not-showing == removed. Review basis=INFERRED.", family="lazy-only-ungrouped", basis="INFERRED")

    ledger = {
        "_doc": ("Retirement ledger -- the ONE list of what is dead and buried. policy 'hide' = never visible in any picker, "
                 "never injected/merged/rehomed by any script, marked retired:true by /api/finish-data; the renderer stays so "
                 "saved cars paint. Enforced by scripts/spb_retired_gate.py. Regenerate with scripts/build_retired_catalog.py -- "
                 "do not hand-edit ids. Owner mandate 2026-09-05: 'MAKE SURE that things that are supposed to be dead and buried "
                 "stay dead and buried.'"),
        "policy_default": "hide",
        "generated_by": "scripts/build_retired_catalog.py",
        "counts": {},
        "entries": entries,
    }
    from collections import Counter
    ledger["counts"] = dict(Counter(e["kind"] for e in entries))
    ledger["counts"]["inferred"] = sum(1 for e in entries if e.get("basis") == "INFERRED")
    return ledger


JS_OUT = os.path.join(ROOT, "js", "spb-retired-catalog.js")

JS_TEMPLATE = """// GENERATED by scripts/build_retired_catalog.py from scripts/retired_catalog.json -- DO NOT HAND-EDIT.
// Owner mandate 2026-09-05: "MAKE SURE that things that are supposed to be dead and buried stay dead and buried."
// Loaded BEFORE paint-booth-0-finish-data.js. Retired ids/groups are removed from every picker table at the
// end of catalog parse AND again after the /api/finish-data server merge, so no parse-time merge, runtime
// "rescue", "rehome" or server regroup can surface them. Tiles stay in MONOLITHICS/BASES/PATTERNS so a saved
// car that references a retired finish still renders. Gate: python scripts/spb_retired_gate.py
(function () {
    var IDS = %(ids)s;
    var GROUPS = %(groups)s;
    var idSet = new Set(IDS), groupSet = new Set(GROUPS);
    function pruneArray(arr) {
        if (!Array.isArray(arr)) return 0;
        var n = 0;
        for (var i = arr.length - 1; i >= 0; i--) { if (idSet.has(arr[i])) { arr.splice(i, 1); n++; } }
        return n;
    }
    function pruneTable(tbl) {
        if (!tbl || typeof tbl !== 'object') return 0;
        var n = 0;
        Object.keys(tbl).forEach(function (g) {
            if (groupSet.has(g)) { delete tbl[g]; n++; return; }
            n += pruneArray(tbl[g]);
        });
        return n;
    }
    function pruneSections(sections) {
        if (!sections || typeof sections !== 'object') return 0;
        var n = 0;
        Object.keys(sections).forEach(function (s) {
            var list = sections[s];
            if (!Array.isArray(list)) return;
            for (var i = list.length - 1; i >= 0; i--) { if (groupSet.has(list[i])) { list.splice(i, 1); n++; } }
        });
        return n;
    }
    window.SPB_RETIRED = {
        ids: idSet,
        groups: groupSet,
        count: IDS.length,
        isRetired: function (id) { return idSet.has(id); },
        isRetiredGroup: function (g) { return groupSet.has(g); },
        // Call with the live tables. Safe to call any number of times.
        prune: function (t) {
            t = t || {};
            var n = 0;
            n += pruneTable(t.SPECIAL_GROUPS); n += pruneTable(t.BASE_GROUPS); n += pruneTable(t.PATTERN_GROUPS);
            n += pruneSections(t.SPECIALS_SECTIONS);
            if (t.homes && typeof t.homes === 'object') {
                Object.keys(t.homes).forEach(function (id) { if (idSet.has(id) || groupSet.has(t.homes[id])) { delete t.homes[id]; n++; } });
            }
            try { window.SPB_RETIRED.lastPruned = n; } catch (e) {}
            return n;
        }
    };
})();
"""


def write_js(ledger: dict) -> None:
    ids = sorted({e["id"] for e in ledger["entries"] if "id" in e})
    groups = sorted({e["group"] for e in ledger["entries"] if "group" in e})
    src = JS_TEMPLATE % {"ids": json.dumps(ids, ensure_ascii=False), "groups": json.dumps(groups, ensure_ascii=False)}
    d = os.path.dirname(JS_OUT)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".retired-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    os.replace(tmp, JS_OUT)


def main() -> int:
    ledger = build()
    if "--print" not in sys.argv:
        d = os.path.dirname(LEDGER)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".retired-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=1, ensure_ascii=False)
        os.replace(tmp, LEDGER)
        write_js(ledger)
        print("wrote", LEDGER, "and", JS_OUT)
    print("retired ledger:", ledger["counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
