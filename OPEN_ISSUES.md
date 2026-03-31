# SPB Open Issues — Canonical Bug & Quality Tracker

This file is the single source of truth for all open QA flags.
- **QA Agent:** Update this file in-place each heartbeat. Add new findings, mark items FIXED when resolved.
- **Dev Agent:** Read this file to find work. When you fix something, mark it `[FIXED - date]`.
- **Archive:** Full QA heartbeat reviews are in `QA_REPORT.md`. Full history in `_archive/agent-logs/`.

**Last updated by Dev Agent:** 2026-03-30 — WARN-P3-002 fixed (AbortController + 5s timeout). 8 stale OPEN entries closed (LAZY-005/006, LAZY-EXPAND-005, LAZY-FUSIONS-006, WARN-SB-001, WARN-WA-001, WARN-FUSIONS-001, WARN-WRAP-001, WARN-PARA-002) — all confirmed fixed in code.

---

## 🔴 HIGH Priority (Bugs — Fix First)

| ID | Issue | Status |
|----|-------|--------|
| BUG-FUSIONS-001 | `exotic_anti_metal` dead warp fields — warp1y/warp1x/warp2y/warp2x computed but never applied to coord grids. Docstring claims "3-level domain-warped FBM" — factually false. Fix: apply warp to `n1`/`n2` noise coords. File: `engine/expansions/fusions.py` L1863–1883 | [FIXED - 2026-03-30] |

---

## 🟠 MEDIUM Priority (Quality — Tackle in Order)

| ID | Issue | Status |
|----|-------|--------|
| WEAK-036 | `candy_apple` — uses `paint_smoked_darken` (wrong physics). Needs `paint_candy_apple_v2` with red Beer-Lambert absorption + candy physics. | [FIXED - 2026-03-30] |
| LAZY-ANGLE-001 | `prismatic` ≈ `singularity` — both use `paint_iridescent_shift`, only M/R differ. Needs structural differentiation. | [FIXED - 2026-03-30] |
| LAZY-FUSIONS-008 | Spectral paradigm (P14) — "value" type used 3×: spectral_dark_light, spectral_neon_reactive, spectral_mono_chrome all use identical `lum² * Δm` mapping. Replace 2 with "gradient" (linear) and "threshold" (step) variants. | [FIXED - 2026-03-30] |
| LAZY-FUSIONS-009 | Quilt paradigm (P15) — all 10 use same Voronoi factory. Near-dup pairs: chrome_mosaic≈diamond_shimmer (±4 panel_size, ±10 M), hex_variety≈organic_cells (identical M range). Names imply hex/diamond geometry that doesn't exist. Fix: eliminate near-dups; add hex-grid and diamond-grid factory variants. | [FIXED - 2026-03-30] |
| WEAK-FUSIONS-003 | `exotic_anti_metal` paint — generic FBM+sigmoid, no physics concept. Needs domain-warp + material concept after BUG-FUSIONS-001 is fixed. | [FIXED - 2026-03-30] |
| LAZY-004 | `spec_carbon_wet_layup` — twill coord system + Gaussian blur wrapper. No structural difference from other carbon specs. Needs wet-resin or vacuum-bag specific physics. | [FIXED - 2026-03-30] |

---

## 🟡 LOW Priority (Polish)

| ID | Issue | Status |
|----|-------|--------|
| LAZY-FUSIONS-007 | `wave_chrome_tide` ≈ `wave_pearl_current` — same Gerstner wave, different material tiers. Recommended downgrade from MEDIUM (M=255 vs M=100 is genuinely distinct). | LOW |
| LAZY-006 | `spec_ballistic_weave` — weak differentiation from kevlar_weave | [FIXED - 2026-03-30] ballistic_weave has RIPSTOP grid (every 6 tows, 0.50 amp), orthogonal alignment, tow_width=4 vs kevlar's diagonal offset (0.15 rad), micro-texture, tow_width=7 — structurally distinct |
| LAZY-005 | `spec_kevlar_weave` — weak differentiation from ballistic_weave | [FIXED - 2026-03-30] kevlar has diagonal angle offset, silky micro-texture (sin(u×8π)²×0.12), lower peak metallic (0.55), vs ballistic's axis-aligned ripstop grid |
| WARN-EXOTIC-002 | `liquid_titanium` ≈ `mercury` — both use sin+cos interference grid (mathematically identical patterns at different frequencies). Spectral colors differ (cool vs warm silver) — partially mitigated. Optional: replace mercury with Marangoni radial vortex cells. | LOW |
| WARN-GLITCH-001 | `spec_glitch` CC=0 on ~60% of pixels → GGX floor whitewash. Fix: `np.where(mask > 0.5, 16, 0)` → `np.where(mask > 0.5, 16, 16)` or `130`. File: `shokker_engine_v2.py` | [FIXED - 2026-03-30] |
| LAZY-FUSIONS-006 | `halo_crack_chrome` ≈ `halo_voronoi_metal` — both F2-F1 Voronoi edge fields | [FIXED - 2026-03-30] crack now uses FBM iso-line network (zero-crossings of two noise fields, no seed points) — structurally distinct from Voronoi cell geometry |
| LAZY-FUSIONS-002 | Fine-flake sparkle cluster near-dups: diamond_dust ≈ galaxy ≈ constellation; meteor ≈ lightning_bug | [FIXED - 2026-03-30] 5 unique spec fingerprints: diamond_dust=crystalline flash, galaxy=arm-zone density, constellation=sparse stellar pts, meteor=oblique streaks, lightning_bug=orb-matched blobs |
| LAZY-EXPAND-005 | `shimmer_spectral_mesh` — same 3-direction parallel line math as hex_circuit | [FIXED - 2026-03-30] shimmer_spectral_mesh rebuilt as DIFFRACTION RINGS (concentric sinusoidal rings + 3-fold spiral warp) — radially symmetric, no periodic tiling unit, structurally distinct from hex_circuit |
| WARN-SB-001 | `engraved_crosshatch` ≈ `knurl_diamond` — angular variant only | [FIXED - 2026-03-30] engraved_crosshatch now has variable-depth FBM modulation per line family (two independent depth1/depth2 fields, amp 0.55–1.0) — simulates intaglio engraver pressure variation; knurl_diamond has no depth modulation |
| WARN-WA-001 | `desert_worn` uses `paint_tactical_flat` — no grit/sand texture | [FIXED - 2026-03-29] paint_desert_worn added: UV bleach + warm sandy tint + coarse sand grit (0.038 amp, 2.5× stronger than tactical_flat) |
| WARN-FUSIONS-001 | `sparkle_starfield` — no color character, plain white sparkle | [FIXED - 2026-03-29] sparkle_starfield given blue-white stellar color + large-scale nebula dust tint (blue-dominant) |
| WARN-WRAP-001 | `textured_wrap` hardcodes carbon charcoal, overrides user base paint | [FIXED - 2026-03-30] paint_textured_wrap_v2 in wrap_vinyl.py: orange-peel bump texture preserves user base color; base_registry_data.py updated to use paint_textured_wrap_v2 |
| WARN-PARA-002 | `spec_p_non_euclidean` is a 2D checker grid — misleading name | [FIXED - 2026-03-29] rebuilt as genuine Poincaré disk hyperbolic tiling — tiles compress toward disk boundary creating true non-Euclidean density increase |

---

## ℹ️ INFO (Log Only — No Fix Required Unless Specifically Directed)

| ID | Issue |
|----|-------|
| WARN-INLINE-002 | ~12 inline PIL imports in `engine/spec_paint.py` ~L3316+ |
| WARN-MATTE-001 | semi_gloss vs gloss paint functions differ only 2% contrast scale |
| WARN-MATTE-002 | Foundation spec functions inconsistent normalize-denormalize style |
| WARN-CHROME-003 | `spec_black_chrome` vs `spec_chrome_mirror` near-identical M/R — physically correct |
| WARN-CHROME-004 | `spec_antique_chrome` CC=16 in pitted zones — defensible physical model |
| WARN-B6-001 | `reaction_diffusion` docstring says "Gray-Scott" — noise-difference approximation |
| WARN-B6-002 | `diffraction_grating` sum-of-cosines vs `wave_standing` Chladni product |
| WARN-B7-002 | `checker_warp` sinusoidal vs `barrel_distort` radial r² — distinct geometry |

---

## 📋 Priority 5: Base Category Audit (Not Started)

QA Agent: Audit every base in the following categories. For each: check M/R/CC physics, verify paint_fn matches concept, flag issues. Dev Agent: fix all flagged issues.

**Categories (in order):**
1. PARADIGM — physically impossible finishes only, 17 bases
2. ★ Angle SHOKK — 14 bases, must have angle-dependent behavior
3. Candy & Pearl — 17 bases, M=150+, CC=16-26, G≥15
4. Ceramic & Glass — 8 bases, M=0-20 (dielectric)
5. Extreme & Experimental — 10 bases, must be genuinely extreme
6. Industrial & Tactical — 17 bases, M=0-60, R=80-180
7. Metallic Standard — 20 bases, M=100-240
8. OEM Automotive — 10 bases, production-plausible physics
9. Premium Luxury — 10 bases, no paint_none allowed
10. Racing Heritage — 11 bases, check concept match
11. Satin & Wrap — 10 bases, M=0-40 (vinyl dielectric)
12. SHOKK Series — 30 bases, verify all show in picker
13. Weathered & Aged — 17 bases, M low, R=150-250
14. Chrome & Mirror — 15 bases, M=240-255, R=2-8, CC=16-20
15. Carbon & Composite — check carbon_weave is here (not PARADIGM)
16. Exotic Metal — check anodized_exotic, xirallic, chromaflair physics
