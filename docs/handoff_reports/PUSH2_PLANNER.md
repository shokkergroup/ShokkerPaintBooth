# PUSH2-PLANNER (2026-10-03) - layer order, part-bound layers, size words in the stack planner

Lane: `js/spb-pro-advisor.js` (B2 stack planner parse + apply only), `_easy_claude_work/stack_test.js` (+ `push2_tests.js`, 12 cases), this file.
Token `spb-pro-advisor.js?v=spb-pro-advisor-20261003push2b`, synced with `sync_mine.json` (`--check`: no drift). Pre-edit copy: `_easy_claude_work/stack_base/spb-pro-advisor.before-push2.js`. Patch scripts: `_easy_claude_work/push2_patch.py`, `push2_patch2.py` .. `push2_patch4.py`.

## The three rules
1. **Layer order** (`stUnder`, run before `stOnSplit` in `stackParse`): "X under / underneath / beneath / below Y" -> "Y with X" (X = the lower layer = pattern, Y = base look). "under it / that / the paint / the clear ..." is untouched (still the B2 spec cue), and so is a sentence that already orders its layers (comma / over / on top before "under" - M596). "Y over X" / "Y on top of X" already worked. Coat case "carbon under a candy coat" -> "carbon with a candy coat": the planner still makes CANDY the base + carbon pattern (visually candy over carbon, but NOT the asked "carbon base + candy coat") - open.
2. **Placement** (`stackPlan` -> `plan.lparts`; `applyPlan` stackWith): when the ask names parts and the stack has a base + a layer, every named part is collected (hood / roof / trunk / spoiler / bumpers / sides as `region.part`, stripes as `region.element:'stripes'`; numbers never). Apply = the base step on the WHOLE car (body zone, pattern cleared to `none` on an edited body zone) + one `add_zone` "<Parts> <layer>" with the same finish / colour / adjust + the pattern / shine, `region.part` = the union ("hood + roof" -> ["hood","roof"]). "on just the sides" / "only on the hood" normalised. Reply: "on the body + the hood" and a `Placement:` line. Plan `target` still names the part (scorer parts_hit, M451).
3. **Scale words** (`stScaleAbs` / `stScaleRel`, layer scale in `stackPlan`): explicit numbers stay absolute ("crushed to 20%" = 0.2, "50% scale" = 0.5); relative words multiply the layer's OWN default (pattern default = `stFineScale` 0.7 / 0.85 / 1.1, spec 1): finer / fine / small x0.6, tiny / micro x0.4, half size x0.5, big / chunky / bold x1.4 (at least x1.1, so "big" never comes out smaller than normal - the old "big kevlar" case), huge / double x2. Reply: `Size: Marble Veining at "finer" = x0.51 (0.6 of its normal x0.85).` The base-texture `scaleBase` path is unchanged.

## Gates
| gate | before | after |
|---|---|---|
| `node _easy_claude_work/stack_test.js` | 82/82 | 94/94 (82 old + 12 PUSH2) |
| convo_test / tool_test / adv_fp | 52/52, 15/15, 0 claimed | 52/52, 15/15, 0 claimed |
| mad asks (610) any-pass, same rule as MSR-RUN, before = pre-edit advisor run now | 0.510 (MSR round 7 log: 0.515) | 0.515 |
| placement / scale / stack3 / ambiguous | 0.220 / 0.239 / 0.750 / 0.200 | 0.244 / 0.239 / 0.750 / 0.200 |
3 asks fixed, 0 regressed (`_easy_claude_work/push2_rates.py push2_before push2`). The SCALE class does not move because the scorer's `scale_hit` reads the chosen item's card scale facet (fine / broad), not the layer scale the planner sets - metric-blind to this rule.

## In-app (test server 59879, private Chrome 9651, NG City, built-in helper only; `_easy_claude_work/pw/push2_inapp.py` -> `push2_inapp.out`)
1. "marble under candy red" -> stack cards (3 kits, 6/6 thumbs); Use -> 1 change: zone "Everything Else" = reactive_candy_reveal (hue -22 sat +25 bri -28) + pattern marble_veining 65% x0.85. PASS (was: plain candy red, marble dropped).
2. "snake scales on the hood only in gold" (same session, after 1) -> "2 layers on the body + the hood" + Placement line; Use -> 2 changes: NEW zone 0 "Hood Snake Skin" = cx_gold_green #D4A017 + snake_skin 65% x1.1; "Everything Else" = cx_gold_green, pattern none. PASS on the zone list.

## NOT verified
- The hood zone's region could not be read from the zone list (the ZS reader prints region "" for every zone); the part binding is proven in node (`region.part:'hood'`) and by the zone name, not by a rendered preview - no preview image was looked at.
- Ask 2 inherited hue -22 / sat +25 / bri -28 on the body from ask 1 (edit_zone does not reset sliders a stack does not set) - pre-existing stack behaviour, not changed.
- "carbon under a candy coat" = candy base + carbon pattern, not carbon base + candy coat. Stripes as a layer region use `region.element:'stripes'`, which needs the element finder to have found stripes (flat paints) - not tested in-app. MCP / paid tiers not run.
