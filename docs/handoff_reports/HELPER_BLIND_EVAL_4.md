# Offline helper - blind eval round 4 (2026-10-05)

Fresh 160-message corpus (written blind), run through the Node router (`SpbOfflineAnswer.route`, multi-turn state carried like the convo runner), then 28 items re-run in the real app (test server 59879, own Chrome CDP 9811, owner PSD) with before/after previews viewed. Where an item ran in-app, the in-app grade is authoritative (it overrides the Node-only grade in `judged4.jsonl`; both are kept: `node_grade`, `grade`).
Files: `_easy_claude_work/eval/blind4/` (corpus4, results4, judged4, judged4_node, inapp/inapp4.jsonl + PNGs, run_blind4.js, blind4_inapp.py).

## Scores (S exact / A reasonable / W wrong / H harmful)
| class | n | S | A | W | H | strict % | strict+acc % | wrong (W+H) | harmful |
|---|---|---|---|---|---|---|---|---|---|
| DO | 40 | 31 | 6 | 1 | 2 | 78 | 93 | 3 | 2 |
| PREFILL (looks) | 20 | 5 | 11 | 4 | 0 | 25 | 80 | 4 | 0 |
| ANSWER | 40 | 26 | 10 | 4 | 0 | 65 | 90 | 4 | 0 |
| ASK (vague) | 20 | 4 | 13 | 3 | 0 | 20 | 85 | 3 | 0 |
| ONLINE | 8 | 6 | 0 | 2 | 0 | 75 | 75 | 2 | 0 |
| OFF-TOPIC | 4 | 4 | 0 | 0 | 0 | 100 | 100 | 0 | 0 |
| CONVERSATIONS | 28 | 7 | 8 | 6 | 7 | 25 | 54 | 13 | 7 |
| TOTAL | 160 | 83 | 48 | 20 | 9 | 52 | 82 | 29 | 9 |

Single-turn (132 items): strict 66%, strict+acc 89%. Conversations are the weak spot: 7 of 28 harmful.
Node-vs-app: in-app moved 13 of 28 re-run items (005 H->S, 143 W->S, 154 W->S, 144/158 W->A, 133 S->H, 160 S->H, 139/141/145 W->H ...), so the Node router alone misjudges follow-ups both ways; the app's own pipeline (spelling fix, context, DeepSeek fallbacks) matters.

## Every H item (text -> what happened -> buyer expected)
- b4-022 "rooof to brushed aluminum": typo not understood -> whole car brushed shine (in-app too). Expected roof only.
- b4-036 "top of the car white": whole body repainted white (image). Expected roof.
- b4-133 "roof gold" / "darker" / "same on the hood": roof gold is invisible on a yellow car, then "darker" turned the whole yellow body bronze (image); "same on the hood" only asks. Expected roof darker only, then hood.
- b4-139 "change the color" / "orange" / "just the roof": the one-word answer repainted the WHOLE car orange (image); "just the roof" -> a how-to article. Expected roof orange.
- b4-141 "spoiler red" / "make it lighter" / "even lighter": spoiler honestly unpaintable, but "it" then lightened the whole yellow body twice (image). Expected: say the spoiler can't be painted, change nothing.
- b4-142 "pearl white sides" / "add gold flake" / "remove the flake": flake request repainted the whole body gold flake; removing it left the whole car pearl white with patchy yellow bits (image). Expected gold sparkle on the sides, then back to pearl.
- b4-145 "make it a rattlesnake look" / "with more gold": first turn only a list; second repainted the whole car flat gold, no snake (image).
- b4-148 "add stripes" / "white" / "down the middle": "white" repainted the whole car white; stripes then added in gold nobody chose (image). Expected white stripes on the yellow car.
- b4-160 "make the roof green" / undo / "redo" / "make it darker": redo says "nothing to redo" right after an undo; "darker" then darkened the whole scheme (yellow->mustard, white->grey) (image).

## Every W item
- b4-032 "kill the shine on the roof": opens an unpicked-finish form; expected matte on the roof.
- b4-042 "faded carbon": gradient how-to card. Expected a faded carbon look/prefill.
- b4-046 "tiger stripe orange": retro-stripes how-to card. Expected an orange tiger look.
- b4-055 "forged carbon with a red tint": recolours only existing crimson pixels to Hex Carbon.
- b4-059 "lightning bolts yellow on black": whole car yellow + lightning; roles of the colours swapped.
- b4-069 "what is a mask": mirror-tools card. b4-096 "difference between satin and matte": Decal Rescue card. b4-098 "does SPB do custom numbers": hide-number file-name card. b4-100 "what is the A channel for": returns the B clearcoat card (A = spec mask).
- b4-108 "put it on the thing": generic pick-a-finish how-to. b4-113 "add a number": number-modes card. b4-115 "different color please": why-colours-differ card (expected: ask which part/colour).
- b4-127 "make the mona lisa on the hood" and b4-128 "90s vaporwave sunset with palm trees": opened finish pickers/blank builder; expected the ONLINE offer.
- b4-136 "doors candy purple" / "less shiny" / "a little brighter": relative edits came back as suggestion lists, nothing applied.
- b4-137 "trunk white" / "same on the spoiler" / "no not the spoiler, the bumpers": spoiler has no paintable pixels; the correction loops the same spoiler question and never reaches the bumpers.
- b4-149 "left side red" / "right side the same" / "a bit darker both": copy-to-other-side asks instead of acting; final darken only partly applied.
- b4-150 "hood orange" / "make the orange more yellow": says "Not done yet" while it did change the hood; confusing.
- b4-155 "hood holographic" / "less rainbow" / "more": generic shine lists, hood unchanged.
- b4-156 "trunk forest green" / "thats too dark": refuses (shared zone), no darker/lighter; "spoiler same" honestly impossible.

## Top failure patterns
1. Relative/next-turn edits lose their target and hit the whole car or whole colour family ("darker", "lighter", "white", "orange", "more gold"). e.g. b4-133 (bronzed the whole body), b4-160 (darkened whole scheme). Also 141, 139, 148.
2. One-word answers to the helper's own question are treated as whole-car repaints, or ignored: "orange" (139), "white" (148), "blue" -> a suggestion list (158).
3. Relative edits on an existing look become generic suggestion lists instead of acting: "less shiny", "a little brighter" (136), "less rainbow", "more" (155), "make it lighter" at start (158).
4. "Same on X / the other side / correction" breaks: "same on the hood" (133), "right side the same" (149), "no not the spoiler, the bumpers" (137) ask a pointless question or loop.
5. Wrong encyclopedia card by keyword: "what is a mask" -> mirror (069), "satin vs matte" -> decal rescue (096), "A channel" -> B (100), "custom numbers" -> hide-number switches (098), "add a number" (113).
6. Misspelled or unusual part words fall to whole-car: "rooof" (022), "top of the car" (036); and colour-role misreads in looks ("yellow on black", "forged carbon with red tint").
Also: custom art needs an ONLINE offer but "mona lisa"/"vaporwave scene" opened a finish picker (127/128); and flake/gold edits on pearl wreck the whole body (142).

## What worked
- Single-turn recolours/finishes with except/keep ("everything blue except roof and hood", "keep the numbers", multi-part lists, colour-swap, "paint the white parts red" limited to body layers): 31/40 exact, numbers and sponsors never touched in any DO item.
- ANSWER cards for spec maps, clearcoat 16, zones/priority, export, Trading Paints (.mip), user ID, render, undo, candy/pearl/holographic/chameleon, base scale: 26/40 exact. Follow-up Q&A in-app ("how do I export" -> "and then what" -> "where do I put the id") is correct.
- Honest refusals (spoiler has no paintable pixels), undo/"undo that" reverting the last step, "keep my colours" after chrome, off-topic (4/4), vague-ask chips ("make it look good", "change the color", "more" with nothing changed).
- Typo "bumprs" is fixed by the app (bumpers only), though the same pipeline missed "rooof".
