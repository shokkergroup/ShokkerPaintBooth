"""
Shokker FUSIONS Expansion — "Paradigm Shift Hybrids"
=====================================================
150 finishes: 10 for each of the 15 Paradigm Shifts from the Spec Map Bible.

FUSIONS are a NEW 4th category — not bases, not patterns, not specials.
They are multi-material hybrid systems where TWO OR MORE complete material
states blend per-pixel using noise, gradients, or geometric fields.

Each Fusion has its own spec_fn and paint_fn (monolithic format).

Registry: FUSION_REGISTRY  (spec_fn, paint_fn) tuples
Integration: integrate_fusions(engine_module) merges into engine
"""

import numpy as np
from PIL import Image, ImageFilter

# ================================================================
# HELPERS
# ================================================================

def _mgrid(shape):
    return np.mgrid[0:shape[0], 0:shape[1]]

def _noise(shape, scales, weights, seed):
    """Multi-octave noise."""
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    for s, wt in zip(scales, weights):
        raw = rng.randn(max(1, h // s), max(1, w // s)).astype(np.float32)
        img = Image.fromarray((raw * 127 + 128).clip(0, 255).astype(np.uint8))
        up = np.array(img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 127.0 - 1.0
        result += up * wt
    return result

def _hsv_to_rgb(h, s, v):
    """Vectorized HSV→RGB."""
    h6 = (h % 1.0) * 6.0
    i = np.floor(h6).astype(np.int32) % 6
    f = h6 - np.floor(h6)
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    r = np.where(i == 0, v, np.where(i == 1, q, np.where(i == 2, p, np.where(i == 3, p, np.where(i == 4, t, v)))))
    g = np.where(i == 0, t, np.where(i == 1, v, np.where(i == 2, v, np.where(i == 3, q, np.where(i == 4, p, p)))))
    b = np.where(i == 0, p, np.where(i == 1, p, np.where(i == 2, t, np.where(i == 3, v, np.where(i == 4, v, q)))))
    return r, g, b

def _spec_out(shape, mask, M, G, B):
    """Standard spec output helper."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(G * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(B * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _blend_materials(blend, mat_a, mat_b):
    """Blend two (M,G,B) material tuples using a 0-1 blend field."""
    M = mat_a[0] * (1 - blend) + mat_b[0] * blend
    G = mat_a[1] * (1 - blend) + mat_b[1] * blend
    B = mat_a[2] * (1 - blend) + mat_b[2] * blend
    return M, G, B

def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint

def _paint_brighten(paint, shape, mask, seed, pm, bb):
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# PARADIGM 1: MULTI-MATERIAL GRADIENT — Spatial material transitions
# ================================================================

def _gradient_y(shape):
    h, w = shape
    return np.linspace(0, 1, h).reshape(h, 1).astype(np.float32) * np.ones((1, w), dtype=np.float32)

def _gradient_x(shape):
    h, w = shape
    return np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, w).reshape(1, w).astype(np.float32)

def _gradient_diag(shape):
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1)
    x = np.linspace(0, 1, w).reshape(1, w)
    return np.clip((y + x) / 2.0, 0, 1).astype(np.float32)

def _gradient_radial(shape):
    h, w = shape
    y = np.linspace(-1, 1, h).reshape(h, 1)
    x = np.linspace(-1, 1, w).reshape(1, w)
    return np.clip(np.sqrt(y**2 + x**2) / 1.414, 0, 1).astype(np.float32)

def _make_gradient_fusion(mat_a, mat_b, grad_fn, seed_offset=0, warp=False, paint_warm=False):
    """Factory for gradient fusions."""
    def spec_fn(shape, mask, seed, sm):
        grad = grad_fn(shape)
        if warp:
            warp_noise = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 500)
            grad = np.clip(grad + warp_noise * 0.15, 0, 1)
        M, G, B = _blend_materials(grad, mat_a, mat_b)
        n = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset)
        M = M + n * 10 * sm
        G = G + n * 8 * sm
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        grad = grad_fn(shape)
        if warp:
            warp_noise = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 500)
            grad = np.clip(grad + warp_noise * 0.15, 0, 1)
        if paint_warm:
            warm = grad * 0.08 * pm
            paint[:,:,0] = np.clip(paint[:,:,0] + warm * mask, 0, 1)
            cool = (1 - grad) * 0.06 * pm
            paint[:,:,2] = np.clip(paint[:,:,2] + cool * mask, 0, 1)
        bright = np.where(grad < 0.5, grad * 0.15, (1 - grad) * 0.15) * pm
        paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

# Chrome(255,2,0) → Matte(0,200,0)
spec_gradient_chrome_matte, paint_gradient_chrome_matte = _make_gradient_fusion((255,2,0), (0,200,0), _gradient_y, 7000)
# Candy(200,15,16) → Frozen(225,140,0)
spec_gradient_candy_frozen, paint_gradient_candy_frozen = _make_gradient_fusion((200,15,16), (225,140,0), _gradient_y, 7010, paint_warm=True)
# Pearl(100,40,16) → Chrome(255,2,0)
spec_gradient_pearl_chrome, paint_gradient_pearl_chrome = _make_gradient_fusion((100,40,16), (255,2,0), _gradient_diag, 7020)
# Metallic(200,50,16) → Satin(0,100,10)
spec_gradient_metallic_satin, paint_gradient_metallic_satin = _make_gradient_fusion((200,50,16), (0,100,10), _gradient_x, 7030)
# Liquid Obs(130,6,16) → Chrome(255,2,0)
spec_gradient_obsidian_mirror, paint_gradient_obsidian_mirror = _make_gradient_fusion((130,6,16), (255,2,0), _gradient_radial, 7040)
# Candy(200,15,16) → Matte(0,215,0)
spec_gradient_candy_matte, paint_gradient_candy_matte = _make_gradient_fusion((200,15,16), (0,215,0), _gradient_y, 7050, warp=True)
# Anodized(170,80,0) → Wet Gloss(10,5,16)
spec_gradient_anodized_gloss, paint_gradient_anodized_gloss = _make_gradient_fusion((170,80,0), (10,5,16), _gradient_diag, 7060)
# Ember(200,40,16) → Frozen(225,140,0)
spec_gradient_ember_ice, paint_gradient_ember_ice = _make_gradient_fusion((200,40,16), (225,140,0), _gradient_y, 7070, paint_warm=True)
# Carbon(55,35,16) → Chrome(255,2,0)
spec_gradient_carbon_chrome, paint_gradient_carbon_chrome = _make_gradient_fusion((55,35,16), (255,2,0), _gradient_y, 7080, warp=True)
# Spectraflame(245,8,16) → Vantablack(0,255,0)
spec_gradient_spectraflame_void, paint_gradient_spectraflame_void = _make_gradient_fusion((245,8,16), (0,255,0), _gradient_radial, 7090)


# ================================================================
# PARADIGM 2: CLEARCOAT-ONLY PATTERNING — Ghost geometry in CC
# ================================================================

def _make_ghost_fusion(base_m, base_g, pattern_fn_name, seed_offset=0):
    """Factory: uniform M/G everywhere, CC varies via pattern."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        # Generate pattern field 0-1
        if pattern_fn_name == "hex":
            y, x = _mgrid(shape)
            hex_size = max(16, min(h, w) // 20)
            row = y / (hex_size * 0.866)
            col = x / hex_size
            col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
            cy = np.round(row) * hex_size * 0.866
            cx = (np.round(col_shifted) + 0.5 * (np.round(row).astype(int) % 2)) * hex_size
            dist = np.sqrt((y - cy)**2 + (x - cx)**2)
            pv = (dist / (hex_size * 0.45) > 0.75).astype(np.float32)
        elif pattern_fn_name == "stripes":
            y = np.arange(h).reshape(-1, 1)
            stripe_w = max(8, h // 30)
            pv = ((y % (stripe_w * 4)) < stripe_w).astype(np.float32)
            pv = np.broadcast_to(pv, (h, w)).copy()
        elif pattern_fn_name == "diamonds":
            y, x = _mgrid(shape)
            sz = max(20, min(h, w) // 25)
            dx = (x % sz) - sz / 2
            dy = (y % sz) - sz / 2
            pv = ((np.abs(dx) + np.abs(dy)) < sz * 0.38).astype(np.float32)
        elif pattern_fn_name == "waves":
            y, x = _mgrid(shape)
            yf = y.astype(np.float32)
            xf = x.astype(np.float32)
            wave = np.sin(yf * 0.03 + xf * 0.015) * 0.4 + np.sin(yf * 0.015 - xf * 0.02) * 0.3
            pv = np.clip((wave + 0.7) * 0.7, 0, 1)
        elif pattern_fn_name == "camo":
            rng = np.random.RandomState(seed + seed_offset + 100)
            bh, bw = max(1, h // 16), max(1, w // 16)
            raw = rng.random((bh, bw)).astype(np.float32)
            img = Image.fromarray((raw * 255).astype(np.uint8))
            pv = np.array(img.resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0
            pv = np.where(pv > 0.5, 1.0, 0.0)
        elif pattern_fn_name == "scales":
            y, x = _mgrid(shape)
            sz = max(18, min(h, w) // 25)
            row = y // sz
            col = (x + (row % 2) * (sz // 2)) // sz
            cy = (row + 0.5) * sz
            cx = col * sz + (row % 2) * (sz // 2) + sz // 2
            dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (sz * 0.55)
            pv = np.clip(dist, 0, 1)
        elif pattern_fn_name == "circuit":
            rng = np.random.RandomState(seed + seed_offset + 100)
            grid_s = max(12, min(h, w) // 40)
            gh, gw = h // grid_s + 1, w // grid_s + 1
            nodes = rng.random((gh, gw)) > 0.6
            canvas = np.zeros((h, w), dtype=np.float32)
            for gy in range(gh):
                for gx in range(gw):
                    if nodes[gy, gx]:
                        py, px = gy * grid_s, gx * grid_s
                        canvas[max(0,py-1):min(h,py+2), max(0,px-grid_s):min(w,px+grid_s)] = 1.0
                        canvas[max(0,py-grid_s):min(h,py+grid_s), max(0,px-1):min(w,px+2)] = 1.0
            pv = canvas
        elif pattern_fn_name == "vortex":
            y = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            angle = np.arctan2(y, x)
            dist = np.sqrt(y**2 + x**2)
            spiral = np.sin(angle * 5 + dist * 15) * 0.5 + 0.5
            pv = np.clip(spiral, 0, 1)
        elif pattern_fn_name == "fracture":
            n1 = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            n2 = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + seed_offset + 200)
            cracks = np.exp(-n1**2 * 20) + np.exp(-n2**2 * 20)
            pv = np.clip(cracks, 0, 1)
        elif pattern_fn_name == "quilt":
            ps = max(16, min(h, w) // 30)
            y, x = _mgrid(shape)
            panel_y = (y // ps) % 2
            panel_x = (x // ps) % 2
            pv = (panel_y ^ panel_x).astype(np.float32)
        else:
            pv = np.zeros((h, w), dtype=np.float32)

        M = np.full((h, w), float(base_m), dtype=np.float32)
        G = np.full((h, w), float(base_g), dtype=np.float32)
        # Clearcoat: pattern areas get perfect CC=16, non-pattern gets hazed CC
        B = pv * 16.0 + (1 - pv) * 100.0
        # Make the ghost pattern pop slightly in metallic and roughness as well
        M = np.clip(M + pv * 60.0 * sm, 0, 255)
        G = np.clip(G - pv * 30.0 * sm, 0, 255)
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset)
        M = np.clip(M + n * 8 * sm, 0, 255)
        G = np.clip(G + n * 6 * sm, 0, 255)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        # Ghost patterns are subtle — minimal paint modification
        n = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset)
        shimmer = np.clip(n * 0.04 * pm, -0.04, 0.04)
        paint = np.clip(paint + shimmer[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_ghost_hex, paint_ghost_hex = _make_ghost_fusion(200, 40, "hex", 7100)
spec_ghost_stripes, paint_ghost_stripes = _make_ghost_fusion(255, 5, "stripes", 7110)
spec_ghost_diamonds, paint_ghost_diamonds = _make_ghost_fusion(200, 15, "diamonds", 7120)
spec_ghost_waves, paint_ghost_waves = _make_ghost_fusion(100, 40, "waves", 7130)
spec_ghost_camo, paint_ghost_camo = _make_ghost_fusion(200, 50, "camo", 7140)
spec_ghost_scales, paint_ghost_scales = _make_ghost_fusion(235, 65, "scales", 7150)
spec_ghost_circuit, paint_ghost_circuit = _make_ghost_fusion(250, 5, "circuit", 7160)
spec_ghost_vortex, paint_ghost_vortex = _make_ghost_fusion(245, 8, "vortex", 7170)
spec_ghost_fracture, paint_ghost_fracture = _make_ghost_fusion(170, 80, "fracture", 7180)
spec_ghost_quilt, paint_ghost_quilt = _make_ghost_fusion(220, 40, "quilt", 7190)


# ================================================================
# PARADIGM 3: ANISOTROPIC ROUGHNESS — Directional grain simulation
# ================================================================

def _make_aniso_fusion(base_m, base_g, base_cc, grain_fn_name, seed_offset=0):
    """Factory: directional roughness grain."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)
        if grain_fn_name == "horizontal":
            grain = rng.randn(h, 1).astype(np.float32) * 1.0
            grain = np.tile(grain, (1, w))
            grain += rng.randn(h, w).astype(np.float32) * 0.15
        elif grain_fn_name == "vertical":
            grain = rng.randn(1, w).astype(np.float32) * 1.0
            grain = np.tile(grain, (h, 1))
            grain += rng.randn(h, w).astype(np.float32) * 0.15
        elif grain_fn_name == "diagonal":
            diag = rng.randn(h + w, 1).astype(np.float32) * 1.0
            y, x = _mgrid(shape)
            idx = np.clip(y + x, 0, h + w - 1)
            grain = diag[idx, 0] + rng.randn(h, w).astype(np.float32) * 0.12
        elif grain_fn_name == "radial":
            y = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            angle = np.arctan2(y, x)
            grain = np.sin(angle * 40) * 0.5 + rng.randn(h, w).astype(np.float32) * 0.2
        elif grain_fn_name == "circular":
            y = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            dist = np.sqrt(y**2 + x**2)
            grain = np.sin(dist * 60) * 0.6 + rng.randn(h, w).astype(np.float32) * 0.15
        elif grain_fn_name == "crosshatch":
            d1 = rng.randn(h + w, 1).astype(np.float32) * 0.7
            d2 = rng.randn(h + w, 1).astype(np.float32) * 0.7
            y, x = _mgrid(shape)
            grain = d1[np.clip(y + x, 0, h+w-1), 0] + d2[np.clip(y - x + w, 0, h+w-1), 0]
            grain += rng.randn(h, w).astype(np.float32) * 0.1
        elif grain_fn_name == "spiral":
            y = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            angle = np.arctan2(y, x)
            dist = np.sqrt(y**2 + x**2)
            grain = np.sin(angle * 8 + dist * 25) * 0.6 + rng.randn(h, w).astype(np.float32) * 0.15
        elif grain_fn_name == "wave":
            y_arr = np.arange(h, dtype=np.float32).reshape(h, 1)
            x_arr = np.arange(w, dtype=np.float32).reshape(1, w)
            wave = np.sin(y_arr * 0.04 + np.sin(x_arr * 0.02) * 4)
            grain_base = rng.randn(1, w).astype(np.float32) * 0.8
            grain = np.tile(grain_base, (h, 1)) * (wave * 0.3 + 0.7)
            grain += rng.randn(h, w).astype(np.float32) * 0.12
        elif grain_fn_name == "herringbone":
            y, x = _mgrid(shape)
            block_h = max(12, h // 40)
            row_block = (y // block_h) % 2
            diag_idx_a = y + x
            diag_idx_b = y - x + w
            grain_a = rng.randn(h + w).astype(np.float32)
            grain_b = rng.randn(h + w).astype(np.float32)
            ga = grain_a[np.clip(diag_idx_a, 0, h+w-1)]
            gb = grain_b[np.clip(diag_idx_b, 0, h+w-1)]
            grain = np.where(row_block == 0, ga, gb) * 0.8
            grain += rng.randn(h, w).astype(np.float32) * 0.1
        elif grain_fn_name == "turbulence":
            grain = _noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            grain = np.abs(grain) * 1.5
        else:
            grain = rng.randn(h, w).astype(np.float32)

        grain_norm = np.clip((grain + 2) / 4, 0, 1)
        M = np.full((h, w), float(base_m), dtype=np.float32)
        M = M + grain_norm * 15 * sm
        G = float(base_g) + grain_norm * 45 * sm
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 50)
        sheen = np.clip(n * 0.03 * pm, -0.03, 0.03)
        paint = np.clip(paint + sheen[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_aniso_horizontal_chrome, paint_aniso_horizontal_chrome = _make_aniso_fusion(255, 5, 0, "horizontal", 7200)
spec_aniso_vertical_pearl, paint_aniso_vertical_pearl = _make_aniso_fusion(100, 30, 16, "vertical", 7210)
spec_aniso_diagonal_candy, paint_aniso_diagonal_candy = _make_aniso_fusion(200, 15, 16, "diagonal", 7220)
spec_aniso_radial_metallic, paint_aniso_radial_metallic = _make_aniso_fusion(200, 40, 16, "radial", 7230)
spec_aniso_circular_chrome, paint_aniso_circular_chrome = _make_aniso_fusion(255, 3, 0, "circular", 7240)
spec_aniso_crosshatch_steel, paint_aniso_crosshatch_steel = _make_aniso_fusion(245, 6, 0, "crosshatch", 7250)
spec_aniso_spiral_mercury, paint_aniso_spiral_mercury = _make_aniso_fusion(255, 3, 0, "spiral", 7260)
spec_aniso_wave_titanium, paint_aniso_wave_titanium = _make_aniso_fusion(180, 60, 0, "wave", 7270)
spec_aniso_herringbone_gold, paint_aniso_herringbone_gold = _make_aniso_fusion(240, 12, 0, "herringbone", 7280)
spec_aniso_turbulence_metal, paint_aniso_turbulence_metal = _make_aniso_fusion(220, 35, 16, "turbulence", 7290)


# ================================================================
# PARADIGM 4: REACTIVE METALLIC ZONES — Fresnel-differentiated panels
# ================================================================

def _make_reactive_fusion(m_low, m_high, base_g, base_cc, seed_offset=0):
    """Factory: two metallic zones, same everything else."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        zones = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset)
        zone_mask = np.clip(zones * 0.5 + 0.5, 0, 1)
        zone_sharp = np.where(zone_mask > 0.5, 1.0, 0.0).astype(np.float32)
        M = m_low * (1 - zone_sharp) + m_high * zone_sharp
        n = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        M = M + n * 8 * sm
        G = np.full((h, w), float(base_g), dtype=np.float32) + n * 5 * sm
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        zones = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset)
        zone_mask = np.where(zones > 0, 1.0, 0.0).astype(np.float32)
        # Slightly differentiate color temperature between zones
        warm = zone_mask * 0.04 * pm
        paint[:,:,0] = np.clip(paint[:,:,0] + warm * mask, 0, 1)
        cool = (1 - zone_mask) * 0.03 * pm
        paint[:,:,2] = np.clip(paint[:,:,2] + cool * mask, 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_reactive_stealth_pop, paint_reactive_stealth_pop = _make_reactive_fusion(30, 220, 30, 16, 7300)
spec_reactive_pearl_flash, paint_reactive_pearl_flash = _make_reactive_fusion(60, 200, 40, 16, 7310)
spec_reactive_candy_reveal, paint_reactive_candy_reveal = _make_reactive_fusion(100, 240, 15, 16, 7320)
spec_reactive_chrome_fade, paint_reactive_chrome_fade = _make_reactive_fusion(150, 255, 5, 0, 7330)
spec_reactive_matte_shine, paint_reactive_matte_shine = _make_reactive_fusion(0, 180, 60, 16, 7340)
spec_reactive_dual_tone, paint_reactive_dual_tone = _make_reactive_fusion(80, 200, 80, 10, 7350)
spec_reactive_ghost_metal, paint_reactive_ghost_metal = _make_reactive_fusion(40, 240, 20, 16, 7360)
spec_reactive_mirror_shadow, paint_reactive_mirror_shadow = _make_reactive_fusion(200, 255, 3, 0, 7370)
spec_reactive_warm_cold, paint_reactive_warm_cold = _make_reactive_fusion(60, 220, 40, 16, 7380)
spec_reactive_pulse_metal, paint_reactive_pulse_metal = _make_reactive_fusion(20, 250, 25, 16, 7390)


# ================================================================
# PARADIGM 5: STOCHASTIC SPARKLE — Micro-mirror individuality
# ================================================================

def _make_sparkle_fusion(base_m, base_g, density, seed_offset=0, cluster=False, trails=False):
    """Factory: sparse sparkle points on moderate metallic base."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)
        M = np.full((h, w), float(base_m), dtype=np.float32)
        G = np.full((h, w), float(base_g), dtype=np.float32)
        # Sparkle points
        sparkle_map = rng.random((h, w)).astype(np.float32)
        threshold = 1.0 - density * 0.01 * sm
        sparkles = (sparkle_map > threshold).astype(np.float32)
        if cluster:
            sparkle_img = Image.fromarray((sparkles * 255).astype(np.uint8))
            sparkle_img = sparkle_img.filter(ImageFilter.GaussianBlur(radius=2))
            cluster_map = np.array(sparkle_img).astype(np.float32) / 255.0
            sparkles = np.clip(sparkles + cluster_map * 0.5, 0, 1)
        if trails:
            for _ in range(3):
                sparkles[:, 1:] = np.maximum(sparkles[:, 1:], sparkles[:, :-1] * 0.4)
        M = M * (1 - sparkles) + 255 * sparkles
        G = G * (1 - sparkles) + 2 * sparkles
        n = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        M = M + n * 6 * sm * (1 - sparkles)
        G = G + n * 5 * sm * (1 - sparkles)
        return _spec_out(shape, mask, M, G, np.full((h, w), 16.0))

    def paint_fn(paint, shape, mask, seed, pm, bb):
        rng = np.random.RandomState(seed + seed_offset)
        sparkle_map = rng.random(shape).astype(np.float32)
        threshold = 1.0 - density * 0.01
        sparkles = (sparkle_map > threshold).astype(np.float32)
        bright = sparkles * 0.12 * pm
        paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_sparkle_diamond_dust, paint_sparkle_diamond_dust = _make_sparkle_fusion(160, 50, 4, 7400)
spec_sparkle_starfield, paint_sparkle_starfield = _make_sparkle_fusion(140, 60, 2, 7410)
spec_sparkle_galaxy, paint_sparkle_galaxy = _make_sparkle_fusion(100, 45, 3, 7420, cluster=True)
spec_sparkle_firefly, paint_sparkle_firefly = _make_sparkle_fusion(180, 35, 1.5, 7430)
spec_sparkle_snowfall, paint_sparkle_snowfall = _make_sparkle_fusion(200, 30, 5, 7440)
spec_sparkle_champagne, paint_sparkle_champagne = _make_sparkle_fusion(220, 25, 3.5, 7450)
spec_sparkle_meteor, paint_sparkle_meteor = _make_sparkle_fusion(160, 55, 2, 7460, trails=True)
spec_sparkle_constellation, paint_sparkle_constellation = _make_sparkle_fusion(120, 50, 1, 7470, cluster=True)
spec_sparkle_confetti, paint_sparkle_confetti = _make_sparkle_fusion(180, 40, 4, 7480)
spec_sparkle_lightning_bug, paint_sparkle_lightning_bug = _make_sparkle_fusion(130, 60, 1.5, 7490)


# ================================================================
# PARADIGM 6: MACRO vs MICRO ROUGHNESS — Multi-scale surface
# ================================================================

def _make_multiscale_fusion(base_m, macro_scales, micro_scales, r_base, r_macro, r_micro, base_cc, seed_offset=0):
    """Factory: large-scale roughness zones + fine-grained texture within."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        macro = _noise(shape, macro_scales, [0.3, 0.4, 0.3][:len(macro_scales)], seed + seed_offset)
        macro = np.clip(macro * 0.5 + 0.5, 0, 1)
        micro = _noise(shape, micro_scales, [0.3, 0.4, 0.3][:len(micro_scales)], seed + seed_offset + 100)
        micro = np.clip(micro * 0.5 + 0.5, 0, 1)
        G = r_base + macro * r_macro * sm + micro * r_micro * sm
        M = np.full((h, w), float(base_m), dtype=np.float32) + macro * 15 * sm
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        macro = _noise(shape, macro_scales, [0.3, 0.4, 0.3][:len(macro_scales)], seed + seed_offset)
        bright = np.clip(macro * 0.05 * pm, -0.05, 0.05)
        paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_multiscale_chrome_grain, paint_multiscale_chrome_grain = _make_multiscale_fusion(255, [64, 128], [4, 8], 5, 40, 15, 0, 7500)
spec_multiscale_candy_frost, paint_multiscale_candy_frost = _make_multiscale_fusion(200, [64, 128], [8, 16], 15, 60, 20, 16, 7510)
spec_multiscale_metal_grit, paint_multiscale_metal_grit = _make_multiscale_fusion(220, [32, 64], [2, 4], 30, 50, 25, 16, 7520)
spec_multiscale_pearl_texture, paint_multiscale_pearl_texture = _make_multiscale_fusion(100, [64, 128], [4, 8], 30, 35, 15, 16, 7530)
spec_multiscale_satin_weave, paint_multiscale_satin_weave = _make_multiscale_fusion(235, [48, 96], [6, 12], 50, 30, 20, 16, 7540)
spec_multiscale_chrome_sand, paint_multiscale_chrome_sand = _make_multiscale_fusion(255, [96, 192], [3, 6], 3, 50, 18, 0, 7550)
spec_multiscale_matte_silk, paint_multiscale_matte_silk = _make_multiscale_fusion(30, [64, 128], [4, 8], 140, -60, 20, 16, 7560)
spec_multiscale_flake_grain, paint_multiscale_flake_grain = _make_multiscale_fusion(240, [64, 128], [2, 4], 10, 30, 12, 16, 7570)
spec_multiscale_carbon_micro, paint_multiscale_carbon_micro = _make_multiscale_fusion(55, [48, 96], [3, 6], 30, 40, 15, 16, 7580)
spec_multiscale_frost_crystal, paint_multiscale_frost_crystal = _make_multiscale_fusion(225, [80, 160], [4, 8], 80, 50, 20, 0, 7590)


# ================================================================
# PARADIGM 7: CLEARCOAT WEATHER GRADIENT — Environmental storytelling
# ================================================================

def _make_weather_fusion(base_m, base_g, cc_top, cc_bottom, seed_offset=0, invert_y=False, spot_damage=False, paint_tint=None):
    """Factory: clearcoat degrades along a gradient, telling a weather story."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        grad = _gradient_y(shape)
        if invert_y:
            grad = 1.0 - grad
        # Add noise to break up perfect gradient
        weather_noise = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset)
        grad = np.clip(grad + weather_noise * 0.12, 0, 1)
        CC = cc_top * (1 - grad) + cc_bottom * grad
        if spot_damage:
            spots = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 200)
            spot_mask = np.where(spots > 0.6, 1.0, 0.0).astype(np.float32)
            CC = CC + spot_mask * 40 * sm
        M = np.full((h, w), float(base_m), dtype=np.float32)
        G = np.full((h, w), float(base_g), dtype=np.float32)
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 50)
        M = M + n * 8 * sm
        G = G + n * 6 * sm
        return _spec_out(shape, mask, M, G, CC)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        grad = _gradient_y(shape)
        if invert_y:
            grad = 1.0 - grad
        if paint_tint == "warm":
            warm = (1 - grad) * 0.06 * pm
            paint[:,:,0] = np.clip(paint[:,:,0] + warm * mask, 0, 1)
            paint[:,:,1] = np.clip(paint[:,:,1] + warm * 0.4 * mask, 0, 1)
        elif paint_tint == "cool":
            cool = grad * 0.05 * pm
            paint[:,:,2] = np.clip(paint[:,:,2] + cool * mask, 0, 1)
        elif paint_tint == "dirty":
            dirt = grad * 0.08 * pm
            paint[:,:,0] = np.clip(paint[:,:,0] - dirt * 0.3 * mask, 0, 1)
            paint[:,:,1] = np.clip(paint[:,:,1] - dirt * 0.2 * mask, 0, 1)
        darken = np.where(grad > 0.7, (grad - 0.7) * 0.15 * pm, 0.0)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] - darken * mask, 0, 1)
        paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_weather_sun_fade, paint_weather_sun_fade = _make_weather_fusion(200, 40, 200, 16, 7600, paint_tint="warm")
spec_weather_salt_spray, paint_weather_salt_spray = _make_weather_fusion(200, 50, 80, 180, 7610, invert_y=True, paint_tint="dirty")
spec_weather_acid_rain, paint_weather_acid_rain = _make_weather_fusion(180, 45, 160, 40, 7620, spot_damage=True)
spec_weather_desert_blast, paint_weather_desert_blast = _make_weather_fusion(190, 55, 220, 60, 7630, paint_tint="warm")
spec_weather_ice_storm, paint_weather_ice_storm = _make_weather_fusion(220, 35, 16, 200, 7640, invert_y=True, paint_tint="cool")
spec_weather_road_spray, paint_weather_road_spray = _make_weather_fusion(200, 50, 30, 160, 7650, invert_y=True, paint_tint="dirty")
spec_weather_hood_bake, paint_weather_hood_bake = _make_weather_fusion(200, 40, 200, 16, 7660, paint_tint="warm")
spec_weather_barn_dust, paint_weather_barn_dust = _make_weather_fusion(180, 55, 120, 80, 7670, paint_tint="warm")
spec_weather_ocean_mist, paint_weather_ocean_mist = _make_weather_fusion(200, 45, 60, 140, 7680, paint_tint="cool")
spec_weather_volcanic_ash, paint_weather_volcanic_ash = _make_weather_fusion(160, 60, 180, 100, 7690, spot_damage=True, paint_tint="warm")


# ================================================================
# PARADIGM 8: DIELECTRIC MIRROR — Impossible Fresnel exploits
# ================================================================

def _make_impossible_fusion(base_m, base_g, base_cc, seed_offset=0, noise_m=5, noise_g=3):
    """Factory: physics-defying finishes using extreme frequency noise and glitch aesthetics."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        # Extreme frequency noise
        n1 = _noise(shape, [2, 4, 8, 16, 32], [0.2, 0.3, 0.3, 0.1, 0.1], seed + seed_offset)
        # Geometric glitch effect (stepped noise)
        gf = (n1 * 10).astype(np.int32).astype(np.float32) / 10.0
        n2 = _noise(shape, [1, 3, 7, 15], [0.4, 0.3, 0.2, 0.1], seed + seed_offset + 50)
        M = np.clip(np.full((h, w), float(base_m), dtype=np.float32) + (gf * 100 - 50) * sm * noise_m/5, 0, 255)
        G = np.clip(np.full((h, w), float(base_g), dtype=np.float32) + (n2 * 255 - 127) * sm * noise_g/3, 0, 255)
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        # Impossible paint: hue shifting glitch blocks
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 80)
        glitch = (n * 5).astype(np.int32).astype(np.float32) / 5.0
        shift = np.clip(glitch * 0.2 * pm, -0.2, 0.2)
        # Add high-contrast brightness shifting
        paint = np.clip(paint + shift[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        contrast = np.clip(paint + bb * 0.5 * (glitch * 2 - 1)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        return contrast
    return spec_fn, paint_fn

spec_impossible_glass_paint, paint_impossible_glass_paint = _make_impossible_fusion(0, 0, 16, 7700, 3, 2)
spec_impossible_foggy_chrome, paint_impossible_foggy_chrome = _make_impossible_fusion(255, 0, 255, 7710, 5, 3)
spec_impossible_inverted_candy, paint_impossible_inverted_candy = _make_impossible_fusion(0, 2, 200, 7720, 3, 2)
spec_impossible_liquid_glass, paint_impossible_liquid_glass = _make_impossible_fusion(0, 3, 16, 7730, 2, 2)
spec_impossible_phantom_mirror, paint_impossible_phantom_mirror = _make_impossible_fusion(0, 0, 0, 7740, 3, 2)
spec_impossible_ceramic_void, paint_impossible_ceramic_void = _make_impossible_fusion(0, 1, 16, 7750, 2, 1)
spec_impossible_anti_metal, paint_impossible_anti_metal = _make_impossible_fusion(5, 0, 255, 7760, 3, 2)
spec_impossible_crystal_clear, paint_impossible_crystal_clear = _make_impossible_fusion(0, 5, 16, 7770, 3, 3)
spec_impossible_dark_glass, paint_impossible_dark_glass = _make_impossible_fusion(10, 0, 50, 7780, 5, 2)
spec_impossible_wet_void, paint_impossible_wet_void = _make_impossible_fusion(0, 2, 16, 7790, 2, 2)


# ================================================================
# PARADIGM 9: TRI-ZONE MATERIAL FENCING — 3 materials in 1 zone
# ================================================================

def _make_trizone_fusion(mat_a, mat_b, mat_c, seed_offset=0):
    """Factory: noise-driven 3-zone material distribution."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset)
        n = np.clip(noise * 0.5 + 0.5, 0, 1)
        zone_a = (n > 0.66).astype(np.float32)
        zone_b = ((n > 0.33) & (n <= 0.66)).astype(np.float32)
        zone_c = (n <= 0.33).astype(np.float32)
        M = mat_a[0] * zone_a + mat_b[0] * zone_b + mat_c[0] * zone_c
        G = mat_a[1] * zone_a + mat_b[1] * zone_b + mat_c[1] * zone_c
        B = mat_a[2] * zone_a + mat_b[2] * zone_b + mat_c[2] * zone_c
        fine = _noise(shape, [4, 8], [0.5, 0.5], seed + seed_offset + 100)
        M = M + fine * 6 * sm
        G = G + fine * 5 * sm
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset)
        n = np.clip(noise * 0.5 + 0.5, 0, 1)
        # Subtle color differentiation between zones
        zone_a = (n > 0.66).astype(np.float32) * 0.04 * pm
        zone_c = (n <= 0.33).astype(np.float32) * 0.03 * pm
        paint[:,:,0] = np.clip(paint[:,:,0] + zone_a * mask, 0, 1)
        paint[:,:,2] = np.clip(paint[:,:,2] + zone_c * mask, 0, 1)
        # Edge glow between zones
        edge = np.abs(np.diff(n, axis=1, prepend=n[:,:1])) + np.abs(np.diff(n, axis=0, prepend=n[:1,:]))
        rim = np.clip(edge * 6, 0, 1) * 0.10 * pm
        paint = np.clip(paint + rim[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

# Chrome / Candy / Matte
spec_trizone_chrome_candy_matte, paint_trizone_chrome_candy_matte = _make_trizone_fusion((255,2,0), (200,15,16), (0,200,0), 7800)
spec_trizone_pearl_carbon_gold, paint_trizone_pearl_carbon_gold = _make_trizone_fusion((100,40,16), (55,35,16), (255,2,0), 7810)
spec_trizone_frozen_ember_chrome, paint_trizone_frozen_ember_chrome = _make_trizone_fusion((225,140,0), (200,40,16), (255,2,0), 7820)
spec_trizone_anodized_candy_silk, paint_trizone_anodized_candy_silk = _make_trizone_fusion((170,80,0), (200,15,16), (30,85,16), 7830)
spec_trizone_vanta_chrome_pearl, paint_trizone_vanta_chrome_pearl = _make_trizone_fusion((0,255,0), (255,2,0), (100,40,16), 7840)
spec_trizone_glass_metal_matte, paint_trizone_glass_metal_matte = _make_trizone_fusion((0,0,16), (200,50,16), (0,200,0), 7850)
spec_trizone_mercury_obsidian_candy, paint_trizone_mercury_obsidian_candy = _make_trizone_fusion((255,3,0), (130,6,16), (200,15,16), 7860)
spec_trizone_titanium_copper_chrome, paint_trizone_titanium_copper_chrome = _make_trizone_fusion((180,70,0), (190,55,16), (255,2,0), 7870)
spec_trizone_ceramic_flake_satin, paint_trizone_ceramic_flake_satin = _make_trizone_fusion((60,8,16), (240,12,16), (0,100,10), 7880)
spec_trizone_stealth_spectra_frozen, paint_trizone_stealth_spectra_frozen = _make_trizone_fusion((30,220,0), (245,8,16), (225,140,0), 7890)


# ================================================================
# PARADIGM 10: DEPTH ILLUSION via CC Roughness — 3D from flat
# ================================================================

def _make_depth_fusion(base_m, base_g, cc_deep, cc_shallow, pattern_type, seed_offset=0):
    """Factory: clearcoat roughness creates depth illusion."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        if pattern_type == "canyon":
            field = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset)
            pv = np.clip(np.abs(field) * 2, 0, 1)
        elif pattern_type == "bubble":
            y = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            rng = np.random.RandomState(seed + seed_offset)
            pv = np.zeros((h, w), dtype=np.float32)
            for _ in range(15):
                cy, cx = rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)
                r = rng.uniform(0.05, 0.2)
                dist = np.sqrt((y - cy)**2 + (x - cx)**2)
                bubble = np.clip(1.0 - dist / r, 0, 1) ** 2
                pv = np.maximum(pv, bubble)
        elif pattern_type == "ripple":
            y, x = _mgrid(shape)
            yf, xf = y.astype(np.float32), x.astype(np.float32)
            cy, cx = h / 2.0, w / 2.0
            dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
            pv = np.sin(dist * 0.08) * 0.5 + 0.5
        elif pattern_type == "scale":
            y, x = _mgrid(shape)
            sz = max(18, min(h, w) // 25)
            row = y // sz
            col = (x + (row % 2) * (sz // 2)) // sz
            cy_s = (row + 0.5) * sz
            cx_s = col * sz + (row % 2) * (sz // 2) + sz // 2
            dist = np.sqrt((y - cy_s)**2 + (x - cx_s)**2) / (sz * 0.55)
            pv = 1.0 - np.clip(dist, 0, 1)
        elif pattern_type == "honeycomb":
            y, x = _mgrid(shape)
            sz = max(16, min(h, w) // 24)
            row = y / (sz * 0.866)
            col = x / sz
            col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
            cy_h = np.round(row) * sz * 0.866
            cx_h = (np.round(col_shifted) + 0.5 * (np.round(row).astype(int) % 2)) * sz
            dist = np.sqrt((y - cy_h)**2 + (x - cx_h)**2)
            pv = np.clip(1.0 - dist / (sz * 0.4), 0, 1)
        elif pattern_type == "crack":
            n1 = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            pv = np.exp(-n1**2 * 15)
        elif pattern_type == "wave":
            y, x = _mgrid(shape)
            yf = y.astype(np.float32)
            xf = x.astype(np.float32)
            wave = np.sin(yf * 0.025 + xf * 0.01) * 0.4 + np.sin(yf * 0.01 - xf * 0.018) * 0.3
            pv = np.clip((wave + 0.7) * 0.7, 0, 1)
        elif pattern_type == "pillow":
            y, x = _mgrid(shape)
            sz = max(24, min(h, w) // 20)
            cell_y = (y % sz).astype(np.float32) / sz
            cell_x = (x % sz).astype(np.float32) / sz
            pv = np.sin(cell_y * np.pi) * np.sin(cell_x * np.pi)
        elif pattern_type == "vortex":
            y = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            angle = np.arctan2(y, x)
            dist = np.sqrt(y**2 + x**2)
            pv = np.sin(angle * 3 + dist * 10) * 0.5 + 0.5
        elif pattern_type == "erosion":
            field = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            pv = np.clip(field * 0.5 + 0.5, 0, 1)
        else:
            pv = np.zeros((h, w), dtype=np.float32)

        M = np.full((h, w), float(base_m), dtype=np.float32)
        G = np.full((h, w), float(base_g), dtype=np.float32)
        CC = pv * cc_deep + (1 - pv) * cc_shallow
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 50)
        M = M + n * 8 * sm
        G = G + n * 5 * sm
        return _spec_out(shape, mask, M, G, CC)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        n = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 80)
        depth_shade = np.clip(n * 0.06 * pm, -0.06, 0.06)
        paint = np.clip(paint + depth_shade[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_depth_canyon, paint_depth_canyon = _make_depth_fusion(200, 35, 16, 140, "canyon", 7900)
spec_depth_bubble, paint_depth_bubble = _make_depth_fusion(220, 30, 16, 100, "bubble", 7910)
spec_depth_ripple, paint_depth_ripple = _make_depth_fusion(200, 40, 16, 120, "ripple", 7920)
spec_depth_scale, paint_depth_scale = _make_depth_fusion(210, 35, 16, 130, "scale", 7930)
spec_depth_honeycomb, paint_depth_honeycomb = _make_depth_fusion(220, 30, 16, 110, "honeycomb", 7940)
spec_depth_crack, paint_depth_crack = _make_depth_fusion(200, 35, 16, 150, "crack", 7950)
spec_depth_wave, paint_depth_wave = _make_depth_fusion(200, 40, 16, 100, "wave", 7960)
spec_depth_pillow, paint_depth_pillow = _make_depth_fusion(210, 35, 16, 90, "pillow", 7970)
spec_depth_vortex, paint_depth_vortex = _make_depth_fusion(220, 30, 16, 140, "vortex", 7980)
spec_depth_erosion, paint_depth_erosion = _make_depth_fusion(190, 40, 16, 160, "erosion", 7990)


# ================================================================
# PARADIGM 11: METALLIC HALO EFFECT — Glowing material outlines
# ================================================================

def _make_halo_fusion(center_m, halo_m, base_g, base_cc, pattern_type, seed_offset=0):
    """Factory: pattern elements with metallic halo rims around colored centers."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        if pattern_type == "hex":
            y, x = _mgrid(shape)
            sz = max(20, min(h, w) // 18)
            row = y / (sz * 0.866)
            col = x / sz
            col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
            cy = np.round(row) * sz * 0.866
            cx = (np.round(col_shifted) + 0.5 * (np.round(row).astype(int) % 2)) * sz
            dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (sz * 0.5)
            dist = np.clip(dist, 0, 1)
        elif pattern_type == "scale":
            y, x = _mgrid(shape)
            sz = max(20, min(h, w) // 20)
            row = y // sz
            col = (x + (row % 2) * (sz // 2)) // sz
            cy = (row + 0.5) * sz
            cx = col * sz + (row % 2) * (sz // 2) + sz // 2
            dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (sz * 0.55)
            dist = np.clip(dist, 0, 1)
        elif pattern_type == "circle":
            rng = np.random.RandomState(seed + seed_offset)
            y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
            dist = np.ones((h, w), dtype=np.float32)
            for _ in range(25):
                cy, cx = rng.uniform(0, 1), rng.uniform(0, 1)
                r = rng.uniform(0.03, 0.08)
                d = np.sqrt((y - cy)**2 + (x - cx)**2) / r
                dist = np.minimum(dist, np.clip(d, 0, 1))
        elif pattern_type == "diamond":
            y, x = _mgrid(shape)
            sz = max(16, min(h, w) // 25)
            dx = np.abs((x % sz) - sz / 2).astype(np.float32) / (sz / 2)
            dy = np.abs((y % sz) - sz / 2).astype(np.float32) / (sz / 2)
            dist = np.clip((dx + dy) / 1.2, 0, 1)
        elif pattern_type == "voronoi":
            rng = np.random.RandomState(seed + seed_offset)
            n_pts = 30
            pts_y = rng.randint(0, h, n_pts).astype(np.float32)
            pts_x = rng.randint(0, w, n_pts).astype(np.float32)
            y, x = _mgrid(shape)
            yf, xf = y.astype(np.float32), x.astype(np.float32)
            min_d = np.full((h, w), 1e6, dtype=np.float32)
            for py, px in zip(pts_y, pts_x):
                d = np.sqrt((yf - py)**2 + (xf - px)**2)
                min_d = np.minimum(min_d, d)
            max_r = min(h, w) * 0.08
            dist = np.clip(min_d / max_r, 0, 1)
        elif pattern_type == "wave":
            yf, xf = _mgrid(shape)
            wave = np.sin(yf * 0.025 + xf * 0.01) * 0.4 + np.sin(yf * 0.01 - xf * 0.018) * 0.3
            dist = 1.0 - np.clip((wave + 0.7) * 0.7, 0, 1)
        elif pattern_type == "crack":
            n1 = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            n2 = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + seed_offset + 200)
            dist = 1.0 - np.clip(np.exp(-n1**2 * 20) + np.exp(-n2**2 * 20), 0, 1)
        elif pattern_type in ("star", "grid", "ripple_ring"):
            # Simplified fallback for remaining
            field = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            field_norm = np.clip(field * 0.5 + 0.5, 0, 1)
            gy = np.abs(np.diff(field_norm, axis=0, prepend=field_norm[:1,:]))
            gx = np.abs(np.diff(field_norm, axis=1, prepend=field_norm[:,:1]))
            dist = 1.0 - np.clip((gy + gx) * 8, 0, 1)
        else:
            dist = np.zeros((h, w), dtype=np.float32)

        # center (dist≈0) = low metallic, rim (dist≈0.7-1.0) = high metallic
        rim_zone = np.clip((dist - 0.5) * 4, 0, 1)
        center_zone = np.clip(1.0 - dist * 2, 0, 1)
        M = center_m * center_zone + halo_m * rim_zone + (center_m + halo_m) / 2 * (1 - center_zone - rim_zone)
        G = np.full((h, w), float(base_g), dtype=np.float32)
        G = G * (1 - rim_zone) + 5.0 * rim_zone  # Rim is smooth
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        n = _noise(shape, [4, 8], [0.5, 0.5], seed + seed_offset + 50)
        M = M + n * 6 * sm
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        n = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 80)
        glow = np.clip(n * 0.05 * pm, -0.05, 0.05)
        paint = np.clip(paint + glow[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_halo_hex_chrome, paint_halo_hex_chrome = _make_halo_fusion(20, 240, 30, 16, "hex", 8000)
spec_halo_scale_gold, paint_halo_scale_gold = _make_halo_fusion(30, 250, 35, 0, "scale", 8010)
spec_halo_circle_pearl, paint_halo_circle_pearl = _make_halo_fusion(40, 200, 40, 16, "circle", 8020)
spec_halo_diamond_chrome, paint_halo_diamond_chrome = _make_halo_fusion(15, 255, 25, 0, "diamond", 8030)
spec_halo_voronoi_metal, paint_halo_voronoi_metal = _make_halo_fusion(25, 230, 35, 16, "voronoi", 8040)
spec_halo_wave_candy, paint_halo_wave_candy = _make_halo_fusion(50, 210, 15, 16, "wave", 8050)
spec_halo_crack_chrome, paint_halo_crack_chrome = _make_halo_fusion(20, 245, 30, 0, "crack", 8060)
spec_halo_star_metal, paint_halo_star_metal = _make_halo_fusion(30, 255, 25, 16, "star", 8070)
spec_halo_grid_pearl, paint_halo_grid_pearl = _make_halo_fusion(35, 220, 40, 16, "grid", 8080)
spec_halo_ripple_chrome, paint_halo_ripple_chrome = _make_halo_fusion(20, 240, 30, 0, "ripple_ring", 8090)


# ================================================================
# PARADIGM 12: DYNAMIC ROUGHNESS WAVES — Flowing light bands
# ================================================================

def _make_wave_fusion(base_m, r_min, r_max, wave_type, base_cc, seed_offset=0):
    """Factory: large-scale wave patterns in roughness creating flowing light bands."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        y, x = _mgrid(shape)
        yf = y.astype(np.float32)
        xf = x.astype(np.float32)
        if wave_type == "low":
            wave = np.sin(yf * 0.015 + xf * 0.008) * 0.5 + 0.5
        elif wave_type == "medium":
            wave = np.sin(yf * 0.03 + xf * 0.015) * 0.4 + np.sin(yf * 0.01) * 0.3 + 0.3
            wave = np.clip(wave, 0, 1)
        elif wave_type == "high":
            wave = np.sin(yf * 0.06 + xf * 0.03) * 0.3 + np.sin(yf * 0.04 - xf * 0.02) * 0.2 + 0.5
            wave = np.clip(wave, 0, 1)
        elif wave_type == "dual":
            w1 = np.sin(yf * 0.015 + xf * 0.008) * 0.5 + 0.5
            w2 = np.sin(yf * 0.06 + xf * 0.03) * 0.5 + 0.5
            wave = w1 * 0.6 + w2 * 0.4
        elif wave_type == "diagonal":
            wave = np.sin((yf + xf) * 0.02) * 0.4 + np.sin((yf - xf) * 0.015) * 0.3 + 0.3
            wave = np.clip(wave, 0, 1)
        elif wave_type == "radial":
            cy, cx = h / 2.0, w / 2.0
            dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
            wave = np.sin(dist * 0.06) * 0.5 + 0.5
        elif wave_type == "chaotic":
            n = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            wave = np.clip(n * 0.5 + 0.5, 0, 1)
        elif wave_type == "standing":
            wave = np.sin(yf * 0.025) * np.sin(xf * 0.025) * 0.5 + 0.5
        elif wave_type == "moire":
            w1 = np.sin(yf * 0.03 + xf * 0.01) * 0.5 + 0.5
            w2 = np.sin(yf * 0.028 + xf * 0.012) * 0.5 + 0.5
            wave = np.abs(w1 - w2) * 2
            wave = np.clip(wave, 0, 1)
        else:
            wave = np.ones((h, w), dtype=np.float32) * 0.5

        G = r_min + wave * (r_max - r_min) * sm
        M = np.full((h, w), float(base_m), dtype=np.float32)
        n = _noise(shape, [4, 8], [0.5, 0.5], seed + seed_offset + 50)
        M = M + n * 8 * sm
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        n = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 80)
        shimmer = np.clip(n * 0.04 * pm, -0.04, 0.04)
        paint = np.clip(paint + shimmer[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_wave_chrome_tide, paint_wave_chrome_tide = _make_wave_fusion(255, 2, 80, "low", 0, 8100)
spec_wave_candy_flow, paint_wave_candy_flow = _make_wave_fusion(200, 10, 60, "medium", 16, 8110)
spec_wave_pearl_current, paint_wave_pearl_current = _make_wave_fusion(100, 20, 70, "low", 16, 8120)
spec_wave_metallic_pulse, paint_wave_metallic_pulse = _make_wave_fusion(220, 15, 90, "high", 16, 8130)
spec_wave_dual_frequency, paint_wave_dual_frequency = _make_wave_fusion(200, 5, 100, "dual", 16, 8140)
spec_wave_diagonal_sweep, paint_wave_diagonal_sweep = _make_wave_fusion(240, 5, 60, "diagonal", 0, 8150)
spec_wave_circular_radar, paint_wave_circular_radar = _make_wave_fusion(230, 3, 80, "radial", 16, 8160)
spec_wave_turbulent_flow, paint_wave_turbulent_flow = _make_wave_fusion(210, 10, 100, "chaotic", 16, 8170)
spec_wave_standing_chrome, paint_wave_standing_chrome = _make_wave_fusion(250, 2, 50, "standing", 0, 8180)
spec_wave_moire_metal, paint_wave_moire_metal = _make_wave_fusion(200, 8, 70, "moire", 16, 8190)


# ================================================================
# PARADIGM 13: FRACTAL MATERIAL MIXING — Self-similar chaos
# ================================================================

def _make_fractal_fusion(m_low, m_high, r_smooth, r_rough, num_octaves, base_cc, seed_offset=0):
    """Factory: fractal octave noise drives material state at every scale."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        combined = np.zeros((h, w), dtype=np.float32)
        weight_sum = 0.0
        for i in range(num_octaves):
            scale = 2 ** (i + 2)  # 4, 8, 16, 32, 64, ...
            weight = 1.0 / (i + 1)  # decreasing weight
            octave = _noise(shape, [scale], [1.0], seed + seed_offset + i * 100)
            combined += octave * weight
            weight_sum += weight
        combined = combined / weight_sum
        combined = np.clip(combined * 0.5 + 0.5, 0, 1)
        M = m_low + combined * (m_high - m_low) * sm
        G = r_rough - combined * (r_rough - r_smooth) * sm
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        n = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 500)
        tint = np.clip(n * 0.05 * pm, -0.05, 0.05)
        paint = np.clip(paint + tint[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_fractal_chrome_decay, paint_fractal_chrome_decay = _make_fractal_fusion(10, 255, 2, 180, 4, 0, 8200)
spec_fractal_candy_chaos, paint_fractal_candy_chaos = _make_fractal_fusion(80, 200, 5, 60, 3, 16, 8210)
spec_fractal_pearl_cloud, paint_fractal_pearl_cloud = _make_fractal_fusion(40, 120, 15, 80, 4, 16, 8220)
spec_fractal_metallic_storm, paint_fractal_metallic_storm = _make_fractal_fusion(100, 255, 5, 130, 5, 16, 8230)
spec_fractal_matte_chrome, paint_fractal_matte_chrome = _make_fractal_fusion(0, 255, 0, 220, 4, 0, 8240)
spec_fractal_warm_cold, paint_fractal_warm_cold = _make_fractal_fusion(60, 240, 10, 100, 3, 16, 8250)
spec_fractal_deep_organic, paint_fractal_deep_organic = _make_fractal_fusion(20, 180, 20, 90, 4, 16, 8260)
spec_fractal_electric_noise, paint_fractal_electric_noise = _make_fractal_fusion(150, 255, 2, 60, 5, 16, 8270)
spec_fractal_cosmic_dust, paint_fractal_cosmic_dust = _make_fractal_fusion(30, 200, 10, 120, 4, 16, 8280)
spec_fractal_liquid_fire, paint_fractal_liquid_fire = _make_fractal_fusion(80, 250, 3, 140, 3, 0, 8290)


# ================================================================
# PARADIGM 14: SPECTRAL GRADIENT MATERIAL — Color-reactive spec
# ================================================================

def _make_spectral_fusion(mapping_type, m_range, g_range, base_cc, seed_offset=0):
    """Factory: paint color determines material properties."""
    def spec_fn(shape, mask, seed, sm):
        # Spectral fusions use noise as proxy for hue variation
        h, w = shape
        field = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset)
        field = np.clip(field * 0.5 + 0.5, 0, 1)
        if mapping_type == "rainbow":
            M = m_range[0] + field * (m_range[1] - m_range[0]) * sm
            G = g_range[1] - field * (g_range[1] - g_range[0]) * sm
        elif mapping_type == "binary":
            zone = np.where(field > 0.5, 1.0, 0.0).astype(np.float32)
            M = m_range[0] * (1 - zone) + m_range[1] * zone
            G = g_range[1] * (1 - zone) + g_range[0] * zone
        elif mapping_type == "value":
            M = m_range[0] + field * (m_range[1] - m_range[0]) * sm
            G = g_range[0] + (1 - field) * (g_range[1] - g_range[0]) * sm
        elif mapping_type == "saturation":
            M = m_range[0] + field * (m_range[1] - m_range[0]) * sm
            G = g_range[0] + field * 10
        elif mapping_type == "tri":
            z1 = (field > 0.66).astype(np.float32)
            z2 = ((field > 0.33) & (field <= 0.66)).astype(np.float32)
            z3 = (field <= 0.33).astype(np.float32)
            M = 255 * z1 + 130 * z2 + 0 * z3
            G = 5 * z1 + 40 * z2 + 180 * z3
        elif mapping_type == "inverted":
            M = m_range[1] - field * (m_range[1] - m_range[0]) * sm
            G = g_range[0] + field * (g_range[1] - g_range[0]) * sm
        else:
            M = np.full((h, w), float(m_range[0]), dtype=np.float32)
            G = np.full((h, w), float(g_range[0]), dtype=np.float32)
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        field = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset)
        hue = np.clip(field * 0.5 + 0.5, 0, 1)
        r, g, b = _hsv_to_rgb(hue, np.full_like(hue, 0.6), np.full_like(hue, 0.7))
        blend = 0.08 * pm
        paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r * blend * mask, 0, 1)
        paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g * blend * mask, 0, 1)
        paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b * blend * mask, 0, 1)
        paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_spectral_rainbow_metal, paint_spectral_rainbow_metal = _make_spectral_fusion("rainbow", (0, 255), (2, 200), 16, 8300)
spec_spectral_warm_cool, paint_spectral_warm_cool = _make_spectral_fusion("binary", (0, 255), (5, 180), 16, 8310)
spec_spectral_dark_light, paint_spectral_dark_light = _make_spectral_fusion("value", (20, 240), (5, 150), 16, 8320)
spec_spectral_sat_metal, paint_spectral_sat_metal = _make_spectral_fusion("saturation", (40, 230), (20, 60), 16, 8330)
spec_spectral_complementary, paint_spectral_complementary = _make_spectral_fusion("binary", (30, 220), (10, 120), 16, 8340)
spec_spectral_neon_reactive, paint_spectral_neon_reactive = _make_spectral_fusion("value", (50, 255), (2, 100), 0, 8350)
spec_spectral_earth_sky, paint_spectral_earth_sky = _make_spectral_fusion("rainbow", (30, 200), (20, 140), 16, 8360)
spec_spectral_mono_chrome, paint_spectral_mono_chrome = _make_spectral_fusion("value", (0, 255), (2, 180), 0, 8370)
spec_spectral_prismatic_flip, paint_spectral_prismatic_flip = _make_spectral_fusion("tri", (0, 255), (5, 180), 16, 8380)
spec_spectral_inverse_logic, paint_spectral_inverse_logic = _make_spectral_fusion("inverted", (0, 255), (2, 200), 16, 8390)


# ================================================================
# PARADIGM 15: MICRO-PANEL QUILTING — Material mosaic
# ================================================================

def _make_quilt_fusion(panel_size, m_range, g_range, base_cc, seed_offset=0, use_hex=False, use_voronoi=False):
    """Factory: surface divided into micro-panels, each with different material."""
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)
        if use_voronoi:
            n_pts = max(20, (h * w) // (panel_size * panel_size))
            pts_y = rng.randint(0, h, n_pts).astype(np.float32)
            pts_x = rng.randint(0, w, n_pts).astype(np.float32)
            y, x = _mgrid(shape)
            yf, xf = y.astype(np.float32), x.astype(np.float32)
            closest = np.zeros((h, w), dtype=np.int32)
            min_d = np.full((h, w), 1e9, dtype=np.float32)
            for i, (py, px) in enumerate(zip(pts_y, pts_x)):
                d = (yf - py)**2 + (xf - px)**2
                closer = d < min_d
                closest = np.where(closer, i, closest)
                min_d = np.where(closer, d, min_d)
            panel_M_vals = rng.randint(m_range[0], m_range[1] + 1, n_pts).astype(np.float32)
            panel_G_vals = rng.randint(g_range[0], g_range[1] + 1, n_pts).astype(np.float32)
            M = panel_M_vals[closest]
            G = panel_G_vals[closest]
        else:
            ps = panel_size
            num_py = h // ps + 1
            num_px = w // ps + 1
            panel_M = rng.randint(m_range[0], m_range[1] + 1, (num_py, num_px)).astype(np.float32)
            panel_G = rng.randint(g_range[0], g_range[1] + 1, (num_py, num_px)).astype(np.float32)
            y_idx = np.clip(np.arange(h).reshape(-1, 1) // ps, 0, num_py - 1)
            x_idx = np.clip(np.arange(w).reshape(1, -1) // ps, 0, num_px - 1)
            if use_hex:
                # Offset every other row by half a panel width
                row_idx = np.arange(h).reshape(-1, 1) // ps
                offset = (row_idx % 2) * (ps // 2)
                x_idx = np.clip((np.arange(w).reshape(1, -1) + offset) // ps, 0, num_px - 1)
            M = panel_M[y_idx, x_idx]
            G = panel_G[y_idx, x_idx]
        n = _noise(shape, [4, 8], [0.5, 0.5], seed + seed_offset + 50)
        M = M + n * 5 * sm
        G = G + n * 4 * sm
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 80)
        tint = np.clip(n * 0.03 * pm, -0.03, 0.03)
        paint = np.clip(paint + tint[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return spec_fn, paint_fn

spec_quilt_chrome_mosaic, paint_quilt_chrome_mosaic = _make_quilt_fusion(24, (150, 255), (2, 50), 0, 8400)
spec_quilt_candy_tiles, paint_quilt_candy_tiles = _make_quilt_fusion(32, (100, 220), (5, 40), 16, 8410)
spec_quilt_pearl_patchwork, paint_quilt_pearl_patchwork = _make_quilt_fusion(20, (60, 140), (15, 60), 16, 8420)
spec_quilt_metallic_pixels, paint_quilt_metallic_pixels = _make_quilt_fusion(16, (120, 255), (5, 80), 16, 8430)
spec_quilt_hex_variety, paint_quilt_hex_variety = _make_quilt_fusion(28, (80, 240), (3, 70), 16, 8440, use_hex=True)
spec_quilt_diamond_shimmer, paint_quilt_diamond_shimmer = _make_quilt_fusion(20, (160, 255), (2, 40), 0, 8450)
spec_quilt_random_chaos, paint_quilt_random_chaos = _make_quilt_fusion(12, (0, 255), (0, 200), 0, 8460)
spec_quilt_gradient_tiles, paint_quilt_gradient_tiles = _make_quilt_fusion(36, (100, 250), (5, 60), 16, 8470)
spec_quilt_alternating_duo, paint_quilt_alternating_duo = _make_quilt_fusion(24, (0, 255), (5, 20), 16, 8480)
spec_quilt_organic_cells, paint_quilt_organic_cells = _make_quilt_fusion(30, (80, 240), (5, 90), 16, 8490, use_voronoi=True)


# ================================================================
# FUSION REGISTRY — 150 entries (15 Paradigm Shifts × 10 each)
# ================================================================

FUSION_REGISTRY = {
    # ── PARADIGM 1: Multi-Material Gradient ──
    "gradient_chrome_matte":      (spec_gradient_chrome_matte, paint_gradient_chrome_matte),
    "gradient_candy_frozen":      (spec_gradient_candy_frozen, paint_gradient_candy_frozen),
    "gradient_pearl_chrome":      (spec_gradient_pearl_chrome, paint_gradient_pearl_chrome),
    "gradient_metallic_satin":    (spec_gradient_metallic_satin, paint_gradient_metallic_satin),
    "gradient_obsidian_mirror":   (spec_gradient_obsidian_mirror, paint_gradient_obsidian_mirror),
    "gradient_candy_matte":       (spec_gradient_candy_matte, paint_gradient_candy_matte),
    "gradient_anodized_gloss":    (spec_gradient_anodized_gloss, paint_gradient_anodized_gloss),
    "gradient_ember_ice":         (spec_gradient_ember_ice, paint_gradient_ember_ice),
    "gradient_carbon_chrome":     (spec_gradient_carbon_chrome, paint_gradient_carbon_chrome),
    "gradient_spectraflame_void": (spec_gradient_spectraflame_void, paint_gradient_spectraflame_void),
    # ── PARADIGM 2: Clearcoat-Only Patterning ──
    "ghost_hex":                  (spec_ghost_hex, paint_ghost_hex),
    "ghost_stripes":              (spec_ghost_stripes, paint_ghost_stripes),
    "ghost_diamonds":             (spec_ghost_diamonds, paint_ghost_diamonds),
    "ghost_waves":                (spec_ghost_waves, paint_ghost_waves),
    "ghost_camo":                 (spec_ghost_camo, paint_ghost_camo),
    "ghost_scales":               (spec_ghost_scales, paint_ghost_scales),
    "ghost_circuit":              (spec_ghost_circuit, paint_ghost_circuit),
    "ghost_vortex":               (spec_ghost_vortex, paint_ghost_vortex),
    "ghost_fracture":             (spec_ghost_fracture, paint_ghost_fracture),
    "ghost_quilt":                (spec_ghost_quilt, paint_ghost_quilt),
    # ── PARADIGM 3: Anisotropic Roughness ──
    "aniso_horizontal_chrome":    (spec_aniso_horizontal_chrome, paint_aniso_horizontal_chrome),
    "aniso_vertical_pearl":       (spec_aniso_vertical_pearl, paint_aniso_vertical_pearl),
    "aniso_diagonal_candy":       (spec_aniso_diagonal_candy, paint_aniso_diagonal_candy),
    "aniso_radial_metallic":      (spec_aniso_radial_metallic, paint_aniso_radial_metallic),
    "aniso_circular_chrome":      (spec_aniso_circular_chrome, paint_aniso_circular_chrome),
    "aniso_crosshatch_steel":     (spec_aniso_crosshatch_steel, paint_aniso_crosshatch_steel),
    "aniso_spiral_mercury":       (spec_aniso_spiral_mercury, paint_aniso_spiral_mercury),
    "aniso_wave_titanium":        (spec_aniso_wave_titanium, paint_aniso_wave_titanium),
    "aniso_herringbone_gold":     (spec_aniso_herringbone_gold, paint_aniso_herringbone_gold),
    "aniso_turbulence_metal":     (spec_aniso_turbulence_metal, paint_aniso_turbulence_metal),
    # ── PARADIGM 4: Reactive Metallic Zones ──
    "reactive_stealth_pop":       (spec_reactive_stealth_pop, paint_reactive_stealth_pop),
    "reactive_pearl_flash":       (spec_reactive_pearl_flash, paint_reactive_pearl_flash),
    "reactive_candy_reveal":      (spec_reactive_candy_reveal, paint_reactive_candy_reveal),
    "reactive_chrome_fade":       (spec_reactive_chrome_fade, paint_reactive_chrome_fade),
    "reactive_matte_shine":       (spec_reactive_matte_shine, paint_reactive_matte_shine),
    "reactive_dual_tone":         (spec_reactive_dual_tone, paint_reactive_dual_tone),
    "reactive_ghost_metal":       (spec_reactive_ghost_metal, paint_reactive_ghost_metal),
    "reactive_mirror_shadow":     (spec_reactive_mirror_shadow, paint_reactive_mirror_shadow),
    "reactive_warm_cold":         (spec_reactive_warm_cold, paint_reactive_warm_cold),
    "reactive_pulse_metal":       (spec_reactive_pulse_metal, paint_reactive_pulse_metal),
    # ── PARADIGM 5: Stochastic Sparkle ──
    "sparkle_diamond_dust":       (spec_sparkle_diamond_dust, paint_sparkle_diamond_dust),
    "sparkle_starfield":          (spec_sparkle_starfield, paint_sparkle_starfield),
    "sparkle_galaxy":             (spec_sparkle_galaxy, paint_sparkle_galaxy),
    "sparkle_firefly":            (spec_sparkle_firefly, paint_sparkle_firefly),
    "sparkle_snowfall":           (spec_sparkle_snowfall, paint_sparkle_snowfall),
    "sparkle_champagne":          (spec_sparkle_champagne, paint_sparkle_champagne),
    "sparkle_meteor":             (spec_sparkle_meteor, paint_sparkle_meteor),
    "sparkle_constellation":      (spec_sparkle_constellation, paint_sparkle_constellation),
    "sparkle_confetti":           (spec_sparkle_confetti, paint_sparkle_confetti),
    "sparkle_lightning_bug":      (spec_sparkle_lightning_bug, paint_sparkle_lightning_bug),
    # ── PARADIGM 6: Macro vs Micro Roughness ──
    "multiscale_chrome_grain":    (spec_multiscale_chrome_grain, paint_multiscale_chrome_grain),
    "multiscale_candy_frost":     (spec_multiscale_candy_frost, paint_multiscale_candy_frost),
    "multiscale_metal_grit":      (spec_multiscale_metal_grit, paint_multiscale_metal_grit),
    "multiscale_pearl_texture":   (spec_multiscale_pearl_texture, paint_multiscale_pearl_texture),
    "multiscale_satin_weave":     (spec_multiscale_satin_weave, paint_multiscale_satin_weave),
    "multiscale_chrome_sand":     (spec_multiscale_chrome_sand, paint_multiscale_chrome_sand),
    "multiscale_matte_silk":      (spec_multiscale_matte_silk, paint_multiscale_matte_silk),
    "multiscale_flake_grain":     (spec_multiscale_flake_grain, paint_multiscale_flake_grain),
    "multiscale_carbon_micro":    (spec_multiscale_carbon_micro, paint_multiscale_carbon_micro),
    "multiscale_frost_crystal":   (spec_multiscale_frost_crystal, paint_multiscale_frost_crystal),
    # ── PARADIGM 7: Clearcoat Weather Gradient ──
    "weather_sun_fade":           (spec_weather_sun_fade, paint_weather_sun_fade),
    "weather_salt_spray":         (spec_weather_salt_spray, paint_weather_salt_spray),
    "weather_acid_rain":          (spec_weather_acid_rain, paint_weather_acid_rain),
    "weather_desert_blast":       (spec_weather_desert_blast, paint_weather_desert_blast),
    "weather_ice_storm":          (spec_weather_ice_storm, paint_weather_ice_storm),
    "weather_road_spray":         (spec_weather_road_spray, paint_weather_road_spray),
    "weather_hood_bake":          (spec_weather_hood_bake, paint_weather_hood_bake),
    "weather_barn_dust":          (spec_weather_barn_dust, paint_weather_barn_dust),
    "weather_ocean_mist":         (spec_weather_ocean_mist, paint_weather_ocean_mist),
    "weather_volcanic_ash":       (spec_weather_volcanic_ash, paint_weather_volcanic_ash),
    # ── PARADIGM 8: Dielectric Mirror (Impossible) ──
    "impossible_glass_paint":     (spec_impossible_glass_paint, paint_impossible_glass_paint),
    "impossible_foggy_chrome":    (spec_impossible_foggy_chrome, paint_impossible_foggy_chrome),
    "impossible_inverted_candy":  (spec_impossible_inverted_candy, paint_impossible_inverted_candy),
    "impossible_liquid_glass":    (spec_impossible_liquid_glass, paint_impossible_liquid_glass),
    "impossible_phantom_mirror":  (spec_impossible_phantom_mirror, paint_impossible_phantom_mirror),
    "impossible_ceramic_void":    (spec_impossible_ceramic_void, paint_impossible_ceramic_void),
    "impossible_anti_metal":      (spec_impossible_anti_metal, paint_impossible_anti_metal),
    "impossible_crystal_clear":   (spec_impossible_crystal_clear, paint_impossible_crystal_clear),
    "impossible_dark_glass":      (spec_impossible_dark_glass, paint_impossible_dark_glass),
    "impossible_wet_void":        (spec_impossible_wet_void, paint_impossible_wet_void),
    # ── PARADIGM 9: Tri-Zone Material Fencing ──
    "trizone_chrome_candy_matte":     (spec_trizone_chrome_candy_matte, paint_trizone_chrome_candy_matte),
    "trizone_pearl_carbon_gold":      (spec_trizone_pearl_carbon_gold, paint_trizone_pearl_carbon_gold),
    "trizone_frozen_ember_chrome":    (spec_trizone_frozen_ember_chrome, paint_trizone_frozen_ember_chrome),
    "trizone_anodized_candy_silk":    (spec_trizone_anodized_candy_silk, paint_trizone_anodized_candy_silk),
    "trizone_vanta_chrome_pearl":     (spec_trizone_vanta_chrome_pearl, paint_trizone_vanta_chrome_pearl),
    "trizone_glass_metal_matte":      (spec_trizone_glass_metal_matte, paint_trizone_glass_metal_matte),
    "trizone_mercury_obsidian_candy": (spec_trizone_mercury_obsidian_candy, paint_trizone_mercury_obsidian_candy),
    "trizone_titanium_copper_chrome": (spec_trizone_titanium_copper_chrome, paint_trizone_titanium_copper_chrome),
    "trizone_ceramic_flake_satin":    (spec_trizone_ceramic_flake_satin, paint_trizone_ceramic_flake_satin),
    "trizone_stealth_spectra_frozen": (spec_trizone_stealth_spectra_frozen, paint_trizone_stealth_spectra_frozen),
    # ── PARADIGM 10: Depth Illusion ──
    "depth_canyon":               (spec_depth_canyon, paint_depth_canyon),
    "depth_bubble":               (spec_depth_bubble, paint_depth_bubble),
    "depth_ripple":               (spec_depth_ripple, paint_depth_ripple),
    "depth_scale":                (spec_depth_scale, paint_depth_scale),
    "depth_honeycomb":            (spec_depth_honeycomb, paint_depth_honeycomb),
    "depth_crack":                (spec_depth_crack, paint_depth_crack),
    "depth_wave":                 (spec_depth_wave, paint_depth_wave),
    "depth_pillow":               (spec_depth_pillow, paint_depth_pillow),
    "depth_vortex":               (spec_depth_vortex, paint_depth_vortex),
    "depth_erosion":              (spec_depth_erosion, paint_depth_erosion),
    # ── PARADIGM 11: Metallic Halo Effect ──
    "halo_hex_chrome":            (spec_halo_hex_chrome, paint_halo_hex_chrome),
    "halo_scale_gold":            (spec_halo_scale_gold, paint_halo_scale_gold),
    "halo_circle_pearl":          (spec_halo_circle_pearl, paint_halo_circle_pearl),
    "halo_diamond_chrome":        (spec_halo_diamond_chrome, paint_halo_diamond_chrome),
    "halo_voronoi_metal":         (spec_halo_voronoi_metal, paint_halo_voronoi_metal),
    "halo_wave_candy":            (spec_halo_wave_candy, paint_halo_wave_candy),
    "halo_crack_chrome":          (spec_halo_crack_chrome, paint_halo_crack_chrome),
    "halo_star_metal":            (spec_halo_star_metal, paint_halo_star_metal),
    "halo_grid_pearl":            (spec_halo_grid_pearl, paint_halo_grid_pearl),
    "halo_ripple_chrome":         (spec_halo_ripple_chrome, paint_halo_ripple_chrome),
    # ── PARADIGM 12: Dynamic Roughness Waves ──
    "wave_chrome_tide":           (spec_wave_chrome_tide, paint_wave_chrome_tide),
    "wave_candy_flow":            (spec_wave_candy_flow, paint_wave_candy_flow),
    "wave_pearl_current":         (spec_wave_pearl_current, paint_wave_pearl_current),
    "wave_metallic_pulse":        (spec_wave_metallic_pulse, paint_wave_metallic_pulse),
    "wave_dual_frequency":        (spec_wave_dual_frequency, paint_wave_dual_frequency),
    "wave_diagonal_sweep":        (spec_wave_diagonal_sweep, paint_wave_diagonal_sweep),
    "wave_circular_radar":        (spec_wave_circular_radar, paint_wave_circular_radar),
    "wave_turbulent_flow":        (spec_wave_turbulent_flow, paint_wave_turbulent_flow),
    "wave_standing_chrome":       (spec_wave_standing_chrome, paint_wave_standing_chrome),
    "wave_moire_metal":           (spec_wave_moire_metal, paint_wave_moire_metal),
    # ── PARADIGM 13: Fractal Material Mixing ──
    "fractal_chrome_decay":       (spec_fractal_chrome_decay, paint_fractal_chrome_decay),
    "fractal_candy_chaos":        (spec_fractal_candy_chaos, paint_fractal_candy_chaos),
    "fractal_pearl_cloud":        (spec_fractal_pearl_cloud, paint_fractal_pearl_cloud),
    "fractal_metallic_storm":     (spec_fractal_metallic_storm, paint_fractal_metallic_storm),
    "fractal_matte_chrome":       (spec_fractal_matte_chrome, paint_fractal_matte_chrome),
    "fractal_warm_cold":          (spec_fractal_warm_cold, paint_fractal_warm_cold),
    "fractal_deep_organic":       (spec_fractal_deep_organic, paint_fractal_deep_organic),
    "fractal_electric_noise":     (spec_fractal_electric_noise, paint_fractal_electric_noise),
    "fractal_cosmic_dust":        (spec_fractal_cosmic_dust, paint_fractal_cosmic_dust),
    "fractal_liquid_fire":        (spec_fractal_liquid_fire, paint_fractal_liquid_fire),
    # ── PARADIGM 14: Spectral Gradient Material ──
    "spectral_rainbow_metal":     (spec_spectral_rainbow_metal, paint_spectral_rainbow_metal),
    "spectral_warm_cool":         (spec_spectral_warm_cool, paint_spectral_warm_cool),
    "spectral_dark_light":        (spec_spectral_dark_light, paint_spectral_dark_light),
    "spectral_sat_metal":         (spec_spectral_sat_metal, paint_spectral_sat_metal),
    "spectral_complementary":     (spec_spectral_complementary, paint_spectral_complementary),
    "spectral_neon_reactive":     (spec_spectral_neon_reactive, paint_spectral_neon_reactive),
    "spectral_earth_sky":         (spec_spectral_earth_sky, paint_spectral_earth_sky),
    "spectral_mono_chrome":       (spec_spectral_mono_chrome, paint_spectral_mono_chrome),
    "spectral_prismatic_flip":    (spec_spectral_prismatic_flip, paint_spectral_prismatic_flip),
    "spectral_inverse_logic":     (spec_spectral_inverse_logic, paint_spectral_inverse_logic),
    # ── PARADIGM 15: Micro-Panel Quilting ──
    "quilt_chrome_mosaic":        (spec_quilt_chrome_mosaic, paint_quilt_chrome_mosaic),
    "quilt_candy_tiles":          (spec_quilt_candy_tiles, paint_quilt_candy_tiles),
    "quilt_pearl_patchwork":      (spec_quilt_pearl_patchwork, paint_quilt_pearl_patchwork),
    "quilt_metallic_pixels":      (spec_quilt_metallic_pixels, paint_quilt_metallic_pixels),
    "quilt_hex_variety":          (spec_quilt_hex_variety, paint_quilt_hex_variety),
    "quilt_diamond_shimmer":      (spec_quilt_diamond_shimmer, paint_quilt_diamond_shimmer),
    "quilt_random_chaos":         (spec_quilt_random_chaos, paint_quilt_random_chaos),
    "quilt_gradient_tiles":       (spec_quilt_gradient_tiles, paint_quilt_gradient_tiles),
    "quilt_alternating_duo":      (spec_quilt_alternating_duo, paint_quilt_alternating_duo),
    "quilt_organic_cells":        (spec_quilt_organic_cells, paint_quilt_organic_cells),
}


# ================================================================
# INTEGRATION
# ================================================================

def integrate_fusions(engine_module):
    """Merge FUSIONS into the engine as a NEW 4th category.

    Creates engine_module.FUSION_REGISTRY if it doesn't exist,
    then merges all 150 Fusions into it. Also adds them to
    MONOLITHIC_REGISTRY so the existing render pipeline can find them.
    """
    # Create the FUSION_REGISTRY on the engine module
    if not hasattr(engine_module, 'FUSION_REGISTRY'):
        engine_module.FUSION_REGISTRY = {}
    engine_module.FUSION_REGISTRY.update(FUSION_REGISTRY)

    # Also register in MONOLITHIC_REGISTRY so existing pipeline works
    if hasattr(engine_module, 'MONOLITHIC_REGISTRY'):
        engine_module.MONOLITHIC_REGISTRY.update(FUSION_REGISTRY)

    # Sort registries
    for reg_name in ('FUSION_REGISTRY', 'MONOLITHIC_REGISTRY'):
        reg = getattr(engine_module, reg_name, None)
        if reg is not None:
            sorted_reg = dict(sorted(reg.items()))
            reg.clear()
            reg.update(sorted_reg)

    print(f"[FUSIONS] Loaded {len(FUSION_REGISTRY)} Paradigm Shift Fusions across 15 categories")
    return {"fusions": len(FUSION_REGISTRY)}


def get_fusion_group_map():
    """Return group metadata for UI organization."""
    return {
        "fusions": {
            "FUSIONS — Material Gradients": [
                "gradient_chrome_matte", "gradient_candy_frozen", "gradient_pearl_chrome",
                "gradient_metallic_satin", "gradient_obsidian_mirror", "gradient_candy_matte",
                "gradient_anodized_gloss", "gradient_ember_ice", "gradient_carbon_chrome",
                "gradient_spectraflame_void",
            ],
            "FUSIONS — Ghost Geometry": [
                "ghost_hex", "ghost_stripes", "ghost_diamonds", "ghost_waves", "ghost_camo",
                "ghost_scales", "ghost_circuit", "ghost_vortex", "ghost_fracture", "ghost_quilt",
            ],
            "FUSIONS — Directional Grain": [
                "aniso_horizontal_chrome", "aniso_vertical_pearl", "aniso_diagonal_candy",
                "aniso_radial_metallic", "aniso_circular_chrome", "aniso_crosshatch_steel",
                "aniso_spiral_mercury", "aniso_wave_titanium", "aniso_herringbone_gold",
                "aniso_turbulence_metal",
            ],
            "FUSIONS — Reactive Panels": [
                "reactive_stealth_pop", "reactive_pearl_flash", "reactive_candy_reveal",
                "reactive_chrome_fade", "reactive_matte_shine", "reactive_dual_tone",
                "reactive_ghost_metal", "reactive_mirror_shadow", "reactive_warm_cold",
                "reactive_pulse_metal",
            ],
            "FUSIONS — Sparkle Systems": [
                "sparkle_diamond_dust", "sparkle_starfield", "sparkle_galaxy", "sparkle_firefly",
                "sparkle_snowfall", "sparkle_champagne", "sparkle_meteor", "sparkle_constellation",
                "sparkle_confetti", "sparkle_lightning_bug",
            ],
            "FUSIONS — Multi-Scale Texture": [
                "multiscale_chrome_grain", "multiscale_candy_frost", "multiscale_metal_grit",
                "multiscale_pearl_texture", "multiscale_satin_weave", "multiscale_chrome_sand",
                "multiscale_matte_silk", "multiscale_flake_grain", "multiscale_carbon_micro",
                "multiscale_frost_crystal",
            ],
            "FUSIONS — Weather & Age": [
                "weather_sun_fade", "weather_salt_spray", "weather_acid_rain", "weather_desert_blast",
                "weather_ice_storm", "weather_road_spray", "weather_hood_bake", "weather_barn_dust",
                "weather_ocean_mist", "weather_volcanic_ash",
            ],
            "FUSIONS — Impossible Physics": [
                "impossible_glass_paint", "impossible_foggy_chrome", "impossible_inverted_candy",
                "impossible_liquid_glass", "impossible_phantom_mirror", "impossible_ceramic_void",
                "impossible_anti_metal", "impossible_crystal_clear", "impossible_dark_glass",
                "impossible_wet_void",
            ],
            "FUSIONS — Tri-Zone Materials": [
                "trizone_chrome_candy_matte", "trizone_pearl_carbon_gold", "trizone_frozen_ember_chrome",
                "trizone_anodized_candy_silk", "trizone_vanta_chrome_pearl", "trizone_glass_metal_matte",
                "trizone_mercury_obsidian_candy", "trizone_titanium_copper_chrome",
                "trizone_ceramic_flake_satin", "trizone_stealth_spectra_frozen",
            ],
            "FUSIONS — Depth Illusion": [
                "depth_canyon", "depth_bubble", "depth_ripple", "depth_scale", "depth_honeycomb",
                "depth_crack", "depth_wave", "depth_pillow", "depth_vortex", "depth_erosion",
            ],
            "FUSIONS — Metallic Halos": [
                "halo_hex_chrome", "halo_scale_gold", "halo_circle_pearl", "halo_diamond_chrome",
                "halo_voronoi_metal", "halo_wave_candy", "halo_crack_chrome", "halo_star_metal",
                "halo_grid_pearl", "halo_ripple_chrome",
            ],
            "FUSIONS — Light Waves": [
                "wave_chrome_tide", "wave_candy_flow", "wave_pearl_current", "wave_metallic_pulse",
                "wave_dual_frequency", "wave_diagonal_sweep", "wave_circular_radar",
                "wave_turbulent_flow", "wave_standing_chrome", "wave_moire_metal",
            ],
            "FUSIONS — Fractal Chaos": [
                "fractal_chrome_decay", "fractal_candy_chaos", "fractal_pearl_cloud",
                "fractal_metallic_storm", "fractal_matte_chrome", "fractal_warm_cold",
                "fractal_deep_organic", "fractal_electric_noise", "fractal_cosmic_dust",
                "fractal_liquid_fire",
            ],
            "FUSIONS — Spectral Reactive": [
                "spectral_rainbow_metal", "spectral_warm_cool", "spectral_dark_light",
                "spectral_sat_metal", "spectral_complementary", "spectral_neon_reactive",
                "spectral_earth_sky", "spectral_mono_chrome", "spectral_prismatic_flip",
                "spectral_inverse_logic",
            ],
            "FUSIONS — Panel Quilting": [
                "quilt_chrome_mosaic", "quilt_candy_tiles", "quilt_pearl_patchwork",
                "quilt_metallic_pixels", "quilt_hex_variety", "quilt_diamond_shimmer",
                "quilt_random_chaos", "quilt_gradient_tiles", "quilt_alternating_duo",
                "quilt_organic_cells",
            ],
        },
    }


def get_fusion_counts():
    return {
        "fusions": len(FUSION_REGISTRY),
        "paradigm_shifts": 15,
        "per_paradigm": 10,
    }

