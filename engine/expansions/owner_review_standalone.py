"""Source-owned Standalone Effects rebuilds for SPB-67.

Shared helpers here are math primitives only. Each finish keeps a distinct
layout, material recipe, and spec response so Standalone Effects does not rely
on the old generic post-wrapper.
"""

from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np


STANDALONE_EFFECT_IDS = (
    "thermal_titanium",
    "galaxy_nebula_base",
    "dark_sigil",
    "deep_space_void",
    "polished_obsidian_mono",
    "patinated_bronze",
    "reactive_plasma",
    "molten_metal",
    "oil_slick_base",
    "aurora_borealis_mono",
)


def _shape2(shape):
    return tuple(shape[:2] if len(shape) > 2 else shape)


def _mask(mask, shape):
    if mask is None:
        return np.ones(shape, dtype=np.float32)
    return np.asarray(mask, dtype=np.float32)


def _work_shape(shape, limit=1024):
    h, w = shape
    scale = min(1.0, float(limit) / float(max(h, w)))
    if scale >= 1.0:
        return shape
    return max(96, int(round(h * scale))), max(96, int(round(w * scale)))


def _xy(shape):
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _seed(seed, salt):
    return float((int(seed) * 1103515245 + int(salt) * 12345) & 0x7FFFFFFF) / 0x7FFFFFFF


def _norm(a):
    arr = np.asarray(a, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _hash(shape, seed, salt=0):
    x, y = _xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + _seed(seed, salt) * 91.7) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _soft(a, passes=1):
    out = np.asarray(a, dtype=np.float32)
    for _ in range(int(passes)):
        out = (
            out
            + np.roll(out, 1, 0)
            + np.roll(out, -1, 0)
            + np.roll(out, 1, 1)
            + np.roll(out, -1, 1)
        ) * 0.2
    return out.astype(np.float32)


def _line(v, period, width, phase=0.0):
    p = np.mod(v + float(phase), float(period))
    d = np.minimum(p, float(period) - p)
    return np.clip(1.0 - d / max(float(width), 1e-4), 0, 1).astype(np.float32)


def _dots(x, y, period_x, period_y, radius, phase_x=0.0, phase_y=0.0):
    px = np.mod(x + float(phase_x), float(period_x)) - float(period_x) * 0.5
    py = np.mod(y + float(phase_y), float(period_y)) - float(period_y) * 0.5
    rr = float(radius) * float(radius)
    return np.clip(1.0 - (px * px + py * py) / max(rr, 1e-4), 0, 1).astype(np.float32)


def _resize(a, shape):
    arr = np.asarray(a, dtype=np.float32)
    if arr.shape == shape:
        return arr
    return cv2.resize(arr, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR).astype(np.float32)


def _hsv_to_rgb(h, s, v):
    h = np.asarray(h, dtype=np.float32) % 1.0
    s = np.clip(s, 0, 1).astype(np.float32)
    v = np.clip(v, 0, 1).astype(np.float32)
    i = np.floor(h * 6.0).astype(np.int32)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    imod = i % 6
    r = np.select([imod == 0, imod == 1, imod == 2, imod == 3, imod == 4], [v, q, p, p, t], default=v)
    g = np.select([imod == 0, imod == 1, imod == 2, imod == 3, imod == 4], [t, v, v, q, p], default=p)
    b = np.select([imod == 0, imod == 1, imod == 2, imod == 3, imod == 4], [p, p, t, v, v], default=q)
    return np.stack([r, g, b], axis=2).astype(np.float32)


def _ramp(t, stops):
    t = np.clip(t, 0, 1).astype(np.float32)
    colors = np.asarray(stops, dtype=np.float32)
    pos = t * (len(colors) - 1)
    idx = np.clip(pos.astype(np.int32), 0, len(colors) - 2)
    frac = (pos - idx)[:, :, None]
    return colors[idx] * (1.0 - frac) + colors[idx + 1] * frac


@lru_cache(maxsize=20)
def _fields(finish_id, shape, seed):
    h, w = _work_shape(shape)
    x, y = _xy((h, w))
    px = x * float(w)
    py = y * float(h)
    salt = sum(ord(c) for c in finish_id)
    phase = _seed(seed, salt) * 997.0
    n1 = _soft(_hash((h, w), seed, salt), 2)
    n2 = _soft(_hash((h, w), seed, salt + 71), 1)
    fine = _norm(
        np.sin((x * (53.0 + salt % 13) + y * 31.0) * np.pi + phase * 0.013) * 0.45
        + np.sin((x * 137.0 - y * (101.0 + salt % 17)) * np.pi + phase * 0.017) * 0.35
        + (n1 - 0.5) * 0.42
    )
    sparkle = (_hash((h, w), seed, salt + 913) > 0.985).astype(np.float32)
    cx = x - (0.50 + (_seed(seed, salt + 9) - 0.5) * 0.08)
    cy = y - (0.50 + (_seed(seed, salt + 10) - 0.5) * 0.08)
    r = np.sqrt(cx * cx + cy * cy)
    a = np.arctan2(cy, cx)

    if finish_id == "oil_slick_base":
        film = _norm(n1 * 0.62 + np.sin((x * 9.0 + y * 5.0 + n2 * 2.5) * np.pi) * 0.28)
        rings = _line(r * max(h, w) + np.sin(a * 5.0) * 8.0, 56.0, 3.2, phase)
        motif = np.clip(film * 0.72 + rings * 0.35 + sparkle * 0.22, 0, 1)
        aux = rings
    elif finish_id == "thermal_titanium":
        bands = _norm(np.sin((x * 4.0 + y * 2.7 + n1 * 1.7) * np.pi + phase * 0.009))
        score = np.maximum(_line(px + py * 0.23, 78.0, 1.2, phase), _line(px - py * 0.37, 111.0, 0.9, phase * 0.4))
        motif = np.clip(bands * 0.70 + score * 0.42 + fine * 0.12, 0, 1)
        aux = score
    elif finish_id == "galaxy_nebula_base":
        cloud = _norm(n1 * 0.55 + n2 * 0.38 + np.sin((x * 3.2 - y * 2.4) * np.pi + phase * 0.005) * 0.22)
        stars = (_hash((h, w), seed, salt + 303) > 0.992).astype(np.float32)
        trails = np.maximum(_line(px + py * 0.18, 147.0, 1.0, phase), _line(px - py * 0.29, 213.0, 0.9, phase * 0.7))
        motif = np.clip(cloud * 0.62 + _soft(stars, 1) * 0.75 + trails * 0.22, 0, 1)
        aux = np.clip(stars + trails * 0.6, 0, 1)
    elif finish_id == "dark_sigil":
        rings = _line(r * max(h, w) + a * 12.0, 42.0, 2.2, phase)
        runes = ((np.sin(a * 19.0 + r * 95.0 + phase * 0.018) > 0.72) & (r > 0.10) & (r < 0.48)).astype(np.float32)
        motif = np.clip(rings * 0.55 + runes * 0.72 + fine * 0.14, 0, 1)
        aux = np.clip(runes + rings * 0.4, 0, 1)
    elif finish_id == "deep_space_void":
        orbit = _line(r * max(h, w) + np.sin(a * 3.0) * 10.0, 73.0, 2.1, phase)
        star = (_hash((h, w), seed, salt + 404) > 0.991).astype(np.float32)
        lens = np.exp(-((r - 0.28) / 0.12) ** 2).astype(np.float32)
        motif = np.clip(lens * 0.45 + orbit * 0.55 + star * 0.75 + fine * 0.08, 0, 1)
        aux = np.clip(orbit + star, 0, 1)
    elif finish_id == "polished_obsidian_mono":
        fracture = np.maximum(_line(px + py * 0.54 + n1 * 24.0, 116.0, 1.15, phase), _line(px - py * 0.61 + n2 * 19.0, 181.0, 0.95, phase * 0.31))
        glass = np.exp(-((r - 0.22) / 0.19) ** 2).astype(np.float32)
        motif = np.clip(glass * 0.30 + fracture * 0.86 + fine * 0.30 + sparkle * 0.18, 0, 1)
        aux = fracture
    elif finish_id == "patinated_bronze":
        pits = (_hash((h, w), seed, salt + 515) > 0.955).astype(np.float32) * _soft(n1, 1)
        veins = np.maximum(_line(px + py * 0.31, 91.0, 1.25, phase), _line(px - py * 0.42, 139.0, 1.0, phase * 0.5))
        patina = np.clip((n2 > 0.54).astype(np.float32) * 0.6 + pits * 0.8 + veins * 0.32, 0, 1)
        motif = np.clip(n1 * 0.28 + patina * 0.82 + fine * 0.28 + sparkle * 0.18, 0, 1)
        aux = patina
    elif finish_id == "reactive_plasma":
        arcs = np.maximum(_line(py + np.sin(x * 17.0 + phase * 0.01) * 26.0, 67.0, 2.0, phase), _line(px - py * 0.72 + n1 * 36.0, 101.0, 1.6, phase * 0.3))
        nodes = _dots(px, py, 128.0, 96.0, 5.2, phase, phase * 0.41)
        motif = np.clip(arcs * 0.75 + nodes * 0.55 + sparkle * 0.26 + fine * 0.10, 0, 1)
        aux = np.clip(arcs + nodes, 0, 1)
    elif finish_id == "molten_metal":
        rivers = _norm(np.sin((x * 5.5 + n1 * 2.2) * np.pi + phase * 0.006) + np.sin((y * 7.0 - n2 * 1.8) * np.pi) * 0.55)
        crust = np.maximum(_line(px + py * 0.21, 88.0, 1.7, phase), _line(px - py * 0.47, 132.0, 1.4, phase * 0.2))
        motif = np.clip(rivers * 0.74 + crust * 0.46 + sparkle * 0.22, 0, 1)
        aux = np.clip(crust + (rivers > 0.72).astype(np.float32) * 0.55, 0, 1)
    else:
        curtains = _norm(np.sin((x * 6.0 + np.sin(y * 8.0 + phase * 0.004) * 0.8 + n1 * 1.8) * np.pi))
        veil = np.maximum(_line(px + np.sin(y * 11.0) * 22.0, 124.0, 2.6, phase), _line(px - py * 0.12, 177.0, 1.4, phase * 0.6))
        stars = (_hash((h, w), seed, salt + 818) > 0.993).astype(np.float32)
        motif = np.clip(curtains * 0.62 + veil * 0.42 + stars * 0.55 + fine * 0.10, 0, 1)
        aux = np.clip(veil + stars, 0, 1)

    fields = tuple(_resize(arr, shape) for arr in (motif, aux, fine, sparkle, n1))
    return fields


def _spec_channels(finish_id, shape, seed, sm):
    motif, aux, fine, sparkle, noise = _fields(finish_id, shape, int(seed))
    if finish_id == "oil_slick_base":
        m = 150.0 + motif * 82.0 + sparkle * 50.0
        r = 20.0 + fine * 56.0 + aux * 22.0 - sparkle * 16.0
        cc = 16.0 + motif * 160.0 + aux * 42.0
    elif finish_id == "thermal_titanium":
        m = 174.0 + aux * 70.0 + sparkle * 36.0 - motif * 24.0
        r = 24.0 + motif * 92.0 + fine * 24.0
        cc = 18.0 + motif * 122.0 + sparkle * 36.0
    elif finish_id == "galaxy_nebula_base":
        m = 42.0 + motif * 110.0 + aux * 116.0 + sparkle * 55.0
        r = 82.0 - aux * 62.0 - motif * 24.0 + fine * 38.0
        cc = 22.0 + motif * 118.0 + aux * 62.0
    elif finish_id == "dark_sigil":
        m = 24.0 + aux * 190.0 + sparkle * 45.0
        r = 158.0 - aux * 116.0 + fine * 34.0
        cc = 18.0 + motif * 152.0 + aux * 44.0
    elif finish_id == "deep_space_void":
        m = 10.0 + motif * 100.0 + aux * 120.0
        r = 120.0 - motif * 82.0 + fine * 42.0
        cc = 20.0 + motif * 164.0 + aux * 44.0
    elif finish_id == "polished_obsidian_mono":
        m = 14.0 + aux * 112.0 + sparkle * 32.0
        r = 18.0 + fine * 44.0 + aux * 26.0
        cc = 16.0 + motif * 205.0 + sparkle * 24.0
    elif finish_id == "patinated_bronze":
        m = 178.0 + noise * 58.0 - aux * 86.0 + sparkle * 32.0
        r = 58.0 + aux * 128.0 + fine * 32.0
        cc = 24.0 + noise * 80.0 + (1.0 - aux) * 38.0
    elif finish_id == "reactive_plasma":
        m = 18.0 + aux * 225.0 + sparkle * 70.0
        r = 142.0 - aux * 112.0 + fine * 25.0
        cc = 16.0 + motif * 210.0 + sparkle * 26.0
    elif finish_id == "molten_metal":
        m = 106.0 + motif * 132.0 + aux * 44.0
        r = 82.0 + aux * 74.0 - motif * 48.0 + fine * 26.0
        cc = 18.0 + motif * 178.0 + sparkle * 28.0
    else:
        m = 34.0 + motif * 118.0 + aux * 62.0
        r = 88.0 - motif * 48.0 + fine * 58.0
        cc = 20.0 + motif * 178.0 + aux * 28.0
    return [np.clip(ch * float(sm), 0, 255).astype(np.float32) for ch in (m, r, cc)]


def _paint_rgb(finish_id, shape, seed):
    motif, aux, fine, sparkle, noise = _fields(finish_id, shape, int(seed))
    if finish_id == "oil_slick_base":
        rgb = _hsv_to_rgb((motif * 0.85 + noise * 0.18) % 1.0, 0.86 + aux * 0.12, 0.40 + motif * 0.42 + sparkle * 0.16)
        base = np.dstack([noise * 0.03, noise * 0.025, noise * 0.04])
        return np.clip(base * 0.45 + rgb * 0.92, 0, 1), 0.88
    if finish_id == "thermal_titanium":
        ramp = _ramp(motif, ([0.74, 0.76, 0.73], [0.84, 0.62, 0.24], [0.82, 0.34, 0.16], [0.45, 0.16, 0.62], [0.11, 0.22, 0.68], [0.30, 0.35, 0.42]))
        return np.clip(ramp + aux[:, :, None] * [0.08, 0.04, 0.10] + sparkle[:, :, None] * 0.12, 0, 1), 0.86
    if finish_id == "galaxy_nebula_base":
        neb = _hsv_to_rgb(0.57 + motif * 0.42, 0.70 + noise * 0.24, 0.16 + motif * 0.42)
        star = np.dstack([aux * 0.78, aux * 0.82, aux])
        return np.clip(neb * 0.85 + star * 0.42 + sparkle[:, :, None] * 0.15, 0, 1), 0.84
    if finish_id == "dark_sigil":
        base = np.dstack([0.024 + fine * 0.020, 0.014 + fine * 0.010, 0.040 + fine * 0.024])
        glow = np.dstack([0.52 + motif * 0.25, 0.02 + aux * 0.08, 0.78 + motif * 0.20])
        return np.clip(base * (1.0 - motif[:, :, None]) + glow * motif[:, :, None] + sparkle[:, :, None] * 0.10, 0, 1), 0.80
    if finish_id == "deep_space_void":
        base = np.dstack([0.006 + fine * 0.012, 0.008 + fine * 0.018, 0.024 + noise * 0.055])
        halo = np.dstack([motif * 0.09, motif * 0.18, motif * 0.42])
        return np.clip(base + halo + aux[:, :, None] * [0.10, 0.11, 0.22], 0, 1), 0.90
    if finish_id == "polished_obsidian_mono":
        micro = np.dstack([fine * 0.045, fine * 0.060, fine * 0.095])
        base = np.dstack([0.010 + noise * 0.026, 0.012 + noise * 0.030, 0.018 + noise * 0.042])
        fracture = np.dstack([aux * 0.30, aux * 0.38, aux * 0.52])
        glint = np.dstack([sparkle * 0.20, sparkle * 0.24, sparkle * 0.32])
        return np.clip(base + micro + fracture * 0.70 + glint + motif[:, :, None] * 0.045, 0, 1), 0.90
    if finish_id == "patinated_bronze":
        micro = np.dstack([fine * 0.11, fine * 0.075, fine * 0.035])
        bronze = np.dstack([0.45 + noise * 0.24, 0.24 + noise * 0.14, 0.075 + noise * 0.075])
        patina = np.dstack([0.018 + aux * 0.055, 0.32 + aux * 0.30, 0.23 + aux * 0.26])
        verdigris_dust = np.dstack([sparkle * 0.02, sparkle * 0.20, sparkle * 0.17])
        return np.clip(
            bronze * (1.0 - aux[:, :, None] * 0.58)
            + patina * (aux[:, :, None] * 0.74)
            + micro
            + verdigris_dust,
            0,
            1,
        ), 0.86
    if finish_id == "reactive_plasma":
        field = _hsv_to_rgb(0.60 + motif * 0.22, 0.86, 0.12 + motif * 0.74)
        arcs = np.dstack([aux * 0.80, aux * 0.16, aux * 0.96])
        return np.clip(field + arcs * 0.42 + sparkle[:, :, None] * [0.12, 0.16, 0.24], 0, 1), 0.86
    if finish_id == "molten_metal":
        crust = np.dstack([0.035 + noise * 0.05, 0.024 + noise * 0.03, 0.018 + noise * 0.02])
        hot = _ramp(motif, ([0.20, 0.03, 0.01], [0.64, 0.14, 0.03], [0.95, 0.38, 0.06], [1.00, 0.78, 0.22]))
        return np.clip(crust * (1.0 - motif[:, :, None] * 0.65) + hot * 0.88 + aux[:, :, None] * [0.10, 0.03, 0.01], 0, 1), 0.86
    curtains = _hsv_to_rgb(0.34 + motif * 0.48, 0.72 + noise * 0.18, 0.16 + motif * 0.62)
    veil = np.dstack([aux * 0.15, aux * 0.38, aux * 0.55])
    return np.clip(curtains + veil * 0.35 + sparkle[:, :, None] * 0.12, 0, 1), 0.82


def _make_standalone(finish_id):
    def _spec(shape, mask=None, seed=0, sm=1.0, *args, **kwargs):
        shape2 = _shape2(shape)
        msk = _mask(mask, shape2)
        m, r, cc = _spec_channels(finish_id, shape2, int(seed), float(sm))
        spec = np.zeros((shape2[0], shape2[1], 4), dtype=np.uint8)
        spec[:, :, 0] = np.clip(m * msk + 4.0 * (1.0 - msk), 0, 255).astype(np.uint8)
        spec[:, :, 1] = np.clip(r * msk + 115.0 * (1.0 - msk), 15, 255).astype(np.uint8)
        spec[:, :, 2] = np.clip(cc * msk + 80.0 * (1.0 - msk), 16, 255).astype(np.uint8)
        spec[:, :, 3] = np.clip(msk * 255.0, 0, 255).astype(np.uint8)
        return spec

    def _paint(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        shape2 = _shape2(shape)
        msk = _mask(mask, shape2)
        rgb, blend_gain = _paint_rgb(finish_id, shape2, int(seed))
        blend = np.clip(float(pm) * blend_gain, 0, 1) * msk
        out = paint[:, :, :3] * (1.0 - blend[:, :, None]) + rgb * blend[:, :, None]
        return np.ascontiguousarray(np.clip(out, 0, 1).astype(np.float32))

    _spec._spb_standalone_source_owned = True
    _paint._spb_standalone_source_owned = True
    return _spec, _paint


OWNER_REVIEW_STANDALONE_MONOLITHICS = {
    finish_id: _make_standalone(finish_id) for finish_id in STANDALONE_EFFECT_IDS
}
