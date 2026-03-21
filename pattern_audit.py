"""
Pattern Audit Script — Removes patterns and categories per Ricky's audit instructions.
Modifies paint-booth-0-finish-data.js (the single source of truth).

This script:
1. Removes entire PATTERN_GROUPS categories
2. Removes specific patterns from remaining categories
3. Moves patterns between categories
4. Removes orphaned pattern entries from PATTERNS array
5. Syncs to electron-app/server/ copy
"""
import re
import os
import shutil

V5 = os.path.dirname(os.path.abspath(__file__))
JS_FILE = os.path.join(V5, 'paint-booth-0-finish-data.js')
JS_COPY = os.path.join(V5, 'electron-app', 'server', 'paint-booth-0-finish-data.js')

# ================================================================
# CATEGORIES TO COMPLETELY REMOVE (all patterns in them go too)
# ================================================================
CATEGORIES_TO_REMOVE = [
    "Flames",
    "Flames - Expansion",
    "Music & Band",
    "Music Inspired",
    "Astrological & Cosmic",
    "Damage & Wear",
    "Medical & Science",
    "Nature & Organic",
    "Racing & Motorsport",
    "Skate & Surf",
]

# ================================================================
# SPECIFIC PATTERNS TO REMOVE FROM CATEGORIES THAT STAY
# ================================================================
PATTERNS_TO_REMOVE_FROM = {
    "Metal & Industrial": ["grating", "knurled", "mega_flake", "rivet_grid", "rivet_plate", "roll_cage"],
    "Tech & Digital": ["binary_code", "circuit_board", "hologram", "qr_code", "static_noise", "tron", "holographic_flake"],
}

# ================================================================
# PATTERNS TO MOVE: Tech & Digital → SHOKK PATTERNS
# ================================================================
PATTERNS_TO_MOVE_TO_SHOKK = ["data_stream", "glitch_scan", "matrix_rain", "pixel_grid"]

# ================================================================
# SHOKK PATTERNS: Remove ALL current entries (will be replaced with new ones later)
# ================================================================
SHOKK_REMOVE_ALL = True

# ================================================================
# "Other" patterns to nuke (patterns in PATTERNS array but NOT in any group)
# These are the specific IDs from the user's list
# ================================================================
OTHER_PATTERNS_TO_REMOVE = [
    # Legacy flames
    "blue_flame_legacy", "classic_hotrod", "ember_scatter", "fire_lick", "fireball",
    "flame_fade", "ghost_flames", "hellfire", "inferno", "nitro_burst",
    "none_base_only", "pinstripe_flames", "torch_burn", "tribal_flame", "wildfire",
    # 50s starburst variants
    "atomic_starburst_gradient", "atomic_starburst_halftone", "atomic_starburst_mixed",
    "atomic_starburst_pure", "atomic_starburst_shiny_dots",
    # 50s dice/drive-in
    "dice_roll_halftone", "dice_roll_pure", "drivein_halftone", "drivein_pure",
    # 50s hot rod
    "hotrod_flame_gradient", "hotrod_flame_halftone_gradient", "hotrod_flame_pure",
    # 60s
    "clockwork_halftone", "clockwork_pure", "doo_flower_tile", "groovy_pure", "hippie_pure",
    "peace_gradient", "peace_gradient_noise", "peace_halftone", "peace_pure",
    # 70s
    "breaker_pure", "breaker_tiled", "diamond_knot_halftone", "diamond_knot_pure",
    "diamond_knot_wild", "disco_fever_halftone", "disco_fever_pure", "groovy_geometry",
    # 80s
    "rad_bell", "synthwave_future_shock", "synthwave_future_pure", "synthwave_pure",
    # 90s
    "grunge_hex", "grunge_scratch",
    # Misc orphans
    "bullet_holes", "cape_flow", "carbon_4x4", "carbon_spread_tow", "carbon_uni",
    "cartoon_plaid", "circuitboard", "comic_halftone", "comic_panel", "dark_knight_scales",
    # Decade 60s orphans
    "decade_60s_acid_test", "decade_60s_british_invasion", "decade_60s_flower_power",
    "decade_60s_mod_target", "decade_60s_moon_landing", "decade_60s_muscle_car_stripe",
    "decade_60s_paisley_bandana", "decade_60s_psychedelic_swirl", "decade_60s_surf_wave",
    "decade_60s_tv_static", "decade_60s_vw_bus_panel", "decade_60s_warhol_grid",
    "decade_60s_woodstock_mud",
    # More orphans
    "exhaust_wrap", "g_force", "gamma_pulse", "groovy_swirl", "harness_weave",
    "hero_burst", "hero_crest_curve", "hero_pointed_cowl", "hero_scallop_edge",
    "lace", "morse_code",
    "music_blues", "music_licked", "music_smilevana", "music_strat", "music_the_artist",
    "peeling_paint", "polka_pop", "pow_burst", "power_aura", "power_bolt",
    "prehistoric_spot", "quilted", "retro_atom", "retro_flower_power",
    "river_stone", "road_rash", "rust_bloom", "shield_rings",
    "shokk_phase_interference", "shokk_phase_split", "shokk_phase_vortex",
    "shrapnel", "silk_weave", "smilexx_pure_placeholder",
    "soundwave", "spark_scatter",
    "toon_bones", "toon_cloud", "toon_lightning", "toon_speed", "toon_stars",
    "tree_bark", "tweed_weave", "velvet", "villain_stripe", "web_pattern",
    "wifi_waves", "yin_yang", "zigzag_stripe",
]

def main():
    with open(JS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Collect ALL pattern IDs to remove
    all_ids_to_remove = set(OTHER_PATTERNS_TO_REMOVE)

    # ── Step 1: Extract IDs from categories being removed ──
    for cat in CATEGORIES_TO_REMOVE:
        pattern = rf'"{re.escape(cat)}"\s*:\s*\[(.*?)\]'
        m = re.search(pattern, content)
        if m:
            ids = re.findall(r'"([^"]+)"', m.group(1))
            all_ids_to_remove.update(ids)
            print(f"  Category '{cat}': {len(ids)} patterns to remove")
        else:
            print(f"  WARNING: Category '{cat}' not found in PATTERN_GROUPS!")

    # ── Step 2: Extract IDs from specific removals within categories ──
    for cat, ids in PATTERNS_TO_REMOVE_FROM.items():
        all_ids_to_remove.update(ids)
        print(f"  From '{cat}': removing {len(ids)} specific patterns")

    # ── Step 3: SHOKK - remove all current entries ──
    if SHOKK_REMOVE_ALL:
        m = re.search(r'"SHOKK PATTERNS"\s*:\s*\[(.*?)\]', content)
        if m:
            shokk_ids = re.findall(r'"([^"]+)"', m.group(1))
            # Don't remove data_stream, glitch_scan, matrix_rain, pixel_grid - those are moving IN
            shokk_to_remove = [sid for sid in shokk_ids if sid not in PATTERNS_TO_MOVE_TO_SHOKK]
            all_ids_to_remove.update(shokk_to_remove)
            print(f"  SHOKK: removing {len(shokk_to_remove)} current patterns")

    print(f"\nTotal unique pattern IDs to remove: {len(all_ids_to_remove)}")

    # ── Step 4: Remove category entries from PATTERN_GROUPS ──
    for cat in CATEGORIES_TO_REMOVE:
        # Remove the entire line for this category
        pattern = rf'\s*"{re.escape(cat)}"\s*:\s*\[.*?\],?\n'
        content, n = re.subn(pattern, '\n', content)
        if n:
            print(f"  Removed PATTERN_GROUPS entry: '{cat}'")
        else:
            print(f"  WARNING: Could not remove PATTERN_GROUPS entry: '{cat}'")

    # ── Step 5: Remove specific patterns from categories that stay ──
    for cat, ids_to_remove in PATTERNS_TO_REMOVE_FROM.items():
        pattern = rf'("{re.escape(cat)}"\s*:\s*\[)(.*?)(\])'
        m = re.search(pattern, content)
        if m:
            old_list = m.group(2)
            # Remove each ID from the list
            for pid in ids_to_remove:
                old_list = re.sub(rf',?\s*"{re.escape(pid)}"', '', old_list)
                old_list = re.sub(rf'"{re.escape(pid)}"\s*,?\s*', '', old_list)
            # Clean up double commas and leading/trailing commas
            old_list = re.sub(r',\s*,', ', ', old_list)
            old_list = old_list.strip().strip(',').strip()
            content = content[:m.start()] + m.group(1) + old_list + m.group(3) + content[m.end():]
            print(f"  Updated '{cat}': removed {len(ids_to_remove)} patterns")

    # ── Step 6: Update SHOKK PATTERNS to contain the moved patterns ──
    shokk_new_ids = PATTERNS_TO_MOVE_TO_SHOKK[:]
    shokk_list = ', '.join(f'"{pid}"' for pid in shokk_new_ids)
    content = re.sub(
        r'"SHOKK PATTERNS"\s*:\s*\[.*?\]',
        f'"SHOKK PATTERNS": [{shokk_list}]',
        content
    )
    print(f"  Updated SHOKK PATTERNS: now contains {shokk_new_ids}")

    # ── Step 7: Update Tech & Digital (remove moved + removed patterns) ──
    tech_remove = set(PATTERNS_TO_MOVE_TO_SHOKK) | set(PATTERNS_TO_REMOVE_FROM.get("Tech & Digital", []))
    m = re.search(r'("Tech & Digital"\s*:\s*\[)(.*?)(\])', content)
    if m:
        old_list = m.group(2)
        for pid in tech_remove:
            old_list = re.sub(rf',?\s*"{re.escape(pid)}"', '', old_list)
            old_list = re.sub(rf'"{re.escape(pid)}"\s*,?\s*', '', old_list)
        old_list = re.sub(r',\s*,', ', ', old_list)
        old_list = old_list.strip().strip(',').strip()
        if not old_list:
            # If empty, remove the whole category
            content = re.sub(r'\s*"Tech & Digital"\s*:\s*\[.*?\],?\n', '\n', content)
            print("  Tech & Digital: ALL patterns removed, category deleted")
        else:
            content = content[:m.start()] + m.group(1) + old_list + m.group(3) + content[m.end():]
            print(f"  Updated Tech & Digital: remaining = {old_list}")

    # ── Step 8: Remove pattern entries from PATTERNS array ──
    removed_count = 0
    for pid in all_ids_to_remove:
        # Match pattern entry: { id: "xxx", name: "...", desc: "...", swatch: "..." }
        # Handle both single-line and possible multi-line entries
        pattern = rf'\s*\{{\s*id:\s*"{re.escape(pid)}"[^}}]*\}},?\n?'
        content, n = re.subn(pattern, '', content, count=1)
        if n:
            removed_count += 1

    print(f"\n  Removed {removed_count} / {len(all_ids_to_remove)} pattern entries from PATTERNS array")

    # ── Step 9: Clean up any double blank lines ──
    content = re.sub(r'\n{3,}', '\n\n', content)

    # ── Step 10: Write back ──
    with open(JS_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\nWrote {JS_FILE}")

    # Sync to electron-app/server/
    if os.path.isfile(JS_COPY):
        shutil.copy2(JS_FILE, JS_COPY)
        print(f"Synced to {JS_COPY}")

    # ── Summary ──
    # Count remaining patterns
    remaining = len(re.findall(r'\{\s*id:\s*"', content))
    print(f"\n{'='*60}")
    print(f"AUDIT COMPLETE")
    print(f"  Removed {removed_count} patterns from PATTERNS array")
    print(f"  Removed {len(CATEGORIES_TO_REMOVE)} entire categories")
    print(f"  Remaining patterns: ~{remaining}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
