"""NEON UNDERGROUND ENGINE (2026-06-19) — total rework: distinct neon STRUCTURES, not colour swaps.

The old NEON UNDERGROUND was 10 recolours of one tube glow. This invents genuinely different neon
TOPOLOGIES. The neon signature everywhere: a thin WHITE-HOT core + a wide COLOURED bloom halo on a
near-black backing (additive light). Full-canvas, crushed-fine (thin cores, dense structure), <3s.
Self-contained (numpy+cv2); reuses flame_math noise + gate helpers.
"""
from __future__ import annotations
import numpy as np
import cv2

from engine.paint_v2.flame_math import _fbm, _norm, _rng

# vivid neon colours (RGB 0..1) — saturated, glow-y
NEON = {
    "pink":   (1.00, 0.12, 0.62), "cyan":   (0.10, 0.98, 1.00), "lime":   (0.55, 1.00, 0.10),
    "violet": (0.65, 0.20, 1.00), "orange": (1.00, 0.45, 0.05), "blue":   (0.15, 0.45, 1.00),
    "magenta":(1.00, 0.10, 0.95), "yellow": (1.00, 0.90, 0.10), "green":  (0.10, 1.00, 0.45),
    "red":    (1.00, 0.10, 0.20),
}
_NEON_KEYS = list(NEON)


def _bloom(intensity, colormap, glow_sigma, core_pow=1.0):
    """Neon composite: white-hot core (the thin intensity) + a wide COLOURED bloom (blurred colour
    normalised by blurred intensity) on black. Additive light look."""
    inten = _norm(intensity)
    glow_i = cv2.GaussianBlur(inten, (0, 0), glow_sigma)
    glow_c = cv2.GaussianBlur(colormap, (0, 0), glow_sigma)
    halo = glow_c / (glow_i[..., None] + 0.04)                  # colour of the bloom
    halo = halo * _norm(glow_i)[..., None]                       # fade with distance
    core = np.power(np.clip(inten, 0, 1), core_pow)[..., None] * np.array([1.0, 1.0, 1.0], np.float32)
    out = np.clip(halo * 1.15 + core * 0.95, 0, 1)
    return out.astype(np.float32)


def neon_sign_tubes(shape, seed=7, tubes=40):
    """Bent-glass NEON TUBE SIGNS: a tangle of glowing tube strokes (sine-warped paths) in mixed
    neon colours, white-hot cores + colour bloom, on black. The iconic neon-sign look, full-canvas."""
    h, w = shape
    G = 720
    r = _rng(seed * 3 + 1)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    for _ in range(tubes):
        col = np.array(NEON[_NEON_KEYS[int(r.integers(0, len(_NEON_KEYS)))]], np.float32)
        x0, y0 = r.random() * G, r.random() * G
        ang = r.random() * 2 * np.pi
        length = int((0.35 + 0.6 * r.random()) * G)
        amp = (6 + 26 * r.random())
        freq = (2 + 7 * r.random()) / max(40, length)
        pts = []
        for t in range(0, length, 3):
            perp = ang + np.pi / 2
            off = amp * np.sin(t * freq * 2 * np.pi + r.random() * 6)
            x = x0 + np.cos(ang) * t + np.cos(perp) * off
            y = y0 + np.sin(ang) * t + np.sin(perp) * off
            pts.append((int(x), int(y)))
        pts = np.array([p for p in pts if 0 <= p[0] < G and 0 <= p[1] < G], np.int32)
        if len(pts) < 2:
            continue
        m = np.zeros((G, G), np.float32)
        cv2.polylines(m, [pts], False, 1.0, thickness=2, lineType=cv2.LINE_AA)
        inten = np.maximum(inten, m)
        colmap += m[..., None] * col
    out = _bloom(inten, colmap, glow_sigma=G * 0.010, core_pow=1.2)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_circuit_city(shape, seed=7, traces=120):
    """Glowing PCB / circuit city: Manhattan-routed neon TRACES (90-degree turns) with via DOTS and
    pads — a cyberpunk motherboard lit from within. Dense fine traces, full-canvas."""
    h, w = shape
    G = 760
    r = _rng(seed * 5 + 1)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    base_cols = [NEON["cyan"], NEON["lime"], NEON["green"], NEON["blue"]]
    for _ in range(traces):
        col = np.array(base_cols[int(r.integers(0, len(base_cols)))], np.float32)
        x, y = int(r.integers(0, G)), int(r.integers(0, G))
        m = np.zeros((G, G), np.float32)
        for _seg in range(int(r.integers(2, 6))):
            horiz = r.random() < 0.5
            ln = int(r.integers(20, 130))
            nx = int(np.clip(x + (ln if r.random() < 0.5 else -ln), 0, G - 1)) if horiz else x
            ny = y if horiz else int(np.clip(y + (ln if r.random() < 0.5 else -ln), 0, G - 1))
            cv2.line(m, (x, y), (nx, ny), 1.0, thickness=1, lineType=cv2.LINE_AA)
            x, y = nx, ny
            if r.random() < 0.5:
                cv2.circle(m, (x, y), 2, 1.0, -1)               # via pad
        inten = np.maximum(inten, m)
        colmap += m[..., None] * col
    out = _bloom(inten, colmap, glow_sigma=G * 0.006, core_pow=1.4)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_laser_web(shape, seed=7, beams=46):
    """LASER WEB: many straight neon BEAMS crossing at all angles with brilliant nodes where they
    intersect (the crossings bloom brightest). A taut light-grid, full-canvas + fine."""
    h, w = shape
    G = 760
    r = _rng(seed * 7 + 1)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    for _ in range(beams):
        col = np.array(NEON[_NEON_KEYS[int(r.integers(0, len(_NEON_KEYS)))]], np.float32)
        ang = r.random() * np.pi
        c = r.random() * G
        x0 = int(c + np.cos(ang) * G); y0 = int(np.sin(ang) * 0 - 50)
        # draw a long beam across the canvas through a random point at a random angle
        px, py = r.random() * G, r.random() * G
        dx, dy = np.cos(ang), np.sin(ang)
        a = (int(px - dx * G * 1.5), int(py - dy * G * 1.5))
        b = (int(px + dx * G * 1.5), int(py + dy * G * 1.5))
        m = np.zeros((G, G), np.float32)
        cv2.line(m, a, b, 1.0, thickness=1, lineType=cv2.LINE_AA)
        inten = inten + m                                       # ADD: crossings accumulate -> bright nodes
        colmap += m[..., None] * col
    nodes = np.clip(inten - 1.2, 0, None)                       # where >=2 beams cross
    out = _bloom(_norm(inten) + nodes, colmap, glow_sigma=G * 0.007, core_pow=1.0)
    # extra white pop at the nodes
    out = np.clip(out + cv2.GaussianBlur(nodes, (0, 0), G * 0.004)[..., None] * 0.9, 0, 1)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_rain(shape, seed=7, drops=300):
    """NEON RAIN (Blade Runner): falling streaks of coloured light, thin + bright, with a wet-street
    REFLECTION glow smeared along the bottom. Dense vertical light-rain, full-canvas + fine."""
    h, w = shape
    G = 760
    r = _rng(seed * 11 + 1)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    for _ in range(drops):
        col = NEON[_NEON_KEYS[int(r.integers(0, len(_NEON_KEYS)))]]
        x = int(r.random() * G)
        y0 = int(r.random() * G)
        ln = int((0.06 + 0.42 * r.random()) * G)
        lean = int((r.random() - 0.5) * 6)
        # draw DIRECTLY onto the buffers (no per-line temp/np.maximum — ~4x faster)
        cv2.line(inten, (x, y0), (x + lean, min(G - 1, y0 + ln)), 1.0, 1, cv2.LINE_AA)
        cv2.line(colmap, (x, y0), (x + lean, min(G - 1, y0 + ln)), tuple(col), 1, cv2.LINE_AA)
    # wet-street reflection: mirror the lower streaks + horizontal smear in the bottom fifth
    refl = np.zeros_like(inten)
    refl[int(G * 0.8):] = cv2.GaussianBlur(inten[int(G * 0.8):][::-1], (0, 0), 5)[::-1] * 0.5
    rcol = np.zeros_like(colmap)
    rcol[int(G * 0.8):] = cv2.GaussianBlur(colmap[int(G * 0.8):][::-1], (0, 0), 5)[::-1] * 0.5
    inten = np.maximum(inten, refl)
    colmap = colmap + rcol
    out = _bloom(inten, colmap, glow_sigma=G * 0.007, core_pow=1.3)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_blacklight_splatter(shape, seed=7, blobs=95):
    """BLACKLIGHT SPLATTER: UV-reactive paint splatter — glowing blobs with drip tails + a fine
    SPRAY of micro-specks, over a faint UV-violet haze. Organic full-canvas splatter, crushed-fine."""
    h, w = shape
    G = 760
    r = _rng(seed * 13 + 1)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    for _ in range(blobs):
        col = np.array(NEON[_NEON_KEYS[int(r.integers(0, len(_NEON_KEYS)))]], np.float32)
        cx, cy = int(r.random() * G), int(r.random() * G)
        rad = int((0.004 + 0.05 * r.random()) * G)
        m = np.zeros((G, G), np.float32)
        cv2.circle(m, (cx, cy), max(1, rad), 1.0, -1)
        if r.random() < 0.55:                                   # drip tail
            cv2.line(m, (cx, cy), (cx + int((r.random() - 0.5) * 30), cy + int(12 + 50 * r.random())),
                     1.0, max(1, rad // 2), cv2.LINE_AA)
        inten = np.maximum(inten, m)
        colmap += m[..., None] * col
    spray = (r.random((G, G)) < 0.006).astype(np.float32)       # fine micro-spray
    scol = np.array(NEON["lime"], np.float32) * 0.6 + np.array(NEON["cyan"], np.float32) * 0.4
    colmap += spray[..., None] * scol
    # COLOUR-FORWARD composite (no white core — the paint blobs keep their neon hue), + coloured bloom
    glow = cv2.GaussianBlur(colmap, (0, 0), G * 0.012)
    out = np.clip(colmap * 0.95 + glow * 1.2, 0, 1)
    out = np.clip(out + spray[..., None] * 0.55, 0, 1)          # tiny white-ish spray glints only
    haze = (1.0 - _norm(cv2.GaussianBlur(inten, (0, 0), G * 0.02)))[..., None] * np.array([0.05, 0.0, 0.10], np.float32)
    return cv2.resize(np.clip(out + haze, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)


def neon_wireframe(shape, seed=7, nodes=150):
    """NEON WIREFRAME: a glowing k-nearest mesh NET — scattered nodes joined to their neighbours by
    bright edges with glowing vertex dots, like a holographic wireframe. Connected polygonal net,
    distinct from random crossing beams (laser_web). Full-canvas + fine."""
    h, w = shape
    G = 760
    r = _rng(seed * 17 + 1)
    pts = np.column_stack([r.integers(0, G, nodes), r.integers(0, G, nodes)]).astype(np.int32)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    try:
        from scipy.spatial import cKDTree
        tree = cKDTree(pts)
        nbr = [tree.query(p, k=6)[1] for p in pts]
    except Exception:
        nbr = [list(range(max(0, i - 3), i)) + list(range(i + 1, min(nodes, i + 4))) for i in range(nodes)]
    drawn = set()
    for i, idxs in enumerate(nbr):
        col = np.array(NEON[_NEON_KEYS[i % len(_NEON_KEYS)]], np.float32)
        for j in np.atleast_1d(idxs):
            j = int(j)
            if j == i or (min(i, j), max(i, j)) in drawn:
                continue
            drawn.add((min(i, j), max(i, j)))
            # draw directly onto the buffers (no per-edge full-canvas mask + np.maximum) -> fast
            cv2.line(inten, tuple(pts[i]), tuple(pts[j]), 1.0, 1, cv2.LINE_AA)
            cv2.line(colmap, tuple(pts[i]), tuple(pts[j]), tuple(col.tolist()), 1, cv2.LINE_AA)
    for i, p in enumerate(pts):                                  # vertex glow dots
        col = np.array(NEON[_NEON_KEYS[i % len(_NEON_KEYS)]], np.float32)
        cv2.circle(inten, tuple(p), 2, 1.0, -1)
        cv2.circle(colmap, tuple(p), 2, tuple(col.tolist()), -1)
    out = _bloom(inten, colmap, glow_sigma=G * 0.0075, core_pow=1.1)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_plasma_tubes(shape, seed=7, bolts=80):
    """PLASMA GLOBE: branching electric TENDRILS that curve and fork through the dark like a plasma
    ball's filaments, glowing in neon. Curvy branch topology, distinct from straight beams / mesh."""
    h, w = shape
    G = 760
    r = _rng(seed * 19 + 1)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    stack = [(r.random() * G, r.random() * G, r.random() * 2 * np.pi,
              NEON[_NEON_KEYS[int(r.integers(0, len(_NEON_KEYS)))]], int(30 + 70 * r.random()))
             for _ in range(bolts)]
    segs = 0
    while stack and segs < 9000:
        x, y, ang, col, life = stack.pop()
        for _t in range(life):
            ang += (r.random() - 0.5) * 0.6
            nx, ny = x + np.cos(ang) * 4.0, y + np.sin(ang) * 4.0
            cv2.line(inten, (int(x), int(y)), (int(nx), int(ny)), 1.0, 1, cv2.LINE_AA)
            cv2.line(colmap, (int(x), int(y)), (int(nx), int(ny)), tuple(col), 1, cv2.LINE_AA)
            x, y = nx, ny; segs += 1
            if not (0 <= x < G and 0 <= y < G):
                break
            if r.random() < 0.04 and life > 12 and len(stack) < 400:
                stack.append((x, y, ang + (r.random() - 0.5) * 1.6, col, life // 2))
    out = _bloom(inten, colmap, glow_sigma=G * 0.0075, core_pow=1.1)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_hex_grid(shape, seed=7, cols=20):
    """NEON HONEYCOMB: a glowing hexagonal grid — bright neon cell EDGES on black, hue drifting
    across cells, with a low-freq brightness pulse so some cells blaze. Full-canvas hex net, fine."""
    h, w = shape
    G = 760
    r = _rng(seed * 23 + 1)
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    s = G / cols
    rad = s * 0.62
    pulse = _fbm((cols + 4, cols + 4), seed * 23 + 5, octaves=3, freq=3)
    for j in range(-1, cols + 2):
        for i in range(-1, cols + 2):
            cx = i * s + (s * 0.5 if j % 2 else 0.0)
            cy = j * s * 0.866
            hexpts = np.array([[cx + rad * np.cos(a), cy + rad * np.sin(a)]
                               for a in np.linspace(0, 2 * np.pi, 7) + np.pi / 6], np.int32)
            col = np.array(NEON[_NEON_KEYS[(i * 3 + j * 5) % len(_NEON_KEYS)]], np.float32)
            br = 0.45 + 0.85 * float(pulse[np.clip(j + 1, 0, cols + 3), np.clip(i + 1, 0, cols + 3)])
            cv2.polylines(inten, [hexpts], True, float(min(1.0, br)), 1, cv2.LINE_AA)
            cv2.polylines(colmap, [hexpts], True, tuple((col * min(1.0, br)).tolist()), 1, cv2.LINE_AA)
    out = _bloom(inten, colmap, glow_sigma=G * 0.006, core_pow=1.3)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_flow_tubes(shape, seed=7, tubes=90, steps=110):
    """FLOW TUBES: smooth glowing neon PIPES streaming along a curl-noise flow (laminar, bending
    organically) — distinct from the zigzag sign tubes (these are smooth streamlines). Full-canvas."""
    h, w = shape
    G = 720
    r = _rng(seed * 29 + 1)
    pot = _fbm((G, G), seed * 29 + 2, octaves=4, freq=3.0)
    gy, gx = np.gradient(pot)
    vx, vy = gy, -gx                                            # curl flow
    mag = np.sqrt(vx * vx + vy * vy) + 1e-6
    vx, vy = vx / mag, vy / mag
    inten = np.zeros((G, G), np.float32)
    colmap = np.zeros((G, G, 3), np.float32)
    for _ in range(tubes):
        x, y = r.random() * G, r.random() * G
        col = NEON[_NEON_KEYS[int(r.integers(0, len(_NEON_KEYS)))]]
        for _t in range(steps):
            ix, iy = int(np.clip(x, 0, G - 1)), int(np.clip(y, 0, G - 1))
            nx, ny = x + vx[iy, ix] * 3.0, y + vy[iy, ix] * 3.0
            cv2.line(inten, (int(x), int(y)), (int(nx), int(ny)), 1.0, 1, cv2.LINE_AA)
            cv2.line(colmap, (int(x), int(y)), (int(nx), int(ny)), tuple(col), 1, cv2.LINE_AA)
            x, y = nx, ny
            if not (0 <= x < G and 0 <= y < G):
                break
    out = _bloom(inten, colmap, glow_sigma=G * 0.008, core_pow=1.2)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def neon_synthwave_sun(shape, seed=7):
    """SYNTHWAVE SUN: a glowing gradient sun (magenta->yellow) sliced by horizontal slat gaps, over
    a neon perspective horizon GRID — the retro/vaporwave icon, with a starfield fill for coverage."""
    h, w = shape
    G = 760
    yy, xx = np.mgrid[0:G, 0:G].astype(np.float32)
    xn, yn = xx / G, yy / G
    r = _rng(seed * 31 + 1)
    cx, cy = 0.5, 0.42
    rad = np.sqrt((xn - cx) ** 2 + (yn - cy) ** 2) * 2.0
    sun = np.clip(1.0 - rad / 0.55, 0, 1)
    t = np.clip((yn - (cy - 0.27)) / 0.54, 0, 1)                # vertical position within sun -> hue
    sun_rgb = np.stack([1.0 * np.ones_like(t), 0.15 + 0.8 * t, 0.55 * (1 - t) + 0.05], 2)  # magenta->yellow
    slats = (np.sin((yn) * 60.0 * np.pi) > -0.2).astype(np.float32)
    slats = np.clip(slats + (yn < cy).astype(np.float32), 0, 1)  # only slice the lower half of the sun
    sun_img = sun_rgb * (sun * slats)[..., None]
    horizon = cy + 0.18
    below = yn > horizon
    # --- VAPORWAVE SKY (fills the upper canvas so there are NO dead-black corners) ---
    sky_t = np.clip((horizon - yn) / max(horizon, 1e-3), 0, 1)    # 1 at top edge, 0 at horizon
    top_c = np.array([0.06, 0.02, 0.16], np.float32)             # deep indigo (top)
    hor_c = np.array([0.45, 0.06, 0.42], np.float32)             # magenta glow (at horizon)
    sky = (hor_c[None, None, :] * (1 - sky_t)[..., None] + top_c[None, None, :] * sky_t[..., None])
    sky = sky * (~below)[..., None]
    horizon_glow = np.exp(-((yn - horizon) ** 2) / (2 * 0.012 ** 2))[..., None] * np.array([0.9, 0.3, 0.8], np.float32)
    # --- GROUND: deep-purple plane fading down + the bright perspective grid (fills lower canvas) ---
    gnd_t = np.clip((yn - horizon) / max(1 - horizon, 1e-3), 0, 1)
    ground = np.array([0.18, 0.03, 0.22], np.float32)[None, None, :] * (0.5 + 0.5 * (1 - gnd_t))[..., None] * below[..., None]
    vstep = np.abs(((xn - 0.5) / np.maximum(yn - horizon, 1e-3)) % 0.5 - 0.25)
    hstep = np.abs((1.0 / np.maximum(yn - horizon, 1e-3)) % 0.6 - 0.3)
    grid = (np.clip(0.02 - np.minimum(vstep, hstep), 0, 1) * 48.0) * below
    gcol = np.array([0.25, 0.95, 1.0], np.float32)
    stars = (r.random((G, G)) < 0.010).astype(np.float32) * (~below)   # denser starfield, full sky
    out = sky + horizon_glow + ground + sun_img * 1.1 + grid[..., None] * gcol + stars[..., None] * 0.9
    out = np.clip(out + cv2.GaussianBlur(np.clip(out, 0, 1), (0, 0), G * 0.006) * 0.55, 0, 1)
    return cv2.resize(out.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


NEON_STRUCTURES = {
    "sign_tubes":          neon_sign_tubes,
    "circuit_city":        neon_circuit_city,
    "laser_web":           neon_laser_web,
    "rain":                neon_rain,
    "blacklight_splatter": neon_blacklight_splatter,
    "wireframe":           neon_wireframe,
    "plasma_tubes":        neon_plasma_tubes,
    "hex_grid":            neon_hex_grid,
    "flow_tubes":          neon_flow_tubes,
    "synthwave_sun":       neon_synthwave_sun,
}
