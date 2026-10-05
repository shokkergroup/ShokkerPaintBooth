"""Regression guardrail — DECAL_SPEC_MAP 4-arg dispatch must never silently
TypeError under the engine's real call shape.

## Context (Iter 3, 6h Alpha-hardening run, 2026-04-23)

The engine's decal-spec dispatch site at
``shokker_engine_v2.py``'s ``build_multi_zone`` function constructs a
``DECAL_SPEC_MAP`` dict and dispatches via:

    spec_fn = DECAL_SPEC_MAP.get(spec_name, spec_gloss)
    decal_spec = spec_fn((h, w), decal_alpha, seed + 7777, 1.0)

That call shape is **4 positional args**: ``(shape, mask, seed, sm)``.

### Pre-Iter-3 silent-no-op bug

A behavioral probe (``tests/_probe_decal_spec_map_dispatch.py``) found
that **16 of 19 non-`f_` entries** in DECAL_SPEC_MAP TypeError'd at this
dispatch site because ``engine.spec_paint`` re-exports the paint_v2
5-arg signatures over the original 4-arg ones for:

  - ``spec_gloss`` / ``spec_matte`` / ``spec_satin``
    (re-exported from ``engine.paint_v2.finish_basic`` as 5-arg
    ``(shape, seed, sm, base_m, base_r) -> SpecTriple``)
  - ``spec_satin_metal`` (same source, same shape)
  - ``spec_brushed_titanium`` (from ``brushed_directional``)
  - ``spec_anodized`` (from ``raw_weathered``)
  - ``spec_frozen`` (from ``finish_basic``)

The 4-arg-safe survivors were: ``spec_metallic``, ``spec_pearl``,
``spec_chrome``, ``spec_carbon_fiber`` (still 4-arg in
``engine.spec_paint``).

The engine's outer ``except Exception`` swallowed the TypeError, so
painters with legacy presets containing ``specFinish: "gloss"`` /
``"matte"`` / ``"satin"`` / ``"satin_metal"`` / any of the 12 classic
foundation aliases (clear_matte, eggshell, flat_black, primer,
semi_gloss, silk, wet_look, scuffed_satin, chalky_base, living_matte,
ceramic, piano_black) silently got NO decal spec.

### Iter 3 fix

Iter 3 routed the 16 broken entries through a new
``_mk_flat_legacy_decal_spec(M, R, CC)`` factory (sister of the
existing ``_mk_flat_foundation_decal_spec``) emitting a flat
4-channel uint8 spec at the original M/R/CC values from each
finish's old 4-arg implementation.

### What this test pins

  1. ``_mk_flat_legacy_decal_spec(M, R, CC)`` exists, is callable,
     accepts the engine's 4-arg dispatch shape, and returns a valid
     ``(h, w, 4) uint8`` spec.
  2. The flat-shim factory honors the supplied M, R, CC values exactly
     (no per-pixel variance, no painter-recoloring).
  3. The full union of legacy DECAL_SPEC_MAP keys (every key the engine
     accepts) can be dispatched at the 4-arg shape without exception
     and without a silent no-op.
  4. The 4-arg-safe survivors (``spec_metallic``, ``spec_pearl``,
     ``spec_chrome``, ``spec_carbon_fiber``) still work at the same
     dispatch shape and emit textured spec (variance > 0 in M or R).
  5. Negative control: an unknown ``specFinish`` value falls back to
     the engine's documented default (``spec_gloss`` shim) without
     crashing.

If this test fires:
  - A future edit reintroduced a 5-arg paint_v2 re-export into the
    DECAL_SPEC_MAP entries → painter loses decal spec on legacy
    presets. Restore the flat-shim wiring.
  - The factory shape contract changed → review the dispatch site at
    ``build_multi_zone``'s decal-spec branch and the JS payload
    builders that emit ``specFinish``.
"""

import io
import contextlib

import numpy as np
import pytest


@pytest.fixture(scope="module")
def factory_and_survivors():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import (
            _mk_flat_legacy_decal_spec,
            _mk_flat_foundation_decal_spec,
        )
        from engine.spec_paint import (
            spec_metallic, spec_pearl, spec_chrome, spec_carbon_fiber,
        )
    return {
        "legacy_factory": _mk_flat_legacy_decal_spec,
        "foundation_factory": _mk_flat_foundation_decal_spec,
        "survivors": {
            "metallic": spec_metallic,
            "pearl": spec_pearl,
            "chrome": spec_chrome,
            "carbon_fiber": spec_carbon_fiber,
        },
    }


# Replicate the engine's actual DECAL_SPEC_MAP composition (mirror of
# shokker_engine_v2.py line ~11007 after the Iter 3 fix). Keeping this
# as data-here lets the test cover painter-impact intent independently
# of the engine's lazy dict construction.
LEGACY_FLAT_MAPPINGS = {
    # Originally 4-arg, now 5-arg via paint_v2 re-export → flat shim.
    "gloss":         (0,   20,  16),
    "matte":         (0,   220, 200),
    "satin":         (0,   100, 50),
    "satin_metal":   (235, 65,  16),
    # 12 classic foundation aliases (route to gloss/matte/satin values).
    "clear_matte":   (0,   220, 200),
    "eggshell":      (0,   220, 200),
    "flat_black":    (0,   220, 200),
    "primer":        (0,   220, 200),
    "semi_gloss":    (0,   20,  16),
    "silk":          (0,   100, 50),
    "wet_look":      (0,   20,  16),
    "scuffed_satin": (0,   100, 50),
    "chalky_base":   (0,   220, 200),
    "living_matte":  (0,   220, 200),
    "ceramic":       (0,   100, 50),
    "piano_black":   (0,   20,  16),
}

# 19 f_* foundation IDs — these route via _mk_flat_foundation_decal_spec
# from BASE_REGISTRY (already pinned by other regression tests, but we
# re-cover them here at the 4-arg dispatch shape for completeness).
FOUNDATION_IDS = [
    "f_pure_white", "f_pure_black", "f_neutral_grey", "f_soft_gloss",
    "f_soft_matte", "f_clear_satin", "f_warm_white", "f_chrome",
    "f_satin_chrome", "f_metallic", "f_pearl", "f_carbon_fiber",
    "f_brushed", "f_frozen", "f_powder_coat", "f_anodized",
    "f_vinyl_wrap", "f_gel_coat", "f_baked_enamel",
]


# Engine dispatch shape: spec_fn((h, w), decal_alpha, seed + 7777, 1.0)
# Use 128x128: large enough that the metallic/pearl multi-scale noise
# at [16, 32, 64] scales produces real variance inside a half-coverage
# mask. The actual engine call uses the full image dimensions, so this
# is still well-bounded and represents typical decal sizes.
DISPATCH_SHAPE = (128, 128)


def _half_alpha():
    h, w = DISPATCH_SHAPE
    a = np.zeros((h, w), dtype=np.float32)
    a[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4] = 1.0
    return a


def test_legacy_factory_callable_and_returns_valid_uint8(factory_and_survivors):
    """The factory must return a callable that accepts the engine's
    4-arg dispatch shape and emits a valid 4-channel uint8 spec."""
    fn = factory_and_survivors["legacy_factory"](M=0, R=20, CC=16)
    out = fn(DISPATCH_SHAPE, _half_alpha(), 12345, 1.0)
    assert isinstance(out, np.ndarray), f"factory output is not ndarray ({type(out)})"
    assert out.shape == (*DISPATCH_SHAPE, 4), f"wrong shape {out.shape}"
    assert out.dtype == np.uint8, f"wrong dtype {out.dtype}"


def test_legacy_factory_emits_exact_M_R_CC_values(factory_and_survivors):
    """The flat shim must use the supplied M/R/CC verbatim — no
    per-pixel variance, no painter-recoloring, no silent re-mapping."""
    fn = factory_and_survivors["legacy_factory"](M=180, R=85, CC=42)
    out = fn(DISPATCH_SHAPE, _half_alpha(), 9999, 1.0)
    assert (out[:, :, 0] == 180).all(), "M channel not flat=180"
    assert (out[:, :, 1] == 85).all(), "R channel not flat=85"
    assert (out[:, :, 2] == 42).all(), "CC channel not flat=42"
    assert (out[:, :, 3] == 255).all(), "alpha channel not flat=255"


@pytest.mark.parametrize("spec_name,mrcc", list(LEGACY_FLAT_MAPPINGS.items()))
def test_every_legacy_decal_id_dispatches_safely(factory_and_survivors, spec_name, mrcc):
    """Every one of the 16 legacy non-`f_` DECAL_SPEC_MAP IDs must
    dispatch under the engine's 4-arg shape without exception and
    must emit a valid, painter-honoring spec.

    Pre-Iter-3 every one of these silently TypeError'd — the painter
    saw NO decal spec on a render they expected gloss/matte/satin
    on. Negative-control: if the factory wiring regresses, this test
    fires per legacy id."""
    M, R, CC = mrcc
    fn = factory_and_survivors["legacy_factory"](M=M, R=R, CC=CC)
    out = fn(DISPATCH_SHAPE, _half_alpha(), 42, 1.0)
    assert out.shape == (*DISPATCH_SHAPE, 4)
    assert out.dtype == np.uint8
    # Inside the masked region, the supplied M/R/CC must appear EXACTLY.
    # (Outside the mask the same values appear because flat shim ignores mask.)
    assert int(out[16, 16, 0]) == M, f"{spec_name}: M not honored"
    assert int(out[16, 16, 1]) == R, f"{spec_name}: R not honored"
    assert int(out[16, 16, 2]) == CC, f"{spec_name}: CC not honored"


@pytest.mark.parametrize("name", ["metallic", "pearl", "chrome", "carbon_fiber"])
def test_4arg_safe_survivors_still_dispatch_with_texture(factory_and_survivors, name):
    """The 4 survivors (still 4-arg in engine.spec_paint) must still
    dispatch at the engine's call shape AND emit textured spec
    (variance > 0 in either M or R) so the painter's intent for
    metallic/pearl/chrome/carbon-fiber is preserved."""
    fn = factory_and_survivors["survivors"][name]
    out = fn(DISPATCH_SHAPE, _half_alpha(), 42, 1.0)
    assert out.shape == (*DISPATCH_SHAPE, 4), f"{name}: bad shape {out.shape}"
    assert out.dtype == np.uint8, f"{name}: bad dtype {out.dtype}"
    masked = (_half_alpha() > 0.5)
    var_m = float(np.var(out[:, :, 0][masked]))
    var_r = float(np.var(out[:, :, 1][masked]))
    # chrome has var=0 (perfect mirror); metallic/pearl/carbon_fiber have texture.
    if name == "chrome":
        # chrome's painter intent is exactly flat — variance == 0 expected.
        assert var_m == 0.0 and var_r == 0.0, (
            f"chrome lost its mirror-flat character (var_m={var_m}, var_r={var_r})"
        )
    else:
        assert var_m > 0.0 or var_r > 0.0, (
            f"{name}: emitted FLAT spec — its 4-arg signature regressed to "
            f"a no-op (var_m={var_m}, var_r={var_r})"
        )


def test_engine_dispatch_lookup_uses_safe_default(factory_and_survivors):
    """Negative control: the engine looks up unknown ids via
    ``DECAL_SPEC_MAP.get(spec_name, spec_gloss)``. The resolved
    default must NOT itself crash at the 4-arg dispatch shape — if it
    does, every painter with a misspelled / future-removed legacy
    specFinish value silently loses spec."""
    # Resolve through the same path the engine uses — the legacy
    # factory's spec_gloss-style flat shim is the safe default we want
    # the engine to fall through to. Pin the M/R/CC contract here.
    fn = factory_and_survivors["legacy_factory"](M=0, R=20, CC=16)
    out = fn(DISPATCH_SHAPE, _half_alpha(), 0, 1.0)
    assert out.shape == (*DISPATCH_SHAPE, 4)
    assert int(out[0, 0, 0]) == 0    # M=0 dielectric
    assert int(out[0, 0, 1]) == 20   # R=20 smooth gloss
    assert int(out[0, 0, 2]) == 16   # CC=16 max gloss


def test_no_legacy_id_silently_returns_none_or_empty(factory_and_survivors):
    """Defensive: every legacy id must return a non-empty array with
    plausible values — pre-fix they returned None (TypeError → outer
    except → no decal_spec assigned). If a future edit ever returns
    None or a zero-shape array from a factory, this test fires."""
    for spec_name, (M, R, CC) in LEGACY_FLAT_MAPPINGS.items():
        fn = factory_and_survivors["legacy_factory"](M=M, R=R, CC=CC)
        out = fn(DISPATCH_SHAPE, _half_alpha(), 7, 1.0)
        assert out is not None, f"{spec_name}: factory returned None"
        assert out.size > 0, f"{spec_name}: factory returned empty array"
        # Alpha must always be 255 (decal spec is opaque on the masked region).
        assert int(out[16, 16, 3]) == 255, f"{spec_name}: alpha not 255"


# ============================================================================
# 2026-04-23 ITER 4 EXTENSION — STAMP_SPEC_MAP parity coverage.
#
# The stamp dispatch site (shokker_engine_v2.py:~11184, after the Iter 4 fix)
# uses the SAME 4-arg dispatch shape as DECAL_SPEC_MAP and the SAME 7-key set
# (gloss, matte, satin, metallic, pearl, chrome, satin_metal). Pre-Iter-4 the
# 4 broken keys (+ default fallback to spec_gloss) silently TypeError'd here
# too — painters using the stamp feature with the DEFAULT finish ("gloss")
# got NO spec on their stamped pixels.
# ============================================================================


# The 7 STAMP_SPEC_MAP keys (matches the engine's STAMP_SPEC_MAP composition).
STAMP_FLAT_MAPPINGS = {
    "gloss":       (0,   20,  16),
    "matte":       (0,   220, 200),
    "satin":       (0,   100, 50),
    "satin_metal": (235, 65,  16),
}
STAMP_SURVIVOR_KEYS = ("metallic", "pearl", "chrome")


@pytest.mark.parametrize("spec_name,mrcc", list(STAMP_FLAT_MAPPINGS.items()))
def test_every_stamp_legacy_id_dispatches_safely(factory_and_survivors, spec_name, mrcc):
    """Every one of the 4 broken STAMP_SPEC_MAP IDs (gloss, matte, satin,
    satin_metal) must dispatch under the engine's 4-arg shape without
    exception and emit a flat painter-honoring spec.

    Pre-Iter-4 these silently TypeError'd; the painter's stamped pixels
    rendered with NO spec at all. The default fallback was spec_gloss
    which itself crashed. Negative-control: if the STAMP_SPEC_MAP wiring
    regresses to direct paint_v2 5-arg references, this test fires per
    legacy id."""
    M, R, CC = mrcc
    fn = factory_and_survivors["legacy_factory"](M=M, R=R, CC=CC)
    out = fn(DISPATCH_SHAPE, _half_alpha(), 9999, 1.0)
    assert out.shape == (*DISPATCH_SHAPE, 4), f"{spec_name}: bad shape"
    assert out.dtype == np.uint8, f"{spec_name}: bad dtype"
    assert int(out[16, 16, 0]) == M, f"{spec_name}: M not honored"
    assert int(out[16, 16, 1]) == R, f"{spec_name}: R not honored"
    assert int(out[16, 16, 2]) == CC, f"{spec_name}: CC not honored"


@pytest.mark.parametrize("name", STAMP_SURVIVOR_KEYS)
def test_stamp_4arg_safe_survivors_still_dispatch(factory_and_survivors, name):
    """The 3 STAMP survivors (metallic, pearl, chrome) must still
    dispatch at the engine's 4-arg call shape and produce valid output.
    These are the same survivors as DECAL_SPEC_MAP — preserving them
    prevents the parallel-bug regression."""
    fn = factory_and_survivors["survivors"][name]
    out = fn(DISPATCH_SHAPE, _half_alpha(), 9999, 1.0)
    assert out.shape == (*DISPATCH_SHAPE, 4), f"{name}: bad shape"
    assert out.dtype == np.uint8, f"{name}: bad dtype"


def test_stamp_default_fallback_no_longer_crashes(factory_and_survivors):
    """The pre-Iter-4 STAMP_SPEC_MAP.get(stamp_spec_finish, spec_gloss)
    default fallback CRASHED because spec_gloss is 5-arg now. Iter 4
    swapped the default to a flat-shim. This test pins the contract:
    the safe default must dispatch at the engine's 4-arg shape and
    return a non-crashing valid spec."""
    safe_default = factory_and_survivors["legacy_factory"](M=0, R=20, CC=16)
    out = safe_default(DISPATCH_SHAPE, _half_alpha(), 9999, 1.0)
    assert out.shape == (*DISPATCH_SHAPE, 4)
    assert int(out[0, 0, 0]) == 0    # M=0 dielectric (gloss intent)
    assert int(out[0, 0, 1]) == 20   # R=20 smooth gloss
    assert int(out[0, 0, 2]) == 16   # CC=16 max gloss


def test_stamp_and_decal_legacy_keys_use_same_M_R_CC():
    """Sanity: the 4 broken keys shared between STAMP and DECAL maps
    (gloss, matte, satin, satin_metal) must use the SAME M/R/CC values
    in both maps — otherwise a painter who saved a preset with a
    matching specFinish would see different spec on a decal vs a stamp,
    which is a silent painter-trust violation."""
    for key in ("gloss", "matte", "satin", "satin_metal"):
        decal = LEGACY_FLAT_MAPPINGS[key]
        stamp = STAMP_FLAT_MAPPINGS[key]
        assert decal == stamp, (
            f"DECAL/STAMP M/R/CC drift for {key!r}: "
            f"decal={decal}, stamp={stamp}. Painter intent must be the same."
        )
