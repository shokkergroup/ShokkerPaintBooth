# ★ NEON UNDERGROUND FULL REBUILD — 20 redesigned + 5 new = 25 (owner mandate 2026-08-27)

**Owner's brief:** "Totally REBUILD NEON UNDERGROUND and the 20 finishes it has plus invent 5 new
one's for a total of 25. You can rename/redo the one's already there… Make a couple of the finishes
at least racing specific. Checkered flag elements, speed lines, anything that gives it just a hint
of auto racing feel." Framed as a gentleman's game vs Codex's Fractured Wilds rebuild; owner judges.

**Lane state doc** — per-run evidence lives HERE, not the wiki (lean rules). Claude owns this lane.

## Owner calibration (2026-08-27, from his Wilds standouts) — THE DESIGN LAWS

> "The MAIN THING is we can't have too many artifacts/crap in the designs… Some of the designs have
> too much garbage… Just too gritty. We don't need too much noise. SOME is ok or on SOME designs —
> but not all of them."

1. **CLEAN LINES FIRST.** Crisp geometry, smooth glow falloffs. Noise/grit is a RATIONED spice —
   only where the story earns it (asphalt, concrete, graffiti), structured even there. (His Nacre
   Brick note: "if the lines were cleaner it would be very very cool.")
2. **BRIGHTS MUST BE BRIGHT.** Dark grounds with genuinely luminous accents popping off them.
   (Chalcopyrite: "if the blues were popping brighter off the darker color… it would be electric";
   Crackle Eyeshine: "too dark and the brights aren't bright enough.")
3. **INTRICACY FROM PATTERN, NOT NOISE.** Fine 8–32px CLEAN elements — ticks, tread blocks,
   checker cells, tube segments, scales. (Claw Rake: "the intricate PATTERN… is awesome.")
4. **SPEC FOLLOWS THE PAINT** — married by construction, one build pass. (Claw Rake's original
   spec "didn't follow the paint design" = the canonical anti-pattern.)
5. **SPEC COLOR MOVEMENT** — 8-tier quantile ladders per channel, wide spans, per-feature tiers.
   (Cyan Spineball: "tons of spec color movement which is good.")
6. Amber Moldring benchmark: chroma shift + "a lot of little details."

Category identity: **blacklight culture as a PLACE** — dive bar, drag strip at 1 a.m., security
corridor, flooded drain, 90s arcade. Not "glowing lines."

## Pre-rebuild state (recon 2026-08-27)

- 10 bases (`engine/paint_v2/neon_underground.py`): color-swap variants of one glow carrier —
  names ARE colors. M7 55.8–75.3; 4 under the 75 floor; zero near the 85 ship-bar.
- 10 `neon2_*` monolithics (`engine/expansions/neon_catalog_2026.py` ← `neon_math.py`): never
  measured (no scorecard/M7 rows); several topologies now collide with 2026-08-25 anime work
  (Neo-Tokyo Glow, Mecha Hologrid, Cyber Glitch) + Tactical Cyberpunk + carbon hexes.
- No owner-review override module covers neon ids (checked — the anime SPB-30 trap does NOT apply).
- Owner's own concept bank recovered from git (`NEON_UNDERGROUND_IDEAS.html`, deleted working-tree):
  50 names incl. a street-racing section — slate draws from it.

## Architecture

NEW library `engine/paint_v2/neon_math_v2.py` (old `neon_math.py` untouched until wiring swaps —
zero-breakage window if the owner restarts mid-lane). Same proven contract as anime_math:
`_b_<key>(shape, seed) -> {'rgb': f32 (h,w,3) 0..1, 'spec': f32 (h,w,3) 0..255 M/R/CC}` in ONE
pass from shared geometry; `build()` lru-cached; features scale h/2048; deterministic; ≤~2.5s @2048.
Neon-specific core: cv2-rasterized geometry → distanceTransform fields → clean tube/glow shading;
subwindow polar stamping for ring/arc systems; `_qmap` 8-tier quantile ladders for M/R/CC.

Wiring (later phase, ids stable so saved projects survive): bases keep paint_/spec_ fn names in
`neon_underground.py` → wrappers over neon_math_v2; monolithics in `neon_catalog_2026.py`; JS
specials list 10→15 + display entries + base renames; NEW fail-closed gate
`tests/regression_neon_uniqueness_test.py` cloned from the anime gate; whole-catalog uniqueness at
wiring time via `spb_catalog_fingerprint` + `spb_uniqueness_gate` (dev-phase gate is pairwise
in-set — cross-catalog MUST NOT be silently skipped at wiring).

## THE 25 — concept ledger (all mechanisms distinct; ★ = racing-specific)

| # | structure key | id | display | dominant process |
|---|---|---|---|---|
| 1 | blacklight_reactor | neon_blacklight | Blacklight Reactor | UV two-population physics: muted day substrate, rare fluorescent bloom clusters w/ halation rings |
| 2 | hazard_sector | neon_cyber_yellow | Hazard Sector | torn caution-tape collage — layered chevron strips, peel curls, adhesive ghosts |
| 3 | afterhours_inversion | neon_dual_glow | Afterhours Inversion | positive/negative glow interlock — dark geometry rimmed magenta one flank, cyan the other |
| 4 | lightning_cage | neon_electric_blue | Lightning Cage | arcs pinned between insulator studs, corona fuzz, scorch points |
| 5 | vacancy_motel | neon_ice_white | Vacancy Motel | dead-tube americana — white tube runs w/ failing segments, flicker ghosts, rust-bled mounts |
| 6 | sodium_tunnel | neon_orange_hazard | Sodium Tunnel | underpass sodium-vapor cones pooling on stained concrete, joint seams, conduits |
| 7 | cocktail_hour | neon_pink_blaze | Cocktail Hour | bent-glass sign anatomy — double-tube outlines, glass highlights, transformer wiring |
| 8 | spectrum_coil | neon_rainbow_tube | Spectrum Coil | ONE continuous tube coiling the canvas, hue cycling by arc-length, occluded crossovers |
| 9 ★ | redline_tach | neon_red_alert | Redline Tach | tachometer sweep-arc systems into redline sectors, tick combs, needle-blur ghosts, checker ribbon |
| 10 | toxic_runoff | neon_toxic_green | Toxic Runoff | phosphorescent drain-water threading a cracked-asphalt web, meniscus edges, drips |
| 11 | last_call | neon2_sign_tubes | Last Call | dive-bar sign graveyard — glass fragments lit / dying / dead, mount hardware |
| 12 | mainframe | neon2_circuit_city | Mainframe | physical PCB — solder-blob specular field, pulsing trace ribbons, via holes (NOT a hologram grid) |
| 13 | laser_maze | neon2_laser_web | Laser Maze | security beam fans between anchor nodes, dust-lit volumetrics, breach scorch |
| 14 | miami_heat | neon2_rain | Miami Heat | ground-level wet asphalt mirroring unseen neon — puddle ellipses, anisotropic smear (no city, no windows) |
| 15 | graffiti_burner | neon2_splatter | Graffiti Burner | UV throw-up layers — fat-cap outlines, fill fades, drips, slaps, buffed ghosts (grit ration HERE) |
| 16 | grid_runner | neon2_wireframe | Grid Runner | outrun terrain-RELIEF wireframe w/ elevation glow ridges (vs Hologrid's flat CAD planes) |
| 17 ★ | boost_spool | neon2_plasma_tubes | Boost Spool | turbo plumbing — pipe runs w/ clamp rings, glass spool-vortex sections, BOV blooms, heat-wrap weave |
| 18 | serpent_coil | neon2_honeycomb | Serpent Coil | backlit snake-scale lattice flowing along slither curves — organic, not hex tiling |
| 19 | heartbeat | neon2_flow_tubes | Heartbeat | EKG pulse rivers — QRS spikes, phosphor decay trails, grid-paper ghost |
| 20 | arcade_carpet | neon2_synthwave_sun | Arcade Carpet | 90s blacklight carpet — cosmic squiggles, bang shapes, planet rings, confetti on deep purple |
| 21 ★ | quarter_mile | neon2_quarter_mile (NEW) | Quarter Mile | night drag strip — christmas-tree light stacks, timing beams, rubber laydown arcs, SPEED-WARPED CHECKER band, light-pool reflections |
| 22 ★ | burnout_ring | neon2_burnout_ring (NEW) | Burnout Ring | overlapping donut scars — annular TREAD-BLOCK stamps, blacklight-fresh rubber rims, underglow smoke wisps |
| 23 | phantom_koi | neon2_phantom_koi (NEW) | Phantom Koi | blacklight irezumi koi stream — glowing silhouettes in flow lines, scale micro-detail |
| 24 | dragon_drift | neon2_dragon_drift (NEW) | Dragon Drift | neon dragon ribbon coiling through drift-smoke light streaks |
| 25 | equalizer | neon2_equalizer (NEW) | Equalizer | spectrum-analyzer bar field — peak-hold caps, mirrored bass wells, level-ladder chroma |

**Collision watchlist** (fingerprint arbitrates; ≥0.80 = concept redone, not tweaked):
9 vs 22 (both annular → tick-comb thin arcs vs fat block-stamp annuli + smoke), 12/16 vs anime
mecha_hologrid, 14 vs anime neo_tokyo_glow, 20 vs anime retro_broadcast, 18 vs insect/carbon hex,
8 vs 17 (tubes → single hue-cycling coil vs pipe network w/ hardware), 2 vs anime mecha chevrons,
9/21 checker elements vs anime manga_page panels. Cross-catalog gate runs at wiring.

**Identity guardrails:** no numerals/text/sponsor marks (spec-map app), omnidirectional designs
(UV reversed/rotated per car), design 2–4x finer than the swatch suggests.

## Progress log (newest first)

- 2026-08-27 LANE PARKED — owner: ditch this experiment for now, it failed. Racing four passed all
  mechanical gates after 2 correction rounds but not the owner eye (board verdict: gauges, cable
  spaghetti, checker banners, ring wallpaper). NOTHING WIRED — neon_math_v2.py standalone, old neon
  modules untouched, zero shipped impact. If retried: mechanical laws below stand; the CONCEPTS
  need rethinking (scene-derived motifs kept reading as props, not paint — start from material
  processes, not places).


- 2026-08-27 OWNER CORRECTION #2 — THE SCALE LAW (binding for all 25): the first racing four were
  POSTER COMPOSITIONS (7 fender-size gauges on void). Owner: canvases cover ENTIRE CARS, no dead
  space, tons of detail, compare Wilds. Rebuilt as FIELDS: 3 size tiers of motifs (max ~160px),
  8-32px working detail, luminous textured grounds (brushed sheen bands), micro-tiers (LED lamps,
  rivet glints, ghost rings). NEW EMPIRICAL GATE calibrated on accepted finishes (anime refs score
  covP99=1.00, covP90=1.00): floors covP99>=0.98 AND covP90>=0.90 (p90 means >=10 percent of EVERY
  256px cell is real bright content — washes cannot fake it, only structure counts). All four now:
  covP99=1.00, covP90 0.91-0.94, worst pairwise sim 0.32, spec stds 33-88. Render times measured
  clean at 1.9-3.0s; final run timed under a 100%-loaded machine (owner racing in iRacing) so the
  wiring-phase load-normalized gate re-verifies. LESSON: luma floors — magenta/violet is luma-dim,
  white-hot cores + real structure carry cells, not chroma washes.


- 2026-08-27 RACING FOUR BUILT + dev-gated (awaiting owner eye): redline_tach 2.55s/cov.66/fin.62,
  boost_spool 2.76s/.63/.54, quarter_mile 2.48s/.69/.51, burnout_ring 2.53s/.70/.55; spec stds all
  >=18 w/ full spans; pairwise uniqueness worst 0.33; 0 axis-seam lines on all four (new mechanical
  square-seam detector). KEY LESSONS: (1) subwindow glow terms (pool AND halo) must smoothstep to
  zero inside the window or they print square seams; (2) per-feature rng streams — background
  features stealing layout draws reshuffle the whole composition; (3) chaikin-smooth every organic
  polyline (elbows read as kinks); (4) magenta/violet is luma-dim — blacklight brights need
  white-hot cores to register; (5) full-canvas per-arc field math is the perf killer — share
  direction fields, band-box the computations. neon_math_v2.py is NOT yet wired/synced (deliberate
  zero-breakage window; wiring turn adds manifest + registries + JS + cross-catalog gate).


- 2026-08-27 LANE OPENED. Recon + owner calibration banked. Racing four (redline_tach,
  boost_spool, quarter_mile, burnout_ring) authored first in neon_math_v2.py; dev gate =
  pairwise uniqueness + coverage + fineness + render-time + spec-stds; evidence renders to
  `_neon_rebuild_work/` (append-only NEON_REBUILD_PROGRESS.jsonl).
