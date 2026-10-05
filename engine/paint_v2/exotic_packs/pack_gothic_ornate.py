"""GOTHIC / DARK-ORNATE — menacing-elegance field engines for SPB.

Each engine produces an intricate, FULL-COVERAGE scalar FIELD in 0..1 (shape h,w),
computed at a low 'res' then upscaled. Every engine is a DIFFERENT algorithm, none of
them re-skins of the already-covered families (no voronoi/marble/RD/curl/penrose/
apollonian/guilloche/etc). They build crisp, high-contrast, in-your-face structure that
reads as wrought iron / cathedral tracery wrapped on a race car.

  * rose_window        — recursive radial tracery: rotational mullion network with nested
                         foils carved by an inverse-distance-to-stroke field (rose window).
  * rib_vault          — pointed-arch rib-vault: a network of two-center ogival arches whose
                         rib skeletons knit into a groin-vault lattice (segment-distance web).
  * iron_filigree      — wrought-iron scrollwork: parametric logarithmic C/S volute scrolls
                         stamped as raised iron bars (stroke stamping + emboss ridges).
  * thorn_bramble      — barbed bramble lattice: space-colonization vine growth (open-leaf
                         venation algorithm) with recursive barb spurs along every branch.
  * dark_damask        — damask brocade: a half-drop ogee repeat built from analytic
                         super-ellipse ogee cells filled with mirrored acanthus silhouettes.
  * blackletter_grid   — blackletter stroke geometry: broad-nib pen strokes (oriented
                         elliptical brush convolved along Gothic textura ductus paths).
  * ossuary_lattice    — bone lattice: an interlocked femur/skull arcade built from
                         capsule + ovoid distance primitives packed on a brick grid.
  * spire_fractal      — spire & finial fractal: recursive crocketed pinnacles (an L-system
                         of pointed gables with cusped finials) rasterized as a ridge field.
  * quatrefoil_tess    — quatrefoil/trefoil tessellation: a tiled lobed-circle pattern with
                         interstitial cusps via min-of-lobe-distances on a tight lattice.
  * baroque_acanthus   — baroque acanthus scroll: a recursive helical-frond field where each
                         frond spawns counter-curling leaflets (turtle-curve flow stamping).
  * tracery_web        — gothic plate-tracery web: a randomized cusped-arc network grown by
                         a Delaunay-of-arcs skeleton, every cell a pointed lancet.
  * wrought_screen     — pierced iron screen: an interlaced over/under strapwork band that
                         weaves a quatrefoil rood-screen grille (signed alternating weave).

Contract: def NAME(h, w, seed, *, res=...) -> float32 (h,w) in [0,1].
Pure numpy + cv2 + scipy. Deterministic via np.random.default_rng(seed & 0xffffffff).
"""
from __future__ import annotations

import numpy as np
import cv2
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt

PHI = (1.0 + 5.0 ** 0.5) / 2.0
TAU = 2.0 * np.pi


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


def _stroke_field(res, polylines, width_px=1.4, kind="ridge"):
    """Distance-to-nearest-stroke field. polylines: list of (N,2) arrays in PIXEL coords.
    Returns a crisp raised-bar field where strokes are bright (kind='ridge') ."""
    pts = []
    for pl in polylines:
        pl = np.asarray(pl, np.float32)
        if pl.shape[0] < 2:
            continue
        # densify so the KD tree sees a continuous stroke
        seg = np.diff(pl, axis=0)
        seglen = np.hypot(seg[:, 0], seg[:, 1])
        for i in range(len(seg)):
            n = max(2, int(seglen[i] / 1.2) + 1)
            t = np.linspace(0, 1, n, dtype=np.float32)[:, None]
            pts.append(pl[i][None, :] * (1 - t) + pl[i + 1][None, :] * t)
    if not pts:
        return np.zeros((res, res), np.float32)
    pts = np.concatenate(pts, 0)
    pts = pts[(pts[:, 0] >= -4) & (pts[:, 0] < res + 4) &
              (pts[:, 1] >= -4) & (pts[:, 1] < res + 4)]
    if len(pts) == 0:
        return np.zeros((res, res), np.float32)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:res, 0:res]
    q = np.stack([xx.ravel(), yy.ravel()], 1).astype(np.float32)
    d, _ = tree.query(q, k=1, workers=-1)
    d = d.reshape(res, res)
    # raised bar: bright on the stroke, dark off it, but never flat (carve a valley)
    bar = np.exp(-(d / width_px) ** 2)
    return bar.astype(np.float32)


# ===========================================================================
# 1. ROSE WINDOW — recursive radial tracery.
# ===========================================================================
def rose_window(h, w, seed, *, res=640):
    rng = _rng(seed)
    X, Y = _grid(res)
    r = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    N = int(rng.integers(8, 14))          # primary petals
    rings = int(rng.integers(3, 5))
    field = np.zeros((res, res), np.float32)
    bw = res * 0.012                      # bar half-width in px-equivalents (crisp)

    # radial mullions + concentric ring mullions (the lead cames)
    mull = np.abs(np.cos(N * th * 0.5)) ** 6
    field = np.maximum(field, mull * np.clip(1.0 - r, 0, 1))
    for k in range(1, rings + 1):
        rk = k / (rings + 0.5)
        field = np.maximum(field, np.exp(-((r - rk) / (bw * 0.0026)) ** 2))

    # nested foils: exploit rotational symmetry — fold the whole plane into ONE wedge
    # per ring (angle modulo 2pi/spokes), so each ring is a single vectorized pass.
    cusps = int(rng.integers(3, 6))
    for k in range(1, rings + 1):
        rk = k / (rings + 0.5)
        spokes = N if k % 2 else N * 2
        rad = 0.42 / (rings + 0.5)
        phase = 0.0 if k % 2 else np.pi / spokes
        wedge = TAU / spokes
        # nearest spoke angle to each pixel
        a_snap = np.round((th - phase) / wedge) * wedge + phase
        cx = rk * np.cos(a_snap); cy = rk * np.sin(a_snap)
        dx = X - cx; dy = Y - cy
        lr = np.hypot(dx, dy)
        la = np.arctan2(dy, dx)
        lobe = rad * (1.0 + 0.42 * np.cos(cusps * la))
        foil = np.exp(-((lr - lobe) / 0.012) ** 2)
        field = np.maximum(field, foil)
    # central oculus + outer roundel frame
    field = np.maximum(field, np.exp(-((r - 0.10) / 0.012) ** 2))
    field = np.maximum(field, np.exp(-((r - 0.97) / 0.013) ** 2))
    field = np.maximum(field, np.exp(-((r - 0.78) / 0.012) ** 2))
    field *= (r <= 1.02)
    # glazed ground inside each compartment so coverage is total + crisp
    glaze = 0.30 * (np.abs(np.sin(N * th)) ** 0.5) * (r < 0.97) * (1 - field)
    field = np.maximum(field, glaze)
    return _finish(field, h, w)


# ===========================================================================
# 2. RIB VAULT — pointed-arch ogival rib network.
# ===========================================================================
def _ogive(p0, p1, bend, n=40):
    """Two-center pointed arch between p0,p1 with apex pushed by 'bend' along the normal."""
    p0 = np.asarray(p0, np.float32); p1 = np.asarray(p1, np.float32)
    mid = 0.5 * (p0 + p1)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]], np.float32)
    nl = np.hypot(*nrm) + 1e-6
    nrm /= nl
    apex = mid + nrm * bend
    t = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    a = p0 * (1 - t) + apex * t
    b = apex * (1 - t) + p1 * t
    return np.concatenate([a, b * (t > 0.5) + a * 0])  # quadratic-ish two-segment pointed


def rib_vault(h, w, seed, *, res=512):
    rng = _rng(seed)
    gx = int(rng.integers(4, 6)); gy = int(rng.integers(4, 6))
    polys = []
    xs = np.linspace(0, res, gx + 1)
    ys = np.linspace(0, res, gy + 1)
    bend = res / (gx + gy) * rng.uniform(0.45, 0.7)
    for j in range(gy):
        for i in range(gx):
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys[j], ys[j + 1]
            c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
            corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            # diagonal groin ribs from each corner to a raised boss + side ogives
            for cx, cy in corners:
                p = np.array([cx, cy], np.float32)
                t = np.linspace(0, 1, 30)[:, None]
                rib = p * (1 - t) + c * t
                # bow the rib outward (pointed vault springing)
                mid = 0.5 * (p + c); nrm = (c - p)[::-1] * np.array([-1, 1])
                nrm = nrm / (np.hypot(*nrm) + 1e-6)
                bow = np.sin(t.ravel() * np.pi) * bend * 0.3
                rib = rib + nrm[None, :] * bow[:, None]
                polys.append(rib)
            # the 4 pointed wall arches
            polys.append(_ogive((x0, y0), (x1, y0), bend))
            polys.append(_ogive((x1, y0), (x1, y1), bend))
            polys.append(_ogive((x1, y1), (x0, y1), bend))
            polys.append(_ogive((x0, y1), (x0, y0), bend))
    field = _stroke_field(res, polys, width_px=res / 200.0)
    # emboss: add a thin secondary rib offset to give iron-edge crispness
    field = np.maximum(field, 0.6 * _stroke_field(res, polys, width_px=res / 380.0))
    return _finish(field, h, w)


# ===========================================================================
# 3. IRON FILIGREE — logarithmic C/S volute scrollwork.
# ===========================================================================
def iron_filigree(h, w, seed, *, res=512):
    rng = _rng(seed)
    polys = []
    n_scroll = int(rng.integers(26, 40))
    for _ in range(n_scroll):
        cx, cy = rng.uniform(0.05, 0.95, 2) * res
        a0 = rng.uniform(0, TAU)
        turns = rng.uniform(1.4, 2.6)
        b = rng.uniform(0.10, 0.20)            # log-spiral tightness
        scale = rng.uniform(0.04, 0.11) * res
        sign = 1 if rng.random() < 0.5 else -1
        t = np.linspace(0, turns * TAU, 90)
        r = scale * np.exp(b * t)
        x = cx + sign * r * np.cos(t + a0)
        y = cy + r * np.sin(t + a0)
        m = (x > -10) & (x < res + 10) & (y > -10) & (y < res + 10)
        polys.append(np.stack([x[m], y[m]], 1))
        # mirrored S-partner sharing the eye -> S-scroll
        x2 = cx - sign * r * np.cos(-t + a0)
        y2 = cy - r * np.sin(-t + a0)
        m2 = (x2 > -10) & (x2 < res + 10) & (y2 > -10) & (y2 < res + 10)
        polys.append(np.stack([x2[m2], y2[m2]], 1))
    field = _stroke_field(res, polys, width_px=res / 230.0)
    # iron emboss: bright core ridge + dark groove edges
    core = _stroke_field(res, polys, width_px=res / 420.0)
    field = np.clip(field + 0.5 * core, 0, 1)
    # fill the negative space with a faint hammered tooth so coverage is total
    tooth = _norm(cv2.GaussianBlur(field, (0, 0), 1.0))
    field = np.maximum(field, 0.18 * (np.sin(_grid(res)[0] * 60) * np.sin(_grid(res)[1] * 60) * 0.5 + 0.5) * (1 - tooth))
    return _finish(field, h, w)


# ===========================================================================
# 4. THORN BRAMBLE — space-colonization vine growth + barbs.
# ===========================================================================
def thorn_bramble(h, w, seed, *, res=512):
    rng = _rng(seed)
    n_attr = 1100
    attr = rng.uniform(0.04, 0.96, (n_attr, 2)) * res
    n_roots = int(rng.integers(6, 10))
    nodes = list(rng.uniform(0.1, 0.9, (n_roots, 2)) * res)
    parent = [-1] * n_roots
    infl = res * 0.16
    kill = res * 0.035
    step = res * 0.022
    edges = []
    for _ in range(420):
        if len(attr) == 0:
            break
        ntree = cKDTree(np.array(nodes))
        d, idx = ntree.query(attr, k=1)
        keep = d < infl
        if not keep.any():
            break
        # accumulate growth direction per node
        grow = {}
        for ai in np.where(keep)[0]:
            ni = idx[ai]
            v = attr[ai] - nodes[ni]
            v = v / (np.hypot(*v) + 1e-6)
            grow.setdefault(ni, []).append(v)
        new_nodes = []
        for ni, vs in grow.items():
            dirv = np.mean(vs, 0)
            dirv = dirv / (np.hypot(*dirv) + 1e-6)
            jit = rng.normal(0, 0.18, 2)
            np_pos = nodes[ni] + (dirv + jit) * step
            new_nodes.append((np_pos, ni))
        for np_pos, ni in new_nodes:
            nodes.append(np_pos); parent.append(ni)
            edges.append((nodes[ni], np_pos))
        atree = cKDTree(np.array(nodes))
        dd, _ = atree.query(attr, k=1)
        attr = attr[dd > kill]
        if len(nodes) > 2600:
            break
    polys = [np.array([a, b], np.float32) for a, b in edges]
    # barbs: at every other edge spawn a short backward spur (the thorn)
    for k, (a, b) in enumerate(edges):
        if k % 2:
            a = np.asarray(a); b = np.asarray(b)
            v = b - a; L = np.hypot(*v) + 1e-6
            v /= L
            nrm = np.array([-v[1], v[0]])
            base = a + v * (L * 0.6)
            tip = base + (nrm * (1 if k % 4 else -1) - v) * (res * 0.018)
            polys.append(np.array([base, tip], np.float32))
    field = _stroke_field(res, polys, width_px=res / 300.0)
    # backdrop bramble haze so nothing is bare
    field = np.maximum(field, 0.22 * _norm(cv2.GaussianBlur(field, (0, 0), 4.0)))
    return _finish(field, h, w)


# ===========================================================================
# 5. DARK DAMASK — half-drop ogee acanthus brocade.
# ===========================================================================
def _ogee_cell(res, cx, cy, rx, ry, rng):
    """One damask ogee motif: super-ellipse pointed cartouche + mirrored leaf veins."""
    X, Y = _grid(res, 0, res)
    u = (X - cx) / rx
    v = (Y - cy) / ry
    n = 2.6
    se = np.abs(u) ** n + np.abs(v) ** n           # super-ellipse
    shell = np.exp(-((se - 1.0) * 5.0) ** 2)       # cartouche outline
    # pointed top/bottom (ogee): pinch with |v|
    point = np.exp(-((np.abs(u) * (1 + 1.4 * np.abs(v)) - 0.55 * (1 - np.abs(v))) * 7) ** 2)
    # interior acanthus veins: mirrored arcs
    leaf = np.zeros_like(X)
    for s in (-1, 1):
        veinu = u
        arc = np.exp(-((np.abs(veinu) - (0.45 - 0.4 * np.abs(v))) * 12) ** 2) * (v * s > 0)
        leaf = np.maximum(leaf, arc)
    return np.maximum.reduce([shell, 0.7 * point, 0.85 * leaf]).astype(np.float32)


def dark_damask(h, w, seed, *, res=512):
    rng = _rng(seed)
    cols = int(rng.integers(3, 5))
    rows = int(rng.integers(4, 6))
    rx = res / cols * 0.5
    ry = res / rows * 0.5
    field = np.zeros((res, res), np.float32)
    for j in range(-1, rows + 1):
        drop = (res / cols) * 0.5 if (j % 2) else 0.0   # half-drop repeat
        for i in range(-1, cols + 2):
            cx = i * (res / cols) + drop
            cy = j * (res / rows) + (res / rows) * 0.5
            field = np.maximum(field, _ogee_cell(res, cx, cy, rx, ry, rng))
    # connective stem lattice between motifs (brocade ground)
    X, Y = _grid(res, 0, res)
    stem = np.abs(np.sin(X / res * cols * np.pi) * np.sin(Y / res * rows * np.pi))
    field = np.maximum(field, 0.35 * (stem ** 0.4))
    return _finish(field, h, w)


# ===========================================================================
# 6. BLACKLETTER GRID — broad-nib textura stroke geometry.
# ===========================================================================
def blackletter_grid(h, w, seed, *, res=512):
    rng = _rng(seed)
    canvas = np.zeros((res, res), np.float32)
    cols = int(rng.integers(7, 11))
    rows = int(rng.integers(7, 11))
    cw = res / cols
    ch = res / rows
    nib_ang = np.deg2rad(rng.uniform(35, 50))   # the gothic pen tilt
    # build a small oriented nib kernel (broad rectangular pen)
    ks = max(3, int(cw * 0.16))
    ky = max(2, ks // 2)
    nib = np.zeros((ks * 2 + 1, ks * 2 + 1), np.float32)
    nib[ks - 0:ks + 1, :] = 1.0
    M = cv2.getRotationMatrix2D((ks, ks), np.rad2deg(nib_ang), 1.0)
    nib = cv2.warpAffine(nib, M, (ks * 2 + 1, ks * 2 + 1))
    nib /= nib.sum() + 1e-6

    for j in range(rows):
        for i in range(cols):
            x0 = i * cw + cw * 0.22
            y0 = j * ch + ch * 0.18
            # textura: vertical strokes with diamond feet/heads + occasional diagonal
            strokes = int(rng.integers(2, 4))
            for s in range(strokes):
                xx = x0 + s * cw * 0.28
                top = (xx, y0)
                bot = (xx, y0 + ch * 0.64)
                t = np.linspace(0, 1, 16)
                pts = np.stack([np.full(16, xx), y0 + t * ch * 0.64], 1)
                for px, py in pts:
                    iy, ix = int(py), int(px)
                    if 0 <= iy < res and 0 <= ix < res:
                        canvas[iy, ix] = 1.0
            # diamond serif at base
            bx, by = int(x0), int(y0 + ch * 0.64)
            if 0 <= by < res and 0 <= bx < res:
                canvas[by, bx] = 1.0
            # a connecting hairline (the gothic 'feet')
            if rng.random() < 0.7:
                yy = int(y0 + ch * 0.32)
                if 0 <= yy < res:
                    canvas[yy, int(x0):int(min(res, x0 + cw * 0.6))] = 0.6
    field = cv2.filter2D(canvas, -1, nib)
    field = _norm(field)
    # crisp the nib edges
    field = np.clip(field * 1.6, 0, 1)
    # add the writing-grid ground rule so coverage is complete
    X, Y = _grid(res, 0, res)
    rule = 0.16 * (np.sin(Y / ch * np.pi) ** 8)
    field = np.maximum(field, rule)
    return _finish(field, h, w)


# ===========================================================================
# 7. OSSUARY LATTICE — interlocked bone/skull arcade.
# ===========================================================================
def _capsule(res, p0, p1, rad, _grid_xy=None):
    if _grid_xy is None:
        YY, XX = np.mgrid[0:res, 0:res].astype(np.float32)
    else:
        XX, YY = _grid_xy
    a = np.asarray(p0, np.float32); b = np.asarray(p1, np.float32)
    ab = b - a
    L2 = float(ab @ ab) + 1e-6
    t = np.clip(((XX - a[0]) * ab[0] + (YY - a[1]) * ab[1]) / L2, 0, 1)
    px = a[0] + t * ab[0]; py = a[1] + t * ab[1]
    d = np.hypot(XX - px, YY - py)
    return np.exp(-((d - rad) * 0.9) ** 2) + (d < rad) * np.exp(-(d / (rad + 1e-6)) ** 2) * 0.6


def ossuary_lattice(h, w, seed, *, res=384):
    rng = _rng(seed)
    field = np.zeros((res, res), np.float32)
    cols = int(rng.integers(4, 6))
    rows = int(rng.integers(5, 7))
    cw = res / cols; ch = res / rows
    rad = cw * 0.10
    YY, XX = np.mgrid[0:res, 0:res].astype(np.float32)   # shared grid (once)

    def ring(ex, ey, rr, soft):
        dd = np.hypot(XX - ex, YY - ey)
        return np.exp(-((dd - rr) * soft) ** 2)

    for j in range(rows):
        off = (cw * 0.5) if (j % 2) else 0.0    # brick stagger
        for i in range(-1, cols + 1):
            cx = i * cw + off + cw * 0.5
            cy = j * ch + ch * 0.5
            # crossed femurs (X of capsules) with bulbous epiphyses
            l = cw * 0.42
            field = np.maximum(field, _capsule(res, (cx - l, cy - l), (cx + l, cy + l), rad, (XX, YY)))
            field = np.maximum(field, _capsule(res, (cx - l, cy + l), (cx + l, cy - l), rad, (XX, YY)))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    field = np.maximum(field, ring(cx + sx * l, cy + sy * l, rad * 1.5, 0.8))
            # central skull-orbit pair (two dark sockets ringed bright)
            for sx in (-1, 1):
                field = np.maximum(field, ring(cx + sx * cw * 0.13, cy, rad * 1.3, 1.1))
    return _finish(field, h, w)


# ===========================================================================
# 8. SPIRE FRACTAL — recursive crocketed pinnacles (L-system gables).
# ===========================================================================
def spire_fractal(h, w, seed, *, res=512):
    rng = _rng(seed)
    polys = []

    def gable(cx, base_y, width, depth):
        if depth <= 0 or width < res * 0.012:
            return
        apex = base_y - width * 1.55          # tall pointed spire
        left = (cx - width / 2, base_y)
        right = (cx + width / 2, base_y)
        top = (cx, apex)
        polys.append(np.array([left, top], np.float32))
        polys.append(np.array([right, top], np.float32))
        polys.append(np.array([left, right], np.float32))
        # crockets: little hooked spurs up each rake
        ncr = 4
        for s in (-1, 1):
            for k in range(1, ncr + 1):
                t = k / (ncr + 1)
                px = cx + s * (width / 2) * (1 - t)
                py = base_y + (apex - base_y) * t
                hook = (px + s * width * 0.06, py - width * 0.04)
                polys.append(np.array([(px, py), hook], np.float32))
        # finial pinnacle on top + flanking sub-spires (the recursion)
        gable(cx, apex, width * 0.34, depth - 1)
        gable(cx - width * 0.42, base_y, width * 0.5, depth - 1)
        gable(cx + width * 0.42, base_y, width * 0.5, depth - 1)

    n = int(rng.integers(3, 5))
    for i in range(n):
        cx = (i + 0.5) / n * res
        gable(cx, res * 0.96, res / n * rng.uniform(0.85, 1.0), 4)
    field = _stroke_field(res, polys, width_px=res / 260.0)
    field = np.maximum(field, 0.6 * _stroke_field(res, polys, width_px=res / 480.0))
    # ground arcade so lower half isn't bare
    field = np.maximum(field, 0.2 * (np.sin(_grid(res)[0] * 40) ** 8))
    return _finish(field, h, w)


# ===========================================================================
# 9. QUATREFOIL TESSELLATION — lobed-circle tiling with cusps.
# ===========================================================================
def quatrefoil_tess(h, w, seed, *, res=600):
    rng = _rng(seed)
    cols = int(rng.integers(5, 8))
    rows = int(rng.integers(5, 8))
    lobes = int(rng.choice([3, 4, 4, 5]))     # trefoil / quatrefoil / cinquefoil
    cw = res / cols; ch = res / rows
    X, Y = _grid(res, 0, res)
    field = np.zeros((res, res), np.float32)
    twist = rng.uniform(0, np.pi)
    bw = cw * 0.06                            # crisp outline width in px
    for j in range(rows + 1):
        off = cw * 0.5 if (j % 2) else 0.0
        for i in range(-1, cols + 1):
            cx = i * cw + off
            cy = j * ch
            dx = X - cx; dy = Y - cy
            lr = np.hypot(dx, dy)
            la = np.arctan2(dy, dx)
            rad = (cw * 0.46) * (1.0 + 0.5 * np.cos(lobes * la + twist))
            outline = np.exp(-((lr - rad) / bw) ** 2)
            field = np.maximum(field, outline)
            # bright body fill of the foil (high-contrast positive lobes)
            field = np.maximum(field, 0.55 * (lr < rad) * np.exp(-((lr / (rad + 1e-6)) ** 4)))
    # interstitial cusps: the dark pinched diamonds between foils, ringed bright
    cusp = np.abs(np.sin(X / cw * np.pi + 0.5) * np.sin(Y / ch * np.pi + 0.5))
    field = np.maximum(field, 0.5 * (1 - cusp) ** 4)
    return _finish(field, h, w)


# ===========================================================================
# 10. BAROQUE ACANTHUS — recursive helical fronds (turtle-curve stamping).
# ===========================================================================
def baroque_acanthus(h, w, seed, *, res=512):
    rng = _rng(seed)
    polys = []

    def frond(x, y, ang, length, curl, depth):
        if depth <= 0 or length < res * 0.025:
            return
        n = 22
        pts = np.zeros((n, 2), np.float32)
        a = ang
        cx, cy = x, y
        for k in range(n):
            pts[k] = (cx, cy)
            a += curl * (1.0 / n)
            seglen = length / n
            cx += np.cos(a) * seglen
            cy += np.sin(a) * seglen
        polys.append(pts)
        # counter-curling leaflets along the spine
        for k in range(4, n - 2, 5):
            bx, by = pts[k]
            ba = np.arctan2(pts[k][1] - pts[k - 1][1], pts[k][0] - pts[k - 1][0])
            for s in (-1, 1):
                frond(bx, by, ba + s * 0.9, length * 0.42, -curl * s * 1.3, depth - 1)

    # seed roots on a jittered lattice so the whole canvas is covered
    g = 4
    for jj in range(g):
        for ii in range(g):
            x = (ii + rng.uniform(0.25, 0.75)) / g * res
            y = (jj + rng.uniform(0.25, 0.75)) / g * res
            ang = rng.uniform(0, TAU)
            frond(x, y, ang, res * rng.uniform(0.22, 0.32),
                  rng.uniform(2.2, 3.6) * (1 if rng.random() < 0.5 else -1), 3)
    field = _stroke_field(res, polys, width_px=res / 300.0)
    # scrolled acanthus ground so negative space still reads as carved leaf
    X, Y = _grid(res, 0, res)
    ground = 0.30 * np.abs(np.sin(X / res * 18 + np.sin(Y / res * 9)) *
                           np.cos(Y / res * 16 + np.cos(X / res * 11)))
    field = np.maximum(field, ground * (1 - field))
    field = np.maximum(field, 0.25 * _norm(cv2.GaussianBlur(field, (0, 0), 4.0)))
    return _finish(field, h, w)


# ===========================================================================
# 11. TRACERY WEB — randomized cusped-lancet plate tracery.
# ===========================================================================
def tracery_web(h, w, seed, *, res=512):
    rng = _rng(seed)
    npts = int(rng.integers(70, 96))
    # jittered-grid points => even coverage (no bare cells)
    g = int(np.ceil(np.sqrt(npts)))
    gx, gy = np.meshgrid(np.arange(g), np.arange(g))
    P = np.stack([gx.ravel(), gy.ravel()], 1).astype(np.float32)
    P = (P + rng.uniform(0.15, 0.85, P.shape)) / g
    P = P[:npts] * (res * 0.92) + res * 0.04
    tree = cKDTree(P)
    polys = []
    # connect each point to its k nearest -> a planar-ish web, then bow each link into
    # a pointed lancet arch (gothic ogive).
    seen = set()
    for i in range(npts):
        d, idx = tree.query(P[i], k=5)
        for j in idx[1:]:
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)
            p0, p1 = P[i], P[j]
            mid = 0.5 * (p0 + p1)
            v = p1 - p0
            nrm = np.array([-v[1], v[0]]); nrm /= (np.hypot(*nrm) + 1e-6)
            t = np.linspace(0, 1, 24)
            base = p0[None] * (1 - t)[:, None] + p1[None] * t[:, None]
            bow = np.sin(t * np.pi) * np.hypot(*v) * 0.18
            arc1 = base + nrm[None] * bow[:, None]
            arc2 = base - nrm[None] * bow[:, None]
            polys.append(arc1); polys.append(arc2)   # the two sides of a lancet
    # cusps: a small foil at each node
    for p in P:
        a = np.linspace(0, TAU, 24)
        rr = res * 0.018 * (1 + 0.5 * np.cos(3 * a))
        polys.append(np.stack([p[0] + rr * np.cos(a), p[1] + rr * np.sin(a)], 1))
    field = _stroke_field(res, polys, width_px=res / 320.0)
    # cusped diaper ground so every cell carries crisp structure (no bare lancets)
    X, Y = _grid(res, 0, res)
    cell = res / max(2, int(np.sqrt(npts)))
    diaper = np.abs(np.sin(X / cell * np.pi) * np.sin(Y / cell * np.pi))
    field = np.maximum(field, 0.32 * (1 - diaper) ** 2 * (1 - field))
    field = np.maximum(field, 0.28 * _norm(cv2.GaussianBlur(field, (0, 0), 3.0)))
    return _finish(field, h, w)


# ===========================================================================
# 12. WROUGHT SCREEN — interlaced over/under quatrefoil strapwork grille.
# ===========================================================================
def wrought_screen(h, w, seed, *, res=512):
    rng = _rng(seed)
    cols = int(rng.integers(4, 7))
    rows = int(rng.integers(4, 7))
    cw = res / cols; ch = res / rows
    X, Y = _grid(res, 0, res)
    # Two interlaced sinusoidal band families woven over/under (strapwork).
    fx = TAU * cols / res
    fy = TAU * rows / res
    band_a = np.sin(fx * X) * np.sin(fy * Y)              # warp ribbon family
    band_b = np.sin(fx * X + np.pi / 2) * np.sin(fy * Y - np.pi / 2)  # weft family
    # ribbon = narrow bright bar near each band's zero-cross ridge
    rib_a = np.exp(-((band_a) * 5.0) ** 2)
    rib_b = np.exp(-((band_b) * 5.0) ** 2)
    # over/under: a checker decides which ribbon is on top at each crossing
    checker = (np.floor(X / cw) + np.floor(Y / ch)) % 2
    field = np.where(checker > 0.5, np.maximum(rib_a, 0.4 * rib_b),
                     np.maximum(rib_b, 0.4 * rib_a))
    # punch quatrefoil piercings in every cell (pierced iron screen)
    cxg = (np.floor(X / cw) + 0.5) * cw
    cyg = (np.floor(Y / ch) + 0.5) * ch
    dx = X - cxg; dy = Y - cyg
    lr = np.hypot(dx, dy); la = np.arctan2(dy, dx)
    quat = (cw * 0.30) * (1 + 0.55 * np.cos(4 * la))
    pierce = np.exp(-((lr - quat) * 14.0) ** 2)
    field = np.maximum(field, 0.9 * pierce)
    # solid grille frame between cells
    frame = np.maximum(np.exp(-((X % cw) * 4) ** 2 / cw),
                       np.exp(-((Y % ch) * 4) ** 2 / ch))
    field = np.maximum(field, 0.5 * frame)
    return _finish(field, h, w)


# --------------------------------------------------------------------------- registry
ENGINES = {
    "rose_window": rose_window,
    "rib_vault": rib_vault,
    "iron_filigree": iron_filigree,
    "thorn_bramble": thorn_bramble,
    "dark_damask": dark_damask,
    "blackletter_grid": blackletter_grid,
    "ossuary_lattice": ossuary_lattice,
    "spire_fractal": spire_fractal,
    "quatrefoil_tess": quatrefoil_tess,
    "baroque_acanthus": baroque_acanthus,
    "tracery_web": tracery_web,
    "wrought_screen": wrought_screen,
}


# --------------------------------------------------------------------------- self-test
def _metrics(f):
    f = np.asarray(f, np.float32)
    fn = (f - f.min()) / (np.ptp(f) + 1e-9)
    blur = cv2.GaussianBlur(f, (0, 0), 8)
    fine = (f - blur).std() / (f.std() + 1e-6)
    # coverage over 8x8 grid
    H, W = f.shape
    gh, gw = H // 8, W // 8
    cov_hits = 0
    for j in range(8):
        for i in range(8):
            cell = f[j * gh:(j + 1) * gh, i * gw:(i + 1) * gw]
            if cell.std() > 0.035:
                cov_hits += 1
    coverage = cov_hits / 64.0
    sx = cv2.Sobel(fn, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(fn, cv2.CV_32F, 0, 1, ksize=3)
    g = np.hypot(sx, sy)
    g = (g - g.min()) / (np.ptp(g) + 1e-9)
    edge = float((g > 0.18).mean())
    return fine, coverage, edge


if __name__ == "__main__":
    import time
    h = w = 1024
    print(f"{'engine':<20}{'secs':>8}{'fine':>8}{'cov':>8}{'edge':>8}{'min':>7}{'max':>7}  status")
    print("-" * 80)
    allpass = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(h, w, 12345)
        secs = time.time() - t0
        f = np.asarray(f, np.float32)
        fine, cov, edge = _metrics(f)
        finite = np.isfinite(f).all()
        ok = (secs < 2.5) and (fine >= 0.12) and (cov >= 0.82) and (edge >= 0.12) \
             and finite and (f.min() >= -1e-4) and (f.max() <= 1 + 1e-4)
        allpass = allpass and ok
        print(f"{name:<20}{secs:>8.3f}{fine:>8.3f}{cov:>8.3f}{edge:>8.3f}"
              f"{f.min():>7.3f}{f.max():>7.3f}  {'OK' if ok else 'FAIL'}")
    print("-" * 80)
    print("ALL PASS" if allpass else "SOME FAILED")
