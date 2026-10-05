# Encyclopedia v2 - Lane C report (writer: Sonnet 5.5, 2026-10-04)

Brief: `docs/handoff_reports/ENCYCLOPEDIA_V2_WRITER_BRIEF.md`. Subagents used: 0.
Files I own: `data/encyclopedia/{preview_render,support,workflows,recipes,cars,shokk_drop,easy_mode,ai_copilot,settings,car_pages}.json`, `scripts/ai_atlas/enc_gen_C.py` (generator), `scripts/ai_atlas/enc_write_C.py` (writer helper), drafts in `scripts/ai_atlas/enc_C_drafts/` (the older `_drafts` scripts were removed by another lane; the JSON files are authoritative).

## Progress (articles written / planned)
| Part | File | Written | Gate |
|---|---|---|---|
| X Preview, render, export | preview_render.json | 12 | PASS |
| XV Troubleshooting | support.json | 15 (8 quick cards) | PASS |
| I Getting started | workflows.json | 10 | PASS |
| XIV Recipes | recipes.json | 20 (split from workflows to stay under 100 KB) | PASS |
| XI Cars | cars.json | 5 | PASS |
| XII Shokk Drop | shokk_drop.json | 5 | PASS |
| XIII Easy / Chat / AI | easy_mode.json 4, ai_copilot.json 5 | 9 | PASS |
| XIII Settings | settings.json | 4 (overview, file picker, looks + Training Wheels, licence) | PASS |
| Generated car pages | car_pages.json (by `enc_gen_C.py`) | 38 / 38 cars, 98 KB, all `covers:["car.<id>"]` | PASS |
Hand-written: 80. Generated: 38. Gate: `node _easy_claude_work/enc_v2_test.js --final` -> `TOTAL 275 files, 5907 articles checked, all PASS` (no PENDING ids, coverage 80.6%).
Regenerate pages: `python scripts/ai_atlas/enc_gen_C.py` (reads `js/spb-car-atlas-data.js` + `enc_inventory.json`; compact one-article-per-line output keeps it under the 100 KB cap).

## Code differs from the wiki / plan / other lanes (code wins)
- EASY mode is hidden by CSS (`spb-mode-opt` EASY button `aria-hidden`); only PRO and CHAT are visible. Lane A `ui_shell.mode_pill` and figure `g17_pick_a_door` (three doors) still show EASY as a visible third mode.
- Lane A `zones.presets_templates` mentions Render All Cars; Fleet / Season batch modes are retired ("disabled in this booth build").
- Lane B `finishes.wear` describes a Wear control and Season set-up that are retired or not visible in this build.
- `GETTING_STARTED.html` is stale (three-mode text, older flow). The `spb-quests.js` Q-render hint says Auto-Deploy copies renders; Auto-deploy defaults to OFF and only matters when the car folder is empty.
- `docs/CAR_LEARNING.md` says 31 cars; the atlas has 38 (31 checked + 7 `claude-*` drafts, each with 3-4 parts and needing buyer confirmation).
- Quests: 11 in code (older text says fewer / more).
- Licence: the Settings gear License section in `paint-booth-v2.html:4911-4978` always shows "License Active (Alpha)" and hides the key box (`updateLicenseUI`); the key is entered in the launch window (`electron-app/license.html`, key placeholder XXXXX-XXXXX-XXXXX-XXXXX). Lane A control pages `licenseKeyInput` / Activate / Deactivate describe a key format SHOKKER-XXXX-XXXX-XXXX and a visible box that the code hides. `activation-grace` (72 h) has a reader but nothing starts it, so I did not document it.
- `docs/ai_knowledge/04_limits_and_app_map.md` still says "OpenRouter key" and lists EASY as a switch; I wrote the CURRENT decision (offline guided builder + encyclopedia flags; online DeepSeek via gear; MCP through Claude/ChatGPT; one model only; every AI change has Undo; numbers/sponsors/logos untouched unless named).
- No PSD/XCF/ORA write exists, only the Photoshop round-trip export; helmet / suit are not supported targets.
- Image Forge (`IMAGE_FORGE_GUIDE.html`) is an author-side finish-id guide; the Auto Painter (Shokk Trace) button was removed from the top bar (2026-05-31); the EXPERIMENTAL tab (Design It / Photo to Livery / Shokker-ize) is hidden (2026-06-14).
- Preview "render stats" have no visible button; Trading Paints spec is the compiled .mip only; "User ID" is the iRacing Customer ID, never the car number (SPB has no car-number field; Custom Number / Sim-Stamped Number only choose car_num_<ID>.tga vs car_<ID>.tga).

## Overlap with Lane A (aliases yielded to A)
My quick cards (number_modes, where_files_go, auto_deploy, saving_projects, preview_vs_render) overlap Lane A ui_shell articles; colliding aliases were dropped from my side (the helper now also checks `pages/`). Lane A control pages for my domains use ids `controls_<area>_<n>.<inventory id>`.

## Gaps
- No `performance` settings article: the only code for it is a localStorage flag (`spb_iracing_performance_mode`) with no visible control; replaced by "Looks, light or dark, and Training Wheels".
- Training Wheels default: `wheelsOn:false` until the user chooses (`js/spb-quests.js:43`); Export ZIP default read as off from the unchecked checkbox, not from a runtime test.
- Licence key shape and per-machine rules are from `electron-app/main.js` only; I did not exercise the Payhip service.
- Car pages describe part positions from fractional boxes (words like "top left of the sheet") and say "roughly N by M pixels"; they were not eyeballed against each template.
- Scratch finder `scripts/ai_atlas/_enc_find_C.js` deleted.

## FINAL
Done: 80 hand-written articles + 38 generated car pages, all passing; shared gate `--final` green (275 files, 5907 articles). Pending related ids: none.

## FINAL 2 (2026-10-04, coverage push + index merge)

**Coverage: 1554 / 1554 = 100.0%** (was 80.6% after Phase 1, 95.0% after the generated help pages). Gate `node _easy_claude_work/enc_v2_test.js --final`: 283 files, 6164 articles, all PASS. `_easy_claude_work/enc_test.js`: 26/26 GREEN.

| What | Where | Count |
|---|---|---|
| Generated help pages (how-do-I answers, self-help topics, support answers, Getting Started sections) | `data/encyclopedia/help_pages.json` + `pages/help_{howto,topics,support,guide}_N.json`, made by `scripts/ai_atlas/enc_gen_C2.py` (+ `enc_gen_C2_dump.js`, read-only) | 224 pages, 5 parts, 235 KB |
| New recipes | `recipes.json` (now 27): three-colour gradient, holographic, rear accents, finish on numbers, make it pop, undo/start over, change body keep numbers | +7 |
| New playbook domain | `playbook.json` (16): colour modes, strengths, H/S/B, gradients and flake, buyer words, recolour part of art, session start, preview cannot show, things to avoid, artwork reveal, spec-only, livery parts, scheme families, composition, placement, Smart Separate status | +16 |
| New concepts domain | `concepts.json` (5): the wiki lessons rewritten for a buyer | +5 |
| Easy / AI / render | `easy_mode.screen_tour`, `ai_copilot.panel_tour`, `ai_copilot.can_and_cannot`, `ai_copilot.mcp_tool_list`, `preview_render.render_stats_overlay` | +5 |
| Covers added to existing articles | doc.10 support records, doc.04 records, a few doc.03 records -> the support / preview_render / settings / workflows / ai_copilot articles that already explain them (`enc_C_drafts/C_p2_covers.py`, idempotent) | 23 ids |

Writers: `scripts/ai_atlas/enc_C_drafts/C_p2_a.py`, `C_p2_b.py`, `C_p2_covers.py` (re-runnable; each call upserts by id).

### Index merge
`scripts/ai_atlas/build_encyclopedia.py` now writes `window.SPB_ENCYCLOPEDIA.v2` into `js/spb-encyclopedia-data.js`: `groups[]` = `{f: file under data/encyclopedia/ holding the full article, d: domain, k: 0 hand-written | 1 script-made page, r: rows}`, row = `[slug, title, summary?, aliases?]`, article id = `d + "." + slug`; `byAlias` = alias -> `[group, row]`. All 6164 articles/pages are in it. Hand-written articles carry summary + aliases; script-made pages carry slug + title (summaries dropped by the size guard, read them from `f`; their aliases live in `byAlias`). v2 aliases are deliberately NOT merged into the v1 `index`/`phrases`, so what the helper underlines does not change. File: 879 KB (v1 keyword part 435 KB + v2 index 444 KB), under the 900 KB target.
`_easy_claude_work/enc_test.js` size check changed from "whole file < 450 KB" to "keyword part < 450 KB and whole file < 900 KB" (the v2 index is budgeted separately, per the orchestrator's 900 KB target). `enc_gen_A.py` re-run: control pages link the new shokk_drop / settings / ai_copilot articles.

### Code vs docs notes added in Phase 2
- Render Statistics overlay exists in `paint-booth-v2.html` (5143-5152, 5303-5345) but nothing in this build opens `toggleRenderStats()`; the article says so.
- Smart Separate / Auto-build layers: scripts are not loaded by the customer app (`paint-booth-v2.html:4721-4725`); `playbook.smart_separate_status` says so and points to Spec Sculpt's own Auto-Separate and to layered files.
- `docs/ai_knowledge/*` cards are written for AIs and partly predate the current owner decision (offline guided builder, online gear model, MCP); the buyer articles follow the code and the decision, and cite the docs only for facts that still hold.
- GETTING_STARTED.html is beta-era (10 quests vs 11 in code; Easy mentioned though parked); its generated pages are kept as written there and the Easy parts are corrected in `easy_mode.*`.

### Open item for the orchestrator
`node scripts/sync-runtime-copies.js --check` reports drift for `js/spb-encyclopedia-data.js` and `js/spb-encyclopedia.js` vs `electron-app/server/js/`. I did not run `--write` (it would also copy other agents' files); run it after the last agent finishes.

## FINAL 3 - Easy mode removed from the whole Encyclopedia (owner rule 2026-10-04: "EASY MODE is HIDDEN on purpose")

Gates (all green, run after the final rebuild): `node _easy_claude_work/enc_v2_test.js --final` = 281 files, 6130 articles, all PASS, coverage 1513/1513 = 100% (visible features only; was 1554). `node _easy_claude_work/enc_test.js` = 27/27 GREEN. Index `js/spb-encyclopedia-data.js` = 894 KB (under the 900 KB budget).

Removed / changed:
- **easy_mode domain**: 5 articles. 2 deleted (the Easy overview and the parked-Easy screen tour); 3 were really chat / helper articles and moved to `ai_copilot` with new ids: `ai_copilot.chat_mode`, `ai_copilot.offline_vs_ai`, `ai_copilot.edit_existing` (every reference renamed). `data/encyclopedia/easy_mode.json` is gone.
- **Generated pages**: controls 861 -> 838 (23 removed, incl. `controls_easy_mode_1`); help pages 224 -> 215 (9 removed). Related links and aliases pointing at them are scrubbed.
- **Inventory**: 41 records marked `hidden:true` (all `easy.*`, `mode.easy`, `spbModeEasyBtn`, `hdi.easy_*`, `topic.easy_pro`, `sculpt.btnEasyMode`). Judgment call: `sculpt.btnEasyMode` ("OPEN EASY SPEC SCULPT") is hidden too. Coverage excludes hidden records.
- **Hand-written rewrites** (sentence rewritten, no holes): `ui_shell.mode_pill` (now "PRO / CHAT pill"), `ui_shell.template_layer_views`, `workflows.tutorial_quests`, and `workflows.pro_chat_easy` -> renamed `workflows.pro_or_chat`.
- **v1 glossary**: term `easy_pro` and all Easy aliases dropped; 500 terms remain.
- **Figures**: g07 (layer stack note + Easy source line), g12 (PRO CHAT EASY box, legend, caption) and g17 (now "Pick a door: PRO or CHAT", two cards) regenerated; `figures.json` + SVGs contain no Easy text.

Making it stick:
- One shared list: `scripts/ai_atlas/enc_hidden_features.json` (`features:["easy_mode"]`, reason, date, hidden id patterns, `gate_text_patterns`); helper `scripts/ai_atlas/enc_hidden.py`; sweeper `enc_hidden_apply.py [--report]`; `enc_inventory.py --apply-hidden`.
- Generators honoring it: `enc_gen_A.py` and `enc_gen_C2.py` (filter + scrub), `enc_gen_B.py` and `enc_gen_C.py` and `enc_figs_svg.py` (fail-closed guard: output naming the hidden feature aborts the write), `build_encyclopedia.py` (term/alias/link scrub).
- Gate checks: both `enc_v2_test.js` (all article text, aliases, related ids, figures.json, figure SVGs, index) and `enc_test.js` (whole glossary/flows/v2 index) FAIL if text matches the patterns in the JSON (Easy mode, capital EASY, PRO|EASY pill, paint by numbers, Easy-only buttons). The plain adjective "easy" is not flagged.
- To un-hide later: remove `easy_mode` from `features` and re-run the generators; the deleted hand-written articles are in git history.

Open: `node scripts/sync-runtime-copies.js --check` will show drift for `js/spb-encyclopedia-data.js` and `js/spb-encyclopedia.js` until the Orchestrator runs `--write`.

## V3 FINAL (2026-10-04)
- **111/111 lane C hand-written articles meet the depth bar** (`node _easy_claude_work/enc_v2_test.js --depth --lane C`): concepts 5, settings 4, cars 5, shokk_drop 5, ai_copilot 11, workflows 10, preview_render 13, playbook 16, recipes 27 (complete worked builds, exact settings), support 15 (symptom, every cause, fix steps, how to confirm). Each has deep >=2, examples >=2, faq >=3, mistakes >=2, protips >=1, screens >=1, level; numbers reuse the already-sourced facts.
- **215/215 help_* pages upgraded** (howto 103, topics 36, support 55, guide 21) by `enc_gen_C2.py` + `enc_help_v3.py` (+ `enc_help_v3_links.py`): controls' own curated does/where/when/mistakes, needs/mode, "ask in Chat" lines, follow-up questions, a cited library of common mistakes/faq/protips, links to the matching worked recipe or troubleshooting article (116 pages have combos). First-person helper voice neutralised, poor guide/support titles rewritten.
- Drafts live in `scripts/ai_atlas/enc_C_drafts/V3_*.py`, merged idempotently by `enc_v3_merge.py`; screenshots attached by `enc_v3_screens.py` (lane S ids first, else best word overlap, else window tour) - re-run it after lane S adds more screens.
- Index rebuilt: `js/spb-encyclopedia-data.js` 881 KB. Gates: `enc_v2_test.js --final` and `enc_test.js` (27/27) green for lane C; the only FAIL left is `screens.json` header (lane S file lacks the `articles:[]` the shared gate asks for - not a lane C file).
- Open: run `node scripts/sync-runtime-copies.js --write` (js data/viewer drift); re-run `enc_v3_screens.py` when lane S finishes so articles get topic-matched pictures instead of the generic window tour.
