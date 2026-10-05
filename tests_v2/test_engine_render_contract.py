"""
test_engine_render_contract.py -- the suite's backbone.

THE CONTRACT under test: "everything renders without crashing."

A representative SAMPLE of every registry kind -- BASE_REGISTRY (~518),
PATTERN_REGISTRY (~617), MONOLITHIC_REGISTRY (~985) -- must render at the
SMALL (64) contract size (and a couple at a mid size, 256) WITHOUT raising,
and each result must be a *finite* ndarray of the expected rank. SMALL=64 also
exercises the small-size code path that crashed before the 2026-05 hardening.

HOW EACH KIND IS INVOKED
------------------------
Probed directly from the live engine and mirrored from the canonical caller
server_routes/finish_viewer_render_routes.py (+ its spec_result_support helper
invoke_monolithic_spec_fn). The engine has NO single render_finish entry point;
each registry kind has its own entry shape and call convention:

  * MONOLITHIC_REGISTRY[id]  ->  a TUPLE (spec_fn, paint_fn)
        spec : invoke_monolithic_spec_fn(spec_fn, shape, mask, seed, sm)
               (the MONOLITHIC contract wrapper -- (shape, mask, seed, sm),
               with legacy-signature fallbacks)         -> spec map
        paint: paint_fn(paint, shape, mask, seed, 1.0, 0.10)     -> (H,W,3)

  * BASE_REGISTRY[id]        ->  a DICT with base_spec_fn + paint_fn
        spec : base_spec_fn(shape, seed, intensity, M, R)   (signature varies
               across entries; we fall back through legacy forms)  -> spec map
        paint: paint_fn(paint, shape, mask, seed, 1.0, 0.0)     -> (H,W,4)

  * PATTERN_REGISTRY[id]     ->  a DICT with texture_fn + paint_fn
        texture: texture_fn(shape, mask, seed, intensity)   -> dict or array
        paint  : paint_fn(paint, shape, mask, seed, 0.75, 0.0)  -> (H,W,3)

  where shape = (size, size) and mask = np.ones(shape, float32), exactly as the
  render route builds them.

STABLE-CONTRACT DISCIPLINE (see tests_v2/README.md)
---------------------------------------------------
We assert ONLY invariants that hold regardless of catalog contents: renders
without crashing, output is finite, and the rank/spatial-shape is right. We do
NOT assert exact counts, IDs, membership, or pixel/M/R/CC values (those flap
daily as the catalog is rebuilt). The sample is parametrized by finish id so a
single broken finish is named in the failing test id.
"""
from __future__ import annotations

import contextlib
import io

import numpy as np
import pytest

# conftest is the sibling module; import its constants/helpers so parametrize
# id lists can be built at collection time.
from conftest import SMALL, SEED, is_valid_spec  # noqa: E402

MID = 256  # a mid render size to prove size-independence on a few entries

# Sample sizes: chosen so a 64-px sweep stays fast (measured ~5s/80 monolithics,
# <1s/60 bases, ~1.5s/60 patterns) while striding the whole id-space (every Nth).
_N_MONO = 80
_N_BASE = 60
_N_PATTERN = 60


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _suppressed():
    """Silence the chatty engine during a render call."""
    return contextlib.redirect_stdout(io.StringIO())


def _sample(keys, n):
    """Deterministic representative sample: every Nth key (insertion order), capped at n."""
    keys = list(keys)
    if len(keys) <= n:
        return keys
    step = max(1, len(keys) // n)
    return keys[::step][:n]


def _shape_mask(size):
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    return shape, mask


def _invoke_monolithic_spec_fn(spec_fn, shape, mask, seed, intensity):
    """The MONOLITHIC spec contract wrapper: (shape, mask, seed, sm) with fallbacks.

    Mirrors server_routes/spec_result_support.invoke_monolithic_spec_fn so this
    test exercises the exact call path the server uses.
    """
    for args in ((shape, mask, seed, intensity), (shape, mask, seed), (shape, seed), (shape,)):
        try:
            return spec_fn(*args)
        except TypeError:
            continue
    return spec_fn(shape)


def _invoke_base_spec_fn(spec_fn, shape, seed, intensity, m_val, r_val):
    """Invoke a base base_spec_fn across the several signatures present in the catalog.

    Observed forms (probed): the dominant (shape, seed, intensity, base_m, base_r),
    plus legacy (shape, mask, seed, intensity) and (shape, seed) variants. We try
    the richest signature first, then degrade -- same robustness strategy the
    monolithic wrapper uses.
    """
    mask = np.ones(shape, dtype=np.float32)
    candidates = (
        (shape, seed, intensity, m_val, r_val),
        (shape, seed, intensity),
        (shape, mask, seed, intensity),
        (shape, mask, seed),
        (shape, seed),
        (shape,),
    )
    last_exc = None
    for args in candidates:
        try:
            return spec_fn(*args)
        except TypeError as ex:
            last_exc = ex
            continue
    # If nothing matched a TypeError chain, re-raise the last to surface a real bug.
    raise last_exc if last_exc is not None else RuntimeError("base_spec_fn uncallable")


def _spec_paint_from_entry(entry):
    """Extract (spec_fn, paint_fn) from a monolithic entry (tuple or dict).

    Mirrors finish_viewer_render_routes._entry_spec_paint.
    """
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        return entry[0], entry[1]
    if isinstance(entry, dict):
        return entry.get("spec_fn"), entry.get("paint_fn")
    if callable(entry):
        return None, entry
    return None, None


# --------------------------------------------------------------------------- #
# Collection-time id lists
# --------------------------------------------------------------------------- #
def _reg(name):
    """Import the engine once (stdout-suppressed) and return one registry."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import shokker_engine_v2 as s  # noqa: E402
    return getattr(s, name, {}) or {}


def _collect_ids():
    """Build per-kind sampled id lists for parametrize. Defensive at collection time."""
    try:
        base = _reg("BASE_REGISTRY")
        pattern = _reg("PATTERN_REGISTRY")
        mono = _reg("MONOLITHIC_REGISTRY")
    except Exception:  # pragma: no cover - import guard
        return [], [], [], []

    base_ids = _sample(base.keys(), _N_BASE)
    pattern_ids = _sample(pattern.keys(), _N_PATTERN)
    mono_ids = _sample(mono.keys(), _N_MONO)

    # Fold in curated masterclass refs if the engine exposes them (optional --
    # not all builds define MASTERCLASS_REFS; absence must not break collection).
    import shokker_engine_v2 as s  # already imported above, cheap
    refs = getattr(s, "MASTERCLASS_REFS", None) or []
    seen = set(mono_ids)
    for r in refs:
        if r in mono and r not in seen:
            mono_ids.append(r)
            seen.add(r)

    # Mid-size: a small handful of monolithics + a couple of bases.
    mid_mono = mono_ids[:3]
    mid_base = base_ids[:2]
    return base_ids, pattern_ids, mono_ids, (mid_mono, mid_base)


_BASE_IDS, _PATTERN_IDS, _MONO_IDS, (_MID_MONO_IDS, _MID_BASE_IDS) = _collect_ids()


# --------------------------------------------------------------------------- #
# Assertion helper
# --------------------------------------------------------------------------- #
def _assert_finite_paint(arr, finish_id, *, size):
    """Assert `arr` is a finite paint image: (size, size, C>=3), channels-last.

    Paint images are always channels-last (H,W,C) -- this is the literal preview
    the render route encodes to PNG.
    """
    assert arr is not None, f"{finish_id}: paint render returned None"
    a = np.asarray(arr)
    assert a.size > 0, f"{finish_id}: paint render produced an empty array"
    assert a.ndim == 3, f"{finish_id}: expected rank-3 paint image, got ndim={a.ndim} shape={a.shape}"
    assert a.shape[2] >= 3, f"{finish_id}: expected >=3 channels, got shape={a.shape}"
    assert a.shape[0] == size and a.shape[1] == size, (
        f"{finish_id}: expected paint spatial dims ({size},{size}), got shape={a.shape}"
    )
    af = a.astype(np.float64, copy=False)
    assert np.isfinite(af).all(), (
        f"{finish_id}: paint contains non-finite values "
        f"(nan={int(np.isnan(af).sum())}, inf={int(np.isinf(af).sum())})"
    )


def _assert_finite_spec(arr, finish_id, *, size):
    """Assert `arr` is a finite spec map resolvable to the right spatial size.

    Spec contracts in this engine return several layouts, all of which
    normalize_spec_result_to_rgba accepts:
      * (H, W)            -- single-channel spec
      * (H, W, C>=3)      -- channels-LAST  (e.g. monolithics return (H,W,4))
      * (C, H, W), C in (3,4)  -- channels-FIRST (bases commonly return (2/3, H, W))
    We accept any of these and verify finiteness + that the spatial dims match.
    """
    assert arr is not None, f"{finish_id}: spec render returned None"
    a = np.asarray(arr)
    assert a.size > 0, f"{finish_id}: spec render produced an empty array"
    assert a.ndim in (2, 3), f"{finish_id}: spec must be 2D or 3D, got ndim={a.ndim} shape={a.shape}"

    if a.ndim == 2:
        h, w = a.shape
    else:
        # channels-last (H,W,C)?
        if a.shape[0] == size and a.shape[1] == size:
            h, w = a.shape[0], a.shape[1]
        # channels-first (C,H,W) with a small leading channel dim?
        elif a.shape[0] in (1, 2, 3, 4) and a.shape[1] == size and a.shape[2] == size:
            h, w = a.shape[1], a.shape[2]
        else:
            raise AssertionError(
                f"{finish_id}: spec shape {a.shape} not resolvable to ({size},{size}) "
                f"in channels-first or channels-last layout"
            )
    assert h == size and w == size, (
        f"{finish_id}: spec spatial dims ({h},{w}) != ({size},{size}); shape={a.shape}"
    )

    af = a.astype(np.float64, copy=False)
    assert np.isfinite(af).all(), (
        f"{finish_id}: spec contains non-finite values "
        f"(nan={int(np.isnan(af).sum())}, inf={int(np.isinf(af).sum())})"
    )


# --------------------------------------------------------------------------- #
# MONOLITHIC -- tuple (spec_fn, paint_fn)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _MONO_IDS, reason="MONOLITHIC_REGISTRY empty or engine unavailable at collection")
@pytest.mark.parametrize("mono_id", _MONO_IDS)
def test_monolithic_renders_small(engine, mono_id):
    """Each sampled monolithic renders (spec + paint) at SMALL without crashing; output finite."""
    entry = engine.MONOLITHIC_REGISTRY[mono_id]
    spec_fn, paint_fn = _spec_paint_from_entry(entry)
    assert callable(spec_fn), f"{mono_id}: monolithic entry has no callable spec_fn"
    assert callable(paint_fn), f"{mono_id}: monolithic entry has no callable paint_fn"

    shape, mask = _shape_mask(SMALL)
    paint_in = np.ones((SMALL, SMALL, 3), dtype=np.float32) * 0.5
    with _suppressed():
        spec = _invoke_monolithic_spec_fn(spec_fn, shape, mask, SEED, 1.0)
        painted = paint_fn(paint_in, shape, mask, SEED, 1.0, 0.10)

    _assert_finite_spec(spec, mono_id, size=SMALL)
    _assert_finite_paint(painted, mono_id, size=SMALL)


# --------------------------------------------------------------------------- #
# BASE -- dict base_spec_fn + paint_fn
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _BASE_IDS, reason="BASE_REGISTRY empty or engine unavailable at collection")
@pytest.mark.parametrize("base_id", _BASE_IDS)
def test_base_renders_small(engine, base_id):
    """Each sampled base renders (spec + paint) at SMALL without crashing; output finite."""
    entry = engine.BASE_REGISTRY[base_id]
    assert isinstance(entry, dict), f"{base_id}: base entry is not a dict"
    spec_fn = entry.get("base_spec_fn")
    paint_fn = entry.get("paint_fn")
    assert callable(spec_fn), f"{base_id}: base entry has no callable base_spec_fn"
    assert callable(paint_fn), f"{base_id}: base entry has no callable paint_fn"

    m_val = float(entry.get("M", 5))
    r_val = float(entry.get("R", 100))
    shape, mask = _shape_mask(SMALL)
    paint_in = np.zeros((SMALL, SMALL, 4), dtype=np.float32)
    with _suppressed():
        spec = _invoke_base_spec_fn(spec_fn, shape, SEED, 1.0, m_val, r_val)
        painted = paint_fn(paint_in, shape, mask, SEED, 1.0, 0.0)

    # base spec may be (H,W), (H,W,C) or channels-first (C,H,W) -- all valid.
    _assert_finite_spec(spec, base_id, size=SMALL)
    assert is_valid_spec(spec), f"{base_id}: base spec failed is_valid_spec"
    _assert_finite_paint(painted, base_id, size=SMALL)


# --------------------------------------------------------------------------- #
# PATTERN -- dict texture_fn + paint_fn
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _PATTERN_IDS, reason="PATTERN_REGISTRY empty or engine unavailable at collection")
@pytest.mark.parametrize("pattern_id", _PATTERN_IDS)
def test_pattern_renders_small(engine, pattern_id):
    """Each sampled pattern renders (texture + paint) at SMALL without crashing; output finite."""
    entry = engine.PATTERN_REGISTRY[pattern_id]
    assert isinstance(entry, dict), f"{pattern_id}: pattern entry is not a dict"
    paint_fn = entry.get("paint_fn")
    assert callable(paint_fn), f"{pattern_id}: pattern entry has no callable paint_fn"

    shape, mask = _shape_mask(SMALL)
    texture_fn = entry.get("texture_fn")
    paint_in = np.zeros((SMALL, SMALL, 4), dtype=np.float32)
    with _suppressed():
        if callable(texture_fn):
            tex = texture_fn(shape, mask, SEED, 1.0)
            # texture_fn returns either a dict of channel maps or a raw array;
            # if it's a raw array it must be finite. dict channels are validated
            # implicitly by the paint render below.
            if not isinstance(tex, dict) and tex is not None:
                _assert_finite_spec(tex, f"{pattern_id}(texture)", size=SMALL)
        painted = paint_fn(paint_in, shape, mask, SEED, 0.75, 0.0)

    _assert_finite_paint(painted, pattern_id, size=SMALL)


# --------------------------------------------------------------------------- #
# Mid size (256) -- prove size-independence on a small handful (not only 64).
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _MID_MONO_IDS, reason="MONOLITHIC_REGISTRY empty at collection")
@pytest.mark.parametrize("mono_id", _MID_MONO_IDS)
def test_monolithic_renders_mid(engine, mono_id):
    """A few monolithics also render cleanly at MID (256), not just at SMALL."""
    entry = engine.MONOLITHIC_REGISTRY[mono_id]
    spec_fn, paint_fn = _spec_paint_from_entry(entry)
    assert callable(spec_fn) and callable(paint_fn), f"{mono_id}: missing renderer fns"

    shape, mask = _shape_mask(MID)
    paint_in = np.ones((MID, MID, 3), dtype=np.float32) * 0.5
    with _suppressed():
        spec = _invoke_monolithic_spec_fn(spec_fn, shape, mask, SEED, 1.0)
        painted = paint_fn(paint_in, shape, mask, SEED, 1.0, 0.10)

    _assert_finite_spec(spec, mono_id, size=MID)
    _assert_finite_paint(painted, mono_id, size=MID)


@pytest.mark.skipif(not _MID_BASE_IDS, reason="BASE_REGISTRY empty at collection")
@pytest.mark.parametrize("base_id", _MID_BASE_IDS)
def test_base_renders_mid(engine, base_id):
    """A couple of bases also render cleanly at MID (256)."""
    entry = engine.BASE_REGISTRY[base_id]
    spec_fn = entry.get("base_spec_fn")
    paint_fn = entry.get("paint_fn")
    assert callable(spec_fn) and callable(paint_fn), f"{base_id}: missing renderer fns"

    m_val = float(entry.get("M", 5))
    r_val = float(entry.get("R", 100))
    shape, mask = _shape_mask(MID)
    paint_in = np.zeros((MID, MID, 4), dtype=np.float32)
    with _suppressed():
        spec = _invoke_base_spec_fn(spec_fn, shape, SEED, 1.0, m_val, r_val)
        painted = paint_fn(paint_in, shape, mask, SEED, 1.0, 0.0)

    _assert_finite_spec(spec, base_id, size=MID)
    _assert_finite_paint(painted, base_id, size=MID)


# --------------------------------------------------------------------------- #
# Determinism -- same id + same seed + same size -> identical bytes.
# A core render contract and a guard against accidental global-RNG-state leaks.
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _MONO_IDS, reason="MONOLITHIC_REGISTRY empty or engine unavailable at collection")
def test_monolithic_render_is_deterministic(engine):
    """A monolithic paint render is reproducible for a fixed (id, size, seed)."""
    mono_id = _MONO_IDS[0]
    _, paint_fn = _spec_paint_from_entry(engine.MONOLITHIC_REGISTRY[mono_id])
    assert callable(paint_fn), f"{mono_id}: no paint_fn"

    shape, mask = _shape_mask(SMALL)
    with _suppressed():
        a = np.asarray(paint_fn(np.ones((SMALL, SMALL, 3), np.float32) * 0.5, shape, mask, SEED, 1.0, 0.10))
        b = np.asarray(paint_fn(np.ones((SMALL, SMALL, 3), np.float32) * 0.5, shape, mask, SEED, 1.0, 0.10))
    assert a.shape == b.shape, f"{mono_id}: shape changed between identical renders"
    assert np.array_equal(a, b), f"{mono_id}: render not deterministic for fixed (size, seed)"


# --------------------------------------------------------------------------- #
# enforce_iron_rules is callable on a finite spec and returns a finite array.
# (Stable surface contract; we do NOT assert the exact clamped floors -- those
# are an engine invariant detail covered by test_spec_contract.)
# --------------------------------------------------------------------------- #
def _get_enforce_iron_rules(engine):
    """Resolve enforce_iron_rules from whichever surface exposes it.

    The canonical home is the engine.core module (`from engine.core import
    enforce_iron_rules`, as the render route does); some builds also re-export it
    on the top-level engine module. Try both.
    """
    fn = getattr(getattr(engine, "core", None), "enforce_iron_rules", None)
    if callable(fn):
        return fn
    fn = getattr(engine, "enforce_iron_rules", None)
    if callable(fn):
        return fn
    try:
        import importlib
        return importlib.import_module("engine.core").enforce_iron_rules
    except Exception:  # pragma: no cover - only if engine.core truly absent
        return None


def test_enforce_iron_rules_keeps_spec_finite(engine):
    """enforce_iron_rules accepts a spec, mutates it in place, leaves it finite, no crash.

    The engine contract is in-place (returns None) -- it clamps M/R/CC to the
    iron-safe floors. We only assert the stable surface contract: it runs without
    crashing and the spec stays finite. (Exact floor values are an engine
    invariant covered by test_spec_contract, per stable-contract discipline.)
    """
    enforce = _get_enforce_iron_rules(engine)
    assert callable(enforce), "enforce_iron_rules not importable from engine.core or engine"

    spec = np.zeros((SMALL, SMALL, 4), dtype=np.float32)
    spec[:, :, 1] = 100.0
    spec[:, :, 2] = 16.0
    spec[:, :, 3] = 255.0
    with _suppressed():
        ret = enforce(spec)  # in-place; conventionally returns None

    # If a build returns the array instead of mutating in place, validate that;
    # otherwise validate the (mutated) input. Either way it must stay finite.
    result = spec if ret is None else np.asarray(ret)
    assert result.size > 0, "enforce_iron_rules produced an empty spec"
    assert np.isfinite(result.astype(np.float64)).all(), (
        "enforce_iron_rules produced non-finite values"
    )
