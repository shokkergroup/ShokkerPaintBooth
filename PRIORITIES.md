# SPB Dev Agent — Priorities

This file is how Ricky steers the agent. The agent reads this BEFORE choosing what to work on each heartbeat.

**Last updated by Ricky:** 2026-03-29

---

## Current Focus

MAJOR EXPANSION PUSH — Work these in order, one heartbeat at a time:

### Priority 5: Full Category Base Audit + Improvements ✅ COMPLETE (2026-03-30)

**COMPLETED 2026-03-30 in a direct Claude Code session.** All 16 categories audited. 18 registry fixes + ~100 code-level GGX floor fixes. See CHANGELOG.md SESSION SUMMARY.

**QA Agent:** Verify the fixes. Check 3-copy sync. Flag any remaining issues to `QA_REPORT.md`.
**Dev Agent:** After QA flags issues, implement all improvements. Three-copy sync required on every file touched.

#### Categories to Audit (in order):

**PARADIGM** — 18 bases. These should be the most extreme, wild, physically impossible finishes.
- Check: are M/R/CC values genuinely exotic? Do paint functions deliver on the concept?
- Flag any PARADIGM base that feels like it could belong in a regular category

**★ Angle SHOKK** — 14 bases (angle-resolved micro-spec). Each should respond to viewing angle.
- Check: does each base actually have color-shift / angle-dependent behavior in its paint_fn?
- Flag any that are just static finishes with no angle-dependent character

**Candy & Pearl** — 17 bases. Deep, layered, candy-coat / pearl / iridescent character.
- Check: M values (candy needs high M=150+), CC must be 16–26 range (NOT 100+)
- Check: G channel — all candy/pearl need G≥15 (GGX quirk floor)
- Flag any with wrong CC direction or flat G=0 paint

**Ceramic & Glass** — 8 bases. These are dielectric — M should be 0–20 (not metallic).
- Check: M values. Ceramic/glass is NOT metallic. Flag any M>30.
- Check: CC values. Ceramic is high-gloss (CC=16–30) or semi-gloss. Matte ceramic is CC=50–80.

**Extreme & Experimental** — 10 bases. Should be visually bizarre.
- Check: are any of these just "slightly different metallic"? They should be genuinely extreme.
- Flag any that don't live up to the "experimental" concept.

**Industrial & Tactical** — 17 bases. Cerakote, duracoat, powder coat, military finishes.
- Check: M values (most should be M=0–60, low metallic), R values (most matte/satin, R=80–180)
- Flag any that are too shiny/glossy for a "tactical" finish

**Metallic Standard** — 20 bases. The bread-and-butter metallic flakes and solids.
- Check: M values (should be M=100–240 for metallic flakes)
- Check: pearl vs flake distinction — pearl needs iridescent paint_fn, flake needs sparkle

**OEM Automotive** — 10 bases. Factory-accurate car finishes.
- Check: are M/R/CC values plausible for actual production cars?
- Ambulance white should be very flat (R=200+). Ferrari rosso is semi-metallic (M=60–100).

**Premium Luxury** — 10 bases. Bentley, Bugatti, Koenigsegg tier.
- Check: these should have very high-spec paint functions — NOT paint_none
- Flag any luxury base using paint_none or a generic paint_fn

**Pro Grade (Atelier)** — 10 cc_* custom colors. These are pre-mixed color washes.
- Check: are M/R/CC values appropriate for a "pro grade" painted effect?

**Racing Heritage** — 11 bases. Vintage race car character.
- Check: race_day_gloss should be high gloss (CC=16–22), barn_find should look weathered
- Flag any racing base that doesn't match its concept

**Satin & Wrap** — 10 bases. Vinyl wrap finishes — satin, matte, color-flip.
- Check: M values (wrap is dielectric, M should be 0–40)
- Check: color_flip_wrap must have a color-shift paint_fn

**Shokk Series** — 30 bases. SHOKK color-shift bases from SHOKK v2.
- These are loaded from shokker_engine_v2.py SHOKK_V2 — check the loading mechanism is correct
- Check: do all 30 show up in the picker? Are they all genuinely distinct?

**Weathered & Aged** — 17 bases. Patina, rust, oxidation, weathering.
- Check: M values (weathered metal should NOT be high metallic — oxidation removes shine)
- Check: R values (weathered = HIGH roughness R=150–250)
- Flag anything too shiny for a "weathered" look

**Chrome & Mirror** — 15 bases (now including chromaflair).
- Check: all chrome needs M=240–255, R=2–8, CC=16–20
- Check: chromaflair (newly added) — does it have color-shift character?
- Flag any chrome with R>30 (that's not chrome anymore)

**Exotic Metal** — 15 bases (now including anodized_exotic, xirallic).
- Check: anodized_exotic and xirallic — are their spec values and paint_fn correct?
- Check: diamond_coat — should have very specific CC behavior (clearcoat over crystal)

**Carbon & Composite** — 10 bases. Carbon fiber, kevlar, graphene etc.
- Check: M values (carbon fiber is NOT metallic, M=0–20 unless it has metallic flake coat)
- Check: are paint functions delivering visible weave texture?

**Foundation** — 33 bases. The baseline finishes every user starts with.
- Check: are all "f_*" (foundation) entries using appropriate base values?
- Check: are the descriptions accurate for what the values actually do?

#### Specific Issues to Investigate:
- **`oil_slick`** — is it in a group? (it's one of the exotic bases, check placement)
- **`thermal_titanium`** — same question
- **`galaxy_nebula`** — same question
- **`alubeam`** — listed in Chrome & Mirror but Alubeam is really a metallic base (Standox Alubeam). Should it be in Metallic Standard instead?
- **Pro Grade (Atelier) spec functions** — the cc_* color washes: do they have actual spec functions or just M/R/CC constants?

#### What to Write in QA_REPORT.md:
For each category, write:
```
## CATEGORY: [Name]
- Total bases: N
- Issues found: N
- [FLAG-CAT-001] <description> — Severity: HIGH/MED/LOW
  - Base: <id>, Problem: <what's wrong>, Fix: <what to change>
```

#### After QA Audit — Dev Agent Fixes:
- Implement ALL HIGH and MEDIUM severity fixes
- For spec function fixes: update all 3 copies of the relevant .py file
- For BASE_REGISTRY value fixes: update all 3 copies of base_registry_data.py
- For paint function improvements: update relevant paint_v2 .py files

### Priority 1: Add 100 New Paint Patterns (ADDITIVE ONLY)
- DO NOT change or remove any existing patterns
- Add 100 new intricate, highly detailed pattern designs
- Fill gaps in existing categories AND create new categories
- Every pattern must be the highest level of detail possible — striking, intricate, designed to look incredible on car paints
- Think: geometric tessellations, tribal circuits, biomechanical, Art Deco, Celtic knotwork, Japanese wave/cloud, Damascus steel, circuit board traces, fractal flames, sacred geometry, carbon weave variants, honeycomb morphs, topographic, reptile scales, lace/filigree, baroque scrollwork, stained glass, mosaic tiles, chainmail, wood grain burls, marble veining, brushed metal hatching, interference patterns, op-art illusions, noise gradients, Voronoi cells, Penrose tiling, Escher-style tessellations
- Break this into batches — do 10-15 per heartbeat session, grouped by category
- Each pattern needs proper registration in the pattern system so it shows up in the UI

### Priority 2: Add 100 New Spec Overlay Patterns ✅ COMPLETE — 100/100 spec overlay patterns
- Same quality bar — intricate, detailed, designed for spec map work
- These control how chrome/matte/metallic channels behave
- **APPROVED (from Research Agent RESEARCH-005):** Organize by WHICH CHANNEL they target:
  - **Roughness Patterns (Green channel):** directional brushed lines, radial brushed, woven fabric, crosshatch, wood grain — simulate physical surface texture direction
  - **Metallic Patterns (Red channel):** cellular/Voronoi, hexagonal flakes, sparkle noise, metallic islands — simulate metallic flake distribution
  - **Clearcoat Patterns (Blue channel):** smooth gradients, vignette, panel-edge fade — simulate clearcoat pooling/dripping at edges
  - **Full-Channel Patterns:** complex patterns that drive all 3 channels simultaneously (like carbon fiber weave)
- This teaches users correct usage while making it easy to find the right pattern

### Priority 3: Spec Overlay Preview System Overhaul ✅ COMPLETE (2026-03-29)
### Priority 3b: Smart Thumbnail Caching System ✅ COMPLETE (2026-03-29)
- Static `/thumbnails/<path>` route (immutable cache, direct file I/O)
- Hash-manifest (`_manifest.json`): thumbnails only regenerate when function source changes
- `_prebake_spec_patterns()` daemon thread bakes 100+ spec thumbnails on startup
- JS updated to static URLs with onerror fallback to API endpoints
- `rebuild_thumbnails.py` now supports `--type spec`
- Phase 1 DONE: Category tab filtering in spec overlay picker (17 group tabs)
- Phase 2 DONE: Upgraded M/R/CC split thumbnail visualization (192x64, 3-panel labeled)
- Phase 3 DONE: New /api/spec-pattern-preview-metal endpoint (128x128 realistic metal surface)
- Phase 4 DONE: New /api/spec-preview-composite endpoint (256x128 stack over base finish)
- Phase 5 DONE: Dedicated SPEC PREVIEW collapsible panel with 4 base presets + live canvas
- Phase 6 DONE: Grid upgraded to 4 columns, 48x48px thumbnails, full tooltip on hover

### Priority 4: UI Modernization Pass ✅ COMPLETE (2026-03-29)
- Design token system added to :root (--accent-p4, --bg-*, --border-*, --text-*, --radius-*, --shadow-panel)
- Button system: .btn-primary, .btn-secondary, .btn-icon classes
- Zone selector tabs: active gradient + accent bar + color dot indicator
- Finish picker modal: backdrop blur, shadow, hover-lift cards
- Custom dark scrollbars (6px, rgba opacity), toast slide-in + colored left border
- Panel headers: letter-spacing 0.12em, active sections get left accent bar
- All 3 CSS copies synced

## Do NOT Touch (Off-Limits)

- Do NOT modify or remove any existing patterns — only ADD new ones
- Do NOT change existing functionality — improvements and additions only
- V5 production build is completely off-limits

## CRITICAL BUGS — Fix Immediately

### [FLAG-CANDY-004] ✅ FIXED (2026-03-30 09:30) — `opal` CC=100→16
`paint_opal_v2`+`spec_opal` already auto-wired via `candy_special_reg.py` staging patch. Only CC needed fixing. All 3 copies.

### [FLAG-CANDY-005] ✅ FIXED (2026-03-30 09:30) — `satin_candy` CC=6→65
CC was below CC≥16 threshold, triggering metallised renderer path. CC=65 = satin sheen tier. All 3 copies.

### [FLAG-IND-003] ✅ FIXED (2026-03-30 09:30) — `velvet_floc` CC=0→245
CC=0 was triggering chrome/mirror renderer path. CC=245 = dead-flat maximum degradation (near vantablack). All 3 copies.

### [FLAG-IND-005] ✅ FIXED (2026-03-30 10:00) — `cerakote_pvd` CC=5→160, M=178→55
CC=5 triggered metallised renderer path. CC=160 = flat industrial tier. M=55 = semi-metallic TiN/TiAlN. R=174 correct, unchanged. All 3 copies.

### [FLAG-OEM-002] ✅ FIXED (2026-03-30 10:00) — `school_bus` paint_fn `paint_electric_blue_tint`→`paint_none`
Blue hue tint on Federal Standard 13432 chrome yellow = wrong color family. paint_none preserves correct yellow base. All 3 copies.

### [FLAG-IND-001] ✅ FIXED (2026-03-30 10:00) — `cerakote_gloss` M=100→45, R=15→55
M=45 = semi-metallic polymer (not near-chrome); R=55 = smooth polymer surface (not mirror). All 3 copies.

### [FLAG-IND-004] ✅ FIXED (2026-03-30 10:30) — `gunmetal_satin` moved from Industrial & Tactical → Metallic Standard
JS-only category reassignment in `BASE_GROUPS`. M=205 is clearly metallic (not industrial M=0–80). Now sits after `gunmetal` in Metallic Standard. All 3 `paint-booth-0-finish-data.js` copies.

### [BUG-WA-001 / WARN-GGX-006] ✅ FIXED (2026-03-30 16:00) — `spec_weathered_aged` CC=0 → CC=130
**QA verified (2026-03-30, Heartbeat 31):** All 3 copies of `engine/spec_paint.py` confirmed at L3103: `CC = np.where(rot < 0.4, 24.0, 130.0).astype(np.float32)`. Inline comment present. Fix consistent with WARN-GGX-001–005 precedent. ✓

### [BUG-CHROME-001] ✅ FIXED (2026-03-30 06:30) — chrome_mirror.py wired into base_registry_data.py
**Fixed by:** SPB Dev Agent. Added `from engine.paint_v2.chrome_mirror import (20 functions)` block to all 3 copies of `base_registry_data.py`. Updated all 10 chrome BASE_REGISTRY entries: chrome, black_chrome, blue_chrome, red_chrome, satin_chrome, antique_chrome, bullseye_chrome, checkered_chrome, dark_chrome, vintage_chrome — all now use correct v2 `paint_fn` + `base_spec_fn`. 583 lines of chrome physics now live in render pipeline.

### [BUG-EXOTIC-001] ✅ FIXED (2026-03-30 02:30) — Exotic Finishes Added to base_registry_data.py
**QA verified (2026-03-30 03:00):** All 3 copies of base_registry_data.py confirmed correct. chromaflair (M=210,R=12,CC=18), xirallic (M=170,R=20,CC=18), anodized_exotic (M=110,R=38,CC=45) all present with correct imports and registry values matching shokker_engine_v2.py exactly. ✓

---

## Known Issues to Investigate

### [BUG-SB-001] ✅ FIXED (2026-03-30) — Dead guilloché bodies removed from spec_patterns.py
Removed `guilloche_rose`, `engine_turning_square`, `engine_turning_hex`, `engine_turning_diagonal` from all 3 `spec_patterns.py` copies. ~60 lines of dead code eliminated. Live Batch B functions (guilloche_straight, guilloche_wavy, guilloche_basket, sunburst_rays, etc.) intact. All 3 copies.

### [WARN-CX-001] ✅ ALREADY FIXED (prior session) — Success print removed from FINISH_REGISTRY wiring
Verified 2026-03-30: only `print(f"[V2 FINISH_REGISTRY] v2 wire-in skipped: {_v2_fr_exc}")` remains (error path only, correct to keep). Success print was removed in heartbeat 36. All 3 copies confirmed clean.

### [CONCERN-CX-001] ✅ FIXED (2026-03-30) — `jelly_pearl` FINISH_REGISTRY now uses `spec_jelly_pearl`
Added `spec_jelly_pearl as _spec_jelly_pearl` to the candy_special import block. Changed `FINISH_REGISTRY["jelly_pearl"]` from `(spec_pearl, ...)` to `(_spec_jelly_pearl, ...)`. `spec_jelly_pearl` provides mica particle field + angle-shift noise M/R/CC vs generic `spec_pearl`. `FINISH_REGISTRY["pearl"]` correctly retains `spec_pearl`. All 3 `shokker_engine_v2.py` copies.

### [WARN-P3-001] ✅ FIXED (2026-03-29) All 4 spec overlay pickers now use identical system
Overlay pickers 2-4 upgraded to match picker 1: `spec-cat-tab-row` / `spec-cat-tab` / `specPickerCatTab()` / `data-category`, 4-column grid, 48×48px thumbnails, bounds-aware popup. All 3 JS copies synced.
**QA verified (2026-03-29 20:00):** All 4 pickers confirmed identical across all 3 JS copies. `data-spg=` fully removed from active code. ✓

### [WARN-P3-DCA-001] ✅ FIXED (2026-03-30) — Dead `specPickerTab()` + old tab CSS removed
Removed `specPickerTab()` function body (17 lines, zero callers) from all 3 JS copies. Also removed entire dead CSS block: `.spec-picker-tabs`, `.spec-tab-btn`, `.spec-tab-btn:hover`, `.spec-tab-btn.sp-tab-active` (37 lines) — all exclusively referenced inside the removed function. New `spec-cat-tab-row` / `spec-cat-tab` system is unaffected. All 3 JS + CSS copies.

### [WARN-SPEC-001] ✅ FIXED (2026-03-30 19:00) — `spec_tri_coat_pearl` unsafe shape unpack
Batched with WARN-SPEC-002+003. `h, w = shape` → `h, w = shape[:2] if len(shape) > 2 else shape`. All 3 `candy_special.py` copies.

### [WARN-SPEC-002] ✅ FIXED (2026-03-30 19:00) — 4 candy spec functions unsafe shape unpack
`spec_candy`, `spec_candy_burgundy`, `spec_candy_chrome`, `spec_candy_emerald` — all fixed. All 3 `candy_special.py` copies.

### [WARN-SPEC-003] ✅ FIXED (2026-03-30 19:00) — `paint_anodized_exotic` unsafe shape unpack
`paint_anodized_exotic` in `engine/spec_paint.py` — fixed. All 3 copies.

### [WARN-P3-002] `updateSpecPreview()` has no fetch timeout or abort controller (LOW)
**File:** `paint-booth-2-state-zones.js` (root, electron-app, _internal) — L6286
**What:** The spec preview panel fetch call has no timeout and no `AbortController`. If the `/api/spec-preview-composite` server is slow or unresponsive, the UI canvas silently stalls with no indication to the user.
**Fix:** Add `AbortController` + 5-second timeout. Show a loading state on the canvas during fetch.

### [WARN-P3-003] Composite preview endpoint hardcodes seed=42 (LOW)
**File:** `server.py` (root, electron-app, _internal) — L864 (approx)
**What:** `/api/spec-preview-composite` uses `fn((H,W), 42, 1.0)` for all previews. Every pattern always renders the same spatial arrangement in the preview — no way to see how a pattern varies with seed.
**Fix:** Accept an optional `seed` param in the request JSON body. Low priority — consistent preview is actually user-friendly.

### [WARN-GGX-001] ✅ FIXED (2026-03-30 03:30) — `spec_hydrographic` G min raised to 15
**QA verified (2026-03-30 04:00):** L204 confirmed `np.clip(R*255.0, 15, 255)` in all 3 copies. ✓

### [WARN-GGX-002] ✅ FIXED (2026-03-30 03:30) — `spec_moonstone` G min raised to 15
**QA verified (2026-03-30 04:00):** L304 confirmed `np.clip(R*255.0, 15, 255)` in all 3 copies. ✓

### [WARN-GGX-003] ✅ FIXED (2026-03-30 03:30) — `spec_smoked` G min raised to 15
**QA verified (2026-03-30 04:00):** L426 confirmed `np.clip(R*255.0, 15, 255)` in all 3 copies. ✓

### [WARN-GGX-004] ✅ FIXED (2026-03-30 04:30) — `spec_tinted_clear` G min raised to 15
**QA verified (2026-03-30 05:00):** L525 confirmed `np.clip(R*255.0, 15, 255)` in all 3 copies. candy_special.py now fully GGX-safe (9/9 spec functions floor at 15). ✓

### [WARN-GGX-005] ✅ FIXED (2026-03-30 04:30) — `spec_tinted_lacquer` G min raised to 15
**QA verified (2026-03-30 05:00):** L564 confirmed `np.clip(R*255.0, 15, 255)` in all 3 copies. ✓

### [WARN-P4-CSS-001] ✅ FIXED (2026-03-30) — Dead `.zone-card-expanded` border rule removed
Legacy L1067 `.zone-card-expanded { border-left: 3px solid var(--accent-blue); }` removed from all 3 CSS copies. P4 rule at L5675 `.zone-card.zone-card-expanded { border-left: var(--accent-p4); ... }` is the sole active rule. Functional `.zone-card-expanded .zone-summary { display: none; }` rule preserved.

### [WARN-SA-001] ✅ FIXED + QA VERIFIED (2026-03-30) — `hairline_polish` now genuinely distinct from `brushed_linear`
Added perpendicular micro-scratch component: `secondary = sin(x * 400Hz)` at 12% weight blended with primary `sin(y * 200Hz + noise)` grooves. Physical basis: abrasive particle contacts leave finer cross-grain marks in real hairline polish. Distinct from `brushed_cross` (50/50) — this is 100% H + 12% V subdued cross-grain. All 3 `engine/spec_patterns.py` copies.

### [WARN-SB-001] `engraved_crosshatch` shares >70% code structure with `knurl_diamond` (LOW)
**File:** `engine/spec_patterns.py` (root, electron-app, _internal)
**What:** Both functions use a diamond grid via `|sin(x*f)| * |sin(y*f)|` product approach. `knurl_diamond` computes the product at 45° rotation; `engraved_crosshatch` computes it at 0°/90°. The distinguishing element is rotation angle + line depth constants, not a fundamentally different construction.
**Fix:** Add a genuine distinguishing element to `engraved_crosshatch` — e.g., variable-depth grooves (sinusoidal FBM depth modulation along groove length) that knurl_diamond doesn't have. Or accept as a valid angular variant and leave as-is.

### [WARN-B7-002] ✅ FALSE POSITIVE (2026-03-30) — `hex_op` already identical across all 3 JS copies
Grepped all 3 copies — description "Nested hexagonal shells receding to vanishing point — 3D optical tunnel illusion" is identical in root, electron-app, and _internal. No fix needed.

### [WARN-B9-001] ✅ FIXED (2026-03-30) — `texture_hypocycloid` ci cap added
`ci = max(20, int(sm * 48))` → `ci = min(max(20, int(sm * 48)), 24)`. Max cell size capped at 24 — prevents 100MB+ intermediate array allocation at extreme sm values. All 3 `shokker_engine_v2.py` copies.

### [BUG-CHLOG-001] Two CHANGELOG entries labeled "Priority 2 Batch E" (LOW)
**File:** `CHANGELOG.md`
**What:** CHANGELOG has two distinct entries both labeled "Priority 2 Batch E" — one for Clearcoat Behavior (10 patterns) and one for Geometric & Architectural (12 patterns). Creates ambiguity in batch tracking. No functional impact.
**Fix:** Rename one entry to the correct sequential batch letter (likely the Geometric batch should be labeled "Batch E" with Clearcoat relabeled, or vice versa — align with PRIORITIES.md RESEARCH-009 roadmap).

### [WARN-JS-001] ✅ ALREADY FIXED (heartbeat 35) — console.log statements removed from assignFinish
Verified 2026-03-30: zero `console.log` matches in `paint-booth-2-state-zones.js` (all 3 copies). Previously fixed under function name `assignFinishToSelected()`. No action needed.

### [BUG-CHLOG-002] CHANGELOG running count inconsistent — true total was 70/100 (LOW)
**File:** `CHANGELOG.md`
**What:** The two "Batch E" entries show 58/100 and 60/100 respectively — each assuming the other batch hasn't been done yet. True running total when both were complete was 70/100 (A+B+C+D=48 + Clearcoat 10 + Geometric 12 = 70). CHANGELOG entry count is off by 10. No functional impact.
**Fix:** Note-only correction in CHANGELOG. Add a corrective comment or edit counts.

### [BUG-B5-001] ✅ FIXED (2026-03-29) — Duplicate PATTERN_REGISTRY keys removed
Removed 4 old duplicate entries from all 3 engine copies. One entry per key remains, all pointing to correct Batch 5 implementations.

### [BUG-B5-002] ✅ FIXED (2026-03-29) — Old shadowed texture function bodies removed
Removed 4 old function definitions (`texture_basket_weave` old L523, `texture_houndstooth` old L1604, `texture_herringbone` old L2881, `texture_art_deco_fan` old L2901) from all 3 engine copies. Batch 5 versions remain as the sole implementations.

### [BUG-B5-003] ✅ FIXED (2026-03-29) — Stale PATTERNS entries removed
Removed 4 old duplicate entries (argyle/basket_weave/herringbone/houndstooth with stale descriptions + wrong swatch colors) from all 3 JS copies. Batch 5 entries with correct metadata remain.

### [BUG-B5-004] ✅ FIXED (2026-03-29) — Double PATTERN_GROUPS membership cleared
Removed basket_weave from "Carbon & Weave" and argyle/herringbone/houndstooth from "Geometric" in all 3 JS copies. Each of these 4 patterns now appears in exactly one tab ("🎨 Art Deco & Geometric").

### [BUG-EXOTIC-SPEC-001] ✅ FIXED (2026-03-30 18:00) — 7 spec functions in `exotic_metal.py` CC inverted — polished metals render as matte
**Fix applied:** All 7 spec functions corrected: `spec_cobalt_metal`, `spec_liquid_titanium`, `spec_mercury`, `spec_platinum`, `spec_surgical_steel`, `spec_titanium_raw`, `spec_tungsten`. Old `CC = np.ones(...) * 0.75–1.0` → per-finish CC formula in 0-255 range. Return changed from `np.clip(CC * 255.0, ...)` to `np.clip(CC, ...)`. CC ranges: cobalt 16–30, liquid_titanium 16–22, mercury 16 (flat), platinum 16–24, surgical_steel 16–45, titanium_raw 30–80, tungsten 50–90. All 3 copies.

### [BUG-EXOTIC-SPEC-002] ✅ FIXED (2026-03-30 18:00) — 7 spec functions in `exotic_metal.py` unsafe `h, w = shape`
**Fix applied:** All 7 changed to `h, w = shape[:2] if len(shape) > 2 else shape`. Batched with BUG-EXOTIC-SPEC-001. All 3 copies.

## Known Issues — Weak Special Finishes to Improve

### [WEAK-002] ✅ FIXED (2026-03-29) `candy` (FINISH_REGISTRY) — generic sparkle paint replaced with v2
**Fix applied:** `paint_candy_v2` (Beer-Lambert absorption) wired into FINISH_REGISTRY in `shokker_engine_v2.py`. BASE_REGISTRY already patched via `candy_special_reg.py`.

### [WEAK-003] ✅ FIXED (2026-03-29) `spectraflame` (FINISH_REGISTRY) — v2 Rodrigues hue rotation wired in
**Fix applied:** `paint_spectraflame_v2` wired into FINISH_REGISTRY in `shokker_engine_v2.py`. BASE_REGISTRY already patched via `candy_special_reg.py`.

### [WEAK-004] `smoked` (SPECIAL_FINISHES) — single-line paint multiply, not a finish (LOW)
**File:** `engine/spec_paint.py` — function `paint_smoked_darken`
**Why it's weak:** Entire function: `paint * (1 - 0.15 * pm * mask)`. One uniform multiply. No spatial variation, no spectral shift.
**Fix:** Add mild cool spectral shift (−red, +blue), noise-modulated darkening strength, slight edge vignette.

### [WEAK-005] ✅ FIXED (2026-03-29) `jelly_pearl` (FINISH_REGISTRY) — v2 iridescent shimmer wired in
**Fix applied:** `paint_jelly_pearl_v2` wired into FINISH_REGISTRY in `shokker_engine_v2.py`. BASE_REGISTRY already patched via `candy_special_reg.py`.

### [WEAK-006] ✅ FIXED (2026-03-29) `spec_candy_chrome` (candy_special.py) — CC corrected
**Fix applied:** CC changed to `np.clip(16.0 + fine_noise * 4.0 * sm, 16, 30)`.

### [WEAK-007] ✅ FIXED (2026-03-29) `spec_candy_emerald` (candy_special.py) — CC corrected
**Fix applied:** CC changed to `np.clip(16.0 + noise_m * 6.0 * sm, 16, 28)`.

### [WEAK-008] ✅ FIXED (2026-03-29) `spec_tinted_clear` (candy_special.py) — CC corrected
**Fix applied:** CC changed to `np.clip(16.0 + noise_r * 5.0 * sm, 16, 26)`. Note: `paint_tinted_clear_v2` hardcoded tint color still pending separate fix.

### [WEAK-009] ✅ FIXED (2026-03-29) `spec_candy_cobalt` (exotic_metal.py) — CC wrong, hardcoded seeds
**File:** `engine/paint_v2/exotic_metal.py`
**Fix applied:** CC changed to `np.clip(16.0 + crystal * 8.0, 16, 30)`. Seeds changed to `seed + 1410` / `seed + 1411`. Also fixed `paint_candy_cobalt_v2` seed `1401` → `seed + 1401`.

### [BROKEN-001] ✅ FIXED (2026-03-29) `spec_candy` (candy_special.py) — CC=127 inverted
**File:** `engine/paint_v2/candy_special.py`
**Fix applied:** CC changed to `np.clip(16.0 + noise * 6.0, 16, 26)`. Note: `paint_candy_v2` hardcoded red color is a separate issue (color override) — not in scope of this critical pass.

### [BROKEN-002] ✅ FIXED (2026-03-29) `spec_candy_burgundy` (candy_special.py) — CC=102 inverted
**File:** `engine/paint_v2/candy_special.py`
**Fix applied:** CC changed to `np.clip(16.0 + noise * 6.0, 16, 26)`.

**NOTE — Systemic CC inversion in candy_special.py FIXED 2026-03-29:** All affected spec functions (spec_candy, spec_candy_burgundy, spec_candy_chrome, spec_candy_emerald, spec_hydrographic, spec_moonstone, spec_smoked, spec_tinted_clear, spec_tinted_lacquer) corrected. spec_jelly_pearl and spec_spectraflame were already correct.

### [WEAK-001] ✅ FIXED (2026-03-29) `blue_chrome` spec identical to pure chrome / paint is trivial tint (MEDIUM)
**File:** `engine/paint_v2/chrome_mirror.py` — functions `spec_blue_chrome` + `paint_blue_chrome_v2`
**Fix applied:** `paint_blue_chrome_v2` now implements real thin-film interference: 2-octave FBM film thickness (0.3–1.0) → piecewise hue LUT (blue 240°→purple 280°→gold 50°→green-blue 180°), vectorised HSV→RGB, lerped 50/50 with chrome base. `spec_blue_chrome` upgraded from flat constants to FBM-driven spatial variation: M=220+noise×35, R=2+noise×6, CC=14+noise×4. All 3 copies synced.

### [WEAK-010] ✅ FIXED (2026-03-29) `matte` (FINISH_REGISTRY / spec_matte) — flat constants, paint_none, zero spatial variation (MEDIUM)
**File:** `engine/spec_paint.py` — function `spec_matte`
**Fix applied:** `spec_matte` upgraded with 3-octave FBM roughness variation (G: 220-255, M: 0-30 micro-variation, CC: 200-230 noise). New `paint_matte_flat` function added: ~12% desaturation + 5% darkening for chalky undertone. FINISH_REGISTRY wired to `paint_matte_flat`. Both spec_matte and paint_matte_v2 in finish_basic.py upgraded. All 3 copies synced.

### [WEAK-011] ✅ FIXED (2026-03-29) `satin` (FINISH_REGISTRY / spec_satin) — R formula is dead no-op, flat constants (MEDIUM)
**File:** `engine/spec_paint.py` — function `spec_satin`
**Fix applied:** Replaced dead-code `100*mask+100*(1-mask)` R formula with real 2-octave FBM sheen variation. R: 80-140 spatially varied, M: 0-18 micro-variation, CC: 40-90 noise. Both spec_satin in spec_paint.py and spec_satin in finish_basic.py upgraded. All 3 copies synced.

### [WEAK-012] ✅ FIXED (2026-03-29) `matte` (BASE_REGISTRY) — duplicate of FINISH_REGISTRY matte, flat constants (LOW)
**File:** `shokker_engine_v2.py` + `engine/base_registry_data.py` — BASE_REGISTRY entry `"matte"`
**Fix applied:** Both BASE_REGISTRY matte entries upgraded: added `noise_scales=[8,16,32]`, `noise_R=25`, `paint_fn=paint_matte_flat`. Spatially-varied FBM organic chalk texture distinct from legacy flat version. All 3 copies synced.

### [WEAK-013] ✅ FIXED (2026-03-29) `clear_matte` — flat constants, near-duplicate spec to `living_matte` (LOW)
**File:** `engine/paint_v2/finish_basic.py` — `spec_clear_matte`, `paint_clear_matte_v2`, `spec_living_matte`, `paint_living_matte_v2`
**Fix applied:** clear_matte rebuilt as precision matte clearcoat (BMW Frozen/Porsche Chalk style): paint preserves base color (+0.02 only), spec uses very low-amplitude FBM (±5) for engineered uniformity (G: 200-220), fine-scale dust-particle metallic flicker (M: 0-15), CC: 180-200 slight sheen. living_matte upgraded to organic irregular matte: high-amplitude 3-octave FBM roughness (G: 210-255), patchy CC variation (175-230), desaturation + darkening in paint function for chalky character. Now clearly distinct finishes. All 3 copies synced.

### [WEAK-014] ✅ FIXED (2026-03-29) `satin` (BASE_REGISTRY) — duplicate of FINISH_REGISTRY satin, flat constants (LOW)
**File:** `shokker_engine_v2.py` + `engine/base_registry_data.py` — BASE_REGISTRY entry `"satin"`
**Fix applied:** Both BASE_REGISTRY satin entries upgraded: added `noise_scales=[4,8,16]`, `noise_R=20`. Spatially-varied via corrected spec_satin (FBM R: 80-140). All 3 copies synced.

### [WEAK-015] ✅ FIXED (2026-03-29) `scuffed_satin` — R/CC values backward for stated concept (MEDIUM)
**File:** `shokker_engine_v2.py` + `engine/base_registry_data.py` + `engine/paint_v2/finish_basic.py`
**Fix applied:** Physically corrected: R changed from 80/110 → 160 (rougher than satin R=95-100), CC changed from 16/90 → 110 (duller than satin CC=70). New `spec_scuffed_satin` generates 160-200 roughness range with occasional bright metallic highlight spots (scuffing exposes micro-metal). New `paint_f_scuffed_satin` / `paint_scuffed_satin_v2` now desaturates ~8% + micro-abrasion darkening (was previously brightening — backward). All 3 copies synced.

### [WEAK-016] ✅ FIXED (2026-03-29) `liquid_wrap` — near-duplicate of `satin_wrap`, rubber character absent (LOW)
**File:** `shokker_engine_v2.py` + `engine/base_registry_data.py` + `engine/paint_v2/wrap_vinyl.py`
**Fix applied:** New `paint_liquid_wrap_fn` + `paint_liquid_wrap_v2` replace shared `paint_satin_wrap`: 10% desaturation (vs satin's 0%), fine rubber grain Perlin texture, stretch-point darkening simulation. `spec_liquid_wrap` updated: R 60-100 range (vs satin_wrap's 35-55), M near-zero (no metallic character). M fixed from 80→0 (rubber is dielectric). All 3 copies synced.

### [WEAK-017] ✅ FIXED (2026-03-29) `frozen_matte` — near-duplicate of `frozen` (same noise scales, same paint fn) (LOW)
**File:** `shokker_engine_v2.py` + `engine/base_registry_data.py` + `engine/paint_v2/finish_basic.py`
**Fix applied:** Made genuinely distinct. `frozen`: ice-crystal Worley-pattern spec (crystalline roughness), blue iridescence in paint_frozen_v2 (−0.025 R, +0.04 B), finer noise_scales [4,8,16]. `frozen_matte`: frosted/etched glass — uniform micro-roughness spec (R: 200-230), no crystalline sparkle, paint_frozen_matte_v2 adds slight desaturation+dimming (translucency effect), noise_scales [2,3,5] for finer uniform texture. All 3 copies synced.

### [WEAK-018] ✅ FIXED (2026-03-29 13:00) `pearl` (SPECIAL_FINISHES + FINISH_REGISTRY) — no iridescence in paint function (MEDIUM)
**File:** `engine/spec_paint.py` `paint_fine_sparkle`; `shokker_engine_v2.py` SPECIAL_FINISHES + FINISH_REGISTRY `pearl`
**Why it's weak:** `paint_fine_sparkle` is a channel-neutral brightness overlay — adds identical sparkle to all three RGB channels, producing zero color shift or iridescence. Description claims "iridescent sheen" that doesn't exist in any code path. Shares paint function with `candy` and `jelly_pearl`. Spec M/R are fully correlated (same noise field) — misses per-platelet M/R independence.
**Fix applied:** (1) Wired `paint_jelly_pearl_v2` (adapted with `_adapt_bb` wrapper) into FINISH_REGISTRY and BASE_REGISTRY `pearl` entries. (2) Rewrote `spec_pearl` with three decoupled noise seeds (M: seed+42, R: seed+137, CC: seed+251), M range 80-200, R range 30-90, CC range 18-40. (3) Added `spec_pearl_base` (base_spec_fn API) and fine-scale platelet flash via seed+99 blended at 30% into M channel. All 3 copies synced.

### [WEAK-019] ✅ FIXED (2026-03-29 13:00) `pearlescent_white` (SPECIAL_FINISHES) — near-duplicate of `pearl`, tri-coat description not implemented (MEDIUM)
**File:** `shokker_engine_v2.py` SPECIAL_FINISHES `pearlescent_white`
**Why it's weak:** M noise range ~95–145 vs pearl's ~80–120 — 80% range overlap. Same noise scales, same noise weights, same paint function (`paint_fine_sparkle`). Two entries delivering near-identical spec and identical paint output. Description says "tri-coat pearlescent white" — a three-layer coat system — that is completely absent (single noise field, no coat-layer separation).
**Fix applied:** Added `spec_pearlescent_white` (mask-based API) and `spec_pearlescent_white_base` (base_spec_fn API) with three independently-seeded noise fields: base coat seed+11 [4,8], pearl mid-coat seed+73 [20,40], clearcoat seed+199 [40,80]. M range ~120-220, R range 15-55, CC range 16-24. Added `paint_pearlescent_white_fn` with HSV hue rotation shimmer (hue += pearl_mid*30 degrees), slight value push toward white. BASE_REGISTRY entry now references `paint_pearlescent_white_fn` and `spec_pearlescent_white_base`. All 3 copies synced.

### [WEAK-020] ✅ FIXED (2026-03-29 13:00) `iridescent` (SPECIAL_FINISHES) — RGB additive tinting at 25% blend, not rainbow iridescence (MEDIUM)
**File:** `engine/spec_paint.py` `paint_iridescent_shift`
**Why it's weak:** Applies direct R/G/B channel addition at 25% max blend — not HSV hue rotation. On any saturated base color, produces muted tinted patches rather than vivid rainbow banding. Claims "rainbow angle-shift iridescent wrap" — delivers a barely visible overlay. Spatial frequency (2 cycles across canvas) too coarse for iridescent character. Spec is solid (M=160–255, R=0–45); the paint function is the sole failure.
**Fix applied:** Replaced body of `paint_iridescent_shift` with full HSV hue rotation using `hsv_to_rgb_vec` (same math as `paint_interference_shift`). FBM at seed+17 offset, 8-cycle frequency [8,16] scales. Full 360-degree rainbow rotation (t=0-1 maps full hue wheel). Blend raised from 0.25 to 0.55. `paint_cp_chameleon` also upgraded from lazy RGB ±0.25 to HSV hue rotation (±60 degrees based on angle_field, 0.4 blend). All 3 copies synced.

### [WEAK-021] ✅ FIXED (2026-03-29) `galaxy` — nebula color regions + LCG star field + Gaussian star spec peaks
`paint_galaxy_nebula` rewritten: 4-region FBM nebula color ramp (blue/violet/rose/teal), LCG hash star field (~0.3% pixels), per-star color type (white/blue-white/yellow-white), Gaussian dot spread (r=1.5px). `spec_galaxy` rewritten: LCG star field matching paint (~0.5% pixels), Gaussian metallic dot (M=220+), R pulled to near-zero on stars. Nebula blend 40%, base livery 60%. All 3 copies synced.

### [WEAK-022] ✅ FIXED (2026-03-29) `plasma_metal` — FBM sin-vein plasma pattern, 0.55 blend (was 4% invisible)
`paint_plasma_shift` rewritten: FBM + sin(fbm*8*pi) vein field, power-sharpened to isolate vein peaks, electric blue/violet HSV (H=223-252, S=0.85), per-pixel blend up to 0.55 at vein peak. Spec noise_scales updated to match vein FBM. All 3 copies synced.

### [WEAK-023] ✅ FIXED (2026-03-29) `burnt_headers` — full titanium oxide color gradient (was 3-4% invisible)
`paint_burnt_metal` rewritten: FBM-warped horizontal gradient, 6-stop titanium oxide HSV ramp (gray-blue→deep blue→purple→amber→straw→silver), 0.65 blend. All 3 copies synced.

### [WEAK-024] ✅ FIXED (2026-03-29) `heat_treated` — differentiated from burnt_headers (tool steel, not titanium)
PATTERN_REGISTRY: M 185→140, R 35→80, CC 0→16. `paint_heat_tint` rewritten: vertical linear gradient + FBM waver + power sharpening, 4-stop tool steel HSV (dark blue→peacock→bronze→straw, lower S than titanium), 0.60 blend. All 3 copies synced.

### [WEAK-025] ✅ FIXED (2026-03-29) `aurora_bands` — wired paint_aurora (correct) vs paint_wave_shimmer (wrong)
One-line PATTERN_REGISTRY fix. `paint_aurora` (HSV green→magenta aurora bands, 50% blend) now wired. All 3 copies synced.

### [WEAK-026] ✅ FIXED (2026-03-30) `satin_wax` — hand-wax character upgraded
**Fix applied:** `paint_satin_wax` rebuilt. Amplitude 5%→15%. Added micro-buff FBM octave (seed+831, 25% blend). Added saturation warmth: +10% push-from-gray in swirl peak zones. Now returns a clean `np.clip(...).astype(np.float32)` instead of mutating paint in-place. All 3 `engine/spec_paint.py` copies synced.

### [WEAK-027] ✅ FIXED (2026-03-30 08:00) — `spec_satin_chrome()` directional brush-grain R-channel noise
Per-row horizontal brush noise (seed+285) + 30% per-pixel micro-scatter. R varies ±10–13 around base 45 at sm=1.0. Clamped [15, 85]. Matches sin(y×0.8) direction in paint function. All 3 `engine/paint_v2/chrome_mirror.py` copies synced.

### [WARN-CHROME-002] ✅ FIXED (2026-03-30 07:00) — `spec_chrome()` CC raised to 16
`spec[:,:,2] = 0` → `spec[:,:,2] = 16` in `spec_chrome()`. Docstring updated. All 3 `engine/spec_paint.py` copies synced.

### [WEAK-028] ✅ FIXED (2026-03-30 H47) — `candy_cobalt` + `candy_emerald` v2 functions wired via registry patches
**Fix applied:** `paint_candy_cobalt_v2` in `engine/paint_v2/exotic_metal.py` wired via `engine/registry_patches/exotic_metal_reg.py` REGISTRY_PATCH + SPEC_PATCH (`spec_candy_cobalt`). `paint_candy_emerald_v2` in `engine/paint_v2/candy_special.py` wired via `engine/registry_patches/candy_special_reg.py` REGISTRY_PATCH + SPEC_PATCH (`spec_candy_emerald`). Both functions apply material-specific spectral physics (cobalt: R×0.3/G×0.5/B×1.2 selective absorption; emerald: Beer-Lambert + CuPc micro-sparkle). All 3 copies.

### [WEAK-029] ✅ FIXED (2026-03-30 H47) — `candy_chrome` v2 Fresnel function wired via registry patch
**Fix applied:** `paint_candy_chrome_v2` in `engine/paint_v2/candy_special.py` wired via `engine/registry_patches/candy_special_reg.py` REGISTRY_PATCH + SPEC_PATCH (`spec_candy_chrome`). `paint_candy_chrome_v2` implements Fresnel approximation (`0.3 + 0.4*|sin(y*π)|`) — directional reflection model, genuinely distinct from Beer-Lambert candy functions. All 3 copies.

### [WEAK-037] ✅ FIXED (2026-03-30) `chameleon` BASE — pass-through paint + flat spec constants (MEDIUM)
**Fix applied:** Removed `"chameleon"` from both REGISTRY_PATCH and SPEC_PATCH in `finish_basic_reg.py`. `paint_cp_chameleon` (BASE_REGISTRY fallback: bb-based angle proxy, smoothstepped t, ±60° HSV hue shift, 0.4 blend) now takes effect. BASE_REGISTRY M=160/R=25/CC=16 with perlin_octaves=3 noise field now applies for spec. All 3 `engine/registry_patches/finish_basic_reg.py` copies.
**Found:** 2026-03-30 (QA Agent H49)

### [WEAK-038] ✅ FIXED (2026-03-30) `iridescent` BASE — pass-through paint + flat spec constants (MEDIUM)
**Fix applied:** Removed `"iridescent"` from both REGISTRY_PATCH and SPEC_PATCH in `finish_basic_reg.py`. `paint_cp_iridescent` (BASE_REGISTRY fallback: 3-phase R/G/B sine wave rainbow at 120° offsets, 40% blend) now takes effect. BASE_REGISTRY M=200/R=10/CC=16 with noise_scales=[2,4]/noise_M=80/noise_R=30 now live. All 3 `engine/registry_patches/finish_basic_reg.py` copies.
**Found:** 2026-03-30 (QA Agent H49)

### [WEAK-036] ✅ FIXED (2026-03-30) `candy_apple` — no red candy physics, uses paint_smoked_darken (MEDIUM)
**Fix applied:** Wrote `paint_candy_apple_v2` in `engine/paint_v2/candy_special.py` (appended at EOF). Beer-Lambert deep crimson `[0.72, 0.02, 0.02]` with high base absorption `0.82 + noise*(0.10+0.05)` for shadow-crush effect. Green channel suppressed ×12%, blue ×18% (short-wavelength absorption). bb boost=0.20 (specular pops hard from crushed shadows). Wired via `candy_special_reg.py`: REGISTRY_PATCH → `paint_candy_apple_v2`, SPEC_PATCH → `spec_candy` (M=230/R=2 base gives bright sparse metallic flake). All 3 `engine/paint_v2/candy_special.py` + all 3 `engine/registry_patches/candy_special_reg.py` copies.
**Found:** 2026-03-30 (QA Agent H47)

### [WEAK-039] ✅ FIXED (2026-03-30) `oil_slick` Atmosphere SPECIAL — 10% sine paint, near-invisible rainbow (MEDIUM)
**Fix applied:** Changed `"oil_slick"` FINISH_REGISTRY from `(spec_oil_slick, paint_oil_slick)` to `(spec_oil_slick, paint_oil_slick_full)`. Now uses FBM thin-film → full 360° HSV rotation at 70% blend — same quality as `oil_slick_base` MONOLITHIC. All 3 `shokker_engine_v2.py` copies.
**Found:** 2026-03-30 (QA Agent H50)

### [WEAK-040] `aurora` Effects & Vision MONOLITHIC — legacy sine-wave, flat sat/val (LOW)
**Files:** `shokker_engine_v2.py` L249–290, MONOLITHIC_REGISTRY L7041
**Why weak:** `spec_aurora` uses 2 additive sine waves (no multi-scale noise), M=200-240, R=10-40. `paint_aurora` uses 3 sine waves with HSV sweep but flat sat=0.7, flat val=0.65 across all bands — no depth, no brightness variation. 50% blend only. Dedicated aurora presets use domain-warped flowing field, per-stop HSV variation, 93% blend, fine flake layer. The legacy `aurora` entry is the weakest aurora variant.
**Fix:** Redirect `aurora` MONOLITHIC_REGISTRY to `(spec_aurora_borealis_mono, paint_aurora_borealis_mono)`. Or write `spec_aurora_legacy`/`paint_aurora_legacy` stubs for old users and wire `aurora` to the mono versions. All 3 copies.
**Found:** 2026-03-30 (QA Agent H50)

### [WEAK-041] ✅ FIXED (2026-03-30) `spec_dark_brushed_steel` — directional sin(y*freq) formula applied
**Fix applied:** Replaced `x_noise = _multi_scale_noise(shape, [2,4], [0.5,0.5], seed+1221)` with `y_coord = np.linspace(0,1,h,dtype=np.float32).reshape(h,1); x_noise = np.abs(np.sin(y_coord * 180.0 + noise * 0.15)) ** 0.4`. Produces ~28 repeating horizontal scratch bands across normalized height, with `noise * 0.15` warp for organic irregularity. All 3 `engine/expansions/arsenal_24k.py` copies.
**Found:** 2026-03-30 (QA Agent H53)

---

### [WARN-CANDY-001] ✅ FIXED (2026-03-30) `candy_emerald` sparkle tinted green-yellow to match CuPc spectral output
**Fix applied:** `sparkle[:,:,np.newaxis]` → `sparkle[:,:,np.newaxis] * np.array([0.8, 1.0, 0.3], dtype=np.float32)`. All 3 `engine/paint_v2/candy_special.py` copies.
**Found:** 2026-03-30 (QA Agent H47)

### [WARN-CANDY-002] `candy_cobalt` uses linear channel scale, not Beer-Lambert (LOW)
**File:** `engine/paint_v2/exotic_metal.py` L31–34 — `paint_candy_cobalt_v2`
**Issue:** `effect[:,:,2] = base[:,:,2] * 1.2 * depth` — linear scale. True cobalt candy uses Beer-Lambert: `transmitted = base * exp(-alpha * depth)` where alpha_red >> alpha_blue (cobalt selectively absorbs red/green, transmits blue). The linear model approximates the blue-boost but lacks the characteristic deepening at high absorption depths.
**Fix (optional):** Replace linear scale with `exp(-alpha_R * depth)` per channel: `effect[:,:,0] = base[:,:,0] * exp(-3.5 * depth)`, `effect[:,:,1] = base[:,:,1] * exp(-2.0 * depth)`, `effect[:,:,2] = base[:,:,2] * exp(-0.3 * depth)`. Low priority since current output is visually acceptable.
**Found:** 2026-03-30 (QA Agent H47)

### [WARN-CANDY-003] ✅ FIXED (2026-03-30) `moonstone` adularescence center now seed-derived
**Fix applied:** Added `cy = 0.35 + (seed % 31) / 100.0` / `cx = 0.35 + (seed % 29) / 100.0` before shimmer formula; replaced hardcoded `0.5` centers. All 3 `engine/paint_v2/candy_special.py` copies.
**Found:** 2026-03-30 (QA Agent H47)

### [WARN-GLITCH-001] ✅ FIXED (2026-03-30) `spec_glitch` CC=0 → CC=16 GGX floor
**Fix applied:** `spec[:,:,2] = 0` → `spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)`. Applied to all 3 `shokker_engine_v2.py` copies (not root-only as originally noted — three-copy sync rule).
**Found:** 2026-03-30 (QA Agent H51)

### [WARN-CANDY-004] ✅ FIXED (2026-03-30) debug print() in `_apply_staging_registry_patches()` fires on every engine import (INFO)
**Fix applied:** Removed `if paint_updates or spec_updates: print(...)` block entirely. Error path print preserved. All 3 `engine/base_registry_data.py` copies.
**Found:** 2026-03-30 (QA Agent H47)

### [WEAK-030] ✅ FIXED (2026-03-30 08:30) — `clear_matte` R=175→220, CC=130→210, paint_fn wired
R=220 (true matte tier), CC=210 (no-gloss). Also wired `paint_f_clear_matte` (was `paint_none`). All 3 `engine/base_registry_data.py` copies synced.

### [WEAK-031] ✅ FIXED (2026-03-30) `pearl` + `midnight_pearl` — wired spec_pearl_base (LOW)
**Fix applied:** Added `spec_pearl_base` to `spec_paint` imports. Wired into `pearl` (was missing `base_spec_fn`) and `midnight_pearl` (was `spec_metallic_standard`). `spec_pearl_base` has decoupled M/R/CC noise seeds + fine platelet flash (M: 80–200, R: 30–90, CC: 18–40). All 3 copies.

### [WEAK-032] ✅ FIXED (2026-03-30) `dealer_pearl` + `pace_car_pearl` — wired spec_tri_coat_pearl (LOW)
**Fix applied:** Added `spec_tri_coat_pearl` to candy_special import block. Wired into `dealer_pearl` (was `spec_oem_automotive`) and `pace_car_pearl` (was `spec_racing_heritage`). `spec_tri_coat_pearl` generates three distinct coat zones (chrome pearl / satin pearl / gloss pearl) with independent noise seeds. All 3 copies.

### [WEAK-033] ✅ FIXED (2026-03-30) `opal` — wired paint_opal_v2 + spec_opal (MEDIUM)
**Fix applied:** Added `from engine.paint_v2.candy_special import (paint_opal_v2, spec_opal)` import block after chrome_mirror imports. Changed `opal` BASE entry: `paint_fn` from `paint_forged_carbon` → `paint_opal_v2`, added `base_spec_fn: spec_opal`. All 3 `engine/base_registry_data.py` copies synced. Opal now renders as iridescent hexagonal scale pattern with angle-shift shimmer instead of dark woven carbon fiber.

### [BUG-WA-002 + WARN-WA-001] ✅ FIXED (2026-03-30) — `sun_fade` + `sun_baked` wired to `paint_sun_fade_v2`
**Fix applied:** Added `paint_sun_fade_v2` to spec_paint imports. `sun_fade`: `paint_none` → `paint_sun_fade_v2`. `sun_baked`: `paint_volcanic_ash` → `paint_sun_fade_v2`. Both UV-damage finishes now use FBM bleach + 40% desaturation. All 3 `engine/base_registry_data.py` copies synced.

### [WARN-GGX-006] ✅ FIXED (2026-03-30) — `spec_weathered_aged` CC=0 → CC=130
**Fix applied:** `CC = np.where(rot < 0.4, 24.0, 0.0)` → `CC = np.where(rot < 0.4, 24.0, 130.0)`. Weathered areas now output CC=130 (dull clearcoat) instead of CC=0 (chrome trigger). Remnant-gloss pockets remain at CC=24. Affects `sun_baked`, `salt_corroded`, and all entries using `spec_weathered_aged`. All 3 `engine/spec_paint.py` copies synced.

### ✅ FIXED [WARN-GN-001] `spec_galaxy_nebula_base` + other functions — inline PIL imports (LOW)
**File:** `engine/spec_paint.py` (root, electron-app, _internal) — multiple functions use `from PIL import Image as _PILImg, ImageFilter as _PILFlt` inline
**Issue:** PIL is imported at module level as `Image`/`ImageFilter` (L6). Inline imports redundantly re-bind PIL using local aliases (`_PILImg`, `_PILFlt`, `_PILImg2`, `_PILFlt2`). Found at L4282, L4352, L4846, L4867, L5264, L5291. Cannot simply remove the import — must also rename all alias references (`_PILImg` → `Image`, `_PILFlt` → `ImageFilter`) within each function body.
**Fix applied:** All 6 inline import lines removed from all 3 copies. Aliases `_PILImg`→`Image`, `_PILFlt`→`ImageFilter`, `_PILImg2`→`Image`, `_PILFlt2`→`ImageFilter` substituted in-place. Verified with grep — 0 alias references remaining.
**Priority:** LOW — note the QA Agent underestimated scope (it is NOT a one-liner)
**Found:** 2026-03-30 (QA Agent Heartbeat 26; corrected scope: Dev Agent Heartbeat 54) | **Fixed:** 2026-03-30 (Dev Agent Heartbeat 60)

### [WARN-PARA-001] ✅ FIXED (2026-03-30) — `p_superfluid` + `p_erised` R=0 → R=2
**Fix applied:** Changed `"R": 0` → `"R": 2` for both `p_superfluid` and `p_erised` in `engine/expansions/paradigm.py`. All 3 copies synced. Prevents iRacing GGX whitewash artifact at the roughness floor. Consistent with WARN-GGX-001–005 fixes establishing R=2 as project minimum.

### [WEAK-034] ✅ FIXED (2026-03-30 20:00) — `carbon_weave` removed from ★ PARADIGM
Removed `"carbon_weave"` from `"★ PARADIGM"` entry in `BASE_GROUPS` in all 3 `paint-booth-0-finish-data.js` copies. It was already present in `"Carbon & Composite"` — this fix eliminates the double-listing. PARADIGM tab now contains only physically-impossible/extreme concepts.

### [WARN-PARA-002] `spec_p_non_euclidean` is a 2D checkerboard — doesn't reflect the concept (LOW)
**File:** `engine/paint_v2/paradigm_scifi.py` L1097 — `spec_p_non_euclidean()`
**Issue:** The implementation divides the canvas into 32px tile cells: even tiles = mirror face (M=255/R=5), odd tiles = matte face (M=80/R=80) + edge noise. This is a standard 2D checkerboard. "Non-Euclidean geometry" should imply hyperbolic space, impossible tiling angles, or geometry that wraps through itself — none of which the current render delivers. The finish passes the visual distinctness test (hard-edge 32px checker is recognizable) but misrepresents its concept.
**Fix:** Replace with a more conceptually faithful implementation. Options: Poincaré disk mapping (conformal hyperbolic tiling), triangular impossible tiling pattern, or at minimum a radially-warped checker grid (mapped through a fisheye lens function).
**Found:** 2026-03-30 (QA Agent Heartbeat 16)

### [WEAK-035] ✅ FIXED (2026-03-30) — `paint_anodized_exotic` hex pore depth added
**Fix applied:** Added hex pore grid computation (identical 8px cell + row-offset geometry to `spec_anodized_exotic_base`) into `paint_anodized_exotic`. `pore_depth = (hex_pore - 0.3) * 0.06 * pm`: rim=+0.042, center=−0.018 brightness offset at pm=1.0. Blended via `mask_3d` — preserves zero-zone isolation. All 3 `engine/spec_paint.py` copies synced.

### [WARN-GN-001] `spec_galaxy_nebula_base` — redundant inline PIL import (LOW)
**File:** `engine/spec_paint.py` (root, electron-app, _internal) — `spec_galaxy_nebula_base` ~L4280
**Issue:** Function body contains `from PIL import Image as _PILImg, ImageFilter as _PILFlt` as an inline import. PIL is already imported at module level (L6 approximately). The inline import is redundant, creates a minor startup cost on first call, and adds visual noise to the function. No functional impact.
**Fix:** Remove the inline import from the function body. PIL is already available at module scope. One-line change per copy.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 26)

---

## Known Issues — Base Finish Spec Miscalibrations ✅ ALL FIXED (2026-03-29 20:00)

**QA Audit Date:** 2026-03-28 | **Audited by:** QA Agent
**Fixed:** 2026-03-29 20:00 | **Fixed by:** Dev Agent — all 50 issues resolved, all 3 copies synced
**Source:** `shokker_engine_v2.py` BASE_REGISTRY + `engine/base_registry_data.py` BASE_REGISTRY + spec functions in `engine/spec_paint.py`, `engine/paint_v2/finish_basic.py`, `engine/paint_v2/candy_special.py`

---

### CRITICAL — Legacy CC=0 in Monolith BASE_REGISTRY ✅ ALL FIXED

- **BASE-001** ✅ FIXED `matte` (monolith) — CC=0 → CC=215
- **BASE-002** ✅ FIXED `flat_black` (monolith) — CC=0 → CC=220
- **BASE-003** ✅ FIXED `vantablack` (monolith) — CC=0 → CC=240
- **BASE-004** ✅ FIXED `anodized` (monolith) — CC=0 → CC=140
- **BASE-005** ✅ FIXED `satin_chrome` (monolith) — CC=0 → CC=40
- **BASE-006** ✅ FIXED `surgical_steel` (monolith) — CC=0 → CC=16
- **BASE-007** ✅ FIXED `frozen` (monolith) — CC=0 → CC=100
- **BASE-008** ✅ FIXED `frozen_matte` (monolith) — CC=0 → CC=175
- **BASE-009** ✅ FIXED `sandblasted` (monolith) — CC=0 → CC=155
- **BASE-010** ✅ FIXED `satin_gold` (monolith) — CC=0 → CC=16

---

### CRITICAL — Wrong Material Class (base_registry_data.py) ✅ ALL FIXED

- **BASE-011** ✅ FIXED `rose_gold` — M=10 → M=220, R=60→30, desc corrected, paint_fn=paint_rose_gold_tint
- **BASE-012** ✅ FIXED `spectraflame` — M=80,CC=120 → M=245,R=8,CC=16, desc corrected
- **BASE-013** ✅ FIXED `candy_burgundy` — M=20,R=60 → M=180,R=15, paint_fn=paint_cp_candy_burgundy, desc corrected
- **BASE-014** ✅ FIXED `dark_chrome` — R=180,CC=200 → R=15,CC=40, paint_fn=paint_smoked_darken, desc corrected

---

### SIGNIFICANT — Physical Values Contradict Material Description ✅ ALL FIXED

- **BASE-015** ✅ FIXED `champagne_flake` — R=0 → R=2
- **BASE-016** ✅ FIXED `singularity` — R=0 → R=2
- **BASE-017** ✅ FIXED `liquid_obsidian` — R=0 → R=2
- **BASE-018** ✅ FIXED `cerakote` (monolith) — CC=30 → CC=160
- **BASE-019** ✅ FIXED `duracoat` (monolith) — CC=35 → CC=150
- **BASE-020** ✅ FIXED `rugged` (monolith) — CC=25 → CC=175
- **BASE-021** ✅ FIXED `primer` (monolith) — CC=20 → CC=175
- **BASE-022** ✅ FIXED `living_matte` (monolith) — CC=45 → CC=160
- **BASE-023** ✅ FIXED `cerakote_gloss` (monolith) — M=200 → M=100
- **BASE-024** ✅ FIXED `arctic_ice` — M=0,R=6,CC=16 → M=80,R=50,CC=90
- **BASE-025** ✅ FIXED `frozen` (base_registry_data) — CC=16 → CC=100

---

### MINOR — Values Close But Could Be More Accurate ✅ ALL FIXED

- **BASE-026** ✅ FIXED `brushed_aluminum` — M=230 → M=200 (both files)
- **BASE-027** ✅ FIXED `satin_metal` (monolith) — CC=16 → CC=55
- **BASE-028** ✅ FIXED `silk` (monolith) — CC=16 → CC=50
- **BASE-029** ✅ FIXED `matte_wrap` — R=145 → R=195
- **BASE-030** ✅ FIXED `stealth_wrap` — M=120 → M=10
- **BASE-031** ✅ FIXED `ceramic` — M=60 → M=10 (both files)
- **BASE-032** ✅ FIXED `patina_bronze` — CC=16 → CC=100 (both files)
- **BASE-033** ✅ FIXED `raw_aluminum` — M=240→200, CC=0→100 (both files)
- **BASE-034** ✅ FIXED `anodized` (base_registry_data) — R=180 → R=80
- **BASE-035** ✅ FIXED `heat_treated` (base_registry_data) — M=185 → M=140
- **BASE-036** ✅ FIXED `battle_patina` — M=200 → M=140 (both files)
- **BASE-037** ✅ FIXED `metal_flake_base` — CC=40 → CC=18
- **BASE-038** ✅ FIXED `iridescent` — M=255→200 (canon), M=210→200 (monolith)
- **BASE-039** ✅ FIXED `superconductor` — M=255→200, R=90→145
- **BASE-040** ✅ FIXED `prismatic` — CC=80 → CC=16
- **BASE-041** ✅ FIXED `fine_silver_flake` — M=0 → M=160
- **BASE-042** ✅ FIXED `gunmetal_flake` — R=85 → R=30
- **BASE-043** ✅ FIXED `smoked` (monolith + canon) — R=10 → R=30

### P5 OPEN: Weathered & Aged M-Calibration Flags ✅ ALL FIXED (2026-03-30)

### [FLAG-WA-001] ✅ FIXED (2026-03-30) `oxidized_copper` M=140 → M=25
CuCO3/Cu(OH)2 verdigris is dielectric. M=140 → M=25. All 3 copies.

### [FLAG-WA-002] ✅ FIXED (2026-03-30) `patina_bronze` M=160 → M=40
CuO/Cu2O/CuCO3 oxide layers are dielectric-dominant. M=160 → M=40. All 3 copies.

### [FLAG-WA-003] ✅ FIXED (2026-03-30) `oxidized` M=180 → M=15, paint_fn `paint_burnt_metal` → `paint_none`
Fe2O3 is dielectric + burnt_metal was applying thermal heat-tint colors (wrong for room-temp rust). All 3 copies.

### [FLAG-WA-004] ✅ FIXED (2026-03-30) `sun_fade` M=60 → M=10
UV-damaged dielectric paint, compare sun_baked M=0. All 3 copies.

### [WEAK-CANDY-001] ✅ FIXED (2026-03-30) — `candy_burgundy_v2` and `candy_emerald_v2` now genuinely distinct
**Fix applied:**
- `candy_v2`: Unchanged. Standard Beer-Lambert reference.
- `candy_burgundy_v2`: Added `result[...,2] *= (1 - absorption * 0.15)` — near-IR absorption suppresses blue channel in thick-coat zones. Burgundy's wine-red character comes from heavy short-wavelength absorption. B channel loses ~11–15% in peak-absorption areas.
- `candy_emerald_v2`: Added `rng.random((h,w)) < 0.003` LCG sparkle field at `pm * 0.4 * mask` brightness. CuPc pigment crystal facets produce 0.3% micro-specular bright points. Applied before bb boost.
All 3 `engine/paint_v2/candy_special.py` copies. Verified 6 WEAK-CANDY-001 markers (2×3).

### ✅ FIXED [BUG-CANDY-001] `paint_candy_burgundy_v2` blue suppression leaks outside mask (MEDIUM)
**File:** `engine/paint_v2/candy_special.py` L66, L74 (all 3 copies)
**Root cause:** `absorption` at L66 is a uniform noise field ranging ~0.625–0.875, non-zero everywhere. At L74, blue suppression `result[...,2] *= (1 - absorption * 0.15)` is applied without masking. In `mask=0` regions, `result ≈ base` paint. The base paint's blue channel is reduced by ~9–13% across the entire render tile, producing a warm yellow cast in zones where only the base paint should show.
**Note:** `candy_emerald_v2` sparkle fix is correctly masked (`sparkle = ... * mask`). Only burgundy is affected.
**Fix:**
```python
# Line 74 — was:
result[..., 2] = np.clip(result[..., 2] * (1.0 - absorption * 0.15), 0, 1)
# Should be:
result[..., 2] = np.clip(result[..., 2] * (1.0 - absorption * 0.15 * mask), 0, 1)
```
**Priority:** MEDIUM — visible on neutral/gray base paints in multi-zone setups
**Found:** 2026-03-30 (QA Heartbeat 41)

### [WEAK-EXOTIC-001] ✅ FIXED (2026-03-30) — 7 exotic metal paint functions now have per-metal spectral response
**Fix applied:** Added per-channel tint multipliers to each of 7 `paint_*_v2` functions in `engine/paint_v2/exotic_metal.py`:
- `cobalt_metal`: B×1.06 (distinctive blue ferromagnetic sheen)
- `liquid_titanium`: R×0.95, B×1.05 (cool silver)
- `mercury`: R×1.03, B×0.97 (warm silver — mercury reflects warm)
- `platinum`: R×0.97, G×0.99, B×1.02 (cool neutral noble metal)
- `surgical_steel`: R×0.95, G×0.98, B×1.02 (cold 316 SST passive oxide tone)
- `titanium_raw`: R×1.05, G×0.98, B×0.96 (warm gray alpha-beta phase)
- `tungsten`: 70% desaturation toward gray (charcoal refractory metal)
All 3 `engine/paint_v2/exotic_metal.py` copies synced. Verified 21 WEAK-EXOTIC-001 markers (7×3).

### [WARN-EXOTIC-002] `liquid_titanium` ≈ `mercury` — same sin+cos interference structure at different freq (LOW)
**Files:** `engine/paint_v2/exotic_metal.py` — `paint_liquid_titanium_v2` (L124) vs `paint_mercury_v2` (L179)
**Issue:** Both functions compute a 2-axis sin+cos interference pattern:
- liquid_titanium: `sin(y/15) + cos(x/15)` (freq=15, surface tension flow)
- mercury: `cos(x/12) + sin(y/12)` (freq=12, Marangoni convection)
Cos(A)+Sin(B) is mathematically identical to Sin(A)+Cos(B) up to axis labeling. Frequencies differ by ~25% (12 vs 15px). After WEAK-EXOTIC-001 spectral fix, color temperatures diverge (cool silver vs warm silver), which provides meaningful visual differentiation.
**Mitigating factor:** WEAK-EXOTIC-001 fix (spectral channel responses) already addressed this — different BB levels and spectral tints provide perceptible distinction. LOW priority as-is.
**Fix (optional):** Replace `paint_mercury_v2` interference term with radial Marangoni vortex cells: `sin(r * freq) * cos(theta * 4)` — rotating spoke-like cells (Bénard convection topology). Physical basis: Marangoni convection forms radial cells, not parallel fringes.
**Found:** 2026-03-30 (QA Agent H52)

---

## Known Issues — Lazy/Duplicate Patterns to Improve

### [BUG-EXPAND-001] ✅ FIXED (2026-03-30) — 14 expansion patterns dispatch conditions updated
All 14 stale `if "old_name" in variant` conditions corrected in all 3 `engine/expansion_patterns.py` copies. 5 new music patterns (blues, strat, the_artist, smilevana, licked) got dedicated texture implementations. 9 renamed decade patterns were matched to appropriate geometry. `_paint_expansion()` updated to match. See CHANGELOG for full per-pattern breakdown.
**Found:** 2026-03-30 (QA Agent Heartbeat 17) | **Fixed:** 2026-03-30 (Dev Agent)

### [LAZY-EXPAND-001] ✅ FIXED (2026-03-30) — `decade_60s_mod_stripe` / `decade_60s_wide_stripe` split
`mod_stripe` = unchanged 6 even stripes. `wide_stripe` = 3-cycle asymmetric `cycle < 1.33` → bold 2:1 wide+thin pairs. All 3 `engine/expansion_patterns.py` copies.

### [LAZY-EXPAND-002] ✅ FIXED (2026-03-30) — `decade_60s_swirl` / `decade_60s_lavalamp` split
`swirl` = angular warp spiral (`r * pi * 5` rotation + sinusoid threshold). `lavalamp` = `_noise_simple(scale=1.3)` + `Y-bias(-Y2*0.15)` for rising-blob effect. All 3 copies.

### [LAZY-EXPAND-003] ✅ FIXED (2026-03-30) — `decade_70s_earth_geo` / `decade_70s_orange_curve` split
`earth_geo` = `floor(geo*6)/6` topographic quantization. `orange_curve` = `exp(-((Y-sin(X*pi*0.7)*0.4)^2)*5)` Gaussian arch band. All 3 copies.

### [LAZY-EXPAND-004] ✅ FIXED (2026-03-30) — `music_lightning_bolt` / `music_arrow_bold` split
`lightning_bolt` keeps `texture_lightning`. `arrow_bold` → `clip(1 - |Y - |X|*0.7| * 5, 0,1) * (X>-0.7)` bold rightward chevron SDF. All 3 copies.
**Note:** Formula corrected by WARN-EXPAND-001 fix (2026-03-30) → `clip(0.18 - (|Y| - X*0.7), 0, 1) * (X>0)` — proper ">" shape.

### [LAZY-EXPAND-005] `shimmer_spectral_mesh` uses same 3-direction parallel line approach as `hex_circuit` (LOW)
**File:** `engine/expansion_patterns.py` L2140-2159 vs `shokker_engine_v2.py` L5176-5193
**Why it's lazy:** Both iterate over 3 angles at 120° intervals, project via `X*cos(a) + Y*sin(a)`, and mark lines where distance to nearest line < threshold. Same core math, different scale.
**Mitigating factors:** Different categories (Micro Shimmer vs Pattern), different scale (normalized vs pixel coords), different use context.
**Fix (optional):** Since these are in different categories with different visual scales, this is low priority. If fixed, could replace spectral_mesh with a triangular dot-matrix pattern (points at triangle lattice positions, distance to nearest point).
**Found:** 2026-03-30 (QA Agent Heartbeat 17)

### [LAZY-EXPAND-006] ✅ FIXED (2026-03-30) — `decade_80s_vapor` / `decade_80s_pixel` split
`vapor` → `_noise_simple(seed, 1.0)` smooth blobs. `pixel` → `_checkerboard(shape, 16)` clean grid. All 3 copies.

### [LAZY-EXPAND-007] ✅ FIXED (2026-03-30) — `decade_50s_bullet` / `decade_50s_rocket` split
`bullet` keeps speed-lines + oval. `rocket` → `exp(-X²*18 + (Y+0.3)²*1.5)` nose cone + `exp(-((X±0.2)²*80 + (Y-0.5)²*8)) * (Y>0.3)` fin pair. All 3 copies.

### [LAZY-EXPAND-008] ✅ FIXED (2026-03-30) — `decade_90s_trolls` / `decade_90s_tama90s` split
`trolls` → `(_noise_simple(seed, 1.8) > 0.4)` organic blob field. `tama90s` → `_stripe_horizontal(shape, 4)` bold drum-wrap stripes. All 3 copies.

### ✅ FIXED [WARN-EXPAND-001] `music_arrow_bold` chevron direction is ∨ not → (LOW)
**File:** `engine/expansion_patterns.py` (all 3 copies) — `if "music_arrow_bold" in variant` block
**Issue:** Formula `1 - |Y − |X|×0.7| × 5` creates proximity to curve `Y = |X|×0.7` — a downward-opening V (∨) shape in image space. The `(X > −0.7)` mask clips the far-left tail only; result is ∨ not a rightward ">". LAZY-EXPAND-004 is resolved (distinct from texture_lightning) — this is a design quality concern.
**Fix (LOW priority):** `clip(0.18 - (abs(Y) - X*0.7), 0, 1) * (X > 0)` for a proper rightward ">" chevron.
**Found:** 2026-03-30 (QA Agent Heartbeat 38)

### ✅ FIXED [LAZY-008] `cane_weave` is a parameter tweak of `celtic_plait` (MEDIUM)
**File:** `shokker_engine_v2.py` (root, electron-app, _internal) — L6482
**Why it's lazy:** Both `cane_weave` (L6482) and `celtic_plait` (L6463) use `d1 = (xf+yf)/sq2`, `d2 = (xf-yf)/sq2` diagonal projections and the same over-under weave logic: `top1 = s1 & (~s2 | (cell==0))`, `top2 = s2 & (~s1 | (cell!=0))`. Code overlap is >70%. The only differences are `dp = p*2.0` (double period), slightly wider stripe formula, and different fill values `[0.85, 0.45, 0.08]` vs `[0.90, 0.40, 0.05]`. This is a scaled parameter preset of celtic_plait, not a new pattern.
**What it should do differently:** Real cane weave has an orthogonal (horizontal + vertical) grid structure, not ±45° diagonal. Replace the diagonal projection with `xf % p_h` / `yf % p_v` orthogonal grid with appropriate over-under logic. A vertical-and-horizontal woven cane pattern is visually distinct from Celtic diagonal interlace.
**Priority:** MEDIUM
**Confirmed:** H38, H45 (QA Agent — H45 double-verified: cane_weave uses `(d1<pw)|(|d1-p|<pw)` dual-strand vs celtic_plait `|d1%p-p*0.5|<sw` centered; same braid algorithm; parameter variation only)

### [WARN-CHLOG-004] Research Session 6 CHANGELOG entry misdated `2026-03-28` (INFO)
**File:** `CHANGELOG.md`
**What:** The entry `## 2026-03-28 — Research Session 6: 23 New Finishes Implemented` is at the TOP of the CHANGELOG file (which is in newest-first order). Since it appears above entries dated 2026-03-30 03:30 and 2026-03-30 02:30, the actual implementation date is 2026-03-30 or later. The entry date `2026-03-28` is incorrect. No functional impact.
**Fix:** Update the CHANGELOG heading date to the actual implementation date.

### ✅ FIXED [LAZY-007] `spec_peeling_clear` is `spec_galvanic_corrosion` + random peel mask (MEDIUM)
**File:** `engine/spec_patterns.py` (root, electron-app, _internal) — L3639
**Why it's lazy:** Both functions perform an identical mathematical pipeline: Voronoi site generation, k=2 query, d1/d2/cell ID extraction, boundary via distance difference, exponential decay, invert. The ONLY addition in `spec_peeling_clear` is a `np.random.random(n_sites) < 0.35` random cell mask. 85%+ mathematical overlap confirmed.
**Fix:** Replace with delamination mechanics: (a) use `_voronoi_cracks_fast` for crack seam rendering with directional curl at cracks, (b) simulate a primary fracture line with secondary branches, or (c) add proximity-based peel probability (panels peel more at edges, not uniform random). Any of these creates a genuinely different construction from galvanic's pure edge-metric approach.

### [LAZY-006] `spec_ballistic_weave` — weak differentiation from `spec_carbon_plain_weave` (LOW)
**File:** `engine/spec_patterns.py` (root, electron-app, _internal) — L4100
**Why it's lazy:** Orthogonal plain weave parity grid identical to `spec_carbon_plain_weave`. Differences are parameter tweaks only: lower crown amplitude, additive nylon-sheen sinusoid, tighter pitch, different roughness formula.
**Fix:** Implement ripstop reinforcement pattern — every N-th tow has a doubled/reinforced thread (higher specular peak, wider geometry). This creates a grid-within-grid structure that plain_weave + parameters cannot produce.

### [LAZY-005] `spec_kevlar_weave` — near-duplicate of `spec_carbon_plain_weave` with rotation (LOW)
**File:** `engine/spec_patterns.py` (root, electron-app, _internal) — L3903
**Why it's lazy:** Plain weave (0°/90° orthogonal parity) same as `spec_carbon_plain_weave`. Differentiation: 0.15 rad rotation + micro-texture at 0.12 amplitude + lower metallic ceiling. These are parameter tweaks.
**Fix:** Add angle-dependent specularity via `sin(atan2(dy,dx) * 2)` shimmer (simulating Kevlar birefringence — aramid polarization angle-dependence absent from carbon). Or add per-tow rippled fiber modulation along the tow length.

### [LAZY-004] `spec_carbon_wet_layup` is `spec_carbon_2x2_twill` with Gaussian blur (MEDIUM)
**File:** `engine/spec_patterns.py` (root, electron-app, _internal) — L3875
**Why it's lazy:** Function body is the same 2×2 twill geometry (same diagonal coordinates, same cos² crowns, same phase offsets). Only difference: result Gaussian-blurred (sigma=3.5) + low-amplitude resin pool added (0.3×). Post-processing on a copied function, not a new pattern.
**Fix:** Replace with Voronoi-based resin pooling zones — FBM-driven areas of thick resin (nearly smooth, low texture) vs. thin resin (raw weave peaks visible). Add gravity-direction anisotropic blur (horizontal > vertical). Zone distribution creates organic resin-flow appearance impossible to fake with isotropic blurring.

### [LAZY-003] ✅ FIXED (2026-03-30) `spec_carbon_3k_fine` is `spec_carbon_2x2_twill` with Gaussian crown only (MEDIUM)
**File:** `engine/spec_patterns.py` (root, electron-app, _internal) — L3809
**Fix applied:** Rebuilt with dual-frequency construction: main 2×2 twill cos² crowns (tow_width=4.5) PLUS 3-bundle sub-tow Gaussian crowns at tow_width/3 spacing (σ=0.22). Sub-detail modulated by main tow envelope (`* metallic_main * 0.38`) so bundle ribbing only appears inside tow crowns. Micro-gap roughness term between bundles. Two distinct spatial scales (tow + bundle) — impossible to produce from single-scale twill. All 3 copies synced.

### [LAZY-002] ✅ FIXED (2026-03-29) `dragon_curve` doesn't implement a dragon curve (MEDIUM)
**All 3 engine copies** (`shokker_engine_v2.py`). `texture_dragon_curve` draws 5 levels of 45°-rotated right-angle crosshatch grids — this has no relationship to the actual dragon curve fractal. Name is misleading.
**Fix applied:** Replaced with real dragon curve using fold-sequence bit-trick algorithm (12 iterations, 4096 steps). Path pre-computed, scaled to canvas, rendered as per-pixel minimum distance to any segment with glow halo. Produces genuine space-filling right-angle fractal. All 3 copies synced.

### [LAZY-001] ✅ FIXED (2026-03-29) `fiber_optic` is insufficiently distinct from `chainmail_hex`
Both functions used identical interleaved hex close-pack grid code. Only difference was hollow vs filled circle on same grid.
**Fix applied:** Replaced with genuine fiber optic bundle simulation: per-fiber random brightness (fiber_id LCG hash → 0.3–1.0), explicit cladding dark ring zone, per-fiber TIR off-center bright spot (position seeded from fiber_id). Sublattice A/B used explicitly for cell identity. Completely distinct from chainmail_hex. All 3 copies synced.

### ✅ FIXED [LAZY-FUSIONS-001] `gradient_candy_frozen` ≈ `gradient_ember_ice` — nearly identical factory calls (MEDIUM)
**File:** `engine/expansions/fusions.py` L276, L288
**Why it's lazy:**
- `gradient_candy_frozen`: `_make_gradient_fusion((200,15,16), (225,140,16), _gradient_y, 7010, paint_warm=True)`
- `gradient_ember_ice`: `_make_gradient_fusion((200,40,16), (225,140,16), _gradient_y, 7070, paint_warm=True)`
- Identical destination material `(225,140,16)`, identical gradient direction `_gradient_y`, identical `paint_warm=True`. mat_a differs only in G channel by 25 (~10% of range). Both produce a warm horizontal gradient to the same "frozen" terminus material. Nearly identical visual output.
**Fix:** `gradient_ember_ice` should have a different destination material — e.g., arctic silver `(220,30,80)` instead of frozen `(225,140,16)`. Or use `_gradient_diag` direction + `warp=True` to give "ember" an organic feel distinct from the clean horizontal candy gradient. The name "Ember→Ice" implies dramatic warm/cool tension that should be visible in the gradient character.
**Found:** 2026-03-30 (QA Agent Heartbeat 19)

### [LAZY-FUSIONS-002] Same-flake-style sparkle fusions with near-identical spec maps (LOW)
**File:** `engine/expansions/fusions.py` L954–963
**Why it's lazy:**
- diamond_dust (fine, M=60, R=80) vs galaxy (fine, M=50, R=70): both "fine" flake_style, M diff=10, R diff=10. The spec maps are effectively indistinguishable at the renderer level. Visual differentiation is entirely in paint color (icy blue vs purple).
- snowfall (fine, M=80, R=50): third "fine" style entry with different base values but same flake structure
**Fix:** Give diamond_dust a denser micro-sparkle by adding a fourth `[2,4]` noise octave to the micro-pass. Give galaxy a "transparency veil" by multiplying M by 0.8 in high-density areas (nebula is semi-transparent, not fully metallic flake). Give snowfall a hexagonal crystalline structure by adding `_noise(shape, [1], [1.0], seed) > 0.92` sharp-threshold micro crystals.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 19)

### [WARN-FUSIONS-001] `sparkle_starfield` lacks distinct color character (LOW)
**File:** `engine/expansions/fusions.py` L944 (paint_fn, seed_offset == 7410 branch)
**Issue:** starfield paint_fn applies uniform `bright * 1.1` to all RGB channels equally — no color tint, no extra structure. All other 9 sparkle fusions have either distinct color palettes (warm gold, bioluminescent green, purple nebula) or extra structural noise (cluster grouping, streak directionality). Starfield is "just brighter white." In a spec map context, it's indistinguishable from a low-intensity version of any other white-sparkle finish.
**Fix:** Add cold blue-white tint: R=0.90, G=1.00, B=1.25 — matches clear night sky vs. warm incandescent. Or add star cluster grouping: `cluster = _noise(shape, [48, 96], [0.5, 0.5], seed+500); bright_c = bright * (0.5 + cluster*0.5)` — identical to what constellation already does but at a different seed for spatial variation.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 19)

### [WARN-WRAP-001] `textured_wrap` hardcodes carbon charcoal base, overrides user paint (LOW)
**File:** `engine/paint_v2/wrap_vinyl.py` L419–421
**Issue:** `carbon_base = np.array([0.25, 0.25, 0.26])` hardcoded. At pm=1.0, the user's car color is replaced by ~charcoal gray regardless of their chosen base. All other 9 wrap functions tonally modify the user's paint; only textured_wrap replaces it. A painter applying textured_wrap to a red car would get dark charcoal.
**Fix options:**
1. (Preserve intent) Keep carbon gray but document clearly: "Carbon Fiber Wrap — applies charcoal carbon base override." Rename display to "Carbon Fiber Wrap" rather than plain "Textured Wrap."
2. (Color-neutral) Multiply `carbon_sheen` against normalized `paint / (paint.max() + 1e-8)` to add carbon texture while preserving user hue.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 19)

### [LAZY-FUSIONS-004] `horizontal`, `vertical`, `diagonal` anisotropic grain types share >70% code (LOW)
**File:** `engine/expansions/fusions.py` L539–563
**Why it's flagged:** All three use the identical pipeline: `_gabor_noise(angle, 0.1, ≈12, seed)` + stroke-overlay (bilinear-resized Gaussian noise in the grain direction). Differences: angle only (0°, 90°, 45°) and freq (12 vs 12 vs 10). Code overlap ~85%.
**Mitigating factor:** Horizontal/vertical/diagonal brushing ARE physically distinct finish techniques and look different on 3D car panels. The visual outputs are genuinely different. This is a LOW-priority polish item.
**Fix (optional):** Give each a distinguishing property beyond rotation: `vertical` → add perpendicular cross-scratch noise at lower amplitude; `diagonal` → add a `sin(diag_distance * 0.3)` large-scale wave modulation that differs from horizontal's straight strokes.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 21)

### ✅ FIXED (minimal) [LAZY-FUSIONS-005] Paradigm 4 (Reactive) — all 10 entries share identical visual structure, zero structural variety (MEDIUM)
**File:** `engine/expansions/fusions.py` L786–795
**Why it's lazy:** All 10 reactive fusions use the identical `_make_reactive_fusion` spec/paint logic: domain-warped Voronoi (30 pts, 8% warp), F2-F1 chrome seams, odd/even cell zone assignment. The Voronoi seed is randomized per render, so zone shapes vary per-render — not per-fusion. All 10 produce "organic Voronoi zones with chrome seams" as their visual identity. Only 4 material parameters (m_low, m_high, G, CC) differ.
**Specific near-duplicate:** `pearl_flash` (m_low=60, m_high=200, G=40) vs `warm_cold` (m_low=60, m_high=220, G=40) — 3 of 4 parameters identical (m_low and G exactly the same). These are visually indistinguishable at any reasonable viewing distance.
**Additional close pair:** `chrome_fade` (m_low=150, m_high=255, G=5) vs `mirror_shadow` (m_low=200, m_high=255, G=3) — both in high-chrome territory with near-identical G values.
**Fix — two levels:**
1. (Minimal, fix near-duplicates): Change `warm_cold` to use a different G tier (G=80-90, "cold rough") and different m_high (160-170, not 220), making it a genuine matte-cold vs warm-metallic contrast.
2. (Proper, add structural variety): Give some entries different zone geometry — e.g., `reactive_matte_shine` uses horizontal stripe zones (not Voronoi), `reactive_dual_tone` uses radial zones, `reactive_warm_cold` uses diagonal wipe. Structural diversity makes each entry visually unique regardless of material values.
**Priority:** MEDIUM
**Found:** 2026-03-30 (QA Agent Heartbeat 22)

### [LAZY-FUSIONS-006] `halo_crack_chrome` ≈ `halo_voronoi_metal` — both use F2-F1 Voronoi edge detection (LOW)
**File:** `engine/expansions/fusions.py` L2522–2544
**Why it's lazy:** Both `voronoi` (L2522) and `crack` (L2531) compute F2-F1 Voronoi boundary distance:
- `voronoi`: `_halo_voronoi_dist(30 pts)` → `edge_w = d2-d1`, normalized by `percentile(90)`
- `crack`: inline Voronoi 45 pts → `crack_edge = d2-d1`, normalized by `percentile(85)`
Both produce "organic cell boundary halos." The 45 vs 30 point count and 85 vs 90 percentile differ, but the algorithm and visual output type are identical. Compare to `depth_crack` (Paradigm 10) which adds F3 triple-point junctions (`d3 - d1`) to create genuine crack character — `halo_crack_chrome` skips this.
**Fix:** Add triple-point junction emphasis to `halo_crack_chrome`: compute d3 alongside d1/d2, add `exp(-(d3-d1)^2 * 2)` at triple-point junctions to create T-junction branching pattern. This gives "crack" its characteristic appearance (main fracture + branch seams) vs "voronoi" (smooth organic cell boundaries). ~3–4 line change.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 24)

### [LAZY-FUSIONS-007] `wave_chrome_tide` ≈ `wave_pearl_current` — both use Gerstner "low" wave model (MEDIUM)
**File:** `engine/expansions/fusions.py` L2827–2836
**Why it's lazy:**
- `wave_chrome_tide`: `_make_wave_fusion(255, 2, 80, "low", 16, 8100)`
- `wave_pearl_current`: `_make_wave_fusion(100, 20, 70, "low", 16, 8120)`
- Both use `wave_type="low"` (Gerstner steep wave: `sin(kx*x + ky*y - steep*sin(kx*x + ky*y))`). Same wave geometry (peaks, troughs, crest lines) at any given seed. Only base_m and r_min/r_max differ. The other 8 wave types are all distinct algorithms (Bessel, Lorenz, Kelvin wake, beat-pattern, etc.).
**Fix:** Change one entry to an unused wave_type. `wave_pearl_current` → use `"radial"` (Airy diffraction) or `"standing"` (4-corner reflections). Pearl + radial diffraction has a clear visual concept (diffraction shimmer). Chrome + Gerstner ocean waves can stay as `wave_chrome_tide`.
**Priority:** MEDIUM
**Found:** 2026-03-30 (QA Agent Heartbeat 25)

### [LAZY-FUSIONS-008] ✅ FIXED 2026-03-30 — Paradigm 14 Spectral — 7/10 entries share mapping_types; "value" used 3× as parameter sweep (MEDIUM)
**File:** `engine/expansions/fusions.py` L3600–3609
**Why it's lazy:**
- `"rainbow"` × 2: `spectral_rainbow_metal` (8300) and `spectral_earth_sky` (8360) — same wavelength→RGB formula, same `_wavelength_to_rgb(wl)` paint overlay.
- `"binary"` × 2: `spectral_warm_cool` (8310) and `spectral_complementary` (8340) — same logistic phase boundary, same fringe hue logic.
- `"value"` × 3: `spectral_dark_light` (8320), `spectral_neon_reactive` (8350), `spectral_mono_chrome` (8370) — all use identical `lum = field; M = m_range[0] + lum² * (m_range[1]-m_range[0]) * sm`. Pure parameter sweep.
- Only 3 mapping_types appear once: saturation, tri, inverted — these are excellent and genuinely distinct.
**Fix (priority: fix "value" triplet first):**
1. Replace one "value" entry with a new mapping_type, e.g., `"gradient"` — linear luminance (not quadratic) for a different visual response curve.
2. Replace another "value" entry with `"threshold"` — hard quantized step function (3–4 distinct material bands) vs. smooth quadratic curve.
3. For the "rainbow/binary" duplicates: give each pair a different `_spectral_field()` frequency scale so the underlying domain structure differs visually (not just different seed noise).
**Priority:** MEDIUM
**Found:** 2026-03-30 (QA Agent Heartbeat 25)

### [LAZY-FUSIONS-009] Paradigm 15 Quilt — all 10 entries identical factory; chrome_mosaic ≈ diamond_shimmer; hex_variety ≈ organic_cells (MEDIUM)
**File:** `engine/expansions/fusions.py` L3701–3710
**Why it's lazy:**
All 10 entries use the identical `_make_quilt_fusion()` pipeline: irregular Voronoi tessellation, random per-panel M/G/CC, chrome grout lines `max(2.0, panel_size * 0.06)`, random tint paint. No structural variation exists between any two entries — only panel_size and M/G ranges differ.

**Near-duplicate pairs:**
- `chrome_mosaic` (24, M=150–255, G=2–50) vs `diamond_shimmer` (20, M=160–255, G=2–40): panel_size ±4, M offset 10, G nearly identical.
- `hex_variety` (28, M=80–240, G=3–70) vs `organic_cells` (30, M=80–240, G=5–90): M range **identical**, G differs by 20 units, panel_size ±2.

**Naming vs implementation gap:** Names like "hex_variety", "diamond_shimmer", and "organic_cells" imply different cell geometries — but factory uses standard irregular Voronoi for all 10. No entry uses a hexagonal lattice, diamond grid, or any other tessellation structure.

**Fix (two-level):**
1. (Minimum) Remove the 2–3 near-duplicate parameter entries; replace with entries that use genuinely different M/G tier territory (e.g., full-ceramic G=100–200 or near-zero metallic M=0–40).
2. (Proper) Introduce factory variants: a hexagonal-grid quilt (regular hex cells instead of Voronoi), a rectangular-pixel quilt (axis-aligned rectangular regions), and a diamond-grid quilt. Each variant gives a different cell geometry type to the paradigm.
**Priority:** MEDIUM
**Found:** 2026-03-30 (QA Agent Heartbeat 25)

### [BUG-FUSIONS-001] ✅ FIXED (2026-03-30) `_spec_exotic_anti_metal` — domain warping now wired via map_coordinates
**Fix applied:** Added `from scipy.ndimage import map_coordinates as _mc` + `yy/xx` coordinate grids. Warp vectors scaled to pixel space (`* h * 0.09` / `* w * 0.09`). `n1` and `n2` now sampled at warped positions via `_mc`. Level 2 uses accumulated warp `warp1 + warp2` (Quilez nested FBM). All 3 `engine/expansions/fusions.py` copies.
**Found:** 2026-03-30 (QA Agent Heartbeat 20)

### [WEAK-FUSIONS-003] `exotic_anti_metal` — weakest exotic, generic FBM+sigmoid, no physics concept (MEDIUM)
**File:** `engine/expansions/fusions.py` L1863–1903 (spec + paint pair)
**Why it's weak:** Every other Exotic Physics fusion has a named physical analogy (caustic refraction, reaction-diffusion, Newton's rings, gravitational lensing, quantum vortex, etc.). After fixing BUG-FUSIONS-001 (dead warp code), `exotic_anti_metal` will at least have genuine domain warping — but it still has no distinct physics concept to explain WHAT is being simulated.
**Suggested concept:** Anti-reflective coating (ARC) interference — dielectric surface with destructive interference at metallic nodes. Use domain-warped field to modulate `cos(field * 2π * f)` thin-film interference pattern. This would combine domain warp + thin-film optics in a way that none of the other 9 exotics currently does, giving it a unique visual fingerprint (banded interference fringes with organic, warped edges).
**Priority:** MEDIUM — fix BUG-FUSIONS-001 first, then enhance the physics concept
**Found:** 2026-03-30 (QA Agent Heartbeat 20)

### [LAZY-ANGLE-001] ✅ FIXED (2026-03-30) `singularity` now uses radial ring topology vs prismatic FBM blobs
**Fix applied:** Wrote `paint_singularity_v2` in `engine/spec_paint.py` (all 3 copies): radial distance field from centre + 3-petal angular warp `sin(angle*3 + seed*0.2)*0.18` → 8 concentric hue rings with twisted organic edges. Light FBM perturbation (8%) for natural variation. HSV rotation at blend=0.65 (vs prismatic's 0.55). Wired into `singularity` BASE_REGISTRY + import block (all 3 `base_registry_data.py` copies).
**Found:** 2026-03-30 (QA Agent Heartbeat 27)

### [FLAG-ANGLE-001] `neutron_star` `spec_black_hole_accretion` returns M=R=CC=255 all flat (LOW)
**File:** `engine/spec_paint.py` (root, electron-app, _internal) — `spec_black_hole_accretion` L3370–3375
**Issue:** Function body is 4 lines: `M=255, R=255, CC=255` for all pixels — maximum roughness + maximum matte + maximum metallic, completely static. Zero spec variation anywhere on the surface. Listed in "★ Angle SHOKK" category which requires spec-channel angle-dependent behavior. `paint_black_hole_accretion` correctly uses `bb` for accretion ring glow (sound idea!) but spec channels are inert static max values.
**Fix:** Echo the ring structure in spec. Ring zones (high `bb` → high brightness angle) → M=240–255 mirror metallic, R=10–20. Void (low `bb`) → M=0–20, R=240–255. This brings spec channels into the Angle SHOKK concept and makes the ring effect visible in both paint and spec simultaneously.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 27)

### [FLAG-ANGLE-002] `color_flip_wrap` description claims "dual-colour flip" but implementation is smooth hue rotation (LOW)
**File:** `engine/spec_paint.py` (root, electron-app, _internal) — `paint_chameleon_shift` L1404; `paint-booth-0-finish-data.js` — `color_flip_wrap` display entry
**Issue:** Description: "dual-colour angle-shift vinyl film" — implies ChromaFlair-style hard 2-color snap at a flip angle. Implementation: `paint_chameleon_shift` applies smooth full-spectrum hue rotation through all colors, with blend hard-capped at `np.clip(pm * 0.25, 0, 1.0)` — the weakest blend (25% max) of any Angle SHOKK entry. Real color-flip vinyl (e.g. 3M Colorflip, ORAFOL Orajet 3640) has a hard snap between exactly 2 specific colors at a defined tilt angle — not a smooth rainbow sweep.
**Fix option A:** Update description to "multi-colour smooth hue shift vinyl" — accurately describes current implementation. No code change needed.
**Fix option B:** Write `paint_color_flip_wrap_v2` — seed-driven 2-color selection, hard threshold at `bb > 0.5` boundary, smooth narrow transition band (±0.05). Uses bb for genuine angle detection unlike current spatial version.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 27)

### [WARN-INLINE-002] ~12 redundant inline imports in `engine/spec_paint.py` ~L3316+ (LOW)
**File:** `engine/spec_paint.py` (root, electron-app, _internal) — functions starting at L3316
**Issue:** At least 12 functions in the late-added Extreme/Experimental finishes block have inline `import numpy as np` and/or `from engine.core import multi_scale_noise, get_mgrid` inside the function body. Both are already imported at module top (L5: `import numpy as np`, L7: `from engine.core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec`). These are defensive no-ops (Python import cache) but violate spec_paint.py style, add visual clutter, and follow the same anti-pattern as WARN-GN-001 (PIL re-import in spec_galaxy_nebula_base). Affected functions: `paint_dark_matter`, `spec_dark_matter`, `paint_black_hole_accretion`, `spec_black_hole_accretion`, `paint_quantum_black`, `spec_quantum_black`, `paint_absolute_zero`, `spec_absolute_zero`, `paint_holographic_base`, `spec_holographic_base`, `paint_plasma_core`, and several more.
**Fix:** Remove all redundant inline imports from these function bodies. Module-level imports at L5 and L7 already provide numpy and core utilities. ~24 lines removed across the block.
**Priority:** LOW
**Found:** 2026-03-30 (QA Agent Heartbeat 27)

### [LAZY-EXOTIC-001] `paint_cobalt_metal_v2`, `paint_liquid_titanium_v2`, `paint_mercury_v2`, `paint_platinum_v2` share identical sinusoid+noise structure (MEDIUM)
**File:** `engine/paint_v2/exotic_metal.py` (root, electron-app, _internal) — L~60–180
**Why it's lazy:** All 4 use the identical mathematical pipeline:
1. `base = paint / 255.0`
2. `noise_field = multi_scale_noise(shape, scales, weights, seed+X)` (2-octave, identical structure)
3. `field = sin(freq*X) + cos(freq*Y)` (same sinusoid — only freq constant differs)
4. `effect = base * np.clip(mult + field * amp, lo, hi)[:,:,np.newaxis]` (identical broadcast)
Only the `freq`, `mult`, `amp`, `lo`, `hi` constants differ — this is a parameter sweep of one formula, not 4 distinct paint approaches. Confirmed >70% code overlap.
**What each should do differently:**
- cobalt_metal: add crystalline facet structure — `floor(noise * 6.0) / 6.0` quantized grain. Cobalt's metallic grain has discrete facet regions unlike fluid metals.
- liquid_titanium: replace sinusoid with flow-warp — `grad_x = sin(noise * pi)`, `grad_y = cos(noise * pi)`, warp coordinate lookup for fluid motion directionality.
- mercury: replace with vertical convection gradient — `exp(-((yy - noise_y)**2) / sigma)` meniscus pooling effect. Mercury forms visible puddle physics distinct from pure sine.
- platinum: sinusoid at low freq (current y/25, x/25) is already the most differentiated — keep as-is once others are fixed.
**Priority:** MEDIUM
**Found:** 2026-03-30 (QA Heartbeat 33)

## Suggestions from Agent (Needs Ricky's Approval)

### [COLORSHOXX] 20 New Color-Shifting Finishes Ready for Implementation

**Context:** COLORSHOXX is the category of premium color-shift finishes using the paint+spec marriage pattern. 5 already exist and are registered (`cx_inferno`, `cx_arctic`, `cx_venom`, `cx_solar`, `cx_phantom`). Research is now complete for 20 more.

**See:** RESEARCH-035 (engine analysis) + RESEARCH-036 (25 finish library) + RESEARCH-037 (5 dev handoff specs) in RESEARCH.md.

**The 20 new finishes by category:**
- **Intensity Shifters (5):** `cx_abyss`, `cx_obsidian_blaze`, `cx_emerald_depth`, `cx_tungsten`, `cx_plutonium` — same color family, massive brightness swing at angle
- **Temperature Shifts (4 new):** `cx_forge`, `cx_sunset`, `cx_copper_dawn`, `cx_magma_steel` — warm↔cool temperature transition
- **Gradient Reveals (5):** `cx_spectrum_veil`, `cx_eclipse`, `cx_midnight_chroma`, `cx_ghost_fire`, `cx_titanium_bloom` — hidden gradient blazes at specular
- **Multi-Zone Prismatic (5):** `cx_mosaic`, `cx_dragon_scale`, `cx_prism_fragment`, `cx_kaleidoscope`, `cx_spectral_fracture` — Voronoi cells each flashing independently

**5 finishes have FULL pseudocode in RESEARCH-037** — Dev Agent can implement directly. The other 15 have RGB values + spec profiles in RESEARCH-036 tables.

**Dev work estimate:** ~20 lines of code each × 20 finishes = ~400 lines in structural_color.py + registry entries. Follow the same pattern as existing cx_inferno/arctic/venom functions.

**Question for Ricky:** Should COLORSHOXX get its own picker tab/category in the UI? Currently the 5 existing ones would need to be placed in a group — suggest `BASE_GROUPS['colorshoxx']` with a label like "★ COLORSHOXX Color-Shift".

**Priority:** HIGH — 20 finishes represent the most differentiated product feature SPB has vs any competitor tool.

---

### [RESEARCH-001] Built-in Finish Preset Reference Panel ⬆️ ELEVATED PRIORITY
**What:** A visible reference panel (or "cheat sheet" popover) inside SPB that shows the canonical RGB values for the 10 most-used iRacing finishes — Chrome, Metallic, Matte, Satin, Candy, Gloss, Suede, Brushed Alloy, Velvet, Pearl — as one-click presets. Click a finish name and it sets the correct R/G/B spec values automatically.
**Why it matters (updated):** iRacing's 2025 Season 1 update (Dec 2024) performed a major specular rendering overhaul — the "double-exposed sun in cubemaps" bug was fixed, dramatically changing how spec values look in-game. ALL existing community reference charts were calibrated against the old (broken) renderer. Nobody has published a verified post-2025-S1 reference table yet. SPB can be the FIRST tool with correctly calibrated values, labeled "Calibrated for 2025 S1+ renderer." This goes from "nice convenience" to "genuinely fills a real knowledge gap in the community."
**Research refresh (2026-03-30):** Through **2026 Season 2** initial release notes, no second specular overhaul appeared — label when shipping: **"Calibrated for 2025 S1+ specular (stable through 2026 S2)"** — see `RESEARCH.md` §**RESEARCH-001 / RESEARCH-002 / RESEARCH-006 Refresh**.
**Visual:** Small expandable "Finish Library" panel near spec controls. Each preset shows its name + a small swatch + R/G/B numbers. Include a badge: "Calibrated for 2025+ renderer."

### [RESEARCH-002] Multi-Lighting Spec Preview (Noon / Overcast / Dawn / Rain)
**What:** When the user is in the Spec Overlay Preview panel, show the same car section under 4 lighting conditions simultaneously — Noon (harsh direct sun), Overcast (flat ambient), Dawn (low angle warm), Rain (wet reflective). The Gabir Motors tool proves this is a high-demand feature, but theirs only shows flat color swatches. SPB should show it on actual car geometry in the real-time preview.
**Why it matters:** A chrome spec that looks amazing at Noon looks like a grey blob at Dawn. Painters don't discover this until race day. SPB can prevent that. This is a concrete, measurable advantage over every competitor.
**Visual:** 4 thumbnail-sized preview tiles arranged horizontally under the main spec preview, each labeled with the lighting condition.
**Research refresh (2026-03-30):** **Priority order** if building incrementally: **(1) noon / high sun**, **(2) low golden-hour sun**, **(3) overcast** — highest impact on spec readability; rain/night as stretch tiles. See `RESEARCH.md` same refresh section.

### [RESEARCH-003] Alpha/Specular Mask — "Specular Kill" for Flat Vinyl Areas ✅ VERIFIED FUNCTIONAL (but reframed)
**Research verdict:** The Alpha channel IS functional and actively maintained (2025 S1 specular overhaul covered the full pipeline including mirrors). Ricky's instinct was right that the original framing was wrong — it's NOT a "subtle metallic control." It's a hard **specular kill**: Alpha=0 = zero environment effects, Alpha=255 = full specular. There's no blending, it's a kill switch.
**Corrected use case:** Not "matte logo over metallic body" (that would require gradient roughness control). The Alpha channel's actual value: suppressing reflectivity completely in areas that should be dead flat — like flat vinyl sponsor stickers on an otherwise chrome car, or suppressing false lighting in panel gap geometry.
**What:** Expose the Alpha/Specular Mask as a "Specular Kill" pattern target in SPB. Painter can apply a pattern to the Alpha channel to define "dead zones" where specular lighting is completely suppressed.
**Why it matters:** Still differentiating — no other tool exposes this. Best framed as a power feature: "Dead Flat Zones — suppress all reflectivity in selected areas for perfect flat vinyl sticker simulation." Useful for cars with a mix of ultra-shiny body + flat sponsor graphics.
**Visual:** Add an "α" (or "✗ SPEC") toggle alongside M/R/C toggles. Label it "Dead Flat" or "Kill Spec" in the UI so users understand what it does.
**Ricky's call:** Worth implementing as a power feature, but secondary to M/R/C patterns. Ship after Priority 2 is complete.

### [RESEARCH-004] Pattern Scale Warning for Spec Overlays
**What:** When a spec overlay pattern has detail finer than ~8px at 2048x2048 (approximately 0.4% of canvas), show a soft warning: "This pattern has very fine detail — it may render as noise rather than texture in iRacing. Consider scaling up."
**Why it matters:** Community consensus is "big and bold works best" — iRacing's rendering blurs/noises ultra-fine spec detail. Beginners waste hours on intricate patterns that look like noise in-game. This catches that problem before it wastes their time.
**Visual:** Yellow caution icon next to pattern tile when threshold is exceeded. Not a blocker, just a heads-up.

### [RESEARCH-006] Post-2025-S1 Renderer Recalibration — Community Knowledge Gap
**What:** The 2025 Season 1 iRacing update (Dec 2024) fixed a major specular rendering bug where spec maps were "double-exposed by the sun in cubemaps, causing blown-out, white-wash, or milky tone." All existing community reference values for Chrome, Metallic, Matte etc. were created and tested on the OLD broken renderer. Nobody has published recalibrated values for the current renderer.
**Research refresh (2026-03-30):** No superseding specular change called out in **2026 S1 / S2** release notes — the **recalibration narrative remains valid**; cite stability through 2026 S2 when publishing. See `RESEARCH.md` refresh section.
**Why it matters:** This is a genuine knowledge vacuum. Painters using old reference charts may be getting different results than expected without understanding why. SPB can fill this vacuum by:
1. Labeling its Finish Preset Library (RESEARCH-001) as "Calibrated for 2025 S1+ renderer"
2. Eventually publishing a Trading Paints reference car with the recalibrated values
3. Community goodwill + free PR for SPB as the authoritative source
**Action required:** Dev Agent doesn't need to do anything yet. This is context for Ricky to pursue as a community/marketing play once RESEARCH-001 is built.

### [RESEARCH-005] Spec Overlay Category: Channel-Optimized Pattern Groups
**What:** For Priority 2 (100 new spec overlay patterns), organize them explicitly by *which channel they're designed for*:
- **Roughness Patterns (Green):** directional brushed lines, radial brushed, woven fabric, crosshatch, wood grain — simulate physical surface texture direction
- **Metallic Patterns (Red):** cellular/Voronoi, hexagonal flakes, sparkle noise, metallic islands — simulate metallic flake distribution
- **Clearcoat Patterns (Blue):** smooth gradients, vignette, panel-edge fade — simulate clearcoat pooling/dripping at edges
- **Full-Channel Patterns:** complex patterns that drive all 3 channels simultaneously (like carbon fiber weave)
**Why it matters:** Users don't intuitively know that brushed metal requires a *roughness* pattern, not a metallic one. Channel-labeled categories teach correct usage while making it easy to find the right pattern for the job.

### [RESEARCH-007] Pattern Batches 6–8 Roadmap — Remaining 40 Slots *(updated 2026-03-28)*
**Context:** 60/100 done. Batch 5 (Art Deco & Geometric) was executed differently from the original plan — it pulled patterns from my Textile and Op-Art lists. Roadmap below is updated to reflect reality. Dev Agent executes these in order.

**Note on Batch 5:** Patterns `houndstooth`, `herringbone`, `basket_weave`, `argyle`, `tartan` are now DONE (were in Batch 5). `op_art_rings` and `moire_grid` are DONE. `art_deco_fan`, `chevron_stack`, `lozenge_tile`, `ogee_lattice`, `quatrefoil` are DONE.

**Batch 6 — 🌀 Mathematical & Fractal (12 patterns) ✅ DONE (2026-03-28):**
`reaction_diffusion`, `fractal_fern`, `hilbert_curve`, `lorenz_slice`, `julia_boundary`, `wave_standing`, `lissajous_web`, `dragon_curve`, `diffraction_grating`, `perlin_terrain`, `phyllotaxis`, `truchet_flow`

**Batch 7 — 🔮 Op-Art & Visual Illusions (12 patterns) ✅ DONE (2026-03-28):**
`concentric_op`, `checker_warp`, `barrel_distort`, `moire_interference`, `twisted_rings`, `spiral_hypnotic`, `necker_grid`, `radial_pulse`, `hex_op`, `pinwheel_tiling`, `impossible_grid`, `rose_curve`

**Batch 8 — 🏛️🧵 Art Deco Depth + Textile Rest (12 patterns) ✅ DONE (2026-03-28):**
`art_deco_sunburst` (Chrysler Building radiating lines + ring bands — the iconic one), `art_deco_chevron` (bold nested V-stacks — different from chevron_stack), `greek_meander` (Greek key right-angle continuous spiral), `moroccan_zellige` (8-point Islamic star + cross interlocking tile), `escher_reptile` (hexagonal lizard tessellation approximation), `constructivist` (Soviet Constructivist overlapping rectangles/diagonals), `bauhaus_system` (primary shape grid — Bauhaus design school), `celtic_plait` (interwoven linear braid — different from Trinity/Viking), `cane_weave` (diagonal wicker with gaps), `cable_knit` (rope-twist column), `damask_brocade` (ornate floral damask — satin-vs-matte contrast), `tatami_grid` (Japanese mat alternating rectangle layout)

**Final 4 (to reach 100 total) ✅ DONE (2026-03-29) — Priority 1 COMPLETE:** `hypocycloid` (Spirograph epicycloid curves), `voronoi_relaxed` (centroidal Voronoi — smoother organic cells), `wave_ripple_2d` (circular + radial wave interference), `sierpinski_tri` (Sierpinski gasket at iteration 7)

**Priority order:** Batch 6 Mathematical first — these are the most unique patterns in the entire set (no iRacing tool has reaction-diffusion or a Lorenz attractor). Then Op-Art (stunning on metallic). Then mixed Art Deco + Textile.

**Biggest single spec overlay gap:** `brushed_linear` — clean parallel horizontal lines targeting Green (roughness) channel. Add as first spec overlay pattern when Dev Agent reaches Priority 2.

### [RESEARCH-010] Structural Color Finishes — Natural Photonics as New BASE + MONOLITHIC Finishes *(added 2026-03-30)*
**What:** 5 new finishes inspired by natural structural color (not pigment — physical nanostructure interference). These are the most visually advanced finishes on earth, and ZERO competitor tools offer them. All are technically achievable in Python/numpy as paint_fn + spec_fn pairs. Based on deep research into butterfly wing, jewel beetle, moth-eye, and peacock feather nanostructures.

**Why it would be amazing:** Toyota's Structural Blue (Lexus LC500, 2018) is widely considered one of the most beautiful automotive finishes ever produced. 300 cars were made with it. Every car painter who has seen it wants it. Zero tools let you apply it to a virtual race car. SPB can be first — and can offer 5 variants of the same physics class.

**The 5 new finishes:**

1. **"Morpho Blue" BASE FINISH** *(inspired by Morpho butterfly, Toyota Structural Blue)* — Pure structural blue. Deep electric blue that varies only in intensity with angle (NOT hue rotation). Appears to glow — 70% of incident light reflected. Paint: HSV value modulation of fixed blue (H=215–225°, S=0.90) via FBM spatial field. Spec: M=200, R=3–8, CC=16. Description: "Structural color inspired by the Morpho butterfly wing — the same physics used in Toyota's Structural Blue Lexus LC500. Pure electric blue that glows from within, never shifts hue, never fades." Different from chameleon (full hue wheel); different from chromaflair (hard snap). The single most jaw-dropping blue achievable.

2. **"Jewel Beetle" BASE FINISH** *(inspired by Chrysochroa jewel beetle elytra)* — Warm structural iridescence: green → gold → bronze narrow-band shift. Unlike chameleon (which sweeps the full spectrum), jewel beetle stays within a warm green/gold/bronze family. The color family itself is what's precious. Paint: HSV ramp spanning H=30°→130° (warm bronze to green) based on viewing angle field; S=0.80, V=0.80. Spec: M=180, R=10–18, CC=16–20. No other iRacing tool has a warm-band structural iridescent finish.

3. **"Moth Eye Matte" BASE FINISH** *(inspired by moth-eye nanostructure, 10× less reflective than glass)* — The most extreme possible matte. Anti-reflective nanostructure that achieves 0–1% reflectance at ALL angles. Concept: no highlights, ever, from any angle. Available in any color — the albedo shows pure and saturated with zero specular contamination. Paint: pure pass-through (preserves albedo color with no modification). Spec: M=0, R=255, CC=245. Description: "Inspired by moth-eye nanostructure — the natural anti-reflective surface that reflects 10× less light than glass. No highlights. No shine. Just pure color." Offer as: Moth Eye Black, Moth Eye White, Moth Eye Red variants.

4. **"Peacock Crystal" BASE FINISH** *(inspired by peacock feather 2D photonic crystal barbule)* — Mosaic iridescence where different micro-zones each have a different iridescent hue simultaneously (teal, green, bronze, gold). Unlike chameleon or chromaflair (single uniform shift across whole surface), Peacock Crystal has spatial variation in the color-shift character itself — each Voronoi zone has its own center wavelength. Paint: Voronoi segmentation with per-cell hue rng.choice([teal 175°, green 140°, bronze 30°, gold 45°]) + angle-shift blend at 0.5–0.6. Spec: M=160, R=12–22, CC=16–20.

5. **"Scarab Gold" BASE FINISH** *(inspired by Chrysina beetle helicoidal chitin, circularly polarized reflectance)* — Deep metallic gold that reflects circularly polarized light — appears gold/green from head-on, dramatically darker from oblique angles. The circular polarization physics means it only reflects one handedness of light — it's the most "selective" metallic possible. Paint: warm gold base (H=45°, S=0.8, V=0.85) with FBM-driven darkening at oblique field angles (not hue shift — only value/saturation). Blend 0.65. Spec: M=220, R=5–12, CC=16.

**New spec overlay patterns generated from these microstructures:**
- `morpho_lamellae` — Fine horizontal comb structure (120px-scale ridges with lamellae at 150nm pitch → fine periodic horizontal lines, Roughness channel)
- `peacock_crystal_hex` — Top-down hexagonal close-packed melanin rod array (140–165nm spacing → hex close-pack spec grid, Metallic channel)
- `scarab_helicoidal` — Cross-section of helicoidal chitin: diagonal curved band stripes (like very regular wood grain with helical twist, Roughness channel)
- `moth_eye_array` — Top-down moth-eye nano-pillar array (200–300nm spacing → fine Poisson/hexagonal close-packed dot overlay, Roughness channel)

**Implementation guidance:**
- All 5 finishes have M=160–220 (high metallic), R=3–22 (near-mirror), CC=16–22 (full gloss) — cluster in the "structural metallic" zone
- Key distinction from chrome: chrome has M=255, these have M=160–220 — they have the directional brightness of chrome but with saturation of a colored finish
- Morpho/Jewel/Peacock are MONOLITHICs (paint_fn + spec_fn in shokker_engine_v2.py SPECIAL_FINISHES); Moth Eye and Scarab Gold are BASE FINISHES (base_registry_data.py)
- Full physics notes in RESEARCH.md (2026-03-30 entry)
- **Dev acceptance (added 2026-03-30):** Pass/fail criteria + channel bands for all five finishes → `RESEARCH.md` section **"Ship Spec: RESEARCH-010 (Structural Color Finishes)"**.

### [RESEARCH-011] Sim-Stamp & Stencil "Material Inheritance" Rescue Kit *(added 2026-03-29)*
**What:** iRacing’s official docs state that **sim-stamped numbers, sponsors, and paint-kit overlays cannot be assigned their own material** — they inherit **metallic, roughness, clearcoat, and spec mask** from whatever the spec map contains **under that UV texel**. That is why a **chrome or candy spec** makes **white car numbers look metallic/dark/wrong-gloss** unless the painter hand-builds **spec islands** in Photoshop. SPB should ship **purpose-built multi-channel spec overlays** (rounded rectangle / sponsor-block masks, edge-feathered) that painters **align to their number panels**: **lower M**, **raise G into the GGX-safe matte band (≥15)**, tune **B** for satin vs gloss decal reads, and optionally drive **A** for **full spec kill** where RESEARCH-003 applies. Tier 1 = user-positionable overlays + short in-app explainer citing the official limitation; Tier 2 = optional per-car coordinate presets for popular templates.

**Why it would be amazing:** Every competitive painter hits this wall; it is **engine-level**, not skill-level. No competitor generates **coherent R/G/B[/A] “decal rescue” patches** with **real-time car preview**. Photoshop experts solve it with tedious per-template channel surgery — everyone else lives with ugly numbers. SPB becomes the tool that answers *“how do I keep chrome and still have flat white numbers?”* in one workflow.

**Technical:** Reuse existing spec overlay pipeline: **SDF or soft rectangular masks**, smoothstep/Gaussian feather, `np.clip`, **G floor 15+** next to chrome/candy bases. Same numpy patterns as current `spec_patterns.py` overlays — **no new renderer hooks**.
- **Tier 1 preset numbers + UX copy (added 2026-03-30):** Three working presets (`decal_flat_vinyl`, `decal_satin_screen`, `decal_spec_kill_only`), feather widths, and tooltip text → `RESEARCH.md` section **"Ship Spec: RESEARCH-011 Tier 1"**.

### [RESEARCH-012] Priority 5 Living Calibration Briefs — QA Rubric *(added 2026-03-30)*
**What:** Batch documentation so Priority 5 base audits (PARADIGM → Foundation) use the **same pass/fail table** Research defined for **PARADIGM**, **Angle SHOKK**, and **Candy & Pearl** — real coating/optics references + SPB-specific rules (GGX floor, CC bands, angle vs static distinction). **Batch 2** = **[RESEARCH-013]**; **Batch 3** = **[RESEARCH-014]** (all remaining base categories).

**Where:** `RESEARCH.md` — **"2026-03-30 — Priority 5 Audit Support Pack (Batch 1)"** plus **RESEARCH-012** footer in the same dated block.

**Why it matters:** Stops “this feels weak” flags without a standard; accelerates QA/Dev agreement while Priority 5 is **ACTIVE NOW**.

### [RESEARCH-013] Priority 5 Audit Support Pack — Batch 2 (Chrome, Exotic Metal, Ceramic & Glass, Industrial) *(added 2026-03-31)*
**What:** Four-category QA rubric matching RESEARCH-012 format: **category intent**, **PASS** (M/R/CC + required “physics” / paint story), **FAIL**, **LAZY**. Covers **Chrome & Mirror** (chrome bands, when `paint_chrome_brighten`-only is OK vs hollow), **Exotic Metal** (anodized vs xirallic vs chromaflair minimum distinctness vs Metallic Standard), **Ceramic & Glass** (dielectric M 0–20, R/CC by gloss level, GGX floor), **Industrial & Tactical** (Cerakote/powder M 0–60, R 80–180, high CC for flat, decision rule vs Metallic Standard).

**Where:** `RESEARCH.md` — **"RESEARCH-013: Priority 5 Audit Support Pack (Batch 2) (2026-03-31)"** (summary card at end for quick QA lookup).

**Changelog alignment:** Written after tail review of **2026-03-30** entries (Candy GGX registry fixes, `singularity` PARADIGM fix, `candy_special.py` G min=15 sweep, BUG-EXOTIC-001 exotic trio registry).

### [RESEARCH-014] Priority 5 Audit Support Pack — Batch 3 (8 remaining categories) *(added 2026-03-31)*
**What:** Completes the Priority 5 rubric set: **Metallic Standard** (M 100–240, flake `paint_fn` LAZY vs PASS, boundary to Exotic), **Oem Automotive** (fleet plausibility, FS 595 / school bus yellow guidance, restrained paint), **Premium Luxury** (**no `paint_none`**, bespoke paint, M/R/CC bands, `pagani_tricolore` dual-tab note), **Pro Grade `cc_*`** (minimum distinctness between Atelier SKUs), **Racing Heritage** (era physics + cross-audit chrome patterned bases vs RESEARCH-013), **Satin & Wrap** (M 0–40 dielectric, satin vs matte vs stealth separation, `textured_wrap` color-preservation), **Weathered & Aged** (M low, R 150–250, patina LAZY rules, `desert_worn` grit), **Foundation** (`f_*` reference quality bar, anti–lazy-dup contract).

**Where:** `RESEARCH.md` — **"RESEARCH-014: Priority 5 Audit Support Pack (Batch 3)"** + summary card.

**Changelog alignment:** Session opened with **CHANGELOG** review (Candy GGX sweep, PARADIGM `infinite_finish`/`singularity` fixes, fusion sparkle work, WARN-P3-002, etc.).

### [RESEARCH-015] GGX Roughness Floor — Safety Audit Cheatsheet *(added 2026-03-31)*
**What:** Single doc for **G 0–14 whitewash** risk, **`noise_R` negative** invariant (**min R ≥ 15**), **known-safe** `candy_special.py` vs **grep-flagged** `exotic_metal.py` / `raw_weathered.py` / `weathered_worn.py` / broad `spec_paint.py` review; category **risk hint** table; chrome **below-15** nuance.
**Where:** `RESEARCH.md` — **RESEARCH-015**.

### [RESEARCH-016] iRacing 2025 S1/S2 Specular — Deep Dive *(added 2026-03-31)*
**What:** Official **2025 S1** specular/lighting language, **no format change** to PBR channels; **2026 S1/S2** no second overhaul in public notes; **calibration + SPB advantage** = post-2025-S1 **verified presets**.
**Where:** `RESEARCH.md` — **RESEARCH-016**.

### [RESEARCH-017] Community Pain Points Scan *(added 2026-03-31)*
**What:** Clustered **top complaints** (MIP loop, Photoshop channels, PBR confusion, preview, fine noise); **requested features**; **tool sentiment** surface read; **Discord not scraped** — directional only.
**Where:** `RESEARCH.md` — **RESEARCH-017**.

### [RESEARCH-018] Spec Overlay Gap Analysis — 15 High-Impact Candidates *(added 2026-03-31)*
**What:** After **~163** `SPEC_PATTERNS`, lists **15** suggested overlays (wrap seam, PPF edge, rain evaporation front, road film, dealer sticker ghost, panel gap, spray booger, tire rub, polish hologram, carbon resin starve, plate dead zone, EV port, headlamp ring, wing tape, soot) with **R/G/B** targeting.
**Where:** `RESEARCH.md` — **RESEARCH-018**.

### [RESEARCH-019] Multi-Zone vs Forza / GT / Substance *(added 2026-03-31)*
**What:** **Layer/vinyl** editors vs **iRacing TGA**; **Substance** mesh-first vs **SPB zone-from-2D** speed; **moat-widening** ideas (stamp-aware zones, per-zone lighting, template packs, export lint).
**Where:** `RESEARCH.md` — **RESEARCH-019**.

### [RESEARCH-020] Priority 1 Pattern Roadmap Prep *(added 2026-03-31)*
**What:** **PATTERN_GROUPS** thin buckets (**Geometric**, **PARADIGM** subgroups, **Final Collection**); **~288** registry scale reminder; **20** new pattern ideas across **geometric / organic / cultural / industrial / digital / nature** for future greenlight waves.
**Where:** `RESEARCH.md` — **RESEARCH-020**.

### [RESEARCH-021] Top 10 Priority 1 Patterns — Implementation Playbook *(added 2026-03-31)*
**What:** Dev-ready specs for **10** patterns from RESEARCH-020: **numpy** approach (SDF, Voronoi cracks, arcs, heatmap grid, corrugation, branching frost, drips), **diffuse RGB** channel strategy (Priority 1 = paint not spec M/R/B), **2048×2048** visual read, **LOC** + **deps** table.
**Where:** `RESEARCH.md` — **RESEARCH-021**.

### [RESEARCH-022] Spec Overlay Ship Specs — Top 8 (RESEARCH-018) *(added 2026-03-31)*
**What:** Acceptance criteria for **wrap seam, PPF edge, rain evaporation, road film, sticker ghost, panel gap, tire rub, polisher hologram** — **R/G/B** value bands, **feather** px, **G≥15** GGX notes, **tooltip** copy each.
**Where:** `RESEARCH.md` — **RESEARCH-022**.

### [RESEARCH-023] Moat Defense Report — Ricky Brief *(added 2026-03-31)*
**What:** **One-page** strategy: **3** unmatched SPB capabilities (iRacing-native procedural stack, multi-zone from 2D paint, channel-pure overlays at scale); **2** threats (official spec builder, DCC export pipelines); **1** ROI pick = **post-2025-S1 preset library + copy**; optional **multi-light per zone**.
**Where:** `RESEARCH.md` — **RESEARCH-023**.

### [RESEARCH-024] Spec–Paint Marriage Audit — Special Finishes *(added 2026-03-29)*
**What:** Per-base **A/B/C** grades for how well **`base_spec_fn`** (or static M/R/CC + compose noise) supports each **`paint_fn`’s** spatial / optical story — **Part 1:** **Candy & Pearl** (17) + **Chrome & Mirror** (14); **Part 2** (Exotic / Extreme / PARADIGM) deferred. Audited from real Python (`candy_special.py`, `chrome_mirror.py`, `spec_paint.py`, `base_registry_data.py`, registry patches).
**Where:** `RESEARCH.md` — **RESEARCH-024**.
**Dev takeaway:** Highest-ROI gaps in-doc include **`blue_chrome`** (spec must share paint’s **thin-film thickness** map), **`chameleon`**, **`iridescent`**, **`liquid_obsidian`**, **`mirror_gold`**, **`surgical_steel`**, **`terrain_chrome`**, **`candy_cobalt`**. A-grade **template patterns** (shared driver field, replicated defect topology, multi-layer dominance weights) are listed for **Structural Color**-style work.

### [RESEARCH-009] Priority 2 — Complete 100-Pattern Spec Overlay Roadmap *(added 2026-03-28)*
**What:** Full implementation plan for Priority 2 (100 new spec overlay patterns for `spec_patterns.py`), organized into 9 thematic batches. Research confirmed `spec_patterns.py` already has 65 patterns; 100 new ones bring it to 165. Unlike Priority 1 (paint patterns in `shokker_engine_v2.py`), these live in `spec_patterns.py` and must also be registered in the `SPEC_PATTERNS` array in `paint-booth-0-finish-data.js`.

**Why it would be amazing:** The #1 missing capability in SPB (and all competitor tools) is channel-specific procedural patterns. Guilloché on chrome. Brushed roughness lines. Clearcoat pooling. No other tool on earth will let a painter apply watch-dial engine turning to ONLY the roughness channel of a chrome base. This is pure moat.

**Key finding from research:** `brushed_linear` must use `sin(y * freq)` with **zero x-modulation** — not a noise warp. This makes it a true parallel-line simulation vs. `aniso_grain` which uses sine-modulated waves. The distinction is why every painter who wants brushed aluminum currently fails.

**Batch roadmap (execute in this order):**
1. **Batch A: 🪛 Directional Brushed (12) ✅ DONE (2026-03-29)** — `brushed_linear`, `brushed_diagonal`, `brushed_cross`, `brushed_radial`, `brushed_arc`, `hairline_polish`, `lathe_concentric`, `bead_blast_uniform`, `orbital_swirl`, `buffer_swirl`, `wire_brushed_coarse`, `hand_polished`
2. **Batch B: ⌚ Guilloché & Machined (12) ✅ DONE (2026-03-29)** — `guilloche_barleycorn`, `guilloche_hobnail`, `guilloche_waves`, `guilloche_sunray`, `guilloche_moire_eng`, `jeweling_circles`, `knurl_diamond`, `knurl_straight`, `face_mill_bands`, `fly_cut_arcs`, `engraved_crosshatch`, `edm_dimple`
3. **Batch C: 🦾 Worn, Patina & Weathering (12) ✅ DONE (2026-03-29)** — `spec_rust_bloom`, `spec_patina_verdigris`, `spec_oxidized_pitting`, `spec_heat_scale`, `spec_galvanic_corrosion`, `spec_stress_fractures`, `spec_battle_scars`, `spec_worn_edges`, `spec_peeling_clear`, `spec_sandblast_strip`, `spec_micro_chips`, `spec_aged_matte`
4. **Batch D: 🏎️ Carbon Fiber & Industrial Weave (12) ✅ DONE (2026-03-29)** — `spec_carbon_2x2_twill`, `spec_carbon_plain_weave`, `spec_carbon_3k_fine`, `spec_carbon_forged`, `spec_carbon_wet_layup`, `spec_kevlar_weave`, `spec_fiberglass_chopped`, `spec_woven_dyneema`, `spec_mesh_perforated`, `spec_expanded_metal`, `spec_chainlink_fence`, `spec_ballistic_weave`
4b. **Batch E (Clearcoat): 🔵 Clearcoat Behavior (10) ✅ DONE (2026-03-29)** — `cc_panel_pool`, `cc_drip_runs`, `cc_fish_eye`, `cc_overspray_halo`, `cc_edge_thin`, `cc_masking_edge`, `cc_spot_polish`, `cc_gloss_stripe`, `cc_wet_zone`, `cc_panel_fade`
4c. **Batch E (Geometric): 🏗️ Geometric & Architectural (12) ✅ DONE (2026-03-29)** — `spec_faceted_diamond`, `spec_hammered_dimple`, `spec_knurled_diamond`, `spec_knurled_straight`, `spec_architectural_grid`, `spec_hexagonal_tiles`, `spec_brick_mortar`, `spec_corrugated_panel`, `spec_riveted_plate`, `spec_weld_seam`, `spec_stamped_emboss`, `spec_cast_surface` *(60/100 total)*
4d. **Batch F: 🌿 Natural & Organic (12) ✅ DONE (2026-03-29)** — `spec_wood_grain_fine`, `spec_wood_burl`, `spec_stone_granite`, `spec_stone_marble`, `spec_water_ripple_spec`, `spec_coral_reef`, `spec_snake_scales`, `spec_fish_scales`, `spec_leaf_venation`, `spec_terrain_erosion`, `spec_crystal_growth`, `spec_lava_flow` *(72/100 total)*
4e. **Batch G: 💡 Lighting & Optical Effects (12) ✅ DONE (2026-03-29)** — `spec_fresnel_gradient`, `spec_caustic_light`, `spec_diffraction_grating`, `spec_retroreflective`, `spec_velvet_sheen`, `spec_sparkle_flake`, `spec_iridescent_film`, `spec_anisotropic_radial`, `spec_bokeh_scatter`, `spec_light_leak`, `spec_subsurface_depth`, `spec_chromatic_aberration` *(84/100 total)*
5. **Batch G: 🔴 Metallic Distribution (10)** — `metallic_fade_radial`, `metallic_islands`, `chrome_delete_stripe`, `foil_crumple`, `electroplate_uneven`, `anodize_rings`, `steel_grain_direc`, `chrome_craze`, `sputter_erosion`, `metallic_gradient_lin`
6. **Batch F: ⚙️ Full-Channel Materials (12)** — `brushed_stainless_full`, `anodized_hard_full`, `titanium_raw_full`, `copper_patina_full`, `galvanized_zinc_full`, `pewter_hammered_full`, `polished_chrome_tool`, `satin_nickel_full`, `black_oxide_full`, `electroless_nickel`, `cast_iron_grind`, `vapor_deposition`
7. **Batch G: 👜 Luxury Textures (10)** — `velvet_pile`, `corduroy_ribs`, `leather_pebble_fine`, `leather_perforated`, `alcantara_nap`, `silk_sheen`, `carbon_dry_weave`, `tweed_texture`, `denim_twill`, `tapestry_cross`
8. **Batch H: 🌧️ Environmental (10)** — `dew_droplets`, `rain_beading`, `frost_crystal`, `condensation_fog`, `ice_sheet_cracks`, `dusty_film`, `smoke_deposit`, `water_stain_ring`, `mud_spray_pattern`, `wet_asphalt_wet`
9. **Batch I: 🧮 Mathematical (12)** — `aniso_voronoi`, `perlin_erosion`, `fibonacci_pack`, `weierstrass_rough`, `poisson_disk_spec`, `blue_noise_grain`, `halftone_screen`, `turing_labyrinth`, `gabor_grain`, `voronoi_flat_edge`, `stochastic_fm_screen`, `turing_spots_align`
10. **Batch J: 🏁 Racing Structural (12)** — `racing_stripe_gloss`, `checker_gloss_matte`, `number_panel_zone`, `livery_edge_transition`, `pinstripe_gloss`, `corner_vignette_spec`, `sponsor_clear_zone`, `hex_polish_zone`, `diagonal_hatch_gloss`, `rib_stripe_spec`, `diamond_plate_spec`, `panel_seam_shadow`

**Implementation notes for Dev Agent:**
- Add new function `def PATTERN_ID(shape, seed, sm, **kwargs)` to `spec_patterns.py` (all 3 copies: root/electron-app/pyserver)
- Add corresponding entry to `SPEC_PATTERNS` array in `paint-booth-0-finish-data.js` (all 3 copies)
- Channel guidance in each pattern's description: G=Roughness, R=Metallic, B=Clearcoat
- Full-channel patterns (Batch H) should set appropriate `R_range`, `M_range` and `CC` hint in return value
- Full channel descriptions and visual specs in RESEARCH.md (2026-03-28 22:00 entry)

### [RESEARCH-008] New Base Finishes & Monolithics from Exotic Automotive Paint Science *(added 2026-03-28)* — **IMPLEMENTED 2026-03-29**
**Context:** Deep research into exotic automotive paint effects reveals several finish types SPB doesn't have that would be jaw-dropping additions. All are technically achievable in Python/numpy. Needs Ricky's approval on which to implement.

**New BASE FINISH suggestions:**

1. **"Light Shift" (ChromaFlair-style Hard Dual-Color Angular Shift)** — Different from SPB's chameleon. ChromaFlair uses thin-film interference flakes that produce a HARD color transition between 2–3 anchor colors at defined viewing angles (not a smooth spectrum rotation). The Ford Mystic Mustang Cobra was the first OEM use. In SPB: implement as a dual-anchor chameleon where the hue snaps between two specific user-chosen colors at a defined angle threshold rather than rotating through the full spectrum. Visually very distinct.

2. **"Crystal Flake" (Xirallic-style Sharp Point Sparkle)** — Standard metallic paint has diffuse warm sheen from metallic flake blur. Xirallic (aluminum oxide crystals) produces sharp, discrete, individually-visible bright points against the background color — like stars. BMW uses this in their Frozen series. In SPB: implement as metallic base with superimposed bright discrete noise points (Poisson disk sample pattern) at low density — very different from existing metallic flake.

3. **"Anodized" (Colored Matte-Metallic)** — The electrochemical anodizing process creates a color IN the metal surface, not on top. The result is a flat-but-clearly-metallic look with saturated color. No current SPB finish achieves this. In SPB: high metallic (R=220+), medium roughness (G=140-160), no clearcoat (B=0-15), applied with the color as a dye tint rather than surface color. Available in hard black, blue, red, gold, purple, green.

**New MONOLITHIC (Special Finish) suggestions:**

4. **"Oil Slick" (Thin-Film Interference Rings)** — The most visually distinctive effect not in SPB. Oil on water creates rainbow interference bands visible as rings/zones, with 4–6 color shift. Key detail: the interference creates PATTERNS (rings, bands), not uniform color shift. The color zones correspond to oil film thickness variation. In SPB: combine the chameleon hue shift with a visible interference pattern overlay — concentric rings or flowing organic zones, each zone showing a different color in the shift sequence.

5. **"Thermal Titanium" (Heat-Oxide Gradient)** — When titanium is heated, oxide layers of different thicknesses produce specific colors in a natural sequence: silver → gold → bronze → rose → purple → blue → grey. Radiates from heat sources (weld lines, exhaust). Stunning on race cars and motorcycles. In SPB: a monolithic that simulates radial gradient from center outward: silver core → gold → bronze → purple rim. The color bands are narrow and precise, not diffuse like a gradient.

6. **"Galaxy / Nebula" (Dark + Multi-Color Sparkle)** — Very dark base with individually-colored metallic sparkle points at low density — silver, blue, purple, gold points, like looking into space. Different from dark metallic which has uniform diffuse sheen. In SPB: deep dark base (R=30-50, near-black), with superimposed Poisson-distributed bright points where each point has a randomized color (blue, purple, silver, gold). The per-point color variation is the key — regular dark metallic can't achieve this.

**Technical feasibility:** All 6 are achievable with Python/numpy in the engine. Light Shift and Crystal Flake are new base finishes. Oil Slick, Thermal Titanium, and Galaxy are new monolithics. Anodized is a base finish variant. None conflicts with existing finishes.

## Completed (Move Here When Done)

- [2026-03-28] ✅ Research Session 6 IMPLEMENTED — 23 new finishes: 9 base (alubeam, satin_candy, velvet_floc, deep_pearl, gunmetal_satin, forged_carbon_vis, electroplated_gold, cerakote_pvd, hypershift_spectral), 8 special (iridescent_fog, chrome_delete_edge, carbon_clearcoat_lock, racing_scratch, pearlescent_flip, frost_crystal, satin_wax, uv_night_accent), 6 monolithic (aurora_borealis_mono, deep_space_void, polished_obsidian_mono, patinated_bronze, reactive_plasma, molten_metal). All 4 files synced to all 3 copies.

- [2026-03-29] 🏆 Priority 2 COMPLETE — Final Batch H+I (16 spec overlays): Surface Treatments: spec_electroplated_chrome, spec_anodized_texture, spec_powder_coat_texture, spec_thermal_spray, spec_electroformed_texture, spec_pvd_coating, spec_shot_peened, spec_laser_etched. Exotic: spec_liquid_metal, spec_chameleon_flake, spec_xirallic_crystal, spec_holographic_foil, spec_oil_film_thick, spec_magnetic_ferrofluid, spec_aerogel_surface, spec_damascus_steel_spec. 🎉 100/100 COMPLETE. Two new picker tabs added: "Surface Treatment" + "Exotic".
- [2026-03-29] Priority 2 Batch G DONE — 💡 Lighting & Optical Effects (12 spec overlays): spec_fresnel_gradient, spec_caustic_light, spec_diffraction_grating, spec_retroreflective, spec_velvet_sheen, spec_sparkle_flake, spec_iridescent_film, spec_anisotropic_radial, spec_bokeh_scatter, spec_light_leak, spec_subsurface_depth, spec_chromatic_aberration. Running total: 84/100 spec overlays. "Optical" group expanded with 12 new entries.
- [2026-03-29] Priority 2 Batch F DONE — 🌿 Natural & Organic (12 spec overlays): spec_wood_grain_fine, spec_wood_burl, spec_stone_granite, spec_stone_marble, spec_water_ripple_spec, spec_coral_reef, spec_snake_scales, spec_fish_scales, spec_leaf_venation, spec_terrain_erosion, spec_crystal_growth, spec_lava_flow. Running total: 72/100 spec overlays. New "Natural" tab added to picker.
- [2026-03-29] Priority 2 Geometric Batch DONE — 🏗️ Geometric & Architectural (12 spec overlays): spec_faceted_diamond, spec_hammered_dimple, spec_knurled_diamond, spec_knurled_straight, spec_architectural_grid, spec_hexagonal_tiles, spec_brick_mortar, spec_corrugated_panel, spec_riveted_plate, spec_weld_seam, spec_stamped_emboss, spec_cast_surface. Running total: 70/100 spec overlays. New "Geometric" tab added to picker.
- [2026-03-29] Priority 2 Clearcoat Batch DONE — 🔵 Clearcoat Behavior (10 spec overlays): cc_panel_pool, cc_drip_runs, cc_fish_eye, cc_overspray_halo, cc_edge_thin, cc_masking_edge, cc_spot_polish, cc_gloss_stripe, cc_wet_zone, cc_panel_fade. Running total: 58/100 spec overlays. New "Clearcoat" tab added to picker.
- [2026-03-29] Priority 2 Batch D DONE — 🏎️ Carbon Fiber & Industrial Weave (12 spec overlays): spec_carbon_2x2_twill, spec_carbon_plain_weave, spec_carbon_3k_fine, spec_carbon_forged, spec_carbon_wet_layup, spec_kevlar_weave, spec_fiberglass_chopped, spec_woven_dyneema, spec_mesh_perforated, spec_expanded_metal, spec_chainlink_fence, spec_ballistic_weave. Running total: 48/100 spec overlays.
- [2026-03-29] Priority 2 Batch C DONE — 🦾 Worn, Patina & Weathering (12 spec overlays): spec_rust_bloom, spec_patina_verdigris, spec_oxidized_pitting, spec_heat_scale, spec_galvanic_corrosion, spec_stress_fractures, spec_battle_scars, spec_worn_edges, spec_peeling_clear, spec_sandblast_strip, spec_micro_chips, spec_aged_matte. Running total: 36/100 spec overlays.
- [2026-03-29] Priority 2 Batch B DONE — ⌚ Guilloché & Machined (12 spec overlays): guilloche_barleycorn, guilloche_hobnail, guilloche_waves, guilloche_sunray, guilloche_moire_eng, jeweling_circles, knurl_diamond, knurl_straight, face_mill_bands, fly_cut_arcs, engraved_crosshatch, edm_dimple. Running total: 24/100 spec overlays. (NOTE: Old entry listed wrong IDs from a prior session — corrected by QA 2026-03-29)
- [2026-03-29] Priority 2 Batch A DONE — 🪛 Directional Brushed (12 spec overlays): brushed_linear, brushed_diagonal, brushed_cross, brushed_radial, brushed_arc, hairline_polish, lathe_concentric, bead_blast_uniform, orbital_swirl, buffer_swirl, wire_brushed_coarse, hand_polished. Running total: 12/100 spec overlays.
- [2026-03-29] BUG-B5-002/003/004 FIXED — All Batch 5 duplicate code cleared: 4 old shadowed engine functions removed, 4 stale JS PATTERNS entries removed, 4 double-grouped picker tabs corrected. All across 3 copies each.
- [2026-03-29] BUG-B5-001 FIXED — 4 duplicate PATTERN_REGISTRY keys removed from all 3 engine copies.
- [2026-03-29] 🏁 Priority 1 COMPLETE — Final Collection Batch 9 (4 patterns): Hypocycloid, Voronoi Relaxed, Wave Ripple 2D, Sierpinski Triangle. Grand total: 100/100 new patterns added.
- [2026-03-28] Added 🏛️🧵 Art Deco Depth + Textile pattern group Batch 8 (12 patterns) — Art Deco Sunburst, Art Deco Chevron, Greek Meander, Moroccan Zellige, Escher Reptile, Constructivist, Bauhaus System, Celtic Plait, Cane Weave, Cable Knit, Damask Brocade, Tatami Grid. Running total: 96/100.
- [2026-03-28] Added 🔮 Op-Art & Visual Illusions pattern group Batch 7 (12 patterns) — Concentric Op-Art, Checker Warp, Barrel Distort, Moiré Interference, Twisted Rings, Hypnotic Spiral, Necker Grid, Radial Pulse, Hex Tunnel, Pinwheel Tiling, Impossible Grid, Rose Curve. Running total: 84/100.
- [2026-03-28] Added 🌀 Mathematical & Fractal pattern group Batch 6 (12 patterns) — Reaction Diffusion, Fractal Fern, Hilbert Curve, Lorenz Attractor, Julia Set, Standing Wave, Lissajous Web, Dragon Curve, Diffraction Grating, Perlin Terrain, Phyllotaxis, Truchet Flow. Running total: 72/100.
- [2026-03-28] Added 🎨 Art Deco & Geometric pattern group Batch 5 (12 patterns) — Art Deco Fan, Chevron Stack, Quatrefoil, Herringbone, Basket Weave, Houndstooth, Argyle, Tartan, Op-Art Rings, Moiré Grid, Lozenge Tile, Ogee Lattice. Running total: 60/100.
- [2026-03-28] Added ⚙️ Tech & Circuit pattern group Batch 4 (12 patterns) — Circuit Traces, Hex Circuit, Biomech Cables, Dendrite Web, Crystal Lattice, Chainmail Hex, Graphene Hex, Gear Mesh, Vinyl Record, Fiber Optic, Sonar Ping, Waveform Stack. Running total: 48/100.
- [2026-03-28] Added 🌿 Natural Textures pattern group Batch 3 (12 patterns) — Marble Veining, Wood Burl, Seigaiha Scales, Ammonite Chambers, Peacock Eye, Dragonfly Wing, Compound Eye, Diatom Radial, Coral Polyp, Birch Bark, Pine Cone Scale, Geode Crystal. Running total: 36/100.
- [2026-03-28] Added ✨ Tribal & Ancient pattern group Batch 2 (12 patterns) — Maori Koru, Polynesian Tapa, Aztec Sun, Celtic Trinity, Viking Knotwork, Native Geometric, Inca Step Fret, Aboriginal Dots, Turkish Arabesque, Islamic Star, Egyptian Lotus, Chinese Cloud; also synced Batch 1 entries into electron-app JS copies that were missing them. Running total: 24/100 new patterns.
- [2026-03-28] Wired up ★ Intricate & Ornate pattern group Batch 1 (12 patterns) — all now render properly; 11 new texture functions added to engine
- [2026-03-28] Removed 4 stray debug print statements from engine (clean, no behavior change)

---

## How This File Works

- **Ricky edits** the "Current Focus" and "Do NOT Touch" sections to steer the agent
- **Agent reads** this file at the start of every heartbeat before choosing work
- **Agent writes** to "Suggestions from Agent" when it finds something it can't decide alone
- **Both** move items to "Completed" when done
