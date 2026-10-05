# ============================================================================
# engine/expansions/patterns_rebuild_2026.py
# DE-DUPE regular patterns (2026-06-22). 24 renderers were each reused across
# multiple distinctly-named patterns (e.g. pixel_grid/rev_counter/roll_cage/
# shokk_grid/starting_grid/tron all rendered the SAME tron grid). The owner-rule:
# no two patterns share a design. Here each non-canonical member gets its OWN
# name-true bespoke texture renderer. The canonical member of each group keeps
# its original renderer. Two all-legacy groups (flame_aggressive, flame_wild)
# are left for the legacy-removal phase.
#
# Contract: texture_fn(shape,(h,w)), mask, seed, sm) ->
#   {"pattern_val": HxW float32 0..1, "R_range": float, "M_range": float, "CC": int}
# pattern_val is the relief/coverage field; paint_fn (kept as-is) colors it.
# Install DEAD-LAST over shokker_engine_v2.PATTERN_REGISTRY (the render path's reg).
# 2-copy file (root -> electron-app/server).
# ============================================================================
from __future__ import annotations
import numpy as np
import cv2

F32 = np.float32


def _D(pv, R=-110.0, M=170.0, CC=0):
    return {"pattern_val": np.clip(pv, 0, 1).astype(F32), "R_range": float(R), "M_range": float(M), "CC": int(CC)}


def _win_bounds(cy, cx, r, h, w):
    """Clamped bounding window [y0:y1, x0:x1] around (cy,cx) with half-size r.
    Used for windowed splats — compute a primitive only where it can be nonzero
    instead of over the whole grid (huge speedup; bit-identical for primitives
    that are exactly 0 outside this box)."""
    return (max(0, int(np.floor(cy - r))), min(h, int(np.ceil(cy + r)) + 1),
            max(0, int(np.floor(cx - r))), min(w, int(np.ceil(cx + r)) + 1))


def _mg(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    return yy.astype(F32), xx.astype(F32)


def _rng(s):
    return np.random.default_rng(int(s) & 0xFFFFFFFF)


def _vnoise(h, w, cells, seed):
    return cv2.resize(_rng(seed).random((max(2, cells), max(2, cells))).astype(F32), (w, h), interpolation=cv2.INTER_CUBIC)


def _fbm(h, w, seed, octs=4, base=4):
    a = np.zeros((h, w), F32); amp = 1.0; tot = 0.0
    for o in range(octs):
        a += amp * _vnoise(h, w, base * (2 ** o), seed + o * 7 + 1); tot += amp; amp *= 0.5
    return a / tot


def _norm(a):
    a = a.astype(F32); lo = float(a.min()); hi = float(a.max())
    return (a - lo) / (hi - lo) if hi - lo > 1e-9 else a * 0


def _vor(h, w, seed, n, cap=560):
    """Voronoi nearest-id + edge field, computed at <=cap then upscaled."""
    sc = min(1.0, cap / max(h, w)); hc, wc = max(8, int(h * sc)), max(8, int(w * sc))
    rng = _rng(seed); pts = np.stack([rng.uniform(0, hc, n), rng.uniform(0, wc, n)], 1).astype(F32)
    yy, xx = np.mgrid[0:hc, 0:wc]
    best = np.full((hc, wc), 1e9, F32); idx = np.zeros((hc, wc), np.int32); second = np.full((hc, wc), 1e9, F32)
    for i in range(n):
        d = (yy - pts[i, 0]) ** 2 + (xx - pts[i, 1]) ** 2
        m = d < best
        second = np.where(m, best, np.minimum(second, d)); idx = np.where(m, i, idx); best = np.where(m, d, best)
    edge = _norm(np.sqrt(second) - np.sqrt(best))
    if (hc, wc) != (h, w):
        edge = cv2.resize(edge, (w, h), interpolation=cv2.INTER_LINEAR)
        idx = cv2.resize(idx.astype(F32), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    return idx, edge


def _scatter(h, w, seed, n, rmin, rmax, cap=720):
    sc = min(1.0, cap / max(h, w)); hc, wc = max(8, int(h * sc)), max(8, int(w * sc))
    rng = _rng(seed); out = np.zeros((hc, wc), F32); yy, xx = np.mgrid[0:hc, 0:wc]
    for _ in range(n):
        cy, cx = rng.uniform(0, hc), rng.uniform(0, wc); r = rng.uniform(rmin, rmax) * sc
        d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        out = np.maximum(out, np.clip(1 - d / max(r, 1), 0, 1))
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR) if (hc, wc) != (h, w) else out


# ---------------- TECH / GRID family ----------------
def t_pixel_grid(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); cell = max(6, d // 44)
    by = (yf // cell).astype(int); bx = (xf // cell).astype(int)
    vals = _rng(seed).random((by.max() + 2, bx.max() + 2)).astype(F32)
    pv = vals[by, bx] * 0.8 + 0.2
    gap = ((xf % cell) < 1.2) | ((yf % cell) < 1.2)
    pv = np.where(gap, 0.05, pv)
    return _D(pv, R=-85, M=150)


def t_roll_cage(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(40, d // 3); tw = max(4, d // 24)
    def bar(c): m = np.abs(((c % p) - p / 2)); return np.clip(1 - m / tw, 0, 1)
    tube = np.maximum.reduce([bar(xf + yf), bar(xf - yf), bar(xf)])
    pv = np.sqrt(np.clip(tube, 0, 1)) * 0.9 + 0.05
    return _D(pv, R=-125, M=195)


def t_shokk_grid(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(28, d // 30); lw = max(2, d // 360)
    u = np.abs(((xf + yf) % p) - p / 2); v = np.abs(((xf - yf) % p) - p / 2)
    grid = np.clip(1 - u / lw, 0, 1) + np.clip(1 - v / lw, 0, 1)
    nodes = np.clip(1 - np.maximum(u, v) / (lw * 2.5), 0, 1) ** 2  # glow nodes at diamond intersections
    pv = np.clip(grid * 0.7 + nodes * 1.0, 0, 1)
    return _D(pv, R=-120, M=200)


def t_starting_grid(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); row = max(40, d // 6); col = max(60, d // 4)
    rr = (yf // row).astype(int); off = (rr % 2) * (col // 2)  # staggered grid boxes
    bx = ((xf + off) % col); by = (yf % row)
    box = ((bx > col * 0.12) & (bx < col * 0.62) & (by > row * 0.2) & (by < row * 0.8)).astype(F32)
    lane = (((xf + off) % col) < max(2, d // 300)).astype(F32) * 0.5
    pv = np.clip(box * 0.85 + lane, 0, 1)
    return _D(pv, R=-70, M=120)


def t_pit_lane_marks(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    lane = (np.abs(((xf % (d // 3)) - d // 6)) < max(3, d // 220)).astype(F32)
    hatch = (((xf + yf) % (d // 16)) < (d // 40)).astype(F32) * 0.5  # hazard hatch
    pv = np.clip(lane + hatch * 0.6, 0, 1)
    return _D(pv, R=-60, M=110)


def t_lap_counter(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); grp = max(40, d // 7); tick = max(28, d // 11)
    gx = (xf % grp); col = (xf // (tick / 5))
    vert = ((gx % (tick / 5)) < max(2, d // 360)).astype(F32) * ((yf % (d // 5)) < (d // 8)).astype(F32)
    cross = (np.abs((gx) - (yf % (d // 5))) < max(2, d // 360)).astype(F32) * (gx < tick).astype(F32) * 0.7
    pv = np.clip(vert + cross, 0, 1)
    return _D(pv, R=-80, M=130)


def t_qr_code(shape, mask, seed, sm):
    h, w = shape; d = min(h, w); cell = max(8, d // 40)
    nh, nw = h // cell + 1, w // cell + 1
    rng = _rng(seed); mods = (rng.random((nh, nw)) > 0.5).astype(F32)
    for (cy, cx) in [(1, 1), (1, nw - 4), (nh - 4, 1)]:  # finder squares
        if 0 <= cy < nh - 3 and 0 <= cx < nw - 3:
            mods[cy:cy + 3, cx:cx + 3] = 1.0; mods[cy + 1, cx + 1] = 0.0
    pv = cv2.resize(mods, (w, h), interpolation=cv2.INTER_NEAREST)
    return _D(pv, R=-70, M=140)


def t_perforated(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(16, d // 34); r = p * 0.32
    row = (yf // p).astype(int); off = (row % 2) * (p * 0.5)        # staggered (hex-packed) holes
    cy = ((yf % p) - p / 2); cx = (((xf + off) % p) - p / 2)
    hole = (np.sqrt(cy * cy + cx * cx) < r).astype(F32)
    pv = np.clip(1 - hole, 0.1, 1)  # holes carve down
    return _D(pv, R=80, M=-60)


def t_rev_counter(shape, mask, seed, sm):
    """RPM bar-graph readout — vertical bars rising toward redline (not tally marks)."""
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); bw = max(8, d // 26)
    col = (xf // bw).astype(int)
    cyc = (col % 18) / 17.0
    bartop = h * (1.0 - (0.25 + cyc * 0.7))
    bar = ((xf % bw) < bw * 0.68) & (yf > bartop)
    pv = bar.astype(F32) * 0.9 + 0.05
    return _D(pv, R=-80, M=150)


def t_shokk_hex(shape, mask, seed, sm):
    """True honeycomb (3-sine hex) with glowing nodes — distinct from the diamond grid."""
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); f = 6.2832 / max(10, d // 20)
    a = np.cos(f * xf) + np.cos(f * (xf * 0.5 + yf * 0.866)) + np.cos(f * (xf * 0.5 - yf * 0.866))
    cell = _norm(a)
    edge = np.clip(1 - np.abs(cell - 0.5) / 0.12, 0, 1)
    node = (cell > 0.93).astype(F32)
    pv = np.clip(edge * 0.7 + node, 0, 1)
    return _D(pv, R=-115, M=195)


def t_rpm_gauge(shape, mask, seed, sm):
    """Tachometer sweep — radial ticks + redline arc from a corner pivot."""
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); cy, cx = h * 1.0, 0.0
    ang = np.arctan2(yf - cy, xf - cx); r = np.sqrt((yf - cy) ** 2 + (xf - cx) ** 2)
    ticks = (0.5 + 0.5 * np.sin(ang * 44) > 0.72).astype(F32) * 0.8
    band = ((r % (d * 0.42)) < d * 0.045).astype(F32) * 0.4
    redline = ((ang > -0.35) & (ang < 0.0)).astype(F32) * 0.35
    pv = np.clip(ticks + band + redline, 0, 1)
    return _D(pv, R=-70, M=140)


def t_track_map(shape, mask, seed, sm):
    """Winding race-circuit ribbon paths (two interleaving)."""
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    warp = _fbm(h, w, seed, 3, 2) * d * 0.4
    rib1 = np.clip(1 - np.abs(((xf + warp) % (d * 0.7)) - d * 0.35) / (d * 0.03), 0, 1)
    warp2 = _fbm(h, w, seed + 9, 3, 2) * d * 0.4
    rib2 = np.clip(1 - np.abs(((yf + warp2) % (d * 0.85)) - d * 0.42) / (d * 0.03), 0, 1)
    pv = np.clip(np.maximum(rib1, rib2), 0, 1)
    return _D(pv, R=-80, M=150)


def t_racing_scratch(shape, mask, seed, sm):
    """Fine directional surface scratches/scuffs (not clean stripes)."""
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(int(140 + d / 10)):
        cy = rng.uniform(0, h); cx = rng.uniform(0, w); a = rng.uniform(-0.32, 0.32); ln = rng.uniform(d * 0.05, d * 0.32); ww = rng.uniform(0.6, 1.8); val = rng.uniform(0.4, 1.0)
        r = np.hypot(ln, ww) + 2.0; y0, y1, x0, x1 = _win_bounds(cy, cx, r, h, w)
        if y1 <= y0 or x1 <= x0:
            continue
        uw = (xf[y0:y1, x0:x1] - cx) * np.cos(a) + (yf[y0:y1, x0:x1] - cy) * np.sin(a)
        vw = -(xf[y0:y1, x0:x1] - cx) * np.sin(a) + (yf[y0:y1, x0:x1] - cy) * np.cos(a)
        m = ((np.abs(vw) < ww) & (np.abs(uw) < ln)).astype(F32) * val
        sl = pv[y0:y1, x0:x1]; np.maximum(sl, m, out=sl)
    return _D(pv, R=105, M=-45)


def t_expanded_metal(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(20, d // 30)
    row = (yf // (p // 2)).astype(int); off = (row % 2) * (p // 2)
    u = np.abs((((xf + off) % p) - p / 2)); v = np.abs(((yf % (p // 2)) - p / 4))
    strut = np.clip(1 - (u + v * 1.6) / (p * 0.5), 0, 1)
    pv = np.sqrt(np.clip(strut, 0, 1))
    return _D(pv, R=-100, M=170)


def t_rivet_grid(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(22, d // 26); r = p * 0.22
    cy = ((yf % p) - p / 2); cx = ((xf % p) - p / 2); dd = np.sqrt(cy * cy + cx * cx)
    dome = np.clip(1 - dd / r, 0, 1) ** 0.5  # rounded rivet heads
    pv = dome * 0.9 + 0.05
    return _D(pv, R=-110, M=185)


# ---------------- DAMAGE / GRUNGE family ----------------
def t_g_force(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    streak = _vnoise(h, w, 3, seed)  # broad
    streak = cv2.GaussianBlur(streak, (0, 0), (1, 1) and max(1, d // 80))
    lines = 0.5 + 0.5 * np.sin(xf / (d / 60.0) + streak * 6)
    grad = _norm(xf)  # compression toward one edge
    pv = np.clip(lines * (0.3 + grad * 0.9), 0, 1)
    return _D(pv, R=70, M=-40)


def t_peeling_paint(shape, mask, seed, sm):
    h, w = shape; idx, edge = _vor(h, w, seed, 70)
    flake = _norm(_fbm(h, w, seed + 5, 4, 5))
    peeled = (flake > 0.55).astype(F32)
    pv = np.clip(peeled * (0.4 + edge * 1.4) + (1 - peeled) * 0.1, 0, 1)
    return _D(pv, R=95, M=-50)


def t_road_rash(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    grain = _fbm(h, w, seed, 5, 6)
    scuff = np.clip(_norm(grain) - 0.45, 0, 1) * 2
    streak = 0.5 + 0.5 * np.sin((xf * 0.9 + yf * 0.2) / (d / 90.0))
    pv = np.clip(scuff * (0.5 + streak * 0.6), 0, 1)
    return _D(pv, R=110, M=-55)


def t_bullet_holes(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(int(10 + (d / 180))):
        cy, cx = rng.uniform(0, h), rng.uniform(0, w); r = rng.uniform(d * 0.018, d * 0.045)
        dd = np.sqrt((yf - cy) ** 2 + (xf - cx) ** 2)
        rim = np.exp(-(((dd - r) / (r * 0.28)) ** 2))          # bright raised rim ring
        crater = -np.clip(1 - dd / (r * 0.8), 0, 1) * 0.6       # dark punched center
        ang = np.arctan2(yf - cy, xf - cx)
        cracks = (np.abs(np.sin(ang * rng.integers(5, 9))) > 0.9) * np.clip(1 - dd / (r * 3.0), 0, 1) * 0.35
        pv = np.maximum(pv, np.clip(rim + crater + cracks, 0, 1))
    return _D(pv, R=120, M=-60)


def t_shrapnel(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(int(40 + d / 30)):
        cy = rng.uniform(0, h); cx = rng.uniform(0, w); a = rng.uniform(0, np.pi); ln = rng.uniform(d * 0.01, d * 0.05); wd = rng.uniform(1.5, 4); val = rng.uniform(0.6, 1.0)
        r = np.hypot(ln, wd) + 2.0; y0, y1, x0, x1 = _win_bounds(cy, cx, r, h, w)
        if y1 <= y0 or x1 <= x0:
            continue
        uw = (xf[y0:y1, x0:x1] - cx) * np.cos(a) + (yf[y0:y1, x0:x1] - cy) * np.sin(a)
        vw = -(xf[y0:y1, x0:x1] - cx) * np.sin(a) + (yf[y0:y1, x0:x1] - cy) * np.cos(a)
        m = ((np.abs(vw) < wd) & (np.abs(uw) < ln)).astype(F32) * val
        sl = pv[y0:y1, x0:x1]; np.maximum(sl, m, out=sl)
    return _D(pv, R=85, M=120)


def t_skid_marks(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    a = 0.5
    u = (xf * np.cos(a) + yf * np.sin(a))
    band = np.exp(-((((u % (d * 0.6)) - d * 0.3) / (d * 0.06)) ** 2))  # smeared diagonal bands
    tread = (0.6 + 0.4 * np.sin(u / (d / 120.0)))
    grain = _fbm(h, w, seed, 4, 8) * 0.4
    pv = np.clip(band * (tread + grain), 0, 1)
    return _D(pv, R=100, M=-50)


def t_rust_bloom(shape, mask, seed, sm):
    h, w = shape; b = _norm(_fbm(h, w, seed, 5, 4))
    bloom = np.clip((b - 0.45) * 2.5, 0, 1)
    speck = (_rng(seed + 9).random((h, w)) > 0.97).astype(F32) * bloom
    pv = np.clip(bloom * 0.85 + speck, 0, 1)
    return _D(pv, R=120, M=-40)


# ---------------- WEATHER / NATURE / MISC family ----------------
def t_hailstorm(shape, mask, seed, sm):
    h, w = shape; d = min(h, w)
    balls = _scatter(h, w, seed, int(40 + d / 25), d * 0.012, d * 0.04)
    pv = np.clip(balls ** 0.6, 0, 1)
    return _D(pv, R=-40, M=90)


def t_rooster_tail(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    cy, cx = h * 0.95, w * 0.2  # spray origin
    for _ in range(int(500 + d)):
        a = rng.uniform(-1.2, -0.1); rr = rng.uniform(0, d * 0.9)
        py = cy + np.sin(a) * rr; px = cx + np.cos(a) * rr + rng.uniform(-4, 4)
        iy, ix = int(py), int(px)
        if 0 <= iy < h and 0 <= ix < w:
            pv[iy, ix] = max(pv[iy, ix], rng.uniform(0.5, 1.0))
    pv = cv2.GaussianBlur(pv, (0, 0), max(1, d // 300))
    return _D(_norm(pv), R=-30, M=80)


def t_sandstorm(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    flow = _fbm(h, w, seed, 5, 6)
    streak = cv2.GaussianBlur(_rng(seed + 3).random((h, w)).astype(F32), (max(1, d // 12) | 1, 1), 0)  # horizontal smear
    pv = np.clip(_norm(streak) * 0.7 + flow * 0.4, 0, 1)
    return _D(pv, R=90, M=-30)


def t_grip_tape(shape, mask, seed, sm):
    h, w = shape; g = _rng(seed).random((h, w)).astype(F32)
    pv = np.clip(_norm(g) ** 1.3, 0, 1)  # dense coarse grit
    return _D(pv, R=130, M=-60)


def t_pulse_monitor(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); per = max(60, d // 4)
    t = (xf % per) / per
    spike = np.where(t < 0.5, 0.5, np.where(t < 0.56, 0.5 + (t - 0.5) / 0.06 * 0.5, np.where(t < 0.62, 1.0 - (t - 0.56) / 0.06 * 0.9, 0.5)))
    line = np.clip(1 - np.abs(yf - (h * 0.5 - (spike - 0.5) * h * 0.4)) / max(2, d // 220), 0, 1)
    # repeat rows
    rows = max(2, d // 200)
    band = (yf % (h / rows))
    pv = line
    return _D(np.clip(pv, 0, 1), R=-90, M=160)


def t_rip_tide(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    warp = _fbm(h, w, seed, 4, 4) * (d / 12.0)
    cur = 0.5 + 0.5 * np.sin((xf - yf + warp) / (d / 55.0))
    pv = np.clip(cur, 0, 1)
    return _D(pv, R=-50, M=100)


def t_glacier_crack(shape, mask, seed, sm):
    h, w = shape; idx, edge = _vor(h, w, seed, 22)  # few large cells = wide fissures
    crack = np.clip((edge < 0.06).astype(F32), 0, 1)
    crack = cv2.GaussianBlur(crack, (0, 0), max(1, min(h, w) // 400))
    pv = np.clip(crack * 1.2, 0, 1)
    return _D(pv, R=-70, M=120)


def t_leather_grain(shape, mask, seed, sm):
    h, w = shape; idx, edge = _vor(h, w, seed, 240)  # many small pebble cells
    bump = _norm(_fbm(h, w, seed + 4, 4, 12))
    # pebble interiors raised (soft), thin valleys between -> supple hide, not cracked web
    pv = np.clip(edge ** 0.7 * 0.8 + bump * 0.25, 0, 1)
    return _D(pv, R=80, M=-25)


def t_tropical_leaf(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(int(7 + d / 280)):
        cy = rng.uniform(0, h); cx = rng.uniform(0, w); a = rng.uniform(0, np.pi); L = rng.uniform(d * 0.18, d * 0.4)
        y0, y1, x0, x1 = _win_bounds(cy, cx, L + 2.0, h, w)  # leaf tip is at most L from center
        if y1 <= y0 or x1 <= x0:
            continue
        xw = xf[y0:y1, x0:x1]; yw = yf[y0:y1, x0:x1]
        u = (xw - cx) * np.cos(a) + (yw - cy) * np.sin(a); v = -(xw - cx) * np.sin(a) + (yw - cy) * np.cos(a)
        t = np.clip(u / L, 0, 1)
        width = np.sin(t * np.pi) * L * 0.32
        leaf = (u > 0) & (u < L) & (np.abs(v) < width)
        midrib = leaf & (np.abs(v) < max(2, d // 300))
        veins = leaf & (np.abs((np.abs(v) - (u * 0.3) % (L * 0.1))) < max(1, d // 360))  # angled veins
        sl = pv[y0:y1, x0:x1]
        np.maximum(sl, leaf.astype(F32) * 0.6, out=sl)
        np.maximum(sl, (midrib | veins).astype(F32), out=sl)
    return _D(np.clip(pv, 0, 1), R=60, M=-20)


def t_victory_confetti(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(int(120 + d / 12)):
        cy = rng.uniform(0, h); cx = rng.uniform(0, w); a = rng.uniform(0, np.pi); sx = rng.uniform(d * 0.006, d * 0.02); sy = sx * rng.uniform(0.4, 0.8); val = rng.uniform(0.6, 1.0)
        r = np.hypot(sx, sy) + 2.0; y0, y1, x0, x1 = _win_bounds(cy, cx, r, h, w)
        if y1 <= y0 or x1 <= x0:
            continue
        uw = (xf[y0:y1, x0:x1] - cx) * np.cos(a) + (yf[y0:y1, x0:x1] - cy) * np.sin(a)
        vw = -(xf[y0:y1, x0:x1] - cx) * np.sin(a) + (yf[y0:y1, x0:x1] - cy) * np.cos(a)
        m = ((np.abs(uw) < sx) & (np.abs(vw) < sy)).astype(F32) * val
        sl = pv[y0:y1, x0:x1]; np.maximum(sl, m, out=sl)
    return _D(pv, R=20, M=110)


def t_turbo_swirl(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); cy, cx = h / 2, w / 2; d = min(h, w)
    ang = np.arctan2(yf - cy, xf - cx); r = np.sqrt((yf - cy) ** 2 + (xf - cx) ** 2)
    arms = 0.5 + 0.5 * np.sin(ang * 5 + np.log(r + 1) * 4.5)  # log-spiral vortex
    pv = np.clip(arms, 0, 1)
    return _D(pv, R=-80, M=150)


def t_surf_stripe(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); rng = _rng(seed)
    widths = rng.uniform(0.4, 1.6, 8); edges = np.cumsum(widths); edges = edges / edges[-1] * (d * 1.2)
    t = (yf % (d * 1.2))
    band = np.zeros((h, w), F32)
    for i, e in enumerate(edges):
        band = np.where(t < e, band, (i + 1) % 2 * 1.0)
    band = ((np.searchsorted(edges, (yf % (d * 1.2))) % 2)).astype(F32)
    pv = band * 0.8 + 0.1
    return _D(pv, R=-60, M=110)


def t_wind_tunnel(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    warp = _fbm(h, w, seed, 3, 3) * (d / 16.0)
    lam = 0.5 + 0.5 * np.sin((yf + warp + np.sin(xf / (d / 3.0)) * d * 0.05) / (d / 70.0))
    pv = np.clip(lam ** 1.4, 0, 1)
    return _D(pv, R=-70, M=120)


def t_sponsor_fade(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(8, d // 60)
    cy = ((yf % p) - p / 2); cx = ((xf % p) - p / 2); dd = np.sqrt(cy * cy + cx * cx)
    size = (1 - _norm(xf)) * (p * 0.5)  # halftone dots shrink across -> fade
    pv = np.clip(1 - dd / np.maximum(size, 1), 0, 1)
    return _D(pv, R=-50, M=120)


def t_art_deco(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); step = max(20, d // 16)
    chev = np.abs(((xf + (yf // step) * (step * 0.5)) % step) - step / 2) / (step / 2)
    steps = (1.0 - (yf % step) / step)
    pv = np.clip(0.5 * (1 - chev) + 0.5 * steps, 0, 1)
    return _D(pv, R=-80, M=150)


# pattern_id -> bespoke renderer (canonical member of each group keeps its original)
PATTERN_DEDUPE_MAP = {
    # tron group (tron keeps)
    "pixel_grid": t_pixel_grid, "rev_counter": t_rev_counter, "roll_cage": t_roll_cage,
    "shokk_grid": t_shokk_grid, "starting_grid": t_starting_grid,
    # battle_worn group (battle_worn keeps)
    "g_force": t_g_force, "peeling_paint": t_peeling_paint, "road_rash": t_road_rash,
    # fracture group (fracture keeps)
    "bullet_holes": t_bullet_holes, "shrapnel": t_shrapnel,
    # static_noise group (static_noise keeps)
    "grip_tape": t_grip_tape, "sandstorm": t_sandstorm,
    # rain_drop group (rain_drop keeps)
    "hailstorm": t_hailstorm, "rooster_tail": t_rooster_tail,
    # pinstripe_fine group (none canonical -> all 3 get bespoke)
    "lap_counter": t_lap_counter, "pit_lane_marks": t_pit_lane_marks, "sponsor_fade": t_sponsor_fade,
    # pinstripe_diagonal group (pinstripe_flames=legacy)
    "surf_stripe": t_surf_stripe, "wind_tunnel": t_wind_tunnel,
    # wave_choppy group (wave_curl keeps)
    "pulse_monitor": t_pulse_monitor, "rip_tide": t_rip_tide,
    # topographic group (topographic keeps)
    "rpm_gauge": t_rpm_gauge, "track_map": t_track_map,
    # 2-member groups (first listed keeps its original)
    "rust_bloom": t_rust_bloom,            # acid_wash keeps
    "art_deco": t_art_deco,                # art_deco_fan keeps the fan
    "perforated": t_perforated,            # brake_dust keeps
    "glacier_crack": t_glacier_crack,      # cracked_ice keeps
    "expanded_metal": t_expanded_metal,    # grating keeps
    "leather_grain": t_leather_grain,      # hammered keeps
    "shokk_hex": t_shokk_hex,              # hex_mesh keeps (this is a real honeycomb)
    "racing_scratch": t_racing_scratch,    # racing_stripe keeps (gate caught this dup)
    "qr_code": t_qr_code,                  # houndstooth keeps
    "tropical_leaf": t_tropical_leaf,      # racing_stripe keeps
    "rivet_grid": t_rivet_grid,            # rivet_plate keeps
    "skid_marks": t_skid_marks,            # tire_tread keeps
    "victory_confetti": t_victory_confetti,  # spark_scatter keeps
    "turbo_swirl": t_turbo_swirl,          # turbine keeps
}
# ============================================================================
# PHASE 3 — SHOWN generic-engine patterns whose literal name wasn't depicted by
# the abstract _texture engine. Give the depictable ones real bespoke renderers.
# (Iconic subjects — eagle/flag/filigree — are left for image conversion, owner call.)
# ============================================================================
def t_aztec(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); s = max(24, d // 10)
    u = np.minimum(yf % s, s - 1 - (yf % s)); v = np.minimum(xf % s, s - 1 - (xf % s))
    step = np.minimum(u, v)  # concentric stepped squares (Aztec fret)
    ring = (step.astype(int) % max(2, s // 8) < max(1, s // 16)).astype(F32)
    fret = ((xf % (s // 2) < 2) | (yf % (s // 2) < 2)).astype(F32) * 0.4
    return _D(np.clip(ring * 0.8 + fret, 0, 1), R=-70, M=140)


def t_gear_mesh(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(60, d // 4); R = p * 0.42; teeth = 14
    pv = np.zeros((h, w), F32)
    for oy in (0, p // 2):
        for ox in (0, p // 2):
            cy = ((yf + oy) % p) - p / 2; cx = ((xf + ox) % p) - p / 2
            r = np.sqrt(cy * cy + cx * cx); ang = np.arctan2(cy, cx)
            tooth = R + np.sin(ang * teeth) * (p * 0.05)
            body = (r < tooth) & (r > tooth - p * 0.12)  # gear rim with teeth
            hub = (r < p * 0.1)
            pv = np.maximum(pv, (body | hub).astype(F32))
    return _D(pv, R=-110, M=185)


def t_chainmail_hex(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); s = max(18, d // 22); rr = s * 0.5
    row = (yf // s).astype(int); off = (row % 2) * (s * 0.5)
    cy = ((yf % s) - s / 2); cx = (((xf + off) % s) - s / 2)
    r = np.sqrt(cy * cy + cx * cx)
    ring = np.clip(1 - np.abs(r - rr * 0.7) / (s * 0.12), 0, 1)  # interlocking rings
    return _D(np.clip(ring, 0, 1), R=-105, M=180)


def t_hilbert(shape, mask, seed, sm):
    h, w = shape; d = min(h, w); order = 5; n = 2 ** order
    def d2xy(n, dd):
        rx = ry = 0; x = y = 0; t = dd
        s = 1
        while s < n:
            rx = 1 & (t // 2); ry = 1 & (t ^ rx)
            if ry == 0:
                if rx == 1:
                    x = s - 1 - x; y = s - 1 - y
                x, y = y, x
            x += s * rx; y += s * ry; t //= 4; s *= 2
        return x, y
    pts = [d2xy(n, i) for i in range(n * n)]
    canv = np.zeros((d, d), np.float32); sc = (d - 1) / (n - 1)
    for i in range(len(pts) - 1):
        x0, y0 = int(pts[i][0] * sc), int(pts[i][1] * sc); x1, y1 = int(pts[i + 1][0] * sc), int(pts[i + 1][1] * sc)
        cv2.line(canv, (x0, y0), (x1, y1), 1.0, max(1, d // 220))
    pv = cv2.resize(canv, (w, h), interpolation=cv2.INTER_LINEAR)
    return _D(pv, R=-90, M=160)


def t_fiber_optic(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(int(18 + d / 60)):
        a = rng.uniform(0, np.pi); cy, cx = rng.uniform(0, h), rng.uniform(0, w)
        u = (xf - cx) * np.cos(a) + (yf - cy) * np.sin(a); v = -(xf - cx) * np.sin(a) + (yf - cy) * np.cos(a)
        strand = np.exp(-(v * v) / (2 * (d * 0.004) ** 2)) * (np.abs(u) < d * 0.6)
        glow = np.exp(-((u - d * 0.55) ** 2 + v * v) / (2 * (d * 0.02) ** 2))  # bright tip
        pv = np.maximum(pv, np.clip(strand * 0.7 + glow, 0, 1))
    return _D(pv, R=-120, M=190)


def t_thorn_vine(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(int(6 + d / 220)):
        cy, cx = rng.uniform(0, h), rng.uniform(0, w); a = rng.uniform(0, np.pi)
        warp = _fbm(h, w, seed + int(cy), 3, 3) * d * 0.15
        u = (xf - cx) * np.cos(a) + (yf - cy) * np.sin(a) + warp; v = -(xf - cx) * np.sin(a) + (yf - cy) * np.cos(a)
        vine = np.clip(1 - np.abs(v) / (d * 0.012), 0, 1) * (np.abs(u) < d * 0.7)
        thorns = (np.abs((u % (d * 0.05)) - (d * 0.025)) < d * 0.004) & (np.abs(v) < d * 0.03)
        pv = np.maximum(pv, np.maximum(vine, thorns.astype(F32) * 0.9))
    return _D(np.clip(pv, 0, 1), R=80, M=-30)


def t_bark(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    warp = _fbm(h, w, seed, 4, 5) * d * 0.05
    ridges = 0.5 + 0.5 * np.sin((xf + warp) / (d / 40.0))
    cracks = (_norm(_fbm(h, w, seed + 7, 5, 6)) > 0.6).astype(F32) * 0.5
    pv = np.clip(ridges ** 1.5 * 0.8 + cracks, 0, 1)
    return _D(pv, R=95, M=-40)


def t_firework_radial(shape, mask, seed, sm):
    h, w = shape; rng = _rng(seed); yf, xf = _mg(h, w); d = min(h, w); pv = np.zeros((h, w), F32)
    for _ in range(4):  # a few bursts (tiled feel, not one centered)
        cy, cx = rng.uniform(h * 0.2, h * 0.8), rng.uniform(w * 0.2, w * 0.8)
        ang = np.arctan2(yf - cy, xf - cx); r = np.sqrt((yf - cy) ** 2 + (xf - cx) ** 2)
        rays = (np.abs(np.sin(ang * rng.integers(16, 26))) > 0.85) * np.clip(1 - r / (d * 0.4), 0, 1)
        spark = (np.abs(r - d * 0.3) < d * 0.02) * (np.abs(np.sin(ang * 30)) > 0.5)
        pv = np.maximum(pv, np.clip(rays + spark, 0, 1))
    return _D(pv, R=-60, M=150)


def t_ribbon_weave(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(40, d // 8)
    over = (np.floor(xf / p) + np.floor(yf / p)) % 2
    hb = (0.5 + 0.5 * np.sin(yf / p * np.pi * 2)); vb = (0.5 + 0.5 * np.sin(xf / p * np.pi * 2))
    ribbon = np.where(over > 0, hb, vb)
    pv = np.clip(ribbon ** 1.2, 0, 1)
    return _D(pv, R=-70, M=130)


def t_stripe_drift(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    warp = _fbm(h, w, seed, 3, 3) * d * 0.12
    pv = (0.5 + 0.5 * np.sin((yf + warp) / (d / 16.0)))
    pv = (pv > 0.5).astype(F32) * 0.85 + 0.1
    return _D(pv, R=-65, M=120)


def t_bunting_scallop(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); p = max(40, d // 8); rowh = max(50, d // 5)
    cx = ((xf % p) - p / 2); ry = (yf % rowh)
    arc = np.sqrt(np.clip((p / 2) ** 2 - cx * cx, 0, None))  # scallop arc
    scallop = ((ry < arc * 0.8) & (ry < rowh * 0.55)).astype(F32)
    pv = np.clip(scallop * 0.85 + 0.08, 0, 1)
    return _D(pv, R=-55, M=110)


def t_rubiks(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w); cube = max(60, d // 3); cell = cube / 3
    inq = ((xf % cube) // cell + ((yf % cube) // cell) * 3).astype(int)
    rng = _rng(seed); face = rng.random((((h // cube) + 2), ((w // cube) + 2), 9)).astype(F32)
    bi = (yf // cube).astype(int); bj = (xf // cube).astype(int)
    val = face[bi, bj, inq]
    gap = ((xf % cell) < max(2, d // 200)) | ((yf % cell) < max(2, d // 200))
    cubegap = ((xf % cube) < max(3, d // 130)) | ((yf % cube) < max(3, d // 130))
    pv = np.where(gap | cubegap, 0.02, val * 0.8 + 0.2)
    return _D(pv, R=-70, M=130)


def t_pong(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    cw = max(120, d // 2); ch = max(90, d // 3)            # tiled mini courts -> reads as Pong, not empty
    lx = (xf % cw); ly = (yf % ch); pw = max(4, cw // 26); ph = ch * 0.3
    center = (np.abs(lx - cw / 2) < max(2, d // 160)) & ((ly // max(6, d // 42)) % 2 == 0)
    padL = (lx < pw * 2) & (np.abs(ly - ch * 0.35) < ph / 2)
    padR = (lx > cw - pw * 2) & (np.abs(ly - ch * 0.62) < ph / 2)
    ball = (np.abs(lx - cw * 0.55) < pw) & (np.abs(ly - ch * 0.45) < pw)
    border = (ly < max(2, d // 200)) | (ly > ch - max(2, d // 200))
    pv = (center | padL | padR | ball | border).astype(F32) * 0.9 + 0.04
    return _D(pv, R=-60, M=120)


def t_biomech_cables(shape, mask, seed, sm):
    h, w = shape; yf, xf = _mg(h, w); d = min(h, w)
    warp = _fbm(h, w, seed, 4, 4) * d * 0.08
    bund = 0.5 + 0.5 * np.sin((xf + warp) / (d / 70.0))  # tight parallel cables
    seg = 0.5 + 0.5 * np.sin((yf) / (d / 50.0))  # segment rings
    pv = np.clip(bund ** 2 * (0.6 + seg * 0.4), 0, 1)
    return _D(pv, R=-90, M=160)


# SHOWN generic-engine patterns -> bespoke (depictable subset; iconic ones left for images)
PATTERN_UPGRADE_MAP = {
    "aztec": t_aztec, "gear_mesh": t_gear_mesh, "chainmail_hex": t_chainmail_hex,
    "geo_hilbert_curve": t_hilbert, "fiber_optic": t_fiber_optic, "thorn_vine": t_thorn_vine,
    "nature_bark_rough": t_bark, "lfr_firework_radial": t_firework_radial, "lfr_ribbon_weave": t_ribbon_weave,
    "lfr_stripe_drift": t_stripe_drift, "lfr_bunting_scallop": t_bunting_scallop,
    "decade_80s_rubiks_cube_2": t_rubiks, "decade_70s_pong_pixel": t_pong, "biomech_cables": t_biomech_cables,
}


def install_pattern_dedupe(pattern_reg):
    n = 0
    for amap in (PATTERN_DEDUPE_MAP, PATTERN_UPGRADE_MAP):
        for pid, fn in amap.items():
            e = pattern_reg.get(pid)
            if isinstance(e, dict) and e.get("texture_fn") is not None:
                e["texture_fn"] = fn; n += 1
    return n
