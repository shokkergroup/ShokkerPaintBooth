"""ASTRA FUTURE SHOXX — engineered metamaterials (ten constructions).

SPB-105 / ASTRA-R2 2026-09-27 (Claude). Lane arc: MATTER THAT WAS DESIGNED —
every card is a precision-engineered surface (fold tessellations, photonic
chips, auxetic lattices, conformal zippers, voxel matter...) drawn with
crisp, exact geometry: hard edges, machined metals, lit emitters, and a spec
that separates the machined parts from the substrate they sit on.

Every function: (seed) -> (paint HxWx3 float 0..1, spec HxWx3 float 0..255).
"""
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


def _conformal(seed, n=512, count=26, alpha=.4):
    """Exact orthogonal (potential, stream) pair of a uniform flow past
    dipoles: w(z) = z e^{-i a} + sum d_k/(z - z_k). Returns (phi, psi, |w'|)."""
    r = K.rng(seed)
    ys, xs = np.mgrid[:n, :n].astype(np.float64) * (N / n) + N / n / 2
    z = xs + 1j * ys
    w = z * np.exp(-1j * alpha)
    dw = np.full(z.shape, np.exp(-1j * alpha))
    for _ in range(count):
        zk = complex(*r.uniform(0, N, 2)); dk = r.uniform(1500, 5000) * np.exp(1j * r.uniform(0, 6.28))
        q = z - zk
        q = np.where(np.abs(q) < 25, 25 * q / (np.abs(q) + 1e-9), q)
        w = w + dk / q; dw = dw - dk / q ** 2
    up = lambda a: cv2.resize(a.astype(F32), (N, N), interpolation=cv2.INTER_CUBIC)
    return up(w.real), up(w.imag), up(np.abs(dw))


# ============================================================ CAUSAL ORIGAMI
def causal_origami(seed=42):
    """Miura-ori folded metal-foil: straight horizontal folds and zigzag
    vertical folds make parallelogram facets in four orientations; a causal
    fold wave (a hidden field) changes the fold depth across the car so the
    facets flash differently, chrome mountain creases and dark valleys."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 45, 4)
    u0, v0 = K.rot(wx, wy, F32(.28))
    h = F32(15.); w = F32(13.); s = F32(5.5)
    j = np.floor(v0 / h)
    ty = v0 / h - j
    par = (j % 2).astype(F32)
    zig = s * np.where(par > 0, ty, 1 - ty)
    u = u0 - zig
    i = np.floor(u / w)
    fu = u / w - i
    fold = .35 + .65 * K.unit(K.fbm(seed + 2, (3, 6, 12), .55))
    sx = np.where((i % 2) == 0, F32(1.), F32(-1.)) * fold
    sy = np.where(par > 0, F32(1.), F32(-1.)) * fold * .55
    lit = (-.55 * sx - .8 * sy) / np.sqrt(1 + sx * sx + sy * sy)
    tone = .5 + .5 * lit
    hue = K.fhash(i, j, seed + 3)
    ori = ((i % 2) * 2 + par).astype(np.int32)
    duty = .18 + .64 * K.unit(K.fbm(seed + 8, (4, 8), .5))
    even = K.fhash(i, seed + 21) < duty
    drift = K.unit(K.fbm(seed + 6, (4, 8, 16), .55))
    warmc = K.hue_rgb(.90 + .07 * drift, .86, 1.)      # hot magenta-pink
    coolc = K.hue_rgb(.47 + .06 * drift, .92, 1.)      # teal-cyan (complement; NOT Chevron's gold/cobalt)
    base = np.where(even[..., None], warmc, coolc)
    base = K.mix(base, np.array([.95, .96, 1.], F32), K.sstep(.86, .98, hue) * .4)
    col = base * (.42 + .78 * tone)[..., None]
    cv_ = K.near(np.minimum(fu, 1 - fu) * w, .7)
    ch = K.near(np.minimum(ty, 1 - ty) * h, .7)
    mountain = np.where((i % 2) == 0, cv_, 0) + np.where(par > 0, ch, 0)
    valley = np.where((i % 2) == 1, cv_, 0) + np.where(par < 1, ch, 0)
    col = K.mix(col, np.array([1., 1., 1.], F32), np.clip(mountain, 0, 1) * .9)
    col = col * (1 - .7 * np.clip(valley, 0, 1))[..., None]
    tier = K.tiers(hue)
    M = np.where(even, 20 + 30 * tier, 230 + 20 * tier)
    C = np.where(even, 230 - 60 * tone, 30 + 120 * (1 - tone))
    Rr = K.r_from_luma(col, M, C)
    M, Rr, C = _over(M, Rr, C, np.clip(mountain, 0, 1), 255, 16, 16)
    M, Rr, C = _over(M, Rr, C, np.clip(valley, 0, 1), 60, 220, 255)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=1., cc_lo=16., cc_hi=255.)
    return K.pack(col, M, Rr, C)


# ======================================================= PHOTONIC SWITCHBOARD
def photonic_switchboard(seed=42):
    """A silicon photonics wafer: Manhattan waveguides with 45-degree bends
    carrying red, green and violet laser light, ring resonators glowing on
    their buses, grating-coupler combs, die streets with alignment crosses,
    and the wafer's interference sheen underneath."""
    r = K.rng(seed)
    x, y = K.xy()
    film = K.thin_film(K.unit(K.fbm(seed + 1, (2, 4, 8), .5)) * .9 + .2, .5, .16)
    wafer = np.full((N, N, 3), .05, F32) + film * .35
    street = np.maximum(K.near(np.abs(K.frac(x / F32(256.)) - .5) * 256, 1.5), K.near(np.abs(K.frac(y / F32(256.)) - .5) * 256, 1.5))
    guides = np.zeros((N, N, 3), np.uint8); core = np.zeros((N, N), np.uint8)
    rings = np.zeros((N, N, 3), np.uint8); comb = np.zeros((N, N), np.uint8)
    cols = [(255, 40, 60), (60, 255, 120), (150, 90, 255), (255, 170, 40)]
    G = 12
    dirs = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    for _ in range(300):
        p = np.array(r.integers(0, N // G, 2) * G, np.float64); d = int(r.integers(0, 8)) // 2 * 2
        c = cols[int(r.integers(0, 4))]; pts = [p.copy()]
        for s in range(int(r.integers(6, 16))):
            L = r.integers(2, 9) * G
            dv = np.array(dirs[d], np.float64); dv = dv / np.linalg.norm(dv)
            p = p + dv * L; pts.append(p.copy())
            d = (d + r.choice([-1, 1])) % 8
            if r.random() < .5:
                dv = np.array(dirs[d], np.float64); dv /= np.linalg.norm(dv); p = p + dv * G * 1.5; pts.append(p.copy())
                d = (d + r.choice([-1, 1])) % 8
            if r.random() < .12:
                cc = p + np.array([-dv[1], dv[0]]) * 11
                cv2.circle(rings, (int(cc[0] * 16), int(cc[1] * 16)), 8 * 16, c, 2, cv2.LINE_AA, 4)
        pp = np.round(np.array(pts) * 16).astype(np.int32)
        cv2.polylines(guides, [pp], False, c, 3, cv2.LINE_AA, 4)
        cv2.polylines(core, [pp], False, 255, 1, cv2.LINE_AA, 4)
        e = pts[-1]
        for k in range(-3, 4):
            q0 = e + np.array([k * 3., -7.]); q1 = e + np.array([k * 3., 7.])
            cv2.line(comb, (int(q0[0] * 16), int(q0[1] * 16)), (int(q1[0] * 16), int(q1[1] * 16)), 255, 1, cv2.LINE_AA, 4)
    gf = guides.astype(F32) / 255; rf = rings.astype(F32) / 255
    cf = core.astype(F32) / 255; kf = comb.astype(F32) / 255
    em = np.clip(gf + rf, 0, 1)
    glow = cv2.GaussianBlur(em, (0, 0), 3.) * 1.2 + cv2.GaussianBlur(em, (0, 0), 9.) * .6
    col = wafer * (1 - .5 * street)[..., None] + street[..., None] * np.array([.25, .28, .32], F32)
    col = col + glow * .7
    col = np.maximum(col, em * .9)
    col = K.mix(col, np.array([1., 1., 1.], F32), cf * .8)
    col = K.mix(col, np.array([.85, .8, .6], F32), kf)
    lit = np.clip(em.max(2) + cf, 0, 1)
    M = 150 + 60 * K.lum(film)
    Rr = 30 + 30 * street
    C = np.full((N, N), 16., F32)
    M, Rr, C = _over(M, Rr, C, np.clip(glow.max(2), 0, 1) * .5, 90, 60, 60)
    M, Rr, C = _over(M, Rr, C, lit, 20, 120, 200)
    M, Rr, C = _over(M, Rr, C, kf, 255, 20, 60)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(col, M, Rr, C)


# ===================================================== NEGATIVE SPACE ENGINE
def negative_space_engine(seed=42):
    """A perforated anodised-titanium skin over a live engine: a hex field of
    holes whose size is modulated by hidden gear-train silhouettes, so the
    machine exists only as negative space; through every hole glows the copper,
    machined core. v2: the plate is polished blue-to-violet anodised metal, the
    holes are matte copper light with a warm spill onto the plate (complements),
    and the gear trains open much wider, so the spec is the colour-opposite of
    the paint."""
    r = K.rng(seed)
    x, y = K.xy()
    gear = np.zeros((N, N), F32)
    for (gx, gy) in K.sites(seed + 1, 190, .9):
        Rg = r.uniform(40, 90); nt = int(Rg / 6); a0 = r.uniform(0, 6.28)
        x0, y0 = int(max(0, gx - Rg - 12)), int(max(0, gy - Rg - 12)); x1, y1 = int(min(N, gx + Rg + 12)), int(min(N, gy + Rg + 12))
        if x1 <= x0 or y1 <= y0:
            continue
        sx, sy = x[y0:y1, x0:x1] - gx, y[y0:y1, x0:x1] - gy
        rr = np.hypot(sx, sy); th = np.arctan2(sy, sx) + a0
        tooth = Rg + 7 * (np.cos(th * nt) > 0)
        ring = (rr < tooth) & (rr > Rg * .72)
        hub = (rr < Rg * .22) & (rr > Rg * .1)
        spokes = (rr < Rg * .75) & (np.abs(np.sin(th * 3)) * rr < 7) & (rr > Rg * .1)
        g = (ring | hub | spokes).astype(F32)
        gear[y0:y1, x0:x1] = np.maximum(gear[y0:y1, x0:x1], g)
    gear = K.blur(gear, 2.5)
    P = F32(12.)
    rh = P * F32(.866)
    row = np.floor(y / rh)
    best = None
    for dr in (0, 1):
        rw = row + dr
        uu = x / P - K.frac(rw * F32(.5))
        d = np.hypot((uu - np.round(uu)) * P, y - rw * rh)
        best = d if best is None else np.minimum(best, d)
    hr = 1.7 + 3.5 * gear
    hole = K.near(best, hr)
    rim = K.near(np.abs(best - hr - .8), .7) * (1 - hole)
    lathe = .5 + .5 * np.sin(np.hypot(x - 1024, y - 1024) * F32(K.TAU / 3.))
    core = K.ramp(np.clip(.4 + .4 * lathe + .25 * gear, 0, 1), ['a03008', 'e0600e', 'ff9a30', 'ffe0a0'])
    brush = K.noise(seed + 2, 900, interp=cv2.INTER_LINEAR) * .5
    hp = .57 + .17 * K.unit(K.fbm(seed + 6, (3, 6, 12), .55))
    pv = np.clip(.34 + .2 * np.clip(.5 + brush, 0, 1) + .06 * K.noise(seed + 3, 20), 0, 1)
    plate = K.hue_rgb(hp, .74, pv)
    col = plate * (1 - .5 * K.blur(hole, 1.5))[..., None]
    col += rim[..., None] * F32(.3)
    col = K.mix(col, core, hole)
    K.addc(col, K.blur(hole * gear, 5.) * .9, (1., .5, .15))
    M = 228 + 25 * brush
    C = 16 + 40 * (1 - pv)
    M = M * (1 - rim) + 255 * rim; C = C * (1 - rim) + 60 * rim
    M = M * (1 - hole) + 12 * hole; C = C * (1 - hole) + 228 * hole
    Rr = K.r_from_luma(col, M, C)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(col, M, Rr, C)


# ========================================================== TEMPORAL BRAILLE
def temporal_braille(seed=42):
    """A refreshable braille display the size of the car: lines of six-dot
    cells spell a random text, every raised pin a domed light. v2: bigger, denser
    cells over a backlit panel that drifts blue to violet to red, with every pin
    the COMPLEMENT of the panel colour beneath it; pins are polished metal on a
    matte panel, so the spec is the colour-opposite of the paint."""
    x, y = K.xy()
    cw, chh, lh = F32(20.), F32(28.), F32(38.)
    ln = np.floor(y / lh)
    ly = y - ln * lh
    xs = x + K.fhash(ln, None, seed) * 200
    ci = np.floor(xs / cw)
    lx = xs - ci * cw
    space = K.fhash(ci, ln, seed + 1) < .12
    col_i = np.where(lx < cw / 2, 0, 1)
    row_i = np.clip(np.floor((ly - 5) / 8.), 0, 2)
    dcx = np.where(col_i == 0, 5.5, 14.5); dcy = 9 + row_i * 8
    dd = np.hypot(lx - dcx, ly - dcy)
    bit = K.fhash(ci * 6 + col_i * 3 + row_i, ln, seed + 2) < .55
    on = bit & ~space & (ly < chh)
    Rd = F32(3.3)
    pin = K.near(dd, Rd) * on
    socket = K.near(np.abs(dd - 3.5), .6) * (~on) * (~space) * (ly < chh)
    dome = np.sqrt(np.clip(1 - (dd / Rd) ** 2, 0, 1)) * on
    hp = K.unit(K.fbm(seed + 3, (3, 6, 12), .55)) * .55 + .04 * K.fhash(ln, None, seed + 9) + .55
    panel_v = .24 + .14 * K.unit(K.fbm(seed + 6, (4, 8, 32), .6))
    panel = K.hue_rgb(hp, .85, panel_v)
    pinh = K.hue_rgb(hp + .5 + .04 * K.fhash(ci, ln, seed + 4), .6, 1.)
    hl = K.relief(dome * 3, 1.)
    pinc = pinh * (.65 + .5 * dome)[..., None] + np.clip(hl - .2, 0, 1)[..., None] * .8
    glow = K.blur(pin, 2.5) * 1.4
    guide = K.near(np.abs(ly - (chh + 2)), .5) * .5
    cur = (K.fhash(ci, ln, seed + 5) < .012) & (ly < chh + 3) & (lx > 2) & (lx < 13)
    col = panel + glow[..., None] * pinh * F32(.7)
    col += guide[..., None] * F32(.16)
    col += socket[..., None] * F32(.14)
    col = K.mix(col, pinc, pin)
    col = np.where(cur[..., None], np.array([.95, .97, 1.], F32), col)
    M = np.full((N, N), 12., F32)
    Rr = 198 + 20 * guide
    C = np.full((N, N), 230., F32)
    M, Rr, C = _over(M, Rr, C, np.clip(glow, 0, 1) * .5, 150, 90, 80)
    M, Rr, C = _over(M, Rr, C, pin, 245, 20 + 30 * (1 - dome), 16)
    M, Rr, C = _over(M, Rr, C, socket, 60, 235, 250)
    M = np.where(cur, 0, M); Rr = np.where(cur, 16, Rr)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=1., cc_lo=16., cc_hi=255.)
    return K.pack(col, M, Rr, C)


# ============================================================== KLEIN CIRCUIT
def klein_circuit(seed=42):
    """A printed circuit that loops back through itself: 45-degree routed
    buses of gold traces on black solder mask, a lilac inner layer glimpsed
    beneath, vias, pads and chip packages, and Klein bridges where a trace
    passes over itself."""
    r = K.rng(seed)
    x, y = K.xy()
    top = np.zeros((N, N), np.uint8); inner = np.zeros((N, N), np.uint8); vias = np.zeros((N, N), np.uint8)
    pads = np.zeros((N, N), np.uint8); bridge = np.zeros((N, N), np.uint8)
    G = 8
    dirs = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    for b in range(480):
        p = np.array(r.integers(0, N // G, 2) * G, np.float64); d = int(r.integers(0, 8))
        width = int(r.integers(2, 6)); tgt = top if r.random() < .65 else inner
        path = [p.copy()]
        for s in range(int(r.integers(4, 11))):
            dv = np.array(dirs[d], np.float64)
            p = p + dv * G * r.integers(3, 14); path.append(p.copy())
            d = (d + r.choice([-1, 1])) % 8
        path = np.array(path)
        for k in range(width):
            seg = np.diff(path, axis=0); nrm = np.stack([-seg[:, 1], seg[:, 0]], 1)
            nrm = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
            nrm = np.vstack([nrm[:1], (nrm[1:] + nrm[:-1]) / 2, nrm[-1:]])
            off = path + nrm * (k - (width - 1) / 2) * 9
            pp = np.round(off * 16).astype(np.int32)
            cv2.polylines(tgt, [pp], False, 255, 3, cv2.LINE_AA, 4)
            e = off[-1]
            cv2.circle(vias, (int(e[0] * 16), int(e[1] * 16)), 3 * 16, 255, 1, cv2.LINE_AA, 4)
        if r.random() < .3:
            m = path[len(path) // 2]
            cv2.circle(bridge, (int(m[0] * 16), int(m[1] * 16)), 7 * 16, 255, 2, cv2.LINE_AA, 4)
    for _ in range(140):
        cx, cy = r.uniform(0, N, 2); wd, ht = r.uniform(10, 30), r.uniform(6, 18)
        cv2.rectangle(pads, (int(cx * 16), int(cy * 16)), (int((cx + wd) * 16), int((cy + ht) * 16)), 255, -1, cv2.LINE_AA, 4)
    tf = top.astype(F32) / 255; inf = inner.astype(F32) / 255; vf = vias.astype(F32) / 255
    pf = pads.astype(F32) / 255; bf = bridge.astype(F32) / 255
    mask = K.ramp(K.unit(K.fbm(seed + 1, (4, 8, 64), .6)) * .5 + .1, ['040605', '0a0e0c', '121814'])
    col = mask + inf[..., None] * np.array([.35, .22, .5], F32)
    goldc = K.ramp(np.clip(.5 + .3 * K.noise(seed + 2, 40), 0, 1), ['a07a20', 'e8c050', 'fff0a0'])
    col = K.mix(col, goldc, tf)
    col = K.mix(col, np.array([.08, .08, .1], F32), pf * .95)
    col = col + (K.near(np.abs(K.blur(pf, 1.) - .5), .15) * .3)[..., None]
    col = K.mix(col, np.array([.9, .92, 1.], F32), vf)
    col = K.mix(col, np.array([.7, .6, 1.], F32), bf * .9)
    M = np.full((N, N), 10., F32)
    Rr = 40 + 30 * inf
    C = np.full((N, N), 16., F32)
    M, Rr, C = _over(M, Rr, C, tf, 255, 50, 200)
    M, Rr, C = _over(M, Rr, C, pf, 0, 200, 240)
    M, Rr, C = _over(M, Rr, C, np.clip(vf + bf, 0, 1), 255, 16, 40)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================ AUXETIC EXOSKIN
def auxetic_exoskin(seed=42):
    """A rotating-squares auxetic metamaterial: bevelled gunmetal plates
    hinged corner to corner, each turned the opposite way to its neighbours;
    a hidden strain field opens and closes the lattice across the car, the
    diamond gaps glowing ember-red from the skin beneath."""
    x, y = K.xy()
    wx, wy = K.warp(seed + 1, 30, 4)
    u, v = K.rot(wx, wy, F32(.4))
    P = F32(22.)
    i = np.floor(u / P); j = np.floor(v / P)
    lu = u - (i + .5) * P; lv = v - (j + .5) * P
    strain = K.unit(K.fbm(seed + 2, (8, 16, 32), .6))
    th = (.05 + .5 * strain) * np.where(((i + j) % 2) == 0, F32(1.), F32(-1.))
    ru, rv = K.rot(lu, lv, th)
    s = (P / 2) / (np.cos(np.abs(th)) + np.sin(np.abs(th)))
    cheb = np.maximum(np.abs(ru), np.abs(rv))
    plate = K.near(cheb, s - .4)
    bev = np.clip((s - cheb) / 3., 0, 1)
    face = np.where(np.abs(ru) > np.abs(rv), np.sign(ru), np.sign(rv) * 2)
    shade = np.where(bev < 1, .75 + .12 * face, 1.)
    tone = K.fhash(i, j, seed + 3)
    metal = K.ramp(np.clip(.3 + .35 * tone + .25 * bev, 0, 1), ['1a1e26', '3a4250', '6a7686', 'a8b4c4'])
    metal = metal * shade[..., None]
    pin = K.near(np.hypot(np.abs(ru) - s * .55, np.abs(rv) - s * .55), 1.3) * plate
    ember = K.ramp(np.clip(strain + .2 * K.noise(seed + 4, 60), 0, 1), ['400400', 'a01800', 'ff4a00', 'ffb040'])
    col = K.mix(ember * (.5 + .6 * (1 - plate))[..., None], metal, plate)
    col = K.mix(col, np.array([.95, .95, 1.], F32), pin)
    col = col + (K.blur(1 - plate, 3.) * .25)[..., None] * np.array([1., .3, .05], F32)
    tier = K.tiers(tone)
    M = 230 + 20 * tier
    Rr = 190 - 170 * K.lum(col) + 10 * tier
    C = 200 - 100 * bev
    M, Rr, C = _over(M, Rr, C, 1 - plate, 20, 200, 240)
    M, Rr, C = _over(M, Rr, C, pin, 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991, cc_mix=.8)
    return K.pack(col, M, Rr, C)


# ======================================================= MEMORY METAL ZIPPER
def memory_metal_zipper(seed=42):
    """Zippers laid along an exact conformal flow (uniform stream past hidden
    obstacles, so every zipper stays parallel to its neighbours): alternating
    nitinol teeth in heat-tinted copper and silver interlock along each
    track, dark woven tape either side, and some runs spring open."""
    x, y = K.xy()
    phi, psi, gw = _conformal(seed + 1)
    sp = F32(46.)
    k = np.floor(psi / sp)
    f = (psi / sp - k - .5) * sp / np.maximum(gw, .2)
    tp = F32(9.)
    t = phi / np.maximum(1, 1) / tp
    ti = np.floor(t); tf = t - ti
    side = (ti % 2 == 0)
    open_ = K.sstep(.55, .7, K.unit(K.fbm(seed + 2, (4, 8, 16), .55)))
    shift = np.where(side, -1., 1.) * open_ * 5
    fl = f - shift
    tooth_x = (np.abs(tf - .5) < .38)
    tooth = tooth_x & np.where(side, (fl > -8.5) & (fl < 1.6), (fl < 8.5) & (fl > -1.6)) & (gw < 2.2)
    toothf = tooth.astype(F32)
    tape = (np.abs(f) < 16) & ~tooth
    weave = .5 + .5 * np.sin(phi * F32(K.TAU / 2.5)) * np.sin(f * F32(K.TAU / 2.5))
    heat = K.frac(k * .37 + .25 * K.noise(seed + 3, 30))
    cop = np.clip(K.thin_film(heat * .5 + .15, .6, .62) * np.array([1.25, .8, .5], F32), 0, 1)
    sil = np.array([.8, .82, .86], F32) * (.85 + .2 * heat)[..., None]
    tc = K.mix(sil, cop, side.astype(F32))
    bump = np.clip(1 - np.abs(tf - .5) / .38, 0, 1)
    tc = tc * (.6 + .5 * bump)[..., None]
    th_ = K.frac(K.fhash(k, None, seed + 4) * .35 + .3 * K.unit(K.fbm(seed + 7, (3, 6), .5)))
    tapec = K.hue_rgb(th_, .75, .55 + .3 * weave)
    bg = K.ramp(K.unit(K.fbm(seed + 5, (4, 8), .5)), ['101010', '1a1a1e'])
    col = np.where(tape[..., None], tapec, bg)
    col = K.mix(col, tc, toothf)
    edge = K.near(np.abs(np.abs(f) - 16), .7)
    col = col * (1 - .6 * edge)[..., None]
    tier = K.tiers(K.fhash(ti, k, seed + 6))
    M = np.where(tape, 20, 60).astype(F32)
    Rr = np.where(tape, 200 - 40 * weave, 180).astype(F32)
    C = np.where(tape, 240, 240).astype(F32)
    M, Rr, C = _over(M, Rr, C, toothf, 235 + 20 * tier, 20 + 50 * (1 - bump), 200)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ======================================================= ORBITLESS NAVIGATION
def orbitless_navigation(seed=42):
    """A portolan chart with no orbits, only rhumbs: dozens of hidden wind
    roses shoot their 32 rhumb lines straight across the car in the old
    colour code (principal winds gold, half-winds green, quarter-winds
    red), the web crossing a sea-green vellum with graticule and gilt
    compass stars."""
    r = K.rng(seed)
    x, y = K.xy()
    vellum = K.ramp(K.unit(K.fbm(seed + 1, (3, 6, 12, 48), .6)), ['031a22', '06303a', '0a4450', '125a64'])
    fib = K.noise(seed + 2, 500, interp=cv2.INTER_LINEAR)
    col = vellum * (1 + .04 * fib)[..., None]
    L = [np.zeros((N, N), np.uint8) for _ in range(3)]
    roses = K.sites(seed + 3, 380, .95)
    stars = np.zeros((N, N), np.uint8)
    for (cx, cy) in roses:
        a0 = r.uniform(0, np.pi / 16)
        for k in range(32):
            a = a0 + k * np.pi / 16
            cls = 0 if k % 4 == 0 else (1 if k % 2 == 0 else 2)
            d = np.array([np.cos(a), np.sin(a)])
            e = np.array([cx, cy]) + d * 3000
            cv2.line(L[cls], (int(cx * 16), int(cy * 16)), (int(e[0] * 16), int(e[1] * 16)), 255, 1, cv2.LINE_AA, 4)
        pts = []
        R1, R2 = 16, 5
        for k in range(32):
            a = a0 + k * np.pi / 16; rad = R1 if k % 4 == 0 else (R1 * .6 if k % 2 == 0 else R2)
            pts.append((cx + np.cos(a) * rad, cy + np.sin(a) * rad))
        cv2.fillPoly(stars, [np.round(np.array(pts) * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
    lf = [l.astype(F32) / 255 for l in L]
    cols = [np.array([1., .78, .25], F32), np.array([.2, .95, .55], F32), np.array([1., .3, .25], F32)]
    for c, w in zip(cols, lf):
        col = K.mix(col, c, w * .85)
    g = np.maximum(K.near(np.abs(K.frac(x / F32(128.)) - .5) * 128, .4), K.near(np.abs(K.frac(y / F32(128.)) - .5) * 128, .4)) * .35
    col = col + (g * .25)[..., None] * np.array([.4, .7, .8], F32)
    sf = stars.astype(F32) / 255
    sh = K.relief(K.blur(sf, 1.) * 3, 1.)
    col = K.mix(col, np.array([.95, .75, .3], F32) * (.8 + .4 * np.clip(sh + .3, 0, 1))[..., None], sf)
    anyl = np.clip(lf[0] + lf[1] + lf[2], 0, 1)
    M = 10 + 20 * fib
    Rr = 200 + 20 * fib
    C = np.full((N, N), 220., F32)
    M, Rr, C = _over(M, Rr, C, lf[0], 240, 40, 120)
    M, Rr, C = _over(M, Rr, C, np.clip(lf[1] + lf[2], 0, 1), 30, 60, 30)
    M, Rr, C = _over(M, Rr, C, sf, 255, 20, 60)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ============================================================ TACHYON FEATHER
def tachyon_feather(seed=42):
    """Plumage faster than light: overlapping contour feathers along a swept
    flow, each with a bright rachis and hundreds of barbs, structurally
    coloured like a hummingbird gorget so the hue shifts barb by barb, with
    Cherenkov-blue streaks trailing from the tips."""
    r = K.rng(seed)
    x, y = K.xy()
    th = K.fbm(seed + 1, (2, 4), .5) * F32(np.pi * .8)
    pts = K.sites(seed + 2, 24, .95)
    order = np.argsort(pts[:, 1] + r.uniform(0, 40, len(pts)))
    pts = pts[order]
    n = len(pts)
    pi = np.clip(pts.astype(np.int32), 0, N - 1)
    ang = (th[pi[:, 1], pi[:, 0]] + r.normal(0, .12, n)).astype(F32)
    L = r.uniform(40, 62, n).astype(F32); W = r.uniform(8, 12, n).astype(F32)
    tt = np.linspace(-.5, .5, 12)
    prof = np.clip(np.sin(np.pi * (tt + .5)) ** .6, 0, 1) * (1 - .35 * (tt + .5))
    d = np.stack([np.cos(ang), np.sin(ang)], 1); m = np.stack([-d[:, 1], d[:, 0]], 1)
    a1 = pts[:, None, :] + d[:, None, :] * (tt[None, :, None] * L[:, None, None]) + m[:, None, :] * (prof[None, :, None] * W[:, None, None])
    a2 = pts[:, None, :] + d[:, None, :] * (tt[::-1][None, :, None] * L[:, None, None]) - m[:, None, :] * (prof[::-1][None, :, None] * W[:, None, None])
    ids = K.stamp_ids(np.concatenate([a1, a2], 1))
    k = np.maximum(ids, 0); on = ids >= 0
    u, v = K.id_local(ids, pts[:, 0], pts[:, 1], ang, x, y)
    Lk = L[k]; Wk = W[k]
    along = np.clip(u / Lk + .5, 0, 1)
    barb = .5 + .5 * np.cos((u * F32(.62) - np.abs(v) * F32(1.)) * F32(K.TAU / 3.2))
    rach = K.near(np.abs(v), .8) * on
    film = K.thin_film(.25 + .55 * along + .25 * np.abs(v) / Wk + .15 * K.fhash(ids.astype(F32), None, seed + 3), 1.2, .5)
    fc = film * (.35 + .75 * barb)[..., None] * (.6 + .5 * (1 - np.abs(v) / Wk))[..., None]
    fc = K.mix(fc, np.array([.95, .92, .85], F32), rach * .9)
    tip = np.exp(-np.maximum(0, u - Lk * .3) / 6) * (u > Lk * .3) * on
    col = np.where(on[..., None], fc, np.array([.02, .02, .05], F32))
    streak = K.blur((tip > .5).astype(F32), 3.) * .5
    col = col + streak[..., None] * np.array([.3, .6, 1.], F32)
    M = np.where(on, 150 + 90 * barb, 30).astype(F32)
    Rr = np.where(on, 90 - 70 * barb, 200).astype(F32)
    C = np.where(on, 16 + 40 * (1 - barb), 240).astype(F32)
    M, Rr, C = _over(M, Rr, C, rach, 255, 16, 16)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)


# ======================================================== PROGRAMMABLE MATTER
def programmable_matter(seed=42):
    """Programmable matter at rest: an isometric field of voxel modules,
    each cube's three faces lit top/left/right, colour-coded by the state a
    hidden program has written into them; empty slots show the dark lattice
    below and active modules carry glowing edge LEDs."""
    x, y = K.xy()
    S = F32(12.)
    a = x / (S * F32(1.7320508)); b = y / S
    q = a - b * F32(.5773503) * 0
    # axial hex lattice (pointy-top) for the cube silhouettes
    qf = (x * F32(.5773503) - y / 3.) / S
    rf = (2. / 3.) * y / S
    xf = qf; zf = rf; yf = -xf - zf
    rx, ry, rz = np.round(xf), np.round(yf), np.round(zf)
    dx, dy, dz = np.abs(rx - xf), np.abs(ry - yf), np.abs(rz - zf)
    rx = np.where((dx > dy) & (dx > dz), -ry - rz, rx)
    rz = np.where(~((dx > dy) & (dx > dz)) & ~(dy > dz), -rx - ry, rz)
    cx = S * F32(1.7320508) * (rx + rz / 2); cy = S * 1.5 * rz
    lu = x - cx; lv = y - cy
    ang = np.arctan2(lv, lu)
    face = np.where(lv < 0, 0, np.where(lu < 0, 1, 2)).astype(np.int32)
    face = np.where((np.abs(lu) * F32(.5773503) > -lv) & (lv < 0), 0, np.where(lu < 0, 1, 2))
    bq = np.floor((rx + 1000) / 4); bz = np.floor((rz + 1000) / 4)
    code = np.floor(K.fhash(bq, bz, seed + 1) * 5 + .45 * K.fhash(rx, rz, seed + 2))
    empty = K.fhash(rx, rz, seed + 3) < .08
    active = K.fhash(rx, rz, seed + 4) < .18
    pal = K.hexrgb('ff3a6a', 'ffb020', '2ad8a0', '2a8aff', 'b04aff', 'e8eef4')
    base = pal[np.clip(code, 0, 5).astype(np.int32)]
    shade = np.array([1., .72, .5], F32)[face]
    col = base * shade[..., None]
    hexd = np.maximum(np.abs(lu) * F32(.866) + np.abs(lv) * .5, np.abs(lv))
    edge_out = K.near(np.abs(hexd - S * .98), .8)
    edge_in = np.where(face == 0, 0, K.near(np.abs(lu), .6) * (lv > 0)) + K.near(np.abs(lv - np.abs(lu) * F32(.5773503) * 0) * 0 + np.abs(np.abs(lu) * F32(.5773503) + lv), .6) * (lv < 0) * 0
    edges = np.clip(edge_out + edge_in, 0, 1)
    col = col * (1 - .55 * edges)[..., None]
    led = edges * active
    col = K.mix(col, np.array([.9, 1., 1.], F32), led)
    col = np.where(empty[..., None], np.array([.04, .05, .07], F32) * (1 + shade[..., None]), col)
    tier = K.tiers(K.fhash(rx, rz, seed + 5))
    M = 60 + 120 * (face == 0) + 40 * tier
    Rr = 140 - 100 * shade + 20 * tier
    C = 16 + 60 * (1 - shade)
    M, Rr, C = _over(M, Rr, C, led, 255, 16, 16)
    M, Rr, C = _over(M, Rr, C, empty.astype(F32), 20, 230, 250)
    M, Rr, C = K.enrich(np.asarray(M, F32).copy(), np.asarray(Rr, F32).copy(), np.asarray(C, F32).copy(), seed + 991)
    return K.pack(col, M, Rr, C)
