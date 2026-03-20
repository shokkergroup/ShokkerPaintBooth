"""
Shokker Color Clash Expansion — 25 Harsh Gradient Finishes
============================================================
Intentionally clashing, punk, neon-vs-dark color gradients.
Layout: dominant center color, contrasting edges (left-to-right).
Each finish has a UNIQUE spec character (chrome, matte, satin, mixed zones, etc.)

Spec Contract: spec functions return uint8 [H,W,4] RGBA
  Channel 0 (R): Roughness (0=smooth/glossy, 255=rough/matte)
  Channel 1 (G): Metallic  (0=non-metallic, 255=fully metallic)
  Channel 2 (B): Reserved/specular
  Channel 3 (A): Usually 255

Paint Contract: paint functions modify float32 [H,W,3] paint array in-place
  pm=0 => return paint unchanged (PM Identity Contract)

Author: Shokker Engine — Color Clash Series
"""

import numpy as np


# ================================================================
# HELPERS
# ================================================================

def _gradient_lr(shape):
    """Left-to-right gradient 0..1 across width."""
    h, w = shape[:2]
    return np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))


def _center_weight(shape):
    """Center-dominant weight: 1 at center, 0 at edges (left-to-right)."""
    h, w = shape[:2]
    x = np.linspace(-1, 1, w, dtype=np.float32)
    # Bell curve centered at 0
    cw = np.exp(-3.0 * x * x)
    return np.tile(cw, (h, 1))


def _edge_weight(shape):
    """Edge weight: 1 at edges, 0 at center (complement of center_weight)."""
    return 1.0 - _center_weight(shape)


def _apply_clash_gradient(paint, shape, mask, center_rgb, edge_rgb, seed, pm, bb):
    """Apply center-dominant, edge-contrasting L-R gradient to paint.
    PM Identity Contract: pm=0 returns paint unchanged.
    """
    if pm == 0.0:
        return paint

    cw = _center_weight(shape)
    ew = _edge_weight(shape)

    for ch in range(3):
        target = cw * center_rgb[ch] + ew * edge_rgb[ch]
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask) + target * pm * mask,
            0, 1
        )

    # Apply base brightness boost
    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


def _uniform_spec(shape, mask, sm, roughness, metallic, specular=16):
    """Build a uniform spec map with given roughness/metallic values."""
    h, w = shape[:2]
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(roughness * mask * sm, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(metallic * mask * sm, 0, 255).astype(np.uint8)
    spec[:, :, 2] = specular
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def _gradient_spec(shape, mask, sm, r_center, m_center, r_edge, m_edge, specular=16):
    """Build a spec map that varies from center to edges (L-R)."""
    h, w = shape[:2]
    cw = _center_weight(shape)
    ew = _edge_weight(shape)

    roughness = cw * r_center + ew * r_edge
    metallic = cw * m_center + ew * m_edge

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(roughness * mask * sm, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(metallic * mask * sm, 0, 255).astype(np.uint8)
    spec[:, :, 2] = specular
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def _multizone_spec(shape, mask, sm, zones, specular=16):
    """Build spec with multiple zones across L-R axis.
    zones: list of (roughness, metallic) tuples, evenly distributed.
    """
    h, w = shape[:2]
    n = len(zones)
    roughness = np.zeros((h, w), dtype=np.float32)
    metallic = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(0, 1, w, dtype=np.float32)

    for i in range(n - 1):
        start = i / (n - 1)
        end = (i + 1) / (n - 1)
        blend = np.clip((x - start) / (end - start + 1e-8), 0, 1)
        zone_mask_1d = ((x >= start) & (x <= end)).astype(np.float32)
        r_val = zones[i][0] * (1 - blend) + zones[i + 1][0] * blend
        m_val = zones[i][1] * (1 - blend) + zones[i + 1][1] * blend
        roughness += np.tile(r_val * zone_mask_1d, (h, 1))
        metallic += np.tile(m_val * zone_mask_1d, (h, 1))

    # Remove overlapping accumulations by just doing a clean interpolation
    roughness = np.zeros((h, w), dtype=np.float32)
    metallic = np.zeros((h, w), dtype=np.float32)
    positions = np.linspace(0, 1, n, dtype=np.float32)
    r_vals = np.array([z[0] for z in zones], dtype=np.float32)
    m_vals = np.array([z[1] for z in zones], dtype=np.float32)
    r_interp = np.interp(x, positions, r_vals)
    m_interp = np.interp(x, positions, m_vals)
    roughness = np.tile(r_interp, (h, 1))
    metallic = np.tile(m_interp, (h, 1))

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(roughness * mask * sm, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(metallic * mask * sm, 0, 255).astype(np.uint8)
    spec[:, :, 2] = specular
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def _add_noise_to_spec(spec, shape, seed, intensity=8):
    """Add subtle noise to spec for realism."""
    rng = np.random.RandomState(seed)
    noise = rng.randint(-intensity, intensity + 1, size=(shape[0], shape[1]), dtype=np.int16)
    for ch in range(2):  # roughness and metallic only
        spec[:, :, ch] = np.clip(spec[:, :, ch].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return spec


# ================================================================
# 1. cc_neon_bruise — Electric purple center, toxic green edges — CHROME
# ================================================================

def spec_cc_neon_bruise(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=15, metallic=250)
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_neon_bruise(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.55, 0.0, 0.85),   # electric purple
                                  edge_rgb=(0.2, 0.95, 0.1),      # toxic green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 2. cc_acid_burn — Acid yellow center, deep purple edges — MATTE
# ================================================================

def spec_cc_acid_burn(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=220, metallic=15)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_acid_burn(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.95, 0.95, 0.0),   # acid yellow
                                  edge_rgb=(0.25, 0.0, 0.5),      # deep purple
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 3. cc_blood_orange — Blood red center, electric blue edges — SATIN
# ================================================================

def spec_cc_blood_orange(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=100, metallic=130)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_blood_orange(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.7, 0.05, 0.0),    # blood red
                                  edge_rgb=(0.0, 0.3, 0.95),      # electric blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 4. cc_toxic_sunset — Hot pink center, acid green edges — CHROME fading to MATTE
# ================================================================

def spec_cc_toxic_sunset(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=15, m_center=245,    # chrome center
                          r_edge=210, m_edge=20)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_toxic_sunset(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.1, 0.55),    # hot pink
                                  edge_rgb=(0.3, 0.95, 0.05),     # acid green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 5. cc_electric_conflict — Cyan center, magenta edges — HIGH GLOSS
# ================================================================

def spec_cc_electric_conflict(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=25, metallic=200)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_electric_conflict(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.0, 0.9, 0.95),    # cyan
                                  edge_rgb=(0.9, 0.0, 0.7),       # magenta
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 6. cc_nuclear_dawn — Nuclear green center, crimson edges — ROUGH MATTE
# ================================================================

def spec_cc_nuclear_dawn(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=240, metallic=15)
    return _add_noise_to_spec(spec, shape, seed, 8)

def paint_cc_nuclear_dawn(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.15, 0.95, 0.0),   # nuclear green
                                  edge_rgb=(0.7, 0.0, 0.05),      # crimson
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 7. cc_voltage_split — Electric yellow center, deep navy edges — CHROME center, MATTE edges
# ================================================================

def spec_cc_voltage_split(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=10, m_center=250,    # chrome center
                          r_edge=230, m_edge=10)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_voltage_split(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.95, 0.0),    # electric yellow
                                  edge_rgb=(0.0, 0.05, 0.3),      # deep navy
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 8. cc_coral_venom — Coral center, viper green edges — SATIN
# ================================================================

def spec_cc_coral_venom(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=90, metallic=140)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_coral_venom(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.4, 0.3),     # coral
                                  edge_rgb=(0.0, 0.6, 0.1),       # viper green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 9. cc_ultraviolet_burn — UV purple center, safety orange edges — SEMI-GLOSS
# ================================================================

def spec_cc_ultraviolet_burn(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=60, metallic=170)
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_ultraviolet_burn(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.4, 0.0, 0.9),     # UV purple
                                  edge_rgb=(1.0, 0.5, 0.0),       # safety orange
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 10. cc_rust_vs_ice — Rust orange center, ice blue edges — MATTE center, CHROME edges
# ================================================================

def spec_cc_rust_vs_ice(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=200, m_center=30,    # matte center
                          r_edge=15, m_edge=240)        # chrome edges
    return _add_noise_to_spec(spec, shape, seed, 7)

def paint_cc_rust_vs_ice(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.7, 0.3, 0.05),    # rust orange
                                  edge_rgb=(0.7, 0.85, 0.95),     # ice blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 11. cc_magma_freeze — Molten red center, arctic white edges — MIXED (chrome/matte/satin zones)
# ================================================================

def spec_cc_magma_freeze(shape, mask, seed, sm):
    # 5 zones: chrome | satin | matte | satin | chrome
    zones = [
        (15, 245),   # chrome (left edge)
        (100, 130),  # satin
        (200, 20),   # matte (center)
        (100, 130),  # satin
        (15, 245),   # chrome (right edge)
    ]
    spec = _multizone_spec(shape, mask, sm, zones)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_magma_freeze(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.9, 0.15, 0.0),    # molten red
                                  edge_rgb=(0.92, 0.95, 1.0),     # arctic white
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 12. cc_punk_static — Hot pink center, black & white static edges — FLAT MATTE
# ================================================================

def spec_cc_punk_static(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=235, metallic=10)
    # Add heavier noise for static feel at edges
    rng = np.random.RandomState(seed + 100)
    ew = _edge_weight(shape)
    noise = (rng.randint(0, 30, size=(shape[0], shape[1])) * ew).astype(np.int16)
    spec[:, :, 0] = np.clip(spec[:, :, 0].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return spec

def paint_cc_punk_static(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    cw = _center_weight(shape)
    ew = _edge_weight(shape)
    # Center: hot pink
    for ch, val in enumerate([1.0, 0.05, 0.5]):
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask * cw) + val * pm * mask * cw,
            0, 1)
    # Edges: black & white static
    rng = np.random.RandomState(seed + 200)
    static = rng.choice([0.0, 1.0], size=(shape[0], shape[1])).astype(np.float32)
    for ch in range(3):
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask * ew) + static * pm * mask * ew,
            0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# 13. cc_radioactive — Neon green center, deep maroon edges — GLOSS
# ================================================================

def spec_cc_radioactive(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=35, metallic=180)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_radioactive(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.1, 1.0, 0.05),    # neon green
                                  edge_rgb=(0.35, 0.0, 0.05),     # deep maroon
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 14. cc_bruised_sky — Deep purple center, sickly yellow edges — SATIN to MATTE
# ================================================================

def spec_cc_bruised_sky(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=90, m_center=140,    # satin center
                          r_edge=210, m_edge=25)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_bruised_sky(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.3, 0.0, 0.55),    # deep purple
                                  edge_rgb=(0.85, 0.85, 0.2),     # sickly yellow
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 15. cc_chemical_spill — Lime green center, chemical orange edges — CHROME
# ================================================================

def spec_cc_chemical_spill(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=20, metallic=245)
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_chemical_spill(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.4, 0.95, 0.0),    # lime green
                                  edge_rgb=(1.0, 0.45, 0.0),      # chemical orange
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 16. cc_deep_friction — Deep red center, electric teal edges — ROUGH TEXTURE
# ================================================================

def spec_cc_deep_friction(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=235, metallic=70)
    # Add heavy grain for texture
    rng = np.random.RandomState(seed + 300)
    grain = rng.randint(-15, 16, size=(shape[0], shape[1]), dtype=np.int16)
    spec[:, :, 0] = np.clip(spec[:, :, 0].astype(np.int16) + grain, 0, 255).astype(np.uint8)
    return spec

def paint_cc_deep_friction(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.55, 0.0, 0.0),    # deep red
                                  edge_rgb=(0.0, 0.85, 0.75),     # electric teal
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 17. cc_plasma_edge — White-hot center, plasma blue edges — ULTRA CHROME
# ================================================================

def spec_cc_plasma_edge(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=5, metallic=255)
    return _add_noise_to_spec(spec, shape, seed, 3)

def paint_cc_plasma_edge(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.98, 0.9),    # white-hot
                                  edge_rgb=(0.1, 0.2, 0.95),      # plasma blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 18. cc_candy_poison — Candy pink center, poison black-green edges — GLOSS to MATTE
# ================================================================

def spec_cc_candy_poison(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=30, m_center=190,    # gloss center
                          r_edge=220, m_edge=30)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_candy_poison(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.4, 0.65),    # candy pink
                                  edge_rgb=(0.05, 0.15, 0.05),    # poison black-green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 19. cc_solar_clash — Solar gold center, void black edges — CHROME center only
# ================================================================

def spec_cc_solar_clash(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=10, m_center=250,    # chrome center
                          r_edge=120, m_edge=60)        # semi-matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_solar_clash(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.8, 0.1),     # solar gold
                                  edge_rgb=(0.02, 0.02, 0.02),    # void black
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 20. cc_fever_dream — Fever red center, hallucination purple edges — MULTI-FINISH (4 zones)
# ================================================================

def spec_cc_fever_dream(shape, mask, seed, sm):
    # 4 distinct zones: matte | chrome | satin | rough
    zones = [
        (210, 20),   # matte (left edge)
        (15, 245),   # chrome
        (90, 130),   # satin (center-right)
        (230, 50),   # rough (right edge)
    ]
    spec = _multizone_spec(shape, mask, sm, zones)
    return _add_noise_to_spec(spec, shape, seed, 7)

def paint_cc_fever_dream(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.9, 0.1, 0.05),    # fever red
                                  edge_rgb=(0.5, 0.0, 0.75),      # hallucination purple
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 21. cc_digital_rot — Digital cyan center, rot brown edges — SATIN
# ================================================================

def spec_cc_digital_rot(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=85, metallic=145)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_digital_rot(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.0, 0.9, 0.9),     # digital cyan
                                  edge_rgb=(0.4, 0.2, 0.05),      # rot brown
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 22. cc_flash_burn — Flash white center, burn orange-red edges — CHROME to ROUGH
# ================================================================

def spec_cc_flash_burn(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=10, m_center=240,    # chrome center
                          r_edge=225, m_edge=60)        # rough edges
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_flash_burn(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 1.0, 0.95),    # flash white
                                  edge_rgb=(0.9, 0.3, 0.0),       # burn orange-red
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 23. cc_venom_strike — Venom green center, black edges — HIGH GLOSS
# ================================================================

def spec_cc_venom_strike(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=20, metallic=210)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_venom_strike(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.15, 0.85, 0.0),   # venom green
                                  edge_rgb=(0.02, 0.02, 0.02),    # black
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 24. cc_neon_war — Neon orange center, neon blue edges — CHROME
# ================================================================

def spec_cc_neon_war(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=15, metallic=248)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_neon_war(paint, shape, mask, seed, pm, bb):
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.4, 0.0),     # neon orange
                                  edge_rgb=(0.0, 0.3, 1.0),       # neon blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 25. cc_chaos_theory — Shifting rainbow center, black edges — MIXED EVERYTHING
# ================================================================

def spec_cc_chaos_theory(shape, mask, seed, sm):
    # 7 zones cycling through all finish types
    zones = [
        (230, 15),   # rough matte (left edge)
        (15, 250),   # chrome
        (90, 130),   # satin
        (50, 200),   # semi-gloss (center)
        (200, 40),   # matte
        (10, 245),   # chrome
        (230, 15),   # rough matte (right edge)
    ]
    spec = _multizone_spec(shape, mask, sm, zones)
    return _add_noise_to_spec(spec, shape, seed, 8)

def paint_cc_chaos_theory(paint, shape, mask, seed, pm, bb):
    """Rainbow center with black edges — uses multi-band color injection."""
    if pm == 0.0:
        return paint

    h, w = shape[:2]
    cw = _center_weight(shape)
    ew = _edge_weight(shape)

    # Rainbow bands across center
    x = np.linspace(0, 2 * np.pi, w, dtype=np.float32)
    rainbow_r = np.tile(np.clip(np.sin(x) * 0.5 + 0.5, 0, 1), (h, 1))
    rainbow_g = np.tile(np.clip(np.sin(x + 2.094) * 0.5 + 0.5, 0, 1), (h, 1))  # +120 deg
    rainbow_b = np.tile(np.clip(np.sin(x + 4.189) * 0.5 + 0.5, 0, 1), (h, 1))  # +240 deg

    for ch, rainbow in enumerate([rainbow_r, rainbow_g, rainbow_b]):
        center_color = rainbow * cw
        edge_color = 0.02 * ew  # near-black edges
        target = center_color + edge_color
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask) + target * pm * mask,
            0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# REGISTRY — Maps finish IDs to (spec_fn, paint_fn) tuples
# ================================================================

COLOR_CLASH_MONOLITHICS = {
    "cc_neon_bruise":       (spec_cc_neon_bruise,       paint_cc_neon_bruise),
    "cc_acid_burn":         (spec_cc_acid_burn,         paint_cc_acid_burn),
    "cc_blood_orange":      (spec_cc_blood_orange,      paint_cc_blood_orange),
    "cc_toxic_sunset":      (spec_cc_toxic_sunset,      paint_cc_toxic_sunset),
    "cc_electric_conflict": (spec_cc_electric_conflict, paint_cc_electric_conflict),
    "cc_nuclear_dawn":      (spec_cc_nuclear_dawn,      paint_cc_nuclear_dawn),
    "cc_voltage_split":     (spec_cc_voltage_split,     paint_cc_voltage_split),
    "cc_coral_venom":       (spec_cc_coral_venom,       paint_cc_coral_venom),
    "cc_ultraviolet_burn":  (spec_cc_ultraviolet_burn,  paint_cc_ultraviolet_burn),
    "cc_rust_vs_ice":       (spec_cc_rust_vs_ice,       paint_cc_rust_vs_ice),
    "cc_magma_freeze":      (spec_cc_magma_freeze,      paint_cc_magma_freeze),
    "cc_punk_static":       (spec_cc_punk_static,       paint_cc_punk_static),
    "cc_radioactive":       (spec_cc_radioactive,       paint_cc_radioactive),
    "cc_bruised_sky":       (spec_cc_bruised_sky,       paint_cc_bruised_sky),
    "cc_chemical_spill":    (spec_cc_chemical_spill,    paint_cc_chemical_spill),
    "cc_deep_friction":     (spec_cc_deep_friction,     paint_cc_deep_friction),
    "cc_plasma_edge":       (spec_cc_plasma_edge,       paint_cc_plasma_edge),
    "cc_candy_poison":      (spec_cc_candy_poison,      paint_cc_candy_poison),
    "cc_solar_clash":       (spec_cc_solar_clash,       paint_cc_solar_clash),
    "cc_fever_dream":       (spec_cc_fever_dream,       paint_cc_fever_dream),
    "cc_digital_rot":       (spec_cc_digital_rot,       paint_cc_digital_rot),
    "cc_flash_burn":        (spec_cc_flash_burn,        paint_cc_flash_burn),
    "cc_venom_strike":      (spec_cc_venom_strike,      paint_cc_venom_strike),
    "cc_neon_war":          (spec_cc_neon_war,          paint_cc_neon_war),
    "cc_chaos_theory":      (spec_cc_chaos_theory,      paint_cc_chaos_theory),
}


def integrate_color_clash(engine_module):
    """Merge Color Clash expansion into the engine's registries."""
    engine_module.MONOLITHIC_REGISTRY.update(COLOR_CLASH_MONOLITHICS)

    # Sort registry alphabetically after merge
    reg = engine_module.MONOLITHIC_REGISTRY
    sorted_reg = dict(sorted(reg.items()))
    reg.clear()
    reg.update(sorted_reg)

    count = len(COLOR_CLASH_MONOLITHICS)
    print(f"[COLOR CLASH] Loaded {count} color clash gradient finishes")
    return count
