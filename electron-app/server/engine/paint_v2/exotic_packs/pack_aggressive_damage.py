"""DAMAGE / FRACTURE / ENERGY — aggressive, edgy, FULL-COVERAGE field engines for
Shokker Paint Booth procedural race-car paint.

Each engine is a DIFFERENT algorithm (no voronoi/marble/RD/curl/gabor/etc. re-skins).
Contract (matches engine/paint_v2/fractured_math.py):
    def NAME(h, w, seed, *, res=512) -> np.ndarray float32 in [0,1], shape (h, w)
    - compute at low 'res', upscale with cv2 INTER_LINEAR, normalize ((a-a.min())/(ptp+1e-9))
    - pure numpy + cv2 + scipy ONLY, deterministic rng = default_rng(int(seed) & 0xffffffff)

Run from repo root:  python _engine_expansion/pack_aggressive_damage.py
"""
from __future__ import annotations

import numpy as np
import cv2
from scipy import ndimage as ndi


# ----------------------------------------------------------------------------- helpers
def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _rng(seed):
    return np.random.default_rng(int(seed) & 0xffffffff)


def _grid(res):
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    return xs, ys


# ============================================================================= 1
def impact_shatter(h, w, seed, *, res=512) -> np.ndarray:
    """Radial impact star: cracks shoot OUT from one (or few) impact points, with
    concentric stress rings + angular-jaggy radial spokes. Sharp ridged crack lines
    woven over a stressed gradient — full coverage, very edgy."""
    rng = _rng(seed)
    xs, ys = _grid(res)
    field = np.zeros((res, res), np.float32)
    n_imp = int(rng.integers(2, 4))
    for _ in range(n_imp):
        cx = rng.uniform(0.2, 0.8) * res
        cy = rng.uniform(0.2, 0.8) * res
        dx = xs - cx
        dy = ys - cy
        r = np.hypot(dx, dy) + 1e-3
        ang = np.arctan2(dy, dx)
        # angular jaggedness: many sharp spokes that wobble with radius
        n_spokes = int(rng.integers(22, 40))
        wob = 0.0
        for k in (1, 2, 3):
            wob += np.sin(r * (0.05 * k) + rng.uniform(0, 6.28)) * (0.6 / k)
        spoke = np.abs(np.sin(ang * n_spokes * 0.5 + wob * 2.0))
        spoke = np.power(spoke, 6.0)  # crisp radial cracks
        # concentric stress rings, frequency rises near impact
        rings = np.abs(np.sin(np.sqrt(r) * rng.uniform(1.4, 2.2)))
        rings = np.power(rings, 4.0)
        falloff = np.exp(-r / (res * rng.uniform(0.35, 0.6)))
        contrib = (spoke * 0.7 + rings * 0.5) * (0.4 + falloff)
        field = np.maximum(field, contrib)
    # background stress micro-texture so nothing is flat
    micro = cv2.GaussianBlur(rng.random((res, res)).astype(np.float32), (0, 0), 1.0)
    field = field * 0.85 + micro * 0.18
    field = np.power(_norm(field), 0.8)
    return _norm(_up(field, h, w))


# ============================================================================= 2
def crack_network(h, w, seed, *, res=512) -> np.ndarray:
    """DENSE propagating crack network. Anisotropic random walks ("crack tips") march
    across the grid, branching and turning, rasterized as thin sharp lines, then a
    distance-to-crack field is inverted so the whole surface reads as fractured glass."""
    rng = _rng(seed)
    canvas = np.zeros((res, res), np.float32)
    n_seeds = int(rng.integers(40, 64))
    tips = []
    for _ in range(n_seeds):
        x = rng.uniform(0, res)
        y = rng.uniform(0, res)
        a = rng.uniform(0, 2 * np.pi)
        tips.append([x, y, a, rng.uniform(0.0, 1.0)])
    steps = 120
    for _ in range(steps):
        new_tips = []
        for (x, y, a, intensity) in tips:
            a += rng.normal(0, 0.35)  # wandering crack
            nx = x + np.cos(a) * 2.2
            ny = y + np.sin(a) * 2.2
            ix0, iy0 = int(x) % res, int(y) % res
            ix1, iy1 = int(nx) % res, int(ny) % res
            cv2.line(canvas, (ix0, iy0), (ix1, iy1), float(0.6 + 0.4 * intensity), 1)
            x, y = nx % res, ny % res
            # branch
            if rng.random() < 0.06:
                new_tips.append([x, y, a + rng.uniform(0.6, 1.2), intensity * 0.9])
            new_tips.append([x, y, a, intensity])
        # cap population to keep it dense but bounded
        if len(new_tips) > 900:
            rng.shuffle(new_tips)
            new_tips = new_tips[:900]
        tips = new_tips
    # distance transform: surface tile interiors get a smooth shade, cracks stay dark
    cracks = (canvas > 0.05).astype(np.uint8)
    dist = cv2.distanceTransform(1 - cracks, cv2.DIST_L2, 3)
    dist = _norm(dist)
    field = dist * 0.7 + canvas * 0.9
    field = np.power(_norm(field), 0.85)
    return _norm(_up(field, h, w))


# ============================================================================= 3
def claw_rake(h, w, seed, *, res=512) -> np.ndarray:
    """Shredded claw-rake gouges: parallel sets of curved deep grooves swept across the
    surface in several attack directions, with torn-metal ridges between gouges."""
    rng = _rng(seed)
    xs, ys = _grid(res)
    field = np.zeros((res, res), np.float32)
    n_swipes = int(rng.integers(4, 7))
    for _ in range(n_swipes):
        ang = rng.uniform(0, np.pi)
        ca, sa = np.cos(ang), np.sin(ang)
        # rotate coords; u along claw travel, v across the claw set
        u = (xs * ca + ys * sa)
        v = (-xs * sa + ys * ca)
        # the claw set curves: bend v as a function of u
        bend = np.sin(u * rng.uniform(0.006, 0.012) + rng.uniform(0, 6.28)) * res * 0.15
        vv = v + bend
        n_claws = rng.uniform(0.06, 0.11)  # spacing
        gouge = np.abs(np.sin(vv * n_claws))
        gouge = np.power(gouge, rng.uniform(3.0, 6.0))
        # the swipe has a travel envelope so claws fade in/out along u (torn look)
        env = 0.5 + 0.5 * np.sin(u * rng.uniform(0.004, 0.009) + rng.uniform(0, 6.28))
        field = np.maximum(field, gouge * (0.5 + 0.5 * env))
    # torn ridges: high-freq noise gated to between gouges
    ridge = cv2.GaussianBlur(rng.random((res, res)).astype(np.float32), (0, 0), 0.7)
    field = field * 0.85 + (1 - field) * ridge * 0.3
    field = np.power(_norm(field), 0.9)
    return _norm(_up(field, h, w))


# ============================================================================= 4
def ember_burst(h, w, seed, *, res=768) -> np.ndarray:
    """Dense ember/spark field: thousands of bright spark cores with directional streak
    trails (motion-blurred sparks) over a glowing heat-haze base — packed, NOT sparse."""
    rng = _rng(seed)
    spark = np.zeros((res, res), np.float32)
    n = int(res * res * 0.035)  # very dense
    sx = rng.integers(0, res, n)
    sy = rng.integers(0, res, n)
    amp = rng.random(n).astype(np.float32) ** 1.8  # mostly small, some hot
    np.add.at(spark, (sy, sx), amp)
    # global blast direction => motion-streak the sparks (short, keeps cores sharp)
    gang = rng.uniform(0, 2 * np.pi)
    k = max(5, int(res * 0.025)) | 1
    kern = np.zeros((k, k), np.float32)
    cx = k // 2
    for t in range(k):
        px = int(round(cx + (t - cx) * np.cos(gang)))
        py = int(round(cx + (t - cx) * np.sin(gang)))
        if 0 <= px < k and 0 <= py < k:
            kern[py, px] = 1.0 - 0.6 * abs(t - cx) / max(1, cx)  # fading trail
    kern /= kern.sum() + 1e-6
    streaks = cv2.filter2D(spark, -1, kern)
    cores = spark  # keep raw spark cores razor-sharp (no blur) for edge density
    # heat haze base so background is never bare
    haze = cv2.GaussianBlur(rng.random((res, res)).astype(np.float32), (0, 0), res * 0.02)
    haze = _norm(haze)
    field = streaks * 1.5 + cores * 4.0 + haze * 0.4
    field = np.power(_norm(field), 0.55)
    return _norm(_up(field, h, w))


# ============================================================================= 5
def glitch_mosh(h, w, seed, *, res=768) -> np.ndarray:
    """Glitch / datamosh block displacement: a noise base is torn into horizontal scan
    bands that get shifted, channel-split, and pixel-sorted — hard rectangular tears,
    blocky corruption. Crisp aggressive blocks, full coverage."""
    rng = _rng(seed)
    base = cv2.GaussianBlur(rng.random((res, res)).astype(np.float32), (0, 0), 1.0)
    base = _norm(base)
    out = base.copy()
    # horizontal scanline shifts (datamosh tear)
    y = 0
    while y < res:
        bh = int(rng.integers(2, max(4, res // 24)))
        shift = int(rng.integers(-res // 6, res // 6))
        out[y:y + bh] = np.roll(base[y:y + bh], shift, axis=1)
        # occasional hard bright/dark corruption band
        if rng.random() < 0.15:
            out[y:y + bh] = np.clip(out[y:y + bh] + rng.uniform(-0.6, 0.6), 0, 1)
        y += bh
    # rectangular block displacement (macroblocks)
    nblk = int(rng.integers(60, 110))
    for _ in range(nblk):
        bw = int(rng.integers(res // 32, res // 8))
        bh = int(rng.integers(res // 32, res // 8))
        x0 = int(rng.integers(0, res - bw))
        y0 = int(rng.integers(0, res - bh))
        sx = int(rng.integers(0, res - bw))
        sy = int(rng.integers(0, res - bh))
        out[y0:y0 + bh, x0:x0 + bw] = base[sy:sy + bh, sx:sx + bw]
    # pixel-sort a fraction of rows for the smeary mosh look
    for _ in range(int(res * 0.25)):
        r = int(rng.integers(0, res))
        x0 = int(rng.integers(0, res - res // 4))
        seg = out[r, x0:x0 + res // 4]
        out[r, x0:x0 + res // 4] = np.sort(seg)
    # hard posterize to crush soft gradients into crisp glitch steps (edgy)
    levels = 5
    out = np.round(out * levels) / levels
    field = _norm(out)
    return _norm(_up(field, h, w))


# ============================================================================= 6
def dazzle_razor(h, w, seed, *, res=768) -> np.ndarray:
    """Dazzle-camo razor striping: hard-edged black/white razor stripes broken into
    angular faceted zones (WWI dazzle camo). Each zone has its own stripe angle &
    frequency; boundaries are sharp polygon edges. Maximum contrast, full coverage."""
    rng = _rng(seed)
    xs, ys = _grid(res)
    # partition the plane into angular wedge zones via a coarse label field
    n_pts = int(rng.integers(14, 22))
    px = rng.uniform(0, res, n_pts)
    py = rng.uniform(0, res, n_pts)
    # nearest-point label (cheap manhattan-ish for hard facets)
    label = np.zeros((res, res), np.int32)
    best = np.full((res, res), 1e18, np.float32)
    for i in range(n_pts):
        d = (xs - px[i]) ** 2 + (ys - py[i]) ** 2
        m = d < best
        best[m] = d[m]
        label[m] = i
    field = np.zeros((res, res), np.float32)
    for i in range(n_pts):
        ang = rng.uniform(0, np.pi)
        freq = rng.uniform(0.14, 0.30)  # tighter razor stripes
        proj = xs * np.cos(ang) + ys * np.sin(ang)
        stripe = (np.sin(proj * freq) > 0).astype(np.float32)  # hard razor edge
        m = label == i
        field[m] = stripe[m]
    # hard black contrast seam on zone borders so facets pop (adds crisp edges)
    edges = (np.abs(cv2.Laplacian(label.astype(np.float32), cv2.CV_32F)) > 0.5)
    edges = cv2.dilate(edges.astype(np.float32), np.ones((3, 3), np.float32)) > 0
    field[edges] = 0.0
    field = field * 0.96 + 0.02  # keep tiny floor variance
    return _norm(_up(field, h, w))


# ============================================================================= 7
def warp_moire(h, w, seed, *, res=512) -> np.ndarray:
    """Aggressive op-art moire: two hard square-wave grids at slightly different angles &
    pitches multiply into a beat pattern, then the whole thing is radially pinched so the
    moire bands sweep into tense aggressive curves. NOT soft interference — square waves."""
    rng = _rng(seed)
    xs, ys = _grid(res)
    cx, cy = res * rng.uniform(0.35, 0.65), res * rng.uniform(0.35, 0.65)
    dx, dy = xs - cx, ys - cy
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    # radial pinch warp of coordinates
    pinch = r * (1.0 + 0.4 * np.sin(ang * rng.integers(3, 7)))
    a1 = rng.uniform(0, np.pi)
    a2 = a1 + rng.uniform(0.05, 0.18)
    f1 = rng.uniform(0.12, 0.20)
    f2 = f1 * rng.uniform(1.03, 1.12)
    u1 = (xs * np.cos(a1) + ys * np.sin(a1)) * f1 + pinch * 0.01
    u2 = (xs * np.cos(a2) + ys * np.sin(a2)) * f2 - pinch * 0.01
    g1 = (np.sin(u1) > 0).astype(np.float32)  # hard square grid
    g2 = (np.sin(u2) > 0).astype(np.float32)
    moire = np.abs(g1 - g2)  # beat = XOR-like aggressive bands
    # add a second crossed pair for denser interference
    v1 = (np.sin((-xs * np.sin(a1) + ys * np.cos(a1)) * f1) > 0).astype(np.float32)
    v2 = (np.sin((-xs * np.sin(a2) + ys * np.cos(a2)) * f2) > 0).astype(np.float32)
    field = np.maximum(moire, np.abs(v1 - v2)) * 0.9 + g1 * 0.1
    return _norm(_up(field, h, w))


# ============================================================================= 8
def blade_fan(h, w, seed, *, res=512) -> np.ndarray:
    """Kaleido-blade shard fans: from several pivots, sharp triangular blade shards fan
    out (angular sectors with hard radial edges + tapered length), overlapping into a
    dense aggressive shard storm. Crisp polygonal blades, full coverage."""
    rng = _rng(seed)
    res = max(res, h, w)  # compute at full output res so fine hard edges survive
    xs, ys = _grid(res)
    field = np.zeros((res, res), np.float32)
    n_fans = int(rng.integers(4, 6))
    for _ in range(n_fans):
        cx = rng.uniform(0.1, 0.9) * res
        cy = rng.uniform(0.1, 0.9) * res
        dx, dy = xs - cx, ys - cy
        r = np.hypot(dx, dy) + 1e-3
        ang = np.arctan2(dy, dx)
        n_blades = int(rng.integers(70, 110))  # many thin blades -> fine angular edges
        phase = rng.uniform(0, 6.28)
        # thin sharp blade EDGES (bright lines at each wedge boundary, not solid fills)
        saw = ((ang * n_blades / (2 * np.pi) + phase) % 1.0)
        blade_edge = (np.minimum(saw, 1.0 - saw) < 0.10).astype(np.float32)
        # thin sharp concentric facet rings (bright lines, dense radial pitch)
        rp = (r * rng.uniform(0.45, 0.65)) % 1.0
        facet_edge = (np.minimum(rp, 1.0 - rp) < 0.18).astype(np.float32)
        # combine the thin-line lattices -> dense web of hard edges everywhere
        contrib = np.maximum(blade_edge, facet_edge)
        field = np.maximum(field, contrib)
    # keep strictly binary so edges stay maximally crisp
    field = (field > 0.5).astype(np.float32)
    return _norm(_up(field, h, w))


# ============================================================================= 9
def arc_lattice(h, w, seed, *, res=512) -> np.ndarray:
    """Dense electric-arc lattice: a grid of charged nodes; arcs jump between near nodes
    as jagged jittered polylines (mini lightning), forming a packed crackling lattice
    with bright nodes + ridge glow. Edgy, full coverage, NOT the parked plasma engine."""
    rng = _rng(seed)
    canvas = np.zeros((res, res), np.float32)
    # node grid with jitter
    g = int(rng.integers(9, 13))
    cell = res / g
    nodes = []
    for j in range(g):
        for i in range(g):
            nx = (i + 0.5) * cell + rng.uniform(-cell * 0.3, cell * 0.3)
            ny = (j + 0.5) * cell + rng.uniform(-cell * 0.3, cell * 0.3)
            nodes.append((nx, ny))
    nodes = np.array(nodes, np.float32)

    def jag(p0, p1, depth, amp):
        if depth == 0:
            cv2.line(canvas, (int(p0[0]) % res, int(p0[1]) % res),
                     (int(p1[0]) % res, int(p1[1]) % res), 1.0, 1)
            return
        mid = (p0 + p1) * 0.5
        nrm = np.array([-(p1[1] - p0[1]), p1[0] - p0[0]], np.float32)
        nrm /= (np.linalg.norm(nrm) + 1e-6)
        mid = mid + nrm * rng.uniform(-amp, amp)
        jag(p0, mid, depth - 1, amp * 0.55)
        jag(mid, p1, depth - 1, amp * 0.55)

    # connect each node to a few near neighbors with arcs (dense lattice)
    for i in range(len(nodes)):
        d = np.sum((nodes - nodes[i]) ** 2, axis=1)
        order = np.argsort(d)[1:5]
        for k in order:
            if k > i:  # avoid double-draw
                jag(nodes[i], nodes[k], 4, cell * 0.5)
    # bright nodes
    for (nx, ny) in nodes:
        cv2.circle(canvas, (int(nx) % res, int(ny) % res), 2, 1.0, -1)
    glow = cv2.GaussianBlur(canvas, (0, 0), 1.2)
    field = np.maximum(canvas, glow * 0.8)
    # subtle field haze for full coverage
    field = field * 0.9 + cv2.GaussianBlur(canvas, (0, 0), res * 0.02) * 1.5
    field = np.power(_norm(field), 0.7)
    return _norm(_up(field, h, w))


# ============================================================================= 10
def tread_shred(h, w, seed, *, res=512) -> np.ndarray:
    """Tire-shred tread chunks: aggressive tire-tread block lugs (offset rows of chunky
    blocks with deep sipe grooves) that get TORN — chunks ripped out, edges shredded —
    via a destruction mask. Heavy mechanical pattern, full coverage."""
    rng = _rng(seed)
    xs, ys = _grid(res)
    # base tread: rows of blocks separated by deep grooves, alternating offset
    row_h = res / rng.uniform(10, 16)
    col_w = res / rng.uniform(8, 14)
    row = np.floor(ys / row_h)
    offset = (row % 2) * (col_w * 0.5)
    bx = ((xs + offset) % col_w) / col_w
    by = (ys % row_h) / row_h
    # block = inside margins; groove = near edges (deep / dark)
    mb = rng.uniform(0.12, 0.2)
    block = ((bx > mb) & (bx < 1 - mb) & (by > mb) & (by < 1 - mb)).astype(np.float32)
    # diagonal sipes carved across each block
    sipe = (np.sin((xs + ys) * rng.uniform(0.25, 0.4)) > 0.4).astype(np.float32)
    tread = block * (1.0 - 0.5 * sipe)
    tread = tread * (0.6 + 0.4 * rng.random())  # base height
    tread = np.where(block > 0, tread, 0.1)  # grooves dark, not zero
    # SHRED: tear out chunks with a torn destruction mask (noisy threshold)
    tear = cv2.GaussianBlur(rng.random((res, res)).astype(np.float32), (0, 0), res * 0.04)
    tear = _norm(tear)
    torn = tear < rng.uniform(0.25, 0.4)
    # torn regions get jagged rubber shreds instead of clean blocks
    shred = (np.sin(xs * 0.5 + ys * 0.3 + cv2.GaussianBlur(
        rng.random((res, res)).astype(np.float32), (0, 0), 1.0) * 8) > 0).astype(np.float32)
    field = np.where(torn, shred * 0.9, tread)
    # rough rubber grain everywhere so no patch is flat
    grain = cv2.GaussianBlur(rng.random((res, res)).astype(np.float32), (0, 0), 0.7)
    field = field * 0.85 + grain * 0.22
    field = np.power(_norm(field), 0.9)
    return _norm(_up(field, h, w))


# ============================================================================= 11
def stress_fracture(h, w, seed, *, res=768) -> np.ndarray:
    """Stress-field fracture: build a turbulent stress potential, then carve a DENSE
    network of fault lines along its level-set contours (where stress crosses many
    closely-spaced yield thresholds). Contour-isoline fracturing — field-driven, totally
    different from crack_network's random-walk tips."""
    rng = _rng(seed)
    xs, ys = _grid(res)
    # turbulent anisotropic stress potential (many directional load waves -> rich field)
    pot = np.zeros((res, res), np.float32)
    for _ in range(int(rng.integers(7, 11))):
        a = rng.uniform(0, np.pi)
        f = rng.uniform(0.02, 0.09)
        ph = rng.uniform(0, 6.28)
        pot += np.sin((xs * np.cos(a) + ys * np.sin(a)) * f + ph) * rng.uniform(0.4, 1.0)
    # warp the potential by noise so contours go jagged like real faults
    warp = cv2.GaussianBlur(rng.random((res, res)).astype(np.float32), (0, 0), 6.0)
    pot = pot + _norm(warp) * 4.0
    pot = _norm(pot)
    # DENSE level-set faults: fracture wherever the potential crosses any of N isolevels
    n_levels = 26
    lev = pot * n_levels
    frac = np.abs(lev - np.round(lev))          # distance to nearest contour, 0..0.5
    fault = (frac < 0.085).astype(np.float32)   # thin sharp fault lines everywhere
    # shear-stress shading between faults so tile interiors aren't flat
    gx = cv2.Sobel(pot, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(pot, cv2.CV_32F, 0, 1, ksize=3)
    shear = _norm(np.hypot(gx, gy))
    field = np.maximum(fault, shear * 0.55)
    field = np.power(_norm(field), 0.85)
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- registry
ENGINES = {
    "impact_shatter":  impact_shatter,
    "crack_network":   crack_network,
    "claw_rake":       claw_rake,
    "ember_burst":     ember_burst,
    "glitch_mosh":     glitch_mosh,
    "dazzle_razor":    dazzle_razor,
    "warp_moire":      warp_moire,
    "blade_fan":       blade_fan,
    "arc_lattice":     arc_lattice,
    "tread_shred":     tread_shred,
    "stress_fracture": stress_fracture,
}

DESCRIPTIONS = {
    "impact_shatter":  "Radial impact star — sharp spoke cracks + concentric stress rings from impact points",
    "crack_network":   "Dense propagating crack network — branching crack-tip walks + glass tile shading",
    "claw_rake":       "Shredded claw-rake gouges — curved parallel deep grooves with torn ridges",
    "ember_burst":     "Dense ember/spark burst — motion-streaked spark cores over heat haze",
    "glitch_mosh":     "Glitch datamosh — scanline tears, macroblock displacement, pixel-sort smear",
    "dazzle_razor":    "Dazzle-camo razor stripes — hard B/W stripes in angular faceted zones",
    "warp_moire":      "Aggressive op-art moire — hard square-wave grids beating under radial pinch",
    "blade_fan":       "Kaleido-blade shard fans — hard triangular blades fanning from pivots",
    "arc_lattice":     "Dense electric-arc lattice — jagged arcs jumping a jittered charged node grid",
    "tread_shred":     "Tire-shred tread chunks — chunky tread lugs torn apart into rubber shreds",
    "stress_fracture": "Stress-field fracture — fault lines carved where shear stress beats noisy yield",
}


# ----------------------------------------------------------------------------- self-test
if __name__ == "__main__":
    import time

    def _n(f):
        return (f - f.min()) / (np.ptp(f) + 1e-9)

    SZ = 1024
    fails = []
    print(f"{'engine':18s} {'fine':>6s} {'cover':>6s} {'edge':>6s} {'sec':>6s}  result")
    print("-" * 60)
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(SZ, SZ, 12345)
        dt = time.time() - t0
        f = f.astype(np.float32)
        ok = True
        msgs = []
        if not np.all(np.isfinite(f)):
            ok = False; msgs.append("NaN/inf")
        if f.min() < -1e-4 or f.max() > 1 + 1e-4:
            ok = False; msgs.append(f"range[{f.min():.3f},{f.max():.3f}]")
        fineness = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
        # coverage over 8x8 grid
        gh, gw = SZ // 8, SZ // 8
        covs = []
        for j in range(8):
            for i in range(8):
                cell = f[j * gh:(j + 1) * gh, i * gw:(i + 1) * gw]
                covs.append(cell.std() > 0.035)
        coverage = float(np.mean(covs))
        sx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
        mag = _n(np.hypot(sx, sy))
        edge_density = float(np.mean(mag > 0.18))
        if fineness < 0.12:
            ok = False; msgs.append(f"fineness {fineness:.3f}")
        if coverage < 0.82:
            ok = False; msgs.append(f"coverage {coverage:.3f}")
        if edge_density < 0.12:
            ok = False; msgs.append(f"edge {edge_density:.3f}")
        if dt > 2.5:
            ok = False; msgs.append(f"slow {dt:.2f}s")
        status = "PASS" if ok else "FAIL " + ",".join(msgs)
        if not ok:
            fails.append(name)
        print(f"{name:18s} {fineness:6.3f} {coverage:6.3f} {edge_density:6.3f} {dt:6.2f}  {status}")
    print("-" * 60)
    if fails:
        raise SystemExit(f"FAILED: {fails}")
    print("ALL PASS")
