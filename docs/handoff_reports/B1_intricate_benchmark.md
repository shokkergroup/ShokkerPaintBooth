# B1 - INTRICATE-ASKS benchmark (baseline, 2026-10-03)

Measurement only. 200 buyer/painter-voice asks that need a STACK (base + pattern + spec), a scale, a part binding, a negation, a like-but, a constraint, a question or an ask-back. Headless, free, deterministic (no LLM). Baseline = the code on disk at 2026-10-03 (offline advisor + `suggest_finishes` tool).

Files: `scripts/ai_atlas/intricate_asks.json` (asks + structured `expect`), `intricate_run.js`, `intricate_score.py`, builders `_easy_claude_work/eval/intricate_build_asks.py` and `intricate_report.py`, results `_easy_claude_work/eval/intricate_baseline.jsonl` + `intricate_baseline_score.json` + `intricate_baseline_table.txt`.

## Ask counts
ambiguous 10, constraint 20, like_but_stack 20, mood_stack 20, negated_stack 20, placement 22, question 22, scale 22, stack2 22, stack3 22

## Scorecard (mean per class; `-` = not applicable)
Path **offline** = what a buyer with no key gets (`classify` + `answer`); **tool** = `suggestTool({ask})` (what every AI tier calls); **any** = best of the two per metric.


**offline**

| class | base_hit | pattern_hit | spec_hit | stack_shape | scale_hit | parts_hit | must_not_ok | askback_ok | composite |
|---|---|---|---|---|---|---|---|---|---|
| ambiguous | 0.25 | 0.00 | - | 0.00 | - | - | - | 0.00 | 0.03 |
| constraint | 0.35 | 0.00 | 0.00 | 0.00 | 0.50 | 0.25 | 0.00 | - | 0.25 |
| like_but_stack | 0.85 | 0.00 | 0.00 | 0.00 | 0.00 | - | - | - | 0.28 |
| mood_stack | 0.25 | 0.00 | 0.00 | 0.12 | 1.00 | - | - | - | 0.16 |
| negated_stack | 0.15 | 0.00 | 0.00 | 0.05 | - | - | 0.16 | - | 0.09 |
| placement | 0.14 | 0.27 | 0.00 | 0.08 | - | 0.14 | - | - | 0.12 |
| question | 0.27 | 0.07 | 0.20 | 0.05 | - | 0.50 | - | - | 0.17 |
| scale | 0.32 | 0.23 | - | 0.31 | 0.14 | 0.00 | - | - | 0.25 |
| stack2 | 0.09 | 0.06 | 0.20 | 0.09 | 0.00 | - | - | - | 0.09 |
| stack3 | 0.05 | 0.00 | 0.00 | 0.05 | 0.50 | - | - | - | 0.03 |
| ALL | 0.27 | 0.06 | 0.04 | 0.07 | 0.21 | 0.19 | 0.15 | 0.00 | 0.15 |

**tool**

| class | base_hit | pattern_hit | spec_hit | stack_shape | scale_hit | parts_hit | must_not_ok | askback_ok | composite |
|---|---|---|---|---|---|---|---|---|---|
| ambiguous | 1.00 | 0.00 | - | 0.00 | - | - | - | 0.00 | 0.12 |
| constraint | 1.00 | 0.20 | 0.33 | 0.38 | 1.00 | 1.00 | 1.00 | - | 0.73 |
| like_but_stack | 1.00 | 0.25 | 0.50 | 0.50 | 0.67 | - | - | - | 0.61 |
| mood_stack | 1.00 | 0.38 | 0.25 | 0.65 | 1.00 | - | - | - | 0.73 |
| negated_stack | 0.95 | 0.17 | 0.50 | 0.40 | - | - | 0.68 | - | 0.55 |
| placement | 0.91 | 0.36 | 1.00 | 0.67 | - | 0.58 | - | - | 0.71 |
| question | 1.00 | 0.07 | 0.40 | 0.45 | - | 1.00 | - | - | 0.59 |
| scale | 1.00 | 0.15 | - | 0.23 | 0.50 | 1.00 | - | - | 0.60 |
| stack2 | 1.00 | 0.41 | 0.40 | 0.50 | 1.00 | - | - | - | 0.65 |
| stack3 | 0.95 | 0.18 | 0.27 | 0.00 | 1.00 | - | - | - | 0.37 |
| ALL | 0.98 | 0.23 | 0.36 | 0.40 | 0.64 | 0.70 | 0.70 | 0.00 | 0.59 |

**any**

| class | base_hit | pattern_hit | spec_hit | stack_shape | scale_hit | parts_hit | must_not_ok | askback_ok | composite |
|---|---|---|---|---|---|---|---|---|---|
| ambiguous | 1.00 | 0.00 | - | 0.00 | - | - | - | 0.00 | 0.12 |
| constraint | 1.00 | 0.20 | 0.33 | 0.38 | 1.00 | 1.00 | 1.00 | - | 0.73 |
| like_but_stack | 1.00 | 0.25 | 0.50 | 0.50 | 0.67 | - | - | - | 0.61 |
| mood_stack | 1.00 | 0.38 | 0.25 | 0.71 | 1.00 | - | - | - | 0.74 |
| negated_stack | 0.95 | 0.17 | 0.50 | 0.45 | - | - | 0.68 | - | 0.57 |
| placement | 0.95 | 0.45 | 1.00 | 0.67 | - | 0.58 | - | - | 0.73 |
| question | 1.00 | 0.13 | 0.40 | 0.45 | - | 1.00 | - | - | 0.61 |
| scale | 1.00 | 0.31 | - | 0.46 | 0.50 | 1.00 | - | - | 0.66 |
| stack2 | 1.00 | 0.47 | 0.40 | 0.50 | 1.00 | - | - | - | 0.67 |
| stack3 | 0.95 | 0.18 | 0.27 | 0.05 | 1.00 | - | - | - | 0.38 |
| ALL | 0.98 | 0.27 | 0.36 | 0.44 | 0.64 | 0.70 | 0.70 | 0.00 | 0.60 |

**Headline:** the offline advisor claims only **30%** of these asks; when it answers, only **11%** of ALL replies contain more than one layer kind (stack_shape offline **0.07**). The tool path returns several layer kinds for **98%** of asks but hits the expected layer-kind set for only **0.40** (stack_shape tool). Composite: offline 0.152, tool 0.589, any 0.605.

## Failure taxonomy (counts of the 200 asks; an ask can be in several)

- 139  A. Advisor does not claim the ask - the no-key buyer gets nothing
- 143  B. Stack ask answered with ONE layer kind offline (single finish / base only)
- 91  C. Stack ask: expected layer kinds missing on BOTH paths (tool returns lanes, but no pattern/spec matching the words)
- 94  D. Asked-for pattern family never returned (carbon, hex, camo, chevron ...)
- 36  E. Asked-for spec layer (flake, carbon, holographic ...) never returned
- 11  F. Scale words (fine / coarse / crushed %) ignored
- 13  G. Part binding lost or partial (hood + roof, numbers, stripes)
- 6  H. Negated attribute still returned (not-X items present)
- 13  I. Like-but loses the layer (reference found, added layer dropped)
- 10  J. Ambiguous ask answered without asking back

Note: the tool path never contains a question (askback 0.00 there) and its `texture` lane rows come from texture search on the sentence, not from the stack words; the offline advisor gives ONE lane set per reply and often no reply.

## 25 worst asks (by composite, any path)

| id | class | comp | ask | offline: claimed / keys | tool keys (top 4) | offline reply (120 chars) |
|---|---|---|---|---|---|---|
| ia191 | ambiguous | 0.00 | make it look cool | NO  | gloss, f_metallic, piano_black, factory_basecoat | (no reply) |
| ia193 | ambiguous | 0.00 | I want it like the one I saw last week | NO  | ms_zero_hour, eggshell, ffr_cyan_frond, last_lap | (no reply) |
| ia194 | ambiguous | 0.00 | make the car more interesting but not too much | yes matte_wrap, primer, ceramic_matte, f_brushed | matte_wrap, primer, ceramic_matte, black_flag | For the body: a few directions that work on an existing scheme. Your body is Gloss (high gloss). I searched the whole ca |
| ia196 | ambiguous | 0.00 | the usual but better | NO  | gloss, f_metallic, piano_black, gunmetal_satin | (no reply) |
| ia198 | ambiguous | 0.00 | fancy | NO  | silk, sparkle_diamond_dust, astra_quasicrystal_cro, piano_black | (no reply) |
| ia200 | ambiguous | 0.00 | make it pop but keep it subtle | yes matte, reactive_stealth_pop, living_matte, satin | matte, reactive_stealth_pop, living_matte, rad_bacterio_print | For your car: a few directions that work on an existing scheme. Your body is Gloss (high gloss). I searched the whole ca |
| ia023 | stack3 | 0.25 | matte black base, a carbon fibre pattern, and a sparkle spec layer | NO  | matte, f_carbon_fiber, multiscale_carbon_micr, carbon_raw | (no reply) |
| ia025 | stack3 | 0.25 | white pearl, with a subtle chevron pattern and a holographic spec pattern | NO  | pearl, f_pearl, wave_pearl_current, exotic_crystal_clear | (no reply) |
| ia027 | stack3 | 0.25 | red gloss, add a camo pattern and make the spec glittery | NO  | gloss, fire_engine, red_mist, mc_desert_camo | (no reply) |
| ia028 | stack3 | 0.25 | gold base, an art deco pattern, and a brushed metal spec pattern | NO  | f_brushed, satin_metal, art_deco_gold, vm_zapotec_thunder | (no reply) |
| ia031 | stack3 | 0.25 | orange paint, stripes pattern, and a carbon spec pattern | NO  | f_carbon_fiber, flm_chevron_herringbon, tac_carbon_handguard, multiscale_carbon_micr | (no reply) |
| ia034 | stack3 | 0.25 | satin white, a japanese wave pattern, and a pearl spec pattern | NO  | f_pearl, pearl, satin, wave_pearl_current | (no reply) |
| ia038 | stack3 | 0.25 | pink pearl, chain mail pattern over it, and a shimmer spec layer | NO  | pearl, f_pearl, fractal_pearl_cloud, spectrum_nacre_tide | (no reply) |
| ia041 | stack3 | 0.25 | cyan metallic base, dragon scale pattern, and a holographic spec layer | NO  | fsk_dragon_scale, fm_dragon_scale, fab_dragon_scale, metallic | (no reply) |
| ia042 | stack3 | 0.25 | burgundy base with a diamond plate pattern and glitter in the spec | NO  | fm_diamond_plate, fsk_diamond_plate, dkc_burgundy, ghost_diamonds | (no reply) |
| ia043 | stack3 | 0.25 | jet black base with aztec pattern and a gold flake spec pattern | NO  | fmo_chrysina_gold, cf_jungle_venom, cx_gold_green, cs_green_gold | (no reply) |
| ia044 | stack3 | 0.25 | chrome base, a hex pattern, and a matte spec layer to break it up | NO  | f_chrome, matte, chrome, halo_hex_chrome | (no reply) |
| ia048 | scale | 0.25 | huge broad stripes across the whole car | NO  | fcw_bronze_rivets, fnb_violet_billows, fnb_teal_annulus, pace_car_pearl | (no reply) |
| ia052 | scale | 0.25 | giant dragon scales, each one the size of a door panel | NO  | ghost_scales, ms_crimson_dragon, cf_dragon_scale, fc_hide_scale_glass | (no reply) |
| ia054 | scale | 0.25 | medium sized diamonds repeated evenly | NO  | sparkle_diamond_dust, gloss, ffo_diamond_knurl, mclaren_orange | (no reply) |
| ia064 | scale | 0.25 | medium wave pattern, not too busy and not too tiny | NO  | wave_candy_flow, reactive_pulse_metal, living_wave_tide, halo_wave_candy | (no reply) |
| ia121 | negated_stack | 0.25 | red car, stripes pattern, not too shiny, no candy | NO  | mc_red_marble, fire_engine, cc_blood_orange, rad_lacquer_cabinet | (no reply) |
| ia124 | negated_stack | 0.25 | green with a carbon layer, no metallic | NO  | multiscale_carbon_micr, f_carbon_fiber, necrotic, kevlar_red | (no reply) |
| ia128 | negated_stack | 0.25 | a diamond pattern on a blue car, not metallic | NO  | rad_grid_floor, lich_king, argyle_pastel, aramid | (no reply) |
| ia192 | ambiguous | 0.25 | something with a pattern and some shine | yes gloss, f_soft_gloss, fable_wovenlight, elm_frost_fern | f_neutral_grey, gloss_wrap, ceramic, eggshell | Here are the closest matches in the catalogue for “with pattern and glossy”, best first (swatches on your car's colour). |

## How to rerun and compare (later workers)
```
node scripts/ai_atlas/intricate_run.js after          # ~15 s, headless, no server; resumable (delete the jsonl to redo)
python scripts/ai_atlas/intricate_score.py after --compare baseline
```
Writes `_easy_claude_work/eval/intricate_after.jsonl` and `intricate_after_score.json`; prints the per-class table and a composite delta per class (any / offline / tool). Suggested gate: stack_shape (any) and pattern_hit / spec_hit up, no class composite down, `must_not_ok` and `base_hit` not below baseline. Re-run `python _easy_claude_work/eval/intricate_build_asks.py` only if the asks change (then re-run baseline too). Keep tag `baseline` frozen.

## What the scorer cannot judge
- Matching is by facet words (tags, shine, colour name, shelf, name/description tokens): generous for broad words like gloss / dark (so base_hit ~0.98 on the tool path is an upper bound), strict for pattern/spec (needs a returned `pattern::` / `spec::` item).
- Not scored: colour match, the picture, whether the reply TEXT explains the stack (only keys and a `?` are read), the designer path (`SpbProDesign.offlinePlan` / zone compile; needs state and zones), applied scale percentages (the advisor has no scale output, so scale_hit uses the returned items' fineness facet), and tool-path parts beyond its inferred `part`.
- ask_back counts only a `?` in the reply; the tool path has none by design.
- `expect` was hand-authored from the catalogue vocabulary; an item the author did not foresee can be right and still miss.
