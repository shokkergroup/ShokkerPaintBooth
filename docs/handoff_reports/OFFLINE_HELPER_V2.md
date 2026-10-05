# OFFLINE HELPER V2 (2026-10-04)

Owner: "Remember to keep trying to improve the Offline Helper also, not just the Encyclopedia." Offline = guided builder + keyword encyclopedia; free chat = online (DeepSeek via OpenRouter) / MCP.

## Progress log
- Step 1 (measure): `_easy_claude_work/helper_corpus.json` (251 buyer inputs: 54 DO, 30 PREFILL, 8 ASK, 134 ANSWER incl. 22 troubleshooting, 25 ONLINE) + `_easy_claude_work/helper_eval.js` (node/vm, $0; `--before` = the helper as it was).
- BASELINE (`node _easy_claude_work/helper_eval.js --before`): DO 50/54 (93%), PREFILL 5/30 (17%), ASK 0/8, ANSWER 0/134, ONLINE 0/25, OVERALL 55/251 = 21.9%. Flagging 0.15 ms per keystroke at 200 chars.
  - Why ANSWER is 0: no index term carries an `art` pointer, so a question only lit up glossary words (card = index summary); nothing searched the v2/v3 articles.
  - Why ASK is 0: on the seafoam design the builder showed the parser's long "I do not see any yellow..." text with a single "what" chip.
- Step 2 (improve): new `js/spb-offline-answer.js` (route + BM25F index over 234 hand articles + 215 help pages + FAQ questions, typo/synonym tolerant, hidden-feature filter) + builder changes (v2 alias flagging, colour+finish compounds, seafoam ask-first chips, catalogue look step, v3 term cards). Eval 21.9% -> 91.6% -> 93.2% -> 97.6% (restored lost `\b` regex boundaries) -> 98.0% (stemmed synonym expansion: "missing" ~ "vanished") -> 99.2% (2 corpus relabels: "look wet"/"rusty and old" are exact parser plans = DO; auto_pop accepted for "shinier").
- Answer quality pass (eyeballed 15 sampled answers): an FAQ answer is used only when the FAQ question is mostly in what was asked (both directions), a Yes/No answer only for a yes/no question, a "why won't X" answer only for a problem question.
- Texture thumbs: `/api/spec-pattern-preview` (and the visual/combined/metal bakes) average these fine 2048-scale fields to one flat grey at 160 px = 4 clones (`_easy_claude_work/eval/helper2/tex_compare*.png`). New `scripts/bake_offline_tex_thumbs.py` bakes 1:1 detail crops shaded as a lit coupon -> `thumbnails/offline_builder_tex/*.png` (5 ids): grid / brick / diamond lattice / scallops, clearly distinct (`tex_compare3.png`).
- Wiring: `send()` in js/spb-pro-ai.js calls `SpbOfflineAnswer.claim(text)` (typed + offline only) right before selfHelpClaim; html tag + ?v= tokens (hv1); runtime-sync-manifest + `_easy_claude_work/sync_helper2.json`; CSS for the answer card / level badge / screenshot / FAQ / hidden-colour chips.
- Gates so far: builder_test 136/136 (thumb regex now also accepts the baked path), ft2 35/35, edit_corpus 509/0, stack 108/108, enc_test 27/27, enc_v2_test PASS (+ --final), undo_inapp 8/8, replay_owner after3 exit 0 ($0.0022).
- In-app pass 1 findings, all fixed: answer screenshot shrank to 0 px (flex child with overflow hidden) -> `flex: none`; the dock kept the previous scroll so new steps / the seafoam chips were drawn above the fold -> a new sentence's steps / answer / term starts at the top; the WHAT list (13 layers on the owner's PSD) pushed the looks below the fold -> once WHAT + DO are chosen it folds to the chosen chip + "Change…"; "Candy paint" term card opened "Colour scale, depth, flip and underglow" (that article lists "candy paint" as an alias) -> reader `byName` now picks the best candidate (exact title > title carrying the head word > alias); "Ask DeepSeek instead" was hidden under offline answers (`builder:true`) -> kept for answers / look searches when a model is set.

## FINAL
**Score (`node _easy_claude_work/helper_eval.js`, 251 buyer inputs, $0):** recorded baseline -> after
| class | before (helper as it was) | after |
|---|---|---|
| DO | 50/54 (93%) | 56/56 (100%) |
| PREFILL | 5/30 (17%) | 28/28 (100%) |
| ASK | 0/8 | 8/8 (100%) |
| ANSWER | 0/134 | 132/134 (99%) |
| ONLINE | 0/25 | 25/25 (100%) |
| **OVERALL** | **55/251 = 21.9%** | **249/251 = 99.2%** |
Route 3.0 ms avg; flagging 0.19 ms per keystroke at 200 chars (budget 5 ms). Two corpus items moved PREFILL -> DO ("make the car look wet", "make it look rusty and old": the parser reads both exactly). `--before` now only drops the answer module (the builder changes stay), so it reads 40.6%; the 21.9% is the number recorded before any change. The corpus was written by me, so treat 99% as "every class works", not as a field accuracy.

**What the buyer sees (offline, typed):**
- A question ("what is a spec map", "how do i make it shinier", "why are my numbers missing in iracing") gets a 📖 answer card under the chat: title + level badge, the short answer (a matching FAQ answer only when the question really matches), how-to steps, the article's first real app screenshot (click = full article), "Read the full article", and "Do it" buttons from the article's actions (finish / control spotlight). The chat line says where the card is; "✨ Ask DeepSeek instead" stays when a model is set.
- A look the parser can't read ("make it look like a rattlesnake") opens the builder: WHAT = whole car, DO = finish, WHICH LOOK pre-searched in the catalogue (Snakeskin / Sea Snake / Python Scale …). Nothing changes until ▶ Run.
- Typing "pink chrome" lights it up as ONE term (colour + finish compound); its card has "Do it" (recolour + finish steps).
- On the seafoam design, "make the yellow matte" asks first: "Your body shows “Seafoam Chalk” (mint green) now, not yellow … Change the Seafoam Chalk, or the original yellow under it?" with two chips.
- Spec-texture thumbnails are real 1:1 detail crops (grid / brick / diamond lattice / scallops), not 5 grey clones.
- Term cards show v3 depth: level badge, summary, first screenshot, top FAQ, "Read the full article".
- Free chat with no model ("write me a poem") gets an honest card: the built-in helper can build / explain, free chat needs the online helper (gear) — never "Nothing was changed". (Eval-verified only: the test server has a model set, so in-app free chat goes to DeepSeek as before.)

**Files:** NEW `js/spb-offline-answer.js`, `scripts/bake_offline_tex_thumbs.py`, `thumbnails/offline_builder_tex/*.png` (5, root + electron-app/server), `_easy_claude_work/helper_eval.js`, `helper_corpus.json`, `sync_helper2.json`, `pw/helper2_inapp.py`. EDITED `js/spb-offline-builder.js` (flagging, compounds, ask-first, look step, term card depth, WHAT fold, scroll reset, thumbs), `js/spb-encyclopedia.js` (byName best candidate), `css/spb-offline-builder.css`, `js/spb-pro-ai.js` (ONE anchored line in `send()` before selfHelpClaim), `paint-booth-v2.html` (answer script tag; ?v= tokens: pro-ai hv1, builder hv3, answer hv2, reader hv1, css hv2), `scripts/runtime-sync-manifest.json` (+ answer js), `_easy_claude_work/builder_test.js` (thumb check accepts the baked path). Synced root -> electron-app/server via `--manifest _easy_claude_work/sync_helper2.json`; `--check` no drift; `node --check` both copies.

**Gates (all green, after the last edit):** helper_eval 99.2%; builder_test 136/136; ft2_corpus 35/35; edit_corpus 509/0; stack_test 108/108; enc_test 27/27; enc_v2_test all PASS (default + --final); undo_inapp 8/8 PASS; replay_owner after3 exit 0 ($0.0011).

**Screenshots (`_easy_claude_work/eval/helper2/`, test server 59879, Chrome CDP 9725, owner PSD, typed + Enter) — what I saw:**
- `question_answer.png`: "What the spec map is" card, BEGINNER badge, 3 how steps, the 4-panel spec-channel screenshot, Read the full article, Do it (chrome / soft matte / Show me zone spec strength).
- `rattlesnake_builder.png`: builder step "The whole car → ? finish", WHAT folded, search box "rattlesnake", Snakeskin / Sea Snake / Python Scale tiles; chat has ✨ Ask DeepSeek instead.
- `pink_chrome_flag.png`: "make the body pink chrome" with `body` and `pink chrome` (one mark).
- `seafoam_ask_first.png`: the ask text + the two chips at the top of the step.
- `texture_thumbs.png`: Texture in the shine row: grid, brick, diamond lattice, scallop, snake rows — distinct.
- `term_card_v3.png`: "Candy colours: how to get depth", INTERMEDIATE, screenshot, FAQ "Which colours work best?", Read the full article.
- `narrow_1100_page.png` / `_panel.png`: 1100 px, panel 392 px, no horizontal overflow; Auto-Pop card with its screenshot.
- `tex_compare.png` / `tex_compare2.png` (old previews = grey clones) vs `tex_compare3.png` (new).

**Gaps:**
- In-app, SpbSupport diagnose / error kinds and SelfHelp explain_state keep precedence (live setup checks beat an article) — e.g. "why are my numbers missing in iracing" goes to the setup check, not the article.
- 2 eval misses: "difference between candy and pearl" (no comparison article; gets Spec presets), "explain the spec channels" (gets Preview channel views / channel sliders, not "What the spec map is").
- Data issues for lane S (not edited, read-only): `finishes.gradients_flip_depth_underglow` lists "candy paint" as an alias (wins the search for "candy paint"); the candy article's first screenshot is the header-rows tour (not candy); the catalogue's `fc_snakeskin` swatch renders nearly black at grey.
- Harness sends (non-typed) bypass the new path by design (`typedNow`), so replay/undo gates don't exercise it; `helper2_inapp.py` does.

## FINAL 2 (2026-10-04 evening): fix the blind-eval PATTERNS

The independent blind eval scored 76.0% correct+acceptable, 48.7% strictly correct, with 6 harmful items. This pass fixes the patterns, not the sentences. The new logic is a pattern layer in `js/spb-offline-answer.js` (route/claim) plus a common-word guard in `js/spb-offline-builder.js`.
- **P0 negation is a constraint.** "dont touch / leave / keep / without touching X" (lists too: "the numbers and sponsors") is removed from the request, and those words are recorded.
  - With nothing left to do, it asks "I will leave the X alone. What should I change?" and offers palette chips.
  - Otherwise, steps on protected targets are dropped and the steps say "Kept as you asked: …".
  - `SpbOfflineAnswer.constraint()` + 1 anchored line in `spb-pro-ai.js complaintOf`: when there is no change to take back, the app's complaint path no longer reads "dont touch the numbers" / "my number disappeared" as a complaint.
- **P1 compound requests keep every clause.** Clause-by-clause reading (`clauseOps`) splits on commas, then/also, "with <part>" and `E.splitClauses`.
  - It wins over the whole-sentence plan only when that plan drops a named part, numbers or sponsors, or reads nothing, or reads a common word as a look. The whole-sentence plan keeps "that pink" back-references (FT2 still 35/35).
  - Unreadable clauses are listed as "Not done: “…”". Stripes, flames and fades get their own reason.
- **P2 destination vs target.**
  - "paint the car white" / "mak the car blak" / "make it green" → body + new colour.
  - "a black roof" → colour adjective before a part. "bumpers" → both bumpers.
  - A look with a verb and no target → body.
  - "X is too bright, can u tone it down" → "make the X darker". The complaint word is never the look.
- **P3 hijack guard.**
  - `COMMON_LOOK` in the builder: an everyday word (racing, little, nothing, team, keep, …), or a short generic `word:`/`tag:` term, never picks a finish. A parser `ext` of common words is dropped.
  - Curated slang table: murdered/blacked out, stealth, chromed out/full chrome, whited out, flat/primer colours.
- **P4 honest decline.** Faces, animals, photos, new logos, own name/words, exact replicas, "full/custom livery" and "from scratch" → ONLINE with a reason. "look like a shark" stays a catalogue look search.
  - In-app the card says plainly that it needs custom art, offers DeepSeek or MCP, and shows no steps. With a model configured, the bubble shows "Ask DeepSeek instead" (the buyer chooses to spend).
- **P5 symptom → answer.**
  - Problem phrasing → the article first. Ranking now handles "get rid of" = remove, "ctrl r" = reload, "R/G/B channel", "trading paints", what-question FAQ guard, how-vs-what title penalty, and support boost for problems.
  - Off-topic (maths, wheels/pedals, which cars to buy) → ONLINE.
  - Questions back with chips: removal ("get rid of the sponsors" → confirm, then the chip goes to the app's undoable layer switch), vague ("change the color", "fix it", "i dont like it"), bare adjustments ("make it darker", "a little less saturated"), and "favourite colour".
  - A fade/gradient → the gradient how-to (never a solid recolour). A stand-alone stripe/flag → the app's element designer, or the stripes how-to, or ONLINE.
  - Answer bubbles no longer show "Look & refine" / "Another take".
- **Corpus:** +46 own paraphrase items tagged `pat:P0..P5`, with new checks `why`, `nd` (not-done count), `kept` and `nostep` in `helper_eval.js`. The adder is `eval/helper2/add_phase2_items.js`.

**Gates (after the last edit):**
- helper_eval **295/297 = 99.3%**. The original 251 items are 249/251 = 99.2%, equal to before. The 2 misses are the old candy-vs-pearl and spec-channels items.
- builder_test 136/136; ft2 35/35; edit_corpus 509/0; stack 108/108; enc_test 27/27; enc_v2_test all PASS.
- undo_inapp 8/8; replay_owner after3 exit 0 ($0.0022).
- **Blind runner re-run (NO LONGER BLIND: re-judged by me, `eval/blind/blind_rejudge_p2.jsonl`):** 61 of 150 outputs changed. Re-judged: 113 correct, 37 acceptable, 0 wrong, 0 harmful, i.e. 100% correct+acceptable and 75.3% strictly correct (before: 76.0% / 48.7%, 6 harmful).
  - This number is self-graded. The real test is the fresh blind round.

**In-app (59879, Chrome 9725), looked at:** `eval/helper2/p2_negate_ask.png`, `p2_negate_steps.png`, `p2_compound.png`, `p2_decline.png` and `p2_problem_answer.png`.
- The negation ask shows palette chips.
- The compound shows roof black + hood white with "Not done: add flames on the trunk".
- The face-on-hood request gets a custom-art decline card with no steps.
- "my number disappeared" gets the Numbers-vanished article card.

**Files:**
- `js/spb-offline-answer.js` and `js/spb-offline-builder.js` (owned, synced to electron-app/server with `_easy_claude_work/sync_helper2b.json`, only these two).
- `js/spb-pro-ai.js`: 1 anchored line in complaintOf. Root only, NOT synced.
- `paint-booth-v2.html` tokens: builder hv4, answer hv4, pro-ai `…-20261005-hv2`. Root only, NOT synced; the electron copy still has the old tokens until the next release sync.

**Gaps:**
- In-app, `SpbSupport` diagnose still owns symptoms it classifies (for example "car is too shiny in sim" → the live setup check, which used DeepSeek for $0.0008 in the test profile).
- Chip clicks are not "typed", so they take the app's own path.
- "snake skin" (two words) is not read inside a compound; it is listed as Not done.
- "give me a checkered band" → ONLINE (element).

## FINAL 3 (2026-10-04 night): structural rebuild after blind round 2 (78% / 43% strict / 2 harmful)

**What changed (js/spb-offline-answer.js; claim() in the same file; no sub-agents; spb-pro-ai.js / paint-booth-v2.html NOT synced)**
- **Semantic frames.** Each message is split into clauses (`splitFrames`). Each clause is read as `{target, action, value}` (`clauseFrame`). Scope (only / except / not / keep / keep the colours) applies to ALL clauses.
  - "X with a Y stripe/pinstripe" = base X + a stripe chip.
  - "X body with Y hood" = two jobs.
  - "a dark blue base" = the body.
  - it/that binds to the previous clause.
  - A bare part after "and" shares the value.
  - Parts named before a whole-body colour are ordered AFTER it, so they survive. Seen in-app: "lime green hood and roof, black body" first ran as an all-black car.
  - The pattern on "X pattern" wins over "camo colours".
  - Adjacent colour words are ONE colour ("emerald green").
  - When the edit brain's plan conflicts with the frames (wrong part colour, entity not named, lost part, off-map part), the frames win.
- **Typed entities.** Numbers, sponsors / logos / brand names, text and images never go to finish search. They get the honest how-to with a lead line: there is no number or text tool, and a logo goes on as a PNG layer.
- **Never-touch, the last filter.** Steps on numbers / sponsors / stripes are dropped unless that clause named them. Every part and plain-colour step carries `exclude`. claim() now shows ALL step readings itself, so the filter always applies. Plans for protected panels still use the app's own path.
- **ASK, not guess.** Chips for: the other one, red or blue?, less, same…, make that part red, match what, remove it, fix the stripe, bare "two tone", vague asks, and "crushed to X%" (= texture SCALE).
- **Conversation state.**
  - claim() reads the last change past the helper's own no-change replies.
  - "a bit darker" re-colours the last change ~15% darker ("darker" ~28%).
  - "same on the roof" copies the last change.
  - "no not that" undoes, then asks.
- **Off-topic and art.** Off-topic and small talk get one short local line with chips and no online call. Custom art (face / animal / photo / logo / text / replica / themed livery) gets an honest decline plus the online / MCP offer.
- Filler and sarcasm sentences are dropped. A shade word on a colour is not a look. Encyclopedia-only terms ("keyboard shortcuts", "iracing") no longer count as finish words.

**Scores (strict = C only; acceptable = C + A; W/H = 0 everywhere)**

| set | n | strict | correct + acceptable | harmful | judged by |
|---|---|---|---|---|---|
| helper_corpus.json (dev) | 297 | 100% | 100% | 0 | `helper_eval.js` (cls + ids) |
| blind round 1 | 150 | **79.3%** | **100%** | 0 | self-judged: `eval/blind/judge3.js` → `blind_results3.jsonl` |
| blind round 2 | 150 | **80.0%** | **100%** | 0 (was 2) | self-judged: `eval/blind2/judge3.js` → `results3.jsonl` |

Caveat: the blind sets are no longer blind (I fixed against them), and rounds 1 and 2 are self-judged. Round 3 (fresh tester, fresh inputs) is the honest number.

Most "A" verdicts fall into these groups:
- The car map has no doors, splitter or mirrors, so those become whole sides / bumper / box-select.
- Stripes, flames and fades are offered as a chip or a recipe, not drawn in the same run.
- Mood words ("make it look expensive") open a look search.

**Gates (all green):**
- helper_eval 297/297
- builder_test 136/136
- ft2 35/35
- edit_corpus 509/0
- stack 108/108
- enc_test 27/27
- enc_v2 --final all PASS
- undo_inapp 8/8
- replay_owner after4: same 5 turns as after3, $0.0011

**In-app on 59879 (screenshots looked at; `_easy_claude_work/eval/helper2/p3_*.png`):**
- Harmful 1, "reflective silver like a mirror but only the body not the numbers": body silver + chrome. The 32s and every sponsor are untouched.
- Harmful 2, "I want teh hood to be matt black wiht a gold pinstripe": hood matte black, gold / yellow items untouched, plus an "Add a gold pinstripe on the hood" chip.
- Conversation: "make the hood red" → Run → "a bit darker" → Run (hood darker red) → "same on the roof" → Run (roof darker red). Numbers and decals intact.
- Ordering: "lime green hood and roof, black body" now gives a black body with a lime hood and roof.
- Off-topic: one local line + 3 chips, no card.

**Open:**
- Whole-body recolour leaves mint / pink fringes on this PSD. This is the existing body-mask coverage, not the helper.
- Chip clicks still take the app's own path.
- "copy the hood colour to the roof" opens a look search; it should be MATCH.

## FINAL 4 (2026-10-04 late night): fix pass 4 after blind round 3 (53% strict / 79% acc / 2 HARMFUL)

**Result (blind3, now NON-blind: I tuned against it).** `node _easy_claude_work/eval/blind3/run4.js && node rejudge4.js` (single items n=145; the tester's verdict is kept where the output did not change, my verdicts are in `verdict4.json`):
- **before: strict 57%, acceptable 83%, 25 wrong, 0 harmful. after: strict 71%, acceptable 99%, 2 wrong, 0 harmful.**
- The 2 still wrong are b3-059 and b3-064 (element designer: number/stripe layout). That is the pro-design lane, not the helper.

**Conversation harness** (`node _easy_claude_work/convo_test.js`, multi-turn, real env carry: `last` / `pending` / `topic` / `undone`):
- DEV 18/18 conversations, 44/44 turns.
- HELD-OUT (`--held`, the 15 blind-3 conversations, not tuned to) 14/15, 36/37 turns.
- Open: b3-156 ("ok put that on the roof" after an un-run look). It now PREFILLs "roof → yellow" with one open step, where it should carry the look itself.

**What changed** (all in `js/spb-offline-answer.js` / `js/spb-offline-builder.js` / `js/spb-pro-edit.js`; comments cite "HELPER_V2 fix pass 4"):
1. **Harmful follow-ups fixed.** A follow-up with no target inherits the last target. A bare answer to the helper's own question ("front") fills that question's slot (`pend {need:'which'|'value'}`). A follow-up never falls back to whole-car. A singular "the bumper" ASKs front / rear / both.
2. **Context carry.** "do the bumper too", "on the roof too", "same for the rear bumper", "ok do that on the hood" copy the last act (look object, texture, scale, shade direction) to the new parts. Undo is kept per step.
3. **Relative edits.** "darker / lighter / a bit less" shade the last colour ops. "lighten the whole car a bit" is rewritten to a relative edit. "smaller / bigger" on a pattern sets `scaleMul` (0.6/0.8 or 1.6/1.25, clamped 0.2–4); the builder reads it as "size N%".
4. **Vague asks ASK with 2–4 chips** ("make it pop", "make it look mean", "add a stripe", "put it in the middle"…). The topic survives an apply-ASK.
5. **Ranking and grounding misses.**
   - New `data/encyclopedia/_alias_overlay.json`: search aliases layered over the articles without touching the fact-check worker's files. It covers Lock Base Color, 8–32 px feature size, Clear next to Import Spec Map, sponsors gone after a finish, add a number, mirror finish, and others.
   - The JS helper and `server_routes/encyclopedia_routes.py` both read the overlay (it is part of the index signature). **Server parity: 327/327 top-1 same article.**
   - Symptoms said as statements, and strong-article how-to goals, now answer. "how do i make a snakeskin finish" gives the look as steps.
6. **Extra words** ("camo scheme", "chameleon colour shifting paint", "splatter look") are stripped to the look word (`denoise`). "pearl that shifts purple to green" gives the shift looks, never a purple→green recolour. "matte black car with red accents" makes the body matte black, plus chips for where the red goes. Scenes ("a unicorn riding a rocket") are declined honestly as custom art.

**In-app proof** (TYPED in the panel, Run pressed, test server 59879; `python _easy_claude_work/pw/helper2_inapp.py p4`). I looked at each picture:
- `eval/helper2/p4_c14_3_white_preview.png`: "paint the bumper" → *Which bumper?* [front / rear / both] → "front" → *What should the front bumper be?* → "white". **Only the front-bumper strip is white**; the body, numbers and sponsors are unchanged (blind-3 had the whole car white).
- `eval/helper2/p4_roof_3_glossy_preview.png`: "make the roof black" → "make it matte" → "actually glossy". **Only the roof is black.** Matte, then gloss, edit the same roof zone: one zone at the end, `Roof gloss {f_soft_gloss}` (blind-3 had the whole car matte).

**Whole-body recolour pink/mint patches: ROOT CAUSE found, not fixed (outside my lane).**
- Picture: `eval/helper2/p4_bodymask_after.png`, from "make the whole car silver" on the owner ARCA design. Big blocky pink and mint patches show through the silver.
- Chain of cause:
  1. A whole-car zone gets `region.paintable = true`. It is set in two places: `js/spb-pro-edit.js` (~line 1049, `{ everything: true, paintable: true }`) and `js/spb-pro-ai.js` line 288 (`protectDecals`: `if (whole && … (r.everything || r.remaining)) … r.paintable = true`).
  2. That calls `SpbProCar.paintableMask(true)`, then `binaryGrid()` in `js/spb-pro-carmap.js`.
  3. `binaryGrid()` treats every opaque cell of the template **"Mask" layer** as not paintable, on a 256-cell grid (hence the blocky edges).
  4. On the owner PSD that Mask layer covers about 22.6% of the sheet, **including real body**. So the new zone's mask is only 85% nonzero (3,562,688 / 4,194,304 px). The owner's older zones show through the holes: Seafoam Chalk on psd_0 (mint) and GTA Pink on psd_1 (pink).
- Evidence (`_easy_claude_work/pw/body_mask_probe.py alpha`): every mint cell is Yellow Base + Mask; every pink cell is Yellow + Black Base + Mask.
- **Proof of cause:** `body_mask_probe.py run nopaint` switches `paintableMask` off in the page only, with no file edited. Result: `eval/helper2/p4_bodymask_fix_sim.png` is **clean silver over the whole body, no patches**, and the numbers and sponsors are still untouched (the zone keeps `sourceLayers psd_0..2`).
- **Proposed patch** (owner/Codex lane: `spb-pro-ai.js` + `spb-pro-carmap.js`):
  - (a) In `protectDecals`, do not set `r.paintable` when the zone already has `sourceLayers` / body layers. The layers already keep the decals out, and the template Mask only adds holes.
  - (b) Matching one-liner in `spb-pro-edit.js` ~1049 (mine, held back because (a) alone re-adds the flag).
  - (c) Belt and braces: in carmap `binaryGrid`, ignore a Mask layer whose opaque cells overlap the body-paint layers by more than ~5%.
- Keep the zone-kit caveat (comment ~line 483): a mask-less "everything" zone without body layers still needs `paintable`.

**Gates (all re-run on the final code):**

| Gate | Result |
|---|---|
| helper_eval | 297/297 |
| builder_test | 136/136 |
| ft2_corpus | 35/35 |
| edit_corpus | 509 / 0 mismatches |
| stack_test | 108/108 |
| convo_test | DEV 18/18, HELD 14/15 |
| enc_test | 27/27 |
| enc_v2_test --final | 6,086 PASS, anchors 0 gone |
| enc_parity | 327/327 |
| undo_inapp | 8/8 PASS |
| replay_owner after5 | same 5 turns as after4 |

**Files**
- Code: `js/spb-offline-answer.js`, `js/spb-offline-builder.js`, `js/spb-pro-edit.js`, `server_routes/encyclopedia_routes.py`.
- Data: `data/encyclopedia/_alias_overlay.json` (new).
- `?v=` cache tokens in both copies of paint-booth-v2.html: hv8 for my three files only.
- Synced to electron-app/server via `_easy_claude_work/sync_helper2b.json` (4 files). `data/encyclopedia` ships via copy-server-assets at build.
- Harness: `convo_test.js`, `eval/blind3/run4.js` + `rejudge4.js` + `verdict4.json`, `pw/body_mask_probe.py`, the p4 scenario in `pw/helper2_inapp.py`.

**For other lanes**
- Encyclopedia data: the `swirl_look` term's first choice is Chain Link (it should be a swirl).
- The 3 helper_corpus items now expect ASK (with a `note`), per the owner directive that vague asks ask.

### FINAL 4b (2026-10-04 late night): body-mask fix LANDED (option a, orchestrator go-ahead)

**The change: two one-line hunks, nothing reformatted, both copies edited in place by exact match.** Comments cite "HELPER_V2 fix pass 4b".
- `js/spb-pro-ai.js` `protectDecals` (line 288): the condition gains `!bl.length`. A whole-car zone that body layers already scope no longer gets `r.paintable` (the template-Mask grid).
- `js/spb-pro-edit.js` (~1049): the whole-car region is `{ everything: true }` when `env.bodyLayers` exist, otherwise `{ everything: true, paintable: true }` as before.
- **Zone-kit caveat kept:** a mask-less "everything" zone on a file with no body layers still gets `paintable`.
- `electron-app/server/js/spb-pro-ai.js` also differs from root elsewhere (Codex work in progress). It got the same targeted line edit, not a file copy.
- `?v=` cache tokens: `spb-pro-ai.js` → `20261004hv8b-bodymask` and `spb-pro-edit.js` → `20261004hv8b`, in both `paint-booth-v2.html` copies.

**In-app proof** (test server 59879; `python _easy_claude_work/pw/body_mask_probe.py run car=<owner|truck|ss>`, "make the whole car silver" typed and run). I looked at each picture:

| # | Car | Zone after the fix | Picture | What I saw |
|---|---|---|---|---|
| 1 | Owner ARCA PSD | `sourceLayers psd_0..2`, no regionMask | `eval/helper2/p4_bodymask_after.png` | Clean silver over the whole body, no pink/mint patches. Numbers, sponsors, spray cans and logos untouched. Before the fix: `p4_bodymask_before_fix.png`. |
| 2 | Chevy Truck PSD (different template, body layer "Car Paint") | `sourceLayers psd_0` | `eval/helper2/p4b_bodymask_truck.png` | Clean silver body. The 55s, Shokker, Aviato, Tres Comas and Chevrolet/Goodyear decals are all kept. |
| 3 | Flat SS sheet (no body layers = the mask-less everything case) | regionMask still set (3,622,208 nonzero) | `eval/helper2/p4b_bodymask_ss.png` | The paintable path still works: silver body with the template's protected areas left out, as before. |

**Gates (re-run after the fix):**

| Gate | Result |
|---|---|
| helper_eval | 297/297 |
| builder_test | 136/136 |
| ft2_corpus | 35/35 |
| edit_corpus | 509 / 0 mismatches |
| stack_test | 108/108 |
| convo_test DEV | 18/18 (44/44 turns) |
| convo_test HELD | 14/15 (36/37 turns) |
| undo_inapp | 8/8 PASS |
| replay_owner after6 | same 5 turns as after5 |

In replay_owner after6, turn 1 (online) recoloured the rear black pink as its reply says. I looked at `eval/replay_owner/after6/turn1_preview.png`: decals intact, no patches.

### FINAL 5a (owner live failure) — 2026-10-05 ~01:15

**Owner sentence:** "Make the current black hexagon - Black Base layer - make it a light blue with silver accent. And give the spec on it a holographic look". I reproduced it on 59879 with the owner ARCA PSD, restored to his 00:35 state (Yellow Base yellows hue -81 = pink satin chrome + Everything Else). Probe: `_easy_claude_work/pw/owner_live_probe.py` (`ids=0 state0035 [before] run|askai`). Node pre-check: `_easy_claude_work/owner5a.js`.

**Root causes (each one reproduced):**
1. **Offline parse.** `layerScope` (spb-pro-edit.js) tried the SHORTEST name first. "Base" matched the first `*Base` layer (Yellow Base), so "Black" was left over as a colour: "Yellow Base layer → Black". Separately, "light blue" tripped `UNKNOWN_PART_RE` ("the light" was read as a car part). The frame path never knew about layers: "make the Black Base layer light blue" became "whole car → Black".
2. **"Asking deepseek instead…".** This is NOT a silent fall-through. That note is only written by the builder's "✨ Ask DeepSeek instead" button (`spb-offline-builder.js` askAI → `spbProAI` askAI); nothing calls it automatically. The open "?" steps made the buyer reach for it. Now the reading has no open steps, so the offline result is complete.
3. **White blocks gone, one small area, jagged edges.** The request log (below) shows what happened. DeepSeek's FIRST zone was right: region = Black Base layer, light blue + chrome second base + holographic flake. Then the picture check ("strict quality checker") judged the whole car ("car is predominantly pink", score 2). The automatic repair then rewrote the zone onto every body part (`region.part: [left side, …, spoiler]`), which covered other layers' art and gave part-mask edges. The app's colour-edit measurement also counted the layer's own charcoal as "18% collateral".

**Fixes (all undoable app changes; comments cite FINAL 5a):**
- `js/spb-pro-edit.js`:
  - `layerScope` tries the longest exact layer name first.
  - "light <colour>" is a colour, never an unknown "light" part. The check sits at the usage site, so the enc parser-vocabulary gate stays green.
- `js/spb-offline-answer.js` — new `layerSentence()` (runs before the follow-up and frame readings). A named PSD layer is the target:
  - Colour words inside the layer's name are part of the name.
  - "the (current) black hexagon / art / design" = ALL of that layer (its own alpha).
  - "the yellow on the Yellow Base layer" stays a colour pick inside that layer.
  - "with silver accent" is not a second target; a note says the holographic shine gives the metal sparkle.
  - "give the spec on it a holographic look" = the colour-keeping holographic shine on the SAME zone.
  - Two named layers in one sentence = one clause each.
- `js/spb-pro-ai.js` (Codex lane; minimal targeted hunks in BOTH copies):
  - New `namedLayerOf(text)`.
  - The picture-check prompt now says only that layer should change.
  - A picture-only doubt about a named-layer request never triggers the AI repair and never undoes it.
  - The colour-edit measurement is skipped when the colour words name a layer.
- **Request log (owner MANDATE):**
  - `server_routes/ai_copilot_routes.py` (both copies) writes `output/ai_logs/copilot_turns.jsonl`. It rotates at 5 MB, keeps `.1`–`.4`, and falls back to `%APPDATA%/ShokkerPaintBooth/ai/ai_logs` on a read-only install. It is local only.
  - Every `/api/ai/chat` call is logged: the buyer text, the model, its reply, tool calls with their arguments, and the cost. Failures are logged too.
  - New `POST /api/ai/turn-log`. `js/spb-offline-builder.js` posts one record per typed turn (Enter / Send / chip / Run / Ask-the-AI). Each record holds the text, offline or online mode, the offline class/path/steps/open steps, the replies, and the zones changed (name, layers, finish, colour).
  - Reader: `python scripts/ai_logs_tail.py [-n 20] [--full 3]`.
- Tokens: `answer`/`builder` `20261005hv9b`, `pro-edit` `…-v1-hv9b`, pro-ai root `20261005mcp8` (Codex bumped it after my edit) and electron `…bodymask-hv9b`. Synced via `_easy_claude_work/sync_helper5.json` (answer, builder, pro-edit only).

**Proof (in-app, 59879, screenshots looked at):**
- Offline: the sentence reads as "① The Black Base layer → Light blue ② Holographic shine on ①", with 0 open steps. Run gives ONE zone, "Black Base layer holographic, in powder blue": layer `psd_1`, everything, `efx_holographic_drift`. All Black Base areas are light blue. The white blocks are intact with clean edges, and the numbers, logos and pink are untouched.
  - Shots: `eval/owner_live_2026-10-05/probe_0_before.png` → `probe_0_preview.png`, plus the bottom-left crop `probe_0_preview_crop.png`.
- Online (the same sentence via "Ask DeepSeek instead", real model, ~$0.003): one zone on `psd_1` only (f_pearl light blue). No repair ran, the white blocks are intact, and there is no spread. Shot: `probe_0_askai_preview.png`.
  - Before the guard, the same repro showed the failure. The repair moved the zone onto every part, and "changed 38% of the paint that was not light blue" (log 01:04).
- Log lines for the sentence:
  ```
  10-05 01:12:43  TURN  enter offline offline helper | Make the current black hexagon - Black Base layer - … | DO/layer steps 2 open 0 | zones: none | reply: I read this as: ① The Black Base layer → Light blue ② Holographic shine on ① …
  10-05 01:12:56  TURN  run   offline app            | ▶ Run: ① The Black Base layer → Light blue ② Holographic shine on ① | zones: added Black Base layer holographic, in powder [["psd_1"]] efx_holographic_drift | reply: Done — the Black Base layer (18% of the car) is now holographic, in powder blue …
  ```

**Not done / owner:**
- The "silver accent" is not a second colour. The holographic shine carries the metal, and the note says so. A real two-colour accent (a gradient band like the owner's own manual zone, or the hexagon outlines in silver) is the owner's call on what "accent" means.
- Other AI repairs can still widen a zone when no layer is named. Only named-layer requests are guarded.
- The live server (59876) needs a restart for the request log route.

## FINAL 5 (2026-10-05, 01:15–03:30): in-app conversation gate + fix pass 5

**Why Node and the app gave different answers (root cause).** The Node convo harness called `route()` directly. The app goes `spbProAI.send → SpbOfflineAnswer.claim → editPlan → SpbOfflineBuilder.claim → app path / online model`. These were the gaps:
1. Turns that `claim()` returned `null` for (undo / redo / "back to how it was", a `pass`) went to the app's own parser or to DeepSeek. "back to how it was" once came back as "the app wouldn't let me undo"; DeepSeek could not redo ("redo" → "Nothing to redo").
2. The app exported only `_undoLast`, not `undoLast`. There was no redo export at all.
3. Spoiler paintability: in-app, `probeRegion` answers `{share_pct: 0, note: "selects nothing on the paint"}`, and `noPaintParts` ignored any result that had a note. So "spoiler orange" ran, failed in the app, and "same for the rear bumper" had nothing to copy.
4. Builder runs flagged `efx_holographic*` as spec-only, and the app's spec-only guard then refused it ("hood holographic" failed in-app only).
5. On a finish-only zone, `strengthMul` set `intensity`, which changes 0 pixels on a finish that keeps the paint (measured). `spec_strength` changes 1,813 hood cells.
6. Earlier ones (pass 5 / 5a): the `send()` bypass, part typos, an empty `act` in `cvPlan`, and named-layer repairs.

**The in-app gate.** `_easy_claude_work/pw/convo_inapp.py` types each blind3 + blind4 conversation (43) into the real panel on 59879 and presses Run. It diffs the paint and spec previews against part masks and prints one verdict per conversation. Shots go to `eval/convo_inapp/<tag>/shots/`.
- Start state: `eval/convo_inapp/owner_payload_8z.json`. This is the owner's 8-zone design, rebuilt from transcript cd90f42f because the job folder was deleted. Zones 0/1 have only 2 colour picks.
- Gate fixes: the grab now waits for the `<img>` to load (a null grab used to read as "changed 0"). There is a new `S:` code for size or small-shade turns, judged at a colour step of 8 instead of 28. I looked at `probe/trunk_scale_cmp.png`: camo 100%→60% is real but subtle (179 cells).

**Before / after (conversations, in-app)**
- Before (start of pass 5): 3/7 pass. The run crashed at b3-153. Blind4 by hand: 52% strict, 9 harmful.
- `after` (01:20, full run): 33/43 (77%), 3 harmful. All 3 harmful were harness noise, not the helper: b3-157 grabbed the pre-render source paint during a test-server restart; b4-134 and b4-135 ran while my own probes shared the browser and server.
- Re-runs after the fixes: `after2` 7/10, then `after3` 3/3, all 0 harmful. `single.json` (b4-022, 036, 042, 046): 4/4.
- `final` (full clean run): **36/37 pass, 0 harmful** (b3-146 → b4-154). The only fail was b4-150 "back to how it was" (the online model refused to undo). That is fixed in `claim()` (offline undo for undo phrasings; a plain "undo" keeps the app's own path) and Node-verified, **not yet in-app**. The 59879 test server hit its 2 h background limit at 03:28, so b4-155…b4-160 did not run in `final`. b4-155 and b4-160 passed in `after2`/`after3` on near-final code.

**The 9 former HARMFUL items** (contact sheets looked at: `eval/convo_inapp/h_items_sheet.png`, `h_single_sheet.png`)
- b4-022 "rooof to brushed aluminum": roof only, spec 4,131 cells, outside 0, paint untouched.
- b4-036 "top of the car white": roof white, numbers kept.
- b4-133: hood gold → darker → "the trunk too": only those parts.
- b4-139: roof orange (it used to be the whole car orange).
- b4-141 "spoiler red / make it lighter / even lighter": "nothing to paint there", then asks which part. Nothing changed.
- b4-142: sides pearl white → gold flake → remove. Sides only. "remove the flake" now undoes (pass undo, offline).
- b4-145 "rattlesnake look / with more gold": turn 1 is snakeskin shine with the paint kept. In `final`, turn 2 **still repainted the whole car flat gold**, as the sheet shows. Fixed afterwards: a whole-car look that kept the paint plus "more <colour>" now opens catalogue picks for "snakeskin gold". Nothing changes until Run. Node-verified, not yet in-app.
- b4-148 "add stripes / white / down the middle": the how-to first, then asks which part, then a white side stripe. Numbers kept.
- b4-160: roof green → undo → redo (offline `_redoLast`) → darker. Redo is in-app proven (`after2`).

**W items:** "faded carbon" → catalogue look picks (in-app, 0 changed until Run). "tiger stripe orange" → whole car orange plus Tiger Stripe picks (the open step now carries the catalogue's own tiles). "bring the yellow back on the roof" no longer adds a stray "? finish" step.

**Other work (orchestrator asks)**
- AI log: every record has `port` and `src`. `python scripts/ai_logs_tail.py --live | --test | --port N` filters by server (checked: `:59879` records).
- Job folders deleted on render: the legacy `server.py` `/render` AUTO-PURGE kept only the newest 2 `job_*` folders in the SHARED `output/`. So any render on one server deleted the other server's jobs, including the owner's live render jobs. It now deletes only job folders that this process created; the rest is left to the existing 24 h janitor (`server_routes/job_cleanup.py`). Applied to both copies.

**Files:**
- `js/spb-offline-answer.js`: hv9f.
- `js/spb-offline-builder.js`: hv9c.
- `js/spb-pro-edit.js`: targeted hunk in both copies; token `…-hv9c`.
- `js/spb-pro-ai.js`: `_redoLast` export, both copies. Token left to Codex, who has bumped it since.
- `server_routes/ai_copilot_routes.py`, `server.py`: both copies.
- `scripts/ai_logs_tail.py`.
- Harness: `pw/convo_inapp.py`, `pw/turn_probe.py`, `pw/strength_probe.py`, `pw/np_probe.py`, `o5probe.js`, `eval/convo_inapp/{specs,single}.json`.
- The sync manifest now lists answer + builder only; root pro-edit carries a Codex-only MCPSCEN hunk.

**Gates (Node, last run):**
- helper_eval 296/297. The one miss is "what does roughness mean" → the article ranking, owned by the SEARCH LAB. It was 297/297 earlier tonight; I did not touch `search()`.
- builder 136/136; edit_corpus 509/0; stack 108/108; ft2 35/35; enc_test 27/27.
- convo dev 18/18, held-out 15/15, specs 43/43.
- **Not run:** undo_inapp and replay_owner after7. The test server stopped.

**Open:**
- Re-run `convo_inapp.py tag=final2 fresh` once 59879 is up (it confirms b4-150 / b4-145 / b4-155…160 in-app). Then undo_inapp + replay_owner.
- "add gold flake" gives a metallic flake in the zone's own colour, not gold. The catalogue's gold flakes ("CX Gold-Green Flake", "Rose Gold Dust") are weak matches.
- Live 59876 must be restarted for the port field and the purge fix. Restarting it does not wipe other servers' jobs any more.

## FINAL 6 (2026-10-05, from 03:40): pass-5 confirmation runs + fix pass 6 (answer UX)

Written as the work goes; newest facts at the bottom of each list.

### Pass-5 confirmation runs (59879, restarted by the orchestrator 07:40 server time)
- `convo_inapp.py tag=final2 fresh`: running (43 items).

### Root causes found so far
- **Node is not the app for questions.** `helper_eval.js` and the Node probes never load `js/spb-enc-search.js`, so they rank with the BM25F *fallback* in `spb-offline-answer.js`; the app ranks with the shared SEARCH LAB ranker. With `SX=1 node _easy_claude_work/o6probe.js eval/casual6.txt` (shared ranker loaded) 34/35 casual questions still answer offline, but several pick a different (worse) article: "hey how do i make my car shiny" -> make_matte, "how do i make stripes" -> recipes.finish_on_numbers, "what are layers?" -> layers.roles, "whats the deal with clearcoat" -> off-topic. Ranking belongs to the reader/search worker.
- **Chatty wrappers broke questions.** "hey quick question, what does roughness do", "can you explain pearl to me", "could you tell me what candy is", "i was wondering how zones work" were read as edits / unknown (-> online model when a key is set), and "whats the deal with clearcoat" lost coverage. Fix: `casualCore()` drops the wrapper before `kind()` and before the search; a diluted-coverage top hit answers when its own title / aliases carry the asked word (`titleOverlap`). Search() untouched.
- Node gates can now load a working copy and the in-app ranker: `OA_FILE=<file> SX=1 node helper_eval.js` / `convo_test.js` (harness-only change).

### Fix pass 6 (staged in scratchpad answer_fx6.js until the final2 gate finishes, then copied in)
- (a) casual set `eval/casual6.txt` (50 questions, 15 chatty, written before measuring), shared ranker: 43/50 -> 50/50 answered offline.
- (b) style menu: `STYLES` (8 ideas from `ideas.style_menu.related`, step sentence follows each article's examples[0]); `STYLE_ASK_RE` + VAGUE2 -> `styleAsk()` 4 chips "Build: <title>"; `styleOf()` turns a chip into guided-builder steps with a note naming the recipe. Node: all 8 chips give 2-4 steps (whole car + hood/roof).
- (c) answer bubble = one pointer line; the card carries the answer. (e-punctuation) a title ending in ? ! . takes no colon / stop.
- (d) Do-it labels: control -> the article's `controls[].inv` label (the UI audit's human label, same as the reader), finish/pattern/spec -> catalogue name; duplicates get a suffix. Node shows "Copy TP Desc", "LAYERS tab", "+ Add Zone", "Candy / Candy (foundation)".
- helper_eval corpus: "something aggressive" / "make it look expensive" PREFILL -> ASK (the coordinator's mandate: vague style asks get recipe chips). helper_eval 297/297 (fallback ranker) and 297/297 with SX=1; convo dev 18/18, held 15/15.
- final2 in-app gate (pass-5 code): 38/43 first run, the 5 misses (b4-151..156) all inside 04:16-04:19 when another client loaded the app on 59879 three times (server log) and the preview showed the un-zoned source paint after a plain question; rerun `tag=final2r ids=...`: 5/5, 0 harmful -> **43/43, 0 harmful**. Confirms in-app: b4-150 "back to how it was" (undo phrasing), b4-145 rattlesnake+colour, b4-155 "less rainbow", b4-160 redo.
- undo_inapp: 8/8 PASS.
- replay_owner after7: same 5 replies as after6, turn-1 preview identical by eye (`eval/replay_owner/a6_a7_t1.png`). Harness fix: the owner's job folder is gone, so `REF_RENDER` falls back to `eval/replay_owner/ref_RENDER_paint.png`.

### Fix pass 6 installed (js/spb-offline-answer.js hv10a -> hv10c, both HTML copies, electron copy synced)
- In-app (59879, model configured, `qa_probe.py`): 10/10 casual questions answered by the helper, none sent to DeepSeek (`eval/convo_inapp/qa_p6a.json`; looked at qa_p6a_6.png candy and qa_p6a_7.png layers: one bubble line + the card, no picture on candy, "What are layers?" with no colon, Do-it "LAYERS tab", "Copy TP Desc", "IRACING USER ID box", "Candy / Candy (Foundation)").
- Style chips in-app: "something aggressive" -> 4 "Build: ..." chips; clicking one -> builder steps with the recipe note (looked at qa_p6b_2.png); "Build: Aggressive and mean" run -> whole car matte black + hood gloss red, numbers and sponsors untouched (looked at `eval/convo_inapp/style_run_sheet.png`).
- Extra fix found while testing: "make the hood look mean" searched “hood mean” and put the look on the WHOLE CAR; `lookStep` now targets the named part(s) and searches the rest.
- Do-it duplicate names get "(Foundation)" for `::f_` ids instead of raw id words.
- Gates: helper_eval 297/297 (fallback ranker) and 297/297 (SX=1, the app's ranker); builder 136/136; ft2 35/35; edit_corpus 509/0; stack 108/108; enc_test 27/27; convo dev 18/18, held 15/15, specs 43/43; in-app `p6.json` 3/3 (style chip run + undo, chatty questions), full in-app gate **final6: 43/43, 0 harmful** (59879 was restarted by the orchestrator mid-run; no item was cut off; grabs checked by eye in `eval/convo_inapp/final6_sheet.png`).

### Open items after pass 6
- The app ranks with the shared SEARCH LAB ranker, Node gates rank with the fallback unless `SX=1`. Some casual phrasings now land on a weaker article with the shared ranker ("hey how do i make my car shiny" -> make_matte, "how do i make stripes" -> recipes.finish_on_numbers). That is ranking, so it goes to the reader/search worker. Suggest making `SX=1` the default in helper_eval.
- Answer card header: the INTERMEDIATE badge overlaps "answered offline" at the 392 px panel width (CSS, cosmetic).
- Style recipes put the accent on the hood or roof. On the owner's ARCA PSD the big hood decal covers most of the red hood (by design: decals stay on top).
- `make the sides look aggressive` gives 2 open steps (left / right), each needing its own pick.

## FINAL 7 (helper fix pass 7, 2026-10-05: driven by blind round 5)
Blind round 5 (HELPER_BLIND_EVAL_5.md): 63% good+ok, 23% strict, 5 HARMFUL. Fixed by CLASS, not by item. The tuning set is new: `_easy_claude_work/eval/fix7/dev.jsonl` (58 conversations, 81 turns, 7 classes, wording different from blind5), made by `eval/fix7/make_dev.py`, which also writes the in-app specs `eval/convo_inapp/specs_fix7.json`. Blind5 is re-run only as a regression check, labelled CONTAMINATED.
Work copies were edited in a scratch folder and installed at the end (see Install below). Node dev numbers: `node convo_test.js --file=eval/fix7/dev.jsonl` (the new `--file` / BYCLASS mode).

### Harness upgrades (done first)
- `convo_test.js --file=<jsonl>`: dev conversations plus new judge keys: `only` (no step outside the named parts), `nofill` (no solid recolour unless it is an outline or gradient), `noundo`, `excl` (kept parts excluded), `list` (a real finish list), `topic` (regex on answer + lead + ask + notes). Overrides `OA_FILE` / `OB_FILE` / `PE_FILE` load scratch copies.
- `pw/convo_inapp.py`: merged `convo_inapp5.py` panel capture (`<tag>/panel.jsonl`); answer-topic check on what the buyer reads (reply, options, card, notes); paint and spec diffs split (`paint X out Y | spec-only out Z`); new codes E (kept parts untouched inside), K (refinement keeps the earlier change), O (outline: paint inside the part, <=60% of it, none outside; harmful if >85% = a fill, or paint outside), G (gradient: paint only inside the part AND a gradient zone exists); CDP port from `SPB_CDP_PORT`.

### Node dev set, before -> after (per class)
| class | before | after |
|---|---|---|
| scope (outline / gradient / refinement) | 8/10 | 10/10 |
| question (never an edit; finish lists) | 6/10 | 10/10 |
| negation / keep-clauses | 3/9 | 9/9 |
| honest (small colour) | 5/5 (Node has no shares) | 5/5 |
| garble | 6/6 (judge too lenient: see unit test) | 6/6 + `garble_test.js` 55/55 strings |
| memory | 5/10 | 10/10 |
| topic | 2/8 | 8/8 |
| total | 35/58 conv, 56/81 turns | 58/58, 81/81 |
In-app before/after and the HARMFUL-class shots follow below.

### In-app dev set (owner car on test 59879), before -> after
`python pw/convo_inapp.py specs=specs_fix7.json tag=fix7_before|fix7_after`. The before run used the old O/G-less codes for the scope items, so those 8 were re-run with the new codes on the OLD runtime (`fix7_before_scope`) before anything was installed.
| class | before | after |
|---|---|---|
| scope | 3/10, 1 harmful | 10/10, 0 harmful |
| question | 6/10, 3 harmful | 10/10, 0 harmful |
| negation / keep | 3/9, 4 harmful | 7/9, 0 harmful |
| honest | 2/5 | 5/5 |
| garble | 5/6 | 6/6 |
| memory | 6/10, 1 harmful | 10/10, 0 harmful |
| topic | 5/8, 2 harmful | 8/8, 0 harmful |
| total | 30/58, 11 harmful | 56/58, 0 harmful |
Spec corrections made after the before run (counted as before-fail, not harmful): o03 "turn the green bits white" -> "brown" (the owner car's body IS mint green, so recolouring it was right); o04 topic regex also accepts the honest "not gold: that zone paints over it" answer; g03 bare "gold" at chat start -> W? (a whole-car gold is a fair, undoable reading); the harness BLOB now includes the builder step's own ask (o02's honest "I do not see any orange" lives there).
Still failing: n01 / n03 (E code). The kept part keeps its colour by eye (looked at `fix7_after/cmp_n01.png` + `n01_hood_diff.png`: the hood stays mint), but 513 / 1625 cells inside the eroded kept part still differ (was 751 / 4776 before), along one edge of the part. Not harmful; cause not pinned down (see What is left).

### Shots looked at, 1:1 (HARMFUL classes)
- s02 trim on the trunk: before = solid gold fill of the trunk; after = a thin gold line along the trunk edge, nothing else changed (`fix7_after/cmp_f7-s02_t1.png`).
- s04 outline the left side: before = nothing; after = a white line along the left side's edge, decals on top (`cmp_f7-s04_t1.png`).
- s05 fade the hood: before = nothing; after = a red-to-black gradient across the hood only, the hood logo on top (`cmp_f7-s05_t1.png`).
- q03 "show me some satin finishes": before = a whole-car satin spec change; after = a list, no pixel changed (`cmp_q03.png`).
- s09 refinement: matte black stays after "some gloss somewhere" -> ask -> "a touch on the roof" (`cmp_s09.png`).
- n01 keep-clause: the hood keeps its colour, the rest is silver (`cmp_n01.png`).

### What changed, per class (all hunks tagged `HELPER FIX PASS 7 2026-10-05`)
1. **Scope (HARMFUL).**
   - Outline / trim / edge / border / "line around": `p7Outline` makes a recolour step with `extra.outline {w}`. pro-edit turns it into `region.graphic {kind:'outline'}`. The new graphics kind `outline` is the part's car-map mask minus its eroded self (thin 6 px, default 10, thick 18 at 2048). With no part named it asks which part; with no colour it asks which colour. "silver or gold for the trim" offers both colours.
   - Gradient / fade / "from X to Y" on a part: `p7Grad` gives a step with `extra.gradient {from,to,axis,start}`. pro-edit `partGradient` orients the stops by the car map's front / roof-line side, and zone-kit fits them to the part. If one colour is missing (or the buyer says "fade to nothing"), it asks for both colours.
   - Refinements:
     - "somewhere" asks where.
     - "tone it down" / "too bright" gives the same colour, calmer (toned hex). On a finish it lowers the strength instead.
     - "just a little on the hood" adds the change on the hood and never takes the last change back first.
   - **Hard guard before ▶ Run** (`spb-offline-builder.js scopeGuard`):
     - When the sentence names parts and has no whole-car or keep words, every compiled zone is probed with those parts cut out (`SpbProZone.probeRegion`).
     - If more than 1% of the car is left, Run is refused with "Not run: this would change X% of the car OUTSIDE the <part>".
     - The measured value is kept in `S.guard`.
2. **Questions.**
   - Bare is / are / was now start a question.
   - "X vs Y" / "difference" questions go to the encyclopedia.
   - `qGuard`: a question can never come back as runnable steps.
   - "show me / list / give me … finishes", "which/what … finishes": a numbered list of real catalogue finishes, with "Use X on the body" chips. Nothing changes until one is picked.
3. **Keep-clauses.**
   - Phrases recognised: "the sides stay as they are", "leave the hood alone", "don't touch the sides", "except / apart from / but not the X", "keep the roof", "keep it shiny".
   - The kept parts become `extra.exclude` on whole-body / colour steps, and steps on a kept part are dropped.
   - zone-kit `excludedUnion` now cuts out a named part's car-map mask, and validation accepts part names.
   - Such a turn is shown by the helper, so the app's own path no longer refuses it ("I can't yet guarantee …").
4. **Honest.**
   - Under 2% shown: it asks, as before.
   - 2-3% shown: the change is made, but the reply now says "Only about N% of the paint is <colour>, so this is a small change. If you meant the main colour, say …" (pro-edit note).
   - Why the split: the edit corpus has deliberate 2% accents that must still run.
5. **Garble.**
   - `tidy()` / `chipOk()` run on every routed ask, chip, note and lead, and on the reply text. They remove empty slots, undefined / null / NaN, "make the car is", doubled verbs and the dangling "the".
   - `cvAskValue` never asks about an empty part.
   - `CHOICE_RE` never captures is / are / the.
   - Filler words (then / i guess / maybe …) are not the value.
   - An unfinished "paint the" asks what to change.
   - New unit test: `node _easy_claude_work/garble_test.js` (tidy cases + 25-input sweep, 55 strings).
6. **Memory.**
   - "use the second / first / last one", "put the third one on the hood" and a chip label pick from the last list (`CS.list`, kept 10 min).
   - "something else / a different one": other catalogue looks for the same part, or other colours.
   - "same on the other side" / "mirror that on the left": the opposite side only.
   - "nah / actually go back", "back to how it was" = undo.
   - "save it / export it / how do I export … for iRacing" answers with the render articles. The lead is taken from server.py naming: RENDER writes `car_num_<ID>.tga` or `car_<ID>.tga` plus `car_spec_<ID>.tga` into `Documents\iRacing\paint\<car folder>`, Ctrl+R in iRacing reloads, and Save project keeps the design.
7. **Topics.**
   - plastic / toy / fake / flat in iRacing → `support.flat_or_shiny` + `spec.paint_spec_marriage`, with a spec lead.
   - "see me from across the track / easy to spot" → `ideas.stand_out_in_pack` + `make_it_pop` + `readable_on_tv`, with a contrast lead.
   - "sponsors / numbers hard to read / get lost" → `ideas.sponsor_friendly_bases` or `numbers_match_body` + `readable_on_tv`. The lead says the fix is the body behind them, with sponsors and numbers untouched; the chips are plain whole-car colours.

### Gates (after install, 2026-10-05)
- `node _easy_claude_work/helper_eval.js`: 297/297. One corpus expectation was changed: "blend the roof from white into blue" no longer expects `pass:design`, because that path painted the roof solid white. It now gets a roof gradient zone; the reason is in `why7` on the item.
- `builder_test` 136/136 · `ft2_corpus` 35/35 · `edit_corpus` 509 phrases, 0 mismatches · `stack_test` 108/108 · `convo_test` 18/18 · `convo_test --held` 15/15 · `convo_test --file=eval/fix7/dev.jsonl` 58/58 · `garble_test` 55/55.
- In-app `specs.json` (tag final7): **43/43, 0 harmful**. In-app fix7 dev: 56/58, 0 harmful.
- `python pw/undo_inapp.py`: 8/8.
- `python scripts/ai_atlas/hidden_feature_check.py -q`: PASS (406 files, 0 hits).
- Install:
  - Files: js/ + electron-app/server/js/ for spb-offline-answer.js, spb-offline-builder.js, spb-pro-edit.js, spb-pro-graphics.js and spb-pro-zone-kit.js.
  - `?v=` tokens bumped in both paint-booth-v2.html: answer `hv11p7b`, builder `hv11p7`, pro-edit `…-rf2-p7b`, graphics `spb-graphics-20261005p7`, zone-kit `mcp30-p7b`.
  - spb-pro-ai.js and spb-enc-search.js were not touched.

### Late fix (after the blind5 regression read): `hv11p7b` -> `hv11p7c`
Reading the blind5 answers by hand turned up two class misses that the harness had scored as passes:
- **b5-020, question class.** "will my paint look the same in iracing as in here" was answered "Same as what? There is no earlier change…".
  - Cause: a question that says "the same" was read as a copy request.
  - Fix: a guard in the same / other-side branch. Now goes to the support helper, "Why it looks different in iRacing".
- **b5-029 and b5-050 T3, garble class.**
  - The replies were "Which part should I make looks too clean, look like its been through hell?" and "Which part should I make no thats too wide?".
  - Cause: cvAskPart put the leftover text back into the question.
  - Fix: cvAskPart now uses the leftover only when it is a short value. Otherwise it asks the plain "Which part should change, and to what?".
- **Unit cases.** garble_test.js now has all three inputs, a check for "Which part should I make <4+ words / no / looks>", and a check against reading the b5-020 question as a copy request. GARBLE PASS 65/65.
- **Install.** Answer only, root + electron copy, token `hv11p7c` in both HTMLs.
- **Re-check.**
  - Node: every gate below re-run after this change.
  - In-app: b5-020 / 029 / 046 / 047 / 050 re-run (tag `blind5_p7c`), 5/5, 0 harmful. I read all three replies in the panel text.

### Blind5 regression (CONTAMINATED: I fixed against these failure classes, so this is a regression check, not a blind score)
The harness run was tag `blind5_after7`, owner car, test 59879.
- **Harness (mask codes):** 52/60, 2 flagged "harmful". Before (round 5): 45/60, 8 flagged.
- **Both flags are false alarms.** I looked at the shots at 1:1.
  - **b5-039** "keep the colors, just make the whole body shine like chrome". The paint shot is identical to t0 and the change is spec-only chrome, exactly as asked. The harness counts a spec change on the whole body as harmful.
  - **b5-059** "i want the number big and yellow". The numbers are yellow and nothing else changed. The buyer named the numbers, so this is allowed. "big" is silently not done, so I grade it ok, not good.

**My judgement with the round-5 rubric.** I read every reply in compact.txt and the panel text, and looked at the shots for 039, 042, 047, 051, 059 and 060. This includes the `hv11p7c` re-runs of 020, 029 and 050:

| | good | ok | bad | HARMFUL | good+ok |
|---|---|---|---|---|---|
| Round 5 (blind judge, before pass 7) | | | | 5 | 63% |
| After pass 7 (my read, contaminated) | 27 | 23 | 10 | **0** | **83%** |

All five round-5 HARMFUL items are now safe:
- **b5-047** (trim line became the whole car red). Now: roof gloss black plus a thin red outline only on the roof. I looked at b5-047_t3.png.
- **b5-057** (gradient became a solid whole car). Now it asks for the second colour and changes nothing.
- **b5-046** (refinement reverted). Now: tone-down updates the same zone, go-back undoes it, satin asks which part.
- **Questions run as edits.** Now answered.
- **b5-060.** Stealth black, then shine only on the hood (looked at t3).

The 10 bad items are where the remaining work is:
- **b5-033** "just fix it it looks off": the numbers / sponsors card is unrelated.
- **b5-034** "Black Base layer light blue with silver trim and a holographic spec": only the holographic spec in silver was applied, the light blue was dropped and the reply says "paint colour stays". This is the owner's live sentence again: the partial parse is honest but incomplete.
- **b5-038** "only the rear bumper and spoiler, matte orange": the spoiler has no body paint on this car, so it asked again and did NOT do the rear bumper.
- **b5-041** checkered trunk at 40%: the pattern was dropped and it became a white trunk step plus an unpicked finish.
- **b5-042** "red to teal but dont touch the number or sponsors": the red is only 2% and is shared with the logos. The reply says honestly that the sponsors changed too, but the buyer said not to.
- **b5-045** "colour shift front bumper, purple to blue": it picked the CX Blue Orange shift and needed a pick.
- **b5-050 T3 / T4** "no thats too wide" / "half that": a refinement of the app's stripe is not understood. No longer garbled, but it still does nothing useful.
- **b5-053**:
  - "thats not the hood thats the roof" and "put red on the hood and undo the roof": a part correction is not understood.
  - T3 even plans red on the hood + roof, which is the opposite of what was asked. It waits for Run, so nothing was painted.
- **b5-057 T4** "now do the same on the other side": with no completed gradient yet, it answers "no earlier change". Safe, but the conversation never got to a gradient because the buyer never gave a second colour.
- **b5-058** "is gold or silver better for black" gave the "Colour names" card. Then "just the wheels and trim not the body" went to the outline ask instead of gold accents.

### What is left (next pass / other lanes)
1. **Part correction and multi-part requests** (b5-038, b5-053):
   - when one named part is not paintable, do the rest and say so;
   - "that's not the X, that's the Y" should move the last change.
2. **Refining the app's own stripe** (b5-050): "too wide / half that" should change the stripe width.
3. **Three-part owner-style sentences** (b5-034): colour + trim + spec on a named layer. Light blue is still dropped. The owner's open question about what "silver accent" means is still open.
4. **Keep-clause against a shared colour** (b5-042): when the colour being changed is also in the logos and the buyer said not to touch them, ask or mask the logos out. Do not do it and then warn.
5. **Patterns at an opacity** (b5-041), and a purple → blue colour shift that picks a matching shift finish (b5-045).
6. **n01 / n03 residue on the dev set**: "everything except/but the hood" leaves 513 / 1625 hood cells changed (was 751 / 4776). On the shot the hood still reads mint; the residue runs along one edge. Not pinned down.
7. **Not yet verified:**
   - the direction of a hood gradient in the iRacing view (front / rear on the sheet);
   - "black car with gold trim" drops the trim (whole-car scheme kept, trim not done);
   - follow-up "silver i guess" after an outline colour ask (g02) does not continue the outline.
8. **Ranker notes for the search lane** (spb-enc-search.js was not touched):
   - "is white or black better on a blue car" → playbook.gradients_and_flake is weak;
   - "what's shinier, satin or gloss" → ideas.satin_modern_oem, which should be a gloss-vs-satin comparison;
   - "is gold or silver better for black" → the "Colour names" card;
   - "whats metallic vs pearl" → only the metallic R-channel card.
9. **Harness:** a spec-only whole-body change asked for with "keep the colors" should not count as harmful (b5-039). The buyer naming the numbers should allow a number change (b5-059).
10. **The next blind score needs a NEW corpus.** blind6 (`_easy_claude_work/eval/blind6/corpus6.jsonl`) is ready. blind5 is now contaminated.
