# Texture & Category Cleanup — Next Edits Plan

Suggested reworks for **Decades (50s–90s)**, **Flames** (5 categories), **Racing & Motorsport**, **Skate & Surf**, and **Music & Band**. Single source of truth for pattern **categories** is `paint-booth-1-data.js` → `PATTERN_GROUPS`. Pattern **definitions** (id, name, desc, swatch) are in `PATTERNS`; backend texture/paint live in `shokker_engine_v2.py` (PATTERN_REGISTRY) and `engine/expansion_patterns.py` (expansion IDs).

---

## 1. Decades — 50s / 60s / 70s / 80s / 90s — TOTAL REWORK

**Current state**
- **50s:** Image patterns only (atomicstarburst_*, diceroll_*, drivein_*, hotrodflame_*) — 12 entries.
- **60s:** Image only (clockwork, dooflower, groovy, hippie, peace_*) — 9 entries.
- **70s:** Image only (breaker, diamondknot, discofever, groovygeometry) — 8 entries.
- **80s:** Image only — 4 entries (radbell, synthwave_*). Feels thin.
- **90s:** Image only — 2 entries (grungehex, grungescratch). Very thin.

**Problems**
- 80s/90s are underfilled; no procedural decade options in the picker.
- Expansion already has procedural **decade_50s_***, **decade_60s_***, … **decade_90s_*** in `engine/pattern_expansion.py` (NEW_PATTERN_IDS) and `engine/expansion_patterns.py`, but they are **not** in PATTERN_GROUPS under "Decades — 50s" etc., so they don’t show in the Decades sections.

**Suggested edits**

1. **Merge procedural Decades into PATTERN_GROUPS**
   - In `paint-booth-1-data.js`, under each "Decades — 50s/60s/70s/80s/90s" key in `PATTERN_GROUPS`, add the matching procedural IDs from expansion (see `engine/pattern_expansion.py` NEW_PATTERN_IDS).
   - **50s:** Add `decade_50s_starburst`, `decade_50s_bullet`, `decade_50s_diner_curve`, `decade_50s_tailfin`, `decade_50s_boomerang`, `decade_50s_scallop`, `decade_50s_rocket`, `decade_50s_classic_stripe`, `decade_50s_diamond`, `decade_50s_chrome_line` (keep existing image IDs or trim duplicates by feel).
   - **60s:** Add `decade_60s_flower`, `decade_60s_peace_curve`, `decade_60s_mod_stripe`, `decade_60s_opart_ray`, `decade_60s_gogo_check`, `decade_60s_lavalamp`, `decade_60s_wide_stripe`, `decade_60s_thin_stripe`, `decade_60s_woodstock`, `decade_60s_swirl`.
   - **70s:** Add `decade_70s_disco`, `decade_70s_patchwork`, `decade_70s_bicentennial`, `decade_70s_funk_zigzag`, `decade_70s_shag`, `decade_70s_studio54`, `decade_70s_bell_flare`, `decade_70s_earth_geo`, `decade_70s_orange_curve`, `decade_70s_sparkle`.
   - **80s:** Add `decade_80s_neon_hex`, `decade_80s_memphis`, `decade_80s_my_little_friend`, `decade_80s_synth_sun`, `decade_80s_yo_joe`, `decade_80s_outrun`, `decade_80s_pixel`, `decade_80s_acid_washed`, `decade_80s_pastel_zig`, `decade_80s_vapor`.
   - **90s:** Add `decade_90s_grunge`, `decade_90s_trolls`, `decade_90s_alt_cross`, `decade_90s_geo_minimal`, `decade_90s_rave_zig`, `decade_90s_chrome_bubble`, `decade_90s_y2k`, `decade_90s_tama90s`, `decade_90s_dot_matrix`, `decade_90s_floppy_disk`.

2. **Add PATTERNS entries for any expansion decade ID** that isn’t already in the `PATTERNS` array (so the picker has name/desc/swatch). Match names/descriptions to the era (e.g. "50s Tailfin", "80s Outrun", "90s Y2K").

3. **Optional:** Add a **PATTERN_SECTION_ORDER** (or equivalent) so "Decades — 50s" through "Decades — 90s" appear in order in the picker instead of alphabetically mixed with other groups. If the UI currently uses `Object.keys(PATTERN_GROUPS).sort()`, introduce a separate ordered list for pattern section order and use it where the pattern picker is built (`paint-booth-2-state-zones.js`).

4. **Image assets:** Keep existing image-based Decades; consider adding more image patterns per decade later (e.g. more 80s/90s PNGs in `assets/patterns/80s/`, `90s/`) and their entries in PATTERNS + PATTERN_GROUPS.

---

## 2. Flames — 5 Categories, Plenty of Variety

**Current sections**
- **Flames — Classic:** classic_hotrod, pinstripe_flames, fire_lick, fireball, torch_burn  
- **Flames — Modern & Aggressive:** blue_flame, hellfire, inferno, wildfire, nitro_burst  
- **Flames — Tribal & Flowing:** tribal_flame, flame_fade  
- **Flames — Ghost & Fade:** ghost_flames, ember_scatter  
- **Flames — Expansion:** long_flame_sweep, short_flame_lick, flame_panel_edge, … (20 IDs)

**Texture variety (already repointed in engine)**
- Classic: `texture_flame_sweep` (classic_hotrod), `texture_flame_tongues` (fire_lick), `texture_flame_ball` (fireball), `texture_flame_teardrop` (torch_burn), `texture_pinstripe_diagonal` (pinstripe_flames).
- Modern: `texture_flame_aggressive` (blue_flame, hellfire), `texture_flame_wild` (inferno, wildfire).
- Tribal/Flowing: `texture_flame_tribal_curves` (tribal_flame), `texture_flame_smoke_fade` (flame_fade).
- Ghost: `texture_plasma_soft` (ghost_flames); ember_scatter uses expansion/ember.

**Suggested edits**

1. **Spread flame IDs across more distinct texture_fns** so no section is dominated by one look. In `shokker_engine_v2.py` PATTERN_REGISTRY:
   - Give **hellfire** and **blue_flame** different textures (e.g. keep one `texture_flame_aggressive`, other `texture_flame_slash` or `texture_flame_ribbon`).
   - Give **inferno** and **wildfire** different textures (e.g. one `texture_flame_wild`, one `texture_flame_aggressive` or `texture_flame_ghost_soft`).
   - Tribal & Flowing: consider adding one more procedural from engine (e.g. a pattern that uses `texture_flame_ribbon` or `texture_flame_teardrop`) so the section has three distinct looks.

2. **Expansion flames:** In `engine/expansion_patterns.py`, ensure **Flames — Expansion** IDs (long_flame_sweep, short_flame_lick, flame_panel_edge, …) call **engine texture_flame_*** variants where possible (e.g. delegate to `texture_flame_sweep`, `texture_flame_ribbon`, `texture_flame_tongues`, `texture_flame_teardrop`, etc.) instead of a single shared flame texture, so each expansion flame variant looks different.

3. **Rename or subdivide (optional)** for clarity:
   - "Flames — Classic" = hot rod / vintage sweep and tongues.
   - "Flames — Modern & Aggressive" = high-contrast, sharp, blue/white tips.
   - "Flames — Tribal & Flowing" = curved, tattoo-style, smoke fade.
   - "Flames — Ghost & Fade" = subtle, transparent, ember.
   - "Flames — Expansion" = all the long/short/panel/belt/fishtail/teardrop/arrow/layered/ribbon/slash/overlay/core/smoke/tribal wide/fine/flow/fade/ember/smoke variants.

4. **PATTERN_GROUPS:** Optionally move 1–2 IDs between sections so each of the 5 has a balanced mix of textures (e.g. one "ghost" style in Ghost & Fade, one in Modern if it fits).

---

## 3. Racing & Motorsport — TOTAL REWORK

**Current list (24 IDs)**  
aero_flow, asphalt_texture, brake_dust, checkered_flag, drift_marks, finish_line, lap_counter, pit_lane_marks, podium_stripe, racing_stripe, rev_counter, rooster_tail, rpm_gauge, skid_marks, speed_lines, sponsor_fade, starting_grid, tire_smoke, tire_tread, track_map, trophy_laurel, turbo_swirl, victory_confetti, wind_tunnel.

**Suggested edits**

1. **Group into sub-themes** (either as separate PATTERN_GROUPS keys or as one "Racing & Motorsport" with a logical order):
   - **Stripes & lines:** racing_stripe, podium_stripe, aero_flow, speed_lines, wind_tunnel, lap_counter, pit_lane_marks, sponsor_fade.
   - **Flags & finish:** checkered_flag, finish_line, starting_grid.
   - **Track & tires:** tire_tread, tire_smoke, skid_marks, drift_marks, asphalt_texture, brake_dust, rooster_tail.
   - **Instruments & data:** rev_counter, rpm_gauge, track_map.
   - **Victory & power:** trophy_laurel, victory_confetti, turbo_swirl.

2. **Ensure variety:** Many of these already use different textures (pinstripe_vertical/diagonal/fine, grating_heavy, houndstooth_bold, wave_*, etc.). Audit PATTERN_REGISTRY so no two racing patterns that should feel different share the same `texture_fn`. Add or repoint to **texture_chevron_bold**, **texture_chevron_fine**, **texture_pinstripe_***, **texture_grating_heavy** as needed.

3. **Names/descriptions:** In `PATTERNS`, give each ID a short, racing-specific desc (e.g. "Pit lane boundary stripes", "Checkered finish line band", "Tire tread contact patch").

4. **Optional new IDs:** If you add more procedural patterns (e.g. "pole_position_stripe", "pit_stop_chevron"), add them to PATTERN_REGISTRY, PATTERNS, and the appropriate PATTERN_GROUPS section.

---

## 4. Skate & Surf — Total Rework

**Current list (12 IDs)**  
bamboo_stalk, board_wax, grip_tape, halfpipe, hibiscus, ocean_foam, palm_frond, rip_tide, surf_stripe, tiki_totem, tropical_leaf, wave_curl.

**Suggested edits**

1. **Split or label by subculture:**
   - **Surf:** wave_curl, rip_tide, ocean_foam, board_wax, surf_stripe, bamboo_stalk, palm_frond, tropical_leaf, tiki_totem, hibiscus (beach/tropical).
   - **Skate:** halfpipe, grip_tape; optionally move or add patterns that read as deck graphics, street, or ramp (e.g. bold stripes, grip texture, concrete/curb).

2. **Variety:** These already use texture_wave_*, texture_pinstripe_*, texture_ripple_*, texture_tribal_* in the engine. Ensure no two surf/skate patterns that should feel distinct share the same texture. Consider adding 1–2 procedural variants (e.g. "deck_weave", "wave_barrel") in the engine and PATTERN_REGISTRY, then add to PATTERNS and PATTERN_GROUPS.

3. **Descriptions:** Make PATTERNS descriptions clearly surf or skate (e.g. "Surfboard wax circles", "Halfpipe curve cross-section", "Tropical palm frond").

4. **PATTERN_GROUPS:** Either keep one "Skate & Surf" section with a clear order (e.g. surf first, then skate) or split into "Surf & Beach" and "Skate & Street" if you want two collapsible sections.

---

## 5. Music & Band — Total Rework (Think It Through)

**Current state**
- **Music & Band** (PATTERN_GROUPS): 10 procedural IDs — music_lightning_bolt, music_wing_sweep, music_script_curve, music_skull_abstract, music_arrow_bold, music_star_burst, music_circle_ring, music_slash_bold, music_chain_heavy, music_flame_ribbon. Many are generic (stripes, starburst, rings) and could be any genre.
- **Music Inspired:** Image-based (AC/DC bolt, artist, darkside, ram seal, smilexx, van strat) — band/artist-inspired assets.

**Problems**
- "Music & Band" feels like a grab-bag of shapes (bolt, wing, script, skull, arrow, star, circle, slash, chain, flame) without a clear music narrative.
- No genre distinction (metal, rock, punk, hip-hop, electronic, blues, jazz).
- No instrument or stage tropes (vinyl, guitar, drums, mic, neon stage, crowd, tour bus).

**Suggested direction — Music as a real category**

1. **Sub-themes (pick and implement in PATTERN_GROUPS + expansion):**
   - **Band / logo style:** Lightning bolt, skull, wings, bold type-like stripes, crests. Keep or rename: music_lightning_bolt, music_skull_abstract, music_wing_sweep, music_arrow_bold, music_slash_bold.
   - **Instruments & vinyl:** Guitar pick shape, fret/string lines, drum skin texture, vinyl groove concentric rings, mic silhouette. New IDs (e.g. music_vinyl_groove, music_pick_shape, music_fret_lines) with dedicated texture in expansion or engine.
   - **Stage & tour:** Neon grid, spotlight rays, crowd silhouette, marquee stripes. New or repurpose: e.g. music_neon_arena (use engine hologram/plasma), music_spotlight_rays (starburst/radial).
   - **Genre flavor:** Metal (chains, spikes, dark geometric); punk (safety pin, plaid, ransom-note slash); electronic (waveform, spectrum, grid); blues/jazz (smooth curves, brass texture). Implement as new music_* variants in expansion_patterns and NEW_PATTERN_IDS.

2. **Concrete next steps**
   - **Rename** existing Music & Band entries so they read as music (e.g. "Bolt Logo", "Skull Motif", "Wing Sweep", "Script Curve", "Bold Slash", "Star Burst", "Ring Motif", "Heavy Chain", "Flame Ribbon"). Descriptions in PATTERNS should say "band logo style", "stage graphic", etc.
   - **Add** 5–10 new music_* IDs in `engine/pattern_expansion.py` (NEW_PATTERN_IDS) and implement them in `engine/expansion_patterns.py` (_texture_music_variant / _paint_expansion): e.g. music_vinyl_groove, music_neon_stage, music_metal_chain, music_waveform_bars, music_spotlight_rays. Use engine textures (ripple, wave, starburst, circuit, hologram) or new small helpers in expansion_patterns.
   - **Add** matching entries in `paint-booth-1-data.js` PATTERNS and add those IDs to PATTERN_GROUPS under "Music & Band" (or under new subsections like "Music — Logos & Icons", "Music — Stage & Neon", "Music — Instruments").
   - **Keep** "Music Inspired" as the image-based band/artist section (AC/DC, etc.); optionally rename to "Music Inspired — Bands & Artists" and keep it separate from the procedural "Music & Band" so the category isn’t lazy rehashing of the same shapes.

3. **Avoid**
   - Reusing the same texture for every music pattern (e.g. not all lightning/star/slash).
   - Purely generic names (e.g. "Bold Slash") without a one-line music context in the description.

---

## 6. Where to Edit (Quick Reference)

| Goal | File | What to change |
|------|------|----------------|
| Which pattern IDs appear in which category | `paint-booth-1-data.js` | `PATTERN_GROUPS` object (keys = section names, values = arrays of pattern IDs). |
| Pattern display name, description, swatch | `paint-booth-1-data.js` | `PATTERNS` array (id, name, desc, swatch; optional swatch_image). |
| Backend texture/paint for procedural patterns | `shokker_engine_v2.py` | `PATTERN_REGISTRY` (texture_fn, paint_fn per id). |
| Expansion pattern list | `engine/pattern_expansion.py` | `NEW_PATTERN_IDS`. |
| Expansion pattern look (decade, music, flame, astro) | `engine/expansion_patterns.py` | `_texture_expansion`, `_paint_expansion`, and family helpers. |
| Pattern section order in picker | `paint-booth-2-state-zones.js` (and any copy) | Where pattern picker is built; switch from `Object.keys(PATTERN_GROUPS).sort()` to an explicit order list for pattern sections if you add one in 1-data.js. |

---

## 7. Order of Implementation (Suggested)

1. **Flames** — Quick win: repoint 2–3 more flame IDs in PATTERN_REGISTRY so Classic/Modern/Tribal/Ghost/Expansion each use multiple distinct texture_fns; optionally wire expansion flame variants to engine texture_flame_* in expansion_patterns.
2. **Decades** — Add procedural decade_* IDs to PATTERN_GROUPS and ensure all have PATTERNS entries; add PATTERN_SECTION_ORDER if desired.
3. **Racing & Motorsport** — Reorder and optionally subgroup in PATTERN_GROUPS; audit textures; tighten names/descriptions in PATTERNS.
4. **Skate & Surf** — Reorder, clarify surf vs skate in PATTERNS; optionally add 1–2 new patterns.
5. **Music & Band** — Deep rework: new music_* IDs, new branches in expansion_patterns, rename/describe existing entries, expand PATTERN_GROUPS with subsections or a single curated list.

This plan keeps textures and categories aligned and gives each section a clear identity without a hard cap on how many variants you add.
