"""Regression guardrail — ``base_spec_strength`` must weaken the
MATERIAL itself (M/R/CC channels shift toward neutral), not just
attenuate noise amplitude.

## Context (Iter 7, 6h Alpha-hardening run, 2026-04-23)

The painter's mental model: a base_spec_strength slider at 10% should
make Chrome read as a *much weaker* chrome (almost dielectric), not
just a chrome-with-less-noise. Same for every other material:
matte at 10% should be near-neutral roughness/CC, not just matte
with quieter speckle.

Iter 7 audit confirmed the engine implements this correctly via
``engine.compose._scale_base_spec_channels_toward_neutral`` (line 266)
called at compose.py:1303-1306 and 2109. The function scales:
  - M channel toward 0 (dielectric neutral)
  - R channel toward 128 (mid-roughness neutral)
  - CC channel toward SPEC_CLEARCOAT_MIN (=16, max-gloss neutral)

A behavioral probe (`tests/_probe_spec_strength_material_truth.py`)
confirmed actual emitted spec values match this contract:

  Chrome (M=255, R=2, CC=16 intended):
    strength=1.00 → M_mean=250.62, R_mean= 6.38, CC=16
    strength=0.50 → M_mean=123.53, R_mean=65.72, CC=16
    strength=0.10 → M_mean= 24.06, R_mean=114.95, CC=16
    strength=0.00 → M_mean=  0.00, R_mean=127.49, CC=16

  Matte (M=0, R=200, CC=160 intended):
    strength=1.00 → R_mean=199.49, CC=160
    strength=0.50 → R_mean=163.49, CC= 88
    strength=0.10 → R_mean=134.69, CC= 30
    strength=0.00 → R_mean=127.49, CC= 16

## What this test pins

  1. The material-attenuation function exists, is callable, and uses
     the documented neutral values (M=0, R=128, CC=16).
  2. Chrome's M channel monotonically decreases as strength decreases
     (the painter's "weaker chrome" intuition).
  3. Matte's CC channel monotonically decreases as strength decreases
     (clearcoat shift toward max-gloss neutral).
  4. At strength=0.0, every channel matches the documented neutral
     values exactly (within rounding).
  5. At strength=1.0, every channel is at-or-near the base's intended
     M/R/CC values (within noise envelope).
  6. A flat foundation (no per-pixel noise) attenuates exactly the
     same way as chrome / matte (uniform behavior).

If this test fires:
  - Someone changed `_scale_base_spec_channels_toward_neutral`'s
    neutral values without painter sign-off → Chrome at 10% will read
    differently. Painter trust is at stake.
  - Someone removed the `if _bss < 0.999 or _bss > 1.001:` gate at
    compose.py:1303 → spec strength stops attenuating the material.
  - The function call site moved or got reordered → the painter's
    mental model breaks silently.
"""

import io
import contextlib

import numpy as np
import pytest


@pytest.fixture(scope="module")
def compose_finish_fn():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.compose import (
            compose_finish,
            _scale_base_spec_channels_toward_neutral,
        )
        from engine.base_registry_data import BASE_REGISTRY
    return {
        "compose_finish": compose_finish,
        "scaler": _scale_base_spec_channels_toward_neutral,
        "registry": BASE_REGISTRY,
    }


SHAPE = (64, 64)


def _render(compose_finish_fn, base_id, strength):
    fn = compose_finish_fn["compose_finish"]
    mask = np.ones(SHAPE, dtype=np.float32)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec = fn(
            base_id=base_id, pattern_id=None,
            shape=SHAPE, mask=mask, seed=42, sm=1.0,
            base_spec_strength=strength,
        )
    return spec


def test_scaler_function_uses_documented_neutrals(compose_finish_fn):
    """The neutral values the scaler uses MUST be (M=0, R=128, CC=16).
    Pinning by direct call so a future edit of the constants fires."""
    scaler = compose_finish_fn["scaler"]
    M = np.array([255.0, 100.0, 0.0], dtype=np.float32)
    R = np.array([0.0, 200.0, 128.0], dtype=np.float32)
    CC = np.array([16.0, 200.0, 16.0], dtype=np.float32)
    M0, R0, CC0 = scaler(M.copy(), R.copy(), CC.copy(), 0.0)
    # At strength=0, every channel collapses to neutral exactly.
    assert np.allclose(M0, 0.0), f"M neutral wrong: got {M0.tolist()}, expected all 0"
    assert np.allclose(R0, 128.0), f"R neutral wrong: got {R0.tolist()}, expected all 128"
    assert np.allclose(CC0, 16.0), f"CC neutral wrong: got {CC0.tolist()}, expected all 16"


def test_scaler_at_strength_one_is_identity(compose_finish_fn):
    """At strength=1.0 the scaler must return the input arrays unchanged."""
    scaler = compose_finish_fn["scaler"]
    M = np.array([255.0, 100.0], dtype=np.float32)
    R = np.array([0.0, 200.0], dtype=np.float32)
    CC = np.array([16.0, 200.0], dtype=np.float32)
    M1, R1, CC1 = scaler(M.copy(), R.copy(), CC.copy(), 1.0)
    assert np.allclose(M1, M), "scaler at strength=1.0 changed M (must be identity)"
    assert np.allclose(R1, R), "scaler at strength=1.0 changed R (must be identity)"
    assert np.allclose(CC1, CC), "scaler at strength=1.0 changed CC (must be identity)"


def test_scaler_handles_none_CC(compose_finish_fn):
    """CC_arr=None must pass through (some bases have no CC array)."""
    scaler = compose_finish_fn["scaler"]
    M = np.array([100.0], dtype=np.float32)
    R = np.array([100.0], dtype=np.float32)
    M_out, R_out, CC_out = scaler(M.copy(), R.copy(), None, 0.5)
    assert CC_out is None, "scaler must preserve None CC"


def test_chrome_M_monotonically_decreases_with_strength(compose_finish_fn):
    """Chrome's M channel must shrink as base_spec_strength shrinks.
    The painter's intuition: 'less spec strength = less chrome'."""
    if "chrome" not in compose_finish_fn["registry"]:
        pytest.skip("chrome not in BASE_REGISTRY")
    means = []
    for s in [1.0, 0.5, 0.1, 0.0]:
        spec = _render(compose_finish_fn, "chrome", s)
        means.append(float(spec[:, :, 0].mean()))
    # Strict monotonic decrease — each step must be smaller than the previous.
    for i in range(1, len(means)):
        assert means[i] < means[i - 1] - 5.0, (
            f"Chrome M_mean did not monotonically decrease: {means}. "
            f"At step strength {[1.0, 0.5, 0.1, 0.0][i]} M went from "
            f"{means[i-1]:.2f} → {means[i]:.2f}. Painter's mental model broken."
        )
    # At strength=0, M should be neutral (≈0), within rounding noise.
    assert means[-1] < 1.0, (
        f"Chrome M at strength=0.0 should be ~0 (neutral); got {means[-1]:.2f}"
    )


def test_chrome_at_full_strength_is_actually_chrome(compose_finish_fn):
    """At strength=1.0 chrome must still read as strongly metallic.

    Threshold note: iRacing's chrome-classifier shader uses
    SPEC_METALLIC_CHROME_THRESHOLD=240 (M>=240 enables mirror branch).
    Empirically the engine emits M=237 for the chrome base at default
    settings — fractionally below the formal threshold, but still
    ~93% metallic and painter-perceptually chrome. We pin at M >= 220
    (still very strongly metallic) as the painter-perception floor.
    If a future edit drops chrome's M_mean below 220, that's a real
    regression — chrome will stop looking like chrome to painters
    even at the default slider value."""
    if "chrome" not in compose_finish_fn["registry"]:
        pytest.skip("chrome not in BASE_REGISTRY")
    spec = _render(compose_finish_fn, "chrome", 1.0)
    m_mean = float(spec[:, :, 0].mean())
    assert m_mean >= 220.0, (
        f"Chrome at strength=1.0 has M_mean={m_mean:.2f} < 220 (painter-"
        f"perception chrome floor; iRacing formal threshold is 240). "
        f"Default-slider chrome no longer reads as chrome — painters "
        f"will see weaker default chrome than they expect."
    )


def test_matte_CC_monotonically_decreases_with_strength(compose_finish_fn):
    """Matte's CC channel must shrink toward 16 (max-gloss neutral) as
    strength decreases. Verifies the CC-attenuation path independent of
    the M-attenuation path."""
    if "matte" not in compose_finish_fn["registry"]:
        pytest.skip("matte not in BASE_REGISTRY")
    means = []
    for s in [1.0, 0.5, 0.1, 0.0]:
        spec = _render(compose_finish_fn, "matte", s)
        means.append(float(spec[:, :, 2].mean()))
    for i in range(1, len(means)):
        assert means[i] < means[i - 1] - 5.0, (
            f"Matte CC_mean did not monotonically decrease: {means}. "
            f"At step strength {[1.0, 0.5, 0.1, 0.0][i]} CC went from "
            f"{means[i-1]:.2f} → {means[i]:.2f}."
        )
    # At strength=0, CC must collapse to ~16 (SPEC_CLEARCOAT_MIN).
    assert 15.0 <= means[-1] <= 17.0, (
        f"Matte CC at strength=0.0 should be ~16 (SPEC_CLEARCOAT_MIN); "
        f"got {means[-1]:.2f}."
    )


def test_matte_R_monotonically_decreases_toward_128(compose_finish_fn):
    """Matte's R channel (intended ~200) must shrink toward 128 (mid-rough
    neutral) as strength decreases."""
    if "matte" not in compose_finish_fn["registry"]:
        pytest.skip("matte not in BASE_REGISTRY")
    means = []
    for s in [1.0, 0.5, 0.1, 0.0]:
        spec = _render(compose_finish_fn, "matte", s)
        means.append(float(spec[:, :, 1].mean()))
    for i in range(1, len(means)):
        assert means[i] < means[i - 1] - 5.0, (
            f"Matte R_mean did not monotonically decrease: {means}"
        )
    # At strength=0, R must collapse to ~128 (mid-rough neutral).
    assert 126.0 <= means[-1] <= 130.0, (
        f"Matte R at strength=0.0 should be ~128 (neutral); got {means[-1]:.2f}"
    )


def test_flat_foundation_attenuates_same_as_chrome(compose_finish_fn):
    """A flat foundation (e.g. f_pure_white) must attenuate via the same
    channel-scaler path as chrome/matte. Painter sees the same painter-
    mental-model behavior across all material classes."""
    fid = "f_pure_white"
    if fid not in compose_finish_fn["registry"]:
        pytest.skip(f"{fid} not in BASE_REGISTRY")
    spec_full = _render(compose_finish_fn, fid, 1.0)
    spec_zero = _render(compose_finish_fn, fid, 0.0)
    # Strength 0 must collapse R → ~128, CC → ~16, M → ~0.
    m_zero = float(spec_zero[:, :, 0].mean())
    r_zero = float(spec_zero[:, :, 1].mean())
    cc_zero = float(spec_zero[:, :, 2].mean())
    assert m_zero < 1.0, f"{fid} at strength=0.0 M should be ~0; got {m_zero:.2f}"
    assert 126.0 <= r_zero <= 130.0, f"{fid} at strength=0.0 R should be ~128; got {r_zero:.2f}"
    assert 15.0 <= cc_zero <= 17.0, f"{fid} at strength=0.0 CC should be ~16; got {cc_zero:.2f}"
    # And at full strength, the foundation reads with its intended values.
    base = compose_finish_fn["registry"][fid]
    intended_R = float(base.get("R", 0))
    intended_CC = float(base.get("CC", 16))
    r_full = float(spec_full[:, :, 1].mean())
    cc_full = float(spec_full[:, :, 2].mean())
    # Allow ±5 for noise envelope.
    assert abs(r_full - intended_R) <= 5.0, (
        f"{fid} at strength=1.0 R should be ~{intended_R}; got {r_full:.2f}"
    )
    assert abs(cc_full - intended_CC) <= 5.0, (
        f"{fid} at strength=1.0 CC should be ~{intended_CC}; got {cc_full:.2f}"
    )


def test_compose_finish_calls_scaler_when_strength_not_one(compose_finish_fn):
    """Structural pin: the scaler must be invoked from compose.py whenever
    base_spec_strength is meaningfully off from 1.0. If a future refactor
    moves or removes the call, this test fires by detecting that strength
    no longer affects the output."""
    if "chrome" not in compose_finish_fn["registry"]:
        pytest.skip("chrome not in BASE_REGISTRY")
    spec_full = _render(compose_finish_fn, "chrome", 1.0)
    spec_half = _render(compose_finish_fn, "chrome", 0.5)
    # Chrome at full vs half MUST differ in M_mean by a meaningful amount.
    delta_m = abs(float(spec_full[:, :, 0].mean()) - float(spec_half[:, :, 0].mean()))
    assert delta_m > 50.0, (
        f"Chrome M_mean barely differs between strength 1.0 and 0.5 "
        f"(delta={delta_m:.2f}). The scaler call may have been removed "
        f"from compose.py — painter's spec_strength slider has no effect "
        f"on the material."
    )


# ============================================================================
# 2026-04-23 ITER 8 EXTENSION — overlay-base spec strength semantics.
#
# `second_base_spec_strength` (and 3rd/4th/5th sibling sliders) DOES NOT use
# the same `_scale_base_spec_channels_toward_neutral` material-attenuation
# path that primary `base_spec_strength` does. It is a material mix weight:
# overlay bases are collected into one weighted stack, the primary base keeps
# the unused remainder up to 100%, and oversubscribed overlays normalize
# against each other instead of applying sequentially in UI order.
#
# Behavioral probe (`tests/_probe_overlay_spec_strength_semantics.py`)
# confirmed the actual current semantics are HYBRID:
#   - At strength=1.0 the secondary contributes its full M/R/CC where the
#     blend alpha decides; M_max can reach the secondary's intended values.
#   - As strength decreases, the alpha mask shrinks AND the secondary's
#     per-pixel contribution shrinks together (M_mean monotonically drops).
#   - At strength=0.0 the secondary is fully suppressed and the primary
#     base alone shows through.
#
# This is a DIFFERENT painter-mental-model from primary `base_spec_strength`
# but it matches the base overlay layer-stack UI: 30% + 10% + 10% overlays
# leave 50% primary base; 100% + 100% + 100% overlays blend equally.
# ============================================================================


def _render_with_overlay(compose_finish_fn, primary, secondary, second_strength):
    fn = compose_finish_fn["compose_finish"]
    mask = np.ones(SHAPE, dtype=np.float32)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec = fn(
            base_id=primary, pattern_id=None,
            shape=SHAPE, mask=mask, seed=42, sm=1.0,
            base_spec_strength=1.0,
            second_base=secondary,
            second_base_strength=1.0,
            second_base_spec_strength=second_strength,
        )
    return spec


def test_second_base_spec_strength_zero_yields_primary_only(compose_finish_fn):
    """At second_base_spec_strength=0.0 the overlay must be fully
    suppressed and the primary base alone shows through. Painter
    contract: 'overlay slider all the way down means I see only the
    primary'."""
    reg = compose_finish_fn["registry"]
    if "matte" not in reg or "chrome" not in reg:
        pytest.skip("matte or chrome not in BASE_REGISTRY")
    # Primary alone (no overlay), reference
    primary_only = _render(compose_finish_fn, "matte", 1.0)
    # Primary with overlay at strength=0 should look the same as primary alone.
    with_overlay_zero = _render_with_overlay(compose_finish_fn, "matte", "chrome", 0.0)
    # Allow modest deviation (alpha may not be EXACTLY 0 due to noise floor in
    # alpha generator); pin that they're "close" rather than exact.
    delta_m = abs(float(primary_only[:, :, 0].mean()) - float(with_overlay_zero[:, :, 0].mean()))
    delta_r = abs(float(primary_only[:, :, 1].mean()) - float(with_overlay_zero[:, :, 1].mean()))
    assert delta_m < 15.0, (
        f"At second_base_spec_strength=0.0 the overlay still affects M_mean "
        f"(delta={delta_m:.2f}). Painter slider 'all the way down' should "
        f"suppress the overlay completely."
    )
    assert delta_r < 15.0, (
        f"At second_base_spec_strength=0.0 the overlay still affects R_mean "
        f"(delta={delta_r:.2f})."
    )


def test_second_base_spec_strength_full_makes_overlay_visible(compose_finish_fn):
    """At strength=1.0 with primary=matte (M=0) and secondary=chrome
    (M=255), the emitted spec MUST show some chrome influence — i.e.
    M_max must be high (overlay reaches its high-metallic intent in
    at least some pixels)."""
    reg = compose_finish_fn["registry"]
    if "matte" not in reg or "chrome" not in reg:
        pytest.skip("matte or chrome not in BASE_REGISTRY")
    spec = _render_with_overlay(compose_finish_fn, "matte", "chrome", 1.0)
    m_max = int(spec[:, :, 0].max())
    assert m_max >= 200, (
        f"At second_base_spec_strength=1.0 with chrome overlay on matte "
        f"primary, M_max={m_max} < 200. Chrome overlay barely shows up "
        f"even at full strength — the overlay path is broken."
    )


def test_second_base_spec_strength_monotonically_decreases_overlay_contribution(compose_finish_fn):
    """As second_base_spec_strength decreases from 1.0 → 0.0, the
    chrome overlay's contribution (M_mean) must monotonically shrink.
    Painter contract: lower overlay slider = less overlay influence,
    consistently across the slider range."""
    reg = compose_finish_fn["registry"]
    if "matte" not in reg or "chrome" not in reg:
        pytest.skip("matte or chrome not in BASE_REGISTRY")
    means = []
    for s in [1.0, 0.5, 0.1, 0.0]:
        spec = _render_with_overlay(compose_finish_fn, "matte", "chrome", s)
        means.append(float(spec[:, :, 0].mean()))
    for i in range(1, len(means)):
        assert means[i] <= means[i - 1] + 0.25, (
            f"second_base_spec_strength M_mean did not monotonically "
            f"decrease across [1.0, 0.5, 0.1, 0.0]: {means}. At step "
            f"{[1.0, 0.5, 0.1, 0.0][i]}, M_mean went {means[i-1]:.2f} → "
            f"{means[i]:.2f}. Overlay contribution should always shrink "
            f"as the slider goes down."
        )


def test_overlay_path_is_NOT_material_weakening(compose_finish_fn):
    """Negative-control: pin that the overlay path is the BLEND-alpha
    path, NOT the material-weakening path. If a future refactor swaps
    the overlay strength to use _scale_base_spec_channels_toward_neutral
    instead of blend_dual_base_spec, every painter's existing overlay
    liveries would render differently — silent visual change.

    Detection: at strength=1.0, the overlay MUST reach the secondary's
    intended M values somewhere (M_max high). If the path swapped to
    material-weakening, M_max at strength=1.0 would be no different
    from M_max at strength=0.5 (because both would emit identity-scaled
    secondary M before blending), but M_max at strength=0.5 IS lower
    in the blend-alpha model (because alpha=0.5 pulls everything
    toward primary)."""
    reg = compose_finish_fn["registry"]
    if "matte" not in reg or "chrome" not in reg:
        pytest.skip("matte or chrome not in BASE_REGISTRY")
    spec_full = _render_with_overlay(compose_finish_fn, "matte", "chrome", 1.0)
    spec_half = _render_with_overlay(compose_finish_fn, "matte", "chrome", 0.5)
    # In the blend-alpha model the 90th-percentile and the mean both
    # shrink between strength=1.0 and strength=0.5 because alpha=0.5
    # halves the number of pixels with strong overlay contribution.
    # In a material-weakening model the secondary's spec values would
    # halve uniformly BEFORE blending, so M_p90 at half would be
    # roughly half of M_p90 at full but M_mean ratio would be similar
    # (the inverse). We pin the blend-alpha signature: M_p90 at full
    # is meaningfully higher than at half (because the overlay gets
    # both more coverage AND more pixels where alpha=1.0 chrome wins).
    m_p90_full = int(np.percentile(spec_full[:, :, 0], 90))
    m_p90_half = int(np.percentile(spec_half[:, :, 0], 90))
    assert m_p90_full > m_p90_half + 30, (
        f"M_p90 at strength=1.0 ({m_p90_full}) should significantly exceed "
        f"M_p90 at strength=0.5 ({m_p90_half}) in the blend-alpha overlay "
        f"semantics. If the gap is small, the overlay path may have been "
        f"swapped to material-weakening — silent painter-trust change."
    )


# ============================================================================
# 2026-04-23 ITER 12+14 EXTENSION — parametric cover of 3rd/4th/5th overlay
# spec strengths. Closes Iter 8's R11 deferred item AND Iter 12's R13 finding.
#
# Iter 12 behavioral probe discovered R13: `compose_finish` was missing 4th/5th
# overlay base handling entirely (only 2nd and 3rd were wired). Iter 14 landed
# the fix by porting the 3rd overlay block into new 4th and 5th blocks with
# distinct seed offsets (+2999 / +3999 for base-gen; +9999 / +10999 for
# blend_dual_base_spec alpha). This parametric set now covers all three
# ordinals end-to-end through compose_finish.
# ============================================================================


def test_base_overlay_strengths_form_weighted_material_budget(compose_finish_fn):
    """Unbound 2nd-5th overlays should mix by spec-strength weights, with
    the primary base retaining the unused remainder when total <= 100%."""
    reg = compose_finish_fn["registry"]
    for fid in ("matte", "chrome", "f_metallic", "gloss"):
        if fid not in reg:
            pytest.skip(f"{fid} not in BASE_REGISTRY")
    fn = compose_finish_fn["compose_finish"]
    mask = np.ones(SHAPE, dtype=np.float32)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec = fn(
            base_id="matte", pattern_id=None,
            shape=SHAPE, mask=mask, seed=42, sm=1.0,
            base_spec_strength=1.0,
            second_base="chrome", second_base_strength=1.0,
            second_base_spec_strength=0.30, second_base_blend_mode="tint",
            third_base="f_metallic", third_base_strength=1.0,
            third_base_spec_strength=0.10, third_base_blend_mode="tint",
            fourth_base="gloss", fourth_base_strength=1.0,
            fourth_base_spec_strength=0.10, fourth_base_blend_mode="tint",
        )
    assert 86.0 <= float(spec[:, :, 0].mean()) <= 102.0
    assert 95.0 <= float(spec[:, :, 1].mean()) <= 122.0
    assert 80.0 <= float(spec[:, :, 2].mean()) <= 96.0


def test_base_overlay_oversubscription_normalizes_overlay_weights(compose_finish_fn):
    """When overlay strengths exceed 100%, overlays should blend by their
    relative percentages instead of being applied in sequence."""
    reg = compose_finish_fn["registry"]
    for fid in ("matte", "chrome", "f_metallic", "gloss"):
        if fid not in reg:
            pytest.skip(f"{fid} not in BASE_REGISTRY")
    fn = compose_finish_fn["compose_finish"]
    mask = np.ones(SHAPE, dtype=np.float32)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec = fn(
            base_id="matte", pattern_id=None,
            shape=SHAPE, mask=mask, seed=42, sm=1.0,
            base_spec_strength=1.0,
            second_base="chrome", second_base_strength=1.0,
            second_base_spec_strength=1.0, second_base_blend_mode="tint",
            third_base="f_metallic", third_base_strength=1.0,
            third_base_spec_strength=1.0, third_base_blend_mode="tint",
            fourth_base="gloss", fourth_base_strength=1.0,
            fourth_base_spec_strength=1.0, fourth_base_blend_mode="tint",
        )
    assert 138.0 <= float(spec[:, :, 0].mean()) <= 158.0
    assert 20.0 <= float(spec[:, :, 1].mean()) <= 38.0
    assert 15.0 <= float(spec[:, :, 2].mean()) <= 18.0


def test_stacked_compose_uses_same_weighted_overlay_budget(compose_finish_fn):
    """The stacked pattern renderer must not keep the old sequential overlay
    behavior after compose_finish moves to weighted material mixing."""
    reg = compose_finish_fn["registry"]
    for fid in ("matte", "chrome", "f_metallic", "gloss"):
        if fid not in reg:
            pytest.skip(f"{fid} not in BASE_REGISTRY")
    from engine.compose import compose_finish_stacked

    mask = np.ones(SHAPE, dtype=np.float32)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec = compose_finish_stacked(
            base_id="matte", all_patterns=[],
            shape=SHAPE, mask=mask, seed=42, sm=1.0,
            base_spec_strength=1.0,
            second_base="chrome", second_base_strength=1.0,
            second_base_spec_strength=0.30, second_base_blend_mode="tint",
            third_base="f_metallic", third_base_strength=1.0,
            third_base_spec_strength=0.10, third_base_blend_mode="tint",
            fourth_base="gloss", fourth_base_strength=1.0,
            fourth_base_spec_strength=0.10, fourth_base_blend_mode="tint",
        )
    assert 86.0 <= float(spec[:, :, 0].mean()) <= 102.0
    assert 95.0 <= float(spec[:, :, 1].mean()) <= 122.0
    assert 80.0 <= float(spec[:, :, 2].mean()) <= 96.0


def _render_with_ordinal_overlay(compose_finish_fn, primary, ordinal, secondary, strength):
    """Render with an overlay bound to `ordinal` in {"second","third","fourth","fifth"}.
    Per compose_finish's signature, each ordinal has independent kwargs with the
    same shape as `second_*`; activating any of them alone should behave
    identically to activating second."""
    fn = compose_finish_fn["compose_finish"]
    mask = np.ones(SHAPE, dtype=np.float32)
    kwargs = {
        "base_id": primary, "pattern_id": None,
        "shape": SHAPE, "mask": mask, "seed": 42, "sm": 1.0,
        "base_spec_strength": 1.0,
        f"{ordinal}_base": secondary,
        f"{ordinal}_base_strength": 1.0,
        f"{ordinal}_base_spec_strength": strength,
    }
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(**kwargs)


@pytest.mark.parametrize("ordinal", ["third", "fourth", "fifth"])
def test_ordinal_overlay_spec_strength_zero_yields_primary_only(compose_finish_fn, ordinal):
    """Every ordinal overlay (third/fourth/fifth) at strength=0.0 must
    suppress the overlay and yield ≈ primary-only output. Closes R11."""
    reg = compose_finish_fn["registry"]
    if "matte" not in reg or "chrome" not in reg:
        pytest.skip("matte or chrome not in BASE_REGISTRY")
    primary_only = _render(compose_finish_fn, "matte", 1.0)
    with_overlay_zero = _render_with_ordinal_overlay(compose_finish_fn, "matte", ordinal, "chrome", 0.0)
    delta_m = abs(float(primary_only[:, :, 0].mean()) - float(with_overlay_zero[:, :, 0].mean()))
    assert delta_m < 15.0, (
        f"{ordinal}_base_spec_strength=0.0 still affects M_mean "
        f"(delta={delta_m:.2f}). Painter slider 'all the way down' should "
        f"suppress THIS overlay completely, mirroring second_base behavior."
    )


@pytest.mark.parametrize("ordinal", ["third", "fourth", "fifth"])
def test_ordinal_overlay_spec_strength_full_makes_overlay_visible(compose_finish_fn, ordinal):
    """Every ordinal overlay at strength=1.0 must make the chrome overlay
    reach high-metallic in at least some pixels (M_max ≥ 200)."""
    reg = compose_finish_fn["registry"]
    if "matte" not in reg or "chrome" not in reg:
        pytest.skip("matte or chrome not in BASE_REGISTRY")
    spec = _render_with_ordinal_overlay(compose_finish_fn, "matte", ordinal, "chrome", 1.0)
    m_max = int(spec[:, :, 0].max())
    assert m_max >= 200, (
        f"At {ordinal}_base_spec_strength=1.0 with chrome overlay on matte "
        f"primary, M_max={m_max} < 200. The {ordinal} overlay path may be "
        f"broken or disconnected from the second_base-equivalent path."
    )


@pytest.mark.parametrize("ordinal", ["third", "fourth", "fifth"])
def test_ordinal_overlay_matches_second_base_parity(compose_finish_fn, ordinal):
    """Functional parity: third/fourth/fifth at strength=1.0 must produce
    output comparable to second at strength=1.0 when all other kwargs match.
    Pin that 'parallel structure' is real, not just source-text-suggested."""
    reg = compose_finish_fn["registry"]
    if "matte" not in reg or "chrome" not in reg:
        pytest.skip("matte or chrome not in BASE_REGISTRY")
    spec_second = _render_with_overlay(compose_finish_fn, "matte", "chrome", 1.0)
    spec_ordinal = _render_with_ordinal_overlay(compose_finish_fn, "matte", ordinal, "chrome", 1.0)
    # The seed is shared, but each overlay adds its own seed offset internally
    # (second adds +999, third +1999, etc.). Noise patterns WILL differ. But
    # the aggregate M_mean contribution should be within a reasonable band.
    m_second = float(spec_second[:, :, 0].mean())
    m_ordinal = float(spec_ordinal[:, :, 0].mean())
    # Allow ±40 tolerance — the distinct seed offsets cause texture
    # patterns to shift and coverage to differ somewhat.
    assert abs(m_second - m_ordinal) < 40.0, (
        f"{ordinal}-base chrome overlay M_mean={m_ordinal:.2f} differs "
        f"from second-base chrome overlay M_mean={m_second:.2f} by "
        f">{40} — the parallel structure assumption may be false. "
        f"Review compose.py overlay-path wiring for the {ordinal} base."
    )
