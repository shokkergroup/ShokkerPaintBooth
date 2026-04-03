# -*- coding: utf-8 -*-
"""
Raw Weathered Metal Paint Functions
Electrochemical corrosion, oxidation, and material degradation models
Base IDs: anodized, battle_patina, burnt_headers, galvanized, heat_treated,
          patina_bronze, patina_coat, raw_aluminum, sandblasted
"""

import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


# ANODIZED ALUMINUM - Electrochemical oxide layer thickness variation
def paint_anodized_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Anodized layer thickness creates color shift via interference
    thickness = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1500)
    thickness = (thickness + 1.0) / 2.0  # Normalize to [0, 1]
    
    # Color shift from thickness (cyan/purple iridescence)
    hue_shift = thickness * 0.15
    saturation_boost = thickness * 0.3
    
    effect = base.copy()
    effect[:, :, 0] = np.clip(base[:, :, 0] + hue_shift * 0.1, 0, 1)  # R
    effect[:, :, 1] = np.clip(base[:, :, 1] * (1.0 + saturation_boost * 0.5), 0, 1)  # G
    effect[:, :, 2] = np.clip(base[:, :, 2] + hue_shift * 0.2, 0, 1)  # B
    
    # Add micro-pitting texture
    pitting = multi_scale_noise((h, w), [2, 4], [0.4, 0.2], seed + 1501)
    pitting = np.maximum(0, pitting - 0.3) * 0.5
    
    effect = np.dstack([np.clip(effect[:, :, i] * (1.0 - pitting * 0.2), 0, 1) for i in range(3)])
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_anodized(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Anodized surface is harder, more specular
    M = np.full((h, w), np.clip(base_m + 0.25, 0, 1), dtype=np.float32)
    
    # Add micro-roughness from pitting
    pitting = multi_scale_noise((h, w), [2, 4], [0.3, 0.2], seed + 1501)
    M = np.clip(M + np.maximum(0, pitting - 0.4) * 0.15, 0, 1).astype(np.float32)
    
    # Specular color shift toward cool tones (iridescence)
    R = np.full((h, w), np.clip(base_r * 0.9, 0, 1), dtype=np.float32)
    
    # Coating clarity (high)
    CC = np.full((h, w), 0.8, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# BATTLE PATINA - Multi-oxide corrosion with impact crater damage
def paint_battle_patina_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Oxide layer buildup creates deep reds/browns
    oxide = multi_scale_noise((h, w), [2, 3, 6], [0.4, 0.35, 0.25], seed + 1502)
    oxide = (oxide + 1.0) / 2.0
    
    # Deep rust coloration (Fe2O3 red/brown)
    effect = base.copy()
    effect[:, :, 0] = np.clip(base[:, :, 0] + oxide * 0.3, 0, 1)
    effect[:, :, 1] = np.clip(base[:, :, 1] * (0.6 + oxide * 0.3), 0, 1)
    effect[:, :, 2] = np.clip(base[:, :, 2] * (0.4 + oxide * 0.2), 0, 1)
    
    # Impact crater damage (Voronoi-like)
    y, x = get_mgrid((h, w))
    craters = multi_scale_noise((h, w), [1, 1], [0.6, 0.4], seed + 1503)
    craters = np.maximum(0, craters - 0.4) * 2.0
    craters = np.clip(craters, 0, 1)
    
    # Crater darkening
    crater_shadow = craters * 0.4
    effect = np.dstack([np.clip(effect[:, :, i] * (1.0 - crater_shadow), 0, 1) for i in range(3)])
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_battle_patina(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Rough, pitted surface from corrosion
    M = np.full((h, w), np.clip(base_m - 0.3, 0.1, 1), dtype=np.float32)
    
    # Crater pitting increases roughness
    craters = multi_scale_noise((h, w), [1, 1], [0.5, 0.3], seed + 1503)
    M = np.clip(M - np.maximum(0, craters - 0.4) * 0.2, 0.1, 1).astype(np.float32)
    
    # Dull specular response
    R = np.full((h, w), np.clip(base_r * 0.7, 0, 1), dtype=np.float32)
    
    # Low coating clarity (oxidized/dull)
    CC = np.full((h, w), 0.3, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# BURNT HEADERS - Exhaust manifold heat cycling with tempering colors
def paint_burnt_headers_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Heat gradient creates tempering color zones (straw->blue->purple)
    heat_map = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 1504)
    heat_map = (heat_map + 1.0) / 2.0
    
    effect = base.copy()
    # Straw yellow (200C)
    straw = heat_map < 0.3
    effect[straw, 0] = np.clip(base[straw, 0] + 0.2, 0, 1)
    effect[straw, 1] = np.clip(base[straw, 1] + 0.1, 0, 1)
    effect[straw, 2] = np.clip(base[straw, 2] - 0.1, 0, 1)
    
    # Blue (350C)
    blue = (heat_map >= 0.3) & (heat_map < 0.6)
    effect[blue, 0] = np.clip(base[blue, 0] - 0.2, 0, 1)
    effect[blue, 1] = np.clip(base[blue, 1] - 0.1, 0, 1)
    effect[blue, 2] = np.clip(base[blue, 2] + 0.25, 0, 1)
    
    # Purple (450C+)
    purple = heat_map >= 0.6
    effect[purple, 0] = np.clip(base[purple, 0] + 0.15, 0, 1)
    effect[purple, 1] = np.clip(base[purple, 1] - 0.2, 0, 1)
    effect[purple, 2] = np.clip(base[purple, 2] + 0.2, 0, 1)
    
    # Heat stress cracking
    cracks = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 1505)
    cracks = np.maximum(0, cracks - 0.5) * 1.5
    effect = np.dstack([np.clip(effect[:, :, i] * (1.0 - cracks * 0.15), 0, 1) for i in range(3)])
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_burnt_headers(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Heat cycling creates oxide scale (moderate roughness)
    M = np.full((h, w), np.clip(base_m - 0.15, 0.2, 1), dtype=np.float32)
    
    # Cracking increases roughness
    cracks = multi_scale_noise((h, w), [1, 2], [0.4, 0.3], seed + 1505)
    M = np.clip(M - np.maximum(0, cracks - 0.5) * 0.15, 0.2, 1).astype(np.float32)
    
    # Oxidized specular (warm tones)
    R = np.full((h, w), np.clip(base_r * 0.8, 0, 1), dtype=np.float32)
    
    # Medium coating clarity
    CC = np.full((h, w), 0.5, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# GALVANIZED - Zinc spangle crystallization dendritic pattern
def paint_galvanized_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Dendritic crystal growth pattern (high-freq noise)
    y, x = get_mgrid((h, w))
    dendrites = multi_scale_noise((h, w), [1, 1, 1], [0.5, 0.35, 0.15], seed + 1506)
    dendrites = (dendrites + 1.0) / 2.0
    
    # Zinc silver coloration with crystal boundaries
    effect = base.copy()
    effect[:, :, 0] = np.clip(base[:, :, 0] + dendrites * 0.25, 0, 1)
    effect[:, :, 1] = np.clip(base[:, :, 1] + dendrites * 0.25, 0, 1)
    effect[:, :, 2] = np.clip(base[:, :, 2] + dendrites * 0.2, 0, 1)
    
    # Crystal grain shadowing (Voronoi cellular)
    cells = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1507)
    cells = np.maximum(0, cells - 0.3)
    
    # Subtle grain darkening
    effect = np.dstack([np.clip(effect[:, :, i] * (1.0 - cells * 0.1), 0, 1) for i in range(3)])
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_galvanized(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Crystalline surface (moderate specularity)
    M = np.full((h, w), np.clip(base_m + 0.1, 0, 1), dtype=np.float32)
    
    # Crystal grain boundaries add micro-roughness
    cells = multi_scale_noise((h, w), [2, 4], [0.5, 0.3], seed + 1507)
    M = np.clip(M + np.maximum(0, cells - 0.3) * 0.12, 0, 1).astype(np.float32)
    
    # Zinc has cool specular response
    R = np.full((h, w), np.clip(base_r * 0.95, 0, 1), dtype=np.float32)
    
    # High coating clarity (metallic)
    CC = np.full((h, w), 0.75, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# HEAT TREATED - Steel tempering color gradient (straw->blue->purple)
def paint_heat_treated_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Temperature gradient (directional)
    y, x = get_mgrid((h, w))
    temp_grad = (x / w) * 0.7 + 0.3
    
    # Tempering color noise
    temp_noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1508)
    temp_noise = (temp_noise + 1.0) / 2.0 * 0.4
    
    temp_zones = temp_grad + temp_noise
    temp_zones = np.clip(temp_zones, 0, 1)
    
    effect = base.copy()
    # Pale straw (180-200C)
    straw = temp_zones < 0.2
    effect[straw, 0] = np.clip(base[straw, 0] + 0.15, 0, 1)
    effect[straw, 1] = np.clip(base[straw, 1] + 0.08, 0, 1)
    effect[straw, 2] = np.clip(base[straw, 2] - 0.05, 0, 1)
    
    # Light yellow (220-280C)
    yellow = (temp_zones >= 0.2) & (temp_zones < 0.35)
    effect[yellow, 0] = np.clip(base[yellow, 0] + 0.1, 0, 1)
    effect[yellow, 1] = np.clip(base[yellow, 1] + 0.1, 0, 1)
    effect[yellow, 2] = np.clip(base[yellow, 2] - 0.08, 0, 1)
    
    # Brown (300-330C)
    brown = (temp_zones >= 0.35) & (temp_zones < 0.5)
    effect[brown, 0] = np.clip(base[brown, 0] + 0.05, 0, 1)
    effect[brown, 1] = np.clip(base[brown, 1] - 0.05, 0, 1)
    effect[brown, 2] = np.clip(base[brown, 2] - 0.1, 0, 1)
    
    # Purple-blue (350-400C)
    purple = (temp_zones >= 0.5) & (temp_zones < 0.7)
    effect[purple, 0] = np.clip(base[purple, 0] - 0.1, 0, 1)
    effect[purple, 1] = np.clip(base[purple, 1] - 0.15, 0, 1)
    effect[purple, 2] = np.clip(base[purple, 2] + 0.25, 0, 1)
    
    # Deep blue (420C+)
    deep_blue = temp_zones >= 0.7
    effect[deep_blue, 0] = np.clip(base[deep_blue, 0] - 0.15, 0, 1)
    effect[deep_blue, 1] = np.clip(base[deep_blue, 1] - 0.1, 0, 1)
    effect[deep_blue, 2] = np.clip(base[deep_blue, 2] + 0.35, 0, 1)
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_heat_treated(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]

    # Tempered steel (hard, moderately specular)
    M = np.full((h, w), np.clip(base_m + 0.2, 0, 1), dtype=np.float32)

    # Very slight surface variation from tempering color bands
    micro = multi_scale_noise((h, w), [4, 8], [0.3, 0.2], seed + 1509)
    M = np.clip(M + np.maximum(0, micro - 0.3) * 0.15, 0, 1).astype(np.float32)

    # Temper zone affects roughness - blued areas are smoother, straw areas rougher
    temp_zones = multi_scale_noise((h, w), [2, 3, 6], [0.4, 0.35, 0.25], seed + 1508)
    temp_zones = (temp_zones + 1.0) / 2.0
    R = np.clip(base_r * (0.85 + temp_zones * 0.15), 0, 1).astype(np.float32)

    # Clarity varies with tempering - blued zones have higher clarity
    CC = np.clip(0.7 + temp_zones * 0.15, 0, 1).astype(np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 0, 255).astype(np.float32),
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


# PATINA BRONZE - Verdigris copper carbonate formation model
def paint_patina_bronze_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Verdigris formation (copper carbonate Cu2CO3(OH)2) - greenish
    oxidation = multi_scale_noise((h, w), [2, 3, 6], [0.45, 0.35, 0.2], seed + 1510)
    oxidation = (oxidation + 1.0) / 2.0
    
    # Underlying bronze warmth
    effect = base.copy()
    effect[:, :, 0] = np.clip(base[:, :, 0] * (0.8 + oxidation * 0.15), 0, 1)
    effect[:, :, 1] = np.clip(base[:, :, 1] * (0.7 + oxidation * 0.35), 0, 1)
    effect[:, :, 2] = np.clip(base[:, :, 2] + oxidation * 0.25, 0, 1)
    
    # Moisture-driven patina zones (lighter greens at edges)
    y, x = get_mgrid((h, w))
    moisture = np.exp(-((y - h/2)**2 + (x - w/2)**2) / (h * w * 0.1))
    
    verdigris = moisture * oxidation * 0.3
    effect[:, :, 0] = np.clip(effect[:, :, 0] - verdigris * 0.2, 0, 1)
    effect[:, :, 1] = np.clip(effect[:, :, 1] + verdigris * 0.3, 0, 1)
    effect[:, :, 2] = np.clip(effect[:, :, 2] + verdigris * 0.1, 0, 1)
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.07 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_patina_bronze(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Patinated surface is rough but with some metallic undertone
    M = np.full((h, w), np.clip(base_m - 0.2, 0.15, 1), dtype=np.float32)
    
    # Oxidation roughness
    oxidation = multi_scale_noise((h, w), [2, 3], [0.4, 0.3], seed + 1510)
    M = np.clip(M - (oxidation + 1.0) / 2.0 * 0.15, 0.15, 1).astype(np.float32)
    
    # Warm specular (bronze undertone)
    R = np.full((h, w), np.clip(base_r * 0.75, 0, 1), dtype=np.float32)
    
    # Low-medium clarity (patina veils the surface)
    CC = np.full((h, w), 0.4, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# PATINA COAT - General oxidation with moisture-driven patina zones
def paint_patina_coat_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # General oxidation layer
    oxide = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 1511)
    oxide = (oxide + 1.0) / 2.0
    
    # Moisture gradient (top-down environment exposure)
    y, x = get_mgrid((h, w))
    moisture = y / h
    
    # Patina zone mixing
    patina_strength = (oxide * 0.6 + moisture * 0.4)
    
    effect = base.copy()
    effect[:, :, 0] = np.clip(base[:, :, 0] * (1.0 - patina_strength * 0.25), 0, 1)
    effect[:, :, 1] = np.clip(base[:, :, 1] * (1.0 - patina_strength * 0.15), 0, 1)
    effect[:, :, 2] = np.clip(base[:, :, 2] * (1.0 - patina_strength * 0.2), 0, 1)
    
    # Highlight wet/dry patina zones (greenish at high moisture)
    wet = moisture > 0.5
    effect[wet, 1] = np.clip(effect[wet, 1] + 0.1 * patina_strength[wet], 0, 1)
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_patina_coat(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Oxidized coat reduces specularity
    M = np.full((h, w), np.clip(base_m - 0.25, 0.1, 1), dtype=np.float32)
    
    # Patina unevenness adds roughness
    oxide = multi_scale_noise((h, w), [2, 4], [0.35, 0.25], seed + 1511)
    M = np.clip(M - (oxide + 1.0) / 2.0 * 0.2, 0.1, 1).astype(np.float32)
    
    # Dull warm specular
    R = np.full((h, w), np.clip(base_r * 0.65, 0, 1), dtype=np.float32)
    
    # Very low clarity (thick patina layer)
    CC = np.full((h, w), 0.25, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# RAW ALUMINUM - Mill-finish aluminum with rolling marks and oxide bloom
def paint_raw_aluminum_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Rolling mill marks (directional linear pattern)
    y, x = get_mgrid((h, w))
    rolling = np.sin(y * 0.05) * 0.3 + 0.7
    
    # Directional noise for rolling texture
    roll_texture = multi_scale_noise((h, w), [1, 2], [0.5, 0.3], seed + 1512)
    rolling = rolling + (roll_texture * 0.2)
    rolling = np.clip(rolling, 0.5, 1.0)
    
    # Aluminum oxide bloom (white oxidation)
    oxide = multi_scale_noise((h, w), [2, 3, 6], [0.4, 0.3, 0.3], seed + 1513)
    oxide = np.maximum(0, oxide) * 0.5
    
    effect = base.copy()
    effect[:, :, 0] = np.clip(base[:, :, 0] * rolling + oxide * 0.15, 0, 1)
    effect[:, :, 1] = np.clip(base[:, :, 1] * rolling + oxide * 0.15, 0, 1)
    effect[:, :, 2] = np.clip(base[:, :, 2] * rolling + oxide * 0.2, 0, 1)
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_raw_aluminum(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Mill finish is moderately rough with directional texture
    y, x = get_mgrid((h, w))
    rolling = np.sin(y * 0.05) * 0.2 + 0.5
    
    M = np.full((h, w), np.clip(base_m + rolling * 0.15, 0, 1), dtype=np.float32)
    
    # Oxide bloom adds micro-roughness
    oxide = multi_scale_noise((h, w), [2, 3], [0.3, 0.25], seed + 1513)
    M = np.clip(M - (oxide + 1.0) / 2.0 * 0.15, 0, 1).astype(np.float32)
    
    # Bright aluminum specular
    R = np.full((h, w), np.clip(base_r + 0.1, 0, 1), dtype=np.float32)
    
    # Medium-high clarity
    CC = np.full((h, w), 0.65, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# SANDBLASTED - Abrasive particle impact crater distribution model
def paint_sandblasted_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Impact crater distribution (clustered impacts)
    impacts = multi_scale_noise((h, w), [1, 1, 2], [0.5, 0.4, 0.3], seed + 1514)
    impacts = np.maximum(0, impacts - 0.2) * 1.2
    impacts = np.clip(impacts, 0, 1)
    
    # Crater depth variation
    depth = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 1515)
    depth = (depth + 1.0) / 2.0
    
    # Surface roughening (whitening from exposure)
    roughness = impacts * depth * 0.4
    
    effect = base.copy()
    effect[:, :, 0] = np.clip(base[:, :, 0] + roughness * 0.2, 0, 1)
    effect[:, :, 1] = np.clip(base[:, :, 1] + roughness * 0.2, 0, 1)
    effect[:, :, 2] = np.clip(base[:, :, 2] + roughness * 0.15, 0, 1)
    
    # Crater shadow darkening
    shadow = impacts * (1.0 - depth) * 0.2
    effect = np.dstack([np.clip(effect[:, :, i] * (1.0 - shadow), 0, 1) for i in range(3)])
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.07 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_sandblasted(shape, seed, sm, base_m, base_r):
    h, w = shape = shape if len(shape) == 2 else shape[:2]
    
    # Sandblasted surface is highly rough
    M = np.full((h, w), np.clip(base_m - 0.4, 0.1, 1), dtype=np.float32)
    
    # Impact craters add significant roughness
    impacts = multi_scale_noise((h, w), [1, 1], [0.45, 0.35], seed + 1514)
    M = np.clip(M - np.maximum(0, impacts - 0.2) * 0.25, 0.1, 1).astype(np.float32)
    
    # Very dull specular response
    R = np.full((h, w), np.clip(base_r * 0.5, 0, 1), dtype=np.float32)
    
    # Very low clarity (matte finish)
    CC = np.full((h, w), 0.15, dtype=np.float32)
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))
