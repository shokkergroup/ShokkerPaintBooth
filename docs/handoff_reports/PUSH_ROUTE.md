# PUSH-ROUTE (2026-10-03) - new-design asks no longer swallowed by the edit helper

Lane: `js/spb-pro-ai.js` routing only (+ `_easy_claude_work/route_test.js`, `_easy_claude_work/pw/route_inapp.py`, `chrome_up_9631.py`). Token `spb-pro-ai.js?v=20261003route`, synced (`--check`: no drift).

## Change
- `editYieldsToStack(text, ed)` (new, before `offlineAsk`): edit plan of kind `ops` whose EVERY target is `body`/`it` AND `SpbProAdvisor.classify(text).stack` is set -> the edit brain yields. Used in `offlineAsk` (step 2) and `offlineAskCore` (edit step). Colour / numbers / layer / part targets never yield, so true edits are untouched.
- `offlineLookAsk`: before "I do not know a look called X", classify -> if `.stack`, `SpbProAdvisor.answer` and, when it returns `kind:'stack'`, reply with the stack cards.

## Numbers
- route_test (MODEL of the router: recorded editPlan targets from `eval/fixb_edit_claims.txt` + live advisor classify): edit claims 163 -> 128 (35 yield to the stack planner); true edits stolen 0/5; unknown-look asks with a stack plan 3/4 ("marble under candy red" -> stackPlan null).
- Suites unchanged: edit_corpus 409/0, edit_req 17/17, convo 52/52, tool 15/15, stack 75/75, design_compound 50/50 + 22/22, selfhelp 162/182 + 22/22, adv_fp 0, corpus_eval 1031/1100 / 400/400. (None of these load spb-pro-ai.js, so they only prove the neighbours are untouched.)

## In-app (test server 59879, Chrome 9631, built-in helper only, `route_inapp.out`)
1. "a pink camo rattlesnake look" -> stack cards (3 kits); Use -> Cyber Camo base (hue +97) + Snake Skin pattern 65% x1.1 on one zone. PASS
2. "tiger stripes in orange on a satin black car" -> designer compound, 3 changes (satin black base + orange stripes on both sides). PASS (multi-layer, via compoundPlan not the advisor)
3. "marble under candy red" -> plain "body is now red candy", marble DROPPED. FAIL - the stack planner itself does not parse "X under Y" here (advisor lane, not routing).
4. "make the black matte" -> edit (black 33% matte). PASS
5. "make the numbers chrome" -> edit (numbers chrome). PASS

## Open / NOT verified
- 128 edit claims remain: accents / colour / layerword targets on design asks (e.g. "zebra stripes in red and black" -> accents) are not covered by the yield rule; a colour target is only "on the car" in the corpus env, not checked against the live palette.
- route_test does not execute spb-pro-ai.js (UI IIFE); the counts model the rule. The zone list in route_inapp was read after the reply (before==after counts are not a diff for direct asks).
- "marble under candy red": needs a stackParse fix in `js/spb-pro-advisor.js` (out of lane).
