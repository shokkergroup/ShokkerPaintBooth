"""Name-faithful fine-detail geometry for picker-visible SPEC overlays.

SPB-105 semantic correction, 2026-07-13.
Owner verdict: many overlays "don't match what the SPEC PATTERN says it is";
brick, fish scales, snake patterns and checker flag must read as their named
subjects.  This module is the auditable identity layer over the fast material
response system in :mod:`overhaul_2026`.

Every picker id is explicitly assigned.  Builders share vectorized primitives
where the real subjects share construction, but topology remains specific:
brick is staggered masonry, checker is square cloth, fish uses overlapping
scallops, snake uses keeled diamonds, and alligator uses irregular scutes.
Cells are clamped so their defining primitives remain roughly 8-32 px at
2048²; recognizability comes from silhouette, not macro-scale marks.

SPB-105 deconfetti correction, 2026-07-13: the owner rejected universal
grain/noise/confetti. Clean geometry is now the default; particulate and
textured-surface behavior are explicit opt-ins. Related identities receive
coherent named construction differences instead of hash noise for uniqueness.
"""

from __future__ import annotations

import math

import cv2
import numpy as np


_TAU = math.tau


_GROUPS: dict[str, tuple[str, ...]] = {
    "circuit_trace": ("spec_holographic_oil_circuit", "spec_ember_circuit_maze", "spec_circuit_solder_mask"),
    "mandala_sigil": ("spec_black_emboss_mandala", "samhain_ritual", "ouija_mystic", "candle_wax_veve", "midnight_gris_gris"),
    "cross_lattice": ("spec_graphite_cross_lattice", "diamond_lattice", "spec_gunmetal_geo_tessellation", "oni_veil_mosaic"),
    "marble_vein": ("spec_marble_flow_pearl", "spec_damascus_steel_spec", "spec_lfr_capitol_veins"),
    "carbon_mesh": ("spec_acid_carbon_mesh", "spec_carbon_weave", "spec_carbon_2x2_twill", "spec_carbon_3k_fine"),
    "houndstooth": ("spec_noir_houndstooth_star",),
    "chevron": ("spec_hazard_chevron_weave", "chevron_bands"),
    "burn_hole_mesh": ("spec_burn_hole_mesh",),
    "hex_cell": ("spec_teal_hex_haze", "hex_cells", "viper_pit_hex", "scorpion_ember_hex", "spec_anodized_hex_fade"),
    "diamond_mesh": ("spec_shadow_diamond_mesh", "spec_expanded_metal"),
    "talavera_rosette": ("spec_talavera_tile_riot",),
    "branching_vein": ("spec_green_plasma_vein", "root_doctor_copper", "bonsai_drift_circuit"),
    "fracture_net": ("spec_neon_fracture_net", "crackle_network", "voronoi_fracture", "spec_stress_fractures", "kintsugi_rift", "spec_abalone_crack_inlay"),
    "checker_cloth": ("spec_pink_checker_carbon", "checker_flag_subtle"),
    "herringbone": ("spec_red_herringbone_heat",),
    "chain_link": ("spec_chrome_oval_chain",),
    "tile_grid": ("spec_terracotta_ceramic_grid", "spec_architectural_grid"),
    "script_loop": ("spec_tokyo_script_textile", "bayou_smoke_script"),
    "pixel_confetti": ("spec_lime_pixel_confetti",),
    "floral_petal": ("spec_psychedelic_floral_spin", "sakura_static"),
    "facet_shatter": ("spec_ice_facet_shatter", "spec_blue_polygon_shatter", "prismatic_shatter"),
    "banded_rows": ("banded_rows", "gradient_bands", "spec_lfr_corridor_sheen"),
    "panel_zones": ("panel_zones", "cc_panel_fade"),
    "pebble": ("pebble_grain", "edm_dimple", "spec_hammered_dimple", "spec_ceramic_brake_sinter"),
    "water_wave": ("wave_ripple", "wave_bands", "seigaiha_chrome"),
    "galaxy_spiral": ("galaxy_swirl",),
    "lava_crack": ("lava_crack", "spec_mud_crackle_dried"),
    "diffraction_lines": ("spec_diffraction_grating_cd", "holo_prism_shift", "spec_chromatic_aberration"),
    "sand_grain": ("metallic_sand", "spec_sandblast_strip", "spec_sandblasted_mask_edge"),
    "flake_field": ("holographic_flake", "stardust_fine", "pearl_micro", "gold_flake", "spec_chameleon_flake", "spec_lfr_sparkler_embers"),
    "brushed_grain": ("brushed_diagonal", "brushed_cross", "brushed_linear_cool", "spec_anodized_texture", "spec_lfr_anisotropic_drift"),
    "rune_field": ("brushed_sparkle",),
    "razor_wire": ("sparkle_shattered",),
    "guilloche": ("guilloche_waves", "guilloche_moire_eng", "spec_guilloche_watch_dial"),
    "sunray": ("guilloche_sunray", "spec_anisotropic_radial", "rising_sun_prismwave"),
    "knurl": ("knurl_diamond", "spec_knurled_socket_grip"),
    "forged_chip": ("spec_carbon_forged", "spec_fiberglass_chopped"),
    "wet_weave": ("spec_carbon_wet_layup", "spec_prepreg_resin_bleed"),
    "kevlar_weave": ("spec_kevlar_weave", "spec_kevlar_blue_hybrid"),
    "perforated_mesh": ("spec_mesh_perforated", "spec_retroreflective"),
    "clearcoat_pool": ("cc_panel_pool", "cc_wet_zone", "spec_liquid_metal"),
    "halo_ring": ("cc_overspray_halo", "spec_fuel_stain_evap_ring"),
    "corrosion": ("spec_galvanic_corrosion", "salt_spray_corrosion", "swamp_charm_patina"),
    "brick_mortar": ("spec_brick_mortar", "crypt_brick"),
    "snake_scale": ("spec_snake_scales", "snake_scale_diamond"),
    "fish_scale": ("spec_fish_scales", "spec_titanium_heat_fishscale"),
    "topographic": ("spec_terrain_erosion", "spec_lfr_canyon_bevel"),
    "soft_gradient": ("spec_fresnel_gradient", "spec_exhaust_soot_gradient"),
    "iridescent_film": ("spec_iridescent_film", "spec_pvd_coating", "heat_discoloration", "anodized_rainbow"),
    "laser_etch": ("spec_laser_etched", "spec_laser_etched_microbar", "spec_waterjet_cut_edge"),
    "vinyl_stretch": ("vinyl_stretched",),
    "nacre_inlay": ("mother_of_pearl_inlay",),
    "dew_droplet": ("morning_dew_fog", "spec_rain_bead_aero"),
    "engine_turn": ("airbrush_gradient_bloom",),
    "halftone": ("halftone_print",),
    "ember": ("ember_field", "spec_burnt_clutch_dust"),
    "pangolin_shield": ("pangolin_armor",),
    "cobra_coil": ("king_cobra_coil", "spec_tar_snake_sealant"),
    "spider_web": ("widow_web_venom",),
    "fang_slash": ("tiger_fang_fracture", "sharkbite_riptide"),
    "hornet_swarm": ("hornet_swarm_static",),
    "croc_scute": ("croc_delta_armor", "alligator_hide", "spec_alligator_scute_plate"),
    "claw_marks": ("panther_shadow_claw",),
    "piranha_school": ("piranha_frenzy_current",),
    "jellyfish": ("jellyshock_drift",),
    "burlap": ("bayou_hex_burlap", "mojo_bag_grain"),
    "pins_thread": ("pins_and_thread",),
    "rust_nail": ("coffin_nail_rust",),
    "hanging_moss": ("spanish_moss_static",),
    "shogun_scale": ("shogun_scale_brocade",),
    "lantern_filigree": ("kyoto_lantern_filigree",),
    "fuji_crest": ("fuji_frost_crest",),
    "shark_denticle": ("shark_denticle", "spec_sharkskin_riblet"),
    "jaguar_rosette": ("jaguar_rosette",),
    "dragon_scale": ("dragon_scale_macro",),
    "feather": ("raptor_feather", "spec_ice_frost_feather"),
    "weld_bead": ("spec_weld_stack_rainbow",),
    "bolt_circle": ("spec_beadlock_bolt_circle",),
    "louver_slot": ("spec_louvered_aluminum_slot",),
    "tow_ribbon": ("spec_carbon_tow_spread",),
    "honeycomb_core": ("spec_nomex_honeycomb_core",),
    "braided_sleeve": ("spec_braided_hose_sleeve", "spec_rubber_tire_cord"),
    "mantis_shell": ("spec_mantis_shrimp_shell",),
    "armadillo_band": ("spec_armadillo_band_armor",),
    "flame_tongue": ("spec_flame_lapped_clearcoat", "spec_lfr_torch_flicker"),
    "clay_roost": ("spec_red_clay_roost",),
    "polish_swirl": ("spec_polished_swirl_compound",),
    "starfield": ("spec_lfr_starfield_scatter",),
    "firework": ("spec_lfr_firework_radial",),
    "eagle_brocade": ("spec_lfr_brocade_relief",),
    "liberty_prism": ("spec_lfr_liberty_colorflip",),
}


_ARCHETYPE_BY_ID: dict[str, str] = {}
for _archetype, _ids in _GROUPS.items():
    for _pid in _ids:
        if _pid in _ARCHETYPE_BY_ID:
            raise RuntimeError(f"duplicate semantic overlay assignment: {_pid}")
        _ARCHETYPE_BY_ID[_pid] = _archetype


_PARTICULATE_ARCHETYPES = frozenset({
    "pixel_confetti", "sand_grain", "flake_field", "forged_chip", "pebble",
    "ember", "clay_roost", "starfield", "firework",
})

_TEXTURED_SURFACE_ARCHETYPES = frozenset({
    "brushed_grain", "corrosion", "lava_crack", "burn_hole_mesh",
    "wet_weave", "burlap", "rust_nail", "hanging_moss", "polish_swirl",
})


def semantic_archetype(pid: str) -> str | None:
    """Return the explicit visible-subject archetype, never a hash fallback."""
    return _ARCHETYPE_BY_ID.get(str(pid))


def semantic_texture_policy(pid: str) -> str | None:
    """Declare whether visible loose texture is meaningful for this subject.

    ``clean`` is deliberately the default. It prevents quality metrics from
    reintroducing catalog-wide grain or confetti over named geometry.
    """
    kind = semantic_archetype(pid)
    if kind is None:
        return None
    if kind in _PARTICULATE_ARCHETYPES:
        return "particulate"
    if kind in _TEXTURED_SURFACE_ARCHETYPES:
        return "surface"
    return "clean"


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float32)
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < 1e-7:
        return np.full_like(a, .5, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _rotate(x: np.ndarray, y: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray]:
    ca, sa = math.cos(angle), math.sin(angle)
    return x * ca + y * sa, -x * sa + y * ca


def _line(a: np.ndarray, period: float, width: float = .1) -> np.ndarray:
    p = np.mod(a / max(period, .5), 1.0)
    d = np.minimum(p, 1.0 - p)
    return np.clip(1.0 - d / max(width, .012), 0.0, 1.0).astype(np.float32)


def _hash(x: np.ndarray, y: np.ndarray, key: int) -> np.ndarray:
    phase = float(key & 65535) * .000137
    return np.mod(np.sin(x * 12.9898 + y * 78.233 + phase) * 43758.5453, 1.0).astype(np.float32)


def _noise(h: int, w: int, key: int, cell: int = 20) -> np.ndarray:
    rng = np.random.default_rng(key & 0xFFFFFFFF)
    gh, gw = max(4, h // max(cell, 3)) + 2, max(4, w // max(cell, 3)) + 2
    return cv2.resize(rng.random((gh, gw), dtype=np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _dots(x: np.ndarray, y: np.ndarray, px: float, py: float, radius: float,
          stagger: bool = False) -> np.ndarray:
    row = np.floor(y / max(py, 1.0))
    shift = np.mod(row, 2.0) * px * .5 if stagger else 0.0
    dx = np.mod(x + shift + px * .5, max(px, 1.0)) - px * .5
    dy = np.mod(y + py * .5, max(py, 1.0)) - py * .5
    return np.clip(1.0 - np.hypot(dx, dy) / max(radius, .6), 0.0, 1.0).astype(np.float32)


def _units(x: np.ndarray, y: np.ndarray, feature: float) -> float:
    scale = max(x.shape[1], y.shape[0]) / 2048.0
    return float(np.clip(feature, max(.72, 8.0 * scale), max(1.35, 16.0 * scale)))


def _brick(x: np.ndarray, y: np.ndarray, s: float, key: int, crypt: bool) -> np.ndarray:
    bh, bw = s, s * 2.0
    row = np.floor(y / bh)
    xx = np.mod(x + np.mod(row, 2.0) * bw * .5, bw)
    yy = np.mod(y, bh)
    mortar = np.maximum(np.exp(-np.minimum(xx, bw - xx) / max(s * .08, .24)),
                        np.exp(-np.minimum(yy, bh - yy) / max(s * .08, .24)))
    shade = _hash(np.floor((x + np.mod(row, 2.0) * bw * .5) / bw), row, key)
    if crypt:
        chips = (_hash(np.floor(x / max(s * .28, .8)), np.floor(y / max(s * .28, .8)), key + 7) > .91)
        mortar = np.maximum(mortar, chips.astype(np.float32) * .8)
    return _norm(mortar * .72 + shade * .28)


def _checker(x: np.ndarray, y: np.ndarray, s: float, key: int, waving: bool) -> np.ndarray:
    warp = np.sin(y / max(s * 2.4, 1.0)) * s * .25 if waving else 0.0
    ix, iy = np.floor((x + warp) / s), np.floor(y / s)
    checks = np.mod(ix + iy, 2.0)
    seams = np.maximum(_line(x + warp, s, .045), _line(y, s, .045))
    return _norm(checks * .82 + seams * .18)


def _fish_scale(x: np.ndarray, y: np.ndarray, s: float, key: int) -> np.ndarray:
    rh, rw = s * .72, s * 1.45
    row = np.floor(y / rh)
    dx = np.mod(x + np.mod(row, 2.0) * rw * .5 + rw * .5, rw) - rw * .5
    dy = np.mod(y, rh)
    r = np.sqrt((dx / (rw * .52)) ** 2 + (dy / (rh * .92)) ** 2)
    scallop = np.exp(-np.abs(r - 1.0) * 15.0)
    inner = np.clip(1.0 - r, 0.0, 1.0)
    return _norm(scallop * .78 + inner * .22)


def _snake_scale(x: np.ndarray, y: np.ndarray, s: float, key: int) -> np.ndarray:
    cw, ch = s * 1.35, s * 1.6
    row = np.floor(y / ch)
    dx = np.abs(np.mod(x + np.mod(row, 2.0) * cw * .5 + cw * .5, cw) - cw * .5) / (cw * .5)
    dy = np.abs(np.mod(y + ch * .5, ch) - ch * .5) / (ch * .5)
    diamond = dx + dy
    rim = np.exp(-np.abs(diamond - .82) * 15.0)
    keel = np.exp(-dx * 8.0) * (diamond < .82)
    return _norm(rim * .74 + keel * .26)


def _scute(x: np.ndarray, y: np.ndarray, s: float, key: int) -> np.ndarray:
    cw, ch = s * 1.65, s * 1.1
    row, col = np.floor(y / ch), np.floor(x / cw)
    jitter = (_hash(col, row, key) - .5) * s * .20
    xx = np.mod(x + np.mod(row, 2.0) * cw * .36 + jitter, cw)
    yy = np.mod(y, ch)
    edge = np.maximum(np.exp(-np.minimum(xx, cw - xx) / max(s * .09, .25)),
                      np.exp(-np.minimum(yy, ch - yy) / max(s * .10, .25)))
    boss = _dots(x + s * .2, y, cw, ch, s * .27, True)
    return _norm(edge * .72 + boss * .28)


def _hex(x: np.ndarray, y: np.ndarray, s: float) -> np.ndarray:
    a = _line(x, s * 1.72, .075)
    b = _line(x * .5 + y * .8660254, s * 1.72, .075)
    c = _line(x * .5 - y * .8660254, s * 1.72, .075)
    return _norm(np.maximum(np.maximum(a, b), c))


def _petals(x: np.ndarray, y: np.ndarray, s: float, key: int, count: int = 5) -> np.ndarray:
    cell = s * 2.0
    dx = np.mod(x + cell * .5, cell) - cell * .5
    dy = np.mod(y + cell * .5, cell) - cell * .5
    r, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    petal_r = s * (.48 + .24 * np.cos(th * count))
    rim = np.exp(-np.abs(r - petal_r) / max(s * .08, .25))
    center = np.exp(-r / max(s * .20, .45))
    return _norm(rim * .76 + center * .42)


def _fracture(x: np.ndarray, y: np.ndarray, s: float, key: int, lava: bool = False) -> np.ndarray:
    n = _noise(y.shape[0], x.shape[1], key + 17, max(5, int(s * 2.5))) - .5
    fault = np.sin((x + n * s * 2.5) / max(s, .7) * 2.1) + np.sin((y - n * s * 1.8) / max(s, .7) * 2.7)
    crack = np.exp(-np.abs(fault) * (4.4 if lava else 3.5))
    branch = _line(x * .72 - y * .31 + n * s * 4.0, s * 3.0, .045)
    return _norm(crack * .78 + branch * .42)


def _weave(x: np.ndarray, y: np.ndarray, s: float, key: int, kind: str) -> np.ndarray:
    u, v = _rotate(x, y, math.pi * .25)
    if kind == "tow_ribbon":
        ribbon = _line(u, s * 1.8, .28)
        filaments = _line(u, max(s * .20, .65), .055)
        cross = _line(v, s * 3.0, .045)
        return _norm(ribbon * .42 + filaments * .44 + cross * .14)
    if kind == "braided_sleeve":
        a, b = _line(u, s * .78, .16), _line(v, s * .78, .16)
        nodes = np.minimum(1.0, a * b * 2.2)
        return _norm(a * .42 + b * .42 + nodes * .35)
    if kind == "burlap":
        a, b = _line(x, s * .55, .18), _line(y, s * .62, .18)
        gaps = _hash(np.floor(x / s), np.floor(y / s), key)
        return _norm((a + b) * (.72 + gaps * .28))
    a, b = _line(u, s * .72, .15), _line(v, s * .72, .15)
    over = np.mod(np.floor(u / max(s * .72, .7)) + np.floor(v / max(s * .72, .7)), 2.0)
    return _norm(a * (.58 + over * .34) + b * (1.0 - over * .26))


def _motif_field(kind: str, x: np.ndarray, y: np.ndarray, s: float, angle: float,
                 key: int, variant: int) -> np.ndarray:
    u, v = _rotate(x, y, angle)
    h, w = y.shape[0], x.shape[1]
    noise = _noise(h, w, key + 31, max(5, int(s * 2.4)))

    if kind == "brick_mortar": return _brick(x, y, s, key, False)
    if kind == "checker_cloth": return _checker(x, y, s, key, "subtle" in str(key))
    if kind == "fish_scale": return _fish_scale(x, y, s, key)
    if kind == "snake_scale": return _snake_scale(x, y, s, key)
    if kind == "croc_scute": return _scute(x, y, s, key)
    if kind == "hex_cell" or kind == "honeycomb_core": return _hex(x, y, s)
    if kind == "circuit_trace":
        gx, gy = _line(u, s * 1.6, .055), _line(v, s * 1.9, .055)
        gate = _hash(np.floor(u / (s * 1.6)), np.floor(v / (s * 1.9)), key)
        traces = gx * (gate > .43) + gy * (gate <= .57)
        pads = _dots(u, v, s * 2.4, s * 2.2, s * .16, True)
        return _norm(traces * .76 + pads * .72)
    if kind == "burn_hole_mesh":
        mesh = _hex(x, y, s)
        outer = _dots(x, y, s * 1.9, s * 1.7, s * .56, True)
        inner = _dots(x, y, s * 1.9, s * 1.7, s * .37, True)
        char = np.clip(outer - inner * .96, 0.0, 1.0)
        return _norm(char * .78 + mesh * (1.0 - inner) * .42)
    if kind == "branching_vein":
        warp = (noise - .5) * s * 2.8
        trunk = _line(u + warp, s * 2.3, .045)
        branch_a = _line(u * .58 + v * .42 + warp * .7, s * 2.3, .035)
        branch_b = _line(u * .61 - v * .37 - warp * .6, s * 2.3, .035)
        return _norm(trunk * .62 + branch_a * .48 + branch_b * .48)
    if kind == "facet_shatter":
        a = _line(u, s * 1.25, .045)
        b = _line(u * .5 + v * .866, s * 1.25, .045)
        c = _line(u * .5 - v * .866, s * 1.25, .045)
        cells = _hash(np.floor((u + v) / s), np.floor((u - v) / s), key)
        return _norm(np.maximum.reduce([a, b, c]) * .70 + cells * .30)
    if kind == "chain_link":
        cell = s * 1.8
        dx = np.mod(x + cell * .5, cell) - cell * .5
        dy = np.mod(y + cell * .5, cell) - cell * .5
        row = np.mod(np.floor(y / cell), 2.0)
        rx = np.where(row > .5, s * .38, s * .62)
        ry = np.where(row > .5, s * .62, s * .38)
        oval = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
        ring = np.exp(-np.abs(oval - 1.0) * 13.0)
        bridge = _line(x + y, cell, .035)
        return _norm(ring * .82 + bridge * .25)
    if kind == "floral_petal": return _petals(x, y, s, key, 5)
    if kind == "talavera_rosette": return _norm(_petals(x, y, s, key, 6) + _hex(x, y, s) * .25)
    if kind in ("fracture_net", "lava_crack"): return _fracture(x, y, s, key, kind == "lava_crack")
    if kind in ("carbon_mesh", "kevlar_weave", "wet_weave", "tow_ribbon", "braided_sleeve", "burlap"):
        return _weave(x, y, s, key, kind)
    if kind == "houndstooth":
        ix, iy = np.floor(u / s), np.floor(v / s); lx, ly = np.mod(u, s) / s, np.mod(v, s) / s
        parity = np.mod(ix + iy, 2.0)
        return _norm((((lx + ly * .62) > (.70 + parity * .10)) | ((lx < .25) & (ly > .48) & (parity < .5))).astype(np.float32))
    if kind in ("chevron", "herringbone"):
        fold = np.abs(np.mod(u, s * 2.0) - s)
        phase = v + fold * (.82 if kind == "chevron" else .48)
        bands = _line(phase, s * (1.25 if kind == "chevron" else .72), .18)
        return _norm(bands + _line(phase + s * .25, s * 1.25, .045) * .38)
    if kind in ("cross_lattice", "diamond_mesh", "knurl"):
        a, b = _line(u + v, s * 1.25, .09), _line(u - v, s * 1.25, .09)
        if kind == "diamond_mesh": return _norm(np.maximum(a, b))
        return _norm(a * .45 + b * .45 + np.minimum(1.0, a * b * 2.4) * .38)
    if kind == "tile_grid": return _norm(np.maximum(_line(x, s * 1.8, .07), _line(y, s * 1.8, .07)))
    if kind == "panel_zones": return _norm(np.maximum(_line(x, s * 2.0, .055), _line(y, s * 1.5, .055)) + _dots(x, y, s * 2.0, s * 1.5, s * .12) * .5)
    if kind == "banded_rows": return _norm(_line(v, s * 1.25, .22) + _line(v + s * .28, s * 1.25, .045) * .5)
    if kind == "pixel_confetti":
        ix, iy = np.floor(x / max(s * .38, .75)), np.floor(y / max(s * .38, .75)); r = _hash(ix, iy, key)
        return _norm((r > .62).astype(np.float32) * (.35 + r * .65))
    if kind == "halftone":
        cell = s * .75; ix, iy = np.floor(x / cell), np.floor(y / cell); radius = s * (.10 + .24 * (.5 + .5 * np.sin(ix * .31 + iy * .21)))
        dx = np.mod(x + cell * .5, cell) - cell * .5; dy = np.mod(y + cell * .5, cell) - cell * .5
        return _norm(np.clip(1.0 - np.hypot(dx, dy) / np.maximum(radius, .25), 0.0, 1.0))
    if kind in ("pebble", "perforated_mesh"):
        outer = _dots(x, y, s * 1.3, s * 1.15, s * (.43 if kind == "pebble" else .34), True)
        inner = _dots(x, y, s * 1.3, s * 1.15, s * .20, True)
        return _norm((outer - inner * .72) + inner * (.3 if kind == "pebble" else .05))
    if kind == "water_wave" or kind == "marble_vein":
        wave = np.sin((v + np.sin(u / max(s * 1.8, .8)) * s * .65 + (noise - .5) * s * 2.2) / max(s * .62, .55) * _TAU)
        return _norm(wave + (noise - .5) * (.45 if kind == "marble_vein" else .18))
    if kind == "galaxy_spiral":
        cell = s * 2.0; dx = np.mod(x + cell * .5, cell) - cell * .5; dy = np.mod(y + cell * .5, cell) - cell * .5
        r, th = np.hypot(dx, dy), np.arctan2(dy, dx); arms = np.cos(th * 2.0 + r / max(s * .18, .35))
        return _norm(arms * np.exp(-r / max(s, .7)) + _dots(x, y, s * .9, s * 1.1, s * .10) * .6)
    if kind in ("diffraction_lines", "brushed_grain"):
        fine = _line(u + (noise - .5) * s * .8, s * (.32 if kind == "diffraction_lines" else .22), .055)
        sweep = _line(u * .24 + v * .06, s * 2.0, .12)
        return _norm(fine * .70 + sweep * .30)
    if kind == "sand_grain" or kind == "flake_field" or kind == "ember" or kind == "starfield":
        q = max(s * (.18 if kind != "starfield" else .30), .7); r = _hash(np.floor(x / q), np.floor(y / q), key)
        cut = {"sand_grain":.55,"flake_field":.70,"ember":.82,"starfield":.90}[kind]
        return _norm(np.clip((r - cut) / max(1.0 - cut, .01), 0.0, 1.0) + noise * .10)
    if kind == "rune_field":
        cell = s * 1.6; lx=np.mod(x,cell)/cell; ly=np.mod(y,cell)/cell; rid=_hash(np.floor(x/cell),np.floor(y/cell),key)
        stem=np.exp(-np.abs(lx-.48)/.055); arm=np.exp(-np.abs(ly-(.25+lx*.45))/.06); gate=((ly>.15)&(ly<.85)&(rid>.30)).astype(np.float32)
        return _norm((stem+arm)*gate)
    if kind == "razor_wire":
        coil = _line(v + np.sin(u / max(s, .7) * _TAU) * s * .45, s * 1.6, .06)
        barb = _line(u + v * .42, s * .72, .045) * (_line(v, s * 1.6, .12) > .35)
        return _norm(coil * .76 + barb * .52)
    if kind in ("guilloche", "mandala_sigil", "engine_turn"):
        cell=s*2.0;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        rose=np.sin(r/max(s*.20,.35)*_TAU+np.sin(th*(5+variant))*2.4)
        rings=_line(r,s*.42,.07);return _norm(rose*.62+rings*.38)
    if kind in ("sunray", "firework", "liberty_prism"):
        cell=s*2.0;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        rays=_line(th*s*(5+variant),s,.065);rings=_line(r,s*.48,.07)
        return _norm(rays*.72+rings*.28)
    if kind == "forged_chip":
        q=max(s*.35,.8);r=_hash(np.floor(x/q),np.floor(y/q),key); shard=(r>.68).astype(np.float32); slash=_line(u+v*.25,s*.9,.05)
        return _norm(shard*(.55+.45*r)+slash*shard*.45)
    if kind in ("clearcoat_pool", "iridescent_film", "soft_gradient"):
        flow=np.sin((u+(noise-.5)*s*4.0)/max(s*.8,.6)*_TAU)+np.cos((v-(noise-.5)*s*3.0)/max(s*1.1,.7)*_TAU)
        return _norm(flow*.45+noise*.55)
    if kind == "halo_ring" or kind == "dew_droplet":
        outer=_dots(x,y,s*1.8,s*1.7,s*.65,True);inner=_dots(x,y,s*1.8,s*1.7,s*.42,True)
        return _norm(np.clip(outer-inner*.94,0,1)*.72+inner*.22)
    if kind == "corrosion":
        pits=(_hash(np.floor(x/max(s*.25,.7)),np.floor(y/max(s*.25,.7)),key)>.72).astype(np.float32)
        islands=np.clip((noise-.48)*3.2,0,1);return _norm(islands*.62+pits*.48)
    if kind == "topographic": return _norm(_line(noise*s*5.0,s*.42,.08)+_line(noise*s*5.0+s*.18,s*.42,.035)*.4)
    if kind == "laser_etch": return _norm(_line(u,s*.42,.055)*.65+_line(v,s*.75,.04)*.25+_dots(x,y,s*1.2,s*1.1,s*.10)*.45)
    if kind == "vinyl_stretch": return _norm(_line(u+(noise-.5)*s*2.2,s*.58,.08)*.62+noise*.38)
    if kind == "nacre_inlay": return _norm(_fracture(x,y,s,key)*.52+_petals(x,y,s,key,6)*.30+noise*.18)
    if kind == "pangolin_shield" or kind == "dragon_scale" or kind == "shogun_scale":
        cw,ch=s*1.35,s*1.25;row=np.floor(y/ch);dx=np.abs(np.mod(x+np.mod(row,2)*cw*.5+cw*.5,cw)-cw*.5)/(cw*.5);dy=np.mod(y,ch)/ch
        shield=dx+np.abs(dy-.35)*1.15;rim=np.exp(-np.abs(shield-.82)*13.0);spine=np.exp(-dx*7.0)*(dy<.82)
        return _norm(rim*.72+spine*.28)
    if kind == "cobra_coil":
        coil=_line(v+np.sin(u/max(s*1.3,.7)*_TAU)*s*.48,s*1.45,.12);scale=_snake_scale(x,y,s,key)
        return _norm(coil*.70+scale*.30)
    if kind == "spider_web":
        cell=s*2.0;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        return _norm(_line(th*s*5.0,s,.055)*.58+_line(r,s*.38,.07)*.58)
    if kind == "fang_slash":
        tri=np.abs(np.mod(u,s*1.35)-s*.675);slash=np.clip(1.0-(tri+np.mod(v,s*1.5)*.55)/max(s*.72,.6),0,1)
        return _norm(slash+_fracture(x,y,s,key)*.24)
    if kind == "hornet_swarm" or kind == "piranha_school":
        cell=s*1.55;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5
        body=np.exp(-((dx/(s*.42))**2+(dy/(s*.24))**2)*2.0);tail=np.clip(1.0-(np.abs(dx+s*.48)+np.abs(dy)*1.8)/max(s*.35,.4),0,1)
        stripe=_line(dx,s*.22,.08)*body;return _norm(body*.58+tail*.48+stripe*.30)
    if kind == "claw_marks":
        bend=np.sin(v/max(s*1.7,.7))*s*.32;marks=np.maximum.reduce([_line(u+bend+i*s*.32,s*2.0,.045) for i in (-1,0,1)])
        gate=(np.mod(v,s*2.1)<s*1.05).astype(np.float32);return _norm(marks*gate+_dots(x,y,s*2,s*2.1,s*.10)*.4)
    if kind == "jellyfish":
        cell=s*1.8;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;dome=np.exp(-np.abs(np.hypot(dx/(s*.55),dy/(s*.38))-1)*12)*(dy<0)
        tent=_line(dx+np.sin(dy/max(s*.35,.4))*s*.15,s*.33,.055)*(dy>=0);return _norm(dome*.72+tent*.52)
    if kind == "pins_thread":
        pins=_dots(x,y,s*1.5,s*1.4,s*.12,True);threads=np.maximum(_line(u+v*.42,s*1.5,.035),_line(u-v*.36,s*1.4,.035))
        return _norm(pins*.75+threads*.42)
    if kind == "rust_nail":
        shaft=_line(u,s*1.25,.075)*(np.mod(v,s*1.8)<s*1.2);head=_dots(u,v,s*1.25,s*1.8,s*.22);ring=np.clip(head-_dots(u,v,s*1.25,s*1.8,s*.12)*.88,0,1)
        slot=_line(u+v*.18,s*1.25,.035)*head;barb=_line(v-u*.28,s*1.8,.030)*shaft
        mini_head=_dots(u+s*.31,v+s*.44,s*.625,s*.90,s*.075,True);mini_shaft=_line(u+s*.31,s*.625,.030)*(np.mod(v+s*.44,s*.90)<s*.54)
        return _norm(shaft*.58+head*.26+ring*.52+slot*.38+barb*.26+mini_head*.46+mini_shaft*.32)
    if kind == "script_loop" or kind == "hanging_moss":
        loop=_line(u+np.sin(v/max(s*.65,.5))*s*.45,s*1.2,.055);drop=_line(v+np.sin(u/max(s*.8,.6))*s*.25,s*1.7,.05)
        return _norm(loop*.62+drop*(.46 if kind=="hanging_moss" else .28)+noise*.12)
    if kind == "lantern_filigree":
        outer=_dots(x,y,s*1.5,s*1.7,s*.52,True);inner=_dots(x,y,s*1.5,s*1.7,s*.32,True);bars=_line(x,s*1.5,.05)
        return _norm(np.clip(outer-inner*.9,0,1)*.70+bars*outer*.35)
    if kind == "fuji_crest":
        lx=np.mod(x,s*2)/ (s*2);ly=np.mod(y,s*1.4)/(s*1.4);mount=np.clip(1.0-np.abs(lx-.5)*2.0-ly,0,1);snow=(ly<.28+np.abs(lx-.5)*.3)*mount
        return _norm(mount*.48+snow*.62)
    if kind == "shark_denticle":
        cw,ch=s*1.2,s*.9;row=np.floor(y/ch);dx=np.abs(np.mod(x+np.mod(row,2)*cw*.5+cw*.5,cw)-cw*.5)/(cw*.5);dy=np.mod(y,ch)/ch
        tooth=np.clip(1.0-(dx+dy*.82),0,1);ridge=np.exp(-dx*8)*tooth;return _norm(tooth*.62+ridge*.42)
    if kind == "jaguar_rosette":
        outer=_dots(x,y,s*1.8,s*1.65,s*.62,True);inner=_dots(x,y,s*1.8,s*1.65,s*.35,True);spots=_dots(x+s*.48,y+s*.31,s*1.8,s*1.65,s*.12,True)
        return _norm(np.clip(outer-inner*.94,0,1)*.75+spots*.55)
    if kind == "feather" or kind == "eagle_brocade":
        shaft=_line(u,s*1.45,.045);barb1=_line(u+v*.55,s*.72,.045);barb2=_line(u-v*.55,s*.72,.045);gate=(np.mod(v,s*1.5)<s*1.1)
        return _norm(shaft*gate*.68+(barb1+barb2)*gate*.36)
    if kind == "weld_bead":
        band=np.mod(v,s*1.8)-s*.9;beadx=np.mod(u,s*.55)-s*.275;bead=np.exp(-((beadx/(s*.24))**2+(band/(s*.42))**2)*2);toe=np.exp(-np.abs(np.abs(band)-s*.45)/max(s*.06,.2))
        return _norm(bead*.78+toe*.44)
    if kind == "bolt_circle":
        cell=s*2;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx);ring=_line(r,s*.58,.055);bolts=_line(th*s*5,s,.09)*(np.abs(r-s*.58)<s*.16)
        return _norm(ring*.58+bolts*.72)
    if kind == "louver_slot":
        row=np.floor(y/(s*.72));shift=np.mod(row,2)*s*.65;dx=np.abs(np.mod(x+shift,s*1.3)-s*.65);dy=np.abs(np.mod(y,s*.72)-s*.36);slot=np.clip(1.0-np.maximum(dx/(s*.52),dy/(s*.16)),0,1)
        return _norm(slot+_line(x+shift,s*1.3,.04)*.25)
    if kind == "mantis_shell": return _norm(_scute(x,y,s,key)*.58+_line(u+v*.3,s*.52,.07)*.42)
    if kind == "armadillo_band": return _norm(_line(y,s*.75,.20)*.62+_scute(x,y,s,key)*.38)
    if kind == "flame_tongue":
        phase=np.mod(y,s*1.6)/ (s*1.6);tongue=np.clip(1.0-(np.abs(np.mod(x+np.sin(y/max(s,.7))*s*.25,s*.9)-s*.45)/(s*.45)+phase*.85),0,1)
        return _norm(tongue)
    if kind == "clay_roost":
        drops=_dots(u,v,s*1.4,s*1.1,s*.22,True);trail=_line(u+v*.45,s*1.4,.04)*drops;return _norm(drops*.72+trail*.46)
    if kind == "polish_swirl":
        cell=s*2.4;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        sweep=_line(r+th*s*.16,s*.42,.055);cross=_line(r-th*s*.11,s*.66,.035)
        return _norm(sweep*.72+cross*.38)

    # Every explicit identity should land above.  This is a fail-visible field,
    # not a visually plausible fallback that could hide missing semantics.
    return np.zeros((h, w), dtype=np.float32)


def _identity_refinement(pid: str, field: np.ndarray, x: np.ndarray, y: np.ndarray,
                         s: float, angle: float, key: int) -> np.ndarray:
    """Give related named subjects coherent construction—not random uniqueness."""
    u, v = _rotate(x, y, angle)
    if pid == "spec_acid_carbon_mesh":
        return _norm(field * .58 + _fracture(x, y, s * .82, key + 73) * .42)
    if pid == "spec_carbon_weave":
        basket = np.maximum(_line(u, s * 1.55, .14), _line(v, s * 1.55, .14))
        return _norm(field * .58 + basket * .42)
    if pid == "spec_carbon_2x2_twill":
        twill = _line(u + v * .62, s * 1.42, .16)
        return _norm(field * .54 + twill * .46)
    if pid == "spec_carbon_3k_fine":
        filaments = np.maximum.reduce([_line(u + i * s * .10, s * .52, .035) for i in (-1, 0, 1)])
        return _norm(field * .48 + filaments * .52)
    if pid in ("spec_kevlar_weave", "spec_kevlar_blue_hybrid"):
        braid = np.maximum(_line(u + v, s * 1.08, .10), _line(u - v, s * 1.52, .065))
        return _norm(field * .55 + braid * .45)
    if pid == "spec_prepreg_resin_bleed":
        resin = _line(u + np.sin(v / max(s, .7)) * s * .42, s * 2.15, .19)
        return _norm(field * .58 + resin * .42)
    if pid == "wave_ripple":
        cell=s*2.35;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy)
        return _norm(_line(r,s*.38,.065)*.72+_line(r+s*.16,s*.76,.040)*.42)
    if pid == "wave_bands":
        swell=_line(v+np.sin(u/max(s*1.3,.7))*s*.42,s*1.10,.16);crest=_line(v+np.sin(u/max(s*1.3,.7))*s*.42+s*.24,s*1.10,.045)
        return _norm(swell*.68+crest*.52)
    if pid == "seigaiha_chrome":
        cell=s*1.75;row=np.floor(y/(cell*.52));dx=np.mod(x+np.mod(row,2)*cell*.5+cell*.5,cell)-cell*.5;dy=np.mod(y,cell*.52);r=np.hypot(dx,dy)
        return _norm(_line(r,s*.34,.060)*.62+_line(r+s*.16,s*.68,.045)*.56)
    if pid == "diamond_lattice":
        lattice=np.maximum(_line(u+v,s*1.45,.075),_line(u-v,s*1.45,.075));nodes=_dots(x,y,s*1.45,s*1.45,s*.13,True)
        return _norm(lattice*.66+nodes*.62)
    if pid == "spec_graphite_cross_lattice":
        major=np.maximum(_line(u+v,s*1.78,.12),_line(u-v,s*1.78,.12));minor=np.maximum(_line(u+v+s*.34,s*.89,.035),_line(u-v-s*.34,s*.89,.035))
        return _norm(major*.70+minor*.36)
    if pid == "spec_nomex_honeycomb_core":
        return _norm(_hex(x,y,s*1.18)*.68+_dots(x,y,s*1.02,s*.88,s*.12,True)*.54)
    if pid == "viper_pit_hex":
        diagonal=_line(u+v*.42,s*1.64,.065)
        return _norm(_hex(x,y,s*.92)*.68+diagonal*.44)
    if pid == "spec_anodized_hex_fade":
        broad=_line(u,s*2.1,.20)
        return _norm(_hex(x,y,s*1.08)*.72+broad*.30)
    if pid == "spec_terracotta_ceramic_grid":
        grout=np.maximum(_line(x,s*2.05,.10),_line(y,s*1.55,.10));inset=np.maximum(_line(x+s*.22,s*2.05,.035),_line(y+s*.18,s*1.55,.035))
        return _norm(grout*.72+inset*.34)
    if pid == "spec_architectural_grid":
        major=np.maximum(_line(x,s*2.4,.075),_line(y,s*2.4,.075));minor=np.maximum(_line(x+s*.6,s*.80,.028),_line(y+s*.6,s*.80,.028))
        return _norm(major*.76+minor*.32)
    if pid == "snake_scale_diamond":
        a=np.maximum(_line(u+v,s*1.55,.085),_line(u-v,s*1.55,.085));keel=_line(u,s*.78,.035)*(a<.4)
        return _norm(a*.78+keel*.32)
    if pid == "spec_flame_lapped_clearcoat":
        laps=_line(u+np.sin(v/max(s*.9,.7))*s*.46,s*1.38,.11);tips=_line(u-v*.42,s*.69,.045)
        return _norm(laps*.74+tips*.34)
    if pid == "spec_lfr_torch_flicker":
        tongues=np.clip(1.0-(np.abs(np.mod(x+np.sin(y/max(s,.7))*s*.28,s*.82)-s*.41)/(s*.41)+np.mod(y,s*1.7)/(s*1.7)*.9),0,1)
        return _norm(tongues)
    if pid == "crackle_network":
        return _norm(_fracture(x,y,s*.68,key+301,False))
    if pid == "voronoi_fracture":
        tri=np.maximum.reduce([_line(u,s*1.42,.045),_line(u*.5+v*.866,s*1.42,.045),_line(u*.5-v*.866,s*1.42,.045)])
        return _norm(tri)
    if pid == "spec_stress_fractures":
        primary=_line(u+(np.sin(v/max(s*1.2,.7))*s*.38),s*1.9,.045);branches=_line(u*.68+v*.32,s*1.9,.030)
        return _norm(primary*.74+branches*.46)
    if pid == "kintsugi_rift":
        vein=_line(u+(np.sin(v/max(s*1.4,.7))*s*.44),s*2.2,.14);rim=_line(u+(np.sin(v/max(s*1.4,.7))*s*.44)+s*.18,s*2.2,.035)
        return _norm(vein*.72+rim*.42)
    if pid == "spec_neon_fracture_net":
        net=np.maximum.reduce([_line(u,s*1.18,.055),_line(u*.5+v*.866,s*1.18,.055),_line(u*.5-v*.866,s*1.18,.055)])
        nodes=_dots(x,y,s*1.18,s*1.02,s*.10,True)
        return _norm(net*.70+nodes*.48)

    if pid == "guilloche_sunray":
        cell=s*2.8;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        return _norm(_line(th*s*8.0,s,.045)*.62+_line(r,s*.34,.045)*.48)
    if pid == "spec_anisotropic_radial":
        cell=s*3.1;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;th=np.arctan2(dy,dx)
        return _norm(_line(th*s*13.0,s,.032)*.78+_line(np.hypot(dx,dy),s*.88,.035)*.25)
    if pid == "rising_sun_prismwave":
        cell=s*3.0;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;th=np.arctan2(dy,dx)
        fan=_line(th*s*6.0,s,.075)*(dy<0);horizon=_line(dy,s*3.0,.055)
        return _norm(fan*.78+horizon*.48)
    if pid == "spec_lfr_liberty_colorflip":
        star = _petals(x, y, s * 1.25, key + 101, 5)
        facets = np.maximum(_line(u + v * .55, s * 1.45, .05), _line(u - v * .55, s * 1.45, .05))
        return _norm(star * .70 + facets * .38)
    if pid == "widow_web_venom":
        cell=s*3.2;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        spokes=_line(th*s*8.0,s,.04);spiral=_line(r+th*s*.12,s*.42,.055)
        return _norm(spokes*.58+spiral*.68)
    if pid == "spec_beadlock_bolt_circle":
        cell=s*2.6;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        ring=_line(r,s*.78,.045);bolts=_line(th*s*10.0,s,.06)*(np.abs(r-s*.78)<s*.18)
        return _norm(ring*.38+bolts*.92)

    if pid == "spec_black_emboss_mandala":
        return _norm(_petals(x, y, s * 1.25, key + 211, 8) * .78 + field * .22)
    if pid == "samhain_ritual":
        tri=np.maximum.reduce([_line(u,s*1.7,.045),_line(u+v*1.72,s*1.7,.045),_line(u-v*1.72,s*1.7,.045)])
        nodes=_dots(x,y,s*1.7,s*1.48,s*.12,True)
        return _norm(tri*.70+nodes*.52)
    if pid == "ouija_mystic":
        outer=_dots(x,y,s*2.0,s*1.35,s*.62,True);inner=_dots(x,y,s*2.0,s*1.35,s*.34,True);pupil=_dots(x+s*.26,y,s*2.0,s*1.35,s*.10,True)
        pointer=np.maximum(_line(u+v*.62,s*1.0,.045),_line(u-v*.62,s*1.0,.045));rail=_line(v,s*.68,.035)
        return _norm(np.clip(outer-inner*.90,0,1)*.58+pupil*.68+pointer*.34+rail*.24)
    if pid == "candle_wax_veve":
        loops=_line(u+np.sin(v/max(s,.7))*s*.38,s*1.25,.065);drops=_dots(x,y+s*.31,s*1.25,s*1.72,s*.13,True)
        return _norm(loops*.70+drops*.58)
    if pid == "midnight_gris_gris":
        cross=np.maximum(_line(u+v,s*1.18,.055),_line(u-v,s*1.18,.055));rings=_dots(x,y,s*1.75,s*1.75,s*.42,True)-_dots(x,y,s*1.75,s*1.75,s*.27,True)
        return _norm(cross*.62+np.clip(rings,0,1)*.52)
    if pid == "spec_guilloche_watch_dial":
        waves=_line(u+np.sin(v/max(s*.8,.7))*s*.55,s*.72,.045);cross=_line(v+np.sin(u/max(s*1.1,.7))*s*.28,s*1.35,.035)
        return _norm(waves*.72+cross*.44)
    if pid == "spec_lfr_brocade_relief":
        rosette=_petals(x,y,s*1.18,key+419,4);vine=np.maximum(_line(u+np.sin(v/max(s,.7))*s*.34,s*1.42,.045),_line(v+np.sin(u/max(s,.7))*s*.34,s*1.42,.045))
        crest=_dots(x,y,s*1.68,s*1.68,s*.13,True)
        return _norm(rosette*.58+vine*.46+crest*.42)

    if pid == "dragon_scale_macro":
        cw,ch=s*1.48,s*1.15;row=np.floor(y/ch);dx=np.abs(np.mod(x+np.mod(row,2)*cw*.5+cw*.5,cw)-cw*.5)/(cw*.5);dy=np.mod(y,ch)/ch
        shield=dx*.78+np.abs(dy-.38)*1.18;rim=np.exp(-np.abs(shield-.78)*8.0);ridge=np.exp(-dx*8.0)*(shield<.78)
        return _norm(rim*.72+ridge*.34)
    if pid == "spec_rain_bead_aero":
        bead=_dots(x,y,s*1.9,s*1.55,s*.38,True);tail=_line(x+y*.46,s*1.9,.045)*bead
        return _norm(bead*.72+tail*.52)
    if pid == "morning_dew_fog":
        large=_dots(x,y,s*2.2,s*1.8,s*.58,True);small=_dots(x+s*.62,y+s*.44,s*2.2,s*1.8,s*.16,True)
        return _norm(large*.62+small*.72)
    if pid == "spec_fuel_stain_evap_ring":
        outer=_dots(x,y,s*2.1,s*1.85,s*.72,True);inner=_dots(x,y,s*2.1,s*1.85,s*.49,True);gate=(_line(u+v*.2,s*.78,.14)>.25)
        return _norm(np.clip(outer-inner*.96,0,1)*gate)
    if pid == "spec_retroreflective":
        return _norm(_dots(x,y,s*.84,s*.74,s*.18,True))
    if pid == "spec_hammered_dimple":
        outer=_dots(x,y,s*1.55,s*1.35,s*.52,True);inner=_dots(x+s*.12,y-s*.10,s*1.55,s*1.35,s*.31,True)
        return _norm(outer*.52+inner*.58)
    if pid == "spec_ceramic_brake_sinter":
        coarse=_dots(x,y,s*1.42,s*1.25,s*.38,True);pores=_dots(x+s*.34,y+s*.27,s*.71,s*.62,s*.09,True)
        return _norm(coarse*.58+pores*.66)
    if pid == "spec_lfr_firework_radial":
        cell=s*2.05;dx=np.mod(x+cell*.5,cell)-cell*.5;dy=np.mod(y+cell*.5,cell)-cell*.5;r=np.hypot(dx,dy);th=np.arctan2(dy,dx)
        reach=s*(.58+.38*(.5+.5*np.cos(th*5.0)));spokes=_line(th*s*13.0,s,.045)*(r<reach)
        echo=_line((th+.11)*s*9.0,s,.035)*(r<s*.70);fronts=np.maximum(_line(r,s*.46,.045),_line(r+s*.15,s*.69,.035))
        return _norm(spokes*.66+echo*.42+fronts*.58)
    return field


def semantic_field(pid: str, x: np.ndarray, y: np.ndarray, feature: float,
                   angle: float, key: int, variant: int) -> np.ndarray | None:
    """Build the recognizable subject field for ``pid`` or return ``None``."""
    kind = semantic_archetype(pid)
    if kind is None:
        return None
    s = _units(x, y, feature)
    if kind == "brick_mortar":
        return _brick(x, y, s, key, pid == "crypt_brick")
    if kind == "checker_cloth":
        return _checker(x, y, s, key, pid == "checker_flag_subtle")
    field = _motif_field(kind, x, y, s, angle, key, variant)
    field = _identity_refinement(pid, field, x, y, s, angle, key)
    # Subject-specific secondary marks for the hardest owner-visible motifs.
    # These are semantic anatomy/construction, not generic noise decoration.
    if pid == "hornet_swarm_static":
        wings_a = _dots(x + s * .34, y + s * .20, s * 1.55, s * 1.55, s * .18, True)
        wings_b = _dots(x - s * .34, y + s * .20, s * 1.55, s * 1.55, s * .18, True)
        antenna = _line(x + y * .28, s * .78, .035)
        nest = _hex(x + s * .17, y, s * .62)
        field = _norm(field * .44 + wings_a * .22 + wings_b * .22 + antenna * .14 + nest * .28)
    elif pid == "spec_red_clay_roost":
        satellites = _dots(x + s * .42, y + s * .31, s * .74, s * .67, s * .10, True)
        streaks = _line(x + y * .55, s * .82, .04)
        field = _norm(field * .62 + satellites * .30 + streaks * .18)
    elif pid == "panther_shadow_claw":
        punctures = _dots(x + s * .24, y, s * 1.0, s * 1.05, s * .12, True)
        hairline = _line(x - y * .30, s * .68, .035)
        fur = _line(x + y * .18, s * .38, .045) + _line(x - y * .12, s * .57, .03)
        field = _norm(field * .45 + punctures * .25 + hairline * .18 + fur * .28)
    elif pid == "spec_mantis_shrimp_shell":
        eye_spots = _dots(x + s * .21, y + s * .18, s * .86, s * .78, s * .10, True)
        fan_ribs = _line(x * .62 + y * .78, s * .58, .045)
        chromatophores = _dots(x - s * .16, y + s * .11, s * .54, s * .49, s * .075, True)
        field = _norm(field * .46 + eye_spots * .25 + fan_ribs * .28 + chromatophores * .25)
    elif pid in ("diamond_lattice", "spec_graphite_cross_lattice"):
        nodes = _dots(x, y, s * 1.25, s * 1.25, s * .11, True)
        inner = _line(x + y, s * .62, .035) + _line(x - y, s * .62, .035)
        field = _norm(field * .60 + nodes * .32 + inner * .18)
    return field


__all__ = ["semantic_archetype", "semantic_field", "semantic_texture_policy"]
