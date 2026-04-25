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

    # ── INTRICATE & ORNATE — Batch 1 (2026-03-28) ────────────────────────────
    "damascus_steel",       # Folded-metal layered bands with flowing distortion field
    "sacred_geometry",      # Flower of Life 3-wave hex interference rings
    "lace_filigree",        # Delicate interlaced openwork — orthogonal + diagonal grids
    "stained_glass",        # Voronoi cells with thick dark grout borders
    "brushed_metal_fine",   # Three-frequency directional micro-scratch brushing
    "carbon_3k_weave",      # 3K satin-braid diagonal carbon fiber variant
    "honeycomb_organic",    # Warped 3-wave hex — organic irregular honeycomb cells
    "baroque_scrollwork",   # Spiral+flourish S-curve ornate scrollwork
    "art_nouveau_vine",     # Sinuous vine stems with branching Art Nouveau tendrils
    "penrose_quasi",        # 5-fold quasicrystal — aperiodic Penrose-like tiling
    "topographic_dense",    # Dense contour lines over multi-scale noise height field
    "interference_rings",   # Newton's-ring multi-source radial interference bands
]


# Astro v2 IDs (sourced from engine.expansions.astro_cosmic_v2, not expansion_patterns)
ASTRO_V2_IDS = [
    "pulsar_beacon", "event_horizon", "solar_corona", "nebula_pillars", "magnetar_field", "asteroid_belt",
    "gravitational_lens", "cosmic_web", "plasma_ejection", "dark_matter_halo", "quasar_jet", "supernova_remnant",
]


def _spb_hash_seed(text):
    h = 2166136261
    for ch in str(text):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _spb_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _spb_micro_field(shape, seed, family):
    h, w = shape[:2] if len(shape) > 2 else shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s = int(seed) + int(family) * 0.019
    a = np.sin(xx * (0.67 + (family % 9) * 0.021) + yy * 0.18 + s)
    b = np.sin(yy * (0.89 + (family % 7) * 0.025) - xx * 0.29 + s * 1.3)
    c = np.sin((xx - yy) * (1.47 + (family % 5) * 0.031) + s * 2.1)
    fine = _spb_norm01(a * 0.44 + b * 0.34 + c * 0.22)
    sparkle = (fine > (0.91 - min(0.05, (family % 8) * 0.006))).astype(np.float32)
    return fine, sparkle


def _spb_decade_signature(pattern_id, shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    family = _spb_hash_seed(pattern_id)
    phase = (family % 360) * np.pi / 180.0
    sig = np.zeros((h, w), dtype=np.float32)
    if "50s" in pattern_id:
        r = np.hypot(xx - w * 0.28, yy - h * 0.38)
        theta = np.arctan2(yy - h * 0.38, xx - w * 0.28)
        star = (np.sin(theta * 12.0 + phase) * 0.5 + 0.5) * np.clip(1.0 - r / max(h, w), 0, 1)
        boomer = np.sin(xx * 0.055 + np.sin(yy * 0.030 + phase) * 2.6) * 0.5 + 0.5
        chrome = np.sin((xx + yy) * 0.095 + phase) * 0.5 + 0.5
        sig = np.clip(star * 0.45 + boomer * 0.35 + chrome * 0.20, 0, 1)
    elif "60s" in pattern_id:
        r = np.hypot(xx - w * 0.5, yy - h * 0.5)
        theta = np.arctan2(yy - h * 0.5, xx - w * 0.5)
        tie = np.sin(r * 0.075 + theta * 5.0 + phase) * 0.5 + 0.5
        op = np.sin((xx - w * 0.5) * 0.075 + np.sin(yy * 0.045) * 3.0) * 0.5 + 0.5
        flower = np.sin(theta * 9.0 + np.sin(r * 0.055)) * 0.5 + 0.5
        sig = np.clip(tie * 0.45 + op * 0.30 + flower * 0.25, 0, 1)
    elif "70s" in pattern_id:
        disco = _spb_norm01(np.sin(xx * 0.16 + phase) * np.sin(yy * 0.13 - phase))
        zig = np.sin((xx + np.abs((yy % 28.0) - 14.0) * 2.2) * 0.090 + phase) * 0.5 + 0.5
        shag = _spb_norm01(np.sin(xx * 0.51 + yy * 0.17 + phase) + np.sin(yy * 0.47 - phase))
        sig = np.clip(disco * 0.34 + zig * 0.38 + shag * 0.28, 0, 1)
    elif "80s" in pattern_id:
        grid = np.maximum(
            1.0 - np.abs(np.mod(xx / 18.0 + 0.5, 1.0) - 0.5) * 8.0,
            1.0 - np.abs(np.mod(yy / 18.0 + 0.5, 1.0) - 0.5) * 8.0,
        )
        memphis = _spb_norm01(np.sin(xx * 0.21 + phase) + np.sign(np.sin(yy * 0.17 - phase)) * 0.7)
        sun = np.sin(np.hypot(xx - w * 0.5, yy - h * 0.72) * 0.11 + phase) * 0.5 + 0.5
        sig = np.clip(np.clip(grid, 0, 1) * 0.42 + memphis * 0.34 + sun * 0.24, 0, 1)
    elif "90s" in pattern_id:
        rng = np.random.default_rng(seed + family)
        grunge = _spb_norm01(rng.random((h, w)).astype(np.float32) * 0.55 + np.sin(xx * 0.37 + yy * 0.13) * 0.45)
        dot = ((np.mod(xx, 8.0) < 2.0) & (np.mod(yy, 8.0) < 2.0)).astype(np.float32)
        glitch = (np.sin(yy * 0.31 + phase) > 0.72).astype(np.float32) * (np.sin(xx * 0.08) * 0.5 + 0.5)
        sig = np.clip(grunge * 0.44 + dot * 0.30 + glitch * 0.26, 0, 1)
    return sig.astype(np.float32)


def _spb_expansion_detail_profile(pattern_id, index):
    family = _spb_hash_seed(pattern_id)
    is_decade = pattern_id.startswith("decade_")
    is_sparkle = any(tok in pattern_id for tok in ("sparkle", "shimmer", "chrome", "disco", "star", "prism"))
    is_ornate = any(tok in pattern_id for tok in ("lace", "filigree", "baroque", "mandala", "vine", "topographic"))
    return {
        "pv_weight": 0.78 - (0.05 if is_decade else 0.0) - (0.03 if is_sparkle else 0.0) - (index % 7) * 0.001,
        "fine_weight": 0.15 + (0.06 if is_decade else 0.0) + (0.03 if is_ornate else 0.0) + (family % 5) * 0.006 + (index % 11) * 0.001,
        "sparkle_weight": 0.05 + (0.09 if is_sparkle else 0.0) + (index % 4) * 0.008 + (index % 13) * 0.001,
        "range_boost": 1.06 + (0.08 if is_sparkle else 0.0) + (0.04 if is_ornate else 0.0) + (family % 6) * 0.006 + (index % 17) * 0.001,
    }


_EXPANSION_PATTERN_DETAIL_PROFILES = {
    _pid: _spb_expansion_detail_profile(_pid, _i)
    for _i, _pid in enumerate(NEW_PATTERN_IDS)
}


def _wrap_expansion_entry_detail(pattern_id, entry):
    if not isinstance(entry, dict):
        return entry
    tex_fn = entry.get("texture_fn")
    if tex_fn is None or getattr(tex_fn, "_spb_expansion_detail_wrapped", False):
        return entry

    def _texture(shape, mask, seed, sm):
        tex = tex_fn(shape, mask, seed, sm)
        if not isinstance(tex, dict) or "pattern_val" not in tex:
            return tex
        family = _spb_hash_seed(pattern_id)
        pv = _spb_norm01(tex["pattern_val"])
        fine, sparkle = _spb_micro_field(shape, seed + 811, family)
        profile = _EXPANSION_PATTERN_DETAIL_PROFILES.get(pattern_id) or _spb_expansion_detail_profile(pattern_id, 0)
        if pattern_id.startswith("decade_"):
            signature = _spb_decade_signature(pattern_id, shape, seed + 1301)
            pv = np.clip(pv * 0.66 + signature * 0.34, 0, 1)
        detail = np.clip(
            pv * profile["pv_weight"] + fine * profile["fine_weight"] + sparkle * profile["sparkle_weight"],
            0,
            1,
        )
        h, w = shape[:2] if len(shape) > 2 else shape
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        phase = (family % 360) * np.pi / 180.0
        micro_ink = (
            np.sin(xx * (1.07 + (family % 5) * 0.031) + yy * 0.17 + phase)
            * np.sin(yy * (1.19 + (family % 7) * 0.027) - xx * 0.13 - phase)
        ) * 0.5 + 0.5
        fiber = (
            (np.mod(xx + yy * 0.37 + (family % 29), 7.0) < 1.0)
            | (np.mod(xx - yy * 0.29 + (family % 31), 11.0) < 0.85)
        ).astype(np.float32)
        print_carrier = np.clip(micro_ink * 0.52 + fiber * 0.30 + fine * 0.18, 0, 1)
        if pattern_id.startswith("decade_"):
            # The Decades patterns need era motifs, not giant isolated stamps.
            # Add a dense print/film carrier so the pattern keeps coverage at
            # 2048 while the motif still carries the decade identity.
            halftone = (
                np.sin(xx * (0.72 + (family % 5) * 0.035) + phase)
                * np.sin(yy * (0.69 + (family % 7) * 0.029) - phase)
            ) * 0.5 + 0.5
            print_grain = np.clip(fine * 0.42 + halftone * 0.22 + sparkle * 0.14 + print_carrier * 0.34, 0, 1)
            detail = np.clip(detail * 0.70 + print_grain * 0.30, 0, 1)
            detail = np.maximum(detail, pv * 0.54 + print_grain * 0.34)
        else:
            detail = np.clip(detail * 0.84 + print_carrier * 0.16, 0, 1)
        out = dict(tex)
        out["pattern_val"] = detail.astype(np.float32)
        out["M_range"] = float(out.get("M_range") or 0.0) * profile["range_boost"]
        out["R_range"] = float(out.get("R_range") or 0.0) * profile["range_boost"]
        return out

    _texture._spb_expansion_detail_wrapped = True
    wrapped = dict(entry)
    wrapped["texture_fn"] = _texture
    return wrapped


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
        out = {pid: _wrap_expansion_entry_detail(pid, entry) for pid, entry in out.items()}
        return out
    except Exception as ex:
        # QUALITY GATE: Log loudly so pattern failures are visible
        import traceback
        print(f"[PATTERN EXPANSION] CRITICAL: Expansion patterns failed to load!")
        print(f"[PATTERN EXPANSION] Error: {ex}")
        traceback.print_exc()
        print(f"[PATTERN EXPANSION] WARNING: {len(NEW_PATTERN_IDS)} patterns degraded to generic fallback")

        # Fallback: generic no-op so registry load does not crash
        def _generic_texture(shape, mask, seed, sm):
            h, w = shape
            return {"pattern_val": np.full((h, w), 0.5, dtype=np.float32), "R_range": 0.0, "M_range": 0.0, "CC": None}

        def _generic_paint(paint, shape, mask, seed, pm, bb):
            if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
            return np.ascontiguousarray(paint[:, :, :3].astype(np.float32))

        generic = {"texture_fn": _generic_texture, "paint_fn": _generic_paint, "variable_cc": False, "desc": "Pattern (DEGRADED - expansion load failed)"}
        return {pid: dict(generic) for pid in NEW_PATTERN_IDS}


NEW_PATTERNS = _build_new_patterns()
