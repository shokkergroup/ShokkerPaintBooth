"""FRACTURED expansion pack — RECURSIVE CURVES & SPACE-FILLING FRACTALS.

Eleven GENUINELY DISTINCT field-generators in the space-filling / recursive-curve /
fractal family. Each is a *different algorithm*, not a recolor of another:

  * hilbert_curve      — L-system Hilbert space-filling curve, rasterized as a ribbon +
                         a signed distance field (continuous serpentine flow).
  * dragon_curve       — Heighway dragon via the bit-reversal turn sequence; rasterized
                         polyline distance field (self-similar twin-dragon tessellation).
  * gosper_flowsnake   — Gosper (flowsnake) L-system on a hex lattice; 60deg turtle.
  * koch_snowflake     — Koch edge-subdivision flakes, multi-flake lattice, distance field.
  * sierpinski_carpet  — base-3 digit test (no recursion stack); square-hole gasket field.
  * sierpinski_arrow   — Sierpinski arrowhead-curve L-system (a CURVE that fills a triangle).
  * tsquare_fractal    — T-square: recursive square placement at corners (overlap depth field).
  * htree_fractal      — H-tree: recursive binary H branching; segment distance field.
  * pythagoras_tree    — recursive square+right-triangle branching with per-branch lean.
  * vicsek_fractal     — Vicsek cross/saltire IFS via base-3 digit test (plus-shape gasket).
  * levy_c_curve       — Levy C curve L-system; 45deg turtle, dense fractal coastline.

All deterministic by seed, computed at low 'res' then upscaled, normalized to 0..1.
Pure numpy + cv2 + scipy. Self-test at the bottom (run from repo root).
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy import ndimage


# ----------------------------------------------------------------------------- helpers
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _finish(field, h, w):
    """Sanitize, upscale, normalize."""
    field = np.nan_to_num(field.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    return _norm(_up(field, h, w))


def _polyline_field(pts, res, thick=1.2):
    """Rasterize a polyline (Nx2 in pixel coords) into a thin mask, then return the
    distance-from-line field (continuous, fine, full coverage). pts in [0,res)."""
    img = np.zeros((res, res), np.uint8)
    p = np.round(pts).astype(np.int32)
    p[:, 0] = np.clip(p[:, 0], 0, res - 1)
    p[:, 1] = np.clip(p[:, 1], 0, res - 1)
    cv2.polylines(img, [p.reshape(-1, 1, 2)], False, 255,
                  thickness=max(1, int(round(thick))), lineType=cv2.LINE_AA)
    return img


def _ridged_distance(mask, res):
    """From a stroke mask build a ridged distance field: bright ON the curve, ringing
    away from it via sin of the EDT. Gives crushed high-frequency detail everywhere."""
    on = mask > 32
    if not on.any():
        on[res // 2, res // 2] = True
    dist = ndimage.distance_transform_edt(~on).astype(np.float32)
    dist /= (dist.max() + 1e-6)
    # ringed contours of the distance field -> busy fine detail filling the whole plane
    rings = 0.5 + 0.5 * np.cos(dist * (res * 0.18))
    core = np.exp(-dist * 9.0)            # bright crisp curve
    body = (1.0 - dist) ** 1.6           # smooth falloff for coverage
    f = 0.55 * core + 0.30 * rings * (0.3 + 0.7 * body) + 0.25 * body
    return f


# ----------------------------------------------------------------------------- L-system
def _lsystem(axiom, rules, depth):
    s = axiom
    for _ in range(depth):
        s = "".join(rules.get(c, c) for c in s)
    return s


def _turtle(commands, angle_deg, *, start=(0.0, 0.0), heading=0.0,
            forward_chars="F", draw_chars="F"):
    """Run a turtle over an L-system string. + turns left, - turns right.
    Returns Nx2 array of vertices (float). Vectorized post-pass keeps it fast."""
    th = np.deg2rad(angle_deg)
    # First pass: build a list of (turn, draw) ops -> turn deltas and draw flags.
    turns = []
    draws = []
    for c in commands:
        if c == "+":
            turns.append(+th); draws.append(0)
        elif c == "-":
            turns.append(-th); draws.append(0)
        elif c in forward_chars or c in draw_chars:
            turns.append(0.0); draws.append(1)
        # other symbols (A, B, X, Y ...) are pure rewrite vars -> no turtle action
    if not draws:
        return np.array([[start[0], start[1]]], np.float32)
    turns = np.asarray(turns, np.float64)
    draws = np.asarray(draws, np.float64)
    head = heading + np.cumsum(turns)
    dx = np.cos(head) * draws
    dy = np.sin(head) * draws
    x = start[0] + np.cumsum(dx)
    y = start[1] + np.cumsum(dy)
    pts = np.stack([np.concatenate([[start[0]], x]),
                    np.concatenate([[start[1]], y])], axis=1)
    return pts.astype(np.float32)


def _fit_to(pts, res, margin=0.06):
    """Scale+center a polyline to fit [margin*res, (1-margin)*res]^2."""
    mn = pts.min(0); mx = pts.max(0)
    span = np.maximum(mx - mn, 1e-6)
    s = (1.0 - 2 * margin) * res / span.max()
    q = (pts - mn) * s
    off = (res - (mx - mn) * s) * 0.5
    return q + off


# =========================================================================== ENGINES
def hilbert_curve(h, w, seed, *, res=512) -> np.ndarray:
    """Hilbert space-filling curve (L-system A/B), rasterized to a ribbon + distance field."""
    rng = _rng(seed)
    depth = int(rng.integers(6, 8))          # 6 or 7 -> dense serpentine fill
    rules = {"A": "+BF-AFA-FB+", "B": "-AF+BFB+FA-"}
    s = _lsystem("A", rules, depth)
    pts = _turtle(s, 90.0, heading=rng.uniform(0, 2 * np.pi))
    pts = _fit_to(pts, res)
    mask = _polyline_field(pts, res, thick=1.0)
    f = _ridged_distance(mask, res)
    # overlay the crisp serpentine ribbon so the curve itself reads premium
    f = 0.7 * f + 0.3 * _norm(mask.astype(np.float32))
    return _finish(f, h, w)


def dragon_curve(h, w, seed, *, res=512) -> np.ndarray:
    """Heighway dragon curve from the bit-reversal turn sequence; twin-dragon tessellation."""
    rng = _rng(seed)
    n = int(rng.integers(15, 17))            # 2^n segments
    N = 1 << n
    # turn at step k = ((k & -k) << 1) & k  -> 0 means left(+), nonzero means right(-)
    k = np.arange(1, N)
    left = (((k & -k) << 1) & k) == 0
    turns = np.where(left, +np.pi / 2, -np.pi / 2)
    head = rng.uniform(0, 2 * np.pi) + np.concatenate([[0.0], np.cumsum(turns)])
    dx = np.cos(head); dy = np.sin(head)
    x = np.concatenate([[0.0], np.cumsum(dx)])
    y = np.concatenate([[0.0], np.cumsum(dy)])
    pts = np.stack([x, y], 1).astype(np.float32)
    pts = _fit_to(pts, res, margin=0.08)
    mask = _polyline_field(pts, res, thick=1.0)
    f = _ridged_distance(mask, res)
    f = 0.65 * f + 0.35 * _norm(cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.0))
    return _finish(f, h, w)


def gosper_flowsnake(h, w, seed, *, res=512) -> np.ndarray:
    """Gosper (flowsnake) curve L-system on a hex lattice; 60deg turtle fills the plane."""
    rng = _rng(seed)
    depth = int(rng.integers(3, 5))
    rules = {"A": "A-B--B+A++AA+B-", "B": "+A-BB--B-A++A+B"}
    s = _lsystem("A", rules, depth)
    # A and B both draw forward; +/- turn 60deg
    pts = _turtle(s, 60.0, heading=rng.uniform(0, 2 * np.pi),
                  forward_chars="AB", draw_chars="AB")
    pts = _fit_to(pts, res, margin=0.05)
    mask = _polyline_field(pts, res, thick=1.1)
    f = _ridged_distance(mask, res)
    f = 0.72 * f + 0.28 * _norm(mask.astype(np.float32))
    return _finish(f, h, w)


def koch_snowflake(h, w, seed, *, res=512) -> np.ndarray:
    """Koch snowflake: edge-subdivision flakes tiled across the plane; distance field."""
    rng = _rng(seed)

    def koch_edge(p0, p1, depth):
        if depth == 0:
            return [p0]
        p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
        d = (p1 - p0) / 3.0
        a = p0 + d
        b = p0 + 2 * d
        # apex of the outward bump (rotate d by -60deg)
        ang = -np.pi / 3
        rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        c = a + rot @ d
        return (koch_edge(p0, a, depth - 1) + koch_edge(a, c, depth - 1)
                + koch_edge(c, b, depth - 1) + koch_edge(b, p1, depth - 1))

    depth = 4
    # base equilateral triangle
    base = [np.array([0.0, 0.0]), np.array([1.0, 0.0]),
            np.array([0.5, np.sqrt(3) / 2])]
    verts = []
    for i in range(3):
        verts += koch_edge(base[i], base[(i + 1) % 3], depth)
    verts.append(base[0])
    flake = np.asarray(verts, np.float32)
    flake -= flake.mean(0)

    # tile several flakes at varied scales/rotations for full coverage + fine detail
    mask = np.zeros((res, res), np.uint8)
    ncell = int(rng.integers(3, 5))
    cell = res / ncell
    for gy in range(ncell + 1):
        for gx in range(ncell + 1):
            cx = (gx + 0.5 * (gy % 2)) * cell
            cy = gy * cell
            sc = cell * rng.uniform(0.34, 0.5)
            a = rng.uniform(0, 2 * np.pi)
            R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]], np.float32)
            p = (flake @ R.T) * sc + np.array([cx, cy], np.float32)
            mask = np.maximum(mask, _polyline_field(p, res, thick=1.0))
    f = _ridged_distance(mask, res)
    return _finish(f, h, w)


def sierpinski_carpet(h, w, seed, *, res=512) -> np.ndarray:
    """Sierpinski carpet via base-3 digit test (membership-by-digits, no recursion)."""
    rng = _rng(seed)
    levels = 6
    rot = rng.uniform(0, 2 * np.pi)
    jx, jy = rng.uniform(-0.12, 0.12, 2)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    # rotate the lattice so the carpet isn't axis-aligned on the UV sheet
    cx = cy = (res - 1) / 2.0
    ca, sa = np.cos(rot), np.sin(rot)
    u = (ca * (xx - cx) - sa * (yy - cy)) / res + 0.5 + jx
    v = (sa * (xx - cx) + ca * (yy - cy)) / res + 0.5 + jy
    u = np.mod(u, 1.0); v = np.mod(v, 1.0)
    # membership: a point is removed at any level where BOTH base-3 digits == 1
    member = np.ones((res, res), np.float32)
    depth_field = np.zeros((res, res), np.float32)
    uu = u.copy(); vv = v.copy()
    for lvl in range(levels):
        uu = uu * 3.0; vv = vv * 3.0
        du = np.floor(np.mod(uu, 3.0)).astype(np.int32)
        dv = np.floor(np.mod(vv, 3.0)).astype(np.int32)
        hole = (du == 1) & (dv == 1)
        depth_field += member * hole * (levels - lvl)   # bigger holes weigh more
        member = member * (~hole)
    # blend the gasket membership with the depth field -> crushed nested-square detail
    f = 0.5 * _norm(depth_field) + 0.5 * member
    f = cv2.GaussianBlur(f, (0, 0), 0.7)
    return _finish(f, h, w)


def sierpinski_arrow(h, w, seed, *, res=512) -> np.ndarray:
    """Sierpinski arrowhead curve (L-system) — a single CURVE that fills a triangle."""
    rng = _rng(seed)
    depth = int(rng.integers(7, 9))
    rules = {"A": "B-A-B", "B": "A+B+A"}     # A,B both draw forward
    s = _lsystem("A", rules, depth)
    pts = _turtle(s, 60.0, heading=rng.uniform(0, 2 * np.pi),
                  forward_chars="AB", draw_chars="AB")
    pts = _fit_to(pts, res, margin=0.05)
    mask = _polyline_field(pts, res, thick=1.0)
    f = _ridged_distance(mask, res)
    f = 0.7 * f + 0.3 * _norm(mask.astype(np.float32))
    return _finish(f, h, w)


def tsquare_fractal(h, w, seed, *, res=512) -> np.ndarray:
    """T-square fractal: recursively place quarter-size squares at each corner; overlap depth."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)

    def place(cx, cy, half, depth):
        if depth == 0 or half < 1.0:
            return
        x0 = int(max(0, cx - half)); x1 = int(min(res, cx + half))
        y0 = int(max(0, cy - half)); y1 = int(min(res, cy + half))
        if x1 > x0 and y1 > y0:
            acc[y0:y1, x0:x1] += 1.0
        hh = half * 0.5
        for sx in (-1, 1):
            for sy in (-1, 1):
                place(cx + sx * half, cy + sy * half, hh, depth - 1)

    depth = 6
    rot = rng.uniform(0, 2 * np.pi)
    place(res * 0.5, res * 0.5, res * 0.235, depth)
    # rotate so it isn't axis aligned; ring the integer depth field for fine detail
    M = cv2.getRotationMatrix2D((res / 2, res / 2), np.rad2deg(rot), 1.0)
    acc = cv2.warpAffine(acc, M, (res, res), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT)
    edges = cv2.Laplacian(acc, cv2.CV_32F, ksize=3)
    f = 0.6 * _norm(acc) + 0.4 * _norm(np.abs(edges))
    return _finish(f, h, w)


def htree_fractal(h, w, seed, *, res=512) -> np.ndarray:
    """H-tree fractal: recursive H-shaped binary branching; segment distance field."""
    rng = _rng(seed)
    segs = []   # list of (x0,y0,x1,y1)

    def htree(cx, cy, length, horiz, depth):
        if depth == 0 or length < 2.0:
            return
        hl = length / 2.0
        if horiz:
            segs.append((cx - hl, cy, cx + hl, cy))
            ends = [(cx - hl, cy), (cx + hl, cy)]
        else:
            segs.append((cx, cy - hl, cx, cy + hl))
            ends = [(cx, cy - hl), (cx, cy + hl)]
        nl = length / np.sqrt(2.0)
        for ex, ey in ends:
            htree(ex, ey, nl, not horiz, depth - 1)

    htree(res * 0.5, res * 0.5, res * 0.62, True, 11)
    rot = rng.uniform(0, 2 * np.pi)
    img = np.zeros((res, res), np.uint8)
    ca, sa = np.cos(rot), np.sin(rot); cx = cy = res / 2.0
    for (x0, y0, x1, y1) in segs:
        def rp(x, y):
            return (ca * (x - cx) - sa * (y - cy) + cx,
                    sa * (x - cx) + ca * (y - cy) + cy)
        ax, ay = rp(x0, y0); bx, by = rp(x1, y1)
        cv2.line(img, (int(ax), int(ay)), (int(bx), int(by)), 255, 1, cv2.LINE_AA)
    f = _ridged_distance(img, res)
    f = 0.68 * f + 0.32 * _norm(img.astype(np.float32))
    return _finish(f, h, w)


def pythagoras_tree(h, w, seed, *, res=512) -> np.ndarray:
    """Pythagoras tree: recursive square + right-triangle branching with per-tree lean."""
    rng = _rng(seed)
    lean = float(rng.uniform(np.deg2rad(28), np.deg2rad(58)))   # branch angle
    ca, sa = np.cos(lean), np.sin(lean)
    img = np.zeros((res, res), np.float32)      # filled-square depth field
    edge = np.zeros((res, res), np.uint8)       # crisp square outlines (fine detail)

    def grow(a, b, depth):
        a = np.asarray(a, float); b = np.asarray(b, float)
        d = b - a
        L = np.hypot(*d)
        if depth <= 0 or L < 2.0:
            # still draw the leaf square
            perp = np.array([-d[1], d[0]])
            poly = np.array([a, b, b + perp, a + perp], np.int32)
            cv2.fillConvexPoly(img, poly, 0.9)
            cv2.polylines(edge, [poly.reshape(-1, 1, 2)], True, 255, 1, cv2.LINE_AA)
            return
        perp = np.array([-d[1], d[0]])
        e = a + perp; c = b + perp
        poly = np.array([a, b, c, e], np.int32)
        cv2.fillConvexPoly(img, poly, float(0.3 + 0.7 * depth / 12.0))
        cv2.polylines(img, [poly.reshape(-1, 1, 2)], True, 1.0, 1, cv2.LINE_AA)
        cv2.polylines(edge, [poly.reshape(-1, 1, 2)], True, 255, 1, cv2.LINE_AA)
        # top edge e->c ; apex splits it via the lean
        topvec = c - e
        # left segment: rotate topvec by lean, length cos(lean)*L
        Rl = np.array([[ca, -sa], [sa, ca]])
        left_v = (Rl @ topvec) * ca
        apex = e + left_v
        grow(e, apex, depth - 1)
        grow(apex, c, depth - 1)

    base = res * rng.uniform(0.16, 0.22)
    bx = res * 0.5
    by = res * 0.92
    grow((bx - base / 2, by), (bx + base / 2, by), 11)
    rot = rng.uniform(-0.4, 0.4)
    M = cv2.getRotationMatrix2D((res / 2, res / 2), np.rad2deg(rot), 1.0)
    img = cv2.warpAffine(img, M, (res, res), borderMode=cv2.BORDER_REFLECT)
    edgef = cv2.warpAffine(edge.astype(np.float32), M, (res, res),
                           borderMode=cv2.BORDER_REFLECT)
    # ridge the structure for crushed detail + ensure coverage via distance ringing
    on = img > 0.05
    dist = ndimage.distance_transform_edt(~on).astype(np.float32)
    dist /= (dist.max() + 1e-6)
    rings = 0.5 + 0.5 * np.cos(dist * (res * 0.16))
    f = (0.40 * _norm(img) + 0.30 * _norm(edgef)
         + 0.18 * rings * (1.0 - dist) + 0.12 * (1.0 - dist) ** 1.4)
    return _finish(f, h, w)


def vicsek_fractal(h, w, seed, *, res=512) -> np.ndarray:
    """Vicsek (cross/saltire) fractal via base-3 digit test; plus-shape recursive gasket."""
    rng = _rng(seed)
    levels = 6
    saltire = bool(rng.integers(0, 2))       # X variant vs + variant
    rot = rng.uniform(0, 2 * np.pi)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx = cy = (res - 1) / 2.0
    ca, sa = np.cos(rot), np.sin(rot)
    u = (ca * (xx - cx) - sa * (yy - cy)) / res + 0.5
    v = (sa * (xx - cx) + ca * (yy - cy)) / res + 0.5
    u = np.mod(u, 1.0); v = np.mod(v, 1.0)
    member = np.ones((res, res), np.float32)
    depth_field = np.zeros((res, res), np.float32)
    uu = u.copy(); vv = v.copy()
    for lvl in range(levels):
        uu = uu * 3.0; vv = vv * 3.0
        du = np.floor(np.mod(uu, 3.0)).astype(np.int32)
        dv = np.floor(np.mod(vv, 3.0)).astype(np.int32)
        if saltire:   # keep the 4 corners + center (X)
            keep = ((du != 1) & (dv != 1)) | ((du == 1) & (dv == 1))
        else:         # keep center column/row + center (+)
            keep = (du == 1) | (dv == 1)
        depth_field += member * keep * (lvl + 1)
        member = member * keep
    f = 0.5 * _norm(depth_field) + 0.5 * member
    f = cv2.GaussianBlur(f, (0, 0), 0.6)
    return _finish(f, h, w)


def levy_c_curve(h, w, seed, *, res=512) -> np.ndarray:
    """Levy C curve L-system; 45deg turtle, dense self-similar fractal coastline."""
    rng = _rng(seed)
    depth = int(rng.integers(13, 16))
    rules = {"F": "+F--F+"}
    s = _lsystem("F", rules, depth)
    pts = _turtle(s, 45.0, heading=rng.uniform(0, 2 * np.pi))
    pts = _fit_to(pts, res, margin=0.06)
    mask = _polyline_field(pts, res, thick=1.0)
    f = _ridged_distance(mask, res)
    f = 0.66 * f + 0.34 * _norm(cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.9))
    return _finish(f, h, w)


# ----------------------------------------------------------------------------- registry
ENGINES = {
    "hilbert_curve": hilbert_curve,
    "dragon_curve": dragon_curve,
    "gosper_flowsnake": gosper_flowsnake,
    "koch_snowflake": koch_snowflake,
    "sierpinski_carpet": sierpinski_carpet,
    "sierpinski_arrow": sierpinski_arrow,
    "tsquare_fractal": tsquare_fractal,
    "htree_fractal": htree_fractal,
    "pythagoras_tree": pythagoras_tree,
    "vicsek_fractal": vicsek_fractal,
    "levy_c_curve": levy_c_curve,
}


def _fineness(f):
    f = f.astype(np.float32)
    return float((f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6))


if __name__ == "__main__":
    H = W = 1024
    print(f"{'engine':<20} {'secs':>6} {'fine':>6} {'std':>6} {'min':>5} {'max':>5}  status")
    print("-" * 70)
    all_ok = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, W, 12345)
        dt = time.time() - t0
        fine = _fineness(f)
        std = float(f.std())
        finite = bool(np.isfinite(f).all())
        ok = (dt < 2.5) and (fine >= 0.12) and (std > 0.06) and finite \
            and f.min() >= -1e-4 and f.max() <= 1.0 + 1e-4
        all_ok = all_ok and ok
        flags = []
        if dt >= 2.5: flags.append("SLOW")
        if fine < 0.12: flags.append("BLOB")
        if std <= 0.06: flags.append("FLAT")
        if not finite: flags.append("NAN")
        print(f"{name:<20} {dt:6.2f} {fine:6.3f} {std:6.3f} "
              f"{f.min():5.2f} {f.max():5.2f}  {'OK' if ok else ' '.join(flags)}")
    print("-" * 70)
    print("ALL PASS" if all_ok else "FAILURES PRESENT")
