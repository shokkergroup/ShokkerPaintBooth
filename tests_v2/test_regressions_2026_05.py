"""
Permanent regression guards for bugs fixed in the 2026-05-29/30 hardening pass.

Source of truth for *why* each test exists:
  - SPB_RUNTIME_BUGHUNT.md          (the runtime bug-hunt triage)
  - SHIP_READY_PROGRESS.md          (the ship-ready progress log)

SCOPE (read this before adding tests here):
  This file holds ENGINE / UNIT-level guards only -- things provable by importing
  the engine and rendering spec/paint functions, with NO live server. Server-route
  regressions (the SERVERCORE-1 render-lock 429, the ROUTESB-1 serve-local-file
  path-traversal hole) are deliberately NOT duplicated here -- they live in
  tests_v2/test_server_contract.py. Keep that split so a fix is guarded in exactly
  one place.

DESIGN (matches tests_v2/README.md "test stable CONTRACTS, not churning DATA"):
  We never assert exact finish counts, exact IDs, exact membership, or exact
  pixel/M/R/CC values -- the catalog is under active rebuild and those flap daily.
  We assert invariants that hold regardless of catalog contents:
    * the previously-crashing small-size (64x64) render path no longer raises;
    * spec output is a finite ndarray of a contract-valid shape;
    * a spec_fn handed a (h, w, 3) work-shape tuple no longer blows up unpacking;
    * enforce_iron_rules keeps output finite and in-range.

  Renders are done at SMALL=64 on purpose: that is exactly the size class that the
  depth_*/halo_* MONO spec_fns used to crash at (production always renders >=256,
  so this is finish-neutral). We sample the 985-entry MONOLITHIC registry rather
  than rendering all of it, to keep the file fast (< ~90s).

CALLING CONVENTIONS (probed from the live engine 2026-05-30; baked in so the
  guards exercise the *real* render path rather than a guessed one):
    * MONOLITHIC_REGISTRY[id] == (spec_fn, paint_fn). spec_fn signature is
      (shape, mask=None, seed=0, ...): call spec_fn((h, w)) or spec_fn((h, w, 3)).
      Calling spec_fn(h, w, seed) positionally mis-binds mask=w (a scalar) and
      raises an IndexError WE caused -- so we must use the tuple convention.
    * BASE_REGISTRY[id] is a dict with base_spec_fn(shape, seed, sm, base_m,
      base_r): call base_spec_fn((h, w), seed, 1.0, M, R).
    * PATTERN_REGISTRY[id] is a dict with texture_fn(shape, mask, seed, sm); the
      sm argument convention is finicky across the rebuild, so the PATTERN guard
      treats a probe-signature exception as "skip", and only a value/index/unpack
      error from a correctly-shaped call as a real regression.
"""
import io
import contextlib

import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# Constants / tunables
# --------------------------------------------------------------------------- #
SMALL = 64          # the small-size that the depth_*/halo_* MONOs used to crash at
SEED = 7

# How many MONOLITHIC entries to render at SMALL size. Rendering all 985 at 64x64
# is unnecessary and slow; an evenly-spaced sample exercises the same shared
# monolithic-contract wrapper + the depth/halo work-shape helpers.
MONO_SAMPLE = 90

# The spec families that historically crashed at small sizes (the depth_* shape
# unpack bug + its halo_* twin). The MONO sample ALWAYS includes every member of
# these, not just whatever the even-stride sampling happens to hit.
CRASH_PRONE_PREFIXES = ("depth_", "halo_")


# --------------------------------------------------------------------------- #
# Small local helpers (kept self-contained so a regression guard does not break
# when conftest.py churns).
# --------------------------------------------------------------------------- #
def _quiet():
    """Silence the (very chatty) engine while rendering."""
    return contextlib.redirect_stdout(io.StringIO())


def _is_finite_valid_spec(arr):
    """
    True iff arr is a FINITE ndarray of a contract-valid spec shape:
    (H, W) or a 3-D array with a channel/plane axis of size >= 2, non-empty.

    Note on shape: raw engine spec layers come in a couple of layouts -- the MONO
    wrappers emit (H, W, C) (C is 3 or 4), while a BASE base_spec_fn emits a
    plane-first (P, H, W). We accept either by only requiring ndim in (2, 3) and a
    non-trivial size; we deliberately do NOT pin an exact channel count or axis
    order, which would flap as the rebuild changes layer composition. Finiteness,
    however, IS required -- the live engine was confirmed (2026-05-30) to emit
    finite raw output at 64x64 for the whole sampled set, so a NaN/inf here would
    be a real regression.
    """
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim not in (2, 3):
        return False
    if a.ndim == 3 and min(a.shape) < 2:
        return False
    if a.size == 0:
        return False
    return bool(np.isfinite(a).all())


# --------------------------------------------------------------------------- #
# Engine import (collection time). If it cannot be imported at all, every test in
# this file skips with a clear reason instead of erroring the whole tests_v2 run.
# --------------------------------------------------------------------------- #
def _import_engine():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import shokker_engine_v2 as s  # noqa: E402
    return s


try:
    _ENGINE = _import_engine()
    _IMPORT_ERR = None
except Exception as _e:  # pragma: no cover - only on a broken engine tree
    _ENGINE = None
    _IMPORT_ERR = _e

pytestmark = pytest.mark.skipif(
    _ENGINE is None,
    reason="shokker_engine_v2 failed to import: %r" % (_IMPORT_ERR,),
)


# --------------------------------------------------------------------------- #
# Registry sampling (all built at collection time, before any test references).
# --------------------------------------------------------------------------- #
def _mono_sample_keys(engine):
    """Every depth_*/halo_* MONO key + an evenly spaced sample of the rest."""
    if engine is None:
        return []
    reg = getattr(engine, "MONOLITHIC_REGISTRY", {}) or {}
    keys = list(reg.keys())
    if not keys:
        return []
    must = [
        k for k in keys
        if isinstance(k, str) and any(p in k for p in CRASH_PRONE_PREFIXES)
    ]
    must_set = set(must)
    rest = [k for k in keys if k not in must_set]
    budget = max(0, MONO_SAMPLE - len(must))
    if rest and budget:
        stride = max(1, len(rest) // budget)
        sampled = rest[::stride][:budget]
    else:
        sampled = []
    return must + sampled


def _even_sample(reg, n=30):
    keys = list(reg.keys())
    if not keys:
        return []
    stride = max(1, len(keys) // n)
    return keys[::stride][:n]


_MONO_KEYS = _mono_sample_keys(_ENGINE)
_BASE_KEYS = _even_sample(getattr(_ENGINE, "BASE_REGISTRY", {}) or {}) if _ENGINE else []
_PATTERN_KEYS = (
    _even_sample(getattr(_ENGINE, "PATTERN_REGISTRY", {}) or {}) if _ENGINE else []
)


# --------------------------------------------------------------------------- #
# Render helpers that use the engine's REAL calling conventions (probed live).
# Each returns the rendered array, or None if the convention genuinely did not
# apply to this entry (caller then skips -- a probe gap is never a failure).
# --------------------------------------------------------------------------- #
def _render_mono_spec(spec_fn, shape):
    """
    Render a MONOLITHIC spec_fn at the given shape tuple.

    [2026-07-08] The engine's live convention is spec_fn(shape, mask, seed, sm)
    (see shokker_engine_v2 monolithic render blocks); older generations carried
    defaults so the legacy single-arg probe worked. The 2026-06-21/22 color
    science rebuild generates closures WITHOUT defaults, so this probe now
    tries the legacy call first and falls back to the full engine convention —
    a TypeError on arity is a probe-convention gap, not a render regression.
    Any OTHER exception still propagates (real small-size regression).
    """
    import numpy as _np
    with _quiet():
        try:
            return spec_fn(shape)
        except TypeError as te:
            if "positional argument" not in str(te):
                raise
            h, w = int(shape[0]), int(shape[1])
            mask = _np.ones((h, w), dtype=_np.float32)
            return spec_fn(shape, mask, 51, 1.0)


def _render_base_spec(entry, shape, seed):
    """
    Render a BASE base_spec_fn(shape, seed, sm, base_m, base_r). Returns the
    array, or None if the entry has no base_spec_fn. Pulls base_m/base_r from the
    entry's M/R when present (falling back to engine defaults) so we feed the
    factory plausible material values rather than guesses.
    """
    if not isinstance(entry, dict):
        return None
    fn = entry.get("base_spec_fn")
    if not callable(fn):
        return None
    base_m = entry.get("M", 120)
    base_r = entry.get("R", 80)
    try:
        base_m = float(base_m)
    except (TypeError, ValueError):
        base_m = 120.0
    try:
        base_r = float(base_r)
    except (TypeError, ValueError):
        base_r = 80.0
    with _quiet():
        return fn(shape, seed, 1.0, base_m, base_r)


def _render_pattern_texture(entry, shape, seed):
    """
    Render a PATTERN texture_fn(shape, mask, seed, sm). Returns whatever the
    factory produces (probed 2026-05-30: usually a DICT of named layers, e.g.
    {'pattern_val': ndarray, 'M_pattern': ndarray, 'M_range': float, 'CC': ...},
    NOT a bare spec array), or None if there is no texture_fn or the sm-convention
    probe did not take.

    The sm argument convention varies across the rebuild; we try the common forms
    and treat a pure signature/argument-type rejection as "not applicable"
    (return None -> caller skips). A value/index/unpack error from a call that WAS
    accepted is a real small-size regression and propagates.
    """
    if not isinstance(entry, dict):
        return None
    fn = entry.get("texture_fn")
    if not callable(fn):
        return None
    for sm in (1.0, {}, None):
        try:
            with _quiet():
                return fn(shape, None, seed, sm)
        except TypeError:
            # Wrong sm convention for this factory -- try the next form.
            continue
    return None


def _iter_arrays(value):
    """
    Yield every ndarray buried in a texture_fn result, whatever its container:
    a bare array, a dict of layers (the common PATTERN shape), or a tuple/list of
    either. Scalars / None / strings are ignored. Lets the PATTERN guard validate
    the array layers without pinning the (rebuild-varying) dict schema.
    """
    if value is None:
        return
    if isinstance(value, np.ndarray):
        yield value
        return
    if isinstance(value, dict):
        for v in value.values():
            yield from _iter_arrays(v)
        return
    if isinstance(value, (tuple, list)):
        for v in value:
            yield from _iter_arrays(v)
        return
    if hasattr(value, "__array__"):
        yield np.asarray(value)


# --------------------------------------------------------------------------- #
# BUG 1 -- depth_*/MONO spec_fns crash at small sizes (64x64).
#
# Fixed 2026-05-29 (SHIP_READY_PROGRESS.md "depth_*/MONO crash at small sizes",
# task #7). 19 depth_* then 11 halo_* MONO spec_fns crashed below ~96px due to a
# bad shape unpack in fusions._depth_work_shape and the work!=out reconcile;
# hardened systemically by a fallback in the monolithic-contract wrapper in
# shokker_engine_v2.py that triggers only on the otherwise-crashing path.
#
# Guard: rendering a representative sample of MONOLITHIC spec fns -- with every
# depth_*/halo_* entry forcibly included -- at 64x64 must not raise, and must
# return a finite, contract-valid ndarray.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key", _MONO_KEYS, ids=[str(k) for k in _MONO_KEYS])
def test_monolithic_spec_fns_do_not_crash_at_64x64(key):
    """
    BUG (2026-05-29, SHIP_READY_PROGRESS.md task #7 / 'depth_*/MONO crash at
    small sizes'): depth_* and halo_* MONO spec_fns crashed at sizes < ~96px
    (shape-unpack in fusions._depth_work_shape + the work!=out reconcile), now
    also caught systemically by the monolithic-contract-wrapper fallback in
    shokker_engine_v2.py. Guards that the 64x64 path stays uncrashing for the
    whole MONOLITHIC family and that its output is finite + contract-shaped.
    """
    entry = _ENGINE.MONOLITHIC_REGISTRY[key]
    # MONO entries are (spec_fn, paint_fn) tuples; spec_fn is index 0.
    if not isinstance(entry, (tuple, list)) or not entry:
        pytest.skip("MONO entry %r is not the expected (spec_fn, paint_fn) tuple" % (key,))
    spec_fn = entry[0]
    if not callable(spec_fn):
        pytest.skip("MONO entry %r has no callable spec_fn" % (key,))

    # The fix itself: this call (engine's own convention) must NOT raise at 64x64.
    result = _render_mono_spec(spec_fn, (SMALL, SMALL))
    assert _is_finite_valid_spec(result), (
        "MONO %r spec_fn produced a non-finite / wrong-shape array at 64x64 "
        "(regression of the depth/halo small-size fix); shape=%r"
        % (key, getattr(np.asarray(result), "shape", None))
    )


def test_depth_and_halo_families_are_actually_covered():
    """
    Meta-guard for BUG 1 (2026-05-29): the specific families that crashed
    (depth_* / halo_*) must actually exist in MONOLITHIC_REGISTRY and be present
    in this file's sample, so the small-size guard truly exercises the fixed code
    path. If the rebuild renames/removes these families this xfails loudly rather
    than silently passing on an empty set. We assert NO exact count -- only that
    the family is non-empty and fully sampled.
    """
    reg = getattr(_ENGINE, "MONOLITHIC_REGISTRY", {}) or {}
    family = [
        k for k in reg.keys()
        if isinstance(k, str) and any(p in k for p in CRASH_PRONE_PREFIXES)
    ]
    if not family:
        pytest.xfail(
            "no depth_*/halo_* MONO entries currently present (catalog rebuild "
            "may have renamed them); the small-size guard then covers the wrapper "
            "fallback path only"
        )
    sample = set(_MONO_KEYS)
    missing = [k for k in family if k not in sample]
    assert not missing, (
        "depth_*/halo_* members not in the small-size sample: %r" % (missing[:10],)
    )


# --------------------------------------------------------------------------- #
# BUG 2 -- spec_fn must tolerate a (h, w, 3) shape *tuple* (the _depth_work_shape
# fix). Handing a spec_fn a 3-element work-shape tuple (h, w, 3) instead of a
# 2-tuple (h, w) used to crash on the unpack. Every MONO spec_fn (the engine
# calls them via a shape tuple) must accept a 3-tuple without an unpack/index
# error from inside its body.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key", _MONO_KEYS, ids=[str(k) for k in _MONO_KEYS])
def test_mono_spec_fn_tolerates_hw3_shape_tuple(key):
    """
    BUG (2026-05-29, the fusions._depth_work_shape fix): handing a spec_fn a
    3-element work-shape tuple (h, w, 3) instead of a 2-tuple (h, w) used to crash
    on the unpack. Guards that every sampled MONO spec_fn accepts a (64, 64, 3)
    tuple at the small size without an unpack/index/value error and returns a
    finite, contract-valid array.
    """
    entry = _ENGINE.MONOLITHIC_REGISTRY[key]
    if not isinstance(entry, (tuple, list)) or not entry:
        pytest.skip("MONO entry %r is not the expected (spec_fn, paint_fn) tuple" % (key,))
    spec_fn = entry[0]
    if not callable(spec_fn):
        pytest.skip("MONO entry %r has no callable spec_fn" % (key,))

    result = _render_mono_spec(spec_fn, (SMALL, SMALL, 3))
    assert _is_finite_valid_spec(result), (
        "MONO %r spec_fn produced a non-finite / wrong-shape array from a "
        "(64,64,3) work-shape tuple (regression of the _depth_work_shape fix); "
        "shape=%r" % (key, getattr(np.asarray(result), "shape", None))
    )


# --------------------------------------------------------------------------- #
# BUG-CLASS 3 -- engine-level small-size + iron-safety invariants on BASE/PATTERN.
#
# Not a single dated bug, but the engine contract the 2026-05 pass hardened
# around: spec output rendered at the small size that used to crash must be
# finite and correctly shaped, and enforce_iron_rules must keep output finite +
# bounded. Keeps any future small-size regression from sneaking in via the
# BASE/PATTERN factories too.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key", _BASE_KEYS, ids=[str(k) for k in _BASE_KEYS])
def test_base_spec_fns_finite_at_64x64(key):
    """
    Engine contract (hardened in the 2026-05-29/30 pass): a sampled BASE
    base_spec_fn rendered at the 64x64 small-size path produces a finite,
    contract-valid ndarray and never raises. Guards the same small-size code path
    as BUG 1 from the BASE side.
    """
    entry = _ENGINE.BASE_REGISTRY[key]
    result = _render_base_spec(entry, (SMALL, SMALL), SEED)
    if result is None:
        pytest.skip("BASE entry %r has no base_spec_fn to render" % (key,))
    assert _is_finite_valid_spec(result), (
        "BASE %r base_spec_fn produced a non-finite / wrong-shape array at 64x64; "
        "shape=%r" % (key, getattr(np.asarray(result), "shape", None))
    )


@pytest.mark.parametrize("key", _PATTERN_KEYS, ids=[str(k) for k in _PATTERN_KEYS])
def test_pattern_texture_fns_finite_at_64x64(key):
    """
    Engine contract (hardened in the 2026-05-29/30 pass): a sampled PATTERN
    texture_fn rendered at the 64x64 small-size path produces FINITE layer arrays
    and never raises. texture_fn returns a DICT of named layers (pattern_val,
    M_pattern, ...) plus scalar metadata, not a single spec array (probed
    2026-05-30), so we validate every ndarray layer it produced rather than the
    container shape -- which keeps the guard stable as the rebuild changes the
    dict schema. The sm convention varies, so an entry the probe can't drive is
    skipped (probe gap, not a failure); an entry we DO render must yield at least
    one finite array layer at the small size.
    """
    entry = _ENGINE.PATTERN_REGISTRY[key]
    result = _render_pattern_texture(entry, (SMALL, SMALL), SEED)
    if result is None:
        pytest.skip(
            "PATTERN entry %r texture_fn convention not matched by the probe" % (key,)
        )
    arrays = [a for a in _iter_arrays(result) if a.size > 0]
    if not arrays:
        pytest.skip(
            "PATTERN entry %r texture_fn produced no array layers to validate" % (key,)
        )
    for a in arrays:
        assert np.isfinite(np.asarray(a, dtype=np.float32)).all(), (
            "PATTERN %r texture_fn produced a NON-FINITE layer array at 64x64 "
            "(shape=%r) -- a real small-size regression" % (key, a.shape)
        )


def _load_engine_core():
    """
    Import the engine.core package module, where enforce_iron_rules + the iron
    constants live (probed 2026-05-30: engine/core.py). enforce_iron_rules is NOT
    an attribute of the shokker_engine_v2 facade, so we import the package module
    directly. Returns the module, or None if it cannot be imported.
    """
    try:
        with _quiet():
            from engine import core as _engine_core
        return _engine_core
    except Exception:
        return None


def test_enforce_iron_rules_applies_cc_and_roughness_floors():
    """
    Engine iron-safety contract (the last-line guarantee the 2026-05-29/30
    hardening leans on): enforce_iron_rules (engine.core) raises every spec pixel
    to the iron floors -- clearcoat CC up to SPEC_CLEARCOAT_MIN (where CC>0) and,
    for NON-chrome pixels (M < SPEC_METALLIC_CHROME_THRESHOLD), roughness R up to
    SPEC_ROUGHNESS_MIN. If this floor ever stops applying, the small-size renders
    guarded above could ship below-floor specs.

    Probed real behavior 2026-05-30: signature enforce_iron_rules(spec) on an
    (H, W, 4) uint8 (M, R, CC, A) array, in place. We assert the INVARIANT using
    the engine's OWN constants (so a future retune of the floor values keeps the
    test correct), never hardcoded pixel numbers.
    """
    core = _load_engine_core()
    if core is None or not callable(getattr(core, "enforce_iron_rules", None)):
        pytest.xfail(
            "engine.core.enforce_iron_rules not importable (engine/catalog "
            "rebuild may have moved it)"
        )
    enforce = core.enforce_iron_rules
    cc_min = int(getattr(core, "SPEC_CLEARCOAT_MIN"))
    r_min = int(getattr(core, "SPEC_ROUGHNESS_MIN"))
    chrome_thr = int(getattr(core, "SPEC_METALLIC_CHROME_THRESHOLD"))

    h = w = 8
    bad_r = max(0, r_min - 5)
    bad_cc = max(1, cc_min - 5)  # >0 so the CC floor must engage
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = max(0, chrome_thr - 50)   # M: non-chrome
    spec[:, :, 1] = bad_r                      # R: below floor
    spec[:, :, 2] = bad_cc                     # CC: >0, below floor
    spec[:, :, 3] = 255                         # A

    with _quiet():
        out = np.asarray(enforce(spec.copy()))
    assert out.shape == (h, w, 4), (
        "enforce_iron_rules changed the spec shape: %r" % (out.shape,)
    )
    assert int(out[:, :, 1].min()) >= r_min, (
        "enforce_iron_rules did NOT raise non-chrome roughness to the floor "
        "(R min %d < SPEC_ROUGHNESS_MIN %d)" % (int(out[:, :, 1].min()), r_min)
    )
    assert int(out[:, :, 2].min()) >= cc_min, (
        "enforce_iron_rules did NOT raise clearcoat to the floor "
        "(CC min %d < SPEC_CLEARCOAT_MIN %d)" % (int(out[:, :, 2].min()), cc_min)
    )


def test_enforce_iron_rules_exempts_chrome_from_roughness_floor():
    """
    Engine iron-safety contract (complement of the floor test): chrome pixels
    (M >= SPEC_METALLIC_CHROME_THRESHOLD) are intentionally EXEMPT from the
    roughness floor -- chrome must keep its near-zero roughness for a mirror
    finish. Guards that enforce_iron_rules does not over-correct chrome, which
    would dull every mirror finish. Probed real behavior 2026-05-30.
    """
    core = _load_engine_core()
    if core is None or not callable(getattr(core, "enforce_iron_rules", None)):
        pytest.xfail("engine.core.enforce_iron_rules not importable")
    enforce = core.enforce_iron_rules
    r_min = int(getattr(core, "SPEC_ROUGHNESS_MIN"))
    chrome_thr = int(getattr(core, "SPEC_METALLIC_CHROME_THRESHOLD"))

    low_r = max(0, r_min - 10)
    spec = np.zeros((8, 8, 4), dtype=np.uint8)
    spec[:, :, 0] = min(255, chrome_thr + 50)  # M: chrome
    spec[:, :, 1] = low_r                        # R: below the non-chrome floor
    spec[:, :, 2] = 0                            # CC: 0 -> CC floor does not apply
    spec[:, :, 3] = 255

    with _quiet():
        out = np.asarray(enforce(spec.copy()))
    assert int(out[:, :, 1].max()) <= low_r, (
        "enforce_iron_rules wrongly applied the roughness floor to CHROME pixels "
        "(R %d raised above the input %d) -- chrome must stay mirror-smooth"
        % (int(out[:, :, 1].max()), low_r)
    )


def test_registries_are_dicts_and_nonempty():
    """
    Smoke invariant for the whole file: the primary registries load as non-empty
    containers. We assert NO exact counts (the catalog is under active rebuild) --
    only that the engine populated them, so the parametrized guards above run
    against real data and are not silently empty.
    """
    base = getattr(_ENGINE, "BASE_REGISTRY", None)
    pattern = getattr(_ENGINE, "PATTERN_REGISTRY", None)
    mono = getattr(_ENGINE, "MONOLITHIC_REGISTRY", None)
    for name, reg in (("BASE_REGISTRY", base), ("PATTERN_REGISTRY", pattern),
                      ("MONOLITHIC_REGISTRY", mono)):
        assert isinstance(reg, dict), "%s is not a dict: %r" % (name, type(reg))
        assert len(reg) > 0, "%s is empty -- engine did not populate it" % (name,)
