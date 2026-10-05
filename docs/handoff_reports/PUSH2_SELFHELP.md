# PUSH2-SELFHELP - the five cheapest fixes from PUSH-HOLDOUT, measured three ways (2026-10-03)

Lane: `js/spb-self-help.js`, `docs/ai_knowledge/how_do_i.md`, `js/spb-ai-knowledge.js` (rebuilt by `scripts/build_ai_knowledge.py`), `js/spb-pro-ai.js` (one guard), `_easy_claude_work/selfhelp_test.js`, `selfhelp_holdout_test.js`, `stuck_holdout2.json` (+ `stuck_holdout2_raw.txt`), this report.

## Numbers (honest)
| Set | Before | After | Note |
|---|---|---|---|
| In-sample 182 (stuck_questions.json) | 162/182 (89%) | 163/182 (90%) | not held out (hint table was written against it) |
| Holdout-60 (stuck_holdout.json) | 27/60 (45%) | 57/60 (95%) | NOW TUNED: the fixes were written from its miss list, so this is no longer a held-out number |
| **Holdout2-30 (stuck_holdout2.json, clean)** | - | **16/30 (53%)** | 30 questions written first (before reading any set or the miss list); expect ids assigned from the how_do_i id list before the first run; not tuned afterwards |

The clean number (53%) is the one to quote. It sits close to PUSH-HOLDOUT's 45-50%: the fixes closed the specific holes, not the general gap.
Holdout2 misses (14): 10 NULL - support / in-game owned in the real router (washed out in iracing, number disappeared, preview vs game, all black in sim), orders (`i want a matte black finish`), "can the ai ..." (rejected by the can-you order rule), statements with no claim words (app slow, render greyed out, deleted a layer, sponsor pixelated); 4 wrong entry (`load my old paint` -> not_in_iracing, `make the paint sparkle` -> Load a paint, `finish is too big` -> generic stuck, `see the car in 3d` -> Get it into iRacing instead of the honest no).

## Fixes applied
1. Word table: new `CLAIM_HINTS` (first in HINTS) for ui size / too small, "what can't the ai", text on the car.
2. Buyer words for existing entries: closed/lost work -> save_project, little eye -> layer_visibility, easy vs pro / top buttons -> switch_mode, jagged edges -> mask_edges, blurry sponsors -> decal_rescue, photo of a car -> copy_picture, part missing -> teach_parts, opened blank -> loaded_nothing, flake down -> finish_less_strong, how big flames -> pattern_finer, preview the same -> preview_not_changing, iracing old paint -> not_in_iracing, looks flat in game -> look_differs.
3. Routing: a claim hint now claims statements (classify) and outranks generic word hints in matchHowto ("keeps undoing" -> colour_not_applying, not Undo); render-nothing-happens -> render_wont_start; stripes -> draw_area; sponsers -> add_logo; stuck in easy -> easy_to_pro.
4. New `hdi.not_in_shokker` entry (animation, glow, other sims, 3D view/paint, shop, live Photoshop sync, Mac) + `NOT_IN` regex; `capability()` prefers it (kills H51/54/55/56/57/59 bogus answers).
5. `js/spb-pro-ai.js` `selfHelpClaim`: `SH_FIRST_RE` (keeps undoing / nothing happens ... render / looks flat in game) returns the help answer before the support + edit checks; `editYieldsToStack` untouched.
Matcher (tests only): `shortHit` - `hdi.gradient` matches cite `zone_gradient`; an answer citing an hdi entry's own ui id counts (H18, H49). `selfhelp_holdout_test.js` takes a json name arg.

## Gates
selfhelp guards 22/22, chips PASS; claims 24 overlaps (unchanged; self-help claims 138); edit_corpus 409/0; convo_test 52/52; tool_test 15/15; adv_fp 0 claimed; corpus_eval FINISH claimed 1031/1100 (was 1030 - +1, not bisected), compatible 967/1100 unchanged, OTHER 400/400. node --check on all three js; scan_ctrl 0; ?v= bumped to *20261003push2*; sync --write then --check no drift.
Rebuild note: `selfhelp_build.py` re-embedded UI_DATA from the current ui_map.json: 566 rows (SELF-BRAIN reported 575; ui_map changed under another lane).

## Not verified
No in-app run (59879) - node only; the SH_FIRST_RE guard is not exercised by any suite in the real send() order. The +1 corpus_eval claim is unexplained. Holdout2 is one 30-question sample written by the same agent that tuned the brain.
