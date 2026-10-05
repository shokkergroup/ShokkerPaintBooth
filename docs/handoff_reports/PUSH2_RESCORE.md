# PUSH2-RESCORE
Rounds run with `mad_run.py --once --round-min 0 --stop 23:59` (appends round N to mad_scoreboard.json) + B1 `intricate_run.js postN`.
| | any | offline | tool | B1 any | B1 vs baseline |
|---|---|---|---|---|---|
| round 7 (17:24) | 0.515 | 0.343 | 0.495 | 0.800 | |
| round 8 / post1 (17:45, advisor.js as of 17:32 = PUSH-VISIBLE) | 0.515 | 0.343 | 0.495 | 0.800 | +0.195 |
| round 9 / post2 (18:05, advisor.js as of 17:52 = + PUSH2-PLANNER) | 0.520 | 0.347 | 0.498 | 0.803 | +0.198 |
Round 8: 0 flips, every class identical. Round 9: 3 fixed (M027 M029 M137), 0 regressions; material_mashup 0.564->0.615, placement 0.220->0.244.
Attribution: PUSH-ROUTE is in spb-pro-ai.js, not loaded by the headless runner - unmeasured. PUSH-VISIBLE changes apply-time defaults, which the 8 metrics do not score - zero delta. The round-9 gain came from edits made to spb-pro-advisor.js between 17:32 and 17:52 (PUSH2-PLANNER); concurrent edits mean it is not separable from other advisor changes.
