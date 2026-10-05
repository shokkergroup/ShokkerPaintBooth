# "Change what is already on the car" - the copilot's edit brain (2026-10-02)

Owner: most buyers will NOT paint a car from nothing. They load a finished livery and say *"make the black matte"*, *"make the numbers purple and metallic"*, *"the yellow on the car, make it matte or powder-coat looking"*. The helpers (offline built-in and online AI / MCP) must **read what the paint really has** and **know the app's Bases / Specs** well enough to do that without a painter's vocabulary.

## What was built
| piece | where |
|---|---|
| Brain (parse + compile, no catalogue, no network) | `js/spb-pro-edit.js` -> `window.SpbProEdit` |
| Offline executor + routing + chips | `js/spb-pro-ai.js` (`editEnv`, `editPlan`, `offlineEditAsk`, `queueEditZones`; routed in `offlineAsk` BEFORE the finish advisor, in `offlineAskCore`, in `offlineCanHandle` and in `send()` so the support fallback never swallows an edit) |
| Online AI tools | `describe_paint` (read) + `refinish` (queue) in `makeTools`; system-prompt rule 16d |
| MCP | `spb_describe_paint`, `spb_refinish` (`mcp/server/tools.json`, `index.js` NAME_MAP / READ_ONLY / INSTRUCTIONS, `MAPT` + `MCP_WRITE` in ai.js) |
| Palette read | `Z.paintColours(n, mask)` (zone-kit) - `mask` = `SpbProCar.paintableMask()` so the template's dead-space backdrop is NOT reported as a livery colour (every iRacing template showed "brown ~20%": `#534741`) |

**One executor:** the offline parser and the online `refinish` tool both end in `compile()` / `compileRequest()` -> the same zone specs -> the same `queueEditZones` (add_zone / edit_zone). An AI call and a typed sentence produce identical zones.

## How a sentence is understood
1. `fixText`: lowercase, spoken spellings (powdercoated, plastidip, matt, metalic, glosy, crome ...), word typos, one-edit fuzz for long words (colour / look vocabulary), slang (da -> the).
2. Clauses: commas / `;` / `&` / "and / then / but / plus" split it. A clause with no target ("make it have a wet look", "and metallic") finishes the previous job; a target with no action takes the next clause's ("make the hood and the roof powder coat"). Two looks on one job: a known combination wins (matte + metallic = *matte metallic*), else the later one.
3. **Target** = a colour ON the car ("the black", "all the red", "the dark blue", "everything that is white", "the black on the hood") / numbers / sponsors (decals / logos layers) / stripes (a tape layer if there is one, else the one non-body colour, else ask) / main colour / a part / the whole car / "pop" (body flat, accents metallic). A colour word is a TARGET with a determiner ("the black"), before a noun ("black parts"), in "turn X into Y", or when the next clause shares a verb; otherwise it is the NEW colour ("make the numbers purple").
4. **Resolve** the spoken colour to the car's real colours by FAMILY (chroma-based: `#fffefe` is white, `#252525` is charcoal, `#141416` is black) + the exact name the helper itself reports; neutral neighbours (black/charcoal/grey/silver) are used silently; a different colour (pink -> red) is ASKED ("I do not see any pink... did you mean red?" with chips).
5. **Action**: look alone -> Foundation finish + `color:"source"` (the paint stays identical: measured); new colour -> repaint exactly those pixels (`base::gloss` unless a look is named); both -> Foundation finish + the colour; relative (glossier / duller / "a little") -> `f_soft_gloss` / `f_gel_coat` / `f_clear_satin` / `f_soft_matte`; darker / lighter / brighter / neon -> a recomputed hex of the colour that is there.
6. **Unknown look words** ("carbon fiber", "camo", "galaxy") go to the catalogue (`resolveLook`); if that fails the helper ASKS with chips, never guesses.

## Spoken look -> finish (client BASES only have 24 `f_*` ids; the rest are `spec_shift` variations)
powder coat `f_powder_coat` | wrinkle coat `f_powder_coat` +rough | plasti dip / rubberized / stealth `f_soft_matte` +rough +clearcoat | cerakote / primer `f_soft_matte` | matte `f_soft_matte` | satin `f_clear_satin` | gloss `f_soft_gloss` | wet look / ceramic / glassy `f_gel_coat` | chrome `f_chrome` | satin chrome `f_satin_chrome` | dark chrome `f_dark_chrome` | plated `f_chrome` | metallic `f_metallic` | matte metallic `f_matte_metallic` | pearl `f_pearl` | satin pearl `f_satin_pearl` | candy `f_candy` | brushed `f_brushed` | anodized `f_anodized` | frosted `f_frozen` | bead blasted / hammered `f_bead_blast` | vinyl wrap `f_vinyl_wrap` | enamel `f_baked_enamel` | patina / galvanized `f_matte_metallic` shifted. **`f_matte`, `f_wrinkle_coat`, `f_electroplate`, `f_shot_peen`, `f_patina`, `f_galvanized` exist in `/api/finish-data` but NOT in the client's `BASES` (validate says "unknown finish")**: check `SpbProZone.validate` for any new key (`_easy_claude_work/pw/t247_finish_valid.py`).

## Stacking
A second request about the SAME colour / layer edits the zone the helper made for it (`_editReg`, keyed by region). Without that, a new `color:"source"` zone on top would show the ORIGINAL paint again and drop the first change ("white purple", then "white glossier" -> white again).

## Tests (run after ANY edit to these files)
```
node _easy_claude_work/edit_corpus.js        # 173 phrases x 8 palettes (the owner's sentences, typos, slang, compound, asks, deferred-to-legacy) - 0 mismatches
node _easy_claude_work/edit_req_test.js      # the online refinish request compiler (17)
node _easy_claude_work/edit_test.js          # verbose listing of 77 phrases with their zones
python _easy_claude_work/pw/t246_edit_real.py arca,ram,f150,dlm,ram2   # real paints in the real app (offline helper), palette-derived sentences
python _easy_claude_work/pw/t248_edit_stack.py arca                    # stacking + real preview pixels
python _easy_claude_work/pw/t251_legacy_and_online.py both              # older handlers keep their sentences; 3 live DeepSeek prompts (~$0.005)
python _easy_claude_work/pw/t254_mcp_tools.py                           # the MCP entry points (describe_paint / refinish) in-page
node _easy_claude_work/convo_test.js ; node _easy_claude_work/tool_test.js ; node _easy_claude_work/l6/adversarial.cjs
```
Traps: bash heredocs turn `\b` into a literal 0x08 (two regexes were broken this way; `scan_ctrl.py`); `\b` after a lookahead group is redundant; HSL saturation is meaningless at the extremes (use chroma).

## Online AI and the picture critic
The model calls `describe_paint` then `refinish` (system rule 16d) and gets the SAME zones as the typed sentence. The post-apply vision critic used to read "make the black matte" as "make the body black" and a dark metallic purple as black, then undo correct work ($0.04 per false undo): it now carries an edit-request paragraph (judge matte / chrome in the SPEC MAP, only the named colour changes) and is skipped entirely when every queued change came through `refinish` (those are compiled and measured by the app). Priority: colour zones are placed BELOW the numbers / sponsors / stripes zones the helper made ("the numbers" is more specific than "the black"); layer zones in one request are added last.

## Part 2 (2026-10-03): conversation, exclusions, flat paints
- Done since this list was written: "except / but leave the numbers alone" (`region.exclude`), hue-shift recolours that keep the shading, follow-ups ("a bit more", "do the same for the roof"), options gallery, put-back, painter shorthand, hex colours, a misses log (`/api/ai/misses`).
- **Numbers / sponsors / stripes on a FLAT paint** (no layers): `docs/ELEMENT_FINDER.md`. The finder is only proven on truck sheets, so the app always asks first; an AI uses `look_at_paint` + `mark_elements` (boxes it reads off the picture).
- A bare "undo" is always the regular Undo (the planner used to read it as an unknown look for the last target).

## Not done / owner decisions
- Adaptive per-colour tolerance and soft-edge growth for fine glyphs (needs a trustworthy flat-paint preview to judge).
- Part-bound edits ("the hood powder coat") are not merged by `queueEditZones` (spec-only on spec-only is safe; spec-only over a recolour of the same part would show the original paint).
- The online path is covered by the same compiler and unit tests; a live DeepSeek run needs the owner's key and was kept small.

## 2026-10-03 afternoon sprint - what changed (details: `docs/handoff_reports/`)
- **Corpus 212 -> 409 phrases at 0 mismatches (WP7)** + two real parser bugs fixed (a part after an element word recoloured the whole part; five questions were executed as edits). Offline red team: 114 prompts, 0 OpenRouter calls.
- **Adaptive per-colour tolerance (WP6):** `SpbProZone.edgeFit` sets each colour's tolerance from its measured spread (+ shades and AA-ramp colours); probe rule now matches the engine's weighted RGB distance; thin-glyph halos -40..53%. A real soft edge needs an engine `edge_grow_px` / `edge_unmix` (spec in the WP6 report). Side effect: "red matte" can include a dark-red tail-light lens.
- **Stacks:** intricate-asks benchmark (`scripts/ai_atlas/intricate_*`, 200 asks) + stack planner in `js/spb-pro-advisor.js` (B2): offline composite 0.152 -> 0.536, tool 0.589 -> 0.761; the base layer carries an `adjust` block (colour / hue / saturation / brightness / spec_strength / scale) - "pink camo rattlesnake" -> Ghost Camo #ff7eb6 + Snake Skin 3 @40%. Designer compound orders -> real layer stacks (`SpbProDesign.compoundPlan`, C): 0/40 -> 40/40; the advisor yields to it on matching orders. App controls knowledge: `scripts/ai_atlas/app_controls.json` (35 controls, measured) + the knowledge chunk `docs/ai_knowledge/sliders_and_controls.md`. Measured trap: a SOLID base colour recolours a brings-its-own-colours item and flattens its texture - prefer the hue offset there.
- **Flat-preview bug fixed (WP4):** a flat TGA load never bumped `_spbLayerRev`, so the preview kept the previous car for 30 s; fixed in `paint-booth-3-canvas.js`; harness loader `pw/flatload.py`.
- **Deep cards:** every catalogue item has a `deep` card (`_atlas_deep/`), merged into the cards data and shipped through `finish_details` (`SpbAICards.deep(key)`).

