"""HEENAN AUTO-LOOP — autonomous-continuation ratchets.

Each /loop iteration that widens an engine parameter set pins the
minimum dM/dR here so future shifts cannot silently regress.

Every test is deterministic (fixed seeds, fixed shapes) and runs in the
default pytest session.
"""

import numpy as np
import pytest


# ─── HARDMODE FOUNDATION-VISIBILITY RATCHETS — REMOVED 2026-04-21 ─────
#
# The 8 tests originally here (test_enh_metallic_flake_depth_visible,
# test_enh_pearl_nacre_cc_visible, test_enh_carbon_fiber_resin_pool_visible,
# test_enh_semi_gloss_has_surface_nuance, test_enh_soft_gloss_has_shimmer_variation,
# test_enh_piano_black_has_mirror_depth_variation, test_enh_gloss_has_wet_ripple_variation,
# and the chrome-flake variants) were written by the HARDMODE auto-loop
# to PIN minimum dM/dR/dCC variances on Foundation Bases. Those ratchets
# were enforcing the WRONG design intent.
#
# Painter clarification (2026-04-21): "The FOUNDATION FUCKING BASES are
# supposed to be vanilla. Metallic just LOOKS metallic - whatever the
# color is. It doesn't change the color - it doesn't add its own textures
# to the spec map. NONE of the foundation bases are supposed to do
# ANYTHING other than change the texture/look of the color it's
# affecting."
#
# Foundation Bases are now FLAT. The correct guardrail is:
#   tests/test_regression_foundation_spec_flatness.py
# which asserts the OPPOSITE — that no Foundation Base produces visible
# variance beyond the sub-perceptible ±1 anti-banding dither.
#
# The pattern-visibility tests below (scarab_gold, butterfly_morpho,
# anime_*, neon_*, etc.) ARE legitimate — patterns SHOULD be visible.
# Foundations are not patterns.


# Sentinel: ensure ALL enh_* foundation variance ratchets stay out
# of this file. Any `test_enh_*` function is forbidden here — the
# design intent was formally inverted by painter mandate: Foundation
# Bases are FLAT, not variable. The correct foundation guardrail
# lives in tests/test_regression_foundation_spec_flatness.py.
#
# Pre-2026-04-22 this sentinel filtered only `test_enh_*_visible`
# names; that missed 4 obsolete ratchets whose names did NOT contain
# "visible" (semi_gloss/soft_gloss/piano_black/baked_enamel/gloss/
# gel_coat/ceramic_glaze/wet_look/etc.). Broadening the filter catches
# the whole family.
def test_no_enh_foundation_ratchets_in_this_file():
    """If a future contributor adds any `test_enh_*` function back into
    this file, fail loudly — Foundations are flat by painter mandate.

    Legitimate pattern-visibility tests (scarab/butterfly/moth/neon/
    anime/…) do NOT use the `enh_` prefix, so they pass this sentinel."""
    import sys
    mod = sys.modules[__name__]
    bad = [n for n in dir(mod) if n.startswith("test_enh_")]
    assert not bad, (
        "Foundation-variance (`test_enh_*`) ratchets reintroduced: "
        f"{bad}. Foundations are flat — see "
        "tests/test_regression_foundation_spec_flatness.py for the "
        "correct flat-only Foundation guardrail and the painter "
        "rationale. If someone is intentionally adding a non-variance "
        "test with the test_enh_* prefix, rename it to something else."
    )


def _disabled_obsolete_enh_metallic_flake_depth_visible_template(seed, shape):
    """OBSOLETE / DISABLED — kept as a comment-form record of the
    pre-pivot HARDMODE assertion shape so reviewers can find it via
    grep. Do NOT re-enable."""
    from engine.paint_v2.foundation_enhanced import spec_enh_metallic
    M, R, CC = spec_enh_metallic(shape, seed, 1.0, 200, 45)
    dCC = float(CC.max() - CC.min())
    assert dCC >= 12.0, f"enh_metallic dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=12)"


# ─── Foundation-variance ratchets DELETED 2026-04-22 HEENAN FAMILY iter 5 ───
#
# The following 6 `test_enh_*` functions used to live here and asserted
# minimum dM/dR/dCC spreads on Foundation Base spec output:
#
#   test_enh_pearl_nacre_cc_visible
#   test_enh_carbon_fiber_resin_pool_visible
#   test_enh_semi_gloss_has_surface_nuance
#   test_enh_soft_gloss_has_shimmer_variation
#   test_enh_piano_black_has_mirror_depth_variation
#   test_enh_gloss_has_wet_ripple_variation
#
# All six contradicted the painter-mandated Foundation flat-spec
# contract ("Foundation Bases are vanilla — no texture, no recoloring").
# They were written by an earlier HARDMODE auto-loop that assumed
# variable foundations; the painter subsequently inverted the intent.
# Removed in iter 5 after Raven's sweep caught them — each was a
# sentinel-tripping dead-green when the design contract flipped.


# ─── AUTO-LOOP-22 — scarab_gold iridescent shell R/CC contrast ────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_scarab_gold_shell_contrast_visible(seed, shape):
    """scarab_gold: Egyptian scarab gold↔green iridescence. Pre-AUTO-
    LOOP-22 dR=19 dCC=12. Pin dR>=48, dCC>=22 (dM already strong)."""
    from engine.paint_v2.iridescent_insects import spec_scarab_gold
    M, R, CC = spec_scarab_gold(shape, seed, 1.0, 240, 15)
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dR >= 48.0, f"scarab_gold dR = {dR:.1f} at seed={seed}, shape={shape} (want >=48)"
    assert dCC >= 22.0, f"scarab_gold dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=22)"


# ─── AUTO-LOOP-21 — butterfly_morpho angle-flash roughness contrast ───

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_butterfly_morpho_roughness_contrast_visible(seed, shape):
    """butterfly_morpho: Morpho structural-color angle flash. Pre-
    AUTO-LOOP-21 dR=15 (too flat for roughness-driven angle effect).
    Pin dR>=40, dCC>=18 (dM already strong at 140+)."""
    from engine.paint_v2.iridescent_insects import spec_butterfly_morpho
    M, R, CC = spec_butterfly_morpho(shape, seed, 1.0, 240, 20)
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dR >= 40.0, f"butterfly_morpho dR = {dR:.1f} at seed={seed}, shape={shape} (want >=40)"
    assert dCC >= 18.0, f"butterfly_morpho dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=18)"


# ─── AUTO-LOOP-20 — moth_luna eye-spot pop ────────────────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_moth_luna_eye_spots_visible(seed, shape):
    """moth_luna: fuzzy wing with eye-spots. Pre-AUTO-LOOP-20 dM=80.
    Pin dM>=160, dR>=110, dCC>=65."""
    from engine.paint_v2.iridescent_insects import spec_moth_luna
    M, R, CC = spec_moth_luna(shape, seed, 1.0, 240, 25)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 160.0, f"moth_luna dM = {dM:.1f} at seed={seed}, shape={shape} (want >=160)"
    assert dR >= 110.0, f"moth_luna dR = {dR:.1f} at seed={seed}, shape={shape} (want >=110)"
    assert dCC >= 65.0, f"moth_luna dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=65)"


# ─── AUTO-LOOP-19 — wasp_warning band contrast ─────────────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_wasp_warning_band_contrast_visible(seed, shape):
    """wasp_warning: yellow/black hazard bands. Pre-AUTO-LOOP-19
    dM=60 dR=50 dCC=30. Pin dM>=190, dR>=55, dCC>=40."""
    from engine.paint_v2.iridescent_insects import spec_wasp_warning
    M, R, CC = spec_wasp_warning(shape, seed, 1.0, 240, 15)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 190.0, f"wasp_warning dM = {dM:.1f} at seed={seed}, shape={shape} (want >=190)"
    assert dR >= 55.0, f"wasp_warning dR = {dR:.1f} at seed={seed}, shape={shape} (want >=55)"
    assert dCC >= 40.0, f"wasp_warning dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=40)"


# ─── AUTO-LOOP-18 — butterfly_monarch satiny vs matte wing contrast ────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_butterfly_monarch_wing_contrast_visible(seed, shape):
    """butterfly_monarch: orange wing zones vs dark vein seams.
    Pre-AUTO-LOOP-18 dM=55 (wings and veins too similar metallic).
    Pin dM>=160 so wings read satin-metallic vs matte-dielectric veins."""
    from engine.paint_v2.iridescent_insects import spec_butterfly_monarch
    M, R, CC = spec_butterfly_monarch(shape, seed, 1.0, 240, 20)
    dM = float(M.max() - M.min())
    assert dM >= 160.0, f"butterfly_monarch dM = {dM:.1f} at seed={seed}, shape={shape} (want >=160)"


# ─── AUTO-LOOP-17 — beetle_rainbow iridescent shell depth ──────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_beetle_rainbow_iridescence_visible_in_spec(seed, shape):
    """beetle_rainbow: iridescent shell finish. Pre-AUTO-LOOP-17
    dM=50 dR=15 dCC=8. Pin dM>=110, dR>=25, dCC>=18."""
    from engine.paint_v2.iridescent_insects import spec_beetle_rainbow
    M, R, CC = spec_beetle_rainbow(shape, seed, 1.0, 240, 20)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 110.0, f"beetle_rainbow dM = {dM:.1f} at seed={seed}, shape={shape} (want >=110)"
    assert dR >= 25.0, f"beetle_rainbow dR = {dR:.1f} at seed={seed}, shape={shape} (want >=25)"
    assert dCC >= 18.0, f"beetle_rainbow dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=18)"


# ─── AUTO-LOOP-16 — anime_comic_halftone ink vs paper contrast ──────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_anime_comic_halftone_ink_visible_in_spec(seed, shape):
    """anime_comic_halftone: magenta ink dots on paper. Pre-AUTO-LOOP-16
    dM=80 dR=50 dCC=20. Pin dM>=150, dR>=80, dCC>=35 (deterministic
    binary dot mask)."""
    from engine.paint_v2.anime_style import spec_anime_comic_halftone
    M, R, CC = spec_anime_comic_halftone(shape, seed, 1.0, 240, 25)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 150.0, f"anime_comic_halftone dM = {dM:.1f} at seed={seed}, shape={shape} (want >=150)"
    assert dR >= 80.0, f"anime_comic_halftone dR = {dR:.1f} at seed={seed}, shape={shape} (want >=80)"
    assert dCC >= 35.0, f"anime_comic_halftone dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=35)"


# ─── AUTO-LOOP-15 — anime_sakura_scatter petal contrast ─────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_anime_sakura_scatter_petals_visible_in_spec(seed, shape):
    """anime_sakura_scatter: cherry-blossom petals on bg. Weakest
    anime_style spec baseline (dM=60 dR=20 dCC=8). Pin dM>=110,
    dR>=32, dCC>=18."""
    from engine.paint_v2.anime_style import spec_anime_sakura_scatter
    M, R, CC = spec_anime_sakura_scatter(shape, seed, 1.0, 240, 20)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 110.0, f"anime_sakura_scatter dM = {dM:.1f} at seed={seed}, shape={shape} (want >=110)"
    assert dR >= 32.0, f"anime_sakura_scatter dR = {dR:.1f} at seed={seed}, shape={shape} (want >=32)"
    assert dCC >= 18.0, f"anime_sakura_scatter dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=18)"


# ─── AUTO-LOOP-14 — neon_cyber_yellow circuit grid depth ─────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_cyber_yellow_circuit_visible_in_spec(seed, shape):
    """neon_cyber_yellow: cyberpunk H+V circuit grid. Pre-AUTO-LOOP-14
    dM=15 dR=4 dCC=0. Pin dM>=35, dR>=22, dCC>=16."""
    from engine.paint_v2.neon_underground import spec_neon_cyber_yellow
    M, R, CC = spec_neon_cyber_yellow(shape, seed, 1.0, 240, 16)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 35.0, f"neon_cyber_yellow dM = {dM:.1f} at seed={seed}, shape={shape} (want >=35)"
    assert dR >= 22.0, f"neon_cyber_yellow dR = {dR:.1f} at seed={seed}, shape={shape} (want >=22)"
    assert dCC >= 16.0, f"neon_cyber_yellow dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=16)"


# ─── AUTO-LOOP-13 — neon_orange_hazard diagonal stripe split ─────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_orange_hazard_stripes_visible_in_spec(seed, shape):
    """neon_orange_hazard: construction-tape diagonal stripe. Pre-AUTO-
    LOOP-13 dM=15 dR=5 dCC=0. Pin dM>=38, dR>=25, dCC>=20 (binary
    stripe so the amplitude is deterministic)."""
    from engine.paint_v2.neon_underground import spec_neon_orange_hazard
    M, R, CC = spec_neon_orange_hazard(shape, seed, 1.0, 240, 15)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 38.0, f"neon_orange_hazard dM = {dM:.1f} at seed={seed}, shape={shape} (want >=38)"
    assert dR >= 25.0, f"neon_orange_hazard dR = {dR:.1f} at seed={seed}, shape={shape} (want >=25)"
    assert dCC >= 20.0, f"neon_orange_hazard dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=20)"


# ─── AUTO-LOOP-12 — neon_electric_blue plasma vein depth ─────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_electric_blue_veins_visible_in_spec(seed, shape):
    """neon_electric_blue: plasma discharge veins. Pre-AUTO-LOOP-12
    had dM=15 dR=3 dCC=0 — vein field computed but amplitude hid
    the pattern. Pin dM>=30, dR>=22, dCC>=15."""
    from engine.paint_v2.neon_underground import spec_neon_electric_blue
    M, R, CC = spec_neon_electric_blue(shape, seed, 1.0, 240, 17)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 30.0, f"neon_electric_blue dM = {dM:.1f} at seed={seed}, shape={shape} (want >=30)"
    assert dR >= 22.0, f"neon_electric_blue dR = {dR:.1f} at seed={seed}, shape={shape} (want >=22)"
    assert dCC >= 15.0, f"neon_electric_blue dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=15)"


# ─── AUTO-LOOP-11 — neon_red_alert radial siren pulse depth ──────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_red_alert_siren_visible_in_spec(seed, shape):
    """neon_red_alert: radial siren-pulse rings. Pre-AUTO-LOOP-11 had
    dM=12 dR=5 dCC=0. Pin dM>=28, dR>=20, dCC>=15."""
    from engine.paint_v2.neon_underground import spec_neon_red_alert
    M, R, CC = spec_neon_red_alert(shape, seed, 1.0, 243, 15)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 28.0, f"neon_red_alert dM = {dM:.1f} at seed={seed}, shape={shape} (want >=28)"
    assert dR >= 20.0, f"neon_red_alert dR = {dR:.1f} at seed={seed}, shape={shape} (want >=20)"
    assert dCC >= 15.0, f"neon_red_alert dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=15)"


# ─── AUTO-LOOP-10 — neon_rainbow_tube horizontal band depth ───────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_rainbow_tube_bands_visible_in_spec(seed, shape):
    """neon_rainbow_tube desc: 'full spectrum neon tube with horizontal
    banding'. Pre-AUTO-LOOP-10 had dM=10 dR=5 dCC=0 — bands invisible
    in spec. Pin dM>=28, dR>=20, dCC>=15."""
    from engine.paint_v2.neon_underground import spec_neon_rainbow_tube
    M, R, CC = spec_neon_rainbow_tube(shape, seed, 1.0, 245, 15)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 28.0, f"neon_rainbow_tube dM = {dM:.1f} at seed={seed}, shape={shape} (want >=28)"
    assert dR >= 20.0, f"neon_rainbow_tube dR = {dR:.1f} at seed={seed}, shape={shape} (want >=20)"
    assert dCC >= 15.0, f"neon_rainbow_tube dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=15)"


# ─── AUTO-LOOP-9 — neon_toxic_green geiger hotspot depth ──────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_toxic_green_hotspots_visible_in_spec(seed, shape):
    """neon_toxic_green desc: 'radioactive green with Geiger-counter
    scatter particles — random hot spots'. Pre-AUTO-LOOP-9 had
    dM=10 dR=5 dCC=0 — hot spots computed but invisible in spec.
    Pin dM>=28, dR>=20, dCC>=15."""
    from engine.paint_v2.neon_underground import spec_neon_toxic_green
    M, R, CC = spec_neon_toxic_green(shape, seed, 1.0, 245, 15)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 28.0, f"neon_toxic_green dM = {dM:.1f} at seed={seed}, shape={shape} (want >=28)"
    assert dR >= 20.0, f"neon_toxic_green dR = {dR:.1f} at seed={seed}, shape={shape} (want >=20)"
    assert dCC >= 15.0, f"neon_toxic_green dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=15)"


# ─── AUTO-LOOP-8 — neon_ice_white dendrite depth ──────────────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_ice_white_dendrite_visible_in_spec(seed, shape):
    """neon_ice_white desc promises 'frost crystallization — dendritic
    ice crystal growth pattern'. Pre-AUTO-LOOP-8 had dM=7, dR=5, dCC=0
    — dendrite field existed but spec amplitude was below perceptual
    threshold. Pin dM>=25, dR>=20, dCC>=15."""
    from engine.paint_v2.neon_underground import spec_neon_ice_white
    M, R, CC = spec_neon_ice_white(shape, seed, 1.0, 248, 15)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 25.0, f"neon_ice_white dM = {dM:.1f} at seed={seed}, shape={shape} (want >=25)"
    assert dR >= 20.0, f"neon_ice_white dR = {dR:.1f} at seed={seed}, shape={shape} (want >=20)"
    assert dCC >= 15.0, f"neon_ice_white dCC = {dCC:.1f} at seed={seed}, shape={shape} (want >=15)"


# ─── AUTO-LOOP-7 — neon_dual_glow pink/blue split parity ───────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_dual_glow_split_visible_in_spec(seed, shape):
    """neon_dual_glow desc promises 'dual pink-blue glow with sharp
    diagonal split'. Pre-AUTO-LOOP-7 the spec formula was degenerate:
    M = 242+split*10+(1-split)*8 collapsed both sides to ~250..252
    producing dM=2 (completely unusable for dual-side identity).
    Pin dM>=30, dR>=24, dCC>=18.
    """
    from engine.paint_v2.neon_underground import spec_neon_dual_glow
    M, R, CC = spec_neon_dual_glow(shape, seed, 1.0, 242, 16)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 30.0, (
        f"neon_dual_glow dM = {dM:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 30 (AUTO-LOOP-7 pinned 35)."
    )
    assert dR >= 24.0, (
        f"neon_dual_glow dR = {dR:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 24 (AUTO-LOOP-7 pinned 30)."
    )
    assert dCC >= 18.0, (
        f"neon_dual_glow dCC = {dCC:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 18 (AUTO-LOOP-7 pinned 24)."
    )


# ─── AUTO-LOOP-6 — neon_blacklight inverse UV response depth ───────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_blacklight_uv_response_visible_in_spec(seed, shape):
    """neon_blacklight desc promises 'UV-reactive purple that glows in
    dark zones — inverse brightness response'. Pre-AUTO-LOOP-6 had
    dM=11, dR=2, dCC=0 (uv_response was computed but spec amplitude
    was perceptually flat). Pin dM>=30, dR>=24, dCC>=16.
    """
    from engine.paint_v2.neon_underground import spec_neon_blacklight
    M, R, CC = spec_neon_blacklight(shape, seed, 1.0, 244, 18)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 30.0, (
        f"neon_blacklight dM = {dM:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 30 (AUTO-LOOP-6 pinned 35)."
    )
    assert dR >= 24.0, (
        f"neon_blacklight dR = {dR:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 24 (AUTO-LOOP-6 pinned 28)."
    )
    assert dCC >= 16.0, (
        f"neon_blacklight dCC = {dCC:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 16 (AUTO-LOOP-6 pinned 20)."
    )


# ─── AUTO-LOOP-5 — neon_pink_blaze concentric pulse depth ──────────────────

@pytest.mark.parametrize("seed", [1, 42, 99, 123])
@pytest.mark.parametrize("shape", [(128, 128), (256, 256), (512, 512)])
def test_neon_pink_blaze_pulse_visible_in_spec(seed, shape):
    """neon_pink_blaze desc promises 'concentric pulsing glow zones'.

    Pre-AUTO-LOOP-5 the spec had M swing 13 (242..255), R swing 4 (16..20),
    CC flat 16 — the pulse field was computed correctly but its
    amplitude in the spec response was below perceptual threshold.
    Widened amplitudes: pin dM>=18, dR>=20, dCC>=15.
    """
    from engine.paint_v2.neon_underground import spec_neon_pink_blaze
    M, R, CC = spec_neon_pink_blaze(shape, seed, 1.0, 242, 16)
    dM = float(M.max() - M.min())
    dR = float(R.max() - R.min())
    dCC = float(CC.max() - CC.min())
    assert dM >= 18.0, (
        f"neon_pink_blaze dM = {dM:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 18 (AUTO-LOOP-5 pinned ~30)."
    )
    assert dR >= 20.0, (
        f"neon_pink_blaze dR = {dR:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 20 (AUTO-LOOP-5 pinned ~30)."
    )
    assert dCC >= 15.0, (
        f"neon_pink_blaze dCC = {dCC:.1f} at seed={seed}, shape={shape}. "
        f"Expected >= 15 (AUTO-LOOP-5 pinned ~25)."
    )


# ─── Foundation-variance ratchets DELETED 2026-04-22 HEENAN FAMILY iter 5 (cont'd) ───
#
# Four more `test_enh_*` functions previously at the end of this file
# also violated the Foundation flat-spec contract and have been
# removed alongside the six near the top:
#
#   test_enh_baked_enamel_has_kiln_fired_depth   (ex-AUTO-LOOP-4)
#   test_enh_gel_coat_has_visible_flow_variation (ex-AUTO-LOOP-3)
#   test_enh_ceramic_glaze_has_visible_pooling   (ex-AUTO-LOOP-2)
#   test_enh_wet_look_has_visible_flow_out_variation (ex-AUTO-LOOP-1)
#
# All four asserted minimum dR / dCC spreads on spec_enh_* functions
# whose painter-mandated behavior is now FLAT (no visible variance).
# Deleted rather than xfail-ed because they were asserting the wrong
# design contract, not detecting regressions.
#
# If variance on a specific foundation becomes painter-requested in
# the future, the *new* test belongs in a dedicated file with that
# painter rationale documented — not in this HARDMODE ratchet file.
