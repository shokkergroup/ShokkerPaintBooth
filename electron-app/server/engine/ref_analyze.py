"""REFERENCE ANALYZER (2026-10-02): read a livery REFERENCE PICTURE (a concept sheet, a side view, a photo, a flat wrap) and measure its DESIGN so the copilot can rebuild it on any car with the design graphics
(js/spb-pro-graphics.js): base colour, accent colours, big colour BANDS, concentric RINGS ("sonic arcs"), and thin STROKES (speed lines). Numbers, sponsors, logos, tires and windows are NOT design: they are filtered out.

Pipeline (all measured, no AI needed):
  1. views    - the caller gives boxes for the orthographic views (side / overhead); this module can snap a rough box to the car silhouette (rembg isnet, the model already cached on this PC; never downloads)
  2. coverage - per view, soft colour UNMIXING against (base, accent1, accent2): coverage maps that keep thin anti-aliased lines
  3. part space - a side view is warped to the part's (u front->rear, v roof-line->rocker) frame; fits happen there
  4. fits     - bands (wide blocks), rings (concentric-circle Hough on the thin strokes), strokes (long thin horizontal-ish components)
All geometry comes out in PART space (fractions), the same space add_graphic uses.
"""
from __future__ import annotations

import base64
import io
import math
from typing import Any

import cv2
import numpy as np
from PIL import Image

try:
    from sklearn.cluster import KMeans
except Exception:      # pragma: no cover
    KMeans = None


# ------------------------------------------------------------------ small helpers
def _decode_image(data_url_or_bytes) -> np.ndarray:
    if isinstance(data_url_or_bytes, (bytes, bytearray)):
        raw = bytes(data_url_or_bytes)
    else:
        s = str(data_url_or_bytes)
        raw = base64.b64decode(s.split(',', 1)[1] if s.startswith('data:') else s)
    im = Image.open(io.BytesIO(raw))
    im.load()
    if im.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', im.size, (255, 255, 255))
        im = im.convert('RGBA')
        bg.paste(im, mask=im.split()[3])
        im = bg
    return np.array(im.convert('RGB'))


def _hex(rgb) -> str:
    r, g, b = [int(max(0, min(255, round(float(v))))) for v in rgb]
    return '#%02x%02x%02x' % (r, g, b)


def _lab(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)


def _lab2rgb(c) -> np.ndarray:
    return cv2.cvtColor(np.uint8([[np.clip(c, 0, 255)]]), cv2.COLOR_LAB2RGB)[0, 0]


def to_py(o):
    """numpy scalars / arrays -> plain python (JSON-safe)."""
    if isinstance(o, dict):
        return {str(k): to_py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def snap_box(img: np.ndarray, box, grow: float = 0.06):
    """Tighten a rough (x0,y0,x1,y1) box to the car silhouette inside it. Falls back to the box itself."""
    try:
        from rembg import new_session, remove
        h, w = img.shape[:2]
        x0, y0, x1, y1 = box
        gx, gy = int((x1 - x0) * grow), int((y1 - y0) * grow)
        X0, Y0, X1, Y1 = max(0, x0 - gx), max(0, y0 - gy), min(w, x1 + gx), min(h, y1 + gy)
        sess = new_session('isnet-general-use')        # cached locally; naming it explicitly stops rembg from fetching another model
        m = np.array(remove(Image.fromarray(img[Y0:Y1, X0:X1]), session=sess, only_mask=True)) > 128
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        if n < 2:
            return tuple(box)
        i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        bx, by, bw, bh = st[i, :4]
        return (int(X0 + bx), int(Y0 + by), int(X0 + bx + bw), int(Y0 + by + bh))
    except Exception:
        return tuple(box)


# ------------------------------------------------------------------ palette / base / accents
def palette(img: np.ndarray, boxes: list, k_accents: int = 3) -> dict:
    """Base colour (the car body), accent colours (strong chroma), dark colour. Computed inside the view boxes only."""
    pix = []
    for (x0, y0, x1, y1) in boxes:
        pix.append(img[y0:y1, x0:x1].reshape(-1, 3))
    px = np.concatenate(pix, 0)
    lab = _lab(px.reshape(-1, 1, 3)).reshape(-1, 3)
    L = lab[:, 0] * 100 / 255
    C = np.hypot(lab[:, 1] - 128, lab[:, 2] - 128)
    body = (L > 62) & (C < 16)
    base_rgb = np.median(px[body], 0) if body.sum() > 200 else np.median(px, 0)
    # the car body may itself be coloured: when bright low-chroma pixels are rare, take the most common mid colour
    if body.sum() < 0.12 * len(px):
        q = (px // 24).astype(np.int32)
        key = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
        u, cnt = np.unique(key, return_counts=True)
        top = u[np.argmax(cnt)]
        base_rgb = np.median(px[key == top], 0)
    sat = (C > 58) & (L > 40)
    accents = []
    if sat.sum() > 300 and KMeans is not None:
        sample = lab[sat][:: max(1, int(sat.sum() // 20000))]
        km = KMeans(n_clusters=min(k_accents + 1, max(2, len(sample) // 50)), n_init=4, random_state=3).fit(sample)
        lbl = km.predict(lab[sat])
        order = np.argsort(-np.bincount(lbl, minlength=len(km.cluster_centers_)))
        for ci in order:
            share = float((lbl == ci).sum()) / max(1, len(px))
            rgb = _lab2rgb(km.cluster_centers_[ci])
            if share < 0.002:
                continue
            if any(np.linalg.norm(rgb.astype(float) - np.array(a['rgb'])) < 48 for a in accents):
                continue
            accents.append({'hex': _hex(rgb), 'rgb': [int(v) for v in rgb], 'share_pct': round(100 * share, 2)})
    dark_share = float((L < 24).sum()) / max(1, len(px))
    return {'base': {'hex': _hex(base_rgb), 'rgb': [int(v) for v in base_rgb]}, 'accents': accents[:k_accents], 'dark_share_pct': round(100 * dark_share, 1)}


# ------------------------------------------------------------------ coverage by unmixing
def coverage(view_rgb: np.ndarray, base_rgb, accent_rgbs: list):
    """soft coverage per accent (0..1) + a dark-furniture mask. base + accents are the endmembers."""
    ends = [np.array(base_rgb, np.float32)] + [np.array(a, np.float32) for a in accent_rgbs]
    E = np.stack([_lab(np.uint8([[e]]))[0, 0] for e in ends], 1)             # 3 x n
    lab = _lab(view_rgb).reshape(-1, 3)
    # least squares with a sum-to-one row (weighted) then clamp: cheap non-negative unmixing
    A = np.vstack([E, 40.0 * np.ones((1, E.shape[1]), np.float32)])
    pinv = np.linalg.pinv(A)
    b = np.hstack([lab, 40.0 * np.ones((len(lab), 1), np.float32)])
    w = np.clip(b @ pinv.T, 0, 1.2)
    w = w / (w.sum(1, keepdims=True) + 1e-6)
    Lv = lab[:, 0] * 100 / 255
    dark = (Lv < 36).reshape(view_rgb.shape[:2])
    cov = w[:, 1:].reshape(view_rgb.shape[0], view_rgb.shape[1], len(accent_rgbs)).copy()
    cov[dark] = 0
    return cov, dark


# ------------------------------------------------------------------ rings (concentric circle Hough on thin strokes)
def fit_rings(mask: np.ndarray, cov_cols: list, L: float, H: float, max_r: float = 0.95) -> dict | None:
    """mask: bool image (H x L) of thin strokes in part pixels. Finds the centre whose radial profile is the most 'ringy', then reads the rings off that profile."""
    ys, xs = np.nonzero(mask)
    if len(xs) < 400:
        return None
    step = max(1, int(len(xs) // 14000))
    xs, ys = xs[::step].astype(np.float32), ys[::step].astype(np.float32)
    nb = int(1.3 * H / 2)

    def profile(cx, cy, bw=2.0):
        r = np.hypot(xs - cx, ys - cy)
        idx = (r / bw).astype(np.int32)
        idx = idx[idx < nb]
        return np.bincount(idx, minlength=nb).astype(np.float32)

    def score(cx, cy):
        h = profile(cx, cy)
        sm = cv2.GaussianBlur(h.reshape(1, -1), (0, 0), 4).ravel()
        lim = int(max_r * H / 2)
        d = (h - sm)[:lim]
        return float((d * d).sum()) / (float(h[:lim].sum()) + 1.0)

    best = (-1.0, (0.4, 0.6))
    for cu in np.linspace(0.04, 0.96, 24):
        for cv_ in np.linspace(0.0, 1.1, 20):
            sc = score(cu * L, cv_ * H)
            if sc > best[0]:
                best = (sc, (cu, cv_))
    c0 = best[1]
    for dcu in np.linspace(-0.04, 0.04, 9):
        for dcv in np.linspace(-0.06, 0.06, 9):
            sc = score((c0[0] + dcu) * L, (c0[1] + dcv) * H)
            if sc > best[0]:
                best = (sc, (c0[0] + dcu, c0[1] + dcv))
    cu, cv_ = best[1]
    cx, cy = cu * L, cv_ * H
    r = np.hypot(xs - cx, ys - cy)
    h, _ = np.histogram(r, bins=np.arange(0, 1.3 * H, 1.0))
    hs = cv2.GaussianBlur(h.astype(np.float32).reshape(1, -1), (0, 0), 1.6).ravel()
    base = cv2.GaussianBlur(h.astype(np.float32).reshape(1, -1), (0, 0), 14.0).ravel()
    ex = hs - base
    pos = ex[ex > 0]
    if not len(pos):
        return None
    thr = max(4.0, 0.16 * float(np.percentile(pos, 92)))
    lim = int(max_r * H)
    peaks = []
    i = 3
    while i < min(len(ex) - 3, lim):
        if ex[i] > thr and ex[i] >= ex[i - 1] and ex[i] >= ex[i + 1]:
            lo = i
            while lo > 0 and ex[lo] > 0.4 * ex[i]:
                lo -= 1
            hi = i
            while hi < len(ex) - 1 and ex[hi] > 0.4 * ex[i]:
                hi += 1
            peaks.append((float(i), float(hi - lo), float(ex[i])))
            i = hi + 1
        else:
            i += 1
    if len(peaks) < 3:
        return None
    ang_all = np.arctan2(ys - cy, xs - cx)
    rings = []
    for (rp, wd, st) in peaks:
        sel = np.abs(r - rp) < max(2.0, wd * 0.6)
        if sel.sum() < 25:
            continue
        a = ang_all[sel]
        mx, my = float(np.cos(a).mean()), float(np.sin(a).mean())
        face = math.atan2(my, mx)
        # angular extent: the arc length actually covered, from the spread of the angles around the mean direction
        dev = np.abs(((a - face + np.pi) % (2 * np.pi)) - np.pi)
        extent = float(np.degrees(2 * np.percentile(dev, 95)))
        ci = 0
        if cov_cols:
            sx, sy = xs[sel][:300].astype(int), ys[sel][:300].astype(int)
            vals = [float(c[np.clip(sy, 0, H - 1), np.clip(sx, 0, L - 1)].mean()) for c in cov_cols]
            ci = int(np.argmax(vals))
        rings.append({'r': rp / H, 'w': max(2.0, wd) / H, 'colour_idx': ci, 'face_deg': math.degrees(face), 'span_deg': min(320.0, max(40.0, extent + 12))})
    if len(rings) < 3:
        return None
    faces = np.array([math.radians(x['face_deg']) for x in rings])
    face = math.degrees(math.atan2(np.sin(faces).mean(), np.cos(faces).mean()))
    f = ((face + 180) % 360) - 180
    facing = 'front' if abs(f) > 125 else ('rear' if abs(f) < 55 else ('down' if f > 0 else 'up'))
    return {'cu': round(float(cu), 3), 'cv': round(float(cv_), 3), 'score': round(best[0], 2), 'facing': facing, 'face_deg': round(face, 1), 'rings': rings,
            'n': len(rings), 'span': round(float(np.median([x['span_deg'] for x in rings])), 0)}


# ------------------------------------------------------------------ strokes (long thin horizontal-ish components)
def fit_strokes(mask: np.ndarray, cov_cols: list, L: float, H: float, exclude: np.ndarray | None = None, min_len: float = 0.03) -> list:
    m = (mask & ~exclude) if exclude is not None else mask.copy()
    k = max(9, int(min_len * L))
    op = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1)))
    op = cv2.dilate(op, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    n, lab, st, cen = cv2.connectedComponentsWithStats(op, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if w < min_len * L or h > 0.08 * H:           # keep long, thin, roughly horizontal
            continue
        comp = lab == i
        cols_idx = 0
        if cov_cols:
            vals = [float(c[comp].mean()) for c in cov_cols]
            cols_idx = int(np.argmax(vals))
        ys, xs = np.nonzero(comp)
        # thickness at the start vs the end (taper)
        thick = []
        for xx in (x + int(0.1 * w), x + int(0.9 * w)):
            colm = ys[xs == min(xx, xs.max())]
            thick.append(float(colm.max() - colm.min() + 1) if len(colm) else 1.0)
        out.append({'u0': x / L, 'u1': (x + w) / L, 'v': (y + h / 2.0) / H, 'w0': thick[0] / H, 'w1': thick[1] / H, 'colour_idx': cols_idx})
    out.sort(key=lambda s: s['v'])
    return out[:44]


# ------------------------------------------------------------------ bands (wide solid blocks across the panel)
def fit_bands(cov_cols: list, L: float, H: float, thr: float = 0.5) -> list:
    bands = []
    for ci, c in enumerate(cov_cols):
        m = (c > thr).astype(np.uint8)
        k = max(15, int(0.12 * L))
        op = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, max(3, int(0.03 * H)))))
        prof = op.mean(1)                       # per row: share of the length covered
        inside = prof > 0.55
        v = 0
        while v < len(prof):
            if inside[v]:
                w = v
                while w < len(prof) and inside[w]:
                    w += 1
                if (w - v) / H > 0.03:
                    bands.append({'from': v / H, 'to': w / H, 'colour_idx': ci, 'coverage': float(prof[v:w].mean())})
                v = w
            else:
                v += 1
    return bands


# ------------------------------------------------------------------ part-space side view
def warp_to_part(view_rgb: np.ndarray, L: int, H: int, rot180: bool = False) -> np.ndarray:
    im = cv2.resize(view_rgb, (int(L), int(H)), interpolation=cv2.INTER_CUBIC)
    return im[::-1, ::-1].copy() if rot180 else im


def analyze_side(img: np.ndarray, box, part_px: tuple, pal: dict | None = None, nose: str = 'left') -> dict:
    """box: side view (x0,y0,x1,y1) in the picture (nose left = front at left, roof on top). part_px: (L, H) of the part in sheet pixels."""
    L, H = int(part_px[0]), int(part_px[1])
    x0, y0, x1, y1 = box
    view = img[y0:y1, x0:x1]
    pal = pal or palette(img, [box])
    if nose == 'right':
        view = view[:, ::-1].copy()          # part space is nose-left: a nose-right view is mirrored
    accents = [a['rgb'] for a in pal['accents'][:3]]
    cov, dark = coverage(view, pal['base']['rgb'], accents)
    cov = [cv2.resize(cov[..., i], (L, H), interpolation=cv2.INTER_CUBIC) for i in range(cov.shape[2])]
    dk = cv2.resize(dark.astype(np.float32), (L, H), interpolation=cv2.INTER_LINEAR) > 0.5
    # furniture: big dark blobs (tires, windows) and a margin
    dku = dk.astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(dku, 8)
    big = np.zeros_like(dku)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 0.0012 * L * H:
            big[lab == i] = 1
    furn = cv2.dilate(big, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))) > 0
    thin = []
    thick_mask = np.zeros((H, L), bool)
    for c in cov:
        m = (cv2.GaussianBlur(c, (0, 0), 1.2) > 0.30).astype(np.uint8)
        dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        core = (dist > 0.022 * H).astype(np.uint8)                       # stroke core thicker than a line: number / logo / block
        core = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.05 * H) | 1, int(0.05 * H) | 1)))
        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(m, 8)
        blobs = np.zeros_like(m)
        for i in range(1, n2):
            x, y, w, h, a = st2[i]
            if a < 80:
                continue
            comp = lab2 == i
            if (core[comp] > 0).mean() > 0.30 and w < 0.2 * L and h < 0.5 * H:        # compact thick object: a number, a logo, a hot dog, a rocket
                blobs[comp] = 1
        thick_mask |= cv2.dilate(blobs, np.ones((9, 9), np.uint8)) > 0
        thin.append((m > 0))
    thin = [t & ~furn & ~thick_mask for t in thin]
    union = np.zeros((H, L), bool)
    for t in thin:
        union |= t
    rings = fit_rings(union, cov, L, H)
    excl = None
    if rings:
        yy, xx = np.mgrid[0:H, 0:L]
        rr = np.hypot(xx - rings['cu'] * L, yy - rings['cv'] * H)
        excl = rr < (max(x['r'] for x in rings['rings']) + 0.05) * H
    strokes = fit_strokes(union, cov, L, H, exclude=excl)
    bands = fit_bands(cov, L, H)
    return to_py({'rings': rings, 'strokes': strokes, 'bands': bands, 'base': pal['base'], 'accents': pal['accents'],
                  'cover_pct': [round(100 * float((t & ~furn).mean()), 2) for t in thin], 'size': [L, H]})


# ------------------------------------------------------------------ suggestions: analysis -> tool calls the copilot (or the offline matcher) can run as they are
def _regular_rings(rs: list) -> list:
    """rs: rings sorted by radius. Fill gaps in an evenly spaced series (a faint ring the detector missed) and drop outliers far from the series."""
    if len(rs) < 3:
        return rs
    r = [x['r'] for x in rs]
    gaps = np.diff(r)
    med = float(np.median(gaps[gaps > 0.01])) if (gaps > 0.01).any() else 0.05
    out = []
    for i, x in enumerate(rs):
        out.append(x)
        if i + 1 < len(rs):
            g = rs[i + 1]['r'] - x['r']
            k = int(round(g / med)) - 1
            if 1 <= k <= 3 and g < 4.2 * med:
                for j in range(1, k + 1):
                    out.append({'r': x['r'] + g * j / (k + 1), 'w': (x['w'] + rs[i + 1]['w']) / 2, 'colour_idx': (x['colour_idx'] + j) % 2, 'span_deg': (x['span_deg'] + rs[i + 1]['span_deg']) / 2, 'filled': True})
    return out


def suggest(an: dict, finish: str = 'base::gloss', gain: float = 1.5) -> list:
    steps = []
    acc = [a['hex'] for a in an.get('accents', [])]
    steps.append({'tool': 'apply_scheme', 'args': {'elements': [{'id': 'base', 'colour': an['base']['hex']}], 'paint_finish': finish}, 'why': 'the body colour of the reference'})
    for bnd in an.get('bands', [])[:3]:
        if bnd['colour_idx'] < len(acc):
            steps.append({'tool': 'apply_scheme', 'args': {'elements': [{'id': 'side_stripe', 'colour': acc[bnd['colour_idx']], 'from': round(bnd['from'], 3), 'to': round(bnd['to'], 3)}], 'paint_finish': finish}, 'why': 'a wide colour band along the sides'})
    r = an.get('rings')
    cols = acc[:3] if acc else ['#ff6a13']
    if r and r.get('rings'):
        rs = _regular_rings(sorted(r['rings'], key=lambda x: x['r']))
        steps.append({'tool': 'add_graphic', 'args': {'kind': 'rings', 'colours': cols, 'cu': r['cu'], 'cv': r['cv'], 'facing': r['facing'], 'span': r['span'],
                                                        'radii': [round(x['r'], 3) for x in rs], 'widths': [round(min(0.07, x['w'] * gain), 3) for x in rs], 'seq': [x['colour_idx'] for x in rs], 'spans': [round(x['span_deg']) for x in rs], 'paint_finish': finish}, 'why': 'concentric arcs measured on the reference'})
    st = an.get('strokes') or []
    if st:
        items = [{'u0': round(x['u0'], 3), 'u1': round(x['u1'], 3), 'v': round(x['v'], 3), 'w0': round(min(0.05, x['w0'] * gain), 4), 'w1': round(min(0.05, x['w1'] * gain), 4), 'c': x['colour_idx']} for x in st]
        steps.append({'tool': 'add_graphic', 'args': {'kind': 'strokes', 'colours': cols, 'items': items, 'paint_finish': finish}, 'why': 'speed lines / streaks measured on the reference'})
        if len(st) < 26:        # the detector only finds the clearest streaks: add more in the SAME region and style so the density matches
            u0 = float(np.percentile([x['u0'] for x in st], 10)); u1 = float(np.percentile([x['u1'] for x in st], 90)); v0 = float(min(x['v'] for x in st)); v1 = float(max(x['v'] for x in st))
            wm = float(np.median([x['w0'] for x in st])) * gain
            steps.append({'tool': 'add_graphic', 'args': {'kind': 'speed_lines', 'colours': cols, 'u0': round(u0, 3), 'u1': round(max(u0 + 0.1, u1 - 0.1), 3), 'v0': round(v0, 3), 'v1': round(v1, 3), 'n': 26 - len(st), 'wmin': round(wm * 0.5, 4), 'wmax': round(min(0.04, wm * 1.4), 4), 'lenmin': 0.08, 'lenmax': 0.32, 'taper': 'tail', 'seed': 7, 'paint_finish': finish}, 'why': 'more streaks in the same region and style'})
    return steps


def analyze(img: np.ndarray, views: list, part_px: tuple, snap: bool = False) -> dict:
    """views: [{'kind': 'side', 'nose': 'left'|'right', 'box': (x0,y0,x1,y1) in image px}]. Uses the first side view for the fits (both sides get the same car-relative design)."""
    sides = [v for v in views if v.get('kind') == 'side']
    if not sides:
        return {'error': 'no side view was given: the analyzer needs at least one side view box'}
    v = sides[0]
    box = tuple(int(x) for x in v['box'])
    if snap:
        box = snap_box(img, box)
    pal = palette(img, [box])
    an = analyze_side(img, box, part_px, pal, nose=v.get('nose', 'left'))
    an['box'] = list(box)
    an['nose'] = v.get('nose', 'left')
    an['suggest'] = suggest(an)
    return to_py(an)
