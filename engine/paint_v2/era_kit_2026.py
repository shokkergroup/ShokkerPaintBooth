# -*- coding: utf-8 -*-
"""🕰 ERA KIT (2026-08-31) — primitives for the decade shelves and the split of
TACTICAL & CYBERPUNK.

Owner: flip ★ OPTIC LAB to the 1970s, Marble & Onyx to the 1980s ("Bad and Rad"),
add a 1990s shelf, and split TACTICAL & CYBERPUNK into two 60-finish categories.
*"Apply the best spec rules possible across the board to make totally unique
finishes. DO NOT just automatically make them all Fractured styles... SOME
finishes should lean flat, chalky, glossy, wet, GLITTERY — ALL looks and blends
welcome."*

Everything already in the catalog's kits is re-exported rather than rewritten —
worley, curl, filaments, dendrites, cracks, plates, craters, dunes, bands,
honeycomb, polygons, the tartan sett, the zellij star tiling, ikat, wax resist,
guilloche, intaglio, microtext, moire, knurl, facets, bricks, shred. What is
here is the fourteen things those five shelves need and no existing kit has.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

from engine.expansions.fractured_flames_kit_2026 import (      # noqa: F401
    GEN, WORK, fbm, n01, pct, rng, upscale, cell_mean, worley, curl, filaments,
    dla, percolate, spall, anneal_crack, kh_braid, rt_fingers, sparks, eden,
    wrinkle, _h1,
)
from engine.expansions.fractured_cosmos_kit_2026 import (      # noqa: F401
    craters, dunes, polygons, honeycomb, bands, crinkle, starfield, glyphs, hull,
)
from engine.expansions.world_of_color_kit_2026 import (        # noqa: F401
    sett, stars, ikat, resist,
)
from engine.expansions.money_shokk_kit_2026 import (           # noqa: F401
    guilloche, intaglio, microtext, moire, knurl, facets, bricks, shred, threads,
)

_TAU = 6.283185307179586


# ════════════════════════════════════════════════════════════════════════════
# SCREENS AND SIGNALS
# ════════════════════════════════════════════════════════════════════════════

def scanline(shape, seed, lines=190.0, triad=3.0, bloom=1.0, roll=0.22, jitter=0.5):
    """A CRT: phosphor triads behind horizontal scan lines, with bloom.

    The shadow mask is a vertical RGB triad at a much finer pitch than the scan
    lines, so the two beat against each other — which is exactly what makes an
    arcade cabinet photograph the way it does. `roll` adds the slow brightness
    band of an out-of-sync refresh.
    """
    h, w = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    scan = 0.5 + 0.5 * np.cos(yy * (_TAU * lines / max(h, 1)))
    scan = np.power(np.clip(scan, 0, 1), 0.7)
    tri = 0.5 + 0.5 * np.cos(xx * (_TAU * lines * float(triad) / max(w, 1)))
    band = 0.5 + 0.5 * np.sin(yy * (_TAU * float(roll) / max(h, 1)) + 1.1)
    sig = fbm((h, w), seed + 5, octaves=(32, 64, 128, 256), weights=(1.0, .8, .6, .4))
    out = (0.42 + 0.58 * scan) * (0.55 + 0.45 * tri) * (0.70 + 0.30 * band)
    out = out * (0.72 + 0.56 * sig)
    if bloom and cv2 is not None:
        hot = np.clip(out - 0.62, 0, None)
        out = out + cv2.GaussianBlur(hot, (0, 0), 3.0 * w / 2048.0) * 2.2 * float(bloom)
    if jitter:
        off = ((_h1(np.floor(yy / max(h / lines, 1)).astype(np.int64), 71) - 0.5)
               * float(jitter) * 6.0 * w / 2048.0)
        out = np.take_along_axis(out, np.clip(
            (xx + off).astype(np.int32), 0, w - 1), axis=1)
    return pct(out)


def pixels(shape, seed, cell=9.0, levels=9, dither=0.35, sprite=0.0):
    """Pixel art: a hard grid quantised to a few levels, optionally with sprite
    blocks. `cell` is in 2048-space so the blocks stay in the visible window."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    C = max(3.0, float(cell) * sc)
    # The source field must vary at the CELL pitch or neighbouring cells land
    # on the same level and merge into blocks far bigger than `cell`.
    f = fbm((h, w), seed, octaves=(32, 64, 128, 256), weights=(1.0, .85, .7, .5))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    gy, gx = (yy / C).astype(np.int64), (xx / C).astype(np.int64)
    key = gy * 8191 + gx
    v = cell_mean(f, key)
    if dither:
        v = np.clip(v + (_h1(key, 131) - 0.5) * float(dither), 0, 1)
    q = np.floor(v * float(levels)) / max(float(levels) - 1, 1)
    if sprite:
        blocks = (_h1(gy // 4 * 7919 + gx // 4, 211) < float(sprite)).astype(np.float32)
        q = np.clip(q * (0.55 + 0.45 * blocks) + blocks * 0.35, 0, 1)
    return pct(q)


def wireframe(shape, seed, rows=26, persp=1.7, horizon=0.42, glow=1.0, width=1.6):
    """The vector grid running to a horizon — the single most 1980s image there
    is. Row spacing compresses with perspective, so the frequency sweeps through
    the visible window instead of sitting at one pitch."""
    h, w = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = np.clip((yy / max(h - 1, 1) - float(horizon)) / max(1.0 - float(horizon), 1e-3), 1e-3, 1)
    depth = np.power(v, float(persp))
    lat = 0.5 + 0.5 * np.cos(depth * _TAU * float(rows))
    u = (xx / max(w - 1, 1) - 0.5) / np.maximum(depth, 0.03)
    lon = 0.5 + 0.5 * np.cos(u * _TAU * 7.0)
    lw = float(width) * w / 2048.0
    grid = np.maximum(np.power(lat, 40.0 / max(lw, 0.4)), np.power(lon, 30.0 / max(lw, 0.4)))
    # An empty sky is a dead third of the canvas (coverage 0.62). Fill it with
    # the other thing every 1980s grid render had in it: a starfield and a
    # scanline haze.
    sky = np.clip(1.0 - yy / max(h * float(horizon), 1), 0, 1) ** 2
    stars_ = starfield((h, w), seed + 31, n=2200, mag=2.0, glow=1.1) * (sky > 0.02)
    haze = (0.5 + 0.5 * np.cos(yy * (_TAU * 150.0 / max(h, 1)))) * sky * 0.30
    out = np.clip(grid + sky * 0.22 + stars_ * 0.85 + haze, 0, 1)
    if glow and cv2 is not None:
        out = out + cv2.GaussianBlur(out, (0, 0), 2.4 * w / 2048.0) * 0.8 * float(glow)
    return pct(out)


def glitch(shape, seed, slices=54, shift=44.0, tear=0.30, block=0.22, field=None):
    """Datamosh: whole rows displaced, blocks dropped, channels torn apart. The
    1990s corrupted-JPEG look and the CYBERPUNK signal-failure look are the same
    artefact, so one primitive serves both."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    base = field if field is not None else fbm(
        (h, w), seed, octaves=(16, 32, 64, 128, 256), weights=(1.0, .8, .65, .5, .35))
    base = pct(np.asarray(base, np.float32))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row = np.floor(yy / max(h / float(slices), 1)).astype(np.int64)
    amt = (_h1(row, 97) - 0.5) * 2.0
    hit = (_h1(row, 151) < float(tear)).astype(np.float32)
    off = (amt * hit * float(shift) * sc).astype(np.int32)
    out = np.take_along_axis(base, np.clip(xx.astype(np.int32) + off, 0, w - 1), axis=1)
    if block:
        bs = max(4, int(26 * sc))
        by = (yy / bs).astype(np.int64) * 6151 + (xx / bs).astype(np.int64)
        drop = (_h1(by, 223) < float(block)).astype(np.float32)
        out = out * (1.0 - drop) + _h1(by, 307) * drop
    return pct(out)


def holo(shape, seed, rings=340.0, orders=3.0, warp=90.0, sharp=1.0):
    """Thin-film interference: the order of the fringe walks with thickness, so
    the pattern is a set of nested bands whose SPACING varies. Holographic CD,
    dichroic film, oil slick, hologram sticker — all the same physics."""
    h, w = int(shape[0]), int(shape[1])
    t = fbm((h, w), seed, octaves=(8, 16, 32, 64), weights=(1.0, .75, .5, .3))
    if warp:
        t = t + (fbm((h, w), seed + 13, octaves=(4, 8, 16), weights=(1.0, .5, .3)) - 0.5) \
            * float(warp) / 255.0
    phase = t * float(rings)
    out = 0.5 + 0.5 * np.cos(_TAU * phase)
    for k in range(2, int(orders) + 1):
        out = np.maximum(out, (0.5 + 0.5 * np.cos(_TAU * phase * k)) * (1.0 / k))
    return pct(np.power(np.clip(out, 0, 1), float(sharp)))


# ════════════════════════════════════════════════════════════════════════════
# CLOTH, PILE AND HIDE
# ════════════════════════════════════════════════════════════════════════════

def shag(shape, seed, strands=5200, length=46, splay=0.9, lean=0.35):
    """Deep pile: long soft strands lying every which way with the tips catching
    light. Shag carpet, a velour tracksuit, a fun-fur — the 1970s in one field."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    f = filaments((h, w), seed, n=int(strands), length=int(length * sc) + 3,
                  wander=float(splay), width=1.2)
    if lean and cv2 is not None:
        k = max(3, int(7 * sc) | 1)
        kern = np.zeros((k, k), np.float32)
        cv2.line(kern, (0, k - 1), (k - 1, 0), 1.0, 1)
        f = np.maximum(f, cv2.filter2D(f, -1, kern / max(kern.sum(), 1)) * float(lean) * 2.2)
    tips = sparks((h, w), seed + 9, n=int(strands * 0.45), life=int(10 * sc) + 4,
                  g=0.1, spread=1.6, width=0.8)
    base = fbm((h, w), seed + 3, octaves=(64, 128, 256), weights=(1.0, .7, .45))
    return pct(np.clip(f * 0.72 + tips * 0.45 + base * 0.26, 0, None))


def tooled(shape, seed, cell=118.0, petals=6, stamp=0.55, bevel=1.0):
    """Western tooled leather: a repeating floral punch, beveled and backgrounded.
    Built as a field so the swivel-knife line and the beveled shoulder are one
    object, which is what makes tooling read as depth rather than as print."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    C = max(14.0, float(cell) * sc)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    wob = (fbm((h, w), seed + 7, octaves=(4, 8, 16), weights=(1.0, .5, .3)) - 0.5) * 14.0 * sc
    row = np.floor((yy + wob) / C)
    dx = np.mod(xx + wob + row * C * 0.5, C) - C * 0.5
    dy = np.mod(yy + wob, C) - C * 0.5
    rho = np.hypot(dx, dy) / (C * 0.5)
    phi = np.arctan2(dy, dx)
    rose = 0.55 + 0.45 * np.cos(float(petals) * phi + rho * 3.4)
    d = rho / np.maximum(rose, 0.15)
    cut = np.exp(-((d - 0.72) ** 2) / 0.0075)                 # the knife line
    shoulder = np.clip(1.0 - d, 0, 1) ** 1.6                   # the beveled lift
    ground = (_h1((row.astype(np.int64) * 8191
                   + np.floor((xx + wob) / C).astype(np.int64)), 173) * 0.30)
    out = np.clip(shoulder * float(bevel) + cut * float(stamp) + ground, 0, 1)
    grain = fbm((h, w), seed + 11, octaves=(128, 256, 512), weights=(1.0, .7, .45))
    return pct(out * (0.80 + 0.40 * grain))


def discs(shape, seed, n=2600, radius=15.0, tilt=0.75, facet=1.0):
    """A sequin wall or a mirror ball: overlapping discs, each tilted its own way
    so each returns light from a different angle. `facet` breaks the disc into
    the flat sub-planes a real mirror tile has."""
    h, w = int(shape[0]), int(shape[1])
    if cv2 is None:
        return np.zeros((h, w), np.float32)
    sc = w / 2048.0
    r = rng(seed)
    out = np.zeros((h, w), np.float32)
    R = max(2.0, radius * sc)
    for _ in range(int(n)):
        cx, cy = r.uniform(0, w), r.uniform(0, h)
        rr = R * r.uniform(0.72, 1.3)
        val = 0.18 + 0.82 * (r.random() ** (1.0 / max(tilt, 0.15)))
        cv2.circle(out, (int(cx), int(cy)), int(max(1, rr)), float(val), -1, cv2.LINE_AA)
        if facet and rr > 3:
            cv2.circle(out, (int(cx - rr * 0.28), int(cy - rr * 0.28)),
                       int(max(1, rr * 0.42)), float(min(1.0, val + 0.35 * facet)), -1, cv2.LINE_AA)
    edge = cv2.Laplacian(out, cv2.CV_32F)
    return pct(np.clip(out + np.abs(edge) * 0.30, 0, None))


def splatter(shape, seed, blobs=520, rmax=34.0, drips=0.45, spatter=1.0):
    """Thrown paint: fat blobs, satellite spatter and a few runs. The 1980s
    splatter tee and the 1990s paint-drip both live here."""
    h, w = int(shape[0]), int(shape[1])
    if cv2 is None:
        return np.zeros((h, w), np.float32)
    sc = w / 2048.0
    r = rng(seed)
    out = np.zeros((h, w), np.float32)
    for _ in range(int(blobs)):
        cx, cy = r.uniform(0, w), r.uniform(0, h)
        rr = max(1.5, rmax * sc * (r.random() ** 2.2))
        v = r.uniform(0.45, 1.0)
        cv2.circle(out, (int(cx), int(cy)), int(rr), float(v), -1, cv2.LINE_AA)
        if drips and r.random() < drips:
            ln = rr * r.uniform(2.0, 7.0)
            cv2.line(out, (int(cx), int(cy)), (int(cx), int(cy + ln)),
                     float(v * 0.8), max(1, int(rr * 0.5)), cv2.LINE_AA)
        for _s in range(int(6 * spatter)):
            a, d = r.uniform(0, _TAU), rr * r.uniform(1.4, 5.0)
            cv2.circle(out, (int(cx + np.cos(a) * d), int(cy + np.sin(a) * d)),
                       int(max(1, rr * 0.18)), float(v * 0.9), -1, cv2.LINE_AA)
    return pct(out)


def squiggle(shape, seed, n=420, length=120.0, amp=16.0, confetti=0.55, width=3.0):
    """Memphis-Milano: the squiggle, the confetti and the bacterio print. Loose
    hand-drawn strokes that wander, plus a scatter of hard little shapes."""
    h, w = int(shape[0]), int(shape[1])
    if cv2 is None:
        return np.zeros((h, w), np.float32)
    sc = w / 2048.0
    r = rng(seed)
    out = np.zeros((h, w), np.float32)
    for _ in range(int(n)):
        x, y = r.uniform(0, w), r.uniform(0, h)
        ang = r.uniform(0, _TAU)
        pts, ph = [], r.uniform(0, _TAU)
        steps = max(6, int(length * sc / 6))
        for s in range(steps):
            ang += np.sin(ph + s * 0.55) * 0.42
            x += np.cos(ang) * 6.0 * sc
            y += np.sin(ang) * 6.0 * sc + np.sin(ph + s * 0.9) * amp * sc * 0.06
            pts.append((int(x), int(y)))
        cv2.polylines(out, [np.asarray(pts, np.int32).reshape(-1, 1, 2)], False,
                      float(r.uniform(0.5, 1.0)), int(max(1, width * sc)), cv2.LINE_AA)
    if confetti:
        for _ in range(int(900 * confetti)):
            cx, cy = int(r.uniform(0, w)), int(r.uniform(0, h))
            s = int(max(2, 9 * sc * r.uniform(0.5, 1.6)))
            v = float(r.uniform(0.55, 1.0))
            if r.random() < 0.5:
                cv2.rectangle(out, (cx, cy), (cx + s, cy + s), v, -1)
            else:
                cv2.circle(out, (cx, cy), s // 2 + 1, v, -1, cv2.LINE_AA)
    return pct(out)


# ════════════════════════════════════════════════════════════════════════════
# CONCEALMENT
# ════════════════════════════════════════════════════════════════════════════

def camo(shape, seed, patches=5, blob=150.0, roughness=1.0, edge=0.0):
    """Organic disruptive camouflage: overlapping irregular patches at several
    scales, hard-edged. Returns a LEVEL field (0..1 in `patches` steps) so the
    caller can map each level to its own colour, which is how camo is printed."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    lv = np.zeros((h, w), np.float32)
    for i in range(int(patches)):
        oct0 = max(3, int(2048.0 / max(blob * sc * (0.62 ** i), 8.0)))
        f = fbm((h, w), seed + 17 * i,
                octaves=(oct0, oct0 * 2, oct0 * 4),
                weights=(1.0, 0.55 * roughness, 0.3 * roughness))
        thr = float(np.percentile(f, 100.0 - 62.0 / (i + 1.35)))
        lv = np.maximum(lv, (f > thr).astype(np.float32) * ((i + 1.0) / patches))
    if edge and cv2 is not None:
        e = np.abs(cv2.Laplacian(lv, cv2.CV_32F))
        lv = np.clip(lv + (e > 0).astype(np.float32) * float(edge), 0, 1)
    return lv


def digicam(shape, seed, cell=7.0, patches=4, cluster=2.2):
    """Pixellated camouflage (MARPAT, CADPAT, AOR). Not a blurred blob field
    squared off — real digital camo is built from clustered squares at two
    scales, which is what breaks up an outline at BOTH distances."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    C = max(3.0, float(cell) * sc)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lv = np.zeros((h, w), np.float32)
    for i in range(int(patches)):
        s = C * (float(cluster) ** (i % 2))
        gy, gx = (yy / s).astype(np.int64), (xx / s).astype(np.int64)
        f = cell_mean(fbm((h, w), seed + 29 * i, octaves=(48, 96, 192),
                          weights=(1.0, .7, .45)), gy * 8191 + gx)
        thr = float(np.percentile(f, 100.0 - 58.0 / (i + 1.3)))
        lv = np.maximum(lv, (f > thr).astype(np.float32) * ((i + 1.0) / patches))
    return lv


def topo(shape, seed, lines=118.0, warp=1.0, index=5, width=1.4):
    """A contour map: equal-interval lines with a heavier index contour every
    n-th. Reads as terrain, as a depth chart, or as a heat map."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    f = fbm((h, w), seed, octaves=(4, 8, 16, 32, 64), weights=(1.0, .8, .6, .4, .25))
    if warp:
        f = f + (fbm((h, w), seed + 5, octaves=(8, 16, 32), weights=(1.0, .6, .3)) - 0.5) * 0.16 * warp
    ph = np.mod(pct(f) * float(lines), 1.0)
    d = np.minimum(ph, 1.0 - ph)
    line = np.exp(-(d ** 2) / (2.0 * (0.055 * float(width)) ** 2))
    band = np.floor(pct(f) * float(lines)).astype(np.int64)
    idx = (np.mod(band, int(index)) == 0).astype(np.float32)
    return pct(np.clip(line * (0.62 + 0.38 * idx) + pct(f) * 0.18, 0, None))


def scales(shape, seed, cell=26.0, rows=1.0, keel=0.55, sheen=1.0):
    """Fish scale / snake belly / chainmail: overlapping lapped plates in offset
    courses, each with a lit leading edge."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    C = max(5.0, float(cell) * sc)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row = np.floor(yy / (C * float(rows)))
    dx = np.mod(xx + row * C * 0.5, C) - C * 0.5
    dy = np.mod(yy, C * float(rows)) - C * float(rows) * 0.5
    d = np.hypot(dx / (C * 0.5), dy / (C * float(rows) * 0.62))
    body = np.clip(1.0 - d, 0, 1) ** 0.7
    lip = np.exp(-((d - 0.92) ** 2) / 0.008) * float(keel)
    out = np.clip(body * (0.55 + 0.45 * sheen) + lip, 0, 1)
    g = fbm((h, w), seed + 3, octaves=(128, 256, 512), weights=(1.0, .7, .4))
    return pct(out * (0.82 + 0.36 * g))
