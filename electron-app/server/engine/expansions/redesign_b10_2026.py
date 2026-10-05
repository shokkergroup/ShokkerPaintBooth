# -*- coding: utf-8 -*-
"""REDESIGN BATCH 10 (2026-06-10) — owner: "designs are LAZY, break out of the box,
50-100x better, truly UNIQUE across the board." Ten finishes/patterns, ten totally
different visual languages, NO shared motif. Low-level helpers only (noise, ramps,
blur, windowed splats); every MOTIF is bespoke. Colored with engine/color_science.
All vectorized + windowed; <=2s at 2048. Each design renders at (h,w); the engine
calls at a 1024 work grid and upscales.

Designs:
  butterfly_morpho     iridescent overlapping wing-scale shingles (structural blue)
  moth_luna            luna-moth wing: jade membrane + eyespot ocelli + fur + piping
  fable_comet_parade   prismatic meteor streaks, blown-out heads, chromatic tails
  fable_magnetite_flow sharp ferrofluid Rosensweig spikes (NOT blobs)
  lfr_liberty_filigree engraved interwoven scrollwork + beadwork (pattern)
  lfr_freedom_forge    Damascus folded/watered pattern-welded steel
  lfr_rockets_red_glare layered multi-type fireworks (chrysanthemum/willow/spark)
  lfr_eagle_crest      heraldic layered feather plumage with fine barbs (pattern)
  lfr_constellation_field dense star cartography, thousands of micro stars (pattern)
  lfr_distressed_flag  weathered torn battle-flag textile weave (pattern)
"""
import numpy as np
import cv2

from engine.color_science import oklch_ramp, interference_palette, candy_absorb


# ---------------------------------------------------------------- low-level helpers
def _rng(seed, off=0):
    return np.random.default_rng((int(seed) ^ (0x9E3779B1 + off * 0x85EBCA77)) & 0x7FFFFFFF)


def _coords(h, w):
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    return yy, xx


def _noise(h, w, seed, scales):
    """Sum of upsampled white-noise octaves, normalized 0..1."""
    out = np.zeros((h, w), np.float32)
    wsum = 0.0
    rng = _rng(seed, 7)
    for i, s in enumerate(scales):
        gh, gw = max(2, int(h / s)), max(2, int(w / s))
        g = rng.random((gh, gw)).astype(np.float32)
        out += cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC) * (1.0 / (i + 1))
        wsum += 1.0 / (i + 1)
    out /= max(wsum, 1e-6)
    out -= out.min()
    return (out / max(out.max(), 1e-6)).astype(np.float32)


def _warp(yy, xx, h, w, seed, amp):
    wx = (_noise(h, w, seed ^ 0x1111, (max(8, w // 12), max(20, w // 5))) - 0.5) * amp
    wy = (_noise(h, w, seed ^ 0x2222, (max(8, h // 12), max(20, h // 5))) - 0.5) * amp
    return yy + wy, xx + wx


def _splat_points(h, w, seed, n, value_fn, rad):
    """Windowed accumulate of n splats; value_fn(dy,dx,rng)->local field added in a
    (2*rad+1) window. Vectorized per-splat, capped window — no full-canvas per point."""
    acc = np.zeros((h, w), np.float32)
    rng = _rng(seed, 3)
    cys = rng.uniform(0, h, n); cxs = rng.uniform(0, w, n)
    r = int(rad)
    yy0, xx0 = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    for i in range(n):
        cy, cx = float(cys[i]), float(cxs[i])
        iy, ix = int(cy), int(cx)
        y0, y1 = max(0, iy - r), min(h, iy + r + 1)
        x0, x1 = max(0, ix - r), min(w, ix + r + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        dy = yy0[(y0 - iy + r):(y1 - iy + r), (x0 - ix + r):(x1 - ix + r)]
        dx = xx0[(y0 - iy + r):(y1 - iy + r), (x0 - ix + r):(x1 - ix + r)]
        loc = value_fn(dy, dx, rng, i)
        np.maximum(acc[y0:y1, x0:x1], loc, out=acc[y0:y1, x0:x1])
    return acc


def _sr(h, w):
    return max(h, w) / 1024.0


def _microtex(h, w, s):
    """Fine all-over tooth (~2-4px) so no region is left flat/empty (coverage rule)."""
    return _noise(h, w, (s ^ 0x6C71), (2, 4))


# ================================================================ 1. BUTTERFLY MORPHO
def _morpho_fields(h, w, s):
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    # curved scale rows via gentle domain warp of a rotated axis
    a = _rng(s, 1).uniform(0, np.pi)
    wy, wx = _warp(yy, xx, h, w, s, 26 * sr)
    u = (wx * np.cos(a) + wy * np.sin(a))
    v = (-wx * np.sin(a) + wy * np.cos(a))
    row_p = 13.0 * sr          # scale row pitch (~13px work -> ~26px @2048)
    col_p = 9.0 * sr           # scale width along row
    ru = u / row_p
    rowi = np.floor(ru)
    # brick offset every other row
    vv = v / col_p + (rowi % 2.0) * 0.5
    fu = ru - rowi
    fv = vv - np.floor(vv)
    # scale shingle: rounded fan, brighter ridge toward the overlapping (low fu) edge
    scale = (np.clip(1.0 - ((fv - 0.5) * 2.0) ** 2, 0, 1) ** 0.7) * np.clip(1.0 - fu * 0.85, 0, 1)
    ridge = np.clip(1.0 - fu / 0.18, 0, 1) ** 2          # bright leading ridge of each scale
    # thickness field for thin-film travel (per scale + slow drift)
    thick = (0.5 + 0.5 * np.sin(rowi * 0.7 + np.floor(vv) * 1.3)) * 0.6 + 0.4 * _noise(h, w, s ^ 0x55, (60 * sr, 160 * sr))
    return scale.astype(np.float32), ridge.astype(np.float32), np.clip(thick, 0, 1).astype(np.float32), rowi, vv


def _butterfly_morpho_paint(h, w, s):
    scale, ridge, thick, rowi, vv = _morpho_fields(h, w, s)
    # structural blue: cobalt->violet->teal thin-film by thickness
    film = interference_palette(thick, 2.4, 0.78, base_srgb=np.float32([0.05, 0.10, 0.22]))[..., :3]
    blue = oklch_ramp([(0.07, 0.14, 0.42), (0.20, 0.40, 0.86), (0.50, 0.68, 1.0)], thick, flatten_lightness=0.2)
    body = 0.5 * film + 0.5 * blue + 0.10   # brighter so it reads on the car, not near-black
    # dark branching wing-vein armature (sparse thick web)
    veins = _splat_points(h, w, (s ^ 0x7A1), int(28 * _sr(h, w) ** 2 + 8),
                          lambda dy, dx, rng, i: np.exp(-(dy * dy + dx * dx) / (2 * (rng.uniform(2, 5)) ** 2)),
                          rad=int(7 * _sr(h, w)) + 2)
    vmask = np.clip(veins * 1.4, 0, 1)
    eff = body * (0.6 + 0.4 * scale[..., None])   # scale gaps stay lit, not black
    # white-hot ridge glints on rare scales
    glint = (ridge * (_noise(h, w, s ^ 0x33, (3, 7)) > 0.82)).astype(np.float32)
    eff = eff + glint[..., None] * np.float32([0.9, 0.95, 1.0]) * 0.8
    eff = eff * (1.0 - 0.7 * vmask[..., None])           # dark veins cut through
    eff = eff + (1.0 - scale)[..., None] * np.float32([0.015, 0.02, 0.05])   # deep chitin gaps
    eff = eff * (1.0 + 0.60 * (_microtex(h, w, s)[..., None] - 0.5))   # all-over scale tooth (coverage, mean-preserving)
    return np.clip(eff, 0, 1).astype(np.float32)


def _butterfly_morpho_spec(h, w, s):
    scale, ridge, thick, rowi, vv = _morpho_fields(h, w, s)
    glint = (ridge * (_noise(h, w, s ^ 0x33, (3, 7)) > 0.82)).astype(np.float32)
    M = np.clip(24 + 226 * ridge * scale + 60 * glint, 0, 255)     # mirror on scale ridges
    R = np.clip(150 - 70 * scale + 50 * (1 - ridge), 15, 255)      # membrane satin, gaps rough
    Cc = np.clip(40 + 150 * thick * scale + 30 * glint, 16, 255)   # thin-film wet sheen
    return M.astype(np.float32), R.astype(np.float32), Cc.astype(np.float32)


# ================================================================ 2. MOTH LUNA
def _luna_fields(h, w, s):
    sr = _sr(h, w); yy, xx = _coords(h, w)
    rng = _rng(s, 2)
    by, bx = h * rng.uniform(0.42, 0.58), w * rng.uniform(0.42, 0.58)
    dy, dx = yy - by, xx - bx
    rad = np.sqrt(dy * dy + dx * dx) + 1e-3
    ang = np.arctan2(dy, dx)
    radn = rad / (0.60 * max(h, w))
    wob = (_noise(h, w, s ^ 0x9, (6 * sr, 16 * sr)) - 0.5) * 1.8
    # DENSE fine red radial veins fanning from the body across the whole wing
    nv = 52.0
    phase = (ang * nv / (2 * np.pi) + wob) % 1.0
    veins = np.clip(1.0 - np.abs(phase - 0.5) * 2.0 / 0.16, 0, 1) ** 1.5
    veins = veins * np.clip(radn * 1.5, 0, 1)
    # fine concentric ribbing — full-coverage cross-striation texture
    rib = (0.5 + 0.5 * np.cos(rad / (3.0 * sr) * 2 * np.pi + wob * 2.5)) ** 2
    macro = _noise(h, w, s ^ 0xA, (40 * sr, 110 * sr))
    # eyespots: pale center + orange ring + dark outer ring
    spots = np.zeros((h, w), np.float32); ring1 = np.zeros((h, w), np.float32); ring2 = np.zeros((h, w), np.float32)
    for _ in range(6):
        cy, cx = rng.uniform(0.18, 0.82) * h, rng.uniform(0.18, 0.82) * w
        rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        R0 = rng.uniform(16, 26) * sr
        spots = np.maximum(spots, np.clip(1 - rr / (R0 * 0.42), 0, 1))
        ring1 = np.maximum(ring1, np.exp(-((rr - R0 * 0.62) / (R0 * 0.12)) ** 2))
        ring2 = np.maximum(ring2, np.exp(-((rr - R0 * 0.92) / (R0 * 0.10)) ** 2))
    margin = np.clip((radn - 0.80) / 0.15, 0, 1)            # dark maroon wing edge
    return (veins.astype(np.float32), rib.astype(np.float32), macro,
            spots.astype(np.float32), ring1.astype(np.float32), ring2.astype(np.float32), margin.astype(np.float32))


def _moth_luna_paint(h, w, s):
    veins, rib, macro, spots, ring1, ring2, margin = _luna_fields(h, w, s)
    t = np.clip(0.42 + 0.32 * macro + 0.18 * rib, 0, 1)
    jade = oklch_ramp([(0.34, 0.54, 0.34), (0.56, 0.80, 0.48), (0.74, 0.90, 0.60)], t, flatten_lightness=0.3)
    eff = jade * (0.88 + 0.16 * rib[..., None])
    eff = eff * (1 - veins[..., None] * 0.82) + np.float32([0.54, 0.10, 0.14]) * veins[..., None] * 0.82
    eff = eff * (1 - spots[..., None]) + np.float32([0.96, 0.74, 0.18]) * spots[..., None]   # gold center
    eff = eff * (1 - ring1[..., None]) + np.float32([0.92, 0.34, 0.05]) * ring1[..., None]   # orange ring
    eff = eff * (1 - ring2[..., None]) + np.float32([0.12, 0.03, 0.04]) * ring2[..., None]   # dark ring
    eff = eff * (1 - margin[..., None]) + np.float32([0.34, 0.06, 0.10]) * margin[..., None]  # margin
    eff = eff * (1.0 + 0.52 * (_microtex(h, w, s)[..., None] - 0.5))   # fine membrane tooth (coverage, mean-preserving)
    return np.clip(eff, 0, 1).astype(np.float32)


def _moth_luna_spec(h, w, s):
    veins, rib, macro, spots, ring1, ring2, margin = _luna_fields(h, w, s)
    M = np.clip(22 + 150 * ring1 + 120 * veins + 60 * spots, 0, 255)
    R = np.clip(184 - 70 * rib - 40 * spots - 30 * veins, 15, 255)
    Cc = np.clip(34 + 150 * spots + 50 * ring1 + 30 * macro, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), Cc.astype(np.float32)


# ================================================================ 3. FABLE COMET PARADE
def _comet_fields(h, w, s):
    sr = _sr(h, w); yy, xx = _coords(h, w)
    rng = _rng(s, 3)
    # DENSE starfield (thousands, magnitude-varied) — full coverage
    imp = np.zeros((h, w), np.float32)
    nst = int(15000 * sr * sr)
    ys = rng.integers(0, h, nst); xs = rng.integers(0, w, nst)
    np.maximum.at(imp, (ys, xs), (rng.random(nst) ** 3.2).astype(np.float32))
    stars = np.clip(cv2.GaussianBlur(imp, (0, 0), 0.6 * sr) * 3.0, 0, 1)
    # milky-way nebula band: bright warped star-cloud sweeping the frame
    a = rng.uniform(0, np.pi)
    band = (xx * np.cos(a) + yy * np.sin(a)) / max(h, w) + (_noise(h, w, s ^ 0xB, (50 * sr, 130 * sr)) - 0.5) * 0.55
    mw = np.exp(-((band - rng.uniform(0.35, 0.65)) / 0.15) ** 2)
    nebula = (mw * (0.45 + 0.55 * _noise(h, w, s ^ 0xC, (16 * sr, 50 * sr)))).astype(np.float32)
    stars = np.clip(stars + mw * (_noise(h, w, s ^ 0xE, (2, 5)) > 0.45) * 0.6
                    + (_noise(h, w, s ^ 0x1B, (2, 4)) > 0.5) * _noise(h, w, s ^ 0x1C, (3, 6)) * 0.38, 0, 1)
    # comet streaks
    heads = np.zeros((h, w), np.float32); tails = np.zeros((h, w), np.float32); tdir = np.zeros((h, w), np.float32)
    ba = rng.uniform(0, 2 * np.pi)
    for _ in range(int(11 * sr * sr) + 5):
        cy, cx = rng.uniform(0, h), rng.uniform(0, w); ang = ba + rng.uniform(-0.4, 0.4)
        L = rng.uniform(60, 150) * sr; wv = max(1.2, rng.uniform(1.4, 2.6) * sr); amp = rng.uniform(0.6, 1.0)
        ca, sa = np.cos(ang), np.sin(ang); rr = int(L + 6); iy, ix = int(cy), int(cx)
        y0, y1 = max(0, iy - rr), min(h, iy + rr + 1); x0, x1 = max(0, ix - rr), min(w, ix + rr + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        ly, lx = yy[y0:y1] - cy, xx[:, x0:x1] - cx
        u = lx * ca + ly * sa; v = -lx * sa + ly * ca; t = np.clip(-u / L, 0, 1)
        tail = np.exp(-(v * v) / (2 * (wv * (0.4 + t)) ** 2)) * (u < 1.0) * (u > -L) * amp * (1 - t)
        head = np.exp(-(u * u + v * v) / (2 * (wv * 1.4) ** 2)) * amp
        sub = tails[y0:y1, x0:x1]; keep = tail > sub; sub[keep] = tail[keep]; tdir[y0:y1, x0:x1][keep] = t[keep]
        np.maximum(heads[y0:y1, x0:x1], head, out=heads[y0:y1, x0:x1])
    return stars.astype(np.float32), np.clip(tails, 0, 1).astype(np.float32), tdir.astype(np.float32), nebula, heads.astype(np.float32)


def _comet_parade_paint(h, w, s):
    stars, tails, tdir, nebula, heads = _comet_fields(h, w, s)
    base = oklch_ramp([(0.02, 0.04, 0.16), (0.05, 0.11, 0.34), (0.12, 0.26, 0.55)],
                      np.clip(0.18 + 0.82 * nebula, 0, 1), flatten_lightness=0.25)
    eff = base + np.float32([0.85, 0.92, 1.0]) * stars[..., None] * 0.95
    chroma = oklch_ramp([(0.95, 0.35, 0.12), (0.98, 0.98, 0.95), (0.45, 0.70, 1.0)], tdir)
    eff = eff + chroma * tails[..., None] * 0.9 + np.float32([1.0, 1.0, 1.0]) * heads[..., None]
    eff = eff * (0.9 + 0.2 * _microtex(h, w, s)[..., None])     # fine sky granulation (coverage)
    return np.clip(eff, 0, 1).astype(np.float32)


def _comet_parade_spec(h, w, s):
    stars, tails, tdir, nebula, heads = _comet_fields(h, w, s)
    M = np.clip(16 + 238 * heads + 120 * stars, 0, 255)
    R = np.clip(172 - 110 * tails - 40 * nebula, 15, 255)
    Cc = np.clip(28 + 150 * tails + 70 * stars + 40 * nebula, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), Cc.astype(np.float32)


# ================================================================ 4. FABLE MAGNETITE FLOW (ferrofluid spikes)
def _ferro_fields(h, w, s):
    sr = _sr(h, w); yy, xx = _coords(h, w)
    rng = _rng(s, 4)
    # scalar potential from scattered poles -> gradient magnitude drives spike packing
    nd = 16
    cy = rng.uniform(0, h, nd); cx = rng.uniform(0, w, nd)
    q = rng.choice([-1.0, 1.0], nd)
    phi = np.zeros((h, w), np.float32)
    for i in range(nd):
        d2 = (yy - cy[i]) ** 2 + (xx - cx[i]) ** 2 + (40 * sr) ** 2
        phi += q[i] * np.log(d2).astype(np.float32)
    phi = (phi - phi.min()) / max(float(np.ptp(phi)), 1e-6)
    # SHARP Rosensweig spike lattice: hex-ish peaks where field is strong, warped
    warpy, warpx = _warp(yy, xx, h, w, s, 7 * sr)
    p = 7.0 * sr
    cellx = 0.5 + 0.5 * np.cos(2 * np.pi * warpx / p)
    celly = 0.5 + 0.5 * np.cos(2 * np.pi * warpy / (p * 0.87))
    peaks = (cellx * celly) ** 3.0                          # sharp peaks, deep valleys
    field = np.clip(0.35 + 0.9 * phi, 0, 1)
    spikes = np.clip(peaks * (0.4 + field), 0, 1)
    tips = np.clip((spikes - 0.6) / 0.4, 0, 1)              # bright tip caps only
    return spikes.astype(np.float32), tips.astype(np.float32), phi.astype(np.float32)


def _magnetite_flow_paint(h, w, s):
    spikes, tips, phi = _ferro_fields(h, w, s)
    # black-chrome: near-black valleys, steel-blue spike flanks, white-hot tips
    steel = oklch_ramp([(0.03, 0.04, 0.07), (0.16, 0.20, 0.28), (0.60, 0.68, 0.80)], spikes, flatten_lightness=0.12)
    eff = steel
    eff = eff + tips[..., None] * np.float32([0.95, 0.97, 1.0]) * 0.85
    # subtle violet field tint by phi (polarity territories)
    eff = eff + (phi[..., None] - 0.5) * np.float32([0.10, 0.02, 0.16]) * 0.5
    return np.clip(eff, 0, 1).astype(np.float32)


def _magnetite_flow_spec(h, w, s):
    spikes, tips, phi = _ferro_fields(h, w, s)
    M = np.clip(30 + 225 * tips + 40 * spikes, 0, 255)      # chrome tips ignite
    R = np.clip(190 - 150 * spikes, 12, 255)               # valleys rough, tips polished
    Cc = np.clip(26 + 150 * tips + 40 * (phi - 0.5), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), Cc.astype(np.float32)


# ================================================================ 5. LFR FREEDOM FORGE (Damascus steel)
def _damascus_fields(h, w, s):
    sr = _sr(h, w); yy, xx = _coords(h, w)
    rng = _rng(s, 5)
    # folded watered pattern: turbulent-warped stacked sine bands
    turb = (_noise(h, w, s ^ 0x1, (24 * sr, 70 * sr)) - 0.5) * 60 * sr + (_noise(h, w, s ^ 0x2, (8 * sr, 22 * sr)) - 0.5) * 18 * sr
    a = rng.uniform(0, np.pi)
    proj = (xx * np.cos(a) + yy * np.sin(a)) + turb
    bands = 0.5 + 0.5 * np.sin(proj / (5.0 * sr) * 2 * np.pi)
    bands = bands ** 1.6                                   # crisp light bands, dark valleys
    # secondary cross-fold for the watered "ladder"
    proj2 = (xx * np.cos(a + 1.3) + yy * np.sin(a + 1.3)) + turb * 0.6
    ladder = (0.5 + 0.5 * np.sin(proj2 / (11.0 * sr) * 2 * np.pi)) ** 3
    grain = _noise(h, w, s ^ 0x3, (2, 4))
    return bands.astype(np.float32), ladder.astype(np.float32), grain.astype(np.float32)


def _freedom_forge_design_paint(h, w, s):
    bands, ladder, grain = _damascus_fields(h, w, s)
    t = np.clip(0.5 * bands + 0.3 * ladder + 0.2 * grain, 0, 1)
    steel = oklch_ramp([(0.18, 0.19, 0.23), (0.46, 0.48, 0.53), (0.82, 0.84, 0.89)], t, flatten_lightness=0.18)
    # faint forge-heat bloom in the deepest etch valleys
    heat = np.clip(1 - bands, 0, 1) ** 2
    warm = np.float32([0.85, 0.35, 0.10])
    eff = steel * (0.94 + 0.12 * grain[..., None]) + warm * heat[..., None] * 0.10
    return np.clip(eff, 0, 1).astype(np.float32)


def _freedom_forge_design_spec(h, w, s):
    bands, ladder, grain = _damascus_fields(h, w, s)
    M = np.clip(30 + 210 * bands, 0, 255)                  # polished light bands mirror
    R = np.clip(200 - 150 * bands + 30 * ladder, 15, 255)  # etched valleys rough
    Cc = np.clip(34 + 110 * (bands * ladder), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), Cc.astype(np.float32)


# ================================================================ 6. LFR ROCKETS RED GLARE (layered fireworks)
def _fireworks_fields(h, w, s):
    sr = _sr(h, w); yy, xx = _coords(h, w)
    rng = _rng(s, 6)
    sparks = np.zeros((h, w), np.float32)
    cores = np.zeros((h, w), np.float32)
    hue = np.zeros((h, w), np.float32)
    n = int(80 * sr * sr) + 26
    for _ in range(n):
        cy, cx = rng.uniform(0.05, 0.95) * h, rng.uniform(0.05, 0.95) * w
        reach = rng.uniform(40, 95) * sr
        kind = rng.integers(0, 3)
        col = rng.uniform(0, 1)
        rr = int(reach * 1.25)
        iy, ix = int(cy), int(cx)
        y0, y1 = max(0, iy - rr), min(h, iy + rr + 1)
        x0, x1 = max(0, ix - rr), min(w, ix + rr + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        ly, lx = yy[y0:y1] - cy, xx[:, x0:x1] - cx
        r = np.sqrt(ly * ly + lx * lx) + 1e-3
        th = np.arctan2(ly, lx)
        nsp = int(rng.integers(22, 40))
        ph = rng.uniform(0, 6.28)
        decay = np.exp(-r / reach)
        if kind == 0:      # chrysanthemum: straight spokes + terminal dots
            beam = np.clip(np.cos(th * nsp + ph), 0, 1) ** 12
            dots = np.exp(-((r - reach * 0.9) / (2.2 * sr)) ** 2) * np.clip(np.cos(th * nsp + ph), 0, 1) ** 18
            f = (beam * decay + dots)
        elif kind == 1:    # willow: drooping curved trails
            droop = th + 0.0009 * r * r / (sr * sr) * 0.0
            beam = np.clip(np.cos((th + r * 0.006 / sr) * nsp + ph), 0, 1) ** 10
            f = beam * decay
        else:              # crossette: sparse splitting bright pin trails
            beam = np.clip(np.cos(th * (nsp // 2) + ph), 0, 1) ** 6
            split = (np.sin(r * 0.5 / sr) > 0.4).astype(np.float32)
            f = beam * split * decay
        f = f.astype(np.float32)
        sub = sparks[y0:y1, x0:x1]
        keep = f > sub
        sub[keep] = f[keep]
        hue[y0:y1, x0:x1][keep] = col
        np.maximum(cores[y0:y1, x0:x1], np.exp(-(r / (3 * sr)) ** 2), out=cores[y0:y1, x0:x1])
    # dense falling spark-rain between bursts (full coverage, fine)
    rain = (_noise(h, w, s ^ 0xA, (2, 4)) > 0.74).astype(np.float32)
    rainv = rain * (0.35 + 0.45 * _noise(h, w, s ^ 0xC, (9 * sr, 24 * sr)))
    fresh = rainv > sparks
    hue[fresh] = _noise(h, w, s ^ 0xE, (12 * sr, 30 * sr))[fresh]
    sparks = np.maximum(sparks, rainv)
    night = _noise(h, w, s ^ 0x9, (70 * sr, 200 * sr))
    return np.clip(sparks, 0, 1), np.clip(cores, 0, 1), hue.astype(np.float32), night


def _rockets_red_glare_design_paint(h, w, s):
    sparks, cores, hue, night = _fireworks_fields(h, w, s)
    sky = oklch_ramp([(0.02, 0.03, 0.62), (0.05, 0.05, 0.62), (0.10, 0.06, 0.55)], night, flatten_lightness=0.3)
    burst = oklch_ramp([(0.85, 0.22, 0.05), (0.97, 0.18, 0.25), (0.80, 0.14, 0.95)], hue)
    white = np.float32([1.0, 0.97, 0.9])
    eff = sky + burst * sparks[..., None] + white * cores[..., None]
    eff = eff + white * (sparks ** 3)[..., None] * 0.5
    return np.clip(eff, 0, 1).astype(np.float32)


def _rockets_red_glare_design_spec(h, w, s):
    sparks, cores, hue, night = _fireworks_fields(h, w, s)
    M = np.clip(16 + 150 * (sparks ** 2) + 90 * cores, 0, 255)
    R = np.clip(180 - 60 * sparks - 30 * night, 15, 255)
    Cc = np.clip(24 + 215 * sparks + 40 * cores, 16, 255)   # wet spark trails ignite
    return M.astype(np.float32), R.astype(np.float32), Cc.astype(np.float32)


# ================================================================ PATTERN designs (texture + paint)
# Patterns return a single-channel artwork field (0..1, alpha-stampable) from
# _<id>_tex(h,w,s); the colorizer paints metal/ink over it.
def _filigree_tex(h, w, s):
    sr = _sr(h, w)
    canvas = np.zeros((h, w), np.uint8)
    rng = _rng(s, 11)
    n = int(780 * sr * sr) + 170
    for _ in range(n):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        scale = rng.uniform(4, 9) * sr
        rot = rng.uniform(0, 2 * np.pi)
        turns = rng.uniform(1.6, 3.0)
        # logarithmic spiral scroll
        t = np.linspace(0, turns * 2 * np.pi, 44).astype(np.float32)
        rr = scale * np.exp(0.17 * t)
        px = cx + np.cos(t + rot) * rr * 0.16
        py = cy + np.sin(t + rot) * rr * 0.16
        pts = np.stack([px, py], 1).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], False, 255, max(1, int(round(0.9 * sr))), cv2.LINE_AA)
        # beadwork dots along the scroll
        for k in range(0, 44, 8):
            cv2.circle(canvas, (int(px[k]), int(py[k])), max(1, int(round(1.0 * sr))), 255, -1, cv2.LINE_AA)
        # a mirrored C-scroll partner
        cv2.ellipse(canvas, (int(cx), int(cy)), (int(scale), int(scale * 0.6)),
                    np.degrees(rot), 20, 300, 255, max(1, int(round(0.9 * sr))), cv2.LINE_AA)
    tex = cv2.GaussianBlur(canvas.astype(np.float32) / 255.0, (0, 0), 0.6 * sr)
    # fine engraved cross-hatch ground so the whole plate carries detail (coverage)
    yy, xx = _coords(h, w)
    hatch = (0.5 + 0.5 * np.sin((xx + yy) / (2.6 * sr) * 6.283)) * (0.5 + 0.5 * np.sin((xx - yy) / (3.1 * sr) * 6.283))
    return np.maximum(np.clip(tex * 1.4, 0, 1), (hatch * 0.42).astype(np.float32)).astype(np.float32)


def _eaglecrest_tex(h, w, s):
    sr = _sr(h, w); yy, xx = _coords(h, w)
    rng = _rng(s, 12)
    # all-over shingled plumage: warped rows of overlapping feather lenses with fine
    # barb striations + central shafts. Fully vectorized -> fast + full coverage.
    wy, wx = _warp(yy, xx, h, w, s, 16 * sr)
    a = rng.uniform(0, np.pi)
    u = wx * np.cos(a) + wy * np.sin(a)
    v = -wx * np.sin(a) + wy * np.cos(a)
    rowp = 22.0 * sr
    rowi = np.floor(u / rowp)
    fu = u / rowp - rowi
    colp = 15.0 * sr
    vv = v / colp + (rowi % 2.0) * 0.5
    fv = vv - np.floor(vv)
    lens = np.clip(1.0 - ((fv - 0.5) * 2.0) ** 2, 0, 1) * np.clip(1.0 - fu * 0.6, 0, 1)
    rachis = np.exp(-(((fv - 0.5) * colp) / (1.1 * sr)) ** 2) * np.clip(1.0 - fu, 0, 1)
    barbs = (0.5 + 0.5 * np.cos((np.abs(fv - 0.5) * colp * 0.9 + fu * rowp) / (2.4 * sr) * 6.283)) ** 2
    feather = np.clip(0.36 * lens + 0.64 * lens * barbs + 0.6 * rachis, 0, 1)
    return np.clip(feather + 0.20 * _microtex(h, w, s), 0, 1).astype(np.float32)


def _constellation_tex(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 13)
    # tens of thousands of micro stars, magnitude-varied (full coverage)
    imp = np.zeros((h, w), np.float32)
    n = int(26000 * sr * sr)
    ys = rng.integers(0, h, n); xs = rng.integers(0, w, n)
    np.maximum.at(imp, (ys, xs), (rng.random(n) ** 2.6).astype(np.float32))
    stars = np.clip(cv2.GaussianBlur(imp, (0, 0), 0.55 * sr) * 3.2, 0, 1)
    # nebula dust gives structure EVERYWHERE so no empty gaps
    neb = _noise(h, w, s ^ 0x5, (24 * sr, 70 * sr))
    dust = (_noise(h, w, s ^ 0x21, (2, 4)) > 0.45) * _noise(h, w, s ^ 0x22, (3, 6)) * 0.42
    canvas = np.clip(stars + neb * 0.22 + dust, 0, 1)
    # bright anchor stars + dense constellation line web
    nanc = int(120 * sr)
    ay = rng.integers(0, h, nanc); ax = rng.integers(0, w, nanc)
    for i in range(nanc - 1):
        if rng.random() < 0.7:
            cv2.line(canvas, (int(ax[i]), int(ay[i])), (int(ax[i + 1]), int(ay[i + 1])),
                     0.6, max(1, int(round(0.8 * sr))), cv2.LINE_AA)
        cv2.circle(canvas, (int(ax[i]), int(ay[i])), max(1, int(round(1.8 * sr))), 1.0, -1, cv2.LINE_AA)
    return np.clip(canvas, 0, 1).astype(np.float32)


def _distressedflag_tex(h, w, s):
    sr = _sr(h, w); yy, xx = _coords(h, w)
    rng = _rng(s, 14)
    # woven fabric: over-under thread grid (two phases) warped slightly
    wy, wx = _warp(yy, xx, h, w, s, 4 * sr)
    p = 3.4 * sr
    warp_t = 0.5 + 0.5 * np.sin(wx / p * 2 * np.pi)
    weft_t = 0.5 + 0.5 * np.sin(wy / p * 2 * np.pi)
    weave = np.maximum(warp_t * (weft_t < 0.5), weft_t * (warp_t < 0.5)).astype(np.float32)
    weave = 0.4 + 0.6 * weave
    # worn/cracked paint patches (large soft noise threshold) + frays at edges
    wear = _noise(h, w, s ^ 0x7, (40 * sr, 110 * sr))
    worn = np.clip((wear - 0.42) / 0.28, 0, 1)
    # small torn holes (scattered dark voids) — kept tight so weave stays the texture
    holes = _splat_points(h, w, s ^ 0x8, int(16 * sr * sr) + 5,
                          lambda dy, dx, rng2, i: np.exp(-(dy * dy + dx * dx) / (2 * (rng2.uniform(2, 5) * sr) ** 2)),
                          rad=int(7 * sr) + 2)
    # fine thread fray grain so every patch still reads as woven cloth
    fray = _noise(h, w, s ^ 0xF, (2, 4))
    canvas = (weave * (0.74 + 0.26 * worn) * (0.85 + 0.20 * fray)).astype(np.float32)
    canvas = canvas * (1 - np.clip(holes * 1.3, 0, 1))
    return np.clip(canvas, 0, 1).astype(np.float32)


# pattern colorizers: paint metal/ink over the texture, alpha = texture
_PAT_COLOR = {
    "lfr_liberty_filigree": (np.float32([0.86, 0.69, 0.28]), np.float32([0.96, 0.86, 0.55])),  # gold
    "lfr_eagle_crest":      (np.float32([0.55, 0.40, 0.16]), np.float32([0.93, 0.82, 0.5])),    # bronze-gold
    "lfr_constellation_field": (np.float32([0.75, 0.82, 1.0]), np.float32([1.0, 1.0, 1.0])),    # starlight
    "lfr_distressed_flag":  (np.float32([0.42, 0.10, 0.14]), np.float32([0.74, 0.72, 0.70])),   # worn red/bone
}
_PAT_TEX = {
    "lfr_liberty_filigree": _filigree_tex,
    "lfr_eagle_crest": _eaglecrest_tex,
    "lfr_constellation_field": _constellation_tex,
    "lfr_distressed_flag": _distressedflag_tex,
}


# ---------------------------------------------------------------- design registry
# id -> (paint(h,w,s)->HxWx3, spec(h,w,s)->(M,R,Cc), kind)
DESIGNS = {
    "butterfly_morpho":      (_butterfly_morpho_paint, _butterfly_morpho_spec, "mono_base"),
    "moth_luna":             (_moth_luna_paint, _moth_luna_spec, "mono_base"),
    "fable_comet_parade":    (_comet_parade_paint, _comet_parade_spec, "fable"),
    "fable_magnetite_flow":  (_magnetite_flow_paint, _magnetite_flow_spec, "fable"),
    "lfr_freedom_forge":     (_freedom_forge_design_paint, _freedom_forge_design_spec, "lfr_mono"),
    "lfr_rockets_red_glare": (_rockets_red_glare_design_paint, _rockets_red_glare_design_spec, "lfr_mono"),
    "lfr_liberty_filigree":  (None, None, "pattern"),
    "lfr_eagle_crest":       (None, None, "pattern"),
    "lfr_constellation_field": (None, None, "pattern"),
    "lfr_distressed_flag":   (None, None, "pattern"),
}


# ============================================================ LIVE-ENGINE WIRING
# Owner 2026-06-10: ALWAYS wire review designs onto the car + ALWAYS optimize for
# render speed. Designs render at a 1024 work grid (fast, <=2s) and upscale to the
# requested canvas (the engine's standard approach), adapted to each registry's
# contract: monolithic (spec_fn, paint_fn), base (base_spec_fn 3-tuple + paint_fn),
# and the LFR pattern dispatch (texture pack dict + paint).
_WORK = 1024


def _seed_int(seed):
    try:
        return int(seed) & 0x7FFFFFFF
    except Exception:
        return abs(hash(str(seed))) & 0x7FFFFFFF


def _up(a, fh, fw):
    return cv2.resize(np.asarray(a, np.float32), (fw, fh), interpolation=cv2.INTER_LINEAR)


def _m2(mask, fh, fw):
    if mask is None:
        return np.ones((fh, fw), np.float32)
    m = np.asarray(mask, np.float32)
    if m.ndim == 3:
        m = m[:, :, 0]
    if m.shape[:2] != (fh, fw):
        m = cv2.resize(m, (fw, fh), interpolation=cv2.INTER_LINEAR)
    return np.clip(m, 0.0, 1.0)


def _pack(M, R, Cc, m, sm):
    out = np.zeros(M.shape[:2] + (4,), np.uint8)
    inv = 1.0 - m
    out[:, :, 0] = np.clip(M * sm * m + 4.0 * inv, 0, 255)
    out[:, :, 1] = np.clip(R * sm * m + 120.0 * inv, 15, 255)
    out[:, :, 2] = np.clip(Cc * sm * m + 16.0 * inv, 0, 255)
    out[:, :, 3] = 255
    return out


def _mk_finish(fid):
    paint_d, spec_d, _k = DESIGNS[fid]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        eff = _up(paint_d(_WORK, _WORK, _seed_int(seed)), fh, fw)
        base = np.asarray(paint, np.float32)[:, :, :3]
        m = (_m2(mask, fh, fw) * float(pm))[..., None]
        return np.clip(base * (1.0 - m) + eff * m, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        M, R, Cc = spec_d(_WORK, _WORK, _seed_int(seed))
        return _pack(_up(M, fh, fw), _up(R, fh, fw), _up(Cc, fh, fw), _m2(mask, fh, fw), float(sm))

    def base_spec_fn(shape, seed, sm, base_m=None, base_r=None, **kw):
        fh, fw = int(shape[0]), int(shape[1])
        M, R, Cc = spec_d(_WORK, _WORK, _seed_int(seed))
        return _up(M, fh, fw), _up(R, fh, fw), _up(Cc, fh, fw)

    return spec_fn, paint_fn, base_spec_fn


def _mk_pattern(fid):
    texfn = _PAT_TEX[fid]
    lo, hi = _PAT_COLOR[fid]

    def tex_route(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        val = np.asarray(texfn(fh, fw, _seed_int(seed)), np.float32)  # patterns are cheap -> native res, no upscale blur
        cc = np.clip(16.0 * (1.0 - val * 0.5), 0, 16).astype(np.uint8)
        return {"pattern_val": np.clip(val, 0, 1).astype(np.float32),
                "R_range": -120.0, "M_range": 95.0, "CC": cc}

    def paint_route(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        val = np.asarray(texfn(fh, fw, _seed_int(seed)), np.float32)
        if isinstance(bb, dict) and bb.get("pattern_val") is not None:
            val = np.clip(np.asarray(bb["pattern_val"], np.float32), 0, 1)
            if val.shape[:2] != (fh, fw):
                val = cv2.resize(val, (fw, fh), interpolation=cv2.INTER_LINEAR)
        metal = lo[None, None, :] + (hi - lo)[None, None, :] * val[..., None]
        base = np.asarray(paint, np.float32)[:, :, :3]
        # ALWAYS confine to the zone mask — a pattern must stay in the color zone it
        # is tied to, never bleed across the whole car (owner bug 2026-06-10). If bb
        # carried a pre-masked pattern_val this is a no-op; if it didn't (we used the
        # full-canvas texture), the mask multiply is what keeps it in-zone.
        a = (val * float(pm) * _m2(mask, fh, fw))[..., None]
        return np.clip(base * (1.0 - a) + metal * a, 0, 1).astype(np.float32)

    return tex_route, paint_route


def install_into_engine(mono_reg, base_reg):
    """Register all 10 redesigns into the live registries. Returns a summary str."""
    nf = nb = npat = 0
    for fid, (_pd, _sd, kind) in DESIGNS.items():
        if kind == "pattern":
            try:
                import engine.expansion_patterns as _xp
                tex_route, paint_route = _mk_pattern(fid)
                if hasattr(_xp, "_IGN_TEX_ROUTES"):
                    _xp._IGN_TEX_ROUTES[fid] = tex_route
                    _xp._IGN_PAINT_ROUTES[fid] = paint_route
                    npat += 1
            except Exception:
                pass
            continue
        spec_fn, paint_fn, base_spec_fn = _mk_finish(fid)
        mono_reg[fid] = (spec_fn, paint_fn)
        nf += 1
        be = base_reg.get(fid) if base_reg is not None else None
        if isinstance(be, dict) and "base_spec_fn" in be:
            be["paint_fn"] = paint_fn
            be["base_spec_fn"] = base_spec_fn
            nb += 1
    return "redesign-b10: %d finishes (%d base), %d patterns wired" % (nf, nb, npat)
