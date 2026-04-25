"""Perceptual color-shift finishes for iRacing's fixed-paint/PBR box.

These do not rely on a painted macro gradient. They embed both target colors
everywhere as pixel-scale opponent populations, then use spec to make one
population diffuse/matte and the other metallic/glossy. At distance and in
motion, iRacing's lighting, mipmaps, and highlights make the dominant perceived
color flip harder than a normal static TGA should allow.
"""

from __future__ import annotations

import numpy as np

try:
    from engine.core import get_mgrid, multi_scale_noise
except ImportError:  # pragma: no cover - direct module execution fallback
    from core import get_mgrid, multi_scale_noise


def _norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _rgb(rgb):
    return np.array(rgb, dtype=np.float32).reshape(1, 1, 3)


def _color_table(colors):
    if colors is None:
        colors = []
    arr = np.array(colors, dtype=np.float32)
    if arr.size == 0:
        arr = np.array([[0.03, 0.18, 1.0]], dtype=np.float32)
    return arr.reshape(-1, 3)


def _luma(rgb):
    arr = np.array(rgb, dtype=np.float32)
    return float(arr[0] * 0.2126 + arr[1] * 0.7152 + arr[2] * 0.0722)


def _hyperflip_fields(
    shape,
    seed,
    density=0.42,
    orientation=0.0,
    turbulence=1.0,
    fine_density=0.18,
):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    size_scale = max(0.50, min(h, w) / 512.0)
    pix = max(1.0, min(h, w) / 2048.0)

    ang = float(orientation)
    c = np.cos(ang)
    s = np.sin(ang)
    u = xf * c + yf * s
    v = xf * -s + yf * c

    warp_a = (multi_scale_noise((h, w), [18, 36, 72], [0.42, 0.36, 0.22], seed + 911) - 0.5)
    warp_b = (multi_scale_noise((h, w), [9, 18, 36], [0.38, 0.36, 0.26], seed + 929) - 0.5)
    blue = _norm01(multi_scale_noise((h, w), [2, 4, 8, 16], [0.36, 0.28, 0.22, 0.14], seed + 941))

    # Three carriers avoid a simple checkerboard. The periods intentionally
    # live near pixel/mipmap scale so the viewer's eye integrates them.
    stripe_a = np.sin((u + warp_a * 8.0 * size_scale) / max(2.2 * pix, 1.0) * np.pi)
    stripe_b = np.sin((v + warp_b * 7.0 * size_scale) / max(3.1 * pix, 1.0) * np.pi)
    cross = np.sin((u * 0.63 + v * 0.77 + warp_a * 5.0 * size_scale) / max(5.3 * pix, 1.0) * np.pi)
    carrier = _norm01(stripe_a * 0.55 + stripe_b * 0.35 + cross * 0.24 + (blue - 0.5) * 0.42)

    # Separate mist layer: much finer and lower opacity than the flash cells.
    # This fills red gaps with color information without becoming coarse pepper.
    micro_a = np.sin((u * 1.71 + v * 0.43 + warp_b * 3.0 * size_scale) / max(1.13 * pix, 0.72) * np.pi)
    micro_b = np.sin((u * -0.58 + v * 1.93 + warp_a * 2.4 * size_scale) / max(1.47 * pix, 0.72) * np.pi)
    micro_noise = multi_scale_noise((h, w), [1, 2, 4, 8], [0.38, 0.30, 0.20, 0.12], seed + 953)
    micro = _norm01(micro_a * 0.40 + micro_b * 0.36 + (micro_noise - 0.5) * 0.54)

    macro = _norm01(
        u / max(w, 1)
        + 0.24 * np.sin(v / max(31.0 * size_scale, 1.0) + seed * 0.017)
        + 0.18 * np.cos((u + v) / max(47.0 * size_scale, 1.0))
        + warp_a * 0.30 * float(turbulence)
    )
    density_field = np.clip(float(density) + (macro - 0.5) * 0.10, 0.06, 0.36)
    flash = (carrier > (1.0 - density_field)).astype(np.float32)
    mist_density = np.clip(float(fine_density) + (macro - 0.5) * 0.08, 0.04, 0.42)
    mist = (micro > (1.0 - mist_density)).astype(np.float32)

    edge = np.maximum.reduce([
        xf / max(w - 1, 1),
        yf / max(h - 1, 1),
        1.0 - xf / max(w - 1, 1),
        1.0 - yf / max(h - 1, 1),
    ])
    edge = _norm01(edge)
    sparkle = np.clip((blue - 0.84) * 7.0, 0.0, 1.0) * (0.35 + edge * 0.65)
    veil = np.clip(flash * 0.82 + mist * 0.18 + sparkle * 0.42, 0.0, 1.0).astype(np.float32)
    return flash, mist, veil, macro, blue, micro


def paint_hyperflip_core(
    paint, shape, mask, seed, pm, bb,
    color_a=(1.0, 0.04, 0.02),
    color_b=(0.03, 0.18, 1.0),
    flake_colors=None,
    density=0.42,
    fine_density=0.18,
    orientation=0.0,
    turbulence=1.0,
    base_bias=0.66,
    carrier_chroma=0.34,
    carrier_alpha_scale=1.0,
    carrier_alpha_max=0.32,
    fine_alpha_scale=0.42,
    fine_alpha_max=0.15,
):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]

    flash, mist, veil, macro, blue, micro = _hyperflip_fields(
        (h, w), seed, density, orientation, turbulence, fine_density
    )
    ca = _rgb(color_a)
    cb = _rgb(color_b)
    flakes = _color_table(flake_colors if flake_colors is not None else [color_b])
    mask3 = mask[:, :, np.newaxis].astype(np.float32)

    base = ca * (0.92 + (1.0 - macro[:, :, np.newaxis]) * 0.12)
    base = base * (0.98 + (_norm01(blue)[:, :, np.newaxis] - 0.5) * 0.045)

    # The opponent population needs real chroma or iRacing's specular response
    # turns it into white flake. Keep it sparse and dark, but not neutral.
    b_luma = max(_luma(color_b), 0.08)
    chroma = float(carrier_chroma)
    carrier_tint = cb * (0.20 + b_luma * 0.10 + chroma * 0.78)
    carrier_shadow = ca * (0.052 + 0.020 * (1.0 - chroma)) + carrier_tint
    carrier_shadow = np.clip(carrier_shadow, 0.0, 1.0)
    carrier_alpha = (flash * (0.105 + 0.048 * macro) + veil * 0.030)[:, :, np.newaxis]
    carrier_alpha = np.clip(carrier_alpha * float(carrier_alpha_scale), 0.0, float(carrier_alpha_max))
    paint_rgb = base * (1.0 - carrier_alpha) + carrier_shadow * carrier_alpha

    selector = np.floor(micro * len(flakes)).astype(np.int32)
    selector = np.clip(selector, 0, len(flakes) - 1)
    mist_tint = flakes[selector]
    mist_luma = (
        mist_tint[:, :, 0] * 0.2126
        + mist_tint[:, :, 1] * 0.7152
        + mist_tint[:, :, 2] * 0.0722
    )[:, :, np.newaxis]
    mist_boost = np.clip(0.72 + (0.36 - mist_luma) * 0.28, 0.58, 0.88)
    fine_alpha = (mist * (0.030 + 0.040 * blue) + veil * 0.012)[:, :, np.newaxis]
    fine_alpha = np.clip(fine_alpha * float(fine_alpha_scale), 0.0, float(fine_alpha_max))
    fine_color = np.clip(mist_tint * mist_boost + ca * 0.018, 0.0, 1.0)
    paint_rgb = paint_rgb * (1.0 - fine_alpha) + fine_color * fine_alpha

    rng = np.random.RandomState(seed + 989)
    nano = rng.random((h, w)).astype(np.float32)
    nano_noise = _norm01(multi_scale_noise((h, w), [1, 2, 4], [0.50, 0.32, 0.18], seed + 991))
    nano_mask = np.clip(
        np.where(nano > 0.55, (nano - 0.55) / 0.45, 0.0) * 0.60
        + np.where(nano_noise > 0.50, (nano_noise - 0.50) / 0.50, 0.0) * 0.40,
        0.0,
        1.0,
    )
    nano_selector = np.floor(_norm01(nano + nano_noise * 0.65) * len(flakes)).astype(np.int32)
    nano_selector = np.clip(nano_selector, 0, len(flakes) - 1)
    nano_color = np.clip(flakes[nano_selector] * 0.86 + cb.reshape(3) * 0.10 + ca.reshape(3) * 0.04, 0.0, 1.0)
    nano_alpha = (nano_mask * (0.075 + 0.055 * np.clip(float(carrier_chroma), 0.0, 1.2)))[:, :, np.newaxis]
    paint_rgb = np.clip(paint_rgb * (1.0 - nano_alpha) + nano_color * nano_alpha, 0.0, 1.0)
    nano_luma = ((nano_noise - 0.5) * 0.10 + (nano_mask - 0.5) * 0.045)[:, :, np.newaxis]
    paint_rgb = np.clip(paint_rgb * (1.0 + nano_luma), 0.0, 1.0)

    # Add tiny same-hue pearl noise so the finish still has richness without
    # showing obvious blue/purple pixels in the diffuse texture.
    pearl = (_norm01(multi_scale_noise((h, w), [4, 8, 16], [0.45, 0.35, 0.20], seed + 977)) - 0.5)
    paint_rgb = np.clip(paint_rgb + ca * pearl[:, :, np.newaxis] * 0.045, 0.0, 1.0)

    blend = np.clip(float(pm) * 0.96, 0.0, 1.0)
    result = paint * (1.0 - mask3 * blend) + paint_rgb * (mask3 * blend)
    result = np.clip(result + bb * 0.09 * mask3 * float(pm), 0.0, 1.0)
    return result.astype(np.float32)


def spec_hyperflip_core(
    shape, mask, seed, sm,
    density=0.42,
    fine_density=0.18,
    orientation=0.0,
    turbulence=1.0,
    matte_rough=205.0,
    flash_metal=252.0,
    flash_rough=15.0,
    base_clearcoat=194.0,
    flash_clearcoat=16.0,
):
    h, w = shape[:2] if len(shape) > 2 else shape
    flash, mist, veil, macro, blue, micro = _hyperflip_fields(
        (h, w), seed, density, orientation, turbulence, fine_density
    )
    mask = mask.astype(np.float32)
    strength = np.clip(float(sm), 0.25, 2.0)

    glint = np.clip((flash * 0.82 + mist * 0.18 + veil * 0.24) * strength, 0.0, 1.0)
    M = np.clip(8.0 + glint * (float(flash_metal) - 8.0) + macro * 10.0, 0.0, 255.0)
    R = np.clip(float(matte_rough) - glint * (float(matte_rough) - float(flash_rough)) + (blue - 0.5) * 12.0, 15.0, 255.0)
    CC = np.clip(
        float(base_clearcoat) - glint * (float(base_clearcoat) - float(flash_clearcoat)) + macro * 10.0,
        16.0,
        235.0,
    )

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.where(mask > 0.01, np.clip(R, 15, 255), 0).astype(np.uint8)
    spec[:, :, 2] = np.where(mask > 0.01, np.clip(CC, 16, 255), 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


HYPERFLIP_PRESETS = {
    "hyperflip_red_blue": {
        "color_a": (1.0, 0.02, 0.015),
        "color_b": (0.020, 0.38, 1.0),
        "flake_colors": [(0.020, 0.38, 1.0), (0.05, 0.62, 1.0)],
        "density": 0.20,
        "fine_density": 0.30,
        "orientation": 0.18,
        "turbulence": 1.22,
        "base_bias": 0.70,
        "carrier_chroma": 1.00,
        "carrier_alpha_scale": 3.60,
        "carrier_alpha_max": 0.74,
        "fine_alpha_scale": 0.92,
        "fine_alpha_max": 0.16,
        "matte_rough": 214.0,
        "flash_metal": 132.0,
        "flash_rough": 54.0,
        "flash_clearcoat": 118.0,
    },
    "hyperflip_pink_black": {
        "color_a": (1.0, 0.04, 0.55),
        "color_b": (0.004, 0.004, 0.010),
        "flake_colors": [(0.004, 0.004, 0.010), (0.18, 0.03, 0.16)],
        "density": 0.28,
        "fine_density": 0.20,
        "orientation": 1.05,
        "turbulence": 1.35,
        "base_bias": 0.76,
        "carrier_chroma": 0.12,
        "carrier_alpha_scale": 0.96,
        "fine_alpha_scale": 0.26,
        "fine_alpha_max": 0.09,
        "matte_rough": 190.0,
        "flash_metal": 255.0,
        "flash_rough": 15.0,
    },
    "hyperflip_orange_cyan": {
        "color_a": (1.0, 0.34, 0.00),
        "color_b": (0.00, 0.88, 1.0),
        "flake_colors": [(0.00, 0.88, 1.0), (0.04, 0.50, 1.0)],
        "density": 0.22,
        "fine_density": 0.26,
        "orientation": -0.62,
        "turbulence": 1.10,
        "base_bias": 0.68,
        "carrier_chroma": 0.52,
        "carrier_alpha_scale": 1.75,
        "carrier_alpha_max": 0.46,
        "fine_alpha_scale": 0.62,
    },
    "hyperflip_lime_purple": {
        "color_a": (0.35, 1.0, 0.02),
        "color_b": (0.55, 0.03, 1.0),
        "flake_colors": [(0.55, 0.03, 1.0), (0.82, 0.03, 0.88)],
        "density": 0.25,
        "fine_density": 0.25,
        "orientation": 0.72,
        "turbulence": 1.28,
        "base_bias": 0.64,
        "carrier_chroma": 0.48,
        "carrier_alpha_scale": 1.55,
        "carrier_alpha_max": 0.42,
        "fine_alpha_scale": 0.58,
    },
    "hyperflip_purple_gold": {
        "color_a": (0.30, 0.05, 0.70),
        "color_b": (1.0, 0.70, 0.05),
        "flake_colors": [(1.0, 0.70, 0.05), (1.0, 0.92, 0.24)],
        "density": 0.18,
        "fine_density": 0.29,
        "orientation": -0.18,
        "turbulence": 1.18,
        "carrier_chroma": 0.82,
        "carrier_alpha_scale": 2.35,
        "carrier_alpha_max": 0.58,
        "fine_alpha_scale": 0.84,
        "fine_alpha_max": 0.16,
        "matte_rough": 208.0,
        "flash_metal": 148.0,
        "flash_rough": 50.0,
        "flash_clearcoat": 104.0,
    },
    "hyperflip_electric_blue_copper": {
        "color_a": (0.00, 0.18, 1.0),
        "color_b": (1.0, 0.42, 0.06),
        "flake_colors": [(1.0, 0.42, 0.06), (1.0, 0.72, 0.10)],
        "density": 0.17,
        "fine_density": 0.30,
        "orientation": 0.34,
        "turbulence": 1.16,
        "carrier_chroma": 0.86,
        "carrier_alpha_scale": 2.28,
        "carrier_alpha_max": 0.56,
        "fine_alpha_scale": 0.82,
        "fine_alpha_max": 0.15,
        "matte_rough": 210.0,
        "flash_metal": 140.0,
        "flash_rough": 52.0,
        "flash_clearcoat": 110.0,
    },
    "hyperflip_bronze_teal": {
        "color_a": (0.72, 0.36, 0.12),
        "color_b": (0.00, 0.86, 0.78),
        "flake_colors": [(0.00, 0.86, 0.78), (0.10, 0.58, 1.0)],
        "density": 0.18,
        "fine_density": 0.27,
        "orientation": -0.86,
        "turbulence": 1.20,
        "carrier_chroma": 0.76,
        "carrier_alpha_scale": 2.10,
        "carrier_alpha_max": 0.52,
        "fine_alpha_scale": 0.72,
        "fine_alpha_max": 0.14,
        "matte_rough": 206.0,
        "flash_metal": 150.0,
        "flash_rough": 48.0,
        "flash_clearcoat": 104.0,
    },
    "hyperflip_silver_violet": {
        "color_a": (0.70, 0.72, 0.76),
        "color_b": (0.66, 0.06, 1.0),
        "flake_colors": [(0.66, 0.06, 1.0), (0.16, 0.42, 1.0)],
        "density": 0.16,
        "fine_density": 0.24,
        "orientation": 0.92,
        "turbulence": 1.08,
        "carrier_chroma": 0.72,
        "carrier_alpha_scale": 1.95,
        "carrier_alpha_max": 0.46,
        "fine_alpha_scale": 0.58,
        "fine_alpha_max": 0.12,
        "matte_rough": 192.0,
        "flash_metal": 118.0,
        "flash_rough": 58.0,
        "flash_clearcoat": 124.0,
    },
    "hyperflip_crimson_prism": {
        "color_a": (0.95, 0.02, 0.05),
        "color_b": (0.00, 0.86, 1.0),
        "flake_colors": [(0.00, 0.86, 1.0), (1.0, 0.74, 0.06), (0.72, 0.05, 1.0)],
        "density": 0.16,
        "fine_density": 0.34,
        "orientation": -0.42,
        "turbulence": 1.24,
        "carrier_chroma": 0.92,
        "carrier_alpha_scale": 2.32,
        "carrier_alpha_max": 0.54,
        "fine_alpha_scale": 0.86,
        "fine_alpha_max": 0.15,
        "matte_rough": 212.0,
        "flash_metal": 138.0,
        "flash_rough": 54.0,
        "flash_clearcoat": 116.0,
    },
    "hyperflip_midnight_opal": {
        "color_a": (0.015, 0.025, 0.12),
        "color_b": (1.0, 0.46, 0.08),
        "flake_colors": [(1.0, 0.46, 0.08), (0.42, 1.0, 0.05), (1.0, 0.05, 0.72)],
        "density": 0.18,
        "fine_density": 0.36,
        "orientation": 1.24,
        "turbulence": 1.30,
        "carrier_chroma": 0.98,
        "carrier_alpha_scale": 2.75,
        "carrier_alpha_max": 0.62,
        "fine_alpha_scale": 0.92,
        "fine_alpha_max": 0.17,
        "matte_rough": 220.0,
        "flash_metal": 154.0,
        "flash_rough": 46.0,
        "flash_clearcoat": 96.0,
    },
}


def _make_spec(preset):
    def _spec(shape, mask, seed, sm):
        return spec_hyperflip_core(
            shape, mask, seed, sm,
            density=preset.get("density", 0.42),
            fine_density=preset.get("fine_density", 0.18),
            orientation=preset.get("orientation", 0.0),
            turbulence=preset.get("turbulence", 1.0),
            matte_rough=preset.get("matte_rough", 205.0),
            flash_metal=preset.get("flash_metal", 252.0),
            flash_rough=preset.get("flash_rough", 15.0),
            base_clearcoat=preset.get("base_clearcoat", 194.0),
            flash_clearcoat=preset.get("flash_clearcoat", 16.0),
        )
    return _spec


def _make_paint(preset):
    def _paint(paint, shape, mask, seed, pm, bb):
        return paint_hyperflip_core(
            paint, shape, mask, seed, pm, bb,
            color_a=preset["color_a"],
            color_b=preset["color_b"],
            flake_colors=preset.get("flake_colors"),
            density=preset.get("density", 0.42),
            fine_density=preset.get("fine_density", 0.18),
            orientation=preset.get("orientation", 0.0),
            turbulence=preset.get("turbulence", 1.0),
            base_bias=preset.get("base_bias", 0.66),
            carrier_chroma=preset.get("carrier_chroma", 0.34),
            carrier_alpha_scale=preset.get("carrier_alpha_scale", 1.0),
            carrier_alpha_max=preset.get("carrier_alpha_max", 0.32),
            fine_alpha_scale=preset.get("fine_alpha_scale", 0.42),
            fine_alpha_max=preset.get("fine_alpha_max", 0.15),
        )
    return _paint


HYPERFLIP_MONOLITHICS = {
    f"cx_{name}": (_make_spec(preset), _make_paint(preset))
    for name, preset in HYPERFLIP_PRESETS.items()
}
