"""Owner-review Carbon & Composite base renderers for SPB-30.

These source renderers replace the flat/dim/repeating baseline composites with
material-specific weave, strand, lattice, and chopped-fiber behavior that still
holds up at full-car 2048 scale.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, sobel

from engine.core import _resize_array, multi_scale_noise, get_mgrid


_FIELD_CACHE: dict[tuple[str, tuple[int, int], int], tuple[np.ndarray, ...]] = {}
_NOISE_CACHE: dict[tuple[tuple[int, int], int, tuple[float, ...], tuple[float, ...]], np.ndarray] = {}
_GRID_CACHE: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}

# SPB paint-finish perf loop 2026-06-04: the strand/forged loop fields (_forged,
# _fiberglass_strands) are built at a capped resolution then cv2.resize'd up to the
# full 2048 canvas. The per-line np.sin loop is the whole cost (18 lines for strands,
# 9-14 for forged) so it scales with the capped pixel count. Dropping the cap from
# 960 -> 576 cuts the trig loop ~2.8x with the softening invisible at swatch scale
# (these fields are near-flat once downsampled to a 160px swatch). Measured paint
# std@256 drift at 576 (vs the 960 baseline) is +10.0% / +10.0% / +7.6% for
# fiberglass / forged_composite / forged_carbon_vis -- well inside the +/-20% gate.
# (256px catalog swatches never trip the cap, so their std is bit-identical.)
_FIELD_BUILD_CAP = 576.0
# SPB paint-finish perf loop tick 2026-05-31 05:38; owner: "Speed is king in this app."
# Exact cache/allocation cleanup only: carbon_ceramic 4468.2->3264.7 ms,
# carbon_weave 3136.3->2114.1 ms, carbon_base 3000.9->2380.3 ms; std drift 0.


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _grid(shape):
    h, w = shape
    key = (int(h), int(w))
    cached = _GRID_CACHE.get(key)
    if cached is not None:
        return cached
    yy, xx = get_mgrid((h, w))
    x = np.asarray(xx, dtype=np.float32) / max(w - 1, 1)
    y = np.asarray(yy, dtype=np.float32) / max(h - 1, 1)
    if len(_GRID_CACHE) > 3:
        _GRID_CACHE.clear()
    _GRID_CACHE[key] = (y, x)
    return y, x


def _norm(v):
    v = np.asarray(v, dtype=np.float32)
    lo = float(v.min())
    hi = float(v.max())
    if hi - lo < 1e-6:
        return np.zeros_like(v, dtype=np.float32)
    return ((v - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, seed, scales=(2, 5, 13, 31), weights=(0.28, 0.28, 0.24, 0.20)):
    key = (_shape2(shape), int(seed), tuple(float(v) for v in scales), tuple(float(v) for v in weights))
    cached = _NOISE_CACHE.get(key)
    if cached is not None:
        return cached
    out = _norm(multi_scale_noise(shape, list(scales), list(weights), seed))
    if len(_NOISE_CACHE) > 96:
        _NOISE_CACHE.clear()
    _NOISE_CACHE[key] = out
    return out


def _blend(paint, mask, pm, color, strength=0.92):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask, 0, 1)[:, :, None] * np.clip(pm * strength, 0, 1)
    # SPB perf 2026-06-04: every paint_* caller already feeds a color clipped to
    # [0, 1], so the inner np.clip(color, ...) was a redundant full-res pass; drop
    # it (output is unchanged because color is already in range). Fuse the lerp as
    #   out = paint + (color - paint) * a
    # so we build one temp instead of the paint*(1-a) + color*a two-temp form, then
    # apply the single safety clip the original contract guaranteed.
    rgb = paint[:, :, :3]
    paint[:, :, :3] = rgb + (color - rgb) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _resize_fields(fields, shape):
    h, w = _shape2(shape)
    return tuple(_resize_array(np.asarray(field, dtype=np.float32), h, w) for field in fields)


def _line_field(y, x, angles, offsets, widths, freqs):
    field = np.zeros_like(y, dtype=np.float32)
    for ang, off, width, freq in zip(angles, offsets, widths, freqs):
        coord = x * np.cos(ang) + y * np.sin(ang)
        d = np.abs(np.sin((coord * freq + off) * np.pi))
        field = np.maximum(field, np.clip((width - d) / max(width, 1e-5), 0, 1).astype(np.float32))
    return field


def _twill(shape, seed, scale=92.0, warp=0.10):
    cache_key = ("twill", _shape2(shape), int(seed), float(scale), float(warp))
    cached = _FIELD_CACHE.get(cache_key)
    if cached is not None:
        return cached
    y, x = _grid(shape)
    n = _noise(shape, seed + 10, (4, 11, 27), (0.25, 0.35, 0.40))
    u = (x + y * (1.0 + warp) + (n - 0.5) * 0.035) * scale
    v = (x * (1.0 - warp) - y + (n - 0.5) * 0.035) * scale
    a = np.sin(u * np.pi)
    b = np.sin(v * np.pi)
    tow_a = np.clip((0.42 - np.abs(a)) * 3.4, 0, 1)
    tow_b = np.clip((0.42 - np.abs(b)) * 3.4, 0, 1)
    over = ((np.floor(u / 2.0) + np.floor(v / 2.0)) % 2).astype(np.float32)
    weave = np.clip(tow_a * over + tow_b * (1.0 - over), 0, 1)
    rib = np.clip((0.055 - np.minimum(np.abs(a), np.abs(b))) * 11.0, 0, 1)
    grain = _noise(shape, seed + 11, (1, 2, 4), (0.42, 0.34, 0.24))
    out = (weave.astype(np.float32), rib.astype(np.float32), grain.astype(np.float32))
    if len(_FIELD_CACHE) > 64:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[cache_key] = out
    return out


def _plain_weave(shape, seed, scale=112.0):
    y, x = _grid(shape)
    n = _noise(shape, seed + 20, (3, 7, 17), (0.32, 0.34, 0.34))
    u = (x + (n - 0.5) * 0.025) * scale
    v = (y + (n - 0.5) * 0.025) * scale
    thread_x = np.clip((0.46 - np.abs(np.sin(u * np.pi))) * 3.0, 0, 1)
    thread_y = np.clip((0.46 - np.abs(np.sin(v * np.pi))) * 3.0, 0, 1)
    over = ((np.floor(u) + np.floor(v)) % 2).astype(np.float32)
    weave = np.clip(thread_x * over + thread_y * (1 - over), 0, 1)
    seam = np.clip((0.035 - np.minimum(np.abs(np.sin(u * np.pi)), np.abs(np.sin(v * np.pi)))) * 13.0, 0, 1)
    return weave.astype(np.float32), seam.astype(np.float32), n.astype(np.float32)


def _basket(shape, seed, scale=74.0):
    y, x = _grid(shape)
    n = _noise(shape, seed + 30, (3, 9, 21), (0.30, 0.34, 0.36))
    u = (x + (n - 0.5) * 0.018) * scale
    v = (y + (n - 0.5) * 0.018) * scale
    block = ((np.floor(u / 2.0) + np.floor(v / 2.0)) % 2).astype(np.float32)
    tx = np.clip((0.62 - np.abs(np.sin(u * np.pi * 0.5))) * 2.2, 0, 1)
    ty = np.clip((0.62 - np.abs(np.sin(v * np.pi * 0.5))) * 2.2, 0, 1)
    weave = np.clip(tx * block + ty * (1 - block), 0, 1)
    edge = np.clip((0.04 - np.minimum(np.abs(np.sin(u * np.pi * 0.5)), np.abs(np.sin(v * np.pi * 0.5)))) * 14.0, 0, 1)
    return weave.astype(np.float32), edge.astype(np.float32), n.astype(np.float32)


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


def _forged(shape, seed, dense=False):
    cache_key = ("forged_dense" if dense else "forged", _shape2(shape), int(seed))
    cached = _FIELD_CACHE.get(cache_key)
    if cached is not None:
        return cached
    h, w = _shape2(shape)
    if max(h, w) > _FIELD_BUILD_CAP:
        scale = _FIELD_BUILD_CAP / float(max(h, w))
        small_shape = (max(128, int(round(h * scale))), max(128, int(round(w * scale))))
        fields = _resize_fields(_forged(small_shape, seed, dense=dense), (h, w))
        if len(_FIELD_CACHE) > 48:
            _FIELD_CACHE.clear()
        _FIELD_CACHE[cache_key] = fields
        return fields
    y, x = _grid(shape)
    n1 = _noise(shape, seed + 40, (5, 13, 29, 61), (0.2, 0.3, 0.3, 0.2))
    n2 = _noise(shape, seed + 41, (3, 9, 23, 49), (0.2, 0.3, 0.3, 0.2))
    shard = np.zeros(shape, dtype=np.float32)
    count = 14 if dense else 9
    rng = np.random.RandomState((seed + 42) & 0x7FFFFFFF)
    # Per-line jitter term is constant across the loop -- hoist it out of the
    # np.sin loop so it is built once instead of `count` times.
    coord_jitter = (n1 - 0.5) * 0.035
    for _ in range(count):
        ang = rng.uniform(0, np.pi)
        freq = rng.uniform(20, 78 if dense else 56)
        off = rng.uniform(0, 1)
        coord = x * np.cos(ang) + y * np.sin(ang) + coord_jitter
        sliver = np.clip((0.035 - np.abs(np.sin((coord * freq + off) * np.pi))) * 13.0, 0, 1)
        shard = np.maximum(shard, sliver.astype(np.float32))
    marble = _norm(n1 * 0.58 + n2 * 0.42 + shard * 0.45)
    edges = np.clip(np.sqrt(sobel(marble, axis=0) ** 2 + sobel(marble, axis=1) ** 2) * 1.4, 0, 1)
    out = (marble.astype(np.float32), shard.astype(np.float32), edges.astype(np.float32))
    if len(_FIELD_CACHE) > 48:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[cache_key] = out
    return out


def paint_carbon_base(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    weave, rib, grain = _twill((h, w), seed, 118.0, 0.18)
    y, x = _grid((h, w))
    directional = 0.070 + weave * 0.095 + rib * 0.045 + grain * 0.035 + x * 0.020
    color = np.stack([directional * 0.72, directional * 0.82, directional], axis=-1)
    color = np.clip(color + rib[:, :, None] * [0.015, 0.020, 0.030], 0, 1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_carbon_base(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    weave, rib, grain = _twill((h, w), seed, 118.0, 0.18)
    M = np.clip(58 + weave * 88 * sm + rib * 38 + grain * 18, 0, 255)
    R = np.clip(34 - weave * 17 - rib * 8 + grain * 12, 15, 255)
    CC = np.clip(18 + rib * 10 + grain * 4, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_carbon_ceramic(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    weave, rib, grain = _twill((h, w), seed, 94.0, -0.08)
    y, x = _grid((h, w))
    ceramic = _noise((h, w), seed + 101, (11, 29, 67), (0.28, 0.38, 0.34))
    wear = _line_field(y, x, [0.08, -0.12, 0.22], [0.1, 0.45, 0.77], [0.004, 0.003, 0.0025], [42, 57, 76])
    heat = _hsv(0.57 + x * 0.05 + ceramic * 0.08, 0.20 + wear * 0.34, 0.10 + ceramic * 0.20 + wear * 0.12)
    base = 0.115 + ceramic * 0.125 + weave * 0.034 + grain * 0.030
    color = np.stack([base * 0.86, base * 0.95, base * 0.93], axis=-1)
    color = np.clip(color + heat * 0.25 + wear[:, :, None] * [0.13, 0.11, 0.070] - rib[:, :, None] * 0.032, 0, 1)
    return _blend(paint, mask, pm, color, 0.93)


def spec_carbon_ceramic(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    weave, rib, _ = _twill((h, w), seed, 94.0, -0.08)
    ceramic = _noise((h, w), seed + 101, (11, 29, 67), (0.28, 0.38, 0.34))
    M = np.clip(24 + weave * 52 * sm + rib * 16, 0, 255)
    R = np.clip(72 + ceramic * 82 - weave * 20, 15, 255)
    CC = np.clip(18 + ceramic * 18 + rib * 6, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_aramid(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    weave, seam, n = _plain_weave((h, w), seed, 132.0)
    gold = 0.46 + weave * 0.25 + n * 0.10
    color = np.stack([gold * 1.20, gold * 0.93, gold * 0.43], axis=-1)
    color = np.clip(color - seam[:, :, None] * [0.12, 0.09, 0.035], 0, 1)
    return _blend(paint, mask, pm, color, 0.92)


def spec_aramid(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    weave, seam, n = _plain_weave((h, w), seed, 132.0)
    M = np.clip(6 + weave * 18 * sm + n * 6, 0, 255)
    R = np.clip(96 + seam * 55 + (1 - weave) * 24, 15, 255)
    CC = np.clip(22 + weave * 18 + seam * 8, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def _fiberglass_strands(shape, seed):
    cache_key = ("fiberglass", _shape2(shape), int(seed))
    cached = _FIELD_CACHE.get(cache_key)
    if cached is not None:
        return cached
    h, w = _shape2(shape)
    if max(h, w) > _FIELD_BUILD_CAP:
        scale = _FIELD_BUILD_CAP / float(max(h, w))
        small_shape = (max(128, int(round(h * scale))), max(128, int(round(w * scale))))
        fields = _resize_fields(_fiberglass_strands(small_shape, seed), (h, w))
        if len(_FIELD_CACHE) > 48:
            _FIELD_CACHE.clear()
        _FIELD_CACHE[cache_key] = fields
        return fields
    y, x = _grid(shape)
    n = _noise(shape, seed + 201, (2, 6, 15, 39), (0.26, 0.28, 0.26, 0.20))
    rng = np.random.RandomState((seed + 202) & 0x7FFFFFFF)
    angles = rng.uniform(0, np.pi, 18)
    offsets = rng.uniform(0, 1, 18)
    widths = rng.uniform(0.0028, 0.008, 18)
    freqs = rng.uniform(18, 88, 18)
    strands = _line_field(y + (n - 0.5) * 0.025, x, angles, offsets, widths, freqs)
    mat = np.clip(strands * 0.75 + n * 0.36 + (_noise(shape, seed + 203, (1, 3, 7), (0.4, 0.35, 0.25)) > 0.84) * 0.18, 0, 1)
    out = (mat.astype(np.float32), strands.astype(np.float32))
    if len(_FIELD_CACHE) > 48:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[cache_key] = out
    return out


def paint_fiberglass(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    mat, strands = _fiberglass_strands((h, w), seed)
    base = 0.50 + mat * 0.23
    color = np.stack([base * 0.88, base * 0.96, base * 0.91], axis=-1)
    color = np.clip(color + strands[:, :, None] * [0.16, 0.18, 0.13], 0, 1)
    return _blend(paint, mask, pm, color, 0.90)


def spec_fiberglass(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    mat, strands = _fiberglass_strands((h, w), seed)
    M = np.clip(2 + strands * 18 * sm + mat * 4, 0, 255)
    R = np.clip(112 + mat * 86 + strands * 18, 15, 255)
    CC = np.clip(28 + mat * 30, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_forged_composite(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    marble, shard, edges = _forged((h, w), seed, dense=True)
    base = 0.025 + marble * 0.105 + shard * 0.055
    color = np.stack([base * 0.86, base * 0.92, base * 1.05], axis=-1)
    color = np.clip(color + edges[:, :, None] * [0.045, 0.052, 0.066], 0, 1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_forged_composite(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    marble, shard, edges = _forged((h, w), seed, dense=True)
    M = np.clip(44 + marble * 78 * sm + shard * 52, 0, 255)
    R = np.clip(42 + (1 - marble) * 36 - shard * 18 + edges * 10, 15, 255)
    CC = np.clip(17 + edges * 18 + shard * 7, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def _graphene_lattice(shape, seed):
    y, x = _grid(shape)
    n = _noise(shape, seed + 301, (4, 13, 31), (0.26, 0.36, 0.38))
    sqrt3 = np.sqrt(3.0)
    scale = 48.0
    q = (2.0 / 3.0 * x + (n - 0.5) * 0.015) * scale
    r = (-1.0 / 3.0 * x + sqrt3 / 3.0 * y + (n - 0.5) * 0.015) * scale
    qf = q - np.floor(q)
    rf = r - np.floor(r)
    sf = qf + rf
    edge = np.minimum.reduce([qf, 1 - qf, rf, 1 - rf, np.abs(sf - 1.0)])
    line = np.clip((0.055 - edge) * 22.0, 0, 1)
    cell = _norm(np.sin(np.floor(q) * 1.73 + np.floor(r) * 2.11) * 0.5 + n * 0.5)
    return line.astype(np.float32), cell.astype(np.float32)


def paint_graphene(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    line, cell = _graphene_lattice((h, w), seed)
    y, x = _grid((h, w))
    base = 0.040 + cell * 0.070 + line * 0.080
    sheen = _hsv(0.48 + x * 0.10 + cell * 0.05, 0.42, 0.12 + line * 0.32)
    color = np.stack([base * 0.75, base * 0.92, base * 1.0], axis=-1)
    color = np.clip(color + sheen * line[:, :, None] * 0.28, 0, 1)
    return _blend(paint, mask, pm, color, 0.93)


def spec_graphene(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    line, cell = _graphene_lattice((h, w), seed)
    M = np.clip(116 + cell * 44 + line * 50 * sm, 0, 255)
    R = np.clip(20 + (1 - line) * 18 + cell * 12, 15, 255)
    CC = np.clip(16 + line * 10 + cell * 4, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_hybrid_weave(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    weave, rib, grain = _twill((h, w), seed, 104.0, 0.12)
    y, x = _grid((h, w))
    material = ((np.floor((x + y) * 92.0) + np.floor((x - y) * 88.0)) % 3 == 0).astype(np.float32)
    material = np.clip(material * 0.82 + weave * 0.18, 0, 1)
    carbon = np.stack([0.035 + grain * 0.035, 0.039 + grain * 0.036, 0.050 + grain * 0.042], axis=-1)
    kevlar = np.stack([0.62 + grain * 0.12, 0.45 + grain * 0.08, 0.13 + grain * 0.04], axis=-1)
    color = carbon * (1 - material[:, :, None]) + kevlar * material[:, :, None]
    color = np.clip(color * (0.70 + weave[:, :, None] * 0.42) + rib[:, :, None] * [0.05, 0.04, 0.02], 0, 1)
    return _blend(paint, mask, pm, color, 0.93)


def spec_hybrid_weave(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    weave, rib, grain = _twill((h, w), seed, 104.0, 0.12)
    y, x = _grid((h, w))
    material = ((np.floor((x + y) * 92.0) + np.floor((x - y) * 88.0)) % 3 == 0).astype(np.float32)
    material = np.clip(material * 0.82 + weave * 0.18, 0, 1)
    M = np.clip((1 - material) * 80 + material * 12 + weave * 40 * sm + rib * 24, 0, 255)
    R = np.clip((1 - material) * 38 + material * 96 - weave * 16 + grain * 16, 15, 255)
    CC = np.clip(18 + weave * 9 + rib * 8, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_kevlar_base(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    weave, edge, n = _basket((h, w), seed, 86.0)
    gold = 0.44 + weave * 0.26 + n * 0.10
    color = np.stack([gold * 1.26, gold * 0.88, gold * 0.18], axis=-1)
    color = np.clip(color - edge[:, :, None] * [0.15, 0.10, 0.02], 0, 1)
    return _blend(paint, mask, pm, color, 0.92)


def spec_kevlar_base(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    weave, edge, n = _basket((h, w), seed, 86.0)
    M = np.clip(5 + weave * 15 * sm + edge * 6, 0, 255)
    R = np.clip(86 + (1 - weave) * 38 + edge * 52 + n * 14, 15, 255)
    CC = np.clip(21 + weave * 16 + edge * 8, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_carbon_weave(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    weave, rib, grain = _twill((h, w), seed, 156.0, -0.20)
    y, x = _grid((h, w))
    micro = _line_field(y, x, [0.74, -0.82, 0.0], [0.2, 0.53, 0.71], [0.004, 0.003, 0.0025], [95, 122, 148])
    base = 0.060 + weave * 0.075 + rib * 0.046 + grain * 0.034 + micro * 0.040
    color = np.stack([base * 0.78, base * 0.87, base * 1.08], axis=-1)
    return _blend(paint, mask, pm, np.clip(color, 0, 1), 0.93)


def spec_carbon_weave(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    weave, rib, grain = _twill((h, w), seed, 156.0, -0.20)
    M = np.clip(64 + weave * 72 * sm + rib * 44 + grain * 16, 0, 255)
    R = np.clip(40 - weave * 18 - rib * 10 + grain * 13, 15, 255)
    CC = np.clip(18 + rib * 9 + weave * 5, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_forged_carbon_vis(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    marble, shard, edges = _forged((h, w), seed + 700, dense=False)
    flakes = np.clip(shard * 0.75 + (marble > 0.68).astype(np.float32) * 0.35, 0, 1)
    base = 0.032 + marble * 0.085 + flakes * 0.060
    color = np.stack([base * 0.92, base * 0.96, base * 1.08], axis=-1)
    color = np.clip(color + edges[:, :, None] * [0.035, 0.040, 0.055], 0, 1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_forged_carbon_vis(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    marble, shard, edges = _forged((h, w), seed + 700, dense=False)
    flakes = np.clip(shard * 0.75 + (marble > 0.68).astype(np.float32) * 0.35, 0, 1)
    M = np.clip(52 + flakes * 90 * sm + edges * 30, 0, 255)
    R = np.clip(38 + (1 - marble) * 42 - flakes * 18, 15, 255)
    CC = np.clip(17 + flakes * 10 + edges * 14, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


OWNER_REVIEW_CARBON_COMPOSITE_OVERRIDES = {
    "aramid": (paint_aramid, spec_aramid),
    "carbon_base": (paint_carbon_base, spec_carbon_base),
    "carbon_ceramic": (paint_carbon_ceramic, spec_carbon_ceramic),
    "fiberglass": (paint_fiberglass, spec_fiberglass),
    "forged_composite": (paint_forged_composite, spec_forged_composite),
    "graphene": (paint_graphene, spec_graphene),
    "hybrid_weave": (paint_hybrid_weave, spec_hybrid_weave),
    "kevlar_base": (paint_kevlar_base, spec_kevlar_base),
    "carbon_weave": (paint_carbon_weave, spec_carbon_weave),
    "forged_carbon_vis": (paint_forged_carbon_vis, spec_forged_carbon_vis),
}
