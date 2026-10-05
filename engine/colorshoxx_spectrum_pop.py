"""COLORSHOXX Spectrum Pop — paint-traced spec with full M/R/CC range.

SPB owner 2026-05-27 — micro_flake percentile compression (M 42–164) reads flat in
Finish Viewer. This module marries each finish's fine geometry to extreme spec swings
(ΔM≥200 typical) and stacks 8–32px paint features with multi-tier flake palettes.

See docs/COLORSHOXX_ANGLE_REVEAL.md for angle-reveal family; this is the
multi-zone / multi-flake pop lane for Wave 4 + Micro Shift rebuilds.
"""

from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache

import cv2
import numpy as np

from engine.paint_v2.structural_color import (
    _cx_buried_reveal_gate,
    _cx_directional_mask,
    _cx_fine_spec_pins,
    _cx_hash01,
    _cx_ultra_micro,
    _cx_xy,
)


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _paint3(paint):
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].copy()
    return paint


def _pack_spec(M, R, CC, mask, shape):
    h, w = _hw(shape)
    # 2026-06-20 COLORSHOXX spectrum-pop rework: csp_spec_pop drove M/R/Cc from one
    # `flash` field (|corr|~1.0, flat Cc). Add fake-3D bevel relief + decorrelate R/Cc
    # via the shared depth3d post-pass (deterministic per-finish seed from M content).
    try:
        from engine.paint_v2 import depth3d_2026 as _d3
        _M = np.asarray(M, np.float32)
        _seed = int(abs(float(_M.mean()) * 131.0) + abs(float(_M[::97, ::97].sum()))) & 0x7FFFFFFF
        M, R, CC = _d3.decorrelate_envelope(_M, R, CC, seed=_seed, blend=0.7)
    except Exception:
        pass
    m = mask.astype(np.float32)
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(M * m, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.where(m > 0.01, np.clip(R, 15, 255), 0).astype(np.uint8)
    spec[:, :, 2] = np.where(m > 0.01, np.clip(CC, 16, 255), 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    return spec


_CSP_GEO_CACHE = OrderedDict()
_CSP_GEO_CACHE_MAX = 16
_CSP_DIR_MASK_CACHE = OrderedDict()
_CSP_DIR_MASK_CACHE_MAX = 32
_CSP_GATE_CACHE = OrderedDict()
_CSP_GATE_CACHE_MAX = 8
_CSP_WORK_MAX = 768


def _csp_work_shape(shape, cap=_CSP_WORK_MAX):
    h, w = _hw(shape)
    work = min(int(cap), int(h), int(w))
    if work >= min(h, w):
        return int(h), int(w)
    return max(128, int(round(h * work / max(h, w)))), max(128, int(round(w * work / max(h, w))))


def _csp_resize(field, shape):
    h, w = _hw(shape)
    if field.shape == (h, w):
        return field.astype(np.float32, copy=False)
    return cv2.resize(field.astype(np.float32, copy=False), (int(w), int(h)), interpolation=cv2.INTER_LINEAR).astype(np.float32)


def _csp_geo(shape, seed, seed_off, geo_fn):
    h, w = _hw(shape)
    key = (int(h), int(w), int(seed), int(seed_off), id(geo_fn))
    cached = _CSP_GEO_CACHE.get(key)
    if cached is not None:
        _CSP_GEO_CACHE.move_to_end(key)
        return cached
    work_shape = _csp_work_shape((int(h), int(w)))
    out = geo_fn(work_shape, seed)
    if work_shape != (int(h), int(w)):
        out = _csp_resize(out, (int(h), int(w)))
    _CSP_GEO_CACHE[key] = out
    _CSP_GEO_CACHE.move_to_end(key)
    while len(_CSP_GEO_CACHE) > _CSP_GEO_CACHE_MAX:
        _CSP_GEO_CACHE.popitem(last=False)
    return out


def _csp_directional_mask(shape, axis, seed, freq=52.0):
    # SPB paint-finish perf loop tick 2026-05-31 07:08; owner: "Speed is king in this app."
    # Exact directional-mask reuse for Spectrum COLORSHOXX spec+paint; cx_ocean_trench 8096.7 -> 7118.3 ms,
    # cx_emerald_city 8073.6 -> 7143.7 ms, paint/spec std drift 0.
    h, w = _hw(shape)
    key = (int(h), int(w), str(axis), int(seed), float(freq))
    cached = _CSP_DIR_MASK_CACHE.get(key)
    if cached is not None:
        _CSP_DIR_MASK_CACHE.move_to_end(key)
        return cached
    work_shape = _csp_work_shape((int(h), int(w)))
    out = _cx_directional_mask(work_shape, axis, seed, freq=freq)
    if work_shape != (int(h), int(w)):
        out = _csp_resize(out, (int(h), int(w)))
    _CSP_DIR_MASK_CACHE[key] = out
    _CSP_DIR_MASK_CACHE.move_to_end(key)
    while len(_CSP_DIR_MASK_CACHE) > _CSP_DIR_MASK_CACHE_MAX:
        _CSP_DIR_MASK_CACHE.popitem(last=False)
    return out


def _blend(paint, color, mask, pm, strength=0.96):
    m3 = mask[:, :, np.newaxis].astype(np.float32)
    bl = np.clip(float(pm) * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * bl) + color * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


def csp_spec_pop(flash, sm, *, pin=None, m_absorb=10, m_flash=252, r_absorb=215, r_flash=15,
                 cc_absorb=185, cc_flash=16, m_mod=None, r_mod=None, cc_mod=None):
    """Full-range spec marriage — NO percentile compression."""
    flash = np.clip(flash, 0, 1)
    pins = np.clip(pin if pin is not None else flash, 0, 1)
    absorb = 1.0 - flash
    M = m_absorb + flash * (m_flash - m_absorb) * sm + pins * 78.0 * sm
    R = r_absorb - flash * (r_absorb - r_flash) * sm - pins * 62.0 * sm + absorb * 10.0
    CC = cc_absorb - flash * (cc_absorb - cc_flash) * sm + pins * 52.0 * sm
    if m_mod is not None:
        M = np.clip(M + m_mod * sm, 0, 255)
    if r_mod is not None:
        R = np.clip(R + r_mod * sm, 15, 255)
    if cc_mod is not None:
        CC = np.clip(CC + cc_mod * sm, 16, 255)
    return (
        np.clip(M, 0, 255).astype(np.float32),
        np.clip(R, 15, 255).astype(np.float32),
        np.clip(CC, 16, 255).astype(np.float32),
    )


def _csp_gate_stack(shape, seed, seed_off, density=0.0115):
    # SPB paint-finish perf loop tick 2026-05-31 06:53; owner: "Speed is king in this app."
    # Exact gate/geometry reuse for Spectrum COLORSHOXX spec+paint; cx_emerald_city 8073.6 -> 7143.7 ms, std drift 0.
    h, w = _hw(shape)
    key = (int(h), int(w), int(seed), int(seed_off), float(density))
    cached = _CSP_GATE_CACHE.get(key)
    if cached is not None:
        _CSP_GATE_CACHE.move_to_end(key)
        return cached
    work_shape = _csp_work_shape((int(h), int(w)))
    fields = _csp_gate_stack_cached(work_shape[0], work_shape[1], int(seed), int(seed_off), float(density))
    if work_shape != (int(h), int(w)):
        fields = tuple(_csp_resize(field, (int(h), int(w))) for field in fields)
    # SPB perf loop 2026-05-31; owner hard ceiling: no base over 4s. Work at 1024, reuse full-size paint+spec fields.
    _CSP_GATE_CACHE[key] = fields
    _CSP_GATE_CACHE.move_to_end(key)
    while len(_CSP_GATE_CACHE) > _CSP_GATE_CACHE_MAX:
        _CSP_GATE_CACHE.popitem(last=False)
    return fields


@lru_cache(maxsize=32)
def _csp_gate_stack_cached(h, w, seed, seed_off, density=0.0115):
    shape = (int(h), int(w))
    gate = _cx_buried_reveal_gate(shape, seed, seed_off, density=density, layers=6)
    micro = _cx_ultra_micro(shape, seed + seed_off * 17)
    pins = _cx_fine_spec_pins(shape, seed, seed_off, density=density * 0.82, layers=6)
    sparkle = np.clip((micro - 0.24) * 1.55, 0, 1)
    return gate, micro, pins, sparkle


def _csp_body(body_rgb, shadow_rgb, h, w, ratio=0.58):
    body = np.asarray(body_rgb, dtype=np.float32).reshape(1, 1, 3)
    shadow = np.asarray(shadow_rgb, dtype=np.float32).reshape(1, 1, 3)
    return np.broadcast_to(np.clip(shadow * (1.0 - ratio) + body * ratio, 0, 1), (h, w, 3)).copy()


def _csp_tier_flakes(shape, seed, salt, palette, micro, strength=0.32):
    pal = np.asarray(palette, dtype=np.float32).reshape(-1, 3)
    pick = _cx_hash01(shape, seed, salt)
    idx = np.clip(np.floor(pick * len(pal)).astype(np.int32), 0, len(pal) - 1)
    tier = np.clip((pick * 8.0) % 1.0, 0, 1)
    mask = np.clip((micro - 0.20) * 1.65, 0, 1) * (0.55 + tier * 0.45) * strength
    return pal[idx] * mask[:, :, np.newaxis], mask


def _csp_add_reveals(color, shape, seed, seed_off, reveals, gate, pm):
    h, w = _hw(shape)
    bl = np.clip(float(pm), 0, 1)
    for i, (rgb, axis, strength) in enumerate(reveals):
        axis_m = _csp_directional_mask(shape, axis, seed + seed_off + i * 419)
        rgb3 = np.asarray(rgb, dtype=np.float32).reshape(1, 1, 3)
        layer = gate * axis_m * float(strength)
        color = np.clip(color + rgb3 * layer[:, :, np.newaxis] * bl * 0.82, 0, 1)
    return color


# ── Motif geometry (shared paint + spec) ───────────────────────────────────

def _geo_sun_rays(shape, seed):
    x, y = _cx_xy(shape)
    cx, cy = 0.52 + 0.06 * np.sin(seed * 0.011), 0.72 + 0.05 * np.cos(seed * 0.013)
    ang = np.arctan2(y - cy, x - cx)
    rad = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    rays = np.clip(0.5 + 0.5 * np.sin(ang * 28.0 + rad * 88.0 * np.pi + seed * 0.002), 0, 1)
    return np.clip((rays - 0.42) * 2.6, 0, 1).astype(np.float32)


def _geo_biolum(shape, seed):
    x, y = _cx_xy(shape)
    pulse = np.clip(0.5 + 0.5 * np.sin((y * 118.0 + np.sin(x * 94.0 + seed * 0.002) * 0.35) * np.pi), 0, 1)
    pins = _cx_fine_spec_pins(shape, seed, 9601, density=0.0108, layers=6)
    return np.clip(pulse * 0.48 + pins * 0.52, 0, 1).astype(np.float32)


def _geo_starfield(shape, seed):
    h1 = _cx_hash01(shape, seed, 9602)
    stars = np.clip((h1 - 0.82) * 9.5, 0, 1)
    x, y = _cx_xy(shape)
    dust = np.clip(0.5 + 0.5 * np.sin((x * 132.0 + y * 98.0 + seed * 0.003) * np.pi), 0, 1)
    dust = np.clip((dust - 0.55) * 3.2, 0, 1)
    return np.clip(stars * 0.72 + dust * 0.28, 0, 1).astype(np.float32)


def _geo_neon_tubes(shape, seed):
    x, y = _cx_xy(shape)
    tube_a = np.clip(0.5 + 0.5 * np.sin((x * 96.0 + seed * 0.004) * np.pi), 0, 1)
    tube_b = np.clip(0.5 + 0.5 * np.cos((y * 88.0 + np.sin(x * 72.0) * 0.4) * np.pi), 0, 1)
    edge = np.clip((tube_a - 0.68) * 5.0, 0, 1) + np.clip((tube_b - 0.66) * 4.8, 0, 1)
    return np.clip(edge * 0.55, 0, 1).astype(np.float32)


def _geo_magma_crack(shape, seed):
    x, y = _cx_xy(shape)
    crack = np.clip(0.5 + 0.5 * np.sin((x * 82.0 + np.cos(y * 104.0 + seed * 0.002) * 0.45) * np.pi), 0, 1)
    crack *= np.clip(0.5 + 0.5 * np.cos((y * 74.0 + crack * 0.55) * np.pi), 0, 1)
    return np.clip((crack - 0.48) * 4.5, 0, 1).astype(np.float32)


def _geo_lightning(shape, seed):
    x, y = _cx_xy(shape)
    bolt = np.zeros(shape, dtype=np.float32)
    for fx, fy, ph in [(92.0, 118.0, 0.0), (68.0, 142.0, 1.4)]:
        b = np.clip(0.5 + 0.5 * np.sin((x * fx + np.sin(y * fy + seed * 0.001 + ph) * 0.38) * np.pi), 0, 1)
        bolt = np.clip(bolt + np.clip((b - 0.54) * 5.5, 0, 1) * 0.55, 0, 1)
    rain = np.clip(0.5 + 0.5 * np.sin((x * 148.0 + y * 12.0) * np.pi), 0, 1)
    rain = np.clip((rain - 0.72) * 6.0, 0, 1)
    return np.clip(bolt * 0.68 + rain * 0.32, 0, 1).astype(np.float32)


def _geo_emerald_spires(shape, seed):
    x, _ = _cx_xy(shape)
    spire = np.clip(0.5 + 0.5 * np.sin((x * 124.0 + seed * 0.003) * np.pi), 0, 1)
    spire = np.clip((spire - 0.66) * 5.2, 0, 1)
    road = _csp_directional_mask(shape, "v", seed + 9633)
    return np.clip(spire * 0.62 + road * 0.38, 0, 1).astype(np.float32)


def _geo_patina_plates(shape, seed):
    x, y = _cx_xy(shape)
    plate = np.clip(0.5 + 0.5 * np.cos((x * 64.0 + y * 52.0) * np.pi), 0, 1)
    edge = np.clip(1.0 - np.abs(plate - 0.5) * 4.2, 0, 1)
    verd = _cx_ultra_micro(shape, seed + 9644)
    return np.clip(edge * 0.70 + np.clip((verd - 0.58) * 3.0, 0, 1) * 0.30, 0, 1).astype(np.float32)


def _geo_ember_smoke(shape, seed):
    x, y = _cx_xy(shape)
    ember = _cx_hash01(shape, seed, 9655)
    ember = np.clip((ember - 0.78) * 6.5, 0, 1)
    smoke = np.clip(0.5 + 0.5 * np.sin((y * 76.0 - x * 18.0 + seed * 0.002) * np.pi), 0, 1)
    smoke = np.clip((smoke - 0.45) * 2.2, 0, 1)
    return np.clip(ember * 0.58 + smoke * 0.42, 0, 1).astype(np.float32)


def _geo_stealth_rainbow(shape, seed):
    h1 = _cx_hash01(shape, seed, 9666)
    burst = np.clip((h1 - 0.84) * 8.0, 0, 1)
    x, _ = _cx_xy(shape)
    stealth = np.clip(1.0 - np.abs(x - 0.5) * 1.8, 0, 1)
    return np.clip(burst * stealth, 0, 1).astype(np.float32)


def _geo_impossible_shards(shape, seed):
    x, y = _cx_xy(shape)
    shard = np.sin((x * 156.0 + y * 112.0) * np.pi) * np.cos((x * 88.0 - y * 134.0 + seed * 0.002) * np.pi)
    return np.clip((shard - 0.08) * 2.4, 0, 1).astype(np.float32)


def _geo_trizone_weave(shape, seed, freq=108.0):
    u = _csp_directional_mask(shape, "u", seed)
    v = _csp_directional_mask(shape, "v", seed + 17)
    d = _csp_directional_mask(shape, "diag_a", seed + 31)
    x, y = _cx_xy(shape)
    weave = np.clip(0.5 + 0.5 * np.sin((x * freq + y * freq * 0.62) * np.pi), 0, 1)
    return np.clip(u * 0.38 + v * 0.34 + d * 0.28 + weave * 0.22, 0, 1).astype(np.float32)


def _geo_prism_shards(shape, seed):
    x, y = _cx_xy(shape)
    shard = np.sin((x * 142.0 + y * 98.0) * np.pi) * np.cos((x * 76.0 - y * 118.0 + seed * 0.002) * np.pi)
    pins = _cx_fine_spec_pins(shape, seed, 9109, density=0.0105, layers=6)
    return np.clip(np.clip((shard - 0.12) * 2.6, 0, 1) * 0.58 + pins * 0.42, 0, 1).astype(np.float32)


def _geo_copper_filament(shape, seed):
    x, y = _cx_xy(shape)
    arc = np.clip(0.5 + 0.5 * np.sin((x * 82.0 + np.cos(y * 102.0 + seed * 0.002) * 0.48) * np.pi), 0, 1)
    arc *= np.clip(0.5 + 0.5 * np.cos((y * 72.0 + arc * 0.65) * np.pi), 0, 1)
    return np.clip((arc - 0.46) * 4.8, 0, 1).astype(np.float32)


def _geo_pearl_shift(shape, seed):
    frost = _cx_ultra_micro(shape, seed + 91081)
    pearl = _cx_hash01(shape, seed, 91082)
    band = _csp_directional_mask(shape, "v", seed + 91083)
    return np.clip((frost - 0.48) * 2.2 + (pearl - 0.62) * 2.6 + band * 0.18, 0, 1).astype(np.float32)


# ── Generic finish builder ─────────────────────────────────────────────────

def _csp_generic_paint(paint, shape, mask, seed, pm, seed_off, body, shadow, flakes, reveals, geo_fn, gate_density=0.012):
    paint = _paint3(paint)
    h, w = _hw(shape)
    gate, micro, pins, sparkle = _csp_gate_stack((h, w), seed, seed_off, gate_density)
    color = _csp_body(body, shadow, h, w)
    color = _csp_add_reveals(color, (h, w), seed, seed_off, reveals, gate, pm)
    flake_rgb, flake_m = _csp_tier_flakes((h, w), seed, seed_off + 55, flakes, micro, 0.34)
    color = np.clip(color + flake_rgb * gate[:, :, np.newaxis] * pm, 0, 1)
    geo = _csp_geo((h, w), seed, seed_off, geo_fn) * gate
    m3 = mask[:, :, np.newaxis]
    accent = np.asarray(flakes[0], dtype=np.float32).reshape(1, 1, 3)
    color = np.clip(color + accent * geo[:, :, np.newaxis] * 0.42 * pm * m3, 0, 1)
    color = np.clip(color + sparkle[:, :, np.newaxis] * np.asarray(body, dtype=np.float32).reshape(1, 1, 3) * 0.12 * pm, 0, 1)
    return _blend(paint, color, mask, pm)


def _csp_generic_spec(shape, mask, seed, sm, seed_off, geo_fn, reveals, gate_density=0.012, cc_forward=False):
    h, w = _hw(shape)
    gate, micro, pins, sparkle = _csp_gate_stack((h, w), seed, seed_off, gate_density)
    geo = _csp_geo((h, w), seed, seed_off, geo_fn) * gate
    axis_flash = np.zeros((h, w), dtype=np.float32)
    for i, (_, axis, strength) in enumerate(reveals):
        axis_flash = np.clip(axis_flash + _csp_directional_mask((h, w), axis, seed + seed_off + i * 419) * strength, 0, 1)
    if reveals:
        axis_flash /= len(reveals)
    flash = np.clip(geo * 0.72 + axis_flash * gate * 0.28 + sparkle * 0.18, 0, 1)
    pin = np.clip(pins * geo + sparkle * 0.35, 0, 1)
    if cc_forward:
        M, R, CC = csp_spec_pop(flash, sm, pin=pin, cc_absorb=140, cc_flash=22, r_absorb=175, r_flash=18)
        CC = np.clip(CC + (1.0 - flash) * 48.0 * sm - flash * 38.0 * sm + geo * 42.0 * sm, 16, 255)
    else:
        M, R, CC = csp_spec_pop(flash, sm, pin=pin)
    return _pack_spec(M, R, CC, mask, shape)


def _mk(seed_off, body, shadow, flakes, reveals, geo_fn, gate_density=0.012, cc_forward=False):
    def paint(paint, shape, mask, seed, pm, bb):
        return _csp_generic_paint(paint, shape, mask, seed, pm, seed_off, body, shadow, flakes, reveals, geo_fn, gate_density)

    def spec(shape, mask, seed, sm):
        return _csp_generic_spec(shape, mask, seed, sm, seed_off, geo_fn, reveals, gate_density, cc_forward)

    return spec, paint


# ── Wave 4 + Micro Shift rebuilds ─────────────────────────────────────────

_SPEC_DEEP_SEA = _mk(
    9601, (0.08, 0.42, 0.62), (0.02, 0.06, 0.12),
    [(0.12, 0.95, 0.82), (0.05, 0.55, 0.95), (0.02, 0.18, 0.42), (0.68, 0.92, 0.98)],
    [((0.12, 0.95, 0.82), "v", 0.90), ((0.05, 0.55, 0.95), "u", 0.84), ((0.68, 0.92, 0.98), "diag_a", 0.72)],
    _geo_biolum, 0.0125,
)

_SPEC_GALAXY = _mk(
    9602, (0.12, 0.08, 0.28), (0.02, 0.02, 0.06),
    [(0.85, 0.45, 0.98), (0.55, 0.62, 1.0), (0.98, 0.72, 0.42), (0.22, 0.08, 0.55)],
    [((0.85, 0.45, 0.98), "diag_a", 0.88), ((0.55, 0.62, 1.0), "u", 0.82), ((0.98, 0.72, 0.42), "v", 0.68)],
    _geo_starfield, 0.0118,
)

_SPEC_TROPICAL = _mk(
    9630, (0.92, 0.38, 0.18), (0.10, 0.06, 0.08),
    [(0.98, 0.72, 0.18), (0.98, 0.28, 0.52), (0.98, 0.48, 0.12), (0.92, 0.18, 0.38)],
    [((0.98, 0.72, 0.18), "u", 0.90), ((0.98, 0.28, 0.52), "v", 0.86), ((0.98, 0.48, 0.12), "diag_a", 0.80)],
    _geo_sun_rays, 0.0122,
)

_SPEC_NEON = _mk(
    9648, (0.08, 0.12, 0.18), (0.03, 0.04, 0.06),
    [(0.98, 0.12, 0.82), (0.12, 0.92, 0.98), (0.22, 0.98, 0.42), (0.72, 0.22, 0.98)],
    [((0.98, 0.12, 0.82), "u", 0.88), ((0.12, 0.92, 0.98), "v", 0.86), ((0.22, 0.98, 0.42), "diag_b", 0.78)],
    _geo_neon_tubes, 0.0130,
)

_SPEC_VOLCANIC = _mk(
    9644, (0.18, 0.06, 0.04), (0.04, 0.02, 0.02),
    [(0.98, 0.42, 0.08), (0.98, 0.72, 0.18), (0.55, 0.08, 0.02), (0.12, 0.12, 0.14)],
    [((0.98, 0.42, 0.08), "u", 0.92), ((0.98, 0.72, 0.18), "v", 0.84), ((0.12, 0.12, 0.14), "diag_a", 0.62)],
    _geo_magma_crack, 0.0120,
)

_SPEC_THUNDER = _mk(
    9626, (0.06, 0.08, 0.14), (0.02, 0.03, 0.05),
    [(0.82, 0.88, 0.98), (0.42, 0.55, 0.95), (0.95, 0.95, 0.98), (0.18, 0.22, 0.35)],
    [((0.82, 0.88, 0.98), "v", 0.90), ((0.42, 0.55, 0.95), "u", 0.82), ((0.95, 0.95, 0.98), "diag_a", 0.74)],
    _geo_lightning, 0.0115,
)

_SPEC_EMERALD_W4 = _mk(
    9656, (0.12, 0.72, 0.38), (0.04, 0.08, 0.05),
    [(0.18, 0.92, 0.48), (0.95, 0.82, 0.18), (0.82, 0.12, 0.28), (0.08, 0.58, 0.32)],
    [((0.18, 0.92, 0.48), "u", 0.90), ((0.95, 0.82, 0.18), "v", 0.88), ((0.82, 0.12, 0.28), "diag_b", 0.68)],
    _geo_emerald_spires, 0.0120,
)

_SPEC_BRONZE_AGE = _mk(
    9664, (0.72, 0.42, 0.14), (0.12, 0.08, 0.05),
    [(0.88, 0.58, 0.18), (0.42, 0.72, 0.38), (0.62, 0.32, 0.12), (0.28, 0.48, 0.42)],
    [((0.88, 0.58, 0.18), "u", 0.88), ((0.42, 0.72, 0.38), "v", 0.82), ((0.62, 0.32, 0.12), "diag_a", 0.72)],
    _geo_patina_plates, 0.0118,
)

_SPEC_FOREST = _mk(
    9610, (0.18, 0.62, 0.12), (0.05, 0.08, 0.04),
    [(0.98, 0.42, 0.08), (0.98, 0.72, 0.12), (0.42, 0.98, 0.18), (0.12, 0.38, 0.08)],
    [((0.98, 0.42, 0.08), "u", 0.90), ((0.42, 0.98, 0.18), "v", 0.82), ((0.98, 0.72, 0.12), "diag_a", 0.76)],
    _geo_ember_smoke, 0.0122,
)

_SPEC_RAINBOW_STEALTH = _mk(
    9697, (0.08, 0.08, 0.10), (0.02, 0.02, 0.03),
    [(0.98, 0.22, 0.32), (0.98, 0.82, 0.12), (0.22, 0.92, 0.48), (0.28, 0.42, 0.98), (0.82, 0.22, 0.98), (0.98, 0.42, 0.72)],
    [((0.98, 0.22, 0.32), "u", 0.78), ((0.22, 0.92, 0.48), "v", 0.74), ((0.28, 0.42, 0.98), "diag_a", 0.70)],
    _geo_stealth_rainbow, 0.0095,
)

_SPEC_RED_GREEN = _mk(
    9316, (0.88, 0.08, 0.08), (0.06, 0.06, 0.06),
    [(0.98, 0.12, 0.10), (0.12, 0.92, 0.22), (0.92, 0.18, 0.12), (0.18, 0.98, 0.32)],
    [((0.98, 0.12, 0.10), "u", 0.92), ((0.12, 0.92, 0.22), "v", 0.90), ((0.18, 0.98, 0.32), "diag_b", 0.82)],
    _geo_impossible_shards, 0.0135,
)

_SPEC_GOLD_OLIVE = _mk(
    9253, (0.92, 0.72, 0.18), (0.10, 0.08, 0.05),
    [(0.98, 0.82, 0.22), (0.58, 0.72, 0.18), (0.18, 0.82, 0.42), (0.82, 0.62, 0.12)],
    [((0.98, 0.82, 0.22), "u", 0.88), ((0.58, 0.72, 0.18), "v", 0.84), ((0.18, 0.82, 0.42), "diag_a", 0.78)],
    lambda s, sd: _geo_trizone_weave(s, sd, 112.0), 0.0120,
)

_SPEC_PURPLE_PLUM = _mk(
    9259, (0.48, 0.12, 0.72), (0.08, 0.05, 0.10),
    [(0.62, 0.08, 0.88), (0.82, 0.18, 0.58), (0.88, 0.55, 0.22), (0.42, 0.08, 0.62)],
    [((0.62, 0.08, 0.88), "u", 0.88), ((0.88, 0.55, 0.22), "v", 0.86), ((0.82, 0.18, 0.58), "diag_a", 0.74)],
    lambda s, sd: _geo_trizone_weave(s, sd, 104.0), 0.0120,
)

_SPEC_BURGUNDY = _mk(
    9271, (0.62, 0.08, 0.18), (0.08, 0.04, 0.06),
    [(0.82, 0.06, 0.14), (0.52, 0.04, 0.22), (0.98, 0.78, 0.22), (0.92, 0.42, 0.12)],
    [((0.82, 0.06, 0.14), "u", 0.90), ((0.98, 0.78, 0.22), "v", 0.88), ((0.52, 0.04, 0.22), "diag_b", 0.72)],
    lambda s, sd: _geo_trizone_weave(s, sd, 98.0), 0.0122,
)


def _geo_trench_vents(shape, seed):
    _, y = _cx_xy(shape)
    vent = np.clip(0.5 + 0.5 * np.sin((y * 132.0 + seed * 0.004) * np.pi), 0, 1)
    vent = np.clip((vent - 0.40) * 2.2, 0, 1)
    bio = _geo_biolum(shape, seed)
    return np.clip(vent * 0.48 + bio * 0.52, 0, 1).astype(np.float32)


_SPEC_OCEAN_TRENCH = _mk(
    9024, (0.10, 0.72, 0.58), (0.01, 0.03, 0.08),
    [(0.08, 0.92, 0.78), (0.04, 0.42, 0.88), (0.02, 0.12, 0.38), (0.55, 0.98, 0.92)],
    [((0.08, 0.92, 0.78), "v", 0.92), ((0.04, 0.42, 0.88), "u", 0.86), ((0.55, 0.98, 0.92), "diag_b", 0.74)],
    _geo_trench_vents, 0.0128,
)


def paint_spectrum_ocean_trench(paint, shape, mask, seed, pm, bb):
    return _SPEC_OCEAN_TRENCH[1](paint, shape, mask, seed, pm, bb)


def spec_spectrum_ocean_trench(shape, mask, seed, sm):
    return _SPEC_OCEAN_TRENCH[0](shape, mask, seed, sm)


def paint_spectrum_emerald_city(paint, shape, mask, seed, pm, bb):
    return _SPEC_EMERALD_W4[1](paint, shape, mask, seed, pm, bb)


def spec_spectrum_emerald_city(shape, mask, seed, sm):
    return _SPEC_EMERALD_W4[0](shape, mask, seed, sm)


# ── HyperFlip upgrades (crimson / blue-copper / silver-violet) ─────────────

_CRIMSON_COMPLIMENTS = [
    (0.02, 0.88, 0.98),   # cyan — complement to crimson
    (0.22, 0.95, 0.18),   # green-gold triad
    (0.68, 0.10, 0.98),   # violet split-complement
]

_CRIMSON_REVEALS = [
    (_CRIMSON_COMPLIMENTS[0], "u", 0.92),
    (_CRIMSON_COMPLIMENTS[1], "v", 0.88),
    (_CRIMSON_COMPLIMENTS[2], "diag_a", 0.84),
]


def paint_spectrum_crimson_prism(paint, shape, mask, seed, pm, bb):
    paint = _paint3(paint)
    h, w = _hw(shape)
    gate, micro, _, sparkle = _csp_gate_stack((h, w), seed, 9109, 0.0125)
    color = _csp_body((0.82, 0.05, 0.08), (0.08, 0.04, 0.05), h, w)
    color = _csp_add_reveals(color, (h, w), seed, 9109, _CRIMSON_REVEALS, gate, pm)
    shards = _geo_prism_shards((h, w), seed) * gate
    flake_rgb, _ = _csp_tier_flakes((h, w), seed, 91091, _CRIMSON_COMPLIMENTS, micro, 0.38)
    m3 = mask[:, :, np.newaxis]
    for i, rgb in enumerate(_CRIMSON_COMPLIMENTS):
        axis = ("u", "v", "diag_a")[i]
        axis_m = _csp_directional_mask((h, w), axis, seed + 9109 + i * 419)
        rgb3 = np.asarray(rgb, dtype=np.float32).reshape(1, 1, 3)
        color = np.clip(color + rgb3 * shards[:, :, np.newaxis] * axis_m[:, :, np.newaxis] * 0.48 * pm * m3, 0, 1)
    color = np.clip(color + flake_rgb * gate[:, :, np.newaxis] * pm + sparkle[:, :, np.newaxis] * 0.08 * pm, 0, 1)
    return _blend(paint, color, mask, pm)


def spec_spectrum_crimson_prism(shape, mask, seed, sm):
    h, w = _hw(shape)
    gate, micro, pins, sparkle = _csp_gate_stack((h, w), seed, 9109, 0.0125)
    shards = _geo_prism_shards((h, w), seed) * gate
    u = _csp_directional_mask((h, w), "u", seed + 9109) * gate
    v = _csp_directional_mask((h, w), "v", seed + 9209) * gate
    da = _csp_directional_mask((h, w), "diag_a", seed + 9309) * gate
    flash = np.clip(shards * 0.68 + (u * 0.34 + v * 0.33 + da * 0.33) * 0.32 + sparkle * 0.15, 0, 1)
    pin = np.clip(pins * shards + sparkle * 0.42, 0, 1)
    M, R, CC = csp_spec_pop(flash, sm, pin=pin, r_mod=-u * 42.0 + v * 28.0 + da * 22.0)
    CC = np.clip(CC + u * 38.0 * sm - v * 24.0 * sm + da * 32.0 * sm + np.clip((micro - 0.5) * 2.0, 0, 1) * 28.0 * sm, 16, 255)
    M = np.clip(M + shards * 48.0 * sm, 0, 255)
    return _pack_spec(M, R, CC, mask, shape)


_COPPER_REVEALS = [
    ((0.98, 0.52, 0.08), "u", 0.94),
    ((0.12, 0.38, 0.98), "v", 0.82),
    ((0.98, 0.72, 0.18), "diag_a", 0.76),
]


def paint_spectrum_electric_blue_copper(paint, shape, mask, seed, pm, bb):
    paint = _paint3(paint)
    h, w = _hw(shape)
    gate, micro, _, _ = _csp_gate_stack((h, w), seed, 9106, 0.0120)
    color = _csp_body((0.72, 0.38, 0.10), (0.06, 0.08, 0.14), h, w, ratio=0.52)
    color = _csp_add_reveals(color, (h, w), seed, 9106, _COPPER_REVEALS, gate, pm)
    copper = _geo_copper_filament((h, w), seed) * gate
    copper_rgb = np.array([0.98, 0.55, 0.10], dtype=np.float32)
    blue_rgb = np.array([0.08, 0.32, 0.98], dtype=np.float32)
    u = _csp_directional_mask((h, w), "u", seed + 9106)
    v = _csp_directional_mask((h, w), "v", seed + 9206)
    m3 = mask[:, :, np.newaxis]
    color = np.clip(
        color + copper_rgb.reshape(1, 1, 3) * copper[:, :, np.newaxis] * u[:, :, np.newaxis] * 0.58 * pm * m3
        + blue_rgb.reshape(1, 1, 3) * copper[:, :, np.newaxis] * (1.0 - u)[:, :, np.newaxis] * v[:, :, np.newaxis] * 0.38 * pm * m3,
        0, 1,
    )
    flake_rgb, _ = _csp_tier_flakes((h, w), seed, 91061, [(0.98, 0.62, 0.12), (0.98, 0.42, 0.08), (0.12, 0.42, 0.98)], micro, 0.36)
    return _blend(paint, np.clip(color + flake_rgb * gate[:, :, np.newaxis] * pm, 0, 1), mask, pm)


def spec_spectrum_electric_blue_copper(shape, mask, seed, sm):
    h, w = _hw(shape)
    gate, _, pins, sparkle = _csp_gate_stack((h, w), seed, 9106, 0.0120)
    copper = _geo_copper_filament((h, w), seed) * gate
    u = _csp_directional_mask((h, w), "u", seed + 9106)
    v = _csp_directional_mask((h, w), "v", seed + 9206)
    flash = np.clip(copper * u * 0.62 + copper * (1.0 - u) * v * 0.38 + sparkle * 0.12, 0, 1)
    pin = np.clip(pins * copper + sparkle * 0.35, 0, 1)
    M, R, CC = csp_spec_pop(flash, sm, pin=pin, r_mod=-copper * u * 55.0 + (1.0 - copper) * v * 18.0)
    CC = np.clip(CC + copper * u * 45.0 * sm - (1.0 - copper) * 28.0 * sm, 16, 255)
    M = np.clip(M + copper * 52.0 * sm, 0, 255)
    return _pack_spec(M, R, CC, mask, shape)


def paint_spectrum_silver_violet(paint, shape, mask, seed, pm, bb):
    paint = _paint3(paint)
    h, w = _hw(shape)
    gate, micro, _, sparkle = _csp_gate_stack((h, w), seed, 9108, 0.0118)
    color = _csp_body((0.82, 0.84, 0.88), (0.10, 0.10, 0.12), h, w)
    reveals = [((0.92, 0.94, 0.98), "u", 0.86), ((0.62, 0.12, 0.95), "v", 0.84)]
    color = _csp_add_reveals(color, (h, w), seed, 9108, reveals, gate, pm)
    shift = _geo_pearl_shift((h, w), seed) * gate
    silver = np.array([0.92, 0.94, 0.98], dtype=np.float32)
    violet = np.array([0.62, 0.12, 0.95], dtype=np.float32)
    v = _csp_directional_mask((h, w), "v", seed + 9108)
    u = _csp_directional_mask((h, w), "u", seed + 9208)
    m3 = mask[:, :, np.newaxis]
    color = np.clip(
        color + silver.reshape(1, 1, 3) * shift[:, :, np.newaxis] * u[:, :, np.newaxis] * 0.32 * pm * m3
        + violet.reshape(1, 1, 3) * shift[:, :, np.newaxis] * v[:, :, np.newaxis] * 0.38 * pm * m3
        + sparkle[:, :, np.newaxis] * silver.reshape(1, 1, 3) * 0.14 * pm * m3,
        0, 1,
    )
    flake_rgb, _ = _csp_tier_flakes((h, w), seed, 91081, [silver, violet, (0.78, 0.72, 0.98), (0.48, 0.08, 0.82)], micro, 0.34)
    return _blend(paint, np.clip(color + flake_rgb * gate[:, :, np.newaxis] * pm, 0, 1), mask, pm)


def spec_spectrum_silver_violet(shape, mask, seed, sm):
    h, w = _hw(shape)
    gate, micro, pins, sparkle = _csp_gate_stack((h, w), seed, 9108, 0.0118)
    shift = _geo_pearl_shift((h, w), seed) * gate
    u = _csp_directional_mask((h, w), "u", seed + 9108)
    v = _csp_directional_mask((h, w), "v", seed + 9208)
    silver_flash = shift * u
    violet_flash = shift * v
    flash = np.clip(silver_flash * 0.48 + violet_flash * 0.52 + sparkle * 0.14, 0, 1)
    pin = np.clip(pins * shift + sparkle * 0.45, 0, 1)
    M, R, CC = csp_spec_pop(flash, sm, pin=pin, cc_absorb=195, cc_flash=18, r_absorb=168, r_flash=16)
    CC = np.clip(CC + (1.0 - violet_flash) * 62.0 * sm - violet_flash * 72.0 * sm + silver_flash * 38.0 * sm, 16, 255)
    R = np.clip(R - violet_flash * 48.0 * sm + silver_flash * 22.0 * sm, 15, 255)
    M = np.clip(M + shift * 58.0 * sm + np.clip((micro - 0.55) * 2.5, 0, 1) * 32.0 * sm, 0, 255)
    return _pack_spec(M, R, CC, mask, shape)


SPECTRUM_POP_MONOLITHICS = {
    "cx_deep_sea": _SPEC_DEEP_SEA,
    "cx_galaxy_dust": _SPEC_GALAXY,
    "cx_tropical_sunset": _SPEC_TROPICAL,
    "cx_neon_dreams": _SPEC_NEON,
    "cx_volcanic_glass": _SPEC_VOLCANIC,
    "cx_thunderstorm": _SPEC_THUNDER,
    "cx_emerald_city": _SPEC_EMERALD_W4,
    "cx_bronze_age": _SPEC_BRONZE_AGE,
    "cx_forest_fire": _SPEC_FOREST,
    "cx_rainbow_stealth": _SPEC_RAINBOW_STEALTH,
    "cx_red_green_chaos": _SPEC_RED_GREEN,
    "cx_gold_olive_emerald": _SPEC_GOLD_OLIVE,
    "cx_purple_plum_bronze": _SPEC_PURPLE_PLUM,
    "cx_burgundy_wine_gold": _SPEC_BURGUNDY,
}

HYPERFLIP_SPECTRUM_POP = {
    "cx_hyperflip_crimson_prism": (spec_spectrum_crimson_prism, paint_spectrum_crimson_prism),
    "cx_hyperflip_electric_blue_copper": (spec_spectrum_electric_blue_copper, paint_spectrum_electric_blue_copper),
    "cx_hyperflip_silver_violet": (spec_spectrum_silver_violet, paint_spectrum_silver_violet),
}
