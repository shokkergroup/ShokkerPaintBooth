"""
iridescent_flip.py — wild-spec-v2 family 'iridescent_flip' (10 finishes).

wild-spec-v2 2026-06-07. The owner REJECTED v1 (make_wild_spec in
wild_spec_lab.py) ON SIGHT AS LAZY: one generator template + per-finish scalar
dials, with M/R/Cc all derived from the SAME fields, so the channels correlated
and every composite map read as ONE hue. Owner's words: "VERY LAZY... NO SPEC
DIVERSITY... repeated pattern styles... The spec channel looks should all have
many hues of colors in unique ways." His #1 rule is NO LAZINESS.

This module is the OPPOSITE: every finish has its OWN algorithm + motif, and the
three channels (M, R, Cc) carry GEOMETRICALLY DIFFERENT structures so the owner's
composite view (Red=M, Green=R, Blue=Cc) shows many distinct hue zones — never
one field rescaled three ways.

Family members (all about iridescence / colour-flip / spectral split):
  chameleon         — continuous 120deg-phase-offset hue-wheel rotation (smooth sweep)
  color_flip_wrap   — flat Voronoi WRAP-PLATES, per-panel hard flip + die-cut seams
  pagani_tricolore  — twill CARBON-WEAVE crossed with national flag colour bands
  holographic_base  — ruled DIFFRACTION GRATING, per-channel freq dispersion -> moire
  prismatic         — hard TRIANGULAR facets, per-facet Cc refraction ramp + wireframe
  bioluminescent    — blob cell cores + ridge-skeleton FILAMENT net + dilated halos
  shokk_spectrum    — quantized vertical spectral STRIPES + per-band EQ bar heights
  shokk_prism       — single ASYMMETRIC dispersion FAN (polar->hue, radius->bright)
  shokk_aurora      — domain-warped vertical CURTAIN sheets + offset fringe + starfield

(plus the family roster may evolve; EXPORTS at the bottom is authoritative.)

CONTRACT (matches v1 base_spec_fn so apply_wild_specs can drop these in):
  spec_<id>(shape, seed, sm, base_m, base_r) -> (M, R, CC) float32 (h,w) arrays
  clipped M[0,255], R[15,255], CC[16,255]. sm is a DAMPED contrast knob only
  (contrast = 1 + (sm-1)*0.42), so post-sm output stays varied and clips <1%.

SAFETY (CLAUDE.md / Trouble Log): paint_fn untouched; compose.py never edited;
determinism = all rng seeded from (seed, finish_id hash); no Python pixel loops.
"""

import numpy as np

try:
    import cv2
    _HAVE_CV2 = True
except Exception:  # pragma: no cover - cv2 is always present in this app
    _HAVE_CV2 = False

from engine.core import multi_scale_noise

# Reuse v1 helpers per the workflow brief.
from engine.expansions.wild_spec_lab import (
    _wild_work_shape,
    _wild_upscale,
    SM_CONTRAST_GAIN,
)

# structural_color angle/pin primitives (the angle-reveal vocabulary).
from engine.paint_v2.structural_color import (
    _cx_directional_mask,
    _cx_fine_spec_pins,
    _cx_buried_reveal_gate,
    _cx_ultra_micro,
    _cx_hash01,
    _cx_xy,
)


# ════════════════════════════════════════════════════════════════════════════
# SHARED LOW-LEVEL HELPERS (geometry primitives — each finish COMPOSES these
# differently; the per-finish geometry is its own code, not a shared template).
# ════════════════════════════════════════════════════════════════════════════

# Work resolution for macro/mid bands (perf). Finest band added at full res.
_WORK_MAX = 640


def _seed_of(finish_id, seed):
    """Deterministic per-finish seed from (seed, finish_id hash). No runtime rng."""
    h = 0
    for ch in finish_id:
        h = (h * 131 + ord(ch)) & 0x7FFFFFFF
    return (int(seed) * 2654435761 + h * 40503 + 17) & 0x7FFFFFFF


def _contrast(sm):
    """x2.0-aware damped contrast knob. sm=2.0 -> ~1.42 (NOT 2.0)."""
    sm_f = float(sm) if sm and sm > 0 else 1.0
    c = 1.0 + (sm_f - 1.0) * SM_CONTRAST_GAIN
    return float(np.clip(c, 0.55, 1.75))


def _work_shape(h, w):
    if max(h, w) <= _WORK_MAX:
        return h, w
    scale = _WORK_MAX / float(max(h, w))
    return max(1, int(round(h * scale))), max(1, int(round(w * scale)))


def _up(arr, h, w, nearest=False):
    """Upscale a work-shape field to (h,w). nearest=True keeps speckle crisp."""
    if arr.shape[:2] == (h, w):
        return arr.astype(np.float32, copy=False)
    if _HAVE_CV2:
        interp = cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR
        return cv2.resize(arr.astype(np.float32), (w, h), interpolation=interp).astype(np.float32)
    yi = np.linspace(0, arr.shape[0] - 1, h).astype(np.int32)
    xi = np.linspace(0, arr.shape[1] - 1, w).astype(np.int32)
    return arr[yi][:, xi].astype(np.float32)


def _noise(shape, scales, weights, seed):
    """[-1,1] coherent multi-octave noise (cv2-smoothed grid)."""
    return multi_scale_noise(shape, scales, weights, int(seed) & 0x7FFFFFFF).astype(np.float32)


def _noise01(shape, scales, weights, seed):
    return (_noise(shape, scales, weights, seed) * 0.5 + 0.5).astype(np.float32)


def _warp_xy(shape, seed, amp, scale_px):
    """Domain-warped coordinates: x,y displaced by low-freq noise (in [0,1] units)."""
    x, y = _cx_xy(shape)
    h, w = shape
    base = max(h, w)
    dx = _noise(shape, [scale_px, scale_px * 2], [0.66, 0.34], seed + 11)
    dy = _noise(shape, [scale_px, scale_px * 2], [0.66, 0.34], seed + 29)
    return (x + dx * amp).astype(np.float32), (y + dy * amp).astype(np.float32)


def _sparse_dots(shape, seed, density, jitter_seed=0):
    """Crisp single-pixel dot grid at FULL res via hash threshold (NEAREST-clean)."""
    h, w = shape
    hsh = _cx_hash01(shape, int(seed) + jitter_seed, 4242)
    return (hsh > (1.0 - float(density))).astype(np.float32)


def _voronoi(shape, seed, n_seeds):
    """Voronoi cell id + edge-distance field on the work shape (vectorized, no loop
    over pixels). Returns (cell_id int32, edge_dist float32 in ~[0,1], cx, cy arrays).

    Distances computed against n_seeds points in a single broadcast against a
    coarse grid then upsampled — perf-safe (n_seeds small, grid coarse)."""
    h, w = shape
    rng = np.random.RandomState(int(seed) & 0x7FFFFFFF)
    cx = rng.uniform(0.03, 0.97, n_seeds).astype(np.float32)
    cy = rng.uniform(0.03, 0.97, n_seeds).astype(np.float32)
    # coarse coordinate grid for the assignment (then upsample id + dist)
    gh = min(h, 192)
    gw = min(w, 192)
    gx = np.linspace(0.0, 1.0, gw, dtype=np.float32).reshape(1, gw, 1)
    gy = np.linspace(0.0, 1.0, gh, dtype=np.float32).reshape(gh, 1, 1)
    px = cx.reshape(1, 1, n_seeds)
    py = cy.reshape(1, 1, n_seeds)
    d2 = (gx - px) ** 2 + (gy - py) ** 2  # (gh,gw,n)
    order = np.argsort(d2, axis=2)
    nearest = order[:, :, 0].astype(np.int32)
    d1 = np.take_along_axis(d2, order[:, :, 0:1], axis=2)[:, :, 0]
    d2nd = np.take_along_axis(d2, order[:, :, 1:2], axis=2)[:, :, 0]
    # edge proximity = small where near a cell boundary (d1 ~ d2nd)
    edge = np.sqrt(np.maximum(d2nd, 1e-9)) - np.sqrt(np.maximum(d1, 1e-9))
    edge = (edge / (edge.max() + 1e-6)).astype(np.float32)  # 0 at seam, 1 deep inside
    cell_up = _up(nearest.astype(np.float32), h, w, nearest=True).astype(np.int32)
    edge_up = _up(edge, h, w, nearest=False)
    return cell_up, edge_up, cx, cy


def _cell_hash(cell_id, seed, mod):
    """Deterministic per-cell integer hash in [0, mod)."""
    v = (cell_id.astype(np.int64) * 2654435761 + int(seed)) & 0x7FFFFFFF
    return (v % int(mod)).astype(np.int32)


def _cell_hash01(cell_id, seed):
    v = (cell_id.astype(np.int64) * 2246822519 + int(seed) * 374761393) & 0xFFFFFFFF
    return (v.astype(np.float32) / 4294967295.0).astype(np.float32)


def _ridge(field01):
    """Ridge transform: bright thin lines where the field crosses 0.5."""
    return (1.0 - np.abs(field01 * 2.0 - 1.0)).astype(np.float32)


def _angle_shift(shape, seed, freq, amt):
    """Signed [-amt, amt] phase shift from opposing directional masks (the pan flip)."""
    a = _cx_directional_mask(shape, "u", int(seed), freq=freq)
    b = _cx_directional_mask(shape, "v", int(seed) + 313, freq=freq * 0.9)
    return ((a - b) * amt).astype(np.float32)


def _finalize(M, R, CC, h, w, work_shape, micro_pack=None):
    """Upscale macro/mid bands, then ADD the finest full-res band, then clip.

    micro_pack: optional (dM, dR, dCC) full-res additive fine fields (already at
    (h,w)) — the legitimate single-pixel sparkle/flake band per the freq doctrine.
    """
    if work_shape != (h, w):
        M = _up(M, h, w)
        R = _up(R, h, w)
        CC = _up(CC, h, w)
    if micro_pack is not None:
        dM, dR, dCC = micro_pack
        M = M + dM
        R = R + dR
        CC = CC + dCC
    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.clip(R, 15, 255).astype(np.float32)
    CC = np.clip(CC, 16, 255).astype(np.float32)
    return M, R, CC


def _micro_flake(h, w, seed, m_amp=0.0, r_amp=0.0, cc_amp=0.0, density=0.012):
    """Full-res crisp single-pixel flake band shared as an additive pack.

    Returns (dM, dR, dCC). The sparkle is the SAME pin lattice but each channel
    weights it differently (and R is inverted: flakes are SHINY = lower R), so it
    stays decorrelating rather than a common offset."""
    dots = _sparse_dots((h, w), seed + 555, density)
    fine = _cx_ultra_micro((h, w), seed + 777)
    sparkle = dots * (0.6 + 0.4 * fine)
    grain = (fine - 0.5)
    dM = sparkle * m_amp + grain * (m_amp * 0.18)
    dR = -sparkle * r_amp + grain * (r_amp * 0.22)
    dCC = sparkle * cc_amp + grain * (cc_amp * 0.18)
    return dM.astype(np.float32), dR.astype(np.float32), dCC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# chameleon — continuous hue-wheel rotation (channels = same flow phi at three
# 120deg-offset trig phases, so a crest in M is a shoulder in R, trough in Cc).
# ════════════════════════════════════════════════════════════════════════════
def spec_chameleon(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. SIGNATURE: the ONLY finish that cycles the
    # full hue wheel as a smooth 120deg-phase-offset continuous spectrum sweep.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("chameleon", seed)
    c = _contrast(sm)

    # Band A (octave ~128): the macro domain-warped flow-phase scalar phi1.
    wx, wy = _warp_xy(ws, sd, amp=0.16, scale_px=max(4, ws[0] // 6))
    flow_dir = 0.62 + (sd % 13) * 0.05
    phi1 = wx * np.cos(flow_dir) + wy * np.sin(flow_dir)
    phi1 = phi1 * (ws[1] / 16.0)  # ~ octave 128 on the work shape
    # Band B (octave ~256-512): a finer phi2 that beats against phi1 (band wobble).
    phi2 = _noise01(ws, [max(4, ws[0] // 12), max(4, ws[0] // 24)], [0.6, 0.4], sd + 91)
    phi = phi1 + phi2 * 1.7

    # ANGLE: pan advances/retards the wheel.
    phi = phi + _angle_shift(ws, sd, freq=64.0, amt=0.55)

    two_pi = 2.0 * np.pi
    # 120deg-offset phases -> channels diverge geometrically.
    mM = 0.5 + 0.5 * np.cos(two_pi * phi)
    mR = 0.5 + 0.5 * np.cos(two_pi * phi - two_pi / 3.0)
    mC = 0.5 + 0.5 * np.cos(two_pi * phi - 2.0 * two_pi / 3.0)

    # thin neutral seam where all three near 0.5 (the gray seam zone)
    seam = np.exp(-((mM - 0.5) ** 2 + (mR - 0.5) ** 2 + (mC - 0.5) ** 2) * 26.0)

    # anchor at mid with damped contrast around it (keeps peaks off 255).
    M = 132 + (mM - 0.5) * 150 * c
    R = 132 + (mR - 0.5) * 150 * c
    CC = 130 + (mC - 0.5) * 148 * c
    # pull seams toward mid-gray (all-mid)
    M = M * (1 - seam * 0.55) + 128 * (seam * 0.55)
    R = R * (1 - seam * 0.55) + 128 * (seam * 0.55)
    CC = CC * (1 - seam * 0.55) + 128 * (seam * 0.55)

    # Band C full-res: per-flake hue jitter -> a tiny per-channel phase wobble that
    # makes individual flakes flash a slightly off hue (real chromaflair sparkle).
    fl = _cx_ultra_micro((h, w), sd + 401)
    jit = (fl - 0.5)
    micro = (jit * 22.0, -jit * 14.0, jit * 18.0)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# color_flip_wrap — flat Voronoi WRAP-PLATES; M/Cc carry FLAT cell fill, R carries
# a DIFFERENT geometry (squeegee creases + seam distance). Per-panel hard flip.
# ════════════════════════════════════════════════════════════════════════════
def spec_color_flip_wrap(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. SIGNATURE: large DEAD-FLAT vinyl panels with
    # per-panel hard flip + die-cut seam blacks + squeegee anisotropic creases.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("color_flip_wrap", seed)
    c = _contrast(sm)

    # Band A: big flat Voronoi plates (~door-panel sized -> few seeds).
    cell, edge, cx, cy = _voronoi(ws, sd, n_seeds=12)
    # per-cell flip state, gated by a diagonal pan mask so whole PANELS flip.
    cell_flip = (_cell_hash01(cell, sd + 7) > 0.5).astype(np.float32)
    pan = _cx_directional_mask(ws, "diag_a", sd + 51, freq=10.0)
    flip_state = np.clip(cell_flip * 0.7 + (pan - 0.5) * 0.9 + 0.5, 0.0, 1.0)
    flip_state = (flip_state > 0.5).astype(np.float32)  # 1 = magenta plate, 0 = yellow plate

    # Band B: die-cut seam blacks + squeegee crease corridors.
    seam = np.clip(1.0 - edge * 5.0, 0.0, 1.0)  # 1 right at a knife-cut seam
    # squeegee creases: 1D anisotropic sine grain along a per-cell axis (in R only).
    x, y = _cx_xy(ws)
    crease_ang = _cell_hash01(cell, sd + 13) * np.pi
    proj = x * np.cos(crease_ang) + y * np.sin(crease_ang)
    crease = 0.5 + 0.5 * np.sin(proj * 70.0 + _noise(ws, [ws[0] // 8], [1.0], sd + 5) * 2.0)
    crease = (crease > 0.74).astype(np.float32)  # sparse stretch marks

    # M: DEAD-FLAT per-cell metallic vinyl base (decorrelated from Cc via own hash),
    # minus the knife-cut seams. Zero internal gradient (the flatness of vinyl).
    M = 140 + _cell_hash01(cell, sd + 3) * 30  # flat per-cell, ~140..170
    M = M * (1.0 - seam * 0.85)

    # Cc: flat plate fill — HIGH on magenta plates (M+Cc), LOW on yellow plates.
    CC = 36 + flip_state * 150
    CC = CC * (1.0 - seam * 0.85)

    # R: creases + seams geometry (GREEN squeegee marks, BLACK seams). NOT flat.
    # yellow plates also carry R (M+R yellow), magenta plates do NOT.
    R = 30 + (1 - flip_state) * 140 + crease * 60
    R = R * (1.0 - seam * 0.8)
    R = R * (0.88 + 0.12 * c)

    # trapped air bubbles: all-high white pinpoints at full res (crisp NEAREST).
    bub = _sparse_dots((h, w), sd + 88, density=0.0016)
    micro = (bub * 80.0, bub * 80.0, bub * 80.0)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# pagani_tricolore — twill CARBON WEAVE (R/Cc) crossed with flag colour BANDS (M).
# ════════════════════════════════════════════════════════════════════════════
def spec_pagani_tricolore(shape, seed, sm, base_m, base_r):
    # wild-spec-v2-straggler-fix 2026-06-07. v2-round-1 pagani FAILED the owner
    # eyeball test: washed-out pink/cream, the tricolore barely read, weak name
    # match. REDO with BOLD GEOMETRY: three crisp DIAGONAL SASH BANDS separated by
    # hard stitched-seam corridors — band 1 R+Cc-heavy (cyan/green-read), band 2
    # all-high (white-read), band 3 M-dominant (red-read) — so the Italian flag
    # reads instantly as three differently-hued macro zones. Inside every band a
    # fine 2x2 TWILL carbon-weave (Pagani signature) runs at a HIGHER frequency
    # than shokk_fusion_base's crosshatch and subordinate to the bold bands. The
    # seams carry morphological pin cores (stitch glints). SIGNATURE: the ONLY
    # finish built as diagonal national-flag sashes over a carbon twill substrate.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("pagani_tricolore", seed)
    c = _contrast(sm)
    x, y = _cx_xy(ws)
    two_pi = 2.0 * np.pi

    # ── Band A (octave ~128): three BOLD DIAGONAL SASH bands. The sash axis is a
    # 45deg-ish diagonal so the flag runs corner-to-corner (not the v1 horizontal
    # thirds). A low-freq wobble warps the seams so they aren't ruler-straight.
    diag = (x * 0.74 + y * 0.66)                                   # ~42deg sash normal
    diag = diag + _noise(ws, [ws[0] // 4, ws[0] // 8], [0.6, 0.4], sd + 3) * 0.05
    # ANGLE: pan slides which sash sits under the highlight (the tricolore pans).
    pan = _cx_directional_mask(ws, "diag_a", sd + 21, freq=6.0)
    sash_f = (diag + (pan - 0.5) * 0.06)
    sash_f = (sash_f - sash_f.min()) / (sash_f.max() - sash_f.min() + 1e-6)
    band = np.clip(sash_f * 3.0, 0.0, 2.999).astype(np.int32)      # 0,1,2 sashes

    # hard stitched-seam corridor: distance to the nearest 1/3 or 2/3 sash boundary.
    seam_phase = np.abs(((sash_f * 3.0) % 1.0) - 0.5) * 2.0        # 0 at a seam centre
    interior = (sash_f > 0.02) & (sash_f < 0.98)
    seam = np.clip(1.0 - seam_phase * 12.0, 0.0, 1.0) * interior   # bright stitch corridor

    # ── Band B (octave ~512+): fine 2x2 TWILL carbon weave. A 2x2 twill = a tow
    # that floats over 2, under 2, stepping one each row -> a tight diagonal rib.
    # Built as two phase-locked high-freq gratings; their over/under interleave is
    # the twill. Frequency is HIGHER than shokk_fusion_base's crosshatch (subordinate
    # micro texture, not a macro motif).
    fw = 230.0
    u = (x + y)
    v = (x - y)
    rib_a = np.sin(u * fw * two_pi)                               # tow rib A
    rib_b = np.sin((v * fw + u * (fw * 0.5)) * two_pi + 0.9)      # stepped cross rib
    # 2x2 twill float: which tow is ON top alternates in a 2-period stagger.
    stagger = np.floor(u * fw * 0.5) + np.floor(v * fw * 0.5)
    top = (np.mod(stagger, 2.0) < 1.0).astype(np.float32)         # 0/1 over-under select
    tow = rib_a * top + rib_b * (1.0 - top)
    weave_sheen = np.clip(tow * 0.5 + 0.5, 0.0, 1.0)             # catching tow (highlight)
    weave_shadow = np.clip(1.0 - np.abs(tow), 0.0, 1.0)          # valley between tows
    weave_dev = (weave_sheen - 0.5)                              # signed, +-0.5

    # ── COMPOSE the three sash triplets (each a DIFFERENT hue read), with the twill
    # riding INSIDE every band (subordinate ripple) and the stitched seams cutting
    # corridors between them. The bianco (white) band is deliberately NOT pinned to
    # the ceiling in all three channels — it sits a notch below max so the channels
    # don't collapse to one all-high field (that was the correlated, over-clipped
    # failure). Each channel reads a DIFFERENT twill component + a DIFFERENT seam
    # sign so the three carry distinct geometry (decorrelating).
    #   band 0 -> R+Cc heavy  (cyan/green read: high R, high Cc, low M)  [verde side]
    #   band 1 -> all high     (white read, slightly tinted per channel) [bianco]
    #   band 2 -> M dominant   (red read: high M, low R, low Cc)         [rosso]
    # The band fills are intentionally DAMPED (not pinned to the ceiling) so the
    # high-frequency twill — which is channel-DISTINCT and decorrelating — remains a
    # strong fraction of each channel's variance. R and Cc would otherwise track
    # together (both high on the verde/bianco side); to break that, R carries the
    # SIGNED sheen rib while Cc carries the sheen MAGNITUDE (a different waveform of
    # the same weave, only weakly correlated), and they get opposite-sign seam writes.
    # Band fills are damped (not ceiling-pinned). To keep R and Cc from tracking
    # together (both ride the verde/bianco side), they are given band profiles that
    # DISAGREE on the bianco third: R reads bianco HIGH (the white sash is bright in
    # the green channel) while Cc reads bianco only MID and instead peaks on the
    # verde third — so the band step itself partly anti-aligns R vs Cc.
    m_band = np.choose(band, [46.0, 138.0, 170.0])                # rosso + bianco light M
    r_band = np.choose(band, [150.0, 168.0, 52.0])               # bianco-bright R
    cc_band = np.choose(band, [150.0, 116.0, 58.0])              # verde-peaked Cc

    # Channel-distinct PRIMARY geometry so R and Cc don't share a waveform:
    #   M  -> twill under-tow VALLEYS (dark ribs) — its own weave read.
    #   R  -> twill SIGNED sheen rib (the catching tow) — the weave is R's structure.
    #   Cc -> the SEAM/stitch CORRIDOR is Cc's primary structure (clearcoat pooling
    #         in the stitched channels), only lightly touched by the weave -> a
    #         thin sparse geometry orthogonal to R's broad weave (decorrelating).
    wM = -weave_shadow                                            # M: dark under-tow valleys
    wR = weave_dev                                                # R: signed sheen rib (+-)

    M = m_band + wM * 54.0 - seam * 44.0
    M = 26 + (M - 26) * (0.84 + 0.16 * c)
    R = r_band + wR * 66.0 - seam * 30.0
    R = 20 + (R - 20) * (0.84 + 0.16 * c)
    CC = cc_band + seam * 90.0 + weave_sheen * 18.0
    CC = 22 + (CC - 22) * (0.84 + 0.16 * c)

    # ── Band C full-res: morphological PIN CORES along the stitched seams (the
    # thread glints) + sparse carbon flecks densest in the bianco band. The seam
    # pins are crisp single-pixel highlights gated to the seam corridor so they
    # read as needle punches along the stitch line.
    seam_full = _up(seam, h, w)
    band_full = _up(band.astype(np.float32), h, w, nearest=True)
    stitch = _sparse_dots((h, w), sd + 211, density=0.09) * (seam_full > 0.35)
    dens = np.where(np.abs(band_full - 1.0) < 0.5, 0.012, 0.0040)
    fleck = (_cx_hash01((h, w), sd + 91, 33) < dens).astype(np.float32)
    # seam pins read as needle punches. They pop brightest on M (whose seam is a dark
    # trough, so the pins give max local contrast) and only LIGHTLY touch R and Cc,
    # whose seam corridors are already bright (the pins would otherwise push the Cc
    # corridor over the ceiling). Carbon flecks weight cool channels.
    dM = stitch * 150.0 + fleck * 44.0
    dR = stitch * 56.0 + fleck * 22.0
    dCC = stitch * 60.0 + fleck * 52.0
    micro = (dM, dR, dCC)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# holographic_base — full-spectrum DIFFRACTION TERRACES. A domain-warped diffraction
# -angle field is QUANTIZED into broad iridescent plates; each plate's angle drives
# a 120deg-phase hue wheel so the composite sweeps red->yellow->green->cyan->blue->
# magenta as DISTINCT macro zones (no flat-gray bed). A sharp ruled grating fringe
# rides on top + a dense crisp micro-flake rainbow sparkle band at full res.
# ════════════════════════════════════════════════════════════════════════════
def spec_holographic_base(shape, seed, sm, base_m, base_r):
    # wild-spec-v2-straggler-fix 2026-06-07. v2-round-1 holographic FAILED the
    # owner eyeball test: a fine green/magenta DITHER that read as a cousin of
    # chameleon's micro-dither with no macro motif (chameleon keeps EXCLUSIVE
    # ownership of uniform micro-dither). REDO as a HOLO-FOIL DIFFRACTION SWEEP:
    # 2-3 broad angular RAINBOW SWEEP FANS radiate from off-canvas origins, the hue
    # stepping across each fan via a 120deg triplet rotation of the fan ANGLE -> the
    # composite cycles the whole hue wheel as big sweeping arcs. Embossed GROOVE
    # RULING (fine parallel line grating) rides on top and BEATS into a visible
    # moire where the fans cross. Sparse die-cut EMBLEM glints punch the foil. The
    # macro sweep DOMINATES. SIGNATURE: angular diffraction sweep fans + groove
    # moire — geometry differs per channel via the per-fan triplet-rotated hue.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("holographic_base", seed)
    c = _contrast(sm)
    x, y = _cx_xy(ws)
    two_pi = 2.0 * np.pi

    # ANGLE: pan rotates the whole foil (advances every fan's diffraction order).
    pan = _cx_directional_mask(ws, "u", sd + 71, freq=5.0)
    pan_phase = (pan - 0.5) * 0.9

    # gentle domain warp so the sweep arcs undulate (holo foil is never ruler-clean).
    warp = _noise(ws, [ws[0] // 4, ws[0] // 8], [0.62, 0.38], sd + 5) * 0.06

    # ── Band A (octave ~128-256): 3 broad RAINBOW SWEEP FANS from off-canvas origins.
    # Each fan: polar ANGLE about an origin drives a hue wheel; that hue is read into
    # the three channels with a PER-FAN 120deg triplet ROTATION so fans light
    # different channels and overlap into many composite hues. Radius softly fades
    # the fan so it's a finite spray, not a full-frame wash. We accumulate the three
    # channels (max-combine the fan bodies, weighted-add the hue) so the sweep is the
    # DOMINANT macro structure.
    rng = np.random.RandomState((sd + 17) & 0x7FFFFFFF)
    accM = np.zeros(ws, np.float32)
    accR = np.zeros(ws, np.float32)
    accC = np.zeros(ws, np.float32)
    cover = np.zeros(ws, np.float32)
    n_fan = 3
    # off-canvas origins (corners/edges) so the arcs sweep ACROSS the body.
    origins = [(-0.25, -0.20), (1.22, 0.35), (0.40, 1.28)]
    fan_turns = [2.2, 2.7, 1.9]                                   # hue cycles per fan
    chan_roll = [0, 1, 2]                                         # triplet rotation per fan
    for i in range(n_fan):
        ox, oy = origins[i]
        dx = (x - ox)
        dy = (y - oy)
        rad = np.sqrt(dx * dx + dy * dy)
        ang = np.arctan2(dy, dx) / two_pi + 0.5                   # 0..1 around the origin
        # the diffraction hue: angle * fan_turns, advanced by pan + warp.
        hue = (ang * fan_turns[i] + pan_phase * (0.6 + 0.2 * i) + warp) % 1.0
        ph = hue * two_pi
        # radial envelope: bright sweep that fades with distance from the origin.
        env = np.clip(1.0 - np.abs(rad - (0.55 + 0.18 * i)) * (1.5 + 0.4 * i), 0.0, 1.0)
        env = env ** 0.85
        # triplet-rotated hue lobes (PER-FAN channel roll -> fans light diff channels)
        lobes = [0.5 + 0.5 * np.cos(ph - k * two_pi / 3.0) for k in range(3)]
        r0 = chan_roll[i]
        lM = lobes[(0 + r0) % 3]
        lR = lobes[(1 + r0) % 3]
        lC = lobes[(2 + r0) % 3]
        accM = np.maximum(accM, env * lM)
        accR = np.maximum(accR, env * lR)
        accC = np.maximum(accC, env * lC)
        cover = np.maximum(cover, env)

    # ── Band B (octave ~512): embossed GROOVE RULING — a fine parallel line grating.
    # TWO rulings at slightly different angles/pitches produce a visible MOIRE BEAT
    # where they cross (the holo foil's ruled-emboss shimmer). Per channel the groove
    # sits at a dispersed frequency so the bright rule line differs by channel.
    coord1 = (x * 0.96 + y * 0.28) + warp * 0.5
    coord2 = (x * 0.30 - y * 0.95) + warp * 0.5
    k1, k2 = 150.0, 138.0
    rule1 = 0.5 + 0.5 * np.sin(coord1 * k1 * two_pi)
    rule2 = 0.5 + 0.5 * np.sin(coord2 * k2 * two_pi)
    moire = rule1 * rule2                                         # beat pattern where they cross
    # per-channel groove dispersion (the rainbow split of a single rule line).
    gM = 0.5 + 0.5 * np.sin(coord1 * k1 * two_pi)
    gR = 0.5 + 0.5 * np.sin(coord1 * (k1 * 1.04) * two_pi + 1.1)
    gC = 0.5 + 0.5 * np.sin(coord1 * (k1 * 1.08) * two_pi + 2.2)

    # ── COMPOSE: the sweep fans dominate (broad amplitude), groove ruling + moire
    # add the fine shimmer on top. A low foil floor keeps un-swept gaps iridescent
    # rather than dead. Amplitudes sized so post-sm peaks (c~1.42) stay off 255.
    foil = 30.0
    M = foil + accM * 120.0 * c + (gM - 0.5) * 26.0 + (moire - 0.5) * 24.0
    R = foil + accR * 118.0 * c + (gR - 0.5) * 26.0 + (moire - 0.5) * 20.0
    CC = foil + accC * 122.0 * c + (gC - 0.5) * 26.0 + (moire - 0.5) * 28.0

    # ── Band C full-res: sparse die-cut EMBLEM glints — small crisp all-high punches
    # scattered like the foil's stamped logos catching light, plus a faint per-channel
    # grain so the foil isn't dead-flat (NOT a uniform dither — kept sparse + low).
    emblem = _sparse_dots((h, w), sd + 311, density=0.0022)
    fl = _cx_ultra_micro((h, w), sd + 401)
    glint = emblem * (0.6 + 0.4 * fl)
    g = (fl - 0.5)
    dM = glint * 150.0 + g * 8.0
    dR = glint * 150.0 - g * 7.0
    dCC = glint * 158.0 + g * 8.0
    micro = (dM, dR, dCC)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# prismatic — hard TRIANGULAR facets; R = flat facet pair, Cc = facet + internal
# refraction ramp, M = facet + edge wireframe. Per-facet discrete hue flip.
# ════════════════════════════════════════════════════════════════════════════
def spec_prismatic(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. ARBITER: triangulated cut-gemstone facets,
    # NOT rounded Worley. SIGNATURE: hard angular facets + per-facet Cc refraction
    # ramp + crisp 1px wireframe + 3-way hash so neighbours differ.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("prismatic", seed)
    c = _contrast(sm)

    # Band A: angular facet tessellation (hand-span shards -> moderate seed count).
    cell, edge, cx, cy = _voronoi(ws, sd, n_seeds=42)
    # 3-way hue hash so neighbours differ (yellow / cyan / magenta).
    hue = _cell_hash(cell, sd + 9, 3)  # 0,1,2
    lit_warm = (hue == 0).astype(np.float32)   # M+R yellow
    lit_cool = (hue == 1).astype(np.float32)   # R+Cc cyan
    lit_viol = (hue == 2).astype(np.float32)   # M+Cc magenta

    # ANGLE: each facet flips between yellow (M+R) and magenta (M+Cc) with pan.
    pan = _cx_directional_mask(ws, "diag_b", sd + 31, freq=14.0)
    facet_pan = _cell_hash01(cell, sd + 17)
    flip = ((facet_pan + (pan - 0.5) * 0.8) > 0.5).astype(np.float32)

    # crisp 1px-ish wireframe at facet boundaries
    wire = np.clip(1.0 - edge * 7.0, 0.0, 1.0)

    # per-facet internal linear refraction RAMP (Cc only) — fakes refraction depth.
    x, y = _cx_xy(ws)
    ramp_ang = _cell_hash01(cell, sd + 23) * 2.0 * np.pi
    ramp = (x * np.cos(ramp_ang) + y * np.sin(ramp_ang))
    # localize ramp per cell by subtracting its mean via the cell centroid lookup
    cxv = cx[np.clip(cell, 0, len(cx) - 1)]
    cyv = cy[np.clip(cell, 0, len(cy) - 1)]
    ramp_local = (x - cxv) * np.cos(ramp_ang) + (y - cyv) * np.sin(ramp_ang)
    refract = np.clip(ramp_local * 6.0 + 0.5, 0.0, 1.0)

    # M: warm/violet facets light M; PLUS the edge wireframe (M-specific geometry).
    M = 30 + (lit_warm + lit_viol) * 120 + flip * 22
    M = M * (0.85 + 0.15 * c) + wire * 48

    # R: flat facet pair (warm+cool light R), NO wireframe, NO ramp.
    R = 28 + (lit_warm + lit_cool) * 138 + (1 - flip) * 24
    R = R * (0.85 + 0.15 * c)

    # Cc: cool+violet facets light Cc + internal refraction RAMP (Cc-only geometry).
    CC = 30 + (lit_cool + lit_viol) * 118 + flip * 22 + refract * 50
    CC = CC * (0.85 + 0.15 * c)

    # deep facet cores: pull interior centers darker on a fraction of facets (black)
    core = (1.0 - edge)  # bright deep inside; invert to darken cores selectively
    dark = (_cell_hash01(cell, sd + 41) > 0.78).astype(np.float32) * np.clip((edge - 0.4) * 2.0, 0, 1)
    M = M * (1 - dark * 0.7)
    R = R * (1 - dark * 0.7)
    CC = CC * (1 - dark * 0.7)

    # Band C full-res: micro-fracture sparkle inside facets (crystal inclusions).
    spk = _sparse_dots((h, w), sd + 66, density=0.0026)
    micro = (spk * 55.0, spk * 40.0, spk * 55.0)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# bioluminescent — THREE distinct organism COLONIES, each its own glow triplet:
#   magenta jellyfish (M+Cc), cyan plankton (R+Cc), amber bacteria (M+R), each
# living in its own Voronoi-partitioned territory so the composite shows three
# different hues — plus a mid-frequency mycelium VEIN network threading the dark
# bed and crisp pinpoint glow sparkle at full res. The dark tissue stays only the
# minority (network keeps it structured), not a dominant black void with flecks.
# ════════════════════════════════════════════════════════════════════════════
def spec_bioluminescent(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. v2-round-1 bioluminescent FAILED visual
    # judging: too dark a bed with only sparse green/pink glows and cores that lit
    # ALL channels (correlated). REDO: partition the surface into THREE colony
    # territories, each driving a DIFFERENT channel pair (magenta jellyfish M+Cc /
    # cyan plankton R+Cc / amber bacteria M+R), threaded by a mid-freq mycelium vein
    # net so the bed carries structure and varied-hue coverage is high. Channels are
    # decorrelated because each colony lights a distinct pair.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("bioluminescent", seed)
    c = _contrast(sm)

    # Band A (octave ~128): colony TERRITORIES — broad Voronoi regions, each cell
    # assigned one of three organism types (its glow triplet). This is what gives
    # the map several big differently-hued patches instead of one dark field.
    cell, edge, cx, cy = _voronoi(ws, sd + 2, n_seeds=16)
    ctype = _cell_hash(cell, sd + 9, 3)              # 0 jelly, 1 plankton, 2 bacteria
    jelly_t = (ctype == 0).astype(np.float32)
    plank_t = (ctype == 1).astype(np.float32)
    bact_t = (ctype == 2).astype(np.float32)

    # Band B: compact emissive cell BODIES (sparse blobs) — the glowing organisms.
    blob_n = _noise01(ws, [ws[0] // 6, ws[0] // 11], [0.62, 0.38], sd + 3)
    cores = np.clip((blob_n - 0.52) * 4.0, 0.0, 1.0) ** 1.15
    # a SECOND, finer blob set for plankton (smaller, denser dots) so colony types
    # also differ in TEXTURE, not just hue.
    fine_blob = _noise01(ws, [ws[0] // 12, ws[0] // 20], [0.6, 0.4], sd + 33)
    plank_cells = np.clip((fine_blob - 0.58) * 5.0, 0.0, 1.0)

    # Band C-mid: mycelium VEIN network (ridge skeleton of a third noise) — threads
    # the dark bed everywhere so it is never an empty void.
    fil_n = _noise01(ws, [ws[0] // 7, ws[0] // 14], [0.6, 0.4], sd + 27)
    veins = np.clip((_ridge(fil_n) - 0.74) * 5.0, 0.0, 1.0)
    # warm secondary capillary net (offset noise) carried in a different channel
    cap_n = _noise01(ws, [ws[0] // 9, ws[0] // 18], [0.6, 0.4], sd + 51)
    caps = np.clip((_ridge(cap_n) - 0.78) * 5.5, 0.0, 1.0)

    # halo aura around the bright bodies (soft ring) -> adds to the cool channel.
    if _HAVE_CV2:
        dil = cv2.GaussianBlur(cores, (0, 0), sigmaX=max(1.0, ws[0] / 55.0))
    else:
        dil = cores
    halo = np.clip(dil - cores, 0.0, 1.0)
    halo = halo / (halo.max() + 1e-6)

    # ANGLE: colonies pulse — different territories brighten at different pan angles.
    pan = _cx_directional_mask(ws, "v", sd + 61, freq=14.0)
    pulse = 0.45 + 0.55 * pan

    # per-colony emissive bodies (each type uses its own blob texture)
    jelly = jelly_t * cores * pulse
    plank = plank_t * plank_cells * pulse
    bact = bact_t * cores * pulse
    faint = _noise01(ws, [ws[0] // 10], [1.0], sd + 71) * 0.10  # dim tissue glow

    # COMPOSE the three triplets (decorrelated — each colony lights a distinct pair):
    #   jelly   -> M + Cc (magenta), strong halo in M
    #   plankton-> R + Cc (cyan), carried by veins
    #   bacteria-> M + R (amber), carried by capillaries
    M = 14 + (jelly * 170 + bact * 150) * c + halo * jelly_t * 80 + caps * 60 + faint * 30
    R = 14 + (plank * 165 + bact * 140) * c + veins * 95 + caps * 45 + faint * 24
    CC = 16 + (jelly * 165 + plank * 155) * c + halo * 85 + veins * 60 + faint * 26

    # Band D full-res: pinpoint glow sparkle — each spark tinted to its colony hue
    # (decorrelating, crisp single-pixel). Densest where a colony body is lit.
    ct_full = _up(ctype.astype(np.float32), h, w, nearest=True)
    lit_full = _up(np.clip(jelly + plank + bact, 0, 1), h, w)
    spk = _sparse_dots((h, w), sd + 88, density=0.016) * (lit_full > 0.04)
    is_j = (np.abs(ct_full - 0.0) < 0.5).astype(np.float32)
    is_p = (np.abs(ct_full - 1.0) < 0.5).astype(np.float32)
    is_b = (np.abs(ct_full - 2.0) < 0.5).astype(np.float32)
    dM = spk * (is_j + is_b) * 120.0
    dR = spk * (is_p + is_b) * 120.0
    dCC = spk * (is_j + is_p) * 120.0
    micro = (dM, dR, dCC)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# shokk_spectrum — quantized vertical spectral STRIPES (M/Cc flat) + per-band EQ
# bar HEIGHTS (R). Strict spectral order R->Y->G->C->B->M across X.
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_spectrum(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. SIGNATURE: QUANTIZED hard vertical spectral
    # stripes in strict order + per-band EQ bar-height modulation in a separate
    # channel (flat stripes in M/Cc vs bar-graph heights in R).
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("shokk_spectrum", seed)
    c = _contrast(sm)
    x, y = _cx_xy(ws)

    n_bands = 18
    # ANGLE: bands scroll sideways with pan ('u' offsets the X ramp).
    pan_u = _cx_directional_mask(ws, "u", sd + 11, freq=4.0)
    ramp = x + (pan_u - 0.5) * 0.18
    band_f = np.clip(ramp, 0.0, 0.99999) * n_bands
    band = band_f.astype(np.int32)
    stripe = (band % 6).astype(np.int32)  # 0..5 spectral slot

    # spectral order R,Y,G,C,B,M -> per-channel ON tables (this IS the hue cycle).
    # M on for R(0),Y(1),M(5); R on for Y(1),G(2),C(3); Cc on for C(3),B(4),M(5).
    m_on = np.isin(stripe, [0, 1, 5]).astype(np.float32)
    r_on = np.isin(stripe, [1, 2, 3]).astype(np.float32)
    c_on = np.isin(stripe, [3, 4, 5]).astype(np.float32)

    # per-band random height for EQ bars (R-only second geometry).
    band_h = _cell_hash01(band, sd + 31) * 0.6 + 0.35  # 0.35..0.95 height fraction
    pan_v = _cx_directional_mask(ws, "v", sd + 53, freq=5.0)
    band_h = np.clip(band_h + (pan_v - 0.5) * 0.25, 0.05, 1.0)
    bar = (y > (1.0 - band_h)).astype(np.float32)  # bars rise from bottom

    # sub-stripe splitting: thin internal lines within each bar
    sub = 0.5 + 0.5 * np.sin(ramp * n_bands * 6.0 * np.pi)
    sub = (sub > 0.6).astype(np.float32)

    # on-band brightness damped by c around a fixed peak so binary stripes don't
    # saturate at 255 (c only nudges the on/off swing).
    on_v = 150.0 + 60.0 * (c - 1.0)  # ~175 at c=1.42, well under 255
    # M: FLAT stripes (no height) — m_on bands are bright top-to-bottom.
    M = 24 + m_on * on_v
    # Cc: FLAT stripes — c_on bands bright top-to-bottom.
    CC = 26 + c_on * (on_v - 4)
    # R: BAR GRAPHS — r_on bands but only where the bar has risen (height geom).
    R = 22 + r_on * bar * on_v + r_on * (1 - bar) * 10 + sub * 12

    # Band C full-res: per-stripe horizontal scan-line micro-flicker (crisp pins).
    yf = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    scan = (np.sin(yf * 900.0) > 0.85).astype(np.float32) * np.ones((1, w), np.float32)
    flick = _sparse_dots((h, w), sd + 77, density=0.02) * scan
    micro = (flick * 30.0, flick * 40.0, flick * 30.0)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# shokk_prism — MULTIPLE dispersion streaks: several prism beams cast rainbow
# caustic fans that fill most of the tile, crossed with hard prism FACET zones
# (each face its own triplet) over a mid-frequency cut-glass bed (never black).
# Each channel rides a DIFFERENT spectral offset of the streak so the rainbows
# split spatially (decorrelated) + a fine caustic-sparkle band at full res.
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_prism(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. v2-round-1 shokk_prism FAILED visual judging:
    # a single thin fan over a MOSTLY-BLACK tile (tiny hue coverage) + a shared beam
    # spine that correlated all three channels (corr ~0.78). REDO: cast SEVERAL
    # dispersion streaks at angled directions so rainbow caustics fill most of the
    # area; cut the surface into hard prism FACETS (each face a distinct triplet);
    # break the dark bed with a mid-freq cut-glass structure. Channels decorrelate
    # because each rides a different perpendicular spectral offset of the streaks.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("shokk_prism", seed)
    c = _contrast(sm)
    x, y = _cx_xy(ws)
    two_pi = 2.0 * np.pi

    # ANGLE: pan slides the dispersion across the streaks' perpendicular offset.
    pan_u = _cx_directional_mask(ws, "u", sd + 19, freq=5.0)
    pan_off = (pan_u - 0.5) * 0.35

    # --- Band A: MULTIPLE caustic streaks. Each streak is a directed corridor
    # (bright along a line) whose PERPENDICULAR coordinate drives the rainbow.
    # 4 streaks at spread angles -> caustics criss-cross and fill the tile.
    rng = np.random.RandomState((sd + 4) & 0x7FFFFFFF)
    sM = np.zeros(ws, np.float32)
    sR = np.zeros(ws, np.float32)
    sC = np.zeros(ws, np.float32)
    n_streak = 4
    for i in range(n_streak):
        ang = rng.uniform(0.0, np.pi)
        ux, uy = np.cos(ang), np.sin(ang)            # along the beam
        px, py = -uy, ux                             # perpendicular (dispersion axis)
        ox = rng.uniform(0.1, 0.9)
        oy = rng.uniform(0.1, 0.9)
        along = (x - ox) * ux + (y - oy) * uy        # position along the beam
        perp = (x - ox) * px + (y - oy) * py + pan_off  # perpendicular -> spectrum
        # corridor envelope: bright in a band of perpendicular distance (the beam
        # width), tapering along its length so each streak is a finite shaft.
        width = 0.18 + 0.06 * (i % 3)
        env = np.clip(1.0 - np.abs(perp) / width, 0.0, 1.0)
        env = env * np.clip(1.0 - np.abs(along) * 0.55, 0.0, 1.0) ** 0.8
        # spectrum across the perpendicular: per-channel SHIFTED so the red/green/
        # blue lobes of THIS streak land at different perpendicular positions.
        s01 = np.clip(perp / width * 0.5 + 0.5, 0.0, 1.0)   # 0..1 across the beam
        lobeM = np.clip(1.0 - np.abs(s01 - 0.20) * 3.0, 0.0, 1.0)
        lobeR = np.clip(1.0 - np.abs(s01 - 0.50) * 3.0, 0.0, 1.0)
        lobeC = np.clip(1.0 - np.abs(s01 - 0.80) * 3.0, 0.0, 1.0)
        sM = np.maximum(sM, env * lobeM)
        sR = np.maximum(sR, env * lobeR)
        sC = np.maximum(sC, env * lobeC)

    # --- Band B: prism FACET zones (hard angular cells), each a distinct triplet,
    # so even between streaks the tile is divided into coloured glass faces.
    cell, edge, cx, cy = _voronoi(ws, sd + 6, n_seeds=28)
    fhue = _cell_hash(cell, sd + 11, 3)
    face_warm = (fhue == 0).astype(np.float32)   # M+R amber face
    face_cool = (fhue == 1).astype(np.float32)   # R+Cc cyan face
    face_viol = (fhue == 2).astype(np.float32)   # M+Cc violet face
    facet_lvl = 0.30 + 0.45 * _cell_hash01(cell, sd + 17)   # per-face brightness
    wire = np.clip(1.0 - edge * 7.0, 0.0, 1.0)               # crisp facet edges

    # --- Band C: mid-freq cut-glass refractive bed (keeps it from being black).
    glass = _noise01(ws, [ws[0] // 6, ws[0] // 12, ws[0] // 24], [0.45, 0.35, 0.2], sd + 41)
    glass_r = _ridge(glass)                                  # internal refraction veins

    # COMPOSE: streaks (vivid, per-channel disjoint) + facet faces + glass bed.
    M = 22 + sM * 165 * c + (face_warm + face_viol) * facet_lvl * 105 + glass * 26 + wire * 28
    R = 20 + sR * 124 * c + (face_warm + face_cool) * facet_lvl * 78 + glass_r * 32 + glass * 12
    CC = 22 + sC * 165 * c + (face_cool + face_viol) * facet_lvl * 105 + glass * 30 + wire * 22

    # --- Band D full-res: crisp caustic sparkle along the dispersion edges, tinted
    # per fleck so the sparkle is itself rainbow (decorrelating single-pixel band).
    streak_full = _up(np.maximum.reduce([sM, sR, sC]), h, w)
    fleck = _sparse_dots((h, w), sd + 73, density=0.016) * (streak_full > 0.05)
    fph = _cx_hash01((h, w), sd + 75, 23) * two_pi
    dM = fleck * (0.5 + 0.5 * np.cos(fph)) * 90.0
    dR = fleck * (0.5 + 0.5 * np.cos(fph - two_pi / 3.0)) * 90.0
    dCC = fleck * (0.5 + 0.5 * np.cos(fph - 2.0 * two_pi / 3.0)) * 90.0
    micro = (dM, dR, dCC)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
# shokk_aurora — DRAPED LIGHT-CURTAIN CORRIDORS as the DOMINANT structure: a few
# wide ribbon corridors (protected ridge cores + soft halos) sweep top-to-bottom
# across the frame, and each curtain carries a HUE GRADIENT along its length —
# green/cyan ray base (R+Cc) at the bottom sweeping to magenta/violet tips (M+Cc)
# at the top — so MANY composite hues appear within one curtain. Mid-band vertical
# ray striations rib the sheets; the starfield is ONLY the fine full-res band.
# ════════════════════════════════════════════════════════════════════════════
def spec_shokk_aurora(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. v2-round-2 shokk_aurora FAILED visual judging
    # THREE ways: it was a near-black, low-contrast green/teal SPECKLE haze
    # (mean ~38/75/66, std too low), the aurora CURTAIN motif was illegible (no
    # vertical light columns, no sweeping multi-hue ribbons), it read as
    # underexposed dotty noise (the exact v1-lazy failure), and the name did not
    # match the look. REDO: the CURTAIN is now the DOMINANT low/mid-freq structure —
    # a handful of WIDE draped ribbon corridors (domain-warped, ridge cores +
    # soft halos) brightened well off the sky, each carrying a hue gradient along
    # its length (green/cyan base -> magenta/violet tips). SIGNATURE: sweeping
    # multi-hue light curtains, NOT scattered dots. Channels decorrelate because
    # M tracks the upper tips, R tracks the green ray-body, Cc spans the full drape.
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    ws = _work_shape(h, w)
    sd = _seed_of("shokk_aurora", seed)
    c = _contrast(sm)
    x, y = _cx_xy(ws)
    two_pi = 2.0 * np.pi

    # ─ Band A (octave ~128-256): the DOMINANT draped curtain corridors. A handful
    # of wide vertical/diagonal ribbons whose horizontal POSITION is domain-warped
    # so they drape and billow. The ribbon field is a protected ridge: hard bright
    # core where the warped column coordinate hits a corridor centre, with a soft
    # halo falloff to either side. This is the dominant structure, not speckle.
    warp_x = _noise(ws, [ws[1] // 3, ws[1] // 6], [0.6, 0.4], sd + 5)   # billow sideways
    drift = _noise(ws, [ws[0] // 4, ws[0] // 8], [0.6, 0.4], sd + 17)   # vertical lean
    # ANGLE: pan slides the curtains sideways and breathes their ray phase.
    pan_u = _cx_directional_mask(ws, "u", sd + 67, freq=6.0)
    pan_v = _cx_directional_mask(ws, "v", sd + 41, freq=7.0)
    xw = x + warp_x * 0.30 + drift * y * 0.18 + (pan_u - 0.5) * 0.14

    n_curtain = 5.0          # a FEW wide ribbons (door-to-roof scale) — not stripes
    col = xw * n_curtain
    # distance to the nearest corridor centre (each integer of `col` is a curtain).
    cdist = np.abs((col - np.floor(col)) - 0.5) * 2.0   # 0 at centre, 1 at the gap
    # protected ridge: hard bright CORE + soft halo (raised to a power for a crisp
    # core that decays smoothly = a draped sheet, not a hard bar).
    core = np.clip(1.0 - cdist * 1.45, 0.0, 1.0) ** 1.6        # bright spine
    halo = np.clip(1.0 - cdist, 0.0, 1.0) ** 2.6 * 0.55        # soft surrounding glow
    body = np.clip(core + halo, 0.0, 1.0)
    # per-curtain brightness + a per-curtain hue offset so neighbouring curtains
    # don't all start at the same colour (curtain index from the floored column).
    cidx = np.floor(col).astype(np.int32)
    cbright = 0.62 + 0.38 * _cell_hash01(cidx, sd + 23)        # 0.62..1.0 per curtain
    chue_off = _cell_hash01(cidx, sd + 29)                      # 0..1 hue phase offset
    body = body * cbright

    # ─ Band B (octave ~512): vertical RAY striations ribbing the sheets (the fine
    # filament rays inside an aurora) + height fade (curtains hang from the top).
    rays = 0.5 + 0.5 * np.sin((xw * 90.0 + (pan_v - 0.5) * 0.7) * two_pi)
    rays = 0.55 + 0.45 * rays                                   # never fully extinguish
    height_glow = np.clip(1.1 - y * 0.35, 0.55, 1.1)           # a touch brighter up top
    curtain = body * rays * height_glow

    # ─ HUE GRADIENT ALONG THE CURTAIN: bottom = green ray base (R+Cc -> cyan/green),
    # top = magenta/violet tips (M+Cc). `hue_t` runs 0 (bottom) -> 1 (top), offset
    # per-curtain so the colour sweep starts at a different phase in each ribbon ->
    # MANY hues across the frame. Each channel reads a DIFFERENT lobe of this sweep
    # so the geometry decorrelates (M, R, Cc are not one field rescaled).
    hue_t = np.clip((1.0 - y) + (chue_off - 0.5) * 0.5, 0.0, 1.0)
    hue_t = hue_t + drift * 0.12                                # ragged colour edges
    hue_t = np.clip(hue_t, 0.0, 1.0)
    # lobes peak at different heights: green low, cyan low-mid, violet high, mag top.
    lobe_green = np.clip(1.0 - np.abs(hue_t - 0.12) * 2.6, 0.0, 1.0)   # R strong
    lobe_cyan = np.clip(1.0 - np.abs(hue_t - 0.42) * 2.4, 0.0, 1.0)    # R+Cc
    lobe_violet = np.clip(1.0 - np.abs(hue_t - 0.74) * 2.6, 0.0, 1.0)  # M+Cc
    lobe_mag = np.clip(1.0 - np.abs(hue_t - 0.95) * 3.0, 0.0, 1.0)     # M (tips)

    # offset-phase edge FRINGE (rides the curtain EDGES, a separate thin geometry).
    if curtain.shape[1] >= 2:
        fringe = np.abs(np.diff(curtain, axis=1, prepend=curtain[:, :1]))
    else:
        fringe = np.zeros_like(curtain)
    fringe = fringe / (fringe.max() + 1e-6)

    # COMPOSE the curtains as the DOMINANT, BRIGHT structure (sky stays a dim floor
    # but the curtains carry std>=20 on their own). Each channel = curtain *
    # (its hue lobes), so the three channels light DIFFERENT heights of the drape.
    sky_m, sky_r, sky_cc = 18.0, 16.0, 20.0                     # dim aurora sky floor
    # Amplitudes sized so the brightest curtain spines stay under 255 post-sm
    # (c~1.42): the violet/magenta tips and green base are the dominant reads but
    # do not white-clip (kept <1% per channel while std stays well above the floor).
    # wild-spec-v2-straggler-fix 2026-06-07: violet/magenta curtain TIPS pushed raw
    # M clip to ~1.38% (>1%); trimmed lobe amps (124->116, 138->126) so the bright
    # magenta tips sit just under 255 — the dominant curtain read is unchanged.
    M = sky_m + curtain * (lobe_violet * 116 + lobe_mag * 126) * c + fringe * lobe_mag * 52
    R = sky_r + curtain * (lobe_green * 168 + lobe_cyan * 112) * c + fringe * lobe_green * 38
    CC = sky_cc + curtain * (lobe_cyan * 140 + lobe_violet * 120 + lobe_green * 66) * c \
        + fringe * (lobe_cyan + lobe_violet) * 56

    # ─ Band C (full-res FINE): the starfield — ONLY here, sparse crisp single-pixel
    # white pins (NEAREST-clean) so stars stay crisp on top of the bright curtains.
    stars = _sparse_dots((h, w), sd + 99, density=0.0013)
    star_fine = _cx_ultra_micro((h, w), sd + 121)
    star = stars * (0.7 + 0.3 * star_fine)
    # a faint per-channel micro grain so the sky floor isn't dead-flat (decorrelating).
    g = (star_fine - 0.5)
    # straggler-fix: M star pin 120->104 so a star landing on a bright magenta tip
    # doesn't re-push M over 255 (raw clip <1%). R/Cc pins unchanged.
    micro = (star * 104.0 + g * 7.0, star * 120.0 - g * 6.0, star * 125.0 + g * 7.0)

    return _finalize(M, R, CC, h, w, ws, micro_pack=micro)


# ════════════════════════════════════════════════════════════════════════════
EXPORTS = {
    "chameleon": spec_chameleon,
    "color_flip_wrap": spec_color_flip_wrap,
    "pagani_tricolore": spec_pagani_tricolore,
    "holographic_base": spec_holographic_base,
    "prismatic": spec_prismatic,
    "bioluminescent": spec_bioluminescent,
    "shokk_spectrum": spec_shokk_spectrum,
    "shokk_prism": spec_shokk_prism,
    "shokk_aurora": spec_shokk_aurora,
}
