"""
engine/pattern_expansion.py - Additional patterns (Decades, Flames, Music, Astro, Hero, Sports).

Design: Each expansion ID is built individually. No mapping to legacy IDs - each has its
own texture_fn and paint_fn implemented in engine/expansion_patterns.py (variant = pattern_id).
"""

import numpy as np

# -- IDs: each has a dedicated implementation in expansion_patterns --
NEW_PATTERN_IDS = [
    # ── FLAMES (10 all-new, unique texture+paint each) ─────────────────────────
    "flame_hotrod_classic",    # Traditional hot rod tongues from the left, tapering to pointed tips
    "flame_ghost",             # Ultra-thin see-through wisps - barely-there ghost flames
    "flame_blue_propane",      # Tight propane-torch blue-white cones from base edge
    "flame_tribal_knife",      # Razor-sharp angular tribal flame silhouettes
    "flame_hellfire_column",   # Vertical meandering hellfire columns, chaotic and wide
    "flame_inferno_wall",      # Full-canvas raging inferno - no surface uncovered
    "flame_pinstripe_outline", # Fine pinstripe outline flames, two-tone edge only
    "flame_ember_field",       # Floating ember sparks drifting upward, no tongue shape
    "flame_split_fishtail",    # Double fishtail split tongues, symmetrical, rearward motion
    "flame_smoke_fade",        # Flames dissolving upward into soft smoke haze
    # 50s
    "decade_50s_starburst", "decade_50s_bullet", "decade_50s_diner_curve", "decade_50s_tailfin", "decade_50s_boomerang",
    "decade_50s_scallop", "decade_50s_rocket", "decade_50s_classic_stripe", "decade_50s_diamond", "decade_50s_chrome_line",
    # 60s  (petal → woodstock, wide_stripe stays but distinct)
    "decade_60s_flower", "decade_60s_peace_curve", "decade_60s_mod_stripe", "decade_60s_opart_ray", "decade_60s_gogo_check",
    "decade_60s_lavalamp", "decade_60s_wide_stripe", "decade_60s_thin_stripe", "decade_60s_woodstock", "decade_60s_swirl",
    # 70s  (wide_stripe → patchwork)
    "decade_70s_disco", "decade_70s_patchwork", "decade_70s_bicentennial", "decade_70s_funk_zigzag", "decade_70s_shag",
    "decade_70s_studio54", "decade_70s_bell_flare", "decade_70s_earth_geo", "decade_70s_orange_curve", "decade_70s_sparkle",
    # 80s  (neon_grid → neon_hex, angle → my_little_friend, triangle → yo_joe, bolt → acid_washed)
    "decade_80s_neon_hex", "decade_80s_memphis", "decade_80s_my_little_friend", "decade_80s_synth_sun", "decade_80s_yo_joe",
    "decade_80s_outrun", "decade_80s_pixel", "decade_80s_acid_washed", "decade_80s_pastel_zig", "decade_80s_vapor",
    # 90s  (minimal_stripe → trolls, y2k fixed, bold_stripe → tama90s, indie → floppy_disk)
    "decade_90s_grunge", "decade_90s_trolls", "decade_90s_alt_cross", "decade_90s_geo_minimal", "decade_90s_rave_zig",
    "decade_90s_chrome_bubble", "decade_90s_y2k", "decade_90s_tama90s", "decade_90s_dot_matrix", "decade_90s_floppy_disk",
    # Music  (star_burst → blues, circle_ring → strat, slash_bold → the_artist, chain_heavy → smilevana, flame_ribbon → licked)
    "music_lightning_bolt", "music_wing_sweep", "music_script_curve", "music_skull_abstract", "music_arrow_bold",
    "music_blues", "music_strat", "music_the_artist", "music_smilevana", "music_licked",
    # Astro v2 (12 physics-based cosmic; replaces 7 astro + 12 zodiac)
    "pulsar_beacon", "event_horizon", "solar_corona", "nebula_pillars", "magnetar_field", "asteroid_belt",
    "gravitational_lens", "cosmic_web", "plasma_ejection", "dark_matter_halo", "quasar_jet", "supernova_remnant",
    # Hero
    "hero_crest_curve", "hero_scallop_edge", "hero_pointed_cowl",
    # Pop Culture & Sports removed per user direction - will be rebuilt as a separate section

    # ── MICRO SHIMMER PATTERNS (REBUILT) ─────────────────────────────────────
    "shimmer_quantum_shard",   # faceted shard interference with sharp color split
    "shimmer_prism_frost",     # crossed prism frost lines with cool crystalline lift
    "shimmer_velvet_static",   # matte velvet static with controlled micro-grain
    "shimmer_chrome_flux",     # directional chrome sweep with moving spec bands
    "shimmer_matte_halo",      # soft halo rings for matte-leaning shimmer depth
    "shimmer_oil_tension",     # thin-film tension waves with odd hue travel
    "shimmer_neon_weft",       # woven neon filaments with high-frequency crossings
    "shimmer_void_dust",       # dark field + sparse high-energy spark dust
    "shimmer_turbine_sheen",   # curved turbine blades with rotating sheen cues
    "shimmer_spectral_mesh",   # spectral mesh lattice with mixed chrome/matte behavior
]


# Astro v2 IDs (sourced from engine.expansions.astro_cosmic_v2, not expansion_patterns)
ASTRO_V2_IDS = [
    "pulsar_beacon", "event_horizon", "solar_corona", "nebula_pillars", "magnetar_field", "asteroid_belt",
    "gravitational_lens", "cosmic_web", "plasma_ejection", "dark_matter_halo", "quasar_jet", "supernova_remnant",
]


def _build_new_patterns():
    """Build NEW_PATTERNS: expansion IDs from expansion_patterns; astro v2 from engine.expansions.astro_cosmic_v2."""
    try:
        from engine.expansion_patterns import build_expansion_entries
        # Build entries for all IDs except astro v2 (they have no expansion_patterns variant)
        other_ids = [pid for pid in NEW_PATTERN_IDS if pid not in ASTRO_V2_IDS]
        out = build_expansion_entries(other_ids)
        # Merge astro v2 (scalar-bb wrapped in module)
        try:
            from engine.expansions.astro_cosmic_v2 import ASTRO_COSMIC_PATTERNS
            for pid, entry in ASTRO_COSMIC_PATTERNS.items():
                out[pid] = dict(entry)
        except Exception:
            pass
        return out
    except Exception as ex:
        # Fallback: generic no-op so registry load does not crash
        def _generic_texture(shape, mask, seed, sm):
            h, w = shape
            return {"pattern_val": np.full((h, w), 0.5, dtype=np.float32), "R_range": 0.0, "M_range": 0.0, "CC": None}

        def _generic_paint(paint, shape, mask, seed, pm, bb):
            return np.ascontiguousarray(paint[:, :, :3].astype(np.float32))

        generic = {"texture_fn": _generic_texture, "paint_fn": _generic_paint, "variable_cc": False, "desc": "Pattern (fallback)"}
        return {pid: dict(generic) for pid in NEW_PATTERN_IDS}


NEW_PATTERNS = _build_new_patterns()
