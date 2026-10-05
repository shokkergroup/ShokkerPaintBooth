"""FLAME SPEC-MAP ENGINE (2026-06-18) — the spec-map FOUNDATION for the flame finishes.

The PAINT (albedo) for every flame already exists in engine/paint_v2/flame_math.py
(FLAME_STRUCTURES[name]((H,W),seed) -> HxWx3 float 0..1). This module does NOT touch
paint. It turns a flame's paint into an iRacing SPEC MAP: an HxWx3 uint8 image where
R=Metallic, G=Roughness, B=Clearcoat (0..255).

DOCTRINE (binding):
  * WOVENLIGHT IGNITION — the spec TRACES the paint's exact geometry. The bright flame
    (hot cores/edges) ignites: near-max metallic + a FRACTURED-math-carved clearcoat +
    low roughness on the SAME pixels as the hot paint; everything else stays calm/matte.
    Channels are DECORRELATED: M, R and Cc each key off a different ASPECT of the same
    hot motif (M=hot mask, R=inverse hot, Cc=carved texture), never alien geometry.
  * IRON RULES (mirror of shokker_engine_v2._enforce_iron_rules):
      - Clearcoat: 0 == matte, but 1..15 is an ugly GGX whitewash band -> never land there.
        We use 0 for calm matte and >=CC_FLOOR(16) where there is any clearcoat.
      - Roughness floor: where M < CHROME_M_THRESHOLD(240), Roughness >= ROUGHNESS_FLOOR(15).
      - No giant flat chrome plate (huge fraction of M>=240) — flames ignite a SUBSET.
  * GHOST-SHIFT (spec_dance) — high M + pattern-carved Cc + LOW R on the hot mask makes
    iRacing's environment light flash/shift with viewing angle so the flame "dances".

Self-contained: numpy + cv2 (worley engine pulls scipy lazily, same as fractured_math).
Deterministic per seed. Each generator renders < 3s at 2048.

PUBLIC SURFACE:
  trace_hot(paint, kind='core') -> HxW float 0..1
  spec_ignite(paint, *, palette='classic', frac='auto', strength=1.0) -> HxWx3 uint8
  spec_topo  (paint, *, palette='classic', layers=3)                  -> HxWx3 uint8
  spec_dance (paint, *, palette='classic')                            -> HxWx3 uint8
  PALETTES (dict)
  spec_traces_paint(spec, paint) -> float in [0,1]      (gate: require >= 0.5)
  spec_iron_safe(spec) -> (bool, reason)                (gate: require True)
"""
from __future__ import annotations

import numpy as np
import cv2

# ---- Iron-rule constants — mirror shokker_engine_v2 EXACTLY (read 2026-06-18) ----
CC_FLOOR = 16                  # clearcoat: 0 ok, else must be >= 16 (1..15 = whitewash)
ROUGHNESS_FLOOR_NONMIRROR = 15  # roughness floor where M < chrome threshold
CHROME_M_THRESHOLD = 240        # M >= this == mirror chrome (may drop R to 0)
_WHITEWASH_LO, _WHITEWASH_HI = 1, 15   # the forbidden clearcoat band
_MAX_CHROME_FRACTION = 0.55     # no "giant flat chrome plate": M>=240 over > this frac = unsafe


# =====================================================================  utilities
def _f32(paint):
    a = np.asarray(paint, np.float32)
    if a.ndim == 3 and a.shape[2] > 3:
        a = a[:, :, :3]
    return a


def _luma(paint):
    a = _f32(paint)
    if a.ndim == 2:
        return a
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def _norm(a):
    a = a.astype(np.float32)
    mn, mx = float(a.min()), float(a.max())
    return (a - mn) / (mx - mn) if mx - mn > 1e-6 else np.zeros_like(a)


def _seed_from_paint(paint):
    """Deterministic seed from the paint content (so the spec is stable per flame)."""
    L = _luma(paint)
    return int(abs(np.int64(float(L.sum()) * 1000.0)) & 0x7FFFFFFF) + 1


# =====================================================================  PALETTES
# Palettes tune the spec CHARACTER per colour family. The colours mostly live in the
# paint; here we tune metallic/clearcoat balance and WHICH luminance ignites.
#   ign_q       : percentile of luma that counts as "hot" (lower = more ignites)
#   m_hot       : peak metallic on the hot mask (kept < 240 unless mirror flag)
#   m_calm      : metallic of the calm surround (low, matte)
#   cc_hot      : peak clearcoat carved onto the hot zone (>= CC_FLOOR)
#   r_hot       : roughness floor on the ignited zone (low = glossy ignition)
#   r_calm      : roughness of the calm surround (high = matte)
#   carve_gain  : how hard the fractured texture carves the clearcoat
#   edge_bias   : extra weight on flame EDGES vs solid cores (0..1)
# PUNCH-UP 2026-06-18 (owner: "stunning/dancing"): the first pass ignited only hairline cores
# (~1-4% of the surface) so the on-metal flame barely flashed. ign_q LOWERED (ignite the flame BODY,
# not just the peaks) + r_calm RAISED (deader-matte base for harder gloss-flash contrast) + a
# fill_gamma lift in _hot_mask fills the ignited band. Still iron-safe (m_hot<240, r>=15, cc>=16/0)
# and still traces (it follows MORE of the same flame). Recipes auto-benefit (data-driven).
PALETTES = {
    "classic": dict(ign_q=48, m_hot=232, m_calm=8, cc_hot=212, r_hot=24,
                    r_calm=176, carve_gain=1.00, edge_bias=0.35, fill_gamma=0.62),
    "blue":    dict(ign_q=46, m_hot=226, m_calm=12, cc_hot=236, r_hot=18,
                    r_calm=170, carve_gain=1.10, edge_bias=0.30, fill_gamma=0.60),
    "white_hot": dict(ign_q=56, m_hot=238, m_calm=6, cc_hot=204, r_hot=16,
                      r_calm=188, carve_gain=0.90, edge_bias=0.20, fill_gamma=0.66),
    "green_toxic": dict(ign_q=44, m_hot=214, m_calm=14, cc_hot=194, r_hot=30,
                        r_calm=160, carve_gain=1.25, edge_bias=0.45, fill_gamma=0.58),
    "violet":  dict(ign_q=50, m_hot=230, m_calm=10, cc_hot=226, r_hot=22,
                    r_calm=176, carve_gain=1.05, edge_bias=0.30, fill_gamma=0.62),
    "spectral": dict(ign_q=42, m_hot=234, m_calm=10, cc_hot=216, r_hot=26,
                     r_calm=166, carve_gain=1.30, edge_bias=0.50, fill_gamma=0.56),
}


def _palette(name):
    return dict(PALETTES.get(name, PALETTES["classic"]))


# =====================================================================  trace_hot
def trace_hot(paint, kind="core"):
    """The geometry every mode TRACES. Returns an HxW float mask 0..1 of the flame's
    hot structure. kind in {'core','edge','band'}:
      'core' — brightest regions (smoothed luma, gamma-lifted toward the peaks).
      'edge' — gradient-magnitude of luma (flame OUTLINES / licking tongue edges).
      'band' — the single hottest luminance BAND (a soft window around the top luma).
    """
    L = _norm(_luma(paint))
    h, w = L.shape
    if kind == "edge":
        # gradient magnitude on lightly-blurred luma = flame outlines
        Lb = cv2.GaussianBlur(L, (0, 0), max(0.8, h / 1024.0))
        gx = cv2.Sobel(Lb, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(Lb, cv2.CV_32F, 0, 1, ksize=3)
        m = _norm(np.sqrt(gx * gx + gy * gy))
        return np.power(m, 0.75).astype(np.float32)
    if kind == "band":
        # soft window centred on the hottest luminance band
        hi = float(np.percentile(L, 88))
        m = np.exp(-((L - hi) / 0.10) ** 2)
        return _norm(m).astype(np.float32)
    # 'core' (default): brightest regions, peaks emphasised
    Lb = cv2.GaussianBlur(L, (0, 0), max(0.8, h / 900.0))
    return np.power(_norm(Lb), 1.6).astype(np.float32)


def _hot_mask(paint, pal, kind="core"):
    """Combine a core hot mask with an edge term (edge_bias) and threshold at ign_q
    into a smooth ignition mask 0..1."""
    core = trace_hot(paint, kind)
    edge = trace_hot(paint, "edge")
    mixed = (1.0 - pal["edge_bias"]) * core + pal["edge_bias"] * edge
    mixed = _norm(mixed)
    thr = float(np.percentile(mixed, pal["ign_q"]))
    span = max(1e-3, 1.0 - thr)
    m = np.clip((mixed - thr) / span, 0.0, 1.0)
    # fill the ignited BODY (not just the peaks): gamma<1 lifts mid-mask toward full ignition
    return np.power(m, float(pal.get("fill_gamma", 0.62))).astype(np.float32)


# =====================================================================  carve texture
_CARVE_CACHE = {}


def _carve_field(h, w, seed, gain):
    """FRACTURED-math carved texture (worley crack web) 0..1 used to TEXTURE the ignited
    clearcoat so the highlight breaks into facets/cracks (decorrelated from the hot mask).
    Falls back to multi-octave noise if scipy is unavailable. Computed small + upscaled,
    and cached per (h,w,seed) so a batch of modes for one flame pays the cost once."""
    key = (h, w, int(seed))
    if key in _CARVE_CACHE:
        base = _CARVE_CACHE[key]
        return np.power(base, max(0.4, 1.0 / max(0.4, gain))).astype(np.float32)
    try:
        from engine.paint_v2 import fractured_math as fm
        # crack web at low res; cells scale with canvas so it stays fine but not noisy.
        # res capped low so even the FIRST (scipy-cold) call renders < 3s at 2048.
        # res trimmed 2026-06-24 (pass-3 timing margin) so the heaviest flame PAINTS stay
        # comfortably < 3s end-to-end; coarser worley, still fine after the upscale.
        cells = int(np.clip(110 + (h // 28), 110, 260))
        field = fm.worley(h, w, seed, res=min(300, max(200, h // 8)),
                          cells=cells, kind="cracks")
    except Exception:
        # self-contained fallback: ridged multi-octave value noise
        small = max(64, h // 8)
        rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
        acc = np.zeros((small, small), np.float32)
        amp, f = 1.0, 4
        for o in range(5):
            g = rng.random((max(2, f), max(2, f))).astype(np.float32)
            acc += amp * cv2.resize(g, (small, small), interpolation=cv2.INTER_CUBIC)
            amp *= 0.55
            f *= 2
        ridge = 1.0 - np.abs(2.0 * (acc / acc.max()) - 1.0)
        field = cv2.resize(ridge, (w, h), interpolation=cv2.INTER_CUBIC)
    field = _norm(field)
    _CARVE_CACHE[key] = field
    # push toward facets/cracks with the palette carve gain
    return np.power(field, max(0.4, 1.0 / max(0.4, gain))).astype(np.float32)


def _empty_spec(h, w):
    return np.zeros((h, w, 3), np.float32)


# ============================================================  color-shift engine (2026-06-24)
def _color_shift_spec(paint, pal, seed, *, mode="ignite", strength=1.0):
    """FRACTURED-SOUL-style COLOR-SHIFT flame spec (rebuild 2026-06-24, owner directive).

    NOT a calm-matte base with sparse ignition. Built like FRACTURED SOULS/MINDS: a DENSE
    near-chrome field (high Metallic = colour amplifier, high Clearcoat, roughness at a
    GLOSS FLOOR) so the WHOLE surface reflects and the env hue SHIFTS across it. Fine
    DECORRELATED fractured fields cut slightly-different-hue micro-facets so it 'dances'.
    The FLAME's hot geometry is CUT into the design: it opens roughness reveal lanes +
    razor sparkle pins and lifts M/Cc so the flame POPS out of the dancing field (and the
    spec traces the paint). Iron-safe: M<=238 (no mirror plate), roughness>=15, clearcoat>=16.
    Single 2048 pass < 3s (reuses one cached worley field; second field is a free transform)."""
    paint = _f32(paint)
    h, w = paint.shape[:2]
    s = float(np.clip(strength, 0.0, 1.4))
    palm = dict(pal)
    if mode == "dance":
        palm["edge_bias"] = min(0.7, palm.get("edge_bias", 0.35) + 0.25)
    core = trace_hot(paint, "core")          # the exact signal spec_traces_paint measures
    edge = trace_hot(paint, "edge")
    # ignition mask inlined from _hot_mask but REUSING core/edge above (no 2x recompute -> faster)
    _mixed = _norm((1.0 - palm["edge_bias"]) * core + palm["edge_bias"] * edge)
    _thr = float(np.percentile(_mixed, palm["ign_q"]))
    _span = max(1e-3, 1.0 - _thr)
    hot = np.power(np.clip((_mixed - _thr) / _span, 0.0, 1.0), float(palm.get("fill_gamma", 0.62))).astype(np.float32)
    cA = _carve_field(h, w, seed, pal.get("carve_gain", 1.0))
    # second field: a near-free decorrelation of cA (avoids a 2nd worley render -> timing)
    cB = _norm(0.5 * np.flipud(cA) + 0.5 * np.roll(cA, (h // 6, w // 4), axis=(0, 1)))

    # ---- dense near-chrome COLOR-SHIFT base (SOUL physics, kept under mirror 240) ----
    M_BASE, B_BASE, G_FLOOR, G_LANE = 214.0, 234.0, 26.0, 82.0
    M_FLAME, B_FLAME = 28.0, 22.0
    m_amp = 12.0 + 4.0 * s   # deeper decorrelated cuts -> more visible "slightly different hues" dance
    b_amp = 8.0
    # the FLAME lifts metal+clearcoat (so the spec TRACES the paint + the flame pops out);
    # fine decorrelated micro-cuts shift the local (M,Cc) ratio -> reflected HUE dances.
    # The cuts RIDE the flame (ng): full on the hot geometry, calmer (smoother dense field)
    # off it -> "flames cut into the spec" + the flame stays the dominant traced structure.
    # adapt the cut amplitude to how much flame structure exists: a DIFFUSE flame
    # (low core variance) gets a cleaner, more-traceable spec; a SHARP flame keeps the
    # full dance. Keeps low-contrast paints (ember_storm) above the traces gate.
    nv = float(np.clip(np.std(core) / 0.18, 0.09, 1.0))
    ng = (0.32 + 0.68 * core) * nv
    M = M_BASE + m_amp * (2.0 * cA - 1.0) * ng + M_FLAME * core
    B = B_BASE + b_amp * (2.0 * cB - 1.0) * ng + B_FLAME * core
    # ---- ROUGHNESS carries the DESIGN: gloss floor opened into reveal lanes by the FLAME
    aperture = np.clip(hot * (0.7 + 0.3 * cA) + 0.45 * edge, 0.0, 1.0)
    G = G_FLOOR + (G_LANE - G_FLOOR) * aperture
    # razor sparkle pins where the hot flame meets crack ridges -> 'popping' glints
    pins = ((hot > 0.55) & (cA > 0.78)).astype(np.float32)
    G = G * (1.0 - pins) + 15.0 * pins

    if mode == "dance":
        # MAX angle-flash: extra razor pins on the flame SKELETON (roughness facets that
        # flash at different angles). Keep M core-led (no extra noise) so it still traces.
        pins2 = ((edge > 0.5) & (cB > 0.7)).astype(np.float32)
        G = G * (1.0 - pins2) + 15.0 * pins2
    elif mode == "topo":
        # layered relief depth: deepen cuts by flame relief so it reads raised/3D
        L = _norm(_luma(paint))
        relief = np.zeros((h, w), np.float32)
        for i in range(3):
            sig = max(0.8, (h / 700.0) * (2 ** i))
            Lb = cv2.GaussianBlur(L, (0, 0), sig)
            gx = cv2.Sobel(Lb, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(Lb, cv2.CV_32F, 0, 1, ksize=3)
            relief += (0.6 ** i) * np.sqrt(gx * gx + gy * gy)
        relief = _norm(relief)
        G = np.clip(G + 22.0 * (0.5 - relief), 15.0, 110.0)
        B = B + 6.0 * relief

    spec = _empty_spec(h, w)
    spec[..., 0] = np.clip(M, 0.0, 238.0)   # stay below mirror-chrome (240) -> iron-safe
    spec[..., 1] = G
    spec[..., 2] = B
    return _finalize(spec)


# =====================================================================  spec_ignite
def spec_ignite(paint, *, palette="classic", frac="auto", strength=1.0):
    """CALM near-matte base IGNITED only where the flame is hot.

    Calm surround: low metallic, high roughness, clearcoat = 0 (true matte, safely OUT
    of the 1..15 whitewash band). On the hot mask: near-max metallic + a FRACTURED-math-
    carved clearcoat (>= CC_FLOOR) + low roughness, so the flame's hot geometry lights up.

    frac='auto' uses the palette's ign_q; pass a float 0..1 to override (fraction of the
    canvas that ignites; smaller = tighter ignition).
    strength scales the ignition intensity (0..~1.4).
    """
    paint = _f32(paint)
    pal = dict(_palette(palette))
    if frac != "auto":
        pal["ign_q"] = float(np.clip((1.0 - float(frac)) * 100.0, 40.0, 96.0))
    return _color_shift_spec(paint, pal, _seed_from_paint(paint), mode="ignite", strength=strength)


# =====================================================================  spec_topo
def spec_topo(paint, *, palette="classic", layers=3):
    """DEPTH: a relief/normal-like roughness+clearcoat built from LAYERED luminance
    gradients so the flame reads as raised/carved 3D. Brighter+steeper paint = raised,
    glossier facets; flat dark areas = matte and sunk. Still traces the hot geometry
    (the relief follows the flame), with low correlation between R and Cc."""
    paint = _f32(paint)
    return _color_shift_spec(paint, dict(_palette(palette)), _seed_from_paint(paint), mode="topo")


# =====================================================================  spec_dance
def spec_dance(paint, *, palette="classic"):
    """GHOST-SHIFT on the hot mask so the flame FLASHES / dances under moving light:
    HIGH metallic + pattern-carved clearcoat + LOW roughness exactly on the hot flame,
    calm matte elsewhere. The carved clearcoat means different facets catch the light at
    different angles -> iRacing's env light shifts across the flame as the car turns."""
    paint = _f32(paint)
    return _color_shift_spec(paint, dict(_palette(palette)), _seed_from_paint(paint), mode="dance")


# =====================================================================  finalize (iron rules)
def _finalize(spec_f):
    """Apply the iron rules, in-engine-identical, and return HxWx3 uint8.
    Mirrors shokker_engine_v2._enforce_iron_rules (CC>0 -> >=16, R floor on non-mirror)."""
    s = np.asarray(spec_f, np.float32)
    M = s[..., 0]
    R = s[..., 1]
    B = s[..., 2]
    # Clearcoat: 0 stays 0 (matte); any positive value floored to CC_FLOOR (skip 1..15).
    cc_active = B > 0
    s[..., 2] = np.where(cc_active, np.maximum(B, CC_FLOOR), 0)
    # Roughness floor on non-mirror pixels.
    s[..., 1] = np.where(M < CHROME_M_THRESHOLD,
                         np.maximum(R, ROUGHNESS_FLOOR_NONMIRROR), R)
    s = np.nan_to_num(s, nan=0.0, posinf=255.0, neginf=0.0)
    return np.clip(s, 0, 255).astype(np.uint8)


# =====================================================================  GATE HELPERS
def spec_traces_paint(spec, paint):
    """Correlation in [0,1] between the spec's BRIGHT structure and the paint's hot mask.
    A real ignition lights the same pixels as the bright flame. Require >= 0.5.

    Spec brightness = a clearcoat-led ignition signal (Cc carries the carved highlight,
    M the metallic core). Paint hot = the smoothed luma hot mask."""
    spec = np.asarray(spec, np.float32)
    M = spec[..., 0] / 255.0
    B = spec[..., 2] / 255.0
    ign = _norm(0.6 * B + 0.4 * M)            # where the spec "lights up"
    hot = trace_hot(paint, "core")
    # downsample both to compare structure (and dodge tiny misalignments)
    a = cv2.resize(ign, (64, 64), interpolation=cv2.INTER_AREA).ravel()
    b = cv2.resize(_norm(hot), (64, 64), interpolation=cv2.INTER_AREA).ravel()
    if a.std() < 1e-6 or b.std() < 1e-6:
        return 0.0
    c = float(np.corrcoef(a, b)[0, 1])
    return max(0.0, c)   # negative correlation = anti-traces = fail (clamped to 0)


def spec_iron_safe(spec):
    """Fail-closed iron-rule check. Returns (ok: bool, reason: str).
    Mirrors the thresholds in shokker_engine_v2._enforce_iron_rules:
      - clearcoat never in the 1..15 whitewash band,
      - roughness >= ROUGHNESS_FLOOR_NONMIRROR where M < CHROME_M_THRESHOLD (non-mirror),
      - no giant flat chrome plate (M>=240 over too much of the canvas)."""
    spec = np.asarray(spec)
    if spec.ndim != 3 or spec.shape[2] < 3:
        return False, "spec must be HxWx3 (R=M,G=Rough,B=Cc)"
    M = spec[..., 0].astype(np.int32)
    R = spec[..., 1].astype(np.int32)
    B = spec[..., 2].astype(np.int32)
    # 1) clearcoat whitewash band
    bad_cc = int(np.count_nonzero((B >= _WHITEWASH_LO) & (B <= _WHITEWASH_HI)))
    if bad_cc:
        return False, f"clearcoat in 1..15 whitewash band on {bad_cc} px"
    # 2) roughness floor on non-mirror pixels
    nonmirror = M < CHROME_M_THRESHOLD
    bad_r = int(np.count_nonzero(nonmirror & (R < ROUGHNESS_FLOOR_NONMIRROR)))
    if bad_r:
        return False, f"roughness < {ROUGHNESS_FLOOR_NONMIRROR} on {bad_r} non-mirror px"
    # 3) no giant flat chrome plate
    chrome_frac = float(np.count_nonzero(M >= CHROME_M_THRESHOLD)) / M.size
    if chrome_frac > _MAX_CHROME_FRACTION:
        return False, f"giant chrome plate: M>=240 over {chrome_frac:.0%} of canvas"
    return True, "ok"
