# R - Rendered previews for spec patterns and patterns (2026-10-03)

## Render path
`_atlas_deep/render_previews.py` (one process, below-normal priority, resumable). The server `/api/swatch/<type>/<key>` has NO `spec` type
(404 "Unknown swatch type: spec") and its pattern route is a 128 px swatch, so the engine is driven offline:
`shokker_engine_v2.preview_render()` on a 2048 canvas with one zone (`base` + `spec_pattern_stack` [layer opacity 1.0, channels MRC] or `pattern`),
solid mid-grey base colour (0.54). The engine returns paint + M|R|Cc spec map. The engine has no lit preview of a flat sheet,
so lighting is ours: a flat panel facing a fixed studio environment (sky gradient, bright diagonal softbox, dark flag, dark floor band);
metal (R channel) tints the reflection, roughness (G) blurs the environment, clearcoat (B, 16 = glossy) adds a sharp clear layer.
Glossy pixels mirror the softbox sharply, rough pixels smear it, metallic pixels turn bright. Each tile is a 1:1 512 px crop of the 2048 render (true default scale).
Note: neutral grey paint is treated as "unpainted" by the `everything` selector, so a red selector paint is fed in; `base_color` explicit solid overrides it.

## spec done
- 301 spec-pattern renders, `_atlas_deep/img/spec/<id>.png`, 1024x536 (24 px label strip + 1024x512): LEFT over mid-grey SATIN base, RIGHT over mid-grey METALLIC base (`f_metallic`). 0 failures, 5.2 s per item (two 2048 renders + lighting).
- Shards 001-006 updated: `img` = new path, `img_px` = [1024, 536], old strip path kept in `img_strip` (old size in `img_small_px`). Script: `_atlas_deep/update_shards_img.py`.
- Eyeball (candle_wax_veve, metallic_sand, spec_lfr_firework_radial, spov2_wing_scale_sockets, plus abalone_crack_inlay, acanthus_scrolls): the texture is clearly readable now (cells, scales, firework radials, sand grain, wax ripples); the satin vs metallic comparison shows the pattern's effect on shine. Subtle patterns (candle_wax_veve) are faint but visible in the softbox band: that faintness is real, and a writer should call such a pattern "subtle".
Caveat: the light is a fixed studio setup, so judge "what moves" from the softbox band: texture is strongest inside the bright band and fades in the dark floor/flag areas.

## patterns done
- 319 pattern renders (4 were done in the test run), `_atlas_deep/img/pattern/<id>.png`, 1024x536: LEFT default scale 1:1 (512 crop of a 2048 render over a neutral solid satin base, same studio light), RIGHT 2x zoom of the centre 256 px. 0 failures, 2.4 s per item.
- Shards 007-012 updated: `img` = new path, `img_px` = [1024, 536], old swatch path in `img_strip` / `img_small_px`.
- Eyeball (razor_wire, gothic_arch, decade_50s_drivein_marquee, 6868396_23455, rune_symbols, 12155818_4903117): motifs, colours and fine edge detail (razor barbs, pixel-stepped arches, rune dots) are clearly readable; image-asset patterns show a mosaic of their tiles. The paint colours are the pattern's own (the pattern replaces the neutral base colour); the soft light band is the studio lighting, not part of the pattern.
- RUBRIC.md "Reading the data" picture bullet rewritten for the new images.
