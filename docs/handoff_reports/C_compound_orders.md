# WP C - Compound design orders in the offline designer (2026-10-03)

Lane: `js/spb-pro-design.js`, `_easy_claude_work/design_compound_*`, `_easy_claude_work/pw/wpc_*`, this report.
Restarted once (machine reboot ~17:09Z cut the first run before anything was written); resumed from step 1.

## Step 1 - map of js/spb-pro-design.js (540 lines) + why the four failures happen  [DONE]

The designer is a set of PURE parsers; the dispatcher that decides which one runs lives in `js/spb-pro-ai.js` (read-only for me):
`offlineAsk` (ai.js ~1436) -> `editPlan` (SpbProEdit, other lane) FIRST -> `advisorIntent` -> `offlineAskCore` (~1514):
refine -> offlineIdeas -> cannot -> layerVis -> numbers fix -> editPlan -> **D.lookRequest** -> **D.offlineSpec** -> **D.offlinePart** -> **D.offlineElement** -> **D.offlinePlan**.
`offlineCanHandle` (~1236) sends the order to the paid AI (when a key is set) if words > 14 or >= 2 verbs.

Designer map (file:line):
- 14-61 colours: `COLOURS`, `parseColours` (colours in order, negation-aware), `ensureContrast`.
- 64-140 `PALETTES` (themes), 144-205 `ELEMENTS` (base / lower_band / pinstripe / twin_stripes / centre_stripe / bumpers / hood / roof ... each -> zone specs on NAMED parts), 225-228 graphic elements (`rays_graphic` = sunburst, `checker_graphic`, ... via SpbGraphics).
- 208-215 `PRESETS`, 229-241 `build(elements, palette, ctx)` -> `{zones, skipped}`; every zone is `{name, finish, color, region}` - **no pattern, spec_patterns or second_base is ever emitted** by build.
- 259-272 `SPEC_LOOKS` (word -> Foundation finish), 275-289 `offlineSpec` (spec-only, color "source").
- 292-319 `offlinePart` (colour per named part, ONE finish word for all), 329-361 `refine`, 363-402 `offlinePlan` (sentence -> preset + palette; finish word -> ctx.paint for ALL zones).
- 409-463 `offlineIdeas`; 467 `LOOK_CURATED` (look word -> zone {finish, pattern?}); 470-488 `lookRequest` -> ONE query string + ONE colour + ONE finish -> ai.js `offlineLookAsk` -> `resolveLook` (curated, else atlas name search) -> ONE zone per target.
- 490-519 `offlineElement` (one stripe element); 520-538 `describePlan`, `summarise`.
- Layers the designer can emit today: colour+finish zones on parts/bands, graphics (rays etc.), and (only via LOOK_CURATED) a paint `pattern`. Never `spec_patterns`, never `second_base`, never two layers of one order.

Why the known failures happen (measured with a node probe, palette with black/white/green on the car):
1. "matte black with orange pearl flakes": `SpbProEdit.plan` (edit.js, runs first) reads it as "recolour the BLACK on the car to orange metallic" (ops black=metallic+orange). With no black on the car it falls to `offlinePlan` (design.js:377 `cols>=2 && /with/` -> `retro_lower_band`): the orange becomes a lower BAND, the flakes are lost. "make it ..." variant: `lookRequest` (design.js:470) collapses it to ONE look "pearl flakes" on the whole body (one zone, the matte/black layer is lost).
2. "a sunburst": `lookRequest` -> query "sunburst" -> catalogue name search on FINISHES (ai.js resolveLook) - the designer's own `rays_graphic` (sunburst) element is never considered; no base.
3. "pearl then pink pearl": `lookRequest` strips colours and joins the rest -> query "pearl then pearl" (design.js:479): one garbage query, one zone; the second coat is lost.
4. "satin on the stripes": `SpbProEdit.plan` (stripes=satin) - an edit, handled outside the designer; the 10-02 failure was the AI tier ("why would you put satin on the stripes" = a QUESTION, critic undo) - not a designer path.
Root cause in one line: every designer entry point returns ONE layer (one finish, one colour, one look query); there is no stack plan, and the dispatcher order lets single-layer parsers (edit / look / plan) claim a compound sentence first.

## Step 2 - node test `_easy_claude_work/design_compound_test.js`  [DONE]
40 compound orders + 12 single-layer guards. Each order runs through the designer route in ai.js order (lookRequest -> offlineSpec -> offlinePart -> offlineElement -> offlinePlan) and the zones are reduced to a stack signature (kind bottom->top + finish/colour/spec/pattern/coat tags, nearest-named-colour compare). An EDIT-FIRST column flags orders `SpbProEdit.plan` claims before the designer runs (ai.js order).
Baseline (designer before the fix): **compound 0/40**, guards 12/12, 18/40 claimed first by SpbProEdit.plan (palette with black / yellow / white / red on the car). Failures seen: retro_lower_band / classic_stripes schemes (coat became a band), single `look=` zones ("pearl then pearl"), one-part zones (layers lost), and "none" (gloss red with a carbon fiber hood got NO offline answer).

## Step 3 - the fix: compound order -> stack plan -> zones  [DONE]
New in `js/spb-pro-design.js` (block "COMPOUND ORDERS", just above `describePlan`): `compoundPlan(text)` (exported) = `cpSeg` (split at with / then / and / plus / over / topped with; "... on a black car" = the base) -> layers -> `cpCompile` -> zones.
Stack rules implemented (all measured by the node test):
- Base = body zone `{everything, paintable}` with the buyer's finish + colour. No colour named -> `color:"source"` + the FOUNDATION finish of the sheen (f_pearl, f_soft_matte ...) so the paint stays.
- Spec texture words (flake / pearl flakes / glitter / holographic or chameleon flakes / brushed / engine-turned) -> `spec_patterns` (gold_flake, pearl_micro, holographic_flake, spec_chameleon_flake, brushed_linear_cool, guilloche_sunray) ON the zone of those pixels; a COLOURED texture ("orange pearl flakes") adds a coat `second_base {id: base::pearl | base::xirallic | base::metallic, color, strength 35-45}`. "pearl then pink pearl" / "black with red pearl" = a second coat (second_base) on the same zone. Zones never blend, so a spec layer is never a separate color-"source" zone over a painted one (T29).
- Part-bound layers -> own zone `region.part` (inherit base colour / finish when they name none; curated looks carbon / camo / hex ... bring their `pattern`; carbon adds spec_carbon_3k_fine). A bare "and hood" joins the previous part layer; "... then pink pearl over it on the hood" moves that coat to the hood.
- Stripes (twin / centre / pinstripe / lower band) via the existing ELEMENTS, then graphics (sunburst = rays_graphic, lightning, chevrons, speed lines, dots, waves, rings) via SpbGraphics - emitted LAST so they sit on top (add_zone puts each new zone at index 0 = wins overlaps; kit SCHEMA priority text confirms "LOWER position wins").
- Unknown leftover words -> SpbAIAtlas spec / pattern names (every word must match) else `null` (old single-layer path; never guessed). Guards: questions, ideas, themes / palettes, two bare colours ("black and gold"), numbers / sponsors, "the <colour> ..." targets (SpbProEdit's job), single-layer orders.
- Routing inside my lane: `lookRequest`, `offlineSpec`, `offlinePart`, `offlinePlan` return null for a compound order; `offlineElement` returns the stack `{kind:'compound', zones, parts, colour:'layered', label:'look (bottom to top: ...)'}` -> ai.js `offlineElementAsk` (re-plans after the car map loads, preflights `parts`, add_zone in order, one Undo).
Tests: compound **0/40 -> 40/40**, guards 12/12; `design_compound_regress.js` (562 phrases of the other harnesses, old vs new designer): 42 changed, all now compound stacks, **0 non-compound changes**.
NOT fixable in my lane: 18/40 orders are claimed by `SpbProEdit.plan` BEFORE the designer when the car already shows one of the colours (see "Needed change in spb-pro-ai.js" below).
Coat strength (measured in-app, eval/wpc_coat_sheet.png): a coloured flake / pearl coat is a UNIFORM `second_base` blend in the paint - orange pearl at 45% turned matte black into flat brown with no flakes. Now `cpFlakeStrength`: 15% on a dark base (it still reads black, warm cast), default-10 otherwise; the sparkle lives in the spec pattern. A paint `metal_flake` pattern was tried and rejected (regular diagonal dot rows at preview scale). Kit limitation: `second_base` has no pattern mask in the zone-kit SCHEMA (the zone state HAS `secondBasePattern`), so a real "orange flakes ONLY in the specks" needs that field exposed by the kit lane.

## Step 4 - in the real app (test server 59879, own Chrome CDP 9444, ARCA PSD)  [DONE]
Script `_easy_claude_work/pw/wpc_compound.py` (results `eval/wpc_results.jsonl`, run 1 in `wpc_results_run1.jsonl`; previews `eval/wpc_arca_<n>.png` real route, `..._direct.png` = the PROPOSED dispatcher order simulated on the test page by making SpbProEdit.plan and SpbProAdvisor.classify yield to `SpbProDesign.compoundPlan`). Sheet: `eval/wpc_arca_sheet.png` (looked at).
Real route today (other lanes are editing ai.js / advisor live, routing moved between my two runs):
| order | real route | zones (bottom -> top) with the proposed order |
|---|---|---|
| matte black with orange pearl flakes | SpbProEdit: "the black (9%) is now metallic, in orange" (WRONG) | Body base matte #111113 + spec pearl_micro + coat pearl #f26b21 15% (preview: near-black, warm cast, numbers untouched) |
| a sunburst | stack (run 1: SpbProEdit "the black is now 60s Sunburst") | Gold rays graphic on both sides (preview: gold rays at the front of the sides) |
| pearl then pink pearl | stack (run 1: SpbProEdit "black pearl, in pink") | Body base f_pearl colour source + coat pearl pink 45% (preview: own art with a pink cast, numbers clean) |
| gloss red with a carbon fiber hood | B2 advisor stack card: "2 layers in one zone on the hood" (red base lost from the body; proposal only) | Body gloss red; hood: carbon_fiber pattern 45% + spec_carbon_3k_fine, #0e0e12 (preview: red body, carbon hood) |
| black with a gold sunburst on the hood | stack | Body gloss black; gold rays on the hood (preview OK) |
| blue metallic with a matte black hood | stack | Body metallic blue; matte black hood (preview OK) |
Zones before every order: the clean ARCA ("Everything Else" only); each order was restored to clean before the next. Lower index wins: every part / graphic zone sits ABOVE the body base (index 0 vs 1), verified in the zone list.
Regressions: convo_test 52/52, tool_test 15/15, l6/adversarial 11 PASS / 0 FAIL, edit_corpus 409 phrases / 0 mismatches, design_compound_regress 562 phrases / 0 non-compound changes, t255_conversation arca (CDP 9444): all 11 turns answered as before (make the black matte ... undo).

## Needed change in js/spb-pro-ai.js (NOT applied: not my lane)
Without it 1 of the 6 orders (and 18/40 in the node set, on a car that already shows one of the colours) is claimed by SpbProEdit.plan, and B2's advisor stack claim can take declarative orders before the designer.
1. `offlineAsk`, first line of the body:
   `var cpx = (D && D.compoundPlan && !START_OVER_RE.test(text)) ? D.compoundPlan(text) : null;`
   then guard the edit block with `!cpx &&` (i.e. `if (E && !cpx && !START_OVER_RE.test(text) && ...)`) and the advisor line with `if (!cpx && !START_OVER_RE.test(text) && !(o && o.noAdvisor)) it = advisorIntent(text);`
2. `offlineAskCore`: `var edp = (D && D.compoundPlan && D.compoundPlan(text)) ? null : editPlan(text); if (edp) return offlineEditAsk(text, edp, o);`
3. `offlineCanHandle`: right after the editPlan line add `if (D.compoundPlan && D.compoundPlan(t)) return words <= 30;` (a 15-30 word stack order stays offline when offline-first is on).
4. Critic (AI tier; offline answers skip postCheck because `r.offline`): in `critic()` use `editMode = !!(epc && epc.kind === 'ops') && !(D && D.compoundPlan && D.compoundPlan(text));` and in `postCheck` drop coat colours from `want`: `var cpw = (D && D.compoundPlan) ? D.compoundPlan(text) : null; if (cpw) want = want.filter(function (c) { return !cpw.zones.some(function (z) { return z.second_base && D.nameColour(z.second_base.color) === c; }); });` plus one prompt line when `cpw`: `'\nThis request is a LAYER STACK (bottom to top: ' + cpw.desc.join(', then ') + '). A coloured flake / pearl coat is only a faint tint in the paint and speckle in the SPEC map: never report it as a missing colour.'` - today the critic reads "matte black with orange pearl flakes" as an EDIT of the black (editMode) and demands >=1.2% visible orange, so it undoes a correct stack.
Boundary to settle with B2 (advisor stack planner, same day): B2 `stackClaim` claims verbless stack wishes as PROPOSALS; the designer APPLIES the same sentences. Suggest: B2 yields when `SpbProDesign.compoundPlan(raw)` is non-null unless the sentence is a question / "ideas" ask (`it.kind` from an explicit what/which/suggest), or the designer applies and the advisor offers the alternatives as a follow-up.

## Bookkeeping
`node --check` OK; scan_ctrl 0 control chars; `?v=` token `spb-pro-design-20261005a` -> `...20261003wpc` -> `...20261003wpc2`; sync --manifest sync_mine.json --write then --check: no drift.
Not verified: iRacing spec look of the flake / pearl spec patterns (the preview shows paint only); flat (non-PSD) cars; the paid AI tier; graphics on cars whose sides have no learned roof-line / front (they are skipped with a reason); "tiger stripes" style looks containing the word stripes (the stripe element wins).
