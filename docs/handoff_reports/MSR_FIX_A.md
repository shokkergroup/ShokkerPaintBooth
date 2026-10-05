# MSR-FIX-A - stack planner / pairing / adjust fixes for the MAD SCIENTIST RUN misses (2026-10-03)

Lane: `js/spb-pro-advisor.js` (B2 STACK PLANNER section), `js/spb-pro-rank.js`, `_easy_claude_work/stack_test.js`, `_easy_claude_work/eval/fixa_*`. Patch scripts `_easy_claude_work/eval/fixa_patch*.py`; pre-run copies `eval/fixa_bak_advisor.0.js`, `fixa_bak_rank.0.js`, `fixa_bak_stack_test.0.js`.

## Method
- `scripts/ai_atlas/intricate_run.js` was broken by a live MSR-RUN edit at 15:38 (a literal newline inside `split('\n')`), so I score through a private copy `eval/fixa_run.js` (regenerated from the runner by `fixa_mkrun.py` every gate; ADV/RNK env vars let the same harness run the PRE-RUN advisor as a control).
- Gate battery `eval/fixa_gates.sh <n>`: node --check, stack_test / convo_test / tool_test, adv_fp over all 11 `*prompts*.txt` (284 prompts, claim list diffed vs `eval/fixa_fp_before.txt`), B1 200 (`intricate_fixa_<n>`) + the same 200 through the pre-run advisor (`intricate_fixa_ctl<n>`, because MSR-FIX-B edits lexicon/cards files concurrently and moves the numbers under me), and the full `mad_asks.jsonl` through both (`fixa_mad<n>` vs `fixa_madctl<n>`, per-ask flips in `eval/fixa_madchg<n>.txt`).
- Misses were grouped from my own scoring of `mad_asks.jsonl` (same asks and same scorer as `mad_misses.jsonl`, but current).
- Start: B1 composite any 0.780 / offline 0.534 / tool 0.772 (`fixa_0`); mad asks 377/610 failing (pre-run advisor).

## Fixes (newest last)

### Fix 1 - layer structure of the sentence (stackParse) [patch1, 1b, 2]
Causes: (a) "X **on a satin black car**" was never split, so "tiger stripes in orange on a satin black car", "leopard spots on a gloss gold body", "chrome splatter on a matte pink car" were ONE clause and returned no stack; (b) "leopard spots" / "snake scales" counted as TWO concepts, so the first became a base LOOK and the generic noun the pattern (leopard -> concentric dot rings); (c) the B2p2 rule "a colour + a concept in the first clause = the base" also fired for pattern concepts ("dragon scales in deep emerald green with a metallic shine" -> two bases, no stack); (d) "carbon but gold", "giraffe patches in brown and cream", "tiger stripes in orange": a layer + a colour with no base clause -> no stack; (e) "the pink is too much" named the base; (f) "what goes well over pearl white" must keep pearl white as the base.
Fix (`js/spb-pro-advisor.js`): `stOnSplit` (on + colour / look / car|body|base, never a part, never after work / go / suit / what), `stMergeGen` (generic marks noun merged into the animal concept), B2p2 restricted to base-look concepts or an explicit body word, colour from a layer clause leads the base when nothing else names one, a synthesized colour base under a layer (2+ clauses, or "X in <colour>"), complaint clauses are filler, the clause after "over" is the base when it names a colour / base look. New concepts: giraffe, barbed wire, sunburst, squiggle.
Numbers (gate 3/4): mad asks 377 -> 338 failing (42 flipped to PASS, 3 PASS->fail of which 2 came from a "pearl over camo = pearl base" rule I then REVERTED: the asks disagree 2:1 that pearl over X is a shine layer); B1 any 0.779 ctl -> 0.785 (offline 0.536 -> 0.543, tool 0.770 -> 0.779); ia128 "a diamond pattern on a blue car, not metallic" -> PASS, ia062 better; suites 64/64, 52/52, 15/15; adv_fp claim list identical (220/284).
Flipped (from `eval/fixa_madchg4.txt`, 42): M004 leopard spots on a gloss gold body, M007 tiger stripes in orange on a satin black car, M009 fish scale pattern in pearl white, M026 carbon but gold, M049 art deco gold sunburst on black, M084 bubblegum pink with barbed wire, M091 chrome splatter on a matte pink car, M180 blue scales over gloss black, M181 red weave pattern on a matte grey car, M182 gold hex on satin black, M319 jaguar rosettes on a satin yellow body, M322 mermaid scales in teal and purple with a pearl shimmer, M428 flake base in gold with a black hex pattern, M531 jungle fever, green with leopard spots and gold flake, M564 hammered gold with a camo of dark brown, M608 tye dye pink n purple swirls ... (M037 flipped only under the reverted pearl-base rule).

### Fix 2 - negated colours + tag-level negation in the ranker (avoidSet) [patch4]
Cause: `SpbProRank.avoidSet` knew shine / metal / sparkle / camo ... predicates but no COLOURS, so "camo without green", "candy paint but not red, not orange", "is there a snake pattern that is not green", "dark and moody but not black" kept items whose own name / tags / colour name say that colour; "no metallic" / "no pearl" missed items tagged metallic / pearl.
Fix (`js/spb-pro-rank.js` `avoidSet`): `AV_COL` + `avCol` (colour token in a short dislike phrase -> exclude items whose name / tags / colour name carry it; takes-colour items are judged by their name/tags only); metallic + pearl predicates also read tags + name. `isTrait` unchanged (negation routing in the advisor untouched).
Numbers (gate 5): mad 338 -> 331 failing; flipped M214, M233, M246, M282, M394 (M238 partial); B1 any 0.785 -> 0.788 (ia119 "a scales pattern but no gold and no yellow" -> PASS, ia127 must_not fixed); suites green; adv_fp identical.

### Ship ritual 1 (15:59)
scan_ctrl 0 control chars; tokens `spb-pro-advisor-20261003msrA1`, `spb-pro-rank-20261003msrA1`; sync --write then --check: no drift. stack_test +5 cases (MSR-FIX-A block) -> 69/69.

### Fix 3 - which layer a concept plays (stackParse roles) [patch5, 5b-5f]
Causes: (a) "hammered" could only be a spec, but the asks treat a hammered METAL as a paint pattern + its shine, and next to another pattern as the shine; (b) "dragon scales in carbon fiber" / "scales made of carbon": the material after in / made of was a layer, not the base; (c) "snow leopard look, grey and white with soft spots": the animal LOOK took the base although another clause names the base colours; (d) "pearl camo with holographic hex edges": two concept looks -> two bases (the second won); (e) "brushed titanium / brushed copper / pearl base in champagne + a pattern": the brushed / pearl base lost its own shine texture, and with no colour word "brushed titanium" became a spec with no base; (f) "a hammered sheen / hammered shine" was not a shine cue; (g) "keep my colours, hammered metal feel": a kept paint must not get a hammered paint pattern.
Fix (`js/spb-pro-advisor.js` `ST_C`, `ST_CUE_SPEC`, `stackParse`): hammered lanes 'ps'; material-base rule (`matB`); the itemish concept-look rule yields to a plain colour / look clause for pattern concepts; only the first concept look is the base, later ones become layers; a first-clause base-look-only concept ('sb': brushed / pearl / holo / weathered) is the base when nothing else names one (never before "over", which keeps the 2:1 "pearl over X = shine" reading); brushed / pearl base echo their own shine texture when a pattern is named and no shine; hammered next to another pattern -> shine, alone -> pattern + hammered shine; sheen / shine are spec cues; keep + hammered -> shine only.
Numbers (gate 10): mad 331 -> 316 failing (vs 376 control); flipped M005, M017, M028, M092, M195, M336, M398, M430, M433, M451, M515, M519, M549, M556, M565, M579 (M557 / M564 / M172 / M571 / M206 regressed on intermediate gates and were fixed before this gate: PASS-to-fail 0 vs control); B1 any 0.788 -> 0.790 (ia037 "copper metallic base with hammered pattern and flake spec" -> PASS); suites 69/69, 52/52, 15/15; adv_fp identical.

### Ship ritual 2 (16:19)
scan_ctrl 0; token `spb-pro-advisor-20261003msrA2` (rank unchanged since A1); sync --write then --check: no drift. stack_test +4 cases (fix 3) -> 73/73.

### Fix 4 - like-X-but-colour, negated colours, filler before the base [patch6]
Causes: (a) "like Ghost Camo but in hot pink" / "kinda like carbon but red" returned ONLY the original (an adjust-only plan: a hue slider on a multi-colour look reads poorly, K_app_controls R2); (b) "that Snake Skin 3 but in pink and not so brown": the NEGATED colour (brown) became the asked colour; (c) "expensive looking, not flashy, deep pearl with a fine weave": the base-look rule only looked at clause 0, so a leading mood clause pushed the pearl into a shine layer and the stack had no base.
Fix (`js/spb-pro-advisor.js`): `stackPlan` adds an alternative stack for like-X + colour = a base in the asked colour + the original's own pattern concept at 40% (only when the original's NAME carries a pattern concept), and drops duplicate like-only alternatives; clause colours ignore negated words (not / no / without / less ... X); the base-look rule applies to the first clause after filler.
Numbers (gate 11): mad 316 -> 311 failing (control 375); flipped M111, M261, M269, M460 (+ M553 from concurrent data); B1 any 0.790 -> 0.792 (ia105 better); suites 73/73, 52/52, 15/15; adv_fp identical.

### Fix 5 - typo'd layer words [patch7]
Cause: the planner parsed the raw sentence only, so "neon green marbel on black", "dragon scalez in gold on red", "gold carbn fibre but make it classy" found no concept and no stack (classify's own spellFix retry runs only when nothing claims the ask).
Fix (`js/spb-pro-advisor.js` `stackParseFix`, used by `stackPlan` and `stackClaim`): when the sentence parses to no stack, parse the advisor's own `spellFix()` of it (same snap-to-card-word the classifier uses); the reply keeps the buyer's words.
Numbers (gate 12): mad 311 -> 308 (control 375); flipped M389, M404, M406; B1 unchanged 0.792; suites green; adv_fp identical.
Handed to MSR-FIX-B (`eval/fix_handoff_to_B.jsonl`, 7 rows): <5-letter typos below spellFix (wit / blak / blu / tha), sidez / strips / thiner / hamerd, "army colours" as a colour.

### Fix 6 - size words + unnamed texture / "spec" layers [patch8, 8b, 8c]
Causes: (a) size words ("tiny", "big bold", "thin", "fine") only set the adjust scale; the candidates were picked ignoring their own feature size, so a "tiny" ask could get broad-featured items (the scorer and the eye read the item's own size); (b) an unnamed texture with the word "pattern" ("make the pattern coarser") competed evenly with spec items; (c) "a neon spec pattern" / "a chrome-ish spec pattern" / "a matte spec layer": the look word made the clause a SECOND base, so the stack lost its shine layer.
Fix (`js/spb-pro-advisor.js`): `stSizeWant` / `stSizeFit` (atlas fb micro / fine / medium / broad vs the asked size, +10..12 / -4..-10) in `stLane` and `stBases`; "pattern" in an unnamed texture clause prefers the pattern lane (+10); a later clause with the word spec / specular is a spec layer searched in the spec lane only.
Numbers (gate 15): mad 308 -> 305 (control 375; flipped M197, M505, M513); B1 any 0.792 -> **0.800** (offline 0.547 -> 0.557, tool 0.786 -> 0.793; ia024 + ia035 -> PASS, ia029 / ia044 / ia143 gain stack_shape); suites 73/73, 52/52, 15/15; adv_fp identical.

### Ship ritual 3 (16:40)
scan_ctrl 0; token `spb-pro-advisor-20261003msrA3`; sync --write then --check: no drift.

### Fix 7 - layer concepts the planner did not know [patch9]
Cause: the planner's own word table (`ST_C`) had no cracks, veins, butterfly or disco ball, so "orange and black with cracks", "dark rock with orange cracks", "frozen lake blue with cracks in the ice", "black gloss with green neon cracks" found no layer.
Fix (`js/spb-pro-advisor.js` `ST_C`): crack (crack / fracture / shatter, 'ps'), veins -> marble, butterfly / morpho, disco ball / mirror ball / sequins -> flake. Tried and REMOVED in the same gate round: glass ('sb') broke "the Truchet Glass pattern but on a matte body" (M274) and B1 ia093 "a subtle glass shimmer"; spider web made M505 worse.
Numbers (gate 17): mad 305 -> 299 (flipped M014, M058, M253, M480, M489, M536; 0 PASS->fail vs gate 15); B1 any 0.800 (unchanged); suites 73/73, 52/52, 15/15; adv_fp identical.

### Fix 8 - ask back on a self-contradicting wish [patch10]
Cause: "make it metal but also soft", "like a snake but not really" were answered with a confident list and no question (askback expected).
Fix (`js/spb-pro-advisor.js` `stAmbig` + `answer`): when a recommend / find / stack reply has no question and the wish joins two opposites (metal/shine vs soft/flat, bright vs dark, loud vs quiet) with but / also / yet / and and no layer word between them, or says "but not really", the reply keeps its options and adds ONE question naming the two readings. "metallic green with a matte top" (a real stack) is not asked.
Numbers (gate 18): mad 299 -> 297 (M298, M299); B1 any 0.800 unchanged; suites 73/73, 52/52, 15/15; adv_fp identical.

### Ship ritual 4 (16:50) + in-app check (16:52-16:55)
Token `msrA4`, sync clean. In-app (test server 59879, Chrome 9444, `eval/fixa_inapp.py`, token msrA5 confirmed loaded): "tiger stripes in orange on a satin black car" is answered by the DESIGNER's compound order BEFORE the advisor and reads tiger stripes as racing-stripe zones (satin black base + orange stripes on both sides, 3 changes). The advisor's own claim no longer yields to the designer for animal marks (patch11), but the in-app router is outside this lane -> handed to MSR-FIX-B. The follow-up "like Ghost Camo but in hot pink" was then taken by the edit-existing stripes helper ("Which colour are the stripes?"), also outside this lane. No kit was applied, no preview judged.

### Fix 9 - exact hex colours in a layered wish [patch12, 12b]
Cause: "#1b1b1b base, diamond plate pattern, frosted shine" - `colourOf` does not read hex, so the base clause was filler and the stack had no base; "flat #ff2d95 pink" used the generic pink, not the exact hex.
Fix (`js/spb-pro-advisor.js` `stHexCol`, `stBases`): a hex in a clause is the asked colour, exact (name from the colour word beside it or from its hue / lightness for the search), and an exact hex prefers bases that take the zone colour (+25 / -15).
Numbers (gate 20): mad 297 -> 296 (M165); B1 unchanged.

## Final (gate 21, 17:04)
- B1 composite any **0.780 -> 0.800** (offline 0.534 -> 0.557, tool 0.772 -> 0.793); vs the pre-run advisor on the same data files: 0.779 -> 0.800. Per class vs the pre-run advisor: no class down; vs `fixa_0` constraint -0.033 = ia166 "dont change my colours, just add a hex spec pattern", which fails identically with the pre-run advisor on today's data (concurrent lexicon / cards edits, not this lane).
- MAD asks (610 in `mad_asks.jsonl` at 17:04): failing **374 (pre-run advisor) -> 296**; 78 asks flipped to PASS, 0 PASS -> fail (`eval/fixa_madchg21.txt`).
- Suites: stack_test 75/75 (64 + 11 new MSR-FIX-A cases; no singles re-snapped), convo_test 52/52, tool_test 15/15, adv_fp claim list identical on all 284 prompts (220 claimed).
- Tokens: `spb-pro-advisor-20261003msrA6`, `spb-pro-rank-20261003msrA1`; scan_ctrl 0; sync --manifest sync_mine --write then --check: no drift.

## Declined on purpose (scorer expectation vs the right reading)
- "wet clear / wet gloss clear / wet shine" (10 asks: M158, M162, M170, M176, M434, M442, M559, M566 ...) expect a "glass" SPEC item; the catalogue's glass-tagged specs are shattered / faceted glass textures, which would add a visible pattern to a plain wet clear. The planner keeps a wet clear as a gloss constraint.
- "pearl over camo" (M037) wants a pearl BASE, while "pearl over matte ..." / "pearl over carbon ..." (M346, M596) want a pearl SHINE: kept the 2:1 reading.
- flames (~12 asks), spots / dalmatian / ladybug, ice: pattern_class words no catalogue item carries (scorer facets), so no planner change can pass them.

## Not verified
- Any applied render of the new stacks (no kit applied in-app; the only in-app ask went to the designer). Paid / MCP tiers. The B1 runner `scripts/ai_atlas/intricate_run.js` itself (broken by a live edit at 15:38; all numbers come from the private copy `eval/fixa_run.js`, identical except the split fix and ADV/RNK overrides). corpus_eval / fuzz_advisor were not rerun (not in the gate list).
- Note 17:05: `scripts/ai_atlas/intricate_run.js` passes node --check again (repaired by its owner); the numbers above still come from `eval/fixa_run.js`.
