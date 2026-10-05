"""color_science_2026 — ELABORATE per-finish spec engine for the COLOR SCIENCE category.

Built 2026-06-21 for the owner's total COLOR SCIENCE redirect: Chameleon / Prizm /
Color Clash / Gradient Directional / Gradient Vortex / Gradient Extended must each have
UNIQUE, dynamic, deep specs — NO shared spec, NO duplicates. This module provides:

  1. CANDY-DEPTH response  — the owner's Pic-1 look: a depth field drives a *wet glossy
     core* (Cc≈16, R low, M high) blending out to a *satin edge* (Cc≈175, R≈102). This is
     what makes a finish read as having real 3-D depth under the moving sun.

  2. A palette of ELABORATE high-math LOOK GENERATORS, each a structurally distinct field
     (so two finishes never look alike): spectral log-spiral, holographic voronoi mosaic,
     oil-slick thin-film, crystal facets, iridescent domain-warp flow, ripple caustics,
     guilloché interference. Each returns a (structure, shimmer) pair in 0..1.

  3. `compose_cs_spec(...)` — one call per finish: pick a look + a depth field + per-channel
     recipe, and out comes a decorrelated, iron-legal, motion-capable (H,W,4) uint8 spec
     whose three channels each ride DIFFERENT geometry. Uniqueness comes from the look
     choice + seed + recipe, not from a shared template.

Pure numpy (+ optional cv2 accel via depth3d). Channels: M=metallic, R=roughness
(15..255, low=glossy), Cc=clearcoat (16=max gloss .. 255=dull), A=255.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple
import numpy as np

from engine.paint_v2 import depth3d_2026 as _d3

__all__ = [
    "candy_depth", "spectral_spiral", "holographic_mosaic", "oilslick_thinfilm",
    "crystal_facets", "iridescent_flow", "ripple_caustics", "guilloche",
    "LOOKS", "compose_cs_spec",
]

_TWO_PI = 2.0 * np.pi


def _n01(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    lo = float(a.min()); rng = float(np.ptp(a))
    return np.zeros_like(a) if rng < 1e-9 else (a - lo) / rng


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _coords(h: int, w: int):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx / max(1, w - 1), yy / max(1, h - 1)


def _warp(x, y, seed, amp=0.18, base=5):
    """Domain-warp the coordinate grid with low-freq fbm so motifs aren't axis-aligned."""
    h, w = x.shape
    wx = _d3._fbm(h, w, seed * 7 + 3, octaves=4, base=base)
    wy = _d3._fbm(h, w, seed * 7 + 9, octaves=4, base=base)
    return x + (wx - 0.5) * amp, y + (wy - 0.5) * amp


# =====================================================================================
# 1. CANDY-DEPTH response — wet glossy core -> satin edge (owner Pic 1)
# =====================================================================================
def candy_depth(depth01: np.ndarray, *, m_lo=110.0, m_hi=236.0,
                r_core=25.0, r_edge=112.0, cc_core=16.0, cc_edge=178.0,
                gamma=1.35) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map a 0..1 DEPTH field (1=deep wet core, 0=thin satin edge) to (M,R,Cc).

    Core  -> high metallic, low roughness, max-gloss clearcoat (wet, mirror-deep).
    Edge  -> lower metallic, satin roughness, dull clearcoat (matte rim).
    The gamma crushes the transition toward the core so the wet pool reads tight + glossy,
    exactly the Pic-1 response (Cc 16/R 25 center, Cc ~175/R ~102 edge).
    """
    d = np.clip(depth01.astype(np.float32), 0, 1)
    dc = np.power(d, gamma)
    M = m_lo + (m_hi - m_lo) * dc
    R = r_edge + (r_core - r_edge) * dc
    Cc = cc_edge + (cc_core - cc_edge) * dc
    return M, R, Cc


# =====================================================================================
# 2. ELABORATE LOOK GENERATORS — each returns (structure01, shimmer01)
#    structure = the macro motif (drives depth); shimmer = fine angle-flash carrier.
# =====================================================================================
def spectral_spiral(h, w, seed, *, arms=5.0, twist=6.0, work_cap=640):
    """Logarithmic color-spiral interference (owner Pic 3 'spectral spiral')."""
    H, W = h, w
    if max(h, w) > work_cap:
        s = work_cap / max(h, w); H, W = max(2, int(h * s)), max(2, int(w * s))
    x, y = _coords(H, W); x, y = _warp(x, y, seed, amp=0.10)
    cx, cy = 0.5, 0.5
    dx, dy = x - cx, y - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-4
    th = np.arctan2(dy, dx)
    spiral = np.sin(arms * th + twist * np.log(r) * _TWO_PI * 0.5 + float(seed % 13))
    structure = _n01(0.5 + 0.5 * spiral)
    shimmer = _n01(np.sin((th * arms * 3.0 + r * 60.0)) * np.cos(r * 90.0 + th * 7.0))
    return _d3._resize(structure, h, w), _d3._resize(shimmer, h, w)


def holographic_mosaic(h, w, seed, *, cells=26.0, work_cap=640):
    """Voronoi facets, each carrying its own diffraction phase (Pic 3 'holographic mosaic')."""
    H, W = h, w
    if max(h, w) > work_cap:
        s = work_cap / max(h, w); H, W = max(2, int(h * s)), max(2, int(w * s))
    rng = _rng(seed * 5 + 1)
    n = max(8, int(cells))
    px = rng.random(n).astype(np.float32); py = rng.random(n).astype(np.float32)
    phase = rng.random(n).astype(np.float32) * _TWO_PI
    x, y = _coords(H, W); x, y = _warp(x, y, seed, amp=0.06)
    # nearest-seed facet id + distance (chunked to bound memory)
    best = np.full((H, W), 1e9, np.float32); fid = np.zeros((H, W), np.int32)
    d2nd = np.full((H, W), 1e9, np.float32)
    for i in range(n):
        d = (x - px[i]) ** 2 + (y - py[i]) ** 2
        closer = d < best
        d2nd = np.where(closer, best, np.minimum(d2nd, d))
        fid = np.where(closer, i, fid); best = np.where(closer, d, best)
    facet_phase = phase[fid]
    structure = _n01(0.5 + 0.5 * np.cos(facet_phase + np.sqrt(best) * 14.0))
    edge = _n01(np.sqrt(d2nd) - np.sqrt(best))           # bright crack between facets
    shimmer = _n01(np.cos(facet_phase * 3.0 + np.sqrt(best) * 80.0) * (1.0 - edge))
    return _d3._resize(structure, h, w), _d3._resize(shimmer, h, w)


def oilslick_thinfilm(h, w, seed, *, bands=7.0, work_cap=640):
    """Domain-warped thin-film interference — oily, smoothly-shifting spectral sheets."""
    H, W = h, w
    if max(h, w) > work_cap:
        s = work_cap / max(h, w); H, W = max(2, int(h * s)), max(2, int(w * s))
    thick = _d3._fbm(H, W, seed * 11 + 5, octaves=5, base=6)   # film thickness
    x, y = _coords(H, W)
    structure = _n01(0.5 + 0.5 * np.sin(thick * _TWO_PI * bands + (x + y) * 2.0))
    shimmer = _n01(0.5 + 0.5 * np.cos(thick * _TWO_PI * bands * 2.3 + float(seed % 7)))
    return _d3._resize(structure, h, w), _d3._resize(shimmer, h, w)


def crystal_facets(h, w, seed, *, cells=40.0, work_cap=640):
    """Angular crystalline facets — sharp planar shards each catching light differently."""
    st, sh = holographic_mosaic(h, w, seed * 3 + 7, cells=cells, work_cap=work_cap)
    # sharpen into hard planar shards. clip first: cv2 cubic upscale can overshoot <0,
    # and power(negative, 0.6) -> NaN (only bites above the work cap, where resize runs).
    st = _n01(np.power(np.clip(st, 0.0, 1.0), 0.6))
    return st, sh


def iridescent_flow(h, w, seed, *, scale=4.0, work_cap=640):
    """Smooth chameleon iridescence — multi-octave domain-warped flow, soft color travel."""
    H, W = h, w
    if max(h, w) > work_cap:
        s = work_cap / max(h, w); H, W = max(2, int(h * s)), max(2, int(w * s))
    f1 = _d3._fbm(H, W, seed * 13 + 2, octaves=5, base=int(scale))
    f2 = _d3._fbm(H, W, seed * 13 + 8, octaves=5, base=int(scale) + 2)
    flow = _n01(f1 + 0.5 * np.sin(f2 * _TWO_PI * 2.0))
    shimmer = _n01(np.sin(f1 * _TWO_PI * 9.0) * np.cos(f2 * _TWO_PI * 7.0))
    return _d3._resize(flow, h, w), _d3._resize(shimmer, h, w)


def ripple_caustics(h, w, seed, *, rings=9.0, work_cap=640):
    """Concentric warped caustic ripples — pooled-light depth, great for vortex/gradient."""
    H, W = h, w
    if max(h, w) > work_cap:
        s = work_cap / max(h, w); H, W = max(2, int(h * s)), max(2, int(w * s))
    x, y = _coords(H, W); x, y = _warp(x, y, seed, amp=0.14, base=4)
    rng = _rng(seed); cx, cy = 0.35 + 0.3 * rng.random(), 0.35 + 0.3 * rng.random()
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    structure = _n01(0.5 + 0.5 * np.sin(r * _TWO_PI * rings))
    shimmer = _n01(np.abs(np.cos(r * _TWO_PI * rings * 2.0)))
    return _d3._resize(structure, h, w), _d3._resize(shimmer, h, w)


def guilloche(h, w, seed, *, a=11.0, b=13.0, work_cap=640):
    """Guilloché engine-turned interference lattice — currency-grade fine-detail flash."""
    H, W = h, w
    if max(h, w) > work_cap:
        s = work_cap / max(h, w); H, W = max(2, int(h * s)), max(2, int(w * s))
    x, y = _coords(H, W); x, y = _warp(x, y, seed, amp=0.05)
    g = np.sin(x * _TWO_PI * a) * np.sin(y * _TWO_PI * b) + \
        np.sin((x + y) * _TWO_PI * (a * 0.6)) * 0.6
    structure = _n01(0.5 + 0.5 * g)
    shimmer = _n01(np.cos(x * _TWO_PI * a * 2.0 - y * _TWO_PI * b * 2.0))
    return _d3._resize(structure, h, w), _d3._resize(shimmer, h, w)


LOOKS = {
    "spectral_spiral": spectral_spiral,
    "holographic_mosaic": holographic_mosaic,
    "oilslick_thinfilm": oilslick_thinfilm,
    "crystal_facets": crystal_facets,
    "iridescent_flow": iridescent_flow,
    "ripple_caustics": ripple_caustics,
    "guilloche": guilloche,
}


# =====================================================================================
# 3. COMPOSE — one elaborate, unique, decorrelated, candy-depth spec per finish
# =====================================================================================
def compose_cs_spec(shape, seed, sm, recipe: Dict) -> np.ndarray:
    """Build a (H,W,4) uint8 COLOR SCIENCE spec for ONE finish.

    recipe keys:
        look (str)        : which LOOKS generator (the finish's signature geometry).
        look_kwargs (dict): generator params (arms/cells/bands/...) — vary per finish.
        depth_from (str)  : 'structure' | 'invert' | 'shimmer' — what drives candy-depth.
        candy (dict)      : candy_depth overrides (m_lo/m_hi/r_core/r_edge/cc_core/cc_edge/gamma).
        phase (float)     : sun-angle for the traveling motion glint.
        motion (float)    : 0..1 weight of motion into M.
        shimmer_gain (float): metallic-flake glint weight into M.
        relief (float)    : fake-3D bevel relief depth (0..~40).
        decorrelate (bool): give R/Cc their own bevel/grain geometry (default True).
        blend (float)     : decorrelation blend strength.
    """
    h, w = shape[:2] if len(shape) >= 2 else shape
    h, w = int(h), int(w)
    seed = int(seed)
    look = recipe.get("look", "iridescent_flow")
    gen = LOOKS.get(look, iridescent_flow)
    structure, shimmer = gen(h, w, seed, **recipe.get("look_kwargs", {}))

    # DIVERSITY: blend a SECOND look so two finishes never share one structure.
    # (7 looks -> dozens of distinct hybrids via look2 x blend ratio x blend op.)
    look2 = recipe.get("look2")
    if look2 and look2 in LOOKS and look2 != look:
        s2, sh2 = LOOKS[look2](h, w, seed * 7 + 13, **recipe.get("look2_kwargs", {}))
        lb = float(np.clip(recipe.get("look_blend", 0.5), 0.0, 1.0))
        op = recipe.get("blend_op", "mix")
        if op == "mult":
            structure = _n01(structure * (0.35 + 0.65 * s2))
        elif op == "max":
            structure = _n01(np.maximum(structure, s2 * (0.6 + 0.4 * lb)))
        elif op == "diff":
            structure = _n01(np.abs(structure - s2) * (0.5 + lb))
        else:  # mix
            structure = _n01((1.0 - lb) * structure + lb * s2)
        shimmer = _n01((1.0 - lb) * shimmer + lb * sh2)

    df = recipe.get("depth_from", "structure")
    depth = {"structure": structure, "invert": 1.0 - structure, "shimmer": shimmer}.get(df, structure)
    # smooth the depth a touch so the wet core pools instead of speckling
    depth = _n01(depth)

    M, R, Cc = candy_depth(depth, **recipe.get("candy", {}))

    smf = float(np.clip(sm, 0.0, 1.0))
    # metallic flash: fold the fine shimmer + a traveling motion band into M (sun flicker)
    sg = float(recipe.get("shimmer_gain", 40.0))
    M = M + (shimmer - 0.5) * sg * smf
    mo = float(recipe.get("motion", 0.0))
    if mo > 0.0:
        motion = _d3.traveling_colorshift(structure, float(recipe.get("phase", 0.0)),
                                          bands=6.0, sharpness=2.0)
        M = M + (motion - 0.5) * 60.0 * mo * smf

    # DYNAMISM GUARANTEE: a skewed look distribution (esp. with depth_from='invert') can
    # concentrate the depth field and flatten M. Never ship a dull metallic — if M came out
    # low-variance, inject the (full-range) look structure so the finish stays dynamic.
    if float(np.std(M)) < 24.0:
        M = M + (_n01(structure) - 0.5) * 82.0

    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.clip(R, 15, 255).astype(np.float32)
    Cc = np.clip(Cc, 16, 255).astype(np.float32)

    if recipe.get("decorrelate", True):
        relief = float(recipe.get("relief", 24.0))
        blend = float(recipe.get("blend", 0.66))
        M, R, Cc = _d3.decorrelate_envelope(M, R, Cc, seed=seed * 3 + 17,
                                            blend=blend, relief=relief)

    spec = np.stack([np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(Cc, 16, 255),
                     np.full((h, w), 255.0, np.float32)], axis=-1).astype(np.uint8)
    return _d3.enforce_iron_rules(spec)


def _self_test():
    import time
    def corr(a, b):
        a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
        a -= a.mean(); b -= b.mean()
        return float((a * b).sum() / ((np.sqrt((a*a).sum())*np.sqrt((b*b).sum())) + 1e-9))
    print("color_science_2026 self-test")
    for look in LOOKS:
        t = time.time()
        spec = compose_cs_spec((2048, 2048), 7, 1.0,
                               {"look": look, "motion": 0.4, "phase": 1.1, "relief": 26})
        dt = time.time() - t
        M, R, Cc = spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]
        mx = max(abs(corr(M, R)), abs(corr(M, Cc)), abs(corr(R, Cc)))
        cc_ok = bool(((Cc == 0) | (Cc >= 16)).all())
        nc = M < 240; r_ok = bool((R[nc] >= 15).all()) if nc.any() else True
        print(f"  {look:20s} {dt:4.2f}s maxcorr={mx:.2f} M.std={M.std():5.1f} "
              f"Cc[{Cc.min()}..{Cc.max()}] iron={cc_ok and r_ok}")


if __name__ == "__main__":
    _self_test()
