from __future__ import annotations

import itertools

import cv2
import numpy as np

from engine.paint_v2.paradigm_scifi import paint_p_volcanic_v2, spec_p_volcanic
from engine.expansions import fusions
from engine.expansions import arsenal_24k
import engine.pattern_expansion as pattern_expansion
import engine.spec_patterns as spec_patterns
from engine.perceptual_color_shift import (
    HYPERFLIP_MONOLITHICS,
    HYPERFLIP_PRESETS,
    paint_hyperflip_core,
    spec_hyperflip_core,
)
from engine.pattern_expansion import NEW_PATTERNS
from engine.spec_patterns import PATTERN_CATALOG
import shokker_engine_v2 as eng


SHAPE = (192, 192)
SHAPE_SMALL = (96, 96)


REQUESTED_FUSION_LAB_IDS = [
    "depth_bubble", "depth_canyon", "depth_crack", "depth_erosion", "depth_honeycomb", "depth_map",
    "depth_pillow", "depth_ripple", "depth_scale", "depth_vortex", "depth_wave",
    "gradient_anodized_gloss", "gradient_candy_frozen", "gradient_candy_matte", "gradient_carbon_chrome",
    "gradient_chrome_matte", "gradient_ember_ice", "gradient_metallic_satin", "gradient_obsidian_mirror",
    "gradient_pearl_chrome", "gradient_spectraflame_void",
    "aniso_circular_chrome", "aniso_crosshatch_steel", "aniso_diagonal_candy", "aniso_herringbone_gold",
    "aniso_horizontal_chrome", "aniso_radial_metallic", "aniso_spiral_mercury", "aniso_turbulence_metal",
    "aniso_vertical_pearl", "aniso_wave_titanium",
    "reactive_candy_reveal", "reactive_chrome_fade", "reactive_dual_tone", "reactive_ghost_metal",
    "reactive_matte_shine", "reactive_mirror_shadow", "reactive_pearl_flash", "reactive_pulse_metal",
    "reactive_stealth_pop", "reactive_warm_cold",
    "sparkle_champagne", "sparkle_confetti", "sparkle_constellation", "sparkle_diamond_dust",
    "sparkle_firefly", "sparkle_galaxy", "sparkle_lightning_bug", "sparkle_meteor", "sparkle_snowfall",
    "sparkle_starfield",
    "multiscale_candy_frost", "multiscale_carbon_micro", "multiscale_chrome_grain",
    "multiscale_chrome_sand", "multiscale_flake_grain", "multiscale_frost_crystal",
    "multiscale_matte_silk", "multiscale_metal_grit", "multiscale_pearl_texture", "multiscale_satin_weave",
    "weather_acid_rain", "weather_barn_dust", "weather_desert_blast", "weather_hood_bake",
    "weather_ice_storm", "weather_ocean_mist", "weather_road_spray", "weather_salt_spray",
    "weather_sun_fade", "weather_volcanic_ash",
    "exotic_anti_metal", "exotic_ceramic_void", "exotic_crystal_clear", "exotic_dark_glass",
    "exotic_foggy_chrome", "exotic_glass_paint", "exotic_inverted_candy", "exotic_liquid_glass",
    "exotic_phantom_mirror", "exotic_wet_void",
    "trizone_anodized_candy_silk", "trizone_ceramic_flake_satin", "trizone_chrome_candy_matte",
    "trizone_frozen_ember_chrome", "trizone_glass_metal_matte", "trizone_mercury_obsidian_candy",
    "trizone_pearl_carbon_gold", "trizone_stealth_spectra_frozen", "trizone_titanium_copper_chrome",
    "trizone_vanta_chrome_pearl",
    "halo_circle_pearl", "halo_crack_chrome", "halo_diamond_chrome", "halo_grid_pearl",
    "halo_hex_chrome", "halo_ripple_chrome", "halo_scale_gold", "halo_star_metal",
    "halo_voronoi_metal", "halo_wave_candy",
    "wave_candy_flow", "wave_chrome_tide", "wave_circular_radar", "wave_diagonal_sweep",
    "wave_dual_frequency", "wave_metallic_pulse", "wave_moire_metal", "wave_pearl_current",
    "wave_standing_chrome", "wave_turbulent_flow",
    "fractal_candy_chaos", "fractal_chrome_decay", "fractal_cosmic_dust", "fractal_deep_organic",
    "fractal_electric_noise", "fractal_liquid_fire", "fractal_matte_chrome", "fractal_metallic_storm",
    "fractal_pearl_cloud", "fractal_warm_cold",
    "spectral_complementary", "spectral_dark_light", "spectral_earth_sky", "spectral_inverse_logic",
    "spectral_mono_chrome", "spectral_neon_reactive", "spectral_prismatic_flip",
    "spectral_rainbow_metal", "spectral_sat_metal", "spectral_warm_cool",
]


PATTERN_MONO_REBUILD_IDS = [
    "hex_mandala", "lace_filigree", "honeycomb_organic", "baroque_scrollwork",
    "art_nouveau_vine", "penrose_quasi", "topographic_dense", "interference_rings",
    "brushed_metal_fine",
]


ORNAMENTAL_SPECIAL_IDS = [
    "hex_mandala", "lace_filigree", "honeycomb_organic", "baroque_scrollwork",
    "art_nouveau_vine", "penrose_quasi", "topographic_dense", "interference_rings",
]


SPARKLE_SYSTEM_IDS = [
    "sparkle_champagne", "sparkle_confetti", "sparkle_constellation", "sparkle_diamond_dust",
    "sparkle_firefly", "sparkle_galaxy", "sparkle_lightning_bug", "sparkle_meteor",
    "sparkle_snowfall", "sparkle_starfield",
]


METALLIC_HALO_IDS = [
    "halo_circle_pearl", "halo_crack_chrome", "halo_diamond_chrome", "halo_grid_pearl",
    "halo_hex_chrome", "halo_ripple_chrome", "halo_scale_gold", "halo_star_metal",
    "halo_voronoi_metal", "halo_wave_candy",
]


MULTISCALE_TEXTURE_IDS = [
    "multiscale_candy_frost", "multiscale_carbon_micro", "multiscale_chrome_grain",
    "multiscale_chrome_sand", "multiscale_flake_grain", "multiscale_frost_crystal",
    "multiscale_matte_silk", "multiscale_metal_grit", "multiscale_pearl_texture",
    "multiscale_satin_weave",
]


LIGHT_WAVE_IDS = [
    "wave_candy_flow", "wave_chrome_tide", "wave_circular_radar", "wave_diagonal_sweep",
    "wave_dual_frequency", "wave_metallic_pulse", "wave_moire_metal", "wave_pearl_current",
    "wave_standing_chrome", "wave_turbulent_flow",
]


SPECTRAL_REACTIVE_IDS = [
    "spectral_complementary", "spectral_dark_light", "spectral_earth_sky",
    "spectral_inverse_logic", "spectral_mono_chrome", "spectral_neon_reactive",
    "spectral_prismatic_flip", "spectral_rainbow_metal", "spectral_sat_metal",
    "spectral_warm_cool",
]


TRIZONE_RESIDUAL_BLOB_IDS = [
    "trizone_frozen_ember_chrome",
    "trizone_glass_metal_matte",
]


ATELIER_CALLEDOUT_IDS = [
    "atelier_carbon_weave_micro",
    "atelier_cathedral_glass",
    "atelier_pearl_depth_layers",
]


EXTREME_INTERNAL_DETAIL_IDS = [
    "plasma_core",
    "quantum_black",
]


CANDY_PEARL_REVIEW_IDS = [
    "tri_coat_pearl",
    "deep_pearl",
    "jelly_pearl",
    "hypershift_spectral",
]


SPEC_PATTERN_REVIEW_IDS = [
    "micro_sparkle", "sparkle_rain", "spec_sparkle_flake", "brushed_linear",
    "spec_carbon_weave", "concentric_ripple", "crackle_network", "hex_cells",
    "crushed_glass", "prismatic_shatter", "sparkle_shattered", "micro_facets",
    "voronoi_fracture", "spec_faceted_diamond", "spec_crystal_growth",
]


GHOST_GEOMETRY_IDS = [
    "ghost_hex", "ghost_stripes", "ghost_diamonds", "ghost_waves", "ghost_camo",
    "ghost_scales", "ghost_circuit", "ghost_vortex", "ghost_fracture", "ghost_quilt",
]


METALS_FORGED_SOURCE_IDS = [
    "forged_titanium",
    "brushed_gunmetal",
    "cast_iron_raw",
    "polished_brass",
    "annealed_steel",
    "oxidized_bronze",
    "damascus_steel",
]


def _fine_energy(arr: np.ndarray) -> float:
    arr = np.asarray(arr, dtype=np.float32)
    dx = np.abs(np.diff(arr, axis=1)).mean()
    dy = np.abs(np.diff(arr, axis=0)).mean()
    return float(dx + dy)


def _residual_energy(arr: np.ndarray, block: int = 8) -> float:
    arr = np.asarray(arr, dtype=np.float32)
    h, w = arr.shape
    cropped = arr[: h - (h % block), : w - (w % block)]
    coarse = cropped.reshape(cropped.shape[0] // block, block, cropped.shape[1] // block, block).mean(axis=(1, 3))
    up = np.repeat(np.repeat(coarse, block, axis=0), block, axis=1)
    return float(np.abs(cropped - up).mean())


def _normalized(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-6:
        return np.zeros_like(arr)
    return (arr - float(arr.min())) / span


def _large_blob_ratio(arr: np.ndarray, block: int = 32) -> float:
    arr = _normalized(np.asarray(arr, dtype=np.float32))
    h, w = arr.shape
    cropped = arr[: h - (h % block), : w - (w % block)]
    coarse = cropped.reshape(cropped.shape[0] // block, block, cropped.shape[1] // block, block).mean(axis=(1, 3))
    return float(np.std(coarse) / (np.std(cropped) + 1e-6))


def _color_population(rgb: np.ndarray) -> int:
    rgb = np.asarray(rgb, dtype=np.float32)
    bins = np.floor(np.clip(rgb[:, :, :3], 0, 0.999) * 8).astype(np.int16)
    packed = bins[:, :, 0] * 64 + bins[:, :, 1] * 8 + bins[:, :, 2]
    counts = np.bincount(packed.ravel(), minlength=512)
    return int((counts > (rgb.shape[0] * rgb.shape[1] * 0.002)).sum())


def _largest_region_detail(arr: np.ndarray, block: int = 16, levels: int = 6) -> tuple[float, float]:
    src = _normalized(np.asarray(arr, dtype=np.float32))
    smooth = cv2.GaussianBlur(src, (0, 0), sigmaX=block * 0.55, sigmaY=block * 0.55)
    q = np.floor(_normalized(smooth) * levels).astype(np.uint8)
    q = np.clip(q, 0, levels - 1)
    best_area = 0
    best_mask = None
    for level in range(levels):
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats((q == level).astype(np.uint8), 8)
        if count <= 1:
            continue
        idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area > best_area:
            best_area = area
            best_mask = labels == idx
    assert best_mask is not None
    eroded = cv2.erode(best_mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1).astype(bool)
    sample = eroded if eroded.any() else best_mask
    blur = cv2.GaussianBlur(src, (0, 0), sigmaX=3.0, sigmaY=3.0)
    highpass = float(np.abs(src[sample] - blur[sample]).mean())
    return float(best_area / src.size), highpass


def _block_seam_ratio(arr: np.ndarray, period: int = 16) -> float:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    gx = np.abs(np.diff(arr, axis=1))
    gy = np.abs(np.diff(arr, axis=0))
    cols = np.arange(gx.shape[1])
    rows = np.arange(gy.shape[0])
    seam_x = (cols % period == period - 1) | (cols % period == 0)
    seam_y = (rows % period == period - 1) | (rows % period == 0)
    seam = np.concatenate([gx[:, seam_x].ravel(), gy[seam_y, :].ravel()])
    off = np.concatenate([gx[:, ~seam_x].ravel(), gy[~seam_y, :].ravel()])
    return float(seam.mean() / (off.mean() + 1e-6))


def _paint_hyperflip_preset(name: str) -> tuple[np.ndarray, np.ndarray]:
    preset = HYPERFLIP_PRESETS[name]
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.12, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)
    paint_kwargs = {
        key: preset[key]
        for key in (
            "color_a",
            "color_b",
            "flake_colors",
            "density",
            "fine_density",
            "orientation",
            "turbulence",
            "base_bias",
            "carrier_chroma",
            "carrier_alpha_scale",
            "carrier_alpha_max",
            "fine_alpha_scale",
            "fine_alpha_max",
        )
        if key in preset
    }
    spec_kwargs = {
        key: preset[key]
        for key in (
            "density",
            "fine_density",
            "orientation",
            "turbulence",
            "matte_rough",
            "flash_metal",
            "flash_rough",
            "base_clearcoat",
            "flash_clearcoat",
        )
        if key in preset
    }
    painted = paint_hyperflip_core(
        paint, SHAPE, mask, seed=9901, pm=1.0, bb=np.zeros(SHAPE, dtype=np.float32), **paint_kwargs
    )
    spec = spec_hyperflip_core(SHAPE, mask, seed=9901, sm=1.0, **spec_kwargs)
    return painted, spec


def _spec_m_channel(spec_out: object) -> np.ndarray:
    if isinstance(spec_out, tuple):
        return np.asarray(spec_out[0], dtype=np.float32)
    arr = np.asarray(spec_out)
    if arr.ndim == 3:
        return arr[:, :, 0].astype(np.float32)
    return arr.astype(np.float32)


def _paint_base_finish(finish_id: str) -> tuple[np.ndarray, np.ndarray]:
    entry = eng.BASE_REGISTRY[finish_id]
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.18, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)
    painted = entry["paint_fn"](paint, SHAPE, mask, seed=3701, pm=1.0, bb=np.zeros(SHAPE, dtype=np.float32))
    spec_m = _spec_m_channel(entry["base_spec_fn"](SHAPE, seed=3701, sm=1.0, base_m=entry["M"], base_r=entry["R"]))
    return painted, spec_m


def test_p_volcanic_uses_fine_filaments_not_broad_convection_blobs():
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.18, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)

    out = paint_p_volcanic_v2(paint, SHAPE, mask, seed=1776, pm=1.0, bb=np.zeros(SHAPE, dtype=np.float32))
    red = out[:, :, 0]
    hot = red > 0.38

    assert out.shape == paint.shape
    assert np.isfinite(out).all()
    assert float(red.max() - red.min()) > 0.34
    assert 0.006 < float(hot.mean()) < 0.34
    assert _fine_energy(red) > 0.018
    assert _residual_energy(red) > 0.020


def test_p_volcanic_spec_tracks_hot_filaments_with_opposed_roughness():
    m, r, cc = spec_p_volcanic(SHAPE, seed=1776, sm=1.0, base_m=0, base_r=80)

    for channel in (m, r, cc):
        assert channel.shape == SHAPE
        assert np.isfinite(channel).all()

    assert float(m.max() - m.min()) > 120.0
    assert float(r.max() - r.min()) > 130.0
    assert _fine_energy(m / 255.0) > 0.018
    assert _residual_energy(m / 255.0) > 0.020
    assert float(np.corrcoef(m.ravel(), r.ravel())[0, 1]) < -0.55


def test_ornamental_textures_have_detail_and_do_not_collapse_to_one_family():
    funcs = [
        eng.texture_sacred_geometry,
        eng.texture_lace_filigree,
        eng.texture_honeycomb_organic,
        eng.texture_baroque_scrollwork,
        eng.texture_art_nouveau_vine,
        eng.texture_penrose_quasi,
        eng.texture_topographic_dense,
        eng.texture_interference_rings,
    ]

    patterns = {}
    mask = np.ones(SHAPE, dtype=np.float32)
    for i, fn in enumerate(funcs):
        arr = np.asarray(fn(SHAPE, mask, seed=2400 + i, sm=1.0)["pattern_val"], dtype=np.float32)
        assert arr.shape == SHAPE, fn.__name__
        assert np.isfinite(arr).all(), fn.__name__
        assert float(arr.max() - arr.min()) > 0.42, fn.__name__
        assert _fine_energy(arr) > 0.018, fn.__name__
        assert _residual_energy(arr) > 0.018, fn.__name__
        patterns[fn.__name__] = _normalized(arr).ravel()

    for (name_a, a), (name_b, b) in itertools.combinations(patterns.items(), 2):
        corr = float(np.corrcoef(a, b)[0, 1])
        assert abs(corr) < 0.965, f"{name_a} and {name_b} are too similar: corr={corr:.3f}"


def test_ornamental_special_monolithics_are_visible_and_not_catalog_fallbacks():
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.18, dtype=np.float32)
    bb = np.zeros(SHAPE_SMALL, dtype=np.float32)
    fallback_ids = getattr(eng, "CATALOG_FALLBACK_WIRED_IDS", set())
    fingerprints = {}

    for i, finish_id in enumerate(ORNAMENTAL_SPECIAL_IDS):
        assert finish_id in eng.MONOLITHIC_REGISTRY
        assert finish_id not in fallback_ids
        spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[finish_id]
        rgb = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=6100 + i, pm=1.0, bb=bb)
        spec_m = _spec_m_channel(spec_fn(SHAPE_SMALL, mask, 6100 + i, 1.0))
        luma = rgb[:, :, :3].mean(axis=2)

        assert np.isfinite(rgb).all(), finish_id
        assert float(rgb[:, :, :3].std(axis=(0, 1)).max()) > 0.045, finish_id
        assert _fine_energy(luma) > 0.010, finish_id
        assert _residual_energy(luma) > 0.004, finish_id
        assert float(spec_m.max() - spec_m.min()) > 82.0, finish_id
        fingerprints[finish_id] = _normalized(luma).ravel()

    for (id_a, a), (id_b, b) in itertools.combinations(fingerprints.items(), 2):
        corr = float(np.corrcoef(a, b)[0, 1])
        assert abs(corr) < 0.94, f"{id_a} and {id_b} monolithic paints are too similar: corr={corr:.3f}"


def test_hyperflip_embeds_opponent_colors_and_spec_selects_flash_population():
    red_blue, spec = _paint_hyperflip_preset("hyperflip_red_blue")
    red_signal = red_blue[:, :, 0]
    blue_signal = red_blue[:, :, 2]
    metallic = spec[:, :, 0].astype(np.float32)
    roughness = spec[:, :, 1].astype(np.float32)
    chroma_leak = blue_signal / np.maximum(red_signal + blue_signal, 1e-6)
    blue_dominant = blue_signal > red_signal
    cobalt_population = (blue_signal > 0.30) & (chroma_leak > 0.36)

    assert float(red_signal.mean()) > 0.72
    assert 0.052 < float(chroma_leak.mean()) < 0.115
    assert 0.45 < float(np.quantile(chroma_leak, 0.95)) < 0.64
    assert 0.035 < float(blue_dominant.mean()) < 0.090
    assert 0.045 < float(cobalt_population.mean()) < 0.110
    assert _fine_energy(blue_signal) > 0.060
    assert _residual_energy(blue_signal) > 0.030
    assert 120.0 < float(metallic.max() - metallic.min()) < 155.0
    assert float(roughness.max() - roughness.min()) > 145.0
    assert int(spec[:, :, 2].min()) >= 110
    assert float(np.corrcoef((1.0 - red_signal).ravel(), metallic.ravel())[0, 1]) > 0.70
    assert float(np.corrcoef(metallic.ravel(), roughness.ravel())[0, 1]) < -0.80


def test_hyperflip_batch_is_registered_and_keeps_fine_flake_detail():
    expected = {
        "hyperflip_red_blue",
        "hyperflip_pink_black",
        "hyperflip_orange_cyan",
        "hyperflip_lime_purple",
        "hyperflip_purple_gold",
        "hyperflip_electric_blue_copper",
        "hyperflip_bronze_teal",
        "hyperflip_silver_violet",
        "hyperflip_crimson_prism",
        "hyperflip_midnight_opal",
    }
    assert set(HYPERFLIP_PRESETS) == expected
    assert {key.removeprefix("cx_") for key in HYPERFLIP_MONOLITHICS} == expected

    for name in sorted(expected):
        painted, spec = _paint_hyperflip_preset(name)
        assert painted.shape == (SHAPE[0], SHAPE[1], 3), name
        assert spec.shape == (SHAPE[0], SHAPE[1], 4), name
        assert np.isfinite(painted).all(), name
        assert float(painted.max() - painted.min()) > 0.25, name
        assert _fine_energy(painted[:, :, 0]) + _fine_energy(painted[:, :, 2]) > 0.020, name
        assert max(_residual_energy(painted[:, :, i]) for i in range(3)) > 0.006, name
        assert float(spec[:, :, 0].max() - spec[:, :, 0].min()) > 95.0, name
        assert float(spec[:, :, 1].max() - spec[:, :, 1].min()) > 60.0, name


def test_colorshoxx_shipping_batch_uses_fine_aligned_detail():
    eng._ensure_expansions_loaded()
    first_25 = [
        "cx_inferno", "cx_arctic", "cx_venom", "cx_solar", "cx_phantom",
        "cx_chrome_void", "cx_blood_mercury", "cx_neon_abyss", "cx_glacier_fire", "cx_obsidian_gold",
        "cx_electric_storm", "cx_rose_chrome", "cx_toxic_chrome", "cx_midnight_chrome", "cx_white_lightning",
        "cx_aurora_borealis", "cx_dragon_scale", "cx_frozen_nebula", "cx_hellfire", "cx_ocean_trench",
        "cx_supernova", "cx_prism_shatter", "cx_acid_rain", "cx_royal_spectrum", "cx_apocalypse",
    ]

    for finish_id in first_25:
        painted, spec_m = _paint_base_finish(finish_id)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        assert painted.shape == (SHAPE[0], SHAPE[1], 3), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert float(painted.max() - painted.min()) > 0.18, finish_id
        assert _fine_energy(signal) > 0.012, finish_id
        assert _residual_energy(signal) > 0.009, finish_id
        assert float(spec_m.max() - spec_m.min()) > 95.0, finish_id
        assert _fine_energy(spec_m / 255.0) > 0.010, finish_id


def test_older_colorshoxx_flake_monolithics_are_not_coarse_blocks():
    eng._ensure_expansions_loaded()
    ids = [
        "cx_gold_green", "cx_gold_purple", "cx_teal_blue", "cx_copper_rose",
        "cx_gold_olive_emerald", "cx_purple_plum_bronze", "cx_blue_teal_cyan",
        "cx_burgundy_wine_gold", "cx_sunset_horizon", "cx_northern_lights",
    ]
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)

    for finish_id in ids:
        spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[finish_id]
        painted = paint_fn(paint.copy(), SHAPE, mask, seed=4109, pm=1.0, bb=np.zeros(SHAPE, dtype=np.float32))
        spec_m = _spec_m_channel(spec_fn(SHAPE, mask, 4109, 1.0))
        assert np.isfinite(painted).all(), finish_id
        assert _fine_energy(painted.max(axis=2)) > 0.010, finish_id
        assert _residual_energy(painted.max(axis=2)) > 0.006, finish_id
        assert _fine_energy(spec_m / 255.0) > 0.008, finish_id


def test_ornamental_special_ids_are_real_pattern_driven_monolithics():
    eng._ensure_expansions_loaded()
    ids = [
        "hex_mandala", "lace_filigree", "honeycomb_organic", "baroque_scrollwork",
        "art_nouveau_vine", "penrose_quasi", "topographic_dense", "interference_rings",
    ]
    signatures = []

    for finish_id in ids:
        assert finish_id in eng.MONOLITHIC_REGISTRY, finish_id
        spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[finish_id]
        assert spec_fn.__name__ == "_spec", finish_id
        assert paint_fn.__name__ == "_paint", finish_id
        m = _spec_m_channel(spec_fn(SHAPE, seed=5201, sm=1.0, base_m=80, base_r=80))
        assert float(m.max() - m.min()) > 95.0, finish_id
        assert _fine_energy(m / 255.0) > 0.012, finish_id
        signatures.append(_normalized(m).ravel())

    for a, b in itertools.combinations(signatures, 2):
        assert abs(float(np.corrcoef(a, b)[0, 1])) < 0.985


def test_ornamental_tuple_specs_survive_runtime_sanitizer():
    """Pattern-driven ornamental specials return (M, R, CC), not HxWx4."""
    ids = [
        "hex_mandala", "lace_filigree", "honeycomb_organic", "baroque_scrollwork",
        "art_nouveau_vine", "penrose_quasi", "topographic_dense", "interference_rings",
    ]
    signatures = []
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)

    for finish_id in ids:
        spec_fn, _paint_fn = eng.MONOLITHIC_REGISTRY[finish_id]
        raw_spec = spec_fn(SHAPE_SMALL, mask, seed=5311, sm=1.0)
        assert isinstance(raw_spec, tuple), finish_id
        spec = eng._sanitize_spec_result(raw_spec, SHAPE_SMALL)
        assert spec.shape == (SHAPE_SMALL[0], SHAPE_SMALL[1], 4), finish_id
        assert float(spec[:, :, 0].max() - spec[:, :, 0].min()) > 95.0, finish_id
        signatures.append(_normalized(spec[:, :, 0]).ravel())

    for a, b in itertools.combinations(signatures, 2):
        assert abs(float(np.corrcoef(a, b)[0, 1])) < 0.985


def test_spec_patterns_and_decades_get_micro_detail_ratchets():
    mask = np.ones(SHAPE, dtype=np.float32)
    spec_ids = ["micro_sparkle", "sparkle_rain", "spec_sparkle_flake", "brushed_linear", "spec_carbon_weave"]
    decade_ids = ["decade_50s_starburst", "decade_70s_sparkle", "decade_80s_memphis", "decade_90s_grunge"]

    for pattern_id in spec_ids:
        arr = PATTERN_CATALOG[pattern_id](SHAPE, seed=6101, sm=1.0)
        assert np.isfinite(arr).all(), pattern_id
        assert float(arr.max() - arr.min()) > 0.35, pattern_id
        assert _fine_energy(arr) > 0.035, pattern_id

    for pattern_id in decade_ids:
        arr = NEW_PATTERNS[pattern_id]["texture_fn"](SHAPE, mask, seed=6203, sm=1.0)["pattern_val"]
        assert np.isfinite(arr).all(), pattern_id
        assert float(arr.max() - arr.min()) > 0.45, pattern_id
        assert _fine_energy(arr) > 0.025, pattern_id


def test_requested_fusion_lab_ids_have_individual_rebuild_profiles_and_depth_map_is_real():
    assert len(REQUESTED_FUSION_LAB_IDS) == len(set(REQUESTED_FUSION_LAB_IDS))
    assert set(REQUESTED_FUSION_LAB_IDS).issubset(fusions.FUSION_REGISTRY)
    assert set(REQUESTED_FUSION_LAB_IDS).issubset(fusions._FUSION_DETAIL_PROFILES)

    profile_signatures = {
        finish_id: tuple(fusions._FUSION_DETAIL_PROFILES[finish_id].items())
        for finish_id in REQUESTED_FUSION_LAB_IDS
    }
    assert len(set(profile_signatures.values())) == len(profile_signatures)

    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    for finish_id in REQUESTED_FUSION_LAB_IDS:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE_SMALL, mask, seed=7103, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7103, pm=1.0, bb=np.zeros(SHAPE_SMALL, dtype=np.float32))
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32

        assert spec.shape == (SHAPE_SMALL[0], SHAPE_SMALL[1], 4), finish_id
        assert painted.shape == paint.shape, finish_id
        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        spec_ranges = [float(spec[:, :, ch].max() - spec[:, :, ch].min()) for ch in range(3)]
        assert max(spec_ranges) > 18.0, finish_id
        assert _fine_energy(spec[:, :, 0] / 255.0) > 0.004, finish_id
        assert _fine_energy(signal) > 0.002, finish_id


def test_ghost_geometry_fusions_have_individual_profiles_and_visible_spec_range():
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    for finish_id in GHOST_GEOMETRY_IDS:
        assert finish_id in fusions.FUSION_REGISTRY
        assert finish_id in fusions._FUSION_DETAIL_PROFILES
        spec_fn, _paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE_SMALL, mask, seed=7701, sm=1.0)
        m = _spec_m_channel(spec)
        assert float(m.max() - m.min()) >= 44.0, finish_id
        assert _fine_energy(m / 255.0) > 0.010, finish_id


def test_sparkle_systems_render_dense_crushed_sand_without_square_blobs():
    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    bb = np.zeros(SHAPE_SMALL, dtype=np.float32)

    for finish_id in SPARKLE_SYSTEM_IDS:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE_SMALL, mask, seed=7103, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7103, pm=1.0, bb=bb)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        spec_ranges = [float(spec[:, :, ch].max() - spec[:, :, ch].min()) for ch in range(3)]

        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert max(spec_ranges) > 140.0, finish_id
        assert _fine_energy(signal) > 0.030, finish_id
        assert _residual_energy(signal) > 0.014, finish_id
        assert _large_blob_ratio(signal) < 0.36, finish_id


def test_multiscale_textures_keep_fine_material_detail_without_square_cells():
    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    bb = np.zeros(SHAPE_SMALL, dtype=np.float32)
    fingerprints = []

    for finish_id in MULTISCALE_TEXTURE_IDS:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE_SMALL, mask, seed=7103, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7103, pm=1.0, bb=bb)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        metallic = spec[:, :, 0].astype(np.float32) / 255.0

        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert float(signal.max() - signal.min()) > 0.15, finish_id
        assert float(metallic.max() - metallic.min()) > 0.28, finish_id
        assert _fine_energy(signal) > 0.010, finish_id
        assert _residual_energy(signal) > 0.006, finish_id
        assert _block_seam_ratio(signal, period=16) < 1.35, finish_id
        assert _block_seam_ratio(metallic, period=16) < 1.35, finish_id
        fingerprints.append(_normalized(signal).ravel())

    for a, b in itertools.combinations(fingerprints, 2):
        assert abs(float(np.corrcoef(a, b)[0, 1])) < 0.985


def test_light_waves_use_smooth_crests_without_square_cell_noise():
    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    bb = np.zeros(SHAPE_SMALL, dtype=np.float32)
    fingerprints = []

    for finish_id in LIGHT_WAVE_IDS:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE_SMALL, mask, seed=7119, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7119, pm=1.0, bb=bb)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        metallic = spec[:, :, 0].astype(np.float32) / 255.0

        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert float(signal.max() - signal.min()) > 0.18, finish_id
        assert float(metallic.max() - metallic.min()) > 0.18, finish_id
        assert _fine_energy(signal) > 0.018, finish_id
        assert _residual_energy(signal) > 0.014, finish_id
        assert _block_seam_ratio(signal, period=16) < 1.22, finish_id
        assert _block_seam_ratio(metallic, period=16) < 1.22, finish_id
        fingerprints.append(_normalized(signal).ravel())

    for a, b in itertools.combinations(fingerprints, 2):
        assert abs(float(np.corrcoef(a, b)[0, 1])) < 0.985


def test_spectral_reactive_uses_smooth_optical_fields_without_square_cells():
    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    bb = np.zeros(SHAPE_SMALL, dtype=np.float32)
    fingerprints = []

    for finish_id in SPECTRAL_REACTIVE_IDS:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE_SMALL, mask, seed=7127, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7127, pm=1.0, bb=bb)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        metallic = spec[:, :, 0].astype(np.float32) / 255.0
        roughness = spec[:, :, 1].astype(np.float32) / 255.0

        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert float(signal.max() - signal.min()) > 0.12, finish_id
        assert float(metallic.max() - metallic.min()) > 0.22, finish_id
        assert _fine_energy(signal) > 0.010, finish_id
        assert _residual_energy(signal) > 0.006, finish_id
        assert _block_seam_ratio(signal, period=16) < 1.42, finish_id
        assert _block_seam_ratio(metallic, period=16) < 1.42, finish_id
        assert _block_seam_ratio(roughness, period=16) < 1.42, finish_id
        fingerprints.append(_normalized(signal).ravel())

    for a, b in itertools.combinations(fingerprints, 2):
        assert abs(float(np.corrcoef(a, b)[0, 1])) < 0.985


def test_residual_trizone_materials_are_not_blob_dominant_or_internally_flat():
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)
    bb = np.zeros(SHAPE, dtype=np.float32)

    for finish_id in TRIZONE_RESIDUAL_BLOB_IDS:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE, mask, seed=7111, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE, mask, seed=7111, pm=1.0, bb=bb)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        metallic = spec[:, :, 0].astype(np.float32) / 255.0
        paint_region_ratio, paint_region_detail = _largest_region_detail(signal)
        spec_region_ratio, spec_region_detail = _largest_region_detail(metallic)

        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert _large_blob_ratio(signal) < 0.78, finish_id
        assert paint_region_ratio > 0.12, finish_id
        assert spec_region_ratio > 0.12, finish_id
        assert paint_region_detail > 0.040, finish_id
        assert spec_region_detail > 0.040, finish_id
        assert _fine_energy(signal) > 0.040, finish_id
        assert _residual_energy(signal) > 0.022, finish_id


def test_called_out_atelier_finishes_keep_ultra_detail_not_flat_regions():
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.18, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)
    bb = np.zeros(SHAPE, dtype=np.float32)

    for finish_id in ATELIER_CALLEDOUT_IDS:
        assert finish_id in eng.MONOLITHIC_REGISTRY
        spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[finish_id]
        spec = spec_fn(SHAPE, mask, seed=7301, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE, mask, seed=7301, pm=1.0, bb=bb)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        metallic = spec[:, :, 0].astype(np.float32) / 255.0
        _paint_region_ratio, paint_region_detail = _largest_region_detail(signal)
        _spec_region_ratio, spec_region_detail = _largest_region_detail(metallic)

        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert _fine_energy(signal) > 0.026, finish_id
        assert _residual_energy(signal) > 0.010, finish_id
        assert _large_blob_ratio(signal) < 0.78, finish_id
        assert max(paint_region_detail, spec_region_detail) > 0.050, finish_id

    spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY["atelier_carbon_weave_micro"]
    painted = paint_fn(paint.copy(), SHAPE, mask, seed=7301, pm=1.0, bb=bb)
    assert _color_population(painted) >= 2


def test_extreme_experimental_bases_keep_internal_detail_in_large_regions():
    for finish_id in EXTREME_INTERNAL_DETAIL_IDS:
        painted, spec_m = _paint_base_finish(finish_id)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        _paint_region_ratio, paint_region_detail = _largest_region_detail(signal)
        _spec_region_ratio, spec_region_detail = _largest_region_detail(spec_m / 255.0)

        assert np.isfinite(painted).all(), finish_id
        assert np.isfinite(spec_m).all(), finish_id
        assert _fine_energy(signal) > 0.030, finish_id
        assert _residual_energy(signal) > 0.014, finish_id
        assert _large_blob_ratio(signal) < 0.78, finish_id
        assert max(paint_region_detail, spec_region_detail) > 0.040, finish_id


def test_candy_pearl_review_targets_keep_depth_and_pixel_detail():
    for finish_id in CANDY_PEARL_REVIEW_IDS:
        painted, spec_m = _paint_base_finish(finish_id)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        _paint_region_ratio, paint_region_detail = _largest_region_detail(signal)
        _spec_region_ratio, spec_region_detail = _largest_region_detail(spec_m / 255.0)

        assert np.isfinite(painted).all(), finish_id
        assert np.isfinite(spec_m).all(), finish_id
        assert _fine_energy(signal) > 0.018, finish_id
        assert _residual_energy(signal) > 0.008, finish_id
        assert _large_blob_ratio(signal) < 0.78, finish_id
        assert max(paint_region_detail, spec_region_detail) > 0.040, finish_id
        assert _color_population(painted) >= 2, finish_id


def test_metallic_halos_have_broad_aligned_coverage_without_block_artifacts():
    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    bb = np.zeros(SHAPE_SMALL, dtype=np.float32)

    for finish_id in METALLIC_HALO_IDS:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = spec_fn(SHAPE_SMALL, mask, seed=7111, sm=1.0)
        painted = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7111, pm=1.0, bb=bb)
        signal = painted[:, :, 0] * 0.31 + painted[:, :, 1] * 0.37 + painted[:, :, 2] * 0.32
        metallic = spec[:, :, 0].astype(np.float32) / 255.0
        hot = metallic > np.quantile(metallic, 0.70)

        assert np.isfinite(spec).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert float(metallic.max() - metallic.min()) > 0.42, finish_id
        assert 0.20 < float(hot.mean()) < 0.46, finish_id
        assert _fine_energy(signal) > 0.012, finish_id
        assert _residual_energy(signal) > 0.004, finish_id
        assert _large_blob_ratio(signal) < 0.62, finish_id


def test_spec_patterns_have_stronger_category_specific_micro_overlays():
    for pattern_id in SPEC_PATTERN_REVIEW_IDS:
        assert pattern_id in PATTERN_CATALOG
        arr = np.asarray(PATTERN_CATALOG[pattern_id](SHAPE, seed=6127, sm=1.0), dtype=np.float32)
        assert np.isfinite(arr).all(), pattern_id
        assert float(arr.max() - arr.min()) > 0.42, pattern_id
        assert _fine_energy(arr) > 0.040, pattern_id
        assert _residual_energy(arr) > 0.016, pattern_id


def test_decade_patterns_keep_era_signature_and_pixel_detail():
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    decade_ids = [pid for pid in pattern_expansion.NEW_PATTERNS if pid.startswith("decade_")]
    assert len(decade_ids) >= 50

    signatures = []
    for pattern_id in decade_ids:
        arr = np.asarray(
            pattern_expansion.NEW_PATTERNS[pattern_id]["texture_fn"](SHAPE_SMALL, mask, seed=6221, sm=1.0)["pattern_val"],
            dtype=np.float32,
        )
        assert np.isfinite(arr).all(), pattern_id
        assert float(arr.max() - arr.min()) > 0.44, pattern_id
        assert _fine_energy(arr) > 0.020, pattern_id
        assert _residual_energy(arr) > 0.010, pattern_id
        signatures.append(_normalized(arr).ravel())

    sampled = signatures[::5]
    for a, b in itertools.combinations(sampled, 2):
        assert abs(float(np.corrcoef(a, b)[0, 1])) < 0.985


def test_pattern_monolithic_material_world_ids_have_individual_rebuild_profiles():
    assert set(PATTERN_MONO_REBUILD_IDS).issubset(eng._PATTERN_MONO_PROFILES)
    assert len({
        tuple(eng._PATTERN_MONO_PROFILES[finish_id].items())
        for finish_id in PATTERN_MONO_REBUILD_IDS
    }) == len(PATTERN_MONO_REBUILD_IDS)

    eng._ensure_expansions_loaded()
    signatures = []
    for finish_id in PATTERN_MONO_REBUILD_IDS:
        spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[finish_id]
        m = _spec_m_channel(spec_fn(SHAPE_SMALL, seed=7201, sm=1.0, base_m=80, base_r=80))
        paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
        painted = paint_fn(
            paint, SHAPE_SMALL, np.ones(SHAPE_SMALL, dtype=np.float32),
            seed=7201, pm=1.0, bb=np.zeros(SHAPE_SMALL, dtype=np.float32),
        )

        assert np.isfinite(m).all(), finish_id
        assert np.isfinite(painted).all(), finish_id
        assert float(m.max() - m.min()) > 70.0, finish_id
        assert _fine_energy(m / 255.0) > 0.006, finish_id
        signatures.append(_normalized(m).ravel())

    for a, b in itertools.combinations(signatures, 2):
        assert abs(float(np.corrcoef(a, b)[0, 1])) < 0.990


def test_spec_and_regular_pattern_registries_have_per_id_detail_profiles():
    assert set(spec_patterns.PATTERN_CATALOG).issubset(spec_patterns._SPEC_PATTERN_DETAIL_PROFILES)
    assert set(pattern_expansion.NEW_PATTERNS).issubset(pattern_expansion._EXPANSION_PATTERN_DETAIL_PROFILES)

    spec_profiles = [
        tuple(sorted(profile.items()))
        for profile in spec_patterns._SPEC_PATTERN_DETAIL_PROFILES.values()
    ]
    expansion_profiles = [
        tuple(sorted(profile.items()))
        for profile in pattern_expansion._EXPANSION_PATTERN_DETAIL_PROFILES.values()
    ]

    assert len(set(spec_profiles)) >= int(len(spec_profiles) * 0.90)
    assert len(set(expansion_profiles)) >= int(len(expansion_profiles) * 0.90)


def test_metals_forged_source_paint_functions_do_not_crash_or_get_masked():
    paint = np.full((SHAPE_SMALL[0], SHAPE_SMALL[1], 3), 0.16, dtype=np.float32)
    mask = np.ones(SHAPE_SMALL, dtype=np.float32)
    scalar_bb = 0.0
    array_bb = np.zeros(SHAPE_SMALL, dtype=np.float32)

    for finish_id in METALS_FORGED_SOURCE_IDS:
        spec_fn, paint_fn = getattr(arsenal_24k, f"spec_{finish_id}"), getattr(arsenal_24k, f"paint_{finish_id}")
        source_out = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7301, pm=1.0, bb=scalar_bb)
        array_bb_out = paint_fn(paint.copy(), SHAPE_SMALL, mask, seed=7301, pm=1.0, bb=array_bb)
        source_spec = spec_fn(SHAPE_SMALL, mask, seed=7301, sm=1.0)

        assert source_out.shape == paint.shape, finish_id
        assert array_bb_out.shape == paint.shape, finish_id
        assert source_spec.shape == (SHAPE_SMALL[0], SHAPE_SMALL[1], 4), finish_id
        assert np.isfinite(source_out).all(), finish_id
        assert np.isfinite(array_bb_out).all(), finish_id
        assert np.isfinite(source_spec).all(), finish_id
        assert float(np.abs(source_out - paint).mean()) > 0.010, finish_id
        assert max(float(source_spec[:, :, ch].max() - source_spec[:, :, ch].min()) for ch in range(3)) >= 8.0, finish_id

    eng._ensure_expansions_loaded()
    for finish_id in METALS_FORGED_SOURCE_IDS:
        _spec_fn, registry_paint_fn = eng.MONOLITHIC_REGISTRY[finish_id]
        assert not getattr(registry_paint_fn, "_spb_standalone_detail_wrapped", False), finish_id
