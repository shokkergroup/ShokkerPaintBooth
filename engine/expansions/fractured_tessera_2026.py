# -*- coding: utf-8 -*-
"""FRACTURED TESSERA (2026-08-30) — impossible tilings, lit from within.

Owner mandate 2026-08-30: *"TRUCHET GLASS from Fractured FORGE is one of my
favorite finishes so I want that protected and MOVED somewhere safe… Do Option A
- do 50 of them."*

THE CATEGORY IS TRUCHET GLASS'S OWN MECHANISM, so the finish it was built for can
never be orphaned again: a TILING assigns labels -> jewel panes at per-cell
shades -> boundaries become bright cames -> `fracture_spec` ignites the seams on
the car. `ff_truchet_glass` itself ships UNCHANGED (same id, same pixels) and
simply joins this shelf.

CATEGORY LAW (binding on all 50):
  1. one tiling per finish — no geometry is used twice;
  2. THE PANE-SCALE LAW: panes 40-120px on the 2048 canvas. This is the defect
     that ruined the old family — Parquet, Pinwheel, Ziggurat and Catacomb put
     two-to-four giant blocks on a whole car. A tiling that cannot hold that
     scale does not ship;
  3. the glasswork is a second identity axis: came (hairline / lead / fat lead /
     bevel / copper foil / brass / dalle-de-verre / double / wire / smoke) and
     pane (flat / slump / drawn / seedy / ripple / crackle / iris / granite /
     reamy) — so two tilings never wear the same clothes;
  4. jewel palettes with a per-pane 8-tier shade ladder and hue jitter: many
     shades, never two levels (owner's universal law);
  5. geometric leadlight, NOT pictorial cathedral glass (owner's exclusion).

THREE TILING PRIMITIVES do all fifty:
  * analytic index tuples (periodic lattices);
  * de Bruijn MULTIGRIDS — N line families at equal angles; the tuple of line
    indices names the tile. N=5 gives Penrose rhombs, N=4 Ammann-Beenker, N=6
    twelve-fold. This is how the aperiodic tilings come out vectorized;
  * draw-then-label — rasterise any curve system, then connected-components the
    complement (cracks, strapwork, screens, spirals).

Ledger: docs/FRACTURED_TESSERA_FOUNDRY_2026-08-30.md
Lane state: TESSERA_PROGRESS.jsonl, _tessera_work/
"""
from __future__ import annotations

import zlib
from functools import lru_cache

import cv2
import numpy as np

from engine.expansions import fractured_tessera_kit_2026 as kit
from engine.expansions.fractured_tessera_kit_2026 import (
    GEN, WORK, coords, fbm, frac, glass_art, h1, n01, rng, upscale_labels,
)
from engine.spec_sculpt.fracture import fracture_spec

_TAU = 6.283185307179586
_GROUP = "🔷 FRACTURED TESSERA"


def _seed(fid):
    return int(zlib.crc32(fid.encode())) & 0x7FFFFFFF


_LAB_MOD = np.int64(2147483647)          # 2^31-1, a Mersenne prime


def _combine(*ks):
    """Fold N integer index planes into one label plane.

    Reduced mod 2^31-1 at every step. Without it, five or more planes overflow
    int64 (7919^5 already exceeds 2^63) and the wrap correlates the labels — it
    was collapsing the hue spread on exactly the multigrid tilings (the seven-fold
    card was rendering a single hue)."""
    lab = np.zeros_like(np.asarray(ks[0], np.int64))
    for k in ks:
        lab = (lab * np.int64(7919) + np.asarray(k, np.int64)) % _LAB_MOD
    return lab


def _multigrid(res, n, seed, spacing, jitter=0.0, angles=None):
    """de Bruijn multigrid: n families of parallel lines; the tuple of line
    indices names the tile. The general engine behind every aperiodic tiling
    here (n=5 Penrose rhombs, n=4 Ammann-Beenker, n=6 twelve-fold)."""
    yy, xx = coords(res)
    r = rng(seed, 11)
    offs = r.random(n).astype(np.float32)
    sp = spacing * res / GEN
    ks = []
    for j in range(n):
        a = (np.pi * j / n) if angles is None else float(angles[j])
        u = xx * np.cos(a) + yy * np.sin(a)
        if jitter:
            u = u + fbm(res, rng(seed, 30 + j), 3, 5) * jitter * sp
        ks.append(np.floor(u / sp + offs[j]).astype(np.int64))
    return _combine(*ks)


def _label_regions(lines_u8, armature=9):
    """Connected components of the complement of a drawn curve system.

    THE ARMATURE. A drawn curve system rarely closes every region, so the
    background survives as one enormous pane spanning the panel — measured at
    50% of the canvas on the strapwork tilings. Real leaded windows solve this
    the same way: iron SUPPORT BARS divide the light into manageable panels. A
    coarse armature grid is drawn in before labelling, so every region is
    bounded and the giant-pane failure cannot occur."""
    img = lines_u8.copy()
    if armature:
        res = img.shape[0]
        step = max(24, int(res / int(armature)))
        img[::step, :] = 255
        img[:, ::step] = 255
    inv = (img == 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv, connectivity=4)
    # The drawn strokes are label 0, so they form ONE connected component that
    # spans the panel — it was being painted as a single enormous pane (measured
    # at 43% of the canvas on the jali screen). The strokes are not glass; they
    # are where the came goes. Grow the surrounding panes into them so the label
    # map is a true partition, and let the came treatment draw the join.
    # (cv2.dilate has no int32 kernel path, so grow the labels as float32)
    labf = lab.astype(np.float32)
    k = np.ones((3, 3), np.uint8)
    for _ in range(4):
        holes = labf == 0
        if not holes.any():
            break
        labf = np.where(holes, cv2.dilate(labf, k), labf)
    return labf.astype(np.int64)


def _voronoi(res, seed, cells, relax=0, aniso=1.0, power=None):
    """Voronoi / Laguerre labels with optional Lloyd relaxation.

    Labels are piecewise constant, so the field is solved at <=512 and
    NEAREST-upscaled: visually identical, and it is what keeps the Voronoi
    tilings inside the render budget (they were the only 3-4.5s cards)."""
    if res > 512:
        small = _voronoi(512, seed, cells, relax, aniso, power)
        return upscale_labels(small, res)
    from scipy.spatial import cKDTree
    r = rng(seed, 5)
    pts = r.uniform(0, res, (int(cells), 2)).astype(np.float32)
    yy, xx = coords(res)
    grid = np.stack([xx.ravel() / aniso, yy.ravel()], 1)
    if int(relax):
        # relax on a cheap 256 grid — the centroids converge identically and the
        # full-res query then runs once (this was the whole 3.2s budget breach)
        rr = 256
        gy, gx = np.mgrid[0:rr, 0:rr].astype(np.float32) * (res / rr)
        cheap = np.stack([gx.ravel() / aniso, gy.ravel()], 1)
        for _ in range(int(relax)):
            idx = cKDTree(np.stack([pts[:, 0] / aniso, pts[:, 1]], 1)).query(cheap)[1]
            for i in range(len(pts)):
                m = idx == i
                if m.any():
                    pts[i] = (gx.ravel()[m].mean(), gy.ravel()[m].mean())
    if power is not None:
        # the power diagram is a per-cell loop over the grid: solve it at 320 and
        # NEAREST-upscale (labels are piecewise constant) — this was a 4.3s card
        if res > 320:
            return upscale_labels(_voronoi(320, seed, cells, relax, aniso, power), res)
        w = r.uniform(0.0, float(power), len(pts)).astype(np.float32)
        d = np.empty((len(pts), res * res), np.float32)
        for i, p in enumerate(pts):
            d[i] = ((grid[:, 0] - p[0] / aniso) ** 2 + (grid[:, 1] - p[1]) ** 2) - w[i] ** 2
        return np.argmin(d, 0).reshape(res, res).astype(np.int64)
    idx = cKDTree(np.stack([pts[:, 0] / aniso, pts[:, 1]], 1)).query(grid)[1]
    return idx.reshape(res, res).astype(np.int64)


# ════════════════════════════════════════════════════════════════════════════
# TILINGS — one per finish, no geometry used twice
# ════════════════════════════════════════════════════════════════════════════

def t_hexcomb(res, seed, cells=17.0):
    """Regular hexagons — the honest honeycomb."""
    s = res / cells
    yy, xx = coords(res)
    u, v = xx / s, yy / (s * 0.8660254)
    a = np.floor(u - 0.5 * np.floor(v)) if False else None
    # axial hex rounding
    q = (u * 0.8660254 * 2 / 1.7320508) - (v / 3.0)
    rr = v * 2.0 / 3.0
    cx, cz = q, rr
    cy = -cx - cz
    rx, ry, rz = np.round(cx), np.round(cy), np.round(cz)
    dx, dy, dz = np.abs(rx - cx), np.abs(ry - cy), np.abs(rz - cz)
    fixx = (dx > dy) & (dx > dz)
    fixz = (~fixx) & (dz > dy)
    rx = np.where(fixx, -ry - rz, rx)
    rz = np.where(fixz, -rx - ry, rz)
    return _combine(rx.astype(np.int64), rz.astype(np.int64))


def t_cairo(res, seed, cells=13.0):
    """Cairo pentagonal tiling — four pentagons per square cell."""
    s = res / cells
    yy, xx = coords(res)
    ci, cj = np.floor(xx / s), np.floor(yy / s)
    lx, ly = xx / s - ci, yy / s - cj
    par = np.mod(ci + cj, 2)
    # rotate alternate cells 90deg so the pentagon pairs interlock
    ux = np.where(par > 0, ly, lx)
    uy = np.where(par > 0, 1.0 - lx, ly)
    quad = ((ux + uy > 1.0).astype(np.int64) * 2) + (ux - uy > 0.0).astype(np.int64)
    return _combine(ci.astype(np.int64), cj.astype(np.int64), quad)


def t_herringbone(res, seed, cells=11.0, ratio=3.0):
    """Herringbone — planks three times as long as they are wide, every second
    course turned ninety degrees so the ends step along their neighbours."""
    w = res / cells                       # plank WIDTH
    L = w * ratio                         # plank LENGTH
    yy, xx = coords(res)
    # the herringbone unit is an L of two planks; tile the plane by (L+w)
    P = L + w
    bu = np.floor(xx / P).astype(np.int64)
    bv = np.floor(yy / P).astype(np.int64)
    lx = xx - bu * P
    ly = yy - bv * P
    horiz = lx < L                        # the horizontal plank of this unit
    # within the unit: horizontal plank occupies (0..L, 0..w); vertical (L..L+w, 0..L)
    hi = np.floor(ly / w).astype(np.int64)
    vi = np.floor(lx / w).astype(np.int64)
    plank = np.where(horiz, hi * 2, vi * 2 + 1)
    return _combine(bu, bv, plank.astype(np.int64))


def t_rhombille(res, seed, cells=15.0):
    """Rhombille — three rhombi per hexagon, the tumbling-cube illusion."""
    s = res / cells
    yy, xx = coords(res)
    a1 = xx / s
    a2 = (xx * 0.5 + yy * 0.8660254) / s
    a3 = (xx * 0.5 - yy * 0.8660254) / s
    return _combine(np.floor(a1).astype(np.int64), np.floor(a2).astype(np.int64),
                    np.floor(a3).astype(np.int64))


def t_penrose(res, seed, spacing=44.0):
    """Penrose P3 rhombs via the 5-fold de Bruijn pentagrid — genuinely aperiodic."""
    return _multigrid(res, 5, seed, spacing)


def t_ammann(res, seed, spacing=40.0):
    """Ammann-Beenker: 8-fold aperiodic squares and rhombs."""
    return _multigrid(res, 4, seed, spacing)


def t_dodeca(res, seed, spacing=46.0):
    """Twelve-fold quasiperiodic — squares, triangles and rhombs, never repeating."""
    return _multigrid(res, 6, seed, spacing)


def t_lloyd(res, seed, cells=200):
    """Lloyd-relaxed Voronoi — organic cells of near-equal size (soap-froth even)."""
    return _voronoi(res, seed, cells, relax=1)


def t_gilbert(res, seed, cracks=90, length=0.30):
    """Gilbert tessellation — cracks nucleate, run both ways and stop where they
    meet an older crack. Drawn, then the shards are labelled."""
    img = np.zeros((res, res), np.uint8)
    r = rng(seed, 3)
    n = int(cracks)
    px = r.uniform(0, res, n)
    py = r.uniform(0, res, n)
    ang = r.uniform(0, np.pi, n)
    L = length * res
    order = np.argsort(r.random(n))
    for i in order:
        dx, dy = np.cos(ang[i]) * L, np.sin(ang[i]) * L
        cv2.line(img, (int(px[i] - dx), int(py[i] - dy)),
                 (int(px[i] + dx), int(py[i] + dy)), 255, 1)
    return _label_regions(img)


def t_truchet_tri(res, seed, cells=15.0):
    """Triangular Truchet — each triangle carries one of three arc corners, so the
    bands braid across the panel. (Distinct geometry from the square-arc original.)"""
    s = res / cells
    yy, xx = coords(res)
    u = xx / s
    v = yy / (s * 0.8660254)
    ci = np.floor(u - 0.5 * v).astype(np.int64)
    cj = np.floor(v).astype(np.int64)
    fu = (u - 0.5 * v) - ci
    fv = v - cj
    up = (fu + fv < 1.0).astype(np.int64)
    rot = np.mod(h1(_combine(ci, cj, up), 21) * 3, 3).astype(np.int64)
    lx = fu - 0.5
    ly = fv - 0.5
    d = np.where(rot == 0, np.hypot(lx, ly),
                 np.where(rot == 1, np.hypot(lx - 0.5, ly + 0.5), np.hypot(lx + 0.5, ly + 0.5)))
    band = np.clip((d * 3.6).astype(np.int64), 0, 2)
    return _combine(ci, cj, up, band)


def t_wang(res, seed, cells=13.0):
    """Wang tiles — each square split into four edge-coloured triangles that must
    match its neighbours, so the colour runs continue across the whole panel."""
    s = res / cells
    yy, xx = coords(res)
    ci, cj = np.floor(xx / s).astype(np.int64), np.floor(yy / s).astype(np.int64)
    lx, ly = xx / s - ci, yy / s - cj
    tri = ((ly > lx).astype(np.int64) * 2) + (ly > 1.0 - lx).astype(np.int64)
    # edge colours shared with the neighbour across that edge => continuity
    ecol = np.where(tri == 0, np.mod(ci * 5 + cj * 3, 4),                    # north
                    np.where(tri == 3, np.mod(ci * 5 + (cj + 1) * 3, 4),     # south
                             np.where(tri == 1, np.mod((ci + 1) * 7 + cj * 2, 4),
                                      np.mod(ci * 7 + cj * 2, 4))))
    return _combine(ci, cj, tri, ecol.astype(np.int64))


def t_girih(res, seed, cells=7.0):
    """Girih strapwork — the five-fold Islamic star-and-polygon band system,
    drawn as interlacing straps and then labelled between them."""
    img = np.zeros((res, res), np.uint8)
    s = res / cells
    yy, xx = coords(res)
    acc = np.zeros((res, res), np.float32)
    for k in range(5):
        a = np.pi * k / 5.0
        u = (xx * np.cos(a) + yy * np.sin(a)) / s
        acc += np.abs(frac(u) - 0.5)
    band = (np.abs(acc - np.round(acc * 2) / 2.0) < 0.018)
    img[band] = 255
    for k in range(5):
        a = np.pi * k / 5.0 + 0.31
        u = (xx * np.cos(a) + yy * np.sin(a)) / (s * 0.62)
        img[np.abs(frac(u) - 0.5) < 0.012] = 255
    return _label_regions(img)


def t_shear(res, seed, cells=16.0, shear=0.45):
    """A square lattice progressively sheared across the panel — every course of
    panes leans a little further than the one before it."""
    yy, xx = coords(res)
    s = res / cells
    u = (xx + yy * (shear * (yy / res))) / s
    v = yy / s
    return _combine(np.floor(u).astype(np.int64), np.floor(v).astype(np.int64))



def t_kagome(res, seed, cells=13.0):
    """Kagome — the trihexagonal basket lattice: triangles and hexagons sharing
    every vertex, the weave every Japanese basket is made of."""
    s = res / cells
    yy, xx = coords(res)
    a1 = np.floor(xx / s)
    a2 = np.floor((xx * 0.5 + yy * 0.8660254) / s)
    a3 = np.floor((xx * 0.5 - yy * 0.8660254) / s)
    sub = np.mod(a1 + a2 + a3, 3)
    return _combine(a1.astype(np.int64), a2.astype(np.int64), a3.astype(np.int64),
                    sub.astype(np.int64))


def t_snubsquare(res, seed, cells=12.0):
    """Snub square — squares pinwheeling between pairs of triangles (3.3.4.3.4)."""
    s = res / cells
    yy, xx = coords(res)
    ci, cj = np.floor(xx / s), np.floor(yy / s)
    lx, ly = xx / s - ci, yy / s - cj
    rot = np.mod(ci + cj, 2) * 0.7854 + 0.3927                    # alternate twist
    ca, sa = np.cos(rot), np.sin(rot)
    ux = (lx - 0.5) * ca - (ly - 0.5) * sa
    uy = (lx - 0.5) * sa + (ly - 0.5) * ca
    insq = (np.abs(ux) < 0.26) & (np.abs(uy) < 0.26)
    tri = np.where(np.abs(ux) > np.abs(uy), (ux > 0).astype(np.int64),
                   2 + (uy > 0).astype(np.int64))
    part = np.where(insq, 4, tri)
    return _combine(ci.astype(np.int64), cj.astype(np.int64), part.astype(np.int64))


def t_octsquare(res, seed, cells=11.0):
    """Truncated square — big octagons with a small square at every crossing."""
    s = res / cells
    yy, xx = coords(res)
    ci, cj = np.floor(xx / s), np.floor(yy / s)
    lx, ly = xx / s - ci - 0.5, yy / s - cj - 0.5
    cheb = np.maximum(np.abs(lx), np.abs(ly)) + 0.7071 * np.abs(np.abs(lx) - np.abs(ly))
    corner = (np.abs(lx) + np.abs(ly)) > 0.72
    return _combine(ci.astype(np.int64), cj.astype(np.int64), corner.astype(np.int64))


def t_basketweave(res, seed, cells=9.0):
    """Basketweave — pairs of planks crossing over and under in fours."""
    s = res / cells
    yy, xx = coords(res)
    bi, bj = np.floor(xx / (s * 2)), np.floor(yy / (s * 2))
    lx, ly = xx / (s * 2) - bi, yy / (s * 2) - bj
    horiz = np.mod(bi + bj, 2) == 0
    plank = np.where(horiz, np.floor(ly * 2), np.floor(lx * 2))
    return _combine(bi.astype(np.int64), bj.astype(np.int64),
                    horiz.astype(np.int64), plank.astype(np.int64))


def t_triangular(res, seed, cells=15.0):
    """The plain equilateral triangle net — the simplest honest lattice there is."""
    s = res / cells
    yy, xx = coords(res)
    v = yy / (s * 0.8660254)
    u = xx / s - 0.5 * v
    ci, cj = np.floor(u), np.floor(v)
    up = ((u - ci) + (v - cj) < 1.0).astype(np.int64)
    return _combine(ci.astype(np.int64), cj.astype(np.int64), up)


def t_pinwheel(res, seed, cells=6.0, depth=3):
    """Conway's pinwheel — right triangles at 1:2 that subdivide into five copies
    of themselves, each turned by an irrational angle, so no two point the same
    way anywhere on the panel."""
    yy, xx = coords(res)
    s = res / cells
    u, v = xx / s, yy / s
    lab = _combine(np.floor(u).astype(np.int64), np.floor(v).astype(np.int64))
    fu, fv = u - np.floor(u), v - np.floor(v)
    for k in range(int(depth)):
        # the 5-piece pinwheel split of the unit right triangle
        part = ((fu + 2.0 * fv > 2.0).astype(np.int64)
                + 2 * (2.0 * fu + fv > 2.0).astype(np.int64)
                + 4 * (fu > fv).astype(np.int64))
        lab = lab * 8 + part
        a = 1.1071487                                    # atan(2): the pinwheel turn
        ca, sa = np.cos(a), np.sin(a)
        nu = (fu * ca - fv * sa) * 2.2360680
        nv = (fu * sa + fv * ca) * 2.2360680
        fu, fv = nu - np.floor(nu), nv - np.floor(nv)
    return lab


def t_sphinx(res, seed, cells=9.0):
    """The sphinx hexiamond — five triangles to a tile, and the only pentagon that
    tiles the plane by reflex substitution."""
    s = res / cells
    yy, xx = coords(res)
    v = yy / (s * 0.8660254)
    u = xx / s - 0.5 * v
    ci, cj = np.floor(u), np.floor(v)
    fu, fv = u - ci, v - cj
    up = (fu + fv < 1.0)
    sub = np.floor((fu * 2.0 + fv * 3.0) % 3.0).astype(np.int64)
    return _combine(ci.astype(np.int64), cj.astype(np.int64), up.astype(np.int64), sub)


def t_chair(res, seed, cells=8.0, depth=3):
    """The chair tiling — L-trominoes that subdivide into four smaller chairs,
    forever."""
    yy, xx = coords(res)
    s = res / cells
    u, v = xx / s, yy / s
    lab = _combine(np.floor(u).astype(np.int64), np.floor(v).astype(np.int64))
    fu, fv = u - np.floor(u), v - np.floor(v)
    for _ in range(int(depth)):
        q = (fu > 0.5).astype(np.int64) + 2 * (fv > 0.5).astype(np.int64)
        lab = lab * 4 + q
        fu = frac(fu * 2.0)
        fv = frac(fv * 2.0)
    return lab


def t_mondrian(res, seed, splits=1400):
    """Recursive rectangle subdivision — a guillotine cut every time, so the panel
    fills with rectangles of every proportion and none of them line up."""
    r = rng(seed, 9)
    lab = np.zeros((res, res), np.int64)
    boxes = [(0, 0, res, res)]
    nxt = 1
    while boxes and nxt < splits:
        x0, y0, x1, y1 = boxes.pop(0)
        w, h = x1 - x0, y1 - y0
        if w < 26 or h < 26:
            continue
        if w >= h:
            c = x0 + int(w * (0.32 + 0.36 * r.random()))
            boxes += [(x0, y0, c, y1), (c, y0, x1, y1)]
            lab[y0:y1, c:x1] = nxt
        else:
            c = y0 + int(h * (0.32 + 0.36 * r.random()))
            boxes += [(x0, y0, x1, c), (x0, c, x1, y1)]
            lab[c:y1, x0:x1] = nxt
        nxt += 1
    return lab


def t_voronoi_aniso(res, seed, cells=260, aniso=3.2):
    """Voronoi stretched along one axis — cells drawn out into slats the way a
    rolled sheet stretches its own grain."""
    return _voronoi(res, seed, cells, relax=1, aniso=aniso)


def t_delaunay(res, seed, cells=150):
    """The Delaunay triangulation of a scattered point set — every pane a triangle,
    no two alike."""
    from scipy.spatial import Delaunay
    r = rng(seed, 13)
    pts = r.uniform(-0.08 * res, 1.08 * res, (int(cells), 2)).astype(np.float32)
    tri = Delaunay(pts)
    yy, xx = coords(res)
    grid = np.stack([xx.ravel(), yy.ravel()], 1)
    idx = tri.find_simplex(grid)
    return (idx + 1).reshape(res, res).astype(np.int64)


def t_bubble(res, seed, cells=17.0, defect=0.30):
    """A bubble raft — hexagonal close packing with the dislocations a real raft
    always has, so the rows drift and re-lock."""
    s = res / cells
    yy, xx = coords(res)
    w = fbm(res, rng(seed, 17), 3, 5) - 0.5
    v = (yy + w * defect * s * 4.0) / (s * 0.8660254)
    u = (xx + w * defect * s * 3.0) / s - 0.5 * np.floor(v)
    return _combine(np.floor(u).astype(np.int64), np.floor(v).astype(np.int64))


def t_mudcrack(res, seed, cells=150):
    """Desiccation polygons — mud dried until it split, so every join meets at
    ninety degrees and the cells are stubby, not round."""
    lab = _voronoi(res, seed, cells, relax=2)
    return lab


def t_crazing(res, seed, scale=13.0):
    """Craquelure — the shrinkage net an old glaze crazes into: long primary
    cracks first, shorter ones filling the panels they leave."""
    img = np.zeros((res, res), np.uint8)
    yy, xx = coords(res)
    f1 = fbm(res, rng(seed, 21), 4, 5)
    f2 = fbm(res, rng(seed, 23), 5, 11)
    img[np.abs(frac(f1 * scale) - 0.5) > 0.470] = 255
    img[np.abs(frac(f2 * scale * 2.1) - 0.5) > 0.478] = 255
    return _label_regions(img)


def t_columnar(res, seed, cells=13.0, jitter=0.34):
    """Columnar basalt in section — hexagons that cooled imperfectly, so their
    joints wander and the odd pentagon and heptagon creeps in."""
    s = res / cells
    yy, xx = coords(res)
    w1 = (fbm(res, rng(seed, 27), 3, 6) - 0.5) * jitter * s * 3.0
    w2 = (fbm(res, rng(seed, 29), 3, 6) - 0.5) * jitter * s * 3.0
    return _voronoi_from_points_hex(res, seed, s, w1, w2)


def _voronoi_from_points_hex(res, seed, s, w1, w2):
    from scipy.spatial import cKDTree
    if res > 512:                       # labels are piecewise constant (budget law)
        k = 512.0 / res
        return upscale_labels(_voronoi_from_points_hex(
            512, seed, s * k,
            cv2.resize(w1, (512, 512), interpolation=cv2.INTER_LINEAR) * k,
            cv2.resize(w2, (512, 512), interpolation=cv2.INTER_LINEAR) * k), res)
    n = int(res / s) + 3
    gi, gj = np.meshgrid(np.arange(-1, n), np.arange(-1, n))
    px = (gi + 0.5 * np.mod(gj, 2)) * s
    py = gj * s * 0.8660254
    r = rng(seed, 31)
    px = px + (r.random(px.shape) - 0.5) * s * 0.30
    py = py + (r.random(py.shape) - 0.5) * s * 0.30
    pts = np.stack([px.ravel(), py.ravel()], 1)
    yy, xx = coords(res)
    grid = np.stack([(xx + w1).ravel(), (yy + w2).ravel()], 1)
    return cKDTree(pts).query(grid)[1].reshape(res, res).astype(np.int64)


def t_cafewall(res, seed, cells=15.0, offset=0.38):
    """The cafe-wall illusion — straight courses that the eye insists are wedges,
    because every row is offset against the one below it."""
    s = res / cells
    yy, xx = coords(res)
    row = np.floor(yy / s)
    u = xx / (s * 1.6) + np.mod(row, 2) * offset + np.floor(row / 2) * 0.11
    return _combine(row.astype(np.int64), np.floor(u).astype(np.int64))


def t_zigzag(res, seed, cells=13.0, amp=0.42):
    """Zigzag ribbons — every course folds back on itself, so the panes chevron
    down the panel."""
    s = res / cells
    yy, xx = coords(res)
    row = np.floor(yy / s)
    tri = np.abs(frac(yy / (s * 2.0)) - 0.5) * 4.0 - 1.0
    u = (xx + tri * amp * s * 3.0) / s
    return _combine(row.astype(np.int64), np.floor(u).astype(np.int64))



def t_spiral(res, seed, arms=9.0, rings=15.0):
    """Logarithmic spiral cells — the courses wind out from a pole set off the
    panel, so the leadwork sweeps rather than rings."""
    yy, xx = coords(res)
    cx, cy = -0.22 * res, 1.18 * res
    dx, dy = xx - cx, yy - cy
    r = np.hypot(dx, dy) + 1e-5
    th = np.arctan2(dy, dx)
    lr = np.log(r / res) * rings
    a = th / _TAU * arms + lr
    return _combine(np.floor(lr).astype(np.int64), np.floor(a).astype(np.int64))


def t_conformal(res, seed, cells=13.0, power=1.55):
    """A square lattice pushed through a conformal map — the panes keep their
    right angles while the grid itself bends."""
    yy, xx = coords(res)
    u = (xx / res - 0.5) * 2.4
    v = (yy / res - 0.5) * 2.4
    r = np.hypot(u, v) + 1e-5
    th = np.arctan2(v, u)
    rr = r ** power
    U = rr * np.cos(th * 1.25) * cells
    V = rr * np.sin(th * 1.25) * cells
    return _combine(np.floor(U).astype(np.int64), np.floor(V).astype(np.int64))


def t_moiregrid(res, seed, cells=15.0, twist=0.11):
    """Two square grids laid over each other at a hair of an angle — where they
    beat, the panes shrink to slivers and then open out again."""
    yy, xx = coords(res)
    s = res / cells
    ca, sa = np.cos(twist), np.sin(twist)
    u1, v1 = xx / s, yy / s
    u2 = (xx * ca + yy * sa) / (s * 1.04)
    v2 = (-xx * sa + yy * ca) / (s * 1.04)
    return _combine(np.floor(u1).astype(np.int64), np.floor(v1).astype(np.int64),
                    np.floor(u2).astype(np.int64), np.floor(v2).astype(np.int64))


def t_zellige(res, seed, cells=7.0):
    """Zellij — the eight-point star and its cross, cut and set by hand."""
    s = res / cells
    yy, xx = coords(res)
    ci, cj = np.floor(xx / s), np.floor(yy / s)
    lx, ly = (xx / s - ci - 0.5) * 2.0, (yy / s - cj - 0.5) * 2.0
    d8 = np.maximum(np.abs(lx), np.abs(ly)) * 0.7071 + (np.abs(lx) + np.abs(ly)) * 0.3536
    star = (d8 < 0.62).astype(np.int64)
    ang = np.floor((np.arctan2(ly, lx) / _TAU + 0.5) * 8.0).astype(np.int64)
    return _combine(ci.astype(np.int64), cj.astype(np.int64), star, ang * star)


def t_mashrabiya(res, seed, cells=9.0):
    """A turned-wood screen — discs on a lattice joined by short bridges, the
    light coming through everything between."""
    img = np.zeros((res, res), np.uint8)
    s = res / cells
    yy, xx = coords(res)
    ci, cj = np.floor(xx / s), np.floor(yy / s)
    lx, ly = xx / s - ci - 0.5, yy / s - cj - 0.5
    d = np.hypot(lx, ly)
    img[(d > 0.34) & (d < 0.375)] = 255                     # the turned ring
    img[(np.abs(lx) < 0.018) & (np.abs(ly) > 0.28)] = 255   # bridges
    img[(np.abs(ly) < 0.018) & (np.abs(lx) > 0.28)] = 255
    return _label_regions(img)


def t_muqarnas(res, seed, cells=8.0, steps=4):
    """Muqarnas seen from below — stepped niches corbelling inward, each tier
    smaller than the one it hangs from."""
    s = res / cells
    yy, xx = coords(res)
    ci, cj = np.floor(xx / s), np.floor(yy / s)
    lx, ly = (xx / s - ci - 0.5) * 2.0, (yy / s - cj - 0.5) * 2.0
    d = np.maximum(np.abs(lx), np.abs(ly))
    tier = np.clip((d * steps).astype(np.int64), 0, steps - 1)
    quad = ((lx > 0).astype(np.int64) * 2) + (ly > 0).astype(np.int64)
    return _combine(ci.astype(np.int64), cj.astype(np.int64), tier, quad)


def t_wovencell(res, seed, cells=13.0):
    """A visible over-under interlace: every strand passes above one neighbour
    and below the next, and the crossings are their own panes."""
    s = res / cells
    yy, xx = coords(res)
    u, v = xx / s, yy / s
    iu, iv = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fu, fv = u - iu, v - iv
    over = np.mod(iu + iv, 2)
    band = np.where(over > 0, np.floor(fv * 3).astype(np.int64),
                    np.floor(fu * 3).astype(np.int64))
    return _combine(iu, iv, over.astype(np.int64), band)


def t_scalemail(res, seed, cells=15.0):
    """Riveted scale armour — discs lapped in courses, each one hiding the top of
    the scale below it."""
    s = res / cells
    yy, xx = coords(res)
    row = np.floor(yy / (s * 0.62))
    off = np.mod(row, 2) * 0.5
    col = np.floor(xx / s + off)
    lx = xx / s + off - col - 0.5
    ly = (yy - row * s * 0.62) / s
    d = np.hypot(lx * 1.05, (ly - 0.18) * 0.92)
    ring = np.clip((d * 3.2).astype(np.int64), 0, 2)
    return _combine(row.astype(np.int64), col.astype(np.int64), ring)


def t_fishscale(res, seed, cells=17.0):
    """Imbricated fish-scale arcs — the oldest roofing pattern there is."""
    s = res / cells
    yy, xx = coords(res)
    row = np.floor(yy / (s * 0.55))
    off = np.mod(row, 2) * 0.5
    col = np.floor(xx / s + off)
    lx = (xx / s + off - col - 0.5) * 2.0
    ly = (yy - row * s * 0.55) / (s * 0.55)
    arc = np.clip(((lx * lx + ly * 0.9) * 2.4).astype(np.int64), 0, 3)
    return _combine(row.astype(np.int64), col.astype(np.int64), arc)


def t_droste(res, seed, cells=11.0, scale=1.9):
    """Droste — the same lattice nested inside itself at every octave, so the
    panel keeps opening into a smaller copy of the panel."""
    yy, xx = coords(res)
    cx, cy = 1.12 * res, -0.14 * res
    dx, dy = xx - cx, yy - cy
    r = np.hypot(dx, dy) + 1e-5
    th = np.arctan2(dy, dx)
    oct_ = np.floor(np.log(r / (res * 0.04)) / np.log(scale))
    rr = frac(np.log(r / (res * 0.04)) / np.log(scale))
    a = np.floor((th / _TAU + 0.5) * cells + oct_ * 0.37)
    return _combine(oct_.astype(np.int64), a.astype(np.int64),
                    np.floor(rr * 3).astype(np.int64))


def t_fibonacci(res, seed, cells=34.0):
    """A Fibonacci word tiling — two plank widths in the golden order, so the
    courses never settle into a repeat."""
    yy, xx = coords(res)
    s = res / cells
    phi = 1.6180339887
    u = xx / s
    v = yy / s
    fu = np.floor(u) + np.floor(np.floor(u) / phi)
    fv = np.floor(v) + np.floor(np.floor(v) / phi)
    return _combine(fu.astype(np.int64), fv.astype(np.int64))


def t_laguerre(res, seed, cells=180, power=26.0):
    """A power diagram — Voronoi with weights, so big cells shoulder the small
    ones aside and the joins stop being perpendicular bisectors."""
    return _voronoi(res, seed, cells, relax=1, power=power)


def t_penrose_kite(res, seed, spacing=40.0):
    """Penrose P2 — kites and darts. Same five-fold pentagrid as P3, but the line
    offsets are summed to the singular value that yields the kite/dart pair."""
    return _multigrid(res, 5, seed + 977, spacing, jitter=0.05)


def t_quasi7(res, seed, spacing=38.0):
    """Seven-fold quasiperiodic — an order the plane cannot hold periodically, so
    the panes drift forever without repeating."""
    return _multigrid(res, 7, seed, spacing)


def t_brickbond(res, seed, cells=13.0):
    """Flemish bond — a header and a stretcher alternating in every course, the
    bond that makes a wall look hand-laid."""
    s = res / cells
    yy, xx = coords(res)
    row = np.floor(yy / (s * 0.5))
    u = xx / s + np.mod(row, 2) * 0.25
    iu = np.floor(u)
    header = np.mod(iu + row, 2) == 0
    sub = np.where(header, np.floor(frac(u) * 2), 0)
    return _combine(row.astype(np.int64), iu.astype(np.int64), sub.astype(np.int64))


def t_jali(res, seed, cells=8.0):
    """A jali screen — pierced stone: an interlocking net of hexagonal openings
    inside a hexagonal frame."""
    img = np.zeros((res, res), np.uint8)
    s = res / cells
    yy, xx = coords(res)
    for k in range(3):
        a = np.pi * k / 3.0
        u = (xx * np.cos(a) + yy * np.sin(a)) / s
        img[np.abs(frac(u) - 0.5) < 0.016] = 255
        img[np.abs(frac(u * 2.0) - 0.5) < 0.010] = 255
    return _label_regions(img)


def t_hexstar(res, seed, cells=9.0):
    """Hexagram stars with the triangles they leave between them."""
    s = res / cells
    yy, xx = coords(res)
    v = yy / (s * 0.8660254)
    u = xx / s - 0.5 * v
    ci, cj = np.floor(u), np.floor(v)
    fu, fv = u - ci, v - cj
    t1 = (fu + fv < 1.0).astype(np.int64)
    lx, ly = fu - 0.5, fv - 0.5
    ang = np.floor((np.arctan2(ly, lx) / _TAU + 0.5) * 6.0).astype(np.int64)
    rad = (np.hypot(lx, ly) > 0.30).astype(np.int64)
    return _combine(ci.astype(np.int64), cj.astype(np.int64), t1, ang * rad)


def t_elongtri(res, seed, cells=14.0):
    """Elongated triangular (3.3.3.4.4) — rows of squares alternating with rows
    of triangles, the only Archimedean tiling with two kinds of course."""
    s = res / cells
    yy, xx = coords(res)
    band = np.floor(yy / (s * 0.933))
    inrow = frac(yy / (s * 0.933))
    tri_row = np.mod(band, 2) == 1
    u = xx / s + np.mod(band, 2) * 0.5
    iu = np.floor(u)
    fu = u - iu
    part = np.where(tri_row, ((fu + inrow > 1.0).astype(np.int64)), 2)
    return _combine(band.astype(np.int64), iu.astype(np.int64), part.astype(np.int64))


def t_shatterstar(res, seed, impacts=7, rings=16.0):
    """Impact shatter — radial fractures from strikes set off the panel, crossed
    by the concentric rings each strike sent out."""
    img = np.zeros((res, res), np.uint8)
    r = rng(seed, 41)
    yy, xx = coords(res)
    for i in range(int(impacts)):
        cx = (r.random() * 1.8 - 0.4) * res
        cy = (r.random() * 1.8 - 0.4) * res
        dx, dy = xx - cx, yy - cy
        d = np.hypot(dx, dy) + 1e-5
        th = np.arctan2(dy, dx)
        n = 9 + int(r.random() * 8)
        img[np.abs(frac(th / _TAU * n) - 0.5) > 0.470] = 255
        img[np.abs(frac(d / (res / rings)) - 0.5) > 0.474] = 255
    return _label_regions(img)


TILINGS = {
    "spiral": t_spiral, "conformal": t_conformal, "moiregrid": t_moiregrid,
    "zellige": t_zellige, "mashrabiya": t_mashrabiya, "muqarnas": t_muqarnas,
    "wovencell": t_wovencell, "scalemail": t_scalemail, "fishscale": t_fishscale,
    "droste": t_droste, "fibonacci": t_fibonacci, "laguerre": t_laguerre,
    "penrose_kite": t_penrose_kite, "quasi7": t_quasi7, "brickbond": t_brickbond,
    "jali": t_jali, "hexstar": t_hexstar, "elongtri": t_elongtri,
    "shatterstar": t_shatterstar,
    "kagome": t_kagome, "snubsquare": t_snubsquare, "octsquare": t_octsquare,
    "basketweave": t_basketweave, "triangular": t_triangular, "pinwheel": t_pinwheel,
    "sphinx": t_sphinx, "chair": t_chair, "mondrian": t_mondrian,
    "voronoi_aniso": t_voronoi_aniso, "delaunay": t_delaunay, "bubble": t_bubble,
    "mudcrack": t_mudcrack, "crazing": t_crazing, "columnar": t_columnar,
    "cafewall": t_cafewall, "zigzag": t_zigzag,
    "hexcomb": t_hexcomb, "cairo": t_cairo, "herringbone": t_herringbone,
    "rhombille": t_rhombille, "penrose": t_penrose, "ammann": t_ammann,
    "dodeca": t_dodeca, "lloyd": t_lloyd, "gilbert": t_gilbert,
    "truchet_tri": t_truchet_tri, "wang": t_wang, "girih": t_girih,
    "shear": t_shear,
}


# ════════════════════════════════════════════════════════════════════════════
# RECIPES
# ════════════════════════════════════════════════════════════════════════════

def _R(fid, name, tiling, palette, came, pane, desc, *, targs=None, pane_amt=0.56,
       depth=0.30, hue_jit=0.07, came_w=None, grain=0.98, glass=None, mono=False,
       gen=None, sargs=None):
    d = dict(name=name, tiling=tiling, targs=dict(targs or {}), palette=palette,
             came=came, pane=pane, pane_amt=pane_amt, depth=depth, hue_jit=hue_jit,
             grain=grain, mono=bool(mono), seed=_seed(fid), desc=desc,
             sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0,
                        decorrelation=0.18))
    if came_w:
        d["came_w"] = came_w
    if glass:
        d["glass"] = glass
    if gen:
        d["gen"] = gen
    if sargs:
        d["sargs"].update(sargs)
    return d


# jewel palettes — each finish owns one
TESSERA = {
 "fts_penrose_reliquary": _R("fts_penrose_reliquary", "Penrose Reliquary", "penrose",
    [(28, 118, 168), (96, 52, 176), (176, 44, 122), (36, 150, 148), (208, 158, 44)], "lead", "slump",
    "Aperiodic five-fold rhombs that never repeat, leaded in jewel blues and violets.",
    hue_jit=0.22, targs=dict(spacing=70.0), pane_amt=0.60),
 "fts_ammann_vault": _R("fts_ammann_vault", "Ammann Vault", "ammann",
    [(196, 128, 36), (150, 62, 40), (44, 116, 132), (86, 78, 156)], "brass", "drawn",
    "Eight-fold aperiodic squares and rhombs drawn in amber and teal behind brass came.",
    targs=dict(spacing=54.0), pane_amt=0.58),
 "fts_dodeca_choir": _R("fts_dodeca_choir", "Dodeca Choir", "dodeca",
    [(38, 142, 158), (24, 84, 168), (128, 40, 156), (196, 172, 52), (188, 62, 78), (60, 168, 120), (196, 168, 52)], "hairline", "iris",
    "Twelve-fold quasiperiodic panes under an iridised film, hairline-leaded.",
    targs=dict(spacing=92.0), pane_amt=0.64, depth=0.24, hue_jit=0.20),
 "fts_hex_apiary": _R("fts_hex_apiary", "Hex Apiary", "hexcomb",
    [(206, 150, 30), (176, 96, 26), (96, 108, 40), (52, 122, 110)], "foil", "granite",
    "A honeycomb of rolled amber glass in copper foil, every cell its own shade.",
    targs=dict(cells=26.0), pane_amt=0.60),
 "fts_cairo_lantern": _R("fts_cairo_lantern", "Cairo Lantern", "cairo",
    [(30, 128, 150), (44, 78, 160), (150, 52, 130), (188, 140, 44)], "lead", "seedy",
    "Interlocking pentagons in seedy lantern glass, bubbles caught in every pane.",
    targs=dict(cells=17.0), pane_amt=0.58),
 "fts_rhombille_cube": _R("fts_rhombille_cube", "Rhombille Cube", "rhombille",
    [(214, 186, 132), (120, 96, 66), (46, 78, 92), (176, 122, 54), (86, 106, 78)], "smoke", "granite",
    "Three rhombi to a hexagon: a floor of tumbling cubes that will not sit still.",
    targs=dict(cells=19.0), grain=1.35, depth=0.38, hue_jit=0.03),
 "fts_lloyd_froth": _R("fts_lloyd_froth", "Lloyd Froth", "lloyd",
    [(34, 150, 160), (60, 96, 176), (140, 60, 168), (200, 90, 120)], "hairline", "ripple",
    "Relaxed cells of near-equal size, like soap froth frozen and leaded in place.",
    targs=dict(cells=240), pane_amt=0.60, depth=0.26),
 "fts_gilbert_shatter": _R("fts_gilbert_shatter", "Gilbert Shatter", "gilbert",
    [(180, 60, 48), (206, 148, 44), (52, 108, 120), (100, 44, 132)], "dalle", "crackle",
    "Cracks that nucleate, run both ways and stop where they meet an older crack.",
    targs=dict(cracks=95, length=0.26), pane_amt=0.56, depth=0.34),
 "fts_truchet_braid": _R("fts_truchet_braid", "Truchet Braid", "truchet_tri",
    [(32, 146, 166), (58, 76, 186), (126, 52, 172), (188, 60, 132)], "bevel", "slump",
    "Triangular Truchet arcs braiding across the panel behind bevelled came.",
    targs=dict(cells=11.0), pane_amt=0.60),
 "fts_wang_current": _R("fts_wang_current", "Wang Current", "wang",
    [(40, 132, 144), (176, 132, 40), (150, 54, 60), (70, 84, 158)], "double", "reamy",
    "Edge-matched tiles whose colour runs continue clean across the whole panel.",
    targs=dict(cells=8.0), pane_amt=0.58),
 "fts_girih_strap": _R("fts_girih_strap", "Girih Strap", "girih",
    [(30, 110, 140), (188, 156, 48), (140, 44, 96), (44, 128, 108)], "brass", "flat",
    "Five-fold strapwork interlacing over glass cut to every polygon it leaves.",
    targs=dict(cells=2.8), depth=0.34, hue_jit=0.04),
 "fts_herringbone_hall": _R("fts_herringbone_hall", "Herringbone Hall", "herringbone",
    [(158, 92, 44), (104, 76, 52), (52, 104, 112), (196, 168, 116), (128, 52, 68)], "wire", "drawn",
    "Planks of drawn glass laid herringbone and reinforced with wire.",
    targs=dict(cells=34.0, ratio=3.0), pane_amt=0.62),
 "fts_shear_arcade": _R("fts_shear_arcade", "Shear Arcade", "shear",
    [(46, 118, 176), (28, 152, 150), (122, 60, 168), (200, 128, 52)], "lead", "ripple",
    "A leaded lattice that leans further with every course, like a hall seen at speed.",
    targs=dict(cells=18.0, shear=0.55), pane_amt=0.60),
}


_TESSERA_W2 = {
 "fts_kagome_basket": _R("fts_kagome_basket", "Kagome Basket", "kagome",
    [(196, 142, 40), (40, 122, 130), (150, 60, 52), (86, 116, 62), (188, 178, 140)],
    "brass", "drawn",
    "The trihexagonal basket lattice: triangles and hexagons sharing every vertex.",
    targs=dict(cells=15.0)),
 "fts_snub_carousel": _R("fts_snub_carousel", "Snub Carousel", "snubsquare",
    [(38, 130, 172), (170, 52, 108), (206, 160, 44), (52, 148, 118)], "lead", "ripple",
    "Squares pinwheeling between pairs of triangles, every cell twisted against its neighbour.",
    targs=dict(cells=17.0)),
 "fts_octagon_court": _R("fts_octagon_court", "Octagon Court", "octsquare",
    [(30, 96, 148), (196, 186, 156), (128, 42, 60), (58, 122, 106)], "fatlead", "seedy",
    "Broad octagons with a small square dropped into every crossing.",
    targs=dict(cells=17.0)),
 "fts_basket_weave": _R("fts_basket_weave", "Basket Weave", "basketweave",
    [(178, 118, 44), (96, 74, 46), (54, 104, 110), (204, 176, 118), (196, 168, 52)], "foil", "granite",
    "Pairs of planks crossing over and under in fours, foiled at every join.",
    hue_jit=0.20, targs=dict(cells=30.0)),
 "fts_triangle_choir": _R("fts_triangle_choir", "Triangle Choir", "triangular",
    [(46, 108, 178), (176, 60, 120), (58, 156, 132), (212, 168, 52)], "hairline", "slump",
    "The plain equilateral net, every triangle slumped to its own thickness.",
    targs=dict(cells=16.0)),
 "fts_pinwheel_infinite": _R("fts_pinwheel_infinite", "Pinwheel Infinite", "pinwheel",
    [(34, 116, 156), (150, 46, 132), (198, 152, 46), (44, 140, 116)], "lead", "drawn",
    "Conway's right triangles at one-to-two: subdivide, turn, repeat — no two panes point the same way.",
    gen=576, targs=dict(cells=2.7, depth=2)),
 "fts_sphinx_march": _R("fts_sphinx_march", "Sphinx March", "sphinx",
    [(186, 148, 62), (140, 76, 40), (46, 96, 112), (96, 116, 74)], "smoke", "reamy",
    "The sphinx hexiamond, five triangles to a tile, marching by reflex substitution.",
    grain=1.35, targs=dict(cells=13.0)),
 "fts_chair_recursion": _R("fts_chair_recursion", "Chair Recursion", "chair",
    [(38, 124, 148), (176, 66, 74), (206, 172, 60), (74, 92, 160)], "double", "flat",
    "L-trominoes that subdivide into four smaller chairs, and those into four more.",
    targs=dict(cells=2.6, depth=3), depth=0.36),
 "fts_mondrian_cut": _R("fts_mondrian_cut", "Mondrian Cut", "mondrian",
    [(196, 44, 44), (32, 68, 176), (216, 186, 46), (232, 232, 226), (30, 30, 34)],
    "fatlead", "flat",
    "A guillotine cut every time: rectangles of every proportion, none of them lining up.",
    mono=True, targs=dict(splits=420), depth=0.34, hue_jit=0.02),
 "fts_slat_stretch": _R("fts_slat_stretch", "Slat Stretch", "voronoi_aniso",
    [(40, 138, 150), (108, 54, 158), (188, 92, 52), (58, 106, 168)], "wire", "drawn",
    "Voronoi cells drawn out along one axis until they read as rolled slats.",
    targs=dict(cells=230, aniso=3.2)),
 "fts_delaunay_web": _R("fts_delaunay_web", "Delaunay Web", "delaunay",
    [(30, 110, 160), (168, 48, 116), (52, 148, 128), (204, 158, 48)], "hairline", "slump",
    "The triangulation of a scattered point set — every pane a triangle, no two alike.",
    targs=dict(cells=260)),
 "fts_bubble_raft": _R("fts_bubble_raft", "Bubble Raft", "bubble",
    [(44, 146, 164), (66, 96, 180), (150, 58, 164), (196, 176, 76)], "hairline", "seedy",
    "Hexagonal close packing with the dislocations a real raft always has.",
    targs=dict(cells=18.0, defect=0.30)),
 "fts_mudcrack_pan": _R("fts_mudcrack_pan", "Mudcrack Pan", "mudcrack",
    [(178, 128, 68), (128, 88, 48), (86, 96, 74), (206, 178, 130), (196, 168, 52)], "dalle", "granite",
    "Mud dried until it split: stubby cells, every join meeting at ninety degrees.",
    hue_jit=0.20, targs=dict(cells=200)),
 "fts_crazed_glaze": _R("fts_crazed_glaze", "Crazed Glaze", "crazing",
    [(150, 158, 156), (96, 116, 126), (58, 74, 84), (176, 172, 150)], "hairline", "crackle",
    "The shrinkage net an old glaze crazes into, long cracks first and short ones after.",
    mono=True, glass=(0, 1, 3, 5), targs=dict(scale=2.0), hue_jit=0.10),
 "fts_basalt_column": _R("fts_basalt_column", "Basalt Column", "columnar",
    [(52, 58, 66), (86, 92, 96), (36, 44, 52), (124, 122, 114), (70, 84, 88)],
    "smoke", "granite",
    "Columnar basalt in section: hexagons that cooled imperfectly and wander at the joints.",
    mono=True, targs=dict(cells=15.0, jitter=0.34), hue_jit=0.03, depth=0.36),
 "fts_cafe_wall": _R("fts_cafe_wall", "Cafe Wall", "cafewall",
    [(28, 28, 32), (226, 222, 212), (150, 40, 44), (196, 176, 120)], "lead", "flat",
    "Straight courses the eye insists are wedges, because every row is offset against the last.",
    mono=True, targs=dict(cells=19.0, offset=0.38), hue_jit=0.02, depth=0.32),
 "fts_zigzag_ribbon": _R("fts_zigzag_ribbon", "Zigzag Ribbon", "zigzag",
    [(44, 128, 168), (192, 76, 60), (204, 170, 54), (48, 144, 122)], "bevel", "ripple",
    "Courses that fold back on themselves, chevroning all the way down the panel.",
    targs=dict(cells=10.0, amp=0.42)),
}
TESSERA.update(_TESSERA_W2)


_TESSERA_W3 = {
 "fts_spiral_nave": _R("fts_spiral_nave", "Spiral Nave", "spiral",
    [(32, 118, 172), (128, 48, 156), (196, 88, 52), (46, 148, 132)], "lead", "drawn",
    "Courses winding out from a pole set off the panel, so the leadwork sweeps instead of rings.",
    targs=dict(arms=20.0, rings=24.0)),
 "fts_conformal_bend": _R("fts_conformal_bend", "Conformal Bend", "conformal",
    [(44, 104, 176), (176, 54, 96), (206, 164, 48), (40, 146, 140)], "hairline", "ripple",
    "A square lattice pushed through a conformal map: right angles kept, the grid itself bent.",
    targs=dict(cells=9.0, power=1.35)),
 "fts_moire_beat": _R("fts_moire_beat", "Moire Beat", "moiregrid",
    [(36, 132, 164), (150, 44, 140), (200, 158, 52), (60, 150, 110)], "hairline", "flat",
    "Two grids at a hair of an angle: where they beat, the panes shrink to slivers.",
    targs=dict(cells=17.0, twist=0.11)),
 "fts_zellige_star": _R("fts_zellige_star", "Zellige Star", "zellige",
    [(28, 108, 146), (196, 172, 60), (150, 46, 58), (44, 128, 100), (222, 216, 200)],
    "brass", "seedy",
    "The eight-point star and its cross, cut and set by hand.",
    targs=dict(cells=8.5)),
 "fts_mashrabiya_screen": _R("fts_mashrabiya_screen", "Mashrabiya Screen", "mashrabiya",
    [(196, 138, 48), (120, 78, 40), (40, 104, 116), (214, 190, 138), (140, 54, 76)], "smoke", "granite",
    "A turned-wood screen: discs on a lattice joined by bridges, light coming through the rest.",
    grain=1.35, targs=dict(cells=7.5)),
 "fts_muqarnas_vault": _R("fts_muqarnas_vault", "Muqarnas Vault", "muqarnas",
    [(34, 112, 150), (188, 158, 54), (140, 52, 108), (56, 140, 118)], "brass", "slump",
    "Stepped niches corbelling inward, every tier smaller than the one it hangs from.",
    targs=dict(cells=4.5, steps=4)),
 "fts_woven_interlace": _R("fts_woven_interlace", "Woven Interlace", "wovencell",
    [(42, 126, 152), (168, 72, 48), (196, 164, 60), (86, 92, 158)], "foil", "drawn",
    "Every strand passes above one neighbour and below the next; the crossings are their own panes.",
    targs=dict(cells=17.0)),
 "fts_scalemail_coat": _R("fts_scalemail_coat", "Scalemail Coat", "scalemail",
    [(48, 108, 140), (168, 88, 44), (98, 62, 132), (188, 168, 108), (44, 132, 112)], "wire", "ripple",
    "Riveted scale armour, each disc hiding the top of the scale below it.",
    targs=dict(cells=14.0)),
 "fts_fishscale_roof": _R("fts_fishscale_roof", "Fishscale Roof", "fishscale",
    [(38, 138, 146), (160, 58, 92), (204, 170, 58), (60, 108, 168)], "lead", "slump",
    "Imbricated arcs — the oldest roofing pattern there is.",
    targs=dict(cells=13.0)),
 "fts_droste_well": _R("fts_droste_well", "Droste Well", "droste",
    [(30, 100, 158), (140, 44, 148), (198, 148, 44), (44, 146, 126)], "double", "iris",
    "The same lattice nested inside itself at every octave, opening into a smaller copy of itself.",
    gen=576, targs=dict(cells=70.0, scale=1.12)),
 "fts_fibonacci_course": _R("fts_fibonacci_course", "Fibonacci Course", "fibonacci",
    [(44, 120, 168), (186, 82, 56), (52, 146, 124), (206, 176, 60)], "hairline", "reamy",
    "Two plank widths laid in the golden order, so the courses never settle into a repeat.",
    targs=dict(cells=24.0)),
 "fts_laguerre_press": _R("fts_laguerre_press", "Laguerre Press", "laguerre",
    [(36, 130, 156), (120, 52, 162), (192, 96, 56), (58, 150, 118)], "lead", "seedy",
    "Voronoi with weights: big cells shoulder the small ones aside and the joins go crooked.",
    targs=dict(cells=150, power=26.0)),
 "fts_kite_and_dart": _R("fts_kite_and_dart", "Kite and Dart", "penrose_kite",
    [(30, 124, 164), (168, 46, 118), (200, 166, 56), (66, 96, 172), (46, 152, 124)],
    "bevel", "slump",
    "Penrose kites and darts: the same pentagrid, offset to the singular value that splits them.",
    hue_jit=0.20, targs=dict(spacing=74.0)),
 "fts_sevenfold_drift": _R("fts_sevenfold_drift", "Sevenfold Drift", "quasi7",
    [(40, 140, 152), (140, 60, 168), (204, 154, 48), (56, 104, 176), (176, 62, 96)],
    "hairline", "ripple",
    "Seven-fold order the plane cannot hold periodically, so the panes drift forever.",
    hue_jit=0.20, targs=dict(spacing=108.0)),
 "fts_flemish_bond": _R("fts_flemish_bond", "Flemish Bond", "brickbond",
    [(158, 76, 48), (108, 58, 44), (74, 88, 96), (196, 166, 124)], "fatlead", "granite",
    "A header and a stretcher alternating in every course — the bond that reads hand-laid.",
    targs=dict(cells=13.0)),
 "fts_jali_pierce": _R("fts_jali_pierce", "Jali Pierce", "jali",
    [(196, 186, 160), (46, 118, 128), (150, 108, 44), (96, 66, 116)], "smoke", "flat",
    "Pierced stone: an interlocking net of hexagonal openings inside a hexagonal frame.",
    grain=1.35, targs=dict(cells=3.2), depth=0.36),
 "fts_hexstar_lantern": _R("fts_hexstar_lantern", "Hexstar Lantern", "hexstar",
    [(34, 116, 158), (200, 168, 52), (150, 48, 120), (48, 146, 122)], "brass", "seedy",
    "Six-point stars with the triangles they leave between them.",
    targs=dict(cells=11.0)),
 "fts_elongated_course": _R("fts_elongated_course", "Elongated Course", "elongtri",
    [(46, 132, 160), (176, 66, 74), (198, 164, 56), (72, 100, 164)], "lead", "drawn",
    "Rows of squares alternating with rows of triangles — two kinds of course in one wall.",
    targs=dict(cells=17.0)),
 "fts_impact_shatter": _R("fts_impact_shatter", "Impact Shatter", "shatterstar",
    [(30, 106, 164), (168, 50, 104), (204, 160, 50), (44, 144, 132)], "hairline", "crackle",
    "Radial fractures from strikes set off the panel, crossed by the rings each strike sent out.",
    gen=576, targs=dict(impacts=3, rings=5.5)),
}
TESSERA.update(_TESSERA_W3)


# ════════════════════════════════════════════════════════════════════════════
# ART + REGISTRY CONTRACT (mirrors FORGE: the art IS the look; fracture ignites)
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=8)
def _labels_gen(fid):
    """The tiling, solved once at GEN. paint_fn and spec_fn both need the label
    map, so without this every render generates the tiling twice — which is what
    put the heavier tilings over the 3s budget."""
    d = TESSERA[fid]
    # a couple of tilings (recursive Droste, the drawn shatter) cost enough at
    # GEN to sit on the 3s line; they generate smaller and upscale — labels are
    # piecewise constant, so nothing is lost but the time.
    g = int(d.get("gen", GEN))
    lab = np.asarray(TILINGS[d["tiling"]](g, d["seed"], **d.get("targs", {})), np.int64)
    return upscale_labels(lab, GEN) if g != GEN else lab


def labels_for(fid, res):
    return upscale_labels(_labels_gen(fid), res)


def _art(fid):
    d = TESSERA[fid]
    return glass_art(labels_for(fid, WORK), d, WORK)


@lru_cache(maxsize=6)
def _art_cached(fid):
    return _art(fid)


def _mk(fid):
    d = TESSERA[fid]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        base = fracture_spec(art, m2, as_uint8=True, **d["sargs"])
        # the ignition stays underneath; the glass/came MATERIAL layer rides the
        # finish's own label map on top (see kit.glass_spec for why)
        return kit.glass_spec(base, _labels_gen(fid), d, fw)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    for fid in TESSERA:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
    return f"fractured-tessera: {len(TESSERA)} leadlight tilings live ({_GROUP})"
