#!/usr/bin/env python3
"""spb_catalog_report.py -- READ-ONLY catalog-integrity report for Shokker Paint Booth.

Purpose
-------
Surface catalog-health facts the owner can check anytime, WITHOUT changing a
single byte of catalog data. This tool only *reads*: it imports the engine
(``shokker_engine_v2``, with the engine's chatty import stdout suppressed),
introspects the live registries + group tables, and prints a clear, skimmable
PASS / WARN report. It NEVER mutates the catalog, NEVER writes engine/data
files, and -- because it is a report, not a gate -- it ALWAYS exits 0 so it can
be wired into any build or cron without ever failing it.

What it reports
---------------
  1. Registry counts -- entries per stable registry (BASE / PATTERN / FINISH /
     MONOLITHIC) so you can see the catalog size at a glance.
  2. Phantom group refs -- a group lists an id that is NOT present in any
     registry (e.g. a "Predator Skins" group that still points at a retired
     ``sparkle_champagne`` id). These are dangling references the UI cannot
     resolve.
  3. Orphan / ungrouped entries -- ids that ARE in a registry but appear in NO
     group (or only land in a catch-all 'Misc' bucket), e.g. the known
     race-day-base stragglers. These render but are hard to find in the picker.
  4. Duplicate ids -- the same id claimed by more than one registry. (Within a
     single dict-keyed registry, keys are unique by construction, so a true
     duplicate can only happen ACROSS registries -- which is the data side of
     the dupe-key issue.)
  5. JS catalog cross-check (best-effort) -- if
     ``paint-booth-0-finish-data.js`` is cheaply parseable, scrape its finish
     ids / group ids and cross-check against the Python registries to flag ids
     present in one side but missing from the other.

Group discovery is done by *introspection* (it scans the engine module for any
dict that looks like ``{group_name: [id, ...]}`` plus callables that return
one), so it keeps working even if the engine's group plumbing is renamed -- it
never assumes a hard-coded attribute name. If no group table can be found the
group-dependent sections degrade to an INFO note rather than a crash.

run: python scripts/spb_catalog_report.py

Exit code
---------
  Always 0 -- this is a report, never a build gate. Read the PASS/WARN badges
  in the body to learn the catalog's health.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import os
import re
import sys
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Paths -- the project ROOT is the parent of this scripts/ directory. We never
# assume the current working directory is the project root (agents reset cwd).
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# The four stable registries documented in shokker_engine_v2's module docstring.
REGISTRY_NAMES = (
    "BASE_REGISTRY",
    "PATTERN_REGISTRY",
    "FINISH_REGISTRY",
    "MONOLITHIC_REGISTRY",
)

# The catch-all bucket name(s) an entry "falls into" when it has no real group.
# Landing here is treated as effectively-ungrouped (a WARN, never a FAIL).
_MISC_GROUP_NAMES = frozenset({"misc", "miscellaneous", "ungrouped", "other", "uncategorized"})

# The JS catalog data file we best-effort cross-check against.
JS_CATALOG_FILE = "paint-booth-0-finish-data.js"

# ---------------------------------------------------------------------------
# Status constants + result model
# ---------------------------------------------------------------------------
PASS = "PASS"
WARN = "WARN"
INFO = "INFO"


class Section:
    """One report section: a status, a one-line summary, and detail lines."""

    __slots__ = ("title", "status", "summary", "details")

    def __init__(
        self,
        title: str,
        status: str,
        summary: str,
        details: Optional[List[str]] = None,
    ) -> None:
        self.title = title
        self.status = status
        self.summary = summary
        self.details = details or []


# ---------------------------------------------------------------------------
# Color helpers -- colorama if available + TTY, plain-text fallback otherwise.
# (Mirrors spb_doctor.py so the two tools read alike.)
# ---------------------------------------------------------------------------
def _make_colors():
    ident: Callable[[str], str] = lambda s: s
    if not sys.stdout.isatty():
        return ident, ident, ident, ident, ident
    try:
        import colorama  # type: ignore

        colorama.init()
        from colorama import Fore, Style  # type: ignore

        return (
            lambda s: f"{Fore.GREEN}{s}{Style.RESET_ALL}",
            lambda s: f"{Fore.YELLOW}{s}{Style.RESET_ALL}",
            lambda s: f"{Fore.CYAN}{s}{Style.RESET_ALL}",
            lambda s: f"{Style.DIM}{s}{Style.RESET_ALL}",
            lambda s: f"{Style.BRIGHT}{s}{Style.RESET_ALL}",
        )
    except Exception:
        return ident, ident, ident, ident, ident


GREEN, YELLOW, CYAN, DIM, BRIGHT = _make_colors()


def _status_badge(status: str) -> str:
    if status == PASS:
        return GREEN("PASS")
    if status == WARN:
        return YELLOW("WARN")
    return CYAN("INFO")


# ---------------------------------------------------------------------------
# Engine import -- stdout-suppressed (the engine prints during import) and
# wrapped so a failure becomes a reported note rather than a crash. NOT
# memoized in any way that could drop circular-import-recovered finishes: we do
# a single plain import_module and use whatever the engine exposes.
# ---------------------------------------------------------------------------
def _import_engine() -> Tuple[Optional[object], Optional[str]]:
    """Import shokker_engine_v2 with stdout suppressed.

    Returns (module, error_string_or_None). The engine emits progress chatter
    to stdout during import; we redirect that into a throwaway buffer so the
    report stays clean. stderr is left alone so genuine warnings still surface.
    """
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink):
            mod = importlib.import_module("shokker_engine_v2")
        return mod, None
    except Exception as exc:  # noqa: BLE001 - report any import failure as a note
        return None, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------
def _get_registries(eng) -> Dict[str, dict]:
    """Return {name: registry_dict} for every stable registry that is a dict."""
    out: Dict[str, dict] = {}
    for name in REGISTRY_NAMES:
        reg = getattr(eng, name, None)
        if isinstance(reg, dict):
            out[name] = reg
    return out


def _all_registry_ids(registries: Dict[str, dict]) -> Set[str]:
    """Union of every id across every registry."""
    ids: Set[str] = set()
    for reg in registries.values():
        ids.update(str(k) for k in reg.keys())
    return ids


# ---------------------------------------------------------------------------
# Group discovery -- find {group_name: [id, ...]} tables by introspection so we
# do not hard-code a (possibly-renamed) attribute name.
# ---------------------------------------------------------------------------
def _looks_like_group_map(obj) -> bool:
    """True if obj is a dict mapping str group-name -> iterable of str-ish ids.

    We sample (don't fully scan) for speed and require the common shape: keys
    are strings and at least one value is a list/tuple/set of scalars. Plain
    registry dicts (whose values are dicts/tuples of callables) won't match.
    """
    if not isinstance(obj, dict) or not obj:
        return False
    saw_list_of_scalars = False
    for i, (k, v) in enumerate(obj.items()):
        if not isinstance(k, str):
            return False
        if isinstance(v, (list, tuple, set, frozenset)):
            for item in v:
                if isinstance(item, (str, int)):
                    saw_list_of_scalars = True
                else:
                    # value collections that hold dicts/objects are not id lists
                    return False
        elif isinstance(v, dict):
            # could be {group: {sub: [...]}} -- not the flat shape we want here
            return False
        if i >= 25:
            break
    return saw_list_of_scalars


def _normalize_group_map(obj) -> Dict[str, List[str]]:
    """Coerce a discovered group map into {group_name: [str_id, ...]}."""
    out: Dict[str, List[str]] = {}
    for k, v in obj.items():
        if isinstance(v, (list, tuple, set, frozenset)):
            out[str(k)] = [str(x) for x in v]
    return out


def discover_group_maps(eng) -> Tuple[Dict[str, Dict[str, List[str]]], List[str]]:
    """Discover engine group tables by introspection.

    Returns (maps, notes) where ``maps`` is {attr_name: {group: [id,...]}} for
    every module attribute that looks like a flat group->ids table (or a
    zero-arg callable that returns one), and ``notes`` records what was found /
    skipped for the report's INFO line.
    """
    maps: Dict[str, Dict[str, List[str]]] = {}
    notes: List[str] = []

    for name in sorted(dir(eng)):
        low = name.lower()
        if "group" not in low:
            continue
        if name in REGISTRY_NAMES:
            continue
        try:
            obj = getattr(eng, name)
        except Exception:  # noqa: BLE001
            continue
        # Direct dict group-map.
        if _looks_like_group_map(obj):
            maps[name] = _normalize_group_map(obj)
            notes.append(f"{name} ({len(maps[name])} groups)")
            continue
        # Zero-arg callable that returns a group-map (no required params).
        if callable(obj):
            try:
                code = getattr(obj, "__code__", None)
                required = 0
                if code is not None:
                    defaults = getattr(obj, "__defaults__", None) or ()
                    required = code.co_argcount - len(defaults)
                if required != 0:
                    continue
                with contextlib.redirect_stdout(io.StringIO()):
                    result = obj()
            except Exception:  # noqa: BLE001 - never let discovery crash the report
                continue
            if _looks_like_group_map(result):
                maps[name] = _normalize_group_map(result)
                notes.append(f"{name}() ({len(maps[name])} groups)")

    return maps, notes


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def section_registry_counts(registries: Dict[str, dict], import_err: Optional[str]) -> Section:
    """Counts per registry (always informational)."""
    if import_err:
        return Section(
            "Registry counts",
            INFO,
            f"engine import failed: {import_err}",
            ["  (catalog could not be loaded; remaining sections will be limited)"],
        )
    details: List[str] = []
    total = 0
    for name in REGISTRY_NAMES:
        reg = registries.get(name)
        if reg is None:
            details.append(f"  {name:<20} (not a dict / missing)")
            continue
        n = len(reg)
        total += n
        details.append(f"  {name:<20} {n}")
    short = ", ".join(
        f"{n.split('_')[0].title()}={len(registries[n])}"
        for n in REGISTRY_NAMES
        if n in registries
    )
    return Section(
        "Registry counts",
        PASS,
        f"{total} catalog entries across {len(registries)} registries ({short})",
        details,
    )


def section_duplicate_ids(registries: Dict[str, dict]) -> Section:
    """Duplicate ids = an id claimed by more than one registry (cross-registry).

    Within one dict-keyed registry the keys are unique by construction, so a
    true duplicate id can only be one that appears in two+ registries. That is
    the data side of the dupe-key issue.
    """
    if not registries:
        return Section("Duplicate ids", INFO, "no registries loaded; nothing to compare", [])

    owners: Dict[str, List[str]] = {}
    for reg_name, reg in registries.items():
        for key in reg.keys():
            owners.setdefault(str(key), []).append(reg_name)

    dupes = {k: v for k, v in owners.items() if len(v) > 1}
    if not dupes:
        return Section(
            "Duplicate ids",
            PASS,
            "no id claimed by more than one registry",
            [f"  {len(owners)} unique ids across {len(registries)} registries"],
        )
    details = [f"  '{k}' in: {', '.join(sorted(set(v)))}" for k, v in sorted(dupes.items())[:20]]
    if len(dupes) > 20:
        details.append(f"  ... +{len(dupes) - 20} more")
    return Section(
        "Duplicate ids",
        WARN,
        f"{len(dupes)} id(s) claimed by more than one registry",
        details,
    )


def section_phantom_group_refs(
    group_maps: Dict[str, Dict[str, List[str]]],
    all_ids: Set[str],
    discovery_notes: List[str],
) -> Section:
    """Phantom refs: a group lists an id that is in NO registry (dangling)."""
    if not group_maps:
        return Section(
            "Phantom group refs",
            INFO,
            "no group table discovered in the engine; skipped",
            ["  (group->id tables are introspected; none matched the expected shape)"],
        )

    phantoms: List[Tuple[str, str, str]] = []  # (attr, group, id)
    total_refs = 0
    for attr, gmap in group_maps.items():
        for group, ids in gmap.items():
            for fid in ids:
                total_refs += 1
                if fid not in all_ids:
                    phantoms.append((attr, group, fid))

    note = "groups: " + ("; ".join(discovery_notes) if discovery_notes else "n/a")
    if not phantoms:
        return Section(
            "Phantom group refs",
            PASS,
            f"all {total_refs} group references resolve to a registry id",
            [f"  {note}"],
        )
    details = [f"  {note}"]
    details += [f"  [{attr}] group '{g}' -> missing id '{i}'" for (attr, g, i) in phantoms[:25]]
    if len(phantoms) > 25:
        details.append(f"  ... +{len(phantoms) - 25} more")
    return Section(
        "Phantom group refs",
        WARN,
        f"{len(phantoms)} group reference(s) point at an id not in any registry",
        details,
    )


def section_orphan_entries(
    group_maps: Dict[str, Dict[str, List[str]]],
    registries: Dict[str, dict],
) -> Section:
    """Orphans: ids in a registry but in NO group (or only in a 'Misc' bucket).

    We only consider registries that the discovered groups actually reference,
    so we don't falsely flag a whole registry (e.g. BASE) that legitimately
    isn't grouped in the picker. An id is reported as:
      * ungrouped  -- not present in any discovered group, OR
      * misc-only  -- present only in a catch-all 'Misc'/'Ungrouped' bucket.
    """
    if not group_maps:
        return Section(
            "Orphan / ungrouped",
            INFO,
            "no group table discovered in the engine; skipped",
            ["  (cannot compute ungrouped entries without a group->id table)"],
        )

    # All ids that any group references (regardless of which registry owns them).
    grouped_real: Set[str] = set()
    grouped_misc_only: Set[str] = set()
    referenced_ids: Set[str] = set()
    for gmap in group_maps.values():
        for group, ids in gmap.items():
            is_misc = group.strip().lower() in _MISC_GROUP_NAMES
            for fid in ids:
                referenced_ids.add(fid)
                if is_misc:
                    grouped_misc_only.add(fid)
                else:
                    grouped_real.add(fid)
    # An id "really grouped" if it appears in any non-misc group.
    misc_only = {i for i in grouped_misc_only if i not in grouped_real}

    # Which registries does the group system actually cover? Only flag ungrouped
    # ids from registries that have at least one grouped member -- otherwise a
    # registry that is simply never grouped (by design) would spam false orphans.
    covered_regs: List[str] = []
    for reg_name, reg in registries.items():
        reg_ids = {str(k) for k in reg.keys()}
        if reg_ids & referenced_ids:
            covered_regs.append(reg_name)

    ungrouped: List[Tuple[str, str]] = []  # (reg, id)
    for reg_name in covered_regs:
        for fid in (str(k) for k in registries[reg_name].keys()):
            if fid not in referenced_ids:
                ungrouped.append((reg_name, fid))

    problems = len(ungrouped) + len(misc_only)
    cov = ", ".join(covered_regs) if covered_regs else "none"
    if problems == 0:
        return Section(
            "Orphan / ungrouped",
            PASS,
            f"every entry in grouped registries ({cov}) lands in a real group",
            [f"  registries covered by groups: {cov}"],
        )

    details = [f"  registries covered by groups: {cov}"]
    if ungrouped:
        details.append(f"  ungrouped (in registry, in no group): {len(ungrouped)}")
        for reg_name, fid in ungrouped[:20]:
            details.append(f"    [{reg_name}] '{fid}'")
        if len(ungrouped) > 20:
            details.append(f"    ... +{len(ungrouped) - 20} more")
    if misc_only:
        details.append(f"  misc-only (only in a catch-all bucket): {len(misc_only)}")
        for fid in sorted(misc_only)[:20]:
            details.append(f"    '{fid}'")
        if len(misc_only) > 20:
            details.append(f"    ... +{len(misc_only) - 20} more")
    return Section(
        "Orphan / ungrouped",
        WARN,
        f"{problems} entry(ies) ungrouped or only in a 'Misc' bucket",
        details,
    )


# ---------------------------------------------------------------------------
# JS catalog cross-check (best-effort, regex-scraped -- never executes JS).
# ---------------------------------------------------------------------------
def _scrape_js_ids(text: str) -> Set[str]:
    """Best-effort scrape of finish ids from the JS catalog source.

    We look for ``id: 'foo'`` / ``id: "foo"`` and ``"id": "foo"`` shapes. This
    is intentionally conservative: if the file's shape doesn't match, we return
    whatever we found (possibly empty) and the caller degrades to an INFO note.
    """
    ids: Set[str] = set()
    for m in re.finditer(r"""["']?\bid["']?\s*:\s*["']([^"']+)["']""", text):
        ids.add(m.group(1))
    return ids


def section_js_crosscheck(all_ids: Set[str]) -> Section:
    """Cross-check Python registry ids against the JS catalog's scraped ids."""
    path = os.path.join(ROOT_DIR, JS_CATALOG_FILE)
    if not os.path.isfile(path):
        return Section(
            "JS catalog cross-check",
            INFO,
            f"{JS_CATALOG_FILE} not found; skipped",
            [],
        )
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception as exc:  # noqa: BLE001
        return Section(
            "JS catalog cross-check",
            INFO,
            f"could not read {JS_CATALOG_FILE}: {type(exc).__name__}: {exc}",
            [],
        )

    js_ids = _scrape_js_ids(text)
    if not js_ids:
        return Section(
            "JS catalog cross-check",
            INFO,
            f"no ids cheaply parseable from {JS_CATALOG_FILE}; skipped deep compare",
            ["  (the scrape found no id: '...' literals; file shape may differ)"],
        )

    if not all_ids:
        return Section(
            "JS catalog cross-check",
            INFO,
            f"scraped {len(js_ids)} JS ids but engine registries empty; no compare",
            [],
        )

    only_js = sorted(js_ids - all_ids)
    only_py = sorted(all_ids - js_ids)
    overlap = len(js_ids & all_ids)

    if not only_js and not only_py:
        return Section(
            "JS catalog cross-check",
            PASS,
            f"JS and Python id sets agree ({overlap} shared ids)",
            [f"  scraped {len(js_ids)} JS ids; {len(all_ids)} Python ids"],
        )

    details = [f"  scraped {len(js_ids)} JS ids; {len(all_ids)} Python ids; {overlap} shared"]
    if only_js:
        details.append(f"  in JS but not in any Python registry: {len(only_js)}")
        for fid in only_js[:15]:
            details.append(f"    '{fid}'")
        if len(only_js) > 15:
            details.append(f"    ... +{len(only_js) - 15} more")
    if only_py:
        details.append(f"  in Python but not scraped from JS: {len(only_py)}")
        for fid in only_py[:15]:
            details.append(f"    '{fid}'")
        if len(only_py) > 15:
            details.append(f"    ... +{len(only_py) - 15} more")
    # WARN only when the JS side references ids Python cannot resolve (the side
    # that actually breaks the UI). Python-only ids are common (bases, helpers
    # not surfaced in the finish catalog) so they stay informational.
    status = WARN if only_js else INFO
    summary = (
        f"{len(only_js)} JS id(s) missing from Python"
        if only_js
        else f"{len(only_py)} Python id(s) not scraped from JS (informational)"
    )
    return Section("JS catalog cross-check", status, summary, details)


# ---------------------------------------------------------------------------
# Runner + report
# ---------------------------------------------------------------------------
def build_report() -> List[Section]:
    """Run every section and return the ordered list of results (pure-ish)."""
    eng, import_err = _import_engine()
    registries = _get_registries(eng) if eng is not None else {}
    all_ids = _all_registry_ids(registries)

    group_maps: Dict[str, Dict[str, List[str]]] = {}
    discovery_notes: List[str] = []
    if eng is not None:
        try:
            group_maps, discovery_notes = discover_group_maps(eng)
        except Exception as exc:  # noqa: BLE001 - discovery must never crash report
            discovery_notes = [f"group discovery error: {type(exc).__name__}: {exc}"]

    sections: List[Section] = []
    sections.append(section_registry_counts(registries, import_err))
    sections.append(section_duplicate_ids(registries))
    sections.append(section_phantom_group_refs(group_maps, all_ids, discovery_notes))
    sections.append(section_orphan_entries(group_maps, registries))
    sections.append(section_js_crosscheck(all_ids))
    return sections


def _run_section(fn: Callable[[], Section]) -> Section:
    """Defensive wrapper -- a crashing section becomes an INFO note, not a stop."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return Section("section", INFO, f"section crashed: {type(exc).__name__}: {exc}", [])


def main(argv: Optional[List[str]] = None) -> int:
    print()
    print(DIM("=" * 66))
    print(BRIGHT(" SPB CATALOG REPORT -- read-only catalog-integrity report"))
    print(DIM(f" root: {ROOT_DIR}"))
    print(DIM(" (report-only: never mutates the catalog; always exits 0)"))
    print(DIM("=" * 66))

    sections = build_report()

    n_pass = sum(1 for s in sections if s.status == PASS)
    n_warn = sum(1 for s in sections if s.status == WARN)
    n_info = sum(1 for s in sections if s.status == INFO)

    for s in sections:
        print(f"[{_status_badge(s.status)}] {s.title:<22} {s.summary}")
        for line in s.details:
            print(DIM(f"        {line}"))

    print(DIM("-" * 66))
    print(
        f" {GREEN(str(n_pass) + ' PASS')}   "
        f"{YELLOW(str(n_warn) + ' WARN')}   "
        f"{CYAN(str(n_info) + ' INFO')}"
    )
    if n_warn:
        print(
            YELLOW(
                " RESULT: catalog has WARN item(s) above to review "
                "(report-only -- not a build failure)."
            )
        )
    else:
        print(GREEN(" RESULT: no catalog warnings surfaced."))
    print(DIM("=" * 66))
    print()

    # Report-only: ALWAYS exit 0. Never fail a build.
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
