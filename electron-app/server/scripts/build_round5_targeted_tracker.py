"""Build targeted re-attack tracker: 11 direct + 30 theme neighbors.

Reads round-5 owner verdicts (REBUILD/MIXED/KEEP) and builds a per-pattern
rebuild brief that bakes the owner comment OR derived theme into the prompt.
"""
import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Direct re-attack targets (11) — owner comment baked into brief
DIRECT = [
    # (name, rating, verdict, owner_comment, brief)
    ("spec_oil_film_thick", 4, "REBUILD",
     "Way too sparse",
     "DENSITY 5x. Currently too few pools across canvas. Need 30-60 iridescent pools (instead of 6), each 20-100 px (smaller), packed densely. Per-pool independent CC rainbow segment still mandatory. Add micro-droplet field between pools so NO blank substrate visible."),

    ("wear_scuff", 3, "REBUILD",
     "This looks more like confetti than anything else",
     "OWNER SAYS IT LOOKS LIKE CONFETTI. The current scattered specks are wrong. Replace with: large bare-metal patches (50-150 px) showing through worn paint at high-traffic zones. Bold M-channel contrast (paint M=low, bare metal M=high) in BOLD regions not tiny dots. Directional scratch streaks 30-120 px long. NO scattered specks."),

    ("galaxy_swirl", 2, "REBUILD",
     "Do NOT like the pattern at all. Too sparse",
     "OWNER HATES IT. Total rebuild with 5-8 galaxies (not 2-3), MUCH denser star fields (3-5x), brighter cores, defined dust lanes. Galaxies must read clearly even at thumbnail scale — current preview shows mostly empty space."),

    ("spec_hammered_dimple", 3, "REBUILD",
     "Like the idea not execution. I would think Hammered Dimple would be like the dimples on a golf ball and have more interesting texture/pattern design",
     "OWNER WANTS GOLF-BALL DIMPLES. Distinct circular indentations 14-22 px with CLEAR circular outline (dark rim shadow + dark well + bright opposite-side highlight crescent). Hexagonal close-packing like a real golf ball. Per-dimple INDEPENDENT M/R/CC. Tight uniform sizes, NOT varied scatter."),

    ("spec_wood_grain_fine", 3, "REBUILD",
     "Just dont like the texture/finish",
     "Owner rejects current grain look. Try a different wood: more BURL-like with concentric whorls + chatoyance (cats-eye sheen along grain) instead of straight rings. Mix flatsawn ring patches with quartersawn ray-fleck patches. Per-ring INDEPENDENT M/R/CC. Knots prominent with ring-distortion around them."),

    ("spec_stone_marble", 2, "REBUILD",
     "HATE the design",
     "OWNER HATES IT. Ground-up redesign. Try Carrara aesthetic: white-grey base matrix with bold black/dark-grey veins flowing diagonally (NOT mottled blob veins). Macro veins 24-60 px with sharp branching tributaries. Per-vein independent CC + M. Gold/copper minor veins as accent. Avoid current random scribble look."),

    ("buffer_swirl", 6, "MIXED",
     "Its decent but the spec IMO could use a little more pattern work (make it come through more)",
     "Decent direction. STRENGTHEN: triple density of polish arcs, deeper M-channel contrast between burnish ridges and valleys, stronger per-swirl CC variation so arcs are visually DISTINCT in color/tint not just position."),

    ("spec_lava_flow", 5, "MIXED",
     "Its got some interesting elements but overall it feels like it has no depth in the lava flow areas. Not interesting",
     "Needs DEPTH in flow areas. Current ropes are too uniform. Add: bright hot cracks running ALONG flow ropes (M=low R=high CC=bright cracked center), 3-tier flow widths (8/16/32 px nested), dark obsidian crust between flows with sharp edges. Strong M-channel gradient between hot/cool zones."),

    ("crackle_network", 6, "MIXED",
     "Dinging it because of similarities with other finishes",
     "TOO SIMILAR to other patterns. Make it UNIQUELY crackle: shrinkage cracks NOT voronoi cells. Long curved cracks 40-200 px branching dendritically. Crack edges sharp + bright. Between cracks: very flat substrate (NOT colorful cells). Less colorful, more mud-cracked-dry-lake aesthetic."),

    ("spec_iridescent_film", 4, "MIXED",
     "Another one where the preview looks much better than the rendering result. They look like different finishes",
     "OWNER SAYS PREVIEW BETTER THAN RENDER — the description sold thin-film soap-bubble interference and the render does not deliver. Make it ACTUALLY look like a soap bubble: smooth flowing rainbow gradients across the canvas (not the current static striped look), high mirror M everywhere, R near zero, CC carries continuous spectral sweep. Film-flex highlights."),

    ("spec_damascus_steel_spec", 6, "MIXED",
     "Has some originality - but the pattern design itself is just too large, not enough variety in the spec coloring, etc",
     "Pattern TOO LARGE — current bands are panel-scale, owner wants fine. Shrink band scale 3-4x so layers are 4-12 px wide not 30+. Add 4-tier brightness variance per band (no two adjacent same), independent CC tint per band, micro-etching dots inside bands."),
]

# Theme-sweep neighbors (30)
THEME_TOO_SPARSE = [
    "sparkle_champagne","sparkle_constellation","sparkle_electric_field","sparkle_firefly",
    "sparkle_galaxy_swirl","sparkle_nebula","sparkle_rain","sparkle_shattered",
    "stardust_fine","prismatic_dust","flake_scatter",
]
THEME_PATTERN_TOO_LARGE = [
    "spec_brick_mortar","spec_corrugated_panel","spec_expanded_metal",
    "magnetic_field","plasma_turbulence","orbital_swirl",
]
THEME_ABSTRACT_EXECUTION = [
    "abstract_kandinsky_shapes","abstract_mondrian_grid","abstract_rothko_field",
    "abstract_color_field_bleed","abstract_suprematism",
]
THEME_SIBLING_DEDUPE = [
    "brushed_arc","brushed_cross","brushed_diagonal","brushed_radial",
    "spec_carbon_2x2_twill","spec_carbon_3k_fine","spec_carbon_forged","spec_carbon_wet_layup",
]

NEIGHBORS = []
for n in THEME_TOO_SPARSE:
    NEIGHBORS.append((n, "TOO_SPARSE",
        "DENSITY 5-10x. Owners recurring complaint is that pattern outputs are too sparse / look like confetti with empty substrate. For this pattern: triple-to-quintuple the feature count, pack tightly, no large blank substrate regions. Add chroma diversity per feature so the density doesnt go flat."))
for n in THEME_PATTERN_TOO_LARGE:
    NEIGHBORS.append((n, "PATTERN_TOO_LARGE",
        "FEATURES TOO LARGE. Owner explicitly bans macro/panel-scale features. Shrink current primary feature scale 3-4x to land in 8-32 px range. Add per-feature INDEPENDENT M/R/CC continuous uniforms. Multiple feature tiers stacked. Density up to compensate for smaller features."))
for n in THEME_ABSTRACT_EXECUTION:
    NEIGHBORS.append((n, "PREVIEW_VS_RENDER",
        "EXECUTION RISK. Abstract patterns frequently fail the owner because the description promises art-school intent but render delivers something different. For this pattern: actively study the named art movements signature visual rhythm and force that into the render — Mondrian = bold orthogonal blocks with primary colors, Rothko = soft horizontal color-field bands, Kandinsky = floating geometric forms with bold colors, Suprematism = pure geometric shapes on void, color_field_bleed = soft saturated edges meeting. Match the named aesthetic exactly."))
for n in THEME_SIBLING_DEDUPE:
    NEIGHBORS.append((n, "TOO_SIMILAR",
        "UNIQUENESS FAIL RISK. This pattern is part of a sibling family (brushed_*, spec_carbon_*) where multiple variants risk looking identical. For THIS specific variant: lean HARDER into its names differentiator. brushed_arc = curved drag marks, brushed_cross = perpendicular cross-grain, brushed_diagonal = single 45-deg direction, brushed_radial = arcs around center, carbon_2x2_twill = diagonal twill weave, carbon_3k_fine = ultra-fine 4-6 px tows, carbon_forged = chunky marbled patches, carbon_wet_layup = visible resin flow + air bubbles. Avoid generic striations."))

# Priority queue: REBUILDs first (highest), then MIXEDs, then theme neighbors
priority_order = [n for n,r,v,c,f in DIRECT if v=="REBUILD"]
priority_order += [n for n,r,v,c,f in DIRECT if v=="MIXED"]
priority_order += [n for n,_,_ in NEIGHBORS]

briefs = {}
for n,r,v,c,f in DIRECT:
    briefs[n] = {"kind":"DIRECT","rating":r,"verdict":v,"owner_comment":c,"brief":f}
for n,theme,brief in NEIGHBORS:
    briefs[n] = {"kind":"NEIGHBOR","theme":theme,"brief":brief}

tracker = {
    "started": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
    "total": len(priority_order),
    "pending": priority_order,
    "rebuilt": [],
    "briefs": briefs,
    "ticks": [],
}
out = ROOT / "_loop_state" / "targeted_round5_tracker.json"
out.write_text(json.dumps(tracker, indent=2), encoding="utf-8")
print(f"Built targeted tracker: {len(priority_order)} patterns")
print(f"  REBUILDs (priority 1): 6")
print(f"  MIXEDs   (priority 2): 5")
print(f"  Theme neighbors:       {len(NEIGHBORS)}")
print(f"  tracker: {out}")
