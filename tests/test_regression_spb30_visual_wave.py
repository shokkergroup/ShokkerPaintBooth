import numpy as np


def _render_base(engine, base_id, size=160, seed=9301):
    entry = engine.BASE_REGISTRY[base_id]
    paint = np.full((size, size, 3), 0.18, dtype=np.float32)
    mask = np.ones((size, size), dtype=np.float32)
    bb = np.zeros((size, size), dtype=np.float32)
    rgb = entry["paint_fn"](paint, (size, size), mask, seed, 1.0, bb)
    spec = entry["base_spec_fn"]((size, size), seed, 1.0, float(entry.get("M", 120)), float(entry.get("R", 80)))
    return np.asarray(rgb, dtype=np.float32), tuple(np.asarray(c, dtype=np.float32) for c in spec[:3])


def test_spb30_native_category_sources_survive_expansion_load():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    expected_sources = {
        "fire_engine": "owner_review_oem_automotive",
        "school_bus": "owner_review_oem_automotive",
        "checkered_chrome": "owner_review_racing_heritage",
        "chrome_wrap": "owner_review_satin_wrap",
        "stone_marble_polished": "stone_textile",
        "stone_granite_speckled": "stone_textile",
        "stone_sandstone_warm": "stone_textile",
        "stone_obsidian_mirror": "stone_textile",
        "stone_travertine_cream": "stone_textile",
        "stone_slate_matte": "stone_textile",
        "textile_denim_weave": "stone_textile",
        "textile_canvas_rough": "stone_textile",
        "textile_silk_sheen": "stone_textile",
        "textile_velvet_crush": "stone_textile",
        "textile_burlap_coarse": "stone_textile",
        "textile_suede_soft": "stone_textile",
        "shokk_blood": "owner_review_shokk_series",
        "shokk_flux": "owner_review_shokk_series",
        "matte_wrap": "owner_review_satin_wrap",
        "color_flip_wrap": "owner_review_satin_wrap",
        "acid_rain": "owner_review_weathered_aged",
        "destroyed_coat": "owner_review_weathered_aged",
        "anime_speed_lines": "owner_review_anime",
        "anime_crystal_facet": "owner_review_anime",
        "carbon_base": "owner_review_carbon_composite",
        "forged_composite": "owner_review_carbon_composite",
        "carbon_weave": "owner_review_carbon_composite",
        "ambulance_white": "owner_review_oem_automotive",
        "smoked": "owner_review_oem_automotive",
        "diamond_coat": "owner_review_exotic_metal",
        "organic_metal": "owner_review_exotic_metal",
        "chromaflair": "owner_review_exotic_metal",
        "ferrari_rosso": "owner_review_premium_luxury",
        "porsche_pts": "owner_review_premium_luxury",
        "asphalt_grind": "owner_review_racing_heritage",
        "victory_lane": "owner_review_racing_heritage",
    }
    for base_id, module_name in expected_sources.items():
        entry = engine.BASE_REGISTRY[base_id]
        paint_fn = entry.get("paint_fn")
        spec_fn = entry.get("base_spec_fn")
        assert paint_fn is not None and spec_fn is not None
        assert module_name in getattr(paint_fn, "__module__", "")
        assert module_name in getattr(spec_fn, "__module__", "")
        assert not getattr(paint_fn, "_spb_regular_base_quality_wrapped", False)


def test_spb30_owner_wave_renderers_are_nonflat_and_intentful():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    fire, _ = _render_base(engine, "fire_engine")
    assert float(fire[:, :, 0].mean()) > 0.80
    assert float(fire[:, :, 0].mean() - fire[:, :, 1].mean()) > 0.60

    school_bus, _ = _render_base(engine, "school_bus")
    assert float(school_bus[:, :, 0].mean()) > 0.80
    assert float(school_bus[:, :, 1].mean()) > 0.55
    assert float(school_bus[:, :, 2].mean()) < 0.10

    marble, marble_spec = _render_base(engine, "stone_marble_polished")
    assert float(marble.std()) > 0.035
    assert float(marble[:, :, 0].mean()) > float(marble[:, :, 2].mean())
    assert float(marble_spec[2].max() - marble_spec[2].min()) > 10.0

    granite, granite_spec = _render_base(engine, "stone_granite_speckled")
    assert float(granite.std()) > 0.055
    assert float(granite_spec[0].max() - granite_spec[0].min()) > 80.0

    denim, denim_spec = _render_base(engine, "textile_denim_weave")
    assert float(denim[:, :, 2].mean()) > float(denim[:, :, 0].mean()) * 1.8
    assert float(denim.std()) > 0.025
    assert float(denim_spec[1].max() - denim_spec[1].min()) > 20.0


def test_spb30_chameleon_classics_use_owner_review_sources_and_have_fine_detail():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    for finish_id in ("chameleon_neon", "chameleon_obsidian", "chameleon_phoenix", "mystichrome"):
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id]
        assert "owner_review_chameleon" in getattr(spec_fn, "__module__", "")
        assert "owner_review_chameleon" in getattr(paint_fn, "__module__", "")

        size = 192
        paint = np.full((size, size, 3), 0.18, dtype=np.float32)
        mask = np.ones((size, size), dtype=np.float32)
        bb = np.zeros((size, size), dtype=np.float32)
        rgb = paint_fn(paint, (size, size), mask, 9101, 1.0, bb)
        spec = spec_fn((size, size), mask, 9101, 1.0)

        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.09
        assert fine_energy > 0.010
        assert float(spec[:, :, 0].max() - spec[:, :, 0].min()) > 40.0
        assert float(spec[:, :, 2].max() - spec[:, :, 2].min()) > 8.0


def test_spb30_gradient_owner_review_sources_cover_directional_vortex_and_extended():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "grad_fire_fade",
        "grad_fire_fade_h",
        "grad_sunset_diag",
        "grad_blue_vortex",
        "grad_black_gold",
        "grad_patriot_h",
        "grad_neon_violet_diag",
        "grad_solar_vortex",
        "grad_wine_silk",
        "grad_titanium_fire",
        "grad_crimson_vortex",
        "grad_opal_vortex",
    )
    fingerprints = []
    for finish_id in ids:
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id]
        assert "owner_review_gradients" in getattr(spec_fn, "__module__", "")
        assert "owner_review_gradients" in getattr(paint_fn, "__module__", "")

        size = 176
        paint = np.full((size, size, 3), 0.16, dtype=np.float32)
        mask = np.ones((size, size), dtype=np.float32)
        bb = np.zeros((size, size), dtype=np.float32)
        rgb = paint_fn(paint, (size, size), mask, 9971, 1.0, bb)
        spec = spec_fn((size, size), mask, 9971, 1.0)

        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        spec_energy = float(np.abs(np.diff(spec[:, :, 0].astype(np.float32), axis=1)).mean())
        assert float(rgb.std()) > 0.030
        assert fine_energy > 0.0020
        assert spec_energy > 0.45
        assert float(spec[:, :, 0].max() - spec[:, :, 0].min()) > 40.0
        assert float(spec[:, :, 1].max() - spec[:, :, 1].min()) > 20.0
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        x_bias = float((luma * (xx / max(size - 1, 1))).mean())
        y_bias = float((luma * (yy / max(size - 1, 1))).mean())
        fingerprints.append(np.array([rgb[..., 0].mean(), rgb[..., 1].mean(), rgb[..., 2].mean(), luma.std(), fine_energy, x_bias, y_bias], dtype=np.float32))

    fps = np.vstack(fingerprints)
    distances = np.sqrt(((fps[:, None, :] - fps[None, :, :]) ** 2).sum(axis=2))
    nearest = distances + np.eye(len(ids), dtype=np.float32) * 999.0
    assert float(nearest.min()) > 0.010


def test_spb30_shokk_series_owner_review_sources_are_detailed():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    for base_id in ("shokk_blood", "shokk_void", "shokk_flux", "shokk_helix", "shokk_reactor", "shokk_cipher"):
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_shokk_series" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_shokk_series" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9401)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.018
        assert fine_energy > 0.0015
        assert float(spec[0].max() - spec[0].min()) > 30.0
        assert float(spec[1].max() - spec[1].min()) > 18.0


def test_spb30_satin_wrap_owner_review_sources_are_detailed():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    for base_id in ("color_flip_wrap", "frozen_matte", "liquid_wrap", "matte_wrap", "stealth_wrap", "textured_wrap"):
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_satin_wrap" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_satin_wrap" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9507)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.012
        assert fine_energy > 0.001
        assert float(spec[0].max() - spec[0].min()) > 20.0
        assert float(spec[1].max() - spec[1].min()) > 12.0


def test_spb30_weathered_aged_owner_review_sources_are_damaged_and_detailed():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    for base_id in ("acid_rain", "desert_worn", "oxidized_copper", "sun_baked", "sun_fade", "crumbling_clear", "destroyed_coat"):
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_weathered_aged" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_weathered_aged" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9601)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.012
        assert fine_energy > 0.001
        assert float(spec[0].max() - spec[0].min()) > 20.0
        assert float(spec[1].max() - spec[1].min()) > 25.0


def test_spb30_anime_owner_review_sources_are_fine_scaled_and_distinct():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "anime_cel_shade_chrome",
        "anime_speed_lines",
        "anime_sparkle_burst",
        "anime_gradient_hair",
        "anime_mecha_plate",
        "anime_sakura_scatter",
        "anime_energy_aura",
        "anime_comic_halftone",
        "anime_neon_outline",
        "anime_crystal_facet",
    )
    fingerprints = []
    for base_id in ids:
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_anime" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_anime" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9703)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        spec_energy = float(np.abs(np.diff(spec[0], axis=1)).mean() + np.abs(np.diff(spec[1], axis=0)).mean())
        assert float(rgb.std()) > 0.018
        assert fine_energy > 0.0014
        assert spec_energy > 0.55
        assert float(spec[0].max() - spec[0].min()) > 24.0
        fingerprints.append(np.array([rgb[..., 0].mean(), rgb[..., 1].mean(), rgb[..., 2].mean(), luma.std(), fine_energy], dtype=np.float32))

    fps = np.vstack(fingerprints)
    distances = np.sqrt(((fps[:, None, :] - fps[None, :, :]) ** 2).sum(axis=2))
    nearest = distances + np.eye(len(ids), dtype=np.float32) * 999.0
    assert float(nearest.min()) > 0.018


def test_spb30_carbon_composite_owner_review_sources_have_material_identity():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "aramid",
        "carbon_base",
        "carbon_ceramic",
        "fiberglass",
        "forged_composite",
        "graphene",
        "hybrid_weave",
        "kevlar_base",
        "carbon_weave",
        "forged_carbon_vis",
    )
    fingerprints = []
    for base_id in ids:
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_carbon_composite" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_carbon_composite" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9801)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.010
        assert fine_energy > 0.0013
        assert float(spec[0].max() - spec[0].min()) > 10.0
        assert float(spec[1].max() - spec[1].min()) > 10.0
        fingerprints.append(np.array([rgb[..., 0].mean(), rgb[..., 1].mean(), rgb[..., 2].mean(), luma.std(), fine_energy], dtype=np.float32))

    fps = np.vstack(fingerprints)
    distances = np.sqrt(((fps[:, None, :] - fps[None, :, :]) ** 2).sum(axis=2))
    nearest = distances + np.eye(len(ids), dtype=np.float32) * 999.0
    assert float(nearest.min()) > 0.012


def test_spb30_oem_automotive_owner_review_sources_are_vehicle_paint_grade():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "ambulance_white",
        "dealer_pearl",
        "factory_basecoat",
        "fire_engine",
        "fleet_white",
        "police_black",
        "school_bus",
        "showroom_clear",
        "smoked",
        "taxi_yellow",
    )
    for base_id in ids:
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_oem_automotive" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_oem_automotive" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9901)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.006
        assert fine_energy > 0.0009
        assert float(spec[0].max() - spec[0].min()) > 4.0
        assert float(spec[1].max() - spec[1].min()) > 4.0

    fire, _ = _render_base(engine, "fire_engine", size=192, seed=9901)
    assert float(fire[:, :, 0].mean()) > 0.85
    assert float(fire[:, :, 0].mean() - fire[:, :, 1].mean()) > 0.75

    bus, _ = _render_base(engine, "school_bus", size=192, seed=9901)
    assert float(bus[:, :, 0].mean()) > 0.88
    assert float(bus[:, :, 1].mean()) > 0.60
    assert float(bus[:, :, 2].mean()) < 0.08


def test_spb30_exotic_metal_owner_review_sources_are_distinct_and_detailed():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "anodized",
        "brushed_aluminum",
        "brushed_titanium",
        "cobalt_metal",
        "diamond_coat",
        "frozen",
        "liquid_titanium",
        "platinum",
        "raw_aluminum",
        "rose_gold",
        "titanium_raw",
        "tungsten",
        "organic_metal",
        "anodized_exotic",
        "xirallic",
        "chromaflair",
    )
    fingerprints = []
    for base_id in ids:
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_exotic_metal" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_exotic_metal" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9917)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.010
        assert fine_energy > 0.0012
        assert float(spec[0].max() - spec[0].min()) > 14.0
        assert float(spec[1].max() - spec[1].min()) > 8.0
        fingerprints.append(np.array([rgb[..., 0].mean(), rgb[..., 1].mean(), rgb[..., 2].mean(), luma.std(), fine_energy], dtype=np.float32))

    fps = np.vstack(fingerprints)
    distances = np.sqrt(((fps[:, None, :] - fps[None, :, :]) ** 2).sum(axis=2))
    nearest = distances + np.eye(len(ids), dtype=np.float32) * 999.0
    assert float(nearest.min()) > 0.010


def test_spb30_premium_luxury_owner_review_sources_are_polished_and_distinct():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "bentley_silver",
        "bugatti_blue",
        "ferrari_rosso",
        "koenigsegg_clear",
        "lamborghini_verde",
        "maybach_two_tone",
        "mclaren_orange",
        "pagani_tricolore",
        "porsche_pts",
        "satin_gold",
    )
    fingerprints = []
    for base_id in ids:
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_premium_luxury" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_premium_luxury" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9931)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.010
        assert fine_energy > 0.0012
        assert float(spec[0].max() - spec[0].min()) > 10.0
        assert float(spec[1].max() - spec[1].min()) > 8.0
        fingerprints.append(np.array([rgb[..., 0].mean(), rgb[..., 1].mean(), rgb[..., 2].mean(), luma.std(), fine_energy], dtype=np.float32))

    fps = np.vstack(fingerprints)
    distances = np.sqrt(((fps[:, None, :] - fps[None, :, :]) ** 2).sum(axis=2))
    nearest = distances + np.eye(len(ids), dtype=np.float32) * 999.0
    assert float(nearest.min()) > 0.012


def test_spb30_racing_heritage_owner_review_sources_are_detailed_and_distinct():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "asphalt_grind",
        "barn_find",
        "bullseye_chrome",
        "checkered_chrome",
        "drag_strip_gloss",
        "endurance_ceramic",
        "pace_car_pearl",
        "race_day_gloss",
        "rally_mud",
        "stock_car_enamel",
        "victory_lane",
    )
    fingerprints = []
    for base_id in ids:
        entry = engine.BASE_REGISTRY[base_id]
        assert "owner_review_racing_heritage" in getattr(entry["paint_fn"], "__module__", "")
        assert "owner_review_racing_heritage" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=192, seed=9947)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.012
        assert fine_energy > 0.0014
        assert float(spec[0].max() - spec[0].min()) > 10.0
        assert float(spec[1].max() - spec[1].min()) > 8.0
        fingerprints.append(np.array([rgb[..., 0].mean(), rgb[..., 1].mean(), rgb[..., 2].mean(), luma.std(), fine_energy], dtype=np.float32))

    fps = np.vstack(fingerprints)
    distances = np.sqrt(((fps[:, None, :] - fps[None, :, :]) ** 2).sum(axis=2))
    nearest = distances + np.eye(len(ids), dtype=np.float32) * 999.0
    assert float(nearest.min()) > 0.010


def test_spb30_stone_textile_sources_are_detailed_and_distinct():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()

    ids = (
        "stone_slate_matte",
        "stone_marble_polished",
        "stone_granite_speckled",
        "stone_sandstone_warm",
        "stone_obsidian_mirror",
        "stone_travertine_cream",
        "textile_denim_weave",
        "textile_canvas_rough",
        "textile_silk_sheen",
        "textile_velvet_crush",
        "textile_burlap_coarse",
        "textile_suede_soft",
    )
    fingerprints = []
    for base_id in ids:
        entry = engine.BASE_REGISTRY[base_id]
        assert "stone_textile" in getattr(entry["paint_fn"], "__module__", "")
        assert "stone_textile" in getattr(entry["base_spec_fn"], "__module__", "")

        rgb, spec = _render_base(engine, base_id, size=160, seed=9961)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        assert float(rgb.std()) > 0.010
        assert fine_energy > 0.0012
        assert float(spec[1].max() - spec[1].min()) > 16.0
        assert float(spec[2].max() - spec[2].min()) > 10.0
        fingerprints.append(np.array([rgb[..., 0].mean(), rgb[..., 1].mean(), rgb[..., 2].mean(), luma.std(), fine_energy], dtype=np.float32))

    fps = np.vstack(fingerprints)
    distances = np.sqrt(((fps[:, None, :] - fps[None, :, :]) ** 2).sum(axis=2))
    nearest = distances + np.eye(len(ids), dtype=np.float32) * 999.0
    assert float(nearest.min()) > 0.006
