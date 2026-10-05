# OFFLINE_BUILDER (2026-10-04) - offline = guided builder + encyclopedia (owner decision)

Lane: NEW `js/spb-offline-builder.js`, NEW `css/spb-offline-builder.css`, NEW `_easy_claude_work/builder_test.js`; ONE surgical hook in `js/spb-pro-ai.js` (after FIRSTTEST `## FINAL`); `paint-booth-v2.html` script/link tags. Test server 59879 only.

## Progress log
- start: read FIRSTTEST / FIRSTTEST2 / ENCYCLOPEDIA_DATA contract, offlineEditAsk, compile, render, send/ask, objectCard, zone-kit region schema (rect + colours combine). FIRSTTEST.md has no `## FINAL` yet -> build + test the new file first, no edits to spb-pro-ai.js / spb-pro-edit.js.
- design: builder = docked section between `.spb-pai-log` and `.spb-pai-bar` (render() only rewrites the log, so the dock survives). Steps -> SpbProEdit ops (colour / part / layer / numbers / sponsors / body targets; recolour = op.colour, finish = op.look (catalogue zone), pattern / shine texture = op.texture; "result of step N" merges into op N = one zone per pixels). Box step = colour of the parent + region.rect (post-compile). Run goes through the existing offlineEditAsk -> finish() path (same undo). Interception only for text TYPED in the panel (harnesses call spbProAI.send directly: unchanged behaviour, gates unaffected).
- core written: `js/spb-offline-builder.js` (flag / fromPlan / fromFlags / fromText / toPlan + box post / check / step editor UI / term card / box editor / claim / attach). `node --check` OK.
- ORCHESTRATOR (2026-10-04, owner: encyclopedia v2 "must FEEL like an encyclopedia"): every encyclopedia read goes through ONE accessor `SpbEnc` in the new file (`lookup(alias)`, `term(id)`, `terms()`, `domainOf(t)`, `article(id)` -> Promise; fetches `data/encyclopedia/<domain>.json` on demand, `{articles:[...]}` or a bare array, falls back to the index entry shaped as an article). Term card = article view (summary / what / when / how / controls table / tips / pitfalls / Do-it actions -> builder steps / links / related (clickable) / sources). BROWSE entry point (`📖 Encyclopedia` in the dock + builder header): search + A–Z / By topic, renders from the 501 index terms now. No article content authored here (other lane).
- gate `node _easy_claude_work/builder_test.js` -> 136/136 GREEN (35 sentences incl. both owner sentences, 24 round-trips = steps->plan compiles to the SAME zones as the parser's plan, 10 partial cases -> open steps, clicks-only yellow->pink->holo+snake = ONE zone, box step = colour test + rect, >12% box refused, flagging user id / holographic / color / snakeskin / number won't show, card->step, SpbEnc fallback). Unknown looks the encyclopedia knows ("carbon fiber", "zebra") are pre-filled with the label-matching / first catalogue choice, shown with an info note before Run.
- existing node gates unchanged: ft2_corpus 35/35, edit_corpus 492/0, stack_test 108/108, enc_test 26/26.
- hook: FIRSTTEST `## FINAL` found (line 33) -> ONE edit in `js/spb-pro-ai.js` directly above `function offlineEditAsk(`: `window.__spbOB` bridge (env / busy / configured / undo / askAI / run) + first line of offlineEditAsk asks `SpbOfflineBuilder.claim()` (typed text only, offline mode only). `node --check` OK.
- html / packaging: `paint-booth-v2.html` link + 2 script tags; spb-pro-ai.js token bumped; js+css now `?v=20261004ob2`. New files added to `scripts/runtime-sync-manifest.json` + `_easy_claude_work/sync_mine.json`; synced root -> electron-app/server.
- in-app (`_easy_claude_work/pw/ob_inapp.py`, server 59879, own Chrome 9781): fixed 3 things found by eye - (1) box editor rendered under the builder, off-screen -> now on top of the dock; (2) a box drawn round the can recoloured the body paint inside the rectangle too (visible pink square) -> the box step now auto-picks the art layer holding that colour inside the box (`boxLayerFor`, SpbProZone.probeRegion) and says so, Where chips can widen it; (3) at 1100px the dock was squeezed to ~80px by the log -> `flex: 0 0 auto`.

## FINAL

**What the buyer sees (offline, no AI key or offline-first on)**
- Typing a request no longer gets a chat answer: the words the app knows are highlighted, and the panel says "I read this as: ① Yellow (base paint + spray can) → Pink ② Holographic + snakeskin shine on ①". The steps sit in a Step builder under the chat. Nothing changes until ▶ Run.
- Each step is three clicks: WHAT (colours on the car with %, parts, layers, numbers / sponsors / whole car, ▭ box-select, or "result of step N"), DO WHAT (recolour / add finish / add pattern or texture / change shine only), WHICH LOOK (real catalogue thumbnails + search + exact colour). Use "+ Add another step", then Run. Undo / Edit the steps / New appear after Run.
- Words the app could not place become open (orange) steps with choices. Run stays disabled and says why. The app never answers "Nothing was changed".
- Highlighted terms open an encyclopedia card: summary, what it is, links, and "Do it" choices that become a builder step. 📖 opens a browser (search, A–Z, by topic) over all 501 terms.
- "Ask DeepSeek instead" sends the same text to the online model. Online and MCP chat are unchanged.

**Files / functions**
- NEW `js/spb-offline-builder.js`:
  - `flag` / `flagHtml`; the `SpbEnc` accessor (`lookup`, `term`, `terms`, `article` → Promise).
  - `fromPlan` / `fromFlags` / `fromText`; `toPlan` + `postFor` (box rect); `check`; `readAs` / `summary`.
  - The UI (`dock`, `draw`, `stepHtml`, `termCardHtml`, `browseHtml`, box editor `initBox` / `boxColours` / `boxLayerFor`); `claim`; `attach`.
- NEW `css/spb-offline-builder.css`.
- `js/spb-pro-ai.js`: ONE hook above `offlineEditAsk` (`window.__spbOB`). Run goes through offlineEditAsk → finish(), so it uses the same undo path.
- `paint-booth-v2.html`: the tags. Both manifests updated.
- Tests: NEW `_easy_claude_work/builder_test.js` and `_easy_claude_work/pw/ob_inapp.py`.

**Gates (before → after)**
- builder_test: new → 136/136 GREEN (35 sentences, 24 round-trips).
- ft2_corpus 35/35 → 35/35. stack_test 108/108 → 108/108. enc_test 26/26 → 26/26.
- edit_corpus 492/0 → 509 phrases / 0 mismatches (another lane added phrases).
- undo_inapp: SUMMARY 8/8 PASS.
- replay_owner after3: runs clean (exit 0, built-in replies, $0.0019).
- ob_inapp: 0 page errors.

**Screenshots (`_easy_claude_work/eval/builder/`) and what I saw**
- `typed_1_flags` / `typed_2_steps`: the owner's pink sentence with 11 highlighted terms, the exact "I read this as" line, two steps, Run enabled.
- `typed_3_after`: base paint and both spray cans are pink and the numbers are untouched. Zones went 5 → 6, yellow 50.9% → 0.1%. Undo brought back zones 5 and yellow 50.9% (`typed_5_undone`).
- `holo_card` / `holo_card_to_step`: Holographic article card with 6 thumbnail choices. Picking one gave step `body>shine:Holographic Drift`.
- `userid_card`: User ID card (Customer ID, 4–7 digits, NOT the car number; where to find it) with support / guide links.
- `browse`: the encyclopedia browser.
- `clicks_1..4`: built only by clicks: Yellow → Pink, then step ① + Holographic + Snakeskin = one zone; yellow 2.7% left. Clicks-only "Yellow" means body paint, so the cans stay yellow.
- `box_1_drawn` / `box_2_step` / `box_3_after`: a box drawn round the top can. Choosing "only the yellow" auto-picked the Logos layer. Only that can turned pink; the body paint and the other can stayed yellow.
- `narrow_1100_page` / `narrow_1100_panel`: at 1100px the panel is 392px wide, the dock has no horizontal overflow, and the steps and Run are visible.

**Gaps**
- When `SpbProEdit.plan` returns nothing (e.g. "make the hood chrome and the roof matte", "make it look like a rattlesnake"), the request still goes to the existing designer / advisor. The builder only gets it through "Put this in the builder" (shown under the live highlights before Send).
- Encyclopedia v2 articles are not authored here (another lane writes them). Cards fall back to the index summary until `data/encyclopedia/<domain>.json` exists. The v2 sections render when it does.
- Spec-texture thumbnails (snakeskin / croc / dragon) are grey roughness previews, so they are hard to tell apart at 72px.
- Offline result cards in the log still carry the older "Ask the AI instead" button next to the dock's "Ask DeepSeek instead". Both do the same thing.
- The box auto-layer picks the single non-base layer with the most of the colour in the box. If art spans two layers, the buyer adds the second one under Where.

## FINAL 2: the standalone SPB Encyclopedia (2026-10-04)

**What the buyer sees.** A **📖 Encyclopedia** button in the Pro top bar, next to Shokk Drop. The 📖 browse button and every term card ("Read the full article ›") in the AI helper open it too, as does a `#enc:<id>` link. It opens a full-window dark reader:
- **Left side.** The 16-Part contents (collapsible, remembered), an A–Z index, and instant search across hand-written articles, quick answers, control pages, glossary words and every finish, pattern and spec-pattern name (with thumbnails). Enter opens the first hit.
- **Centre.** Breadcrumbs, back/forward (Alt+←/→), the Part kicker, a level badge, a lead, and "What it is". Then come real screenshots (large, numbered callout legend, click to zoom), SVG figures, "When", numbered "How", **How it really works**, the controls table, **Worked examples**, **Works with**, ⚡ **Pro tip** boxes, Tips, Watch out, **Common mistakes** (you see / why / fix), **Questions people ask** (collapsible), Do it, and Related.
- **Finish and pattern pages.** A swatch hero, "▶ Try X on my car", and the `car_<key>` car render when lane S has shot one. If there is no shot of that exact look, the `cat_<shelf>` render is shown, labelled as the shelf.
- **Home.** Counts, Start-here cards, the spec-channel figure, Part cards, and a rotating **💡 Did you know?** It shows the articles' `protips[]` (falling back to tips until protips land), changes every 9 s, pauses on hover, and has a Next tip button.
- **Do it and examples.** "Do it" and "▶ Start this on my car" (examples whose settings name a real finish or pattern) build a step in the guided builder with the note "From the encyclopedia: X". Control actions point at the real UI control (flash). If its panel is closed, the reader shows an inline note instead. Examples also have ⧉ Copy settings.

**Files**
- `js/spb-encyclopedia.js` and `css/spb-encyclopedia.css` (new; `?v=20261004enc5` / `enc3`).
  - Data loads on demand: hand domains plus manifests at boot; part files per shelf or page; controls and help parts in the background for search.
  - Reads the index through SpbEnc / `art` pointers. Never edits the data or the index.
- New domains are wired in:
  - `concepts` → Part I
  - `playbook` → Part XIV
  - `help_pages.json` → Part XV "Quick answers" (GEN `help`, search type "Quick answer")
- `screens.json` (lane S) is read as `{screens:[…]}` or a list. `article_ids` attach screens to articles. A screen's `replaces:[figure ids]` hides the redrawn SVG it supersedes; without it, both show, screenshot first.
- `server_v5.py` gained the route `/data/encyclopedia/<path>`:
  - It serves .json/.svg/.webp/.png/.jpg only and refuses `_*` paths.
  - `hidden_features.json` is an alias for `scripts/ai_atlas/enc_hidden_features.json`.
  - The generic route is untouched. 59879 was restarted once; 59876 was never touched.
- `electron-app/copy-server-assets.js` ships `data/encyclopedia/**` (except `_drafts`). `runtime-sync-manifest.json` lists the reader js/css.
- `js/spb-pro-ai.js`, three anchored edits:
  - `entry.builder` flag.
  - The old ask button is hidden on builder replies.
  - Its label now uses the same model name as the builder ("✨ Ask DeepSeek instead").
- `js/spb-offline-builder.js`:
  - `SpbEnc.article` delegates to the reader.
  - Term card "Read the full article".
  - Exports `takeAction`, `linkOut`, `gearName`.
  - `hiddenTerm` filter.
- `paint-booth-v2.html`: the button plus link/script tags.

**OWNER RULE (Easy mode hidden).**
- The reader keeps a built-in HID list, merged at boot with `enc_hidden_features.json` (domains, prefixes, record ids, text patterns). It is applied to domains, articles, manifest parts, terms, catalogue names, search, A–Z, `get()`, and every v2/v3 list field. Sentences that mention a hidden feature are scrubbed.
- Part XIII is now "Chat and the AI helper".
- The builder never flags, cards or browses a hidden term.
- Harness `hidden` result: 0 hits for "easy mode" or "paint by numbers", `get` returns null, no flags, no Part, no page text. The only hit for the bare word "easy" is Brushed Wrap's description adjective.

**Gates (all on test server 59879, CDP 9781):**
- node: builder_test 136/136, ft2 35/35, edit_corpus 509/0, stack 108/108, enc_test 27/27.
- In-app: undo_inapp 8/8, replay_owner after3 exit 0 ($0.0023).
- `enc_v2_test --final`: 6130 articles. The 1 FAIL is not reader code: `screens.json` (lane S, just created) is judged as an article file ("needs {domain:'screens', version, articles:[]}"). Lane A's gate should skip it, or lane S should add the header.
- The owner payload `output/job_render_1791086800_…` was pruned again; I rebuilt it with `pw/ft_rebuild_payload.py`.

**Harness** `_easy_claude_work/pw/enc_inapp.py`: 14 scenarios, 0 page errors, all green.
- The 10 asked for: TOC 16 Parts; spec article (figures 2/2, how 4); Spec Strength control page; Chrome finish page with thumbnail; "user id" → "Your iRacing User ID and car folder"; "clearcoat" → "B channel: clearcoat"; support.not_in_iracing; holographic card deep link → full article with 7 Do-its; Do it → builder step; 1100px with no overflow.
- Plus: hidden, help, real (ui_window_tour loaded with its 10 callouts), and v3. v3 uses a fixture: level badge, 2 screenshots, 2 deep, 2 examples, "Start this on my car (Chrome)" → builder step, 2 combos, 3 FAQ, 2 mistakes, 1 pro tip, lightbox zoom, finish car render, and the home tip rotated.
- Screenshots I looked at, in `eval/builder/`:
  - enc_home, enc_toc, enc_spec_article, enc_finish_page, enc_slider_page, enc_search_userid, enc_trouble_article, enc_deeplink_reader, enc_doit_builder, enc_narrow_1100
  - enc_v3_examples, enc_v3_mistakes, enc_v3_home_dyk, enc_v3_finish_car, enc_real_ui_window_tour

**Gaps**
- No article carries v3 fields yet: the rendering is proven on a fixture only.
- Car renders (`car_*`/`cat_*`) appear as soon as lane S adds them to screens.json.
- Search is heuristic (tiered weights).
- `showControl` cannot point at a control whose panel is closed; it falls back to an inline note.
- The packaged copies of `js/spb-pro-ai.js` and `paint-booth-v2.html` are NOT synced by me (shared with Codex). Mine went through `_easy_claude_work/sync_enc_only.json`. The next release sync carries the html token bump (`own1b`/`ob6`) and the label edit.

## FINAL 3: learning paths, Spec Explorer, Compare and reader polish (2026-10-04)

**Shipped in the reader (my files only; no sub-agents; test server 59879 only; Easy mode stays hidden):**
1. **Learning paths.** There are three courses: *Your first paint* (8 lessons), *Spec mastery* (10) and *Pro workflows* (8).
   - Every lesson is an existing article, plus a 1–2 question check and a "▶ Try it on my car" button. The button opens the step builder with that lesson's look, or points at the control in the app.
   - Answers come from each article's own text.
   - Progress is kept per viewer in localStorage (`spb_enc_paths`, wrapped in try/catch). You see it as a lesson bar with dots, "N of M done", Continue and Reset.
   - The course cards are on the Encyclopedia home. Each lesson article has a "🎓 Lesson N of …" link, and `[` / `]` step between lessons.
   - Lesson ids are checked at load and again in the smoke test.
2. **Spec Explorer** (Part VIII tool entry, linked from every `spec.*` article and from every finish page):
   - R/G/B sliders and number boxes, each with its own colour ramp.
   - The preview balls are cut from the REAL r01 (metal × roughness) and r02 (clearcoat) sweep renders, snapped to the nearest ball.
   - It shows the exact numbers iRacing receives after the iron rules, with a ⚖ note when a rule changes a value. It also gives a plain sentence per channel and names the corner (Chrome only for metal ≥240 with roughness ≤20, otherwise "Polished metal").
   - It shows the matching real spec-viewer screen and the 12 nearest catalogue finishes, taken from a new 4,177-row index. You can try any of them on the car or compare it.
   - There are 10 real-finish presets.
3. **Compare.** Put any two finishes side by side: car render, metal/roughness/clearcoat bars with plain meanings, shelf, best uses, paint advice, and a "difference in one look" summary.
   - Reach it from any finish page ("⇄ Compare with another finish") or from the Part VI tool entry, which has a name picker.
4. **Polish:**
   - Reading width is 780px at 15.5px (820px at 16.5px from 1700px wide), with paragraphs capped at 72 characters.
   - Articles with 5 or more sections get an "On this page" table of contents. It is a sticky strip at 1100px and a right-hand rail from 1420px, and it highlights the section you are in as you scroll.
   - Search ranking is exact title > title phrase > alias > summary. A real bug was hiding the title tiers: an inline `//` comment had swallowed every `else if` branch.
   - A matching FAQ answer now shows inline in the search results.
   - Keyboard: ↑/↓ move through the results and Enter opens the highlighted one.
   - Inline "1. … 2. … 3. …" runs now render as numbered lists.
   - There is a 🖨 Print view (white page, no nav).
   - Fixes: the app's own CSS was greying the quiz answers (an aria-disabled filter) and forcing one cyan colour on every slider track. The 🎛 icon showed as a box and is now 🔬.

**Files:**
- New: `js/spb-encyclopedia-learn.js`, `css/spb-encyclopedia-learn.css`, `data/encyclopedia/reader/paths.json`, `data/encyclopedia/reader/spec_index.json` (built by `_easy_claude_work/enc_spec_index.py`).
- Patched: `js/spb-encyclopedia.js` (extension API `_x`, EXT views/home/artTop/artEnd, mini-TOC, search, keys, print, listify), `css/spb-encyclopedia.css`.
- `paint-booth-v2.html`: four `?v=` tags only (enc11 / enc6 / lrn4 / lrn5).
- The data lives in `reader/` because `enc_v2_test` treats every top-level `data/encyclopedia/*.json` as an article file.
- The learn js/css were added to `scripts/runtime-sync-manifest.json`. Synced with `_easy_claude_work/sync_enc_only.json`, which I trimmed to the 4 reader files (the builder and server files belong to other lanes now); `--check` shows no drift.

**Gates:**
- `enc_reader_smoke.js` (NEW): 128/128 checks pass. It covers the data, the iron rules, snapping, nearest finishes, the view HTML, the links, and search ranking ("clearcoat" → B channel, "user id" → User ID and car folder, "spec map" → What the spec map is).
- `enc_test`: 27/27 pass.
- `enc_v2_test` (default): 376 files, all PASS.
- `pw/enc_inapp.py`: 19 scenarios, 0 page errors. The only console errors are the test server's `/api` 403s.

**Looked at:** `_easy_claude_work/eval/builder/enc_f3_*.png` (22 shots):
- courses, course, course progress, quiz wrong / done
- explorer default / chrome / coat / matte and at 1100 / 1440 / 1920
- finish links, compare and at 1100 / 1440 / 1920
- article at 1100 / 1440 / 1920
- search FAQ, print

**Gaps:**
- The explorer balls are red-paint renders with fixed sweep steps (8×8 metal/roughness at coat 16; coat at metal 150 / roughness 110 only).
- Compare shows a car render only when an exact `car_<finish>` render exists. 53 do; the others get a large swatch, so you never see a different finish standing in.
- The finish page's shelf example render (for example "Moonstone on the car" on Chrome) is captioned honestly but is not the finish itself.
- The spec-viewer screen shown in the explorer is chosen by region (chrome / matte / candy).
- **Not synced (on purpose):** `paint-booth-v2.html` (the new `?v=` tags plus the two learn tags) has not been copied to `electron-app/server/`, because other lanes have edits in flight in that file. The release sync has to carry it, or the packaged app loads the reader without the learn extension. The extension is optional, so the reader still works without it.
