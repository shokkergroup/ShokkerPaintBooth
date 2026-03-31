# Shokker Paint Booth — Research Intelligence

**Last Updated:** 2026-03-30

This file tracks **active research** steering current development. Historical findings and reference material are in [RESEARCH_REFERENCE.md](RESEARCH_REFERENCE.md).

---

## RESEARCH-042: State of the Codebase — 2026-03-31 Snapshot

**Date: 2026-03-31 | Agent: Hermes Agent | Mission: Complete codebase health assessment**

### Total Content

| Category | Count | Notes |
|----------|-------|-------|
| **Bases** | 344 | Across 22 BASE_GROUPS categories (includes Angle SHOKK cross-refs) |
| **Patterns** | ~305 | Across 27 PATTERN_GROUPS categories |
| **Spec Overlays** | ~80+ | In SPEC_PATTERNS + SPECIAL_GROUPS |
| **Fusions** | 150 | Paradigm Shift Hybrids (15 paradigms × 10 each) |
| **Color Monolithics** | 260+ | Gradient, ghost, multi-color dynamically generated |
| **TOTAL CONTENT** | **~1100+** | Bases + patterns + overlays + fusions + monolithics |

### Category Strength Rankings

| Rank | Category | Bases | Strength | Notes |
|------|----------|-------|----------|-------|
| 1 | Foundation | 34 | ★★★ | Solid, well-audited. Full f_ factory set for 15 materials. |
| 2 | Shokk Series | 30 | ★★★ | 20 dedicated SHOKK + 10 legacy metallic. All have unique paint+spec. 1 GGX fix applied tonight. |
| 3 | ★ COLORSHOXX | 25 | ★★★ | All 25 fully audited. Fine-field architecture. Married paint+spec pairs. Wave 3 designed (RESEARCH-041). |
| 4 | Metallic Standard | 22 | ★★ | Good variety. Some could be more distinct from each other. |
| 5 | ★ PARADIGM | 17 | ★★★ | Wild, extreme, genuinely unique finishes. All have dedicated spec functions. |
| 6 | Candy & Pearl | 17 | ★★ | Strong after GGX sweep. Dragon's Pearl Scale fixed tonight. orange_peel_gloss questionable fit. |
| 7 | Weathered & Aged | 17 | ★★ | Good variety. Patina/rust/sun-fade finishes well differentiated. |
| 8 | Industrial & Tactical | 16 | ★★ | Solid military/tactical finishes. vantablack potentially miscategorized. |
| 9 | Exotic Metal | 15 | ★★★ | ChromaFlair, Xirallic, anodized exotic all wired. Spectral color response per metal. |
| 10 | Chrome & Mirror | 14 | ★★ | All GGX-safe (chrome exception). chromaflair may be miscategorized here. |
| 11 | Carbon & Composite | 10 | ★★ | Good weave/grain detail in spec functions. |
| 12 | Extreme & Experimental | 10 | ★★ | Unique concepts (dark matter, superconductor, etc.). |
| 13 | Racing Heritage | 11 | ★★ | Motorsport finishes. Missing pit_lane_matte and heat_shield. |
| 14 | Premium Luxury | 10 | ★★ | Brand-themed finishes. satin_gold may be miscategorized. |
| 15 | OEM Automotive | 10 | ★ | Basic emergency/fleet vehicle finishes. Functional but not exciting. |
| 16 | Ceramic & Glass | 8 | ★ | Smallest category. Could use more entries (raku, celadon, stained glass). |

### Health Metrics

| Metric | Status |
|--------|--------|
| **GGX Floor Compliance** | ✅ All R≥15 for non-chrome (M<240). Fixed 100+ clips in GGX sweep (03-30). Fixed spec_shokk_dual tonight. |
| **3-Copy Sync** | ✅ All modified files synced and md5-verified tonight. |
| **Lazy Function Detection** | ✅ No remaining lazy finishes detected. quantum_foam/infinite_finish split (03-30). |
| **Registry Patches** | ✅ All 18 patch files audited, all function references properly imported. |
| **Fusions Quality** | ✅ Factory pattern, parametrically distinct. 150/150 non-lazy. |
| **COLORSHOXX Marriage** | ✅ 25/25 seed-married pairs verified. All use fine-field architecture. |

### Top 5 Priorities for Next Dev Push

1. **Implement COLORSHOXX Wave 3** — 25 finishes fully designed in RESEARCH-041 (seeds 9030-9054). Ready for Dev Agent. Add to structural_color.py + registry + JS.

2. **Category miscategorization fixes** — Move chromaflair from Chrome to Exotic Metal, liquid_obsidian from Chrome to Extreme, vantablack from Industrial to Extreme. Remove ceramic/piano_black duplicates from Foundation.

3. **Implement 19 COLORSHOXX finishes from RESEARCH-037/038** — These are additional finishes designed by the Research Agent (intensity shifters, temperature shifts, prismatic, etc.) that haven't been coded yet.

4. **Ceramic & Glass expansion** — Smallest category (8 bases). Add: raku pottery, celadon glaze, stained glass, blown glass, Venetian mirror, bone china, tempered steel glass, electrochromic glass.

5. **OEM Automotive enrichment** — Currently the weakest category in terms of spec detail. The spec functions are basic. Could benefit from paint_v2 upgrades with spray-booth imperfections, factory dust nibs, dealer-prep polish patterns.

---

## RESEARCH-041: COLORSHOXX Wave 3 — 25 New Finish Designs (Seeds 9030-9054)

**Date: 2026-03-31 | Agent: Hermes Agent | Mission: Complete design specs for 25 Wave 3 COLORSHOXX finishes**

Seeds 9030-9054. All use `_cx_fine_field` + `_cx_ultra_micro` architecture. Organized into 5 categories of 5 finishes each.

---

### CATEGORY A: Gradient Reveals (9030-9034)
*A hidden color gradient only appears at specular angle — at normal incidence looks like a single color.*

**A1: cx_ember_gradient (seed 9030)**
Looks solid dark charcoal at normal. At specular, a gradient from deep ember red → bright orange → gold is revealed.
- Paint C1: [0.85, 0.30, 0.05] (ember orange), C2: [0.12, 0.10, 0.10] (charcoal)
- Spec: m_hi=245, m_lo=20, r_hi=15, r_lo=180, cc_hi=16, cc_lo=160
- ΔM=225

**A2: cx_ocean_gradient (seed 9031)**
Solid dark navy at normal. At specular, gradient from deep navy → cerulean → seafoam green reveals.
- Paint C1: [0.10, 0.75, 0.65] (seafoam), C2: [0.03, 0.06, 0.28] (deep navy)
- Spec: m_hi=240, m_lo=15, r_hi=15, r_lo=190, cc_hi=16, cc_lo=170
- ΔM=225

**A3: cx_sunset_gradient (seed 9032)**
Dark plum at normal. Specular reveals sunset: magenta → tangerine → gold.
- Paint C1: [0.92, 0.55, 0.12] (tangerine gold), C2: [0.25, 0.05, 0.20] (dark plum)
- Spec: m_hi=248, m_lo=18, r_hi=15, r_lo=200, cc_hi=16, cc_lo=180
- ΔM=230

**A4: cx_forest_gradient (seed 9033)**
Muddy dark olive at normal. Specular reveals lush gradient: dark forest → emerald → lime.
- Paint C1: [0.55, 0.85, 0.15] (bright lime), C2: [0.08, 0.15, 0.06] (dark forest)
- Spec: m_hi=242, m_lo=12, r_hi=15, r_lo=195, cc_hi=16, cc_lo=175
- ΔM=230

**A5: cx_dawn_gradient (seed 9034)**
Soft gray at normal. Specular reveals pink → peach → warm white dawn sky.
- Paint C1: [0.95, 0.78, 0.68] (warm peach), C2: [0.35, 0.33, 0.36] (soft gray)
- Spec: m_hi=238, m_lo=50, r_hi=15, r_lo=120, cc_hi=16, cc_lo=90
- ΔM=188

---

### CATEGORY B: Temperature Shifts (9035-9039)
*Warm color ↔ cool color — the car shifts between warm and cool tones.*

**B1: cx_equinox (seed 9035)**
Warm amber-gold ↔ cool ice-blue. The quintessential warm/cool shift.
- Paint C1: [0.88, 0.65, 0.10] (amber gold), C2: [0.10, 0.45, 0.85] (ice blue)
- Spec: m_hi=240, m_lo=60, r_hi=15, r_lo=90, cc_hi=16, cc_lo=52
- ΔM=180

**B2: cx_magma_frost (seed 9036)**
Molten lava red-orange ↔ arctic frost blue-white. Extreme temperature.
- Paint C1: [0.90, 0.25, 0.02] (molten lava), C2: [0.72, 0.82, 0.92] (arctic frost)
- Spec: m_hi=245, m_lo=55, r_hi=15, r_lo=95, cc_hi=16, cc_lo=55
- ΔM=190

**B3: cx_autumn_winter (seed 9037)**
Warm russet-brown ↔ steel blue-gray. Seasonal shift.
- Paint C1: [0.70, 0.35, 0.10] (russet autumn), C2: [0.30, 0.38, 0.52] (steel winter)
- Spec: m_hi=235, m_lo=70, r_hi=15, r_lo=75, cc_hi=16, cc_lo=48
- ΔM=165

**B4: cx_desert_oasis (seed 9038)**
Hot desert sand-gold ↔ cool oasis teal-green.
- Paint C1: [0.85, 0.72, 0.35] (desert sand), C2: [0.08, 0.55, 0.48] (oasis teal)
- Spec: m_hi=242, m_lo=50, r_hi=15, r_lo=85, cc_hi=16, cc_lo=50
- ΔM=192

**B5: cx_coral_reef (seed 9039)**
Warm coral pink ↔ cool aquamarine. Tropical shift.
- Paint C1: [0.90, 0.42, 0.35] (coral pink), C2: [0.12, 0.68, 0.62] (aquamarine)
- Spec: m_hi=238, m_lo=65, r_hi=15, r_lo=80, cc_hi=16, cc_lo=48
- ΔM=173

---

### CATEGORY C: Single-Hue Intensity (9040-9044)
*One color family — brightness/metallic shift only. Like Morpho butterfly: same hue, different intensity.*

**C1: cx_morpho_blue (seed 9040)**
Deep navy blue → brilliant electric blue. Same hue family, intensity shift only.
- Paint C1: [0.08, 0.35, 0.92] (brilliant electric blue), C2: [0.02, 0.08, 0.30] (deep navy)
- Spec: m_hi=248, m_lo=10, r_hi=15, r_lo=200, cc_hi=16, cc_lo=180
- ΔM=238

**C2: cx_ruby_depth (seed 9041)**
Deep burgundy → brilliant ruby red. Same red family.
- Paint C1: [0.88, 0.08, 0.05] (brilliant ruby), C2: [0.25, 0.02, 0.04] (deep burgundy)
- Spec: m_hi=245, m_lo=15, r_hi=15, r_lo=180, cc_hi=16, cc_lo=160
- ΔM=230

**C3: cx_jade_glow (seed 9042)**
Deep forest green → brilliant jade. Same green family.
- Paint C1: [0.10, 0.82, 0.35] (brilliant jade), C2: [0.03, 0.22, 0.10] (deep forest)
- Spec: m_hi=242, m_lo=12, r_hi=15, r_lo=190, cc_hi=16, cc_lo=170
- ΔM=230

**C4: cx_amethyst_deep (seed 9043)**
Dark purple → brilliant amethyst violet. Same purple family.
- Paint C1: [0.60, 0.12, 0.85] (brilliant amethyst), C2: [0.15, 0.03, 0.22] (dark purple)
- Spec: m_hi=240, m_lo=18, r_hi=15, r_lo=185, cc_hi=16, cc_lo=165
- ΔM=222

**C5: cx_bronze_sun (seed 9044)**
Dark bronze → brilliant warm bronze. Same bronze family.
- Paint C1: [0.82, 0.58, 0.18] (brilliant bronze), C2: [0.28, 0.18, 0.06] (dark bronze)
- Spec: m_hi=245, m_lo=25, r_hi=15, r_lo=150, cc_hi=16, cc_lo=130
- ΔM=220

---

### CATEGORY D: Metallic-to-Matte (9045-9049)
*Chrome mirror zones next to dead-flat matte zones. Maximum material contrast.*

**D1: cx_chrome_velvet (seed 9045)**
Mirror chrome zones ↔ dead-flat black velvet matte. Material contrast, not color.
- Paint C1: [0.88, 0.90, 0.92] (chrome), C2: [0.04, 0.04, 0.05] (velvet black)
- Spec: m_hi=252, m_lo=0, r_hi=15, r_lo=252, cc_hi=16, cc_lo=252
- ΔM=252

**D2: cx_liquid_stone (seed 9046)**
Liquid chrome mercury zones ↔ rough matte concrete gray.
- Paint C1: [0.82, 0.84, 0.88] (liquid chrome), C2: [0.42, 0.40, 0.38] (concrete gray)
- Spec: m_hi=248, m_lo=5, r_hi=15, r_lo=230, cc_hi=16, cc_lo=220
- ΔM=243

**D3: cx_silk_armor (seed 9047)**
Smooth silk-sheen zones ↔ rough hammered armor plate.
- Paint C1: [0.75, 0.68, 0.60] (silk cream), C2: [0.25, 0.28, 0.30] (armor plate)
- Spec: m_hi=220, m_lo=30, r_hi=15, r_lo=180, cc_hi=16, cc_lo=160
- ΔM=190

**D4: cx_glass_sand (seed 9048)**
Mirror-glass chrome zones ↔ rough sandblasted matte.
- Paint C1: [0.90, 0.92, 0.95] (glass), C2: [0.55, 0.52, 0.48] (sand)
- Spec: m_hi=250, m_lo=8, r_hi=15, r_lo=245, cc_hi=16, cc_lo=240
- ΔM=242

**D5: cx_polish_patina (seed 9049)**
High-polish chrome zones ↔ oxidized patina matte green.
- Paint C1: [0.85, 0.88, 0.90] (polished chrome), C2: [0.20, 0.45, 0.30] (patina green)
- Spec: m_hi=248, m_lo=15, r_hi=15, r_lo=200, cc_hi=16, cc_lo=190
- ΔM=233

---

### CATEGORY E: Wild Cards (9050-9054)
*Most creative and unusual ideas. Push the engine.*

**E1: cx_bioluminescent (seed 9050)**
Near-black base with glowing bioluminescent cyan zones that flash at specular. Like deep-sea creatures.
- Paint C1: [0.05, 0.85, 0.75] (bioluminescent cyan), C2: [0.01, 0.02, 0.04] (abyss black)
- Spec: m_hi=235, m_lo=0, r_hi=15, r_lo=250, cc_hi=16, cc_lo=245
- ΔM=235

**E2: cx_lava_crust (seed 9051)**
Cracked black crust with molten orange-red visible in the "cracks" (high-field zones). Use 3-color.
- Paint: C1=[0.95, 0.60, 0.05] (molten lava), C2=[0.70, 0.20, 0.02] (cooling crust), C3=[0.08, 0.06, 0.05] (cold crust)
- Spec: m_vals=(240, 120, 5), r_vals=(15, 40, 230), cc_vals=(16, 25, 220)
- ΔM=235

**E3: cx_oil_water (seed 9052)**
Iridescent oil-film colors floating on "water" zones. 4-color prismatic.
- Paint: C1=[0.70, 0.20, 0.65] (oil magenta), C2=[0.15, 0.50, 0.75] (oil cyan), C3=[0.80, 0.70, 0.15] (oil gold), C4=[0.30, 0.35, 0.42] (water gray)
- Spec: m_vals=(235, 200, 220, 15), r_vals=(15, 20, 18, 180), cc_vals=(16, 18, 16, 160)
- ΔM=220

**E4: cx_plasma_bolt (seed 9053)**
Dark space-black base with crackling plasma-white lightning bolt zones. 3-color.
- Paint: C1=[0.95, 0.92, 0.98] (plasma white), C2=[0.25, 0.10, 0.55] (plasma purple), C3=[0.02, 0.01, 0.03] (space black)
- Spec: m_vals=(252, 180, 0), r_vals=(15, 25, 252), cc_vals=(16, 20, 250)
- ΔM=252

**E5: cx_zen_garden (seed 9054)**
Raked sand matte zones ↔ smooth polished stone zones. Meditative, organic.
- Paint C1: [0.65, 0.60, 0.52] (polished stone), C2: [0.82, 0.78, 0.68] (raked sand)
- Spec: m_hi=200, m_lo=8, r_hi=15, r_lo=220, cc_hi=16, cc_lo=200
- ΔM=192

---

### Implementation Checklist

- [ ] Add 25 paint+spec function pairs to `structural_color.py` (seeds 9030-9054)
- [ ] Cat A (9030-9034): 5 gradient reveals — use `_cx_paint_2color` / `_cx_spec_2color`
- [ ] Cat B (9035-9039): 5 temperature shifts — use `_cx_paint_2color` / `_cx_spec_2color`
- [ ] Cat C (9040-9044): 5 single-hue intensity — use `_cx_paint_2color` / `_cx_spec_2color`
- [ ] Cat D (9045-9049): 5 metallic-to-matte — use `_cx_paint_2color` / `_cx_spec_2color`
- [ ] Cat E (9050-9054): 5 wild cards — E2/E3/E4 use `_cx_paint_3color`/`_cx_paint_4color`, E1/E5 use `_cx_paint_2color`
- [ ] Add 25 registry entries to `base_registry_data.py` COLORSHOXX section (all 3 copies)
- [ ] Add 25 JS BASE entries to `paint-booth-0-finish-data.js` (all 3 copies)
- [ ] Update BASE_GROUPS `"★ COLORSHOXX"` with all 25 new IDs (all 3 JS copies)
- [ ] Sync all 3 copies of every modified file

---

## RESEARCH-040: COLORSHOXX Complete System Documentation & QA Audit Results

**Date: 2026-03-31 | Agent: Hermes Agent (Dev+QA session) | Mission: Full system doc + audit of all 25 finishes**

### Architecture: How COLORSHOXX Paint+Spec Marriage Works

COLORSHOXX finishes are fundamentally different from every other category in SPB. Here's the full architecture:

**The Marriage Principle:**
1. A shared spatial **field** divides the texture into zones (high-field vs low-field)
2. The **paint function** maps Color A to high-field zones and Color B to low-field zones
3. The **spec function** uses the IDENTICAL field (same helper, same seed) to assign different M/R/CC per zone
4. High-field zones get HIGH metallic (M=220-250) + LOW roughness (R=15) = mirror flash at specular angle
5. Low-field zones get LOW metallic (M=0-90) + HIGH roughness (R=65-250) = matte, visible at normal incidence
6. iRacing's PBR renderer does the Fresnel: high-M zones "pop" at specular, low-M zones stay steady
7. Result: the car appears to FLIP between two colors depending on viewing angle

**Why this works vs Chameleon:** Chameleon rotates through ALL hues using a continuous shift — wide M range not needed because the hue change itself creates the angle effect. COLORSHOXX uses STATIC colors — the ONLY mechanism for angle-dependent differentiation is M differential. Needs ΔM=80-220+ to create visible contrast.

**Key helpers (structural_color.py):**

| Helper | Noise Scales | Purpose |
|--------|-------------|---------|
| `_cx_fine_field(shape, seed)` | 4/8/16 + 2/4 + 32/64 | Primary zone field — tight, car-scale visible texture |
| `_cx_ultra_micro(shape, seed)` | 1/2/3 | Per-flake shimmer within zones |
| `_cx_paint_2color(...)` | Calls fine_field + ultra_micro | Generic 2-color paint with fine detail |
| `_cx_spec_2color(...)` | Calls fine_field + ultra_micro | Generic 2-color spec with extreme M/R ranges |
| `_cx_3zone(field)` | — | Splits field into low/mid/high for 3-color finishes |
| `_cx_4zone(field)` | — | Splits field into 4 zones for 4-color finishes |
| `_cx_paint_3color(...)` | Calls fine_field | 3-color paint helper |
| `_cx_spec_3color(...)` | Calls fine_field | 3-color spec helper |
| `_cx_paint_4color(...)` | Calls fine_field | 4-color paint helper |
| `_cx_spec_4color(...)` | Calls fine_field | 4-color spec helper |
| `_colorshoxx_field(...)` | 32/64/128 + 16/32 | LEGACY coarse field — ORPHANED, no longer used |
| `_colorshoxx_micro(...)` | 2/4/8 | LEGACY micro — ORPHANED, no longer used |

**Seed offset scheme:** Seeds 9001-9029, one per finish. Both paint and spec use `seed + offset` ensuring pixel-perfect field alignment.

### Complete QA Audit Results (25 Finishes)

**Audit date: 2026-03-31 | All checks performed programmatically**

#### Check 1: Seed Marriage — 25/25 PASS ✓

Every paint+spec pair uses identical seed offsets. No spatial drift between paint zones and spec zones.

#### Check 2: GGX Roughness Floor — 25/25 PASS ✓

All spec functions route through `_cx_spec_2color` / `_cx_spec_3color` / `_cx_spec_4color` helpers, which all clip R via `np.clip(R, 15, 255)`. No GGX artifact risk.

#### Check 3: Color Vibrancy — 25/25 PASS ✓

All color pairs have Euclidean distance > 0.3 in RGB space (range: 0.46 to 1.49). Two finishes (Chrome Void, White Lightning) flagged as low-saturation — both are intentional chrome/white designs where the contrast is luminance-based rather than hue-based. Not a defect.

#### Check 4: M/R Zone Contrast — 24/25 EXCELLENT, 1 ACCEPTABLE

| Rating | Count | Finishes |
|--------|-------|----------|
| ★★★ (ΔM ≥ 180) | 18 | chrome_void, midnight_chrome, obsidian_gold, hellfire, apocalypse, supernova, white_lightning, toxic_chrome, acid_rain, dragon_scale, rose_chrome, electric_storm, frozen_nebula, ocean_trench, neon_abyss, glacier_fire, venom, blood_mercury |
| ★★ (ΔM 120-179) | 6 | inferno(163), arctic(177), phantom(200), solar(155), aurora_borealis(175), prism_shatter(160) |
| ★ (ΔM 80-119) | 1 | royal_spectrum(98) — 4-color, uses color variety over M contrast |
| ⚠ (ΔM < 80) | 0 | none |

### Per-Finish Reference Table

| # | ID | Name | Type | Colors | Seed | M Range | ΔM | R Range |
|---|-----|------|------|--------|------|---------|-----|---------|
| 01 | cx_inferno | Inferno Flip | 2-color | Crimson ↔ Midnight Blue | 9001 | 75-238 | 163 | 15-80 |
| 02 | cx_arctic | Arctic Mirage | 2-color | Ice Silver ↔ Deep Teal | 9002 | 65-242 | 177 | 15-85 |
| 03 | cx_venom | Venom Shift | 2-color | Toxic Green ↔ Black Purple | 9003 | 15-235 | 220 | 15-140 |
| 04 | cx_solar | Solar Flare | 2-color | Gold ↔ Copper Red | 9004 | 90-245 | 155 | 15-65 |
| 05 | cx_phantom | Phantom Violet | 2-color | Electric Violet ↔ Gunmetal | 9005 | 40-240 | 200 | 15-100 |
| 06 | cx_chrome_void | Chrome Void | 2-color | Chrome Silver ↔ Matte Black | 9010 | 0-245 | 245 | 15-220 |
| 07 | cx_blood_mercury | Blood Mercury | 2-color | Chrome Silver ↔ Crimson | 9011 | 60-245 | 185 | 15-80 |
| 08 | cx_neon_abyss | Neon Abyss | 2-color | Hot Pink ↔ Black-Green | 9012 | 15-230 | 215 | 15-180 |
| 09 | cx_glacier_fire | Glacier Fire | 2-color | Icy Chrome ↔ Molten Orange | 9013 | 30-240 | 210 | 15-140 |
| 10 | cx_obsidian_gold | Obsidian Gold | 2-color | 24k Gold ↔ Obsidian Black | 9014 | 5-248 | 243 | 15-230 |
| 11 | cx_electric_storm | Electric Storm | 2-color | Electric Blue ↔ Dark Gray | 9015 | 20-238 | 218 | 15-160 |
| 12 | cx_rose_chrome | Rose Chrome | 2-color | Rose Gold ↔ Burgundy | 9016 | 25-245 | 220 | 15-190 |
| 13 | cx_toxic_chrome | Toxic Chrome | 2-color | Acid Green ↔ Brown-Black | 9017 | 8-242 | 234 | 15-200 |
| 14 | cx_midnight_chrome | Midnight Chrome | 2-color | Dark Blue ↔ Flat Black | 9018 | 0-248 | 248 | 15-248 |
| 15 | cx_white_lightning | White Lightning | 2-color | White Chrome ↔ Charcoal | 9019 | 10-250 | 240 | 15-200 |
| 16 | cx_aurora_borealis | Aurora Borealis | 3-color | Green + Teal + Violet | 9020 | 60-235 | 175 | 15-100 |
| 17 | cx_dragon_scale | Dragon Scale | 3-color | Gold + Ember + Charcoal | 9021 | 5-248 | 243 | 15-230 |
| 18 | cx_frozen_nebula | Frozen Nebula | 3-color | Ice Chrome + Blue + Purple | 9022 | 30-250 | 220 | 15-150 |
| 19 | cx_hellfire | Hellfire | 3-color | White-Hot + Lava + Scorched | 9023 | 0-250 | 250 | 15-250 |
| 20 | cx_ocean_trench | Ocean Trench | 3-color | Bio Teal + Navy + Black | 9024 | 5-230 | 225 | 15-200 |
| 21 | cx_supernova | Supernova | 4-color | Chrome + Blue + Magenta + Void | 9025 | 0-250 | 250 | 15-250 |
| 22 | cx_prism_shatter | Prism Shatter | 4-color | Red + Gold + Teal + Indigo | 9026 | 80-240 | 160 | 15-70 |
| 23 | cx_acid_rain | Acid Rain | 4-color | Toxic Yellow + Green + Purple + Ash | 9027 | 15-245 | 230 | 15-180 |
| 24 | cx_royal_spectrum | Royal Spectrum | 4-color | Silver + Sapphire + Ruby + Emerald | 9028 | 150-248 | 98 | 15-40 |
| 25 | cx_apocalypse | Apocalypse | 4-color | Chrome + Blood + Rust + Black | 9029 | 0-252 | 252 | 15-252 |

### Cleanup Note

The legacy helpers `_colorshoxx_field` (scales 32/64/128) and `_colorshoxx_micro` (scales 2/4/8) are still in the file at lines 22-38. They are **no longer called by any of the 25 finishes** — all now use the Wave 2 fine-field helpers. Safe to remove in a future cleanup pass.

### Suggestions for Next 25 Finishes (Wave 3)

See RESEARCH-041 (forthcoming) for complete Wave 3 designs. Key areas to explore:
- **Single-hue intensity shifts** (like Morpho blue — one color family, brightness/metallic change only)
- **Temperature shifts** (warm ↔ cool within the same finish)
- **Gradient reveals** (a hidden color gradient that only appears at specular angle)
- **Voronoi/cellular patterns** (using `_voronoi_cells` from shokk_series.py instead of noise fields)
- **Asymmetric 3-zone** finishes where the middle zone is the "hero" color

---

## RESEARCH-039: COLORSHOXX Status Audit — What's Implemented vs What's Pending

**Date: 2026-03-30 | Agent: SPB Research Agent | Supersedes stale PRIORITIES.md entry**

### Current Live State (as of 2026-03-30)

COLORSHOXX has **25 finishes fully implemented and wired** — not 5 as PRIORITIES.md stated. Previous sessions completed the full Wave 1 + Wave 2 rollout.

**Wave 1 (5 finishes — large organic fields, seed offsets +9001 to +9005):**

| ID | Name | Colors |
|----|------|--------|
| `cx_inferno` | Inferno Flip | Crimson Red ↔ Midnight Blue |
| `cx_arctic` | Arctic Mirage | Ice Silver ↔ Deep Teal |
| `cx_venom` | Venom Shift | Toxic Green ↔ Black Purple |
| `cx_solar` | Solar Flare | Gold ↔ Copper Red |
| `cx_phantom` | Phantom Violet | Electric Violet ↔ Gunmetal |

**Wave 2 Extreme Dual-Tone (10 finishes — fine fields `_cx_fine_field`, seed offsets +9010 to +9019):**

| ID | Colors |
|----|--------|
| `cx_chrome_void` | Mirror Chrome ↔ Absolute Matte Black (M=245/0, R=15/220) |
| `cx_blood_mercury` | Chrome Silver ↔ Arterial Crimson |
| `cx_neon_abyss` | Hot Pink ↔ Abyssal Black-Green |
| `cx_glacier_fire` | Icy White-Blue ↔ Molten Orange-Red |
| `cx_obsidian_gold` | 24k Gold ↔ Volcanic Obsidian (M=248/5 — second widest ΔM) |
| `cx_electric_storm` | Electric Blue ↔ Thundercloud Dark |
| `cx_rose_chrome` | Rose Gold ↔ Burgundy Velvet |
| `cx_toxic_chrome` | Acid Green ↔ Chemical Brown |
| `cx_midnight_chrome` | Dark Blue ↔ Pure Black (M=248/0, R=15/248 — widest ΔM and ΔR) |
| `cx_white_lightning` | Blinding White ↔ Charcoal |

**Wave 2 Three-Color (5 finishes — fine fields, seed offsets +9020 to +9024):**

| ID | Zone Colors (Hi/Mid/Lo) | M Hi/Mid/Lo |
|----|-------------------------|-------------|
| `cx_aurora_borealis` | Green / Teal / Violet Purple | 235 / 140 / 60 |
| `cx_dragon_scale` | Chrome Gold / Ember Orange / Charcoal Black | 248 / 180 / 5 |
| `cx_frozen_nebula` | Ice White / Cosmic Blue / Deep Purple | 250 / 160 / 30 |
| `cx_hellfire` | White-Hot / Lava Orange / Scorched Black | 250 / 150 / 0 |
| `cx_ocean_trench` | Bioluminescent Teal / Deep Navy / Abyssal Black | 230 / 120 / 5 |

**Wave 2 Four-Color (5 finishes — fine fields, seed offsets +9025 to +9029):**

| ID | Zone Colors | Approach |
|----|------------|---------|
| `cx_supernova` | White + Blue + Magenta + Black | 4-zone stellar death, widest M range (0–250) |
| `cx_prism_shatter` | Red + Gold + Teal + Indigo | All 4 zones metallic (M 80–240), only R varies |
| `cx_acid_rain` | Yellow + Green + Purple + Gray | Graduating M (15/60/180/245) — zone escalation |
| `cx_royal_spectrum` | Silver + Sapphire + Ruby + Emerald | Near-uniform high M (150–248), all premium metallic |
| `cx_apocalypse` | White + Red + Orange + Black | Extreme span: M 0–252, R 15–252, CC 16–252 |

**Registration Status:**
- All 25 in `engine/base_registry_data.py` (lines 735–778) ✓
- All 25 in `paint-booth-0-finish-data.js` under `"★ COLORSHOXX"` group ✓
- `structural_color.py` 3-copy sync confirmed: all 3 at 27950 bytes ✓

### What RESEARCH-037 + RESEARCH-038 Proposed (NOT YET IN CODE)

19 additional COLORSHOXX finishes with full Python pseudocode, ready for Dev Agent implementation. All use `_colorshoxx_field` (large-scale helper) — NOT `_cx_fine_field` (Wave 2's helper). No spatial conflicts.

**Seed allocation for the 19 new finishes (using `_colorshoxx_field`):**

| IMPL | ID | Category | Seed offset | Code location |
|------|-----|----------|-------------|---------------|
| 1 | `cx_abyss` | Intensity Shifter | +9006 | RESEARCH-037 |
| 2 | `cx_forge` | Temperature Shift | +9007 | RESEARCH-037 |
| 3 | `cx_spectrum_veil` | Gradient Reveal | +9008 | RESEARCH-037 |
| 4 | `cx_mosaic` | Multi-Zone Prismatic | +9009 | RESEARCH-037 |
| 5 | `cx_sunset` | Temperature Shift | +9010 | RESEARCH-037 |
| 6 | `cx_obsidian_blaze` | Intensity Shifter | +9011 | RESEARCH-038 |
| 7 | `cx_emerald_depth` | Intensity Shifter | +9012 | RESEARCH-038 |
| 8 | `cx_tungsten` | Intensity Shifter | +9013 | RESEARCH-038 |
| 9 | `cx_plutonium` | Intensity Shifter | +9014 | RESEARCH-038 |
| 10 | `cx_copper_dawn` | Temperature Shift | +9015 | RESEARCH-038 |
| 11 | `cx_magma_steel` | Temperature Shift | +9016 | RESEARCH-038 |
| 12 | `cx_eclipse` | Gradient Reveal | +9017 | RESEARCH-038 |
| 13 | `cx_midnight_chroma` | Gradient Reveal | +9018 | RESEARCH-038 |
| 14 | `cx_ghost_fire` | Gradient Reveal | +9019 | RESEARCH-038 |
| 15 | `cx_titanium_bloom` | Gradient Reveal | +9020 | RESEARCH-038 (NOTE: use +9020, NOT +9019) |
| 16 | `cx_wyrm_scale` | Multi-Zone Prismatic | +9021 | RESEARCH-038 (⚠️ RENAMED — see below) |
| 17 | `cx_prism_fragment` | Multi-Zone Prismatic | +9022 | RESEARCH-038 |
| 18 | `cx_kaleidoscope` | Multi-Zone Prismatic | +9023 | RESEARCH-038 |
| 19 | `cx_spectral_fracture` | Multi-Zone Prismatic | +9024 | RESEARCH-038 |

### ⚠️ CRITICAL: cx_dragon_scale Naming Conflict

RESEARCH-038 proposed a Multi-Zone Prismatic finish named `cx_dragon_scale`. **This name already exists** as a Wave 2 three-color finish (chrome gold + ember orange + charcoal black in `_cx_paint_3color`). Implementing the RESEARCH-038 version under that name would overwrite or conflict with the existing registry entry.

**Resolution:** Rename the RESEARCH-038 prismatic finish to `cx_wyrm_scale`.

- RESEARCH-038's description: "Uses `_voronoi_edges` for edge detection. Edge pixels: M=240, R=16. Interior: M=140, R=40. Creates physical 'scale-tip catches light' behavior."
- New name `cx_wyrm_scale` — preserves the dragon/reptile theme while being unique
- Use seed offset `+9021` (was IMPL-16 in the original numbering)
- JS entry: `{ id: "cx_wyrm_scale", name: "CX Wyrm Scale", desc: "Voronoi scale-tip lighting — edge-tip facets M=240 mirror-flash, scale body M=140 metallic hold. Physical dragon scale behavior.", swatch: "#BB8800" }`
- Registry: `"cx_wyrm_scale": {"base_spec_fn": spec_cx_wyrm_scale, "M": 190, "R": 32, "CC": 20, "paint_fn": paint_cx_wyrm_scale}`

### Seed Safety Analysis

**No actual seed conflicts exist** between the 19 proposed finishes and the 20 already-implemented Wave 2 finishes, despite using overlapping numeric offsets (+9010 through +9024). The reason:

- Wave 2 finishes call `_cx_fine_field(shape, seed + offset)` — noise scales `[4,8,16]+[2,4]+[32,64]`
- Proposed finishes call `_colorshoxx_field(shape, seed + offset)` — noise scales `[32,64,128]+[16,32]`

Different noise scale parameters → fundamentally different spatial outputs → no visual correlation even at same numeric offset.

**Only within-family conflicts are dangerous.** Verify no two `_colorshoxx_field`-based finishes share the same seed+offset:
- Existing Wave 1: +9001, +9002, +9003, +9004, +9005 ✓
- Proposed 19: +9006 through +9024 (no repeats) ✓

### Import Requirements for the 19 New Finishes

5 finishes (cx_eclipse, cx_midnight_chroma, cx_ghost_fire, cx_titanium_bloom, cx_spectrum_veil) use `hsv_to_rgb_vec`. Add to top of `structural_color.py`:

```python
from engine.chameleon import hsv_to_rgb_vec
```

4 Multi-Zone Prismatic finishes (cx_mosaic, cx_wyrm_scale, cx_prism_fragment, cx_kaleidoscope, cx_spectral_fracture) use Voronoi/BZ helpers:

```python
from engine.shokk_series import _voronoi_cells, _voronoi_edges, _bz_reaction
```

**Dev Agent checklist:**
- [ ] Add `hsv_to_rgb_vec` import to `structural_color.py` (all 3 copies)
- [ ] Add shokk_series imports to `structural_color.py` (all 3 copies)
- [ ] Implement 19 paint/spec function pairs following RESEARCH-037 (5 functions) + RESEARCH-038 (14 functions)
- [ ] `cx_dragon_scale` in RESEARCH-038 → implement as `cx_wyrm_scale`
- [ ] `cx_titanium_bloom` seed = `+9020` (not +9019 — see RESEARCH-038 typo note)
- [ ] Add 19 registry entries to `engine/base_registry_data.py` (all 3 copies)
- [ ] Add 19 JS `BASES` entries to `paint-booth-0-finish-data.js` (all 3 copies)
- [ ] Update `BASE_GROUPS["★ COLORSHOXX"]` with all 19 new IDs (all 3 copies)
- [ ] GGX verify: all R clips use `np.clip(R, 15, 255)` — pseudocode already verified per-function
- [ ] 3-copy sync: root + `electron-app/server/` + `electron-app/server/pyserver/_internal/`

---

## RESEARCH-038: COLORSHOXX Dev Handoff — 14 Remaining Implementation Specs

**Date: 2026-03-30 | Agent: SPB Research Agent | Supplements: RESEARCH-037 (5 specs)**

Completes the full 20-finish new COLORSHOXX library. Seeds +9011–+9024 (continuing from RESEARCH-037's +9006–+9010).
All use the `_colorshoxx_field` + `_colorshoxx_micro` helpers already in `structural_color.py`.

### Import Additions Required at Top of structural_color.py

```python
# Current: from engine.core import multi_scale_noise
# Add:
from engine.chameleon import hsv_to_rgb_vec          # gradient reveals + prismatic
from engine.shokk_series import (_voronoi_cells,     # prismatic multi-zone
                                  _voronoi_edges,    # dragon_scale, spectral_fracture
                                  _bz_reaction)      # spectral_fracture
```

### GGX Floor Rule (All 14 Finishes)

All R channels: `np.clip(R, 15, 255)` — never `np.clip(R, 0, 255)`. Every minimum R value below is verified ≥ 15.

---

### IMPL-6: "Obsidian Blaze" — Intensity Shifter `cx_obsidian_blaze` (seed offset +9011)

**Effect:** From absolute void (near-black) to volcanic crimson flash — 205 ΔM, the second-largest in the library. Surface appears black/dead at normal incidence; crimson fire erupts at specular.

```python
def paint_colorshoxx_obsidian_blaze(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9011)
    micro = _colorshoxx_micro((h, w), seed + 9011)
    crimson  = np.array([0.75, 0.06, 0.04], dtype=np.float32)   # HIGH-M zone: the flash
    void_blk = np.array([0.05, 0.04, 0.06], dtype=np.float32)   # LOW-M zone: the base
    blend_field = np.clip(field + (micro - 0.5) * 0.16, 0, 1)
    color = (crimson[np.newaxis, np.newaxis, :] * blend_field[:,:,np.newaxis] +
             void_blk[np.newaxis, np.newaxis, :] * (1 - blend_field[:,:,np.newaxis]))
    blend = np.clip(pm * 0.93, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_obsidian_blaze(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9011)
    micro = _colorshoxx_micro((h, w), seed + 9011)
    M  = 30.0  + field * 205.0 * sm + micro * 8.0 * sm   # range 30 (void) → 235 (crimson flash)
    R  = 75.0  - field * 57.0  * sm + micro * 4.0 * sm   # range 75 (void=matte) → 18 (crimson=mirror) ✓GGX
    CC = 42.0  - field * 26.0                             # range 42 (void) → 16 (crimson=max gloss)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_obsidian_blaze": {"base_spec_fn": spec_colorshoxx_obsidian_blaze, "M": 130, "R": 46, "CC": 29, "paint_fn": paint_colorshoxx_obsidian_blaze, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_obsidian_blaze", name: "COLORSHOXX Obsidian Blaze", desc: "Near-black void to volcanic crimson — from dead void to fire flash at specular. Darkest secondary in the library.", swatch: "#CC0A06" }`

---

### IMPL-7: "Emerald Depth" — Intensity Shifter `cx_emerald_depth` (seed offset +9012)

**Effect:** Dark forest undergrowth at normal view → brilliant jewel-jade flash at specular. Both are green, but the delta is ~3 stop exposure difference. Like looking through pine trees vs catching a sunlit emerald.

```python
def paint_colorshoxx_emerald_depth(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9012)
    micro = _colorshoxx_micro((h, w), seed + 9012)
    jade   = np.array([0.10, 0.82, 0.22], dtype=np.float32)   # HIGH-M: brilliant jade flash
    forest = np.array([0.04, 0.22, 0.08], dtype=np.float32)   # LOW-M: dark forest base
    blend_field = np.clip(field + (micro - 0.5) * 0.14, 0, 1)
    color = (jade[np.newaxis, np.newaxis, :] * blend_field[:,:,np.newaxis] +
             forest[np.newaxis, np.newaxis, :] * (1 - blend_field[:,:,np.newaxis]))
    blend = np.clip(pm * 0.90, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_emerald_depth(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9012)
    micro = _colorshoxx_micro((h, w), seed + 9012)
    M  = 55.0  + field * 160.0 * sm + micro * 7.0 * sm   # range 55 → 215 ✓
    R  = 72.0  - field * 52.0  * sm + micro * 4.0 * sm   # range 72 → 20 ✓GGX min=20
    CC = 38.0  - field * 22.0                             # range 38 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_emerald_depth": {"base_spec_fn": spec_colorshoxx_emerald_depth, "M": 135, "R": 46, "CC": 27, "paint_fn": paint_colorshoxx_emerald_depth, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_emerald_depth", name: "COLORSHOXX Emerald Depth", desc: "Dark forest green to brilliant jade flash — same hue family, 3-stop intensity swing at specular.", swatch: "#1AD038" }`

---

### IMPL-8: "Tungsten Cobalt" — Intensity Shifter `cx_tungsten` (seed offset +9013)

**Effect:** Cold tungsten grey at normal → electric cobalt blue blast at specular. Achromatic to hyper-chromatic — the grey looks factory-unpainted until light catches it.

```python
def paint_colorshoxx_tungsten(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9013)
    micro = _colorshoxx_micro((h, w), seed + 9013)
    cobalt  = np.array([0.10, 0.25, 0.95], dtype=np.float32)  # HIGH-M: electric cobalt
    tungsten = np.array([0.25, 0.27, 0.30], dtype=np.float32)  # LOW-M: cold grey
    blend_field = np.clip(field + (micro - 0.5) * 0.13, 0, 1)
    color = (cobalt[np.newaxis, np.newaxis, :] * blend_field[:,:,np.newaxis] +
             tungsten[np.newaxis, np.newaxis, :] * (1 - blend_field[:,:,np.newaxis]))
    blend = np.clip(pm * 0.88, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_tungsten(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9013)
    micro = _colorshoxx_micro((h, w), seed + 9013)
    M  = 60.0  + field * 160.0 * sm + micro * 6.0 * sm   # range 60 → 220 ✓
    R  = 65.0  - field * 46.0  * sm + micro * 4.0 * sm   # range 65 → 19 ✓GGX min=19
    CC = 35.0  - field * 19.0                             # range 35 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_tungsten": {"base_spec_fn": spec_colorshoxx_tungsten, "M": 140, "R": 42, "CC": 25, "paint_fn": paint_colorshoxx_tungsten, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_tungsten", name: "COLORSHOXX Tungsten Cobalt", desc: "Cold tungsten grey base — electric cobalt blue erupts at specular. Factory grey to hyper-chromatic reveal.", swatch: "#1A40F0" }`

---

### IMPL-9: "Plutonium" — Intensity Shifter `cx_plutonium` (seed offset +9014)

**Effect:** Silver-grey at rest → neon green radioactive flash. The most unexpected: looks like standard silver metallic until the right angle reveals nuclear green. Maximum surprise factor.

```python
def paint_colorshoxx_plutonium(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9014)
    micro = _colorshoxx_micro((h, w), seed + 9014)
    neon_g  = np.array([0.25, 0.95, 0.10], dtype=np.float32)   # HIGH-M: neon green flash
    silver  = np.array([0.48, 0.48, 0.50], dtype=np.float32)   # LOW-M: silver-grey base
    blend_field = np.clip(field + (micro - 0.5) * 0.14, 0, 1)
    color = (neon_g[np.newaxis, np.newaxis, :] * blend_field[:,:,np.newaxis] +
             silver[np.newaxis, np.newaxis, :] * (1 - blend_field[:,:,np.newaxis]))
    blend = np.clip(pm * 0.89, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_plutonium(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9014)
    micro = _colorshoxx_micro((h, w), seed + 9014)
    M  = 65.0  + field * 165.0 * sm + micro * 7.0 * sm   # range 65 → 230 ✓
    R  = 60.0  - field * 42.0  * sm + micro * 4.0 * sm   # range 60 → 18 ✓GGX min=18
    CC = 30.0  - field * 14.0                             # range 30 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_plutonium": {"base_spec_fn": spec_colorshoxx_plutonium, "M": 148, "R": 39, "CC": 23, "paint_fn": paint_colorshoxx_plutonium, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_plutonium", name: "COLORSHOXX Plutonium", desc: "Silver-grey to neon green flash — looks standard metallic until the right angle reveals radioactive green. Maximum surprise.", swatch: "#40F21A" }`

---

### IMPL-10: "Copper Dawn" — Temperature Shift `cx_copper_dawn` (seed offset +9015)

**Effect:** Warm rose-copper at normal → pastel periwinkle dawn at specular. The most refined temperature shift — both colors are mid-saturation pastels. Elegant, not aggressive.

```python
def paint_colorshoxx_copper_dawn(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9015)
    micro = _colorshoxx_micro((h, w), seed + 9015)
    rose_copper  = np.array([0.75, 0.38, 0.22], dtype=np.float32)   # HIGH-M: warm rose copper
    periwinkle   = np.array([0.55, 0.58, 0.85], dtype=np.float32)   # LOW-M: dawn periwinkle
    blend_field = np.clip(field + (micro - 0.5) * 0.12, 0, 1)
    color = (rose_copper[np.newaxis, np.newaxis, :] * blend_field[:,:,np.newaxis] +
             periwinkle[np.newaxis, np.newaxis, :] * (1 - blend_field[:,:,np.newaxis]))
    blend = np.clip(pm * 0.87, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_copper_dawn(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9015)
    micro = _colorshoxx_micro((h, w), seed + 9015)
    M  = 90.0  + field * 110.0 * sm + micro * 6.0 * sm   # range 90 → 200 ✓
    R  = 50.0  - field * 28.0  * sm + micro * 4.0 * sm   # range 50 → 22 ✓GGX min=22
    CC = 32.0  - field * 16.0                             # range 32 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_copper_dawn": {"base_spec_fn": spec_colorshoxx_copper_dawn, "M": 145, "R": 36, "CC": 24, "paint_fn": paint_colorshoxx_copper_dawn, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_copper_dawn", name: "COLORSHOXX Copper Dawn", desc: "Rose copper warmth to dawn periwinkle — the most refined temperature shift, pastel-elegant both ways.", swatch: "#C06038" }`

---

### IMPL-11: "Magma Steel" — Temperature Shift `cx_magma_steel` (seed offset +9016)

**Effect:** Volcanic magma red at rest → cold tempered steel at specular. The blade just pulled from the forge vs cooled and hardened. Masculine temperature contrast.

```python
def paint_colorshoxx_magma_steel(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9016)
    micro = _colorshoxx_micro((h, w), seed + 9016)
    magma  = np.array([0.88, 0.16, 0.04], dtype=np.float32)   # HIGH-M: volcanic magma red
    steel  = np.array([0.55, 0.62, 0.72], dtype=np.float32)   # LOW-M: cold steel blue-grey
    blend_field = np.clip(field + (micro - 0.5) * 0.15, 0, 1)
    color = (magma[np.newaxis, np.newaxis, :] * blend_field[:,:,np.newaxis] +
             steel[np.newaxis, np.newaxis, :] * (1 - blend_field[:,:,np.newaxis]))
    blend = np.clip(pm * 0.90, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_magma_steel(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9016)
    micro = _colorshoxx_micro((h, w), seed + 9016)
    M  = 70.0  + field * 145.0 * sm + micro * 7.0 * sm   # range 70 → 215 ✓
    R  = 55.0  - field * 35.0  * sm + micro * 4.0 * sm   # range 55 → 20 ✓GGX min=20
    CC = 34.0  - field * 18.0                             # range 34 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_magma_steel": {"base_spec_fn": spec_colorshoxx_magma_steel, "M": 143, "R": 37, "CC": 25, "paint_fn": paint_colorshoxx_magma_steel, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_magma_steel", name: "COLORSHOXX Magma Steel", desc: "Volcanic magma red to cold tempered steel — forge-hot base, blade-cool specular. Industrial masculine.", swatch: "#E02808" }`

---

### IMPL-12: "Eclipse Trail" — Gradient Reveal `cx_eclipse` (seed offset +9017)

**Effect:** Near-black surface hides a blue→violet→teal aurora gradient at V=0.35. Completely invisible at flat diffuse light. At specular: a corona of deep blue-purple-teal sweeps across the dark surface. Like a solar eclipse with a colored chromosphere.

**Paint approach:** Two-layer blend. Near-black base everywhere + hidden aurora using `hsv_to_rgb_vec` driven by field. Aurora blends in only at high-field zones (those same zones get high M).

```python
def paint_colorshoxx_eclipse(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9017)
    micro = _colorshoxx_micro((h, w), seed + 9017)
    # Near-black base (always present)
    base_r = np.full((h, w), 0.06, dtype=np.float32)
    base_g = np.full((h, w), 0.07, dtype=np.float32)
    base_b = np.full((h, w), 0.10, dtype=np.float32)
    # Hidden aurora: field drives hue 210→270° (blue→indigo→violet), V=0.35, S=0.80
    aurora_hue = 0.583 + field * 0.167     # 210/360=0.583 → 270/360=0.750
    aurora_r, aurora_g, aurora_b = hsv_to_rgb_vec(aurora_hue, np.float32(0.80), np.float32(0.35))
    # Aurora visible in high-field zones (where M is also high → specular pop)
    aurora_blend = field * 0.70 * pm
    final_r = np.clip(base_r * (1 - aurora_blend) + aurora_r * aurora_blend, 0, 1)
    final_g = np.clip(base_g * (1 - aurora_blend) + aurora_g * aurora_blend, 0, 1)
    final_b = np.clip(base_b * (1 - aurora_blend) + aurora_b * aurora_blend, 0, 1)
    m3 = mask[:,:,np.newaxis]
    blend_str = np.clip(pm * 0.85, 0, 1)
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend_str) + final_r * mask * blend_str
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend_str) + final_g * mask * blend_str
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend_str) + final_b * mask * blend_str
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_eclipse(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9017)
    micro = _colorshoxx_micro((h, w), seed + 9017)
    # High M at high-field = aurora zones flash; low M elsewhere = void stays dark
    M  = 40.0  + field * 170.0 * sm + micro * 7.0 * sm   # range 40 → 210 ✓
    R  = 70.0  - field * 48.0  * sm + micro * 4.0 * sm   # range 70 → 22 ✓GGX min=22
    CC = 40.0  - field * 24.0                             # range 40 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_eclipse": {"base_spec_fn": spec_colorshoxx_eclipse, "M": 125, "R": 46, "CC": 28, "paint_fn": paint_colorshoxx_eclipse, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_eclipse", name: "COLORSHOXX Eclipse Trail", desc: "Near-black hides blue-violet-teal aurora — invisible at diffuse, chromosphere corona reveals at specular.", swatch: "#0F1019" }`

---

### IMPL-13: "Midnight Chroma" — Gradient Reveal `cx_midnight_chroma` (seed offset +9018)

**Effect:** Dark midnight navy surface with 3 sequential reveals: the field is divided into 3 zones — purple, indigo, teal — each with escalating M (160/210/240). At low specular: purple zone lights up. As angle increases: indigo lights. At maximum: teal blazes. Sequential spectral reveal as light sweeps the car.

**Key architecture difference:** Three discrete M tiers instead of a continuous ramp. Both paint and spec use the SAME zone weights (`w1`/`w2`/`w3`).

```python
def paint_colorshoxx_midnight_chroma(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9018)
    micro = _colorshoxx_micro((h, w), seed + 9018)
    # 3 zone colors
    z1 = np.array([0.28, 0.05, 0.45], dtype=np.float32)   # purple (field < ~0.40)
    z2 = np.array([0.12, 0.10, 0.60], dtype=np.float32)   # indigo (field ~0.40-0.60)
    z3 = np.array([0.05, 0.55, 0.72], dtype=np.float32)   # teal   (field > ~0.60)
    # Smooth zone weights (20% crossfade bands)
    w1 = np.clip((0.40 - field) / 0.20, 0, 1)
    w3 = np.clip((field - 0.60) / 0.20, 0, 1)
    w2 = np.clip(1.0 - w1 - w3, 0, 1)
    # Add micro-variation to soften zone edges
    w_noise = (micro - 0.5) * 0.08
    w1 = np.clip(w1 + w_noise, 0, 1)
    w3 = np.clip(w3 - w_noise, 0, 1)
    w2 = np.clip(1.0 - w1 - w3, 0, 1)
    color = (z1[np.newaxis, np.newaxis, :] * w1[:,:,np.newaxis] +
             z2[np.newaxis, np.newaxis, :] * w2[:,:,np.newaxis] +
             z3[np.newaxis, np.newaxis, :] * w3[:,:,np.newaxis])
    blend = np.clip(pm * 0.88, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_midnight_chroma(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9018)
    micro = _colorshoxx_micro((h, w), seed + 9018)
    # Same zone weights — marriage guaranteed
    w1 = np.clip((0.40 - field) / 0.20, 0, 1)
    w3 = np.clip((field - 0.60) / 0.20, 0, 1)
    w2 = np.clip(1.0 - w1 - w3, 0, 1)
    # Tier M: purple=160, indigo=210, teal=240
    M  = 160.0*w1 + 210.0*w2 + 240.0*w3 + micro * 8.0 * sm
    # Tier R: purple=55, indigo=35, teal=18
    R  = 55.0*w1  + 35.0*w2  + 18.0*w3  + micro * 3.0 * sm   # min=18 ✓GGX
    # Tier CC: purple=35, indigo=22, teal=16
    CC = 35.0*w1  + 22.0*w2  + 16.0*w3
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_midnight_chroma": {"base_spec_fn": spec_colorshoxx_midnight_chroma, "M": 203, "R": 36, "CC": 24, "paint_fn": paint_colorshoxx_midnight_chroma, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_midnight_chroma", name: "COLORSHOXX Midnight Chroma", desc: "3 sequential reveals — purple, indigo, teal each unlock at rising specular angle. Deepest blue space vibes.", swatch: "#1E1880" }`

---

### IMPL-14: "Ghost Fire" — Gradient Reveal `cx_ghost_fire` (seed offset +9019)

**Effect:** Sandy neutral/khaki at diffuse. As specular angle rises: hidden thermal gradient blazes through — crimson→orange→gold heat map. A ghost hiding fire within plain sand.

```python
def paint_colorshoxx_ghost_fire(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9019)
    micro = _colorshoxx_micro((h, w), seed + 9019)
    # Sandy neutral base — always present as foundation
    sandy_r = np.full((h, w), 0.68, dtype=np.float32)
    sandy_g = np.full((h, w), 0.62, dtype=np.float32)
    sandy_b = np.full((h, w), 0.50, dtype=np.float32)
    # Hidden thermal overlay: field drives hue 0°→50° (red→orange→gold) at S=0.80, V=0.76
    thermal_hue = field * (50.0 / 360.0)   # 0 → 0.139 (red → gold)
    thermal_r, thermal_g, thermal_b = hsv_to_rgb_vec(
        thermal_hue + (micro - 0.5) * 0.02,  # micro adds ±2° organic variation
        np.float32(0.80), np.float32(0.76))
    # Thermal visible in high-field zones — same zones as high-M spec
    thermal_blend = field * 0.55
    final_r = np.clip(sandy_r * (1 - thermal_blend) + thermal_r * thermal_blend, 0, 1)
    final_g = np.clip(sandy_g * (1 - thermal_blend) + thermal_g * thermal_blend, 0, 1)
    final_b = np.clip(sandy_b * (1 - thermal_blend) + thermal_b * thermal_blend, 0, 1)
    blend_str = np.clip(pm * 0.87, 0, 1)
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend_str) + final_r * mask * blend_str
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend_str) + final_g * mask * blend_str
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend_str) + final_b * mask * blend_str
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_ghost_fire(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9019)
    micro = _colorshoxx_micro((h, w), seed + 9019)
    M  = 50.0  + field * 145.0 * sm + micro * 7.0 * sm   # range 50 → 195 ✓
    R  = 65.0  - field * 44.0  * sm + micro * 4.0 * sm   # range 65 → 21 ✓GGX min=21
    CC = 38.0  - field * 22.0                             # range 38 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_ghost_fire": {"base_spec_fn": spec_colorshoxx_ghost_fire, "M": 122, "R": 43, "CC": 27, "paint_fn": paint_colorshoxx_ghost_fire, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_ghost_fire", name: "COLORSHOXX Ghost Fire", desc: "Sandy neutral hides thermal heat map — khaki hides crimson-orange-gold fire that blazes at specular.", swatch: "#ADAE80" }`

---

### IMPL-15: "Titanium Bloom" — Gradient Reveal `cx_titanium_bloom` (seed offset +9020)

**⚠ Seed correction:** Previous RESEARCH-036 note incorrectly wrote `seed+9019` for titanium_bloom. Correct offset is **+9020** (ghost_fire uses +9019). All three copies of structural_color.py must use +9020.

**Effect:** Metallic grey base (like bare titanium billet) with a hidden heat-treat gradient. Field drives hue 0.08→0.70 (gold→bronze→rose→purple→blue — full heat-treat spectrum). S=0.55 keeps it metallic-looking. The gradient is always present in paint; spec M differential makes it POP at specular.

```python
def paint_colorshoxx_titanium_bloom(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9020)
    micro = _colorshoxx_micro((h, w), seed + 9020)
    # Metallic grey base
    grey_r = np.full((h, w), 0.60, dtype=np.float32)
    grey_g = np.full((h, w), 0.65, dtype=np.float32)
    grey_b = np.full((h, w), 0.70, dtype=np.float32)
    # Heat-tint: hue 0.08→0.70 (gold→bronze→rose→purple→blue), S=0.55, V=0.72
    bloom_hue = 0.08 + field * 0.62
    bloom_r, bloom_g, bloom_b = hsv_to_rgb_vec(
        bloom_hue + (micro - 0.5) * 0.03,
        np.float32(0.55), np.float32(0.72))
    # Bloom visible in high-field zones (same zones get high M → specular pop)
    bloom_blend = field * 0.55
    final_r = np.clip(grey_r * (1 - bloom_blend) + bloom_r * bloom_blend, 0, 1)
    final_g = np.clip(grey_g * (1 - bloom_blend) + bloom_g * bloom_blend, 0, 1)
    final_b = np.clip(grey_b * (1 - bloom_blend) + bloom_b * bloom_blend, 0, 1)
    blend_str = np.clip(pm * 0.88, 0, 1)
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend_str) + final_r * mask * blend_str
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend_str) + final_g * mask * blend_str
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend_str) + final_b * mask * blend_str
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_titanium_bloom(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _colorshoxx_field((h, w), seed + 9020)
    micro = _colorshoxx_micro((h, w), seed + 9020)
    M  = 120.0 + field * 110.0 * sm + micro * 6.0 * sm   # range 120 → 230 ✓
    R  = 48.0  - field * 28.0  * sm + micro * 4.0 * sm   # range 48 → 20 ✓GGX min=20
    CC = 28.0  - field * 12.0                             # range 28 → 16
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_titanium_bloom": {"base_spec_fn": spec_colorshoxx_titanium_bloom, "M": 175, "R": 34, "CC": 22, "paint_fn": paint_colorshoxx_titanium_bloom, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_titanium_bloom", name: "COLORSHOXX Titanium Bloom", desc: "Bare titanium grey with heat-treat bloom — gold-bronze-rose-blue gradient pops at specular. Aerospace aesthetic.", swatch: "#9AA6B2" }`

---

### IMPL-16: "Dragon Scale" — Multi-Zone Prismatic `cx_dragon_scale` (seed offset +9021)

**Effect:** 45 Voronoi cells assigned warm gradient colors (red→orange→gold, H=0°→50°). The EDGES of each scale catch maximum light (M=240/R=16). Scale interiors hold a warm glow (M=140/R=40). At specular: individual scale-tips flash sequentially as angle sweeps.

**Key:** Uses `_voronoi_edges` to isolate scale-tip pixels. Both paint and spec use `_voronoi_cells(shape, 45, seed+9021)`.

```python
def paint_colorshoxx_dragon_scale(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    labels, dists = _voronoi_cells((h, w), 45, seed + 9021)
    rng = np.random.RandomState(seed + 9021)
    # Warm gradient: H=0°→50° per cell (red→orange→gold)
    cell_hues  = rng.uniform(0.00, 0.139, 45).astype(np.float32)   # 0/360 → 50/360
    cell_sats  = rng.uniform(0.80, 0.95,  45).astype(np.float32)
    cell_vals  = rng.uniform(0.70, 0.85,  45).astype(np.float32)
    hue_map = cell_hues[labels]
    sat_map = cell_sats[labels]
    val_map = cell_vals[labels]
    # Micro distance variation (dists brighten interior center)
    val_map = np.clip(val_map - dists * 0.12, 0, 1)
    r_c, g_c, b_c = hsv_to_rgb_vec(hue_map, sat_map, val_map)
    blend = np.clip(pm * 0.85, 0, 1)
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + r_c * mask * blend
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + g_c * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + b_c * mask * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_dragon_scale(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    labels, _ = _voronoi_cells((h, w), 45, seed + 9021)
    micro_n = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 9021 + 200)
    micro   = np.clip(micro_n * 0.5 + 0.5, 0, 1).astype(np.float32)
    # Scale edges: mirror flash. Scale interior: moderate metallic.
    edges = _voronoi_edges(labels, thickness=3)
    M = edges * 240.0 + (1.0 - edges) * 140.0 + micro * 8.0 * sm
    R = edges * 16.0  + (1.0 - edges) * 40.0  + micro * 4.0 * sm   # min=16 ✓GGX
    CC = np.full((h, w), 16.0, dtype=np.float32)  # uniform max gloss (scale finish)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_dragon_scale": {"base_spec_fn": spec_colorshoxx_dragon_scale, "M": 190, "R": 28, "CC": 16, "paint_fn": paint_colorshoxx_dragon_scale, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_dragon_scale", name: "COLORSHOXX Dragon Scale", desc: "45 warm-gradient Voronoi scales — each scale-tip catches maximum light independently. Gold fire mosaic.", swatch: "#CC3308" }`

---

### IMPL-17: "Prism Fragment" — Multi-Zone Prismatic `cx_prism_fragment` (seed offset +9022)

**Effect:** 12 large crystal fragments, each a different shade from the cool spectrum (teal→blue→violet). Each fragment has a random but distinct M (160–240) and R (16–35), so each catches light at its own angle threshold. Like looking at a shattered sapphire.

```python
def paint_colorshoxx_prism_fragment(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    labels, _ = _voronoi_cells((h, w), 12, seed + 9022)
    rng = np.random.RandomState(seed + 9022)
    # Cool spectrum: H=180°→280° (teal → blue → violet)
    cell_hues = rng.uniform(0.50, 0.778, 12).astype(np.float32)   # 180/360 → 280/360
    cell_sats = rng.uniform(0.75, 0.95,  12).astype(np.float32)
    hue_map = cell_hues[labels]
    sat_map = cell_sats[labels]
    r_c, g_c, b_c = hsv_to_rgb_vec(hue_map, sat_map, np.float32(0.80))
    blend = np.clip(pm * 0.85, 0, 1)
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + r_c * mask * blend
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + g_c * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + b_c * mask * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_prism_fragment(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    labels, _ = _voronoi_cells((h, w), 12, seed + 9022)
    micro_n = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 9022 + 200)
    micro   = np.clip(micro_n * 0.5 + 0.5, 0, 1).astype(np.float32)
    # Each cell: independent M and R from a seeded random LUT
    rng = np.random.RandomState(seed + 9022 + 1)
    cell_M = rng.uniform(160.0, 240.0, 12).astype(np.float32)
    cell_R = rng.uniform(16.0, 35.0, 12).astype(np.float32)   # min=16 ✓GGX
    M = cell_M[labels] + micro * 8.0 * sm
    R = cell_R[labels] + micro * 4.0 * sm
    CC = np.full((h, w), 18.0, dtype=np.float32)   # slight clearcoat on crystals
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_prism_fragment": {"base_spec_fn": spec_colorshoxx_prism_fragment, "M": 200, "R": 26, "CC": 18, "paint_fn": paint_colorshoxx_prism_fragment, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_prism_fragment", name: "COLORSHOXX Prism Fragment", desc: "12 cool-spectrum crystal fragments — each shard catches light at its own angle. Shattered sapphire.", swatch: "#2255BB" }`

---

### IMPL-18: "Kaleidoscope" — Multi-Zone Prismatic `cx_kaleidoscope` (seed offset +9023)

**Effect:** 8 radial pie segments (4 warm + 4 cool alternating). Warm segments: M=215/R=20 (gold-range flash). Cool segments: M=90/R=55 (blue-range matte hold). As light sweeps the car, warm and cool segments alternate their flash in a kaleidoscope rhythm.

**Key detail:** Organic noise added to segment boundaries to prevent hard geometric lines.

```python
def paint_colorshoxx_kaleidoscope(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx_c = h / 2.0, w / 2.0
    angle = np.arctan2(yy - cy, xx - cx_c)   # -pi to pi
    # Organic boundary softening
    n_soft = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 9023 + 50)
    n_soft = np.clip(n_soft * 0.5 + 0.5, 0, 1) * 0.35   # ±17.5% of a segment width
    # Map angle to 8 segments with soft noise
    seg_float = ((angle / (2 * np.pi) + 0.5 + n_soft) * 8.0)
    segment = np.floor(seg_float).astype(np.int32) % 8
    # 4 warm (even) + 4 cool (odd): varying hues within each group
    warm_hues = np.array([0.05, 0.09, 0.12, 0.14], dtype=np.float32)   # H=18°,32°,43°,50°
    cool_hues = np.array([0.56, 0.60, 0.64, 0.67], dtype=np.float32)   # H=202°,216°,230°,241°
    hue_lut = np.array([warm_hues[0], cool_hues[0], warm_hues[1], cool_hues[1],
                        warm_hues[2], cool_hues[2], warm_hues[3], cool_hues[3]], dtype=np.float32)
    hue_map = hue_lut[segment]
    r_c, g_c, b_c = hsv_to_rgb_vec(hue_map, np.float32(0.88), np.float32(0.82))
    blend = np.clip(pm * 0.88, 0, 1)
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + r_c * mask * blend
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + g_c * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + b_c * mask * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_kaleidoscope(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx_c = h / 2.0, w / 2.0
    angle = np.arctan2(yy - cy, xx - cx_c)
    n_soft = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 9023 + 50)
    n_soft = np.clip(n_soft * 0.5 + 0.5, 0, 1) * 0.35
    seg_float = ((angle / (2 * np.pi) + 0.5 + n_soft) * 8.0)
    segment = np.floor(seg_float).astype(np.int32) % 8
    micro_n = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 9023 + 200)
    micro   = np.clip(micro_n * 0.5 + 0.5, 0, 1).astype(np.float32)
    # Even=warm=high M, Odd=cool=low M
    M_lut = np.array([215, 90, 215, 90, 215, 90, 215, 90], dtype=np.float32)
    R_lut = np.array([ 20, 55,  20, 55,  20, 55,  20, 55], dtype=np.float32)  # min=20 ✓GGX
    M = M_lut[segment] + micro * 10.0 * sm
    R = R_lut[segment] + micro * 5.0  * sm
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_kaleidoscope": {"base_spec_fn": spec_colorshoxx_kaleidoscope, "M": 152, "R": 38, "CC": 16, "paint_fn": paint_colorshoxx_kaleidoscope, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_kaleidoscope", name: "COLORSHOXX Kaleidoscope", desc: "8 radial warm/cool alternating segments — warm gold flashes alternate with steady cool blue in a rhythmic kaleidoscope.", swatch: "#CC6622" }`

---

### IMPL-19: "Spectral Fracture" — Multi-Zone Prismatic `cx_spectral_fracture` (seed offset +9024)

**Effect:** Belousov-Zhabotinsky spiral-wave topology creates 8 organic zones of full-spectrum color. Zone EDGES (the fracture lines) get M=245/R=16 — maximum specular flash. Zone interiors have graduating M (240 down to 80 by zone index). Like a cracked gemstone where every facet-edge catches light at maximum intensity.

**Important:** `_bz_reaction` returns `(labels, field)` where labels are `int` 0..n_colors-1. Use `_voronoi_edges` on BZ labels for fracture-line detection (it works on any int label array).

```python
def paint_colorshoxx_spectral_fracture(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    bz_labels, bz_field = _bz_reaction((h, w), seed + 9024, n_waves=5, n_colors=8)
    # Full spectrum: 8 BZ zones → 8 equally-spaced hues (0°, 45°, 90°, ..., 315°)
    hue_map  = bz_labels.astype(np.float32) / 8.0   # 0 → 0.875 (0° → 315°)
    r_c, g_c, b_c = hsv_to_rgb_vec(hue_map, np.float32(0.90), np.float32(0.75))
    blend = np.clip(pm * 0.85, 0, 1)
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + r_c * mask * blend
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + g_c * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + b_c * mask * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def spec_colorshoxx_spectral_fracture(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    bz_labels, _ = _bz_reaction((h, w), seed + 9024, n_waves=5, n_colors=8)
    micro_n = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 9024 + 200)
    micro   = np.clip(micro_n * 0.5 + 0.5, 0, 1).astype(np.float32)
    # Fracture edges: maximum M flash
    edges = _voronoi_edges(bz_labels, thickness=2)
    # Interior M grades by zone index: zone 0=240, zone 7=80 (decreasing)
    interior_M_lut = np.array([240, 220, 200, 160, 140, 120, 100, 80], dtype=np.float32)
    interior_R_lut = np.array([ 16,  20,  24,  30,  35,  40,  48, 55], dtype=np.float32)  # min=16 ✓GGX
    zone_M = interior_M_lut[bz_labels]
    zone_R = interior_R_lut[bz_labels]
    # Fracture lines override with max brightness
    M = edges * 245.0 + (1.0 - edges) * zone_M + micro * 6.0 * sm
    R = edges * 16.0  + (1.0 - edges) * zone_R  + micro * 4.0 * sm   # edges floor at 16 ✓GGX
    CC = 16.0 + (1.0 - edges) * 10.0   # fracture lines get max gloss; interiors slightly less
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
```
**Registry:** `"cx_spectral_fracture": {"base_spec_fn": spec_colorshoxx_spectral_fracture, "M": 162, "R": 35, "CC": 18, "paint_fn": paint_colorshoxx_spectral_fracture, "category": "colorshoxx"}`
**JS BASES:** `{ id: "cx_spectral_fracture", name: "COLORSHOXX Spectral Fracture", desc: "BZ spiral-wave fracture zones in full spectrum — fracture-line edges catch maximum light. Cracked gemstone.", swatch: "#8822AA" }`

---

### JS BASE_GROUPS Update (Append to "★ COLORSHOXX" array)

```javascript
"★ COLORSHOXX": [
  "cx_inferno", "cx_arctic", "cx_venom", "cx_solar", "cx_phantom",  // existing 5
  "cx_obsidian_blaze", "cx_emerald_depth", "cx_tungsten", "cx_plutonium",  // intensity shifters
  "cx_copper_dawn", "cx_magma_steel",  // temperature shifts
  "cx_eclipse", "cx_midnight_chroma", "cx_ghost_fire", "cx_titanium_bloom",  // gradient reveals
  "cx_dragon_scale", "cx_prism_fragment", "cx_kaleidoscope", "cx_spectral_fracture",  // prismatic
  // "cx_abyss", "cx_forge", "cx_spectrum_veil", "cx_mosaic", "cx_sunset"  // from RESEARCH-037
]
```

### base_registry_data.py Import Block Additions

```python
from engine.paint_v2.structural_color import (
    # Existing 5 (already there)
    paint_colorshoxx_inferno, spec_colorshoxx_inferno,
    # ...
    # Add these 14:
    paint_colorshoxx_obsidian_blaze, spec_colorshoxx_obsidian_blaze,
    paint_colorshoxx_emerald_depth,  spec_colorshoxx_emerald_depth,
    paint_colorshoxx_tungsten,       spec_colorshoxx_tungsten,
    paint_colorshoxx_plutonium,      spec_colorshoxx_plutonium,
    paint_colorshoxx_copper_dawn,    spec_colorshoxx_copper_dawn,
    paint_colorshoxx_magma_steel,    spec_colorshoxx_magma_steel,
    paint_colorshoxx_eclipse,        spec_colorshoxx_eclipse,
    paint_colorshoxx_midnight_chroma, spec_colorshoxx_midnight_chroma,
    paint_colorshoxx_ghost_fire,     spec_colorshoxx_ghost_fire,
    paint_colorshoxx_titanium_bloom, spec_colorshoxx_titanium_bloom,
    paint_colorshoxx_dragon_scale,   spec_colorshoxx_dragon_scale,
    paint_colorshoxx_prism_fragment, spec_colorshoxx_prism_fragment,
    paint_colorshoxx_kaleidoscope,   spec_colorshoxx_kaleidoscope,
    paint_colorshoxx_spectral_fracture, spec_colorshoxx_spectral_fracture,
)
```

### Dev Agent Checklist (14 Remaining)

- [ ] Add import lines to structural_color.py: `from engine.chameleon import hsv_to_rgb_vec` + `from engine.shokk_series import (_voronoi_cells, _voronoi_edges, _bz_reaction)`
- [ ] Add 14 paint+spec function pairs to structural_color.py (all 3 copies)
- [ ] Add 14 import pairs to base_registry_data.py import block (all 3 copies)
- [ ] Add 14 registry entries to BASE_REGISTRY COLORSHOXX section (all 3 copies)
- [ ] Add 14 BASES entries to paint-booth-0-finish-data.js BASES array (all 3 JS copies)
- [ ] Update BASE_GROUPS `"★ COLORSHOXX"` with all 19 new IDs (all 3 JS copies, noting 5 from RESEARCH-037 too)
- [ ] GGX verify: all `np.clip(R, 15, 255)` — confirmed above per function
- [ ] **Seed correction**: cx_titanium_bloom must use `seed + 9020`, NOT `seed + 9019` (corrects RESEARCH-036 typo)

---

## RESEARCH-037: COLORSHOXX Dev Handoff — 5 New Implementation Specs

**Date: 2026-03-30 | Agent: SPB Research Agent | Builds on: RESEARCH-030 + direct source code analysis**

Five new COLORSHOXX finishes (Intensity Shifters, Temperature Shifts, Gradient Reveals, Multi-Zone Prismatic) with complete paint+spec pseudocode ready for the Dev Agent. All use the `_colorshoxx_field` + `_colorshoxx_micro` helpers already in `structural_color.py`.

### Marriage Pattern (Same for all 5)

```python
# Paint function: same field seed as spec
field = _colorshoxx_field((h,w), seed + UNIQUE_OFFSET)
micro = _colorshoxx_micro((h,w), seed + UNIQUE_OFFSET)
color = (COLOR_A * blend_field + COLOR_B * (1 - blend_field))  # simple lerp

# Spec function: SAME seed+offset — spatial marriage guaranteed
field = _colorshoxx_field((h,w), seed + UNIQUE_OFFSET)  # same call, same result
M  = M_min + field * (M_max - M_min) * sm
R  = R_max - field * (R_max - R_min) * sm
CC = CC_high - field * (CC_high - CC_min)
```

### IMPL-1: "Abyss Flash" — Intensity Shifter `cx_abyss` (seed offset +9006)

**Effect:** Midnight navy at normal view → electric cobalt blazes at specular. Same blue family, 20× contrast.

```python
# Paint colors
cobalt  = np.array([0.10, 0.30, 0.95])  # electric cobalt — the FLASH color, HIGH-M zone
navy    = np.array([0.02, 0.04, 0.32])  # midnight navy — BASE color, LOW-M zone
blend = np.clip(pm * 0.92, 0, 1)

# Spec: HUGE M differential creates intensity shift not hue shift
M  = 45.0  + field * 195.0 * sm  → range: 45 (navy) → 240 (cobalt)
R  = 85.0  - field * 68.0  * sm  → range: 85 (navy) → 17 (cobalt)   ← GGX safe: min=17
CC = 42.0  - field * 26.0        → range: 42 (navy) → 16 (cobalt)
```
**Registry:** `"cx_abyss": {"M": 140, "R": 45, "CC": 28, "base_spec_fn": spec_colorshoxx_abyss, "paint_fn": paint_colorshoxx_abyss}`

### IMPL-2: "Forge to Glacier" — Temperature Shift `cx_forge` (seed offset +9007)

**Effect:** Hot orange forge metal at rest → arctic glacier blue-steel at specular. ~4000K temperature swing.

```python
forge   = np.array([0.82, 0.36, 0.08])  # hot orange, HIGH-M zone
glacier = np.array([0.30, 0.55, 0.85])  # arctic blue, LOW-M zone
blend = np.clip(pm * 0.88, 0, 1)

M  = 85.0  + field * 120.0 * sm  → range: 85 → 205     ← GGX safe: floor 15
R  = 58.0  - field * 32.0  * sm  → range: 58 → 26
CC = 36.0  - field * 20.0        → range: 36 → 16
```
**Registry:** `"cx_forge": {"M": 145, "R": 38, "CC": 24}`

### IMPL-3: "Spectrum Veil" — Gradient Reveal `cx_spectrum_veil` (seed offset +9008)

**Effect:** Neutral silver at normal view. Full-spectrum rainbow BLAZES at specular. Completely invisible hidden gradient.

```python
# KEY: Low-saturation hue rotation. Looks silver/metallic normally.
# At specular: Fresnel amplifies the hidden hue via high M differential.
hue_field = field  # 0→1 drives 0→360° hue rotation
veil_rgb = hsv_to_rgb_vec(hue_field, sat=0.35, val=0.78)  # low sat = silver-looking at diffuse

# Spec: HUGE M range (160 units) — the dominant reveal mechanism
M  = 80.0  + field * 160.0 * sm  → range: 80 → 240     ← GGX safe: R min=18
R  = 18.0  + field * 10.0  * sm  → range: 18 → 28       (near-uniform mirror surface)
CC = 16.0  + field * 12.0        → range: 16 → 28
```
**Registry:** `"cx_spectrum_veil": {"M": 160, "R": 22, "CC": 18}`

### IMPL-4: "Mosaic Prism" — Multi-Zone Prismatic `cx_mosaic` (seed offset +9009)

**Effect:** 18-cell Voronoi mosaic. Each cell a different spectral color. Mirror cells (even-indexed) vs matte cells (odd-indexed) create independent per-cell flashes.

```python
# Same Voronoi construction in paint AND spec (same seed = marriage)
rng = np.random.RandomState(seed + 9009)
n_cells = 18
pts = np.stack([rng.rand(n_cells)*h, rng.rand(n_cells)*w], axis=1)  # same in both fns

# Paint: full hue wheel per cell
cell_hues = np.linspace(0, 1, n_cells, endpoint=False)  # 0°,20°,40°,…,340°
cell_sats = [0.95, 0.75, ...]  # alternating
hue_map   = cell_hues[cell_labels]
veil_rgb  = hsv_to_rgb_vec(hue_map, sat_map, val_map)

# Spec: alternating M per cell (not per field)
cell_M = [220.0 if i%2==0 else 80.0 for i in range(n_cells)]   # mirror vs matte
cell_R = [18.0  if i%2==0 else 60.0 for i in range(n_cells)]
# + organic noise overlay: n_noise * 12.0 on M, * 5.0 on R
```
**Registry:** `"cx_mosaic": {"M": 150, "R": 38, "CC": 18}` | **Note:** Requires `scipy.spatial.cKDTree` (already used in shokk_series.py).

### IMPL-5: "Sunset Protocol" — Temperature Shift `cx_sunset` (seed offset +9010)

**Effect:** Warm sunset amber at rest → deep space navy reveals at specular. Astronomical temperature contrast.

```python
sunset = np.array([0.92, 0.56, 0.10])  # warm amber, HIGH-M zone
space  = np.array([0.04, 0.06, 0.38])  # deep space navy, LOW-M zone
blend = np.clip(pm * 0.88, 0, 1)

M  = 58.0  + field * 135.0 * sm  → range: 58 → 193     ← GGX safe: R min=28
R  = 68.0  - field * 40.0  * sm  → range: 68 → 28
CC = 40.0  - field * 24.0        → range: 40 → 16
```
**Registry:** `"cx_sunset": {"M": 130, "R": 44, "CC": 26}`

### Dev Agent Checklist

- [ ] Add 5 new `paint_colorshoxx_X` + `spec_colorshoxx_X` function pairs to `engine/paint_v2/structural_color.py` (all 3 copies)
- [ ] Add import lines to `engine/base_registry_data.py` import block (all 3 copies)
- [ ] Add 5 registry entries to `BASE_REGISTRY` COLORSHOXX section in `base_registry_data.py` (all 3 copies)
- [ ] Add 5 entries to `BASES` array in `paint-booth-0-finish-data.js` (all 3 JS copies)
- [ ] Add 5 IDs to `BASE_GROUPS['colorshoxx']` (or equivalent group) in JS (all 3 JS copies)
- [ ] `hsv_to_rgb_vec` import check in structural_color.py if using Spectrum Veil
- [ ] GGX safety verify: all R `np.clip(R, 15, 255)` confirmed

---

## RESEARCH-036: COLORSHOXX — Complete 25 Finish Library

**Date: 2026-03-30 | Agent: SPB Research Agent**

5 existing (implemented, registered) + 20 new designs. Organized by category with exact RGB values and spec profiles.

### Category A: Dual-Tone Flips — EXISTING 5 (all implemented in structural_color.py)

| ID | Name | Color A (HIGH-M, flash) | Color B (LOW-M, holds) | ΔM | Notes |
|----|------|------------------------|------------------------|----|-------|
| `cx_inferno` | Inferno Flip | Crimson (0.78,0.08,0.06) | Midnight Blue (0.06,0.08,0.55) | 115 | Max complementary contrast |
| `cx_arctic` | Arctic Mirage | Ice Silver (0.75,0.78,0.82) | Deep Teal (0.04,0.35,0.38) | 110 | Chrome-reveal feel |
| `cx_venom` | Venom Shift | Toxic Green (0.20,0.75,0.10) | Black-Purple (0.15,0.03,0.25) | 155 | Max ΔM in library |
| `cx_solar` | Solar Flare | Warm Gold (0.85,0.68,0.15) | Deep Copper (0.60,0.22,0.08) | 80 | Same hue family (warm only) |
| `cx_phantom` | Phantom Violet | Electric Violet (0.50,0.10,0.75) | Cold Gunmetal (0.22,0.24,0.27) | 125 | Achromatic secondary |

### Category B: Intensity Shifters — 5 NEW (same color family, brightness/saturation swing)

| ID | Name | Flash Color (HIGH-M) | Base Color (LOW-M) | M range | Key hook |
|----|------|---------------------|-------------------|---------|----------|
| `cx_abyss` | Abyss Flash | Electric cobalt (0.10,0.30,0.95) | Midnight navy (0.02,0.04,0.32) | 45→240 | Max ΔM intensity shift; same blue family |
| `cx_obsidian_blaze` | Obsidian Blaze | Vivid crimson (0.75,0.06,0.04) | Near-black (0.05,0.04,0.06) | 30→235 | Darkest secondary; from void to fire |
| `cx_emerald_depth` | Emerald Depth | Brilliant jade (0.10,0.82,0.22) | Dark forest (0.04,0.22,0.08) | 55→215 | Green-family; emerald jewel reveal |
| `cx_tungsten` | Tungsten Cobalt | Electric cobalt (0.10,0.25,0.95) | Tungsten grey (0.25,0.27,0.30) | 60→220 | Near-achromatic grey, max sat blue |
| `cx_plutonium` | Plutonium | Neon green (0.25,0.95,0.10) | Silver-grey (0.48,0.48,0.50) | 65→230 | Most unexpected: silver→neon green |

### Category C: Temperature Shifts — 5 (1 existing, 4 new)

| ID | Name | Warm Color | Cool Color | M warm | M cool | Narrative |
|----|------|-----------|-----------|--------|--------|-----------|
| `cx_solar` ✅ | Solar Flare | Gold (0.85,0.68,0.15) | Copper (0.60,0.22,0.08) | 240 | 160 | Both warm — intensity not temp |
| `cx_forge` | Forge to Glacier | Hot orange (0.82,0.36,0.08) | Glacier blue (0.30,0.55,0.85) | 205 | 85 | Blacksmith + arctic |
| `cx_sunset` | Sunset Protocol | Sunset amber (0.92,0.56,0.10) | Space navy (0.04,0.06,0.38) | 193 | 58 | Astronomical contrast |
| `cx_copper_dawn` | Copper Dawn | Rose copper (0.75,0.38,0.22) | Dawn periwinkle (0.55,0.58,0.85) | 200 | 90 | Pastel temp shift, most refined |
| `cx_magma_steel` | Magma Steel | Magma red (0.88,0.16,0.04) | Cold steel (0.55,0.62,0.72) | 215 | 70 | Volcanic→tempered blade |

**cx_copper_dawn spec profile:** M=90+field*110*sm, R=50-field*28*sm, CC=32-field*16, seed+9015
**cx_magma_steel spec profile:** M=70+field*145*sm, R=55-field*35*sm, CC=34-field*18, seed+9016

### Category D: Gradient Reveals — 5 NEW (hidden gradient blazes at specular)

| ID | Name | Base Look | Hidden Gradient | Reveal Mechanism |
|----|------|----------|-----------------|-----------------|
| `cx_spectrum_veil` | Spectrum Veil | Neutral silver-grey | Full 360° hue rotation, S=0.35 | M=80→240 (widest in library); hidden in low-sat paint |
| `cx_eclipse` | Eclipse Trail | Near-black (0.06,0.07,0.10) | Blue→violet→teal aurora, V=0.35 | M=40→210; darkest base; aurora zones emerge from darkness |
| `cx_midnight_chroma` | Midnight Chroma | Dark midnight navy | 3-zone: purple→indigo→teal | 3 discrete M levels (160/210/240) — sequential reveals |
| `cx_ghost_fire` | Ghost Fire | Sandy neutral (0.68,0.62,0.50) | Thermal: crimson→orange→gold | M=50→195; warm-on-warm reveal (same temperature family) |
| `cx_titanium_bloom` | Titanium Bloom | Metallic grey (0.60,0.65,0.70) | Heat-tint: gold→bronze→rose→blue | M=120→230; both metallic; heat-treat signature look |

**cx_eclipse paint:** Near-black base + hidden aurora gradient (`hsv(H=210→270, S=0.80, V=0.35)`) mapped through `_colorshoxx_field`. Blend=0.70.
**cx_midnight_chroma paint:** 3-stop field ramp: field<0.33→purple(0.28,0.05,0.45), 0.33-0.66→indigo(0.12,0.10,0.60), >0.66→teal(0.05,0.55,0.72).
**cx_ghost_fire paint:** Sandy base (0.68,0.62,0.50) with thermal overlay (H=0→50, V=0.65-0.85) at 55% blend.
**cx_titanium_bloom paint:** Grey base + heat-tint (H=0.08→0.70, S=0.55, V=0.70) overlay at 55% blend, field seed+9019.

### Category E: Multi-Zone Prismatic — 5 NEW (cell/facet zones with independent flash)

| ID | Name | Cells | Color Distribution | Spec Behavior |
|----|------|-------|-------------------|---------------|
| `cx_mosaic` | Mosaic Prism | 18 Voronoi | Full hue wheel (0→360°) | Even=M220/R18, Odd=M80/R60 — alternating flash |
| `cx_dragon_scale` | Dragon Scale | 45 Voronoi (scale-like) | Red→orange→gold (H=0→50) | Edge M=240/R16, Interior M=140/R40 — scale-tip flash |
| `cx_prism_fragment` | Prism Fragment | 12 Voronoi (large) | Cool spectrum only (H=180→280) | Per-cell M random 160-240, R 16-35 — sequential reveals |
| `cx_kaleidoscope` | Kaleidoscope | 8 radial pie segments | 4 warm + 4 cool (alternating) | Warm M=215/R20, Cool M=90/R55 — warm/cool interplay |
| `cx_spectral_fracture` | Spectral Fracture | 8 BZ-reaction zones | Full spectrum (H=0→360°) | Edge M=245/R16, Interior M=80-160 — fracture-line flash |

**cx_dragon_scale key detail:** Uses `_voronoi_edges` for edge detection (like shokk_series.py). Edge pixels: M=240, R=16. Interior: M=140, R=40. Creates physical "scale-tip catches light" behavior.
**cx_kaleidoscope key detail:** 8 radial segments (pie slices, not Voronoi). Even=warm (H=25-45), Odd=cool (H=200-240). Add ±5% organic noise to segment boundaries to soften geometric rigidity.
**cx_spectral_fracture key detail:** Use `_bz_reaction(shape, seed+9023, n_waves=5, n_colors=8)` from shokk_series.py. 8-color BZ zones with edge M=245 creates "cracked gemstone" appearance.

---

## RESEARCH-035: COLORSHOXX Engine Analysis — Source Code Deep Dive

**Date: 2026-03-30 | Agent: SPB Research Agent | Files read: structural_color.py, chameleon.py, shokk_series.py, chrome_mirror.py, spec_paint.py**

### What Already Exists (Critical — Not a Failed Attempt)

`engine/paint_v2/structural_color.py` (244 lines) is the **working V3 COLORSHOXX implementation**. Five pairs already registered:

| Registry Key | Functions | Lines | Seed Offset |
|-------------|-----------|-------|-------------|
| `cx_inferno` | paint/spec_colorshoxx_inferno | L45–88 | +9001 |
| `cx_arctic` | paint/spec_colorshoxx_arctic | L95–127 | +9002 |
| `cx_venom` | paint/spec_colorshoxx_venom | L134–166 | +9003 |
| `cx_solar` | paint/spec_colorshoxx_solar | L173–205 | +9004 |
| `cx_phantom` | paint/spec_colorshoxx_phantom | L212–244 | +9005 |

All registered in `engine/base_registry_data.py` lines 729–742.

### The `_colorshoxx_field` Architecture (structural_color.py L22–32)

The **spatial backbone** that makes paint+spec marriage work:

```python
def _colorshoxx_field(shape, seed, ...):
    n1 = multi_scale_noise((h,w), [32, 64, 128], [0.3, 0.4, 0.3], seed)      # coarse organic
    n2 = multi_scale_noise((h,w), [16, 32],       [0.5, 0.5],     seed+100)  # medium flow
    field = (np.clip(n1*0.7 + n2*0.3, -1, 1) + 1.0) * 0.5                    # → [0,1]
    return field.astype(np.float32)
```

Scales `[32,64,128]` at 2048px res = ~1.5/3/6cm zones (car-body-scale organic variation). The `seed+100` offset for n2 creates correlated but slightly different flow, giving soft organic zone boundaries.

**`_colorshoxx_micro`** (L35–38): scales `[2,4,8]` = 1–4mm range. Adds `±0.075` variation to break hard zone boundaries and simulate physical flake scatter.

### How the Paint+Spec Marriage Works at Code Level

Both paint_colorshoxx_X and spec_colorshoxx_X call `_colorshoxx_field(shape, seed + OFFSET)` with the **same seed+offset** → deterministic Python random state = pixel-perfect spatial alignment.

**cx_inferno as example** (L50–88):
```
Paint: high-field → Crimson (0.78,0.08,0.06)   low-field → Midnight Blue (0.06,0.08,0.55)
Spec:  M = 120 + field*115*sm   → M range: 120 (blue zones) to 235 (red zones)
       R = 50  - field*35*sm    → R range: 50  (blue zones) to 15  (red zones)  ← GGX floor at 15
       CC = 40 - field*24       → CC range: 40 (blue zones) to 16  (red zones)
```

**Why red zones "flash" at specular:** M=235 + R=15 = near-mirror metallic. At specular angle: Fresnel boost maxed, specular peak very tight → surface flashes metallic-white, red dims.
**Why blue zones "hold":** M=120 + R=50 = moderate metallic, moderate scatter. Fresnel effect weaker → diffuse blue component still significant at specular → blue color visible.

### M/R/CC Engineering Reference (From All COLORSHOXX Implementations)

**M (Metallic/Red channel):**
- M=0–50: near-dielectric; paint holds at ALL angles; very little Fresnel → "holds color" zones
- M=50–120: low metallic; some Fresnel at grazing; color mostly visible → moderate flash zones
- M=120–180: mid metallic; visible sheen; clear angle brightness variation → standard dual-tone secondary
- M=180–220: high metallic; strong Fresnel; color dims at specular → flashy primary colors
- M=220–255: near-mirror; at specular = almost pure white reflection, paint invisible → chrome-like max flash

**R (Roughness/Green channel):** — GGX floor: R must be ≥15 always (use `np.clip(R, 15, 255)`)
- R=15–22: near-mirror; tight specular peak; chrome-quality highlights → combine with high M for max flash
- R=22–40: premium metallic; broad but tight specular; luxury-car shiny → primary flash zones
- R=40–70: satin; moderate scatter; visible but diffuse specular → colored metallic that pops
- R=70–100: semi-matte; wide scatter; no clear peaks → darker zones, color holds across angles
- R=100+: matte; essentially no specular angle-variation → static deep color zones

**CC (Clearcoat/Blue channel):** — CC=16 = max gloss (counterintuitive; LOWER = GLOSSIER)
- CC=16: ultra-gloss; deepest apparent depth; glass-like → chrome, candy, max-gloss
- CC=16–30: very high gloss; production showroom quality → luxury metallic
- CC=30–50: high gloss with character; slight texture → premium effect paint
- CC=50+: satin to matte territory → avoid in COLORSHOXX (degrades premium feel)

**COLORSHOXX target zone: M 40–240, R 15–85, CC 16–45.** All premium metallic range.

### Chromaflair vs COLORSHOXX: Why Marriage Quality Matters

**paint_chromaflair** (spec_paint.py L4091–4128) vs **spec_chromaflair_base** (L4132–4157):
- Paint: `angle_proxy` with seeds +310/+311
- Spec: different fields with seeds +320/+321 → **seeds differ by +10**
- Different seeds = different spatial noise patterns = paint hue-flip zones don't align with spec M/R zones
- Grade: B (concept matched, spatial fields drift)

**COLORSHOXX**: Both functions call `_colorshoxx_field(shape, seed + 9001)` — **same seed** = identical noise field = pixel-perfect alignment. That's the architectural fix.

### chameleon.py — The Most Sophisticated Angle System (Reference Architecture)

`spec_chameleon_v5` (chameleon.py L197–242):
- **M**: `M_base + (1.0 - field) * M_range` → M_base=225, M_range=30 → range 225–255 (narrow)
- **R**: Independent from field (Voronoi 5px flake cells) → R_base=10, R_range=12 → range 10–22
- **CC**: `CC_base + field * CC_range` → 16 + field*50 → range 16–66

**Why chameleon uses narrow M range (225–255):** Chameleon rotates through ALL hues continuously. The renderer's Fresnel effect on the rotating color is just a brightness modifier. Wide M range not needed because the color change is HUE-BASED.

**Why COLORSHOXX needs wide M range:** COLORSHOXX uses STATIC COLORS. The ONLY mechanism for angle-dependent differentiation is M differential between zones. Needs ΔM=80–155 to create visible zone contrast.

### Shokk Series — Additional Field Patterns Available for COLORSHOXX

From shokk_series.py, these helpers can be reused in COLORSHOXX Prismatic finishes:
- `_voronoi_cells(shape, n_cells, seed)` → (labels, dist) — for per-cell color assignment
- `_voronoi_edges(labels, thickness)` → binary edge mask — for scale-tip / fracture-line effects
- `_bz_reaction(shape, seed, n_waves, n_colors)` → (labels, field) — organic spiral zone topology
- `_spiral_field(shape, seed, arms, tightness)` → radial spiral field

All available in shokk_series.py — import from there rather than re-implementing.

### Anti-Patterns Confirmed (What NOT To Do)

1. **Don't use `bb` (base brightness) for angle effects in paint functions** — `bb` is diffuse environment brightness, not viewing angle. It affects all pixels uniformly. Using it to "simulate angle" (as in earlier chameleon versions) just varies the overall brightness, not the per-zone differential.
2. **Don't use different seed offsets in paint and spec** — even +1 seed difference creates uncorrelated spatial noise. Marriage requires identical seed+offset in both functions.
3. **Don't overcomplicate paint** — the V1/V2 structural_color had 15–20 noise calls per function. V3 has 2. Simpler paint = cleaner zones = more dramatic angle effect.
4. **Don't rely on R alone** — R creates matte vs gloss distinction but needs M differential for DUAL-COLOR behavior. Low M + varied R creates matte-vs-satin transitions, not color shifts.

---

## RESEARCH-030: COLORSHOXX Session 1 — How iRacing's Renderer Creates Angle-Dependent Effects

**Date: 2026-03-30 | Agent: SPB Research Agent | Mission: Design COLORSHOXX real color-shift finishes**

### Executive Summary

iRacing's PBR pipeline creates angle-dependent color through **paint channel** (static color/topology) + **spec channel** (M/R/CC variation). The renderer does physics; we control the material properties.

### Core Discoveries

**Discovery 1: The "Field" Abstraction**
- Chameleon finishes use a 0-1 normalized "field" representing surface orientation
- M (metallic) = INVERSE to field → high M at grazing angles creates flash
- CC (clearcoat) = FOLLOWS field → creates gloss variation
- R (roughness) = independent flake-based variation

**Discovery 2: Spec Map Mechanics**
- M range: 195–255 (high M = mirror-like, low M = paint dominates)
- R range: 15–22 (low R = specular peaks, high R = matte scatter)
- CC range: 16–66 (CC=16 max gloss, >16 increasingly matte)

**Discovery 3: The Paint–Spec Marriage Principle**
1. **Paint:** Creates STATIC zones/gradients/cells with consistent RGB (don't simulate angle-dependence)
2. **Spec:** Uses same spatial structure, varies M/R/CC to control how zones render at different angles
3. **Renderer:** Applies PBR: Fresnel (angle-dependent on M), GGX (angle-independent on R), clearcoat (CC depth)
4. **Result:** Single car looks like different colors/metallics at different angles

**Discovery 4: structural_color.py Failure Analysis**
- ❌ Paint tried to simulate angle-dependence itself → too complex
- ✅ Solution: Paint creates static zones, spec varies M/R/CC per zone

### COLORSHOXX Finish Categories (5 Types)

1. **Single-hue intensity shifters** (Morpho-like) — one color, M varies (color shifts brightness at angles)
2. **Dual-tone flips** (ChromaFlair-like) — two zones with inverted M (red front, blue metallic side)
3. **Gradient reveals** — smooth gradient, M inverse (rotates appearance at angles)
4. **Zone-based multi-color** — 3–4 Voronoi cells, each with independent M/R/CC
5. **Temperature shifts** — warm↔cool gradient with R variation (matte warm, glossy cool)

### Next Steps
- Deep dive into paint+spec coordination mechanics
- Design 25 distinct COLORSHOXX finishes with paint/spec concepts
- Implementation specs with noise seeds, M/R/CC ranges

---

## Active Findings Summary

| Entry | Date | Key Finding | Reference |
|-------|------|-------------|-----------|
| RESEARCH-038 | 2026-03-30 | Dev handoff — **14 remaining** finishes with full pseudocode (completes all 20 new finishes) | Above |
| RESEARCH-035 | 2026-03-30 | COLORSHOXX engine deep dive — M/R/CC ranges, field architecture, marriage pattern | Above |
| RESEARCH-036 | 2026-03-30 | Complete 25 COLORSHOXX finish library — 5 existing + 20 new designs with RGB values | Above |
| RESEARCH-037 | 2026-03-30 | Dev handoff — 5 new finishes with full pseudocode ready for implementation | Above |
| RESEARCH-030 | 2026-03-30 | COLORSHOXX Session 1 — PBR renderer mechanics, marriage principle | Below |
| RESEARCH-001 | 2026-03-28 | 2025 S1 renderer overhaul means finish presets need recalibration | [Link](RESEARCH_REFERENCE.md#research-001) |
| RESEARCH-003 | 2026-03-28 | Alpha channel is a **Specular Kill** switch (hard on/off, not subtle) | [Link](RESEARCH_REFERENCE.md#research-003) |
| RESEARCH-005 | 2026-03-28 | Channel-optimized spec patterns: brushed→R, cellular→G, gradient→B | [Link](RESEARCH_REFERENCE.md#research-005) |
| RESEARCH-007 | 2026-03-28 | Pattern roadmap for remaining 52 slots (Batches 5–8) | [Link](RESEARCH_REFERENCE.md#batches-5-8) |
| RESEARCH-009 | 2026-03-28 | Competitive landscape: SPB's moat is pattern-per-channel + real-time car preview | [Link](RESEARCH_REFERENCE.md#research-009) |
| RESEARCH-010–015 | 2026-03-30 | Structural color finishes, stamp/stencil overlays, GGX floor audits | [Link](RESEARCH_REFERENCE.md) |

---

## Key Technical Specs (Quick Ref)

**Spec Map Channels (iRacing PBR):**
- **R (Metallic):** 0=dielectric, 255=fully metallic
- **G (Roughness):** 0=mirror-smooth, 255=matte; ⚠️ GGX floor at G=15 minimum
- **B (Clearcoat):** 0–15=no coat, **16=max gloss**, 255=dull; ⚠️ inverted from intuition
- **A (Specular Mask):** rarely used; kill switch for environment effects

**Critical Finish Values:**
- Chrome: R255/G0–8/B16
- Metallic: R255/G85/B0
- Matte: R0/G200–220/B0
- Gloss: R0/G0–32/B16

---

## For Ricky

**Current Priority:** COLORSHOXX engine analysis complete. 25 finish library designed. Dev handoff ready. See RESEARCH-035/036/037 above.

**Known Gaps Filled:**
- ✅ Paint–spec marriage principle explained (RESEARCH-030)
- ✅ Exact M/R/CC value ranges from source code (RESEARCH-035)
- ✅ 5 existing COLORSHOXX finishes documented and verified working (RESEARCH-036)
- ✅ 20 new COLORSHOXX finishes designed across all 5 categories (RESEARCH-036)
- ✅ 5 implementation specs with full pseudocode ready for Dev Agent (RESEARCH-037)
- ✅ Dev Agent checklist for 3-copy sync + GGX safety included (RESEARCH-037)

**Ready to Implement — 20 New Finishes:**
- 5 Intensity Shifters: `cx_abyss`, `cx_obsidian_blaze`, `cx_emerald_depth`, `cx_tungsten`, `cx_plutonium`
- 4 Temperature Shifts: `cx_forge`, `cx_sunset`, `cx_copper_dawn`, `cx_magma_steel`
- 5 Gradient Reveals: `cx_spectrum_veil`, `cx_eclipse`, `cx_midnight_chroma`, `cx_ghost_fire`, `cx_titanium_bloom`
- 5 Multi-Zone Prismatic: `cx_mosaic`, `cx_dragon_scale`, `cx_prism_fragment`, `cx_kaleidoscope`, `cx_spectral_fracture`

**5 fully spec'd in RESEARCH-037** (Dev Agent can code from pseudocode directly): `cx_abyss`, `cx_forge`, `cx_spectrum_veil`, `cx_mosaic`, `cx_sunset`.

**Remaining 15** have color values + spec profiles in RESEARCH-036 tables — need ~20 lines of code each following the established marriage pattern.

**Next Research Questions:**
- Should COLORSHOXX get its own picker category/tab in the UI (separate from existing bases)?
- Batches 5–8 pattern implementation: which should we prioritize for maximum visual impact?
