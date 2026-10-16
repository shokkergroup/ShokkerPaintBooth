# R1 — Answer routing (2026-10-07)

Lane R1 (opus worker), finished 2026-10-07; orchestrator verified. Patches `js/spb-offline-answer.js` only: 9 hunks in `_easy_claude_work/eval/r1/hunks.diff`, scripts in `patch.py` / `patches/`, round log in `PROGRESS.md`.

## Root cause
The misroutes (gold article in the search top 3, but the route did not answer with it) came almost entirely from `kind()` labelling questions as `other`. The `confident()` threshold was not a cause. The fixes are in `kind()` and the routes around it (p01–p08, p10, p11).

## Results (worker)
- Corpus, correct article shown (8,051 rows): 63.4% -> 80.3%.
- Corpus, answer id is gold: 51.0% -> 67.1%.
- B-kind: train 206 -> 209, p1 169 -> 193, p2 152 -> 160 (p2 target was 180).
- Dev: 81 -> 82 (harm 6 -> 6).
- Change rows: none flipped to an answer.
- helper_eval: 297/297.

## Orchestrator check (real grader, OA_FILE = patched copy, before -> after)
| Set | Before | After |
|---|---|---|
| blind6 | 75/150, harm 6 | 76, harm 5 |
| sealed | 82/199, harm 15 | 85, harm 15 |
| regression | 62/68 | 62/68 |
| helper_eval | 297/297 | 297/297 |

## Misroute classes (2,627 -> 1,550 rows)
| Class | Rows |
|---|---|
| Answered a sibling article (ranker order) | 1,159 -> 1,145 |
| Builder prefill | 473 -> 109 |
| Parsed as an edit | 306 -> 92 |
| APP_WORD_RE "did not catch that" | 168 -> 37 |
| Online free-design | 145 -> 36 |
| Online unknown | 138 -> 35 |
| Which-part / same / outline-part asks | 87/40/23 -> 32/1/1 |

## Tried and dropped
- New stop words: reshaped the index, train B 206 -> 197.
- Clause search on every long text: lost 9 train items. It is kept only for story clauses or a weak whole-text match.
- Answer instead of an open ask: flipped 44 change rows.
- Query fusion: no gain.
- car_pages load: no misroute class pointed at it.

## Next levers
- Ranker and article order for sibling confusion (34 of the 88 p2 failures).
- The kNN intent reader (`js/spb-intent-knn.js`) as a question-vs-edit vote inside `kind()`, for the 30 confident-article rows labelled `other`. A broad rule for those would hit 223 of 2,030 change rows.

## Apply
```bash
git apply _easy_claude_work/eval/r1/hunks.diff
node scripts/sync-runtime-copies.js --write
```
Then bump the `?v=` token of `spb-offline-answer.js` in both `paint-booth-v2.html`. Patched copy: `_easy_claude_work/eval/r1/oa_r1.js`.
