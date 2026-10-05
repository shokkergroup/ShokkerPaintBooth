"""Buprestid Furnace I2 — offset refractory cells with nested multilayers.

SPB-105 / Finish Identity Law / owner 2026-09-01: "spec maps look nearly
identical" and bases must not be recolors.  I1's paint and M/R/Cc were dominated
by shared low-frequency f0/f1/f2 waves.  I2 is a complete identity rewrite based
on Buprestid stacked chitin/melanin reflector plates, irregular air gaps,
thermally shifted local spectra and reflection broadening from surface
sculpting (Vigneron et al. 2006; Stavenga 2026).  Every 25-31px refractory cell
owns nested 8-12px lamellae, an oxide lip, soot vents and distinct material
states.  There is no category house field and no palette-only distinction.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

GEN = 768


def _hw(shape): return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape)
    a = np.asarray(a, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, col):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .96, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(col, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    px, py = 11.4, 9.4  # 30.4 x 25.1 native pixels at 2048².
    row = np.floor(y / py)
    stagger = np.mod(row, 2.0) * px * .5
    col = np.floor((x + stagger) / px)
    cx = (col + .5) * px - stagger
    cy = (row + .5) * py
    u, v = x - cx, y - cy
    fid = row * 1093.0 + col * 29.0 + (int(seed) % 1543)

    thermal = n01(np.sin(fid * 1.771 + .31) + .61 * np.cos(fid * .613 - 1.1))
    metal_state = np.mod(np.sin(fid * 19.117 + .73) * 31415.9265, 1.0)
    rough_state = np.mod(np.sin(fid * 37.391 - .27) * 27182.8183, 1.0)
    coat_state = np.mod(np.sin(fid * 61.733 + 1.41) * 16180.3399, 1.0)

    # Slightly tapering ingot cell: a distinct furnace brick rather than the
    # Voronoi bowls/plates used by other insect cards.
    half_w = 5.02 - .12 * v + .16 * (thermal - .5)
    q = np.maximum(np.abs(u) / half_w, np.abs(v) / 4.15)
    body = np.clip((1.03 - q) / .12, 0, 1)
    core = np.clip((.82 - q) / .14, 0, 1)
    lip = np.clip(1 - np.abs(q - .90) / .095, 0, 1)
    crown = np.clip((-.25 - v) / 2.9, 0, 1) * core
    floor = np.clip((v + .55) / 2.8, 0, 1) * core

    # Nested chevron multilayers: 9.3px native pitch, phase varies per cell and
    # layer, never through a global screen-space wave.
    nested = v + .31 * np.abs(u) + (thermal - .5) * .64
    phase = np.mod(nested + 24.0, 3.48)
    lamella = np.clip((.42 - np.abs(phase - .48)) / .42, 0, 1) * core
    air_gap = np.clip((.36 - np.abs(phase - 2.02)) / .36, 0, 1) * core
    layer_id = np.floor((nested + 24.0) / 3.48)
    layer_state = n01(np.sin(fid * .239 + layer_id * 1.713) + .53 * np.cos(fid * .091 - layer_id * .733))

    # Two 8-10px native soot/air pockets and a broken oxidation scar create
    # secondary anatomy without scatter or confetti.
    vent_l = np.clip(1 - np.sqrt(((u + 2.55) / 1.58) ** 2 + ((v - 1.55) / 1.28) ** 2), 0, 1)
    vent_r = np.clip(1 - np.sqrt(((u - 2.55) / 1.58) ** 2 + ((v - 1.55) / 1.28) ** 2), 0, 1)
    vents = np.maximum(vent_l, vent_r) * core
    scar_phase = np.cos(np.arctan2(v, u) * 5.0 + thermal * 5.3)
    oxide = lip * np.clip((scar_phase + .38) * 1.25, 0, 1)
    quench = floor * np.clip((np.cos(u * np.pi / 2.7 + layer_state * 2.1) - .42) * 1.8, 0, 1)
    seam = np.clip(1 - np.abs(q - 1.01) / .045, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        body, core, lip, crown, floor, lamella, air_gap, vents, oxide, quench,
        seam, thermal, layer_state, metal_state, rough_state, coat_state,
    ))


def paint_beetle_buprestid_i2(paint, shape, mask, seed, pm, bb):
    body, core, lip, crown, floor, lamella, air, vents, oxide, quench, seam, thermal, layer_state, metal_state, rough_state, coat_state = _surface(seed + 22469)
    melanin = np.array([.006, .004, .009], np.float32)
    emerald = np.array([.008, .49, .18], np.float32)
    cobalt = np.array([.012, .10, .66], np.float32)
    violet = np.array([.30, .014, .47], np.float32)
    copper = np.array([.77, .12, .012], np.float32)
    ember = np.array([1.00, .42, .018], np.float32)
    brass = np.array([.96, .70, .08], np.float32)

    cool = emerald[None, None, :] * (1 - layer_state[..., None]) + cobalt[None, None, :] * layer_state[..., None]
    hot = copper[None, None, :] * (1 - layer_state[..., None]) + ember[None, None, :] * layer_state[..., None]
    cell_col = cool * (1 - thermal[..., None]) + hot * thermal[..., None]
    violet_gate = np.clip((metal_state - .68) * 2.5, 0, .72)[..., None]
    cell_col = cell_col * (1 - violet_gate) + violet[None, None, :] * violet_gate

    col = melanin[None, None, :] * (.72 + .20 * rough_state[..., None])
    col += body[..., None] * cell_col * (.55 + .25 * coat_state[..., None])
    col += crown[..., None] * emerald[None, None, :] * (.15 + .22 * coat_state[..., None])
    col += lamella[..., None] * brass[None, None, :] * (.18 + .22 * layer_state[..., None])
    col += air[..., None] * cobalt[None, None, :] * (.10 + .18 * (1 - thermal[..., None]))
    col += oxide[..., None] * ember[None, None, :] * (.30 + .28 * metal_state[..., None])
    col += quench[..., None] * violet[None, None, :] * (.25 + .23 * rough_state[..., None])
    col *= 1 - vents[..., None] * (.72 + .18 * rough_state[..., None])
    col += lip[..., None] * brass[None, None, :] * (.14 + .18 * metal_state[..., None])
    col += seam[..., None] * np.array([.055, .018, .008], np.float32)
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_beetle_buprestid_i2(shape, seed, sm, base_m, base_r):
    body, core, lip, crown, floor, lamella, air, vents, oxide, quench, seam, thermal, layer_state, metal_state, rough_state, coat_state = _surface(seed + 22469)
    # Each channel owns named anatomy.  Per-cell and per-layer states provide a
    # broad material palette without any generic full-frame f0/f1/f2 carrier.
    # P2 ownership split: P1's high roughness baseline made the combined map a
    # lime checker and let all three channels over-own the same cell face.
    # Metallic = reflector stacks/oxide; roughness = voids/soot/quench;
    # clearcoat = smooth crowns/seams.  Refractory channels stay materially dark.
    m = 18 + body * (14 + 26 * metal_state) + lip * (82 + 54 * layer_state)
    m += lamella * (112 + 62 * thermal) + oxide * (64 + 46 * metal_state) - vents * 16
    r = 26 + body * (10 + 12 * rough_state) + floor * (24 + 30 * rough_state)
    r += air * (116 + 62 * rough_state)
    r += vents * (132 + 54 * thermal) + quench * (84 + 42 * layer_state) - crown * 12
    cc = 12 + body * (6 + 12 * coat_state) + crown * (148 + 68 * coat_state)
    cc += core * (22 + 38 * coat_state)
    cc += seam * (86 + 34 * layer_state) + air * (42 + 32 * (1 - thermal))
    cc -= vents * 18 + oxide * 20
    return (
        np.clip(_resize(np.clip(m * sm, 8, 238), shape), 8, 238),
        np.clip(_resize(np.clip(r, 12, 236), shape), 12, 236),
        np.clip(_resize(np.clip(cc, 6, 242), shape), 6, 242),
    )
