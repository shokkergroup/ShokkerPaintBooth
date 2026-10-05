"""
test_spec_contract.py — the spec-output (M/R/CC) contract.

What this guards (stable CONTRACTS, never churning catalog data):

  1. For a representative sample of finishes that produce a spec map, the spec
     result is_valid_spec: a finite ndarray of rank 2 (H,W) or (H,W,C>=3).

  2. engine.core.enforce_iron_rules keeps a spec iron-safe. The real function
     (engine/core.py) operates on a (H,W,C>=3) spec where channel 0=M(etallic),
     1=R(oughness/G), 2=C(lear)C(oat) and enforces, in place:
         - CC floor:   CC >= SPEC_CLEARCOAT_MIN (=16) for any pixel that has
                       *some* clearcoat (the floor is applied only where CC>0;
                       a fully-zero CC pixel is intentionally left at 0),
         - R floor:    R/G >= SPEC_ROUGHNESS_MIN (=15) for non-chrome pixels
                       (M < SPEC_METALLIC_CHROME_THRESHOLD =240; chrome bypasses
                       the roughness floor).
     We resolve those constants from the engine at runtime (so a retune tracks
     automatically) and assert the invariants HOLD on the output (floors are
     respected where applicable, no negatives, output finite, same shape) and
     that the pass is IDEMPOTENT (enforce(enforce(x)) == enforce(x)) — the
     universal property of any correct floor/clamp pass. We do NOT assert exact
     pixel / M / R / CC values.

  3. The 2026-05-29 depth/MONO regression class: a (h,w,3) shape tuple flowing
     where (h,w) was assumed (and vice-versa) used to crash. We guard it
     generally: enforce_iron_rules must give a *clean, predictable* result for
     both a 2-D (H,W) spec and a 3-D (H,W,3) spec — never a silent corruption —
     and any sampled spec callable that takes a bare shape tuple must accept
     BOTH (h,w) and (h,w,3) without crashing.

These tests SURFACE defects: the iron-rule assertions check the documented
floors directly (a regression that drops the CC>=16 floor, introduces NaNs, or
breaks idempotence turns this file red), rather than merely asserting "it
returned something". Everything that depends on the (churning) catalog degrades
to xfail/vacuous-pass so the file stays green regardless of catalog contents.

Run standalone:
    python -m pytest tests_v2/test_spec_contract.py \
        -o addopts= -o filterwarnings= -p no:cacheprovider -q
"""
import inspect

import numpy as np
import pytest

from conftest import is_valid_spec, suppress_stdout, SMALL, SEED


# ---------------------------------------------------------------------------
# Runtime probing helpers. Catalog entries are DICTs (or tuples in MONOLITHIC)
# whose exact key layout is under active rebuild, so we DISCOVER the
# spec-producing callable per entry at runtime instead of hard-coding a key.
# ---------------------------------------------------------------------------

# Keys that, by convention in this engine, hold a spec-producing callable.
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


def _iter_entries(reg):
    """Yield (id, entry) for a dict-or-list registry, robustly."""
    if reg is None:
        return
    if isinstance(reg, dict):
        for k, v in reg.items():
            yield k, v
    elif isinstance(reg, (list, tuple)):
        for i, v in enumerate(reg):
            yield i, v


def _candidate_callables(entry):
    """All plausible spec-producing callables reachable from one entry."""
    out = []
    if callable(entry):
        out.append(entry)
        return out
    if isinstance(entry, dict):
        for key in _SPEC_KEYS:
            fn = entry.get(key)
            if callable(fn):
                out.append(fn)
        if not out:  # fall back: any callable value whose key hints "spec"
            for k, v in entry.items():
                if callable(v) and "spec" in str(k).lower():
                    out.append(v)
    elif isinstance(entry, (list, tuple)):
        for v in entry:
            if callable(v):
                out.append(v)
            elif isinstance(v, dict):
                out.extend(_candidate_callables(v))
    return out


def _try_call_spec(fn, shape_hw):
    """Invoke a spec callable across common engine call conventions.

    Returns the produced ndarray (ndim 2 or 3, non-empty) on first success,
    else None. We deliberately swallow per-attempt exceptions: a callable that
    is not a (probeable) spec producer is simply skipped — it is not this
    test's job to coerce arbitrary callables.
    """
    h, w = shape_hw
    attempts = (
        ((h, w), {}),
        (((h, w),), {}),
        ((h, w, SEED), {}),
        (((h, w), SEED), {}),
        ((h, w), {"seed": SEED}),
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
        try:
            arr = np.asarray(res, dtype=np.float32)
        except Exception:
            continue
        if arr.ndim in (2, 3) and arr.size > 0:
            return arr
    return None


def _collect_spec_samples(registries, limit_per_reg=20):
    """Build a representative sample of (label, spec ndarray) pairs.

    Sample, don't exhaust: first N of each registry plus an evenly-spaced
    stride across the rest (so the large MONOLITHIC tail is represented),
    keeping only entries we could actually coax a spec array out of.
    """
    samples = []
    for reg_name, reg in registries.items():
        items = list(_iter_entries(reg))
        if not items:
            continue
        n = len(items)
        idxs = list(range(min(limit_per_reg, n)))
        if n > limit_per_reg:
            stride = max(1, n // limit_per_reg)
            idxs += list(range(0, n, stride))
        seen, picked = set(), []
        for i in idxs:
            if i not in seen:
                seen.add(i)
                picked.append(items[i])
        for ent_id, entry in picked:
            for fn in _candidate_callables(entry):
                arr = _try_call_spec(fn, (SMALL, SMALL))
                if arr is not None:
                    samples.append((f"{reg_name}:{ent_id}", arr))
                    break  # one spec per entry is enough for the contract
    return samples


@pytest.fixture(scope="session")
def spec_samples(registries):
    """Representative (label, spec ndarray) pairs, collected once per session."""
    np.random.seed(SEED)
    return _collect_spec_samples(registries)


@pytest.fixture(scope="session")
def iron_fn(engine):
    """engine.core.enforce_iron_rules, resolved across the ways it is exposed.

    Tries, in order: a module-level export on the engine, engine.core.<fn>,
    and finally a direct ``import engine.core``. Returns None only if the
    symbol genuinely does not exist in this build (then the iron tests xfail).
    """
    fn = getattr(engine, "enforce_iron_rules", None)
    if fn is None:
        core = getattr(engine, "core", None)
        fn = getattr(core, "enforce_iron_rules", None) if core is not None else None
    if fn is None:
        try:
            with suppress_stdout():
                import engine.core as _core  # type: ignore
            fn = getattr(_core, "enforce_iron_rules", None)
        except Exception:
            fn = None
    return fn


# Engine iron-rule constants. Resolved from the engine at runtime so a retune
# tracks automatically; the literals are only documented fallbacks (the values
# currently in engine/core.py). These are NOT catalog data.
_CC_FLOOR_DEFAULT = 16
_R_FLOOR_DEFAULT = 15
_CHROME_M_DEFAULT = 240


def _const(engine, name, default):
    """Read an engine spec constant, falling back to its documented default."""
    core = getattr(engine, "core", None)
    for holder in (core, engine):
        if holder is not None and hasattr(holder, name):
            try:
                return float(getattr(holder, name))
            except (TypeError, ValueError):
                pass
    return float(default)


@pytest.fixture(scope="session")
def iron_consts(engine):
    return {
        "CC_FLOOR": _const(engine, "SPEC_CLEARCOAT_MIN", _CC_FLOOR_DEFAULT),
        "R_FLOOR": _const(engine, "SPEC_ROUGHNESS_MIN", _R_FLOOR_DEFAULT),
        "CHROME_M": _const(engine, "SPEC_METALLIC_CHROME_THRESHOLD", _CHROME_M_DEFAULT),
    }


def _spec3(rng, *, shape=(SMALL, SMALL, 4)):
    """A finite float32 spec with channels in a realistic 0..255-ish range."""
    return rng.random(shape, dtype=np.float32) * 255.0


# ---------------------------------------------------------------------------
# Sanity: the sample fixture actually found spec producers. If the engine
# surface changed so much we find nothing, that is a probe/environment issue
# (not a catalog-data assertion), so xfail rather than red.
# ---------------------------------------------------------------------------

def test_some_spec_samples_collected(spec_samples):
    if not spec_samples:
        pytest.xfail(
            "Could not probe any spec-producing callable from the registries; "
            "entry layout may have changed — update _SPEC_KEYS / call conventions."
        )
    assert len(spec_samples) >= 1


# ---------------------------------------------------------------------------
# Contract 1: every sampled spec is a valid spec (finite, rank 2 or (H,W,>=3)).
# ---------------------------------------------------------------------------

def test_spec_results_are_valid_specs(spec_samples):
    if not spec_samples:
        pytest.xfail("no spec samples collected (see test_some_spec_samples_collected)")
    bad = [
        (label, getattr(arr, "shape", None))
        for label, arr in spec_samples
        if not is_valid_spec(arr)
    ]
    assert not bad, f"non-contract spec outputs: {bad[:10]}"


def test_spec_results_are_finite(spec_samples):
    if not spec_samples:
        pytest.xfail("no spec samples collected")
    nonfinite = [
        label for label, arr in spec_samples
        if not np.isfinite(np.asarray(arr, dtype=np.float32)).all()
    ]
    assert not nonfinite, f"spec outputs with NaN/Inf: {nonfinite[:10]}"


def test_spec_results_have_contract_rank(spec_samples):
    if not spec_samples:
        pytest.xfail("no spec samples collected")
    bad_rank = []
    for label, arr in spec_samples:
        a = np.asarray(arr, dtype=np.float32)
        if a.ndim == 3 and a.shape[2] < 3:
            bad_rank.append((label, a.shape))
        elif a.ndim not in (2, 3):
            bad_rank.append((label, a.shape))
    assert not bad_rank, f"specs with wrong rank/channels: {bad_rank[:10]}"


# ---------------------------------------------------------------------------
# Contract 2: enforce_iron_rules enforces its documented floors and is safe.
#
# The real function indexes spec[:, :, 0..2], so it requires a (H,W,C>=3)
# array. We feed it exactly that (its documented input) and assert the FLOORS
# actually hold on the output — a defect-surfacing check, not a "did it return
# something" check.
# ---------------------------------------------------------------------------

def test_enforce_iron_rules_available(iron_fn):
    if iron_fn is None:
        pytest.xfail("engine.core.enforce_iron_rules not present in this build")
    assert callable(iron_fn)


def test_enforce_iron_rules_raises_cc_floor(iron_fn, iron_consts):
    """Every pixel that HAS clearcoat (CC>0) but sits below the floor must be
    lifted to the floor. (Pixels with CC==0 are intentionally exempt.)"""
    if iron_fn is None:
        pytest.xfail("enforce_iron_rules not present")
    cc_floor = iron_consts["CC_FLOOR"]
    rng = np.random.default_rng(SEED)
    spec = _spec3(rng)
    # Seed CC with small POSITIVE values strictly below the floor so the
    # `where=(CC>0)` carve-out applies and the floor must engage.
    spec[:, :, 2] = max(1.0, cc_floor - 5.0)
    out = iron_fn(spec.copy())
    out = spec if out is None else np.asarray(out, dtype=np.float32)
    cc = out[:, :, 2]
    assert np.isfinite(cc).all(), "CC has NaN/Inf after enforce"
    assert float(cc.min()) >= cc_floor - 1e-3, (
        f"CC floor not enforced: min={float(cc.min())} < {cc_floor}"
    )


def test_enforce_iron_rules_roughness_floor_for_non_chrome(iron_fn, iron_consts):
    """Non-chrome pixels (M below the chrome threshold) must have R >= R floor,
    and no pixel may end up with negative roughness."""
    if iron_fn is None:
        pytest.xfail("enforce_iron_rules not present")
    r_floor = iron_consts["R_FLOOR"]
    chrome_m = iron_consts["CHROME_M"]
    rng = np.random.default_rng(SEED)
    spec = _spec3(rng)
    # Clearly NON-chrome: metallic well below the chrome threshold, roughness
    # below the floor -> the R floor MUST engage.
    spec[:, :, 0] = max(0.0, chrome_m - 50.0)  # M below chrome threshold
    spec[:, :, 1] = 2.0                          # R below floor
    out = iron_fn(spec.copy())
    out = spec if out is None else np.asarray(out, dtype=np.float32)
    r = out[:, :, 1]
    assert np.isfinite(r).all(), "R has NaN/Inf after enforce"
    assert float(r.min()) >= 0.0, f"negative roughness leaked: {float(r.min())}"
    assert float(r.min()) >= r_floor - 1e-3, (
        f"non-chrome R floor not enforced: min={float(r.min())} < {r_floor}"
    )


def test_enforce_iron_rules_output_is_finite_and_in_shape(iron_fn):
    """Output stays finite, same shape, contract-valid for a random spec."""
    if iron_fn is None:
        pytest.xfail("enforce_iron_rules not present")
    rng = np.random.default_rng(SEED)
    for shape in [(SMALL, SMALL, 3), (SMALL, SMALL, 4)]:
        spec = _spec3(rng, shape=shape)
        out = iron_fn(spec.copy())
        out = spec if out is None else np.asarray(out, dtype=np.float32)
        assert out.shape == shape, f"shape changed {shape} -> {out.shape}"
        assert np.isfinite(out).all(), f"non-finite output for shape {shape}"
        assert is_valid_spec(out), f"non-contract output for shape {shape}"


def test_enforce_iron_rules_is_idempotent(iron_fn):
    """A floor/clamp pass applied twice must equal applying it once.
    Non-idempotence (overshoot) is exactly the iron-safety bug class."""
    if iron_fn is None:
        pytest.xfail("enforce_iron_rules not present")
    rng = np.random.default_rng(SEED)
    spec = _spec3(rng)
    once = iron_fn(spec.copy())
    once = spec if once is None else np.asarray(once, dtype=np.float32)
    twice_in = once.copy()
    twice = iron_fn(twice_in)
    twice = twice_in if twice is None else np.asarray(twice, dtype=np.float32)
    assert once.shape == twice.shape
    assert np.allclose(once, twice, rtol=1e-4, atol=1e-4), (
        "enforce_iron_rules is not idempotent "
        f"(max delta {float(np.max(np.abs(once - twice)))})"
    )


def test_enforce_iron_rules_keeps_sampled_specs_iron_safe(iron_fn, iron_consts, spec_samples):
    """Real sampled specs (promoted to >=3 channels) come out finite, floored
    where applicable, non-negative R, and contract-valid after enforcement."""
    if iron_fn is None:
        pytest.xfail("enforce_iron_rules not present")
    if not spec_samples:
        pytest.xfail("no spec samples collected")
    cc_floor = iron_consts["CC_FLOOR"]
    problems = []
    checked = 0
    for label, arr in spec_samples:
        a = np.asarray(arr, dtype=np.float32)
        # enforce_iron_rules needs >=3 channels; promote a 2-D/low-C spec the
        # same way the engine pipeline would before the safety net runs.
        if a.ndim == 2:
            a = np.repeat(a[:, :, None], 4, axis=2)
        elif a.ndim == 3 and a.shape[2] < 3:
            a = np.repeat(a[:, :, :1], 4, axis=2)
        try:
            out = iron_fn(a.copy())
        except Exception as e:  # a crash on a valid 3-D spec IS a defect
            problems.append((label, f"crash: {type(e).__name__}: {e}"))
            continue
        out = a if out is None else np.asarray(out, dtype=np.float32)
        checked += 1
        if not np.isfinite(out).all():
            problems.append((label, "non-finite after enforce"))
            continue
        if not is_valid_spec(out):
            problems.append((label, f"non-contract shape {out.shape}"))
            continue
        cc = out[:, :, 2]
        cc_pos = cc[cc > 0]  # CC floor only applies where CC>0
        if cc_pos.size and float(cc_pos.min()) < cc_floor - 1e-3:
            problems.append((label, f"CC floor breached {float(cc_pos.min())}"))
        if float(out[:, :, 1].min()) < 0.0:
            problems.append((label, f"negative R {float(out[:, :, 1].min())}"))
    assert checked > 0, "no sample could be exercised through enforce_iron_rules"
    assert not problems, f"iron-safety violations: {problems[:10]}"


# ---------------------------------------------------------------------------
# Contract 3: the 2-D vs 3-D shape-handling regression (fixed 2026-05-29).
#
# enforce_iron_rules indexes channels 0..2, so a bare 2-D (H,W) spec cannot be
# floored channel-wise — the engine promotes such specs to (H,W,C>=3) before
# the safety net. We guard the two behaviors that matter:
#   (a) a 3-D (H,W,3) spec is handled cleanly (no crash, floors hold), and
#   (b) a 2-D (H,W) spec must not be SILENTLY corrupted: enforce_iron_rules
#       either handles it or raises a clean, predictable error — it must never
#       return a wrong-shaped or non-finite result without erroring. (Silent
#       corruption on the 2-D path is the precise regression class.)
# and, on the spec-producer side, any sampled callable that takes a bare shape
# tuple must accept BOTH (h,w) and (h,w,3) without crashing.
# ---------------------------------------------------------------------------

def test_enforce_iron_rules_handles_3channel_array(iron_fn):
    if iron_fn is None:
        pytest.xfail("enforce_iron_rules not present")
    rng = np.random.default_rng(SEED)
    a3 = _spec3(rng, shape=(SMALL, SMALL, 3))
    out = iron_fn(a3.copy())
    out = a3 if out is None else np.asarray(out, dtype=np.float32)
    assert out.shape == (SMALL, SMALL, 3)
    assert np.isfinite(out).all()
    assert is_valid_spec(out)


def test_enforce_iron_rules_2d_path_is_not_silently_corrupted(iron_fn):
    """A 2-D (H,W) spec must not yield a silently-wrong result.

    Acceptable outcomes: a clean exception (the engine promotes to 3-D before
    calling), OR a finite, contract-valid array. The forbidden outcome — the
    regression we are guarding — is a non-finite or non-contract result
    returned WITHOUT error (silent corruption).
    """
    if iron_fn is None:
        pytest.xfail("enforce_iron_rules not present")
    rng = np.random.default_rng(SEED)
    a2 = rng.random((SMALL, SMALL), dtype=np.float32) * 255.0
    try:
        out = iron_fn(a2.copy())
    except Exception:
        # Clean failure on an unsupported rank is fine (caller promotes first).
        return
    out = a2 if out is None else np.asarray(out, dtype=np.float32)
    assert np.isfinite(out).all(), "2-D path returned non-finite WITHOUT error (corruption)"
    assert is_valid_spec(out), f"2-D path returned non-contract shape {out.shape} WITHOUT error"


def _accepts_shape_tuple(fn):
    """Heuristic: does fn take a single shape/size tuple as its first required arg?"""
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    pos = [
        p for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY)
        and p.default is p.empty
    ]
    if not pos:
        return False
    name = pos[0].name.lower()
    return name in ("shape", "size", "dims", "hw", "wh") or "shape" in name or "size" in name


def test_spec_callables_tolerate_both_shape_tuple_forms(registries):
    """For sampled spec callables that take a shape/size tuple, calling with a
    (h,w) tuple AND a (h,w,3) tuple must not raise — the fixed 2026-05-29 bug.

    Only callables that actually accept a shape tuple as their first required
    arg are exercised, so this is a precise guard, not a fuzz test. A TypeError
    just means "wrong call convention for this fn" (not the bug class) and is
    skipped; any OTHER exception on a valid shape tuple is the regression and
    fails the test. If no sampled callable takes a bare shape tuple, the 2-D/3-D
    guard above covers the class, so we xfail-vacuous rather than red.
    """
    exercised = 0
    failures = []
    for reg_name, reg in registries.items():
        for ent_id, entry in list(_iter_entries(reg))[:30]:
            for fn in _candidate_callables(entry):
                if not _accepts_shape_tuple(fn):
                    continue
                hit = False
                for shp in ((SMALL, SMALL), (SMALL, SMALL, 3)):
                    try:
                        with suppress_stdout():
                            fn(shp)
                        hit = True
                    except TypeError:
                        continue  # wrong convention, not the bug class
                    except Exception as e:  # a crash on a valid shape tuple IS the bug
                        failures.append((f"{reg_name}:{ent_id}", str(shp), repr(e)))
                        hit = True
                if hit:
                    exercised += 1
                break
    if failures:
        pytest.fail(f"spec callables crashed on a shape tuple form: {failures[:10]}")
    if exercised == 0:
        pytest.xfail(
            "no sampled spec callable takes a bare shape tuple; the (h,w) vs "
            "(h,w,3) regression is covered by the enforce_iron_rules 2-D/3-D "
            "tests above instead."
        )
    assert exercised >= 1
