# Prompt for Claude: Pattern Upgrade Feedback & Next Round

**Copy the text below and give it to Claude** (the model that authored the staging pattern upgrades in `_staging/pattern_upgrades/astro_cosmic_v2.py` and `damage_wear_v2.py`) so it knows what to keep, what to fix, and how to make the next round implementation-ready.

---

## What you got RIGHT

- **Per-pattern uniqueness:** Each of the 12 astro and 14 damage entries has its own **texture_fn** and **paint_fn**. No shared generic paints (e.g. one “stardust” or “darken_heavy” for many IDs). That’s the right direction for a benchmark paint app.
- **Physics / real-world basis:** Astro set is clearly astrophysics-based (pulsar, event horizon, corona, nebula pillars, magnetar, etc.); damage set covers real damage types (ballistic, hail, sandblast, thermal fatigue, acid etch, weld splatter, salt rot, UV delamination, electrolysis, etc.). Names and behavior match the theme.
- **Contract compliance:** Texture returns `{"pattern_val": float32[H,W], "R_range", "M_range", "CC": None}`; paint signature is `(paint, shape, mask, seed, pm, bb)`; **PM identity holds** (pm=0 ⇒ output ≈ input); outputs are finite, in [0,1], and NaN-safe in tested shapes. Seed-stable and no crashes on (8,8), (16,16), (512,512) when `bb` is 2D.
- **bb and pm usage:** You correctly gate pattern-driven color changes by **pm** (and use **bb** in the paint formulas). That matches how the engine uses these knobs.

---

## What you got WRONG (or missed)

- **Scalar `bb`:** The engine calls pattern paint_fns with **scalar** `pm` and **scalar** `bb` (see `engine/compose.py` around lines 1263–1265, 1731). Your paint_fns use `bb[:, :, np.newaxis]`, which assumes `bb` is a 2D array. With a scalar you get `TypeError: 'float' object is not subscriptable`. So the patterns were not directly callable by the engine until we wrapped them: when `bb` is scalar (or 0-d array), expand it to `np.full(shape[:2], float(bb), dtype=np.float32)` before any indexing. **Next time:** either accept both scalar and array `bb` inside each paint_fn (e.g. `bb = np.full(shape[:2], float(bb), dtype=np.float32) if np.isscalar(bb) or getattr(bb, 'ndim', 2) == 0 else bb` at the start), or document clearly that the engine passes scalar `bb` and that a wrapper is required at integration.
- **Texture signature:** You used `tex_fn(shape, mask, seed, sm)` and returned a dict. That’s correct. No change needed; just confirming so future patterns keep this contract.
- **R_range / M_range:** You used fixed values (e.g. 1.0, 2.0). The engine accepts that. If you want more control over specular response per pattern, we can later add optional `M_pattern` / `R_pattern` arrays in the texture dict; for this round, what you did is fine.

---

## What to do for the NEXT round (so patterns are implementation-ready)

1. **Support scalar `bb` in paint_fns**  
   At the top of every pattern paint_fn, normalize `bb` so it’s always (H,W) before using it:
   - If `bb` is scalar or 0-d: `bb = np.full((shape[0], shape[1]), float(bb), dtype=np.float32)`  
   - Then use `bb[:, :, np.newaxis]` (or equivalent) as you already do.  
   That way the same code works when the engine passes a scalar and when a test passes a 2D array.

2. **Keep the same contracts**  
   - Texture: `(shape, mask, seed, sm)` → dict with `pattern_val`, `R_range`, `M_range`, and optionally `CC`.  
   - Paint: `(paint, shape, mask, seed, pm, bb)` → float32 [H,W,3] in [0,1].  
   - PM identity: when pm=0, output must be very close to input (e.g. max diff ≤ 0.001) so the engine can blend by pattern_val without surprises.

3. **Naming and IDs**  
   - Use **snake_case** IDs that match the engine/frontend (e.g. `pulsar_beacon`, `ballistic_impact`, `acid_etch_drip`).  
   - Keep IDs stable so we can reference them in `NEW_PATTERN_IDS`, `PATTERN_GROUPS`, and the pattern registry without redoing mappings.

4. **Optional: per-pattern R_range / M_range**  
   If you want a pattern to affect specular more (e.g. metallic/roughness), return different `R_range` / `M_range` (or optional `R_pattern` / `M_pattern` arrays) from the texture_fn. Document the intent so integration doesn’t override it by mistake.

5. **Testing before handoff**  
   Run your own quick check with **scalar** `bb` (e.g. `bb = 0.5`) for all new paint_fns to ensure they don’t subscript `bb` before normalizing. That will catch the scalar bug before integration.

---

## Summary for Claude

- **Right:** Unique texture+paint per pattern, physics/real-damage theme, correct texture/paint contract, PM identity, bb/pm gating, no NaNs, seed stability.  
- **Wrong:** Assuming `bb` is always 2D; engine passes scalar `bb`, so paint_fns must normalize it.  
- **Next round:** Normalize scalar/0-d `bb` to (H,W) at the start of every paint_fn; keep contracts and IDs; optionally add per-pattern R/M; test with scalar `bb` before handoff.

The current staging modules have been integrated into the app with a **scalar-bb wrapper** applied at registration time. Future pattern sets that handle scalar `bb` inside the paint_fn will not need that wrapper.
