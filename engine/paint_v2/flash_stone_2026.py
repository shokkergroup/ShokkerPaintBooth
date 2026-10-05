# -*- coding: utf-8 -*-
"""
engine/paint_v2/flash_stone_2026.py — ★ OPTIC LAB : FLASH STONE (rebuilt 2026-06-15)

10 natural + art-glass ANGLE-FLASH stones. The owner's complaint that drove this
rebuild (verbatim): "fire_agate, labradorite and spectrolite use pretty much the
EXACT SAME spec. black_opal looks too close to ammolite. The dichroic_glass pattern
is bad and needs rethinking."

DOCTRINE FOLLOWED HERE:
  * NO shared template / factory / _RECIPES. Every finish has its OWN bespoke design
    algorithm and its OWN motif. The old _flash_albedo/_flash_spec factory is GONE.
  * Each spec recomputes the SAME geometric fields its paint uses (same seed, shared
    per-finish field helpers) so the spec IGNITES the exact pixels the paint shows.
  * Each spec rides M / R / CC on DIFFERENT geometry with DIFFERENT value
    distributions so the combined (R=M, G=R, B=CC) RGB shows MANY hues, and the
    channels decorrelate (|corr| < 0.85 by construction).

THE TEN — each a distinct optical physics:
  labradorite    broad anisotropic SCHILLER FLASH PLANES (blue/gold), cleavage-aligned
  spectrolite    FULL-spectrum labradorite — intersecting multi-angle plane sets, violent flash
  ammolite       cracked fossil-shell rainbow PLATES, each a solid iris hue, dark seams
  tiger_eye      fine chatoyant silk fibre bands, gold/brown, moving cat's-eye sheen
  dichroic_glass FLOWING thin-film interference SHEETS along warped streamlines (not blocky)
  fire_agate     stacked concentric RED-ORANGE IRIS DOMES (botryoidal layers)
  malachite      banded malachite eyes, green, satin
  azurite        deep-blue wavy contour bands + crystal glints
  black_opal     SPARSE vivid play-of-color FLECKS (pinfire splats) on near-black body
  sunstone       copper aventurescent schiller glitter in warm feldspar

Contracts: paint_x(paint,shape,mask,seed,pm,bb)->HxWx3 ; spec_x(shape,seed,sm,bm,br)->(M,R,CC).
R>=15 (GGX floor), M<=255, CC>=16. sm scales spec contrast. FINE detail; <3s @2048.
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array, hsv_to_rgb_vec
from engine.color_science import interference_palette, linear_to_srgb, srgb_to_linear

_FS_CACHE = {}


# =====================================================================
# small shared PRIMITIVES (math helpers only — NOT a design factory).
# Every finish below builds its OWN motif out of these; no two finishes
# share a motif, a palette recipe, or a spec shape.
# =====================================================================
def _cache(key, fn):
    v = _FS_CACHE.get(key)
    if v is None:
        if len(_FS_CACHE) > 200:
            _FS_CACHE.clear()
        v = fn()
        _FS_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, scales, weights, seed, cap=0):
    """Cached multi-scale noise in [0,1]-ish, optionally generated at a work cap
    then upscaled (for smooth broad fields only)."""
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


def _grain(shape, seed):
    """Full-res tri-tap white-ish grain in [0,1] (fine micro texture, never capped)."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x3C9A) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        return ((n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) * 0.333).astype(np.float32)

    return _cache(key, build)


def _rot(shape, deg):
    """Rotated (u, v) coordinate fields. Cached per (h, w, deg): _rot was the #1
    cost (two full-res 2048² multiply-adds per call, called many times per finish)."""
    h, w = shape[:2]
    key = ("rot", h, w, round(float(deg), 3))

    def build():
        y, x = get_mgrid((h, w))
        y = y.astype(np.float32); x = x.astype(np.float32)
        a = np.deg2rad(deg); ca, sa = np.cos(a), np.sin(a)
        return (x * ca + y * sa).astype(np.float32), (-x * sa + y * ca).astype(np.float32)

    return _cache(key, build)


def _to3(paint):
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].copy()
    return paint


def _blend(col, paint, mask):
    # `col` arrives already clipped + float32 from _finish / paint bodies.
    col = np.asarray(col, np.float32)
    # Fast path: full mask (the common car case) skips the per-pixel composite.
    if mask.min() >= 0.999:
        return col
    m = mask[:, :, None]
    return col * m + _to3(paint) * (1 - m)


def _finish(col_work, h, w, seed, grain_amt=0.05):
    """Upscale a work-resolution iridescent color to full res then stamp full-res
    micro grain on top. This keeps the heavy color math (body blend + thin film)
    at the work cap while the FINE detail (grain) stays crisp at full res."""
    col = _up(col_work, h, w) if (col_work.shape[0] != h or col_work.shape[1] != w) else col_work
    g = _grain((h, w), seed + 3)[:, :, None]
    col = col * (1.0 + grain_amt * (g - 0.5) * 2.0)
    return np.clip(col, 0, 1, out=col).astype(np.float32, copy=False)


def _pack_spec(M, R, CC):
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def _work_shape(shape, cap):
    """Return a (sh, sw) work resolution capped to `cap` on the long edge (or the
    original if already small). Smooth optical fields are built here then upscaled;
    the fine grain is always added back at full res, so detail is preserved."""
    h, w = shape[:2]
    if max(h, w) <= cap:
        return h, w
    sh = cap if h >= w else max(64, int(round(cap * h / w)))
    sw = cap if w >= h else max(64, int(round(cap * w / h)))
    return sh, sw


def _up(a, h, w):
    if a.shape[0] == h and a.shape[1] == w:
        return a.astype(np.float32)
    return _resize_array(a.astype(np.float32), h, w)


def _band_capped(shape, seed, deg, freq, warp_scales=(60, 130), warp_amp=20.0,
                 power=1.0, cap=1024):
    """A wavy parallel-contour band field (rotated `deg`, spatial frequency `freq`)
    built at a work cap then upscaled. This is plain band MATH — each finish chooses
    its own angle/frequency/warp/power to make its OWN motif; it is NOT a shared
    design template. Cached per parameter set."""
    h, w = shape[:2]
    key = ("band", h, w, int(seed), round(float(deg), 2), round(float(freq), 5),
           tuple(warp_scales), round(float(warp_amp), 2), round(float(power), 3))

    def build():
        sh, sw = _work_shape((h, w), cap)
        fs = h / float(sh)
        _u, v = _rot((sh, sw), deg)
        warp = (_noise((sh, sw), list(warp_scales), [0.6, 0.4], seed, cap=900) - 0.5) * warp_amp
        b = 0.5 + 0.5 * np.sin((v + warp) * freq * fs)
        b = np.clip(b ** power, 0, 1)
        return _up(b, h, w)

    return _cache(key, build)


# =====================================================================
# 1) LABRADORITE — broad anisotropic SCHILLER FLASH PLANES (blue/gold).
#    Twin-lamellae cleavage planes catch light in big oriented sheets. The
#    flash is BLUE↔GOLD (interference order ~1.5), the body is dark gray.
# =====================================================================
def _labr_fields(shape, seed):
    """Returns (plane, flash, body). plane = which cleavage lamella you are in,
    flash = how strongly that lamella catches the schiller (angle gate), body =
    micro grain. All from one seed so the spec traces the paint."""
    h, w = shape[:2]
    key = ("labr", h, w, int(seed))

    def build():
        sh, sw = _work_shape((h, w), 1100)
        fs = h / float(sh)                                    # frequency rescale for upscale
        # cleavage lamellae: one dominant direction, slightly warped — broad PLANES
        u, v = _rot((sh, sw), 28.0)
        warp = (_noise((sh, sw), [180, 380], [0.6, 0.4], seed + 1, cap=900) - 0.5) * 90.0
        lam = 0.5 + 0.5 * np.sin((v + warp) * 0.018 * fs)     # broad lamellae bands
        lam = lam ** 1.4
        # flash domains: large smooth zones that light up (where lamellae face you)
        dom = _norm01(_noise((sh, sw), [220, 460], [0.6, 0.4], seed + 2, cap=900))
        flash = np.clip((dom - 0.34) * 2.1, 0, 1) * lam       # gated by lamella facing
        return _up(lam, h, w), _up(flash, h, w)

    return _cache(key, build)


def paint_labradorite(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    lam, flash = _labr_fields((h, w), seed)
    sh, sw = _work_shape((h, w), 896)
    lm = _resize_array(lam, sh, sw); fl = _resize_array(flash, sh, sw)
    body = np.empty((sh, sw, 3), np.float32); body[:] = (0.10, 0.115, 0.145)   # dark gray-blue
    # blue↔gold schiller: thin film at low orders gives exactly that pair
    film = np.asarray(interference_palette(0.30 + 0.42 * lm, orders=1.5,
                                           quantize=0.45, brightness=1.18), np.float32)
    fstr = (fl ** 1.1)[:, :, None]
    col = body * (1 - fstr) + film * fstr
    return _blend(_finish(col, h, w, seed, 0.05), paint, mask)


def spec_labradorite(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    lam, flash = _labr_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # second decorrelated field: a perpendicular cleavage set (different geometry)
    cross = _band_capped((h, w), seed + 88, 28.0 + 90.0, 0.020, (90, 200), 30.0, 1.0)
    # M ignites on the flashing planes (big oriented sheets), straddling 120.
    M = 70 + 185 * np.clip(flash * sm, 0, 1.0)
    # R rides the PERPENDICULAR set (different geometry), straddling 120 broadly.
    R = 60 + 130 * cross - 40 * flash + 18 * (g - 0.5) * 2.0 * sm
    # CC rides the lamella band itself (third field) and crosses 120 on lit lamellae.
    CC = 30 + 200 * (lam ** 1.5) * (0.45 + 0.55 * (1 - flash))
    return _pack_spec(M, R, CC)


# =====================================================================
# 2) SPECTROLITE — FULL-SPECTRUM labradorite. Distinct algorithm: THREE
#    intersecting plane sets at different angles, each lit by its own domain,
#    blended into a violent multi-order rainbow. More hues, more flash.
# =====================================================================
def _spectro_fields(shape, seed):
    h, w = shape[:2]
    key = ("spectro", h, w, int(seed))

    def build():
        sh, sw = _work_shape((h, w), 860)
        fs = h / float(sh)
        angs = (12.0, 67.0, 119.0)
        freqs = (0.024, 0.031, 0.019)
        thick = np.zeros((sh, sw), np.float32)
        flash = np.zeros((sh, sw), np.float32)
        for i, (ang, fr) in enumerate(zip(angs, freqs)):
            _u, v = _rot((sh, sw), ang)
            warp = (_noise((sh, sw), [120, 260], [0.6, 0.4], seed + 10 + i, cap=900) - 0.5) * 70.0
            band = 0.5 + 0.5 * np.sin((v + warp) * fr * fs)
            dom = _norm01(_noise((sh, sw), [200, 420], [0.6, 0.4], seed + 20 + i, cap=900))
            lit = np.clip((dom - 0.45) * 2.4, 0, 1) * (band ** 1.3)
            thick += band * (0.45 + 0.55 * lit)               # thickness gets richer where lit
            flash = np.maximum(flash, lit)                    # take the strongest plane set
        thick = _norm01(thick)
        return _up(thick, h, w), _up(np.clip(flash, 0, 1), h, w)

    return _cache(key, build)


def paint_spectrolite(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    thick, flash = _spectro_fields((h, w), seed)
    sh, sw = _work_shape((h, w), 896)
    th = _resize_array(thick, sh, sw); fl = _resize_array(flash, sh, sw)
    body = np.empty((sh, sw, 3), np.float32); body[:] = (0.055, 0.06, 0.085)   # near-black body
    # high interference orders => the FULL spectrum (more hues than labradorite)
    film = np.asarray(interference_palette(th, orders=4.2, quantize=0.34, brightness=1.32), np.float32)
    fstr = (0.20 + 0.80 * fl)[:, :, None]                     # more violent: even dim areas glow
    col = body * (1 - fstr) + film * fstr
    return _blend(_finish(col, h, w, seed, 0.06), paint, mask)


def spec_spectrolite(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    thick, flash = _spectro_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # M chases the violent flash (near-chrome on the brightest plane crossings).
    M = 26 + 224 * np.clip(flash ** 0.85 * sm, 0, 1.05)
    # R rides the thickness ORDER fraction (sawtooth) — fine independent banding.
    order_frac = (thick * 4.2) % 1.0
    R = 70 + 70 * order_frac - 40 * flash + 18 * (g - 0.5) * 2.0 * sm
    # CC rides a phase-shifted thickness so CC peaks where M does NOT — extra hues.
    CC = 18 + 150 * (0.5 + 0.5 * np.cos(thick * 4.2 * 2 * np.pi + 2.1)) * (0.5 + 0.5 * (1 - flash))
    return _pack_spec(M, R, CC)


# =====================================================================
# 3) AMMOLITE — cracked fossil-shell rainbow PLATES. Voronoi plates, each a
#    SOLID iridescent hue (whole-plate color, NOT per-pixel sparkle), with
#    HEAVY dark mineral seams. Deliberately different from black_opal (which
#    is sparse point flecks on black).
# =====================================================================
def _ammo_plates(shape, seed):
    """Voronoi: per-plate id (one hue per plate) + thick crack-seam mask + a slow
    within-plate gradient so each plate has a little roll of color."""
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("ammo", h, w, int(seed))

    def build():
        work = 820
        sh = work if h >= w else max(64, int(round(work * h / w)))
        sw = work if w >= h else max(64, int(round(work * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        rng = np.random.default_rng((int(seed) ^ 0x55C1) & 0xFFFFFFFF)
        n = 360                                               # many small fossil plates
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        hue = rng.random(n).astype(np.float32)                # each plate its own hue seed
        gx = rng.uniform(-1, 1, n).astype(np.float32)         # plate's color-roll direction
        gy = rng.uniform(-1, 1, n).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        grid = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32)
        d, idx = cKDTree(pts).query(grid, k=2, workers=-1)
        near = idx[:, 0]
        plate = hue[near].reshape(sh, sw)
        # within-plate gradient: dot of (pixel - centroid) with plate direction
        dy = (yy.ravel() - pts[near, 0]) * gy[near]
        dx = (xx.ravel() - pts[near, 1]) * gx[near]
        roll = _norm01((dy + dx).reshape(sh, sw))
        seam = np.clip(1.0 - (d[:, 1] - d[:, 0]).reshape(sh, sw) / 2.2, 0, 1) ** 1.6
        if (sh, sw) != (h, w):
            plate = _resize_array(plate.astype(np.float32), h, w)
            roll = _resize_array(roll.astype(np.float32), h, w)
            seam = _resize_array(seam.astype(np.float32), h, w)
        return plate.astype(np.float32), roll.astype(np.float32), seam.astype(np.float32)

    return _cache(key, build)


def paint_ammolite(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    plate, roll, seam = _ammo_plates((h, w), seed)
    # composite at the film work cap; seams stay as crisp as the plate upscale allows
    sh, sw = _work_shape((h, w), 896)
    pl = _resize_array(plate, sh, sw); rl = _resize_array(roll, sh, sw); sm_ = _resize_array(seam, sh, sw)
    thick = (pl * 0.9 + rl * 0.18) % 1.0
    film = np.asarray(interference_palette(thick, orders=1.0, quantize=0.0, brightness=1.28), np.float32)
    base = np.empty((sh, sw, 3), np.float32); base[:] = (0.06, 0.05, 0.045)
    col = base * 0.1 + film * 0.95
    col = col * (1 - sm_[:, :, None] * 0.96)                  # heavy black mineral seams
    return _blend(_up(col, h, w), paint, mask)


def spec_ammolite(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    plate, roll, seam = _ammo_plates((h, w), seed)
    g = _grain((h, w), seed + 3)
    # M: whole plates are mirror-bright shell nacre; seams are dead (anti-traces seam).
    M = (60 + 190 * (0.50 + 0.50 * roll)) * (1 - 0.85 * seam) * np.clip(0.55 + 0.55 * sm, 0, 1.3)
    # R: roughness rides plate-PARITY (a high-freq function of the plate hue id) + grain,
    # which is uncorrelated with M's smooth roll/seam product. Straddles 120.
    parity = 0.5 + 0.5 * np.sin(plate * 23.0 + 1.3)
    R = 55 + 130 * parity + 18 * (g - 0.5) * 2.0 * sm
    # CC: clearcoat pools per-plate by a DIFFERENT hue parity so adjacent plates differ.
    CC = 28 + 200 * (0.5 + 0.5 * np.sin(plate * 11.0 + roll * 4.0))
    return _pack_spec(M, R, CC)


# =====================================================================
# 4) TIGER EYE — fine chatoyant SILK FIBRE bands. Tightly packed parallel
#    fibres (very fine) with a broad sweeping cat's-eye sheen across them.
# =====================================================================
def _tiger_fields(shape, seed):
    h, w = shape[:2]
    key = ("tiger", h, w, int(seed))

    def build():
        sh, sw = _work_shape((h, w), 1280)               # high cap: fibres stay fine
        fs = h / float(sh)
        u, v = _rot((sh, sw), 18.0)
        warp = (_noise((sh, sw), [50, 110], [0.6, 0.4], seed + 1, cap=900) - 0.5) * 10.0
        # fine fibres along u (tight frequency -> crisp silk)
        fibre = 0.5 + 0.5 * np.sin(u * 0.85 * fs + warp)
        fibre = np.clip(fibre ** 1.6 * 1.3, 0, 1)
        # broad cat's-eye sheen sweeping across v (one soft bright lane)
        lane = np.clip(1.0 - np.abs(((v / (sh * 0.55)) % 1.0) - 0.5) * 1.7, 0, 1)
        return _up(fibre, h, w), _up(lane, h, w)

    return _cache(key, build)


def paint_tiger_eye(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    fibre, lane = _tiger_fields((h, w), seed)
    gold = np.array([0.80, 0.53, 0.13], np.float32)
    dark = np.array([0.24, 0.13, 0.04], np.float32)
    col = dark[None, None, :] + (gold - dark)[None, None, :] * (0.35 + 0.65 * fibre)[:, :, None]
    sheen = (lane * fibre)[:, :, None] * np.array([0.55, 0.40, 0.14], np.float32)
    col = np.clip(col + sheen, 0, 1)
    return _blend(col, paint, mask)


def spec_tiger_eye(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    fibre, lane = _tiger_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # cross-fibre weave (perpendicular ripple) — spatially distinct from the silk
    # fibre that drives M, built at the work cap (it only needs to straddle 120).
    weave = _band_capped((h, w), seed + 91, 18.0 + 90.0, 0.16, (40, 90), 18.0, 1.0)
    # M ignites the silk where the cat's-eye lane crosses bright fibres.
    M = 55 + 185 * np.clip((0.3 + 0.7 * lane) * fibre * sm, 0, 1.0)
    # R rides the perpendicular weave (independent geometry), straddling 120.
    R = 55 + 130 * weave + 18 * (g - 0.5) * 2.0 * sm
    # CC pools along the broad lane, crossing 120 inside the cat's-eye -> amber/teal zone.
    CC = 22 + 180 * (lane ** 1.4) * (0.5 + 0.5 * (1 - fibre))
    return _pack_spec(M, R, CC)


# =====================================================================
# 5) DICHROIC GLASS — RETHOUGHT. Flowing fine thin-film interference SHEETS.
#    Domain-warped flow streamlines carry continuously varying optical
#    thickness, so the color SWEEPS smoothly along ribbons (NOT blocky voronoi).
# =====================================================================
def _dichro_flow(shape, seed):
    """A smooth flow potential + a domain-warped thickness that streams along it.
    Returns (thickness, sheet_edge) where sheet_edge highlights the thin bright
    transition lines between film orders (the dichroic 'rim')."""
    h, w = shape[:2]
    key = ("dichro", h, w, int(seed))

    def build():
        sh, sw = _work_shape((h, w), 1100)
        fs = h / float(sh)
        # two warp fields push the coordinate around -> flowing sheets
        wx = (_noise((sh, sw), [90, 200], [0.6, 0.4], seed + 1, cap=900) - 0.5)
        wy = (_noise((sh, sw), [90, 200], [0.6, 0.4], seed + 2, cap=900) - 0.5)
        u, v = _rot((sh, sw), 40.0)
        # thickness streams along u, dragged by the warp -> long flowing ribbons
        thick = 0.5 + 0.5 * np.sin((u * 0.012 * fs + wx * 7.0) + np.cos(v * 0.010 * fs + wy * 7.0))
        thick = _norm01(thick)
        # bright rim where the film order flips fast (gradient of thickness)
        gy_, gx_ = np.gradient(thick.astype(np.float32))
        edge = _norm01(np.sqrt(gx_ * gx_ + gy_ * gy_))
        edge = np.clip(edge * 2.2, 0, 1)
        return _up(thick, h, w), _up(edge, h, w)

    return _cache(key, build)


def paint_dichroic_glass(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    thick, edge = _dichro_flow((h, w), seed)
    sh, sw = _work_shape((h, w), 896)
    th = _resize_array(thick, sh, sw); ed = _resize_array(edge, sh, sw)
    # smooth (low quantize) thin-film that flows -> continuous magenta/cyan/gold sheets
    film = np.asarray(interference_palette(th, orders=3.0, quantize=0.12, brightness=1.30), np.float32)
    # the bright transition rim reads as the glass catching light along the sheet edge
    col = film + ed[:, :, None] * np.array([0.30, 0.34, 0.42], np.float32)
    return _blend(_finish(col, h, w, seed, 0.04), paint, mask)


def spec_dichroic_glass(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    thick, edge = _dichro_flow((h, w), seed)
    # M is high+flowing (glass is reflective) and SPIKES on the sheet-edge rims;
    # the order phase drives it up and down so M itself straddles 120.
    M = 95 + 120 * edge + 60 * np.sin(thick * 3.0 * 2 * np.pi)
    M = np.clip(M * (0.6 + 0.5 * sm), 0, 255)
    # R rides a SECOND, separate flow field (a perpendicular sheet set) so its bright
    # zones sit off the M/CC ribbons -> R crosses 120 in its own territory.
    flowR = _band_capped((h, w), seed + 77, 40.0, 0.013, (90, 200), 16.0, 1.0)
    R = 40 + 150 * flowR - 30 * edge
    # CC sweeps with raw thickness (different phase than M) -> blue/teal cast where M is mid.
    CC = 26 + 200 * (0.5 + 0.5 * np.cos(thick * 3.0 * 2 * np.pi + 1.7))
    return _pack_spec(M, R, CC)


# =====================================================================
# 6) FIRE AGATE — stacked concentric RED-ORANGE IRIS DOMES (botryoidal).
#    Layered hemispherical domes; thin iridescent film between layers gives
#    the famous red/orange/green fire trapped under the dome surface.
# =====================================================================
def _fire_domes(shape, seed):
    """Several overlapping domes; for each pixel return the LAYER index (which
    concentric shell it sits on, fine) and the dome-facing term (center = bright)."""
    h, w = shape[:2]
    key = ("fire", h, w, int(seed))

    def build():
        work = 680
        sh = work if h >= w else max(64, int(round(work * h / w)))
        sw = work if w >= h else max(64, int(round(work * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        fscale = h / float(sh)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x7711) & 0xFFFFFFFF)
        ncenters = 9
        dmin = np.full((sh, sw), 1e9, np.float32)
        facing = np.zeros((sh, sw), np.float32)
        for _ in range(ncenters):
            cy = rng.uniform(0, sh); cx = rng.uniform(0, sw)
            rad = rng.uniform(sh * 0.10, sh * 0.26)
            d = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
            closer = d < dmin
            dmin = np.where(closer, d, dmin)
            facing = np.where(closer, np.clip(1.0 - d / rad, 0, 1) ** 0.6, facing)
        warp = (np.asarray(multi_scale_noise((sh, sw), [40, 90], [0.6, 0.4], seed + 5), np.float32) - 0.5) * 14.0
        # fine concentric shells (the layered iris films)
        shells = 0.5 + 0.5 * np.sin(dmin * 0.42 * fscale + warp)
        layer = shells ** 1.3
        if (sh, sw) != (h, w):
            layer = _resize_array(layer, h, w)
            facing = _resize_array(facing, h, w)
        return layer.astype(np.float32), facing.astype(np.float32)

    return _cache(key, build)


def paint_fire_agate(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    layer, facing = _fire_domes((h, w), seed)
    # composite the smooth optical color at the work cap, then upscale + full-res grain
    sh, sw = _work_shape((h, w), 896)
    lay = _resize_array(layer, sh, sw); fac = _resize_array(facing, sh, sw)
    body = np.empty((sh, sw, 3), np.float32); body[:] = (0.30, 0.12, 0.05)   # warm chalcedony
    film = np.asarray(interference_palette(0.10 + 0.55 * lay, orders=2.2, quantize=0.30,
                                           brightness=1.2, base_srgb=(1.0, 0.66, 0.34)), np.float32)
    fire = (fac * (0.4 + 0.6 * lay))[:, :, None]              # fire strongest at dome centers
    col = body * (1 - fire) + film * fire
    return _blend(_finish(col, h, w, seed, 0.05), paint, mask)


def spec_fire_agate(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    layer, facing = _fire_domes((h, w), seed)
    g = _grain((h, w), seed + 3)
    # independent chalcedony body field (broad blotches not tied to the domes)
    body = _norm01(_noise((h, w), [90, 200], [0.6, 0.4], seed + 33, cap=900))
    # M ignites the dome fire (centers + bright shells), straddling 120.
    M = 45 + 195 * np.clip(facing * (0.35 + 0.65 * layer) * sm, 0, 1.0)
    # R rides the body blotch field (its own geometry), straddling 120.
    R = 50 + 140 * body + 20 * (g - 0.5) * 2.0 * sm
    # CC pulses on the concentric shells EVERYWHERE (not gated by facing) -> green/teal
    # cast appears across the whole stone, decorrelated from the dome-gated M.
    CC = 28 + 200 * (layer ** 1.4)
    return _pack_spec(M, R, CC)


# =====================================================================
# 7) MALACHITE — banded green EYES. Concentric malachite rings with sharp
#    light/dark green banding (its own concentric algorithm, distinct from
#    fire_agate's facing domes).
# =====================================================================
def _mala_bands(shape, seed):
    h, w = shape[:2]
    key = ("mala", h, w, int(seed))

    def build():
        work = 820
        sh = work if h >= w else max(64, int(round(work * h / w)))
        sw = work if w >= h else max(64, int(round(work * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        fscale = h / float(sh)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x2EE3) & 0xFFFFFFFF)
        acc = np.full((sh, sw), 1e9, np.float32)
        for _ in range(7):
            cy = rng.uniform(0, sh); cx = rng.uniform(0, sw)
            acc = np.minimum(acc, np.sqrt((y - cy) ** 2 + (x - cx) ** 2))
        warp = (np.asarray(multi_scale_noise((sh, sw), [40, 90], [0.55, 0.45], seed + 7), np.float32) - 0.5) * 16.0
        # sharper banding than fire (malachite has crisp concentric stripes)
        bands = 0.5 + 0.5 * np.sin(acc * 0.30 * fscale + warp)
        bands = np.clip((bands - 0.5) * 1.8 + 0.5, 0, 1)
        if (sh, sw) != (h, w):
            bands = _resize_array(bands, h, w)
        return bands.astype(np.float32)

    return _cache(key, build)


def paint_malachite(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    bands = _mala_bands((h, w), seed)
    dark = np.array([0.02, 0.16, 0.07], np.float32)
    light = np.array([0.32, 0.74, 0.43], np.float32)
    col = dark[None, None, :] + (light - dark)[None, None, :] * bands[:, :, None]
    g = _grain((h, w), seed + 3)[:, :, None]
    col = np.clip(col * (1.0 + 0.05 * (g - 0.5) * 2.0), 0, 1)
    return _blend(col, paint, mask)


def spec_malachite(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    bands = _mala_bands((h, w), seed)
    g = _grain((h, w), seed + 3)
    # M: light green bands are polished/satin-bright; dark bands dull (straddles 120).
    M = 40 + 170 * np.clip(bands * sm, 0, 1.0)
    # R: roughness rides the band EDGES (band gradient), not the band value -> decorrelated.
    gy_, gx_ = np.gradient(bands.astype(np.float32))
    edge = _norm01(np.sqrt(gx_ * gx_ + gy_ * gy_))
    R = 55 + 150 * edge + 20 * (g - 0.5) * 2.0 * sm
    # CC: a SEPARATE broad blotch field (botryoidal lobes), NOT (1-bands), so it does
    # not anti-correlate with M. Crosses 120 in its own territory -> extra hues.
    lobe = _norm01(_noise((h, w), [120, 260], [0.6, 0.4], seed + 41, cap=820))
    CC = 28 + 200 * lobe ** 1.2
    return _pack_spec(M, R, CC)


# =====================================================================
# 8) AZURITE — deep-blue wavy CONTOUR bands + crystalline glints. Parallel
#    wavy contours (its own field, distinct from malachite's rings) studded
#    with sharp little crystal sparkles.
# =====================================================================
def _azur_fields(shape, seed):
    h, w = shape[:2]
    key = ("azur", h, w, int(seed))

    def build():
        bands = _band_capped((h, w), seed + 7, 24.0, 0.045, (60, 130), 26.0, 1.3)
        # crystalline glints: sharp sparse points (full-res for crispness)
        spk = _grain((h, w), seed + 5)
        glint = (spk > 0.965).astype(np.float32)
        return bands.astype(np.float32), glint.astype(np.float32)

    return _cache(key, build)


def paint_azurite(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    bands, glint = _azur_fields((h, w), seed)
    dark = np.array([0.02, 0.05, 0.24], np.float32)
    light = np.array([0.16, 0.34, 0.88], np.float32)
    col = dark[None, None, :] + (light - dark)[None, None, :] * bands[:, :, None]
    col = np.clip(col + glint[:, :, None] * np.array([0.5, 0.6, 0.95], np.float32) * 0.55, 0, 1)
    g = _grain((h, w), seed + 3)[:, :, None]
    col = np.clip(col * (1.0 + 0.04 * (g - 0.5) * 2.0), 0, 1)
    return _blend(col, paint, mask)


def spec_azurite(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    bands, glint = _azur_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # M: crystal glints fire near-chrome over a low body; band adds only a touch.
    M = 45 + 45 * bands + 205 * glint
    M = np.clip(M * (0.6 + 0.5 * sm), 0, 255)
    # R: rides an INDEPENDENT broad blotch field (mineral coarseness), straddling 120;
    # glints knock it down so flecks stay slick (light decorrelation from M's glint).
    coarse = _norm01(_noise((h, w), [70, 160], [0.6, 0.4], seed + 52, cap=1000))
    R = 60 + 130 * coarse + 22 * (g - 0.5) * 2.0 * sm - 60 * glint
    # CC: a SEPARATE crossing contour set (different angle) so CC's high zones are
    # spatially offset from M and R -> blues/teals via channel math.
    cc_band = _band_capped((h, w), seed + 81, 24.0 + 70.0, 0.05, (50, 110), 30.0, 1.3)
    CC = 28 + 200 * cc_band
    return _pack_spec(M, R, CC)


# =====================================================================
# 9) BLACK OPAL — SPARSE vivid play-of-color FLECKS (pinfire) on near-black.
#    Discrete scattered color SPLATS (point flecks), each its own hue, sitting
#    on an almost-black body. NOT plates, NOT cells — sparse points. This is
#    what separates it from ammolite's full rainbow plates.
# =====================================================================
def _opal_flecks(shape, seed):
    """Scatter sparse fleck splats at work-res; each fleck a small soft disc with
    its own hue. Returns (intensity, hue) full-res. Windowed splats = cheap."""
    h, w = shape[:2]
    key = ("opal", h, w, int(seed))

    def build():
        work = 1024
        sh = work if h >= w else max(64, int(round(work * h / w)))
        sw = work if w >= h else max(64, int(round(work * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        rng = np.random.default_rng((int(seed) ^ 0x09A1) & 0xFFFFFFFF)
        inten = np.zeros((sh, sw), np.float32)
        hue = np.zeros((sh, sw), np.float32)
        nfleck = 900                                          # sparse vivid flecks
        cy = rng.integers(0, sh, nfleck)
        cx = rng.integers(0, sw, nfleck)
        rad = rng.integers(2, 6, nfleck)                      # tiny pinfire
        hh = rng.random(nfleck).astype(np.float32)
        amp = rng.uniform(0.6, 1.0, nfleck).astype(np.float32)
        for i in range(nfleck):
            r = int(rad[i])
            y0 = max(0, cy[i] - r); y1 = min(sh, cy[i] + r + 1)
            x0 = max(0, cx[i] - r); x1 = min(sw, cx[i] + r + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            dd = ((yy - cy[i]) ** 2 + (xx - cx[i]) ** 2) / float(r * r + 1e-3)
            disc = np.clip(1.0 - dd, 0, 1) ** 1.4 * amp[i]
            win = inten[y0:y1, x0:x1]
            take = disc > win
            inten[y0:y1, x0:x1] = np.where(take, disc, win)
            hue[y0:y1, x0:x1] = np.where(take, hh[i], hue[y0:y1, x0:x1])
        if (sh, sw) != (h, w):
            inten = _resize_array(inten, h, w)
            hue = _resize_array(hue, h, w)
        return np.clip(inten, 0, 1).astype(np.float32), hue.astype(np.float32)

    return _cache(key, build)


def paint_black_opal(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    inten, hue = _opal_flecks((h, w), seed)
    body = np.empty((h, w, 3), np.float32); body[:] = (0.025, 0.025, 0.04)   # near-black
    # vivid saturated play-of-color: high-sat HSV per fleck hue
    r, g, b = hsv_to_rgb_vec(hue, np.full_like(hue, 0.95), np.full_like(hue, 1.0))
    fleck = np.stack([r, g, b], axis=-1).astype(np.float32)
    col = body + fleck * (inten[:, :, None] ** 0.8) * 1.25
    return _blend(col, paint, mask)


def spec_black_opal(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    inten, hue = _opal_flecks((h, w), seed)
    g = _grain((h, w), seed + 3)
    # The near-black BODY is not dead in the spec: it carries faint potch-color
    # marbling on three independent fields so the dark areas still show hue variety
    # in motion (the flecks then blaze on top). Each field crosses 120 somewhere.
    fA = _norm01(_noise((h, w), [80, 180], [0.6, 0.4], seed + 61, cap=1000))   # M body
    fB = _norm01(_noise((h, w), [55, 130], [0.6, 0.4], seed + 62, cap=1000))   # R body
    fC = _norm01(_noise((h, w), [110, 240], [0.6, 0.4], seed + 63, cap=900))   # CC body
    # M: flecks fire near-chrome; body has a low-mid metal marble that straddles 120.
    M = 60 + 110 * fA + 200 * np.clip(inten ** 0.7 * sm, 0, 1.0)
    # R: body roughness marble (own field), flecks knock it slick.
    R = 60 + 130 * fB + 18 * (g - 0.5) * 2.0 * sm - 120 * inten
    # CC: potch clearcoat marble (own field) PLUS a hue-keyed pool on flecks.
    CC = 30 + 160 * fC + 120 * (0.5 + 0.5 * np.sin(hue * 6.28 + 1.0)) * inten
    return _pack_spec(M, R, CC)


# =====================================================================
# 10) SUNSTONE — copper AVENTURESCENT schiller glitter in warm feldspar.
#     Dense fine metallic copper flakes (its own scatter) over a warm body
#     with a soft schiller wash. Distinct from opal's sparse vivid flecks:
#     here the flakes are MANY, fine, copper-monochrome, and directional.
# =====================================================================
def _sun_fields(shape, seed):
    """Copper flake intensity (dense fine) + a broad warm schiller wash."""
    h, w = shape[:2]
    key = ("sun", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0xA17C) & 0xFFFFFFFF)
        nflk = min(int(h * w * 0.035), 260000)
        flk = np.zeros((h, w), np.float32)
        yy = rng.integers(0, h, nflk); xx = rng.integers(0, w, nflk)
        flk[yy, xx] = rng.uniform(0.45, 1.0, nflk)
        # tiny directional smear so flakes catch a raking glint (aventurescence)
        flk = np.maximum.reduce([flk, np.roll(flk, 1, 0) * 0.5, np.roll(flk, 1, 1) * 0.5])
        wash = _norm01(_noise((h, w), [160, 340], [0.6, 0.4], seed + 9, cap=900))
        return np.clip(flk, 0, 1).astype(np.float32), wash.astype(np.float32)

    return _cache(key, build)


def paint_sunstone(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    flk, wash = _sun_fields((h, w), seed)
    base = np.empty((h, w, 3), np.float32); base[:] = (0.72, 0.37, 0.11)      # warm feldspar
    base = base * (0.74 + 0.42 * wash[:, :, None])           # soft schiller depth
    copper = np.array([1.0, 0.66, 0.30], np.float32)
    col = np.clip(base + flk[:, :, None] * copper * 0.75, 0, 1)
    return _blend(col, paint, mask)


def spec_sunstone(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    flk, wash = _sun_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # M: the copper flakes are the metal — dense bright points; body low-mid metal.
    M = 75 + 35 * wash + 170 * flk
    M = np.clip(M * (0.6 + 0.5 * sm), 0, 255)
    # R: feldspar body satin; rides the broad schiller wash + grain (not the flakes).
    R = 55 + 130 * wash - 30 * flk + 22 * (g - 0.5) * 2.0 * sm
    # CC: a SEPARATE warm-resin clearcoat field (own blotches), NOT (1-wash), so it is
    # decorrelated from R and adds an amber/teal cast in its own territory.
    resin = _norm01(_noise((h, w), [100, 220], [0.6, 0.4], seed + 71, cap=900))
    CC = 30 + 190 * resin ** 1.2
    return _pack_spec(M, R, CC)
