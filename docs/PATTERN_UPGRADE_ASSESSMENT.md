# Pattern Upgrade Assessment — Are They Good & Worth It?

**Question:** Are the staging pattern upgrades (astro_cosmic_v2, damage_wear_v2) **good patterns** that work in the current ecosystem and **worth** replacing the old astro/damage groups?

**Short answer:** **Yes.** Both are clear upgrades in variety, distinctness, and fit. One integration fix is required (scalar `bb` support).

---

## 1. How patterns are used in the ecosystem

- **Texture:** `tex_fn(shape, mask, seed, sm)` is called; must return a dict with `pattern_val` (float32 H×W), `R_range`, `M_range`, and optionally `CC`. Used for blend alpha and M/R modulation.
- **Paint:** `pat_paint_fn(paint, shape, hard_mask, seed, pm, bb)` is called with **scalar** `pm` and **scalar** `bb` (see `compose.py` lines 1263–1265, 1731). The pattern’s paint result is then blended with the zone paint using `pattern_val` as alpha.
- **Contract:** PM=0 → output ≈ input (identity). No NaN; paint in [0,1].

Staging modules return the right texture dict. Their paint_fns use `bb[:, :, np.newaxis]`, so they expect **array** `bb`. The engine passes **scalar** `bb` → would raise `TypeError` if called as-is. **Fix:** wrap staging paint_fns so that when `bb` is a scalar, expand it to `np.full(shape[:2], float(bb), dtype=np.float32)` before calling the staging implementation. Same pattern as color_monolithics/atelier.

---

## 2. Old vs new — Astro / Cosmic

### Old (expansion_patterns.py + pattern_expansion.py)

| What | Reality |
|------|--------|
| **Texture** | 7 astro (moon_phases, stars_constellation, sun_rays, orbital_rings, comet_trail, galaxy_swirl, nebula_drift) + 12 zodiac glyphs. Each has its own geometry (circles, scatter+lines, radial starburst, concentric rings, comet head+trail, log spiral, tiled symbol). |
| **Paint** | **Only 3–4 engine calls for all 19 entries:** “stars/cosmic/comet/galaxy” → `paint_stardust_sparkle` or `paint_coarse_flake`; “sun_rays” → `paint_lightning_glow`; “zodiac” → `paint_celtic_emboss` or `paint_ripple_reflect`; everything else → `paint_ripple_reflect`. So comet_trail and galaxy_swirl get the **same** paint effect; moon_phases and orbital_rings also share. |
| **Distinctness** | Textures are different; **paint is generic**. Many options look similar in color. Zodiac is decorative, not physics-based. |

### New (astro_cosmic_v2.py)

| What | Reality |
|------|--------|
| **Texture** | 12 entries, each with a **unique** physics-based texture (pulsar beam, event horizon, corona, nebula pillars, magnetar, asteroid belt, lensing, cosmic web, CME, dark-matter halo, quasar jet, supernova remnant). |
| **Paint** | **12 unique paint functions** — e.g. pulsar = cool blue-white pulse, event_horizon = warm accretion glow, corona = golden tendrils, nebula_pillars = blue-green + dust reddening, magnetar = violet/cyan, etc. Each matches the physics of the texture. |
| **Distinctness** | Every entry is visually and physically distinct. No zodiac; coherent “astrophysics” theme. |

**Verdict — Astro:** **Worth the change.** You gain 12 distinct cosmic looks with matching color treatment, and drop 19 old entries (7 astro + 12 zodiac) that shared only a few generic paint effects. Fits a paint booth as a premium/livery theme (cosmic, sci-fi, racing fantasy).

---

## 3. Old vs new — Damage & Wear

### Old (arsenal_24k.py Group 10)

| What | Reality |
|------|--------|
| **Texture** | 7 entries with **unique** textures: bullet_holes (craters + rim + cracks), shrapnel (jagged fragments), road_rash (directional scratches), rust_bloom (organic rust patches), peeling_paint, g_force (radial compression), spark_scatter. Each has its own geometry. |
| **Paint** | **Only 4 shared paint functions:** `ppaint_darken_heavy` (bullet_holes, shrapnel), `ppaint_darken_medium` (road_rash, peeling_paint), `ppaint_tint_rust` (rust_bloom), `ppaint_emboss_heavy` (g_force), `ppaint_glow_red` (spark_scatter). So bullet_holes and shrapnel look different in shape but **same** in color (both darken_heavy). |
| **Distinctness** | Texture: good. **Paint: generic** — damage type is not reflected in color (e.g. no “bare metal” for road rash, no “temper color” for weld, no “acid stain” for chemical). |

### New (damage_wear_v2.py)

| What | Reality |
|------|--------|
| **Texture** | 14 entries, each with **unique** damage physics: ballistic (crater + stress fractures + spall), hail (dent field + compression rings), sandblast (directional erosion), thermal_fatigue (crazing), acid_etch_drip (drips + pooling), weld_splatter (droplets + HAZ), chain_drag (gouges + ridges), impact_spider (radial cracks), salt_rot (blistering + rust), exhaust_soot (carbon + falloff), rockchip_constellation, UV_delamination, freeze_thaw_heave, electrolysis_pitting. |
| **Paint** | **14 unique paint functions** — e.g. ballistic = dark crater + bright rim + blue-gray cracks; sandblast = silver bare metal reveal; thermal_fatigue = oxide rainbow (gold→purple→blue); acid_etch_drip = green-yellow stain + dark channels; weld_splatter = temper halos + burn centers; salt_rot = orange-brown rust through blister paint; etc. Each matches the damage type. |
| **Distinctness** | Every entry is a distinct damage scenario with matching color response. More real-world cases (rock chips, UV clearcoat failure, electrolysis) and better for storytelling on a car. |

**Verdict — Damage:** **Worth the change.** You go from 7 damage types with 4 shared paints to 14 damage types with 14 distinct paint effects. The new set reads as real damage (ballistic, environmental, chemical, mechanical) and fits the paint-booth use case.

---

## 4. Ecosystem compatibility

| Check | Status |
|-------|--------|
| Texture return shape | Staging returns `{"pattern_val": float32[H,W], "R_range", "M_range", "CC": None}`. Matches what compose expects. |
| Paint signature | `(paint, shape, mask, seed, pm, bb)` — correct. |
| PM identity | 26/26 pass with pm=0 when bb is 2D. |
| Scalar `bb` | Engine passes **scalar** bb. Staging uses `bb[:,:,np.newaxis]` → will crash. **Required fix:** wrap each staging paint_fn so that if `np.isscalar(bb)` (or ndim==0), set `bb = np.full(shape[:2], float(bb), dtype=np.float32)` before use. |
| Seed stability / edge cases | No crashes on (8,8), (16,16), (512,512); output finite and in range; same seed → same output. |

So: **they work in the ecosystem** once paint_fns are wrapped for scalar `bb`.

---

## 5. Summary

- **Astro:** Old = 19 entries (7 astro + 12 zodiac), only a few generic paint effects. New = 12 astrophysics entries, each with unique texture + unique paint. **Good patterns, worth the swap.**
- **Damage:** Old = 7 entries with unique textures but only 4 shared paints. New = 14 entries, each with unique texture + unique paint and real damage semantics. **Good patterns, worth the swap.**
- **Implementation:** Integrate as planned (replace IDs in pattern_expansion.py; merge astro from astro_cosmic_v2 and damage from damage_wear_v2 in expansion_patterns / arsenal_24k). **Add a scalar-`bb` wrapper** for all staging paint_fns so the current engine (which passes scalar `bb`) works without changing compose.

**Bottom line:** Yes — they are good patterns that fit the current ecosystem and are worth implementing and replacing the old groups, as long as you add the scalar-`bb` handling at integration time.
