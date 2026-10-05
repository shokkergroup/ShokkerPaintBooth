# -*- coding: utf-8 -*-
"""FRACTURED FOUNDRY KIT (2026-08-30) — the worked-metal shader.

Owner mandate 2026-08-30: *"THEN also build out FRACTURED FOUNDRY with 50 of its
own finishes because I like the idea so much. Masculine, industrial."*

FOUNDRY is deliberately a DIFFERENT MECHANISM from its siblings — that is the
whole point of giving a category an identity:
  * FRACTURED RELICS  = thin-film interference over aged ritual geometry;
  * FRACTURED TESSERA = jewel panes divided by ignitable cames;
  * FRACTURED FOUNDRY = a SURFACE, lit. Every finish is a height field left by a
    process — a tool, a hammer, an arc, a pour — shaded through an anisotropic
    metal model, then tinted by what the heat or the chemistry did to it.

Metal does not read as metal because of its colour. It reads because of the way
its highlight STRETCHES ACROSS the tooling: a brushed panel throws a long streak
perpendicular to the grain, a milled one throws arcs, a cast one throws nothing
at all. So the shader is anisotropic by construction:

    height  -> normals -> (diffuse + anisotropic specular along the tool axis)
            -> heat/oxide tint -> the metal's own colour
    spec    -> M from the metal and its coating, R carved ALONG the tooling
               (low across the grain, high along it), Cc from the coating

THE TOOTH LAW: a foundry surface is never smooth. Every finish carries at least
two scales of tooling — the process mark (mill lines, hammer facets, weld
ripples) and the mill tooth underneath it — because a single-scale metal reads
as plastic.
"""
from __future__ import annotations

import cv2
import numpy as np

WORK = 1152
GEN = 768
_TAU = 6.283185307179586


def rng(seed, salt=0):
    return np.random.default_rng([(int(seed) * 100003) & 0x7FFFFFFF, int(salt) & 0x7FFFFFFF])


def coords(res):
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    return yy, xx


def frac(a):
    a = np.asarray(a, np.float32)
    return (a - np.floor(a)).astype(np.float32)


def n01(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-9)


def gauss(a, s):
    return cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), float(s))


def h2(cx, cy, salt=0):
    return frac(np.sin(cx * 127.1 + cy * 311.7 + salt * 74.7) * 43758.5453)


def fbm(res, r, octaves=4, base=4, gain=0.55):
    acc = np.zeros((res, res), np.float32)
    amp, tot, s = 1.0, 0.0, int(base)
    for _ in range(int(octaves)):
        g = r.random((s, s)).astype(np.float32)
        acc += amp * cv2.resize(g, (res, res), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= gain
        s = min(s * 2, res)
        if s >= res:
            break
    return acc / max(tot, 1e-9)


def cells(res, pitch, salt, jit=0.55, taps=9, need2=True):
    """Jittered-grid nearest-feature field -> (dx, dy, d1, id1, d2)."""
    g = float(pitch)
    yy, xx = coords(res)
    cu, cv_ = np.floor(xx / g), np.floor(yy / g)
    n = int(np.ceil(res / g)) + 4
    ii = np.arange(-1, n, dtype=np.float32)
    CU, CV = np.meshgrid(ii, ii)
    JX, JY, JB = h2(CU, CV, salt), h2(CU, CV, salt + 57), h2(CU, CV, salt + 91)
    iu, iv = cu.astype(np.int32) + 1, cv_.astype(np.int32) + 1
    best = np.full((res, res), 1e9, np.float32)
    second = np.full((res, res), 1e9, np.float32) if need2 else None
    bdx = np.zeros((res, res), np.float32); bdy = np.zeros((res, res), np.float32)
    bid = np.zeros((res, res), np.float32)
    offs = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1))[:int(taps)]
    for di, dj in offs:
        ix, iy = np.clip(iu + di, 0, n), np.clip(iv + dj, 0, n)
        fx = (cu + (di + 0.5) + (JX[iy, ix] - 0.5) * jit) * g
        fy = (cv_ + (dj + 0.5) + (JY[iy, ix] - 0.5) * jit) * g
        ddx, ddy = xx - fx, yy - fy
        d = ddx * ddx + ddy * ddy
        mm = d < best
        if need2:
            second = np.where(mm, best, np.minimum(second, d))
        best = np.where(mm, d, best)
        bdx = np.where(mm, ddx, bdx); bdy = np.where(mm, ddy, bdy)
        bid = np.where(mm, JB[iy, ix], bid)
    return bdx, bdy, np.sqrt(best), bid, (np.sqrt(second) if need2 else None)


def tooth(res, seed, k=1.0):
    """THE TOOTH LAW: the mill finish under every process mark. Two dome
    lattices at 4.2 and 2.6px — a shape field, never pixel noise."""
    yy, xx = coords(res)
    acc = np.zeros((res, res), np.float32)
    for c, w, salt in ((4.2 * res / GEN, 0.62, 811), (2.6 * res / GEN, 0.38, 823)):
        du, dv = frac(xx / c) - 0.5, frac(yy / c) - 0.5
        dome = np.clip(1.0 - 3.4 * (du * du + dv * dv), 0.0, 1.0)
        acc += (h2(np.floor(xx / c), np.floor(yy / c), seed % 7919 + salt) - 0.5) * dome * w
    return (acc * float(k)).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# METALS — base colour + how metallic the plain surface is
# ════════════════════════════════════════════════════════════════════════════
METALS = {
    "steel":     ((0.62, 0.64, 0.67), 236.0),
    "iron":      ((0.46, 0.46, 0.48), 218.0),
    "castiron":  ((0.30, 0.30, 0.32), 196.0),
    "brass":     ((0.70, 0.60, 0.38), 240.0),
    "bronze":    ((0.60, 0.46, 0.31), 234.0),
    "copper":    ((0.83, 0.48, 0.31), 242.0),
    "aluminium": ((0.76, 0.78, 0.80), 244.0),
    "titanium":  ((0.60, 0.60, 0.64), 232.0),
    "zinc":      ((0.70, 0.72, 0.74), 226.0),
    "nickel":    ((0.72, 0.70, 0.66), 240.0),
    "blued":     ((0.20, 0.24, 0.34), 224.0),
    "graphite":  ((0.24, 0.25, 0.27), 190.0),
}

# heat-oxide ladder (the temper colours a smith reads off the steel)
# Straw -> bronze -> plum -> blue -> blue-grey. Deliberately stops short of the
# lilac/pink end: past that it stops reading as tempered steel and starts
# reading as an oil slick, which is the wrong category entirely.
_TEMPER = np.array([[0.60, 0.61, 0.63], [0.72, 0.63, 0.42], [0.66, 0.47, 0.27],
                    [0.50, 0.28, 0.27], [0.34, 0.28, 0.42], [0.22, 0.31, 0.50],
                    [0.26, 0.42, 0.50], [0.42, 0.46, 0.46]], np.float32)


def temper(t):
    """Map 0..1 to the oxide temper ladder (straw -> bronze -> purple -> blue)."""
    p = np.clip(t, 0, 1) * (len(_TEMPER) - 1)
    i = np.minimum(np.floor(p).astype(np.int32), len(_TEMPER) - 2)
    f = (p - i)[..., None]
    return _TEMPER[i] * (1 - f) + _TEMPER[i + 1] * f


# ════════════════════════════════════════════════════════════════════════════
# THE SHADER
# ════════════════════════════════════════════════════════════════════════════

def normals(height, strength=1.0):
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) * strength
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) * strength
    return gx, gy


def metal_art(height, recipe, res):
    """height (0..1) + recipe -> lit metal RGB.

    The anisotropic term is what sells it: the highlight is stretched ALONG the
    tool axis, so brushed steel throws a long streak and cast iron throws none.
    """
    d = recipe
    seed = int(d.get("seed", 3))
    base_rgb, _m = METALS.get(d.get("metal", "steel"), METALS["steel"])
    base = np.asarray(base_rgb, np.float32)

    h = np.clip(np.asarray(height, np.float32), 0.0, 1.0)
    h = h + tooth(res, seed, float(d.get("tooth", 0.16)))
    gx, gy = normals(h, float(d.get("relief", 14.0)))

    # light from upper-left; the anisotropy axis is the tool direction
    a = float(d.get("axis", 0.0))
    ca, sa = np.cos(a), np.sin(a)
    along = gx * ca + gy * sa            # slope along the tooling
    across = -gx * sa + gy * ca          # slope across it
    lam = np.clip(0.52 - 0.42 * (across * 0.7 + along * 0.3), 0.0, 1.4)   # diffuse

    aniso = float(d.get("aniso", 0.75))
    # a stretched highlight: sharp across the grain, broad along it
    spec = np.exp(-((across * 2.2) ** 2) / (0.30 + 1e-6)) * np.exp(-((along * (1.0 - aniso) * 2.2) ** 2) / 0.9)
    # cap the highlight: an unclamped anisotropic lobe blows to pure white and
    # the panel reads as printed stripes rather than lit metal
    spec = np.minimum(spec, 0.62) * float(d.get("gloss", 0.85))

    col = base[None, None, :] * (0.34 + 0.78 * lam)[..., None]
    # HEAT / OXIDE TINT. Applied flat across a smooth field this reads as an
    # oil slick — full-spectrum rainbow on what should be hot steel. Real temper
    # colour only appears where the metal actually got hot, and it stays in the
    # straw-bronze-purple-blue band. So: square the field (only the hot zones
    # tint), cap the blend, and keep the ladder narrow.
    ht = d.get("heat")
    if ht is not None:
        hf = np.clip(np.asarray(ht, np.float32), 0, 1) ** 2.0
        amt = float(d.get("heat_amt", 0.55))
        band = float(d.get("temper_band", 0.62))          # how far up the ladder
        col = col * (1.0 - hf[..., None] * amt) + temper(hf * band) * (hf[..., None] * amt)
    col = col + spec[..., None] * np.asarray(d.get("spec_rgb", (1.0, 0.98, 0.94)), np.float32)

    # dirt / soot / oil settles in the low ground of the tooling
    grime = float(d.get("grime", 0.0))
    if grime > 0:
        low = np.clip(1.0 - h * 1.6, 0.0, 1.0)
        col = col * (1.0 - low[..., None] * grime)
    return np.clip(col, 0.0, 1.0).astype(np.float32)


def metal_spec(height, recipe, res):
    """M/R/Cc carved from the same surface. Roughness is ANISOTROPIC: low along
    the tool axis (the highlight runs), high across it."""
    d = recipe
    seed = int(d.get("seed", 3))
    _rgb, mbase = METALS.get(d.get("metal", "steel"), METALS["steel"])
    h = np.clip(np.asarray(height, np.float32), 0.0, 1.0)
    h = h + tooth(res, seed, float(d.get("tooth", 0.16)))
    gx, gy = normals(h, float(d.get("relief", 14.0)))
    a = float(d.get("axis", 0.0))
    ca, sa = np.cos(a), np.sin(a)
    across = np.abs(-gx * sa + gy * ca)
    along = np.abs(gx * ca + gy * sa)
    # NORMALISE THE SLOPE per surface. A hammer facet and a lathe groove differ
    # in gradient by an order of magnitude, so a fixed clip gave the smooth
    # processes almost no spec travel at all (measured M sigma 10 on the milled
    # and turned cards). Percentile scaling lets every process use the full
    # roughness range that its own tooling earns.
    def _norm_slope(a_):
        hi = float(np.percentile(a_, 96.0))
        return np.clip(a_ / max(hi, 1e-5), 0.0, 1.0)
    across = _norm_slope(across)
    along = _norm_slope(along)

    M = np.full((res, res), float(d.get("metallic", mbase)), np.float32)
    M = M - across * 62.0 * float(d.get("mvar", 1.0))
    M = M + (h - 0.5) * 58.0 * float(d.get("mvar", 1.0))

    r0 = float(d.get("rough", 42.0))
    R = r0 + np.clip(across, 0, 1) * 150.0 * float(d.get("rvar", 1.0)) \
        - np.clip(along, 0, 1) * 40.0 * float(d.get("rvar", 1.0))
    R = R + (0.5 - h) * 46.0

    C = np.full((res, res), float(d.get("clear", 40.0)), np.float32)
    C = C + across * 88.0 * float(d.get("cvar", 1.0))

    # THE WEAR FIELD: no worked panel is uniform. Oil film, uneven grinding,
    # oxide bloom and handling all vary slowly across a part, and without that
    # the spec is flat at car scale even when the tooling is right.
    w = float(d.get("wear", 0.55))
    if w > 0:
        wf = n01(gauss(fbm(res, rng(seed, 401), 3, 4), res / 96.0))
        M = M - (wf - 0.45) * 60.0 * w
        R = R + (wf - 0.45) * 84.0 * w
        C = C + (wf - 0.5) * 56.0 * w

    # coating / oxide states: a real foundry panel is patchy, not uniform
    patch = d.get("patch")
    if patch is not None:
        pf = np.clip(np.asarray(patch, np.float32), 0, 1)
        pm, pr, pc = d.get("patch_spec", (60.0, 200.0, 210.0))
        M = M * (1 - pf) + pm * pf
        R = R * (1 - pf) + pr * pf
        C = C * (1 - pf) + pc * pf

    out = np.empty((res, res, 4), np.uint8)
    out[..., 0] = np.clip(M, 4, 255).astype(np.uint8)
    out[..., 1] = np.clip(R, 6, 250).astype(np.uint8)
    out[..., 2] = np.clip(C, 10, 250).astype(np.uint8)
    out[..., 3] = 255
    return out
