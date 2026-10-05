# HELPER BLIND EVAL 5 (2026-10-05)

- **Runner and judge:** a blind Sonnet agent. The orchestrator compiled this report from its final message, because the subagent was not allowed to write files.
- **Corpus:** `_easy_claude_work/eval/blind5/corpus5.jsonl`, 60 items written blind.
- **How it ran:** in the app on test server 59879, using `_easy_claude_work/pw/convo_inapp5.py`. That is a copy of `convo_inapp.py` that also captures the panel text. Specs are in `eval/convo_inapp/specs5.json`.
- **Results:** judged lines in `_easy_claude_work/eval/blind5/judged5.jsonl`; shots in `_easy_claude_work/eval/convo_inapp/blind5/shots/`.
- **Caveat:** search ranker sl5 landed after about 45 items.

## Accuracy per kind (judge, reads the answers and looks at the shots)

| kind | n | good | ok | bad | HARMFUL | good+ok | good only |
|---|---|---|---|---|---|---|---|
| how-to | 15 | 5 | 6 | 4 | 0 | 73% | 33% |
| question | 6 | 3 | 0 | 2 | 1 | 50% | 50% |
| vague | 12 | 1 | 8 | 3 | 0 | 75% | 8% |
| edit | 12 | 5 | 4 | 3 | 0 | 75% | 42% |
| back-and-forth | 15 | 0 | 6 | 5 | 4 | 40% | 0% |
| **overall** | 60 | 14 | 24 | 17 | 5 | **63%** | **23%** |

**The harness's own verdict is 45/60 with 8 harmful.** It checks only the part masks:

- it never reads the answer, so a wrong FAQ card plus "nothing changed" counts as a pass;
- it flagged b5-059, a correct number recolour, as harmful.

**Previous round (blind 4):** how-to 74, vague 72, back-and-forth 40, overall 82% with 9 harmful. This round is harsher and not like for like: there are more negations ("doors stay what they are") and more turns that refine the last turn.

## HARMFUL (5)

- **b5-019:** asked "is roughness 0 matte or shiny". The question was never answered, and a whole-car matte (spec-only) was proposed and run.
- **b5-052:** "show me the matte ones" was run as an edit, applying a whole-car matte instead of listing finishes.
- **b5-047:** "thin red line around the edge of the roof" turned the whole car red. 41,160 cells changed outside the roof.
- **b5-057:** "blue gradient on the doors" became a solid blue over the whole car, with no gradient.
- **b5-060:** "just a little on the hood" replaced the earlier whole-car black with a hood-only change, so the rest of the car reverted.

## 10 worst

1. **b5-060:** T3 wiped the earlier whole-car black. T4 "save it" opened a finish picker.
2. **b5-047:** a trim line around the roof painted the whole car.
3. **b5-057:** a door gradient became a whole-car solid colour. T3 proposed a "Distressed Patina on the whole car" step.
4. **b5-052:** T1 gave a colour-shift card, T2 applied whole-car matte, T3 asked "Which one do you mean?"
5. **b5-019:** a question was treated as an edit.
6. **b5-044 / b5-042:** overclaim. The reply said "the red (2% of the car) is now burgundy" when only 58–150 pixels changed, because the car has no red body.
7. **b5-049:** flames on the sides, then something else, then a fade. The answers were FAQ cards plus "I did not catch that"; nothing was applied.
8. **b5-058:** garbled templates: "Make the car is gold", "What should the  be?", and a literal "Show me looks for the undefined" button.
9. **b5-030:** "see me from across the track" was answered with an unrelated FAQ card about refunds and PCs.
10. **b5-054:** for "sponsors hard to read" it targeted the sponsor art itself instead of calming the body paint.

**Close behind:**

- b5-003: "looks plastic" got a reload checklist.
- b5-007: "save for iRacing" got Save project instead of Render and the file names.
- b5-008: "how" was read as a finish name.
- b5-016: metallic vs pearl got only the R channel.
- b5-029: the request was garbled.
- b5-043: a negation produced door steps that need a pick.
- b5-046: "tone it down" and "go back" were both missed.

## What worked

- **How-to cards:**
  - chrome (b5-001)
  - spec map (b5-002, b5-018)
  - chameleon (b5-009)
  - spec view (b5-012)
  - guide layers (b5-015)
  - clearcoat direction (b5-017)
  - numbers not showing (b5-021)
- **Clear single edits:**
  - roof carbon (b5-035)
  - hood candy red (b5-036)
  - left satin black with right white (b5-037)
  - spec-only chrome that keeps the colours (b5-039)
  - gold pinstripes on both doors (b5-040)
- **Decals:** numbers and sponsors stayed intact in every 1:1 shot of these items.

## Harness gaps to fix

- **No answer check:** the harness needs to judge answers, not only masks. Capture the panel text (as `convo_inapp5.py` does) and check it against the expected topic.
- **Spec-only edits:** the spec diff counts spec-only changes as "changed cells" even when the paint is identical (b5-039).
