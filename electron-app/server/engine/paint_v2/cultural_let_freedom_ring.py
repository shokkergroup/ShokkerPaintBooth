# ============================================================================
# engine/paint_v2/cultural_let_freedom_ring.py
# Cultural / LET FREEDOM RING - 10 fully-procedural patriotic monolithics.
#
# ZERO image plates: every finish builds its paint AND its decorrelated spec in
# code, so it renders for every buyer with no downloads. UV-orientation-agnostic
# by design (scattered / radial / omnidirectional / per-region-varied motifs --
# NO upright flags, NO 13-parallel-stripes, NO centered emblems).
#
# CONTRACT (engine/registry.py):
#   MONOLITHIC_REGISTRY[id] = (spec_fn, paint_fn)
#   paint_fn(paint, shape, mask, seed, pm, bb) -> float32 HxWx3/4 in [0,1]
#   spec_fn(shape, mask, seed, sm)            -> uint8  HxWx4 (M,R,Cc,A)
# Floors: R>=15, Cc>=16. Outside-mask: M~4, R~120, Cc~80 (cultural convention).
#
# 2-copy file (root is source of truth; mirrored to electron-app/server via
# scripts/sync-runtime-copies.js -- listed in runtime-sync-manifest.json).
# ============================================================================
from __future__ import annotations

import hashlib
from functools import lru_cache

import cv2
import numpy as np

from engine.core import multi_scale_noise

# ---------------------------------------------------------------------------
# SHARED HELPERS (one block, reused by all 10 -- but each finish owns its
# primary geometry function below; helpers only do plumbing + spec packing).
# ---------------------------------------------------------------------------
_WORK_CAP = 1024  # engine work-grid cap (owner: speed is king); upscale to canvas after.


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _seed_of(finish_id, seed):
    base = int.from_bytes(hashlib.blake2s(finish_id.encode("utf-8"), digest_size=4).digest(), "big")
    return (base ^ (int(seed) & 0x7FFFFFFF)) & 0x7FFFFFFF


def _work_shape(shape):
    h, w = _shape2(shape)
    m = max(h, w)
    if m <= _WORK_CAP:
        return int(h), int(w), 1.0
    s = _WORK_CAP / float(m)
    return max(64, int(round(h * s))), max(64, int(round(w * s))), s


def _mask2(mask, h, w):
    if mask is None:
        return np.ones((h, w), np.float32)
    if np.isscalar(mask) or (hasattr(mask, "ndim") and getattr(mask, "ndim", 1) == 0):
        return np.full((h, w), float(mask), np.float32)
    a = np.asarray(mask, np.float32)
    if a.ndim == 3:
        a = a[:, :, 0]
    if a.shape != (h, w):
        a = cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def _msc(h, w, scales, seed):
    """multi_scale_noise normalised to 0..1."""
    wts = [0.5, 0.3, 0.2][: len(scales)]
    n = multi_scale_noise((h, w), list(scales), wts, int(seed) & 0x7FFFFFFF)
    return ((np.asarray(n, np.float32) + 1.0) * 0.5).astype(np.float32)


@lru_cache(maxsize=8)
def _coords(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yn = yy / max(h - 1, 1)
    xn = xx / max(w - 1, 1)
    return yy, xx, yn, xn


def _edge(field, gain=6.0):
    dx = np.abs(np.diff(field, axis=1, prepend=field[:, :1]))
    dy = np.abs(np.diff(field, axis=0, prepend=field[:1, :]))
    return np.clip(np.sqrt(dx * dx + dy * dy) * gain, 0.0, 1.0).astype(np.float32)


def _scatter_field(h, w, seed, count, value_fn, support=2.0):
    """Seeded omnidirectional point scatter -> accumulation field via
    value_fn(acc, yy, xx, cy, cx, rad, ang, amp).

    PERF (owner doctrine: ~1s per finish, >3s unacceptable): each splat is
    computed ONLY inside its local bounding window (support * rad margin),
    not over the full grid — identical output (every motif's footprint is
    bounded by ~1.8*rad; gaussian tails beyond 2*rad are < 1e-7), but 50-500x
    less math at the 1024 work grid. RNG draw order is unchanged.
    """
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    acc = np.zeros((h, w), np.float32)
    yy, xx, _, _ = _coords(h, w)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        rad = rng.uniform(0.010, 0.034) * max(h, w)
        ang = rng.uniform(0.0, 2.0 * np.pi)
        amp = rng.uniform(0.55, 1.0)
        r = support * rad + 2.0
        y0, y1 = max(0, int(cy - r)), min(h, int(cy + r) + 1)
        x0, x1 = max(0, int(cx - r)), min(w, int(cx + r) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        value_fn(acc[y0:y1, x0:x1], yy[y0:y1, x0:x1], xx[y0:y1, x0:x1], cy, cx, rad, ang, amp)
    return acc


def _upscale(arr, h, w):
    if arr.shape[:2] == (h, w):
        return arr
    return cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR)


def _pack_spec(M, R, Cc, mask_full, sm, h, w):
    """Assemble + clamp + apply sm + outside-mask convention. Inputs full-res HxW."""
    outside = 1.0 - mask_full
    out = np.empty((h, w, 4), np.float32)
    out[:, :, 0] = np.clip(np.clip(M, 0, 255) * float(sm) * mask_full + 4.0 * outside, 0, 255)
    out[:, :, 1] = np.clip(np.clip(R, 15, 255) * mask_full + 120.0 * outside, 15, 255)
    out[:, :, 2] = np.clip(np.clip(Cc, 16, 255) * mask_full + 80.0 * outside, 16, 255)
    out[:, :, 3] = 255
    return out.astype(np.uint8)


def _blend_paint(paint, effect, mask_full, pm):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    m3 = mask_full[:, :, None]
    s = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * s) + effect[:, :, :3] * (m3 * s)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


# ---------------------------------------------------------------------------
# Shared LUT-evaluated oklch_ramp (render-time doctrine): the per-finish IGNITION
# helpers _ign_torch_ramp / _ign_eagle_ramp / _ign_wtp_ramp already proved a
# 257-entry LUT + linear interp is visually identical to a full-grid OKLab
# convert while skipping the expensive per-pixel oklab_to_srgb chain. This is
# the same technique exposed once for the remaining direct oklch_ramp callers
# (gated SSIM>=0.999, max-abs-delta<=2/255 vs the exact ramp — see _NIGHTLY).
# ---------------------------------------------------------------------------
@lru_cache(maxsize=64)
def _ramp_lut(stops_key, flatten):
    from engine.color_science import oklch_ramp
    ts = np.linspace(0.0, 1.0, 257, dtype=np.float32)
    return oklch_ramp([list(s) for s in stops_key], ts,
                      flatten_lightness=flatten).astype(np.float32)


def _ramp(stops, t, flatten_lightness=0.0):
    """LUT-evaluated oklch_ramp (visually identical; skips full-grid OKLab)."""
    key = tuple(tuple(float(c) for c in s) for s in stops)
    lut = _ramp_lut(key, float(flatten_lightness))
    x = np.clip(np.asarray(t, np.float32), 0.0, 1.0) * np.float32(256)
    i0 = np.minimum(x.astype(np.int32), 255)
    f = (x - i0.astype(np.float32))[..., None]
    return (lut[i0] * (1.0 - f) + lut[i0 + 1] * f).astype(np.float32)


# Palette anchors (sRGB 0..1) reused across the pack.
_NAVY = np.array([0.043, 0.067, 0.196], np.float32)
_RED = np.array([0.706, 0.075, 0.137], np.float32)
_WHITE = np.array([0.945, 0.945, 0.961], np.float32)
_GOLD = np.array([0.831, 0.659, 0.220], np.float32)
_STEEL = np.array([0.215, 0.235, 0.270], np.float32)
_AMBER = np.array([0.808, 0.557, 0.165], np.float32)


def _star_splat(acc, yy, xx, cy, cx, rad, ang, amp):
    """5-point star intensity splat, rotated by ang (UV-agnostic)."""
    dy = yy - cy
    dx = xx - cx
    r = np.sqrt(dy * dy + dx * dx) + 1e-6
    th = np.arctan2(dy, dx) - ang
    # 5-point star radial profile: petals via cos(5*theta)
    petal = 0.55 + 0.45 * np.cos(5.0 * th)
    edge_r = rad * petal
    local = np.clip(1.0 - r / edge_r, 0.0, 1.0)
    # tight falloff -> crisp little stars
    np.maximum(acc, (local ** 1.6) * amp, out=acc)


# ============================================================================
# 1) OLD GLORY FLUX
# ============================================================================
FID_1 = "lfr_old_glory_flux"


def _flux_fields(h, w, seed):
    stars = _scatter_field(h, w, seed ^ 0x51A1, count=520, value_fn=_star_splat)
    flake = _msc(h, w, [2, 4, 8], seed ^ 0xA1)
    macro = _msc(h, w, [40, 90, 180], seed ^ 0xB2)          # roughness source
    yy, xx, yn, xn = _coords(h, w)
    iso = _msc(h, w, [22, 55, 120], seed ^ 0xC3)
    travel = 0.5 + 0.5 * np.sin(iso * 6.2831 + (xn + yn) * 3.1)  # tri-band hue carrier
    return stars, flake, macro, travel


def _spec_lfr_old_glory_flux(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_1, seed)
    stars, flake, macro, travel = _flux_fields(h, w, s)
    star_m = stars * (0.45 + 0.55 * flake)
    M = 30.0 + star_m * 210.0 + flake * 26.0
    R = 150.0 - macro * 120.0 - star_m * 40.0          # anti-aligned to M
    Cc = 34.0 + travel * 150.0 + star_m * 30.0          # independent carrier
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_old_glory_flux(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_1, seed)
    stars, flake, _macro, travel = _flux_fields(h, w, s)
    rng = np.random.default_rng(s ^ 0xBEEF)
    star_is_white = (cv2.resize((rng.random((max(8, h // 24), max(8, w // 24))) > 0.5).astype(np.float32),
                                (w, h), interpolation=cv2.INTER_NEAREST))
    base = np.broadcast_to(_NAVY, (h, w, 3)).copy()
    # subtle hue-travel tint stays mostly in spec; tiny albedo nudge for life
    base += (travel[:, :, None] - 0.5) * np.array([0.05, 0.0, 0.06], np.float32)
    star_col = _WHITE * star_is_white[:, :, None] + _RED * (1.0 - star_is_white[:, :, None])
    sm_mask = np.clip(stars * (0.6 + 0.4 * flake), 0.0, 1.0)[:, :, None]
    eff = np.clip(base * (1.0 - sm_mask) + star_col * sm_mask, 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 2) ROCKETS RED GLARE  (radial firework bloom, hidden-flare living finish)
# ============================================================================
FID_2 = "lfr_rockets_red_glare"


def _burst_fields(h, w, seed):
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    rings = np.zeros((h, w), np.float32)
    spokes = np.zeros((h, w), np.float32)
    halo = np.zeros((h, w), np.float32)
    n = rng.integers(6, 10)
    for _ in range(int(n)):
        cy = rng.uniform(0.05, 0.95) * h
        cx = rng.uniform(0.05, 0.95) * w
        dy = yy - cy
        dx = xx - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        reach = rng.uniform(0.18, 0.34) * max(h, w)
        decay = np.exp(-r / reach)
        period = rng.uniform(reach / 9.0, reach / 5.0)
        ring = np.clip(np.cos(r / period * 6.2831 + rng.uniform(0, 6.28)) * decay, 0.0, 1.0)
        nspk = int(rng.integers(18, 34))
        spoke = np.clip(np.cos(th * nspk + rng.uniform(0, 6.28)) ** 8, 0.0, 1.0) * decay
        rings = np.maximum(rings, ring)
        spokes = np.maximum(spokes, spoke)
        halo = halo + np.exp(-(r / (reach * 1.5)) ** 2) * 0.6
    halo = np.clip(halo, 0.0, 1.0)
    return rings, spokes, halo


def _spec_lfr_rockets_red_glare(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_2, seed)
    rings, spokes, halo = _burst_fields(h, w, s)
    grit = _msc(h, w, [3, 6, 12], s ^ 0x44)
    # Decorrelated channels: each owns ONE burst geometry (spokes / rings / halo)
    # plus its own micro field — never the same composite re-scaled.
    grit_r = _msc(h, w, [5, 11, 23], s ^ 0x45)
    glow_c = _msc(h, w, [34, 76], s ^ 0x46)
    M = 22.0 + spokes * 215.0 + grit * 22.0               # hidden-flare chrome spark spokes
    R = 170.0 - rings * 115.0 + (grit_r - 0.5) * 44.0     # shock-ring crests glossy, own grain
    Cc = 30.0 + halo * 120.0 + glow_c * 46.0              # soft glow corona on its own field
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_rockets_red_glare(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_2, seed)
    rings, spokes, halo = _burst_fields(h, w, s)
    night = np.broadcast_to(np.array([0.020, 0.027, 0.063], np.float32), (h, w, 3)).copy()
    glow = np.clip(rings * 0.9 + spokes * 0.8, 0.0, 1.0)[:, :, None]
    # red core -> gold tips; albedo identical for spark regardless of spec flare
    col = _RED * glow + _GOLD * np.clip(spokes[:, :, None] - rings[:, :, None] * 0.5, 0.0, 1.0)
    eff = np.clip(night + col * 0.95 + halo[:, :, None] * np.array([0.06, 0.02, 0.10], np.float32), 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 3) LIBERTY TORCH  (omnidirectional domain-warped flame field)
# ============================================================================
FID_3 = "lfr_liberty_torch"


def _flame_fields(h, w, seed):
    # curl-like warp from two perpendicular noises (no global flow direction)
    wx = (_msc(h, w, [60, 130], seed ^ 0x01) - 0.5) * 2.0
    wy = (_msc(h, w, [70, 150], seed ^ 0x02) - 0.5) * 2.0
    yy, xx, _, _ = _coords(h, w)
    amp = 0.06 * max(h, w)
    sx = np.clip(xx + wx * amp, 0, w - 1).astype(np.float32)
    sy = np.clip(yy + wy * amp, 0, h - 1).astype(np.float32)
    base = _msc(h, w, [10, 22, 46], seed ^ 0x71)
    flame = cv2.remap(base, sx, sy, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    flame = np.clip((flame - 0.42) / 0.5, 0.0, 1.0)        # threshold into tongues
    tip = np.clip((flame - 0.6) * 2.5, 0.0, 1.0)
    return flame, tip


def _spec_lfr_liberty_torch(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_3, seed)
    flame, tip = _flame_fields(h, w, s)
    ember = _msc(h, w, [18, 40, 85], s ^ 0x82)
    haze = _msc(h, w, [50, 110], s ^ 0x93)
    M = 26.0 + tip * 200.0 + flame * 40.0
    R = 165.0 - tip * 95.0 - ember * 35.0                 # different source than M
    Cc = 30.0 + (0.5 + 0.5 * np.sin(haze * 6.2831 + 1.3)) * 120.0 * (1.0 - tip) + tip * 50.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_liberty_torch(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_3, seed)
    flame, tip = _flame_fields(h, w, s)
    ember_black = np.array([0.067, 0.024, 0.012], np.float32)
    base = np.broadcast_to(ember_black, (h, w, 3)).copy()
    # red roots -> orange mid -> gold tips
    col = _RED * np.clip(flame - tip, 0.0, 1.0)[:, :, None]
    col = col + _AMBER * (flame * 0.5)[:, :, None]
    col = col + _GOLD * tip[:, :, None]
    eff = np.clip(base + col, 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 4) EAGLE ASCENDANT  (omnidirectional feather brocade / damask)
# ============================================================================
FID_4 = "lfr_eagle_ascendant"


def _feather_splat(acc, yy, xx, cy, cx, rad, ang, amp):
    dy = yy - cy
    dx = xx - cx
    # rotate into motif frame
    ca, sa = np.cos(-ang), np.sin(-ang)
    u = dx * ca - dy * sa
    v = dx * sa + dy * ca
    # feather = tapered shaft (v small) with barb chevrons along u
    shaft = np.exp(-(v / (rad * 0.18)) ** 2) * np.clip(1.0 - np.abs(u) / rad, 0.0, 1.0)
    barbs = np.clip(np.cos(u / (rad * 0.16)) , 0.0, 1.0) * np.exp(-(v / (rad * 0.5)) ** 2)
    barbs = barbs * np.clip(1.0 - np.abs(u) / rad, 0.0, 1.0)
    motif = np.clip(shaft * 0.9 + barbs * 0.6, 0.0, 1.0) * amp
    np.maximum(acc, motif, out=acc)


def _brocade_fields(h, w, seed):
    feathers = _scatter_field(h, w, seed ^ 0xE10, count=240, value_fn=_feather_splat)
    feathers = np.clip(feathers * 1.15, 0.0, 1.0)
    line = _edge(feathers, gain=7.0)
    return feathers, line


def _spec_lfr_eagle_ascendant(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_4, seed)
    feathers, line = _brocade_fields(h, w, s)
    gild = np.clip(feathers * 0.7 + line * 0.9, 0.0, 1.0)
    weave = _msc(h, w, [6, 13, 27], s ^ 0xE2)
    bloom = _msc(h, w, [45, 100], s ^ 0xE3)
    M = 28.0 + gild * 215.0
    R = 150.0 - weave * 110.0 - gild * 35.0               # weave geometry != feather
    Cc = 32.0 + (0.5 + 0.5 * np.sin(bloom * 6.2831 + 0.7)) * 130.0 * (1.0 - gild) + gild * 40.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_eagle_ascendant(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_4, seed)
    feathers, line = _brocade_fields(h, w, s)
    base = np.broadcast_to(_NAVY, (h, w, 3)).copy()
    gild = np.clip(feathers * 0.6 + line * 1.0, 0.0, 1.0)[:, :, None]
    eff = np.clip(base * (1.0 - gild * 0.85) + _GOLD * gild, 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 5) WE THE PEOPLE  (engraved guilloche on parchment, matte document)
# ============================================================================
FID_5 = "lfr_we_the_people"


def _guilloche_fields(h, w, seed):
    _, _, yn, xn = _coords(h, w)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    eng = np.zeros((h, w), np.float32)
    for _ in range(5):
        ang = rng.uniform(0, np.pi)
        ca, sa = np.cos(ang), np.sin(ang)
        u = xn * ca + yn * sa
        v = -xn * sa + yn * ca
        f1 = rng.uniform(34.0, 70.0)
        f2 = rng.uniform(26.0, 58.0)
        eng += np.sin(u * f1 + np.sin(v * f2) * 2.6 + rng.uniform(0, 6.28))
    eng = 0.5 + 0.5 * np.sin(eng * 1.1)                    # interwoven lace
    line = np.clip(np.abs(eng - 0.5) * 2.0, 0.0, 1.0)      # the ink lines
    line = 1.0 - line                                     # 1 on lines
    line = np.clip((line - 0.55) * 3.0, 0.0, 1.0)
    depth = _edge(eng, gain=5.0)
    return line, depth


def _spec_lfr_we_the_people(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_5, seed)
    line, depth = _guilloche_fields(h, w, s)
    fiber = _msc(h, w, [4, 9, 19], s ^ 0x33)
    # Decorrelated channels: line and depth share the guilloche geometry, so they
    # may not drive two channels. M keeps the ink; R rides an independent paper
    # blotch; Cc rides fiber + an independent aging stain.
    blotch = _msc(h, w, [14, 31, 67], s ^ 0x34)
    stain = _msc(h, w, [48, 104], s ^ 0x35)
    M = 14.0 + line * 26.0 + fiber * 8.0                  # matte ink: M stays low
    R = 205.0 - blotch * 52.0 - depth * 14.0              # paper tooth, faint groove gloss
    Cc = np.minimum(20.0 + fiber * 24.0 + stain * 12.0, 60.0)  # capped: document
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_we_the_people(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_5, seed)
    line, _depth = _guilloche_fields(h, w, s)
    fiber = _msc(h, w, [5, 12, 26], s ^ 0x39)
    parchment = np.array([0.847, 0.788, 0.643], np.float32)
    base = np.broadcast_to(parchment, (h, w, 3)).copy()
    base *= (0.92 + 0.08 * fiber)[:, :, None]             # aged mottle
    ink = np.array([0.149, 0.106, 0.078], np.float32)
    lm = line[:, :, None]
    eff = np.clip(base * (1.0 - lm * 0.78) + ink * (lm * 0.78), 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 6) MIDNIGHT MILITIA  (tactical matte camo, ultra-low shine)
# ============================================================================
FID_6 = "lfr_midnight_militia"

_CAMO = (
    np.array([0.063, 0.082, 0.149], np.float32),   # navy
    np.array([0.176, 0.196, 0.227], np.float32),   # slate
    np.array([0.247, 0.255, 0.196], np.float32),   # olive
    np.array([0.114, 0.122, 0.110], np.float32),   # charcoal
)


def _camo_fields(h, w, seed):
    a = _msc(h, w, [70, 150], seed ^ 0x61)
    b = _msc(h, w, [40, 95], seed ^ 0x65)
    c = _msc(h, w, [110, 210], seed ^ 0x69)
    # 4-way blob assignment
    idx = np.zeros((h, w), np.int32)
    idx = np.where(a > 0.55, 1, idx)
    idx = np.where(b > 0.60, 2, idx)
    idx = np.where(c > 0.58, 3, idx)
    light = np.clip(a * 0.5 + b * 0.5, 0.0, 1.0)
    return idx, light


def _spec_lfr_midnight_militia(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_6, seed)
    _idx, light = _camo_fields(h, w, s)
    grain = _msc(h, w, [2, 5, 11], s ^ 0x62)
    grit = _msc(h, w, [3, 7], s ^ 0x63)
    M = 12.0 + light * 22.0                               # faint, only on lightest
    R = 226.0 - grain * 26.0                              # matte, micro-varied by grain
    Cc = np.minimum(18.0 + grit * 14.0, 40.0)            # near-floor clearcoat
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_midnight_militia(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_6, seed)
    idx, _light = _camo_fields(h, w, s)
    grain = _msc(h, w, [2, 5, 11], s ^ 0x6A)
    eff = np.zeros((h, w, 3), np.float32)
    for k, col in enumerate(_CAMO):
        eff[idx == k] = col
    eff *= (0.90 + 0.10 * grain)[:, :, None]              # deep grain, no shine
    eff = _upscale(np.clip(eff, 0.0, 1.0), fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 7) FREEDOM FORGE  (Voronoi molten-crack steel crust)
# ============================================================================
FID_7 = "lfr_freedom_forge"


def _forge_fields(h, w, seed):
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    npts = 90
    py = rng.uniform(0, h, npts).astype(np.float32)
    px = rng.uniform(0, w, npts).astype(np.float32)
    yy, xx, _, _ = _coords(h, w)
    # F1/F2 Worley via KD-tree (exact two nearest distances — identical to the
    # old npts x full-grid loop, but O(N log n); owner render-time doctrine).
    try:
        from scipy.spatial import cKDTree
        dd, _ = cKDTree(np.stack([py, px], axis=1)).query(
            np.stack([yy.ravel(), xx.ravel()], axis=1), k=2, workers=-1)
        d1 = dd[:, 0].reshape(h, w).astype(np.float32)
        d2 = dd[:, 1].reshape(h, w).astype(np.float32)
    except Exception:  # scipy ships with SPB; loop kept as a safety net
        d1 = np.full((h, w), 1e9, np.float32)
        d2 = np.full((h, w), 1e9, np.float32)
        for i in range(npts):
            dd = (yy - py[i]) ** 2 + (xx - px[i]) ** 2
            closer = dd < d1
            d2 = np.where(closer, d1, np.minimum(d2, dd))
            d1 = np.where(closer, dd, d1)
        d1 = np.sqrt(d1)
        d2 = np.sqrt(d2)
    crack = np.clip(1.0 - (d2 - d1) / (0.02 * max(h, w)), 0.0, 1.0)  # 1 on cell edges
    plateau = 1.0 - crack
    # white-hot sparks
    spark = _scatter_field(h, w, seed ^ 0x77, count=160,
                           value_fn=lambda acc, Y, X, cy, cx, rad, ang, amp:
                           np.maximum(acc, np.exp(-(((Y - cy) ** 2 + (X - cx) ** 2) / (rad * 0.25) ** 2)) * amp, out=acc))
    return crack, plateau, np.clip(spark, 0.0, 1.0)


def _spec_lfr_freedom_forge(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_7, seed)
    crack, plateau, spark = _forge_fields(h, w, s)
    micro = _msc(h, w, [4, 9, 18], s ^ 0x22)
    # Decorrelated channels: plateau is 1-crack (perfect complement), so only ONE
    # channel may ride the crack web. Cc keeps it (the glowing-crack identity);
    # M rides an independent tempering mottle; R rides its own heat-brush grain.
    temper = _msc(h, w, [11, 26, 57], s ^ 0x23)
    M = 40.0 + temper * 130.0 + spark * 80.0             # tempered steel mottle + hot glints
    R = 210.0 - micro * 70.0 - spark * 70.0              # forge-brush grain, sparks glossy
    Cc = 24.0 + crack * 150.0 + spark * 110.0            # molten cracks blaze in clearcoat
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_freedom_forge(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_7, seed)
    crack, plateau, spark = _forge_fields(h, w, s)
    steel = np.broadcast_to(_STEEL, (h, w, 3)).copy()
    micro = _msc(h, w, [3, 7, 15], s ^ 0x2A)
    steel *= (0.85 + 0.20 * micro)[:, :, None]
    molten = np.array([0.961, 0.392, 0.078], np.float32)
    hot = np.array([1.0, 0.86, 0.55], np.float32)
    cm = crack[:, :, None]
    eff = np.clip(steel * (1.0 - cm) + molten * cm, 0.0, 1.0)
    eff = np.clip(eff + hot * spark[:, :, None], 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 8) AMBER WAVES  (multi-directional rippling wheat grain + sheen corridors)
# ============================================================================
FID_8 = "lfr_amber_waves"


def _aniso_line(h, w, seed, angle, freq):
    _, _, yn, xn = _coords(h, w)
    ca, sa = np.cos(angle), np.sin(angle)
    axis = (xn * ca + yn * sa) * freq
    cross = (-xn * sa + yn * ca)
    jit = _msc(h, w, [30, 70], seed) - 0.5
    return 0.5 + 0.5 * np.sin(axis * 6.2831 + cross * 3.0 + jit * 4.0)


def _wheat_fields(h, w, seed):
    g = (_aniso_line(h, w, seed ^ 0x1, 0.35, 22.0) * 0.4
         + _aniso_line(h, w, seed ^ 0x2, 1.25, 17.0) * 0.35
         + _aniso_line(h, w, seed ^ 0x3, 2.45, 13.0) * 0.25)
    g = np.clip(g, 0.0, 1.0)
    corridor = np.clip((g - 0.55) * 2.6, 0.0, 1.0)        # traveling sheen corridors
    blade = _edge(g, gain=5.5)
    return g, corridor, blade


def _spec_lfr_amber_waves(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_8, seed)
    g, corridor, blade = _wheat_fields(h, w, s)
    rough_dir = _aniso_line(h, w, s ^ 0xF2, 1.9, 19.0)     # different angle
    bloom = _msc(h, w, [55, 120], s ^ 0xF3)
    M = 30.0 + blade * 150.0 + g * 26.0
    R = 165.0 - corridor * 95.0 - rough_dir * 28.0        # corridors glossy, anti-align
    Cc = 30.0 + (0.5 + 0.5 * np.sin(bloom * 6.2831 + 2.0)) * 90.0 + corridor * 50.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_amber_waves(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_8, seed)
    g, corridor, _blade = _wheat_fields(h, w, s)
    wheat_dark = np.array([0.502, 0.357, 0.110], np.float32)
    wheat_lit = np.array[(0.886, 0.722, 0.286)] if False else np.array([0.886, 0.722, 0.286], np.float32)
    gm = g[:, :, None]
    base = wheat_dark * (1.0 - gm) + wheat_lit * gm
    sun = np.array([0.98, 0.90, 0.62], np.float32)
    eff = np.clip(base + sun * (corridor[:, :, None] * 0.30), 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 9) GLORY CHROME  (crossed-brush chrome + tri-color mirror flecks)
# ============================================================================
FID_9 = "lfr_glory_chrome"


def _chrome_fields(h, w, seed):
    _, _, yn, xn = _coords(h, w)
    brush = np.zeros((h, w), np.float32)
    for k, ang in enumerate((0.2, 1.15, 2.3)):
        ca, sa = np.cos(ang), np.sin(ang)
        cross = (-xn * sa + yn * ca)
        jit = _msc(h, w, [3, 8], seed ^ (0x10 + k)) - 0.5
        brush += np.abs(np.sin(cross * (180.0 + 40 * k) + jit * 6.0)) * (0.4 - 0.08 * k)
    brush = np.clip(brush, 0.0, 1.0)
    flecks = _scatter_field(h, w, seed ^ 0xC10, count=420,
                            value_fn=lambda acc, Y, X, cy, cx, rad, ang, amp:
                            np.maximum(acc, np.exp(-(((Y - cy) ** 2 + (X - cx) ** 2) / (rad * 0.18) ** 2)) * amp, out=acc))
    return brush, np.clip(flecks, 0.0, 1.0)


def _spec_lfr_glory_chrome(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_9, seed)
    brush, flecks = _chrome_fields(h, w, s)
    glint = _msc(h, w, [6, 14], s ^ 0xC3)
    M = 200.0 + flecks * 55.0                             # chrome base -> mirror flecks
    R = 40.0 + brush * 60.0 - flecks * 22.0               # crossed-brush is the texture
    R = np.clip(R, 15.0, 255.0)
    Cc = 24.0 + (0.5 + 0.5 * np.sin(glint * 6.2831 + flecks * 4.0)) * 70.0 + flecks * 60.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_glory_chrome(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_9, seed)
    brush, flecks = _chrome_fields(h, w, s)
    rng = np.random.default_rng(s ^ 0xC0DE)
    pick = cv2.resize(rng.integers(0, 3, (max(8, h // 22), max(8, w // 22))).astype(np.float32),
                      (w, h), interpolation=cv2.INTER_NEAREST)
    chrome = np.array([0.80, 0.82, 0.86], np.float32)
    base = np.broadcast_to(chrome, (h, w, 3)).copy()
    base *= (0.80 + 0.30 * brush)[:, :, None]             # crossed-brush shading
    fleck_col = np.where(pick[:, :, None] < 0.5, _RED,
                         np.where(pick[:, :, None] < 1.5, _WHITE, np.array([0.13, 0.20, 0.55], np.float32)))
    fm = flecks[:, :, None]
    eff = np.clip(base * (1.0 - fm) + fleck_col * fm, 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# 10) SPARKLER DUSK  (scattered comet-spark micro-flake over twilight)
# ============================================================================
FID_10 = "lfr_sparkler_dusk"


def _comet_splat(acc_head, acc_tail, yy, xx, cy, cx, length, ang, amp):
    ca, sa = np.cos(-ang), np.sin(-ang)
    dy = yy - cy
    dx = xx - cx
    u = dx * ca - dy * sa            # along streak
    v = dx * sa + dy * ca            # across streak
    width = max(1.0, length * 0.06)
    across = np.exp(-(v / width) ** 2)
    # tail: 0..length behind head, tapering
    tail = np.clip(1.0 - u / length, 0.0, 1.0) * (u >= 0).astype(np.float32) * across
    head = np.exp(-((u) ** 2 + (v) ** 2) / (width * 1.4) ** 2)
    np.maximum(acc_tail, tail * amp, out=acc_tail)
    np.maximum(acc_head, head * amp, out=acc_head)


def _sparkler_fields(h, w, seed):
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, yn, xn = _coords(h, w)
    head = np.zeros((h, w), np.float32)
    tail = np.zeros((h, w), np.float32)
    for _ in range(360):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        length = rng.uniform(0.02, 0.06) * max(h, w)
        ang = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.5, 1.0)
        # PERF: splat only in the comet's bounding window (tail reaches +length
        # from the head at any rotation; across-width gaussian dies < 0.3*length)
        # — identical output, ~60x less math per comet at the 1024 work grid.
        r = length * 1.3 + 4.0
        y0, y1 = max(0, int(cy - r)), min(h, int(cy + r) + 1)
        x0, x1 = max(0, int(cx - r)), min(w, int(cx + r) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        _comet_splat(head[y0:y1, x0:x1], tail[y0:y1, x0:x1],
                     yy[y0:y1, x0:x1], xx[y0:y1, x0:x1], cy, cx, length, ang, amp)
    # isotropic twilight vignette (not top-down)
    vig = np.sqrt((xn - 0.5) ** 2 + (yn - 0.5) ** 2)
    return np.clip(head, 0, 1), np.clip(tail, 0, 1), vig


def _spec_lfr_sparkler_dusk(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_10, seed)
    head, tail, _vig = _sparkler_fields(h, w, s)
    haze = _msc(h, w, [40, 90], s ^ 0xD2)
    nebula = _msc(h, w, [60, 130], s ^ 0xD3)
    # Decorrelated channels: the comet field may only drive M (the twinkling
    # flake identity). R rides its own dusk grain; Cc rides the nebula bloom.
    grain_r = _msc(h, w, [6, 13, 29], s ^ 0xD4)
    M = 22.0 + head * 225.0 + tail * 28.0                # hot micro-flake comet heads
    R = 175.0 - haze * 42.0 - grain_r * 40.0 - tail * 38.0  # dusk ground soft, streaks crisp
    Cc = 28.0 + nebula * 132.0 + haze * 26.0             # twilight bloom on its own field
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_lfr_sparkler_dusk(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_10, seed)
    head, tail, vig = _sparkler_fields(h, w, s)
    dusk_near = np.array([0.176, 0.110, 0.286], np.float32)
    dusk_far = np.array([0.063, 0.043, 0.137], np.float32)
    base = dusk_near * (1.0 - vig[:, :, None]) + dusk_far * vig[:, :, None]
    tail_col = _GOLD * tail[:, :, None]
    head_col = _WHITE * head[:, :, None]
    eff = np.clip(base + tail_col * 0.7 + head_col, 0.0, 1.0)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)

# ---------------------------------------------------------------------------
# REGISTRY EXPORT - engine/registry.py does mono_reg.update(LFR_MONOLITHICS)
# ---------------------------------------------------------------------------
LFR_MONOLITHICS = {
    FID_1:  (_spec_lfr_old_glory_flux,    _paint_lfr_old_glory_flux),
    FID_2:  (_spec_lfr_rockets_red_glare, _paint_lfr_rockets_red_glare),
    FID_3:  (_spec_lfr_liberty_torch,     _paint_lfr_liberty_torch),
    FID_4:  (_spec_lfr_eagle_ascendant,   _paint_lfr_eagle_ascendant),
    FID_5:  (_spec_lfr_we_the_people,     _paint_lfr_we_the_people),
    FID_6:  (_spec_lfr_midnight_militia,  _paint_lfr_midnight_militia),
    FID_7:  (_spec_lfr_freedom_forge,     _paint_lfr_freedom_forge),
    FID_8:  (_spec_lfr_amber_waves,       _paint_lfr_amber_waves),
    FID_9:  (_spec_lfr_glory_chrome,      _paint_lfr_glory_chrome),
    FID_10: (_spec_lfr_sparkler_dusk,     _paint_lfr_sparkler_dusk),
}

# ── 2026-08-31 spec rebuild ────────────────────────────────────────────────
# Owner: "keep the designs in place that's there now for the base paint and
# rework ALL of the specs." Unlike the other four cultural shelves these ten are
# fully PROCEDURAL — there is no authored plate on disk to read — so each spec
# renders its own paint once at the role-finding resolution and authors the
# material from that. The paint functions are untouched.
def _lfr_render_paint(paint_fn, res):
    import numpy as _np
    base = _np.full((res, res, 3), 0.5, _np.float32)
    out = _np.asarray(paint_fn(base, (res, res), _np.ones((res, res), _np.float32),
                               51, 1.0, None), _np.float32)
    return out / 255.0 if out.max() > 1.5 else out


def _lfr_new_spec_fn(finish_id, paint_fn):
    def spec_fn(shape, mask, seed, sm):
        import numpy as _np
        from engine.paint_v2 import cultural_spec_2026 as _CS
        _CS.ensure("let_freedom_ring",
                   tuple(LFR_MONOLITHICS.keys()),
                   lambda fid: _lfr_render_paint(LFR_MONOLITHICS[fid][1], 256))
        h, w = int(shape[0]), int(shape[1])
        tex = _lfr_render_paint(paint_fn, min(1024, max(h, w)))
        spec, _story = _CS.build("let_freedom_ring", finish_id, tex, 51, float(sm))
        spec = _np.asarray(spec, _np.uint8)
        if cv2 is not None and spec.shape[:2] != (h, w):
            spec = cv2.resize(spec, (w, h), interpolation=cv2.INTER_NEAREST)
        m = _np.asarray(mask, _np.float32)
        if m.ndim == 3:
            m = m[:, :, 0]
        if cv2 is not None and m.shape[:2] != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
        out = spec.astype(_np.float32)
        if out.shape[2] < 4:
            out = _np.dstack([out, _np.full((h, w, 1), 255.0, _np.float32)])
        outside = 1.0 - m
        out[:, :, 0] = _np.clip(out[:, :, 0] * m + 4.0 * outside, 0, 255)
        out[:, :, 1] = _np.clip(out[:, :, 1] * m + 120.0 * outside, 15, 255)
        out[:, :, 2] = _np.clip(out[:, :, 2] * m + 80.0 * outside, 16, 255)
        out[:, :, 3] = 255
        return out.astype(_np.uint8)

    spec_fn.__name__ = "spec_%s_v2" % finish_id
    return spec_fn


_LFR_NEW_SPECS = {
    fid: (_lfr_new_spec_fn(fid, pair[1]), pair[1])
    for fid, pair in LFR_MONOLITHICS.items()
}
LFR_MONOLITHICS.update(_LFR_NEW_SPECS)



# === IGNITION REBUILD 2026-06-10 START ===
# --- IGNITION: lfr_old_glory_flux ---
# ============================================================================
# 1) OLD GLORY FLUX -- IGNITION REBUILD (the Wovenlight principle, 2026-06-10)
# Motif system: star-spangled flux. Three random-angle, domain-warped current
# filaments sweep a deep navy body; two constellations of randomly-rotated
# 5-point stars ride the same currents. IGNITION (dark-hidden polarity): the
# ember constellation is sunk INTO the navy as quiet shadow stars
# (deep-lightness only, no hue shift) while those EXACT pixels carry near-max
# METALLIC -- invisible at most angles, it DETONATES silver-white the moment
# the sun lines up. Aspect split of ONE motif system (decorrelation by
# construction, never alien geometry per channel):
#   M  = hidden ember-star constellation (detonator, ~8-12% hot)
#   R  = crimson current-ridge gloss corridors (the filaments run wet)
#   Cc = third-angle macro flux-phase pools breathing across the body
# UV-agnostic: per-star random rotation, three random filament angles +
# domain warp, random pool angle -- nothing upright, no stripes, no canton.
# ============================================================================


@lru_cache(maxsize=2)
def _ign_ogf_fields(h, w, seed):
    # memoized so spec_fn + paint_fn (same shape/seed, back-to-back in every
    # render) build the shared fields ONCE — returned arrays are READ-ONLY
    # (all consumers below do pure arithmetic; matches _ign_rrg/torch/eagle).
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    sr = max(h, w) / 1024.0
    # flux currents: three random-angle, domain-warped filament families
    wu = _msc(h, w, [max(9, int(37 * sr)), max(25, int(101 * sr))], seed ^ 0x0F1) - 0.5
    wv = _msc(h, w, [max(9, int(43 * sr)), max(25, int(117 * sr))], seed ^ 0x0F2) - 0.5
    cur = np.zeros((h, w), np.float32)
    phs = np.zeros((h, w), np.float32)
    for _k in range(3):
        ang = rng.uniform(0.0, np.pi)
        per = max(6.0, rng.uniform(18.0, 30.0) * sr)
        ca, sa = np.cos(ang), np.sin(ang)
        u = (xx * ca + yy * sa) / per + wu * rng.uniform(2.0, 3.4) + wv * rng.uniform(-1.7, 1.7)
        fu = u - np.floor(u)
        phs += (0.5 + 0.5 * np.sin(2.0 * np.pi * u)).astype(np.float32)
        ridge = np.clip(1.0 - np.abs(fu - 0.5) / 0.085, 0.0, 1.0) ** 1.6
        cur = np.maximum(cur, ridge.astype(np.float32))
    phs = (phs / 3.0).astype(np.float32)
    # third-angle macro pools (Cc aspect -- same system, slower carrier)
    a3 = rng.uniform(0.0, np.pi)
    p3 = max(48.0, rng.uniform(170.0, 260.0) * sr)
    w3 = (_msc(h, w, [max(15, int(61 * sr)), max(37, int(149 * sr))], seed ^ 0x0F3) - 0.5) * (44.0 * sr)
    c3 = (xx * np.cos(a3) + yy * np.sin(a3) + w3) / p3
    pools = ((0.5 + 0.5 * np.sin(2.0 * np.pi * c3)) ** 2.0).astype(np.float32)
    # two constellations from the SAME star generator: proud + hidden
    glory = _scatter_field(h, w, seed ^ 0x57A6, count=520, value_fn=_star_splat)
    ember = _scatter_field(h, w, seed ^ 0xE3B7, count=1300, value_fn=_star_splat)
    return cur, phs, pools, np.clip(glory, 0.0, 1.0), np.clip(ember, 0.0, 1.0)


def _ign_ogf_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_1, seed)
    cur, phs, pools, glory, ember = _ign_ogf_fields(h, w, s)
    em = np.clip(ember * 2.6, 0.0, 1.0)
    gm = np.clip(glory * 1.6, 0.0, 1.0)
    flake = _msc(h, w, [3, 7, 15], s ^ 0x6F1)
    grain = _msc(h, w, [5, 11, 23], s ^ 0x6F2)
    # M -- DETONATOR: the hidden ember constellation blazes near-max on the
    # exact shadow-star pixels; glory stars only a satin pip; body calm.
    M = 14.0 + 241.0 * em + 24.0 * gm * (1.0 - em) + 12.0 * (flake - 0.5)
    # R -- the crimson filaments run wet/glossy; the navy field stays satin
    # with its own micro grain; ember stars dry slightly (cross-term only).
    R = 168.0 - 118.0 * cur - 30.0 * (grain - 0.5) - 22.0 * em
    # Cc -- third-angle macro flux pools; the slow carrier breathes the coat.
    Cc = 40.0 + 138.0 * pools + 26.0 * (phs - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_ogf_paint(paint, shape, mask, seed, pm, bb):
    from engine.color_science import oklch_ramp
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_1, seed)
    cur, phs, pools, glory, ember = _ign_ogf_fields(h, w, s)
    em = np.clip(ember * 2.6, 0.0, 1.0)
    gm = np.clip(glory * 1.6, 0.0, 1.0)
    # navy flux body -- deep-lightness OKLab ramp breathing with the carrier
    t_b = np.clip(0.10 + 0.55 * phs + 0.20 * (pools - 0.5), 0.0, 1.0)
    body = _ramp([(0.016, 0.026, 0.092), (0.043, 0.067, 0.196), (0.080, 0.122, 0.322)],
                 t_b, flatten_lightness=0.25)
    # crimson current filaments -- red heart, gold-white crest at full ridge
    fil = _ramp([(0.42, 0.04, 0.10), (0.78, 0.10, 0.15), (0.97, 0.84, 0.62)],
                np.clip(cur * 1.12, 0.0, 1.0))
    line = cur[..., None]
    eff = body * (1.0 - 0.88 * line) + fil * (0.88 * line)
    # glory stars -- proud white / red, per-star pick (coarse jitter grid)
    rng = np.random.default_rng(s ^ 0x6107)
    pick = cv2.resize((rng.random((max(8, h // 24), max(8, w // 24))) > 0.45).astype(np.float32),
                      (w, h), interpolation=cv2.INTER_NEAREST)
    star_col = _WHITE * pick[..., None] + _RED * (1.0 - pick[..., None])
    eff = eff * (1.0 - gm[..., None]) + star_col * gm[..., None]
    # IGNITION: the ember constellation sinks DARK into the navy -- the same
    # pixels that detonate in M; deep-lightness only, no hue change.
    eff = eff * (1.0 - em[..., None]) + (body * 0.18) * em[..., None]
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


LFR_MONOLITHICS[FID_1] = (_ign_ogf_spec, _ign_ogf_paint)


# --- IGNITION: lfr_rockets_red_glare ---
# ============================================================================
# 2) ROCKETS RED GLARE -- IGNITION REBUILD (the Wovenlight principle)
# Motif system: night-sky shellbursts. Scattered burst hearts throw fine
# scintillating spark filaments (random spoke counts/phases -- radial, never
# upright); thin shock shells ring each heart; ember dust drifts between.
# IGNITION (saffron polarity -- bright lines traced hot): the white-red-gold
# spark filaments + burst hearts are painted BRIGHT and those EXACT pixels
# carry near-max CLEARCOAT -- at most angles they read as painted fireworks;
# when the sun lines up the whole burst flares wet like live fire.
# Aspect split of ONE motif system (decorrelation by construction):
#   Cc = spark filaments + burst hearts (detonator, ~5-10% hot)
#   R  = shock-shell gloss rings (each smoke ring is a slick wet band)
#   M  = drifting ember-dust scatter (metallic pinpricks between bursts)
# UV-agnostic: radial bursts at random centers/phases, no global direction.
# ============================================================================


@lru_cache(maxsize=2)
def _ign_rrg_fields(h, w, seed):
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    ray = np.zeros((h, w), np.float32)
    core = np.zeros((h, w), np.float32)
    shell = np.zeros((h, w), np.float32)
    halo = np.zeros((h, w), np.float32)
    radf = np.zeros((h, w), np.float32)
    n = int(rng.integers(10, 15))
    for _ in range(n):
        cy = rng.uniform(0.04, 0.96) * h
        cx = rng.uniform(0.04, 0.96) * w
        reach = rng.uniform(0.06, 0.11) * m
        rwin = reach * 1.8
        y0, y1 = max(0, int(cy - rwin)), min(h, int(cy + rwin) + 1)
        x0, x1 = max(0, int(cx - rwin)), min(w, int(cx + rwin) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        rr = (r / reach).astype(np.float32)
        decay = np.exp(-rr * 1.25).astype(np.float32)
        nspk = int(rng.integers(24, 42))
        ph = rng.uniform(0.0, 6.28318)
        beam = np.clip(np.cos(th * nspk + ph), 0.0, 1.0) ** 10
        # scintillation: rays break into spark dashes along their length
        dash = 0.55 + 0.45 * np.sin(rr * rng.uniform(80.0, 130.0) + th * 3.0 + ph)
        fil = (beam * dash * decay).astype(np.float32)
        sray = ray[y0:y1, x0:x1]
        keep = fil > sray
        sradf = radf[y0:y1, x0:x1]
        np.copyto(sradf, np.clip(rr, 0.0, 1.0).astype(np.float32), where=keep)
        np.copyto(sray, fil, where=keep)
        score = core[y0:y1, x0:x1]
        np.maximum(score, np.exp(-(rr / 0.19) ** 2).astype(np.float32), out=score)
        sshell = shell[y0:y1, x0:x1]
        for _j in range(int(rng.integers(2, 5))):
            rad_j = reach * rng.uniform(0.35, 0.95)
            wdt = max(2.5, 0.016 * reach)
            np.maximum(sshell, (np.exp(-((r - rad_j) / wdt) ** 2)
                                * rng.uniform(0.6, 1.0)).astype(np.float32), out=sshell)
        halo[y0:y1, x0:x1] += np.exp(-rr * rr * 0.9).astype(np.float32) * 0.5
    # ember-fall: scattered glowing dust drifting between the bursts (M aspect)
    ember = _scatter_field(h, w, seed ^ 0x3E3, count=900,
                           value_fn=lambda acc, Y, X, cy, cx, rad, ang, amp:
                           np.maximum(acc, np.exp(-(((Y - cy) ** 2 + (X - cx) ** 2)
                                                    / (rad * 0.22) ** 2)) * amp, out=acc))
    return (np.clip(ray * 2.0, 0.0, 1.0), np.clip(core, 0.0, 1.0),
            np.clip(shell, 0.0, 1.0), np.clip(halo, 0.0, 1.0),
            radf, np.clip(ember, 0.0, 1.0))


def _ign_rrg_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_2, seed)
    ray, core, shell, halo, radf, ember = _ign_rrg_fields(h, w, s)
    soot = _msc(h, w, [4, 9, 19], s ^ 0x9A1)
    glare = np.clip(ray + core * 0.9, 0.0, 1.0)
    # Cc -- DETONATOR (saffron polarity): the wet coat blazes on the EXACT
    # bright spark filaments + hearts; the powder night idles in the 20s.
    Cc = 22.0 + 236.0 * glare + 12.0 * (soot - 0.5)
    # R -- shock shells own the gloss corridors: each ring is a slick circular
    # wet band; the night is matte with its own soot grain.
    R = 196.0 - 132.0 * shell - 34.0 * (soot - 0.5) - 26.0 * glare
    # M -- drifting ember dust: scattered metallic pinpricks (own geometry);
    # the burst halo only re-biases it softly.
    M = 14.0 + 178.0 * ember + 30.0 * halo
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_rrg_paint(paint, shape, mask, seed, pm, bb):
    from engine.color_science import oklch_ramp, candy_absorb
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_2, seed)
    ray, core, shell, halo, radf, ember = _ign_rrg_fields(h, w, s)
    # powder-night body -- bruised violet lift inside the halos, never dead black
    t_n = np.clip(0.16 + 0.58 * halo, 0.0, 1.0)
    night = _ramp([(0.027, 0.031, 0.078), (0.071, 0.047, 0.133), (0.122, 0.075, 0.192)],
                  t_n, flatten_lightness=0.1)
    # THE GLARE -- white-hot roots, blood-red body, ember-gold tips; traced on
    # the exact pixels the clearcoat detonates on.
    sparkc = _ramp([(1.00, 0.93, 0.78), (0.92, 0.18, 0.10), (0.96, 0.62, 0.18)],
                   np.clip(radf * 1.05, 0.0, 1.0))
    rm = ray[..., None]
    eff = night * (1.0 - rm) + sparkc * rm
    # burst hearts bloom red -> white-hot
    heart = _ramp([(0.92, 0.20, 0.12), (1.00, 0.90, 0.74)], core)
    cm = (core * 0.9)[..., None]
    eff = eff * (1.0 - cm) + heart * cm
    # shock shells -- quiet smoke rings drinking candy-red (R goes slick there)
    eff = candy_absorb(eff, (0.62, 0.16, 0.20), shell * 0.55, density=1.0)
    # drifting ember dust -- faint warm pinpricks married to the M scatter
    eff = eff + np.array([0.30, 0.12, 0.03], np.float32) * (ember * 0.5)[..., None]
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


LFR_MONOLITHICS[FID_2] = (_ign_rrg_spec, _ign_rrg_paint)


# --- IGNITION: lfr_liberty_torch ---
# ============================================================================
# 3) LIBERTY TORCH  (IGNITION REBUILD — crucible braid / mirror-smoke detonation)
# Paint: char-black crucible crossed by thin curl-warped flame braids (deep
# red roots -> amber -> white-gold cores; two-axis domain warp = no global
# "up", UV-agnostic). IGNITION (M, hidden-mirror polarity): a SECOND iso-band
# of the SAME braid field — interleaved with the flame band by construction,
# never overlapping it — is painted as near-black "cold smoke" (darker than
# the body, invisible at most angles) while carrying mirror metal ~240+ on
# those exact pixels: liquid-chrome smoke that detonates when the sun lines
# up. The braid is quantile-uniformized so band areas are seed-stable.
# Aspects of one braid system: M = smoke iso-band, R = blurred heat bloom +
# char grain, Cc = braid flow-wall shimmer + slow varnish pools.
# ============================================================================
from engine.color_science import oklch_ramp


@lru_cache(maxsize=16)
def _ign_torch_ramp_lut(stops_key, flatten):
    ts = np.linspace(0.0, 1.0, 257, dtype=np.float32)
    return oklch_ramp([list(s) for s in stops_key], ts,
                      flatten_lightness=flatten).astype(np.float32)


def _ign_torch_ramp(stops, t, flatten_lightness=0.0):
    """LUT-evaluated oklch_ramp (visually identical, skips full-grid OKLab)."""
    key = tuple(tuple(float(c) for c in s) for s in stops)
    lut = _ign_torch_ramp_lut(key, float(flatten_lightness))
    x = np.clip(np.asarray(t, np.float32), 0.0, 1.0) * np.float32(256)
    i0 = np.minimum(x.astype(np.int32), 255)
    f = (x - i0.astype(np.float32))[..., None]
    return (lut[i0] * (1.0 - f) + lut[i0 + 1] * f).astype(np.float32)


@lru_cache(maxsize=2)
def _ign_torch_fields(h, w, seed):
    # memoized so paint reuses spec's fields in the same render pass
    # (deterministic per (h,w,seed); callers must NOT mutate returned arrays)
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, _, _ = _coords(h, w)
    # two-axis curl warp — omnidirectional, no global flame direction
    wx = (_msc(h, w, [max(11, int(36 * sr)), max(29, int(96 * sr))], seed ^ 0x1A11) - 0.5)
    wy = (_msc(h, w, [max(11, int(42 * sr)), max(29, int(108 * sr))], seed ^ 0x2B22) - 0.5)
    amp = 0.055 * m
    sx = np.clip(xx + wx * 2.0 * amp, 0, w - 1).astype(np.float32)
    sy = np.clip(yy + wy * 2.0 * amp, 0, h - 1).astype(np.float32)
    carrier = _msc(h, w, [max(4, int(7 * sr)), max(8, int(15 * sr)), max(17, int(32 * sr))],
                   seed ^ 0x3C33)
    braid = cv2.remap(carrier, sx, sy, interpolation=cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    # quantile-uniformize -> iso-band areas are IDENTICAL for every seed
    knots = np.linspace(0.0, 1.0, 65).astype(np.float32)
    qs = np.maximum.accumulate(np.quantile(braid, knots).astype(np.float32))
    bu = np.interp(braid, qs, knots).astype(np.float32)
    # flame filaments: thin band around one rank-isoline of the braid
    d_fl = np.abs(bu - 0.66)
    tongue = (np.clip(1.0 - d_fl / 0.10, 0.0, 1.0) ** 1.4).astype(np.float32)
    core = (np.clip(1.0 - d_fl / 0.05, 0.0, 1.0) ** 1.2).astype(np.float32)
    # mirror smoke: a SECOND rank-band of the SAME field (gap 0.36 > 0.14+0.13)
    d_sm = np.abs(bu - 0.30)
    smoke = (np.clip(1.0 - d_sm / 0.10, 0.0, 1.0) ** 0.85).astype(np.float32)
    # heat bloom (R's aspect): soft warmth halo breathing around the braid
    bloom = cv2.GaussianBlur(tongue, (0, 0), max(1.6, 4.2 * sr)).astype(np.float32)
    bloom = np.clip(bloom * 1.8, 0.0, 1.0).astype(np.float32)
    # flow walls (Cc's aspect): gradient ridges of the same braid
    wall = _edge(bu, gain=8.0)
    ember = _msc(h, w, [max(3, int(4 * sr)), max(5, int(9 * sr))], seed ^ 0x4D44)
    pool = _msc(h, w, [max(21, int(44 * sr)), max(43, int(98 * sr))], seed ^ 0x5E55)
    return bu, tongue, core, smoke, bloom, wall, ember, pool


def _ign_torch_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("lfr_liberty_torch", seed)
    bu, tongue, core, smoke, bloom, wall, ember, pool = _ign_torch_fields(h, w, s)
    # M — DETONATOR: chrome smoke band (near-black in paint, mirror in spec)
    M = 14.0 + 244.0 * np.clip(smoke * 1.45, 0.0, 1.0) + 10.0 * core * (1.0 - smoke)
    # R — heat bloom: glossy warmth halo around the braid, raw char elsewhere
    R = 182.0 - 118.0 * bloom - 30.0 * (ember - 0.5) * 2.0 - 24.0 * core
    # Cc — flow-wall shimmer + slow varnish pools (third aspect, stays sub-hot)
    Cc = (34.0 + 96.0 * wall * (1.0 - smoke)
          + 58.0 * (0.5 + 0.5 * np.sin(pool * 6.2831 + 0.9)) + 28.0 * core)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_torch_paint(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("lfr_liberty_torch", seed)
    bu, tongue, core, smoke, bloom, wall, ember, pool = _ign_torch_fields(h, w, s)
    # crucible body: char black breathing with faint heat
    t_b = np.clip(0.18 + 0.55 * bloom + 0.20 * (ember - 0.5), 0.0, 1.0)
    body = _ign_torch_ramp([(0.043, 0.022, 0.016), (0.125, 0.055, 0.026)], t_b)
    # flame braid: committed red -> amber -> white-gold along the filament heat
    t_f = np.clip(0.10 + 0.62 * tongue + 0.55 * core, 0.0, 1.0)
    flame = _ign_torch_ramp([(0.36, 0.043, 0.031), (0.78, 0.31, 0.051), (0.98, 0.86, 0.55)],
                            t_f, flatten_lightness=0.1)
    fmask = np.clip(tongue * 1.25, 0.0, 1.0)[..., None]
    eff = body * (1.0 - fmask) + flame * fmask
    # IGNITION pixels stay QUIET: cold smoke paints DARKER than the body
    sm3 = np.clip(smoke * 1.2, 0.0, 1.0)[..., None]
    cold = np.array([0.014, 0.018, 0.034], np.float32)
    eff = eff * (1.0 - sm3 * 0.85) + cold * (sm3 * 0.85)
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# --- IGNITION: lfr_eagle_ascendant ---
# ============================================================================
# 4) EAGLE ASCENDANT  (IGNITION REBUILD — pinion storm / gilded-barb detonation)
# Paint: scattered rotated pinion feathers (tapered vanes, engraved barb
# chevrons, bone-white spines; an oxblood war-spine minority) over a deep
# night-navy field. IGNITION (Cc, traced-hot polarity): about half the
# feathers are "gilded pinions" — their outer-vane barb lines are painted
# committed gold AND carry clearcoat ~235+ on those exact pixels, so the
# gold lacquer lines detonate against the calm navy when the sun walks
# across them. Aspects of one feather system: M = spine skeleton + faint
# third-angle gleam, R = vane-body satin vs inter-feather down (own grain),
# Cc = gilded outer-vane barb lines.
# ============================================================================
from engine.color_science import oklch_ramp


@lru_cache(maxsize=16)
def _ign_eagle_ramp_lut(stops_key, flatten):
    ts = np.linspace(0.0, 1.0, 257, dtype=np.float32)
    return oklch_ramp([list(s) for s in stops_key], ts,
                      flatten_lightness=flatten).astype(np.float32)


def _ign_eagle_ramp(stops, t, flatten_lightness=0.0):
    """LUT-evaluated oklch_ramp (visually identical, skips full-grid OKLab)."""
    key = tuple(tuple(float(c) for c in s) for s in stops)
    lut = _ign_eagle_ramp_lut(key, float(flatten_lightness))
    x = np.clip(np.asarray(t, np.float32), 0.0, 1.0) * np.float32(256)
    i0 = np.minimum(x.astype(np.int32), 255)
    f = (x - i0.astype(np.float32))[..., None]
    return (lut[i0] * (1.0 - f) + lut[i0 + 1] * f).astype(np.float32)


@lru_cache(maxsize=2)
def _ign_eagle_fields(h, w, seed):
    # memoized so paint reuses spec's fields in the same render pass
    # (deterministic per (h,w,seed); callers must NOT mutate returned arrays)
    m = float(max(h, w))
    sr = m / 1024.0
    rng = np.random.default_rng((seed ^ 0xEA61E) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    vane = np.zeros((h, w), np.float32)
    shaft = np.zeros((h, w), np.float32)
    shaft_r = np.zeros((h, w), np.float32)
    barb = np.zeros((h, w), np.float32)
    gild = np.zeros((h, w), np.float32)
    for _ in range(520):
        cy = rng.uniform(0.0, h)
        cx = rng.uniform(0.0, w)
        rad = rng.uniform(0.018, 0.038) * m
        ang = rng.uniform(0.0, 2.0 * np.pi)
        amp = rng.uniform(0.72, 1.0)
        bsp = rng.uniform(3.4, 5.4) * sr
        roll = rng.random()
        rwin = 1.25 * rad + 2.0
        y0, y1 = max(0, int(cy - rwin)), min(h, int(cy + rwin) + 1)
        x0, x1 = max(0, int(cx - rwin)), min(w, int(cx + rwin) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        ca, sa = np.cos(-ang), np.sin(-ang)
        u = dx * ca - dy * sa
        v = dx * sa + dy * ca
        un = u / rad                                  # -1 tip .. +1 root
        env = np.clip(1.0 - np.abs(un), 0.0, 1.0)
        half = rad * (0.14 + 0.40 * np.clip((un + 1.0) * 0.5, 0.0, 1.0))
        vn = np.abs(v) / np.maximum(half, 1e-3)
        vbody = np.clip(1.0 - vn * vn, 0.0, 1.0) * np.clip(env * 1.7, 0.0, 1.0) * amp
        sline = np.exp(-(v / (rad * 0.035)) ** 2) * np.clip(env * 1.4, 0.0, 1.0) * amp
        ph = (u * 0.95 + np.abs(v) * 1.65) / max(bsp, 1.0)
        ridge = 0.5 + 0.5 * np.cos(ph * 6.2831853)
        bline = np.clip((ridge - 0.45) / 0.25, 0.0, 1.0) * (vbody > 0.04) * amp
        np.maximum(vane[y0:y1, x0:x1], vbody, out=vane[y0:y1, x0:x1])
        if roll < 0.52:
            outer = np.clip((vn - 0.16) / 0.20, 0.0, 1.0)
            np.maximum(gild[y0:y1, x0:x1], bline * outer, out=gild[y0:y1, x0:x1])
            np.maximum(shaft[y0:y1, x0:x1], sline, out=shaft[y0:y1, x0:x1])
        elif roll < 0.68:
            np.maximum(shaft_r[y0:y1, x0:x1], sline, out=shaft_r[y0:y1, x0:x1])
        else:
            np.maximum(shaft[y0:y1, x0:x1], sline, out=shaft[y0:y1, x0:x1])
        np.maximum(barb[y0:y1, x0:x1], bline, out=barb[y0:y1, x0:x1])
    down = _msc(h, w, [max(3, int(4 * sr)), max(5, int(9 * sr)), max(11, int(19 * sr))],
                seed ^ 0xD0D0)
    # third-angle sheen lane (M's faint gleam) + macro breath (Cc calm bed)
    a3 = rng.uniform(0.0, np.pi)
    w3 = (_msc(h, w, [max(17, int(67 * sr)), max(43, int(171 * sr))], seed ^ 0xC4C4) - 0.5) * (40.0 * sr)
    c3 = (xx * np.cos(a3) + yy * np.sin(a3) + w3) / max(150.0 * sr, 40.0)
    sheen = ((0.5 + 0.5 * np.sin(2.0 * np.pi * c3)) ** 2.0).astype(np.float32)
    macro = _msc(h, w, [max(31, int(120 * sr)), max(61, int(260 * sr))], seed ^ 0xB5B5)
    return vane, shaft, shaft_r, barb, gild, down, sheen, macro


def _ign_eagle_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("lfr_eagle_ascendant", seed)
    vane, shaft, shaft_r, barb, gild, down, sheen, macro = _ign_eagle_fields(h, w, s)
    spine = np.maximum(shaft, shaft_r)
    # M — spine skeleton + faint third-angle gleam (moderate, never detonates)
    M = 24.0 + 152.0 * spine + 34.0 * sheen * (1.0 - vane * 0.6)
    # R — vane-body satin vs rough inter-feather down; barbs add tooth back
    R = (174.0 - 104.0 * vane * (1.0 - 0.45 * barb)
         + 22.0 * (down - 0.5) * 2.0 - 26.0 * spine)
    # Cc — DETONATOR: gilded outer-vane barb lines (the gold paint lines)
    Cc = (36.0 + 22.0 * (macro - 0.5) * 2.0 + 12.0 * sheen
          + 222.0 * np.clip(gild * 1.35, 0.0, 1.0))
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_eagle_paint(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("lfr_eagle_ascendant", seed)
    vane, shaft, shaft_r, barb, gild, down, sheen, macro = _ign_eagle_fields(h, w, s)
    g1 = np.clip(gild * 1.35, 0.0, 1.0)
    # night-navy field breathing under the storm
    t_b = np.clip(0.25 + 0.90 * (macro - 0.5) + 0.30 * (down - 0.5), 0.0, 1.0)
    body = _ign_eagle_ramp([(0.016, 0.030, 0.102), (0.047, 0.078, 0.212)], t_b)
    # steel-navy satin vanes
    vcol = _ign_eagle_ramp([(0.055, 0.092, 0.243), (0.140, 0.196, 0.392)],
                           np.clip(0.20 + 0.85 * vane, 0.0, 1.0))
    v3 = np.clip(vane * 1.5, 0.0, 1.0)[..., None]
    eff = body * (1.0 - v3) + vcol * v3
    # engraved barb chevrons (darker), except where gilded
    eff = eff * (1.0 - 0.38 * (barb * (1.0 - g1))[..., None])
    # bone-white spines / oxblood war spines (red seasoning)
    sw3 = np.clip(shaft * 1.2, 0.0, 1.0)[..., None]
    eff = eff * (1.0 - sw3) + np.array([0.886, 0.902, 0.929], np.float32) * sw3
    sr3 = np.clip(shaft_r * 1.2, 0.0, 1.0)[..., None]
    eff = eff * (1.0 - sr3) + np.array([0.557, 0.071, 0.110], np.float32) * sr3
    # IGNITION pixels painted committed gold — the exact Cc hot-lines
    g3 = g1[..., None]
    eff = eff * (1.0 - g3) + np.array([0.945, 0.776, 0.337], np.float32) * g3
    # third-angle light lane kisses the albedo (subtle)
    eff = np.clip(eff + 0.05 * sheen[..., None] * np.array([0.6, 0.7, 1.0], np.float32),
                  0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# --- IGNITION: lfr_we_the_people ---
def _ign_wtp_ramp_lut(stops_key, flatten):
    """257-entry LUT for oklch_ramp (smooth parchment ramp: lerp error invisible;
    skips the full-grid OKLab conversion -- render-time doctrine)."""
    from engine.color_science import oklch_ramp
    return oklch_ramp([list(s) for s in stops_key],
                      np.linspace(0.0, 1.0, 257).astype(np.float32),
                      flatten_lightness=flatten).astype(np.float32)

def _ign_wtp_ramp(stops, t, flatten=0.0):
    lut = _ign_wtp_ramp_lut(tuple(tuple(float(c) for c in s) for s in stops), float(flatten))
    x = np.clip(np.asarray(t, np.float32), 0.0, 1.0) * np.float32(256.0)
    i0 = np.minimum(x.astype(np.int32), 255)
    f = (x - i0.astype(np.float32))[..., None]
    return (lut[i0] * (1.0 - f) + lut[i0 + 1] * f).astype(np.float32)

@lru_cache(maxsize=2)
def _ign_wtp_fields(h, w, seed):
    # NOTE: memoized so spec_fn + paint_fn (same shape/seed, back-to-back in
    # every render) build the shared fields ONCE — returned arrays are shared,
    # treat them as READ-ONLY (all consumers below do pure arithmetic).
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, yn, xn = _coords(h, w)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    ink = np.zeros((h, w), np.float32)      # every engraved line
    seal = np.zeros((h, w), np.float32)     # sealed-rosette ink (the ignition)
    heart = np.zeros((h, w), np.float32)    # burnish halos (Cc's aspect)
    n_ros = int(rng.integers(18, 24))
    for _ in range(n_ros):
        cy = rng.uniform(0.04, 0.96) * h
        cx = rng.uniform(0.04, 0.96) * w
        rad = rng.uniform(0.075, 0.14) * m
        nr = float(rng.integers(7, 12))            # lathe rings per rosette
        pet = float(rng.integers(5, 10))           # petal harmonic
        ph = rng.uniform(0.0, 6.28318)
        ph2 = rng.uniform(0.0, 6.28318)
        sealed = rng.random() < 0.60
        r_win = rad * 1.5 + 2.0   # wide enough for the heart halo to die smoothly
        y0, y1 = max(0, int(cy - r_win)), min(h, int(cy + r_win) + 1)
        x0, x1 = max(0, int(cx - r_win)), min(w, int(cx + r_win) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        g = np.cos((r / np.float32(rad)) * np.float32(6.28318 * nr)
                   + np.float32(2.6) * np.sin(th * np.float32(pet) + np.float32(ph))
                   + np.float32(ph2))
        fade = np.clip((np.float32(1.0) - r / np.float32(rad)) * np.float32(5.0), 0.0, 1.0)
        lin = np.clip((g - np.float32(0.40)) / np.float32(0.45), 0.0, 1.0) * fade
        np.maximum(ink[y0:y1, x0:x1], lin, out=ink[y0:y1, x0:x1])
        if sealed:
            np.maximum(seal[y0:y1, x0:x1], lin, out=seal[y0:y1, x0:x1])
        # halo fades to EXACT zero at the window edge (no square seams in Cc)
        hfade = np.clip((np.float32(1.5) - r / np.float32(rad)) / np.float32(0.25), 0.0, 1.0)
        heart[y0:y1, x0:x1] += np.exp(-((r / np.float32(rad * 0.75)) ** 2)) * np.float32(0.85) * hfade
    # two wavy lathe-work line beds at random angles knit the rosettes together
    # (float32 scalars throughout: a python-float scalar would upcast the whole
    # grid to float64 and double the trig cost — render-time doctrine)
    for k in range(2):
        ang = rng.uniform(0.0, np.pi)
        ca, sa = np.float32(np.cos(ang)), np.float32(np.sin(ang))
        u = xn * ca + yn * sa
        v = -xn * sa + yn * ca
        f1 = np.float32(rng.uniform(240.0, 330.0))
        f2 = np.float32(rng.uniform(26.0, 52.0))
        jit = _msc(h, w, [max(9, int(31 * sr)), max(21, int(77 * sr))], seed ^ (0x5A1 + k)) - np.float32(0.5)
        bed = np.cos(u * f1 + np.sin(v * f2) * np.float32(2.4) + jit * np.float32(5.0)
                     + np.float32(rng.uniform(0.0, 6.28318)))
        np.maximum(ink, np.clip((bed - np.float32(0.62)) / np.float32(0.38), 0.0, 1.0) * np.float32(0.55), out=ink)
    depth = _edge(ink, gain=5.0)
    heart = np.clip(heart, 0.0, 1.0)
    fiber = _msc(h, w, [3, 7, 15], seed ^ 0x33A)
    blotch = _msc(h, w, [14, 31, 67], seed ^ 0x34B)
    return ink, seal, heart, depth, fiber, blotch

def _ign_wtp_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_5, seed)
    ink, seal, heart, depth, fiber, blotch = _ign_wtp_fields(h, w, s)
    grain = _msc(h, w, [4, 9, 19], s ^ 0x35C)
    # M — IGNITION: sealed-rosette ink detonates into mirror-gold intaglio
    # foil on its EXACT paint pixels; plain ink keeps a graphite whisper.
    M = 10.0 + seal * 252.0 + np.clip(ink - seal, 0.0, 1.0) * 24.0 + fiber * 8.0
    # R — its own aspect: intaglio groove relief (every engraved EDGE polishes
    # glossy) over matte paper tooth + blotch. Not the ink body.
    R = 206.0 - depth * 148.0 - blotch * 44.0 + (grain - 0.5) * 18.0
    # Cc — third aspect: burnish halos pooling on the rosette hearts; the wet
    # seal cross-term backs the gold flash without copying it.
    Cc = 30.0 + heart * 110.0 + fiber * 22.0 + seal * 40.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)

def _ign_wtp_paint(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_5, seed)
    ink, seal, heart, depth, fiber, blotch = _ign_wtp_fields(h, w, s)
    # aged parchment via OKLab ramp (deep tan -> parchment -> pale cream)
    t_p = np.clip(0.22 + 0.50 * blotch + 0.22 * fiber + 0.10 * heart, 0.0, 1.0)
    parch = _ign_wtp_ramp([(0.588, 0.494, 0.333), (0.847, 0.788, 0.643), (0.933, 0.902, 0.776)],
                          t_p, flatten=0.12)
    sepia = np.array([0.196, 0.137, 0.090], np.float32)
    im = np.clip(ink - seal * 0.85, 0.0, 1.0)[:, :, None]
    eff = parch * (1.0 - im * 0.74) + sepia * (im * 0.74)
    # the sealed articles: near-black iron-gall ink — quiet in albedo, the
    # SAME pixels the spec detonates. A whisper of gold rims the intaglio.
    seal_ink = np.array([0.058, 0.051, 0.075], np.float32)
    sl3 = seal[:, :, None]
    eff = eff * (1.0 - sl3 * 0.90) + seal_ink * (sl3 * 0.90)
    gold_rim = (depth * 0.10)[:, :, None] * np.array([0.83, 0.66, 0.22], np.float32)
    eff = np.clip(eff + gold_rim, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)

# --- IGNITION: lfr_midnight_militia ---
@lru_cache(maxsize=2)
def _ign_militia_fields(h, w, seed):
    # NOTE: memoized so spec_fn + paint_fn (same shape/seed, back-to-back in
    # every render) build the shared fields ONCE — returned arrays are shared,
    # treat them as READ-ONLY (all consumers below do pure arithmetic).
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    a = _msc(h, w, [20, 46, 95], seed ^ 0x61A)
    b = _msc(h, w, [13, 30, 66], seed ^ 0x65B)
    c = _msc(h, w, [32, 72, 140], seed ^ 0x69C)
    # quantile-pinned thresholds: patch coverage is a DESIGNED fraction, not a
    # seed lottery (the ghost panel must stay in the 5-35% hot-area window)
    q1 = float(np.quantile(a, 0.62))
    q2 = float(np.quantile(b, 0.74))
    gtgt = rng.uniform(0.19, 0.25)                 # ghost coverage target
    q3 = float(np.quantile(c, 1.0 - gtgt))
    m1 = np.clip((a - q1) / 0.045, 0.0, 1.0)
    m2 = np.clip((b - q2) / 0.045, 0.0, 1.0)
    m3 = np.clip((c - q3) / 0.045, 0.0, 1.0)       # the ghost patch (ignition)
    # panel seam corridors: thin bands hugging EVERY patch boundary
    bnd = np.maximum.reduce([
        1.0 - np.clip(np.abs(a - q1) / 0.02, 0.0, 1.0),
        1.0 - np.clip(np.abs(b - q2) / 0.02, 0.0, 1.0),
        1.0 - np.clip(np.abs(c - q3) / 0.02, 0.0, 1.0)]).astype(np.float32)
    # two random-angle micro-hatch combs (each patch family owns one);
    # float32 scalars keep the full-grid trig out of float64
    hat = []
    for k in range(2):
        ang = rng.uniform(0.0, np.pi)
        u = xx * np.float32(np.cos(ang)) + yy * np.float32(np.sin(ang))
        p = rng.uniform(3.2, 5.2)
        jit = _msc(h, w, [9, 23], seed ^ (0x7A0 + k)) - np.float32(0.5)
        hat.append((np.float32(0.5) + np.float32(0.5)
                    * np.sin(u * np.float32(6.28318 / p) + jit * np.float32(5.0))).astype(np.float32))
    # retroreflector dust (tiny windowed splats) — only lives inside m3
    spk = _scatter_field(h, w, seed ^ 0x77D, count=2400,
                         value_fn=lambda acc, Y, X, cy, cx, rad, ang, amp:
                         np.maximum(acc, np.exp(-(((Y - cy) ** 2 + (X - cx) ** 2) / (rad * 0.22) ** 2)) * amp, out=acc))
    spk = (np.clip(spk, 0.0, 1.0) * m3).astype(np.float32)
    grain = _msc(h, w, [2, 5, 11], seed ^ 0x6AE)
    return m1, m2, m3, bnd, hat[0], hat[1], spk, grain

def _ign_militia_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_6, seed)
    m1, m2, m3, bnd, h1, h2, spk, grain = _ign_militia_fields(h, w, s)
    # Cc — IGNITION: the ghost patches are a hidden glass coat (~237) on the
    # EXACT blue-black paint pixels; everything else stays night-matte.
    Cc = 22.0 + m3 * 215.0 + spk * 20.0 - bnd * 8.0
    # M — retroreflector dust inside the ghost panels only; dead matte outside.
    M = 8.0 + spk * 247.0 + bnd * 24.0 + h2 * m3 * 12.0
    # R — its own aspect: stitched seam corridors polish glossy; ghost panels
    # run semi-gloss under their glass; per-family hatch combs the matte.
    hsel = np.maximum(m1, m3)
    comb = h1 * (1.0 - hsel) + h2 * hsel
    R = (226.0 - bnd * 150.0 - m3 * 48.0 - spk * 70.0
         - (comb - 0.5) * 26.0 - (grain - 0.5) * 22.0)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)

def _ign_militia_paint(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_6, seed)
    m1, m2, m3, bnd, h1, h2, spk, grain = _ign_militia_fields(h, w, s)
    gun = np.array([0.075, 0.090, 0.137], np.float32)     # gunmetal navy
    slate = np.array([0.169, 0.188, 0.212], np.float32)
    olive = np.array([0.204, 0.212, 0.161], np.float32)   # gray-olive
    ghost = np.array([0.027, 0.031, 0.047], np.float32)   # the wet-panel black
    eff = np.broadcast_to(gun, (h, w, 3)).copy()
    eff = eff * (1.0 - m1[:, :, None]) + slate * m1[:, :, None]
    eff = eff * (1.0 - m2[:, :, None]) + olive * m2[:, :, None]
    eff = eff * (1.0 - m3[:, :, None]) + ghost * m3[:, :, None]
    # per-family micro-hatch comb + deep grain (matte cloth, never shine)
    hsel = np.maximum(m1, m3)
    comb = h1 * (1.0 - hsel) + h2 * hsel
    eff = eff * (0.88 + 0.09 * comb + 0.05 * grain)[:, :, None]
    # stitched panel seams catch a thread of light (R's corridor, visible)
    eff = eff + (bnd * 0.055)[:, :, None] * np.array([0.55, 0.60, 0.68], np.float32)
    # retroreflector dust: barely-there in albedo — the sun finds it
    eff = eff + (spk * 0.12)[:, :, None] * np.array([0.65, 0.70, 0.80], np.float32)
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)

# --- IGNITION: lfr_freedom_forge ---
# ============================================================================
# ===== LFR: FREEDOM FORGE — IGNITION REBUILD (2026-06-10, Wovenlight pass) ==
# One shared forge-floor geometry feeds paint AND spec. ~260 scattered Voronoi
# steel plates (cKDTree F1/F2 — omnidirectional, UV-agnostic), each plate
# dealt its own tempering hue; ~22% of plates are OIL-QUENCHED: rendered
# near-black gun-blue in the albedo but carrying M~244 across their EXACT
# faces — invisible mirror plates that DETONATE when the sun lines up
# (dark-hidden Wovenlight polarity). The molten seam web between plates glows
# ember->white-hot in the paint and the SAME seam pixels blaze in Cc, so both
# ignition reads marry the visible geometry. Aspect split (decorrelation):
# M = quenched plate faces ONLY; R = hammer-peen dimple relief (its own
# scattered geometry); Cc = breathing molten seams + anvil-spark pins.
# Color is seasoning: one charcoal->gun-blue->bronze temper ramp + ember seams.
# ============================================================================
from engine.color_science import oklch_ramp


def _ign_forge_dimple_splat(acc, yy, xx, cy, cx, rad, ang, amp):
    """Hammer-peen dimple: bright rim ring + soft bowl (R's own aspect)."""
    dy = yy - cy
    dx = xx - cx
    r = np.sqrt(dy * dy + dx * dx)
    rim = np.exp(-((r - rad * 0.70) / (rad * 0.15 + 0.5)) ** 2)
    bowl = np.exp(-(r / (rad * 0.50 + 0.5)) ** 2)
    np.maximum(acc, (rim * 0.90 + bowl * 0.35) * amp, out=acc)


@lru_cache(maxsize=2)
def _ign_forge_fields(h, w, seed):
    """Shared geometry for paint AND spec (spec marries paint).
    Returns (cell_t, quench, crack, glowmod, dimple, spark).
    Memoized: spec_fn + paint_fn build it ONCE per render; returned arrays
    are READ-ONLY (all consumers do pure arithmetic)."""
    m = float(max(h, w))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    npts = 850
    py_ = rng.uniform(0, h, npts).astype(np.float32)
    px_ = rng.uniform(0, w, npts).astype(np.float32)
    yy, xx, _, _ = _coords(h, w)
    try:
        from scipy.spatial import cKDTree
        dd, ii = cKDTree(np.stack([py_, px_], axis=1)).query(
            np.stack([yy.ravel(), xx.ravel()], axis=1), k=2, workers=-1)
        d1 = dd[:, 0].reshape(h, w).astype(np.float32)
        d2 = dd[:, 1].reshape(h, w).astype(np.float32)
        cell = ii[:, 0].reshape(h, w).astype(np.int64)
    except Exception:  # scipy ships with SPB; loop kept as a safety net
        d1 = np.full((h, w), 1e9, np.float32)
        d2 = np.full((h, w), 1e9, np.float32)
        cell = np.zeros((h, w), np.int64)
        for i in range(npts):
            ddi = np.sqrt((yy - py_[i]) ** 2 + (xx - px_[i]) ** 2)
            closer = ddi < d1
            d2 = np.where(closer, d1, np.minimum(d2, ddi))
            cell = np.where(closer, i, cell)
            d1 = np.where(closer, ddi, d1)
    # per-PLATE identities — a DESIGNED deal, never per-pixel randomness
    temper_v = rng.random(npts).astype(np.float32)
    quench_v = (rng.random(npts) < 0.22).astype(np.float32)
    cell_t = temper_v[cell]
    quench = quench_v[cell]
    # molten seam web between plates (~5 px at the 1024 work grid)
    crack = (np.clip(1.0 - (d2 - d1) / (0.0050 * m), 0.0, 1.0) ** 1.5).astype(np.float32)
    quench = (quench * (1.0 - crack)).astype(np.float32)   # seams stay seams
    # slow heat-breath along the seams (drives Cc AND the paint glow)
    glowmod = _msc(h, w, [max(int(m * 0.026), 4), max(int(m * 0.07), 7)], seed ^ 0x4F1)
    # hammer-peen dimple rims — R's OWN scattered geometry
    dimple = np.clip(_scatter_field(h, w, seed ^ 0x4F2, count=1900,
                                    value_fn=_ign_forge_dimple_splat), 0.0, 1.0)
    # white-hot anvil sparks (shared pinpoints: visible AND hot in M/Cc)
    spark = np.clip(_scatter_field(h, w, seed ^ 0x4F3, count=300,
                                   value_fn=lambda acc, Y, X, cy, cx, rad, ang, amp:
                                   np.maximum(acc, np.exp(-(((Y - cy) ** 2 + (X - cx) ** 2)
                                                            / (rad * 0.22) ** 2)) * amp, out=acc)),
                    0.0, 1.0)
    return cell_t, quench, crack, glowmod, dimple, spark


def _ign_forge_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("lfr_freedom_forge", seed)
    cell_t, quench, crack, glowmod, dimple, spark = _ign_forge_fields(h, w, s)
    micro = _msc(h, w, [3, 7, 15], s ^ 0x4F4)
    # M — IGNITION: the quenched plates (near-black in the paint) are full
    # mirrors ~244 on their EXACT pixels (~20% area); tempered plates hold a
    # calm 26-58 satin floor; molten seams kill the metal read entirely.
    M = 26.0 + 218.0 * quench + 32.0 * cell_t * (1.0 - quench) + 60.0 * spark
    M = M * (1.0 - 0.80 * crack)
    # R — hammer-peen relief (its own scatter): dimple rims polish glossy,
    # plate faces stay forge-satin with anvil micro grain.
    R = 196.0 - 132.0 * dimple - 60.0 * spark + 26.0 * (micro - 0.5)
    # Cc — the molten seam web blazes on the EXACT ember pixels of the paint,
    # breathing along glowmod; quenched mirrors shed coat (oil-quench dull).
    Cc = 30.0 + 215.0 * crack * (0.62 + 0.38 * glowmod) + 90.0 * spark - 14.0 * quench
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_forge_paint(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("lfr_freedom_forge", seed)
    cell_t, quench, crack, glowmod, dimple, spark = _ign_forge_fields(h, w, s)
    # tempered plate steel: charcoal -> gun-blue -> bronze, dealt per plate
    t_p = np.clip(0.15 + 0.70 * cell_t + 0.10 * (glowmod - 0.5), 0.0, 1.0)
    body = _ramp([(0.118, 0.133, 0.165), (0.165, 0.220, 0.330), (0.430, 0.300, 0.180)],
                 t_p, flatten_lightness=0.30)
    # hammer-peen shading rides the SAME dimple geometry R polishes
    body = body * (0.86 + 0.22 * dimple[..., None])
    # QUENCHED MIRROR PLATES: near-black blued steel — quiet at most angles,
    # detonating in M on these EXACT pixels when the sun lines up
    qcol = _ramp([(0.030, 0.042, 0.075), (0.058, 0.075, 0.120)], cell_t)
    qm = quench[..., None]
    eff = body * (1.0 - qm) + qcol * qm
    # molten seam web: ember -> white-hot, breathing with glowmod (the SAME
    # pixels the clearcoat detonates on)
    heat = np.clip(crack * (0.55 + 0.45 * glowmod), 0.0, 1.0)
    ember = _ramp([(0.62, 0.16, 0.04), (0.97, 0.55, 0.12), (1.00, 0.88, 0.58)], heat)
    cm = np.clip(crack * 1.15, 0.0, 1.0)[..., None]
    eff = eff * (1.0 - cm) + ember * cm
    # anvil sparks: white-hot pinpoints (shared with the M/Cc pins)
    eff = np.clip(eff + np.array([1.0, 0.92, 0.70], np.float32) * spark[..., None],
                  0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


LFR_MONOLITHICS.update({
    "lfr_freedom_forge": (_ign_forge_spec, _ign_forge_paint),
})


# --- IGNITION: lfr_amber_waves ---
# ============================================================================
# ===== LFR: AMBER WAVES — IGNITION REBUILD (2026-06-10, Wovenlight pass) ====
# One shared harvest geometry feeds paint AND spec. Three random-angle,
# domain-warped ripple trains build the rolling grain swells (UV-agnostic —
# never one direction); ~620 scattered wheat-awn bristle strokes glint pale
# straw in the paint and metal-flash M on the SAME pixels. The IGNITION is the
# HONEY RIVERS: meandering level-set channels of one slow field, painted as
# deep molasses — dark and quiet in the albedo — while their EXACT pixels
# carry Cc~245: a glass-wet glaze that is near-invisible until the sun rakes
# the panel, then the dark rivers flash like poured honey (dark-hidden
# polarity detonating in Cc — deliberately a different channel and a different
# choreography than Freedom Forge). Aspect split (decorrelation): M = awn
# bristles; R = ripple-crest gloss corridors; Cc = honey rivers + faint
# third-angle pool. Color is seasoning: one amber->gold ramp, straw glints,
# molasses rivers.
# ============================================================================
from engine.color_science import oklch_ramp


def _ign_amber_awn_splat(acc, yy, xx, cy, cx, rad, ang, amp):
    """Wheat-awn bristle: short tapered stroke in its own rotated frame."""
    ca, sa = np.cos(-ang), np.sin(-ang)
    dy = yy - cy
    dx = xx - cx
    u = dx * ca - dy * sa
    v = dx * sa + dy * ca
    taper = np.clip(1.0 - np.abs(u) / (rad * 1.7), 0.0, 1.0)
    across = np.exp(-(v / (rad * 0.13 + 0.6)) ** 2)
    np.maximum(acc, (taper ** 0.7) * across * amp, out=acc)


@lru_cache(maxsize=2)
def _ign_amber_fields(h, w, seed):
    """Shared geometry for paint AND spec (spec marries paint).
    Returns (g, crest, river, rmod, awn, pool).
    Memoized: spec_fn + paint_fn build it ONCE per render; returned arrays
    are READ-ONLY (all consumers do pure arithmetic)."""
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, _, _ = _coords(h, w)
    rng = np.random.default_rng((seed ^ 0x3A7B) & 0x7FFFFFFF)
    # rolling grain swells: THREE random-angle, domain-warped ripple trains
    g = np.zeros((h, w), np.float32)
    for k, wgt in enumerate((0.40, 0.34, 0.26)):
        ang = float(rng.uniform(0.0, np.pi))
        per = max(4.5, float(rng.uniform(6.0, 11.0)) * sr)
        warp = (_msc(h, w, [max(13, int(47 * sr)), max(31, int(120 * sr))],
                     seed ^ (0x3A90 + k)) - 0.5) * (11.0 * sr)
        c = (xx * np.cos(ang) + yy * np.sin(ang) + warp) / per
        g = g + wgt * (0.5 + 0.5 * np.sin(2.0 * np.pi * c))
    g = np.clip(g, 0.0, 1.0).astype(np.float32)
    crest = np.clip((g - 0.62) * 3.2, 0.0, 1.0).astype(np.float32)
    # HONEY RIVERS: meandering level-set channels of one quantile-normalised
    # slow field (closed wandering curves — omnidirectional by construction)
    slow = _msc(h, w, [max(26, int(95 * sr)), max(56, int(210 * sr))], seed ^ 0x3AC1)
    s_lo = float(np.quantile(slow, 0.02))
    s_hi = float(np.quantile(slow, 0.98))
    slow = np.clip((slow - s_lo) / max(s_hi - s_lo, 1e-6), 0.0, 1.0)
    bw = 0.038
    riv1 = np.clip(1.0 - np.abs(slow - 0.50) / bw, 0.0, 1.0)
    riv2 = np.clip(1.0 - np.abs(slow - 0.24) / (bw * 0.55), 0.0, 1.0)   # tributaries
    river = np.maximum(riv1 ** 1.7, (riv2 ** 1.7) * 0.85).astype(np.float32)
    # heat-breath along the rivers (drives Cc AND the molasses tint)
    rmod = _msc(h, w, [max(int(m * 0.03), 4), max(int(m * 0.08), 7)], seed ^ 0x3AD2)
    # wheat-awn bristles — M's OWN scattered geometry (visible straw glints)
    awn = np.clip(_scatter_field(h, w, seed ^ 0x3AE3, count=1600,
                                 value_fn=_ign_amber_awn_splat), 0.0, 1.0)
    # faint third-angle pool (Cc's calm off-river drift)
    a3 = float(rng.uniform(0.0, np.pi))
    p3 = max(40.0, float(rng.uniform(150.0, 230.0)) * sr)
    w3 = (_msc(h, w, [max(17, int(67 * sr)), max(43, int(171 * sr))], seed ^ 0x3AF4) - 0.5) * (38.0 * sr)
    c3 = (xx * np.cos(a3) + yy * np.sin(a3) + w3) / p3
    pool = ((0.5 + 0.5 * np.sin(2.0 * np.pi * c3)) ** 2.2).astype(np.float32)
    return g, crest, river, rmod, awn, pool


def _ign_amber_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("lfr_amber_waves", seed)
    g, crest, river, rmod, awn, pool = _ign_amber_fields(h, w, s)
    husk = _msc(h, w, [3, 6, 13], s ^ 0x3AF5)
    # M — the awn bristles metal-flash on their EXACT pale paint pixels; the
    # field holds a warm satin floor; rivers drown the metal completely.
    M = (30.0 + 190.0 * awn + 26.0 * crest * (1.0 - awn)) * (1.0 - 0.72 * river)
    # R — ripple-crest gloss corridors (its own geometry): crests polish,
    # troughs stay chaff-dry; husk micro grain keeps the plateau alive.
    R = 188.0 - 124.0 * crest - 30.0 * awn + 24.0 * (husk - 0.5)
    # Cc — IGNITION: the dark molasses rivers carry a glass-wet honey glaze
    # ~245 on their EXACT pixels (~8-16% area) — near-invisible until the sun
    # rakes them; elsewhere the coat stays dry-field calm with a faint pool.
    Cc = 28.0 + 220.0 * (river ** 1.5) * (0.72 + 0.28 * rmod) + 26.0 * pool * (1.0 - river)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_amber_paint(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("lfr_amber_waves", seed)
    g, crest, river, rmod, awn, pool = _ign_amber_fields(h, w, s)
    # golden field: deep amber troughs -> bright gold crests (the SAME swell
    # geometry whose crests R polishes)
    t_g = np.clip(0.18 + 0.58 * g + 0.16 * crest, 0.0, 1.0)
    body = _ramp([(0.42, 0.26, 0.07), (0.80, 0.55, 0.16), (0.97, 0.82, 0.42)],
                 t_g, flatten_lightness=0.20)
    # awn bristles: pale straw glints on the EXACT M pixels
    am = (awn ** 1.2)[..., None]
    eff = body * (1.0 - 0.85 * am) + np.array([0.99, 0.91, 0.62], np.float32) * (0.85 * am)
    # HONEY RIVERS: deep molasses channels — DARK and quiet in the albedo,
    # detonating in Cc on these EXACT pixels; a thin amber edge-light keeps
    # the channel reading as a designed river, not dirt
    rivcol = _ramp([(0.16, 0.075, 0.020), (0.30, 0.140, 0.035)], rmod)
    rm = (river ** 1.2)[..., None]
    eff = eff * (1.0 - rm) + rivcol * rm
    edge = np.clip(river * (1.0 - river) * 4.0, 0.0, 1.0) ** 2
    eff = np.clip(eff + np.array([0.30, 0.16, 0.03], np.float32) * edge[..., None] * 0.30, 0.0, 1.0)
    # the third-angle pool kisses the albedo (subtle; Cc carries the glow)
    eff = np.clip(eff * (0.94 + 0.11 * pool[..., None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


LFR_MONOLITHICS.update({
    "lfr_amber_waves": (_ign_amber_spec, _ign_amber_paint),
})


# --- IGNITION: lfr_glory_chrome ---
# ============================================================================
# 9) GLORY CHROME -- engine-turned chrome shard mosaic with candy detonators.
# IGNITION (wovenlight principle, mirror-under-candy polarity): ~28% of the
# shards are dipped in DEEP candy oxblood / midnight-navy -- near-black glass
# in the albedo -- but carry near-max M on those EXACT pixels. Dead quiet at
# most angles; when the sun lines up the dark shards detonate as red and blue
# mirror fire against calm spun silver. SPEC MARRIES PAINT: R traces the same
# engine-turn grooves that shade every shard, Cc rides the seam corridors cut
# between shards, M owns the shard territory. UV-agnostic: scattered shards,
# per-shard radial rings -- no global axis anywhere.
# ============================================================================


@lru_cache(maxsize=2)
def _ign_glorychrome_fields(h, w, seed):
    # memoized so spec_fn + paint_fn (same shape/seed) build the shared fields
    # ONCE per render — returned arrays are READ-ONLY (consumers do pure math).
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    m = float(max(h, w))
    sr = m / 1024.0
    npts = max(600, int(2600 * sr * sr))
    py = rng.uniform(0, h, npts).astype(np.float32)
    px = rng.uniform(0, w, npts).astype(np.float32)
    yy, xx, _, _ = _coords(h, w)
    try:
        from scipy.spatial import cKDTree
        dd, ii = cKDTree(np.stack([py, px], axis=1)).query(
            np.stack([yy.ravel(), xx.ravel()], axis=1), k=2, workers=-1)
        d1 = dd[:, 0].reshape(h, w).astype(np.float32)
        d2 = dd[:, 1].reshape(h, w).astype(np.float32)
        idx = ii[:, 0].reshape(h, w).astype(np.int32)
    except Exception:
        d1 = np.full((h, w), 1e9, np.float32)
        d2 = np.full((h, w), 1e9, np.float32)
        idx = np.zeros((h, w), np.int32)
        for i in range(npts):
            di = np.sqrt((yy - py[i]) ** 2 + (xx - px[i]) ** 2)
            closer = di < d1
            d2 = np.where(closer, d1, np.minimum(d2, di))
            idx = np.where(closer, i, idx)
            d1 = np.where(closer, di, d1)
    # per-shard engine-turn rings: every shard spins around ITS OWN center,
    # with its own period and phase (8-17px features at the 2048 canvas)
    period = (rng.uniform(3.4, 6.4, npts) * max(0.35, sr)).astype(np.float32)
    phase = rng.uniform(0.0, 2.0 * np.pi, npts).astype(np.float32)
    ring = (0.5 + 0.5 * np.cos(d1 / period[idx] * 2.0 * np.pi + phase[idx])).astype(np.float32)
    groove = (1.0 - ring).astype(np.float32)
    # shard classes: 0 = bare chrome (calm), 1 = candy oxblood, 2 = candy navy
    cls = rng.choice(np.array([0, 1, 2], np.int32), size=npts, p=[0.72, 0.14, 0.14]).astype(np.int32)
    shard_cls = cls[idx]
    candy = (shard_cls > 0).astype(np.float32)
    red_shard = (shard_cls == 1).astype(np.float32)
    # seam lines + wider corridor lattice between shards (parity-free aspect)
    seam_w = max(1.2, 1.6 * sr)
    seam = np.clip(1.0 - (d2 - d1) / (seam_w * 2.4), 0.0, 1.0).astype(np.float32)
    corridor = np.clip(1.0 - (d2 - d1) / (seam_w * 7.0), 0.0, 1.0).astype(np.float32)
    macro = _msc(h, w, [max(19, int(74 * sr)), max(43, int(170 * sr))], seed ^ 0x9C1).astype(np.float32)
    return ring, groove, candy, red_shard, seam, corridor, macro


def _ign_glorychrome_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_9, seed)
    ring, groove, candy, red_shard, seam, corridor, macro = _ign_glorychrome_fields(h, w, s)
    g = np.random.default_rng((s ^ 0x6C0) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    # M -- IGNITION: the dark candy shards hide a near-max mirror (~28% area
    # hot); bare spun silver stays calm mid-bright; the cut seams kill M so the
    # shards read as separate tiles when the flare walks across them.
    M = (130.0 + 30.0 * ring) * (1.0 - candy) + (238.0 + 17.0 * ring) * candy
    M = M * (1.0 - 0.80 * seam)
    # R -- marries the VISIBLE engine-turn shading: cut grooves rough, crests
    # polished, the SAME response on every shard (parity-free vs candy class).
    R = 52.0 + 132.0 * groove + 26.0 * (macro - 0.5) + 14.0 * (g - 0.5)
    # Cc -- the seam-corridor lattice owns the wet coat; candy pools a little
    # deeper in its grooves (small cross-term only, keeps |corr| low).
    Cc = 44.0 + 158.0 * corridor + 26.0 * candy * groove + 22.0 * (macro - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_glorychrome_paint(paint, shape, mask, seed, pm, bb):
    from engine.color_science import oklch_ramp, candy_absorb
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_9, seed)
    ring, groove, candy, red_shard, seam, corridor, macro = _ign_glorychrome_fields(h, w, s)
    # spun silver: the SAME ring field R reads as roughness shades every shard
    metal_t = np.clip(0.30 + 0.55 * ring + 0.15 * (macro - 0.5), 0.0, 1.0)
    silver = _ramp([(0.46, 0.49, 0.55), (0.85, 0.88, 0.93)], metal_t)
    # detonator shards: the same spun metal under DEEP tinted glass -- dark,
    # quiet albedo (the mirror lives in M); candy pools thicker in the grooves
    depth = 1.55 + 0.85 * groove + 0.25 * (macro - 0.5)
    candy_red = candy_absorb(silver, (0.62, 0.045, 0.10), depth, density=1.15)
    candy_navy = candy_absorb(silver, (0.075, 0.115, 0.42), depth, density=1.15)
    rs = red_shard[:, :, None]
    cm = candy[:, :, None]
    eff = silver * (1.0 - cm) + (candy_red * rs + candy_navy * (1.0 - rs)) * cm
    # cut seam shadows give the mosaic its tile read
    eff = eff * (1.0 - 0.55 * seam)[:, :, None]
    # the wet corridor lattice kisses the albedo so Cc reads as designed
    eff = np.clip(eff * (0.96 + 0.07 * corridor[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# --- IGNITION: lfr_sparkler_dusk ---
# ============================================================================
# 10) SPARKLER DUSK -- bent sparkler arcs over a lantern-lit twilight, with a
# hidden ghost-spark detonation. IGNITION (wovenlight principle, dark-hidden
# polarity): ~40% of the sparks are BURNT OUT -- drawn as near-invisible
# charcoal filigree in the albedo -- but those exact arcs carry near-max Cc:
# at most angles only the live gold sparks show; when the sun lines up the
# dead sparks reignite as white fire across the dusk. SPEC MARRIES PAINT: M
# traces the live spark lines crackle-dash for crackle-dash, R rides the
# smoke drift between them, Cc owns the ghost arcs. UV-agnostic: arcs at all
# angles with random curvature, multi-center lantern pools -- no global axis.
# ============================================================================


@lru_cache(maxsize=2)
def _ign_sparklerdusk_fields(h, w, seed):
    # memoized so spec_fn + paint_fn (same shape/seed) build the shared fields
    # ONCE per render — returned arrays are READ-ONLY (consumers do pure math).
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, _, _ = _coords(h, w)
    live_core = np.zeros((h, w), np.float32)
    live_heat = np.zeros((h, w), np.float32)
    ghost_core = np.zeros((h, w), np.float32)
    ghost_glow = np.zeros((h, w), np.float32)
    n_arcs = max(160, int(620 * sr * sr))
    for _ in range(n_arcs):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        length = rng.uniform(0.030, 0.085) * m
        ang = rng.uniform(0.0, 2.0 * np.pi)
        curv = rng.uniform(-0.55, 0.55)
        amp = rng.uniform(0.6, 1.0)
        dash_k = rng.uniform(0.55, 1.15) / max(sr, 0.2)
        dash_p = rng.uniform(0.0, 2.0 * np.pi)
        is_ghost = rng.random() < 0.42
        # PERF: windowed splat (owner doctrine) -- the bent arc never leaves
        # length*1.45 of its head at any curvature; identical output.
        r = length * 1.45 + 4.0
        y0, y1 = max(0, int(cy - r)), min(h, int(cy + r) + 1)
        x0, x1 = max(0, int(cx - r)), min(w, int(cx + r) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        ca, sa = np.cos(-ang), np.sin(-ang)
        u = dx * ca - dy * sa
        v = dx * sa + dy * ca
        vb = v - curv * (u * u) / max(length, 1.0)
        width = max(1.0, length * 0.060)
        along = np.clip(u / length, 0.0, 1.0)
        inside = ((u >= 0.0) & (u <= length)).astype(np.float32)
        across = np.exp(-(vb / width) ** 2)
        if is_ghost:
            core = across * inside * (1.0 - 0.55 * along)
            glow = np.exp(-(vb / (width * 2.4)) ** 2) * inside * (1.0 - 0.38 * along)
            np.maximum(ghost_core[y0:y1, x0:x1], core * amp, out=ghost_core[y0:y1, x0:x1])
            np.maximum(ghost_glow[y0:y1, x0:x1], glow * amp, out=ghost_glow[y0:y1, x0:x1])
        else:
            crackle = 0.60 + 0.40 * np.cos(u * dash_k + dash_p)
            core = across * inside * (1.0 - 0.70 * along) * crackle
            heat = across * inside * (1.0 - along) ** 1.6
            np.maximum(live_core[y0:y1, x0:x1], core * amp, out=live_core[y0:y1, x0:x1])
            np.maximum(live_heat[y0:y1, x0:x1], heat * amp, out=live_heat[y0:y1, x0:x1])
    # multi-center lantern pools (UV-agnostic: several glows, never one vignette)
    lant = np.zeros((h, w), np.float32)
    for _ in range(int(rng.integers(4, 7))):
        gy = rng.uniform(0, h)
        gx = rng.uniform(0, w)
        reach = rng.uniform(0.22, 0.40) * m
        lant += np.exp(-(((yy - gy) ** 2 + (xx - gx) ** 2) / (reach * reach)))
    lant = np.clip(lant, 0.0, 1.0).astype(np.float32)
    smoke = _msc(h, w, [max(13, int(48 * sr)), max(31, int(110 * sr)), max(61, int(230 * sr))], seed ^ 0xD51)
    return (np.clip(live_core, 0.0, 1.0), np.clip(live_heat, 0.0, 1.0),
            np.clip(ghost_core, 0.0, 1.0), np.clip(ghost_glow, 0.0, 1.0), lant, smoke)


def _ign_sparklerdusk_spec(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FID_10, seed)
    live_core, live_heat, ghost_core, ghost_glow, lant, smoke = _ign_sparklerdusk_fields(h, w, s)
    g = np.random.default_rng((s ^ 0xDD7) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    # M -- traces the VISIBLE gold sparks pixel-for-pixel (same crackle dashes
    # the paint draws): hot metallic wire on those lines, calm low dusk floor.
    M = 18.0 + 162.0 * live_core + 30.0 * live_heat + 14.0 * smoke
    # R -- its own aspect of the system: drifting smoke corridors BETWEEN the
    # sparks; any spark line (live or ghost) cuts crisp gloss through the soft.
    R = 158.0 + 56.0 * (smoke - 0.5) - 52.0 * np.maximum(live_core, ghost_core) + 14.0 * (g - 0.5)
    # Cc -- IGNITION: the burnt-out ghost arcs (near-invisible charcoal in the
    # paint) detonate to near-max clearcoat on those EXACT pixels (~8% hot).
    Cc = 34.0 + 16.0 * lant + 226.0 * ghost_glow ** 1.3 + 10.0 * (smoke - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _ign_sparklerdusk_paint(paint, shape, mask, seed, pm, bb):
    from engine.color_science import oklch_ramp
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FID_10, seed)
    live_core, live_heat, ghost_core, ghost_glow, lant, smoke = _ign_sparklerdusk_fields(h, w, s)
    # twilight body: lantern-pooled plum -> deep indigo (OKLab keeps it rich)
    t_d = np.clip(0.16 + 0.48 * lant + 0.22 * (smoke - 0.5), 0.0, 1.0)
    dusk = _ramp([(0.043, 0.033, 0.110), (0.118, 0.072, 0.218), (0.224, 0.130, 0.338)],
                 t_d, flatten_lightness=0.15)
    # ghost sparks: burnt charcoal filigree, a whisper darker than the dusk --
    # the reignition lives in Cc on these exact arcs
    eff = dusk * (1.0 - 0.52 * ghost_core - 0.10 * ghost_glow)[:, :, None]
    # live sparks: ember-red tails -> white-gold heads, crackle dashes visible
    t_s = np.clip(0.18 + 0.42 * live_core + 0.58 * live_heat, 0.0, 1.0)
    spark = _ramp([(0.42, 0.055, 0.030), (0.93, 0.55, 0.13), (1.0, 0.93, 0.78)], t_s)
    a = np.clip(live_core * 1.3, 0.0, 1.0)[:, :, None]
    eff = np.clip(eff * (1.0 - a) + spark * a, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


LFR_MONOLITHICS.update({
    "lfr_old_glory_flux": (_ign_ogf_spec, _ign_ogf_paint),
    "lfr_rockets_red_glare": (_ign_rrg_spec, _ign_rrg_paint),
    "lfr_liberty_torch": (_ign_torch_spec, _ign_torch_paint),
    "lfr_eagle_ascendant": (_ign_eagle_spec, _ign_eagle_paint),
    "lfr_we_the_people": (_ign_wtp_spec, _ign_wtp_paint),
    "lfr_midnight_militia": (_ign_militia_spec, _ign_militia_paint),
    "lfr_freedom_forge": (_ign_forge_spec, _ign_forge_paint),
    "lfr_amber_waves": (_ign_amber_spec, _ign_amber_paint),
    "lfr_glory_chrome": (_ign_glorychrome_spec, _ign_glorychrome_paint),
    "lfr_sparkler_dusk": (_ign_sparklerdusk_spec, _ign_sparklerdusk_paint),
})
# === IGNITION REBUILD 2026-06-10 END ===


# === IGN CALIB 2026-06-10 START ===

def _ign_knee_packed(fn, ch, t_pct=92.0):
    """LEDGE remap: pixels above the t_pct percentile land on 210-255 (guaranteed
    ignition); an over-bright sub-ledge body is scaled under 195 for calm."""
    def f(shape, mask, seed, sm, _f=fn, _c=ch, _t=t_pct):
        import numpy as _np
        out = _f(shape, mask, seed, sm)
        c = out[:, :, _c].astype(_np.float32)
        # deterministic micro-dither breaks ties so flat-bright channels still
        # ledge their top 8% (reads as fine metal-flake sparkle, not a wall)
        c = c + _np.random.default_rng(0x1D17).random(c.shape).astype(_np.float32)
        sel = out[:, :, 3] > 0
        t = float(_np.percentile(c[sel] if sel.any() else c, _t))
        cmax = float(c.max())
        low = c * (195.0 / t) if t > 195.0 else c
        hi = 210.0 + 45.0 * (c - t) / max(1e-3, cmax - t)
        out[:, :, _c] = _np.clip(_np.where(c >= t, hi, low), 0, 255).astype(_np.uint8)
        return out
    return f


def _ign_crush_paint(fn, amp=0.50):
    """SHARP-edged 4-8px micro-fleck layer multiplied into the painted region —
    hard transitions carry the fine gradient energy the fineness metric reads
    (smooth grain does not move it)."""
    def f(paint, shape, mask, seed, pm, bb, _f=fn, _a=amp):
        import numpy as _np
        out = _f(paint, shape, mask, seed, pm, bb)
        fh, fw = _shape2(shape)
        wh, ww = min(fh, 1024), min(fw, 1024)
        g = _np.asarray(_msc(wh, ww, [2, 4], (int(seed) ^ 0xC4C4C4) & 0x7FFFFFFF), _np.float32)
        fleck = _np.clip((g - 0.42) * 5.0, 0.0, 1.0)
        fleck = _upscale(fleck, fh, fw)
        mk = _mask2(mask, fh, fw)
        mod = 1.0 + (fleck - float(fleck.mean())) * _a * mk
        out = _np.clip(_np.asarray(out, _np.float32) * mod[..., None], 0.0, 1.0)
        return out.astype(_np.float32)
    return f


LFR_MONOLITHICS["lfr_rockets_red_glare"] = (LFR_MONOLITHICS["lfr_rockets_red_glare"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_rockets_red_glare"][1], 0.5))

LFR_MONOLITHICS["lfr_rockets_red_glare"] = (_ign_knee_packed(LFR_MONOLITHICS["lfr_rockets_red_glare"][0], 2), LFR_MONOLITHICS["lfr_rockets_red_glare"][1])

LFR_MONOLITHICS["lfr_freedom_forge"] = (LFR_MONOLITHICS["lfr_freedom_forge"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_freedom_forge"][1], 0.5))

LFR_MONOLITHICS["lfr_freedom_forge"] = (_ign_knee_packed(LFR_MONOLITHICS["lfr_freedom_forge"][0], 2), LFR_MONOLITHICS["lfr_freedom_forge"][1])

LFR_MONOLITHICS["lfr_amber_waves"] = (LFR_MONOLITHICS["lfr_amber_waves"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_amber_waves"][1], 0.5))

LFR_MONOLITHICS["lfr_amber_waves"] = (_ign_knee_packed(LFR_MONOLITHICS["lfr_amber_waves"][0], 0), LFR_MONOLITHICS["lfr_amber_waves"][1])

LFR_MONOLITHICS["lfr_old_glory_flux"] = (LFR_MONOLITHICS["lfr_old_glory_flux"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_old_glory_flux"][1], 0.5))

LFR_MONOLITHICS["lfr_liberty_torch"] = (LFR_MONOLITHICS["lfr_liberty_torch"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_liberty_torch"][1], 0.5))

LFR_MONOLITHICS["lfr_eagle_ascendant"] = (LFR_MONOLITHICS["lfr_eagle_ascendant"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_eagle_ascendant"][1], 0.5))

LFR_MONOLITHICS["lfr_we_the_people"] = (LFR_MONOLITHICS["lfr_we_the_people"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_we_the_people"][1], 0.5))

LFR_MONOLITHICS["lfr_midnight_militia"] = (LFR_MONOLITHICS["lfr_midnight_militia"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_midnight_militia"][1], 0.5))

LFR_MONOLITHICS["lfr_glory_chrome"] = (LFR_MONOLITHICS["lfr_glory_chrome"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_glory_chrome"][1], 0.5))

LFR_MONOLITHICS["lfr_sparkler_dusk"] = (LFR_MONOLITHICS["lfr_sparkler_dusk"][0], _ign_crush_paint(LFR_MONOLITHICS["lfr_sparkler_dusk"][1], 0.5))
# === IGN CALIB 2026-06-10 END ===
