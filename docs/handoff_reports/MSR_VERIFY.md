# MSR-VERIFY: do headless-passing asks LOOK right in the real app? (2026-10-03, 15:39-17:12)

Method: private headless Chrome (CDP 9611), test server 59879, PSD Next Gen City car, built-in helper only (SpbAI.cached forced unconfigured). Per ask: send to helper, press Use on the first stack card if one is offered (otherwise the helper applied/answered directly), wait for render, save preview + zone list (`_easy_claude_work/eval/msr_verify/c<cycle>_<id>.json|_preview.png`), look at the PNG, judge. Verdicts: `eval/msr_verify/verdicts.jsonl`; every partial/fail appended to `eval/mad_misses.jsonl` (`round:"inapp", verify:true`). Scripts: `pw/msr_verify.py`, `msr_pick.py` (picks headless-passing asks: offline composite >= 0.99 and is_stack, spread over classes), `msr_log.py`, `msr_chrome_up.py`.

## Running table (each cycle = 12 new asks + 3 re-checks of earlier failures; cycle 0 was an unfiltered warm-up pick)

| cycle | asks | pass | partial | fail | notes |
|---|---|---|---|---|---|
| 0 (unfiltered) | 13 | 2 | 3 | 8 | not score-filtered; found the "nothing applied" routes |
| 1 | 12 | 3 | 6 | 3 | incl. owner pink camo rattlesnake |
| 2 | 15 | 4 | 3 | 8 | 3 re-checks: M027 M043 M273 unchanged |
| 3 | 15 | 2 | 5 | 8 | 3 re-checks unchanged |
| 4 | 15 | 1 | 6 | 8 | 3 re-checks unchanged |
| 5 | 15 | 2 | 6 | 7 | 3 re-checks unchanged |
| 6 (last) | 15 | 0 | 10 | 5 | incl. owner ask again; 1 re-check improved (M027) |

100 verdicts over ~70 distinct asks: 14 pass, 39 partial, 47 fail. Only the in-app flat preview was judged (see not-verified below).

## Recurring visual failure modes (with example ids)

1. **Headless "stack" pass is not what the app does.** The headless score reads the kit card; in the app many passing asks never produce a stack: "I do not know a look called ..." (M312 mamba, M022 feathers, M042 synthwave sunset, M048, M053, M274 Truchet), glossary/manual text instead of a design (M358, M595), or a wrong route into edit-the-existing-livery ("Which colour are the stripes?" for zebra M006 and Ghost Camo M280). Nothing applied = fail.
2. **Pattern at 40%/x1 is invisible or buried** (the stack default): Snake Skin on Cyber Camo (owner ask, M001, M517), barbed wire (M084, M508), kevlar weave (M159, M181), leopard (M531), splatter (M527, M091), hex on black (M329, M081), denticles (M018). The base reads, the second layer does not.
3. **Wrong colour family from the base's own palette + the hue/sat/bri nudges**: Neon Rush lime dominates "pink" asks (M278, M423, M457), Reactive Candy Reveal turns "candy apple red" magenta (M108, M043), Cold Fire stays cold for "warm" (M273), Radioactive Glass #16FF00 for any green/camo (M003, M531, M605: pink camo on a green car gave NO pink), CF Sapphire Ice at brightness -57 for "pale blue" (M250, dark noise).
4. **Saturation -100 / brightness shifts flatten colour**: Storm Waterspout sat -100 gave black-and-white for "aqua and white" (M537); Piano Black / Arcade Afterhours sat -100 (M359, M329) lose the requested neon/gold.
5. **Recolour of a colour that numbers/sponsors share also changes the numbers** (M597 gold to black, M066 green hex): breaks "numbers untouched" (the helper prints a heads-up but still does it).
6. **Spec-only layers are invisible in the flat preview** (M346, M458, M221, M338, M196, M571 weave/hammer, M568 scales, M059): cannot be judged by eye here, and the helper answers them with no visible change at all.
7. **Mood/vibe words collapse to a plain base** ("stealth rainbow" -> matte black M509, "oil" -> plasti dip M056, wet sand M510, "grunge faded black" -> manual page): the sheen/colour-shift half of the ask is dropped.
8. **Scale mismatch**: "tiny fish scales" gave ~100px peach/teal scales and lost pearl white (M009).
9. Hard bug (fixed during the run): M027 "marble under candy red" errored `unknown spec pattern id "undefined"` until cycle 6, now applies flat red candy but drops the marble.

Passes (what works): plain recolour + one visible texture (M008 emerald dragon scales, M011 python skin, M608 tie-dye swirls, M557 hammered silver + red stripes, M169 yellow + black stripes, M471 orange matte hood, M459/M236 subtle texture).

## Owner ask: "a pink camo rattlesnake look"
First (cycle 0/1) and last (cycle 6) previews are byte-identical (same md5): Cyber Camo hue +28/bri +34 + Snake Skin 40%. Reads as magenta + blue/cyan pixel camo, roughly 40% blue; no scale/snake read at all. Verdict **partial** both times; no fix reached this path during the run.

## Fixer pointers
- Raise default second-layer strength/scale when the ask names the pattern (snake, barbed wire, weave) and add a visibility check on the rendered composite.
- Guard hue/sat/bri nudges: never sat -100 on a coloured ask; check the dominant hue of the rendered base against the named colour.
- Route "I do not know a look called X" asks through the finish/pattern search before giving up (the headless tool lane already handles them).
- Numbers-share-colour recolours should be refused or region-limited, not warned.

## NOT verified
Only the flat in-app preview of the Next Gen City PSD at 1024 (wireframe/Mask layers were still drawn on top; Wire visibility toggle in my driver did not hide them). No gloss/metal/clearcoat/spec behaviour (flat preview is blind to it), no 3D car, no other cars, no Use on the 2nd/3rd stack card, no slider moves, no online/MCP AI. Some verdicts (M167, M410, M508, M510, M338) were made from zone data plus a related viewed run, not their own screenshot. Asks were picked by my own filter because the scoreboard has no per-ask pass list; I used `intricate_mad_b*_r1_score.json` offline composite >= 0.99 and is_stack.
