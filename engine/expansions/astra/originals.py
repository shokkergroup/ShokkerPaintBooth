"""ASTRA ORIGINALS — celestial luxury materials (ten constructions).

SPB-105 / ASTRA-R2 2026-09-27 (Claude). Owner: R1 "surprisingly AWFUL"; wants
every finish unique, jumping off the screen, doing what its name says, and as
intricate as possible. Lane arc: PRECIOUS MATTER UNDER STARLIGHT — each card is
one real luxury material or cosmic object, built from the mathematics that
actually produces it, rendered as a dense whole-car field of 8-32 px detail
with a spec deck owned by that finish alone.

Every function: (seed) -> (paint HxWx3 float 0..1, spec HxWx3 float 0..255)
at the native 2048 canvas. Blue/Cc is iRacing-inverted: 16 = strongest coat.
"""
import cv2
import numpy as np
from . import kit as K

N = K.N
F32 = np.float32


def _per(n, seed):
    return K.hash01(np.arange(n), seed)


# ============================================================ EVENT HORIZON
def event_horizon(seed=42):
    """Field of small black holes: absorbing shadow, photon ring, lensed far-
    disc halo, Doppler-beamed turbulent accretion discs, rare polar jets, and a
    gravitationally lensed starfield + nebula between them."""
    r = K.rng(seed)
    x, y = K.xy()
    lab, _, pts = K.voronoi(K.sites(seed + 1, 116, .9))
    n = len(pts)
    R = (22 + 36 * _per(n, seed + 2))[lab]
    rs = R * (.28 + .08 * _per(n, seed + 3))[lab]
    ang = (_per(n, seed + 4) * K.TAU)[lab]
    inc = (.20 + .40 * _per(n, seed + 5))[lab]
    fam = (_per(n, seed + 6) * 3).astype(np.int32)[lab]
    jet = (_per(n, seed + 7) < .2)[lab]
    dx, dy = K.cell_local(lab, pts, x, y)
    rr = np.sqrt(dx * dx + dy * dy) + F32(1e-3)
    u, v = K.rot(dx, dy, ang)
    vi = v / inc
    re = np.sqrt(u * u + vi * vi)
    phi = np.arctan2(vi, u)
    # lensed starfield + nebula
    defl = np.minimum(1.5 * rs * rs / (rr * rr), 1.3) * rs
    k = r.random((N // 2, N // 2)).astype(np.float32)
    k = np.where(k > .982, (k - .982) / .018, 0).astype(np.float32)
    star = K.remap(cv2.resize(k, (N, N), interpolation=cv2.INTER_NEAREST), x + dx / rr * defl, y + dy / rr * defl)
    neb = K.unit(K.fbm(seed + 9, (4, 8, 16, 48, 160), .62))
    wisp = K.sstep(.55, .95, K.ridged(seed + 10, (24, 64, 160), .7))
    space = K.ramp(neb, ['05020c', '120827', '2c0f4a', '1f2d5c', '0e1b36'])
    K.addc(space, wisp, (.10, .05, .16)); K.addc(space, star, (.9, .85, 1.))
    # accretion disc
    turb = K.fbm(seed + 11, (64, 128, 256), .7)
    streak = .5 + .5 * np.sin(re * F32(K.TAU / 4.4) + 3.4 * turb + phi * 3)
    rin = rs * 1.35
    band = K.sstep(rin, rin + 2.5, re) * (1 - K.sstep(R * .72, R, re))
    temp = np.clip((re - rin) / np.maximum(R - rin, 1), 0, 1)
    dop = np.cos(phi)
    td = np.clip(temp - .32 * dop, 0, 1)
    pal = [['fffaf0', 'ffd37a', 'ff7a24', 'b8143e', '3a0628'],
           ['f4fcff', '9ee6ff', '4a7aff', '7a28ff', '1c063e'],
           ['fff4ff', 'ffb4f2', 'e83ec4', '7c0ea4', '22042e']]
    disc = K.ramps(td, fam, pal)
    disc *= ((1 + .95 * dop) * (.45 + .75 * streak))[..., None]
    band = np.where((v < 0) & (rr < rs * 1.02), 0, band)
    # lensed far-side image: a bright arc hugging the shadow top and bottom
    arc = np.exp(-((rr - rs * 1.2) / (rs * .13 + .7)) ** 2) * (.5 + .6 * np.abs(np.sin(np.arctan2(v, u)))) * (.6 + .5 * streak)
    photon = np.exp(-((rr - rs * 1.03) / 1.) ** 2)
    shadow = K.sstep(rs * 1.01, rs * .95, rr)
    jl = np.abs(u) < (1.1 + .025 * np.abs(v))
    jetm = (jet & jl & (np.abs(v) > rs) & (np.abs(v) < R * 1.5)).astype(F32) * np.exp(-np.abs(v) / (R * .6))
    hc = np.array([[1., .78, .42], [.55, .82, 1.], [1., .55, .95]], F32)[fam]
    paint = K.lerp3(space, disc, band)
    hc *= (arc * (1 - shadow) * F32(.95))[..., None]; paint += hc
    K.lerp3(paint, (.004, .004, .004), shadow)
    K.addc(paint, photon, (1.15, 1.115, 1.058)); K.addc(paint, jetm, (.7, .85, 1.))
    # spec: nebula pearl, star glints, foil disc, chrome photon ring, absorbing void
    tier = K.tiers(_per(n, seed + 12)[lab])
    st = np.minimum(star, 1)
    M = 30 + 150 * neb + 60 * wisp + 200 * st
    Rr = 170 - 90 * neb - 150 * st
    C = 230 - 150 * neb
    M = M * (1 - band) + (170 + 65 * streak + 20 * tier) * band
    Rr = Rr * (1 - band) + (72 - 48 * streak - 12 * tier + 22 * temp) * band
    C = C * (1 - band) + (140 - 90 * streak) * band
    hl = np.clip(arc * 1.3, 0, 1) * (1 - shadow)
    M = M * (1 - hl) + 235 * hl; Rr = Rr * (1 - hl) + 28 * hl; C = C * (1 - hl) + 80 * hl
    M = M * (1 - shadow); Rr = Rr * (1 - shadow) + 255 * shadow; C = C * (1 - shadow) + 255 * shadow
    pr = np.clip(photon * 1.5, 0, 1)
    M = M * (1 - pr) + 255 * pr; Rr = Rr * (1 - pr) + 16 * pr; C = C * (1 - pr) + 16 * pr
    M = np.maximum(M, 240 * jetm); Rr = np.where(jetm > .2, 24, Rr)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(paint, M, Rr, C)


# ======================================================= QUASICRYSTAL CROWN
def quasicrystal_crown(seed=42):
    """Five-fold quasiperiodic wave interference (the diffraction maths of a
    real quasicrystal) drawn as gold contour filigree over jewel enamel. Each
    polycrystal grain has its own orientation and gem family; ten-fold maxima
    rise into engraved gold crowns, deep minima into cabochon gems."""
    x, y = K.xy()
    lab, _, gp = K.voronoi(K.sites(seed + 1, 360, .9))
    ng = len(gp)
    th = (_per(ng, seed) * K.TAU / 5)[lab]
    ph = (_per(ng, seed + 1) * 50)[lab]
    k = F32(K.TAU / 34.)
    xh, yh = x[::2, ::2], y[::2, ::2]; thh, phh = th[::2, ::2], ph[::2, ::2]
    fh = np.zeros(xh.shape, F32)
    for i in range(5):
        a = thh + F32(i * K.TAU / 5)
        fh += np.cos(k * (xh * np.cos(a) + yh * np.sin(a)) + phh * F32(i + 1))
    fh *= F32(1 / 5.)
    f = cv2.resize(fh, (N, N), interpolation=cv2.INTER_CUBIC)
    g = np.zeros((N, N), F32)
    k2 = F32(K.TAU / 7.)
    for i in range(7):
        a = th * 1.3 + F32(i * K.TAU / 7)
        g += np.cos(k2 * (x * np.cos(a) + y * np.sin(a)))
    g *= F32(1 / 7.)
    line, q, fr = K.iso(f, .21, 1.3)
    fam = np.minimum((_per(ng, seed + 2) * 1.15).astype(np.int32), 1)[lab] * 0
    enam = [['030830', '08208a', '1648d8', '3a80ff', '8ab8ff'],
            ['03101c', '06305a', '0c5a8a', '1c8ab8', '58c0e8'],
            ['0a0420', '1c0a5a', '3418a0', '5a3cd0', '9a80f4']]
    lev = np.clip((f + .62) / 1.24, 0, 1)
    col = K.ramp(lev, enam[0])
    col *= (.75 + .5 * fr)[..., None]
    crown = K.sstep(.52, .6, f)
    gem = K.sstep(-.52, -.6, f)
    ch = K.relief(np.clip(f - .52, 0, 1) * 60 + g * crown * 1.5, 1.)
    goldc = K.ramp(np.clip(.55 + .45 * ch + .15 * g, 0, 1), ['6a4210', 'b8842a', 'f0c860', 'fff2c0', 'ffffff'])
    col = K.mix(col, goldc, crown)
    gh = K.relief(np.clip(-.52 - f, 0, 1) * 70, 1.)
    gems = np.array([[.85, .05, .18], [.05, .75, .85], [1., .55, .05]], F32)[(K.hash01(q, lab, seed + 5) * 3).astype(np.int32)]
    gcol = gems * (.45 + .7 * np.clip(.5 + gh, 0, 1.2))[..., None] + np.clip(gh - .35, 0, 1)[..., None] * 1.2
    col = K.mix(col, gcol, gem)
    lg = K.ramp(np.clip(.6 + .3 * np.sin(f * 40), 0, 1), ['a07020', 'f0c050', 'fff0b0'])
    col = K.mix(col, lg, line * (1 - gem))
    seam = K.near(K.edge_distance(lab), 1.2)
    col = K.mix(col, np.array([1., .95, .8], F32), seam)
    tier = K.tiers(K.hash01(q + 20, lab, seed))
    M = 25 + 70 * lev + 15 * tier
    Rr = 22 + 26 * (1 - fr) + 10 * tier
    C = 16 + 22 * tier
    M = M * (1 - crown) + (250 - 12 * np.abs(g)) * crown
    Rr = Rr * (1 - crown) + (18 + 40 * np.abs(g)) * crown
    C = C * (1 - crown) + 180 * crown
    M = M * (1 - gem) + 110 * gem; Rr = Rr * (1 - gem) + 16 * gem; C = C * (1 - gem) + 16 * gem
    lm = line * (1 - gem)
    M = M * (1 - lm) + 255 * lm; Rr = Rr * (1 - lm) + 20 * lm; C = C * (1 - lm) + 220 * lm
    M = np.maximum(M, 255 * seam); Rr = Rr * (1 - seam) + 16 * seam
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================ GRAVITY LOOM
def gravity_loom(seed=42):
    """A 2/2 twill woven from metallic silk and pulled into gravity wells:
    thread coordinates are bent by a field of point masses (lensing warp),
    threads redshift and sink toward each mass, every well is ringed by a
    bright Einstein ring and holds a tiny star."""
    r = K.rng(seed)
    x, y = K.xy()
    n = 256
    ms = K.sites(seed + 1, 240, .95)
    mass = (0.5 + 1.5 * r.random(len(ms))).astype(F32)
    ys, xs = np.mgrid[:n, :n].astype(F32) * (N / n) + N / n / 2
    Dx = np.zeros((n, n), F32); Dy = np.zeros((n, n), F32); P = np.zeros((n, n), F32)
    for (mx, my), m in zip(ms, mass):
        ddx = xs - mx; ddy = ys - my
        r2 = ddx * ddx + ddy * ddy + 2000.
        Dx -= 3800 * m * ddx / r2; Dy -= 3800 * m * ddy / r2
        P += m * 1600. / r2
    up = lambda a: cv2.resize(a, (N, N), interpolation=cv2.INTER_CUBIC)
    Dx, Dy, P = up(Dx), up(Dy), up(P)
    u = x + Dx; v = y + Dy
    p = F32(10.)
    i = np.floor(u / p).astype(np.int32); j = np.floor(v / p).astype(np.int32)
    fu = u / p - i; fv = v / p - j
    over = ((i + j) % 4) < 2
    cw = np.sin(F32(np.pi) * fu); cf = np.sin(F32(np.pi) * fv)
    tw = .5 + .5 * np.sin(F32(K.TAU) * (fv * 2 + fu * .9))
    tf = .5 + .5 * np.sin(F32(K.TAU) * (fu * 2 - fv * .9))
    gold = K.hash01(i, seed + 7) < .14
    well = np.clip(P / 1.6, 0, 1)
    wc = K.ramp(np.clip(K.hash01(i, seed + 8) * .3 + .08 + .6 * well, 0, 1), ['0c6a58', '1fc4a4', '7af0d0', 'e0b040', 'c0402a'])
    fc = K.ramp(np.clip(K.hash01(j, seed + 9) * .25 + .02 + .6 * well, 0, 1), ['070f30', '12286a', '2a4cb0', '7a3cc0', '6a0c34'])
    wc = np.where(gold[..., None], np.array([1., .82, .38], F32), wc)
    paint = np.where(over[..., None], wc * (.28 + .9 * cw * (.7 + .4 * tw))[..., None],
                     fc * (.22 + .8 * cf * (.7 + .4 * tf))[..., None])
    paint *= (1 - .5 * well)[..., None]
    ein = np.zeros((N, N), F32); core = np.zeros((N, N), F32)
    for (mx, my), m in zip(ms, mass):
        cv2.circle(ein, (int(mx), int(my)), int(14 + 12 * m), 1., 2, cv2.LINE_AA)
        cv2.circle(core, (int(mx), int(my)), int(2 + 1.5 * m), 1., -1, cv2.LINE_AA)
    ring = np.clip(ein * .9 + K.blur(ein, 2.5) * 1.2, 0, 1)
    glow = K.blur(core, 4) * 3
    K.addc(paint, ring, (.44, .64, .8)); K.addc(paint, core + glow, (1., .9, .7))
    tw_ = K.tiers(K.hash01(i, seed + 11)); tf_ = K.tiers(K.hash01(j, seed + 12))
    Mw = np.where(gold, 255, 185 + 45 * tw_); Rw = np.where(gold, 18, 34 + 26 * tw_) + 80 * (1 - cw) - 18 * tw
    Mf = 25 + 45 * tf_; Rf = 110 + 30 * tf_ + 80 * (1 - cf) - 20 * tf
    M = np.where(over, Mw, Mf) * (1 - .35 * well)
    Rr = np.where(over, Rw, Rf) + 60 * well
    C = np.where(over, 160 - 70 * tw_, 16 + 26 * tf_) + 60 * well
    cm = np.clip(ring + core + glow * .5, 0, 1)
    M = M * (1 - cm) + 255 * cm; Rr = Rr * (1 - cm) + 16 * cm; C = C * (1 - cm) + 16 * cm
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(paint, M, Rr, C)


# ========================================================== PHOENIX CERAMIC
def phoenix_ceramic(seed=42):
    """Raku kintsugi: two-scale craquelure (smoke-stained crackle inside a
    coarse fracture net), raised gold repair seams, copper-luster fire flashes
    whose iridescent contour tongues rise like phoenix feathers, pinholes."""
    x, y = K.xy()
    fl, _, fp = K.voronoi(K.sites(seed + 1, 14, .95))
    fe = K.edge_distance(fl)
    bl, _, bp = K.voronoi(K.sites(seed + 2, 115, .95))
    be = K.edge_distance(bl)
    wx, wy = K.warp(seed + 3, 45, 14)
    fire = K.fbm(seed + 4, (14, 28, 56, 112), .62)
    fire = K.unit(K.remap(fire, wx, wy - .35 * np.abs(wx - x)) + .30 * K.ridged(seed + 5, (12, 24, 48)))
    flame = K.sstep(.46, .62, fire)
    feather, fq, ffr = K.iso(fire, .035, 1.1)
    film = K.thin_film(fire * 3.6, 1.15, .55)
    copper = K.ramp(fire, ['1e0806', '5a1a0c', 'a8401a', 'e07838', 'ffc07a'])
    luster = K.mix(copper, film, .38) * (.7 + .5 * ffr)[..., None]
    luster = K.mix(luster, np.array([1., .75, .35], F32), feather * .7)
    gt = K.hash01(fl, seed + 7)
    glaze = K.ramp(np.clip(.25 + .55 * gt + .2 * (1 - fire), 0, 1), ['b8a888', 'dccfb2', 'f2e9d6', 'e2ece6', 'b6d6cc'])
    crack = K.near(fe, .7, .8)
    base = K.mix(glaze, luster, flame)
    base = base * (1 - crack * (.8 - .3 * flame))[..., None]
    pin = (K.hash01(fl, seed + 9) < .07) & (np.hypot(*K.cell_local(fl, fp, x, y)) < 1.7)
    base = np.where(pin[..., None], base * .2, base)
    seam = K.near(be, 2.4, 1.2)
    sh = K.relief(np.clip(3.2 - be, 0, 3.2) * 1.6, 1.2)
    goldc = K.ramp(K.unit(K.noise(seed + 10, 200)), ['9a6a18', 'e8b840', 'fff2a8']) * (.75 + .6 * sh[..., None])
    paint = K.mix(base, goldc, seam)
    tier = K.tiers(K.hash01(bl, seed + 11))
    M = 5 + 200 * flame * (.55 + .45 * ffr) + 18 * tier
    Rr = 20 + 14 * tier + 170 * crack + 40 * flame * (1 - ffr)
    C = 16 + 50 * flame + 190 * crack
    M = np.where(feather * flame > .5, 250, M); Rr = np.where(feather * flame > .5, 18, Rr)
    Rr = np.where(pin, 210, Rr)
    M = M * (1 - seam) + 255 * seam; Rr = Rr * (1 - seam) + (18 + 34 * np.clip(-sh, 0, 1)) * seam; C = C * (1 - seam) + 210 * seam
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(paint, M, Rr, C)


# ========================================================== SOVEREIGN NACRE
def sovereign_nacre(seed=42):
    """Paua/abalone nacre: interference colour from a swirling growth-height
    field, terrace growth lines a few px apart, a 9 px aragonite-tablet mosaic
    that shimmers tile by tile, and scattered blister pearls."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 70, 12)
    wx = wx + 24 * K.noise(seed + 2, 36); wy = wy + 24 * K.noise(seed + 3, 36)
    h = K.unit(K.remap(K.fbm(seed + 4, (8, 16, 32, 64), .62), wx, wy), 0, 100)
    tl, _, tp = K.voronoi(K.sites(seed + 5, 9, .9))
    th = K.hash01(tl, seed + 6)
    te = K.edge_distance(tl)
    line, gq, fr = K.iso(h, 1 / 34., 1.2)
    t = h * 3.1 + .06 * th + .12 * fr
    paua = K.cospal(t * 1.5, (.24, .34, .52), (.24, .24, .36), (1., .85, .7), (.62, .30, .08))
    flash = K.sstep(.55, .85, .5 + .5 * np.cos(F32(K.TAU) * (h * 9 + .3 * th)))
    col = paua * (.55 + .55 * fr)[..., None] * (.72 + .56 * th[..., None])
    col = col + flash[..., None] * np.array([.18, .30, .28], F32)
    col = col * (1 - .22 * (te < 1.))[..., None]
    col = col * (1 - .6 * line)[..., None]
    pl, pd, pp = K.voronoi(K.sites(seed + 8, 92, .95))
    pr = (5 + 11 * _per(len(pp), seed + 9))[pl]
    on = (_per(len(pp), seed + 10) < .45)[pl]
    dome = np.clip(1 - (pd / pr) ** 2, 0, 1) * on
    hs = K.relief(np.sqrt(dome) * pr, 1.)
    pc = K.cospal(.15 + .3 * dome, (.86, .80, .86), (.12, .10, .14), (1, 1, 1), (.0, .2, .4))
    pc = pc * (.72 + .6 * hs[..., None]) + np.clip(hs - .45, 0, 1)[..., None] * .9
    cov = K.near(pd, pr) * on
    paint = K.mix(col, pc, cov)
    tier = K.tiers(th)
    M = 95 + 125 * tier * (1 - line) + 30 * fr
    Rr = 16 + 150 * (1 - K.lum(col)) + 10 * (1 - tier)
    C = 16 + 40 * line + 30 * (1 - flash)
    M = M * (1 - cov) + (80 + 60 * dome) * cov; Rr = Rr * (1 - cov) + 16 * cov; C = C * (1 - cov) + 16 * cov
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(paint, M, Rr, C)


# ========================================================= MAGNETIC REGALIA
def magnetic_regalia(seed=42):
    """Ferrofluid under magnets: black-chrome Rosensweig spike crowns erupt
    where the dipole field is strongest (hex lattice per domain, spike height =
    field strength), while gold iron-filing dashes trace every field line
    across the glossy black fluid between the poles."""
    r = K.rng(seed)
    x, y = K.xy()
    dl, _, dp = K.voronoi(K.sites(seed + 1, 200, .9))
    ang = (_per(len(dp), seed) * np.pi / 3)[dl]
    u, v = K.rot(x, y, ang)
    pitch = F32(14.)
    b1 = v / (pitch * F32(.866))
    row = np.floor(b1)
    best = None
    for dr in (0, 1):
        rw = row + dr
        uu = u / pitch - K.frac(rw * F32(.5))
        d = np.hypot((uu - np.round(uu)) * pitch, (b1 - rw) * pitch * F32(.866))
        best = d if best is None else np.minimum(best, d)
    n = 512
    ys, xs = np.mgrid[:n, :n].astype(F32) * (N / n) + N / n / 2
    cell = N / n; G = 2 * n
    Mx = np.zeros((G, G), np.float64); My = np.zeros((G, G), np.float64)
    for (mx, my) in K.sites(seed + 2, 185, .9):
        a = r.uniform(0, 2 * np.pi)
        ix = int(np.clip(mx // cell, 0, n - 1)); iy = int(np.clip(my // cell, 0, n - 1))
        Mx[iy, ix] += np.cos(a); My[iy, ix] += np.sin(a)
    off = np.where(np.arange(G) < n, np.arange(G), np.arange(G) - G) * cell
    ddy, ddx = np.meshgrid(off, off, indexing='ij')
    rr2 = ddx * ddx + ddy * ddy + 500.
    FKx = np.fft.rfft2(ddx / rr2); FKy = np.fft.rfft2(ddy / rr2)
    FMx = np.fft.rfft2(Mx); FMy = np.fft.rfft2(My)
    psi = (9000 * np.fft.irfft2(FKy * FMx - FKx * FMy, s=(G, G))[:n, :n]).astype(F32)
    phi = (9000 * np.fft.irfft2(FKx * FMx + FKy * FMy, s=(G, G))[:n, :n]).astype(F32)
    up = lambda a: cv2.resize(a, (N, N), interpolation=cv2.INTER_CUBIC)
    psi, phi = up(psi), up(phi)
    sp = F32(4.2)
    fil, fq, _ = K.iso(psi, sp, 1.15)
    gx, gy = K.grad(psi)
    dens = np.hypot(gx, gy) / sp                 # field lines per px
    zone = K.sstep(.52, .70, K.blur(dens, 3))
    dash = (K.frac(phi / sp * .55) < .62).astype(F32)
    fil = fil * dash * (1 - zone) * (K.hash01(fq, seed + 3) < .85)
    hgt = np.clip(1 - best / (pitch * .56), 0, 1) ** 1.4 * zone
    sh = K.relief(hgt * 13, 1.)
    rim = K.near(np.abs(K.blur(dens, 3) - .6) / (np.hypot(*K.grad(K.blur(dens, 3))) + 1e-3), 1.1) * (1 - hgt)
    env = K.mix(K.hexrgb('18e0d8')[0], K.hexrgb('8a3cff')[0], K.unit(K.noise(seed + 4, 22)))
    lit = np.clip(sh, -1, 1)
    fluid = np.full((N, N, 3), .03, F32) + K.unit(K.noise(seed + 5, 110))[..., None] * np.array([.02, .03, .05], F32)
    fluid = fluid + (np.clip(lit, 0, 1) ** 1.2)[..., None] * env * 1.1 + (np.clip(-lit, 0, 1) ** 2)[..., None] * np.array([.10, .04, .22], F32)
    tip = K.sstep(.78, .95, hgt)
    fluid = fluid + tip[..., None] * .95
    gold = K.ramp(K.unit(K.noise(seed + 6, 140)), ['b07818', 'f2c848', 'fff4b8'])
    gm = np.clip(fil + rim, 0, 1)
    paint = K.mix(fluid, gold, gm)
    tier = K.tiers(K.hash01(dl, seed + 7))
    M = 70 + 185 * zone + 10 * tier
    Rr = 26 - 8 * zone + 26 * (1 - hgt) * zone + 16 * tier
    C = 16 + 60 * (1 - hgt) * zone
    M = M * (1 - gm) + 230 * gm; Rr = Rr * (1 - gm) + 90 * gm; C = C * (1 - gm) + 230 * gm
    M = np.maximum(M, 255 * tip); Rr = Rr * (1 - tip) + 16 * tip
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(paint, M, Rr, C)


# ========================================================== METEORITE ROYAL
def meteorite_royal(seed=42):
    """Etched iron meteorite: Widmanstaetten kamacite lamellae (irregular
    widths and gaps) in three octahedral directions per parent crystal, each
    direction etched to its own reflectance, bright taenite rims, fine Neumann
    lines, dark plessite fill and a royal heat-anodised tint."""
    r = K.rng(seed)
    x, y = K.xy()
    gl, _, gp = K.voronoi(K.sites(seed + 1, 330, .95))
    ng = len(gp)
    base = (_per(ng, seed) * np.pi)[gl]
    S = 4.
    L = int(12000 * S)
    best = np.full((N, N), -1., F32); which = np.zeros((N, N), np.int8)
    for kd in range(3):
        wid = r.uniform(5, 26, 4000); gap = r.uniform(3, 22, 4000)
        edges = np.cumsum(np.stack([gap, wid], 1).ravel())
        sidx = np.arange(L, dtype=np.float32) / S
        pos = np.searchsorted(edges, sidx)
        lo = np.concatenate([[0], edges])[pos]; hi = edges[np.minimum(pos, len(edges) - 1)]
        inside = (pos % 2) == 1
        dep = np.where(inside, np.minimum(sidx - lo, hi - sidx), -1).astype(F32)
        a = base + kd * np.pi / 3 + (_per(ng, seed + 10 + kd)[gl] - .5) * .16
        s = x * np.cos(a) + y * np.sin(a) + (_per(ng, seed + 20 + kd)[gl] * 5000 + 3000)
        d = dep[np.clip((s * S).astype(np.int32), 0, L - 1)]
        take = d > best
        best = np.where(take, d, best); which = np.where(take, kd, which).astype(np.int8)
    kam = best >= 0
    rim = kam & (best < .9)
    perm = (_per(ng, seed + 30) * 6).astype(np.int32)[gl]
    lvl = np.array([[1., .78, .58], [1., .58, .78], [.78, 1., .58], [.58, 1., .78], [.78, .58, 1.], [.58, .78, 1.]], F32)
    bright = lvl[perm, which.astype(np.int32)]
    neu = .5 + .5 * np.cos((x * np.cos(base + 1.1) + y * np.sin(base + 1.1)) * F32(K.TAU / 7.))
    neu = K.sstep(.93, 1., neu) * (K.hash01(np.floor(x / 40).astype(np.int32), np.floor(y / 40).astype(np.int32), seed) < .5)
    tint = np.array([[1.4, .98, .28], [.34, .52, 1.55], [.98, .3, 1.45]], F32)[which.astype(np.int32)]
    tint = tint * (1 + .10 * K.fbm(seed + 41, (24, 48), .5))[..., None]
    steel = np.array([.86, .86, .92], F32)
    col = (steel * bright[..., None]) * (.9 + .1 * np.clip(best, 0, 8)[..., None] / 8)
    col = K.mix(col, col * tint, .8)
    col = col * (1 - .25 * neu)[..., None]
    grit = K.noise(seed + 50, 600, interp=cv2.INTER_LINEAR)
    pc = K.ramp(np.clip(.4 + .3 * grit + .25 * np.sin((x * .8 + y * .3) * 1.7), 0, 1), ['141218', '2c2834', '4a4456', '221e2a'])
    col = np.where(kam[..., None], col, pc)
    col = np.where(rim[..., None], col * .5 + .48, col)
    wt = K.tiers(K.hash01(which.astype(np.int32), gl, seed + 60))
    dw = which.astype(np.int32)
    M = np.where(kam, np.array([30., 238., 150.], F32)[dw] + 22 * bright - 8 * wt, 160 + 30 * grit)
    C = np.where(kam, np.array([235., 40., 130.], F32)[dw] + 30 * (1 - bright), 235)
    Rr = K.r_from_luma(col, M, C)
    M = np.where(rim, 255, M); Rr = np.where(rim, 16, Rr); C = np.where(rim, 40, C)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(col, M, Rr, C)


# ========================================================= CRYOGENIC BLOOM
def cryogenic_bloom(seed=42):
    """Hexagonal ice dendrites (fern-branched, six-fold, asymmetric growth)
    blooming from hundreds of nuclei over a crystalline rime of micro-facets;
    cold halos, violet cryo-plasma in a hidden selector field, glassy ice
    against matte frost."""
    r = K.rng(seed)
    x, y = K.xy()
    nuc = K.sites(seed + 1, 60, .95)
    segs = []
    for (cx, cy) in nuc:
        a0 = r.uniform(0, np.pi / 3); L0 = r.uniform(10, 34)
        c = np.array([cx, cy])
        for arm in range(6):
            L = L0 * r.uniform(.65, 1.2)
            a = a0 + arm * np.pi / 3
            d = np.array([np.cos(a), np.sin(a)]); nrm = np.array([-d[1], d[0]])
            segs.append(np.array([c, c + d * L]))
            for b in range(1, int(L / 6.5)):
                p = c + d * (b * 6.5)
                for sgn in (-1, 1):
                    sl = (L - b * 6.5) * .36 * r.uniform(.5, 1.)
                    segs.append(np.array([p, p + (d * .5 + sgn * nrm * .866) * sl]))
    ice = K.draw_polys(segs, 1, aa=True).astype(F32) / 255
    core = np.zeros((N, N), np.uint8)
    for (cx, cy) in nuc:
        cv2.circle(core, (int(cx * 16), int(cy * 16)), 24, 255, -1, cv2.LINE_AA, 4)
    ice = np.clip(ice * .9 + core.astype(F32) / 255, 0, 1)
    halo = np.clip(K.blur(ice, 1.8) * 1.3 + K.blur(ice, 7) * .55, 0, 1.)
    fl, _, fp = K.voronoi(K.sites(seed + 3, 7, .95))
    fh = K.hash01(fl, seed + 4)
    fe = K.edge_distance(fl)
    rime = (fh - .5) * 2
    lay = K.unit(K.fbm(seed + 5, (8, 16, 32, 96), .65))
    ground = K.ramp(np.clip(lay * .32 + .22 + .16 * rime, 0, 1), ['040c20', '0a2448', '164478', '3272a8', '7ab6e0'])
    ground = ground * (1 - .18 * (fe < .8))[..., None]
    plasma = K.sstep(.62, .8, K.unit(K.fbm(seed + 2, (3, 6), .5)))
    hc = K.mix(np.array([.45, .88, 1.], F32), np.array([.80, .45, 1.], F32), plasma)
    paint = ground + hc * halo[..., None] * .42
    paint = K.mix(paint, np.array([.94, .98, 1.], F32), ice)
    tier = K.tiers(fh)
    hl = np.clip(halo, 0, 1)
    M = 30 + 60 * tier + 70 * hl
    Rr = 170 - 60 * tier - 110 * hl
    C = 200 - 50 * tier - 150 * hl
    M = M * (1 - ice) + 150 * ice; Rr = Rr * (1 - ice) + 16 * ice; C = C * (1 - ice) + 16 * ice
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.85)
    return K.pack(paint, M, Rr, C)


# ========================================================== CHRONOGRAPH GOLD
def chronograph_gold(seed=42):
    """Watchmaker's gold: dial panels each engine-turned with its own
    guilloche (sunburst, concentric, clous de Paris, rosette, flinque wave,
    perlage), polished chamfers between panels, ruby jewels in gold chatons
    and toothed wheel rims around some of them."""
    x, y = K.xy()
    pl, _, pp = K.voronoi(K.sites(seed + 1, 94, .9))
    npn = len(pp)
    typ = (_per(npn, seed) * 6).astype(np.int32)[pl]
    ang = (_per(npn, seed + 1) * K.TAU)[pl]
    dx, dy = K.cell_local(pl, pp, x, y)
    u, v = K.rot(dx, dy, ang)
    rr = np.hypot(u, v) + F32(1e-3); th = np.arctan2(v, u)
    ed = K.edge_distance(pl)
    g = np.zeros((N, N), F32)
    m = typ == 0; g[m] = np.cos(th[m] * 64)
    m = typ == 1; g[m] = np.cos(rr[m] * F32(K.TAU / 4.4))
    m = typ == 2
    cu = (u[m] / 9.) % 1 - .5; cv = (v[m] / 9.) % 1 - .5
    g[m] = np.where(np.abs(cu) > np.abs(cv), np.sign(cu), np.sign(cv) * .35)
    m = typ == 3; g[m] = np.cos(rr[m] * F32(K.TAU / 4.8) + 3.0 * np.sin(th[m] * 9))
    m = typ == 4; g[m] = np.cos(v[m] * F32(K.TAU / 4.6) + 2.4 * np.sin(u[m] * F32(K.TAU / 36)))
    m = typ == 5
    pu = u[m] / 12.; pv = v[m] / 12.
    pr_ = np.floor(pv); pc_ = np.floor(pu + .5 * (pr_ % 2))
    ld = np.hypot((pu + .5 * (pr_ % 2) - pc_ - .5) * 12, (pv - pr_ - .5) * 12)
    g[m] = np.cos(ld * F32(K.TAU / 3.)) * (ld < 8.)
    bev = K.sstep(0, 4., ed)
    tq = _per(npn, seed + 2)
    tone = np.where(tq < .6, 0, np.where(tq < .9, 1, 2)).astype(np.int32)[pl]
    golds = [['6a4410', 'c89632', 'f8d880', 'fff8d8'], ['62301e', 'c47456', 'f6bca0', 'fff2ea'], ['58585c', 'b0b0b8', 'ececf2', 'ffffff']]
    s = .5 + .5 * g
    col = K.ramps(np.clip(.12 + .75 * s, 0, 1), tone, golds)
    sh = K.relief(g * 1.2 + bev * 4, 1.)
    col *= (.82 + .38 * sh)[..., None]
    col = K.mix(col * 1.35 + .08, col, bev)
    jew = (_per(npn, seed + 3) < .45)[pl]
    ruby = K.near(rr, 5.) * jew
    chaton = K.near(np.abs(rr - 7.), 1.6) * jew
    wheel = (_per(npn, seed + 4) < .35)[pl]
    wr = (18 + 12 * _per(npn, seed + 5))[pl]
    teeth = np.cos(th * np.round(wr * .9)) > 0
    ring = wheel & ((np.abs(rr - wr) < 2.) | ((rr > wr + 2.) & (rr < wr + 5.) & teeth))
    hl = K.relief(ruby * 5, 1.)
    rub = np.array([.6, .02, .1], F32) * (.55 + .8 * np.clip(.5 + hl, 0, 1))[..., None] + np.clip(hl - .45, 0, 1)[..., None] * 1.5
    col = K.mix(col, rub, ruby)
    col = K.mix(col, np.array([1., .9, .6], F32) * (.9 + .3 * sh[..., None]), chaton)
    col = np.where(ring[..., None], np.array([1., .86, .5], F32) * (.95 + .25 * sh[..., None]), col)
    tier = K.tiers(K.hash01(pl, seed + 6))
    M = 255 - 10 * tier
    Rr = (18 + 70 * (1 - s) * (typ != 2) + 36 * (typ == 2) * (g < 0) + 12 * tier) * bev + 16 * (1 - bev)
    C = np.where(K.hash01(pl, seed + 7) < .35, 16., 255.)
    M = M * (1 - ruby); Rr = Rr * (1 - ruby) + 16 * ruby; C = C * (1 - ruby) + 16 * ruby
    Rr = np.where(ring, 16, Rr); C = np.where(ring, 60, C)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ========================================================= VELVET SUPERNOVA
def velvet_supernova(seed=42):
    """Panne velvet (fine nap-angle sheen, crease lines, pile speckle) strewn
    with supernova remnants: knotty filamentary shock shells (some bipolar),
    synchrotron cores and neutron-star glints with diffraction spikes."""
    r = K.rng(seed)
    x, y = K.xy()
    nap = K.fbm(seed + 1, (16, 32, 64, 128), .6) * F32(np.pi * 1.4)
    sheen = .5 + .5 * np.cos(2 * (nap - .7))
    crease = K.sstep(.82, .96, K.ridged(seed + 2, (48, 96, 192), .6))
    pile = r.random((N, N)).astype(F32)
    vel = K.ramp(np.clip(.14 + .42 * sheen + .16 * crease + .15 * (pile - .5) + .10 * (pile > .86), 0, 1),
                 ['10030c', '2a0720', '4e0e3c', '7a2058', 'b04a80', 'e890bc'])
    sl, sd, sp = K.voronoi(K.sites(seed + 3, 88, .95))
    ns = len(sp)
    Rn = (11 + 26 * _per(ns, seed + 4))[sl]
    on = (_per(ns, seed + 5) < .85)[sl]
    fam = (_per(ns, seed + 6) * 3).astype(np.int32)[sl]
    bip = (_per(ns, seed + 7) < .3)[sl]
    dx, dy = K.cell_local(sl, sp, x, y)
    ua, va = K.rot(dx, dy, (_per(ns, seed + 8) * K.TAU)[sl])
    ell = np.where(bip, np.hypot(ua * 1.6, va * .75), sd)
    fil = K.fbm(seed + 9, (96, 192, 384), .75)
    rr = ell + 4. * fil
    knot = K.sstep(-.1, .4, fil)
    shell = np.exp(-((rr - Rn) / (1.4 + .06 * Rn)) ** 2) * (.4 + 1.2 * knot) * on
    shell2 = np.exp(-((rr - Rn * .68) / 1.1) ** 2) * K.sstep(.15, .55, fil) * on * .8
    inner = np.exp(-(ell / (Rn * .5)) ** 2) * on * (.35 + .5 * K.unit(K.noise(seed + 10, 180)))
    shells = [K.hexrgb('ff5a2a', 'ffd070'), K.hexrgb('30f0c0', 'ff40b0'), K.hexrgb('ffd060', 'ff3a7a')]
    cores = K.hexrgb('3a7aff', '9a50ff', '50c0ff')
    t = K.sstep(-.3, .6, fil)[..., None]
    s0 = np.array([s_[0] for s_ in shells], F32)[fam]; s1 = np.array([s_[1] for s_ in shells], F32)[fam]
    s1 -= s0; s1 *= t; s0 += s1
    scol = s0
    sh = np.clip(shell + shell2, 0, 1.4)
    paint = vel * (1 - np.clip(sh, 0, 1)[..., None]) + scol * sh[..., None]
    cf = cores[fam]; cf *= (inner * F32(.8))[..., None]; paint += cf
    spike = (np.exp(-np.abs(dx) / .8) * np.exp(-np.abs(dy) / 6) + np.exp(-np.abs(dy) / .8) * np.exp(-np.abs(dx) / 6)) * on
    star = np.exp(-(sd / 1.5) ** 2) * on
    stars = (pile > .9994).astype(F32)
    K.addc(paint, spike * .8 + star * 1.2 + stars * .8, (.9, .95, 1.))
    shc = np.clip(sh, 0, 1)
    tier = K.tiers(_per(ns, seed + 11)[sl])
    M = 3 + 18 * pile
    # lame velvet: ~18% metallic-but-rough pile threads (owner ask: more spec shades; also
    # decouples metal from roughness the way a real lame weave does). ASTRA-R2 M6 independence.
    lame = (pile > .86).astype(F32) * (1 - np.clip(shell + shell2, 0, 1))
    Rr = 250 - 70 * sheen - 30 * crease
    C = 255 - 30 * crease
    M = M * (1 - lame) + 215 * lame; Rr = Rr * (1 - lame) + (165 + 40 * pile) * lame
    C = C * (1 - lame) + (190 + 65 * K.fhash(np.floor(x), np.floor(y), seed + 21)) * lame
    M = M * (1 - shc) + (185 + 55 * tier) * shc; Rr = Rr * (1 - shc) + (55 - 30 * tier) * shc; C = C * (1 - shc) + 235 * shc  # dull-coat foil (NIGHTSHIFT night carrier)
    ic = np.clip(inner, 0, 1) * .8
    M = M * (1 - ic) + 140 * ic; Rr = Rr * (1 - ic) + 90 * ic
    st = np.clip(star + spike + stars, 0, 1)
    M = M * (1 - st) + 255 * st; Rr = Rr * (1 - st) + 16 * st; C = C * (1 - st) + 16 * st
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, mask=np.clip(shc + st, 0, 1), cc_lo=150.)
    M, Rr, C = K.enrich(M, Rr, C, seed + 992, cc_mix=.6, chrome=0., dull=0., mask=1 - np.clip(shc + st, 0, 1), cc_lo=205., cc_hi=255.)
    return K.pack(paint, M, Rr, C)
