"""3D STACKING / HEIGHT / DEPTH-ILLUSION FIELDS — generative-math engines for SPB.

Every engine here builds a HEIGHT field and renders it so the surface reads as
PHYSICAL RELIEF rising off the panel: discrete quantized strata + directional
(light-vector) shading of the risers, with crisp full-coverage structure. None of
these is a recolor of another — each is a distinct height-construction algorithm.

  * terraced_strata     — fBm elevation quantized into contour plateaus; risers shaded
                          by the up-slope so it reads like a topographic relief model.
  * voxel_cityscape     — isometric stacked-cube cityscape: a per-cell tower height map
                          extruded into a fake-3D iso projection (top/left/right faces).
  * drop_shadow_plates  — offset layered plates: stacked thresholded sheets each casting a
                          hard directional drop-shadow onto the layer below.
  * extruded_tessellation — Voronoi-cell prisms extruded to quantized heights with bevelled
                          shaded side-walls (towers of irregular polygons).
  * beveled_panels      — embossed multi-panel grid; each rounded-rect panel sits at a
                          stepped height with bevel highlights/shadows on its edges.
  * depth_portal        — recursive concentric portal/tunnel: nested rectangular frames
                          receding to a vanishing point with stepped wall shading.
  * parallax_grids      — several quantized grids at different scales/offsets stacked with
                          depth-attenuated shading -> parallax layered lattice.
  * stepped_pyramid     — distance-transform ziggurats: random footprints whose stepped
                          plateaus + shaded steps build a pyramid lattice.
  * cut_paper_relief    — layered cut-paper: many soft blobs hard-quantized into stacked
                          paper sheets, each edge given a contact-shadow lip.
  * greeble_heightmap   — mechanical greeble plating: recursive panel subdivision with
                          per-tile extruded boxes, vents and rivets, hard-shaded.
  * isometric_blocks    — brick/parallelepiped stagger: offset rows of iso blocks at
                          quantized heights forming a staggered 3D wall.

Pure numpy + cv2 + scipy. Deterministic by seed. Computed low-res then upscaled.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy import ndimage


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xffffffff)


def _norm(a):
    a = a.astype(np.float32)
    p = float(np.ptp(a))
    return (a - a.min()) / (p + 1e-9)


def _up(field, h, w):
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _fbm(res, rng, octaves=5, base=4, gain=0.55):
    """Periodic fractal value noise via summed upsampled white-noise lattices."""
    out = np.zeros((res, res), np.float32)
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        n = min(base * (2 ** o), res)
        lat = rng.standard_normal((n, n)).astype(np.float32)
        layer = cv2.resize(lat, (res, res), interpolation=cv2.INTER_CUBIC)
        out += amp * layer
        tot += amp
        amp *= gain
    return _norm(out / (tot + 1e-9))


def _shade(height, lx=-0.7, ly=-0.7, ka=0.45, kd=0.9):
    """Lambert-ish shade of a height field: ambient + diffuse(light . normal).
    Returns a [0..1] relief image where up-slopes facing the light are bright."""
    gy, gx = np.gradient(height.astype(np.float32))
    nz = np.ones_like(gx)
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + nz * nz + 1e-9)
    nx, ny, nz = -gx * inv, -gy * inv, nz * inv
    ll = 1.0 / np.sqrt(lx * lx + ly * ly + 1.0)
    lxx, lyy, lzz = lx * ll, ly * ll, 1.0 * ll
    diff = np.clip(nx * lxx + ny * lyy + nz * lzz, 0.0, 1.0)
    return np.clip(ka + kd * diff, 0.0, 1.0)


def _quantize(x, levels):
    return np.round(_norm(x) * (levels - 1)) / (levels - 1)


def _emboss_steps(img, sigma=1.0, k=1.2):
    """Add hard high-pass step edges so quantized fields keep crisp risers after upscale."""
    hp = img - cv2.GaussianBlur(img, (0, 0), sigma)
    return np.clip(img + k * hp, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 1. TERRACED STRATA — quantized topographic relief with shaded risers
# ---------------------------------------------------------------------------
def terraced_strata(h, w, seed, *, res=512):
    rng = _rng(seed)
    elev = _fbm(res, rng, octaves=6, base=3, gain=0.58)
    # ridge fold to get sharper plateaus
    elev = _norm(np.abs(elev - 0.5))
    elev = _norm(elev + 0.4 * _fbm(res, rng, octaves=4, base=6))
    levels = int(rng.integers(9, 14))
    terr = _quantize(elev, levels)
    # riser shading: where the quantized step jumps, brighten the up-slope edge
    relief = _shade(cv2.GaussianBlur(terr, (0, 0), 1.0), lx=-0.8, ly=-0.6, ka=0.35, kd=1.1)
    # hard contour lines at each terrace boundary
    gy, gx = np.gradient(terr)
    risers = _norm(np.hypot(gx, gy))
    risers = (risers > 0.02).astype(np.float32)
    plateau_tone = 0.30 + 0.70 * terr           # higher terraces are brighter
    out = plateau_tone * (0.55 + 0.45 * relief)
    out = np.clip(out - 0.55 * risers, 0.0, 1.0)  # dark crisp riser cliffs
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 2. VOXEL CITYSCAPE — isometric stacked-cube tower field
# ---------------------------------------------------------------------------
def voxel_cityscape(h, w, seed, *, res=512):
    rng = _rng(seed)
    g = int(rng.integers(20, 28))               # grid of towers
    base = rng.random((g, g)).astype(np.float32)
    base = cv2.resize(base, (g, g))
    # cluster heights with a low-freq mask so skyline has districts
    mask = _fbm(g, rng, octaves=3, base=2)
    height = _quantize(base * (0.4 + 0.9 * mask), int(rng.integers(6, 10)))
    cell = res // g
    res2 = cell * g
    img = np.zeros((res2, res2), np.float32)
    # iso-ish stacking: draw each tower as top + two shaded side faces, painter's order
    sh = max(2, cell // 3)                        # extrusion shear in pixels per height unit
    order = np.argsort(height.ravel())            # short towers first (back), tall last
    top_tone, left_tone, right_tone = 1.0, 0.45, 0.72
    for idx in order:
        r, c = divmod(int(idx), g)
        y0, x0 = r * cell, c * cell
        hpx = int(round(height[r, c] * sh * 4)) + 1
        # right side face (offset down-right) — darker
        rect = np.zeros((cell + hpx, cell), np.float32)
        # left/right faces drawn as vertical extrusion underneath the top
        img[y0:y0 + cell, x0:x0 + cell] = 0.0
        # extruded body (the riser) below the top
        yb = min(res2, y0 + cell + hpx)
        img[y0 + cell // 2:yb, x0:x0 + cell] = left_tone
        # top face
        img[y0:y0 + cell, x0:x0 + cell] = top_tone * (0.5 + 0.5 * height[r, c])
        # right column shadow stripe for face separation
        img[y0:yb, x0 + cell - max(1, cell // 4):x0 + cell] = right_tone
    # grout/edge lines between cells -> crisp city blocks
    img = cv2.resize(img, (res, res), interpolation=cv2.INTER_NEAREST)
    edge = np.zeros_like(img)
    edge[::cell, :] = 1.0
    edge[:, ::cell] = 1.0
    img = np.clip(img - 0.5 * edge, 0.0, 1.0)
    return _norm(_up(img, h, w))


# ---------------------------------------------------------------------------
# 3. DROP-SHADOW PLATES — stacked sheets each casting a hard offset shadow
# ---------------------------------------------------------------------------
def drop_shadow_plates(h, w, seed, *, res=512):
    rng = _rng(seed)
    nlayers = int(rng.integers(7, 10))
    canvas = np.full((res, res), 0.15, np.float32)
    off = max(4, res // 70)
    for k in range(nlayers):
        # each plate is a hard-thresholded MEDIUM-scale blob set (finer base)
        f = _fbm(res, rng, octaves=5, base=int(rng.integers(5, 9)))
        thr = float(np.quantile(f, rng.uniform(0.50, 0.66)))
        plate = (f > thr).astype(np.float32)
        plate = cv2.morphologyEx(plate, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        # cast a hard drop-shadow of this plate down-right onto whatever's below
        sh = np.roll(np.roll(plate, off, 0), off, 1)
        canvas = np.where((sh > 0) & (plate == 0), canvas * 0.30, canvas)
        # the plate itself: tone steps up per layer (higher = brighter/closer),
        # with fine machined GROOVE lines so each plate reads as relief, not a flat blob
        gf = _fbm(res, rng, octaves=4, base=12)
        grooves = (np.cos(_norm(gf) * np.pi * 2 * 9.0) > 0.4).astype(np.float32)
        tone = (0.32 + 0.62 * (k + 1) / nlayers)
        face = np.clip(tone - 0.22 * grooves, 0, 1)
        canvas = np.where(plate > 0, face, canvas)
        # bright catch-light lip on the top-left edge of each plate
        lip = np.clip(plate - cv2.erode(plate, np.ones((3, 3), np.uint8)), 0, 1)
        lip = cv2.dilate(lip, np.ones((2, 2), np.uint8))
        canvas = np.clip(canvas + 0.55 * lip, 0.0, 1.0)
    return _norm(_up(_emboss_steps(canvas, sigma=1.0, k=1.0), h, w))


# ---------------------------------------------------------------------------
# 4. EXTRUDED TESSELLATION — Voronoi prisms at quantized heights, bevelled walls
# ---------------------------------------------------------------------------
def extruded_tessellation(h, w, seed, *, res=440):
    rng = _rng(seed)
    npts = int(rng.integers(320, 420))
    pts = rng.random((npts, 2)).astype(np.float32) * res
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    d2 = (xx[..., None] - pts[:, 0]) ** 2 + (yy[..., None] - pts[:, 1]) ** 2
    label = np.argmin(d2, axis=2)
    f1 = np.sqrt(np.min(d2, axis=2))
    # each cell gets a random quantized extrusion height
    cell_h = _quantize(rng.random(npts).astype(np.float32), int(rng.integers(5, 9)))
    height = cell_h[label]
    # per-cell flat tone with relief shading from the height steps between cells
    relief = _shade(cv2.GaussianBlur(height, (0, 0), 1.2), lx=-0.7, ly=-0.8,
                    ka=0.4, kd=1.2)
    tone = (0.22 + 0.78 * height) * (0.45 + 0.55 * relief)
    # crisp dark cell walls + bright top-left rim on every cell (the bevel)
    wall = _norm(f1)
    walls = (wall < 0.04).astype(np.float32)
    walls = cv2.dilate(walls, np.ones((2, 2), np.uint8))
    # bright rim: pixels close to wall on the light side
    rim = ((wall >= 0.04) & (wall < 0.10)).astype(np.float32)
    out = np.clip(tone - 0.55 * walls + 0.3 * rim, 0.0, 1.0)
    return _norm(_up(_emboss_steps(out, sigma=1.0, k=0.9), h, w))


# ---------------------------------------------------------------------------
# 5. BEVELED PANELS — embossed stepped multi-panel grid
# ---------------------------------------------------------------------------
def beveled_panels(h, w, seed, *, res=512):
    rng = _rng(seed)
    g = int(rng.integers(11, 15))
    cell = res // g
    res2 = cell * g
    height = _quantize(rng.random((g, g)).astype(np.float32), int(rng.integers(4, 7)))
    tone = np.full((res2, res2), 0.06, np.float32)   # dark gaps
    gap = max(2, cell // 10)
    bw = max(3, cell // 5)                             # bevel width in px
    for r in range(g):
        for c in range(g):
            y0, x0 = r * cell + gap, c * cell + gap
            y1, x1 = (r + 1) * cell - gap, (c + 1) * cell - gap
            face = 0.30 + 0.70 * height[r, c]
            tone[y0:y1, x0:x1] = face
            # hard bevels: bright top + left, dark bottom + right (raised emboss)
            tone[y0:y0 + bw, x0:x1] = np.clip(face + 0.40, 0, 1)   # top hi
            tone[y0:y1, x0:x0 + bw] = np.clip(face + 0.30, 0, 1)   # left hi
            tone[y1 - bw:y1, x0:x1] = np.clip(face - 0.35, 0, 1)   # bottom lo
            tone[y0:y1, x1 - bw:x1] = np.clip(face - 0.28, 0, 1)   # right lo
    out = cv2.resize(tone, (res, res), interpolation=cv2.INTER_LINEAR)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 6. DEPTH PORTAL — recursive receding rectangular tunnel
# ---------------------------------------------------------------------------
def depth_portal(h, w, seed, *, res=512):
    rng = _rng(seed)
    # multiple vanishing points so the whole field is full of nested portals
    nport = int(rng.integers(6, 10))
    img = np.zeros((res, res), np.float32)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    for _ in range(nport):
        cx, cy = rng.uniform(0.1, 0.9, 2) * res
        ang = rng.uniform(0, np.pi)
        ca, sa = np.cos(ang), np.sin(ang)
        u = (xx - cx) * ca + (yy - cy) * sa
        v = -(xx - cx) * sa + (yy - cy) * ca
        # chebyshev distance -> nested SQUARE frames; LINEAR spacing = uniform rings
        cheb = np.maximum(np.abs(u), np.abs(v))
        ringw = rng.uniform(7.0, 10.0)           # ring period in px (fine, uniform)
        idx = np.floor(cheb / ringw)
        frac = cheb / ringw - idx                 # 0..1 within a ring
        depth = _norm(cheb)
        # alternate-step shading gives wall/floor of the tunnel
        step = (idx.astype(np.int32) % 2).astype(np.float32)
        local = (0.25 + 0.75 * (1.0 - depth)) * (0.50 + 0.50 * step)
        # hard dark riser + bright sill at every ring boundary -> dense crisp edges
        riser = (frac < 0.22).astype(np.float32)
        sill = (frac > 0.80).astype(np.float32)
        local = np.clip(local - 0.45 * riser + 0.25 * sill, 0, 1)
        img = np.maximum(img, local)
    img = _norm(img)
    return _norm(_up(_emboss_steps(img, sigma=0.9, k=1.0), h, w))


# ---------------------------------------------------------------------------
# 7. PARALLAX GRIDS — quantized lattices stacked at depth
# ---------------------------------------------------------------------------
def parallax_grids(h, w, seed, *, res=512):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    nlayers = int(rng.integers(4, 6))
    acc = np.zeros((res, res), np.float32)
    for k in range(nlayers):
        freq = (k + 1) * rng.uniform(7.0, 11.0)
        ph = rng.uniform(0, np.pi, 2)
        off = rng.uniform(0, 6.28)
        # square-wave grid -> crisp bars, not soft sine
        gx = (np.cos(xx / res * freq * 2 * np.pi + ph[0]) > 0.2).astype(np.float32)
        gy = (np.cos(yy / res * freq * 2 * np.pi + ph[1] + off) > 0.2).astype(np.float32)
        grid = np.maximum(gx, gy)
        # depth tone + a hard drop-shadow offset to fake stacking
        depth_tone = 0.25 + 0.75 * (k + 1) / nlayers
        o = (nlayers - k) * 2
        shadow = np.roll(np.roll(grid, o, 0), o, 1)
        acc = np.where(shadow > 0, acc * 0.5, acc)
        acc = np.where(grid > 0, depth_tone, acc)
    # quantized backfill so nothing is bare
    bg = _quantize(_fbm(res, rng, octaves=3, base=4), 4) * 0.3
    acc = np.where(acc <= 0.0, bg, acc)
    # emboss the whole stack a touch for relief
    acc = _norm(acc + 0.5 * (acc - cv2.GaussianBlur(acc, (0, 0), 2.0)))
    return _norm(_up(acc, h, w))


# ---------------------------------------------------------------------------
# 8. STEPPED PYRAMID — distance-transform ziggurats
# ---------------------------------------------------------------------------
def stepped_pyramid(h, w, seed, *, res=512):
    rng = _rng(seed)
    seeds = np.zeros((res, res), np.uint8) + 1
    n = int(rng.integers(18, 30))
    # carve random rectangular footprints whose interiors are the pyramid bases
    for _ in range(n):
        rw = int(rng.integers(res // 12, res // 4))
        rh = int(rng.integers(res // 12, res // 4))
        y0 = int(rng.integers(0, res - rh))
        x0 = int(rng.integers(0, res - rw))
        seeds[y0:y0 + rh, x0:x0 + rw] = 0   # background between footprints
    # distance INTO each footprint -> stepped plateaus = ziggurat
    inside = (seeds == 1).astype(np.uint8)
    dist = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
    # FINE stepped plateaus: fixed step PERIOD in px so steps are uniform & dense
    stepw = rng.uniform(8.0, 13.0)
    lvl = np.floor(dist / stepw)
    height = _norm(lvl)
    relief = _shade(cv2.GaussianBlur(height, (0, 0), 1.0), lx=-0.7, ly=-0.7,
                    ka=0.35, kd=1.15)
    tone = (0.25 + 0.75 * height) * (0.5 + 0.5 * relief)
    # crisp dark riser at every integer step boundary
    risers = (np.abs(dist - (lvl * stepw) - 1.0) < 1.6).astype(np.float32)
    out = np.clip(tone - 0.5 * risers, 0.0, 1.0)
    # background between ziggurats: dense stepped ripple so coverage/edges stay high
    bgd = cv2.distanceTransform((1 - inside).astype(np.uint8), cv2.DIST_L2, 5)
    bgl = np.floor(bgd / (stepw * 0.7))
    bg = 0.06 + 0.16 * _norm(bgl)
    bgr = (np.abs(bgd - bgl * stepw * 0.7 - 1.0) < 1.4).astype(np.float32)
    bg = np.clip(bg + 0.12 * bgr, 0, 1)
    out = np.where(inside > 0, out, bg)
    return _norm(_up(_emboss_steps(out, sigma=1.0, k=0.8), h, w))


# ---------------------------------------------------------------------------
# 9. CUT-PAPER RELIEF — stacked hard-quantized paper sheets with contact shadows
# ---------------------------------------------------------------------------
def cut_paper_relief(h, w, seed, *, res=512):
    rng = _rng(seed)
    field = _fbm(res, rng, octaves=5, base=3, gain=0.6)
    field = _norm(field + 0.5 * _fbm(res, rng, octaves=4, base=7))
    layers = int(rng.integers(7, 11))
    q = _quantize(field, layers)
    levels = np.round(q * (layers - 1)).astype(np.int32)
    canvas = np.zeros((res, res), np.float32)
    for L in range(layers):
        sheet = (levels >= L).astype(np.float32)   # everything at/above this height
        # contact shadow: dark lip just OUTSIDE each sheet's lower-right boundary
        grow = cv2.dilate(sheet, np.ones((5, 5), np.uint8))
        shadow = np.clip(grow - sheet, 0, 1)
        shadow = np.roll(np.roll(shadow, 3, 0), 3, 1)
        canvas = np.where(shadow > 0, canvas * 0.5, canvas)
        tone = 0.25 + 0.7 * L / (layers - 1)
        canvas = np.where(sheet > 0, tone, canvas)
        # bright cut-edge highlight on the upper-left (dilated to survive upscale)
        edge = np.clip(sheet - cv2.erode(sheet, np.ones((3, 3), np.uint8)), 0, 1)
        edge = cv2.dilate(edge, np.ones((2, 2), np.uint8))
        canvas = np.clip(canvas + 0.45 * edge, 0.0, 1.0)
    return _norm(_up(_emboss_steps(canvas, sigma=0.9, k=0.7), h, w))


# ---------------------------------------------------------------------------
# 10. GREEBLE HEIGHTMAP — recursive mechanical panel plating
# ---------------------------------------------------------------------------
def greeble_heightmap(h, w, seed, *, res=512):
    rng = _rng(seed)
    height = np.zeros((res, res), np.float32)
    # recursive binary-space partition of the panel into greeble boxes.
    # Pre-tile into a coarse grid so subdivision is ALWAYS dense regardless of seed.
    pg = 5
    pc = res // pg
    boxes = []
    stack = [(c * pc, r * pc, (c + 1) * pc, (r + 1) * pc, 0)
             for r in range(pg) for c in range(pg)]
    while stack:
        x0, y0, x1, y1, d = stack.pop()
        wsz, hsz = x1 - x0, y1 - y0
        if d >= 4 or min(wsz, hsz) < res // 28 or (d >= 2 and rng.random() < 0.30):
            boxes.append((x0, y0, x1, y1))
            continue
        if wsz >= hsz:
            cut = int(rng.uniform(0.35, 0.65) * wsz) + x0
            stack.append((x0, y0, cut, y1, d + 1))
            stack.append((cut, y0, x1, y1, d + 1))
        else:
            cut = int(rng.uniform(0.35, 0.65) * hsz) + y0
            stack.append((x0, y0, x1, cut, d + 1))
            stack.append((x0, cut, x1, y1, d + 1))
    levels = int(rng.integers(5, 8))
    tone = np.full((res, res), 0.05, np.float32)   # dark recessed gutters
    for (x0, y0, x1, y1) in boxes:
        m = max(1, (x1 - x0) // 14)
        bx0, by0, bx1, by1 = x0 + m, y0 + m, x1 - m, y1 - m
        if bx1 - bx0 < 4 or by1 - by0 < 4:
            continue
        lv = round(rng.random() * (levels - 1)) / (levels - 1)
        face = 0.30 + 0.55 * lv
        tone[by0:by1, bx0:bx1] = face
        bw2 = max(2, m)
        # hard extruded bevel: bright top/left, dark bottom/right
        tone[by0:by0 + bw2, bx0:bx1] = min(1.0, face + 0.40)
        tone[by0:by1, bx0:bx0 + bw2] = min(1.0, face + 0.32)
        tone[by1 - bw2:by1, bx0:bx1] = max(0.0, face - 0.32)
        tone[by0:by1, bx1 - bw2:bx1] = max(0.0, face - 0.26)
        # greeble details: vents (dark stripes) or a raised bright stud
        det = rng.random()
        if det < 0.45 and (bx1 - bx0) > 12:
            for vx in range(bx0 + bw2 + 2, bx1 - bw2 - 1, 5):
                tone[by0 + bw2:by1 - bw2, vx:vx + 2] = max(0.0, face - 0.30)
        elif det < 0.75 and (by1 - by0) > 12:
            cyx, cxx = (by0 + by1) // 2, (bx0 + bx1) // 2
            rr = max(2, (by1 - by0) // 6)
            tone[cyx - rr:cyx + rr, cxx - rr:cxx + rr] = min(1.0, face + 0.45)
    out = np.clip(tone, 0.0, 1.0)
    return _norm(_up(_emboss_steps(out, sigma=0.9, k=0.7), h, w))


# ---------------------------------------------------------------------------
# 11. ISOMETRIC BLOCKS — staggered brick wall of extruded parallelepipeds
# ---------------------------------------------------------------------------
def isometric_blocks(h, w, seed, *, res=512):
    rng = _rng(seed)
    rows = int(rng.integers(26, 34))
    ch = res // rows
    res2 = ch * rows
    bw = ch * 2                                  # bricks twice as wide as tall
    img = np.zeros((res2 + bw, res2 + bw), np.float32)
    sh = max(2, ch // 2)                          # extrusion depth
    for r in range(rows + 1):
        y0 = r * ch
        stagger = (r % 2) * (bw // 2)
        ncols = res2 // bw + 2
        for c in range(ncols):
            x0 = c * bw - stagger
            if x0 + bw < 0 or x0 > res2:
                continue
            hgt = round(rng.random() * 5) / 5.0
            top = 0.55 + 0.45 * hgt
            # right side face (down-right) darker
            for dy in range(sh):
                yy = min(img.shape[0] - 1, y0 + ch + dy)
                xs = max(0, x0 + dy)
                xe = min(img.shape[1], x0 + bw + dy)
                if xs < xe:
                    img[yy, xs:xe] = 0.32
            # top face
            ys, xe = max(0, y0), max(0, x0)
            img[ys:y0 + ch, xe:x0 + bw] = top
            # mortar: bright lip on top + left edge, dark seam on right + bottom
            img[ys:y0 + ch, xe:xe + 2] = 0.97
            img[ys:ys + 2, xe:x0 + bw] = 0.97
            xr = min(img.shape[1], x0 + bw)
            img[ys:y0 + ch, max(0, xr - 2):xr] = 0.10
            img[max(0, y0 + ch - 2):y0 + ch, xe:x0 + bw] = 0.10
    img = img[:res2, :res2]
    img = cv2.resize(img, (res, res), interpolation=cv2.INTER_NEAREST)
    # emboss for extra relief punch (keeps the hard block edges crisp)
    img = _emboss_steps(img, sigma=1.0, k=0.9)
    return _norm(_up(img, h, w))


# ---------------------------------------------------------------------------
ENGINES = {
    "terraced_strata": terraced_strata,
    "voxel_cityscape": voxel_cityscape,
    "drop_shadow_plates": drop_shadow_plates,
    "extruded_tessellation": extruded_tessellation,
    "beveled_panels": beveled_panels,
    "depth_portal": depth_portal,
    "parallax_grids": parallax_grids,
    "stepped_pyramid": stepped_pyramid,
    "cut_paper_relief": cut_paper_relief,
    "greeble_heightmap": greeble_heightmap,
    "isometric_blocks": isometric_blocks,
}


if __name__ == "__main__":
    H = W = 1024

    def norm(f):
        return (f - f.min()) / (np.ptp(f) + 1e-9)

    def metrics(f):
        f = np.asarray(f, np.float32)
        fine = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
        # coverage over 8x8 grid
        gh, gw = f.shape[0] // 8, f.shape[1] // 8
        cov_hits = 0
        for r in range(8):
            for c in range(8):
                cell = f[r * gh:(r + 1) * gh, c * gw:(c + 1) * gw]
                if cell.std() > 0.035:
                    cov_hits += 1
        cov = cov_hits / 64.0
        sx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
        ed = float((norm(np.hypot(sx, sy)) > 0.18).mean())
        return fine, cov, ed

    print(f"{'engine':24s} {'secs':>6s} {'fine':>6s} {'cov':>6s} {'edge':>6s}  ok")
    allok = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, W, 12345)
        secs = time.time() - t0
        f = np.asarray(f, np.float32)
        finite = bool(np.isfinite(f).all())
        fine, cov, ed = metrics(f)
        ok = (secs < 2.5 and fine >= 0.12 and cov >= 0.82 and ed >= 0.12
              and finite and f.min() >= -1e-4 and f.max() <= 1.0 + 1e-4)
        allok = allok and ok
        print(f"{name:24s} {secs:6.3f} {fine:6.3f} {cov:6.3f} {ed:6.3f}  "
              f"{'OK' if ok else 'FAIL'}")
        if not ok:
            print(f"    -> finite={finite} min={f.min():.3f} max={f.max():.3f}")
    print("ALL PASS" if allok else "SOME FAILED")
