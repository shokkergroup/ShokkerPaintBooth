"""ASTRA MAD SCIENTIST — the living lab (ten constructions).

SPB-105 / ASTRA-R2 2026-09-27 (Claude). Lane arc: SPECIMENS UNDER THE
MICROSCOPE — every card is a real lab phenomenon (mitosis, colonies,
karyotypes, attractors, neurons, bubble-chamber tracks, bismuth hoppers...)
rendered from its actual mathematics, in maximal continuous colour (the lane
brief asks for millions of distinct colours, so every card carries smooth
per-feature gradients rather than flat fills).

Every function: (seed) -> (paint HxWx3 float 0..1, spec HxWx3 float 0..255).
"""
import math
import cv2
import numpy as np
from . import kit as K

N = K.N
F32 = np.float32


def _per(n, seed):
    return K.hash01(np.arange(n), seed)


def _over(M, R, C, w, m, r, c):
    w = np.clip(w, 0, 1)
    return M * (1 - w) + m * w, R * (1 - w) + r * w, C * (1 - w) + c * w


def _hue(h, s=.85, v=1.):
    """HSV->RGB for a hue field (LUT-backed, see kit.hue_rgb)."""
    return K.hue_rgb(h, s, v)


def _dither(paint, seed, amt=.012):
    """Continuous micro-variation: the lane's multi-million colour population."""
    return paint * (1 + amt * K.noise(seed, 700, interp=cv2.INTER_LINEAR))[..., None]


# ======================================================== CYTOKINESIS CANDY
def cytokinesis_candy(seed=42):
    """A tissue of hard-candy cells caught mid-mitosis: resting cells hold
    one speckled nucleus; dividing cells pinch into peanuts at the cleavage
    furrow, with two daughter nuclei joined by glowing spindle fibres. Glassy
    candy highlights, extracellular jelly between."""
    x, y = K.xy()
    lab, sd, sp = K.voronoi(K.sites(seed + 1, 29, .9))
    n = len(sp)
    R = (11 + 4 * _per(n, seed + 2))[lab]
    div = (_per(n, seed + 3) < .45)[lab]
    ang = (_per(n, seed + 4) * K.TAU)[lab]
    dx, dy = K.cell_local(lab, sp, x, y)
    u, v = K.rot(dx, dy, ang)
    sep = R * .52 * div
    d1 = np.hypot(u - sep, v); d2 = np.hypot(u + sep, v)
    rr = np.where(div, R * .74, R)
    kk = F32(.35)
    sm = -np.log(np.exp(-kk * (d1 - rr)) + np.exp(-kk * (d2 - rr))) / kk
    wob = 1.2 * K.noise(seed + 5, 180)
    sdf = np.where(div, sm, np.hypot(u, v) - R) + wob
    cell = K.near(sdf, 0., 1.2)
    depth = np.clip(-sdf / (R * .8), 0, 1)
    hue = (.5 * K.unit(K.fbm(seed + 13, (3, 6), .5)) * 1.6 + _per(n, seed + 6)[lab] * .22 + .05 * K.noise(seed + 7, 60) + .02 * depth)
    body = _hue(hue, .45 + .25 * depth, 1.) * (.72 + .3 * depth)[..., None]
    hl = K.relief(np.sqrt(depth) * 6, 1.)
    body = body + np.clip(hl - .2, 0, 1)[..., None] * .6
    nd = np.where(div, np.minimum(d1, d2), np.hypot(u, v))
    nuc = K.near(nd, R * .32, 1.) * cell
    chrom = K.sstep(.3, 1.2, K.noise(seed + 8, 500)) * nuc
    nucc = _hue(hue + .5, .75, .55)
    spin = div & (np.abs(u) < sep) & (np.abs(v) < R * .32 * np.sqrt(np.clip(1 - (u / np.maximum(sep, 1)) ** 2, 0, 1)) + .8)
    fib = K.near(np.abs(K.frac(v / F32(2.6)) - .5) * 2.6, .45) * spin * (1 - nuc)
    jelly = K.ramp(K.unit(K.fbm(seed + 9, (6, 12, 48), .6)), ['12081e', '221236', '301a4a'])
    fibres = K.near(np.abs(K.noise(seed + 10, 120)), .04, .03) * .5
    ground = jelly + fibres[..., None] * np.array([.3, .2, .5], F32)
    col = K.mix(ground, body, cell)
    col = K.mix(col, nucc * (.7 + .5 * chrom)[..., None], nuc)
    col = K.mix(col, np.array([1., 1., .85], F32), fib * .85)
    col = _dither(col, seed + 11)
    tier = K.tiers(_per(n, seed + 12)[lab])
    M = 20 + 30 * tier
    Rr = 200 - 170 * depth * cell
    C = 16 + 200 * (1 - cell)
    M, Rr, C = _over(M, Rr, C, nuc, 120, 60, 40)
    M, Rr, C = _over(M, Rr, C, fib, 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ===================================================== QUANTUM PETRI CARNIVAL
def quantum_petri(seed=42):
    """A carnival of bacterial colonies on amber agar: each colony grows in
    quantised concentric rings with a pinwheel core and fractal fingering at
    its rim, some ringed by clear zones of inhibition, tiny satellite
    colonies speckling the gel between."""
    x, y = K.xy()
    lab, sd, sp = K.voronoi(K.sites(seed + 1, 64, .9))
    n = len(sp)
    Rc = (16 + 18 * _per(n, seed + 2))[lab]
    on = (_per(n, seed + 3) < .88)[lab]
    dx, dy = K.cell_local(lab, sp, x, y)
    th = np.arctan2(dy, dx)
    fing = K.fbm(seed + 4, (48, 96, 192), .7) * .35 + K.ridged(seed + 5, (64, 128), .6) * .25
    rn = sd / (Rc * (1 + fing))
    colony = (rn < 1) & on
    ring = np.floor(rn * 6)
    hue0 = K.unit(K.fbm(seed + 14, (3, 6), .5)) * 1.2 + _per(n, seed + 6)[lab] * .25
    hue = hue0 + ring * .07 + .03 * K.noise(seed + 7, 40)
    pin = (np.cos(th * (4 + (_per(n, seed + 8)[lab] * 5).astype(np.int32)) + rn * 6) > 0) & (rn < .35)
    body = _hue(hue, .75, 1.) * (.6 + .4 * K.frac(rn * 6))[..., None]
    body = np.where(pin[..., None], _hue(hue0 + .5, .8, 1.), body)
    edge = K.near(np.abs(rn - 1) * Rc, 1.) * on
    zone = (rn > 1.05) & (rn < 1.45) & (_per(n, seed + 9)[lab] < .4)
    agar = K.ramp(K.unit(K.fbm(seed + 10, (4, 8, 16), .55)), ['5a3006', '8a5210', 'b8801e', 'd8a84a'])
    agar = np.where(zone[..., None], agar * .55 + .35, agar)
    sat = (K.noise(seed + 11, 420, interp=cv2.INTER_NEAREST) > 1.9) & ~colony
    col = np.where(colony[..., None], body, agar)
    col = col * (1 - .6 * edge)[..., None]
    col = np.where(sat[..., None], _hue(K.noise(seed + 12, 30) * .5 + .5, .6, 1.), col)
    col = _dither(col, seed + 13)
    tier = K.tiers(K.frac(ring * .37 + hue0))
    M = np.where(colony, 60 + 120 * tier, 20)
    Rr = 210 - 175 * K.lum(col)
    C = np.where(colony, 30, 16)
    M, Rr, C = _over(M, Rr, C, edge, 0, 200, 220)
    M, Rr, C = _over(M, Rr, C, sat.astype(F32), 150, 30, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ========================================================= CHROMOSOME RIOT
def chromosome_riot(seed=42):
    """A spectral karyotype rioting across the car: thousands of X-shaped
    chromosomes at every angle, sister chromatids pinched at the centromere,
    each painted its own fluorescent spectral hue with G-band stripes and
    bright telomere caps, on DAPI-blue darkness."""
    r = K.rng(seed)
    x, y = K.xy()
    pts = K.sites(seed + 1, 36, .95)
    r.shuffle(pts)
    n = len(pts)
    a0 = r.uniform(0, np.pi, n); spread = r.uniform(.3, .7, n)
    p_len = r.uniform(8, 15, n); q_len = r.uniform(15, 30, n); W = r.uniform(3.4, 4.8, n)
    arms, cx, cy, aa, ll, ww = [], [], [], [], [], []
    for i in range(n):
        for k, (da, L) in enumerate(((spread[i], q_len[i]), (-spread[i], q_len[i]), (np.pi + spread[i], p_len[i]), (np.pi - spread[i], p_len[i]))):
            a = a0[i] + da
            d = np.array([np.cos(a), np.sin(a)]); m = np.array([-d[1], d[0]])
            c0 = pts[i]; c1 = pts[i] + d * L
            w = W[i]
            arms.append(np.array([c0 + m * w * .55, c1 + m * w, c1 + d * w * .9, c1 - m * w, c0 - m * w * .55]))
            cx.append(c0[0]); cy.append(c0[1]); aa.append(a); ll.append(L); ww.append(w)
    ids = K.stamp_ids(arms)
    cx, cy, aa, ll, ww = [np.asarray(v, F32) for v in (cx, cy, aa, ll, ww)]
    k = np.maximum(ids, 0); on = ids >= 0
    u, v = K.id_local(ids, cx, cy, aa, x, y)
    chrom = k // 4
    hue = K.unit(K.fbm(seed + 7, (3, 6), .5)) * 1.3 + K.fhash(chrom.astype(F32), None, seed + 2) * .22
    t = np.clip(u / ll[k], 0, 1.2)
    band = K.fhash(np.floor(t * (4 + ll[k] / 3)), chrom.astype(F32), seed + 3)
    gband = (band < .35).astype(F32)
    edge_w = ww[k] * (.55 + .45 * np.clip(u / 4., 0, 1))
    across = np.clip(1 - np.abs(v) / np.maximum(edge_w, .5), 0, 1)
    body = _hue(hue, .8, 1.) * (.45 + .65 * np.sqrt(across))[..., None] * (1 - .55 * gband)[..., None]
    telo = (t > .92) & on
    body = np.where(telo[..., None], np.array([1., 1., 1.], F32), body)
    cen = K.near(np.hypot(x - cx[k], y - cy[k]), 1.6) * on
    bg = K.ramp(K.unit(K.fbm(seed + 4, (4, 8, 32), .6)), ['02041a', '06103a', '0a1a5a'])
    haze = K.blur(on.astype(F32), 4.) * .35
    col = bg + haze[..., None] * np.array([.2, .25, .6], F32)
    col = np.where(on[..., None], body, col)
    col = K.mix(col, np.array([.1, .05, .15], F32), cen * .7)
    col = _dither(col, seed + 5)
    tier = K.tiers(K.fhash(chrom.astype(F32), None, seed + 6))
    M = np.where(on, 90 + 150 * tier * (1 - gband), 30)
    Rr = np.where(on, 110 - 80 * across + 60 * gband, 200)
    C = np.where(on, 16 + 40 * gband, 240)
    Rr = np.where(telo, 16, Rr); M = np.where(telo, 255, M)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.9)
    return K.pack(col, M, Rr, C)


# ============================================================ PLASMA SUTURES
def plasma_sutures(seed=42):
    """Wounds in an iridescent plasma membrane closed with plasma: flowing
    incisions across the car, each stitched shut with glowing cross-stitches
    of violet-white arc, Lichtenberg discharges branching off the stitches,
    cauterised dark edges along every cut."""
    r = K.rng(seed)
    x, y = K.xy()
    th = K.fbm(seed + 1, (2, 4, 8), .5) * F32(np.pi * 1.6)
    cut = np.zeros((N, N), np.uint8); stitch = np.zeros((N, N), np.uint8); arc = np.zeros((N, N), np.uint8)
    seeds = K.sites(seed + 2, 64, .95)
    for (sx, sy) in seeds:
        px_, py_ = float(sx), float(sy); path = [(px_, py_)]
        for s in range(int(r.integers(10, 24))):
            ix, iy = min(max(int(px_), 0), N - 1), min(max(int(py_), 0), N - 1)
            a = float(th[iy, ix]); px_ += math.cos(a) * 6; py_ += math.sin(a) * 6; path.append((px_, py_))
        path = np.array(path)
        cv2.polylines(cut, [np.round(path * 16).astype(np.int32)], False, 255, 2, cv2.LINE_AA, 4)
        seg = np.diff(path, axis=0); nrm = np.stack([-seg[:, 1], seg[:, 0]], 1) / 6.
        cen = path[:-1] + seg * .5
        st = []
        for sgn in (1, -1):
            a_ = cen - nrm * 5 - seg * .35 * sgn; b_ = cen + nrm * 5 + seg * .35 * sgn
            st.extend(np.stack([a_, b_], 1))
        for j in range(len(seg)):
            c = cen[j]
            if r.random() < .08:
                q = c.copy(); a = np.arctan2(nrm[j, 1], nrm[j, 0]) * r.choice([-1, 1]); pts = [q.copy()]
                for b in range(int(r.integers(4, 9))):
                    a += r.normal(0, .6); q = q + np.array([np.cos(a), np.sin(a)]) * r.uniform(3, 6); pts.append(q.copy())
                cv2.polylines(arc, [np.round(np.array(pts) * 16).astype(np.int32)], False, 255, 1, cv2.LINE_AA, 4)
        cv2.polylines(stitch, [np.round(q_ * 16).astype(np.int32) for q_ in st], False, 255, 1, cv2.LINE_AA, 4)
    cutf = cut.astype(F32) / 255; stf = stitch.astype(F32) / 255; arcf = arc.astype(F32) / 255
    em = np.clip(stf + arcf * .8, 0, 1)
    glow = K.blur(em, 2.) * 1.6 + K.blur(em, 6.) * .9
    burn = K.blur(cutf, 2.5) * 1.5
    mem = K.unit(K.fbm(seed + 3, (12, 24, 48, 128), .65))
    skin = K.thin_film(mem * 1.6 + .15 * K.noise(seed + 4, 200), .8, .40) * .75
    col = skin * (1 - np.clip(burn, 0, .9))[..., None]
    col = K.mix(col, np.array([.08, .0, .02], F32), cutf)
    col = col + glow[..., None] * np.array([.55, .35, 1.], F32)
    col = K.mix(col, np.array([.95, .9, 1.], F32), em)
    col = _dither(col, seed + 5)
    M = 150 + 80 * mem
    Rr = 20 + 150 * (1 - K.lum(col)) + 60 * np.clip(burn, 0, 1)
    C = 16 + 150 * np.clip(burn, 0, 1)
    M, Rr, C = _over(M, Rr, C, cutf, 0, 250, 255)
    M, Rr, C = _over(M, Rr, C, np.clip(glow, 0, 1) * .6, 220, 30, 60)
    M, Rr, C = _over(M, Rr, C, em, 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ========================================================== BISMUTH DELIRIUM
def bismuth_delirium(seed=42):
    """An aggregate of bismuth hopper crystals: every crystal a square
    stair-stepped spiral sinking to its hollow centre, its oxide skin shifting
    gold-magenta-blue-green with terrace height by thin-film interference,
    bright metal lips on every step."""
    x, y = K.xy()
    lab, _, sp = K.voronoi(K.sites(seed + 1, 58, .9))
    n = len(sp)
    ang = (_per(n, seed + 2) * np.pi / 2)[lab]
    step = (7. + 3.5 * _per(n, seed + 3))[lab]
    spiral = (_per(n, seed + 4) < .5)[lab]
    dx, dy = K.cell_local(lab, sp, x, y)
    u, v = K.rot(dx, dy, ang)
    cheb = np.maximum(np.abs(u), np.abs(v))
    quad = (np.arctan2(v, u) / F32(K.TAU) + .5)
    cs = cheb / step + np.where(spiral, quad, 0)
    lev = np.floor(cs)
    fr = cs - lev
    ed = K.edge_distance(lab)
    hgt = lev * .09 + fr * .03
    film = K.thin_film(hgt * 1.6 + K.unit(K.fbm(seed + 10, (3, 6), .5)) * 1.1 + _per(n, seed + 5)[lab] * .18 + .08 * K.noise(seed + 6, 80), 1.1, .56)
    film = K.mix(np.array([.62, .6, .66], F32), film, .55 + .45 * K.sstep(.2, .8, K.unit(K.fbm(seed + 9, (6, 12), .5))))
    lip = K.near(fr * step, .9)
    face = np.where(np.abs(u) > np.abs(v), np.sign(u), np.sign(v) * 2)
    shade = .78 + .12 * face.astype(F32) * .5
    col = film * shade[..., None] * (.75 + .35 * fr)[..., None]
    col = K.mix(col, np.array([.92, .9, .88], F32), lip * .85)
    col = col * (1 - .7 * K.near(ed, 1.2))[..., None]
    col = _dither(col, seed + 7)
    tier = K.tiers(K.fhash(lev, lab.astype(F32), seed + 8))
    M = 235 + 20 * tier
    Rr = 150 - 130 * K.lum(col) + 10 * tier
    C = 220 - 60 * tier
    M, Rr, C = _over(M, Rr, C, lip, 255, 16, 120)
    M, Rr, C = _over(M, Rr, C, K.near(ed, 1.2), 120, 180, 250)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ========================================================= STRANGE ATTRACTOR
def strange_attractor(seed=42):
    """Specimens of chaos: real Clifford and de Jong strange attractors are
    iterated hundreds of thousands of times, their visit densities rendered
    as glowing filament galaxies coloured by orbit speed, and scattered as
    rotated, mirrored specimens of every size across a dark phase-space
    grid."""
    r = K.rng(seed)
    S = 176
    params = [('c', -1.4, 1.6, 1.0, .7), ('c', 1.7, 1.7, .6, 1.2), ('c', -1.7, 1.3, -.1, -1.21),
              ('d', 1.4, -2.3, 2.4, -2.1), ('d', -2.7, -.09, -.86, -2.2), ('d', 2.01, -2.53, 1.61, -.33)]
    specs = []
    for kind, a, b, c, d in params:
        px = r.uniform(-.1, .1, 3000); py = r.uniform(-.1, .1, 3000)
        H = np.zeros((S, S), np.float64); V = np.zeros((S, S), np.float64)
        for it in range(160):
            if kind == 'c':
                nx = np.sin(a * py) + c * np.cos(a * px); ny = np.sin(b * px) + d * np.cos(b * py)
            else:
                nx = np.sin(a * py) - np.cos(b * px); ny = np.sin(c * px) - np.cos(d * py)
            sp_ = np.hypot(nx - px, ny - py)
            px, py = nx, ny
            if it > 10:
                lim = 1 + abs(c) if kind == 'c' else 2.
                ix = ((px / (lim * 2.05) + .5) * (S - 1)).astype(np.int32); iy = ((py / (lim * 2.05) + .5) * (S - 1)).astype(np.int32)
                ok = (ix >= 0) & (ix < S) & (iy >= 0) & (iy < S)
                np.add.at(H, (iy[ok], ix[ok]), 1.); np.add.at(V, (iy[ok], ix[ok]), sp_[ok])
        dens = np.log1p(H); dens /= max(dens.max(), 1e-6)
        spd = np.where(H > 0, V / np.maximum(H, 1), 0); spd /= max(spd.max(), 1e-6)
        specs.append((dens.astype(F32), spd.astype(F32)))
    acc = np.zeros((N, N), F32); hacc = np.zeros((N, N), F32)
    for (cx, cy) in K.sites(seed + 1, 120, .95):
        dens, spd = specs[int(r.integers(0, len(specs)))]
        sc = r.uniform(.6, 1.15); a = r.uniform(0, 360); mir = r.random() < .5
        dd = dens[:, ::-1] if mir else dens; ss = spd[:, ::-1] if mir else spd
        M_ = cv2.getRotationMatrix2D((S / 2, S / 2), a, sc)
        size = int(S * sc * 1.45) | 1
        M_[0, 2] += size / 2 - S / 2; M_[1, 2] += size / 2 - S / 2
        wd = cv2.warpAffine(dd, M_, (size, size), flags=cv2.INTER_LINEAR)
        ws = cv2.warpAffine(ss, M_, (size, size), flags=cv2.INTER_LINEAR)
        x0, y0 = int(cx - size / 2), int(cy - size / 2)
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(N, x0 + size), min(N, y0 + size)
        if xb <= xa or yb <= ya:
            continue
        sub_d = wd[ya - y0:yb - y0, xa - x0:xb - x0]; sub_s = ws[ya - y0:yb - y0, xa - x0:xb - x0]
        acc[ya:yb, xa:xb] = np.maximum(acc[ya:yb, xa:xb], sub_d)
        hacc[ya:yb, xa:xb] = np.where(sub_d >= acc[ya:yb, xa:xb] - 1e-6, sub_s, hacc[ya:yb, xa:xb])
    x, y = K.xy()
    grid = np.maximum(K.near(np.abs(K.frac(x / F32(64.)) - .5) * 64, .5), K.near(np.abs(K.frac(y / F32(64.)) - .5) * 64, .5)) * .12
    bg = K.ramp(K.unit(K.fbm(seed + 2, (3, 6, 12), .5)), ['04020c', '0a0620', '140a30']) + grid[..., None] * np.array([.2, .4, .6], F32)
    d = np.clip(acc * 1.25, 0, 1)
    hue = .72 - .62 * hacc + .05 * K.noise(seed + 3, 50)
    fil = _hue(hue, .85 - .5 * d ** 3, 1.)
    col = bg * (1 - d)[..., None] + fil * (d ** .8)[..., None]
    col = col + (K.blur(d, 3.) * .35)[..., None] * _hue(hue, .7, 1.)
    col = _dither(col, seed + 4)
    M = 40 + 210 * d
    Rr = 170 - 150 * d
    C = 200 - 180 * d
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(col, M, Rr, C)


# ============================================================ NEURON CARNIVAL
def neuron_carnival(seed=42):
    """A Brainbow tangle: hundreds of neurons each labelled its own
    fluorescent colour, somata glowing, dendrites branching three levels
    deep, axons running long and studded with synaptic boutons, all over a
    dark neuropil."""
    r = K.rng(seed)
    x, y = K.xy()
    img = np.zeros((N, N, 3), np.uint8); cov = np.zeros((N, N), np.uint8); soma = np.zeros((N, N), np.uint8)
    bout = np.zeros((N, N), np.uint8)
    for (cx, cy) in K.sites(seed + 1, 72, .95):
        h = r.random(); rgb = tuple(int(255 * c) for c in _hue(np.array([h]), .8, 1.)[0])
        polys = []
        jit = iter(r.normal(0, .25, 400).tolist()); uni = iter(r.random(400).tolist())
        def branch(px, py, a, L, depth):
            pts = [(px, py)]
            for s in range(6):
                a += next(jit); px += math.cos(a) * L / 6; py += math.sin(a) * L / 6; pts.append((px, py))
            polys.append(np.array(pts))
            if depth > 0:
                for sgn in (-1, 1):
                    if next(uni) < .8:
                        bx, by = pts[2 + int(next(uni) * 4)]
                        branch(bx, by, a + sgn * (.4 + .5 * next(uni)), L * .65, depth - 1)
        for k in range(int(r.integers(4, 7))):
            branch(float(cx), float(cy), r.uniform(0, 6.28), r.uniform(18, 30), 2)
        a = r.uniform(0, 6.28); qx, qy = float(cx), float(cy); ax = [(qx, qy)]
        aj = r.normal(0, .12, 40).tolist()
        for s in range(40):
            a += aj[s]; qx += math.cos(a) * 6; qy += math.sin(a) * 6; ax.append((qx, qy))
            if s % 5 == 4:
                cv2.circle(bout, (int(qx * 16), int(qy * 16)), 2 * 16, 255, -1, cv2.LINE_AA, 4)
                cv2.circle(img, (int(qx * 16), int(qy * 16)), 2 * 16, rgb, -1, cv2.LINE_AA, 4)
        polys.append(np.array(ax))
        pp = [np.round(p_ * 16).astype(np.int32) for p_ in polys]
        cv2.polylines(img, pp, False, rgb, 1, cv2.LINE_AA, 4)
        cv2.polylines(cov, pp, False, 255, 1, cv2.LINE_AA, 4)
        cv2.circle(img, (int(cx * 16), int(cy * 16)), int(4.5 * 16), rgb, -1, cv2.LINE_AA, 4)
        cv2.circle(soma, (int(cx * 16), int(cy * 16)), int(4.5 * 16), 255, -1, cv2.LINE_AA, 4)
    c = img.astype(F32) / 255
    cv_ = np.clip((cov.astype(F32) + soma + bout) / 255, 0, 1)
    halo = cv2.GaussianBlur(c, (0, 0), 3.) * 1.3 + cv2.GaussianBlur(c, (0, 0), 9.) * .6
    bg = K.ramp(K.unit(K.fbm(seed + 2, (4, 8, 32, 128), .6)), ['04030a', '0a0816', '120c22'])
    col = bg + halo * .6
    col = K.mix(col, c * 1.15, cv_)
    sf = soma.astype(F32) / 255
    col = K.mix(col, np.minimum(c * .6 + .55, 1), K.near(np.hypot(*K.grad(K.blur(sf, 1.5))) * 0 + (1 - sf), .15) * sf * .6)
    col = _dither(col, seed + 3)
    hl = np.clip(halo.max(2), 0, 1)
    M = 40 + 100 * hl
    Rr = 180 - 120 * hl
    C = 200 - 150 * hl
    M, Rr, C = _over(M, Rr, C, cv_, 230, 20, 30)
    M, Rr, C = _over(M, Rr, C, sf, 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(col, M, Rr, C)


# ============================================================ XENOBOT ORCHARD
def xenobot_orchard(seed=42):
    """An orchard of xenobots: speckled frog-cell spheres with Pac-Man mouths and
    beating cilia planted in drifting rows, gathering loose cells into piles.
    v2: bigger bots in lime / cyan / hot pink on a warm oxblood soil (a real
    complement), pearl-metal bodies on a matte ground, so the spec is the
    colour-opposite of the paint."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 25, 5)
    rowh = F32(44.)
    j = np.floor(wy / rowh)
    colw = F32(48.)
    xs = wx + K.fhash(j, None, seed) * 48
    i = np.floor(xs / colw)
    cxl = (i + .5) * colw + (K.fhash(i, j, seed + 1) - .5) * 8
    cyl = (j + .5) * rowh + (K.fhash(i, j, seed + 2) - .5) * 6
    du = xs - cxl; dv = wy - cyl
    Rb = 14 + 5 * K.fhash(i, j, seed + 3)
    mouth_a = K.fhash(i, j, seed + 4) * F32(K.TAU)
    rr = np.hypot(du, dv); th = np.arctan2(dv, du)
    dth = np.abs(((th - mouth_a + np.pi) % F32(K.TAU)) - np.pi)
    gape = .35 + .35 * K.fhash(i, j, seed + 5)
    mouth = (dth < gape) & (rr > Rb * .2)
    body = (rr < Rb) & ~mouth
    cl, cd, cp = K.voronoi(K.sites(seed + 6, 4.2, .95))
    ch = K.hash01(cl, seed + 7)
    kind = K.fhash(i, j, seed + 8)
    fam = np.array([[.55, 1., .15], [.1, .85, .95], [1., .25, .6]], F32)[np.minimum((kind * 3).astype(np.int32), 2)]
    cells = fam * (.72 + .5 * ch)[..., None] * (.75 + .4 * np.clip(1 - rr / Rb, 0, 1))[..., None]
    cellwall = K.near(K.edge_distance(cl), .6) * body
    cili = (rr > Rb) & (rr < Rb + 4.5) & ~mouth & (np.cos(th * np.round(Rb * 3.2)) > .2)
    cili_t = np.clip(1 - (rr - Rb) / 4.5, 0, 1) * cili
    pile = (K.fhash(i, j, seed + 9) < .3) & (np.hypot(du - Rb * 1.6, dv) < 5.5)
    piles = pile & (ch > .3)
    bg = K.ramp(K.unit(K.fbm(seed + 10, (5, 10, 40), .6)), ['2a0a14', '4a1220', '6e1e2c'])
    col = np.where(body[..., None], cells * (1 - .35 * cellwall)[..., None], bg)
    col = K.mix(col, np.array([.95, 1., .9], F32), cili_t * .85)
    col = np.where(piles[..., None], np.array([1., .85, .35], F32) * (.6 + .5 * ch)[..., None], col)
    col = _dither(col, seed + 11)
    tier = K.tiers(ch)
    M = np.where(body, 120 + 70 * tier, 12).astype(F32)
    Rr = np.where(body, 40 + 50 * tier + 40 * cellwall, 205).astype(F32)
    C = np.where(body, 16 + 30 * tier, 230).astype(F32)
    M, Rr, C = _over(M, Rr, C, cili_t, 210, 30, 40)
    M = np.where(piles, 240, M); Rr = np.where(piles, 30, Rr)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=1., cc_lo=16., cc_hi=255.)
    return K.pack(col, M, Rr, C)


# ============================================================ FERMION FOUNDRY
def fermion_foundry(seed=42):
    """A bubble chamber in a foundry: collision vertices spray tracks that curl
    into tightening spirals in the magnetic field, V-shaped decays, fiducial
    crosses and bubble speckle. v2: a glowing oxblood furnace ground with
    thicker tracks coloured by momentum (negatives cyan to aqua-white, positives
    orange to white-gold); the tracks are polished metal on a matte ground, so
    the spec is the colour-opposite of the paint."""
    r = K.rng(seed)
    x, y = K.xy()
    trk = np.zeros((N, N, 3), np.uint8); cov = np.zeros((N, N), np.uint8)
    for (vx, vy) in K.sites(seed + 1, 112, .95):
        cv2.circle(cov, (int(vx * 16), int(vy * 16)), 4 * 16, 255, -1, cv2.LINE_AA, 4)
        cv2.circle(trk, (int(vx * 16), int(vy * 16)), 4 * 16, (255, 244, 225), -1, cv2.LINE_AA, 4)
        for k in range(int(r.integers(4, 9))):
            q = 1 if r.random() < .5 else -1
            a = r.uniform(0, 6.28); px, py = float(vx), float(vy)
            c0 = r.uniform(.004, .03); curv = c0 * q
            L = r.uniform(90, 280); pts = [(px, py)]
            for s in range(int(L / 3.)):
                a += curv * 3.; curv *= 1.012
                px += math.cos(a) * 3.; py += math.sin(a) * 3.; pts.append((px, py))
                if abs(curv) > .35:
                    break
            pm = 1. - (c0 - .004) / .026
            c = (255, int(90 + 110 * pm), int(20 + 70 * pm)) if q > 0 else (int(20 + 50 * pm), int(130 + 100 * pm), 255)
            pp = np.round(np.array(pts) * 16).astype(np.int32)
            cv2.polylines(trk, [pp], False, c, 2, cv2.LINE_AA, 4)
            cv2.polylines(cov, [pp], False, 255, 2, cv2.LINE_AA, 4)
            if r.random() < .3:
                j = int(r.integers(len(pts) // 3, len(pts))); cx_, cy_ = pts[j]
                for sgn in (-1, 1):
                    ln_ = r.uniform(25, 60)
                    e = (cx_ + math.cos(a + sgn * .4) * ln_, cy_ + math.sin(a + sgn * .4) * ln_)
                    p2 = np.round(np.array([(cx_, cy_), e]) * 16).astype(np.int32)
                    cv2.polylines(trk, [p2], False, c, 2, cv2.LINE_AA, 4)
                    cv2.polylines(cov, [p2], False, 255, 2, cv2.LINE_AA, 4)
    covf = cov.astype(F32) / 255
    trkf = trk.astype(F32) / 255
    g = K.frac(x / F32(128.)); h = K.frac(y / F32(128.))
    fid = (K.near(np.abs(g - .5) * 128, .6) * K.near(np.abs(h - .5) * 128, 5)) + (K.near(np.abs(h - .5) * 128, .6) * K.near(np.abs(g - .5) * 128, 5))
    bub = (K.noise(seed + 2, 900, interp=cv2.INTER_NEAREST) > 2.15).astype(F32)
    heat = K.unit(K.fbm(seed + 4, (3, 6, 12, 24), .55))
    col = K.ramp(heat, ['1a0508', '3a0c12', '5e1418', '8a2216'])
    glow = cv2.GaussianBlur(trkf, (0, 0), 2.2) * F32(.55)
    col = col * (1 - covf)[..., None] + trkf
    col += glow * F32(.7)
    K.addc(col, fid * .5 + bub * .3, (1., .9, .8))
    col = _dither(col, seed + 5)
    gl = np.clip(glow.max(2), 0, 1)
    M = 12 + 25 * heat
    Rr = 200 - 60 * heat
    C = 230 - 30 * heat
    M, Rr, C = _over(M, Rr, C, gl * .7, 200, 60, 60)
    M, Rr, C = _over(M, Rr, C, covf, 255, 16, 16)
    M, Rr, C = _over(M, Rr, C, bub, 0, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=1., cc_lo=16., cc_hi=255.)
    return K.pack(col, M, Rr, C)


# ======================================================= CHROMATIC CENTRIFUGE
def chromatic_centrifuge(seed=42):
    """A lab full of rotors: lathe-turned metal discs, each carrying a ring of
    sample tubes whose contents have spun into density-gradient bands of
    colour - pellet at the rim, rainbow layers toward the axis - with
    centrifugal smear spirals and a polished hub."""
    x, y = K.xy()
    lab, sd, sp = K.voronoi(K.sites(seed + 1, 62, .8))
    n = len(sp)
    R = (24 + 9 * _per(n, seed + 2))[lab]
    ntube = (8 + (_per(n, seed + 3) * 8).astype(np.int32))[lab].astype(F32)
    rot0 = (_per(n, seed + 4) * K.TAU)[lab]
    dx, dy = K.cell_local(lab, sp, x, y)
    th = np.arctan2(dy, dx) + rot0
    rn = sd / R
    disc = rn < 1
    lathe = .5 + .5 * np.sin(sd * F32(K.TAU / 4.5))
    sector = K.frac(th / F32(K.TAU) * ntube)
    tw = np.abs(sector - .5) * F32(K.TAU) / ntube * sd
    tube = disc & (rn > .38) & (rn < .9) & (tw < R * .09)
    wall = disc & (rn > .36) & (rn < .92) & (np.abs(tw - R * .09) < 1.)
    grad_ = np.clip((rn - .38) / .52, 0, 1)
    hue0 = K.unit(K.fbm(seed + 11, (3, 6), .5)) * 1.1 + _per(n, seed + 5)[lab] * .2
    layers = np.floor(grad_ * 7) / 7
    tubec = _hue(hue0 + layers * .55 + .02 * K.noise(seed + 6, 90), .85, .45 + .55 * (1 - grad_ * .6))
    pellet = grad_ > .9
    tubec = np.where(pellet[..., None], np.array([.35, .02, .05], F32), tubec)
    smear = K.near(np.abs(K.frac(th / F32(K.TAU) * 3 + rn * 2.5) - .5), .06, .05) * disc * (rn > .9) * .6
    metal = K.ramp(np.clip(.15 + .5 * lathe * (1 - rn * .3), 0, 1), ['181a22', '363c4a', '6e7686', 'b8c0d0'])
    hub = K.near(sd, R * .16) + K.near(np.abs(sd - R * .24), 1.)
    col = K.ramp(K.unit(K.fbm(seed + 7, (4, 8, 32), .6)), ['0c0e14', '161a24', '1e2432'])
    anod = K.hue_rgb(hue0 * .6 + .55, .7, 1.)
    col = np.where(disc[..., None], metal * (anod * .9 + .15), col)
    col = col + smear[..., None] * _hue(hue0 + .3, .6, 1.)
    col = np.where(tube[..., None], tubec, col)
    col = np.where(wall[..., None], np.array([.85, .9, .95], F32), col)
    col = K.mix(col, np.array([.95, .96, 1.], F32), np.clip(hub, 0, 1) * disc)
    col = col * (1 - .6 * K.near(np.abs(rn - 1) * R, 1.2))[..., None]
    col = _dither(col, seed + 8)
    tier = K.tiers(K.fhash(layers * 7, lab.astype(F32), seed + 9))
    M = np.where(disc, 240 - 40 * lathe, 40)
    Rr = np.where(disc, 30 + 50 * lathe, 200)
    C = np.where(disc, 200, 240)
    M = np.where(tube, 20 + 40 * tier, M); Rr = np.where(tube, 20 + 30 * grad_, Rr); C = np.where(tube, 16, C)
    M, Rr, C = _over(M, Rr, C, np.clip(hub, 0, 1) * disc, 255, 16, 40)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)
