"""Registry / catalog internal-consistency contracts (shape, not values).

These tests assert INVARIANTS about the *structure* of the engine's four
primary registries, never about churning *values*:

    BASE_REGISTRY        ~518  dict entries  {base_spec_fn, paint_fn, CC, M, R, desc, ...}
    FINISH_REGISTRY      ~43   2-tuple entries (callable, callable)
    PATTERN_REGISTRY     ~617  dict entries  {paint_fn, desc, [texture_fn], [image_path], ...}
    MONOLITHIC_REGISTRY  ~985  2-tuple entries (callable, callable)

What we deliberately do NOT assert (these churn daily as the catalog is rebuilt):
exact counts, exact IDs, exact membership, exact CC/M/R values, exact pixels.

What we DO assert (holds regardless of catalog contents):
  * each registry loads, is a dict, and is non-empty
  * no entry is None
  * every entry is the expected *type* for its registry (dict vs 2-tuple)
  * the callable contract each registry uses is honoured by EVERY entry
    (BASE: base_spec_fn + paint_fn callable; PATTERN: paint_fn callable;
     FINISH/MONOLITHIC: a 2-tuple of callables)
  * finish IDs within a registry are unique (no internal collisions)
  * "no phantom group": every key maps to a real, renderable entry -- and every
    pattern *alias* points at a target key that actually exists in the same
    registry (derived from the registry itself, never a hardcoded list)

The catalog count thresholds used below are deliberately tiny floor checks
(">= a handful") that exist only to prove the registry actually loaded its data
module rather than coming up empty; they are an order of magnitude below the
real sizes and so never flap when the owner curates the catalog.
"""

from __future__ import annotations

import numbers

import pytest


# Map our short fixture names -> the engine attribute that backs each registry.
# Used to give precise, registry-named assertion messages.
_REGISTRY_ATTR = {
    "BASE": "BASE_REGISTRY",
    "FINISH": "FINISH_REGISTRY",
    "PATTERN": "PATTERN_REGISTRY",
    "MONOLITHIC": "MONOLITHIC_REGISTRY",
}

ALL_NAMES = tuple(_REGISTRY_ATTR)

# Registries whose entries are dicts vs. (callable, callable) 2-tuples.
_DICT_REGISTRIES = ("BASE", "PATTERN")
_TUPLE_REGISTRIES = ("FINISH", "MONOLITHIC")

# Tiny floor: a registry that loaded its data module will have at least this many
# entries. Set far below real sizes so curation never trips it.
_NONEMPTY_FLOOR = 5


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _reg(registries, name):
    """Fetch one registry from the conftest `registries` fixture by short name."""
    assert name in registries, (
        f"{name} missing from registries fixture (have {sorted(registries)})"
    )
    return registries[name]


# ---------------------------------------------------------------------------
# load / non-empty / type-of-container
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_NAMES)
def test_registry_loads_and_is_a_nonempty_dict(registries, name):
    """Each registry loaded, is a dict container, and is non-empty.

    We assert a tiny floor (not an exact count) purely to prove the data module
    actually populated the registry instead of coming up empty.
    """
    reg = _reg(registries, name)
    assert reg is not None, f"{name} registry is None"
    assert isinstance(reg, dict), (
        f"{name} registry is {type(reg).__name__}, expected dict"
    )
    assert len(reg) >= _NONEMPTY_FLOOR, (
        f"{name} registry has only {len(reg)} entries (looks unloaded); "
        f"expected at least {_NONEMPTY_FLOOR}"
    )


@pytest.mark.parametrize("name", ALL_NAMES)
def test_no_entry_is_none(registries, name):
    """No entry in any registry is None."""
    reg = _reg(registries, name)
    nones = [k for k, v in reg.items() if v is None]
    assert not nones, f"{name} has None entries for keys: {nones[:10]}"


@pytest.mark.parametrize("name", ALL_NAMES)
def test_keys_are_nonempty_strings(registries, name):
    """Registry keys (finish IDs) are non-empty strings."""
    reg = _reg(registries, name)
    bad = [k for k in reg if not isinstance(k, str) or not k.strip()]
    assert not bad, f"{name} has non-string/empty keys: {bad[:10]}"


# ---------------------------------------------------------------------------
# entry TYPE matches each registry's convention
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", _DICT_REGISTRIES)
def test_dict_registry_entries_are_dicts(registries, name):
    """BASE / PATTERN entries are dicts (not tuples, not scalars)."""
    reg = _reg(registries, name)
    wrong = {k: type(v).__name__ for k, v in reg.items() if not isinstance(v, dict)}
    assert not wrong, (
        f"{name} has non-dict entries: {dict(list(wrong.items())[:10])}"
    )


@pytest.mark.parametrize("name", _TUPLE_REGISTRIES)
def test_tuple_registry_entries_are_2_tuples_of_callables(registries, name):
    """FINISH / MONOLITHIC entries are length-2 tuples of callables.

    This is the registry's spec_fn/paint_fn pairing in positional form; both
    elements must be callable for the entry to be renderable.
    """
    reg = _reg(registries, name)
    not_tuple = {k: type(v).__name__ for k, v in reg.items()
                 if not isinstance(v, tuple)}
    assert not not_tuple, (
        f"{name} has non-tuple entries: {dict(list(not_tuple.items())[:10])}"
    )
    wrong_len = {k: len(v) for k, v in reg.items() if len(v) != 2}
    assert not wrong_len, (
        f"{name} has tuple entries that are not length-2: "
        f"{dict(list(wrong_len.items())[:10])}"
    )
    not_callable = [k for k, v in reg.items()
                    if not all(callable(x) for x in v)]
    assert not not_callable, (
        f"{name} has tuple entries with a non-callable element: "
        f"{not_callable[:10]}"
    )


# ---------------------------------------------------------------------------
# required callable keys present + callable (dict registries)
# ---------------------------------------------------------------------------

# The callable keys each dict registry *requires* on every entry. Derived from
# the registries' own universal convention (verified to hold across all entries),
# not from a curated list of finishes -- so it stays green across rebuilds.
_REQUIRED_CALLABLE_KEYS = {
    "BASE": ("base_spec_fn", "paint_fn"),
    # PATTERN intentionally requires only paint_fn: texture_fn is optional in the
    # current catalog (many image-backed / asset-variant patterns omit it).
    "PATTERN": ("paint_fn",),
}


@pytest.mark.parametrize("name", sorted(_REQUIRED_CALLABLE_KEYS))
def test_dict_registry_required_callables_present(registries, name):
    """Every dict entry carries its registry's required callable keys, and each
    such key's value is actually callable.
    """
    reg = _reg(registries, name)
    required = _REQUIRED_CALLABLE_KEYS[name]
    for key in required:
        missing = [k for k, v in reg.items() if key not in v]
        assert not missing, (
            f"{name}: {len(missing)} entries missing required key {key!r} "
            f"(e.g. {missing[:8]})"
        )
        non_callable = [k for k, v in reg.items() if not callable(v.get(key))]
        assert not non_callable, (
            f"{name}: {len(non_callable)} entries have non-callable {key!r} "
            f"(e.g. {non_callable[:8]})"
        )


@pytest.mark.parametrize("name", ["PATTERN"])
def test_optional_texture_fn_is_callable_or_none(registries, name):
    """A PATTERN entry's texture_fn, where present, is either callable or None.

    texture_fn is optional in two ways: the key may be absent, OR the key may be
    present with value ``None`` (the catalog's explicit "no texture" sentinel --
    ~235 entries use this). What we forbid is a *present, non-None, non-callable*
    texture_fn (e.g. a stray string), which would crash a pattern that tries to
    invoke it.
    """
    reg = _reg(registries, name)
    bad = [(k, type(v["texture_fn"]).__name__) for k, v in reg.items()
           if "texture_fn" in v
           and v["texture_fn"] is not None
           and not callable(v["texture_fn"])]
    assert not bad, (
        f"{name} has a present, non-None, non-callable texture_fn: {bad[:10]}"
    )


# ---------------------------------------------------------------------------
# numeric spec params are numeric (BASE)
# ---------------------------------------------------------------------------

def test_base_spec_params_are_numeric_where_present(registries):
    """BASE entries' CC/M/R spec parameters, where present, are real numbers.

    We assert the *type* (numeric, finite), never the value -- the actual
    CC/M/R numbers churn as the owner tunes finishes.
    """
    reg = _reg(registries, "BASE")
    bad = []
    for k, v in reg.items():
        for field in ("CC", "M", "R"):
            if field in v:
                val = v[field]
                if isinstance(val, bool) or not isinstance(val, numbers.Number):
                    bad.append((k, field, type(val).__name__))
                elif val != val or val in (float("inf"), float("-inf")):
                    bad.append((k, field, "non-finite"))
    assert not bad, f"BASE has non-numeric/non-finite spec params: {bad[:10]}"


# ---------------------------------------------------------------------------
# uniqueness of finish IDs within a registry
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_NAMES)
def test_finish_ids_unique_within_registry(registries, name):
    """Finish IDs are unique within a registry, and each is hashable.

    Each registry is a dict, so raw keys are unique by construction -- this test
    proves that guarantee actually holds (the container really is a dict whose
    key set has no duplicates and whose keys are all hashable, so a finish can be
    looked up deterministically). We do NOT impose a case-insensitive rule: the
    current catalog legitimately ships distinct entries that differ only by case
    (e.g. ``art_deco`` vs ``Art_Deco``), and that membership churns -- so a
    case-fold contract would flap without protecting any real invariant.
    """
    reg = _reg(registries, name)
    keys = list(reg.keys())
    # Hashable (dict membership already proves this, but assert it explicitly so
    # the contract is documented and a future list-backed registry would fail).
    for k in keys:
        hash(k)
    assert len(keys) == len(set(keys)), (
        f"{name} has duplicate finish IDs (impossible for a dict -- the registry "
        f"is not the dict it claims to be)"
    )


# ---------------------------------------------------------------------------
# "no phantom group": every key renders + aliases resolve
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_NAMES)
def test_no_phantom_every_key_maps_to_renderable_entry(registries, name):
    """Every key maps to a renderable entry per its registry's convention.

    Renderable means: dict registries -> the required callable key(s) are present
    and callable; tuple registries -> a 2-tuple of callables. Derived entirely
    from the registry's own shape, with no hardcoded membership, so a placeholder
    / phantom key (empty dict, stub, bad tuple) is caught while curation is not.
    """
    reg = _reg(registries, name)
    phantoms = []
    for k, v in reg.items():
        if name in _DICT_REGISTRIES:
            if not isinstance(v, dict):
                phantoms.append((k, f"not-a-dict({type(v).__name__})"))
                continue
            for key in _REQUIRED_CALLABLE_KEYS[name]:
                if not callable(v.get(key)):
                    phantoms.append((k, f"no callable {key!r}"))
                    break
        else:  # tuple registry
            if not (isinstance(v, tuple) and len(v) == 2
                    and all(callable(x) for x in v)):
                phantoms.append((k, "not a 2-tuple of callables"))
    assert not phantoms, (
        f"{name} has phantom (non-renderable) entries: {phantoms[:10]}"
    )


def test_pattern_aliases_resolve_within_registry(registries):
    """Every PATTERN alias points at a target key that exists in the registry.

    Pattern aliases carry ``_spb_alias_of`` -> another pattern key. A dangling
    alias target is a phantom-group reference that would crash the picker. We
    derive the alias set and its targets from the registry itself; if there are
    no aliases in the current catalog the contract is vacuously satisfied (no
    skip needed -- absence of aliases is itself fine).
    """
    reg = _reg(registries, "PATTERN")
    aliases = {k: v.get("_spb_alias_of")
               for k, v in reg.items()
               if isinstance(v, dict) and "_spb_alias_of" in v}
    dangling = {k: tgt for k, tgt in aliases.items() if tgt not in reg}
    assert not dangling, (
        f"PATTERN has aliases whose target key does not exist: "
        f"{dict(list(dangling.items())[:10])}"
    )
    # An alias must not point at itself (that is a degenerate phantom loop).
    self_aliases = [k for k, tgt in aliases.items() if tgt == k]
    assert not self_aliases, f"PATTERN has self-referential aliases: {self_aliases[:10]}"


# ---------------------------------------------------------------------------
# anti-stub: a multi-entry registry must not alias one object everywhere
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_NAMES)
def test_registry_not_collapsed_to_single_object(registries, name):
    """A registry of many keys must not collapse to a single shared entry object.

    Many distinct keys all pointing at the *same* dict/tuple instance is a classic
    copy/paste stub bug. We allow some intentional aliasing but reject the
    degenerate case of one underlying object for the whole registry. Pure identity
    check -- no value comparison.
    """
    reg = _reg(registries, name)
    if len(reg) <= 1:
        return
    distinct = {id(v) for v in reg.values()}
    assert len(distinct) > 1, (
        f"{name}: all {len(reg)} entries alias one object (suspected stub bug)"
    )
