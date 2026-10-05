"""MATERIALS & PHYSICS ENGINE (2026-06-19) — total rework: real physical MATERIAL surfaces, not
gradient/exotic colour swaps.

Each structure is a different fabricated material with crushed-fine surface structure:
  - carbon_twill   : a true 2/2 twill carbon-fibre weave (over/under tows + fine fibre filaments)
  - forged_carbon  : marbled chopped-carbon composite (random-oriented flake shards in resin)
  - engine_turned  : machined "jeweling" / engine-turning (overlapping fine concentric brush swirls)
  - liquid_metal   : flowing chrome/mercury (reflective metaball surface + capillary ripples)

Colours stay material-honest (carbon black, steel/aluminium silver, chrome) — the drama comes from
the structure + the spec. Full-canvas, crushed-fine (tight weave / fine arcs / micro-ripples),
<3s @1152. Self-contained (numpy+cv2); reuses flame_math noise + gate helpers.
"""
from __future__ import annotations
import numpy as np
import cv2

from engine.paint_v2.flame_math import _fbm, _norm, _rng


def _coords(shape):
    H, W = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return H, W, xx, yy


def _tint(gray, lo, hi):
    """Map a 0..1 gray field to a colour ramp lo->hi (both RGB tuples)."""
    lo = np.array(lo, np.float32); hi = np.array(hi, np.float32)
    g = np.clip(gray, 0, 1)[..., None]
    return lo[None, None, :] * (1 - g) + hi[None, None, :] * g


# ----------------------------------------------------------------------------- 1. carbon twill
def carbon_twill(shape, seed=7, cell=26):
    """A real 2/2 twill carbon-fibre weave: warp/weft tows interlace with the diagonal twill rib,
    each tow rounded (cylinder shading) and threaded with fine carbon filaments. Crushed-fine."""
    H, W, xx, yy = _coords(shape)
    gx = np.floor(xx / cell).astype(np.int32)
    gy = np.floor(yy / cell).astype(np.int32)
    # 2/2 twill: warp-on-top where ((gx+gy) mod 4) < 2, shifting one cell per row -> diagonal rib
    twill = (((gx + gy) % 4) < 2)
    fx = (xx / cell) % 1.0
    fy = (yy / cell) % 1.0
    # rounded cylinder shading across each tow (bright crown, dark seam)
    crown_w = np.sin(np.pi * fy)          # weft tow rounded along y
    crown_h = np.sin(np.pi * fx)          # warp tow rounded along x
    crown = np.where(twill, crown_h, crown_w)
    # fine carbon filaments running ALONG each tow (very fine striations -> the 25%-finer detail)
    fil_h = 0.5 + 0.5 * np.cos(yy * (2 * np.pi / 3.0))   # warp tow: filaments run vertical
    fil_w = 0.5 + 0.5 * np.cos(xx * (2 * np.pi / 3.0))   # weft tow: filaments run horizontal
    fil = np.where(twill, fil_h, fil_w)
    base = 0.10 + 0.42 * np.clip(crown, 0, 1)            # tow crown brightness
    base = base * (0.78 + 0.22 * fil)                    # filament micro-modulation
    # anisotropic sheen: tows on top catch a cool sheen
    sheen = np.clip(crown, 0, 1) ** 2 * np.where(twill, 0.22, 0.16)
    img = _tint(base, (0.015, 0.02, 0.03), (0.30, 0.34, 0.42)) + sheen[..., None] * np.array([0.5, 0.6, 0.8], np.float32)
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 2. forged carbon
def forged_carbon(shape, seed=7, regions=260):
    """Marbled forged-carbon composite — chopped flake shards at random orientations set in resin,
    each shard catching the light along its own fibre direction. Full-canvas marble of silver/black."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    from scipy.spatial import cKDTree
    pts = np.stack([rng.random(regions) * W, rng.random(regions) * H], 1).astype(np.float32)
    ang = rng.random(regions).astype(np.float32) * np.pi
    tree = cKDTree(pts)
    grid = np.stack([xx.ravel(), yy.ravel()], 1)
    _, idx = tree.query(grid, k=1)                      # nearest shard per pixel (fast)
    lab = idx.reshape(H, W).astype(np.int32)
    shard_ang = ang[lab]
    bright = 0.25 + 0.6 * _norm(_fbm((H, W), seed + 3, octaves=4, freq=9.0))   # per-area flake luma
    # fine fibre striations along each shard's own angle (crushed-fine)
    u = xx * np.cos(shard_ang) + yy * np.sin(shard_ang)
    fibre = 0.5 + 0.5 * np.cos(u * (2 * np.pi / 3.2))
    flake = bright * (0.68 + 0.32 * fibre)
    # micro flake glints — random bright specks within shards (the carbon sparkle)
    glint = (_fbm((H, W), seed + 14, octaves=2, freq=150.0) > 0.86).astype(np.float32)
    flake = flake + 0.35 * glint * (0.4 + 0.6 * fibre)
    # resin seams between shards (dark glossy boundaries)
    edge = (cv2.Laplacian(lab.astype(np.float32), cv2.CV_32F, ksize=3) != 0).astype(np.float32)
    edge = cv2.GaussianBlur(edge, (0, 0), 0.8)
    flake = flake * (1.0 - 0.6 * np.clip(edge, 0, 1))
    img = _tint(np.clip(flake, 0, 1), (0.02, 0.02, 0.03), (0.66, 0.70, 0.78))
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 3. engine turning
def engine_turned(shape, seed=7, cols=12):
    """Machined 'jeweling' / engine-turning: a grid of overlapping circular brush swirls, each a set
    of fine concentric arcs with a directional metal highlight. Full-canvas precision-metal."""
    H, W, xx, yy = _coords(shape)
    step = W / cols
    sv = step * 0.6
    # analytic nearest brick-grid centre (NO per-spot loop): each pixel belongs to one swirl, bounded
    # by the centres' Voronoi -> the classic overlapping engine-turned tiling.
    rf = yy / sv
    best_d = np.full((H, W), 1e18, np.float32)
    bdx = np.zeros((H, W), np.float32); bdy = np.zeros((H, W), np.float32)
    for rr in (np.floor(rf), np.floor(rf) + 1):
        r_int = rr.astype(np.int32)
        off = np.where((r_int % 2) != 0, step * 0.5, 0.0).astype(np.float32)
        cyc = rr * sv
        cxc = np.round((xx - off) / step) * step + off
        dx, dy = xx - cxc, yy - cyc
        d2 = dx * dx + dy * dy
        take = d2 < best_d
        best_d = np.where(take, d2, best_d)
        bdx = np.where(take, dx, bdx); bdy = np.where(take, dy, bdy)
    d = np.sqrt(best_d)
    arc = 0.5 + 0.5 * np.cos(d * (2 * np.pi / 5.0))      # concentric brush rings (visible circles)
    fine = 0.5 + 0.5 * np.cos(d * (2 * np.pi / 2.6))     # crushed-fine micro tool marks
    th = np.arctan2(bdy, bdx)
    hi = 0.5 + 0.5 * np.cos(th - 0.7)                    # directional swirl highlight per spot
    dome = np.exp(-best_d / (2 * (0.42 * step) ** 2))    # raised circular jewel per spot
    val = (0.30 + 0.45 * arc) * (0.6 + 0.45 * hi) * (0.55 + 0.55 * dome) * (0.85 + 0.15 * fine)
    val = 0.26 + 0.68 * _norm(val)
    img = _tint(val, (0.10, 0.11, 0.13), (0.88, 0.91, 0.97))   # aluminium / steel
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 4. liquid metal
def liquid_metal(shape, seed=7):
    """Flowing chrome / mercury: a smooth reflective metaball surface whose normal samples a bright
    environment, pooling into merging blobs with fine capillary ripples. Mirror-bright + dark."""
    H, W, xx, yy = _coords(shape)
    # surface height = smooth blobs + fine ripples
    h = _fbm((H, W), seed, octaves=4, freq=3.2)
    h = h + 0.10 * _fbm((H, W), seed + 7, octaves=3, freq=22.0)    # capillary micro-ripples (fine)
    h = cv2.GaussianBlur(h, (0, 0), 1.0)
    nx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=5)
    ny = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=5)
    # reflect a banded chrome environment by the surface slope (sharp light/dark mirror bands)
    refl = np.sin((nx * 9.0 + ny * 5.0) * 3.0) * 0.5 + 0.5
    env = np.clip(np.power(refl, 1.6), 0, 1)
    # bright specular streaks where slope aligns with the key light
    spec = np.clip(1.0 - np.abs(nx * 4.0 - 0.3), 0, 1) ** 3
    val = 0.18 + 0.62 * env + 0.5 * spec
    img = _tint(np.clip(val, 0, 1), (0.04, 0.05, 0.08), (0.92, 0.95, 1.0))  # chrome blue-white
    # a touch of cool tint in the mid reflections
    img[..., 2] = np.clip(img[..., 2] * 1.05, 0, 1)
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 5. crystal lattice
def crystal_lattice(shape, seed=7, sites=520):
    """A bed of grown mineral crystals — a dense Voronoi of faceted grains, each face shaded by its
    own slope (3D read) with bright cleavage edges and pin-point glints. Druzy geode, full-canvas."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    from scipy.spatial import cKDTree
    pts = np.stack([rng.random(sites) * W, rng.random(sites) * H], 1).astype(np.float32)
    grid = np.stack([xx.ravel(), yy.ravel()], 1)
    dd, idx = tree_q = cKDTree(pts).query(grid, k=2)        # k=2 -> F1,F2 for crisp facet edges
    f1 = dd[:, 0].reshape(H, W); f2 = dd[:, 1].reshape(H, W)
    lab = idx[:, 0].reshape(H, W)
    # each grain a random brightness + a directional facet slope so it reads as a 3D crystal face
    gb = (0.30 + 0.55 * rng.random(sites))[lab]
    ga = (rng.random(sites) * 2 * np.pi)[lab]
    slope = np.cos(ga) * (xx - pts[lab, 0]) + np.sin(ga) * (yy - pts[lab, 1])
    face = gb * (0.7 + 0.012 * slope)
    edge = np.clip(1.0 - (f2 - f1) * 0.6, 0, 1) ** 3                       # bright cleavage seams
    glint = (np.abs(f2 - f1) < 0.6).astype(np.float32) * (gb > 0.7)        # sparkle at triple points
    val = np.clip(face * (1.0 + 0.5 * edge) + 0.6 * glint, 0, 1)
    img = _tint(val, (0.05, 0.05, 0.08), (0.74, 0.80, 0.92))               # quartz/amethyst silver
    img[..., 2] = np.clip(img[..., 2] * 1.06 + 0.04 * edge, 0, 1)          # cool crystalline cast
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 6. ferrofluid spikes
def ferrofluid(shape, seed=7):
    """Ferrofluid under a magnetic field — the Rosensweig instability: a lattice of liquid-iron
    spikes, each a peaked black mound with a glossy specular cap. Hexagonal spike packing, fine."""
    H, W, xx, yy = _coords(shape)
    # warped hex-ish lattice of spike centres via cosine sum -> peak field, then sharpen to spikes
    warp = 22.0 * _fbm((H, W), seed + 2, octaves=3, freq=3.0)
    u = (xx + warp) / W * np.pi * 26.0
    v = (yy + warp) / H * np.pi * 26.0
    field = (np.cos(u) + np.cos(0.5 * u + 0.866 * v) + np.cos(-0.5 * u + 0.866 * v))   # hex lattice
    # low-freq height envelope -> spikes cluster into tall ridges + low fields (not uniform polka-dots)
    env = 0.45 + 0.85 * _norm(_fbm((H, W), seed + 12, octaves=3, freq=2.2))
    peaks = _norm(np.clip(field, 0, None)) * env
    spike = np.power(_norm(peaks), 1.8)                                   # sharpen into spikes
    # 3D cone read: dark iron body lifted off black + bright specular cap on the lit (upper-left) flank
    nx = cv2.Sobel(spike, cv2.CV_32F, 1, 0, ksize=5)
    ny = cv2.Sobel(spike, cv2.CV_32F, 0, 1, ksize=5)
    cap = _norm(np.clip(-(nx * 0.6 + ny * 0.5), 0, None)) * spike
    micro = 0.5 + 0.5 * np.cos((u * 3.0) + (v * 3.0))                     # fine surface-tension ripples
    val = 0.04 + 0.30 * np.power(spike, 0.7) + 0.55 * spike + 1.05 * np.power(cap, 1.2)  # body + bright cap
    val = val * (0.92 + 0.08 * micro)
    img = _tint(np.clip(val, 0, 1), (0.01, 0.01, 0.02), (0.86, 0.88, 0.94))  # black iron -> bright steel cap
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 7. fracture net
def fracture_net(shape, seed=7, sites=300):
    """Fracture mechanics — a stressed brittle surface shattered into a crack network: the Voronoi
    boundaries are bright opened cracks, the cells are subtly tilted plates. Full-canvas craquelure."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    from scipy.spatial import cKDTree
    pts = np.stack([rng.random(sites) * W, rng.random(sites) * H], 1).astype(np.float32)
    grid = np.stack([xx.ravel(), yy.ravel()], 1)
    dd, idx = cKDTree(pts).query(grid, k=2)
    f1 = dd[:, 0].reshape(H, W); f2 = dd[:, 1].reshape(H, W)
    lab = idx[:, 0].reshape(H, W)
    plate = (0.35 + 0.4 * rng.random(sites))[lab]                         # each plate a flat tone
    plate = plate * (0.85 + 0.15 * _norm(_fbm((H, W), seed + 5, octaves=3, freq=40.0)))  # fine grain
    crack = (f2 - f1)
    crack_bright = np.clip(1.0 - crack * 0.5, 0, 1) ** 4                  # thin bright opened seams
    # secondary fine micro-cracks branching off (high-freq ridged noise gated to mid distances)
    micro = np.power(_norm(np.abs(_fbm((H, W), seed + 8, octaves=4, freq=70.0) - 0.5)), 6.0)
    val = plate * (1.0 - 0.55 * crack_bright) + 0.9 * crack_bright + 0.25 * micro
    img = _tint(np.clip(val, 0, 1), (0.03, 0.03, 0.04), (0.70, 0.72, 0.78))
    img = img + crack_bright[..., None] * np.array([0.10, 0.12, 0.16], np.float32)   # cool glow in cracks
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 8. damascus steel
def damascus_steel(shape, seed=7):
    """Pattern-welded Damascus steel — folded layers of light/dark steel ground back to reveal the
    classic flowing banded watermark. Domain-warped contour bands + fine etch grain, full-canvas."""
    H, W, xx, yy = _coords(shape)
    # base layered field warped by a flow so the bands swirl like ground-back forge folds
    fx = _fbm((H, W), seed + 1, octaves=4, freq=2.4)
    fy = _fbm((H, W), seed + 2, octaves=4, freq=2.4)
    warpx = np.clip(xx + (fx - 0.5) * 240.0, 0, W - 1).astype(np.float32)
    warpy = np.clip(yy + (fy - 0.5) * 240.0, 0, H - 1).astype(np.float32)
    layers = 0.5 + 0.5 * np.cos((warpx * 0.16 + warpy * 0.05))            # the folded layer bands
    layers = cv2.remap(layers, warpx, warpy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    bands = np.power(0.5 + 0.5 * np.cos(layers * 6.28 * 3.0), 1.4)        # crisp light/dark steel layers
    etch = 0.5 + 0.5 * np.cos((warpx + warpy) * 1.4)                      # fine acid-etch tooth
    val = 0.22 + 0.6 * bands + 0.12 * etch * bands
    img = _tint(np.clip(val, 0, 1), (0.07, 0.07, 0.08), (0.82, 0.83, 0.86))  # blued steel -> bright nickel
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 9. kevlar aramid
def kevlar_aramid(shape, seed=7, cell=30):
    """Golden aramid (Kevlar) BASKET weave — pairs of tows woven over/under two-at-a-time (distinct
    from the 2/2 twill's diagonal rib), each tow rounded with fine aramid filaments. Full-canvas."""
    H, W, xx, yy = _coords(shape)
    gx = np.floor(xx / cell).astype(np.int32)
    gy = np.floor(yy / cell).astype(np.int32)
    # 2x2 basket: warp-on-top in 2x2 blocks alternating (checkerboard of blocks, not a diagonal rib)
    warp = (((gx // 2) + (gy // 2)) % 2) == 0
    fx = (xx / cell) % 1.0
    fy = (yy / cell) % 1.0
    crown = np.where(warp, np.sin(np.pi * fx), np.sin(np.pi * fy))
    fil_w = 0.5 + 0.5 * np.cos(xx * (2 * np.pi / 2.6))   # warp tow: fine vertical filaments
    fil_h = 0.5 + 0.5 * np.cos(yy * (2 * np.pi / 2.6))
    fil = np.where(warp, fil_w, fil_h)
    base = 0.18 + 0.5 * np.clip(crown, 0, 1)
    base = base * (0.8 + 0.2 * fil)
    img = _tint(base, (0.05, 0.04, 0.01), (0.92, 0.74, 0.18))   # deep gold -> bright aramid yellow
    return np.clip(img, 0.0, 1.0).astype(np.float32)


_TI_STOPS = [(0.00, (0.55, 0.57, 0.60)), (0.22, (0.78, 0.66, 0.30)), (0.40, (0.62, 0.30, 0.55)),
             (0.55, (0.30, 0.32, 0.78)), (0.72, (0.20, 0.62, 0.85)), (0.88, (0.45, 0.82, 0.80)),
             (1.00, (0.85, 0.88, 0.95))]


def _ti_ramp(t):
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,), np.float32)
    for (a0, c0), (a1, c1) in zip(_TI_STOPS[:-1], _TI_STOPS[1:]):
        m = (t >= a0) & (t <= a1)
        f = (t[m] - a0) / max(1e-6, a1 - a0)
        c0a = np.array(c0, np.float32); c1a = np.array(c1, np.float32)
        out[m] = c0a[None, :] * (1 - f)[:, None] + c1a[None, :] * f[:, None]
    return out


# ----------------------------------------------------------------------------- 10. anodized titanium
def anodized_titanium(shape, seed=7):
    """Heat-tinted anodized titanium — oxide interference colours (straw / violet / cobalt / cyan)
    flowing across fine ground/brushed metal, the way a burnt titanium exhaust bleeds colour."""
    H, W, xx, yy = _coords(shape)
    temp = _fbm((H, W), seed, octaves=4, freq=3.2)               # oxide-thickness / heat field
    temp = cv2.GaussianBlur(temp, (0, 0), 1.4)
    col = _ti_ramp(_norm(temp))
    # fine ground grind: curved directional brush lines (radial-ish so not straight up/down) — crushed
    cx, cy = W * 0.5, H * 0.5
    rr = np.hypot(xx - cx, yy - cy)
    th = np.arctan2(yy - cy, xx - cx)
    grind = 0.5 + 0.5 * np.cos(rr * 1.4 + th * 60.0)            # finer, deeper brush striations
    grind = 0.62 + 0.38 * grind
    grain = _fbm((H, W), seed + 13, octaves=3, freq=95.0)       # fine metal tooth
    grind = grind * (0.80 + 0.20 * (0.5 + 0.5 * np.cos((xx * 2.3 + yy * 1.9))))
    img = col * grind[..., None]
    img = img + 0.22 * (grain - 0.5)[..., None]                 # fine isotropic grind grain
    img = img * (0.6 + 0.45 * _norm(temp))[..., None] + col * 0.16
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# ----------------------------------------------------------------------------- 11. Widmanstatten
def meteorite_widmanstatten(shape, seed=7):
    """Etched iron-meteorite Widmanstatten pattern — interlocking kamacite ribbons crossing at the
    octahedrite ~60deg angles, acid-etched into nickel-iron. Crisp metallic lattice, full-canvas."""
    H, W, xx, yy = _coords(shape)
    rng = _rng(seed)
    warp = 20.0 * _fbm((H, W), seed + 4, octaves=3, freq=2.4)    # slight warp so bands aren't ruler-straight
    wx, wy = xx + warp, yy + warp
    fams = []
    edges = np.zeros((H, W), np.float32)
    for k in range(3):
        a = rng.random() * 0.3 + k * (np.pi / 3.0)               # ~60deg-spaced kamacite families
        u = wx * np.cos(a) + wy * np.sin(a)
        ph = np.mod(u / 17.0, 1.0)                               # finer lamellae (period ~17px)
        tw = np.power(0.5 + 0.5 * np.cos(ph * 2 * np.pi), 2.2)   # crisp bright lamella ribbons
        fams.append(tw)
        edges = edges + np.power(1.0 - np.abs(np.cos(ph * 2 * np.pi)), 8.0)  # thin etched boundaries
    lattice = np.maximum.reduce(fams)                            # interlocking: brightest lamella wins
    edges = _norm(edges)
    etch = 0.80 + 0.20 * _norm(_fbm((H, W), seed + 8, octaves=4, freq=85.0))   # fine acid-etch grain
    val = (0.22 + 0.62 * lattice) * etch + 0.45 * edges
    img = _tint(np.clip(val, 0, 1), (0.08, 0.08, 0.10), (0.86, 0.88, 0.93))    # nickel-iron silver
    return np.clip(img, 0.0, 1.0).astype(np.float32)


MATERIALS_STRUCTURES = {
    "carbon_twill":   carbon_twill,
    "forged_carbon":  forged_carbon,
    "engine_turned":  engine_turned,
    "liquid_metal":   liquid_metal,
    "crystal_lattice": crystal_lattice,
    "ferrofluid":     ferrofluid,
    "fracture_net":   fracture_net,
    "damascus_steel": damascus_steel,
    "kevlar_aramid":  kevlar_aramid,
    "anodized_titanium": anodized_titanium,
    "meteorite_widmanstatten": meteorite_widmanstatten,
}


# ----------------------------------------------------------------------------- material spec map
def material_spec(art, metal=0.80, rough_base=0.40, rough_range=0.42, cc_gain=0.32):
    """Physically-metallic spec that TRACES the material structure (these are metals, not emissive
    art): high METALLIC (R-chan) brightest on the lit structure, ROUGHNESS (G-chan) glossy on the
    crowns + rougher in the valleys (mirror->satin via params), CLEARCOAT (B-chan) on the highlights.
    Iron-safe by construction (M<240, R>=18, Cc is 0 or >=16). Returns uint8 HxWx3 (M,R,Cc)."""
    a = np.clip(np.asarray(art, np.float32), 0, 1)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, 2)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    L = _norm(lum)
    M = np.clip(metal * 255.0 * (0.70 + 0.30 * L), 0, 235)               # metallic, structure-bright
    R = np.clip((rough_base + rough_range * (1.0 - L)) * 255.0, 18, 250)  # glossy crowns, rough valleys
    hi = np.clip((L - 0.68) / 0.32, 0, 1)
    Cc = np.where(hi > 0, np.clip(42.0 + cc_gain * 255.0 * hi, 16, 255), 0.0)  # clearcoat on highlights
    return np.stack([M, R, Cc], -1).clip(0, 255).astype(np.uint8)


# per-finish spec params -> a DIVERSE metal family (mirror chrome ... satin carbon)
MATERIAL_SPEC_PARAMS = {
    "carbon_twill":   dict(metal=0.72, rough_base=0.44, rough_range=0.44, cc_gain=0.26),  # satin carbon
    "forged_carbon":  dict(metal=0.80, rough_base=0.38, rough_range=0.44, cc_gain=0.38),  # flake glints
    "engine_turned":  dict(metal=0.90, rough_base=0.24, rough_range=0.40, cc_gain=0.46),  # polished machined
    "liquid_metal":   dict(metal=0.93, rough_base=0.12, rough_range=0.34, cc_gain=0.56),  # mirror chrome
    "crystal_lattice": dict(metal=0.85, rough_base=0.20, rough_range=0.50, cc_gain=0.52),  # faceted gem glint
    "ferrofluid":     dict(metal=0.88, rough_base=0.16, rough_range=0.46, cc_gain=0.50),  # glossy iron caps
    "fracture_net":   dict(metal=0.70, rough_base=0.46, rough_range=0.40, cc_gain=0.34),  # matte plates, lit cracks
    "damascus_steel": dict(metal=0.86, rough_base=0.30, rough_range=0.44, cc_gain=0.40),  # etched steel bands
    "kevlar_aramid":  dict(metal=0.74, rough_base=0.42, rough_range=0.44, cc_gain=0.30),  # satin gold weave
    "anodized_titanium": dict(metal=0.88, rough_base=0.26, rough_range=0.42, cc_gain=0.48),  # glossy oxide
    "meteorite_widmanstatten": dict(metal=0.87, rough_base=0.32, rough_range=0.42, cc_gain=0.42),  # etched nickel-iron
}
