# -*- coding: utf-8 -*-
"""FRACTURED RELICS (2026-08-30) — THE CABINET OF CURSED THINGS.

Owner mandate 2026-08-30 (full rebuild, 100 -> 50): *"EACH CATEGORY should have
an identity - an overreaching arc... RELICS should feel old world... I am not as
interested in the cathedral stained glass, guilloche... I DO want it to lean
heavily into Occult, Cryptozoology... when someone opens FRACTURED RELICS -
EVERYTHING - feels like Relics... EVERY SINGLE ONE should be totally unique...
With the most advanced spec map properties you can possibly build. The spec maps
for the most part should follow the pattern designs."*

The old 100 were five COMBINATORIAL GRIDS (6 materials x 4 archetypes, 6 glass
colours x 6 window types, ...). That is why they read as the same finish over
and over even at M7 86-91: the metric scores a recolor exactly as well as the
original. The rebuild is 50 OBJECTS instead — every id is an artifact or a
remain with its own generator, its own palette and its own story. If a name
could be written as "<colour> <pattern>", it does not belong here.

CATEGORY LAW (binding on all 50):
  1. it is an OBJECT, not a motif;
  2. aged ground always (the `_age` ply is mandatory);
  3. ritual/organic INTENT in the geometry — marks made by someone, or grown;
  4. the curse wakes in the light (FRACTURED thin-film hue window = family DNA);
  5. 8-32px dense pave, car-band law (pitch ~_P0, `lowcut` knee at r=64);
  6. no confetti, no mangled garbage — every feature attached to a structure.

Design ledger + gates: docs/FRACTURED_RELICS_REBUILD_2026-08-30.md
Lane state: FRACTURED_RELICS_PROGRESS.jsonl, _relics_work/
Spec: RelicKit material-state carve (kit module) — four material zones taken
from each finish's OWN generator, plus tool-mark shoulders, structural tooth,
patina grain, gated pits, metal fleck and a burial gradient.
"""
from __future__ import annotations

import zlib

import numpy as np

from engine.expansions import fractured_relics_kit_2026 as kit
from engine.expansions.fractured_relics_kit_2026 import (
    _P0, _S, _age, _bump, _cells, _fat, _fibers, _fine, _flat, _grain, _pave,
    _ptier, _sd, _tier, coords, fbm, frac, gauss, h2, n01, rng, sstep,
    warp_pair,
)

_TAU = 6.283185307179586


def _seed(fid):
    return int(zlib.crc32(fid.encode())) & 0x7FFFFFFF


# ════════════════════════════════════════════════════════════════════════════
# ⛧ THE BINDING — witch-work: wards, hexes, bindings, things nailed shut
# ════════════════════════════════════════════════════════════════════════════

def g_hexfoil(res, seed, pitch=11.4, arc=1.35, fine=0.12):
    """Hexfoil ward — compass-scribed daisy wheels burned into oak. The arc
    network IS the flower-of-life: circles of radius = lattice pitch centred on
    a hex lattice, so every scribed line is shared by two wheels."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 11, 2.2)
    p = pitch * s
    hx, hy = (xx + wu) / p, (yy + wv) / (p * 0.866)
    ci, cj = np.floor(hx), np.floor(hy)
    best = np.full((res, res), 1e9, np.float32)
    tone = np.zeros((res, res), np.float32)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            cu, cv_ = ci + di, cj + dj
            ox = (cu + 0.5 + 0.5 * np.mod(cv_, 2.0)) * p
            oy = (cv_ + 0.5) * p * 0.866
            d = np.hypot((xx + wu) - ox, (yy + wv) - oy)
            ring = np.abs(d - p * arc * 0.5)
            m = ring < best
            best = np.where(m, ring, best)
            tone = np.where(m, _tier(h2(cu, cv_, sd + 5)), tone)
    scribe = _bump((best / (1.15 * s)) ** 2)                # the compass groove
    scribe = np.maximum(scribe, _bump(((best - 2.2 * s) / (0.8 * s)) ** 2) * 0.55)  # 2nd pass
    burn = sstep(2.6 * s, 0.4 * s, best) * 0.18             # scorch either side
    oak = _fibers(res, seed + 3, 0.06, 7.4, wob=1.5, duty=0.72) * 0.16
    endgrain = _grain(xx, yy, 4.2 * s, sd + 71, thr=0.5) * 0.22        # cut-end pores
    T = 0.05 + scribe * (0.78 + tone * 0.36) + burn * 0.6 + oak * 0.34 + endgrain * 0.7
    return T + _age(res, seed, 0.17, 0.12) + _fine(res, seed, fine)


def g_witchbottle(res, seed, pitch=9.2, fine=0.13):
    """Witch bottle — bent iron nails, pins and hair packed into glass. Three
    overlapping needle passes at different angles + head domes; the glass is a
    slow caustic ground the iron sits in."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    iron = np.zeros((res, res), np.float32)
    for k, (salt, ln) in enumerate(((131, 4.6), (271, 3.8), (419, 5.4))):
        dx, dy, d1, id1, _ = _cells(res, pitch * s * (1.0 + 0.14 * k), sd + salt,
                                    0.52, taps=9, need2=False)
        a = id1 * _TAU + k * 1.1
        ca, sa = np.cos(a), np.sin(a)
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        L = ln * s * (0.72 + 0.55 * h2(np.floor(id1 * 53.0), 0.0, sd + 17))
        bend = v + np.sin(u / np.maximum(L, 1e-3) * 2.2) * 0.55 * s   # bent nails
        shaft = _bump((bend / (0.95 * s)) ** 2) * sstep(L, L * 0.55, np.abs(u))
        head = _bump(((np.hypot(u - L * 0.92, v)) / (1.5 * s)) ** 2)
        iron = np.maximum(iron, np.maximum(shaft * 0.92, head))
    glass = (np.sin((xx * 0.9 + yy * 1.3) / (7.0 * s)) *
             np.sin((xx * 1.2 - yy * 0.8) / (8.4 * s))) * 0.10
    T = 0.17 + iron * 0.52 + glass + _grain(xx, yy, 5.0 * s, sd + 29) * 0.10
    return T + _age(res, seed, 0.15, 0.13) + _fine(res, seed, fine)


def g_bindknot(res, seed, pitch=10.8, fine=0.11):
    """Binding knot — an endless-knot rope weave. Two strand families cross
    over-under on a checkerboard; every cord carries its own twist bumps."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 23, 2.0)
    p = pitch * s
    u = (xx + wu + yy * 0.0) / p
    v = (yy + wv) / p
    a = (u + v) * 0.7071
    b = (u - v) * 0.7071
    def strand(q, salt):
        f = frac(q) - 0.5
        body = np.clip(1.0 - (np.abs(f) / 0.34) ** 2, 0.0, 1.0)
        twist = 0.5 + 0.5 * np.sin((q * _TAU * 0.0) + (xx + yy) / (2.3 * s) + salt)
        return body * (0.72 + 0.28 * twist)
    def strand2(q, other):
        f = frac(q) - 0.5
        body = np.clip(1.0 - (np.abs(f) / 0.34) ** 2, 0.0, 1.0)
        twist = 0.5 + 0.5 * np.sin(other * _TAU * 1.6)        # ply runs ALONG the cord
        return body * (0.62 + 0.38 * twist)
    sa_ = strand2(a, b)
    sb = strand2(b, a)
    over = np.mod(np.floor(a) + np.floor(b), 2.0)            # over-under table
    rope = np.where(over > 0.5, np.maximum(sa_, sb * 0.42),
                    np.maximum(sb, sa_ * 0.42))
    tone = _tier(h2(np.floor(a), np.floor(b), sd + 9)) * 0.26
    hemp = _fibers(res, seed + 5, 0.79, 3.1, wob=0.9, duty=0.6) * 0.13
    T = 0.15 + rope * (0.40 + tone) + hemp
    return T + _age(res, seed, 0.16, 0.11) + _fine(res, seed, fine)


def g_coffinnail(res, seed, pitch=10.2, fine=0.12):
    """Coffin-nail ward — hammered nail heads driven in a ward grid, each one
    ringed by the bruise its hammer left in the plate."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd + 61, 0.34, taps=9, need2=False)
    rad = (1.9 + 0.7 * h2(np.floor(id1 * 41.0), 0.0, sd + 13)) * s
    head = _bump((d1 / rad) ** 2)
    facet = np.clip(1.0 - (np.maximum(np.abs(dx), np.abs(dy)) / (rad * 0.72)) ** 2,
                    0.0, 1.0) * 0.42                          # struck flat top
    bruise = np.exp(-((d1 - rad * 1.9) / (1.1 * s)) ** 2) * 0.30
    ring = np.exp(-((d1 - rad * 3.1) / (1.6 * s)) ** 2) * 0.14
    plate = _fibers(res, seed + 7, 1.42, 8.6, wob=1.2, duty=0.8) * 0.12
    tone = _tier(h2(np.floor(id1 * 67.0), 0.0, sd + 3))
    T = 0.07 + head * (0.46 + tone * 0.32) + facet * head + bruise - ring + plate * 0.5
    return T + _age(res, seed, 0.19, 0.13) + _fine(res, seed, fine)


def g_saltcircle(res, seed, lines=7.2, fine=0.13):
    """Salt circle — a poured salt ridge that dries into contour crusts and
    throws micro-dendrites off every edge onto black slate."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    base = fbm(res, res, rng(seed, 71), 4, 4)
    wu, wv = warp_pair(res, seed, 73, 5.0)
    fieldv = base + (wu + wv) / (res * 0.5) * 0.6
    q = fieldv * lines
    ridge = 1.0 - np.abs(frac(q) - 0.5) * 2.0
    crust = np.clip(ridge, 0.0, 1.0) ** 2.2
    gx = np.gradient(gauss(fieldv, 1.6), axis=1)
    gy = np.gradient(gauss(fieldv, 1.6), axis=0)
    gn = np.hypot(gx, gy) + 1e-6
    spur = np.sin((xx * gx / gn + yy * gy / gn) / (2.1 * s) * _TAU) * 0.5 + 0.5
    dend = crust * spur * 0.34                                  # dendrite fringe
    crystal = _grain(xx, yy, 4.6 * s, sd + 37, thr=0.42) * 0.34
    facet = _grain(xx, yy, 3.0 * s, sd + 137, thr=0.46) * 0.30        # cubic salt facets
    T = 0.06 + crust ** 2.0 * 0.56 + dend * 1.2 + crystal * (0.55 + crust) * 1.5 + facet * (0.75 + crust) * 1.3
    return T + _age(res, seed, 0.13, 0.14) + _fine(res, seed, fine)


def g_poppetstitch(res, seed, weave=4.3, stitch=12.6, fine=0.11):
    """Poppet stitch — coarse sackcloth in plain weave, closed with crossed
    sutures and studded with the pins that were pushed through it."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    p = weave * s
    fu, fv = frac(xx / p) - 0.5, frac(yy / p) - 0.5
    warp = np.clip(1.0 - (np.abs(fu) / 0.36) ** 2, 0.0, 1.0)
    weft = np.clip(1.0 - (np.abs(fv) / 0.36) ** 2, 0.0, 1.0)
    over = np.mod(np.floor(xx / p) + np.floor(yy / p), 2.0)
    slub = 0.72 + 0.28 * h2(np.floor(xx / (p * 5.0)), np.floor(yy / (p * 5.0)), sd + 41)
    cloth = np.where(over > 0.5, np.maximum(warp, weft * 0.45),
                     np.maximum(weft, warp * 0.45)) * slub
    shadow = (1.0 - np.maximum(warp, weft)) * 0.26                     # weave shadow
    sp = stitch * s
    dx, dy, d1, id1, _ = _cells(res, sp, sd + 83, 0.30, taps=5, need2=False)
    a = 0.7854 + (h2(np.floor(id1 * 31.0), 0.0, sd + 11) - 0.5) * 0.5
    ca, sa = np.cos(a), np.sin(a)
    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
    arm = sp * 0.46
    x1 = _bump((v / (2.1 * s)) ** 2) * sstep(arm, arm * 0.42, np.abs(u))
    x2 = _bump((u / (2.1 * s)) ** 2) * sstep(arm, arm * 0.42, np.abs(v))
    sutures = np.maximum(x1, x2) * (0.45 + 0.55 * _tier(h2(np.floor(id1 * 53.0), 0.0, sd + 5)))
    _, _, pd, pid, _ = _cells(res, sp * 0.62, sd + 137, 0.5, taps=5, need2=False)
    pins = _bump((pd / (1.0 * s)) ** 2) * sstep(0.62, 0.9, h2(np.floor(pid * 29.0), 0.0, sd + 19))
    T = 0.09 + cloth * 0.40 + sutures * 0.86 - pins * 0.30 - shadow * 1.3
    return T + _age(res, seed, 0.15, 0.12) + _fine(res, seed, fine)


def g_hagstone(res, seed, pitch=13.5, fine=0.13):
    """Hag stone — water-bored flint. Conchoidal flake scars in the body, bore
    holes punched clean through, chalk cortex clinging in the hollows."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, pitch * s, sd + 91, 0.42, 0.20)
    # conchoidal ripples: concentric shells inside each flake scar
    shell = 0.5 + 0.5 * np.cos(d1 / (2.0 * s) * _TAU + id1 * _TAU)
    scar = crown * (0.55 + 0.45 * shell)
    _, _, bd, bid, _ = _cells(res, pitch * s * 1.9, sd + 211, 0.55, taps=5, need2=False)
    bore = sstep(0.70, 0.94, h2(np.floor(bid * 47.0), 0.0, sd + 7))
    hole = _bump((bd / (2.4 * s)) ** 2) * bore
    rim = np.exp(-((bd - 2.7 * s) / (1.0 * s)) ** 2) * bore * 0.42
    cortex = _grain(xx, yy, 5.2 * s, sd + 43, thr=0.46) * 0.34 * (1.0 - crown * 0.7)
    rib = _bump(((d1 - 1.6 * s) / (0.55 * s)) ** 2) * 0.42             # ripple rib
    lip = _fat(edge, 0.10) * 0.30                                      # fracture lip
    T = 0.07 + scar * 0.52 + cortex + rib + lip + rim - hole * 0.56 - seam * 0.20
    return T + _age(res, seed, 0.18, 0.13) + _fine(res, seed, fine)


def g_sigilwax(res, seed, pitch=13.8, fine=0.11):
    """Sigil seal — matrix-stamped wax discs, each with its own radial sigil
    cut into the die, each sagging into a drip skirt as it cooled."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd + 101, 0.30, taps=9, need2=False)
    rad = pitch * s * 0.46
    disc = sstep(rad, rad * 0.86, d1)
    ang = np.arctan2(dy, dx) + id1 * _TAU
    spokes = 5.0 + np.floor(h2(np.floor(id1 * 37.0), 0.0, sd + 3) * 4.0)
    star = 0.5 + 0.5 * np.cos(ang * spokes)
    inner = sstep(rad * 0.74, rad * 0.60, d1)
    ring = np.exp(-((d1 - rad * 0.80) / (0.9 * s)) ** 2)
    sigil = disc * (0.34 + 0.42 * star * inner + 0.44 * ring)
    skirt = np.clip((dy - rad * 0.7) / (2.4 * s), 0.0, 1.0) * disc * 0.18
    slab = _grain(xx, yy, 6.0 * s, sd + 53, thr=0.6) * 0.10
    tone = _tier(h2(np.floor(id1 * 61.0), 0.0, sd + 13)) * 0.24
    T = 0.15 + sigil * (0.72 + tone) + skirt + slab * (1.0 - disc)
    return T + _age(res, seed, 0.16, 0.11) + _fine(res, seed, fine)


def g_threadcross(res, seed, wrap=5.2, fine=0.11):
    """Red thread cross — yarn wound over crossed twigs. Two wrap territories
    interleave; inside each band the ply twist runs across the wind."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    terr = np.mod(np.floor(xx / (wrap * s * 7.0)) + np.floor(yy / (wrap * s * 7.0)), 2.0)
    wu, wv = warp_pair(res, seed, 113, 2.6)
    q1 = (xx + wu) / (wrap * s)
    q2 = (yy + wv) / (wrap * s)
    def band(q, ang):
        f = frac(q) - 0.5
        core = np.clip(1.0 - (np.abs(f) / 0.40) ** 2, 0.0, 1.0)
        ply = 0.5 + 0.5 * np.sin((xx * np.cos(ang) + yy * np.sin(ang)) / (1.5 * s) * _TAU)
        fib = _fibers(res, seed + 31, ang + 1.5708, 2.2, wob=0.5, duty=0.5)  # single fibres
        return core * (0.44 + 0.28 * ply + 0.40 * fib)
    wind = np.where(terr > 0.5, band(q1, 1.15), band(q2, -0.42))
    tone = _tier(h2(np.floor(q1), np.floor(q2), sd + 17)) * 0.30
    twig = _fibers(res, seed + 9, 0.35, 9.0, wob=1.8, duty=0.55) * 0.20
    gap = np.clip(1.0 - wind * 1.6, 0.0, 1.0)                 # dark between wraps
    T = 0.13 + wind * (0.50 + tone) + twig * gap - gap * 0.10
    return T + _age(res, seed, 0.15, 0.12) + _fine(res, seed, fine)


def g_ironcage(res, seed, strap=12.4, fine=0.12):
    """Iron cage — riveted strap iron crossing over a void, forge scale still
    flaking off the bars, a rivet at every crossing."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    p = strap * s
    fu, fv = frac(xx / p) - 0.5, frac(yy / p) - 0.5
    w = 0.30
    barh = sstep(w, w * 0.55, np.abs(fv))
    barv = sstep(w, w * 0.55, np.abs(fu))
    bevh = np.clip(1.0 - (np.abs(fv) / w) ** 2, 0.0, 1.0)
    bevv = np.clip(1.0 - (np.abs(fu) / w) ** 2, 0.0, 1.0)
    over = np.mod(np.floor(xx / p) + np.floor(yy / p), 2.0)
    bars = np.where(over > 0.5, np.maximum(barh * bevh, barv * bevv * 0.5),
                    np.maximum(barv * bevv, barh * bevh * 0.5))
    rd = np.hypot(fu, fv) * p
    rivet = _bump((rd / (1.7 * s)) ** 2) * np.maximum(barh, barv)
    scale = _grain(xx, yy, 4.8 * s, sd + 59, thr=0.52) * 0.24
    tone = _ptier(res, 9.0 * s, sd + 23, ang=0.5, relief=0.5) * 0.22
    T = 0.05 + bars * (0.54 + tone) + rivet * 0.40 + scale * bars * 0.8
    return T + _age(res, seed, 0.20, 0.14) + _fine(res, seed, fine)



# ════════════════════════════════════════════════════════════════════════════
# 🦴 THE BEAST — cryptozoology: what was left behind
# ════════════════════════════════════════════════════════════════════════════

def g_horn(res, seed, ring=13.0, fine=0.11):
    """Wendigo horn — keratin laid down in growth laminae around a curved core,
    the whole sheath split lengthwise where it dried."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 17, 4.0)
    # off-canvas core: the laminae arc across the panel instead of ringing it
    cx, cy = -0.55 * res, 0.35 * res
    d = np.hypot((xx + wu) - cx, (yy + wv) - cy)
    th = np.arctan2((yy + wv) - cy, (xx + wu) - cx)
    q = d / (ring * s)
    lam = np.abs(frac(q) - 0.5) * 2.0
    band = np.clip(1.0 - lam ** 1.4, 0.0, 1.0)
    tier = _tier(h2(np.floor(q), np.floor(th * 9.0), sd + 5))
    # longitudinal drying splits: thin, along the horn axis, sparse
    sp = frac(th * 14.0 + fbm(res, res, rng(seed, 33), 3, 4) * 0.9)
    split = _bump(((np.abs(sp - 0.5) * 2.0) / 0.10) ** 2) * sstep(0.30, 0.75,
             h2(np.floor(th * 14.0), np.floor(q * 0.5), sd + 11))
    keratin = _fibers(res, seed + 7, 1.35, 3.0, wob=1.1, duty=0.55) * 0.22
    T = 0.07 + band * (0.42 + tier * 0.34) + keratin * band - split * 0.30
    return T + _age(res, seed, 0.16, 0.12) + _fine(res, seed, fine)


def g_quill(res, seed, barb=3.4, fine=0.10):
    """Thunderbird quill — barbs combed off the shaft, zipped by barbules and
    torn open in gaps where the vane has parted."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    ang = 0.62
    ca, sa = np.cos(ang), np.sin(ang)
    u = (xx * ca + yy * sa)
    v = (-xx * sa + yy * ca)
    lane = np.floor(v / (barb * s * 6.0))                      # vane sections
    drift = (h2(lane, 0.0, sd + 3) - 0.5) * 1.6 * s
    q = (u + drift) / (barb * s)
    f = frac(q) - 0.5
    core = np.clip(1.0 - (np.abs(f) / 0.34) ** 2, 0.0, 1.0)
    barbule = 0.5 + 0.5 * np.sin(v / (1.35 * s) * _TAU)        # the zip
    tier = _tier(h2(np.floor(q), lane, sd + 9))
    gap = sstep(0.72, 0.94, h2(np.floor(q * 0.5), np.floor(v / (barb * s * 11.0)), sd + 21))
    T = 0.07 + core * (0.40 + tier * 0.30) * (0.62 + 0.38 * barbule) - gap * 0.26
    return T + _age(res, seed, 0.14, 0.12) + _fine(res, seed, fine)


def g_mothdust(res, seed, scale=8.6, fine=0.11):
    """Mothman dust — lepidoptera scales shingled in rows, each a ribbed paddle
    that comes off on your fingers."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    rows = scale * s * 0.72
    rj = np.floor(yy / rows)
    off = np.mod(rj, 2.0) * 0.5 + (h2(rj, 0.0, sd + 5) - 0.5) * 0.3
    cq = xx / (scale * s) + off
    ci = np.floor(cq)
    fu = frac(cq) - 0.5
    fv = frac(yy / rows) - 0.5
    a = (h2(ci, rj, sd + 13) - 0.5) * 0.55                     # per-scale tilt
    uu = fu * np.cos(a) - fv * np.sin(a)
    vv = fu * np.sin(a) + fv * np.cos(a)
    paddle = np.clip(1.0 - ((uu / 0.46) ** 2 + (vv / 0.62) ** 2), 0.0, 1.0)
    rib = 0.5 + 0.5 * np.cos(uu * _TAU * 5.0)                  # scale ribs
    tip = sstep(0.10, 0.55, vv + 0.5)
    tier = _tier(h2(ci, rj, sd + 29))
    gapd = (1.0 - sstep(0.02, 0.42, paddle)) * 0.26
    T = 0.06 + paddle * (0.52 + tier * 0.38) * (0.60 + 0.40 * rib) * (0.50 + 0.50 * tip) - gapd
    return T + _age(res, seed, 0.15, 0.13) + _fine(res, seed, fine)


def g_scute(res, seed, pitch=14.5, fine=0.10):
    """Lake serpent scute — keeled belly plates, each carrying the growth annuli
    of the years it swam, under a haze of shed skin."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, pitch * s, sd + 41, 0.34, 0.16)
    keel = _bump((dx / (1.5 * s)) ** 2) * crown                # raised centre ridge
    annuli = 0.5 + 0.5 * np.cos(d1 / (1.9 * s) * _TAU + id1 * _TAU)
    tier = _tier(h2(np.floor(id1 * 53.0), 0.0, sd + 7))
    shed = _grain(xx, yy, 4.4 * s, sd + 61, thr=0.66) * 0.16
    T = (0.07 + crown * (0.34 + tier * 0.30) * (0.70 + 0.30 * annuli)
         + keel * 0.30 + shed - seam * 0.22)
    return T + _age(res, seed, 0.16, 0.12) + _fine(res, seed, fine)


def g_hoof(res, seed, lam=11.0, fine=0.10):
    """Devil's hoof — horn wall in laminae, packed with the tubules that grew it,
    split down the cleft."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 51, 3.2)
    q = (xx * 0.32 + yy * 0.95 + wv) / (lam * s)
    lamina = np.abs(frac(q) - 0.5) * 2.0
    wall = np.clip(1.0 - lamina ** 1.6, 0.0, 1.0)
    tub = _grain(xx + wu, yy, 2.9 * s, sd + 17, thr=0.42)      # horn tubules
    tier = _tier(h2(np.floor(q), np.floor((xx - yy * 0.3) / (lam * s * 2.0)), sd + 5))
    cleft = _bump(((frac((xx * 0.95 - yy * 0.30) / (lam * s * 7.0)) - 0.5) / 0.055) ** 2) * 0.34
    T = 0.07 + wall * (0.38 + tier * 0.32) + tub * 0.34 * wall - cleft
    return T + _age(res, seed, 0.17, 0.13) + _fine(res, seed, fine)


def g_pelt(res, seed, hair=2.6, fine=0.11):
    """Sasquatch pelt — guard hair matted into locks, every lock combed by the
    same weather and clumped where it dried.

    [relics iter17] Rewritten: rotating the coordinate frame by a spatially
    varying angle aliases into moire (the first pass looked like a digital
    artefact, not fur). Hair now follows the ISO-CONTOURS of a smooth scalar
    potential — the strands can never cross, exactly like real combed fur, and
    there is no rotating frame to alias."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    F = fbm(res, res, rng(seed, 71), 3, 4)
    F = gauss(F, 2.2 * s) * 1.0 + (xx * 0.35 + yy * 0.16) / (res * 1.0) * 0.55
    q = F * (res / (hair * s * 1.35))
    strand = np.clip(1.0 - (np.abs(frac(q) - 0.5) / 0.34) ** 2, 0.0, 1.0)
    gx = np.gradient(F, axis=1)
    gy = np.gradient(F, axis=0)
    speed = n01(gauss(np.hypot(gx, gy), 3.0 * s))
    lock = sstep(0.28, 0.80, speed)                      # hair bunches into locks
    tier = _tier(h2(np.floor(q), np.floor((xx * gy - yy * gx) * 900.0), sd + 11))
    tipfleck = _grain(xx, yy, 3.4 * s, sd + 47, thr=0.70) * 0.20
    T = (0.07 + strand * (0.34 + tier * 0.36) * (0.55 + 0.55 * lock)
         + lock * 0.10 + tipfleck * strand)
    return T + _age(res, seed, 0.13, 0.14) + _fine(res, seed, fine)


def g_spine(res, seed, row=15.0, fine=0.10):
    """Chupacabra spine — dorsal spikes in ranks with the membrane still
    stretched between them, veined and torn."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    rj = np.floor(yy / (row * s))
    off = (h2(rj, 0.0, sd + 3) - 0.5) * 0.6
    cq = xx / (row * s * 0.62) + off
    ci = np.floor(cq)
    fu = frac(cq) - 0.5
    fv = frac(yy / (row * s))
    hgt = 0.42 + 0.38 * h2(ci, rj, sd + 7)
    spike = np.clip(1.0 - (np.abs(fu) / (0.34 * (1.0 - fv * 0.75) + 1e-3)) ** 2, 0.0, 1.0)         * sstep(hgt + 0.06, hgt - 0.20, fv)
    web = sstep(0.16, 0.55, fv) * (1.0 - spike) * 0.40         # stretched membrane
    vein = _bump(((frac(cq * 3.0) - 0.5) / 0.12) ** 2) * web * 0.9
    tier = _tier(h2(ci, rj, sd + 23))
    T = 0.07 + spike * (0.46 + tier * 0.30) + web + vein * 0.5
    return T + _age(res, seed, 0.15, 0.12) + _fine(res, seed, fine)


def g_tubercle(res, seed, pitch=12.6, fine=0.11):
    """Grendel hide — thick leather gone to warts: nodules of every size bedded
    in a cracked matrix, seamed where old wounds closed."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, pitch * s, sd + 83, 0.46, 0.20)
    rad = (1.4 + 1.9 * h2(np.floor(id1 * 37.0), 0.0, sd + 5)) * s
    wart = _bump((d1 / rad) ** 2)
    _, _, d2_, id2, _ = _cells(res, pitch * s * 0.44, sd + 211, 0.55, taps=5, need2=False)
    beadlet = _bump((d2_ / (1.0 * s)) ** 2) * sstep(0.55, 0.86,
              h2(np.floor(id2 * 29.0), 0.0, sd + 13)) * 0.30
    tier = _tier(h2(np.floor(id1 * 61.0), 0.0, sd + 17))
    T = (0.07 + wart * (0.40 + tier * 0.32) + beadlet + crown * 0.14
         - seam * 0.30)
    return T + _age(res, seed, 0.18, 0.13) + _fine(res, seed, fine)


def g_sucker(res, seed, pitch=15.0, fine=0.10):
    """Kraken sucker — rings of chitin teeth packed down the arm, each cup a
    ring of dentition around a dark throat."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 97, 3.0)
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd + 101, 0.36, taps=9, need2=False)
    rad = pitch * s * (0.30 + 0.10 * h2(np.floor(id1 * 41.0), 0.0, sd + 3))
    cup = sstep(rad * 1.15, rad * 0.92, d1)
    throat = _bump((d1 / (rad * 0.44)) ** 2)
    ang = np.arctan2(dy + wv * 0.0, dx) + id1 * _TAU
    nteeth = 14.0 + np.floor(h2(np.floor(id1 * 53.0), 0.0, sd + 11) * 8.0)
    teeth = (0.5 + 0.5 * np.cos(ang * nteeth)) ** 3
    ringz = np.exp(-((d1 - rad * 0.78) / (0.75 * s)) ** 2)
    folds = (0.5 + 0.5 * np.cos(ang * (nteeth * 0.5))) ** 2 * sstep(rad * 0.86, rad * 0.30, d1)
    tier = _tier(h2(np.floor(id1 * 67.0), 0.0, sd + 19))
    _, _, pd, pid, _ = _cells(res, 3.6 * s, sd + 307, 0.55, taps=5, need2=False)
    papilla = _bump((pd / (1.35 * s)) ** 2) * (0.45 + 0.55 * h2(np.floor(pid * 31.0), 0.0, sd + 23))
    skin = (1.0 - cup) * papilla * 0.66                        # papillate arm skin
    T = (0.07 + cup * (0.26 + tier * 0.26) + ringz * teeth * 0.66 + folds * 0.30
         - throat * 0.40 + skin + _grain(xx, yy, 3.8 * s, sd + 31, thr=0.56) * 0.16)
    return T + _age(res, seed, 0.16, 0.12) + _fine(res, seed, fine)


def g_gill(res, seed, lam=4.4, fine=0.10):
    """Deep One gill — lamellae stacked plate on plate in curved ranks, every
    filament combed the same way by the water it last breathed."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    bend = np.sin(xx / (res * 0.22)) * 6.0 * s
    rank = np.floor((yy + bend) / (lam * s * 7.0))
    ph = (h2(rank, 0.0, sd + 5) - 0.5) * 0.7
    q = (yy + bend) / (lam * s) + ph
    plate = np.clip(1.0 - (np.abs(frac(q) - 0.5) / 0.32) ** 2, 0.0, 1.0)
    filament = 0.5 + 0.5 * np.cos(xx / (1.5 * s) * _TAU + rank * 1.3)
    tier = _tier(h2(np.floor(q), np.floor(xx / (lam * s * 9.0)), sd + 13))
    gap = sstep(0.34, 0.02, np.abs(frac(q) - 0.5)) * 0.0
    T = 0.07 + plate * (0.38 + tier * 0.32) * (0.60 + 0.40 * filament) + gap
    return T + _age(res, seed, 0.14, 0.13) + _fine(res, seed, fine)


# ════════════════════════════════════════════════════════════════════════════
# ⚱ THE BARROW — grave goods: what went into the ground with them
# ════════════════════════════════════════════════════════════════════════════

def g_bogleather(res, seed, wrinkle=13.0, fine=0.11):
    """Bog body — skin tanned by peat acid: the pore field survives, the whole
    hide creased into ridges where the bog folded it."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    F = gauss(fbm(res, res, rng(seed, 61), 3, 4), 2.0 * s)
    q = F * (res / (wrinkle * s * 1.6))
    crease = 1.0 - np.abs(frac(q) - 0.5) * 2.0
    ridge = np.clip(crease, 0.0, 1.0) ** 1.5
    _, _, pd, pid, _ = _cells(res, 2.7 * s, sd + 131, 0.62, taps=5, need2=False)
    pore = _bump((pd / (0.80 * s)) ** 2) * sstep(0.34, 0.72,
            h2(np.floor(pid * 37.0), 0.0, sd + 7))
    porerim = np.exp(-((pd - 1.15 * s) / (0.42 * s)) ** 2) * 0.34    # raised rim
    stain = _ptier(res, 11.0 * s, sd + 19, ang=0.4, relief=0.42) * 0.26
    T = 0.07 + ridge * 0.20 + stain + porerim - pore * 0.70
    return T + _age(res, seed, 0.15, 0.13) + _fine(res, seed, fine)


def g_gravewax(res, seed, lobe=14.0, fine=0.10):
    """Grave wax — adipocere: soft lobes that set into each other, every lobe
    surface crazed with the fine cracks of a wax that dried too slowly."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, lobe * s, sd + 71, 0.52, 0.24)
    dome = np.clip(1.0 - (d1 / (lobe * s * 0.62)) ** 2, 0.0, 1.0) ** 0.7
    F = fbm(res, res, rng(seed, 73), 4, 6)
    craze = _bump(((np.abs(frac(F * 22.0) - 0.5) * 2.0) / 0.16) ** 2) * 0.30
    tier = _tier(h2(np.floor(id1 * 43.0), 0.0, sd + 11))
    T = 0.07 + dome * (0.40 + tier * 0.30) + crown * 0.14 - craze - seam * 0.24
    return T + _age(res, seed, 0.13, 0.12) + _fine(res, seed, fine)


def g_ossuary(res, seed, pitch=13.6, fine=0.11):
    """Ossuary wall — long bones stacked end out, packed with the small pieces
    that fill the gaps, every shaft ring showing its marrow void."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, pitch * s, sd + 89, 0.40, 0.18)
    rad = pitch * s * (0.30 + 0.12 * h2(np.floor(id1 * 31.0), 0.0, sd + 5))
    shaft = sstep(rad * 1.12, rad * 0.90, d1)
    wall = np.exp(-((d1 - rad * 0.72) / (1.15 * s)) ** 2)      # cortical ring
    marrow = _bump((d1 / (rad * 0.46)) ** 2)
    _, _, fd, fid_, _ = _cells(res, pitch * s * 0.40, sd + 233, 0.60, taps=5, need2=False)
    chips = _bump((fd / (1.5 * s)) ** 2) * sstep(0.50, 0.84,
             h2(np.floor(fid_ * 29.0), 0.0, sd + 13)) * (1.0 - shaft)
    tier = _tier(h2(np.floor(id1 * 59.0), 0.0, sd + 17))
    stria = (0.5 + 0.5 * np.cos(np.arctan2(dy, dx) * 26.0 + id1 * _TAU)) * shaft * 0.24
    porosity = _grain(xx, yy, 2.8 * s, sd + 43, thr=0.60) * 0.24
    T = (0.07 + shaft * (0.26 + tier * 0.26) + wall * 0.50 - marrow * 0.38
         + chips * 0.34 + stria + porosity * shaft - seam * 0.16)
    return T + _age(res, seed, 0.17, 0.13) + _fine(res, seed, fine)


def g_shroud(res, seed, weave=4.8, fine=0.10):
    """Shroud — loose linen: a plain weave with threads pulled out of it and
    the bloom of what soaked through."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    p = weave * s
    wu = (h2(np.floor(yy / p), 0.0, sd + 3) - 0.5) * 0.5 * p    # slack in the warp
    wv = (h2(np.floor(xx / p), 0.0, sd + 5) - 0.5) * 0.5 * p
    fu = frac((xx + wv) / p) - 0.5
    fv = frac((yy + wu) / p) - 0.5
    warp = np.clip(1.0 - (np.abs(fu) / 0.33) ** 2, 0.0, 1.0)
    weft = np.clip(1.0 - (np.abs(fv) / 0.33) ** 2, 0.0, 1.0)
    over = np.mod(np.floor((xx + wv) / p) + np.floor((yy + wu) / p), 2.0)
    cloth = np.where(over > 0.5, np.maximum(warp, weft * 0.42),
                     np.maximum(weft, warp * 0.42))
    pull = sstep(0.66, 0.92, h2(np.floor(xx / (p * 9.0)), np.floor(yy / (p * 9.0)), sd + 23))
    tier = _tier(h2(np.floor(xx / (p * 5.0)), np.floor(yy / (p * 5.0)), sd + 31)) * 0.24
    T = 0.07 + cloth * (0.36 + tier) * (1.0 - pull * 0.55) + pull * 0.10
    return T + _age(res, seed, 0.14, 0.13) + _fine(res, seed, fine)


def g_frost(res, seed, feather=15.0, fine=0.11):
    """Barrow frost — hoar crystals feathering off cold stone.

    [relics iter24] Rewritten as real dendritic growth: ice nucleates at
    scattered sites and grows SIX arms (hexagonal habit), each arm carrying
    side-branches that shorten toward the tip. The first pass built the frost
    from contours of a smooth field, which reads as a topographic map, not a
    crystal."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, 3.0)
    dx, dy, d1, id1, _ = _cells(res, feather * s, sd + 137, 0.55, taps=9, need2=False)
    dxw, dyw = dx + wu * 0.5, dy + wv * 0.5
    d = np.hypot(dxw, dyw) + 1e-5
    th = np.arctan2(dyw, dxw) + id1 * _TAU
    R = feather * s * (0.95 + 0.45 * h2(np.floor(id1 * 37.0), 0.0, sd + 5))
    arm = (0.5 + 0.5 * np.cos(6.0 * th)) ** 4                  # hexagonal habit
    reach = np.clip(1.0 - d / R, 0.0, 1.0)
    spine = arm * reach
    # side branches: rungs along each arm, shortening toward the tip
    rung = (0.5 + 0.5 * np.cos(d / (1.5 * s) * _TAU)) ** 3
    side = (0.5 + 0.5 * np.cos(6.0 * th + np.pi / 6.0)) ** 8 * rung * reach ** 2
    ice = np.clip(spine * 1.25 + side * 0.85, 0.0, 1.0)
    facet = _grain(xx, yy, 2.9 * s, sd + 41, thr=0.40) * 0.34
    rime = _grain(xx, yy, 4.6 * s, sd + 59, thr=0.30) * 0.30    # granular rime mat
    T = 0.05 + ice * 0.62 + facet * (0.35 + ice) + rung * reach * 0.10 + rime
    return T + _age(res, seed, 0.10, 0.14) + _fine(res, seed, fine)


def g_urnslip(res, seed, burnish_p=9.0, fine=0.10):
    """Urn slip — a burnished pot: the pebble tool left its parallel strokes,
    the kiln left its clouds."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 101, 5.0)
    ang = 1.15
    u = (xx + wu) * np.cos(ang) + (yy + wv) * np.sin(ang)
    stroke = 0.5 + 0.5 * np.cos(u / (burnish_p * s * 0.30) * _TAU)
    lane = np.floor(u / (burnish_p * s * 2.4))
    amp = 0.55 + 0.45 * h2(lane, np.floor((yy - xx * 0.3) / (burnish_p * s * 6.0)), sd + 7)
    cloud = _ptier(res, 9.0 * s, sd + 13, ang=0.7, relief=0.45) * 0.22
    grit = _grain(xx, yy, 3.4 * s, sd + 29, thr=0.58) * 0.26
    chatter = _bump(((frac(u / (burnish_p * s * 0.94)) - 0.5) / 0.18) ** 2) * 0.20  # tool chatter
    T = 0.08 + stroke * amp * 0.46 + cloud + grit + chatter
    return T + _age(res, seed, 0.16, 0.12) + _fine(res, seed, fine)


def g_varnish(res, seed, plate=11.5, fine=0.10):
    """Coffin varnish — shellac gone alligator: hard plates of finish curling
    off the grain that still shows underneath."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, plate * s, sd + 113, 0.38, 0.26)
    curl = np.clip(1.0 - (d1 / (plate * s * 0.55)) ** 2, 0.0, 1.0) ** 0.8
    lip = _fat(edge, 0.13) * 0.42                              # the curled edge
    grain = _fibers(res, seed + 5, 0.10, 6.2, wob=2.0, duty=0.62) * 0.24
    tier = _tier(h2(np.floor(id1 * 47.0), 0.0, sd + 11))
    T = 0.07 + curl * (0.34 + tier * 0.30) + grain * (1.0 - curl * 0.45) + lip - seam * 0.34
    return T + _age(res, seed, 0.17, 0.12) + _fine(res, seed, fine)


def g_boneash(res, seed, sinter=6.4, fine=0.12):
    """Bone ash — calcined to a crust: grains sintered into each other with the
    voids the burning left between them."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    acc = np.zeros((res, res), np.float32)
    for k, (p, w, salt) in enumerate(((sinter, 0.52, 149), (sinter * 1.7, 0.32, 163),
                                      (sinter * 2.8, 0.22, 179))):
        _, _, d, idk, _ = _cells(res, p * s, sd + salt, 0.58, taps=5, need2=False)
        acc += _bump((d / (p * s * 0.34)) ** 2) * w * (0.5 + 0.5 * _tier(
            h2(np.floor(idk * 33.0), 0.0, sd + salt + 3)))
    void = sstep(0.30, 0.02, acc) * 0.30
    T = 0.07 + acc * 0.44 - void
    return T + _age(res, seed, 0.12, 0.15) + _fine(res, seed, fine)


def g_tallow(res, seed, drip=16.0, fine=0.10):
    """Corpse candle — tallow run down in curtains and set, wick soot blackening
    the runs it poured over."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    lane = np.floor(xx / (drip * s * 0.42))
    jit = (h2(lane, 0.0, sd + 5) - 0.5) * 0.7
    q = xx / (drip * s * 0.42) + jit
    col = np.clip(1.0 - (np.abs(frac(q) - 0.5) / 0.38) ** 2, 0.0, 1.0)
    phase = h2(lane, 0.0, sd + 11) * _TAU
    length = 0.45 + 0.5 * h2(lane, 0.0, sd + 17)
    run = sstep(length + 0.10, length - 0.30,
                frac(yy / (drip * s * 3.4) + phase * 0.16))
    bead = _bump(((frac(yy / (drip * s * 0.62) + phase) - 0.5) / 0.26) ** 2) * 0.34
    soot = _grain(xx, yy, 4.2 * s, sd + 37, thr=0.60) * 0.24
    T = 0.07 + col * run * (0.44 + bead) - soot * (1.0 - col * run * 0.5)
    return T + _age(res, seed, 0.14, 0.12) + _fine(res, seed, fine)


def g_barrowsoil(res, seed, pitch=7.6, fine=0.12):
    """Barrow soil — the matrix an excavation comes out of: grit, root threads
    and the sherd edges that make the dig worth digging."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    _, _, gd, gid, _ = _cells(res, pitch * s, sd + 191, 0.62, taps=5, need2=False)
    grit = _bump((gd / (pitch * s * 0.34)) ** 2) * (0.45 + 0.55 * _tier(
        h2(np.floor(gid * 41.0), 0.0, sd + 7)))
    F = gauss(fbm(res, res, rng(seed, 193), 3, 5), 1.6 * s)
    root = _bump(((np.abs(frac(F * 26.0) - 0.5) * 2.0) / 0.13) ** 2) * 0.34
    dx, dy, d1, sid, edge, crown, seam = _pave(res, pitch * s * 3.1, sd + 197, 0.55, 0.14)
    sherd = crown * sstep(0.66, 0.90, h2(np.floor(sid * 53.0), 0.0, sd + 11)) * 0.42
    T = 0.07 + grit * 0.36 + root + sherd - seam * sherd * 0.5
    return T + _age(res, seed, 0.16, 0.14) + _fine(res, seed, fine)


# ════════════════════════════════════════════════════════════════════════════
# 🜏 THE ORACLE — divination: the surfaces people read the future off
# ════════════════════════════════════════════════════════════════════════════

def g_crackle(res, seed, plate=12.0, fine=0.10):
    """Blood augury — a poured offering dried to a crackle glaze: the network of
    cracks is the reading, fed by the veins that ran while it was still wet."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, plate * s, sd + 151, 0.55, 0.10)
    dx2, dy2, d2, id2, edge2, crown2, seam2 = _pave(res, plate * s * 0.42, sd + 157, 0.60, 0.09)
    crack = np.maximum(seam, seam2 * 0.66)                     # two crack orders
    gloss = crown * (0.55 + 0.45 * crown2)
    tier = _tier(h2(np.floor(id1 * 43.0), 0.0, sd + 7))
    F = gauss(fbm(res, res, rng(seed, 159), 3, 4), 2.4 * s)
    vein = _bump(((np.abs(frac(F * 17.0) - 0.5) * 2.0) / 0.11) ** 2) * 0.30
    stip = _grain(xx, yy, 3.0 * s, sd + 61, thr=0.50) * 0.30
    T = (0.06 + gloss * (0.54 + tier * 0.34) + vein * (1.0 - crack)
         + stip * gloss - crack * 0.62)
    return T + _age(res, seed, 0.14, 0.12) + _fine(res, seed, fine)


def g_planchette(res, seed, cell=9.6, fine=0.10):
    """Planchette path — a spirit board worn by decades of travel: the letter
    blocks are still there under the arcs the planchette polished into them."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    p = cell * s
    ci, rj = np.floor(xx / p), np.floor(yy / (p * 1.35))
    fu = frac(xx / p) - 0.5
    fv = frac(yy / (p * 1.35)) - 0.5
    block = np.clip(1.0 - (np.maximum(np.abs(fu) / 0.34, np.abs(fv) / 0.30)) ** 2, 0.0, 1.0)
    letter = _bump(((frac(fu * 5.0 + h2(ci, rj, sd + 3)) - 0.5) / 0.30) ** 2)         * _bump(((frac(fv * 4.0 + h2(ci, rj, sd + 5)) - 0.5) / 0.34) ** 2)
    cx, cy = 1.35 * res, -0.35 * res                           # pivot off the board
    d = np.hypot(xx - cx, yy - cy)
    sweep = _bump(((np.abs(frac(d / (10.0 * s)) - 0.5) * 2.0) / 0.42) ** 2)
    wear = sweep * 0.34
    grain = _fibers(res, seed + 9, 0.03, 6.8, wob=1.6, duty=0.66) * 0.18
    T = 0.07 + block * (0.28 + letter * 0.44) + grain * (1.0 - block * 0.4) + wear
    return T + _age(res, seed, 0.16, 0.12) + _fine(res, seed, fine)


def g_knuckle(res, seed, pitch=11.8, fine=0.11):
    """Casting bones — knucklebones thrown and settled where they fell, packed
    tight, each one knobbed at both ends."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    bone = np.zeros((res, res), np.float32)
    tone = np.zeros((res, res), np.float32)
    for k, salt in enumerate((167, 173, 179)):
        dx, dy, d1, id1, _ = _cells(res, pitch * s * (1.0 + 0.18 * k), sd + salt,
                                    0.52, taps=9, need2=False)
        a = id1 * _TAU + k * 0.9
        ca, sa = np.cos(a), np.sin(a)
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        L = pitch * s * (0.26 + 0.12 * h2(np.floor(id1 * 31.0), 0.0, sd + 3))
        shaft = np.clip(1.0 - ((v / (L * 0.44)) ** 2 + (u / (L * 1.25)) ** 2), 0.0, 1.0)
        knob1 = _bump((np.hypot(u - L, v) / (L * 0.62)) ** 2)
        knob2 = _bump((np.hypot(u + L, v) / (L * 0.62)) ** 2)
        b = np.maximum(shaft * 0.9, np.maximum(knob1, knob2))
        m = b > bone
        bone = np.where(m, b, bone)
        tone = np.where(m, _tier(h2(np.floor(id1 * 53.0), 0.0, sd + salt)), tone)
    T = 0.07 + bone * (0.40 + tone * 0.34)
    return T + _age(res, seed, 0.17, 0.13) + _fine(res, seed, fine)


def g_tealeaf(res, seed, ring=17.0, fine=0.11):
    """Tasseomancy — leaf fragments left in the cup, settled into the bands the
    last swirl of tea drew them into."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 181, 6.0)
    cx, cy = 0.62 * res, 1.28 * res                            # cup rim off-canvas
    d = np.hypot((xx + wu) - cx, (yy + wv) - cy)
    th = np.arctan2((yy + wv) - cy, (xx + wu) - cx)
    band = 0.5 + 0.5 * np.cos(d / (ring * s) * _TAU)
    dx, dy, d1, id1, _ = _cells(res, 5.6 * s, sd + 187, 0.62, taps=5, need2=False)
    a = id1 * _TAU
    ca, sa = np.cos(a), np.sin(a)
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    flake = np.clip(1.0 - ((u / (3.4 * s)) ** 2 + (v / (1.35 * s)) ** 2), 0.0, 1.0)
    fedge = np.exp(-((np.sqrt((u / (3.4 * s)) ** 2 + (v / (1.35 * s)) ** 2) - 0.92) / 0.13) ** 2) * 0.40
    curl = 0.5 + 0.5 * np.cos(u / (0.9 * s) * _TAU)
    leafvein = _bump(((frac(v / (0.42 * s)) - 0.5) / 0.30) ** 2) * flake * 0.30
    tier = _tier(h2(np.floor(id1 * 47.0), 0.0, sd + 11))
    density = sstep(0.25, 0.85, band)
    T = (0.07 + flake * (0.34 + tier * 0.34) * (0.55 + 0.45 * curl) * (0.40 + 0.75 * density)
         + leafvein + fedge + band * 0.10 + _grain(xx, yy, 3.0 * s, sd + 53, thr=0.56) * 0.26)
    return T + _age(res, seed, 0.14, 0.13) + _fine(res, seed, fine)


def g_dermato(res, seed, ridge=3.1, fine=0.10):
    """Palm reading — friction ridges flowing around the loops and whorls they
    grew into, broken where the major lines cross them."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    # ridge phase from a few singularities: loops (charge +1) and deltas (-1)
    phase = np.zeros((res, res), np.float32)
    for k in range(5):
        px = (0.18 + 0.66 * h2(np.float32(k), 0.0, sd + 3)) * res
        py = (0.18 + 0.66 * h2(np.float32(k), 1.0, sd + 5)) * res
        q = 1.0 if k % 2 == 0 else -1.0
        phase = phase + q * np.arctan2(yy - py, xx - px)
    base = (xx * 0.55 + yy * 0.30) / (ridge * s)
    q = base + phase * (1.0 / _TAU) * 3.0
    rdg = np.clip(1.0 - (np.abs(frac(q) - 0.5) / 0.34) ** 2, 0.0, 1.0)
    pore = _grain(xx, yy, 3.0 * s, sd + 23, thr=0.72) * 0.24 * rdg
    F = gauss(fbm(res, res, rng(seed, 191), 2, 3), 6.0 * s)
    major = _bump(((np.abs(frac(F * 5.0) - 0.5) * 2.0) / 0.055) ** 2) * 0.42
    tier = _tier(h2(np.floor(q), np.floor((yy * 0.55 - xx * 0.30) / (ridge * s * 12.0)), sd + 13))
    T = 0.06 + rdg * (0.56 + tier * 0.34) - pore * 1.2 - major * 1.15
    return T + _age(res, seed, 0.13, 0.12) + _fine(res, seed, fine)


def g_astrolabe(res, seed, arc=13.5, fine=0.09):
    """Astrolabe plate — almucantar arcs and azimuth rays engraved into brass,
    with a star pointer punched at the crossings."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    cx, cy = -0.30 * res, 1.42 * res                           # pole off the plate
    d = np.hypot(xx - cx, yy - cy)
    th = np.arctan2(yy - cy, xx - cx)
    ring = np.abs(frac(d / (arc * s)) - 0.5) * 2.0
    almu = _bump((ring / 0.10) ** 2)                           # engraved arc line
    az = np.abs(frac(th * (30.0 / _TAU) * _TAU / _TAU * 9.0) - 0.5) * 2.0
    azl = _bump((az / 0.09) ** 2) * sstep(0.25 * res, 0.9 * res, d)
    tick = _bump((ring / 0.30) ** 2) * _bump((az / 0.34) ** 2) * 0.5
    star = _bump((np.maximum(ring / 0.22, az / 0.22)) ** 2)         * sstep(0.55, 0.86, h2(np.floor(d / (arc * s)), np.floor(th * 4.5), sd + 7))
    brass = _fibers(res, seed + 3, 0.9, 4.2, wob=0.8, duty=0.7) * 0.16
    tier = _tier(h2(np.floor(d / (arc * s)), np.floor(th * 4.5), sd + 17))
    T = 0.08 + (almu + azl * 0.8) * (0.34 + tier * 0.30) + tick * 0.24 + star * 0.42 + brass
    return T + _age(res, seed, 0.15, 0.11) + _fine(res, seed, fine)


def g_ceromancy(res, seed, sheet=15.0, fine=0.10):
    """Ceromancy — molten wax dropped into cold water: it sets as thin lobed
    sheets, holed and rimmed where it tore."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    F = gauss(fbm(res, res, rng(seed, 197), 4, 5), 1.4 * s)
    G = gauss(fbm(res, res, rng(seed, 199), 3, 4), 3.0 * s)
    film = sstep(0.44, 0.52, F * 0.7 + G * 0.3)                # the sheet
    rim = _bump(((np.abs(F * 0.7 + G * 0.3 - 0.48) * 2.0) / 0.055) ** 2)
    _, _, hd, hid, _ = _cells(res, sheet * s * 0.62, sd + 211, 0.62, taps=5, need2=False)
    hole = _bump((hd / (2.0 * s)) ** 2) * sstep(0.62, 0.90, h2(np.floor(hid * 37.0), 0.0, sd + 5))
    hrim = np.exp(-((hd - 2.3 * s) / (0.8 * s)) ** 2) * 0.34
    tier = _ptier(res, 8.0 * s, sd + 13, ang=0.3, relief=0.5) * 0.26
    T = 0.07 + film * (0.34 + tier) + rim * 0.44 + hrim * hole * 0.0 + hrim - hole * 0.40
    return T + _age(res, seed, 0.13, 0.12) + _fine(res, seed, fine)


def g_obsidian(res, seed, shell=8.6, fine=0.09):
    """Black mirror — a scrying glass knapped from obsidian: conchoidal shells
    ripple out from every strike, and the breath of whoever last used it still
    blooms across the face."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, shell * s * 2.6, sd + 223, 0.50, 0.12)
    ripple = 0.5 + 0.5 * np.cos(d1 / (shell * s * 0.30) * _TAU + id1 * _TAU)
    conch = crown * (0.45 + 0.55 * ripple ** 2)
    bloom = sstep(0.42, 0.86, n01(gauss(fbm(res, res, rng(seed, 227), 2, 3), 9.0 * s))) * 0.20
    tier = _tier(h2(np.floor(id1 * 61.0), 0.0, sd + 11))
    T = 0.06 + conch * (0.42 + tier * 0.26) + bloom - seam * 0.34
    return T + _age(res, seed, 0.11, 0.11) + _fine(res, seed, fine)


def g_inkplume(res, seed, filament=3.6, fine=0.10):
    """Ink scrying — a drop of ink opening in water: sheets of filament pulled
    into each other, thinning to smoke at the edges."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 229, 26.0)                   # heavy advection
    wu2, wv2 = warp_pair(res, seed, 233, 9.0)
    u = xx + wu + wu2 * 0.5
    v = yy + wv + wv2 * 0.5
    q = (u * 0.62 + v * 0.30) / (filament * s)
    strand = np.clip(1.0 - (np.abs(frac(q) - 0.5) / 0.36) ** 2, 0.0, 1.0)
    q2 = (u * -0.28 + v * 0.74) / (filament * s * 1.7)
    strand2 = np.clip(1.0 - (np.abs(frac(q2) - 0.5) / 0.40) ** 2, 0.0, 1.0) * 0.62
    density = sstep(0.30, 0.80, n01(gauss(np.hypot(wu, wv), 5.0 * s)))
    tier = _tier(h2(np.floor(q), np.floor(q2), sd + 19))
    T = 0.07 + np.maximum(strand, strand2) * (0.36 + tier * 0.32) * (0.45 + 0.75 * density)
    return T + _age(res, seed, 0.11, 0.13) + _fine(res, seed, fine)


def g_liver(res, seed, lobe=17.0, fine=0.10):
    """Haruspex — the reading surface itself: lobes divided by their fissures,
    the vessel tree branching across every one of them."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, lobe * s, sd + 239, 0.48, 0.16)
    F = gauss(fbm(res, res, rng(seed, 241), 4, 4), 1.8 * s)
    # vessel tree: three thinning orders of the same warped field
    v1 = _bump(((np.abs(frac(F * 6.0) - 0.5) * 2.0) / 0.075) ** 2)
    v2 = _bump(((np.abs(frac(F * 13.0) - 0.5) * 2.0) / 0.055) ** 2) * 0.66
    v3 = _bump(((np.abs(frac(F * 27.0) - 0.5) * 2.0) / 0.045) ** 2) * 0.40
    vessels = np.clip(v1 + v2 + v3, 0.0, 1.2)
    grain = _grain(xx, yy, 2.7 * s, sd + 29, thr=0.48) * 0.36
    acini = _bump(((_cells(res, 3.4 * s, sd + 313, 0.6, taps=5, need2=False)[2]) / (1.15 * s)) ** 2) * 0.26
    tier = _tier(h2(np.floor(id1 * 41.0), 0.0, sd + 13))
    T = (0.07 + crown * (0.32 + tier * 0.28) + grain * crown + acini * crown
         + vessels * 0.44 - seam * 0.30)
    return T + _age(res, seed, 0.14, 0.12) + _fine(res, seed, fine)


# ════════════════════════════════════════════════════════════════════════════
# ⚗ THE ALEMBIC — alchemy: what was left in the vessels
# ════════════════════════════════════════════════════════════════════════════

def g_slag(res, seed, vesicle=9.0, fine=0.11):
    """Athanor slag — the glass that froze in the furnace mouth: gas vesicles
    caught mid-rise, strung out along the flow that was still moving."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 251, 14.0)
    flowq = ((xx + wu) * 0.34 + (yy + wv) * 0.94) / (vesicle * s * 2.2)
    band = 0.5 + 0.5 * np.cos(flowq * _TAU)
    _, _, vd_, vid, _ = _cells(res, vesicle * s, sd + 257, 0.60, taps=9, need2=False)
    rad = vesicle * s * (0.16 + 0.26 * h2(np.floor(vid * 37.0), 0.0, sd + 3))
    bubble = sstep(rad * 1.10, rad * 0.86, vd_)
    lip = np.exp(-((vd_ - rad) / (0.75 * s)) ** 2) * 0.44      # the meniscus rim
    tier = _tier(h2(np.floor(vid * 53.0), 0.0, sd + 11))
    glassgrain = _grain(xx, yy, 3.2 * s, sd + 29, thr=0.60) * 0.22
    T = 0.07 + band * (0.26 + tier * 0.26) + glassgrain - bubble * 0.44 + lip
    return T + _age(res, seed, 0.15, 0.13) + _fine(res, seed, fine)


def g_botryoid(res, seed, nodule=11.0, fine=0.11):
    """Sulfur crust — botryoidal: spheroids budded on spheroids, with the
    needle crystals that sublimed out of the gaps between them."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    acc = np.zeros((res, res), np.float32)
    tone = np.zeros((res, res), np.float32)
    for k, (p, salt) in enumerate(((nodule, 263), (nodule * 0.54, 269), (nodule * 0.31, 271))):
        dx, dy, d, idk, _ = _cells(res, p * s, sd + salt, 0.56, taps=9, need2=False)
        rad = p * s * (0.42 + 0.20 * h2(np.floor(idk * 31.0), 0.0, sd + salt + 1))
        bud = np.clip(1.0 - (d / rad) ** 2, 0.0, 1.0) ** 0.6
        m = bud > acc
        acc = np.where(m, bud, acc)
        tone = np.where(m, _tier(h2(np.floor(idk * 47.0), 0.0, sd + salt + 5)), tone)
    gap = sstep(0.30, 0.02, acc)
    needle = _fibers(res, seed + 7, 0.42, 1.9, wob=1.4, duty=0.42) * gap * 0.46
    T = 0.07 + acc * (0.36 + tone * 0.32) + needle
    return T + _age(res, seed, 0.14, 0.14) + _fine(res, seed, fine)


def g_venation(res, seed, blade=15.0, fine=0.10):
    """Herbarium press — a specimen flattened onto rag paper a century ago:
    midrib, secondaries, and the reticulation between them, over foxing."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 277, 5.0)
    u = (xx + wu) / (blade * s)
    v = (yy + wv) / (blade * s)
    mid = _bump(((frac(v * 0.34) - 0.5) / 0.030) ** 2) * 0.9   # midribs
    lat = np.abs(frac(v * 0.34) - 0.5) * 2.0
    sec = _bump(((frac(u * 1.15 + lat * 1.6) - 0.5) / 0.055) ** 2) * (0.55 + 0.45 * lat)
    F = gauss(fbm(res, res, rng(seed, 281), 4, 6), 1.2 * s)
    retic = _bump(((np.abs(frac(F * 30.0) - 0.5) * 2.0) / 0.10) ** 2) * 0.34
    fox = _grain(xx, yy, 5.4 * s, sd + 19, thr=0.74) * 0.30    # foxing spots
    rag = _fibers(res, seed + 3, 1.9, 2.6, wob=1.0, duty=0.5) * 0.14
    T = 0.08 + mid * 0.44 + sec * 0.40 + retic + rag + fox
    return T + _age(res, seed, 0.13, 0.12) + _fine(res, seed, fine)


def g_ringtext(res, seed, ring=11.0, fine=0.09):
    """Transmutation seal — concentric engraved bands of ring text with the
    figure struck across them, cut sharp into the plate."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    cx, cy = 0.42 * res, 1.03 * res                            # centre just off-plate
    d = np.hypot(xx - cx, yy - cy)
    th = np.arctan2(yy - cy, xx - cx)
    rq = d / (ring * s)
    rline = _bump(((np.abs(frac(rq) - 0.5) * 2.0) / 0.11) ** 2)
    glyph_n = 46.0
    gq = (th / _TAU + 0.5) * glyph_n                       # 46 glyphs per ring
    letter = _bump(((frac(gq) - 0.5) / 0.26) ** 2)         * _bump(((np.abs(frac(rq) - 0.5) * 2.0 - 0.42) / 0.24) ** 2)         * (0.45 + 0.55 * _tier(h2(np.floor(gq), np.floor(rq), sd + 7)))
    # the struck figure: two rotated triangles as straight chords
    fig = np.zeros((res, res), np.float32)
    for a0 in (0.0, 1.047, 2.094, 3.14159, 4.18879, 5.23599):
        ln = np.abs((xx - cx) * np.cos(a0) + (yy - cy) * np.sin(a0) - ring * s * 3.1)
        fig = np.maximum(fig, _bump((ln / (1.05 * s)) ** 2))
    plate = _fibers(res, seed + 5, 0.75, 4.6, wob=0.7, duty=0.72) * 0.14
    T = 0.06 + rline * 0.52 + letter * 0.60 + fig * 0.46 + plate * 0.7
    return T + _age(res, seed, 0.16, 0.11) + _fine(res, seed, fine)


def g_bloomcells(res, seed, colony=10.5, fine=0.11):
    """Verdigris bloom — copper corrosion spreading as colonies: each one a
    crusted disc that grew until it met the next, rimmed where they touched."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, colony * s, sd + 283, 0.58, 0.18)
    growth = 0.5 + 0.5 * np.cos(d1 / (1.7 * s) * _TAU + id1 * _TAU)   # growth rings
    crust = crown * (0.5 + 0.5 * growth ** 2)
    _, _, md, mid_, _ = _cells(res, 3.0 * s, sd + 293, 0.62, taps=5, need2=False)
    micro = _bump((md / (1.05 * s)) ** 2) * sstep(0.40, 0.80,
             h2(np.floor(mid_ * 29.0), 0.0, sd + 13)) * 0.34
    tier = _tier(h2(np.floor(id1 * 61.0), 0.0, sd + 17))
    T = 0.07 + crust * (0.38 + tier * 0.30) + micro * (0.4 + crown) - seam * 0.26
    return T + _age(res, seed, 0.17, 0.13) + _fine(res, seed, fine)


def g_tincture(res, seed, ring=16.0, fine=0.10):
    """Apothecary crust — a bottle left to evaporate: every level it stopped at
    is a ring, and the salt it dropped crystallised on each one."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 307, 7.0)
    acc = np.zeros((res, res), np.float32)
    tone = np.zeros((res, res), np.float32)
    for k, salt in enumerate((311, 313, 317)):
        _, _, d, idk, _ = _cells(res, ring * s * (1.0 + 0.5 * k), sd + salt, 0.62,
                                 taps=5, need2=False)
        dd = d + (wu + wv) * 0.12
        r0 = ring * s * (0.30 + 0.22 * h2(np.floor(idk * 37.0), 0.0, sd + salt))
        rim = np.exp(-((dd - r0) / (1.05 * s)) ** 2)
        m = rim > acc
        acc = np.where(m, rim, acc)
        tone = np.where(m, _tier(h2(np.floor(idk * 43.0), 0.0, sd + salt + 3)), tone)
    crystal = _grain(xx, yy, 2.8 * s, sd + 23, thr=0.52) * 0.34
    film = _ptier(res, 9.5 * s, sd + 29, ang=0.6, relief=0.42) * 0.22
    T = 0.07 + acc * (0.42 + tone * 0.30) + crystal * (0.35 + acc) + film
    return T + _age(res, seed, 0.13, 0.13) + _fine(res, seed, fine)


def g_etchpit(res, seed, pit=8.4, fine=0.11):
    """Vitriol etch — acid on metal: pits that ate outward along the grain,
    each one fringed by the dendrites the reaction left."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, _ = _cells(res, pit * s, sd + 331, 0.62, taps=9, need2=False)
    a = id1 * _TAU
    ca, sa = np.cos(a), np.sin(a)
    u = dx * ca + dy * sa
    v = (-dx * sa + dy * ca) * 1.9                             # pits eat anisotropically
    dd = np.hypot(u, v)
    rad = pit * s * (0.24 + 0.20 * h2(np.floor(id1 * 31.0), 0.0, sd + 5))
    pitm = sstep(rad * 1.15, rad * 0.80, dd)
    fringe = _bump(((dd - rad * 1.35) / (0.95 * s)) ** 2)         * (0.5 + 0.5 * np.cos(np.arctan2(v, u) * 11.0)) * 0.42
    grainl = _fibers(res, seed + 3, 1.25, 3.4, wob=0.9, duty=0.62) * 0.24
    tier = _tier(h2(np.floor(id1 * 59.0), 0.0, sd + 11))
    T = 0.08 + grainl + fringe + tier * 0.16 - pitm * 0.50
    return T + _age(res, seed, 0.16, 0.13) + _fine(res, seed, fine)


def g_mercury(res, seed, bead=10.0, fine=0.10):
    """Quicksilver — beads that ran together and stopped: fat lenses joined by
    necks, with a tarnish skin creeping over the ones that sat longest."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    field = np.zeros((res, res), np.float32)
    for k, salt in enumerate((337, 347, 349)):
        _, _, d, idk, _ = _cells(res, bead * s * (1.0 + 0.42 * k), sd + salt, 0.58,
                                 taps=9, need2=False)
        r0 = bead * s * (0.42 + 0.22 * h2(np.floor(idk * 29.0), 0.0, sd + salt))
        field = field + np.exp(-(d / r0) ** 2) * (0.9 - 0.2 * k)   # metaball sum
    body = sstep(0.52, 0.86, field)                            # coalesced surface
    dome = np.clip(field - 0.52, 0.0, 1.0) ** 0.6
    rim = np.exp(-((field - 0.62) / 0.09) ** 2) * 0.46          # specular meniscus
    tarnish = _grain(xx, yy, 3.6 * s, sd + 19, thr=0.62) * 0.26
    T = 0.07 + body * 0.26 + dome * 0.40 + rim - tarnish * body * 0.6
    return T + _age(res, seed, 0.12, 0.12) + _fine(res, seed, fine)


def g_gasket(res, seed, big=17.0, fine=0.10):
    """Philosopher's Stone — the impossible packing: discs of every size nested
    into the gaps of the discs before them, each cut as a faceted gem."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    acc = np.zeros((res, res), np.float32)
    tone = np.zeros((res, res), np.float32)
    facet = np.zeros((res, res), np.float32)
    for k, (p, rr, salt) in enumerate(((big, 0.50, 353), (big * 0.55, 0.46, 359),
                                       (big * 0.32, 0.42, 367), (big * 0.19, 0.38, 373))):
        dx, dy, d, idk, _ = _cells(res, p * s, sd + salt, 0.50,
                                   taps=9 if k < 2 else 5, need2=False)
        r0 = p * s * rr
        disc = sstep(r0, r0 * 0.90, d)
        if k:
            disc = disc * (1.0 - sstep(0.55, 0.85, acc))       # only in the gaps
        cut = (0.5 + 0.5 * np.cos((np.arctan2(dy, dx) + idk * _TAU) * 8.0)) ** 2 * disc
        cut = cut + np.exp(-((d - r0 * 0.82) / (1.1 * s)) ** 2) * disc * 0.6   # girdle
        m = disc > acc
        acc = np.where(m, np.maximum(acc, disc), acc)
        facet = np.where(m, cut, facet)
        tone = np.where(m, _tier(h2(np.floor(idk * 41.0), 0.0, sd + salt)), tone)
        acc = np.maximum(acc, disc)
    T = 0.07 + acc * (0.34 + tone * 0.30) + facet * 0.30
    return T + _age(res, seed, 0.14, 0.12) + _fine(res, seed, fine)


def g_druse(res, seed, crystal=9.6, fine=0.10):
    """Cinnabar druse — a vug lined with crystal: every termination a facetted
    point, all of them crowded into the same small space."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    dx, dy, d1, id1, edge, crown, seam = _pave(res, crystal * s, sd + 379, 0.52, 0.12)
    a = id1 * _TAU
    ca, sa = np.cos(a), np.sin(a)
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    # hexagonal termination: three cleaved faces meeting at a point
    f1 = u * 0.866 + v * 0.5
    f2 = -u * 0.866 + v * 0.5
    f3 = -v
    face = np.maximum(np.maximum(f1, f2), f3) / (crystal * s * 0.5)
    point = np.clip(1.0 - face, 0.0, 1.0) ** 0.75 * crown
    which = np.argmax(np.stack([f1, f2, f3]), axis=0).astype(np.float32)
    shade = 0.55 + 0.45 * (which / 2.0)                        # per-face lighting
    tier = _tier(h2(np.floor(id1 * 53.0), 0.0, sd + 11))
    edgel = _fat(edge, 0.09) * 0.34
    T = 0.06 + point * (0.40 + tier * 0.30) * shade + edgel - seam * 0.16
    return T + _age(res, seed, 0.13, 0.12) + _fine(res, seed, fine)

# ════════════════════════════════════════════════════════════════════════════
# ENGINE TABLE + RECIPE HELPER
# ════════════════════════════════════════════════════════════════════════════

_RAW_ENGINES = {
    "slag": g_slag, "botryoid": g_botryoid, "venation": g_venation,
    "ringtext": g_ringtext, "bloomcells": g_bloomcells, "tincture": g_tincture,
    "etchpit": g_etchpit, "mercury": g_mercury, "gasket": g_gasket,
    "druse": g_druse,
    "crackle": g_crackle, "planchette": g_planchette, "knuckle": g_knuckle,
    "tealeaf": g_tealeaf, "dermato": g_dermato, "astrolabe": g_astrolabe,
    "ceromancy": g_ceromancy, "obsidian": g_obsidian, "inkplume": g_inkplume,
    "liver": g_liver,
    "bogleather": g_bogleather, "gravewax": g_gravewax, "ossuary": g_ossuary,
    "shroud": g_shroud, "frost": g_frost, "urnslip": g_urnslip,
    "varnish": g_varnish, "boneash": g_boneash, "tallow": g_tallow,
    "barrowsoil": g_barrowsoil,
    "horn": g_horn, "quill": g_quill, "mothdust": g_mothdust,
    "scute": g_scute, "hoof": g_hoof, "pelt": g_pelt, "spine": g_spine,
    "tubercle": g_tubercle, "sucker": g_sucker, "gill": g_gill,
    "hexfoil": g_hexfoil, "witchbottle": g_witchbottle, "bindknot": g_bindknot,
    "coffinnail": g_coffinnail, "saltcircle": g_saltcircle,
    "poppetstitch": g_poppetstitch, "hagstone": g_hagstone,
    "sigilwax": g_sigilwax, "threadcross": g_threadcross, "ironcage": g_ironcage,
}
ENGINES = {k: kit.lowcut(v) for k, v in _RAW_ENGINES.items()}


def _R(fid, name, engine, lut, hues, desc, *, eargs=None, hue_cell=6.0,
       macro=("none", {}), vd=(0.88, 1.12), tmod=0.08, hspan=0.085,
       satboost=1.18, val=0.225, mats=None, matmix=0.58,
       mat_cuts=(0.34, 0.62, 0.86), pit=1.0, span=0.48, contrast=1.45,
       micro=1.0, burnish=0.55, struct_gain=1.0, kw=None):
    """One relic = one recipe row. `mats` are the four material (M,R,Cc)
    centres the spec carve quantises this finish's own structure into.

    [2026-08-30 iter 2] THE OLD-WORLD COLOUR LAW. Iteration 1 came out candy
    neon — hot magenta and electric blue on every card — because the recipe
    defaults were inherited from the old module (satboost 1.40, no gray dial).
    Nothing about a dug-up object is saturated. The law now:
      satboost 0.55-0.85 (siblings prove 0.77-0.98) + `gray` 0.28-0.55 (aged
      scattering pulls chroma toward the pixel's own luma) + `flash` (chroma
      fires only at luma peaks = the curse waking where light catches) +
      deeper `vd`. Hue diversity is bought by SPREADING the four anchors over
      an old-world arc (rust / amber / verdigris / iron-blue), not by cranking
      saturation — so the finish stays tonal and still clears >= 5 hue bins.

    [iter 3] ...and iteration 2 over-corrected into MUD: gray 0.28-0.50 on top
    of satboost 0.6 and a val ceiling of 0.20 gave ten murky brown-green cards.
    An old object is not muddy — a gold mask under museum light is near-black
    in the recesses and brilliantly chromatic where the light catches. So the
    darkness now comes from VALUE DRAMA (vd shadow 0.26-0.38) and the FLASH
    gate, not from crushing the ceiling: val 0.30-0.38, satboost 0.85-1.15,
    gray only 0.10-0.28 as a scattering seasoning."""
    base_kw = dict(ambient=0.18, ambient_sigma=40, floor=0.075, sparkle=0.07,
                   mswing=1.35, burial=1.0, gray=0.14, flash=(0.30, 0.72))
    if kw:
        base_kw.update(kw)
    # THE LUT-WALK LAW [relics 2026-08-30 iter10] — the single biggest
    # shape-destroyer found this lane. The thin-film LUT is an OSCILLATOR: over
    # a 390-950nm stack it runs ~2 sin^2 cycles, so a T field spanning 0..1 maps
    # smooth geometry onto a non-monotonic curve and every carved arc, scale and
    # nail head comes out as scrambled speckle (the iteration-9 hexfoil crop was
    # pure orange noise — no daisy wheels at all). Compressing the walk to a
    # `span`-wide window centred on the LUT's STEEPEST MONOTONE stretch makes
    # luma track the structure again, so the object reads.
    ea = dict(eargs or {})
    ea.setdefault("span", float(span))
    ea.setdefault("contrast", float(contrast))
    ea.setdefault("mid", kit._lut_steep(lut, float(span)))
    return dict(name=name, engine=engine, eargs=ea,
                seed=_seed(fid), lut=lut, hues=hues, hspan=hspan,
                satboost=satboost, macro=macro, vd=vd, tmod=tmod, val=val,
                hue_cell=hue_cell, hue_drift=0.5, kw=base_kw, desc=desc,
                mats=mats or kit.MATS_DEFAULT, matmix=matmix,
                mat_cuts=mat_cuts, pit=pit, micro=float(micro),
                burnish=float(burnish), struct_gain=float(struct_gain))


# material palettes (M, R, Cc) per zone: void / matrix / polished / inlay
M_IRON = ((22.0, 226.0, 244.0), (78.0, 168.0, 200.0), (196.0, 74.0, 96.0), (238.0, 30.0, 40.0))
M_WOOD = ((18.0, 232.0, 246.0), (62.0, 186.0, 210.0), (150.0, 104.0, 130.0), (226.0, 44.0, 58.0))
M_CLOTH = ((16.0, 238.0, 240.0), (54.0, 198.0, 214.0), (128.0, 122.0, 150.0), (214.0, 56.0, 74.0))
M_STONE = ((24.0, 224.0, 248.0), (86.0, 176.0, 206.0), (176.0, 88.0, 110.0), (232.0, 38.0, 52.0))
M_WAX = ((30.0, 210.0, 232.0), (104.0, 150.0, 178.0), (188.0, 70.0, 88.0), (240.0, 26.0, 34.0))
M_GLASS = ((20.0, 216.0, 250.0), (70.0, 150.0, 196.0), (210.0, 46.0, 62.0), (250.0, 16.0, 22.0))


# ════════════════════════════════════════════════════════════════════════════
# THE 50 — chapter 1 of 5
# ════════════════════════════════════════════════════════════════════════════

_BINDING = {
 # [relics 2026-08-30 iter2] burned oak: amber scorch, rust, olive char, cold iron
 "frl_hexfoil": _R("frl_hexfoil", "Hexfoil Ward", "hexfoil",
    (398.0, 928.0, 1.0, 1.30, 0.9), [0.075, 0.0, 0.17, 0.045],  # hero: ember orange
    "Compass-scribed daisy wheels burned into a threshold beam to turn a witch back at the door. A FRACTURED RELICS finish.",
    eargs=dict(pitch=14.0, arc=2.0), burnish=0.75, hue_cell=6.5, mats=M_WOOD, val=0.235,
    satboost=1.14, macro=("continents", dict(cells=4, lo=0.40, hi=0.64)),
    kw=dict(gray=0.12, flash=(0.28, 0.70))),
 # green bottle glass + the iron inside it
 "frl_witch_bottle": _R("frl_witch_bottle", "Witch Bottle", "witchbottle",
    (392.0, 946.0, 1.0, 1.26, 3.4), [0.32, 0.25, 0.39, 0.3],  # hero: bottle green
    "Bent nails, pins and hair packed into buried glass to catch a curse before it reaches the house. A FRACTURED RELICS finish.",
    eargs=dict(pitch=11.5), burnish=0.85, hue_cell=5.5, mats=M_GLASS, val=0.215,
    satboost=1.30, kw=dict(gray=0.06, sparkle=0.14, flash=(0.34, 0.78))),
 # hemp rope + the oxblood it was soaked in
 "frl_binding_knot": _R("frl_binding_knot", "Binding Knot", "bindknot",
    (404.0, 918.0, 1.0, 1.28, 1.8), [0.235, 0.15, 0.32, 0.205],  # hero: hemp ochre
    "An endless knot tied over and under itself so that whatever it holds can never be untied. A FRACTURED RELICS finish.",
    eargs=dict(pitch=13.5), hue_cell=6.0, mats=M_CLOTH, val=0.225,
    satboost=1.10, kw=dict(gray=0.18)),
 # cold iron plate, rust in the bruises
 "frl_coffin_nail": _R("frl_coffin_nail", "Coffin Nail Ward", "coffinnail",
    (396.0, 934.0, 1.0, 1.24, 5.0), [0.58, 0.51, 0.65, 0.56],  # hero: cold iron blue
    "Coffin nails driven in a ward grid, each head ringed by the bruise its hammer left in the plate. A FRACTURED RELICS finish.",
    eargs=dict(pitch=13.2), hue_cell=6.0, mats=M_IRON, val=0.205,
    satboost=1.06, macro=("domains", dict(cells=6, salt=4021)),
    kw=dict(gray=0.20)),
 # salt on black slate — the one that is allowed to sparkle
 "frl_salt_circle": _R("frl_salt_circle", "Salt Circle", "saltcircle",
    (386.0, 952.0, 1.0, 1.22, 2.6), [0.48, 0.41, 0.55, 0.46],  # hero: ice cyan
    "A poured salt line dried to a crust, throwing dendrites off every edge across black slate. A FRACTURED RELICS finish.",
    eargs=dict(lines=9.0, contrast=1.85), micro=2.2, burnish=1.05, hue_cell=5.0, mats=M_STONE, val=0.20,
    satboost=0.58, kw=dict(gray=0.4, sparkle=0.18, floor=0.10,
                           flash=(0.44, 0.84))),
 # sackcloth tan, red thread, olive mildew
 "frl_poppet_stitch": _R("frl_poppet_stitch", "Poppet Stitch", "poppetstitch",
    (400.0, 922.0, 1.0, 1.28, 4.2), [0.015, 0.945, 0.08, 0.995],  # hero: oxblood
    "Sackcloth closed with crossed sutures and studded with the pins pushed through the poppet. A FRACTURED RELICS finish.",
    eargs=dict(weave=5.4, stitch=13.5), hue_cell=6.5, mats=M_CLOTH, val=0.225, hspan=0.115,
    satboost=1.16, kw=dict(gray=0.14)),
 # flint grey, chalk cortex, sea-worn green
 "frl_hag_stone": _R("frl_hag_stone", "Hag Stone", "hagstone",
    (394.0, 940.0, 0.98, 1.20, 0.4), [0.72, 0.65, 0.79, 0.7],  # hero: flint violet-grey
    "Flint bored through by water, hung on a nail so the eye it grew can watch the door. A FRACTURED RELICS finish.",
    eargs=dict(pitch=15.5, contrast=1.75), micro=2.0, burnish=0.95, hue_cell=6.5, mats=M_STONE, val=0.215,
    satboost=1.04, macro=("continents", dict(cells=5, lo=0.38, hi=0.66)),
    kw=dict(gray=0.22)),
 # oxblood wax, gold die, violet in the deep
 "frl_sigil_wax": _R("frl_sigil_wax", "Sigil Seal", "sigilwax",
    (402.0, 926.0, 1.0, 1.30, 1.2), [0.12, 0.04, 0.2, 0.095],  # hero: old gold
    "Oxblood wax struck with a sigil die, every disc sagging into the skirt it cooled in. A FRACTURED RELICS finish.",
    eargs=dict(pitch=14.0), burnish=0.75, hue_cell=6.0, mats=M_WAX, val=0.235,
    satboost=1.28, kw=dict(gray=0.05, flash=(0.32, 0.74))),
 # crimson yarn on bark
 "frl_thread_cross": _R("frl_thread_cross", "Red Thread Cross", "threadcross",
    (406.0, 914.0, 1.0, 1.30, 3.0), [0.955, 0.885, 0.02, 0.93],  # hero: crimson
    "Crimson yarn wound over crossed rowan twigs, the ply twist running against the wind. A FRACTURED RELICS finish.",
    eargs=dict(wrap=7.6, contrast=1.55), micro=2.4, burnish=1.15, hue_cell=5.5, mats=M_CLOTH, val=0.235,
    satboost=1.22, kw=dict(gray=0.10)),
 # black iron + verdigris weeping from the rivets
 "frl_iron_cage": _R("frl_iron_cage", "Iron Cage", "ironcage",
    (390.0, 944.0, 1.0, 1.24, 5.6), [0.395, 0.325, 0.465, 0.375],  # hero: verdigris
    "Riveted strap iron crossed over a void, forge scale still flaking from the bars. A FRACTURED RELICS finish.",
    eargs=dict(strap=13.0), burnish=0.75, hue_cell=6.0, mats=M_IRON, val=0.195,
    satboost=1.08, macro=("bands", dict(angle=0.5, freq=2.4, warp=0.26)),
    kw=dict(gray=0.26)),
}


# material palettes for organic remains
M_HORN = ((26.0, 220.0, 240.0), (92.0, 158.0, 192.0), (188.0, 74.0, 92.0), (236.0, 30.0, 40.0))
M_CHITIN = ((20.0, 210.0, 246.0), (74.0, 146.0, 198.0), (206.0, 52.0, 66.0), (246.0, 18.0, 24.0))
M_HIDE = ((28.0, 236.0, 236.0), (86.0, 190.0, 206.0), (156.0, 96.0, 122.0), (222.0, 44.0, 60.0))
M_FLESH = ((32.0, 214.0, 230.0), (108.0, 154.0, 180.0), (180.0, 78.0, 96.0), (232.0, 34.0, 44.0))

_BEAST = {
 # yellowed keratin: bone-cream hero, no chroma shouting
 "frl_wendigo_horn": _R("frl_wendigo_horn", "Wendigo Horn", "horn",
    (400.0, 924.0, 1.0, 1.22, 1.4), [0.085, 0.010, 0.160, 0.065],
    "Keratin laid down in growth laminae around a curved core, split lengthwise where it dried. A FRACTURED RELICS finish.",
    eargs=dict(ring=13.0), hue_cell=6.5, mats=M_HORN, val=0.235, satboost=0.66,
    burnish=0.85, kw=dict(gray=0.34)),
 # blue-black iridescent flight feather
 "frl_thunderbird_quill": _R("frl_thunderbird_quill", "Thunderbird Quill", "quill",
    (388.0, 950.0, 1.0, 1.30, 4.6), [0.640, 0.560, 0.720, 0.610],
    "Barbs combed off a storm-bird shaft, zipped by barbules and torn open where the vane parted. A FRACTURED RELICS finish.",
    eargs=dict(barb=3.4), hue_cell=5.5, mats=M_CHITIN, val=0.215, satboost=1.24,
    burnish=0.80, kw=dict(gray=0.10, flash=(0.32, 0.76))),
 # violet-brown moth scale dust
 "frl_mothman_dust": _R("frl_mothman_dust", "Mothman Dust", "mothdust",
    (396.0, 932.0, 1.0, 1.26, 2.2), [0.800, 0.720, 0.880, 0.775],
    "Wing scales shingled in rows, each a ribbed paddle that comes off on your fingers. A FRACTURED RELICS finish.",
    eargs=dict(scale=8.6), hue_cell=6.0, mats=M_CHITIN, val=0.225, satboost=1.12,
    burnish=0.75, kw=dict(gray=0.18)),
 # dark green belly scute
 "frl_lake_serpent": _R("frl_lake_serpent", "Lake Serpent Scute", "scute",
    (392.0, 942.0, 1.0, 1.24, 5.2), [0.340, 0.265, 0.415, 0.320],
    "Keeled belly plates carrying the growth annuli of every year it swam, under a haze of shed skin. A FRACTURED RELICS finish.",
    eargs=dict(pitch=14.5), hue_cell=6.5, mats=M_HIDE, val=0.215, satboost=1.06,
    burnish=0.85, macro=("domains", dict(cells=5, salt=5507)), kw=dict(gray=0.24)),
 # red-brown horn
 "frl_devil_hoof": _R("frl_devil_hoof", "Devil's Hoof", "hoof",
    (404.0, 916.0, 1.0, 1.26, 0.7), [0.045, 0.975, 0.115, 0.020],
    "Horn wall in laminae, packed with the tubules that grew it, split down the cleft. A FRACTURED RELICS finish.",
    eargs=dict(lam=11.0), hue_cell=6.0, mats=M_HORN, val=0.205, satboost=1.10,
    burnish=0.90, kw=dict(gray=0.20)),
 # dark umber matted fur
 "frl_sasquatch_pelt": _R("frl_sasquatch_pelt", "Sasquatch Pelt", "pelt",
    (408.0, 912.0, 1.0, 1.20, 3.8), [0.175, 0.105, 0.245, 0.15],
    "Guard hair matted into locks, every lock combed by the same weather and clumped where it dried. A FRACTURED RELICS finish.",
    eargs=dict(hair=2.6), hue_cell=5.5, mats=M_HIDE, val=0.195, satboost=1.00,
    burnish=1.00, kw=dict(gray=0.26)),
 # sickly teal membrane
 "frl_chupacabra_spine": _R("frl_chupacabra_spine", "Chupacabra Spine", "spine",
    (386.0, 948.0, 1.0, 1.28, 1.9), [0.440, 0.370, 0.515, 0.415],
    "Dorsal spikes in ranks with the membrane still stretched between them, veined and torn. A FRACTURED RELICS finish.",
    eargs=dict(row=15.0), hue_cell=6.0, mats=M_FLESH, val=0.215, satboost=1.18,
    burnish=0.85, kw=dict(gray=0.14, flash=(0.30, 0.74))),
 # olive-drab warty leather
 "frl_grendel_hide": _R("frl_grendel_hide", "Grendel Hide", "tubercle",
    (398.0, 930.0, 1.0, 1.22, 4.1), [0.260, 0.185, 0.335, 0.235],
    "Thick leather gone to warts, nodules of every size bedded in a cracked matrix and seamed where old wounds closed. A FRACTURED RELICS finish.",
    eargs=dict(pitch=12.6), hue_cell=6.5, mats=M_HIDE, val=0.205, satboost=1.02,
    burnish=0.90, kw=dict(gray=0.24)),
 # pink-red flesh cup, chitin teeth
 "frl_kraken_sucker": _R("frl_kraken_sucker", "Kraken Sucker", "sucker",
    (402.0, 922.0, 1.0, 1.28, 2.7), [0.955, 0.885, 0.030, 0.930],
    "Rings of chitin teeth packed down the arm, each cup a ring of dentition around a dark throat. A FRACTURED RELICS finish.",
    eargs=dict(pitch=15.0, contrast=1.85), micro=2.2, hue_cell=6.0, mats=M_FLESH, val=0.225,
    satboost=1.06, burnish=1.35, kw=dict(gray=0.12, flash=(0.34, 0.78))),
 # cyan-green gill lamellae
 "frl_deep_one_gill": _R("frl_deep_one_gill", "Deep One Gill", "gill",
    (390.0, 944.0, 1.0, 1.26, 3.3), [0.530, 0.455, 0.605, 0.505],
    "Lamellae stacked plate on plate in curved ranks, every filament combed by the water it last breathed. A FRACTURED RELICS finish.",
    eargs=dict(lam=4.4), hue_cell=5.5, mats=M_FLESH, val=0.215, satboost=1.16,
    burnish=0.95, kw=dict(gray=0.16)),
}


# material palettes for grave goods
M_BONE = ((24.0, 232.0, 240.0), (88.0, 176.0, 202.0), (170.0, 84.0, 104.0), (228.0, 36.0, 48.0))
M_EARTH = ((26.0, 240.0, 234.0), (80.0, 196.0, 208.0), (146.0, 108.0, 132.0), (214.0, 50.0, 68.0))
M_TALLOW = ((30.0, 206.0, 228.0), (110.0, 146.0, 174.0), (192.0, 66.0, 84.0), (240.0, 24.0, 32.0))
M_ICE = ((18.0, 212.0, 252.0), (66.0, 148.0, 200.0), (204.0, 44.0, 58.0), (248.0, 14.0, 20.0))

_BARROW = {
 "frl_urn_slip": _R("frl_urn_slip", "Urn Slip", "urnslip",
    (404.0, 918.0, 1.0, 1.24, 1.1), [0.025, 0.950, 0.100, 0.005],
    "A burnished funerary pot: the pebble tool left its strokes, the kiln left its clouds. A FRACTURED RELICS finish.",
    eargs=dict(burnish_p=9.0), hue_cell=6.0, mats=M_EARTH, val=0.225, satboost=1.04,
    burnish=0.85, kw=dict(gray=0.22)),
 "frl_bog_body": _R("frl_bog_body", "Bog Body", "bogleather",
    (400.0, 926.0, 1.0, 1.22, 3.6), [0.085, 0.0, 0.175, 0.055],
    "Skin tanned by peat acid, the pore field still there, the whole hide creased where the bog folded it. A FRACTURED RELICS finish.",
    eargs=dict(wrinkle=13.0, contrast=1.70), hue_cell=6.5, mats=M_EARTH, val=0.175,
    satboost=1.10, burnish=1.35, micro=2.0, hspan=0.115, kw=dict(gray=0.26)),
 "frl_coffin_varnish": _R("frl_coffin_varnish", "Coffin Varnish", "varnish",
    (398.0, 934.0, 1.0, 1.28, 0.6), [0.145, 0.055, 0.235, 0.115],
    "Shellac gone alligator, hard plates of finish curling off the grain that still shows underneath. A FRACTURED RELICS finish.",
    eargs=dict(plate=11.5), hue_cell=6.0, mats=M_EARTH, val=0.235, satboost=1.16,
    burnish=0.80, kw=dict(gray=0.12, flash=(0.32, 0.74))),
 "frl_grave_wax": _R("frl_grave_wax", "Grave Wax", "gravewax",
    (396.0, 930.0, 1.0, 1.20, 4.4), [0.205, 0.135, 0.275, 0.180],
    "Adipocere: soft lobes set into each other, every surface crazed by a wax that dried too slowly. A FRACTURED RELICS finish.",
    eargs=dict(lobe=14.0), hue_cell=6.5, mats=M_TALLOW, val=0.225, satboost=0.98,
    burnish=0.95, kw=dict(gray=0.28)),
 "frl_shroud": _R("frl_shroud", "Shroud", "shroud",
    (402.0, 920.0, 1.0, 1.22, 2.4), [0.280, 0.210, 0.350, 0.255],
    "Loose linen with threads pulled out of it and the bloom of what soaked through. A FRACTURED RELICS finish.",
    eargs=dict(weave=4.8), hue_cell=6.0, mats=M_BONE, val=0.235, satboost=0.55,
    burnish=1.00, kw=dict(gray=0.44)),
 "frl_barrow_soil": _R("frl_barrow_soil", "Barrow Soil", "barrowsoil",
    (394.0, 938.0, 1.0, 1.24, 5.4), [0.420, 0.350, 0.490, 0.395],
    "The matrix an excavation comes out of: grit, root threads and the sherd edges that make the dig worth digging. A FRACTURED RELICS finish.",
    eargs=dict(pitch=7.6), hue_cell=5.5, mats=M_EARTH, val=0.205, satboost=1.02,
    burnish=0.85, kw=dict(gray=0.26)),
 "frl_bone_ash": _R("frl_bone_ash", "Bone Ash", "boneash",
    (392.0, 944.0, 1.0, 1.18, 1.7), [0.500, 0.430, 0.570, 0.475],
    "Calcined to a crust, grains sintered into each other with the voids the burning left between. A FRACTURED RELICS finish.",
    eargs=dict(sinter=6.4), hue_cell=5.5, mats=M_BONE, val=0.245, satboost=0.48,
    burnish=0.90, kw=dict(gray=0.5)),
 "frl_barrow_frost": _R("frl_barrow_frost", "Barrow Frost", "frost",
    (386.0, 954.0, 1.0, 1.26, 2.9), [0.580, 0.510, 0.650, 0.555],
    "Hoar crystals feathering off cold stone: a spine, side branches, and branches off those. A FRACTURED RELICS finish.",
    eargs=dict(feather=13.0, contrast=1.70, lowcut=1.4), hue_cell=5.0, mats=M_ICE, val=0.185,
    satboost=1.14, burnish=1.35, micro=2.2, kw=dict(gray=0.14, sparkle=0.14, flash=(0.44, 0.84))),
 "frl_ossuary": _R("frl_ossuary", "Ossuary Wall", "ossuary",
    (406.0, 914.0, 0.98, 1.18, 5.8), [0.700, 0.630, 0.770, 0.675],
    "Long bones stacked end out, packed with the small pieces that fill the gaps, every shaft showing its marrow void. A FRACTURED RELICS finish.",
    eargs=dict(pitch=13.6, contrast=1.80), hue_cell=6.5, mats=M_BONE, val=0.235,
    satboost=0.5, burnish=1.30, micro=1.9, macro=("continents", dict(cells=4, lo=0.40, hi=0.64)),
    kw=dict(gray=0.48)),
 "frl_corpse_candle": _R("frl_corpse_candle", "Corpse Candle", "tallow",
    (390.0, 946.0, 1.0, 1.26, 0.3), [0.920, 0.850, 0.990, 0.895],
    "Tallow run down in curtains and set, wick soot blackening the runs it poured over. A FRACTURED RELICS finish.",
    eargs=dict(drip=16.0), hue_cell=6.0, mats=M_TALLOW, val=0.225, satboost=1.12,
    burnish=0.85, kw=dict(gray=0.16, flash=(0.34, 0.78))),
}


# material palettes for the reading surfaces
M_BOARD = ((22.0, 234.0, 238.0), (76.0, 188.0, 204.0), (168.0, 88.0, 112.0), (226.0, 40.0, 54.0))
M_BRASS = ((20.0, 214.0, 244.0), (72.0, 150.0, 194.0), (212.0, 48.0, 60.0), (250.0, 16.0, 20.0))
M_GLASSY = ((16.0, 206.0, 250.0), (62.0, 138.0, 190.0), (216.0, 38.0, 50.0), (252.0, 12.0, 16.0))
M_OFFAL = ((30.0, 218.0, 232.0), (100.0, 158.0, 184.0), (176.0, 80.0, 100.0), (230.0, 34.0, 46.0))

_ORACLE = {
 "frl_blood_augur": _R("frl_blood_augur", "Blood Augury", "crackle",
    (404.0, 920.0, 1.0, 1.28, 0.8), [0.005, 0.930, 0.075, 0.985],
    "A poured offering dried to a crackle glaze: the network of cracks is the reading. A FRACTURED RELICS finish.",
    eargs=dict(plate=12.0, contrast=1.65), hue_cell=6.0, mats=M_OFFAL, val=0.215,
    satboost=1.18, burnish=1.10, micro=1.5, kw=dict(gray=0.14, flash=(0.32, 0.74))),
 "frl_planchette": _R("frl_planchette", "Planchette Path", "planchette",
    (400.0, 928.0, 1.0, 1.24, 2.1), [0.075, 0.005, 0.145, 0.050],
    "A spirit board worn by decades of travel, the letter blocks still there under the arcs the planchette polished. A FRACTURED RELICS finish.",
    eargs=dict(cell=9.6), hue_cell=6.5, mats=M_BOARD, val=0.225, satboost=1.06,
    burnish=0.85, kw=dict(gray=0.22)),
 "frl_casting_bones": _R("frl_casting_bones", "Casting Bones", "knuckle",
    (398.0, 924.0, 0.98, 1.20, 4.9), [0.135, 0.065, 0.205, 0.110],
    "Knucklebones thrown and settled where they fell, packed tight, each knobbed at both ends. A FRACTURED RELICS finish.",
    eargs=dict(pitch=11.8), hue_cell=6.5, mats=M_BOARD, val=0.235, satboost=0.52,
    burnish=0.95, kw=dict(gray=0.46)),
 "frl_tasseomancy": _R("frl_tasseomancy", "Tasseomancy", "tealeaf",
    (402.0, 918.0, 1.0, 1.22, 3.2), [0.200, 0.130, 0.270, 0.175],
    "Leaf fragments left in the cup, settled into the bands the last swirl of tea drew them into. A FRACTURED RELICS finish.",
    eargs=dict(ring=17.0, contrast=1.70), hue_cell=6.0, mats=M_BOARD, val=0.175,
    satboost=1.02, burnish=1.15, micro=1.6, kw=dict(gray=0.24)),
 "frl_palm_line": _R("frl_palm_line", "Palm Reading", "dermato",
    (396.0, 932.0, 1.0, 1.22, 5.5), [0.300, 0.230, 0.370, 0.275],
    "Friction ridges flowing around the loops they grew into, broken where the major lines cross. A FRACTURED RELICS finish.",
    eargs=dict(ridge=3.1), hue_cell=5.5, mats=M_OFFAL, val=0.215, satboost=1.04,
    burnish=1.00, kw=dict(gray=0.24)),
 "frl_astrolabe": _R("frl_astrolabe", "Astrolabe Plate", "astrolabe",
    (394.0, 936.0, 1.0, 1.26, 1.5), [0.380, 0.310, 0.450, 0.355],
    "Almucantar arcs and azimuth rays engraved into brass, a star pointer punched at the crossings. A FRACTURED RELICS finish.",
    eargs=dict(arc=13.5), hue_cell=6.0, mats=M_BRASS, val=0.225, satboost=1.16,
    burnish=0.80, kw=dict(gray=0.14, flash=(0.34, 0.76))),
 "frl_ceromancy": _R("frl_ceromancy", "Ceromancy", "ceromancy",
    (392.0, 940.0, 1.0, 1.24, 2.8), [0.47, 0.4, 0.54, 0.445],
    "Molten wax dropped into cold water, set as thin lobed sheets, holed and rimmed where it tore. A FRACTURED RELICS finish.",
    eargs=dict(sheet=15.0), hue_cell=6.5, mats=M_GLASSY, val=0.225, satboost=1.10,
    burnish=0.95, kw=dict(gray=0.18)),
 "frl_black_mirror": _R("frl_black_mirror", "Black Mirror", "obsidian",
    (388.0, 948.0, 1.0, 1.28, 4.3), [0.560, 0.490, 0.630, 0.535],
    "A scrying glass knapped from obsidian, conchoidal shells rippling from every strike. A FRACTURED RELICS finish.",
    eargs=dict(shell=8.6), hue_cell=6.0, mats=M_GLASSY, val=0.195, satboost=1.22,
    burnish=0.85, kw=dict(gray=0.10, flash=(0.30, 0.72))),
 "frl_ink_scry": _R("frl_ink_scry", "Ink Scrying", "inkplume",
    (386.0, 950.0, 1.0, 1.26, 5.9), [0.660, 0.590, 0.730, 0.635],
    "A drop of ink opening in water: sheets of filament pulled into each other, thinning to smoke. A FRACTURED RELICS finish.",
    eargs=dict(filament=3.6), hue_cell=5.5, mats=M_GLASSY, val=0.205, satboost=1.20,
    burnish=1.00, kw=dict(gray=0.12)),
 "frl_haruspex": _R("frl_haruspex", "Haruspex", "liver",
    (406.0, 916.0, 1.0, 1.26, 0.4), [0.930, 0.860, 0.995, 0.905],
    "The reading surface itself: lobes divided by their fissures, the vessel tree branching across every one. A FRACTURED RELICS finish.",
    eargs=dict(lobe=17.0, contrast=1.65), hue_cell=6.0, mats=M_OFFAL, val=0.205,
    satboost=1.14, burnish=1.15, micro=1.7, kw=dict(gray=0.16, flash=(0.32, 0.76))),
}


# material palettes for the alchemist's leavings
M_SLAG = ((18.0, 222.0, 246.0), (70.0, 158.0, 200.0), (198.0, 60.0, 76.0), (242.0, 22.0, 30.0))
M_MINERAL = ((22.0, 216.0, 244.0), (78.0, 152.0, 196.0), (206.0, 50.0, 64.0), (246.0, 18.0, 26.0))
M_PAPER = ((26.0, 240.0, 232.0), (84.0, 198.0, 210.0), (150.0, 104.0, 128.0), (216.0, 48.0, 64.0))
M_METAL = ((16.0, 208.0, 248.0), (64.0, 142.0, 192.0), (218.0, 40.0, 52.0), (252.0, 12.0, 18.0))

_ALEMBIC = {
 "frl_athanor_slag": _R("frl_athanor_slag", "Athanor Slag", "slag",
    (402.0, 924.0, 1.0, 1.26, 1.6), [0.070, 0.000, 0.140, 0.045],
    "The glass that froze in the furnace mouth, gas vesicles caught mid-rise along a flow still moving. A FRACTURED RELICS finish.",
    eargs=dict(vesicle=9.0), hue_cell=6.0, mats=M_SLAG, val=0.215, satboost=1.16,
    burnish=0.90, kw=dict(gray=0.14, flash=(0.32, 0.74))),
 "frl_sulfur_crust": _R("frl_sulfur_crust", "Sulfur Crust", "botryoid",
    (398.0, 928.0, 1.0, 1.24, 3.1), [0.140, 0.070, 0.210, 0.115],
    "Botryoidal sulfur: spheroids budded on spheroids, needles sublimed out of the gaps between. A FRACTURED RELICS finish.",
    eargs=dict(nodule=11.0), hue_cell=6.5, mats=M_MINERAL, val=0.235, satboost=1.10,
    burnish=0.95, kw=dict(gray=0.16)),
 "frl_herbarium": _R("frl_herbarium", "Herbarium Press", "venation",
    (404.0, 918.0, 1.0, 1.20, 4.7), [0.185, 0.115, 0.255, 0.16],
    "A specimen flattened onto rag paper a century ago: midrib, secondaries, reticulation, foxing. A FRACTURED RELICS finish.",
    eargs=dict(blade=15.0), hue_cell=6.0, mats=M_PAPER, val=0.235, satboost=0.96,
    burnish=0.95, kw=dict(gray=0.26)),
 "frl_transmutation": _R("frl_transmutation", "Transmutation Seal", "ringtext",
    (396.0, 934.0, 1.0, 1.26, 0.9), [0.3, 0.23, 0.37, 0.275],
    "Concentric bands of ring text with the figure struck across them, cut sharp into the plate. A FRACTURED RELICS finish.",
    eargs=dict(ring=11.0), hue_cell=6.0, mats=M_METAL, val=0.215, satboost=0.6,
    burnish=0.80, kw=dict(gray=0.38, flash=(0.34, 0.76))),
 "frl_verdigris": _R("frl_verdigris", "Verdigris Bloom", "bloomcells",
    (392.0, 940.0, 1.0, 1.24, 5.3), [0.360, 0.290, 0.430, 0.335],
    "Copper corrosion spreading as colonies, each a crusted disc that grew until it met the next. A FRACTURED RELICS finish.",
    eargs=dict(colony=10.5), hue_cell=6.5, mats=M_MINERAL, val=0.215, satboost=1.08,
    burnish=0.95, macro=("domains", dict(cells=5, salt=6607)), kw=dict(gray=0.22)),
 "frl_apothecary_crust": _R("frl_apothecary_crust", "Apothecary Crust", "tincture",
    (390.0, 942.0, 1.0, 1.22, 2.3), [0.415, 0.345, 0.485, 0.39],
    "A bottle left to evaporate: every level it stopped at is a ring, and the salt crystallised on each. A FRACTURED RELICS finish.",
    eargs=dict(ring=16.0), hue_cell=6.0, mats=M_MINERAL, val=0.225, satboost=1.06,
    burnish=1.00, kw=dict(gray=0.20)),
 "frl_vitriol_etch": _R("frl_vitriol_etch", "Vitriol Etch", "etchpit",
    (388.0, 946.0, 1.0, 1.26, 4.0), [0.545, 0.475, 0.615, 0.52],
    "Acid on metal: pits that ate outward along the grain, each fringed by the dendrites the reaction left. A FRACTURED RELICS finish.",
    eargs=dict(pit=8.4), hue_cell=5.5, mats=M_METAL, val=0.205, satboost=1.12,
    burnish=0.95, kw=dict(gray=0.18)),
 "frl_quicksilver": _R("frl_quicksilver", "Quicksilver", "mercury",
    (386.0, 950.0, 1.0, 1.28, 5.7), [0.600, 0.530, 0.670, 0.575],
    "Beads that ran together and stopped: fat lenses joined by necks, tarnish creeping over the stillest. A FRACTURED RELICS finish.",
    eargs=dict(bead=10.0), hue_cell=6.0, mats=M_METAL, val=0.215, satboost=0.62,
    burnish=0.85, kw=dict(gray=0.36, flash=(0.30, 0.72))),
 "frl_philosopher": _R("frl_philosopher", "Philosopher's Stone", "gasket",
    (400.0, 930.0, 1.0, 1.30, 2.6), [0.860, 0.790, 0.930, 0.835],
    "The impossible packing: discs of every size nested into the gaps of the discs before them, each cut as a gem. A FRACTURED RELICS finish.",
    eargs=dict(big=27.0), hue_cell=6.5, mats=M_MINERAL, val=0.225, satboost=1.24,
    burnish=0.90, kw=dict(gray=0.10, flash=(0.34, 0.78))),
 "frl_cinnabar": _R("frl_cinnabar", "Cinnabar Druse", "druse",
    (406.0, 914.0, 1.0, 1.30, 0.2), [0.990, 0.920, 0.060, 0.965],
    "A vug lined with crystal: every termination a facetted point, all crowded into the same small space. A FRACTURED RELICS finish.",
    eargs=dict(crystal=9.6), hue_cell=6.0, mats=M_MINERAL, val=0.205, satboost=1.26,
    burnish=0.90, kw=dict(gray=0.08, flash=(0.32, 0.76))),
}

GROUPS = {
    "⚗ THE ALEMBIC": _ALEMBIC,
    "🜏 THE ORACLE": _ORACLE,
    "⚱ THE BARROW": _BARROW,
    "🦴 THE BEAST": _BEAST,
    "⛧ THE BINDING": _BINDING,
}

KIT = kit.RelicKit(ENGINES, GROUPS, "fractured-relics-2026")


def install_into_engine(mono_reg, base_reg=None):
    return KIT.install_into_engine(mono_reg, base_reg)
