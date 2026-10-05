"""Flower Power Enamel Garden I1 — candidate 1960s psychedelic lacquer.

SPB-105 / owner doctrine / 2026-08-30.  A proper Flower Power finish must be
an authored garden, not a dark dot field or one repeated flower stamp.  This
one builds connected garlands from fine 8–28px native petals, centers, stems,
leaves, pearl outlines and small paint-causal shadows.  The several flower
families are distributed along unique curling vines across the full canvas;
there is no macro logo, random confetti, generic grain, or detached spec map.
"""
from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_PETALS = ((0.96, .10, .39), (1.00, .47, .06), (.98, .78, .05),
           (.12, .73, .61), (.16, .38, .88), (.55, .16, .74))


def _draw_garden(h, w, seed):
    """Return float colour plus masks at half native scale (then upscale)."""
    rng = np.random.default_rng((int(seed) ^ 0xF10A) & 0xFFFFFFFF)
    flower = np.zeros((h, w), np.uint8); center = flower.copy(); leaf = flower.copy()
    vine = flower.copy(); outline = flower.copy(); petal_code = np.zeros((h, w), np.uint8)
    # Deep plum enamel carries deliberate slow colour variation, never noise.
    y, x = np.mgrid[:h, :w].astype(np.float32)
    base = np.empty((h, w, 3), np.float32)
    shift = .5 + .5 * np.sin(x / 97.0 + .42 * np.sin(y / 71.0) + seed * .03)
    base[..., 0] = .032 + .042 * shift
    base[..., 1] = .012 + .014 * shift
    base[..., 2] = .060 + .073 * shift

    # I2 density correction: I1's garden looked sparse at picker scale.
    # Increase only the number of connected garlands/bouquets—not petal size
    # and not free-floating particles—so the full car receives authored flora.
    count = 38
    for vine_i in range(count):
        # Each vine has a different low-frequency path and bouquet cadence.
        x0, y0 = rng.uniform(0, w), rng.uniform(0, h)
        amp_x, amp_y = rng.uniform(w * .10, w * .29), rng.uniform(h * .08, h * .25)
        phase = rng.uniform(0, np.pi * 2); spin = rng.uniform(.72, 1.38)
        pts = []
        for j in range(80):
            t = j / 79.0 * np.pi * 2 * spin
            px = int(np.clip(x0 + amp_x * np.sin(t + phase) + amp_x * .34 * np.sin(2.37 * t - phase), 0, w - 1))
            py = int(np.clip(y0 + amp_y * np.cos(1.13 * t - phase) + amp_y * .30 * np.sin(2.13 * t + phase), 0, h - 1))
            pts.append((px, py))
        cv2.polylines(vine, [np.array(pts, np.int32)], False, 185, 1, cv2.LINE_AA)
        # A garland only places flowers on the authored path, plus linked
        # leaves alongside it; placement cannot read as detached fleck noise.
        for j in range(2 + (vine_i % 3), 78, 3 + (vine_i % 2)):
            px, py = pts[j]
            radius = int(rng.integers(4, 12))  # 8–24px at native 2048²
            family = int((vine_i * 2 + j // 5 + rng.integers(0, 3)) % len(_PETALS))
            # Five/six deliberate petal ellipses plus a center and pearl rim.
            petal_n = 5 + (family % 2)
            angle0 = rng.uniform(0, np.pi)
            for k in range(petal_n):
                ang = angle0 + k * 2 * np.pi / petal_n
                cx = int(px + np.cos(ang) * radius * .62); cy = int(py + np.sin(ang) * radius * .62)
                axes = (max(2, int(radius * .62)), max(2, int(radius * .37)))
                cv2.ellipse(flower, (cx, cy), axes, np.degrees(ang), 0, 360, 255, -1, cv2.LINE_AA)
                cv2.ellipse(petal_code, (cx, cy), axes, np.degrees(ang), 0, 360, family + 1, -1, cv2.LINE_AA)
                cv2.ellipse(outline, (cx, cy), axes, np.degrees(ang), 0, 360, 150, 1, cv2.LINE_AA)
            cv2.circle(center, (px, py), max(2, int(radius * .35)), 255, -1, cv2.LINE_AA)
            cv2.circle(outline, (px, py), max(2, int(radius * .43)), 210, 1, cv2.LINE_AA)
            # Two small attached leaves and a short stem fork.
            if j + 2 < len(pts):
                qx, qy = pts[j + 2]
                cv2.line(vine, (px, py), (qx, qy), 205, 1, cv2.LINE_AA)
                for sign in (-1, 1):
                    lx = int(px + sign * radius * .9); ly = int(py + radius * .42)
                    cv2.ellipse(leaf, (lx, ly), (max(2, radius // 2), max(1, radius // 4)), sign * 38, 0, 360, 255, -1, cv2.LINE_AA)

    flowerf, centerf, leaff = flower.astype(np.float32) / 255., center.astype(np.float32) / 255., leaf.astype(np.float32) / 255.
    vinef, rim = vine.astype(np.float32) / 255., outline.astype(np.float32) / 255.
    col = base.copy()
    for i, rgb in enumerate(_PETALS, 1):
        m = (petal_code == i).astype(np.float32)
        col += np.array(rgb, np.float32) * (m * .69)[..., None]
    col += np.array((.97, .61, .07), np.float32) * (centerf * .62)[..., None]
    col += np.array((.07, .48, .21), np.float32) * (leaff * .56)[..., None]
    col += np.array((.10, .42, .18), np.float32) * (vinef * .41)[..., None]
    col += np.array((.38, .22, .52), np.float32) * (rim * .23)[..., None]
    # Label M/R/Cc by physical enamel component, preserving all local contrast.
    hue_code = petal_code.astype(np.float32) / len(_PETALS)
    M = 17 + 117 * flowerf + 82 * centerf + 52 * rim + 36 * leaff + 23 * hue_code
    R = 220 - 83 * flowerf - 112 * centerf - 91 * rim + 35 * vinef + 20 * (1 - hue_code)
    C = 18 + 111 * flowerf + 92 * centerf + 104 * rim + 30 * leaff + 18 * hue_code
    spec = np.stack((np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(C, 16, 255)), axis=2).astype(np.uint8)
    return np.clip(col, 0, 1).astype(np.float32), spec


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        prior = _CACHE.get(key)
        if prior is not None:
            _CACHE.move_to_end(key); return prior
    scale = min(1.0, 1024.0 / max(h, w)); wh, ww = max(8, int(round(h * scale))), max(8, int(round(w * scale)))
    paint, spec = _draw_garden(wh, ww, seed)
    if (wh, ww) != (h, w):
        paint = cv2.resize(paint, (w, h), interpolation=cv2.INTER_CUBIC)
        spec = cv2.resize(spec, (w, h), interpolation=cv2.INTER_NEAREST)
    result = (paint.astype(np.float32), spec.astype(np.uint8))
    with _LOCK:
        _CACHE[key] = result
        while len(_CACHE) > 2: _CACHE.popitem(last=False)
    return result


def paint_flower_power_enamel(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5: source = source / 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(source * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_flower_power_enamel(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed)
    return spec[..., 0], spec[..., 1], spec[..., 2]
