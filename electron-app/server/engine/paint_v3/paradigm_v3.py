"""
paint_v3.paradigm_v3 — 5 seed Paradigm finishes built on paint_v3 primitives.

SPB-107 Paradigm retool, owner mandate 2026-05-18 ("make finishes MATCH
what they say they do/look like. UNIQUE, no duplicate patterns/functions.
Everything STRIVING to be a 100 score").

Each seed picks a different design-space corner so paint_v3 primitives get
stress-tested across the breadth of Paradigm before the bulk-batch rework
of the remaining 25 below-75 finishes:

  Seed           Pre-rework M7   Motif                    Identity
  ─────────────  ─────────────   ──────────────────────   ──────────────────────
  blackbody       48.7  fix      thermal_hotspots         dark void w/ thermal glow
  mercury_pool    53.8  watch    liquid_pool              liquid metallic w/ ripples
  ember           41.8  fix      fissure_network          charcoal w/ molten cracks
  living_chrome   42.1  fix      flow_curl                chrome w/ frozen flow lines
  wormhole         N/A  missing  spiral_lens              spacetime distortion vortex

Each finish is implemented as a (spec_fn, paint_fn) pair matching the
engine's existing monolithic contract so the registry can drop them in
place of the legacy implementations from paradigm.py without touching
the registration machinery.

All 5 share the same compose_spec / compose_paint composers but build
DISTINCT motif stacks — no two finishes derive their character from
the same underlying field. That's the "no duplicate patterns/functions"
discipline made structural.
"""
from __future__ import annotations

import numpy as np

from .primitives import (
    motif_thermal_hotspots,
    motif_fissure_network,
    motif_liquid_pool,
    motif_flow_curl,
    motif_spiral_lens,
    fine_grain,
    dithered_threshold,
    radial_gauss,
    palette_lut,
    compose_spec,
    compose_paint,
)


# ===========================================================================
# Palette LUTs — each finish gets a hand-tuned palette
# ===========================================================================
# Built lazily and cached at module scope so the 256-entry HSV→RGB
# interpolation runs once per finish, not per render.

_LUT_CACHE: dict = {}


def _lut(name: str) -> np.ndarray:
    cached = _LUT_CACHE.get(name)
    if cached is not None:
        return cached
    if name == "blackbody":
        # Cold-to-white thermal radiation curve (real physics). Cold end is
        # near-black with tiny IR-red bias; hot end is white-blue.
        stops = [
            (0.00, 0.10, 0.04),   # vantablack
            (0.04, 0.55, 0.08),   # cooler red embers
            (0.05, 0.95, 0.20),   # deep red glow
            (0.08, 0.95, 0.55),   # orange-red flame
            (0.11, 0.85, 0.85),   # yellow-orange
            (0.16, 0.50, 0.95),   # pale yellow
            (0.55, 0.15, 1.00),   # white-blue (10000 K)
        ]
    elif name == "mercury_pool":
        # Liquid mercury — cool silver-blue, neutral metallic, into deep
        # pool shadow blue-black. Ripple crests catch sky reflection.
        stops = [
            (0.58, 0.40, 0.06),   # deep pool shadow (blue-black)
            (0.55, 0.30, 0.32),   # pool mid-depth
            (0.52, 0.18, 0.58),   # surface silver-blue
            (0.50, 0.06, 0.78),   # quicksilver bright
            (0.50, 0.00, 0.96),   # mirror crest highlight
        ]
    elif name == "ember":
        # Charcoal crust with molten-gold/orange cracks. Crust is matte
        # near-black, crack interior glows hot orange-yellow.
        stops = [
            (0.00, 0.40, 0.06),   # cold charcoal
            (0.02, 0.85, 0.15),   # warming crust
            (0.05, 0.95, 0.45),   # crack edge red
            (0.07, 0.95, 0.78),   # crack interior orange
            (0.11, 0.85, 0.95),   # core yellow-gold
        ]
    elif name == "living_chrome":
        # Chrome flow — neutral mirror silver along the flow ridges,
        # cooler shadow valleys with a faint blue-violet shift to suggest
        # the "alive" iridescent personality without becoming candy.
        stops = [
            (0.70, 0.18, 0.20),   # deep cool shadow
            (0.65, 0.10, 0.45),   # cool steel valley
            (0.60, 0.03, 0.78),   # silver mid
            (0.55, 0.00, 0.95),   # mirror crest
            (0.78, 0.15, 0.85),   # iridescent flicker (violet shift)
        ]
    elif name == "wormhole":
        # Spacetime distortion — singularity black core, accretion ring
        # in violet-magenta-blue spectrum, outer halo cooling to dark
        # cosmic blue-green. Pure void contrast at center.
        stops = [
            (0.65, 0.95, 0.04),   # singularity void (near-black indigo)
            (0.72, 0.95, 0.28),   # inner ring violet
            (0.85, 0.90, 0.60),   # accretion magenta
            (0.95, 0.75, 0.80),   # outer arm pink-cyan flicker
            (0.50, 0.85, 0.40),   # halo blue-cyan
            (0.40, 0.75, 0.12),   # outer void teal
        ]
    else:
        raise ValueError(f"unknown LUT: {name}")
    table = palette_lut(stops)
    _LUT_CACHE[name] = table
    return table


# ===========================================================================
# Helper: extract shape from incoming spec/paint args
# ===========================================================================

def _shape_hw(shape):
    return shape[:2] if len(shape) > 2 else shape


# ---------------------------------------------------------------------------
# Internal helper: PARADIGM-profile spec composition
#
# PARADIGM category requires HIGH on specMRange + specCcRange +
# specChannelIndependence (per m6 profile, scripts/spb_workbook_compute_m6.py
# L166). Achieved by composing each channel (M, R, CC) from a DIFFERENT
# weighted combination of 3 independent fields — keeper-style.
# ---------------------------------------------------------------------------

def _paradigm_spec(shape, mask, sm,
                   primary, secondary, tertiary,
                   m_coeffs, r_coeffs, cc_coeffs,
                   m_base=8.0, r_base=15.0, cc_base=18.0):
    """Compose (h, w, 4) uint8 spec map with independent M/R/CC channel
    derivation from three motif/noise fields.

    primary, secondary, tertiary: (h, w) fields in [0, 1].
    m_coeffs, r_coeffs, cc_coeffs: 3-tuples of weights applied to
        (primary, secondary, tertiary) for each channel.
    m_base, r_base, cc_base: additive base values to give each channel a
        non-zero minimum.

    Channel independence comes from the COEFFICIENTS being different per
    channel — same fields, different weightings, so M and R don't move
    in lockstep (which is what kills specChannelIndependence).
    """
    from .primitives import _apply_placement_to_field
    primary = _apply_placement_to_field(primary)
    secondary = _apply_placement_to_field(secondary)
    tertiary = _apply_placement_to_field(tertiary)

    h, w = primary.shape[:2]
    s = max(float(sm), 0.05)
    pm = m_coeffs
    pr = r_coeffs
    pc = cc_coeffs
    M = (m_base + primary * pm[0] + secondary * pm[1] + tertiary * pm[2]) * s
    R = (r_base + primary * pr[0] + secondary * pr[1] + tertiary * pr[2]) * s
    CC = cc_base + primary * pc[0] + secondary * pc[1] + tertiary * pc[2]
    if mask is not None:
        mask2 = mask[:, :, 0] if mask.ndim == 3 else mask
        active = (mask2 > 0.01).astype(np.float32)
    else:
        active = np.ones((h, w), dtype=np.float32)
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[:, :, 0] = (np.clip(M, 0, 255).astype(np.uint8)) * (active > 0)
    out[:, :, 1] = (np.clip(R, 15, 255).astype(np.uint8)) * (active > 0)
    out[:, :, 2] = (np.clip(CC, 16, 255).astype(np.uint8)) * (active > 0)
    out[:, :, 3] = (active * 255).astype(np.uint8)
    return out


# ===========================================================================
# BLACKBODY — thermal radiation from a perfect absorber
# ===========================================================================
# SPB-107 v3 (pre-rework M7: 48.7 / fix tier).
# Identity: deep vantablack-grade dark surface punctuated by glowing
# stellar-core hotspots radiating across the blackbody color curve.
# Each channel composes from 3 independent fields per PARADIGM m6 profile:
#   primary  = thermal hotspots (the structural identity)
#   secondary = fissure-style background turbulence (cold-zone variation)
#   tertiary = fine pixel grain (channel decorrelation)

def spec_blackbody(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71001
    # SPB-108 r2 (owner verdict 2026-05-18 "60-65, like the idea not the
    # execution"): blackbody v3 r1 read as isolated round dots. r2 adds
    # CORONA TENDRILS — fissure-network masked by hotspot reach simulates
    # plasma prominences radiating from each stellar core. Spec map now
    # shows discrete thermal pockets with visible plasma rays, not blobs.
    hotspots = motif_thermal_hotspots((h, w), seed_eff, n_hotspots=10,
                                      hotspot_sigma=0.10)
    sharp = dithered_threshold(hotspots, threshold=0.30, jitter=0.20,
                               seed=seed_eff + 100)
    primary = np.clip(sharp * 0.55 + hotspots * 0.45, 0, 1).astype(np.float32)
    # Corona tendrils — fissure ridges restricted to the hotspot halo
    coronae = motif_fissure_network((h, w), seed_eff + 500, density=0.85)
    halo = np.clip(hotspots * 1.6 - 0.2, 0, 1)
    secondary = np.clip(coronae * halo + halo * 0.35, 0, 1).astype(np.float32)
    # Finer pixel grain — smaller freqs give crisper micro-detail in spec
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(4, 8, 16),
                          weights=(0.45, 0.35, 0.20))
    # M weighted on PRIMARY but with secondary boost (corona spills hot),
    # R weighted on SECONDARY (corona structure controls roughness),
    # CC weighted on TERTIARY (grain decorrelates) — all 3 channels carry
    # visible motif structure so the spec map "shows" the design.
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(235.0,  35.0,  18.0),
                          r_coeffs=(-50.0,  170.0,  55.0),
                          cc_coeffs=(-30.0, -40.0,  160.0),
                          m_base=20.0, r_base=55.0, cc_base=55.0)


def paint_blackbody(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71001
    hotspots = motif_thermal_hotspots((h, w), seed_eff, n_hotspots=10,
                                      hotspot_sigma=0.09)
    return compose_paint(paint, hotspots, _lut("blackbody"),
                         mask, pm, bb,
                         intensity=0.92, dark_zone_only=True,
                         dark_threshold=0.50)


# ===========================================================================
# MERCURY_POOL — liquid mercury surface with ripples and pool depth
# ===========================================================================
# SPB-107 v3 (pre-rework M7: 53.8 / watch tier).
# Identity: full liquid metal surface with concentric ripples and pooling
# darkness in the depths. Always mostly metallic mirror; ripple crests
# brighten further, ripple troughs darken toward pool shadow.
# Primitives: motif_liquid_pool + fine_grain. Stays metallic everywhere
# (no binary threshold) — the "state" is depth, not on/off.

def spec_mercury_pool(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71002
    # SPB-108 r3 (owner verdict 2026-05-18 "looks like same lifeless render
    # but with Living Chrome's spec map — that's not how it's supposed to
    # work. The spec mirrors the paint and matches it just enhanced"):
    # r2 made the architectural mistake of introducing curl-flow into the
    # spec that doesn't exist in the paint. r3 enforces motif-mirror —
    # spec and paint BOTH derive structure from the same liquid_pool
    # motif. Secondary is a HIGHER-FREQ ripple of the SAME primitive
    # (micro-shimmer riding on the same pool dynamics) — adds independence
    # without introducing a competing pattern.
    ripples = motif_liquid_pool((h, w), seed_eff, ripple_freq=6.0)
    # Same motif at higher freq — micro-ripple shimmer crests riding on
    # the same pool surface. NOT a different pattern.
    micro_ripples = motif_liquid_pool((h, w), seed_eff + 1000, ripple_freq=13.0)
    primary = ripples
    secondary = micro_ripples
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(16, 32),
                          weights=(0.55, 0.45))
    # M weighted heavily on PRIMARY ripple (matches paint's ripple),
    # R weighted on SECONDARY micro-ripple (subtle surface roughness shift —
    # follows the same pool dynamics, just at smaller scale),
    # CC weighted on TERTIARY grain (decorrelator, not a visible pattern).
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(225.0,  -30.0,  12.0),
                          r_coeffs=(-25.0,  150.0,  40.0),
                          cc_coeffs=(35.0,   25.0, 155.0),
                          m_base=30.0, r_base=50.0, cc_base=55.0)


def paint_mercury_pool(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71002
    pool = motif_liquid_pool((h, w), seed_eff, ripple_freq=5.5)
    return compose_paint(paint, pool, _lut("mercury_pool"),
                         mask, pm, bb,
                         intensity=0.78, dark_zone_only=True,
                         dark_threshold=0.42)


# ===========================================================================
# EMBER — charcoal crust with glowing molten cracks
# ===========================================================================
# SPB-107 v3 (pre-rework M7: 41.8 / fix tier).
# Identity: matte black-charcoal crust fractured by a hot fissure network
# showing molten gold/orange in the cracks. Sharp state contrast: crust
# is fully matte, fissure interior is fully glowing with internal heat.
# Primitives: motif_fissure_network + motif_thermal_hotspots (subtle
# under-fissure heat reservoirs) + fine_grain.
# Distinct from blackbody (which uses isolated hotspot points) — ember
# uses a CONNECTED CRACK NETWORK as its motif.

def spec_ember(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71003
    # SPB-108 r3 (owner verdict 2026-05-18 "still have a long way to go,
    # rate this very low"): r2 dual-fissure network introduced cracks
    # in the spec that didn't exist in the paint. r3 enforces motif-mirror
    # (paint_ember must use the SAME compound motif), AND boosts the
    # visibility by:
    #   - DENSER primary fissures (density 1.10 → 1.40 baseline)
    #   - SECONDARY fine cracks at smaller scale (sub-fissures branching)
    #   - WARM CRUST BASELINE so the surface between cracks isn't pure
    #     black — gives the eye a non-zero gradient to read as "cooling
    #     lava crust" rather than "black void with thin orange streaks".
    fissures_main = motif_fissure_network((h, w), seed_eff, density=1.40)
    fissures_fine = motif_fissure_network((h, w), seed_eff + 7, density=0.85)
    reservoirs = motif_thermal_hotspots((h, w), seed_eff + 50, n_hotspots=6,
                                        hotspot_sigma=0.18)
    # Dense crack network: main + fine branching
    network = np.clip(np.maximum(fissures_main, fissures_fine * 0.72), 0, 1)
    # Compound motif (this is what paint_ember will ALSO use)
    primary = np.clip(network * (0.55 + reservoirs * 0.55), 0, 1).astype(np.float32)
    # Secondary: reservoirs alone (independent from fissures) — drives R
    secondary = reservoirs
    # Tertiary: pixel grain on the charcoal crust
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(4, 8, 16),
                          weights=(0.45, 0.35, 0.20))
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(245.0,   30.0,  18.0),
                          r_coeffs=(-60.0, -190.0,  60.0),
                          cc_coeffs=(40.0,  -35.0, 170.0),
                          m_base=12.0, r_base=240.0, cc_base=55.0)


def paint_ember(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71003
    # MUST match spec_ember's compound motif exactly (motif-mirror rule):
    # main fissures × fine fissures, amplified at reservoir hotspots.
    fissures_main = motif_fissure_network((h, w), seed_eff, density=1.40)
    fissures_fine = motif_fissure_network((h, w), seed_eff + 7, density=0.85)
    reservoirs = motif_thermal_hotspots((h, w), seed_eff + 50, n_hotspots=6,
                                        hotspot_sigma=0.18)
    network = np.clip(np.maximum(fissures_main, fissures_fine * 0.72), 0, 1)
    motif = np.clip(network * (0.55 + reservoirs * 0.55), 0, 1).astype(np.float32)
    return compose_paint(paint, motif, _lut("ember"),
                         mask, pm, bb,
                         intensity=0.92, dark_zone_only=True,
                         dark_threshold=0.50)


# ===========================================================================
# LIVING_CHROME — chrome with frozen flow lines as if mid-motion
# ===========================================================================
# SPB-107 v3 (pre-rework M7: 42.1 / fix tier).
# Identity: mostly full mirror chrome, but with subtle flow ridges that
# suggest the surface was caught mid-movement. Flow ridges have a faint
# iridescent shift (visible at glancing angles) so the chrome looks
# "alive" rather than dead-mirror.
# Primitives: motif_flow_curl + fine_grain. NO threshold — flow ridges
# are smooth bands across the mirror, not binary on/off.

def spec_living_chrome(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71004
    # Primary motif: curl-noise flow ridges (the alive-motion identity)
    primary = motif_flow_curl((h, w), seed_eff, viscosity=1.0)
    # Secondary: orthogonal flow at different viscosity — interference between
    # two flow systems creates "cross-current" zones with wider M range.
    secondary = motif_flow_curl((h, w), seed_eff + 700, viscosity=1.6)
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(16, 32, 64),
                          weights=(0.4, 0.35, 0.25))
    # M: dominant flow boosts mirror, secondary flow adds wider variation,
    #    grain provides decorrelation
    # R: inverse-flow drives smoothness, secondary inverts differently, grain pushes
    # CC: flow ridges = perfect clarity, valleys = significant CC degradation
    # living_chrome: M weighted on PRIMARY (first flow ridges = mirror M),
    # R weighted on SECONDARY (second flow valleys drive roughness), CC
    # weighted on TERTIARY (grain texture decorrelates clearcoat).
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(180.0,  15.0,  20.0),
                          r_coeffs=(-20.0,  -150.0, 55.0),
                          cc_coeffs=(15.0,  -20.0,  155.0),
                          m_base=80.0, r_base=180.0, cc_base=50.0)


def paint_living_chrome(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71004
    flow = motif_flow_curl((h, w), seed_eff, viscosity=1.0)
    return compose_paint(paint, flow, _lut("living_chrome"),
                         mask, pm, bb,
                         intensity=0.62, dark_zone_only=True,
                         dark_threshold=0.45)


# ===========================================================================
# WORMHOLE — spacetime singularity with spiral lensing
# ===========================================================================
# SPB-107 v3 (pre-rework M7: MISSING — wormhole was registered in legacy
# paradigm.py but skipped during M7 bake, exact cause TBD).
# Identity: dark singularity core with spiral arms of accretion-disk
# light spiraling inward, chromatic distortion at the lensing rim.
# Sharp inner void contrast against bright accretion ring.
# Primitives: motif_spiral_lens + dithered_threshold (rim crispness)
# + fine_grain (halo turbulence).
# Distinct from blackbody/ember/mercury_pool in that the motif has a
# DEFINED CENTER POINT and radial structure — every other seed motif is
# distributed across the surface, wormhole has a singularity locus.

def spec_wormhole(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71005
    # SPB-108 r3 (owner verdict 2026-05-18 "pattern way too massive, like
    # the different colors, spec has too much random stuff — squiggles
    # don't go with the paint"): r2 used arms=3 + halo turbulence
    # secondary. r3 cuts the pattern down (arms=5, pull_strength=2.4 →
    # tighter, more repetitions across body) AND removes the halo
    # fissure-network secondary that owner read as random squiggles.
    # Spec now mirrors the paint's spiral structure only.
    lens = motif_spiral_lens((h, w), seed_eff, arms=5, pull_strength=2.4)
    rim_mask = dithered_threshold(lens, threshold=0.55, jitter=0.12,
                                  seed=seed_eff + 80)
    # Primary: lens + crisp ring rim (same as paint sees)
    primary = np.clip(lens * 0.62 + rim_mask * 0.44, 0, 1).astype(np.float32)
    # Secondary: a SOFT-EDGE version of the same lens (low-pass via blur
    # surrogate — using a second motif_spiral_lens at gentler pull to read
    # as the SAME pattern's halo, not as a different field).
    soft_lens = motif_spiral_lens((h, w), seed_eff + 1500, arms=5, pull_strength=1.6)
    secondary = soft_lens
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(16, 32),
                          weights=(0.6, 0.4))
    # M weighted on PRIMARY lens (accretion-arm metallic brightness — mirrors paint),
    # R weighted on SECONDARY soft-lens (gradient between arms drives roughness,
    # follows the SAME spiral structure at a different phase),
    # CC weighted on TERTIARY grain (decorrelator).
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(245.0,  -25.0,  15.0),
                          r_coeffs=(-30.0,  180.0,  45.0),
                          cc_coeffs=(25.0,  -30.0,  165.0),
                          m_base=10.0, r_base=50.0, cc_base=55.0)


def paint_wormhole(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71005
    # MUST match spec_wormhole's lens params exactly (motif-mirror rule).
    lens = motif_spiral_lens((h, w), seed_eff, arms=5, pull_strength=2.4)
    return compose_paint(paint, lens, _lut("wormhole"),
                         mask, pm, bb,
                         intensity=0.93, dark_zone_only=True,
                         dark_threshold=0.55)


# ===========================================================================
# Registry export — (spec_fn, paint_fn) tuples for engine MONOLITHIC_REGISTRY
# ===========================================================================

V3_PARADIGM_SEEDS = {
    "blackbody":      (spec_blackbody,     paint_blackbody),
    "mercury_pool":   (spec_mercury_pool,  paint_mercury_pool),
    "ember":          (spec_ember,         paint_ember),
    "living_chrome":  (spec_living_chrome, paint_living_chrome),
    "wormhole":       (spec_wormhole,      paint_wormhole),
}
