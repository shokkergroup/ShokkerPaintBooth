# HELPER QUESTIONS LANE (2026-10-06)

Goal: make the helper answer how-to / troubleshooting / iRacing / edge / vague questions better (B-kinds of the 1,000-scenario bank).
Owned: `js/spb-enc-search.js`, `server_routes/encyclopedia_routes.py`, `data/encyclopedia/*`, `scripts/ai_atlas/enc_*.py`, `build_encyclopedia.py`.
Lab: `_easy_claude_work/search_lab/ql/` (probe.js = route + ranker probe; miss.py = miss lister; backup/ = pre-lane copies of every owned file).

## Baseline (tier 1, train, ranker VERSION 2026-10-05.9, before any change; tag `ql_base`)
- TOTAL train: items 162/615 (26.3%), turns 415/1053, harm-flag items 9
- B:trouble 6/48 (12.5%) · B:edge 2/19 (10.5%) · B:vague 5/35 (14.3%) · B:iracing 9/27 (33.3%) · B:howto 26/54 (48.1%) · B:question 28/48 (58.3%) · B:qa_convo 0/17
- A:convo 26/189 · A:edit 60/178

### Miss anatomy (155 failing first turns, non-convo B)
- Routing (class wrong: the router built steps / asked / went online while the ranker already had the gold at rank 1-3): ~50. Mostly statements ("iracing still shows the old paint", "wire lines are on my rendered paint") that are not caught by `Q_PROBLEM` / `SYMPTOM_RE`, and style asks. Listed for S3 below.
- Cover (right article, but its summary / FAQ answer does not carry the fix): ~45. Several generated help pages have one-line summaries such as "The key stays on your PC." / "Shokker writes files for YOU.".
- Ranker / missing knowledge (gold not in answer + top 3): ~35.

## Round 1 (2026-10-06)
- **Ranker VERSION 2026-10-06.1**: 30 R6 REWRITE rows (phrasing classes, `ql/ql_rows.txt`, applied between the `R6 rows begin/end` markers by `ql/apply_rows.py`; the Python mirror reads them from the JS like the R4/R5 rows). Classes: emotional filler, colour-differs-in-sim, white car in sim, half/part of the car differs (zone priority / Everything Else), spec all black, mirrored number, stale preview, edge halo, wear not showing, road grime, deploy did nothing, cannot find my files, everything grey although I picked a colour, some drivers see grey, price, piracy, real car / 3D print, new season cars, privacy / AI training, "are you a bot", TGA bit depth, manual copy + file name, same paint on two cars, 4096, where the spec file goes, matte black, save a look for reuse, UI too big, send the paint to my driver, spec over my logos.
- Guard sets (`search_lab/r5.js`, shared): dev 91.7 = 91.7, held 87.4 -> 87.9, h2 78.7 = 78.7, h3 73.6 -> 74.7, ctune 76.2 = 76.2, ctest 67.6 -> 68.0, para/r5p/r5m unchanged. No drop.
- **Content** (`ql/ql_patches.py` via `ql/ql_apply.py`, format-preserving, logged in `ql_apply_log.jsonl`): 10 summaries rewritten so the answer text carries the fix (support.not_in_iracing, support.flat_or_shiny, support.colours_differ, zones.not_showing, preview_render.render_slow, support.smeared_blobby, four generated help pages whose summary was one stray sentence: help_support_1.output_folder / trading_paints / ai_setup / size_2048); 7 FAQs + 1 mistake (half glossy half matte, teammates see different colours, saturated in the sim, copy the TGA myself, where the spec goes, TGA bit depth, ghost pattern in preview only). Facts checked: engine/core.py write_tga_24bit (paint) / write_tga_32bit (spec) via shokker_engine_v2.py:20845-20846.
- Train after round 1 (tag ql2): trouble 6 -> 16/48, iracing 9 -> 12/27, howto 26 -> 29/54, edge 2 -> 4/19, question 28 = 28, vague 5 = 5; harm items 9 = 9; A-kind items unchanged except a convo flip that comes and goes with the S3 worker's concurrent edits.

## Rounds 2-4 (2026-10-06)
- **Ranker rows.** The R6 block now holds 51 rows.
  - New: WHEREGO, ZONEPART, SPECDEF, ANGLE, NUMDRV, TEAMPC, WHATBASE, SPECSEE (excludes "spec value"), PAYALL, PAINTBOTH, LOGIN, WHOLEJOB, REALTRACK, FIRSTPAINT, SHEENVS, SPECPAT, NOIDEA, ZONELAYER, RENAME, RENDEREVERY, WHEREFILE.
  - Fixed: NEWCARS ("new iRacing season cars"), REALCAR, GREYPICK (it fired but its words were too weak), SENDDRV, MATTEBLK, WEARSIM, STALEPREV.
  - ZONESPLIT's "part ... and part" branch moved into ZONEPART.
- **Content.** Every claim restates a fact already in the same or a sibling article, or one checked in code.
  - Definition-form summaries: spec.overlays_stack; zones.priority (now adds reorder and Everything Else).
  - FAQs added:
    - finishes.base_compare: matte vs satin, using values from its own sheen ladder.
    - patterns.what_is_a_pattern: finish vs pattern.
    - zones.what_is_a_zone: zone vs layer.
    - spec.channel_b_clearcoat: what clearcoat is.
    - help_howto_3.what_is_spec: a separate texture, with the alpha as the specular mask.
    - workflows.user_id_and_folder: why the ID is in the file name.
    - preview_render.preview_vs_render: do I have to render every time.
    - concepts.preview_vs_truth: is the preview lying.
    - zones.everything_else: the bottom of the car is the wrong colour.
    - zones.priority: which zone wins.
    - preview_render.render_history_stats: render history is empty.
    - preview_render.output_files: bit depth.
    - cars.choose_template: the same paint on two cars.
    - workflows.platform_and_limits: painting a real car.
  - Aliases added:
    - real car, my real car, paint my real car, real vehicle
    - matte vs satin, plus 4 more
    - japan style, japanese style, cherry blossom(s)
    - old renders, previous renders
    - Skipped "render history" because tools.undo_redo owns it.
  - Six FAQs that pulled the wrong article to rank 1 were moved to the gold article, using the new `faq_drop` key in ql_apply.
- **Maintenance found by the gates (not caused by this lane).**
  - An engine edit (+42 lines in shokker_engine_v2.py) left 4 stale cites in finishes.json (cited-without-anchor 4). I moved each by +42 after checking the line text is identical: 20467->20509, 22944->22986, 23013->23055, 23354-23380->23396-23422.
  - flame_licks.flame_job failed `--depth` (screens>=1). Fixed with a surgical `"screens": ["cat_flames"]`. The file is hand-formatted, so enc_reader_fix calls it UNWRITABLE; it rejected `pair_zone_added` as a wrong picture.

## FINAL (2026-10-06)
### Tier 1, before -> after
Both runs use one snapshot of the helper code; only this lane's files are swapped.

| split / kind | before | after | app-faithful (qbank loaded) before -> after |
|---|---|---|---|
| train items | 173/615 | 206/615 | 173 -> 204 |
| B:trouble | 6/48 | 19/48 | 7 -> 19 |
| B:iracing | 9/27 | 14/27 | 9 -> 14 |
| B:howto | 26/54 | 32/54 | 25 -> 30 |
| B:question | 28/48 | 34/48 | 28 -> 34 |
| B:edge | 2/19 | 4/19 | 2 -> 4 |
| B:vague | 5/35 | 6/35 | 5 -> 6 |
| B:qa_convo | 0/17 (t39.2) | 0/17 (t39.2) | 0 (t33.3 -> t35.3) |
| A:convo / A:edit | 37 / 60 | 37 / 60 | 37 / 60 |
| harm items (train) | 9 | 9 | 9 -> 9 |
| DEV (checked at end) | 47/186 | 47/186 (0 items flipped) | 46 -> 46 |

- **Dev did not move.** On dev, B turns fail mostly on cover (52) and gold (29). The train rows did not generalise to dev phrasing. The next lever is content depth plus the routing fixes below, not more rows.
- **Grader fidelity gap.** grade_offline.js never loads js/spb-enc-qbank.js, while the app and the Python mirror do. The app-faithful column used `ql/runs/grade_qb.js`, a copy with that one line added. Fix for the grader's owner: add `run('js/spb-enc-qbank.js');` after `run('js/spb-enc-search.js');` on line 28.
- **A-0250 flip.** In the ql5 run, A-0250 turn 3 went from change to ask. That comes from concurrent helper-code edits: it passes with the snapshot helper code and this lane's final files.

### Gates (all green)
- **Helper gates:** helper_eval 297/297, builder 136/136, ft2 35/35, edit_corpus 0 mismatches, stack 108/108, convo dev 18/18 and held 15/15 (`search_lab/gates_final.txt`).
- **Encyclopedia gates:** enc_test 27/27, enc_v2_test --final all PASS, --depth all PASS, enc_reader_smoke 128/128.
- **Parity:** rewrite 2103/2103, search 69/69, enc_parity 1689/1689 = 100%, lane parity (all B-bank turns, JS vs Python top-1) 464/464. That last check also fed sealed turns through both rankers; only the mismatch count was read, with no scoring and no tuning.
- **Stale refs and hidden features:** enc_stale_refs_check PASS, hidden_feature_check -q PASS.
- **Guard sets:**
  - dev 91.7, unchanged
  - held 87.4 -> 87.7
  - h3 73.6 -> 74.7
  - ctest 67.6, unchanged
  - ctune 76.2 -> 75.8: the one loss is "satin vs matte", which now goes to finishes.base_compare instead of the labelled help_howto_2.make_matte.

### Sync and cache
- Synced js/spb-enc-search.js and js/spb-encyclopedia-data.js to electron-app/server.
- encyclopedia_routes.py is unchanged. The Python mirror reads the rows from the JS and rebuilds when the file changes, so no restart is needed.
- ?v= tokens in both html copies: `20261006ql1` (enc-search) and `20261005gap1-fl1-ql1` (encyclopedia-data).

### In-app spot check
Server 59880, own headless Chrome on CDP 9987 (closed afterwards). Results in `ql/inapp_spot.jsonl`, shots in `ql/inapp_shots/`.
- **Correct (7):** file name, where is my file, real car, clearcoat, preview lying, bit depth (the new FAQ is shown), where do I see the spec map.
- **Weak (3):**
  - matte vs satin -> ideas.satin_modern_oem, because the qbank pulls it.
  - "do my teammates need to buy shokker" went ONLINE (DeepSeek, $0.0062). The offline top-1 scores 18.1 with cov 0.53.
  - "my car in iracing is just white after I render" opened the Step builder as "The whole car -> White". This is a prefill: nothing changes until Run.
- I looked at 3 panels (white, sheen, teampay). A stale Step builder card stays open under later answers.

## Routing misses for S3 / S6 (files I may not edit)
1. **Symptom statements become edits or asks.**
   - Items: B-0162, B-0178, B-0190, B-0195, B-0200, B-0214, B-0225, plus the in-app "white after I render". The gold is at rank 1 with cov 0.6-1.0.
   - Fix in js/spb-offline-answer.js: add to SYMPTOM_RE (~line 990): `|\b(?:is|looks?|shows?|went|turned|comes? out)\s+(?:just\s+|all\s+|completely\s+)?(?:white|blank|grey|gray|black|backwards|mirrored|reversed|dull)\b[^.]{0,40}\b(?:iracing|sim|render(?:ed)?|rendr|in game|after)\b|\b(?:iracing|sim)\b[^.]{0,30}\bstill shows? (?:the )?(?:old|previous|default)\b|\bwire ?lines?\b[^.]{0,30}\bon (?:my )?(?:render(?:ed)?|paint)\b|\bweird holes\b`
   - Also run the SYMPTOM_RE + confident(top,'question') answer BEFORE the builder/frame claim.
2. **Plastic/toy pin.** The plastic pin (~line 1212) should lead with `support.looks_plastic`, then support.flat_or_shiny. Fixes B-0196, B-0209, B-0309.
3. **"stock car" read as off-topic.** In CHAT_RE (line 214), replace `stock` with `stock(?!\s*cars?\b)`. Fixes B-0274.
4. **New season cars read as off-topic.** For B-0273, kind() returns 'chat' and APP_WORD_RE misses it, so it goes to local offtopic (~line 1532), although the top hit is cars.teach_parts at 15.0. Fix: add `iracing|cars?` to APP_WORD_RE, or skip chat -> offtopic when the top score is >= 12.
5. **Goes ONLINE although the offline top-1 is gold.** Items: B-0167, B-0236, B-0247, B-0253, B-0263, B-0360, plus the in-app teammates question. Fix: in kind(), treat a message as a question if ANY sentence ends with "?" or starts with Q_START; then answer offline when score >= 14 and cov >= 0.5.
6. **Asks although the gold is rank 1.** Items: B-0003, B-0163, B-0180, B-0225, B-0272, B-0364. Fix: a why/how question whose top-1 scores >= 13 should get an answer, not an ask.
7. **v3-verify asks on pure questions.** Items: B-0057, B-0176, B-0234. Fix: skip the verifier when the reply is an answer card.
8. **Answers where the bank wants one clarifying question.** Items: B-0165, B-0171, B-0181, B-0206, B-0217, B-0222, B-0287. Ask "which car / what do you see" first.
9. **Stale Step builder card.** Close the old builder card when a new turn is answered.

## DEPTH 1 (2026-10-06) - deeper article text for the answer class (content only, no js/server/bank edits)
Scope: `data/encyclopedia/*.json` through `build_encyclopedia.py`; patches in `_easy_claude_work/search_lab/d1/d1_p01..p06.py` (applied by `d1_apply.py`, backups in `d1/backup/`). Method: train B-kind turns failing on missing key points, grouped by article; the answer card shows title + best FAQ answer (or the summary) + action labels, so the lever is a dense summary (<=260 chars, <=2 sentences) plus natural FAQ question variants, plus aliases for wrong-article routing. Dev was not read while writing; one dev run at the end.

Results (tier 1, tag d1_base -> d1_r6 train; dev s4post -> d1_final):
- TRAIN items 206 -> 255 /615; turns 469 -> 522 /1053; gold 171 -> 177 /243; cover 136 -> 188 /260; harm-flag items 9 -> 9.
- Train per kind: B:howto 32 -> 51 /54 · B:question 34 -> 44 /48 · B:iracing 14 -> 21 /27 · B:edge 4 -> 12 /19 · B:trouble 19 -> 23 /48 · B:vague 6 -> 5 /35 (ranker side effect, unfixed) · B:qa_convo 0 -> 2 /17 · A kinds unchanged.
- DEV items 47 -> 49 /186; turns 117 -> 119 /305; gold 49 -> 51 /78; cover 32 -> 33 /84; harm items 6 -> 6. Per kind: B:howto 5 -> 6 /18 · B:iracing 0 -> 1 /4 · B:trouble 3 -> 4 /16 · B:question 10 -> 9 /14 (one lost, not tuned: dev is not read) · others unchanged. Smaller than train: train content was written to its class, so some of the train gain is wording-specific.

Articles changed (62): ai_copilot.{chat_mode, edit_existing, gear_key_model, mcp_claude_chatgpt, offline_vs_ai, what_ai_sees}; cars.{choose_template, reading_sheet, supported_cars, teach_parts}; concepts.what_makes_a_finish_good; finishes.{base_compare, four_kinds, second_base_overlays}; help_howto_1.finish_one_part; help_howto_2.look_differs; help_howto_3.{spec_sculpt, ui_size}; help_support_1.{about_me, ai_privacy, output_folder}; help_topics_1.{add_zone, ai_key, gradient}; layers.export_photoshop; patterns.layers_and_stacking; playbook.{buyer_words, livery_parts}; preview_render.{export_psd_photoshop, number_modes, output_files, preview_vs_render, render_slow, trading_paints_mip}; recipes.{add_race_number, artwork_on_car, glow_look, gradient_roof_rocker, named_looks, team_liveries, two_tone, weathered}; spec.{angle_reveal, channel_a_mask, channel_r_metallic, overlays_stack, what_is_spec_map}; spec_sculpt.{smart_separate, three_modes}; support.trading_paints; tools.zoom_pan; ui_shell.{car_folder, panels_and_ui_size}; workflows.{business_and_sharing, loading_paint, platform_and_limits, six_words, what_is_shokker}; zones.{add_pick_colour, priority, restrict_layers, what_is_a_zone}.

Facts used (all taken from the same or sibling articles that already carry source cites, or code): number modes and files (car_ID.tga = Sim-Stamped, car_num_ID.tga = Custom, spec only as .mip on Trading Paints; `preview_render.number_modes` + `preview_render.trading_paints_mip`); mip detail loss `engine/color_science.py:396-399` (mip_survival); Alt+Tab then Ctrl+R and "preview updates by itself, re-render is quicker" (`preview_render.render_slow` body); MCP: control option in the AI gear, Install in Claude Desktop, ~27 tools; offline helper sends nothing, AI key sends a text summary (+ sometimes the preview); no refund/selling/training terms are stated in the app, so answers send people to support (Report a Problem) and never invent them; the "Update My Own Paints" Trading Paints option is named as a thing to look for, with an explicit "I do not know the exact menu" note. Dropped on purpose: a "render at 1024 for tests" claim (no such option found in the UI).

Also fixed so the gate is green: the flame-shelf rework changed the text of finish-data lines 878-897, so the 7 flame anchors in `scripts/ai_atlas/enc_source_anchors.json` were shortened to `{ id: "flame_x", name: "..."` (stable against desc edits), and the cite `shokker_engine_v2.py:23354-23380` (drifted by 1 line; regenerated by `scripts/ai_atlas/enc_wear_fix.py` on each build) was changed to 23355-23381 in that script, the drafts and finishes.json.

Not fixable here (JS routing, listed above): ~26 train turns where the helper asks/declines instead of answering (B-0162/0163/0167/0176/0178/0180/0189/0190/0195/0200/0205/0210/0214/0215/0225/0234/0236/0247/0263/0264/0272/0351/0353/0360/0364/0365) and 8 where it answers but the bank wants one question (B-0165/0171/0181/0206/0217/0222/0259/0368).

Gates (all green): enc_test 27/27; enc_v2_test --final and --depth all PASS (6178 articles, anchors 2624 ok); enc_reader_smoke 128/128; helper_eval 297/297; enc_stale_refs_check PASS; hidden_feature_check PASS. Two-copy: `js/spb-encyclopedia-data.js` copied to electron-app/server (identical; there is no electron-app/server/data/encyclopedia copy); `?v=` token now `20261005gap1-fl1-ql1-d1` in both paint-booth-v2.html copies.

## DEPTH 2 (2026-10-06) - content-only pass on the B:trouble / B:vague / B:qa_convo / B:edge failures

Scope: `data/encyclopedia/*.json` via `_easy_claude_work/search_lab/d2/` (`d2_p01..p03.py`, `d2_apply.py`, backups in `d2/backup/`, `PROGRESS.md`, probe + diff helpers `probe.js` / `diff.py`). No js, server, bank-item or split edits. Dev was not read while writing; run once at the end (numbers only).

Finding that sets the ceiling: of the 87 failing B turns in these four kinds, about 75 fail in JS routing (the helper asks / declines / pre-fills the builder / goes ONLINE / the PIN table forces `support.flat_or_shiny` instead of answering). Content can only move turns that already reach an answer card, plus a few ONLINE/no-article turns whose top hit just needs more coverage to count as "confident". B:trouble is therefore almost entirely a routing problem (24/48 -> 24/48 here; B-0236 gained, B-0196/B-0209 cannot because the gold id never enters the pinned hits).

Results (tier 1, tag d2_base -> d2_final_train, train):
- TRAIN items 255 -> 268 /615; turns 522 -> 534 /1053; gold 177 -> 184 /243; cover 188 -> 199 /260; harm-flag items 9 -> 9.
- Per kind: B:vague 5 -> 11 /35 (the D1 side effect was exactly one item, B-0283: the D1 `recipes.team_liveries` FAQ answered a league-theme question with "same files look the same on every PC"; fixed) | B:edge 12 -> 14 /19 | B:qa_convo 2 -> 3 /17 | B:trouble 23 -> 24 /48 | B:howto 51 -> 52 /54 | B:question 44 -> 46 /48 | B:iracing 21 (unchanged) | A kinds unchanged.
- DEV (once, tag d2_final): items 49 -> 48 /186 (d1_final -> d2_final); turns 119 -> 118 /305; gold 51 -> 52 /78; cover 33 -> 32 /84; harm items 6 -> 6. Per kind: B:trouble 4 -> 3 /16 (one item lost, not looked at: dev is unread); every other kind identical to d1_final. So the train gain (+13) did not transfer, and there is one dev loss. Likely suspects for the trouble loss (both are train-specific FAQs that gained nothing on train): the three FAQs added to `support.flat_or_shiny` (toy / TP-upload / night paints) and the aliases on `zones.tolerance`. If the S6 worker wants it undone: `faq_drop` those questions in a d2 patch.

Articles changed (17): help_support_1.about_me, recipes.team_liveries, ideas.racing_green_heritage, playbook.composition_rules, ideas.black_gold_luxury, recipes.artwork_on_car, support.flat_or_shiny, zones.tolerance, ai_copilot.can_and_cannot, ideas.pastel, playbook.scheme_families, ideas.neon_night, ui_shell.save_open_projects, ai_copilot.mcp_claude_chatgpt (alias only), finishes.catalogue_overview, spec.overlays_stack (aliases only), recipes.carbon_hood. Gains by item: B-0236 B-0283 B-0297 B-0300 B-0312 B-0320 B-0333 B-0346 B-0360 B-0387 (+B-0036 B-0098 B-0146 in B:howto / B:question).

Facts used (all from sibling articles with cites, no new menus, prices or refund terms): team colours = main colour + accent + trim, same hex on every car (`ideas.team_colours`), style menu (`ideas.style_menu`), one master project + a variant per car (`recipes.team_liveries`); racing green / pearl / satin / sponsor-friendly plain doors-hood-rear (`ideas.racing_green_heritage`, `ideas.pearl_white`, `ideas.satin_modern_oem`, `ideas.sponsor_friendly_bases`); 60/30/10 hierarchy and clean-classy (`playbook.composition_rules`, `ideas.clean_classy`); black + gold + chrome accents on trim only (`ideas.black_gold_luxury`, `ideas.chrome_show_car`); logo as a PNG via + Layer / Move (V) / Transform, exact hex in BASE COLOR (`recipes.artwork_on_car`, `playbook.colour_matching`); edge halo = colour tolerance 10-16 for dark fills beside black strokes, Refine selection (`zones.tolerance`, `tools.refine_selection`); helper does steps with Undo, cannot open/save/export (`ai_copilot.can_and_cannot`, `history.panel`); pastel finishes (`ideas.pastel`); Neon night + Wet Look (`ideas.neon_night`, `ideas.look_wet`); Open in the toolbar vs Import Recipe (`ui_shell.save_open_projects`); TP spec is a .mip (`preview_render.trading_paints_mip`); spec pattern = shine channels, paint pattern = colour, up to five overlays (`spec.overlays_stack`); 4,137-finish catalogue in shelves (`finishes.catalogue_overview`). Dropped on purpose: smart-object handling (B-0380: no article states it, so nothing invented) and any "UV sheets" claim (reworded to "I read the flat sheet from a text summary" per `ai_copilot.what_ai_sees`).

Gates (all green, run after the last build): enc_test 27/27; enc_v2_test --final and --depth all PASS (6178 articles, anchors 2624 ok); enc_reader_smoke 128/128; helper_eval 297/297; enc_stale_refs_check PASS; hidden_feature_check PASS. Two-copy: `js/spb-encyclopedia-data.js` copied to electron-app/server (identical); `?v=` token now `20261005gap1-fl1-ql1-d1-d2` in both paint-booth-v2.html copies.

Routing misses for the S6 worker (JS only; content cannot fix; all verified by probing `OA.route` with the current encyclopedia, gold at search rank 1-3 unless noted):
1. **v3 verifier asks on questions/statements that the search answers confidently.** ASK(v3-question) with the gold article at rank 1: B-0176 (chrome looks grey), B-0234 (Auto-pop worse), B-0330 (neon_night 32.8/cov 1.0 after D2), B-0305, B-0057. Fix: skip the v3 `question` verdict when the search top is confident (score >= 10 and cov >= 0.5) or when the text has no edit verb.
2. **ASK(same) on a stray word "same".** B-0163 ("Same files"), B-0225 ("wanted the same all over"), B-0299, B-0397. Fix: SAME_RE2 must only fire when the message is short (<= 4 words) or starts with "same"; otherwise route as a question.
3. **ASK(which-part) on "more saturated / old colour" symptoms.** B-0180, B-0205, B-0215. Fix: apply SYMPTOM_RE (colours differ / still shows old) before the edit-claim path.
4. **Symptom statements pre-fill the builder (PREFILL).** B-0162, B-0178, B-0189, B-0190, B-0195, B-0200, B-0214, B-0326, B-0335, B-0339 (same SYMPTOM_RE fix as DEPTH 1 item 1, which is still open).
5. **Plastic/toy PIN picks `support.flat_or_shiny`** and the gold `support.looks_plastic` never enters the hits: B-0196, B-0209, B-0309 (pin line ~1212: lead with looks_plastic, and for "night / lights" skip the pin).
6. **Entity pin (add_logo) beats the artwork recipe**: B-0313 ("matches our team logo, I'll upload it") -> `help_howto_1.add_logo`; gold `recipes.artwork_on_car` is search rank 1 (23.1).
7. **Goes ONLINE although a gold article is rank 1-3**: B-0167 ("... I am very sad" splits into clauses -> free-design), B-0360 fixed by content, B-0308, B-0236 fixed by content, B-0399 turn 3.
8. **List-wanted vague turns land on the builder/ASK with generic chips**: B-0290, B-0294, B-0296, B-0302, B-0311, B-0316, B-0318 (ideas.* hits exist at rank 3-5): when the text has no edit verb and no part, answer with the top 3 `ideas.*` titles as a list.
9. **Context turns with no context**: B-0376 "how", B-0378 "so what now", B-0394 "what can it do" go to local.offtopic / offline_vs_ai because the search sees only stop words; carry the previous turn's topic into the query.
10. Remaining D1 routing list (ask-vs-answer, v3-verify, stale builder card) is unchanged.

## DEPTH 3 (2026-10-06)

Method: DEPTH 1/2 patch scripts (`_easy_claude_work/search_lab/d3/`, `d3_p01..p05.py`, applied additively on the restored base by `run.sh`, backups in `d3/backup/`), tuned ONLY on `train_aug` items ending `-p1` in B kinds question/howto/trouble/iracing/edge/vague/qa_convo (248 items); `-p2` (held-out) and `--split train` were checked every round and nothing that lowered either was kept. 5 rounds used (r6 rejected).

Results (B-kind, /248; frozen copy of S6's offline-answer.js from round 2 on because S6 edited the JS mid-run; the final numbers are identical against the real JS):
- p1: 81 (pre-S6 baseline) / 99 (same data, S6 JS) -> **156**
- p2 (held-out): 110 / 117 -> **137**
- train (B kinds): 182 / 183 -> **191**
- Whole train_aug 367/1230 -> 478/1230; train split items 298 -> 305/615; harm-flag items unchanged (train 9; train_aug 63 -> 61). Part of the early baseline gain (81 -> 99) is S6's JS, not content; the content effect is 99 -> 156 p1 (+57), p2 +20, train +8. p1 gained far more than p2, so a good share of the p1 gain is fit to p1 phrasing; p2 +20 and train +8 are the honest generalising part.
- Round log: r1 124/127/187, r2b 135/131/189, r3b 149/135/189, r4 156/137/188, r5 156/137/191.

Articles changed (79, data/encyclopedia/*.json, aliases/FAQ variants/denser <=260-char summaries): ai_copilot.chat_mode, gear_key_model, offline_vs_ai; cars.interior_and_dashboard, reading_sheet, supported_cars, wheels_and_rims; concepts.preview_vs_truth; finishes.astra, base_compare, colour_source_modes, foundation_shine_only, ghost_geometry_clearcoat, wear; help_support_1.about_me, ai_privacy; ideas.chrome_show_car, liquid_metal, rat_rod; layers.export_photoshop, opacity_blend, paintable_area, wire_mask_mandatory; patterns.layers_and_stacking, paint_mode, what_is_a_pattern; preview_render.auto_deploy, output_files, reload_in_iracing, render_button, render_history_stats, render_slow, saving_projects, trading_paints_mip, where_files_go; recipes.add_race_number, artwork_on_car, gradient_roof_rocker, holographic, named_looks, night_day, team_liveries, weathered; settings.activation_license; shokk_drop.shokk_library_files, what_is_shokk_drop; shortcuts.table; spec.auto_pop, channel_a_mask, channel_b_clearcoat, channel_r_metallic, what_is_spec_map; spec_sculpt.three_modes, what_is_spec_sculpt; support.colours_differ, flat_or_shiny, image_files, looks_plastic, lost_files, psd_wont_open, smeared_blobby, trading_paints; tools.mask_vs_layer; ui_shell.car_folder, template_layer_views; workflows.business_and_sharing, first_paint, iracing_side, platform_and_limits, pro_or_chat, six_words, tutorial_quests, user_id_and_folder, view_in_3d, what_is_shokker; zones.everything_else, priority, tolerance, what_is_a_zone.

Facts and sources: every new sentence restates a fact already in a sibling article (cites kept), e.g. 31 checked templates + 7 drafts (cars.supported_cars), Chrome = metal 255 / roughness 2 / coat 16 and Primer metal 0 / roughness 215 / coat 200 (ideas.chrome_show_car, ideas.rat_rod), alpha = lighting mask 255 normal (spec.channel_a_mask), render gives up after 5 / Terminate (preview_render.render_slow), files named with the Customer ID and not to be renamed (preview_render.output_files), Ctrl+R in iRacing (preview_render.reload_in_iracing), Shokk Drop accepts PNG/JPG/WebP/TGA/BMP (shokk_drop.what_is_shokk_drop), higher zone wins a pixel / Ctrl+Up (zones.priority), TGA 24-bit paint vs 32-bit spec alpha (support.image_files). No new menus, prices or refund terms. Two honest "not stated" answers: AI training policy (help_support_1.ai_privacy points to support) and piracy ("cracked version", settings.activation_license declines).

Gates (final data, real JS, all green): enc_test 27/27; enc_v2_test --final and --depth all PASS (6178 articles); enc_reader_smoke 128/128; helper_eval 297/297; enc_stale_refs_check PASS; hidden_feature_check PASS. js/spb-encyclopedia-data.js copied to electron-app/server/js/; `spb-encyclopedia-data.js?v=` is now `20261005gap1-fl1-ql1-d1-d2-d3` in both paint-booth-v2.html copies.

Traps found: (a) patches are additive, so restore the base before every apply; (b) FAQ questions containing problem words (why, wont, not...) are never shown unless the user text has one; (c) a "preview misleading" FAQ on support.colours_differ stole B-0148-p2 from its gold concepts.preview_vs_truth, so FAQs belong on the gold article; (d) a `support.render_slow_or_fails` FAQ made the "spinner" turn (B-0201) route to DECLINE via ART_NOUN, so it was dropped; an alias for it was also rejected (p2 -1, train -1); (e) B-0100-p2 flips to about_me through a non-additive interaction (no single group fixes it).

Routing misses for S6 (gold article is in the search top 3 but the route is not an answer; content cannot fix):
- DECLINE instead of ANSWER: B-0009 B-0070 B-0079 B-0084 B-0127 B-0139 B-0185 B-0190 B-0197 B-0247 B-0254 B-0272 B-0299 B-0300 B-0353 B-0367 (B-0201 "spinner": ART_NOUN regex fires once the render-fail article is on top; narrow it so "render spinner" is a symptom, not artwork).
- ASK instead of ANSWER: B-0046 B-0064 B-0078 B-0080 B-0082 B-0085 B-0090 B-0128 B-0134 B-0141 B-0153 B-0172 B-0251 B-0255 B-0326 B-0330 B-0337 B-0339 B-0355 B-0386 B-0394 (fix: answer when the top hit is confident and the text is a question or symptom; the D2 list items 1-4 still apply).
- CHANGE/nothing instead of ANSWER: B-0072 B-0395.
- ANSWERED but an ASK was wanted: B-0165 B-0181 B-0206 B-0217 B-0222 B-0259 B-0288 B-0307 B-0321 B-0378 B-0392 B-0397 B-0399.
- Gold not in top 3 and routed ask/decline/list (vague/qa_convo, needs context or a list route): B-0171 B-0174 B-0205 B-0225 B-0226 B-0283 B-0287 B-0289 B-0290 B-0294 B-0296 B-0297 B-0298 B-0302 B-0304 B-0305 B-0310 B-0311 B-0312 B-0316 B-0318 B-0323 B-0328 B-0365 B-0368 (vague 7/35 and qa_convo 2/17 on p1 are the weakest kinds: bare words like "so what now" need conversation context, not content).


## DEPTH 4 (2026-10-07) - encyclopedia retrieval at scale (content only; no js, bank or grader edits)

Method: `_easy_claude_work/search_lab/d4/` (`retr.js` = the app's own `SpbOfflineAnswer.search` over the 8,051 answer/decline rows of `eval/corpus/corpus.jsonl` that carry gold_ids; `an.py` / `summ.py` / `cand.py` / `mine.py` analyse; `run.sh TAG` = restore the post-D3 data, apply `d4_p01..p04.py` in the D3 patch format, build, grade B-kind p1/p2/train with a FROZEN copy of S6b's `spb-offline-answer.js` taken at session start, then run the corpus; `bisect.sh` finds the entry that flips a B item). Per-batch log: `d4/PROGRESS.md`. Mining used only plain / polite / rude / slang / phone rows (typo, esl and ramble rows are never mined: a typo is a ranker problem, not an alias). Aliases carry no facts; the 11 FAQ answers restate that article's own summary. No dev / sealed / blind6 / p2 item text was read; p2 was scored every round, dev twice (base and final).

Before / after (frozen S6b JS, same data otherwise; top-1 = any gold id at rank 1, top-3 = any gold id in the first 3):

| set | n | top-1 before | top-1 after | top-3 before | top-3 after |
|---|---|---|---|---|---|
| corpus, all answer rows | 8051 | 61.4 | **66.6** | 78.5 | 83.6 |
| answer-act rows (no list/save/decline) | 7213 | 67.1 | 71.8 | 83.7 | 87.6 |
| knowledge rows (faq / alias / symptom / seed) | 5553 | 68.5 | 73.1 | 86.8 | 90.4 |
| how-to rows | 1517 | 65.2 | 69.7 | 75.9 | 79.9 |
| para (hand-written, never mined) | 219 | 65.3 | 69.4 | 83.1 | 85.8 |
| seed | 500 | 67.8 | 71.0 | 89.6 | 90.4 |
| B-kind p1 / p2 / train (of 248) | | 169 / 151 / 206 | 169 / 152 / 206 | | |
| dev items (2 runs only) | 186 | 81 | 81 | | |

The D3 figure "p2 137" was measured before S6b's JS; with S6b's JS the D3 data already scored p1 169, p2 151, train 206. The target p2 >= 170 was NOT reached (p2 +1). No batch was kept that lowered p1, p2 or train.

Why 85 % top-1 is not reachable by content (misses after batch 4, 2,687 rows; buckets are exclusive, in this order):
- 872 rows (10.8 pts) are not article-retrieval questions: list ("show me options for the hood", gold ideas.style_menu / finishes.base_compare), save/export commands ("send it to the sim", gold render_button / auto_deploy / where_files_go), decline (windows, wheels, brake calipers), preview. The app routes these to a list, a button pointer or a decline, never to the article.
- 439 (5.5 pts) typo / esl rows and 335 (4.2 pts) ramble rows lose to words in the noise, not to missing content.
- 131 (1.6 pts) slot how-to rows ("put chevrons on the front bumper how", "make the bonnet navy how") whose gold is a catch-all article (patterns.what_is_a_pattern, ai_copilot.picking_colours_in_words, finishes.base_compare); the winner (recipes.carbon_hood, help_howto_1.add_pattern ...) is usually a better answer, so no alias was added.
- 759 (9.4 pts) have the gold in the top 6 behind a sibling that answers the same question just as well (older help_howto_* / help_topics_1 / help_support_1 pages, recipes.retro_stripes vs ideas.racing_stripes, support.trading_paints vs preview_render.trading_paints_mip ...). The corpus labels the FAQ/alias OWNER, not the best answer, and 20 verbatim questions are owned by two articles; grade these top-3.
- 78 (1.0 pt) gold absent; 42 (0.5 pt) car_pages.*: `OA.load` does not load `car_pages.json`, so "what is the folder for protrucks pro2lite" can never hit. That is an index/loader item (S6b), not content.

What was fixed by content: aliases for the vocabulary the plain corpus rows use on the support.* symptom articles, how-to / export / save wording (recipes.*, preview_render.render_button / auto_deploy / where_files_go, ui_shell.save_open_projects), and a second and third tier of articles in zones / spec / spec_sculpt / ui_shell / tools / workflows / ideas / layers.

Findings for S6b / the ranker owner (files I may not edit):
1. RAMBLE rows: top-1 31 % (188/598) when the whole text is searched, 54 % (322/598) if each clause (split on . , ; ! ? and "anyway", at least 3 words) is searched and the clause with the highest-scoring best hit wins (`d4/ramble.js`, +1.7 pts overall). 154 of the ramble misses are won by recipes.team_liveries purely on the preamble words "team" / "league" / "my team lead".
2. Words missing from `SpbEncSearch.STOP`: "teach", "tips", "steps", "walk through" ("any tips on how to make the car holographic" lands on finishes.what_makes_a_finish_pop, "teach me how to make camo" on cars.teach_parts).
3. Compare questions ("candy versus chrome which one", "pearl or metallic") are won by the single-finish recipe; a "versus / or / difference" boost toward finishes.base_compare would fix about 130 rows.
4. `OA.load` file list lacks `car_pages.json` (42 corpus rows).
5. Routing: `d4/routing_misses.json` lists 1,179 rows (of 6,054 answer-act rows whose gold IS in the search top 3) that route() sends somewhere other than ANSWER: ASK 310 (unclear 146, which-part 67, same 43), ONLINE 304 (unknown 164, free-design 123), PREFILL 296, DO 269 (DO(none) 218: "want mud effect", "brushed aluminium bare metal like a prototype", "what separates pearl from metallic"). A further 966 rows ANSWER with an article that is not one of the gold ids (mostly acceptable siblings). Fix: when the text is a question or symptom and the top hit is confident, answer instead of ASK / ONLINE / PREFILL / DO.

Traps: (a) B-0025-p1 is knife-edge: it passes only while recipes.matte_black owns "flat black on the entire car" and flips with the NUMBER of aliases added elsewhere (no single entry is to blame); (b) aliases such as "iracing shows a grey car", "white in the sim", "everything looks duller in iracing" flipped B-0208 / B-0222, "am i talking to a human or a bot" / "can it add text" on can_and_cannot flipped B-0346, and "the render spinner never stops" repeated the D3 trap (d) and lost B-0201; all were dropped; (c) FAQs add almost nothing next to aliases (+0.1 pt for 11 FAQs); (d) `data/encyclopedia/_drafts/` and spec_sculpt.json were intermittently locked on Windows (PermissionError / OSError 22 in the build): `restore.py` / `d4_apply.py` retry, and the build must be re-run until its last line starts with "encyclopedia:"; (e) the build rewrites line numbers in `sources` of ~10 controls pages (anchor repair after other lanes edited paint-booth-v2.html), which is expected.

Gates (final data, real JS): enc_test 27/27; enc_v2_test --final and --depth all PASS (6178 articles); enc_reader_smoke 128/128; helper_eval 297/297; enc_stale_refs_check PASS; hidden_feature_check PASS. `js/spb-encyclopedia-data.js` copied to `electron-app/server/js/` (identical); `?v=` token now `20261005gap1-fl1-ql1-d1-d2-d3-d4` in both paint-booth-v2.html copies. Articles touched: 109 (279 aliases, 11 FAQs, 0 new articles) in ai_copilot, finishes, history, ideas, layers, patterns, playbook, preview_render, recipes, settings, shokk_drop, shortcuts, spec, spec_sculpt, support, tools, ui_shell, workflows, zones.
