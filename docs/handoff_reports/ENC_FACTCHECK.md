# ENC_FACTCHECK - independent fact-check of the SPB Encyclopedia (2026-10-04)

Verdicts: `_easy_claude_work/eval/factcheck/verdicts.jsonl` (214 rows). Fix log: `fixes_applied.jsonl`. Sample ids: `sample_ids.json`.
Method: every concrete claim in a sampled article was checked against the cited source AND the current code (code wins). UI claims were checked in the HTML/JS and, for the picker, in the live app (test server 59879, picker DOM). Gates after all fixes: `enc_v2_test.js --final` 378 files / 6,128 articles PASS, `--depth` PASS, `enc_test.js` 27/27 GREEN.

## Error rate (before fix)
Sampled 171 articles (127 hand-written of the 240, 44 generated). An article counts as an error when any claim in it was wrong, a contradiction or unsourced; "vague" is counted separately.

| domain | sampled | with errors | vague only | error rate |
|---|---|---|---|---|
| ai_copilot | 5 | 1 | 0 | 20% |
| cars | 2 | 0 | 0 | 0% |
| concepts | 3 | 1 | 0 | 33% |
| controls (generated) | 6 | 1 | 1 | 17% |
| finish pages (generated) | 20 | 1 | 0 | 5% |
| finishes | 11 | 6 | 2 | 55% |
| help pages (generated) | 12 | 3 | 2 | 25% |
| history | 1 | 0 | 0 | 0% |
| layers | 6 | 0 | 0 | 0% |
| pattern pages (generated) | 3 | 0 | 0 | 0% |
| patterns | 4 | 0 | 0 | 0% |
| playbook | 10 | 3 | 0 | 30% |
| preview_render | 6 | 2 | 0 | 33% |
| recipes | 13 | 6 | 0 | 46% |
| settings | 2 | 0 | 1 | 0% |
| shokk_drop | 2 | 1 | 0 | 50% |
| shortcuts | 4 | 0 | 0 | 0% |
| spec | 15 | 14 | 0 | 93% |
| spec-pattern pages (generated) | 3 | 0 | 0 | 0% |
| spec_sculpt | 8 | 0 | 0 | 0% |
| support | 8 | 4 | 0 | 50% |
| tools | 6 | 0 | 0 | 0% |
| ui_shell | 9 | 0 | 1 | 0% |
| workflows | 4 | 0 | 0 | 0% |
| zones | 8 | 1 | 0 | 12% |

Hand-written: 39 of 127 = 30.7%. Generated: 5 of 44 sampled = 11.4%, but one generator defect (below) affects about a third of all 4,179 finish pages. All sampled errors are fixed (after: 0 known wrong claims in the sample, 7 vague items left, see "Left open").
Quality split: the newer code-derived domains (ui_shell, zones, layers, tools, spec_sculpt, patterns, workflows, history, shortcuts) were 0-12% wrong. The errors sit in the older concept-level domains (spec 93%, finishes 55%, support 50%, recipes 46%, preview_render, playbook).

## Top error patterns
1. **Finishes that are not in the picker were documented as pickable (generated, systematic).** 1,364 of 4,179 finish pages (More Bases 371 of 449, More Specials 982 of 1,158, Wave & Flow 10, ALL THAT 1) told the reader to open the Base Material picker and search for a finish that the live picker does not list (verified in the running app: picker holds 2,762 ids; `paint-booth-2-state-zones.js:5926` removed the "Other Bases" bucket; specials likewise). "More Bases / More Specials" are not shelves in Pro (the names come from the hidden Easy mode and the AI atlas).
2. **Retired Foundation names and numbers shown as live** (Soft Matte, Clear Satin, Gel Coat, Soft Gloss, stale numbers 165/158/75): spec, recipes, finishes, support, help.
3. **Wrong UI names or places:** "expand the SPEC sliders section" (it is Spec Sliders in the BASE section), Independent Spec gating (it only gates Spec Scale; rotation is always live), Spec Tools menu, Lock box, ASTRA shelf, Chrome label, Shokk Drop file types (also TGA and BMP).
4. **Ranges that do not match the UI:** Base/Spec Strength 0-200 (UI 0-100), a non-existent Intensity slider ("intensity 0 hides the zone"), Color Depth default (reads "off", first touch turns it on at 65).
5. **Stale facts after concurrent changes by other workers:** Spec Feels coat signs, zone limit 16 -> about 20 (decode budget now 1 GiB), render-button gate, palette count 74 -> 75, "jump back several steps" in Undo History (rows are read-only).
6. **Counts that contradicted each other:** "about 4,800 finishes" vs 4,179 (4,799 counts patterns and spec patterns).
7. Generator text bugs: 7 control titles were HTML attribute fragments; one help summary was cut mid-sentence ("... and the."); the "Satin" claim for Clear Satin; the Finish Law article said the sameness check is a gate (it is advisory) and that green means original.
8. Examples whose settings would not give the stated result (Spec Feels, Satin Matte), and recipes citing `ui_map.json` ids instead of code lines (sources added).

## Fixes made (right layer)
- Hand-written JSON: spec (10 articles), recipes (13), finishes (5), support (3), playbook (2), zones, preview_render, ui_shell, settings, shokk_drop, concepts, ai_copilot, tools, shortcuts; global replaces (Foundation Bases wording, Chrome label, retired-name map, zone limit).
- Generators: `scripts/ai_atlas/enc_gen_B.py` (NOT_IN_PICKER branch reading new `scripts/ai_atlas/enc_picker_hidden.json`: those pages now say the finish is not in the picker and to ask the Shokker AI helper for it by name; the two stray `ui_*` user-import patterns are no longer given pages), `enc_gen_A.py` (LABEL_FIX for 7 control titles), `enc_gen_C2.py` (no mid-sentence summary cuts), `encyclopedia_recipes.py`, `ui_map.json` and `enc_inventory.json` (Clear Satin, "jump back" wording). All affected page sets regenerated; index rebuilt (`build_encyclopedia.py`).
- App strings that fed the encyclopedia and the helper: `js/spb-support-answers.js`, `js/spb-support.js` (zone limit), `js/spb-self-help.js` (retired ids, Undo wording), `js/spb-ai-knowledge.js`, `js/spb-pro-ai.js` (one string: "more than 70" themes). Cache tokens bumped in `paint-booth-v2.html` for self-help, ai-knowledge, support-answers, encyclopedia-data.

## Left open / systematic risks for unsampled data
- **Source line drift:** about 253 of 838 control pages cite a file:line that is 3-40 lines off (paint-booth-v2.html moves as other workers edit it); 309 more could not be matched by id. The text is right, the line is stale. Needs a line re-anchor step in the gate (not done: files are in flux).
- `finish_more_bases` / `finish_more_specials` still carry the shelf label "More Bases/Specials" in the reader (the claim text is now honest, the label is Easy-mode vocabulary).
- **Atlas data leak:** `js/spb-ai-atlas-data.js` and `js/spb-ai-cards-data.js` ship two of the dev machine's own Shokk Drop imports (`ui_krak_2`, `ui_x_1862`); pages are removed, the data is not.
- `base::semi_gloss` page says measured coat 16 / roughness 60 but the registry pins 0/55/40 (`engine/base_registry_data.py:397`); 19 of 20 pure Foundation bases match, this one does not (atlas measurement is stale or the render path differs). Not changed, needs an engine owner.
- `js/spb-pro-advisor.js` (lines 760-832) still recommends retired ids (`base::f_gel_coat`, `f_soft_matte`, `f_clear_satin`, `f_soft_gloss`); they resolve but are not in the picker.
- Known open app bug (not documented as intended): `apply_wear` clamps clearcoat to 16 (another worker is fixing it).
- Files edited are untracked in git and mirrored under `electron-app/server/`; mirror sync deferred (use `--manifest` syncs only; other Codex lanes are editing `js/spb-pro-ai.js` and `paint-booth-v2.html`).
- Sampled articles with a "vague" verdict left as is: settings.looks_training_wheels (control default now "off"), help_topics_1.undo, help_howto_3.spec_sculpt (WHAT is a tooltip), a few others in verdicts.jsonl.

## ROUND 2 (2026-10-04, same worker, no sub-agents)

Scope: every remaining hand-written article in 12 domains, read against code and fixed at the right layer (generator for generated pages, direct edit for hand-written pages). 73 articles checked (verdict log: `_easy_claude_work/eval/factcheck/verdicts.jsonl`, tools in the same folder).

### Error rate per domain (articles with at least one wrong / contradicted / unsourced claim, before the fix)
| domain | checked | with errors | rate |
|---|---|---|---|
| spec | 7 | 3 | 43% |
| finishes | 10 | 4 | 40% |
| recipes | 14 | 3 | 21% |
| ai_copilot | 6 | 1 | 17% |
| support | 7 | 0 | 0% |
| workflows | 6 | 0 | 0% |
| playbook | 6 | 0 | 0% |
| preview_render | 7 | 0 | 0% |
| settings | 2 | 0 | 0% |
| cars | 3 | 0 | 0% |
| concepts | 2 | 0 | 0% |
| shokk_drop | 3 | 0 | 0% |
| total | 73 | 11 | 15% |

Round 1 sampled the riskiest pages (25.7% with errors). Round 2 covers the rest and is cleaner, but spec and finishes still carry the stale-fact risk.

### What was wrong and is now fixed
- Counts: 4,755 finishes / 4,137 / 2,993 / 317 patterns corrected in spec, finishes, patterns and shortcuts pages (and their generator drafts).
- ColorShoxx / Atmosphere / Aurora Flow retirement wording (ColorShoxx is off the shelves, 78 cx_ ids are picker-hidden, WORLD OF COLOR replaced it).
- Angle Reveal removed from the colour-shift recipe; Strength-vs-opacity wording (the spec overlay slider is "Strength"); new-zone order (+ Add Zone appends at the bottom; lower index wins overlaps).
- MCP tool list in ai_copilot (about 27 tools, counts).
- `base::semi_gloss`: the page now states the registry pin (0 / 55 / 40), fixed in `enc_gen_B.py` via `enc_foundation_pinned.json`.
- Bugfix-lane behaviour (code is truth, `BUGFIX_2026-10-04.md`): B COAT direction unchanged, 4 Spec Feels flipped, wear now dulls the clearcoat, Layer Blend / Strength Map / Spec Sculpt Showroom / split mix are live. Updated: controls_spec_1.zone.b_coat, help_howto_1.gloss_level, spec.presets_feels, finishes.wear, controls_bases_1.zone.wear, controls_zones_1.pro.zones.quick_wear_ramp, recipes.weathered, spec_sculpt Fusion text, plus the self-help / ai-knowledge / app_map sources of the B COAT phrase.
- `js/spb-pro-advisor.js`: retired finish ids replaced (cache tokens bumped: advisor `20261004fc2`).
- Shokk Drop dev imports: the maintainer's 44 `*::ui_*` items (including `ui_krak_2`, `ui_x_1862`) came from `dump_catalog.py` dumping the running app. Fixed at the source (`dump_catalog.py` filter, `enc_gen_B.py` exclusion), purged from `js/spb-ai-atlas-data.js`, `spb-ai-cards-data.js`, `spb-lsa-data.js`, with a guard script `scripts/ai_atlas/purge_user_imports.py --check`.

### Source-line anchors
- `scripts/ai_atlas/enc_source_anchors.py` + sidecar `enc_source_anchors.json` (2,321 cited `file:line` keys, each with distinctive anchor text). `--repair` relocates a drifted line by its anchor and rewrites every article and the sidecar; it fails only when the anchor is gone from the file.
- Wired into `build_encyclopedia.py` (build then repair) and into the gate `_easy_claude_work/enc_v2_test.js` (prints `ANCHORS PASS/FAIL`).
- First run repaired the drifting control pages (about 1,000 line moves), found 1 genuinely gone anchor (a version hash in the generated data blob, re-anchored to a stable `window.X =` head), plus 1 re-anchored code line.
- Limitation: for hand-written sources the anchor is the line text at build time, so a citation that had already drifted before the build was anchored to the wrong text only if its line text was not distinctive; control pages (the bulk) use inventory id / label anchors.

### Gates at the end
`enc_v2_test.js --final` 376 files / 6,086 articles PASS, ANCHORS PASS (2,321 ok / 0 gone), `--depth` PASS, `enc_test.js` 27/27, `enc_reader_smoke.js` 128/128. Regression after the advisor / atlas purge: `convo_test.js` 52/52, `builder_test.js` 136/136. Not rerun: the `adv_test` harness (needs prompt fixtures).

### Not done / open
- Nothing synced to `electron-app/server/` (release sync later, via `--manifest` only; Codex lanes are editing `js/spb-pro-ai.js` and `paint-booth-v2.html`).
- Vague verdicts left as is (settings.looks_training_wheels, help_topics_1.undo, help_howto_3.spec_sculpt).
- Wear noise looks blobby (pre-existing, owner look).


## ROUND 3 (2026-10-04, same worker, no sub-agents)

Scope: the ~40 hand-written articles rounds 1 and 2 had not covered (zones, layers, patterns, shortcuts, spec_sculpt, tools, ui_shell, plus `patterns.nine_groups` and the late find `tools.refine_selection`). 1,376 individual claims checked against code/data with file:line. Verdicts: `_easy_claude_work/factcheck3/verdicts.jsonl`.

**Result: 17 of 39 articles (44%) had at least one error; all fixed.** Higher than round 2 because these are the hand-written, behaviour-heavy pages (zones, layers, spec sculpt, UI shell) that describe how controls act.

### Errors found and fixed (claim -> truth -> source)
| Article | Claim | Truth | Source |
|---|---|---|---|
| zones.priority | New zones go on top | + Add Zone appends at the bottom; only the Chat/AI kit puts new zones on top | paint-booth-2-state-zones.js:4269; js/spb-pro-zone-kit.js:47 |
| zones.priority | List order is the only priority | Scoped Include marks carry a priority_override exception | paint-booth-3-canvas.js:2119; engine 18413, 18585 |
| zones.card_controls | Rand All Zones clears pattern stacks; new zones on top; Reset Zone is instant | Stacks are kept; new zones at bottom; Reset Zone asks for confirmation | paint-booth-6-ui-boot.js:2133-2200; js/zones/workflow-controls.js:439 |
| zones.regions | Alt+Arrow nudges the region | Arrow = 1 px, Shift+Arrow = 10 px, only with Move Selection Border armed | paint-booth-3-canvas.js:5122, 34533-34553 |
| zones.popout_panel | Lists a SPEC SOURCE row | Row no longer exists | paint-booth-2-state-zones.js:1821 |
| layers.roles | Stacking order of an ARCA template presented as general | Late-model template order differs | spec-sculpt / layer role tables |
| layers.open_psd | Picker title text; restore is silent | Restore first asks "Restore them?" | paint-booth-3-canvas.js:21621, 22272 |
| layers.turn_off_before_export | Car_Mandatory is exported | Car_Mandatory is a template layer to switch off | js/spb-support.js:132, 261 |
| patterns.what_is_a_pattern / nine_groups | 319 patterns; label wording | 317 listed in 9 groups; label is "Pattern 1 on this Layer/Zone" | pattern picker data |
| shortcuts.table | Alt+Arrow nudges 1 px (5 with Shift) | Alt+Arrow only works with Move Selection Border armed and otherwise just toasts; Arrow/Shift+Arrow nudge 1/10 px | paint-booth-6-ui-boot.js (Alt handler); canvas.js:34533 |
| tools.refine_selection | Alt+Arrow nudges 1 px (5 with Shift) | Same as above (found by a corpus-wide Alt+Arrow scan after the list was done) | paint-booth-3-canvas.js:5122, 34533-34553 |
| spec_sculpt.what_is_spec_sculpt | How the lab opens; 10 jobs kept | SPEC SCULPT button opens the guided look library; the full lab is behind "OPEN ORIGINAL SPEC SCULPT"; 12 jobs kept | js/features/spb-easy-sculpt.js:3411, 3613; server.py:1300 |
| spec_sculpt.paint_response / recipes | Paint response makes clearcoat "rise" | Gain on channel 2 makes the coat duller (higher B = duller), clamped 0.52..1.62 | engine/spec_sculpt/generate.py:144-148 |
| tools.selection_modes | Pen supports Shift add / Alt subtract | Pen path-to-selection follows only the Selection Mode dropdown; Shift = 45 deg snap, Alt = break handles | paint-booth-3-canvas.js |
| tools.shortcuts_quick (FAQ) | Overlay lists I / S / G | It does not | paint-booth-6-ui-boot.js:4682 (F1) |
| ui_shell.template_layer_views | Flat TGA can be split with the smart tools | Smart Separate scripts are not loaded; flat TGA says NO LAYERS ... Import PSD | paint-booth-v2.html:4728-4731 |
| ui_shell.top_bar_buttons | SPEC SCULPT opens a separate window | It opens the guided library; only Shokk Drop opens a separate window | js/features/spb-easy-sculpt.js:3411 |
| ui_shell.render_results_panel | Missing car folder / template layers block rendering | Render refuses only for: no paint, User ID not 4-7 digits, no zone with colour + finish | paint-booth-5-api-render.js:3483-3526 |

Also removed the self-referential source `data/encyclopedia/tools.json:1` from recipes.mirror_side and workflows.one_flat_sheet (and the stale sidecar key), which had turned into a GONE anchor.

### Clean (0 errors)
shortcuts.glossary, spec_sculpt.smart_separate, spec_sculpt.diagnostics, tools.fill_bucket, tools.eyedropper_pick, tools.retouch, tools.mask_vs_layer, tools.move_transform, ui_shell.mode_pill, panels_and_ui_size, car_folder, number_modes, selection_bar, save_open_projects, patterns.paint_mode, plus the remaining items in the todo list.

### Generator fixes (so a rebuild does not regress)
`scripts/ai_atlas/enc_gen_A.py`, `scripts/ai_atlas/enc_B_part9.py`, `scripts/ai_atlas/enc_B_v3_spec_sculpt.py`, `_easy_claude_work/encA/deep/r16.py`, `_easy_claude_work/encA/part2a.py`, `_easy_claude_work/encA/part2b.py`. Hand-written pages were edited in `data/encyclopedia/*.json` (zones, layers, patterns, shortcuts, spec_sculpt, tools, ui_shell, recipes, workflows).

### Gates at the end
`enc_v2_test.js --final` 376 files / 6,086 articles PASS; ANCHORS PASS (2,348 ok / 0 gone / 0 cited-without-anchor); `--depth` PASS; `enc_test.js` 27/27 GREEN; `purge_user_imports.py --check` removed 0. Easy-mode mentions: 0.

### Left open
- The hidden header control's aria-label "Choose Pro or Easy view" is in the app (not the encyclopedia); changing it needs an app edit.
- The old canvas.js shortcut legend still lists retired keys (shadowed at runtime); app-side, not touched.
- Nothing synced to `electron-app/server/`; the encyclopedia data syncs with the next release sync.
- Error rates by round: 25.7% -> 15% -> 44%. Round 3 is higher because its pool is the behaviour-heavy hand-written set; the 6,000+ generated pages are protected by the source-anchor gate, not claim-by-claim review.

## ROUND 4 (ideas.json)

Scope: `data/encyclopedia/ideas.json`, the 70 new style-recipe articles (ideas.*). Worker, no sub-agents. Verdict log: `_easy_claude_work/factcheck_ideas/verdicts.jsonl` (one row per article).

Checked: 70 articles, about 1,419 claims (ids, spec numbers, UI labels, hexes, look/contrast claims). Articles with at least one error: 44/70 = 63%. Errors fixed: 153 edits (97 distinct wrong claims, the rest are follow-on title/result edits of the same claim). All 70 are now clean.

Passed with 0 errors: every finish/pattern/spec id exists and is picker-visible (`enc_ideas.py check` 70 articles, 0 bad ids); all R/G/B numbers match `base_registry_data.py` (Candy 200/15/16, Matte 0/200/160, Satin 0/95/70, Gloss 0/30/16, Wet Look 0/15/16, Chrome 255/2/16, Dark Chrome 250/15/40, Satin Chrome 250/45/40, Metallic 200/50/16); all uppercase UI labels are real; colour hexes match their names; the pop/contrast doctrine (complementary neighbours + shine contrast) is stated correctly; no brand names or logos are used as instructions (Gulf / Martini appear only as buyer words and the titles are generic).

### Error classes found

| Class | Count | Example | Truth source |
|---|---|---|---|
| finish/pattern look contradicted by the render card | 133 | ideas.aggressive_mean: Chevron Stack gives sharp points | deep render card (_dumpB.json) pattern::chevron_stack, patte |
| spec overlay promised a colour/visible look (shine only) | 10 | ideas.look_expensive: Gold Flake overlay gives a gold shimmer | deep render card (_dumpB.json) spec gold_flake |
| wrong control name/range | 6 | ideas.look_expensive: G ROUGH view shows 'dark greens' | ui_audit R METAL/G ROUGH/B COAT labels |
| zone order not stated (new zones go to the BOTTOM) | 2 | ideas.make_it_pop: hero zone wins by being above the matte zone, without saying where a new zone la | ui_map zone list + ENC_FACTCHECK R1-3 |
| wrong clearcoat direction | 1 | ideas.worn_patina: 'coat down' for wear | MEMORY spec map; base_registry efx_sun_faded |
| retired foundation name | 1 | ideas.retro_70s: 'Soft Gloss' foundation | picker VIS / enc_ideas find |

### Errors by article (claim -> truth)

- **ideas.make_it_pop**: hero zone wins by being above the matte zone, without saying where a n -> + Add Zone appends to the bottom; higher in the list (lower index) wins
- **ideas.aggressive_mean**: Chevron Stack gives sharp points -> Chevron Stack renders as fine horizontal pinstripes; the chevrons vanish. Chevron renders ; same -> same; Razor Wire = sharp lines -> Razor Wire renders as wavy wire strands, barbs vanish
- **ideas.look_expensive**: Gold Flake overlay gives a gold shimmer -> Gold Flake spec overlay renders as a smooth sheen with a slight sandy shimmer; nothing loo; same -> same; G ROUGH view shows 'dark greens' -> The channel preview is a greyscale-style channel view; no green is promised
- **ideas.look_fast**: Lightning pattern gives speed bolts; control called Rotation -> Lightning renders as hairline scratches (nothing readable as lightning); the control is Ro; same -> same; Chevron makes arrow shapes pointing at the nose -> Chevron renders as horizontal zigzag rows of Vs, not big arrows; Pinstripe = fine lengthwise lines -> Pinstripe card renders as a busy upright streak texture; direction depends on Rotate (patt; Lightning example -> Lightning pattern is hairline scratches; same -> same; same -> same; panels are mirrored on the flat sheet -> Unverified claim; direction must be checked on the CAR view
- **ideas.candy_lowrider**: Gold Flake gives gold sparkle -> Gold Flake spec overlay: smooth sheen, slight sandy shimmer, nothing looks gold; same -> same; Gothic Scroll gives scrolled hood panel -> no scrolls survive in the Gothic Scroll render; same -> same; same -> same; same -> same; Pinstripe is a crisp line -> renders as a busy upright streak texture
- **ideas.worn_patina**: 'coat down' for wear -> B coat: 16 = max gloss, higher = duller; worn paint has a HIGHER coat value (Sun Faded 137; same -> same; Surface Rust = orange bloom and dark scabs -> Surface Rust renders as a polka-dot spread of orange rust spots
- **ideas.rat_rod**: Pinstripe = a clean line -> renders as a flickery streak texture
- **ideas.retro_70s**: 'Soft Gloss' foundation -> No Soft Gloss in the picker; Gloss is roughness 30; pattern looks -> both render as busy plaid, not clean zigzag shapes; zigzag skirt -> Funk Zigzag reads as orange-brown plaid with wavy lines
- **ideas.retro_60s**: Mod Color Block = Mondrian-style blocks -> Mod Color Block (decade_60s_gogo_check) renders as a busy multi-colour pixel/tile mosaic; same -> same; Sunburst = radiating rainbow -> 60s Sunburst renders as dark red-brown with a polka dot of orange-gold; the rays vanish; same -> same
- **ideas.retro_80s**: Neon Grid = a grid -> renders as fine plaid / graph-paper shimmer, lines merge into neon static; same -> same
- **ideas.retro_90s**: Geo Minimal = minimal shapes -> Geo Minimal renders as dense tiny confetti dots; shapes vanish
- **ideas.vintage_diner_50s**: black and white check -> Diner Checkerboard finish renders as red-and-cream gingham; same -> same
- **ideas.gulf_style**: Pinstripe = a thin line -> renders as flickery streaks
- **ideas.hot_rod_kustom**: Pinstripe = hand-lettered thin lines -> renders as a flickery streak texture; same -> same; Hot Rod Flames = licks -> reads as heat shimmer or blazing embers over the whole panel; title mentions scallops not in settings -> settings have no scallops
- **ideas.jdm**: wave motifs read as clear waves -> Seigaiha = soft corrugated ripple; Japanese Wave = scaly mesh with flecks; Import Royalty = razor-vinyl slashes with prismatic edges -> renders as loud neon pink/purple/blue crossing ribbons on black; Rising Sun Flare vague lacquer texture -> renders as dark red-maroon with an orange sun and golden rays (a picture finish)
- **ideas.drift_car**: Exhaust Soot Gradient adds soot -> renders as nothing at distance, at most a watery shimmer; it changes shine only; sooty edges from the spec overlay -> spec overlay is shine only; heat marks -> renders as a clean sheen with light glittery dust
- **ideas.rally**: Red Clay Roost / Dried Mud Crackle give dusty mud -> both render as plain base finish; no red or brown appears, shine only; dusty lower panels from overlay -> overlay is shine only; cracked mud visible -> Dried Mud Crackle is gone at distance, a trace of mottling
- **ideas.touring_car**: a box can be rotated with the Chevron pattern -> a Draw box has no rotation; Chevron is a pattern with its own Rotate (pattern); same -> same; Chevron = notched arrows pointing forward -> renders as horizontal zigzag rows of Vs
- **ideas.black_gold_luxury**: Gold Flake glitters gold -> smooth sheen with slight sandy shimmer, nothing looks gold; Cs Black Gold = black that warms to gold -> Cs Black Gold renders as a vivid teal and purple marble; same -> Black Gold (gradient) renders black-to-gold; same -> same
- **ideas.racing_stripes**: Pinstripe = fine lengthwise line -> renders as a busy upright streak texture; stripes above body zone, without saying new zones start at the bottom -> + Add Zone appends to the bottom; higher in the list wins
- **ideas.checkered_flag**: same -> renders as a fine checker that merges to mid-grey at distance; checker appears in reflections -> renders as a faint gingham shimmer, no flag read
- **ideas.speed_lines_motion**: bolts -> Lightning pattern renders as hairline scratches; Zigzag Bands / Lightning make speed streaks; control called Rotation -> Zigzag Bands = brown/cream stepped basket bands; Lightning = hairline scratches; control i; Rollerblade Streak = streaks fading to the rear -> renders as 90s Memphis zigzag bands and dots; bolts / control called 'Rotation' -> Lightning = hairline scratches; label is Rotate (pattern)
- **ideas.cyberpunk_synthwave**: Neon Grid = crisp grid -> renders as fine plaid / graph-paper shimmer, neon static; same -> same; same -> renders as purple lenses with lime ribbons
- **ideas.high_vis**: Blaze Orange finish = fluorescent safety orange -> renders as dark brown with orange sparks, not solid safety orange; same -> same; Blaze Orange finish example -> replaced by a plain Gloss orange; same -> same; Wasp Signal = yellow and black chevron plates -> renders as dark golden-brown amber with fine black stipple; Retroreflective gives a visible glint -> renders as a dry sandy sheen, no colour of its own
- **ideas.fade_gradient**: Arctic Dawn = pale blue to white -> renders as icy cyan marbled mosaic
- **ideas.camo_woodland_desert**: same -> renders dark brown with tan spots
- **ideas.camo_digital_urban**: same -> renders as mid-light grey-white frosty speckle
- **ideas.police_emergency**: yellow-black chevrons; typo 'cuticle' -> Wasp Signal renders as amber with black stipple
- **ideas.flames**: licks -> Hot Rod Flames reads as heat shimmer / embers over the panel; same -> same; blue flames on a white body -> Blue Flame is sparse glowing blue orbs on black; it needs a dark ground; same -> same
- **ideas.tribal**: tribal patterns paint bold swirls/spikes -> Tribal Tattoo = scratchy multicolour confetti; Celtic Spiral = dotted green-purple wallpap; same -> same; Tribal Tattoo = thick black swirls -> renders as fine scratchy multicolour confetti; Celtic Spiral = knotwork -> spirals shrink to a polka-dot texture; same -> Tribal Flame renders as bold red/black camo-like fire shapes with yellow edge glow
- **ideas.geometric**: Chevron Stack = arrows -> Chevron Stack renders as fine horizontal pinstripes; arrows pointing forward -> Chevron renders as horizontal zigzag rows of Vs; same -> same; Argyle = diamond pattern -> reads as a soft purple-green harlequin check, no strong contrast; all listed patterns read as crisp flat shapes -> Houndstooth = busy confetti, Star Tile Mosaic = speckle, Art Deco Chevron = mottled grey
- **ideas.hex_tech**: Hex Mesh / Hex Circuit give clean honeycombs and traces -> Hex Mesh = multicolour confetti with no mesh; Hex Circuit = dense static, no structure; same -> same; same -> same; same -> same; same -> Graphene Hex renders as a fine jewel-toned hex-ring dot grid; Hex Circuit = cyan circuit traces -> renders as dense multicolour static, no traces; same -> same; same -> Hex Carbon renders as a soft muted hex-dot pattern, strokes gone; same -> same; Hex Circuit = circuits -> renders as static; summary lists Hex Mesh / Hex Circuit as good hex looks -> both render as busy multicolour static
- **ideas.marble_stone**: Marble Veining = stone veins -> renders as rippled striped fabric in muted purple, teal, pink; same -> same; Marble Veining pale veins on black -> pattern has no visible stone veins; same -> same; same -> Ebru Marble renders as a purple and black marbled car; Moonstone = blue-white glow over silver -> renders as cool blue-grey cracked crystal with blue-violet edges; same -> same; Marble Veining pattern draws stone veins (summary/faq) -> renders as rippled drapery stripes
- **ideas.holographic_iridescent**: Holo Flake brings its own colours -> renders as a sparkling dust that tints with pink-white twinkle; the real colour is what is; mirror finish with rainbow flake -> see how[1]; thin-film rainbow -> renders as a smooth oily sheen with faint wavering shimmer
- **ideas.colour_shift**: Cs Black Gold for black-gold -> renders as teal/purple marbled swirl; Color Flip range 0 to 100 -> Color Flip: 0 = off, 90 = neighbour, 180 = opposite; only on finishes that support it; same -> same; Chameleon Neon = green yellow pink -> renders as black with faint neon-cyan crackle; same -> same
- **ideas.pastel**: pink and teal grid -> renders pink with aqua and yellow Memphis shapes; diamonds -> renders as cream with confetti-and-net texture
- **ideas.metal_flake_sparkle**: gold sparkle -> Gold Flake renders as smooth sheen, nothing looks gold; rainbow sparkle -> Holographic Flake renders as a sparkly grainy sheen
- **ideas.glass_crystal**: same -> renders as saturated stained-glass confetti; ice dendrites -> renders as navy blue with snowy starfield; same -> same
- **ideas.space_galaxy**: Stardust pattern makes stars -> renders as a deep navy woven fabric with faint purple haze; same -> same; same -> same; Nebula = magenta and cyan -> renders purple/lilac on indigo, no cyan visible; same -> same; spiral of sparkle -> renders as a soft wavy ripple / fine scroll sheen
- **ideas.dragon_snake_scales**: same -> see cards; Duality Scales / Dragon Ascent = scale looks -> Duality = clashing two-colour patchwork; Dragon Ascent = dragon-in-flames illustration; overlapping dark red scales -> Dragon Scale renders as a mottled hide with a few soft ovals; Snake Skin 3 = green reptile skin -> Snake Skin 3 is warm brown-gold brocade; Snake Skin is olive-green scales; same -> same; same -> MS Dragon Ascent renders as a dragon-in-flames illustration
- **ideas.patriotic_rwb**: star flecks -> renders as navy streaked red and white; black field -> renders royal blue-violet; weathered flag -> renders as flat grainy muted red
- **ideas.japanese_art**: clear waves -> Japanese Wave renders as a fish-scale mesh with colour flecks; same -> renders as a pastel Fuji landscape; same -> renders as red/black/silver diagonal stripes with a sunburst; cool white lacquer -> renders as a dragon hero picture
- **ideas.surf_beach_summer**: same -> renders as aqua ripples with white crests; same -> renders as pale cream with faint speckle
- **ideas.punk_grunge_street**: splatter in a picked colour #ff2bd6 / #d7ff00 -> Overlay paints own colours; Grunge Splatter renders as dark maroon/charcoal digital camo, ; same -> same; lime splatter -> see how[2]; faded clearcoat patches -> Die-Back Patina renders as dusty aged earth-tone paint

Clean (0 errors): clean_classy, stand_out_in_pack, readable_on_tv, stealth_murdered_out, look_wet, satin_modern_oem, chrome_show_car, martini_style, old_school_muscle, le_mans_endurance, oval_stock_car, neon_night, fighter_jet, military_tactical, two_tone, camo_ghost_blackout, carbon_race_bare, monochrome, pearl_white, liquid_metal, matte_chrome_accents, racing_green_heritage, team_colours, numbers_match_body, sponsor_friendly_bases, style_menu

### Generator fix
`scripts/ai_atlas/enc_ideas_fix_r4.py` re-applies every text fix (idempotent: second run changes nothing); run it after `enc_ideas_build.py`. The b01..b07 generator files were not edited.

### Gates at the end
`enc_v2_test.js --final` 379 files / 6,164 articles all PASS (ANCHORS PASS); `--depth` all PASS; `enc_test.js` 27/27 GREEN; `enc_ideas.py check` 70 articles, 0 bad ids. Rebuilt `js/spb-encyclopedia-data.js`, copied to `electron-app/server/js/`, `?v=` bumped to `20261005fc4` in both `paint-booth-v2.html` copies (targeted sed).

### Notes / left open
- Several render cards describe the preview-tinted thumbnail, so a few looks (Snake Skin 3, Dragon Scale colour) depend on Blend vs Overlay on the car; the recipes now say so and send the reader to the CAR view.
- The Pinstripe pattern card reads as a busy upright streak while the engine code draws horizontal lines; the recipes now call it a fine stripe texture and tell the reader to set Rotate (pattern) and check the CAR view. A truth check by the owner on a real car would settle it.
- `ui_labels.json` named in the task does not exist; used `_easy_claude_work/ui_audit/labels.json`, the sweep rows and `scripts/ai_atlas/ui_map.json`.

## ROUND 5 (search-lab articles)

Checked the 8 articles the search-lab worker added on 2026-10-05 against code, data and render cards. All 8 needed fixes (about 47 sentence-level edits). Verdicts: `_easy_claude_work/factcheck_lab/verdicts.jsonl` (round 5).

| Article | Main error found -> fix |
|---|---|
| recipes.named_looks | **Every named finish (Tri-Coat Pearl, Forged Carbon Visible, Forged Composite, Anodized, Blackout, Blackout Ops, Rally Mud) is picker-hidden** (`enc_picker_hidden.json`), so "search the finish picker" was false. Foundation Anodized (`f_anodized`) is retired and redirects to `f_brushed` (`base_registry_data.py:1623`). Rewritten to "ask the AI panel by name", with the picker-visible nearest finishes listed. |
| support.image_files | Engine writes **uncompressed** TGA (header type 2, `engine/core.py:266`), not RLE. Paint is 24-bit, spec is 32-bit (alpha = lighting mask). Size follows the template. Both Channel PNG Export labels documented. |
| tools.editing_limits | Layer card has FLIP H **and** FLIP V. Layer undo is up to 30, with a floor of 5 and a 96 MiB budget (`paint-booth-3-canvas.js:27389`). Right-click Flip View H/V (view-only mirror) added. |
| workflows.business_and_sharing | GPU path is CuPy (NVIDIA CUDA or AMD ROCm), not NVIDIA only. ZIP keeps only the 2 newest renders. Refund / beta / specs / selling / cloud sync stay "not stated, ask support" (nothing in the repo states them). |
| workflows.platform_and_limits | "Store page shows the current price" is not in the repo (only the Payhip link, `main.js:754`) -> softened. |
| workflows.iracing_side | "Need to own the car: yes" was an inference -> reworded to the repo fact (run it once; ownership is iRacing's rule). Parent-folder save quirk added. |
| playbook.colour_matching | Helmet/suit advice removed (cars only). Colour-blind points labelled general practice, not an app feature. |
| recipes.add_race_number | "Many templates have a Numbers layer" -> "if your PSD has one". The rest matched code. |

Rebuilt with `build_encyclopedia.py`: `enc_v2_test --final` PASS (379 files, 6164 articles), `--depth` PASS, `enc_test` 27/27 GREEN. `js/spb-encyclopedia-data.js` copied to `electron-app/server/js/`; both `paint-booth-v2.html` copies now load `spb-encyclopedia-data.js?v=20261005fc5`. `aliases` were not touched.


## Wear article fix (2026-10-05)

**Old claim** (`finishes.wear`, 2026-10-04): open "Season set-up" in the left column, click "+ Add Race", "Quick: Wear Ramp", "Render All Races"; "Not every build shows a per-zone wear slider". Same text lived in `_drafts/finishes.jsonl` / `finishes_v3.json`, `enc_B_part6.py:325` and `enc_B_v3_finishes_b.py:290-315`, plus three generated control pages (`controls_zones_1`: Add Race, Quick: Wear Ramp, Render All Races) that said "Click the button".

**Evidence**
- Season mode retired: `toggleSeasonMode()` only hides `#seasonPanel` and shows the retired toast (`paint-booth-5-api-render.js:2648`, toast text `:2352` "is disabled in this booth build"); `doSeasonRender()` toasts then returns (`:2706`). `#seasonPanel` is `display: none` (`paint-booth-v2.html:2534`) and the page has no `btnSeasonToggle`; nothing calls `toggleSeasonMode`, so the panel (and Add Race / Wear Ramp) cannot be reached.
- No wear control anywhere live: `setZoneWear` (`paint-booth-2-state-zones.js:12221`, clamps 0-100, also `js/zones/zone-material-assignment-controls.js:78`) has no caller (no onclick/oninput in html or js); no `wearSlider` element exists (`paint-booth-3-canvas.js:249` and `paint-booth-2-state-zones.js:16067` read one that is not in the page); zone card has Base Strength (`:2098`) and no wear. MCP `spb_edit_zone` has `base_strength` (`mcp/server/tools.json:721`) and no wear; `js/spb-pro-edit.js`, `js/spb-pro-ai.js`, `js/spb-offline-answer.js` have no wear setting.
- Wear is still a real stored value: saved with zone setups (`js/zones/zone-config-preset-controls.js:113`), sent to the engine as `wear_level` when > 0 (`paint-booth-5-api-render.js:738`), applied per zone (`shokker_engine_v2.py:20467`, `apply_wear :22944`); the render server also accepts it (`server.py:5052`, `:5566`).
- Real worn looks today (names exact, all in the Base Material picker): Sun Faded (`paint-booth-0-finish-data.js:1107`, Foundation EFX shelf), Die-Back Patina (`:152`, SHOKK WORKS), Hardware: Battle Worn (`:441`, TACTICAL & FIELD), Surface Rust (`:1104`, Foundation EFX); spec overlays Micro Chipping (`js/spec-overlays/catalog-data.js:1244`) and Scuffed Enamel (`:1169`); Base Strength 0-100 slider. **Desert Worn (`:650`), Barn Find (`:574`) and Rally Mud (`:993`) are picker-hidden** (`scripts/ai_atlas/enc_picker_hidden.json`: reachable by name through the Shokker AI helper / MCP only), so the new article does not send buyers to them in the picker.

**New text** (`finishes.wear`): Wear is a number 0-100 kept per zone that the engine turns into chips, scratches and duller clearcoat; this build has no Wear slider and Season set-up is retired; to get the look pick a worn Base Material, lower Base Strength to 50-70, add Micro Chipping / Scuffed Enamel at 30-40, render once per stage for a "season". Deep sections add "Where the controls went" and "The look you can get today"; FAQ answers "What happened to Season mode / Add Race / Quick: Wear Ramp?" and "Can the AI or MCP set wear?" (no). The three Season control pages now say retired / cannot be reached, point to `finishes.wear`, and no longer carry a Do-it action. No mention of the hidden mode.

**Generators**: new `scripts/ai_atlas/enc_wear_fix.py` holds the corrected text once (`WEAR_ADD`, `WEAR_V3`, Season page text); `enc_B_part6.py` and `enc_B_v3_finishes_b.py` now import it, so a regenerate gives the same words. `enc_wear_fix.py --write` is idempotent, also patches the stale drafts, and is run by `build_encyclopedia.py` right after `enc_reader_fix.py`.

**Gates**: `helper_eval.js` 297/297; `enc_test.js` 27/27 GREEN; `enc_v2_test.js --final` 379 files / 6,173 articles all PASS (ANCHORS PASS); `--depth` PASS; `enc_reader_smoke.js` 128/128 GREEN. `enc_ideas_fix_r4.py` re-run: 0 changes. `js/spb-encyclopedia-data.js` copied to `electron-app/server/js/`; both `paint-booth-v2.html` now load `?v=20261005wr1`. `data/encyclopedia/` is not mirrored under `electron-app/server/` in the tree; `copy-server-assets.js:478-481` copies it at build time.

**Left open (not changed, outside this fix)**
- `recipes.weathered` (`recipes.json`), `workflows.json` (crash-damage article, ~lines 2178-2269) and `pages/finish_more_bases_7.json` tell buyers to pick Desert Worn / Rally Mud under BASE, but both are picker-hidden. Worn-look recipe source: `scripts/ai_atlas/enc_C_drafts/V3_recipes.py`.
- Fleet batch control pages (`controls_zones_1`: Add Car, Render All Cars) are the same kind of retired control (`toggleFleetMode`, `paint-booth-5-api-render.js:2356`) and still say "Click the button".
- `docs/ai_knowledge/app_map.md:139-141`, `js/spb-ai-knowledge.js`, `js/spb-self-help.js` (generated from `scripts/ai_atlas/ui_map.json`, `build_ui_map.py:169`) still list Add Race / Quick: Wear Ramp / Render All Races as live buttons under "Season batch".

## Stale references sweep (2026-10-05)

**Problem.** Help text sent buyers to (a) RETIRED batch controls, (b) finishes that are not in the Base Material picker, and (c) three generated help files (`docs/ai_knowledge/app_map.md`, `js/spb-self-help.js`, `js/spb-ai-knowledge.js`) that listed the Season / Fleet buttons as live.

**Gate (new).** `python scripts/ai_atlas/enc_stale_refs_check.py` scans `data/encyclopedia/**/*.json` (not `_drafts`), `js/spb-self-help.js` and `js/spb-ai-knowledge.js`, prints one verdict line per hit and exits non-zero while any remain (`-q` = hits only, `--list-retired` = the derived list). The retired list is DERIVED from code on every run (and the gate fails if it finds none), the hidden-finish list is `scripts/ai_atlas/enc_picker_hidden.json` (1,322 ids; 1,224 names tracked after masking names that a visible finish also carries). A hidden-picker article is only allowed to describe hidden finishes when it says they are not listed AND tells the buyer to ask the Shokker AI helper by name (`recipes.named_looks`; a hidden finish's own `finish_*` page keeps its Do-it, which applies the finish directly).

**Retired controls, with evidence (Fleet verified like Season).**
- `paint-booth-5-api-render.js:2356` `toggleFleetMode()` and `:2411` `doFleetRender()` only call `_showRetiredBatchModeToast('Fleet mode')` and return (everything after the `return` at :2412 is dead code). Toast text at `:2352`.
- `paint-booth-5-api-render.js:2648` `toggleSeasonMode()` and `:2706` `doSeasonRender()` do the same for `'Season mode'`.
- `paint-booth-v2.html:2517` `#fleetPanel style="display: none;"` holds Add Car / Render All Cars; `:2534` `#seasonPanel style="display: none;"` holds Add Race / Quick: Wear Ramp / Render All Races. No toggle button opens either panel.

**Fixes (build-time, so a rebuild keeps them).**
- `scripts/ai_atlas/enc_stale_fix.py` (NEW, wired into `build_encyclopedia.py` right after `enc_wear_fix.py`, idempotent, also patches `_drafts/*` and the generator sources `enc_B_v3_finishes_b.py`, `enc_B_v3_spec_a.py`, `enc_C_drafts/V3_recipes.py`): Fleet pages (`controls_zones_1.pro.zones.add_car`, `controls_zones_1.btnFleetRender`) now say "retired, render each car with RENDER", lose their Do-it; weathered "season ramp" wording removed; hidden finishes swapped; Do-it ids remapped (`ACTION_MAP`, de-duplicated).
- Generated files: `scripts/ai_atlas/build_ui_map.py` marks every control inside the hidden panels `retired` from `enc_stale_refs_check.retired_code_evidence()` (no hand list), `app_map.md` leaves them out of the live lists and gets one "Retired controls (not in this build)" chunk, `_easy_claude_work/selfhelp_build.py` carries the `retired` flag into UI_DATA. Regenerated `ui_map.json`, `app_map.md`, `js/spb-self-help.js`, `js/spb-ai-knowledge.js`. Two hand-written sources fixed: `docs/ai_knowledge/how_do_i.md` ("Clear Satin" -> "Satin") and `05_design_and_taste.md` ("Race Worn" -> "Hardware: Battle Worn"; the liquid-mirror line).

**Hidden-finish swaps (all checked against `paint-booth-0-finish-data.js`; spec = metal/rough/coat).**

| Was (hidden) | Now (visible) | Evidence |
|---|---|---|
| Soft Matte / Clear Satin / Soft Gloss (Do-it) | Matte / Satin / Gloss | :791 0/200/158, :1001 0/95/69, :724 0/30/16 - identical numbers to the hidden twins |
| Candy, Candy Gold/Lime/Aqua | Candy (Foundation), colour chosen by the buyer; Van: Candy Apple | :714 200/15/16 polished metal under a colour you pick |
| Carbon Base, Carbon Fiber | Hardware: Carbon Handguard | :442 twill weave under resin, high gloss |
| Carbon Satin | Carbon Twill Weave | :5356 true 2/2 twill, semi-matte |
| Metal Flake, Supernova Flake, Starlight Mica Resin | Chunky Metalflake, Holo Flake, Micro Glitter | :1101, :1097, Foundation EFX; Pearl -> Pearl (Foundation) |
| Sapphire / Ruby / Emerald / Amber / Cathedral / Smoked Glass | Wet Look + a colour (gem glass), Cathedral Veil, Shag: Smoked Glass, Glass Flake | :1077 Wet Look 0/15/16 vs gem glass 0/17/16; :1084; :268; :1102 |
| Desert Worn | Sun Faded | :1107 bleached zones, dust-pitted skin (Desert Worn: sun-bleached, matte) |
| Rally Mud | Extreme: BMX Dirt | :380 compacted clay, embedded grains, semi-matte |
| Race Worn | Hardware: Battle Worn | :441 |
| Firefly Glow, Bioluminescent | Firefly Lantern, Bioluminescent Wave | :663, :3948 |

Also removed: "Candy Chrome is roughness 4 / Mercury is 3" in `spec.channel_g_roughness` (Candy Chrome is hidden, and the visible Mercury base is roughness 127, so the claim was wrong for the visible catalogue); it now cites Foundation Chrome roughness 2 only. Named gem-glass finishes are still reachable: `recipes.wet_glass` tips say to ask the Shokker AI helper by name.

**Counts.** Gate hits before: 100 (RETIRED 11 + HIDDEN 89, incl. 18 in the generated JS files) -> after: 0 (`RESULT PASS: 6173 article(s)+js scanned, hits retired=0 hidden=0`). Edited: 61 text/Do-it edits in 7 final JSON files (`recipes`, `finishes`, `spec`, `workflows`, `pages/controls_zones_1`, and the two drafts), 3 generator sources, 4 generated help files.

**Gates (all re-run after the final rebuild).** `enc_stale_refs_check.py` exit 0; `helper_eval.js` 297/297; `enc_test.js` 27/27 GREEN; `enc_v2_test.js --final` and `--depth` all PASS (6,173 articles; one first-pass FAIL, `recipes.wet_glass` summary over 2 sentences, fixed by moving the ask-by-name hint to a tip); `enc_reader_smoke.js` 128/128 GREEN. Copied `spb-self-help.js`, `spb-ai-knowledge.js`, `spb-encyclopedia-data.js` to `electron-app/server/js/`, `?v=` tokens bumped in BOTH `paint-booth-v2.html` copies (`20261005st1`, encyclopedia data `20261005st2`). Not touched: `spb-offline-answer.js`, `spb-pro-ai.js`, `spb-pro-edit.js`.

**Open (not fixed here).** (1) `js/spb-self-help.js` and `js/spb-ai-knowledge.js` still name the hidden Easy panel (8 mentions each: UI_DATA rows for the Easy panel, `hdi.use_easy...`); these come from `ui_map.json` panel items, unchanged by this sweep and not covered by `enc_v2_test`'s Easy check (which only scans the encyclopedia data). (2) Whether `spb-offline-answer.js` / `spb-pro-ai.js` still suggest a Season/Fleet button or a hidden finish by name was not checked (other worker's files).

## Hidden-feature sweep (2026-10-05)

Owner rule 2026-10-04: Easy mode is hidden, so no buyer-facing or AI-facing text may name it. The Encyclopedia was already filtered; this sweep covered the other helper outputs. The single list of hidden features stays `scripts/ai_atlas/enc_hidden_features.json` (its `gate_text_patterns` define a hit).

**Inventory (hits under those patterns, before -> after)**

| File | Before | After |
|---|---|---|
| js/spb-self-help.js | 63 | 0 |
| js/spb-ai-knowledge.js | 52 | 0 |
| docs/ai_knowledge/app_map.md (generated) | 22 | 0 |
| docs/ai_knowledge/04_limits_and_app_map.md | 1 | 0 |
| docs/ai_knowledge/how_do_i.md (source) | 31 | 0 after the generator filter; the raw file keeps the hidden how-tos on purpose (24 raw) |
| scripts/ai_atlas/ui_map.json (generated) | 75 | 0 |
| js/spb-support-answers.js | 0 | 0 |
| docs/ai_knowledge/ other cards, tutorials/*.md | 0 | 0 |
| mcp/ (server/tools.json, server/index.js, README.md), integrations/spb-mcp | 0 | 0 |
| server_routes/ai_copilot_routes.py | 0 | 0 |
| data/encyclopedia/** (string values) | 0 | 0 |

**Generator changes**
- `scripts/ai_atlas/enc_hidden.py`: new `is_hidden_item()` (UI-map item / panel / mode) and `scrub_md()` (line-wise markdown filter: drops hidden how-to blocks, removes hidden ui ids from tag lines, scrubs sentences, renumbers steps, drops empty blocks).
- `scripts/ai_atlas/build_ui_map.py`: how_do_i goes through `scrub_md`; a new 3c step drops the hidden items / panels / mode (30 items, 2 panels, 8 how-tos) and scrubs the text of the rest; four curated sentences reworded to the Pro way (layer filter box, Pro-mode "when", mode-pill panel text, app_map header); meta caveats no longer mention it.
- `_easy_claude_work/selfhelp_build.py`: filters hidden ids / items and scrubs UI_DATA text; HOWTO built from the filtered how_do_i.
- `scripts/build_ai_knowledge.py`: every card and tutorial goes through `scrub_md` before chunking.
- `docs/ai_knowledge/how_do_i.md` and `04_limits_and_app_map.md`: sentences that said "switch to Easy for X" reworded to the Pro / Chat way (first-steps, the "do I need zones" card, layers-by-colour, numbers colour, the many-layers PSD card, the app-map line).
- `js/spb-self-help.js` hand-written code (outside the generated block): removed the Easy-vs-Pro topic (now "Pro vs Chat"), the L.easy label, the dead hdi.easy_* routes and the CHECK_HDI entry; the "you are in Easy mode" sentences now say "a simplified view" and point at the PRO / CHAT pill. Detection of that state is kept as code only.
- Regenerated: ui_map.json, app_map.md, spb-self-help.js UI_DATA / HOWTO (111 entries), spb-ai-knowledge.js (339 chunks). Root copies of spb-self-help.js and spb-ai-knowledge.js copied to electron-app/server/js/; ?v= tokens set to `20261005hs1` in both paint-booth-v2.html copies.

**New gate:** `python scripts/ai_atlas/hidden_feature_check.py` (add `-q` for verdicts only). Scans the outputs above (JSON by string values, JS / Python without full-line comments, how_do_i.md after the generator filter) and the root vs electron-app/server mirror of the generated JS; exits 1 on any hit. Result: PASS, 406 files, 0 hits.

**Gates run:** hidden_feature_check PASS; helper_eval 297/297; enc_test 27/27; enc_v2_test --final all PASS; enc_reader_smoke 128/128; enc_stale_refs_check PASS (hits 0); the 14 tests/ai_self_help_*.cjs contracts, selfhelp_test / holdout / claims all unchanged.

**MCP:** no MCP manual or tools.json text changed (0 hits before and after), so the .mcpb does NOT need a rebuild.

**Left for the owner / other lanes**
- Not edited (other worker): js/spb-offline-answer.js has 1 hit under the gate patterns (listed, not edited); js/spb-pro-ai.js and js/spb-pro-edit.js have 0. They read the regenerated knowledge / self-help data at run time, so re-run hidden_feature_check.py after that worker finishes.
- Code comments that name the mode (spb-chat-studio.js, spb-quests.js, spb-guided-mode.js, spb-native-file-dialogs.js, spb-offline-builder.js, spb-encyclopedia*.js) are developer text, not shipped to a buyer, and were left. paint-booth-v2.html still holds the hidden Easy UI itself (aria-hidden); that is the feature's own code.
- tests/ai_selfhelp_display_editor_contract.cjs fails on a frozen source hash ("self-help source changed after this test freeze"); it was already failing before this sweep (the file had drifted from the frozen hash). The hash needs a reviewed refresh by whoever owns that test.
- js/spb-support-answers.js differs between the root and electron-app/server/ copies (not touched here, it is another lane's file); `node scripts/sync-runtime-copies.js --write` will carry it over when that lane is done.
- To un-hide later: remove `easy_mode` from enc_hidden_features.json, then run build_ui_map.py, selfhelp_build.py, build_ai_knowledge.py (and re-add the Pro vs Easy wording that was reworded by hand).
