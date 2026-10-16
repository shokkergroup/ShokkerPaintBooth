# V4-F: FRAME-FIRST OFFLINE reader (2026-10-07)

**What it is:** `js/spb-intent-offline-frame.js` (UMD, ES5, `window.SpbIntentOfflineFrame`, VERSION `2026-10-07-v4f3`). It makes the offline helper produce an IntentFrame directly, the same way the online model does, so both helpers share one path: frame -> SpbIntentPlan -> apply -> report.

`frameOf(text, prevTurns, env)` returns `{frame, want, confidence, source, shape, said, fixes}`:

- **Spelling pass first:** the text goes through the S7c shared fixer `SpbIntentModel.clean()`; the said text is kept on the result.
- **Skeleton (the kind of request):** the kNN reader (`SpbIntentKnn.read`).
- **Slots (part, colour, finish and so on):** the kNN typed normaliser, plus this file's typo pass, part aliases, colour-target / keep / except / negation / relative marking, grouping, themes, and two-colour schemes.
- **References:** `env.last` (SpbConvo editCtx) or `env.planLast` (the planner's `live().last`); the planner resolves `ref`.
- **Validation:** `SpbIntentFrame.validate`. An invalid frame is never returned.

`decide(text, prevTurns, env, r, regexFrame, opt)` is the one call the route() hook makes. It implements the **mix** policy:

- A strong regex result is kept.
- Otherwise the frame wins.
- A frame that would only ask, or do nothing, never overrides a regex result that acts on a named target.

The kill switch is `SPB_OFFLINE_FRAME='0'` (window or localStorage).

Files:

- **Module:** `js/spb-intent-offline-frame.js`
- **Unit test:** `_easy_claude_work/eval/v4f/test_offline_frame.js`. Result: `OK 18/18`, max 45 ms; the first call takes about 0.5 s while it builds the kNN index.
- **Harness:** `_easy_claude_work/eval/v4f/eval.js` (`--set train|p1|p2|dev --pols regex,ff,mix,online`), plus `dbg.js`, `cmp.js` and `tally.js`.
- **Experiment log:** `_easy_claude_work/eval/v4f/PROGRESS.md` (v0 to v20).

## Numbers (final run, one consistent snapshot, 2026-10-07 ~05:05)

All policies use the same planner (`SpbIntentPlan`) and the same grader (`grade_offline` checks plus the model_frames turn grader). ALL = turns that pass. h = harmful turns.

- **regex:** today's offline reader; its result goes through `routeToFrame`.
- **ff:** frame-first, falling back to regex when frameOf has nothing.
- **mix:** `decide()`.
- **online:** stored DeepSeek frames replayed through the same planner and grader. This is a reference, not part of this lane.
- **train:** leave-one-out (the item's own corpus neighbours are excluded from the kNN).

| set | regex | ff | **mix** | online ref |
|---|---|---|---|---|
| train (615 turns) | 367 (59.7%) h12 | 397 (64.6%) h8 | **412 (67.0%) h16** | 454 (73.8%) h11 (earlier snapshot) |
| p1 (615) | 298 (48.5%) h17 | 334 (54.3%) h8 | **351 (57.1%) h19** | 409 (66.5%) h19 |
| p2 held-out (615) | 281 (45.7%) h45 | 297 (48.3%) h35 | **312 (50.7%) h51** | 400 (65.0%) h31 |
| dev (186, totals only) | 77 (41.4%) h3 | 77 (41.4%) h11 | **88 (47.3%) h11** | 110 (59.1%) h6 |

Per kind (passing turns, with harm counts):

| set / policy | edit /178 | convo /189 | qa_convo /17 | vague /35 | question /48 | trouble /48 |
|---|---|---|---|---|---|---|
| train regex | 87 h1 | 74 h6 | 5 h2 | 15 h3 | 46 | 44 |
| train ff | 117 h3 | 74 h2 | 5 h1 | 15 h2 | 46 | 43 |
| train mix | 121 h3 | 86 h7 | 5 h2 | 14 h4 | 46 | 43 |
| p1 regex | 79 h4 | 49 h8 | 2 h3 | 10 h2 | 42 | 38 |
| p1 ff | 103 h5 | 59 h1 | 2 h2 | 13 | 42 | 36 |
| p1 mix | 109 h6 | 70 h8 | 2 h3 | 12 h2 | 42 | 37 |
| p2 regex | 79 h9 | 49 h18 | 1 h2 | 13 h8 | 40 h1 | 29 h5 |
| p2 ff | 88 h9 | 51 h17 | 1 h2 | 16 h1 | 41 | 29 h4 |
| p2 mix | 95 h12 | 61 h26 | 1 h2 | 14 h5 | 41 | 29 h4 |

Bank A (edits and conversations, /367): mix scores train 207, p1 179, p2 156, dev 48/110. For comparison, regex scores 161 / 128 / 128 / 36.

**Speed:** frameOf averages 12-15 ms per turn. p95 is 21-26 ms and the maximum is 59-79 ms, measured while 3 other agents were loading this machine; in a quiet earlier run the average was 11 ms and p95 18 ms. The first call takes about 0.5 s to build the kNN index. The average is within the 20 ms budget; p95 is at or just over it under load.

### Honest verdict

- **The 70% p2 milestone was not reached.** Mix scores 50.7% on p2, up 5 points on regex. Even the tuned online model scores 65.0% through the same planner and grader. Most of the remaining gap is outside the reader (see limits below).
- **Harm does not go down overall, so "harm must not rise" holds only for ff.**
  - ff lowers harm on train (12->8), p1 (17->8) and p2 (45->35).
  - ff raises harm on dev (3->11).
  - mix gains the most points, but its harm is about regex's level or higher: train 12->16, p1 17->19, p2 45->51, dev 3->11.
  - Most of mix's extra harm comes from the regex reader's own confident paint changes, which it keeps, when the label is ask or answer. Overriding them with the frame loses more correct turns than it saves (measured: on p1, 21 correct turns lost to save 7 harms).
  - Two attempts to cut mix harm were neutral or worse and were reverted: a "safe-mix" (v19) and an "answer veto" (v20).
- **Recommendation:**
  - Ship **ff** if harm is the gate.
  - Ship **mix** only behind the S2 verifier / S6b guards, which run after route() and catch some of these.
  - Both are options of `decide()`; ff = `OF.frameOf` + `TH.use`.
- **The S7c shared spell-fixer (`SpbIntentModel.clean`) is in frameOf.** It made no difference on the bank:
  - train ff -2 (one is a label quirk: "chrome" is expected to also set silver);
  - p1 and p2 unchanged.
  - The bank has few typos. On typed typos it clearly helps: "doirs rd" now finds red on the sides (before, it asked "what"), and "whitte" / "puple" confidence goes from 0.4-0.5 to 1.0.
  - Kept. Disable it with `SPB_OF_CLEAN='0'`.

### Limits (what the reader cannot fix)

1. **Planner refusals of correct frames (for V4-E):**
   - object targets (mirrors, bed, spray can) where the car has no part or layer for them, so the planner asks;
   - `adjust` + `ref` with an empty look ("and the hood same", "a bit more"): the planner asks "What should change on the last change";
   - the concept "animal print" / "snakeskin" is not resolved to a pattern id;
   - tape-layer zones render nothing (app quirk; V4-E has this open).
2. **Context the reader does not have:**
   - option picks ("the second one", "the first was better") need the helper's previous reply and options list. The kNN maps some of these to undo by mistake;
   - layer operations (blend, hue, spec on a named layer);
   - part swaps ("swap the hood and roof colours").
3. **Labels:** "too shiny / too glossy" complaints are labelled ask, not a gloss tweak. "chrome X" expects a silver colour. 47 truck items were relabelled ask by D (applied).
4. **p2 harm:** about 20 of mix's 51 harmful p2 turns are "want answer, got change" (a question that looks like an order).

### Process notes

- Iteration used train and p1 only. p2 and dev were scored as totals (dev used 2 of the 3 allowed runs).
- **Disclosure:** one early grep of the stored online calls (`calls.jsonl`) printed the text of one p2 turn (A-0005-p2). It was not used for any rule. After that, no p2 or dev text was printed.

## Hook for S6b: `js/spb-offline-answer.js` route()

Rename the current `function route(text, env)` header (the line `function route(text, env) {          // V3 S6b 2026-10-07 G9: Pantone names -> hex, then the normal reader`) to **`function routeSaid(text, env) {`**. Keep its body unchanged.

**Do not name it `route0`** (`function route0` already exists, at about line 2013). Also avoid `routeRx`, which the V4-B kNN hook proposes. If both land, chain them: `route` -> V4-F -> `routeSaid`. V4-F's measured "regex" baseline is the reader **without** the kNN hybrid, and V4-F already uses the kNN inside frameOf, so **land V4-F instead of the V4-B hybrid**. V4-B hybrid measured train 391 / p2 305; V4-F mix measured 412 / 312.

Then add, directly above `routeSaid`:

```js
    // HELPER V4 V4-F 2026-10-07: frame-first offline reader (js/spb-intent-offline-frame.js, decide() = the "mix" policy). Kill: SPB_OFFLINE_FRAME='0'
    function route(text, env) {
        var r = routeSaid(text, env);
        var r4f = null; try { r4f = offlineFrame4f(text, env || {}, r); } catch (e4f) { r4f = null; }
        return r4f || r;
    }
    function offlineFrame4f(text, env, r) {
        var OF = W.SpbIntentOfflineFrame, IFx = W.SpbIntentFrame, IP = W.SpbIntentPlan; if (!OF || !OF.on() || !IFx || !IP) return null;
        var e2 = {}, k; for (k in env) if (Object.prototype.hasOwnProperty.call(env, k)) e2[k] = env[k];
        try { var lv = IP.live && IP.live(); if (lv && lv.last) e2.planLast = lv.last; } catch (eL) {}
        var rxF = null; try { rxF = (r && r.s5frame) || IFx.routeToFrame(r, text, env); } catch (eF) { rxF = null; }
        var d = OF.decide(text, env.prevTurns || [], e2, r, rxF, {}); if (!d || !d.frame) return null;
        var F = d.frame, out = null;
        if (F.act === 'change') {
            try { var SMx = W.SpbIntentModel, ATx = W.SpbAIAtlas; if (SMx && SMx.resolveLooks) SMx.resolveLooks(F, function (o) { try { return (ATx && ATx.find(o)) || []; } catch (eA) { return []; } }); } catch (eR) {}
            out = gfx8Plan(F, text, env);
        } else if (F.act === 'undo') out = { cls: 'DO', pass: 'undo' };
        else if (F.act === 'answer' || F.act === 'list') {
            if (r && /^(ANSWER|ASK|LOCAL|OFFTOPIC|PREFILL|DECLINE|ONLINE)$/.test(r.cls || '')) return null;          // the regex reader already answered / asked: keep its reply
            var hs = search(String(text), 6) || []; if (hs.length) out = answered(hs, String(text));
        } else if (F.act === 'nothing') { out = local('ack', 'Nothing changed. Tell me the next change whenever you are ready, or ask me anything about the app.'); out.why = 'ack'; }
        else if (F.act === 'ask_back') out = asked('of-ask', F.question || 'What should change, and where?', []);
        if (out) out.v4f = { source: d.source, confidence: d.confidence };
        return out;
    }
```

- **`env.prevTurns`:** frameOf uses the previous user text only when there is no last change. S6b owns `spb-pro-ai.js`, which already builds `prevT` at about line 1145; pass it as `env.prevTurns = prevT` on the offline env. Without it, `[]` is used, at a small cost to convo turns.
- **What the hook mirrors:** the evaluated mix policy. A change goes through `resolveLooks` and then the planner (`gfx8Plan`), and an answer uses the encyclopedia search. The S6b guards that run inside routeSaid (ack20, Pantone, confirm24, simComplaint9, ...) produce the `r` that `decide()` sees, exactly as in the eval.
- **For an ff-only (lower-harm) variant:** replace the `OF.decide(...)` line with `var o = OF.frameOf(text, env.prevTurns || [], e2, {}); var d = o && o.frame ? { frame: o.frame, source: o.source, confidence: o.confidence } : null; if (!d) return null;`.

## HTML script tags (both `paint-booth-v2.html` and `electron-app/server/paint-booth-v2.html`)

Insert these after the `spb-intent-model.js` tag (line ~4698) and **before** `spb-offline-answer.js` (line ~4706). The kNN files are from V4-B and are not yet in the html:

```html
    <script src="js/spb-intent-knn-data.js?v=20261007-v4b1"></script><!-- HELPER V4 V4-B 2026-10-07: kNN corpus index (2.1 MB) -->
    <script src="js/spb-intent-knn.js?v=20261007-v4b1"></script><!-- HELPER V4 V4-B 2026-10-07: window.SpbIntentKnn (read / norm / weak) -->
    <script src="js/spb-intent-offline-frame.js?v=20261007-v4f3"></script><!-- HELPER V4 V4-F 2026-10-07: frame-first offline reader, window.SpbIntentOfflineFrame -->
```

Bump the `spb-offline-answer.js` token (e.g. append `-v4f3`) when the hook lands.

## Copies and sync manifest

The new js files exist **only at the root** `js/`. Copy them to `electron-app/server/js/`:

- `spb-intent-offline-frame.js`
- `spb-intent-knn.js`
- `spb-intent-knn-data.js`

Then add these lines to `scripts/runtime-sync-manifest.json` `files` (next to `js/spb-intent-model.js`, line ~448) and run `node scripts/sync-runtime-copies.js --write`:

```json
    "js/spb-intent-knn-data.js",
    "js/spb-intent-knn.js",
    "js/spb-intent-offline-frame.js",
```
