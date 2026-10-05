# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — 20 distinct plate archetypes, one per finish id.
# Every one is a dense in-band micro-field per the law above; the ARCHETYPE
# LEDGER at the top of the module is unchanged (one composition per id).
# [SPB-FRACTURED-090b 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_droplets(res, seed, pitch=_P0, dome=0.50, seam=0.24, fine=0.10):
    """domed droplet close-pack — glossy colony domes with offset specular
    caps and contact shadows where droplets kiss. The DOME is the value (L1);
    the 8-tier tint only stains it."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.46, seam)
    capd = np.hypot(dx + p * 0.18, dy + p * 0.18)
    cap = _bump((capd / (2.0 * s)) ** 2) * 0.34
    T = (0.13 + crown * dome + cap * crown
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) + _fine(res, seed, fine))


def g_satellite(res, seed, pitch=_P0, sats=5.0, fine=0.10):
    """satellite dot scatter — mother colonies ringed by satellite daughters
    over a coarser dust ply. Both plies are in-band lattices (mother 8.7 px,
    dust 5.4 px at GEN)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.5, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.68)
    mother = np.clip(1.0 - rr * rr, 0.0, 1.0)
    ring = sstep(0.20, 0.06, np.abs(rr - 0.56))
    satm = ring * (0.5 + 0.5 * np.cos(th * sats + id1 * _TAU)) ** 2.0
    _, _, db, idb, _b = _cells(res, 6.5 * s, sd + 77, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.9 * s)) ** 2) * (0.18 + _flat(_tier(idb), _LC * s) * 0.28)
    T = (0.14 + mother * (0.34 + _flat(_tier(id1), _LC * s) * 0.36)
         + satm * 0.30 + dust)
    return n01(T + _fine(res, seed, fine))


def g_streaks(res, seed, lane=10.4, dotp=9.6, fine=0.10):
    """streak-plate lanes — sinuous inoculation streaks beaded with colonies.
    [090b] lane pitch 10.8 -> 8.7 px at GEN (the old lane fundamental sat at
    r=59, UNDER the band), dot pitch 5.0 -> 8.0 px (the old one put a 4 px
    x-period at 512, i.e. a NEGATIVE lag-1 autocorrelation), warp 14 -> 4 px
    (a big warp smears the lane fundamental across the spectrum)."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 31, 4.0)
    q = (yy + wu + np.sin(xx / (26.0 * s)) * 2.2 * s) / (lane * s)
    li = np.floor(q)
    v = frac(q)
    lanem = 0.5 + 0.5 * np.cos((v - 0.5) * _TAU)
    X2 = xx + h2(li, li * 0.0, sd + 21) * 43.0
    ci = np.floor(X2 / (dotp * s))
    u = frac(X2 / (dotp * s))
    dot = _bump((((u - 0.5) * dotp) ** 2 + ((v - 0.5) * lane * 0.7) ** 2)
                / (2.6 ** 2)) * sstep(0.35, 0.6, h2(ci, li, sd + 33))
    tier = _flat(_tier(h2(ci, li, sd + 5)), _LC * s)
    T = (0.15 + lanem * 0.34 + dot * (0.30 + tier * 0.40)
         + _grain(xx, yy, 5.0 * s, sd + 13) * 0.14)
    return n01(T + _fine(res, seed, fine))


def g_crackle(res, seed, pitch=_P0, seam=0.30, fine=0.10):
    """crackle-net — a dried-agar crack web at two scales over domed shards.
    The cracks are FAT edge-distance seams (L2): a hairline crack smears its
    power into r>200 harmonics and buys no band."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, seam)
    _dx2, _dy2, _d1b, idb, eb, crownb, gs2 = _pave(res, p * 0.66, sd + 41,
                                                   0.50, 0.24)
    T = (0.14 + crown * 0.40 + crownb * 0.14
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) * (1.0 - 0.34 * gs2)
               + _fine(res, seed, fine))


def g_dendrite(res, seed, pitch=_P0, arms=5.0, fine=0.10):
    """dendrite fans — tiled radial branching fern colonies. [090b] LAW L4:
    the ray jitter was an fbm (a low-pass field feeding straight into the
    luma); it is now a per-colony hash, which is also crisper."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.45, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.68)
    jag = h2(np.floor(id1 * 331.0), np.floor(th * 2.0), sd + 71)
    ray = (0.5 + 0.5 * np.cos(th * arms + id1 * _TAU + (jag - 0.5) * 1.6)) ** 1.8
    sub = (0.5 + 0.5 * np.cos(th * arms * 2.0 + id1 * 9.0)) ** 1.6
    fan = (ray * 0.75 + sub * 0.35 * sstep(0.35, 0.6, rr)) * np.clip(
        1.05 - rr, 0.0, 1.0)
    core = _bump((rr * 2.6) ** 2) * 0.34
    T = (0.15 + _flat(_tier(id1), _LC * s) * 0.26 + fan * 0.46 + core)
    return n01(T + _fine(res, seed, fine))


def g_pills(res, seed, bw=11.5, rh=7.4, striae=3.0, fine=0.09):
    """brick-course ribbed pills — offset rows of rounded diatom tiles with
    transverse striae and a girdle line. [090b] the brick width dropped
    17 -> 11.5 (_S), i.e. the course fundamental moved from r=45 (sub-band)
    to r=67, and the striae from a 5 px to an 8 px period."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 81, 3.0)
    v = (yy + wv) / (rh * s)
    rj = np.floor(v)
    u = (xx + wu) / (bw * s) + h2(rj, rj * 0.0, sd + 3) * 7.0
    ci = np.floor(u)
    du = (u - ci - 0.5) * bw * s
    dv = (v - rj - 0.5) * rh * s
    dd = np.maximum(np.abs(du) - bw * s * 0.30, 0.0) ** 2 + dv * dv
    body = sstep((rh * s * 0.50) ** 2, (rh * s * 0.26) ** 2, dd)
    stri = (0.5 + 0.5 * np.cos(du / (striae * s * 0.42))) * body * 0.18
    girdle = sstep(1.3 * s, 0.3 * s, np.abs(dv)) * body * 0.20
    tier = _flat(_tier(h2(ci, rj, sd + 7)), _LC * s)
    T = 0.15 + body * (0.34 + tier * 0.36) + stri + girdle
    return n01(T + _fine(res, seed, fine))


def g_raphe(res, seed, pitch=_P0, ln=6.0, fine=0.10):
    """raphe needle felt — striated pennate needles with a dark centre raphe
    over a loose spore-dot underlay. Needle orientation is QUANTIZED to 8
    directions: free angles smear the spectrum into a disc, quantized ones
    give 8 sharp lobes (the peakiness guard) and read as a real felt."""
    s = res / _S
    sd = _sd(seed)
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd, 0.5, taps=5, need2=False)
    a = np.floor(id1 * 8.0) * 0.7853982 + 0.35
    ca, sa = np.cos(a), np.sin(a)
    along = dx * ca + dy * sa
    across = np.abs(-dx * sa + dy * ca)
    L = ln * s * (0.8 + 0.5 * h2(np.floor(id1 * 31.0), 0.0, sd + 3))
    body = sstep(2.3 * s, 0.6 * s, across) * sstep(L, L * 0.74, np.abs(along))
    tapern = 1.0 - np.clip(np.abs(along) / np.maximum(L, 1e-4), 0.0, 1.0)
    raphe = sstep(0.7 * s, 0.15 * s, across) * body * 0.28
    ticks = (0.5 + 0.5 * np.cos(along / (1.9 * s))) * body * 0.20
    _, _, db, idb, _b = _cells(res, 6.4 * s, sd + 99, 0.5, taps=5, need2=False)
    dots = _bump((db / (1.9 * s)) ** 2) * (0.16 + _tier(idb) * 0.26)
    T = (0.15 + body * (0.26 + _flat(_tier(id1), _LC * s) * 0.38)
         * (0.6 + 0.4 * tapern) + ticks - raphe + dots)
    return n01(T + _fine(res, seed, fine))


def g_discs(res, seed, pitch=_P0, ribs=6.0, fine=0.10):
    """radial-ribbed disc lattice — centric diatom valves on a NEAR-REGULAR
    lattice (jitter 0.24, law L3: the sharpest spectral fundamental in the
    module). 11 ribs inside a 9 px valve was a 1 px feature living above the
    band; 6 reads as a rib fan and lands inside it."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.24, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.62)
    body = sstep(1.04, 0.86, rr)
    fan = (0.5 + 0.5 * np.cos(th * ribs + id1 * _TAU)) * body
    fan = fan * sstep(0.10, 0.34, rr)
    margin = sstep(0.16, 0.05, np.abs(rr - 0.78)) * 0.26
    pore = _bump((d1 / (2.2 * s)) ** 2) * 0.30
    T = (0.15 + body * (0.26 + _flat(_tier(id1), _LC * s) * 0.34)
         + fan * 0.26 + margin - pore)
    return n01(T + _fine(res, seed, fine))


def g_hexmesh(res, seed, pitch=8.6, fine=0.09):
    """perforated hex mesh — a near-regular silica hole lattice: dark pores,
    bright walls, a lit rim on every pore."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dx, _dy, d1, id1, d2 = _cells(res, p, sd, 0.22)
    hole = sstep(p * 0.42, p * 0.18, d1)
    wall = _fat((d2 - d1) / p, 0.26)
    rimlight = sstep(1.8 * s, 0.4 * s, np.abs(d1 - p * 0.42)) * 0.34
    T = (0.20 + _flat(_tier(id1), _LC * s) * 0.24 - hole * 0.52
         + wall * 0.34 + rimlight)
    return n01(T + _fine(res, seed, fine))


def g_spineball(res, seed, pitch=_P0, spines=6.0, fine=0.10):
    """spine-burst scatter — small urchin spike balls with bright cores and
    radiating rays, over a coarser dust ply."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.46, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.72)
    spike = (0.5 + 0.5 * np.cos(th * spines + id1 * _TAU)) ** 3.0
    spike = spike * sstep(0.98, 0.22, rr)
    ball = _bump((rr * 3.0) ** 2) * 0.46
    _, _, db, idb, _b = _cells(res, 6.2 * s, sd + 88, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.8 * s)) ** 2) * (0.14 + _tier(idb) * 0.24)
    T = (0.15 + _flat(_tier(id1), _LC * s) * 0.24 + spike * 0.44 + ball + dust)
    return n01(T + _fine(res, seed, fine))


def g_memfoam(res, seed, pitch=_P0, wall=0.30, fine=0.10):
    """foam pack with nuclei — bright membrane walls (the fat seam IS the
    membrane), a shallow cytoplasm dome and an offset nucleus per cell."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, wall)
    nx = (h2(np.floor(id1 * 61.0), 0.0, sd + 5) - 0.5) * p * 0.30
    ny = (h2(np.floor(id1 * 47.0), 0.0, sd + 6) - 0.5) * p * 0.30
    nd = np.hypot(dx - nx, dy - ny)
    nuc = _bump((nd / (2.6 * s)) ** 2) * 0.34
    nucleol = _bump((nd / (1.4 * s)) ** 2) * 0.24
    stip = _grain(dx + 17.0, dy + 41.0, 4.6 * s, sd + 15) * crown * 0.16
    T = (0.14 + gs * 0.40 + crown * 0.22
         + _flat(_tier(id1), _LC * s) * 0.24 * (0.3 + 0.7 * crown)
         - nuc + nucleol + stip)
    return n01(T + _fine(res, seed, fine))


def g_stainplates(res, seed, pitch=_P0, seam=0.28, fine=0.09):
    """stained plate-mosaic — polygonal tissue plates in dark grout with a
    per-plate chromatin stipple density. [090b] this was the module's purest
    L1 violation: FLAT plates carrying flat per-cell tints, which is a
    low-pass field however small the plates are. The plates are now gently
    domed and the stipple sits on an in-band cell."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.48, seam)
    dens = sstep(0.25, 0.75, h2(np.floor(id1 * 77.0), 0.0, sd + 4))
    stip = _grain(dx + 29.0, dy + 57.0, 4.4 * s, sd + 11)
    stip2 = _grain(dx + 3.0, dy + 9.0, 6.6 * s, sd + 12)
    T = (0.14 + crown * 0.34 + _flat(_tier(id1), _LC * s) * 0.28
         + (stip * 0.24 + stip2 * 0.16) * (0.35 + 0.65 * dens))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def g_ripples(res, seed, pitch=7.2, angle=0.35, warp=5.0, fine=0.10):
    """micro-ripple carpet — warped cortical-fold ridges with a finer cross
    ply. [090b] the warp dropped 26 -> 5 px (it was smearing the ridge
    fundamental over half the spectrum) and the amplitude envelope moved off
    an fbm (LAW L4) onto the cross ply itself."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wu) * sa + (yy + wv) * ca) / (pitch * s)
    rip = 0.5 + 0.5 * np.cos(q * _TAU)
    q2 = ((xx - wv) * ca - (yy - wu) * sa) / (pitch * 1.7 * s)
    cross = 0.5 + 0.5 * np.cos(q2 * _TAU)
    tier = _flat(_tier(h2(np.floor(q), np.floor(q2), sd + 9)), _LC * s)
    T = 0.15 + rip * (0.34 + 0.16 * cross) + tier * 0.26 + cross * 0.12
    return n01(T + _fine(res, seed, fine))


def g_sporedust(res, seed, pitch=_P0, fine=0.09):
    """clumped spore dust — dense bimodal spores gathered in clumps with a
    fuzzy margin. [090b] LAW L4: the clump envelope AND the fuzz were fbm,
    i.e. pure sub-band energy dressed as composition. The clumps are now a
    bounded-jitter lattice of their own — same look, no leak."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dx, _dy, dc, idc, edge, crown, _gs = _pave(res, p, sd + 9, 0.5, 0.18)
    gate = sstep(0.25, 0.70, h2(np.floor(idc * 313.0), 0.0, sd + 4))
    env = 0.28 + 0.72 * crown * gate
    fuzz = _fat(edge, 0.22) * gate * 0.22
    _, _, da, ida, _a = _cells(res, 5.0 * s, sd, 0.5, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 7.6 * s, sd + 55, 0.5, taps=5, need2=False)
    ga = _bump((da / (1.6 * s)) ** 2) * (0.4 + _tier(ida) * 0.6)
    gb = _bump((db / (2.4 * s)) ** 2) * (0.4 + _tier(idb) * 0.6)
    dust = np.maximum(ga, gb * 0.92) * env
    T = 0.15 + dust * 0.74 + fuzz + crown * 0.12
    return n01(T + _fine(res, seed, fine))


def g_ringspots(res, seed, pitch=_P0, rings=1.35, fine=0.10):
    """ring-pack spots — packed mold spots with concentric zonation and a
    ragged sporing fringe. The zonation wobble moved off fbm onto a per-spot
    hash (L4) and the ring count from 3.4 to 1.35: 3.4 rings inside a 9 px
    spot is a 1.3 px feature, above the band and pure denominator."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.44, 0.20)
    rr = d1 / (p * 0.66)
    wob = (h2(np.floor(id1 * 197.0), 0.0, sd + 121) - 0.5) * 0.20
    ring = 0.5 + 0.5 * np.cos((rr + wob) * rings * _TAU + id1 * 9.0)
    th = np.arctan2(dy, dx)
    fringe = sstep(0.18, 0.05, np.abs(rr - 0.74 + wob))
    fringe = fringe * (0.5 + 0.5 * np.cos(th * 11.0 + id1 * _TAU)) ** 2
    T = (0.13 + crown * 0.34 + ring * ring * 0.26 * (0.3 + 0.7 * crown)
         + fringe * 0.24 + _flat(_tier(id1), _LC * s) * 0.24)
    return n01(T * (1.0 - 0.70 * gs) + _fine(res, seed, fine))


def g_hyphae(res, seed, pitch=_P0, fine=0.09):
    """hyphal thread web — a connected mycelium at two scales with conidia
    beads riding the threads. [090b] LAW L4: the threads were ridged fbm
    crest lines, a low-pass field dressed as a network. They are now
    bounded-jitter Voronoi ridge webs, which branch at TRUE triple points (a
    better hyphal habit anyway) and carry a sharp in-band fundamental."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dxa, _dya, _d1a, ida, ea, crowna, _va = _pave(res, p, sd + 131, 0.52, 0.28)
    _dxb, _dyb, _d1b, idb, eb, _cb, _vb = _pave(res, p * 0.74, sd + 141, 0.52,
                                                0.22)
    web1 = _fat(ea, 0.28)
    web2 = _fat(eb, 0.22) * (1.0 - web1)
    _, _, bd, bid, _b = _cells(res, 6.8 * s, sd + 61, 0.5, taps=5, need2=False)
    beads = _bump((bd / (2.0 * s)) ** 2)
    conidia = beads * np.clip(web1 + web2, 0.0, 1.0)
    T = (0.15 + web1 * 0.40 + web2 * 0.24 + crowna * 0.14
         + _flat(_tier(ida), _LC * s) * 0.20 + conidia * 0.30 + beads * 0.08)
    return n01(T + _fine(res, seed, fine))


def g_beadchains(res, seed, pitch=_P0, bead=7.6, angle=0.7, fine=0.10):
    """bead-chain drift — wandering cocci chains of touching beads with loose
    singles between. [090b] bead spacing 3.7 -> 6.3 px at GEN: along a chain
    tilted 0.7 rad the old spacing projected to a 3 px x-period at 512, i.e.
    a negative lag-1 autocorrelation. The chain wander dropped from an 18 px
    fbm warp to 3 px so the chain lattice keeps its own period (L3)."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    ca, sa = np.cos(angle), np.sin(angle)
    U = xx * ca + yy * sa
    V = -xx * sa + yy * ca
    wu, _wv = warp_pair(res, seed, 151, 3.0)
    Vw = V + wu + np.sin(U / (22.0 * s)) * 1.6 * s
    ci = np.floor(Vw / (pitch * s))
    ph = h2(ci, ci * 0.0, sd + 11)
    off = Vw - (ci + 0.5) * (pitch * s)
    bj = np.floor(U / (bead * s) + ph * 9.0)
    ub = frac(U / (bead * s) + ph * 9.0)
    bd = np.sqrt(off * off + ((ub - 0.5) * bead * s) ** 2)
    gate = sstep(0.22, 0.42, h2(bj * 0.13, ci, sd + 29))
    beadm = _bump((bd / (2.8 * s)) ** 2) * gate
    tier = _flat(_tier(h2(bj, ci, sd + 17)), _LC * s)
    _, _, db, idb, _b = _cells(res, 7.4 * s, sd + 71, 0.5, taps=5, need2=False)
    loose = _bump((db / (2.0 * s)) ** 2) * (0.14 + _tier(idb) * 0.24)
    T = 0.15 + beadm * (0.34 + tier * 0.44) + loose
    return n01(T + _fine(res, seed, fine))


def g_ribbons(res, seed, pitch=10.0, seg=9.0, angle=0.62, fine=0.09):
    """segmented ribbon weave — two crossing families of linked-cell ribbons
    with woven over/under parity. The families are tilted from VERTICAL so
    their 2-D radius stays at r=77 while their x-period nearly doubles: the
    band metric sees |k|, the coherence guard only sees kx."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 161, 4.0)
    X = xx + wu
    Y = yy + wv
    ca, sa = np.cos(angle), np.sin(angle)
    qa = (X * sa + Y * ca) / (pitch * s)
    qb = (X * sa - Y * ca) / (pitch * s)
    pa = 0.5 + 0.5 * np.cos(qa * _TAU)
    pb = 0.5 + 0.5 * np.cos(qb * _TAU)
    ribA = pa ** 1.3
    ribB = pb ** 1.3
    ua = (X * sa - Y * ca) / (seg * s)
    ub = (X * sa + Y * ca) / (seg * s)
    cutA = sstep(0.16, 0.02, np.abs(frac(ua) - 0.5)) * 0.42
    cutB = sstep(0.16, 0.02, np.abs(frac(ub) - 0.5)) * 0.42
    tA = _flat(_tier(h2(np.floor(qa), np.floor(ua), sd + 3)), _LC * s)
    tB = _flat(_tier(h2(np.floor(qb), np.floor(ub), sd + 4)), _LC * s)
    over = np.mod(np.floor(qa) + np.floor(qb), 2.0)
    A = ribA * (0.34 + tA * 0.40) - cutA * ribA
    Bv = ribB * (0.34 + tB * 0.40) - cutB * ribB
    T = 0.16 + np.where(over > 0.5, np.maximum(A, Bv * 0.55),
                        np.maximum(Bv, A * 0.55))
    return n01(T + _fine(res, seed, fine))


def g_loopnet(res, seed, pitch=_P0, bead=6.0, seam=0.30, fine=0.09):
    """beaded loop-net — pseudohypha loops whose cell walls are strung with
    touching yeast beads, dim lumens inside. The wall IS the fat seam (L2)
    and the beads ride it as a phase modulation of the same lattice."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.52, seam)
    phase = (dx * np.cos(id1 * _TAU) + dy * np.sin(id1 * _TAU)) / (bead * s)
    beads = gs * (0.5 + 0.5 * np.cos(phase * _TAU)) ** 1.4
    T = (0.15 + gs * 0.26 + beads * 0.38 + crown * 0.14
         + _flat(_tier(id1), _LC * s) * 0.22 - crown * crown * 0.10)
    return n01(T + _fine(res, seed, fine))


def g_swirlspecks(res, seed, pitch=7.6, steps=3, step_px=2.4, fine=0.10):
    """flow-swirled speck drift — micro plankton specks smeared along curl
    swirls. The flow POTENTIAL stays fbm (it only bends geometry, it adds no
    luma — the L4 carve-out); the specks are an in-band lattice."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _, _, d1, id1, _n = _cells(res, p, sd, 0.5, taps=5, need2=False)
    dot = _bump((d1 / (2.2 * s)) ** 2) * (0.45 + _flat(_tier(id1), _LC * s) * 0.55)
    pot = gauss(fbm(res, res, rng(seed, 171), 3, 8), 2.4)
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
        acc = np.maximum(acc, samp * (1.0 - 0.17 * (k + 1)))
    _, _, db, idb, _b = _cells(res, 5.6 * s, sd + 177, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.7 * s)) ** 2) * (0.16 + _tier(idb) * 0.40)
    T = 0.14 + acc * 0.78 + dust * 0.60
    return n01(T + _fine(res, seed, fine))
