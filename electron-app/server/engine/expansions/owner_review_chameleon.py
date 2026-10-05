"""Owner-review chameleon rebuilds for SPB-30.

These functions replace the broad legacy chameleon ramps with high-frequency
thin-film interference fields. Shared helpers keep the math compact, while
each finish gets its own palette, field topology, detail frequency, and spec
personality.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np


def _xy(shape):
    h, w = shape[:2] if len(shape) > 2 else shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _mask(mask, shape):
    if mask is None:
        h, w = shape[:2] if len(shape) > 2 else shape
        return np.ones((h, w), dtype=np.float32)
    return np.asarray(mask, dtype=np.float32)


def _seed(seed, salt):
    return float((int(seed) * 1664525 + int(salt) * 1013904223) & 0xFFFFFFFF) / 0xFFFFFFFF


def _norm(arr):
    arr = np.asarray(arr, dtype=np.float32)
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def _hsv_to_rgb(h, s, v):
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


def _palette(hues, t):
    hues = np.asarray(hues, dtype=np.float32) % 1.0
    n = len(hues)
    pos = np.clip(t, 0.0, 0.9999) * n
    idx = np.floor(pos).astype(np.int32) % n
    frac = pos - np.floor(pos)
    a = hues[idx]
    b = hues[(idx + 1) % n]
    delta = ((b - a + 0.5) % 1.0) - 0.5
    return (a + delta * frac) % 1.0


_FIELD_CACHE = OrderedDict()
_FIELD_CACHE_MAX = 4


def _field(shape, seed, cfg):
    h, w = shape[:2] if len(shape) > 2 else shape
    cache_key = (int(h), int(w), int(seed), int(cfg["salt"]))
    cached = _FIELD_CACHE.get(cache_key)
    if cached is not None:
        _FIELD_CACHE.move_to_end(cache_key)
        return cached
    x, y = _xy(shape)
    cx = x - cfg.get("cx", 0.5)
    cy = y - cfg.get("cy", 0.5)
    angle = np.arctan2(cy, cx)
    dist = np.sqrt(cx * cx + cy * cy)
    phase = _seed(seed, cfg["salt"]) * np.pi * 2.0
    freq = cfg["freq"]
    warp = (
        np.sin((x * (freq * 0.31) + y * (freq * 0.19)) * np.pi + phase) * 0.28
        + np.sin((x * (freq * 0.73) - y * (freq * 0.41)) * np.pi + phase * 1.7) * 0.20
        + np.sin((x * (freq * 1.47) + y * (freq * 1.13)) * np.pi + phase * 2.3) * 0.12
    )
    mode = cfg["mode"]
    if mode == "aurora":
        core = np.sin((y * (freq * 1.3) + np.sin(x * np.pi * 6.0 + phase) * 0.16 + warp * 0.35) * np.pi)
    elif mode == "shards":
        core = np.sin((x * freq + y * (freq * 0.67) + np.floor((x + y + warp) * 18.0) * 0.11) * np.pi)
    elif mode == "rings":
        core = np.sin((dist * freq * 2.4 + angle * cfg.get("twist", 1.0) + warp * 1.1) * np.pi)
    elif mode == "comet":
        core = np.sin(((x * 0.35 + y * 1.85) * freq + dist * 9.0 + warp) * np.pi)
    elif mode == "frost":
        core = np.sin((x * freq + y * freq * 0.42 + np.abs(np.sin(angle * 6.0)) * 1.4 + warp) * np.pi)
    elif mode == "oil":
        core = np.sin((dist * freq * 1.8 + np.sin(angle * 5.0 + phase) * 0.9 + warp * 1.5) * np.pi)
    elif mode == "black":
        core = np.sin((x * freq * 0.72 - y * freq * 0.55 + dist * 17.0 + warp * 1.1) * np.pi)
    else:
        core = np.sin((x * freq + y * freq * 0.82 + warp * 1.2) * np.pi)
    field = _norm(core * 0.62 + warp * 0.38)
    if mode == "shards":
        cells = (
            np.floor(np.clip(x * 9.0 + y * 4.0 + warp * 2.0 + phase, 0.0, 99.0))
            + np.floor(np.clip(x * -5.0 + y * 12.0 - warp * 1.4 + phase * 0.7, 0.0, 99.0)) * 1.7
            + np.floor(np.clip(x * 15.0 - y * 8.0 + phase * 0.3, 0.0, 99.0)) * 0.6
        )
        field = _norm(np.mod(cells, 11.0) / 10.0 + warp * 0.18)
    elif mode == "rings":
        field = _norm(dist * cfg.get("ring_scale", 2.4) + angle * cfg.get("twist", 1.0) * 0.10 + warp * 0.38)
    elif mode == "aurora":
        field = _norm(y * 0.72 + np.sin(x * np.pi * cfg.get("curtain", 7.0) + phase) * 0.18 + warp * 0.44)
    elif mode == "comet":
        field = _norm(y * 0.95 - x * 0.18 + dist * 0.22 + np.sin(x * np.pi * 9.0 + phase) * 0.08 + warp * 0.34)
    elif mode == "frost":
        ray_field = 1.0 - np.abs(np.sin(angle * cfg.get("rays", 9.0) + phase))
        field = _norm(ray_field * 0.46 + dist * 0.42 + warp * 0.26)
    elif mode == "oil":
        field = _norm(np.sin((dist * cfg.get("ring_scale", 3.2) + angle * 0.28 + warp) * np.pi) * 0.55 + warp * 0.35)
    elif mode == "black":
        field = _norm(field * 0.45 + dist * 0.35 + warp * 0.30)
    if mode == "shards":
        a = np.abs(np.sin((x * cfg["ridge"] + y * cfg["ridge"] * 0.37 + warp * 1.7 + phase) * np.pi))
        b = np.abs(np.sin((x * -cfg["ridge"] * 0.31 + y * cfg["ridge"] * 0.92 + warp * 1.2 + phase * 1.3) * np.pi))
        c = np.abs(np.sin((x * cfg["ridge"] * 0.71 - y * cfg["ridge"] * 0.63 + phase * 0.7) * np.pi))
        ridges = np.clip(1.0 - np.minimum(np.minimum(a, b), c) * (cfg["ridge_width"] * 0.82), 0.0, 1.0)
    elif mode == "rings":
        facets = np.sin(angle * cfg.get("petals", 7.0) + warp * 2.0 + phase) * 0.08
        ridges = np.clip(1.0 - np.abs(np.sin((dist * cfg["ridge"] * 3.6 + facets + field * 2.0) * np.pi)) * cfg["ridge_width"], 0.0, 1.0)
    elif mode == "aurora":
        curtains = y * cfg["ridge"] * 0.72 + np.sin(x * 18.0 + phase) * 0.55 + warp * 1.6
        cross = x * cfg["ridge"] * 0.18 + np.sin(y * 12.0 + phase * 0.4) * 0.35
        ridges = np.clip(1.0 - np.abs(np.sin((curtains + cross) * np.pi)) * cfg["ridge_width"], 0.0, 1.0)
    elif mode == "comet":
        flame = (y * cfg["ridge"] * 0.9 - x * cfg["ridge"] * 0.23 + np.sin(x * 22.0 + phase) * 0.6 + warp * 2.2)
        ridges = np.clip(1.0 - np.abs(np.sin(flame * np.pi)) * cfg["ridge_width"], 0.0, 1.0)
        ridges *= np.clip(0.45 + y * 0.85 + np.sin((x * 6.0 + phase) * np.pi) * 0.15, 0.0, 1.0)
    elif mode == "frost":
        ray = np.abs(np.sin((angle * cfg.get("rays", 9.0) + warp * 2.8 + phase) * np.pi))
        ring = np.abs(np.sin((dist * cfg["ridge"] * 3.2 + field * 1.4) * np.pi))
        branch = np.minimum(ray, ring)
        ridges = np.clip(1.0 - branch * (cfg["ridge_width"] * 0.72), 0.0, 1.0)
    elif mode == "oil":
        cell = np.sin((dist * cfg["ridge"] * 2.9 + angle * 2.0 + warp * 2.4) * np.pi)
        flow = np.sin((x * cfg["ridge"] * 0.52 - y * cfg["ridge"] * 0.43 + warp * 2.0 + phase) * np.pi)
        ridges = np.clip(1.0 - np.abs(cell * 0.65 + flow * 0.35) * cfg["ridge_width"], 0.0, 1.0)
    elif mode == "black":
        scratch = np.minimum(
            np.abs(np.sin((x * cfg["ridge"] * 0.8 - y * cfg["ridge"] * 0.42 + phase) * np.pi)),
            np.abs(np.sin((x * cfg["ridge"] * 0.17 + y * cfg["ridge"] * 1.3 + warp + phase * 1.4) * np.pi)),
        )
        ridges = np.clip(1.0 - scratch * (cfg["ridge_width"] * 0.95), 0.0, 1.0) * np.clip(field * 1.4, 0.0, 1.0)
    else:
        ridges = np.clip(1.0 - np.abs(np.sin((field * cfg["ridge"] + x * cfg["micro"] + y * cfg["micro"] * 0.37 + phase) * np.pi)) * cfg["ridge_width"], 0.0, 1.0)
    glint = np.clip(1.0 - np.abs(np.sin((x * cfg["glint_x"] - y * cfg["glint_y"] + warp * 0.45 + phase) * np.pi)) * 42.0, 0.0, 1.0)
    micro = _norm(
        np.sin((x * (cfg["micro"] * 3.1) + y * (cfg["micro"] * 2.7)) * np.pi + phase)
        + np.sin((x * (cfg["micro"] * 5.3) - y * (cfg["micro"] * 4.9)) * np.pi + phase * 0.7) * 0.5
    )
    fine = _norm(
        np.sin((x * (cfg["micro"] * 7.1) - y * (cfg["micro"] * 6.3)) * np.pi + phase * 1.9)
        + np.sin((x * (cfg["micro"] * 10.7) + y * (cfg["micro"] * 8.9)) * np.pi + phase * 2.6) * 0.45
    )
    micro = _norm(micro * 0.72 + fine * 0.28)
    result = (field, ridges.astype(np.float32), glint.astype(np.float32), micro.astype(np.float32))
    _FIELD_CACHE[cache_key] = result
    _FIELD_CACHE.move_to_end(cache_key)
    while len(_FIELD_CACHE) > _FIELD_CACHE_MAX:
        _FIELD_CACHE.popitem(last=False)
    return result


def _make_spec(cfg):
    def spec_fn(shape, mask, seed, sm):
        mask_arr = _mask(mask, shape)
        h, w = shape[:2] if len(shape) > 2 else shape
        field, ridges, glint, micro = _field((h, w), seed, cfg)
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        m_ridge = float(cfg.get("m_ridge_gain", 18.0))
        m_glint = float(cfg.get("m_glint_gain", 24.0))
        m_micro = float(cfg.get("m_micro_gain", 12.0))
        m = cfg["m0"] + field * cfg["m_span"] + ridges * m_ridge + glint * m_glint + (micro - 0.5) * m_micro
        # Preserve strong pattern lock in metallic while preventing flat high-red fills.
        # Contrast-stretch masked metallic values so the R(M) channel visibly tracks paint structure.
        spec_style = str(cfg.get("spec_style", "balanced"))
        style_m_bounds = {
            "chrome": (110.0, 210.0),
            "candy": (24.0, 118.0),
            "anodized": (34.0, 136.0),
            "frozen": (0.0, 92.0),
            "satin_flake": (48.0, 154.0),
            "balanced": (54.0, 166.0),
        }
        style_r_bounds = {
            "chrome": (18.0, 58.0),
            "candy": (62.0, 138.0),
            "anodized": (76.0, 156.0),
            "frozen": (118.0, 218.0),
            "satin_flake": (58.0, 132.0),
            "balanced": (54.0, 142.0),
        }
        style_cc_bounds = {
            "chrome": (16.0, 52.0),
            "candy": (70.0, 158.0),
            "anodized": (88.0, 174.0),
            "frozen": (122.0, 230.0),
            "satin_flake": (62.0, 150.0),
            "balanced": (58.0, 156.0),
        }
        m_lo, m_hi = style_m_bounds.get(spec_style, style_m_bounds["balanced"])
        m_masked = m[mask_arr > 0.01]
        if m_masked.size > 64:
            p5 = float(np.percentile(m_masked, 5))
            p95 = float(np.percentile(m_masked, 95))
            if p95 - p5 > 1e-3:
                m = m_lo + ((m - p5) / (p95 - p5)) * (m_hi - m_lo)
            else:
                m = np.full_like(m, (m_lo + m_hi) * 0.5, dtype=np.float32)
            m = np.clip(m, m_lo, m_hi)
        r_style_gain = float(cfg.get("r_style_gain", 1.0))
        cc_style_gain = float(cfg.get("cc_style_gain", 1.0))
        r = cfg["r0"] + (1.0 - field) * cfg["r_span"] - glint * 9.0 + ridges * 5.0 + (micro - 0.5) * 16.0
        cc = cfg["cc0"] + field * cfg["cc_span"] + glint * 8.0 + (micro - 0.5) * 11.0 + ridges * 3.0
        r *= r_style_gain
        cc = cfg["cc0"] + (cc - cfg["cc0"]) * cc_style_gain
        for channel, bounds in ((r, style_r_bounds), (cc, style_cc_bounds)):
            c_lo, c_hi = bounds.get(spec_style, bounds["balanced"])
            c_masked = channel[mask_arr > 0.01]
            if c_masked.size > 64:
                c5 = float(np.percentile(c_masked, 5))
                c95 = float(np.percentile(c_masked, 95))
                if c95 - c5 > 1e-3:
                    channel[:] = c_lo + ((channel - c5) / (c95 - c5)) * (c_hi - c_lo)
                else:
                    channel[:] = (c_lo + c_hi) * 0.5
                channel[:] = np.clip(channel, c_lo, c_hi)
        spec[:, :, 0] = np.clip(m * float(sm) * mask_arr + 5.0 * (1.0 - mask_arr), 0, 255).astype(np.uint8)
        spec[:, :, 1] = np.clip(r * mask_arr + 100.0 * (1.0 - mask_arr), 15, 255).astype(np.uint8)
        spec[:, :, 2] = np.where(mask_arr > 0.0, np.clip(cc, 16, 255), 0).astype(np.uint8)
        spec[:, :, 3] = np.clip(mask_arr * 255.0, 0, 255).astype(np.uint8)
        return spec

    return spec_fn


def _make_paint(cfg):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        mask_arr = _mask(mask, shape)
        h, w = shape[:2] if len(shape) > 2 else shape
        base = paint[:, :, :3].astype(np.float32, copy=True)
        field, ridges, glint, micro = _field((h, w), seed, cfg)
        paint_field = field
        if cfg.get("flow_paint"):
            x, y = _xy((h, w))
            phase = _seed(seed, cfg["salt"] + 71) * np.pi * 2.0
            flow_freq = float(cfg.get("flow_freq", cfg["freq"] * 0.42))
            flow = (
                np.sin((x * flow_freq + y * flow_freq * 0.58) * np.pi + phase)
                + np.sin((x * flow_freq * -0.36 + y * flow_freq * 1.12) * np.pi + phase * 1.7) * 0.62
                + np.sin((x * flow_freq * 1.74 - y * flow_freq * 0.22) * np.pi + phase * 0.4) * 0.28
            )
            paint_field = _norm(flow * 0.72 + field * 0.45 + ridges * 0.12)
        hue = _palette(cfg["hues"], np.clip(paint_field + ridges * cfg["ridge_hue"] + (micro - 0.5) * cfg["micro_hue"], 0.0, 1.0))
        sat = np.clip(cfg["sat"] + ridges * 0.10 + (micro - 0.5) * 0.105, 0.0, 1.0)
        val = np.clip(cfg["val"] + paint_field * cfg["val_span"] + ridges * 0.16 + glint * 0.22 + (micro - 0.5) * 0.078, 0.0, 1.0)
        if cfg.get("dark"):
            val *= np.clip(0.44 + field * 0.42 + ridges * 0.24 + glint * 0.28, 0.0, 1.0)
        if cfg.get("pale"):
            sat *= np.clip(0.42 + field * 0.25 + ridges * 0.22, 0.0, 1.0)
            val = np.clip(val + 0.16 + glint * 0.10, 0.0, 1.0)
        target = _hsv_to_rgb(hue, sat, val)
        tint = np.array(cfg.get("tint", (0.0, 0.0, 0.0)), dtype=np.float32).reshape(1, 1, 3)
        target = np.clip(target + tint * ridges[:, :, None] * 0.16 + glint[:, :, None] * 0.10, 0.0, 1.0)
        blend = cfg["blend"] * float(pm) * mask_arr[:, :, None]
        out = base * (1.0 - blend) + target * blend
        if bb is not None:
            bb_arr = bb[:, :, None] if getattr(bb, "ndim", 0) == 2 else bb
            out = np.clip(out + bb_arr * 0.22 * mask_arr[:, :, None], 0.0, 1.0)
        return np.ascontiguousarray(out.astype(np.float32))

    return paint_fn


_CONFIGS = {
    "chameleon_amethyst": dict(hues=[0.72, 0.80, 0.91, 0.66], mode="shards", freq=18.0, ridge=19.0, micro=86.0, glint_x=44.0, glint_y=63.0, salt=110, m0=136, m_span=84, r0=28, r_span=42, cc0=16, cc_span=34, sat=0.86, val=0.58, val_span=0.28, blend=0.86, ridge_hue=0.13, micro_hue=0.05, tint=(0.16, 0.02, 0.20), ridge_width=28.0, spec_style="candy", r_style_gain=1.18, cc_style_gain=1.22),
    "chameleon_arctic": dict(hues=[0.52, 0.58, 0.64, 0.48], mode="frost", freq=22.0, ridge=24.0, micro=118.0, glint_x=74.0, glint_y=51.0, salt=120, m0=178, m_span=44, r0=14, r_span=20, cc0=16, cc_span=16, sat=0.48, val=0.72, val_span=0.23, blend=0.82, ridge_hue=0.06, micro_hue=0.03, tint=(0.03, 0.09, 0.14), ridge_width=24.0, pale=True, spec_style="frozen", r_style_gain=1.32, cc_style_gain=1.30),
    "chameleon_aurora": dict(hues=[0.36, 0.48, 0.59, 0.73, 0.84], mode="aurora", freq=17.0, ridge=21.0, micro=97.0, glint_x=55.0, glint_y=38.0, salt=130, m0=190, m_span=50, r0=12, r_span=24, cc0=16, cc_span=20, sat=0.88, val=0.57, val_span=0.30, blend=0.88, ridge_hue=0.18, micro_hue=0.04, tint=(0.0, 0.15, 0.08), ridge_width=26.0, spec_style="anodized", r_style_gain=1.20, cc_style_gain=1.24),
    "chameleon_copper": dict(hues=[0.045, 0.085, 0.13, 0.42, 0.02], mode="oil", freq=19.0, ridge=17.0, micro=79.0, glint_x=46.0, glint_y=69.0, salt=140, m0=202, m_span=46, r0=10, r_span=25, cc0=16, cc_span=22, sat=0.82, val=0.55, val_span=0.33, blend=0.88, ridge_hue=0.09, micro_hue=0.03, tint=(0.18, 0.08, 0.01), ridge_width=30.0, spec_style="chrome", r_style_gain=0.95, cc_style_gain=0.88),
    "chameleon_emerald": dict(hues=[0.31, 0.38, 0.46, 0.54, 0.27], mode="aurora", freq=18.0, ridge=21.0, micro=128.0, glint_x=61.0, glint_y=49.0, salt=150, m0=192, m_span=52, r0=12, r_span=24, cc0=16, cc_span=18, sat=0.90, val=0.50, val_span=0.34, blend=0.89, ridge_hue=0.13, micro_hue=0.055, tint=(0.0, 0.18, 0.08), ridge_width=25.0, twist=2.7, spec_style="satin_flake", r_style_gain=1.15, cc_style_gain=1.05, flow_paint=True, flow_freq=9.0),
    "chameleon_fire": dict(hues=[0.99, 0.035, 0.08, 0.13, 0.02], mode="comet", freq=21.0, ridge=26.0, micro=92.0, glint_x=65.0, glint_y=35.0, salt=160, m0=198, m_span=52, r0=10, r_span=22, cc0=16, cc_span=18, sat=0.92, val=0.55, val_span=0.35, blend=0.90, ridge_hue=0.10, micro_hue=0.03, tint=(0.24, 0.08, 0.0), ridge_width=24.0, spec_style="chrome", r_style_gain=0.92, cc_style_gain=0.84),
    "chameleon_frost": dict(hues=[0.54, 0.60, 0.69, 0.78, 0.50], mode="frost", freq=24.0, ridge=29.0, micro=132.0, glint_x=87.0, glint_y=71.0, salt=170, m0=176, m_span=46, r0=15, r_span=19, cc0=16, cc_span=15, sat=0.42, val=0.74, val_span=0.22, blend=0.82, ridge_hue=0.05, micro_hue=0.025, tint=(0.04, 0.07, 0.13), ridge_width=22.0, pale=True, spec_style="frozen", r_style_gain=1.34, cc_style_gain=1.35),
    "chameleon_galaxy": dict(hues=[0.64, 0.72, 0.84, 0.91, 0.58, 0.03], mode="aurora", freq=20.5, ridge=28.0, micro=150.0, glint_x=97.0, glint_y=53.0, salt=180, m0=202, m_span=50, r0=11, r_span=26, cc0=16, cc_span=24, sat=0.92, val=0.40, val_span=0.38, blend=0.91, ridge_hue=0.24, micro_hue=0.075, tint=(0.08, 0.02, 0.18), ridge_width=22.0, twist=3.4, dark=True, spec_style="candy", r_style_gain=1.24, cc_style_gain=1.18, flow_paint=True, flow_freq=8.2),
    "chameleon_midnight": dict(hues=[0.62, 0.70, 0.80, 0.48], mode="black", freq=20.0, ridge=25.0, micro=108.0, glint_x=58.0, glint_y=77.0, salt=190, m0=185, m_span=54, r0=13, r_span=26, cc0=16, cc_span=22, sat=0.84, val=0.42, val_span=0.30, blend=0.86, ridge_hue=0.12, micro_hue=0.04, tint=(0.02, 0.03, 0.18), ridge_width=25.0, dark=True, spec_style="anodized", r_style_gain=1.25, cc_style_gain=1.22),
    "chameleon_neon": dict(hues=[0.31, 0.18, 0.88, 0.52, 0.97], mode="aurora", freq=23.0, ridge=34.0, micro=140.0, glint_x=72.0, glint_y=96.0, salt=200, m0=206, m_span=44, r0=9, r_span=20, cc0=16, cc_span=22, sat=0.97, val=0.58, val_span=0.38, blend=0.91, ridge_hue=0.26, micro_hue=0.07, tint=(0.10, 0.20, 0.03), ridge_width=22.0, spec_style="satin_flake", r_style_gain=1.10, cc_style_gain=1.04),
    "chameleon_obsidian": dict(hues=[0.70, 0.78, 0.61, 0.90], mode="black", freq=25.0, ridge=30.0, micro=122.0, glint_x=84.0, glint_y=56.0, salt=210, m0=195, m_span=50, r0=9, r_span=20, cc0=16, cc_span=24, sat=0.75, val=0.34, val_span=0.25, blend=0.86, ridge_hue=0.15, micro_hue=0.045, tint=(0.02, 0.00, 0.12), ridge_width=24.0, dark=True, spec_style="frozen", r_style_gain=1.38, cc_style_gain=1.32),
    "chameleon_ocean": dict(hues=[0.46, 0.53, 0.60, 0.69, 0.42], mode="aurora", freq=18.5, ridge=22.0, micro=90.0, glint_x=52.0, glint_y=66.0, salt=220, m0=190, m_span=52, r0=12, r_span=22, cc0=16, cc_span=18, sat=0.88, val=0.50, val_span=0.33, blend=0.89, ridge_hue=0.13, micro_hue=0.04, tint=(0.00, 0.12, 0.18), ridge_width=28.0, spec_style="candy", r_style_gain=1.20, cc_style_gain=1.20),
    "chameleon_phoenix": dict(hues=[0.96, 0.02, 0.08, 0.15, 0.86], mode="comet", freq=24.0, ridge=33.0, micro=116.0, glint_x=81.0, glint_y=43.0, salt=230, m0=112, m_span=34, r0=18, r_span=38, cc0=16, cc_span=34, sat=0.94, val=0.53, val_span=0.37, blend=0.91, ridge_hue=0.14, micro_hue=0.045, tint=(0.24, 0.07, 0.02), ridge_width=22.0, spec_style="frozen", r_style_gain=2.15, cc_style_gain=2.25),
    "chameleon_venom": dict(hues=[0.26, 0.33, 0.18, 0.42, 0.12], mode="shards", freq=27.0, ridge=35.0, micro=138.0, glint_x=96.0, glint_y=62.0, salt=240, m0=200, m_span=46, r0=10, r_span=22, cc0=16, cc_span=20, sat=0.95, val=0.48, val_span=0.39, blend=0.91, ridge_hue=0.17, micro_hue=0.055, tint=(0.08, 0.22, 0.02), ridge_width=21.0, spec_style="anodized", r_style_gain=1.24, cc_style_gain=1.16),
    "mystichrome": dict(hues=[0.58, 0.70, 0.84, 0.94, 0.06, 0.15, 0.34], mode="oil", freq=18.5, ridge=31.0, micro=170.0, glint_x=101.0, glint_y=91.0, salt=250, m0=208, m_span=46, r0=8, r_span=22, cc0=16, cc_span=26, sat=0.88, val=0.48, val_span=0.42, blend=0.92, ridge_hue=0.30, micro_hue=0.095, tint=(0.06, 0.05, 0.16), ridge_width=20.0, spec_style="chrome", r_style_gain=0.90, cc_style_gain=0.86, flow_paint=True, flow_freq=7.4),
}


OWNER_REVIEW_CHAMELEON_MONOLITHICS = {
    finish_id: (_make_spec(cfg), _make_paint(cfg)) for finish_id, cfg in _CONFIGS.items()
}
