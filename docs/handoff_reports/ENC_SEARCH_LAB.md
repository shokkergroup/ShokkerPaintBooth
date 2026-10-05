# ENC SEARCH LAB: one shared encyclopedia ranker (2026-10-05)

**Owner problem:** the offline helper's how-to answers were only 74% acceptable. Four of its misses: "how do layers work" went to the Save/Open card, "what is candy paint" to the colour slider, "where do the spec maps go for trading paints" to the .shokk card, and "how do i add a number" to retro stripes.

**Result:** all three searches now run on ONE ranker, `js/spb-enc-search.js` (UMD, VERSION `2026-10-05.3`):
- the offline helper (`js/spb-offline-answer.js` search())
- the reader search box (`js/spb-encyclopedia.js` search())
- the server / MCP search (`server_routes/encyclopedia_routes.py`, a Python mirror that reads its constants from the JS file)

All four owner examples now land on the right card in-app (shots below).

**Targets: NOT reached.** The targets were held top-1 ≥88% and top-3 ≥96%. Held is **86.3 / 95.1**. On freshly written, more colloquial question sets the ranker scores only about 69–71% top-1. Details below.

## Benchmark (`_easy_claude_work/search_lab/`)

| Set | Size | Notes |
|---|---|---|
| `bench.jsonl` | 1,226 q, 265 topic clusters | Split 50/50 **by cluster**: dev 615 / held 611. Gold ids live in `bench_src_*.txt` and are compiled by `compile_bench.js`. 14 questions are flagged GAP: no article answered them, so they became the two new articles. |
| `bench_held2.jsonl` | 136 q | Written later, in fresh phrasing. Used as a diagnostic set after the first final scoring (see disclosures). |
| `bench_held3.jsonl` | 87 q | Written and sealed before any fusion work. Scored **once**. |

## Results (top-1 / top-3 / MRR)

| Search | DEV | HELD | HELD2 (diagnostic) | HELD3 (sealed, once) |
|---|---|---|---|---|
| BASELINE offline helper = server (old ranker, old data) | 74.8 / 87.6 / .815 | 78.9 / 89.5 / .845 | 58.1 / 74.3 | – |
| BASELINE reader search box | 39.0 / 48.8 / .444 | 36.3 / 48.6 / .428 | 10.3 / 20.6 | – |
| old offline ranker + NEW data | 84.2 / 95.6 / .898 | 83.8 / 93.0 / .886 | 72.1 / 85.3 | 63.2 / 74.7 |
| shared ranker, main channel only (.2) | 90.2 / 98.2 / .941 | 85.1 / 94.6 / .898 | 64.7 / 82.4 | 70.1 / 82.8 |
| **FINAL shared (.3) = offline helper = Python server** | **89.6 / 98.5 / .939** | **86.3 / 95.1 / .907** | **69.9 / 84.6** | **69.0 / 81.6** |
| **FINAL reader search box (full corpus)** | **89.9 / 98.4 / .940** | **85.6 / 94.3 / .900** | 68.4 / 80.9 | 71.3 / 81.6 |

- The tables come from `final_table.txt` (`node final_table.js`) and `held3_table.txt` (`node score_h3.js`).
- The baseline was re-scored against the current gold. The GAP questions count as baseline misses, because no article existed for them.

**Speed**
- Shared index build is 165–280 ms.
- A query averages 1.5 ms. The worst case is 37 ms, which is the first unknown word building the typo map.
- The offline helper boots in about 430 ms in Node.
- The reader builds its article index on the first search, in about 230 ms. Its catalogue index is built deferred, in about 260 ms.
- Python takes about 25 ms per query.

## The ranker (`js/spb-enc-search.js`)

**Main channel**
- BM25F over 7 fields: title, aliases, FAQ questions, summary, control labels, mistake symptoms, body. Field weights are tuned on DEV only.
- An F-beta match against the title, each alias and each FAQ question, plus a bonus when the question is exactly one of them.
- A phrase (bigram) boost and a whole-title boost.
- Intent detection (what / how / where / problem) multiplied by the kind of article, plus kind and domain priors.
- Synonyms and expansions, and typo repair with delete-1 and delete-2 neighbours.
- A prefix mode for the reader.
- Help pages get ×0.92. Anything that mentions Easy mode is excluded.

**Plain channel (new in .3)**
- This is the old helper's one-bag BM25 with its title and alias bonuses. It is fused with the main channel by reciprocal rank: `1/(1+rank) + 0.75/(1+plain rank)`.
- The main channel overfit to bench phrasing: held2 scored 64.7, against 72.1 for the old ranker on the same data. Fusion bought +1.2 on held, +5.2 on held2 and the best DEV top-3, at a cost of −0.6 DEV top-1 and −1 question on held3.

**Score scale:** after fusion, the main channel's scores are handed back out in the new order. The helper's score thresholds (`confident()`, the route shortcut) therefore keep their meaning.

## Python mirror and parity

`server_routes/encyclopedia_routes.py` reads these straight from the JS source, and re-reads them when the JS file changes:
- STOP, SYN, EXPAND, FIELDS, K1, EXP_W
- KIND_PRIOR, DOM_PRIOR, P, LFW
- every intent regex, and VERSION

**Parity: top-1 matches 1689/1689 = 100%** (`enc_parity.py` over bench + held2 + the earlier parity sets).

## Knowledge added (`data/encyclopedia/**`, written atomically and only to fields this lab owns)

**Two new full-depth articles**, with `sources[]` file:line and anchors built:
- `recipes.add_race_number`: either iRacing stamps the number (Sim-Stamped Number) or you paint your own (Custom Number), plus the layer route.
- `workflows.platform_and_limits`: Windows only, iRacing only, price via Buy License, no Mac / other sims / animated / glow, wheels only where the sheet has them.

**About 1,032 aliases** across about 28 article files, written by `apply_aliases.py` in format-preserving round trips. About 145 aliases were skipped because another article already owns them.

## Gates (`run_gates.sh` → `gates_fused2.txt`, all with the shared ranker loaded like the app)

| Gate | Result |
|---|---|
| helper_eval | **297/297** (no regression) |
| builder | 136/136 |
| ft2 | 35/35 |
| edit | 509 / 0 mismatches |
| stack | 108/108 |
| convo dev | 18/18 |
| convo held | **15/15** |
| enc_test | 27/27 |
| enc_v2 --final | PASS (378 files, 6,088 articles) |
| enc_v2 --depth | PASS |
| enc_reader_smoke | 128/128 |
| parity | 100% |

## In-app on the TEST server 59879 (never 59876)

Run with `inapp_check.py` (own headless Chrome on CDP 9767). Shots are in `_easy_claude_work/search_lab/inapp/` and every one was looked at.

**Helper (previously missed):**
- "how do layers work" → What are layers? (`h1_layers.png`)
- "what is candy paint" → Candy colours (`h2_candy.png`)
- "where do the spec maps go for trading paints" → Trading Paints and .mip files (`h3_tp.png`)
- "how do i add a number" → Put a race number on your car (`h4_number.png`)
- "will this run on my mac" → Windows, iRacing, price… (`h5_mac.png`)

**Reader:**
- "how big does the paint have to be" → The paint must be 2048×2048 (`r1_size.png`)
- "my car is black in iracing" → Black paint or missing parts (`r2_black.png`)
- "can i use it for acc paints" → wrong at first (How do I paint on a layer by hand?). After 10 other-sim aliases were added (acc, assetto corsa competizione, automobilista, …) it goes to Windows, iRacing, price… (`r3_acc.png`).
- Page errors: 0.

**Seen in the shots, other lanes (not search):**
- The helper card's DO IT buttons show raw ids: "Show me rpTabLayers" and "Show me pro render copy tp desc".
- The candy card's picture is the header-boxes screen, not a candy screen.
- The chat line reads "What are layers?:" (double punctuation).

## Disclosures (honest accounting)

- I wrote every benchmark question myself, so the phrasing is not from real users. Held3 shows how much that flatters dev and held: about 70% on more colloquial questions.
- Alias rounds 1–2 were partly derived from DEV misses.
- Held aggregates were peeked three times. Held misses were **viewed once**, to classify phase-4 gaps. Every peek is logged in `held_peeks.log`. Held is therefore not perfectly clean.
- Held2 became a diagnostic set after it exposed the overfit. The decision to add the plain channel used held2 alongside DEV top-3.
- Held3 was scored once, before the 10 other-sim aliases. Those aliases came from the in-app check, which reused one held3 question. The held3 numbers above are from before that change.

## Next (if someone picks this up)

- The remaining gap is phrasing generalisation, not missing articles. Real user questions (`output/ai_logs/copilot_turns.jsonl`) should become the next benchmark.
- Short, noisy round-3 aliases are suspect: "no effect" matches Layer Effects, and rare words dominate ("hour ago" → update banner).
- Fix the DO IT raw-id labels (UI-label lane).

## ROUND 2 baseline (blind casual set, scored once BEFORE any change, ranker VERSION 2026-10-05.3)

Set: `_easy_claude_work/casual_set/casual.jsonl` (585 q, 55 topics, written blind by another worker; tune 309 / test 276 split by topic). Gap rows (28) excluded. Top-1 / top-3 / MRR:

| search | TUNE all | TUNE without weak | TEST all | TEST without weak |
|---|---|---|---|---|
| shared = offline helper = Python server | 72.1 / 85.9 / .790 (n298) | 72.2 / 86.3 / .790 (n291) | 63.3 / 79.5 / .723 (n259) | 65.3 / 80.9 / .740 (n251) |
| reader search box | 73.5 / 84.6 / .788 | 73.5 / 84.5 / .788 | 62.9 / 76.4 / .706 | 64.9 / 78.1 / .724 |

Result files sealed in `_easy_claude_work/search_lab/cas_sealed/` (scorer `score_casual.js`). Test-split misses are not looked at; test is scored again exactly once at the end.

## ROUND 2 result (ranker VERSION 2026-10-05.4)

**Bottom line: no gain on the blind casual TEST split.** Shared ranker, top-1 / top-3 / MRR:

| Run | TEST all | TEST without weak |
|---|---|---|
| before | 63.3 / 79.5 / .723 | 65.3 / 80.9 / .740 |
| after (scored once) | 62.9 / 79.2 / .714 | 64.5 / 80.9 / .729 |

The reader went from 62.9 / 76.4 to 63.3 / 76.1. The offline helper and the Python server are identical to the shared ranker (parity 100%).

### All sets, before and after round 2

| Set | Before | After |
|---|---|---|
| Casual TUNE | 72.1 / 85.9 | 72.5 / 84.9 |
| DEV | 89.6 / 98.5 | 89.3 / 98.0 |
| HELD | 86.3 / 95.1 | 84.6 / 94.4 |
| held2 (diagnostic) | 69.9 / 84.6 | 66.9 / 86.0 |

### Why it is flat

My changes and a new data file pulled in opposite directions.

**My changes helped on their own.** Measured before `ideas.json` existed: DEV 91.5 / 98.7, casual TUNE 74.5 / 85.9, held2 69.1 / 84.6.

**`ideas.json` cost more than that.** Mid-round, another worker added 70 style-idea cards with about 790 broad aliases.
- At full weight they took ordinary how-to questions: DEV fell to 87.6, TUNE to 69.5 and held2 to 61.0.
- I set `DOM_PRIOR.ideas` to 0.7. That keeps 10 of my own 12 vague style questions ("make it look aggressive", "stealth", "retro"…) on an ideas card and gets most of the loss back.
- 0.5 recovers more (DEV 90.1, held2 69.1) but keeps only 7 of 12 style questions on ideas. This is a one-number trade-off for the orchestrator (`ideas_sweep.js`).

**Some ideas aliases are too broad** (for the ideas worker). Examples of how-to questions they took:
- "how to make something look like polished metal" → `ideas.marble_stone`
- "metalflake finish" → `ideas.vintage_diner_50s`
- "change the blue parts to red" → `ideas.patriotic_rwb`

### What changed

**Words**
- Casual past tenses and slang: undid / undone / undos → undo, wetter → wet, lit → lighting, pic / pics → picture.
- Near-synonyms: sandpaper and grainy → rough, lasso → select, wet → gloss, cheap / expensive → pop.
- wtf, omg, bruh, dude and guys are now ignored.
- A misspelled "trading panits" is joined back into Trading Paints after typo repair.

**Parameters**
- I re-tuned on DEV plus casual TUNE (`tune.js` with `CAS=1`).
- The full optimum overfit: held2 fell 2.3 points. I applied a half step instead (geometric mean of the old and new values) to P, FIELDS, KIND_PRIOR and DOM_PRIOR.

**6 new articles** with `sources[]`. Facts come from the code; where the repo says nothing, the article says so and points to support.
- `recipes.named_looks`: the real finishes Tri-Coat Pearl, Forged Carbon Visible / Forged Composite, Anodized (x2), Blackout / Blackout Ops and Rally Mud. There is no bug-splatter finish, and the article says so.
- `tools.editing_limits`: Transform with rotate 90 / 180, Flip H / V, Restrict to Layers as the nearest thing to a clipping mask, Healing Brush since the Clone Stamp was cut. There is no crop and no whole-paint flip. Undo depth: 60 selection / 30 layer / 15 zone / 6 brush steps, from the code constants.
- `support.image_files`: 24-bit RLE TGA, Export to Photoshop, Export PNG and Channel PNG Export, and why logos go blurry.
- `playbook.colour_matching`: hex box and screen eyedropper on BASE COLOR. There is no Pantone library and no colour-blind mode.
- `workflows.business_and_sharing`:
  - GPU: optional CuPy, CPU fallback (`engine/gpu.py`).
  - Refund, beta, minimum specs and selling rights: not stated in the app, so ask via Settings gear > Report a Problem.
  - Two PCs and teamwork: share files (projects, SHOKK files, recipes, ZIP package). No cloud sync, no live co-editing.
- `workflows.iracing_side`:
  - You need the car's paint folder, which iRacing creates the first time you run the car.
  - Pit stall, interior and iRacing's own store are not Shokker targets.

**Gap questions:** all 28 now land top-1 on a new article. This is not independent: the aliases were written from the README's gap wording.

### Gates

| Gate | Result |
|---|---|
| helper_eval | 297/297 |
| builder | 136/136 |
| ft2 | 35/35 |
| edit | 0 mismatches |
| stack | 108/108 |
| convo dev | 18/18 |
| convo held | 15/15 |
| enc_test | 27/27 |
| enc_v2 --final | PASS (379 files, 6164 articles) |
| enc_v2 --depth | PASS |
| reader smoke | 128/128 |
| parity | 100% |

One parity run showed 95%. That was transient: `ideas.json` landed between the JS and Python passes, and a rerun gave 1689/1689.

Electron copies of `spb-enc-search.js` and `encyclopedia_routes.py` are synced, and the ranker token is now `20261005sx3`. I did not touch `spb-encyclopedia.js` or the data bundle.

### Real owner turns: none usable

`output/ai_logs/copilot_turns.jsonl`, as of the round-2 check:
- 125 carry `port` 59879, the test server.
- None carry 59876.
- The 46 rows without a port are scripted conversation-gate turns (paint edits such as "roof black" or "darker") plus probes. These are not encyclopedia questions, and their origin cannot be proven.

So I seeded no owner set rather than mislabel test traffic. Once real 59876 questions are logged with a port, they should become the next benchmark.

### Protocol log (`held_peeks.log`)

1. Baseline: TUNE and TEST scored once, before any change. Result files sealed in `cas_sealed/`.
2. Tuning: I looked at TUNE-split misses only (`misses_cas.js` filters to tune).
3. TEST: scored exactly once at the end.
4. HELD: aggregates peeked a 4th time for the table above. held2 is still diagnostic only, and it informed the half-step choice.

## ROUND 3 (paraphrase bank)

Ranker version 2026-10-05.5.

**Bottom line: the casual TEST split went up modestly, about 6 questions out of 259.** Shared ranker, top-1 / top-3 / MRR:

| Run | TEST all | TEST without weak |
|---|---|---|
| round 2 | 62.9 / 79.2 / .714 | 64.5 / 80.9 / .729 |
| round 3 (scored once) | 65.3 / 81.5 / .737 | 66.9 / 83.3 / .755 |

- The Python server mirror gives identical numbers.
- The reader TEST score rose from 63.3 / 76.1 / .702 to 64.5 / 78.8 / .719.

**Other sets**

| Set | Round 2 | Round 3 |
|---|---|---|
| Casual TUNE | 72.5 / 84.9 | 75.2 / 86.9 |
| DEV | 89.3 / 98.0 | 90.6 / 98.4 |
| HELD | 84.6 / 94.4 | 86.1 / 95.9 |
| held2 | 66.9 / 86.0 | 67.6 / 89.7 |

### What was built

**The bank file:** `js/spb-enc-qbank.js`.
- 533 articles and 7,768 casual questions, about 199 KB.
- Generated by `_easy_claude_work/search_lab/build_qbank.js` from the blind writer's `_easy_claude_work/paraphrase/qbank.jsonl`.
- Every id resolves to an article and no question names the hidden mode.
- It is kept out of the 1.2 MB index.

**How it loads:**
- **Browser:** `spb-enc-search.js` injects it 1.5 s after the page `load` event (token `qb1`, inside the ranker). Any index built before it lands is rebuilt in place, as the same object, when it arrives. This was tested with a late-arriving bank. A search before then simply runs without the bank.
- **Node:** loaded with `require`.
- **Server:** `server_routes/encyclopedia_routes.py` reads the same file, and its index signature now includes the bank's and the ranker's file times.

**How it is used**, two ways at once:

1. **Document expansion.**
   - Each article's bank questions become a new BM25 field `p` (weight 1, b 0.5).
   - Each bank question also becomes a "nearest question" unit. The best F-match scores x`up` 2; the exact-match bonus `xp` is 0.
2. **Nearest-question channel.**
   - Matching is a TF-IDF cosine over char 3/4-grams, words and word pairs.
   - It runs on the ranker's tokens, keeping stop words (dropping them made "what is a zone" match "zone not showing"), with typo repair on the asked question.
   - An article's score is its best question plus 0.3 x its second best.
   - Blend: `1/(3+rank+1) + 0.1*sim` for sims >= 0.3.
   - Scores are reassigned by position, so the helper's thresholds keep their meaning.
   - When the top hit's sim is >= 0.6, its coverage is lifted to that sim.

**Speed.** Adding about 7.7k units tripled query time (median 1.9 -> 6 ms, p95 4 -> 14 ms in Node).
- I rewrote the unit match to visit only units that share a word with the question (a word -> (doc, unit) postings list), in JS and in the Python mirror alike.
- I also gave the cosine channel a typed accumulator.
- Results are unchanged (tune objective 258.38 both ways) and parity is 100%.

### Fitting (DEV + casual TUNE only; log in `qb_tune.jsonl` and `qb_tune_cosine_v1.jsonl`)

Objective = top-1 + 0.5 x top-3 over DEV and casual TUNE. Round 2 scored 253.23.

| Variant | Objective | DEV top-1 | TUNE top-1 |
|---|---|---|---|
| Cosine channel only, stop words dropped | - | below baseline | 68.8 |
| Cosine channel only, best grid point | 255.5 | - | - |
| Bank as a field + units | 255.2 | - | - |
| Both + second-nearest vote | **258.38** | 90.6 | 75.2 |

- With stop words dropped the cosine channel fell below the baseline at every weight.
- Bank questions on their own reach 77-79 top-1 on DEV but only 55-60 on TUNE. Even at sim >= 0.8 they are only 76% precise on TUNE.
- Two things limit the bank:
  - It routes phrases to one of several near-duplicate articles: help_howto_* / help_topics_* versus the core articles, and ideas.* versus recipes.*.
  - Gold labels often name the other twin.
- A heavier bank weight (qw 0.2-0.4, any gate) lowered TUNE by 2-8 points. So it stays light.
- I did not try LSA. Char-gram TF-IDF alone already trails the main ranker, and the blend optimum is flat, so there was no sign LSA would clearly win.
- I left `qcs` (char grams from content words only) at 0. It moved DEV +2.4 but TUNE -1.3 in the bank-alone test.

### Speed

| Measure | Result |
|---|---|
| Helper boot (`helper_eval` harness) | 2,047 ms (< 2.5 s) |
| Helper boot in-app on 59879 (encyclopedia load + first search, which builds the index with the bank) | 406 ms |
| Queries in-app (300 timed) | median 0.8 ms, p95 2.8 ms, max 4.7 ms (< 15 ms) |
| Queries in Node (924 timed) | median 1.6-1.9 ms, p95 4.3-5.1 ms |
| Index build in Node | about 430 ms |
| Python server query | about 30 ms average (not in the helper's budget) |

The bank's script takes 3.4 ms to evaluate.

### ideas.json aliases (aliases only; re-read right before; atomic write in the file's own one-article-per-line layout)

Script: `_easy_claude_work/search_lab/fix_ideas_aliases.py`.

| Card | Old alias | New alias | Result |
|---|---|---|---|
| `ideas.patriotic_rwb` | "red white and blue" | "red white and blue scheme" | "change the blue parts to red" now gets `help_howto_1.change_one_colour` |
| `ideas.marble_stone` | "polished stone" | "marble or stone finish" | "polished metal" **still** goes to `ideas.marble_stone` |

The marble miss remains because the card's **title** says "veined, polished and natural". Fixing it needs a title change by the ideas owner, which is outside the aliases-only rule.

### In-app check on 59879 (screenshots in `_easy_claude_work/search_lab/inapp_r3/`, all looked at)

The questions are new ones I wrote, not from any benchmark split.

**Helper, 2 of 5 good:**

| Question | Result |
|---|---|
| "how do i make it look wet and shiny" | Correct: "Make it look wet" card |
| "my paint wont show up in the sim" | Correct: the helper's live support checklist answered |
| "how do i put a stripe down the middle" | Weak: "Reading the flat sheet" card. Stripe articles ranked 2-3; the bank had `ideas.racing_stripes` at 0.71 but its weight is light |
| "oops how do i go back a step" | Miss: "I did not catch that" (top match coverage 0.31). The bank found undo at 0.65 but it did not reach rank 1 |
| "wat does the spec thing even do" | Not answered offline: fell through to the online model |

The last one used **DeepSeek on the test server, a real call costing $0.0012**.

**Reader, 3 of 3 good:**
- "sparkly flakes in the paint" -> Metal flake and pearl.
- "where does it save my stuff" -> How do I save my project.
- "my logo looks blurry" -> the TGA / blurry-logo article.

Page errors: 0.

### Gates (`gates_r3.txt`): all green

| Gate | Result |
|---|---|
| helper_eval | 297/297 |
| builder | 136/136 |
| ft2 | 35/35 |
| edit | 0 mismatches |
| stack | 108/108 |
| convo dev | 18/18 |
| convo held | 15/15 |
| enc_test | 27/27 |
| enc_v2 --final | PASS |
| enc_v2 --depth | PASS |
| reader smoke | 128/128 |
| parity | 1689/1689 |

The gate preload (`preload_sx.js`), `eval.js` and `enc_parity.js` now load the bank the way the app does once it has landed. `NOQB=1` gives the state before it lands.

### Files

**Changed:**
- `js/spb-enc-search.js`
- `js/spb-enc-qbank.js` (new; added to `scripts/runtime-sync-manifest.json`)
- `server_routes/encyclopedia_routes.py`
- `data/encyclopedia/ideas.json` (2 aliases)

The JS and Python files are synced to `electron-app/server`. The ranker token is `20261005sx4` in both `paint-booth-v2.html` copies.

**Lab:** `build_qbank.js`, `qb_tune.js`, `qb_alone.js`, `qb_docexp.js`, `qb_timing*.js`, `inapp_check_r3.py`.

### Disclosures (`held_peeks.log`)

- TEST: scored exactly once, at the end.
- HELD: aggregates peeked a 5th time for the table above.
- held2: shown only in the final table and not used for any round-3 decision.
- TUNE-split misses were viewed (`qb_miss.js`). TEST misses were not.

## ROUND 4 (casual)

Goal: make the search understand casual buyer phrasing. Ranker at start: VERSION 2026-10-05.6. Runner: `_easy_claude_work/search_lab/r4.js <tag> [shared|reader]` (one process, one verdict line for all sets; `C150=1` adds the blind held-out).

**Protocol.** Held-out = `_easy_claude_work/eval/blind5/casual150.jsonl` (150 q, 9 gap rows). Scored once at the start and once at the end; results sealed in `search_lab/r4_sealed/` with ids only (no question text). Its questions are not read. Tuning: misses viewed on casual TUNE split + held2 only; casual TEST split + held3 are aggregate-only generalisation checks; dev/held are regression guards (must not drop > 0.5).

**Gap scoring rule (fixed before any change).** A gap row (gold = []) counts as correct at top-1 when the top hit is NOT confident by the helper's own bar (cov >= 0.34 and score >= 2.4, so the helper says it has no card and offers the nearest), or the top hit is an article that honestly states the limit (`workflows.platform_and_limits`, `tools.editing_limits`, `workflows.iracing_side`, `workflows.business_and_sharing`), or one of the new round-4 gap articles. Top-3: the same test on any of the top 3.

### Baseline (scored once, before any change)

| Search | casual150 non-gap top-1 / top-3 / MRR (n141) | finish (38) | spec (24) | tool (29) | symptom (27) | export (14) | ideas (9) |
|---|---|---|---|---|---|---|---|
| shared = offline helper = Python server | 86.5 / 92.9 / .903 | 84.2 / 86.8 | 79.2 / 83.3 | 89.7 / 100 | 88.9 / 100 | 92.9 / 92.9 | 88.9 / 100 |
| reader search box (full corpus) | 87.2 / 92.9 / .906 | 86.8 / 86.8 | 79.2 / 83.3 | 89.7 / 100 | 88.9 / 100 | 92.9 / 92.9 | 88.9 / 100 |

Gap rows (shared), top-1 correct **2 / 9**: c5-039 → `workflows.platform_and_limits` (honest), c5-125 → not confident (honest). The other 7 land confidently on unrelated cards (`ideas.neon_night`, `finishes.nature_tactical_cyberpunk`, `ideas.liquid_metal`, `spec_sculpt.generation_dna`, `support.wont_start_or_update`, `ai_copilot.gear_key_model`, `recipes.camo`).
**Overall incl. gaps (shared): top-1 124/150 = 82.7%.**

Note: the casual150 non-gap score (86.5) is already far above the older casual sets, so the old-set ~70% does not carry over to this writer; most of the held-out headroom is in the gap rows and in finish/spec.

Other sets at start (shared / reader), top-1 / top-3 / MRR:

| Set | shared | reader |
|---|---|---|
| DEV (n615) | 90.6 / 98.4 / .945 | 90.1 / 98.0 / .940 |
| HELD (n611) | 86.1 / 96.1 / .911 | 85.1 / 96.1 / .904 |
| held2 (n136) | 69.1 / 90.4 / .798 | 67.6 / 89.7 / .786 |
| held3 (n87) | 73.6 / 86.2 / .804 | 73.6 / 86.2 / .802 |
| casual TUNE (n298) | 75.8 / 86.9 / .811 | 77.2 / 87.2 / .821 |
| casual TEST (n259) | 66.8 / 83.0 / .750 | 65.3 / 80.3 / .726 |

### Mechanism (ranker VERSION 2026-10-05.7)

**Question rewrites (`REWRITE` in `js/spb-enc-search.js`, mirrored by `sx_rewrite` in `server_routes/encyclopedia_routes.py`).** A table of `[/regex/, 'replacement']` rows, one per line, run on the spell-repaired question before tokens and intent (`spell -> rewrite -> cue`). The Python mirror reads the rows from the JS file (`_js_rewrite`, `$&`/`$n` converted to `\g<0>`/`\g<n>`), so the two cannot drift. Rewrite-step parity: 2043/2043 questions (`r4_rwpar.py`). Every row is a phrasing class:
- texting slang -> plain words (`y` at the start -> why, b4, cuz, idk, smth, teh, gotta, lemme);
- filler openers stripped or turned into "how to" ("is there a way to", "is it possible to", "whats the best way to", "anyone know", "for some reason", "in this app");
- verb -> tool intent: "send / get / put it to my car / into iracing", "race with it", "finished, now what" -> export; "go back a step", "messed up", "oops" -> undo; "a finish called X" -> search finishes by name; "bring in" -> load; "start a new zone / layer" -> add; change verb + two colour words -> change one colour; "only change the shine", "keep my colours" -> spec only;
- symptom -> topic: stock / old paint in the sim, "cant see it in the session" -> paint not showing in iRacing; "shows for me but not on the grid", "my buddy cant see it" -> other drivers; "looks like sandpaper / chalky / primer" -> finish looks flat; "chrome looks grey on track" -> chrome looks dark; texture "massive / huge" -> tiny-or-huge scale; "shrink the weave" -> pattern finer; "zone / finish isnt painting / has no effect" -> zone does not show; preview "shows nothing / blank / stuck" -> fix preview; red / green / blue next to "spec" -> that channel.
- EXPAND: massive / enormous / giant / gigantic -> big, huge, scale; reflection -> shine, gloss, spec.

Rows that showed no gain or a net loss in a per-row ablation (`r4_ablate.js`, `r4_diff.js`) were removed: a "values / numbers for shiny metal" row, a broad size row, an "only on the roof" row and a "what now" row (that one cost a DEV question).

Sets after the rewrites (shared, top-1 / top-3): DEV 90.9 / 98.4 (was 90.6 / 98.4), HELD 86.4 / 96.4 (86.1 / 96.1), held2 77.9 / 97.1 (69.1 / 90.4), held3 77.0 / 88.5 (73.6 / 86.2), casual TUNE 76.5 / 87.6 (75.8 / 86.9), casual TEST 66.8 / 83.4 (66.8 / 83.0). The aggregate-only checks moved too (held3 +3.4), but casual TEST stayed flat: most of its remaining misses are twin-article labels and catalogue items that the helper corpus does not hold.

### Gap articles (lane C, 2026-10-05, full depth bar; script `_easy_claude_work/search_lab/new_articles/add_articles_r4.py`)

Every claim was checked against the cited lines (a checker printed each cited line before the write; 19 wordings were corrected or dropped where a line did not back them up, e.g. invented finish colours, a Transform "flip" claim, an undo-depth claim). Where neither the app nor the docs say anything (how iRacing draws rain, damage, frame rate), the article says Shokker has no setting for it and gives the nearest real workflow.

| id | what it says | key sources |
|---|---|---|
| `recipes.glow_look` | no emissive paint; alpha only turns lighting down; fake it with Arcade: Phosphor Green / Vector Glow, Bioluminescent, Firefly Glow on dark + Outer Glow (size 1-50) | 05_design_and_taste.md:31, how_do_i.md:794, finish-data 312/317/591/690, v2.html:5170-5200, state-zones:1910 |
| `cars.wheels_and_rims` | only where the template sheet has them; no rim files claimed; Wire/Mask to find, APPLY AREA box, Foundation Chrome/Satin Chrome | 06_layers:8/11, 10_support:7/19, finish-data 701-706, v2.html:3805 |
| `cars.interior_and_dashboard` | only cockpit areas that are on the sheet; no interior file; helmet/suit not written | 06_layers:8, 10_support:19, SPB_WIKI.html:1044 |
| `workflows.rain_and_wet_track` | one paint + one spec for every weather; preview cannot show rain; Wet Look / CC Wet Zone | 10_support:19/23, support-answers:22, finish-data 1077/4961 |
| `workflows.crash_damage` | no damage files; worn look via Hardware: Battle Worn, Desert Worn, Die-Back Patina, Rally Mud + Base Strength (no Season mode) | 10_support:19, finish-data 152/441/650/993, state-zones:2098 |
| `tools.liquify_and_warp` | no Liquify/Warp; Transform Ctrl+T, Smudge (Q) Strength 1-100; warp in Photoshop and reopen via PSD/XCF/ORA | v2.html:2281/2283/2353-2361/2873-2878/3844, how_do_i.md:795 |
| `support.fps_and_performance` | Shokker cannot measure/change iRacing FPS; file is the template size whatever the finish; 2048 textures option needs an iRacing restart; render time = zones/masks/heavy finishes | 10_support:19/23, support-answers:50-57/125, v2.html:3578 |
| `workflows.view_in_3d` | no 3D view, no OBJ/FBX/GLB export; iRacing 3D Car Viewer (My Content) / Ctrl+R in session | self-help:580, how_do_i.md:791-795, 10_support:23, v2.html:3531-3532 |
| `recipes.number_fonts` | no font/number tool; Sim-Stamped = iRacing's style; custom = transparent PNG via + Layer, Move/Transform, STROKE FX, Custom Number + Hide Car Numbers ON | v2.html:1797-1801, support-answers:28, 10_support:13/23 |

Aliases moved to the dedicated articles: "glow in the dark", "rims", "paint my wheels" (from `workflows.platform_and_limits`) and "paint the interior" (from `workflows.iracing_side`). All other aliases are phrasing classes (topic nouns + common verb forms), not copies of test questions. Rebuilt with `python scripts/ai_atlas/build_encyclopedia.py` (the build's own anchor-repair and picture-audit steps also touched ai_copilot/layers/zones json; the picture audit dropped the screens of `recipes.glow_look` and `recipes.number_fonts`, which are now screens-exempt).

**FACT ERROR in another lane (not fixed here):** `finishes.wear` tells buyers to use Season mode / a wear ramp, but Season mode is RETIRED (`paint-booth-5-api-render.js:2645-2660`, `_showRetiredBatchModeToast`) and there is no wear slider in the root UI.

### FINAL held-out (casual150, sealed, scored ONCE)

| search | ALL non-gap n141 | finish 38 | spec 24 | tool 29 | symptom 27 | export 14 | ideas 9 | gaps top-1 (9) | overall incl. gaps |
|---|---|---|---|---|---|---|---|---|---|
| shared BASELINE | 86.5 / 92.9 | 84.2 / 86.8 | 79.2 / 83.3 | 89.7 / 100 | 88.9 / 100 | 92.9 / 92.9 | 88.9 / 100 | 2 / 9 | 124/150 = 82.7 |
| shared FINAL | 85.8 / 93.6 | 84.2 / 86.8 | 79.2 / 87.5 | 89.7 / 100 | 85.2 / 100 | 92.9 / 92.9 | 88.9 / 100 | 8 / 9 (9/9 top-3) | 129/150 = 86.0 |
| reader BASELINE | 87.2 / 92.9 | 86.8 / 86.8 | 79.2 / 83.3 | 89.7 / 100 | 88.9 / 100 | 92.9 / 92.9 | 88.9 / 100 | (same rule) | |
| reader FINAL | 86.5 / 92.9 | 86.8 / 86.8 | 79.2 / 87.5 | 89.7 / 100 | 85.2 / 96.3 | 92.9 / 92.9 | 88.9 / 100 | 8 / 9 | 130/150 = 86.7 |

Gap rows: 8 of 9 now land on the new honest article at top-1; the number-font gap ranks `recipes.number_fonts` 2nd behind `recipes.camo`. Non-gap top-1 lost ONE symptom question (-0.7) and top-3 gained one spec question; not investigated, because that would mean reading the sealed set. Old sets after everything (shared): DEV 90.6 / 98.4 (base 90.6), HELD 86.4 / 96.1 (base 86.1), held2 77.2 / 97.1 (69.1), held3 77.0 / 88.5 (73.6), casual TUNE 75.8 / 87.9 (75.8), casual TEST 67.2 / 83.4 (66.8). Reader DEV 90.2 (90.1), HELD 85.4 (85.1). No old number dropped.

### Gates (`_easy_claude_work/search_lab/gates_r4.txt`): all green
helper_eval 297/297 (with the shared ranker preloaded) · builder_test 136/136 · ft2 35/35 · edit_corpus 509/0 mismatches · stack_test 108/108 · convo dev 18/18, held 15/15 · enc_test 27/27 · enc_v2 --final all PASS (6,173 articles) · --depth lanes A 66/66, B 63/63, C 198/198 · enc_reader_smoke 128/128 · PARITY 1689/1689 = 100% · rewrite-step parity JS vs Python 2043/2043.

### Files (synced to `electron-app/server/` by copy, only these three: `js/spb-enc-search.js`, `server_routes/encyclopedia_routes.py`, `js/spb-encyclopedia-data.js`; `?v=` of both JS bumped to `20261005sl4` in both `paint-booth-v2.html` copies)
Data: `data/encyclopedia/{recipes,cars,workflows,tools,support}.json`. Lab: `_easy_claude_work/search_lab/r4*.js|py|txt`, `r4_sealed/` (ids only), `results/r4_*`. The live/test servers need a restart (not done by me) to load the Python `sx_rewrite`; the app pages pick up the JS on reload.

### R4b (orchestrator follow-up: stripes / numbers stand out / number fonts) - ranker VERSION 2026-10-05.8

casual150 was NOT re-scored (spent). Tuning used the old sets plus 20 new paraphrases I wrote myself, logged in `_easy_claude_work/search_lab/r4b_para.jsonl` (7 stripes, 7 numbers-stand-out, 6 number-font; gold = the stripes how-to/recipe, the two legibility cards, `recipes.number_fonts`). HELD was looked at while picking qlock (logged in `held_peeks.log`).

Causes found (`r4b_ch.js` shows main / +fusion / +bank stages):
- **number fonts:** the main channel ranks `recipes.number_fonts` first by a wide margin (score ratio > 3x), but the paraphrase bank moved `help_topics_1.numbers` over it. Articles written after the bank have no bank questions, so the bank systematically overturns them.
- **numbers stand out:** "stand out" / "pop" phrase-match the generic pack / pop cards; the number-legibility cards only share the word "number".
- **make stripes:** the stripes recipe's aliases say "add stripes"; "make" did not reach them, and "Give the numbers, sponsors or stripes their own finish" won on the bare word.

Mechanisms (no weight retune, no aliases):
1. **`P.qlock = 1.5`, the bank is a tie-breaker.** The bank cannot move a main-channel winner whose score is >= 1.5x the runner-up (and that is still first after fusion). Plateau: 1.3-1.75 gave the same or better on every set; 1.15 and 2-3 were worse on casual TUNE or DEV. Mirrored in Python (`_sx_qbblend(..., lock)`).
2. **REWRITE `R4B-LEGIBILITY`** (phrasing class): numbers / sponsors / logos / lettering + a visibility goal ("stand out", "pop", "readable", "more visible", "easier to see", "hard to read", "blends in", "gets lost"), or "read / stand out ... numbers" -> appends "readable number contrast". Guards: not when a finish is named ("hard to read on chrome" is the decal-rescue case: the first draft cost 1 HELD item there, fixed by the guard), and not "not visible / missing" (vanished numbers).
3. **REWRITE `R4B-ADDELEM`** (verb -> tool intent): make / create / draw / do / paint / put / want + a drawn design element (stripes, pinstripes, flames, checkers, chevrons, stars) -> "add <element>". Numbers / logos / sponsors were taken OUT of the list after the per-row diff showed "make my numbers chrome" / "paint my numbers red" (editing existing art) dropping.
- Tried and rejected: a subject-in-the-id boost (`sl` 0.1-0.3): +1.5 held2 but HELD -0.6 to -0.8, h3 -1.1 to -3.4.

| set (top-1 / top-3) | before R4b | after R4b |
|---|---|---|
| paraphrases (shared) | 55.0 / 85.0 (stripes 5/7, numbers 1/7, fonts 5/6) | 100 / 100 (7/7, 7/7, 6/6) |
| paraphrases (reader) | - | 95.0 / 100 |
| DEV shared / reader | 90.6 / 98.4 · 90.2 / 98.0 | 91.5 / 98.4 · 91.2 / 98.0 |
| HELD shared / reader | 86.4 / 96.1 · 85.4 / 96.1 | 86.9 / 96.1 · 85.9 / 96.1 |
| held2 shared / reader | 77.9 / 97.1 · 77.2 / 97.1 | 78.7 / 97.1 · 77.9 / 97.1 |
| held3 shared / reader | 77.0 / 88.5 · 75.9 / 88.5 | 77.0 / 88.5 · 75.9 / 88.5 |
| casual TUNE shared / reader | 75.8 / 87.9 · 77.2 / 87.6 | 75.8 / 87.9 · 77.2 / 87.6 |
| casual TEST shared / reader | 67.2 / 83.4 · 65.3 / 80.7 | 68.0 / 83.4 · 66.0 / 80.7 |

No set dropped. With qlock alone casual TUNE was 76.2; ADDELEM moves one TUNE item ("hw do i do raccing stripes") from `recipes.retro_stripes` to its twin `ideas.racing_stripes` (both stripes how-tos; still top-3).

Gates (`gates_r4b.txt` + two scripts): helper_eval 297/297 · builder 136/136 · ft2 35/35 · edit_corpus 0 mismatches · stack 108/108 · convo 18/18 + held 15/15 · enc_test 27/27 · enc_v2 --final all PASS (6,173) · --depth A 66/66 B 63/63 C 198/198 · enc_reader_smoke 128/128 · PARITY 1689/1689 · rewrite parity 2043/2043 + 23/23 new phrasings · search parity on the 20 paraphrases 20/20 · `enc_stale_refs_check.py` PASS · `hidden_feature_check.py` PASS. No data change, so no rebuild. Synced `js/spb-enc-search.js` + `server_routes/encyclopedia_routes.py` to `electron-app/server/` (copy); token `spb-enc-search.js?v=20261005sl5` in both `paint-booth-v2.html`. No server restart, no in-app check (blind run on 59879). Lab files: `r4b_para.jsonl`, `r4b_probe.js`, `r4b_ch.js`, `r4b_dbg.js`, `r4b_edit.py`, `r4b_row.py/.txt`, backups `r4b_backup_*`.
