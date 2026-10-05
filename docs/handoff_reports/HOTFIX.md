# HOTFIX (2026-10-03, 18:12-18:27, Chrome CDP 9681, server 59879)

## 1. t259 "those are not the numbers" -> self-help checklist (FIXED)
- Root cause: `send()` in `js/spb-pro-ai.js` calls `selfHelpClaim(text)` (SELF-BRAIN / PUSH2-SELFHELP) BEFORE `ask()`, where
  `NOT_ELEM_RE` -> `offlineElemWrong()` lives. The why-not classifier claimed the negation and answered "I found 3 likely reasons ...".
- Fix (`js/spb-pro-ai.js`): new `ELEM_REPLY_RE` ("there are none ...", "no, I will show you", "yes, those are them"), `elemCardPending()`
  (any AI entry with `elem && !elem.done`) and `elemOwnsText()` = NOT_ELEM_RE || ELEM_REPLY_RE || pending card.
  `selfHelpClaim()` returns null first when `elemOwnsText()`; the SpbSelfHelp `redirect` / `runDoIt` pre-pass in `send()` is skipped too.
- Token: `spb-pro-ai.js?v=20261003hotfix` (own token only). Synced via `sync_mine.json` (--check: no drift).

## 2. stack_test "SINGLE unchanged: something subtle for the hood" (NOT an advisor regression - NOT changed)
- Diff: same 6 keys, only `base::satin_metal` and `monolithic::cool_down` swapped rank (snapshot: eggshell, cool_down, satin_metal, ...).
- Proof it is not PUSH2-PLANNER: `node _easy_claude_work/hotfix_single_diff.js old` loads the pre-PUSH2 advisor
  (`stack_base/spb-pro-advisor.before-push2.js`) and gives the SAME new order. `stackPlan()` returns null for this ask (no "stack planned").
- Real cause: `js/spb-ai-cards-data.js`, `js/spb-lsa-data.js`, `js/spb-ai-cards.js` were rebuilt at 18:08 (another lane; `_atlas_cards/lsa_*`
  also 18:08). The new LSA/card scores reorder two near-tied matches. Outside this lane: owner/lane of the data rebuild decides
  (accept + re-snap `stack_base/singles.json`, or revert the data). advisor.js untouched.

## Gates
| gate | result |
|---|---|
| t259_elem_policy.py arcachevy25 | 11/11 |
| wp12_askfirst.py | 13/13 |
| selfhelp_inapp.py | ran clean, errors [] |
| route_inapp.py | 3 stacks (2 kit replies + 1 layered "Done") + 2 edits Done |
| stack_test.js | 93/94 (only the data-rebuild single above) |
| selfhelp_test.js | 163/182 cite-any, guards 22/22 |
| selfhelp_holdout_test.js stuck_holdout2.json | 16/30, guards 22/22 |
| edit_corpus.js | 409 / 0 mismatches |
| edit_req_test.js | 17 / 0 |
| convo_test.js | 52/52 |
| tool_test.js | 15/15 |
| design_compound_test.js | 50/50, guards 22/22 |
| adv_fp.js (all *prompts*.txt) | TOTAL 284 claimed 220, identical to last fixa_fp |
| corpus_eval.js | other 400/400 left alone, finish claimed 1031/1100 |
| node --check, scan_ctrl.py | OK, 0 control chars |

Not verified: typed "there are none on this paint" / "no, I will show you" as free text (they are now kept from self-help, but no
text handler routes them to the card actions - the buttons do); the live app (59876) untouched, needs the owner's reload.
