# Pattern Category Upgrade Verification Report

**Date:** 2026-03-14  
**Scope:** `_staging/pattern_upgrades/astro_cosmic_v2.py` (12 entries) and `damage_wear_v2.py` (14 entries)  
**Status:** Staging modules **validated**; integration **not yet applied**

---

## 1. PM identity (handoff script)

Run from V5 root with **2D `bb`** (see note below):

```python
import sys
sys.path.insert(0, '_staging/pattern_upgrades')
from astro_cosmic_v2 import ASTRO_COSMIC_PATTERNS
from damage_wear_v2 import DAMAGE_WEAR_PATTERNS
import numpy as np
shape = (64, 64)
mask = np.ones(shape, dtype=np.float32)
bb = np.full(shape, 0.5, dtype=np.float32)  # 2D required
paint = np.random.rand(64, 64, 3).astype(np.float32)
for name, entry in {**ASTRO_COSMIC_PATTERNS, **DAMAGE_WEAR_PATTERNS}.items():
    tex = entry["texture_fn"](shape, mask, 42, 0.5)
    out = entry["paint_fn"](paint.copy(), shape, mask, 42, 0.0, bb)
    diff = np.max(np.abs(out - paint))
    status = "PASS" if diff <= 0.001 else "FAIL (diff=%f)" % diff
    print("  %s: %s" % (name, status))
```

**Result:** **26/26 PASS** (12 astro + 14 damage).

---

## 2. Edge cases and seed stability

- **Shapes:** (8,8), (16,16), (512,512) — texture_fn + paint_fn run without crash; output finite and in range.
- **Seed stability:** Same seed (99) run twice per entry; max pixel diff &lt; 1e-5 for all 26.
- **Result:** **0 issues** when `bb` is (H,W) float32.

---

## 3. BB scalar vs array

Staging paint functions use `bb[:, :, np.newaxis]`. If the engine passes **scalar** `bb`, those calls raise `TypeError: 'float' object is not subscriptable`.

- **Current staging:** Expects `bb` as (H,W) array.
- **Recommendation for integration:** At call site (or in a thin wrapper), expand scalar `bb` to `np.full(shape[:2], float(bb), dtype=np.float32)` so both scalar and array `bb` are supported, consistent with color_monolithics/atelier.

---

## 4. Engine integration points (current state)

| Location | Current state | Handoff action |
|----------|----------------|----------------|
| **engine/pattern_expansion.py** | `NEW_PATTERN_IDS` includes 7 astro + 12 zodiac IDs (lines 35–40). | **Replace** astro block with 12 new IDs: `pulsar_beacon`, `event_horizon`, `solar_corona`, `nebula_pillars`, `magnetar_field`, `asteroid_belt`, `gravitational_lens`, `cosmic_web`, `plasma_ejection`, `dark_matter_halo`, `quasar_jet`, `supernova_remnant`. |
| **engine/expansion_patterns.py** | ~959 lines. Astro/zodiac handled in `_texture_expansion` / `_paint_expansion` by variant (e.g. `astro_moon_phases`, `zodiac_aries`). `build_expansion_entries(pattern_ids)` builds one entry per ID via closure. | **Option A:** Add 12 branches for new astro IDs that delegate to `astro_cosmic_v2` texture/paint. **Option B:** In `_build_new_patterns()`, merge in `ASTRO_COSMIC_PATTERNS` from `engine.expansions.astro_cosmic_v2` (or staging) for those 12 IDs instead of building them via `build_expansion_entries`. |
| **engine/expansions/arsenal_24k.py** | Group 10 DAMAGE & WEAR: 7 entries — `bullet_holes`, `shrapnel`, `road_rash`, `rust_bloom`, `peeling_paint`, `g_force`, `spark_scatter`. Each uses shared paint (`ppaint_darken_heavy`, `ppaint_darken_medium`, etc.) and local `texture_*`. | **Replace** those 7 with 14 entries from `DAMAGE_WEAR_PATTERNS` (e.g. import from `engine.expansions.damage_wear_v2` and merge into the same dict that holds Group 10). Ensure texture/paint for the 14 are used; add scalar→2D `bb` wrapper if engine passes scalar. |

---

## 5. Contract checklist

| Contract | Staging |
|----------|--------|
| texture_fn(shape, mask, seed, sm) → `{"pattern_val": float32[H,W], "R_range", "M_range", "CC"}` | Yes (spot-checked). |
| paint_fn(paint, shape, mask, seed, pm, bb) → float32[H,W,3] | Yes. |
| PM identity (pm=0 → output ≈ input) | Yes, 26/26. |
| BB gating (bb terms × pm) | Yes; code uses bb and pm. |
| No NaN (clip / safe pow) | Yes in tested shapes. |
| Output in [0,1] | Yes in tested shapes. |

---

## 6. Summary

- **Staging content:** 26/26 entries pass PM identity, edge-case shapes, and seed stability when `bb` is (H,W).
- **Integration:** Not done yet. Pattern expansion and arsenal still use old astro/zodiac and old damage/wear entries.
- **Before integration:** Prefer Option B (import v2 modules and merge) to avoid duplicating logic; add scalar-`bb` handling at the layer that calls these paint_fns.
