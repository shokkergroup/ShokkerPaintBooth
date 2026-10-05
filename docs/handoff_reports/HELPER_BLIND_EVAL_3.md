# Helper blind eval, round 3 (fresh tester, offline routing + in-app conversations)

Tester could not write .md (environment); orchestrator compiled this from `_easy_claude_work/eval/blind3/judged3.jsonl` on 2026-10-04.

## Scores
| Class | n | Strict | Strict+acc | Wrong | Harmful |
|---|---|---|---|---|---|
| DO | 45 | 80% | 98% | 1 | 0 |
| PREFILL | 25 | 8% | 76% | 6 | 0 |
| ANSWER | 38 | 61% | 74% | 10 | 0 |
| ASK | 25 | 44% | 72% | 7 | 0 |
| ONLINE | 8 | 88% | 88% | 1 | 0 |
| Off-topic | 4 | 100% | 100% | 0 | 0 |
| Conversations (worst turn) | 15 | 7% | 40% | 7 | 2 |
| **All** | 160 | **53%** | **79%** | **32** | **2** |

Conversation turns separately (37): 38% strict, 70% strict+acceptable. Harmful confirmed in-app: `inapp/c14/s1_3_after.png` (bumper → front → white = WHOLE car white).

## Top patterns
1. Follow-ups lose context ("do the bumper too", "on the roof too", "ok do that on the hood") — re-ask for the look.
2. Vague asks applied car-wide instead of ASK ("fix the shiny", "make it pop").
3. Questions return the wrong card (layers → Save/Open; candy → colour slider; TP spec maps → .shokk; add a number → retro stripes).
4. Vague asks get unrelated UI cards ("change it up", "apply the finish", "put it on the middle").
5. Extra words break look lookup ("camo scheme", "chameleon colour shifting", "splatter").
6. Escalations dead-end ("darker" after "sides green" → 'app blocks edits to those side zones'; "smaller" on trunk camo).

## Every WRONG / HARMFUL item
- **W** `b3-042` — "lighten the whole car a bit" → 'lighten the whole car a bit' sent ONLINE; a basic relative edit
- **W** `b3-050` — "two tone paint split down the side" → 'I do not know a look called two tone split' with sides prefilled to unknown finish
- **W** `b3-059` — "diagonal stripes on the trunk" → diagonal stripes on trunk answered with the generic retro-stripes card, nothing about diagonal/trunk
- **W** `b3-061` — "splatter paint look all over" → splatter: unknown look, body prefilled to nothing useful
- **W** `b3-063` — "matte black car with red accents" → IN-APP screenshot: whole car turned maroon/dark red (matte black + red pearl coat); wanted black body with red accents. Route-only harness said recolour red->black
- **W** `b3-064` — "add a checkered flag border" → checkered flag border answered with retro-stripes card
- **W** `b3-069` — "pearlescent paint that shifts purple to green" → pearl purple->green read as recolour purple->green; ASK has zero chips and says no purple exists
- **W** `b3-073` — "what does the blue channel do in the spec map" → asked about the BLUE channel, got generic spec-map card (blue/clearcoat card exists)
- **W** `b3-080` — "how do layers work" → 'how do layers work' returned the Save/Open card
- **W** `b3-085` — "how do i make a snakeskin finish" → snakeskin how-to went ONLINE/no-article although snakeskin is known to the DO path
- **W** `b3-093` — "can i use my own logo" → 'can i use my own logo' got the Grab Object (numbers) card
- **W** `b3-097` — "how do i get a mirror finish" → 'mirror finish' got spec sculpt brushes card (chrome how-to exists)
- **W** `b3-098` — "where do the spec maps go for trading paints" → asked where spec maps go for Trading Paints, got the .shokk project card
- **W** `b3-099` — "what is candy paint" → 'what is candy paint' got the colour sliders card (candy card exists)
- **W** `b3-102` — "how do i add a number to my car" → 'how do i add a number' got the retro-stripes card
- **W** `b3-106` — "the sponsors are gone after i applied that finish" → complaint 'sponsors are gone' turned into a sponsors>finish prefill (could restyle sponsors); should be troubleshooting
- **W** `b3-107` — "why is my roof still yellow" → 'why is my roof still yellow' got the supported-cars blurb
- **W** `b3-118` — "the back" → 'the back' prefilled body>finish unknown; no question
- **W** `b3-120` — "change it up" → 'change it up' answered with zone-order card
- **W** `b3-123` — "make the front different" → 'front different' prefilled whole body with unknown finish
- **W** `b3-124` — "can you fix the shiny" → PROV: 'fix the shiny' guessed gloss on whole body (could be the wrong direction)
- **W** `b3-126` — "the stripe should be blue" → 'the stripe should be blue' answered with retro-stripes card; should ask which stripe
- **W** `b3-129` — "apply the finish" → 'apply the finish' got the More menu card
- **W** `b3-133` — "put it on the middle" → 'put it on the middle' got the canvas overlay card
- **W** `b3-140` — "generate a unicorn riding a rocket on the trunk" → unicorn+rocket drawing prefilled as 'what should I do with the trunk?' instead of admitting it cannot draw
- **W** `b3-146` — "paint the doors blue > lighter > do the bumper too" → T1 "paint the doors blue" S: doors/sides blue, sponsors intact (screenshot) || T2 "lighter" A: offline asked which colour; DeepSeek made both sides lighter (after a false "done" claim it corrected) || T3 "do the bumper too" W: "do the bumpe
- **H** `b3-148` — "roof black > make it matte > actually glossy" → T1 "roof black" S: roof black || T2 "make it matte" H: "make it matte" -> WHOLE car spec matte; "it" = roof lost || T3 "actually glossy" W: "actually glossy" -> whole car gloss; roof zone stays matte
- **W** `b3-149` — "spoiler orange > same for the rear bumper" → T1 "spoiler orange" A: honest: spoiler has no paintable pixels on this template || T2 "same for the rear bumper" W: "same for the rear bumper" -> asks what look; context lost
- **W** `b3-150` — "make the sides green > darker > a bit less" → T1 "make the sides green" S: sides green || T2 "darker" W: "darker" via DeepSeek refused: says the app blocks edits to side zones || T3 "a bit less" W: "a bit less" same refusal
- **W** `b3-151` — "how do i make chrome > ok do that on the hood" → T1 "how do i make chrome" A: chrome how-to arrives as a "directions for your car" card || T2 "ok do that on the hood" W: "ok do that on the hood" -> asks matte/satin/gloss; chrome forgotten
- **W** `b3-152` — "put camo on the trunk > smaller > undo" → T1 "put camo on the trunk" S: trunk camo || T2 "smaller" W: "smaller" -> DeepSeek: app blocked, nothing changed || T3 "undo" S: "undo" removed the camo zone
- **W** `b3-154` — "make the hood carbon fiber > on the roof too" → T1 "make the hood carbon fiber" S: hood carbon fibre || T2 "on the roof too" W: "on the roof too" -> asks matte/satin/gloss for roof; carbon forgotten
- **W** `b3-155` — "left side red > and the right > no wait make both blue" → T1 "left side red" S: left side red || T2 "and the right" A: "and the right" -> DeepSeek made right side red || T3 "no wait make both blue" W: "no wait make both blue" -> returned a suggestions card, nothing turned blue
- **H** `b3-159` — "paint the bumper > front > white" → T1 "paint the bumper" A: "paint the bumper" -> asks look for FRONT bumper only (did not ask front/rear) || T2 "front" A: "front" -> DeepSeek asks for a look || T3 "white" H: "white" -> WHOLE car body painted white (screenshot), not the bump
