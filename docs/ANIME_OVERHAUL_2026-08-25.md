# ★ ANIME INSPIRED OVERHAUL — 19 → 25 mind-melting designs (owner mandate 2026-08-25)

**Owner's words:** "Make it your lifes goal to expand the 19 we have to 25 designs and making them mind melting…
NO REPEATS, NO LAZINESS — do NOT reuse patterns or designs. Everything should stand on it's own ground."

**Lane state doc** — per-run evidence lives HERE, not the wiki (lean rules). Claude owns this lane.

## Pre-overhaul state (recon 2026-08-25)

- 10 `anime_*` BASE_REGISTRY finishes (`engine/paint_v2/anime_style.py`): M7 composites **55.9–72.3 — every one
  below the 75 floor** (speed_lines 55.9, sparkle_burst 56.6, comic_halftone 58.7, energy_aura 62.3, crystal 66.9,
  cel_shade 69.3, neon_outline 70.3, mecha 71.6, gradient_hair 71.9, sakura 72.3). Mostly single low-freq fields +
  recolors.
- 8 `anime2_*` monolithic specials (`engine/expansions/anime_catalog_2026.py` → `anime_math.ANIME_STRUCTURES`):
  better concepts but rendered at **760–1152 px then upscaled to 2048** (mush, violates crushed-fine-detail),
  petals are plain ellipses, and **specs are recycled flame_spec modes** (dance/ignite/topo) — not married to the
  art (violates spec-mirrors-structure).
- +1 stray `monolithic:cel_shade` @ 46.6 (fix tier) = the owner's "19".

## Architecture

ONE library: `engine/paint_v2/anime_math.py` (full rewrite) — 25 structures, each `_b_<key>(shape, seed)` returning
`{'rgb': float32 (h,w,3) 0-1, 'spec': float32 (h,w,3) 0-255 as M,R,CC}` computed in ONE pass from shared geometry
(married spec = high trace on the catalog fingerprint by construction). `build(key, shape, seed)` is lru-cached so
paint_fn + spec_fn share one compute. All features scale by `h/2048` (native-res generation at ANY size — no
upscale mush; fine features 8–32 px AT 2048). Budget ≤ ~2.5 s @2048 per structure (paint+spec combined).

Wiring (ids stable, saved projects safe):
- 10 base ids keep their `paint_/spec_` fn names in `anime_style.py` → thin wrappers over anime_math.
- 15 mono ids in `anime_catalog_2026.py` (8 rebuilt concepts + 7 NEW ids), specs switched to married `ANIME_SPECS`.
- JS: 7 new entries + desc/name updates; `_SPECIALS_ANIME_INSPIRED` grows to 15.
- Gate: NEW `tests/regression_anime_uniqueness_test.py` mirroring the flame reference (uniqueness <0.80,
  render <3 s @2048, coverage ≥ MIN_COVERAGE, fineness ≥ MIN_FINENESS) + spec-std check (M/R/CC std ≥20).

## THE 25 — concept ledger (mechanism families, all distinct)

| # | structure key | id | display | mechanism family (NOT shared with any other) |
|---|---|---|---|---|
| 1 | `cel_terminator` | anime_cel_shade_chrome | Cel Terminator | multi-light posterized warp-field cel bands + SDF ink terminators + hatch penumbra + chrome toon highlight |
| 2 | `speedline_storm` | anime_speed_lines | Speed-Line Storm | multi-focal radial line systems INTERFERING + concentration-density waves + line-weight modulation |
| 3 | `shoujo_sparkle` | anime_sparkle_burst | Shoujo Sparkle Field | 4/5/6-point star SDF scatter + bubble bokeh + prism cross-flares, 8-tier brightness ladder |
| 4 | `inkbrush_strands` | anime_gradient_hair | Ink-Brush Strands | anisotropic streamline hair flow + sheen band angle-mapped + strand crossovers/flyaways |
| 5 | `mecha_greeble` | anime_mecha_plate | Mecha Greeble | recursive CHAMFERED panel subdivision + rivet fields + vent louvers + warning chevrons + glowing seams |
| 6 | `sakura_hurricane` | anime_sakura_scatter | Sakura Hurricane | curl-advected petal storm, TRUE 5-notch petal polygons, 3 depth layers + wind streaks |
| 7 | `ki_corona` | anime_energy_aura | Ki Corona | advected aura tongues (flow-warped) + electric filaments + rising embers, double corona |
| 8 | `screentone_moire` | anime_comic_halftone | Screentone Moiré | interfering rotated Ben-Day dot lattices, radius-modulated tone gradients + ink hatch pockets |
| 9 | `neo_tokyo_glow` | anime_neon_outline | Neo-Tokyo Glow | night city window-grid clusters + neon sign strokes + wet-street reflection streaks |
| 10 | `shard_cascade` | anime_crystal_facet | Crystal Shard Cascade | Voronoi shatter + per-shard internal refraction banding + edge glints + micro-facet dust |
| 11 | `cel_cloud_sea` | anime2_cel_shade | Cel Cloud Sea | stacked cumulus cloudlet SDF puffs, 3-tone cel band shading + ink rims + wind streaks (Ghibli) |
| 12 | `impact_frames` | anime2_screentone | Impact Frames | discrete manga impact-burst CELLS: jagged radial sectors, B/W inversions, halftone interiors |
| 13 | `hanami_night` | anime2_sakura | Hanami Night | paper-lantern glow orbs + firefly bokeh + smoke wisps + minor petal garnish (festival night) |
| 14 | `mecha_hologrid` | anime2_mecha | Mecha Hologrid | holographic CAD wireframe: depth-faded grid + targeting reticles + dimension ticks + scan bands |
| 15 | `shuriken_storm` | anime2_speed_lines | Shuriken Storm | rotated blade-star SDFs + spin arc-trails + embed cracks |
| 16 | `raiton_lightning` | anime2_energy_aura | Raiton Lightning | dendritic Lichtenberg branching, stepped anime bolts, white-hot core / cyan sheath |
| 17 | `iris_gem_field` | anime2_crystal | Iris Gem Field | tiled anime-eye iris geometry: concentric ring systems + radial fibers + catchlight sparkles |
| 18 | `holo_idol_foil` | anime2_gradient_hair | Holo Idol Foil | idol-sticker holo foil: diagonal interference gradients + micro-prism cell lattice + confetti stars |
| 19 | `kanji_rain` | anime2_kanji_rain (NEW) | Kanji Rain | procedural pseudo-glyph stroke assembly falling in columns + speed blur (no real text) |
| 20 | `onomatopoeia` | anime2_onomatopoeia (NEW) | Onomatopoeia Riot | jagged comic burst polygons, double-outline ink, halftone fills, dense overlap |
| 21 | `cyber_glitch` | anime2_glitch (NEW) | Cyber Glitch | slice displacement + pixel-sort streaks + corrupted block mosaic + RGB split |
| 22 | `retro_broadcast` | anime2_broadcast (NEW) | Retro Broadcast | CRT raster: scanlines + phosphor triads + chroma aberration + interlace jitter + test-bar fragments |
| 23 | `blood_moon` | anime2_blood_moon (NEW) | Blood Moon Eclipse | multiplied moon disks w/ crater cel-bands + cloud wisps + silhouette flock speckle |
| 24 | `oni_sumi` | anime2_oni_sumi (NEW) | Oni Sumi-e | sumi-e dry-brush stroke stamping + bristle texture + red hanko seals + ink splatter |
| 25 | `manga_page` | anime2_manga_page (NEW) | Manga Page Chaos | recursive axis-aligned panel tiling, ink gutters, EACH panel a different micro-tone fill |

**Collision watchlist** (verify with fingerprint, redo if ≥0.80): 5 vs 25 vs 9 (rect subdivisions — differentiated:
chamfered industrial vs ink-gutter multi-fill vs tiny uniform window clusters), 2 vs 12 (radial — continuous
interfering line systems vs discrete jagged burst cells), 3 vs 13 vs 18 (sparkle/bokeh — stars vs lantern orbs vs
prism lattice), 7 vs 16 (energy — advected tongues vs dendritic bolts). Cross-catalog: cx_dragon_scale (voronoi),
sequin disco (sparkle), tactical cyberpunk (glitch), carbon (grids), neon underground (city glow).

## Progress log (newest first)

- 2026-08-25 SHIPPED (awaiting owner look): **25/25 >= 85 M7** (93.9 best, 85.3 lowest; was 55.9-72.3
  with every finish under the 75 floor). 25/25 whole-catalog uniqueness PASS (worst neighbor 62%,
  most 35-53%). Anime regression gate 6/6 @2048. Two-copy parity verified (4 engine modules were in
  the report-only sync set — copied manually).
  KEY FINDINGS this run:
  - **owner_review_anime.py (SPB-30) silently overrides anime_style at boot** ("[Regular Base V2]"
    pass) — the first rebuild round shipped to nowhere until that module was re-pointed. It now
    re-exports anime_style (no frozen copies, documented in its header).
  - **rebuild_thumbnails.py base bake was broken since the source-paint contract** — every base
    with a real paint_fn baked flat gray (ms_crimson_dragon std 0.0; M1 had a 63-member gray clone
    group). Fixed like the mono branch: zone gets base_color_mode special + base_color_source.
  - **M2/M5/M6 read paint-booth-0-catalog-scorecard.js** — stale until re-measured; built
    _anime_overhaul_work/refresh_anime_scorecard.py (clones the wilds refresher pattern).
  - Metric-driven ART upgrades that landed: anime-pop saturation pass, micro-flake clear layer
    (multiplicative + additive, per-structure tuned, full-span M 2..252 specs), parity/period-3
    lacquer cels (spec channel independence), 4-color manga print, single-channel glitch spec ops.
  - M6 profiles added for 'Anime / Stylized' + '★ ANIME INSPIRED' = {specMRange HI, specRRange HI};
    M2 vocab batch (kanji/glitch/mecha/sakura; sumi+manga dropped after measuring their claims wrong).
  Verification chain per round: pytest regression @2048 -> bake 25 thumbs (one boot) -> scorecard
  refresh -> m1/m2/m5/m6/m7 -> composites. Sheets in _anime_overhaul_work/sheets/ (FINAL25.png).

- 2026-08-25: recon complete, lane claimed, ledger written. Building library waves next.
  Harness: `_anime_overhaul_work/harness.py`. Contact sheets: `_anime_overhaul_work/sheets/`.
