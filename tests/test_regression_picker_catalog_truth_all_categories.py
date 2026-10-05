"""Catalog-truth coverage for BASE / PATTERN / SPEC_PATTERN picker groups.

## Why this exists (2026-04-24 overnight Iter 1)

`tests/test_regression_specials_catalog_truth.py` already ratchets:
  * No duplicate ids inside SPECIAL_GROUPS
  * Shipping special ids resolve to a real renderer (or are declared gradient family)
  * Shipping special ids do not silently use an active catalog fallback

But that test ONLY covers SPECIAL_GROUPS. The painter-facing pickers also
include BASES (`BASE_GROUPS`), PATTERNS (`PATTERN_GROUPS`), and SPEC_PATTERNS
(`SPEC_PATTERN_GROUPS`). If a future edit adds a picker-exposed id in any
of those that has no Python renderer, or that silently routes to a generic
catalog fallback, the existing test does not fire.

This file mirrors the specials-test contract for the other three picker
families. If any of these tests fire, painters can SELECT an id that
either renders nothing (orphan) or renders an unrelated/generic finish
(active-fallback) — both are silent painter-trust violations the project
has been hunting since the 2026-04-21 CODEX_THREAD_HANDOFF doctrine.

## Honest scope

* "Orphan" = picker-exposed id with no entry in the matching Python
  registry (BASE_REGISTRY / MONOLITHIC_REGISTRY for bases;
  PATTERN_REGISTRY for patterns; SPEC_PATTERN_CATALOG for spec patterns).
* "Active fallback" = id whose MONOLITHIC_REGISTRY entry is _identical_
  to its `CATALOG_FALLBACK_WIRED_TO[id]` target (the catalog wiring
  pointed it at a sibling generic). Same definition the specials test
  uses; copy-pasted on purpose.
* Patterns and spec patterns currently have no equivalent fallback wiring,
  so the active-fallback check is base-only.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load_catalog():
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
const baseGroups = vm.runInContext('BASE_GROUPS', ctx);
const patternGroups = vm.runInContext('PATTERN_GROUPS', ctx);
const specPatternGroups = vm.runInContext('SPEC_PATTERN_GROUPS', ctx);
console.log(JSON.stringify({ baseGroups, patternGroups, specPatternGroups }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", check=True,
    )
    return json.loads(result.stdout)


def _flatten_owners(groups):
    owners = {}
    for grp, ids in (groups or {}).items():
        for fid in ids or []:
            owners.setdefault(fid, []).append(grp)
    return owners


def _spec_pattern_catalog():
    """Return the dict of {spec_pattern_id -> renderer_fn} the engine ships."""
    try:
        from engine.spec_patterns import PATTERN_CATALOG
    except Exception:
        try:
            import shokker_engine_v2 as eng
            return getattr(eng, "SPEC_PATTERN_CATALOG", {})
        except Exception:
            return {}
    return PATTERN_CATALOG


def test_no_base_picker_orphans_in_shipping():
    """Every id in BASE_GROUPS must resolve to BASE_REGISTRY or MONOLITHIC_REGISTRY.
    Pickable-but-renders-nothing is a silent painter-trust violation."""
    import shokker_engine_v2 as eng
    eng._ensure_expansions_loaded()
    cat = _load_catalog()
    owners = _flatten_owners(cat["baseGroups"])
    orphans = sorted(
        bid for bid in owners
        if bid not in eng.BASE_REGISTRY and bid not in eng.MONOLITHIC_REGISTRY
    )
    assert orphans == [], (
        f"BASE_GROUPS exposes {len(orphans)} picker ids with no Python renderer. "
        f"Painters can select these and see nothing render: {orphans[:25]}"
    )


def test_no_pattern_picker_orphans_in_shipping():
    """Every id in PATTERN_GROUPS must resolve to PATTERN_REGISTRY."""
    import shokker_engine_v2 as eng
    eng._ensure_expansions_loaded()
    cat = _load_catalog()
    owners = _flatten_owners(cat["patternGroups"])
    orphans = sorted(pid for pid in owners if pid not in eng.PATTERN_REGISTRY)
    assert orphans == [], (
        f"PATTERN_GROUPS exposes {len(orphans)} picker ids with no PATTERN_REGISTRY "
        f"entry. Painters can select these and see nothing render: {orphans[:25]}"
    )


def test_no_spec_pattern_picker_orphans_in_shipping():
    """Every id in SPEC_PATTERN_GROUPS must resolve in SPEC_PATTERN_CATALOG."""
    cat = _load_catalog()
    owners = _flatten_owners(cat["specPatternGroups"])
    spec_cat = _spec_pattern_catalog()
    orphans = sorted(sid for sid in owners if sid not in spec_cat)
    assert orphans == [], (
        f"SPEC_PATTERN_GROUPS exposes {len(orphans)} picker ids with no "
        f"SPEC_PATTERN_CATALOG entry. Painters can select these and see no spec "
        f"overlay render: {orphans[:25]}"
    )


def test_no_base_picker_id_silently_uses_catalog_fallback():
    """Mirror of test_shipping_special_ids_do_not_use_active_catalog_fallbacks
    but for the BASE_GROUPS picker. A base id whose MONOLITHIC_REGISTRY entry
    is byte-identical to a sibling fallback target means the painter sees a
    generic family render instead of the named finish — the same silent-no-op
    bug class CATALOG_FALLBACK_WIRED_TO was created to expose."""
    import shokker_engine_v2 as eng
    eng._ensure_expansions_loaded()
    cat = _load_catalog()
    owners = _flatten_owners(cat["baseGroups"])
    fallback_to = getattr(eng, "CATALOG_FALLBACK_WIRED_TO", {})

    def _is_active_fallback(fid: str) -> bool:
        target = fallback_to.get(fid)
        return bool(
            target
            and fid in eng.MONOLITHIC_REGISTRY
            and target in eng.MONOLITHIC_REGISTRY
            and eng.MONOLITHIC_REGISTRY[fid] == eng.MONOLITHIC_REGISTRY[target]
        )

    active = sorted(
        f"{fid} -> {fallback_to[fid]}"
        for fid in owners
        if _is_active_fallback(fid)
    )
    assert active == [], (
        f"BASE_GROUPS exposes {len(active)} ids whose renderer is byte-identical "
        f"to a generic catalog fallback. Painter selects a named finish but sees "
        f"the family default: {active[:25]}"
    )


def test_no_unauthorised_base_group_duplicates():
    """The only base ids that may appear in more than one group are the
    Foundation aliases that the legacy picker re-exposes for the spec
    finish dropdown. Anything else is duplicate-category drift."""
    cat = _load_catalog()
    owners = _flatten_owners(cat["baseGroups"])
    dupes = {bid: grps for bid, grps in owners.items() if len(grps) > 1}
    allowed = {
        "ceramic": ["Foundation", "Ceramic & Glass"],
        "piano_black": ["Foundation", "Ceramic & Glass"],
    }
    assert dupes == allowed, (
        f"Unexpected base picker duplicates: {dupes}. Allowed Foundation aliases: "
        f"{allowed}. New duplicates need either explicit whitelisting or removal "
        f"from one of the groups."
    )


def test_picker_total_id_counts_match_audit_baseline():
    """Sentinel: catastrophic drops in picker coverage should fire here.

    Iter 1 baseline measured 256 BASE_GROUPS ids, 307 PATTERN_GROUPS ids,
    255 SPEC_PATTERN_GROUPS ids. Allow growth. Allow modest pruning.
    Catch a mass-deletion regression that drops more than ~15% of any
    picker family."""
    cat = _load_catalog()
    base_n = len(_flatten_owners(cat["baseGroups"]))
    pat_n = len(_flatten_owners(cat["patternGroups"]))
    spec_pat_n = len(_flatten_owners(cat["specPatternGroups"]))
    assert base_n >= 217, f"BASE_GROUPS shrunk from baseline 256 to {base_n} (>15% loss)"
    assert pat_n >= 261, f"PATTERN_GROUPS shrunk from baseline 307 to {pat_n} (>15% loss)"
    assert spec_pat_n >= 217, f"SPEC_PATTERN_GROUPS shrunk from baseline 255 to {spec_pat_n} (>15% loss)"
