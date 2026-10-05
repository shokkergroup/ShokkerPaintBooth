# VERIFY_ONLINE_ASK (2026-10-04) - online model on "make the yellow purple" (8-zone seafoam design)

Lane: verification only (no repo code changed). Test server 59879, own Chrome CDP 9751 (`pw/chrome_up_9751.py`), live app 59876 untouched. Model `deepseek/deepseek-v4.1-flash` via the app, **offline-first OFF** (straight to the gear model, `localStorage spb_pro_ai_offline_first=0`).

## Why
`VISIBLE_COLOUR.md` "Not verified": in 1 of 2 online samples DeepSeek read `colours_you_see` and recoloured the mint green itself (refinish target "mint green") instead of asking; rule 16d + the `colours_you_see` note were tightened afterwards (`vis_p7.py`) but never re-sampled.

## Method
`_easy_claude_work/pw/ft_inapp.py <tag> z8 --online --sentence "make the yellow purple" --cap 0.02`, one FRESH process per run (page boot -> owner PSD `C:/1Shokker Paint Car Examples/SPB ARCA Chevy PSD.psd` -> the 8 zones of the rebuilt `output/job_render_1791086800_23371_a498bdd430c6/zones_payload.json` restored -> chat studio -> send). A fresh boot is the "reset zones between runs": every run starts from the identical 8 zones (`zones_before` compared field-by-field to `zones_after`). Summary: `pw/vo_summary.py vo_b1 ... vo_b5`. Raw: `_easy_claude_work/eval/firsttest/vo_b1..vo_b5/s1_1.json` (+ `_before/_after/_chat.png`), logs `_easy_claude_work/eval/verify_online/b1..b5.log`.

Pass = the model answers that no yellow is visible / asks, AND the zone list is unchanged.

## Result: 5 / 5 PASS (before any change; no fix needed)

| run | reply head (model) | tool calls (`__spbAITranscript`) | zones changed | model calls | cost |
|---|---|---|---|---|---|
| 1 | Nothing changed yet — no yellow actually shows on the car: it's hidden under the mint green zone, so the yellow you see in the file is only the original paint underneath. | describe_paint {}; refinish {"target": "yellow", "colour": "purple"} | no (8 -> 8) | 3 | $0.0027 |
| 2 | Nothing changed yet: no yellow actually shows on the car — it's the original paint sitting under your mint-green zone, so the yellow you see there is mint green. | describe_paint {}; refinish {"target":"yellow","colour":"purple"} | no (8 -> 8) | 3 | $0.0055 |
| 3 | Nothing changed yet: no yellow actually shows on your car — the mint green zone covers almost all of it, and only a little yellow survives in the logos. | describe_paint {}; refinish {"target":"yellow","colour":"purple"} | no (8 -> 8) | 3 | $0.0019 |
| 4 | Nothing changed yet: no yellow actually shows on the car — the yellow is hidden under the mint green "Seafoam Chalk" zone, so the car reads mint, not yellow. | describe_paint {}; refinish {"target":"yellow","colour":"purple"} | no (8 -> 8) | 3 | $0.0019 |
| 5 | Nothing changed yet: no yellow actually shows on the car — the yellow is hidden under your mint-green seafoam zone, so the car looks mint there. | describe_paint {}; refinish {"target": "yellow", "colour": "purple"} | no (8 -> 8) | 3 | $0.0005 |

Every run: `describe_paint` -> `refinish {target: "yellow", colour: "purple"}` -> the app answered `status: "not_visible"` (nothing queued) -> the model relayed it in one sentence and asked "make that hidden yellow purple, or turn the mint green purple?". The app appended its own card ("I do not see any yellow on the body of the car now: your zone Seafoam Chalk paints over it ...") with the 3 chips (Change the hidden yellow under "Seafoam Chalk" / Make the mint green purple / Make all the yellow purple, including the logos). The card + 3 chips were verified in the chat entry of ALL 5 runs; preview metrics identical before/after in all 5 (purple 23.38% -> 23.38%, yellow 2.38% -> 2.38%).

The model never targeted the mint green and never called add_zone / edit_zone in any run: the rule text (16d "Never swap in another colour yourself ... call refinish with the buyer's own colour word") is now followed, and the server-side enforcement (`refinish` handler -> `compileRequest` -> `hiddenAsk` -> `status: "not_visible"`) is what actually stops the recolour for the yellow target.

## Spend
DeepSeek: 5 runs = $0.0125 (15 model calls) + the `undo_inapp.py` online part $0.0052 = about $0.018 of the $0.06 cap.

## Regression gates (run after the 5 samples; no code changed so no ship ritual / bump / sync needed)
- `node _easy_claude_work/edit_corpus.js`: 509 phrases, 0 mismatches
- `node _easy_claude_work/tool_test.js`: 15/15
- `node _easy_claude_work/convo_test.js`: 52/52
- `python _easy_claude_work/pw/undo_inapp.py`: 8/8 PASS (offline 2, kit 2, complaint 2, online 2), page errors []
- `node --check` ai.js + edit.js OK; `scan_ctrl.py` 0 control chars; `sync-runtime-copies.js --manifest sync_mine.json --check`: no drift.

## Residual risk (not changed, by design)
- 5 samples at 5/5 vs 1/2 before the rule tightening: the prompt change very likely fixed the sampling, but it is still prompt text for the "swap in another colour" path. If the model ever calls `refinish {target: "mint green", colour: "purple"}` for a buyer who said "yellow", the handler treats it as a legitimate request (mint green IS visible on the car: the Seafoam Chalk zone). The app's `finalReconcile` then catches it honestly ("Not done yet: the yellow is still yellow ... Try again / Undo"), as seen on 2026-10-04 17:15. A hard guard there (refuse a refinish whose colour word differs from every colour word in the buyer's own sentence) is NOT added: no run recoloured, the brief says fix only on a failure, and such a guard can misfire on legitimate synonyms ("the pink" -> "hot pink", "the main colour"). Add it only if a future sample recolours.
- One sample reply (run 2) says "the yellow you see there is mint green" which is loose wording but not a claim of change; the app card under it is exact.
- Single sentence, single design: other phrasings ("turn the yellow to purple", "recolour the yellow") were not sampled (cap).
