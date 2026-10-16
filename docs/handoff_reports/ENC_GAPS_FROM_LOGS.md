# Encyclopedia gaps from the real request log (2026-10-05)

Lane: Claude worker, encyclopedia data only (no edits to js/spb-enc-search.js, spb-offline-answer.js, spb-pro-ai.js, spb-pro-edit.js).
Work dir: `_easy_claude_work/enc_gaps/` (mine.py, query.py, verdicts.py, art.py, log_queries.jsonl, verdicts.jsonl).

## 1. Mining

- Source: `output/ai_logs/copilot_turns.jsonl` (1,859 lines; typed messages = src enter/chip/askai).
- Question / how-to filter: offline cls ANSWER or ONLINE, ends in `?`, or starts with a question word; edit verbs (make/add/change ...) excluded.
- Near-dup collapse (token-set Jaccard >= 0.8): **96 unique questions / 245 messages**.
- 29 of those are edit commands or context-only follow-ups ("do the bumper too", "half that", "add stripes", "save it") and were not queried.
- **67 queried** against `http://127.0.0.1:59879/api/encyclopedia/search?k=3` (ranker 2026-10-05.8).

## 2. Verdicts (judged on article text, not score)

| verdict | unique | messages |
|---|---|---|
| answered well | 46 | 114 |
| ranking miss | 10 | 23 |
| knowledge gap | 11 | 30 |

After the new articles were added, the questions were queried again (tag `after` in log_queries.jsonl):
- **All 11 gap questions now land top-1 (confident) on the new article.**
- q53 (gold or silver on black) and q32 (pic of my dog on the hood) also move to a new article that answers them.
- **No answered question changed its top-1.**
- That leaves **8 ranking misses** (table in section 4).

## 3. New articles (4)

Written by `_easy_claude_work/enc_gaps/add_articles_gaps.py` in the r4 format, with an atomic write.
- The script keeps ideas.json in its one-article-per-line layout. A first run had reformatted it with indent=1; `fmt_ideas.py` restored it, and the layout was verified byte-identical against HEAD.
- The alias "looks plastic" moved from support.flat_or_shiny to the new dedicated article. "looks cheap" stays on ideas.look_expensive.

| id (file) | log questions (msgs) | fact sources |
|---|---|---|
| `recipes.artwork_on_car` (recipes.json): Put a picture on the car: a dragon, your dog, a skull | draw a dragon on the hood (10), pic of my dog on the hood (2) | + Layer `paint-booth-v2.html:3844`; file types `paint-booth-3-canvas.js:26985`; Move (V) `paint-booth-v2.html:2281`; Transform (Ctrl+T) `:2283`; Brush (B) `:2304`; layer card DUPE / MIRROR (Mirror Clone) / STROKE FX / MAKE ZONE `paint-booth-3-canvas.js:23676-23692`; AI cannot show pictures `js/spb-pro-ai.js:80`; offline custom-art decline `js/spb-offline-answer.js:1489`; Dragon Breath `paint-booth-0-finish-data.js:897` on Flames shelf `:5809` (live in /api/finish-data, not retired) |
| `support.looks_plastic` (support.json): My car looks like plastic, fake or like a toy | looks plastic in iracing (3), fake like a toy (2), cheap plastic (2) | metal 0 = plastic/paint `docs/ai_knowledge/02_spec_and_finishes.md:4`; saturation / fine texture / limited palette `05_design_and_taste.md:4,7`; R METAL view `paint-booth-v2.html:3489`; Foundation Pearl 100/40/16 and Metallic 200/50/16 `engine/base_registry_data.py:427-428`, names `paint-booth-0-finish-data.js:703-704`; overlays Metallic Sand / Holographic Flake / Stardust Fine / Pearl Micro `:4921-4924` in group Sparkle & Micro-Metal `:5437-5445`; Foundation EFX flakes `:1097-1101`, group `:5788`; Spec Strength `paint-booth-2-state-zones.js:2109`; Show my files `paint-booth-5-api-render.js:4110`; Ctrl+R `js/spb-support-answers.js:16` |
| `ideas.finishes_by_body_colour` (ideas.json): Finishes and accent colours for a black, white or coloured car | finishes for a dark car (2), good on a white car (2), white or black on blue (2), gold or silver on black (2) | contrast rules and palettes (Premium dark, Stealth, Clean white, Blue and gold, black separators) `docs/ai_knowledge/05_design_and_taste.md:4,7,10-17,21-25`; iRacing multiplies paint by metal `js/spb-support-answers.js:37`, `docs/ai_knowledge/10_support_troubleshooting.md:29`; Foundation shelf `paint-booth-0-finish-data.js:5785-5787` |
| `finishes.base_compare` (finishes.json): Gloss, satin, matte, metallic, pearl, candy and chrome compared | metallic vs pearl (2), satin or gloss (2), what metallic finishes (2), candy or metallic (1) | every value from `engine/base_registry_data.py` (Gloss 383, Wet Look 395, Semi-Gloss 397, Satin 399, Eggshell 409, Flat Black 574, Matte 581, Primer 657, f_* 425-452); names `paint-booth-0-finish-data.js:701-718`; Foundation has no colour of its own, sheen and metal ladders `:5781-5787`; Foundation Metallic has no baked-in flake `:703`; Foundation listed first `paint-booth-2-state-zones.js:15702`; BASE COLOR options `:1910-1912`; preview views `paint-booth-v2.html:3489-3496` |

Fact-checking caught errors that would have been in the draft:
- The plain `metallic` / `pearl` / `candy` / `chrome` bases are on shelves **retired from the picker on 2026-09-05** (`paint-booth-0-finish-data.js:5764-5772`). The articles name the live **Foundation** versions instead (f_metallic, f_pearl, f_candy, f_chrome ...). They have the same spec numbers.
- Foundation Metallic shows **no flake** (`:703`). The articles send people to a flake overlay or a Foundation EFX flake finish, and do not promise sparkle from Metallic.
- In the picker the shelf is called **Foundation** (the group name). "Foundation Bases" appears only in the finish atlas (`js/spb-finish-atlas.js:85`).
- Neither helper can draw a picture (`spb-pro-ai.js:80`, `spb-offline-answer.js:1489`). The artwork article says so and gives + Layer as the real workflow.

## 4. Ranking misses for the search lane (js/spb-enc-search.js not edited)

| qid | query (msgs) | wrong top-1 | right id | likely general mechanism |
|---|---|---|---|---|
| 21 | how do i save this so i can use it in iracing (3) | help_topics_1.save | help_howto_1.export_iracing | the purpose clause ("use it in iracing") should outrank the verb ("save") |
| 18 | how do i get my number on the doors bigger (3) | recipes.add_race_number | help_howto_2.move_logo | "bigger / smaller / resize" + an object means transform, not add |
| 16 | wheres the spec map thing at (3) | help_howto_3.what_is_spec | help_howto_3.see_spec | "where is X" should prefer the see/find article over the what-is article |
| 20 | whats the diffrence between base and pattern layer (3) | patterns.layers_and_stacking | finishes.four_kinds | "difference between A and B" should prefer an article that defines both |
| 31 | can you explain pearl to me (2) | recipes.flake_pearl | ideas.pearl_white | "explain X" should prefer a definition over a how-to recipe |
| 43 | i want people to see me from across the track (2) | workflows.business_and_sharing | ideas.stand_out_in_pack | "see me / across the track / far away" means visibility; the business page wins on noise words |
| 64 | is that metallic or flat? (2) | spec.channel_r_metallic | ui_shell.preview_channel_views | "is that X" means checking the current zone (preview channel views) |
| 93 | make my sponsors easier to read (1) | recipes.mirror_side | ideas.readable_on_tv | "easier to read" + sponsors means readability; the mirror page wins on noise words |

New articles resolved two of the original 10 misses: q32 (dog pic) now goes to recipes.artwork_on_car, and q53 (gold or silver on black) to ideas.finishes_by_body_colour, which answers it in its FAQ.

## 5. Gates (all run after the final build)

| gate | result |
|---|---|
| node _easy_claude_work/helper_eval.js | 297/297 100% |
| node _easy_claude_work/enc_test.js | 27/27 GREEN |
| node _easy_claude_work/enc_v2_test.js --final | 6177 articles, all PASS. The first run had 3 FAIL (2 summaries over 330 chars, 2 duplicate aliases); all fixed |
| node _easy_claude_work/enc_v2_test.js --depth | lane C 202/202, all PASS |
| node _easy_claude_work/enc_reader_smoke.js | 128/128 GREEN |
| python scripts/ai_atlas/enc_stale_refs_check.py | PASS, 0 hits |
| python scripts/ai_atlas/hidden_feature_check.py -q | PASS, 0 hits |
| python _easy_claude_work/eval/online_ground/enc_parity.py | 1689/1689 = 100% |

## 6. Build, sync, cache

- Rebuilt only through `python scripts/ai_atlas/build_encyclopedia.py`. The wear and stale fixes made no change.
- The build's anchor repair also updated source line numbers in layers.json (2 lines) and shortcuts.json (8 lines). They had moved after another lane edited spb-pro-edit.js and spb-pro-zone-kit.js.
- The reader-fix step of the build emptied the `screens` lists of the 4 new articles, because no screenshot matched them closely. The depth gate passes without them.
- `js/spb-encyclopedia-data.js` was copied to `electron-app/server/js/` (cmp identical).
- Cache token `?v=20261005st2` changed to `?v=20261005gap1` in both `paint-booth-v2.html` copies (line 4694).
- `sync-runtime-copies --check` shows one unrelated report-only drift from another lane: `engine/spec_pattern_families/snakeskin_candidates_2026_10_04.py`.
- Not done: the wiki board and log (left to the lead). Nothing committed.

## Note on the log

All 1,800 port-tagged turns came from the test server (port 59879), so the log mixes real typing with eval-harness traffic. Frequencies are message counts in that log, not unique users.

