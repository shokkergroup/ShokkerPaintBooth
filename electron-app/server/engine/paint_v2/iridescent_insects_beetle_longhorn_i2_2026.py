"""Longhorn Filament I2 — per-scale Cerambycid photonic sacks.

SPB-105 / owner 2026-09-01, cross-card correction pass 1.  The I1 paint used
fine biological sacks, but its M/R/Cc channels were dominated by broad shared
sinusoidal fields and converged visually with Glasswing and other Insects.
I2 removes those macro fields completely.  Every 8-32px native sack now owns
its color family, tilt, metallic tier, roughness tier, clearcoat tier, cortex
lip, lamellar crossbands, axial core and pore nodes.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

GEN = 1024


def _hw(shape): return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape)
    a = np.asarray(a, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, col):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask * pm * .96, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(col, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    warp = 2.1 * np.sin(x / 89.0) + 1.1 * np.sin((x + y) / 151.0)
    row = np.floor((y + warp) / 6.8)
    pitch = 16.4
    staggered_x = x + .5 * row * pitch + 1.7 * np.sin(y / 57.0)
    raw_sx = np.mod(staggered_x, pitch) - pitch * .5
    raw_sy = np.mod(y + warp, 6.8) - 3.4
    sid = row * 1549.0 + np.floor(staggered_x / pitch)
    phase = float(int(seed) % 10007) * .00137

    # All identity fields are indexed by the biological sack, not by screen
    # coordinates.  This is the core anti-duplication correction.
    hue_state = n01(np.sin(sid * .731 + phase) + .57 * np.cos(sid * 1.913 - .8))
    order_state = n01(np.cos(sid * 1.117 + 1.6 + phase) + .49 * np.sin(sid * .283))
    coat_state = n01(np.sin(sid * 2.237 - .4) + .43 * np.cos(sid * .619 + phase))
    rough_state = n01(np.cos(sid * 1.571 + .3) + .51 * np.sin(sid * .947 - phase))
    tilt_state = n01(np.sin(sid * .419 + 2.4) + .37 * np.cos(sid * 2.791))

    angle = (tilt_state - .5) * .62
    ca, sa = np.cos(angle), np.sin(angle)
    sx = raw_sx * ca + raw_sy * sa
    sy = -raw_sx * sa + raw_sy * ca
    half_l = 5.8 + 1.75 * order_state
    half_w = 1.85 + .58 * coat_state
    rr = np.sqrt((sx / half_l) ** 2 + (sy / half_w) ** 2)
    sack = np.clip(1 - (rr - .73) / .24, 0, 1)
    lip = np.clip(1 - np.abs(rr - .80) / .105, 0, 1)
    core = np.clip(1 - np.abs(sy) / (.58 + .24 * rough_state), 0, 1) * sack
    crossband = np.clip((np.cos((sx + .22 * sy) * np.pi / 1.95) - .52) * 2.25, 0, 1) * sack
    node_x = np.mod(sx + 7.9, 3.7) - 1.85
    node = np.clip(1 - (node_x / .72) ** 2 - (sy / .68) ** 2, 0, 1) * sack
    return tuple(np.asarray(a, np.float32) for a in (
        sack, lip, core, crossband, node, hue_state, order_state,
        coat_state, rough_state, tilt_state,
    ))


def paint_beetle_longhorn_i2(paint, shape, mask, seed, pm, bb):
    sack, lip, core, crossband, node, hue, order, coat, rough, tilt = _surface(seed + 28921)
    black = np.array([.002, .003, .005], np.float32)
    turquoise = np.array([.010, .66, .62], np.float32)
    emerald = np.array([.06, .72, .18], np.float32)
    citron = np.array([.70, .88, .04], np.float32)
    gold = np.array([.98, .48, .018], np.float32)
    ember = np.array([.88, .075, .008], np.float32)
    indigo = np.array([.018, .030, .24], np.float32)

    # Six biological structural-color states distributed sack-by-sack.
    stops = np.stack([turquoise, emerald, citron, gold, ember, indigo], axis=0)
    pos = np.clip(hue * (len(stops) - 1), 0, len(stops) - 1.001)
    idx = np.floor(pos).astype(np.int32)
    frac = pos - idx
    scale_rgb = stops[idx] * (1 - frac[..., None]) + stops[idx + 1] * frac[..., None]
    scale_rgb *= (.48 + .42 * order)[..., None]

    col = black[None, None, :] + sack[..., None] * scale_rgb
    col += lip[..., None] * (scale_rgb * .46 + np.array([.17, .18, .08], np.float32))
    col += core[..., None] * np.array([.19, .26, .13], np.float32) * (.28 + .42 * coat[..., None])
    col += crossband[..., None] * np.array([.22, .23, .12], np.float32) * (.24 + .36 * rough[..., None])
    col += node[..., None] * np.array([.74, .84, .54], np.float32) * (.24 + .32 * tilt[..., None])
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_beetle_longhorn_i2(shape, seed, sm, base_m, base_r):
    sack, lip, core, crossband, node, hue, order, coat, rough, tilt = _surface(seed + 28921)

    # Quantized per-sack material tiers create adjacent chrome/flake/satin/glass
    # cells.  Fine substructures then modulate each tier independently.
    metal_tier = np.floor(np.clip(order, 0, .999) * 8.0) / 7.0
    rough_tier = np.floor(np.clip(rough, 0, .999) * 8.0) / 7.0
    coat_tier = np.floor(np.clip(coat, 0, .999) * 8.0) / 7.0
    # Keep the black interstice at a mid material state.  Each sack moves away
    # from that neutral point independently in RGB/spec space, avoiding the
    # bright-green common background and channel correlation of P1.
    m = 126 + sack * ((metal_tier - .5) * 224)
    m += lip * (20 + 34 * tilt) + crossband * (18 + 28 * coat_tier) - core * 22
    r = 118 + sack * ((rough_tier - .5) * 230)
    r += core * (22 + 46 * hue) + node * (18 + 26 * order) - lip * 31
    cc = 132 + sack * ((coat_tier - .5) * 226)
    cc += lip * (18 + 32 * order) + core * (16 + 38 * tilt) - node * 42
    cc -= crossband * (14 + 24 * rough_tier)
    return (
        _resize(np.clip(m * sm, 0, 250), shape),
        _resize(np.clip(r, 5, 248), shape),
        _resize(np.clip(cc, 0, 255), shape),
    )
