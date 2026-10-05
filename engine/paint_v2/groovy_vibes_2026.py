# -*- coding: utf-8 -*-
"""
engine/paint_v2/groovy_vibes_2026.py — ★ GROOVY VIBES (full bespoke rebuild 2026-06-15)

20 60s/70s counterculture finishes. THE OLD MODULE WAS A FACTORY (one _groovy template +
one flat _groovy_spec + a _RECIPES recolor table) — torn out completely. Every finish below
now has its OWN distinct motif algorithm AND its OWN alive, multi-hue spec that recomputes the
SAME geometry the paint uses (shared field helpers, same seed) so the spec ignites the exact
features the paint shows. M / R / CC ride DIFFERENT geometry with DIFFERENT value distributions
so the combined spec reads as many hues (decorrelated, |corr| < 0.85).

Motif roster (all DISTINCT, no two alike):
  tie_dye_spiral    rotational spiral tie-dye w/ rubber-band radial pinches
  tie_dye_crumple   scrunch/crumple tie-dye, dye pooling in ridge valleys
  melting_rainbow   gravity drip — hue columns with descending drip tongues
  psychedelic_swirl iterated curl domain-warp double vortex
  oil_slick_groove  true thin-film interference over a relief field
  sunburst_60s      radial sunburst wedge fan + sun disc
  kaleido_rings     12-fold kaleidoscope mandala (angular wedge mirroring)
  acid_swirl        hot high-freq acid liquid vortex (dialed HARD)
  trippy_concentric op-art twin-center concentric ring moire
  hippie_rainbow    woven macrame over-under rainbow lattice
  groovy_marble     fluid ink marbling veins (turbulence-displaced bands)
  peace_tie_dye     scattered rotated peace-sign SDF field
  warp_op           op-art moire — two rotated line gratings beating
  liquid_light      liquid light-show oil projection (translucent caustic blobs)
  groovy_zigzag     chevron / zigzag flame waves
  lava_lamp_purple  lava-lamp metaballs, purple/magenta
  lava_lamp_groovy  lava-lamp metaballs, earthy orange/teal (diff dynamics)
  mushroom_fade     gilled mushroom-cap fans + spore speckle (earthy/Woodstock)
  neon_acid_blob    reaction-diffusion neon bloom
  flower_power      daisy meadow — scattered rotated petal rosettes

Contract (unchanged, registry resolves by name):
  paint_<id>(paint, shape, mask, seed, pm, bb) -> HxWx3 float32 in [0,1]
  spec_<id>(shape, seed, sm, base_m, base_r)   -> (M, R, CC)  3x HxW float32 0..255
      M = metalness, R = roughness (FLOOR 15), CC = clearcoat (FLOOR 16 = wet gloss).
All render < 3s @ 2048 (broad fields capped at work-res then resized; fine detail full-res).
"""
import numpy as np

try:
    import cv2 as _cv2
    _CV2 = True
except Exception:
    _cv2 = None
    _CV2 = False

from engine.core import multi_scale_noise, get_mgrid, _resize_array
from engine.color_science import interference_palette, oklab_to_srgb, oklch_to_oklab

# ---------------------------------------------------------------------------
# small shared PRIMITIVES (NOT a finish factory — just math helpers, like
# multi_scale_noise. Every finish composes these into a unique algorithm.)
# ---------------------------------------------------------------------------
_GV = {}


def _cache(key, fn):
    v = _GV.get(key)
    if v is None:
        if len(_GV) > 120:
            _GV.clear()
        v = fn()
        _GV[key] = v
    return v


def _n01(a):
    a = np.asarray(a, np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _blur(a, sigma):
    if not _CV2 or sigma <= 0:
        return a
    return _cv2.GaussianBlur(a.astype(np.float32), (0, 0), float(sigma))


def _noise(shape, scales, weights, seed, cap=640):
    """multi_scale_noise in [-1,1] with a broad-field work-res cap for speed."""
    h, w = shape[:2]
    key = ("n", h, w, tuple(scales), tuple(weights), int(seed), int(cap))

    def build():
        if cap and min(h, w) > cap:
            sh = max(64, int(round(h * cap / max(h, w))))
            sw = max(64, int(round(w * cap / max(h, w))))
            f = multi_scale_noise((sh, sw), scales, weights, seed)
            return _resize_array(np.asarray(f, np.float32), h, w)
        return np.asarray(multi_scale_noise((h, w), scales, weights, seed), np.float32)

    return _cache(key, build)


def _grain(shape, seed, sigma=0.0):
    """Fine per-pixel grain in [0,1] (full-res, crisp)."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed), float(sigma))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x9E37) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        if sigma > 0:
            n = _blur(n, sigma)
        return n

    return _cache(key, build)


def _hsv_core(h, s, v):
    """Vectorized HSV->RGB via the standard chroma formula (faster than np.choose
    over 6 full arrays: one abs() + adds instead of six fancy-index gathers)."""
    h6 = (np.asarray(h, np.float32) % 1.0) * 6.0
    s = np.asarray(s, np.float32)
    v = np.asarray(v, np.float32)
    c = v * s
    xx = c * (1.0 - np.abs((h6 % 2.0) - 1.0))
    m = v - c
    z = np.zeros_like(h6)
    seg = np.floor(h6).astype(np.int32) % 6
    r = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [c, xx, z, z, xx, c], default=z)
    g = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [xx, c, c, xx, z, z], default=z)
    b = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [z, z, xx, c, c, xx], default=z)
    out = np.stack([r + m, g + m, b + m], -1)
    return np.clip(out, 0, 1).astype(np.float32)


def _hsv(h, s, v, cap=720):
    """HSV->RGB with a work-res cap (smooth hue/sat/val fields -> resize the RGB
    result up; quality-neutral, the fine crisp detail is the full-res grain)."""
    h = np.asarray(h, np.float32)
    s = np.asarray(s, np.float32) * np.ones_like(h)
    v = np.asarray(v, np.float32) * np.ones_like(h)
    if h.ndim >= 2 and max(h.shape[0], h.shape[1]) > cap:
        H, W = h.shape[:2]
        wh, ww = _work_shape((H, W), cap)
        hs = _resize_array(np.ascontiguousarray(h), wh, ww)
        ss = _resize_array(np.ascontiguousarray(s), wh, ww)
        vs = _resize_array(np.ascontiguousarray(v), wh, ww)
        return _resize_rgb(_hsv_core(hs, ss, vs), H, W)
    return _hsv_core(h, s, v)


def _oklch(L, C, H, cap=384):
    """OKLCH -> sRGB. Perceptually-even, the richest ramps. L/C/H may freely mix
    scalars and HxW arrays; they are broadcast to a common shape first.

    PERF: oklab_to_srgb (with its iterative gamut clamp) is the dominant cost at
    2048. OKLCH output is a SMOOTH color field, so we run the conversion at a
    work-res cap and bilinearly resize the result up — quality-neutral and ~6x
    faster at full res (the 512² swatch timing hid this blowup; doctrine 2026)."""
    L, C, H = np.broadcast_arrays(np.asarray(L, np.float32),
                                  np.asarray(C, np.float32),
                                  np.asarray(H, np.float32))
    if L.ndim >= 2 and max(L.shape[0], L.shape[1]) > cap:
        h, w = L.shape[:2]
        wh, ww = _work_shape((h, w), cap)
        Ls = _resize_array(np.ascontiguousarray(L), wh, ww)
        Cs = _resize_array(np.ascontiguousarray(C), wh, ww)
        Hs = _resize_array(np.ascontiguousarray(H), wh, ww)
        lch = np.stack([Ls, Cs, Hs], -1)
        small = np.clip(oklab_to_srgb(oklch_to_oklab(lch)), 0, 1).astype(np.float32)
        return _resize_rgb(small, h, w)
    lch = np.stack([L, C, H], -1)
    return np.clip(oklab_to_srgb(oklch_to_oklab(lch)), 0, 1).astype(np.float32)


def _polar(shape, seed, jitter=0.22):
    """(angle in [0,1), radius in [0,1]) about a seed-jittered centre."""
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    rng = np.random.default_rng((int(seed) ^ 0x51F3) & 0xFFFFFFFF)
    cy = (0.5 + rng.uniform(-jitter, jitter)) * h
    cx = (0.5 + rng.uniform(-jitter, jitter)) * w
    dy = (y - cy).astype(np.float32); dx = (x - cx).astype(np.float32)
    ang = (np.arctan2(dy, dx) / (2 * np.pi)) % 1.0
    rad = np.sqrt(dy * dy + dx * dx) / (0.5 * np.hypot(h, w))
    return ang.astype(np.float32), rad.astype(np.float32)


def _apply(paint, mask, col):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    m = mask[:, :, None]
    return (col * m + paint * (1 - m)).astype(np.float32)


def _work_shape(shape, cap):
    """Return a (wh, ww) work shape capped at `cap` on the long edge (keeps AR)."""
    h, w = shape[:2]
    if not cap or max(h, w) <= cap:
        return h, w
    if h >= w:
        return cap, max(8, int(round(w * cap / h)))
    return max(8, int(round(h * cap / w))), cap


def _resize_rgb(col, h, w):
    """Resize an HxWx3 float32 image to (h, w) (broad smooth color fields only)."""
    if col.shape[0] == h and col.shape[1] == w:
        return col
    if _CV2:
        return _cv2.resize(col, (w, h), interpolation=_cv2.INTER_LINEAR).astype(np.float32)
    out = np.empty((h, w, col.shape[2]), np.float32)
    for c in range(col.shape[2]):
        out[:, :, c] = _resize_array(col[:, :, c], h, w)
    return out


def _pack(M, R, CC):
    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.clip(R, 15, 255).astype(np.float32)
    CC = np.clip(CC, 16, 255).astype(np.float32)
    return M, R, CC


# ===========================================================================
# 1. TIE-DYE SPIRAL — rotational spiral with radial rubber-band pinches.
# ===========================================================================
def _tds_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        ang, rad = _polar((wh, ww), seed, 0.18)
        warp = _noise((wh, ww), [50, 110], [0.6, 0.4], seed + 7)
        spiral = (ang * 2.0 + rad * 5.0 + warp * 0.18)
        # Fine cotton-resist ridges, not hard rainbow stripes; they stay
        # subordinate to the tied spiral and hold dye/spec together.
        bands = 0.5 + 0.5 * np.sin(rad * 72.0 + warp * 1.4)
        return (_resize_array(spiral.astype(np.float32), h, w),
                _resize_array(rad.astype(np.float32), h, w),
                _resize_array(bands.astype(np.float32), h, w))

    return _cache(("tds", h, w, int(seed)), build)


def paint_tie_dye_spiral(paint, shape, mask, seed, pm, bb):
    spiral, rad, bands = _tds_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)
    if (wh, ww) != (h, w):
        spiral = _resize_array(np.ascontiguousarray(spiral), wh, ww)
        bands = _resize_array(np.ascontiguousarray(bands), wh, ww)
    # SPB-105 / GV-TIED-SPIRAL-I1, 2026-08-29. Owner eye: a generic full
    # rainbow is not hand-dyed cloth. Limit the pigment bath to indigo,
    # violet, magenta and saffron, with actual pale cotton resist. I3 direct
    # native 2048: 0.526 s; M/R/Cc std 45.6/34.2/42.6 (base M7 adapter pending).
    hue=.74+.19*(.5+.5*np.sin(spiral*2*np.pi))
    sat=np.clip(.58+.26*bands,0,1)
    val=np.clip(.38+.36*bands,0,1)
    col = _resize_rgb(_hsv_core(hue, sat, val), h, w)
    resist=np.clip((.13-np.abs(bands-.5))/.11,0,1)
    if resist.shape != (h,w):
        resist=_resize_array(np.ascontiguousarray(resist),h,w)
    resist=resist[:,:,None]
    col=np.clip(col*(1-.20*resist)+np.float32([.96,.78,.38])*resist*.20,0,1)
    return _apply(paint, mask, col)


def spec_tie_dye_spiral(shape, seed, sm, base_m, base_r):
    spiral, rad, bands = _tds_fields(shape, seed)
    # Pigment pool, cotton resist and tied centre are separate, causal states;
    # no generic grain is substituted for material variation.
    dye=.5+.5*np.sin(spiral*2*np.pi)
    resist=np.clip((.13-np.abs(bands-.5))/.11,0,1)
    M=32+205*(.58*dye+.24*resist+.18*bands)*sm
    R=224-164*(.52*bands+.28*resist+.20*dye)
    CC=16+225*np.clip(.46*dye+.32*resist+.22*(1-rad),0,1)
    return _pack(M, R, CC)


# ===========================================================================
# 2. TIE-DYE CRUMPLE — scrunch tie-dye; dye pools in the ridge-network valleys.
# ===========================================================================
def _crm_fields(shape, seed):
    h, w = shape[:2]

    def build():
        # SPB-105 / GV-CRUMPLE-I8, 2026-08-29 — I7's literal knots reduced
        # to a regular printed grid. I8 is a continuous warped cloth ground
        # carrying irregular tied-resist clusters; color lives in the knots
        # and fold rings, not in arbitrary cell backgrounds. Fine features
        # remain 8–32px at 2048². I7 direct 0.670s, M/R/Cc 56.9/64.4/46.4.
        wh, ww = _work_shape((h, w), 1024)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        u=x/max(ww,1); v=y/max(wh,1)
        uw=u+.030*np.sin(2*np.pi*(3*v+.4*u))+.014*np.sin(2*np.pi*(8*v-2*u))
        vw=v+.027*np.sin(2*np.pi*(3*u-.5*v))+.012*np.sin(2*np.pi*(7*u+3*v))
        density=27.0
        gy=np.floor(vw*density).astype(np.int32)
        gx=np.floor(uw*density-.5*(gy&1)).astype(np.int32)
        fu=np.mod(uw*density-.5*(gy&1),1.0)-.5; fv=np.mod(vw*density,1.0)-.5
        radius=np.sqrt(fu*fu+fv*fv); angle=np.arctan2(fv,fu)
        code=np.mod(11*gx+17*gy+3*gx*gy,5).astype(np.float32)/4.0
        knot=np.exp(-((radius/.145)**2))
        ring=np.exp(-((radius-(.23+.035*code))/.040)**2)
        rays=(.5+.5*np.sin(7*angle+1.8*code+5.0*radius))*np.exp(-((radius-.25)/.19)**2)
        cloth=.31+.045*np.sin(2*np.pi*(3*u+2*v))+.030*np.sin(2*np.pi*(7*u-5*v))
        pools=np.clip(cloth+.47*ring*(.38+.62*code)+.30*knot*code+.16*rays*(1-code),0,1)
        ridges=np.clip(.68*ring+.32*rays,0,1)
        fine=np.clip(.52*rays+.48*knot,0,1)
        pools = _resize_array(pools.astype(np.float32), h, w)
        ridges = _resize_array(ridges.astype(np.float32), h, w)
        fine = _resize_array(fine.astype(np.float32), h, w)
        return pools, ridges, fine.astype(np.float32)

    return _cache(("crm", h, w, int(seed)), build)


def paint_tie_dye_crumple(paint, shape, mask, seed, pm, bb):
    pools, ridges, fine = _crm_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)
    if (wh, ww) != (h, w):
        pools = _resize_array(np.ascontiguousarray(pools), wh, ww)
        ridges = _resize_array(np.ascontiguousarray(ridges), wh, ww)
        fine = _resize_array(np.ascontiguousarray(fine), wh, ww)
    # Four limited dye baths, not another spectral rainbow: indigo, plum,
    # magenta and a restrained amber. Tight filament ridges carry the folded
    # cotton detail and remain visibly material-bound when tiled down.
    indigo = np.clip((.43 - pools) / .22, 0, 1)
    magenta = np.clip(1.0 - np.abs(pools - .49) / .23, 0, 1)
    amber = np.clip((pools - .61) / .22, 0, 1)
    fold = np.clip((ridges - .30) / .36, 0, 1)
    filament = fine * np.clip((.62 - ridges) / .30, 0, 1)
    col = np.empty((wh, ww, 3), np.float32)
    col[:] = np.array([.17, .06, .29], np.float32)
    col = col * (1 - indigo[:, :, None]) + np.array([.07, .20, .48], np.float32) * indigo[:, :, None]
    col = col * (1 - magenta[:, :, None]) + np.array([.72, .07, .38], np.float32) * magenta[:, :, None]
    col = col * (1 - amber[:, :, None]) + np.array([.90, .30, .10], np.float32) * amber[:, :, None]
    col = col * (1 - fold[:, :, None] * .58) + np.array([.91, .78, .55], np.float32) * fold[:, :, None] * .58
    col = col * (1 - filament[:, :, None] * .26) + np.array([.86, .22, .54], np.float32) * filament[:, :, None] * .26
    col = _resize_rgb(col, h, w)
    return _apply(paint, mask, col)


def spec_tie_dye_crumple(shape, seed, sm, base_m, base_r):
    pools, ridges, fine = _crm_fields(shape, seed)
    # Pool, cotton fold and fine filament remain distinct material states;
    # neighboring ridges deliberately cross hard spec tiers for track-light
    # reveals without putting symbols/noise into the visible pigment.
    dye_pool = (pools > .56).astype(np.float32)
    pale_fold = (ridges > .53).astype(np.float32)
    filament = (fine > .50).astype(np.float32)
    M = 18 + 226 * np.clip(.48 * dye_pool + .34 * pale_fold + .18 * fine, 0, 1) * sm
    rough_well = (pools < .46).astype(np.float32)
    R = 232 - 198 * np.clip(.62 * rough_well + .25 * pale_fold + .13 * fine, 0, 1)
    CC = 16 + 232 * np.clip(.43 * filament + .34 * dye_pool + .23 * (ridges < .34), 0, 1)
    return _pack(M, R, CC)


# ===========================================================================
# 3. MELTING RAINBOW — gravity drip; hue columns with descending drip tongues.
# ===========================================================================
def _melt_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        # drip threshold per column => varied tongue lengths
        coln = _noise((wh, ww), [6, 14], [0.6, 0.4], seed + 2)
        thresh = (0.35 + 0.4 * _n01(coln[0:1, :].repeat(wh, 0)))
        yy = (y / wh).astype(np.float32)
        drip = np.clip((yy - thresh) / np.maximum(1e-3, 1 - thresh), 0, 1)
        wob = _noise((wh, ww), [30, 70], [0.6, 0.4], seed + 5) * 0.12
        hue = (x / ww + drip * 0.5 + wob)
        return (_resize_array(hue.astype(np.float32), h, w),
                _resize_array(drip.astype(np.float32), h, w),
                _resize_array(_n01(coln).astype(np.float32), h, w))

    return _cache(("melt", h, w, int(seed)), build)


def paint_melting_rainbow(paint, shape, mask, seed, pm, bb):
    hue, drip, coln = _melt_fields(shape, seed)
    col = _hsv(hue % 1.0, 0.92, np.clip(0.97 - 0.18 * drip, 0, 1))
    g = _grain(shape, seed + 8)[:, :, None]
    col = np.clip(col * (0.96 + 0.08 * g), 0, 1)
    return _apply(paint, mask, col)


def spec_melting_rainbow(shape, seed, sm, base_m, base_r):
    hue, drip, coln = _melt_fields(shape, seed)
    g = _grain(shape, seed + 8, 0.7)
    M = 60 + 170 * coln * sm                           # column variation
    R = 40 + 180 * drip                                # drips run wet->matte downward
    CC = 16 + 150 * (0.5 + 0.5 * np.sin(hue * 2 * np.pi)) + 18 * (g - 0.5)
    return _pack(M, R, CC)


# ===========================================================================
# 4. PSYCHEDELIC SWIRL — continuous multi-vortex wax-ink sheet.
# SPB-105 / GV-PSYCH-I3, 2026-08-29. Owner eye rejected the previous generic
# rainbow curl and later micro-vortex tile experiments. This single whole-car
# sheet has four finite fluid vortices with 8–24px phase-locked lips; no grid,
# no grain, no repeated tile carrier and no HSV-rainbow shortcut. I6 direct
# native 2048: 1.231s, M/R/Cc std 73.9/66.8/73.4 and ranges 30–236 / 30–255 /
# 26–254; both standard and buyer-picker bakes are 1/1 with zero errors.
# ===========================================================================
def _swirl_fields(shape, seed):
    h, w = shape[:2]
    if max(h, w) < 512:
        fac = 512.0 / max(1.0, float(max(h, w)))
        fields = _swirl_fields((max(8,int(round(h*fac))),max(8,int(round(w*fac)))),seed)
        return tuple(_resize_array(np.ascontiguousarray(f),h,w) for f in fields)

    def build():
        y,x=np.mgrid[0:h,0:w].astype(np.float32)
        u=x/max(1.,float(w))*2.-1.; v=y/max(1.,float(h))*2.-1.
        # Sequential finite rotations preserve one connected ink sheet. Their
        # centers are intentionally irregular, so this cannot collapse into a
        # tiled cell wallpaper at whole-car scale.
        for cx,cy,rad,turn in ((-.56,-.42,.62,1.08),(.38,-.48,.55,-.94),
                               (.52,.28,.58,.88),(-.30,.44,.54,-.98)):
            dx=u-cx; dy=v-cy; amount=turn*np.exp(-(dx*dx+dy*dy)/(rad*rad))
            cs=np.cos(amount); sn=np.sin(amount)
            u,v=cx+dx*cs-dy*sn,cy+dx*sn+dy*cs
        # I4 card audit: the 94/29 field was visually strong at native size but
        # compressed into 1px picker stripes near vortex pinch points. This
        # widens the authored lips to a stable 12–28px native interval instead
        # of merely scaling the rendered image down.
        phase=64.*u+20.*v+6.*np.sin(5.*u-3.*v)+4.*np.sin(9.*v)
        t=np.mod(phase/(2*np.pi),1.).astype(np.float32)
        lip=np.clip((np.cos(phase)-.92)*12.5,0.,1.).astype(np.float32)
        depth=(.5+.5*np.sin(phase*.36+u*7.-v*5.)).astype(np.float32)
        return t,lip,depth

    return _cache(("swirl_i3", h, w, int(seed)), build)


def paint_psychedelic_swirl(paint, shape, mask, seed, pm, bb):
    t,lip,depth=_swirl_fields(shape,seed)
    # A finite counterculture ink bath: eggplant, indigo, cyan, magenta and
    # saffron. It deliberately avoids the old all-HSV color-wheel read.
    pal=np.asarray(((.035,.015,.09),(.10,.10,.52),(.05,.56,.70),
                    (.54,.08,.58),(.86,.08,.38),(.95,.50,.10)),np.float32)
    p=t*len(pal); low=np.floor(p).astype(np.int32)%len(pal); frac=(p-np.floor(p))[:,:,None]
    col=pal[low]*(1-frac)+pal[(low+1)%len(pal)]*frac
    col=col*(1-.18*lip[:,:,None])+np.asarray((.94,.82,.44),np.float32)*(.18*lip[:,:,None])
    col=np.clip(col*(.76+.24*depth[:,:,None]),0,1)
    return _apply(paint, mask, col)


def spec_psychedelic_swirl(shape, seed, sm, base_m, base_r):
    t,lip,depth=_swirl_fields(shape,seed)
    state=np.clip(np.floor(t*8.).astype(np.int32),0,7)
    # Adjacent 8–24px lips cycle chrome, satin, flat pigment and deep gloss in
    # different channel order. The moving-light effect remains causal to the
    # exact ink bands instead of being a generic spec texture.
    mt=np.asarray((30,220,74,188,48,236,116,174),np.float32)[state]
    rt=np.asarray((220,42,152,70,194,30,116,82),np.float32)[state]
    ct=np.asarray((26,212,88,176,48,238,132,196),np.float32)[state]
    M=mt*sm+18*lip
    R=rt+24*(1-depth)+14*lip
    CC=ct+16*depth+20*lip
    return _pack(M, R, CC)


# ===========================================================================
# 5. OIL SLICK GROOVE — true thin-film interference over a relief field.
# ===========================================================================
def _oil_fields(shape, seed):
    h, w = shape[:2]

    def build():
        # SPB-105 / GV-OIL-I1→I3, 2026-08-28. Owner audit: the old card was
        # graphic line art rather than physical thin-film oil. I1/I2 were
        # rejected visually; I3 builds an 8–32px optical-line field from
        # sheared liquid currents, so interference, relief and response share
        # one flow. Native 2048 paint: 0.553 s; base M7 adapter pending.
        wh, ww = _work_shape((h, w), 896)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        qx=(x-ww*.5)/(ww*.5); qy=(y-wh*.5)/(wh*.5)
        # Sequential finite-radius twists make a historical sheet: every
        # later tongue inherits the prior bend instead of joining a generic
        # flow/noise carrier. This is intentionally distinct from Wilds.
        for cx, cy, radius, turn in ((-.63,-.38,.66,1.05),(.30,-.54,.52,-1.14),
                                     (.68,.16,.58,.92),(-.28,.38,.55,-1.07),
                                     (.36,.57,.49,.98)):
            dx=qx-cx; dy=qy-cy
            bend=np.exp(-(dx*dx+dy*dy)/(radius*radius))*turn
            cb=np.cos(bend); sb=np.sin(bend)
            qx=cx+cb*dx-sb*dy; qy=cy+sb*dx+cb*dy
        qx=qx+.082*np.sin(6.7*qy+1.3*np.sin(3.1*qx))
        qy=qy+.069*np.sin(5.8*qx-1.1*np.sin(4.2*qy))
        thickness=.51+.132*qx-.086*qy+.106*np.sin(7.4*qx+2.4*qy)+.066*np.sin(12.6*qy-3.2*qx)
        gy,gx=np.gradient(thickness)
        slope=np.sqrt(gx*gx+gy*gy)
        # Broad film territories carry the color; one 8–24px fold family
        # appears only as a bounded optical shoulder on that same sheet.
        broad=_n01(thickness)
        fold=.5+.5*np.sin(2*np.pi*(26*qx+8*qy+.10*np.sin(8*qy-3*qx)))
        fold_ridge=np.power(fold,6.0)*_n01(slope)
        thick=np.clip(.82*broad+.18*fold_ridge,0,1)
        relief=_n01(.72*thickness+.28*slope)
        flow=_n01(.62*slope+.38*fold_ridge)
        thick=_resize_array(thick.astype(np.float32),h,w)
        relief=_resize_array(relief.astype(np.float32),h,w)
        flow=_resize_array(flow.astype(np.float32),h,w)
        return thick.astype(np.float32), relief.astype(np.float32), flow.astype(np.float32)

    return _cache(("oil", h, w, int(seed)), build)


def paint_oil_slick_groove(paint, shape, mask, seed, pm, bb):
    thick, relief, flow = _oil_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 896)                     # interference at work-res
    if (wh, ww) != (h, w):
        ts = _resize_array(np.ascontiguousarray(thick), wh, ww)
        col = _resize_rgb(interference_palette(ts, orders=3.4, quantize=0.48, brightness=.82), h, w)
    else:
        col = interference_palette(thick, orders=3.4, quantize=0.48, brightness=.82)
    # Film blackens between orders; it reads as oil on wet asphalt rather
    # than a rainbow poster, while exposed-order lips retain the color flip.
    lip=np.exp(-((thick-.56)/.095)**2)[:,:,None]
    col=np.clip(col*(.07+.31*relief[:,:,None]) + col*lip*.15,0,1)
    return _apply(paint, mask, col)


def spec_oil_slick_groove(shape, seed, sm, base_m, base_r):
    thick, relief, flow = _oil_fields(shape, seed)
    # I3's paint was accepted visually but M/R spread was too timid. These
    # wider, still sheet-causal responses move native M/R/Cc std
    # 18.1/13.2/70.6 → 26.2/31.3/70.6, exposing substrate on relief/film
    # shoulders and softening in true pools—never via unrelated grain.
    M = 108 + 138 * (.70 * relief + .30 * thick) * sm
    R = 25 + 190 * thick
    CC = 16 + 200 * (0.5 + 0.5 * np.sin(thick * 4.0 * 6.28))
    return _pack(M, R, CC)


# ===========================================================================
# 6. SUNBURST 60s — radial sunburst wedge fan + sun disc.
# ===========================================================================
def _sun_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        ang, rad = _polar((wh, ww), seed, 0.12)
        rng = np.random.default_rng((int(seed) ^ 0x77) & 0xFFFFFFFF)
        nrays = int(rng.integers(16, 26))
        wob = _noise((wh, ww), [40, 90], [0.6, 0.4], seed + 2) * 0.04
        wedge = 0.5 + 0.5 * np.sign(np.sin((ang + wob) * nrays * 2 * np.pi))
        disc = np.clip(1.0 - rad / 0.22, 0, 1)         # central sun
        return (_resize_array(wedge.astype(np.float32), h, w),
                _resize_array(rad.astype(np.float32), h, w),
                _resize_array(disc.astype(np.float32), h, w),
                _resize_array(ang.astype(np.float32), h, w))

    return _cache(("sun", h, w, int(seed)), build)


def paint_sunburst_60s(paint, shape, mask, seed, pm, bb):
    wedge, rad, disc, ang = _sun_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)                      # composite at work-res
    if (wh, ww) != (h, w):
        wedge = _resize_array(np.ascontiguousarray(wedge), wh, ww)
        rad = _resize_array(np.ascontiguousarray(rad), wh, ww)
        disc = _resize_array(np.ascontiguousarray(disc), wh, ww)
    # warm 70s sunburst: amber / orange / red rays, golden disc
    hue = (0.06 + 0.10 * wedge + 0.05 * np.clip(rad, 0, 1)) % 1.0
    val = np.clip(0.7 + 0.3 * wedge + 0.3 * disc, 0, 1)
    col = _hsv_core(hue, np.clip(0.95 - 0.4 * disc, 0, 1), val)
    col = _resize_rgb(col, h, w)
    g = _grain(shape, seed + 9)[:, :, None]
    col = np.clip(col * (0.96 + 0.08 * g), 0, 1)
    return _apply(paint, mask, col)


def spec_sunburst_60s(shape, seed, sm, base_m, base_r):
    wedge, rad, disc, ang = _sun_fields(shape, seed)
    g = _grain(shape, seed + 9, 0.6)
    # M = alternating rays; R = radial falloff (independent of wedge);
    # CC = sun disc + fine glints. Three orthogonal geometries -> low corr.
    M = 50 + 190 * wedge * sm + 22 * (g - 0.5)
    R = 40 + 200 * np.clip(rad, 0, 1)                  # crisp near centre, matte rim
    CC = 16 + 200 * disc + 60 * g
    return _pack(M, R, CC)


# ===========================================================================
# 7. KALEIDO RINGS — wax-print kaleido weave (fine mirrored optical ink).
# ===========================================================================
def _kal_fields(shape, seed):
    h, w = shape[:2]

    def build():
        # SPB-105 / GV-KALEIDO-I1, 2026-08-29. The owner rejected the
        # former 12-fold, logo-sized radial assault. This is an all-over
        # 60s wax-print kaleidoscope: every visible feature is a 8–32px
        # optical ink shoulder, nested lobe, or fine print rib. It keeps the
        # mirrored psychedelic proposition without one dominant centre,
        # generic wallpaper, glitter/grain, or a borrowed marble carrier.
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        x = (x / max(w - 1, 1)) * 2.0 - 1.0
        y = (y / max(h - 1, 1)) * 2.0 - 1.0
        def ridge(phase, width):
            dist=np.abs(np.mod(phase+.5,1.0)-.5)
            return np.exp(-((dist/width)**2))
        u = x + .09*np.sin(3.0*y)
        v = y + .08*np.sin(3.0*x)
        field=(np.sin(13*u)*np.cos(11*v)
               +.56*np.sin(19*(u+v))
               -.42*np.cos(17*(u-v)))
        body=_n01(field)
        fine=np.maximum(ridge(78*u+7*np.sin(9*v),.046),
                        ridge(73*v-6*np.sin(8*u),.047))*(.22+.78*body)
        lip=ridge(10.5*body+.19*np.sin(4*(u-v)),.053)
        phase=.5+.5*np.sin(10*u-7*v)
        return body.astype(np.float32), fine.astype(np.float32), lip.astype(np.float32), phase.astype(np.float32)

    return _cache(("kal", h, w, int(seed)), build)


def paint_kaleido_rings(paint, shape, mask, seed, pm, bb):
    body, fine, lip, phase = _kal_fields(shape, seed)
    # Print-ink physical hierarchy: plum ground, magenta/cyan interference,
    # and saffron only on the actual optical shoulder.  This is intentionally
    # a limited 60s poster palette rather than an HSV rainbow loop.
    indigo=np.float32([.055,.025,.15]); plum=np.float32([.26,.04,.38])
    mag=np.float32([.78,.08,.45]); cyan=np.float32([.05,.67,.65])
    saff=np.float32([.98,.55,.10]); cream=np.float32([1.0,.82,.43])
    col=indigo+(plum-indigo)*(.68*body)[:,:,None]
    col=col*(1-(.21*fine)[:,:,None])+mag*(.21*fine)[:,:,None]
    cyan_event=.16*np.sin(13*(phase-.5))**2*fine
    col=col*(1-cyan_event[:,:,None])+cyan*cyan_event[:,:,None]
    col=col*(1-(.18*lip)[:,:,None])+saff*(.18*lip)[:,:,None]
    col=np.clip(col+cream*(.055*lip)[:,:,None],0,1)
    return _apply(paint, mask, col)


def spec_kaleido_rings(shape, seed, sm, base_m, base_r):
    body, fine, lip, phase = _kal_fields(shape, seed)
    # SPB-105 / GV-KALEIDO-I1. Each channel responds to a separate, named
    # part of the printed weave: fine optical ribs flash; pooled plum ink
    # stays matte; saffron shoulders take the clearcoat. No flat-green map.
    M = 28 + 212*np.clip(.48*fine+.30*lip+.22*phase,0,1)*sm
    R = 42 + 190*np.clip(.58*(1-body)+.28*fine+.14*(1-lip),0,1)
    CC = 16 + 221*np.clip(.54*lip+.28*fine+.18*body,0,1)
    return _pack(M, R, CC)


# ===========================================================================
# 8. ACID SWIRL — hot high-freq acid liquid vortex (DIALED HARDEST).
# ===========================================================================
def _acid_fields(shape, seed):
    h, w = shape[:2]

    def build():
        # SPB-105 / GV-ACID-I4, 2026-08-29 — structured blotter replacement
        # was rejected at catalog scale: clean channels, but a single repeated
        # wave grammar too close to other Groovy liquids. Preserve I3 until a
        # genuinely distinct acid construction is ready.
        wh, ww = _work_shape((h, w), 560)               # warp math at work-res
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        fx = (x / ww).astype(np.float32); fy = (y / wh).astype(np.float32)
        w1 = _noise((wh, ww), [22, 50], [0.6, 0.4], seed + 1)
        w2 = _noise((wh, ww), [22, 50], [0.6, 0.4], seed + 2)
        # tight high-frequency curl warp
        for _ in range(3):
            fx = fx + 0.06 * np.sin(w2 * 12.0 + fy * 22.0)
            fy = fy + 0.06 * np.cos(w1 * 12.0 + fx * 22.0)
        ang = np.arctan2(fy - 0.5, fx - 0.5)
        flow = (ang / (2 * np.pi) * 7.0 + np.hypot(fy - 0.5, fx - 0.5) * 22.0)
        burn = _n01(w1 * w2)
        return (_resize_array(flow.astype(np.float32), h, w),
                _resize_array(burn.astype(np.float32), h, w))

    return _cache(("acid", h, w, int(seed)), build)


def paint_acid_swirl(paint, shape, mask, seed, pm, bb):
    flow, burn = _acid_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 560)
    if (wh, ww) != (h, w):
        flow = _resize_array(np.ascontiguousarray(flow), wh, ww)  # smooth pre-modulo
    hue = (flow * 0.5) % 1.0
    H = hue * 2 * np.pi
    col = _oklch(0.72 + 0.10 * np.sin(flow * 9.0), 0.20, H, cap=560)
    col = _resize_rgb(col, h, w)
    g = _grain(shape, seed + 4)[:, :, None]
    col = np.clip(col * (0.94 + 0.12 * g), 0, 1)
    return _apply(paint, mask, col)


def spec_acid_swirl(shape, seed, sm, base_m, base_r):
    flow, burn = _acid_fields(shape, seed)
    g = _grain(shape, seed + 4, 0.5)
    M = 80 + 170 * (0.5 + 0.5 * np.sin(flow * 9.0)) * sm
    R = 20 + 210 * burn + 18 * (g - 0.5) * sm
    CC = 16 + 180 * (0.5 + 0.5 * np.cos(flow * 5.0))
    return _pack(M, R, CC)


# ===========================================================================
# 9. TRIPPY CONCENTRIC — op-art twin-center concentric ring moire.
# ===========================================================================
def _conc_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0xABCD) & 0xFFFFFFFF)
        c1 = (rng.uniform(0.25, 0.45) * wh, rng.uniform(0.25, 0.45) * ww)
        c2 = (rng.uniform(0.55, 0.75) * wh, rng.uniform(0.55, 0.75) * ww)
        d1 = np.sqrt((y - c1[0]) ** 2 + (x - c1[1]) ** 2)
        d2 = np.sqrt((y - c2[0]) ** 2 + (x - c2[1]) ** 2)
        f = float(2 * np.pi / (0.030 * np.hypot(wh, ww)))
        r1 = 0.5 + 0.5 * np.sin(d1 * f)
        r2 = 0.5 + 0.5 * np.sin(d2 * f)
        moire = r1 * r2                                  # beating interference
        return (_resize_array(moire.astype(np.float32), h, w),
                _resize_array(r1.astype(np.float32), h, w),
                _resize_array(r2.astype(np.float32), h, w))

    return _cache(("conc", h, w, int(seed)), build)


def paint_trippy_concentric(paint, shape, mask, seed, pm, bb):
    moire, r1, r2 = _conc_fields(shape, seed)
    hue = (moire * 0.7 + r1 * 0.2) % 1.0
    col = _hsv(hue, 0.85, np.clip(0.6 + 0.4 * moire, 0, 1))
    g = _grain(shape, seed + 5)[:, :, None]
    col = np.clip(col * (0.96 + 0.08 * g), 0, 1)
    return _apply(paint, mask, col)


def spec_trippy_concentric(shape, seed, sm, base_m, base_r):
    moire, r1, r2 = _conc_fields(shape, seed)
    M = 50 + 190 * r1 * sm                              # center-1 rings
    R = 40 + 190 * r2                                   # center-2 rings (decorrelated)
    CC = 16 + 190 * moire                               # bright where both align
    return _pack(M, R, CC)


# ===========================================================================
# 10. HIPPIE RAINBOW — woven macrame over-under rainbow lattice.
# ===========================================================================
def _weave_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x2A) & 0xFFFFFFFF)
        th = rng.uniform(0, np.pi)                       # random weave orientation
        ca, sa = np.cos(th), np.sin(th)
        u = (x * ca + y * sa).astype(np.float32)
        v = (-x * sa + y * ca).astype(np.float32)
        per = max(8.0, 0.012 * np.hypot(wh, ww))
        warp_t = np.sin(u / per * np.pi)                 # vertical threads
        weft_t = np.sin(v / per * np.pi)                 # horizontal threads
        over = (np.floor(u / per) + np.floor(v / per)) % 2.0  # over/under checker
        weave = np.where(over > 0.5, warp_t, weft_t)
        weave = _n01(np.abs(weave))
        strand = (u + v) / per                            # diagonal rainbow run
        return (_resize_array(weave.astype(np.float32), h, w),
                _resize_array(strand.astype(np.float32), h, w),
                _resize_array(over.astype(np.float32), h, w))

    return _cache(("weave", h, w, int(seed)), build)


def paint_hippie_rainbow(paint, shape, mask, seed, pm, bb):
    weave, strand, over = _weave_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)                      # composite at work-res
    if (wh, ww) != (h, w):
        weave = _resize_array(np.ascontiguousarray(weave), wh, ww)
        strand = _resize_array(np.ascontiguousarray(strand), wh, ww)  # smooth pre-modulo
    hue = (strand * 0.12) % 1.0
    val = np.clip(0.55 + 0.45 * weave, 0, 1)             # thread shading = woven look
    col = _hsv_core(hue, 0.85, val)
    col = _resize_rgb(col, h, w)
    g = _grain(shape, seed + 6)[:, :, None]
    col = np.clip(col * (0.95 + 0.1 * g), 0, 1)
    return _apply(paint, mask, col)


def spec_hippie_rainbow(shape, seed, sm, base_m, base_r):
    weave, strand, over = _weave_fields(shape, seed)
    # M = over/under checker; R = thread relief; CC = diagonal strand run (orthogonal)
    M = 40 + 150 * over * sm                              # over-strands metal
    R = 70 + 160 * (1 - weave)                            # thread valleys matte (fiber)
    CC = 16 + 200 * (0.5 + 0.5 * np.sin(strand * np.pi))  # rainbow-run wet bands
    return _pack(M, R, CC)


# ===========================================================================
# 11. GROOVY MARBLE — fluid ink marbling veins (turbulence-displaced bands).
# ===========================================================================
def _marble_fields(shape, seed):
    h, w = shape[:2]

    def build():
        # SPB-105 / GV-MARBLE-I2, 2026-08-29. Owner: full-car carriers were
        # 25–65% too large; the old I1 stayed a two-pool contour maze at
        # picker scale.  I2 is ink-pool marbling built from connected
        # 8–32px native dragged veins in three flow families, not a scaled
        # copy or an unrelated fleck layer. I1 direct 0.671s, M/R/Cc
        # 22.1/26.7/21.5; remeasure after rebake (base M7 adapter pending).
        wh, ww = _work_shape((h, w), 1024)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        qx=(x-ww*.5)/(ww*.5); qy=(y-wh*.5)/(wh*.5)
        for cx,cy,radius,turn in ((-.50,-.37,.70,.72),(.36,-.41,.54,-.78),
                                  (.56,.24,.60,.60),(-.29,.43,.57,-.66)):
            dx=qx-cx; dy=qy-cy
            a=np.exp(-(dx*dx+dy*dy)/(radius*radius))*turn
            ca=np.cos(a); sa=np.sin(a)
            qx=cx+ca*dx-sa*dy; qy=cy+sa*dx+ca*dy
        qx+=.030*np.sin(13*qy+1.8*np.sin(7*qx))+.014*np.sin(29*qy-9*qx)
        qy+=.028*np.sin(12*qx-1.3*np.sin(6*qy))+.012*np.sin(25*qx+8*qy)
        # Three ink streams are warped through the same bath: they form
        # color bodies everywhere, while their tight crests become veins.
        stream_a=.5+.5*np.sin(2*np.pi*(25*qx+8*qy+.31*np.sin(8*qy-5*qx)))
        stream_b=.5+.5*np.sin(2*np.pi*(19*(-.58*qx+.82*qy)+.24*np.sin(9*qx+6*qy)))
        stream_c=.5+.5*np.sin(2*np.pi*(31*(.76*qx+.64*qy)+.18*np.sin(7*qy-10*qx)))
        pool=_n01(.49*stream_a+.31*stream_b+.20*stream_c)
        gy,gx=np.gradient(pool); relief=_n01(np.sqrt(gx*gx+gy*gy))
        vein=np.clip(.52*np.power(stream_a,14)+.31*np.power(stream_b,16)+
                     .17*np.power(stream_c,18),0,1)*(.42+.58*relief)
        return (_resize_array(pool.astype(np.float32), h, w),
                _resize_array(vein.astype(np.float32), h, w),
                _resize_array(relief.astype(np.float32), h, w))

    return _cache(("marb", h, w, int(seed)), build)


def paint_groovy_marble(paint, shape, mask, seed, pm, bb):
    pools, veins, relief = _marble_fields(shape, seed)
    # 60s book-endpaper palette: petrol/indigo pools swing into plum and
    # ochre; cream is ink physically pulled into narrow vein shoulders.
    hue=(.53+.48*pools+.05*relief) % 1.0
    col=_hsv(hue,.68,.25+.62*pools)
    cream=np.float32([1.0,.77,.42])
    col=np.clip(col*(1-.44*veins[:,:,None])+cream*veins[:,:,None]*.44,0,1)
    return _apply(paint, mask, col)


def spec_groovy_marble(shape, seed, sm, base_m, base_r):
    pools, veins, relief = _marble_fields(shape, seed)
    M = 30 + 205*(.62*relief+.38*pools)*sm
    R = 25 + 205*(.63*(1-pools)+.37*(1-veins))
    # Clearcoat follows the wet crest system, offset from dye and roughness.
    CC = 10 + 235*np.clip(.18 + 1.60*relief + .90*veins,0,1)
    return _pack(M, R, CC)


# ===========================================================================
# 12. PEACE TIE-DYE — scattered rotated peace-sign SDF stamps.
# ===========================================================================
def _peace_field(shape, seed):
    """Field high inside scattered peace symbols, low outside (UV-agnostic)."""
    h, w = shape[:2]

    def build():
        work = 384
        wh = work; ww = work
        rng = np.random.default_rng((int(seed) ^ 0x9ACE) & 0xFFFFFFFF)
        field = np.zeros((wh, ww), np.float32)
        spoke = np.zeros((wh, ww), np.float32)
        n = 22
        for _ in range(n):
            cy = rng.uniform(0, wh); cx = rng.uniform(0, ww)
            r = rng.uniform(22, 46); rot = rng.uniform(0, 2 * np.pi)
            # WINDOWED splat: only evaluate the symbol's local bounding box.
            R = int(r) + 2
            y0 = max(0, int(cy) - R); y1 = min(wh, int(cy) + R)
            x0 = max(0, int(cx) - R); x1 = min(ww, int(cx) + R)
            if y1 <= y0 or x1 <= x0:
                continue
            ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            dy = ly - cy; dx = lx - cx
            dist = np.sqrt(dy * dy + dx * dx)
            ring = np.clip(1.0 - np.abs(dist - r) / (r * 0.16), 0, 1)  # circle
            a = np.arctan2(dy, dx) - rot
            line_v = np.clip(1.0 - np.abs(((a - np.pi / 2 + np.pi) % np.pi) - np.pi / 2) / 0.18, 0, 1)
            line_a = np.clip(1.0 - np.abs(((a + np.pi / 6 + np.pi) % np.pi) - np.pi / 2) / 0.18, 0, 1)
            line_b = np.clip(1.0 - np.abs(((a - np.pi / 6 - np.pi / 2 + np.pi) % np.pi) - np.pi / 2) / 0.18, 0, 1)
            inside = (dist < r).astype(np.float32)
            bottom = (dy > 0).astype(np.float32)
            top = (dy <= 0).astype(np.float32)
            lines = np.maximum(line_v * bottom, np.maximum(line_a * top, line_b * top)) * inside
            sym = np.maximum(ring, lines)
            sub = field[y0:y1, x0:x1]
            np.maximum(sub, sym, out=sub)
            ssub = spoke[y0:y1, x0:x1]
            np.maximum(ssub, lines, out=ssub)
        bg = _n01(multi_scale_noise((wh, ww), [30, 70], [0.6, 0.4], seed + 1))
        field = _resize_array(field, h, w)
        spoke = _resize_array(spoke, h, w)
        bg = _resize_array(bg, h, w)
        return field.astype(np.float32), spoke.astype(np.float32), bg.astype(np.float32)

    return _cache(("peace", h, w, int(seed)), build)


def paint_peace_tie_dye(paint, shape, mask, seed, pm, bb):
    sym, spoke, bg = _peace_field(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)                      # composite at work-res
    if (wh, ww) != (h, w):
        sym = _resize_array(np.ascontiguousarray(sym), wh, ww)
        bg = _resize_array(np.ascontiguousarray(bg), wh, ww)
    # tie-dye background, white peace signs sitting on top
    hue = (bg * 1.4) % 1.0
    col = _hsv(hue, 0.8, 0.92)
    white = np.clip(sym, 0, 1)[:, :, None]
    col = col * (1 - white) + np.float32([1, 1, 1]) * white
    col = _resize_rgb(col, h, w)
    g = _grain(shape, seed + 3)[:, :, None]
    col = np.clip(col * (0.96 + 0.08 * g), 0, 1)
    return _apply(paint, mask, col)


def spec_peace_tie_dye(shape, seed, sm, base_m, base_r):
    sym, spoke, bg = _peace_field(shape, seed)
    g = _grain(shape, seed + 3, 0.6)
    # M = tie-dye background (varied, not flat); R = sign cutout (signs glossy);
    # CC = spoke lines + background tie-dye bands (orthogonal to M's value dist).
    M = 30 + 170 * bg * sm + 26 * (g - 0.5)
    R = 220 - 190 * sym                                   # peace signs go mirror-glossy
    CC = 16 + 170 * spoke + 70 * (0.5 + 0.5 * np.sin(bg * 6.0)) * (1 - sym)
    return _pack(M, R, CC)


# ===========================================================================
# 13. WARP OP — op-art moire: two rotated line gratings beating.
# ===========================================================================
def _op_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x0F) & 0xFFFFFFFF)
        a1 = rng.uniform(0, np.pi); a2 = a1 + rng.uniform(0.2, 0.6)
        per = max(6.0, 0.010 * np.hypot(wh, ww))
        warp = _noise((wh, ww), [40, 90], [0.6, 0.4], seed + 2) * 0.16
        u1 = (x * np.cos(a1) + y * np.sin(a1)) / per
        u2 = (x * np.cos(a2) + y * np.sin(a2)) / per
        g1 = 0.5 + 0.5 * np.sin(u1 * np.pi + warp * 6.0)
        g2 = 0.5 + 0.5 * np.sin(u2 * np.pi + warp * 6.0)
        moire = g1 * g2
        return (_resize_array(g1.astype(np.float32), h, w),
                _resize_array(g2.astype(np.float32), h, w),
                _resize_array(moire.astype(np.float32), h, w))

    return _cache(("op", h, w, int(seed)), build)


def paint_warp_op(paint, shape, mask, seed, pm, bb):
    g1, g2, moire = _op_fields(shape, seed)
    # bold op-art: a few crisp hues driven by the moire beat
    hue = (np.floor(moire * 5.0) / 5.0 + 0.55) % 1.0
    col = _hsv(hue, 0.7, np.clip(0.25 + 0.75 * moire, 0, 1))
    return _apply(paint, mask, col)


def spec_warp_op(shape, seed, sm, base_m, base_r):
    g1, g2, moire = _op_fields(shape, seed)
    M = 50 + 200 * g1 * sm                                # grating 1
    R = 30 + 200 * g2                                     # grating 2 (decorrelated)
    CC = 16 + 200 * moire                                 # beat peaks wet
    return _pack(M, R, CC)


# ===========================================================================
# 14. LIQUID LIGHT — liquid light-show oil projection (translucent caustic blobs).
# ===========================================================================
def _liquid_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        # SPB-105 / GV-LIQUID-I1/I2, 2026-08-28. Owner audit: the former
        # card read as flat cyan bands, not a 1960s liquid-light projector.
        # Legacy base lacks an M7 record; I2 direct native gate is 0.551 s
        # with M/R/Cc std 43.3/58.8/57.5 -> category M7 adapter pending.
        # Three warped dye baths
        # form dense 8–32px membranes; the rims are part of each puddle, not
        # unrelated sparkle/noise.
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        u=x/max(ww,1); v=y/max(wh,1)
        u=u+.032*np.sin(2*np.pi*(5*v+.7*u))+.017*np.sin(2*np.pi*(11*v-3*u))
        v=v+.028*np.sin(2*np.pi*(4*u-.5*v))+.014*np.sin(2*np.pi*(9*u+2*v))
        # SPB-105 / GV-LIQUID-I2, 2026-08-29 — the liquid-light projector
        # uses deliberately shaped dye baths and caustic rims.  I3's dense
        # all-over micro-wave experiment was rejected at catalog scale: the
        # owner needs fine organized substructure, never visual mush.
        bath_a=np.sin(2*np.pi*(12*u+1.7*np.sin(2*np.pi*4*v)))
        bath_b=np.sin(2*np.pi*(10*(.48*u+.88*v)+.8*np.sin(2*np.pi*3*u)))
        bath_c=np.sin(2*np.pi*(9*(-.86*u+.50*v)+.6*np.sin(2*np.pi*5*v)))
        liquid=_n01(.50*bath_a+.30*bath_b+.25*bath_c)
        blob=np.clip((liquid-.39)/.48,0,1)
        # Heat-trim threshold makes thin projected caustic rims with an
        # immediately adjacent translucent body rather than uniform stripes.
        edge=np.exp(-((liquid-.57)/.050)**2)
        boil=_n01(.58*bath_a-.24*bath_b+.18*bath_c)
        return (_resize_array(blob.astype(np.float32), h, w),
                _resize_array(edge.astype(np.float32), h, w),
                _resize_array(boil.astype(np.float32), h, w))

    return _cache(("liq", h, w, int(seed)), build)


def paint_liquid_light(paint, shape, mask, seed, pm, bb):
    blob, edge, boil = _liquid_fields(shape, seed)
    # Overhead projector dyes: a black-violet tray, with magenta, tangerine
    # and cyan baths that interpenetrate. HSV avoids the previous cyan clamp.
    # Dye wheels stay in the poster-projector gamut (violet → magenta →
    # orange) while the rim is a contrasting cyan projector flare.  I1's
    # full spectrum wrapped into an unintended night-vision green field.
    hue=(.82+.30*boil+.10*blob) % 1.0
    col=_hsv(hue, .88, .15+.70*blob)
    rim=_hsv(.52+.06*(1.0-boil), .62, .98)
    col=np.clip(col*(.60+.40*blob[:,:,None])+rim*edge[:,:,None]*.72,0,1)
    return _apply(paint, mask, col)


def spec_liquid_light(shape, seed, sm, base_m, base_r):
    blob, edge, boil = _liquid_fields(shape, seed)
    g = _grain(shape, seed + 21, 0.6)
    # M = boiling convection; R = blob body roughness (now full range, banded);
    # CC = caustic rims + boil shimmer (orthogonal). Widened so classes spread.
    M = 50 + 190 * boil * sm + 22 * (g - 0.5)
    R = 40 + 200 * (0.5 + 0.5 * np.sin(blob * 5.0))        # wet/matte plateaus
    CC = 16 + 210 * edge + 90 * boil
    return _pack(M, R, CC)


# ===========================================================================
# 15. GROOVY ZIGZAG — chevron / zigzag flame waves (triangle-wave bands).
# ===========================================================================
def _zig_fields(shape, seed):
    h, w = shape[:2]

    def build():
        wh, ww = _work_shape((h, w), 768)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x3C7) & 0xFFFFFFFF)
        th = rng.uniform(0, np.pi)
        u = (x * np.cos(th) + y * np.sin(th)).astype(np.float32)
        v = (-x * np.sin(th) + y * np.cos(th)).astype(np.float32)
        # SPB-105 / GV-ZIGZAG-I2 / 2026-08-29 — owner: whole-car carriers
        # were 25–65% too large and must be rebuilt from 8–32px primitives,
        # not merely scaled after the fact.  At 2048² this changes the native
        # zigzag period from ~102px to ~29px.  Historical M7 has no entry for
        # this renderer ID; post-rebake evidence is recorded in SPB_WIKI.
        per = max(6.0, 0.014 * min(wh, ww))
        # chevron: triangle wave whose phase shifts by a zigzag of v
        zig = np.abs(((v / (per * 1.2)) % 2.0) - 1.0)     # triangle in v
        tri = np.abs(((u / per + zig) % 2.0) - 1.0)       # triangle in u, sheared
        flame = _n01(tri)
        return (_resize_array(flame.astype(np.float32), h, w),
                _resize_array(zig.astype(np.float32), h, w),
                _resize_array(_n01(u + v).astype(np.float32), h, w))

    return _cache(("zig", h, w, int(seed)), build)


def paint_groovy_zigzag(paint, shape, mask, seed, pm, bb):
    flame, zig, diag = _zig_fields(shape, seed)
    hue = (flame * 0.5 + diag * 0.1) % 1.0
    col = _hsv(hue, 0.92, np.clip(0.55 + 0.45 * flame, 0, 1))
    g = _grain(shape, seed + 4)[:, :, None]
    col = np.clip(col * (0.96 + 0.08 * g), 0, 1)
    return _apply(paint, mask, col)


def spec_groovy_zigzag(shape, seed, sm, base_m, base_r):
    flame, zig, diag = _zig_fields(shape, seed)
    # M = chevron flame; R = zig shear; CC = diagonal run (3 orthogonal geometries)
    M = 50 + 190 * flame * sm
    R = 40 + 190 * zig                                     # chevron shear -> rough bands
    CC = 16 + 200 * (0.5 + 0.5 * np.sin(diag * 7.0 * np.pi))
    return _pack(M, R, CC)


# ===========================================================================
# 16. LAVA LAMP PURPLE — lava-lamp metaballs, purple/magenta.
# ===========================================================================
def _lava_field(shape, seed, n_blobs, squash):
    h, w = shape[:2]

    def build():
        work = 384
        yy, xx = np.mgrid[0:work, 0:work].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0xB10B) & 0xFFFFFFFF)
        field = np.zeros((work, work), np.float32)
        for _ in range(n_blobs):
            cy = rng.uniform(0, work); cx = rng.uniform(0, work)
            r = rng.uniform(40, 95)
            sq = rng.uniform(1.0, squash)
            dy = (yy - cy) * sq; dx = (xx - cx) / sq
            field += (r * r) / (dy * dy + dx * dx + r * r * 0.35)
        field = _n01(field)
        warp = _n01(multi_scale_noise((work, work), [24, 60], [0.6, 0.4], seed + 1))
        field = _resize_array(field, h, w)
        warp = _resize_array(warp, h, w)
        return field.astype(np.float32), warp.astype(np.float32)

    return _cache(("lava", h, w, int(seed), n_blobs, float(squash)), build)


def _lava_purple_fields(shape, seed):
    """A single illuminated wax column: named bulbs + fine convection skins."""
    h, w = shape[:2]

    def build():
        # SPB-105 / GV-LAVA-PURPLE-I1→I6, 2026-08-28. Owner doctrine calls for
        # dense 8–32px detail, but a lava lamp also needs a few readable wax
        # bodies. These are wax bodies first; the small ripple/edge features
        # are physical convection skins, never confetti or generic grain.
        # Native 2048: 0.742 s; spec std M/R/Cc 24.2/42.5/27.8 (the legacy
        # base still has no per-ID M7 adapter, so direct evidence is logged).
        wh, ww = _work_shape((h, w), 896)
        y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
        u=x/max(ww-1,1); v=y/max(wh-1,1)
        # Gentle convection deforms every parcel before it is evaluated: no
        # stamped-circle grid or repeated wallpaper silhouette.
        u=u+.034*np.sin(2*np.pi*(1.3*v+.23*np.sin(3.7*u)))
        v=v+.027*np.sin(2*np.pi*(1.1*u-.19*np.sin(4.1*v)))
        phase=((int(seed) * 0.61803398875) % 1.0) - .5
        # A full-car composition, not six isolated dots: individual wax
        # parcels overlap into rising/descending columns with dark liquid
        # still visible between them.
        bulbs=((.10+.018*phase,.10,.18,.15), (.37-.014*phase,.11,.14,.18),
               (.70+.020*phase,.12,.20,.15), (.23-.016*phase,.35,.18,.21),
               (.57+.014*phase,.38,.23,.20), (.87-.018*phase,.41,.16,.19),
               (.12+.011*phase,.65,.19,.18), (.43-.014*phase,.68,.17,.23),
               (.75+.016*phase,.72,.22,.21), (.45-.009*phase,.93,.23,.11))
        nearest=np.full((wh,ww), 9.0, np.float32)
        density=np.zeros((wh,ww), np.float32)
        for cx,cy,rx,ry in bulbs:
            d=np.sqrt(((u-cx)/rx)**2+((v-cy)/ry)**2)
            nearest=np.minimum(nearest,d)
            density+=np.exp(-1.05*d*d)
        wax=np.clip((density-.23)/.67,0,1)
        edge=np.exp(-((nearest-.92)/.013)**2)*wax
        # 8–32px convection skins lie within the wax, but never outline it
        # as a literal repeated ring. They are deliberately sparse accents.
        fold=.5+.5*np.sin(2*np.pi*(4.4*u+6.2*v+.31*np.sin(9*u-5*v)))
        convection=.5+.5*np.sin(2*np.pi*(3.2*u+7.4*v+.18*np.sin(12*u)))
        skin=np.power(fold,42.0)*wax*(.12+.26*convection)
        fields=(wax.astype(np.float32), edge.astype(np.float32),
                skin.astype(np.float32), convection.astype(np.float32))
        return tuple(_resize_array(z,h,w).astype(np.float32) for z in fields)

    return _cache(("lava-purple-i1", h, w, int(seed)), build)


def paint_lava_lamp_purple(paint, shape, mask, seed, pm, bb):
    wax, edge, skin, convection = _lava_purple_fields(shape, seed)
    # An illuminated plum column: dyed violet wax, hot-magenta rise, and
    # narrow electric skins against a deep aubergine reservoir.
    bg=_hsv(.72,.62,.18)
    # Color follows each wax parcel's depth; convection is a restrained tint
    # shift, never a stripe field painted over the whole surface.
    dye=_hsv(.80+.028*convection+.035*skin,.82,.36+.52*wax)
    pearl=_hsv(.98-.06*convection,.28,.86+.14*edge)
    col=bg*(1-wax[:,:,None])+dye*wax[:,:,None]
    col=np.clip(col+pearl*(.18*edge+.045*skin)[:,:,None],0,1)
    return _apply(paint, mask, col)


def spec_lava_lamp_purple(shape, seed, sm, base_m, base_r):
    wax, edge, skin, convection = _lava_purple_fields(shape, seed)
    # Same wax anatomy, with four actual states per body: reservoir, wax,
    # hot core, and polished skin. Direct native screen precedes live wiring.
    M = 30 + 190*(.36*wax+.46*edge+.18*skin)*sm
    R = 214 - 178*(.72*wax+.18*edge+.10*convection)
    CC = 16 + 225*np.clip(.35*wax+.42*edge+.23*skin,0,1)
    return _pack(M, R, CC)


# ===========================================================================
# 17. LAVA LAMP GROOVY — lava-lamp metaballs, earthy orange/teal (diff dynamics).
# ===========================================================================
def paint_lava_lamp_groovy(paint, shape, mask, seed, pm, bb):
    field, warp = _lava_field(shape, seed + 50, 5, 3.0)    # fewer, taller blobs
    t = np.clip(field, 0, 1)
    # teal background, earthy amber/orange blobs (Woodstock palette)
    H = np.where(t > 0.5, 1.4 - 0.7 * t, 3.4 + 0.6 * warp)
    col = _oklch(0.42 + 0.40 * t, 0.11 + 0.07 * t, H)
    return _apply(paint, mask, col)


def spec_lava_lamp_groovy(shape, seed, sm, base_m, base_r):
    field, warp = _lava_field(shape, seed + 50, 5, 3.0)
    fine = _noise(shape, [8, 18], [0.6, 0.4], seed + 71)   # fine streaming dither
    g = _grain(shape, seed + 17, 0.6)
    t = np.clip(field, 0, 1)                               # the blob motif the paint shows
    # CC RIDES THE BLOB FIELD MONOTONICALLY: hot amber blob cores read as wet,
    # angle-gated clearcoat glint on the EXACT pixels the paint lights up; teal
    # background stays low/matte. This is the traced "holy shit" reveal (sibling
    # spec_lava_lamp_purple traces the same field on R — here it's CC, so the
    # two finishes stay distinct). The OTHER two channels carry their own
    # geometry (warp convection / fine streaming) for hue spread + decorrelation.
    CC = 16 + 218 * (t ** 1.3)                             # monotone in field -> traced
    M = 44 + 188 * (0.5 + 0.5 * np.sin(warp * 5.0 + g * 5.0)) * sm + 20 * (g - 0.5)
    R = 200 - 150 * (0.5 + 0.5 * np.cos(fine * 7.5 + warp * 2.0))  # diff freq/phase
    return _pack(M, R, CC)


# ===========================================================================
# 18. MUSHROOM FADE — gilled mushroom-cap fans + spore speckle (earthy).
# ===========================================================================
def _shroom_fields(shape, seed):
    h, w = shape[:2]

    def build():
        work = 416
        yy, xx = np.mgrid[0:work, 0:work].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x5417) & 0xFFFFFFFF)
        gills = np.zeros((work, work), np.float32)
        caps = np.zeros((work, work), np.float32)
        for _ in range(14):
            cy = rng.uniform(0, work); cx = rng.uniform(0, work)
            r = rng.uniform(35, 80); rot = rng.uniform(0, 2 * np.pi)
            ng = int(rng.integers(18, 30))
            dy = yy - cy; dx = xx - cx
            dist = np.sqrt(dy * dy + dx * dx)
            a = np.arctan2(dy, dx) - rot
            cap = (dist < r).astype(np.float32) * (dy < 0.15 * r).astype(np.float32)  # dome
            g = 0.5 + 0.5 * np.cos(a * ng)                # radial gills under the cap
            gunder = g * (dist < r * 0.95).astype(np.float32) * (dy >= 0).astype(np.float32)
            caps = np.maximum(caps, cap * np.clip(1 - dist / r, 0, 1))
            gills = np.maximum(gills, gunder)
        spore = (rng.random((work, work)) > 0.985).astype(np.float32)
        spore = _blur(spore, 0.6)
        caps = _resize_array(caps, h, w)
        gills = _resize_array(gills, h, w)
        spore = _resize_array(spore, h, w)
        soil = _n01(_noise((h, w), [24, 60, 120], [0.4, 0.35, 0.25], seed + 1))
        return caps.astype(np.float32), gills.astype(np.float32), spore.astype(np.float32), soil.astype(np.float32)

    return _cache(("shroom", h, w, int(seed)), build)


def paint_mushroom_fade(paint, shape, mask, seed, pm, bb):
    caps, gills, spore, soil = _shroom_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)                      # composite at work-res
    if (wh, ww) != (h, w):
        caps = _resize_array(np.ascontiguousarray(caps), wh, ww)
        gills = _resize_array(np.ascontiguousarray(gills), wh, ww)
        spore = _resize_array(np.ascontiguousarray(spore), wh, ww)
        soil = _resize_array(np.ascontiguousarray(soil), wh, ww)
    # earthy forest floor: browns/ochres soil, ruddy caps, pale gills
    H = (1.0 + 0.6 * soil)                                  # browns/ambers
    col = _oklch(0.42 + 0.22 * soil, 0.07 + 0.04 * soil, H)
    cap_col = _oklch(0.5, 0.13, np.float32(0.7))            # rusty-red cap
    pale = np.float32([0.93, 0.88, 0.78])                   # bone gills
    col = col * (1 - caps[:, :, None]) + cap_col * caps[:, :, None]
    col = col * (1 - gills[:, :, None] * 0.8) + pale * (gills[:, :, None] * 0.8)
    col = np.clip(col + spore[:, :, None] * 0.25, 0, 1)
    col = _resize_rgb(col, h, w)
    return _apply(paint, mask, col)


def spec_mushroom_fade(shape, seed, sm, base_m, base_r):
    caps, gills, spore, soil = _shroom_fields(shape, seed)
    # M = micaceous soil + spore glints (wide range); R = gill ridges + dry soil
    # patches; CC = damp cap tops + soil moisture bands (orthogonal value dist).
    M = 20 + 230 * soil * sm + 80 * spore
    R = 50 + 170 * gills + 110 * (1 - soil)               # dry soil patches matte (wide)
    CC = 16 + 180 * caps + 150 * (0.5 + 0.5 * np.sin(soil * 7.0)) * (1 - caps)
    return _pack(M, R, CC)


# ===========================================================================
# 19. NEON ACID BLOB — reaction-diffusion neon bloom.
# ===========================================================================
def _rd_fields(shape, seed):
    """Cheap Gray-Scott reaction-diffusion at low res -> organic neon blobs."""
    h, w = shape[:2]

    def build():
        N = 132
        rng = np.random.default_rng((int(seed) ^ 0xD1FF) & 0xFFFFFFFF)
        U = np.ones((N, N), np.float32)
        V = np.zeros((N, N), np.float32)
        for _ in range(20):
            yy = rng.integers(0, N); xx = rng.integers(0, N)
            V[max(0, yy - 4):yy + 4, max(0, xx - 4):xx + 4] = 1.0
        Du, Dv, F, k = 0.16, 0.08, 0.060, 0.062
        for _ in range(1000):
            lapU = (np.roll(U, 1, 0) + np.roll(U, -1, 0) + np.roll(U, 1, 1) + np.roll(U, -1, 1) - 4 * U)
            lapV = (np.roll(V, 1, 0) + np.roll(V, -1, 0) + np.roll(V, 1, 1) + np.roll(V, -1, 1) - 4 * V)
            uvv = U * V * V
            U += (Du * lapU - uvv + F * (1 - U))
            V += (Dv * lapV + uvv - (F + k) * V)
        V = _n01(V)
        edge = _n01(np.abs(np.gradient(V, axis=0)) + np.abs(np.gradient(V, axis=1)))
        V = _resize_array(V, h, w)
        edge = _resize_array(edge, h, w)
        return V.astype(np.float32), edge.astype(np.float32)

    return _cache(("rd", h, w, int(seed)), build)


def paint_neon_acid_blob(paint, shape, mask, seed, pm, bb):
    V, edge = _rd_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)                      # composite at work-res
    if (wh, ww) != (h, w):
        V = _resize_array(np.ascontiguousarray(V), wh, ww)
        edge = _resize_array(np.ascontiguousarray(edge), wh, ww)
    # electric neon: dark field, hot cyan/lime/magenta blob membranes
    H = (3.0 + 3.0 * V)
    col = _oklch(0.30 + 0.55 * V, 0.12 + 0.10 * V, H)
    col = np.clip(col + edge[:, :, None] * 0.5, 0, 1)       # glowing membrane rims
    col = _resize_rgb(col, h, w)
    return _apply(paint, mask, col)


def spec_neon_acid_blob(shape, seed, sm, base_m, base_r):
    V, edge = _rd_fields(shape, seed)
    g = _grain(shape, seed + 19, 0.6)
    # M = blob mass; R = membrane edges (thin geometry, decorrelated from V);
    # CC = banded interference of V — three different value distributions.
    M = 60 + 180 * V * sm + 22 * (g - 0.5)
    R = 50 + 190 * edge                                     # membrane rims roughen
    CC = 16 + 200 * (0.5 + 0.5 * np.sin(V * 8.0))
    return _pack(M, R, CC)


# ===========================================================================
# 20. FLOWER POWER — daisy meadow, scattered rotated petal rosettes.
# ===========================================================================
def _flower_fields(shape, seed):
    h, w = shape[:2]

    def build():
        # SPB-105 / GV-FLOWER-I1, 2026-08-29. Owner eye rejected sparse
        # multicolour star/confetti. This is a packed, limited-palette 60s
        # daisy print: clear individual petals, real centres, and enough
        # coverage to carry a whole car without one generic wallpaper field.
        wh, ww = _work_shape((h, w), 768)
        rng = np.random.default_rng((int(seed) ^ 0xF10E) & 0xFFFFFFFF)
        petals = np.zeros((wh, ww), np.float32)
        centers = np.zeros((wh, ww), np.float32)
        flhue = np.zeros((wh, ww), np.float32)
        palette=np.array([.00,.075,.145,.84,.56],np.float32)  # coral/gold/pink/teal
        # A jittered field avoids the old empty lawn, but the 60s print is
        # intentionally composed rather than random-sprinkled.
        for gy in range(5):
            for gx in range(5):
                if rng.random() < .04:
                    continue
                cx=(gx+.52+rng.uniform(-.16,.16))*ww/5
                cy=(gy+.50+rng.uniform(-.16,.16))*wh/5
                r=rng.uniform(.115,.170)*min(wh,ww)
                rot=rng.uniform(0,2*np.pi); n_petals=int(rng.choice([5,6,7]))
                hh=float(palette[int(rng.integers(0,len(palette)))]+rng.uniform(-.012,.012))
                # Windowed individual ellipses make literal petals—never the
                # single star-like radial primitive that caused the confetti read.
                R=int(r*1.18)+3
                y0 = max(0, int(cy) - R); y1 = min(wh, int(cy) + R)
                x0 = max(0, int(cx) - R); x1 = min(ww, int(cx) + R)
                if y1 <= y0 or x1 <= x0:
                    continue
                ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                dy = ly - cy; dx = lx - cx
                dist = np.sqrt(dy * dy + dx * dx)
                pet=np.zeros_like(dist,np.float32)
                for k in range(n_petals):
                    a=rot+2*np.pi*k/n_petals
                    px=np.cos(a)*r*.38; py=np.sin(a)*r*.38
                    ca=np.cos(a); sa=np.sin(a)
                    along=(dx-px)*ca+(dy-py)*sa
                    across=-(dx-px)*sa+(dy-py)*ca
                    d=np.sqrt((along/(r*.53))**2+(across/(r*.25))**2)
                    pet=np.maximum(pet,np.clip(1-d,0,1))
                ctr=np.clip(1.0-dist/(r*.27),0,1)
                psub = petals[y0:y1, x0:x1]
                np.maximum(psub, pet, out=psub)
                csub = centers[y0:y1, x0:x1]
                np.maximum(csub, ctr, out=csub)
                hsub = flhue[y0:y1, x0:x1]
                hsub[pet > 0.01] = hh                      # this flower's hue
        meadow=_n01(multi_scale_noise((wh, ww), [26, 58], [.65,.35], seed+1))
        petals = _resize_array(petals, h, w)
        centers = _resize_array(centers, h, w)
        flhue = _resize_array(flhue, h, w)
        meadow = _resize_array(meadow, h, w)
        return petals.astype(np.float32), centers.astype(np.float32), flhue.astype(np.float32), meadow.astype(np.float32)

    return _cache(("flow", h, w, int(seed)), build)


def paint_flower_power(paint, shape, mask, seed, pm, bb):
    petals, centers, flhue, meadow = _flower_fields(shape, seed)
    h, w = shape[:2]
    wh, ww = _work_shape((h, w), 1024)                      # composite at work-res
    if (wh, ww) != (h, w):
        petals = _resize_array(np.ascontiguousarray(petals), wh, ww)
        centers = _resize_array(np.ascontiguousarray(centers), wh, ww)
        flhue = _resize_array(np.ascontiguousarray(flhue), wh, ww)
        meadow = _resize_array(np.ascontiguousarray(meadow), wh, ww)
    # green/turquoise meadow, multicolor daisies w/ golden centres
    bg = _oklch(0.55, 0.10, np.float32(2.5 + 0.7 * meadow))
    pet_col = _hsv(flhue, 0.85, 0.97)
    ctr_col = np.float32([1.0, 0.82, 0.12])
    col = bg * (1 - petals[:, :, None]) + pet_col * petals[:, :, None]
    col = col * (1 - centers[:, :, None]) + ctr_col * centers[:, :, None]
    col = _resize_rgb(np.clip(col, 0, 1), h, w)
    return _apply(paint, mask, col)


def spec_flower_power(shape, seed, sm, base_m, base_r):
    petals, centers, flhue, meadow = _flower_fields(shape, seed)
    # SPB-105 / GV-FLOWER-I3. Every flower gets a material state from its
    # own printed hue: golden centres flash, warm petals polish differently
    # from cool petals, and the teal field remains a quieter ink ground.
    # No generic grass/grain is injected into a graphic flower print.
    petal_tint=.36+.64*(.5+.5*np.sin(6.28*(flhue+.13)))
    M = 28 + 202*centers*sm + 114*petals*petal_tint*sm + 38*meadow*(1-petals)
    R = 220 - 165*petals*(.44+.56*petal_tint) - 125*centers + 22*meadow*(1-petals)
    CC = 16 + 206*petals*(.30+.70*petal_tint) + 32*centers
    return _pack(M, R, CC)
