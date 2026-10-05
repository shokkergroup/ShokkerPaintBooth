# Owner test plan — finish advisor, morning of 2026-10-02

Everything below was built and measured overnight; none of it has been judged by YOU yet. This is the fastest way to find out what is wrong. Nothing needs a rebuild except the MCP part (last section).

**Before you start:** Ctrl+R in the app (loads the new JS, incl. the 1.4 MB latent-semantic file that loads in the background after the cards). One live-server restart is still pending for earlier server-side changes.

## 1. The in-app copilot (Pro > Shokker AI), offline brain only (the default)
Open a car with your scheme loaded, then type these one after another (they depend on each other on purpose):

| # | Type this | What you should see |
|---|---|---|
| 1 | `what finish should I put on the stripes` | 3-5 cards for the stripes, a reason each |
| 2 | `show me more` | the next page, no repeats |
| 3 | `tell me about the second one` | the card's look, how loud / busy it is, cautions |
| 4 | `I like the second one but calmer` | similar finishes, moved calmer; the answer says what it changed |
| 5 | `why did you pick that` | an honest reason from the card, or "no real reason against it" |
| 6 | `no glitter, I hate that` | nothing with glitter from now on, for the whole conversation |
| 7 | `actually I do want glitter on the hood, show me glitter finishes` | the dislike is lifted (you can change your mind without starting over) |
| 8 | `darker` | re-finds close to what you were looking at, moved darker |
| 9 | `what goes with chrome` | accents that read next to chrome |
| 10 | `what texture would look good on the body` | a TEXTURE list (spec patterns change only the shine) |
| 11 | `I want the numbers plain but the stripes to really pop` | "Two parts, two answers" (or, when the car has no numbers zone, it says the numbers stay as drawn); **Use** applies to that part only |
| 12 | `what could make it shinier but keep my colours` | shine-only finishes (the paint stays identical) |
| 13 | `give me a premium kit` | a whole-car kit incl. a spec texture on the hood |
| 14 | `anything but chrome on the wheels` | no chrome in the list |
| 15 | `can we kill the shine? it looks like plastic` | satin / matte / eggshell, not glossy ones |
| 16 | `what finish for the front bumper only` | the card says "Use on the front bumper" (the rear one is not touched) |
| 17 | select a zone in the zone list, then `what finish for the selected zone` | "Use on the selected zone" edits THAT zone (never silently the body) |

Things I most want a verdict on: (a) are the cards the finishes YOU would have picked? (b) did any answer feel dumb or off-topic? (c) any card that is obviously a bad thumbnail / description (tell me the name; I re-write cards from QA).

## 2. Things that should NOT hijack
These are not finish questions and must go to the normal designer / support, not to a finish list:
`make the stripes chrome`, `why is my matte TGA turning black`, `where do I choose 2048 export`, `hello`, `abstract chaos on the rear wing, no pattern just vibes`.

## 3. Typos and painter words
`somthing metalic for the hood`, `a deep candy red that glows`, `quiet stealth wrap look`, `showroom polished look for the hood`, `a car that looks just waxed`. Misspelled words should still find things.

## 4. Undo = a vote
Apply a suggestion, press Undo, ask for more: that finish must not come back in the same conversation.

## 5. Adding a texture keeps your other textures
If a zone already has spec textures with your own opacity / scale / rotation / channels, accept a texture card: the old ones keep their settings and the new one is appended.

## 6. With an AI model on (DeepSeek v4.1 Flash recommended)
Settings gear > turn "offline first" off for one test and ask the same questions as #1. The model should call the finish tool itself (you will see it in the AI log) and answer in 4-5 seconds for under a cent. Known weakness (not the advisor): compound design orders like "matte black with orange pearl flakes" or "guitar sunburst" still fail in the designer / critic.

## 7. MCP (after I rebuild the .mcpb — I have NOT yet)
`python scripts/build_mcpb.py`, install, then in Claude: "design me a livery ... use the Shokker finish tools". The first call it makes should be `spb_suggest_finishes` (new `like` / `mods` / `leave_out` fields, `ask` = the whole sentence, `rejected_mods`, `capability_note`). The spec-only guidance changed: edit the zones that already cover a part, never add a NEW zone with color "source" on a painted part.

## 8. Car learning (the RAM truck)
Needs ONE live-server restart (new `/api/ai/learned-cars` route) + Ctrl+R. Load any car the library does not know (your RAM works), ask "what finish should I put on the hood" and press Use: you should get a picture with dashed labelled boxes ("its layout is NN% the same as the ... template") and Yes / No - never "I do not know where that part is". Yes applies it and remembers the car; reload the same paint and ask again: it goes straight through. No lets you draw the parts. "make the hood bright red and the roof bright blue" must give each part its own colour.
Reality check, please: the hood box on a truck whose hood is covered by artwork may show no visible change (the zone only repaints body-paint layers).

## 9. The app recognises cars from a finished paint (new)
Ctrl+R, then load a normal driver paint (a TGA you did not make from a template) of any car in your iRacing folders. Ask for "the hood": if the car is one the app has learned (ARCA / Late Model / Super Late Model / Monte Carlo / Fusion / Street Stock / Dirt Late Model ...) it should know the parts, or show the dashed-box picture saying "the panel outlines in your paint look like the ... sheet" (Yes remembers it). The Dirt Late Model used to be skipped entirely; it is recognised now. For a car with no library entry (dirt sprint, modifieds): teach the parts once on any paint; a different paint of that car should then be known.
Honest numbers: right car family 95.3% on held-out paints; 10% of cars the app has never seen may get a (wrong) proposal - answer No and teach it.

## 10. "Make the black matte": change what is already on the car (new)
Ctrl+R, load any finished livery (try the ARCA, a Late Model, a truck), open the AI copilot. The chips at the top now come from THIS car's colours ("What's on my car?", "Make the black matte" ...). Try, in plain words, with no AI key:
- "what colours do I have" - it names the colours the paint really has with their share.
- "make the black matte", "make the yellow powder coat looking", "make the white pearl", "make all the red chrome", "make it look like plasti dip", "make the sponsors matte". A look alone changes ONLY the shine (check Shine (spec) tab; the paint colours do not move).
- "make the numbers purple and metallic", "make the numbers gold chrome", "make the yellow purple", "make the red darker", "make the black glossier and the white duller".
- Two jobs in one sentence: "make the black satin and the yellow powder coat looking". Say the same colour twice ("make the white purple", then "make the white glossier"): it edits its own zone, the purple stays.
- Ask for a colour that is not there ("make the pink matte") or "make the stripes chrome" on a car with several accent colours: it asks, with tappable answers, instead of guessing.
With the AI on: the same sentences go through `describe_paint` + `refinish` (cost ~$0.001-0.003 each on DeepSeek v4.1 Flash). Through MCP (after the `.mcpb` rebuild): `spb_describe_paint`, `spb_refinish`.
More to try (2026-10-03): "make the black matte but leave the numbers alone", "make it a bit more" / "less", "do the same for the roof", "put the black back", "show me options for the white", "make the red #1a8cff".
**A paint with NO layers (a plain car_<id>.tga):** say "make the numbers purple". The helper shows what it found tinted (numbers pink, sponsors blue, stripes yellow) and ASKS. It is surest on truck sheets; on other cars it is often wrong, so check the picture. Buttons: Yes / No, I will show you (drag a box around ONE number; its colours are used) / There are none on this paint (iRacing stamps the number itself on many paints, so there may be nothing drawn). "those are not the numbers" switches my last change off and asks again. Details and the honest numbers: `docs/ELEMENT_FINDER.md`.
With Claude through MCP (after the `.mcpb` rebuild and a live-server restart): `spb_look_at_paint` (the flat paint with a 0.1 ruler + the app's guess) then `spb_mark_elements` with boxes it reads off the picture, then `spb_refinish`.
Honest limits: a recolour is an exact-colour region (fringes of the old colour can remain on very fine glyphs).

## Open items that are YOURS to decide (not fixed overnight)
1. **20 finishes named "R1 REJECTED — ..." / "R3 DEV"** are still in the picker / `/api/finish-data`. The advisor, the ranker and the atlas search now hide them; decide whether they ship at all.
2. **Engine semantics:** `color:"source"` means the ORIGINAL template art, not the scheme composed from lower zones (found by Codex L7 on a real ARCA scheme). Guidance now avoids the trap; the engine behaviour and the "composer stays disabled after MCP calls" bug are in the shared MCP lane (see the wiki Known Trouble Spots).
3. **Finish authoring worklist:** `_codex_work/finish_intel/l5_gaps/gap_report.md` = 52 clusters of asks the catalogue answers poorly (9 are conditional authoring leads: G01 sunburst-on-wood-grain, G02 charred oak barrel, G03 honey oak, G06 liquid-metal drips, G07 watch-dial sunburst / guilloche, G08 lake-ice fracture, G11 frosted glass banner, G12 sun-dried asphalt, G13 chalky paper label). Briefs only: authoring stays under the Finish Law.

## Where to look if something is off
- What the advisor classified and why: browser console, `SpbProAdvisor.classify("your text")`.
- Overnight log with every measurement: `_easy_claude_work/OVERNIGHT_LOG.md`.
- Honest numbers: truth-set hit rate 57.5% (was 30%; the same asks through the AI tool: 54.5%, was 36.5%), picture-judged gold score 0.88 (was 0.76), scenario benchmark 1.20 vs the old hand-curated slots 1.13 (second held-out set of flavours: 1.11 vs 1.16; third, never-tuned set: 1.03 vs 0.90), finish-vs-other routing precision 98% / recall 97% on held-out messages.
