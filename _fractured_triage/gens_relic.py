def _age(res, seed, chip=0.20, tooth=0.12):
    """Antiquity ply: small dark chips / losses plus fine stone tooth.
    [SPB-FRACTURED-090b 2026-08-02] LAW L4 — the tooth was fbm(base 300),
    whose power peaks near r=105 but drags a 1/f skirt under the band, and
    the chips ran on a free-jitter lattice. Both are now bounded-jitter
    in-band lattices, so aging ADDS car-band energy instead of a low skirt
    (measured on the module: aging alone was worth -0.04 to -0.09 band)."""
    s = res / _S
    sd = _sd(seed)
    _, _, cd, cid, _c = _cells(res, 8.6 * s, sd + 303, 0.5, taps=5,
                               need2=False)
    chips = _bump((cd / (2.0 * s)) ** 2) * sstep(0.55, 0.85,
                                                 h2(np.floor(cid * 37.0), 0.0,
                                                    sd + 7))
    grit = _fine(res, seed + 313, 1.0)
    return (-chips * float(chip) + grit * float(tooth)).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — 20 distinct relic-pave archetypes, one per finish.
# Every one is a dense in-band micro-field per the law above; the ARCHETYPE
# LEDGER at the top of the module is unchanged (one composition per id).
# [SPB-FRACTURED-090b 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_chipinlay(res, seed, pitch=_P0, seam=0.28, fine=0.09):
    """chip-inlay pave — irregular polished stone chips bedded in dark
    mastic, every chip beveled and crowned (L1), the mastic a fat seam (L2)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, seam)
    bevel = sstep(0.02, 0.16, edge) * 0.18
    polish = _grain(dx + 21.0, dy + 33.0, 4.8 * s, sd + 11) * crown * 0.14
    T = (0.13 + crown * 0.42 + bevel + polish
         + _flat(_tier(id1), _LC * s) * 0.28 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _age(res, seed) + _fine(res, seed, fine))


def g_wireinlay(res, seed, pitch=9.0, steps=3, step_px=2.6, fine=0.09):
    """thread-drift wire inlay — fine gold wires combed across old stone on a
    curl field. The flow POTENTIAL stays fbm (it bends geometry and adds no
    luma — the L4 carve-out); the wire seeds are an in-band lattice."""
    s = res / _S
    sd = _sd(seed)
    _, _, d1, id1, _n = _cells(res, pitch * s, sd, 0.5, taps=5, need2=False)
    dot = _bump((d1 / (2.3 * s)) ** 2) * (0.45 + _flat(_tier(id1), _LC * s) * 0.55)
    pot = gauss(fbm(res, res, rng(seed, 171), 3, 7), 2.6)
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
        acc = np.maximum(acc, samp * (1.0 - 0.14 * (k + 1)))
    stone = _grain(xx, yy, 5.2 * s, sd + 5) * 0.16
    T = 0.15 + acc * 0.76 + stone
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_microdust(res, seed, fine=0.09):
    """granular micro-mosaic — sand-grade tesserae at two grades, no macro
    form at all: the finest pave in the module. Both grades moved into the
    band (4.7 and 7.5 px at GEN == 15 and 24 px on a 2048 car)."""
    s = res / _S
    sd = _sd(seed)
    _, _, da, ida, _a = _cells(res, 5.6 * s, sd, 0.5, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 9.0 * s, sd + 51, 0.5, taps=5, need2=False)
    ga = _bump((da / (1.8 * s)) ** 2) * (0.35 + _flat(_tier(ida), _LC * s) * 0.65)
    gb = _bump((db / (2.8 * s)) ** 2) * (0.35 + _flat(_tier(idb), _LC * s) * 0.65)
    T = 0.16 + np.maximum(ga, gb * 0.92) * 0.76
    return n01(T + _age(res, seed, chip=0.14) + _fine(res, seed, fine))


def g_strata(res, seed, pitch=7.4, angle=0.30, warp=4.0, fine=0.09):
    """banded strata laminae — fine sediment plies with grit inclusions and a
    per-lamina shade. [090b] the warp dropped 16 -> 4 px (it was smearing the
    lamina fundamental) and the plies are tilted a little off horizontal so
    the courses read as bedding rather than a scanline."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 41, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wu) * sa + (yy + wv) * ca) / (pitch * s)
    lam = 0.5 + 0.5 * np.cos(q * _TAU)
    tier = _flat(_tier(h2(np.floor(q), np.floor(q * 0.09), sd + 9)), _LC * s)
    grit = _grain(xx + wv, yy, 4.6 * s, sd + 13) * 0.16
    seam = sstep(0.10, 0.0, np.abs(frac(q * 0.5) - 0.5)) * 0.20
    T = 0.15 + lam * 0.42 + tier * 0.28 + grit - seam
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_tessgrid(res, seed, cell=10.6, gap=0.20, fine=0.09):
    """square tesserae grid — a regular grouted tile pave with per-tile shade
    and a chipped corner nick on some tiles. [090b] cell 10 -> 8.8 px at GEN
    (r 64 -> 73, off the band edge) and every tile now carries a crown."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 61, 3.0)
    u = (xx + wu) / (cell * s)
    v = (yy + wv) / (cell * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    fu = np.abs(u - cu - 0.5)
    fv = np.abs(v - cv_ - 0.5)
    edge = np.maximum(fu, fv)
    tile = sstep(0.5 - gap * 0.4, 0.5 - gap, edge)
    crown = sstep(0.5 - gap, 0.10, edge)
    nick = _bump(((fu - 0.42) ** 2 + (fv - 0.42) ** 2) / (0.06 ** 2))
    nick = nick * sstep(0.6, 0.85, h2(cu, cv_, sd + 17)) * 0.30
    stip = _grain(xx, yy, 4.4 * s, sd + 21) * tile * 0.14
    T = (0.14 + tile * 0.22 + crown * 0.26 + stip - nick
         + _flat(_tier(h2(cu, cv_, sd + 3)), _LC * s) * 0.30 * tile)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_shingle(res, seed, sw=10.6, rh=7.0, fine=0.08):
    """scale imbrication — shingled ivory plaques in offset rows, each with a
    ribbed grain and a lit leading edge. The grain period moved from 3 to
    7.5 px at GEN; the old one lived above the band and only cost coherence."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 71, 3.0)
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
        rr = np.hypot(du, dv * 0.9) / (sw * s * 0.58)
        inside = sstep(1.02, 0.90, rr)
        grain = 0.5 + 0.5 * np.cos(du / (1.2 * s) + h2(cu, cv_, sd + 5) * 6.0)
        lead = sstep(1.0, 0.78, rr) * sstep(0.0, -1.8 * s, dv) * 0.18
        crown = np.clip(1.0 - rr * rr, 0.0, 1.0)
        val = (0.13 + crown * 0.42 + grain * 0.12 * crown + lead
               + _flat(_tier(h2(cu, cv_, sd)), _LC * s) * 0.26
               * (0.25 + 0.75 * crown))
        T = T + val * inside * (1.0 - done)
        done = np.clip(done + inside, 0.0, 1.0)
    T = T + (1.0 - done) * 0.10
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_vermiculatum(res, seed, pitch=7.6, chip=7.0, warp=5.0, angle=0.28,
                   fine=0.09):
    """opus-vermiculatum worms — curved courses of small chips following a
    warped flow, mosaic laid in worm rows. [090b] the warp dropped 30 -> 5 px
    and the chip pitch rose 3.5 -> 5.8 px at GEN: the old course was a 2.8 px
    x-period at 512, i.e. a NEGATIVE lag-1 autocorrelation."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 81, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wv) * sa + (yy + wu) * ca) / (pitch * s)
    ci = np.floor(q)
    v = frac(q)
    U = ((xx + wv) * ca - (yy + wu) * sa) / (chip * s) \
        + h2(ci, ci * 0.0, sd + 11) * 5.0
    ui = np.floor(U)
    u = frac(U)
    rr = np.hypot((u - 0.5) * 1.9, (v - 0.5) * 2.0)
    body = np.clip(1.0 - rr * rr, 0.0, 1.0)
    tier = _flat(_tier(h2(ui, ci, sd + 3)), _LC * s)
    T = 0.14 + body * 0.42 + tier * 0.28 * (0.25 + 0.75 * body)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_starpave(res, seed, pitch=_P0, points=6.0, fine=0.09):
    """star-lattice rosette pave — small tessellated stars with bright cores
    and dark interstices, on a NEAR-REGULAR lattice (jitter 0.20): the
    sharpest spectral fundamental in the module (the peakiness guard)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.20, taps=5, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.64)
    prof = rr - 0.24 * np.abs(np.cos(th * points * 0.5 + id1 * _TAU)) ** 1.4
    body = sstep(0.70, 0.40, prof)
    rim = sstep(0.10, 0.0, np.abs(prof - 0.68)) * 0.20
    core = _bump((rr * 2.6) ** 2) * 0.28
    T = (0.15 + body * (0.30 + _flat(_tier(id1), _LC * s) * 0.40) + rim + core)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_craquelure(res, seed, pitch=_P0, seam=0.28, fine=0.09):
    """crackle-net gilding — leaf craquelure at two scales over slightly
    domed gilded islands. Both crack scales are fat edge-distance seams (L2):
    a hairline craquelure smears its power into r>200 harmonics."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, seam)
    _dx2, _dy2, _d2, idb, eb, crownb, gs2 = _pave(res, p * 0.68, sd + 41,
                                                  0.50, 0.20)
    burnish = _grain(dx + 7.0, dy + 19.0, 4.4 * s, sd + 9) * crown * 0.14
    T = (0.14 + crown * 0.40 + crownb * 0.12 + burnish
         + _flat(_tier(id1), _LC * s) * 0.28 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) * (1.0 - 0.30 * gs2)
               + _age(res, seed) + _fine(res, seed, fine))


def g_tornflake(res, seed, pitch=_P0, fine=0.09):
    """torn-flake pack — overlapping leaf flakes with ragged torn edges and
    lifted, brighter corners. [090b] LAW L4: the ragged edge was an fbm
    displacement feeding straight into the luma; it is now a per-flake
    angular hash, which tears crisper and costs nothing below the band."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, 0.20)
    th = np.arctan2(dy, dx)
    rag = (h2(np.floor(id1 * 419.0), np.floor(th * 2.5), sd + 121) - 0.5) * 0.14
    e2 = edge + rag
    flake = sstep(0.02, 0.20, e2)
    lift = sstep(0.30, 0.06, e2) * 0.26
    a = id1 * _TAU
    lam = np.clip((dx * np.cos(a) + dy * np.sin(a)) / np.maximum(d1, 1e-4),
                  -1.0, 1.0)
    T = (0.14 + flake * (0.34 + _flat(_tier(id1), _LC * s) * 0.36) + lift
         + lam * 0.10 * flake)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_bandlens(res, seed, pitch=_P0, bands=1.35, fine=0.09):
    """micro-billow malachite bands — cushioned lenses, each ringed by its own
    concentric banding. The wobble moved off fbm onto a per-lens hash (L4)
    and the band count from 3.2 to 1.35: 3.2 rings inside a 9 px lens is a
    1.4 px feature, above the band and pure denominator."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.48, 0.22)
    rr = d1 / (p * 0.70)
    wob = (h2(np.floor(id1 * 197.0), 0.0, sd + 131) - 0.5) * 0.20
    ring = 0.5 + 0.5 * np.cos((rr + wob) * bands * _TAU + id1 * 13.0)
    T = (0.13 + crown * 0.36 + ring * ring * 0.28 * (0.3 + 0.7 * crown)
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.75 * gs) + _age(res, seed) + _fine(res, seed, fine))


def g_slivers(res, seed, pitch=_P0, ln=6.0, fine=0.09):
    """needle-felt bone inlay — fine bone slivers in two crossed plies with
    longitudinal grain lines. Sliver orientation is QUANTIZED to 8 directions:
    free angles smear the spectrum into a disc, quantized ones give 8 sharp
    lobes (the peakiness guard) and read as a real laid inlay."""
    s = res / _S
    sd = _sd(seed)

    def ply(pi, salt, lnk, wd):
        dx, dy, _d1, id1, _ = _cells(res, pi * s, salt, 0.5, taps=5,
                                     need2=False)
        a = np.floor(id1 * 8.0) * 0.7853982 + 0.15
        ca, sa = np.cos(a), np.sin(a)
        along = dx * ca + dy * sa
        across = np.abs(-dx * sa + dy * ca)
        L = lnk * s * (0.8 + 0.5 * h2(np.floor(id1 * 31.0), 0.0, salt + 3))
        body = sstep(wd * s, wd * s * 0.35, across) * sstep(L, L * 0.74,
                                                            np.abs(along))
        grain = (0.5 + 0.5 * np.cos(across / (1.1 * s))) * body * 0.16
        return body * (0.28 + _flat(_tier(id1), _LC * s) * 0.42) + grain

    a1 = ply(pitch, sd, ln, 2.1)
    a2 = ply(pitch * 0.82, sd + 101, ln * 0.78, 1.7)
    T = 0.16 + np.maximum(a1, a2 * 0.9)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def _glyph_cell(res, sd, cu, cv_, du, dv, cw, ch, strokes=4):
    """Small carved glyph inside one cell: a few axis-aligned strokes picked
    per cell hash. [090b] the strokes are FATTER (0.09 of the cell, not
    0.055): a hairline stroke on a 9 px cell is a 0.8 px feature that lives
    above r=256 and only costs coherence."""
    g = np.zeros_like(du)
    for k in range(int(strokes)):
        hsel = h2(cu * 1.0 + k * 13.0, cv_ * 1.0 + k * 7.0, sd + 31 + k)
        hx = h2(cu + k * 3.0, cv_ - k * 5.0, sd + 61 + k)
        hy = h2(cu - k * 2.0, cv_ + k * 9.0, sd + 91 + k)
        on = sstep(0.34, 0.42, hsel)
        px = (hx - 0.5) * cw * 0.50
        py = (hy - 0.5) * ch * 0.50
        horiz = hsel > 0.66
        w = np.where(horiz, cw * 0.30, ch * 0.10)
        h = np.where(horiz, cw * 0.10, ch * 0.30)
        bar = (sstep(w, w * 0.30, np.abs(du - px))
               * sstep(h, h * 0.30, np.abs(dv - py)))
        g = np.maximum(g, bar * on)
    return g


def g_tablet(res, seed, cw=10.6, ch=9.6, fine=0.09):
    """glyph tablet grid — a whole TABLET of small carved glyph cells with
    ruled register lines. [090b] the cell dropped 12.5 -> 8.8 px at GEN (the
    old register fundamental sat at r=51, under the band) and every cell now
    carries a face crown so the tablet lattice itself is band-pass."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, 3.0)
    u = (xx + wu) / (cw * s)
    v = (yy + wv) / (ch * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    du = (u - cu - 0.5) * cw * s
    dv = (v - cv_ - 0.5) * ch * s
    face = np.clip(1.0 - (np.maximum(np.abs(du) / (cw * s),
                                     np.abs(dv) / (ch * s)) * 2.2) ** 2,
                   0.0, 1.0)
    gl = _glyph_cell(res, sd, cu, cv_, du, dv, cw * s, ch * s, 4)
    rule = sstep(1.2 * s, 0.3 * s, np.abs(dv - ch * s * 0.5)) * 0.22
    tier = _flat(_tier(h2(cu, cv_, sd + 3)), _LC * s)
    stone = _grain(xx, yy, 4.8 * s, sd + 7) * 0.14
    T = 0.14 + face * 0.26 + gl * (0.30 + tier * 0.34) + rule + stone
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_cartouche(res, seed, colw=10.4, ch=8.6, fine=0.09):
    """column-register glyph strips — vertical cartouche columns divided by
    engraved borders, glyph cells stacked inside. The column pitch moved from
    r=59 (sub-band) to r=74, and the border is a fat seam."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 101, 3.0)
    u = (xx + wu) / (colw * s)
    ci = np.floor(u)
    fu = u - ci - 0.5
    border = _fat(0.5 - np.abs(fu), 0.16) * 0.30
    v = (yy + wv) / (ch * s) + h2(ci, ci * 0.0, sd + 11) * 3.0
    rj = np.floor(v)
    du = fu * colw * s
    dv = (v - rj - 0.5) * ch * s
    face = np.clip(1.0 - (np.abs(fu) * 2.1) ** 2, 0.0, 1.0)
    gl = _glyph_cell(res, sd, ci, rj, du, dv, colw * s * 0.70, ch * s, 3)
    tier = _flat(_tier(h2(ci, rj, sd + 5)), _LC * s)
    T = 0.14 + face * 0.26 + gl * (0.30 + tier * 0.36) + border
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_seals(res, seed, pitch=_P0, rings=1.30, fine=0.09):
    """ring-pack seal impressions — stamped cylinder-seal discs with
    concentric ridges and a beaded rim, each disc pressed into its own crown.
    Ring count 2.6 -> 1.30 and rim beads 17 -> 9: the old sub-features were
    ~1 px at GEN, above the band and pure denominator."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.44, 0.20)
    rr = d1 / (p * 0.66)
    th = np.arctan2(dy, dx)
    ring = 0.5 + 0.5 * np.cos(rr * rings * _TAU + id1 * 17.0)
    beads = sstep(0.14, 0.04, np.abs(rr - 0.76))
    beads = beads * (0.5 + 0.5 * np.cos(th * 9.0 + id1 * _TAU)) ** 2 * 0.26
    T = (0.13 + crown * 0.36 + ring * ring * 0.24 * (0.3 + 0.7 * crown)
         + beads + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.70 * gs) + _age(res, seed) + _fine(res, seed, fine))


def g_wedges(res, seed, pitch=8.8, fine=0.09):
    """wedge-cuneiform dust field — impressed triangular wedges in four
    quantized orientations, dense over the whole tablet. The quantized
    orientation set gives four sharp spectral lobes instead of a smeared
    disc (the peakiness guard)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, _d1, id1, _ = _cells(res, p, sd, 0.45, need2=False)
    a = np.floor(id1 * 4.0) * (np.pi * 0.5) + 0.35
    ca, sa = np.cos(a), np.sin(a)
    U = dx * ca + dy * sa
    V = -dx * sa + dy * ca
    wl = p * 0.44
    tri = sstep(0.0, -1.4 * s, np.abs(V) - (wl - U) * 0.42)
    tri = tri * sstep(wl, wl * 0.70, U) * sstep(-wl * 0.60, -wl * 0.28, U)
    shade = np.clip((V / (wl * 0.5)) * 0.5 + 0.5, 0.0, 1.0)
    tail = _bump(((U + wl * 0.5) ** 2 + V * V) / (2.2 * s) ** 2) * 0.24
    T = (0.15 + tri * (0.30 + _flat(_tier(id1), _LC * s) * 0.38)
         * (0.55 + 0.45 * shade) + tail)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_terracepleat(res, seed, col=12.0, step=8.0, slope=0.45, fine=0.09):
    """chevron pleats — stepped herringbone terraces, zigzag columns of
    quantized terrace steps. [090b] the tread pitch moved 3.7 -> 6.7 px at
    GEN and the chevron slope 0.9 -> 0.45: the old geometry put a 3 px
    x-period at 512, which is a NEGATIVE lag-1 autocorrelation. A tilted
    stair keeps its 2-D radius in the band and its x-period long."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 111, 4.0)
    X = xx + wu
    Y = yy + wv
    cw = col * s
    ci = np.floor(X / cw)
    u = frac(X / cw)
    sign = 1.0 - 2.0 * np.mod(ci, 2.0)
    q = Y / (step * s) + sign * u * (cw / (step * s)) * slope
    tread = np.floor(q)
    riser = 0.5 + 0.5 * np.cos(frac(q) * _TAU)
    lip = sstep(0.18, 0.02, frac(q)) * 0.20
    tier = _flat(_tier(h2(ci, tread, sd + 3)), _LC * s)
    seam = sstep(0.09, 0.0, np.minimum(u, 1.0 - u)) * 0.26
    T = 0.15 + riser * 0.34 + tier * 0.34 + lip
    return n01(T * (1.0 - seam) + _age(res, seed) + _fine(res, seed, fine))


def g_microterrace(res, seed, pitch=_P0, steps=3.0, fine=0.09):
    """stepped micro-terrace pave — tiny stepped pyramids (quantized Chebyshev
    distance) with lit top plates and shadowed east faces. Step count 5 -> 3:
    five terraces inside a 9 px pyramid is a sub-pixel riser."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, _d1, id1, d2 = _cells(res, p, sd, 0.30)
    cheb = np.maximum(np.abs(dx), np.abs(dy)) / (p * 0.54)
    lvl = np.floor(np.clip(1.0 - cheb, 0.0, 1.0) * steps) / steps
    face = sstep(0.0, 1.6 * s, dx) * 0.12
    top = sstep(0.26, 0.06, cheb) * 0.18
    T = (0.14 + _flat(_tier(id1), _LC * s) * 0.26 + lvl * 0.44 + top - face)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_meander(res, seed, cell=10.8, w=0.155, fine=0.09):
    """interlocking meander cells — a Greek-key fret pack: per-cell L/T
    grooves with quadrant rotation, carved and shadowed. [090b] the cell
    dropped 12.5 -> 9.0 px at GEN (r 51 -> 71) and the key arm widened
    0.09 -> 0.155 of the cell so the fret is a real 1.4 px groove at GEN
    (4.5 px on a 2048 car) instead of a sub-pixel scratch."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 121, 3.0)
    u = (xx + wu) / (cell * s)
    v = (yy + wv) / (cell * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    du = (u - cu - 0.5)
    dv = (v - cv_ - 0.5)
    rot = np.floor(h2(cu, cv_, sd + 3) * 4.0)
    for k in (1.0, 2.0, 3.0):
        m = rot == k
        du2 = np.where(m, dv, du)
        dv2 = np.where(m, -du, dv)
        du, dv = du2, dv2
    armA = sstep(w, w * 0.4, np.abs(dv - 0.22)) * sstep(0.42, 0.32, np.abs(du))
    armB = sstep(w, w * 0.4, np.abs(du - 0.22)) * sstep(0.42, 0.32, np.abs(dv))
    armC = sstep(w, w * 0.4, np.abs(dv + 0.12)) * sstep(0.20, 0.10, np.abs(du))
    key = np.clip(armA + armB + armC, 0.0, 1.0)
    field = np.clip(1.0 - (np.maximum(np.abs(du), np.abs(dv)) * 2.1) ** 2,
                    0.0, 1.0)
    tier = _flat(_tier(h2(cu, cv_, sd + 7)), _LC * s)
    T = 0.15 + field * 0.22 + tier * 0.30 + key * 0.36
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_dentils(res, seed, rh=9.0, bw=9.4, fine=0.09):
    """dentil course lattice — rows of small carved dentil blocks separated by
    fillets, each block lit on top and shadowed below. The block pitch moved
    to 7.8 px at GEN so the course lattice sits at r=82 with an x-period long
    enough to keep the coherence guard happy."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 131, 3.0)
    v = (yy + wv) / (rh * s)
    rj = np.floor(v)
    fv = v - rj
    u = (xx + wu) / (bw * s) + h2(rj, rj * 0.0, sd + 11) * 4.0
    ci = np.floor(u)
    fu = np.abs(u - ci - 0.5)
    block = sstep(0.42, 0.28, fu) * sstep(0.74, 0.58, np.abs(fv - 0.40))
    crown = np.clip(1.0 - (fu * 2.4) ** 2, 0.0, 1.0) * block
    top = sstep(0.20, 0.06, np.abs(fv - 0.16)) * block * 0.24
    under = sstep(0.14, 0.02, np.abs(fv - 0.72)) * 0.18
    tier = _flat(_tier(h2(ci, rj, sd + 5)), _LC * s)
    T = 0.15 + block * 0.24 + crown * 0.24 + tier * 0.30 * block + top - under
    return n01(T + _age(res, seed) + _fine(res, seed, fine))
