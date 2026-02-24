# ================================================================
# SHOKKER COLOR SHIFT PRO — Coordinated Dual-Map System
# Novel technique: Paint + Spec generated from shared gradient field
# Creates genuine differential Fresnel behavior for real color shift
# ================================================================

def _generate_colorshift_field(shape, seed):
    """Generate the master gradient field that drives both paint and spec.

    Returns a normalized 0-1 field with multi-directional sine waves
    + multi-scale Perlin noise for organic flow. Deterministic for
    a given seed so paint and spec functions produce matching fields.
    """
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    # 5 directional sine waves at different angles/frequencies
    # More complex than old chameleon (which used 4 waves)
    np.random.seed(seed + 5000)

    # Primary diagonal waves
    f1 = np.sin(yf * 0.010 + xf * 0.007) * 0.22
    f2 = np.sin(yf * 0.005 - xf * 0.013) * 0.20
    # Cross-diagonal
    f3 = np.sin((yf + xf) * 0.008) * 0.18
    f4 = np.sin((yf - xf * 0.6) * 0.012) * 0.16
    # Radial component — creates circular flow patterns
    cy, cx = h * 0.45, w * 0.5
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2).astype(np.float32)
    f5 = np.sin(dist * 0.008) * 0.12

    field = f1 + f2 + f3 + f4 + f5

    # Multi-scale noise for organic breakup (prevents visible banding)
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5001)
    field = field + noise * 0.18

    # Normalize to 0..1
    fmin, fmax = field.min(), field.max()
    field = (field - fmin) / (fmax - fmin + 1e-8)

    return field


def _generate_flake_field(shape, seed, cell_size=6):
    """Generate Voronoi-like flake cells for micro-texture.

    Returns:
      flake_val: 0-1 per-pixel value (random per cell) for hue offsets
      flake_edge: 0-1 edge detection (1.0 at cell boundaries)
    """
    h, w = shape
    rng = np.random.RandomState(seed + 5100)

    # Grid of cell centers
    ny = h // cell_size
    nx = w // cell_size

    # Random value per cell (determines flake "orientation" = hue offset)
    cell_values = rng.rand(ny + 2, nx + 2).astype(np.float32)

    # Map each pixel to its cell
    yidx = np.clip(np.arange(h) // cell_size, 0, ny).astype(int)
    xidx = np.clip(np.arange(w) // cell_size, 0, nx).astype(int)

    # Broadcast to 2D
    flake_val = cell_values[yidx[:, None], xidx[None, :]]

    # Edge detection via gradient magnitude
    gy = np.abs(np.diff(flake_val, axis=0, prepend=flake_val[:1, :]))
    gx = np.abs(np.diff(flake_val, axis=1, prepend=flake_val[:, :1]))
    flake_edge = np.clip((gy + gx) * 8.0, 0, 1)

    return flake_val, flake_edge


def paint_colorshift_pro(paint, shape, mask, seed, pm, bb,
                         primary_hue=120, shift_range=240,
                         flake_size=6, flake_hue_spread=0.06):
    """Coordinated color-shift paint modifier — the Shokker innovation.

    Generates a physically-motivated color ramp with micro-flake texture.
    Uses the SAME gradient field as spec_colorshift_pro for coordination.

    Args:
        primary_hue: Starting hue in degrees (0-360)
        shift_range: Degrees of hue shift across the gradient
        flake_size: Voronoi cell size in pixels (4-12)
        flake_hue_spread: How much each flake shifts from macro hue (0.0-0.15)
    """
    h, w = shape

    # Generate the SAME field that spec will use (deterministic from seed)
    field = _generate_colorshift_field(shape, seed)

    # Generate micro-flake texture
    flake_val, flake_edge = _generate_flake_field(shape, seed, cell_size=flake_size)

    # Map field through HSV color ramp following thin-film interference order
    hue_start = primary_hue / 360.0
    hue_shift = shift_range / 360.0

    # Base hue from macro field
    hue_map = (hue_start + field * hue_shift) % 1.0

    # Add per-flake hue offset (micro-texture)
    flake_offset = (flake_val - 0.5) * flake_hue_spread
    hue_map = (hue_map + flake_offset) % 1.0

    # Saturation: peaks mid-shift for vivid transition colors
    saturation = 0.78 + 0.17 * np.sin(field * np.pi)

    # Value/brightness: compensate for metallic darkening
    # iRacing metallic makes colors appear much darker than paint TGA values
    # So we boost brightness significantly — this will look correct in-sim
    value = 0.65 + 0.15 * np.sin(field * np.pi * 0.5)

    # Add subtle flake-edge darkening (simulates flake boundary shadowing)
    value = value - flake_edge * 0.04

    # Convert HSV to RGB
    r_new, g_new, b_new = hsv_to_rgb_vec(hue_map, saturation, value)

    # Stack into array
    shift_rgb = np.stack([r_new, g_new, b_new], axis=2)

    # Blend with original paint — pm controls overall strength
    # Use 0.75 base blend (slightly higher than old chameleon's 0.70)
    blend = 0.75 * pm
    mask3 = mask[:, :, np.newaxis]
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3

    # Brightness boost for dark paints
    paint = np.clip(paint + bb * 1.3 * mask3, 0, 1)

    return paint


def spec_colorshift_pro(shape, mask, seed, sm,
                        M_base=210, M_range=40,
                        R_base=12, R_var=8,
                        CC_base=16, CC_range=18):
    """Coordinated color-shift spec generator — the Shokker innovation.

    Generates a spec map with spatially varied M/R/CC that creates
    genuine differential Fresnel behavior. Uses the SAME gradient field
    as paint_colorshift_pro for mathematical coordination.

    The key insight: where paint is one color, spec creates one Fresnel
    behavior; where paint is another color, spec creates a different
    Fresnel behavior. The result is genuine view-dependent appearance change.

    Args:
        M_base: Base metallic value (200-230)
        M_range: Metallic variation range (20-50)
        R_base: Base roughness (8-20)
        R_var: Roughness variation (±)
        CC_base: Base clearcoat (16=max)
        CC_range: Clearcoat variation range
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)

    # Generate the SAME field that paint used (deterministic from seed)
    field = _generate_colorshift_field(shape, seed)

    # --- METALLIC: Inversely correlated with field ---
    # Where field is high (one end of color ramp) → lower metallic → more diffuse color visible
    # Where field is low (other end of ramp) → higher metallic → stronger Fresnel reflections
    # This creates GENUINE differential Fresnel behavior
    M_arr = M_base + (1.0 - field) * M_range * sm

    # Add subtle noise to prevent banding
    m_noise = multi_scale_noise(shape, [12, 24], [0.5, 0.5], seed + 5010)
    M_arr = M_arr + m_noise * 6 * sm

    # --- ROUGHNESS: Low base with micro-variation ---
    # Creates regions of sharp vs slightly diffused reflections
    # Like individual flakes at slightly different orientations
    r_noise = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5020)
    R_arr = np.full((h, w), float(R_base)) + r_noise * R_var * sm

    # --- CLEARCOAT: Follows field (opposing metallic) ---
    # Where metallic is HIGH → clearcoat is LOW → colored metallic reflections dominate
    # Where metallic is LOWER → clearcoat is HIGHER → white specular "flash" competes
    # This creates the two-layer system that shifts with viewing angle
    CC_arr = CC_base + field * CC_range * sm

    # Add subtle CC noise for organic feel
    cc_noise = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 5030)
    CC_arr = CC_arr + cc_noise * 3 * sm

    # Clamp and write to spec channels
    spec[:, :, 0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)    # R = Metallic
    spec[:, :, 1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)    # G = Roughness
    spec[:, :, 2] = np.clip(CC_arr * mask, 0, 255).astype(np.uint8)   # B = Clearcoat
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)      # A = Spec mask

    return spec


# ================================================================
# COLOR SHIFT PRESETS — Physically-motivated thin-film color ramps
# ================================================================

# Each preset wraps paint_colorshift_pro and spec_colorshift_pro
# with specific hue/shift parameters following real interference physics

# --- Emerald: Green → Blue → Purple (ChromaFlair classic, Mystichrome-style) ---
def paint_colorshift_emerald(paint, shape, mask, seed, pm, bb):
    """Color Shift Emerald — Green → Blue → Purple (ChromaFlair classic)"""
    return paint_colorshift_pro(paint, shape, mask, seed, pm, bb,
                                primary_hue=120, shift_range=240,
                                flake_size=6, flake_hue_spread=0.06)

def spec_colorshift_emerald(shape, mask, seed, sm):
    """Coordinated spec for Color Shift Emerald"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=210, M_range=40, R_base=12, R_var=8,
                               CC_base=16, CC_range=18)

# --- Inferno: Red → Orange → Gold → Green (warm interference) ---
def paint_colorshift_inferno(paint, shape, mask, seed, pm, bb):
    """Color Shift Inferno — Red → Orange → Gold → Green"""
    return paint_colorshift_pro(paint, shape, mask, seed, pm, bb,
                                primary_hue=0, shift_range=130,
                                flake_size=5, flake_hue_spread=0.05)

def spec_colorshift_inferno(shape, mask, seed, sm):
    """Coordinated spec for Color Shift Inferno"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=215, M_range=35, R_base=10, R_var=6,
                               CC_base=16, CC_range=14)

# --- Nebula: Purple → Pink → Gold (cosmic luxury) ---
def paint_colorshift_nebula(paint, shape, mask, seed, pm, bb):
    """Color Shift Nebula — Purple → Pink → Gold"""
    return paint_colorshift_pro(paint, shape, mask, seed, pm, bb,
                                primary_hue=270, shift_range=120,
                                flake_size=7, flake_hue_spread=0.07)

def spec_colorshift_nebula(shape, mask, seed, sm):
    """Coordinated spec for Color Shift Nebula"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=220, M_range=35, R_base=14, R_var=7,
                               CC_base=16, CC_range=16)

# --- Deep Ocean: Teal → Blue → Violet (cool interference) ---
def paint_colorshift_deepocean(paint, shape, mask, seed, pm, bb):
    """Color Shift Deep Ocean — Teal → Blue → Indigo → Violet"""
    return paint_colorshift_pro(paint, shape, mask, seed, pm, bb,
                                primary_hue=180, shift_range=110,
                                flake_size=6, flake_hue_spread=0.05)

def spec_colorshift_deepocean(shape, mask, seed, sm):
    """Coordinated spec for Color Shift Deep Ocean"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=215, M_range=38, R_base=11, R_var=7,
                               CC_base=16, CC_range=16)

# --- Supernova: Copper → Magenta → Cyan (widest shift, full spectrum) ---
def paint_colorshift_supernova(paint, shape, mask, seed, pm, bb):
    """Color Shift Supernova — Copper → Magenta → Violet → Teal (full spectrum)"""
    return paint_colorshift_pro(paint, shape, mask, seed, pm, bb,
                                primary_hue=20, shift_range=300,
                                flake_size=5, flake_hue_spread=0.08)

def spec_colorshift_supernova(shape, mask, seed, sm):
    """Coordinated spec for Color Shift Supernova"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=205, M_range=45, R_base=12, R_var=9,
                               CC_base=16, CC_range=20)

# --- Solar Flare: Gold → Amber → Red → Crimson (sunset metal) ---
def paint_colorshift_solarflare(paint, shape, mask, seed, pm, bb):
    """Color Shift Solar Flare — Gold → Amber → Red (sunset metal)"""
    return paint_colorshift_pro(paint, shape, mask, seed, pm, bb,
                                primary_hue=45, shift_range=90,
                                flake_size=5, flake_hue_spread=0.04)

def spec_colorshift_solarflare(shape, mask, seed, sm):
    """Coordinated spec for Color Shift Solar Flare"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=225, M_range=30, R_base=10, R_var=5,
                               CC_base=16, CC_range=12)
