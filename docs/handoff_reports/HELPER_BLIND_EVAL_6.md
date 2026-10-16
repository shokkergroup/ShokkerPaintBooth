# HELPER BLIND EVAL 6 (2026-10-05)

- **Who ran it:** a blind Sonnet runner and judge. The orchestrator compiled this report from the runner's final message.
- **Corpus:** `_easy_claude_work/eval/blind6/corpus6.jsonl`, 70 items written blind, 30 of them conversations.
- **How:** in-app on test server 59879, using `pw/convo_inapp.py specs=specs6.json tag=blind6` (CDP 9871).
- **Outputs:** judged lines in `_easy_claude_work/eval/blind6/judged6.jsonl`; contact sheets in `blind6/sheets/`, reruns in `blind6/sheets_re/`.
- **Code under test:** FINAL 7. Fix pass 8 was in progress during the run.

## Per kind (judge reads the answers and looks at the before/after sheets)

| kind | n | good | ok | bad | HARMFUL | good+ok | good |
|---|---|---|---|---|---|---|---|
| how-to | 10 | 9 | 1 | 0 | 0 | 100 | 90 |
| question | 10 | 6 | 3 | 1 | 0 | 90 | 60 |
| vague | 8 | 3 | 4 | 1 | 0 | 88 | 38 |
| edit | 12 | 4 | 2 | 4 | 2 | 50 | 33 |
| back-and-forth | 30 | 4 | 12 | 11 | 3 | 53 | 13 |
| **ALL** | 70 | 26 | 22 | 17 | 5 | **69** | **37** |

**Compared with round 5:**

| | R5 | R6 |
|---|---|---|
| how-to | 73 | 100 |
| question | 50 | 90 |
| vague | 75 | 88 |
| edit | 75 | 50 |
| back-and-forth | 40 | 53 |
| overall good+ok | 63 | 69 |
| good-only | 23 | 37 |
| HARMFUL | 5 | 5 |

Corpus 6 is harder on edits: outlines on named parts, "except X", swaps and pinlines.

**Harness verdict:** its own SUMMARY was 33/70 with 20 harmful. That harmful count is inflated by a preview-capture glitch: on question-only turns, the preview sometimes grabs the original livery.

## HARMFUL (5)

1. **b6-040** — "everything except the roof gets a pearl finish": the whole sheet except the roof became solid pink, wiping numbers, sponsors and decals on about 90% of the car. The reply claimed only the finish changed. It reproduced on rerun, and the orchestrator looked at `sheets_re/b6-040.png`.
2. **b6-008** — "outline the number panel in gold" produced only a card, and "thinner" was not understood. Then "make it white instead" painted the whole car white.
3. **b6-009** — no orange hood stripe appeared, and "thin black line each side of it" painted both side panels black.
4. **b6-020** — "red pinstripe on the left door" went on both sides. "Same on the right" got the reply "no earlier change". "Change both to gold" then made the whole car gold.
5. **b6-042** — "fine silver pinline between the red and white" recoloured both colours everywhere, sponsors included.

## Other bad items

- **b6-003:** "show me gold options" applied the gold instead of listing options; "the second one" got "which one?".
- **b6-004, b6-017, b6-041:** nothing applied in any turn.
- **b6-005:** "something else" and "more desert" only opened a catalogue.
- **b6-010:** "flip it" got a card, and "less red" flattened the gradient to a solid colour.
- **b6-012:** flames on the side gave a card, then "did not catch".
- **b6-016:** a whole-car yellow left an unresolved step.
- **b6-018:** "second one on the front bumper" had no list to refer to.
- **b6-022:** the rat rod was never applied.
- **b6-062:** "what is trading paints / .mip" was read as a catalogue search.
- **b6-067:** "not feeling it" got an unrelated card, with no undo offered.
- **Also bad:** b6-025, b6-030, b6-031, b6-034, b6-039.

## What worked

- **How-tos:** all 10 were correct and specific (numbers, export, undo, sponsors, gradients, save, mirror).
- **Questions:** spec map, clearcoat direction, preview vs render, zone, chrome as a base.
- **Single-part colour and finish edits:** these worked, including spec-only satin/chrome that keeps the colours.
- **Mid-conversation questions:** answered without changing the car.
- **Vague asks:** got menus.
- **Honest refusals:** unpaintable parts were refused honestly.
- **Undo:** restored the car exactly.

## Failure classes to fix next (FINAL 8 / 9)

1. **Finish-only plus "except X" repaints the paint and decals.** It must use a spec-only Foundation finish with colour source and keep the decal protection.
2. **Follow-up scope bleed.** "Make it white instead", "change both to X" and "line each side of it" must stay on the previous target.
3. **Pinlines, outlines, trim and flames** end as cards or unresolved steps instead of being applied.
4. **Relative follow-ups don't resolve:** "same on the right", "the second one", "thinner", "flip it", "less red", "something else".
5. **Pinline between colours** recolours both colours.
6. **The Trading Paints / .mip question** is read as a catalogue search.
