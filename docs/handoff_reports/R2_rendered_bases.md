# R2 rendered base/monolithic previews (2026-10-03)
- Script `_atlas_deep/render_bases.py <lo> <hi>`; path = build_atlas.render_base_or_mono (engine paint_fn/spec, neutral grey 0.5 input, seed 7777), 512x512 tile, 24px label strip.
- Image 1024x512: left default tile, right 2x zoom of centre. For flat-paint (spec-driven foundation) items the right panel instead shows spec M|R|Cc contrast-stretched (label says so); those paints are genuinely flat.
- 4,102 units, shards 013-081, all rendered, all 69 shards in img/_ready.json. ~0.8-1.3 s/item (2 BelowNormal processes, ~45 min total).
- Failures: acid_swirl / infinite_finish spec fns raise arg-count errors in the engine; rendered paint-only fallback (spec panel not available for them).
- Shard json: img -> _atlas_deep/img/<type>/<id>.png, img_px [1024,512], img_small = old thumbnail path.
