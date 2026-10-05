# INT - deep cards integrated + measured (2026-10-03)

## What was merged
`python scripts/ai_atlas/merge_deep_cards.py --write --min-conf 2` over `_atlas_deep/out/` (out_v1_strips never read). 27 shards OK, 2 lines invalid (shard_011 lines 3-4, writer was mid-shard: "asks must be 8-12 items", skipped).
1,330 valid units -> **1,336 cards changed** (spec 287, pattern 85, base 964, monolithic 0); 0 skipped by min-conf (min seen = 2: 30 units conf 2, 262 conf 3, 860 conf 4, 178 conf 5). Coverage 1,329 of 4,722 units (spec 286/301, pattern 85/319, base 958/1138, monolithic 0/2964). Backup: `_atlas_cards/cards.before_deep_20261003.jsonl` (pre-deep original).
Script change: `merge_deep_cards.py` gained `--min-conf N`, `--only a,b`, `--exclude a,b` (shard ids as `7` / `007` / `shard_007`), and prints cards by type + units by confidence. Still idempotent (look0/syn0). Re-merge stragglers: rerun the same command, then steps below.

## Rebuild (commands)
`python scripts/ai_atlas/build_cards_js.py` (chains LSA; cards 4799, data js 3.19 MB) -> `node --check` both OK -> `SPB_CARDS_V` default `20261003f` -> `20261003deep`, `SPB_LSA_V` default `20261003a` -> `20261003deep` in js/spb-ai-cards.js; paint-booth-v2.html `spb-ai-cards.js?v=spb-ai-cards-20261004d` -> `...20261004deep` (the two data files have NO html token: spb-ai-cards.js loads them with those default versions) -> scan_ctrl 0 -> `sync-runtime-copies --manifest _easy_claude_work/sync_mine.json --write` (4 files) then `--check`: **no drift detected**.

## Before / after (pre = current code, old cards; post = deep merge; baseline = B1 original)
| measure | baseline | pre_merge | post_merge |
|---|---|---|---|
| intricate composite offline | 0.152 | 0.536 | 0.537 |
| intricate composite tool | 0.589 | 0.761 | 0.773 |
| intricate composite any | 0.605 | 0.771 | 0.781 |
| stack_shape offline / tool | 0.07 / 0.40 | 0.586 / 0.753 | 0.586 / 0.784 |
| pattern_hit tool / spec_hit tool | 0.23 / 0.36 | 0.56 / 0.73 | 0.57 / 0.77 |
| must_not_ok tool / scale_hit tool | 0.70 / 0.64 | 0.80 / 0.64 | 0.85 / 0.58 (worse) |
| truth set pipe_new HIT / CLEAN / BAD / GOOD@6 | - | 54% / 54% / 0.2% / 15.8% | 55% / 54% / 0.1% / 15.6% |
| truth set rank HIT / CLEAN / GOOD@6 | - | 52% / 48% / 12.3% | 55% / 52% / 12.8% |
| gold judge pipe_new relevance / top3 / clear hit / bad picks | - | 0.89 / 1.03 / 75% / 38% | 0.91 / 1.09 / 77% / 37% |
| convo_test | - | 52/52 | 52/52 |
| tool_test | - | 15/15 | 15/15 |
| stack_test | - | 64/64 | **61/64** |
| adv_fp | - | 0 claimed | 0 claimed |

Per-class intricate delta post-pre (any): constraint +0.068, placement +0.034, scale +0.011, negated +0.013, question +0.008, like_but_stack **-0.042** (tool), others 0. Gains are small and positive overall (+0.010 composite); the big lift vs baseline (+0.17) is the stack planner already on disk, not the cards. Gold judge: 2 runs only, ~$0.058 total (judge caches by ask+keys, so the post run re-judged only changed rows).

## What got worse (plainly)
- stack_test 3 failures are all "SINGLE unchanged" snapshot checks (`stack_base/singles.json`): the ranking tail of "show me chrome finishes", "something subtle for the hood", "gold flake finish" shifted (e.g. f_satin_chrome / black_chrome dropped from the 6 for chrome; eggshell replaced woc_shamma_cotton). Top results unchanged. Not stackPlan misfires. Needs the owner/orchestrator to re-snapshot (`node _easy_claude_work/stack_test.js snap`, not in my lane) or accept.
- tool scale_hit 0.64 -> 0.58 and like_but_stack tool -0.042 (matching is by returned items' facets; small n).
- deep coverage is only 28% of units and monolithic = 0, so effect is bounded; rerun after stragglers.

## Step 7 (expose `deep`) - NOT done
`build_cards_js.py` (outside my lane) packs a fixed 18-field row; `deep` would need a 19th field (look_close/stack/not for ~1.3k+ cards, grows the 3.2 MB file) plus a new unpack in `spb-ai-cards.js` and a `finish_details` change in spb-pro-ai.js (forbidden file). Exact change: add `c.get('deep') and [look_close, stack, not]` as row[18] in build_cards_js.py, read `r[18]` in spb-ai-cards.js `lookup`, show it in finish_details.

## Files / outputs
Evidence in `_easy_claude_work/eval/int_pre_*` and `int_post_*` (+ `intricate_pre_merge|post_merge.jsonl`, gold judged copies).

# FINAL pass (all shards, tag `final`)
Waited ~20 min for shard_021; 4722/4722 units valid (spec 301, pattern 319, base 1138, monolithic 2964). `merge --write --min-conf 2`: 4721 units used (1 below conf 2 skipped), cards cards by type spec 301 / pattern 318 / base 1144 / monolithic 3035; 3,462 cards newly changed + 1,336 already current. Rebuild (packer now ships the 19th `deep` field): `spb-ai-cards-data.js` **11,743,029 B** (was 3.19 MB), `spb-lsa-data.js` 1,619,351 B, `_atlas_cards/cards.jsonl` 18.2 MB. node --check OK. Tokens: SPB_CARDS_V / SPB_LSA_V defaults `20261003final`; html `spb-ai-cards.js?v=spb-ai-cards-20261003final` (DEEP-SHIP had set `...deepship`, replaced). scan_ctrl 0. Sync --write then --check: no drift.

| measure | baseline | pre_merge | post_merge (28%) | FINAL (100%) |
|---|---|---|---|---|
| intricate composite offline / tool / any | 0.152 / 0.589 / 0.605 | 0.536 / 0.761 / 0.771 | 0.537 / 0.773 / 0.781 | 0.534 / 0.772 / 0.780 |
| stack_shape offline / tool | 0.07 / 0.40 | 0.586 / 0.753 | 0.586 / 0.784 | 0.586 / 0.802 |
| pattern / spec hit (tool) | 0.23 / 0.36 | 0.56 / 0.73 | 0.57 / 0.77 | 0.59 / 0.79 (any-path) |
| truth pipe_new HIT / CLEAN / GOOD@6 | - | 54 / 54 / 15.8 | 55 / 54 / 15.6 | 56 / 56 / 15.5 |
| truth rank HIT / CLEAN / GOOD@6 | - | 52 / 48 / 12.3 | 55 / 52 / 12.8 | 56 / 54 / 12.7 |
| gold judge relevance / top3 / clear hit / bad | - | 0.89 / 1.03 / 75% / 38% | 0.91 / 1.09 / 77% / 37% | 0.90 / 1.07 / 76% / 37% |
| convo / tool / adv_fp / deep_test | - | 52, 15, 0 | 52, 15, 0 | 52/52, 15/15, 0 claimed, deep_test 9/9 |
| stack_test | - | 64/64 | 61/64 | 62/64 then 64/64 after re-snap |

Final delta vs pre_merge (composite any): +0.008 (offline -0.001, tool +0.011); scale +0.068, constraint +0.039, ambiguous +0.050; mood_stack -0.033, like_but_stack -0.017, question -0.015. Gold judge is flat within noise vs post_merge (0.91 -> 0.90); full coverage did NOT add measurable lift beyond the first 28%. Total gold judge spend ~$0.083 (3 runs; owner cap was exactly two before/after, third requested by coordinator).
stack_test re-snap (`node _easy_claude_work/stack_test.js snap`, old copy `_easy_claude_work/eval/int_stack_singles_before_resnap.json`): only 2 of the 3 earlier rankings still differed. "something subtle for the hood": satin_metal, wave_moire_metal, woc_shamma_cotton, trizone_glass_metal_matte, mirage, silk -> eggshell, cool_down, satin_metal, moonshine, sparkle_constellation, heat_haze. "gold flake finish": gold_flake, cx_gold_green, msk_leaf_gilding, champagne_flake, victory_lane, candy_gold -> gold_flake, cx_gold_green, cf_rose_gold_dust, msk_leaf_gilding, victory_lane, candy_gold. ("show me chrome finishes" is back to its old order.)
Not verified: live app / picker UI, load time with the 11.7 MB data file (not measured), `finish_details` deep display in the real app.
