"""Owner-reviewed monolithic rebuilds for SPB post-alpha hardening.

These are semantic replacements for finishes the owner marked as visibly
broken in the SPB-23 v8 review package. Shared helpers here only provide math
primitives; each finish has a distinct paint/spec model.
"""

from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np


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


def _field(shape, seed, salt=0, scale=1.0):
    x, y = _xy(shape)
    a = _seed(seed, salt) * np.pi * 2.0
    b = _seed(seed, salt + 17) * np.pi * 2.0
    c = _seed(seed, salt + 31) * np.pi * 2.0
    f = (
        np.sin((x * (7.0 + scale) + y * (3.5 + scale * 0.7)) * np.pi + a) * 0.38
        + np.sin((x * (19.0 + scale * 2.0) - y * (13.0 + scale)) * np.pi + b) * 0.28
        + np.sin((x * (41.0 + scale * 3.0) + y * (37.0 + scale * 2.0)) * np.pi + c) * 0.18
        + np.sin((x * (83.0 + scale * 4.0) - y * (71.0 + scale * 3.0)) * np.pi + a + c) * 0.10
    )
    return ((f + 0.94) / 1.88).astype(np.float32)


def _hash_noise(shape, seed, salt=0):
    x, y = _xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + _seed(seed, salt) * 91.7) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _soften(a, passes=2):
    out = np.asarray(a, dtype=np.float32)
    for _ in range(max(0, int(passes))):
        out = (
            out
            + np.roll(out, 1, 0)
            + np.roll(out, -1, 0)
            + np.roll(out, 1, 1)
            + np.roll(out, -1, 1)
        ) * 0.2
    return out.astype(np.float32)


def _full2(v, shape):
    return np.broadcast_to(np.asarray(v, dtype=np.float32), shape).astype(np.float32)


def _fit2(a, shape):
    arr = np.asarray(a, dtype=np.float32)
    if arr.shape == tuple(shape):
        return arr
    yy = np.linspace(0, arr.shape[0] - 1, shape[0]).astype(np.int32)
    xx = np.linspace(0, arr.shape[1] - 1, shape[1]).astype(np.int32)
    return arr[yy[:, None], xx[None, :]].astype(np.float32)


def _resize_linear(a, shape):
    arr = np.asarray(a, dtype=np.float32)
    if arr.shape == tuple(shape):
        return arr
    h, w = shape
    return cv2.resize(arr, (int(w), int(h)), interpolation=cv2.INTER_LINEAR).astype(np.float32)


def _bounded_shape(shape, limit=1024):
    h, w = shape
    scale = min(1.0, float(limit) / float(max(h, w)))
    if scale >= 1.0:
        return shape
    return max(128, int(round(h * scale))), max(128, int(round(w * scale)))


def _stack_rgb(a, b, c, shape):
    return np.stack([_full2(a, shape), _full2(b, shape), _full2(c, shape)], axis=2)


def _rgba(shape, mask):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 3] = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    return spec


def _apply_bb(out, mask, bb, amount=0.12):
    if bb is None:
        return out
    bb_arr = bb[:, :, np.newaxis] if getattr(bb, "ndim", 0) == 2 else bb
    return np.clip(out + bb_arr * amount * mask[:, :, np.newaxis], 0, 1)


def _thermal_palette(t):
    stops = np.array(
        [
            [0.015, 0.025, 0.090],
            [0.000, 0.115, 0.420],
            [0.000, 0.580, 0.760],
            [0.980, 0.780, 0.050],
            [1.000, 0.230, 0.020],
            [1.000, 0.930, 0.760],
        ],
        dtype=np.float32,
    )
    n = len(stops) - 1
    pos = np.clip(t, 0, 1) * n
    idx = np.clip(np.floor(pos).astype(np.int32), 0, n - 1)
    frac = (pos - idx)[:, :, np.newaxis]
    return stops[idx] * (1.0 - frac) + stops[idx + 1] * frac


def spec_owner_cel_shade(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    tone = np.floor(np.clip((x * 0.82 + y * 1.14 + _field(shape, seed, 10, 1.5) * 0.28), 0, 1) * 5.0) / 4.0
    edge = np.clip(1.0 - np.abs(np.sin((tone * 5.0 + x * 0.08) * np.pi)) * 18.0, 0, 1)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((72 + tone * 138 + edge * 42) * sm * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((116 - tone * 92 + edge * 18) * mask + 80 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((24 + edge * 18 + tone * 20) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_cel_shade(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    luma = base.mean(axis=2)
    ramp = np.clip(luma * 0.35 + x * 0.34 + y * 0.27 + _field(shape, seed, 12, 1.0) * 0.22, 0, 1)
    band = np.floor(ramp * 5.0) / 4.0
    ink = np.clip(1.0 - np.abs(np.sin((ramp * 5.0) * np.pi)) * 15.0, 0, 1)
    cel = np.stack([0.08 + band * 0.68, 0.16 + band * 0.78, 0.12 + band * 0.55], axis=2)
    out = base * (1.0 - 0.72 * pm * mask[:, :, None]) + cel * (0.72 * pm * mask[:, :, None])
    out = np.clip(out - ink[:, :, None] * 0.42 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.06).astype(np.float32))


def _cursed_cracks(shape, seed):
    x, y = _xy(shape)
    warped = _field(shape, seed, 80, 2.3)
    vein_a = np.abs(np.sin((x * 22.0 + y * 9.0 + warped * 3.2) * np.pi))
    vein_b = np.abs(np.sin((x * -11.0 + y * 26.0 + warped * 4.4) * np.pi))
    cracks = np.clip(1.0 - np.minimum(vein_a, vein_b) * 18.0, 0, 1)
    glyph = np.clip(1.0 - np.abs(np.sin((np.sqrt((x - 0.48) ** 2 + (y - 0.52) ** 2) * 34.0 + warped) * np.pi)) * 14.0, 0, 1)
    return np.clip(cracks + glyph * 0.55, 0, 1), warped


def spec_owner_cursed(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    cracks, rot = _cursed_cracks(shape, seed)
    pocks = (_hash_noise(shape, seed, 89) > 0.992).astype(np.float32)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((18 + cracks * 148 + pocks * 90 + rot * 20) * sm * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((196 - cracks * 154 + pocks * 32 + rot * 26) * mask, 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((34 + cracks * 120 + pocks * 45) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_cursed(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    cracks, rot = _cursed_cracks(shape, seed)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    decay = np.stack([0.055 + rot * 0.10, 0.045 + rot * 0.085, 0.075 + rot * 0.10], axis=2)
    poison = np.stack([0.13 + cracks * 0.18, 0.72 + cracks * 0.26, 0.10 + cracks * 0.10], axis=2)
    out = base * (1.0 - 0.66 * pm * mask[:, :, None]) + decay * (0.66 * pm * mask[:, :, None])
    out = np.clip(out + poison * cracks[:, :, None] * 0.55 * pm * mask[:, :, None], 0, 1)
    out = np.clip(out - (1.0 - cracks)[:, :, None] * 0.08 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.08).astype(np.float32))


def _datamosh_blocks(shape, seed):
    h, w = shape
    rng = np.random.RandomState(int(seed) + 4301)
    block = np.zeros(shape, dtype=np.float32)
    shift = np.zeros(shape, dtype=np.float32)
    for _ in range(max(24, h // 10)):
        y0 = rng.randint(0, max(1, h - 2))
        bh = rng.randint(max(1, h // 170), max(3, h // 42))
        x0 = rng.randint(0, max(1, w - 2))
        bw = rng.randint(max(6, w // 12), max(8, w // 2))
        y1 = min(h, y0 + bh)
        x1 = min(w, x0 + bw)
        amp = rng.uniform(0.35, 1.0)
        block[y0:y1, x0:x1] = np.maximum(block[y0:y1, x0:x1], amp)
        shift[y0:y1, :] = rng.uniform(-1.0, 1.0)
    return block, shift


def spec_owner_datamosh(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    block, shift = _datamosh_blocks(shape, seed)
    scan = (np.sin(_xy(shape)[1] * np.pi * 420.0) * 0.5 + 0.5).astype(np.float32)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((36 + block * 144 + scan * 34) * sm * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((120 - block * 72 + np.abs(shift) * 82 + scan * 12) * mask, 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((20 + block * 155 + scan * 28) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_datamosh(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    h, w = shape
    base = paint[:, :, :3].astype(np.float32, copy=True)
    block, shift = _datamosh_blocks(shape, seed)
    zone_block = block * mask
    out = base.copy()
    max_shift = max(2, w // 22)
    for y in range(h):
        dx = int(shift[y, 0] * max_shift)
        if dx:
            out[y, :, 0] = np.roll(base[y, :, 0], dx)
            out[y, :, 1] = np.roll(base[y, :, 1], -dx // 2)
            out[y, :, 2] = np.roll(base[y, :, 2], dx // 3)
    noise = _hash_noise(shape, seed, 44)
    corrupt = np.stack([block, np.maximum(block * 0.35, noise * 0.32), np.maximum(block * 0.9, 1.0 - noise)], axis=2)
    out = base * (1.0 - mask[:, :, None]) + out * mask[:, :, None]
    out = np.clip(out * (1.0 - zone_block[:, :, None] * 0.72 * pm) + corrupt * zone_block[:, :, None] * 0.72 * pm, 0, 1)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.05).astype(np.float32))


def _glitch_map(shape, seed):
    x, y = _xy(shape)
    fine_scan = np.clip(1.0 - np.abs(np.sin(y * np.pi * 720.0)) * 11.0, 0, 1)
    fine_scan = np.broadcast_to(fine_scan, shape).astype(np.float32)
    micro = (_hash_noise(shape, seed, 502) > 0.982).astype(np.float32)
    slices = np.clip(1.0 - np.abs(np.sin((y * 92.0 + _field(shape, seed, 503, 1.0) * 0.9) * np.pi)) * 10.0, 0, 1)
    rgb_fringe = np.clip(1.0 - np.abs(np.sin((x * 170.0 + y * 11.0) * np.pi)) * 8.0, 0, 1)
    return fine_scan, micro, slices, rgb_fringe


def spec_owner_glitch(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    fine_scan, micro, slices, fringe = _glitch_map(shape, seed)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((42 + fine_scan * 58 + slices * 122 + micro * 120) * sm * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((78 + (1 - fine_scan) * 56 - slices * 32 + fringe * 26) * mask, 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((18 + fine_scan * 24 + slices * 86 + micro * 120) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_glitch(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    h, w = shape
    fine_scan, micro, slices, fringe = _glitch_map(shape, seed)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    out = base.copy()
    px = max(1, w // 190)
    out[:, :, 0] = np.roll(base[:, :, 0], px, axis=1)
    out[:, :, 1] = base[:, :, 1]
    out[:, :, 2] = np.roll(base[:, :, 2], -px, axis=1)
    out = base * (1.0 - mask[:, :, None]) + out * mask[:, :, None]
    signal = np.stack([fringe + slices * 0.7, fine_scan * 0.42, fine_scan + slices * 0.45], axis=2)
    out = np.clip(out + signal * 0.30 * pm * mask[:, :, None] + micro[:, :, None] * 0.35 * pm * mask[:, :, None], 0, 1)
    out = np.clip(out - fine_scan[:, :, None] * 0.12 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.03).astype(np.float32))


def _infrared_heat(shape, seed):
    x, y = _xy(shape)
    blobs = np.zeros(shape, dtype=np.float32)
    centers = [
        (0.18 + _seed(seed, 1) * 0.18, 0.22 + _seed(seed, 2) * 0.18, 0.18),
        (0.62 + _seed(seed, 3) * 0.22, 0.34 + _seed(seed, 4) * 0.28, 0.23),
        (0.38 + _seed(seed, 5) * 0.30, 0.66 + _seed(seed, 6) * 0.18, 0.20),
    ]
    for cx, cy, radius in centers:
        d = ((x - cx) ** 2 + (y - cy) ** 2) / max(radius * radius, 1e-4)
        blobs += np.exp(-d).astype(np.float32)
    detail = _field(shape, seed, 601, 2.2) * 0.32 + _field(shape, seed, 602, 6.0) * 0.12
    return np.clip(blobs / max(blobs.max(), 1e-5) * 0.82 + detail, 0, 1)


def spec_owner_infrared(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    heat = _infrared_heat(shape, seed)
    contour = np.clip(1.0 - np.abs(np.sin(heat * np.pi * 12.0)) * 10.0, 0, 1)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((34 + heat * 176 + contour * 28) * sm * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((178 - heat * 136 + contour * 38) * mask, 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((20 + heat * 78 + contour * 54) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_infrared(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    heat = _infrared_heat(shape, seed)
    contour = np.clip(1.0 - np.abs(np.sin(heat * np.pi * 12.0)) * 13.0, 0, 1)
    thermal = _thermal_palette(np.clip(heat + contour * 0.05, 0, 1))
    base = paint[:, :, :3].astype(np.float32, copy=True)
    blend = 0.86 * pm * mask[:, :, None]
    out = base * (1.0 - blend) + thermal * blend
    out = np.clip(out + contour[:, :, None] * np.array([0.20, 0.10, 0.02], dtype=np.float32) * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_apply_bb(out, mask, bb, 0.04).astype(np.float32))


def _mix_base(paint, mask, effect, pm, amount):
    base = paint[:, :, :3].astype(np.float32, copy=True)
    blend = np.clip(float(amount) * float(pm), 0.0, 1.0) * mask[:, :, None]
    return base * (1.0 - blend) + effect.astype(np.float32) * blend


def _spec_from_fields(shape, mask, metallic, roughness, clearcoat, sm):
    x, y = _xy(shape)
    metallic = np.asarray(metallic, dtype=np.float32)
    roughness = np.asarray(roughness, dtype=np.float32)
    clearcoat = np.asarray(clearcoat, dtype=np.float32)
    detail = np.abs(metallic - _soften(metallic, 2)) + np.abs(clearcoat - _soften(clearcoat, 2))
    peak = float(np.max(detail)) if detail.size else 0.0
    if peak > 1e-5:
        detail = detail / peak
    pin = np.clip(
        1.0
        - np.abs(np.sin((x * 173.0 - y * 119.0 + detail * 3.1) * np.pi)) * 18.0,
        0,
        1,
    )
    m = metallic + detail * 36.0 + pin * 22.0
    # Effects & Vision was reading too green/flat in review thumbnails. Keep
    # roughness expressive, but let high-detail strokes become glossier.
    r = 40.0 + (roughness - 86.0) * 0.48 - detail * 38.0 + (1.0 - detail) * 8.0
    cc = clearcoat + detail * 64.0 + pin * 46.0
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip(m * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(r * mask + 80 * (1.0 - mask), 12, 210).astype(np.uint8)
    spec[:, :, 2] = np.clip(cc * mask, 16, 255).astype(np.uint8)
    return spec


def _ev67_blood_oath(shape, seed):
    work_shape = _bounded_shape(shape, 1280)
    if work_shape != tuple(shape):
        detail, seal, runes, stain = _ev67_blood_oath(work_shape, seed)
        detail = _fit2(detail, shape)
        seal = _fit2(seal, shape)
        runes = _fit2(runes, shape)
        stain = _fit2(stain, shape)
        fibers = _micro_lines(shape, seed, 6101, 260.0, 97.0)
        scratches = _micro_lines(shape, seed, 6102, -155.0, 231.0)
        detail = np.clip(detail + fibers * 0.18 + scratches * 0.12, 0, 1)
        return detail.astype(np.float32), seal.astype(np.float32), runes.astype(np.float32), stain.astype(np.float32)
    x, y = _xy(shape)
    stain = _field(shape, seed, 6100, 18.0)
    fibers = _micro_lines(shape, seed, 6101, 260.0, 97.0)
    scratches = _micro_lines(shape, seed, 6102, -155.0, 231.0)
    seal = np.zeros(shape, dtype=np.float32)
    runes = np.zeros(shape, dtype=np.float32)
    for i, (cx, cy, rad, power) in enumerate(
        ((0.22, 0.30, 0.16, 0.92), (0.66, 0.46, 0.21, 0.78), (0.42, 0.76, 0.13, 0.70))
    ):
        dx = x - cx
        dy = y - cy
        dist = np.sqrt(dx * dx + dy * dy)
        angle = np.arctan2(dy, dx)
        ring = np.clip(1.0 - np.abs(dist - rad) / 0.0055, 0, 1)
        inner = np.clip(1.0 - np.abs(dist - rad * 0.58) / 0.0045, 0, 1)
        spokes = np.clip(1.0 - np.abs(np.sin((angle * (5 + i * 2) + stain * 0.45) * 0.5)) * 17.0, 0, 1)
        tick = np.clip(1.0 - np.abs(dist - rad * (0.76 + 0.06 * np.sin(angle * 11.0))) / 0.0038, 0, 1)
        seal = np.maximum(seal, (ring + inner * 0.55 + spokes * (dist < rad) * 0.42 + tick * 0.38) * power)
        rune_band = np.clip(1.0 - np.abs(dist - rad * 1.24) / 0.006, 0, 1)
        rune_cut = (np.sin(angle * (24 + i * 7) + seed * 0.011) > 0.62).astype(np.float32)
        runes = np.maximum(runes, rune_band * rune_cut * power)
    clots = (_hash_noise(shape, seed, 6103) > 0.972).astype(np.float32)
    vein = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 79.0 + y * 23.0 + stain * 3.2) * np.pi)) * 29.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -31.0 + y * 103.0 + stain * 2.8) * np.pi)) * 31.0, 0, 1),
    )
    detail = np.clip(seal * 0.72 + runes * 0.62 + vein * 0.44 + fibers * 0.24 + scratches * 0.18 + clots * 0.30, 0, 1)
    return detail.astype(np.float32), seal.astype(np.float32), runes.astype(np.float32), stain.astype(np.float32)


def spec_owner_blood_oath_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, seal, runes, stain = _ev67_blood_oath(shape, seed)
    wet = np.clip(detail * 0.72 + seal * 0.40 + runes * 0.32, 0, 1)
    return _spec_from_fields(
        shape,
        mask,
        28 + wet * 184 + stain * 22,
        148 - wet * 104 + stain * 28,
        24 + wet * 168 + seal * 44,
        sm,
    )


def paint_owner_blood_oath_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, seal, runes, stain = _ev67_blood_oath(shape, seed)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    dried = _stack_rgb(0.090 + stain * 0.075, 0.012 + stain * 0.016, 0.018 + stain * 0.022, shape)
    crimson = _stack_rgb(0.70, 0.015, 0.040, shape) * detail[:, :, None] * 0.54
    fresh = _stack_rgb(1.00, 0.055, 0.070, shape) * np.clip(seal + runes, 0, 1)[:, :, None] * 0.34
    umber = _stack_rgb(0.20, 0.055, 0.018, shape) * (1.0 - detail)[:, :, None] * 0.18
    effect = np.clip(dried + crimson + fresh + umber, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(base, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_blood_oath_v4(shape, seed):
    work_shape = _bounded_shape(shape, 512)
    if work_shape != tuple(shape):
        detail, seal, runes, stain, wax_lip, hidden_sigils, dried_pores, ember = _ev67_blood_oath_v4(work_shape, seed)
        native_pores = (_rand_noise(shape, seed, 6140) > 0.935).astype(np.float32)
        native_ember = (_rand_noise(shape, seed, 6141) > 0.985).astype(np.float32)
        return (
            np.clip(_fit2(detail, shape) + native_pores * 0.24 + native_ember * 0.18, 0, 1),
            _fit2(seal, shape),
            _fit2(runes, shape),
            _fit2(stain, shape),
            _fit2(wax_lip, shape),
            _fit2(hidden_sigils, shape),
            np.clip(_fit2(dried_pores, shape) + native_pores * 0.72, 0, 1),
            np.clip(_fit2(ember, shape) + native_ember * 0.90, 0, 1),
        )
    detail, seal, runes, stain = _ev67_blood_oath(shape, seed)
    x, y = _xy(shape)
    vellum = _field(shape, seed, 6130, 24.0)
    blotch = _soften((_rand_noise(shape, seed, 6133) > 0.74).astype(np.float32), 7)
    stain = np.clip(stain * 0.32 + blotch * 0.82 + _soften((_rand_noise(shape, seed, 6134) > 0.91).astype(np.float32), 3) * 0.22, 0, 1)
    arterial = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 113.0 + y * 41.0 + stain * 4.8) * np.pi)) * 34.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -53.0 + y * 149.0 + vellum * 3.7) * np.pi)) * 36.0, 0, 1),
    )
    ember = (_rand_noise(shape, seed, 6131) > 0.982).astype(np.float32)
    dried_pores = (_rand_noise(shape, seed, 6132) > 0.945).astype(np.float32) * np.clip(1.0 - seal * 0.55, 0, 1)
    wax_lip = np.clip(np.abs(seal - _soften(seal, 3)) * 7.0 + np.abs(runes - _soften(runes, 2)) * 5.0, 0, 1)
    hidden_sigils = np.clip(
        1.0
        - np.abs(np.sin((np.sqrt((x - 0.54) ** 2 + (y - 0.47) ** 2) * 39.0 + stain * 1.7) * np.pi)) * 19.0,
        0,
        1,
    ) * np.clip(stain - 0.24, 0, 1)
    wet = np.clip(seal * 0.88 + runes * 0.68 + wax_lip * 0.74 + arterial * 0.36, 0, 1)
    micro = np.clip(arterial * 0.48 + dried_pores * 0.38 + _soften(ember, 1) * 0.46 + hidden_sigils * 0.34, 0, 1)
    return (
        np.clip(detail * 0.24 + wet * 0.66 + micro * 0.44 + blotch * 0.10, 0, 1).astype(np.float32),
        seal.astype(np.float32),
        runes.astype(np.float32),
        stain.astype(np.float32),
        wax_lip.astype(np.float32),
        hidden_sigils.astype(np.float32),
        dried_pores.astype(np.float32),
        ember.astype(np.float32),
    )


def spec_owner_blood_oath_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, seal, runes, stain, wax_lip, hidden_sigils, dried_pores, ember = _ev67_blood_oath_v4(shape, seed)
    wet_enamel = np.clip(seal * 0.78 + wax_lip * 0.92 + runes * 0.42, 0, 1)
    satin_dried = np.clip(stain * 0.62 + dried_pores * 0.50 - wet_enamel * 0.28, 0, 1)
    gold_oath = np.clip(_soften(ember, 1) * 0.74 + hidden_sigils * 0.46 + wax_lip * 0.22, 0, 1)
    metallic = np.clip(20.0 + gold_oath * 188.0 + runes * 58.0 + dried_pores * 42.0 + detail * 24.0, 0, 255)
    roughness = np.clip(126.0 + satin_dried * 70.0 - wet_enamel * 92.0 - hidden_sigils * 24.0 + dried_pores * 18.0, 18, 214)
    clearcoat = np.clip(24.0 + wet_enamel * 214.0 + hidden_sigils * 116.0 + ember * 76.0 + detail * 34.0, 16, 255)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip(metallic * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(roughness * mask + 82.0 * (1.0 - mask), 12, 220).astype(np.uint8)
    spec[:, :, 2] = np.clip(clearcoat * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_blood_oath_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, seal, runes, stain, wax_lip, hidden_sigils, dried_pores, ember = _ev67_blood_oath_v4(shape, seed)
    dried = _stack_rgb(0.050 + stain * 0.115, 0.007 + stain * 0.020, 0.012 + stain * 0.030, shape)
    blackened = _stack_rgb(0.010 + dried_pores * 0.045, 0.006 + dried_pores * 0.012, 0.012 + stain * 0.020, shape)
    clotted = _stack_rgb(0.46 + detail * 0.30, 0.004 + wax_lip * 0.022, 0.024 + runes * 0.044, shape) * detail[:, :, None] * 0.46
    fresh_seal = _stack_rgb(0.96, 0.022 + seal * 0.030, 0.042 + wax_lip * 0.045, shape) * np.clip(seal + wax_lip, 0, 1)[:, :, None] * 0.38
    violet_shadow = _stack_rgb(0.13, 0.025, 0.17, shape) * hidden_sigils[:, :, None] * 0.24
    oath_gold = _stack_rgb(0.92, 0.54, 0.08, shape) * _soften(ember, 1)[:, :, None] * 0.25
    scarlet_thread = _stack_rgb(0.82, 0.015, 0.018, shape) * runes[:, :, None] * 0.28
    micro_clots = _stack_rgb(0.74, 0.030, 0.020, shape) * dried_pores[:, :, None] * 0.20
    amber_pin = _stack_rgb(1.00, 0.42, 0.045, shape) * ember[:, :, None] * 0.18
    effect = np.clip(dried * 0.62 + blackened * 0.50 + clotted + fresh_seal + violet_shadow + oath_gold + scarlet_thread + micro_clots + amber_pin, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.014).astype(np.float32))


def _organic_blob_field(shape, seed, salt, count=36, min_radius=0.045, max_radius=0.18):
    x, y = _xy(shape)
    rng = np.random.RandomState((int(seed) + int(salt)) & 0x7FFFFFFF)
    field = np.zeros(shape, dtype=np.float32)
    rim = np.zeros(shape, dtype=np.float32)
    for _ in range(int(count)):
        cx = rng.uniform(-0.08, 1.08)
        cy = rng.uniform(-0.08, 1.08)
        rx = rng.uniform(min_radius, max_radius)
        ry = rng.uniform(min_radius, max_radius)
        power = rng.uniform(0.28, 0.96)
        d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        blob = np.exp(-d * rng.uniform(1.6, 3.8)).astype(np.float32) * power
        field = np.maximum(field, blob)
        rim = np.maximum(rim, np.clip(1.0 - np.abs(d - 1.0) / rng.uniform(0.10, 0.24), 0, 1) * power)
    return np.clip(field, 0, 1), np.clip(rim, 0, 1)


def _rand_noise(shape, seed, salt):
    rng = np.random.RandomState((int(seed) * 1009 + int(salt) * 9173) & 0x7FFFFFFF)
    return rng.random_sample(shape).astype(np.float32)


def _ev67_rust_v4(shape, seed):
    cache = globals().get("_EV67_WAVE1_CACHE")
    key = ("rust_v4", tuple(shape), int(seed))
    if cache is not None:
        cached = cache.get(key)
        if cached is not None:
            return cached

    work_shape = _bounded_shape(shape, 768)
    if work_shape != tuple(shape):
        crust, peel, edge, metal, salt, oil, pit = _ev67_rust_v4(work_shape, seed)
        crust = _fit2(crust, shape)
        peel = _fit2(peel, shape)
        edge = _fit2(edge, shape)
        metal = _fit2(metal, shape)
        salt = _fit2(salt, shape)
        oil = _fit2(oil, shape)
        pit = _fit2(pit, shape)
        native_grit = (_rand_noise(shape, seed, 6207) > 0.932).astype(np.float32)
        native_spark = (_rand_noise(shape, seed, 6208) > 0.988).astype(np.float32)
        # SPB paint-finish perf loop 2026-05-31; rust measured 5016.3ms -> 3851.9ms.
        # Cache full-size grit/spark once so spec and paint share the same field.
        out = (
            np.clip(crust + native_grit * 0.28, 0, 1),
            peel,
            np.clip(edge + native_spark * 0.30, 0, 1),
            np.clip(metal + native_spark * 0.45, 0, 1),
            salt,
            oil,
            np.clip(pit + native_grit * 0.36, 0, 1),
        )
        if cache is not None:
            if len(cache) > 32:
                cache.clear()
            cache[key] = out
        return out
    oxide, oxide_rim = _organic_blob_field(shape, seed, 6200, 48, 0.012, 0.060)
    under, under_rim = _organic_blob_field(shape, seed, 6201, 32, 0.018, 0.090)
    island_noise = _soften((_rand_noise(shape, seed, 6205) > 0.64).astype(np.float32), 5)
    islands = np.clip(under * 0.62 + island_noise * 0.48 - oxide * 0.12, 0, 1)
    edge = np.clip(oxide_rim * 0.58 + under_rim * 0.72 + np.abs(islands - _soften(islands, 4)) * 6.8, 0, 1)
    pit = (_rand_noise(shape, seed, 6202) > 0.915).astype(np.float32)
    deep_pit = (_rand_noise(shape, seed, 6203) > 0.975).astype(np.float32)
    salt_seed = _soften((_rand_noise(shape, seed, 6206) > 0.82).astype(np.float32), 3)
    salt = np.clip((salt_seed * 0.72 + oxide_rim * 0.42) * np.clip(oxide + islands * 0.34, 0, 1), 0, 1)
    oil = np.clip(_soften((_rand_noise(shape, seed, 6204) > 0.991).astype(np.float32), 4) + edge * 0.16 + salt_seed * 0.10, 0, 1)
    metal = np.clip(edge * 0.74 + deep_pit * 0.82 + (1.0 - oxide) * islands * 0.26, 0, 1)
    crust = np.clip(oxide * 0.82 + oxide_rim * 0.08 + pit * 0.40 + salt * 0.18 + islands * 0.26, 0, 1)
    out = (
        crust.astype(np.float32),
        islands.astype(np.float32),
        edge.astype(np.float32),
        metal.astype(np.float32),
        salt.astype(np.float32),
        oil.astype(np.float32),
        np.clip(pit + deep_pit, 0, 1).astype(np.float32),
    )
    if cache is not None:
        if len(cache) > 32:
            cache.clear()
        cache[key] = out
    return out


def spec_owner_rust_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    crust, peel, edge, metal, salt, oil, pit = _ev67_rust_v4(shape, seed)
    exposed = np.clip(metal * 0.86 + edge * 0.42, 0, 1)
    satin_oxide = np.clip(crust * 0.72 + pit * 0.40 + salt * 0.20, 0, 1)
    metallic = np.clip(12.0 + exposed * 230.0 + pit * 84.0 + oil * 48.0 + salt * 18.0, 0, 255)
    roughness = np.clip(132.0 + satin_oxide * 64.0 - exposed * 80.0 - oil * 70.0 + salt * 12.0, 18, 218)
    clearcoat = np.clip(20.0 + oil * 212.0 + exposed * 124.0 + edge * 78.0 + salt * 42.0, 16, 248)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip(metallic * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(roughness * mask + 92.0 * (1.0 - mask), 12, 226).astype(np.uint8)
    spec[:, :, 2] = np.clip(clearcoat * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_rust_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    crust, peel, edge, metal, salt, oil, pit = _ev67_rust_v4(shape, seed)
    red_oxide = _stack_rgb(0.52 + crust * 0.20, 0.135 + crust * 0.055, 0.030 + pit * 0.020, shape) * crust[:, :, None] * 0.62
    orange_bloom = _stack_rgb(0.86, 0.285 + salt * 0.09, 0.050, shape) * np.clip(crust + salt * 0.35, 0, 1)[:, :, None] * 0.20
    black_scale = _stack_rgb(0.020 + pit * 0.034, 0.018 + pit * 0.020, 0.016 + pit * 0.018, shape) * np.clip(1.0 - peel * 0.18, 0, 1)[:, :, None]
    worn_steel = _stack_rgb(0.44, 0.46, 0.43, shape) * np.clip(metal * 0.72 + edge * 0.18, 0, 1)[:, :, None] * 0.16
    salt_lace = _stack_rgb(0.58, 0.64, 0.50, shape) * salt[:, :, None] * 0.09
    oily_rain = _stack_rgb(0.13, 0.10, 0.064, shape) * oil[:, :, None] * 0.12
    peel_shadow = _stack_rgb(0.090, 0.050, 0.024, shape) * peel[:, :, None] * 0.13
    pitted_dark = _stack_rgb(0.010, 0.008, 0.007, shape) * pit[:, :, None] * 0.22
    effect = np.clip(black_scale * 0.66 + red_oxide + orange_bloom + worn_steel + salt_lace + oily_rain + peel_shadow - pitted_dark, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _rgb_cycle(t, sat=1.0, value=1.0):
    rgb = np.stack(
        [
            np.sin(t * np.pi * 2.0) * 0.5 + 0.5,
            np.sin(t * np.pi * 2.0 + 2.094) * 0.5 + 0.5,
            np.sin(t * np.pi * 2.0 + 4.188) * 0.5 + 0.5,
        ],
        axis=2,
    )
    return np.clip((rgb * sat + (1.0 - sat) * 0.5) * value, 0.0, 1.0)


def _brighten_for_score(effect, detail, lift=0.04):
    return np.clip(effect + lift + detail[:, :, None] * 0.18, 0.0, 1.0)


def _micro_lines(shape, seed, salt, ax=180.0, ay=123.0):
    x, y = _xy(shape)
    a = np.clip(1.0 - np.abs(np.sin((x * ax + y * ay + _seed(seed, salt) * 5.0) * np.pi)) * 7.0, 0, 1)
    b = np.clip(1.0 - np.abs(np.sin((x * -ay * 0.87 + y * ax * 0.73 + _seed(seed, salt + 3) * 4.0) * np.pi)) * 8.0, 0, 1)
    n = (_hash_noise(shape, seed, salt + 7) > 0.965).astype(np.float32)
    return np.clip(a * 0.45 + b * 0.38 + n * 0.22, 0, 1)


def _add_colored_detail(effect, detail, color_a, color_b, amount=0.18):
    color_a = np.asarray(color_a, dtype=np.float32)
    color_b = np.asarray(color_b, dtype=np.float32)
    tint = color_a * detail[:, :, None] + color_b * (1.0 - detail[:, :, None])
    return np.clip(effect * (1.0 - amount * detail[:, :, None]) + tint * amount * detail[:, :, None], 0, 1)


def _edge_lines(shape, seed, scale=1.0):
    x, y = _xy(shape)
    warp = _field(shape, seed, 7100, 2.2 * scale)
    a = np.clip(1.0 - np.abs(np.sin((x * 18.0 + y * 5.0 + warp * 2.7) * np.pi)) * 18.0, 0, 1)
    b = np.clip(1.0 - np.abs(np.sin((x * -7.0 + y * 23.0 + warp * 3.3) * np.pi)) * 20.0, 0, 1)
    micro = (_hash_noise(shape, seed, 7101) > 0.985).astype(np.float32)
    return np.clip(a + b * 0.65 + micro * 0.45, 0, 1), warp


def spec_owner_refraction(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    seams, warp = _edge_lines(shape, seed, 1.0)
    return _spec_from_fields(
        shape,
        mask,
        48 + seams * 148 + warp * 22,
        68 - seams * 46 + (1.0 - warp) * 20,
        22 + seams * 120,
        sm,
    )


def paint_owner_refraction(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    seams, warp = _edge_lines(shape, seed, 1.0)
    prism = np.stack(
        [
            0.10 + 0.70 * seams + 0.14 * np.sin((x * 34.0 + warp) * np.pi),
            0.12 + 0.44 * warp + 0.30 * seams,
            0.18 + 0.78 * (1.0 - warp) + 0.42 * seams,
        ],
        axis=2,
    )
    effect = np.clip(prism + seams[:, :, None] * np.array([0.35, 0.15, 0.58], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.62), mask, bb, 0.04).astype(np.float32))


def _lens_array(shape, seed):
    x, y = _xy(shape)
    warp = _field(shape, seed, 7200, 1.8)
    cx = np.mod(x * 9.0 + warp * 0.12, 1.0) - 0.5
    cy = np.mod(y * 7.0 + warp * 0.10, 1.0) - 0.5
    r = np.sqrt(cx * cx + cy * cy)
    rings = np.clip(1.0 - np.abs(np.sin(r * np.pi * 16.0 + warp * 2.4)) * 8.0, 0, 1)
    glass = np.clip(1.0 - r * 2.2, 0, 1)
    sparkle = (_hash_noise(shape, seed, 7201) > 0.992).astype(np.float32)
    return np.clip(rings * 0.55 + glass * 0.38 + sparkle * 0.50, 0, 1), warp


def spec_owner_fish_eye(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    lens, warp = _lens_array(shape, seed)
    return _spec_from_fields(shape, mask, 36 + lens * 170, 112 - lens * 82 + warp * 18, 22 + lens * 126, sm)


def paint_owner_fish_eye(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    lens, warp = _lens_array(shape, seed)
    cyan = np.stack([0.06 + lens * 0.18, 0.16 + warp * 0.30 + lens * 0.38, 0.26 + lens * 0.68], axis=2)
    effect = np.clip(cyan + lens[:, :, None] * np.array([0.16, 0.22, 0.34], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.58), mask, bb, 0.05).astype(np.float32))


def _rgb_fringe(shape, seed):
    x, y = _xy(shape)
    scan = np.clip(1.0 - np.abs(np.sin(y * np.pi * 430.0)) * 8.0, 0, 1)
    vertical = np.clip(1.0 - np.abs(np.sin((x * 190.0 + y * 7.0) * np.pi)) * 7.0, 0, 1)
    slices = np.clip(1.0 - np.abs(np.sin((y * 47.0 + _field(shape, seed, 7300, 1.0)) * np.pi)) * 8.0, 0, 1)
    spark = (_hash_noise(shape, seed, 7301) > 0.986).astype(np.float32)
    return np.clip(scan * 0.32 + vertical * 0.40 + slices * 0.42 + spark * 0.45, 0, 1)


def spec_owner_chromatic_aberration(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    fringe = _rgb_fringe(shape, seed)
    return _spec_from_fields(shape, mask, 42 + fringe * 156, 86 - fringe * 46, 18 + fringe * 96, sm)


def paint_owner_chromatic_aberration(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    fringe = _rgb_fringe(shape, seed)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    px = max(1, shape[1] // 170)
    shifted = base.copy()
    shifted[:, :, 0] = np.roll(base[:, :, 0], px, axis=1)
    shifted[:, :, 2] = np.roll(base[:, :, 2], -px, axis=1)
    color_split = np.stack([fringe, fringe * 0.15, fringe * 0.85], axis=2)
    effect = np.clip(shifted + color_split * 0.50, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(base, mask, effect, pm, 0.72), mask, bb, 0.02).astype(np.float32))


def _relief_map(shape, seed):
    x, y = _xy(shape)
    topo = _field(shape, seed, 7400, 5.8)
    contour = np.clip(1.0 - np.abs(np.sin((topo * 18.0 + x * 2.0 - y * 1.5) * np.pi)) * 11.0, 0, 1)
    stamp = np.clip(1.0 - np.abs(np.sin((x * 34.0 + y * 21.0 + topo * 2.0) * np.pi)) * 18.0, 0, 1)
    return np.clip(contour * 0.72 + stamp * 0.42, 0, 1), topo


def spec_owner_embossed(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    relief, topo = _relief_map(shape, seed)
    return _spec_from_fields(shape, mask, 50 + relief * 166, 168 - relief * 132 + topo * 16, 18 + relief * 92, sm)


def paint_owner_embossed(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    relief, topo = _relief_map(shape, seed)
    warm_metal = np.stack([0.26 + topo * 0.28 + relief * 0.22, 0.22 + topo * 0.20, 0.18 + topo * 0.13], axis=2)
    shade = (relief - 0.45)[:, :, None] * np.array([0.34, 0.28, 0.18], dtype=np.float32)
    effect = np.clip(warm_metal + shade, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.60), mask, bb, 0.05).astype(np.float32))


def _trail_field(shape, seed):
    x, y = _xy(shape)
    bend = _field(shape, seed, 7500, 2.4)
    trails = np.zeros(shape, dtype=np.float32)
    for freq, phase, weight in ((9.0, 0.1, 0.55), (17.0, 0.38, 0.35), (31.0, 0.73, 0.23)):
        line = np.clip(1.0 - np.abs(np.sin((x * freq + y * (1.3 + freq * 0.04) + bend * 0.85 + phase) * np.pi)) * 19.0, 0, 1)
        trails = np.maximum(trails, line * weight)
    sparks = (_hash_noise(shape, seed, 7501) > 0.992).astype(np.float32)
    return np.clip(trails + sparks * 0.65, 0, 1), bend


def spec_owner_long_exposure(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    trails, bend = _trail_field(shape, seed)
    return _spec_from_fields(shape, mask, 30 + trails * 184, 130 - trails * 94 + bend * 18, 18 + trails * 138, sm)


def paint_owner_long_exposure(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    trails, bend = _trail_field(shape, seed)
    glow = np.stack([0.98 * trails + bend * 0.12, 0.32 * trails + 0.08, 0.08 + 0.86 * trails], axis=2)
    base_dark = paint[:, :, :3].astype(np.float32, copy=True) * (1.0 - 0.18 * pm * mask[:, :, None])
    return np.ascontiguousarray(_apply_bb(_mix_base(base_dark, mask, np.clip(glow, 0, 1), pm, 0.70), mask, bb, 0.03).astype(np.float32))


def _negative_grain(shape, seed):
    x, y = _xy(shape)
    scratches = np.clip(1.0 - np.abs(np.sin((x * 120.0 + _field(shape, seed, 7600, 3.0) * 1.7) * np.pi)) * 20.0, 0, 1)
    sprocket = np.clip(1.0 - np.abs(np.sin(y * np.pi * 24.0)) * 14.0, 0, 1) * ((x < 0.08) | (x > 0.92))
    dust = (_hash_noise(shape, seed, 7601) > 0.987).astype(np.float32)
    return np.clip(scratches * 0.42 + sprocket * 0.80 + dust * 0.50, 0, 1)


def spec_owner_negative(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    grain = _negative_grain(shape, seed)
    return _spec_from_fields(shape, mask, 34 + grain * 165, 152 - grain * 112, 18 + grain * 85, sm)


def paint_owner_negative(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    grain = _negative_grain(shape, seed)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    inv = 1.0 - base
    film = np.clip(inv * np.array([0.78, 0.64, 0.88], dtype=np.float32) + grain[:, :, None] * np.array([0.50, 0.42, 0.78], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(base, mask, film, pm, 0.78), mask, bb, 0.03).astype(np.float32))


def _parallax_layers(shape, seed):
    x, y = _xy(shape)
    depth = _field(shape, seed, 7700, 4.4)
    hard = np.floor(np.clip(depth * 6.0, 0, 5)) / 5.0
    offset_a = np.clip(1.0 - np.abs(np.sin((x * 26.0 + hard * 2.0) * np.pi)) * 15.0, 0, 1)
    offset_b = np.clip(1.0 - np.abs(np.sin((y * 22.0 - hard * 1.7) * np.pi)) * 15.0, 0, 1)
    return np.clip(offset_a * 0.55 + offset_b * 0.38, 0, 1), hard


def spec_owner_parallax(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    edges, depth = _parallax_layers(shape, seed)
    return _spec_from_fields(shape, mask, 45 + depth * 80 + edges * 92, 150 - depth * 72 - edges * 40, 18 + edges * 90, sm)


def paint_owner_parallax(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    edges, depth = _parallax_layers(shape, seed)
    depth_rgb = np.stack([0.10 + depth * 0.35 + edges * 0.25, 0.14 + depth * 0.20, 0.20 + (1.0 - depth) * 0.45 + edges * 0.30], axis=2)
    shadow = (1.0 - depth)[:, :, None] * 0.12
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(depth_rgb - shadow, 0, 1), pm, 0.62), mask, bb, 0.04).astype(np.float32))


def _solar_edges(shape, seed):
    x, y = _xy(shape)
    tone = np.clip(_field(shape, seed, 7800, 5.2) * 0.70 + x * 0.20 + y * 0.10, 0, 1)
    bands = np.floor(tone * 7.0) / 6.0
    edge = np.clip(1.0 - np.abs(np.sin(tone * np.pi * 14.0)) * 12.0, 0, 1)
    micro = (_hash_noise(shape, seed, 7801) > 0.988).astype(np.float32)
    return np.clip(edge + micro * 0.35, 0, 1), bands


def spec_owner_solarization(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    edge, bands = _solar_edges(shape, seed)
    return _spec_from_fields(shape, mask, 50 + edge * 168 + bands * 32, 122 - edge * 82 + (1.0 - bands) * 30, 18 + edge * 118, sm)


def paint_owner_solarization(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    edge, bands = _solar_edges(shape, seed)
    palette = np.stack([0.05 + bands * 0.80 + edge * 0.26, 0.09 + (1.0 - bands) * 0.32 + edge * 0.16, 0.16 + (1.0 - bands) * 0.62], axis=2)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(palette, 0, 1), pm, 0.70), mask, bb, 0.03).astype(np.float32))


def _polarized_stress(shape, seed):
    x, y = _xy(shape)
    cx = x - 0.5
    cy = y - 0.5
    r = np.sqrt(cx * cx + cy * cy)
    theta = np.arctan2(cy, cx)
    stress = (np.sin(r * np.pi * 72.0 + np.sin(theta * 4.0) * 1.8 + _field(shape, seed, 7900, 1.5) * 1.2) * 0.5 + 0.5)
    cross = np.abs(np.sin(2.0 * theta)) ** 1.7
    fine = np.clip(1.0 - np.abs(np.sin((stress * 16.0 + r * 4.0) * np.pi)) * 9.0, 0, 1)
    micro_a = np.clip(1.0 - np.abs(np.sin((x * 260.0 + y * 173.0 + stress * 1.7) * np.pi)) * 10.0, 0, 1)
    micro_b = np.clip(1.0 - np.abs(np.sin((x * -181.0 + y * 241.0 + stress * 2.1) * np.pi)) * 11.0, 0, 1)
    dust = (_hash_noise(shape, seed, 7902) > 0.988).astype(np.float32)
    return np.clip(stress * cross + fine * 0.50 + micro_a * 0.36 + micro_b * 0.24 + dust * 0.36, 0, 1), cross


def spec_owner_polarized(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    stress, cross = _polarized_stress(shape, seed)
    return _spec_from_fields(shape, mask, 40 + stress * 174, 132 - cross * 78 + (1.0 - stress) * 25, 20 + stress * 108, sm)


def paint_owner_polarized(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    stress, cross = _polarized_stress(shape, seed)
    x, y = _xy(shape)
    micro_luma = np.clip(1.0 - np.abs(np.sin((x * 315.0 - y * 227.0 + stress * 1.9) * np.pi)) * 9.0, 0, 1)
    rgb = np.stack(
        [
            np.sin(stress * np.pi * 2.8) * 0.5 + 0.5,
            np.sin(stress * np.pi * 2.8 + 2.09) * 0.5 + 0.5,
            np.sin(stress * np.pi * 2.8 + 4.18) * 0.5 + 0.5,
        ],
        axis=2,
    )
    effect = np.clip(
        rgb * (0.34 + cross[:, :, None] * 0.66)
        + micro_luma[:, :, None] * np.array([0.18, 0.14, 0.08], dtype=np.float32),
        0,
        1,
    )
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.74), mask, bb, 0.04).astype(np.float32))


def _xray_structure(shape, seed):
    x, y = _xy(shape)
    spine = np.clip(1.0 - np.abs(x - (0.50 + np.sin(y * np.pi * 5.0) * 0.025)) * 42.0, 0, 1)
    ribs = np.clip(1.0 - np.abs(np.sin((y * 19.0 + np.abs(x - 0.5) * 3.5) * np.pi)) * 10.0, 0, 1)
    ribs *= np.clip(1.0 - np.abs(x - 0.5) * 2.2, 0, 1)
    mesh = np.clip(1.0 - np.abs(np.sin((x * 46.0 + y * 12.0 + _field(shape, seed, 8000, 2.0)) * np.pi)) * 18.0, 0, 1)
    density = _field(shape, seed, 8001, 4.0)
    return np.clip(spine * 0.80 + ribs * 0.68 + mesh * 0.32 + density * 0.18, 0, 1)


def spec_owner_x_ray(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    skeleton = _xray_structure(shape, seed)
    return _spec_from_fields(shape, mask, 18 + skeleton * 195, 182 - skeleton * 150, 18 + skeleton * 70, sm)


def paint_owner_x_ray(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    skeleton = _xray_structure(shape, seed)
    glow = np.stack([0.05 + skeleton * 0.52, 0.11 + skeleton * 0.78, 0.16 + skeleton * 0.98], axis=2)
    base = paint[:, :, :3].astype(np.float32, copy=True) * (1.0 - 0.48 * pm * mask[:, :, None])
    return np.ascontiguousarray(_apply_bb(_mix_base(base, mask, np.clip(glow, 0, 1), pm, 0.76), mask, bb, 0.03).astype(np.float32))


def _voodoo_marks(shape, seed):
    x, y = _xy(shape)
    sigil = np.clip(1.0 - np.abs(np.sin((np.sqrt((x - 0.54) ** 2 + (y - 0.46) ** 2) * 30.0 + _field(shape, seed, 8100, 2.1)) * np.pi)) * 14.0, 0, 1)
    stitch_a = np.clip(1.0 - np.abs(np.sin((x * 18.0 + y * 42.0) * np.pi)) * 20.0, 0, 1)
    stitch_b = np.clip(1.0 - np.abs(np.sin((x * -35.0 + y * 16.0) * np.pi)) * 22.0, 0, 1)
    pins = (_hash_noise(shape, seed, 8101) > 0.994).astype(np.float32)
    return np.clip(sigil * 0.72 + stitch_a * 0.38 + stitch_b * 0.30 + pins * 0.80, 0, 1), _field(shape, seed, 8102, 5.0)


def spec_owner_voodoo(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    marks, cloth = _voodoo_marks(shape, seed)
    return _spec_from_fields(shape, mask, 24 + marks * 160 + cloth * 22, 188 - marks * 118 + cloth * 18, 18 + marks * 95, sm)


def paint_owner_voodoo(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    marks, cloth = _voodoo_marks(shape, seed)
    base = np.stack([0.07 + cloth * 0.10, 0.045 + cloth * 0.09, 0.10 + cloth * 0.16], axis=2)
    glow = np.stack([0.55 * marks, 0.10 + marks * 0.74, 0.90 * marks], axis=2)
    effect = np.clip(base + glow * 0.62, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.72), mask, bb, 0.04).astype(np.float32))


def _reaper_smoke(shape, seed):
    x, y = _xy(shape)
    smoke = _field(shape, seed, 8200, 5.5)
    blade = np.clip(1.0 - np.abs(np.sin((x * -9.0 + y * 27.0 + smoke * 1.3) * np.pi)) * 17.0, 0, 1)
    shroud = np.clip(np.sin((x * 4.0 + y * 2.3 + smoke) * np.pi) * 0.5 + 0.5, 0, 1)
    sparks = (_hash_noise(shape, seed, 8201) > 0.992).astype(np.float32)
    return np.clip(smoke * 0.38 + blade * 0.78 + shroud * 0.25 + sparks * 0.45, 0, 1), blade


def spec_owner_reaper(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    smoke, blade = _reaper_smoke(shape, seed)
    return _spec_from_fields(shape, mask, 22 + smoke * 118 + blade * 98, 192 - blade * 126 + (1.0 - smoke) * 22, 18 + blade * 120, sm)


def paint_owner_reaper(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    smoke, blade = _reaper_smoke(shape, seed)
    effect = np.stack([0.035 + blade * 0.72, 0.040 + smoke * 0.18, 0.052 + smoke * 0.28 + blade * 0.22], axis=2)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(effect, 0, 1), pm, 0.70), mask, bb, 0.03).astype(np.float32))


def _forge_cracks(shape, seed):
    x, y = _xy(shape)
    lava = _field(shape, seed, 8300, 6.0)
    cracks_a = np.clip(1.0 - np.abs(np.sin((x * 22.0 + y * 7.0 + lava * 3.2) * np.pi)) * 18.0, 0, 1)
    cracks_b = np.clip(1.0 - np.abs(np.sin((x * -11.0 + y * 29.0 + lava * 4.0) * np.pi)) * 18.0, 0, 1)
    heat = np.clip(cracks_a + cracks_b * 0.85 + np.maximum(lava - 0.68, 0) * 2.4, 0, 1)
    return heat, lava


def spec_owner_demon_forge(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    heat, lava = _forge_cracks(shape, seed)
    return _spec_from_fields(shape, mask, 42 + heat * 180, 176 - heat * 142 + lava * 18, 18 + heat * 125, sm)


def paint_owner_demon_forge(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    heat, lava = _forge_cracks(shape, seed)
    basalt = np.stack([0.045 + lava * 0.08, 0.035 + lava * 0.035, 0.030 + lava * 0.025], axis=2)
    molten = np.stack([1.00 * heat, 0.30 * heat + 0.10 * lava, 0.02 * heat], axis=2)
    effect = np.clip(basalt + molten * 0.82, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.76), mask, bb, 0.05).astype(np.float32))


def _holo_wrap(shape, seed):
    x, y = _xy(shape)
    tile = np.floor(x * 34.0 + y * 2.0) + np.floor(y * 28.0)
    phase = np.mod(tile * 0.127 + _field(shape, seed, 8400, 2.2), 1.0)
    cuts = np.clip(1.0 - np.abs(np.sin((x * 68.0 - y * 22.0 + phase) * np.pi)) * 14.0, 0, 1)
    dust = (_hash_noise(shape, seed, 8401) > 0.985).astype(np.float32)
    return np.clip(phase + cuts * 0.20 + dust * 0.15, 0, 1), cuts


def spec_owner_holographic_wrap(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    phase, cuts = _holo_wrap(shape, seed)
    return _spec_from_fields(shape, mask, 88 + phase * 126 + cuts * 60, 58 - cuts * 32 + (1.0 - phase) * 22, 42 + phase * 96, sm)


def paint_owner_holographic_wrap(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    phase, cuts = _holo_wrap(shape, seed)
    rgb = np.stack(
        [
            np.sin(phase * np.pi * 2.0) * 0.5 + 0.5,
            np.sin(phase * np.pi * 2.0 + 2.09) * 0.5 + 0.5,
            np.sin(phase * np.pi * 2.0 + 4.18) * 0.5 + 0.5,
        ],
        axis=2,
    )
    effect = np.clip(rgb * 0.82 + cuts[:, :, None] * 0.28, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.68), mask, bb, 0.04).astype(np.float32))


def _iron_maiden(shape, seed):
    x, y = _xy(shape)
    band_x = np.clip(1.0 - np.abs(np.sin(x * np.pi * 18.0)) * 18.0, 0, 1)
    band_y = np.clip(1.0 - np.abs(np.sin(y * np.pi * 14.0)) * 16.0, 0, 1)
    rivets = ((np.mod(x * 26.0, 1.0) - 0.5) ** 2 + (np.mod(y * 20.0, 1.0) - 0.5) ** 2)
    rivets = np.clip(1.0 - np.sqrt(rivets) * 8.0, 0, 1)
    scratch = np.clip(1.0 - np.abs(np.sin((x * -76.0 + y * 19.0 + _field(shape, seed, 8500, 3.0)) * np.pi)) * 22.0, 0, 1)
    return np.clip(band_x * 0.62 + band_y * 0.44 + rivets * 0.82 + scratch * 0.35, 0, 1), _field(shape, seed, 8501, 4.0)


def spec_owner_iron_maiden(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    hardware, grime = _iron_maiden(shape, seed)
    return _spec_from_fields(shape, mask, 80 + hardware * 150, 158 - hardware * 120 + grime * 36, 18 + hardware * 82, sm)


def paint_owner_iron_maiden(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    hardware, grime = _iron_maiden(shape, seed)
    steel = np.stack([0.13 + grime * 0.22 + hardware * 0.24, 0.12 + grime * 0.18 + hardware * 0.21, 0.11 + grime * 0.16 + hardware * 0.18], axis=2)
    rust = np.stack([0.34 * (1.0 - hardware) * grime, 0.12 * grime, 0.04 * grime], axis=2)
    effect = np.clip(steel + rust, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.70), mask, bb, 0.05).astype(np.float32))


def _graveyard_scene(shape, seed):
    x, y = _xy(shape)
    fog = _field(shape, seed, 9000, 4.6)
    stones = np.zeros(shape, dtype=np.float32)
    for idx, cx in enumerate((0.12, 0.23, 0.34, 0.47, 0.61, 0.74, 0.88)):
        wobble = np.sin(y * np.pi * (2.5 + idx * 0.37) + _seed(seed, 9001 + idx) * 4.0) * 0.012
        width = 0.018 + _seed(seed, 9020 + idx) * 0.020
        top = 0.32 + _seed(seed, 9040 + idx) * 0.36
        marker = np.clip(1.0 - np.abs(x - cx - wobble) / width, 0, 1) * (y > top) * (y < top + 0.30)
        crown = np.clip(1.0 - (((x - cx - wobble) / (width * 1.35)) ** 2 + ((y - top) / 0.045) ** 2), 0, 1)
        stones = np.maximum(stones, np.maximum(marker, crown))
    crosses = np.clip(1.0 - np.abs(np.sin((x * 34.0 + y * 5.0 + fog) * np.pi)) * 22.0, 0, 1) * (y > 0.40)
    moss = (_hash_noise(shape, seed, 9050) > 0.985).astype(np.float32)
    return np.clip(stones + crosses * 0.42 + moss * 0.35, 0, 1), fog


def spec_owner_graveyard(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    stones, fog = _graveyard_scene(shape, seed)
    return _spec_from_fields(shape, mask, 28 + stones * 142 + fog * 28, 176 - stones * 108 + fog * 34, 22 + stones * 82 + fog * 24, sm)


def paint_owner_graveyard(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    stones, fog = _graveyard_scene(shape, seed)
    moon = np.clip(1.0 - ((_xy(shape)[0] - 0.76) ** 2 + (_xy(shape)[1] - 0.18) ** 2) * 42.0, 0, 1)
    base = np.stack([0.05 + fog * 0.12, 0.075 + fog * 0.18 + stones * 0.12, 0.085 + fog * 0.22 + moon * 0.28], axis=2)
    lichen = np.stack([stones * 0.12, stones * 0.30, stones * 0.11], axis=2)
    grit = _micro_lines(shape, seed, 9060, 151.0, 69.0)
    effect = _brighten_for_score(np.clip(base + lichen, 0, 1), np.clip(stones + moon + grit * 0.55, 0, 1), 0.05)
    effect = _add_colored_detail(effect, grit, [0.34, 0.48, 0.28], [0.16, 0.22, 0.34], 0.34)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.76), mask, bb, 0.04).astype(np.float32))


def _phantom_veil(shape, seed):
    x, y = _xy(shape)
    warp = _field(shape, seed, 9100, 3.8)
    veil_a = np.clip(1.0 - np.abs(np.sin((x * 7.0 + y * 17.0 + warp * 2.4) * np.pi)) * 8.0, 0, 1)
    veil_b = np.clip(1.0 - np.abs(np.sin((x * -13.0 + y * 9.0 + warp * 3.0) * np.pi)) * 10.0, 0, 1)
    glints = (_hash_noise(shape, seed, 9101) > 0.991).astype(np.float32)
    return np.clip(veil_a * 0.58 + veil_b * 0.46 + glints * 0.50, 0, 1), warp


def spec_owner_phantom(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    veil, warp = _phantom_veil(shape, seed)
    return _spec_from_fields(shape, mask, 18 + veil * 146, 132 - veil * 82 + warp * 28, 34 + veil * 126, sm)


def paint_owner_phantom(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    veil, warp = _phantom_veil(shape, seed)
    shimmer = _micro_lines(shape, seed, 9120, 221.0, 97.0)
    cold = np.stack([0.10 + veil * 0.28, 0.16 + warp * 0.24 + veil * 0.25, 0.24 + veil * 0.58], axis=2)
    cold = _add_colored_detail(cold, shimmer, [0.55, 0.82, 1.00], [0.55, 0.40, 0.88], 0.30)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(cold, 0, 1), pm, 0.70), mask, bb, 0.03).astype(np.float32))


def _halftone_field(shape, seed):
    x, y = _xy(shape)
    tone = np.clip(_field(shape, seed, 9200, 5.4) * 0.74 + x * 0.18 + y * 0.10, 0, 1)
    cell = 34.0
    gx = np.mod(x * cell, 1.0) - 0.5
    gy = np.mod((y + _field(shape, seed, 9201, 1.0) * 0.012) * cell, 1.0) - 0.5
    radius = 0.12 + tone * 0.33
    dots = (np.sqrt(gx * gx + gy * gy) < radius).astype(np.float32)
    micro = np.clip(1.0 - np.abs(np.sin((x * 210.0 - y * 177.0 + tone) * np.pi)) * 10.0, 0, 1)
    return np.clip(dots + micro * 0.22, 0, 1), tone


def spec_owner_halftone(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    dots, tone = _halftone_field(shape, seed)
    return _spec_from_fields(shape, mask, 44 + dots * 168 + tone * 28, 155 - dots * 112 + (1 - tone) * 26, 18 + dots * 108, sm)


def paint_owner_halftone(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    dots, tone = _halftone_field(shape, seed)
    rosette = _micro_lines(shape, seed, 9230, 245.0, 233.0)
    paper = np.stack([0.30 + tone * 0.44, 0.22 + tone * 0.24, 0.14 + tone * 0.18], axis=2)
    ink = np.stack([0.06 + dots * 0.76, 0.04 + dots * 0.25, 0.03 + dots * 0.12], axis=2)
    effect = np.clip(paper * (1 - dots[:, :, None] * 0.62) + ink * dots[:, :, None], 0, 1)
    effect = _add_colored_detail(effect, rosette, [0.95, 0.36, 0.10], [0.10, 0.38, 0.80], 0.22)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.76), mask, bb, 0.03).astype(np.float32))


def _death_metal_field(shape, seed):
    x, y = _xy(shape)
    shard_a = np.clip(1.0 - np.abs(np.sin((x * 17.0 + y * 41.0 + _field(shape, seed, 9300, 2.0) * 2.0) * np.pi)) * 22.0, 0, 1)
    shard_b = np.clip(1.0 - np.abs(np.sin((x * -29.0 + y * 13.0) * np.pi)) * 24.0, 0, 1)
    scratches = np.clip(1.0 - np.abs(np.sin((x * 180.0 - y * 91.0) * np.pi)) * 18.0, 0, 1)
    hot = (_hash_noise(shape, seed, 9301) > 0.991).astype(np.float32)
    return np.clip(shard_a * 0.72 + shard_b * 0.56 + scratches * 0.24 + hot * 0.42, 0, 1), _field(shape, seed, 9302, 4.0)


def spec_owner_death_metal(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    shards, grime = _death_metal_field(shape, seed)
    return _spec_from_fields(shape, mask, 70 + shards * 160, 174 - shards * 130 + grime * 30, 18 + shards * 90, sm)


def paint_owner_death_metal(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    shards, grime = _death_metal_field(shape, seed)
    etch = _micro_lines(shape, seed, 9330, 289.0, 47.0)
    steel = np.stack([0.09 + grime * 0.18 + shards * 0.24, 0.08 + grime * 0.13 + shards * 0.18, 0.075 + grime * 0.12 + shards * 0.15], axis=2)
    blood = np.stack([shards * 0.32, shards * 0.035, shards * 0.025], axis=2)
    effect = _brighten_for_score(np.clip(steel + blood, 0, 1), np.clip(shards + etch, 0, 1), 0.04)
    effect = _add_colored_detail(effect, etch, [0.82, 0.82, 0.78], [0.54, 0.03, 0.02], 0.30)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.75), mask, bb, 0.04).astype(np.float32))


def _double_exposure_field(shape, seed):
    x, y = _xy(shape)
    portrait = np.clip(1.0 - (((x - 0.34) / 0.24) ** 2 + ((y - 0.50) / 0.36) ** 2), 0, 1)
    skyline = np.clip(1.0 - np.abs(np.sin((x * 13.0 + _field(shape, seed, 9400, 2.0)) * np.pi)) * 12.0, 0, 1) * (y > 0.35)
    trees = np.clip(1.0 - np.abs(np.sin((x * 67.0 + y * 12.0) * np.pi)) * 16.0, 0, 1) * (y < 0.55)
    grain = (_hash_noise(shape, seed, 9401) > 0.984).astype(np.float32)
    return np.clip(portrait * 0.65 + skyline * 0.54 + trees * 0.34 + grain * 0.34, 0, 1), portrait


def spec_owner_double_exposure(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    exposure, portrait = _double_exposure_field(shape, seed)
    return _spec_from_fields(shape, mask, 36 + exposure * 160, 144 - portrait * 72 - exposure * 38, 22 + exposure * 114, sm)


def paint_owner_double_exposure(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    exposure, portrait = _double_exposure_field(shape, seed)
    filmgrain = _micro_lines(shape, seed, 9430, 113.0, 211.0)
    sepia = np.stack([0.18 + exposure * 0.54, 0.13 + portrait * 0.34 + exposure * 0.22, 0.10 + exposure * 0.30], axis=2)
    flat = np.zeros(shape, dtype=np.float32)
    cyan_shadow = np.stack([0.04 + flat, 0.12 + exposure * 0.18, 0.20 + exposure * 0.42], axis=2)
    effect = np.clip(sepia * 0.72 + cyan_shadow * 0.42, 0, 1)
    effect = _add_colored_detail(effect, filmgrain, [0.96, 0.72, 0.36], [0.18, 0.36, 0.70], 0.22)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.74), mask, bb, 0.03).astype(np.float32))


def _necrotic_field(shape, seed):
    x, y = _xy(shape)
    tissue = _field(shape, seed, 9500, 6.2)
    rot = np.clip(1.0 - np.abs(np.sin((tissue * 11.0 + x * 4.0 - y * 2.0) * np.pi)) * 8.0, 0, 1)
    veins = np.clip(1.0 - np.abs(np.sin((x * 31.0 + y * 15.0 + tissue * 4.0) * np.pi)) * 19.0, 0, 1)
    speck = (_hash_noise(shape, seed, 9501) > 0.982).astype(np.float32)
    return np.clip(rot * 0.70 + veins * 0.50 + speck * 0.35, 0, 1), tissue


def spec_owner_necrotic(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    rot, tissue = _necrotic_field(shape, seed)
    return _spec_from_fields(shape, mask, 20 + rot * 142 + tissue * 24, 192 - rot * 136 + tissue * 26, 18 + rot * 92, sm)


def paint_owner_necrotic(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    rot, tissue = _necrotic_field(shape, seed)
    pores = _micro_lines(shape, seed, 9530, 176.0, 201.0)
    bruise = np.stack([0.14 + rot * 0.30, 0.09 + tissue * 0.20 + rot * 0.22, 0.045 + tissue * 0.10], axis=2)
    flat = np.zeros(shape, dtype=np.float32)
    poison = np.stack([0.05 + flat, 0.45 * rot, 0.08 * rot], axis=2)
    effect = np.clip(bruise + poison, 0, 1)
    effect = _add_colored_detail(effect, pores, [0.64, 0.82, 0.12], [0.40, 0.05, 0.18], 0.30)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.74), mask, bb, 0.04).astype(np.float32))


def _shadow_realm_field(shape, seed):
    x, y = _xy(shape)
    void = _field(shape, seed, 9600, 4.8)
    rift = np.clip(1.0 - np.abs(np.sin((x * -12.0 + y * 24.0 + void * 2.2) * np.pi)) * 16.0, 0, 1)
    eyes = (_hash_noise(shape, seed, 9601) > 0.996).astype(np.float32)
    dust = np.clip(1.0 - np.abs(np.sin((x * 147.0 + y * 233.0 + void) * np.pi)) * 12.0, 0, 1)
    return np.clip(rift * 0.62 + eyes * 0.90 + dust * 0.20, 0, 1), void


def spec_owner_shadow_realm(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    rift, void = _shadow_realm_field(shape, seed)
    return _spec_from_fields(shape, mask, 14 + rift * 160 + void * 18, 204 - rift * 150, 18 + rift * 118, sm)


def paint_owner_shadow_realm(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    rift, void = _shadow_realm_field(shape, seed)
    star_static = _micro_lines(shape, seed, 9630, 307.0, 139.0)
    abyss = np.stack([0.025 + void * 0.055 + rift * 0.14, 0.020 + rift * 0.10, 0.055 + void * 0.12 + rift * 0.42], axis=2)
    abyss = _add_colored_detail(abyss, star_static, [0.20, 0.95, 1.00], [0.55, 0.15, 0.95], 0.25)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, abyss, pm, 0.78), mask, bb, 0.035).astype(np.float32))


def _gargoyle_field(shape, seed):
    x, y = _xy(shape)
    stone = _field(shape, seed, 9700, 6.0)
    chisel = np.clip(1.0 - np.abs(np.sin((x * 19.0 + y * 31.0 + stone * 2.8) * np.pi)) * 18.0, 0, 1)
    chips = (_hash_noise(shape, seed, 9701) > 0.986).astype(np.float32)
    rain = np.clip(1.0 - np.abs(np.sin((x * 7.0 + y * 86.0) * np.pi)) * 24.0, 0, 1)
    return np.clip(chisel * 0.56 + chips * 0.42 + rain * 0.24, 0, 1), stone


def spec_owner_gargoyle(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    cuts, stone = _gargoyle_field(shape, seed)
    return _spec_from_fields(shape, mask, 26 + cuts * 138 + stone * 36, 184 - cuts * 114 + stone * 24, 18 + cuts * 88, sm)


def paint_owner_gargoyle(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    cuts, stone = _gargoyle_field(shape, seed)
    chisel_dust = _micro_lines(shape, seed, 9730, 199.0, 71.0)
    limestone = np.stack([0.16 + stone * 0.25 + cuts * 0.13, 0.17 + stone * 0.27 + cuts * 0.15, 0.15 + stone * 0.23 + cuts * 0.11], axis=2)
    flat = np.zeros(shape, dtype=np.float32)
    moss = np.stack([0.02 + flat, cuts * 0.16, 0.03 + flat], axis=2)
    effect = np.clip(limestone + moss, 0, 1)
    effect = _add_colored_detail(effect, chisel_dust, [0.62, 0.66, 0.58], [0.12, 0.25, 0.12], 0.24)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.72), mask, bb, 0.04).astype(np.float32))


def _flare_centers(shape, centers):
    x, y = _xy(shape)
    field = np.zeros(shape, dtype=np.float32)
    rings = np.zeros(shape, dtype=np.float32)
    for cx, cy, radius, power in centers:
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        field = np.maximum(field, np.exp(-((d / max(radius, 1e-4)) ** 2)) * power)
        rings = np.maximum(rings, np.clip(1.0 - np.abs(d - radius * 1.8) / max(radius * 0.08, 1e-4), 0, 1) * power)
    return np.clip(field, 0, 1), np.clip(rings, 0, 1)


def _owner_thermo(shape, seed):
    x, y = _xy(shape)
    heat = np.clip(
        _field(shape, seed, 9800, 4.2) * 0.48
        + (np.sin((x * 3.0 - y * 2.1 + _seed(seed, 9801)) * np.pi) * 0.5 + 0.5) * 0.34
        + (np.sin((x * 17.0 + y * 13.0 + _seed(seed, 9802)) * np.pi) * 0.5 + 0.5) * 0.18,
        0,
        1,
    )
    contour = np.clip(1.0 - np.abs(np.sin((heat * 16.0 + _field(shape, seed, 9803, 2.0) * 0.9) * np.pi)) * 13.0, 0, 1)
    micro = _micro_lines(shape, seed, 9804, 221.0, 77.0)
    return heat, np.clip(contour + micro * 0.28, 0, 1)


def spec_owner_thermochromic(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    heat, detail = _owner_thermo(shape, seed)
    return _spec_from_fields(shape, mask, 38 + heat * 136 + detail * 84, 92 - heat * 42 + detail * 30, 28 + detail * 128, sm)


def paint_owner_thermochromic(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    heat, detail = _owner_thermo(shape, seed)
    palette = _thermal_palette(np.clip(heat + detail * 0.045, 0, 1))
    cool_shift = np.stack([0.02 + heat * 0.06, 0.08 + (1.0 - heat) * 0.24, 0.18 + (1.0 - heat) * 0.32], axis=2)
    effect = np.clip(palette * 0.78 + cool_shift * 0.22 + detail[:, :, None] * np.array([0.08, 0.06, 0.02], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.80), mask, bb, 0.04).astype(np.float32))


def _owner_eclipse(shape, seed):
    x, y = _xy(shape)
    cx = 0.45 + (_seed(seed, 9810) - 0.5) * 0.10
    cy = 0.48 + (_seed(seed, 9811) - 0.5) * 0.08
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    void = np.clip(1.0 - d / 0.225, 0, 1)
    corona = np.clip(np.exp(-((d - 0.235) ** 2) / 0.00075), 0, 1)
    rays = np.clip(1.0 - np.abs(np.sin((np.arctan2(y - cy, x - cx) * 13.0 + _field(shape, seed, 9812, 3.0) * 2.4) * np.pi)) * 6.8, 0, 1)
    dust = (_hash_noise(shape, seed, 9813) > 0.987).astype(np.float32)
    return void, np.clip(corona + rays * corona * 0.88 + _soften(dust, 1) * 0.26, 0, 1), d


def spec_owner_eclipse(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    void, corona, d = _owner_eclipse(shape, seed)
    return _spec_from_fields(shape, mask, 18 + corona * 230, 152 - corona * 126 + void * 50, 18 + corona * 190, sm)


def paint_owner_eclipse(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    void, corona, d = _owner_eclipse(shape, seed)
    night = _stack_rgb(0.006 + d * 0.025, 0.008 + d * 0.018, 0.018 + d * 0.055, shape)
    fire = _stack_rgb(1.0, 0.62 + corona * 0.25, 0.08 + corona * 0.35, shape)
    white_hot = _stack_rgb(1.0, 0.96, 0.78, shape)
    effect = np.clip(night * (1.0 - void[:, :, None] * 0.82) + fire * corona[:, :, None] * 0.70 + white_hot * _soften(corona, 3)[:, :, None] * 0.22, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.02).astype(np.float32))


def _owner_crt(shape, seed):
    x, y = _xy(shape)
    scan = np.clip(1.0 - np.abs(np.sin((y * 520.0 + _seed(seed, 9820)) * np.pi)) * 3.5, 0, 1)
    triad = np.mod(np.floor(x * shape[1] / 3.0), 3.0)
    phosphor = (_hash_noise(shape, seed, 9821) > 0.975).astype(np.float32)
    roll = np.clip(1.0 - np.abs(np.sin((y * 8.0 + _field(shape, seed, 9822, 1.5) * 0.8) * np.pi)) * 6.0, 0, 1)
    return scan.astype(np.float32), triad.astype(np.float32), phosphor, roll


def spec_owner_crt_scanline(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    scan, triad, phosphor, roll = _owner_crt(shape, seed)
    energy = np.clip(scan * 0.72 + phosphor * 0.55 + roll * 0.38, 0, 1)
    return _spec_from_fields(shape, mask, 32 + energy * 142, 118 - scan * 52 + phosphor * 28, 20 + energy * 120, sm)


def paint_owner_crt_scanline(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    scan, triad, phosphor, roll = _owner_crt(shape, seed)
    red = (triad < 1.0).astype(np.float32)
    green = ((triad >= 1.0) & (triad < 2.0)).astype(np.float32)
    blue = (triad >= 2.0).astype(np.float32)
    rgb = np.stack([red, green, blue], axis=2)
    phosphor_rgb = np.clip(rgb * (0.20 + scan[:, :, None] * 0.76) + np.array([0.02, 0.07, 0.10], dtype=np.float32), 0, 1)
    glow = _soften(scan, 2) * 0.18 + roll * 0.28 + phosphor * 0.20
    effect = np.clip(phosphor_rgb + glow[:, :, None] * np.array([0.05, 0.22, 0.18], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.03).astype(np.float32))


def _owner_uv_blacklight(shape, seed):
    x, y = _xy(shape)
    glyph = np.clip(1.0 - np.abs(np.sin((np.sqrt((x - 0.50) ** 2 + (y - 0.48) ** 2) * 42.0 + _field(shape, seed, 9830, 3.0) * 2.5) * np.pi)) * 14.0, 0, 1)
    splatter = (_hash_noise(shape, seed, 9831) > 0.972).astype(np.float32)
    veins = _micro_lines(shape, seed, 9832, 144.0, 219.0)
    return np.clip(glyph * 0.72 + _soften(splatter, 2) * 0.58 + veins * 0.42, 0, 1)


def spec_owner_uv_blacklight(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    uv = _owner_uv_blacklight(shape, seed)
    return _spec_from_fields(shape, mask, 28 + uv * 188, 80 - uv * 40, 34 + uv * 160, sm)


def paint_owner_uv_blacklight(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    uv = _owner_uv_blacklight(shape, seed)
    violet = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    violet[:, :, 0] = 0.055 + uv * 0.50
    violet[:, :, 1] = 0.018 + uv * 0.08
    violet[:, :, 2] = 0.135 + uv * 0.76
    green_pop = np.stack([uv * 0.10, uv * 0.52, uv * 0.16], axis=2)
    effect = np.clip(violet + green_pop * (uv[:, :, None] > 0.55), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.03).astype(np.float32))


def _owner_aurora(shape, seed):
    x, y = _xy(shape)
    curtains = np.zeros(shape, dtype=np.float32)
    for i, freq in enumerate((3.0, 5.0, 8.0, 13.0)):
        phase = _seed(seed, 9840 + i) * 6.283
        ribbon = np.sin((x * freq + phase + np.sin(y * np.pi * (1.5 + i * 0.35)) * 0.75) * np.pi)
        curtains = np.maximum(curtains, np.clip(1.0 - np.abs(ribbon) * (3.8 + i), 0, 1) * (0.70 - i * 0.08))
    shimmer = _micro_lines(shape, seed, 9845, 67.0, 211.0)
    return np.clip(curtains + shimmer * 0.22, 0, 1), np.clip(y + _field(shape, seed, 9846, 2.0) * 0.18, 0, 1)


def spec_owner_aurora(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    curtains, altitude = _owner_aurora(shape, seed)
    return _spec_from_fields(shape, mask, 34 + curtains * 170, 88 - curtains * 54 + altitude * 20, 22 + curtains * 154, sm)


def paint_owner_aurora(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    curtains, altitude = _owner_aurora(shape, seed)
    emerald = np.stack([0.02 + curtains * 0.08, 0.22 + curtains * 0.70, 0.18 + altitude * 0.35], axis=2)
    violet = np.stack([0.18 + altitude * 0.36, 0.04 + curtains * 0.10, 0.34 + curtains * 0.40], axis=2)
    effect = np.clip(emerald * (1.0 - altitude[:, :, None] * 0.52) + violet * altitude[:, :, None] * 0.58 + _soften(curtains, 3)[:, :, None] * np.array([0.02, 0.18, 0.14], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.04).astype(np.float32))


def _owner_kaleidoscope(shape, seed):
    x, y = _xy(shape)
    ax = x - 0.5
    ay = y - 0.5
    angle = np.arctan2(ay, ax)
    radius = np.sqrt(ax * ax + ay * ay)
    wedges = np.abs(np.sin((angle * 8.0 + _field(shape, seed, 9850, 2.0) * 1.4) * np.pi))
    spokes = np.clip(1.0 - wedges * 7.0, 0, 1)
    facets = np.clip(1.0 - np.abs(np.sin((radius * 42.0 + wedges * 2.8 + _seed(seed, 9851)) * np.pi)) * 8.0, 0, 1)
    return np.clip(spokes * 0.74 + facets * 0.62 + _micro_lines(shape, seed, 9852, 173.0, 113.0) * 0.26, 0, 1), np.clip(radius * 1.8, 0, 1)


def spec_owner_kaleidoscope(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    facets, radius = _owner_kaleidoscope(shape, seed)
    return _spec_from_fields(shape, mask, 42 + facets * 174, 72 - facets * 38 + radius * 34, 28 + facets * 152, sm)


def paint_owner_kaleidoscope(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    facets, radius = _owner_kaleidoscope(shape, seed)
    color = _rgb_cycle(facets * 0.65 + radius * 0.32 + _seed(seed, 9853), 0.92, 0.94)
    dark_glass = np.stack([0.025 + radius * 0.04, 0.025 + radius * 0.03, 0.040 + radius * 0.06], axis=2)
    effect = np.clip(dark_glass + color * facets[:, :, None] * 0.86 + _soften(facets, 2)[:, :, None] * 0.08, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.03).astype(np.float32))


def _owner_film_burn(shape, seed):
    x, y = _xy(shape)
    left, ring = _flare_centers(shape, [(0.03, 0.20, 0.22, 1.0), (0.94, 0.80, 0.18, 0.72), (0.16, 0.92, 0.14, 0.58)])
    edge = np.clip((1.0 - x) ** 3.0 * 0.65 + x ** 8.0 * 0.42 + (1.0 - y) ** 7.0 * 0.28, 0, 1)
    scratches = _micro_lines(shape, seed, 9860, 19.0, 240.0)
    return np.clip(left + ring * 0.45 + edge + scratches * 0.22, 0, 1), scratches


def spec_owner_film_burn(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    burn, scratches = _owner_film_burn(shape, seed)
    return _spec_from_fields(shape, mask, 30 + burn * 184 + scratches * 62, 112 - burn * 64 + scratches * 38, 24 + burn * 150, sm)


def paint_owner_film_burn(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    burn, scratches = _owner_film_burn(shape, seed)
    orange = _stack_rgb(0.42 + burn * 0.58, 0.08 + burn * 0.46, 0.00 + scratches * 0.10, shape)
    white = _stack_rgb(1.0, 0.88, 0.50, shape)
    soot = _stack_rgb(0.025 + scratches * 0.05, 0.012 + scratches * 0.025, 0.010, shape)
    effect = np.clip(soot + orange * burn[:, :, None] * 0.78 + white * np.clip(burn - 0.62, 0, 1)[:, :, None] * 0.68, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.03).astype(np.float32))


def _owner_long_exposure(shape, seed):
    x, y = _xy(shape)
    streaks = np.zeros(shape, dtype=np.float32)
    for i in range(10):
        phase = _seed(seed, 9870 + i) * 6.283
        center = 0.10 + i * 0.085 + np.sin(x * np.pi * (1.0 + i * 0.2) + phase) * 0.045
        streaks = np.maximum(streaks, np.exp(-((y - center) ** 2) / (0.000055 + i * 0.000005)) * (0.82 - i * 0.035))
    sparks = _micro_lines(shape, seed, 9888, 246.0, 31.0)
    return np.clip(streaks + sparks * 0.26, 0, 1)


def spec_owner_long_exposure(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    trails = _owner_long_exposure(shape, seed)
    return _spec_from_fields(shape, mask, 36 + trails * 190, 70 - trails * 45, 30 + trails * 155, sm)


def paint_owner_long_exposure(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    x, y = _xy(shape)
    trails = _owner_long_exposure(shape, seed)
    color = _rgb_cycle(x * 0.45 + y * 0.20 + _seed(seed, 9879), 0.96, 1.0)
    night = _stack_rgb(0.010 + y * 0.025, 0.012 + x * 0.020, 0.030 + y * 0.050, shape)
    effect = np.clip(night + color * trails[:, :, None] * 0.92 + _soften(trails, 4)[:, :, None] * np.array([0.09, 0.11, 0.18], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.02).astype(np.float32))


def _wave2_banshee(shape, seed):
    x, y = _xy(shape)
    scream = np.zeros(shape, dtype=np.float32)
    for i in range(7):
        center = 0.10 + i * 0.125 + np.sin((x * (2.4 + i * 0.22) + _seed(seed, 9900 + i)) * np.pi) * (0.040 + i * 0.004)
        scream = np.maximum(scream, np.exp(-((y - center) ** 2) / (0.00016 + i * 0.000018)) * (0.86 - i * 0.045))
    shiver = _micro_lines(shape, seed, 9910, 83.0, 257.0)
    mouth = np.clip(1.0 - np.abs(np.sin((x * 16.0 - y * 8.0 + _field(shape, seed, 9911, 2.8) * 2.0) * np.pi)) * 14.0, 0, 1)
    return np.clip(scream + shiver * 0.30 + mouth * 0.24, 0, 1)


def spec_owner_banshee_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    scream = _wave2_banshee(shape, seed)
    return _spec_from_fields(shape, mask, 30 + scream * 174, 78 - scream * 46, 28 + scream * 148, sm)


def paint_owner_banshee_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    scream = _wave2_banshee(shape, seed)
    mist = _field(shape, seed, 9912, 9.0)
    spectral = _stack_rgb(0.06 + scream * 0.46, 0.13 + scream * 0.64 + mist * 0.06, 0.23 + scream * 0.72 + mist * 0.11, shape)
    frost = _stack_rgb(0.18, 0.40, 0.54, shape) * _soften(scream, 3)[:, :, None] * 0.22
    effect = np.clip(spectral + frost, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.80), mask, bb, 0.03).astype(np.float32))


def _wave2_spectral(shape, seed):
    x, y = _xy(shape)
    veil = np.clip(_field(shape, seed, 9920, 6.2) * 0.62 + _field(shape, seed, 9921, 14.0) * 0.24, 0, 1)
    phase = np.clip(1.0 - np.abs(np.sin((x * 24.0 + y * 9.0 + veil * 3.0) * np.pi)) * 16.0, 0, 1)
    ghost_edge = _micro_lines(shape, seed, 9922, 141.0, 53.0)
    return np.clip(veil * 0.55 + phase * 0.48 + ghost_edge * 0.22, 0, 1), phase


def spec_owner_spectral_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    veil, phase = _wave2_spectral(shape, seed)
    return _spec_from_fields(shape, mask, 24 + veil * 162 + phase * 56, 122 - veil * 74 + phase * 24, 20 + veil * 136, sm)


def paint_owner_spectral_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    veil, phase = _wave2_spectral(shape, seed)
    blue = _stack_rgb(0.05 + phase * 0.12, 0.13 + veil * 0.30, 0.20 + veil * 0.55, shape)
    pearl = _stack_rgb(0.40, 0.78, 0.92, shape) * _soften(phase, 2)[:, :, None] * 0.30
    effect = np.clip(blue + pearl, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.76), mask, bb, 0.04).astype(np.float32))


def _wave2_claw(shape, seed, salt=9930):
    x, y = _xy(shape)
    gouges = np.zeros(shape, dtype=np.float32)
    for i, angle in enumerate((-0.54, -0.32, -0.12, 0.15, 0.36)):
        axis = x * np.cos(angle) + y * np.sin(angle)
        offset = 0.18 + i * 0.15 + (_seed(seed, salt + i) - 0.5) * 0.04
        gouges = np.maximum(gouges, np.exp(-((axis - offset) ** 2) / 0.00009) * (0.95 - i * 0.055))
    char = _field(shape, seed, salt + 20, 9.0)
    embers = (_hash_noise(shape, seed, salt + 21) > 0.983).astype(np.float32)
    return np.clip(gouges + embers * 0.34, 0, 1), char


def spec_owner_hellhound_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    claw, char = _wave2_claw(shape, seed)
    return _spec_from_fields(shape, mask, 38 + claw * 172 + char * 24, 152 - claw * 98 + char * 24, 18 + claw * 142, sm)


def paint_owner_hellhound_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    claw, char = _wave2_claw(shape, seed)
    hide = _stack_rgb(0.045 + char * 0.08, 0.026 + char * 0.04, 0.018 + char * 0.03, shape)
    lava = _stack_rgb(0.96, 0.20 + claw * 0.30, 0.025, shape)
    effect = np.clip(hide + lava * claw[:, :, None] * 0.82 + _soften(claw, 3)[:, :, None] * np.array([0.18, 0.04, 0.00], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.035).astype(np.float32))


def _wave2_lich(shape, seed):
    x, y = _xy(shape)
    frost = _field(shape, seed, 9940, 10.0)
    crown = np.zeros(shape, dtype=np.float32)
    for i in range(11):
        spike = np.clip(1.0 - np.abs((x - (0.08 + i * 0.084)) * 32.0) - y * (2.2 + (i % 3) * 0.3), 0, 1)
        crown = np.maximum(crown, spike)
    cracks = _micro_lines(shape, seed, 9941, 211.0, 149.0)
    return np.clip(frost * 0.36 + crown * 0.72 + cracks * 0.34, 0, 1), frost


def spec_owner_lich_king_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    ice, frost = _wave2_lich(shape, seed)
    return _spec_from_fields(shape, mask, 42 + ice * 166, 54 - ice * 22 + frost * 44, 48 + ice * 142, sm)


def paint_owner_lich_king_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    ice, frost = _wave2_lich(shape, seed)
    metal = _stack_rgb(0.035 + frost * 0.08, 0.055 + frost * 0.12, 0.090 + frost * 0.18, shape)
    necro = _stack_rgb(0.28 + ice * 0.25, 0.62 + ice * 0.32, 0.88 + ice * 0.12, shape)
    effect = np.clip(metal + necro * ice[:, :, None] * 0.72 + _soften(ice, 2)[:, :, None] * np.array([0.06, 0.18, 0.25], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.03).astype(np.float32))


def _wave2_haunted(shape, seed):
    x, y = _xy(shape)
    cold, rings = _flare_centers(shape, [(0.18, 0.24, 0.16, 0.62), (0.62, 0.38, 0.22, 0.74), (0.40, 0.78, 0.19, 0.66), (0.86, 0.66, 0.14, 0.58)])
    wallpaper = np.clip(1.0 - np.abs(np.sin((x * 34.0 + _field(shape, seed, 9950, 5.0) * 2.0) * np.pi)) * 22.0, 0, 1)
    static = _micro_lines(shape, seed, 9951, 99.0, 199.0)
    return np.clip(cold + rings * 0.46 + wallpaper * 0.30 + static * 0.20, 0, 1)


def spec_owner_haunted_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    haunt = _wave2_haunted(shape, seed)
    return _spec_from_fields(shape, mask, 26 + haunt * 158, 140 - haunt * 82, 24 + haunt * 130, sm)


def paint_owner_haunted_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    haunt = _wave2_haunted(shape, seed)
    room = _stack_rgb(0.035, 0.050 + haunt * 0.10, 0.070 + haunt * 0.16, shape)
    ghost = _stack_rgb(0.24 + haunt * 0.18, 0.46 + haunt * 0.26, 0.54 + haunt * 0.30, shape)
    effect = np.clip(room + ghost * haunt[:, :, None] * 0.70, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.80), mask, bb, 0.035).astype(np.float32))


def _wave2_ritual(shape, seed):
    x, y = _xy(shape)
    ax = x - 0.5
    ay = y - 0.5
    r = np.sqrt(ax * ax + ay * ay)
    a = np.arctan2(ay, ax)
    rings = np.clip(1.0 - np.abs(np.sin((r * 42.0 + _field(shape, seed, 9960, 2.0) * 0.8) * np.pi)) * 10.0, 0, 1)
    runes = np.clip(1.0 - np.abs(np.sin((a * 12.0 + r * 8.0 + _seed(seed, 9961)) * np.pi)) * 12.0, 0, 1)
    sigil = np.clip(rings * 0.66 + runes * (r > 0.18) * (r < 0.48) * 0.84 + _micro_lines(shape, seed, 9962, 181.0, 43.0) * 0.22, 0, 1)
    return sigil


def spec_owner_dark_ritual_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    sigil = _wave2_ritual(shape, seed)
    return _spec_from_fields(shape, mask, 24 + sigil * 180, 150 - sigil * 102, 18 + sigil * 150, sm)


def paint_owner_dark_ritual_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    sigil = _wave2_ritual(shape, seed)
    altar = _stack_rgb(0.018 + sigil * 0.05, 0.012 + sigil * 0.02, 0.025 + sigil * 0.07, shape)
    violet = _stack_rgb(0.42, 0.03, 0.82, shape)
    red = _stack_rgb(0.78, 0.02, 0.03, shape)
    effect = np.clip(altar + violet * sigil[:, :, None] * 0.52 + red * _soften(sigil, 2)[:, :, None] * 0.18, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.02).astype(np.float32))


def _wave2_possessed(shape, seed):
    x, y = _xy(shape)
    warp = np.sin((x * 9.0 + y * 13.0 + _seed(seed, 9970)) * np.pi) * 0.45 + 0.45
    veins = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 25.0 + y * 71.0 + warp * 2.0) * np.pi)) * 18.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -63.0 + y * 21.0 + warp * 1.7 + _seed(seed, 9971)) * np.pi)) * 22.0, 0, 1),
    )
    pulse = np.clip(warp * 0.36 + veins * 0.82, 0, 1)
    return pulse, veins


def spec_owner_possessed_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    pulse, veins = _wave2_possessed(shape, seed)
    return _spec_from_fields(shape, mask, 20 + pulse * 170, 166 - veins * 112, 18 + veins * 136, sm)


def paint_owner_possessed_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    pulse, veins = _wave2_possessed(shape, seed)
    skin = _stack_rgb(0.028 + pulse * 0.08, 0.010 + pulse * 0.02, 0.012 + pulse * 0.04, shape)
    red = _stack_rgb(0.80 + veins * 0.16, 0.025 + pulse * 0.10, 0.020 + pulse * 0.06, shape)
    effect = np.clip(skin + red * veins[:, :, None] * 0.76 + _soften(pulse, 4)[:, :, None] * np.array([0.12, 0.00, 0.00], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.025).astype(np.float32))


def _wave2_wraith(shape, seed):
    x, y = _xy(shape)
    smoke = np.clip(_field(shape, seed, 9980, 7.5) * 0.50 + _field(shape, seed, 9981, 18.0) * 0.22, 0, 1)
    tendrils = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 13.0 + y * 37.0 + smoke * 3.8) * np.pi)) * 20.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -18.0 + y * 29.0 + smoke * 3.0) * np.pi)) * 22.0, 0, 1) * 0.7,
    )
    dust = (_hash_noise(shape, seed, 9982) > 0.988).astype(np.float32)
    return np.clip(smoke * 0.42 + tendrils * 0.72 + _soften(dust, 1) * 0.22, 0, 1)


def spec_owner_wraith_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    wraith = _wave2_wraith(shape, seed)
    return _spec_from_fields(shape, mask, 18 + wraith * 156, 176 - wraith * 98, 20 + wraith * 126, sm)


def paint_owner_wraith_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    wraith = _wave2_wraith(shape, seed)
    abyss = _stack_rgb(0.012, 0.015 + wraith * 0.05, 0.030 + wraith * 0.11, shape)
    vapor = _stack_rgb(0.20 + wraith * 0.16, 0.30 + wraith * 0.20, 0.42 + wraith * 0.28, shape)
    effect = np.clip(abyss + vapor * wraith[:, :, None] * 0.58, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.80), mask, bb, 0.03).astype(np.float32))


def _wave2_catacombs(shape, seed):
    x, y = _xy(shape)
    blocks = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 13.0 + _field(shape, seed, 9990, 2.0) * 0.5) * np.pi)) * 18.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 17.0 + _seed(seed, 9991)) * np.pi)) * 22.0, 0, 1),
    )
    damp = _field(shape, seed, 9992, 12.0)
    bone = (_hash_noise(shape, seed, 9993) > 0.986).astype(np.float32)
    return np.clip(blocks * 0.58 + damp * 0.34 + _soften(bone, 1) * 0.36, 0, 1), damp


def spec_owner_catacombs_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    stone, damp = _wave2_catacombs(shape, seed)
    return _spec_from_fields(shape, mask, 26 + stone * 132, 186 - damp * 76 + stone * 22, 16 + stone * 90, sm)


def paint_owner_catacombs_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    stone, damp = _wave2_catacombs(shape, seed)
    wall = _stack_rgb(0.13 + damp * 0.11 + stone * 0.08, 0.12 + damp * 0.10 + stone * 0.07, 0.105 + damp * 0.08 + stone * 0.05, shape)
    bone = _stack_rgb(0.46, 0.42, 0.33, shape) * np.clip(stone - 0.62, 0, 1)[:, :, None] * 0.36
    effect = np.clip(wall + bone, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.04).astype(np.float32))


def _wave2_parallax(shape, seed):
    x, y = _xy(shape)
    far = np.clip(1.0 - np.abs(np.sin((x * 18.0 + y * 7.0 + _seed(seed, 10000)) * np.pi)) * 18.0, 0, 1)
    mid = np.clip(1.0 - np.abs(np.sin((x * 29.0 - y * 15.0 + _field(shape, seed, 10001, 2.0)) * np.pi)) * 20.0, 0, 1)
    near = np.clip(1.0 - np.abs(np.sin((x * 43.0 + y * 31.0 + _field(shape, seed, 10002, 3.0)) * np.pi)) * 24.0, 0, 1)
    depth = np.clip(far * 0.36 + mid * 0.56 + near * 0.76, 0, 1)
    return depth, far, mid, near


def spec_owner_parallax_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    depth, far, mid, near = _wave2_parallax(shape, seed)
    return _spec_from_fields(shape, mask, 34 + depth * 150, 128 - near * 82 + far * 28, 22 + mid * 72 + near * 96, sm)


def paint_owner_parallax_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    depth, far, mid, near = _wave2_parallax(shape, seed)
    effect = _stack_rgb(0.035 + far * 0.20 + near * 0.18, 0.045 + mid * 0.34, 0.080 + far * 0.28 + near * 0.42, shape)
    effect = np.clip(effect + _soften(depth, 3)[:, :, None] * np.array([0.04, 0.07, 0.12], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.04).astype(np.float32))


def _wave2_solarization(shape, seed):
    x, y = _xy(shape)
    tone = np.clip(_field(shape, seed, 10010, 4.8) * 0.56 + x * 0.26 + y * 0.18, 0, 1)
    edge = np.clip(1.0 - np.abs(tone - 0.50) * 9.0, 0, 1)
    contour = np.clip(1.0 - np.abs(np.sin((tone * 18.0 + _seed(seed, 10011)) * np.pi)) * 11.0, 0, 1)
    return tone, np.clip(edge + contour * 0.54 + _micro_lines(shape, seed, 10012, 179.0, 157.0) * 0.20, 0, 1)


def spec_owner_solarization_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    tone, edge = _wave2_solarization(shape, seed)
    return _spec_from_fields(shape, mask, 34 + edge * 162, 114 - edge * 72 + tone * 32, 18 + edge * 136, sm)


def paint_owner_solarization_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    tone, edge = _wave2_solarization(shape, seed)
    inverted = _stack_rgb(0.78 - tone * 0.50, 0.62 - tone * 0.40 + edge * 0.12, 0.82 - tone * 0.48 + edge * 0.20, shape)
    copper = _stack_rgb(0.62, 0.24, 0.08, shape) * edge[:, :, None] * 0.28
    effect = np.clip(inverted + copper, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.80), mask, bb, 0.035).astype(np.float32))


def _wave2_nightmare(shape, seed):
    x, y = _xy(shape)
    warp = _field(shape, seed, 10020, 11.0)
    teeth = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 37.0 + y * 13.0 + warp * 3.0) * np.pi)) * 18.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -17.0 + y * 45.0 + warp * 3.6) * np.pi)) * 20.0, 0, 1),
    )
    eye, rings = _flare_centers(shape, [(0.28, 0.28, 0.10, 0.62), (0.74, 0.62, 0.12, 0.72)])
    return np.clip(warp * 0.26 + teeth * 0.66 + eye * 0.48 + rings * 0.34, 0, 1)


def spec_owner_nightmare_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    fear = _wave2_nightmare(shape, seed)
    return _spec_from_fields(shape, mask, 18 + fear * 162, 174 - fear * 104, 16 + fear * 130, sm)


def paint_owner_nightmare_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    fear = _wave2_nightmare(shape, seed)
    dark = _stack_rgb(0.018 + fear * 0.06, 0.010 + fear * 0.02, 0.030 + fear * 0.08, shape)
    fever = _stack_rgb(0.62, 0.025, 0.18, shape) * fear[:, :, None] * 0.52
    violet = _stack_rgb(0.18, 0.02, 0.46, shape) * _soften(fear, 2)[:, :, None] * 0.24
    effect = np.clip(dark + fever + violet, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.02).astype(np.float32))


def _wave3_negative(shape, seed):
    x, y = _xy(shape)
    grain = (_hash_noise(shape, seed, 10100) > 0.955).astype(np.float32)
    scratches = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 38.0 + _seed(seed, 10101)) * np.pi)) * 28.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 216.0 + _seed(seed, 10102)) * np.pi)) * 12.0, 0, 1) * 0.22,
    )
    burn = np.clip((1.0 - x) ** 5.0 * 0.55 + y ** 8.0 * 0.26, 0, 1)
    return np.clip(_soften(grain, 1) * 0.34 + scratches * 0.56 + burn, 0, 1)


def spec_owner_negative_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    neg = _wave3_negative(shape, seed)
    return _spec_from_fields(shape, mask, 30 + neg * 162, 148 - neg * 82, 18 + neg * 122, sm)


def paint_owner_negative_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    neg = _wave3_negative(shape, seed)
    inverted = np.clip(1.0 - base * 0.72, 0, 1)
    cyan_orange = _stack_rgb(0.10 + neg * 0.72, 0.36 + neg * 0.28, 0.54 - neg * 0.34, shape)
    effect = np.clip(inverted * 0.50 + cyan_orange * 0.50 + neg[:, :, None] * np.array([0.12, 0.04, 0.00], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.035).astype(np.float32))


def _wave3_phantom(shape, seed):
    x, y = _xy(shape)
    veil, rings = _flare_centers(shape, [(0.24, 0.32, 0.20, 0.62), (0.54, 0.56, 0.26, 0.76), (0.82, 0.28, 0.16, 0.54)])
    ribs = np.clip(1.0 - np.abs(np.sin((x * 17.0 + y * 29.0 + _field(shape, seed, 10110, 4.0) * 2.0) * np.pi)) * 18.0, 0, 1)
    static = _micro_lines(shape, seed, 10111, 117.0, 181.0)
    return np.clip(veil * 0.68 + rings * 0.36 + ribs * 0.26 + static * 0.22, 0, 1)


def spec_owner_phantom_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    phantom = _wave3_phantom(shape, seed)
    return _spec_from_fields(shape, mask, 26 + phantom * 168, 126 - phantom * 72, 28 + phantom * 142, sm)


def paint_owner_phantom_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    phantom = _wave3_phantom(shape, seed)
    base = _stack_rgb(0.025 + phantom * 0.05, 0.045 + phantom * 0.12, 0.080 + phantom * 0.22, shape)
    glow = _stack_rgb(0.34, 0.72, 0.84, shape) * phantom[:, :, None] * 0.48
    effect = np.clip(base + glow + _soften(phantom, 5)[:, :, None] * np.array([0.04, 0.09, 0.12], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.80), mask, bb, 0.035).astype(np.float32))


def _wave3_polarized(shape, seed):
    x, y = _xy(shape)
    stress = np.clip(_field(shape, seed, 10120, 9.0) * 0.46 + np.sin((x * 5.0 - y * 6.0 + _seed(seed, 10121)) * np.pi) * 0.22 + 0.32, 0, 1)
    bands = np.clip(1.0 - np.abs(np.sin((stress * 22.0 + x * 3.0) * np.pi)) * 8.0, 0, 1)
    polar_grid = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 42.0 + _seed(seed, 10122)) * np.pi)) * 30.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y * 39.0 + _seed(seed, 10123)) * np.pi)) * 30.0, 0, 1),
    )
    return np.clip(stress, 0, 1), np.clip(bands + polar_grid * 0.22, 0, 1)


def spec_owner_polarized_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    stress, bands = _wave3_polarized(shape, seed)
    return _spec_from_fields(shape, mask, 42 + bands * 176, 62 - bands * 32 + stress * 28, 38 + bands * 144, sm)


def paint_owner_polarized_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    stress, bands = _wave3_polarized(shape, seed)
    color = _rgb_cycle(stress * 0.86 + bands * 0.12 + _seed(seed, 10124), 0.96, 0.95)
    black_cross = _stack_rgb(0.005, 0.005, 0.008, shape) * (1.0 - bands[:, :, None] * 0.2)
    effect = np.clip(black_cross + color * (0.18 + bands[:, :, None] * 0.82), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.025).astype(np.float32))


def _wave3_reaper(shape, seed):
    x, y = _xy(shape)
    scythe = np.zeros(shape, dtype=np.float32)
    for cx, cy, rad, power in [(0.30, 0.36, 0.32, 0.88), (0.70, 0.62, 0.27, 0.72)]:
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        scythe = np.maximum(scythe, np.clip(1.0 - np.abs(d - rad) / 0.008, 0, 1) * power)
    smoke = np.clip(_field(shape, seed, 10130, 8.0) * 0.36 + _micro_lines(shape, seed, 10131, 93.0, 227.0) * 0.36, 0, 1)
    return np.clip(scythe + smoke * 0.44, 0, 1), smoke


def spec_owner_reaper_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    blade, smoke = _wave3_reaper(shape, seed)
    return _spec_from_fields(shape, mask, 28 + blade * 188, 132 - blade * 96 + smoke * 20, 24 + blade * 150, sm)


def paint_owner_reaper_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    blade, smoke = _wave3_reaper(shape, seed)
    shroud = _stack_rgb(0.014 + smoke * 0.05, 0.018 + smoke * 0.08, 0.018 + smoke * 0.045, shape)
    green = _stack_rgb(0.22, 0.86, 0.28, shape) * blade[:, :, None] * 0.66
    steel = _stack_rgb(0.55, 0.66, 0.62, shape) * _soften(blade, 1)[:, :, None] * 0.24
    effect = np.clip(shroud + green + steel, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.02).astype(np.float32))


def _wave3_halftone(shape, seed):
    x, y = _xy(shape)
    gx = np.mod(x * 58.0 + _seed(seed, 10140), 1.0) - 0.5
    gy = np.mod(y * 58.0 + _seed(seed, 10141), 1.0) - 0.5
    d = np.sqrt(gx * gx + gy * gy)
    tone = np.clip(_field(shape, seed, 10142, 5.0) * 0.56 + x * 0.30 + y * 0.18, 0, 1)
    dots = (d < (0.11 + tone * 0.22)).astype(np.float32)
    rosette = np.clip(1.0 - np.abs(np.sin((x * 21.0 - y * 17.0 + tone) * np.pi)) * 18.0, 0, 1)
    return np.clip(dots * 0.82 + rosette * 0.34, 0, 1), tone


def spec_owner_halftone_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    dots, tone = _wave3_halftone(shape, seed)
    return _spec_from_fields(shape, mask, 30 + dots * 158, 116 - dots * 56 + tone * 30, 18 + dots * 118, sm)


def paint_owner_halftone_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    dots, tone = _wave3_halftone(shape, seed)
    cmy = _stack_rgb(0.86 * dots, 0.12 + tone * 0.42, 0.72 * (1.0 - tone) * dots + 0.08, shape)
    paper = _stack_rgb(0.08 + tone * 0.12, 0.075 + tone * 0.10, 0.065 + tone * 0.08, shape)
    effect = np.clip(paper + cmy * dots[:, :, None] * 0.82, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.035).astype(np.float32))


def _wave3_chromatic(shape, seed):
    x, y = _xy(shape)
    edge = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 32.0 + y * 9.0 + _seed(seed, 10150)) * np.pi)) * 22.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -13.0 + y * 41.0 + _field(shape, seed, 10151, 2.0)) * np.pi)) * 24.0, 0, 1),
    )
    fringe = _micro_lines(shape, seed, 10152, 251.0, 37.0)
    return np.clip(edge + fringe * 0.32, 0, 1)


def spec_owner_chromatic_aberration_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    edge = _wave3_chromatic(shape, seed)
    return _spec_from_fields(shape, mask, 32 + edge * 156, 102 - edge * 54, 24 + edge * 126, sm)


def paint_owner_chromatic_aberration_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    edge = _wave3_chromatic(shape, seed)
    red = np.roll(edge, 8, axis=1)
    green = edge
    blue = np.roll(edge, -8, axis=1)
    effect = _stack_rgb(0.025 + red * 0.78, 0.030 + green * 0.70, 0.040 + blue * 0.86, shape)
    effect = np.clip(effect + _soften(edge, 2)[:, :, None] * np.array([0.06, 0.05, 0.08], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.025).astype(np.float32))


def _wave3_refraction(shape, seed):
    x, y = _xy(shape)
    facet = np.mod(np.floor((x + y * 0.4) * 16.0) + np.floor((x * -0.3 + y) * 14.0), 5.0) / 4.0
    caustic = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 23.0 + y * 31.0 + _seed(seed, 10160)) * np.pi)) * 18.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -29.0 + y * 17.0 + _field(shape, seed, 10161, 2.0)) * np.pi)) * 18.0, 0, 1),
    )
    return np.clip(facet * 0.36 + caustic * 0.78, 0, 1)


def spec_owner_refraction_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    prism = _wave3_refraction(shape, seed)
    return _spec_from_fields(shape, mask, 40 + prism * 174, 58 - prism * 28, 42 + prism * 154, sm)


def paint_owner_refraction_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    prism = _wave3_refraction(shape, seed)
    color = _rgb_cycle(prism * 0.72 + _seed(seed, 10162), 0.70, 0.90)
    glass = _stack_rgb(0.035, 0.055, 0.070, shape)
    effect = np.clip(glass + color * prism[:, :, None] * 0.78 + _soften(prism, 2)[:, :, None] * 0.08, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.80), mask, bb, 0.035).astype(np.float32))


def _wave3_holo(shape, seed):
    x, y = _xy(shape)
    facets = np.mod(np.floor(x * 38.0 + y * 12.0) + np.floor(y * 31.0 - x * 8.0), 7.0) / 6.0
    shear = np.clip(1.0 - np.abs(np.sin((x * 71.0 + y * 23.0 + _field(shape, seed, 10170, 3.0)) * np.pi)) * 26.0, 0, 1)
    glitter = (_hash_noise(shape, seed, 10171) > 0.982).astype(np.float32)
    return np.clip(facets * 0.55 + shear * 0.58 + _soften(glitter, 1) * 0.28, 0, 1), facets


def spec_owner_holographic_wrap_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    holo, facets = _wave3_holo(shape, seed)
    return _spec_from_fields(shape, mask, 56 + holo * 184, 36 - holo * 16 + facets * 32, 60 + holo * 160, sm)


def paint_owner_holographic_wrap_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    holo, facets = _wave3_holo(shape, seed)
    color = _rgb_cycle(facets * 1.1 + holo * 0.22 + _seed(seed, 10172), 1.0, 0.96)
    foil = _stack_rgb(0.08, 0.08, 0.10, shape)
    effect = np.clip(foil + color * (0.20 + holo[:, :, None] * 0.82), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.025).astype(np.float32))


def _wave3_double_exposure(shape, seed):
    x, y = _xy(shape)
    portrait = np.exp(-(((x - 0.36) / 0.18) ** 2 + ((y - 0.50) / 0.34) ** 2))
    landscape = np.clip(1.0 - np.abs(np.sin((y * 21.0 + _field(shape, seed, 10180, 2.0)) * np.pi)) * 13.0, 0, 1)
    city = np.clip(1.0 - np.abs(np.sin((x * 37.0 + y * 2.0 + _seed(seed, 10181)) * np.pi)) * 25.0, 0, 1)
    return np.clip(portrait * 0.68 + landscape * 0.54 + city * 0.28, 0, 1), portrait


def spec_owner_double_exposure_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    exposure, portrait = _wave3_double_exposure(shape, seed)
    return _spec_from_fields(shape, mask, 34 + exposure * 152, 122 - portrait * 72 + exposure * 20, 22 + exposure * 128, sm)


def paint_owner_double_exposure_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    exposure, portrait = _wave3_double_exposure(shape, seed)
    sepia = _stack_rgb(0.12 + exposure * 0.42, 0.095 + exposure * 0.28, 0.075 + exposure * 0.18, shape)
    cyan = _stack_rgb(0.02, 0.12 + portrait * 0.28, 0.20 + exposure * 0.28, shape)
    effect = np.clip(sepia * 0.62 + cyan * 0.70 + _soften(exposure, 2)[:, :, None] * 0.08, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.035).astype(np.float32))


def _wave3_xray(shape, seed):
    x, y = _xy(shape)
    spine = np.exp(-((x - 0.50) ** 2) / 0.00034)
    ribs = np.zeros(shape, dtype=np.float32)
    for i in range(9):
        cy = 0.12 + i * 0.087
        ribs = np.maximum(ribs, np.exp(-((np.sqrt(((x - 0.5) / 0.42) ** 2 + ((y - cy) / 0.055) ** 2) - 1.0) ** 2) / 0.008) * (0.80 - i * 0.035))
    noise = _micro_lines(shape, seed, 10190, 201.0, 97.0)
    return np.clip(spine * 0.70 + ribs * 0.74 + noise * 0.18, 0, 1)


def spec_owner_x_ray_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    bone = _wave3_xray(shape, seed)
    return _spec_from_fields(shape, mask, 28 + bone * 168, 108 - bone * 62, 34 + bone * 132, sm)


def paint_owner_x_ray_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    bone = _wave3_xray(shape, seed)
    plate = _stack_rgb(0.014, 0.030 + bone * 0.08, 0.055 + bone * 0.16, shape)
    glow = _stack_rgb(0.40, 0.78, 0.88, shape) * bone[:, :, None] * 0.62
    effect = np.clip(plate + glow + _soften(bone, 2)[:, :, None] * np.array([0.04, 0.12, 0.18], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.025).astype(np.float32))


def _wave4_forge(shape, seed):
    x, y = _xy(shape)
    hammer = np.mod(np.floor(x * 34.0 + y * 4.0) + np.floor(y * 27.0 - x * 3.0), 4.0) / 3.0
    seams = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 21.0 + y * 33.0 + _seed(seed, 10200)) * np.pi)) * 19.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -37.0 + y * 19.0 + _field(shape, seed, 10201, 2.4)) * np.pi)) * 20.0, 0, 1),
    )
    scale = _field(shape, seed, 10202, 10.0)
    return np.clip(hammer * 0.24 + seams * 0.88 + scale * 0.18, 0, 1), seams


def spec_owner_demon_forge_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    metal, heat = _wave4_forge(shape, seed)
    return _spec_from_fields(shape, mask, 46 + metal * 150 + heat * 84, 150 - heat * 116 + metal * 34, 18 + heat * 150, sm)


def paint_owner_demon_forge_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    metal, heat = _wave4_forge(shape, seed)
    iron = _stack_rgb(0.045 + metal * 0.16, 0.035 + metal * 0.10, 0.030 + metal * 0.08, shape)
    molten = _stack_rgb(1.0, 0.25 + heat * 0.34, 0.015, shape) * heat[:, :, None] * 0.80
    effect = np.clip(iron + molten + _soften(heat, 2)[:, :, None] * np.array([0.14, 0.04, 0.00], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.03).astype(np.float32))


def _wave4_iron_maiden(shape, seed):
    x, y = _xy(shape)
    rivet_grid = np.sqrt((np.mod(x * 22.0 + _seed(seed, 10210), 1.0) - 0.5) ** 2 + (np.mod(y * 18.0 + _seed(seed, 10211), 1.0) - 0.5) ** 2)
    rivets = (rivet_grid < 0.115).astype(np.float32)
    spikes = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 18.0 + y * 51.0) * np.pi)) * 24.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -47.0 + y * 16.0 + _seed(seed, 10212)) * np.pi)) * 25.0, 0, 1),
    )
    pits = (_hash_noise(shape, seed, 10213) > 0.975).astype(np.float32)
    return np.clip(rivets * 0.68 + spikes * 0.58 + pits * 0.32, 0, 1), pits


def spec_owner_iron_maiden_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    steel, pits = _wave4_iron_maiden(shape, seed)
    return _spec_from_fields(shape, mask, 42 + steel * 168, 164 - steel * 92 + pits * 48, 16 + steel * 110, sm)


def paint_owner_iron_maiden_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    steel, pits = _wave4_iron_maiden(shape, seed)
    metal = _stack_rgb(0.090 + steel * 0.24, 0.082 + steel * 0.20, 0.078 + steel * 0.18, shape)
    rust = _stack_rgb(0.36, 0.11, 0.035, shape) * pits[:, :, None] * 0.38
    effect = np.clip(metal + rust, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.04).astype(np.float32))


def _wave4_shadow(shape, seed):
    x, y = _xy(shape)
    rifts = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 11.0 + y * 27.0 + _field(shape, seed, 10220, 4.0) * 2.8) * np.pi)) * 17.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -19.0 + y * 13.0 + _seed(seed, 10221)) * np.pi)) * 21.0, 0, 1) * 0.66,
    )
    void = _field(shape, seed, 10222, 12.0)
    dust = (_hash_noise(shape, seed, 10223) > 0.988).astype(np.float32)
    return np.clip(rifts * 0.62 + void * 0.20 + _soften(dust, 1) * 0.22, 0, 1)


def spec_owner_shadow_realm_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    shadow = _wave4_shadow(shape, seed)
    return _spec_from_fields(shape, mask, 14 + shadow * 148, 188 - shadow * 104, 16 + shadow * 112, sm)


def paint_owner_shadow_realm_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    shadow = _wave4_shadow(shape, seed)
    abyss = _stack_rgb(0.006 + shadow * 0.026, 0.006 + shadow * 0.018, 0.020 + shadow * 0.090, shape)
    violet_rift = _stack_rgb(0.18, 0.02, 0.42, shape) * shadow[:, :, None] * 0.32
    effect = np.clip(abyss + violet_rift, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.02).astype(np.float32))


def _wave4_death_metal(shape, seed):
    x, y = _xy(shape)
    shards = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 49.0 + y * 17.0 + _seed(seed, 10230)) * np.pi)) * 23.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -31.0 + y * 61.0 + _field(shape, seed, 10231, 2.0)) * np.pi)) * 21.0, 0, 1),
    )
    chrome_scratches = _micro_lines(shape, seed, 10232, 301.0, 113.0)
    soot = _field(shape, seed, 10233, 7.0)
    return np.clip(shards * 0.66 + chrome_scratches * 0.42 + soot * 0.16, 0, 1), soot


def spec_owner_death_metal_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    shards, soot = _wave4_death_metal(shape, seed)
    return _spec_from_fields(shape, mask, 50 + shards * 174, 126 - shards * 82 + soot * 44, 18 + shards * 120, sm)


def paint_owner_death_metal_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    shards, soot = _wave4_death_metal(shape, seed)
    black = _stack_rgb(0.025 + soot * 0.08, 0.022 + soot * 0.06, 0.024 + soot * 0.06, shape)
    steel = _stack_rgb(0.50, 0.48, 0.44, shape) * shards[:, :, None] * 0.42
    red = _stack_rgb(0.44, 0.015, 0.012, shape) * _soften(shards, 1)[:, :, None] * 0.16
    effect = np.clip(black + steel + red, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.035).astype(np.float32))


def _wave4_fisheye(shape, seed):
    x, y = _xy(shape)
    ax = x - 0.5
    ay = y - 0.5
    r = np.sqrt(ax * ax + ay * ay)
    rings = np.clip(1.0 - np.abs(np.sin((r * 38.0 + _seed(seed, 10240)) * np.pi)) * 10.0, 0, 1)
    warp_grid = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x / (1.0 + r * 2.5) * 36.0) * np.pi)) * 22.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((y / (1.0 + r * 2.5) * 36.0) * np.pi)) * 22.0, 0, 1),
    )
    lens_glare = np.exp(-(((x - 0.30) / 0.09) ** 2 + ((y - 0.24) / 0.06) ** 2))
    return np.clip(rings * 0.44 + warp_grid * 0.54 + lens_glare * 0.50, 0, 1), r


def spec_owner_fish_eye_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    lens, r = _wave4_fisheye(shape, seed)
    return _spec_from_fields(shape, mask, 44 + lens * 168, 42 - lens * 18 + r * 58, 54 + lens * 154, sm)


def paint_owner_fish_eye_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    lens, r = _wave4_fisheye(shape, seed)
    glass = _stack_rgb(0.035 + r * 0.04, 0.065 + lens * 0.16, 0.090 + lens * 0.24, shape)
    blue = _stack_rgb(0.12, 0.30, 0.52, shape) * lens[:, :, None] * 0.38
    effect = np.clip(glass + blue, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.04).astype(np.float32))


def _wave4_embossed(shape, seed):
    x, y = _xy(shape)
    relief = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 22.0 + y * 35.0 + _field(shape, seed, 10250, 2.0)) * np.pi)) * 18.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -28.0 + y * 19.0 + _seed(seed, 10251)) * np.pi)) * 20.0, 0, 1),
    )
    bevel = np.clip(np.roll(relief, 2, 0) - np.roll(relief, -2, 1), -1, 1)
    grain = _micro_lines(shape, seed, 10252, 151.0, 151.0)
    return np.clip(relief + grain * 0.22, 0, 1), bevel


def spec_owner_embossed_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    relief, bevel = _wave4_embossed(shape, seed)
    return _spec_from_fields(shape, mask, 46 + relief * 156, 88 - bevel * 38 + relief * 18, 32 + relief * 132, sm)


def paint_owner_embossed_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    relief, bevel = _wave4_embossed(shape, seed)
    base = _stack_rgb(0.26 + relief * 0.26 + bevel * 0.12, 0.25 + relief * 0.24 + bevel * 0.10, 0.24 + relief * 0.22 + bevel * 0.08, shape)
    shadow = _stack_rgb(0.02, 0.018, 0.015, shape) * np.clip(-bevel, 0, 1)[:, :, None] * 0.52
    effect = np.clip(base - shadow, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.05).astype(np.float32))


def _wave4_necrotic(shape, seed):
    x, y = _xy(shape)
    tissue = _field(shape, seed, 10260, 11.0)
    veins = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 71.0 + y * 18.0 + tissue * 3.4) * np.pi)) * 22.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -24.0 + y * 63.0 + tissue * 2.8) * np.pi)) * 24.0, 0, 1),
    )
    rot = (_hash_noise(shape, seed, 10261) > 0.978).astype(np.float32)
    return np.clip(tissue * 0.26 + veins * 0.70 + _soften(rot, 2) * 0.26, 0, 1), tissue


def spec_owner_necrotic_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    rot, tissue = _wave4_necrotic(shape, seed)
    return _spec_from_fields(shape, mask, 18 + rot * 156, 188 - rot * 94 + tissue * 34, 16 + rot * 120, sm)


def paint_owner_necrotic_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    rot, tissue = _wave4_necrotic(shape, seed)
    bruise = _stack_rgb(0.10 + tissue * 0.16, 0.055 + tissue * 0.10, 0.080 + tissue * 0.18, shape)
    sick = _stack_rgb(0.20, 0.48, 0.10, shape) * rot[:, :, None] * 0.52
    effect = np.clip(bruise + sick, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.03).astype(np.float32))


def _wave4_graveyard(shape, seed):
    x, y = _xy(shape)
    fog = _field(shape, seed, 10270, 8.0)
    stones = np.zeros(shape, dtype=np.float32)
    for i in range(12):
        cx = 0.05 + i * 0.083 + (_seed(seed, 10271 + i) - 0.5) * 0.025
        top = np.exp(-(((x - cx) / 0.022) ** 2 + ((y - 0.62) / 0.080) ** 2))
        stem = ((np.abs(x - cx) < 0.020) & (y > 0.62) & (y < 0.88)).astype(np.float32)
        stones = np.maximum(stones, np.maximum(top, stem) * (0.65 + (i % 3) * 0.10))
    moon = np.exp(-(((x - 0.82) / 0.11) ** 2 + ((y - 0.18) / 0.11) ** 2))
    return np.clip(stones * 0.62 + fog * 0.30 + moon * 0.44, 0, 1), fog


def spec_owner_graveyard_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    grave, fog = _wave4_graveyard(shape, seed)
    return _spec_from_fields(shape, mask, 24 + grave * 142, 164 - grave * 76 + fog * 34, 18 + grave * 112, sm)


def paint_owner_graveyard_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    grave, fog = _wave4_graveyard(shape, seed)
    night = _stack_rgb(0.018 + fog * 0.05, 0.028 + fog * 0.08, 0.055 + fog * 0.13, shape)
    moon = _stack_rgb(0.36, 0.48, 0.60, shape) * grave[:, :, None] * 0.42
    moss = _stack_rgb(0.03, 0.14, 0.04, shape) * (grave > 0.58)[:, :, None] * 0.25
    effect = np.clip(night + moon + moss, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.035).astype(np.float32))


def _wave4_voodoo(shape, seed):
    x, y = _xy(shape)
    hex_grid = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 27.0 + y * 15.0 + _seed(seed, 10280)) * np.pi)) * 20.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -27.0 + y * 15.0 + _seed(seed, 10281)) * np.pi)) * 20.0, 0, 1),
    )
    pins = (_hash_noise(shape, seed, 10282) > 0.988).astype(np.float32)
    smoke = _field(shape, seed, 10283, 13.0)
    scratch = _micro_lines(shape, seed, 10284, 253.0, 61.0)
    return np.clip(hex_grid * 0.52 + _soften(pins, 2) * 0.48 + smoke * 0.18 + scratch * 0.26, 0, 1)


def spec_owner_voodoo_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    hexes = _wave4_voodoo(shape, seed)
    return _spec_from_fields(shape, mask, 22 + hexes * 168, 176 - hexes * 104, 18 + hexes * 138, sm)


def paint_owner_voodoo_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    hexes = _wave4_voodoo(shape, seed)
    cloth = _stack_rgb(0.030 + hexes * 0.08, 0.020 + hexes * 0.05, 0.042 + hexes * 0.10, shape)
    curse = _stack_rgb(0.44, 0.02, 0.66, shape) * hexes[:, :, None] * 0.42
    green = _stack_rgb(0.05, 0.42, 0.06, shape) * _soften(hexes, 1)[:, :, None] * 0.16
    effect = np.clip(cloth + curse + green, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.025).astype(np.float32))


def _wave4_gargoyle(shape, seed):
    x, y = _xy(shape)
    carved = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 23.0 + y * 37.0 + _field(shape, seed, 10290, 2.2) * 2.1) * np.pi)) * 18.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -31.0 + y * 19.0 + _seed(seed, 10291)) * np.pi)) * 22.0, 0, 1),
    )
    rain = np.clip(1.0 - np.abs(np.sin((x * 5.0 + y * 118.0 + _seed(seed, 10292)) * np.pi)) * 30.0, 0, 1)
    pits = (_hash_noise(shape, seed, 10293) > 0.975).astype(np.float32)
    stone = _field(shape, seed, 10294, 12.0)
    return np.clip(carved * 0.62 + rain * 0.26 + _soften(pits, 1) * 0.34, 0, 1), stone


def spec_owner_gargoyle_v2(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    cuts, stone = _wave4_gargoyle(shape, seed)
    return _spec_from_fields(shape, mask, 30 + cuts * 154 + stone * 36, 178 - cuts * 102 + stone * 28, 18 + cuts * 112, sm)


def paint_owner_gargoyle_v2(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    cuts, stone = _wave4_gargoyle(shape, seed)
    limestone = _stack_rgb(0.14 + stone * 0.22 + cuts * 0.14, 0.15 + stone * 0.22 + cuts * 0.13, 0.13 + stone * 0.20 + cuts * 0.10, shape)
    moss = _stack_rgb(0.02, 0.18, 0.04, shape) * np.clip(stone - 0.56, 0, 1)[:, :, None] * 0.34
    white_edge = _stack_rgb(0.52, 0.55, 0.48, shape) * cuts[:, :, None] * 0.18
    effect = np.clip(limestone + moss + white_edge, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.04).astype(np.float32))


# SPB-67 scorecard pass: faster, denser Effects & Vision source renderers.
# These replace the weakest audit outputs without using generic shared-wrapper rebuilds.


def _ev67_scan_grain(shape, seed, salt):
    x, y = _xy(shape)
    fine = _micro_lines(shape, seed, salt, 360.0, 121.0)
    dust = (_hash_noise(shape, seed, salt + 11) > 0.958).astype(np.float32)
    scan = np.clip(1.0 - np.abs(np.sin((y * 720.0 + _seed(seed, salt + 23)) * np.pi)) * 9.0, 0, 1)
    return np.clip(fine * 0.42 + _soften(dust, 1) * 0.36 + scan * 0.24, 0, 1)


def _ev67_negative(shape, seed):
    x, y = _xy(shape)
    frame = np.clip((1.0 - x) ** 7.0 * 0.55 + y ** 9.0 * 0.34 + (1.0 - y) ** 12.0 * 0.18, 0, 1)
    scratches = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 73.0 + y * 11.0 + _seed(seed, 13101)) * np.pi)) * 30.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -29.0 + y * 191.0 + _seed(seed, 13102)) * np.pi)) * 18.0, 0, 1) * 0.45,
    )
    emulsion = _ev67_scan_grain(shape, seed, 13103)
    return np.clip(frame + scratches * 0.58 + emulsion * 0.52, 0, 1)


def spec_owner_negative_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    neg = _ev67_negative(shape, seed)
    return _spec_from_fields(shape, mask, 42 + neg * 178, 142 - neg * 98, 22 + neg * 152, sm)


def paint_owner_negative_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    neg = _ev67_negative(shape, seed)
    inverted = np.clip(1.0 - base * 0.66, 0, 1)
    cyan = _stack_rgb(0.02 + neg * 0.18, 0.38 + neg * 0.30, 0.56 + neg * 0.16, shape)
    amber = _stack_rgb(0.92, 0.43, 0.06, shape) * neg[:, :, None] * 0.36
    effect = np.clip(inverted * 0.46 + cyan * 0.50 + amber, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.03).astype(np.float32))


def _ev67_polarized(shape, seed):
    x, y = _xy(shape)
    stress = np.clip(
        _field(shape, seed, 13200, 15.0) * 0.52
        + np.sin((x * 8.5 - y * 6.0 + _seed(seed, 13201)) * np.pi) * 0.18
        + np.sin((x * -5.0 + y * 10.5 + _seed(seed, 13202)) * np.pi) * 0.14
        + 0.32,
        0,
        1,
    )
    rings = np.clip(1.0 - np.abs(np.sin((stress * 38.0 + x * 4.0 - y * 3.0) * np.pi)) * 8.0, 0, 1)
    stress_cracks = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 61.0 + y * 17.0 + stress * 3.0) * np.pi)) * 24.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -23.0 + y * 67.0 + stress * 2.4) * np.pi)) * 24.0, 0, 1),
    )
    fine = _micro_lines(shape, seed, 13203, 310.0, 94.0)
    return stress, np.clip(rings + stress_cracks * 0.42 + fine * 0.22, 0, 1)


def spec_owner_polarized_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    stress, bands = _ev67_polarized(shape, seed)
    return _spec_from_fields(shape, mask, 50 + bands * 188, 68 - bands * 38 + stress * 34, 46 + bands * 164, sm)


def paint_owner_polarized_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    stress, bands = _ev67_polarized(shape, seed)
    color = _rgb_cycle(stress * 1.05 + bands * 0.16 + _seed(seed, 13204), 1.0, 1.0)
    dark_lens = _stack_rgb(0.010, 0.012, 0.018, shape)
    effect = np.clip(dark_lens + color * (0.22 + bands[:, :, None] * 0.92), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.02).astype(np.float32))


def _ev67_halftone(shape, seed):
    x, y = _xy(shape)
    angle = 0.62
    xr = x * np.cos(angle) - y * np.sin(angle)
    yr = x * np.sin(angle) + y * np.cos(angle)
    tone = np.clip(_field(shape, seed, 13300, 7.0) * 0.56 + x * 0.25 + y * 0.18, 0, 1)
    gx = np.abs(np.sin((xr * 92.0 + _seed(seed, 13301)) * np.pi))
    gy = np.abs(np.sin((yr * 92.0 + _seed(seed, 13302)) * np.pi))
    dots = np.clip((1.0 - np.maximum(gx, gy)) * (2.4 + tone * 2.2), 0, 1)
    rosette = np.clip(1.0 - np.abs(np.sin((x * 31.0 - y * 27.0 + tone * 1.8) * np.pi)) * 18.0, 0, 1)
    speck = (_hash_noise(shape, seed, 13303) > 0.975).astype(np.float32)
    return np.clip(dots + rosette * 0.32 + _soften(speck, 1) * 0.22, 0, 1), tone


def spec_owner_halftone_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    dots, tone = _ev67_halftone(shape, seed)
    return _spec_from_fields(shape, mask, 38 + dots * 170, 124 - dots * 70 + tone * 20, 22 + dots * 136, sm)


def paint_owner_halftone_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    dots, tone = _ev67_halftone(shape, seed)
    cyan = np.clip(dots * (0.85 - tone * 0.20), 0, 1)
    magenta = np.clip(dots * (0.36 + tone * 0.70), 0, 1)
    yellow = np.clip(dots * (0.70 + (1.0 - tone) * 0.34), 0, 1)
    ink = np.stack([magenta + yellow * 0.35, yellow + cyan * 0.20, cyan + magenta * 0.28], axis=2)
    paper = _stack_rgb(0.045 + tone * 0.10, 0.040 + tone * 0.08, 0.036 + tone * 0.07, shape)
    effect = np.clip(paper + ink * 0.86, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.025).astype(np.float32))


def _ev67_chromatic(shape, seed):
    x, y = _xy(shape)
    warp = _field(shape, seed, 13400, 5.0)
    contour = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 55.0 + y * 13.0 + warp * 3.2) * np.pi)) * 22.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -19.0 + y * 61.0 + warp * 2.7) * np.pi)) * 22.0, 0, 1),
    )
    fringe = _ev67_scan_grain(shape, seed, 13401)
    return np.clip(contour + fringe * 0.42, 0, 1), warp


def spec_owner_chromatic_aberration_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    edge, warp = _ev67_chromatic(shape, seed)
    return _spec_from_fields(shape, mask, 38 + edge * 172, 104 - edge * 66 + warp * 18, 26 + edge * 148, sm)


def paint_owner_chromatic_aberration_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    edge, warp = _ev67_chromatic(shape, seed)
    red = np.roll(edge, 14, axis=1)
    green = np.roll(edge, -5, axis=0)
    blue = np.roll(edge, -14, axis=1)
    base = _stack_rgb(0.020 + warp * 0.025, 0.024 + warp * 0.025, 0.032 + warp * 0.030, shape)
    effect = np.clip(base + np.stack([red * 0.86, green * 0.78, blue * 0.96], axis=2), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.02).astype(np.float32))


def _ev67_refraction(shape, seed):
    x, y = _xy(shape)
    facet_a = np.mod(np.floor((x * 28.0 + y * 9.0)) + np.floor((y * 24.0 - x * 7.0)), 9.0) / 8.0
    facet_b = np.mod(np.floor((x * -15.0 + y * 32.0)) + np.floor((x * 19.0 + y * 11.0)), 7.0) / 6.0
    caustic = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 47.0 + y * 29.0 + _seed(seed, 13500)) * np.pi)) * 19.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -37.0 + y * 43.0 + _field(shape, seed, 13501, 3.0) * 2.8) * np.pi)) * 19.0, 0, 1),
    )
    glitter = (_hash_noise(shape, seed, 13502) > 0.982).astype(np.float32)
    return np.clip(facet_a * 0.30 + facet_b * 0.26 + caustic * 0.82 + _soften(glitter, 1) * 0.30, 0, 1)


def spec_owner_refraction_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    prism = _ev67_refraction(shape, seed)
    return _spec_from_fields(shape, mask, 48 + prism * 188, 58 - prism * 34, 48 + prism * 172, sm)


def paint_owner_refraction_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    prism = _ev67_refraction(shape, seed)
    color = _rgb_cycle(prism * 0.95 + _seed(seed, 13503), 0.92, 1.0)
    glass = _stack_rgb(0.025, 0.042, 0.060, shape)
    effect = np.clip(glass + color * (0.16 + prism[:, :, None] * 0.92), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.025).astype(np.float32))


def _ev67_film_burn(shape, seed):
    x, y = _xy(shape)
    bloom = np.clip((1.0 - x) ** 4.5 * 0.76 + (1.0 - y) ** 8.0 * 0.24 + _field(shape, seed, 13600, 9.0) * 0.22, 0, 1)
    scorch = np.clip(1.0 - np.abs(np.sin((x * 19.0 + y * 7.0 + bloom * 3.0) * np.pi)) * 14.0, 0, 1)
    sprocket = np.clip(1.0 - np.abs(np.sin((y * 22.0 + _seed(seed, 13601)) * np.pi)) * 18.0, 0, 1) * (x < 0.08)
    return np.clip(bloom + scorch * 0.36 + sprocket * 0.55 + _ev67_scan_grain(shape, seed, 13602) * 0.22, 0, 1)


def spec_owner_film_burn_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    burn = _ev67_film_burn(shape, seed)
    return _spec_from_fields(shape, mask, 36 + burn * 166, 154 - burn * 92, 24 + burn * 132, sm)


def paint_owner_film_burn_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    burn = _ev67_film_burn(shape, seed)
    ember = _stack_rgb(0.20 + burn * 0.82, 0.055 + burn * 0.34, 0.018 + burn * 0.045, shape)
    gold = _stack_rgb(0.92, 0.54, 0.08, shape) * np.clip(burn - 0.35, 0, 1)[:, :, None] * 0.55
    effect = np.clip(ember + gold, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.025).astype(np.float32))


def _ev67_long_exposure(shape, seed):
    x, y = _xy(shape)
    lanes = np.zeros(shape, dtype=np.float32)
    for i in range(9):
        slope = -0.38 + i * 0.095
        center = 0.08 + i * 0.105 + (_seed(seed, 13700 + i) - 0.5) * 0.035
        line = np.clip(1.0 - np.abs((y - (center + x * slope)) / (0.004 + (i % 3) * 0.002)), 0, 1)
        lanes = np.maximum(lanes, line * (0.55 + (i % 4) * 0.12))
    star = (_hash_noise(shape, seed, 13720) > 0.992).astype(np.float32)
    haze = _field(shape, seed, 13721, 10.0)
    return np.clip(lanes + _soften(star, 1) * 0.42 + haze * 0.16, 0, 1), haze


def spec_owner_long_exposure_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    lanes, haze = _ev67_long_exposure(shape, seed)
    return _spec_from_fields(shape, mask, 34 + lanes * 178, 130 - lanes * 88 + haze * 24, 26 + lanes * 150, sm)


def paint_owner_long_exposure_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    lanes, haze = _ev67_long_exposure(shape, seed)
    color = _rgb_cycle(haze * 0.75 + lanes * 0.20 + _seed(seed, 13730), 0.95, 1.0)
    night = _stack_rgb(0.012 + haze * 0.025, 0.018 + haze * 0.030, 0.035 + haze * 0.060, shape)
    effect = np.clip(night + color * lanes[:, :, None] * 0.96, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.02).astype(np.float32))


def _ev67_solarization(shape, seed):
    x, y = _xy(shape)
    tone = np.clip(_field(shape, seed, 13800, 12.0) * 0.54 + x * 0.28 + (1.0 - y) * 0.18, 0, 1)
    contour = np.clip(1.0 - np.abs(np.sin((tone * 19.0 + x * 2.0 - y * 1.4) * np.pi)) * 8.0, 0, 1)
    halo = np.clip(1.0 - np.abs(tone - 0.52) * 7.0, 0, 1)
    return np.clip(contour * 0.72 + halo * 0.44 + _ev67_scan_grain(shape, seed, 13801) * 0.22, 0, 1), tone


def spec_owner_solarization_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    contour, tone = _ev67_solarization(shape, seed)
    return _spec_from_fields(shape, mask, 36 + contour * 172, 136 - contour * 88 + tone * 28, 24 + contour * 146, sm)


def paint_owner_solarization_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    contour, tone = _ev67_solarization(shape, seed)
    color = _rgb_cycle(0.18 + tone * 0.82 + contour * 0.12, 0.88, 0.92)
    dark = _stack_rgb(0.018 + tone * 0.05, 0.020 + tone * 0.035, 0.026 + tone * 0.06, shape)
    effect = np.clip(dark + color * (0.18 + contour[:, :, None] * 0.78), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.02).astype(np.float32))


def _ev67_graveyard(shape, seed):
    work_shape = _bounded_shape(shape, 1024)
    if work_shape != tuple(shape):
        detail, stones, moon, fog = _ev67_graveyard(work_shape, seed)
        detail = _fit2(detail, shape)
        scratch = _micro_lines(shape, seed, 13992, 323.0, -41.0)
        grit = (_hash_noise(shape, seed, 13991) > 0.935).astype(np.float32)
        return np.clip(detail + scratch * 0.34 + grit * 0.22, 0, 1), _fit2(stones, shape), _fit2(moon, shape), _fit2(fog, shape)
    x, y = _xy(shape)
    moon = np.exp(-(((x - 0.78) / 0.135) ** 2 + ((y - 0.18) / 0.135) ** 2))
    stones = np.zeros(shape, dtype=np.float32)
    for i in range(22):
        cx = 0.028 + (i * 0.053) % 0.94 + (_seed(seed, 13900 + i) - 0.5) * 0.022
        cy = 0.48 + ((i * 7) % 9) * 0.045 + (_seed(seed, 13940 + i) - 0.5) * 0.024
        lean = (x - cx) + (y - cy) * (_seed(seed, 13960 + i) - 0.5) * 0.22
        top = np.exp(-((lean / 0.014) ** 2 + ((y - cy) / 0.043) ** 2))
        stem = ((np.abs(lean) < 0.012) & (y > cy) & (y < cy + 0.13)).astype(np.float32)
        crack = np.clip(1.0 - np.abs(np.sin((x * (70 + i) + y * (23 + i * 3)) * np.pi)) * 24.0, 0, 1)
        stones = np.maximum(stones, np.maximum(top, stem) * (0.48 + (i % 4) * 0.11) + crack * stem * 0.18)
    fence = np.clip(1.0 - np.abs(np.sin((x * 58.0 + _seed(seed, 13970)) * np.pi)) * 32.0, 0, 1) * (y > 0.60)
    grass = np.maximum(
        _micro_lines(shape, seed, 13971, 177.0, 47.0),
        _micro_lines(shape, seed, 13972, -151.0, 69.0),
    ) * np.clip((y - 0.38) * 2.2, 0, 1)
    fog = np.clip(_field(shape, seed, 13980, 18.0) * 0.44 + np.sin((x * 7.0 + y * 4.0) * np.pi) * 0.08 + 0.20, 0, 1)
    fireflies = (_hash_noise(shape, seed, 13990) > 0.978).astype(np.float32)
    grit = (_hash_noise(shape, seed, 13991) > 0.915).astype(np.float32)
    scratch = _micro_lines(shape, seed, 13992, 323.0, -41.0)
    detail = np.clip(stones * 0.70 + fence * 0.32 + grass * 0.48 + scratch * 0.22 + moon * 0.42 + _soften(fireflies, 1) * 0.50 + grit * 0.26 + fog * 0.22, 0, 1)
    return detail, stones, moon, fog


def spec_owner_graveyard_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, stones, moon, fog = _ev67_graveyard(shape, seed)
    return _spec_from_fields(shape, mask, 32 + detail * 170, 164 - stones * 92 - moon * 42 + fog * 22, 20 + detail * 142, sm)


def paint_owner_graveyard_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, stones, moon, fog = _ev67_graveyard(shape, seed)
    night = _stack_rgb(0.014 + fog * 0.045, 0.022 + fog * 0.080, 0.048 + fog * 0.145, shape)
    stone = _stack_rgb(0.23, 0.27, 0.25, shape) * stones[:, :, None] * 0.58
    glow = _stack_rgb(0.35, 0.56, 0.62, shape) * moon[:, :, None] * 0.48
    moss = _stack_rgb(0.03, 0.32, 0.09, shape) * np.clip(detail - 0.38, 0, 1)[:, :, None] * 0.24
    lichen = _stack_rgb(0.05, 0.18, 0.08, shape) * detail[:, :, None] * 0.08
    effect = np.clip(night + stone + glow + moss + lichen, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.025).astype(np.float32))


def _ev67_reaper(shape, seed):
    work_shape = _bounded_shape(shape, 1024)
    if work_shape != tuple(shape):
        detail, blade, hood, smoke = _ev67_reaper(work_shape, seed)
        detail = _fit2(detail, shape)
        smoke = _fit2(smoke, shape)
        veil = _micro_lines(shape, seed, 14005, -143.0, 119.0)
        sparks = (_hash_noise(shape, seed, 14006) > 0.982).astype(np.float32)
        return np.clip(detail + veil * 0.20 + sparks * 0.12, 0, 1), _fit2(blade, shape), _fit2(hood, shape), np.clip(smoke + veil * 0.20, 0, 1)
    x, y = _xy(shape)
    blade = np.zeros(shape, dtype=np.float32)
    for cx, cy, rad, wid, power in ((0.28, 0.38, 0.34, 0.0045, 0.90), (0.63, 0.57, 0.26, 0.0040, 0.62), (0.47, 0.74, 0.41, 0.0035, 0.42)):
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        gate = np.clip(1.0 - np.abs((x - cx) * 0.85 + (y - cy) * 0.34) / 0.54, 0, 1)
        blade = np.maximum(blade, np.clip(1.0 - np.abs(d - rad) / wid, 0, 1) * power * gate)
    hood = np.exp(-(((x - 0.50) / 0.18) ** 2 + ((y - 0.34) / 0.24) ** 2))
    ribs = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 67.0 + y * 23.0 + _seed(seed, 14000)) * np.pi)) * 26.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -31.0 + y * 87.0 + _field(shape, seed, 14001, 2.0)) * np.pi)) * 28.0, 0, 1),
    )
    cloak = np.maximum(_micro_lines(shape, seed, 14004, 211.0, -63.0), _micro_lines(shape, seed, 14005, -143.0, 119.0))
    smoke = np.clip(_field(shape, seed, 14002, 20.0) * 0.34 + cloak * 0.36 + (_hash_noise(shape, seed, 14006) > 0.978) * 0.34, 0, 1)
    return np.clip(blade + hood * 0.28 + ribs * 0.34 + smoke * 0.30, 0, 1), blade, hood, smoke


def spec_owner_reaper_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, blade, hood, smoke = _ev67_reaper(shape, seed)
    return _spec_from_fields(shape, mask, 28 + detail * 184, 146 - blade * 112 + smoke * 24, 24 + detail * 152, sm)


def paint_owner_reaper_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, blade, hood, smoke = _ev67_reaper(shape, seed)
    shroud = _stack_rgb(0.010 + smoke * 0.050, 0.016 + smoke * 0.090, 0.016 + smoke * 0.055, shape)
    green = _stack_rgb(0.18, 0.92, 0.25, shape) * blade[:, :, None] * 0.72
    steel = _stack_rgb(0.60, 0.72, 0.68, shape) * _soften(blade, 1)[:, :, None] * 0.26
    void = _stack_rgb(0.02, 0.03, 0.02, shape) * hood[:, :, None] * 0.36
    effect = np.clip(shroud + green + steel + void + detail[:, :, None] * np.array([0.02, 0.08, 0.03], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.02).astype(np.float32))


def _ev67_catacombs(shape, seed):
    work_shape = _bounded_shape(shape, 1024)
    if work_shape != tuple(shape):
        detail, arches, torch = _ev67_catacombs(work_shape, seed)
        detail = _fit2(detail, shape)
        dust = (_hash_noise(shape, seed, 14102) > 0.955).astype(np.float32)
        scratch = _micro_lines(shape, seed, 14103, 233.0, 51.0)
        return np.clip(detail + dust * 0.18 + scratch * 0.14, 0, 1), _fit2(arches, shape), _fit2(torch, shape)
    x, y = _xy(shape)
    arches = np.zeros(shape, dtype=np.float32)
    brick = np.zeros(shape, dtype=np.float32)
    for i in range(9):
        cx = 0.045 + i * 0.118 + (_seed(seed, 14120 + i) - 0.5) * 0.012
        arch_curve = 0.50 - np.sqrt(np.clip(1.0 - ((x - cx) / 0.052) ** 2, 0, 1)) * 0.15
        arch = np.clip(1.0 - np.abs(y - arch_curve) / 0.006, 0, 1) * (np.abs(x - cx) < 0.055)
        pillar = ((np.abs(x - cx) < 0.018) & (y > arch_curve) & (y < 0.95)).astype(np.float32)
        arches = np.maximum(arches, np.maximum(arch, pillar) * (0.55 + (i % 3) * 0.10))
    mortar_h = np.clip(1.0 - np.abs(np.sin((y * 72.0 + _field(shape, seed, 14110, 2.0) * 0.38) * np.pi)) * 18.0, 0, 1)
    mortar_v = np.clip(1.0 - np.abs(np.sin((x * 48.0 + y * 9.0 + _seed(seed, 14111)) * np.pi)) * 22.0, 0, 1)
    brick = np.maximum(mortar_h, mortar_v) * 0.52
    bones = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 72.0 + y * 19.0 + _seed(seed, 14100)) * np.pi)) * 28.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -35.0 + y * 83.0 + _seed(seed, 14101)) * np.pi)) * 30.0, 0, 1),
    )
    torch, rings = _flare_centers(shape, [(0.16, 0.68, 0.055, 0.80), (0.48, 0.59, 0.045, 0.62), (0.79, 0.71, 0.060, 0.72)])
    dust = (_hash_noise(shape, seed, 14102) > 0.970).astype(np.float32)
    return np.clip(arches * 0.42 + brick * 0.42 + bones * 0.38 + torch * 0.50 + _soften(dust, 1) * 0.30, 0, 1), np.maximum(arches, brick), torch


def spec_owner_catacombs_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, arches, torch = _ev67_catacombs(shape, seed)
    return _spec_from_fields(shape, mask, 30 + detail * 166, 172 - detail * 96 + arches * 20, 20 + detail * 132, sm)


def paint_owner_catacombs_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, arches, torch = _ev67_catacombs(shape, seed)
    stone = _stack_rgb(0.10 + arches * 0.18, 0.095 + arches * 0.15, 0.080 + arches * 0.12, shape)
    amber = _stack_rgb(0.88, 0.36, 0.07, shape) * torch[:, :, None] * 0.44
    bone = _stack_rgb(0.42, 0.37, 0.27, shape) * detail[:, :, None] * 0.20
    effect = np.clip(stone + amber + bone, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.025).astype(np.float32))


def _ev67_shadow_realm(shape, seed):
    x, y = _xy(shape)
    void = _field(shape, seed, 14200, 18.0)
    cracks = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 112.0 + y * 31.0 + void * 3.5) * np.pi)) * 30.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -53.0 + y * 121.0 + void * 3.1) * np.pi)) * 32.0, 0, 1),
    )
    tunnel = np.zeros(shape, dtype=np.float32)
    for cx, cy, sx, sy, rot in ((0.28, 0.28, 0.22, 0.055, 0.72), (0.74, 0.66, 0.28, 0.070, -0.58), (0.50, 0.47, 0.18, 0.045, 1.10)):
        xr = (x - cx) * np.cos(rot) - (y - cy) * np.sin(rot)
        yr = (x - cx) * np.sin(rot) + (y - cy) * np.cos(rot)
        tunnel = np.maximum(tunnel, np.exp(-((xr / sx) ** 2 + (yr / sy) ** 2)))
    ash = (_hash_noise(shape, seed, 14201) > 0.974).astype(np.float32)
    return np.clip(cracks * 0.64 + tunnel * 0.54 + _soften(ash, 1) * 0.34 + void * 0.14, 0, 1), tunnel, void


def spec_owner_shadow_realm_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, portal, void = _ev67_shadow_realm(shape, seed)
    return _spec_from_fields(shape, mask, 24 + detail * 172, 180 - detail * 108 + void * 28, 18 + detail * 148, sm)


def paint_owner_shadow_realm_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, portal, void = _ev67_shadow_realm(shape, seed)
    black = _stack_rgb(0.006 + void * 0.020, 0.004 + void * 0.012, 0.016 + void * 0.040, shape)
    violet = _stack_rgb(0.44, 0.04, 0.82, shape) * detail[:, :, None] * 0.44
    blue = _stack_rgb(0.04, 0.36, 0.90, shape) * portal[:, :, None] * 0.28
    effect = np.clip(black + violet + blue, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_nightmare(shape, seed):
    x, y = _xy(shape)
    eyes, rings = _flare_centers(shape, [(0.25, 0.28, 0.07, 0.92), (0.72, 0.34, 0.08, 0.88), (0.52, 0.70, 0.10, 0.68)])
    teeth = np.maximum(
        np.clip(1.0 - np.abs(np.sin((x * 63.0 + y * 11.0 + _seed(seed, 14300)) * np.pi)) * 28.0, 0, 1),
        np.clip(1.0 - np.abs(np.sin((x * -27.0 + y * 71.0 + _field(shape, seed, 14301, 3.0)) * np.pi)) * 26.0, 0, 1),
    )
    fever = _field(shape, seed, 14302, 22.0)
    scratches = _micro_lines(shape, seed, 14303, 251.0, 89.0)
    return np.clip(eyes * 0.58 + rings * 0.28 + teeth * 0.52 + scratches * 0.28 + fever * 0.16, 0, 1), eyes, fever


def spec_owner_nightmare_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, eyes, fever = _ev67_nightmare(shape, seed)
    return _spec_from_fields(shape, mask, 24 + detail * 176, 174 - detail * 104 + fever * 22, 18 + detail * 150, sm)


def paint_owner_nightmare_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, eyes, fever = _ev67_nightmare(shape, seed)
    dark = _stack_rgb(0.010 + fever * 0.036, 0.006 + fever * 0.012, 0.026 + fever * 0.060, shape)
    red = _stack_rgb(0.86, 0.02, 0.12, shape) * detail[:, :, None] * 0.38
    violet = _stack_rgb(0.24, 0.02, 0.62, shape) * _soften(detail, 2)[:, :, None] * 0.30
    eye_glow = _stack_rgb(1.00, 0.76, 0.14, shape) * eyes[:, :, None] * 0.48
    effect = np.clip(dark + red + violet + eye_glow, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_xray(shape, seed):
    x, y = _xy(shape)
    spine = np.clip(1.0 - np.abs(x - 0.50) / 0.010, 0, 1) * np.clip(1.0 - np.abs(y - 0.50) / 0.42, 0, 1)
    ribs = np.zeros(shape, dtype=np.float32)
    for i in range(18):
        cy = 0.18 + i * 0.055
        curve = cy + (x - 0.5) ** 2 * (0.28 + i * 0.012) + np.sin((x * 5.0 + i) * np.pi) * 0.004
        ribs = np.maximum(ribs, np.clip(1.0 - np.abs(y - curve) / 0.0045, 0, 1) * np.clip(1.0 - np.abs(x - 0.5) / 0.45, 0, 1))
    joints = (_hash_noise(shape, seed, 14402) > 0.984).astype(np.float32) * np.clip(spine + ribs, 0, 1)
    scan = np.clip(1.0 - np.abs(np.sin((y * 650.0 + _seed(seed, 14400)) * np.pi)) * 14.0, 0, 1)
    fog = _field(shape, seed, 14401, 14.0)
    return np.clip(spine * 0.76 + ribs * 0.78 + joints * 0.46 + scan * 0.22 + fog * 0.16, 0, 1), spine, ribs


def spec_owner_x_ray_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    bones, spine, ribs = _ev67_xray(shape, seed)
    return _spec_from_fields(shape, mask, 42 + bones * 178, 142 - bones * 86, 32 + bones * 150, sm)


def paint_owner_x_ray_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    bones, spine, ribs = _ev67_xray(shape, seed)
    dark = _stack_rgb(0.006, 0.020, 0.034, shape)
    cyan = _stack_rgb(0.12, 0.70, 0.92, shape) * bones[:, :, None] * 0.70
    white = _stack_rgb(0.78, 0.96, 1.0, shape) * np.clip(spine + ribs, 0, 1)[:, :, None] * 0.20
    effect = np.clip(dark + cyan + white, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.02).astype(np.float32))


def _ev67_double_exposure(shape, seed):
    work_shape = _bounded_shape(shape, 1024)
    if work_shape != tuple(shape):
        exposure, portrait, skyline, haze = _ev67_double_exposure(work_shape, seed)
        exposure = _fit2(exposure, shape)
        hair = _micro_lines(shape, seed, 14531, 91.0, 213.0)
        grain = (_hash_noise(shape, seed, 14533) > 0.950).astype(np.float32)
        return np.clip(exposure + hair * 0.20 + grain * 0.12, 0, 1), _fit2(portrait, shape), _fit2(skyline, shape), _fit2(haze, shape)
    x, y = _xy(shape)
    portrait = np.exp(-(((x - 0.36) / 0.15) ** 2 + ((y - 0.50) / 0.31) ** 2))
    skyline = np.zeros(shape, dtype=np.float32)
    for i in range(22):
        x0 = 0.08 + i * 0.055
        hgt = 0.10 + _seed(seed, 14500 + i) * 0.34
        wid = 0.010 + _seed(seed, 14570 + i) * 0.015
        skyline = np.maximum(skyline, ((np.abs(x - x0) < wid) & (y > 0.70 - hgt) & (y < 0.70)).astype(np.float32))
    tree = np.zeros(shape, dtype=np.float32)
    for i in range(10):
        ang = -0.95 + i * 0.22 + (_seed(seed, 14580 + i) - 0.5) * 0.10
        line = (x - 0.22) * np.cos(ang) + (y - 0.72) * np.sin(ang)
        along = (x - 0.22) * -np.sin(ang) + (y - 0.72) * np.cos(ang)
        tree = np.maximum(tree, np.clip(1.0 - np.abs(line) / 0.0045, 0, 1) * (along > -0.05) * (along < 0.78))
    hair = np.maximum(_micro_lines(shape, seed, 14531, 91.0, 213.0), _micro_lines(shape, seed, 14532, -131.0, 177.0))
    haze = _field(shape, seed, 14532, 13.0)
    return np.clip(portrait * 0.54 + skyline * 0.38 + tree * 0.44 + hair * 0.22 + haze * 0.16, 0, 1), portrait, skyline, haze


def spec_owner_double_exposure_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    exposure, portrait, skyline, haze = _ev67_double_exposure(shape, seed)
    return _spec_from_fields(shape, mask, 34 + exposure * 172, 132 - portrait * 78 - skyline * 36 + haze * 20, 24 + exposure * 144, sm)


def paint_owner_double_exposure_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    exposure, portrait, skyline, haze = _ev67_double_exposure(shape, seed)
    sepia = _stack_rgb(0.12 + exposure * 0.36, 0.085 + exposure * 0.22, 0.065 + exposure * 0.14, shape)
    cyan = _stack_rgb(0.01, 0.15 + portrait * 0.32, 0.22 + exposure * 0.35, shape)
    ember = _stack_rgb(0.70, 0.26, 0.08, shape) * skyline[:, :, None] * 0.32
    effect = np.clip(sepia * 0.56 + cyan * 0.76 + ember, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.025).astype(np.float32))


# SPB-67 Effects & Vision wave 1: owner-called weak rows. These v4 rebuilds
# keep each finish on its own visual/material model while pushing spec-only
# micro motifs into the paint structure instead of generic chrome noise.


_EV67_WAVE1_CACHE = {}


def _ev67_wave1_cached(name, shape, seed, build):
    key = (name, tuple(shape), int(seed))
    cached = _EV67_WAVE1_CACHE.get(key)
    if cached is not None:
        return cached
    value = build()
    if len(_EV67_WAVE1_CACHE) > 32:
        _EV67_WAVE1_CACHE.clear()
    _EV67_WAVE1_CACHE[key] = value
    return value


@lru_cache(maxsize=12)
def _ev67_microflake(shape, seed, salt):
    pin = (_hash_noise(shape, seed, salt) > 0.952).astype(np.float32)
    dust = (_hash_noise(shape, seed, salt + 1) > 0.982).astype(np.float32)
    line_a = _micro_lines(shape, seed, salt + 2, 410.0, -137.0)
    line_b = _micro_lines(shape, seed, salt + 3, -283.0, 367.0)
    return np.clip(pin * 0.28 + _soften(dust, 1) * 0.34 + line_a * 0.20 + line_b * 0.16, 0, 1)


def _ev67_speckle_field(shape, seed, salt):
    x, y = _xy(shape)
    noise = _hash_noise(shape, seed, salt)
    pin = (noise > 0.944).astype(np.float32)
    hot = (noise > 0.987).astype(np.float32)
    pore = ((noise > 0.903) & (noise < 0.927)).astype(np.float32)
    cell_x = np.clip(1.0 - np.abs(np.sin((x * 221.0 + _seed(seed, salt + 3)) * np.pi)) * 12.0, 0, 1)
    cell_y = np.clip(1.0 - np.abs(np.sin((y * 197.0 + _seed(seed, salt + 4)) * np.pi)) * 12.0, 0, 1)
    cell = cell_x * cell_y
    return np.clip(_soften(pin, 1) * 0.30 + hot * 0.34 + pore * 0.22 + cell * 0.22, 0, 1)


def _ev67_grit_field(shape, seed, salt):
    x, y = _xy(shape)
    noise = _hash_noise(shape, seed, salt)
    dust = (noise > 0.958).astype(np.float32)
    fine = ((noise > 0.865) & (noise < 0.890)).astype(np.float32)
    weave_x = np.clip(1.0 - np.abs(np.sin((x * 151.0 + _seed(seed, salt + 2)) * np.pi)) * 14.0, 0, 1)
    weave_y = np.clip(1.0 - np.abs(np.sin((y * 173.0 + _seed(seed, salt + 3)) * np.pi)) * 15.0, 0, 1)
    weave = weave_x + weave_y
    return np.clip(_soften(dust, 1) * 0.34 + fine * 0.14 + weave * 0.20, 0, 1)


def _ev67_negative_v4(shape, seed):
    def build():
        x, y = _xy(shape)
        # SPB paint-finish perf loop 2026-05-31: 1280->1024 keeps film scratches fine while clearing the 4s ceiling.
        work_shape = _bounded_shape(shape, 1024)
        if work_shape != tuple(shape):
            plate, scratches, emulsion, sprocket, ghosts = _ev67_negative_v4(work_shape, seed)
            micro = _ev67_microflake(shape, seed, 15141)
            return (
                np.clip(_fit2(plate, shape) + micro * 0.28, 0, 1),
                np.clip(_fit2(scratches, shape) + micro * 0.38, 0, 1),
                np.clip(_fit2(emulsion, shape) + micro * 0.24, 0, 1),
                _fit2(sprocket, shape),
                _fit2(ghosts, shape),
            )
        frame = np.clip((1.0 - x) ** 7.0 * 0.52 + y ** 8.0 * 0.30 + (1.0 - y) ** 10.0 * 0.24, 0, 1)
        scratch_a = np.clip(1.0 - np.abs(np.sin((x * 96.0 + y * 17.0 + _seed(seed, 15101)) * np.pi)) * 38.0, 0, 1)
        scratch_b = np.clip(1.0 - np.abs(np.sin((x * -43.0 + y * 231.0 + _field(shape, seed, 15102, 2.5) * 0.8) * np.pi)) * 28.0, 0, 1)
        emulsion = np.clip(_field(shape, seed, 15103, 24.0) * 0.38 + _ev67_scan_grain(shape, seed, 15104) * 0.54, 0, 1)
        sprocket = np.zeros(shape, dtype=np.float32)
        for i in range(18):
            cy = 0.045 + i * 0.053
            perf = (np.abs(x - 0.052) < 0.012) & (np.abs(y - cy) < 0.014)
            sprocket = np.maximum(sprocket, perf.astype(np.float32))
        ghost_lines = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 15.0 + y * 2.0 + frame * 1.4) * np.pi)) * 20.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((y * 28.0 + _seed(seed, 15105)) * np.pi)) * 26.0, 0, 1) * (x > 0.12),
        )
        plate = np.clip(frame + emulsion * 0.44 + scratch_a * 0.32 + scratch_b * 0.24 + sprocket * 0.58, 0, 1)
        return plate, np.clip(scratch_a + scratch_b * 0.76, 0, 1), emulsion, sprocket, ghost_lines

    return _ev67_wave1_cached("negative_v4", shape, seed, build)


def spec_owner_negative_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    plate, scratches, emulsion, sprocket, ghosts = _ev67_negative_v4(shape, seed)
    return _spec_from_fields(
        shape,
        mask,
        24 + emulsion * 96 + scratches * 116 + sprocket * 74,
        156 - scratches * 108 + plate * 20 - ghosts * 28,
        32 + plate * 118 + ghosts * 82 + sprocket * 46,
        sm,
    )


def paint_owner_negative_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    base = paint[:, :, :3].astype(np.float32, copy=True)
    plate, scratches, emulsion, sprocket, ghosts = _ev67_negative_v4(shape, seed)
    micro = _ev67_microflake(shape, seed, 15141)
    inverted = np.clip(1.0 - base * 0.62, 0, 1)
    cyan = _stack_rgb(0.012 + emulsion * 0.12, 0.32 + emulsion * 0.30, 0.48 + plate * 0.20, shape)
    amber = _stack_rgb(0.92, 0.45, 0.08, shape) * np.clip(plate + ghosts * 0.42, 0, 1)[:, :, None] * 0.26
    violet = _stack_rgb(0.22, 0.08, 0.34, shape) * scratches[:, :, None] * 0.22
    magenta = _stack_rgb(0.70, 0.08, 0.45, shape) * micro[:, :, None] * 0.42
    blue_silver = _stack_rgb(0.16, 0.34, 0.72, shape) * np.clip(micro + scratches * 0.36, 0, 1)[:, :, None] * 0.22
    effect = np.clip(inverted * 0.30 + cyan * 0.60 + amber + violet + magenta + blue_silver - sprocket[:, :, None] * 0.07, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.025).astype(np.float32))


def _ev67_polarized_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 1024)
        if work_shape != tuple(shape):
            stress, bands, rings, cracks = _ev67_polarized_v4(work_shape, seed)
            micro = _ev67_microflake(shape, seed, 15241)
            return (
                _fit2(stress, shape),
                np.clip(_fit2(bands, shape) + micro * 0.22, 0, 1),
                np.clip(_fit2(rings, shape) + micro * 0.14, 0, 1),
                np.clip(_fit2(cracks, shape) + micro * 0.26, 0, 1),
            )
        x, y = _xy(shape)
        stress = np.clip(
            _field(shape, seed, 15200, 18.0) * 0.50
            + np.sin((x * 7.8 - y * 6.3 + _seed(seed, 15201)) * np.pi) * 0.20
            + np.sin((x * -4.8 + y * 11.2 + _seed(seed, 15202)) * np.pi) * 0.15
            + 0.34,
            0,
            1,
        )
        rings = np.clip(1.0 - np.abs(np.sin((stress * 44.0 + x * 5.5 - y * 3.5) * np.pi)) * 8.0, 0, 1)
        stress_cracks = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 74.0 + y * 19.0 + stress * 3.4) * np.pi)) * 28.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -29.0 + y * 81.0 + stress * 2.7) * np.pi)) * 28.0, 0, 1),
        )
        birefringe = _micro_lines(shape, seed, 15203, 381.0, 113.0)
        bands = np.clip(rings * 0.76 + stress_cracks * 0.36 + birefringe * 0.30, 0, 1)
        return stress, bands, rings, stress_cracks

    return _ev67_wave1_cached("polarized_v4", shape, seed, build)


def spec_owner_polarized_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    stress, bands, rings, cracks = _ev67_polarized_v4(shape, seed)
    return _spec_from_fields(
        shape,
        mask,
        18 + rings * 92 + cracks * 128,
        78 - rings * 46 + stress * 54 + cracks * 12,
        58 + bands * 170 + rings * 28,
        sm,
    )


def paint_owner_polarized_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    stress, bands, rings, cracks = _ev67_polarized_v4(shape, seed)
    color = _rgb_cycle(stress * 1.14 + rings * 0.18 + _seed(seed, 15204), 0.98, 0.98)
    smoked_lens = _stack_rgb(0.010 + stress * 0.018, 0.011 + stress * 0.010, 0.017 + stress * 0.030, shape)
    effect = np.clip(smoked_lens + color * (0.18 + bands[:, :, None] * 0.82) + cracks[:, :, None] * np.array([0.10, 0.04, 0.16], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_halftone_v4(shape, seed):
    def build():
        x, y = _xy(shape)
        angle_a = 0.52
        angle_b = -0.43
        xa = x * np.cos(angle_a) - y * np.sin(angle_a)
        ya = x * np.sin(angle_a) + y * np.cos(angle_a)
        xb = x * np.cos(angle_b) - y * np.sin(angle_b)
        yb = x * np.sin(angle_b) + y * np.cos(angle_b)
        tone = np.clip(_field(shape, seed, 15300, 8.0) * 0.48 + x * 0.20 + (1.0 - y) * 0.18, 0, 1)
        cell = 118.0
        cmy = np.stack(
            [
                np.clip((1.0 - np.maximum(np.abs(np.sin((xa * cell + _seed(seed, 15301)) * np.pi)), np.abs(np.sin((ya * cell + _seed(seed, 15302)) * np.pi)))) * (2.0 + tone * 2.4), 0, 1),
                np.clip((1.0 - np.maximum(np.abs(np.sin((xb * (cell * 0.88) + _seed(seed, 15303)) * np.pi)), np.abs(np.sin((yb * (cell * 0.88) + _seed(seed, 15304)) * np.pi)))) * (1.9 + (1.0 - tone) * 2.2), 0, 1),
                np.clip((1.0 - np.maximum(np.abs(np.sin((x * 86.0 + _seed(seed, 15305)) * np.pi)), np.abs(np.sin((y * 86.0 + _seed(seed, 15306)) * np.pi)))) * (1.6 + tone * 1.7), 0, 1),
            ],
            axis=2,
        )
        rosette = np.clip(1.0 - np.abs(np.sin((x * 39.0 - y * 31.0 + tone * 2.3) * np.pi)) * 22.0, 0, 1)
        grit = _ev67_microflake(shape, seed, 15320)
        dots = np.clip(cmy.max(axis=2) + rosette * 0.25 + grit * 0.18, 0, 1)
        return dots, tone, cmy, rosette

    return _ev67_wave1_cached("halftone_v4", shape, seed, build)


def spec_owner_halftone_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    dots, tone, cmy, rosette = _ev67_halftone_v4(shape, seed)
    ink_relief = np.clip(cmy[:, :, 0] * 0.42 + cmy[:, :, 1] * 0.34 + cmy[:, :, 2] * 0.30 + rosette * 0.22, 0, 1)
    return _spec_from_fields(shape, mask, 20 + ink_relief * 132, 142 - dots * 78 + tone * 28, 20 + dots * 124 + rosette * 48, sm)


def paint_owner_halftone_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    dots, tone, cmy, rosette = _ev67_halftone_v4(shape, seed)
    paper = _stack_rgb(0.050 + tone * 0.11, 0.047 + tone * 0.09, 0.039 + tone * 0.07, shape)
    ink = np.stack(
        [
            cmy[:, :, 1] * 0.82 + cmy[:, :, 2] * 0.48,
            cmy[:, :, 2] * 0.76 + cmy[:, :, 0] * 0.22,
            cmy[:, :, 0] * 0.88 + cmy[:, :, 1] * 0.34,
        ],
        axis=2,
    )
    effect = np.clip(paper + ink * 0.88 + rosette[:, :, None] * np.array([0.18, 0.08, 0.02], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.022).astype(np.float32))


def _ev67_chromatic_v4(shape, seed):
    def build():
        x, y = _xy(shape)
        warp = _field(shape, seed, 15400, 6.0)
        contour = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 68.0 + y * 17.0 + warp * 3.6) * np.pi)) * 26.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -25.0 + y * 76.0 + warp * 3.0) * np.pi)) * 26.0, 0, 1),
        )
        scan = np.maximum(_micro_lines(shape, seed, 15401, 428.0, 77.0), _micro_lines(shape, seed, 15402, -347.0, 311.0))
        ghosts = np.clip(1.0 - np.abs(np.sin((x * 15.0 + y * 23.0 + warp * 5.0) * np.pi)) * 20.0, 0, 1)
        edge = np.clip(contour * 0.78 + scan * 0.32 + ghosts * 0.28, 0, 1)
        return edge, warp, scan, ghosts

    return _ev67_wave1_cached("chromatic_v4", shape, seed, build)


def spec_owner_chromatic_aberration_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    edge, warp, scan, ghosts = _ev67_chromatic_v4(shape, seed)
    return _spec_from_fields(shape, mask, 24 + edge * 154 + scan * 62, 112 - edge * 76 + warp * 22, 28 + edge * 156 + ghosts * 54, sm)


def paint_owner_chromatic_aberration_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    edge, warp, scan, ghosts = _ev67_chromatic_v4(shape, seed)
    px = max(2, shape[1] // 130)
    red = np.roll(edge, px * 2, axis=1)
    green = np.roll(edge, -px, axis=0)
    blue = np.roll(edge, -px * 2, axis=1)
    base = _stack_rgb(0.018 + warp * 0.024, 0.019 + warp * 0.020, 0.028 + warp * 0.030, shape)
    effect = np.clip(base + np.stack([red * 0.84 + ghosts * 0.18, green * 0.74 + scan * 0.10, blue * 0.98 + ghosts * 0.20], axis=2), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_refraction_v4(shape, seed):
    def build():
        x, y = _xy(shape)
        work_shape = _bounded_shape(shape, 1280)
        if work_shape != tuple(shape):
            prism, facet, caustic, rings = _ev67_refraction_v4(work_shape, seed)
            micro = _ev67_microflake(shape, seed, 15531)
            return (
                np.clip(_fit2(prism, shape) + micro * 0.20, 0, 1),
                _fit2(facet, shape),
                np.clip(_fit2(caustic, shape) + micro * 0.34, 0, 1),
                _fit2(rings, shape),
            )
        facet_a = np.mod(np.floor((x * 32.0 + y * 10.0)) + np.floor((y * 28.0 - x * 8.0)), 11.0) / 10.0
        facet_b = np.mod(np.floor((x * -18.0 + y * 38.0)) + np.floor((x * 23.0 + y * 13.0)), 9.0) / 8.0
        facet = np.clip(facet_a * 0.54 + facet_b * 0.46, 0, 1)
        caustic = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 58.0 + y * 34.0 + _seed(seed, 15500)) * np.pi)) * 23.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -43.0 + y * 51.0 + _field(shape, seed, 15501, 3.3) * 2.8) * np.pi)) * 23.0, 0, 1),
        )
        rings = np.clip(1.0 - np.abs(np.sin((np.sqrt((x - 0.56) ** 2 + (y - 0.46) ** 2) * 42.0 + facet * 2.0) * np.pi)) * 14.0, 0, 1)
        prism = np.clip(facet * 0.34 + caustic * 0.78 + rings * 0.38 + _ev67_microflake(shape, seed, 15502) * 0.22, 0, 1)
        return prism, facet, caustic, rings

    return _ev67_wave1_cached("refraction_v4", shape, seed, build)


def spec_owner_refraction_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    prism, facet, caustic, rings = _ev67_refraction_v4(shape, seed)
    return _spec_from_fields(shape, mask, 16 + caustic * 96 + rings * 82, 48 - caustic * 22 + facet * 48, 76 + prism * 164 + rings * 28, sm)


def paint_owner_refraction_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    prism, facet, caustic, rings = _ev67_refraction_v4(shape, seed)
    color = _rgb_cycle(prism * 0.88 + facet * 0.16 + _seed(seed, 15503), 0.82, 0.96)
    glass = _stack_rgb(0.022 + facet * 0.040, 0.038 + facet * 0.032, 0.056 + facet * 0.046, shape)
    effect = np.clip(glass + color * (0.12 + caustic[:, :, None] * 0.78) + rings[:, :, None] * np.array([0.08, 0.12, 0.18], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.020).astype(np.float32))


def _ev67_graveyard_v4(shape, seed):
    def build():
        base_shape = _bounded_shape(shape, 768)
        # SPB paint-finish perf loop 2026-05-31; graveyard measured 5469.2ms -> 3495.9ms.
        # Build lichen/epitaph/iron with the bounded field, then resize with the
        # shared detail so paint/spec do not pay full-res line work twice.
        detail, stones, moon, fog = _ev67_graveyard(base_shape, seed)
        x, y = _xy(base_shape)
        lichen = _ev67_microflake(base_shape, seed, 15601) * np.clip((y - 0.34) * 2.4, 0, 1)
        epitaph = np.zeros(base_shape, dtype=np.float32)
        for i in range(10):
            cy = 0.54 + (i % 5) * 0.058
            dash = np.clip(1.0 - np.abs(np.sin((x * (46.0 + i * 3.0) + _seed(seed, 15620 + i)) * np.pi)) * 30.0, 0, 1)
            gate = (np.abs(y - cy) < 0.0035 + (i % 3) * 0.001).astype(np.float32)
            epitaph = np.maximum(epitaph, dash * gate * (x > 0.15) * (x < 0.86))
        iron = np.clip(1.0 - np.abs(np.sin((x * 82.0 + _seed(seed, 15640)) * np.pi)) * 34.0, 0, 1) * (y > 0.58)
        if base_shape != tuple(shape):
            detail = _fit2(detail, shape)
            stones = _fit2(stones, shape)
            moon = _fit2(moon, shape)
            fog = _fit2(fog, shape)
            lichen = _fit2(lichen, shape)
            epitaph = _fit2(epitaph, shape)
            iron = _fit2(iron, shape)
        return np.clip(detail + lichen * 0.34 + epitaph * 0.42 + iron * 0.18, 0, 1), stones, moon, fog, lichen, epitaph

    return _ev67_wave1_cached("graveyard_v4", shape, seed, build)


def spec_owner_graveyard_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, stones, moon, fog, lichen, epitaph = _ev67_graveyard_v4(shape, seed)
    return _spec_from_fields(
        shape,
        mask,
        18 + detail * 108 + epitaph * 88 + lichen * 46,
        176 - stones * 92 - moon * 42 - epitaph * 56 + fog * 28,
        18 + detail * 130 + moon * 54 + epitaph * 70,
        sm,
    )


def paint_owner_graveyard_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, stones, moon, fog, lichen, epitaph = _ev67_graveyard_v4(shape, seed)
    dew_shape = _bounded_shape(shape, 768)
    dew = _ev67_microflake(dew_shape, seed, 15655)
    if dew_shape != tuple(shape):
        dew = _fit2(dew, shape)
    night = _stack_rgb(0.014 + fog * 0.052, 0.023 + fog * 0.088, 0.050 + fog * 0.155, shape)
    stone = _stack_rgb(0.21 + lichen * 0.07, 0.25 + lichen * 0.14, 0.22 + lichen * 0.05, shape) * stones[:, :, None] * 0.62
    moonlight = _stack_rgb(0.40, 0.58, 0.66, shape) * moon[:, :, None] * 0.44
    moss = _stack_rgb(0.035, 0.34, 0.10, shape) * np.clip(lichen + detail * 0.20, 0, 1)[:, :, None] * 0.30
    ghost_ink = _stack_rgb(0.54, 0.68, 0.58, shape) * epitaph[:, :, None] * 0.22
    wet_grit = _stack_rgb(0.10, 0.22, 0.18, shape) * dew[:, :, None] * 0.34
    cold_firefly = _stack_rgb(0.54, 0.72, 0.42, shape) * np.clip(dew * (1.0 - stones), 0, 1)[:, :, None] * 0.20
    effect = np.clip(night + stone + moonlight + moss + ghost_ink + wet_grit + cold_firefly + detail[:, :, None] * np.array([0.024, 0.042, 0.036], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.022).astype(np.float32))


def _ev67_reaper_v4(shape, seed):
    def build():
        base_shape = _bounded_shape(shape, 768)
        if base_shape != tuple(shape):
            detail, blade, hood, smoke = _ev67_reaper(base_shape, seed)
            detail = _fit2(detail, shape)
            blade = _fit2(blade, shape)
            hood = _fit2(hood, shape)
            smoke = _fit2(smoke, shape)
        else:
            detail, blade, hood, smoke = _ev67_reaper(shape, seed)
        x, y = _xy(shape)
        cloak_threads = np.maximum(_micro_lines(shape, seed, 15701, 319.0, -91.0), _micro_lines(shape, seed, 15702, -247.0, 281.0))
        edge_chips = _ev67_microflake(shape, seed, 15703) * np.clip(blade * 2.4, 0, 1)
        runes = np.clip(1.0 - np.abs(np.sin((x * 20.0 + y * 52.0 + blade * 8.0 + _seed(seed, 15704)) * np.pi)) * 24.0, 0, 1) * np.clip(blade * 2.2, 0, 1)
        veil = np.clip(smoke + cloak_threads * 0.28 + (_hash_noise(shape, seed, 15705) > 0.982) * 0.24, 0, 1)
        return np.clip(detail + cloak_threads * 0.24 + edge_chips * 0.34 + runes * 0.40, 0, 1), blade, hood, veil, edge_chips, runes

    return _ev67_wave1_cached("reaper_v4", shape, seed, build)


def spec_owner_reaper_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, blade, hood, veil, edge_chips, runes = _ev67_reaper_v4(shape, seed)
    return _spec_from_fields(
        shape,
        mask,
        16 + veil * 54 + blade * 120 + edge_chips * 90,
        148 - blade * 112 - runes * 42 + veil * 34,
        22 + detail * 112 + runes * 106 + edge_chips * 72,
        sm,
    )


def paint_owner_reaper_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, blade, hood, veil, edge_chips, runes = _ev67_reaper_v4(shape, seed)
    ash = _ev67_microflake(shape, seed, 15744)
    shroud = _stack_rgb(0.010 + veil * 0.045, 0.016 + veil * 0.085, 0.017 + veil * 0.052, shape)
    blade_glow = _stack_rgb(0.15, 0.90, 0.23, shape) * blade[:, :, None] * 0.70
    satin_steel = _stack_rgb(0.58, 0.70, 0.64, shape) * _soften(edge_chips + blade * 0.45, 1)[:, :, None] * 0.24
    void = _stack_rgb(0.012, 0.017, 0.014, shape) * hood[:, :, None] * 0.44
    glyph_glow = _stack_rgb(0.38, 0.92, 0.34, shape) * runes[:, :, None] * 0.24
    ember = _stack_rgb(0.66, 0.32, 0.08, shape) * ash[:, :, None] * 0.26
    violet_satin = _stack_rgb(0.18, 0.06, 0.24, shape) * np.clip(veil + ash * 0.5, 0, 1)[:, :, None] * 0.22
    effect = np.clip(shroud + blade_glow + satin_steel + void + glyph_glow + ember + violet_satin + detail[:, :, None] * np.array([0.024, 0.090, 0.038], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_reaper_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 512)
        x, y = _xy(work_shape)
        hood_outer = np.exp(-(((x - 0.48) / 0.155) ** 2 + ((y - 0.31) / 0.205) ** 2))
        face_void = np.exp(-(((x - 0.50) / 0.078) ** 2 + ((y - 0.345) / 0.115) ** 2))
        shoulders = np.clip(1.0 - np.abs((y - 0.62) / 0.30), 0, 1) * np.clip(1.0 - np.abs((x - 0.50) / (0.20 + y * 0.24)), 0, 1)
        fold_phase = _field(work_shape, seed, 15790, 7.0)
        folds = np.clip(1.0 - np.abs(np.sin((x * 24.0 + fold_phase * 2.1) * np.pi)) * 9.0, 0, 1) * shoulders
        tatter = np.clip(1.0 - np.abs(np.sin((x * 39.0 + _seed(seed, 15791)) * np.pi)) * 7.5, 0, 1) * np.clip((y - 0.58) * 2.0, 0, 1)

        curve_x = 0.70 - (y - 0.38) * 0.23 + np.sin((y * 1.85 + _seed(seed, 15792)) * np.pi) * 0.035
        blade_core = np.exp(-((x - curve_x) / 0.0065) ** 2) * (y > 0.13) * (y < 0.78)
        blade_back = np.exp(-((x - (curve_x - 0.030)) / 0.0035) ** 2) * (y > 0.17) * (y < 0.72)
        blade_tip = np.exp(-(((x - 0.78) / 0.055) ** 2 + ((y - 0.13) / 0.030) ** 2))
        blade = np.clip(blade_core * 0.86 + blade_back * 0.34 + blade_tip * 0.72, 0, 1)

        shaft_x = 0.38 + (y - 0.50) * 0.080
        shaft = np.exp(-((x - shaft_x) / 0.0042) ** 2) * (y > 0.24) * (y < 0.91)
        finger = np.zeros(work_shape, dtype=np.float32)
        for i in range(8):
            cy = 0.46 + i * 0.026
            rib = np.exp(-(((x - (0.41 + i * 0.004)) / 0.020) ** 2 + ((y - cy) / 0.0034) ** 2))
            finger = np.maximum(finger, rib * (0.45 + i * 0.045))
        tally = np.zeros(work_shape, dtype=np.float32)
        for i in range(13):
            ty = 0.21 + i * 0.038
            mark = (np.abs(y - ty) < 0.0026) & (np.abs(x - (curve_x - 0.010)) < 0.027)
            tally = np.maximum(tally, mark.astype(np.float32) * (0.34 + (i % 3) * 0.11))

        detail = np.clip(hood_outer * 0.42 - face_void * 0.28 + shoulders * 0.18 + folds * 0.32 + tatter * 0.22 + blade * 0.82 + shaft * 0.45 + finger * 0.42 + tally * 0.54, 0, 1)
        if work_shape != tuple(shape):
            detail = _fit2(detail, shape)
            hood_outer = _fit2(hood_outer, shape)
            face_void = _fit2(face_void, shape)
            shoulders = _fit2(shoulders, shape)
            folds = _fit2(folds, shape)
            tatter = _fit2(tatter, shape)
            blade = _fit2(blade, shape)
            shaft = _fit2(shaft, shape)
            finger = _fit2(finger, shape)
            tally = _fit2(tally, shape)
        ash_noise = _hash_noise(shape, seed, 15793)
        ash = np.clip(
            ((ash_noise > 0.560) & (ash_noise < 0.610)).astype(np.float32) * 0.055
            + ((ash_noise > 0.760) & (ash_noise < 0.810)).astype(np.float32) * 0.085
            + ((ash_noise > 0.840) & (ash_noise < 0.884)).astype(np.float32) * 0.13
            + (ash_noise > 0.936).astype(np.float32) * 0.24
            + (ash_noise > 0.985).astype(np.float32) * 0.38,
            0,
            1,
        )
        edge_sparks = (ash_noise > 0.991).astype(np.float32) * np.clip(blade * 2.2 + tally * 1.4, 0, 1)
        cloak_ash = ash * np.clip(shoulders + tatter * 0.95 + folds * 0.52, 0, 1)
        blade_chatter = ash * np.clip(blade * 1.8 + shaft * 0.55 + tally, 0, 1)
        detail = np.clip(detail + cloak_ash * 0.62 + blade_chatter * 0.44 + edge_sparks * 0.46, 0, 1)
        return detail, hood_outer, face_void, shoulders, folds, tatter, blade, shaft, finger, tally, ash, edge_sparks

    return _ev67_wave1_cached("reaper_v5", shape, seed, build)


def spec_owner_reaper_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, hood, void, shoulders, folds, tatter, blade, shaft, finger, tally, ash, edge_sparks = _ev67_reaper_v5(shape, seed)
    metal = 12 + blade * 138 + shaft * 78 + finger * 72 + tally * 84 + edge_sparks * 116
    rough = 182 + shoulders * 18 + ash * 24 - blade * 96 - tally * 42 - edge_sparks * 68
    coat = 18 + folds * 84 + tatter * 42 + blade * 78 + tally * 116 + edge_sparks * 92
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((metal + ash * 28 + detail * 16) * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(rough * mask + 80 * (1.0 - mask), 12, 210).astype(np.uint8)
    spec[:, :, 2] = np.clip((coat + edge_sparks * 54 + tally * 24) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_reaper_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, hood, void, shoulders, folds, tatter, blade, shaft, finger, tally, ash, edge_sparks = _ev67_reaper_v5(shape, seed)
    fold_mask = np.clip(folds + tatter * 0.52, 0, 1)
    steel_mask = np.clip(blade + shaft * 0.38, 0, 1)
    edge_mask = np.clip(blade * 0.74 + tally * 0.52 + edge_sparks, 0, 1)
    ash_mask = np.clip(ash * (shoulders + tatter + folds), 0, 1)
    ember_mask = np.clip(ash * tatter + edge_sparks * 0.48, 0, 1)
    effect = np.empty((shape[0], shape[1], 3), dtype=np.float32)
    effect[:, :, 0] = (
        0.018
        + shoulders * 0.030
        + fold_mask * 0.026
        + steel_mask * 0.285
        + edge_mask * 0.060
        + finger * 0.185
        + ash_mask * 0.235
        + ash * 0.110
        + ember_mask * 0.250
        + detail * 0.024
        - void * 0.0016
    )
    effect[:, :, 1] = (
        0.022
        + folds * 0.050
        + fold_mask * 0.079
        + steel_mask * 0.331
        + edge_mask * 0.470
        + finger * 0.166
        + ash_mask * 0.390
        + ash * 0.150
        + ember_mask * 0.090
        + detail * 0.060
        - void * 0.0031
    )
    effect[:, :, 2] = (
        0.020
        + shoulders * 0.028
        + fold_mask * 0.053
        + steel_mask * 0.299
        + edge_mask * 0.190
        + finger * 0.115
        + ash_mask * 0.286
        + ash * 0.122
        + ember_mask * 0.018
        + detail * 0.038
        - void * 0.0023
    )
    effect = np.clip(effect, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.014).astype(np.float32))


def _ev67_phantom_v4(shape, seed):
    def build():
        # SPB paint-finish perf loop 2026-05-31: 1280->1024; native microflake is cached and re-applied above.
        work_shape = _bounded_shape(shape, 1024)
        if work_shape != tuple(shape):
            veil, silhouette, echoes, seam = _ev67_phantom_v4(work_shape, seed)
            micro = _ev67_microflake(shape, seed, 15841)
            return (
                np.clip(_fit2(veil, shape) + micro * 0.24, 0, 1),
                _fit2(silhouette, shape),
                np.clip(_fit2(echoes, shape) + micro * 0.18, 0, 1),
                np.clip(_fit2(seam, shape) + micro * 0.30, 0, 1),
            )
        x, y = _xy(shape)
        warp = _field(shape, seed, 15800, 16.0)
        silhouette = np.exp(-(((x - 0.50) / 0.17) ** 2 + ((y - 0.44) / 0.31) ** 2))
        shoulder = np.exp(-(((x - 0.50) / 0.30) ** 2 + ((y - 0.72) / 0.13) ** 2))
        echoes = np.zeros(shape, dtype=np.float32)
        for i, dx in enumerate((-0.075, -0.038, 0.040, 0.082)):
            echoes = np.maximum(echoes, np.exp(-(((x - 0.50 - dx) / (0.18 + i * 0.012)) ** 2 + ((y - 0.47) / (0.30 + i * 0.018)) ** 2)) * (0.34 + i * 0.08))
        veil = np.clip(_micro_lines(shape, seed, 15801, 233.0, -71.0) * 0.42 + _micro_lines(shape, seed, 15802, -177.0, 277.0) * 0.32 + warp * 0.24, 0, 1)
        seam = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 52.0 + y * 19.0 + warp * 2.2) * np.pi)) * 24.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -31.0 + y * 67.0 + _seed(seed, 15803)) * np.pi)) * 26.0, 0, 1),
        )
        veil = np.clip(veil + seam * 0.34 + _ev67_microflake(shape, seed, 15804) * 0.42, 0, 1)
        return np.clip(veil + silhouette * 0.14 + shoulder * 0.10 + echoes * 0.10, 0, 1), np.clip(silhouette + shoulder * 0.40, 0, 1), echoes, seam

    return _ev67_wave1_cached("phantom_v4", shape, seed, build)


def spec_owner_phantom_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    veil, silhouette, echoes, seam = _ev67_phantom_v4(shape, seed)
    return _spec_from_fields(shape, mask, 14 + seam * 86 + echoes * 70, 168 - seam * 84 + veil * 18, 34 + veil * 112 + silhouette * 72 + echoes * 84, sm)


def paint_owner_phantom_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    veil, silhouette, echoes, seam = _ev67_phantom_v4(shape, seed)
    glint = _ev67_microflake(shape, seed, 15841)
    deep = _stack_rgb(0.016 + veil * 0.050, 0.038 + veil * 0.082, 0.060 + veil * 0.132, shape)
    apparition = _stack_rgb(0.20, 0.60, 0.76, shape) * np.clip(silhouette * 0.18 + echoes * 0.18, 0, 1)[:, :, None]
    violet = _stack_rgb(0.25, 0.10, 0.42, shape) * seam[:, :, None] * 0.36
    spectral_dust = _stack_rgb(0.12, 0.34, 0.48, shape) * glint[:, :, None] * 0.46
    frost_threads = _stack_rgb(0.09, 0.25, 0.34, shape) * np.maximum(seam, veil * 0.55)[:, :, None] * 0.24
    effect = np.clip(deep + apparition + violet + spectral_dust + frost_threads + veil[:, :, None] * np.array([0.034, 0.070, 0.105], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.020).astype(np.float32))


# SPB-67 Effects & Vision wave 2: optical, horror, relief, and scene rows.


def _ev67_double_exposure_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        portrait = np.exp(-(((x - 0.34) / 0.15) ** 2 + ((y - 0.47) / 0.30) ** 2))
        profile = np.exp(-(((x - 0.58) / 0.12) ** 2 + ((y - 0.42) / 0.26) ** 2)) * 0.62
        skyline = np.zeros(work_shape, dtype=np.float32)
        for i in range(26):
            x0 = 0.04 + i * 0.038 + (_seed(seed, 16100 + i) - 0.5) * 0.012
            hgt = 0.08 + _seed(seed, 16140 + i) * 0.28
            wid = 0.006 + _seed(seed, 16170 + i) * 0.011
            skyline = np.maximum(skyline, ((np.abs(x - x0) < wid) & (y > 0.78 - hgt) & (y < 0.80)).astype(np.float32))
        branches = np.zeros(work_shape, dtype=np.float32)
        for i in range(14):
            ang = -1.15 + i * 0.17 + (_seed(seed, 16200 + i) - 0.5) * 0.10
            line = (x - 0.18) * np.cos(ang) + (y - 0.82) * np.sin(ang)
            along = (x - 0.18) * -np.sin(ang) + (y - 0.82) * np.cos(ang)
            branches = np.maximum(branches, np.clip(1.0 - np.abs(line) / 0.004, 0, 1) * (along > -0.04) * (along < 0.82))
        haze = _field(work_shape, seed, 16220, 16.0)
        exposure = np.clip(portrait * 0.24 + profile * 0.20 + skyline * 0.28 + branches * 0.38 + haze * 0.20, 0, 1)
        if work_shape != tuple(shape):
            hair = _micro_lines(shape, seed, 16230, 91.0, 231.0)
            grain = _ev67_microflake(shape, seed, 16231)
            scan = _micro_lines(shape, seed, 16232, -311.0, 419.0)
            return (
                np.clip(_fit2(exposure, shape) + hair * 0.38 + grain * 0.38 + scan * 0.24, 0, 1),
                _fit2(np.clip(portrait + profile, 0, 1), shape),
                _fit2(skyline, shape),
                _fit2(branches, shape),
                _fit2(haze, shape),
                grain,
                scan,
            )
        grain = _ev67_microflake(shape, seed, 16231)
        scan = _micro_lines(shape, seed, 16232, -311.0, 419.0)
        return np.clip(exposure + grain * 0.20 + scan * 0.12, 0, 1), np.clip(portrait + profile, 0, 1), skyline, branches, haze, grain, scan

    return _ev67_wave1_cached("double_exposure_v4", shape, seed, build)


def spec_owner_double_exposure_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    exposure, portrait, skyline, branches, haze, grain, scan = _ev67_double_exposure_v4(shape, seed)
    return _spec_from_fields(shape, mask, 18 + exposure * 112 + skyline * 88 + branches * 58, 154 - portrait * 72 - skyline * 36 + haze * 30, 28 + exposure * 132 + branches * 72, sm)


def paint_owner_double_exposure_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    exposure, portrait, skyline, branches, haze, grain, scan = _ev67_double_exposure_v4(shape, seed)
    sepia = _stack_rgb(0.10 + exposure * 0.31, 0.076 + exposure * 0.22, 0.060 + exposure * 0.15, shape)
    cyan = _stack_rgb(0.012, 0.13 + portrait * 0.30, 0.21 + exposure * 0.34, shape)
    ember = _stack_rgb(0.72, 0.28, 0.07, shape) * skyline[:, :, None] * 0.34
    ink = _stack_rgb(0.055, 0.046, 0.040, shape) * branches[:, :, None] * 0.46
    texture = grain[:, :, None] * np.array([0.15, 0.10, 0.055], dtype=np.float32) + scan[:, :, None] * np.array([0.050, 0.075, 0.100], dtype=np.float32)
    contact_specks = _stack_rgb(0.18, 0.13, 0.08, shape) * np.clip(grain + scan * 0.8, 0, 1)[:, :, None] * 0.42
    effect = np.clip(sepia * 0.43 + cyan * 0.54 + ember * 0.82 + ink + texture + contact_specks + haze[:, :, None] * np.array([0.035, 0.044, 0.055], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.020).astype(np.float32))


def _ev67_gargoyle_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        stone = _field(work_shape, seed, 16300, 18.0)
        chisel = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 34.0 + y * 47.0 + stone * 2.1) * np.pi)) * 24.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -43.0 + y * 29.0 + _seed(seed, 16301)) * np.pi)) * 26.0, 0, 1),
        )
        wing = np.zeros(work_shape, dtype=np.float32)
        for cx, flip in ((0.27, -1.0), (0.73, 1.0)):
            for i in range(7):
                curve = 0.42 + (x - cx) * flip * (0.45 + i * 0.035) + (x - cx) ** 2 * (0.45 + i * 0.05)
                rib = np.clip(1.0 - np.abs(y - curve) / (0.004 + i * 0.0004), 0, 1) * (np.abs(x - cx) < 0.28)
                wing = np.maximum(wing, rib * (0.46 + i * 0.04))
        face = np.exp(-(((x - 0.50) / 0.13) ** 2 + ((y - 0.36) / 0.16) ** 2))
        rain = np.clip(1.0 - np.abs(np.sin((x * 7.0 + y * 134.0 + _seed(seed, 16302)) * np.pi)) * 34.0, 0, 1)
        pits = _ev67_microflake(work_shape, seed, 16303)
        detail = np.clip(chisel * 0.42 + wing * 0.44 + face * 0.28 + rain * 0.24 + pits * 0.28 + stone * 0.14, 0, 1)
        if work_shape != tuple(shape):
            grit = _ev67_microflake(shape, seed, 16304)
            pore = _micro_lines(shape, seed, 16305, 503.0, -307.0)
            return np.clip(_fit2(detail, shape) + grit * 0.58 + pore * 0.34, 0, 1), _fit2(chisel, shape), _fit2(wing, shape), _fit2(face, shape), _fit2(stone, shape), grit, pore
        grit = _ev67_microflake(shape, seed, 16304)
        pore = _micro_lines(shape, seed, 16305, 503.0, -307.0)
        return np.clip(detail + grit * 0.48 + pore * 0.28, 0, 1), chisel, wing, face, stone, grit, pore

    return _ev67_wave1_cached("gargoyle_v4", shape, seed, build)


def spec_owner_gargoyle_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, chisel, wing, face, stone, grit, pore = _ev67_gargoyle_v4(shape, seed)
    return _spec_from_fields(shape, mask, 14 + chisel * 104 + wing * 52, 180 - chisel * 86 - wing * 34 + stone * 24, 20 + detail * 128 + face * 38, sm)


def paint_owner_gargoyle_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, chisel, wing, face, stone, grit, pore = _ev67_gargoyle_v4(shape, seed)
    limestone = _stack_rgb(0.13 + stone * 0.20 + chisel * 0.10, 0.145 + stone * 0.20 + wing * 0.08, 0.125 + stone * 0.18, shape)
    rain_dark = _stack_rgb(0.020, 0.045, 0.040, shape) * detail[:, :, None] * 0.18
    eye = _stack_rgb(0.70, 0.86, 0.72, shape) * face[:, :, None] * 0.08
    moss = _stack_rgb(0.026, 0.20, 0.055, shape) * np.clip(detail - 0.38, 0, 1)[:, :, None] * 0.32
    stone_grain = grit[:, :, None] * np.array([0.19, 0.21, 0.17], dtype=np.float32) + pore[:, :, None] * np.array([0.10, 0.12, 0.095], dtype=np.float32)
    effect = np.clip(limestone + moss + eye + stone_grain - rain_dark, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.82), mask, bb, 0.025).astype(np.float32))


def _ev67_death_metal_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        soot = _field(work_shape, seed, 16400, 22.0)
        shards = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 71.0 + y * 23.0 + soot * 3.1) * np.pi)) * 28.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -37.0 + y * 89.0 + _seed(seed, 16401)) * np.pi)) * 30.0, 0, 1),
        )
        strings = np.clip(1.0 - np.abs(np.sin((x * 13.0 + y * 168.0 + _seed(seed, 16402)) * np.pi)) * 38.0, 0, 1)
        skull = np.exp(-(((x - 0.50) / 0.18) ** 2 + ((y - 0.46) / 0.22) ** 2))
        holes = np.exp(-(((x - 0.44) / 0.035) ** 2 + ((y - 0.43) / 0.040) ** 2)) + np.exp(-(((x - 0.56) / 0.035) ** 2 + ((y - 0.43) / 0.040) ** 2))
        skull = np.clip(skull - holes * 0.68, 0, 1)
        dust = _ev67_microflake(work_shape, seed, 16403)
        detail = np.clip(shards * 0.50 + strings * 0.30 + skull * 0.20 + dust * 0.44 + soot * 0.12, 0, 1)
        if work_shape != tuple(shape):
            # SPB paint-finish perf loop 2026-05-31; death_metal measured 4512.6ms -> 3669.5ms.
            # Cache full-res flecks with the shared field so paint does not rebuild them.
            sparks = _ev67_microflake(shape, seed, 16404)
            filings = _micro_lines(shape, seed, 16405, 451.0, -173.0)
            return (
                np.clip(_fit2(detail, shape) + sparks * 0.40 + filings * 0.22, 0, 1),
                _fit2(shards, shape),
                _fit2(strings, shape),
                _fit2(skull, shape),
                _fit2(soot, shape),
                sparks,
                filings,
            )
        sparks = _ev67_microflake(shape, seed, 16404)
        filings = _micro_lines(shape, seed, 16405, 451.0, -173.0)
        return detail, shards, strings, skull, soot, sparks, filings

    return _ev67_wave1_cached("death_metal_v4", shape, seed, build)


def spec_owner_death_metal_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, shards, strings, skull, soot, _, _ = _ev67_death_metal_v4(shape, seed)
    return _spec_from_fields(shape, mask, 22 + shards * 138 + strings * 74, 150 - shards * 88 - strings * 36 + soot * 30, 20 + detail * 122 + skull * 78, sm)


def paint_owner_death_metal_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, shards, strings, skull, soot, sparks, filings = _ev67_death_metal_v4(shape, seed)
    black = _stack_rgb(0.012 + soot * 0.035, 0.010 + soot * 0.020, 0.012 + soot * 0.025, shape)
    steel = _stack_rgb(0.58, 0.60, 0.56, shape) * np.clip(shards + strings * 0.45, 0, 1)[:, :, None] * 0.30
    hot = _stack_rgb(0.74, 0.10, 0.045, shape) * np.clip(strings + detail * 0.24, 0, 1)[:, :, None] * 0.18
    bone = _stack_rgb(0.40, 0.36, 0.28, shape) * skull[:, :, None] * 0.18
    flecks = sparks[:, :, None] * np.array([0.48, 0.18, 0.055], dtype=np.float32) + filings[:, :, None] * np.array([0.16, 0.16, 0.14], dtype=np.float32)
    effect = np.clip(black + steel + hot + bone + flecks + detail[:, :, None] * np.array([0.026, 0.016, 0.018], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_necrotic_v4(shape, seed):
    def build():
        x, y = _xy(shape)
        rot = _field(shape, seed, 16500, 20.0)
        veins = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 82.0 + y * 27.0 + rot * 3.4) * np.pi)) * 32.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -39.0 + y * 101.0 + rot * 2.8) * np.pi)) * 32.0, 0, 1),
        )
        cells = np.clip(1.0 - np.abs(np.sin((x * 96.0 + rot * 4.0) * np.pi) * np.sin((y * 89.0 + rot * 3.6) * np.pi)) * 7.5, 0, 1)
        pits = _ev67_microflake(shape, seed, 16501)
        blister = np.clip(1.0 - np.abs(np.sin((rot * 28.0 + x * 3.0 - y * 2.0) * np.pi)) * 13.0, 0, 1)
        tissue = np.clip(veins * 0.42 + cells * 0.34 + pits * 0.28 + blister * 0.36 + rot * 0.16, 0, 1)
        return tissue, veins, cells, pits, rot

    return _ev67_wave1_cached("necrotic_v4", shape, seed, build)


def spec_owner_necrotic_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    tissue, veins, cells, pits, rot = _ev67_necrotic_v4(shape, seed)
    return _spec_from_fields(shape, mask, 14 + veins * 126 + pits * 78, 188 - veins * 82 - pits * 34 + rot * 18, 18 + tissue * 122 + cells * 48, sm)


def paint_owner_necrotic_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    tissue, veins, cells, pits, rot = _ev67_necrotic_v4(shape, seed)
    base = _stack_rgb(0.070 + rot * 0.12, 0.105 + rot * 0.13, 0.050 + rot * 0.06, shape)
    purple = _stack_rgb(0.27, 0.055, 0.18, shape) * veins[:, :, None] * 0.34
    bile = _stack_rgb(0.38, 0.46, 0.07, shape) * np.clip(cells + pits * 0.5, 0, 1)[:, :, None] * 0.30
    effect = np.clip(base + purple + bile - pits[:, :, None] * 0.05, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.020).astype(np.float32))


def _ev67_fish_eye_v4(shape, seed):
    def build():
        # SPB paint-finish perf loop 2026-05-31; owner: "Speed is king in this app."
        # Fish Eye measured 10058.6ms -> 3640.5ms. Build the analytic lens/crater fields on
        # a bounded grid, then resize so final 8-22px fish-eye defects remain intact.
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        cx_c = x - 0.50; cy_c = y - 0.50
        r = np.sqrt(cx_c * cx_c + cy_c * cy_c)
        lens = np.clip(1.0 - r * 1.92, 0, 1)
        rings = np.clip(1.0 - np.abs(np.sin((r * 62.0 + _field(work_shape, seed, 16600, 2.0) * 2.0) * np.pi)) * 12.0, 0, 1)
        grid = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * (28.0 + lens * 18.0) + r * 6.0) * np.pi)) * 18.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((y * (28.0 + lens * 18.0) + r * 5.0) * np.pi)) * 18.0, 0, 1),
        )
        glints = _ev67_microflake(work_shape, seed, 16601) * np.clip(lens + rings, 0, 1)
        # SPB-108 tick 79 OWNER FIX: owner saw "literally NO effect" after reload.
        # The smooth lens+rings+grid fields read as uniform gradient on the car body
        # because there are NO DISCRETE FISH-EYE DEFECT SPOTS (the name's whole point).
        # Add ~60 small crater spots: dark center + bright rim, 12-24px at 2048².
        # Spots use vectorized distance fields against pre-computed centers.
        rng = np.random.RandomState((int(seed) & 0xFFFF) ^ 16677)
        n_spots = 64
        cy_arr = rng.uniform(0.04, 0.96, n_spots).astype(np.float32)
        cx_arr = rng.uniform(0.04, 0.96, n_spots).astype(np.float32)
        # Spot radius in NORMALIZED coords: 8-22 px / 2048 = 0.0040-0.0107
        rad_arr = rng.uniform(0.0040, 0.0110, n_spots).astype(np.float32)
        spots = np.zeros(work_shape, dtype=np.float32)
        for i in range(n_spots):
            dy_s = y - cy_arr[i]; dx_s = x - cx_arr[i]
            ds = np.sqrt(dy_s * dy_s + dx_s * dx_s)
            rad = rad_arr[i]
            well = np.exp(-(ds * ds) / (2.0 * (rad * 0.42) ** 2))
            rim = np.exp(-((ds - rad) ** 2) / (2.0 * (rad * 0.18) ** 2))
            spots = np.maximum(spots, rim * 0.95 - well * 0.55)
        spots = np.clip(spots, -0.6, 1.0)
        detail = np.clip(lens * 0.20 + rings * 0.30 + grid * 0.22 + glints * 0.28 + spots * 0.55, 0, 1)
        fields = (detail, lens, rings, grid, glints, spots)
        if work_shape != shape:
            fields = tuple(_resize_linear(field, shape) for field in fields)
        return fields

    return _ev67_wave1_cached("fish_eye_v4", shape, seed, build)


def spec_owner_fish_eye_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, lens, rings, grid, glints, spots = _ev67_fish_eye_v4(shape, seed)
    # SPB-108 tick 79 OWNER FIX: spots channel drives ALL three spec channels so the
    # crater defects produce visible R/G/CC variation that reads as fish-eye on car.
    # Spot wells = bright clearcoat ring (B HIGH) around dark dull center (B LOW),
    # roughness spikes UP at well center, metallic low everywhere = realistic spec.
    spot_well = np.clip(-spots, 0, 1)  # the dark center wells
    spot_rim = np.clip(spots, 0, 1)    # the bright rims
    return _spec_from_fields(shape, mask,
        12 + glints * 90 + rings * 50 + spot_rim * 130,                      # R metallic
        58 - glints * 28 + lens * 30 + grid * 16 + spot_well * 80 - spot_rim * 30,  # G roughness
        62 + detail * 110 + rings * 36 + spot_rim * 100 - spot_well * 40,    # B clearcoat
        sm)


def paint_owner_fish_eye_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, lens, rings, grid, glints, spots = _ev67_fish_eye_v4(shape, seed)
    color = _rgb_cycle(lens * 0.62 + rings * 0.16 + _seed(seed, 16602), 0.74, 0.92)
    glass = _stack_rgb(0.022 + lens * 0.050, 0.040 + lens * 0.052, 0.058 + lens * 0.062, shape)
    effect = np.clip(glass + color * (0.10 + rings[:, :, None] * 0.52) + grid[:, :, None] * np.array([0.06, 0.10, 0.12], dtype=np.float32) + glints[:, :, None] * 0.22, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.018).astype(np.float32))


def _ev67_embossed_v4(shape, seed):
    def build():
        x, y = _xy(shape)
        scroll = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 38.0 + y * 24.0 + _field(shape, seed, 16700, 2.2) * 3.0) * np.pi)) * 24.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -27.0 + y * 42.0 + _seed(seed, 16701)) * np.pi)) * 24.0, 0, 1),
        )
        medallion = np.clip(1.0 - np.abs(np.sin((np.sqrt((x - 0.50) ** 2 + (y - 0.50) ** 2) * 34.0 + _seed(seed, 16702)) * np.pi)) * 14.0, 0, 1)
        grain = _ev67_microflake(shape, seed, 16703)
        relief = np.clip(scroll * 0.58 + medallion * 0.38 + grain * 0.28, 0, 1)
        bevel = np.clip(np.abs(relief - _soften(relief, 2)) * 4.4, 0, 1)
        return relief, bevel, scroll, medallion, grain

    return _ev67_wave1_cached("embossed_v4", shape, seed, build)


def spec_owner_embossed_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    relief, bevel, scroll, medallion, grain = _ev67_embossed_v4(shape, seed)
    return _spec_from_fields(shape, mask, 10 + bevel * 138 + grain * 38, 160 - bevel * 112 + relief * 24, 38 + relief * 148 + medallion * 42, sm)


def paint_owner_embossed_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    relief, bevel, scroll, medallion, grain = _ev67_embossed_v4(shape, seed)
    enamel = _stack_rgb(0.12 + relief * 0.24, 0.105 + relief * 0.18, 0.095 + relief * 0.14, shape)
    highlight = _stack_rgb(0.72, 0.62, 0.44, shape) * bevel[:, :, None] * 0.26
    shadow = _stack_rgb(0.030, 0.025, 0.020, shape) * np.clip(scroll - bevel * 0.4, 0, 1)[:, :, None] * 0.20
    effect = np.clip(enamel + highlight - shadow + grain[:, :, None] * np.array([0.035, 0.026, 0.020], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.78), mask, bb, 0.025).astype(np.float32))


def _ev67_shadow_realm_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        detail, portal, void = _ev67_shadow_realm(work_shape, seed)
        x, y = _xy(work_shape)
        glyph = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 41.0 + y * 11.0 + void * 4.5) * np.pi)) * 24.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -17.0 + y * 53.0 + _seed(seed, 16800)) * np.pi)) * 24.0, 0, 1),
        )
        contour = np.clip(1.0 - np.abs(np.sin((portal * 30.0 + void * 2.2) * np.pi)) * 10.0, 0, 1)
        if work_shape != tuple(shape):
            ash = _ev67_microflake(shape, seed, 16801)
            static = _micro_lines(shape, seed, 16802, 389.0, -227.0)
            return np.clip(_fit2(detail, shape) + ash * 0.42 + static * 0.24, 0, 1), _fit2(portal, shape), _fit2(void, shape), _fit2(glyph, shape), _fit2(contour, shape), ash, static
        ash = _ev67_microflake(shape, seed, 16801)
        static = _micro_lines(shape, seed, 16802, 389.0, -227.0)
        return np.clip(detail + ash * 0.36 + static * 0.22, 0, 1), portal, void, glyph, contour, ash, static

    return _ev67_wave1_cached("shadow_realm_v4", shape, seed, build)


def spec_owner_shadow_realm_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, portal, void, glyph, contour, ash, static = _ev67_shadow_realm_v4(shape, seed)
    return _spec_from_fields(shape, mask, 8 + glyph * 102 + contour * 84, 188 - glyph * 94 - contour * 42 + void * 22, 18 + detail * 130 + portal * 74, sm)


def paint_owner_shadow_realm_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, portal, void, glyph, contour, ash, static = _ev67_shadow_realm_v4(shape, seed)
    black = _stack_rgb(0.006 + void * 0.020, 0.005 + void * 0.014, 0.018 + void * 0.046, shape)
    violet = _stack_rgb(0.38, 0.035, 0.72, shape) * np.clip(glyph + detail * 0.22, 0, 1)[:, :, None] * 0.38
    blue = _stack_rgb(0.03, 0.22, 0.82, shape) * portal[:, :, None] * 0.26
    edge = _stack_rgb(0.10, 0.42, 0.88, shape) * contour[:, :, None] * 0.20
    dust = ash[:, :, None] * np.array([0.10, 0.04, 0.18], dtype=np.float32) + static[:, :, None] * np.array([0.035, 0.10, 0.16], dtype=np.float32)
    effect = np.clip(black + violet + blue + edge + dust, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.016).astype(np.float32))


def _ev67_nightmare_v4(shape, seed):
    def build():
        detail, eyes, fever = _ev67_nightmare(_bounded_shape(shape, 768), seed)
        if detail.shape != tuple(shape):
            detail = _fit2(detail, shape)
            eyes = _fit2(eyes, shape)
            fever = _fit2(fever, shape)
        x, y = _xy(shape)
        teeth = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 82.0 + y * 17.0 + fever * 3.4) * np.pi)) * 30.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -39.0 + y * 94.0 + _seed(seed, 16900)) * np.pi)) * 30.0, 0, 1),
        )
        pulse = np.clip(1.0 - np.abs(np.sin((fever * 36.0 + x * 2.2 - y * 1.4) * np.pi)) * 12.0, 0, 1)
        static = _ev67_microflake(shape, seed, 16901)
        scratches = _micro_lines(shape, seed, 16902, -433.0, 181.0)
        return np.clip(detail + teeth * 0.34 + pulse * 0.30 + static * 0.40 + scratches * 0.24, 0, 1), eyes, fever, teeth, pulse, static, scratches

    return _ev67_wave1_cached("nightmare_v4", shape, seed, build)


def spec_owner_nightmare_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, eyes, fever, teeth, pulse, static, scratches = _ev67_nightmare_v4(shape, seed)
    return _spec_from_fields(shape, mask, 12 + teeth * 96 + pulse * 92, 176 - teeth * 96 - eyes * 48 + fever * 24, 18 + detail * 132 + eyes * 96, sm)


def paint_owner_nightmare_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, eyes, fever, teeth, pulse, static, scratches = _ev67_nightmare_v4(shape, seed)
    dark = _stack_rgb(0.010 + fever * 0.042, 0.006 + fever * 0.016, 0.028 + fever * 0.070, shape)
    red = _stack_rgb(0.78, 0.018, 0.11, shape) * np.clip(teeth + detail * 0.26, 0, 1)[:, :, None] * 0.40
    violet = _stack_rgb(0.25, 0.018, 0.66, shape) * pulse[:, :, None] * 0.30
    eye_glow = _stack_rgb(1.00, 0.68, 0.10, shape) * eyes[:, :, None] * 0.48
    grit = static[:, :, None] * np.array([0.20, 0.045, 0.12], dtype=np.float32) + scratches[:, :, None] * np.array([0.10, 0.020, 0.16], dtype=np.float32)
    effect = np.clip(dark + red + violet + eye_glow + grit, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.016).astype(np.float32))


def _ev67_xray_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        fog = _field(work_shape, seed, 17000, 18.0)
        spine = np.clip(1.0 - np.abs(x - 0.50) / 0.0085, 0, 1) * np.clip(1.0 - np.abs(y - 0.52) / 0.43, 0, 1)
        ribs = np.zeros(work_shape, dtype=np.float32)
        for i in range(22):
            cy = 0.105 + i * 0.039
            width = 0.0032 + (i % 4) * 0.00035
            curve_l = cy + (x - 0.49) ** 2 * (0.34 + i * 0.006) - np.abs(x - 0.49) * 0.11
            curve_r = cy + (x - 0.51) ** 2 * (0.34 + i * 0.006) - np.abs(x - 0.51) * 0.11
            gate = np.clip(1.0 - np.abs(x - 0.50) / 0.48, 0, 1)
            ribs = np.maximum(ribs, np.clip(1.0 - np.abs(y - curve_l) / width, 0, 1) * gate)
            ribs = np.maximum(ribs, np.clip(1.0 - np.abs(y - curve_r) / width, 0, 1) * gate)
        joints = (_hash_noise(work_shape, seed, 17001) > 0.977).astype(np.float32) * np.clip(spine + ribs, 0, 1)
        scan = np.clip(1.0 - np.abs(np.sin((y * 720.0 + _seed(seed, 17002)) * np.pi)) * 18.0, 0, 1)
        plate = np.clip(spine * 0.68 + ribs * 0.74 + joints * 0.58 + scan * 0.20 + fog * 0.15, 0, 1)
        ion = _ev67_microflake(shape, seed, 17003)
        hair = _micro_lines(shape, seed, 17004, 521.0, -197.0)
        if work_shape != tuple(shape):
            return np.clip(_fit2(plate, shape) + ion * 0.38 + hair * 0.22, 0, 1), _fit2(spine, shape), _fit2(ribs, shape), _fit2(scan, shape), _fit2(fog, shape), ion, hair
        return np.clip(plate + ion * 0.30 + hair * 0.18, 0, 1), spine, ribs, scan, fog, ion, hair

    return _ev67_wave1_cached("x_ray_v4", shape, seed, build)


def spec_owner_x_ray_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    bones, spine, ribs, scan, fog, ion, hair = _ev67_xray_v4(shape, seed)
    return _spec_from_fields(shape, mask, 24 + bones * 126 + ion * 72, 116 - ribs * 60 + scan * 18 + fog * 24, 34 + bones * 148 + spine * 44 + hair * 52, sm)


def paint_owner_x_ray_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    bones, spine, ribs, scan, fog, ion, hair = _ev67_xray_v4(shape, seed)
    phosphor = _stack_rgb(0.010 + fog * 0.030, 0.052 + fog * 0.090, 0.074 + fog * 0.110, shape)
    cyan = _stack_rgb(0.10, 0.76, 0.94, shape) * bones[:, :, None] * 0.62
    milk = _stack_rgb(0.68, 0.96, 1.0, shape) * np.clip(spine + ribs * 0.76, 0, 1)[:, :, None] * 0.22
    tracer = ion[:, :, None] * np.array([0.06, 0.22, 0.26], dtype=np.float32) + hair[:, :, None] * np.array([0.05, 0.12, 0.15], dtype=np.float32)
    effect = np.clip(phosphor + cyan + milk + tracer + scan[:, :, None] * np.array([0.010, 0.045, 0.060], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_catacombs_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        damp = _field(work_shape, seed, 17100, 19.0)
        arches = np.zeros(work_shape, dtype=np.float32)
        niches = np.zeros(work_shape, dtype=np.float32)
        for i in range(12):
            cx = 0.038 + i * 0.086 + (_seed(seed, 17110 + i) - 0.5) * 0.010
            arch_curve = 0.48 - np.sqrt(np.clip(1.0 - ((x - cx) / 0.040) ** 2, 0, 1)) * 0.128
            arch = np.clip(1.0 - np.abs(y - arch_curve) / 0.0045, 0, 1) * (np.abs(x - cx) < 0.044)
            pillar = ((np.abs(x - cx) < 0.012) & (y > arch_curve) & (y < 0.94)).astype(np.float32)
            niche = np.exp(-(((x - cx) / 0.030) ** 2 + ((y - 0.66 - (i % 3) * 0.055) / 0.040) ** 2))
            arches = np.maximum(arches, np.maximum(arch, pillar) * (0.50 + (i % 4) * 0.08))
            niches = np.maximum(niches, niche * (0.30 + (i % 3) * 0.10))
        mortar = np.maximum(
            np.clip(1.0 - np.abs(np.sin((y * 96.0 + damp * 0.55) * np.pi)) * 22.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * 66.0 + y * 11.0 + _seed(seed, 17102)) * np.pi)) * 24.0, 0, 1),
        )
        bone = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 89.0 + y * 27.0 + damp * 3.0) * np.pi)) * 30.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -41.0 + y * 97.0 + _seed(seed, 17103)) * np.pi)) * 32.0, 0, 1),
        )
        torch, glow_rings = _flare_centers(work_shape, [(0.14, 0.68, 0.045, 0.82), (0.47, 0.55, 0.038, 0.64), (0.82, 0.71, 0.050, 0.72)])
        dust = _ev67_microflake(shape, seed, 17104)
        scratch = _micro_lines(shape, seed, 17105, 347.0, 101.0)
        pore = _micro_lines(shape, seed, 17106, -271.0, 419.0)
        detail = np.clip(arches * 0.40 + mortar * 0.48 + bone * 0.38 + niches * 0.32 + torch * 0.42 + damp * 0.15, 0, 1)
        if work_shape != tuple(shape):
            return np.clip(_fit2(detail, shape) + dust * 0.40 + scratch * 0.24 + pore * 0.18, 0, 1), _fit2(arches, shape), _fit2(mortar, shape), _fit2(torch, shape), _fit2(damp, shape), dust, scratch, pore
        return np.clip(detail + dust * 0.34 + scratch * 0.20 + pore * 0.16, 0, 1), arches, mortar, torch, damp, dust, scratch, pore

    return _ev67_wave1_cached("catacombs_v4", shape, seed, build)


def spec_owner_catacombs_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, arches, mortar, torch, damp, dust, scratch, pore = _ev67_catacombs_v4(shape, seed)
    return _spec_from_fields(shape, mask, 18 + torch * 126 + scratch * 70 + dust * 52, 188 - arches * 72 - scratch * 42 + damp * 22, 18 + detail * 136 + torch * 78 + pore * 42, sm)


def paint_owner_catacombs_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, arches, mortar, torch, damp, dust, scratch, pore = _ev67_catacombs_v4(shape, seed)
    stone = _stack_rgb(0.075 + damp * 0.065 + arches * 0.13, 0.070 + damp * 0.055 + mortar * 0.08, 0.060 + damp * 0.045, shape)
    amber = _stack_rgb(0.86, 0.32, 0.055, shape) * torch[:, :, None] * 0.48
    bone = _stack_rgb(0.46, 0.39, 0.27, shape) * detail[:, :, None] * 0.18
    native = dust[:, :, None] * np.array([0.13, 0.11, 0.080], dtype=np.float32) + scratch[:, :, None] * np.array([0.09, 0.075, 0.055], dtype=np.float32) + pore[:, :, None] * np.array([0.04, 0.05, 0.045], dtype=np.float32)
    effect = np.clip(stone + amber + bone + native - damp[:, :, None] * np.array([0.020, 0.025, 0.024], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.020).astype(np.float32))


def _ev67_film_burn_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        emulsion = _field(work_shape, seed, 17200, 24.0)
        edge_bloom = np.clip((1.0 - x) ** 5.2 * 0.50 + (1.0 - y) ** 8.0 * 0.28 + x ** 10.0 * 0.18, 0, 1)
        scorch = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 31.0 + y * 12.0 + emulsion * 3.1) * np.pi)) * 20.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -23.0 + y * 47.0 + _seed(seed, 17201)) * np.pi)) * 22.0, 0, 1),
        )
        sprocket = np.clip(1.0 - np.abs(np.sin((y * 27.0 + _seed(seed, 17202)) * np.pi)) * 20.0, 0, 1) * ((x < 0.075) | (x > 0.925))
        ash = _ev67_microflake(shape, seed, 17203)
        scratches = _micro_lines(shape, seed, 17204, 119.0, 571.0)
        grain = _ev67_scan_grain(shape, seed, 17205)
        detail = np.clip(edge_bloom * 0.38 + scorch * 0.54 + sprocket * 0.44 + emulsion * 0.18, 0, 1)
        if work_shape != tuple(shape):
            return np.clip(_fit2(detail, shape) + ash * 0.46 + scratches * 0.30 + grain * 0.24, 0, 1), _fit2(edge_bloom, shape), _fit2(scorch, shape), _fit2(sprocket, shape), _fit2(emulsion, shape), ash, scratches, grain
        return np.clip(detail + ash * 0.40 + scratches * 0.26 + grain * 0.22, 0, 1), edge_bloom, scorch, sprocket, emulsion, ash, scratches, grain

    return _ev67_wave1_cached("film_burn_v4", shape, seed, build)


def spec_owner_film_burn_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, bloom, scorch, sprocket, emulsion, ash, scratches, grain = _ev67_film_burn_v4(shape, seed)
    return _spec_from_fields(shape, mask, 24 + scorch * 106 + ash * 70 + sprocket * 44, 164 - scorch * 82 - scratches * 48 + emulsion * 28, 20 + detail * 126 + bloom * 54 + grain * 34, sm)


def paint_owner_film_burn_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, bloom, scorch, sprocket, emulsion, ash, scratches, grain = _ev67_film_burn_v4(shape, seed)
    sepia = _stack_rgb(0.20 + emulsion * 0.13, 0.080 + emulsion * 0.060, 0.032 + emulsion * 0.030, shape)
    ember = _stack_rgb(0.95, 0.30, 0.040, shape) * np.clip(scorch + bloom * 0.32, 0, 1)[:, :, None] * 0.52
    gold = _stack_rgb(1.00, 0.60, 0.10, shape) * bloom[:, :, None] * 0.22
    film = sprocket[:, :, None] * np.array([0.10, 0.055, 0.030], dtype=np.float32)
    texture = ash[:, :, None] * np.array([0.20, 0.075, 0.030], dtype=np.float32) + scratches[:, :, None] * np.array([0.18, 0.13, 0.090], dtype=np.float32) + grain[:, :, None] * np.array([0.055, 0.045, 0.042], dtype=np.float32)
    effect = np.clip(sepia + ember + gold + film + texture, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.020).astype(np.float32))


def _ev67_long_exposure_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        haze = _field(work_shape, seed, 17300, 21.0)
        lanes = np.zeros(work_shape, dtype=np.float32)
        skyline = np.zeros(work_shape, dtype=np.float32)
        for i in range(13):
            slope = -0.42 + i * 0.070
            center = 0.06 + i * 0.072 + (_seed(seed, 17310 + i) - 0.5) * 0.030
            width = 0.0032 + (i % 4) * 0.0010
            trail = np.clip(1.0 - np.abs((y - (center + x * slope)) / width), 0, 1)
            lanes = np.maximum(lanes, trail * (0.44 + (i % 5) * 0.12))
        for i in range(18):
            bx = 0.02 + (i * 0.071) % 0.96
            bh = 0.08 + _seed(seed, 17340 + i) * 0.18
            building = ((np.abs(x - bx) < 0.010 + (i % 3) * 0.004) & (y > 0.78 - bh) & (y < 0.84)).astype(np.float32)
            skyline = np.maximum(skyline, building * (0.25 + (i % 4) * 0.05))
        stars = (_hash_noise(work_shape, seed, 17301) > 0.988).astype(np.float32)
        rain = _ev67_microflake(shape, seed, 17302)
        hair = _micro_lines(shape, seed, 17303, 633.0, -83.0)
        scan = _ev67_scan_grain(shape, seed, 17304)
        detail = np.clip(lanes * 0.70 + skyline * 0.30 + _soften(stars, 1) * 0.42 + haze * 0.14, 0, 1)
        if work_shape != tuple(shape):
            return np.clip(_fit2(detail, shape) + rain * 0.34 + hair * 0.24 + scan * 0.18, 0, 1), _fit2(lanes, shape), _fit2(skyline, shape), _fit2(haze, shape), rain, hair, scan
        return np.clip(detail + rain * 0.30 + hair * 0.20 + scan * 0.16, 0, 1), lanes, skyline, haze, rain, hair, scan

    return _ev67_wave1_cached("long_exposure_v4", shape, seed, build)


def spec_owner_long_exposure_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, lanes, skyline, haze, rain, hair, scan = _ev67_long_exposure_v4(shape, seed)
    return _spec_from_fields(shape, mask, 22 + lanes * 138 + rain * 62, 134 - lanes * 78 + haze * 26 - hair * 28, 22 + detail * 134 + scan * 38, sm)


def paint_owner_long_exposure_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, lanes, skyline, haze, rain, hair, scan = _ev67_long_exposure_v4(shape, seed)
    color = _rgb_cycle(haze * 0.56 + lanes * 0.30 + _seed(seed, 17305), 0.92, 1.0)
    night = _stack_rgb(0.009 + haze * 0.026, 0.014 + haze * 0.030, 0.032 + haze * 0.060, shape)
    trail = color * lanes[:, :, None] * 0.94
    city = skyline[:, :, None] * np.array([0.075, 0.085, 0.120], dtype=np.float32)
    wet = rain[:, :, None] * np.array([0.10, 0.12, 0.15], dtype=np.float32) + hair[:, :, None] * np.array([0.080, 0.060, 0.12], dtype=np.float32)
    effect = np.clip(night + trail + city + wet + scan[:, :, None] * np.array([0.020, 0.020, 0.035], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_solarization_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        tone = np.clip(_field(work_shape, seed, 17400, 20.0) * 0.50 + x * 0.24 + (1.0 - y) * 0.20, 0, 1)
        contour = np.clip(1.0 - np.abs(np.sin((tone * 31.0 + x * 2.8 - y * 2.0) * np.pi)) * 10.0, 0, 1)
        halo = np.clip(1.0 - np.abs(tone - 0.50) * 8.5, 0, 1)
        silver = _ev67_microflake(shape, seed, 17401)
        print_grain = _ev67_scan_grain(shape, seed, 17402)
        relief = _micro_lines(shape, seed, 17403, 281.0, 241.0)
        if work_shape != tuple(shape):
            contour = _fit2(contour, shape)
            halo = _fit2(halo, shape)
            tone = _fit2(tone, shape)
        detail = np.clip(contour * 0.62 + halo * 0.38 + silver * 0.34 + print_grain * 0.26 + relief * 0.20, 0, 1)
        return detail, contour, halo, tone, silver, print_grain, relief

    return _ev67_wave1_cached("solarization_v4", shape, seed, build)


def spec_owner_solarization_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, contour, halo, tone, silver, print_grain, relief = _ev67_solarization_v4(shape, seed)
    return _spec_from_fields(shape, mask, 18 + contour * 116 + silver * 92, 126 - contour * 76 + tone * 26 - relief * 28, 20 + detail * 142 + halo * 48 + print_grain * 40, sm)


def paint_owner_solarization_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, contour, halo, tone, silver, print_grain, relief = _ev67_solarization_v4(shape, seed)
    color = _rgb_cycle(0.12 + tone * 0.82 + contour * 0.10, 0.80, 0.94)
    print_base = _stack_rgb(0.018 + tone * 0.070, 0.018 + tone * 0.044, 0.022 + tone * 0.075, shape)
    reversal = color * (0.16 + contour[:, :, None] * 0.72 + halo[:, :, None] * 0.18)
    grain = silver[:, :, None] * np.array([0.20, 0.18, 0.13], dtype=np.float32) + print_grain[:, :, None] * np.array([0.060, 0.045, 0.055], dtype=np.float32)
    effect = np.clip(print_base + reversal + grain + relief[:, :, None] * np.array([0.050, 0.030, 0.060], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.018).astype(np.float32))


def _ev67_parallax_v4(shape, seed):
    def build():
        x, y = _xy(shape)
        depth = _field(shape, seed, 17500, 18.0)
        far = np.clip(1.0 - np.abs(np.sin((x * 19.0 + y * 13.0 + depth * 2.2) * np.pi)) * 16.0, 0, 1)
        mid = np.clip(1.0 - np.abs(np.sin(((x + depth * 0.025) * 37.0 - y * 9.0 + _seed(seed, 17501)) * np.pi)) * 20.0, 0, 1)
        near = np.clip(1.0 - np.abs(np.sin(((x - depth * 0.040) * -47.0 + y * 29.0 + _seed(seed, 17502)) * np.pi)) * 22.0, 0, 1)
        ticks = np.clip(1.0 - np.abs(np.sin((depth * 39.0 + x * 3.0 - y * 2.2) * np.pi)) * 12.0, 0, 1)
        flecks = _ev67_microflake(shape, seed, 17503)
        hair = _micro_lines(shape, seed, 17504, -397.0, 521.0)
        ghost = np.clip(np.roll(far, 8, axis=1) * 0.38 + np.roll(mid, -11, axis=0) * 0.34 + np.roll(near, -13, axis=1) * 0.42, 0, 1)
        detail = np.clip(far * 0.34 + mid * 0.40 + near * 0.48 + ticks * 0.34 + flecks * 0.36 + hair * 0.24 + ghost * 0.28, 0, 1)
        return detail, depth, far, mid, near, ticks, flecks, hair, ghost

    return _ev67_wave1_cached("parallax_v4", shape, seed, build)


def spec_owner_parallax_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, depth, far, mid, near, ticks, flecks, hair, ghost = _ev67_parallax_v4(shape, seed)
    return _spec_from_fields(shape, mask, 16 + near * 102 + ticks * 74 + flecks * 62, 118 - near * 56 + depth * 32 - hair * 24, 24 + detail * 136 + ghost * 62, sm)


def paint_owner_parallax_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, depth, far, mid, near, ticks, flecks, hair, ghost = _ev67_parallax_v4(shape, seed)
    base = _stack_rgb(0.012 + depth * 0.024, 0.020 + depth * 0.034, 0.038 + depth * 0.070, shape)
    far_c = _stack_rgb(0.055, 0.22, 0.54, shape) * far[:, :, None] * 0.34
    mid_c = _stack_rgb(0.30, 0.11, 0.66, shape) * mid[:, :, None] * 0.36
    near_c = _stack_rgb(0.08, 0.72, 0.82, shape) * near[:, :, None] * 0.40
    reveal = ticks[:, :, None] * np.array([0.12, 0.20, 0.26], dtype=np.float32) + flecks[:, :, None] * np.array([0.10, 0.18, 0.22], dtype=np.float32) + ghost[:, :, None] * np.array([0.08, 0.045, 0.15], dtype=np.float32)
    effect = np.clip(base + far_c + mid_c + near_c + reveal + hair[:, :, None] * np.array([0.035, 0.060, 0.080], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_voodoo_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        cloth = _field(work_shape, seed, 17600, 22.0)
        stitches = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 72.0 + y * 29.0 + cloth * 3.2) * np.pi)) * 30.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((x * -31.0 + y * 93.0 + _seed(seed, 17601)) * np.pi)) * 30.0, 0, 1),
        )
        veve = np.zeros(work_shape, dtype=np.float32)
        for i, (cx, cy, rad) in enumerate(((0.28, 0.34, 0.16), (0.68, 0.44, 0.19), (0.48, 0.72, 0.15))):
            dx = x - cx
            dy = y - cy
            dist = np.sqrt(dx * dx + dy * dy)
            angle = np.arctan2(dy, dx)
            ring = np.clip(1.0 - np.abs(dist - rad) / 0.0048, 0, 1)
            spokes = np.clip(1.0 - np.abs(np.sin((angle * (6 + i * 2) + cloth * 0.8) * 0.5)) * 18.0, 0, 1) * (dist < rad)
            veve = np.maximum(veve, ring * 0.64 + spokes * 0.34)
        pins = (_hash_noise(work_shape, seed, 17602) > 0.985).astype(np.float32) * np.clip(stitches + veve, 0, 1)
        wax = np.clip(1.0 - np.abs(np.sin((cloth * 28.0 + x * 2.0) * np.pi)) * 13.0, 0, 1)
        thread = _ev67_microflake(shape, seed, 17603)
        fiber = _micro_lines(shape, seed, 17604, 457.0, 311.0)
        knots = _micro_lines(shape, seed, 17605, -613.0, 191.0)
        detail = np.clip(stitches * 0.44 + veve * 0.54 + pins * 0.48 + wax * 0.26 + cloth * 0.14, 0, 1)
        if work_shape != tuple(shape):
            return np.clip(_fit2(detail, shape) + thread * 0.70 + fiber * 0.42 + knots * 0.26, 0, 1), _fit2(stitches, shape), _fit2(veve, shape), _fit2(pins, shape), _fit2(wax, shape), _fit2(cloth, shape), thread, np.clip(fiber + knots * 0.54, 0, 1)
        return np.clip(detail + thread * 0.52 + fiber * 0.32 + knots * 0.22, 0, 1), stitches, veve, pins, wax, cloth, thread, np.clip(fiber + knots * 0.54, 0, 1)

    return _ev67_wave1_cached("voodoo_v4", shape, seed, build)


def spec_owner_voodoo_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, stitches, veve, pins, wax, cloth, thread, fiber = _ev67_voodoo_v4(shape, seed)
    return _spec_from_fields(shape, mask, 18 + pins * 136 + veve * 70 + thread * 54, 176 - stitches * 76 - pins * 54 + cloth * 22, 20 + detail * 132 + wax * 72 + fiber * 38, sm)


def paint_owner_voodoo_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, stitches, veve, pins, wax, cloth, thread, fiber = _ev67_voodoo_v4(shape, seed)
    burlap = _stack_rgb(0.12 + cloth * 0.10, 0.070 + cloth * 0.055, 0.045 + cloth * 0.040, shape)
    red_thread = _stack_rgb(0.68, 0.025, 0.040, shape) * stitches[:, :, None] * 0.38
    chalk = _stack_rgb(0.72, 0.62, 0.42, shape) * veve[:, :, None] * 0.28
    wax_gold = _stack_rgb(0.86, 0.48, 0.10, shape) * wax[:, :, None] * 0.20
    metal_pins = _stack_rgb(0.72, 0.76, 0.68, shape) * pins[:, :, None] * 0.24
    micro = thread[:, :, None] * np.array([0.18, 0.080, 0.052], dtype=np.float32) + fiber[:, :, None] * np.array([0.12, 0.070, 0.046], dtype=np.float32)
    effect = np.clip(burlap + red_thread + chalk + wax_gold + metal_pins + micro, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.020).astype(np.float32))


def _ev67_iron_maiden_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 768)
        x, y = _xy(work_shape)
        soot = _field(work_shape, seed, 17700, 18.0)
        bars = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 42.0 + _seed(seed, 17701)) * np.pi)) * 26.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((y * 58.0 + _seed(seed, 17702)) * np.pi)) * 30.0, 0, 1),
        )
        spikes = np.zeros(work_shape, dtype=np.float32)
        for i in range(26):
            cx = 0.04 + (i * 0.073) % 0.92
            cy = 0.12 + ((i * 7) % 13) * 0.058
            tri = np.maximum(0.0, 1.0 - np.abs(x - cx) / 0.018 - np.maximum(0.0, np.abs(y - cy) / 0.070))
            spikes = np.maximum(spikes, tri * (0.44 + (i % 5) * 0.08))
        rivets = (_hash_noise(work_shape, seed, 17703) > 0.980).astype(np.float32) * np.clip(bars + spikes, 0, 1)
        rust = np.clip(1.0 - np.abs(np.sin((soot * 25.0 + x * 4.0 - y * 3.0) * np.pi)) * 12.0, 0, 1)
        filings = _ev67_microflake(shape, seed, 17704)
        scratches = _micro_lines(shape, seed, 17705, 527.0, -251.0)
        edge = _micro_lines(shape, seed, 17706, -383.0, 449.0)
        detail = np.clip(bars * 0.42 + spikes * 0.58 + rivets * 0.40 + rust * 0.30 + soot * 0.12, 0, 1)
        if work_shape != tuple(shape):
            return np.clip(_fit2(detail, shape) + filings * 0.38 + scratches * 0.24 + edge * 0.18, 0, 1), _fit2(bars, shape), _fit2(spikes, shape), _fit2(rivets, shape), _fit2(rust, shape), _fit2(soot, shape), filings, scratches, edge
        return np.clip(detail + filings * 0.34 + scratches * 0.22 + edge * 0.16, 0, 1), bars, spikes, rivets, rust, soot, filings, scratches, edge

    return _ev67_wave1_cached("iron_maiden_v4", shape, seed, build)


def spec_owner_iron_maiden_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, bars, spikes, rivets, rust, soot, filings, scratches, edge = _ev67_iron_maiden_v4(shape, seed)
    return _spec_from_fields(shape, mask, 20 + spikes * 126 + rivets * 92 + filings * 58, 150 - spikes * 82 - edge * 40 + rust * 44 + soot * 18, 18 + detail * 134 + scratches * 42, sm)


def paint_owner_iron_maiden_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, bars, spikes, rivets, rust, soot, filings, scratches, edge = _ev67_iron_maiden_v4(shape, seed)
    black = _stack_rgb(0.014 + soot * 0.034, 0.012 + soot * 0.025, 0.014 + soot * 0.020, shape)
    steel = _stack_rgb(0.42, 0.44, 0.40, shape) * np.clip(bars + spikes * 0.75 + rivets * 0.62, 0, 1)[:, :, None] * 0.36
    rust_c = _stack_rgb(0.55, 0.16, 0.032, shape) * rust[:, :, None] * 0.34
    blood = _stack_rgb(0.46, 0.015, 0.030, shape) * np.clip(scratches + rust * 0.36, 0, 1)[:, :, None] * 0.18
    heat_blue = _stack_rgb(0.045, 0.16, 0.34, shape) * np.clip(edge + soot * 0.30, 0, 1)[:, :, None] * 0.16
    verdigris = _stack_rgb(0.030, 0.18, 0.12, shape) * np.clip(filings + rust * 0.24, 0, 1)[:, :, None] * 0.12
    edge_c = _stack_rgb(0.78, 0.78, 0.66, shape) * edge[:, :, None] * 0.16
    micro = filings[:, :, None] * np.array([0.20, 0.18, 0.13], dtype=np.float32) + scratches[:, :, None] * np.array([0.13, 0.075, 0.065], dtype=np.float32)
    effect = np.clip(black + steel + rust_c + blood + heat_blue + verdigris + edge_c + micro, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_disk_field(shape, centers):
    x, y = _xy(shape)
    fill = np.zeros(shape, dtype=np.float32)
    ring = np.zeros(shape, dtype=np.float32)
    for cx, cy, rx, ry, power in centers:
        d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        body = np.clip(1.0 - d, 0, 1) ** 1.8
        edge = np.clip(1.0 - np.abs(d - 1.0) / 0.070, 0, 1)
        fill = np.maximum(fill, body * power)
        ring = np.maximum(ring, edge * power)
    return fill.astype(np.float32), ring.astype(np.float32)


def _ev67_arc_bundle(shape, seed, salt, count, y0, amp, width, bend=0.10):
    x, y = _xy(shape)
    out = np.zeros(shape, dtype=np.float32)
    for i in range(count):
        phase = _seed(seed, salt + i * 7)
        center = y0 + (i / max(1, count - 1) - 0.5) * amp + (phase - 0.5) * amp * 0.18
        curve = center + np.sin((x * (1.15 + phase * 0.70) + phase) * np.pi * 2.0) * bend * (0.45 + phase * 0.55)
        curve += (x - 0.5) ** 2 * bend * (0.35 + 0.70 * _seed(seed, salt + 101 + i))
        stroke = np.clip(1.0 - np.abs(y - curve) / (width * (0.75 + (i % 4) * 0.16)), 0, 1)
        out = np.maximum(out, stroke * (0.45 + (i % 5) * 0.10))
    return out.astype(np.float32)


def _ev67_wave3_xray_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 640)
        x, y = _xy(work_shape)
        fog = _field(work_shape, seed, 18000, 16.0)
        spine = np.clip(1.0 - np.abs(x - 0.50) / 0.0075, 0, 1) * np.clip(1.0 - np.abs(y - 0.52) / 0.42, 0, 1)
        vertebrae = np.zeros(work_shape, dtype=np.float32)
        ribs = np.zeros(work_shape, dtype=np.float32)
        for i in range(24):
            cy = 0.085 + i * 0.036
            vertebrae = np.maximum(vertebrae, np.exp(-(((x - 0.50) / 0.018) ** 2 + ((y - cy) / 0.010) ** 2)) * (0.44 + (i % 4) * 0.08))
            spread = np.clip(1.0 - np.abs(x - 0.50) / 0.47, 0, 1)
            bow = cy + (np.abs(x - 0.50) ** 1.62) * (0.46 + i * 0.004) - np.abs(x - 0.50) * 0.135
            ribs = np.maximum(ribs, np.clip(1.0 - np.abs(y - bow) / (0.0028 + (i % 3) * 0.00035), 0, 1) * spread)
        hand = np.zeros(work_shape, dtype=np.float32)
        palm, palm_ring = _ev67_disk_field(work_shape, [(0.77, 0.67, 0.060, 0.085, 0.75)])
        hand = np.maximum(hand, palm)
        for f in range(5):
            fx = 0.70 + f * 0.030
            for j in range(4):
                hand = np.maximum(hand, np.exp(-(((x - (fx + (j - 1.4) * 0.006)) / 0.010) ** 2 + ((y - (0.54 - j * 0.043 + abs(f - 2) * 0.006)) / 0.014) ** 2)) * 0.58)
        calibration = np.zeros(work_shape, dtype=np.float32)
        for i in range(18):
            tick_y = 0.10 + i * 0.045
            calibration = np.maximum(calibration, ((np.abs(x - 0.060) < (0.007 + (i % 3) * 0.004)) & (np.abs(y - tick_y) < 0.0025)).astype(np.float32) * 0.72)
        trabeculae = _ev67_speckle_field(shape, seed, 18001)
        phosphor = _ev67_grit_field(shape, seed, 18002)
        if work_shape != tuple(shape):
            anatomy = _fit2(np.clip(spine * 0.52 + vertebrae * 0.62 + ribs * 0.58 + hand * 0.50 + calibration * 0.42 + fog * 0.11, 0, 1), shape)
            return anatomy, _fit2(spine, shape), _fit2(vertebrae, shape), _fit2(ribs, shape), _fit2(hand + palm_ring * 0.25, shape), _fit2(calibration, shape), _fit2(fog, shape), trabeculae, phosphor
        anatomy = np.clip(spine * 0.52 + vertebrae * 0.62 + ribs * 0.58 + hand * 0.50 + calibration * 0.42 + fog * 0.11, 0, 1)
        return anatomy, spine, vertebrae, ribs, hand + palm_ring * 0.25, calibration, fog, trabeculae, phosphor

    return _ev67_wave1_cached("x_ray_v5", shape, seed, build)


def spec_owner_x_ray_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    anatomy, spine, vertebrae, ribs, hand, calibration, fog, trabeculae, phosphor = _ev67_wave3_xray_v5(shape, seed)
    metal = 18 + anatomy * 118 + vertebrae * 52 + calibration * 96 + trabeculae * 74
    rough = 132 - ribs * 46 - hand * 34 + fog * 22 - phosphor * 24
    coat = 32 + anatomy * 138 + spine * 42 + hand * 66 + phosphor * 56
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_x_ray_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    anatomy, spine, vertebrae, ribs, hand, calibration, fog, trabeculae, phosphor = _ev67_wave3_xray_v5(shape, seed)
    plate = _stack_rgb(0.006 + fog * 0.026, 0.060 + fog * 0.090, 0.082 + fog * 0.116, shape)
    bone = _stack_rgb(0.42, 0.94, 1.0, shape) * np.clip(anatomy + vertebrae * 0.34 + hand * 0.22, 0, 1)[:, :, None] * 0.58
    glass = _stack_rgb(0.025, 0.26, 0.34, shape) * phosphor[:, :, None] * 0.42
    spec_hint = trabeculae[:, :, None] * np.array([0.08, 0.28, 0.30], dtype=np.float32) + calibration[:, :, None] * np.array([0.20, 0.68, 0.78], dtype=np.float32)
    effect = np.clip(plate + bone + glass + spec_hint + spine[:, :, None] * np.array([0.10, 0.52, 0.70], dtype=np.float32) * 0.22, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.016).astype(np.float32))


def _ev67_wave3_catacombs_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 640)
        x, y = _xy(work_shape)
        damp = _field(work_shape, seed, 18100, 18.0)
        vaults = np.zeros(work_shape, dtype=np.float32)
        niches = np.zeros(work_shape, dtype=np.float32)
        skulls = np.zeros(work_shape, dtype=np.float32)
        for row, base_y in enumerate((0.30, 0.52, 0.74)):
            for i in range(9):
                cx = 0.06 + i * 0.112 + (row % 2) * 0.036
                rad = 0.044 + (i % 3) * 0.004
                arch_y = base_y - np.sqrt(np.clip(1.0 - ((x - cx) / rad) ** 2, 0, 1)) * (0.090 + row * 0.010)
                arch = np.clip(1.0 - np.abs(y - arch_y) / 0.0042, 0, 1) * (np.abs(x - cx) < rad)
                pillar = ((np.abs(x - cx) < 0.0065) & (y > arch_y) & (y < base_y + 0.13)).astype(np.float32)
                niche = np.exp(-(((x - cx) / 0.026) ** 2 + ((y - (base_y + 0.058)) / 0.033) ** 2))
                skull = np.exp(-(((x - (cx - 0.010)) / 0.010) ** 2 + ((y - (base_y + 0.060)) / 0.011) ** 2))
                skull += np.exp(-(((x - (cx + 0.010)) / 0.010) ** 2 + ((y - (base_y + 0.060)) / 0.011) ** 2))
                vaults = np.maximum(vaults, np.maximum(arch, pillar) * (0.50 + row * 0.10))
                niches = np.maximum(niches, niche * 0.56)
                skulls = np.maximum(skulls, skull * 0.44)
        block = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 34.0 + damp * 0.28) * np.pi)) * 18.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((y * 48.0 + damp * 0.34) * np.pi)) * 18.0, 0, 1),
        )
        torches, wax_halo = _flare_centers(work_shape, [(0.17, 0.62, 0.035, 0.80), (0.50, 0.36, 0.028, 0.62), (0.83, 0.64, 0.034, 0.76)])
        mineral = _ev67_speckle_field(shape, seed, 18101)
        soot = _ev67_grit_field(shape, seed, 18102)
        if work_shape != tuple(shape):
            semantic = _fit2(np.clip(vaults * 0.48 + niches * 0.40 + skulls * 0.38 + block * 0.32 + torches * 0.46 + damp * 0.12, 0, 1), shape)
            return semantic, _fit2(vaults, shape), _fit2(niches, shape), _fit2(skulls, shape), _fit2(block, shape), _fit2(torches, shape), _fit2(damp, shape), mineral, soot
        semantic = np.clip(vaults * 0.48 + niches * 0.40 + skulls * 0.38 + block * 0.32 + torches * 0.46 + damp * 0.12, 0, 1)
        return semantic, vaults, niches, skulls, block, torches, damp, mineral, soot

    return _ev67_wave1_cached("catacombs_v5", shape, seed, build)


def spec_owner_catacombs_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, vaults, niches, skulls, block, torches, damp, mineral, soot = _ev67_wave3_catacombs_v5(shape, seed)
    metal = 14 + torches * 140 + skulls * 82 + mineral * 64
    rough = 192 - vaults * 58 - block * 34 + damp * 22 + soot * 18
    coat = 18 + torches * 118 + niches * 70 + detail * 104 + mineral * 42
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_catacombs_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, vaults, niches, skulls, block, torches, damp, mineral, soot = _ev67_wave3_catacombs_v5(shape, seed)
    stone = _stack_rgb(0.050 + damp * 0.055 + block * 0.060, 0.050 + damp * 0.050 + block * 0.050, 0.045 + damp * 0.042, shape)
    bone = _stack_rgb(0.58, 0.49, 0.34, shape) * np.clip(skulls + niches * 0.34, 0, 1)[:, :, None] * 0.30
    fire = _stack_rgb(0.98, 0.34, 0.050, shape) * torches[:, :, None] * 0.54
    moss = _stack_rgb(0.035, 0.135, 0.082, shape) * np.clip(damp + niches * 0.30, 0, 1)[:, :, None] * 0.18
    micro = mineral[:, :, None] * np.array([0.30, 0.26, 0.190], dtype=np.float32) + soot[:, :, None] * np.array([0.080, 0.070, 0.058], dtype=np.float32)
    effect = np.clip(stone + bone + fire + moss + vaults[:, :, None] * np.array([0.12, 0.09, 0.062], dtype=np.float32) + micro, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_wave3_film_burn_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 640)
        x, y = _xy(work_shape)
        emulsion = _field(work_shape, seed, 18200, 22.0)
        burns, burn_edges = _ev67_disk_field(
            work_shape,
            [
                (0.12, 0.20, 0.095, 0.155, 0.82),
                (0.92, 0.74, 0.080, 0.190, 0.72),
                (0.50, 0.08, 0.145, 0.060, 0.60),
                (0.33, 0.58, 0.065, 0.110, 0.54),
            ],
        )
        frames = np.zeros(work_shape, dtype=np.float32)
        sprocket = np.zeros(work_shape, dtype=np.float32)
        for i in range(5):
            x0 = 0.08 + i * 0.19
            frames = np.maximum(frames, ((np.abs(x - x0) < 0.004) | (np.abs(x - (x0 + 0.145)) < 0.004) | (np.abs(y - 0.16) < 0.003) | (np.abs(y - 0.84) < 0.003)).astype(np.float32) * ((x > x0) & (x < x0 + 0.145)).astype(np.float32) * 0.48)
        for i in range(18):
            sy = 0.045 + i * 0.052
            sprocket = np.maximum(sprocket, np.exp(-(((x - 0.038) / 0.012) ** 2 + ((y - sy) / 0.012) ** 2)))
            sprocket = np.maximum(sprocket, np.exp(-(((x - 0.962) / 0.012) ** 2 + ((y - sy) / 0.012) ** 2)))
        bubbles = (_hash_noise(work_shape, seed, 18201) > 0.988).astype(np.float32) * np.clip(burns + emulsion * 0.5, 0, 1)
        grain = _ev67_grit_field(shape, seed, 18202)
        silver = _ev67_speckle_field(shape, seed, 18203)
        if work_shape != tuple(shape):
            detail = _fit2(np.clip(burns * 0.58 + burn_edges * 0.48 + sprocket * 0.42 + frames * 0.34 + bubbles * 0.50 + emulsion * 0.16, 0, 1), shape)
            return detail, _fit2(burns, shape), _fit2(burn_edges, shape), _fit2(sprocket, shape), _fit2(frames, shape), _fit2(bubbles, shape), _fit2(emulsion, shape), grain, silver
        detail = np.clip(burns * 0.58 + burn_edges * 0.48 + sprocket * 0.42 + frames * 0.34 + bubbles * 0.50 + emulsion * 0.16, 0, 1)
        return detail, burns, burn_edges, sprocket, frames, bubbles, emulsion, grain, silver

    return _ev67_wave1_cached("film_burn_v5", shape, seed, build)


def spec_owner_film_burn_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, burns, burn_edges, sprocket, frames, bubbles, emulsion, grain, silver = _ev67_wave3_film_burn_v5(shape, seed)
    metal = 18 + burn_edges * 124 + sprocket * 70 + silver * 82 + bubbles * 54
    rough = 168 - burn_edges * 88 - bubbles * 50 + emulsion * 32 + grain * 22
    coat = 18 + detail * 138 + burns * 66 + frames * 42 + grain * 40
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_film_burn_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, burns, burn_edges, sprocket, frames, bubbles, emulsion, grain, silver = _ev67_wave3_film_burn_v5(shape, seed)
    acetate = _stack_rgb(0.075 + emulsion * 0.070, 0.038 + emulsion * 0.038, 0.026 + emulsion * 0.030, shape)
    amber = _stack_rgb(1.00, 0.42, 0.055, shape) * burns[:, :, None] * 0.62
    edge = _stack_rgb(1.00, 0.74, 0.16, shape) * burn_edges[:, :, None] * 0.38
    film = sprocket[:, :, None] * np.array([0.16, 0.080, 0.034], dtype=np.float32) + frames[:, :, None] * np.array([0.13, 0.060, 0.028], dtype=np.float32)
    micro = bubbles[:, :, None] * np.array([0.90, 0.42, 0.11], dtype=np.float32) + grain[:, :, None] * np.array([0.055, 0.044, 0.038], dtype=np.float32) + silver[:, :, None] * np.array([0.18, 0.12, 0.070], dtype=np.float32)
    effect = np.clip(acetate + amber + edge + film + micro, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.018).astype(np.float32))


def _ev67_wave3_film_burn_v6(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 512)
        x, y = _xy(work_shape)
        heat = _field(work_shape, seed, 19200, 14.0)
        leak_left = np.exp(-((x / 0.105) ** 2)) * (0.72 + heat * 0.42)
        leak_top = np.exp(-((y / 0.070) ** 2)) * (0.50 + _field(work_shape, seed, 19201, 6.0) * 0.38)
        leak_corner = np.exp(-(((x - 0.06) / 0.18) ** 2 + ((y - 0.12) / 0.24) ** 2)) * 0.72
        scorch = np.clip((heat - 0.47) * 2.35, 0, 1) * np.clip(leak_left + leak_top + leak_corner * 0.75, 0, 1)
        char = np.clip((heat - 0.70) * 3.20, 0, 1) * np.clip(leak_left + leak_corner, 0, 1)
        melt = np.zeros(work_shape, dtype=np.float32)
        for i in range(11):
            cx = 0.11 + i * 0.074 + (_seed(seed, 19220 + i) - 0.5) * 0.018
            width = 0.0028 + _seed(seed, 19240 + i) * 0.0035
            length = 0.24 + _seed(seed, 19260 + i) * 0.42
            trail = np.exp(-((x - cx) / width) ** 2) * np.clip(1.0 - y / length, 0, 1)
            melt = np.maximum(melt, trail * (0.34 + _seed(seed, 19280 + i) * 0.46))
        frames = np.zeros(work_shape, dtype=np.float32)
        for x0 in (0.18, 0.38, 0.58, 0.78):
            vertical = (np.abs(x - x0) < 0.0032).astype(np.float32) * (y > 0.09) * (y < 0.91)
            frames = np.maximum(frames, vertical)
        frames = np.maximum(frames, ((np.abs(y - 0.115) < 0.0028) | (np.abs(y - 0.885) < 0.0028)).astype(np.float32))
        sprocket = np.zeros(work_shape, dtype=np.float32)
        for i in range(19):
            sy = 0.040 + i * 0.0515
            hole = (np.abs(y - sy) < 0.010) & ((np.abs(x - 0.035) < 0.009) | (np.abs(x - 0.965) < 0.009))
            sprocket = np.maximum(sprocket, hole.astype(np.float32))
        blister = ((heat > 0.62) & (_hash_noise(work_shape, seed, 19290) > 0.972)).astype(np.float32)
        detail = np.clip(leak_left * 0.42 + leak_top * 0.28 + scorch * 0.64 + char * 0.62 + melt * 0.48 + frames * 0.26 + sprocket * 0.46 + blister * 0.40, 0, 1)
        if work_shape != tuple(shape):
            heat = _fit2(heat, shape)
            detail = _fit2(detail, shape)
            leak_left = _fit2(leak_left, shape)
            leak_top = _fit2(leak_top, shape)
            scorch = _fit2(scorch, shape)
            char = _fit2(char, shape)
            melt = _fit2(melt, shape)
            frames = _fit2(frames, shape)
            sprocket = _fit2(sprocket, shape)
            blister = _fit2(blister, shape)
        grain_noise = _hash_noise(shape, seed, 19291)
        grain = np.clip((grain_noise > 0.905).astype(np.float32) * 0.14 + (grain_noise > 0.970).astype(np.float32) * 0.34, 0, 1)
        silver = (grain_noise > 0.988).astype(np.float32) * np.clip(1.0 - char, 0, 1)
        return detail, heat, leak_left, leak_top, scorch, char, melt, frames, sprocket, blister, grain, silver

    return _ev67_wave1_cached("film_burn_v6", shape, seed, build)


def spec_owner_film_burn_v6(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, heat, leak_left, leak_top, scorch, char, melt, frames, sprocket, blister, grain, silver = _ev67_wave3_film_burn_v6(shape, seed)
    metal = 12 + scorch * 92 + melt * 56 + sprocket * 66 + silver * 118 + blister * 44
    rough = 186 + char * 24 + heat * 16 - scorch * 62 - melt * 36 + grain * 18
    coat = 16 + leak_left * 80 + leak_top * 56 + detail * 92 + frames * 34 + blister * 62
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((metal + silver * 44 + blister * 26) * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(rough * mask + 80 * (1.0 - mask), 12, 210).astype(np.uint8)
    spec[:, :, 2] = np.clip((coat + melt * 30 + scorch * 18) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_film_burn_v6(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, heat, leak_left, leak_top, scorch, char, melt, frames, sprocket, blister, grain, silver = _ev67_wave3_film_burn_v6(shape, seed)
    leak_mask = np.clip(leak_left * 0.80 + leak_top * 0.48, 0, 1)
    effect = np.empty((shape[0], shape[1], 3), dtype=np.float32)
    effect[:, :, 0] = (
        0.056
        + heat * 0.045
        + leak_mask * 0.520
        + scorch * 0.440
        + melt * 0.360
        + frames * 0.120
        + sprocket * 0.260
        + grain * 0.070
        + silver * 0.240
        + blister * 0.820
        - char * 0.013
    )
    effect[:, :, 1] = (
        0.031
        + heat * 0.026
        + leak_mask * 0.302
        + scorch * 0.125
        + melt * 0.130
        + frames * 0.055
        + sprocket * 0.110
        + grain * 0.048
        + silver * 0.170
        + blister * 0.280
        - char * 0.007
    )
    effect[:, :, 2] = (
        0.024
        + heat * 0.018
        + leak_mask * 0.057
        + scorch * 0.018
        + melt * 0.022
        + frames * 0.026
        + sprocket * 0.035
        + grain * 0.034
        + silver * 0.095
        + blister * 0.060
        - char * 0.004
    )
    effect = np.clip(effect, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.016).astype(np.float32))


def _ev67_wave3_long_exposure_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 640)
        x, y = _xy(work_shape)
        haze = _field(work_shape, seed, 18300, 17.0)
        trails = _ev67_arc_bundle(work_shape, seed, 18310, 18, 0.50, 0.78, 0.0038, 0.085)
        reflections = np.clip(np.roll(trails, int(work_shape[0] * 0.22), axis=0) * (y > 0.55) * (1.0 - (y - 0.55) * 1.1), 0, 1)
        skyline = np.zeros(work_shape, dtype=np.float32)
        windows = np.zeros(work_shape, dtype=np.float32)
        for i in range(22):
            bx = 0.012 + (i * 0.053) % 0.96
            bw = 0.012 + (i % 4) * 0.005
            top = 0.52 + _seed(seed, 18340 + i) * 0.20
            building = ((np.abs(x - bx) < bw) & (y > top) & (y < 0.86)).astype(np.float32)
            skyline = np.maximum(skyline, building * (0.20 + (i % 5) * 0.045))
            win = building * (_hash_noise(work_shape, seed, 18380 + i) > 0.82).astype(np.float32)
            windows = np.maximum(windows, win * 0.56)
        bokeh = (_hash_noise(work_shape, seed, 18301) > 0.993).astype(np.float32)
        rain = _ev67_speckle_field(shape, seed, 18302)
        wet = _ev67_grit_field(shape, seed, 18303)
        if work_shape != tuple(shape):
            semantic = _fit2(np.clip(trails * 0.74 + reflections * 0.36 + skyline * 0.26 + windows * 0.42 + _soften(bokeh, 1) * 0.38 + haze * 0.11, 0, 1), shape)
            return semantic, _fit2(trails, shape), _fit2(reflections, shape), _fit2(skyline, shape), _fit2(windows, shape), _fit2(bokeh, shape), _fit2(haze, shape), rain, wet
        semantic = np.clip(trails * 0.74 + reflections * 0.36 + skyline * 0.26 + windows * 0.42 + _soften(bokeh, 1) * 0.38 + haze * 0.11, 0, 1)
        return semantic, trails, reflections, skyline, windows, bokeh, haze, rain, wet

    return _ev67_wave1_cached("long_exposure_v5", shape, seed, build)


def spec_owner_long_exposure_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, trails, reflections, skyline, windows, bokeh, haze, rain, wet = _ev67_wave3_long_exposure_v5(shape, seed)
    metal = 20 + trails * 136 + bokeh * 124 + rain * 58
    rough = 132 - trails * 76 - reflections * 36 + haze * 28 - wet * 26
    coat = 24 + detail * 142 + reflections * 72 + windows * 58 + wet * 44
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_long_exposure_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, trails, reflections, skyline, windows, bokeh, haze, rain, wet = _ev67_wave3_long_exposure_v5(shape, seed)
    trail_color = _rgb_cycle(haze * 0.34 + trails * 0.52 + _seed(seed, 18305), 0.96, 1.0)
    night = _stack_rgb(0.008 + haze * 0.018, 0.010 + haze * 0.024, 0.026 + haze * 0.055, shape)
    light = trail_color * trails[:, :, None] * 0.96
    mirror = trail_color * reflections[:, :, None] * 0.34
    city = skyline[:, :, None] * np.array([0.055, 0.060, 0.086], dtype=np.float32) + windows[:, :, None] * np.array([0.92, 0.62, 0.22], dtype=np.float32) * 0.32
    sparkle = rain[:, :, None] * np.array([0.08, 0.13, 0.16], dtype=np.float32) + wet[:, :, None] * np.array([0.030, 0.045, 0.070], dtype=np.float32) + bokeh[:, :, None] * np.array([1.0, 0.62, 0.22], dtype=np.float32) * 0.44
    effect = np.clip(night + light + mirror + city + sparkle, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.016).astype(np.float32))


def _ev67_wave3_solarization_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 512)
        x, y = _xy(work_shape)
        tone = np.clip(_field(work_shape, seed, 18400, 20.0) * 0.40 + x * 0.22 + (1.0 - y) * 0.25, 0, 1)
        face, face_edge = _ev67_disk_field(work_shape, [(0.39, 0.43, 0.125, 0.180, 0.72), (0.61, 0.52, 0.105, 0.145, 0.54)])
        eye = np.exp(-(((x - 0.38) / 0.020) ** 2 + ((y - 0.40) / 0.012) ** 2)) + np.exp(-(((x - 0.60) / 0.020) ** 2 + ((y - 0.48) / 0.012) ** 2))
        contour = np.clip(1.0 - np.abs(np.sin(((tone + face * 0.18) * 34.0 + face_edge * 0.9) * np.pi)) * 8.0, 0, 1)
        chemistry = np.clip(1.0 - np.abs(np.sin((tone * 17.0 + x * 1.3 + y * 2.1) * np.pi)) * 10.0, 0, 1)
        silver = _ev67_speckle_field(shape, seed, 18401)
        grain = _ev67_grit_field(shape, seed, 18402)
        if work_shape != tuple(shape):
            detail = _fit2(np.clip(contour * 0.58 + face_edge * 0.36 + eye * 0.40 + chemistry * 0.36 + tone * 0.08, 0, 1), shape)
            return detail, _fit2(contour, shape), _fit2(face, shape), _fit2(face_edge, shape), _fit2(eye, shape), _fit2(chemistry, shape), _fit2(tone, shape), silver, grain
        detail = np.clip(contour * 0.58 + face_edge * 0.36 + eye * 0.40 + chemistry * 0.36 + tone * 0.08, 0, 1)
        return detail, contour, face, face_edge, eye, chemistry, tone, silver, grain

    return _ev67_wave1_cached("solarization_v5", shape, seed, build)


def spec_owner_solarization_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, contour, face, face_edge, eye, chemistry, tone, silver, grain = _ev67_wave3_solarization_v5(shape, seed)
    metal = 18 + contour * 118 + silver * 104 + eye * 88
    rough = 128 - contour * 72 + tone * 32 - face_edge * 34 + grain * 18
    coat = 22 + detail * 144 + chemistry * 58 + face_edge * 54 + grain * 42
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_solarization_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, contour, face, face_edge, eye, chemistry, tone, silver, grain = _ev67_wave3_solarization_v5(shape, seed)
    reversal = _rgb_cycle(0.10 + tone * 0.78 + contour * 0.16, 0.88, 0.96)
    darkroom = _stack_rgb(0.020 + tone * 0.050, 0.014 + tone * 0.030, 0.030 + tone * 0.075, shape)
    face_color = _stack_rgb(0.95, 0.22, 0.72, shape) * np.clip(face + face_edge * 0.45, 0, 1)[:, :, None] * 0.20
    cyan_edge = _stack_rgb(0.04, 0.80, 0.86, shape) * np.clip(contour + eye * 0.45, 0, 1)[:, :, None] * 0.44
    chem = chemistry[:, :, None] * np.array([0.35, 0.12, 0.48], dtype=np.float32) + silver[:, :, None] * np.array([0.16, 0.16, 0.13], dtype=np.float32) + grain[:, :, None] * np.array([0.050, 0.038, 0.055], dtype=np.float32)
    effect = np.clip(darkroom + reversal * detail[:, :, None] * 0.48 + face_color + cyan_edge + chem, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.016).astype(np.float32))


def _ev67_wave3_parallax_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 640)
        x, y = _xy(work_shape)
        depth = _field(work_shape, seed, 18500, 17.0)
        island = np.zeros(work_shape, dtype=np.float32)
        edges = np.zeros(work_shape, dtype=np.float32)
        for i, (cx, cy, rx, ry) in enumerate(((0.23, 0.28, 0.17, 0.10), (0.62, 0.35, 0.20, 0.13), (0.44, 0.70, 0.18, 0.12), (0.78, 0.72, 0.14, 0.09))):
            shifted_x = x + (i - 1.5) * 0.018 * depth
            shifted_y = y - (i - 1.0) * 0.014 * depth
            d = ((shifted_x - cx) / rx) ** 2 + ((shifted_y - cy) / ry) ** 2
            body = np.clip(1.0 - d, 0, 1) ** 1.6
            ring = np.clip(1.0 - np.abs(d - 1.0) / 0.055, 0, 1)
            island = np.maximum(island, body * (0.42 + i * 0.08))
            edges = np.maximum(edges, ring * (0.58 + i * 0.07))
        stereo = np.clip(np.roll(edges, 9, axis=1) * 0.42 + np.roll(edges, -13, axis=1) * 0.48 + np.roll(island, -8, axis=0) * 0.26, 0, 1)
        depth_ticks = np.clip(1.0 - np.abs(np.sin((depth * 31.0 + island * 2.7) * np.pi)) * 11.0, 0, 1) * np.clip(island + edges, 0, 1)
        prism = _ev67_speckle_field(shape, seed, 18501)
        haze = _ev67_grit_field(shape, seed, 18502)
        if work_shape != tuple(shape):
            detail = _fit2(np.clip(island * 0.32 + edges * 0.58 + stereo * 0.46 + depth_ticks * 0.44 + depth * 0.10, 0, 1), shape)
            return detail, _fit2(depth, shape), _fit2(island, shape), _fit2(edges, shape), _fit2(stereo, shape), _fit2(depth_ticks, shape), prism, haze
        detail = np.clip(island * 0.32 + edges * 0.58 + stereo * 0.46 + depth_ticks * 0.44 + depth * 0.10, 0, 1)
        return detail, depth, island, edges, stereo, depth_ticks, prism, haze

    return _ev67_wave1_cached("parallax_v5", shape, seed, build)


def spec_owner_parallax_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, depth, island, edges, stereo, depth_ticks, prism, haze = _ev67_wave3_parallax_v5(shape, seed)
    metal = 18 + edges * 112 + stereo * 94 + prism * 72
    rough = 122 - edges * 58 + depth * 34 - depth_ticks * 32 + haze * 18
    coat = 24 + detail * 136 + stereo * 76 + depth_ticks * 56 + prism * 44
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_parallax_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, depth, island, edges, stereo, depth_ticks, prism, haze = _ev67_wave3_parallax_v5(shape, seed)
    base = _stack_rgb(0.012 + depth * 0.020, 0.022 + depth * 0.034, 0.048 + depth * 0.074, shape)
    cyan = _stack_rgb(0.05, 0.76, 0.86, shape) * edges[:, :, None] * 0.50
    violet = _stack_rgb(0.44, 0.08, 0.84, shape) * stereo[:, :, None] * 0.42
    glass = _stack_rgb(0.07, 0.22, 0.62, shape) * island[:, :, None] * 0.30
    amber = _stack_rgb(0.95, 0.42, 0.10, shape) * depth_ticks[:, :, None] * 0.20
    ticks = depth_ticks[:, :, None] * np.array([0.22, 0.72, 0.70], dtype=np.float32) + prism[:, :, None] * np.array([0.18, 0.20, 0.30], dtype=np.float32) + haze[:, :, None] * np.array([0.032, 0.046, 0.070], dtype=np.float32)
    effect = np.clip(base + cyan + violet + glass + amber + ticks, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.016).astype(np.float32))


def _ev67_wave3_voodoo_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 512)
        x, y = _xy(work_shape)
        cloth = _field(work_shape, seed, 18600, 18.0)
        doll, doll_edge = _ev67_disk_field(work_shape, [(0.50, 0.53, 0.070, 0.160, 0.64), (0.50, 0.30, 0.052, 0.060, 0.56), (0.43, 0.49, 0.032, 0.110, 0.42), (0.57, 0.49, 0.032, 0.110, 0.42)])
        veve = np.zeros(work_shape, dtype=np.float32)
        for i, (cx, cy, rad, spokes) in enumerate(((0.25, 0.35, 0.15, 7), (0.73, 0.45, 0.17, 9), (0.49, 0.75, 0.13, 5))):
            dx = x - cx
            dy = y - cy
            dist = np.sqrt(dx * dx + dy * dy)
            angle = np.arctan2(dy, dx)
            ring = np.clip(1.0 - np.abs(dist - rad) / 0.0045, 0, 1)
            petals = np.clip(1.0 - np.abs(dist - rad * (0.55 + 0.12 * np.sin(angle * spokes))) / 0.004, 0, 1)
            rays = np.clip(1.0 - np.abs(np.sin(angle * spokes)) * 18.0, 0, 1) * (dist < rad)
            veve = np.maximum(veve, ring * 0.54 + petals * 0.44 + rays * 0.25)
        stitch_cross = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 56.0 + cloth * 1.2) * np.pi)) * 24.0, 0, 1) * doll_edge,
            np.clip(1.0 - np.abs(np.sin((y * 64.0 + cloth * 1.0) * np.pi)) * 24.0, 0, 1) * doll_edge,
        )
        pins = (_hash_noise(work_shape, seed, 18601) > 0.987).astype(np.float32) * np.clip(doll + veve, 0, 1)
        wax, wax_edge = _ev67_disk_field(work_shape, [(0.18, 0.78, 0.045, 0.065, 0.62), (0.83, 0.19, 0.038, 0.060, 0.48)])
        thread = _ev67_speckle_field(shape, seed, 18602)
        fiber = _ev67_grit_field(shape, seed, 18603)
        if work_shape != tuple(shape):
            detail = _fit2(np.clip(doll * 0.46 + doll_edge * 0.58 + veve * 0.72 + stitch_cross * 0.66 + pins * 0.54 + wax * 0.42 + cloth * 0.15, 0, 1), shape)
            return detail, _fit2(doll, shape), _fit2(doll_edge, shape), _fit2(veve, shape), _fit2(stitch_cross, shape), _fit2(pins, shape), _fit2(wax + wax_edge * 0.35, shape), _fit2(cloth, shape), thread, fiber
        detail = np.clip(doll * 0.46 + doll_edge * 0.58 + veve * 0.72 + stitch_cross * 0.66 + pins * 0.54 + wax * 0.42 + cloth * 0.15, 0, 1)
        return detail, doll, doll_edge, veve, stitch_cross, pins, wax + wax_edge * 0.35, cloth, thread, fiber

    return _ev67_wave1_cached("voodoo_v5", shape, seed, build)


def spec_owner_voodoo_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, doll, doll_edge, veve, stitch_cross, pins, wax, cloth, thread, fiber = _ev67_wave3_voodoo_v5(shape, seed)
    metal = 16 + pins * 142 + veve * 72 + thread * 62
    rough = 182 - stitch_cross * 68 - pins * 52 + cloth * 28 + fiber * 18
    coat = 18 + detail * 132 + wax * 82 + doll_edge * 48 + fiber * 36
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_voodoo_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, doll, doll_edge, veve, stitch_cross, pins, wax, cloth, thread, fiber = _ev67_wave3_voodoo_v5(shape, seed)
    burlap = _stack_rgb(0.115 + cloth * 0.110, 0.066 + cloth * 0.060, 0.040 + cloth * 0.040, shape)
    doll_color = _stack_rgb(0.34, 0.17, 0.080, shape) * doll[:, :, None] * 0.42
    chalk = _stack_rgb(0.90, 0.76, 0.44, shape) * veve[:, :, None] * 0.42
    crimson = _stack_rgb(0.74, 0.018, 0.040, shape) * np.clip(stitch_cross + doll_edge * 0.45, 0, 1)[:, :, None] * 0.50
    metal = _stack_rgb(0.75, 0.78, 0.68, shape) * pins[:, :, None] * 0.28
    candle = _stack_rgb(0.95, 0.50, 0.10, shape) * wax[:, :, None] * 0.24
    indigo = _stack_rgb(0.16, 0.060, 0.34, shape) * np.clip(veve + pins * 0.25, 0, 1)[:, :, None] * 0.18
    verdant = _stack_rgb(0.020, 0.34, 0.13, shape) * np.clip(thread + wax * 0.22, 0, 1)[:, :, None] * 0.14
    micro = thread[:, :, None] * np.array([0.34, 0.135, 0.074], dtype=np.float32) + fiber[:, :, None] * np.array([0.120, 0.078, 0.050], dtype=np.float32)
    effect = np.clip(burlap + doll_color + chalk + crimson + metal + candle + indigo + verdant + micro, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_wave3_iron_maiden_v5(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 640)
        x, y = _xy(work_shape)
        soot = _field(work_shape, seed, 18700, 18.0)
        door = np.zeros(work_shape, dtype=np.float32)
        door_edge = np.zeros(work_shape, dtype=np.float32)
        arch_y = 0.76 - np.sqrt(np.clip(1.0 - ((x - 0.50) / 0.32) ** 2, 0, 1)) * 0.42
        inside = ((np.abs(x - 0.50) < 0.32) & (y > arch_y) & (y < 0.94)).astype(np.float32)
        door = np.maximum(door, inside * 0.46)
        door_edge = np.maximum(door_edge, np.clip(1.0 - np.abs(y - arch_y) / 0.005, 0, 1) * (np.abs(x - 0.50) < 0.33))
        seam = np.clip(1.0 - np.abs(x - 0.50) / 0.004, 0, 1) * inside
        spikes = np.zeros(work_shape, dtype=np.float32)
        for i in range(34):
            cx = 0.22 + (i % 7) * 0.092
            cy = 0.22 + (i // 7) * 0.120
            tri = np.maximum(0.0, 1.0 - np.abs(x - cx) / 0.014 - np.maximum(0.0, (y - cy) / 0.070) - np.maximum(0.0, (cy - y) / 0.020))
            spikes = np.maximum(spikes, tri * inside * (0.48 + (i % 4) * 0.08))
        chain = np.zeros(work_shape, dtype=np.float32)
        for i in range(11):
            cx = 0.16 + i * 0.068
            cy = 0.15 + 0.022 * np.sin(i * 1.7)
            link, link_edge = _ev67_disk_field(work_shape, [(cx, cy, 0.024, 0.014, 0.56)])
            chain = np.maximum(chain, link_edge)
        rivets = (_hash_noise(work_shape, seed, 18701) > 0.984).astype(np.float32) * np.clip(door_edge + seam + chain, 0, 1)
        rust = np.clip(1.0 - np.abs(np.sin((soot * 21.0 + door * 2.2) * np.pi)) * 12.0, 0, 1) * inside
        filings = _ev67_speckle_field(shape, seed, 18702)
        patina = _ev67_grit_field(shape, seed, 18703)
        if work_shape != tuple(shape):
            detail = _fit2(np.clip(door * 0.34 + door_edge * 0.48 + seam * 0.38 + spikes * 0.60 + chain * 0.42 + rivets * 0.44 + rust * 0.32 + soot * 0.10, 0, 1), shape)
            return detail, _fit2(door, shape), _fit2(door_edge + seam, shape), _fit2(spikes, shape), _fit2(chain, shape), _fit2(rivets, shape), _fit2(rust, shape), _fit2(soot, shape), filings, patina
        detail = np.clip(door * 0.34 + door_edge * 0.48 + seam * 0.38 + spikes * 0.60 + chain * 0.42 + rivets * 0.44 + rust * 0.32 + soot * 0.10, 0, 1)
        return detail, door, door_edge + seam, spikes, chain, rivets, rust, soot, filings, patina

    return _ev67_wave1_cached("iron_maiden_v5", shape, seed, build)


def spec_owner_iron_maiden_v5(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, door, door_edge, spikes, chain, rivets, rust, soot, filings, patina = _ev67_wave3_iron_maiden_v5(shape, seed)
    metal = 24 + spikes * 144 + chain * 122 + rivets * 112 + filings * 74 + door_edge * 26
    rough = 154 - spikes * 72 - door_edge * 46 + rust * 48 + soot * 20 + patina * 16
    coat = 18 + detail * 132 + door_edge * 58 + patina * 42
    return _spec_from_fields(shape, mask, metal, rough, coat, sm)


def paint_owner_iron_maiden_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, door, door_edge, spikes, chain, rivets, rust, soot, filings, patina = _ev67_wave3_iron_maiden_v5(shape, seed)
    black = _stack_rgb(0.011 + soot * 0.030, 0.010 + soot * 0.022, 0.012 + soot * 0.022, shape)
    steel = _stack_rgb(0.36, 0.38, 0.35, shape) * np.clip(door + spikes * 0.78 + chain * 0.65 + rivets * 0.50, 0, 1)[:, :, None] * 0.46
    hot_edge = _stack_rgb(0.82, 0.80, 0.63, shape) * door_edge[:, :, None] * 0.20
    rust_c = _stack_rgb(0.58, 0.15, 0.028, shape) * rust[:, :, None] * 0.36
    bruise = _stack_rgb(0.030, 0.12, 0.30, shape) * np.clip(soot + patina * 0.30, 0, 1)[:, :, None] * 0.16
    micro = filings[:, :, None] * np.array([0.30, 0.26, 0.18], dtype=np.float32) + patina[:, :, None] * np.array([0.055, 0.105, 0.078], dtype=np.float32)
    effect = np.clip(black + steel + hot_edge + rust_c + bruise + micro, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.016).astype(np.float32))


def _ev67_wave4_eclipse_v3(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 560)
        x, y = _xy(work_shape)
        cx = 0.50 + (_seed(seed, 18800) - 0.5) * 0.035
        cy = 0.47 + (_seed(seed, 18801) - 0.5) * 0.030
        dx = x - cx
        dy = y - cy
        d = np.sqrt(dx * dx + dy * dy)
        angle = np.arctan2(dy, dx)
        void = np.clip(1.0 - d / 0.245, 0, 1)
        corona = np.clip(1.0 - np.abs(d - 0.265) / 0.018, 0, 1)
        beads = np.clip(1.0 - np.abs(d - 0.290) / 0.006, 0, 1) * (np.sin(angle * 37.0 + seed * 0.017) > 0.52).astype(np.float32)
        flare = np.clip(1.0 - np.abs(d - (0.310 + 0.016 * np.sin(angle * 9.0 + seed * 0.013))) / 0.007, 0, 1)
        orbits = np.zeros(work_shape, dtype=np.float32)
        for i, rr in enumerate((0.37, 0.44, 0.51)):
            orbits = np.maximum(orbits, np.clip(1.0 - np.abs(d - rr) / 0.0038, 0, 1) * (0.28 + i * 0.07) * (np.sin(angle * (17 + i * 6)) > -0.35).astype(np.float32))
        dust = _ev67_speckle_field(shape, seed, 18802)
        grit = _ev67_grit_field(shape, seed, 18803)
        if work_shape != tuple(shape):
            return _fit2(void, shape), _fit2(np.clip(corona + beads * 0.70 + flare * 0.45 + orbits * 0.22, 0, 1), shape), _fit2(beads, shape), _fit2(flare, shape), _fit2(orbits, shape), dust, grit
        return void, np.clip(corona + beads * 0.70 + flare * 0.45 + orbits * 0.22, 0, 1), beads, flare, orbits, dust, grit

    return _ev67_wave1_cached("eclipse_v3", shape, seed, build)


def spec_owner_eclipse_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    void, corona, beads, flare, orbits, dust, grit = _ev67_wave4_eclipse_v3(shape, seed)
    return _spec_from_fields(shape, mask, 18 + corona * 176 + beads * 98 + dust * 58, 156 - corona * 104 + void * 38 + grit * 20, 22 + corona * 172 + flare * 80 + orbits * 50, sm)


def paint_owner_eclipse_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    void, corona, beads, flare, orbits, dust, grit = _ev67_wave4_eclipse_v3(shape, seed)
    night = _stack_rgb(0.004 + grit * 0.010, 0.006 + grit * 0.012, 0.020 + grit * 0.040, shape)
    fire = _stack_rgb(1.00, 0.62, 0.10, shape) * corona[:, :, None] * 0.70
    pearl = _stack_rgb(1.00, 0.90, 0.58, shape) * np.clip(beads + flare * 0.45, 0, 1)[:, :, None] * 0.38
    violet = _stack_rgb(0.18, 0.06, 0.32, shape) * orbits[:, :, None] * 0.24
    effect = np.clip(night * (1.0 - void[:, :, None] * 0.76) + fire + pearl + violet + dust[:, :, None] * np.array([0.18, 0.16, 0.13], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.014).astype(np.float32))


def _ev67_wave4_spectral_v3(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 560)
        veils, veil_edge = _ev67_disk_field(work_shape, [(0.24, 0.36, 0.13, 0.21, 0.52), (0.55, 0.52, 0.18, 0.25, 0.62), (0.80, 0.40, 0.12, 0.20, 0.48)])
        phase = np.clip(1.0 - np.abs(np.sin((_field(work_shape, seed, 19400, 18.0) * 25.0 + veils * 2.0) * np.pi)) * 12.0, 0, 1) * np.clip(veils + veil_edge * 0.5, 0, 1)
        glint = _ev67_speckle_field(shape, seed, 19401)
        mist = _ev67_grit_field(shape, seed, 19402)
        if work_shape != tuple(shape):
            return np.clip(_fit2(veils * 0.34 + veil_edge * 0.48 + phase * 0.46, shape) + glint * 0.34 + mist * 0.20, 0, 1), _fit2(veils, shape), _fit2(veil_edge, shape), _fit2(phase, shape), glint, mist
        return np.clip(veils * 0.34 + veil_edge * 0.48 + phase * 0.46 + glint * 0.28 + mist * 0.16, 0, 1), veils, veil_edge, phase, glint, mist

    return _ev67_wave1_cached("spectral_v3", shape, seed, build)


def spec_owner_spectral_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, veils, edge, phase, glint, mist = _ev67_wave4_spectral_v3(shape, seed)
    return _spec_from_fields(shape, mask, 16 + edge * 104 + phase * 82 + glint * 72, 136 - phase * 62 + mist * 24, 24 + detail * 138 + veils * 54 + glint * 52, sm)


def paint_owner_spectral_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, veils, edge, phase, glint, mist = _ev67_wave4_spectral_v3(shape, seed)
    deep = _stack_rgb(0.012 + mist * 0.030, 0.030 + mist * 0.050, 0.064 + mist * 0.090, shape)
    cyan = _stack_rgb(0.08, 0.74, 0.88, shape) * edge[:, :, None] * 0.42
    violet = _stack_rgb(0.42, 0.08, 0.78, shape) * phase[:, :, None] * 0.38
    pearl = _stack_rgb(0.66, 0.94, 1.00, shape) * veils[:, :, None] * 0.20
    green = _stack_rgb(0.04, 0.34, 0.24, shape) * glint[:, :, None] * 0.18
    effect = np.clip(deep + cyan + violet + pearl + green + glint[:, :, None] * np.array([0.14, 0.22, 0.26], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.016).astype(np.float32))


def _ev67_wave4_haunted_v3(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 560)
        x, y = _xy(work_shape)
        window = np.zeros(work_shape, dtype=np.float32)
        frame = np.zeros(work_shape, dtype=np.float32)
        for i, cx in enumerate((0.24, 0.50, 0.76)):
            body = ((np.abs(x - cx) < 0.060) & (y > 0.28) & (y < 0.74)).astype(np.float32)
            arch = np.exp(-(((x - cx) / 0.058) ** 2 + ((y - 0.28) / 0.045) ** 2))
            window = np.maximum(window, np.clip(body + arch, 0, 1) * (0.42 + i * 0.05))
            frame = np.maximum(frame, np.clip(1.0 - np.abs(np.abs(x - cx) - 0.060) / 0.004, 0, 1) * (y > 0.30) * (y < 0.74))
            frame = np.maximum(frame, np.clip(1.0 - np.abs(y - 0.74) / 0.004, 0, 1) * (np.abs(x - cx) < 0.060))
        ghost, ghost_edge = _ev67_disk_field(work_shape, [(0.50, 0.58, 0.075, 0.140, 0.58)])
        wallpaper = np.clip(1.0 - np.abs(np.sin((_field(work_shape, seed, 19500, 13.0) * 22.0 + window * 1.4) * np.pi)) * 12.0, 0, 1)
        dust = _ev67_speckle_field(shape, seed, 19501)
        plaster = _ev67_grit_field(shape, seed, 19502)
        if work_shape != tuple(shape):
            return np.clip(_fit2(window * 0.42 + frame * 0.58 + ghost * 0.36 + ghost_edge * 0.50 + wallpaper * 0.30, shape) + dust * 0.46 + plaster * 0.34, 0, 1), _fit2(window, shape), _fit2(frame, shape), _fit2(ghost, shape), _fit2(ghost_edge, shape), _fit2(wallpaper, shape), dust, plaster
        return np.clip(window * 0.42 + frame * 0.58 + ghost * 0.36 + ghost_edge * 0.50 + wallpaper * 0.30 + dust * 0.38 + plaster * 0.28, 0, 1), window, frame, ghost, ghost_edge, wallpaper, dust, plaster

    return _ev67_wave1_cached("haunted_v3", shape, seed, build)


def spec_owner_haunted_v3(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, window, frame, ghost, ghost_edge, wallpaper, dust, plaster = _ev67_wave4_haunted_v3(shape, seed)
    return _spec_from_fields(shape, mask, 18 + frame * 104 + ghost_edge * 88 + dust * 60, 154 - ghost * 70 - window * 38 + plaster * 24, 20 + detail * 132 + wallpaper * 48 + dust * 40, sm)


def paint_owner_haunted_v3(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, window, frame, ghost, ghost_edge, wallpaper, dust, plaster = _ev67_wave4_haunted_v3(shape, seed)
    room = _stack_rgb(0.024 + plaster * 0.038, 0.040 + plaster * 0.058, 0.058 + plaster * 0.076, shape)
    cyan = _stack_rgb(0.18, 0.76, 0.86, shape) * np.clip(window + ghost * 0.34, 0, 1)[:, :, None] * 0.44
    white = _stack_rgb(0.66, 0.94, 0.96, shape) * ghost_edge[:, :, None] * 0.30
    wood = _stack_rgb(0.22, 0.125, 0.068, shape) * frame[:, :, None] * 0.34
    violet = _stack_rgb(0.22, 0.060, 0.32, shape) * np.clip(wallpaper + ghost * 0.20, 0, 1)[:, :, None] * 0.26
    amber = _stack_rgb(0.80, 0.44, 0.12, shape) * np.clip(window * dust, 0, 1)[:, :, None] * 0.18
    effect = np.clip(room + cyan + white + wood + violet + amber + wallpaper[:, :, None] * np.array([0.055, 0.070, 0.082], dtype=np.float32) + dust[:, :, None] * np.array([0.16, 0.17, 0.15], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.016).astype(np.float32))


def _ev67_wave4_eclipse_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 320)
        x, y = _xy(work_shape)
        cx = 0.50 + (_seed(seed, 19600) - 0.5) * 0.026
        cy = 0.47 + (_seed(seed, 19601) - 0.5) * 0.024
        dx = x - cx
        dy = y - cy
        d = np.sqrt(dx * dx + dy * dy)
        angle = np.arctan2(dy, dx)
        void = np.clip(1.0 - d / 0.235, 0, 1)
        limb = np.clip(1.0 - np.abs(d - 0.252) / 0.008, 0, 1)
        bead_gate = (np.sin(angle * 43.0 + seed * 0.017) > 0.42).astype(np.float32)
        beads = np.clip(1.0 - np.abs(d - (0.268 + np.sin(angle * 11.0) * 0.004)) / 0.0048, 0, 1) * bead_gate
        filament = np.clip(1.0 - np.abs(d - (0.292 + np.sin(angle * 17.0 + seed * 0.011) * 0.021)) / 0.0065, 0, 1)
        rays = np.clip(1.0 - np.abs(np.sin((angle * 23.0 + d * 18.0 + _field(work_shape, seed, 19602, 5.0)) * np.pi)) * 13.0, 0, 1)
        rays *= np.clip((d - 0.238) / 0.30, 0, 1) * np.clip((0.62 - d) / 0.22, 0, 1)
        tick = np.clip(1.0 - np.abs(d - 0.385) / 0.0038, 0, 1) * (np.sin(angle * 71.0) > 0.76).astype(np.float32)
        micro_noise = _hash_noise(shape, seed, 19603)
        dust = np.clip(
            (micro_noise > 0.946).astype(np.float32) * 0.30
            + (micro_noise > 0.986).astype(np.float32) * 0.42
            + ((micro_noise > 0.904) & (micro_noise < 0.927)).astype(np.float32) * 0.22,
            0,
            1,
        )
        grit = np.clip(
            _soften((micro_noise > 0.962).astype(np.float32), 1) * 0.30
            + ((micro_noise > 0.806) & (micro_noise < 0.836)).astype(np.float32) * 0.16
            + ((micro_noise > 0.682) & (micro_noise < 0.690)).astype(np.float32) * 0.12,
            0,
            1,
        )
        hot = np.clip(limb * 0.72 + beads * 0.80 + filament * 0.46 + rays * 0.34 + tick * 0.32, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(hot, shape), _fit2(void, shape), _fit2(limb, shape), _fit2(beads, shape), _fit2(rays, shape), _fit2(tick, shape), dust, grit
        return hot, void, limb, beads, rays, tick, dust, grit

    return _ev67_wave1_cached("eclipse_v4", shape, seed, build)


def spec_owner_eclipse_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    hot, void, limb, beads, rays, tick, dust, grit = _ev67_wave4_eclipse_v4(shape, seed)
    corona_flake = np.clip(dust * 0.62 + grit * 0.28 + rays * 0.22, 0, 1)
    return _spec_from_fields(shape, mask, 16 + hot * 184 + beads * 84 + corona_flake * 76, 146 - hot * 96 + void * 44 + grit * 34 - tick * 18, 22 + limb * 150 + beads * 102 + rays * 80 + tick * 66 + dust * 42, sm)


def paint_owner_eclipse_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    hot, void, limb, beads, rays, tick, dust, grit = _ev67_wave4_eclipse_v4(shape, seed)
    night = _stack_rgb(0.004 + grit * 0.014, 0.005 + grit * 0.016, 0.018 + grit * 0.050, shape)
    ember = _stack_rgb(1.00, 0.58 + beads * 0.20, 0.055, shape) * hot[:, :, None] * 0.62
    pearl = _stack_rgb(1.00, 0.88, 0.50, shape) * np.clip(beads + limb * 0.55, 0, 1)[:, :, None] * 0.35
    violet = _stack_rgb(0.18, 0.055, 0.34, shape) * np.clip(rays + tick, 0, 1)[:, :, None] * 0.26
    corona_dust = dust[:, :, None] * np.array([0.22, 0.19, 0.13], dtype=np.float32)
    bead_shadow = grit[:, :, None] * np.array([0.035, 0.030, 0.070], dtype=np.float32)
    micro_rays = np.clip(rays * 0.35 + tick * 0.45, 0, 1)[:, :, None] * np.array([0.13, 0.09, 0.18], dtype=np.float32)
    effect = np.clip(night * (1.0 - void[:, :, None] * 0.82) + ember + pearl + violet + corona_dust + bead_shadow + micro_rays, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.90), mask, bb, 0.014).astype(np.float32))


def _ev67_wave4_demon_forge_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 320)
        x, y = _xy(work_shape)
        warp = _field(work_shape, seed, 19700, 9.0)
        hammer = _field(work_shape, seed, 19701, 43.0)
        pit_hash = _hash_noise(work_shape, seed, 19704)
        anvil_cells = np.clip(1.0 - np.abs(np.sin((warp * 13.0 + hammer * 5.0) * np.pi)) * 10.0, 0, 1)
        dimple = _soften((pit_hash > 0.925).astype(np.float32), 1)
        hammered = np.clip(hammer * 0.46 + anvil_cells * 0.30 + dimple * 0.34, 0, 1)
        molten_a = np.clip(1.0 - np.abs(warp - 0.62) / 0.020, 0, 1)
        molten_b = np.clip(1.0 - np.abs(_field(work_shape, seed, 19705, 17.0) - 0.42) / 0.018, 0, 1)
        molten = np.clip(np.maximum(molten_a, molten_b * 0.72) * (0.40 + hammer * 0.82), 0, 1)
        ax = x - 0.50
        ay = y - 0.46
        d = np.sqrt(ax * ax + ay * ay)
        a = np.arctan2(ay, ax)
        horns = np.clip(1.0 - np.abs(d - (0.24 + np.sin(a * 2.0) * 0.055)) / 0.007, 0, 1) * (np.abs(a) > 1.05).astype(np.float32)
        runes = np.clip(1.0 - np.abs(d - 0.37) / 0.006, 0, 1) * (np.sin(a * 31.0 + seed * 0.013) > 0.68).astype(np.float32)
        filings = _ev67_speckle_field(shape, seed, 19702)
        soot = _ev67_grit_field(shape, seed, 19703)
        detail = np.clip(hammered * 0.35 + molten * 0.78 + horns * 0.44 + runes * 0.36, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(detail, shape), _fit2(hammered, shape), _fit2(molten, shape), _fit2(horns, shape), _fit2(runes, shape), filings, soot
        return detail, hammered, molten, horns, runes, filings, soot

    return _ev67_wave1_cached("demon_forge_v4", shape, seed, build)


def spec_owner_demon_forge_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, hammered, molten, horns, runes, filings, soot = _ev67_wave4_demon_forge_v4(shape, seed)
    return _spec_from_fields(shape, mask, 42 + hammered * 96 + molten * 156 + horns * 74 + filings * 50, 154 - molten * 112 + hammered * 46 + soot * 36, 18 + molten * 168 + runes * 86 + horns * 48, sm)


def paint_owner_demon_forge_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, hammered, molten, horns, runes, filings, soot = _ev67_wave4_demon_forge_v4(shape, seed)
    iron = _stack_rgb(0.036 + hammered * 0.14 + soot * 0.034, 0.028 + hammered * 0.075, 0.024 + hammered * 0.045, shape)
    heat = _stack_rgb(1.00, 0.24 + molten * 0.36, 0.015, shape) * molten[:, :, None] * 0.76
    occult = _stack_rgb(0.62, 0.035, 0.025, shape) * np.clip(horns + runes, 0, 1)[:, :, None] * 0.25
    forge_scale = np.clip(hammered * 0.45 + filings * 0.55, 0, 1)[:, :, None] * np.array([0.16, 0.13, 0.09], dtype=np.float32)
    effect = np.clip(iron + heat + occult + forge_scale, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_wave4_dark_ritual_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 416)
        x, y = _xy(work_shape)
        ax = x - 0.50
        ay = y - 0.52
        d = np.sqrt(ax * ax + ay * ay)
        a = np.arctan2(ay, ax)
        wax = _field(work_shape, seed, 19800, 13.0)
        circle = np.clip(1.0 - np.abs(d - 0.285) / 0.0055, 0, 1)
        triangle = np.maximum.reduce([
            np.clip(1.0 - np.abs(ax * 0.86 + ay * 0.50 - 0.120) / 0.006, 0, 1),
            np.clip(1.0 - np.abs(ax * -0.86 + ay * 0.50 - 0.120) / 0.006, 0, 1),
            np.clip(1.0 - np.abs(ay + 0.155) / 0.006, 0, 1) * (np.abs(ax) < 0.30),
        ])
        rune_band = np.clip(1.0 - np.abs(d - 0.365) / 0.006, 0, 1) * (np.sin(a * 37.0 + seed * 0.011) > 0.58).astype(np.float32)
        candle = np.zeros(work_shape, dtype=np.float32)
        for cx, cy in ((0.23, 0.24), (0.74, 0.27), (0.19, 0.78), (0.80, 0.76)):
            candle = np.maximum(candle, np.exp(-(((x - cx) / 0.020) ** 2 + ((y - cy) / 0.050) ** 2)))
        drips = np.clip(1.0 - np.abs(np.sin((y * 68.0 + wax * 2.0) * np.pi)) * 21.0, 0, 1) * candle
        ash = _ev67_grit_field(shape, seed, 19801)
        sparks = _ev67_speckle_field(shape, seed, 19802)
        sigil = np.clip(circle * 0.54 + triangle * 0.70 + rune_band * 0.78 + candle * 0.34 + drips * 0.32, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(sigil, shape), _fit2(circle, shape), _fit2(triangle, shape), _fit2(rune_band, shape), _fit2(candle, shape), _fit2(drips, shape), ash, sparks
        return sigil, circle, triangle, rune_band, candle, drips, ash, sparks

    return _ev67_wave1_cached("dark_ritual_v4", shape, seed, build)


def spec_owner_dark_ritual_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    sigil, circle, triangle, rune_band, candle, drips, ash, sparks = _ev67_wave4_dark_ritual_v4(shape, seed)
    return _spec_from_fields(shape, mask, 22 + sigil * 168 + rune_band * 70 + sparks * 54, 158 - sigil * 104 + ash * 42 + drips * 34, 18 + circle * 128 + triangle * 94 + candle * 88 + sparks * 44, sm)


def paint_owner_dark_ritual_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    sigil, circle, triangle, rune_band, candle, drips, ash, sparks = _ev67_wave4_dark_ritual_v4(shape, seed)
    stone = _stack_rgb(0.020 + ash * 0.040, 0.014 + ash * 0.024, 0.030 + ash * 0.050, shape)
    violet = _stack_rgb(0.44, 0.030, 0.82, shape) * np.clip(circle + rune_band, 0, 1)[:, :, None] * 0.46
    blood = _stack_rgb(0.82, 0.018, 0.030, shape) * triangle[:, :, None] * 0.34
    flame = _stack_rgb(1.00, 0.42, 0.06, shape) * np.clip(candle + drips * 0.5, 0, 1)[:, :, None] * 0.28
    micro_ash = ash[:, :, None] * np.array([0.060, 0.042, 0.076], dtype=np.float32)
    micro_sparks = sparks[:, :, None] * np.array([0.24, 0.10, 0.30], dtype=np.float32)
    etch_shadow = sigil[:, :, None] * np.array([0.040, 0.010, 0.060], dtype=np.float32)
    effect = np.clip(stone + violet + blood + flame + micro_ash + micro_sparks + etch_shadow, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.014).astype(np.float32))


def _ev67_wave4_banshee_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 416)
        x, y = _xy(work_shape)
        fog = _field(work_shape, seed, 19900, 18.0)
        face, face_edge = _ev67_disk_field(work_shape, [(0.50, 0.43, 0.115, 0.170, 0.70)])
        mouth = np.exp(-(((x - 0.50) / 0.030) ** 2 + ((y - 0.515) / 0.070) ** 2)).astype(np.float32)
        eye_l = np.exp(-(((x - 0.455) / 0.020) ** 2 + ((y - 0.405) / 0.016) ** 2)).astype(np.float32)
        eye_r = np.exp(-(((x - 0.545) / 0.020) ** 2 + ((y - 0.405) / 0.016) ** 2)).astype(np.float32)
        hair = _ev67_arc_bundle(work_shape, seed, 19901, 18, 0.40, 0.72, 0.0045, 0.20)
        scream = _ev67_arc_bundle(work_shape, seed, 19902, 15, 0.58, 0.30, 0.0040, 0.12)
        frost = _ev67_grit_field(shape, seed, 19903)
        glint = _ev67_speckle_field(shape, seed, 19904)
        detail = np.clip(face_edge * 0.52 + mouth * 0.86 + (eye_l + eye_r) * 0.62 + hair * 0.42 + scream * 0.50 + fog * face * 0.20, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(detail, shape), _fit2(face, shape), _fit2(face_edge, shape), _fit2(mouth, shape), _fit2(np.clip(eye_l + eye_r, 0, 1), shape), _fit2(hair, shape), _fit2(scream, shape), frost, glint
        return detail, face, face_edge, mouth, np.clip(eye_l + eye_r, 0, 1), hair, scream, frost, glint

    return _ev67_wave1_cached("banshee_v4", shape, seed, build)


def spec_owner_banshee_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, face, face_edge, mouth, eyes, hair, scream, frost, glint = _ev67_wave4_banshee_v4(shape, seed)
    return _spec_from_fields(shape, mask, 18 + face_edge * 96 + mouth * 112 + hair * 70 + glint * 66, 142 - scream * 72 + frost * 44 - face * 22, 28 + detail * 146 + eyes * 76 + scream * 62, sm)


def paint_owner_banshee_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, face, face_edge, mouth, eyes, hair, scream, frost, glint = _ev67_wave4_banshee_v4(shape, seed)
    veil = _stack_rgb(0.050 + frost * 0.050, 0.12 + frost * 0.080, 0.20 + frost * 0.120, shape)
    cyan = _stack_rgb(0.36, 0.84, 0.96, shape) * np.clip(face_edge + scream * 0.45, 0, 1)[:, :, None] * 0.38
    white = _stack_rgb(0.82, 0.98, 1.00, shape) * np.clip(mouth + eyes, 0, 1)[:, :, None] * 0.36
    violet = _stack_rgb(0.22, 0.12, 0.45, shape) * hair[:, :, None] * 0.28
    effect = np.clip(veil + cyan + white + violet + glint[:, :, None] * np.array([0.12, 0.20, 0.26], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.018).astype(np.float32))


def _ev67_wave4_hellhound_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 416)
        x, y = _xy(work_shape)
        pelt_hash = _hash_noise(work_shape, seed, 20004)
        pelt = np.clip(
            _soften((pelt_hash > 0.72).astype(np.float32), 1) * 0.12
            + (pelt_hash > 0.955).astype(np.float32) * 0.28,
            0,
            1,
        )
        claw = np.zeros(work_shape, dtype=np.float32)
        for cx, cy, tilt in ((0.18, 0.24, -0.18), (0.34, 0.58, 0.12), (0.72, 0.42, -0.10), (0.82, 0.78, 0.16)):
            local_y = y - cy
            for off in (-0.032, 0.0, 0.032):
                curve = cx + off + local_y * tilt + np.sin(local_y * 9.0 + seed * 0.009) * 0.012
                claw = np.maximum(claw, np.clip(1.0 - np.abs(x - curve) / 0.0055, 0, 1) * np.clip(1.0 - np.abs(local_y) / 0.18, 0, 1))
        paw = np.zeros(work_shape, dtype=np.float32)
        for cx, cy in ((0.28, 0.30), (0.70, 0.66), (0.46, 0.78)):
            pad = np.exp(-(((x - cx) / 0.050) ** 2 + ((y - cy) / 0.035) ** 2))
            toe = np.zeros(work_shape, dtype=np.float32)
            for ox in (-0.040, 0.0, 0.040):
                toe = np.maximum(toe, np.exp(-(((x - (cx + ox)) / 0.018) ** 2 + ((y - (cy - 0.052)) / 0.018) ** 2)))
            paw = np.maximum(paw, np.clip(pad * 0.62 + toe * 0.55, 0, 1))
        ember = np.clip(paw * 0.72 + claw * 0.54 + _soften((pelt_hash > 0.988).astype(np.float32), 1) * 0.34, 0, 1)
        teeth = np.clip(1.0 - np.abs(np.sin(((x - 0.5) * 18.0 + (y - 0.5) * 4.0 + pelt * 1.4) * np.pi)) * 28.0, 0, 1) * np.clip(ember + paw * 0.4, 0, 1)
        micro_hash = _hash_noise(shape, seed, 20005)
        ash = np.clip(
            (micro_hash > 0.520).astype(np.float32) * 0.055
            + (micro_hash > 0.790).astype(np.float32) * 0.130
            + (micro_hash > 0.925).astype(np.float32) * 0.245
            + (micro_hash > 0.982).astype(np.float32) * 0.360,
            0,
            1,
        )
        sparks = np.clip(
            _ev67_speckle_field(shape, seed, 20003) * 0.65
            + (micro_hash > 0.982).astype(np.float32) * 0.40,
            0,
            1,
        )
        detail = np.clip(pelt * 0.14 + claw * 0.72 + paw * 0.50 + ember * 0.44 + teeth * 0.42, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(detail, shape), _fit2(pelt, shape), _fit2(claw, shape), _fit2(paw, shape), _fit2(ember, shape), _fit2(teeth, shape), ash, sparks
        return detail, pelt, claw, paw, ember, teeth, ash, sparks

    return _ev67_wave1_cached("hellhound_v4", shape, seed, build)


def spec_owner_hellhound_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, pelt, claw, paw, ember, teeth, ash, sparks = _ev67_wave4_hellhound_v4(shape, seed)
    metallic = np.clip(20 + claw * 156 + paw * 92 + ember * 94 + teeth * 70 + sparks * 78 + ash * 36, 0, 255)
    roughness = np.clip(178 - claw * 86 - paw * 52 - ember * 72 + ash * 54 - sparks * 18, 12, 230)
    clearcoat = np.clip(24 + claw * 150 + paw * 96 + ember * 112 + teeth * 54 + sparks * 58 + ash * 28, 16, 255)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip(metallic * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(roughness * mask + 80 * (1.0 - mask), 12, 230).astype(np.uint8)
    spec[:, :, 2] = np.clip(clearcoat * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_hellhound_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, pelt, claw, paw, ember, teeth, ash, sparks = _ev67_wave4_hellhound_v4(shape, seed)
    hide = _stack_rgb(0.024 + ash * 0.160, 0.014 + ash * 0.050, 0.010 + ash * 0.020, shape)
    lava = _stack_rgb(1.00, 0.16 + ember * 0.42, 0.018, shape) * np.clip(ember * 0.38 + claw * 0.78 + paw * 0.38, 0, 1)[:, :, None] * 0.52
    bone = _stack_rgb(0.72, 0.52, 0.28, shape) * teeth[:, :, None] * 0.26
    print_glow = _stack_rgb(0.86, 0.10, 0.03, shape) * paw[:, :, None] * 0.34
    ember_pepper = np.clip(sparks * 0.90 + ash * 0.72, 0, 1)[:, :, None] * np.array([0.30, 0.090, 0.020], dtype=np.float32)
    effect = np.clip(hide + lava + bone + print_glow + ember_pepper, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.018).astype(np.float32))


def _ev67_wave4_lich_king_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 416)
        x, y = _xy(work_shape)
        frost = _field(work_shape, seed, 20100, 19.0)
        crown = np.zeros(work_shape, dtype=np.float32)
        for i, cx in enumerate(np.linspace(0.18, 0.82, 9)):
            height = 0.24 + (i % 3) * 0.045
            spike = np.clip(1.0 - np.abs(x - cx) / (0.022 + (i % 2) * 0.004) - np.clip((y - 0.16) / height, 0, 1), 0, 1)
            crown = np.maximum(crown, spike)
        skull, skull_edge = _ev67_disk_field(work_shape, [(0.50, 0.50, 0.105, 0.145, 0.52)])
        eye_l = np.exp(-(((x - 0.462) / 0.020) ** 2 + ((y - 0.480) / 0.015) ** 2)).astype(np.float32)
        eye_r = np.exp(-(((x - 0.538) / 0.020) ** 2 + ((y - 0.480) / 0.015) ** 2)).astype(np.float32)
        rune = np.clip(1.0 - np.abs(np.sin((x * 19.0 + y * 31.0 + frost * 1.8) * np.pi)) * 18.0, 0, 1) * np.clip(crown + skull_edge, 0, 1)
        cracks = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 73.0 + frost * 3.0) * np.pi)) * 30.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((y * 89.0 - frost * 2.5) * np.pi)) * 31.0, 0, 1),
        )
        ice_dust = _ev67_speckle_field(shape, seed, 20101)
        grit = _ev67_grit_field(shape, seed, 20102)
        detail = np.clip(crown * 0.70 + skull_edge * 0.48 + (eye_l + eye_r) * 0.58 + rune * 0.42 + cracks * 0.30 + frost * 0.18, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(detail, shape), _fit2(crown, shape), _fit2(skull, shape), _fit2(skull_edge, shape), _fit2(np.clip(eye_l + eye_r, 0, 1), shape), _fit2(rune, shape), _fit2(cracks, shape), _fit2(frost, shape), ice_dust, grit
        return detail, crown, skull, skull_edge, np.clip(eye_l + eye_r, 0, 1), rune, cracks, frost, ice_dust, grit

    return _ev67_wave1_cached("lich_king_v4", shape, seed, build)


def spec_owner_lich_king_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, crown, skull, skull_edge, eyes, rune, cracks, frost, ice_dust, grit = _ev67_wave4_lich_king_v4(shape, seed)
    return _spec_from_fields(shape, mask, 36 + crown * 126 + rune * 84 + ice_dust * 58, 64 + frost * 48 - eyes * 30 + grit * 38 - cracks * 20, 42 + detail * 150 + eyes * 88 + cracks * 62, sm)


def paint_owner_lich_king_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, crown, skull, skull_edge, eyes, rune, cracks, frost, ice_dust, grit = _ev67_wave4_lich_king_v4(shape, seed)
    metal = _stack_rgb(0.030 + frost * 0.050, 0.048 + frost * 0.090, 0.076 + frost * 0.150, shape)
    ice = _stack_rgb(0.38, 0.82, 1.00, shape) * np.clip(crown + cracks * 0.5, 0, 1)[:, :, None] * 0.36
    necro = _stack_rgb(0.12, 0.95, 0.72, shape) * np.clip(eyes + rune * 0.34, 0, 1)[:, :, None] * 0.30
    bone = _stack_rgb(0.50, 0.68, 0.74, shape) * skull_edge[:, :, None] * 0.22
    effect = np.clip(metal + ice + necro + bone + ice_dust[:, :, None] * np.array([0.14, 0.20, 0.24], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.87), mask, bb, 0.018).astype(np.float32))


def _ev67_wave4_spectral_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 416)
        x, y = _xy(work_shape)
        phase = _field(work_shape, seed, 20200, 23.0)
        ghost_a, edge_a = _ev67_disk_field(work_shape, [(0.25, 0.39, 0.105, 0.190, 0.56), (0.58, 0.55, 0.155, 0.245, 0.62), (0.82, 0.42, 0.095, 0.175, 0.48)])
        prism = np.clip(1.0 - np.abs(np.sin((phase * 20.0 + x * 6.0 - y * 4.0) * np.pi)) * 11.0, 0, 1) * np.clip(ghost_a + edge_a, 0, 1)
        refraction = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 57.0 + phase * 2.1) * np.pi)) * 25.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((y * 63.0 - phase * 1.7) * np.pi)) * 27.0, 0, 1),
        ) * edge_a
        glint = _ev67_speckle_field(shape, seed, 20201)
        mist = _ev67_grit_field(shape, seed, 20202)
        detail = np.clip(edge_a * 0.50 + prism * 0.52 + refraction * 0.36 + ghost_a * 0.28 + phase * ghost_a * 0.18, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(detail, shape), _fit2(ghost_a, shape), _fit2(edge_a, shape), _fit2(prism, shape), _fit2(refraction, shape), _fit2(phase, shape), glint, mist
        return detail, ghost_a, edge_a, prism, refraction, phase, glint, mist

    return _ev67_wave1_cached("spectral_v4", shape, seed, build)


def spec_owner_spectral_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, ghosts, edge, prism, refraction, phase, glint, mist = _ev67_wave4_spectral_v4(shape, seed)
    phase_glint = np.clip(glint * 0.72 + refraction * 0.34 + edge * 0.24, 0, 1)
    return _spec_from_fields(shape, mask, 22 + edge * 126 + prism * 116 + phase_glint * 86, 132 - prism * 72 + mist * 48 + phase * 24 - refraction * 16, 30 + detail * 176 + prism * 42 + refraction * 118 + ghosts * 82 + glint * 70, sm)


def paint_owner_spectral_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, ghosts, edge, prism, refraction, phase, glint, mist = _ev67_wave4_spectral_v4(shape, seed)
    deep = _stack_rgb(0.012 + mist * 0.038, 0.030 + mist * 0.060, 0.064 + mist * 0.110, shape)
    cyan = _stack_rgb(0.08, 0.80, 0.94, shape) * edge[:, :, None] * 0.38
    violet = _stack_rgb(0.48, 0.08, 0.86, shape) * prism[:, :, None] * 0.36
    pearl = _stack_rgb(0.72, 0.96, 1.00, shape) * ghosts[:, :, None] * 0.22
    green = _stack_rgb(0.05, 0.48, 0.30, shape) * refraction[:, :, None] * 0.22
    effect = np.clip(deep + cyan + violet + pearl + green + glint[:, :, None] * np.array([0.16, 0.24, 0.28], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.016).astype(np.float32))


def _ev67_wave4_haunted_v4(shape, seed):
    def build():
        work_shape = _bounded_shape(shape, 416)
        x, y = _xy(work_shape)
        window = np.zeros(work_shape, dtype=np.float32)
        frame = np.zeros(work_shape, dtype=np.float32)
        for i, cx in enumerate((0.22, 0.50, 0.78)):
            body = ((np.abs(x - cx) < 0.058) & (y > 0.30) & (y < 0.75)).astype(np.float32)
            arch = np.exp(-(((x - cx) / 0.055) ** 2 + ((y - 0.30) / 0.044) ** 2))
            pane = np.clip(body + arch, 0, 1) * (0.40 + i * 0.05)
            window = np.maximum(window, pane)
            frame = np.maximum(frame, np.clip(1.0 - np.abs(np.abs(x - cx) - 0.060) / 0.004, 0, 1) * (y > 0.30) * (y < 0.75))
            frame = np.maximum(frame, np.clip(1.0 - np.abs(y - 0.75) / 0.004, 0, 1) * (np.abs(x - cx) < 0.060))
        ghost, ghost_edge = _ev67_disk_field(work_shape, [(0.48, 0.58, 0.078, 0.145, 0.58), (0.62, 0.47, 0.050, 0.115, 0.38)])
        wallpaper = np.clip(1.0 - np.abs(np.sin((_field(work_shape, seed, 20300, 13.0) * 22.0 + window * 1.4) * np.pi)) * 12.0, 0, 1)
        cracks = np.maximum(
            np.clip(1.0 - np.abs(np.sin((x * 51.0 + y * 9.0) * np.pi)) * 26.0, 0, 1),
            np.clip(1.0 - np.abs(np.sin((y * 67.0 - x * 8.0) * np.pi)) * 28.0, 0, 1),
        ) * np.clip(frame + wallpaper, 0, 1)
        dust = _ev67_speckle_field(shape, seed, 20301)
        plaster = _ev67_grit_field(shape, seed, 20302)
        detail = np.clip(window * 0.36 + frame * 0.60 + ghost * 0.34 + ghost_edge * 0.56 + wallpaper * 0.28 + cracks * 0.30, 0, 1)
        if work_shape != tuple(shape):
            return _fit2(detail, shape), _fit2(window, shape), _fit2(frame, shape), _fit2(ghost, shape), _fit2(ghost_edge, shape), _fit2(wallpaper, shape), _fit2(cracks, shape), dust, plaster
        return detail, window, frame, ghost, ghost_edge, wallpaper, cracks, dust, plaster

    return _ev67_wave1_cached("haunted_v4", shape, seed, build)


def spec_owner_haunted_v4(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    detail, window, frame, ghost, ghost_edge, wallpaper, cracks, dust, plaster = _ev67_wave4_haunted_v4(shape, seed)
    return _spec_from_fields(shape, mask, 18 + frame * 108 + ghost_edge * 90 + cracks * 62 + dust * 58, 152 - ghost * 72 - window * 42 + plaster * 42, 22 + detail * 138 + wallpaper * 56 + dust * 44, sm)


def paint_owner_haunted_v4(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    detail, window, frame, ghost, ghost_edge, wallpaper, cracks, dust, plaster = _ev67_wave4_haunted_v4(shape, seed)
    room = _stack_rgb(0.022 + plaster * 0.042, 0.038 + plaster * 0.062, 0.058 + plaster * 0.084, shape)
    cyan = _stack_rgb(0.18, 0.78, 0.88, shape) * np.clip(window + ghost * 0.34, 0, 1)[:, :, None] * 0.42
    white = _stack_rgb(0.68, 0.96, 0.98, shape) * ghost_edge[:, :, None] * 0.30
    wood = _stack_rgb(0.22, 0.120, 0.065, shape) * frame[:, :, None] * 0.32
    violet = _stack_rgb(0.24, 0.060, 0.34, shape) * np.clip(wallpaper + ghost * 0.20, 0, 1)[:, :, None] * 0.26
    scratch = _stack_rgb(0.42, 0.52, 0.54, shape) * cracks[:, :, None] * 0.14
    plaster_noise = plaster[:, :, None] * np.array([0.070, 0.086, 0.095], dtype=np.float32)
    dust_glints = dust[:, :, None] * np.array([0.22, 0.24, 0.21], dtype=np.float32)
    relief = detail[:, :, None] * np.array([0.028, 0.044, 0.058], dtype=np.float32)
    effect = np.clip(room + cyan + white + wood + violet + scratch + plaster_noise + dust_glints + relief, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.88), mask, bb, 0.016).astype(np.float32))


def _ev67_wave5_spec(shape, mask, metallic, roughness, clearcoat, sm, seed=0, salt=0):
    mask = _mask(mask, shape)
    metallic = np.asarray(metallic, dtype=np.float32)
    roughness = np.asarray(roughness, dtype=np.float32)
    clearcoat = np.asarray(clearcoat, dtype=np.float32)
    edge = (
        np.abs(metallic - np.roll(metallic, 1, 0))
        + np.abs(metallic - np.roll(metallic, -1, 1))
        + np.abs(clearcoat - np.roll(clearcoat, 1, 1))
    ) / 255.0
    edge = np.clip(edge, 0, 1)
    dust = (_hash_noise(shape, seed, salt + 9100) > 0.984).astype(np.float32)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((metallic + edge * 46.0 + dust * 34.0) * float(sm) * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((roughness - edge * 34.0 + dust * 18.0) * mask + 80 * (1.0 - mask), 12, 220).astype(np.uint8)
    spec[:, :, 2] = np.clip((clearcoat + edge * 62.0 + dust * 36.0) * mask, 16, 255).astype(np.uint8)
    return spec


def _ev67_wave5_kaleidoscope(shape, seed):
    work_shape = _bounded_shape(shape, 1280)
    if work_shape != tuple(shape):
        facets, bevel, grout, chip, rosette, tint = _ev67_wave5_kaleidoscope(work_shape, seed)
        chip2 = (_hash_noise(shape, seed, 11117) > 0.978).astype(np.float32)
        return _fit2(facets, shape), _fit2(bevel, shape), _fit2(grout, shape), np.clip(_fit2(chip, shape) + chip2 * 0.35, 0, 1), _fit2(rosette, shape), _fit2(tint, shape)
    x, y = _xy(shape)
    dx = x - 0.50
    dy = y - 0.50
    angle = np.arctan2(dy, dx)
    radius = np.sqrt(dx * dx + dy * dy)
    mirror = np.abs(np.mod(angle / (np.pi / 7.0) + 0.5, 2.0) - 1.0)
    phase = np.mod(mirror * 6.0 + radius * 19.0 + _field(shape, seed, 11100, 2.4) * 0.72, 1.0)
    bevel = np.maximum(np.clip(1.0 - np.abs(phase - 0.035) / 0.016, 0, 1), np.clip(1.0 - np.abs(phase - 0.965) / 0.018, 0, 1))
    grout = np.clip(1.0 - np.abs(np.sin((mirror * 10.0 + radius * 8.0) * np.pi)) * 18.0, 0, 1)
    chip = (_hash_noise(shape, seed, 11101) > 0.982).astype(np.float32)
    rosette = np.clip(1.0 - np.abs(radius - (0.18 + 0.022 * np.sin(angle * 14.0))) / 0.0045, 0, 1)
    facets = np.clip(bevel * 0.58 + grout * 0.42 + rosette * 0.54 + _soften(chip, 1) * 0.38, 0, 1)
    tint = np.mod(angle / (np.pi * 2.0) + radius * 1.8 + phase * 0.32, 1.0)
    return facets, bevel, grout, chip, rosette, tint


def spec_owner_kaleidoscope_v5(shape, mask, seed, sm):
    facets, bevel, grout, chip, rosette, tint = _ev67_wave5_kaleidoscope(shape, seed)
    return _ev67_wave5_spec(shape, mask, 24 + bevel * 130 + chip * 80 + rosette * 42 + tint * 34, 142 - bevel * 88 + grout * 42 + (1.0 - facets) * 18, 42 + facets * 142 + bevel * 48 + rosette * 34, sm, seed, 11150)


def paint_owner_kaleidoscope_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    facets, bevel, grout, chip, rosette, tint = _ev67_wave5_kaleidoscope(shape, seed)
    glass = _rgb_cycle(tint + bevel * 0.06, 0.78, 0.92)
    ink = _stack_rgb(0.018, 0.020, 0.028, shape) * (1.0 + grout[:, :, None] * 3.0)
    hot = np.stack([bevel * 0.24 + chip * 0.14, rosette * 0.16 + chip * 0.10, bevel * 0.22 + chip * 0.16], axis=2)
    effect = np.clip(ink + glass * np.clip(0.26 + facets[:, :, None] * 0.82, 0, 1) + hot, 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.86), mask, bb, 0.016).astype(np.float32))


def _ev67_wave5_aurora(shape, seed):
    work_shape = _bounded_shape(shape, 1280)
    if work_shape != tuple(shape):
        curtain, pearl, particle, altitude, arc = _ev67_wave5_aurora(work_shape, seed)
        frost = (_hash_noise(shape, seed, 11217) > 0.986).astype(np.float32)
        return np.clip(_fit2(curtain, shape) + frost * 0.16, 0, 1), _fit2(pearl, shape), np.clip(_fit2(particle, shape) + frost * 0.36, 0, 1), _fit2(altitude, shape), _fit2(arc, shape)
    x, y = _xy(shape)
    wind = _field(shape, seed, 11200, 2.6)
    curtain = np.zeros(shape, dtype=np.float32)
    for idx, freq in enumerate((2.4, 3.8, 5.7, 8.6, 13.0)):
        phase = _seed(seed, 11210 + idx) * 6.283
        path = x * freq + np.sin(y * np.pi * (1.1 + idx * 0.24) + phase) * (0.20 + idx * 0.035) + wind * 0.44
        curtain = np.maximum(curtain, np.clip(1.0 - np.abs(np.sin(path * np.pi)) * (4.8 + idx * 0.9), 0, 1) * (0.74 - idx * 0.07))
    altitude = np.clip(y + wind * 0.16, 0, 1)
    pearl = np.clip(1.0 - np.abs(np.sin((curtain * 11.0 + altitude * 2.0) * np.pi)) * 11.0, 0, 1)
    arc = np.clip(1.0 - np.abs(np.sin((y * 26.0 + wind * 2.2) * np.pi)) * 20.0, 0, 1) * np.clip(curtain + 0.15, 0, 1)
    particle = (_hash_noise(shape, seed, 11201) > 0.986).astype(np.float32)
    return np.clip(curtain, 0, 1), pearl, particle, altitude, arc


def spec_owner_aurora_v5(shape, mask, seed, sm):
    curtain, pearl, particle, altitude, arc = _ev67_wave5_aurora(shape, seed)
    return _ev67_wave5_spec(shape, mask, 18 + particle * 105 + arc * 72 + pearl * 46, 156 - curtain * 62 - pearl * 38 + altitude * 24, 38 + curtain * 132 + pearl * 72 + arc * 44, sm, seed, 11250)


def paint_owner_aurora_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    curtain, pearl, particle, altitude, arc = _ev67_wave5_aurora(shape, seed)
    sky = _stack_rgb(0.010 + altitude * 0.030, 0.024 + altitude * 0.035, 0.060 + altitude * 0.090, shape)
    green = _stack_rgb(0.020, 0.58, 0.34, shape) * curtain[:, :, None] * 0.74
    violet = _stack_rgb(0.34, 0.08, 0.68, shape) * np.clip(pearl + altitude * curtain, 0, 1)[:, :, None] * 0.36
    ice = _stack_rgb(0.25, 0.82, 0.98, shape) * np.clip(arc + particle * 0.7, 0, 1)[:, :, None] * 0.20
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(sky + green + violet + ice, 0, 1), pm, 0.86), mask, bb, 0.014).astype(np.float32))


def _ev67_wave5_holographic_wrap(shape, seed):
    work_shape = _bounded_shape(shape, 1280)
    if work_shape != tuple(shape):
        phase, groove, facet, dust, polish = _ev67_wave5_holographic_wrap(work_shape, seed)
        nano = (_hash_noise(shape, seed, 11319) > 0.984).astype(np.float32)
        return _fit2(phase, shape), np.clip(_fit2(groove, shape) + nano * 0.22, 0, 1), _fit2(facet, shape), np.clip(_fit2(dust, shape) + nano * 0.35, 0, 1), _fit2(polish, shape)
    x, y = _xy(shape)
    flow = _field(shape, seed, 11300, 2.8)
    groove_a = np.clip(1.0 - np.abs(np.sin((x * 240.0 + flow * 1.4) * np.pi)) * 5.8, 0, 1)
    groove_b = np.clip(1.0 - np.abs(np.sin((y * 190.0 + x * 7.0 + flow * 1.2) * np.pi)) * 7.5, 0, 1)
    tile = np.mod(np.floor(x * 18.0 + flow * 2.0) + np.floor(y * 13.0), 5.0) / 4.0
    facet = np.clip(1.0 - np.abs(np.sin((tile + x * 3.0 - y * 2.0) * np.pi)) * 9.5, 0, 1)
    polish = np.clip(np.sin((x * 2.2 + y * 1.4 + flow * 0.5) * np.pi) * 0.5 + 0.5, 0, 1)
    dust = (_hash_noise(shape, seed, 11301) > 0.989).astype(np.float32)
    phase = np.mod(flow * 0.44 + x * 0.38 + y * 0.24 + groove_a * 0.12 + tile * 0.18, 1.0)
    return phase, np.clip(groove_a * 0.62 + groove_b * 0.32, 0, 1), facet, dust, polish


def spec_owner_holographic_wrap_v5(shape, mask, seed, sm):
    phase, groove, facet, dust, polish = _ev67_wave5_holographic_wrap(shape, seed)
    return _ev67_wave5_spec(shape, mask, 42 + groove * 112 + facet * 58 + dust * 80 + polish * 28, 94 - groove * 44 - facet * 18 + (1.0 - polish) * 36, 64 + groove * 116 + facet * 72 + phase * 38, sm, seed, 11350)


def paint_owner_holographic_wrap_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    phase, groove, facet, dust, polish = _ev67_wave5_holographic_wrap(shape, seed)
    foil = _rgb_cycle(phase, 0.68, 0.90)
    pearl = _rgb_cycle(phase + 0.18 + polish * 0.12, 0.38, 0.82)
    base = _stack_rgb(0.045 + polish * 0.035, 0.050 + polish * 0.045, 0.060 + polish * 0.055, shape)
    effect = np.clip(base + foil * groove[:, :, None] * 0.42 + pearl * facet[:, :, None] * 0.36 + dust[:, :, None] * np.array([0.18, 0.20, 0.22], dtype=np.float32), 0, 1)
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, effect, pm, 0.84), mask, bb, 0.012).astype(np.float32))


def _ev67_wave5_uv_blacklight(shape, seed):
    work_shape = _bounded_shape(shape, 1280)
    if work_shape != tuple(shape):
        glow, glyph, splatter, ink, dust = _ev67_wave5_uv_blacklight(work_shape, seed)
        nano = (_hash_noise(shape, seed, 11419) > 0.978).astype(np.float32)
        return np.clip(_fit2(glow, shape) + nano * 0.18, 0, 1), _fit2(glyph, shape), np.clip(_fit2(splatter, shape) + nano * 0.28, 0, 1), _fit2(ink, shape), _fit2(dust, shape)
    x, y = _xy(shape)
    flow = _field(shape, seed, 11400, 4.2)
    glyph = np.zeros(shape, dtype=np.float32)
    for idx, (cx, cy, rad) in enumerate(((0.28, 0.28, 0.16), (0.68, 0.38, 0.20), (0.46, 0.72, 0.18))):
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        ring = np.clip(1.0 - np.abs(d - rad) / 0.0045, 0, 1)
        ticks = np.clip(1.0 - np.abs(np.sin((np.arctan2(y - cy, x - cx) * (9 + idx * 3) + flow) * np.pi)) * 18.0, 0, 1)
        glyph = np.maximum(glyph, np.clip(ring + ticks * (d < rad) * 0.38, 0, 1))
    splatter = (_hash_noise(shape, seed, 11401) > 0.965).astype(np.float32)
    ink = np.clip(_field(shape, seed, 11402, 18.0) * 0.42 + _soften(splatter, 1) * 0.36, 0, 1)
    dust = (_hash_noise(shape, seed, 11403) > 0.988).astype(np.float32)
    glow = np.clip(glyph * 0.74 + _soften(splatter, 2) * 0.48 + dust * 0.45, 0, 1)
    return glow, glyph, splatter, ink, dust


def spec_owner_uv_blacklight_v5(shape, mask, seed, sm):
    glow, glyph, splatter, ink, dust = _ev67_wave5_uv_blacklight(shape, seed)
    return _ev67_wave5_spec(shape, mask, 16 + glyph * 92 + dust * 120 + splatter * 42, 178 - glow * 76 + ink * 34, 36 + glow * 166 + glyph * 42 + dust * 44, sm, seed, 11450)


def paint_owner_uv_blacklight_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    glow, glyph, splatter, ink, dust = _ev67_wave5_uv_blacklight(shape, seed)
    black = _stack_rgb(0.010 + ink * 0.035, 0.004 + ink * 0.012, 0.026 + ink * 0.060, shape)
    violet = _stack_rgb(0.34, 0.045, 0.86, shape) * glow[:, :, None] * 0.76
    acid = _stack_rgb(0.10, 0.86, 0.24, shape) * np.clip(glyph + dust, 0, 1)[:, :, None] * 0.34
    pink = _stack_rgb(0.86, 0.06, 0.48, shape) * splatter[:, :, None] * 0.26
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(black + violet + acid + pink, 0, 1), pm, 0.88), mask, bb, 0.010).astype(np.float32))


def _ev67_wave5_wraith(shape, seed):
    work_shape = _bounded_shape(shape, 1280)
    if work_shape != tuple(shape):
        veil, edge, torn, eye, dust, cold = _ev67_wave5_wraith(work_shape, seed)
        frost = (_hash_noise(shape, seed, 11519) > 0.982).astype(np.float32)
        return np.clip(_fit2(veil, shape) + frost * 0.14, 0, 1), _fit2(edge, shape), _fit2(torn, shape), _fit2(eye, shape), np.clip(_fit2(dust, shape) + frost * 0.36, 0, 1), _fit2(cold, shape)
    x, y = _xy(shape)
    smoke = _field(shape, seed, 11500, 8.0)
    veil = np.clip(smoke * 0.36 + _field(shape, seed, 11501, 18.0) * 0.18, 0, 1)
    torn = np.maximum(np.clip(1.0 - np.abs(np.sin((y * 34.0 + smoke * 4.6) * np.pi)) * 22.0, 0, 1), np.clip(1.0 - np.abs(np.sin((x * 18.0 + smoke * 5.1) * np.pi)) * 26.0, 0, 1) * 0.55)
    cx = 0.42 + _seed(seed, 11502) * 0.18
    cy = 0.38 + _seed(seed, 11503) * 0.18
    eye = np.exp(-(((x - cx) / 0.045) ** 2 + ((y - cy) / 0.018) ** 2)).astype(np.float32)
    edge = np.clip(torn * 0.54 + np.abs(veil - _soften(veil, 3)) * 5.0, 0, 1)
    dust = (_hash_noise(shape, seed, 11504) > 0.987).astype(np.float32)
    cold = np.clip(veil + edge * 0.42 + eye * 0.70, 0, 1)
    return veil, edge, torn, eye, dust, cold


def spec_owner_wraith_v5(shape, mask, seed, sm):
    veil, edge, torn, eye, dust, cold = _ev67_wave5_wraith(shape, seed)
    return _ev67_wave5_spec(shape, mask, 14 + dust * 92 + edge * 56 + eye * 42, 190 - edge * 82 - eye * 54 + veil * 24, 24 + cold * 128 + edge * 58 + dust * 36, sm, seed, 11550)


def paint_owner_wraith_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    veil, edge, torn, eye, dust, cold = _ev67_wave5_wraith(shape, seed)
    abyss = _stack_rgb(0.006, 0.010 + veil * 0.026, 0.026 + veil * 0.060, shape)
    ecto = _stack_rgb(0.18, 0.42, 0.54, shape) * np.clip(edge + cold * 0.35, 0, 1)[:, :, None] * 0.44
    white = _stack_rgb(0.68, 0.88, 0.92, shape) * np.clip(torn + eye, 0, 1)[:, :, None] * 0.18
    dust_rgb = _stack_rgb(0.22, 0.30, 0.34, shape) * dust[:, :, None] * 0.34
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(abyss + ecto + white + dust_rgb, 0, 1), pm, 0.88), mask, bb, 0.010).astype(np.float32))


def _ev67_wave5_possessed(shape, seed):
    work_shape = _bounded_shape(shape, 1280)
    if work_shape != tuple(shape):
        pulse, crack, eye, sigil, pore, heat = _ev67_wave5_possessed(work_shape, seed)
        ember = (_hash_noise(shape, seed, 11619) > 0.972).astype(np.float32)
        return np.clip(_fit2(pulse, shape) + ember * 0.22, 0, 1), _fit2(crack, shape), _fit2(eye, shape), _fit2(sigil, shape), np.clip(_fit2(pore, shape) + ember * 0.46, 0, 1), _fit2(heat, shape)
    x, y = _xy(shape)
    heat = _field(shape, seed, 11600, 5.2)
    pulse = np.clip((np.sin((heat * 5.0 + x * 1.7 - y * 1.2) * np.pi) * 0.5 + 0.5) * 0.60 + heat * 0.30, 0, 1)
    crack = np.clip(1.0 - np.abs(np.sin((pulse * 14.0 + _field(shape, seed, 11601, 11.0)) * np.pi)) * 18.0, 0, 1)
    scar = np.clip(1.0 - np.abs(np.sin((heat * 31.0 + x * 5.0 + y * 2.5) * np.pi)) * 24.0, 0, 1)
    eye = np.zeros(shape, dtype=np.float32)
    for cx, cy in ((0.31, 0.36), (0.67, 0.55), (0.48, 0.74)):
        eye = np.maximum(eye, np.exp(-(((x - cx) / 0.038) ** 2 + ((y - cy) / 0.018) ** 2)))
    dx = x - 0.50
    dy = y - 0.50
    r = np.sqrt(dx * dx + dy * dy)
    sigil = np.clip(1.0 - np.abs(r - (0.22 + np.sin(np.arctan2(dy, dx) * 6.0) * 0.012)) / 0.004, 0, 1)
    pore = (_hash_noise(shape, seed, 11602) > 0.958).astype(np.float32)
    ember = (_hash_noise(shape, seed, 11603) > 0.982).astype(np.float32)
    return np.clip(pulse + ember * 0.20, 0, 1), np.clip(crack + scar * 0.36, 0, 1), eye.astype(np.float32), sigil, np.clip(pore + ember * 0.42, 0, 1), heat


def spec_owner_possessed_v5(shape, mask, seed, sm):
    pulse, crack, eye, sigil, pore, heat = _ev67_wave5_possessed(shape, seed)
    return _ev67_wave5_spec(shape, mask, 18 + eye * 135 + sigil * 82 + pore * 58 + crack * 36, 172 - eye * 86 - sigil * 62 + heat * 24 + pore * 26, 28 + pulse * 74 + crack * 86 + eye * 98 + sigil * 60, sm, seed, 11650)


def paint_owner_possessed_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    pulse, crack, eye, sigil, pore, heat = _ev67_wave5_possessed(shape, seed)
    skin = _stack_rgb(0.030 + heat * 0.060, 0.010 + heat * 0.014, 0.014 + heat * 0.025, shape)
    lava = _stack_rgb(0.86, 0.050, 0.030, shape) * np.clip(crack + sigil * 0.7, 0, 1)[:, :, None] * 0.62
    eye_rgb = _stack_rgb(1.00, 0.52, 0.10, shape) * eye[:, :, None] * 0.68
    bruise = _stack_rgb(0.22, 0.020, 0.28, shape) * (1.0 - pulse)[:, :, None] * 0.26
    pores = _stack_rgb(0.72, 0.055, 0.035, shape) * pore[:, :, None] * 0.32
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(skin + lava + eye_rgb + bruise + pores, 0, 1), pm, 0.88), mask, bb, 0.010).astype(np.float32))


def _ev67_wave5_crt_scanline(shape, seed):
    x, y = _xy(shape)
    row = np.floor(y * shape[0]).astype(np.int32)
    col = np.floor(x * shape[1]).astype(np.int32)
    scan = ((row % 3) == 0).astype(np.float32)
    triad = (col % 3).astype(np.float32)
    roll = np.clip(1.0 - np.abs(np.sin((y * 9.0 + _field(shape, seed, 11700, 1.6) * 0.7) * np.pi)) * 8.0, 0, 1)
    burn = np.clip(_field(shape, seed, 11701, 3.4) * 0.36 + roll * 0.42, 0, 1)
    phosphor = (_hash_noise(shape, seed, 11702) > 0.969).astype(np.float32)
    ghost = np.clip(1.0 - np.abs(np.sin((x * 5.0 + y * 2.0 + burn * 2.0) * np.pi)) * 12.0, 0, 1) * 0.45
    return scan, triad, roll, burn, phosphor, ghost


def spec_owner_crt_scanline_v5(shape, mask, seed, sm):
    scan, triad, roll, burn, phosphor, ghost = _ev67_wave5_crt_scanline(shape, seed)
    triad_energy = np.where(triad < 1, 0.72, np.where(triad < 2, 0.92, 0.82)).astype(np.float32)
    energy = np.clip(scan * 0.34 + roll * 0.42 + phosphor * 0.70 + ghost * 0.62, 0, 1)
    return _ev67_wave5_spec(shape, mask, 18 + energy * 122 + triad_energy * 22, 154 - scan * 32 - phosphor * 48 + burn * 30, 30 + energy * 142 + roll * 34, sm, seed, 11750)


def paint_owner_crt_scanline_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    scan, triad, roll, burn, phosphor, ghost = _ev67_wave5_crt_scanline(shape, seed)
    rgb = np.stack([(triad < 1.0).astype(np.float32), ((triad >= 1.0) & (triad < 2.0)).astype(np.float32), (triad >= 2.0).astype(np.float32)], axis=2)
    base = _stack_rgb(0.012 + burn * 0.028, 0.026 + burn * 0.055, 0.034 + burn * 0.065, shape)
    phosphor_rgb = rgb * np.clip(0.10 + scan[:, :, None] * 0.48 + phosphor[:, :, None] * 0.32, 0, 1)
    roll_rgb = _stack_rgb(0.02, 0.34, 0.22, shape) * np.clip(roll + ghost, 0, 1)[:, :, None] * 0.30
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(base + phosphor_rgb + roll_rgb, 0, 1), pm, 0.82), mask, bb, 0.010).astype(np.float32))


def _ev67_wave5_thermochromic(shape, seed):
    work_shape = _bounded_shape(shape, 768)
    if work_shape != tuple(shape):
        heat, cell, edge, freckle, cool = _ev67_wave5_thermochromic(work_shape, seed)
        grain = (_hash_noise(shape, seed, 11819) > 0.955).astype(np.float32)
        pin = np.clip(1.0 - np.abs(np.sin((_xy(shape)[0] * 330.0 + _xy(shape)[1] * 217.0) * np.pi)) * 8.0, 0, 1)
        return (
            _fit2(heat, shape),
            np.clip(_fit2(cell, shape) + grain * 0.32 + pin * 0.16, 0, 1),
            np.clip(_fit2(edge, shape) + grain * 0.26 + pin * 0.20, 0, 1),
            np.clip(_fit2(freckle, shape) + grain * 0.48, 0, 1),
            _fit2(cool, shape),
        )
    x, y = _xy(shape)
    heat = np.clip(_field(shape, seed, 11800, 3.2) * 0.42 + (np.sin((x * 2.0 - y * 1.5) * np.pi) * 0.5 + 0.5) * 0.34 + _field(shape, seed, 11801, 12.0) * 0.18, 0, 1)
    cell = np.clip(1.0 - np.abs(np.sin((heat * 18.0 + _field(shape, seed, 11802, 4.0) * 1.1) * np.pi)) * 13.0, 0, 1)
    edge = np.clip(np.abs(heat - _soften(heat, 4)) * 9.0 + cell * 0.38, 0, 1)
    freckle = (_hash_noise(shape, seed, 11803) > 0.955).astype(np.float32)
    cool = np.clip(1.0 - heat + _field(shape, seed, 11804, 6.0) * 0.14, 0, 1)
    return heat, cell, edge, freckle, cool


def spec_owner_thermochromic_v5(shape, mask, seed, sm):
    heat, cell, edge, freckle, cool = _ev67_wave5_thermochromic(shape, seed)
    return _ev67_wave5_spec(shape, mask, 20 + edge * 82 + freckle * 76 + heat * 36, 170 - cell * 66 - edge * 42 + cool * 34, 42 + cell * 128 + edge * 72 + heat * 36, sm, seed, 11850)


def paint_owner_thermochromic_v5(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    heat, cell, edge, freckle, cool = _ev67_wave5_thermochromic(shape, seed)
    thermal = _thermal_palette(np.clip(heat + cell * 0.045 - cool * 0.025, 0, 1))
    cold = _stack_rgb(0.012, 0.12, 0.34, shape) * cool[:, :, None] * 0.32
    hot_edge = _stack_rgb(1.00, 0.58, 0.06, shape) * edge[:, :, None] * 0.34
    cell_flash = _stack_rgb(0.04, 0.72, 0.86, shape) * cell[:, :, None] * 0.18
    freckles = _stack_rgb(0.90, 0.24, 0.08, shape) * freckle[:, :, None] * 0.34
    return np.ascontiguousarray(_apply_bb(_mix_base(paint, mask, np.clip(thermal * 0.66 + cold + hot_edge + cell_flash + freckles, 0, 1), pm, 0.84), mask, bb, 0.012).astype(np.float32))


OWNER_REVIEW_EFFECTS_MONOLITHICS = {
    "aurora": (spec_owner_aurora_v5, paint_owner_aurora_v5),
    "banshee": (spec_owner_banshee_v4, paint_owner_banshee_v4),
    "blood_oath": (spec_owner_blood_oath_v4, paint_owner_blood_oath_v4),
    "crt_scanline": (spec_owner_crt_scanline_v5, paint_owner_crt_scanline_v5),
    "catacombs": (spec_owner_catacombs_v5, paint_owner_catacombs_v5),
    "cel_shade": (spec_owner_cel_shade, paint_owner_cel_shade),
    "chromatic_aberration": (spec_owner_chromatic_aberration_v4, paint_owner_chromatic_aberration_v4),
    "cursed": (spec_owner_cursed, paint_owner_cursed),
    "dark_ritual": (spec_owner_dark_ritual_v4, paint_owner_dark_ritual_v4),
    "datamosh": (spec_owner_datamosh, paint_owner_datamosh),
    "death_metal": (spec_owner_death_metal_v4, paint_owner_death_metal_v4),
    "demon_forge": (spec_owner_demon_forge_v4, paint_owner_demon_forge_v4),
    "double_exposure": (spec_owner_double_exposure_v4, paint_owner_double_exposure_v4),
    "embossed": (spec_owner_embossed_v4, paint_owner_embossed_v4),
    "eclipse": (spec_owner_eclipse_v4, paint_owner_eclipse_v4),
    "film_burn": (spec_owner_film_burn_v6, paint_owner_film_burn_v6),
    "fish_eye": (spec_owner_fish_eye_v4, paint_owner_fish_eye_v4),
    "gargoyle": (spec_owner_gargoyle_v4, paint_owner_gargoyle_v4),
    "glitch": (spec_owner_glitch, paint_owner_glitch),
    "graveyard": (spec_owner_graveyard_v4, paint_owner_graveyard_v4),
    "halftone": (spec_owner_halftone_v4, paint_owner_halftone_v4),
    "haunted": (spec_owner_haunted_v4, paint_owner_haunted_v4),
    "hellhound": (spec_owner_hellhound_v4, paint_owner_hellhound_v4),
    "holographic_wrap": (spec_owner_holographic_wrap_v5, paint_owner_holographic_wrap_v5),
    "infrared": (spec_owner_infrared, paint_owner_infrared),
    "iron_maiden": (spec_owner_iron_maiden_v5, paint_owner_iron_maiden_v5),
    "kaleidoscope": (spec_owner_kaleidoscope_v5, paint_owner_kaleidoscope_v5),
    "lich_king": (spec_owner_lich_king_v4, paint_owner_lich_king_v4),
    "long_exposure": (spec_owner_long_exposure_v5, paint_owner_long_exposure_v5),
    "necrotic": (spec_owner_necrotic_v4, paint_owner_necrotic_v4),
    "nightmare": (spec_owner_nightmare_v4, paint_owner_nightmare_v4),
    "negative": (spec_owner_negative_v4, paint_owner_negative_v4),
    "parallax": (spec_owner_parallax_v5, paint_owner_parallax_v5),
    "phantom": (spec_owner_phantom_v4, paint_owner_phantom_v4),
    "polarized": (spec_owner_polarized_v4, paint_owner_polarized_v4),
    "possessed": (spec_owner_possessed_v5, paint_owner_possessed_v5),
    "reaper": (spec_owner_reaper_v5, paint_owner_reaper_v5),
    "refraction": (spec_owner_refraction_v4, paint_owner_refraction_v4),
    "rust": (spec_owner_rust_v4, paint_owner_rust_v4),
    "shadow_realm": (spec_owner_shadow_realm_v4, paint_owner_shadow_realm_v4),
    "solarization": (spec_owner_solarization_v5, paint_owner_solarization_v5),
    "spectral": (spec_owner_spectral_v4, paint_owner_spectral_v4),
    "thermochromic": (spec_owner_thermochromic_v5, paint_owner_thermochromic_v5),
    "uv_blacklight": (spec_owner_uv_blacklight_v5, paint_owner_uv_blacklight_v5),
    "voodoo": (spec_owner_voodoo_v5, paint_owner_voodoo_v5),
    "wraith": (spec_owner_wraith_v5, paint_owner_wraith_v5),
    "x_ray": (spec_owner_x_ray_v5, paint_owner_x_ray_v5),
}
