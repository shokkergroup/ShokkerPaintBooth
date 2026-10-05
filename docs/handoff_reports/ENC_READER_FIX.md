# SPB Encyclopedia reader fixes (2026-10-05)

Input: docs/handoff_reports/ENC_UX_TEST.md. Work notes appended as I go.

## Baseline (before any change)
- search lab dev (bench.jsonl, n615): shared 90.6/98.4/0.945, reader 90.1/98.0/0.940, offline 90.6/98.4/0.945, python 90.6/98.4/0.945 (top1/top3/MRR). Held split hidden by harness; casual_set not scored or opened.

## 1. Search: did-you-mean + judge miss patterns (shared ranker, JS + Python mirror)
- `js/spb-enc-search.js` (VERSION 2026-10-05.6) + `server_routes/encyclopedia_routes.py`: new `spell(ix, text)` / `sx_spell` repairs RAW words against the surface vocabulary (titles, aliases, FAQ questions, summaries) with an edit distance that counts swaps (1 for short words, 2 from 7 letters; ties -> the more common word). search() runs on the repaired text automatically; spell() returns `fixes` for the reader's "Showing results for ...". Root cause of "tradng paints": the old repair worked on STEMMED words ('trading' -> 'trad', 'iracing' -> 'irac'), so 'tradng' landed on 'strang' and 'iracng' on 'rang'.
- Judge patterns (fitted on DEV only, casual test split untouched): `look` intent (tool word + finish/metal word, no canvas word -> tool pages x0.6, P.il), bare verb ("export?") = how-to, bare file format ("tga?") = files, colour symptom in the sim ("too saturated on track", "red looks orange in iracing") -> "colours look different in iRacing" cue. Aliases (search_lab/alias_add7_reader.txt via apply_aliases.py): 'tga' moved source_paint -> output_files; manual -> Getting Started in-depth; "how many pcs" -> licence article.
- Numbers: dev shared/offline/python 90.6/98.4/0.945, reader 90.1/98.0/0.940 = unchanged (0 dev rows moved). Parity 1689/1689 PASS; own typo/probe parity (`_easy_claude_work/enc_fix/typo_parity.py`, 40 queries) 40/40.
- Note: `_alias_overlay.json` 404 on 59879 is a stale server process: `server_v5.py` already whitelists the file (line ~490); a restart of 59879 picks it up.

## 2. Pictures: fixed at the generators + one shared post-pass (2026-10-05)
- **Root cause.** `enc_gen_B_v3.screens_for` gave every generated finish page its shelf hero `cat_<shelf>` (Chrome page → Moonstone tie-dye car), and the reader's `carShot()` fell back to that hero too. `enc_v3_screens.py` matched by loose word overlap, with a "window tour" fallback. The `enc_ideas_b0*` authors hand-picked shelf heroes by mood ("dark" → the bright blue Abyss Blue DARK CITY car on the stealth page).
- **One rule set: `scripts/ai_atlas/enc_reader_fix.py` (`screen_ok` / `figure_ok`).**
  - A car render is allowed only for a look the page itself uses, or for a finish or shelf the page names in full. Shelf mood words (dark, neon, city…) do not count.
  - A screenshot must share a subject word with the page's title, aliases or summary. App frame words (window, header, menu…) do not count, unless lane S curated it for that page.
  - Each worked example's own picture is judged against that example's settings.
- **Generators now use the same rules:**
  - `enc_gen_B_v3.screens_for` uses exact renders only.
  - `enc_v3_screens` uses `screen_ok`, and its fallback was removed.
  - `enc_ideas_build` filters screens instead of stopping the build.
  - `build_encyclopedia.py` runs `enc_reader_fix.py --write` before indexing, so a rebuild cannot regrow the bad pictures.
- **Applied.**
  - 4,256 bad article pictures were removed: 4,078 shelf cars on other finishes' pages, plus about 178 elsewhere.
  - Second round with tighter rules: 21 more pictures on idea pages and 118 example pictures (e.g. Moonstone on "White, red stripe"). The 8 generic window/top-bar tours were also removed (File Picker, Shokk Drop…).
  - The re-audit now reports 0.
  - Audit list: `_easy_claude_work/enc_fix/reader_fix_audit.json`. Backup: `_easy_claude_work/enc_fix/backup_pre/`.
- **Reader.** On a finish page, `carShot()` now shows only that look's own render; the page's swatch hero already shows the look. Compare already used exact renders only.
- **Titles and labels (same pass).**
  - 49 control-page titles were scanned fragments ("(the color art) 2", "), which is why…", "#candy"). They are now rebuilt from the visible label (`ui_map.json`) plus the section, and `enc_gen_A` uses the same `readable_title`.
  - 233 "Show me" Do-its had no label, which showed raw ids like `btnRender`. They now carry the visible label.
  - Pre-existing syntax error fixed: `enc_gen_A.py` line 528 had an unescaped apostrophe.

### 2b. Pictures round 3: no empty pages and no loose matches
- **Removed rules that let wrong pictures through:**
  - A finish's own car render no longer passes because the page mentions its shelf. "Foundation Bases shelf > Flat Black" in a step had put the Moonstone tie-dye car on 14 idea pages.
  - Shelf heroes need the full shelf name in the page's title, aliases or summary, or a theme word in the page TITLE. Plain shelf words (pattern, shokk, source…) don't count.
- **Pages left with no picture now get the best right one (`best_screen`).**
  - The pick is the screenshot with the most subject words in common that `screen_ok` accepts. 98 pages got one: e.g. "Carbon fibre hood" gets Carbon Weave on the car, and "PSD will not open" gets PSD layers.
  - 3 pages had no matching picture at all (aggressive, look wet, rat rod). They now carry a written `screens_exempt` reason instead of a wrong picture.
  - `enc_v2_test --depth` is green.
- **Round audit.** `_easy_claude_work/enc_fix/reader_fix_audit_round3.json`.

## 3. Do-it handoff (js/spb-encyclopedia.js `runAction`)
- **The colour the page names now comes with the look.** When a page sets a look's colour in the same step or example (stealth: Flat Black + BASE COLOR #0a0a0c), the builder gets the helper's own two-step shape: `body>recolour:near-black #0a0a0c`, then `step1>finish:Flat Black`. Node-checked: `toPlan` produces one op with colour #0a0a0c plus `base::flat_black`.
- **The named look is pre-selected.** The step's look search is set to the look's name, so the grid shows it with the orange ring. The builder's own file was not touched.
- **The step says what will change:** "From the encyclopedia: Flat Black on near-black #0a0a0c (step 1). Press Run to put it on the car; Undo takes it back."
- **"📖 Back to the article: <title>".** A pill re-opens the reader at the same page. It goes away when the reader opens or after 3 minutes.
- **AI-key mode.** The typed request includes the colour ("Use Flat Black in #0a0a0c on the car").

## 4. Raw ids hidden from buyers
- **Labels.** `actLabel` / `controlLabel` fall back to `humanId()` (`btnRender` becomes "Render") and never print an id. A full sweep of every rendered article found 0 raw-id Do-it labels.
- **Footer.** The article id moved to `data-art` on the footer. Setting `localStorage spbEncDev=1` shows it for developers.

## 5. A–Z index and small UX fixes
- **A–Z index.**
  - Digits now have their own "0–9" bucket.
  - The "#" bucket is empty: the 49 fragment titles were fixed at the generator.
  - Same-name twin controls are told apart from their summaries ("90° (placement), clockwise" / "…, counter-clockwise").
- **"YOUR" / "SAME".** Capitals used for emphasis are now bold text, not UI chips.
- **Contents.** An opened Part header scrolls into view.
- **Lessons.** "Next lesson" becomes a quiet "Skip to lesson N" until the check is answered right.
- **Chat window.** It has its own "📖 Encyclopedia" button, because the top-bar one is covered there.
- **Search results.**
  - An ambiguous single word with three near-equal pages shows "Several things in Shokker are called '…'. Pick the one you mean:".
  - A weak match says "No close match… The nearest pages:".
- **New aliases** (dev unchanged at 90.6):
  - "spec map looks wrong in the sim" → The finish looks flat or too shiny.
  - "what is a mask" → ZONE mode and LAYER mode: zone mask.
  - "make the numbers stand out" → numbers-match-body. It still ranks below Make it pop / Stand out in a pack; this is a known, close call.
- **Tried and reverted.** A rule that ranks a page first when the question equals one of its multi-word aliases cost 3 dev rows, so it is not shipped.

## 6. helper_eval: "what does roughness mean"
- **Root cause: a test harness gap, not the ranker.** `helper_eval.js` never loaded `js/spb-enc-search.js`, so it scored the answer module's dead BM25F fallback. The app loads the shared ranker right before `spb-offline-answer.js`. The harness now does the same, and the query lands on `spec.channel_g_roughness`.
- **Result.** 297/297 at 03:4x.
- **Later regression is not from this pass.** At 03:50 the helper worker added 2 new corpus cases for its pending fix pass 6 ("something aggressive", "make it look expensive" → ASK from `ideas.style_menu`). They fail until that builder code lands, which brings the count to 295/297. Neither case is caused by this pass: with the old data JS, or the old ideas.json, it is still 295.

### 2c. Pictures round 4: stricter "best right picture"
- **Tighter rule.** A replacement screenshot must share a word with the page's TITLE or aliases and at least 2 subject words overall. Round 3 had put "The PRO / CHAT pill" on Trading Paints questions on a single shared word.
- **Result.** 48 pages got a right picture. 50 more carry a documented `screens_exempt` and show no picture rather than a wrong one, for 56 exempt in total. Depth is green.
- **CORRECTION (coordinator, by eye): this claim was WRONG.** Retro 90s showed green plaid, Flames a yellow blotchy car with no flames, Wet/glass a teal camo-like car, and both Chrome pages had no picture. Fixed in section 10.
- ~~Looked at 20 fixed pages. All 20 are on-topic:~~ (original text kept below for the record)
  - Chrome pages show only the swatch.
  - Stealth shows a soft-matte spec map, not the blue car.
  - Flames → fire car; Woodland camo → M81 camo car; Retro 90s → flannel plaid; Dragon scales → dragon car; Carbon hood → carbon weave; Wet/glass → dark glass.
  - PSD → PSD layers; Update → update banner; Trading Paints → TGA/.mip diagram; Colours differ → template-layers before/after.
  - Shokk Drop, Japanese art and Platform pages show no picture (exempt).
- Search results now show a repeated FAQ snippet only once.
- In the chat window, "Show me" says the control lives in the full editor and to press **Full editor →** first.

## 7. In-app proof on 59879 (own Chrome, CDP 9815; script `_easy_claude_work/enc_fix/ux/proof.py`; screenshots `p_*.png`, log `proof.jsonl`)
| UX task | Now |
|---|---|
| 3 "spec map looks wrong in the sim" | #1 The finish looks flat or too shiny (troubleshooting); "What the spec map is" is #2 |
| 5 stealth recipe → Do-it | Builder: step 1 whole car → near-black #0a0a0c, step 2 Flat Black on step 1 (ring on Flat Black), note says what changes. **Run** → car turned black, numbers and sponsors untouched ("Done — the whole car (78%) is now Flat Black, in black", version thumbnail before/after). "Back to the article" pill re-opened the stealth page (`p_t5b_builder.png`, `p_t5c_after_run.png`) |
| 8 "what is a mask" | #1 ZONE mode and LAYER mode: zone mask; #2 Wire, Mask and Car_Mandatory |
| 10 "make the numbers stand out" | still #1 Stand out in a pack / Make it pop (numbers article lower): **open** — the fix that helped it cost 3 dev rows |
| 13 "clearcaot" / "tradng paints" | "Showing results for **clearcoat**" / "**trading paints** (you typed …)", right article #1 |
| 14 browse | A–Z: "#" holds only "+1 (expand selection)", digits in "0–9"; Contents Part opens in view |
| 15 Spec Explorer | "spec explorer" → #1 Spec Explorer (interactive) → opens the live tool; "compare two chrome finishes" → #1 Compare tool |
| 19 Show me | "Show me in the app: RENDER", "LAYERS", "Layer eye icon"; footer has no id |
No page errors in the run.

## 8. Gates (final)
- **All green:** enc_test 27/27; enc_v2 --final PASS and --depth PASS; enc_reader_smoke 128/128; builder_test 136/136; convo 18/18 and held 15/15; parity 1689/1689.
- **Search lab dev top-1 matches the baseline:** shared/offline/python 90.6, reader 90.1.
- **helper_eval 295/297.** The only 2 failures are the helper worker's new pass-6 cases (see section 6). Before those were added, it was 297/297.

## 9. Synced, server, follow-ups
- **Copied root → electron-app/server:**
  - spb-enc-search.js, spb-encyclopedia.js, spb-encyclopedia-learn.js, spb-encyclopedia-data.js, spb-chat-studio.js
  - css/spb-encyclopedia.css
  - server_routes/encyclopedia_routes.py
- **Version tokens.** `?v=20261005rf1` in both paint-booth-v2.html copies.
- **Packaged copy was missing the learn script.** The electron copy did not load `spb-encyclopedia-learn.js` at all (no paths / Explorer / Compare in the packaged build); it is now added.
- **Server restart needed.** `encyclopedia_routes.py` changed (did-you-mean, cues, tool-vs-look). The Python ranker only takes it after a restart of 59879 and of the live 59876. I did not restart either.
- **Open items:**
  - Numbers-contrast ranking (task 10).
  - Duplicate finish names (two "Chrome").
  - Slow swatch lazy-load in "More Bases".
  - The builder's look thumbnails tint dark red for a step that builds on a colour step (builder lane).

## 10. Pictures round 5: the picture must SHOW the look (2026-10-05, after the coordinator's eye check)
- **Strict rule (enc_reader_fix.py).** On look pages (ideas, recipes, finishes, patterns, styles):
  - a render or spec map is kept only when its finish / pattern is one the page itself uses (Do-it actions or combos); sharing a shelf or a word is not enough;
  - a look render made for a page (meta.look) only shows on the pages it was judged for;
  - a UI / before-after shot with no finish behind it is kept only when lane S made it for that page;
  - eye verdicts live in `scripts/ai_atlas/enc_pic_verdicts.json` (screens and figures), so a rebuild never undoes a look.
- **Rendered 54 candidate looks** on TEST 59879 (own Chrome 9815, owner's ARCA car, body layers only; `_easy_claude_work/enc_fix/run_looks.py`, PNGs + sheets in `enc_fix/looks/`, every verdict in `looks/_verdicts.jsonl`). **Kept 19, rejected 35 by eye.**
- **The five named pages:**
  - **Retro 90s** → `look_splatter_tee` (Radical: Splatter Tee: teal, purple and pink thrown paint). None of the page's own finishes showed splashes (Rave Zigzag = stripes, Geo Minimal = confetti, Y2K = silver, Flannel = plaid), so the page now offers Splatter Tee (Do-it + a step). Done in the generator `enc_ideas_b03.py` and, for the current file, in `scripts/ai_atlas/enc_ideas_fix_r5.py` (idempotent).
  - **Flames** → **no picture.** I rendered all 10 flame finishes (Hot Rod, True Fire, Ghost, Tribal, Van Flame Job, Candy, Purple, Blue, Pink, Inferno). None draws flame licks on the car: fire blobs, clouds, squares, circles, stars. **Catalogue finding for the finish lane:** the Flames shelf promises "flame licks" that do not render, and the Flames page's Do-it applies Hot Rod Flames (yellow fire blobs).
  - **Wet look / Wet and glass** → no car picture (wet gloss, Sapphire Glass and Crystal Facet are invisible in the flat preview). Wet and glass keeps its clearcoat-scale diagram.
  - **Chrome / Foundation Chrome** → `car_chrome` / `car_f_chrome`: the real 59879 render, paint on the left and the spec map on the right (solid red = full metal, mirror smooth). The app has no lit view, so the captions say the mirror itself shows in iRacing. Chrome with your source colours also shows `car_f_chrome`.
- **Other kept looks:** flat black (stealth, matte-black recipe), 60s sunbursts, 80s pink/cyan, JDM rising sun, neon glow, cerakote grey (fighter jet), FDE (military), digital camo, marble, pastel, nebula, dragon, stars and stripes, great wave (Japanese art), racing green.
- **Audit of 40+ pages, looked at every one** (`_easy_claude_work/enc_fix/ux/pics40.jsonl`, sheets `pics40_a..d.png` and `pics40r2_a..d.png`):
  - Round 1: 37 pages, 27 right and 10 wrong (plaid Base Scale demo on "look fast" and "speed lines", the Chrome spec map on the 50s diner, the yellow star gradient on "black and gold", Chrome-vs-Foundation on sponsor-friendly bases, the Candy zone card on matte black, the PRO/CHAT pill on "match a photo", a worn-chrome map on rear accents, header rows on helmet and suit, a scale diagram on "nine groups").
  - Fixed by the rule plus 4 eye verdicts. Round 2: 38 pages (the 10, the 6 named, 22 new), 36 right; the 2 wrong (Chameleon Fire speckle on "stand out" and "colour shift") are now eye-rejected. Candy and lowrider's new Candy Apple metalflake car was checked: right.
  - Pages that lost a wrong picture show none and carry a no-picture reason (depth bar).
- **Do-it wording:** "is now Flat Black, in black" → "is now Flat Black". The colour words are dropped when the look's name already says the colour (`js/spb-pro-edit.js`, 2 lines + a helper; seen in-app on 59879). Synced to electron; token `-rf2` on spb-pro-edit.js in both html copies.
- **Gates after round 5:**
  - enc_test 27/27; enc_reader_smoke 128/128; enc_v2 --final PASS and --depth PASS; builder_test 136/136; edit_corpus 509/0 mismatches; parity 1689/1689; dev top-1 90.6 shared / 90.1 reader (unchanged).
  - helper_eval 295/297 (the 2 are the helper's pass-6 cases).
  - One source anchor (`js/spb-pro-zone-kit.js:584`) had gone stale because another lane edited that line; the anchor was shortened to the part that is still there.
- **Files this round:**
  - `scripts/ai_atlas/enc_reader_fix.py`, `enc_pic_verdicts.json` (new), `enc_ideas_fix_r5.py` (new), `enc_ideas_b03.py`, `enc_source_anchors.json`
  - `data/encyclopedia/*` (rebuilt; 19 new `screens/look_*.webp` / `car_chrome` / `car_f_chrome`)
  - `js/spb-pro-edit.js` (+ electron copy, token `-rf2`)
  - `SPB_WIKI.html` log bullet
  - `_easy_claude_work/enc_fix/run_looks.py`, `ux/pics40.py`
- **No server restart needed** for this round: pictures and data are served as static files, and the JS is cache-busted.
