"""Owner-review Satin & Wrap source renderers for SPB-30."""

from __future__ import annotations

import numpy as np


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


def _hash(shape, seed, salt):
    x, y = _xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + (int(seed) + salt) * 0.177) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _hsv(h, s, v):
    h6 = (h * 6.0) % 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    r = np.where(i == 0, v, np.where(i == 1, q, np.where(i == 2, p, np.where(i == 3, p, np.where(i == 4, t, v)))))
    g = np.where(i == 0, t, np.where(i == 1, v, np.where(i == 2, v, np.where(i == 3, q, np.where(i == 4, p, p)))))
    b = np.where(i == 0, p, np.where(i == 1, p, np.where(i == 2, t, np.where(i == 3, v, np.where(i == 4, v, q)))))
    return np.stack([r, g, b], axis=2).astype(np.float32)


def _base_fields(shape, seed, cfg):
    x, y = _xy(shape)
    phase = ((int(seed) + cfg["salt"]) % 8192) * 0.011
    grain = (
        np.sin((x * cfg["grain_x"] + y * cfg["grain_y"] + phase) * np.pi) * 0.46
        + np.sin((x * cfg["grain_x"] * 2.7 - y * cfg["grain_y"] * 1.9 + phase * 1.6) * np.pi) * 0.26
        + np.sin((x * cfg["micro"] + y * cfg["micro"] * 0.53 + phase * 0.7) * np.pi) * 0.13
    )
    noise = _hash(shape, seed, cfg["salt"])
    fine = _norm(grain + (noise - 0.5) * 0.55)
    seam = np.clip(1.0 - np.abs(np.sin((x * cfg.get("seam_x", 9.0) + y * cfg.get("seam_y", 1.0) + phase) * np.pi)) * cfg.get("seam_width", 28.0), 0, 1)
    peel = np.clip(1.0 - np.abs(np.sin((fine * cfg.get("peel_freq", 18.0) + x * 7.0 - y * 4.0) * np.pi)) * cfg.get("peel_width", 18.0), 0, 1)
    sparkle = (noise > cfg.get("spark_threshold", 0.986)).astype(np.float32)
    return fine.astype(np.float32), seam.astype(np.float32), peel.astype(np.float32), sparkle


def _paint_from_cfg(cfg):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = shape[:2] if len(shape) > 2 else shape
        mask_arr = np.asarray(mask, dtype=np.float32)
        base = paint[:, :, :3].astype(np.float32, copy=True)
        fine, seam, peel, sparkle = _base_fields((h, w), seed, cfg)
        x, y = _xy((h, w))
        mode = cfg["mode"]

        if mode == "flip":
            hue = (cfg["hue"] + fine * 0.34 + seam * 0.09 + np.sin((x * 5.0 + y * 3.0) * np.pi) * 0.035) % 1.0
            target = _hsv(hue, 0.82 + peel * 0.10, 0.42 + fine * 0.22 + sparkle * 0.22)
        elif mode == "chrome":
            target = np.stack([0.50 + fine * 0.34, 0.51 + fine * 0.33, 0.53 + fine * 0.35], axis=2)
            target = np.clip(target + seam[:, :, None] * 0.20 + peel[:, :, None] * 0.08, 0, 1)
        elif mode == "black":
            target = np.stack([0.025 + fine * 0.065, 0.026 + fine * 0.072, 0.030 + fine * 0.090], axis=2)
            target = np.clip(target + seam[:, :, None] * 0.028 + peel[:, :, None] * 0.035, 0, 1)
        elif mode == "frost":
            hue = 0.55 + fine * 0.08
            target = _hsv(hue, 0.10 + peel * 0.16, 0.58 + fine * 0.18 + seam * 0.18)
        elif mode == "gloss":
            dome = np.clip(1.0 - np.sqrt((x - 0.52) ** 2 + (y - 0.47) ** 2) * 1.8, 0, 1)
            hue = cfg["hue"] + fine * 0.02
            target = _hsv(hue, 0.20 + peel * 0.12, 0.12 + dome * 0.62 + fine * 0.12 + seam * 0.10)
        else:
            hue = cfg["hue"] + fine * cfg.get("hue_span", 0.025)
            target = _hsv(hue, cfg.get("sat", 0.20) + peel * 0.10, cfg.get("val", 0.30) + fine * cfg.get("val_span", 0.20) + seam * 0.10)

        tint = np.array(cfg.get("tint", (0.0, 0.0, 0.0)), dtype=np.float32).reshape(1, 1, 3)
        target = np.clip(target + tint * peel[:, :, None] * 0.16 + sparkle[:, :, None] * cfg.get("spark_gain", 0.10), 0, 1)
        blend = cfg.get("blend", 0.88) * float(pm) * mask_arr[:, :, None]
        out = base * (1.0 - blend) + target * blend
        out = np.clip(out + _bb(bb, (h, w))[:, :, None] * cfg.get("bb_gain", 0.07) * mask_arr[:, :, None], 0, 1)
        return np.ascontiguousarray(out.astype(np.float32))

    return paint_fn


def _spec_from_cfg(cfg):
    def spec_fn(shape, seed, sm, base_m, base_r):
        h, w = shape[:2] if len(shape) > 2 else shape
        fine, seam, peel, sparkle = _base_fields((h, w), seed, cfg)
        m = cfg["m"] + fine * cfg.get("m_span", 24.0) + seam * 22.0 + sparkle * 50.0
        r = cfg["r"] + (1.0 - fine) * cfg.get("r_span", 22.0) + peel * 18.0 - seam * 8.0
        cc = cfg["cc"] + seam * cfg.get("cc_span", 18.0) + peel * 8.0
        return (
            np.clip(m * float(sm), 0, 255).astype(np.float32),
            np.clip(r, 15, 255).astype(np.float32),
            np.clip(cc, 16, 255).astype(np.float32),
        )

    return spec_fn


_CONFIGS = {
    "brushed_wrap": dict(mode="fiber", hue=0.58, sat=0.10, val=0.34, val_span=0.28, grain_x=6.0, grain_y=96.0, micro=230.0, salt=201, seam_x=14.0, seam_y=0.8, m=120, r=56, cc=34, tint=(0.03, 0.04, 0.05)),
    "chrome_wrap": dict(mode="chrome", hue=0.58, grain_x=36.0, grain_y=68.0, micro=210.0, salt=202, seam_x=18.0, seam_y=4.0, peel_freq=26.0, m=232, r=14, cc=16),
    "color_flip_wrap": dict(mode="flip", hue=0.48, grain_x=19.0, grain_y=31.0, micro=160.0, salt=203, seam_x=10.0, seam_y=6.0, peel_freq=22.0, m=196, r=28, cc=18, spark_gain=0.16),
    "frozen_matte": dict(mode="frost", hue=0.56, grain_x=44.0, grain_y=37.0, micro=190.0, salt=204, seam_x=16.0, seam_y=11.0, peel_freq=30.0, m=32, r=188, cc=204, spark_gain=0.08),
    "gloss_wrap": dict(mode="gloss", hue=0.60, grain_x=21.0, grain_y=18.0, micro=150.0, salt=205, seam_x=7.0, seam_y=3.0, peel_freq=16.0, m=26, r=20, cc=16, spark_gain=0.12),
    "liquid_wrap": dict(mode="flip", hue=0.51, grain_x=15.0, grain_y=23.0, micro=145.0, salt=206, seam_x=4.0, seam_y=13.0, peel_freq=20.0, m=166, r=24, cc=16, tint=(0.0, 0.08, 0.15), spark_gain=0.18),
    "matte_wrap": dict(mode="black", hue=0.62, grain_x=33.0, grain_y=41.0, micro=210.0, salt=207, seam_x=12.0, seam_y=9.0, peel_freq=34.0, m=18, r=198, cc=216, spark_gain=0.03),
    "satin_wrap": dict(mode="fiber", hue=0.57, sat=0.08, val=0.46, val_span=0.18, grain_x=10.0, grain_y=118.0, micro=260.0, salt=208, seam_x=20.0, seam_y=0.6, m=74, r=78, cc=52, tint=(0.03, 0.03, 0.04)),
    "stealth_wrap": dict(mode="black", hue=0.61, grain_x=52.0, grain_y=47.0, micro=240.0, salt=209, seam_x=18.0, seam_y=18.0, peel_freq=40.0, m=44, r=158, cc=130, spark_gain=0.04),
    "textured_wrap": dict(mode="fiber", hue=0.60, sat=0.06, val=0.24, val_span=0.22, grain_x=72.0, grain_y=64.0, micro=280.0, salt=210, seam_x=24.0, seam_y=19.0, peel_freq=46.0, m=60, r=132, cc=92, tint=(0.04, 0.04, 0.05), spark_gain=0.06),
}


OWNER_REVIEW_SATIN_WRAP_OVERRIDES = {
    finish_id: (_paint_from_cfg(cfg), _spec_from_cfg(cfg)) for finish_id, cfg in _CONFIGS.items()
}
