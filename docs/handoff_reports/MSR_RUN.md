# MSR-RUN - mad scientist scoring log

Pass = every applicable metric 1.0 on that path (any = best of offline/tool per metric). Misses: `_easy_claude_work/eval/mad_misses.jsonl`; scores: `mad_scoreboard.json`.

- 15:46 B1 200 round 1 composite: any 0.783 offline 0.542 tool 0.779
- 15:46 batch 1 round 1: n=51 any-pass 0.451 offline 0.314 tool 0.451 composite(any) 0.719; 28 misses appended
- 15:46 batch 2 round 1: n=50 any-pass 0.420 offline 0.280 tool 0.380 composite(any) 0.702; 29 misses appended
- 15:46 batch 3 round 1: n=53 any-pass 0.302 offline 0.094 tool 0.302 composite(any) 0.595; 37 misses appended
- 15:46 batch 4 round 1: n=49 any-pass 0.735 offline 0.714 tool 0.735 composite(any) 0.884; 13 misses appended
- 15:46 batch 5 round 1: n=57 any-pass 0.404 offline 0.210 tool 0.386 composite(any) 0.595; 34 misses appended
- 15:46 batch 6 round 1: n=50 any-pass 0.340 offline 0.240 tool 0.280 composite(any) 0.555; 33 misses appended
- 15:46 batch 7 round 1: n=59 any-pass 0.458 offline 0.356 tool 0.458 composite(any) 0.706; 32 misses appended
- 15:46 batch 8 round 1: n=53 any-pass 0.377 offline 0.170 tool 0.340 composite(any) 0.594; 33 misses appended
- 15:47 batch 9 round 1: n=45 any-pass 0.511 offline 0.400 tool 0.511 composite(any) 0.769; 22 misses appended
- 15:47 batch 10 round 1: n=70 any-pass 0.429 offline 0.257 tool 0.429 composite(any) 0.714; 40 misses appended
- 15:47 batch 11 round 1: n=61 any-pass 0.492 offline 0.295 tool 0.492 composite(any) 0.750; 31 misses appended
- 15:47 batch 12 round 1: n=12 any-pass 0.500 offline 0.417 tool 0.417 composite(any) 0.778; 6 misses appended
- 16:02 ROUND 2 (610 asks, 12 batches): any-pass 0.470 offline 0.307 tool 0.454 | B1 composite any 0.790 (off 0.546 tool 0.784) | fixed 19, REGRESSIONS 4 -> M172, M557, M564, M571
  **REGRESSION** ids: M172, M557, M564, M571
- 16:19 ROUND 3 (610 asks, 12 batches): any-pass 0.482 offline 0.315 tool 0.466 | B1 composite any 0.790 (off 0.546 tool 0.784) | fixed 7, REGRESSIONS 0
- 16:35 ROUND 4 (610 asks, 12 batches): any-pass 0.500 offline 0.331 tool 0.484 | B1 composite any 0.791 (off 0.546 tool 0.784) | fixed 11, REGRESSIONS 0
- 16:52 ROUND 5 (610 asks, 12 batches): any-pass 0.513 offline 0.341 tool 0.493 | B1 composite any 0.800 (off 0.557 tool 0.793) | fixed 8, REGRESSIONS 0
- 17:08 ROUND 6 (610 asks, 12 batches): any-pass 0.515 offline 0.343 tool 0.495 | B1 composite any 0.800 (off 0.557 tool 0.793) | fixed 1, REGRESSIONS 0
- 17:24 ROUND 7 (610 asks, 12 batches): any-pass 0.515 offline 0.343 tool 0.495 | B1 composite any 0.800 (off 0.557 tool 0.793) | fixed 0, REGRESSIONS 0

## Final (17:40)
Rounds 1-7 on 610 asks / 12 batches (batch 12 was scored partially in round 1; all later rounds are full). Any-pass 0.446 -> 0.515, offline 0.300 -> 0.343, tool 0.431 -> 0.495; B1 composite(any) 0.783 -> 0.800 (flat since round 5). 4 round-2 regressions (M172 M557 M564 M571) judged noise by FIX-B; 0 since. 296 asks never passed (scoreboard `never_passed`). Weakest classes: placement 0.22, scale 0.26, ambiguous 0.20, weather_light 0.35, era_vibe 0.36. intricate_run.js was syntactically broken only 15:39-15:44 (fixed before the loop started at 15:45); no scored round used the broken file.
- 17:45 ROUND 8 (610 asks, 12 batches): any-pass 0.515 offline 0.343 tool 0.495 | B1 composite any 0.800 (off 0.557 tool 0.793) | fixed 0, REGRESSIONS 0
- 18:05 ROUND 9 (610 asks, 12 batches): any-pass 0.520 offline 0.347 tool 0.498 | B1 composite any 0.803 (off 0.560 tool 0.793) | fixed 3, REGRESSIONS 0

## Post-push rounds
- 17:45 ROUND 8 = post-PUSH-VISIBLE: identical to round 7 (0 flips). 18:05 ROUND 9 = + PUSH2-PLANNER edits: any 0.520 / off 0.347 / tool 0.498, B1 0.803, 3 fixed 0 regressions. See PUSH2_RESCORE.md.
