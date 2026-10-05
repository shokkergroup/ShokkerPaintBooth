"""FLAME MATH ENGINE (2026-06-18) — procedural fire that actually looks like fire.

The old flame_* finishes were flat gradients/noise. Real flames need: a RISING temperature
field, TURBULENT domain-warped edges (licking tongues), multi-scale flicker, and a physically
plausible BLACKBODY color ramp (dark smoke tips → deep red → orange → yellow → white-blue core).

This module is the foundation the flames project builds on (target ~50 flame functions/looks).
Self-contained (numpy + cv2), deterministic per seed. Each `flame_*` returns an HxWx3 float 0..1
paint. UV-agnostic variants (radial / multi-source) included so flames read on scattered car panels.
"""
from __future__ import annotations
import numpy as np
import cv2


# ---------------------------------------------------------------- noise core
def _rng(seed):
    return np.random.default_rng(int(seed) & 0x7FFFFFFF)


def _vnoise(shape, freq, seed):
    """Smooth value noise at ~freq cells, bilinearly upsampled to shape."""
    h, w = shape
    gh, gw = max(2, int(freq)), max(2, int(round(freq * w / max(1, h))))
    g = _rng(seed).random((gh, gw)).astype(np.float32)
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)


def _fbm(shape, seed, octaves=5, freq=4.0, persistence=0.55):
    out = np.zeros(shape, np.float32)
    amp = 1.0; tot = 0.0; f = freq
    for o in range(octaves):
        out += amp * _vnoise(shape, f, seed * 131 + o * 17)
        tot += amp; amp *= persistence; f *= 2.0
    out /= max(tot, 1e-6)
    return out


def _norm(a):
    mn, mx = float(a.min()), float(a.max())
    return (a - mn) / (mx - mn) if mx - mn > 1e-6 else np.zeros_like(a)


# ---------------------------------------------------------------- color ramp
# Blackbody-ish fire ramp: control colors from cold tip -> hot core (0..1).
_FIRE_STOPS = [
    (0.00, (0.02, 0.01, 0.02)),   # near-black smoke
    (0.18, (0.35, 0.03, 0.01)),   # deep red
    (0.40, (0.85, 0.16, 0.02)),   # red-orange
    (0.62, (1.00, 0.45, 0.05)),   # orange
    (0.80, (1.00, 0.80, 0.22)),   # yellow
    (0.93, (1.00, 0.97, 0.80)),   # near-white
    (1.00, (0.85, 0.92, 1.00)),   # blue-white hottest
]


def _ramp(t, stops):
    t = np.clip(t, 0.0, 1.0)
    out = np.zeros(t.shape + (3,), np.float32)
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]; t1, c1 = stops[i + 1]
        m = (t >= t0) & (t <= t1)
        if not np.any(m):
            continue
        f = (t[m] - t0) / max(t1 - t0, 1e-6)
        for ch in range(3):
            out[m, ch] = c0[ch] + (c1[ch] - c0[ch]) * f
    out[t <= stops[0][0]] = stops[0][1]
    out[t >= stops[-1][0]] = stops[-1][1]
    return out


def recolor(t, lo, hi, mid=None):
    """Two/three-stop ramp for colored flames (blue, green, etc.)."""
    stops = [(0.0, (0.01, 0.01, 0.02)), (0.25, tuple(c * 0.4 for c in lo)), (0.55, lo)]
    if mid:
        stops.append((0.78, mid))
    stops += [(0.9, hi), (1.0, (1.0, 1.0, 1.0))]
    return _ramp(t, stops)


# ---------------------------------------------------------------- flame field
def flame_field(shape, seed, *, rise=1.0, turb=1.0, tongues=1.4, gamma=1.15):
    """Core RISING turbulent flame temperature field, 0..1 (hot=1).

    yy=0 bottom..1 top. Fuel is hot at the base; domain-warp + upward advection make plumes
    rise, narrow and flicker; vertical 'tongue' ridges give licking edges that taper with height.
    """
    h, w = shape
    yy = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)  # 1 bottom
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :] * np.ones((h, 1), np.float32)

    # turbulent domain warp (stronger higher up = more chaotic tips)
    wx = (_fbm((h, w), seed * 3 + 1, freq=3) - 0.5) * 0.18 * turb * (0.3 + 0.7 * (1 - yy))
    wy = (_fbm((h, w), seed * 3 + 2, freq=3) - 0.5) * 0.12 * turb
    yw = np.clip(yy + wy + 0.35 * rise * (1 - yy), 0.0, 1.4)   # advect upward
    xw = xx + wx

    # fuel: hot base decaying upward, modulated by warped turbulence
    base = np.clip(1.25 * yw - 0.15, 0.0, 1.2)
    tex = _fbm((h, w), seed * 5 + 7, octaves=6, freq=5)
    tex = cv2.remap(tex, (xw * (w - 1)).astype(np.float32), ((1 - yw / 1.4) * (h - 1)).astype(np.float32),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # vertical licking tongues (ridged), tapering toward the top
    ridge = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 7 + 3, octaves=4, freq=7) - 1.0)
    ridge = np.power(np.clip(ridge, 0, 1), 1.6) * tongues * (0.25 + 0.75 * yw / 1.4)

    temp = base * (0.45 + 0.85 * tex) + ridge * 0.5
    temp = temp * np.clip(1.15 - 0.55 * (1 - yw / 1.4), 0.2, 1.2)   # cool the tips
    temp = _norm(temp)
    return np.power(temp, gamma).astype(np.float32)


# ---------------------------------------------------------------- flames (batch 1)
def _flame_tongue_field(shape, seed, *, tongue_freq=5.0, sway=0.22, taper=0.18,
                        flicker=1.0, base=0.0):
    """RISING TONGUE field — discrete flames licking up from a base, DARK between/above them.

    yb: 1 at top row, 0 at bottom. Flame fills from the bottom up to a per-column tip height
    y_top(x) (medium-freq → several tongues across the width); soft wispy tip over `taper`;
    hot at the base, cooler toward the tip; x is warped more toward the top so tongues lick
    sideways; ridged vertical streaks add licking detail. `base` keeps a hot floor band.
    """
    h, w = shape
    yb = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)  # 1 top, 0 bottom
    xx = (np.arange(w, dtype=np.float32) / max(1, w - 1))[None, :] * np.ones((h, 1), np.float32)
    # sway grows toward the top (flames lick)
    swn = _fbm((h, w), seed * 3 + 1, octaves=4, freq=3) - 0.5
    xw = np.clip(xx + sway * swn * (0.15 + 0.95 * yb), 0.0, 1.0)
    # per-column tip height (tongues) — medium freq + finer sub-tongues, warped by xw
    top = 0.70 * _fbm((h, w), seed * 5 + 2, octaves=4, freq=tongue_freq) \
        + 0.30 * _fbm((h, w), seed * 5 + 9, octaves=3, freq=tongue_freq * 2.3)
    # shift the tip field by the sway so tongues bend with their lean
    top = cv2.remap(top.astype(np.float32), (xw * (w - 1)).astype(np.float32),
                    (np.arange(h, dtype=np.float32)[:, None] * np.ones((1, w))).astype(np.float32),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    y_top = np.clip(0.33 + 0.62 * top, 0.05, 0.99)
    body = np.clip((y_top - yb) / max(taper, 1e-3), 0.0, 1.0)          # 1 inside, soft at tip, 0 above
    body = np.maximum(body, np.clip((base - yb) / 0.12, 0.0, 1.0))      # optional hot floor band
    hot = np.clip(1.15 - 0.95 * yb, 0.18, 1.15)                         # hot base, cool tip
    turb = _fbm((h, w), seed * 7 + 3, octaves=5, freq=9)
    flick = 0.50 + 0.95 * flicker * turb
    streak = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 11 + 4, octaves=3, freq=tongue_freq * 1.6) - 1.0)
    temp = body * hot * flick * (0.55 + 0.55 * np.power(np.clip(streak, 0, 1), 1.3))
    # CRUSHED licking filaments — thin bright vertical ridges inside the tongues (fine-detail mandate)
    fine = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 11 + 8, octaves=2, freq=tongue_freq * 9.0) - 1.0)
    fine = np.power(np.clip(fine, 0, 1), 2.2)                           # sharpen to thin filaments
    temp = temp * (0.72 + 0.50 * fine) + 0.22 * temp * fine            # brighten the filament cores
    return _norm(np.clip(temp, 0.0, 2.0)).astype(np.float32)


def flame_classic(shape, seed=7):
    return _ramp(_flame_tongue_field(shape, seed), _FIRE_STOPS)


def flame_inferno(shape, seed=7):
    t = _flame_tongue_field(shape, seed, tongue_freq=4.0, sway=0.28, taper=0.24, flicker=1.3, base=0.12)
    return _ramp(np.clip(t * 1.15, 0, 1), _FIRE_STOPS)


def flame_blue(shape, seed=7):
    t = _flame_tongue_field(shape, seed, tongue_freq=6.0, sway=0.18)
    return recolor(t, (0.10, 0.35, 1.0), (0.75, 0.92, 1.0), mid=(0.2, 0.7, 1.0))


def flame_green_toxic(shape, seed=7):
    t = _flame_tongue_field(shape, seed, tongue_freq=5.5, sway=0.24)
    return recolor(t, (0.20, 0.85, 0.10), (0.85, 1.0, 0.5), mid=(0.5, 1.0, 0.2))


def flame_ember(shape, seed=7):
    """Cooler, lower licks — dying fire: short tongues, mostly deep-red with hot base."""
    t = _flame_tongue_field(shape, seed, tongue_freq=7.0, sway=0.14, taper=0.12, flicker=0.8)
    return _ramp(np.power(t, 1.35) * 0.82, _FIRE_STOPS)


# ============================================================ UNIQUENESS GATE
# HARDCODED MANDATE (owner 2026-06-18): no two flame STRUCTURES may exceed 80% similarity.
# Similarity is COLOR-INDEPENDENT (structure only) so recoloring the same field does NOT count
# as a new flame. Every new flame structure must pass assert_distinct() before it ships.
MAX_STRUCT_SIMILARITY = 0.80


def _struct_vec(x):
    g = x.mean(2) if (hasattr(x, "ndim") and x.ndim == 3) else np.asarray(x, np.float32)
    g = cv2.resize(g.astype(np.float32), (48, 48), interpolation=cv2.INTER_AREA)
    g = (g - g.mean()) / (g.std() + 1e-6)
    return g.ravel()


def structural_similarity(a, b):
    """Color-independent structural similarity in [0,1] (|correlation| of normalized luma)."""
    return abs(float(np.corrcoef(_struct_vec(a), _struct_vec(b))[0, 1]))


def assert_distinct(new_img, others, names=None, label="flame"):
    """Raise if `new_img` is >MAX_STRUCT_SIMILARITY similar to any in `others`. Returns max sim."""
    worst, who = 0.0, None
    for i, o in enumerate(others):
        s = structural_similarity(new_img, o)
        if s > worst:
            worst, who = s, (names[i] if names else i)
    if worst > MAX_STRUCT_SIMILARITY:
        raise ValueError(f"[uniqueness] {label} too similar ({worst:.2f}) to {who} — redesign the MATH, not the palette")
    return worst


# ============================================================ COVERAGE + FINE-DETAIL GATE
# HARDCODED MANDATE (owner 2026-06-18): full-canvas COVERAGE and crushed FINE DETAIL are the
# DEFAULT for every structure — no dead corners, no lonely centered motif, no smooth boring blobs.
# A structure may opt OUT only with a DOCUMENTED design reason (the owner: "there WILL be cases
# where it's not [covered/crushed]"). Those reasons live in the exempt dicts below — adding a name
# there is a deliberate, reviewable act, not a silent escape hatch.
MIN_COVERAGE = 0.60      # >= this fraction of an 8x8 grid must carry real signal (no dead regions)
MIN_FINENESS = 0.15      # >= this high-frequency-energy ratio (crushed detail, not a smooth blob)

# name -> WHY it is intentionally not full-canvas (a single motif / directional / annular look)
COVERAGE_EXEMPT = {
    "candle":      "a single upright flame is intentionally a lone centered motif",
    "will_o_wisp": "sparse drifting orbs — the empty dark between wisps IS the look",
    "dragon_jet":  "a directional jet from one side leaves cool space ahead of the cone",
    "gas_ring":    "an annular burner ring is a single ring motif (dark hub + corners by design)",
    "eruption_column": "a single volcanic plume rising up the center leaves cool sky at the sides",
    "fire_rose":       "a single centered bloom — dark corners are intrinsic to the rosette (cf. candle)",
    "fire_tornado":    "a single twisting funnel column leaves cool space at the sides (cf. eruption_column)",
}
# name -> WHY it is intentionally smooth/low-frequency (a soft glow is the look)
FINE_DETAIL_EXEMPT = {
    "radial":          "a smooth radiating fireball is intentionally low-frequency",
    "metaball_plumes": "soft billowing plumes are intentionally smooth",
    "will_o_wisp":     "soft glowing orbs are intentionally smooth",
    "candle":          "a single smooth flame body is intentionally low-frequency",
}


def _luma(img):
    a = np.asarray(img, np.float32)
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114 if a.ndim == 3 else a


def coverage_score(img, grid=8, floor=0.18):
    """Fraction of an 8x8 grid whose 99th-percentile luma clears `floor` — i.e. how many regions
    carry ANY real flame. High = signal spread across the whole canvas; low = a lonely motif with
    dead corners. Uses a high percentile (not the mean) so sparse-but-spread structures (an ember
    shower) read as covered, while a centered blob with dark corners does not."""
    L = _luma(img)
    h, w = L.shape
    ch, cw = h // grid, w // grid
    c = L[:ch * grid, :cw * grid].reshape(grid, ch, grid, cw)
    cellp = np.percentile(c, 99, axis=(1, 3))
    return float((cellp > floor).mean())


def fineness_score(img):
    """High-frequency-energy ratio (crushed detail vs smooth blob): RMS of the S/64 high-pass
    over RMS of the signal, measured on the LIT region so a mostly-dark fire field is judged on
    its flames, not its background. High = busy/crushed; low = a smooth gradient or fat blob."""
    L = _luma(img)
    lit = L > max(0.04, 0.18 * float(L.max()))
    if lit.sum() < 16:
        return 0.0
    blur = cv2.GaussianBlur(L, (0, 0), max(1.0, L.shape[0] / 64.0))
    detail = L - blur
    return float(np.sqrt((detail[lit] ** 2).mean()) / (np.sqrt((L[lit] ** 2).mean()) + 1e-6))


# ============================================================ DISTINCT GENERATORS
# Each is a DIFFERENT generative algorithm (not the tongue field recolored).
def flame_cellular_embers(shape, seed=7, n=150):
    """Ember BED — glowing coals via a Worley/distance field (cellular), hot at the base.
    Structure: blobby cells, NOT rising tongues."""
    h, w = shape
    r = _rng(seed * 13 + 1)
    pts = np.ones((h, w), np.uint8)
    pts[r.integers(0, h, n), r.integers(0, w, n)] = 0
    dist = cv2.distanceTransform(pts, cv2.DIST_L2, 3)
    dist /= (dist.max() + 1e-6)
    emb = np.exp(-dist * 8.5)                                   # glow pooled at coals
    emb = 0.7 * emb + 0.3 * _fbm((h, w), seed * 13 + 5, freq=10)  # crackle detail
    yb = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
    hot = np.clip(1.15 - 0.85 * yb, 0.22, 1.15)                 # hotter low (bed)
    t = _norm(emb * hot * (0.5 + 0.8 * _fbm((h, w), seed * 13 + 7, freq=7)))
    return _ramp(np.power(t, 1.1), _FIRE_STOPS)


def flame_curl_streamers(shape, seed=7, steps=16):
    """Licking STREAMERS — a hot base advected along a CURL-noise flow (biased upward).
    Structure: long curling filaments, NOT tongues or cells."""
    H, W = shape
    h, w = max(2, H // 2), max(2, W // 2)                     # advect at half-res then upsample (~4x faster, same look)
    pot = _fbm((h, w), seed * 17 + 2, octaves=5, freq=5.5)
    gy, gx = np.gradient(pot)
    vx, vy = gy, -gx                                           # pure CURL flow (swirls/vortices)
    mag = np.sqrt(vx * vx + vy * vy) + 1e-6
    vx, vy = vx / mag, vy / mag
    vy = vy - 0.25                                             # only a gentle upward drift, swirl-dominant
    # seed = SCATTERED hot sparks everywhere (not a bottom band) -> filaments curl across the frame
    spark = _fbm((h, w), seed * 17 + 1, octaves=3, freq=9)
    dens = np.clip((spark - 0.55) * 6.0, 0, 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cur = dens.copy(); acc = dens.copy()
    for _ in range(max(steps, 22)):                           # step 1.0 at half-res == 2.0 at full-res (length preserved)
        cur = cv2.remap(cur, (xx + vx * 1.0).astype(np.float32), (yy + vy * 1.0).astype(np.float32),
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0) * 0.94
        acc = np.maximum(acc, cur)
    acc = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(acc), _FIRE_STOPS)


def flame_radial(shape, seed=7):
    """UV-agnostic: a fireball radiating outward (no fixed 'up') — reads on any panel."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt(((yy - cy) / h) ** 2 + ((xx - cx) / w) ** 2) * 2.0
    warp = (_fbm((h, w), seed * 9 + 4, octaves=5, freq=6) - 0.5) * 0.5
    t = _norm(np.clip(1.15 - r + warp, 0, 2))
    t = t * (0.5 + 0.6 * _fbm((h, w), seed * 9 + 5, freq=7))
    return _ramp(_norm(t), _FIRE_STOPS)


# ============================================================ STRUCTURE REGISTRY
# DISTINCT flame structures only (one entry per ALGORITHM). Param/palette variants
# (flame_inferno/blue/green/ember = the tongue field re-tuned/recolored) do NOT belong here.
# The uniqueness gate-test (tests/regression_flame_uniqueness_test.py) enumerates THIS dict.
FLAME_STRUCTURES = {
    "tongues":         flame_classic,
    "cellular_embers": flame_cellular_embers,
    "curl_streamers":  flame_curl_streamers,
    "radial":          flame_radial,
}


# ============================================================ DISTINCT GENERATORS (batch 2)
def flame_vortex_spiral(shape, seed=7, arms=5, swirl=5.5):
    """Fire whirl — spiral arms winding into a hot core (log-spiral coords). Distinct geometry."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy, dx = (yy - h / 2) / h, (xx - w / 2) / w
    r = np.sqrt(dx * dx + dy * dy) * 2.0
    th = np.arctan2(dy, dx)
    noise = (_fbm((h, w), seed * 19 + 1, octaves=4, freq=5) - 0.5) * 4.0
    s = np.sin(arms * th + swirl * r * 6.2832 + noise)
    arm = np.power(np.clip(0.5 + 0.5 * s, 0, 1), 1.5)
    falloff = np.clip(1.2 - r, 0.0, 1.2)
    flick = 0.5 + 0.85 * _fbm((h, w), seed * 19 + 2, freq=7)
    return _ramp(_norm(arm * falloff * flick + 0.15 * falloff), _FIRE_STOPS)


def flame_dragon_jet(shape, seed=7):
    """Directional blasted JET — a turbulent cone roaring from the left, widening + cooling.
    Horizontal flow, NOT a vertical/centered structure."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xg, yg = xx / max(1, w - 1), yy / max(1, h - 1)
    center = 0.5 + (_fbm((h, w), seed * 23 + 1, octaves=4, freq=4) - 0.5) * 0.30 * (0.2 + xg)
    spread = 0.035 + 0.5 * xg
    core = np.exp(-((yg - center) / np.maximum(spread, 1e-3)) ** 2)
    decay = np.clip(1.18 - xg * 1.05, 0.08, 1.18)                 # hot at the nozzle (left)
    turb = 0.45 + 0.95 * _fbm((h, w), seed * 23 + 2, octaves=5, freq=8)
    # CRUSHED shear filaments streaming down the jet (fine-detail mandate)
    fil = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 23 + 6, octaves=2, freq=40.0) - 1.0)
    fil = np.power(np.clip(fil, 0, 1), 2.2)                       # thin bright shear lines
    turb = turb * (0.72 + 0.50 * fil) + 0.22 * turb * fil
    return _ramp(_norm(core * decay * turb), _FIRE_STOPS)


def flame_interference_wisps(shape, seed=7):
    """Ghostly overlapping WISPS via warped sinusoidal interference — thin bright fringes.
    Texture is fringe/moire-like, distinct from fields/cells/swirls/jets."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xx / max(1, w - 1), yy / max(1, h - 1)
    xw = xn + (_fbm((h, w), seed * 29 + 1, octaves=3, freq=3) - 0.5) * 0.45
    yw = yn + (_fbm((h, w), seed * 29 + 2, octaves=3, freq=3) - 0.5) * 0.45
    g = np.zeros((h, w), np.float32)
    for fx, fy, ph in [(9.0, 2.0, 0.0), (3.0, 11.0, 1.7), (7.0, 7.0, 3.1)]:
        g += np.sin((xw * fx + yw * fy) * 6.2832 + ph)
    fr = np.power(np.clip(1.0 - np.abs(g / 3.0), 0, 1), 3.0)       # thin fringes where waves cancel
    flick = 0.4 + 0.9 * _fbm((h, w), seed * 29 + 3, freq=8)
    return _ramp(_norm(fr * flick * (0.5 + 0.6 * _fbm((h, w), seed * 29 + 4, freq=4))), _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "vortex_spiral":      flame_vortex_spiral,
    "dragon_jet":         flame_dragon_jet,
    "interference_wisps": flame_interference_wisps,
})


# ============================================================ DISTINCT GENERATORS (batch 3)
def flame_metaball_plumes(shape, seed=7, n=13):
    """Rising soft FIREBALLS — vertically-stretched gaussian metaballs drifting up. Blobby plumes,
    distinct from the dense Worley ember-bed (fewer, larger, teardrop-stretched)."""
    h, w = shape
    r = _rng(seed * 31 + 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    field = np.zeros((h, w), np.float32)
    for _ in range(n):
        cx = r.random() * w
        cy = r.random() * h
        sx = (0.05 + 0.07 * r.random()) * w
        sy = sx * (1.7 + r.random())                              # stretch vertical -> plume
        field += np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) * 0.5)
    yb = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
    hot = np.clip(1.12 - 0.7 * yb, 0.2, 1.12)
    return _ramp(_norm(field * hot * (0.5 + 0.6 * _fbm((h, w), seed * 31 + 2, freq=7))), _FIRE_STOPS)


def flame_candle(shape, seed=7):
    """A SINGLE laminar candle flame — bright teardrop centered in a mostly-dark frame. Distinct:
    one flame, not a field of them."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn = (xx - w / 2) / w
    yb = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)  # 0 bottom..1 top
    sway = (_fbm((h, w), seed * 37 + 1, octaves=3, freq=4) - 0.5) * 0.06 * yb
    width = np.clip(0.13 * np.power(np.clip(0.92 - yb, 0, 1), 0.6), 1e-3, 1)   # narrows with height, caps ~0.92
    core = np.clip(1.0 - np.abs(xn - sway) / width, 0.0, 1.0)
    core *= np.clip((0.95 - yb) / 0.12, 0.0, 1.0)                  # soft tip cutoff near top
    hot = np.clip(1.1 - 0.55 * yb, 0.25, 1.1)
    flick = 0.8 + 0.3 * _fbm((h, w), seed * 37 + 2, freq=6)
    return _ramp(_norm(np.power(core, 1.2) * hot * flick), _FIRE_STOPS)


def flame_ember_storm(shape, seed=7, n=420, tail=26):
    """A storm of rising SPARKS — sparse points with upward motion-blur tails on near-black.
    Distinct: pinpoint streaks, very low coverage."""
    h, w = shape
    r = _rng(seed * 41 + 1)
    pts = np.zeros((h, w), np.float32)
    ys = r.integers(int(h * 0.15), h, n)
    xs = r.integers(0, w, n)
    pts[ys, xs] = 0.6 + 0.4 * r.random(n).astype(np.float32)
    acc = pts.copy()
    for k in range(1, tail):
        sh = np.zeros_like(pts)
        sh[:-k] = pts[k:]                                         # shift up by k rows
        acc = np.maximum(acc, sh * (1.0 - k / tail) ** 1.3)
    yb = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
    acc = acc * np.clip(1.05 - 0.5 * yb, 0.4, 1.05)               # hotter/brighter lower
    return _ramp(_norm(acc), _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "metaball_plumes": flame_metaball_plumes,
    "candle":          flame_candle,
    "ember_storm":     flame_ember_storm,
})


# ============================================================ DISTINCT GENERATORS (batch 4)
def flame_will_o_wisp(shape, seed=7, n=7):
    """A few isolated soft glowing ORBS with faint upward tails on near-black. Distinct: sparse,
    round, low-coverage (vs the frame-filling metaballs or pinpoint ember streaks)."""
    h, w = shape
    r = _rng(seed * 43 + 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    field = np.zeros((h, w), np.float32)
    for _ in range(n):
        cx, cy = r.random() * w, (0.2 + 0.7 * r.random()) * h
        sz = (0.035 + 0.05 * r.random()) * w
        field += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sz * sz)))
        tail = np.exp(-((xx - cx) ** 2) / (2 * (sz * 0.5) ** 2)) * \
            np.exp(-np.clip(cy - yy, 0, h) / (sz * 5.0)) * (yy < cy)
        field += 0.45 * tail
    return _ramp(_norm(field * (0.6 + 0.5 * _fbm((h, w), seed * 43 + 2, freq=6))), _FIRE_STOPS)


def flame_reaction_diffusion(shape, seed=7, iters=2400, gs=120):
    """CORAL-FIRE — Gray-Scott reaction-diffusion Turing pattern colored as fire. Organic
    LABYRINTH (worm regime f=0.039/k=0.058), unlike any field/blob/streak. cv2 laplacian = fast."""
    h, w = shape
    r = _rng(seed * 47 + 1)
    A = np.ones((gs, gs), np.float32)
    B = np.zeros((gs, gs), np.float32)
    # noisy seeding fills the grid so the maze develops everywhere (not isolated squares)
    B[:] = (r.random((gs, gs)).astype(np.float32) < 0.06).astype(np.float32)
    Da, Db, f, k = 0.19, 0.09, 0.030, 0.0565
    K = np.array([[0.05, 0.2, 0.05], [0.2, -1.0, 0.2], [0.05, 0.2, 0.05]], np.float32)
    for _ in range(iters):
        r2 = A * B * B
        A = np.clip(A + Da * cv2.filter2D(A, -1, K, borderType=cv2.BORDER_REFLECT) - r2 + f * (1 - A), 0.0, 1.0)
        B = np.clip(B + Db * cv2.filter2D(B, -1, K, borderType=cv2.BORDER_REFLECT) + r2 - (k + f) * B, 0.0, 1.0)
    pat = cv2.resize(_norm(B), (w, h), interpolation=cv2.INTER_CUBIC)
    return _ramp(_norm(np.power(np.clip(pat, 0, 1), 0.9) * (0.6 + 0.5 * _fbm((h, w), seed * 47 + 3, freq=6))), _FIRE_STOPS)


# (flame_firewall_wave dropped 2026-06-18 — the gate measured it 0.85 similar to `tongues`;
#  a wall-below-a-wavy-crest is structurally a tongue field. Will revisit with genuinely
#  different wave math, e.g. horizontal traveling-wave advection, not a recolor of this.)
FLAME_STRUCTURES.update({
    "will_o_wisp":        flame_will_o_wisp,
    "reaction_diffusion": flame_reaction_diffusion,
})


# ============================================================ DISTINCT GENERATORS (batch 5)
def flame_gas_ring(shape, seed=7, jets=26):
    """Burner RING — an annulus of small jet flames (stove-burner geometry). Distinct: a ring,
    not a field/blob/streak."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy, dx = (yy - h / 2) / h, (xx - w / 2) / w
    rr = np.sqrt(dx * dx + dy * dy) * 2.0
    th = np.arctan2(dy, dx)
    ring = np.exp(-((rr - 0.55) / 0.11) ** 2)                     # annulus
    jetmod = 0.45 + 0.55 * np.sin(th * jets + (_fbm((h, w), seed * 61 + 1, freq=4) - 0.5) * 3.0)
    flick = 0.55 + 0.7 * _fbm((h, w), seed * 61 + 2, freq=9)
    return _ramp(_norm(ring * jetmod * flick), _FIRE_STOPS)


def flame_plasma_arc(shape, seed=7, gen=420, roots=4):
    """Branching PLASMA ARCS (Lichtenberg-style electric fire) — crisp glowing branching
    filaments on a dark field (white-hot lines + dim halo, NOT a blown-out core).
    Distinct: tree/branch topology."""
    h, w = shape
    r = _rng(seed * 67 + 1)
    c = np.zeros((gen, gen), np.float32)
    # roots spread across the bottom so branches fill the canvas instead of clumping center
    walkers = [(gen * (0.12 + 0.76 * (i / max(1, roots - 1))) + (r.random() - 0.5) * gen * 0.08,
                gen - 1.0, (r.random() - 0.5) * 0.4, -1.0) for i in range(roots)]
    maxw = 110
    for _ in range(gen):
        nxt = []
        for (x, y, dx, dy) in walkers:
            dx += (r.random() - 0.5) * 0.65
            dy += (r.random() - 0.5) * 0.18 - 0.04
            n = (dx * dx + dy * dy) ** 0.5 + 1e-6
            dx, dy = dx / n, dy / n
            x2, y2 = x + dx * 2.0, y + dy * 2.0
            xi, yi = int(x2), int(y2)
            if 0 <= xi < gen and 0 <= yi < gen:
                c[yi, xi] = 1.0
                nxt.append((x2, y2, dx, dy))
                if r.random() < 0.038 and (len(nxt) + len(walkers)) < maxw:
                    nxt.append((x2, y2, -dy, dx))                 # perpendicular branch
        walkers = nxt
        if not walkers:
            break
    c = cv2.dilate(c, np.ones((2, 2), np.float32))
    glow = cv2.GaussianBlur(c, (0, 0), gen * 0.010)
    glow = glow / (glow.max() + 1e-6)
    # crisp white-hot lines (1.0) over a DIM orange halo (<=0.5) → reads as electric plasma
    field = np.maximum(c, 0.5 * glow)
    field = cv2.resize(np.clip(field, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "gas_ring":   flame_gas_ring,
    "plasma_arc": flame_plasma_arc,
})


# ---------------------------------------------------------------- batch 6
def flame_lava_flow(shape, seed=7, n=90):
    """Molten LAVA — a glowing crack NETWORK between cooled dark plates (Voronoi cell
    BOUNDARIES ignite, interiors stay crusty-dark). Inverse topology of cellular_embers
    (bright blobs); here the bright thing is the seam mesh."""
    h, w = shape
    r = _rng(seed * 23 + 3)
    pts = np.ones((h, w), np.uint8)
    pts[r.integers(0, h, n), r.integers(0, w, n)] = 0
    _, labels = cv2.distanceTransformWithLabels(pts, cv2.DIST_L2, 3)
    lab = labels.astype(np.int32)
    edge = np.zeros((h, w), np.float32)                          # nearest-seed label changes = Voronoi seams
    edge[:, :-1] += (lab[:, :-1] != lab[:, 1:])
    edge[:-1, :] += (lab[:-1, :] != lab[1:, :])
    edge = np.clip(edge, 0, 1)
    seam = _norm(cv2.GaussianBlur(cv2.dilate(edge, np.ones((2, 2), np.float32)), (0, 0), max(1.0, h * 0.0016)))
    heat = 0.45 + 0.85 * _fbm((h, w), seed * 23 + 7, freq=4)     # some cracks run hotter
    crust = 0.12 * _fbm((h, w), seed * 23 + 9, freq=9)           # faint crust embers in the plates
    t = _norm(seam * heat + crust * (1.0 - seam))
    return _ramp(np.power(t, 0.9), _FIRE_STOPS)


def flame_solar_flare(shape, seed=7, loops=9):
    """SOLAR FLARE — a bright stellar LIMB at the base throwing arcing prominence LOOPS
    that rise and curve back (smooth magnetic arcs, not jagged branches). Built at a fixed
    grid then resized so arc width is resolution-independent."""
    h, w = shape
    G = 512
    r = _rng(seed * 29 + 5)
    c = np.zeros((G, G), np.float32)
    for _ in range(loops):
        x0 = r.random() * G
        span = (0.14 + 0.40 * r.random()) * G
        x1 = np.clip(x0 + (span if r.random() < 0.5 else -span), 0, G - 1)
        ap = (0.35 + 0.55 * r.random()) * G                      # apex height of the loop
        t = np.linspace(0.0, 1.0, 600)
        xs = (x0 + (x1 - x0) * t).astype(np.int32)
        ys = ((G - 1) - ap * np.sin(np.pi * t)).astype(np.int32)
        m = (xs >= 0) & (xs < G) & (ys >= 0) & (ys < G)
        c[ys[m], xs[m]] = 1.0
    c = cv2.dilate(c, np.ones((2, 2), np.float32))
    glow = cv2.GaussianBlur(c, (0, 0), G * 0.006)
    glow = glow / (glow.max() + 1e-6)
    yb = np.linspace(0.0, 1.0, G, dtype=np.float32)[:, None] * np.ones((1, G), np.float32)
    limb = np.exp(-((1.0 - yb) / 0.09) ** 2)                     # hot chromosphere band at the base
    field = np.maximum(0.9 * limb, np.maximum(c, 0.55 * glow))
    field = field * (0.65 + 0.6 * _fbm((G, G), seed * 29 + 9, freq=6))
    field = cv2.resize(np.clip(field, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "lava_flow":   flame_lava_flow,
    "solar_flare": flame_solar_flare,
})


# ---------------------------------------------------------------- batch 7 (INVENTED math)
def flame_ferro_spikes(shape, seed=7):
    """FERROFLUID FIRE — a Rosensweig instability: molten fluid pulled into a self-organising
    field of sharp conical PEAKS on a hex-ish lattice, each peak white-hot at the tip.
    INVENTED: superpose 3 hex-rotated cosine lattices (a quasicrystal-ish peak field), warp the
    lattice with low-freq noise so it organises irregularly, then sharpen peaks with a power
    curve and ignite tips. Full-canvas spike bed, crushed fine ridges between peaks."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = xx / w, yy / h
    warp = (_fbm((h, w), seed * 43 + 1, octaves=3, freq=2.0) - 0.5) * 0.32
    px, py = nx + warp, ny + warp * 0.7
    k = 15.0                                                      # lattice frequency (peak density)
    lat = np.ones((h, w), np.float32)
    for a in (0.0, np.pi / 3.0, 2.0 * np.pi / 3.0):              # 3 hex-rotated wave families -> hex peak lattice
        lat *= (0.5 + 0.5 * np.cos((px * np.cos(a) + py * np.sin(a)) * k * 2.0 * np.pi))
    lat = _norm(lat)
    peaks = np.power(lat, 1.4)                                   # sharpen into conical spike tips
    ridge = 0.25 * _fbm((h, w), seed * 43 + 9, octaves=3, freq=14)  # crushed metal ridges between
    flick = 0.7 + 0.6 * _fbm((h, w), seed * 43 + 5, octaves=4, freq=8)
    t = _norm((peaks + ridge) * flick)
    return _ramp(np.power(t, 0.95), _FIRE_STOPS)


def flame_backdraft_rings(shape, seed=7, rings=6):
    """BACKDRAFT — concentric TURBULENT combustion shock fronts blasting outward from a hot
    core (omnidirectional, UV-agnostic). INVENTED: stack gaussian rings at growing radii with a
    noise-warped radius so the fronts buckle like a real expanding fireball, then chop them into
    combustion cells with angular flicker. Full-canvas; inner rings hottest."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    dy, dx = (yy - cy) / h, (xx - cx) / w
    r = np.sqrt(dx * dx + dy * dy) * 2.0
    wob = (_fbm((h, w), seed * 47 + 3, octaves=4, freq=3.0) - 0.5) * 0.45   # buckled fronts
    rr = r + wob
    field = np.zeros((h, w), np.float32)
    for i in range(rings):
        rad = 0.12 + i * (0.95 / rings)
        amp = 1.0 - 0.65 * (i / rings)                          # inner shells hotter
        field = np.maximum(field, amp * np.exp(-((rr - rad) / 0.05) ** 2))
    field *= (0.5 + 0.75 * _fbm((h, w), seed * 47 + 7, octaves=3, freq=9))  # combustion cells
    field += 0.30 * np.exp(-(rr / 0.11) ** 2)                   # white-hot core
    return _ramp(_norm(field), _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "ferro_spikes":    flame_ferro_spikes,
    "backdraft_rings": flame_backdraft_rings,
})


# ---------------------------------------------------------------- batch 8 (INVENTED math)
def flame_spark_fountain(shape, seed=7, sparks=440):
    """SPARK FOUNTAIN — molten sparks launched off a hot base on BALLISTIC parabolic arcs
    (gravity), fountaining up across the whole width and falling back, each trail fading as it
    cools. INVENTED: a tiny projectile sim — distinct from rising-ember fields (no trajectory),
    branch walks, and closed solar loops (these are open parabolas from many base points)."""
    h, w = shape
    G = 512
    r = _rng(seed * 53 + 2)
    c = np.zeros((G, G), np.float32)
    grav = 0.00040 * G                                            # weak gravity -> tall arcs that fill the frame
    for _ in range(sparks):
        ang = (-np.pi / 2) + (r.random() - 0.5) * 1.95            # mostly up, wide fan
        spd = (0.80 + 1.7 * r.random()) * G * 0.022               # fast -> apexes reach the top
        vx, vy = np.cos(ang) * spd, np.sin(ang) * spd
        x = r.random() * G                                        # emit all along the base -> full width
        y = G - 2.0
        life = int(140 + 260 * r.random())
        for t in range(life):
            xi, yi = int(x), int(y)
            if 0 <= xi < G and 0 <= yi < G:
                c[yi, xi] = max(c[yi, xi], 1.0 - t / life)        # trail cools along the arc
            x += vx; y += vy; vy += grav
            if y >= G or x < 0 or x >= G:
                break
    c = cv2.dilate(c, np.ones((2, 2), np.float32))
    glow = cv2.GaussianBlur(c, (0, 0), G * 0.006)
    glow = glow / (glow.max() + 1e-6)
    yb = np.linspace(0.0, 1.0, G, dtype=np.float32)[:, None] * np.ones((1, G), np.float32)
    base = np.exp(-((1.0 - yb) / 0.05) ** 2)                      # white-hot emission line at the base
    field = np.maximum(0.85 * base, np.maximum(c, 0.5 * glow))
    field = cv2.resize(np.clip(field, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


def flame_corona_rays(shape, seed=7, rays=64):
    """SOLAR CORONA — thin RADIAL streamers flaring out from a white-hot disk over a faint
    granular plasma (omnidirectional, UV-agnostic). INVENTED: a noise-perturbed angular comb
    (irregular ray spacing) modulated by a radial flare profile — distinct from the smooth
    fireball, the annular burner ring, and the concentric shock rings."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    dy, dx = (yy - cy) / h, (xx - cx) / w
    rad = np.sqrt(dx * dx + dy * dy) * 2.0
    th = np.arctan2(dy, dx)
    raymod = 0.5 + 0.5 * np.cos(th * rays + (_fbm((h, w), seed * 59 + 1, octaves=3, freq=2) - 0.5) * 7.0)
    streamers = np.power(np.clip(raymod, 0, 1), 4.0)              # thin rays
    falloff = np.exp(-rad * 1.15)                                 # flare out then fade
    core = np.exp(-(rad / 0.12) ** 2)                            # bright disk
    plasma = 0.22 * _fbm((h, w), seed * 59 + 3, octaves=4, freq=13)  # faint full-field granulation (coverage+fine)
    field = _norm(core + streamers * falloff * (0.55 + 0.85 * _fbm((h, w), seed * 59 + 5, freq=9)) + plasma)
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "spark_fountain": flame_spark_fountain,
    "corona_rays":    flame_corona_rays,
})


# ---------------------------------------------------------------- batch 9 (INVENTED math)
def flame_votive_field(shape, seed=7, billows=5):
    """VOTIVE FIELD — a full-canvas lattice of small glowing flame cores with cat's-eye swirl
    wisps, like a wall of votive flames. INVENTED from STACKED Stuart-vortex stream functions
    psi = log(cosh(Y) + A·cos(X)) (the Kelvin–Helmholtz shear solution) at several heights/phases:
    the vortex cores light up, the braids curl between them. Noise-warped, so no two cores match.
    Distinct from a single flame (candle), a continuous wall (tongues), spirals, and scattered curls."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn = xx / w
    Y = ((yy / h) - 0.5) * 9.0
    warp = (_fbm((h, w), seed * 67 + 1, octaves=3, freq=2.5) - 0.5) * 1.6
    Yw = Y + (_fbm((h, w), seed * 67 + 2, octaves=3, freq=2.0) - 0.5) * 1.1
    A = 0.85
    # STACK several shear layers up the canvas so billows roll top-to-bottom (full coverage)
    core = np.zeros((h, w), np.float32)
    for yc, bil, ph, amp in [(-3.0, billows, 0.0, 0.92), (-1.0, billows + 2, 1.7, 1.0),
                             (1.0, billows - 1, 3.0, 0.95), (3.0, billows + 1, 4.6, 0.9)]:
        X = xn * max(2, bil) * 2.0 * np.pi
        psi = np.log(np.cosh(Yw - yc) + A * np.cos(X + warp + ph) + 1e-2)  # Stuart-vortex streamlines
        core = np.maximum(core, amp * np.exp(-np.clip(psi, -3.0, 3.0) * 1.3))  # bright cores + braids
    flick = 0.6 + 0.7 * _fbm((h, w), seed * 67 + 5, octaves=4, freq=8)
    fil = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 67 + 7, octaves=2, freq=26.0) - 1.0)  # crushed detail
    t = _norm(_norm(core) * flick * (0.58 + 0.60 * np.power(np.clip(fil, 0, 1), 1.4)))
    return _ramp(t, _FIRE_STOPS)


# NOTE: a classic DOOM cellular-automaton fire was prototyped here and DROPPED — the gate measured
# it at 0.78 similarity to solar_flare (a near-duplicate bottom-bright fade) AND it failed both the
# coverage (0.12) and fineness (0.09, blurred by the small-grid→2048 resize) mandates. Per the
# owner rule, the MATH is dropped rather than forced. (Same call as firewall_wave in iter 7.)


FLAME_STRUCTURES.update({
    "votive_field": flame_votive_field,
})


# ---------------------------------------------------------------- batch 10 (INVENTED math)
def flame_meteor_shower(shape, seed=7, meteors=24):
    """METEOR SHOWER — a volley of parallel diagonal fireballs: white-hot heads with long tails
    that cool as they trail, over faint glowing dust. INVENTED: a stamped streak field with a
    head-bright→tail-faint gradient along each track. Distinct directional-streak topology (not
    parabolic fountains, not branch walks, not rising fields)."""
    h, w = shape
    G = 560
    r = _rng(seed * 73 + 1)
    c = np.zeros((G, G), np.float32)
    base_ang = -0.62                                              # shared shower direction
    for _ in range(meteors):
        L = int((0.28 + 0.55 * r.random()) * G)
        hx, hy = r.random() * G, r.random() * G
        a = base_ang + (r.random() - 0.5) * 0.22
        dx, dy = np.cos(a), np.sin(a)
        for t in range(L):
            x, y = int(hx - dx * t), int(hy - dy * t)             # tail trails behind the head
            if 0 <= x < G and 0 <= y < G:
                c[y, x] = max(c[y, x], 1.0 - t / L)
    head = cv2.GaussianBlur(np.power(c, 3.0), (0, 0), G * 0.004)  # bright pop at the hot heads
    c = cv2.dilate(c, np.ones((2, 2), np.float32))
    glow = cv2.GaussianBlur(c, (0, 0), G * 0.005)
    glow = glow / (glow.max() + 1e-6)
    dust = 0.16 * _fbm((G, G), seed * 73 + 5, octaves=3, freq=12)  # faint sky dust (coverage)
    field = np.maximum(np.maximum(c, 0.5 * glow), np.maximum(dust, 1.4 * head))
    field = cv2.resize(np.clip(field, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


def flame_smoke_billow(shape, seed=7):
    """RIM-LIT SMOKE — heavy rolling smoke billows whose edges catch fire-light (bright rims on
    dark masses) over a glowing ember base. INVENTED: rim = gradient magnitude of a billowing
    density field, so the bright structure traces billow EDGES. Distinct from soft filled plumes
    (metaball) and crack networks (lava)."""
    h, w = shape
    dens = _fbm((h, w), seed * 79 + 1, octaves=6, freq=3.0)
    yb = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
    dens = _norm(dens * (0.5 + 0.85 * yb))                       # smoke gathers up high
    gy, gx = np.gradient(dens)
    rim = _norm(np.sqrt(gx * gx + gy * gy))                      # bright billow edges
    rim = np.power(rim, 0.65)
    base = np.exp(-((1.0 - yb) / 0.12) ** 2) * (0.55 + 0.7 * _fbm((h, w), seed * 79 + 5, freq=11))
    field = _norm(0.95 * rim * (0.45 + 0.85 * dens) + 0.75 * base + 0.10 * dens)
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "meteor_shower": flame_meteor_shower,
    "smoke_billow":  flame_smoke_billow,
})


# ---------------------------------------------------------------- batch 11 (INVENTED math)
def flame_pahoehoe_rope(shape, seed=7, ropes=15):
    """PAHOEHOE — ropey lava: parallel curved ridges folded like the squeezed skin of a slow
    lava flow. INVENTED: a heavily domain-WARPED phase field — bands perpendicular to a noisy
    flow fold into ropes — with molten glow riding the ridges. Distinct from the Voronoi crack
    network (lava_flow), thin interference fringes, and scattered curls."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xx / w, yy / h
    wx = (_fbm((h, w), seed * 83 + 1, octaves=4, freq=2.2) - 0.5) * 1.4
    wy = (_fbm((h, w), seed * 83 + 2, octaves=4, freq=2.2) - 0.5) * 1.4
    phase = (yn + wx) * ropes * 2.0 * np.pi + 2.2 * np.sin((xn + wy) * 3.0 * 2.0 * np.pi)
    rope = np.power(0.5 + 0.5 * np.cos(phase), 1.6)              # rounded rope ridges
    heat = 0.5 + 0.75 * _fbm((h, w), seed * 83 + 5, octaves=3, freq=4)
    fine = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 83 + 7, octaves=2, freq=22.0) - 1.0)  # crushed skin
    t = _norm(rope * heat * (0.6 + 0.5 * np.power(np.clip(fine, 0, 1), 1.4)))
    return _ramp(np.power(t, 0.95), _FIRE_STOPS)


def flame_napalm_drips(shape, seed=7, drips=80):
    """NAPALM DRIPS — molten fire DRIPPING downward (the inverse of rising flame): glowing
    runs hang from scattered anchors and pool into bright droplet tips. INVENTED: stamped
    downward runs with a hot droplet at each tip. Distinct downward-drip topology."""
    h, w = shape
    G = 560
    r = _rng(seed * 89 + 1)
    c = np.zeros((G, G), np.float32)
    tipr = max(1, int(G * 0.007))
    for _ in range(drips):
        x = r.random() * G
        y0 = r.random() * G * 0.72                               # anchored across the upper field
        length = int((0.10 + 0.30 * r.random()) * G)
        wob = (r.random() - 0.5) * 0.07
        for t in range(length):
            xi, yi = int(x + wob * t), int(y0 + t)
            if 0 <= xi < G and 0 <= yi < G:
                c[yi, xi] = max(c[yi, xi], 0.62 + 0.25 * (1.0 - t / max(1, length)))
        tx, ty = int(x + wob * length), int(y0 + length)
        if 0 <= tx < G and 0 <= ty < G:
            cv2.circle(c, (tx, ty), tipr, 1.0, -1)               # white-hot molten droplet
    c = cv2.dilate(c, np.ones((2, 2), np.float32))
    glow = cv2.GaussianBlur(c, (0, 0), G * 0.005)
    glow = glow / (glow.max() + 1e-6)
    field = np.maximum(c, 0.55 * glow)
    field = cv2.resize(np.clip(field, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "pahoehoe_rope": flame_pahoehoe_rope,
    "napalm_drips":  flame_napalm_drips,
})


# ---------------------------------------------------------------- batch 12 (INVENTED math)
def flame_magma_bubbles(shape, seed=7, bubbles=150):
    """MAGMA POOL — a bed of bubbling lava: overlapping bubbles each with a bright molten RIM
    and a warm interior, over a dark crust. INVENTED: stamped annuli (rims) + filled cores, so
    the bright structure is circular outlines — distinct from soft distance-blobs (cellular) and
    the Voronoi crack network (lava)."""
    h, w = shape
    G = 600
    r = _rng(seed * 97 + 1)
    rim = np.zeros((G, G), np.float32)
    core = np.zeros((G, G), np.float32)
    for _ in range(bubbles):
        cx, cy = int(r.integers(0, G)), int(r.integers(0, G))
        rad = int((0.025 + 0.065 * r.random()) * G)
        cv2.circle(rim, (cx, cy), rad, 1.0, thickness=max(1, int(rad * 0.20)))   # molten rim
        cv2.circle(core, (cx, cy), max(1, int(rad * 0.72)), 0.45 + 0.4 * r.random(), -1)  # warm interior
    rim = cv2.GaussianBlur(rim, (0, 0), G * 0.0016)
    crust = 0.12 * _fbm((G, G), seed * 97 + 5, octaves=3, freq=10)
    field = _norm(np.maximum(rim, 0.55 * core) + crust)
    field = cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


def flame_marble_swirl(shape, seed=7):
    """MARBLED FIRE — swirled veins of molten color like paper-marbling / stirred fluid.
    INVENTED: iteratively domain-WARP the coordinates (each pass folds the field into the last),
    then band them into veins. The repeated warp gives chaotic swirls — distinct from the parallel
    ropes (pahoehoe), single spirals (vortex), and scattered filaments (curl)."""
    h, w = shape
    # the warps are LOW-frequency, so fold the coordinates at quarter-res then upsample (≈16x cheaper)
    lh, lw = max(2, h // 4), max(2, w // 4)
    yy, xx = np.mgrid[0:lh, 0:lw].astype(np.float32)
    fx, fy = xx / lw, yy / lh
    for i in range(3):
        fx = fx + 0.38 * (_fbm((lh, lw), seed * 101 + 1 + i, octaves=4, freq=2.5 + i) - 0.5)
        fy = fy + 0.38 * (_fbm((lh, lw), seed * 101 + 11 + i, octaves=4, freq=2.5 + i) - 0.5)
    fx = cv2.resize(fx, (w, h), interpolation=cv2.INTER_LINEAR)
    fy = cv2.resize(fy, (w, h), interpolation=cv2.INTER_LINEAR)
    veins = np.power(0.5 + 0.5 * np.sin((fx * 7.0 + fy * 3.0) * 2.0 * np.pi), 1.4)
    fine = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 101 + 21, octaves=2, freq=20.0) - 1.0)
    t = _norm(veins * (0.6 + 0.6 * _fbm((h, w), seed * 101 + 31, freq=5))
              * (0.6 + 0.5 * np.power(np.clip(fine, 0, 1), 1.4)))
    return _ramp(t, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "magma_bubbles": flame_magma_bubbles,
    "marble_swirl":  flame_marble_swirl,
})


# ---------------------------------------------------------------- batch 13 (INVENTED math)
def flame_dragon_scale(shape, seed=7, scale=15.0):
    """DRAGON SCALE — overlapping glowing scales (burning dragon hide). INVENTED: a brick-offset
    lattice where each cell carries the bright lower ARC of a scale, warped organically; the rims
    ignite, the bodies stay dim. A tiled overlapping-scallop topology nothing else has."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    wx = (_fbm((h, w), seed * 107 + 1, octaves=3, freq=2.5) - 0.5) * 0.10
    wy = (_fbm((h, w), seed * 107 + 2, octaves=3, freq=2.5) - 0.5) * 0.10
    u = (xx / w + wx) * scale
    v = (yy / h + wy) * scale * 0.82
    v = v + 0.5 * (np.floor(u).astype(np.int32) % 2)             # brick offset -> overlap like scales
    cu = (u - np.floor(u)) - 0.5
    cv_ = (v - np.floor(v)) - 0.5
    rr = np.sqrt(cu * cu + cv_ * cv_)
    rim = np.exp(-((rr - 0.42) / 0.07) ** 2)                     # glowing scale rim
    body = np.clip(0.46 - rr, 0, 1) * 0.5                        # faint scale body glow
    heat = 0.55 + 0.7 * _fbm((h, w), seed * 107 + 5, octaves=3, freq=4)
    fine = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 107 + 7, octaves=2, freq=20.0) - 1.0)
    t = _norm((rim + body) * heat * (0.62 + 0.5 * np.power(np.clip(fine, 0, 1), 1.4)))
    return _ramp(t, _FIRE_STOPS)


def flame_caustic_web(shape, seed=7):
    """FIRE CAUSTICS — the bright filigree light makes when it refracts and FOCUSES (like sun on a
    pool floor), here in fire color. INVENTED: displace a uniform grid of 'rays' by the gradient of
    a smooth field and HISTOGRAM where they land — rays pile up on caustic curves. Built at half-res
    then upsampled. Smooth curvy convergence web, distinct from straight Voronoi cracks (lava)."""
    H, W = shape
    h, w = max(2, H * 3 // 4), max(2, W * 3 // 4)               # 3/4-res keeps the caustic curves crisp
    pot = _fbm((h, w), seed * 109 + 1, octaves=4, freq=4.0)
    gy, gx = np.gradient(pot)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    amp = 0.16 * h
    sx = np.clip(xx + gx * amp, 0, w - 1).astype(np.int32)
    sy = np.clip(yy + gy * amp, 0, h - 1).astype(np.int32)
    acc = np.zeros((h, w), np.float32)
    np.add.at(acc, (sy, sx), 1.0)                                # ray landing density = caustic intensity
    acc = cv2.GaussianBlur(acc, (0, 0), 0.6)
    acc = np.power(_norm(acc), 0.5)                              # brighten the thin caustic curves
    fine = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 109 + 7, octaves=2, freq=22.0) - 1.0)
    field = _norm(acc * (0.45 + 0.75 * np.power(np.clip(fine, 0, 1), 1.4)))
    field = cv2.resize(field, (W, H), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "dragon_scale": flame_dragon_scale,
    "caustic_web":  flame_caustic_web,
})


# ---------------------------------------------------------------- batch 14 (INVENTED math)
def flame_obsidian_fracture(shape, seed=7, impacts=7):
    """OBSIDIAN FRACTURE — glowing molten cracks radiating from impact points in black volcanic
    glass: STRAIGHT, sharp, occasionally kinked rays (not organic Voronoi seams, not curvy plasma
    walks). INVENTED: shoot straight crack-rays from scattered impacts with rare angle kinks, plus
    fine background crazing for coverage. Angular impact-star topology."""
    h, w = shape
    G = 560
    r = _rng(seed * 127 + 1)
    c = np.zeros((G, G), np.float32)
    for _ in range(impacts):
        ix, iy = r.random() * G, r.random() * G
        for _k in range(int(r.integers(5, 9))):
            x, y = ix, iy
            ang = r.random() * 2.0 * np.pi
            dx, dy = np.cos(ang), np.sin(ang)
            length = int((0.18 + 0.45 * r.random()) * G)
            for t in range(length):
                x += dx; y += dy
                if t % 38 == 0:                                  # rare sharp kink (angular, not curvy)
                    ang += (r.random() - 0.5) * 0.5
                    dx, dy = np.cos(ang), np.sin(ang)
                xi, yi = int(x), int(y)
                if 0 <= xi < G and 0 <= yi < G:
                    c[yi, xi] = 1.0
                else:
                    break
    c = cv2.dilate(c, np.ones((2, 2), np.float32))
    craze = np.power(1.0 - np.abs(2.0 * _fbm((G, G), seed * 127 + 9, octaves=3, freq=16.0) - 1.0), 5.0)
    glow = cv2.GaussianBlur(c, (0, 0), G * 0.004)
    glow = glow / (glow.max() + 1e-6)
    field = np.maximum(np.maximum(c, 0.5 * glow), 0.35 * craze)  # bright cracks + faint crazing
    field = cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


# NOTE: a bilateral-wing 'phoenix' was prototyped here and DROPPED — the body core dominated into a
# radial SUNBURST (gate measured 0.788 similarity to radial — a near-duplicate), it failed coverage
# (0.53), and it didn't read as a bird (name-match fail). Bilateral wings didn't materialise from the
# field math; forced uniqueness/name would violate the mandate, so it's dropped. (cf. doom_ca, firewall_wave.)


FLAME_STRUCTURES.update({
    "obsidian_fracture": flame_obsidian_fracture,
})


# ---------------------------------------------------------------- batch 15 (INVENTED math)
def flame_basalt_columns(shape, seed=7, cols=11):
    """BASALT COLUMNS — the Giant's-Causeway look: packed hexagonal column TOPS (bright flat cells)
    split by thin glowing molten seams. INVENTED: Voronoi over a REGULAR HEX lattice of seeds (not
    random) → regular hexagons; cells glow with per-column heat, seams stay thin. The hex regularity
    sets it apart from random Voronoi lava and soft cellular blobs."""
    h, w = shape
    r = _rng(seed * 137 + 1)
    pts = np.ones((h, w), np.uint8)
    sx = w / cols
    for j, cyf in enumerate(np.linspace(0, h, cols, endpoint=False)):
        xoff = 0.5 * (j % 2) * sx
        for cxf in np.linspace(0, w, cols, endpoint=False):
            cx = int((cxf + xoff + (r.random() - 0.5) * sx * 0.18) % w)
            cy = int(min(h - 1, max(0, cyf + (r.random() - 0.5) * (h / cols) * 0.18)))
            pts[cy, cx] = 0
    dist, labels = cv2.distanceTransformWithLabels(pts, cv2.DIST_L2, 3)
    lab = labels.astype(np.int32)
    edge = np.zeros((h, w), np.float32)
    edge[:, :-1] += (lab[:, :-1] != lab[:, 1:])
    edge[:-1, :] += (lab[:-1, :] != lab[1:, :])
    seam = _norm(cv2.GaussianBlur(cv2.dilate(np.clip(edge, 0, 1), np.ones((2, 2), np.float32)), (0, 0), max(1.0, h * 0.0016)))
    # per-column heat: each cell a different brightness, looked up by its label
    nlab = int(lab.max()) + 1
    heat_lut = (0.45 + 0.55 * r.random(nlab)).astype(np.float32)
    cellheat = heat_lut[np.clip(lab, 0, nlab - 1)]
    fine = 1.0 - np.abs(2.0 * _fbm((h, w), seed * 137 + 7, octaves=2, freq=20.0) - 1.0)
    celltop = np.clip(1.0 - seam, 0, 1) * cellheat                   # bright flat tops, dark seams
    t = _norm(celltop * (0.6 + 0.5 * np.power(np.clip(fine, 0, 1), 1.4)) + 0.18 * seam)
    return _ramp(t, _FIRE_STOPS)


def flame_eruption_column(shape, seed=7):
    """ERUPTION COLUMN — a volcanic plume: a hot column rising from the base, widening as it climbs
    and MUSHROOMING into a cap, turbulent throughout. INVENTED: a height-widening gaussian column
    + a cap lobe + rising turbulence. A single vertical silhouette (cool sky at the sides is intrinsic
    → coverage-exempt)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, ny = xx / w, yy / h
    cx = 0.5 + (_fbm((h, w), seed * 139 + 1, octaves=3, freq=2) - 0.5) * 0.10
    up = 1.0 - ny                                                    # 0 base, 1 top
    width = 0.045 + 0.30 * up ** 1.3
    col = np.exp(-(((xn - cx) / width) ** 2))
    cap = np.exp(-(((ny - 0.17) / 0.11) ** 2)) * np.exp(-(((xn - 0.5) / 0.30) ** 2))
    turb = 0.40 + 0.55 * _fbm((h, w), seed * 139 + 5, octaves=5, freq=6) \
        + 0.35 * _fbm((h, w), seed * 139 + 6, octaves=3, freq=15)        # + fine turbulence (crushed)
    rise = np.clip(1.15 - 0.55 * ny, 0.2, 1.15)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 139 + 9, octaves=2, freq=26.0) - 1.0), 0, 1), 2.2)
    field = _norm(np.maximum(col, 0.85 * cap) * turb * rise * (0.55 + 0.7 * fine))
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "basalt_columns":  flame_basalt_columns,
    "eruption_column": flame_eruption_column,
})


# ---------------------------------------------------------------- batch 16 (INVENTED math)
# NOTE: a classic IFS 'fractal flame' (Scott Draves chaos game) was prototyped here and DROPPED —
# even with a swirl variation + fit-to-frame it covered only 0.34 (an IFS attractor is an inherently
# SPARSE, measure-zero set: ~66% black). It can't meet the full-coverage mandate and isn't a legit
# single-motif exemption, so it's dropped rather than forced. (cf. phoenix, doom_ca, firewall_wave.)


def flame_heat_mirage(shape, seed=7):
    """HEAT MIRAGE — the rippling shimmer of hot air: roughly horizontal hot bands warped into
    wavy shimmer (never ruler-straight). INVENTED: sinusoidal bands whose phase is displaced by
    low-freq noise + a cross sine, hotter toward the base. Distinct wavy-band field."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xx / w, yy / h
    warp = (_fbm((h, w), seed * 151 + 1, octaves=4, freq=3.0) - 0.5) * 0.55
    warp2 = 0.13 * np.sin(xn * 7.0 * 2.0 * np.pi + (_fbm((h, w), seed * 151 + 3, freq=2) - 0.5) * 5.0)
    bands = np.power(0.5 + 0.5 * np.sin((yn + warp + warp2) * 16.0 * 2.0 * np.pi), 1.5)
    heat = np.clip(1.1 - 0.6 * yn, 0.25, 1.1)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 151 + 7, octaves=2, freq=22.0) - 1.0), 0, 1), 1.4)
    t = _norm(bands * heat * (0.6 + 0.5 * fine))
    return _ramp(t, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "heat_mirage":  flame_heat_mirage,
})


# ---------------------------------------------------------------- batch 17 (INVENTED math)
def flame_spiral_galaxy(shape, seed=7, arms=3):
    """SPIRAL GALAXY of fire — grand-design logarithmic ARMS winding out of a white-hot core
    bulge, studded with bright HII knots, over faint dust. INVENTED: cos(arms·(θ − twist·ln r))
    lights the arms; a gaussian bulge; thresholded noise for knots. Multi-arm + bulge sets it apart
    from the single tight vortex swirl."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    dy, dx = (yy - cy) / h, (xx - cx) / w
    r = np.sqrt(dx * dx + dy * dy) * 2.0 + 1e-3
    th = np.arctan2(dy, dx)
    spiral = np.cos(arms * (th - 3.0 * np.log(r)))
    arm = np.power(np.clip(0.5 + 0.5 * spiral, 0, 1), 3.0) * np.exp(-r * 0.85)   # bright arms, fade out
    bulge = np.exp(-(r / 0.14) ** 2)
    knots = np.clip((_fbm((h, w), seed * 163 + 5, octaves=4, freq=14) - 0.62) * 9.0, 0, 1)
    dust = 0.14 * _fbm((h, w), seed * 163 + 7, octaves=4, freq=8)
    field = _norm(arm * (0.55 + 0.85 * _fbm((h, w), seed * 163 + 9, freq=9))
                  + bulge + 0.55 * knots * (arm + 0.3) + dust)
    return _ramp(field, _FIRE_STOPS)


def flame_aurora_drape(shape, seed=7, sheets=8):
    """AURORA DRAPE — hanging curtains of fire: vertical sheets that fold side-to-side with height
    AND carry horizontal fold-banding (the pleat shading that reads as drape, not stripes). INVENTED:
    a vertical sheet phase serpentined by noise, crossed with a horizontal fold modulation. The
    cross-banding is what distinguishes it from discrete rising tongues."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xx / w, yy / h
    fold = 0.12 * np.sin(yn * 3.0 * 2.0 * np.pi + (_fbm((h, w), seed * 167 + 1, freq=2) - 0.5) * 4.0) \
        + (_fbm((h, w), seed * 167 + 2, octaves=3, freq=2.5) - 0.5) * 0.20
    sheet = np.power(0.5 + 0.5 * np.cos((xn + fold) * sheets * 2.0 * np.pi), 2.3)   # vertical curtains
    hbands = 0.55 + 0.45 * np.cos((yn + 0.15 * np.sin((xn + fold) * 6.28)) * 22.0)  # horizontal pleat shading
    prof = np.clip(1.12 - 0.72 * yn, 0.18, 1.12)                                    # bright low, fade up
    flick = 0.6 + 0.7 * _fbm((h, w), seed * 167 + 5, octaves=4, freq=7)
    field = _norm(sheet * (0.45 + 0.7 * hbands) * prof * flick)
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "spiral_galaxy": flame_spiral_galaxy,
    "aurora_drape":  flame_aurora_drape,
})


# ---------------------------------------------------------------- batch 18 (INVENTED math)
def flame_kaleidoscope(shape, seed=7, fold=8):
    """KALEIDOSCOPE — a fire MANDALA: a turbulent fire texture folded into N-fold mirror symmetry,
    so an ornate symmetric ornament emerges. INVENTED: reflect each pixel's polar ANGLE into one
    wedge (abs of angle-within-segment) and resample the base texture there → kaleidoscopic repeat.
    A rotational/mirror symmetry no other structure has; fills the canvas by construction."""
    h, w = shape
    base = _norm(0.45 * _fbm((h, w), seed * 181 + 1, octaves=5, freq=6.0)
                 + 0.32 * (1.0 - np.abs(2.0 * _fbm((h, w), seed * 181 + 3, octaves=3, freq=12.0) - 1.0))
                 + 0.23 * np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 181 + 5, octaves=2, freq=22.0) - 1.0), 0, 1), 2.0))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    dx, dy = xx - cx, yy - cy
    r = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx)
    seg = 2.0 * np.pi / fold
    thf = np.abs((np.mod(th, seg)) - seg / 2.0)                  # mirror within each wedge
    sx = (cx + r * np.cos(thf)).astype(np.float32)
    sy = (cy + r * np.sin(thf)).astype(np.float32)
    mandala = cv2.remap(base, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    rings = 0.68 + 0.42 * np.cos(r / w * 66.0)                   # FINE concentric rings (crushed radial detail)
    ripple = 0.82 + 0.32 * np.cos(thf * fold * 6.0)             # fine symmetric angular ornament
    return _ramp(_norm(mandala * rings * ripple), _FIRE_STOPS)


def flame_basket_weave(shape, seed=7, k=10):
    """BASKET WEAVE — interlaced glowing fire strands woven over/under in a checkerboard, so each
    cell shows one strand on top and the crossing one tucked beneath. INVENTED: two perpendicular
    band sets + a checkerboard 'which is on top' mask. A woven topology nothing else has."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = (_fbm((h, w), seed * 179 + 1, octaves=3, freq=2.0) - 0.5) * 0.04
    xn, yn = xx / w + warp, yy / h + warp
    bx = np.power(0.5 + 0.5 * np.cos(xn * k * 2.0 * np.pi), 3.0)
    by = np.power(0.5 + 0.5 * np.cos(yn * k * 2.0 * np.pi), 3.0)
    over = ((np.floor(xn * k).astype(np.int32) + np.floor(yn * k).astype(np.int32)) % 2).astype(np.float32)
    weave = (over * bx + (1.0 - over) * by) + 0.4 * (over * by + (1.0 - over) * bx)   # top strand + dim under
    heat = 0.6 + 0.6 * _fbm((h, w), seed * 179 + 5, octaves=3, freq=5)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 179 + 7, octaves=2, freq=20.0) - 1.0), 0, 1), 1.4)
    t = _norm(weave * heat * (0.6 + 0.5 * fine))
    return _ramp(t, _FIRE_STOPS)


def flame_lightning_storm(shape, seed=7, bolts=4):
    """LIGHTNING STORM — a few THICK, dramatic forked bolts ripping top-to-bottom over a faintly
    glowing storm cloud. INVENTED: jagged segmented walks with occasional forks drawn as crisp
    cv2 lines + bloom; sparse and bold, distinct from the dense thin radial thicket of plasma_arc."""
    h, w = shape
    G = 560
    r = _rng(seed * 191 + 1)
    c = np.zeros((G, G), np.float32)
    for _ in range(bolts):
        x, y = r.random() * G, 0.0
        lean = (r.random() - 0.5) * 0.3
        while y < G:
            seglen = int(r.integers(16, 42))
            ang = np.pi / 2 + lean + (r.random() - 0.5) * 0.5
            ex, ey = x + np.cos(ang) * seglen, y + np.sin(ang) * seglen
            cv2.line(c, (int(x), int(y)), (int(ex), int(ey)), 1.0, 2)
            if r.random() < 0.38:                               # forked branch
                fa = ang + (r.random() - 0.5) * 1.3
                fl = int(r.integers(20, 70))
                cv2.line(c, (int(x), int(y)), (int(x + np.cos(fa) * fl), int(y + np.sin(fa) * fl)), 0.7, 1)
            x, y = ex, ey
            lean += (r.random() - 0.5) * 0.22
    glow = cv2.GaussianBlur(c, (0, 0), G * 0.010)
    glow = glow / (glow.max() + 1e-6)
    cloud = 0.34 * _fbm((G, G), seed * 191 + 5, octaves=4, freq=10)   # finer storm-cloud glow fills every region
    field = np.maximum(np.maximum(c, 0.6 * glow), cloud)
    field = cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR)
    return _ramp(_norm(field), _FIRE_STOPS)


def flame_fire_rose(shape, seed=7, petals=6):
    """FIRE ROSE — a blooming rosette: layered rose-curve petals of flame at shrinking scales and
    rotated phases, around a white-hot center. INVENTED: glowing arcs riding rose curves
    r≈|cos(kθ)| at several layers. A floral petal topology distinct from thin radial rays/rings."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    dy, dx = (yy - cy) / h, (xx - cx) / w
    r = np.sqrt(dx * dx + dy * dy) * 2.0
    th = np.arctan2(dy, dx)
    rose = np.zeros((h, w), np.float32)
    for pk, sc, rot, amp, wd in [(petals, 0.62, 0.0, 1.0, 0.09), (petals, 0.40, 0.52, 0.85, 0.07),
                                 (petals + 2, 0.22, 1.0, 0.72, 0.055)]:
        petal = np.abs(np.cos(pk * th + rot))
        rose = np.maximum(rose, amp * np.exp(-((r - sc * petal - 0.04) / wd) ** 2))
    core = np.exp(-(r / 0.09) ** 2)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 193 + 7, octaves=2, freq=22.0) - 1.0), 0, 1), 1.4)
    field = _norm((rose * (0.6 + 0.6 * _fbm((h, w), seed * 193 + 3, freq=8)) + core) * (0.6 + 0.5 * fine)
                  + 0.08 * _fbm((h, w), seed * 193 + 9, octaves=3, freq=9))
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "lightning_storm": flame_lightning_storm,
    "fire_rose":       flame_fire_rose,
    "kaleidoscope": flame_kaleidoscope,
    "basket_weave": flame_basket_weave,
})


# ---------------------------------------------------------------- batch 20 (INVENTED math)
# NOTE: a 'river_delta' dendritic branch tree was prototyped here and DROPPED — like the IFS, a thin
# branching tree is an inherently SPARSE structure (the seed-7 tree even degenerated to a stub; cov 0.03)
# and can't meet the full-coverage mandate. Branching line-trees only work when dense (plasma_arc) or
# cloud-backed (lightning_storm); a single widening delta is neither. Dropped, not forced.


def flame_mammatus(shape, seed=7, k=7):
    """MAMMATUS — a ceiling of hanging bulbous pouches lit on their UNDERSIDES (the ominous
    pouch-cloud look). INVENTED: a grid of hemispheres, each shaded bright-bottom/dark-top so they
    read as lobes bulging downward. Distinct from flat cells (basalt) and bubble rings (magma)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = (_fbm((h, w), seed * 199 + 1, octaves=3, freq=2.0) - 0.5) * 0.05
    u = (xx / w + warp) * k
    v = (yy / h + warp) * k
    cu = (u - np.floor(u)) - 0.5
    cv_ = (v - np.floor(v)) - 0.5
    d = np.sqrt(cu * cu + cv_ * cv_)
    pouch = np.clip(1.0 - d * 2.0, 0, 1)                                  # a hemisphere per cell
    lit = 0.35 + 0.65 * np.clip((cv_ + 0.30) / 0.6, 0, 1)                 # underside (lower) brighter
    heat = 0.55 + 0.6 * _fbm((h, w), seed * 199 + 5, octaves=3, freq=4)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 199 + 7, octaves=2, freq=20.0) - 1.0), 0, 1), 1.4)
    t = _norm(pouch * lit * heat * (0.62 + 0.45 * fine) + 0.06)
    return _ramp(t, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "mammatus":    flame_mammatus,
})


# ---------------------------------------------------------------- batch 21 (INVENTED math)
def flame_spider_web(shape, seed=7, spokes=15, rings=9):
    """SPIDER WEB — an orb-weaver net of fire: radial SPOKES crossed by concentric polygonal
    THREADS that sag between spokes, a glowing hub, dew-spark nodes. INVENTED: combine an angular
    spoke comb with a sagged radial ring comb into a NET — distinct from plain rays or plain rings."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    dy, dx = (yy - cy) / h, (xx - cx) / w
    r = np.sqrt(dx * dx + dy * dy) * 2.0
    th = np.arctan2(dy, dx)
    spoke = np.power(np.clip(0.5 + 0.5 * np.cos(th * spokes), 0, 1), 40) * np.clip(1.15 - r, 0, 1)
    sag = 0.045 * np.cos(th * spokes)                            # threads bow inward between spokes -> polygonal
    ring = np.power(np.clip(0.5 + 0.5 * np.cos((r + sag) * rings * 2.0 * np.pi), 0, 1), 16) * np.clip(1.15 - r, 0, 1)
    hub = np.exp(-(r / 0.05) ** 2)
    dew = np.clip((_fbm((h, w), seed * 211 + 5, octaves=4, freq=16) - 0.66) * 9.0, 0, 1) * np.maximum(spoke, ring)
    bg = 0.12 * _fbm((h, w), seed * 211 + 7, octaves=3, freq=11)
    field = _norm(np.maximum.reduce([spoke, ring, hub, 1.3 * dew]) * (0.7 + 0.5 * _fbm((h, w), seed * 211 + 3, freq=7)) + bg)
    return _ramp(field, _FIRE_STOPS)


def flame_mach_cone(shape, seed=7):
    """MACH CONE — a sonic-boom V-wake: a white-hot apex throwing two oblique SHOCK lines into a
    V, with compressed glowing gas inside the cone, over a faint field. INVENTED: distance to the
    two shock rays + an interior fill. A directional V topology distinct from the horizontal jet cone."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xx / w, yy / h
    ax, ay = 0.5, 0.12
    half = 0.62
    dxp, dyp = xn - ax, yn - ay
    ang = np.arctan2(dxp, dyp + 1e-6)                            # 0 = straight down from apex
    below = np.clip(dyp * 3.0, 0, 1)
    shock = np.exp(-((np.abs(ang) - half) / 0.05) ** 2) * below
    inside = (np.abs(ang) < half) & (dyp > 0)
    cone = np.where(inside, np.exp(-(np.abs(ang) / half) * 1.6), 0.0).astype(np.float32) * below
    apex = np.exp(-(((xn - ax) ** 2 + (yn - ay) ** 2) / 0.006))
    turb = 0.55 + 0.7 * _fbm((h, w), seed * 223 + 5, octaves=4, freq=7)
    bg = 0.13 * _fbm((h, w), seed * 223 + 7, octaves=3, freq=11)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 223 + 9, octaves=2, freq=24.0) - 1.0), 0, 1), 1.4)
    field = _norm((np.maximum.reduce([shock, 0.5 * cone, apex])) * turb * (0.7 + 0.55 * fine) + bg)
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "spider_web": flame_spider_web,
    "mach_cone":  flame_mach_cone,
})


# ---------------------------------------------------------------- batch 22 (INVENTED math)
def flame_quasicrystal(shape, seed=7, waves=5):
    """QUASICRYSTAL — an aperiodic Penrose-like fire tiling from summing 5 plane waves at 36°
    (10-fold quasiperiodic interference) — ornate, never-repeating cells. INVENTED, distinct from
    ferro_spikes (3 hex waves MULTIPLIED into peaks); here 5 waves are SUMMED for aperiodicity."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = (_fbm((h, w), seed * 227 + 1, octaves=3, freq=2.0) - 0.5) * 0.30
    xn, yn = xx / w + warp, yy / h + warp
    k = 24.0
    g = np.zeros((h, w), np.float32)
    for i in range(waves):
        a = np.pi * i / waves
        g += np.cos((np.cos(a) * xn + np.sin(a) * yn) * k * 2.0 * np.pi)
    pattern = np.power(_norm(g), 2.0)                           # sharpen the quasicrystal cells
    heat = 0.5 + 0.7 * _fbm((h, w), seed * 227 + 5, octaves=3, freq=4)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 227 + 7, octaves=2, freq=20.0) - 1.0), 0, 1), 1.4)
    t = _norm(pattern * heat * (0.6 + 0.5 * fine))
    return _ramp(t, _FIRE_STOPS)


def flame_crackle_glaze(shape, seed=7, n=330):
    """CRACKLE GLAZE — fine ceramic CRAQUELURE: hairline glowing cracks webbing dense warm cells
    (a kiln-crackled glaze). INVENTED: a many-seed Voronoi (far more seeds than lava) → thin dense
    seams, kept hairline (no dilation). Distinct from lava's bold sparse molten seams by SCALE."""
    h, w = shape
    r = _rng(seed * 229 + 1)
    pts = np.ones((h, w), np.uint8)
    pts[r.integers(0, h, n), r.integers(0, w, n)] = 0
    _, labels = cv2.distanceTransformWithLabels(pts, cv2.DIST_L2, 3)
    lab = labels.astype(np.int32)
    edge = np.zeros((h, w), np.float32)
    edge[:, :-1] += (lab[:, :-1] != lab[:, 1:])
    edge[:-1, :] += (lab[:-1, :] != lab[1:, :])
    seam = _norm(cv2.GaussianBlur(np.clip(edge, 0, 1), (0, 0), 0.8))     # hairline cracks (no dilate)
    nlab = int(lab.max()) + 1
    heat_lut = (0.40 + 0.50 * r.random(nlab)).astype(np.float32)
    cellheat = heat_lut[np.clip(lab, 0, nlab - 1)]
    crack = np.power(seam, 0.6)
    t = _norm(0.9 * crack + 0.5 * cellheat * (1.0 - seam))
    return _ramp(t, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "quasicrystal":  flame_quasicrystal,
    "crackle_glaze": flame_crackle_glaze,
})


# ---------------------------------------------------------------- batch 23 (INVENTED math)
def flame_chevron_herringbone(shape, seed=7, kb=7, ks=18):
    """HERRINGBONE — interlocking chevrons of fire: diagonal glowing strokes whose LEAN flips every
    block, weaving the classic zigzag herringbone. INVENTED: diagonal stripe phase with a per-block
    sign flip. A zigzag topology distinct from the orthogonal basket weave and any banded field."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = (_fbm((h, w), seed * 239 + 1, octaves=3, freq=2.0) - 0.5) * 0.05
    xn, yn = xx / w + warp, yy / h + warp
    lean = np.where(np.floor(xn * kb).astype(np.int32) % 2 == 0, 1.0, -1.0)   # flip diagonal per block
    stripe = np.power(0.5 + 0.5 * np.cos((yn * ks + lean * xn * ks) * 2.0 * np.pi), 2.2)
    block_edge = np.power(0.5 + 0.5 * np.cos(xn * kb * 2.0 * np.pi), 8.0)      # faint seams between blocks
    heat = 0.6 + 0.6 * _fbm((h, w), seed * 239 + 5, octaves=3, freq=5)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 239 + 7, octaves=2, freq=20.0) - 1.0), 0, 1), 1.4)
    t = _norm(np.maximum(stripe, 0.0) * heat * (0.6 + 0.5 * fine) * (1.0 - 0.3 * block_edge))
    return _ramp(t, _FIRE_STOPS)


def flame_fire_tornado(shape, seed=7):
    """FIRE TORNADO — a tall twisting funnel: a vertical column that narrows toward the touchdown,
    wrapped in SPIRAL bands of flame, leaning with height. INVENTED: a height-narrowing gaussian
    column × a spiral phase that wraps the axis. A funnel silhouette distinct from the flat centered
    vortex and the widening eruption plume (single column → coverage-exempt)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xx / w, yy / h
    axis = 0.5 + 0.12 * np.sin(yn * 2.5) + (_fbm((h, w), seed * 241 + 1, octaves=3, freq=2) - 0.5) * 0.10
    width = 0.05 + 0.24 * yn                                          # narrow at the bottom (touchdown)
    dxc = (xn - axis) / width
    body = np.exp(-dxc * dxc)
    spiral = 0.5 + 0.5 * np.cos((yn * 12.0 + dxc * 3.0) * 2.0 * np.pi + (_fbm((h, w), seed * 241 + 3, freq=2) - 0.5) * 4.0)
    turb = 0.5 + 0.75 * _fbm((h, w), seed * 241 + 5, octaves=4, freq=8)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 241 + 7, octaves=2, freq=24.0) - 1.0), 0, 1), 1.4)
    field = _norm(body * (0.4 + 0.75 * spiral) * turb * (0.6 + 0.5 * fine))
    return _ramp(field, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "chevron_herringbone": flame_chevron_herringbone,
    "fire_tornado":        flame_fire_tornado,
})


# ---------------------------------------------------------------- batch 24 (INVENTED math)
# NOTE: a 'plume_forest' (a row of separate rising plumes) was prototyped here and DROPPED — the gate
# measured 0.764 similarity to tongues (the closest pair in the whole catalog; multiple rising columns
# share the bottom-bright/top-dark envelope of the flame wall) AND it failed fineness (0.12). Under the
# 0.80 line but too tongues-adjacent to be a genuinely distinct structure — dropped to keep the catalog crisp.


def flame_quilted_diamond(shape, seed=7, k=8):
    """QUILTED DIAMOND — a padded diamond quilt of fire: diagonal diamond cells that puff bright at
    their centers and sink dark into stitched seams. INVENTED: rotate to diamond (L1) coords, puff
    each cell by 1 − |u| − |v|. A puffy diagonal-diamond topology distinct from the orthogonal weave."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = (_fbm((h, w), seed * 257 + 1, octaves=3, freq=2.0) - 0.5) * 0.04
    xn, yn = xx / w + warp, yy / h + warp
    u = (xn + yn) * k
    v = (xn - yn) * k
    cu = (u - np.floor(u)) - 0.5
    cv_ = (v - np.floor(v)) - 0.5
    d = np.abs(cu) + np.abs(cv_)                                     # diamond (L1) distance in-cell
    puff = np.clip(1.0 - d * 1.7, 0, 1)
    heat = 0.55 + 0.6 * _fbm((h, w), seed * 257 + 5, octaves=3, freq=4)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 257 + 7, octaves=2, freq=20.0) - 1.0), 0, 1), 1.4)
    t = _norm(puff * heat * (0.62 + 0.45 * fine) + 0.05)
    return _ramp(t, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "quilted_diamond": flame_quilted_diamond,
})


# ---------------------------------------------------------------- batch 25 (INVENTED math)
def flame_vortex_street(shape, seed=7, n=6):
    """KÁRMÁN VORTEX STREET — two STAGGERED rows of counter-rotating fire whirls (the wake shed
    behind an obstacle). INVENTED: place swirl-arm vortices on two offset rows with alternating
    spin. The staggered double-row + spiral arms distinguish it from the single vortex and the
    regular core lattice (votive)."""
    H, W = shape
    G = 900                                                       # build at a fixed grid then upsample (swirls are smooth -> fast)
    yy, xx = np.mgrid[0:G, 0:G].astype(np.float32)
    xn, yn = xx / G, yy / G
    field = np.zeros((G, G), np.float32)
    wob = (_fbm((G, G), seed * 263 + 1, octaves=3, freq=3) - 0.5) * 0.04
    for yc, xoff, sign in [(0.36, 0.0, 1.0), (0.64, 0.5, -1.0)]:
        for i in range(n):
            cx = (i + 0.5 + xoff) / n
            d = np.sqrt((xn - cx) ** 2 + (yn - yc + wob) ** 2)
            ang = np.arctan2(yn - yc + wob, xn - cx)
            swirl = 0.5 + 0.5 * np.cos(2.0 * ang + sign * np.clip(d, 0, 0.32) * 42.0)   # spiral arms
            field = np.maximum(field, np.exp(-(d / 0.10) ** 2) * (0.45 + 0.65 * swirl))
    turb = 0.6 + 0.5 * _fbm((G, G), seed * 263 + 5, octaves=3, freq=8)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((G, G), seed * 263 + 7, octaves=2, freq=20.0) - 1.0), 0, 1), 1.4)
    wake = 0.37 * _fbm((G, G), seed * 263 + 9, octaves=4, freq=13)   # turbulent wake fills the frame (coverage)
    field = _norm(np.maximum(field * turb * (0.65 + 0.45 * fine), wake))
    return _ramp(cv2.resize(field, (W, H), interpolation=cv2.INTER_LINEAR), _FIRE_STOPS)


def flame_leopard_rd(shape, seed=7, iters=2600, gs=130):
    """LEOPARD — Gray-Scott reaction-diffusion in the SPOT regime (k≈0.062): isolated rosette
    spots in a dark matrix, NOT the connected coral labyrinth of reaction_diffusion. Same engine,
    a genuinely different Turing regime (mitosis/bubbles), colored as fire."""
    h, w = shape
    r = _rng(seed * 269 + 1)
    A = np.ones((gs, gs), np.float32)
    B = np.zeros((gs, gs), np.float32)
    B[:] = (r.random((gs, gs)).astype(np.float32) < 0.04).astype(np.float32)   # sparse seeds -> spots
    Da, Db, f, k = 0.19, 0.09, 0.030, 0.0620                                   # SPOT regime
    K = np.array([[0.05, 0.2, 0.05], [0.2, -1.0, 0.2], [0.05, 0.2, 0.05]], np.float32)
    for _ in range(iters):
        r2 = A * B * B
        A = np.clip(A + Da * cv2.filter2D(A, -1, K, borderType=cv2.BORDER_REFLECT) - r2 + f * (1 - A), 0.0, 1.0)
        B = np.clip(B + Db * cv2.filter2D(B, -1, K, borderType=cv2.BORDER_REFLECT) + r2 - (k + f) * B, 0.0, 1.0)
    pat = cv2.resize(_norm(B), (w, h), interpolation=cv2.INTER_CUBIC)
    return _ramp(_norm(np.power(np.clip(pat, 0, 1), 0.9) * (0.6 + 0.5 * _fbm((h, w), seed * 269 + 3, freq=6))), _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "vortex_street": flame_vortex_street,
    "leopard_rd":    flame_leopard_rd,
})


# ---------------------------------------------------------------- batch 26 (INVENTED math)
def flame_pele_strands(shape, seed=7, steps=26):
    """PELE'S HAIR — long combed strands of molten glass fibre: dense sparks advected along a
    mostly-PARALLEL (comb-dominant) flow with only a gentle lateral wave. INVENTED, distinct from
    curl_streamers (which is swirl/vortex-dominant) — here the drift is directional, so strands run
    long and roughly parallel like blown volcanic hair. Half-res advection then upsample (fast)."""
    H, W = shape
    h, w = max(2, H // 2), max(2, W // 2)
    lateral = (_fbm((h, w), seed * 271 + 2, octaves=3, freq=3) - 0.5) * 0.6
    vx, vy = lateral, np.ones((h, w), np.float32)                # strong vertical comb, gentle sway
    mag = np.sqrt(vx * vx + vy * vy) + 1e-6
    vx, vy = vx / mag, vy / mag
    dens = np.clip((_fbm((h, w), seed * 271 + 1, octaves=3, freq=10) - 0.5) * 5.0, 0, 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cur = dens.copy(); acc = dens.copy()
    for _ in range(steps):
        cur = cv2.remap(cur, (xx + vx * 1.5).astype(np.float32), (yy + vy * 1.5).astype(np.float32),
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) * 0.95
        acc = np.maximum(acc, cur)
    acc = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)
    # crushed fibre detail at OUTPUT res (the half-res advect smooths it otherwise)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((H, W), seed * 271 + 9, octaves=2, freq=26.0) - 1.0), 0, 1), 1.4)
    return _ramp(_norm(acc * (0.68 + 0.55 * fine)), _FIRE_STOPS)


def flame_tessellated_triangles(shape, seed=7, k=9):
    """TRIANGLE TILING — a regular triangular tessellation of fire: three line families at 60°
    weave a triangular grid with glowing edges and warm cell interiors. INVENTED, a triangular
    tiling distinct from hex basalt, diamond quilt, and aperiodic quasicrystal."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = (_fbm((h, w), seed * 277 + 1, octaves=3, freq=2.0) - 0.5) * 0.04
    xn, yn = xx / w + warp, yy / h + warp
    edges = np.zeros((h, w), np.float32)
    for a in (0.0, np.pi / 3.0, 2.0 * np.pi / 3.0):
        coord = (np.cos(a) * xn + np.sin(a) * yn) * k
        edges = np.maximum(edges, np.power(0.5 + 0.5 * np.cos(coord * 2.0 * np.pi), 20.0))
    heat = 0.5 + 0.6 * _fbm((h, w), seed * 277 + 5, octaves=3, freq=5)
    fine = np.power(np.clip(1.0 - np.abs(2.0 * _fbm((h, w), seed * 277 + 7, octaves=2, freq=20.0) - 1.0), 0, 1), 1.4)
    t = _norm((0.9 * edges + 0.42 * heat * (1.0 - edges)) * (0.6 + 0.5 * fine))
    return _ramp(t, _FIRE_STOPS)


FLAME_STRUCTURES.update({
    "pele_strands":          flame_pele_strands,
    "tessellated_triangles": flame_tessellated_triangles,
})
