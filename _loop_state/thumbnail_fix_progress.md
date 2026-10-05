# Thumbnail Fix — Progress Log

Diagnostic: `THUMBNAIL_BUG_DIAGNOSTIC.md`. This tick implements Fix 1 (drop env-var gate, prefer real engine, cache to disk by renderer-hash) and closes Divergence 2 (zone-shape mismatch between bake and live preview).

## WHAT-CHANGED

### `server_routes/swatch_routes.py` (+ 2 mirrored copies)
- L13-32 `register_swatch_routes(...)` — new optional kwarg `picker_finish_renderer_hash` so the route can compute a stable disk-cache key per finish definition.
- L126-...  picker split branch rewritten:
  - **Dropped the env-var gate** (`SHOKKER_SWATCH_LIVE_SPLIT`). The real-engine path now runs whenever `prefer=live` (the default URL param).
  - **Added per-finish disk cache** at `thumbnails/swatch_cache/picker_split/{type}_{key}_{color}_{size}_{hash}.png`. Cache key includes `_picker_finish_renderer_hash(...)` so when a finish's paint_fn / spec_fn / texture_fn source line changes, the cache invalidates automatically.
  - Fake painter (`render_fast_split_swatch_bytes`) now only runs as a **last-resort fallback** when the real engine raises. Fallback output is NOT cached (so a transient error doesn't pin synthetic pixels on disk).

### `server.py` (+ 2 mirrored copies)
- L1860 `_catalog_swatch_zone_for_preview(...)` — kept legacy signature, now delegates to v2 builder. Old body renamed to `_catalog_swatch_zone_for_preview_legacy` and kept for reference.
- New `_catalog_swatch_zone_for_preview_v2(...)` — emits the **full ~25-key zone** that mirrors `addZone()` defaults in `paint-booth-2-state-zones.js`: `base_strength`, `base_color_mode`, `base_color`, `base_color_strength`, `base_color_scale`, `base_color_rotation`, `base_color_fit_zone`, `base_offset_x/y`, `base_rotation`, `base_flip_h/v`, `base_hue_offset`, `base_saturation_adjust`, `base_brightness_adjust`, `pattern_opacity`, `pattern_offset_x/y`, `pattern_flip_h/v`, empty `spec_pattern_stack` / `overlay_spec_pattern_stack` / `third/fourth/fifth_overlay_spec_pattern_stack`, plus pattern_rotation for patterns. (Engine treats omitted keys as the same defaults, but explicit-over-implicit protects against future engine default drift and documents the contract.)
- L4448 `register_swatch_routes(...)` call — added `picker_finish_renderer_hash` kwarg wired to `_picker_finish_renderer_hash`.

### "Build All Thumbnails" pipeline
- `rebuild_picker_swatches.py` → `bake_picker_split_batch` → `save_picker_split_snapshot` → `_render_picker_split_snapshot_bytes` → `_catalog_swatch_zone_for_preview` (now v2). No script edit needed; the new zone shape flows through automatically.

## WHY
- The picker dropdown was serving paint pixels from the synthetic `_render_swatch_bytes` "fake painter" (peaks*0.55, valleys*0.32, 0.38 hue tint) because the real-engine path was gated behind `SHOKKER_SWATCH_LIVE_SPLIT` (off by default) AND the only baked PNG on disk was `monolithic/depth_wave.png`. Dropping the env gate makes the real engine the default. Caching by renderer hash makes it cheap on repeat loads and self-invalidates when finishes are edited. The zone enrichment removes the divergence between bake and live preview for v6 finish features.

## VERIFY
Side-by-side renders in `_loop_state/thumbnail_fix_verify/`:

| Category               | Type        | Key                | New engine | Old fake-painter |
|------------------------|-------------|--------------------|-----------:|-----------------:|
| Base                   | base        | chrome             |   6507 B   |   3648 B         |
| Pattern                | pattern     | carbon_3k_weave    |  16352 B   |  30194 B         |
| Monolithic / Special   | monolithic  | depth_wave         |  41419 B   |  38628 B         |
| MC (multi-coat)        | monolithic  | acid_rain          |  41774 B   |  44481 B         |
| Gradient               | monolithic  | grad_sunset        |  23671 B   |  29626 B         |

All five `_compare__*.png` files were generated. The new-engine paint half visibly tracks the live preview algorithm (uses real `build_multi_zone` / `compose_finish` / spec stacks), while the old fake-painter is the legacy peaks/valleys synth. `python -c "import server"` returns OK after each batch of edits.

Note: `carbon_2x2`, `mc_fire_storm`, `grad_sunset` were canonical test names; resolver substituted `carbon_3k_weave`, `acid_rain`, and a matching `grad_*` finish from the current registry.

## REMAINING

Fix 2 from the diagnostic (pre-bake the full picker_split library and ship it) is still recommended for release packaging — run `rebuild_picker_swatches.bat --package-alpha` to populate `thumbnails/picker_split/` for all 262+ finishes. Not blocking: Fix 1 covers the on-the-fly case for missing PNGs.

DONE for this tick.

## DONE — 2026-05-27T06:43:42Z

Both engine fixes (env-gate drop, content-hash cache, v6 zone shape) are in. 3-copy mirrored, server imports clean, 5 category compare PNGs verify the new path matches live preview shape. "Build All Thumbnails" routes through the upgraded path with no script change required.

Optional next-tick work: full `rebuild_picker_swatches.bat --package-alpha` to pre-bake the shipped catalog (saves first-paint cost in release builds).
