# PUSH-HOLDOUT - held-out number for js/spb-self-help.js (2026-10-03)
Files: _easy_claude_work/stuck_holdout.json (60 q, written BEFORE reading stuck_questions.json; ids looked up after), _easy_claude_work/selfhelp_holdout_test.js (run: node it; prints every miss + 120-char head).

## Number
Raw cite-any: 27/60 = 45% (in-sample 89%). Answerable-only 24/50 = 48%. Three false misses (test artefacts: H18 and H49 cite the right control by its short id, H53 honestly says "no 3D view") -> adjusted 30/60 = 50% / 26/50 = 52%. Guards 22/22 and chips PASS. Unanswerable 10: honest/unclaimed 4, bogus answer 6 (see below). The 89% was heavily in-sample; real held-out is roughly half.

## Miss classes (33 raw misses)
- Not claimed by any brain, 14: nobody owns 9 (H11 file opened blank, H25 work gone, H28 little eye, H29 easy vs pro, H31 sponsors blurry under chrome, H34 jagged selection, H42 top buttons, H46 copy a photo, H50 part missing from list); support/ingame/preview/look checklist claims 3 (H10, H16, H22); order/edit brain claims 2 (H5 "keeps undoing my color", H48 "candy apple red").
- Right-ish intent, wrong entry/control, 8: H15 sponsors->decal_rescue (want add_logo), H17 stripes->add pattern (want zone/draw_area), H19 flames size->add pattern, H27 flake down->pick finish, H30 stuck in easy->use_easy (want easy_to_pro), H39 text->finish_one_part (want add_text), H1/H7 -> generic why_not "nothing obvious is blocking it" instead of render_wont_start / grey-car.
- Wrong intent (fell to generic "stuck" checklist), 2: H43 screen too small, H45 what can't AI do.
- Empty answer: 0. No-citation: 0 (misses are NULL, not blank).
- Unanswerable 6 bogus: H51 animated->iRacing-look entry, H54 shop->MCP, H55 glow->export, H56 3D paint->paint_on_layer, H57 live photoshop->load_flat, H59 mac->Undo. None says "not available".

## 10 worst answers (head)
H59 "does it have a mac version" -> "**Undo** 1. Press Ctrl+Z..." | H54 "sell my paints in a shop" -> "How do I talk to Claude through MCP" | H55 "glow in the dark in iracing" -> "Get it into iRacing 1. Set iRacing Car Folder" | H51 "animated paint" -> "How do I get my paint to look the same in iRacing" | H39 "put text on the car" -> "How do I put a finish on just one part" | H43 "everything too small on my screen" -> "You have a flat paint loaded... 1 zone" | H45 "what cant the ai do" -> same flat-paint checklist | H1 "nothing happens when i click render" -> "I checked your zones and nothing obvious is blocking it" | H17 "how do i make stripes" -> "Add a pattern 1. Everything Else is selected" | H15 "where do i put my sponsers" -> "make numbers and sponsors read cleanly under chrome".

## 5 cheapest fixes
1. Word table: ui size/small/tiny/zoom text -> hdi.ui_size; "cant/can't the ai" -> hdi.ai_limits; "text/lettering/words on the car" -> hdi.add_text (fixes H39, H43, H45).
2. Add buyer words for existing entries so NULLs get claimed: "closed/lost/gone/saved" -> save_project; "eye" -> layer_visibility; "easy vs pro/difference" -> switch_mode; "jagged/rough edge" -> mask_edges; "blurry sponsors" -> decal_rescue/numbers_look_wrong; "photo/picture of a car" -> copy_picture; "part missing/not in list" -> teach_parts; "just blank/opened" -> loaded_nothing.
3. Routing guard: "nothing happens ... render" and "render wont" -> render_wont_start before the why_not diagnosis; "stripes" -> make_zone/draw_area before add_pattern; sponsers (misspelling) -> add_logo; "stuck in easy / real controls" -> easy_to_pro.
4. New honest "not available" how-do-I (none exists today): a not_in_shokker entry listing animation, other sims (Assetto), 3D model/paint-in-3D, shop/selling, live Photoshop sync, Mac, glow-in-dark; can_i must prefer it over the nearest-token entry (kills all 6 bogus answers).
5. Let the self-help brain run for "keeps undoing my colour"/"candy apple red"-style non-imperative phrasing instead of the edit brain, and for "flat in game" / "preview same" ahead of support (-> look_differs, preview_not_changing).
