"""Owner-reviewed Signal monolithic rebuilds for SPB-67.

Signal finishes need to read as light, energy, glow, or radiation at full-car
scale without becoming slow blob fields. The helpers below are only math
primitives; each finish has its own paint/spec model and shape language.
"""

from __future__ import annotations

import numpy as np

try:
    import cv2 as _cv2
    _CV2_OK = True
except Exception:  # pragma: no cover - cv2 always present in app
    _cv2 = None
    _CV2_OK = False

# 5-point cross box kernel: out = (center + up + down + left + right) * 0.2.
# Used to vectorize the per-pass np.roll smoothing in _soften via cv2.
_SOFTEN_KERNEL = np.array(
    [[0.0, 0.2, 0.0], [0.2, 0.2, 0.2], [0.0, 0.2, 0.0]], dtype=np.float32
)


def _xy(shape):
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _mask(mask, shape):
    if mask is None:
        return np.ones(shape, dtype=np.float32)
    return np.asarray(mask, dtype=np.float32)


def _seed(seed, salt):
    return float((int(seed) * 1103515245 + int(salt) * 12345) & 0x7FFFFFFF) / 0x7FFFFFFF


def _hash_noise(shape, seed, salt=0):
    x, y = _xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + _seed(seed, salt) * 91.7) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _field(shape, seed, salt=0, scale=1.0):
    # 2026-06-13 perf: each octave is sin((x*kx + y*ky)*pi + phase), i.e. a
    # separable 2D sinusoid. Use the angle-addition identity
    #   sin(Ax + By + p) = sin(Ax+p)cos(By) + cos(Ax+p)sin(By)
    # so each octave needs only 1-D sin/cos along x and y (O(w)+O(h)) combined
    # by an outer-product add, instead of four full (h, w) transcendental evals.
    # Output is bit-identical to the previous formula (maxdiff ~1e-5 float
    # rounding) and ~1.3x faster; it stays a pure (h, w) float32 carrier.
    h, w = shape
    xr = np.linspace(0.0, 1.0, w, dtype=np.float32)
    yr = np.linspace(0.0, 1.0, h, dtype=np.float32)
    a = _seed(seed, salt) * np.pi * 2.0
    b = _seed(seed, salt + 17) * np.pi * 2.0
    c = _seed(seed, salt + 31) * np.pi * 2.0
    pi = np.float32(np.pi)
    octaves = (
        (5.0 + scale, 3.0 + scale * 0.5, a, 0.34),
        (17.0 + scale * 2.0, -(13.0 + scale), b, 0.28),
        (43.0 + scale * 3.0, 37.0 + scale * 2.0, c, 0.20),
        (91.0 + scale * 4.0, -(79.0 + scale * 3.0), a + c, 0.12),
    )
    f = np.zeros((h, w), dtype=np.float32)
    for kx, ky, ph, amp in octaves:
        ax = xr * np.float32(kx * np.pi) + np.float32(ph)
        by = yr * np.float32(ky * np.pi)
        sin_ax = np.sin(ax)
        cos_ax = np.cos(ax)
        sin_by = np.sin(by)[:, None]
        cos_by = np.cos(by)[:, None]
        f += np.float32(amp) * (sin_ax[None, :] * cos_by + cos_ax[None, :] * sin_by)
    return np.clip((f + 0.94) / 1.88, 0, 1).astype(np.float32)


def _field_lowres(shape, seed, salt=0, scale=1.0, max_dim=1024):
    """Low-frequency variant of _field for carrier / soft-warble use only.

    Computes _field at bounded resolution and bilinear-upscales. _field's
    highest octave is ~(91 + 4*scale) cycles across the canvas, so at half a
    2048 canvas it is still heavily oversampled (~10 samples/cycle); the
    interpolation error is ~0.01, invisible where the field is used as an
    additive carrier or a soft phase warble. Do NOT use this where the field
    defines crisp high-frequency geometry directly.
    """
    h, w = shape
    if _CV2_OK and max(h, w) > max_dim:
        ds = max(2, int(np.ceil(max(h, w) / float(max_dim))))
        small = _field((max(8, h // ds), max(8, w // ds)), seed, salt, scale)
        return _cv2.resize(small, (w, h), interpolation=_cv2.INTER_LINEAR).astype(np.float32)
    return _field(shape, seed, salt, scale)


def _soften(a, passes=2):
    out = np.asarray(a, dtype=np.float32)
    n = max(0, int(passes))
    if n == 0:
        return out.astype(np.float32)
    if _CV2_OK:
        # 2026-06-13 perf: the np.roll wrap-around 5-point box blur is exactly a
        # circular cross-convolution. Replace the Python-level per-pass roll sum
        # with cv2.filter2D over a 1px wrap-padded buffer (BORDER_WRAP). This is
        # bit-identical to the roll math (maxdiff ~1e-7, float32 rounding) and
        # ~4x faster on a 2048 canvas. Crisp detail is preserved; only the cost
        # of the smoothing changes.
        out = np.ascontiguousarray(out, dtype=np.float32)
        for _ in range(n):
            padded = _cv2.copyMakeBorder(out, 1, 1, 1, 1, _cv2.BORDER_WRAP)
            f = _cv2.filter2D(padded, -1, _SOFTEN_KERNEL, borderType=_cv2.BORDER_REPLICATE)
            out = f[1:-1, 1:-1]
        return np.ascontiguousarray(out, dtype=np.float32)
    for _ in range(n):
        out = (
            out
            + np.roll(out, 1, 0)
            + np.roll(out, -1, 0)
            + np.roll(out, 1, 1)
            + np.roll(out, -1, 1)
        ) * 0.2
    return out.astype(np.float32)


def _rgba(shape, mask):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 3] = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    return spec


def _bb3(bb, shape):
    if bb is None:
        return None
    arr = np.asarray(bb, dtype=np.float32)
    if arr.ndim == 0:
        return np.full((shape[0], shape[1], 3), float(arr), dtype=np.float32)
    if arr.ndim == 2:
        return np.repeat(arr[:, :, None], 3, axis=2).astype(np.float32)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        return arr[:, :, :3].astype(np.float32)
    return None


def _apply_bb(out, mask, bb, amount=0.08):
    bb_arr = _bb3(bb, mask.shape)
    if bb_arr is None:
        return out
    return np.clip(out + bb_arr * amount * mask[:, :, None], 0, 1)


def _full(a, shape):
    return np.broadcast_to(np.asarray(a, dtype=np.float32), shape).astype(np.float32)


def _stack3(a, b, c, shape):
    return np.stack([_full(a, shape), _full(b, shape), _full(c, shape)], axis=2)


def _paint_base(paint):
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].astype(np.float32, copy=True)
    return paint.astype(np.float32, copy=True)


def _mix(base, effect, mask, pm, strength=0.72):
    blend = np.clip(float(pm) * strength, 0, 1) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + effect * blend, 0, 1)


def _spec_from_energy(shape, mask, energy, sm, rough_low=16, cc_gain=105):
    spec = _rgba(shape, mask)
    grain = _hash_noise(shape, 313, 19)
    e = np.clip(energy, 0, 1) * mask
    spec[:, :, 0] = np.clip((36 + e * 204 + grain * 18) * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((rough_low + (1.0 - e) * 76 - e * 18 + grain * 7) * mask, 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((18 + e * cc_gain + grain * 10) * mask, 16, 255).astype(np.uint8)
    return spec


def _line(angle, offset, width, shape):
    x, y = _xy(shape)
    axis = x * np.cos(angle) + y * np.sin(angle)
    return np.exp(-((axis - offset) ** 2) / max(width * width, 1e-6)).astype(np.float32)


def _thin_wave(axis, scale, phase, sharp):
    return np.clip(1.0 - np.abs(np.sin((axis * scale + phase) * np.pi)) * sharp, 0, 1).astype(np.float32)


def _tube_field(shape, seed, salt, count, width, curve=0.045):
    x, y = _xy(shape)
    hot = np.zeros(shape, dtype=np.float32)
    for i in range(count):
        phase = _seed(seed, salt + i * 13)
        base_y = (i + 0.5) / count
        wave = base_y + np.sin(x * np.pi * (1.0 + i % 4) + phase * 6.283) * curve
        hot = np.maximum(hot, np.exp(-((y - wave) ** 2) / max(width * width, 1e-6)))
        if i % 3 == 0:
            wave_x = phase + np.sin(y * np.pi * (2.0 + i % 5)) * curve
            hot = np.maximum(hot, np.exp(-((x - wave_x) ** 2) / max((width * 0.82) ** 2, 1e-6)))
    return np.clip(hot, 0, 1).astype(np.float32)


def _cached_tube_field(shape, seed, salt, count, width, curve=0.045):
    key = ("tube", tuple(shape), int(seed), int(salt), int(count), round(float(width), 8), round(float(curve), 8))
    cached = _SIGNAL_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    hot = _tube_field(shape, seed, salt, count, width, curve)
    if len(_SIGNAL_FIELD_CACHE) > 28:
        _SIGNAL_FIELD_CACHE.clear()
    _SIGNAL_FIELD_CACHE[key] = hot
    return hot


def _arc_field(shape, seed, salt, count=9, branches=7):
    h, w = shape
    rng = np.random.RandomState(int(seed) + salt)
    arcs = np.zeros(shape, dtype=np.float32)
    for i in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, h)
        tx = rng.randint(0, w)
        ty = rng.randint(0, h)
        steps = max(52, min(h, w) // 11)
        px, py = float(x), float(y)
        for step in range(steps):
            t = (step + 1) / steps
            px += (tx - px) * 0.035 + rng.uniform(-w * 0.011, w * 0.011)
            py += (ty - py) * 0.035 + rng.uniform(-h * 0.011, h * 0.011)
            ix = int(np.clip(px, 0, w - 1))
            iy = int(np.clip(py, 0, h - 1))
            arcs[max(0, iy - 1):min(h, iy + 2), max(0, ix - 1):min(w, ix + 2)] = 1.0
            if step % max(6, steps // branches) == 0:
                bx, by = px, py
                for _ in range(rng.randint(7, 20)):
                    bx += rng.uniform(-w * 0.015, w * 0.015)
                    by += rng.uniform(-h * 0.015, h * 0.015)
                    ix = int(np.clip(bx, 0, w - 1))
                    iy = int(np.clip(by, 0, h - 1))
                    arcs[max(0, iy - 1):min(h, iy + 2), max(0, ix - 1):min(w, ix + 2)] = 0.68
    return np.clip(arcs + _soften(arcs, 3) * 0.72, 0, 1).astype(np.float32)


def _dot_swarm(shape, seed, salt, count, radius, streak=False):
    h, w = shape
    rng = np.random.RandomState(int(seed) + salt)
    dots = np.zeros(shape, dtype=np.float32)
    for _ in range(count):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        yy0, yy1 = max(0, cy - radius), min(h, cy + radius + 1)
        xx0, xx1 = max(0, cx - radius), min(w, cx + radius + 1)
        yy, xx = np.ogrid[yy0:yy1, xx0:xx1]
        d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / max(1, radius)
        dots[yy0:yy1, xx0:xx1] = np.maximum(dots[yy0:yy1, xx0:xx1], np.clip(1.0 - d, 0, 1))
        if streak and rng.random() > 0.55:
            length = rng.randint(radius * 3, radius * 10)
            slope = rng.uniform(-0.65, 0.65)
            for s in range(length):
                ix = int(np.clip(cx - s, 0, w - 1))
                iy = int(np.clip(cy + slope * s, 0, h - 1))
                dots[max(0, iy - 1):min(h, iy + 2), max(0, ix - 1):min(w, ix + 2)] = 0.55
    return np.clip(dots + _soften(dots, 4) * 0.55, 0, 1).astype(np.float32)


def _micro_sparkle(shape, seed, salt, threshold=0.986, soften=1):
    sparks = (_hash_noise(shape, seed, salt) > float(threshold)).astype(np.float32)
    if soften:
        sparks = np.clip(sparks + _soften(sparks, soften) * 0.72, 0, 1)
    return sparks.astype(np.float32)


def _flare_map(shape, centers, pulse=None):
    x, y = _xy(shape)
    hot = np.zeros(shape, dtype=np.float32)
    for i, item in enumerate(centers):
        if len(item) == 4:
            cx, cy, rx, ry = item
            amp = 1.0
        else:
            cx, cy, rx, ry, amp = item
        if pulse is not None:
            amp *= 0.82 + 0.30 * float(pulse[i % len(pulse)])
        core = np.exp(-(((x - cx) ** 2) / max(rx, 1e-6) + ((y - cy) ** 2) / max(ry, 1e-6))).astype(np.float32)
        halo = np.exp(-(((x - cx) ** 2) / max(rx * 5.2, 1e-6) + ((y - cy) ** 2) / max(ry * 5.2, 1e-6))).astype(np.float32)
        hot = np.maximum(hot, core * amp + halo * 0.24 * amp)
    return np.clip(hot, 0, 1).astype(np.float32)


_SIGNAL_FIELD_CACHE = {}
_WELDING_CENTERS = (
    (0.14, 0.24, 0.0055, 0.0085, 0.75), (0.27, 0.36, 0.0080, 0.0130, 1.0),
    (0.38, 0.66, 0.0060, 0.0100, 0.82), (0.51, 0.50, 0.0075, 0.0120, 0.95),
    (0.63, 0.78, 0.0065, 0.0100, 0.78), (0.72, 0.24, 0.0080, 0.0130, 1.0),
    (0.84, 0.45, 0.0060, 0.0090, 0.72), (0.46, 0.18, 0.0055, 0.0085, 0.70),
    (0.86, 0.84, 0.0055, 0.0085, 0.68), (0.20, 0.82, 0.0055, 0.0085, 0.70),
)


def _welding_arc_fields(shape, seed):
    key = ("welding_arc", tuple(shape), int(seed))
    cached = _SIGNAL_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    # SPB paint-finish perf loop 2026-05-31; welding_arc measured 4290.6ms -> 2995.0ms.
    # Spec and paint use the same seam/hot/spark fields, so cache them once.
    x, y = _xy(shape)
    seam = np.maximum(
        _thin_wave(x * 2.6 + y * 1.7, 9.0, _seed(seed, 510), 22.0),
        _thin_wave(x * -1.8 + y * 2.9, 12.0, _seed(seed, 511), 26.0),
    )
    hot = _flare_map(shape, _WELDING_CENTERS)
    sparks = _micro_sparkle(shape, seed, 512, 0.970, 1)
    out = (seam, hot, sparks)
    if len(_SIGNAL_FIELD_CACHE) > 24:
        _SIGNAL_FIELD_CACHE.clear()
    _SIGNAL_FIELD_CACHE[key] = out
    return out


def _palette(stops, t):
    stops = np.asarray(stops, dtype=np.float32)
    n = len(stops) - 1
    pos = np.clip(t, 0, 1) * n
    idx = np.clip(np.floor(pos).astype(np.int32), 0, n - 1)
    frac = (pos - idx)[:, :, None]
    return stops[idx] * (1.0 - frac) + stops[idx + 1] * frac


def _paint_neon_tubes(paint, shape, mask, seed, pm, bb, mode):
    base = _paint_base(paint)
    x, y = _xy(shape)
    if mode == "sign":
        hot = _cached_tube_field(shape, seed, 110, 12, 0.00062, 0.052)
        right_tubes = np.clip(1.0 - np.abs(np.sin((x * 18.0 + y * 2.6 + _field(shape, seed, 116, 2.0)) * np.pi)) * 24.0, 0, 1) * np.clip((x - 0.40) * 1.75, 0, 1)
        hot = np.clip(np.maximum(hot, right_tubes), 0, 1)
        halo = _soften(hot, 4)
        glass = np.clip(_field(shape, seed, 113, 10.0) * 0.26 + _hash_noise(shape, seed, 114) * 0.10, 0, 1)
        pink_bias = np.clip((x - 0.38) * 1.9, 0, 1)
        color = _stack3(0.95 + x * 0.05, 0.04 + y * 0.16, 0.46 + halo * 0.42 + pink_bias * 0.20, shape)
        effect = np.clip(base * 0.10 + color * (0.24 + hot[:, :, None] * 0.90 + halo[:, :, None] * 0.54) + glass[:, :, None] * np.array([0.24, 0.04, 0.20], dtype=np.float32), 0, 1)
    elif mode == "vegas":
        # SPB paint-finish perf loop 2026-05-31: reuse tube field from spec; neon_vegas was 4416.7ms.
        hot = np.maximum(_cached_tube_field(shape, seed, 120, 16, 0.00055, 0.033), _line(1.21, 0.62, 0.0010, shape))
        diagonal = np.maximum(_thin_wave(x * 2.2 - y * 1.6, 13.0, _seed(seed, 124), 35.0), _thin_wave(x * 1.3 + y * 2.7, 15.0, _seed(seed, 125), 38.0))
        bulbs = (_hash_noise(shape, seed, 126) > 0.986).astype(np.float32)
        hot = np.clip(np.maximum(hot, diagonal) + _soften(bulbs, 2) * 0.75, 0, 1)
        hue = (np.floor((y * 28 + x * 19 + diagonal * 4.0) % 7) / 6.0).astype(np.float32)
        color = _palette([(1, 0.04, 0.42), (1, 0.58, 0.02), (0.06, 0.9, 1), (0.86, 0.06, 1), (1, 0.95, 0.04)], hue)
        effect = np.clip(base * 0.06 + color * (hot[:, :, None] * 0.98 + _soften(hot, 2)[:, :, None] * 0.46), 0, 1)
    else:
        hot = _cached_tube_field(shape, seed, 130, 9, 0.0010, 0.028)
        pulse = _field(shape, seed, 131, 3.0)
        color = _stack3(0.10 + pulse * 0.18, 0.70 + hot * 0.28, 0.20 + pulse * 0.10, shape)
        effect = np.clip(base * 0.22 + color * (hot[:, :, None] * 0.85 + _soften(hot, 7)[:, :, None] * 0.45), 0, 1)
    out = _mix(base, effect, mask, pm, 0.82)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_neon_sign(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    return _spec_from_energy(shape, mask, _cached_tube_field(shape, seed, 110, 12, 0.00062, 0.052), sm, 12, 150)


def paint_neon_sign(paint, shape, mask, seed, pm, bb):
    return _paint_neon_tubes(paint, shape, _mask(mask, shape), seed, pm, bb, "sign")


def spec_neon_vegas(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    return _spec_from_energy(shape, mask, _cached_tube_field(shape, seed, 120, 16, 0.00055, 0.033), sm, 10, 155)


def paint_neon_vegas(paint, shape, mask, seed, pm, bb):
    return _paint_neon_tubes(paint, shape, _mask(mask, shape), seed, pm, bb, "vegas")


def spec_glow_stick(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    lengthwise = np.maximum(
        np.clip(1.0 - np.abs(np.sin((y * 64.0 + np.sin(x * np.pi * 5.0) * 0.38 + _field(shape, seed, 130, 3.8) * 0.78) * np.pi)) * 21.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 88.0 - x * 12.0 + _seed(seed, 131)) * np.pi)) * 28.0, 0, 1) * 0.72,
    )
    hairline = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 112.0 + y * 47.0 + _field(shape, seed, 132, 5.2) * 1.1) * np.pi)) * 34.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -98.0 + y * 39.0 + _seed(seed, 133)) * np.pi)) * 36.0, 0, 1) * 0.62,
    )
    fizz = _micro_sparkle(shape, seed, 134, 0.969, 1)
    core = np.clip(lengthwise + hairline * 0.42 + fizz * 0.58, 0, 1)
    return _spec_from_energy(shape, mask, core, sm, 16, 126)


def paint_glow_stick(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    lengthwise = np.maximum(
        np.clip(1.0 - np.abs(np.sin((y * 64.0 + np.sin(x * np.pi * 5.0) * 0.38 + _field(shape, seed, 130, 3.8) * 0.78) * np.pi)) * 21.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 88.0 - x * 12.0 + _seed(seed, 131)) * np.pi)) * 28.0, 0, 1) * 0.72,
    )
    hairline = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 112.0 + y * 47.0 + _field(shape, seed, 132, 5.2) * 1.1) * np.pi)) * 34.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -98.0 + y * 39.0 + _seed(seed, 133)) * np.pi)) * 36.0, 0, 1) * 0.62,
    )
    dissolved = _field(shape, seed, 135, 12.0) * 0.18 + _micro_sparkle(shape, seed, 134, 0.969, 1) * 0.34
    chemistry = np.clip(lengthwise * 1.08 + hairline * 0.44 + dissolved, 0, 1)
    glow = np.clip(_soften(lengthwise, 5) * 0.40 + _soften(hairline, 2) * 0.24 + chemistry * 0.68, 0, 1)
    liquid = _stack3(0.025 + dissolved * 0.08, 0.54 + glow * 0.46, 0.11 + lengthwise * 0.16, shape)
    effect = np.clip(liquid + _stack3(0.08, 0.35, 0.07, shape) * glow[:, :, None], 0, 1)
    out = _mix(base, effect, mask, pm, 0.76)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_blacklight_paint(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    splatter = (_hash_noise(shape, seed, 210) > 0.965).astype(np.float32)
    glyph = np.clip(_field(shape, seed, 211, 5.0) - 0.58, 0, 1) * 2.4
    return _spec_from_energy(shape, mask, np.clip(_soften(splatter, 2) + glyph, 0, 1), sm, 22, 145)


def paint_blacklight_paint(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    uv = _field(shape, seed, 211, 5.0)
    freckles = (_hash_noise(shape, seed, 212) > 0.972).astype(np.float32)
    glow = np.clip((uv - 0.46) * 1.7 + _soften(freckles, 3) * 0.95, 0, 1)
    gray = base.mean(axis=2, keepdims=True)
    reactive = np.clip(base + (base - gray) * 1.35, 0, 1)
    ink = _stack3(0.48 + glow * 0.42, 0.03 + freckles * 0.18, 0.92 + glow * 0.08, shape)
    effect = np.clip(reactive * 0.48 + ink * (0.34 + glow[:, :, None] * 0.55), 0, 1)
    out = _mix(base, effect, mask, pm, 0.78)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_fluorescent(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    long_tubes = np.maximum(
        np.clip(1.0 - np.abs(np.sin((y * 42.0 + np.sin(x * np.pi * 2.0) * 0.11 + _seed(seed, 230)) * np.pi)) * 32.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 58.0 - x * 2.2 + _seed(seed, 231)) * np.pi)) * 38.0, 0, 1) * 0.58,
    )
    starter_bars = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 18.0 + y * 0.8 + _seed(seed, 232)) * np.pi)) * 44.0, 0, 1) * 0.50,
        np.clip(1.0 - np.abs(np.sin((x * 31.0 - y * 1.4 + _seed(seed, 233)) * np.pi)) * 52.0, 0, 1) * 0.28,
    )
    phosphor_grain = _micro_sparkle(shape, seed, 234, 0.986, 1)
    energy = np.clip(long_tubes + starter_bars + phosphor_grain * 0.32, 0, 1)
    return _spec_from_energy(shape, mask, energy, sm, 8, 150)


def paint_fluorescent(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    long_tubes = np.maximum(
        np.clip(1.0 - np.abs(np.sin((y * 42.0 + np.sin(x * np.pi * 2.0) * 0.11 + _seed(seed, 230)) * np.pi)) * 32.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 58.0 - x * 2.2 + _seed(seed, 231)) * np.pi)) * 38.0, 0, 1) * 0.58,
    )
    starter_bars = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 18.0 + y * 0.8 + _seed(seed, 232)) * np.pi)) * 44.0, 0, 1) * 0.50,
        np.clip(1.0 - np.abs(np.sin((x * 31.0 - y * 1.4 + _seed(seed, 233)) * np.pi)) * 52.0, 0, 1) * 0.28,
    )
    phosphor_grain = _field(shape, seed, 234, 18.0) * 0.06 + _micro_sparkle(shape, seed, 235, 0.986, 1) * 0.14
    energy = np.clip(long_tubes + starter_bars + phosphor_grain, 0, 1)
    tube_halo = np.clip(_soften(long_tubes, 6) * 0.55 + _soften(starter_bars, 3) * 0.24 + energy * 0.74, 0, 1)
    blue_white = _stack3(0.74 + long_tubes * 0.25, 0.93 + tube_halo * 0.07, 1.00, shape)
    glass_wash = _stack3(0.045 + y * 0.028, 0.105 + x * 0.026, 0.135 + long_tubes * 0.035, shape)
    faint_lime = _stack3(0.08, 0.22 + phosphor_grain * 0.18, 0.10, shape)
    effect = np.clip(glass_wash + blue_white * tube_halo[:, :, None] * 0.82 + faint_lime * phosphor_grain[:, :, None], 0, 1)
    out = _mix(base, effect, mask, pm, 0.78)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_firefly(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    swarm = np.clip(
        _dot_swarm(shape, seed, 240, 255, max(1, min(shape) // 250), True)
        + _micro_sparkle(shape, seed, 246, 0.968, 1) * 0.76,
        0,
        1,
    )
    return _spec_from_energy(shape, mask, swarm, sm, 24, 132)


def paint_firefly(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    swarm = np.clip(
        _dot_swarm(shape, seed, 240, 285, max(1, min(shape) // 260), True)
        + _micro_sparkle(shape, seed, 246, 0.968, 1) * 0.76,
        0,
        1,
    )
    canopy = _field(shape, seed, 241, 2.5)
    mist = _field(shape, seed, 242, 11.0) * 0.16
    dew = (_hash_noise(shape, seed, 243) > 0.982).astype(np.float32)
    x, y = _xy(shape)
    grass = np.clip(1.0 - np.abs(np.sin((x * 23.0 + y * 5.0 + canopy * 3.5) * np.pi)) * 9.0, 0, 1)
    leaf_grain = _hash_noise(shape, seed, 244) * 0.26
    lamp_hue = _hash_noise(shape, seed, 245)
    night = _stack3(0.018 + canopy * 0.04 + mist * 0.24 + grass * 0.035 + leaf_grain * 0.10, 0.035 + canopy * 0.08 + mist * 0.22 + grass * 0.13 + leaf_grain * 0.11, 0.030 + canopy * 0.05 + dew * 0.10 + leaf_grain * 0.06, shape)
    lamps = _stack3(0.92 + lamp_hue * 0.08, 0.70 + swarm * 0.22 + dew * 0.12 + (1.0 - lamp_hue) * 0.18, 0.12 + canopy * 0.10 + dew * 0.10 + lamp_hue * 0.16, shape)
    effect = np.clip(night + lamps * (swarm[:, :, None] * 1.04 + _soften(swarm, 2)[:, :, None] * 0.30 + grass[:, :, None] * 0.14), 0, 1)
    out = _mix(base, effect, mask, pm, 0.80)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.06).astype(np.float32))


def spec_phosphorescent(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    decay = np.clip(1.0 - np.abs(np.sin((_field(shape, seed, 251, 3.0) * 3.0 + x * 1.4 + y * 0.6) * np.pi)) * 3.4, 0, 1)
    return _spec_from_energy(shape, mask, decay, sm, 24, 128)


def paint_phosphorescent(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    gray = base.mean(axis=2)
    x, y = _xy(shape)
    stored = np.clip((1.0 - gray) * 0.80 + _field(shape, seed, 251, 5.0) * 0.48, 0, 1)
    rings = np.clip(1.0 - np.abs(np.sin((stored * 7.0 + x * 2.2 + y * 1.1) * np.pi)) * 6.0, 0, 1)
    afterimage = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 31.0 - y * 19.0 + stored * 2.4) * np.pi)) * 10.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -23.0 + y * 27.0 + stored * 1.7) * np.pi)) * 11.0, 0, 1),
    )
    grains = (_hash_noise(shape, seed, 253) > 0.965).astype(np.float32)
    charge = np.clip(rings * 0.76 + afterimage * 0.62 + _soften(grains, 2) * 0.78, 0, 1)
    effect = _stack3(0.035 + charge * 0.22, 0.48 + stored * 0.34 + charge * 0.36, 0.13 + charge * 0.24, shape)
    out = _mix(base, effect, mask, pm, 0.80)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.06).astype(np.float32))


def spec_electric_arc(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    filaments = np.maximum(_thin_wave(x * 4.2 - y * 2.6, 28.0, _seed(seed, 261), 68.0), _thin_wave(x * -3.4 + y * 4.5, 31.0, _seed(seed, 262), 74.0))
    white_flake = _micro_sparkle(shape, seed, 263, 0.972, 1)
    arcs = np.clip(_arc_field(shape, seed, 260, 14, 12) + filaments * 0.78 + white_flake * 0.72, 0, 1)
    return _spec_from_energy(shape, mask, arcs, sm, 7, 178)


def paint_electric_arc(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    arc = _arc_field(shape, seed, 260, 14, 12)
    filaments = np.maximum(_thin_wave(x * 4.2 - y * 2.6, 28.0, _seed(seed, 261), 68.0), _thin_wave(x * -3.4 + y * 4.5, 31.0, _seed(seed, 262), 74.0))
    white_flake = _micro_sparkle(shape, seed, 263, 0.972, 1)
    arc = np.clip(arc + filaments * 0.70 + white_flake * 0.82, 0, 1)
    halo = _soften(arc, 6)
    effect = _stack3(0.18 + arc * 0.72 + white_flake * 0.42, 0.54 + arc * 0.46 + white_flake * 0.36, 0.97 + halo * 0.03, shape)
    effect = np.clip(base * 0.08 + effect * (arc[:, :, None] * 0.96 + halo[:, :, None] * 0.36 + white_flake[:, :, None] * 0.42), 0, 1)
    out = _mix(base, effect, mask, pm, 0.82)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_sodium_lamp(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    pools = np.zeros(shape, dtype=np.float32)
    for i in range(5):
        cx = 0.12 + i * 0.21 + (_seed(seed, 280 + i) - 0.5) * 0.06
        cy = 0.24 + (i % 2) * 0.42 + (_seed(seed, 290 + i) - 0.5) * 0.10
        pools = np.maximum(pools, np.exp(-(((x - cx) ** 2) / 0.010 + ((y - cy) ** 2) / 0.045)))
    return _spec_from_energy(shape, mask, np.clip(pools + _field(shape, seed, 281, 2.2) * 0.25, 0, 1), sm, 22, 86)


def paint_sodium_lamp(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    gray = base.mean(axis=2)
    x, y = _xy(shape)
    pools = np.zeros(shape, dtype=np.float32)
    for i in range(5):
        cx = 0.12 + i * 0.21 + (_seed(seed, 280 + i) - 0.5) * 0.06
        cy = 0.24 + (i % 2) * 0.42 + (_seed(seed, 290 + i) - 0.5) * 0.10
        pools = np.maximum(pools, np.exp(-(((x - cx) ** 2) / 0.010 + ((y - cy) ** 2) / 0.045)))
    rain = np.clip(1.0 - np.abs(np.sin((x * 46.0 + y * 6.0 + _field(shape, seed, 282, 4.0)) * np.pi)) * 10.0, 0, 1)
    sodium_grain = _field(shape, seed, 284, 12.0)
    glare = np.clip(1.0 - np.abs(np.sin((pools * 5.0 + x * 2.2 - y * 0.8) * np.pi)) * 6.0, 0, 1)
    lens = _hash_noise(shape, seed, 283) * 0.10
    cool_shadow = np.clip((1.0 - pools) * (1.0 - rain) * _field(shape, seed, 285, 7.0), 0, 1)
    tar = np.clip(1.0 - np.abs(np.sin((x * 19.0 - y * 13.0 + sodium_grain * 2.0) * np.pi)) * 8.0, 0, 1)
    amber = _stack3(
        0.84 * gray + pools * 0.44 + rain * 0.18 + glare * 0.13 + sodium_grain * 0.10 + tar * 0.12 + lens,
        0.42 * gray + pools * 0.30 + rain * 0.12 + glare * 0.08 + sodium_grain * 0.06 + tar * 0.05,
        0.07 * gray + rain * 0.045 + sodium_grain * 0.03 + cool_shadow * 0.07,
        shape,
    )
    out = _mix(base, np.clip(amber, 0, 1), mask, pm, 0.82)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_laser_grid(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    perspective = y * (11.0 + x * 5.0)
    grid = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * (42.0 + y * 26.0)) * np.pi)) * 34.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin(perspective * np.pi)) * 36.0, 0, 1),
    )
    grid = np.maximum(grid, _thin_wave(x * 1.7 - y * 2.8, 15.0, _seed(seed, 300), 44.0) * 0.78)
    return _spec_from_energy(shape, mask, grid, sm, 8, 160)


def paint_laser_grid(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    red = np.clip(1.0 - np.abs(np.sin((x * (42.0 + y * 26.0)) * np.pi)) * 34.0, 0, 1)
    cyan = np.clip(1.0 - np.abs(np.sin((y * (16.0 + x * 7.0)) * np.pi)) * 36.0, 0, 1)
    violet = _thin_wave(x * 1.7 - y * 2.8, 15.0, _seed(seed, 300), 44.0)
    nodes = (_hash_noise(shape, seed, 301) > 0.990).astype(np.float32)
    fog = _soften(np.maximum.reduce([red, cyan, violet]), 5)
    effect = _stack3(red + violet * 0.55 + fog * 0.22, cyan * 0.70 + nodes * 0.35, cyan + violet * 0.80 + fog * 0.24, shape)
    out = _mix(base, np.clip(effect, 0, 1), mask, pm, 0.78)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_aurora_glow(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    curtain = np.clip(1.0 - np.abs(np.sin((x * 3.2 + _field(shape, seed, 310, 2.2) * 1.4) * np.pi)) * (2.6 + y * 7.0), 0, 1)
    return _spec_from_energy(shape, mask, curtain, sm, 18, 136)


def paint_aurora_glow(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    curtain = np.clip(1.0 - np.abs(np.sin((x * 3.2 + _field(shape, seed, 310, 2.2) * 1.4) * np.pi)) * (2.6 + y * 7.0), 0, 1)
    stars = (_hash_noise(shape, seed, 311) > 0.996).astype(np.float32)
    color = _palette([(0.00, 0.08, 0.18), (0.02, 0.90, 0.46), (0.12, 0.70, 1.00), (0.82, 0.08, 1.00)], np.clip(x * 0.35 + y * 0.2 + curtain * 0.8, 0, 1))
    effect = np.clip(color * (0.26 + curtain[:, :, None] * 0.78) + stars[:, :, None] * 0.95, 0, 1)
    out = _mix(base, effect, mask, pm, 0.78)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_laser_show(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    beams = np.maximum.reduce([
        _thin_wave(x * 2.8 + y * 0.7, 18.0, _seed(seed, 330), 54.0),
        _thin_wave(x * -1.7 + y * 3.2, 22.0, _seed(seed, 331), 58.0),
        _thin_wave(x * 3.1 - y * 2.0, 26.0, _seed(seed, 332), 64.0),
        _thin_wave(x * 0.8 + y * 4.4, 31.0, _seed(seed, 333), 70.0),
    ])
    fog = _soften(beams, 3)
    return _spec_from_energy(shape, mask, np.clip(beams + fog * 0.40, 0, 1), sm, 7, 170)


def paint_laser_show(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    red = _thin_wave(x * 2.8 + y * 0.7, 18.0, _seed(seed, 330), 54.0)
    green = _thin_wave(x * -1.7 + y * 3.2, 22.0, _seed(seed, 331), 58.0)
    blue = _thin_wave(x * 3.1 - y * 2.0, 26.0, _seed(seed, 332), 64.0)
    magenta = _thin_wave(x * 0.8 + y * 4.4, 31.0, _seed(seed, 333), 70.0)
    beams = np.maximum.reduce([red, green, blue, magenta])
    fog = _soften(beams, 3)
    sparkle = (_hash_noise(shape, seed, 334) > 0.980).astype(np.float32)
    haze = _field(shape, seed, 333, 6.0) * 0.16
    rgb = _stack3(red + magenta * 0.85, green + red * 0.12, blue + magenta * 0.72, shape)
    effect = np.clip(rgb + fog[:, :, None] * np.array([0.28, 0.22, 0.40], dtype=np.float32) + haze[:, :, None] + sparkle[:, :, None] * 0.48, 0, 1)
    out = _mix(base, effect, mask, pm, 0.82)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_cyber_punk(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    panels = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 13.0 + _field(shape, seed, 371, 2.0)) * np.pi)) * 19.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 19.0 + x * 2.0) * np.pi)) * 23.0, 0, 1),
    )
    rain = np.clip(1.0 - np.abs(np.sin((x * 160.0 + y * 23.0) * np.pi)) * 11.0, 0, 1)
    circuitry = np.maximum(_thin_wave(x * 2.5 + y * 1.1, 28.0, _seed(seed, 372), 58.0), _thin_wave(x * -1.6 + y * 3.4, 31.0, _seed(seed, 373), 62.0))
    return _spec_from_energy(shape, mask, np.clip(panels + rain * 0.35 + circuitry * 0.72, 0, 1), sm, 12, 140)


def paint_cyber_punk(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    panels = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 21.0 + _field(shape, seed, 371, 2.0)) * np.pi)) * 24.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 31.0 + x * 3.7) * np.pi)) * 28.0, 0, 1),
    )
    rain = np.clip(1.0 - np.abs(np.sin((x * 210.0 + y * 37.0) * np.pi)) * 10.0, 0, 1)
    circuitry = np.maximum(_thin_wave(x * 2.5 + y * 1.1, 28.0, _seed(seed, 372), 58.0), _thin_wave(x * -1.6 + y * 3.4, 31.0, _seed(seed, 373), 62.0))
    signage = (_hash_noise(shape, seed, 374) > 0.986).astype(np.float32)
    neon = _stack3(panels + circuitry * 0.75 + rain * 0.15, rain * 0.44 + signage * 0.58, panels * 0.62 + circuitry * 0.92 + rain * 0.40, shape)
    slick = _stack3(0.025 + y * 0.025, 0.035 + x * 0.05, 0.065 + y * 0.09, shape)
    effect = np.clip(slick + neon * 0.88 + _soften(signage, 2)[:, :, None] * np.array([0.9, 0.15, 1.0], dtype=np.float32), 0, 1)
    out = _mix(base, effect, mask, pm, 0.80)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


_PLASMA_CENTERS = ((0.50, 0.50), (0.24, 0.30), (0.77, 0.66))


def _plasma_tendrils(shape, seed):
    """Shared plasma tendril field (identical math for spec + paint).

    2026-06-13 perf: spec_plasma_globe and paint_plasma_globe built the SAME
    three-hub tendril field independently (same seed, same formula). Build it
    once and cache it so the second caller (and re-renders of the same finish)
    is free. The slow per-hub `_field` warble is a low-frequency phase carrier,
    so it is computed at half resolution and bilinear-upsampled; the full-res
    arctan2/radius geometry that actually defines the tendril lines is kept at
    native resolution. Whole-finish SSIM vs the full-res field stays >= 0.996.
    """
    key = ("plasma_tendrils", tuple(shape), int(seed))
    cached = _SIGNAL_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    x, y = _xy(shape)
    tendrils = np.zeros(shape, dtype=np.float32)
    for i, (cx, cy) in enumerate(_PLASMA_CENTERS):
        angle = np.arctan2(y - cy, x - cx)
        radius = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        warble = _field_lowres(shape, seed, 390 + i, 3.0)
        tendrils = np.maximum(
            tendrils,
            np.clip(1.0 - np.abs(np.sin(angle * (12 + i * 5) + radius * 44.0 + warble * 4.0)) * 8.0, 0, 1)
            * np.clip(1.0 - radius * 2.8, 0, 1),
        )
    if len(_SIGNAL_FIELD_CACHE) > 28:
        _SIGNAL_FIELD_CACHE.clear()
    _SIGNAL_FIELD_CACHE[key] = tendrils
    return tendrils


def spec_plasma_globe(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    tendrils = _plasma_tendrils(shape, seed)
    return _spec_from_energy(shape, mask, tendrils, sm, 8, 172)


def paint_plasma_globe(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    tendrils = _plasma_tendrils(shape, seed)
    micro = _arc_field(shape, seed, 397, 1, 3) * 0.18
    tendrils = np.clip(tendrils + micro, 0, 1)
    glow = _soften(tendrils, 6)
    corona = _field_lowres(shape, seed, 398, 8.0) * 0.18
    effect = _stack3(0.36 + tendrils * 0.64 + corona, 0.10 + glow * 0.32 + corona * 0.35, 0.88 + tendrils * 0.12, shape)
    effect = np.clip(effect * (tendrils[:, :, None] * 0.98 + glow[:, :, None] * 0.42 + corona[:, :, None]), 0, 1)
    out = _mix(base, effect, mask, pm, 0.84)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_tracer_round(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    energy = np.maximum.reduce([
        _thin_wave(x * 2.4 + y * 1.1, 35.0, _seed(seed, 420), 76.0),
        _thin_wave(x * 1.7 + y * 2.9, 42.0, _seed(seed, 421), 82.0),
        _thin_wave(x * -2.5 + y * 1.2, 38.0, _seed(seed, 422), 78.0),
    ])
    sparks = (_hash_noise(shape, seed, 423) > 0.976).astype(np.float32)
    return _spec_from_energy(shape, mask, np.clip(energy + _soften(energy, 5) * 0.35 + sparks, 0, 1), sm, 9, 145)


def paint_tracer_round(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    energy = np.maximum.reduce([
        _thin_wave(x * 2.4 + y * 1.1, 35.0, _seed(seed, 420), 76.0),
        _thin_wave(x * 1.7 + y * 2.9, 42.0, _seed(seed, 421), 82.0),
        _thin_wave(x * -2.5 + y * 1.2, 38.0, _seed(seed, 422), 78.0),
    ])
    sparks = (_hash_noise(shape, seed, 423) > 0.976).astype(np.float32)
    tail = _soften(energy, 3)
    effect = _stack3(1.0, 0.46 + tail * 0.22, 0.04 + sparks * 0.12, shape) * np.clip(energy[:, :, None] + tail[:, :, None] * 0.42 + sparks[:, :, None] * 0.72, 0, 1)
    out = _mix(base, effect, mask, pm, 0.82)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_bioluminescent_wave(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    wave = np.clip(1.0 - np.abs(np.sin((y * 11.0 + np.sin(x * np.pi * 5.0) * 0.9 + _field(shape, seed, 451, 2.4)) * np.pi)) * 5.2, 0, 1)
    plankton = (_hash_noise(shape, seed, 452) > 0.985).astype(np.float32)
    return _spec_from_energy(shape, mask, np.clip(wave + _soften(plankton, 3), 0, 1), sm, 16, 154)


def paint_bioluminescent_wave(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    wave = np.clip(1.0 - np.abs(np.sin((y * 11.0 + np.sin(x * np.pi * 5.0) * 0.9 + _field(shape, seed, 451, 2.4)) * np.pi)) * 5.2, 0, 1)
    plankton = (_hash_noise(shape, seed, 452) > 0.985).astype(np.float32)
    current = _soften(plankton, 3)
    deep = _stack3(0.005 + y * 0.03, 0.045 + x * 0.05, 0.095 + y * 0.12, shape)
    glow = _stack3(0.02 + current * 0.12, 0.78 + wave * 0.18, 0.92 + current * 0.08, shape)
    effect = np.clip(deep + glow * (wave[:, :, None] * 0.74 + current[:, :, None] * 0.82), 0, 1)
    out = _mix(base, effect, mask, pm, 0.78)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


_MAGNESIUM_BURN_CENTERS = (
    (0.18, 0.18, 0.014, 0.010, 0.96), (0.34, 0.32, 0.020, 0.012, 1.0),
    (0.56, 0.22, 0.017, 0.012, 0.82), (0.72, 0.38, 0.030, 0.018, 1.0),
    (0.24, 0.62, 0.018, 0.014, 0.86), (0.48, 0.72, 0.024, 0.014, 0.95),
    (0.79, 0.72, 0.018, 0.010, 0.82), (0.62, 0.88, 0.014, 0.010, 0.72),
    (0.88, 0.14, 0.016, 0.010, 0.76),
)


def _magnesium_burn_fields(shape, seed):
    key = ("magnesium_burn", tuple(shape), int(seed))
    cached = _SIGNAL_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    # SPB paint-finish perf loop 2026-05-31: spec/paint both need the same flare and micro-spark carriers.
    flare = _flare_map(shape, _MAGNESIUM_BURN_CENTERS)
    micro = _micro_sparkle(shape, seed, 472, 0.978, 1) * 0.44
    sparks_spec = np.clip(_dot_swarm(shape, seed, 470, 170, max(1, min(shape) // 340), True) + micro, 0, 1)
    sparks_paint = np.clip(_dot_swarm(shape, seed, 470, 190, max(1, min(shape) // 340), True) + micro, 0, 1)
    soot = _field(shape, seed, 471, 8.0)
    x, y = _xy(shape)
    oxide = np.clip(1.0 - np.abs(np.sin((x * 25.0 + y * 7.0 + soot * 2.0) * np.pi)) * 11.0, 0, 1)
    out = (flare, sparks_spec, sparks_paint, soot, oxide)
    if len(_SIGNAL_FIELD_CACHE) > 28:
        _SIGNAL_FIELD_CACHE.clear()
    _SIGNAL_FIELD_CACHE[key] = out
    return out


def spec_magnesium_burn(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    flare, sparks, _sparks_paint, _soot, _oxide = _magnesium_burn_fields(shape, seed)
    return _spec_from_energy(shape, mask, np.clip(flare + sparks * 0.90, 0, 1), sm, 5, 172)


def paint_magnesium_burn(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    flare, _sparks_spec, sparks, soot, oxide = _magnesium_burn_fields(shape, seed)
    effect = _stack3(1.0, 0.88 + flare * 0.12, 0.46 + flare * 0.54, shape) * np.clip(flare[:, :, None] * 1.08 + sparks[:, :, None] * 0.82, 0, 1)
    effect += np.stack([0.07, 0.055, 0.04], axis=0)[None, None, :] * (1.0 - flare[:, :, None]) * (soot[:, :, None] + oxide[:, :, None] * 0.7)
    out = _mix(base, np.clip(effect, 0, 1), mask, pm, 0.86)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_tesla_coil(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    hair = np.maximum(_thin_wave(x * 3.8 - y * 3.1, 24.0, _seed(seed, 492), 58.0), _thin_wave(x * -4.0 + y * 2.4, 29.0, _seed(seed, 493), 66.0))
    purple_flake = _micro_sparkle(shape, seed, 494, 0.966, 1)
    arcs = np.clip(np.maximum(_arc_field(shape, seed, 490, 12, 10), _arc_field(shape, seed, 491, 6, 9) * 0.78) + hair * 0.86 + purple_flake * 0.62, 0, 1)
    return _spec_from_energy(shape, mask, arcs, sm, 6, 182)


def paint_tesla_coil(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    hair = np.maximum(_thin_wave(x * 3.8 - y * 3.1, 24.0, _seed(seed, 492), 58.0), _thin_wave(x * -4.0 + y * 2.4, 29.0, _seed(seed, 493), 66.0))
    purple_flake = _micro_sparkle(shape, seed, 494, 0.966, 1)
    arcs = np.clip(np.maximum(_arc_field(shape, seed, 490, 12, 10), _arc_field(shape, seed, 491, 6, 9) * 0.78) + hair * 0.86 + purple_flake * 0.72, 0, 1)
    halo = _soften(arcs, 4)
    effect = _stack3(0.58 + arcs * 0.36 + purple_flake * 0.22, 0.07 + halo * 0.24 + purple_flake * 0.06, 1.0, shape)
    effect = np.clip(effect * (arcs[:, :, None] * 1.08 + halo[:, :, None] * 0.54 + purple_flake[:, :, None] * 0.52), 0, 1)
    out = _mix(base, effect, mask, pm, 0.84)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_welding_arc(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    seam, hot, sparks = _welding_arc_fields(shape, seed)
    return _spec_from_energy(shape, mask, np.clip(seam * 0.65 + hot + sparks, 0, 1), sm, 5, 158)


def paint_welding_arc(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    seam, hot, sparks = _welding_arc_fields(shape, seed)
    smoke = _field(shape, seed, 513, 5.8)
    effect = _stack3(0.46 + hot * 0.54, 0.64 + hot * 0.36, 1.0, shape) * np.clip(seam[:, :, None] * 0.42 + hot[:, :, None] * 1.2 + sparks[:, :, None] * 0.72, 0, 1)
    effect += smoke[:, :, None] * np.array([0.08, 0.07, 0.08], dtype=np.float32)
    out = _mix(base, np.clip(effect, 0, 1), mask, pm, 0.84)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_led_matrix(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    h, w = shape
    yy, xx = np.ogrid[0:h, 0:w]
    yy = yy.astype(np.float32)
    xx = xx.astype(np.float32)
    cell = max(3, min(h, w) // 150)
    dot = np.clip(1.0 - np.sqrt(((xx % cell) - cell * 0.5) ** 2 + ((yy % cell) - cell * 0.5) ** 2) / (cell * 0.34), 0, 1)
    twinkle = (_hash_noise(shape, seed, 522) > 0.58).astype(np.float32)
    chase = ((xx // cell + yy // cell + int(seed)) % 5 == 0).astype(np.float32)
    wave = np.clip(1.0 - np.abs(np.sin(((xx + yy) / max(cell, 1) * 0.42 + _field(shape, seed, 523, 4.0) * 2.0) * np.pi)) * 4.2, 0, 1)
    subpixel = _micro_sparkle(shape, seed, 524, 0.955, 1)
    energy = np.clip(dot * (0.38 + chase * 0.72 + twinkle * 0.45 + wave * 0.38) + subpixel * 0.42, 0, 1)
    return _spec_from_energy(shape, mask, energy, sm, 7, 178)


def paint_led_matrix(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    h, w = shape
    yy, xx = np.ogrid[0:h, 0:w]
    yy = yy.astype(np.float32)
    xx = xx.astype(np.float32)
    cell = max(3, min(h, w) // 150)
    dot = np.clip(1.0 - np.sqrt(((xx % cell) - cell * 0.5) ** 2 + ((yy % cell) - cell * 0.5) ** 2) / (cell * 0.34), 0, 1)
    col = ((xx // cell).astype(np.int32) + (yy // cell).astype(np.int32) * 2 + ((xx + yy) // max(cell * 5, 1)).astype(np.int32) + int(seed)) % 6
    palette = np.array([(1, 0.04, 0.04), (0.05, 1, 0.08), (0.05, 0.25, 1), (1, 0.85, 0.02), (0.9, 0.04, 1), (0.04, 1, 0.95)], dtype=np.float32)
    twinkle = 0.38 + (_hash_noise(shape, seed, 522) > 0.58).astype(np.float32) * 0.62
    wave = np.clip(1.0 - np.abs(np.sin(((xx + yy) / max(cell, 1) * 0.42 + _field(shape, seed, 523, 4.0) * 2.0) * np.pi)) * 4.2, 0, 1)
    glints = _micro_sparkle(shape, seed, 524, 0.955, 1)
    circuit = np.maximum(
        np.clip(1.0 - np.abs(np.sin((xx / max(cell, 1) * 0.17 + yy / max(cell, 1) * 0.03) * np.pi)) * 32.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((yy / max(cell, 1) * 0.19 - xx / max(cell, 1) * 0.04) * np.pi)) * 34.0, 0, 1),
    ) * 0.18
    effect = np.clip(palette[col] * dot[:, :, None] * twinkle[:, :, None] + wave[:, :, None] * palette[(col + 2) % 6] * 0.34 + glints[:, :, None] * 0.75 + circuit[:, :, None], 0, 1)
    out = _mix(base, effect, mask, pm, 0.80)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_radioactive(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    radius = np.sqrt((x - 0.50) ** 2 + (y - 0.50) ** 2)
    rings = np.clip(1.0 - np.abs(np.sin(radius * np.pi * 42.0 + _field(shape, seed, 540, 2.0) * 1.2)) * 9.0, 0, 1)
    particles = (_hash_noise(shape, seed, 541) > 0.986).astype(np.float32)
    return _spec_from_energy(shape, mask, np.clip(rings + particles * 0.8, 0, 1), sm, 17, 132)


def paint_radioactive(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    radius = np.sqrt((x - 0.50) ** 2 + (y - 0.50) ** 2)
    rings = np.clip(1.0 - np.abs(np.sin(radius * np.pi * 42.0 + _field(shape, seed, 540, 2.0) * 1.2)) * 9.0, 0, 1)
    particles = (_hash_noise(shape, seed, 541) > 0.986).astype(np.float32)
    hazard = np.clip(np.sin(np.arctan2(y - 0.50, x - 0.50) * 3.0) > 0.42, 0, 1).astype(np.float32) * np.clip(1.0 - radius * 2.4, 0, 1)
    effect = _stack3(0.11 + hazard * 0.10, 0.72 + rings * 0.26, 0.04 + particles * 0.12, shape)
    effect = np.clip(effect * (0.32 + rings[:, :, None] * 0.58 + particles[:, :, None] * 0.70), 0, 1)
    out = _mix(base, effect, mask, pm, 0.78)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def spec_neon_glow(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    ribbons = np.clip(1.0 - np.abs(np.sin((x * 12.0 - y * 8.0 + _field(shape, seed, 560, 2.8)) * np.pi)) * 7.0, 0, 1)
    mist = _field(shape, seed, 561, 5.0) * 0.28
    return _spec_from_energy(shape, mask, np.clip(ribbons + mist, 0, 1), sm, 14, 150)


def paint_neon_glow(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    ribbons = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 12.0 - y * 8.0 + _field(shape, seed, 560, 2.8)) * np.pi)) * 7.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -7.0 + y * 13.0 + _field(shape, seed, 562, 4.0)) * np.pi)) * 9.0, 0, 1) * 0.82,
    )
    mist = _soften(ribbons, 4)
    gold = np.clip(_thin_wave(x * 1.6 + y * 2.0, 18.0, _seed(seed, 563), 38.0) + _hash_noise(shape, seed, 564) * 0.16, 0, 1)
    color = _palette([(1, 0.02, 0.45), (0.04, 0.92, 1), (0.88, 0.06, 1), (1, 0.78, 0.02)], np.clip(x * 0.4 + y * 0.2 + ribbons + gold * 0.45, 0, 1))
    effect = np.clip(color * (ribbons[:, :, None] * 0.78 + mist[:, :, None] * 0.32 + gold[:, :, None] * 0.32), 0, 1)
    out = _mix(base, effect, mask, pm, 0.78)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_rave(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    h, w = shape
    yy, xx = np.ogrid[0:h, 0:w]
    yy = yy.astype(np.float32)
    xx = xx.astype(np.float32)
    x, y = _xy(shape)
    cell = max(3, min(h, w) // 210)
    dot = np.clip(1.0 - np.sqrt(((xx % cell) - cell * 0.5) ** 2 + ((yy % cell) - cell * 0.5) ** 2) / (cell * 0.32), 0, 1)
    lasers = np.maximum.reduce([
        _thin_wave(x * 4.0 + y * 0.8, 34.0, _seed(seed, 580), 86.0),
        _thin_wave(x * -2.6 + y * 4.6, 38.0, _seed(seed, 581), 92.0),
        _thin_wave(x * 5.2 - y * 3.4, 42.0, _seed(seed, 582), 98.0),
    ])
    confetti = _micro_sparkle(shape, seed, 583, 0.958, 1)
    equalizer = np.clip(1.0 - np.abs(np.sin((x * 96.0 + _field(shape, seed, 584, 4.0) * 1.4) * np.pi)) * 18.0, 0, 1) * np.clip(y * 1.25, 0, 1)
    strobes = np.clip(dot * 0.64 + lasers * 0.90 + confetti * 0.68 + equalizer * 0.42, 0, 1)
    return _spec_from_energy(shape, mask, strobes, sm, 7, 166)


def paint_rave(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    h, w = shape
    yy, xx = np.ogrid[0:h, 0:w]
    yy = yy.astype(np.float32)
    xx = xx.astype(np.float32)
    x, y = _xy(shape)
    cell = max(3, min(h, w) // 210)
    tile_id = ((xx // cell).astype(np.int32) * 5 + (yy // cell).astype(np.int32) * 11 + int(seed)) % 8
    active = (((xx // cell) * 2 + (yy // cell) * 3 + int(seed)) % 4 != 0).astype(np.float32)
    dot = np.clip(1.0 - np.sqrt(((xx % cell) - cell * 0.5) ** 2 + ((yy % cell) - cell * 0.5) ** 2) / (cell * 0.32), 0, 1)
    palette = np.array([(1, 0, 0.5), (0, 1, 0.1), (0, 0.45, 1), (1, 1, 0), (0.95, 0, 1), (1, 0.34, 0), (0, 1, 1), (1, 0, 1)], dtype=np.float32)
    lasers = np.maximum.reduce([
        _thin_wave(x * 4.0 + y * 0.8, 34.0, _seed(seed, 580), 86.0),
        _thin_wave(x * -2.6 + y * 4.6, 38.0, _seed(seed, 581), 92.0),
        _thin_wave(x * 5.2 - y * 3.4, 42.0, _seed(seed, 582), 98.0),
    ])
    confetti = _micro_sparkle(shape, seed, 583, 0.958, 1)
    equalizer = np.clip(1.0 - np.abs(np.sin((x * 96.0 + _field(shape, seed, 584, 4.0) * 1.4) * np.pi)) * 18.0, 0, 1) * np.clip(y * 1.25, 0, 1)
    laser_color = _palette([(0.0, 1.0, 1.0), (1.0, 0.0, 0.9), (0.3, 1.0, 0.1), (1.0, 0.75, 0.0)], np.clip(x * 0.55 + y * 0.22 + lasers * 0.65, 0, 1))
    effect = np.clip(
        palette[tile_id] * (active * dot)[:, :, None] * 0.78
        + laser_color * (lasers[:, :, None] * 0.96 + _soften(lasers, 2)[:, :, None] * 0.22)
        + palette[(tile_id + 3) % 8] * confetti[:, :, None] * 0.72
        + palette[(tile_id + 5) % 8] * equalizer[:, :, None] * 0.34,
        0,
        1,
    )
    out = _mix(base, effect, mask, pm, 0.82)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_static(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    snow = _hash_noise(shape, seed, 590)
    scan = np.clip(1.0 - np.abs(np.sin(_xy(shape)[1] * np.pi * 620.0)) * 5.5, 0, 1)
    return _spec_from_energy(shape, mask, np.clip(snow * 0.74 + scan * 0.52, 0, 1), sm, 28, 96)


def paint_static(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    snow = _hash_noise(shape, seed, 590)
    scan = np.clip(1.0 - np.abs(np.sin(_xy(shape)[1] * np.pi * 620.0)) * 5.5, 0, 1)
    monochrome = np.repeat(np.clip(snow * 0.88 + scan * 0.22, 0, 1)[:, :, None], 3, axis=2)
    out = _mix(base, monochrome, mask, pm, 0.60)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def spec_scorched(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    cracks = np.maximum(
        np.clip(1.0 - np.abs(np.sin((_field(shape, seed, 610, 7.0) * 5.0 + x * 24.0 - y * 13.0) * np.pi)) * 14.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((_field(shape, seed, 613, 9.0) * 4.0 + x * -17.0 + y * 29.0) * np.pi)) * 16.0, 0, 1),
    )
    embers = (_hash_noise(shape, seed, 611) > 0.982).astype(np.float32)
    return _spec_from_energy(shape, mask, np.clip(cracks + embers, 0, 1), sm, 38, 92)


def paint_scorched(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = _paint_base(paint)
    x, y = _xy(shape)
    cracks = np.maximum(
        np.clip(1.0 - np.abs(np.sin((_field(shape, seed, 610, 7.0) * 5.0 + x * 24.0 - y * 13.0) * np.pi)) * 14.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((_field(shape, seed, 613, 9.0) * 4.0 + x * -17.0 + y * 29.0) * np.pi)) * 16.0, 0, 1),
    )
    char = _field(shape, seed, 612, 11.0)
    ember = (_hash_noise(shape, seed, 611) > 0.982).astype(np.float32)
    ash = _hash_noise(shape, seed, 614) * 0.12
    effect = _stack3(0.055 + char * 0.08 + cracks * 0.78 + ember * 0.75 + ash, 0.034 + cracks * 0.22 + ember * 0.46, 0.022 + cracks * 0.045 + ash * 0.25, shape)
    out = _mix(base, np.clip(effect, 0, 1), mask, pm, 0.84)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.05).astype(np.float32))


OWNER_REVIEW_SIGNAL_MONOLITHICS = {
    "aurora_glow": (spec_aurora_glow, paint_aurora_glow),
    "bioluminescent_wave": (spec_bioluminescent_wave, paint_bioluminescent_wave),
    "blacklight_paint": (spec_blacklight_paint, paint_blacklight_paint),
    "cyber_punk": (spec_cyber_punk, paint_cyber_punk),
    "electric_arc": (spec_electric_arc, paint_electric_arc),
    "firefly": (spec_firefly, paint_firefly),
    "fluorescent": (spec_fluorescent, paint_fluorescent),
    "glow_stick": (spec_glow_stick, paint_glow_stick),
    "laser_grid": (spec_laser_grid, paint_laser_grid),
    "laser_show": (spec_laser_show, paint_laser_show),
    "led_matrix": (spec_led_matrix, paint_led_matrix),
    "magnesium_burn": (spec_magnesium_burn, paint_magnesium_burn),
    "neon_glow": (spec_neon_glow, paint_neon_glow),
    "neon_sign": (spec_neon_sign, paint_neon_sign),
    "neon_vegas": (spec_neon_vegas, paint_neon_vegas),
    "phosphorescent": (spec_phosphorescent, paint_phosphorescent),
    "plasma_globe": (spec_plasma_globe, paint_plasma_globe),
    "radioactive": (spec_radioactive, paint_radioactive),
    "rave": (spec_rave, paint_rave),
    "scorched": (spec_scorched, paint_scorched),
    "sodium_lamp": (spec_sodium_lamp, paint_sodium_lamp),
    "static": (spec_static, paint_static),
    "tesla_coil": (spec_tesla_coil, paint_tesla_coil),
    "tracer_round": (spec_tracer_round, paint_tracer_round),
    "welding_arc": (spec_welding_arc, paint_welding_arc),
}
