# -*- coding: utf-8 -*-
"""SPECTRUM SHIFT 2026 — 50 bespoke finishes on the new optical-physics arsenal.
Replaces the 10-palettes x 5-variants clones. Every finish = real spectral
phenomenon + unique geometry + married angle-gated spec."""
import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _coords, _noise, _warp, _sr, _n01, _sstep, _gauss, _curves, _crystal,
    _flow_theta, _flowlines, _caustics, _engrave, _dendrites, _stars, _dirblur,
    _ramp, _ipal, _flakes, _memo, _polish, _finefill, _microtex, _native_finish,
    _seed_int, _up, _m2, _pack, _WORK, _harmonograph, _gray_scott,
)
from engine.expansions.spectrum_arsenal_2026 import (
    spectral, stress_fringes, tempered_quench, scratch_holo, grating_field,
    lc_texture, fan_domains, opal_fire, newton_rings, spectral_caustics,
    moire_phase, hue_advect, blackbody, chromatic_split, spectral_contours,
    spectral_lathe, doppler_field, einstein_arcs, hopper_terraces,
)


# ════════════════════════════════ A. PHOTOELASTIC FAMILY (3 different worlds)
# 1. STRESS STORM — a polariscope hurricane: dozens of colliding load fringes.
@_memo
def _ss_stress_storm_f(h, w, s):
    order, mag = stress_fringes(h, w, s, n_loads=38, fringe_density=14)
    grain = _noise(h, w, s ^ 0x1, (2, 4))
    return order, mag, grain


def _ss_stress_storm_paint(h, w, s):
    order, mag, grain = _ss_stress_storm_f(h, w, s)
    fringe = spectral(order, flatten=0.30)
    body = np.float32([0.05, 0.05, 0.07])[None, None, :] + fringe * (0.25 + 0.75 * mag)[..., None]
    return _polish(body * (0.86 + 0.14 * grain[..., None]), h, w, s)


def _ss_stress_storm_spec(h, w, s):
    order, mag, grain = _ss_stress_storm_f(h, w, s)
    line = _sstep(0.0, 0.10, order) * (1 - _sstep(0.10, 0.22, order))   # dark fringe walls
    gate = _sstep(0.42, 0.5, mag) * (1 - _sstep(0.62, 0.7, mag))
    M = 50 + 140 * mag + 50 * line
    R = np.clip(170 - 130 * mag + 35 * grain, 0, 255)
    Cc = 22 + 200 * line * gate + 60 * mag * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 2. FRACTURE POLARIZED — cracked stressed glass: fringe rainbows CROWD at the
# crack tips (true stress concentration), cracks glassy black.
@_memo
def _ss_fracture_pol_f(h, w, s):
    cracks = _dendrites(h, w, s ^ 0xC4, n_roots=40, depth=6, seg=36 * _sr(h, w), thick=2)
    tips = np.clip(cracks - _gauss(cracks, 5) * 0.8, 0, 1)
    conc = _gauss(cracks, 14)
    order, mag = stress_fringes(h, w, s, n_loads=14, fringe_density=7)
    order = (order + conc * 7.0) % 1.0
    mag = np.clip(mag * 0.6 + conc * 1.1, 0, 1)
    return cracks, order.astype(np.float32), mag.astype(np.float32)


def _ss_fracture_pol_paint(h, w, s):
    cracks, order, mag = _ss_fracture_pol_f(h, w, s)
    fringe = spectral(order, flatten=0.34)
    body = np.float32([0.07, 0.07, 0.10])[None, None, :] + fringe * (0.18 + 0.82 * mag)[..., None]
    body *= (1 - 0.85 * cracks[..., None])
    return _polish(body, h, w, s)


def _ss_fracture_pol_spec(h, w, s):
    cracks, order, mag = _ss_fracture_pol_f(h, w, s)
    gate = _sstep(0.5, 0.58, mag) * (1 - _sstep(0.72, 0.8, mag))
    M = 45 + 130 * mag + 70 * cracks
    R = np.clip(160 - 110 * mag + 60 * cracks, 0, 255)
    Cc = 20 + 210 * cracks * gate + 70 * mag * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 3. TEMPERED GHOST — the polarized-sunglasses car-window quench grid, elevated:
# rose-and-iris stress rosettes in a drifting lattice over smoked glass.
@_memo
def _ss_tempered_ghost_f(h, w, s):
    order, sig = tempered_quench(h, w, s, pitch=32, fringe_density=6)
    smoke = _noise(h, w, s ^ 0x7, (90, 220, 500))
    return order, sig, smoke


def _ss_tempered_ghost_paint(h, w, s):
    order, sig, smoke = _ss_tempered_ghost_f(h, w, s)
    iris = _ramp([(0.30, 0.26, 0.36), (0.58, 0.36, 0.55), (0.30, 0.45, 0.60),
                  (0.62, 0.50, 0.42)], order, flatten_lightness=0.35)
    glass = np.float32([0.10, 0.11, 0.13])[None, None, :] * (0.7 + 0.6 * smoke[..., None])
    body = glass + iris * (sig * 0.85)[..., None]
    return _polish(body, h, w, s)


def _ss_tempered_ghost_spec(h, w, s):
    order, sig, smoke = _ss_tempered_ghost_f(h, w, s)
    gate = _sstep(0.46, 0.54, smoke) * (1 - _sstep(0.66, 0.74, smoke))
    M = 60 + 120 * sig + 40 * gate
    R = np.clip(120 - 70 * sig + 40 * _microtex(h, w, s ^ 2) + 30 * (1 - smoke), 0, 255)
    Cc = 24 + 190 * sig * gate + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ B. SCRATCH-HOLOGRAPHY FAMILY
# 4. ABRASION HALO — polished-metal arc fields; spectral glints CRAWL the arcs.
@_memo
def _ss_abrasion_halo_f(h, w, s):
    arcs, glints, phase = scratch_holo(h, w, s, n_centers=10, arcs_per=110)
    metal = _dirblur(_noise(h, w, s ^ 0x3, (1.6, 3.4)), float(_rng(s, 3).uniform(0, np.pi)), int(18 * _sr(h, w)))
    return arcs, glints, phase, metal


def _ss_abrasion_halo_paint(h, w, s):
    arcs, glints, phase, metal = _ss_abrasion_halo_f(h, w, s)
    steel = _ramp([(0.16, 0.17, 0.20), (0.42, 0.44, 0.50), (0.72, 0.75, 0.82)], metal, flatten_lightness=0.25)
    body = steel * (1 - 0.30 * arcs[..., None])
    body += spectral(phase, flatten=0.30) * (glints * 1.0)[..., None]
    return _polish(body, h, w, s)


def _ss_abrasion_halo_spec(h, w, s):
    arcs, glints, phase, metal = _ss_abrasion_halo_f(h, w, s)
    gate = _sstep(0.30, 0.40, phase) * (1 - _sstep(0.60, 0.70, phase))
    M = 90 + 80 * metal + 80 * glints
    R = np.clip(60 + 90 * arcs - 40 * glints + 30 * (1 - metal), 0, 255)
    Cc = 22 + 215 * glints * (0.35 + 0.65 * gate) + 30 * arcs * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 5. ORBITAL ENGRAVE — interlocking orbital ring systems cut into black chrome,
# each system's glint at a different clock position (sequential flash).
@_memo
def _ss_orbital_engrave_f(h, w, s):
    arcs1, gl1, ph1 = scratch_holo(h, w, s, n_centers=5, arcs_per=70)
    arcs2, gl2, ph2 = scratch_holo(h, w, s ^ 0x99, n_centers=5, arcs_per=70)
    arcs = np.maximum(arcs1, arcs2 * 0.8)
    glints = np.maximum(gl1, gl2)
    phase = _n01(ph1 + ph2)
    return arcs, glints, phase


def _ss_orbital_engrave_paint(h, w, s):
    arcs, glints, phase = _ss_orbital_engrave_f(h, w, s)
    body = np.float32([0.06, 0.06, 0.08])[None, None, :] * _finefill(h, w, s, 0.5, (1.8, 3.5))[..., None]
    body += np.float32([0.30, 0.32, 0.38])[None, None, :] * arcs[..., None] * 0.8
    body += spectral(phase, flatten=0.25) * glints[..., None] * 1.1
    return _polish(body, h, w, s, grain=0.07)


def _ss_orbital_engrave_spec(h, w, s):
    arcs, glints, phase = _ss_orbital_engrave_f(h, w, s)
    gate = _sstep(0.40, 0.48, phase) * (1 - _sstep(0.60, 0.68, phase))
    M = 35 + 170 * arcs + 50 * glints
    R = np.clip(40 + 30 * _microtex(h, w, s ^ 4) + 60 * (1 - arcs), 0, 255)
    Cc = 18 + 220 * glints * (0.4 + 0.6 * gate) + 50 * arcs * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 6. SWIRL SUPERNOVA — the detailer's swirl-mark nightmare made cosmic: dense
# micro arc-galaxies on deep purple-black, dispersive star glints everywhere.
@_memo
def _ss_swirl_nova_f(h, w, s):
    arcs, glints, phase = scratch_holo(h, w, s, n_centers=16, arcs_per=60, glint_sigma=0.3)
    stars = _stars(h, w, s ^ 0x5, n=12000, bright_frac=0.02)
    neb = _noise(h, w, s ^ 0x8, (130, 320))
    return arcs, glints, phase, stars, neb


def _ss_swirl_nova_paint(h, w, s):
    arcs, glints, phase, stars, neb = _ss_swirl_nova_f(h, w, s)
    night = _ramp([(0.05, 0.03, 0.09), (0.12, 0.06, 0.18), (0.20, 0.10, 0.24)], neb, flatten_lightness=0.3)
    body = night * (1 + 0.5 * arcs[..., None])
    body += spectral(phase, flatten=0.3) * glints[..., None] + stars[..., None] * 0.55
    return _polish(body, h, w, s, grain=0.075)


def _ss_swirl_nova_spec(h, w, s):
    arcs, glints, phase, stars, neb = _ss_swirl_nova_f(h, w, s)
    gate = _sstep(0.44, 0.52, neb) * (1 - _sstep(0.64, 0.72, neb))
    M = 40 + 150 * arcs + 60 * stars
    R = np.clip(170 - 120 * arcs - 60 * stars + 30 * _microtex(h, w, s ^ 6), 0, 255)
    Cc = 18 + 205 * (glints + stars * 0.6) * (0.4 + 0.6 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ C. DIFFRACTION GRATING FAMILY
# 7. VINYL GROOVE — record grooves: ultra-fine arc tracks from off-canvas
# spindles, tone-arm dispersion sweeping across the grooves.
@_memo
def _ss_vinyl_groove_f(h, w, s):
    rng = _rng(s, 11)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    groove = np.zeros((h, w), np.float32)
    sweep = np.zeros((h, w), np.float32)
    for i in range(4):
        cx, cy = rng.uniform(-0.6, 1.6) * w, rng.uniform(-0.6, 1.6) * h
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        g = 0.5 + 0.5 * np.sin(r * (2 * np.pi / (3.4 * sr)))
        env = 0.35 + 0.65 * np.exp(-np.abs(r - rng.uniform(0.4, 1.0) * max(h, w)) / (0.55 * max(h, w)))
        groove = np.maximum(groove, g * env)
        sweep += ((np.arctan2(yy - cy, xx - cx) / np.pi) % 1.0) * env
    dust = _flakes(h, w, s ^ 0xD, density=0.05, bright=0.7)
    return groove.astype(np.float32), _n01(sweep), dust


def _ss_vinyl_groove_paint(h, w, s):
    groove, sweep, dust = _ss_vinyl_groove_f(h, w, s)
    vinyl = np.float32([0.07, 0.07, 0.08])[None, None, :] * (0.7 + 0.6 * groove[..., None])
    body = vinyl + spectral(sweep, flatten=0.4) * (groove * 0.8 + 0.14)[..., None] * 1.0
    body += dust[..., None] * 0.4
    return _polish(body, h, w, s, grain=0.07)


def _ss_vinyl_groove_spec(h, w, s):
    groove, sweep, dust = _ss_vinyl_groove_f(h, w, s)
    gate = _sstep(0.35, 0.45, sweep) * (1 - _sstep(0.6, 0.7, sweep))
    M = 60 + 130 * groove + 40 * dust
    R = np.clip(60 + 80 * (1 - groove) + 30 * _microtex(h, w, s ^ 7), 0, 255)
    Cc = 22 + 195 * groove * gate + 80 * dust
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 8. DATA ETCH — optical-disc pit sectors: wedge sectors of micro-track
# stripes, each sector refracting its own order rainbow.
@_memo
def _ss_data_etch_f(h, w, s):
    rng = _rng(s, 13)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    cx, cy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.2, 0.8) * h
    th = np.arctan2(yy - cy, xx - cx)
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    n_sec = 22
    sector = np.floor(((th / (2 * np.pi)) % 1.0) * n_sec)
    per = _n01(np.sin(sector * 12.99) + 1)
    tracks = (0.5 + 0.5 * np.sin(r * (2 * np.pi / (3.0 * sr)) + sector * 2.0)).astype(np.float32)
    blocks = _sstep(0.4, 0.6, _noise(h, w, s ^ 0x21, (12, 30)))   # data blocks
    return per, tracks, blocks, _n01(r)


def _ss_data_etch_paint(h, w, s):
    per, tracks, blocks, rad = _ss_data_etch_f(h, w, s)
    base = np.float32([0.55, 0.57, 0.62])[None, None, :] * (0.55 + 0.45 * tracks[..., None])
    body = base * (1 - 0.35 * blocks[..., None])
    body += spectral((per + rad * 0.6) % 1.0, flatten=0.35) * (0.30 + 0.45 * tracks * blocks)[..., None]
    return _polish(body, h, w, s)


def _ss_data_etch_spec(h, w, s):
    per, tracks, blocks, rad = _ss_data_etch_f(h, w, s)
    gate = _sstep(0.38, 0.46, per) * (1 - _sstep(0.58, 0.66, per))
    M = 100 + 90 * tracks + 40 * blocks
    R = np.clip(50 + 70 * blocks * (1 - tracks) + 30 * _microtex(h, w, s ^ 8), 0, 255)
    Cc = 24 + 185 * tracks * gate * blocks + 50 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 9. GRATING QUILT — holo-foil patchwork: tiles of hairline gratings at angles,
# stitched seams, each patch firing its own order color at its own gate.
@_memo
def _ss_grating_quilt_f(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=240, aniso=1.25, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    yy, xx = _coords(h, w)
    sr = _sr(h, w)
    ang = per * np.pi
    grooves = (0.5 + 0.5 * np.sin((xx * np.cos(ang) + yy * np.sin(ang)) * (2 * np.pi / (3.2 * sr)))).astype(np.float32)
    seam = 1.0 - _sstep(0.03, 0.09, edge)
    return per, grooves, seam


def _ss_grating_quilt_paint(h, w, s):
    per, grooves, seam = _ss_grating_quilt_f(h, w, s)
    foil = spectral(per, flatten=0.45) * (0.42 + 0.42 * grooves)[..., None]
    body = foil * (1 - 0.55 * seam[..., None]) + np.float32([0.85, 0.85, 0.9]) * seam[..., None] * 0.12
    return _polish(body, h, w, s)


def _ss_grating_quilt_spec(h, w, s):
    per, grooves, seam = _ss_grating_quilt_f(h, w, s)
    gate = _sstep(0.36, 0.44, per) * (1 - _sstep(0.56, 0.64, per))
    M = 95 + 95 * grooves + 40 * gate
    R = np.clip(50 + 100 * seam + 40 * (1 - grooves), 0, 255)
    Cc = 26 + 200 * gate * grooves + 30 * grooves
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ D. LIQUID CRYSTAL FAMILY
# 10. LIQUID CRYSTAL — cholesteric fingerprint: pitch bands cycling the
# spectrum, dark disclination defect lines threading through.
@_memo
def _ss_liquid_crystal_f(h, w, s):
    bands, defects = lc_texture(h, w, s, fine=0.5)
    drift = _noise(h, w, s ^ 0x31, (160, 400))
    return bands, defects, drift


def _ss_liquid_crystal_paint(h, w, s):
    bands, defects, drift = _ss_liquid_crystal_f(h, w, s)
    lc = spectral((bands * 2.2 + drift * 0.8) % 1.0, flatten=0.38)
    body = lc * (0.45 + 0.55 * _sstep(0.2, 0.8, bands))[..., None]
    body *= (1 - 0.7 * defects[..., None])
    return _polish(body, h, w, s)


def _ss_liquid_crystal_spec(h, w, s):
    bands, defects, drift = _ss_liquid_crystal_f(h, w, s)
    gate = _sstep(0.44, 0.52, drift) * (1 - _sstep(0.64, 0.72, drift))
    bandv = np.abs(np.cos(bands * np.pi * 3))
    M = 60 + 130 * bandv + 40 * gate
    R = np.clip(70 + 120 * defects + 40 * (1 - bandv), 0, 255)
    Cc = 24 + 190 * bandv * gate + 60 * defects * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 11. THERMO TOUCH — thermochromic sheet: hot zones bloom through the LC
# spectrum (black->bronze->green->blue), cool zones stay dark — heat-map skin.
@_memo
def _ss_thermo_touch_f(h, w, s):
    heat = _n01(_noise(h, w, s ^ 0x41, (50, 130, 300)) +
                _gauss(_flakes(h, w, s ^ 0x42, density=0.02, bright=1.0), 18 * _sr(h, w)) * 2.2)
    bands, defects = lc_texture(h, w, s ^ 0x43, fine=0.62)
    return heat, bands, defects


def _ss_thermo_touch_paint(h, w, s):
    heat, bands, defects = _ss_thermo_touch_f(h, w, s)
    tc = _ramp([(0.05, 0.04, 0.05), (0.35, 0.18, 0.06), (0.10, 0.45, 0.12),
                (0.05, 0.55, 0.60), (0.15, 0.30, 0.85)], heat, flatten_lightness=0.42)
    body = tc * (0.50 + 0.50 * np.abs(np.cos(bands * np.pi * 2))[..., None])
    body *= (1 - 0.75 * defects[..., None])
    return _polish(body, h, w, s)


def _ss_thermo_touch_spec(h, w, s):
    heat, bands, defects = _ss_thermo_touch_f(h, w, s)
    gate = _sstep(0.5, 0.58, heat) * (1 - _sstep(0.72, 0.8, heat))
    M = 45 + 150 * heat + 40 * gate
    R = np.clip(160 - 110 * heat + 50 * defects, 0, 255)
    Cc = 20 + 200 * heat * gate + 40 * np.abs(np.cos(bands * np.pi * 2)) * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 12. SMECTIC FAN — focal-conic fan domains: packed ribbed fans, each fan a
# different slice of the wheel — the polarized-microscope money shot.
@_memo
def _ss_smectic_fan_f(h, w, s):
    fans, rib, per = fan_domains(h, w, s, n_fans=750)
    return fans, rib, per


def _ss_smectic_fan_paint(h, w, s):
    fans, rib, per = _ss_smectic_fan_f(h, w, s)
    body = spectral(per, flatten=0.40) * (0.26 + 0.62 * rib + 0.12 * fans)[..., None]
    body *= (0.42 + 0.58 * fans[..., None])
    return _polish(body + 0.03, h, w, s)


def _ss_smectic_fan_spec(h, w, s):
    fans, rib, per = _ss_smectic_fan_f(h, w, s)
    gate = _sstep(0.36, 0.44, per) * (1 - _sstep(0.56, 0.64, per))
    M = 60 + 120 * rib * fans + 50 * gate
    R = np.clip(60 + 90 * (1 - fans) + 40 * (1 - rib), 0, 255)
    Cc = 24 + 195 * rib * fans * gate + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ E. OPAL FAMILY
# 13. BLACK OPAL — near-black potch with domains of green/orange/violet FIRE,
# the Lightning Ridge look: sleeping color that detonates at the gate angle.
@_memo
def _ss_black_opal_f(h, w, s):
    per, flash, inner = opal_fire(h, w, s, n_domains=1200, lit_frac=0.5, gate_bands=3)
    potch = _noise(h, w, s ^ 0x51, (60, 150, 340))
    return per, flash, inner, potch


def _ss_black_opal_paint(h, w, s):
    per, flash, inner, potch = _ss_black_opal_f(h, w, s)
    body = np.float32([0.04, 0.045, 0.06])[None, None, :] * (0.7 + 0.6 * potch[..., None])
    fire = spectral(per, flatten=0.30)
    body += fire * (inner * 0.22)[..., None]          # sleeping shimmer
    body += fire * (flash * 1.1)[..., None]           # detonating domains
    return _polish(body, h, w, s, grain=0.075)


def _ss_black_opal_spec(h, w, s):
    per, flash, inner, potch = _ss_black_opal_f(h, w, s)
    M = 40 + 100 * inner + 110 * flash
    R = np.clip(60 + 40 * _microtex(h, w, s ^ 9) + 70 * (1 - inner), 0, 255)
    Cc = 18 + 230 * flash + 40 * inner
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 14. BOULDER OPAL — opal fire running in VEINS through dark ironstone matrix.
@_memo
def _ss_boulder_opal_f(h, w, s):
    veins = _gray_scott(h, w, s, "maze", iters=420, grid=448, seeds=26, fine=0.5, speckle=0.07)
    vm = _sstep(0.45, 0.62, veins)
    per, flash, inner = opal_fire(h, w, s ^ 0x2, n_domains=700, lit_frac=0.65, gate_bands=4)
    stone = _noise(h, w, s ^ 0x52, (3, 8, 20))
    return vm, per, flash, stone


def _ss_boulder_opal_paint(h, w, s):
    vm, per, flash, stone = _ss_boulder_opal_f(h, w, s)
    iron = _ramp([(0.16, 0.10, 0.07), (0.30, 0.20, 0.13), (0.45, 0.32, 0.22)], stone, flatten_lightness=0.2)
    fire = spectral(per, flatten=0.3)
    body = iron * (1 - vm[..., None]) + (fire * 0.35 + fire * flash[..., None] * 0.9) * vm[..., None]
    return _polish(body, h, w, s)


def _ss_boulder_opal_spec(h, w, s):
    vm, per, flash, stone = _ss_boulder_opal_f(h, w, s)
    M = 40 + 60 * stone + 140 * vm
    R = np.clip(170 - 120 * vm + 50 * stone, 0, 255)
    Cc = 20 + 225 * flash * vm + 40 * vm
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 15. OPAL CORE — full crystal opal: wall-to-wall play-of-color domains.
@_memo
def _ss_opal_core_f(h, w, s):
    per, flash, inner = opal_fire(h, w, s, n_domains=1700, lit_frac=0.85, gate_bands=5)
    milk = _noise(h, w, s ^ 0x53, (100, 260))
    return per, flash, inner, milk


def _ss_opal_core_paint(h, w, s):
    per, flash, inner, milk = _ss_opal_core_f(h, w, s)
    fire = spectral(per, flatten=0.42)
    base = np.float32([0.80, 0.82, 0.86])[None, None, :] * (0.8 + 0.2 * milk[..., None])
    body = base * 0.5 + fire * (0.34 + 0.30 * inner)[..., None] + fire * flash[..., None] * 0.7
    return _polish(body, h, w, s)


def _ss_opal_core_spec(h, w, s):
    per, flash, inner, milk = _ss_opal_core_f(h, w, s)
    gate = _sstep(0.44, 0.52, milk) * (1 - _sstep(0.64, 0.72, milk))
    M = 70 + 100 * inner + 70 * flash
    R = np.clip(80 + 60 * (1 - inner) + 30 * _microtex(h, w, s ^ 1), 0, 255)
    Cc = 26 + 200 * flash + 60 * inner * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ F. THIN-FILM CONTACT FAMILY
# 16. CONTACT BLOOM — Newton-ring blossoms: ring systems crowding outward
# from touch points, overlapping into interference gardens.
@_memo
def _ss_contact_bloom_f(h, w, s):
    order, env = newton_rings(h, w, s, n_contacts=44, lam=6.5)
    glass = _noise(h, w, s ^ 0x61, (140, 340))
    return order, env, glass


def _ss_contact_bloom_paint(h, w, s):
    order, env, glass = _ss_contact_bloom_f(h, w, s)
    rings = spectral(order, flatten=0.36)
    base = _ramp([(0.10, 0.10, 0.14), (0.22, 0.22, 0.28)], glass, flatten_lightness=0.0)
    body = base + rings * (env * 0.95)[..., None]
    return _polish(body, h, w, s)


def _ss_contact_bloom_spec(h, w, s):
    order, env, glass = _ss_contact_bloom_f(h, w, s)
    line = np.abs(np.cos(order * np.pi * 2))
    gate = _sstep(0.46, 0.54, glass) * (1 - _sstep(0.66, 0.74, glass))
    M = 55 + 130 * env * line + 40 * gate
    R = np.clip(140 - 90 * env + 40 * _microtex(h, w, s ^ 2), 0, 255)
    Cc = 22 + 195 * env * line * gate + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 17. OILFILM RAIN — gasoline rainbow on wet asphalt: drainage swirls, rain
# impact ring sets, micro aggregate poking through the film.
@_memo
def _ss_oilfilm_rain_f(h, w, s):
    rng = _rng(s, 17)
    film = _n01(_noise(h, w, s ^ 0x71, (70, 180, 400)) +
                _dirblur(_noise(h, w, s ^ 0x72, (8, 20)), float(rng.uniform(0, np.pi)), int(40 * _sr(h, w))) * 0.7)
    order, env = newton_rings(h, w, s ^ 0x73, n_contacts=16, lam=14.0)
    agg = _sstep(0.72, 0.92, _noise(h, w, s ^ 0x74, (2.2, 4.5)))
    return film, order, env, agg


def _ss_oilfilm_rain_paint(h, w, s):
    film, order, env, agg = _ss_oilfilm_rain_f(h, w, s)
    slick = _ipal(_n01(film * 1.4 + order * env * 0.8), 4.2, 0.95, np.float32([0.32, 0.33, 0.36]))
    body = slick * (1 - 0.55 * agg[..., None]) + np.float32([0.05, 0.05, 0.06]) * agg[..., None]
    return _polish(body, h, w, s)


def _ss_oilfilm_rain_spec(h, w, s):
    film, order, env, agg = _ss_oilfilm_rain_f(h, w, s)
    gate = _sstep(0.44, 0.52, film) * (1 - _sstep(0.66, 0.74, film))
    M = 90 + 90 * (1 - agg) + 50 * env * gate
    R = np.clip(40 + 160 * agg + 30 * _microtex(h, w, s ^ 3), 0, 255)
    Cc = 24 + 185 * (1 - agg) * gate + 60 * env * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ G. DISPERSED CAUSTICS FAMILY
# 18. PRISM POOL — every caustic filament its own micro-rainbow over deep glass.
@_memo
def _ss_prism_pool_f(h, w, s):
    web3 = spectral_caustics(h, w, s, strength=42, scale=52, split=3.0)
    depth = _noise(h, w, s ^ 0x81, (160, 400))
    return web3, depth


def _ss_prism_pool_paint(h, w, s):
    web3, depth = _ss_prism_pool_f(h, w, s)
    base = _ramp([(0.05, 0.09, 0.14), (0.09, 0.17, 0.26), (0.14, 0.28, 0.38)], depth, flatten_lightness=0.25)
    body = base + web3 * 1.1
    return _polish(body, h, w, s)


def _ss_prism_pool_spec(h, w, s):
    web3, depth = _ss_prism_pool_f(h, w, s)
    web = web3.mean(2)
    gate = _sstep(0.44, 0.52, depth) * (1 - _sstep(0.66, 0.74, depth))
    M = 55 + 160 * web
    R = np.clip(120 - 80 * web + 40 * _microtex(h, w, s ^ 4), 0, 255)
    Cc = 22 + 200 * web * gate + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 19. JEWEL BOX — dispersed caustics caged inside crystal facets, every facet
# a different refraction depth, grout-dark seams.
@_memo
def _ss_jewel_box_f(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=720, aniso=2.2, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    web3 = spectral_caustics(h, w, s ^ 0x2, strength=38, scale=52, split=2.2)
    seam = 1.0 - _sstep(0.04, 0.12, edge)
    return per, web3, seam, edge


def _ss_jewel_box_paint(h, w, s):
    per, web3, seam, edge = _ss_jewel_box_f(h, w, s)
    base = spectral(per, flatten=0.55) * 0.30
    body = base + web3 * (0.5 + 0.5 * edge)[..., None]
    body *= (1 - 0.75 * seam[..., None])
    return _polish(body + 0.02, h, w, s)


def _ss_jewel_box_spec(h, w, s):
    per, web3, seam, edge = _ss_jewel_box_f(h, w, s)
    web = web3.mean(2)
    gate = _sstep(0.36, 0.44, per) * (1 - _sstep(0.56, 0.64, per))
    M = 70 + 120 * web * edge + 40 * gate
    R = np.clip(50 + 120 * seam + 30 * (1 - web), 0, 255)
    Cc = 24 + 195 * web * gate * edge + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ H. MOIRE FAMILY
# 20. MOIRE SILK — two silk-fine lattices; giant slow rainbow beats roll
# across visible micro-threads.
@_memo
def _ss_moire_silk_f(h, w, s):
    lines, beat = moire_phase(h, w, s, pitch=3.8, d_angle=0.045, d_pitch=0.025)
    sheen = _noise(h, w, s ^ 0x91, (120, 300))
    return lines, beat, sheen


def _ss_moire_silk_paint(h, w, s):
    lines, beat, sheen = _ss_moire_silk_f(h, w, s)
    silk = spectral(beat, flatten=0.40)
    body = silk * (0.34 + 0.54 * lines + 0.10 * sheen)[..., None]
    return _polish(body, h, w, s)


def _ss_moire_silk_spec(h, w, s):
    lines, beat, sheen = _ss_moire_silk_f(h, w, s)
    gate = _sstep(0.40, 0.48, beat) * (1 - _sstep(0.60, 0.68, beat))
    M = 70 + 110 * lines + 50 * gate
    R = np.clip(70 + 70 * (1 - lines) + 40 * sheen, 0, 255)
    Cc = 24 + 190 * gate * lines + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 21. INTERFERENCE WEAVE — over-under thread weave where the BEAT phase decides
# each crossing's hue — textile moire.
@_memo
def _ss_interference_weave_f(h, w, s):
    rng = _rng(s, 19)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    a = float(rng.uniform(0, np.pi))
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    p = 9.0 * sr
    fu, fv = (u / p) % 1.0, (v / p) % 1.0
    ribU = (np.abs(fu - 0.5) < 0.34).astype(np.float32)
    ribV = (np.abs(fv - 0.5) < 0.34).astype(np.float32)
    over = ((np.floor(u / p) + np.floor(v / p)) % 2).astype(np.float32)
    lines, beat = moire_phase(h, w, s ^ 0x3, pitch=4.4, d_angle=0.05)
    return ribU, ribV, over, beat


def _ss_interference_weave_paint(h, w, s):
    ribU, ribV, over, beat = _ss_interference_weave_f(h, w, s)
    cA = spectral(beat, flatten=0.40)
    cB = spectral((beat + 0.45) % 1.0, flatten=0.40)
    th = np.where(over > 0.5, ribU, ribV)[..., None]
    body = cA * th * 0.9 + cB * (1 - th) * 0.55 + 0.04
    return _polish(body, h, w, s)


def _ss_interference_weave_spec(h, w, s):
    ribU, ribV, over, beat = _ss_interference_weave_f(h, w, s)
    th = np.where(over > 0.5, ribU, ribV)
    gate = _sstep(0.40, 0.48, beat) * (1 - _sstep(0.60, 0.68, beat))
    M = 60 + 120 * th + 50 * gate
    R = np.clip(70 + 90 * (1 - th) + 30 * _microtex(h, w, s ^ 5), 0, 255)
    Cc = 24 + 185 * th * gate + 50 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ I. HUE ADVECTION FAMILY
# 22. RAINBOW RIVER — spectrum as a fluid: hue streams along currents, eddies
# trap whirlpools of color; streamline filaments visible in the flow.
@_memo
def _ss_rainbow_river_f(h, w, s):
    th = _flow_theta(h, w, s, scale=140, turns=1.8, swirls=4)
    hue, speed = hue_advect(h, w, s, theta=th, steps=110)
    strands = _flowlines(h, w, s ^ 0x4, n=2200, steps=55, step_len=2.2, theta=th, thick=1, fade=True)
    return hue, speed, strands


def _ss_rainbow_river_paint(h, w, s):
    hue, speed, strands = _ss_rainbow_river_f(h, w, s)
    water = spectral(hue, flatten=0.36)
    body = water * (0.50 + 0.28 * speed + 0.35 * strands)[..., None]
    return _polish(body + 0.02, h, w, s)


def _ss_rainbow_river_spec(h, w, s):
    hue, speed, strands = _ss_rainbow_river_f(h, w, s)
    gate = _sstep(0.40, 0.48, hue) * (1 - _sstep(0.60, 0.68, hue))
    M = 55 + 130 * strands + 50 * speed
    R = np.clip(150 - 100 * strands + 40 * _microtex(h, w, s ^ 6), 0, 255)
    Cc = 22 + 190 * strands * gate + 50 * speed * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 23. MAGNET FLOW — spectrum advected along DIPOLE field lines: iron-filing
# arcs sweeping pole to pole, hue riding the field.
@_memo
def _ss_magnet_flow_f(h, w, s):
    rng = _rng(s, 23)
    yy, xx = _coords(h, w)
    bx = np.zeros((h, w), np.float32); by = np.zeros((h, w), np.float32)
    for _ in range(3):
        cx, cy = rng.uniform(0.1, 0.9) * w, rng.uniform(0.1, 0.9) * h
        a = rng.uniform(0, 2 * np.pi)
        mx, my = np.cos(a), np.sin(a)
        dx, dy = (xx - cx), (yy - cy)
        r2 = dx * dx + dy * dy + (30 * _sr(h, w)) ** 2
        r5 = r2 ** 2.5
        dot = dx * mx + dy * my
        bx += (3 * dx * dot / r5 - mx / r2 ** 1.5) * 1e7
        by += (3 * dy * dot / r5 - my / r2 ** 1.5) * 1e7
    th = np.arctan2(by, bx).astype(np.float32)
    hue, speed = hue_advect(h, w, s, theta=th, steps=90)
    filings = _flowlines(h, w, s ^ 0x5, n=2600, steps=46, step_len=2.0, theta=th, thick=1)
    return hue, filings, _n01(np.log1p(np.sqrt(bx * bx + by * by)))


def _ss_magnet_flow_paint(h, w, s):
    hue, filings, fieldmag = _ss_magnet_flow_f(h, w, s)
    body = np.float32([0.05, 0.05, 0.07])[None, None, :] * _finefill(h, w, s, 0.4, (2, 4))[..., None]
    body += spectral(hue, flatten=0.3) * (filings * 0.95 + fieldmag * 0.18)[..., None]
    return _polish(body, h, w, s, grain=0.07)


def _ss_magnet_flow_spec(h, w, s):
    hue, filings, fieldmag = _ss_magnet_flow_f(h, w, s)
    gate = _sstep(0.5, 0.58, fieldmag) * (1 - _sstep(0.72, 0.8, fieldmag))
    M = 40 + 170 * filings + 40 * fieldmag
    R = np.clip(160 - 120 * filings + 30 * _microtex(h, w, s ^ 7), 0, 255)
    Cc = 20 + 200 * filings * (0.4 + 0.6 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 24. SMOKE CHROMA — laminar smoke columns going turbulent, carrying spectrum;
# fine filament curls everywhere.
@_memo
def _ss_smoke_chroma_f(h, w, s):
    th = _flow_theta(h, w, s, scale=90, turns=2.6, swirls=6)
    hue, speed = hue_advect(h, w, s, theta=th, steps=130)
    wisps = np.maximum(
        _flowlines(h, w, s ^ 0x6, n=2000, steps=70, step_len=2.0, theta=th, thick=1, glow=2, fade=True),
        _flowlines(h, w, s ^ 0x7, n=1400, steps=50, step_len=1.7, theta=th, thick=1, fade=True) * 0.7)
    return hue, wisps


def _ss_smoke_chroma_paint(h, w, s):
    hue, wisps = _ss_smoke_chroma_f(h, w, s)
    body = np.float32([0.06, 0.06, 0.075])[None, None, :] * _finefill(h, w, s, 0.45, (2, 4))[..., None]
    body += spectral(hue, flatten=0.32) * (wisps * 0.95 + _gauss(wisps, 6) * 0.16)[..., None]
    return _polish(body, h, w, s, grain=0.07)


def _ss_smoke_chroma_spec(h, w, s):
    hue, wisps = _ss_smoke_chroma_f(h, w, s)
    gate = _sstep(0.40, 0.48, hue) * (1 - _sstep(0.60, 0.68, hue))
    M = 40 + 165 * wisps
    R = np.clip(175 - 130 * wisps + 30 * _microtex(h, w, s ^ 8), 0, 255)
    Cc = 20 + 195 * wisps * (0.4 + 0.6 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ J. BLACKBODY FAMILY
# 25. FORGE HEAT — Planck incandescence: hammered steel with white-hot zones
# cooling through orange to cherry to black, slag flecks, hammer dents.
@_memo
def _ss_forge_heat_f(h, w, s):
    temp = _n01(_noise(h, w, s ^ 0xA1, (50, 130, 300)) * 1.2 +
                _gauss(_flakes(h, w, s ^ 0xA2, density=0.015, bright=1.0), 22 * _sr(h, w)) * 2.0)
    dents = _sstep(0.3, 0.7, _noise(h, w, s ^ 0xA3, (7, 16)))
    slag = _flakes(h, w, s ^ 0xA4, density=0.06, bright=0.8)
    return temp, dents, slag


def _ss_forge_heat_paint(h, w, s):
    temp, dents, slag = _ss_forge_heat_f(h, w, s)
    body = blackbody(np.clip(temp * 1.1 - 0.08 * dents, 0, 1))
    body *= (0.78 + 0.22 * dents[..., None])
    body = body * (1 - 0.4 * slag[..., None]) + np.float32([0.10, 0.09, 0.09]) * slag[..., None]
    return _polish(body, h, w, s)


def _ss_forge_heat_spec(h, w, s):
    temp, dents, slag = _ss_forge_heat_f(h, w, s)
    gate = _sstep(0.55, 0.63, temp) * (1 - _sstep(0.78, 0.86, temp))
    M = 50 + 140 * temp + 40 * dents * (1 - temp)
    R = np.clip(150 - 100 * temp + 70 * slag, 0, 255)
    Cc = 22 + 195 * temp * gate + 40 * dents * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 26. STAR TEMPERATURE — the HR diagram as a sky: every star colored by its
# true class (M red dwarfs through O blue giants), dust lanes between.
@_memo
def _ss_star_temp_f(h, w, s):
    rng = _rng(s, 29)
    sr = _sr(h, w)
    img = np.zeros((h, w), np.float32)
    tmap = np.zeros((h, w), np.float32)
    n = int(16000 * sr * sr) + 3000
    xs = rng.uniform(0, w - 1, n); ys = rng.uniform(0, h - 1, n)
    tcls = rng.power(2.2, n).astype(np.float32)          # most stars cool/red
    mag = (0.25 + 0.75 * tcls) * rng.uniform(0.4, 1.0, n)
    ix, iy = xs.astype(np.int32), ys.astype(np.int32)
    np.maximum.at(img, (iy, ix), mag)
    np.maximum.at(tmap, (iy, ix), tcls)
    big = rng.random(n) > 0.985
    star_b = np.zeros((h, w), np.float32)
    np.maximum.at(star_b, (iy[big], ix[big]), mag[big])
    img = np.maximum(_gauss(img, 0.7), _gauss(star_b, 2.2 * sr) * 4.5)
    dust = _noise(h, w, s ^ 0xB1, (60, 150, 360))
    return np.clip(img, 0, 1), _gauss(tmap, 1.2), dust


def _ss_star_temp_paint(h, w, s):
    img, tmap, dust = _ss_star_temp_f(h, w, s)
    starc = blackbody(np.clip(tmap * 1.2, 0, 1), flatten=0.0)
    sky = _ramp([(0.03, 0.03, 0.06), (0.07, 0.06, 0.11), (0.12, 0.09, 0.14)], dust, flatten_lightness=0.3)
    body = sky + starc * (img * 1.1)[..., None]
    return _polish(body, h, w, s, grain=0.075)


def _ss_star_temp_spec(h, w, s):
    img, tmap, dust = _ss_star_temp_f(h, w, s)
    gate = _sstep(0.44, 0.52, dust) * (1 - _sstep(0.64, 0.72, dust))
    M = 35 + 180 * img
    R = np.clip(185 - 140 * img + 30 * _microtex(h, w, s ^ 9), 0, 255)
    Cc = 18 + 220 * img * (0.45 + 0.55 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ K. CHROMATIC SPLIT FAMILY
# 27. ABERRATION GLITCH — a crisp mono geometric field where EVERY edge grows
# lens-dispersion prism fringes — the broken-lens look.
@_memo
def _ss_aberration_f(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=1700, aniso=1.6, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    tile = _sstep(0.35, 0.65, per)
    return tile, edge


def _ss_aberration_paint(h, w, s):
    tile, edge = _ss_aberration_f(h, w, s)
    mono = np.repeat((0.16 + 0.62 * tile)[..., None], 3, 2).astype(np.float32)
    mono *= (0.7 + 0.3 * edge[..., None])
    body = chromatic_split(mono, s, amount=11.0)
    return _polish(body, h, w, s)


def _ss_aberration_spec(h, w, s):
    tile, edge = _ss_aberration_f(h, w, s)
    seam = 1.0 - _sstep(0.04, 0.14, edge)
    gate = _sstep(0.36, 0.44, tile) * (1 - _sstep(0.56, 0.64, tile))
    M = 70 + 110 * tile + 50 * seam
    R = np.clip(60 + 90 * (1 - tile) + 40 * seam, 0, 255)
    Cc = 24 + 190 * seam * (0.4 + 0.6 * gate) + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 28. GHOST PRISM — double-exposure: an attractor motif and its RGB-split
# ghosts offset in three directions — spectral echo art.
@_memo
def _ss_ghost_prism_f(h, w, s):
    from engine.expansions.redesign_wave2_2026 import _attractor
    fil = np.clip(_attractor(h, w, s, kind="clifford", span=1.9, sigma=0.018) * 3.4, 0, 1)
    return (fil,)


def _ss_ghost_prism_paint(h, w, s):
    (fil,) = _ss_ghost_prism_f(h, w, s)
    sr = _sr(h, w)
    base = np.float32([0.06, 0.06, 0.08])[None, None, :] * _finefill(h, w, s, 0.45, (2, 4))[..., None]
    rng = _rng(s, 31)
    body = base.copy()
    for i, col in enumerate((np.float32([1.0, 0.15, 0.2]), np.float32([0.15, 1.0, 0.35]), np.float32([0.25, 0.4, 1.0]))):
        a = rng.uniform(0, 2 * np.pi)
        d = (i + 1) * 4.5 * sr
        Mshift = np.float32([[1, 0, np.cos(a) * d], [0, 1, np.sin(a) * d]])
        ghost = cv2.warpAffine(fil, Mshift, (w, h), flags=cv2.INTER_LINEAR)
        body += col[None, None, :] * ghost[..., None] * 1.6
    body += fil[..., None] * 0.6
    return _polish(np.clip(body, 0, 1), h, w, s, grain=0.07)


def _ss_ghost_prism_spec(h, w, s):
    (fil,) = _ss_ghost_prism_f(h, w, s)
    halo = _gauss(fil, 7)
    gate = _sstep(0.35, 0.45, halo) * (1 - _sstep(0.6, 0.7, halo))
    M = 35 + 190 * fil
    R = np.clip(50 + 40 * _microtex(h, w, s ^ 1) + 70 * (1 - fil), 0, 255)
    Cc = 18 + 220 * fil * (0.4 + 0.6 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ L. CONTOUR FAMILY
# 29. TOPO RAINBOW — survey-fine elevation isolines cycling hue over shaded
# relief terrain.
@_memo
def _ss_topo_rainbow_f(h, w, s):
    line, elev, slope = spectral_contours(h, w, s, n_bands=34)
    return line, elev, slope


def _ss_topo_rainbow_paint(h, w, s):
    line, elev, slope = _ss_topo_rainbow_f(h, w, s)
    relief = _ramp([(0.10, 0.11, 0.14), (0.18, 0.19, 0.23), (0.26, 0.27, 0.31)], elev, flatten_lightness=0.25)
    body = relief * (0.7 + 0.3 * (1 - slope)[..., None])
    body += spectral(elev, flatten=0.30) * line[..., None] * 1.0
    return _polish(body, h, w, s)


def _ss_topo_rainbow_spec(h, w, s):
    line, elev, slope = _ss_topo_rainbow_f(h, w, s)
    gate = _sstep(0.44, 0.52, elev) * (1 - _sstep(0.64, 0.72, elev))
    M = 50 + 160 * line + 30 * slope
    R = np.clip(150 - 100 * line + 40 * slope, 0, 255)
    Cc = 22 + 200 * line * (0.4 + 0.6 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 30. PRESSURE MAP — meteorology: cyclone isobar spirals, wind-barb streaks,
# pressure cells cycling hue.
@_memo
def _ss_pressure_map_f(h, w, s):
    th = _flow_theta(h, w, s, scale=180, turns=0.8, swirls=5)
    line, elev, slope = spectral_contours(h, w, s ^ 0x9, n_bands=22, scales=(150, 380, 800))
    wind = _flowlines(h, w, s ^ 0xA, n=1100, steps=40, step_len=2.4, theta=th, thick=1)
    return line, elev, wind


def _ss_pressure_map_paint(h, w, s):
    line, elev, wind = _ss_pressure_map_f(h, w, s)
    cells = spectral(elev, flatten=0.46)
    body = cells * 0.45 + cells * line[..., None] * 0.75
    body += np.float32([0.95, 0.97, 1.0])[None, None, :] * wind[..., None] * 0.35
    return _polish(body + 0.02, h, w, s)


def _ss_pressure_map_spec(h, w, s):
    line, elev, wind = _ss_pressure_map_f(h, w, s)
    gate = _sstep(0.44, 0.52, elev) * (1 - _sstep(0.64, 0.72, elev))
    M = 55 + 140 * line + 50 * wind
    R = np.clip(140 - 90 * line + 40 * _microtex(h, w, s ^ 2), 0, 255)
    Cc = 22 + 190 * line * gate + 60 * wind * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ M. LATHE FAMILY
# 31. LATHE BURST — overlapping spin-cut systems; hue follows the cut angle
# like light raking turned metal.
@_memo
def _ss_lathe_burst_f(h, w, s):
    cuts, cutang = spectral_lathe(h, w, s, n_centers=16, pitch=4.2)
    return cuts, cutang


def _ss_lathe_burst_paint(h, w, s):
    cuts, cutang = _ss_lathe_burst_f(h, w, s)
    metal = np.float32([0.14, 0.14, 0.17])[None, None, :] * _finefill(h, w, s, 0.35, (2, 4))[..., None]
    body = metal + spectral(cutang, flatten=0.36) * (cuts * 0.85)[..., None]
    return _polish(body, h, w, s)


def _ss_lathe_burst_spec(h, w, s):
    cuts, cutang = _ss_lathe_burst_f(h, w, s)
    gate = _sstep(0.30, 0.40, cutang) * (1 - _sstep(0.60, 0.70, cutang))
    M = 70 + 150 * cuts
    R = np.clip(60 + 80 * (1 - cuts) + 30 * _microtex(h, w, s ^ 3), 0, 255)
    Cc = 24 + 195 * cuts * (0.35 + 0.65 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 32. CLOCKWORK DIAL — watch-dial guilloche: jittered rosettes + lathe rings +
# spectral order by cut angle. Horology porn.
@_memo
def _ss_clockwork_f(h, w, s):
    rose = _harmonograph(h, w, s, cells=24, pens=1, m=240, thick=1, jitter=0.36, decay=0.2)
    cuts, cutang = spectral_lathe(h, w, s ^ 0x5, n_centers=13, pitch=4.6)
    return rose, cuts, cutang


def _ss_clockwork_paint(h, w, s):
    rose, cuts, cutang = _ss_clockwork_f(h, w, s)
    plate = np.float32([0.07, 0.065, 0.06])[None, None, :] * _finefill(h, w, s, 0.4, (2, 4))[..., None]
    body = plate + spectral(cutang, flatten=0.30) * (cuts * 0.9)[..., None]
    body += np.float32([1.0, 0.82, 0.38])[None, None, :] * rose[..., None] * 0.6
    return _polish(body, h, w, s)


def _ss_clockwork_spec(h, w, s):
    rose, cuts, cutang = _ss_clockwork_f(h, w, s)
    gate = _sstep(0.30, 0.40, cutang) * (1 - _sstep(0.60, 0.70, cutang))
    M = 60 + 110 * rose + 70 * cuts
    R = np.clip(70 + 70 * (1 - rose) * (1 - cuts) + 30 * _microtex(h, w, s ^ 4), 0, 255)
    Cc = 24 + 190 * rose * (0.4 + 0.6 * gate) + 50 * cuts * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ N. DOPPLER FAMILY
# 33. REDSHIFT DRIFT — galaxies fleeing: motif streaks red-shifted trailing,
# blue-shifted leading, smeared along the expansion flow.
@_memo
def _ss_redshift_f(h, w, s):
    th = _flow_theta(h, w, s, scale=220, turns=0.6)
    base_hue = _noise(h, w, s ^ 0xC1, (70, 180, 400))
    hue = doppler_field(h, w, s, base_hue, theta=th, shift=0.3, smear=14)
    streaks = _flowlines(h, w, s ^ 0xC2, n=1900, steps=58, step_len=2.4, theta=th, thick=1, fade=True)
    return hue, streaks


def _ss_redshift_paint(h, w, s):
    hue, streaks = _ss_redshift_f(h, w, s)
    shift = _ramp([(1.0, 0.18, 0.10), (1.0, 0.55, 0.25), (0.85, 0.85, 0.85),
                   (0.35, 0.62, 1.0), (0.15, 0.30, 1.0)], hue, flatten_lightness=0.35)
    body = np.float32([0.05, 0.05, 0.07])[None, None, :] * _finefill(h, w, s, 0.4, (2, 4))[..., None]
    body += shift * (streaks * 0.95 + _gauss(streaks, 9) * 0.3)[..., None]
    return _polish(body, h, w, s, grain=0.07)


def _ss_redshift_spec(h, w, s):
    hue, streaks = _ss_redshift_f(h, w, s)
    gate = _sstep(0.55, 0.63, hue) * (1 - _sstep(0.75, 0.83, hue))   # blue side flashes
    M = 40 + 170 * streaks
    R = np.clip(170 - 130 * streaks + 30 * _microtex(h, w, s ^ 5), 0, 255)
    Cc = 20 + 200 * streaks * (0.35 + 0.65 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 34. EVENT HORIZON — accretion disk: doppler-beamed swirl (approaching side
# blue-hot, receding red-dim) around lensed black cores.
@_memo
def _ss_event_horizon_f(h, w, s):
    lensed, cores = einstein_arcs(h, w, s, n_masses=4, strength=34)
    rng = _rng(s, 37)
    yy, xx = _coords(h, w)
    cx, cy = rng.uniform(0.3, 0.7) * w, rng.uniform(0.3, 0.7) * h
    th = np.arctan2(yy - cy, xx - cx).astype(np.float32)
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    disk_th = (th + r / (60 * _sr(h, w))).astype(np.float32)   # swirl
    beaming = (0.5 + 0.5 * np.cos(disk_th)).astype(np.float32)
    disk = _flowlines(h, w, s ^ 0x8, n=2400, steps=50, step_len=2.2,
                      theta=(th + np.pi / 2).astype(np.float32), thick=1, fade=True)
    return lensed, cores, beaming, disk


def _ss_event_horizon_paint(h, w, s):
    lensed, cores, beaming, disk = _ss_event_horizon_f(h, w, s)
    dop = _ramp([(0.55, 0.05, 0.02), (1.0, 0.45, 0.10), (1.0, 0.92, 0.70), (0.55, 0.75, 1.0)],
                beaming, flatten_lightness=0.25)
    body = np.float32([0.03, 0.03, 0.05])[None, None, :] * _finefill(h, w, s, 0.45, (2, 4))[..., None]
    body += dop * (disk * 0.95)[..., None] + lensed[..., None] * np.float32([0.85, 0.88, 1.0]) * 0.45
    body *= (1 - 0.9 * cores[..., None])
    return _polish(body, h, w, s, grain=0.07)


def _ss_event_horizon_spec(h, w, s):
    lensed, cores, beaming, disk = _ss_event_horizon_f(h, w, s)
    gate = _sstep(0.6, 0.68, beaming) * (1 - _sstep(0.82, 0.9, beaming))
    M = 40 + 160 * disk * (0.5 + 0.5 * beaming) + 50 * lensed
    R = np.clip(60 + 150 * cores + 40 * (1 - disk), 0, 255)
    Cc = 18 + 210 * disk * gate + 60 * lensed * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ O. FACET PRISM FAMILY
# 35. SHATTER GLASS — broken safety glass: shard mosaic, each shard's interior
# dispersing its own gradient, prism fringes at every fracture edge.
@_memo
def _ss_shatter_glass_f(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=520, aniso=3.4, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    seam = 1.0 - _sstep(0.03, 0.10, edge)
    stria = (0.5 + 0.5 * np.sin(axial * 1.8 + per * 7)).astype(np.float32)
    return per, seam, stria, edge


def _ss_shatter_glass_paint(h, w, s):
    per, seam, stria, edge = _ss_shatter_glass_f(h, w, s)
    glass = _ramp([(0.10, 0.13, 0.17), (0.18, 0.23, 0.28), (0.30, 0.36, 0.42)], stria, flatten_lightness=0.2)
    body = glass + spectral((per + stria * 0.25) % 1.0, flatten=0.5) * (edge * 0.4)[..., None]
    body = chromatic_split(body, s, amount=3.5)
    body += np.float32([0.9, 0.95, 1.0])[None, None, :] * seam[..., None] * 0.30
    return _polish(np.clip(body, 0, 1), h, w, s)


def _ss_shatter_glass_spec(h, w, s):
    per, seam, stria, edge = _ss_shatter_glass_f(h, w, s)
    gate = _sstep(0.36, 0.44, per) * (1 - _sstep(0.56, 0.64, per))
    M = 70 + 110 * stria * edge + 60 * seam
    R = np.clip(50 + 110 * seam + 40 * (1 - stria), 0, 255)
    Cc = 24 + 190 * seam * (0.4 + 0.6 * gate) + 40 * stria * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 36. DIAMOND FIRE — brilliant-cut scintillation: kite-facet star mosaics with
# internal dispersion and white scintillation pins.
@_memo
def _ss_diamond_fire_f(h, w, s):
    rng = _rng(s, 41)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    facets = np.zeros((h, w), np.float32)
    fang = np.zeros((h, w), np.float32)
    best = np.zeros((h, w), np.float32)
    # PERF 2026-06-13 (bit-identical in-place combine): the masked assignment
    # below replaces 2 full np.where allocations per facet with in-place writes;
    # same result, fewer 1024^2 temporaries. (Half-res field build was tried and
    # REJECTED — kite-quantization shift dropped SSIM to 0.981; look is sacred.)
    for _ in range(16):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        th = np.arctan2(yy - cy, xx - cx)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        n_k = int(rng.uniform(13, 24))
        kite = (np.floor(((th / (2 * np.pi)) % 1.0) * n_k) / n_k).astype(np.float32)
        ring = (np.floor(r / (rng.uniform(14, 26) * sr))).astype(np.float32)
        f = _n01(np.sin(kite * 97.7 + ring * 31.3) + 1)
        env = (np.exp(-r / (rng.uniform(90, 200) * sr)) * rng.uniform(0.6, 1.0)).astype(np.float32)
        sel = env > best
        facets[sel] = f[sel]
        fang[sel] = kite[sel]
        np.maximum(best, env, out=best)
    pins = _flakes(h, w, s ^ 0xD2, density=0.04, bright=1.0)
    return facets, fang, pins


def _ss_diamond_fire_paint(h, w, s):
    facets, fang, pins = _ss_diamond_fire_f(h, w, s)
    ice = _ramp([(0.55, 0.58, 0.66), (0.78, 0.81, 0.88), (0.94, 0.96, 1.0)], facets, flatten_lightness=0.50)
    body = ice + spectral(fang, flatten=0.45) * (0.30 * _sstep(0.55, 0.9, facets))[..., None]
    body += pins[..., None] * 0.7
    return _polish(body, h, w, s)


def _ss_diamond_fire_spec(h, w, s):
    facets, fang, pins = _ss_diamond_fire_f(h, w, s)
    gate = _sstep(0.36, 0.44, fang) * (1 - _sstep(0.56, 0.64, fang))
    M = 90 + 100 * facets + 60 * pins
    R = np.clip(60 + 60 * (1 - facets) + 30 * _microtex(h, w, s ^ 6), 0, 255)
    Cc = 26 + 200 * pins + 80 * facets * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ P. GHOST REVEAL FAMILY
# 37. XRAY BLOOM — a garden in body color whose VEIN SKELETONS ignite spectral
# at the gate angle — the flowers x-ray themselves.
@_memo
def _ss_xray_bloom_f(h, w, s):
    petals = _gray_scott(h, w, s, "coral", iters=380, grid=448, seeds=36, fine=0.5, speckle=0.08)
    pm = _sstep(0.40, 0.60, petals)
    veins = _dendrites(h, w, s ^ 0xE1, n_roots=180, depth=5, seg=20 * _sr(h, w), thick=1)
    veins = veins * _sstep(0.3, 0.5, pm)        # veins only inside blooms
    vhue = _noise(h, w, s ^ 0xE2, (130, 320))
    return pm, veins, vhue


def _ss_xray_bloom_paint(h, w, s):
    pm, veins, vhue = _ss_xray_bloom_f(h, w, s)
    petal = _ramp([(0.16, 0.06, 0.16), (0.36, 0.12, 0.30), (0.55, 0.22, 0.42)], pm, flatten_lightness=0.3)
    body = petal * (0.55 + 0.45 * pm[..., None])
    body += spectral(vhue, flatten=0.3) * veins[..., None] * 0.55   # veins shimmer faintly in paint
    return _polish(body, h, w, s)


def _ss_xray_bloom_spec(h, w, s):
    pm, veins, vhue = _ss_xray_bloom_f(h, w, s)
    gate = _sstep(0.40, 0.48, vhue) * (1 - _sstep(0.60, 0.68, vhue))
    M = 40 + 90 * pm + 120 * veins
    R = np.clip(170 - 110 * pm - 40 * veins + 30 * _microtex(h, w, s ^ 7), 0, 255)
    Cc = 18 + 230 * veins * (0.35 + 0.65 * gate)     # the skeleton DETONATES
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 38. CIRCUIT AWAKENS — dormant trace-and-via circuitry that powers ON in
# spectral sequence at the flash angle.
@_memo
def _ss_circuit_f(h, w, s):
    rng = _rng(s, 43)
    sr = _sr(h, w)
    # Manhattan traces: H/V random walks
    polys = []
    n_tr = int(260 * sr * sr) + 40
    for _ in range(n_tr):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        pts = [[x, y]]
        for _k in range(int(rng.uniform(3, 7))):
            ln = rng.uniform(14, 60) * sr
            if rng.random() < 0.5:
                x = np.clip(x + rng.choice([-1, 1]) * ln, 0, w - 1)
            else:
                y = np.clip(y + rng.choice([-1, 1]) * ln, 0, h - 1)
            pts.append([x, y])
        polys.append(np.float32(pts))
    traces = _curves(h, w, polys, thick=1)
    vias = _flakes(h, w, s ^ 0xF1, density=0.035, bright=1.0)
    seq = _noise(h, w, s ^ 0xF2, (110, 280))
    return traces, vias, seq


def _ss_circuit_paint(h, w, s):
    traces, vias, seq = _ss_circuit_f(h, w, s)
    board = _ramp([(0.04, 0.09, 0.06), (0.06, 0.13, 0.09), (0.09, 0.18, 0.12)],
                  _noise(h, w, s ^ 0xF3, (40, 110)), flatten_lightness=0.15)
    body = board * _finefill(h, w, s, 0.3, (2, 4))[..., None]
    body += spectral(seq, flatten=0.32) * traces[..., None] * 0.75
    body += np.float32([1.0, 0.92, 0.6])[None, None, :] * vias[..., None] * 0.55
    return _polish(body, h, w, s, grain=0.07)


def _ss_circuit_spec(h, w, s):
    traces, vias, seq = _ss_circuit_f(h, w, s)
    gate = _sstep(0.40, 0.48, seq) * (1 - _sstep(0.60, 0.68, seq))
    M = 40 + 170 * traces + 60 * vias
    R = np.clip(160 - 120 * traces + 30 * _microtex(h, w, s ^ 8), 0, 255)
    Cc = 18 + 225 * traces * (0.3 + 0.7 * gate) + 80 * vias
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ Q. WILD CARDS — cross-engine one-offs
# 39. BISMUTH GARDEN — hopper-crystal stepped spirals, anodize spectrum by
# terrace depth — the rainbow staircase geode.
@_memo
def _ss_bismuth_f(h, w, s):
    lvl, depth, edge = hopper_terraces(h, w, s, n_crystals=110)
    return lvl, depth, edge


def _ss_bismuth_paint(h, w, s):
    lvl, depth, edge = _ss_bismuth_f(h, w, s)
    anod = _ramp([(0.80, 0.72, 0.45), (0.85, 0.45, 0.55), (0.45, 0.25, 0.70),
                  (0.12, 0.35, 0.75), (0.10, 0.62, 0.70), (0.75, 0.80, 0.82)],
                 (lvl * 1.6 + depth * 0.4) % 1.0, flatten_lightness=0.35)
    body = anod * (0.55 + 0.45 * edge[..., None])
    step = np.clip((np.abs(np.gradient(lvl)[0]) + np.abs(np.gradient(lvl)[1])) * 4, 0, 0.5)
    body *= (1 - step[..., None])
    return _polish(body, h, w, s)


def _ss_bismuth_spec(h, w, s):
    lvl, depth, edge = _ss_bismuth_f(h, w, s)
    step = np.clip((np.abs(np.gradient(lvl)[0]) + np.abs(np.gradient(lvl)[1])) * 4, 0, 1)
    gate = _sstep(0.36, 0.44, depth) * (1 - _sstep(0.56, 0.64, depth))
    M = 90 + 90 * edge + 60 * step
    R = np.clip(60 + 90 * step + 30 * (1 - edge), 0, 255)
    Cc = 26 + 190 * step * (0.4 + 0.6 * gate) + 40 * edge * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 40. ANODINE DUNES — wind-ripple dune field; anodize hue rides the slip-face
# aspect, grating-fine ripples everywhere.
@_memo
def _ss_anodine_dunes_f(h, w, s):
    rng = _rng(s, 47)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    a = float(rng.uniform(0, np.pi))
    wy, wx = _warp(yy, xx, h, w, s ^ 0x11, 90 * sr)
    phase = wx * np.cos(a) + wy * np.sin(a)
    rip = (0.5 + 0.5 * np.sin(phase * (2 * np.pi / (7.5 * sr)))).astype(np.float32)
    dune = _noise(h, w, s ^ 0x12, (140, 340, 700))
    gy, gx = np.gradient(_gauss(dune, 6))
    aspect = _n01(np.arctan2(gy, gx))
    return rip, dune, aspect


def _ss_anodine_dunes_paint(h, w, s):
    rip, dune, aspect = _ss_anodine_dunes_f(h, w, s)
    anod = _ramp([(0.85, 0.55, 0.25), (0.70, 0.30, 0.55), (0.25, 0.30, 0.72),
                  (0.10, 0.55, 0.70), (0.82, 0.70, 0.40)], aspect, flatten_lightness=0.40)
    body = anod * (0.50 + 0.34 * rip + 0.16 * dune)[..., None]
    return _polish(body, h, w, s)


def _ss_anodine_dunes_spec(h, w, s):
    rip, dune, aspect = _ss_anodine_dunes_f(h, w, s)
    gate = _sstep(0.36, 0.44, aspect) * (1 - _sstep(0.56, 0.64, aspect))
    M = 80 + 110 * rip
    R = np.clip(70 + 70 * (1 - rip) + 40 * dune, 0, 255)
    Cc = 24 + 185 * rip * (0.35 + 0.65 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 41. PEACOCK EYE — scattered structural-color eyespots (cobalt heart, teal
# iris, bronze halo) over a fine radiating barb field.
@_memo
def _ss_peacock_f(h, w, s):
    rng = _rng(s, 53)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    th = _flow_theta(h, w, s ^ 0x21, scale=170, turns=1.0)
    barbs = _engrave(h, w, _noise(h, w, s ^ 0x22, (50, 130)), s, pitch=3.6, curl=40, sharp=4.0)
    h2, w2 = h // 2, w // 2
    yy2, xx2 = _coords(h2, w2)
    eye_r = np.full((h2, w2), 9.0, np.float32)
    ring = np.zeros((h2, w2), np.float32)
    heart = np.zeros((h2, w2), np.float32)
    # PERF 2026-06-13 (windowed eyespots, look-equivalent): each eyespot only
    # affects pixels within ~R0 of its center (ring nonzero r<0.95, heart r<0.56,
    # and eye_r is clipped to 1.5 == r<1.5*R0 downstream). The old loop ran a
    # full-half-grid sqrt+max/min PER eyespot (~94x). Window each splat to a
    # generous bbox (2.5*R0, well past every support+the resize neighborhood);
    # untouched pixels keep eye_r=9.0 which clips to 1.5 exactly like a far min.
    for _ in range(int(80 * sr * sr) + 14):
        cx, cy = rng.uniform(0, w2), rng.uniform(0, h2)
        R0 = rng.uniform(6, 15) * sr
        win = int(np.ceil(2.5 * R0)) + 2
        x0 = max(0, int(cx) - win); x1 = min(w2, int(cx) + win + 1)
        y0 = max(0, int(cy) - win); y1 = min(h2, int(cy) + win + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        rdx = xx2[:, x0:x1] - cx
        rdy = yy2[y0:y1, :] - cy
        r = np.sqrt(rdx * rdx + rdy * rdy) / R0          # (y1-y0, x1-x0) via broadcast
        sub_ring = ring[y0:y1, x0:x1]
        np.maximum(sub_ring, np.clip(1 - np.abs(r - 0.75) * 5, 0, 1), out=sub_ring)
        sub_heart = heart[y0:y1, x0:x1]
        np.maximum(sub_heart, np.clip(1 - r * 1.8, 0, 1), out=sub_heart)
        sub_eye = eye_r[y0:y1, x0:x1]
        np.minimum(sub_eye, r, out=sub_eye)
    ring = cv2.resize(ring, (w, h)); heart = cv2.resize(heart, (w, h))
    eye_r = cv2.resize(eye_r, (w, h))
    return barbs, ring, heart, np.clip(eye_r, 0, 1.5)


def _ss_peacock_paint(h, w, s):
    barbs, ring, heart, eye_r = _ss_peacock_f(h, w, s)
    train = _ramp([(0.04, 0.30, 0.18), (0.08, 0.48, 0.28), (0.16, 0.66, 0.38)],
                  _noise(h, w, s ^ 0x23, (90, 230)), flatten_lightness=0.3)
    body = train * (0.42 + 0.58 * barbs[..., None])
    body += np.float32([0.72, 0.50, 0.18])[None, None, :] * ring[..., None] * 0.8
    body += np.float32([0.05, 0.16, 0.65])[None, None, :] * heart[..., None] * 1.0
    body += np.float32([0.05, 0.75, 0.65])[None, None, :] * np.clip(1 - np.abs(eye_r - 0.45) * 6, 0, 1)[..., None] * 0.8
    return _polish(body, h, w, s)


def _ss_peacock_spec(h, w, s):
    barbs, ring, heart, eye_r = _ss_peacock_f(h, w, s)
    iris = np.clip(1 - np.abs(eye_r - 0.45) * 6, 0, 1)
    gate = _sstep(0.30, 0.42, eye_r) * (1 - _sstep(0.62, 0.74, eye_r))
    M = 50 + 110 * barbs + 90 * heart
    R = np.clip(150 - 90 * heart - 60 * iris + 40 * barbs, 0, 255)
    Cc = 20 + 210 * heart * gate + 90 * iris * gate + 30 * ring
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 42. BEETLE ELYTRA — jewel-scarab shell: hexagonal micro-dimple lattice with
# directional metallic green-gold bands sweeping across.
@_memo
def _ss_beetle_f(h, w, s):
    rng = _rng(s, 59)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    p = 6.5 * sr
    hx = xx / p
    hy = (yy / p) * 1.1547
    row = np.floor(hy)
    hxo = hx + (row % 2) * 0.5
    du = hxo - np.floor(hxo + 0.5)
    dv = hy - np.floor(hy + 0.5)
    dimple = np.clip(1 - (du * du + dv * dv) * 5.0, 0, 1).astype(np.float32)
    a = float(rng.uniform(0, np.pi))
    wy, wx = _warp(yy, xx, h, w, s ^ 0x31, 60 * sr)
    bands = _n01(np.sin((wx * np.cos(a) + wy * np.sin(a)) * (2 * np.pi / (240 * sr))) +
                 _noise(h, w, s ^ 0x32, (160, 380)))
    return dimple, bands


def _ss_beetle_paint(h, w, s):
    dimple, bands = _ss_beetle_f(h, w, s)
    shell = _ramp([(0.02, 0.30, 0.10), (0.10, 0.55, 0.12), (0.55, 0.62, 0.08),
                   (0.75, 0.45, 0.08), (0.06, 0.40, 0.35)], bands, flatten_lightness=0.30)
    body = shell * (0.60 + 0.40 * dimple[..., None])
    return _polish(body, h, w, s)


def _ss_beetle_spec(h, w, s):
    dimple, bands = _ss_beetle_f(h, w, s)
    gate = _sstep(0.40, 0.48, bands) * (1 - _sstep(0.60, 0.68, bands))
    M = 80 + 120 * dimple
    R = np.clip(60 + 80 * (1 - dimple) + 30 * _microtex(h, w, s ^ 1), 0, 255)
    Cc = 24 + 190 * dimple * (0.35 + 0.65 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 43. NACRE TIDE — abalone growth terraces: wavy stacked layer lines, hue by
# layer count, conchiolin dark seams between terraces.
@_memo
def _ss_nacre_f(h, w, s):
    yy, xx = _coords(h, w)
    sr = _sr(h, w)
    wy, wx = _warp(yy, xx, h, w, s ^ 0x41, 110 * sr)
    growth = _n01(wx * 0.0008 + _noise(h, w, s ^ 0x42, (80, 200, 440)) * 1.4)
    layers = (growth * 26) % 1.0
    line = _sstep(0.0, 0.14, layers) * (1 - _sstep(0.14, 0.30, layers))
    return growth, layers.astype(np.float32), line.astype(np.float32)


def _ss_nacre_paint(h, w, s):
    growth, layers, line = _ss_nacre_f(h, w, s)
    pearl = _ipal(growth, 4.0, 0.85, np.float32([0.70, 0.72, 0.76]))
    body = pearl * (0.80 + 0.20 * np.abs(np.cos(layers * np.pi))[..., None])
    body *= (1 - 0.45 * line[..., None])
    return _polish(body, h, w, s)


def _ss_nacre_spec(h, w, s):
    growth, layers, line = _ss_nacre_f(h, w, s)
    gate = _sstep(0.40, 0.48, growth) * (1 - _sstep(0.60, 0.68, growth))
    bandv = np.abs(np.cos(layers * np.pi))
    M = 70 + 120 * bandv + 40 * gate
    R = np.clip(60 + 110 * line + 30 * (1 - bandv), 0, 255)
    Cc = 24 + 185 * bandv * gate + 50 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 44. BOREALIS ICE — aurora curtains REFRACTED through pack-ice shards: each
# shard displaces and recolors the light passing through it.
@_memo
def _ss_borealis_ice_f(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=420, aniso=3.0, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    th = _flow_theta(h, w, s ^ 0x51, scale=130, turns=1.2)
    curt = _flowlines(h, w, s ^ 0x52, n=2200, steps=60, step_len=2.4, theta=th, thick=1, glow=2.5, fade=True)
    # refract: shift the curtain per shard
    sr = _sr(h, w)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (per - 0.5) * 14 * sr
    curt_r = cv2.remap(curt, xx + dx, yy + dx * 0.6, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    seam = 1.0 - _sstep(0.04, 0.12, edge)
    return curt_r.astype(np.float32), per, seam


def _ss_borealis_ice_paint(h, w, s):
    curt, per, seam = _ss_borealis_ice_f(h, w, s)
    aur = spectral((per * 0.5 + curt * 0.5) % 1.0, flatten=0.34)
    night = np.float32([0.04, 0.05, 0.09])[None, None, :] * _finefill(h, w, s, 0.4, (2, 4))[..., None]
    body = night + aur * (curt * 0.95 + _gauss(curt, 5) * 0.16)[..., None]
    body += np.float32([0.85, 0.93, 1.0])[None, None, :] * seam[..., None] * 0.18
    return _polish(body, h, w, s, grain=0.075)


def _ss_borealis_ice_spec(h, w, s):
    curt, per, seam = _ss_borealis_ice_f(h, w, s)
    gate = _sstep(0.36, 0.44, per) * (1 - _sstep(0.56, 0.64, per))
    M = 40 + 160 * curt + 40 * seam
    R = np.clip(170 - 120 * curt + 40 * seam, 0, 255)
    Cc = 20 + 200 * curt * (0.4 + 0.6 * gate) + 40 * seam * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 45. SPILL METROPOLIS — gasoline rainbow over wet night asphalt: aggregate
# micro-stones, drain swirls, neon-bleed reflections.
@_memo
def _ss_spill_metro_f(h, w, s):
    rng = _rng(s, 61)
    sr = _sr(h, w)
    film = _n01(_noise(h, w, s ^ 0x61, (60, 150, 340)) +
                _dirblur(_noise(h, w, s ^ 0x62, (10, 26)), float(rng.uniform(0, np.pi)), int(50 * sr)))
    agg = _sstep(0.62, 0.86, _noise(h, w, s ^ 0x63, (2.5, 5)))
    bleed = _dirblur(_flakes(h, w, s ^ 0x64, density=0.02, bright=1.0), float(rng.uniform(0, np.pi)), int(90 * sr))
    return film, agg, np.clip(bleed * 3, 0, 1)


def _ss_spill_metro_paint(h, w, s):
    film, agg, bleed = _ss_spill_metro_f(h, w, s)
    slick = _ipal(film, 5.0, 0.95, np.float32([0.16, 0.17, 0.20]))
    body = slick * (1 - 0.6 * agg[..., None]) + np.float32([0.05, 0.05, 0.06]) * agg[..., None]
    body += spectral(_noise(h, w, s ^ 0x65, (200, 480)), flatten=0.4) * bleed[..., None] * 0.5
    return _polish(body, h, w, s)


def _ss_spill_metro_spec(h, w, s):
    film, agg, bleed = _ss_spill_metro_f(h, w, s)
    gate = _sstep(0.44, 0.52, film) * (1 - _sstep(0.64, 0.72, film))
    M = 80 + 100 * (1 - agg) + 50 * bleed
    R = np.clip(40 + 170 * agg, 0, 255)
    Cc = 22 + 190 * (1 - agg) * gate + 70 * bleed
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 46. CHROMATIC ORCHID — orchid petal fields with spectral nectar-guide veins
# (the UV runway insects see, made visible).
@_memo
def _ss_orchid_f(h, w, s):
    petals = _gray_scott(h, w, s, "solitons", iters=340, grid=448, seeds=18, fine=0.55, speckle=0.10)
    pm = _sstep(0.35, 0.60, petals)
    th = _flow_theta(h, w, s ^ 0x71, scale=110, turns=1.4)
    guides = _flowlines(h, w, s ^ 0x72, n=1500, steps=42, step_len=2.0, theta=th, thick=1) * pm
    speck = _flakes(h, w, s ^ 0x73, density=0.06, bright=0.8) * pm
    return pm, guides, speck


def _ss_orchid_paint(h, w, s):
    pm, guides, speck = _ss_orchid_f(h, w, s)
    petal = _ramp([(0.55, 0.12, 0.42), (0.80, 0.30, 0.60), (0.95, 0.62, 0.82)], pm, flatten_lightness=0.30)
    ground = np.float32([0.08, 0.05, 0.09])[None, None, :]
    body = ground * (1 - pm[..., None]) + petal * pm[..., None]
    body += spectral(_noise(h, w, s ^ 0x74, (140, 340)), flatten=0.3) * guides[..., None] * 0.7
    body += speck[..., None] * 0.4
    return _polish(body, h, w, s)


def _ss_orchid_spec(h, w, s):
    pm, guides, speck = _ss_orchid_f(h, w, s)
    drift = _noise(h, w, s ^ 0x75, (130, 320))
    gate = _sstep(0.44, 0.52, drift) * (1 - _sstep(0.64, 0.72, drift))
    M = 45 + 90 * pm + 110 * guides
    R = np.clip(170 - 110 * pm + 30 * _microtex(h, w, s ^ 2), 0, 255)
    Cc = 20 + 215 * guides * (0.35 + 0.65 * gate) + 70 * speck
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 47. MANTIS STRIKE — mantis-shrimp carapace: segmented armor plates, each
# segment cycling its own spectral band, raptorial streak accents.
@_memo
def _ss_mantis_f(h, w, s):
    yy, xx = _coords(h, w)
    rng = _rng(s, 67)
    sr = _sr(h, w)
    a = float(rng.uniform(0, np.pi))
    wy, wx = _warp(yy, xx, h, w, s ^ 0x81, 40 * sr)
    u = wx * np.cos(a) + wy * np.sin(a)
    seg = np.floor(u / (38 * sr))
    per = _n01(np.sin(seg * 12.99) + 1)
    fu = (u / (38 * sr)) % 1.0
    plate = _sstep(0.04, 0.16, fu) * (1 - _sstep(0.84, 0.96, fu))
    ridges = (0.5 + 0.5 * np.sin(u * (2 * np.pi / (4.6 * sr)))).astype(np.float32)
    streaks = _flowlines(h, w, s ^ 0x82, n=700, steps=30, step_len=2.6,
                         theta=np.full((h, w), a + np.pi / 2, np.float32), thick=1, fade=True)
    return per.astype(np.float32), plate.astype(np.float32), ridges, streaks


def _ss_mantis_paint(h, w, s):
    per, plate, ridges, streaks = _ss_mantis_f(h, w, s)
    armor = spectral(per, flatten=0.32)
    body = armor * (0.40 + 0.40 * plate + 0.20 * ridges)[..., None]
    body += np.float32([1.0, 0.45, 0.15])[None, None, :] * streaks[..., None] * 0.6
    return _polish(body + 0.02, h, w, s)


def _ss_mantis_spec(h, w, s):
    per, plate, ridges, streaks = _ss_mantis_f(h, w, s)
    gate = _sstep(0.36, 0.44, per) * (1 - _sstep(0.56, 0.64, per))
    M = 60 + 110 * ridges * plate + 60 * streaks
    R = np.clip(70 + 90 * (1 - plate) + 30 * (1 - ridges), 0, 255)
    Cc = 22 + 190 * ridges * plate * gate + 70 * streaks * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 48. VHS PHANTOM — analog video breakdown: scanline micro, tracking-error
# spectral tear bands, double-image ghosts.
@_memo
def _ss_vhs_f(h, w, s):
    rng = _rng(s, 71)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    a = float(rng.uniform(0, np.pi))
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    scan = (0.5 + 0.5 * np.sin(v * (2 * np.pi / (3.0 * sr)))).astype(np.float32)
    tear_pos = _noise(h, w, s ^ 0x91, (200, 520))
    tear = np.maximum.reduce([
        _sstep(0.30 + k * 0.17, 0.33 + k * 0.17, tear_pos) * (1 - _sstep(0.40 + k * 0.17, 0.43 + k * 0.17, tear_pos))
        for k in range(3)]).astype(np.float32)
    sig = _noise(h, w, s ^ 0x92, (18, 50, 130))
    return scan, tear.astype(np.float32), sig, a


def _ss_vhs_paint(h, w, s):
    scan, tear, sig, a = _ss_vhs_f(h, w, s)
    base = _ramp([(0.10, 0.11, 0.15), (0.18, 0.20, 0.26), (0.28, 0.30, 0.38)], sig, flatten_lightness=0.2)
    body = base * (0.58 + 0.42 * scan[..., None])
    body += spectral(sig, flatten=0.35) * tear[..., None] * 0.9
    body = chromatic_split(body, s, amount=4.0,
                           theta=np.full((h, w), a, np.float32))
    return _polish(np.clip(body, 0, 1), h, w, s, grain=0.075)


def _ss_vhs_spec(h, w, s):
    scan, tear, sig, a = _ss_vhs_f(h, w, s)
    gate = _sstep(0.44, 0.52, sig) * (1 - _sstep(0.64, 0.72, sig))
    M = 55 + 110 * scan + 70 * tear
    R = np.clip(130 - 80 * scan + 50 * tear, 0, 255)
    Cc = 22 + 200 * tear * (0.4 + 0.6 * gate) + 40 * scan * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 49. FLARE SPECTRA — spectroheliograph corona: thin emission-line arcs in pure
# spectral colors leaping across near-black, prominence loops.
@_memo
def _ss_flare_spectra_f(h, w, s):
    rng = _rng(s, 73)
    sr = _sr(h, w)
    polys, hues = [], []
    for _ in range(int(70 * sr * sr) + 14):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(20, 130) * sr
        a0 = rng.uniform(0, 2 * np.pi)
        al = rng.uniform(0.7, 2.4)
        aa = np.linspace(a0, a0 + al, 30)
        sq = rng.uniform(0.35, 1.0)
        polys.append(np.stack([cx + np.cos(aa) * r, cy + np.sin(aa) * r * sq], -1))
        hues.append(rng.random())
    # PERF 2026-06-13 (windowed per-arc, look-equivalent): the old loop ran a
    # full-(h,w) _curves+_gauss glow PER arc (~84x full-grid GaussianBlur). Each
    # arc lives in a tiny bbox, so rasterize+glow it in a local window with a
    # margin (>> the sigma-2.2 kernel radius) — the isolated-arc blur and the
    # max/where combine are identical to the global path within that window.
    arcs = np.zeros((h, w), np.float32)
    hmap = np.zeros((h, w), np.float32)
    MGN = 18
    for p, hu in zip(polys, hues):
        x0 = int(np.floor(p[:, 0].min())) - MGN; x1 = int(np.ceil(p[:, 0].max())) + MGN
        y0 = int(np.floor(p[:, 1].min())) - MGN; y1 = int(np.ceil(p[:, 1].max())) + MGN
        x0 = max(0, x0); y0 = max(0, y0); x1 = min(w, x1); y1 = min(h, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        ww, wh = x1 - x0, y1 - y0
        one = _curves(wh, ww, [p - np.float32([x0, y0])], thick=1, glow=2.2)
        sub_a = arcs[y0:y1, x0:x1]
        np.maximum(sub_a, one, out=sub_a)
        sub_h = hmap[y0:y1, x0:x1]
        np.copyto(sub_h, hu, where=(one > 0.1))
    spik = _flakes(h, w, s ^ 0xA1, density=0.03, bright=0.9)
    return arcs, _gauss(hmap, 3), spik


def _ss_flare_spectra_paint(h, w, s):
    arcs, hmap, spik = _ss_flare_spectra_f(h, w, s)
    body = np.float32([0.06, 0.06, 0.075])[None, None, :] * _finefill(h, w, s, 0.5, (2, 4))[..., None]
    body += spectral(hmap, flatten=0.25) * (arcs * 1.25)[..., None]
    body += np.float32([1.0, 0.9, 0.7])[None, None, :] * spik[..., None] * 0.4
    return _polish(body, h, w, s, grain=0.07)


def _ss_flare_spectra_spec(h, w, s):
    arcs, hmap, spik = _ss_flare_spectra_f(h, w, s)
    gate = _sstep(0.30, 0.42, hmap) * (1 - _sstep(0.58, 0.70, hmap))
    M = 35 + 185 * arcs
    R = np.clip(60 + 40 * _microtex(h, w, s ^ 3) + 60 * (1 - arcs), 0, 255)
    Cc = 18 + 225 * arcs * (0.35 + 0.65 * gate) + 60 * spik
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# 50. SINGULARITY LENS — deep-field sky gravitationally smeared into Einstein
# arcs and rings around invisible dark masses.
@_memo
def _ss_singularity_f(h, w, s):
    lensed, cores = einstein_arcs(h, w, s, n_masses=8, strength=30)
    hueb = _noise(h, w, s ^ 0xB1, (90, 230, 520))
    return lensed, cores, hueb


def _ss_singularity_paint(h, w, s):
    lensed, cores, hueb = _ss_singularity_f(h, w, s)
    body = np.float32([0.03, 0.03, 0.05])[None, None, :] * _finefill(h, w, s, 0.45, (2, 4))[..., None]
    galaxy = spectral(hueb, flatten=0.40)
    body += galaxy * (lensed * 1.05)[..., None]
    body *= (1 - 0.92 * cores[..., None])
    ring = np.clip(_gauss(cores, 4) - cores, 0, 1)
    body += np.float32([0.75, 0.55, 1.0])[None, None, :] * ring[..., None] * 0.8
    return _polish(body, h, w, s, grain=0.075)


def _ss_singularity_spec(h, w, s):
    lensed, cores, hueb = _ss_singularity_f(h, w, s)
    ring = np.clip(_gauss(cores, 4) - cores, 0, 1)
    gate = _sstep(0.44, 0.52, hueb) * (1 - _sstep(0.64, 0.72, hueb))
    M = 35 + 170 * lensed + 60 * ring
    R = np.clip(70 + 140 * cores + 30 * _microtex(h, w, s ^ 4), 0, 255)
    Cc = 18 + 215 * (lensed + ring) * (0.4 + 0.6 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════ REGISTRY + LIVE WIRING
SS_DESIGNS = {
    "spectrum_stress_storm":      (_ss_stress_storm_paint, _ss_stress_storm_spec),
    "spectrum_fracture_polarized": (_ss_fracture_pol_paint, _ss_fracture_pol_spec),
    "spectrum_tempered_ghost":    (_ss_tempered_ghost_paint, _ss_tempered_ghost_spec),
    "spectrum_abrasion_halo":     (_ss_abrasion_halo_paint, _ss_abrasion_halo_spec),
    "spectrum_orbital_engrave":   (_ss_orbital_engrave_paint, _ss_orbital_engrave_spec),
    "spectrum_swirl_supernova":   (_ss_swirl_nova_paint, _ss_swirl_nova_spec),
    "spectrum_vinyl_groove":      (_ss_vinyl_groove_paint, _ss_vinyl_groove_spec),
    "spectrum_data_etch":         (_ss_data_etch_paint, _ss_data_etch_spec),
    "spectrum_grating_quilt":     (_ss_grating_quilt_paint, _ss_grating_quilt_spec),
    "spectrum_liquid_crystal":    (_ss_liquid_crystal_paint, _ss_liquid_crystal_spec),
    "spectrum_thermo_touch":      (_ss_thermo_touch_paint, _ss_thermo_touch_spec),
    "spectrum_smectic_fan":       (_ss_smectic_fan_paint, _ss_smectic_fan_spec),
    "spectrum_black_opal":        (_ss_black_opal_paint, _ss_black_opal_spec),
    "spectrum_boulder_opal":      (_ss_boulder_opal_paint, _ss_boulder_opal_spec),
    "spectrum_opal_core":         (_ss_opal_core_paint, _ss_opal_core_spec),
    "spectrum_contact_bloom":     (_ss_contact_bloom_paint, _ss_contact_bloom_spec),
    "spectrum_oilfilm_rain":      (_ss_oilfilm_rain_paint, _ss_oilfilm_rain_spec),
    "spectrum_prism_pool":        (_ss_prism_pool_paint, _ss_prism_pool_spec),
    "spectrum_jewel_box":         (_ss_jewel_box_paint, _ss_jewel_box_spec),
    "spectrum_moire_silk":        (_ss_moire_silk_paint, _ss_moire_silk_spec),
    "spectrum_interference_weave": (_ss_interference_weave_paint, _ss_interference_weave_spec),
    "spectrum_rainbow_river":     (_ss_rainbow_river_paint, _ss_rainbow_river_spec),
    "spectrum_magnet_flow":       (_ss_magnet_flow_paint, _ss_magnet_flow_spec),
    "spectrum_smoke_chroma":      (_ss_smoke_chroma_paint, _ss_smoke_chroma_spec),
    "spectrum_forge_heat":        (_ss_forge_heat_paint, _ss_forge_heat_spec),
    "spectrum_star_temperature":  (_ss_star_temp_paint, _ss_star_temp_spec),
    "spectrum_aberration_glitch": (_ss_aberration_paint, _ss_aberration_spec),
    "spectrum_ghost_prism":       (_ss_ghost_prism_paint, _ss_ghost_prism_spec),
    "spectrum_topo_rainbow":      (_ss_topo_rainbow_paint, _ss_topo_rainbow_spec),
    "spectrum_pressure_map":      (_ss_pressure_map_paint, _ss_pressure_map_spec),
    "spectrum_lathe_burst":       (_ss_lathe_burst_paint, _ss_lathe_burst_spec),
    "spectrum_clockwork_dial":    (_ss_clockwork_paint, _ss_clockwork_spec),
    "spectrum_redshift_drift":    (_ss_redshift_paint, _ss_redshift_spec),
    "spectrum_event_horizon":     (_ss_event_horizon_paint, _ss_event_horizon_spec),
    "spectrum_shatter_glass":     (_ss_shatter_glass_paint, _ss_shatter_glass_spec),
    "spectrum_diamond_fire":      (_ss_diamond_fire_paint, _ss_diamond_fire_spec),
    "spectrum_xray_bloom":        (_ss_xray_bloom_paint, _ss_xray_bloom_spec),
    "spectrum_circuit_awakens":   (_ss_circuit_paint, _ss_circuit_spec),
    "spectrum_bismuth_garden":    (_ss_bismuth_paint, _ss_bismuth_spec),
    "spectrum_anodine_dunes":     (_ss_anodine_dunes_paint, _ss_anodine_dunes_spec),
    "spectrum_peacock_eye":       (_ss_peacock_paint, _ss_peacock_spec),
    "spectrum_beetle_elytra":     (_ss_beetle_paint, _ss_beetle_spec),
    "spectrum_nacre_tide":        (_ss_nacre_paint, _ss_nacre_spec),
    "spectrum_borealis_ice":      (_ss_borealis_ice_paint, _ss_borealis_ice_spec),
    "spectrum_spill_metropolis":  (_ss_spill_metro_paint, _ss_spill_metro_spec),
    "spectrum_chromatic_orchid":  (_ss_orchid_paint, _ss_orchid_spec),
    "spectrum_mantis_strike":     (_ss_mantis_paint, _ss_mantis_spec),
    "spectrum_vhs_phantom":       (_ss_vhs_paint, _ss_vhs_spec),
    "spectrum_flare_spectra":     (_ss_flare_spectra_paint, _ss_flare_spectra_spec),
    "spectrum_singularity_lens":  (_ss_singularity_paint, _ss_singularity_spec),
}


def _ss_mk_finish(fid):
    paint_d, spec_d = SS_DESIGNS[fid]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        eff = _up(paint_d(_WORK, _WORK, _seed_int(seed)), fh, fw)
        eff = _native_finish(eff, seed)
        base = np.asarray(paint, np.float32)[:, :, :3]
        m = (_m2(mask, fh, fw) * float(pm))[..., None]
        return np.clip(base * (1.0 - m) + eff * m, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        M, R, Cc = spec_d(_WORK, _WORK, _seed_int(seed))
        return _pack(_up(M, fh, fw), _up(R, fh, fw), _up(Cc, fh, fw), _m2(mask, fh, fw), float(sm))

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Replace the 50 palette-clone spectrum_* ids with the 50 new finishes.
    Mutates the fusions module's FUSION_REGISTRY (the UI group map source),
    the engine's FUSION_REGISTRY and MONOLITHIC_REGISTRY."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        _fus = None
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    n_rm = 0
    old = None
    for reg in regs:
        old = [k for k in reg if k.startswith("spectrum_") and k not in SS_DESIGNS]
        for k in old:
            reg.pop(k, None)
            n_rm += 1
    n_new = 0
    for fid in SS_DESIGNS:
        entry = _ss_mk_finish(fid)
        for reg in regs:
            reg[fid] = entry
        n_new += 1
    return "spectrum-shift: %d new finishes registered, %d old clone entries removed" % (n_new, n_rm)
