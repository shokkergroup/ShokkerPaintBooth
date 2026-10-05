"""ANIME INSPIRED base finishes — thin wrappers over the anime_math 25-structure library.

[SPB ANIME OVERHAUL 2026-08-25] Owner mandate: "expand the 19 we have to 25 designs and make
them mind melting… NO REPEATS, NO LAZINESS." The previous 10 hand-rolled fns here scored M7
55.9–72.3 (ALL below the 75 floor; speed_lines 55.9 worst) — single low-frequency fields and
recolors. They are rebuilt as married paint+spec pairs generated in ONE pass from shared
geometry in engine/paint_v2/anime_math.py (ledger: docs/ANIME_OVERHAUL_2026-08-25.md):

    anime_cel_shade_chrome -> cel_terminator    (multi-light cel bands + SDF ink + hatch penumbra)
    anime_speed_lines      -> speedline_storm   (interfering multi-focal radial line systems)
    anime_sparkle_burst    -> shoujo_sparkle    (star SDFs + bubble bokeh + prism flares)
    anime_gradient_hair    -> inkbrush_strands  (anisotropic strand flow + angle-mapped sheen)
    anime_mecha_plate      -> mecha_greeble     (chamfered panels + rivets/vents/chevrons/glow seams)
    anime_sakura_scatter   -> sakura_hurricane  (curl-advected 5-notch petal storm, 3 depth layers)
    anime_energy_aura      -> ki_corona         (advected aura shells + filaments + embers)
    anime_comic_halftone   -> screentone_moire  (interfering Ben-Day lattices + hatch pockets)
    anime_neon_outline     -> neo_tokyo_glow    (aerial night city: windows/neon/wet streets)
    anime_crystal_facet    -> shard_cascade     (voronoi shards + refraction stripes + glints)

A FIXED structure seed keeps paint and spec geometrically identical (married) regardless of
what seed the engine forwards; `sm` scales the spec toward the finish's registry base values.
All structures gate-verified: pairwise similarity <0.35, coverage >=0.60, fineness >=0.15,
<3 s @2048 (see tests/regression_anime_uniqueness_test.py).
"""
import numpy as np

import engine.paint_v2.anime_math as am

_SEED = 7  # fixed so paint+spec stay married even if the engine varies seeds per channel


def _shape2(shape):
    return (int(shape[0]), int(shape[1]))


def _blend_art(paint, shape, mask, pm, art):
    """Blend a full-canvas art field over the incoming paint through mask*pm."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    m3 = np.asarray(mask, np.float32)
    if m3.ndim == 3:
        m3 = m3[:, :, 0]
    m3 = m3[:, :, None]
    bl = np.clip(float(pm), 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1 - m3 * bl) + np.clip(art, 0, 1) * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


def _spec_from(key, shape, sm, base_m, base_r):
    """Married spec channels, eased toward the registry base when sm < 1."""
    spec = am.build(key, _shape2(shape), _SEED)["spec"]
    t = np.clip(float(sm), 0.0, 1.0)
    M = spec[:, :, 0] * t + float(base_m) * (1 - t)
    R = spec[:, :, 1] * t + float(base_r) * (1 - t)
    CC = spec[:, :, 2] * t + 20.0 * (1 - t)
    return M.astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32)


def _mk_pair(key):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        art = am.build(key, _shape2(shape), _SEED)["rgb"]
        return _blend_art(paint, shape, mask, pm, art)

    def spec_fn(shape, seed, sm, base_m, base_r):
        return _spec_from(key, shape, sm, base_m, base_r)

    return paint_fn, spec_fn


paint_anime_cel_shade_chrome, spec_anime_cel_shade_chrome = _mk_pair("cel_terminator")
paint_anime_speed_lines, spec_anime_speed_lines = _mk_pair("speedline_storm")
paint_anime_sparkle_burst, spec_anime_sparkle_burst = _mk_pair("shoujo_sparkle")
paint_anime_gradient_hair, spec_anime_gradient_hair = _mk_pair("inkbrush_strands")
paint_anime_mecha_plate, spec_anime_mecha_plate = _mk_pair("mecha_greeble")
paint_anime_sakura_scatter, spec_anime_sakura_scatter = _mk_pair("sakura_hurricane")
paint_anime_energy_aura, spec_anime_energy_aura = _mk_pair("ki_corona")
paint_anime_comic_halftone, spec_anime_comic_halftone = _mk_pair("screentone_moire")
paint_anime_neon_outline, spec_anime_neon_outline = _mk_pair("neo_tokyo_glow")
paint_anime_crystal_facet, spec_anime_crystal_facet = _mk_pair("shard_cascade")
