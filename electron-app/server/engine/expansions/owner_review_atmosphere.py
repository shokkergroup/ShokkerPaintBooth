"""Owner-reviewed Atmosphere monolithic rebuilds.

Each Special Atmosphere finish uses its own semantic height-field pair for paint
and a tuned spec stack: per-finish ``_living_field`` breath, asymmetric M/R/CC
micro+edge weights, and optional clearcoat/detail coupling so previews read as
distinct weather phenomena instead of a shared green-noise carrier.
"""

from __future__ import annotations

import functools

import numpy as np
import cv2


# --- Perf (look-preserving): cache the small set of shared resources used by
# nearly every finish. Each per-finish ``_*_fields`` builder is invoked by BOTH
# the paint and the spec function for the same (shape, seed); memoizing returns
# the byte-identical arrays the second time instead of recomputing the full
# float64 trig stack. Consumers treat these arrays as read-only (they always
# wrap them in np.clip / arithmetic that allocates fresh output), so sharing the
# object is safe. Small ring-buffer cap keeps memory bounded. ``_xy`` is also
# cached because it allocates two arrays on every helper call.
_ATM_FIELD_CACHE: dict = {}
_ATM_FIELD_CACHE_MAX = 8


def _memo_fields(fn):
    """Memoize a ``_*_fields(shape, seed)`` builder (byte-identical reuse)."""
    name = fn.__name__

    @functools.wraps(fn)
    def wrapper(shape, seed):
        key = (name, int(shape[0]), int(shape[1]), int(seed))
        cached = _ATM_FIELD_CACHE.get(key)
        if cached is not None:
            return cached
        if len(_ATM_FIELD_CACHE) >= _ATM_FIELD_CACHE_MAX:
            _ATM_FIELD_CACHE.pop(next(iter(_ATM_FIELD_CACHE)))
        out = fn(shape, seed)
        _ATM_FIELD_CACHE[key] = out
        return out

    return wrapper


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
    return float((int(seed) * 1664525 + int(salt) * 1013904223) & 0xFFFFFFFF) / 0xFFFFFFFF


def _hash(shape, seed, salt=0):
    x, y = _xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + _seed(seed, salt) * 67.3) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _waves(shape, seed, salt=0, scale=1.0):
    x, y = _xy(shape)
    a = _seed(seed, salt) * np.pi * 2.0
    b = _seed(seed, salt + 17) * np.pi * 2.0
    v = (
        np.sin((x * (9.0 + scale) + y * (5.0 + scale * 0.4)) * np.pi + a) * 0.36
        + np.sin((x * (31.0 + scale * 2.0) - y * (19.0 + scale)) * np.pi + b) * 0.28
        + np.sin((x * (83.0 + scale * 3.0) + y * (71.0 + scale * 2.0)) * np.pi + a + b) * 0.16
    )
    return np.clip((v + 0.80) / 1.60, 0, 1).astype(np.float32)


def _block_noise(shape, seed, salt=0, cells=64):
    h, w = shape
    rng = np.random.RandomState(int(seed) + int(salt))
    low = rng.rand(cells, cells).astype(np.float32)
    ry = int(np.ceil(h / cells))
    rx = int(np.ceil(w / cells))
    return np.repeat(np.repeat(low, ry, axis=0), rx, axis=1)[:h, :w]


def _smooth_noise(shape, seed, salt=0, cells=32):
    h, w = shape
    rng = np.random.RandomState(int(seed) + int(salt))
    low = rng.rand(max(2, cells), max(2, cells)).astype(np.float32)
    out = cv2.resize(low, (w, h), interpolation=cv2.INTER_CUBIC)
    out = cv2.GaussianBlur(out, (0, 0), max(0.6, min(h, w) / max(64.0, cells * 6.0)))
    mn, mx = float(out.min()), float(out.max())
    if mx > mn:
        out = (out - mn) / (mx - mn)
    return out.astype(np.float32)


def _cell_droplets(shape, seed, salt=0, cells=96, density=0.5, r_min=0.14, r_max=0.36):
    """Fast jittered-cell discs/rims for droplets, craters, bubbles, and flakes."""
    x, y = _xy(shape)
    gx = x * float(cells)
    gy = y * float(cells)
    ix = np.floor(gx)
    iy = np.floor(gy)
    fx = gx - ix
    fy = gy - iy
    base = ix * 127.1 + iy * 311.7 + _seed(seed, salt) * 997.3
    rnd = np.sin(base) * 43758.5453
    rnd = rnd - np.floor(rnd)
    rx = np.sin(base + 19.19) * 24634.6345
    rx = rx - np.floor(rx)
    ry = np.sin(base + 73.73) * 13541.2213
    ry = ry - np.floor(ry)
    rr = np.sin(base + 41.41) * 91231.1137
    rr = rr - np.floor(rr)
    present = (rnd > (1.0 - density)).astype(np.float32)
    cx = 0.5 + (rx - 0.5) * 0.52
    cy = 0.5 + (ry - 0.5) * 0.52
    radius = r_min + rr * (r_max - r_min)
    dist = np.sqrt((fx - cx) * (fx - cx) + (fy - cy) * (fy - cy))
    disc = np.clip(1.0 - dist / np.maximum(radius, 1e-4), 0, 1) * present
    rim = np.clip(1.0 - np.abs(dist - radius) / np.maximum(radius * 0.28, 1e-4), 0, 1) * present
    return disc.astype(np.float32), rim.astype(np.float32), present.astype(np.float32)


def _ridge(v, width=0.055):
    return np.clip(1.0 - np.abs(v) / max(width, 1e-4), 0, 1).astype(np.float32)


def _rgba(shape, mask):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 3] = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    return spec


def _bb(out, mask, bb, amount=0.08):
    if bb is None:
        return out
    arr = np.asarray(bb, dtype=np.float32)
    if arr.ndim == 0:
        return out
    if arr.ndim == 2:
        arr = arr[:, :, None]
    # Atmosphere-wide paint enrichment: inject fine, directional micro-variation
    # so large forms do not dominate while preserving each finish's macro story.
    shape = mask.shape
    x, y = _xy(shape)
    sig = int(
        (
            float(out[:, :, 0].mean()) * 1_000_003.0
            + float(out[:, :, 1].mean()) * 2_000_033.0
            + float(out[:, :, 2].mean()) * 3_000_217.0
            + float(amount) * 10_001.0
        )
    ) & 0xFFFFFFFF
    grain = _hash(shape, sig, 901)
    ridge = _ridge(
        np.sin(
            (
                x * (84.0 + amount * 140.0)
                + y * (63.0 + amount * 110.0)
                + grain * 4.8
            )
            * np.pi
        ),
        0.028,
    )
    curl = _ridge(
        np.sin((x * 132.0 - y * 116.0 + grain * 7.1) * np.pi),
        0.020,
    )
    micro = np.clip((grain - 0.5) * 0.18 + ridge * 0.14 + curl * 0.11, -0.16, 0.24)
    out = np.clip(
        out
        + micro[:, :, None]
        * np.array([0.85, 0.95, 1.08], dtype=np.float32).reshape(1, 1, 3)
        * amount
        * 0.52
        * mask[:, :, None],
        0,
        1,
    )
    return np.clip(out + arr[:, :, :1] * amount * mask[:, :, None], 0, 1)


def _paint_base(paint):
    return paint[:, :, :3].astype(np.float32, copy=True)


def _mix(base, color, amount, mask, pm):
    color_arr = np.asarray(color, dtype=np.float32).reshape(1, 1, 3)
    a = np.clip(amount * pm * mask, 0, 1)[:, :, None]
    return base * (1.0 - a) + color_arr * a


def _living_field(shape, seed, salt=0):
    """Slow spatial 'breathing' layer so atmosphere finishes feel alive on canvas."""
    x, y = _xy(shape)
    ph = _seed(seed, salt) * (np.pi * 2.0)
    kx = 11.0 + _seed(seed, salt + 1) * 26.0
    ky = 9.0 + _seed(seed, salt + 2) * 23.0
    warp = _waves(shape, seed, salt + 3, 1.12 + _seed(seed, salt + 7) * 2.05)
    lf = np.sin((x * kx + y * ky + ph) * np.pi * 2.0) * 0.5 + 0.5
    grain = _smooth_noise(shape, seed, salt + 4, cells=18 + int(_seed(seed, salt + 5) * 20))
    curl = np.sin((x * 41.0 - y * 37.0 + warp * 6.0 + _seed(seed, salt + 6) * 12.0) * np.pi) * 0.5 + 0.5
    return np.clip(lf * 0.46 + warp * 0.30 + grain * 0.14 + curl * 0.10, 0, 1).astype(np.float32)


_NEUTRAL_SPEC_KW = dict(
    living_strength=0.0,
    liv_salt=0,
    cc_detail_amp=0.0,
    inv_cc_detail=False,
    m_mic=60.0,
    m_ed=52.0,
    r_mic=38.0,
    r_ed=34.0,
    cc_mic=64.0,
    cc_ed=80.0,
)

# Per-finish spec tuning (all entries boosted vs earlier pass: stronger living + micro/edge + CC coupling).
_ATM_FINISH_KW = {
    "acid_rain": dict(
        living_strength=0.62,
        liv_salt=11,
        cc_detail_amp=64.0,
        m_mic=78.0,
        m_ed=68.0,
        r_mic=18.0,
        r_ed=58.0,
        cc_mic=28.0,
        cc_ed=118.0,
    ),
    "black_ice": dict(
        living_strength=0.44,
        liv_salt=12,
        cc_detail_amp=-50.0,
        inv_cc_detail=True,
        m_mic=50.0,
        m_ed=72.0,
        r_mic=50.0,
        r_ed=24.0,
        cc_mic=104.0,
        cc_ed=44.0,
    ),
    "blizzard": dict(
        living_strength=0.56,
        liv_salt=20,
        cc_detail_amp=-34.0,
        inv_cc_detail=True,
        m_mic=56.0,
        m_ed=60.0,
        r_mic=42.0,
        r_ed=38.0,
        cc_mic=110.0,
        cc_ed=52.0,
    ),
    "desert_mirage": dict(
        living_strength=0.64,
        liv_salt=30,
        cc_detail_amp=44.0,
        m_mic=68.0,
        m_ed=54.0,
        r_mic=44.0,
        r_ed=48.0,
        cc_mic=50.0,
        cc_ed=106.0,
    ),
    "dew_drop": dict(
        living_strength=0.50,
        liv_salt=40,
        cc_detail_amp=72.0,
        m_mic=64.0,
        m_ed=58.0,
        r_mic=24.0,
        r_ed=46.0,
        cc_mic=54.0,
        cc_ed=124.0,
    ),
    "dust_storm": dict(
        living_strength=0.42,
        liv_salt=50,
        cc_detail_amp=28.0,
        m_mic=54.0,
        m_ed=80.0,
        r_mic=56.0,
        r_ed=54.0,
        cc_mic=38.0,
        cc_ed=66.0,
    ),
    "ember_glow": dict(
        living_strength=0.58,
        liv_salt=60,
        cc_detail_amp=24.0,
        m_mic=86.0,
        m_ed=50.0,
        r_mic=30.0,
        r_ed=62.0,
        cc_mic=34.0,
        cc_ed=72.0,
    ),
    "fog_bank": dict(
        living_strength=0.62,
        liv_salt=70,
        cc_detail_amp=-46.0,
        inv_cc_detail=True,
        m_mic=50.0,
        m_ed=66.0,
        r_mic=52.0,
        r_ed=40.0,
        cc_mic=104.0,
        cc_ed=70.0,
    ),
    "frost_bite": dict(
        living_strength=0.48,
        liv_salt=80,
        cc_detail_amp=42.0,
        m_mic=58.0,
        m_ed=64.0,
        r_mic=40.0,
        r_ed=40.0,
        cc_mic=94.0,
        cc_ed=62.0,
    ),
    "frozen_lake": dict(
        living_strength=0.54,
        liv_salt=90,
        cc_detail_amp=48.0,
        m_mic=70.0,
        m_ed=60.0,
        r_mic=34.0,
        r_ed=50.0,
        cc_mic=58.0,
        cc_ed=108.0,
    ),
    "hail_damage": dict(
        living_strength=0.46,
        liv_salt=100,
        cc_detail_amp=34.0,
        m_mic=62.0,
        m_ed=78.0,
        r_mic=52.0,
        r_ed=58.0,
        cc_mic=40.0,
        cc_ed=94.0,
    ),
    "heat_wave": dict(
        living_strength=0.64,
        liv_salt=110,
        cc_detail_amp=54.0,
        m_mic=66.0,
        m_ed=48.0,
        r_mic=36.0,
        r_ed=44.0,
        cc_mic=46.0,
        cc_ed=114.0,
    ),
    "hurricane": dict(
        living_strength=0.56,
        liv_salt=120,
        cc_detail_amp=26.0,
        m_mic=72.0,
        m_ed=62.0,
        r_mic=30.0,
        r_ed=54.0,
        cc_mic=52.0,
        cc_ed=102.0,
    ),
    "lightning_strike": dict(
        living_strength=0.40,
        liv_salt=130,
        cc_detail_amp=30.0,
        m_mic=96.0,
        m_ed=80.0,
        r_mic=26.0,
        r_ed=64.0,
        cc_mic=36.0,
        cc_ed=128.0,
    ),
    "liquid_metal": dict(
        living_strength=0.62,
        liv_salt=140,
        cc_detail_amp=36.0,
        m_mic=78.0,
        m_ed=44.0,
        r_mic=22.0,
        r_ed=32.0,
        cc_mic=48.0,
        cc_ed=84.0,
    ),
    "meteor_shower": dict(
        living_strength=0.56,
        liv_salt=160,
        cc_detail_amp=46.0,
        m_mic=74.0,
        m_ed=70.0,
        r_mic=24.0,
        r_ed=68.0,
        cc_mic=32.0,
        cc_ed=132.0,
    ),
    "monsoon": dict(
        living_strength=0.60,
        liv_salt=170,
        cc_detail_amp=66.0,
        m_mic=60.0,
        m_ed=68.0,
        r_mic=44.0,
        r_ed=52.0,
        cc_mic=54.0,
        cc_ed=110.0,
    ),
    "ocean_floor": dict(
        living_strength=0.54,
        liv_salt=180,
        cc_detail_amp=38.0,
        m_mic=56.0,
        m_ed=56.0,
        r_mic=40.0,
        r_ed=36.0,
        cc_mic=78.0,
        cc_ed=98.0,
    ),
    "permafrost": dict(
        living_strength=0.44,
        liv_salt=190,
        cc_detail_amp=-28.0,
        inv_cc_detail=True,
        m_mic=54.0,
        m_ed=64.0,
        r_mic=44.0,
        r_ed=34.0,
        cc_mic=88.0,
        cc_ed=56.0,
    ),
    "solar_wind": dict(
        living_strength=0.52,
        liv_salt=200,
        cc_detail_amp=32.0,
        m_mic=80.0,
        m_ed=54.0,
        r_mic=28.0,
        r_ed=38.0,
        cc_mic=50.0,
        cc_ed=100.0,
    ),
    "tidal_wave": dict(
        living_strength=0.62,
        liv_salt=210,
        cc_detail_amp=52.0,
        m_mic=62.0,
        m_ed=58.0,
        r_mic=38.0,
        r_ed=40.0,
        cc_mic=70.0,
        cc_ed=106.0,
    ),
    "tornado_alley": dict(
        living_strength=0.58,
        liv_salt=220,
        cc_detail_amp=22.0,
        m_mic=68.0,
        m_ed=66.0,
        r_mic=48.0,
        r_ed=60.0,
        cc_mic=38.0,
        cc_ed=92.0,
    ),
    "volcanic_glass": dict(
        living_strength=0.36,
        liv_salt=230,
        cc_detail_amp=18.0,
        m_mic=76.0,
        m_ed=46.0,
        r_mic=20.0,
        r_ed=28.0,
        cc_mic=42.0,
        cc_ed=70.0,
    ),
}


def _finish_spec(
    shape,
    mask,
    feature,
    detail,
    m0,
    r0,
    cc0=18,
    m_amp=110,
    r_amp=90,
    cc_amp=20,
    sm=1.0,
    *,
    seed=0,
    living_strength=0.0,
    liv_salt=0,
    cc_detail_amp=0.0,
    inv_cc_detail=False,
    m_mic=54.0,
    m_ed=46.0,
    r_mic=34.0,
    r_ed=30.0,
    cc_mic=58.0,
    cc_ed=72.0,
):
    spec = _rgba(shape, mask)
    f = np.clip(feature, 0, 1)
    d = np.clip(detail, 0, 1)
    if living_strength > 1e-6:
        live = _living_field(shape, seed, liv_salt)
        breathe = (live - 0.5) * 2.0 * living_strength
        f = np.clip(f + breathe * 0.44, 0, 1)
        d = np.clip(d + breathe * 0.36, 0, 1)
    edge = np.clip(
        np.abs(f - np.roll(f, 1, axis=0))
        + np.abs(f - np.roll(f, 1, axis=1))
        + np.abs(d - np.roll(d, 2, axis=0)) * 0.60
        + np.abs(d - np.roll(d, 2, axis=1)) * 0.60,
        0,
        1,
    )
    micro = np.clip(
        d * 0.68
        + edge * 1.75
        + np.maximum(0.0, d - np.roll(d, 3, axis=1)) * 0.55
        + np.maximum(0.0, f - np.roll(f, -2, axis=0)) * 0.35,
        0,
        1,
    )
    # Global spec detail boost (micro + edge; stacks with per-finish m_mic / m_ed / …).
    det_scale = 1.38
    micro = np.clip(micro * det_scale, 0, 1)
    edge = np.clip(edge * det_scale, 0, 1)
    dd = (1.0 - d) if inv_cc_detail else d
    cc_bias = dd * cc_detail_amp
    spec[:, :, 0] = np.clip((m0 + f * m_amp + micro * m_mic + edge * m_ed) * sm * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((r0 + (1.0 - f) * r_amp + micro * r_mic - edge * r_ed) * mask + 90 * (1 - mask), 12, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((cc0 + f * cc_amp + micro * cc_mic + edge * cc_ed + cc_bias) * mask, 16, 255).astype(np.uint8)
    return spec


def _spec_atmo(shape, mask, seed, sm, feat, det, m0, r0, cc0, m_amp, r_amp, cc_amp, finish_id):
    kw = dict(_NEUTRAL_SPEC_KW)
    kw.update(_ATM_FINISH_KW.get(finish_id, {}))
    return _finish_spec(
        shape, mask, feat, det, m0, r0, cc0, m_amp, r_amp, cc_amp, sm, seed=seed, **kw
    )


@_memo_fields
def _acid_fields(shape, seed):
    x, y = _xy(shape)
    rain = _ridge(np.sin((x * 46.0 + y * 7.0 + _waves(shape, seed, 1, 2.0) * 1.7) * np.pi), 0.18)
    streak = _ridge(np.sin((y * 118.0 + x * 4.0 + _waves(shape, seed, 3, 2.35) * 2.8) * np.pi), 0.024)
    pits = (_hash(shape, seed, 2) > 0.965).astype(np.float32)
    stain = np.clip(rain * 0.68 + pits + streak * 0.26, 0, 1)
    return stain, pits


def spec_owner_acid_rain(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    stain, pits = _acid_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, stain, pits, 26, 58, 18, 66, 124, 14, "acid_rain")


def paint_owner_acid_rain(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    stain, pits = _acid_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.22, 0.38, 0.10), 0.66 * stain + 0.25 * pits, mask, pm)
    out[:, :, 0] = np.clip(out[:, :, 0] + pits * 0.40 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + stain * 0.38 * pm * mask, 0, 1)
    out = np.clip(out - stain[:, :, None] * 0.16 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.05).astype(np.float32))


@_memo_fields
def _black_ice_fields(shape, seed):
    x, y = _xy(shape)
    frost = _ridge(np.sin((x * 64.0 - y * 39.0 + _waves(shape, seed, 10, 1.4) * 1.2) * np.pi), 0.10)
    hair = _ridge(np.sin((x * 227.0 + y * 181.0 + _waves(shape, seed, 12, 3.1) * 2.5) * np.pi), 0.030)
    chips = (_hash(shape, seed, 13) > 0.992).astype(np.float32)
    glaze = _waves(shape, seed, 11, 0.6)
    return np.clip(frost * 0.72 + glaze * 0.24 + hair * 0.38 + chips * 0.45, 0, 1), np.clip(frost + hair * 0.70 + chips, 0, 1)


def spec_owner_black_ice(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    glaze, frost = _black_ice_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, glaze, frost, 18, 10, 20, 54, 90, 18, "black_ice")


def paint_owner_black_ice(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    glaze, frost = _black_ice_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.015, 0.025, 0.050), 0.82, mask, pm)
    out[:, :, 1] = np.clip(out[:, :, 1] + glaze * 0.10 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + (glaze * 0.20 + frost * 0.18) * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.16).astype(np.float32))


@_memo_fields
def _blizzard_fields(shape, seed):
    x, y = _xy(shape)
    gust = _waves(shape, seed, 19, 1.45)
    curtain = _ridge(np.sin((y * 92.0 + x * 13.0 + gust * 2.0) * np.pi), 0.16)
    shear = _ridge(np.sin((y * 48.0 - x * 76.0 + gust * 3.3) * np.pi), 0.09)
    crystals = _ridge(np.sin((x * 139.0 - y * 121.0) * np.pi), 0.055)
    return np.clip(curtain * 0.62 + shear * 0.38 + crystals * 0.62, 0, 1), np.clip(crystals + shear * 0.55, 0, 1)


def spec_owner_blizzard(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    snow, crystals = _blizzard_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, snow, crystals, 42, 42, 24, 46, 74, 8, "blizzard")


def paint_owner_blizzard(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    snow, crystals = _blizzard_fields(shape, seed)
    base = _paint_base(paint)
    out = _mix(base, (0.82, 0.91, 1.0), 0.48 + snow * 0.46, mask, pm)
    out = np.clip(out + crystals[:, :, None] * 0.18 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.04).astype(np.float32))


@_memo_fields
def _mirage_fields(shape, seed):
    x, y = _xy(shape)
    shimmer = np.sin((y * 42.0 + _waves(shape, seed, 30, 1.5) * 4.0) * np.pi) * 0.5 + 0.5
    horizon = np.clip(1.0 - np.abs(y - 0.55) * 4.0, 0, 1)
    hair = _ridge(np.sin((y * 196.0 + x * 23.0 + shimmer * 4.0) * np.pi), 0.030) * np.clip(horizon + 0.18, 0, 1)
    glints = (_hash(shape, seed, 32) > 0.994).astype(np.float32) * np.clip(horizon + 0.08, 0, 1)
    return np.clip(shimmer * 0.48 + horizon * 0.58 + hair * 0.60 + glints * 0.40, 0, 1), np.clip(shimmer * 0.55 + hair + glints, 0, 1)


def spec_owner_desert_mirage(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    heat, shimmer = _mirage_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, heat, shimmer, 54, 34, 22, 110, 84, 26, "desert_mirage")


def paint_owner_desert_mirage(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    heat, shimmer = _mirage_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.86, 0.58, 0.25), 0.46 + heat * 0.30, mask, pm)
    out[:, :, 2] = np.clip(out[:, :, 2] + shimmer * 0.13 * pm * mask, 0, 1)
    out = np.clip(out + (shimmer[:, :, None] - 0.5) * np.array([0.16, 0.07, 0.20], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.07).astype(np.float32))


@_memo_fields
def _dew_fields(shape, seed):
    cells = max(120, int(min(shape) / 3.4))
    beads, rims, _ = _cell_droplets(shape, seed, 40, cells, 0.42, 0.12, 0.28)
    micro = (_hash(shape, seed, 41) > 0.996).astype(np.float32)
    sparkle = np.clip(rims * 0.90 + micro, 0, 1)
    return np.clip(beads * 0.56 + sparkle * 0.86, 0, 1), sparkle


def spec_owner_dew_drop(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    beads, sparkle = _dew_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, beads, sparkle, 36, 12, 24, 96, 86, 18, "dew_drop")


def paint_owner_dew_drop(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    beads, sparkle = _dew_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.20, 0.50, 0.48), 0.24, mask, pm)
    out = np.clip(out + beads[:, :, None] * np.array([0.08, 0.20, 0.18], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    out = np.clip(out + sparkle[:, :, None] * 0.44 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.12).astype(np.float32))


@_memo_fields
def _dust_fields(shape, seed):
    x, y = _xy(shape)
    wind = _ridge(np.sin((x * 34.0 + y * 74.0 + _waves(shape, seed, 50, 1.0) * 2.0) * np.pi), 0.18)
    grit = _hash(shape, seed, 51)
    return np.clip(wind * 0.75 + (grit > 0.90) * 0.45, 0, 1), grit


def spec_owner_dust_storm(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    wind, grit = _dust_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, wind, grit, 18, 118, 42, 42, 72, 10, "dust_storm")


def paint_owner_dust_storm(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    wind, grit = _dust_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.70, 0.53, 0.30), 0.60 + wind * 0.22, mask, pm)
    out = np.clip(out + (grit[:, :, None] - 0.5) * 0.16 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.03).astype(np.float32))


@_memo_fields
def _ember_fields(shape, seed):
    cracks = _ridge(np.sin((_waves(shape, seed, 60, 2.5) * 9.0 + _waves(shape, seed, 61, 5.0) * 3.0) * np.pi), 0.12)
    ash = _waves(shape, seed, 62, 0.8)
    return cracks, ash


def spec_owner_ember_glow(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    cracks, ash = _ember_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, cracks, ash, 44, 96, 18, 144, 106, 16, "ember_glow")


def paint_owner_ember_glow(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    cracks, ash = _ember_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.055, 0.038, 0.030), 0.78, mask, pm)
    out[:, :, 0] = np.clip(out[:, :, 0] + cracks * 0.88 * pm * mask + ash * 0.10 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + cracks * 0.30 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.05).astype(np.float32))


def _fog_bank_paint(shape, seed):
    """Rolling valley / waterway fog: coverage advances upward, soft billows (paint layer)."""
    x, y = _xy(shape)
    ph = _seed(seed, 70) * (np.pi * 2.0)
    valley = _waves(shape, seed, 70, 0.88)
    # Front advances from bottom; sidewall bias so it reads like fog off terrain or water.
    sidewall = np.sin((x * (2.8 + _seed(seed, 71) * 1.6) + ph) * np.pi) * 0.11
    advance = np.clip((y - 0.12) * 1.52 + valley * 0.42 + sidewall, 0, 1)
    advance = np.power(np.clip(advance, 0, 1), 1.10)
    billow = _ridge(np.sin((x * 24.0 + y * 16.0 + valley * 4.5) * np.pi), 0.13)
    wisps = _ridge(np.sin((x * 58.0 - y * 21.0 + _waves(shape, seed, 72, 1.65) * 2.9) * np.pi), 0.085)
    mist = _smooth_noise(shape, seed, 73, cells=22) * 0.46
    fine = _ridge(np.sin((x * 132.0 + y * 91.0 + _waves(shape, seed, 78, 2.4) * 4.0) * np.pi), 0.022)
    curl = _ridge(np.sin((x * 96.0 - y * 88.0 + valley * 2.2) * np.pi), 0.018)
    coverage = np.clip(
        advance * 0.62 + billow * 0.32 + wisps * 0.24 + mist * 0.24 + fine * 0.30 + curl * 0.14,
        0,
        1,
    )
    return coverage, np.clip(wisps * 0.75 + billow * 0.55 + fine * 0.40, 0, 1)


def _fog_bank_spec(shape, seed):
    """Spec uses different cues: micro-droplet scatter + depth ramp (not a copy of paint coverage)."""
    x, y = _xy(shape)
    hr = _hash(shape, seed, 74)
    micro = _ridge(np.sin((x * 168.0 + y * 104.0 + _waves(shape, seed, 75, 3.1) * 5.2) * np.pi), 0.028)
    depth = np.clip(y * 1.08 + _smooth_noise(shape, seed, 76, cells=32) * 0.44 - 0.10, 0, 1)
    scatter = np.clip(hr * 0.22 + micro * 0.92, 0, 1)
    shelf = _ridge(np.sin((depth * 12.0 + x * 8.8 + _waves(shape, seed, 77, 2.0) * 3.0) * np.pi), 0.048)
    return np.clip(scatter * 0.58 + shelf * 0.62 + depth * 0.28, 0, 1), np.clip(micro * 0.85 + shelf * 0.78 + depth * 0.50, 0, 1)


def spec_owner_fog_bank(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    feat, det = _fog_bank_spec(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, feat, det, 14, 72, 18, 34, 74, 8, "fog_bank")


def paint_owner_fog_bank(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    veil, wisps = _fog_bank_paint(shape, seed)
    cool = (0.62, 0.70, 0.78)
    damp = (0.52, 0.58, 0.62)
    out = _mix(_paint_base(paint), cool, 0.28 + veil * 0.52, mask, pm)
    out = _mix(out, damp, veil * veil * 0.22, mask, pm)
    out = np.clip(out + wisps[:, :, None] * np.array([0.06, 0.07, 0.08], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    out = np.clip(out - (1.0 - veil)[:, :, None] * np.array([0.02, 0.025, 0.03], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    # Break up macro-only luma so workbench residual/macro ratio passes without losing fog mass.
    speck = _hash(shape, seed, 81).astype(np.float32)
    out = np.clip(out + (speck - 0.5)[:, :, None] * 0.062 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.06).astype(np.float32))


@_memo_fields
def _frost_fields(shape, seed):
    x, y = _xy(shape)
    dendrite = _ridge(np.sin((x * 94.0 - y * 86.0 + _waves(shape, seed, 80, 3.2) * 4.0) * np.pi), 0.075)
    needles = _ridge(np.sin((x * 171.0 + y * 37.0) * np.pi), 0.04)
    splinters = _ridge(np.sin((x * 263.0 - y * 214.0 + _waves(shape, seed, 82, 5.0) * 3.0) * np.pi), 0.026)
    glitter = (_hash(shape, seed, 83) > 0.994).astype(np.float32)
    return np.clip(dendrite + needles * 0.42 + splinters * 0.46 + glitter * 0.58, 0, 1), np.clip(needles + splinters + glitter, 0, 1)


def spec_owner_frost_bite(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    frost, needles = _frost_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, frost, needles, 46, 18, 24, 74, 54, 18, "frost_bite")


def paint_owner_frost_bite(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    frost, needles = _frost_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.28, 0.78, 0.96), 0.36 + frost * 0.28, mask, pm)
    out = np.clip(out + needles[:, :, None] * 0.18 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.08).astype(np.float32))


@_memo_fields
def _frozen_lake_fields(shape, seed):
    x, y = _xy(shape)
    warp = _waves(shape, seed, 90, 2.6)
    major = _ridge(np.sin((x * 7.0 + y * 11.0 + warp * 4.0) * np.pi), 0.040)
    cross = _ridge(np.sin((x * 31.0 - y * 27.0 + warp * 2.0) * np.pi), 0.028)
    trapped, rims, _ = _cell_droplets(shape, seed, 92, max(72, int(min(shape) / 8.0)), 0.30, 0.10, 0.24)
    cracks = np.clip(major + cross * 0.58, 0, 1)
    bubbles = np.clip(trapped * 0.50 + rims * 0.72, 0, 1)
    return np.clip(cracks + bubbles * 0.42, 0, 1), bubbles


def spec_owner_frozen_lake(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    crack, bubbles = _frozen_lake_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, crack, bubbles, 30, 8, 36, 92, 56, 30, "frozen_lake")


def paint_owner_frozen_lake(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    crack, bubbles = _frozen_lake_fields(shape, seed)
    x, y = _xy(shape)
    depth = np.clip(0.18 + y * 0.46, 0, 1)
    out = _mix(_paint_base(paint), (0.08, 0.34, 0.56), 0.66, mask, pm)
    out[:, :, 2] = np.clip(out[:, :, 2] + depth * 0.26 * pm * mask, 0, 1)
    out = np.clip(out + crack[:, :, None] * np.array([0.34, 0.58, 0.70], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    out = np.clip(out + bubbles[:, :, None] * 0.22 * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.14).astype(np.float32))


@_memo_fields
def _hail_fields(shape, seed):
    cells = max(46, int(min(shape) / 12.0))
    dents, rims, _ = _cell_droplets(shape, seed, 100, cells, 0.46, 0.18, 0.46)
    chips = (_hash(shape, seed, 101) > 0.991).astype(np.float32)
    crater = np.clip(rims * 0.95 + dents * 0.35 + chips * 0.70, 0, 1)
    return crater, np.clip(rims + chips, 0, 1)


def spec_owner_hail_damage(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    dents, chips = _hail_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, dents, chips, 30, 86, 18, 58, 130, 8, "hail_damage")


def paint_owner_hail_damage(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    dents, chips = _hail_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.36, 0.39, 0.42), 0.46, mask, pm)
    out = np.clip(out - dents[:, :, None] * 0.34 * pm * mask[:, :, None], 0, 1)
    out = np.clip(out + chips[:, :, None] * np.array([0.20, 0.22, 0.24], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.06).astype(np.float32))


@_memo_fields
def _heat_fields(shape, seed):
    x, y = _xy(shape)
    warp = np.sin((x * 28.0 + _waves(shape, seed, 110, 2.1) * 6.0) * np.pi) * 0.040
    horizon = np.clip(1.0 - np.abs(y - 0.50) * 3.4, 0, 1)
    shimmer = _ridge(np.sin(((y + warp) * 76.0 + x * 2.0) * np.pi), 0.070)
    mirage = _ridge(np.sin(((y + warp * 1.6) * 152.0 + _waves(shape, seed, 111, 4.0) * 3.0) * np.pi), 0.045)
    refraction = _ridge(np.sin(((y + warp * 2.2) * 255.0 - x * 19.0 + _waves(shape, seed, 112, 5.5) * 3.0) * np.pi), 0.026)
    sparks = (_hash(shape, seed, 113) > 0.993).astype(np.float32) * horizon
    return np.clip(shimmer * 0.42 + mirage * horizon * 0.74 + refraction * 0.50 + sparks * 0.38, 0, 1), np.clip(mirage * horizon + refraction + sparks, 0, 1)


def spec_owner_heat_wave(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    heat, scan = _heat_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, heat, scan, 24, 38, 18, 80, 72, 14, "heat_wave")


def paint_owner_heat_wave(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    heat, scan = _heat_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.38, 0.23, 0.13), 0.48, mask, pm)
    out[:, :, 0] = np.clip(out[:, :, 0] + heat * 0.34 * pm * mask + scan * 0.18 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + heat * 0.12 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + scan * 0.20 * pm * mask, 0, 1)
    out = np.clip(out + (scan[:, :, None] - 0.45) * np.array([0.10, 0.035, 0.14], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.07).astype(np.float32))


@_memo_fields
def _hurricane_fields(shape, seed):
    x, y = _xy(shape)
    dx = x - 0.52
    dy = y - 0.52
    r = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    bands = np.sin(theta * 4.0 + r * 74.0 + _waves(shape, seed, 120, 1.6) * 3.0) * 0.5 + 0.5
    spray = _ridge(np.sin((theta * 21.0 + r * 260.0) * np.pi), 0.11)
    rain = _ridge(np.sin((theta * 37.0 - r * 410.0 + _waves(shape, seed, 122, 4.0) * 3.0) * np.pi), 0.048)
    droplets = (_hash(shape, seed, 123) > 0.990).astype(np.float32)
    eye = np.clip(1.0 - r * 12.0, 0, 1)
    falloff = np.clip(1.0 - r * 1.55, 0, 1)
    return np.clip(bands * falloff + spray * falloff * 0.36 + rain * falloff * 0.45 + eye, 0, 1), np.clip(eye + rain * falloff + droplets * falloff, 0, 1)


def spec_owner_hurricane(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    bands, eye = _hurricane_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, bands, eye, 32, 78, 20, 94, 112, 14, "hurricane")


def paint_owner_hurricane(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    bands, spray = _hurricane_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.13, 0.20, 0.27), 0.70, mask, pm)
    out = np.clip(out + bands[:, :, None] * np.array([0.16, 0.18, 0.20], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    out = np.clip(out + spray[:, :, None] * np.array([0.22, 0.28, 0.34], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.06).astype(np.float32))


@_memo_fields
def _lightning_fields(shape, seed):
    h, w = shape
    if max(h, w) > 1024:
        scale = 1024.0 / float(max(h, w))
        small_shape = (max(8, int(round(h * scale))), max(8, int(round(w * scale))))
        strike_small, burn_small = _lightning_fields(small_shape, seed)
        strike = cv2.resize(strike_small, (w, h), interpolation=cv2.INTER_LINEAR)
        burn = cv2.resize(burn_small, (w, h), interpolation=cv2.INTER_LINEAR)
        x, y = _xy(shape)
        fork = _ridge(np.sin((x * 143.0 - y * 191.0 + _waves(shape, seed, 134, 5.0) * 4.0) * np.pi), 0.018)
        spark = (_hash(shape, seed, 135) > 0.995).astype(np.float32)
        return np.clip(strike + fork * np.clip(burn + 0.08, 0, 1) * 0.42 + spark * 0.45, 0, 1), np.clip(burn + fork * 0.20, 0, 1)
    x, y = _xy(shape)
    warp = _waves(shape, seed, 131, 3.2)
    bolt = np.zeros(shape, dtype=np.float32)
    glow = np.zeros(shape, dtype=np.float32)
    sources = (
        (0.50, 0.22, 1.04, 28.0, 52.0),
        (0.13, 0.57, 0.86, 22.0, 44.0),
        (0.88, 0.48, 0.82, 22.0, 46.0),
        (0.50, 0.74, 0.58, 16.0, 36.0),
    )
    for sidx, (cx, cy, reach, angular, radial) in enumerate(sources):
        dx = x - cx
        dy = y - cy
        r = np.sqrt(dx * dx + dy * dy) + 1e-6
        theta = np.arctan2(dy, dx)
        phase = _seed(seed, 130 + sidx * 19) * np.pi * 2.0
        bend = np.sin(r * 18.0 + warp * 5.0 + phase) * 0.55
        fan = _ridge(np.sin(theta * angular + r * radial + bend + phase), 0.095)
        hair = _ridge(np.sin(theta * angular * 2.15 - r * radial * 0.72 + warp * 6.0 + phase * 1.7), 0.052)
        fork_texture = _ridge(np.sin((dx * 78.0 - dy * 94.0 + warp * 4.0 + phase) * np.pi), 0.018)
        falloff = np.clip(1.0 - r / reach, 0, 1)
        source = np.clip((fan * 0.72 + hair * 0.62 + fork_texture * 0.22) * falloff, 0, 1)
        bolt = np.maximum(bolt, source)
        glow = np.maximum(glow, np.clip((fan * 0.46 + hair * 0.26) * np.clip(1.0 - r / (reach * 0.70), 0, 1), 0, 1))
    fork_texture = _ridge(np.sin((x * 94.0 - y * 127.0 + _waves(shape, seed, 132, 4.0) * 4.0) * np.pi), 0.016)
    spark = (_hash(shape, seed, 133) > 0.994).astype(np.float32)
    strike = np.clip(np.power(bolt, 0.72) + fork_texture * glow * 0.34 + spark * np.clip(glow + 0.10, 0, 1), 0, 1)
    burn = np.clip(glow * 0.85 + fork_texture * strike * 0.18, 0, 1)
    return strike, burn


def spec_owner_lightning_strike(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    bolt, burn = _lightning_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, bolt, burn, 26, 86, 18, 206, 138, 20, "lightning_strike")


def paint_owner_lightning_strike(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    bolt, burn = _lightning_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.006, 0.008, 0.014), 0.90, mask, pm)
    out = np.clip(out - burn[:, :, None] * 0.16 * pm * mask[:, :, None], 0, 1)
    out[:, :, 0] = np.clip(out[:, :, 0] + bolt * 0.95 * pm * mask + burn * 0.12 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + bolt * 1.00 * pm * mask + burn * 0.22 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + bolt * 1.00 * pm * mask + burn * 0.42 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.04).astype(np.float32))


@_memo_fields
def _liquid_metal_fields(shape, seed):
    x, y = _xy(shape)
    flow = _waves(shape, seed, 140, 2.0)
    ripples = np.sin((x * 24.0 + flow * 5.0 + y * 6.0) * np.pi) * 0.5 + 0.5
    machining = _ridge(np.sin((x * 172.0 + y * 64.0 + flow * 8.0) * np.pi), 0.030)
    beads = (_hash(shape, seed, 142) > 0.994).astype(np.float32)
    return np.clip(flow * 0.56 + ripples * 0.34 + machining * 0.58 + beads * 0.34, 0, 1), np.clip(ripples * 0.42 + machining + beads, 0, 1)


def spec_owner_liquid_metal(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    flow, ripples = _liquid_metal_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, flow, ripples, 168, 7, 18, 78, 46, 10, "liquid_metal")


def paint_owner_liquid_metal(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    flow, ripples = _liquid_metal_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.55, 0.58, 0.62), 0.86, mask, pm)
    out = np.clip(out + flow[:, :, None] * 0.30 * pm * mask[:, :, None] - ripples[:, :, None] * 0.16 * pm * mask[:, :, None], 0, 1)
    out = np.clip(out + (ripples[:, :, None] - 0.45) * np.array([0.08, 0.09, 0.10], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.20).astype(np.float32))


@_memo_fields
def _oil_slick_fields(shape, seed):
    x, y = _xy(shape)
    flow = _waves(shape, seed, 145, 2.6)
    film = np.sin((x * 19.0 - y * 13.0 + flow * 6.5) * np.pi) * 0.5 + 0.5
    eddies = _ridge(np.sin((_waves(shape, seed, 146, 5.2) * 18.0 + x * 4.0 - y * 5.0) * np.pi), 0.070)
    bead = (_hash(shape, seed, 147) > 0.990).astype(np.float32)
    return np.clip(film * 0.58 + eddies * 0.56 + bead * 0.36, 0, 1), np.clip(eddies + bead, 0, 1)


def spec_owner_oil_slick(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    film, eddies = _oil_slick_fields(shape, seed)
    live = _living_field(shape, seed, 1488)
    film = np.clip(film * 0.90 + live * 0.10, 0, 1)
    # Wet pearl film with metallic edge flashes, not an all-chrome wash.
    spec = _rgba(shape, mask)
    edge = np.clip(np.abs(film - np.roll(film, 1, axis=1)) + np.abs(eddies - np.roll(eddies, 1, axis=0)), 0, 1)
    spec[:, :, 0] = np.clip((24 + film * 42 + eddies * 68 + edge * 92) * sm * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((42 + (1.0 - film) * 76 + eddies * 18 - edge * 34) * mask + 90 * (1 - mask), 10, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((42 + film * 116 + eddies * 72 + edge * 58) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_oil_slick(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    film, eddies = _oil_slick_fields(shape, seed)
    phase = np.clip(film, 0, 1)
    c1 = np.dstack([
        0.05 + phase * 0.34,
        0.06 + np.sin(phase * np.pi) * 0.28,
        0.10 + (1.0 - phase) * 0.46,
    ]).astype(np.float32)
    out = _mix(_paint_base(paint), (0.012, 0.014, 0.018), 0.72, mask, pm)
    out = np.clip(out * (1.0 - 0.58 * mask[:, :, None] * pm) + c1 * (0.58 + eddies[:, :, None] * 0.24) * mask[:, :, None] * pm, 0, 1)
    out = np.clip(out + eddies[:, :, None] * np.array([0.18, 0.12, 0.28], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.11).astype(np.float32))


@_memo_fields
def _magma_fields(shape, seed):
    h, w = shape
    terrain = (
        _smooth_noise(shape, seed, 150, max(8, int(min(h, w) / 96))) * 0.54
        + _smooth_noise(shape, seed, 151, max(14, int(min(h, w) / 48))) * 0.34
        + _smooth_noise(shape, seed, 152, max(24, int(min(h, w) / 28))) * 0.12
    )
    terrain = np.clip(terrain, 0, 1)
    frac = terrain * 7.5
    frac = frac - np.floor(frac)
    dist = np.minimum(frac, 1.0 - frac)
    lava = np.clip(1.0 - dist / 0.075, 0, 1)
    heat = np.clip(1.0 - dist / 0.185, 0, 1)
    flakes = ((_hash(shape, seed, 153) > 0.990).astype(np.float32) * np.clip(lava + 0.10, 0, 1))
    return np.clip(lava, 0, 1), np.clip(heat + flakes, 0, 1)


def spec_owner_magma_flow(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    lava, heat = _magma_fields(shape, seed)
    live = _living_field(shape, seed, 1537)
    lava = np.clip(lava * (0.86 + live * 0.18), 0, 1)
    heat = np.clip(heat * (0.90 + live * 0.12), 0, 1)
    hot_flakes = ((_hash(shape, seed, 153) > 0.982).astype(np.float32) * np.clip(lava + heat * 0.30, 0, 1))
    chrome = ((_hash(shape, seed, 154) > 0.55).astype(np.float32) * hot_flakes)
    metallic = np.clip(hot_flakes - chrome, 0, 1)
    spec = _rgba(shape, mask)
    spec[:, :, 0] = np.clip((12 + lava * 106 + hot_flakes * 176) * sm * mask, 0, 255).astype(np.uint8)
    rough = 132 - lava * 46 - chrome * 118 - metallic * 72
    spec[:, :, 1] = np.clip(rough * mask + 90 * (1 - mask), 3, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((16 + lava * 20 + chrome * 58 + metallic * 34) * mask, 16, 255).astype(np.uint8)
    return spec


def paint_owner_magma_flow(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    lava, heat = _magma_fields(shape, seed)
    crust = np.clip(1.0 - lava * 0.82, 0, 1)
    out = _mix(_paint_base(paint), (0.018, 0.021, 0.019), 0.94, mask, pm)
    out = np.clip(out + crust[:, :, None] * np.array([0.020, 0.026, 0.020], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    out[:, :, 0] = np.clip(out[:, :, 0] + lava * 1.00 * pm * mask + heat * 0.96 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + lava * 0.48 * pm * mask + heat * 0.30 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + lava * 0.035 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.04).astype(np.float32))


@_memo_fields
def _meteor_fields(shape, seed):
    x, y = _xy(shape)
    trails = _ridge((x + y * 0.62 + _waves(shape, seed, 160, 1.2) * 0.16) % 0.20 - 0.10, 0.012)
    stars = (_hash(shape, seed, 161) > 0.994).astype(np.float32)
    return np.clip(trails + stars, 0, 1), stars


def spec_owner_meteor_shower(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    trails, stars = _meteor_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, trails, stars, 22, 150, 18, 196, 138, 16, "meteor_shower")


def paint_owner_meteor_shower(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    trails, stars = _meteor_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.025, 0.030, 0.070), 0.84, mask, pm)
    out[:, :, 0] = np.clip(out[:, :, 0] + trails * 0.90 * pm * mask + stars * 0.45 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + trails * 0.58 * pm * mask + stars * 0.45 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + trails * 0.30 * pm * mask + stars * 0.45 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.03).astype(np.float32))


@_memo_fields
def _monsoon_fields(shape, seed):
    x, y = _xy(shape)
    sheets = _ridge(np.sin((x * 18.0 + y * 155.0 + _waves(shape, seed, 170, 1.1) * 2.5) * np.pi), 0.12)
    flood = np.clip(y * 0.55 + _waves(shape, seed, 171, 0.6) * 0.45, 0, 1)
    slant = _ridge(np.sin(((x * 1.15 + y) * 88.0 + _waves(shape, seed, 172, 2.2) * 3.0) * np.pi), 0.045)
    splash = (_hash(shape, seed, 173) > 0.991).astype(np.float32)
    return np.clip(sheets * 0.68 + flood * 0.38 + slant * 0.36 + splash * 0.30, 0, 1), np.clip(sheets * 0.85 + slant + splash, 0, 1)


def spec_owner_monsoon(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    rain, sheets = _monsoon_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, rain, sheets, 30, 58, 24, 84, 82, 18, "monsoon")


def paint_owner_monsoon(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    rain, sheets = _monsoon_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.08, 0.24, 0.38), 0.66, mask, pm)
    out = np.clip(out + sheets[:, :, None] * 0.20 * pm * mask[:, :, None] + rain[:, :, None] * np.array([0.00, 0.08, 0.16], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.10).astype(np.float32))


@_memo_fields
def _ocean_fields(shape, seed):
    caustic = _ridge(np.sin((_waves(shape, seed, 180, 4.0) * 16.0) * np.pi), 0.09)
    bio = (_hash(shape, seed, 181) > 0.989).astype(np.float32)
    return np.clip(caustic + bio * 0.80, 0, 1), bio


def spec_owner_ocean_floor(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    caustic, bio = _ocean_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, caustic, bio, 26, 92, 20, 86, 76, 14, "ocean_floor")


def paint_owner_ocean_floor(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    caustic, bio = _ocean_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.015, 0.075, 0.180), 0.84, mask, pm)
    out[:, :, 1] = np.clip(out[:, :, 1] + caustic * 0.24 * pm * mask + bio * 0.70 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + caustic * 0.34 * pm * mask + bio * 0.52 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.07).astype(np.float32))


@_memo_fields
def _permafrost_fields(shape, seed):
    x, y = _xy(shape)
    block = _block_noise(shape, seed, 190, 48)
    plate_a = _ridge(np.sin((x * 72.0 - y * 88.0 + block * 4.0) * np.pi), 0.075)
    plate_b = _ridge(np.sin((x * 27.0 + y * 53.0 + block * 2.5) * np.pi), 0.090)
    hair = _ridge(np.sin((x * 188.0 + y * 161.0 + block * 6.0) * np.pi), 0.028)
    plates = np.clip(plate_a + plate_b * 0.65, 0, 1)
    trapped = np.clip((_block_noise(shape, seed, 192, 88) - 0.78) * 4.5, 0, 1)
    return np.clip(plates * 0.82 + hair * 0.58 + trapped * 0.40, 0, 1), np.clip(trapped + hair, 0, 1)


def spec_owner_permafrost(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    plates, trapped = _permafrost_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, plates, trapped, 36, 18, 20, 70, 44, 12, "permafrost")


def paint_owner_permafrost(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    plates, trapped = _permafrost_fields(shape, seed)
    grain = (_hash(shape, seed, 193) - 0.5).astype(np.float32)
    out = _mix(_paint_base(paint), (0.50, 0.76, 0.91), 0.54, mask, pm)
    out = np.clip(out + plates[:, :, None] * 0.18 * pm * mask[:, :, None] - trapped[:, :, None] * 0.11 * pm * mask[:, :, None], 0, 1)
    out = np.clip(out + (trapped[:, :, None] - 0.35) * np.array([0.08, 0.12, 0.16], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    out = np.clip(out + grain[:, :, None] * np.array([0.045, 0.060, 0.075], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.11).astype(np.float32))


@_memo_fields
def _solar_fields(shape, seed):
    # OWNER KEEPER LOGIC (2026-04-27): Solar Wind was called
    # "LEGITIMATELY BEAUTIFUL". Preserve its dark-space carrier, aurora-like
    # ribbon flow, and sparse particle glitter. Do not clone this exact logic
    # into other finishes.
    x, y = _xy(shape)
    ribbons = _ridge(np.sin((y * 18.0 + _waves(shape, seed, 200, 2.2) * 5.0 + x * 3.0) * np.pi), 0.16)
    particles = (_hash(shape, seed, 201) > 0.985).astype(np.float32)
    return np.clip(ribbons + particles * 0.50, 0, 1), particles


def spec_owner_solar_wind(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    ribbons, particles = _solar_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, ribbons, particles, 96, 22, 22, 116, 66, 18, "solar_wind")


def paint_owner_solar_wind(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    ribbons, particles = _solar_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.035, 0.045, 0.075), 0.72, mask, pm)
    out[:, :, 0] = np.clip(out[:, :, 0] + ribbons * 0.86 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + ribbons * 0.72 * pm * mask + particles * 0.38 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + ribbons * 0.22 * pm * mask + particles * 0.62 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.05).astype(np.float32))


@_memo_fields
def _tidal_fields(shape, seed):
    x, y = _xy(shape)
    warp = _waves(shape, seed, 210, 1.8)
    crest_y = 0.48 + np.sin((x * 2.2 + _seed(seed, 211)) * np.pi) * 0.10 + warp * 0.10
    face = np.clip((y - crest_y + 0.34) / 0.42, 0, 1)
    curl = _ridge(y - (crest_y + 0.045 * np.sin(x * 18.0 * np.pi)), 0.032)
    foam_lines = _ridge(np.sin((x * 74.0 + y * 28.0 + warp * 6.0) * np.pi), 0.080) * face
    hairfoam = _ridge(np.sin((x * 188.0 - y * 92.0 + warp * 9.0) * np.pi), 0.034) * face
    spray = (_hash(shape, seed, 212) > 0.986).astype(np.float32) * np.clip(1.0 - y * 1.6, 0, 1)
    foam = np.clip(curl + foam_lines * 0.58 + hairfoam * 0.72 + spray, 0, 1)
    wave = np.clip(face * 0.58 + curl * 0.50 + hairfoam * 0.42, 0, 1)
    return wave, foam


def spec_owner_tidal_wave(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    surge, foam = _tidal_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, surge, foam, 38, 20, 28, 94, 48, 28, "tidal_wave")


def paint_owner_tidal_wave(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    surge, foam = _tidal_fields(shape, seed)
    x, y = _xy(shape)
    depth = np.clip(y * 0.55 + 0.18, 0, 1)
    out = _mix(_paint_base(paint), (0.005, 0.075, 0.22), 0.88, mask, pm)
    out[:, :, 1] = np.clip(out[:, :, 1] + surge * 0.30 * pm * mask + foam * 0.42 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + surge * 0.44 * pm * mask + foam * 0.48 * pm * mask - depth * 0.10 * pm * mask, 0, 1)
    out[:, :, 0] = np.clip(out[:, :, 0] + foam * 0.46 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.08).astype(np.float32))


@_memo_fields
def _tornado_fields(shape, seed):
    x, y = _xy(shape)
    dx = x - 0.50
    dy = y - 0.58
    r = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    funnel = np.clip(1.0 - r * 2.2, 0, 1)
    spiral = np.sin(theta * 5.0 + r * 88.0 + _waves(shape, seed, 220, 2.0) * 2.0) * 0.5 + 0.5
    debris = (_hash(shape, seed, 221) > 0.982).astype(np.float32)
    return np.clip(funnel * spiral + debris * 0.35, 0, 1), debris


def spec_owner_tornado_alley(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    funnel, debris = _tornado_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, funnel, debris, 28, 98, 18, 90, 106, 12, "tornado_alley")


def paint_owner_tornado_alley(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    funnel, debris = _tornado_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.20, 0.22, 0.21), 0.72, mask, pm)
    out = np.clip(out - funnel[:, :, None] * 0.20 * pm * mask[:, :, None] + debris[:, :, None] * 0.24 * pm * mask[:, :, None], 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + (1.0 - funnel) * 0.08 * pm * mask, 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.05).astype(np.float32))


@_memo_fields
def _volcanic_glass_fields(shape, seed):
    # OWNER KEEPER LOGIC (2026-04-27): Volcanic Glass produced an A+++ hue /
    # brightness responsive color-shift-under-glass effect. Preserve the black
    # glass carrier, fracture/sheen split, and high-clearcoat/chrome read.
    # Future finishes may learn from this, but should not repeat the function.
    fracture = _ridge(np.sin((_waves(shape, seed, 230, 4.0) * 10.0 + _waves(shape, seed, 231, 7.0) * 3.0) * np.pi), 0.08)
    splinter = _ridge(np.sin((_waves(shape, seed, 233, 7.0) * 28.0 + _waves(shape, seed, 234, 11.0) * 7.0) * np.pi), 0.035)
    obsidian_dust = (_hash(shape, seed, 235) > 0.994).astype(np.float32)
    sheen = _waves(shape, seed, 232, 1.1)
    return np.clip(fracture * 0.82 + splinter * 0.62 + obsidian_dust * 0.45, 0, 1), np.clip(sheen * 0.72 + splinter + obsidian_dust, 0, 1)


def spec_owner_volcanic_glass(shape, mask, seed, sm):
    mask = _mask(mask, shape)
    fracture, sheen = _volcanic_glass_fields(shape, seed)
    return _spec_atmo(shape, mask, seed, sm, fracture, sheen, 172, 6, 18, 72, 30, 12, "volcanic_glass")


def paint_owner_volcanic_glass(paint, shape, mask, seed, pm, bb):
    mask = _mask(mask, shape)
    fracture, sheen = _volcanic_glass_fields(shape, seed)
    out = _mix(_paint_base(paint), (0.018, 0.012, 0.014), 0.90, mask, pm)
    out[:, :, 0] = np.clip(out[:, :, 0] + fracture * 0.58 * pm * mask + sheen * 0.06 * pm * mask, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + fracture * 0.14 * pm * mask, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + sheen * 0.10 * pm * mask, 0, 1)
    out = np.clip(out + (sheen[:, :, None] - 0.40) * np.array([0.10, 0.035, 0.055], dtype=np.float32) * pm * mask[:, :, None], 0, 1)
    return np.ascontiguousarray(_bb(out, mask, bb, 0.16).astype(np.float32))


OWNER_REVIEW_ATMOSPHERE_MONOLITHICS = {
    "acid_rain": (spec_owner_acid_rain, paint_owner_acid_rain),
    "black_ice": (spec_owner_black_ice, paint_owner_black_ice),
    "blizzard": (spec_owner_blizzard, paint_owner_blizzard),
    "desert_mirage": (spec_owner_desert_mirage, paint_owner_desert_mirage),
    "dew_drop": (spec_owner_dew_drop, paint_owner_dew_drop),
    "dust_storm": (spec_owner_dust_storm, paint_owner_dust_storm),
    "ember_glow": (spec_owner_ember_glow, paint_owner_ember_glow),
    "fog_bank": (spec_owner_fog_bank, paint_owner_fog_bank),
    "frost_bite": (spec_owner_frost_bite, paint_owner_frost_bite),
    "frozen_lake": (spec_owner_frozen_lake, paint_owner_frozen_lake),
    "hail_damage": (spec_owner_hail_damage, paint_owner_hail_damage),
    "heat_wave": (spec_owner_heat_wave, paint_owner_heat_wave),
    "hurricane": (spec_owner_hurricane, paint_owner_hurricane),
    "lightning_strike": (spec_owner_lightning_strike, paint_owner_lightning_strike),
    "liquid_metal": (spec_owner_liquid_metal, paint_owner_liquid_metal),
    "magma_flow": (spec_owner_magma_flow, paint_owner_magma_flow),
    "meteor_shower": (spec_owner_meteor_shower, paint_owner_meteor_shower),
    "monsoon": (spec_owner_monsoon, paint_owner_monsoon),
    "ocean_floor": (spec_owner_ocean_floor, paint_owner_ocean_floor),
    "oil_slick": (spec_owner_oil_slick, paint_owner_oil_slick),
    "permafrost": (spec_owner_permafrost, paint_owner_permafrost),
    "solar_wind": (spec_owner_solar_wind, paint_owner_solar_wind),
    "tidal_wave": (spec_owner_tidal_wave, paint_owner_tidal_wave),
    "tornado_alley": (spec_owner_tornado_alley, paint_owner_tornado_alley),
    "volcanic_glass": (spec_owner_volcanic_glass, paint_owner_volcanic_glass),
}
