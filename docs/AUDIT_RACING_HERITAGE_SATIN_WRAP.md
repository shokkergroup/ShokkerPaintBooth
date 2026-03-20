# Audit: Racing Heritage & Satin & Wrap (CC + Rehab)

**Date:** 2026-03-14  
**Scope:** Racing Heritage (16 bases), Satin & Wrap (10 bases).  
**Reference:** `engine/SPEC_MAP_REFERENCE.md` — **CC 16 = full clearcoat**, **17–255 = progressively dull**; **0–15 invalid**.

---

## Clearcoat rule (reminder)

| Intent | CC value |
|--------|----------|
| Full gloss / mirror / wet clearcoat | **16** |
| Satin / degraded clearcoat | ~35–80 |
| Flat / matte / dead flat | **155–255** |
| **Never use** | 0–15 |

---

## Racing Heritage (16 bases)

| Base ID | Intended behavior | Registry M/R/CC | Spec function | Changes made |
|---------|-------------------|-----------------|---------------|--------------|
| asphalt_grind | Rough asphalt-ground, dead flat | M30 R210 CC200 | spec_asphalt_grind | Spec: R→200+, CC 180–255 (was 2–6). |
| barn_find | Decades-old faded, chalky flat | (existing) | (fallback) | No patch; uses registry spec_racing_heritage fallback. |
| bullseye_chrome | Polished chrome, Airy rings | M240 R3 CC16 | spec_bullseye_chrome_rh | Spec: CC 16+ only (was 18+). |
| checkered_chrome | Chrome + matte checkered | M250 R4 CC16 | spec_checkered_chrome_rh | Spec: chrome squares CC=16, matte black CC~120, R raised for matte. |
| dirt_track_satin | Dusty satin from dirt track | M30 R110 CC35 | spec_dirt_track_satin | Spec: CC min 16, R~100+, satin CC 35+. |
| drag_strip_gloss | Ultra-polished show finish | M140 R6 CC16 | spec_drag_strip_gloss | Spec: CC 16+ only. |
| endurance_ceramic | Apollo Shield Char, charred ceramic | M15 R80 CC50 | spec_endurance_ceramic | Registry R/CC updated; spec CC 40+ (was 10–18). |
| heat_shield | Heat-wrap reflective | M240 R40 CC16 | spec_heat_shield | Spec: CC 16+ (was 6–14). |
| pace_car_pearl | Triple-pearl pace car | M110 R16 CC16 | spec_pace_car_pearl | Spec: CC 16+ only. |
| pit_lane_matte | Working matte + grime | M10 R120 CC155 | spec_pit_lane_matte | Spec: R~120+, CC 140–170 (was 2–6). |
| race_day_gloss | Wet-look fresh gloss | M0 R2 CC16 | spec_race_day_gloss | Spec: CC 16+ only. |
| rally_mud | Partially mud-splattered | M20 R185 CC80 | spec_rally_mud | Spec: R~160+, CC 70–110 (was 2–6). |
| rat_rod_primer | Intentional rough primer | M0 R200 CC185 | spec_rat_rod_primer | Registry: added base_spec_fn: spec_racing_heritage. Spec: R~195+, CC 185+ (was 1–3). |
| stock_car_enamel | Thick NASCAR enamel | M0 R18 CC16 | spec_stock_car_enamel | Spec: CC 16+ only. |
| victory_lane | Champagne metallic sparkle | M185 R16 CC16 | spec_victory_lane | Spec: CC 16+ (already compliant). |
| track_worn | Weathered/worn | (weathered_worn patch) | spec_track_worn | Unchanged; uses weathered_worn_reg. |

**Files touched:** `engine/paint_v2/racing_heritage.py` (all spec_* CC clamped 16–255; flat bases use high CC), `engine/base_registry_data.py` (rat_rod base_spec_fn, endurance_ceramic R/CC/desc).

---

## Satin & Wrap (10 bases)

| Base ID | Intended behavior | Registry M/R/CC | Spec function | Changes made |
|---------|-------------------|-----------------|---------------|--------------|
| brushed_wrap | Brushed metal vinyl | M180 R75 CC35 | spec_brushed_wrap | Spec: CC clamped 16–255. |
| chrome_wrap | Mirror chrome vinyl, slight texture | M255 R3 CC16 | spec_chrome_wrap | **Spec: cc 6 → 16.** Paint: smoother base (larger noise scales, lighter blend). |
| color_flip_wrap | Angle-shift film | M155 R22 CC16 | spec_color_flip | **Spec: CC = 16** (was 0.85–0.95×255). Paint: less irido_detail (0.3→0.1), softer blend. |
| frozen_matte | BMW Individual frozen matte | (no patch) | (registry) | Uses registry only. |
| gloss_wrap | High-gloss smooth vinyl | M0 R8 CC16 | spec_gloss_wrap | Spec: CC min 16. **Paint: calendering 0.3→0.06**, softer gloss noise. |
| liquid_wrap | Liquid rubber peel coat | (patch) | spec_liquid_wrap | Spec: CC clamped 16–255. |
| matte_wrap | Dead-flat vinyl | M0 R145 CC165 | spec_matte_wrap | **Spec: clearcoat 0 → 255** (dead flat; 0–15 invalid). |
| satin_wrap | Satin non-metallic sheen | (patch) | spec_satin_wrap | Spec: CC clamped 16–255. |
| stealth_wrap | Active camo / Predator-style | M120 R200 CC170 | spec_stealth_wrap | Spec: clearcoat*255 clamped 16–255. |
| textured_wrap | Orange-peel textured | M0 R95 CC40 | spec_textured_wrap | Spec: CC clamped 16–255. |

**Files touched:** `engine/paint_v2/wrap_vinyl.py` (all spec CC 16–255; chrome_wrap cc=16; matte_wrap CC=255; paint_chrome_wrap_v2, paint_color_flip_v2, paint_gloss_wrap_v2 toned down for smoother base).

---

## Summary

- **Racing Heritage:** Every dedicated spec now returns CC in **[16, 255]**; flat/dull finishes (asphalt, pit lane, rat rod, rally mud) use high CC; glossy finishes use CC=16. Registry rat_rod has base_spec_fn; endurance_ceramic updated for “Apollo Shield Char”.
- **Satin & Wrap:** All wrap specs use CC in **[16, 255]** (chrome/color-flip/gloss = 16 where appropriate; matte = 255). Chrome, color-flip, and gloss **paint** functions made less aggressive (smoother base, less texture).
- **Cross-cutting:** No spec output uses clearcoat below 16; base_registry_data and patch-driven spec functions are aligned with `SPEC_MAP_REFERENCE.md`.
