# Offline helper BLIND eval (2026-10-04)

Blind test: 150 buyer-style inputs written with expectations BEFORE running; routed through the real offline route (OA.route on the ARCA yellow/white/black fixture, env_zero), judged strictly as a buyer. Files: _easy_claude_work/blind_corpus.json (inputs+expectations), _easy_claude_work/eval/blind/blind_results.jsonl (every judgement), blind_raw.jsonl (raw route output), run_blind.js (runner).

## Score

| Expected class | n | correct | acceptable | wrong | harmful | correct+acceptable |
|---|---|---|---|---|---|---|
| DO | 45 | 24 | 11 | 8 | 2 | 78% |
| PREFILL | 23 | 3 | 17 | 2 | 1 | 87% |
| ASK | 16 | 3 | 8 | 4 | 1 | 69% |
| ANSWER | 49 | 35 | 5 | 8 | 1 | 82% |
| ONLINE | 17 | 8 | 0 | 8 | 1 | 47% |
| **OVERALL** | 150 | 73 | 41 | 30 | 6 | **76.0%** (114/150) |

Strictly correct only: 48.7%. Off-topic (10, inside ONLINE): 7/10 handled correctly (7 declined/online with no change; 3 produced a bogus answer or finish search). Note: the helper has no explicit ASK class for vague input; it answers, prefills or goes online instead, which is why ASK scores lowest of the core classes.

## Wrong and harmful items

Harmful = would change or invite changing something not asked (numbers, sponsors, hood, white paint).

| id | exp>chose | buyer typed | helper replied (<=200 chars) | verdict / what a buyer expected |
|---|---|---|---|---|
| b001 | DO>PREFILL | make the car matte black | ["?>shine:matte!"] Pick WHAT it goes on. | **wrong**: dropped 'black'; only matte set, asks WHAT though buyer said the car (expected: body matte black; numbers/sponsors untouched) |
| b002 | DO>PREFILL | murdered out | ["?>finish:CX Midnight Chrome!"] For “murdered out” I picked CX Midnight Chrome (Stealth / murdered out); other Stealth / murdered out looks are below. Pick WHAT it goes on. | **wrong**: 'murdered out' got CX Midnight Chrome, a chrome look, not matte black (expected: body matte black; keep numbers/sponsors) |
| b012 | DO>PREFILL | fade the hood from yellow to black | ["part:hood>recolour:black","step1>finish:?!"] I do not know a look called “fade”. Pick one below (or search). | **wrong**: 'fade' not understood; hood becomes solid black, gradient lost (expected: hood gradient yellow->black) |
| b019 | DO>DO | paint the roof black and the hood white | ["part:roof>recolour:black"]  | **wrong**: second half silently dropped: only roof black, hood white lost (expected: 2 steps roof black, hood white) |
| b020 | DO>DO | make the body matte black, the hood carbon and the bumpers chrome | ["part:hood>recolour:black","step1>shine:matte"]  | **harmful**: closed steps recolour the hood black+matte; carbon hood/chrome bumpers dropped (expected: 3 steps) |
| b029 | DO>PREFILL | make the bumpers black | ["colour:black>?:?!"] Pick what to do, then the look. | **wrong**: treats 'black' as the thing to select (black paint) and asks what to do; bumpers ignored (expected: bumpers black) |
| b034 | DO>PREFILL | paint the car white | ["colour:white>?:?!"] Pick what to do, then the look. | **wrong**: 'paint the car white' parsed as select the white paint; asks what to do (expected: body white) |
| b039 | DO>PREFILL | keep the sponsors but change everything else to red | ["sponsors>finish:?!","body>recolour:red","step2>finish:?!"] I do not know a look called “keep”. Pick one below (or search). / I do not know a look called “else”. Pick one below (or search). | **harmful**: sponsors finish step proposed though buyer said keep the sponsors (expected: body red, sponsors untouched) |
| b043 | DO>PREFILL | mak the car blak | ["colour:black>?:?!"] Pick what to do, then the look. | **wrong**: typo 'blak' parsed black as the target colour; car not painted black (expected: typo: body black) |
| b045 | DO>DO | make the right side blue and the left side red | ["part:right side>recolour:blue"]  | **wrong**: only right side blue; left side red dropped (expected: 2 steps sides) |
| b051 | PREFILL>ONLINE | put a stripe down the middle |  text="put a stripe down the middle" | **wrong**: plain stripe request handed to online AI; offline should set up a stripe (expected: stripe: pick colour/width) |
| b052 | PREFILL>DO | racing stripes | ["tg>finish:Matte"] For “racing” I picked Matte (Racing); other Racing looks are below. | **harmful**: closed step puts Matte finish on stripes; no stripes drawn (expected: stripes: pick colours) |
| b066 | PREFILL>ONLINE | fade the rear |  text="fade the rear" | **wrong**: 'fade the rear' sent to online; offline gradient/ask expected (expected: fade: ask to what colour) |
| b069 | ASK>ANSWER | change the color | When a zone seems to do nothing, check in this order: is it muted, does it have a colour and a finish, does a zone above it cover the same pixels, is it limited to a hidden layer, and is the preview s | **wrong**: 'change the color' answered with the zone-does-nothing troubleshooting article; should ask which colour (expected: which colour/what part) |
| b071 | ASK>ANSWER | fix it | Change one thing at a time, keep the project, and send the real settings rather than a description. A fix starts from your actual file. | **wrong**: 'fix it' answered with problem-reporting article; should ask what (expected: what to fix) |
| b074 | ASK>PREFILL | a little less saturated | ["?>finish:Event Horizon!"] For “little” I picked Event Horizon (Little); other Little looks are below. Pick WHAT it goes on. | **wrong**: 'a little less saturated' matched the word 'little' and offered Event Horizon finish (expected: what) |
| b079 | ASK>ANSWER | get rid of the sponsors | Switch Training Wheels off in Options, or finish the Core Loop and accept the offer to turn it off. | **wrong**: 'get rid of the sponsors' answered with Training Wheels article; unrelated (expected: confirm before touching sponsors) |
| b080 | ASK>PREFILL | dont touch the numbers | ["numbers>?:?!"] Pick what to do, then the look. | **harmful**: numbers step opened though buyer said do not touch the numbers (expected: no action; ask what to change) |
| b085 | ANSWER>ANSWER | how do i add a zone | A zone is two things together: which pixels of your paint it covers, and what look those pixels get. Zones are how you decide what your car looks like. | **wrong**: 'how do i add a zone' answered with what a zone is, not the steps (expected: answer from zones.add_pick_colour) |
| b089 | ANSWER>ANSWER | how do i render | A normal render takes seconds to about a minute. If RENDER will not start, the message names the first thing missing; if it fails, think too many zones, a busy engine or a file held by another program | **wrong**: 'how do i render' answered with render-slow/fails text, not the Render button (expected: answer from preview_render.render_button) |
| b092 | ANSWER>PREFILL | ctrl r does nothing in iracing | ["?>finish:Gloss!"] For “nothing” I picked Gloss (Nothing); other Nothing looks are below. Pick WHAT it goes on. | **wrong**: 'ctrl r does nothing in iracing' opened a finish step with 'Gloss (Nothing)' (expected: answer from preview_render.reload_in_iracing) |
| b104 | ANSWER>ANSWER | how do i update the app | If Shokker shows Server Failed, the paint engine could not start: the usual causes are antivirus software blocking it, a missing Microsoft Visual C++ Redistributable, or another program using its port | **wrong**: 'how do i update the app' answered with the Server Failed / won't start text, not the update banner (expected: answer from workflows.install_update) |
| b105 | ANSWER>ANSWER | what is astra | Use hue, saturation and brightness. A solid colour wipes the design out. | **wrong**: 'what is astra' shows a FAQ snippet about hue/saturation and solid colour, not what ASTRA is (expected: answer from finishes.astra) |
| b117 | ANSWER>ONLINE | how do i get rid of the car numbers |  text="how do i get rid of the car numbers" | **wrong**: app how-to ('how do i get rid of the car numbers') sent online; the number-modes article exists (expected: answer from preview_render.number_modes) |
| b121 | ANSWER>PREFILL | number missing | ["numbers>finish:?!"] I do not know a look called “missing”. Pick one below (or search). | **harmful**: 'number missing' opened a numbers finish step ('I do not know a look called missing') instead of the numbers-vanished help (expected: answer from support.numbers_vanished) |
| b127 | ANSWER>ONLINE | trading paints isnt using my paint |  text="trading paints isnt using my paint" | **wrong**: Trading Paints question sent online; the Trading Paints article exists (expected: answer from support.trading_paints) |
| b131 | ANSWER>PREFILL | car is too shiny in sim | ["?>shine:gloss!"] Pick WHAT it goes on. | **wrong**: 'too shiny' opened a GLOSS step, the opposite direction (expected: answer from support.flat_or_shiny) |
| b134 | ONLINE>PREFILL | put my face on the hood | ["part:hood>?:?!"] Pick what to do, then the look. | **wrong**: 'put my face on the hood' pretends to build: hood found, 'Pick what to do'; no honesty about custom art (expected: needs custom art; offer online) |
| b135 | ONLINE>DO | design a full livery for me, white with red and blue lightning bolts and my name in script | ["colour:white>recolour:red","step1>pattern:Lightning"] For “lightning bolts” I picked Lightning (Lightning / electric); other Lightning / electric looks are below. | **harmful**: full livery request applied closed steps: white recoloured RED plus Lightning pattern; script name and blue dropped (expected: full creative design) |
| b136 | ONLINE>PREFILL | make a logo for my team | ["sponsors>finish:?!"] I do not know a look called “team”. Pick one below (or search). | **wrong**: 'make a logo for my team' opens a sponsors finish step; cannot make logos, should say so (expected: logo creation) |
| b138 | ONLINE>PREFILL | make a realistic photo of a dragon on the side | ["?>pattern:Dragon Scale!"] For “dragon” I picked Dragon Scale (Dragon scales); other Dragon scales looks are below. Pick WHAT it goes on. | **wrong**: 'realistic photo of a dragon' gave Dragon Scale pattern, not an honest 'cannot' (expected: custom illustrated art) |
| b139 | ONLINE>PREFILL | can you draw my dog on the roof | ["part:roof>?:?!"] Pick what to do, then the look. | **wrong**: 'draw my dog on the roof' roof found, 'Pick what to do'; no honest 'cannot' (expected: custom art) |
| b140 | ONLINE>PREFILL | make it look like the 1969 daytona winner exactly | ["body>finish:?!"] I searched the catalogue for “1969 daytona winner exactly”: pick a look below (or search again). It goes on the body paint; your numbers and sponsors keep theirs. look=true | **wrong**: '1969 daytona winner exactly' ran a catalogue search for the sentence; no honest 'cannot' (expected: historical replica) |
| b146 | ONLINE>ANSWER | what is 15 times 12 | The Inspector lets you look at the spec channels one at a time and read exact values from any spot. | **wrong**: off-topic '15 times 12' answered with the Spec Inspector article (expected: off-topic) |
| b148 | ONLINE>PREFILL | my force feedback wheel is weak | ["tg>finish:?!"] I do not know a look called “force feedback weak”. Pick one below (or search). | **wrong**: off-topic 'force feedback wheel' opened a finish search 'force feedback weak' (expected: off-topic (hardware)) |
| b149 | ONLINE>ANSWER | what cars should i buy in iracing | The same licence window has a Buy License button. | **wrong**: off-topic 'what cars should i buy' answered with the Buy License button (expected: off-topic) |

## Top 5 failure patterns

1. **Compound requests silently drop clauses** (b019 roof black + hood white -> only roof; b045 two sides -> only right; b020 3 steps -> hood black+matte, carbon and chrome lost; b012 fade -> solid black; b039 keep sponsors -> sponsor step). Multi-step sentences are the most common real input and the failure is silent: the reply does not say what was left out.
2. **A colour word is read as the target, not the paint colour** (b029 make the bumpers black, b034 paint the car white, b043 typo mak the car blak; b001 make the car matte black loses black; b002 murdered out -> chrome). Plus parts such as bumpers are not resolved (b005, b029, b020).
3. **Single words hijack the finish search** (racing -> Matte, little -> Event Horizon, nothing -> Gloss, missing/team/force feedback weak -> This look is unknown). A stray noun becomes a closed or open finish step (b052, b074, b092, b121, b136, b148).
4. **Impossible, custom-art and off-topic asks are not declined honestly** (b134 face, b139 dog, b138 photo dragon, b140 1969 exact, b136 team logo build steps; b135 applies white->red; b146 15x12, b149 cars to buy, b148 FFB get app articles/steps). Only 7/10 off-topic inputs and 1 of 7 custom-art asks went online cleanly.
5. **Problems, negation and vague input route to the wrong article or step** (b121 number missing and b131 too shiny build steps instead of the support article; b080 dont touch the numbers opens a numbers step; b069 change the color -> zone_no_show; b071 fix it; b079 get rid of sponsors -> Training Wheels; app how-tos land on a sibling: b085 add zone, b089 render, b104 update, b105 astra; b117 and b127 are answerable but sent online).

Strengths: single-target recolours, whole-body/colour-pair changes, undo phrases, numbers/sponsors left alone on body changes (b042, b033), the no-blue-stripe reply (b072), and 35/49 ANSWER cases were exactly right (spec, zones, iRacing reload, licence, MCP, files).
