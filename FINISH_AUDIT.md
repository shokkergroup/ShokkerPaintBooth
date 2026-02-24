# Shokker Engine v2.0 - Complete Finish PBR Audit

**Source File:** `shokker_engine_v2.py`
**Audit Date:** 2026-02-09
**Total Finishes in FINISH_REGISTRY:** 34

---

## iRacing PBR Reference Standards (User-Provided)

| Finish Type | Metallic (R) | Roughness (G) | Clearcoat (B) | SpecMask (A) |
|---|---|---|---|---|
| Gloss | 0 | 15-25 | 16 | 255 |
| Matte | 0 | 200-230 | 0-2 | 255 |
| Satin | 0 | 80-120 | 8-12 | 255 |
| Metallic | 180-220 | 40-60 | 16 | 255 |
| Pearl | 80-120 | 30-50 | 16 | 255 |
| Chrome | 255 | 0-5 | 0 | 255 |
| Candy | 100-150 | 10-20 | 16 | 255 |
| Carbon Fiber | 40-60 | 30-80 | 16 | 255 |

**Key Rule:** B=0-15 = clearcoat OFF, B=16 = clearcoat ON at maximum shine, B=17+ = progressively degraded clearcoat.

---

## Master Audit Table

| Finish | Spec Function (Line) | Metallic (R) | Roughness (G) | Clearcoat (B) | SpecMask (A) | Paint Mod | Issues/Notes |
|--------|---------------------|--------------|----------------|----------------|--------------|-----------|--------------|
| `gloss` | `spec_gloss` (L467) | 5 | 25 | 16 | 255 | `paint_none` | M=5, should be M=0. R=25 at upper bound of ref (15-25). |
| `matte` | `spec_matte` (L474) | 0 | 190 | 0 | 255 | `paint_none` | R=190 below ref range (200-230). Too smooth for matte. |
| `satin` | `spec_satin` (L481) | 0 | 100 | 16 | 255 | `paint_none` | CC=16, should be 8-12. Max clearcoat makes this glossy, not satin. |
| `metallic` | `spec_metallic` (L488) | 225 (+/-40 noise) | 20 (+/-18 noise) | 16 | 255 | `paint_subtle_flake` | M=225 above ref (180-220). R=20 too low (ref 40-60). Noise scales [1,2,4] invisible at 2048. |
| `pearl` | `spec_pearl` (L496) | 210 (+/-20 wave) | 8 (+/-12 wave) | 16 | 255 | `paint_fine_sparkle` | **CRITICAL**: M=210 nearly 2x ref (80-120). R=8 way below ref (30-50). Renders as chrome, not pearl. |
| `chrome` | `spec_chrome` (L508) | 255 | 2 | 16 | 255 | `paint_chrome_brighten` | **CRITICAL**: CC=16 should be CC=0. Real chrome has no clearcoat. |
| `candy` | `spec_candy` (L563) | 200 | 4 | 16 | 255 | `paint_fine_sparkle` | **CRITICAL**: M=200 far above ref (100-150). R=4 below ref (10-20). Looks like chrome, not candy. |
| `satin_metal` | `spec_satin_metal` (L515) | 235 | 65 (+/-20 brush) | 16 | 255 | `paint_subtle_flake` | M=235 high for satin. Directional brush grain is good. |
| `brushed_titanium` | `spec_brushed_titanium` (L574) | 180 (+/-25 grain) | 70 (+/-45 grain) | 0 | 255 | `paint_brushed_grain` | GOOD. CC=0 correct for raw metal. Strong directional grain. |
| `anodized` | `spec_anodized` (L592) | 170 (+/-20 grain) | 80 (+/-25 grain) | 0 | 255 | `paint_subtle_flake` | CC=0 correct. Noise scale=[1] invisible at 2048. Looks flat. |
| `hammered` | `spec_hammered` (L699) | 150-245 (dimple) | 8-120 (dimple) | 0 | 255 | `paint_hammered_dimples` | GOOD. CC=0 correct raw metal. 400 dimples at 8-22px, visible. |
| `metal_flake` | `spec_metal_flake` (L527) | 240 (+/-50 noise) | 12 (+/-40 noise) | 16 | 255 | `paint_coarse_flake` | M=240 very high. Noise scales [1,2,4,8] dominated by invisible pixel noise. |
| `holographic_flake` | `spec_holographic_flake` (L536) | 245 (+/-45 noise) | 10 (+/-30 noise) | 16 | 255 | `paint_coarse_flake` | Nearly identical to metal_flake. M=245 vs 240, R=10 vs 12. Indistinguishable pair. |
| `stardust` | `spec_stardust` (L545) | 160 base, ~255 on stars | 55 base, ~3 on stars | 16 | 255 | `paint_stardust_sparkle` | GOOD. 2% star density creates visible pinpoint flashes. Unique approach. |
| `frozen` | `spec_frozen` (L635) | 225 (+/-30 noise) | 140 (+/-20 noise) | 0 | 255 | `paint_subtle_flake` | Noise scales [1,2,4] invisible. Looks like flat M=225/R=140. |
| `frost_bite` | `spec_frost_bite` (L799) | 230 (+/-35 noise) | 80 (+/-40 noise) | 16 | 255 | `paint_subtle_flake` | Similar to frozen but glossier (CC=16 vs 0). Names confusing. Noise barely visible. |
| `carbon_fiber` | `spec_carbon_fiber` (L643) | 55 | 30+cf*50 (30-80 weave) | 16 | 255 | `paint_carbon_darken` | GOOD. M=55 in ref range (40-60). R=30-80 matches ref. 24px twill visible. Paint mod matches spec weave. |
| `forged_carbon` | `spec_forged_carbon` (L988) | 60-100 (chunk) | 25-83 (chunk+fine) | 14 | 255 | `paint_forged_carbon` | CC=14 is OFF. Comment says clearcoat desired. Change to 16 for epoxy clearcoat. |
| `diamond_plate` | `spec_diamond_plate` (L831) | 180-240 (diamond) | 8-140 (diamond) | 0 | 255 | `paint_diamond_emboss` | GOOD. CC=0 raw metal. 32px diamonds visible. High contrast. |
| `dragon_scale` | `spec_dragon_scale` (L846) | 120-255 (dist) | 3-160 (dist) | 16 | 255 | `paint_scale_pattern` | GOOD. 40px scales visible. Mirror centers, matte edges. |
| `hex_mesh` | `spec_hex_mesh` (L606) | 100-255 (wire/center) | 5-160 (wire/center) | 16 | 255 | `paint_hex_emboss` | GOOD. 24px honeycomb visible. Chrome centers, matte wire. |
| `ripple` | `spec_ripple` (L670) | 140-240 (ring) | 5-90 (ring) | 16 | 255 | `paint_ripple_reflect` | GOOD. 6-10 ring origins, 20-40px spacing. Visible interference rings. |
| `lightning` | `spec_lightning` (L741) | 80-255 (bolt/bg) | 3-180 (bolt/bg) | 16 | 255 | `paint_lightning_glow` | Imports scipy inside function (L787). Bare except silently swallows errors. |
| `plasma` | `spec_plasma` (L890) | 160-255 (vein/bg) | 2-120 (vein/bg) | 16 | 255 | `paint_plasma_veins` | GOOD. Thin vein network distinct from lightning bolts. |
| `hologram` | `spec_hologram` (L927) | 220 | 5-80 (scanline) | 16 | 255 | `paint_hologram_lines` | GOOD. 6px scanline bands. Chromatic aberration in paint mod. |
| `interference` | `spec_interference` (L941) | 240 | 5-105 (wave) | 16 | 255 | `paint_interference_shift` | GOOD. Multi-frequency sine waves. Paint mod does actual hue rotation. |
| `battle_worn` | `spec_battle_worn` (L813) | 200 (+/-50 noise) | 50 (+/-120 noise) | 0-16 variable | 255 | `paint_scratch_marks` | GOOD. Variable clearcoat is unique. Directional scratch pattern. |
| `worn_chrome` | `spec_worn_chrome` (L864) | 100-255 (wear) | 2-120 (wear) | 0-16 variable | 255 | `paint_patina` | GOOD. Patchy wear with degrading clearcoat. Green/brown oxidation tint. |
| `acid_wash` | `spec_acid_wash` (L914) | 200 (+/-35 noise) | 60 (+/-100 noise) | 0-16 variable | 255 | `paint_acid_etch` | R noise +/-100*sm is extreme. At aggressive (sm=1.5): R swings 0-210. |
| `cracked_ice` | `spec_cracked_ice` (L1006) | 230 (+/-15 noise) | 15-130 (crack) | 16 | 255 | `paint_ice_cracks` | GOOD. Smooth ice + rough cracks. Voronoi network in paint mod. |
| `liquid_metal` | `spec_liquid_metal` (L878) | 255 | 2-50 (pool) | 16 | 255 | `paint_liquid_reflect` | CC=16 wrong. Mercury/T-1000 is raw metal. Should be CC=0. |
| `ember_glow` | `spec_ember_glow` (L903) | 180-220 (hot) | 40 (+/-20 noise) | 8 | 255 | `paint_ember_glow` | CC=8 is OFF (0-15 range). Comment says "mid clearcoat" but iRacing has no mid-CC. |
| `phantom` | `spec_phantom` (L1024) | 215-245 (peek) | 2-22 (peek) | 16 | 255 | `paint_phantom_fade` | GOOD. Ultra-mirror vanishing effect. Paint mod desaturates. Unique. |
| `blackout` | `spec_blackout` (L1060) | 30 | 220 | 0 | 200 | `paint_none` | A=200 not 255. Only finish with reduced alpha. Weakens spec authority. |

---

## Detailed Issue List (With Line Numbers)

### CRITICAL -- Values Wrong Per PBR Reference

**Issue 1: pearl is basically chrome (Lines 496-506)**
```
spec[:,:,0] = np.clip(210 * mask + ...   # M=210, ref says 80-120
spec[:,:,1] = np.clip(8 * mask + ...     # R=8, ref says 30-50
```
- Current: M=210, R=8, CC=16
- Reference: M=80-120, R=30-50, CC=16
- Pearl should have moderate metallic so paint color shows through with soft iridescent sheen. At M=210/R=8 this is a mirror that washes out the color completely. The wave noise on top of a mirror base produces "slightly wobbly chrome" not "pearl".
- **Fix Line 502:** Change `210 * mask` to `100 * mask`
- **Fix Line 504:** Change `8 * mask` to `40 * mask`

**Issue 2: chrome has clearcoat CC=16 (Lines 508-513)**
```
spec[:,:,2] = 16    # Should be 0 for raw mirror chrome
```
- Current: M=255, R=2, CC=16
- Reference: M=255, R=0-5, CC=0
- Real chrome is raw polished metal with no clearcoat layer. CC=16 adds a gloss film that softens the mirror reflection. In iRacing this makes chrome look like "glossy metallic" rather than pure mirror.
- **Fix Line 512:** Change `spec[:,:,2] = 16` to `spec[:,:,2] = 0`

**Issue 3: candy metallic way too high (Lines 563-572)**
```
spec[:,:,0] = np.clip(200 * mask + ...   # M=200, ref says 100-150
spec[:,:,1] = np.clip(4 * mask + ...     # R=4, ref says 10-20
```
- Current: M=200, R=4, CC=16
- Reference: M=100-150, R=10-20, CC=16
- Candy is deep transparent gloss -- you look through tinted glass at a metallic base. At M=200 the metallic reflection overpowers the paint color. The whole point of candy is the COLOR showing through, not mirror reflection.
- **Fix Line 569:** Change `200 * mask` to `130 * mask`
- **Fix Line 570:** Change `4 * mask` to `15 * mask`

**Issue 4: liquid_metal has clearcoat (Lines 878-888)**
```
spec[:,:,2] = 16    # Mercury has no clearcoat
```
- Current: M=255, R=2-50, CC=16
- Mercury/T-1000 is raw liquid metal, no clearcoat.
- **Fix Line 887:** Change `spec[:,:,2] = 16` to `spec[:,:,2] = 0`

---

### MODERATE -- Noticeable Inaccuracy

**Issue 5: gloss has M=5, should be M=0 (Line 469)**
```
spec[:,:,0] = np.clip(5 * mask + 5 * (1-mask), 0, 255)   # M=5, ref says 0
```
- Standard gloss paint is dielectric (non-metallic). M=5 introduces slight metallic reflection.
- **Fix Line 469:** Change `5 * mask` to `0 * mask` (or just `5 * (1-mask)`)

**Issue 6: matte R=190, should be 200-230 (Line 477)**
```
spec[:,:,1] = np.clip(190 * mask + ...   # R=190, ref says 200-230
```
- At R=190 this reads as semi-matte. Full flat/matte needs higher roughness.
- **Fix Line 477:** Change `190 * mask` to `215 * mask`

**Issue 7: satin CC=16, should be 8-12 (Line 485)**
```
spec[:,:,2] = 16    # Max clearcoat, ref says 8-12
```
- Satin has LESS gloss than full clearcoat. Max CC makes this read as "slightly rough gloss" not satin.
- **Fix Line 485:** Change `spec[:,:,2] = 16` to `spec[:,:,2] = 10`

**Issue 8: metallic M=225 above range, R=20 too smooth (Lines 491-492)**
```
spec[:,:,0] = np.clip(225 * mask + ...   # M=225, ref says 180-220
spec[:,:,1] = np.clip(20 * mask + ...    # R=20, ref says 40-60
```
- M=225 exceeds the 180-220 metallic range. R=20 is much smoother than the 40-60 reference which accounts for micro-flake diffusion.
- **Fix Line 491:** Change `225 * mask` to `200 * mask`
- **Fix Line 492:** Change `20 * mask` to `50 * mask`
- Also: Noise scales [1,2,4] are invisible at 2048 resolution. Change to [4,8,16] for visible flake.

**Issue 9: forged_carbon CC=14 is OFF, comment says clearcoat desired (Line 1002)**
```
spec[:,:,2] = np.clip(14 * mask + ...    # B=14 is clearcoat OFF
```
- Code comment on L1001: "moderate (real forged carbon has epoxy clearcoat)"
- But B=14 is in the 0-15 OFF range. If clearcoat is intended, needs B=16.
- **Fix Line 1002:** Change `14 * mask` to `16 * mask`

**Issue 10: ember_glow CC=8 is OFF, not "mid clearcoat" (Line 910)**
```
spec[:,:,2] = 8     # Comment: "MID clearcoat -- never used before!"
```
- iRacing has no mid-clearcoat. B=0-15 = OFF, B=16 = ON. B=8 is just OFF.
- **Fix Line 910:** Change to `16` for clearcoat ON, or `0` for explicitly OFF

**Issue 11: blackout A=200 weakens spec authority (Line 1066)**
```
spec[:,:,3] = np.clip(200 * mask + 255 * (1-mask), 0, 255)   # Reduced alpha
```
- Only finish with A!=255. Reduced alpha means iRacing partially ignores the spec map, blending with defaults. The matte blackout effect will be weaker than intended.
- **Fix Line 1066:** Change `200 * mask` to `255 * mask` for full authority, OR document that this is intentional

---

### LOW -- Cosmetic / Edge Cases

**Issue 12: holographic_flake is a near-clone of metal_flake (Lines 527-543)**
- metal_flake: M=240, R=12, noise [1,2,4,8] / [1,3,6]
- holo_flake: M=245, R=10, noise [1,2,4,6] / [1,3]
- These are functionally identical. Both use `paint_coarse_flake`. At 2048 resolution the 5-unit metallic difference and 2-unit roughness difference are invisible.
- **Fix:** Redesign holographic_flake with a fundamentally different pattern (e.g., prismatic bands, fine grid sparkle, or scanline-like alternation)

**Issue 13: acid_wash extreme roughness swing (Line 919)**
```
spec[:,:,1] = np.clip(60 * mask + ... + etch * 100 * sm * mask, ...)
```
- At aggressive intensity (sm=1.5): roughness noise is +/-150, meaning G can swing from 0 to 210.
- This produces unpredictable spotty results.
- **Fix Line 919:** Cap noise multiplier at 60 instead of 100

**Issue 14: lightning uses scipy import inside function + bare except (Lines 787-791)**
```python
from scipy.ndimage import gaussian_filter    # Inside function body
try:
    bolt_map = gaussian_filter(bolt_map, sigma=1.5)
except:
    pass  # Bare except swallows ALL errors including KeyboardInterrupt
```
- If scipy is missing, bolt edges are jagged with no user warning.
- Bare `except` catches KeyboardInterrupt, SystemExit, MemoryError, etc.
- **Fix:** Use PIL GaussianBlur like all other functions, or import at module level and catch ImportError specifically

**Issue 15: frost_bite vs frozen naming/value confusion (Lines 635, 799)**
- frozen: M=225, R=140, CC=0 (matte raw frost)
- frost_bite: M=230, R=80, CC=16 (glossy frost)
- "Frost bite" is conceptually MORE severe than "frozen" but has LOWER roughness and clearcoat ON, making it glossier. This is counterintuitive.
- Both share `paint_subtle_flake` and have invisible noise textures.
- **Fix:** Swap roughness values (frost_bite should be rougher), or give frost_bite CC=0 and unique ice-crystal pattern

---

## Noise Scale Visibility Audit

At 2048x2048, noise at scale=1 is per-pixel (invisible at any normal view distance). Minimum visible scale is approximately 8.

| Finish | Noise Scales | Visible at 2048? |
|--------|-------------|-----------------|
| metallic | [1, 2, 4] | NO -- invisible |
| anodized | [1] | NO -- invisible |
| frozen | [1, 2, 4] | NO -- invisible |
| frost_bite | [2, 4, 8] / [2, 6, 10] | BARELY -- scale 8-10 marginal |
| metal_flake | [1, 2, 4, 8] / [1, 3, 6] | BARELY -- dominated by invisible scale 1 |
| holographic_flake | [1, 2, 4, 6] / [1, 3] | NO -- invisible |
| stardust | Per-pixel stars | YES -- intentional pinpoints |
| pearl | [16, 32, 64] | YES -- large gentle waves |
| liquid_metal | [16, 32, 64] | YES -- large pooling |
| ember_glow | [8, 16, 32] | YES -- visible hotspots |
| all geometric | Procedural patterns 24-40px | YES -- excellent |
| all effects | Large-scale patterns | YES -- excellent |
| all damage | Multi-scale [4-32] | YES -- visible patterns |

**6 finishes have invisible texture and read as flat values.** These are: metallic, anodized, frozen, frost_bite (barely), metal_flake (barely), holographic_flake.

---

## Paint Modifier Reference Table

| Paint Modifier (Line) | Used By | Effect |
|---|---|---|
| `paint_none` (L1074) | gloss, matte, satin, blackout | No modification |
| `paint_subtle_flake` (L1077) | metallic, satin_metal, anodized, frozen, frost_bite | Fine noise sparkle + brightness boost. **5 finishes share this -- reduces differentiation.** |
| `paint_fine_sparkle` (L1086) | pearl, candy | Sparse bright sparkle points at 5% density + fine noise |
| `paint_coarse_flake` (L1098) | metal_flake, holographic_flake | Per-channel RGB noise + 6% bright glints |
| `paint_carbon_darken` (L1116) | carbon_fiber | 24px 2x2 twill weave darken/lighten (adaptive for dark/light paints) |
| `paint_chrome_brighten` (L1144) | chrome | Blends paint toward 0.92 silver + reflection noise |
| `paint_scratch_marks` (L1163) | battle_worn | 120 directional linear scratches, adaptive light/dark |
| `paint_diamond_emboss` (L1193) | diamond_plate | 16px geometric diamond raises |
| `paint_scale_pattern` (L1209) | dragon_scale | 24px hex grid with per-scale color shift |
| `paint_patina` (L1238) | worn_chrome | Green/brown oxidation tint in patchy areas |
| `paint_liquid_reflect` (L1253) | liquid_metal | Large wave reflections toward silver (scales [16,32]+[24,48]) |
| `paint_plasma_veins` (L1268) | plasma | Branching vein glow + blue/purple tint |
| `paint_ember_glow` (L1284) | ember_glow | Orange/red hotspot tint, cool area darkening |
| `paint_acid_etch` (L1303) | acid_wash | Splotchy erosion darkening + desaturation |
| `paint_hologram_lines` (L1317) | hologram | 4px scanlines + chromatic aberration (R/B channel shift) |
| `paint_interference_shift` (L1337) | interference | Full HSV hue rotation via multi-frequency sine waves |
| `paint_forged_carbon` (L1373) | forged_carbon | Heavy darkening toward black + per-chunk tonal variation |
| `paint_ice_cracks` (L1395) | cracked_ice | Voronoi crack network + blue tint |
| `paint_stardust_sparkle` (L1433) | stardust | Sparse 2% bright pinpoints matching spec star density |
| `paint_hex_emboss` (L1447) | hex_mesh | 24px honeycomb wire dark/light pattern |
| `paint_ripple_reflect` (L1470) | ripple | 6-origin concentric ring reflections |
| `paint_hammered_dimples` (L1495) | hammered | 400 dimple indentations (light centers, dark edges) |
| `paint_lightning_glow` (L1534) | lightning | 4 bolt paths glow white/blue + background darken |
| `paint_brushed_grain` (L1574) | brushed_titanium | Horizontal directional grain lines |
| `paint_phantom_fade` (L1044) | phantom | Desaturate toward silver + brighten for vanishing effect |

---

## Summary

### Issue Count by Severity

| Severity | Count | Finishes Affected |
|----------|-------|-------------------|
| CRITICAL (wrong per PBR ref) | 4 | pearl, chrome, candy, liquid_metal |
| MODERATE (noticeable) | 7 | gloss, matte, satin, metallic, forged_carbon, ember_glow, blackout |
| LOW (cosmetic/edge) | 4 | holographic_flake=metal_flake dupe, acid_wash extreme noise, lightning scipy, frozen/frost_bite confusion |
| **TOTAL** | **15** | |

### Finishes With No Issues (19/34)

satin_metal, brushed_titanium, hammered, stardust, carbon_fiber, diamond_plate, dragon_scale, hex_mesh, ripple, plasma, hologram, interference, battle_worn, worn_chrome, cracked_ice, phantom, anodized (values ok, texture invisible), frozen (values ok, texture invisible), frost_bite (values ok, texture barely visible)

Note: anodized, frozen, and frost_bite have correct PBR VALUES but their noise textures are invisible or barely visible at 2048x2048. They are not "wrong" -- they just lack visible texture differentiation.

### Priority Fix Order

1. **pearl** -- M from 210 to 100, R from 8 to 40 (currently renders as chrome)
2. **candy** -- M from 200 to 130, R from 4 to 15 (currently renders as chrome)
3. **chrome** -- CC from 16 to 0 (incorrect clearcoat on raw mirror)
4. **liquid_metal** -- CC from 16 to 0 (incorrect clearcoat on mercury surface)
5. **metallic** -- M from 225 to 200, R from 20 to 50, noise scales to [4,8,16]
6. **satin** -- CC from 16 to 10
7. **matte** -- R from 190 to 215
8. **gloss** -- M from 5 to 0
9. **forged_carbon** -- CC from 14 to 16 (or 0 for raw)
10. **ember_glow** -- CC from 8 to 16 (or 0)
11. **holographic_flake** -- redesign to differentiate from metal_flake
12. **blackout** -- A from 200 to 255 (or document intentional)
