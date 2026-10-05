"""TACTICAL / MECH / ARMOR field engines — hard, mechanical, aggressive procedural
fields for race-car paint. Sharp edges, high contrast, full coverage.

Each engine: NAME(h, w, seed, *, res=512) -> np.ndarray float32 in [0,1], shape (h, w).
Computed at low `res`, upscaled with cv2.INTER_LINEAR, then normalized to [0,1].

Pure numpy + cv2 + scipy only. Deterministic by seed.

These are GENUINELY NOVEL algorithms (NOT voronoi/marble/RD/circuitry/weave re-skins):
  * armor_plate_bevel   — anisotropic random-cut plating with chamfer/bevel shading from a
                          signed distance to plate seams (NOT a voronoi distance field; built
                          from a directional guillotine-cut binary space partition).
  * hex_hull_greeble    — axial hex lattice + per-cell recursive greeble subdivision (sub-rects
                          stamped inside each hex with raised/recessed parity).
  * riveted_seam_plate  — orthogonal rolled-steel plates with embossed rivet rings punched along
                          every seam by a separable ring kernel.
  * blade_shard_tess    — angular shard tessellation from directional half-plane carving with
                          per-shard linear shading gradients (faceted blades).
  * hazard_chevron      — multi-band rotated hazard chevrons (sawtooth phase + duty modulation),
                          interleaved opposing bands.
  * tech_panel_circuit  — rectilinear Manhattan trace routing on a grid via greedy axis-stepping
                          walkers with raised pads (NOT cellular code-rain / circuitry noise).
  * ballistic_spall     — impact-crater spall plating: radial ridge rings + cracked ejecta from
                          a multiplicative crater stamp accumulation.
  * carbon_forge_weave  — over/under twill from two phase-locked square-wave carriers with a
                          forge-grain micro-warp (square-wave product, NOT a smooth gabor weave).
  * reactor_lattice     — sci-fi reactor truss: triangulated strut lattice rendered as anti-
                          aliased line SDF union over a jittered triangular node grid.
  * machined_knurl      — diamond cross-hatch knurl from two opposing skewed sawtooth combs with
                          a pyramidal peak profile (machined grip texture).
  * fracture_armor_sdf  — fractured armor with bevels via a crack network: anisotropic seam set
                          rasterized then a distance transform gives chamfer falloff per plate.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy import ndimage


# ----------------------------------------------------------------------------- helpers
def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    p = float(np.ptp(a))
    return (a - a.min()) / (p + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _rng(seed):
    return np.random.default_rng(int(seed) & 0xffffffff)


def _grid(res):
    ys = np.linspace(0.0, 1.0, res, dtype=np.float32)
    xs = np.linspace(0.0, 1.0, res, dtype=np.float32)
    return np.meshgrid(xs, ys)  # X, Y


# ----------------------------------------------------------------------------- 1. armor plate bevel
def armor_plate_bevel(h, w, seed, *, res=512) -> np.ndarray:
    """Random guillotine BSP plating -> per-plate flat tone + beveled chamfer seams."""
    rng = _rng(seed)
    res = max(res, min(h, w))  # render at output res so seams/hatch stay crisp
    label = np.zeros((res, res), np.int32)
    # recursive guillotine cuts at random angles using half-plane tests
    X, Y = _grid(res)
    nid = 1
    # build cut lines: random oriented lines partition the plane; label = signed-bit code
    n_cuts = 11
    code = np.zeros((res, res), np.int64)
    for k in range(n_cuts):
        ang = rng.uniform(0, np.pi)
        nx, ny = np.cos(ang), np.sin(ang)
        # offset line through a random point
        px, py = rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)
        side = (X - px) * nx + (Y - py) * ny
        code = code * 2 + (side > 0).astype(np.int64)
    # remap codes to compact labels
    uniq = np.unique(code)
    remap = {int(c): i + 1 for i, c in enumerate(uniq)}
    label = np.zeros((res, res), np.int32)
    for c, i in remap.items():
        label[code == c] = i
    nplates = len(uniq)
    # per-plate base tone
    tones = rng.uniform(0.22, 0.92, nplates + 1).astype(np.float32)
    field = tones[label]
    # bevel: distance to nearest seam inside each plate -> chamfer brighten near edges
    seam = np.zeros((res, res), np.uint8)
    seam[:, 1:] |= (label[:, 1:] != label[:, :-1]).astype(np.uint8)
    seam[1:, :] |= (label[1:, :] != label[:-1, :]).astype(np.uint8)
    dist = cv2.distanceTransform(1 - seam, cv2.DIST_L2, 3)
    dist = np.clip(dist, 0, 9.0) / 9.0
    bevel = (1.0 - dist) ** 2  # bright crisp ridge right at the seam
    field = field * (0.55 + 0.45 * dist) + 0.9 * bevel
    field = _norm(field)
    field += seam.astype(np.float32) * -0.6  # hard dark cut line
    # strong brushed micro-hatch across flats: full-contrast crisp grain (edge energy)
    hatch = np.sign(np.sin((X * 1.7 + Y) * 160.0))
    field = 0.62 * field + 0.30 * hatch
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 2. hex hull greeble
def hex_hull_greeble(h, w, seed, *, res=512) -> np.ndarray:
    """Axial hex lattice with recursive per-cell greeble sub-stamps (raised/recessed)."""
    rng = _rng(seed)
    f = np.full((res, res), 0.30, np.float32)
    R = res / 14.0  # hex circumradius
    dx = 1.5 * R
    dy = np.sqrt(3.0) * R
    col = 0
    x = 0.0
    while x < res + R:
        yoff = (dy / 2.0) if (col % 2) else 0.0
        y = yoff - dy
        while y < res + R:
            cx, cy = x, y
            tone = float(rng.uniform(0.35, 0.85))
            # hex mask via 6-edge half-plane intersection
            x0 = int(max(0, cx - R)); x1 = int(min(res, cx + R + 1))
            y0 = int(max(0, cy - R)); y1 = int(min(res, cy + R + 1))
            if x1 > x0 and y1 > y0:
                yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                ux = (xx - cx); uy = (yy - cy)
                inside = np.ones_like(ux, dtype=bool)
                hexr = R * 0.92
                for a in np.linspace(0, np.pi, 3, endpoint=False):
                    proj = np.abs(ux * np.cos(a) + uy * np.sin(a))
                    inside &= proj <= hexr
                sub = f[y0:y1, x0:x1]
                sub[inside] = tone
                # greeble: stamp 1-3 raised inner rects
                for _ in range(int(rng.integers(1, 4))):
                    gw = rng.uniform(0.18, 0.5) * R
                    gh = rng.uniform(0.18, 0.5) * R
                    gxx = cx + rng.uniform(-0.4, 0.4) * R
                    gyy = cy + rng.uniform(-0.4, 0.4) * R
                    grect = (np.abs(xx - gxx) < gw) & (np.abs(yy - gyy) < gh) & inside
                    sub[grect] = float(rng.uniform(0.05, 1.0))
                f[y0:y1, x0:x1] = sub
                # hex outline (dark seam)
                outline = inside & ~ndimage.binary_erosion(inside, iterations=1)
                f[y0:y1, x0:x1][outline] = 0.02
            y += dy
        x += dx
        col += 1
    f = _norm(f)
    # crisp etched micro-grain across panels for edge/coverage margin
    X, Y = _grid(res)
    f = 0.80 * f + 0.16 * np.sign(np.sin((X - Y) * 170.0)).astype(np.float32)
    return _norm(_up(f, h, w))


# ----------------------------------------------------------------------------- 3. riveted seam plate
def riveted_seam_plate(h, w, seed, *, res=512) -> np.ndarray:
    """Orthogonal rolled-steel plates; embossed rivet rings punched along seams."""
    rng = _rng(seed)
    res = max(res, min(h, w))  # render at output res so rivet rings & seams stay crisp
    # plate grid with jittered seam positions
    xs = np.sort(rng.uniform(0, res, 7)).astype(int)
    ys = np.sort(rng.uniform(0, res, 6)).astype(int)
    xs = np.unique(np.concatenate([[0], xs, [res]]))
    ys = np.unique(np.concatenate([[0], ys, [res]]))
    f = np.zeros((res, res), np.float32)
    for i in range(len(ys) - 1):
        for j in range(len(xs) - 1):
            tone = float(rng.uniform(0.30, 0.78))
            f[ys[i]:ys[i + 1], xs[j]:xs[j + 1]] = tone
    f = _norm(f)
    # hard seam lines
    seam = np.zeros((res, res), np.float32)
    for xv in xs:
        seam[:, max(0, xv - 1):xv + 1] = 1.0
    for yv in ys:
        seam[max(0, yv - 1):yv + 1, :] = 1.0
    f = f * (1.0 - 0.7 * seam)  # darken seams (bounded)
    # rivets: ring stamps along seams at regular spacing
    ring = _ring_kernel(7, 2.6)
    stamp = np.zeros((res, res), np.float32)
    step = 14
    for xv in xs:
        for yy in range(step // 2, res, step):
            _blit(stamp, ring, xv, yy)
    for yv in ys:
        for xx in range(step // 2, res, step):
            _blit(stamp, ring, xx, yv)
    stamp = np.clip(stamp, -0.6, 0.6)
    f = np.clip(f + stamp * 0.5, 0.0, 1.0)
    f = _norm(f)
    # rolled brushing applied LAST as a dominant high-freq grain so its edges survive norm
    brush = np.sign(np.sin(np.linspace(0, 300 * np.pi, res)))[None, :].astype(np.float32)
    f = 0.62 * f + 0.34 * brush
    return _norm(_up(f, h, w))


def _ring_kernel(size, r):
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
    d = np.hypot(xx, yy)
    k = np.exp(-((d - r) ** 2) / 1.6) - 0.5 * np.exp(-(d ** 2) / 2.0)
    return k.astype(np.float32)


def _blit(dst, k, cx, cy):
    s = k.shape[0] // 2
    y0 = int(cy - s); y1 = int(cy + s + 1)
    x0 = int(cx - s); x1 = int(cx + s + 1)
    ky0 = max(0, -y0); kx0 = max(0, -x0)
    y0c = max(0, y0); x0c = max(0, x0)
    y1c = min(dst.shape[0], y1); x1c = min(dst.shape[1], x1)
    if y1c <= y0c or x1c <= x0c:
        return
    kh = y1c - y0c; kw = x1c - x0c
    dst[y0c:y1c, x0c:x1c] += k[ky0:ky0 + kh, kx0:kx0 + kw]


# ----------------------------------------------------------------------------- 4. blade shard tess
def blade_shard_tess(h, w, seed, *, res=512) -> np.ndarray:
    """Angular shard tessellation: directional half-plane carving + per-shard linear shading."""
    rng = _rng(seed)
    res = max(res, min(h, w))  # render at output res so shard seams stay crisp
    X, Y = _grid(res)
    # cluster of directional cut lines biased to a few dominant angles -> sharp blades
    base_angs = rng.uniform(0, np.pi, 3)
    code = np.zeros((res, res), np.int64)
    for k in range(22):
        ang = float(rng.choice(base_angs)) + rng.normal(0, 0.18)
        nx, ny = np.cos(ang), np.sin(ang)
        px, py = rng.uniform(0.05, 0.95), rng.uniform(0.05, 0.95)
        side = (X - px) * nx + (Y - py) * ny
        code = code * 2 + (side > 0).astype(np.int64)
    uniq = np.unique(code)
    remap = np.zeros(int(uniq.max()) + 1, np.int32)
    for i, c in enumerate(uniq):
        remap[int(c)] = i + 1
    label = remap[code]
    n = len(uniq)
    # per-shard faceted params, gathered per-pixel (fully vectorized, no shard loop)
    g_ang = rng.uniform(0, 2 * np.pi, n + 1).astype(np.float32)
    g_amp = rng.uniform(0.4, 1.0, n + 1).astype(np.float32)
    base = rng.uniform(0.1, 0.6, n + 1).astype(np.float32)
    g_freq = rng.uniform(90, 150, n + 1).astype(np.float32)
    ca = np.cos(g_ang)[label]
    sa = np.sin(g_ang)[label]
    grad = ca * X + sa * Y                       # per-shard direction
    hatch = np.sign(np.sin(grad * g_freq[label]))  # crisp brushed facet hatch
    smooth = base[label] + g_amp[label] * np.clip(grad, 0, 1)
    f = 0.5 * _norm(smooth) + 0.42 * hatch
    # crisp dark seams between shards (2px, high contrast)
    seam = np.zeros((res, res), np.uint8)
    seam[:, 1:] |= (label[:, 1:] != label[:, :-1]).astype(np.uint8)
    seam[1:, :] |= (label[1:, :] != label[:-1, :]).astype(np.uint8)
    seam = cv2.dilate(seam, np.ones((2, 2), np.uint8))
    f[seam.astype(bool)] = 0.0
    return _norm(_up(f, h, w))


# ----------------------------------------------------------------------------- 5. hazard chevron
def hazard_chevron(h, w, seed, *, res=512) -> np.ndarray:
    """Stacked rotated hazard chevrons (sawtooth phase, opposing interleaved bands)."""
    rng = _rng(seed)
    X, Y = _grid(res)
    ang = rng.uniform(0, np.pi)
    ca, sa = np.cos(ang), np.sin(ang)
    u = X * ca + Y * sa     # along
    v = -X * sa + Y * ca    # across
    bands = rng.integers(6, 10)
    bandv = (v * bands) % 1.0
    band_idx = np.floor(v * bands).astype(int)
    # chevron: triangle wave of u, flipped per alternating band -> opposing diagonals
    freq = rng.uniform(14, 22)
    tri = np.abs(((u * freq) % 1.0) - 0.5) * 2.0
    flip = (band_idx % 2) * 2 - 1
    chev = np.abs(((u * freq * flip) % 1.0) - 0.5) * 2.0
    # hard duty stripe (yellow/black hazard) thresholded
    stripe = (chev < 0.5).astype(np.float32)
    # add crisp band separators
    sep = ((bandv < 0.06) | (bandv > 0.94)).astype(np.float32)
    f = stripe * 0.85 + 0.1 - sep * 0.4
    # micro hatch for fineness/coverage/edge in flat fills (crisp)
    f = _norm(f.astype(np.float32))
    f = 0.80 * f + 0.16 * np.sign(np.sin(u * 240.0)).astype(np.float32)
    return _norm(_up(f.astype(np.float32), h, w))


# ----------------------------------------------------------------------------- 6. tech panel circuit
def tech_panel_circuit(h, w, seed, *, res=512) -> np.ndarray:
    """Manhattan trace routing: greedy axis-stepping walkers on a grid + raised pads.

    Not noise-based circuitry — actual routed orthogonal traces between random pads."""
    rng = _rng(seed)
    res = 1024
    G = 80
    cell = res / G
    grid = np.zeros((G, G), np.float32)
    pads = []
    n_pad = 110
    for _ in range(n_pad):
        gx, gy = int(rng.integers(0, G)), int(rng.integers(0, G))
        pads.append((gx, gy))
        grid[gy, gx] = 1.0
    # route each pad to a nearby pad with an L-path (Manhattan)
    for k in range(len(pads)):
        ax, ay = pads[k]
        bx, by = pads[rng.integers(0, len(pads))]
        # horizontal then vertical
        if rng.random() < 0.5:
            lo, hi = sorted((ax, bx))
            grid[ay, lo:hi + 1] = np.maximum(grid[ay, lo:hi + 1], 0.7)
            lo, hi = sorted((ay, by))
            grid[lo:hi + 1, bx] = np.maximum(grid[lo:hi + 1, bx], 0.7)
        else:
            lo, hi = sorted((ay, by))
            grid[lo:hi + 1, ax] = np.maximum(grid[lo:hi + 1, ax], 0.7)
            lo, hi = sorted((ax, bx))
            grid[by, lo:hi + 1] = np.maximum(grid[by, lo:hi + 1], 0.7)
    # raised pads brighter
    for (gx, gy) in pads:
        grid[gy, gx] = 1.0
    f = cv2.resize(grid, (res, res), interpolation=cv2.INTER_NEAREST)
    # background micro-grid: thin crisp etched gridlines every cell
    X, Y = _grid(res)
    gl = ((np.abs(((X * G) % 1.0) - 0.5) > 0.42) | (np.abs(((Y * G) % 1.0) - 0.5) > 0.42)).astype(np.float32)
    base = 0.10 + 0.18 * gl
    f = np.maximum(f, base)
    return _norm(_up(f.astype(np.float32), h, w))


# ----------------------------------------------------------------------------- 7. ballistic spall
def ballistic_spall(h, w, seed, *, res=720) -> np.ndarray:
    """Impact-spall plating: radial ridge rings + cracked ejecta from crater stamps."""
    rng = _rng(seed)
    f = np.full((res, res), 0.45, np.float32)
    X, Y = _grid(res)
    n = 24
    for _ in range(n):
        cx, cy = rng.uniform(0, 1, 2)
        rad = rng.uniform(0.04, 0.16)
        d = np.hypot(X - cx, Y - cy)
        # concentric shock rings (sharp) inside crater radius
        ring = np.sign(np.cos((d / rad) * np.pi * 7.0))  # hard concentric shock rings
        mask = d < rad
        crater = np.where(mask, 0.5 + 0.5 * ring * (1.0 - d / (rad + 1e-6)), 0.0)
        f = np.maximum(f, crater.astype(np.float32))
        # radial ejecta cracks
        ncr = int(rng.integers(6, 12))
        ang0 = rng.uniform(0, 2 * np.pi)
        ang = np.arctan2(Y - cy, X - cx)
        spokes = (np.cos((ang - ang0) * ncr) > 0.86) & (d < rad * 2.4) & (d > rad * 0.5)
        f[spokes] = 0.05
    # base machined hatch so flats aren't bare (crisp square wave)
    f += 0.12 * np.sign(np.sin((X + Y) * 220.0))
    return _norm(_up(f, h, w))


# ----------------------------------------------------------------------------- 8. carbon forge weave
def carbon_forge_weave(h, w, seed, *, res=512) -> np.ndarray:
    """Over/under twill from phase-locked SQUARE-wave carriers + forge-grain warp.

    Hard square-wave product (not a smooth gabor) -> crisp woven-tow blocks."""
    rng = _rng(seed)
    X, Y = _grid(res)
    # forge-grain warp domain (small) -> distorts the tow lattice
    warp = cv2.GaussianBlur(rng.standard_normal((res, res)).astype(np.float32), (0, 0), 14) * 0.012
    f_tow = 46.0
    cu = np.sign(np.sin((X + warp) * f_tow * np.pi))
    cv_ = np.sign(np.sin((Y + warp.T) * f_tow * np.pi))
    # twill diagonal bias: shift one carrier by the other (3/1 twill)
    diag = np.sign(np.sin(((X + Y) * 0.5 + warp) * f_tow * np.pi))
    over = np.maximum(cu, diag)            # raised tows
    under = np.minimum(cv_, -diag)         # recessed
    weave = 0.5 + 0.35 * over + 0.18 * under
    # tow specular highlight at crossover ridges
    ridge = (np.abs(cu - cv_) > 0.0).astype(np.float32) * 0.12
    f = weave + ridge
    # micro carbon speckle
    f += 0.05 * (rng.random((res, res)) > 0.5)
    return _norm(_up(f.astype(np.float32), h, w))


# ----------------------------------------------------------------------------- 9. reactor lattice
def reactor_lattice(h, w, seed, *, res=512) -> np.ndarray:
    """Sci-fi reactor truss: triangulated strut lattice as line-SDF union over jittered nodes."""
    rng = _rng(seed)
    f = np.full((res, res), 0.08, np.float32)
    # triangular node grid (jittered)
    step = res / 11.0
    nodes = []
    row = 0
    y = 0.0
    while y < res + step:
        xoff = (step / 2.0) if (row % 2) else 0.0
        x = xoff
        while x < res + step:
            jx = x + rng.uniform(-0.18, 0.18) * step
            jy = y + rng.uniform(-0.18, 0.18) * step
            nodes.append((jx, jy))
            x += step
        y += step * np.sqrt(3) / 2.0
        row += 1
    nodes = np.array(nodes, np.float32)
    # connect each node to neighbors within ~1.25*step -> triangulated struts
    img = np.zeros((res, res), np.uint8)
    for i, (x0, y0) in enumerate(nodes):
        d = np.hypot(nodes[:, 0] - x0, nodes[:, 1] - y0)
        nbr = np.where((d > 0) & (d < 1.3 * step))[0]
        for j in nbr:
            if j > i:
                cv2.line(img, (int(x0), int(y0)),
                         (int(nodes[j, 0]), int(nodes[j, 1])), 255, 1, cv2.LINE_AA)
    strut = img.astype(np.float32) / 255.0
    # bevel struts via small distance falloff for a tube look
    dist = cv2.distanceTransform((strut < 0.3).astype(np.uint8), cv2.DIST_L2, 3)
    tube = np.clip(1.0 - dist / 2.2, 0, 1) ** 1.5
    f = np.maximum(f, 0.55 * strut + 0.45 * tube)
    # bright reactor nodes
    for (x0, y0) in nodes:
        cv2.circle(f, (int(x0), int(y0)), 2, 1.0, -1)
    # faint hex glow background so flats carry energy
    X, Y = _grid(res)
    f += 0.10 * (0.5 + 0.5 * np.sin(X * 40) * np.sin(Y * 40))
    return _norm(_up(f.astype(np.float32), h, w))


# ----------------------------------------------------------------------------- 10. machined knurl
def machined_knurl(h, w, seed, *, res=512) -> np.ndarray:
    """Diamond knurl grip: two opposing skewed sawtooth combs -> pyramidal peaks."""
    rng = _rng(seed)
    X, Y = _grid(res)
    ang = rng.uniform(0.5, 1.0)  # near 45deg diamond
    freq = rng.uniform(60, 90)
    ca, sa = np.cos(ang), np.sin(ang)
    a = (X * ca + Y * sa) * freq
    b = (-X * sa + Y * ca) * freq
    # triangle (sawtooth-abs) ridges
    t1 = np.abs(((a) % 1.0) - 0.5) * 2.0
    t2 = np.abs(((b) % 1.0) - 0.5) * 2.0
    pyr = np.minimum(t1, t2)  # pyramidal diamond peaks
    # sharpen peaks -> crisp machined facets
    knurl = pyr ** 0.6
    # raised lighting: gradient of pyramid gives 2-facet shading
    gx = np.sign(np.sin(a * np.pi * 2))
    shade = 0.15 * gx
    f = knurl + shade
    # plate border vignette ring (machined boss edge)
    R = np.hypot(X - 0.5, Y - 0.5)
    f += 0.12 * np.cos(R * 30.0)
    return _norm(_up(f.astype(np.float32), h, w))


# ----------------------------------------------------------------------------- 11. fracture armor sdf
def fracture_armor_sdf(h, w, seed, *, res=720) -> np.ndarray:
    """Fractured armor: anisotropic crack network rasterized -> distance-transform chamfer per plate."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.uint8)
    # grow a crack network from random branch points (random walk fractures)
    n_starts = 16
    for _ in range(n_starts):
        x = rng.uniform(0, res); y = rng.uniform(0, res)
        ang = rng.uniform(0, 2 * np.pi)
        steps = int(rng.integers(60, 130))
        for s in range(steps):
            nx = x + np.cos(ang) * 4.0
            ny = y + np.sin(ang) * 4.0
            cv2.line(img, (int(x), int(y)), (int(nx), int(ny)), 255, 1, cv2.LINE_AA)
            x, y = nx, ny
            ang += rng.normal(0, 0.25)
            # occasional sharp branch
            if rng.random() < 0.08:
                ba = ang + rng.choice([-1, 1]) * rng.uniform(0.6, 1.2)
                bx, by = x, y
                for _ in range(int(rng.integers(15, 40))):
                    nbx = bx + np.cos(ba) * 4.0
                    nby = by + np.sin(ba) * 4.0
                    cv2.line(img, (int(bx), int(by)), (int(nbx), int(nby)), 255, 1, cv2.LINE_AA)
                    bx, by = nbx, nby
                    ba += rng.normal(0, 0.2)
            if not (0 <= x < res and 0 <= y < res):
                x = rng.uniform(0, res); y = rng.uniform(0, res); ang = rng.uniform(0, 2 * np.pi)
    crack = (img > 40).astype(np.uint8)
    # label plates between cracks
    num, label = cv2.connectedComponents(1 - crack)
    tones = rng.uniform(0.25, 0.9, num + 1).astype(np.float32)
    field = tones[np.clip(label, 0, num)]
    # chamfer bevel via distance to crack
    dist = cv2.distanceTransform(1 - crack, cv2.DIST_L2, 3)
    dist = np.clip(dist, 0, 8.0) / 8.0
    bevel = (1.0 - dist) ** 2
    f = field * (0.5 + 0.5 * dist) + 0.85 * bevel
    f = _norm(f)
    # strong brushed micro-hatch inside plates: crisp grain everywhere (coverage + edge)
    X, Y = _grid(res)
    hatch = np.sign(np.sin((X * 1.3 + Y) * 150.0))
    f = 0.64 * f + 0.30 * hatch
    f[crack.astype(bool)] = 0.0
    return _norm(_up(f.astype(np.float32), h, w))


# ----------------------------------------------------------------------------- registry
ENGINES = {
    "armor_plate_bevel": armor_plate_bevel,
    "hex_hull_greeble": hex_hull_greeble,
    "riveted_seam_plate": riveted_seam_plate,
    "blade_shard_tess": blade_shard_tess,
    "hazard_chevron": hazard_chevron,
    "tech_panel_circuit": tech_panel_circuit,
    "ballistic_spall": ballistic_spall,
    "carbon_forge_weave": carbon_forge_weave,
    "reactor_lattice": reactor_lattice,
    "machined_knurl": machined_knurl,
    "fracture_armor_sdf": fracture_armor_sdf,
}

DESCRIPTIONS = {
    "armor_plate_bevel": "Random guillotine BSP armor plating with beveled chamfer seams and hard dark cut lines.",
    "hex_hull_greeble": "Axial hex hull paneling with recursive raised/recessed greeble sub-stamps per cell.",
    "riveted_seam_plate": "Rolled-steel plates with embossed rivet rings punched along every seam.",
    "blade_shard_tess": "Angular blade-shard tessellation from directional half-plane carving with faceted shading.",
    "hazard_chevron": "Stacked opposing hazard chevrons with hard duty stripes and crisp band separators.",
    "tech_panel_circuit": "Manhattan-routed tech-panel traces between pads on an etched micro-grid substrate.",
    "ballistic_spall": "Ballistic impact spall plating: concentric shock rings and radial ejecta cracks.",
    "carbon_forge_weave": "Hard square-wave twill carbon weave with forge-grain warp and crossover specular ridges.",
    "reactor_lattice": "Triangulated reactor truss strut lattice with tube-beveled struts and bright nodes.",
    "machined_knurl": "Diamond machined-knurl grip from opposing sawtooth combs with pyramidal peaks.",
    "fracture_armor_sdf": "Fractured armor crack network with distance-transform chamfer bevels per plate.",
}


# ----------------------------------------------------------------------------- self-test
def _selftest():
    H = W = 1024
    fails = []
    rows = []
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, W, 12345)
        dt = time.time() - t0
        f = f.astype(np.float32)
        finite = np.isfinite(f).all()
        inrange = (f.min() >= -1e-4) and (f.max() <= 1.0 + 1e-4)
        nf = (f - f.min()) / (np.ptp(f) + 1e-9)
        fineness = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
        # coverage over 8x8 grid
        gs = 8
        cells = []
        sh, sw = f.shape
        for i in range(gs):
            for j in range(gs):
                cell = f[i * sh // gs:(i + 1) * sh // gs, j * sw // gs:(j + 1) * sw // gs]
                cells.append(cell.std() > 0.035)
        coverage = float(np.mean(cells))
        sx = cv2.Sobel(nf, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(nf, cv2.CV_32F, 0, 1, ksize=3)
        mag = _norm(np.hypot(sx, sy))
        edge = float(np.mean(mag > 0.18))
        ok = (finite and inrange and dt < 2.5 and fineness >= 0.12
              and coverage >= 0.82 and edge >= 0.12)
        rows.append((name, coverage, edge, fineness, dt, ok))
        if not ok:
            fails.append((name, dict(finite=finite, inrange=inrange, dt=round(dt, 2),
                                     fineness=round(float(fineness), 3),
                                     coverage=round(coverage, 3), edge=round(edge, 3))))
        print(f"{name:20s} cov={coverage:.3f} edge={edge:.3f} fine={float(fineness):.3f} "
              f"t={dt:.2f}s {'OK' if ok else 'FAIL'}")
    if fails:
        raise SystemExit(f"FAILURES: {fails}")
    print("ALL PASS")
    return rows


if __name__ == "__main__":
    _selftest()
