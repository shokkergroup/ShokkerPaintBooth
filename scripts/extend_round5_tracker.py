"""Extend the targeted round-5 tracker with more theme-sweep neighbors.

Owner is going to bed. Loop runs every 10 min. Current queue is 41 patterns
(~40 min of work). Adding ~50 more so the loop has 8-10 hours of overnight
work pushing as many spec patterns as possible toward 75%+ quality.

Patterns are selected based on the recurring themes from round-5 verdicts:
  - "Too sparse" / "looks like confetti"  -> dust, glitter, fleck families
  - "Pattern too large"                   -> abstract canvas-scale, gradient bands
  - "Wrong execution of right idea"       -> remaining abstract art names
  - "Too similar to other finishes"       -> sibling families (cc_*, brushed_*, guilloche_*, etc.)
  - "Preview better than rendering"       -> any pattern whose name promises a specific look
"""
import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER_PATH = ROOT / "_loop_state" / "targeted_round5_tracker.json"

t = json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
existing = set(t["pending"]) | set(t["rebuilt"])

# Theme: TOO_SPARSE (sparkle/dust/flake/pearl/glitter that likely have empty substrate)
EXT_TOO_SPARSE = [
    "pearl_micro", "diamond_dust", "crystal_shimmer", "micro_facets",
    "micro_sparkle", "micro_sparkle_cool", "micro_sparkle_warm",
    "gold_flake", "metallic_sand", "spec_sparkle_flake", "bead_blast_uniform",
]

# Theme: PATTERN_TOO_LARGE (canvas-scale or panel-scale features owner explicitly bans)
EXT_PATTERN_TOO_LARGE = [
    "gradient_bands", "depth_gradient", "split_bands", "banded_rows",
    "chevron_bands", "spiral_sweep", "wave_bands", "wave_ripple",
    "radial_sunburst", "gravity_well", "halftone_print",
    "spec_subsurface_depth", "spec_terrain_erosion", "spec_architectural_grid",
    "topographic_steps", "cc_panel_fade", "cc_panel_pool", "cc_gloss_stripe",
]

# Theme: ABSTRACT_EXECUTION (named after art movements, likely don't match the aesthetic)
EXT_ABSTRACT_EXECUTION = [
    "abstract_bauhaus_forms", "abstract_cubist_facets", "abstract_expressionist_splatter",
    "abstract_fluid_acrylic_pour", "abstract_futurist_motion", "abstract_hard_edge_field",
    "abstract_ink_wash_gradient", "abstract_minimalist_stripe", "abstract_neon_glitch",
    "abstract_op_art_circles", "abstract_op_art_waves", "abstract_retro_wave",
    "brushstroke_bold",
]

# Theme: TOO_SIMILAR (sibling families with high collision risk)
EXT_SIBLING_DEDUPE = [
    # cc_* family
    "cc_drip_runs", "cc_edge_thin", "cc_fish_eye", "cc_masking_edge",
    "cc_overspray_halo", "cc_spot_polish", "cc_wet_zone",
    # brushed_linear variants
    "brushed_linear_cool", "brushed_linear_warm", "brushed_sparkle",
    # guilloche family
    "guilloche_barleycorn", "guilloche_hobnail", "guilloche_moire_eng",
    "guilloche_sunray", "guilloche_waves",
    # rust/patina family
    "rust_bloom", "spec_rust_bloom", "copper_patina_drip", "patina_bloom",
    "spec_patina_verdigris", "spec_galvanic_corrosion",
    # weather/grime family
    "engine_bay_grime", "track_grime", "tire_smoke_residue", "tire_smoke_streaks",
    "mud_splatter_random", "morning_dew_fog", "tarmac_grit_embed",
]

# Build per-name brief
new_briefs = {}
for n in EXT_TOO_SPARSE:
    if n in existing: continue
    new_briefs[n] = {"kind": "NEIGHBOR", "theme": "TOO_SPARSE",
        "brief": "DENSITY 5-10x. Owners recurring complaint is that pattern outputs are too sparse / look like confetti with empty substrate. Triple-to-quintuple the feature count, pack tightly, no large blank substrate regions. Add chroma diversity per feature so the density doesnt go flat."}
for n in EXT_PATTERN_TOO_LARGE:
    if n in existing: continue
    new_briefs[n] = {"kind": "NEIGHBOR", "theme": "PATTERN_TOO_LARGE",
        "brief": "FEATURES TOO LARGE. Owner explicitly bans macro/panel-scale features. Shrink current primary feature scale 3-4x to land in 8-32 px range. Add per-feature INDEPENDENT M/R/CC continuous uniforms. Multiple feature tiers stacked. Density up to compensate for smaller features. If the pattern is band-based, narrow bands to 4-12 px and tile densely. If gradient-based, break the gradient into many short segments with chroma variance."}
for n in EXT_ABSTRACT_EXECUTION:
    if n in existing: continue
    new_briefs[n] = {"kind": "NEIGHBOR", "theme": "PREVIEW_VS_RENDER",
        "brief": "EXECUTION RISK. Abstract patterns frequently fail because the description promises art-school intent but render delivers something different. Study the named art movements signature visual rhythm and force that into the render. Bauhaus = primary colors + bold geometric shapes (circles, triangles, rectangles) on neutral; Cubist = fragmented angular faceting with sharp edges; Expressionist Splatter = energetic visible brushstrokes + paint droplets; Fluid Acrylic Pour = swirling colored cells with ouzo-like rings; Futurist Motion = streaky directional speed lines + dynamic angles; Hard Edge Field = flat saturated color blocks with razor edges; Ink Wash Gradient = soft sumi-e gradients with subtle tonal washes; Minimalist Stripe = few clean parallel stripes with breathing room; Neon Glitch = digital corruption RGB shift + scanlines; Op Art Circles = concentric ring moire; Op Art Waves = parallel wavy line moire; Retro Wave = magenta/cyan grid + sunset gradient; Brushstroke Bold = thick visible impasto strokes with bristle texture. Match the named aesthetic EXACTLY."}
for n in EXT_SIBLING_DEDUPE:
    if n in existing: continue
    new_briefs[n] = {"kind": "NEIGHBOR", "theme": "TOO_SIMILAR",
        "brief": "UNIQUENESS FAIL RISK. This pattern is part of a sibling family where multiple variants risk looking identical. Lean HARDER into this specific names differentiator. cc_drip_runs = vertical running drips; cc_edge_thin = thin clearcoat at panel edges; cc_fish_eye = round crater-like silicone repellent spots; cc_masking_edge = sharp paint masking line with bleed; cc_overspray_halo = soft halo around clearcoat boundary; cc_spot_polish = polished circular spots; cc_wet_zone = wet glossy patches; brushed_linear_cool = cool-tone bias (blue/silver striations); brushed_linear_warm = warm-tone bias (gold/copper striations); brushed_sparkle = brushed direction + sparkle glints; guilloche_barleycorn = oat-grain elongated pattern; guilloche_hobnail = raised pin-dot grid; guilloche_moire_eng = engine-turned moire rings; guilloche_sunray = radiating ray pattern; guilloche_waves = wavy interference; rust_bloom = bloomed orange rust spots; spec_rust_bloom = same as rust but in spec map context; copper_patina_drip = vertical green-blue patina drip trails; patina_bloom = scattered green-blue oxidation patches; spec_patina_verdigris = deep teal-green patina with crystalline crust; spec_galvanic_corrosion = pitted corrosion with metallic crust; engine_bay_grime = oily dark grime smudges; track_grime = layered racing-track soot; tire_smoke_residue = soft grey smoke deposit; tire_smoke_streaks = directional smoke streaks; mud_splatter_random = chunky mud blobs with droplet trails; morning_dew_fog = tiny water droplet beads; tarmac_grit_embed = embedded sharp aggregate particles. Avoid generic substrate + flecks pattern."}

# Add new patterns to pending (after current queue so direct REBUILDs still go first)
added = list(new_briefs.keys())
t["pending"].extend(added)
t["total"] = len(t["pending"]) + len(t["rebuilt"])
t["briefs"].update(new_briefs)
t["_extended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

TRACKER_PATH.write_text(json.dumps(t, indent=2), encoding="utf-8")

# Summary
by_theme = {}
for n, b in new_briefs.items():
    by_theme.setdefault(b["theme"], []).append(n)

print(f"Added {len(added)} new theme-sweep patterns to tracker.")
for theme, names in by_theme.items():
    print(f"  {theme} ({len(names)}): {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")
print(f"\nTracker now: {len(t['pending'])} pending, {len(t['rebuilt'])} rebuilt, {t['total']} total")
print(f"At 12/tick every 10 min, queue covers ~{len(t['pending']) // 12 * 10} min of overnight work")
