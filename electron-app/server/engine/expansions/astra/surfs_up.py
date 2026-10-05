"""ASTRA SURFS UP — ocean and surf-culture constructions (ten).

SPB-105 / ASTRA-R2 2026-09-27 (Claude). Lane arc: THE WHOLE CAR IS THE OCEAN
AT ONE SCALE — every card is a real surf/sea phenomenon (breaking barrels,
reef, foam lace, wax, lava break, bioluminescence, sea glass...) built from
its own geometry as a dense 8-32 px field, wet where water is wet and matte
where wax, foam and frosted glass are matte.

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


# =========================================================== PIPELINE ROYALE
def pipeline_royale(seed=42):
    """Rows of peeling surf barrels across the car: each swell line rises
    from navy trough through turquoise face to a glassy green lip that
    throws white foam; where the wave barrels, a dark tube opens under the
    lip. Fine ripple facets on the faces, spray above every lip."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 40, 5)
    u, v = K.rot(wx, wy, F32(-.35))
    H = F32(44.)
    j = np.floor(v / H)
    t = v / H - j
    ph = K.fhash(j, None, seed) * 40
    c = .30 + .09 * np.sin(u * F32(K.TAU / 150.) + ph) + .04 * np.sin(u * F32(K.TAU / 47.) + ph * 2)
    face = np.clip((t - c) / (1 - c), 0, 1)
    back = t < c
    seg = np.floor(u / 90.)
    barrel = K.fhash(j, seg, seed + 1) < .45
    uc = (seg + .5) * 90 + (K.fhash(j, seg, seed + 2) - .5) * 30
    ex = (u - uc) / 26.; ey = (t - (c + .20)) * H / (H * .16)
    tube = (ex * ex + ey * ey < 1) & barrel
    tube_t = np.clip(1 - (ex * ex + ey * ey), 0, 1) * tube
    rip = K.noise(seed + 3, 260)
    ripl = K.near(np.abs(K.frac(rip * 3 + face * 4) - .5), .1, .08)
    water = K.ramp(np.clip(1 - face * 1.05, 0, 1), ['061a3a', '0a3a6a', '0c7a9a', '12b8b0', '5af0d0', 'c8fff0'],
                   [0, .25, .5, .7, .88, 1.])
    water = water * (1 + .10 * ripl)[..., None]
    backc = K.ramp(np.clip(t / np.maximum(c, .05), 0, 1), ['e8f8ff', '7ad0e0', '1a6a90'])
    col = np.where(back[..., None], backc, water)
    lipd = np.abs(t - c) * H
    lip = K.near(lipd, 2.2)
    spray = (K.noise(seed + 4, 700, interp=cv2.INTER_NEAREST) > 1.7) & (t < c) & (t > c - .18)
    col = K.mix(col, np.array([.96, .99, 1.], F32), np.clip(lip + spray * .9, 0, 1))
    tubec = K.ramp(tube_t, ['0a3050', '0a1a30', '020810'])
    col = np.where(tube[..., None], tubec * (1 - .4 * K.near(1 - tube_t, .08, .1))[..., None], col)
    foam_back = back & (K.noise(seed + 5, 400) > .6)
    col = np.where(foam_back[..., None], col * .6 + .4, col)
    tier = K.tiers(K.fhash(j, seg, seed + 6))
    M = 60 + 70 * face + 20 * tier
    Rr = 18 + 20 * (1 - face) + 14 * ripl
    C = np.full((N, N), 16., F32)
    wh = np.clip(lip + spray + foam_back * .8, 0, 1)
    M, Rr, C = _over(M, Rr, C, wh, 0, 215, 230)
    M, Rr, C = _over(M, Rr, C, tube.astype(F32), 20, 60, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(col, M, Rr, C)


# ============================================================ REEF CATHEDRAL
def reef_cathedral(seed=42):
    """Brain-coral naves: a reaction-diffusion labyrinth (the real maths of
    brain-coral meanders) raised into rounded coral ridges in salmon, coral
    and peach over teal-shadow grooves; star polyps bloom along the ridges,
    darker coral heads vary the nave, and sunlit caustics ripple over it."""
    x, y = K.xy()
    f = K.turing(seed + 1, 17., 16)
    f = K.blur(f, 1.)
    ridge = K.sstep(-.6, .2, f)
    hgt = ridge * 4
    sh = K.relief(K.blur(hgt, 1.2), 1.2)
    tone = K.unit(K.fbm(seed + 3, (5, 10, 20, 40), .6))
    coral = K.ramp(np.clip(.35 + .45 * tone + .2 * np.clip(sh, -1, 1), 0, 1), ['a01830', 'e8402e', 'ff7a3a', 'ffb86a', 'fff0c0'])
    valley = K.ramp(tone, ['160410', '2a0818', '420e26'])
    col = K.mix(valley, coral, ridge) * (.78 + .38 * np.clip(sh, -1, 1))[..., None]
    pl, pd, pp = K.voronoi(K.sites(seed + 4, 20, .95))
    pon = (_per(len(pp), seed + 5)[pl] < .45) & (ridge > .75)
    dx, dy = K.cell_local(pl, pp, x, y)
    a = np.arctan2(dy, dx)
    pr = 4.6 * (.7 + .3 * np.cos(a * 8))
    polyp = K.near(pd, pr) * pon
    pcore = K.near(pd, 1.5) * pon
    pc = np.array([[.72, .5, 1.], [1., .9, .3], [.4, 1., .8]], F32)[(_per(len(pp), seed + 6) * 3).astype(np.int32)][pl]
    col = K.mix(col, pc * (.6 + .5 * (1 - pd / 5.))[..., None], polyp)
    col = K.mix(col, np.array([1., 1., .9], F32), pcore)
    caus = K.sstep(.86, .97, K.ridged(seed + 7, (48, 96), .6))
    col = col + caus[..., None] * np.array([.30, .40, .36], F32)
    M = 10 + 40 * caus
    Rr = 90 + 120 * (1 - ridge) - 40 * np.clip(sh, 0, 1) - 50 * caus
    C = 40 + 180 * (1 - ridge)
    M, Rr, C = _over(M, Rr, C, polyp, 40, 30, 16)
    M, Rr, C = _over(M, Rr, C, pcore, 200, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================ TIDAL LACEWORK
def tidal_lace(seed=42):
    """The lace a retreating wave leaves on the sand: a foam net of bubble walls
    torn open by a hidden dissipation field over golden-orange sand and water
    that deepens from aqua to cobalt-indigo. v2: sand and water are complements
    (orange vs blue), the lace is thicker and pure white so it survives at
    distance, water is polished and sand/foam are matte, so the spec is the
    colour-opposite of the paint."""
    x, y = K.xy()
    bl, bd, bp = K.voronoi(K.sites(seed + 1, 30, .95))
    be = K.edge_distance(bl)
    sl, sd, sp = K.voronoi(K.sites(seed + 2, 10, .95))
    se = K.edge_distance(sl)
    keep = K.unit(K.fbm(seed + 3, (6, 12, 24, 48), .6))
    wall_big = K.near(be, 1.6 + 1.4 * keep)
    wall_small = K.near(se, .6 + .5 * keep) * K.sstep(.62, .88, keep)
    torn = K.sstep(.12, .3, keep) * (K.noise(seed + 11, 90) > -.9)
    foam = np.clip(wall_big + wall_small, 0, 1) * torn
    depth = K.unit(K.fbm(seed + 4, (5, 10, 20), .55))
    sea = K.ramp(depth, ['f4b040', 'f08424', '5ae0b8', '12d0d0', '0a80d8', '101a88'], [0, .28, .35, .5, .75, 1.])
    cau = K.sstep(.82, .96, K.ridged(seed + 5, (48, 96), .6)) * K.sstep(.3, .6, depth)
    K.addc(sea, cau, (.22, .22, .22))
    shadow = K.blur(foam, 2.) * .4
    col = sea * (1 - shadow)[..., None]
    col = K.mix(col, np.array([1., 1., 1.], F32), foam)
    tier = K.tiers(K.fhash(bl.astype(F32), None, seed))
    sandw = 1 - K.sstep(.24, .37, depth)
    M = (190 + 40 * depth) * (1 - sandw) + 10 * sandw + 50 * cau
    Rr = (30 + 30 * (1 - depth) - 10 * cau) * (1 - sandw) + 200 * sandw
    C = (16 + 40 * (1 - depth)) * (1 - sandw) + 230 * sandw
    M, Rr, C = _over(M, Rr, C, foam, 0, 170 + 40 * tier, 215)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=1., cc_lo=16., cc_hi=255.)
    return K.pack(col, M, Rr, C)


# ========================================================== SURF WAX RITUAL
def surf_wax_ritual(seed=42):
    """Fresh wax on a board: big domed wax beads rubbed up in circles over a
    tropical basecoat that glows in every valley between them, a fine comb
    crosshatch scratched through the bumps in patches, and grains of sand."""
    x, y = K.xy()
    wl, wd, wp = K.voronoi(K.sites(seed + 2, 12, .9))
    n = len(wp)
    wr = (5.2 + 3.2 * _per(n, seed + 3))[wl]
    bead = np.clip(1 - (wd / wr) ** 2, 0, 1)
    dome = np.sqrt(bead)
    sh = K.relief(dome * 5, 1.)
    base_t = K.frac((x * .6 + y * .8) / F32(260.) + .35 * K.fbm(seed + 1, (5, 10), .5))
    basecoat = K.ramp(base_t, ['ff4a6a', 'ffa02a', 'ffe03a', '1ad0a8', '2a8aff', 'b04aff', 'ff4a6a'])
    wax = K.ramp(np.clip(.4 + .45 * dome + .15 * _per(n, seed + 4)[wl], 0, 1), ['c8b88c', 'e2d6b2', 'f2ead4', 'fffcf0'])
    wax = wax * (.7 + .45 * np.clip(sh + .35, 0, 1))[..., None]
    valley = 1 - K.sstep(.02, .22, bead)
    col = K.mix(wax, basecoat * .9, valley)
    ang = F32(.6)
    g1 = K.frac((x * np.cos(ang) + y * np.sin(ang)) / F32(10.) + .25 * K.noise(seed + 6, 20))
    g2 = K.frac((x * np.cos(-ang) + y * np.sin(-ang)) / F32(10.) + .25 * K.noise(seed + 7, 20))
    combed = K.sstep(.5, .62, K.unit(K.fbm(seed + 5, (6, 12, 24), .55)))
    comb = np.maximum(K.near(np.abs(g1 - .5) * 10, .7), K.near(np.abs(g2 - .5) * 10, .7)) * combed * (bead > .1)
    col = K.mix(col, basecoat * .75, comb * .85)
    sand = K.noise(seed + 8, 900, interp=cv2.INTER_NEAREST) > 2.
    col = np.where(sand[..., None], np.array([.9, .72, .4], F32), col)
    M = np.zeros((N, N), F32) + 10 * _per(n, seed + 9)[wl]
    Rr = 225 - 70 * dome - 40 * np.clip(sh, 0, 1)
    C = 235 - 50 * dome
    gl = np.clip(valley + comb * .85, 0, 1)
    M, Rr, C = _over(M, Rr, C, gl, 20, 22, 16)
    M = np.where(sand, 200, M); Rr = np.where(sand, 50, Rr)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8, mask=gl)
    return K.pack(col, M, Rr, C)


# =========================================================== WIPEOUT PAISLEY
def wipeout_paisley(seed=42):
    """Psychedelic surf paisley: hundreds of curled boteh teardrops at every
    size and angle, packed and overlapping, each nested with echo bands in
    60s surf colours, a beaded border, a hooked tail and an inner eye, over a
    micro-dot print ground."""
    r = K.rng(seed)
    x, y = K.xy()
    pts = K.sites(seed + 1, 46, .95)
    r.shuffle(pts)
    n = len(pts)
    R0 = r.uniform(12, 25, n).astype(F32); ang = r.uniform(0, K.TAU, n).astype(F32)
    mir = np.where(r.random(n) < .5, -1., 1.).astype(F32)
    # boteh outline in local frame: bulb at origin, tail sweeps to +u and hooks
    tt = np.linspace(0, 1, 60)
    th = tt * 2 * np.pi
    def outline(R):
        rr = R * (1 + 1.9 * ((1 + np.cos(th)) / 2) ** 5)
        cu = rr * np.cos(th); cv_ = rr * np.sin(th)
        cv_ = cv_ + 1.1 * R * (np.clip(cu / R - 1, 0, None) / 1.9) ** 2
        return cu, cv_
    ids = np.full((N, N), -1, np.int32)
    for i in range(n):
        cu, cv_ = outline(R0[i]); cv_ = cv_ * mir[i]
        ca, sa = np.cos(ang[i]), np.sin(ang[i])
        px = pts[i, 0] + cu * ca - cv_ * sa; py = pts[i, 1] + cu * sa + cv_ * ca
        cv2.fillPoly(ids, [np.round(np.stack([px, py], 1) * 16).astype(np.int32)], int(i), cv2.LINE_8, 4)
    k = np.maximum(ids, 0); on = ids >= 0
    u, v = K.id_local(ids, pts[:, 0], pts[:, 1], ang, x, y)
    v = v * mir[k]
    Rk = R0[k]
    v2 = v - 1.1 * Rk * (np.clip(u / Rk - 1, 0, None) / 1.9) ** 2
    rr = np.hypot(u, v2); th2 = np.arctan2(v2, u)
    s = rr / (Rk * (1 + 1.9 * ((1 + np.cos(th2)) / 2) ** 5))
    ed = K.edge_distance(ids)
    band = np.floor(np.clip(ed / np.maximum(Rk * .28, 2.5), 0, 5.99))
    pal = K.hexrgb('ff2a8a', 'ff8a1a', 'ffe030', '6aff3a', '1ad0e0', '8a3aff')
    reg = (K.unit(K.fbm(seed + 9, (3, 6), .5)) * 5.99).astype(np.int32)
    pid = (K.fhash(ids.astype(F32), None, seed + 2) * 2).astype(np.int32) + reg
    ci = (pid + band.astype(np.int32) * 2) % 6
    col = pal[ci]
    echo = K.near(np.abs(K.frac(ed / np.maximum(Rk * .28, 2.5)) - .5) * np.maximum(Rk * .28, 2.5), .5) * on
    col = col * (1 - .75 * echo)[..., None]
    beads = (np.cos(th2 * np.round(Rk * 1.3)) > .55) & (ed > 1.8) & (ed < 3.6)
    col = np.where((beads & on)[..., None], np.array([1., 1., .9], F32), col)
    eyed = np.hypot(u + Rk * .1, v)
    eye = K.near(eyed, Rk * .34) * on
    col = K.mix(col, np.array([.08, .02, .12], F32), eye)
    col = K.mix(col, np.array([1., .95, .3], F32), K.near(eyed, Rk * .12) * on)
    outline_ = K.near(ed, 1.) * on
    col = col * (1 - .9 * outline_)[..., None]
    g1 = K.frac(x / F32(9.)); g2 = K.frac(y / F32(9.))
    dots = K.near(np.hypot(g1 - .5, g2 - .5) * 9, 1.4)
    ground = K.mix(np.array([.14, .04, .2], F32), np.array([.95, .35, .65], F32), dots * .75)
    col = np.where(on[..., None], col, ground)
    tier = K.tiers(K.fhash(ids.astype(F32), None, seed + 3))
    lumc = K.lum(col)
    M = np.where(on, 40 + 180 * (ci % 2) + 20 * tier, 20)
    Rr = np.where(on, 170 - 130 * lumc, 210 - 80 * dots)
    C = np.where(on, 16 + 40 * tier, 220)
    M, Rr, C = _over(M, Rr, C, outline_ + echo, 0, 235, 250)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================== KELP COUTURE
def kelp_couture(seed=42):
    """A kelp forest cut as couture: three depths of translucent ribbon
    blades with ruffled edges and gold midribs sway along the current,
    gas-float pearls at their bases, sequin glints where light hits."""
    r = K.rng(seed)
    x, y = K.xy()
    th = K.fbm(seed + 1, (2, 4), .5) * F32(np.pi * .9) - F32(np.pi / 2)
    col = K.ramp(K.unit(K.fbm(seed + 2, (3, 6, 12), .5)), ['02140e', '04261c', '083a2a'])
    Mm = np.full((N, N), 30., F32); Rm = np.full((N, N), 120., F32); Cm = np.full((N, N), 60., F32)
    pal = [['4a5a0a', '8a9a1a', 'c8c040'], ['0a5a2a', '1a9a4a', '5ae07a'], ['6a4a0a', 'b08a1a', 'f0d060']]
    steps = 18
    for layer in range(3):
        pts = K.sites(seed + 10 + layer, 44 + 10 * layer, .95).astype(np.float64)
        r.shuffle(pts)
        n = len(pts)
        L = r.uniform(80, 170, n); Wd = r.uniform(4, 8, n) * (1 + .3 * layer); ph = r.uniform(0, 6.28, n)
        P = pts.copy(); left = np.zeros((n, steps, 2)); right = np.zeros((n, steps, 2)); cen = np.zeros((n, steps, 2))
        for s in range(steps):
            ix = np.clip(P[:, 0], 0, N - 1).astype(np.int32); iy = np.clip(P[:, 1], 0, N - 1).astype(np.int32)
            a = th[iy, ix] + .35 * np.sin(s * .7 + ph)
            d = np.stack([np.cos(a), np.sin(a)], 1); nrm = np.stack([-d[:, 1], d[:, 0]], 1)
            w = (Wd * np.sin(np.pi * (s + .5) / steps) ** .6 * (1 + .25 * np.sin(s * 2.1 + ph)))[:, None]
            left[:, s] = P + nrm * w; right[:, s] = P - nrm * w; cen[:, s] = P
            P = P + d * (L / steps)[:, None]
        polys = np.round(np.concatenate([left, right[:, ::-1]], 1) * 16).astype(np.int32)
        ids = np.full((N, N), -1, np.int32)
        for i in range(n):
            cv2.fillPoly(ids, [polys[i]], int(i), cv2.LINE_8, 4)
        mid = np.zeros((N, N), np.uint8)
        cv2.polylines(mid, list(np.round(cen * 16).astype(np.int32)), False, 255, 1, cv2.LINE_AA, 4)
        on = ids >= 0
        ed = K.edge_distance(ids)
        across = np.clip(ed / 5., 0, 1)
        t = K.fhash(ids.astype(F32), None, seed + 20 + layer)
        blade = K.ramp(np.clip(.25 + .5 * t + .25 * across, 0, 1), pal[layer])
        rib = mid.astype(F32) / 255
        vein = K.near(np.abs(K.frac(ed / F32(3.)) - .5) * 3, .25) * .25
        sc = (1 - vein) * (.65 + .45 * across)
        blade *= sc[..., None]
        rr_, cc_ = np.nonzero(rib > .01)
        rw = (rib[rr_, cc_] * .85)[:, None]
        blade[rr_, cc_] = blade[rr_, cc_] * (1 - rw) + np.array([1., .85, .35], F32) * rw
        alpha = (.72 + .12 * layer) * on
        blade -= col
        blade *= alpha[..., None]
        col += blade
        tier = K.tiers(t)
        tgt = 20 + 40 * tier + 200 * rib; tgt -= Mm; tgt *= alpha; Mm += tgt
        tgt = 80 - 40 * across - 50 * rib + 20 * tier; tgt -= Rm; tgt *= alpha; Rm += tgt
        tgt = 56 - 40 * across; tgt -= Cm; tgt *= alpha; Cm += tgt
    fl, fd, fp = K.voronoi(K.sites(seed + 30, 70, .95))
    fon = (_per(len(fp), seed + 31) < .35)[fl]
    fr_ = (3 + 3 * _per(len(fp), seed + 32))[fl]
    flt = K.near(fd, fr_) * fon
    fh = K.relief(np.sqrt(np.clip(1 - (fd / fr_) ** 2, 0, 1)) * 4 * fon, 1.)
    col = K.mix(col, np.array([.8, .75, .45], F32) * (.7 + .5 * np.clip(fh + .4, 0, 1))[..., None], flt)
    seq = (K.noise(seed + 33, 800, interp=cv2.INTER_NEAREST) > 2.1) & (Mm > 40)
    col = np.where(seq[..., None], np.array([1., .95, .7], F32), col)
    Mm, Rm, Cm = _over(Mm, Rm, Cm, flt, 90, 16, 16)
    Mm = np.where(seq, 255, Mm); Rm = np.where(seq, 16, Rm)
    Mm, Rm, Cm = K.enrich(np.asarray(Mm, F32).copy(), np.asarray(Rm, F32).copy(), np.asarray(Cm, F32).copy(), seed + 991)
    return K.pack(col, Mm, Rm, Cm)


# ======================================================== BOARDWALK PINLINES
def boardwalk_pinlines(seed=42):
    """A painted boardwalk: every plank a faded beach-hut colour (teal, coral,
    mustard, sky, cream, sea-green, dusty pink) with grain, wear-through to bare
    wood, nails and dark gaps; each plank is coach-lined with a double pinline in
    its COMPLEMENT colour, and cream sign-painter clothoid flourishes curl over
    the boards. v2: warm planks are matte, cool planks satin, pinlines and
    flourishes are metallic leaf, so the spec is the colour-opposite of the paint."""
    r = K.rng(seed)
    x, y = K.xy()
    a = F32(.52)
    u, v = K.rot(x, y, a)
    Wp = F32(26.)
    pj = np.floor(v / Wp)
    pv = v - pj * Wp
    Lp = 150 + 130 * K.fhash(pj, None, seed)
    us = u + K.fhash(pj, None, seed + 1) * 300
    pi = np.floor(us / Lp)
    pu = us - pi * Lp
    gap = np.clip(K.near(np.minimum(pv, Wp - pv), .9) + K.near(np.minimum(pu, Lp - pu), .9), 0, 1)
    gn = K.noise(seed + 2, 60) * 16 + K.noise(seed + 3, 200) * 3
    grain = K.near(np.abs(K.frac((pv + gn + K.fhash(pj, pi, seed + 4) * 30) / F32(5.)) - .5) * 5, .6)
    pid = K.fhash(pj, pi, seed + 5)
    cidx = np.minimum(np.floor(pid * 7).astype(np.int32), 6)
    pal = K.hexrgb('12b0a8', 'f0604a', 'f0b830', '58b8f0', 'f4ecd0', '3ec890', 'e8809a')
    lcol = K.hexrgb('ff7040', '10c8c0', '2848d8', 'ffb020', 'd82030', 'e02a90', '108890')
    warm = np.array([0, 1, 1, 0, 1, 0, 1], F32)[cidx]
    paint = pal[cidx] * (.78 + .3 * K.fhash(pj, pi, seed + 9))[..., None]
    wear = K.sstep(.05, .5, K.noise(seed + 7, 220) * .6 + .7 * grain - .25)
    bare = K.hexrgb('cbb894')[0]
    col = K.mix(paint * (1 - .16 * grain)[..., None], bare * (.85 + .2 * grain)[..., None], wear * .45)
    nd = np.minimum(np.hypot(pu - 7, pv - 5), np.hypot(pu - 7, pv - (Wp - 5)))
    nd = np.minimum(nd, np.minimum(np.hypot(pu - (Lp - 7), pv - 5), np.hypot(pu - (Lp - 7), pv - (Wp - 5))))
    nail = K.near(nd, 1.8)
    inset = np.minimum(np.minimum(pv, Wp - pv), np.minimum(pu, Lp - pu))
    coach = (K.near(np.abs(inset - 3.6), .8) + K.near(np.abs(inset - 6.6), .6)) * (K.fhash(pj, pi, seed + 7) < .86)
    coach = np.clip(coach, 0, 1) * (1 - .6 * wear)
    col = col * (1 - .85 * gap)[..., None]
    col = K.mix(col, np.array([.22, .21, .23], F32), nail)
    col = K.mix(col, lcol[cidx], coach)
    rgba = np.zeros((N, N, 4), np.uint8)
    pal8 = [(250, 240, 215, 255), (255, 196, 40, 255), (255, 255, 255, 255)]
    unit = []
    for k1, k2, L in ((.6, 5.5, 34), (-.4, 4.2, 24), (1.4, 6.5, 18)):
        for side in (1, -1):
            c = K.clothoid((0., 0.), 0., L, side * k1, side * k2, 30)
            unit.append(c)
            unit.append(np.stack([-c[:, 0], c[:, 1]], 1))
    unit = np.asarray(unit)
    for (cx, cy) in K.sites(seed + 8, 112, .95):
        rot_ = r.uniform(0, 6.28); ci = int(r.integers(0, 3)); s = r.uniform(.8, 1.4)
        cr, sr = math.cos(rot_) * s, math.sin(rot_) * s
        pp = np.round(np.stack([cx + unit[..., 0] * cr - unit[..., 1] * sr, cy + unit[..., 0] * sr + unit[..., 1] * cr], -1) * 16).astype(np.int32)
        cv2.polylines(rgba, list(pp), False, pal8[ci], 2, cv2.LINE_AA, 4)
    inkf = rgba[..., 3].astype(F32) / 255
    kf = cv2.dilate(inkf, np.ones((3, 3), np.uint8))
    col = col * (1 - .8 * kf * (1 - inkf))[..., None]
    col = col * (1 - inkf)[..., None] + rgba[..., :3].astype(F32) * F32(1. / 255)
    tier = K.tiers(pid)
    M = np.where(warm > .5, 10 * tier, 150 + 30 * tier)
    C = np.where(warm > .5, 235 - 10 * tier, 130 - 20 * tier)
    M = M * (1 - nail) + 220 * nail; C = C * (1 - nail) + 200 * nail
    en = np.clip(coach + inkf, 0, 1)
    M = M * (1 - en) + 235 * en; C = C * (1 - en) + 50 * en
    M = M * (1 - gap) + 10 * gap; C = C * (1 - gap) + 235 * gap
    Rr = K.r_from_luma(col, M, C)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================ VOLCANIC BREAK
def volcanic_break(seed=42):
    """A surf break over basalt: near-hexagonal columns seen from above, each
    top its own height with a bevel and fracture; lava glows up through a
    hidden set of joints, teal tide floods the low columns and white foam
    rings the rock at the waterline."""
    x, y = K.xy()
    cl, cd, cp = K.voronoi(K.sites(seed + 1, 27, .35))
    ce = K.edge_distance(cl)
    n = len(cp)
    ci = np.clip(cp.astype(np.int32), 0, N - 1)
    field = K.unit(K.fbm(seed + 3, (10, 20, 40), .6))
    hgt = (.35 * _per(n, seed + 2) + .65 * field[ci[:, 1], ci[:, 0]])[cl]
    top = K.ramp(np.clip(.2 + .5 * _per(n, seed + 4)[cl] + .15 * K.noise(seed + 5, 300), 0, 1), ['0a0a0c', '18181c', '28262a', '3e3a38'])
    bev = K.sstep(0, 3.5, ce)
    sh = K.relief(bev * 3, 1.)
    col = top * (.7 + .45 * np.clip(sh + .5, 0, 1))[..., None]
    crack = K.near(np.abs(K.noise(seed + 6, 150)), .03, .03) * (ce > 3)
    col = col * (1 - .6 * crack)[..., None]
    wl = F32(.40)
    water = (hgt < wl).astype(F32)
    depth = np.clip((wl - hgt) / .25, 0, 1)
    teal = K.ramp(depth, ['5ae0d0', '14a8b4', '06607e'])
    col = K.mix(col, teal * (.85 + .2 * K.near(np.abs(K.noise(seed + 10, 200)), .05, .05))[..., None], water * .85)
    shore = (np.abs(hgt - wl) < .06).astype(F32) * K.near(ce, 3.)
    col = K.mix(col, np.array([.95, 1., 1.], F32), shore * .9)
    lava_zone = K.sstep(.6, .72, K.unit(K.fbm(seed + 7, (10, 20, 40), .6))) * (1 - water)
    joint = K.near(ce, 1.4)
    lava = joint * lava_zone
    glow = np.clip(K.blur(lava, 2.5) * 2.2 + K.blur(lava, 8) * 1.4, 0, 1.5)
    col = col * (1 - joint * (1 - lava_zone) * .7)[..., None]
    col = col + glow[..., None] * np.array([1., .32, .04], F32) * .75
    lavac = K.ramp(np.clip(lava * .6 + glow * .4, 0, 1), ['600800', 'e03000', 'ff8a10', 'ffe070'])
    col = K.mix(col, lavac, np.clip(lava * 1.4, 0, 1))
    tier = K.tiers(_per(n, seed + 9)[cl])
    M = 60 + 40 * tier
    Rr = 150 + 60 * crack + 20 * tier - 40 * np.clip(sh, 0, 1)
    C = 180 + 40 * tier
    M, Rr, C = _over(M, Rr, C, water, 40, 20, 16)
    M, Rr, C = _over(M, Rr, C, shore, 0, 200, 220)
    M, Rr, C = _over(M, Rr, C, np.clip(lava * 1.4 + glow * .4, 0, 1), 230, 26, 60)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ========================================================== ABYSSAL LANTERNS
def abyssal_lanterns(seed=42):
    """The deep lit only by its animals: comb jellies with glowing ribbed bells
    and trailing tentacles, siphonophore chains of lights and drifting plankton.
    v2 (owner: colour that explodes with the spec): denser, bigger animals in
    amber / magenta / coral / ice over an INDIGO water column; the warm animals
    are matte gel, the cool water is polished, so the spec picture is the
    colour-opposite of the paint (the Chromatic Undertow mechanism)."""
    r = K.rng(seed)
    x, y = K.xy()
    wat = K.unit(K.fbm(seed + 1, (3, 6, 12, 24), .55))
    deep = K.ramp(wat, ['030a30', '06185a', '0a2a78', '0c4a86'])
    jl, jd, jp = K.voronoi(K.sites(seed + 2, 44, .95))
    n = len(jp)
    on = (_per(n, seed + 3) < .8)[jl]
    ang = (_per(n, seed + 4) * K.TAU)[jl]
    Rb = (10 + 11 * _per(n, seed + 5))[jl]
    hue = (_per(n, seed + 6) * 4).astype(np.int32)[jl]
    dx, dy = K.cell_local(jl, jp, x, y)
    u, v = K.rot(dx, dy, ang)
    bell_r = np.hypot(u / Rb, np.maximum(-v, 0) / (Rb * .85))
    bell = (bell_r < 1) & (v < Rb * .15) & on
    rib = .5 + .5 * np.cos(np.arctan2(-v, u) * 14)
    rim = K.near(np.abs(bell_r - 1) * Rb, 1.2) * (v < Rb * .15) * on
    tx = u / Rb * 4
    tent = K.near(np.abs(K.frac(tx + .5 + .15 * np.sin(v * .35 + tx)) - .5) * Rb / 4, .55) * (v > 0) * (v < Rb * 3) * (np.abs(u) < Rb * .9) * on
    tent = tent * np.exp(-v / (Rb * 1.6))
    glowc = np.array([[1., .62, .12], [1., .16, .66], [1., .34, .2], [.55, .95, 1.]], F32)[hue]
    em = np.clip(rim * 1.3 + bell * (.4 + .5 * rib) + tent * .9, 0, 1.4)
    halo = K.blur(em, 3.) * 1.6 + K.blur(em, 9) * .9
    col = deep + glowc * (em + halo * .6)[..., None]
    chain = np.zeros((N, N), np.uint8)
    for _ in range(140):
        p = r.uniform(0, N, 2); a = r.uniform(0, 6.28)
        for s in range(int(r.integers(10, 26))):
            a += r.normal(0, .25); p = p + np.array([np.cos(a), np.sin(a)]) * 7
            cv2.circle(chain, (int(p[0] * 16), int(p[1] * 16)), int(2.6 * 16), 255, -1, cv2.LINE_AA, 4)
    ch = chain.astype(F32) / 255
    K.addc(col, ch * 1.1 + K.blur(ch, 3.) * 1.3, (1., .82, .3))
    pk = (K.noise(seed + 7, 1000, interp=cv2.INTER_NEAREST) > 2.1).astype(F32)
    K.addc(col, (pk + K.blur(pk, 1.5) * 2) * .8, (.5, 1., .95))
    tier = K.tiers(_per(n, seed + 8)[jl])
    w = np.clip(em + ch + pk + halo * .35, 0, 1)
    M = (225 + 30 * wat) * (1 - w) + (8 * tier) * w
    Rr = (22 + 40 * (1 - wat)) * (1 - w) + (150 + 50 * tier) * w
    C = (16 + 40 * wat) * (1 - w) + (200 + 50 * tier) * w
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=1., cc_lo=16., cc_hi=255.)
    return K.pack(col, M, Rr, C)


# ==================================================== SEA GLASS CONFESSIONAL
def sea_glass_confessional(seed=42):
    """A confessional window of backlit sea glass: frosted pebbles in real
    sea-glass colours set in dark leading, pitted frost, glowing rounded rims
    and the shadow of a lattice screen. v2: saturated backlit glass in strong
    regional colour families; the warm glass (amber, ruby) is matte-frosted and
    the cool glass (kelly, cobalt, aqua) is polished, so the spec is the
    colour-opposite of the paint."""
    x, y = K.xy()
    gl, gd, gp = K.voronoi(K.sites(seed + 1, 31, .95))
    ge = K.edge_distance(gl)
    n = len(gp)
    q = _per(n, seed + 2)
    cum = np.cumsum([.22, .16, .16, .16, .14, .12, .04])
    ci = np.searchsorted(cum, q * cum[-1]).clip(0, 6)
    ci_ = np.clip(gp.astype(np.int32), 0, N - 1)
    regc = (K.unit(K.fbm(seed + 7, (3, 6), .5))[ci_[:, 1], ci_[:, 0]] * 3.99).astype(np.int32)
    ci = np.where(_per(n, seed + 8) < .72, np.array([0, 1, 3, 2])[regc], ci)
    pal = K.hexrgb('22c452', '2a48f0', '28e0d0', 'f2a01c', '90f0c4', 'e42a48', 'f4f8ff')
    warm = np.array([0, 0, 0, 1, 0, 1, 0], F32)
    base = pal[ci][gl]
    isw = warm[ci][gl]
    inset = F32(2.1)
    peb = K.sstep(inset - .5, inset + .5, ge)
    round_ = K.sstep(inset, inset + 6, ge)
    pit = K.noise(seed + 3, 420, interp=cv2.INTER_LINEAR)
    frost = .82 + .2 * (1 - round_) + .05 * pit
    glass = base * frost[..., None] * F32(1.12) + ((1 - round_) * .28 + .05)[..., None]
    lead = np.array([.04, .04, .06], F32) * (1 + .6 * K.near(np.abs(ge - 1.3), .5))[..., None]
    col = K.mix(lead, glass, peb)
    g1 = K.frac((x + y) / F32(64.)); g2 = K.frac((x - y) / F32(64.))
    lat = np.maximum(K.near(np.abs(g1 - .5) * 64, 3.), K.near(np.abs(g2 - .5) * 64, 3.))
    latz = K.sstep(.4, .55, K.unit(K.fbm(seed + 5, (4, 8), .5)))
    shade = K.blur(lat, 2.) * latz * .55
    col = col * (1 - shade)[..., None]
    lumc = K.lum(col)
    tier = K.tiers(_per(n, seed + 6)[gl])
    M = isw * (10 + 25 * tier) + (1 - isw) * (212 + 30 * tier)
    C = isw * 225 + (1 - isw) * (40 + 60 * (1 - round_))
    M = M * peb + 200 * (1 - peb); C = C * peb + 60 * (1 - peb)
    Rr = K.r_from_luma(col, M, C)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)
