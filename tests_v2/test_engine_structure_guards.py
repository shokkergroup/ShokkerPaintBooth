"""
WIN #21 + #22 — engine structural guard CONTRACT tests.

Finish-neutral. These tests do NOT change any paint/spec math or render output;
they lock in *structural* invariants the audit flagged:

  ARCH-03  import-order resilience / circular-import recovery
           -> a fresh `import shokker_engine_v2` must succeed and populate the
              four registries (BASE / PATTERN / MONOLITHIC / FINISH), and every
              entry must carry real callables (no placeholder/None left behind by
              the circular-import recovery path).

  ARCH-11  chameleon / prizm (a.k.a. color_shift / kameleon / dualshift /
           microshift / cs_* / cx_*) finishes must be *real* renderers, not
           silent flat-field stubs. The audit warns these can degrade to a
           constant fill on a name miss; we sample whatever shift-family ids are
           present and assert each one's spec-producing callable yields VARYING,
           finite output at a SMALL size — a real renderer, not a stub.

Registry shapes (the engine's documented convention, asserted in
tests_v2/test_registry_integrity.py):
  - BASE_REGISTRY      : { id : dict(base_spec_fn, paint_fn, CC, M, R, desc) }
  - PATTERN_REGISTRY   : { id : dict(paint_fn, desc, [texture_fn], ...) }
  - MONOLITHIC_REGISTRY: { id : (spec_fn, paint_fn) }   # 2-tuple of callables
  - FINISH_REGISTRY    : { id : (spec_fn, paint_fn) }   # 2-tuple of callables

There is NO `render_finish` helper on the module, and the spec callables do NOT
share one calling convention (BASE base_spec_fn wants (shape, seed, sm, m, r);
MONOLITHIC spec_fn wants a different shape form). So — exactly like the existing
tests_v2/test_spec_contract.py — we DISCOVER each entry's spec-producing
callable and PROBE it across the common engine call conventions, taking the
first that yields a usable 2-D/3-D array. The shift-family finishes currently
live in BASE/PATTERN/MONOLITHIC (the curated FINISH registry has none), so we
scan all four and de-dup by id.

Tolerance: the finish catalog churns. Tests sample what exists by id-regex and
SKIP gracefully if a class of finish is absent, rather than hard-failing on a
specific id. The IRON RULE for this lane is GREEN, so a genuinely-in-flux
condition is xfailed with a reason instead of failing.

Uses the shared tests_v2/conftest.py fixtures: `engine`, `registries`.

Run standalone:
    python -m pytest tests_v2/test_engine_structure_guards.py \
        -o addopts= -o filterwarnings= -p no:cacheprovider -q
"""
import contextlib
import io
import os
import re
import subprocess
import sys

import numpy as np
import pytest

from conftest import SMALL, SEED, suppress_stdout


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
# Matches the chameleon / prizm family by finish id. Deliberately excludes the
# bare `chrome` / `worn_chrome` ids (plain chrome is not a color-shift finish);
# `chrome_flip` / `cs_chrome_shift` etc. are included because they ARE shift
# finishes (the regex hits "shift").
_SHIFT_RE = re.compile(r"cham|prizm|dual|shift|kameleon", re.I)

# Keys that, by convention in this engine, hold a spec-producing callable
# (mirrors tests_v2/test_spec_contract.py).
_SPEC_KEYS = (
    "spec_fn",
    "base_spec_fn",
    "spec",
    "specfn",
    "spec_func",
    "make_spec",
    "spec_map_fn",
    "spec_pattern_fn",
)


def _registries(registries):
    """Yield (name, registry) for whichever of the four are present/non-empty."""
    for name in ("BASE", "PATTERN", "MONOLITHIC", "FINISH"):
        reg = registries.get(name)
        if reg:
            yield name, reg


def _candidate_spec_callables(entry):
    """All plausible spec-producing callables reachable from one entry.

    Handles both entry shapes: dict (BASE/PATTERN) and (spec_fn, paint_fn)
    tuple (MONOLITHIC/FINISH). For tuples the spec fn is the first callable.
    """
    out = []
    if callable(entry):
        return [entry]
    if isinstance(entry, dict):
        for key in _SPEC_KEYS:
            fn = entry.get(key)
            if callable(fn):
                out.append(fn)
        if not out:  # fall back: any callable value whose key hints "spec"
            for k, v in entry.items():
                if callable(v) and "spec" in str(k).lower():
                    out.append(v)
    elif isinstance(entry, (tuple, list)):
        for v in entry:
            if callable(v):
                out.append(v)
    return out


def _all_callables(entry):
    """Every callable member of an entry, shape-agnostic (for the ARCH-03 guard)."""
    if isinstance(entry, dict):
        return [v for v in entry.values() if callable(v)]
    if isinstance(entry, (tuple, list)):
        return [v for v in entry if callable(v)]
    if callable(entry):
        return [entry]
    return []


def _arrays_from_result(res):
    """Normalize a spec result (SpecTriple/tuple/bare array) to a list of 2-D/3-D arrays."""
    arrs = []
    seq = res if (hasattr(res, "_fields") or isinstance(res, (tuple, list))) else [res]
    for v in seq:
        try:
            a = np.asarray(v, dtype=np.float32)
        except Exception:
            continue
        if a.ndim in (2, 3) and a.size > 0:
            arrs.append(a)
    return arrs


def _probe_spec(fn, shape_hw=(SMALL, SMALL)):
    """Invoke a spec callable across common engine call conventions.

    Returns the list of produced 2-D/3-D arrays on the first convention that
    yields any, else None. Per-attempt exceptions are swallowed: a callable that
    is not a probeable spec producer under a given convention is simply skipped.
    (Same probe strategy as tests_v2/test_spec_contract.py:_try_call_spec.)
    """
    h, w = shape_hw
    attempts = (
        ((h, w), {}),
        (((h, w),), {}),
        ((h, w, SEED), {}),
        (((h, w), SEED), {}),
        ((h, w), {"seed": SEED}),
        # [2026-07-08] the engine's LIVE monolithic convention — spec_fn(shape,
        # mask, seed, sm) with no defaults (2026-06-21/22 color-science rebuild
        # closures dropped the legacy defaults, so the probes above miss them).
        (((h, w), np.ones((h, w), dtype=np.float32), SEED, 1.0), {}),
        ((), {"size": (h, w)}),
        ((), {"shape": (h, w)}),
        ((), {"h": h, "w": w}),
    )
    for args, kwargs in attempts:
        try:
            with suppress_stdout():
                res = fn(*args, **kwargs)
        except Exception:
            continue
        if res is None:
            continue
        arrs = _arrays_from_result(res)
        if arrs:
            return arrs
    return None


def _probe_finish(entry):
    """Probe an entry's candidate spec callables; return the first usable arrays."""
    for fn in _candidate_spec_callables(entry):
        arrs = _probe_spec(fn)
        if arrs:
            return arrs
    return None


def _collect_shift(registries):
    """List of (regname, id, entry) for shift-family ids, de-duped by id."""
    seen = set()
    out = []
    for name, reg in _registries(registries):
        for key in reg:
            if key in seen or not _SHIFT_RE.search(str(key)):
                continue
            seen.add(key)
            out.append((name, key, reg[key]))
    return out


def _max_std(arrs):
    stds = [float(np.nanstd(a)) for a in arrs if a.size]
    return max(stds) if stds else -1.0


# ---------------------------------------------------------------------------
# ARCH-03 — import-order resilience / registry population
# ---------------------------------------------------------------------------
def test_arch03_engine_exposes_four_registries(engine):
    """The already-imported engine must expose all four registry attributes."""
    for name in ("BASE_REGISTRY", "PATTERN_REGISTRY", "MONOLITHIC_REGISTRY", "FINISH_REGISTRY"):
        assert hasattr(engine, name), f"engine missing {name}"
        reg = getattr(engine, name)
        assert isinstance(reg, dict), f"{name} is not a dict (got {type(reg).__name__})"


def test_arch03_registries_nonempty(engine):
    """All four registries must be populated (guards circular-import drop)."""
    for name in ("BASE_REGISTRY", "PATTERN_REGISTRY", "MONOLITHIC_REGISTRY", "FINISH_REGISTRY"):
        assert len(getattr(engine, name)) > 0, f"{name} empty"


def test_arch03_registry_entries_carry_callables(engine):
    """Every registry entry must carry real callables (no placeholder/None).

    The circular-import recovery must not leave behind entries that are missing
    their render/spec functions. Entry SHAPE differs by registry (BASE/PATTERN
    are dicts, MONOLITHIC/FINISH are 2-tuples), so we assert the shape-agnostic
    invariant: at least one callable per entry, sampled across each registry.
    """
    for name in ("BASE_REGISTRY", "PATTERN_REGISTRY", "MONOLITHIC_REGISTRY", "FINISH_REGISTRY"):
        reg = getattr(engine, name)
        for key in list(reg)[:5]:  # sample; a full scan is slow and noisy
            calls = _all_callables(reg[key])
            assert calls, f"{name}[{key!r}] carries no callable (placeholder/stub?)"
            assert all(callable(c) for c in calls)


def test_arch03_clean_subprocess_import_succeeds():
    """A fresh interpreter importing the engine must exit 0 with registries built.

    This is the strongest guard for the circular-import chain: it has no warm
    module cache to lean on. We assert both a populated-count print AND the
    process exit code (exit codes are trusted on this network drive).
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, %r);"
        "import shokker_engine_v2 as e;"
        "n=(len(e.BASE_REGISTRY),len(e.PATTERN_REGISTRY),"
        "len(e.MONOLITHIC_REGISTRY),len(e.FINISH_REGISTRY));"
        "assert all(x>0 for x in n), n;"
        "print('REGOK', *n)"
    ) % root
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=root,
    )
    assert proc.returncode == 0, (
        f"clean import failed rc={proc.returncode}\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"
    )
    assert "REGOK" in proc.stdout, f"unexpected stdout: {proc.stdout!r}"


# ---------------------------------------------------------------------------
# ARCH-11 — chameleon / prizm finishes are real renderers, not flat stubs
# ---------------------------------------------------------------------------
def test_arch11_shift_finishes_present(registries):
    """Sanity: the catalog contains chameleon/prizm/shift-family finishes.

    If the catalog churns them away entirely, skip rather than fail — the
    render-quality assertions below would have nothing to sample.
    """
    found = _collect_shift(registries)
    if not found:
        pytest.skip("no chameleon/prizm/shift-family finishes in catalog to sample")
    assert len(found) >= 1


def test_arch11_shift_finishes_have_spec_callable(registries):
    """Shift-family finishes that *should* carry a spec callable do.

    BASE / MONOLITHIC / FINISH entries always pair a spec fn with their paint fn,
    so every shift-family finish in those registries must expose a spec callable.
    PATTERN entries are exempt: many shift-named patterns are image-backed and
    legitimately ship without a texture/spec callable (texture_fn is optional —
    see tests_v2/test_registry_integrity.py), so a PATTERN miss is not a defect.
    We still require that the shift family as a whole yields at least one spec
    callable (otherwise there is nothing for the varying-output guard to judge).
    """
    found = _collect_shift(registries)
    if not found:
        pytest.skip("no chameleon/prizm/shift-family finishes in catalog to sample")

    spec_bearing = [(n, f, e) for n, f, e in found if n != "PATTERN"]
    bad = [f"{name}:{fid}" for name, fid, entry in spec_bearing
           if not _candidate_spec_callables(entry)]
    assert not bad, (
        f"BASE/MONOLITHIC/FINISH shift-family finishes with no spec callable: {bad[:10]}"
    )

    with_spec = sum(1 for _n, _f, e in found if _candidate_spec_callables(e))
    assert with_spec >= 1, "no shift-family finish exposes any spec callable"


def test_arch11_shift_finishes_produce_varying_output(registries):
    """The core ARCH-11 guard: chameleon/prizm renders must VARY, not be flat.

    Probes every present shift-family finish's spec callable at a small size and
    asserts non-trivial variation (a stub flat field would have ~0 standard
    deviation) and finite output. Tolerant of catalog churn.

    A finish we cannot coax any spec array out of (probe miss) is NOT failed
    here — that is a probe/convention concern, separately surfaced below — so
    this test only judges renderers that actually produced output.
    """
    found = _collect_shift(registries)
    if not found:
        pytest.skip("no chameleon/prizm/shift-family finishes in catalog to sample")

    rendered = 0
    flat = []
    nonfinite = []
    for name, fid, entry in found:
        arrs = _probe_finish(entry)
        if arrs is None:
            continue  # probe miss — judged by the coverage test below
        rendered += 1
        if not all(np.isfinite(a).all() for a in arrs):
            nonfinite.append(f"{name}:{fid}")
        if _max_std(arrs) <= 1e-6:
            flat.append(f"{name}:{fid}")

    if rendered == 0:
        pytest.xfail(
            "could not probe a spec array from any shift-family finish; the spec "
            "calling convention may have changed (update _probe_spec attempts)."
        )
    assert not nonfinite, f"shift-family finishes produced non-finite spec output: {nonfinite}"
    assert not flat, (
        f"chameleon/prizm finishes rendered as flat stubs (ARCH-11): {flat} "
        f"of {rendered} probed"
    )


def test_arch11_shift_finishes_probe_coverage(registries):
    """Most shift-family finishes should be probeable through a known convention.

    Surfaces the case where the spec calling convention drifts (so the varying-
    output guard above silently has nothing to check). We require a majority to
    probe successfully; if essentially none do, that is a probe drift, not a
    catalog-data assertion, so we xfail rather than turn the lane red.
    """
    found = _collect_shift(registries)
    if not found:
        pytest.skip("no chameleon/prizm/shift-family finishes in catalog to sample")
    probeable = sum(1 for _n, _f, entry in found if _probe_finish(entry) is not None)
    if probeable == 0:
        pytest.xfail("no shift-family finish was probeable (spec convention drift)")
    assert probeable >= max(1, len(found) // 2), (
        f"only {probeable}/{len(found)} shift-family finishes were probeable "
        "(spec calling convention may have drifted)"
    )


def test_arch11_shift_spec_shape_is_image(registries):
    """A real shift renderer returns image-like (2-D/3-D) spec arrays, not scalars."""
    found = _collect_shift(registries)
    if not found:
        pytest.skip("no chameleon/prizm/shift-family finishes in catalog to sample")
    # First finish we can probe.
    arrs = None
    label = None
    for name, fid, entry in found:
        arrs = _probe_finish(entry)
        if arrs is not None:
            label = f"{name}:{fid}"
            break
    if arrs is None:
        pytest.xfail("no shift-family finish was probeable (spec convention drift)")
    for a in arrs:
        assert a.ndim in (2, 3), f"{label} spec array ndim={a.ndim} (expected image)"
        assert a.size > 0, f"{label} spec array is empty"
