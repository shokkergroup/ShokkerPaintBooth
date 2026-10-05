# Encyclopedia v2 - Lane D (graphics) report

Scripts: `scripts/ai_atlas/enc_figs_lib.py` (helpers), `enc_figs_svg.py` + `enc_figs_svg2.py` (20 SVG diagrams), `enc_figs_render.py` (engine renders).
Output: `data/encyclopedia/figures/`, manifest `data/encyclopedia/figures.json` (merged by id; svg script owns g01-g20, render script owns r01-r14).
Ids are exactly the plan section 5 ids. Manifest entries: id, title, caption, file, kind, sources[] (file:line, verified at build time by src()), alt.
SVGs are dark theme (app tokens), 640 wide viewBox, min font 13 (about 12 px at 600 wide), no external fonts.

## Part 1 - SVG diagrams g01-g20 (built, looked at 1:1 in Edge)
All 20 built by one run. Looked at each rendered PNG; fixes made after looking are noted.
| id | looked |
|---|---|
| g01 | fixed (card overflow, 0/255 labels) then ok |
| g02 | ok |
| g03 | fixed (callout lines crossed text) then ok |
| g04 | fixed (caption collisions) then ok |
| g05 | fixed (rotated label collided) then ok |
| g06 | ok |
| g07 | ok |
| g08 | fixed (front arrow clipped) then ok |
| g09 | ok |
| g10 | ok (card height trimmed) |
| g11 | ok (card height trimmed) |
| g12 | fixed (labels under number badges, legend overflow, popout covered label) then ok |
| g13 | ok |
| g14 | ok |
| g15 | ok |
| g16 | fixed (B bar read as no coat: label now says low = glossy) then ok |
| g17 | ok |
| g18 | fixed (invented example relabelled "Too low (example)") then ok |
| g19 | fixed (duplicate squares, label) then ok |
| g20 | fixed ("new" label) then ok |

## Code vs docs disagreements found
- `docs/ai_knowledge/02_spec_and_finishes.md` says chrome is `M255 R2 CC0` and gloss `M0 R20 CC16`; code (`engine/base_registry_data.py`) has `f_chrome` CC 16 and `gloss` R 30. Code used.
- `f_soft_matte` registry CC is 165 but a live engine render returns 159 (engine adds small variation). Figures say "catalogue values".

## Part 2 - engine renders r01-r14 (script `scripts/ai_atlas/enc_figs_render.py`, one engine boot, WebP <= 250 KB)
Zones go through `shokker_engine_v2.preview_render` (payload shape from a real `zones_payload.json`); sphere swatches (r01-r03) feed the engine's spec output into an illustrative studio shader (`enc_figs_shade.py`) and say so in the caption: not iRacing lighting.
| id | looked |
|---|---|
| r01 | fixed (clearcoat 16 swamped it: shader retuned; axis label overlap) then ok |
| r02 | fixed (engine raises B=0 to 16 so 0 dropped; M150/G110 so steps show; label clipping) then ok |
| r03 | ok |
| r04 | ok |
| r05 | ok (59 shelf tiles, best-hero finish each, unique; "World of Color" casing fixed) |
| r06 | ok |
| r07 | ok |
| r08 | ok |
| r09 | fixed (base_scale had no effect on paint; now shows R-metal channel at 0.25/1/4x) then ok |
| r10 | fixed (gradient needed pos 0..1 and float rgb) then ok |
| r11 | ok |
| r12 | ok |
| r13 | ok |
| r14 | fixed (first draft wrongly claimed "same paint, only spec changes" and used a green gloss tile: now flat grey Before + the app's own preset preview thumbnails, honest caption) then ok |

## Engine findings
- Requested clearcoat 0 comes back as 16 from the engine finalizer (iron rule: CC is 0 only via no-coat paths, 1-15 never).
- `base_scale` scales only the SPEC channels of texture bases (R metal), not the paint colour.
- Gradient payload: `gradient_stops=[{"pos":0..1,"color":[r,g,b] floats 0..1}]` plus `gradient_direction`; hex strings or 0-100 positions silently do nothing.
- Code vs docs items above (chrome, gloss, f_soft_matte).

## Gaps
- r05/r14 reuse existing app thumbnails, not fresh renders; r14 is not a true same-paint before/after (preset previews can add their own colour/pattern).
- Sphere swatches are an illustration of the spec numbers, not iRacing's renderer.

## FINAL
34 of 34 figures built and looked at: g01-g20 (SVG, `data/encyclopedia/figures/`) and r01-r14 (WebP). Manifest `data/encyclopedia/figures.json`: ids exact, every file present, sources all `file:line`, renders <= 250 KB, total 1.5 MB. Rebuild: `python scripts/ai_atlas/enc_figs_svg.py` and `python scripts/ai_atlas/enc_figs_render.py [ids] [--force]`.
