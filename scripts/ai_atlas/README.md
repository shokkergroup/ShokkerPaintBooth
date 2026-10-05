# AI Atlas — the copilot's measured knowledge of every finish

`js/spb-ai-atlas-data.js` (`window.SPB_ATLAS_DATA`) is what lets the Pro copilot *understand* the ~4,800-look catalogue instead of keyword-matching names.
It is GENERATED; never hand-edit it.

```
python scripts/ai_atlas/dump_catalog.py --cdp 9444     # 1. dump the running app's catalogue + shelves (app must be running)
python scripts/ai_atlas/build_atlas.py --workers 8     # 2. render every finish offline (engine) and measure it   (~20 min the first time, resumable)
python scripts/ai_atlas/build_atlas.py --workers 1     #    re-assemble only (uses the cached renders in _easy_claude_work/atlas/atlas_raw.jsonl)
```

Per finish it records: palette (3 hex) + colour name, **brings its own colours vs takes the zone colour** (rendered on two different input paints),
lightness / saturation / contrast / hue spread, texture fineness (catalogue quantiles), metal / roughness / clearcoat mean+std of the spec map,
sparkle (top ~22%), shine class, shelf memberships (the buyer's 59 shelves), curated + derived tags, M7 quality, protected/gold flag.
Hand-written one-liners per shelf live in `shelf_notes.json` (the prompt's catalogue map). Runtime retrieval: `js/spb-ai-atlas.js`
(`SpbAIAtlas.find/details/browse/compare`): concept + synonym + colour + shine + metal + sparkle + texture + shelf facets, quality prior, diversity.

Bump `SPB_ATLAS_V` (default in `js/spb-ai-atlas.js`) and the `?v=` token in `paint-booth-v2.html` after regenerating.
The static route only serves js/css/png/svg/ico, which is why the data is a `.js` file injected lazily on first AI use.
After adding finishes to the catalogue, re-run the three steps above so the copilot knows them.

## Finish CARDS + ratings (2026-10-03): the knowledge lives in the DATA
`js/spb-ai-cards-data.js` (`window.SPB_CARDS_DATA`, GENERATED, ~2.4 MB, lazy-loaded by `js/spb-ai-cards.js`) holds one LLM-written card per catalogue item (4,799): a plain-words look, real-world analogs, 10-16 words a painter might type,
mood / era / car class / best placement, loudness 1-5, busyness 1-5, what it pairs with / what to avoid, and RATINGS 1-5 (appeal, body, accent, hero, risk). Every brain gets it: the built-in advisor (offline, free), Claude / OpenAI over MCP
(`spb_suggest_finishes`, semantic `spb_find_finishes`, `spb_finish_details` with the card) and the OpenRouter / DeepSeek copilot. Cost to (re)generate everything: about $2 (DeepSeek v4.1 flash through the app's own /api/ai/chat; the key never leaves the server).
```
node scripts/ai_atlas/dump_items_for_cards.js                      # 1. atlas data -> _atlas_cards/items.json
python scripts/ai_atlas/annotate_cards.py [--pilot 300]            # 2. cards  (needs a test server on :59879, SPB_CARDS_SERVER overrides; resumable; contact sheets of the baked thumbnails + the measured numbers)
python scripts/ai_atlas/rate_cards.py                              # 3. ratings (appeal / body / accent / hero / risk), resumable
python scripts/ai_atlas/build_cards_js.py                          # 4. -> js/spb-ai-cards-data.js ; bump window.SPB_CARDS_V default in js/spb-ai-cards.js and the ?v= tokens
```
New items: re-run 1-4 (only the new keys are annotated). MEASURE every change (picture-judged, relative, ~$0.05 a run): `python scripts/ai_atlas/gold_asks.py` (356 painter-voice asks, already generated) then
`node scripts/ai_atlas/gold_run.js lexical rank pipe_old pipe_new` and `python scripts/ai_atlas/gold_judge.py lexical rank pipe_old pipe_new`; context-rich scenarios: `node scripts/ai_atlas/scenario_run.js curated|ranked` + `gold_judge.py adv_curated adv_ranked`.
Headless (no browser, no cost): `node _easy_claude_work/adv_test.js <prompts>`, `more_test.js "ask" "show me more"`, `adv_fp.js` (design / support prompts must NOT be claimed).

## Overnight additions (2026-10-03): QA, truth set, intent model, vocabulary, like-benchmark
| script | what it does |
|---|---|
| `qa_cards.py` | No-LLM QA of every card against the measured numbers (shine / metal vs the look, colour words on takes-colour items, loud / busy outliers, thin cards, twins). Writes `_atlas_cards/qa_flags.json`. Flagged cards can be re-written with `annotate_cards.py` (reads `_atlas_cards/qa_hints.json`, one QA note per key). |
| `merge_l1_audit.py <audit.jsonl>` | Merges an independent card audit (Codex L1: verdict fix / bad + issues) into `qa_hints.json`, drops those cards from `cards.jsonl` (backup kept) so `annotate_cards.py` re-writes them with the reviewer's findings. |
| `truth_score.py [system ...]` | Scores `pipe_new` / `rank` / `pipe_old` / `lexical` against the HAND-LABELLED truth set (`_codex_work/finish_intel/l2_truth_asks/truth_asks.json`, 400 asks with good / bad key lists): HIT, CLEAN, BAD, GOOD@6 per category. No AI judge. |
| `train_intent.py --eval / --export [--fold N --out file]` | Trains the offline INTENT MODEL (logistic regression on word 1-2 grams; corpus = Codex L3 1,500 labelled messages + 400 truth asks + the maintainers' negatives). `--eval` = honest 2-fold accuracy; `--export` writes `js/spb-intent-data.js`; `--fold` exports a model that never saw the rows i%2==N (for end-to-end checks: `FOLD=0 node _easy_claude_work/corpus_eval.js`). |
| `build_colour_ext.py` | Builds `js/spb-colours-ext.js` (371 extra colour names, Codex L4 proposals: CSS keywords + racing colours) read by the advisor's colour parser. |
| `vocab_ab.js build / decide` + `gold_judge.py vocabA vocabB` | A/B every proposed painter-vocabulary entry on its own example ask with the picture judge; only entries that improved the judged result ship (`js/spb-lexicon-ext.js`: 72 of 442 changed proposals). |
| `like_run.js [name] [N]` + `like_judge.py name` | Benchmark for "like X but calmer / darker / glossier ..." (`SpbProRank.like`): builds N deterministic cases and has the picture judge score the five results against the reference. Knobs: `CFG='{"likeMod":1.6}'`, `MODW`. Baseline 0.65/2 (strict). |
| `build_lsa.py [--k 96]` (runs `lsa_dump_tf.js` itself; `build_cards_js.py` chains it) | Builds the offline LATENT-SEMANTIC index `js/spb-lsa-data.js` (1.4 MB: 96-d int8 term + card vectors learned from the 4,800 cards themselves; lava ~ molten ~ magma). `js/spb-ai-cards.js` fuses its cosine with BM25 (`SpbAICards._lsa.w`, default 0.5; loads lazily after the cards; no file = plain BM25). Truth hit 54.3% -> 56.8% (pipeline) / 49.5% -> 52.8% (tool), picture-judged gold 0.82 -> 0.87. **Rebuilt automatically at the end of `build_cards_js.py`** (a stale file still works; unknown keys just get no latent score). |
| `gold_run.js` with `ASKS=<file> ASKTAG=<tag>` | Runs any ask list through the systems (used by `truth_score.py`). |
Headless regressions (no cost): `_easy_claude_work/convo_test.js` (scripted multi-turn conversations), `tool_test.js` (suggest_finishes), `corpus_eval.js` (intent routing on the L3 corpus), `claim_stats.js` (truth asks), `fuzz_advisor.js` (2,000 generated asks: exceptions / junk text / slow turns), `adv_fp.js` (which prompts the advisor claims).
