# V4-B — the offline learned reader (kNN / BM25) — handoff (2026-10-07)

Lane V4-B of the HELPER V4 big swing. Owner: Claude (Opus 5.5) worker. **No commits made. The hooks below are NOT applied:** worker S6b owns `js/spb-offline-answer.js` and the html.

## What it is
`js/spb-intent-knn.js` (ES5 UMD, `window.SpbIntentKnn`, VERSION `2026-10-07-v4b`) is a retrieval reader over a labelled corpus. The corpus is shipped as `js/spb-intent-knn-data.js` (`window.SPB_KNN_DATA`, generated, 2.1 MB).
- **Corpus (34,703 rows):**
  - V4-A `eval/corpus/corpus.jsonl`: 21,823 rows (seed 1,798 / para 2,562 / gen 17,463).
  - V4-A2 `eval/corpus/convo/flat_all.jsonl`: 12,880 multi-turn turns (convo 11,755 / qa_convo 1,125).
  - Each row stores: the placeholder text; the **previous buyer turn's placeholder text** (the secondary key); want, shape and FAQ `gold_ids`; and, for 988 regex-proven seed turns, the wording plus slot offsets.
- **Normaliser:** quote/hex/repeated-letter fixes, a slang map, Damerau typo repair against the domain vocabulary, and owner part aliases (rocker/skirt/quarter = sides, cab = roof + sides). Slot placeholders are PART / COL / FIN / PAT / NUMS / SPON / REL / OBJ / N / LAYER.
- **Retrieval:**
  - BM25 over words (stopwords 0.3), bigrams, and prev-turn words (`p:`, 0.35; `p:^first`, 0.5). The index uses integer term ids, typed arrays and precomputed weights.
  - The `x:` context features (convo / fresh / length) and the char 3-5-gram Dice score (λ 0.6) only re-rank the top 250 word candidates. With char grams in the index, load took 5.7 s. As a rerank, accuracy is equal or better (class accuracy train 80.8% vs 80.5%).
- **Reading:** votes on want (change / answer / decline / ask / nothing / undo / redo) and on shape, with confidence = margin × √sim. It also votes on **gold article ids** from the neighbours' answers (FAQ gold@3).
- **Hybrid (`hybrid(text, env, r, routeRx)`):** the regex reader runs first. kNN only acts on a *weak* result: ASK / PREFILL, DO with no steps, whole-body fallback without a whole-car cue, or ANSWER. Paths, in order:
  1. `ack` for filler / acknowledgements.
  2. `answer`: the encyclopedia search re-ranked by the kNN gold vote.
  3. `gold`: swap the article of a regex ANSWER when the neighbours clearly point elsewhere (share ≥ 0.35).
  4. `spell`: the buyer's sentence with only typos / slang fixed, re-read.
  5. `follow`: a bare follow-up written out in full from the previous turn ("and the spoiler" after "chrome roof" → "chrome spoiler").
  6. `rewrite`: a neighbour's proven wording with this turn's slots, or a canonical sentence. Requires sim ≥ 0.4.
- **Every rewrite is re-read by the same regex reader and then `verify()`d.** It cannot:
  - invent parts, body, numbers / sponsors / layers, or colours;
  - touch a protected part or element;
  - turn "everything (but X)" into a parts-only edit.
- **Guards:**
  - Questions, advice, negation, exception, placement ("behind", "upper", "stripe") and sampling turns are never re-worded into edits.
  - A turn the regex reader *answered* is never turned into an edit. Measured: that was right only 2 times in 8.
  - Two-colour requests, object + part, and layer + part combinations are not guessed.
- **Kill switch:** `window.SPB_KNN = '0'` or `localStorage.SPB_KNN = '0'`. Thresholds: `TH` (overridable through `window.SPB_KNN_CFG.th`).

## Numbers (offline grader `bank/grade_offline.js`, unmodified, items all-turns-correct; h = items with a harm flag)
Train, p1 and p2s are 5-fold by original id: the item's own original and its paraphrases are never in the index. p2 = originals allowed. dev and blind6 are totals only.

| set | (c) offline baseline (b2) | (b) HYBRID final (h19, sim floor 0.4) | (b') hybrid without the sim floor (h17) | (a) kNN alone, frame → SpbIntentPlan (FAQ gold@3) |
|---|---|---|---|---|
| train | 383/615 62.3% h15 | 391/615 63.6% h16 | 397/615 64.6% h16 | 259/615 42.1% h53 (gold@3 170/227) |
| p1 | 312/615 50.7% h20 | 323/615 52.5% h19 | 330/615 53.7% h19 | 229/615 37.2% h61 (158/227) |
| p2s (strict) | 290/615 47.2% h54 | 301/615 48.9% h55 | 301/615 48.9% h54 | — |
| p2 | 290/615 47.2% h54 | 305/615 49.6% h55 | 308/615 50.1% h54 | 291/615 47.3% h54 (207/235)* |
| dev (3 uses) | 81/186 43.5% h6 | **83/186 44.6% h6** | 85/186 45.7% h7 | not run (budget) |
| blind6 (2 uses) | 73/150 48.7% h7 | not run (budget spent) | 77/150 51.3% h10 | not run |

\* p2 kNN-alone allows the original in the index, so treat it as optimistic.

- **Turn-level class accuracy of kNN alone** (want, LOO strict): train 80.6%, p1 78.1%, p2 80.2%. Among the 50% most confident turns: 92 / 86 / 89%.
- **Corpus slices** (in-corpus leave-out; drops the row, its conversation, its bank original, and every identical placeholder text; n = 400 each; `knn/slice.js`):

| slice | want | FAQ gold@3 |
|---|---|---|
| seed | 80.0% | 60.3% (n=78) |
| para | 98.0% | 87.5% (n=24) |
| gen | 87.5% | 70.9% (n=165) |
| convo | 92.8% | 95.5% (n=22) |
| qa_convo | 93.0% | 82.7% (n=156) |

  Para is optimistic: its source sentence can stay in.
- **Harm:**
  - **train / p1 / p2 combined: 90 vs 89.** The +1 on train is A-0491: a correct kNN t0 ("triple carbon") followed by a regex mis-read on t2.
  - **dev: harm equal (6 vs 6).**
  - **blind6 was measured only before the sim floor: harm 10 vs 7. Not re-measurable in this lane (budget).** The orchestrator should re-check blind6 with the final code before shipping.
- **Target not met:** ≥75% on p2 / dev was not reached. The gain is +2 to +4 points on every set.

## Speed / size (node, `knn/speed.js`)
- **Data:** 2,138 KB (columnar v3, interned strings). Parse: 42 ms.
- **Load:** synchronous index build 363 ms (budget 300). The app path is `warm()`: it builds in idle 25 ms slices 2.5 s after load, with the **longest block 37 ms** and 385 ms wall. `ready()` finishes synchronously only if a query arrives first.
- **Query:** `read()` 7.8 ms/q average (worst 17.5). `neighbours()` 6.2 ms.
- **Unit test:** `node _easy_claude_work/eval/knn/test_knn.js` → `KNN TEST 20/20 PASS`. Covers exports, the size and data contract, clear wants, gold top-3, aliases, follow-up merge and refusals, kept-strong result, weak re-read, the advice-question block, the kill switch, and speed.

## Where it stalls (honest)
1. **Executor bottleneck.**
   - The hybrid acts only through text that the regex reader can re-read.
   - Train still has 124 "regex asks" turns where kNN knows the turn is an edit but no proven wording or canonical sentence exists. These include copy / match ("right side should match the left"), corrections ("no the roof not the hood"), objects without a part (mirrors, truck bed, wing endplates), two-colour assignments, and layer blend / stroke ops.
   - kNN-alone frames through SpbIntentPlan reach only 30% on bank A, because `toFrame` is too coarse.
2. **Multi-turn cascades.** Follow-ups ("orange", "more", "and the doors") usually refer to a previous turn that also failed (for example "make the car look like a lamborghini"). Carrying `prev` helps the vote (with prev features, class accuracy on convo is 92.8%), but an execution needs the previous target.
3. **Item scoring.** About 80% per-turn class accuracy compounds to about 50% of items once all turns, cover and scope must pass.
4. **Corpus.**
   - 80% of the corpus is templated. On the gen slice FAQ gold@3 is 71% vs 83-95% on the convo slices.
   - Slots are missing for regions (upper / lower / half / line), objects and layer ops.
5. **Label / grader noise.** For example, R-type "TOO SHINY → ask" items are flagged as harm for a reasonable satin step.

**Next lever (not done here):** a confidence-gated *frame* path. Use the kNN shape and slots → SpbIntentPlan for the shapes where `toFrame` is reliable (recolour / refinish of named parts, undo, relative follow-ups with `env.last`), plus kNN neighbours as few-shot examples for the online model (V4-C).

## Files
- **New:**
  - `js/spb-intent-knn.js`
  - `js/spb-intent-knn-data.js` (generated: `node _easy_claude_work/eval/knn/build_index.js`; `--src seed,para,gen,convo`, `--convo none`, `--exclude-origs f`, `--out f`)
- **Harnesses in `_easy_claude_work/eval/knn/`:**
  - `score.js` (`--mode cls|a|hyb|base --set train|p1|p2|p2s|dev|b6 --tag x [--cfg '{"th":{..},"debug":1}']`; refuses sealed)
  - `slice.js`, `speed.js`, `test_knn.js`, `dbg_join.py`, `diag.js`
  - `PROGRESS.md`; runs in `_runs/`
- **Two-copy rule:** copy both js files into `electron-app/server/js/` as well. They are not in `scripts/sync-runtime-copies.js` yet.

## Hook hunks for S6b (exact; NOT applied)
**1. `js/spb-offline-answer.js`: route().** Replace the header line

```
    function route(text, env) {          // V3 S6b 2026-10-07 G9: Pantone names -> hex, then the normal reader
```
with
```
    function route(text, env) {          // HELPER V4 V4-B 2026-10-07: the regex reader first; the kNN reader (js/spb-intent-knn.js) re-reads a weak result (ask / nothing / whole-body fallback / decline)
        var r = routeRx(text, env);
        try { var KN = W.SpbIntentKnn; if (KN && KN.on()) r = KN.hybrid(text, env, r, routeRx) || r; } catch (eKN) {}
        return r;
    }
    function routeRx(text, env) {          // V3 S6b 2026-10-07 G9: Pantone names -> hex, then the normal reader
```
- The existing body stays unchanged as `routeRx`. **Do not name it `route0`:** that name is already taken (`function route0`, about line 2013), and the clash cost 70 train items in testing.
- This is exactly the hunk `score.js` applies (`HOOK_FROM` / `HOOK_TO`) to produce every number above.

**2. `claim()`: no change needed.** It calls `route(text, env)` (about line 2422), so it gets the hybrid. The hybrid keeps its own previous-turn ring and reads each turn once even when claim and route both read it.

**3. `paint-booth-v2.html` (BOTH copies).** Insert right after the `spb-intent-plan.js` tag (line 4697), before `spb-offline-answer.js`:
```
    <script src="js/spb-intent-knn-data.js?v=20261007-v4b1"></script><!-- HELPER V4 V4-B 2026-10-07: kNN reader corpus (generated by _easy_claude_work/eval/knn/build_index.js) -->
    <script src="js/spb-intent-knn.js?v=20261007-v4b1"></script><!-- HELPER V4 V4-B 2026-10-07: offline learned reader, window.SpbIntentKnn (hooked from spb-offline-answer.js route(); kill switch localStorage SPB_KNN='0') -->
```
Bump `spb-offline-answer.js`'s own `?v=` token when hunk 1 lands.
