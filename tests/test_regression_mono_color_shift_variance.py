"""Regression guardrail — chameleon + prizm color-shift MONOs must
produce meaningful SPEC variance (the source of their iridescent
angle-shift behavior), even though their PAINT output is intentionally
flat.

## Context (Iter 7, ship-readiness audit, 2026-04-22)

iRacing chameleon and prizm finishes produce their multi-color
angle-shift via the spec map, not via spatially-varying paint.
The PBR renderer reads metallic/roughness/clearcoat variation at
each viewing angle and produces the iridescence on the 3D surface.
The PAINT is intentionally a flat base color — the painter picks
their base hue, and the spec-map channel variation does the shifting.

Pillman's Iter 7 probe (2026-04-22) measured:

  - paint_fn variance: 0.00000 (exactly flat) across 12 chameleon_*
    and prizm_* entries.
  - base_spec_fn variance: M-range 28-180, R-range 7-80, CC-range
    0-49. Non-zero spec variance is the iridescence source.

**Bug class this test catches:** if someone accidentally flattens
these MONOs' spec output (e.g. by routing them through
`_spec_foundation_flat` during a Foundation-trust-style pass), the
iridescent effect disappears entirely — painter sees a dull flat
color where they expected chameleon shimmer.

## What this test pins

  For each chameleon_* / prizm_* MONO in the registry:
    * paint_fn variance may be zero (intentional, don't fire).
    * base_spec_fn output MUST have at least 5 units of spread on
      at least ONE of M/R/CC — otherwise the color-shift effect
      is gone and the MONO is rendering as a dull flat color.
"""

import io
import contextlib

import numpy as np
import pytest


@pytest.fixture(scope="module")
def mono_reg():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import MONOLITHIC_REGISTRY
    return MONOLITHIC_REGISTRY


SHIFT_FAMILY_MIDS = [
    # Chameleon
    "chameleon_amethyst", "chameleon_arctic", "chameleon_copper",
    "chameleon_emerald", "chameleon_frost", "chameleon_midnight",
    "chameleon_obsidian", "chameleon_ocean", "chameleon_phoenix",
    "chameleon_venom",
    # Prizm
    "prizm_holographic", "prizm_iridescent",
]


@pytest.mark.parametrize("mid", SHIFT_FAMILY_MIDS)
def test_color_shift_mono_has_spec_variance(mono_reg, mid):
    """Each chameleon / prizm MONO's base_spec_fn must produce at
    least 5-unit spread on at least ONE of M/R/CC. Without spec
    variance, the iridescence is invisible and the painter sees a
    dull flat color."""
    assert mid in mono_reg, f"{mid} missing from MONOLITHIC_REGISTRY"
    tup = mono_reg[mid]
    assert isinstance(tup, (tuple, list)) and len(tup) >= 2, (
        f"{mid} registry entry is not a (spec_fn, paint_fn) tuple"
    )
    sf = tup[0]
    shape = (128, 128)
    mask = np.ones(shape, dtype=np.float32)
    out = sf(shape, mask, 42, 1.0)
    arr = np.asarray(out)
    assert arr.ndim == 3 and arr.shape[2] >= 3, (
        f"{mid} spec_fn returned unexpected shape {arr.shape}"
    )
    M_range = int(arr[:, :, 0].max()) - int(arr[:, :, 0].min())
    R_range = int(arr[:, :, 1].max()) - int(arr[:, :, 1].min())
    CC_range = int(arr[:, :, 2].max()) - int(arr[:, :, 2].min())
    max_range = max(M_range, R_range, CC_range)
    assert max_range >= 5, (
        f"{mid} spec has only M-range={M_range}, R-range={R_range}, "
        f"CC-range={CC_range}. Chameleon/prizm iridescence depends on "
        f"spec variance; without it the painter sees dull flat. "
        f"Check that the mono's base_spec_fn wasn't accidentally "
        f"routed through a flat dispatcher (e.g. _spec_foundation_flat)."
    )


def test_entire_color_shift_family_covered(mono_reg):
    """Sanity: SHIFT_FAMILY_MIDS must all exist in MONOLITHIC_REGISTRY.
    If one is renamed or deleted, this fires."""
    missing = [m for m in SHIFT_FAMILY_MIDS if m not in mono_reg]
    assert not missing, (
        f"SHIFT_FAMILY_MIDS includes ids not in MONOLITHIC_REGISTRY: "
        f"{missing}. Either they were renamed (update this list) or "
        f"deleted (remove from list + confirm catalog doesn't still "
        f"reference them)."
    )


def test_color_shift_family_has_intentionally_flat_paint(mono_reg):
    """Sanity counter-test: the SHIFT family's paint_fn is
    intentionally flat (variance < 0.001). If variance rises, someone
    changed the design intent and this test + the spec-variance
    ratchet above may need re-tuning."""
    shape = (128, 128)
    mask = np.ones(shape, dtype=np.float32)
    paint_in = np.full((*shape, 3), 0.5, dtype=np.float32)

    non_flat = []
    for mid in SHIFT_FAMILY_MIDS:
        if mid not in mono_reg: continue
        pf = mono_reg[mid][1]
        try:
            out = pf(paint_in.copy(), shape, mask, 42, 1.0, 1.0)
            arr = np.asarray(out)[..., :3]
            var = float(arr.reshape(-1, 3).var(axis=0).sum())
        except Exception:
            continue
        if var >= 0.001:
            non_flat.append((mid, var))

    assert not non_flat, (
        f"Color-shift MONO paint_fns now have non-flat output: "
        f"{[(m, f'{v:.4f}') for m, v in non_flat]}. If this is "
        f"intentional (design shift to paint-side iridescence), "
        f"update this test and the companion spec-variance ratchet "
        f"together."
    )
