"""ASTRA COLOR SHOXX — two-pigment flip constructions (ten).

SPB-105 / ASTRA-R2 2026-09-27 (Claude). Lane arc: EVERY CARD IS TWO COLOURS
FIGHTING FOR THE SAME CAR. Each finish interleaves two strongly contrasting
pigment populations at 4-16 px inside its own geometry: population A sits on a
matte dielectric (it carries the colour in broad daylight), population B sits
on a dull-coated metal (its colour comes back as tinted reflection under
lights / at night). The mechanism is the NIGHTSHIFT two-population law; the
geometry, pairing and material deck belong to each finish alone.

Every function: (seed) -> (paint HxWx3 float 0..1, spec HxWx3 float 0..255).
"""
import cv2
import numpy as np
from . import kit as K

N = K.N
F32 = np.float32


def _per(n, seed):
    return K.hash01(np.arange(n), seed)


def _deck(b, ta, tb, A, B):
    """Two-population material deck. b = weight of population B (metal).
    A/B = (M_lo, M_hi, R_lo, R_hi, C_lo, C_hi); ta/tb are 0..1 shade tiers."""
    lerp = lambda lo, hi, t: lo + (hi - lo) * t
    M = lerp(A[0], A[1], ta) * (1 - b) + lerp(B[0], B[1], tb) * b
    R = lerp(A[2], A[3], ta) * (1 - b) + lerp(B[2], B[3], tb) * b
    C = lerp(A[4], A[5], ta) * (1 - b) + lerp(B[4], B[5], tb) * b
    return M.astype(F32), R.astype(F32), C.astype(F32)


def _over(M, R, C, w, m, r, c):
    w = np.clip(w, 0, 1)
    return M * (1 - w) + m * w, R * (1 - w) + r * w, C * (1 - w) + c * w


# ============================================================== JANUS BLADES
def janus_blades(seed=42):
    """Dense sheaves of two-faced blades riding a flow field. Every blade is
    split down its spine: the scarlet face is matte lacquer, the cobalt face is
    brushed metal, so the car shows a different face to the sun and to the
    lights. A hidden field slides the split so whole regions lean red or blue.
    Chrome spines, dark heel collars, gunmetal gaps."""
    r = K.rng(seed)
    x, y = K.xy()
    theta = K.fbm(seed + 1, (2, 4, 8), .5) * F32(np.pi * 1.3)
    sel = K.unit(K.fbm(seed + 9, (3, 6), .5))
    pts = K.sites(seed + 2, 19, .95)
    r.shuffle(pts)
    n = len(pts)
    pi = np.clip(pts.astype(np.int32), 0, N - 1)
    ang = (theta[pi[:, 1], pi[:, 0]] + r.normal(0, .16, n)).astype(F32)
    L = r.uniform(36, 62, n).astype(F32); W = r.uniform(4.5, 7.5, n).astype(F32)
    off = ((sel[pi[:, 1], pi[:, 0]] - .5) * 1.5).astype(F32)       # split offset in half-widths
    tt = np.linspace(-.5, .5, 9)
    prof = np.clip(1 - (2 * tt) ** 2, 0, 1) ** .8
    d = np.stack([np.cos(ang), np.sin(ang)], 1); m = np.stack([-d[:, 1], d[:, 0]], 1)
    a1 = pts[:, None, :] + d[:, None, :] * (tt[None, :, None] * L[:, None, None]) + m[:, None, :] * (prof[None, :, None] * W[:, None, None])
    a2 = pts[:, None, :] + d[:, None, :] * (tt[::-1][None, :, None] * L[:, None, None]) - m[:, None, :] * (prof[::-1][None, :, None] * W[:, None, None])
    polys = np.concatenate([a1, a2], 1)
    ids = K.stamp_ids(polys)
    k = np.maximum(ids, 0)
    u, v = K.id_local(ids, pts[:, 0], pts[:, 1], ang, x, y)
    Lk, Wk = L[k], W[k]
    wprof = Wk * np.clip(1 - (2 * u / Lk) ** 2, 1e-3, 1) ** .8
    dd = np.abs(v) - wprof
    on = ids >= 0
    gap = K.near(-dd, 1.1) * on
    s = np.clip(v / np.maximum(wprof, 1e-3), -1, 1)
    face = (s > off[k]).astype(F32)                       # 1 = scarlet lacquer (A)
    ta = K.tiers(K.hash01(k, seed + 3)); tb = K.tiers(K.hash01(k, seed + 4))
    along = np.clip(u / Lk + .5, 0, 1)
    grain = .5 + .5 * np.sin(v * F32(K.TAU / 2.1) + K.hash01(k, seed + 5) * 6)
    scar = K.ramp(np.clip(.45 + .35 * ta + .2 * (1 - np.abs(s)), 0, 1), ['5a0408', 'b00a18', 'ff2030', 'ff7050', 'ffc0a0'])
    cob = K.ramp(np.clip(.05 + .4 * tb + .25 * along, 0, 1), ['01061e', '041870', '1244d0', '4a80ff', 'b0ccff'])
    cob *= (.85 + .22 * grain)[..., None]
    col = K.mix(cob, scar, face)
    spine = K.near(np.abs(s - off[k]) * wprof, .6) * on
    heel = (u < -Lk / 2 + 6) * on
    col = K.mix(col, np.array([.95, .95, 1.], F32), spine * .9)
    col = np.where(heel[..., None], col * .45, col)
    gm = K.ramp(K.unit(K.noise(seed + 6, 300)) * .6 + .2, ['07080c', '14161e', '262a36'])
    col = np.where(on[..., None], col * (1 - .85 * gap)[..., None], gm)
    M, Rr, C = _deck(1 - face, ta, tb, (0, 22, 160, 215, 205, 255), (238, 255, 26, 74, 225, 255))
    Rr = Rr + (1 - face) * (grain - .5) * 24
    M, Rr, C = _over(M, Rr, C, spine, 255, 16, 16)
    M, Rr, C = _over(M, Rr, C, gap + heel * .6, 40, 34, 60)
    M = np.where(on, M, 90); Rr = np.where(on, Rr, 40); C = np.where(on, C, 120)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ========================================================= CHROMATIC UNDERTOW
def scarlet_undertow(seed=42):
    """Rip-current bands: a drifting stream function bent by hundreds of point
    vortices curls into hooks and eddies everywhere. Bands alternate turquoise
    metal (thin-film drifting cyan->blue) and vermilion enamel with a duty
    cycle that a hidden undertow field pushes between the two colours; ink
    separators and pale eddy lips at every vortex core."""
    r = K.rng(seed)
    x, y = K.xy()
    n = 512
    ys, xs = np.mgrid[:n, :n].astype(F32) * (N / n) + N / n / 2
    vort = K.sites(seed + 1, 96, .95)
    gam = r.choice([-1., 1.], len(vort)) * r.uniform(14, 30, len(vort))
    psi = K.field_conv(vort, gam, lambda dx, dy: np.log(dx * dx + dy * dy + 90.), n)
    psi = cv2.resize(psi, (N, N), interpolation=cv2.INTER_CUBIC)
    a = F32(.45)
    psi = psi + (y * np.cos(a) - x * np.sin(a)) * .45 + 20 * K.noise(seed + 2, 10)
    sp2 = F32(18.)
    s = psi / sp2
    fr = s - np.floor(s)
    duty = .3 + .4 * K.unit(K.fbm(seed + 5, (3, 6), .5))
    b = (fr < duty).astype(F32)                          # 1 = turquoise metal (B)
    gx, gy = K.grad(psi)
    gs = np.sqrt(gx * gx + gy * gy) / sp2 + F32(.02)
    dl = np.minimum(np.minimum(fr, 1 - fr), np.abs(fr - duty)) / gs
    line = K.near(dl, .55) * np.clip(1.6 - gs * 7, 0, 1)
    pos = np.where(b > 0, fr / duty, (fr - duty) / (1 - duty))
    tube = np.sin(F32(np.pi) * np.clip(pos, 0, 1))
    q = np.floor(s).astype(np.int32)
    ta = K.tiers(K.hash01(q, seed + 3)); tb = K.tiers(K.hash01(q, seed + 4))
    film = K.thin_film(q.astype(F32) * .07 + pos * .12 + .45, .9, .55)
    turq = K.ramp(np.clip(.2 + .45 * tb + .35 * tube, 0, 1), ['013a3a', '038a8a', '10d0c8', '70f8f0', 'd8fffc'])
    turq = K.mix(turq, np.clip(turq * film * 1.6, 0, 1), .35)
    verm = K.ramp(np.clip(.25 + .4 * ta + .35 * tube, 0, 1), ['4a0a02', 'a01a06', 'f0400e', 'ff8a50', 'ffd0b0'])
    col = K.mix(verm, turq, b)
    col = col * (.68 + .4 * tube)[..., None]
    col = col * (1 - .85 * line)[..., None]
    cores = np.zeros((N, N), F32)
    for (vx, vy), g in zip(vort, gam):
        cv2.circle(cores, (int(vx), int(vy)), int(2 + abs(g) * .18), 1., 1, cv2.LINE_AA)
    lip = np.clip(cores + K.blur(cores, 2.) * 1.5, 0, 1)
    col = K.mix(col, np.array([.95, 1., .96], F32), lip * .9)
    M, Rr, C = _deck(b, ta, tb, (0, 18, 140, 200, 190, 250), (232, 255, 30, 80, 215, 255))
    Rr = Rr + 30 * (1 - tube)
    M, Rr, C = _over(M, Rr, C, line, 20, 235, 255)
    M, Rr, C = _over(M, Rr, C, lip, 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ======================================================= SPECTRUM GUILLOTINE
def cobalt_guillotine(seed=42):
    """Shutter slats sliced by guillotine cuts: dozens of straight blades cut
    the car into polygon shards, every shard's slats are knocked to a new
    angle and offset, and each cut edge burns a thin spectrum. Slats alternate
    lime lacquer and amethyst metal, the duty sliding with a hidden field."""
    r = K.rng(seed)
    x, y = K.xy()
    angs = np.array([0, np.pi / 6, -np.pi / 6, np.pi / 3, -np.pi / 3, np.pi / 2])
    lines = [(r.uniform(0, N), r.uniform(0, N), angs[r.integers(0, 6)] + r.normal(0, .05), r.uniform(.001, 1.)) for _ in range(38)]
    code, dmin = K.lines_code(x, y, lines)
    rh = K.fhash(code, None, seed)
    sa = (np.floor(rh * 6) * F32(np.pi / 6) + (K.fhash(code, None, seed + 2) - .5) * .3).astype(F32)
    per = (10. + 6 * K.fhash(code, None, seed + 3)).astype(F32)
    w = (x * np.cos(sa) + y * np.sin(sa)) / per + K.fhash(code, None, seed + 4) * 7
    q = np.floor(w); fr = (w - q).astype(F32)
    duty = (.3 + .4 * K.unit(K.fbm(seed + 8, (3, 6), .5))).astype(F32)
    b = (fr < duty).astype(F32)
    pos = np.where(b > 0, fr / duty, (fr - duty) / (1 - duty))
    bev = np.sin(F32(np.pi) * np.clip(pos, 0, 1))
    ta = K.tiers(K.fhash(q, code, seed + 5)); tb = K.tiers(K.fhash(q, code, seed + 6))
    lime = K.ramp(np.clip(.35 + .4 * ta + .25 * bev, 0, 1), ['1c4200', '48a000', '8cf000', 'ccff3a', 'f0ffb0'])
    ame = K.ramp(np.clip(.1 + .45 * tb + .35 * bev, 0, 1), ['12022a', '380a78', '7424d0', 'b070ff', 'e4d0ff'])
    col = K.mix(lime, ame, b) * (.55 + .55 * bev)[..., None]
    col = col * (1 - .75 * K.near(np.minimum(np.minimum(fr, 1 - fr), np.abs(fr - duty)) * per, .6))[..., None]
    cut = K.near(dmin, 1.4)
    shadow = K.near(dmin, 4.) * (1 - cut)
    spec_hue = K.ramp((rh * 2) % 1, ['ff2040', 'ffa000', 'f0ff20', '20ff80', '20c0ff', 'a040ff', 'ff2040'])
    col = col * (1 - .55 * shadow)[..., None]
    col = K.mix(col, spec_hue, cut)
    M, Rr, C = _deck(b, ta, tb, (0, 24, 150, 210, 180, 245), (230, 255, 22, 66, 228, 255))
    Rr = Rr + 34 * (1 - bev)
    M, Rr, C = _over(M, Rr, C, cut, 255, 16, 16)
    M, Rr, C = _over(M, Rr, C, shadow * .6, 80, 200, 250)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ====================================================== CHROMATIC SWITCHYARD
def chromatic_switchyard(seed=42):
    """A rail switchyard drawn as a chromatic transit map across the whole
    car: parallel lanes of yellow-lacquer and cobalt-metal track with fine
    sleepers, 45-degree crossovers that switch lanes, yards rotated to their
    own headings, and white station roundels on black ballast."""
    x, y = K.xy()
    rl, _, rp = K.voronoi(K.sites(seed + 1, 360, .9))
    ya = (np.floor(_per(len(rp), seed) * 4) * np.pi / 4)[rl].astype(F32)
    u, v = K.rot(x, y, ya)
    T = F32(15.)
    q = np.floor(v / T)
    f = v - (q + F32(.5)) * T
    blk = np.floor(u / 130.)
    sw = K.fhash(q, blk + rl * 97., seed + 3) < .30
    u0 = blk * 130. + 20 + 50 * K.fhash(q, blk + rl * 97., seed + 4)
    ramp = np.clip((u - u0) / T, 0, 1) * sw                 # 45-degree crossover
    f2 = f - T * ramp
    lane = K.fhash(q, rl.astype(F32), seed + 5)
    b = (lane < .5).astype(F32)                             # 1 = cobalt metal lane
    bw = F32(4.6)
    tr1 = K.near(np.abs(f), bw)
    tr2 = K.near(np.abs(f2), bw) * sw * ((ramp > 0) & (ramp < 1))
    track = np.maximum(tr1, tr2)
    ff = np.where(tr2 > tr1, f2, f)
    slp = K.frac((u + 4096.) / F32(5.))
    sleeper = K.near(np.abs(slp - .5) * 5, .9) * K.near(np.abs(np.abs(ff) - 3.2), .7, 1.)
    groove = K.near(np.abs(ff), .55)
    tb = K.tiers(lane)
    yel = K.ramp(np.clip(.45 + .35 * tb + .2 * (1 - np.abs(ff) / bw), 0, 1), ['6a4a00', 'c89600', 'ffd000', 'fff07a'])
    blu = K.ramp(np.clip(.3 + .4 * tb + .3 * (1 - np.abs(ff) / bw), 0, 1), ['04124a', '0c38b0', '2a70ff', 'a8c8ff'])
    tc = K.mix(yel, blu, b)
    tc = tc * (1 - .5 * sleeper)[..., None] * (1 - .6 * groove)[..., None]
    gh = K.unit(K.noise(seed + 6, 520, interp=cv2.INTER_NEAREST))
    ballast = K.ramp(gh * .5 + .05, ['050507', '101014', '1e1e26'])
    col = K.mix(ballast, tc, track)
    stn_on = K.fhash(q, np.floor(u / 110.) + rl * 31., seed + 8) < .10
    su = K.frac(u / F32(110.)) * 110 - 55
    sd = np.hypot(su, f)
    ring = K.near(np.abs(sd - 5.), 1.3) * stn_on
    disc = K.near(sd, 4.) * stn_on
    col = K.mix(col, np.array([1., 1., 1.], F32), disc)
    col = K.mix(col, np.array([.02, .02, .03], F32), ring)
    M, Rr, C = _deck(b, tb, tb, (0, 18, 24, 60, 16, 40), (235, 255, 26, 70, 225, 255))
    Rr = Rr + 90 * sleeper + 60 * groove
    M = M * track + 30 * (1 - track); Rr = Rr * track + 225 * (1 - track); C = C * track + 250 * (1 - track)
    M, Rr, C = _over(M, Rr, C, disc, 0, 16, 16)
    M, Rr, C = _over(M, Rr, C, ring, 255, 30, 200)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ========================================================== BIPOLAR CYCLONE
def ruby_blue_cyclone(seed=42):
    """A weather map of small cyclones spinning both ways. Every storm is a
    logarithmic spiral of interleaved arms: clockwise storms lead with ruby
    lacquer, counter-clockwise storms with ice-blue metal; calm chrome eyes,
    dark wake lanes where neighbouring storms shear."""
    x, y = K.xy()
    lab, _, pts = K.voronoi(K.sites(seed + 1, 82, .95))
    n = len(pts)
    sg = np.where(_per(n, seed) < .5, -1., 1.).astype(F32)[lab]
    arms = (2 + (_per(n, seed + 1) * 3).astype(np.int32)).astype(F32)[lab]
    tight = (2.4 + 2.2 * _per(n, seed + 2))[lab]
    rot0 = (_per(n, seed + 3) * K.TAU)[lab]
    dx, dy = K.cell_local(lab, pts, x, y)
    rr = np.hypot(dx, dy) + F32(1e-3)
    th = np.arctan2(dy, dx)
    ph = (arms * th + sg * tight * np.log(rr + 2.) * 3.2 + rot0) / F32(K.TAU)
    fr = ph - np.floor(ph)
    lead = np.where(sg > 0, F32(.62), F32(.38))
    ruby = (fr < lead).astype(F32)
    ruby = np.where(sg > 0, ruby, 1 - ruby)
    b = 1 - ruby                                         # 1 = ice metal
    band = np.sin(F32(np.pi) * np.where(ruby > 0, fr / lead, (fr - lead) / (1 - lead)))
    ed = K.edge_distance(lab)
    wake = K.sstep(3.5, 0., ed)
    eye = K.near(rr, 3.5); eyer = K.near(np.abs(rr - 5.5), 1.)
    ta = K.tiers(K.hash01(lab, seed + 4)); tb = K.tiers(K.hash01(lab, seed + 5))
    rub = K.ramp(np.clip(.4 + .35 * band + .25 * ta, 0, 1), ['2a0008', '7a0018', 'd01036', 'ff4a6a', 'ffb0c0'])
    ice = K.ramp(np.clip(.35 + .4 * band + .25 * tb, 0, 1), ['062a4a', '1a70b0', '5ac0f0', 'b0ecff', 'f4ffff'])
    col = K.mix(rub, ice, b)
    col = col * (.62 + .5 * band)[..., None] * (.8 + .35 * np.exp(-rr / 30))[..., None]
    col = col * (1 - .8 * wake)[..., None]
    col = K.mix(col, np.array([1., 1., 1.], F32), np.clip(eye + eyer, 0, 1))
    M, Rr, C = _deck(b, ta, tb, (0, 20, 150, 205, 200, 255), (236, 255, 24, 70, 220, 255))
    Rr = Rr + 40 * (1 - band)
    M, Rr, C = _over(M, Rr, C, wake, 90, 230, 255)
    M, Rr, C = _over(M, Rr, C, np.clip(eye + eyer, 0, 1), 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# =========================================================== PRISM REBELLION
def prism_rebellion(seed=42):
    """A shattered prism wall: a warped triangular lattice where rebel cells
    split into finer triangles, each shard graded like light through glass,
    amber dielectric shards against violet metal shards, and every edge
    dispersed into red/green/blue fringes."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 22, 7)
    def tri(P):
        a = wx / P - wy / (P * F32(1.7320508))
        b2 = 2 * wy / (P * F32(1.7320508))
        ia, ib = np.floor(a), np.floor(b2)
        fa, fb = a - ia, b2 - ib
        up = (fa + fb) > 1
        e = np.minimum(np.minimum(fa, fb), np.abs(1 - fa - fb)) * P * F32(.866)
        return ia.astype(np.int32), ib.astype(np.int32), up.astype(np.int32), e.astype(F32)
    ia, ib, up, e = tri(F32(60.))
    reb = K.hash01(ia, ib, up, seed) < .32
    ja, jb, up2, e2 = tri(F32(30.))
    tid = np.where(reb, K.hash01(ja, jb, up2, seed + 1), K.hash01(ia, ib, up, seed + 2))
    e = np.where(reb, e2, e)
    ga = tid * F32(K.TAU)
    t = .5 + .5 * np.cos((x * np.cos(ga) + y * np.sin(ga)) * F32(K.TAU / 70.))
    lean = .12 + .7 * K.unit(K.fbm(seed + 7, (3, 6, 12), .5))
    b = (K.hash01((tid * 1e6).astype(np.int64), seed + 3) < lean).astype(F32)
    ta = K.tiers(K.hash01((tid * 1e6).astype(np.int64), seed + 4)); tb = K.tiers(K.hash01((tid * 1e6).astype(np.int64), seed + 5))
    amber = K.ramp(np.clip(t * .7 + .3 * ta, 0, 1), ['3a1200', '9a3a00', 'f08a00', 'ffc84a', 'fff4c0'])
    viol = K.ramp(np.clip(t * .7 + .3 * tb, 0, 1), ['14022e', '3a0a80', '7a2ee0', 'b87aff', 'ecd8ff'])
    col = K.mix(amber, viol, b)
    edge = K.near(e, 1.1)
    col = col * (1 - .75 * edge)[..., None]
    fr_ = np.roll(edge, 2, axis=1); fb_ = np.roll(edge, -2, axis=1); fg_ = np.roll(edge, 1, axis=0)
    fringe = np.dstack([fr_, fg_ * .8, fb_]) * .95
    col = np.clip(col + fringe * (1 - edge)[..., None], 0, 1)
    M, Rr, C = _deck(b, ta, tb, (0, 26, 130, 190, 170, 240), (225, 255, 20, 60, 225, 255))
    Rr = Rr + 70 * t
    fm = np.clip(fringe.max(2), 0, 1) * (1 - edge)
    M, Rr, C = _over(M, Rr, C, fm, 255, 16, 16)
    M, Rr, C = _over(M, Rr, C, edge, 30, 220, 255)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# =========================================================== DICHROIC RIVETS
def redshift_rivets(seed=42):
    """Studded dichroic armour: hex-packed domed rivet heads ride curving
    rows over dark gunmetal. Every head is dichroic glass-on-metal - its
    colour slides rose -> gold -> turquoise with the slope of the dome - and
    a hidden field sorts rose-lacquer heads from turquoise-metal heads, with
    a few empty sockets and polished washers."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 38, 4)
    u, v = K.rot(wx, wy, F32(.3))
    P = F32(15.)
    rh = P * F32(.866)
    best = np.full((N, N), 99., F32); bu = np.zeros((N, N), F32); bv = np.zeros((N, N), F32)
    row0 = np.floor(v / rh)
    for dr in (0, 1):
        rw = row0 + dr
        uu = u / P - K.frac(rw * F32(.5))
        cu = np.round(uu)
        du = (uu - cu) * P; dv = v - rw * rh
        d = np.hypot(du, dv)
        take = d < best
        best = np.where(take, d, best); bu = np.where(take, cu + rw * 1000., bu); bv = np.where(take, rw, bv)
    hid = K.fhash(bu, bv, seed + 2)
    lean = .15 + .7 * K.unit(K.fbm(seed + 3, (5, 10), .5))
    b = (hid < lean).astype(F32)                               # 1 = turquoise metal head
    empty = K.fhash(bu, bv, seed + 4) < .05
    Rv = F32(5.6)
    dome = np.clip(1 - (best / Rv) ** 2, 0, 1) * (~empty)
    head = K.near(best, Rv) * (~empty)
    washer = K.near(np.abs(best - 6.4), .8)
    socket = K.near(best, 4.2) * empty
    slope = np.sqrt(np.clip(1 - dome, 0, 1))
    hl = K.relief(np.sqrt(dome) * 6, 1.)
    ta = K.tiers(K.fhash(bu, bv, seed + 5)); tb = K.tiers(K.fhash(bu, bv, seed + 6))
    roseD = K.ramp(np.clip(slope * .85 + .1 * ta, 0, 1), ['ff80b8', 'ff2a7a', 'ff6a30', 'ffc040', '30d0c0'])
    turqD = K.ramp(np.clip(slope * .85 + .1 * tb, 0, 1), ['a0fff0', '10d8c8', '1080e0', '8040ff', 'ff3a90'])
    heads = K.mix(roseD, turqD, b)
    heads = heads * (.55 + .6 * np.clip(hl + .45, 0, 1.2))[..., None] + np.clip(hl - .35, 0, 1)[..., None] * 1.3
    plate = K.ramp(K.unit(K.noise(seed + 7, 160) * .5 + K.noise(seed + 8, 40) * .5) * .5 + .15, ['0a0c10', '181c24', '2a303c', '3a4250'])
    col = K.mix(plate, np.array([.55, .58, .64], F32) * (.8 + .4 * K.relief(washer * 2, 1.))[..., None], washer * (1 - head))
    col = col * (1 - .6 * K.near(np.abs(best - Rv - .8), .9) * (1 - washer))[..., None]
    col = K.mix(col, heads, head)
    col = K.mix(col, np.array([.01, .01, .015], F32), socket)
    M, Rr, C = _deck(b, ta, tb, (10, 40, 30, 70, 16, 40), (235, 255, 18, 50, 200, 250))
    Rr = Rr + 40 * slope
    base_M, base_R, base_C = 170., 150., 230.
    M = M * head + base_M * (1 - head); Rr = Rr * head + base_R * (1 - head); C = C * head + base_C * (1 - head)
    M, Rr, C = _over(M, Rr, C, washer * (1 - head), 250, 60, 120)
    M, Rr, C = _over(M, Rr, C, socket, 0, 250, 255)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ======================================================== SWITCHBLADE CHEVRON
def blueblood_chevron(seed=42):
    """Chevron parquet in bands of random height: V-stripes alternate cobalt
    metal and gold lacquer; switchblade columns flip open the other way with a
    chrome pivot pin, and every band edge is a polished bolster."""
    r = K.rng(seed)
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 26, 4)
    a = F32(.35)
    u, v = K.rot(wx, wy, a)
    brk = np.cumsum(r.uniform(40, 86, 400)) - 4000
    vi = np.searchsorted(brk, v)
    lo = brk[np.clip(vi - 1, 0, len(brk) - 1)].astype(F32); hi = brk[np.clip(vi, 0, len(brk) - 1)].astype(F32)
    vl = v - lo
    Hb = hi - lo
    P = (30 + 12 * K.hash01(vi, seed)).astype(F32)
    us = u + K.hash01(vi, seed + 1) * 200
    col_i = np.floor(us / P).astype(np.int32)
    cu = np.abs((us - col_i * P) - P / 2)
    flip = K.hash01(col_i, vi, seed + 2) < .14
    dirn = np.where(K.hash01(vi, seed + 3) < .5, 1., -1.).astype(F32)
    dirn = np.where(flip, -dirn, dirn)
    c = cu * 1.1 + dirn * vl
    w = F32(7.)
    q = np.floor(c / w).astype(np.int32); fr = c / w - q
    duty = .22 + .56 * K.unit(K.fbm(seed + 8, (4, 8), .5))
    s2 = c / (2 * w); fr2 = s2 - np.floor(s2)
    b = (fr2 < duty).astype(F32)
    pos = np.where(b > 0, fr2 / duty, (fr2 - duty) / (1 - duty))
    fr = pos
    bev = np.sin(F32(np.pi) * np.clip(pos, 0, 1))
    ta = K.tiers(K.fhash(q, vi, seed + 4)); tb = K.tiers(K.fhash(q, vi, seed + 5))
    gold = K.ramp(np.clip(.3 + .4 * ta + .3 * bev, 0, 1), ['4a2a00', '9a6400', 'e8a810', 'ffd850'])
    cob = K.ramp(np.clip(.15 + .4 * tb + .35 * bev, 0, 1), ['01062a', '06208a', '1a4ae0', '5a88ff'])
    col = K.mix(gold, cob, b) * (.6 + .45 * bev)[..., None]
    col = col * (1 - .7 * K.near(np.minimum(fr, 1 - fr) * w, .6))[..., None]
    bol = K.near(np.minimum(vl, Hb - vl), 1.3)
    bh = K.relief(np.minimum(vl, Hb - vl).clip(0, 3), 1.2)
    col = K.mix(col, np.array([.75, .78, .9], F32) * (.6 + .6 * np.clip(bh + .5, 0, 1))[..., None], bol)
    pin = K.near(np.hypot(us - (col_i + .5) * P, vl - Hb / 2), 3.2) * flip
    col = K.mix(col, np.array([1., 1., 1.], F32), pin)
    col = np.where(flip[..., None], col * np.array([1.05, 1.0, 1.15], F32), col)
    M, Rr, C = _deck(b, ta, tb, (0, 18, 150, 205, 190, 250), (240, 255, 28, 72, 230, 255))
    Rr = Rr + 36 * (1 - bev)
    M, Rr, C = _over(M, Rr, C, bol, 255, 120, 60)
    M, Rr, C = _over(M, Rr, C, pin, 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================ DUALITY SCALES
def duality_scales(seed=42):
    """Imbricated scales following curving growth rows. Every scale carries
    two natures: a lime lacquer tip and a plum metal root, with the split
    sliding scale by scale; a hidden field biases which nature leads, so
    regions lean lime or plum through a dither of individual scales."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 55, 4)
    u, v = K.rot(wx, wy, F32(.5))
    h = F32(10.); w = F32(17.); R = F32(11.5)
    best_j = np.full((N, N), -10 ** 6, np.int32); bdx = np.zeros((N, N), F32); bdy = np.zeros((N, N), F32)
    bci = np.zeros((N, N), F32)
    j0 = np.floor(v / h).astype(np.int32)
    for dj in (2, 1, 0):
        j = j0 + dj
        off = (j % 2) * F32(.5)
        ci = np.floor(u / w + off)
        cx = (ci - off + F32(.5)) * w
        cy = j * h
        dx = u - cx; dy = v - cy
        inside = (dx * dx + dy * dy < R * R) & (j > best_j)
        best_j = np.where(inside, j, best_j)
        bdx = np.where(inside, dx, bdx); bdy = np.where(inside, dy, bdy); bci = np.where(inside, ci, bci)
    rr = np.hypot(bdx, bdy)
    sid = K.fhash(best_j.astype(F32), bci, seed + 3)
    split = (-.2 + .5 * sid) * R
    lean = K.unit(K.fbm(seed + 4, (4, 8), .5))
    flip = K.fhash(best_j.astype(F32), bci, seed + 6) < lean
    tipside = bdy < -split
    b = np.where(flip, tipside, ~tipside).astype(F32)       # 1 = plum metal
    ta = K.tiers(sid); tb = K.tiers(K.fhash(best_j.astype(F32), bci, seed + 5))
    t = np.clip(rr / R, 0, 1)
    lime = K.ramp(np.clip(.35 + .4 * ta + .25 * (1 - t), 0, 1), ['1a3a00', '4a8a00', '9ae010', 'd8ff60', 'f8ffd8'])
    plum = K.ramp(np.clip(.08 + .45 * tb + .35 * (1 - t), 0, 1), ['14011a', '48084a', '8a2088', 'd060c8', 'ffc8f0'])
    col = K.mix(lime, plum, b)
    rim = K.near(R - rr, 1.3)
    keel = K.near(np.abs(bdx), .6) * (t < .8)
    col = col * (.5 + .6 * (1 - t ** 2))[..., None]
    col = K.mix(col, np.array([1., .98, .9], F32), rim * .85)
    col = col * (1 - .35 * keel)[..., None]
    M, Rr, C = _deck(b, ta, tb, (0, 22, 150, 205, 185, 250), (228, 255, 22, 60, 222, 255))
    Rr = Rr + 50 * t
    M, Rr, C = _over(M, Rr, C, rim, 255, 16, 40)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================= POLARITY LACE
def polarity_lace(seed=42):
    """Lace woven from electrostatics: hundreds of +/- charges; coral lacquer
    threads follow the field lines, jade metal threads follow the
    equipotentials, the two families cross at right angles in pale knots, and
    the openwork between them falls to deep navy."""
    r = K.rng(seed)
    x, y = K.xy()
    n = 512
    ys, xs = np.mgrid[:n, :n].astype(F32) * (N / n) + N / n / 2
    ch = K.sites(seed + 1, 150, .95)
    qs = r.choice([-1., 1.], len(ch))
    phi = K.field_conv(ch, qs, lambda dx, dy: .5 * np.log(dx * dx + dy * dy + 30.), n)
    psi = K.field_conv(ch, qs, lambda dx, dy: np.arctan2(dy, dx), n)
    gx = K.field_conv(ch, qs, lambda dx, dy: -dy / (dx * dx + dy * dy + 30.), n)
    gy = K.field_conv(ch, qs, lambda dx, dy: dx / (dx * dx + dy * dy + 30.), n)
    up = lambda a: cv2.resize(a, (N, N), interpolation=cv2.INTER_CUBIC)
    m = 14
    Cs, Sn = up(np.cos(m * psi)), up(np.sin(m * psi))
    gpsi = np.hypot(up(gx), up(gy)) * m + F32(1e-4)
    phi = up(phi)
    fl = K.near(np.abs(np.arctan2(Sn, Cs)) / gpsi, 1.05)
    eq, eqq, _ = K.iso(phi, .16, 2.0)
    gphi = np.hypot(*K.grad(phi)) / .16
    crowd = K.sstep(.25, .45, gphi)
    fl = fl * (1 - crowd); eq = eq * (1 - crowd)
    knot = K.near(np.hypot(*K.grad(K.blur(fl * eq, .8))) * 0 + (1 - np.clip(fl * eq * 3, 0, 1)), .2)
    knot = np.clip(fl * eq * 1.6, 0, 1)
    ta = K.tiers(K.hash01(eqq, seed + 2)); tb = K.tiers(K.hash01(eqq, seed + 3))
    ground = K.ramp(K.unit(K.fbm(seed + 4, (6, 12, 48), .6)) * .5 + .1, ['03061a', '0a1238', '162058'])
    net = K.blur(np.clip(fl + eq, 0, 1), 2.5) * .35
    coral = np.array([1., .32, .16], F32) * (.8 + .35 * ta)[..., None]
    jade = np.array([.05, .82, .52], F32) * (.75 + .4 * tb)[..., None]
    med = crowd * K.sstep(.2, .8, .5 + .5 * np.cos(phi * 8))
    medc = K.mix(jade * .8, coral, (np.cos(phi * 4) > 0).astype(F32))
    col = ground * (1 - net)[..., None]
    col = K.mix(col, medc, med)
    col = K.mix(col, jade, eq)
    col = K.mix(col, coral, fl)
    col = K.mix(col, np.array([1., .85, .35], F32), np.clip(knot, 0, 1))
    b = np.clip(eq + (np.cos(phi * 4) <= 0) * med, 0, 1)
    M, Rr, C = _deck(b, ta, tb, (0, 16, 60, 110, 200, 250), (225, 255, 30, 70, 218, 255))
    fa = np.clip(fl + med * (np.cos(phi * 4) > 0), 0, 1)
    open_ = np.clip(1 - fa - b, 0, 1)
    M, Rr, C = _over(M, Rr, C, open_, 20, 235, 240)
    M, Rr, C = _over(M, Rr, C, np.clip(knot, 0, 1), 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)
