"""Owner-review Exotic Metal base renderers for SPB-30.

The visible Exotic Metal group needs real material identities: oxide pores,
machined grain, crystalline facets, liquid flow, frost, clearcoat sparkle, and
angle-shift pigments. These are source renderers, not shared visual wrappers.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, sobel

from engine.core import multi_scale_noise


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _grid(shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy / max(h - 1, 1), xx / max(w - 1, 1)


def _norm(v):
    v = np.asarray(v, dtype=np.float32)
    lo = float(v.min())
    hi = float(v.max())
    if hi - lo < 1e-6:
        return np.zeros_like(v, dtype=np.float32)
    return ((v - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, seed, scales=(2, 5, 13, 31), weights=(0.28, 0.30, 0.25, 0.17)):
    return _norm(multi_scale_noise(shape, list(scales), list(weights), seed))


def _blend(paint, mask, pm, color, strength=0.94):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask, 0, 1)[:, :, None] * np.clip(pm * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - a) + np.clip(color, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _hsv(h, s, v):
    h, s, v = np.broadcast_arrays(h, s, v)
    h = np.mod(h, 1.0).astype(np.float32)
    s = np.clip(s, 0, 1).astype(np.float32)
    v = np.clip(v, 0, 1).astype(np.float32)
    i = np.floor(h * 6.0).astype(np.int32) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    rgb = np.empty(h.shape + (3,), dtype=np.float32)
    cases = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))
    for idx, vals in enumerate(cases):
        m = i == idx
        for c in range(3):
            rgb[..., c][m] = vals[c][m]
    return rgb


def _sparkle(shape, seed, density=0.018, blur=0.35):
    h, w = shape
    rng = np.random.default_rng((seed + 91) & 0xFFFFFFFF)
    n = min(int(h * w * density), 180000)
    out = np.zeros((h, w), dtype=np.float32)
    if n:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.2, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.28, np.roll(out, -1, 1) * 0.28])
    if blur:
        out = gaussian_filter(out, sigma=blur)
    return np.clip(out, 0, 1).astype(np.float32)


def _line_field(shape, seed, angle=0.0, freq=80.0, width=0.020, warp=0.025):
    y, x = _grid(shape)
    n = _noise(shape, seed + 12, (4, 11, 27), (0.30, 0.36, 0.34))
    coord = x * np.cos(angle) + y * np.sin(angle) + (n - 0.5) * warp
    d = np.abs(np.sin(coord * freq * np.pi))
    return np.clip((width - d) / max(width, 1e-5), 0, 1).astype(np.float32)


def _cell_edges(shape, seed, scales=(5, 13, 29), weights=(0.34, 0.36, 0.30)):
    field = _noise(shape, seed, scales, weights)
    edge = np.clip(np.sqrt(sobel(field, axis=0) ** 2 + sobel(field, axis=1) ** 2) * 1.6, 0, 1)
    return field.astype(np.float32), edge.astype(np.float32)


def _brushed(shape, seed, angle, tint):
    y, x = _grid(shape)
    grain = _line_field(shape, seed, angle, 130.0, 0.030, 0.012)
    hair = _line_field(shape, seed + 1, angle + 0.015, 310.0, 0.016, 0.006)
    cloudy = _noise(shape, seed + 2, (9, 23, 61), (0.28, 0.36, 0.36))
    polish = np.clip(0.44 + grain * 0.18 + hair * 0.08 + (cloudy - 0.5) * 0.12, 0, 1)
    color = np.stack([polish * tint[0], polish * tint[1], polish * tint[2]], axis=-1)
    streak = np.clip((0.018 - np.abs(np.sin((x * 17.0 + y * 3.0) * np.pi))) * 5.5, 0, 1)
    return np.clip(color + streak[:, :, None] * 0.08, 0, 1).astype(np.float32), grain, hair, cloudy


def _spec_from_fields(shape, seed, metallic=150, rough=34, cc=24, detail=None, smooth=False):
    base = _noise(shape, seed + 41, (2, 5, 13, 31), (0.30, 0.30, 0.24, 0.16))
    if detail is None:
        detail = base
    detail = np.clip(detail, 0, 1)
    M = np.clip(metallic + detail * 76 + base * 22, 0, 255)
    if smooth:
        R = np.clip(12 + (1 - detail) * rough + base * 6, 0, 255)
    else:
        R = np.clip(rough + (1 - detail) * 38 + base * 18, 15, 255)
    CC = np.clip(cc + detail * 26 + base * 10, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_anodized(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    pore = _line_field((h, w), seed, 0.0, 165.0, 0.020, 0.010) * _line_field((h, w), seed + 1, np.pi / 3, 150.0, 0.018, 0.010)
    oxide = _noise((h, w), seed + 2, (3, 8, 19, 47), (0.26, 0.30, 0.27, 0.17))
    color = _hsv(0.56 + x * 0.08 + y * 0.03 + oxide * 0.05, 0.38 + pore * 0.18, 0.30 + oxide * 0.14 + pore * 0.08)
    return _blend(paint, mask, pm, color, 0.93)


def spec_anodized(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    pore = _line_field((h, w), seed, 0.0, 165.0, 0.020, 0.010)
    return _spec_from_fields((h, w), seed, 104, 52, 24, pore, False)


def paint_brushed_aluminum(paint, shape, mask, seed, pm, bb):
    color, *_ = _brushed(_shape2(shape), seed, 0.02, (0.88, 0.90, 0.96))
    return _blend(paint, mask, pm, color, 0.94)


def spec_brushed_aluminum(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    grain = _line_field((h, w), seed, 0.02, 130.0, 0.030, 0.012)
    return _spec_from_fields((h, w), seed, 166, 24, 22, grain, True)


def paint_brushed_titanium(paint, shape, mask, seed, pm, bb):
    color, grain, hair, cloudy = _brushed(_shape2(shape), seed, -0.10, (0.76, 0.73, 0.68))
    heat = _hsv(0.08 + cloudy * 0.10, 0.18 + hair * 0.20, 0.20 + grain * 0.16)
    return _blend(paint, mask, pm, np.clip(color * 0.78 + heat * 0.34, 0, 1), 0.94)


def spec_brushed_titanium(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    grain = _line_field((h, w), seed, -0.10, 130.0, 0.030, 0.012)
    return _spec_from_fields((h, w), seed, 148, 30, 30, grain, True)


def paint_cobalt_metal(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    facet, edge = _cell_edges((h, w), seed + 10, (7, 17, 41), (0.34, 0.38, 0.28))
    glint = _sparkle((h, w), seed + 11, 0.010, 0.55)
    cobalt = 0.18 + facet * 0.18 + glint * 0.12
    color = np.stack([cobalt * 0.56, cobalt * 0.70, cobalt * 1.18], axis=-1)
    color = np.clip(color + edge[:, :, None] * [0.03, 0.05, 0.10], 0, 1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_cobalt_metal(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    facet, edge = _cell_edges((h, w), seed + 10, (7, 17, 41), (0.34, 0.38, 0.28))
    return _spec_from_fields((h, w), seed, 154, 35, 25, np.clip(facet * 0.7 + edge * 0.5, 0, 1), False)


def paint_diamond_coat(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    dust = _sparkle((h, w), seed, 0.055, 0.28)
    prism = _hsv(0.54 + x * 0.22 - y * 0.08 + dust * 0.18, 0.42 + dust * 0.36, 0.30 + dust * 0.52)
    star = np.maximum(_line_field((h, w), seed + 2, 0.78, 92.0, 0.010, 0.006), _line_field((h, w), seed + 3, -0.72, 88.0, 0.010, 0.006))
    color = np.clip(0.23 + prism * 0.50 + dust[:, :, None] * [0.22, 0.24, 0.30] + star[:, :, None] * 0.12, 0, 1)
    return _blend(paint, mask, pm, color, 0.92)


def spec_diamond_coat(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    dust = _sparkle((h, w), seed, 0.055, 0.28)
    return _spec_from_fields((h, w), seed, 72, 18, 46, dust, True)


def paint_frozen(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    frost = np.maximum(_line_field((h, w), seed, 0.50, 120.0, 0.012, 0.020), _line_field((h, w), seed + 1, -0.42, 145.0, 0.010, 0.018))
    haze = _noise((h, w), seed + 2, (3, 9, 27, 81), (0.24, 0.28, 0.30, 0.18))
    color = _hsv(0.55 + haze * 0.07 + x * 0.03, 0.20 + frost * 0.24, 0.30 + haze * 0.20 + frost * 0.16)
    return _blend(paint, mask, pm, color, 0.94)


def spec_frozen(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    frost = np.maximum(_line_field((h, w), seed, 0.50, 120.0, 0.012, 0.020), _line_field((h, w), seed + 1, -0.42, 145.0, 0.010, 0.018))
    return _spec_from_fields((h, w), seed, 118, 82, 22, frost, False)


def paint_liquid_titanium(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    flow = _noise((h, w), seed + 10, (5, 13, 31, 73), (0.22, 0.28, 0.30, 0.20))
    ribbons = _norm(np.sin((x * 15.0 + flow * 5.0) * np.pi) + np.sin((y * 9.0 - flow * 4.0) * np.pi) * 0.7)
    color = np.stack([0.30 + ribbons * 0.25, 0.33 + flow * 0.20, 0.39 + ribbons * 0.25], axis=-1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_liquid_titanium(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    flow = _noise((h, w), seed + 10, (5, 13, 31, 73), (0.22, 0.28, 0.30, 0.20))
    return _spec_from_fields((h, w), seed, 178, 12, 28, flow, True)


def paint_platinum(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    polish = _noise((h, w), seed + 2, (2, 7, 19, 53), (0.26, 0.30, 0.27, 0.17))
    glint = _sparkle((h, w), seed + 3, 0.016, 0.45)
    value = 0.56 + polish * 0.18 + glint * 0.16
    color = np.stack([value * 0.96, value * 0.98, value * 1.06], axis=-1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_platinum(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 2, (2, 7, 19, 53), (0.26, 0.30, 0.27, 0.17)) + _sparkle((h, w), seed + 3, 0.016, 0.45), 0, 1)
    return _spec_from_fields((h, w), seed, 188, 16, 36, detail, True)


def paint_raw_aluminum(paint, shape, mask, seed, pm, bb):
    color, grain, hair, cloudy = _brushed(_shape2(shape), seed, 0.03, (0.72, 0.73, 0.76))
    scuff = _line_field(_shape2(shape), seed + 7, -0.18, 46.0, 0.014, 0.022)
    return _blend(paint, mask, pm, np.clip(color * 0.74 + scuff[:, :, None] * 0.15 - cloudy[:, :, None] * 0.05, 0, 1), 0.94)


def spec_raw_aluminum(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    scuff = _line_field((h, w), seed + 7, -0.18, 46.0, 0.014, 0.022)
    return _spec_from_fields((h, w), seed, 154, 42, 18, scuff, False)


def paint_rose_gold(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    grain = _line_field((h, w), seed, 0.08, 86.0, 0.025, 0.012)
    satin = _noise((h, w), seed + 1, (4, 11, 29, 67), (0.25, 0.31, 0.28, 0.16))
    hue = 0.020 + satin * 0.025 + grain * 0.010
    color = _hsv(hue, 0.48 + grain * 0.18, 0.46 + satin * 0.22 + grain * 0.11)
    return _blend(paint, mask, pm, color, 0.94)


def spec_rose_gold(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    grain = _line_field((h, w), seed, 0.08, 86.0, 0.025, 0.012)
    return _spec_from_fields((h, w), seed, 170, 24, 32, grain, True)


def paint_titanium_raw(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    phase, edge = _cell_edges((h, w), seed + 20, (3, 8, 18, 42), (0.28, 0.30, 0.25, 0.17))
    needles = np.maximum(_line_field((h, w), seed + 21, 0.52, 112.0, 0.012, 0.018), _line_field((h, w), seed + 22, -0.35, 96.0, 0.010, 0.018))
    color = np.stack([0.38 + phase * 0.24 + needles * 0.10, 0.37 + phase * 0.17, 0.42 + edge * 0.18 + needles * 0.12], axis=-1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_titanium_raw(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    phase, edge = _cell_edges((h, w), seed + 20, (3, 8, 18, 42), (0.28, 0.30, 0.25, 0.17))
    return _spec_from_fields((h, w), seed, 142, 38, 34, np.clip(phase * 0.6 + edge * 0.8, 0, 1), False)


def paint_tungsten(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    dense = _noise((h, w), seed + 30, (1, 3, 8, 21), (0.38, 0.31, 0.20, 0.11))
    grit = _sparkle((h, w), seed + 31, 0.025, 0.45)
    value = 0.10 + dense * 0.13 + grit * 0.08
    color = np.stack([value * 0.88, value * 0.90, value * 0.96], axis=-1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_tungsten(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    dense = _noise((h, w), seed + 30, (1, 3, 8, 21), (0.38, 0.31, 0.20, 0.11))
    return _spec_from_fields((h, w), seed, 168, 48, 28, dense, False)


def paint_organic_metal(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    vein_a = _line_field((h, w), seed, 0.62, 36.0, 0.020, 0.055)
    vein_b = _line_field((h, w), seed + 1, -0.38, 49.0, 0.014, 0.050)
    cell = _noise((h, w), seed + 2, (6, 15, 37, 83), (0.24, 0.30, 0.28, 0.18))
    pulse = np.clip(vein_a * 0.7 + vein_b * 0.5 + cell * 0.4, 0, 1)
    color = _hsv(0.22 + cell * 0.12 + x * 0.04, 0.24 + pulse * 0.34, 0.18 + cell * 0.18 + pulse * 0.20)
    return _blend(paint, mask, pm, color, 0.93)


def spec_organic_metal(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    vein = np.maximum(_line_field((h, w), seed, 0.62, 36.0, 0.020, 0.055), _line_field((h, w), seed + 1, -0.38, 49.0, 0.014, 0.050))
    return _spec_from_fields((h, w), seed, 128, 32, 32, vein, False)


def paint_anodized_exotic(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    pore = np.maximum(_line_field((h, w), seed, np.pi / 6, 210.0, 0.018, 0.008), _line_field((h, w), seed + 1, -np.pi / 6, 205.0, 0.014, 0.008))
    wave = _noise((h, w), seed + 4, (5, 12, 31, 71), (0.24, 0.31, 0.28, 0.17))
    color = _hsv(0.58 + x * 0.28 + y * 0.06 + wave * 0.14, 0.56 + pore * 0.28, 0.20 + wave * 0.22 + pore * 0.18)
    return _blend(paint, mask, pm, color, 0.94)


def spec_anodized_exotic(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    pore = np.maximum(_line_field((h, w), seed, np.pi / 6, 210.0, 0.018, 0.008), _line_field((h, w), seed + 1, -np.pi / 6, 205.0, 0.014, 0.008))
    return _spec_from_fields((h, w), seed, 126, 44, 42, pore, False)


def paint_xirallic(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    facet, edge = _cell_edges((h, w), seed + 50, (2, 5, 11, 23), (0.35, 0.30, 0.22, 0.13))
    crystal = _sparkle((h, w), seed + 51, 0.075, 0.28)
    tint = _hsv(0.57 + facet * 0.14 + x * 0.04, 0.24 + crystal * 0.35, 0.34 + facet * 0.22 + crystal * 0.30)
    color = np.clip(tint + edge[:, :, None] * [0.10, 0.11, 0.16], 0, 1)
    return _blend(paint, mask, pm, color, 0.92)


def spec_xirallic(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    crystal = np.clip(_sparkle((h, w), seed + 51, 0.075, 0.28) + _noise((h, w), seed + 50, (2, 5, 11, 23), (0.35, 0.30, 0.22, 0.13)) * 0.45, 0, 1)
    return _spec_from_fields((h, w), seed, 126, 20, 28, crystal, True)


def paint_chromaflair(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    warp = _noise((h, w), seed + 60, (4, 9, 19, 43), (0.28, 0.30, 0.25, 0.17))
    foil = _norm(np.sin((x * 13.0 + warp * 3.5) * np.pi) + np.sin((y * 7.0 - warp * 4.2) * np.pi) * 0.8)
    flakes = _sparkle((h, w), seed + 61, 0.045, 0.42)
    hue = 0.78 + x * 0.55 - y * 0.22 + warp * 0.36 + foil * 0.18
    color = _hsv(hue, 0.66 + flakes * 0.26, 0.30 + foil * 0.34 + flakes * 0.28)
    return _blend(paint, mask, pm, color, 0.94)


def spec_chromaflair(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    foil = _noise((h, w), seed + 60, (4, 9, 19, 43), (0.28, 0.30, 0.25, 0.17))
    return _spec_from_fields((h, w), seed, 178, 16, 30, foil, True)


OWNER_REVIEW_EXOTIC_METAL_OVERRIDES = {
    "anodized": (paint_anodized, spec_anodized),
    "brushed_aluminum": (paint_brushed_aluminum, spec_brushed_aluminum),
    "brushed_titanium": (paint_brushed_titanium, spec_brushed_titanium),
    "cobalt_metal": (paint_cobalt_metal, spec_cobalt_metal),
    "diamond_coat": (paint_diamond_coat, spec_diamond_coat),
    "frozen": (paint_frozen, spec_frozen),
    "liquid_titanium": (paint_liquid_titanium, spec_liquid_titanium),
    "platinum": (paint_platinum, spec_platinum),
    "raw_aluminum": (paint_raw_aluminum, spec_raw_aluminum),
    "rose_gold": (paint_rose_gold, spec_rose_gold),
    "titanium_raw": (paint_titanium_raw, spec_titanium_raw),
    "tungsten": (paint_tungsten, spec_tungsten),
    "organic_metal": (paint_organic_metal, spec_organic_metal),
    "anodized_exotic": (paint_anodized_exotic, spec_anodized_exotic),
    "xirallic": (paint_xirallic, spec_xirallic),
    "chromaflair": (paint_chromaflair, spec_chromaflair),
}
