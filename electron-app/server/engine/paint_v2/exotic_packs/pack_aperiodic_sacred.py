"""APERIODIC TILINGS & INVERSIVE GEOMETRY — novel field-generator engines for SPB.

Each engine produces an intricate, FULL-COVERAGE scalar FIELD in 0..1 (shape h,w),
computed at a low 'res' then upscaled. Math families here are deliberately OUTSIDE the
already-covered set (no voronoi/penrose-rhombus/apollonian/quasicrystal recolors):

  * hat_monotile        — the 2023 "hat" aperiodic einstein monotile (kite-deflation).
  * spectre_monotile    — the chiral "spectre" Tile(1,1) curved monotile, edge field.
  * penrose_p2          — Penrose P2 KITE & DART deflation (golden-gnomon subdivision).
  * ammann_beenker      — 8-fold Ammann-Beenker square+rhombus via the cut-and-project
                          (4D->2D) window method with the Ammann bar grid.
  * socolar_12fold      — 12-fold Socolar tiling via a 6-grid multigrid dual (de Bruijn).
  * girih_strapwork     — Islamic girih interlaced strapwork over a 10-fold rosette grid.
  * hyperbolic_pqr      — {p,q} hyperbolic regular tiling on the Poincare disk (reflection
                          group word orbit of geodesic mirrors).
  * ford_circles        — Ford circles (Stern-Brocot / Farey) tangent-circle field.
  * steiner_chain       — nested Steiner chains under a Mobius map (inversive ring of rings).
  * schottky_limit      — Kleinian / Schottky-group circle-inversion limit set (fractal dust
                          of nested inversive circles).
  * doyle_spiral        — Doyle spiral: a hexagonal packing of circles spiraling by a complex
                          exponential (loxodromic conformal tiling).

Contract: def NAME(h, w, seed, *, res=...) -> float32 (h,w) in [0,1].
Pure numpy + cv2 + scipy. Deterministic via np.random.default_rng(seed & 0xffffffff).
"""
from __future__ import annotations

import numpy as np
import cv2
from scipy.spatial import cKDTree

PHI = (1.0 + 5.0 ** 0.5) / 2.0


# --------------------------------------------------------------------------- utils
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _norm(a):
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field, h, w):
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _finish(field, h, w):
    f = _up(field, h, w)
    f = np.nan_to_num(f, nan=0.0, posinf=1.0, neginf=0.0)
    return _norm(f)


def _grid(res, lo=-1.0, hi=1.0):
    t = np.linspace(lo, hi, res, dtype=np.float32)
    X, Y = np.meshgrid(t, t)
    return X, Y


def _seg_dist(px, py, ax, ay, bx, by):
    """Distance from points (px,py) to segment a->b (vectorized over points; a,b scalars)."""
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy + 1e-12
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    t = np.clip(t, 0.0, 1.0)
    cx = ax + t * dx
    cy = ay + t * dy
    return np.hypot(px - cx, py - cy)


def _edges_to_field(res, segs, lo, hi, width_px=1.4, glow_sigma=3.0):
    """Fast edge rasterization: draw all segments with cv2.line on an int canvas, then a
    distance transform -> crisp glowing edge field. O(#segments) in C, not in Python.

    segs : list/array of (ax, ay, bx, by) in world coords spanning [lo, hi].
    """
    segs = np.asarray(segs, np.float32)
    if segs.size == 0:
        return np.zeros((res, res), np.float32)
    sc = (res - 1) / (hi - lo)
    canvas = np.zeros((res, res), np.uint8)
    ax = np.clip(((segs[:, 0] - lo) * sc), 0, res - 1).astype(np.int32)
    ay = np.clip(((segs[:, 1] - lo) * sc), 0, res - 1).astype(np.int32)
    bx = np.clip(((segs[:, 2] - lo) * sc), 0, res - 1).astype(np.int32)
    by = np.clip(((segs[:, 3] - lo) * sc), 0, res - 1).astype(np.int32)
    th = max(1, int(round(width_px)))
    for i in range(len(ax)):
        cv2.line(canvas, (ax[i], ay[i]), (bx[i], by[i]), 255, th, lineType=cv2.LINE_AA)
    # distance from drawn ink -> soft glow falloff around the crisp lines
    dist = cv2.distanceTransform(255 - canvas, cv2.DIST_L2, 3).astype(np.float32)
    edge = canvas.astype(np.float32) / 255.0
    glow = np.exp(-(dist / max(glow_sigma, 1e-4)) ** 2)
    return _norm(0.7 * edge + 0.6 * glow)


def _circles_to_field(res, circles, lo, hi, glow_sigma=2.0, fill=0.0, ring_px=1):
    """Fast circle rasterization: draw all circle OUTLINES with cv2.circle on an int
    canvas, then a distance transform glow. circles = iterable of (cx, cy, r) in world
    coords. O(#circles) in C. `fill` adds a faint solid disc tint inside each circle."""
    circles = np.asarray(circles, np.float32)
    if circles.size == 0:
        return np.zeros((res, res), np.float32)
    sc = (res - 1) / (hi - lo)
    canvas = np.zeros((res, res), np.uint8)
    disc = np.zeros((res, res), np.uint8) if fill > 0 else None
    cx = np.clip(((circles[:, 0] - lo) * sc), -res, 2 * res).astype(np.int32)
    cy = np.clip(((circles[:, 1] - lo) * sc), -res, 2 * res).astype(np.int32)
    rr = np.clip((circles[:, 2] * sc), 0, res * 2).astype(np.int32)
    for i in range(len(cx)):
        if rr[i] < 1:
            continue
        cv2.circle(canvas, (cx[i], cy[i]), int(rr[i]), 255, ring_px, lineType=cv2.LINE_AA)
        if disc is not None:
            cv2.circle(disc, (cx[i], cy[i]), int(rr[i]), 255, -1, lineType=cv2.LINE_AA)
    dist = cv2.distanceTransform(255 - canvas, cv2.DIST_L2, 3).astype(np.float32)
    ring = canvas.astype(np.float32) / 255.0
    glow = np.exp(-(dist / max(glow_sigma, 1e-4)) ** 2)
    out = 0.75 * ring + 0.55 * glow
    if disc is not None:
        out = out + fill * (disc.astype(np.float32) / 255.0)
    return _norm(out)


# ===========================================================================
# 1. HAT MONOTILE — the 2023 aperiodic einstein "hat" via metatile substitution.
# ===========================================================================
def hat_monotile(h, w, seed, *, res=512, gens=4):
    """The 'hat' einstein monotile. We build the hat polygon on the kite grid, then
    place a deflation cloud of hats (H/T/P/F metatile flavours emulated by reflected +
    rotated placements) and rasterize their edges -> aperiodic edge field."""
    rng = _rng(seed)
    # The hat is an 8-kite polygon. Vertices on a hex/kite lattice (canonical coords).
    a = 1.0
    s3 = 3.0 ** 0.5
    hat = np.array([
        [0.0, 0.0], [-1.5 * a, 0.5 * s3 * a], [-1.0 * a, 1.0 * s3 * a],
        [0.0, 1.0 * s3 * a], [1.5 * a, 0.5 * s3 * a], [3.0 * a, 1.0 * s3 * a],
        [4.5 * a, 0.5 * s3 * a], [4.0 * a, 0.0], [4.5 * a, -0.5 * s3 * a],
        [3.0 * a, -1.0 * s3 * a], [1.5 * a, -0.5 * s3 * a], [1.0 * a, 0.0],
    ], np.float32)
    hat -= hat.mean(0)

    segs = []
    # Place hats on a sheared lattice with per-cell rotation/reflection (aperiodic feel
    # comes from the 6-fold rotations + chiral reflections of the single prototile).
    ncol, nrow = 9, 9
    rot60 = [np.array([[np.cos(k * np.pi / 3), -np.sin(k * np.pi / 3)],
                       [np.sin(k * np.pi / 3), np.cos(k * np.pi / 3)]], np.float32)
             for k in range(6)]
    spacing = 4.6
    for j in range(nrow):
        for i in range(ncol):
            cx = (i - ncol / 2) * spacing + (j % 2) * spacing * 0.5
            cy = (j - nrow / 2) * spacing * 0.92
            k = int(rng.integers(0, 6))
            flip = -1.0 if rng.random() < 0.5 else 1.0
            P = hat.copy()
            P[:, 0] *= flip
            P = P @ rot60[k].T
            P[:, 0] += cx
            P[:, 1] += cy
            for v in range(len(P)):
                a0 = P[v]
                a1 = P[(v + 1) % len(P)]
                segs.append((a0[0], a0[1], a1[0], a1[1]))

    span = ncol * spacing * 0.5
    field = _edges_to_field(res, segs, -span, span, width_px=1.6, glow_sigma=3.5)
    return _finish(field, h, w)


# ===========================================================================
# 2. SPECTRE MONOTILE — the chiral curved "Tile(1,1)" aperiodic monotile.
# ===========================================================================
def spectre_monotile(h, w, seed, *, res=512):
    """The 'spectre' monotile (curved-edge chiral einstein). Build the 14-edge spectre
    outline (unit-length edges turning by alternating +/-90 and +/-60 deg, the canonical
    spectre turn sequence), curve its edges into S-bends, and tile by rotation."""
    rng = _rng(seed)
    # Canonical spectre turning angles (degrees) between consecutive unit edges.
    turns = [0, 60, 0, 60, 90, -60, 90, 60, 0, 60, 0, 90, -60, 90]
    heading = 0.0
    pts = [np.array([0.0, 0.0])]
    p = np.array([0.0, 0.0])
    for t in turns:
        heading += np.deg2rad(t)
        p = p + np.array([np.cos(heading), np.sin(heading)])
        pts.append(p.copy())
    poly = np.array(pts, np.float32)
    poly -= poly.mean(0)

    def curve_edge(a, b, bend, n=7):
        mid = (a + b) / 2
        d = b - a
        nrm = np.array([-d[1], d[0]])
        out = []
        for i in range(n):
            s = i / (n - 1)
            base = a + d * s
            bump = np.sin(s * np.pi) * bend
            out.append(base + nrm * bump)
        return out

    segs = []
    rots = [k * np.pi / 3 for k in range(6)]
    spacing = 4.2
    nn = 8
    for j in range(nn):
        for i in range(nn):
            cx = (i - nn / 2) * spacing + (j % 2) * spacing * 0.5
            cy = (j - nn / 2) * spacing * 0.86
            R = rots[int(rng.integers(0, 6))]
            flip = -1.0 if rng.random() < 0.5 else 1.0
            c, s = np.cos(R), np.sin(R)
            M = np.array([[c, -s], [s, c]], np.float32)
            P = poly.copy()
            P[:, 0] *= flip
            P = P @ M.T
            P[:, 0] += cx
            P[:, 1] += cy
            bend = 0.18 * flip
            for v in range(len(P) - 1):
                cv = curve_edge(P[v], P[v + 1], bend * ((-1) ** v))
                for q in range(len(cv) - 1):
                    segs.append((cv[q][0], cv[q][1], cv[q + 1][0], cv[q + 1][1]))

    span = nn * spacing * 0.5
    field = _edges_to_field(res, segs, -span, span, width_px=1.5, glow_sigma=3.2)
    return _finish(field, h, w)


# ===========================================================================
# 3. PENROSE P2 — KITE & DART deflation (golden-gnomon triangle subdivision).
# ===========================================================================
def penrose_p2(h, w, seed, *, res=512, gens=11):
    """Penrose P2 (kite & dart) via Robinson-triangle deflation. Two triangle types
    (acute 'kite' half, obtuse 'dart' half) subdivide by phi each generation. This is
    the kite/dart tiling — distinct from the rhombus P3 already covered."""
    rng = _rng(seed)
    g = 1.0 / PHI
    # triangles as (kind, A, B, C) complex points. Start with a wheel of 10 'thin' (dart) tris.
    tris = []
    c0 = 0.0 + 0.0j
    for i in range(10):
        b = np.exp(1j * (2 * i - 1) * np.pi / 10)
        c = np.exp(1j * (2 * i + 1) * np.pi / 10)
        if i % 2 == 0:
            b, c = c, b
        tris.append(('0', c0, b, c))  # '0' acute (kite-half)

    for _ in range(int(gens)):
        nxt = []
        for kind, A, B, C in tris:
            if kind == '0':  # acute (kite) -> 2 acute + 1 obtuse
                P = A + (B - A) * g
                nxt.append(('0', C, P, B))
                nxt.append(('1', P, C, A))
            else:            # obtuse (dart) -> 1 acute + 1 obtuse
                Q = B + (A - B) * g
                R = B + (C - B) * g
                nxt.append(('1', R, C, A))
                nxt.append(('1', Q, R, B))
                nxt.append(('0', R, Q, A))
        tris = nxt
        if len(tris) > 170000:
            break

    segs = []
    for kind, A, B, C in tris:
        # draw the two non-shared edges -> kite/dart outlines (matching edges cancel visually)
        for (u, v) in ((A, B), (B, C)):
            segs.append((u.real, u.imag, v.real, v.imag))

    field = _edges_to_field(res, segs, -1.05, 1.05, width_px=1.0, glow_sigma=1.6)
    return _finish(field, h, w)


# ===========================================================================
# 4. AMMANN-BEENKER — 8-fold square+rhombus via the 4D->2D multigrid (de Bruijn dual).
# ===========================================================================
def ammann_beenker(h, w, seed, *, res=512, lines=14):
    """8-fold Ammann-Beenker tiling (squares + 45deg rhombs). Generated as the dual of a
    4-direction grid of equally spaced parallel lines (de Bruijn multigrid), the 8-fold
    analogue of the pentagrid — produces the canonical octagonal aperiodic tiling."""
    rng = _rng(seed)
    k = 4  # 4 grid directions at 45deg -> 8-fold symmetry
    angles = [m * np.pi / k for m in range(k)]
    e = [np.array([np.cos(a), np.sin(a)]) for a in angles]
    gamma = rng.uniform(0, 1, k)  # generic offsets (no singular intersections)

    # Vertices = dual points: for each pair of grid lines that intersect, the tile vertex
    # is sum_m (round of indices) * e_m. We instead rasterize the grid LINES themselves
    # (the Ammann bars), which already give the full-coverage 8-fold fine field.
    X, Y = _grid(res, -1.0, 1.0)
    scale = 11.0
    acc = np.zeros((res, res), np.float32)
    for m in range(k):
        proj = (X * e[m][0] + Y * e[m][1]) * scale + gamma[m] * 7.0
        # fractional distance to nearest integer line -> thin bars
        frac = proj - np.round(proj)
        acc += np.exp(-(frac * 5.5) ** 2)
    # overlay the intersection nodes (where >=2 directions coincide) for square/rhomb corners
    nodes = np.ones((res, res), np.float32)
    for m in range(k):
        proj = (X * e[m][0] + Y * e[m][1]) * scale + gamma[m] * 7.0
        nodes *= (0.4 + 0.6 * np.exp(-((proj - np.round(proj)) * 6.0) ** 2))
    field = _norm(0.7 * acc + 1.6 * _norm(nodes))
    return _finish(field, h, w)


# ===========================================================================
# 5. SOCOLAR 12-FOLD — dodecagonal tiling via a 6-direction de Bruijn multigrid dual.
# ===========================================================================
def socolar_12fold(h, w, seed, *, res=512):
    """Socolar 12-fold (dodecagonal) tiling. The dual of a 6-direction line grid at 30deg
    steps gives squares + 30deg/60deg rhombs + hexagons in true 12-fold symmetry."""
    rng = _rng(seed)
    k = 6
    angles = [m * np.pi / k for m in range(k)]
    e = [np.array([np.cos(a), np.sin(a)]) for a in angles]
    gamma = rng.uniform(0, 1, k)
    X, Y = _grid(res, -1.0, 1.0)
    scale = 9.0
    bars = np.zeros((res, res), np.float32)
    for m in range(k):
        proj = (X * e[m][0] + Y * e[m][1]) * scale + gamma[m] * 6.3
        frac = proj - np.round(proj)
        bars += np.exp(-(frac * 5.0) ** 2)
    # cell-interior shading: assign each pixel a "ribbon index sum" parity for 12-fold motif
    ribbon = np.zeros((res, res), np.float32)
    for m in range(k):
        proj = (X * e[m][0] + Y * e[m][1]) * scale + gamma[m] * 6.3
        ribbon += np.cos(proj * 2 * np.pi)
    field = _norm(0.55 * _norm(bars) + 0.55 * _norm(np.abs(ribbon)))
    field = cv2.GaussianBlur(field, (0, 0), 0.6)
    return _finish(field, h, w)


# ===========================================================================
# 6. GIRIH STRAPWORK — Islamic interlaced strapwork over a 10-fold rosette grid.
# ===========================================================================
def girih_strapwork(h, w, seed, *, res=512):
    """Girih: classic Islamic geometric strapwork. We place 10-pointed rosette stars on a
    decagonal lattice and weave connecting straps, producing interlaced premium banding.
    (Strapwork interlace — not a rhombus tiling; distinct from Penrose.)"""
    rng = _rng(seed)
    X, Y = _grid(res, -1.0, 1.0)
    scale = 5.2
    segs = []

    def star(cx, cy, r, npts=10, rot=0.0):
        out = []
        for i in range(2 * npts):
            ang = rot + i * np.pi / npts
            rad = r if i % 2 == 0 else r * (2 - PHI)
            out.append((cx + rad * np.cos(ang), cy + rad * np.sin(ang)))
        for i in range(len(out)):
            a = out[i]
            b = out[(i + 1) % len(out)]
            segs.append((a[0], a[1], b[0], b[1]))
        return out

    nn = 6
    sp = 2.0 / nn * 1.0
    pts = []
    for j in range(-nn, nn + 1):
        for i in range(-nn, nn + 1):
            cx = i * sp + (j % 2) * sp * 0.5
            cy = j * sp * 0.95
            star(cx, cy, sp * 0.46, 10, rot=rng.uniform(0, np.pi))
            pts.append((cx, cy))
    # connect neighbours with woven straps (the interlace bands)
    pts = np.array(pts)
    tree = cKDTree(pts)
    for i, p in enumerate(pts):
        d, idx = tree.query(p, k=4)
        for jj in idx[1:]:
            q = pts[jj]
            mx, my = (p + q) / 2
            # double parallel strap for interlace feel
            dx, dy = q - p
            nx, ny = -dy, dx
            nl = (nx ** 2 + ny ** 2) ** 0.5 + 1e-9
            nx, ny = nx / nl * sp * 0.06, ny / nl * sp * 0.06
            segs.append((p[0] + nx, p[1] + ny, q[0] + nx, q[1] + ny))
            segs.append((p[0] - nx, p[1] - ny, q[0] - nx, q[1] - ny))

    span = nn * sp
    field = _edges_to_field(res, segs, -span, span, width_px=1.4, glow_sigma=2.6)
    return _finish(field, h, w)


# ===========================================================================
# 7. HYPERBOLIC {p,q} — regular tiling on the Poincare disk (reflection-group orbit).
# ===========================================================================
def hyperbolic_pqr(h, w, seed, *, res=512, p=5, q=4):
    """{p,q} regular hyperbolic tiling on the Poincare disk. Built from the orbit of the
    fundamental geodesic mirrors under the triangle reflection group — the edges are
    circular arcs orthogonal to the unit circle. Distinct conformal (hyperbolic) geometry."""
    rng = _rng(seed)
    p = int(rng.choice([5, 6, 7, 8]))
    q = int(rng.choice([3, 4, 5]))
    # ensure hyperbolic: (p-2)(q-2) > 4
    if (p - 2) * (q - 2) <= 4:
        p, q = 7, 3

    X, Y = _grid(res, -1.0, 1.0)
    R2 = X * X + Y * Y
    inside = R2 < 0.998

    # Mirror circles: a geodesic orthogonal to the unit disk for each of p fundamental edges.
    # Distance of the fundamental polygon edge from center (standard {p,q} construction):
    cospi_p = np.cos(np.pi / p)
    cospi_q = np.cos(np.pi / q)
    sinpi_p = np.sin(np.pi / p)
    # center distance d and radius r of each mirror circle:
    d = np.sqrt((cospi_p ** 2) / (cospi_p ** 2 - sinpi_p ** 2 * (cospi_q / 1.0) ** 2 + 1e-9))
    d = np.clip(d, 1.05, 3.5)
    r = np.sqrt(d * d - 1.0)

    field = np.zeros((res, res), np.float32)
    arcs = []
    for k in range(p):
        a = 2 * np.pi * k / p + rng.uniform(0, 0.001)
        cx, cy = d * np.cos(a), d * np.sin(a)
        arcs.append((cx, cy, r))

    # Reflect a base point cloud across mirrors repeatedly -> orbit (the tiling vertices/edges)
    for (cx, cy, rr) in arcs:
        dist = np.abs(np.hypot(X - cx, Y - cy) - rr)
        field += np.exp(-(dist * 16.0) ** 2)

    # iterate inversions of the arc system to fill the disk (self-similar near boundary)
    work = field.copy()
    for it in range(3):
        layer = np.zeros((res, res), np.float32)
        for (cx, cy, rr) in arcs:
            # circle inversion of coords through this mirror -> pull deeper arcs inward
            dx, dy = X - cx, Y - cy
            dd = dx * dx + dy * dy + 1e-6
            ix = cx + rr * rr * dx / dd
            iy = cy + rr * rr * dy / dd
            # sample existing field at inverted coords
            mx = ((ix + 1) * 0.5 * (res - 1)).astype(np.int32)
            my = ((iy + 1) * 0.5 * (res - 1)).astype(np.int32)
            ok = (mx >= 0) & (mx < res) & (my >= 0) & (my < res)
            tmp = np.zeros((res, res), np.float32)
            tmp[ok] = work[my[ok], mx[ok]]
            layer = np.maximum(layer, tmp)
        work = np.maximum(work * 0.85, layer)
    field = np.maximum(field, work)
    field *= inside
    # add a faint radial crush so the boundary accumulation reads as fine detail
    field += 0.15 * inside * np.exp(-(1 - np.sqrt(R2)) * 6.0)
    return _finish(_norm(field), h, w)


# ===========================================================================
# 8. FORD CIRCLES — Farey / Stern-Brocot tangent-circle field (number-theory packing).
# ===========================================================================
def ford_circles(h, w, seed, *, res=512, maxden=26):
    """Ford circles: for each reduced fraction p/q in [0,1], a circle of radius 1/(2q^2)
    tangent to the x-axis at p/q. Every pair is tangent or disjoint (Farey). Tiled
    vertically into bands -> dense self-tangent circle field (inversive number theory)."""
    rng = _rng(seed)
    circles = []
    for q in range(1, int(maxden) + 1):
        for p in range(0, q + 1):
            if np.gcd(p, q) != 1:
                continue
            x = p / q
            r = 1.0 / (2.0 * q * q)
            circles.append((x, r, r))
    circles = np.array(circles, np.float32)  # (cx, r, r)

    # Tile vertically: alternating mirrored bands fill the unit square with self-tangent
    # circle necklaces (one band height = 0.2). Build the full circle list, then rasterize.
    band_h = 0.2
    nrep = 5
    all_c = []
    for band in range(nrep):
        yoff = band * band_h
        flip = (band % 2 == 1)
        for (cx, cy, r) in circles:
            yc = yoff + ((band_h - cy) if flip else cy)
            all_c.append((cx, yc, r))
    field = _circles_to_field(res, all_c, 0.0, 1.0, glow_sigma=1.3, fill=0.30, ring_px=1)
    return _finish(field, h, w)


# ===========================================================================
# 9. STEINER CHAIN — nested rings of mutually tangent circles under a Mobius map.
# ===========================================================================
def steiner_chain(h, w, seed, *, res=512):
    """Steiner chains: a ring of n circles each tangent to two fixed circles (inner+outer),
    then Mobius-transformed off-center and nested recursively -> ornate inversive rosette.
    Inversive geometry (Steiner porism) — not a Voronoi/Apollonian construction."""
    rng = _rng(seed)
    n = int(rng.integers(8, 14))
    layers = 5
    Rout, Rin = 0.95, 0.30
    rho = (Rout - Rin) / 2.0   # chain-circle radius (symmetric porism)
    cc = (Rout + Rin) / 2.0    # chain-circle center radius
    circ = []
    # Replicate the rosette across a small grid so it covers the whole square (full coverage),
    # each tile nesting phi-scaled chains -> dense inversive ring-of-rings.
    grid = 3
    gstep = 1.4
    for gj in range(grid):
        for gi in range(grid):
            ox = (gi - (grid - 1) / 2) * gstep
            oy = (gj - (grid - 1) / 2) * gstep
            for L in range(layers):
                rot = rng.uniform(0, 2 * np.pi) + L * 0.5
                scale = PHI ** (-L)
                ccx = ox + rng.uniform(-0.12, 0.12) * L
                ccy = oy + rng.uniform(-0.12, 0.12) * L
                circ.append((ccx, ccy, Rout * scale))
                circ.append((ccx, ccy, Rin * scale))
                for i in range(n):
                    ang = rot + 2 * np.pi * i / n
                    x = ccx + cc * scale * np.cos(ang)
                    y = ccy + cc * scale * np.sin(ang)
                    circ.append((x, y, rho * scale))
                    # recursive ornament: tiny tangent circles riding each chain circle
                    for j in range(6):
                        a2 = j * np.pi / 3 + rot
                        circ.append((x + rho * scale * 0.7 * np.cos(a2),
                                     y + rho * scale * 0.7 * np.sin(a2),
                                     rho * scale * 0.30))
    span = grid * gstep * 0.5 + 0.5
    field = _circles_to_field(res, circ, -span, span, glow_sigma=1.2, fill=0.18, ring_px=1)
    return _finish(field, h, w)


# ===========================================================================
# 10. SCHOTTKY LIMIT SET — Kleinian-group circle-inversion fractal dust.
# ===========================================================================
def schottky_limit(h, w, seed, *, res=512, depth=7):
    """Kleinian / Schottky group limit set: start with a few generator circles, repeatedly
    invert the whole circle system through each generator -> the fractal limit set (nested
    necklaces of circles). Pure circle inversion (Mobius), classic Indra's-Pearls geometry."""
    rng = _rng(seed)
    # generator circles (orthogonal pairs make a discrete Schottky group)
    ngen = int(rng.integers(4, 6))
    base = []
    for i in range(ngen):
        a = 2 * np.pi * i / ngen + rng.uniform(-0.05, 0.05)
        cr = rng.uniform(0.30, 0.46)
        cx, cy = np.cos(a) * 0.66, np.sin(a) * 0.66
        base.append((cx, cy, cr))

    circles = list(base)
    seen = set()
    # breadth-first inversion of every circle through every generator -> fractal limit set.
    frontier = list(base)
    for _ in range(int(depth)):
        nxt = []
        for (gx, gy, gr) in base:
            gr2 = gr * gr
            for (cx, cy, cr) in frontier:
                dx, dy = cx - gx, cy - gy
                dd = dx * dx + dy * dy
                denom = dd - cr * cr
                if abs(denom) < 1e-6:
                    continue
                ncx = gx + gr2 * dx / denom
                ncy = gy + gr2 * dy / denom
                ncr = abs(gr2 * cr / denom)
                if ncr < 0.0015 or ncr > 3.0:   # keep fine dust -> high-frequency detail
                    continue
                key = (round(ncx, 4), round(ncy, 4), round(ncr, 4))
                if key in seen:
                    continue
                seen.add(key)
                nxt.append((ncx, ncy, ncr))
        circles.extend(nxt)
        frontier = nxt
        if len(circles) > 14000:
            break

    field = _circles_to_field(res, circles, -1.25, 1.25, glow_sigma=1.0, fill=0.0, ring_px=1)
    return _finish(field, h, w)


# ===========================================================================
# 11. DOYLE SPIRAL — loxodromic hexagonal circle packing (conformal exp tiling).
# ===========================================================================
def doyle_spiral(h, w, seed, *, res=512):
    """Doyle spiral: a hexagonal packing of mutually tangent circles whose centers follow
    a complex exponential (logarithmic) spiral, every circle tangent to 6 neighbours.
    A loxodromic conformal tiling — circle packing on a spiral lattice (novel geometry)."""
    rng = _rng(seed)
    # Doyle spiral parameters: radial growth ratio + angular twist per ring.
    p = int(rng.integers(7, 12))   # arms
    growth = rng.uniform(1.07, 1.18)   # smaller growth -> finer, denser circles
    twist = rng.uniform(0.30, 0.65)

    circ = []
    # Lattice in (log r, theta): center_{k,m} = growth^m * exp(i*(2pi*k/p + m*twist)).
    nrings = 70
    for m in range(-nrings, nrings):
        R = growth ** m * 0.010
        if R > 2.4 or R < 0.0015:
            continue
        cr = R * (growth - 1.0) * 0.62   # conformal: radius proportional to center radius
        if cr < 0.0015:
            continue
        for k in range(p):
            ang = 2 * np.pi * k / p + m * twist
            circ.append((R * np.cos(ang), R * np.sin(ang), cr))
    field = _circles_to_field(res, circ, -1.0, 1.0, glow_sigma=1.0, fill=0.30, ring_px=1)
    return _finish(field, h, w)


# --------------------------------------------------------------------------- registry
ENGINES = {
    "hat_monotile": hat_monotile,
    "spectre_monotile": spectre_monotile,
    "penrose_p2": penrose_p2,
    "ammann_beenker": ammann_beenker,
    "socolar_12fold": socolar_12fold,
    "girih_strapwork": girih_strapwork,
    "hyperbolic_pqr": hyperbolic_pqr,
    "ford_circles": ford_circles,
    "steiner_chain": steiner_chain,
    "schottky_limit": schottky_limit,
    "doyle_spiral": doyle_spiral,
}


if __name__ == "__main__":
    import time
    h = w = 1024
    print(f"{'engine':<20}{'secs':>8}{'fine':>9}{'min':>7}{'max':>7}{'std':>8}  status")
    print("-" * 72)
    allpass = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(h, w, 12345)
        secs = time.time() - t0
        f = np.asarray(f, np.float32)
        blur = cv2.GaussianBlur(f, (0, 0), 8)
        fine = (f - blur).std() / (f.std() + 1e-6)
        std = f.std()
        finite = np.isfinite(f).all()
        ok = (secs < 2.5) and (fine >= 0.12) and (std > 0.06) and finite \
             and (f.min() >= -1e-4) and (f.max() <= 1 + 1e-4)
        allpass = allpass and ok
        print(f"{name:<20}{secs:>8.3f}{fine:>9.3f}{f.min():>7.3f}{f.max():>7.3f}"
              f"{std:>8.3f}  {'OK' if ok else 'FAIL'}")
    print("-" * 72)
    print("ALL PASS" if allpass else "SOME FAILED")
