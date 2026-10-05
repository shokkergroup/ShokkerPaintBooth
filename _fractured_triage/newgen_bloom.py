# ════════════════════════════════════════════════════════════════════════════
# THE IN-BAND FIELD LAW  [SPB-FRACTURED-090b 2026-08-02] — owner: "push the
# others to the same levels ... WITHOUT it being static noise or just a bunch
# of repeats." Measured frequency budget of the 512 paint (FFT power of luma,
# ring r in [64,256] over total r >= 2):
#
#     r =  64  <=> period 8.0 px at 512 <=> 10.0 px at GEN 640 <=> 32 px @2048
#     r = 256  <=> period 2.0 px at 512 <=>  2.5 px at GEN 640 <=>  8 px @2048
#
# and the anti-static guard (lag-1 horizontal autocorrelation >= 0.55, because
# white noise scores band ~0.95 and is a FAILURE) puts a CEILING on the same
# axis: an isotropic ring at radius r contributes J0(2*pi*r/512) to that
# autocorrelation — r=74 pays 0.80, r=128 pays 0.47, r=200 pays -0.03. So the
# whole field has to live in a 6-10 px window at GEN (== _P0 below), and the
# ONE shape that beats the trade is a TILTED stripe/lattice: its 2-D radius
# sits high in the band while its x-period stays long (high coherence).
#
# Four laws, none of which is "add noise":
#   L1 RELIEF, NOT TINT — value rides a SMOOTH PERIODIC relief inside each
#      cell (dome / rib / crown / bevel). A flat per-cell tint is a LOW-pass
#      field: its power sits under r=64 (a raw 8-tier pave measures band 0.15).
#   L2 FAT SEAMS — cells are separated by a WIDE smooth edge-distance seam.
#      Fat seams concentrate power at the lattice fundamental; hairlines smear
#      it into r>200 harmonics that buy no band and wreck coherence.
#   L3 BOUNDED JITTER — jitter <= ~0.5 cell keeps a preferred period, i.e. a
#      sharp spectral fundamental (the peakiness guard). Free worley smears it.
#   L4 NO fbm IN THE LUMA — an fbm pyramid is 1/f: most of its power lands
#      UNDER the band. Every fbm-derived luma term (fine grain, tiers,
#      turbulence, ridged veins, clump envelopes, wobbles) is replaced by an
#      in-band lattice equivalent. fbm survives only as a domain-warp or a
#      flow-direction field, where it moves geometry instead of adding luma.
#
# Identity is carried by HUE anchors that follow the geometry (hue_drift /
# the hue-probe in _FieldKit), never by value swings (vd) or interference
# phase (tmod) — both are low-frequency, and the metric is a ratio, so macro
# luma drama is charged twice.
# ════════════════════════════════════════════════════════════════════════════

_P0 = 10.4   # canonical lattice pitch in _S units == 8.7 px at GEN 640
             # == 6.9 px at 512 == r 74 (J0 0.80) == 28 px on a 2048 car.


def _flat(x, s=2.5):
    """LOW-CUT a value field: subtract its own local mean, keep the global
    mean. Not a sharpen and not noise — every shape and edge survives; only
    the slow wander that lands under r=64 is deleted (law L1/L3)."""
    x = np.asarray(x, np.float32)
    return x - gauss(x, float(s)) + float(x.mean())


def _fat(d, w, soft=0.34):
    """Fat smooth seam profile from a 0..1 edge-distance field (0 = seam
    centre) -> 1 on the seam, 0 inside the cell (law L2)."""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _grain(xx, yy, cell, salt, thr=0.62):
    """Per-cell speckle — [090b] now DOMED and floored INSIDE the car band.
    A hard hash step on a 2 px cell at GEN puts all of its power above r=256
    (pure denominator); a smooth bump on a >= 4 px cell carries the lattice
    fundamental instead. Signature unchanged."""
    res = int(np.asarray(xx).shape[0])
    c = max(float(cell), 4.0 * res / 640.0)
    du = frac(xx / c) - 0.5
    dv = frac(yy / c) - 0.5
    dome = np.clip(1.0 - 3.6 * (du * du + dv * dv), 0.0, 1.0)
    g = h2(np.floor(xx / c), np.floor(yy / c), salt)
    return sstep(thr, min(thr + 0.18, 0.999), g) * dome


def _fine(res, seed, k=0.13):
    """Closing micro-relief. [090b] LAW L4: this was ridged fbm(base 180)
    plus an fbm octave at base 320 — a 1/f pyramid (most of its power under
    r=64) plus an above-band octave, i.e. leak at both ends. Now ONE
    value-noise octave at ~8 px at GEN with its slow drift subtracted, so
    every photon of it lands inside the car band."""
    n = max(4, int(round(res / 8.0)))
    g = fbm(res, res, rng(seed, 811), 1, n)
    g = g - gauss(g, 2.0 * res / 640.0)
    return (g / (float(g.std()) + 1e-6) * (0.32 * float(k))).astype(np.float32)


def _ptier(res, cell, salt, ang=0.0, relief=0.55, jit=0.30):
    """8-tier tint on an IN-BAND domed patch lattice (law L1): the tint
    arrives WITH its own smooth relief, so it is band-pass instead of the
    low-pass skirt a flat per-cell value leaves behind."""
    yy, xx = coords(res)
    if ang:
        ca, sa = np.cos(float(ang)), np.sin(float(ang))
        u, v = xx * ca + yy * sa, -xx * sa + yy * ca
    else:
        u, v = xx, yy
    c = float(cell)
    ci, cj = np.floor(u / c), np.floor(v / c)
    jx = (h2(ci, cj, salt + 3) - 0.5) * float(jit)
    jy = (h2(ci, cj, salt + 7) - 0.5) * float(jit)
    d = np.maximum(np.abs(frac(u / c) - 0.5 + jx),
                   np.abs(frac(v / c) - 0.5 + jy)) * 2.0
    return _tier(h2(ci, cj, salt)) * (1.0 - relief + relief * sstep(1.02, 0.24, d))


def _cells(res, pitch, salt, jit=0.85, taps=9, need2=True):
    """Jittered-grid nearest-feature field. Returns (dx, dy, d1, id1, d2):
    offset to / distance to the nearest feature point in px, per-feature hash
    id, and second-nearest distance (None when need2=False). The one kernel
    that lets a generator stamp THOUSANDS of 8-32px features vectorized.
    Perf: the per-cell hashes are computed ONCE on the coarse cell grid and
    gathered per tap (27 full-res sin evals -> 3 tiny grids + cheap int
    gathers); dot-stamp layers can run taps=5 / need2=False.
    [090b] callers now pass BOUNDED jitter (<= ~0.55, law L3) so the lattice
    keeps a sharp spectral fundamental."""
    g = float(pitch)
    yy, xx = coords(res)
    cu = np.floor(xx / g)
    cv_ = np.floor(yy / g)
    n = int(np.ceil(res / g)) + 4
    ii = np.arange(-1, n, dtype=np.float32)
    CU, CV = np.meshgrid(ii, ii)
    JX = h2(CU, CV, salt)
    JY = h2(CU, CV, salt + 57)
    JB = h2(CU, CV, salt + 91)
    iu = cu.astype(np.int32) + 1
    iv = cv_.astype(np.int32) + 1
    best = np.full((res, res), 1e9, np.float32)
    second = np.full((res, res), 1e9, np.float32) if need2 else None
    bdx = np.zeros((res, res), np.float32)
    bdy = np.zeros((res, res), np.float32)
    bid = np.zeros((res, res), np.float32)
    offs = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1))[:int(taps)]
    for di, dj in offs:
        ix = np.clip(iu + di, 0, n)
        iy = np.clip(iv + dj, 0, n)
        jx = JX[iy, ix]
        jy = JY[iy, ix]
        fx = (cu + (di + 0.5) + (jx - 0.5) * jit) * g
        fy = (cv_ + (dj + 0.5) + (jy - 0.5) * jit) * g
        ddx = xx - fx
        ddy = yy - fy
        d = ddx * ddx + ddy * ddy
        m = d < best
        if need2:
            second = np.where(m, best, np.minimum(second, d))
        best = np.where(m, d, best)
        bdx = np.where(m, ddx, bdx)
        bdy = np.where(m, ddy, bdy)
        bid = np.where(m, JB[iy, ix], bid)
    return (bdx, bdy, np.sqrt(best), bid,
            np.sqrt(second) if need2 else None)


def _pave(res, p, salt, jit=0.45, seam=0.22, taps=9):
    """THE workhorse of the rebuild: a bounded-jitter cell pave carrying its
    own in-cell RELIEF and a fat edge-distance seam (laws L1-L3). Returns
    (dx, dy, d1, id1, edge, crown, seam_mask) where `edge` is 0 on the
    polygon boundary and `crown` is the smooth dome whose period IS the
    lattice fundamental — the term that moved this module's value off flat
    per-cell tints and into the car band."""
    dx, dy, d1, id1, d2 = _cells(res, p, salt, jit, taps=taps, need2=True)
    edge = (d2 - d1) / p
    return dx, dy, d1, id1, edge, sstep(0.02, 0.40, edge), _fat(edge, float(seam))


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — 20 distinct field archetypes, one per finish id.
# Every one: a dense in-band micro-field per the law above; the ARCHETYPE
# LEDGER at the top of the module is unchanged (one composition per id).
# [SPB-FRACTURED-090b 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_rosette(res, seed, pitch=_P0, rings=1.30, petals=7.0, dome=0.46,
              body=0.24, seam=0.20, fine=0.11):
    """rosette tier-pack — a pave of small scalloped ring whorls, each DOMED
    (L1) and cut from its neighbours by a fat petal-gap seam (L2)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.42, seam)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.62)
    scal = 0.09 * np.cos(th * petals + id1 * 61.0)
    ring = 0.5 + 0.5 * np.cos((rr + scal) * rings * _TAU + id1 * 11.0)
    T = (0.12 + crown * dome + ring * ring * 0.24 * (0.30 + 0.70 * crown)
         + _flat(_tier(id1), 3.0 * s) * body * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def g_pleat(res, seed, col=13.0, rib=9.2, slope=0.45, dome=0.36, fine=0.11):
    """chevron pleats — herringbone columns of pinnate leaflet ribs. [090b]
    rib pitch 3.8 -> 7.7 px at GEN and chevron slope 0.85 -> 0.45: the old
    geometry put its x-period at 3.6 px at 512, which is a NEGATIVE lag-1
    autocorrelation (this finish measured 0.035, the module's worst). A
    tilted stripe keeps its 2-D radius in the band while its x-period stays
    long — the one shape that wins both gates at once."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 23, 4.0)
    X = xx + wu
    Y = yy + wv
    cw = col * s
    ci = np.floor(X / cw)
    u = frac(X / cw)
    sign = 1.0 - 2.0 * np.mod(ci, 2.0)
    q = Y / (rib * s) + sign * u * (cw / (rib * s)) * slope
    ribs = 0.5 + 0.5 * np.cos(q * _TAU)
    seam = sstep(0.09, 0.0, np.minimum(u, 1.0 - u))
    tier = _flat(_tier(h2(ci, np.floor(q), sd + 5)), 3.0 * s)
    T = 0.16 + ribs * dome + tier * 0.30 * (0.30 + 0.70 * ribs)
    return n01(T * (1.0 - 0.55 * seam) + _fine(res, seed, fine))


def g_pinwheel(res, seed, pitch=_P0, arms=4.0, twist=1.1, dome=0.44,
               seam=0.20, fine=0.11):
    """pinwheel curl pave — a field of tiny log-spiral petal whorls, the
    spiral cut INTO the cell dome instead of drawn on a flat tint."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.40, seam)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.60)
    sp = (0.5 + 0.5 * np.cos(th * arms + rr * twist * _TAU + id1 * 43.0)) ** 1.6
    T = (0.12 + crown * dome + sp * 0.26 * (0.25 + 0.75 * crown)
         + _flat(_tier(id1), 3.0 * s) * 0.24 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def g_billow(res, seed, pitch=_P0, lx=0.62, ly=0.79, dome=0.50, seam=0.24,
             fine=0.10):
    """micro-billows — close-packed shaded petal cushions with kissing
    contact shadows. The cushion IS the relief (L1); the light term is a
    lambert tilt across the same dome, so it adds no extra frequency."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.48, seam)
    rr = d1 / (p * 0.70)
    lam = np.clip((dx * lx + dy * ly) / np.maximum(d1, 1e-4), -1.0, 1.0)
    lam = lam * np.sqrt(np.clip(rr, 0.0, 1.0))
    T = (0.13 + crown * dome + lam * 0.16 * crown
         + _flat(_tier(id1), 3.0 * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) + _fine(res, seed, fine))


def g_lamina(res, seed, pitch=7.6, angle=0.9, warp=5.0, cross=0.65,
             fine=0.12):
    """directional lamina eddies — warp-combed fine petal sheets. [090b] the
    warp amplitude dropped 30 -> 5 px: a big warp smears the stripe
    fundamental across the whole spectrum (it was costing both band and
    peakiness), while a small one still bends the sheets into eddies."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 41, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wu) * ca + (yy + wv) * sa) / (pitch * s)
    lam = 0.5 + 0.5 * np.cos(q * _TAU)
    q2 = ((xx - wv) * sa - (yy - wu) * ca) / (pitch * cross * s)
    xl = 0.5 + 0.5 * np.cos(q2 * _TAU)
    tier = _flat(_tier(h2(np.floor(q), np.floor(q2 * 0.5), sd + 9)), 3.0 * s)
    T = 0.14 + lam * 0.44 + xl * 0.14 * lam + tier * 0.26 * (0.30 + 0.70 * lam)
    return n01(T + _fine(res, seed, fine))


def g_rdlab(res, seed, cell=8.6, iters=5, gain=1.5, sig=1.6, fine=0.10):
    """reaction-diffusion petal labyrinth. [090b] LAW L4: the RD seed was a
    3-octave fbm, so the maze inherited the pyramid's sub-band skirt. It now
    grows from ONE band-passed octave at the target maze period, which is
    also what a real Turing system does — one unstable wavelength."""
    s = res / _S
    sd = _sd(seed)
    n = max(4, int(round(res / (cell * s))))
    f = fbm(res, res, rng(seed, 55), 1, n)
    f = n01(f - gauss(f, 2.2 * s))
    for _ in range(int(iters)):
        f = np.clip(f + gain * (f - gauss(f, sig * s)), 0.0, 1.0)
    lab = sstep(0.34, 0.66, f)
    rim = 1.0 - np.abs(2.0 * lab - 1.0)
    T = (0.16 + lab * 0.44 + rim * 0.20
         + _ptier(res, 9.0 * s, sd + 3, relief=0.7) * 0.24)
    return n01(T + _fine(res, seed, fine))


def g_imbric(res, seed, sw=10.6, rh=7.2, ribs=3.0, fine=0.10):
    """scale imbrication — shingled fan-ribbed petal scales in offset rows.
    [090b] 9 fan ribs inside a 9 px scale is a 1 px feature (above the band
    and pure denominator); 3 ribs is a 3 px feature that reads as a fan and
    lands in the band."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 61, 4.0)
    u = (xx + wu) / (sw * s)
    v = (yy + wv) / (rh * s)
    T = np.zeros((res, res), np.float32)
    done = np.zeros((res, res), np.float32)
    for k in (1, 0):
        uu = u + 0.5 * k
        vv = v + 0.5 * k
        cu = np.floor(uu)
        cv_ = np.floor(vv)
        du = (uu - cu - 0.5) * (sw * s)
        dv = (vv - cv_ - 0.15) * (rh * s)
        rrad = np.hypot(du, dv * 0.9) / (sw * s * 0.60)
        inside = sstep(1.02, 0.90, rrad)
        th = np.arctan2(du, dv + 1e-4)
        fan = 0.5 + 0.5 * np.cos(th * ribs + h2(cu, cv_, sd + 7) * 6.0)
        crown = np.clip(1.0 - rrad * rrad, 0.0, 1.0)
        val = (0.14 + crown * 0.46 + fan * 0.14 * crown
               + _flat(_tier(h2(cu, cv_, sd)), 3.0 * s) * 0.26
               * (0.25 + 0.75 * crown))
        T = T + val * inside * (1.0 - done)
        done = np.clip(done + inside, 0.0, 1.0)
    return n01(T + (1.0 - done) * 0.10 + _fine(res, seed, fine))


def g_foam(res, seed, pitch=_P0, wall=0.30, fine=0.10):
    """polyp foam pack — bright-walled foam cells with dark mouth pores. The
    WALL is the fat seam (L2) and the cell floor is a shallow inverted dome,
    so the wall lattice fundamental carries the value."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.52, wall)
    rr = d1 / (p * 0.72)
    mouth = _bump((d1 / (2.0 * s)) ** 2) * 0.30
    T = (0.14 + gs * 0.44 + (1.0 - crown) * 0.10
         + _flat(_tier(id1), 3.0 * s) * 0.26 * (0.30 + 0.70 * crown)
         + crown * 0.20 - mouth)
    return n01(T + _fine(res, seed, fine))


def g_platemosaic(res, seed, pitch=11.0, petals=6.0, seam=0.26, fine=0.10):
    """plate-mosaic — grouted plates, each stamped with a ray floret. The
    plate now carries a crown (L1) and the grout is fat (L2)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.44, seam)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.60)
    ring = sstep(0.20, 0.06, np.abs(rr - 0.44))
    ring = ring * (0.55 + 0.45 * np.cos(th * petals + id1 * 31.0))
    disc = sstep(0.26, 0.12, rr) * 0.24
    T = (0.13 + crown * 0.40 + ring * 0.24 + disc
         + _flat(_tier(id1), 3.0 * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.90 * gs) + _fine(res, seed, fine))


def g_petalcells(res, seed, pitch=_P0, seam=0.22, fine=0.10):
    """interlocking petal-cross cells — packed 4-lobe florets. The lobe
    pattern MODULATES the cell dome rather than sitting on a flat tint."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.38, seam)
    th = np.arctan2(dy, dx)
    a0 = id1 * _TAU
    lobe = np.abs(np.cos((th - a0) * 2.0)) ** 1.2
    vein = sstep(0.12, 0.02, np.abs(np.sin((th - a0) * 2.0))) * crown * 0.20
    eye = _bump((d1 / (2.2 * s)) ** 2) * 0.26
    T = (0.13 + crown * (0.26 + 0.26 * lobe) + vein + eye
         + _flat(_tier(id1), 3.0 * s) * 0.24 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def _needles(res, pitch, sd, ln, wd, s):
    """One ply of oriented needles on a bounded-jitter lattice: (body, tip
    bead, cell id). [090b] the ply is wider (1.8 px at GEN, not 1.3) and
    shorter — a hairline needle throws its power above r=256."""
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd, 0.5, taps=5, need2=False)
    a = np.floor(id1 * 8.0) * 0.7853982 + 0.2
    ca, sa = np.cos(a), np.sin(a)
    along = dx * ca + dy * sa
    across = np.abs(-dx * sa + dy * ca)
    L = ln * s * (0.75 + 0.5 * h2(np.floor(id1 * 31.0), 0.0, sd + 3))
    body = sstep(wd * s, wd * s * 0.35, across) * sstep(L, L * 0.72,
                                                        np.abs(along))
    tipd = np.hypot(dx - ca * L, dy - sa * L)
    return body, _bump((tipd / (2.4 * s)) ** 2), id1


def g_needlefelt(res, seed, pitch=_P0, ln=5.6, fine=0.11):
    """needle felt — two crossed plies of anther-tipped stamen needles. The
    orientation is QUANTIZED to 8 directions [090b]: free angles smear the
    needle spectrum into a disc, quantized ones give 8 sharp lobes (the
    peakiness guard) and read as a real carded felt."""
    s = res / _S
    sd = _sd(seed)
    b1, a1, i1 = _needles(res, pitch, sd, ln, 1.9, s)
    b2, a2, i2 = _needles(res, pitch * 0.82, sd + 101, ln * 0.8, 1.6, s)
    T = (0.18 + np.maximum(b1 * (0.34 + _flat(_tier(i1), 3.0 * s) * 0.44),
                           b2 * (0.30 + _flat(_tier(i2), 3.0 * s) * 0.40))
         + np.maximum(a1, a2 * 0.85) * 0.42)
    return n01(T + _fine(res, seed, fine))


def g_starlat(res, seed, pitch=_P0, rays=5.0, fine=0.11):
    """star-lattice sparks — a NEAR-REGULAR lattice (jitter 0.22) of fine ray
    bursts. Low jitter is deliberate: it is the module's sharpest spectral
    fundamental, which is what the peakiness guard measures (L3)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.22, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.68)
    star = (0.5 + 0.5 * np.cos(th * rays + id1 * _TAU)) ** 2.4
    star = star * np.clip(1.0 - rr, 0.0, 1.0)
    core = _bump((rr * 3.0) ** 2) * 0.42
    halo = sstep(0.20, 0.06, np.abs(rr - 0.60)) * 0.12
    T = (0.16 + star * 0.42 + core + halo
         + _flat(_tier(id1), 3.0 * s) * 0.26)
    return n01(T + _fine(res, seed, fine))


def g_fringe(res, seed, rh=10.6, fw=9.6, fine=0.10):
    """comb-fringe rows — banded filament combs with an anther bead at every
    tip. [090b] filament pitch 3.5 -> 8.0 px at GEN: at the old pitch the
    comb was a 2.8 px x-period at 512 (lag-1 autocorrelation NEGATIVE). At 25
    px on a 2048 car it still reads as a comb, and now it is coherent."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 71, 4.0)
    X = xx + wu
    Y = yy + wv
    rj = np.floor(Y / (rh * s))
    v = frac(Y / (rh * s))
    X2 = X + h2(rj, rj * 0.0, sd + 21) * 37.0
    fi = np.floor(X2 / (fw * s))
    u = frac(X2 / (fw * s))
    fil = 0.5 + 0.5 * np.cos((u - 0.5) * _TAU)
    fil = fil * sstep(0.08, 0.22, v) * sstep(0.97, 0.82, v)
    tier = _flat(_tier(h2(fi, rj, sd + 33)), 3.0 * s)
    bead = _bump(((v - 0.80) * rh / 2.2) ** 2 + ((u - 0.5) * fw / 2.2) ** 2)
    base = sstep(0.12, 0.02, v) * 0.28
    T = 0.16 + fil * (0.30 + tier * 0.38) + bead * 0.42 + base
    return n01(T + _fine(res, seed, fine))


def g_echinate(res, seed, pitch=_P0, spikes=7.0, fine=0.10):
    """echinate dust scatter — spiky pollen grains over a coarser dust ply.
    Both plies now sit in the band (grain 8.7 px, dust 5.4 px at GEN)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.5, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.58)
    prof = rr - 0.20 * np.maximum(np.cos(th * spikes + id1 * _TAU), 0.0) ** 2
    body = sstep(0.66, 0.42, prof)
    dome = np.clip(1.0 - rr * rr, 0.0, 1.0)
    _, _, db, idb, _2 = _cells(res, 6.5 * s, sd + 77, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.9 * s)) ** 2)
    T = (0.15 + body * (0.24 + _flat(_tier(id1), 3.0 * s) * 0.40)
         + dome * 0.16 + dust * (0.16 + _flat(_tier(idb), 3.0 * s) * 0.24))
    return n01(T + _fine(res, seed, fine))


def g_threaddrift(res, seed, pitch=8.4, steps=4, step_px=2.1, fine=0.12):
    """flow-smeared thread-drift — grains advected into fading comet trails.
    The flow POTENTIAL stays fbm (it only bends geometry, it adds no luma —
    the L4 carve-out); the grains themselves are an in-band lattice."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.55, taps=5, need2=False)
    dot = _bump((d1 / (2.6 * s)) ** 2) * (0.50 + _flat(_tier(id1), 3.0 * s) * 0.50)
    pot = gauss(fbm(res, res, rng(seed, 91), 3, 6), 3.0)
    gx = cv2.Sobel(pot, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(pot, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy) + 1e-6
    vx, vy = -gy / mag, gx / mag
    yy, xx = coords(res)
    acc = dot.copy()
    mx, my = xx.copy(), yy.copy()
    for k in range(int(steps)):
        mx = (mx - vx * step_px * s) % res
        my = (my - vy * step_px * s) % res
        samp = cv2.remap(dot, mx.astype(np.float32), my.astype(np.float32),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        acc = np.maximum(acc, samp * (1.0 - 0.16 * (k + 1)))
    _, _, db2, idb2, _b2 = _cells(res, 5.4 * s, sd + 177, 0.55, taps=5,
                                  need2=False)
    dust = _bump((db2 / (1.7 * s)) ** 2) * (0.18 + _tier(idb2) * 0.44)
    T = 0.14 + acc * 0.80 + dust * 0.72
    return n01(T + _fine(res, seed, fine))


def g_dustclump(res, seed, pitch=_P0, fine=0.10):
    """clumped structured dust — grains gathered into clumps. [090b] LAW L4:
    the clump ENVELOPE was a 32 px fbm, i.e. pure sub-band energy dressed as
    composition. The clumps are now a bounded-jitter lattice of their own, so
    the clumping reads exactly the same and costs nothing below r=64."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dx, _dy, dc, idc, edge, crown, _gs = _pave(res, p, sd + 9, 0.5, 0.18)
    env = 0.30 + 0.70 * crown * sstep(0.25, 0.70, h2(np.floor(idc * 313.0),
                                                     0.0, sd + 4))
    _, _, da, ida, _a = _cells(res, 4.6 * s, sd, 0.55, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 7.4 * s, sd + 55, 0.55, taps=5, need2=False)
    ga = _bump((da / (1.6 * s)) ** 2) * (0.4 + _tier(ida) * 0.6)
    gb = _bump((db / (2.4 * s)) ** 2) * (0.4 + _tier(idb) * 0.6)
    dust = np.maximum(ga, gb * 0.92) * env
    T = 0.16 + dust * 0.78 + crown * 0.14
    return n01(T + _fine(res, seed, fine))


def g_porate(res, seed, pitch=_P0, pores=3, seam=0.20, fine=0.10):
    """porate close-pack grains — reticulate near-touching grains with germ
    pores. The grain body is the cell crown; the pores are small craters."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.40, seam)
    rr = d1 / (p * 0.66)
    rim = sstep(0.14, 0.04, np.abs(rr - 0.62)) * 0.20
    ret = _grain(dx + 13.0, dy + 71.0, 4.2 * s, sd + 5) * crown * 0.18
    T = (0.13 + crown * 0.46 + rim + ret
         + _flat(_tier(id1), 3.0 * s) * 0.26 * (0.25 + 0.75 * crown))
    for k in range(int(pores)):
        a = id1 * _TAU + k * 2.4
        pd = np.hypot(dx - np.cos(a) * p * 0.26, dy - np.sin(a) * p * 0.26)
        T = T - _bump((pd / (1.8 * s)) ** 2) * 0.22 * crown
    return n01(T * (1.0 - 0.80 * gs) + _fine(res, seed, fine))


def g_trellis(res, seed, pitch=9.8, angle=0.55, fine=0.10):
    """woven trellis cross — two stem families with knotted crossings.
    [090b] pitch 10.8 -> 8.2 px at GEN: at the old pitch the lattice
    fundamental sat at r=59, i.e. UNDER the car band, and the whole finish
    was paying for a structure the metric could not see."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 111, 4.0)
    X = xx + wu
    Y = yy + wv
    ca, sa = np.cos(angle), np.sin(angle)
    qa = (X * ca + Y * sa) / (pitch * s)
    qb = (X * ca - Y * sa) / (pitch * s)
    pa = 0.5 + 0.5 * np.cos(qa * _TAU)
    pb = 0.5 + 0.5 * np.cos(qb * _TAU)
    stemA = pa ** 1.6
    stemB = pb ** 1.6
    tA = _flat(_tier(h2(np.floor(qa), np.floor(qb * 0.5), sd + 3)), 3.0 * s)
    tB = _flat(_tier(h2(np.floor(qb), np.floor(qa * 0.5), sd + 4)), 3.0 * s)
    stem = np.maximum(stemA * (0.38 + tA * 0.44), stemB * (0.34 + tB * 0.40))
    knot = (pa * pb) ** 2.0
    gate = sstep(0.35, 0.55, h2(np.floor(qa + 0.5), np.floor(qb + 0.5), sd + 9))
    T = 0.16 + stem * 0.52 + knot * gate * 0.40 - stemA * stemB * 0.14
    return n01(T + _fine(res, seed, fine))


def g_stemmesh(res, seed, pitch=_P0, fine=0.10):
    """branching stem mesh — 3-scale venation. [090b] LAW L4: the veins were
    ridged fbm at base 24/56/120, i.e. a low-pass field dressed as a network
    (this finish could not pass 0.62 through three tunings). They are now
    bounded-jitter Voronoi ridge webs, which branch at TRUE triple points (a
    better vein habit anyway) and carry a sharp in-band fundamental."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dxa, _dya, _d1a, ida, ea, crowna, va = _pave(res, p, sd + 121, 0.55, 0.26)
    _dxb, _dyb, d1b, idb, eb, _cb, vb = _pave(res, p * 0.62, sd + 131, 0.55,
                                              0.22, taps=9)
    vein = np.maximum(va, vb * 0.82)
    node = sstep(1.30, 1.75, va + vb)
    _, _, bd, bid, _b = _cells(res, 6.6 * s, sd + 61, 0.55, taps=5, need2=False)
    buds = _bump((bd / (2.0 * s)) ** 2)
    buds = buds * sstep(0.30, 0.70, h2(np.floor(bid * 91.0), 0.0, sd + 8))
    T = (0.15 + vein * 0.46 + node * 0.20 + crowna * 0.14
         + _flat(_tier(ida), 3.0 * s) * 0.22 + buds * 0.30)
    return n01(T + _fine(res, seed, fine))


def g_beadcurtain(res, seed, pitch=9.6, bead=7.2, fine=0.10):
    """hanging bead-strand curtain — swaying strands of tiered pea blossoms.
    Sway amplitude cut to ~1 px at GEN: a big sway walks the strand lattice
    off its own period and smears the fundamental (L3)."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    ci = np.floor(xx / (pitch * s))
    ph = h2(ci, ci * 0.0, sd + 11)
    sway = (np.sin(yy / (30.0 * s) + ph * _TAU) * 1.1 * s
            + np.sin(yy / (11.0 * s) + ph * 9.0) * 0.5 * s)
    u = xx - (ci + 0.5) * (pitch * s) - sway
    strand = sstep(1.9 * s, 0.5 * s, np.abs(u))
    bj = np.floor(yy / (bead * s) + ph * 7.0)
    vb = frac(yy / (bead * s) + ph * 7.0)
    tap = 0.62 + 0.38 * h2(ci, np.floor(yy / (48.0 * s)), sd + 31)
    brad = (2.9 * s) * tap
    bd = np.sqrt(u * u + ((vb - 0.5) * bead * s) ** 2)
    beadm = _bump((bd / np.maximum(brad, 1e-3)) ** 2)
    tier = _flat(_tier(h2(ci, bj, sd + 17)), 3.0 * s)
    T = 0.16 + strand * 0.26 + beadm * (0.34 + tier * 0.46)
    return n01(T + _fine(res, seed, fine))


def _lowcut(fn):
    """Universal LOW-CUT knob (`lowcut` px at GEN) wrapped around every
    generator. [090b] the one dial that trades neighbour coherence for
    car-band energy: it subtracts the field's own slow local mean (keeping
    the global mean, so the LUT walk is unchanged) and therefore deletes
    power UNDER r=64 without touching a single shape or edge. Archetypes
    that still carry an unavoidable sub-band skirt after their geometry is
    fixed spend their coherence surplus here."""
    def g(res, seed, lowcut=0.0, **kw):
        T = fn(res, seed, **kw)
        lc = float(lowcut)
        if lc > 0.0:
            T = np.asarray(T, np.float32)
            T = T - (gauss(T, lc * res / 640.0) - float(T.mean()))
            T = np.clip(T, 0.002, 0.998)
        return T
    g.__name__ = fn.__name__
    g.__doc__ = fn.__doc__
    g.__wrapped__ = fn
    return g


