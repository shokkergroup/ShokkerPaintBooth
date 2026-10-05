"""Owner-review Weathered & Aged source renderers for SPB-30."""

from __future__ import annotations

import numpy as np

from engine.core import hsv_to_rgb_vec


_FIELDS_CACHE: dict[tuple[tuple[int, int], int, int], tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}


def _xy(shape):
    h, w = shape[:2] if len(shape) > 2 else shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _bb(bb, shape):
    h, w = shape[:2] if len(shape) > 2 else shape
    if bb is None:
        return np.zeros((h, w), dtype=np.float32)
    arr = np.asarray(bb, dtype=np.float32)
    if arr.ndim == 0:
        return np.full((h, w), float(arr), dtype=np.float32)
    if arr.ndim == 3:
        return arr[:h, :w, :3].mean(axis=2).astype(np.float32)
    return arr[:h, :w].astype(np.float32)


def _norm(arr):
    arr = np.asarray(arr, dtype=np.float32)
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def _edge(arr):
    gy, gx = np.gradient(np.asarray(arr, dtype=np.float32))
    return _norm(np.sqrt(gx * gx + gy * gy))


def _hash(shape, seed, salt):
    x, y = _xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + (int(seed) + salt) * 0.193) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _hsv(h, s, v):
    h, s, v = np.broadcast_arrays(h, s, v)
    r, g, b = hsv_to_rgb_vec(np.mod(h, 1.0).astype(np.float32), np.clip(s, 0, 1).astype(np.float32), np.clip(v, 0, 1).astype(np.float32))
    return np.stack([r, g, b], axis=2).astype(np.float32)


def _waves(shape, seed, cfg):
    x, y = _xy(shape)
    phase = ((int(seed) + cfg["salt"]) % 4096) * 0.019
    f = cfg["freq"]
    return (
        np.sin((x * f + y * f * 0.31 + phase) * np.pi) * 0.42
        + np.sin((x * f * 0.47 - y * f * 0.86 + phase * 1.7) * np.pi) * 0.31
        + np.sin((x * f * 1.73 + y * f * 1.19 + phase * 0.6) * np.pi) * 0.19
        + np.sin((x * f * 3.41 - y * f * 2.63 + phase * 2.2) * np.pi) * 0.08
    ).astype(np.float32)


def _cracks(shape, seed, cfg):
    x, y = _xy(shape)
    phase = ((int(seed) + cfg["salt"]) % 991) * 0.023
    f = cfg["freq"]
    a = np.abs(np.sin((x * f + y * f * 0.27 + phase) * np.pi))
    b = np.abs(np.sin((x * -f * 0.36 + y * f * 0.93 + phase * 1.3) * np.pi))
    c = np.abs(np.sin((x * f * 0.79 - y * f * 0.64 + phase * 0.7) * np.pi))
    return np.clip(1.0 - np.minimum(np.minimum(a, b), c) * cfg.get("crack_width", 24.0), 0, 1).astype(np.float32)


def _fields(shape, seed, cfg):
    key = ((int(shape[0]), int(shape[1])), int(seed), int(cfg["salt"]))
    cached = _FIELDS_CACHE.get(key)
    if cached is not None:
        return tuple(part.copy() for part in cached)
    x, y = _xy(shape)
    noise = _hash(shape, seed, cfg["salt"])
    flow = _norm(_waves(shape, seed, cfg))
    crack = _cracks(shape, seed, cfg)
    pits = (noise > cfg.get("pit_threshold", 0.90)).astype(np.float32)
    speck = (noise > cfg.get("speck_threshold", 0.975)).astype(np.float32)
    mode = cfg["mode"]

    if mode == "acid":
        rings = np.clip(1.0 - np.abs(np.sin((flow * 28.0 + x * 9.0 - y * 6.0) * np.pi)) * 19.0, 0, 1)
        damage = np.clip(rings * 0.75 + pits * 0.45 + crack * 0.35, 0, 1)
        field = _norm(flow * 0.45 + damage * 0.70)
    elif mode == "desert":
        streak = np.clip(1.0 - np.abs(np.sin((x * 7.0 + y * 74.0 + flow * 3.0) * np.pi)) * 18.0, 0, 1)
        sand = np.clip(noise * 0.45 + streak * 0.75 + (1.0 - y) * 0.18, 0, 1)
        damage = sand
        field = _norm(sand + flow * 0.25)
    elif mode == "galvanized":
        cell = np.floor((x + flow * 0.03) * 38.0) + np.floor((y - flow * 0.03) * 33.0) * 1.7
        spangle = (np.sin(cell * 12.9898 + cfg["salt"]) * 43758.5453) % 1.0
        damage = np.clip(_norm(spangle) * 0.85 + crack * 0.22, 0, 1)
        field = _norm(spangle + flow * 0.22)
    elif mode == "heat":
        band = _norm(np.sin((x * 4.0 + y * 1.5 + flow * 0.75) * np.pi))
        damage = np.clip(crack * 0.25 + speck * 0.35 + band * 0.45, 0, 1)
        field = band
    elif mode == "oxide":
        bloom = np.clip(1.0 - np.abs(np.sin((flow * 18.0 + x * 13.0 + y * 7.0) * np.pi)) * 13.0, 0, 1)
        damage = np.clip(bloom * 0.82 + pits * 0.35 + crack * 0.24, 0, 1)
        field = _norm(flow * 0.42 + bloom * 0.74)
    elif mode == "salt":
        crystal = np.minimum(
            np.abs(np.sin((x * 54.0 + flow * 1.5) * np.pi)),
            np.abs(np.sin((y * 47.0 - flow * 1.2) * np.pi)),
        )
        crystals = np.clip(1.0 - crystal * 22.0, 0, 1)
        damage = np.clip(crystals + speck * 0.65 + crack * 0.22, 0, 1)
        field = _norm(flow * 0.25 + crystals * 0.85)
    elif mode == "uv":
        gradient = np.clip(1.0 - y * 0.82 + flow * 0.18, 0, 1)
        chalk = np.clip(crack * 0.65 + pits * 0.35 + gradient * 0.45, 0, 1)
        damage = chalk
        field = _norm(gradient + crack * 0.35)
    elif mode == "peel":
        island = np.clip(1.0 - np.abs(np.sin((flow * 23.0 + x * 11.0 - y * 8.0) * np.pi)) * 10.0, 0, 1)
        edge = np.clip(1.0 - np.abs(island - 0.42) * 7.0, 0, 1)
        damage = np.clip(island * 0.60 + edge * 0.60 + crack * 0.35 + speck * 0.35, 0, 1)
        field = _norm(island * 0.70 + edge * 0.45 + flow * 0.18)
    else:
        damage = np.clip(flow * 0.55 + crack * 0.40 + pits * 0.25, 0, 1)
        field = _norm(flow * 0.70 + damage * 0.30)

    micro = _norm(
        np.sin((x * cfg["micro"] + y * cfg["micro"] * 0.57 + cfg["salt"]) * np.pi)
        + np.sin((x * cfg["micro"] * 1.83 - y * cfg["micro"] * 1.41 + seed * 0.07) * np.pi) * 0.55
    )
    out = (field.astype(np.float32), damage.astype(np.float32), crack.astype(np.float32), micro.astype(np.float32), speck.astype(np.float32))
    if len(_FIELDS_CACHE) > 32:
        _FIELDS_CACHE.clear()
    _FIELDS_CACHE[key] = tuple(part.copy() for part in out)
    return out


def _paint_from_cfg(cfg):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = shape[:2] if len(shape) > 2 else shape
        mask_arr = np.asarray(mask, dtype=np.float32)
        base = paint[:, :, :3].astype(np.float32, copy=True)
        field, damage, crack, micro, speck = _fields((h, w), seed, cfg)
        _, y = _xy((h, w))
        damage_vis = np.clip(damage * cfg.get("damage_boost", 1.0), 0, 1)
        crack_vis = np.clip(crack * cfg.get("crack_boost", 1.0), 0, 1)
        hue = cfg["hue"] + field * cfg.get("hue_span", 0.035) + damage * cfg.get("damage_hue", 0.02)
        sat = np.clip(cfg.get("sat", 0.42) - damage * cfg.get("desat", 0.12) + micro * 0.05, 0, 1)
        val = np.clip(cfg.get("val", 0.36) + field * cfg.get("val_span", 0.20) - damage_vis * cfg.get("darken", 0.08) + speck * 0.16, 0, 1)
        target = _hsv(hue % 1.0, sat, val)
        oxide = np.array(cfg.get("oxide", (0.0, 0.0, 0.0)), dtype=np.float32).reshape(1, 1, 3)
        primer = np.array(cfg.get("primer", (0.22, 0.19, 0.15)), dtype=np.float32).reshape(1, 1, 3)
        target = target * (1.0 - damage_vis[:, :, None] * cfg.get("oxide_gain", 0.35)) + oxide * damage_vis[:, :, None] * cfg.get("oxide_gain", 0.35)
        target = target * (1.0 - crack_vis[:, :, None] * cfg.get("primer_gain", 0.25)) + primer * crack_vis[:, :, None] * cfg.get("primer_gain", 0.25)
        target = np.clip(target + micro[:, :, None] * cfg.get("micro_gain", 0.045) + speck[:, :, None] * cfg.get("speck_gain", 0.08), 0, 1)
        if cfg["mode"] == "acid":
            rim = np.clip(damage_vis - crack_vis * 0.35, 0, 1)
            target = np.clip(target + rim[:, :, None] * np.array([0.10, 0.18, 0.02], dtype=np.float32), 0, 1)
        elif cfg["mode"] == "uv":
            chalk = np.clip((1.0 - y) * damage_vis, 0, 1)
            target = np.clip(target + chalk[:, :, None] * 0.18 - crack_vis[:, :, None] * 0.08, 0, 1)
        elif cfg["mode"] == "peel":
            lifted = np.clip(damage_vis * 0.85 + crack_vis * 0.65, 0, 1)
            target = target * (1.0 - lifted[:, :, None] * 0.22) + primer * lifted[:, :, None] * 0.22
        blend = cfg.get("blend", 0.88) * float(pm) * mask_arr[:, :, None]
        out = base * (1.0 - blend) + target * blend
        out = np.clip(out + _bb(bb, (h, w))[:, :, None] * cfg.get("bb_gain", 0.05) * mask_arr[:, :, None], 0, 1)
        return np.ascontiguousarray(out.astype(np.float32))

    return paint_fn


def _spec_from_cfg(cfg):
    def spec_fn(shape, seed, sm, base_m, base_r):
        h, w = shape[:2] if len(shape) > 2 else shape
        field, damage, crack, micro, speck = _fields((h, w), seed, cfg)
        lifted_edge = _edge(field * 0.48 + damage * 0.34 + crack * 0.18)
        m = (
            cfg["m"]
            + field * cfg.get("m_span", 24.0)
            - damage * cfg.get("m_loss", 35.0)
            + speck * 44.0
            + lifted_edge * cfg.get("m_edge", 0.0)
        )
        r = (
            cfg["r"]
            + damage * cfg.get("r_damage", 70.0)
            + crack * 35.0
            + (1.0 - micro) * 18.0
            + lifted_edge * cfg.get("r_edge", 0.0)
            - speck * cfg.get("r_speck_drop", 0.0)
        )
        cc = (
            cfg["cc"]
            - damage * cfg.get("cc_loss", 40.0)
            - crack * 24.0
            + field * cfg.get("cc_field", 0.0)
            + lifted_edge * cfg.get("cc_edge", 0.0)
            + speck * cfg.get("cc_speck", 8.0)
            + micro * cfg.get("cc_micro", 0.0)
        )
        return (
            np.clip(m * float(sm), 0, 255).astype(np.float32),
            np.clip(r, 15, 255).astype(np.float32),
            np.clip(cc, 16, 255).astype(np.float32),
        )

    return spec_fn


_CONFIGS = {
    "acid_rain": dict(mode="acid", hue=0.23, sat=0.36, val=0.38, val_span=0.18, freq=42.0, micro=185.0, salt=301, m=44, r=118, cc=68, oxide=(0.52, 0.66, 0.28), primer=(0.22, 0.25, 0.18), pit_threshold=0.84, oxide_gain=0.62, damage_boost=1.55, crack_boost=1.45, darken=0.16),
    "desert_worn": dict(mode="desert", hue=0.105, sat=0.32, val=0.44, val_span=0.16, freq=34.0, micro=210.0, salt=302, m=26, r=166, cc=110, oxide=(0.72, 0.62, 0.42), primer=(0.48, 0.38, 0.24), pit_threshold=0.88, darken=0.06, damage_boost=1.35),
    "galvanized": dict(mode="galvanized", hue=0.58, sat=0.12, val=0.44, val_span=0.24, freq=28.0, micro=160.0, salt=303, m=188, r=52, cc=32, oxide=(0.58, 0.61, 0.56), primer=(0.38, 0.40, 0.38), oxide_gain=0.22),
    "heat_treated": dict(mode="heat", hue=0.63, sat=0.62, val=0.32, val_span=0.34, freq=24.0, micro=150.0, salt=304, m=190, r=42, cc=26, hue_span=0.34, oxide=(0.55, 0.20, 0.08), primer=(0.10, 0.08, 0.12), oxide_gain=0.22),
    "oxidized_copper": dict(mode="oxide", hue=0.42, sat=0.50, val=0.34, val_span=0.24, freq=38.0, micro=176.0, salt=305, m=96, r=122, cc=64, oxide=(0.10, 0.72, 0.58), primer=(0.62, 0.24, 0.08), oxide_gain=0.74, damage_boost=1.35),
    "patina_bronze": dict(mode="oxide", hue=0.10, sat=0.48, val=0.30, val_span=0.22, freq=36.0, micro=165.0, salt=306, m=118, r=104, cc=54, oxide=(0.10, 0.48, 0.40), primer=(0.58, 0.32, 0.10), oxide_gain=0.58, damage_boost=1.25),
    "rugged": dict(mode="default", hue=0.09, sat=0.28, val=0.31, val_span=0.18, freq=60.0, micro=220.0, salt=307, m=42, r=170, cc=96, oxide=(0.36, 0.31, 0.24), primer=(0.20, 0.18, 0.15), pit_threshold=0.82),
    "salt_corroded": dict(mode="salt", hue=0.54, sat=0.14, val=0.34, val_span=0.18, freq=44.0, micro=210.0, salt=308, m=54, r=156, cc=82, oxide=(0.74, 0.78, 0.70), primer=(0.25, 0.28, 0.26), oxide_gain=0.55, speck_threshold=0.94),
    "sun_baked": dict(mode="uv", hue=0.08, sat=0.34, val=0.42, val_span=0.18, freq=46.0, micro=190.0, salt=309, m=20, r=190, cc=96, oxide=(0.82, 0.62, 0.38), primer=(0.48, 0.30, 0.18), crack_width=18.0, desat=0.30, damage_boost=1.55, crack_boost=1.4, darken=0.12),
    "vintage_chrome": dict(mode="salt", hue=0.56, sat=0.08, val=0.56, val_span=0.24, freq=52.0, micro=240.0, salt=310, m=216, r=24, cc=18, oxide=(0.82, 0.80, 0.72), primer=(0.42, 0.40, 0.34), oxide_gain=0.28, pit_threshold=0.78),
    "sun_fade": dict(mode="uv", hue=0.12, sat=0.26, val=0.48, val_span=0.16, freq=34.0, micro=170.0, salt=311, m=18, r=178, cc=106, oxide=(0.82, 0.74, 0.56), primer=(0.46, 0.36, 0.24), crack_width=21.0, desat=0.38, damage_boost=1.45, crack_boost=1.25, darken=0.08),
    "crumbling_clear": dict(mode="peel", hue=0.10, sat=0.24, val=0.36, val_span=0.20, freq=43.0, micro=180.0, salt=312, m=22, r=196, cc=72, oxide=(0.70, 0.62, 0.46), primer=(0.30, 0.23, 0.16), crack_width=16.0, oxide_gain=0.54, primer_gain=0.72, damage_boost=1.60, crack_boost=1.55, m_edge=42, r_edge=-18, r_speck_drop=28, cc_loss=58, cc_field=42, cc_edge=68, cc_speck=28, cc_micro=18),
    "destroyed_coat": dict(mode="peel", hue=0.13, sat=0.18, val=0.26, val_span=0.18, freq=58.0, micro=230.0, salt=313, m=6, r=214, cc=58, oxide=(0.46, 0.42, 0.32), primer=(0.16, 0.14, 0.12), crack_width=14.0, oxide_gain=0.58, primer_gain=0.86, pit_threshold=0.80, damage_boost=1.75, crack_boost=1.75, m_edge=56, r_edge=-22, r_speck_drop=32, cc_loss=66, cc_field=38, cc_edge=74, cc_speck=32, cc_micro=20),
}


OWNER_REVIEW_WEATHERED_AGED_OVERRIDES = {
    finish_id: (_paint_from_cfg(cfg), _spec_from_cfg(cfg)) for finish_id, cfg in _CONFIGS.items()
}
