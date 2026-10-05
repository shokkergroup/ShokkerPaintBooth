# REGRESS (2026-10-03, run 1 at ~17:55-18:04, Chrome CDP 9677, server 59879)
Logs: _easy_claude_work/eval/regress_now/*.log (run 1), regress_post/*.log (run 2, partial).
FAIL t259_elem_policy.py arcachevy25: "B teach card shown" and "B my numbers change switched off". After `those are not the numbers`
  the reply is the self-help checklist ("I found 3 likely reasons ... Zone 1 does not cover any pixels") instead of the teach card,
  and the numbers zone stays on; script then dies at canvas[data-elem] bounding_box (consequence). Same on retry.
  Likely: SELF-BRAIN routing (spb-pro-ai.js / self-help router) claims the "not the numbers" negation before the element-policy handler (spb-pro-elements.js).
Other results: all PASS (see summary in chat).
Run 2 (18:08-18:11, after advisor edit): t259 same 2 FAILs; wp12 13/13; design_compound 50/50+22/22; NEW FAIL stack_test.js 93/94: "SINGLE unchanged: something subtle for the hood" output differs (run 1 was 94/94) -> likely js/spb-pro-advisor.js stackPlan (PUSH2-PLANNER) now claiming a single-finish ask.
