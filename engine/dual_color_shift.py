"""
Dual Color Shift Engine — DEPRECATED (merged into COLORSHOXX)
==============================================================
All dual-shift finishes are now part of the unified COLORSHOXX category.
Old dualshift_* IDs are mapped to cx_* equivalents for backward compat.
The engine code is still used by COLORSHOXX for angle-dependent shifts.

Creates GENUINE angle-dependent color shifting using iRacing's PBR spec map.
This is how real ChromaFlair / Spectraflair paint works, simulated in PBR.
"""

import numpy as np
import cv2

# Import from sibling modules
try:
    from engine.core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec, rgb_to_hsv_array
except ImportError:
    from core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec, rgb_to_hsv_array

def _normalize01(arr):
    """Normalize an array to 0-1, preserving shape and dtype friendliness."""
    arr = np.asarray(arr, dtype=np.float32)
    mn, mx = arr.min(), arr.max()
    if mx <= mn:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - mn) / (mx - mn + 1e-8)).astype(np.float32)


def _dual_shift_micro_detail(shape, seed, turbulence=1.0, style="sweep"):
    """Fine-scale directional detail so COLORSHOXX duos read at 2048 like
    layered pigment/flakes instead of one blunt macro gradient."""
    h, w = shape
    yn = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    xn = np.arange(w, dtype=np.float32).reshape(1, -1) / max(w - 1, 1)
    rng = np.random.RandomState(seed + 8600)
    turbulence = float(max(0.25, turbulence))

    detail = np.zeros((h, w), dtype=np.float32)
    for i in range(6):
        ang = rng.uniform(0.0, 2.0 * np.pi)
        freq = rng.uniform(10.0, 34.0) * (0.95 + 0.15 * min(turbulence, 1.8))
        proj = yn * np.cos(ang) + xn * np.sin(ang)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        ribbon = 1.0 - np.abs(np.sin(proj * np.pi * freq + phase))
        detail += np.clip(ribbon, 0.0, 1.0) ** (1.6 + 0.25 * (i % 3))

    micro_noise = multi_scale_noise(shape, [4, 8, 16, 32], [0.16, 0.24, 0.34, 0.26], seed + 8611)
    cross_noise = multi_scale_noise(shape, [6, 12, 24], [0.40, 0.35, 0.25], seed + 8623)
    detail = detail / max(float(detail.max()), 1e-8)

    cy = 0.5 + rng.uniform(-0.04, 0.04)
    cx = 0.5 + rng.uniform(-0.04, 0.04)
    dist = np.sqrt((yn - cy) ** 2 + (xn - cx) ** 2)
    theta = np.arctan2(yn - cy, xn - cx + 1e-8)

    if style == "vortex":
        spiral = 1.0 - np.abs(np.sin((theta * (6.5 + 0.8 * turbulence) + dist * (24.0 + 6.0 * turbulence)) * np.pi))
        detail = detail * 0.65 + np.clip(spiral, 0.0, 1.0) * 0.35
    elif style == "arc":
        arc = 1.0 - np.abs(np.sin((dist * (28.0 + 5.0 * turbulence) + theta * 1.4) * np.pi))
        detail = detail * 0.70 + np.clip(arc, 0.0, 1.0) * 0.30
    elif style == "split":
        split = 1.0 - np.abs(np.sin((yn * 13.0 - xn * 17.0 + micro_noise * 0.35) * np.pi))
        detail = detail * 0.72 + np.clip(split, 0.0, 1.0) * 0.28
    elif style == "faceted":
        facet = np.abs(np.sin((yn * 18.0 + xn * 22.0) * np.pi)) * np.abs(np.cos((yn * 21.0 - xn * 15.0) * np.pi))
        detail = detail * 0.68 + facet.astype(np.float32) * 0.32
    elif style == "banded":
        band = 1.0 - np.abs(np.sin((yn * 11.0 + micro_noise * 0.25) * np.pi * (1.6 + 0.2 * turbulence)))
        detail = detail * 0.76 + np.clip(band, 0.0, 1.0) * 0.24

    detail = _normalize01(
        detail * 0.74
        + _normalize01(micro_noise) * 0.16
        + _normalize01(cross_noise) * 0.10
    )
    return detail.astype(np.float32)


def _dual_shift_field(shape, seed, flow_complexity=3, style="sweep",
                      seed_offset=0, edge_bias=0.0, turbulence=1.0,
                      band_sharpness=0.0):
    """Generate the angle/flow field that drives a dual shift's personality.

    The original version used one generic sweep for every COLORSHOXX duo,
    which made the family feel like the same finish with different hues.
    Presets now vary the geometry itself so the flip character changes too.
    """
    h, w = shape
    yn = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    xn = np.arange(w, dtype=np.float32).reshape(1, -1) / max(w - 1, 1)
    rng = np.random.RandomState(seed + seed_offset + 8000)
    angles = rng.uniform(0, 2 * np.pi, 8)
    turbulence = float(max(0.25, turbulence))
    # Primary diagonal sweep
    primary = (np.cos(angles[0]) * yn + np.sin(angles[0]) * xn)
    secondary = (np.cos(angles[1]) * yn + np.sin(angles[1]) * xn)
    field = primary * 0.30
    # Secondary cross-flow
    field = field + secondary * (0.18 + 0.05 * min(turbulence, 1.6))
    cy = 0.45 + rng.uniform(-0.10, 0.10)
    cx = 0.50 + rng.uniform(-0.10, 0.10)
    dist = np.sqrt((yn - cy)**2 + (xn - cx)**2)
    theta = np.arctan2(yn - cy, xn - cx + 1e-8)

    if style == "arc":
        field = field + (0.52 - dist) * 0.28
        field = field + np.sin(theta * 1.8 + angles[2]) * 0.10
    elif style == "split":
        split = primary * 1.15 + secondary * 0.20
        field = field + np.tanh((split - 0.52) * 5.5) * 0.22
        field = field + np.sin(split * np.pi * (1.7 + 0.2 * turbulence) + angles[2]) * 0.08
    elif style == "faceted":
        field = field + np.abs(np.sin(primary * np.pi * 2.6 + angles[2])) * 0.16
        field = field + np.abs(np.cos(secondary * np.pi * 2.1 + angles[3])) * 0.12
        field = field + (0.48 - dist) * 0.10
    elif style == "banded":
        bands = np.sin(primary * np.pi * (2.4 + 0.7 * turbulence) + angles[2])
        field = field + bands * 0.22
        field = field + np.cos((secondary + dist * 0.6) * np.pi * 1.8 + angles[3]) * 0.08
    elif style == "vortex":
        spiral = theta / (2 * np.pi) + dist * (1.35 + 0.2 * turbulence)
        field = field + np.sin(spiral * np.pi * 2.3 + angles[2]) * 0.22
        field = field + (0.50 - dist) * 0.16
    else:
        field = field + dist * 0.18
    if flow_complexity >= 2:
        field = field + dist * 0.10
        field = field + np.sin((theta + dist * np.pi) * (1.0 + 0.15 * turbulence)) * 0.04
    if flow_complexity >= 3:
        for i in range(3):
            freq = 1.2 + rng.uniform(-0.3, 0.5)
            phase = angles[2 + i]
            wave = np.sin((yn * np.cos(phase) + xn * np.sin(phase)) * freq * np.pi)
            field = field + wave * ((0.10 - i * 0.02) * min(turbulence, 1.5))
        noise = multi_scale_noise(shape, [16, 32, 64], [0.25, 0.40, 0.35], seed + 8001)
        field = field + noise * (0.03 + 0.02 * min(turbulence, 1.5))
    if flow_complexity >= 4:
        interference = np.cos((primary - secondary * 0.7 + dist) * np.pi * (2.0 + 0.3 * turbulence) + angles[6])
        field = field + interference * 0.05
    if flow_complexity >= 5:
        cellular = np.abs(np.sin((primary + secondary + dist * 1.5) * np.pi * 2.5 + angles[7]))
        field = field + cellular * 0.06

    if edge_bias:
        edge = np.maximum(np.maximum(xn, yn), np.maximum(1.0 - xn, 1.0 - yn))
        field = field + _normalize01(edge) * float(edge_bias)

    detail_strength = 0.20 + 0.04 * min(turbulence, 1.6)
    if style == "banded":
        detail_strength = 0.16
    elif style == "sweep":
        detail_strength = 0.18
    elif style == "vortex":
        detail_strength = 0.28
    micro = _dual_shift_micro_detail(shape, seed + seed_offset, turbulence=turbulence, style=style)
    field = _normalize01(field * (1.0 - detail_strength) + micro * detail_strength)

    field = _normalize01(field)
    if band_sharpness > 0:
        centered = (field - 0.5) * (1.0 + band_sharpness * 4.0)
        field = 0.5 + np.tanh(centered) * 0.5
        field = _normalize01(field)

    return field.astype(np.float32)


def _dual_shift_flake(shape, seed, cell_size=5):
    """Micro-flake noise for per-particle variation."""
    h, w = shape
    rng = np.random.RandomState(seed)
    ch, cw = max(1, h // cell_size), max(1, w // cell_size)
    tile = rng.random((ch, cw)).astype(np.float32)
    flake = cv2.resize(tile, (w, h), interpolation=cv2.INTER_NEAREST)
    return flake


def spec_dual_shift(shape, mask, seed, sm, color_a=None, color_b=None,
                    shift_intensity=1.0, M_low=80, M_high=245, R_base=15,
                    CC_base=16, flow_complexity=3, field_style="sweep",
                    field_seed_offset=0, edge_bias=0.0, turbulence=1.0,
                    band_sharpness=0.0, flake_cell_size=5,
                    roughness_variance=8, clearcoat_gain=15,
                    metal_noise=4, rough_noise=3):
    """Generate spec map for dual color shift.

    The spec map creates a metallic gradient that works WITH the paint color gradient:
    - Where paint is Color A (face-on zones): M is lower -- paint color holds
    - Where paint is Color B (edge zones): M is higher -- Fresnel kicks in
    - The transition: smooth M gradient creates the viewing-angle-dependent shift

    Args:
        color_a, color_b: RGB tuples (0-1) — the two shift colors
        shift_intensity: 0-1 how dramatic the shift is
        M_low: metallic in face-on zones (lower = more paint color)
        M_high: metallic in edge zones (higher = more Fresnel/env reflection)
    """
    h, w = shape
    ds = max(1, min(h, w) // 512)
    sh, sw = max(64, h // ds), max(64, w // ds)

    # Generate panel orientation field
    field = _dual_shift_field(
        (sh, sw),
        seed,
        flow_complexity=flow_complexity,
        style=field_style,
        seed_offset=field_seed_offset,
        edge_bias=edge_bias,
        turbulence=turbulence,
        band_sharpness=band_sharpness,
    )

    # Mask resize
    mask_s = mask
    if ds > 1:
        mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR)

    # Metallic gradient: low in face-on (A color holds), high at edges (B + Fresnel)
    M_range = (M_high - M_low) * shift_intensity
    M_arr = M_low + field * M_range

    # Roughness: very smooth for maximum color clarity
    scaled_cell = max(2, flake_cell_size * sh // max(h, 1)) if ds > 1 else flake_cell_size
    flake = _dual_shift_flake((sh, sw), seed + 50 + field_seed_offset, cell_size=max(2, scaled_cell))
    R_arr = R_base + flake * roughness_variance * sm  # Tight range — stay smooth

    # Clearcoat: max gloss everywhere for vivid color
    CC_arr = np.full((sh, sw), CC_base, dtype=np.float32) + field * clearcoat_gain * shift_intensity

    # Light noise for organic feel
    m_noise = multi_scale_noise((sh, sw), [16, 32], [0.5, 0.5], seed + 8200)
    M_arr = M_arr + m_noise * metal_noise * sm
    r_noise = multi_scale_noise((sh, sw), [16, 32], [0.5, 0.5], seed + 8210)
    R_arr = R_arr + r_noise * rough_noise * sm

    spec = np.zeros((sh, sw, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(M_arr * mask_s, 0, 255).astype(np.uint8)
    # Iron rule: R >= 15 where M < 240
    R_clamped = np.where(M_arr < 240, np.maximum(R_arr, 15), R_arr)
    spec[:, :, 1] = np.clip(R_clamped * mask_s, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC_arr * mask_s, 16, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask_s * 255, 0, 255).astype(np.uint8)

    # Upscale
    if ds > 1:
        spec_full = np.zeros((h, w, 4), dtype=np.uint8)
        for ch in range(4):
            spec_full[:, :, ch] = cv2.resize(spec[:, :, ch].astype(np.float32), (w, h),
                                              interpolation=cv2.INTER_LINEAR).astype(np.uint8)
        spec = spec_full

    return spec


def paint_dual_shift(paint, shape, mask, seed, pm, bb,
                     color_a=(1.0, 0.2, 0.6),   # Hot pink default
                     color_b=(1.0, 0.9, 0.1),   # Yellow default
                     shift_intensity=1.0, blend_strength=0.85,
                     flow_complexity=3, field_style="sweep",
                     field_seed_offset=0, edge_bias=0.0, turbulence=1.0,
                     band_sharpness=0.0, transition_mid=0.3,
                     transition_width=0.4, transition_gamma=1.0,
                     flake_cell_size=5, flake_hue_strength=0.03):
    """Apply dual color shift to paint — WRITES different colors into the paint TGA.

    This is the magic: we don't just tint. We REPLACE paint colors with a gradient
    from Color A to Color B based on the panel orientation field.

    Face-on panels get Color A. Edge panels get Color B. The transition is smooth.
    Combined with the matching spec map, this creates GENUINE color shifting in iRacing.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]

    h, w = shape

    # Get panel orientation field (same one spec uses — critical for coordination)
    ds = max(1, min(h, w) // 512)
    sh, sw = max(64, h // ds), max(64, w // ds)
    field = _dual_shift_field(
        (sh, sw),
        seed,
        flow_complexity=flow_complexity,
        style=field_style,
        seed_offset=field_seed_offset,
        edge_bias=edge_bias,
        turbulence=turbulence,
        band_sharpness=band_sharpness,
    )
    if ds > 1:
        field = cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR)
    detail = _dual_shift_micro_detail(
        (sh, sw),
        seed + 71 + field_seed_offset,
        turbulence=turbulence,
        style=field_style,
    )
    if ds > 1:
        detail = cv2.resize(detail, (w, h), interpolation=cv2.INTER_LINEAR)

    # Build color gradient from A to B driven by the field
    ca = np.array(color_a, dtype=np.float32)
    cb = np.array(color_b, dtype=np.float32)

    # Stronger contrast — push the field toward 0 and 1 extremes
    # This creates CLEARER zones of Color A vs Color B
    width = max(0.08, float(transition_width))
    mid = float(transition_mid)
    t = np.clip((field - (mid - width * 0.5)) / width, 0, 1)
    t = t * t * (3.0 - 2.0 * t)  # Smoothstep for clean edges
    if transition_gamma != 1.0:
        t = np.power(np.clip(t, 0, 1), max(0.35, float(transition_gamma)))
    t = np.clip(t * shift_intensity, 0, 1)
    detail_shift = (detail - 0.5) * (0.16 + 0.08 * np.clip(shift_intensity, 0, 1))
    t = np.clip(t + detail_shift, 0, 1)

    # Create the color gradient
    shift_r = ca[0] * (1.0 - t) + cb[0] * t
    shift_g = ca[1] * (1.0 - t) + cb[1] * t
    shift_b = ca[2] * (1.0 - t) + cb[2] * t

    # Micro-flake sparkle for realism — tiny per-flake color variation
    flake = _dual_shift_flake(shape, seed + 50 + field_seed_offset, cell_size=max(2, int(flake_cell_size)))
    flake_hue = flake * flake_hue_strength * shift_intensity  # Very subtle per-flake hue jitter
    rng = np.random.RandomState(seed + 9050 + field_seed_offset)
    nano = rng.random((h, w)).astype(np.float32)
    nano_a = np.where(nano > 0.64, (nano - 0.64) / 0.36, 0.0).astype(np.float32)
    nano_b = np.where(nano < 0.34, (0.34 - nano) / 0.34, 0.0).astype(np.float32)
    micro_noise = multi_scale_noise(shape, [1, 2, 4], [0.48, 0.34, 0.18], seed + 9060 + field_seed_offset)
    nano_carrier = np.clip(nano_a * 0.52 + nano_b * 0.36 + micro_noise * 0.22, 0, 1)

    # Blend with existing paint
    mask3 = mask[:, :, np.newaxis]
    blend = np.clip(blend_strength * pm, 0, 1)

    shift_rgb = np.stack([
        np.clip(shift_r + flake_hue * 0.5, 0, 1),
        np.clip(shift_g + flake_hue * 0.3, 0, 1),
        np.clip(shift_b - flake_hue * 0.2, 0, 1),
    ], axis=2)
    opponent = cb.reshape(1, 1, 3) * (0.78 + nano_b[:, :, np.newaxis] * 0.18)
    primary = ca.reshape(1, 1, 3) * (0.78 + nano_a[:, :, np.newaxis] * 0.18)
    nano_color = np.where(nano_a[:, :, np.newaxis] > nano_b[:, :, np.newaxis], primary, opponent)
    nano_alpha = np.clip((0.14 + 0.10 * shift_intensity) * nano_carrier, 0, 0.28)[:, :, np.newaxis]
    shift_rgb = np.clip(shift_rgb * (1.0 - nano_alpha) + nano_color * nano_alpha, 0, 1)
    pigment_grain = ((nano_carrier - 0.5) * 0.30 + (micro_noise - 0.5) * 0.14)[:, :, np.newaxis]
    shift_rgb = np.clip(shift_rgb * (1.0 + pigment_grain) + nano_color * np.clip(nano_carrier[:, :, np.newaxis] - 0.72, 0, 1) * 0.08, 0, 1)

    paint[:, :, :3] = paint[:, :, :3] * (1.0 - blend * mask3) + shift_rgb * blend * mask3

    # Brightness boost
    paint = np.clip(paint + bb * 0.2 * mask3 * pm, 0, 1)

    return paint.astype(np.float32)


# Pre-built dramatic shift presets
DUAL_SHIFT_PRESETS = {
    "custom": {
        "name": "Custom Prism Shift",
        "color_a": (0.04, 0.08, 0.18),
        "color_b": (0.96, 0.08, 0.72),
        "M_low": 72, "M_high": 246,
        "field_style": "faceted", "flow_complexity": 5, "field_seed_offset": 71,
        "edge_bias": 0.09, "turbulence": 1.24, "transition_mid": 0.44,
        "transition_width": 0.22, "transition_gamma": 1.04,
        "blend_strength": 0.88, "flake_cell_size": 3, "band_sharpness": 0.24,
        "desc": "Deep ink base with magenta prism flake - default custom COLORSHOXX carrier"
    },
    "pink_to_gold": {
        "name": "Pink  to Gold",
        "color_a": (1.0, 0.2, 0.55),   # Hot pink
        "color_b": (1.0, 0.85, 0.15),  # Rich gold
        "M_low": 60, "M_high": 245,
        "field_style": "arc", "flow_complexity": 4, "field_seed_offset": 111,
        # 2026-04-20 HEENAN HARDMODE-CX-1 (Bockwinkel) — soften the arc bloom
        # so the pink->gold flip feels organic instead of fighting the
        # blue_to_orange split. Wider transition + lower gamma + larger
        # flakes = softer molten roll instead of a hard banded line.
        "edge_bias": 0.08, "turbulence": 1.15, "transition_mid": 0.34,
        "transition_width": 0.40, "transition_gamma": 0.85,
        "blend_strength": 0.90, "flake_cell_size": 5, "band_sharpness": 0.18,
        "desc": "Hot pink face-on, shifts to rich gold at edges — soft molten arc bloom"
    },
    "blue_to_orange": {
        "name": "Blue  to Orange",
        "color_a": (0.1, 0.3, 0.9),    # Deep blue
        "color_b": (1.0, 0.5, 0.05),   # Vivid orange
        "M_low": 70, "M_high": 240,
        "field_style": "split", "flow_complexity": 4, "field_seed_offset": 223,
        "edge_bias": 0.05, "turbulence": 0.95, "transition_mid": 0.49,
        "transition_width": 0.20, "transition_gamma": 1.18,
        "blend_strength": 0.84, "flake_cell_size": 5, "band_sharpness": 0.34,
        "desc": "Deep blue face-on, shifts to vivid orange at edges — complementary shift"
    },
    "purple_to_green": {
        "name": "Purple  to Green",
        "color_a": (0.6, 0.1, 0.8),    # Rich purple
        "color_b": (0.1, 0.9, 0.3),    # Vivid green
        "M_low": 80, "M_high": 245,
        "field_style": "faceted", "flow_complexity": 5, "field_seed_offset": 337,
        # 2026-04-20 HEENAN HARDMODE-CX-2 (Bockwinkel) — faceted geometry
        # already fragments the panel; widen transition + drop sharpness so
        # this reads as a Mystichrome color-wash rather than as the same
        # geometry-fight ice_fire is doing. Tighter flake grain and lower
        # turbulence to differentiate from ice_fire's chaos.
        "edge_bias": 0.04, "turbulence": 1.08, "transition_mid": 0.41,
        "transition_width": 0.28, "transition_gamma": 1.08,
        "blend_strength": 0.86, "flake_cell_size": 3, "band_sharpness": 0.12,
        "desc": "Royal purple face-on, shifts to electric green — Mystichrome color wash through faceted breaks"
    },
    "teal_to_magenta": {
        "name": "Teal  to Magenta",
        "color_a": (0.0, 0.8, 0.7),    # Teal
        "color_b": (0.9, 0.1, 0.5),    # Magenta
        "M_low": 65, "M_high": 240,
        "field_style": "vortex", "flow_complexity": 4, "field_seed_offset": 449,
        # 2026-04-20 HEENAN HARDMODE-CX-3 (Bockwinkel) — vortex is the
        # ONLY spiral geometry in the family. Lean hard into it: tighter
        # transition + sharper bands + maximum turbulence pump up the
        # spiral structure. Larger flakes amplify the spiral arms.
        "edge_bias": 0.07, "turbulence": 1.30, "transition_mid": 0.46,
        "transition_width": 0.20, "transition_gamma": 0.96,
        "blend_strength": 0.88, "flake_cell_size": 5, "band_sharpness": 0.28,
        "desc": "Cool teal face-on, shifts to hot magenta in tight spiral arms — the only vortex duo"
    },
    "red_to_cyan": {
        "name": "Red  to Cyan",
        "color_a": (0.9, 0.1, 0.1),    # Pure red
        "color_b": (0.1, 0.9, 0.9),    # Pure cyan
        "M_low": 75, "M_high": 245,
        "field_style": "banded", "flow_complexity": 4, "field_seed_offset": 557,
        # 2026-04-20 HEENAN HARDMODE-CX-4 (Bockwinkel) — red and cyan are
        # opposite on the colour wheel; make this the EXTREME-stripes finish.
        # Razor-sharp bands, lowest turbulence in the family (stable rails),
        # gamma above 1.0 for hard-edge contrast.
        "edge_bias": 0.02, "turbulence": 0.90, "transition_mid": 0.52,
        "transition_width": 0.14, "transition_gamma": 1.32,
        "blend_strength": 0.87, "flake_cell_size": 5, "band_sharpness": 0.40,
        "desc": "Fire red face-on, ice cyan in razor-stable bands — extreme complementary stripes"
    },
    "sunset": {
        "name": "Sunset Shift",
        "color_a": (1.0, 0.3, 0.0),    # Orange
        "color_b": (0.6, 0.0, 0.4),    # Deep purple
        "M_low": 70, "M_high": 235,
        "field_style": "sweep", "flow_complexity": 3, "field_seed_offset": 661,
        # 2026-04-20 HEENAN HARDMODE-CX-5 (Bockwinkel) — real sunsets blend
        # smoothly. Drop ALL the sharpness, drop turbulence below the rest of
        # the family, lower gamma so the orange dominates the on-axis face
        # like late golden-hour light. The atmospheric anchor of the family.
        "edge_bias": 0.09, "turbulence": 0.85, "transition_mid": 0.36,
        "transition_width": 0.30, "transition_gamma": 0.78,
        "blend_strength": 0.82, "flake_cell_size": 5, "band_sharpness": 0.04,
        "desc": "Sunset orange dominates face-on, blends smoothly into twilight purple — the calmest, most atmospheric duo"
    },
    "emerald_ruby": {
        "name": "Emerald  to Ruby",
        "color_a": (0.0, 0.7, 0.3),    # Emerald
        "color_b": (0.8, 0.05, 0.15),  # Ruby
        "M_low": 80, "M_high": 240,
        "field_style": "arc", "flow_complexity": 5, "field_seed_offset": 773,
        # 2026-04-20 HEENAN HARDMODE-CX-6 (Bockwinkel) — second arc duo.
        # Differentiate from pink_to_gold by tightening band sharpness and
        # shrinking flake cells. Jewel tones want geometric precision; arc
        # geometry + sharp bands + tiny flakes = gem facets catching light.
        "edge_bias": 0.03, "turbulence": 1.12, "transition_mid": 0.45,
        "transition_width": 0.22, "transition_gamma": 1.10,
        "blend_strength": 0.80, "flake_cell_size": 3, "band_sharpness": 0.32,
        "desc": "Emerald face-on, shifts to deep ruby through sharp jewel-facet arcs — second arc duo, geometric vs pink_to_gold's bloom"
    },
    "ice_fire": {
        "name": "Ice  to Fire",
        "color_a": (0.7, 0.85, 1.0),   # Ice blue/white
        "color_b": (1.0, 0.2, 0.0),    # Fire orange/red
        "M_low": 60, "M_high": 250,
        "field_style": "faceted", "flow_complexity": 5, "field_seed_offset": 881,
        "edge_bias": 0.11, "turbulence": 1.30, "transition_mid": 0.43,
        "transition_width": 0.15, "transition_gamma": 1.26,
        "blend_strength": 0.92, "flake_cell_size": 3, "band_sharpness": 0.30,
        "desc": "Frozen ice face-on, shifts to blazing fire — maximum temperature contrast"
    },
}


def build_dual_shift_monolithics():
    """Build monolithic registry entries for all dual shift presets.
    Returns dict of {id: (spec_fn, paint_fn)} tuples ready for MONOLITHIC_REGISTRY."""
    entries = {}
    for preset_id, preset in DUAL_SHIFT_PRESETS.items():
        _ca = preset['color_a']
        _cb = preset['color_b']
        _ml = preset['M_low']
        _mh = preset['M_high']
        _field_style = preset.get('field_style', 'sweep')
        _flow_complexity = preset.get('flow_complexity', 3)
        _field_seed_offset = preset.get('field_seed_offset', 0)
        _edge_bias = preset.get('edge_bias', 0.0)
        _turbulence = preset.get('turbulence', 1.0)
        _band_sharpness = preset.get('band_sharpness', 0.0)
        _transition_mid = preset.get('transition_mid', 0.3)
        _transition_width = preset.get('transition_width', 0.4)
        _transition_gamma = preset.get('transition_gamma', 1.0)
        _blend_strength = preset.get('blend_strength', 0.85)
        _flake_cell_size = preset.get('flake_cell_size', 5)

        def _make_spec(ca=_ca, cb=_cb, ml=_ml, mh=_mh,
                       field_style=_field_style, flow_complexity=_flow_complexity,
                       field_seed_offset=_field_seed_offset, edge_bias=_edge_bias,
                       turbulence=_turbulence, band_sharpness=_band_sharpness,
                       flake_cell_size=_flake_cell_size):
            def _spec(shape, mask, seed, sm):
                return spec_dual_shift(shape, mask, seed, sm, color_a=ca, color_b=cb,
                                       M_low=ml, M_high=mh,
                                       field_style=field_style,
                                       flow_complexity=flow_complexity,
                                       field_seed_offset=field_seed_offset,
                                       edge_bias=edge_bias,
                                       turbulence=turbulence,
                                       band_sharpness=band_sharpness,
                                       flake_cell_size=flake_cell_size)
            return _spec

        def _make_paint(ca=_ca, cb=_cb,
                        field_style=_field_style, flow_complexity=_flow_complexity,
                        field_seed_offset=_field_seed_offset, edge_bias=_edge_bias,
                        turbulence=_turbulence, band_sharpness=_band_sharpness,
                        transition_mid=_transition_mid, transition_width=_transition_width,
                        transition_gamma=_transition_gamma, blend_strength=_blend_strength,
                        flake_cell_size=_flake_cell_size):
            def _paint(paint, shape, mask, seed, pm, bb):
                return paint_dual_shift(paint, shape, mask, seed, pm, bb,
                                        color_a=ca, color_b=cb,
                                        field_style=field_style,
                                        flow_complexity=flow_complexity,
                                        field_seed_offset=field_seed_offset,
                                        edge_bias=edge_bias,
                                        turbulence=turbulence,
                                        band_sharpness=band_sharpness,
                                        transition_mid=transition_mid,
                                        transition_width=transition_width,
                                        transition_gamma=transition_gamma,
                                        blend_strength=blend_strength,
                                        flake_cell_size=flake_cell_size)
            return _paint

        # Map to new cx_ namespace
        _cx_map = {
            "custom": "cx_custom_shift",
            "pink_to_gold": "cx_pink_to_gold",
            "blue_to_orange": "cx_blue_to_orange",
            "purple_to_green": "cx_purple_to_green",
            "teal_to_magenta": "cx_teal_to_magenta",
            "red_to_cyan": "cx_red_to_cyan",
            "sunset": "cx_sunset_shift",
            "emerald_ruby": "cx_emerald_ruby",
            "ice_fire": "cx_ice_fire",
        }
        cx_id = _cx_map.get(preset_id, f"cx_{preset_id}")
        entries[cx_id] = (_make_spec(), _make_paint())
        # Backward compat: also register under old dualshift_ ID
        old_id = f"dualshift_{preset_id}"
        entries[old_id] = entries[cx_id]

    return entries


# Auto-build on import
DUAL_SHIFT_MONOLITHICS = build_dual_shift_monolithics()
