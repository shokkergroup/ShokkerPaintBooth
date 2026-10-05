"""Regression guardrail — Foundation Bases must output FLAT spec.

## Context (2026-04-21 painter report: "foundation bases are vanilla")

Painter: "The FOUNDATION FUCKING BASES are supposed to be vanilla.
Metallic just LOOKS metallic - whatever the color is. It doesn't change
the color - it doesn't add its own textures to the spec map. NONE of
the foundation bases are supposed to do ANYTHING other than change the
texture/look of the color it's affecting."

Pre-fix state: every `f_*` entry in `engine/base_registry_data.py`
carried `noise_M`, `noise_R`, `noise_scales`, `noise_weights`, or
`perlin` keys. The compose pipeline at `engine/compose.py:1207+`
reads those and applies `base_M + multi_scale_noise * noise_M *
_sm_base` per-pixel. That turned a "flat material property" into a
visible diagonal/speckle texture on the spec map. The painter saw
it as "Metallic is adding texture even though I selected a plain
Foundation Base."

Plus `_make_spec` (the factory behind `spec_enh_*` helpers) was
baking in `m_var`/`r_var`/`cc_var` noise by default. Same class of
bug on the `enh_*` side.

## What this test pins

  1. Every Foundation Base (id starts with `f_`) in `BASE_REGISTRY`
     must NOT carry `noise_M`, `noise_R`, `noise_CC`, `noise_scales`,
     `noise_weights`, or `perlin` — keys the compose pipeline reads
     to add noise texture.
  2. Calling the factory-built `_make_spec(...)` at any variance
     arguments must still produce byte-for-byte-constant output
     across the canvas (no per-pixel modulation).
  3. End-to-end: calling compose for each Foundation Base produces
     a spec map whose M, R, and CC channels each have zero
     per-pixel variation inside the mask region.
"""

import io
import contextlib

import numpy as np
import pytest


NOISE_KEYS = (
    "noise_M", "noise_R", "noise_CC",
    "noise_scales", "noise_weights",
    "perlin", "perlin_octaves", "perlin_persistence", "perlin_lacunarity",
)


@pytest.fixture(scope="module")
def base_registry():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import BASE_REGISTRY
    return BASE_REGISTRY


def _foundation_ids(base_registry):
    return sorted(name for name in base_registry.keys() if name.startswith("f_"))


def test_every_foundation_base_carries_no_noise_keys(base_registry):
    """Each `f_*` Foundation Base entry must NOT have any noise /
    perlin keys. If any sneaks back in, the compose pipeline will
    apply per-pixel noise and the painter sees texture on what
    should be a flat material signal.
    """
    offenders = []
    for fname in _foundation_ids(base_registry):
        entry = base_registry[fname]
        bad_keys = [k for k in NOISE_KEYS if k in entry]
        if bad_keys:
            offenders.append(f"{fname}: {bad_keys}")
    assert not offenders, (
        "Foundation Base(s) carry noise keys — the compose pipeline will "
        "add per-pixel texture to their spec output, breaking the 'flat "
        "material property' contract:\n  " + "\n  ".join(offenders)
    )


def test_make_spec_factory_emits_flat_output():
    """The `_make_spec` factory must produce a function whose output
    is constant across every pixel, regardless of what variance
    arguments the call site passed. The variance args are kept in
    the signature for backward-compat but must be ignored.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.paint_v2.foundation_enhanced import _make_spec

    # Pick arbitrary base values and high variance to stress-test.
    fn = _make_spec(200, 45, 16, seed_offset=9999,
                    m_var=50, r_var=40, cc_var=20)
    M, R, CC = fn((32, 32), seed=42, sm=1.0, bm=200, br=45)

    for name, arr, expected in [("M", M, 200), ("R", R, 45), ("CC", CC, 16)]:
        arr_np = np.asarray(arr)
        assert arr_np.ndim == 2, f"{name} has wrong ndim={arr_np.ndim}"
        mn, mx = float(arr_np.min()), float(arr_np.max())
        assert mn == mx, (
            f"{name} channel from _make_spec is NOT flat: "
            f"min={mn}, max={mx}. Foundation Base spec must be constant "
            f"(variance args were ignored before, should still be)."
        )
        # Value should match the base (allow for _enforce_iron adjustments
        # that clamp to legal spec ranges — e.g. R is boosted to ≥ 15 for
        # non-chrome).
        assert abs(mn - expected) <= 15, (
            f"{name} channel base value drifted: got {mn}, expected ~{expected}"
        )


@pytest.mark.parametrize("fid,expected_M,expected_R,expected_CC", [
    ("f_metallic",     200, 50, 16),
    ("f_chrome",       255,  2, 16),
    ("f_satin_chrome", 250, 45, 40),
    ("f_pearl",        100, 40, 16),
    ("f_frozen",       160, 85, 130),
    ("f_anodized",     180, 65, 85),
    ("f_baked_enamel",   0, 18, 20),
    ("f_carbon_fiber",  55, 30, 16),
])
def test_foundation_compose_output_has_no_texture_noise(
    base_registry, fid, expected_M, expected_R, expected_CC
):
    """End-to-end: a Foundation Base compose run must produce a spec
    map with at most ±1 per-pixel variation — that's the anti-banding
    dither (uniform ±0.5 added before uint8 quantization, sub-
    perceptible). Any WIDER range means the Foundation is baking in
    visible texture noise, which is the painter-visible bug this
    fix addressed.

    Concretely the painter's pre-fix f_metallic had M ranging 139→220
    (80-unit spread = obvious diagonal texture). Post-fix should be
    199→200 or tighter.
    """
    if fid not in base_registry:
        pytest.skip(f"{fid} not in BASE_REGISTRY")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.compose import compose_finish

    shape = (32, 32)
    mask = np.ones(shape, dtype=np.float32)

    spec = np.asarray(compose_finish(fid, "none", shape, mask, 42, 1.0))
    assert spec.shape == (32, 32, 4), f"unexpected spec shape {spec.shape}"

    DITHER_TOLERANCE = 1  # ±0.5 uint8 dither widens range by 1
    for ch_idx, ch_name in enumerate(("M", "R", "CC")):
        ch = spec[:, :, ch_idx]
        mn, mx = int(ch.min()), int(ch.max())
        spread = mx - mn
        assert spread <= DITHER_TOLERANCE, (
            f"Foundation {fid!r} compose output has TEXTURE NOISE on "
            f"{ch_name} channel (min={mn}, max={mx}, spread={spread} > "
            f"{DITHER_TOLERANCE}-unit anti-banding dither). A painter "
            f"would see this as diagonal/speckle texture on their spec "
            f"map. The Foundation Base should output essentially-constant "
            f"material properties."
        )


def test_spec_enh_factory_builds_flat_across_all_foundations():
    """Every `spec_enh_*` module-level value in foundation_enhanced.py
    must produce a flat spec output regardless of its historical
    variance arguments. Protects against a future edit that
    accidentally reintroduces `multi_scale_noise` inside the factory.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import engine.paint_v2.foundation_enhanced as fe

    spec_names = [n for n in dir(fe) if n.startswith("spec_enh_")
                  and not n.startswith("spec_enh_factory")]
    offenders = []
    for name in spec_names:
        spec_fn = getattr(fe, name)
        if not callable(spec_fn):
            continue
        try:
            M, R, CC = spec_fn((32, 32), 42, 1.0, 0, 0)
        except TypeError:
            # Some functions may have different signatures — skip
            continue
        for ch_name, arr in (("M", M), ("R", R), ("CC", CC)):
            arr_np = np.asarray(arr)
            if arr_np.ndim != 2:
                continue
            mn, mx = float(arr_np.min()), float(arr_np.max())
            if mn != mx:
                offenders.append(f"{name}.{ch_name}: min={mn}, max={mx}")

    assert not offenders, (
        "spec_enh_* helpers emit non-flat output — Foundation Base "
        "contract broken:\n  " + "\n  ".join(offenders[:15])
    )
