# -*- coding: utf-8 -*-
"""
MILITARY & TACTICAL -- 12 bases, each with unique paint_fn + spec_fn
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid

def paint_armor_plate_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Rolled homogeneous armor: directional rolling marks + hardness variation
    roll_dir = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    hardness = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 1301)
    gray = base.mean(axis=2)
    armor = np.clip(gray * 0.15 + 0.32, 0, 1)
    roll_mark = roll_dir * 0.03
    effect = np.clip(np.stack([armor + roll_mark + hardness * 0.01]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_armor_plate(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    roll = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    M = np.clip(170.0 + roll * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(22.0 + roll * 18.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(2.0 + roll * 3.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_battleship_gray_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Haze gray anti-corrosion coating with salt spray pitting
    salt_pit = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 1310)
    pits = np.clip((salt_pit - 0.7) * 5.0, 0, 1) * 0.04
    base_coat = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1311)
    gray_val = 0.42 + base_coat * 0.03
    effect = np.stack([
        np.clip(gray_val - pits, 0, 1),
        np.clip(gray_val - pits + 0.005, 0, 1),
        np.clip(gray_val - pits + 0.01, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_battleship_gray(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    pit = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 1310)
    M = np.clip(15.0 + pit * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(25.0 + pit * 20.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(6.0 + pit * 4.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_cerakote_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Ceramic-polymer hybrid: ultra-thin spray with micro-ceramic particles
    ceramic_dist = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 1320)
    spray_pattern = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1321)
    gray = base.mean(axis=2)
    cera = np.clip(gray * 0.2 + 0.28, 0, 1)
    ceramic_tex = ceramic_dist * 0.02
    effect = np.clip(np.stack([cera + ceramic_tex + spray_pattern * 0.01]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_cerakote(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    ceramic = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 1320)
    M = np.clip(8.0 + ceramic * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(30.0 + ceramic * 20.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(4.0 + ceramic * 4.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_cerakote_gloss_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Gloss Cerakote: same ceramic particle but polished surface
    ceramic = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 1325)
    polish = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1326)
    gray = base.mean(axis=2)
    cera = np.clip(gray * 0.25 + 0.30, 0, 1)
    effect = np.clip(np.stack([cera + ceramic * 0.015 + polish * 0.02]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_cerakote_gloss(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    polish = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1326)
    M = np.clip(10.0 + polish * 12.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + polish * 10.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(12.0 + polish * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_duracoat_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # DuraCoat: air-dry epoxy with self-leveling properties
    level = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1330)
    drip = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 1331)
    gray = base.mean(axis=2)
    dura = np.clip(gray * 0.2 + 0.30, 0, 1)
    drip_marks = np.clip((drip - 0.75) * 5.0, 0, 1) * 0.02
    effect = np.clip(np.stack([dura + level * 0.015 + drip_marks]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.24 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_duracoat(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    level = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1330)
    M = np.clip(6.0 + level * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(20.0 + level * 15.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(6.0 + level * 4.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_gunship_gray_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Low-vis gunship gray with IR-suppressive pigment
    ir_pigment = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1340)
    gray = base.mean(axis=2)
    gun_gray = np.clip(gray * 0.1 + 0.33, 0, 1)
    ir_mod = ir_pigment * 0.015
    effect = np.stack([
        np.clip(gun_gray + ir_mod + 0.005, 0, 1),
        np.clip(gun_gray + ir_mod, 0, 1),
        np.clip(gun_gray + ir_mod - 0.005, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_gunship_gray(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    ir = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1340)
    M = np.clip(8.0 + ir * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(28.0 + ir * 18.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(4.0 + ir * 3.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_mil_spec_od_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # MIL-DTL-53072 olive drab: chromium oxide green pigment
    pigment = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1350)
    uv_fade = multi_scale_noise((h, w), [32, 64, 128], [0.35, 0.35, 0.3], seed + 1351)
    od_r = 0.22 + pigment * 0.03 + uv_fade * 0.02
    od_g = 0.26 + pigment * 0.04 + uv_fade * 0.01
    od_b = 0.12 + pigment * 0.02
    effect = np.stack([np.clip(od_r, 0, 1), np.clip(od_g, 0, 1), np.clip(od_b, 0, 1)], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_mil_spec_od(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    pigment = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1350)
    M = np.clip(5.0 + pigment * 6.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(35.0 + pigment * 20.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(3.0 + pigment * 3.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_mil_spec_tan_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Coyote tan (FDE): iron oxide pigment with sand-matching IR signature
    iron_ox = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1360)
    sand_match = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1361)
    tan_r = 0.52 + iron_ox * 0.04 + sand_match * 0.02
    tan_g = 0.42 + iron_ox * 0.03 + sand_match * 0.015
    tan_b = 0.28 + iron_ox * 0.02
    effect = np.stack([np.clip(tan_r, 0, 1), np.clip(tan_g, 0, 1), np.clip(tan_b, 0, 1)], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_mil_spec_tan(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    iron = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1360)
    M = np.clip(5.0 + iron * 6.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(32.0 + iron * 20.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(3.0 + iron * 3.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_powder_coat_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Electrostatic powder: particles melt + flow during oven cure
    particle_flow = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 1370)
    cure_var = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1371)
    gray = base.mean(axis=2)
    pc_base = np.clip(gray * 0.3 + 0.35, 0, 1)
    orange_peel = particle_flow * 0.02
    effect = np.clip(np.stack([pc_base + orange_peel + cure_var * 0.01]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.28 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_powder_coat(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flow = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 1370)
    M = np.clip(6.0 + flow * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + flow * 15.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(8.0 + flow * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_rugged_tactical_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Rubberized tactical coating: thick, textured, impact-absorbing
    rubber_tex = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 1380)
    impact_zone = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1381)
    gray = base.mean(axis=2)
    rugged = np.clip(gray * 0.15 + 0.18, 0, 1)
    tex = rubber_tex * 0.025
    effect = np.clip(np.stack([rugged + tex]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_rugged_tactical(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    tex = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 1380)
    M = np.clip(3.0 + tex * 5.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(55.0 + tex * 25.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(1.0 + tex * 2.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_sub_black_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Anechoic tile-like coating: sonar-absorbing rubber tiles
    tile_size = 32
    y, x = get_mgrid((h, w))
    tile_x = (x / tile_size).astype(int)
    tile_y = (y / tile_size).astype(int)
    # Each tile has slight variation (manufacturing tolerance)
    rng = np.random.RandomState(seed + 1390)
    tile_ids = (tile_y * 100 + tile_x) % 997
    tile_var = np.zeros((h, w), dtype=np.float32)
    for tid in np.unique(tile_ids):
        tile_var[tile_ids == tid] = rng.rand() * 0.02
    dark = 0.05 + tile_var
    # Tile seams
    seam_x = np.abs(np.mod(x, tile_size) - tile_size/2) / (tile_size/2)
    seam_y = np.abs(np.mod(y, tile_size) - tile_size/2) / (tile_size/2)
    seam = np.clip(np.maximum(seam_x, seam_y) - 0.85, 0, 1) * 0.03
    effect = np.clip(np.stack([dark - seam]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_sub_black(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    seam = np.clip(np.maximum(np.abs(np.mod(x, 32) - 16)/16, np.abs(np.mod(y, 32) - 16)/16) - 0.85, 0, 1)
    M = np.clip(3.0 + seam * 5.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(60.0 + seam * 20.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(1.0 + seam * 2.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_submarine_black_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Deep-dive pressure hull coating: anti-fouling + corrosion resistant
    fouling = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1395)
    bio_growth = np.clip((fouling - 0.6) * 3.0, 0, 1) * 0.03
    hull_var = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1396)
    dark = 0.06 + hull_var * 0.015
    effect = np.stack([
        np.clip(dark + bio_growth * 0.3, 0, 1),
        np.clip(dark + bio_growth, 0, 1),
        np.clip(dark + bio_growth * 0.5, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_submarine_black(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    fouling = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1395)
    M = np.clip(4.0 + fouling * 5.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(45.0 + fouling * 25.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(2.0 + fouling * 3.0, 0, 255).astype(np.float32)
    return M, R, CC
