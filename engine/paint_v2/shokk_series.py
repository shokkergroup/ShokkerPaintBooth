"""
SHOKK SERIES — Brand Signature Bases — 5 bases
These are the flagship finishes. They MUST be the best in the entire system.
Each uses genuinely different mathematical approaches.
Each includes BOTH paint_fn AND spec_fn for full PBR material definition.

Techniques used (all different):
  shokk_blood  — Reaction-diffusion (Gray-Scott Turing pattern) for organic vein network
  shokk_pulse  — Domain-warped Perlin + Fresnel rim glow for energy arc channels
  shokk_static — Scanline corruption + chromatic aberration + bit-depth quantization
  shokk_venom  — Gravity-driven fluid simulation for acid drip rivulets
  shokk_void   — Exponential absorption + Rayleigh scatter edge glow (vantablack physics)
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


# ══════════════════════════════════════════════════════════════════
# SHOKK BLOOD — Reaction-diffusion vein network
# Gray-Scott model creates organic branching patterns like capillary
# networks under skin. No two seeds produce the same vein layout.
# At 2048x2048 this creates intricate micro-detail.
# ══════════════════════════════════════════════════════════════════

def paint_shokk_blood_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 800)
    # --- Gray-Scott reaction-diffusion for vein pattern ---
    # Run on 1/4 resolution then upscale for performance
    sh, sw = h // 4, w // 4
    u = np.ones((sh, sw), dtype=np.float32)
    v = np.zeros((sh, sw), dtype=np.float32)
    # Seed random activation points
    n_seeds = 30 + (seed % 20)
    for _ in range(n_seeds):
        sy, sx = rng.randint(0, sh), rng.randint(0, sw)
        r = rng.randint(2, 6)
        v[max(0,sy-r):sy+r, max(0,sx-r):sx+r] = 1.0

    # Diffusion parameters tuned for vein-like branching
    Du, Dv = 0.16, 0.08
    f_rate, k_rate = 0.035, 0.065  # mitosis regime

    # Laplacian kernel via convolution
    def laplacian(arr):
        return (
            np.roll(arr, 1, 0) + np.roll(arr, -1, 0) +
            np.roll(arr, 1, 1) + np.roll(arr, -1, 1) - 4 * arr
        )

    # 40 iterations of Gray-Scott
    for _ in range(40):
        uvv = u * v * v
        du = Du * laplacian(u) - uvv + f_rate * (1.0 - u)
        dv = Dv * laplacian(v) + uvv - (f_rate + k_rate) * v
        u = np.clip(u + du * 1.0, 0, 1)
        v = np.clip(v + dv * 1.0, 0, 1)
    # Upscale vein pattern to full resolution
    from PIL import Image as _Img
    vein_map = np.array(_Img.fromarray((v * 255).astype(np.uint8)).resize(
        (w, h), _Img.BICUBIC)).astype(np.float32) / 255.0

    # --- Blood red base with vein darkening ---
    base = paint.copy()
    # Deep crimson target — preserves user's color as undertone
    blood_r = np.clip(base[:,:,0] * 0.25 + 0.5, 0, 1)
    blood_g = np.clip(base[:,:,1] * 0.08, 0, 1)
    blood_b = np.clip(base[:,:,2] * 0.06, 0, 1)
    blood = np.stack([blood_r, blood_g, blood_b], axis=-1)

    # Veins are darker, near-black with deep red core
    vein_dark = np.clip(blood * (1.0 - vein_map[:,:,np.newaxis] * 0.7), 0, 1)
    # Vein cores get extra red saturation
    vein_dark[:,:,0] = np.clip(vein_dark[:,:,0] + vein_map * 0.15, 0, 1)

    # Subsurface scatter in thin areas — light passes through
    scatter = np.clip((1.0 - vein_map) * bb * 0.1 * pm, 0, 1)
    vein_dark[:,:,0] = np.clip(vein_dark[:,:,0] + scatter, 0, 1)

    effect = np.clip(vein_dark, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend),
        0, 1
    )
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_shokk_blood(shape, seed, sm, base_m, base_r):
    """Spec map: wet organic surface — high metallic in vein channels,
    very low roughness (wet), clearcoat varies with vein depth."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 800)

    # Recompute vein pattern at spec resolution
    sh, sw = h // 4, w // 4
    u = np.ones((sh, sw), dtype=np.float32)
    v = np.zeros((sh, sw), dtype=np.float32)
    n_seeds = 30 + (seed % 20)
    for _ in range(n_seeds):
        sy, sx = rng.randint(0, sh), rng.randint(0, sw)
        r = rng.randint(2, 6)
        v[max(0,sy-r):sy+r, max(0,sx-r):sx+r] = 1.0

    def laplacian(arr):
        return np.roll(arr,1,0)+np.roll(arr,-1,0)+np.roll(arr,1,1)+np.roll(arr,-1,1)-4*arr

    Du, Dv, f_rate, k_rate = 0.16, 0.08, 0.035, 0.065
    for _ in range(40):
        uvv = u * v * v
        u = np.clip(u + (Du * laplacian(u) - uvv + f_rate * (1 - u)), 0, 1)
        v = np.clip(v + (Dv * laplacian(v) + uvv - (f_rate + k_rate) * v), 0, 1)

    from PIL import Image as _Img
    vein = np.array(_Img.fromarray((v*255).astype(np.uint8)).resize((w,h),_Img.BICUBIC)).astype(np.float32)/255.0

    # Veins are wet (low roughness, moderate metallic)
    M = np.clip(base_m + vein * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r - vein * 80.0 * sm + 20.0, 15, 255).astype(np.float32)
    CC = np.clip(20 + vein * 30.0, 0, 255).astype(np.float32)
    return M, R, CC

# ══════════════════════════════════════════════════════════════════
# SHOKK PULSE — Domain-warped Perlin + Fresnel rim glow
# Energy arc channels created by warping coordinate space through
# multiple Perlin layers, then applying Fresnel-like rim lighting
# that makes edges glow hot-pink/electric-blue. This is the
# signature Shokker energy look — pulsing, electric, alive.
# ══════════════════════════════════════════════════════════════════

def paint_shokk_pulse_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 810)
    y, x = get_mgrid((h, w))

    # Normalize coords to [0, 1]
    yn = y / max(h - 1, 1)
    xn = x / max(w - 1, 1)

    # --- Domain warping: warp coordinates through noise layers ---
    # First warp layer — large-scale energy flow direction
    warp1 = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1)
    warp2 = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 2)

    # Warped coordinates create organic energy channel paths
    wx = xn + (warp1 - 0.5) * 0.4
    wy = yn + (warp2 - 0.5) * 0.4

    # Second warp — finer turbulence within the channels
    turb = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 3)
    wx2 = wx + (turb - 0.5) * 0.15
    wy2 = wy + (turb - 0.5) * 0.15
    # --- Energy arc pattern from interference of warped sine fields ---
    # Multiple frequency sine waves through warped space = branching arcs
    arc1 = np.sin(wx2 * 18.0 + wy2 * 6.0) * 0.5 + 0.5
    arc2 = np.sin(wx2 * 7.0 - wy2 * 22.0 + 1.5) * 0.5 + 0.5
    arc3 = np.sin((wx2 + wy2) * 13.0 + turb * 4.0) * 0.5 + 0.5

    # Combine — sharp energy channels via power curve
    energy_raw = (arc1 * 0.4 + arc2 * 0.35 + arc3 * 0.25)
    # Power curve sharpens into thin bright channels
    energy = np.power(np.clip(energy_raw, 0, None), 3.0).astype(np.float32)

    # --- Fresnel rim glow ---
    # Simulate viewing angle using distance from mask edges
    # Edges of the painted area glow brighter (like Fresnel reflection)
    from PIL import Image as _Img, ImageFilter as _Filt
    mask_pil = _Img.fromarray((mask * 255).astype(np.uint8))
    mask_blur = np.array(mask_pil.filter(
        _Filt.GaussianBlur(radius=max(h // 64, 3))
    )).astype(np.float32) / 255.0
    # Rim = where mask transitions from 0→1 (edge detection via gradient)
    rim = np.clip(mask - mask_blur, 0, 1)
    rim = np.clip(rim * 8.0, 0, 1)  # Sharpen the rim band

    # --- Color: hot pink core, electric blue rim ---
    base = paint.copy()
    # Energy channel color: Shokker signature electric blue-pink
    pulse_r = np.clip(0.1 + energy * 0.8 + rim * 0.3, 0, 1)
    pulse_g = np.clip(0.02 + energy * 0.1 + rim * 0.15, 0, 1)
    pulse_b = np.clip(0.25 + energy * 0.5 + rim * 0.6, 0, 1)
    pulse = np.stack([pulse_r, pulse_g, pulse_b], axis=-1).astype(np.float32)
    # Blend base darkened underneath with bright energy on top
    dark_base = np.clip(base * 0.15, 0, 1)  # Near-black substrate
    effect = np.clip(dark_base + pulse * energy[:,:,np.newaxis] * 1.5, 0, 1)
    # Rim glow additive
    effect = np.clip(effect + rim[:,:,np.newaxis] * np.array([0.9, 0.2, 1.0]) * 0.3, 0, 1)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend),
        0, 1
    )
    return np.clip(result + bb[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_shokk_pulse(shape, seed, sm, base_m, base_r):
    """Spec: energy channels are highly metallic + mirror-smooth.
    Background is dark dielectric. Rim zones get extra clearcoat."""
    h, w = shape[:2] if len(shape) > 2 else shape
    yn, xn = get_mgrid((h, w))
    yn = yn / max(h - 1, 1)
    xn = xn / max(w - 1, 1)

    warp1 = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1)
    warp2 = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 2)
    turb = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 3)
    wx = xn + (warp1 - 0.5) * 0.4 + (turb - 0.5) * 0.15
    wy = yn + (warp2 - 0.5) * 0.4 + (turb - 0.5) * 0.15
    arc1 = np.sin(wx * 18.0 + wy * 6.0) * 0.5 + 0.5
    arc2 = np.sin(wx * 7.0 - wy * 22.0 + 1.5) * 0.5 + 0.5
    arc3 = np.sin((wx + wy) * 13.0 + turb * 4.0) * 0.5 + 0.5
    energy = np.power(np.clip(arc1 * 0.4 + arc2 * 0.35 + arc3 * 0.25, 0, None), 3.0).astype(np.float32)

    # Energy channels = metallic + smooth; background = rough dielectric
    M = np.clip(base_m * 0.3 + energy * 200.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + 40.0 - energy * 120.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(10.0 + energy * 20.0, 0, 255).astype(np.float32)
    return M, R, CC

# ══════════════════════════════════════════════════════════════════
# SHOKK STATIC — Scanline corruption + chromatic aberration
# Simulates a CRT/digital glitch aesthetic at the material level.
# Horizontal scanlines with random offset corruption, per-channel
# displacement (chromatic aberration), and bit-depth quantization
# artifacts. This is signal interference made physical.
# ══════════════════════════════════════════════════════════════════

def paint_shokk_static_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 820)

    base = paint.copy()

    # --- Scanline pattern: every Nth row is darker (CRT phosphor gaps) ---
    scanline_period = max(2, h // 512)  # ~4px gaps at 2048
    scanline = np.ones((h, w), dtype=np.float32)
    scanline[::scanline_period, :] = 0.7  # Dim every Nth row
    # Alternate sub-rows get slight boost (RGB subpixel simulation)
    if scanline_period > 2:
        scanline[1::scanline_period, :] = 1.05

    # --- Horizontal corruption: random row blocks get shifted ---
    corrupted = base.copy()
    n_glitches = 15 + (seed % 20)
    for _ in range(n_glitches):
        gy = rng.randint(0, h)
        gh = rng.randint(1, max(2, h // 128))  # 1-16 rows tall
        shift = rng.randint(-max(1, w // 32), max(2, w // 32))
        y0, y1 = gy, min(gy + gh, h)
        corrupted[y0:y1, :, :] = np.roll(corrupted[y0:y1, :, :], shift, axis=1)
    # --- Chromatic aberration: shift R and B channels in opposite directions ---
    ca_shift = max(1, w // 256)  # ~8px at 2048
    chroma = corrupted.copy()
    chroma[:, :, 0] = np.roll(corrupted[:, :, 0], ca_shift, axis=1)   # Red → right
    chroma[:, :, 2] = np.roll(corrupted[:, :, 2], -ca_shift, axis=1)  # Blue → left
    # Green stays centered (most luminance info)

    # --- Bit-depth quantization: reduce to N levels then back ---
    # Simulates analog-to-digital conversion artifacts
    quant_levels = 12 + (seed % 8)  # 12-19 levels instead of 256
    quantized = np.floor(chroma * quant_levels) / quant_levels

    # --- Static noise: per-pixel high-frequency interference ---
    static_noise = rng.rand(h, w).astype(np.float32)
    # Only inject noise at low intensity — sparkle, not snow
    static_intensity = 0.08

    # --- Combine all corruption layers ---
    effect = quantized * scanline[:,:,np.newaxis]
    effect = np.clip(effect + (static_noise[:,:,np.newaxis] - 0.5) * static_intensity, 0, 1)

    # Dark blue-gray substrate undertone for the static
    substrate = np.stack([
        np.full((h,w), 0.12, dtype=np.float32),
        np.full((h,w), 0.14, dtype=np.float32),
        np.full((h,w), 0.20, dtype=np.float32)
    ], axis=-1)
    effect = np.clip(effect * 0.7 + substrate * 0.3, 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend),
        0, 1
    )
    return np.clip(result + bb[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_shokk_static(shape, seed, sm, base_m, base_r):
    """Spec: scanlines create alternating roughness bands. Glitch zones
    have higher metallic (exposed circuit). Quantization steps visible
    in the roughness channel as banding."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 820)

    # Scanline roughness bands — sharp horizontal variation
    scanline_period = max(2, h // 512)
    rough_band = np.ones((h, w), dtype=np.float32)
    rough_band[::scanline_period, :] = 1.4  # Scanline gaps are rougher
    if scanline_period > 2:
        rough_band[1::scanline_period, :] = 0.8  # Bright rows are smoother

    # Static noise for metallic sparkle variation
    static = rng.rand(h, w).astype(np.float32)

    # Glitch block zones — higher metallic (exposed "circuit board")
    glitch_map = np.zeros((h, w), dtype=np.float32)
    n_glitches = 15 + (seed % 20)
    for _ in range(n_glitches):
        gy = rng.randint(0, h)
        gh = rng.randint(1, max(2, h // 128))
        glitch_map[gy:min(gy+gh, h), :] = 1.0
    M = np.clip(base_m + glitch_map * 80.0 * sm + static * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r * rough_band - static * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 - glitch_map * 10.0, 0, 255).astype(np.float32)
    return M, R, CC

# ══════════════════════════════════════════════════════════════════
# SHOKK VENOM — Gravity-driven fluid simulation
# Simulates toxic acid dripping down a surface under gravity.
# Fluid accumulates at the top, flows downward through random
# channels carved by surface imperfections, pools at ledges,
# and leaves thin residue trails. The math models actual fluid
# flow with viscosity, surface tension, and gravity.
# ══════════════════════════════════════════════════════════════════

def paint_shokk_venom_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 830)

    # --- Surface imperfection map (what the fluid flows around) ---
    # This creates random ridges and valleys that channel the flow
    surface = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1)

    # --- Gravity-driven flow simulation ---
    # Work at 1/4 res for performance, then upscale
    sh, sw = h // 4, w // 4
    fluid = np.zeros((sh, sw), dtype=np.float32)

    # Seed fluid sources along top edge and random drip points
    fluid[0, :] = rng.rand(sw).astype(np.float32) * 0.8
    n_drips = 20 + (seed % 15)
    for _ in range(n_drips):
        dx, dy = rng.randint(0, sw), rng.randint(0, sh // 3)
        r = rng.randint(1, 4)
        fluid[max(0,dy-r):dy+r, max(0,dx-r):dx+r] = rng.uniform(0.5, 1.0)
    # Downsample surface map for flow simulation
    from PIL import Image as _Img
    surf_small = np.array(_Img.fromarray((surface * 255).astype(np.uint8)).resize(
        (sw, sh), _Img.BILINEAR)).astype(np.float32) / 255.0

    # Iterate: fluid flows downward, deflected by surface features
    # viscosity = how much spreads sideways, gravity = downward pull
    viscosity = 0.15
    gravity = 0.6
    for _ in range(60):
        # Gravity: pull fluid downward (shift array down by 1)
        flow_down = np.roll(fluid, 1, axis=0) * gravity
        flow_down[0, :] = 0  # Nothing flows in from above the top

        # Lateral spread based on surface slope
        slope_l = np.roll(surf_small, 1, axis=1) - surf_small
        slope_r = np.roll(surf_small, -1, axis=1) - surf_small
        flow_l = np.clip(slope_l, 0, 1) * fluid * viscosity
        flow_r = np.clip(slope_r, 0, 1) * fluid * viscosity

        # Surface tension: fluid sticks in valleys (low surface values)
        stick = np.clip(1.0 - surf_small, 0.3, 1.0)

        # Update fluid field
        fluid = np.clip(
            fluid * (1.0 - gravity - viscosity) * stick +
            flow_down + np.roll(flow_l, -1, axis=1) + np.roll(flow_r, 1, axis=1),
            0, 1
        )
        # Re-seed top edge slightly each iteration (continuous drip)
        fluid[0, :] = np.clip(fluid[0, :] + rng.rand(sw) * 0.05, 0, 1)
    # Upscale fluid map to full resolution
    drip_map = np.array(_Img.fromarray((np.clip(fluid, 0, 1) * 255).astype(np.uint8)).resize(
        (w, h), _Img.BICUBIC)).astype(np.float32) / 255.0

    # --- Toxic acid green-yellow color ---
    base = paint.copy()
    # Dark substrate where no fluid
    substrate = np.clip(base * 0.1, 0, 1)
    # Venom color: acid green core, yellow-green in thin areas
    venom_r = np.clip(0.3 + drip_map * 0.5, 0, 1)   # Yellow component
    venom_g = np.clip(0.15 + drip_map * 0.75, 0, 1)  # Strong green
    venom_b = np.clip(0.0 + drip_map * 0.05, 0, 1)   # Almost no blue
    venom = np.stack([venom_r, venom_g, venom_b], axis=-1).astype(np.float32)

    # Thick pooled areas are more saturated, thin residue is translucent
    effect = np.clip(substrate * (1.0 - drip_map[:,:,np.newaxis]) +
                     venom * drip_map[:,:,np.newaxis], 0, 1)

    # Caustic bright highlights where fluid is thickest
    thick = np.clip((drip_map - 0.6) * 3.0, 0, 1)
    effect[:,:,1] = np.clip(effect[:,:,1] + thick * 0.2, 0, 1)  # Extra green glow

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend),
        0, 1
    )
    return np.clip(result + bb[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_shokk_venom(shape, seed, sm, base_m, base_r):
    """Spec: pooled acid is wet and glossy (low roughness, moderate metallic
    from dissolved metal). Dry residue trails are rough. Thick pools get
    clearcoat from surface tension meniscus."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 830)

    # Recompute drip map for spec (same sim parameters)
    surface = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1)
    sh, sw = h // 4, w // 4
    fluid = np.zeros((sh, sw), dtype=np.float32)
    fluid[0, :] = rng.rand(sw).astype(np.float32) * 0.8
    n_drips = 20 + (seed % 15)
    for _ in range(n_drips):
        dx, dy = rng.randint(0, sw), rng.randint(0, sh // 3)
        r = rng.randint(1, 4)
        fluid[max(0,dy-r):dy+r, max(0,dx-r):dx+r] = rng.uniform(0.5, 1.0)

    from PIL import Image as _Img
    surf_small = np.array(_Img.fromarray((surface * 255).astype(np.uint8)).resize(
        (sw, sh), _Img.BILINEAR)).astype(np.float32) / 255.0

    for _ in range(60):
        flow_down = np.roll(fluid, 1, axis=0) * 0.6
        flow_down[0, :] = 0
        slope_l = np.roll(surf_small, 1, axis=1) - surf_small
        slope_r = np.roll(surf_small, -1, axis=1) - surf_small
        stick = np.clip(1.0 - surf_small, 0.3, 1.0)
        fluid = np.clip(
            fluid * 0.25 * stick + flow_down +
            np.roll(np.clip(slope_l,0,1)*fluid*0.15, -1, axis=1) +
            np.roll(np.clip(slope_r,0,1)*fluid*0.15, 1, axis=1), 0, 1)
        fluid[0, :] = np.clip(fluid[0, :] + rng.rand(sw) * 0.05, 0, 1)

    drip = np.array(_Img.fromarray((np.clip(fluid,0,1)*255).astype(np.uint8)).resize(
        (w, h), _Img.BICUBIC)).astype(np.float32) / 255.0

    # Wet pooled acid: low roughness, some metallic (dissolved metal particles)
    # Dry residue: high roughness, no metallic
    M = np.clip(base_m * 0.5 + drip * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + 30.0 - drip * 100.0 * sm, 15, 255).astype(np.float32)
    # Thick pools get clearcoat (surface tension creates smooth meniscus)
    thick = np.clip((drip - 0.5) * 2.0, 0, 1)
    CC = np.clip(5.0 + thick * 25.0, 0, 255).astype(np.float32)
    return M, R, CC

# ══════════════════════════════════════════════════════════════════
# SHOKK VOID — Exponential absorption + Rayleigh scatter edge glow
# Models near-vantablack physics: a surface that absorbs 99.5% of
# light. The math uses Beer-Lambert exponential decay for absorption
# depth, and Rayleigh scattering (1/lambda^4) for the faint blue
# shimmer visible only at extreme grazing angles (edges).
# This should look like staring into nothing, with just a whisper
# of deep blue at the margins.
# ══════════════════════════════════════════════════════════════════

def paint_shokk_void_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 840)

    base = paint.copy()

    # --- Beer-Lambert absorption ---
    # Nearly all light is absorbed. The "depth" varies slightly with
    # surface micro-texture to prevent dead-flat CG look.
    micro_depth = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.4, 0.3], seed + 1)
    # Absorption coefficient — very high (deep black)
    alpha_coeff = 6.0 + micro_depth * 1.5  # 6.0-7.5 extinction
    # Beer-Lambert: I = I0 * exp(-alpha * depth)
    # At alpha=6.5, transmitted light is exp(-6.5) = 0.0015 (99.85% absorbed)
    absorbed = np.exp(-alpha_coeff).astype(np.float32)

    # Base color after absorption — nearly black with micro-variation
    void_base = base * absorbed[:,:,np.newaxis]
    # Clamp to near-zero but not pure zero (prevents banding)
    void_base = np.clip(void_base + 0.003, 0, 0.02)
    # --- Rayleigh scattering at edges ---
    # In reality, even vantablack shows a faint blue shimmer at grazing
    # angles because shorter wavelengths (blue) scatter more (1/lambda^4).
    # We simulate "grazing angle" using distance from mask edges.
    from PIL import Image as _Img, ImageFilter as _Filt

    # Create edge distance map via progressive blur
    mask_pil = _Img.fromarray((mask * 255).astype(np.uint8))
    # Multiple blur passes for smooth gradient from edge
    blur_r = max(h // 32, 4)
    mask_inner = np.array(mask_pil.filter(
        _Filt.GaussianBlur(radius=blur_r)
    )).astype(np.float32) / 255.0

    # Edge proximity: 1.0 at mask edge, 0.0 deep inside
    edge_prox = np.clip((mask - mask_inner) * 6.0, 0, 1)
    # Also catch outer edges
    edge_prox2 = np.clip((mask_inner - np.array(mask_pil.filter(
        _Filt.GaussianBlur(radius=blur_r * 3)
    )).astype(np.float32) / 255.0) * 3.0, 0, 1)
    edge = np.clip(edge_prox + edge_prox2, 0, 1)

    # Rayleigh: blue scatters most, red scatters least (1/lambda^4)
    # lambda_r ~ 650nm, lambda_g ~ 550nm, lambda_b ~ 450nm
    # Relative scatter: R = 1.0, G = (650/550)^4 = 1.95, B = (650/450)^4 = 4.35
    scatter_r = edge * 0.004   # Almost nothing
    scatter_g = edge * 0.008   # Trace
    scatter_b = edge * 0.035   # Visible deep blue shimmer

    # Add scatter to void base
    effect = void_base.copy()
    effect[:,:,0] = np.clip(effect[:,:,0] + scatter_r, 0, 1)
    effect[:,:,1] = np.clip(effect[:,:,1] + scatter_g, 0, 1)
    effect[:,:,2] = np.clip(effect[:,:,2] + scatter_b, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend),
        0, 1
    )
    # Void absorbs even the AO/brightness buffer — almost no BB contribution
    return np.clip(result + bb[:,:,np.newaxis] * 0.01 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_shokk_void(shape, seed, sm, base_m, base_r):
    """Spec: ultra-high roughness everywhere (light trapping micro-texture).
    Zero metallic (dielectric absorber). Near-zero clearcoat except at
    extreme edges where Rayleigh scatter creates a faint gloss band."""
    h, w = shape[:2] if len(shape) > 2 else shape

    # Micro-texture variation — even vantablack has structure
    micro = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.4, 0.3], seed + 1)

    # Essentially zero metallic — this is a dielectric absorber, not a metal
    M = np.clip(base_m * 0.05 + micro * 3.0 * sm, 0, 255).astype(np.float32)
    # Extremely high roughness — the micro-texture traps light
    R = np.clip(220.0 + micro * 30.0 * sm, 15, 255).astype(np.float32)
    # Near-zero clearcoat — no specular reflection layer
    CC = np.clip(2.0 + micro * 3.0, 0, 255).astype(np.float32)
    return M, R, CC