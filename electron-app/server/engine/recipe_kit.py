# ============================================================================
# engine/recipe_kit.py — compact, composable, CRUSHED-FINE geometry generators.
# The AI-as-compiler engine (token mandate 2026-06-10): finishes are ~15-line
# recipes over these primitives instead of bespoke 100-line files. All
# primitives are windowed/vectorized (render-time doctrine) and tuned for the
# fineness doctrine (motifs 2-10px at 2048 in the hundreds-to-thousands).
# 2-copy file (runtime-sync-manifest.json).
# ============================================================================
from __future__ import annotations

import numpy as np
import cv2

from engine.core import multi_scale_noise
from engine.color_science import oklch_ramp


def _rng(seed, off=0):
    return np.random.default_rng((int(seed) ^ off) & 0x7FFFFFFF)


def noise01(h, w, seed, scales=(2, 5, 11)):
    n = multi_scale_noise((h, w), list(scales), [0.5, 0.3, 0.2][: len(scales)], int(seed) & 0x7FFFFFFF)
    return ((np.asarray(n, np.float32) + 1.0) * 0.5).astype(np.float32)


def micro_scatter(h, w, seed, count, rad_px, kind="dot", amp=(0.5, 1.0), len_px=None):
    """Windowed micro-motif scatter -> float32 field [0,1]. kinds: dot (gauss),
    star5 (5-petal), streak (rotated line), arc (ring segment), petal (fan lobe)."""
    rng = _rng(seed, 0xA1)
    acc = np.zeros((h, w), np.float32)
    L = float(len_px or rad_px * 3)
    n = int(count)
    if n <= 0:
        return np.clip(acc, 0, 1)
    # PERF (2026-06-13): per-point scalar draws are preserved EXACTLY (the random
    # sequence is unchanged, so output is bit-identical); only the per-point
    # np.mgrid+astype is replaced by cheaper arange-broadcast windows (dy/dx
    # factorize the regular grid identically). Verified vs reference snapshot.
    _dot_sc = 3.2 if kind == "dot" else 2.2
    for _i in range(n):
        cy, cx = rng.uniform(0, h), rng.uniform(0, w)
        r = rng.uniform(0.6, 1.0) * rad_px
        a = rng.uniform(0, 2 * np.pi)
        v = rng.uniform(*amp)
        R = (L if kind == "streak" else r * _dot_sc) + 2
        y0, y1 = max(0, int(cy - R)), min(h, int(cy + R) + 1)
        x0, x1 = max(0, int(cx - R)), min(w, int(cx + R) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        dy = np.arange(y0, y1, dtype=np.float32)[:, None] - cy
        dx = np.arange(x0, x1, dtype=np.float32)[None, :] - cx
        if kind == "dot":
            m = np.exp(-(dy * dy + dx * dx) / (r * r + 1e-6))
        elif kind == "star5":
            th = np.arctan2(dy, dx) - a
            edge = r * (0.55 + 0.45 * np.cos(5.0 * th))
            m = np.clip(1.0 - np.hypot(dy, dx) / (edge + 1e-6), 0, 1) ** 1.5
        elif kind == "streak":
            u = dx * np.cos(-a) - dy * np.sin(-a)
            v2 = dx * np.sin(-a) + dy * np.cos(-a)
            wdt = max(0.7, r * 0.35)
            m = np.exp(-(v2 / wdt) ** 2) * np.clip(1.0 - np.abs(u) / L, 0, 1)
        elif kind == "arc":
            rad = np.hypot(dy, dx)
            th = np.arctan2(dy, dx) - a
            m = np.exp(-((rad - r) / max(0.8, r * 0.22)) ** 2) * (np.cos(np.clip(th, -1.1, 1.1)) ** 2) * (np.abs(th) < 1.1)
        else:  # petal fan
            th = np.arctan2(dy, dx) - a
            rad = np.hypot(dy, dx)
            m = np.clip(1.0 - rad / (r + 1e-6), 0, 1) * np.clip(np.cos(th * 2.2), 0, 1)
        np.maximum(acc[y0:y1, x0:x1], m.astype(np.float32) * v, out=acc[y0:y1, x0:x1])
    return np.clip(acc, 0, 1)


def micro_voronoi(h, w, seed, cells):
    """KD-tree micro cell mosaic -> (labels int32, d1, edge[0,1])."""
    from scipy.spatial import cKDTree
    rng = _rng(seed, 0xB2)
    pts = np.stack([rng.uniform(0, h, cells), rng.uniform(0, w, cells)], 1).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dd, idx = cKDTree(pts).query(np.stack([yy.ravel(), xx.ravel()], 1), k=2, workers=-1)
    d1 = dd[:, 0].reshape(h, w).astype(np.float32)
    edge = np.clip(1.0 - (dd[:, 1] - dd[:, 0]).reshape(h, w) / (0.35 * np.sqrt(h * w / cells)), 0, 1).astype(np.float32)
    return idx[:, 0].reshape(h, w).astype(np.int32), d1, edge


def filament_web(h, w, seed, nodes, k=2, width=1, intensity=(0.4, 1.0)):
    """Fine connecting filaments between scattered nodes -> field [0,1]."""
    from scipy.spatial import cKDTree
    rng = _rng(seed, 0xC3)
    pts = np.stack([rng.uniform(0, w, nodes), rng.uniform(0, h, nodes)], 1).astype(np.float32)
    _, nb = cKDTree(pts).query(pts, k=k + 1, workers=-1)
    img = np.zeros((h, w), np.float32)
    for i in range(nodes):
        for j in nb[i, 1:]:
            cv2.line(img, (int(pts[i, 0]), int(pts[i, 1])), (int(pts[j, 0]), int(pts[j, 1])),
                     float(rng.uniform(*intensity)), width, cv2.LINE_AA)
    return np.clip(img, 0, 1)


def flow_grain(h, w, seed, axes=3, freq_px=5.0, warp=0.5):
    """Multi-angle fine anisotropic grain -> field [0,1]. freq_px = stripe pitch."""
    rng = _rng(seed, 0xD4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    jit = noise01(h, w, seed ^ 0xD5, (9, 23)) - 0.5
    out = np.zeros((h, w), np.float32)
    for k in range(int(axes)):
        a = rng.uniform(0, np.pi)
        u = xx * np.cos(a) + yy * np.sin(a)
        out += np.abs(np.sin(u * (2 * np.pi / freq_px) + jit * warp * 6.0)) * rng.uniform(0.5, 1.0)
    return (out / max(out.max(), 1e-6)).astype(np.float32)


def ring_swarm(h, w, seed, count, r_px, pitch_px=3.0):
    """Micro concentric ring clusters at many centers -> field [0,1]."""
    rng = _rng(seed, 0xE5)
    acc = np.zeros((h, w), np.float32)
    for _ in range(int(count)):
        cy, cx = rng.uniform(0, h), rng.uniform(0, w)
        R = rng.uniform(0.5, 1.0) * r_px
        y0, y1 = max(0, int(cy - R * 1.4)), min(h, int(cy + R * 1.4) + 1)
        x0, x1 = max(0, int(cx - R * 1.4)), min(w, int(cx + R * 1.4) + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        rad = np.hypot(yy - cy, xx - cx)
        m = np.clip(np.cos(rad * (2 * np.pi / pitch_px)), 0, 1) * np.exp(-rad / (R + 1e-6)) * rng.uniform(0.6, 1.0)
        np.maximum(acc[y0:y1, x0:x1], m.astype(np.float32), out=acc[y0:y1, x0:x1])
    return np.clip(acc, 0, 1)


def halftone(h, w, seed, pitch_px=6.0, angles=3):
    """Rotated micro dot-screens -> field [0,1]."""
    rng = _rng(seed, 0xF6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    out = np.zeros((h, w), np.float32)
    f = 2 * np.pi / pitch_px
    for _ in range(int(angles)):
        a = rng.uniform(0, np.pi)
        u = xx * np.cos(a) + yy * np.sin(a)
        v = -xx * np.sin(a) + yy * np.cos(a)
        out = np.maximum(out, np.clip(np.sin(u * f) * np.sin(v * f), 0, 1) ** 1.5)
    return out.astype(np.float32)


def ramp_lut(stops, flatten=0.5, n=1025):
    return oklch_ramp(stops, np.linspace(0, 1, n).astype(np.float32), flatten_lightness=flatten)


def ramp_apply(field, lut):
    idx = np.clip(field * (len(lut) - 1), 0, len(lut) - 1).astype(np.int32)
    return lut[idx]


def per_label_lut(labels, seed, lut):
    """Each voronoi cell gets its own ramp sample -> HxWx3."""
    rng = _rng(seed, 0x77)
    t = rng.random(int(labels.max()) + 1).astype(np.float32)
    return ramp_apply(t[labels], lut)
