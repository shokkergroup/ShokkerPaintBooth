"""ASTRA R2 generator kit — fast 2048 field primitives for the ASTRA rebuild.

SPB-105 / ASTRA-R2, 2026-09-27 (Claude). Owner on R1: "surprisingly AWFUL";
asked for finishes that are UNIQUE, JUMP OFF THE SCREEN, do what the name says,
and are as intricate as possible. R1 drew every finish with one grammar (sparse
cv2 glyph stamps on a flat ground). R2 gives each finish its own construction
built from these primitives; this module holds NO finish-specific decisions.

Everything works at the native 2048 canvas in float32. Budget: a finish build
must stay well under the 2-3 s owner render budget, so every primitive here is
an O(N) numpy/OpenCV pass (no per-pixel Python loops, no iterative PDE solves).
"""
import cv2
import numpy as np

N = 2048
TAU = np.float32(2 * np.pi)
_XY = {}


def xy(n=N):
    """Pixel-centre coordinate grids (float32), cached per size."""
    if n not in _XY:
        y, x = np.mgrid[:n, :n].astype(np.float32)
        x += .5; y += .5
        x.setflags(write=False); y.setflags(write=False)
        _XY[n] = (x, y)
    return _XY[n]


def rng(seed):
    return np.random.default_rng(int(seed) & 0x7fffffff)


_HLUT = np.random.default_rng(0xA57A2).random(1 << 20).astype(np.float32)
_HP = (-1640531535, 1103515245, -2048144789, 668265263, 374761393, -1028477379)


def hash01(*keys):
    """Deterministic per-integer hash in [0,1).

    Fast path (ASTRA-R2 perf pass): when the keys are integer arrays whose
    combined range fits 2^22, hash the RANGE once and gather (about 4x cheaper
    than mixing every pixel). Otherwise: int32 xor-multiply mix into a 2^20
    random lookup table."""
    arrs = [np.asarray(k) for k in keys]
    big = [a for a in arrs if a.ndim > 0 and a.size > 65536]
    if big:
        ints = []
        for a in arrs:
            if a.dtype.kind == 'f':
                a = np.floor(a)
            ints.append(a)
        lo = [int(a.min()) if a.ndim else int(a) for a in ints]
        hi = [int(a.max()) if a.ndim else int(a) for a in ints]
        span = 1
        for l_, h_ in zip(lo, hi):
            span *= (h_ - l_ + 1)
        if span <= (1 << 22):
            idx = None; mul = 1; grids = []
            for a, l_, h_ in zip(ints, lo, hi):
                grids.append((l_, h_, mul))
                mul *= (h_ - l_ + 1)
            # table over the whole combined range, then one gather
            axes = [np.arange(l_, h_ + 1) for l_, h_, _ in grids]
            mesh = np.meshgrid(*axes, indexing='ij') if len(axes) > 1 else axes
            table = _hash_mix([m.ravel(order='F') for m in mesh]).reshape(-1)
            for a, (l_, h_, m_) in zip(ints, grids):
                if a.ndim == 0:
                    term = np.int64((int(a) - l_) * m_)
                else:
                    term = (a.astype(np.int64) - l_) * m_ if m_ != 1 else (a.astype(np.int64) - l_)
                idx = term if idx is None else idx + term
            return table[idx]
    return _hash_mix(arrs)


# ------------------------------------------------------------------ noise
def noise(seed, cells, n=N, interp=cv2.INTER_CUBIC):
    """Smooth value noise with feature size n/cells, unit-ish std, zero mean."""
    cells = max(2, int(cells))
    g = rng(seed).standard_normal((cells + 3, cells + 3)).astype(np.float32)
    big = cv2.resize(g, (n * (cells + 3) // cells, n * (cells + 3) // cells), interpolation=interp)
    o = n // cells
    out = big[o:o + n, o:o + n]
    return np.ascontiguousarray(out)


def fbm(seed, cells=(4, 8, 16, 32), gain=.55, n=N):
    """Fractal sum of value-noise octaves. Octaves with <= 48 cells are summed
    on a 512 grid and upsampled once (identical character, ~40% cheaper)."""
    lo_n = 512 if n > 512 else n
    lo = np.zeros((lo_n, lo_n), np.float32); acc = None
    amp = 1.; tot = 0.
    for i, c in enumerate(cells):
        if c <= 48 and lo_n < n:
            nz = noise(seed * 7 + i * 131, c, lo_n)
            nz *= np.float32(amp); lo += nz
        else:
            nz = noise(seed * 7 + i * 131, c, n)
            if amp != 1.:
                nz *= np.float32(amp)
            acc = nz if acc is None else (acc.__iadd__(nz))
        tot += amp; amp *= gain
    if lo_n < n:
        up = cv2.resize(lo, (n, n), interpolation=cv2.INTER_CUBIC)
        acc = up if acc is None else acc.__iadd__(up)
    else:
        acc = lo if acc is None else acc.__iadd__(lo)
    acc *= np.float32(1. / tot)
    return acc


def ridged(seed, cells=(8, 16, 32), gain=.6, n=N):
    acc = np.zeros((n, n), np.float32); amp = 1.; tot = 0.
    for i, c in enumerate(cells):
        acc += (1 - np.abs(noise(seed * 5 + i * 77, c, n))) * amp
        tot += amp; amp *= gain
    return acc / np.float32(tot)


def unit(a, lo=1., hi=99.):
    """Robust percentile normalisation to [0,1]."""
    s = a[::7, ::7]
    p0, p1 = np.percentile(s, [lo, hi])
    out = np.subtract(a, np.float32(p0), dtype=np.float32)
    out *= np.float32(1. / max(1e-6, p1 - p0))
    return np.clip(out, 0, 1, out=out)


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), float(s)) if s > 0 else a


def remap(img, mx, my, border=cv2.BORDER_REFLECT):
    return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=border)


def warp(seed, amp, cells=6, n=N):
    """Domain-warped coordinates (x', y')."""
    x, y = xy(n)
    return (x + noise(seed, cells, n) * amp).astype(np.float32), (y + noise(seed + 1, cells, n) * amp).astype(np.float32)


def smooth(d, w=1.):
    """Antialiased coverage from a signed distance (negative inside)."""
    out = np.multiply(d, np.float32(-1. / w), dtype=np.float32)
    out += np.float32(.5)
    return np.clip(out, 0, 1, out=out)


def near(d, w, aa=1.):
    """Coverage of the band d < w (e.g. distance-to-edge under a width)."""
    out = np.subtract(np.float32(w) + np.float32(.5 * aa), d, dtype=np.float32)
    if aa != 1.:
        out *= np.float32(1. / aa)
    return np.clip(out, 0, 1, out=out)


def iso(f, spacing, width=1., phase=0.):
    """Constant-pixel-width contour lines of field f every `spacing` units.
    Returns (line coverage, level index, fraction inside the level)."""
    s = f / np.float32(spacing) + np.float32(phase)
    q = np.floor(s)
    fr = s - q
    gx, gy = grad(f)
    g = np.sqrt(gx * gx + gy * gy) / np.float32(spacing)
    d = np.minimum(fr, 1 - fr) / np.maximum(g, np.float32(.02))
    return near(d, width * .5, 1.), q.astype(np.int32), fr.astype(np.float32)


def sstep(a, b, x):
    t = np.subtract(x, np.float32(a), dtype=np.float32)
    t *= np.float32(1. / (b - a))
    np.clip(t, 0, 1, out=t)
    s = t * t
    t *= np.float32(-2.)
    t += np.float32(3.)
    t *= s
    return t


def grad(h):
    h = np.asarray(h, np.float32)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) * .125
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) * .125
    return gx, gy


def relief(h, k=1., light=(-.6, -.8)):
    """Lambert-like emboss term (~0 on flats) from a height field in px units."""
    gx, gy = grad(h)
    gx *= np.float32(k); gy *= np.float32(k)
    nz = gx * gx
    nz += gy * gy
    nz += np.float32(1.)
    np.sqrt(nz, out=nz)
    gx *= np.float32(-light[0]); gy *= np.float32(-light[1])
    gx += gy
    gx /= nz
    return gx


# --------------------------------------------------------------- cells/sites
def sites(seed, pitch, jitter=.85, hexa=True, n=N, margin=0):
    """Jittered (optionally hex-staggered) site list, shape (k,2) as x,y."""
    r = rng(seed)
    ny = int(np.ceil(n / (pitch * (.866 if hexa else 1)))) + 2
    nx = int(np.ceil(n / pitch)) + 2
    iy, ix = np.mgrid[-1:ny - 1, -1:nx - 1]
    px = (ix + (.5 * (iy % 2) if hexa else 0)) * pitch
    py = iy * pitch * (.866 if hexa else 1)
    px = px + (r.random(px.shape) - .5) * jitter * pitch
    py = py + (r.random(py.shape) - .5) * jitter * pitch
    p = np.stack([px.ravel(), py.ravel()], 1).astype(np.float32)
    keep = (p[:, 0] >= -margin) & (p[:, 0] < n + margin) & (p[:, 1] >= -margin) & (p[:, 1] < n + margin)
    return p[keep]


def poisson_sites(seed, count, n=N):
    return (rng(seed).random((int(count), 2)) * n).astype(np.float32)


def voronoi(points, n=N, precise=False):
    """Nearest-site labels + distance via OpenCV's labelled distance transform.

    Returns (label int32 -> index into `points` (deduplicated order), d1 float32,
    pts (the deduplicated in-canvas points actually used)).
    """
    p = np.round(np.asarray(points)).astype(np.int64)
    ok = (p[:, 0] >= 0) & (p[:, 0] < n) & (p[:, 1] >= 0) & (p[:, 1] < n)
    p = p[ok]
    lin = np.unique(p[:, 1] * n + p[:, 0])          # raster order == OpenCV label order
    src = np.full((n, n), 255, np.uint8)
    src.flat[lin] = 0
    d, lab = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, cv2.DIST_MASK_PRECISE if precise else 5,
                                             labelType=cv2.DIST_LABEL_PIXEL)
    pts = np.stack([lin % n, lin // n], 1).astype(np.float32)
    return (lab - 1).astype(np.int32), d.astype(np.float32), pts


def boundaries(labels):
    """uint8 mask of pixels whose 4-neighbourhood crosses a label change."""
    l = labels
    e = np.zeros(l.shape, bool)
    e[:, 1:] |= l[:, 1:] != l[:, :-1]
    e[1:, :] |= l[1:, :] != l[:-1, :]
    return e


def edge_distance(labels):
    """Distance (px) from each pixel to the nearest cell boundary."""
    e = boundaries(labels)
    return cv2.distanceTransform((~e).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)


def cell_local(labels, pts, x=None, y=None):
    """Offset of every pixel from its own site: (dx, dy)."""
    if x is None:
        x, y = xy(labels.shape[0])
    return x - pts[labels, 0], y - pts[labels, 1]


def grid_cells(pitch, seed=0, stagger=0., n=N, ox=0., oy=0.):
    """Regular (optionally row-staggered) grid: ix, iy, local u, v (px, centred), hash."""
    x, y = xy(n)
    yy = y + oy
    iy = np.floor(yy / pitch).astype(np.int32)
    xx = x + ox + (iy % 2) * pitch * stagger
    ix = np.floor(xx / pitch).astype(np.int32)
    u = xx - (ix + .5) * pitch
    v = yy - (iy + .5) * pitch
    return ix, iy, u.astype(np.float32), v.astype(np.float32), hash01(ix, iy, seed)


def rot(u, v, a):
    c, s = np.cos(a).astype(np.float32), np.sin(a).astype(np.float32)
    return u * c + v * s, -u * s + v * c


# ---------------------------------------------------------------- colour
def hexrgb(*hexes):
    return np.array([[int(h.lstrip('#')[i:i + 2], 16) / 255. for i in (0, 2, 4)] for h in hexes], np.float32)


def ramp(t, stops, pos=None):
    """Gradient-map a [0,1] field through hex colour stops -> HxWx3."""
    cols = hexrgb(*stops)
    pos = np.linspace(0, 1, len(stops)) if pos is None else np.asarray(pos, np.float32)
    lutx = np.linspace(0, 1, 1024, dtype=np.float32)
    lut = np.stack([np.interp(lutx, pos, cols[:, c]) for c in range(3)], 1).astype(np.float32)
    idx = np.multiply(t, np.float32(1023.), dtype=np.float32).astype(np.int32)
    np.clip(idx, 0, 1023, out=idx)
    return lut[idx]


def cospal(t, a, b, c, d):
    """Inigo Quilez cosine palette a + b*cos(2pi(c*t+d)) via a 4096-entry LUT
    spanning the field's actual range (one gather instead of 3 full cosines)."""
    t = np.asarray(t, np.float32)
    lo, hi = float(t[::5, ::5].min()) - 1e-3, float(t[::5, ::5].max()) + 1e-3
    lo = min(lo, float(t.min())); hi = max(hi, float(t.max()))
    xs = np.linspace(lo, hi, 4096, dtype=np.float32)[:, None]
    lut = np.clip(np.float32(a) + np.float32(b) * np.cos(TAU * (np.float32(c) * xs + np.float32(d))), 0, 1).astype(np.float32)
    idx = np.subtract(t, np.float32(lo), dtype=np.float32)
    idx *= np.float32(4095. / max(hi - lo, 1e-6))
    idx = idx.astype(np.int32)
    np.clip(idx, 0, 4095, out=idx)
    return lut[idx]


def thin_film(t, sat=1., bright=.62):
    """Interference-like spectral colour for an optical-thickness field t."""
    c = cospal(t, (bright, bright, bright), (.38 * sat, .38 * sat, .38 * sat), (1., 1., 1.), (0., .33, .67))
    return c


def mix(a, b, t):
    """a*(1-t) + b*t with at most one full-size allocation."""
    t = np.asarray(t, np.float32)
    if t.ndim == 2 and not (np.ndim(a) == 2 and np.ndim(b) == 2):
        t = t[..., None]
    out = np.subtract(b, a, dtype=np.float32)
    if out.shape != np.broadcast_shapes(np.shape(a), np.shape(b), t.shape):
        out = np.broadcast_to(out, np.broadcast_shapes(np.shape(a), np.shape(b), t.shape)).copy()
    out *= t
    out += a
    return out


def lum(p):
    return (.2126 * p[..., 0] + .7152 * p[..., 1] + .0722 * p[..., 2]).astype(np.float32)


# ---------------------------------------------------------------- drawing
def draw_polys(polys, width, n=N, value=255, aa=True, img=None, closed=False):
    """Rasterise many polylines at once into a uint8 coverage image."""
    img = np.zeros((n, n), np.uint8) if img is None else img
    pts = [np.round(np.asarray(p) * 16).astype(np.int32) for p in polys if len(p) > 1]
    if pts:
        cv2.polylines(img, pts, closed, int(value), int(max(1, width)), cv2.LINE_AA if aa else cv2.LINE_8, shift=4)
    return img


def draw_ids(polys, ids, width, n=N, img=None, closed=False):
    """Rasterise polylines carrying an integer id (no AA) into an int32 map."""
    img = np.full((n, n), -1, np.int32) if img is None else img
    for p, i in zip(polys, ids):
        if len(p) > 1:
            cv2.polylines(img, [np.round(np.asarray(p)).astype(np.int32)], closed, int(i), int(max(1, width)), cv2.LINE_8)
    return img


def dilate_ids(ids, r):
    """Spread non-negative ids into -1 holes (so AA edges get a colour)."""
    k = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
    pos = (ids + 1).astype(np.float32)
    grown = cv2.dilate(pos, k)
    out = ids.copy()
    hole = ids < 0
    out[hole] = grown[hole].astype(np.int32) - 1
    return out


# ------------------------------------------------------------------ spec
def pack(paint, M, R, C, n=N):
    """Finalise: clip paint to [0,1]; spec to the real ABI (R/Cc floor 16).
    Allocation-light: clips in place where the inputs are private float32."""
    paint = np.asarray(paint, np.float32)
    if not paint.flags.writeable:
        paint = paint.copy()
    np.clip(paint, 0, 1, out=paint)
    h, w = paint.shape[:2]
    spec = np.empty((h, w, 3), np.float32)
    for ch, (src, lo) in enumerate(((M, 0), (R, 16), (C, 16))):
        spec[..., ch] = src
    np.clip(spec[..., 0], 0, 255, out=spec[..., 0])
    np.clip(spec[..., 1:], 16, 255, out=spec[..., 1:])
    return paint, spec


def tiers(h, k=8):
    """Per-feature 8-tier shade from a hash in [0,1): the owner's shade law."""
    return (np.floor(np.clip(h, 0, .9999) * k) / (k - 1)).astype(np.float32)


# ------------------------------------------------------------ figure fields
def stamp_ids(polys, n=N, img=None):
    """Painter's-order rasterisation of convex polygons into an int32 id map
    (-1 = empty). Later polygons cover earlier ones. Sub-pixel exact (shift 4)."""
    img = np.full((n, n), -1, np.int32) if img is None else img
    for i, p in enumerate(polys):
        cv2.fillConvexPoly(img, np.round(np.asarray(p) * 16).astype(np.int32), int(i), cv2.LINE_8, 4)
    return img


def id_local(ids, cx, cy, ang, x=None, y=None):
    """Local (u along, v across) coordinates of each pixel in its figure frame.
    cx, cy, ang are per-figure arrays; background pixels get figure 0's frame."""
    if x is None:
        x, y = xy(ids.shape[0])
    k = np.maximum(ids, 0)
    return rot(x - cx[k], y - cy[k], ang[k])


def leaf(u, v, L, W, p=.8):
    """Signed distance-ish for a pointed leaf/blade of length L, half-width W."""
    t = np.clip(1 - (2 * u / L) ** 2, 0, 1)
    return (np.abs(v) - W * t ** p).astype(np.float32)


def fhash(a, b=None, seed=0):
    """Cheap per-pixel float hash in [0,1) for integer-valued (or piecewise
    constant) float fields: frac(sin(dot)*43758.5453), all in place."""
    v = np.multiply(a, np.float32(12.9898), dtype=np.float32)
    if b is not None:
        v += np.multiply(b, np.float32(78.233), dtype=np.float32)
    v += np.float32((seed * 0.6180339) % 97.)
    np.sin(v, out=v)
    v *= np.float32(43758.5453)
    v -= np.floor(v)
    return v


def lines_code(x, y, lines, n=N):
    """Arrangement of straight cut lines: returns (region code float, distance
    to the nearest line). lines = [(cx, cy, angle, weight), ...]. In place."""
    code = np.zeros((n, n), np.float32); dmin = np.full((n, n), 1e9, np.float32)
    s = np.empty((n, n), np.float32); t = np.empty((n, n), np.float32)
    for cx, cy, a, w in lines:
        ca, sa = np.float32(np.cos(a)), np.float32(np.sin(a))
        np.multiply(x, ca, out=s); np.multiply(y, sa, out=t); s += t
        s -= np.float32(cx * ca + cy * sa)
        np.add(code, np.float32(w), out=code, where=s > 0)
        np.abs(s, out=s); np.minimum(dmin, s, out=dmin)
    return code, dmin


def frac(a):
    """a - floor(a), allocation-light (np.remainder is ~5x slower)."""
    out = np.floor(a).astype(np.float32)
    np.subtract(a, out, out=out)
    return out


def turing(seed, period=12., iters=14, res=1024, n=N, aniso=None):
    """Reaction-diffusion-like labyrinth (activator/inhibitor DoG iteration)
    computed at `res` and upsampled: returns a smooth field in ~[-1,1] whose
    zero set is a meandering maze with the given period (px at n)."""
    s1 = period / (n / res) / 6.3
    f = rng(seed).standard_normal((res, res)).astype(np.float32)
    for _ in range(iters):
        a = cv2.GaussianBlur(f, (0, 0), s1)
        b = cv2.GaussianBlur(f, (0, 0), s1 * 1.9)
        a -= b
        a *= np.float32(4.)
        f = np.tanh(a)
    return cv2.resize(f, (n, n), interpolation=cv2.INTER_CUBIC)


def clothoid(p0, a0, length, k1, k2, steps=40):
    """Pinstriper's curve: heading a(t) = a0 + k1 t + k2 t^3 (curls at the end)."""
    t = np.linspace(0, 1, steps)
    a = a0 + k1 * t + k2 * t ** 3
    dx = np.cos(a) * length / steps; dy = np.sin(a) * length / steps
    return np.stack([p0[0] + np.cumsum(dx), p0[1] + np.cumsum(dy)], 1)


def _hash_mix(keys):
    with np.errstate(over='ignore'):
        z = np.int32(0x2545F491)
        for i, k in enumerate(keys):
            k = np.asarray(k)
            if k.dtype.kind == 'f':
                k = np.floor(k)
            k = k.astype(np.int32, copy=False)
            z = (z ^ k) * np.int32(_HP[i % len(_HP)])
            z = z ^ (z >> 15)
            z = z * np.int32(-2048144789)
            z = z ^ (z >> 13)
    return _HLUT[np.asarray(z) & 0xFFFFF]


def ramps(t, fam, stop_lists):
    """Several gradient maps selected per pixel by an int family field, done
    as ONE gather from a stacked LUT (no boolean-mask passes)."""
    luts = []
    lutx = np.linspace(0, 1, 1024, dtype=np.float32)
    for stops in stop_lists:
        cols = hexrgb(*stops); pos = np.linspace(0, 1, len(stops))
        luts.append(np.stack([np.interp(lutx, pos, cols[:, c]) for c in range(3)], 1))
    lut = np.concatenate(luts, 0).astype(np.float32)
    idx = np.multiply(t, np.float32(1023.), dtype=np.float32).astype(np.int32)
    np.clip(idx, 0, 1023, out=idx)
    idx += np.asarray(fam, np.int32) * 1024
    return lut[idx]


def field_conv(points, weights, kernel_fn, n=512, pad=2):
    """Sum of kernel(dx, dy) * w over point sources, evaluated on an n x n grid
    covering the canvas, by one FFT convolution (replaces per-source loops).
    kernel_fn(ddx, ddy) receives float64 offset grids in canvas px."""
    cell = N / n; G = pad * n
    src = np.zeros((G, G), np.float64)
    ix = np.clip((np.asarray(points)[:, 0] // cell).astype(int), 0, n - 1)
    iy = np.clip((np.asarray(points)[:, 1] // cell).astype(int), 0, n - 1)
    np.add.at(src, (iy, ix), np.asarray(weights, np.float64))
    off = np.where(np.arange(G) < G // 2, np.arange(G), np.arange(G) - G) * cell
    ddy, ddx = np.meshgrid(off, off, indexing='ij')
    out = np.fft.irfft2(np.fft.rfft2(kernel_fn(ddx, ddy)) * np.fft.rfft2(src), s=(G, G))[:n, :n]
    return out.astype(np.float32)


_HUE_T = None


def hue_rgb(h, s=.85, v=1.):
    """HSV->RGB for a hue field (any real h, wrapped) via a 1024-entry LUT."""
    global _HUE_T
    if _HUE_T is None:
        hh = np.linspace(0, 1, 1024, endpoint=False, dtype=np.float32)
        k = np.stack([(5 + hh * 6) % 6, (3 + hh * 6) % 6, (1 + hh * 6) % 6], -1)
        _HUE_T = np.clip(np.minimum(k, 4 - k), 0, 1).astype(np.float32)
    idx = (frac(np.asarray(h, np.float32)) * np.float32(1023.999)).astype(np.int32)
    t = _HUE_T[idx]
    s = np.asarray(s, np.float32); v = np.asarray(v, np.float32)
    if s.ndim == 2:
        s = s[..., None]
    if v.ndim == 2:
        v = v[..., None]
    t *= -s
    t += np.float32(1.)
    t *= v
    return t


def lerp3(a, b, t):
    """In-place a <- a*(1-t) + b*t for a private HxWx3 float32 `a` (b may be a
    colour triple or an HxWx3 array); returns a. No full-size allocation when
    b is a triple."""
    t = np.asarray(t, np.float32)
    if t.ndim == 2:
        t = t[..., None]
    if np.ndim(b) == 1:
        bb = np.asarray(b, np.float32)
        a -= bb
        a *= (np.float32(1.) - t)
        a += bb
    else:
        d = np.subtract(b, a, dtype=np.float32); d *= t; a += d
    return a


def addc(a, w, color):
    """In-place a += w[...,None] * color (colour triple). Returns a."""
    for ch in range(3):
        c = float(color[ch])
        if c != 0.:
            a[..., ch] += w * np.float32(c)
    return a


_MZ = {}


def enrich(M, R, C, seed, pitch=20., cc_mix=.6, chrome=.035, dull=.035, mask=None, n=N, cc_lo=16., cc_hi=255.):
    """ASTRA-R2 spec micro-zone layer (the Hologram Metal mechanism the owner
    calls a gold standard): an independent clearcoat mosaic over ~20 px zones
    plus 1 px chrome micro-flakes and matte specks (below the 8-32 px band, so
    FOLLOW is untouched), so neighbouring zones never
    respond alike under light. Clearcoat carries only ~7% of spec luminance, so
    the M/R structure that FOLLOWs the paint is preserved. `mask` limits the
    layer (e.g. keep velvet pile or wax body honestly matte). In place."""
    key = (int(seed), float(pitch))
    if key not in _MZ:
        lab, _, pts = voronoi(sites(seed, pitch, .95, n=n), n=n)
        z2 = hash01(np.arange(len(pts)), seed + 2)[lab]
        z1 = rng(seed + 1).random((n, n), dtype=np.float32)   # per-pixel micro-flake field
        _MZ.clear(); _MZ[key] = (z1, z2)
    z1, z2 = _MZ[key]
    chrome *= .25; dull *= .25                                # 1 px flecks: ~0.9% each
    w = np.float32(cc_mix) if mask is None else (np.asarray(mask, np.float32) * np.float32(cc_mix))
    cc = z2 * np.float32(cc_hi - cc_lo) + np.float32(cc_lo)
    cc -= C; cc *= w; C += cc
    ch = (z1 < chrome); du = (z1 > 1 - dull)
    if mask is not None:
        mb = np.asarray(mask) > .5
        ch &= mb; du &= mb
    M[ch] = 255.; R[ch] = 16.
    M[du] = 0.; R[du] = 240.
    return M, R, C


def r_from_luma(col, M, C, lo=20., span=210.):
    """Roughness that makes SPEC LUMA a monotone function of PAINT LUMA while M and
    Cc stay free to carry the spec HUE. The finish law's FOLLOW axis correlates
    band-limited detail of paint luma with spec luma (0.2126 M + 0.7152 R + 0.0722 Cc),
    so a two-population spec (matte vs metal) fails FOLLOW wherever the populations
    change but paint brightness does not. Solving R from a luma target
    Lt = lo + span * lum(paint) removes that failure by construction (ASTRA-R2,
    owner: Chromatic Undertow / Switchblade Chevron 'colours explode with the spec')."""
    Lt = np.float32(lo) + np.float32(span) * lum(col)
    R = Lt - np.float32(.2126) * np.asarray(M, np.float32) - np.float32(.0722) * np.asarray(C, np.float32)
    R *= np.float32(1. / .7152)
    return np.clip(R, 16., 255.).astype(np.float32)
