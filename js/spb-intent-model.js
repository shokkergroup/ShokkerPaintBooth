/* ============================================================================
   HELPER V3 S7 2026-10-06 (docs/handoff_reports/HELPER_ARCHITECTURE_V3.md 2.6, stage S7): DeepSeek becomes a FRAME-FILLER.
   The online model no longer drives ~30 change tools: it describes the buyer's turn as ONE intent frame (schema v1,
   js/spb-intent-frame.js) through a single tool, submit_frame, forced with tool_choice. The deterministic planner
   (js/spb-intent-plan.js) turns the frame into zone ops; js/spb-pro-ai.js applies them through applyQueue (one undo step),
   the verifier (S2/S3) measures them and the reporter writes the reply. Read-only lookups may run before the frame.
   V3 S6 2026-10-06: SPB_FRAME_MODE 'auto' (default; see mode()) / '1' always / '0' off (window var or localStorage). Was: default OFF
   until the bank A/B shows online >= offline on every class (HELPER_V3_STAGES.md "S7"). SPB_AI_FRAME = '0' also turns it off.
   Global: window.SpbIntentModel
     on()                            frameMode flag (default off)
     submitTool()                    the submit_frame tool {name, description, parameters, terminal}
     tools(all)                      submit_frame + the read-only lookups found in `all` (js/spb-pro-ai.js makeTools output)
     toolChoice(round, lookups)      'required' while lookups are allowed, then the forced {type:'function', function:{name:'submit_frame'}}
     SYSTEM                          the system prompt: schema + the doc's 2.8 examples + the planner's precedence rules + owner rules
     userMessage(state, text)        the user turn (STATE data + BUYER SAYS)
     fromCall(callOrCalls, env)      the model's tool call -> { ok, frame, repairs, errors } or { ok:false, ask:{q, chips:[]}, errors }
     resolveLooks(frame, find)       pattern concepts / unknown finish families -> catalogue ids with a find({query, type, limit}) function
     replyOf(plan)                   a plain reply from the planner's steps (the S3 reporter replaces it with measured text)
   V3 S7c 2026-10-07 (ONLINE FRAMES v2, HELPER_V3_STAGES.md "S7c online frames v2"; owner 10-07: "online AND offline helpers over 90%"):
     clean(text)  deterministic spelling pre-pass (OSA distance vs the app's colour / part / finish words, 0.06 ms/turn): "whitte" white,
                  "puple" purple, "doirs" doors, "rd" red. userMessage adds a READ AS line ONLY on turns with a fix (prompt rule 22);
                  the S6 guards + first-request repair read the said text AND the cleaned text, so a typo colour is no longer "never said".
     guards       lower-body portion -> the parts said / sides+bumpers; gradient between 2+ named parts -> those parts; follow-up ops on
                  parts nobody named this turn dropped; empty adjust -> relative from the sentence; "too shiny" w/o a finish -> ask.
     retryHint(fc, text, env) / betterFrame(fc2, fc) / clearRequest(text): ONE retry when a clear request came back ask/nothing
                  (never when an S6/S7b guard asked on purpose). 0 train turns trigger it today. Wiring = S6b hunk in spb-pro-ai.js frameTurn.
     Metric ($0 replay of stored model args, tier-1 grader): train 245 h7 -> 261 h4 /367; p1 223 h11 -> 233 h9 /352;
                  p2 (held-out, totals only) 232 h8 -> 236 h6; dev 70 h5 -> 69 h5 /110. SYSTEM 19,691 -> 19,890 chars.
                  Held back (staged in _easy_claude_work/eval/s7c/work.js, not live-verified: OpenRouter credits ran out): rules 21/21b CARRY,
                  rule 10 pattern colours, rule 20j "no chrome anywhere".
   ES5 only (old Electron). Codex-compatible: additions only, no existing name changes (HELPER_ARCHITECTURE_V3.md 4.1).
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var VERSION = '2026-10-07-s7c';
    var LOOKUPS = ['find_finishes', 'finish_details', 'suggest_finishes', 'describe_paint', 'get_help', 'spb_look_at_paint'];
    var CANON = ['hood', 'roof', 'trunk', 'spoiler', 'front bumper', 'rear bumper', 'left side', 'right side'];
    var F_ACTS = ['change', 'answer', 'list', 'ask_back', 'undo', 'redo', 'save', 'nothing'];
    var F_VERBS = ['recolour', 'refinish', 'restyle', 'outline', 'pinline', 'stripe', 'gradient', 'pattern', 'graphic', 'copy_look', 'adjust', 'retarget', 'hide', 'show'];
    var F_KINDS = ['body', 'part', 'layer', 'colour', 'element', 'object', 'zone', 'box', 'graphic'];

    function flag(name, dflt) {
        try { if (W[name] != null) return String(W[name]); } catch (e) {}
        try { if (W.localStorage) { var v = W.localStorage.getItem(name); if (v != null) return String(v); } } catch (e2) {}
        return dflt;
    }
    // V3 S6 2026-10-06 (S7b landing): SPB_FRAME_MODE 'auto' (DEFAULT) = the online frame runs when a key is set AND the offline reader is not confident (it asks, does nothing,
    // or falls back to the whole body; the offline helper hands those turns over); '1' = every change turn goes to the frame; '0' = off. No key = unchanged (offline only).
    function mode() { if (flag('SPB_AI_FRAME', '1') === '0') return '0'; var m = String(flag('SPB_FRAME_MODE', 'auto') || 'auto').toLowerCase(); return m === '1' || m === 'on' ? '1' : (m === '0' || m === 'off' ? '0' : 'auto'); }
    function on() { return mode() !== '0'; }
    function clone(o) { try { return o == null ? o : JSON.parse(JSON.stringify(o)); } catch (e) { return null; } }
    function arr(x) { return x == null ? [] : (Array.isArray(x) ? x : [x]); }
    function low(t) { return String(t == null ? '' : t).toLowerCase().trim(); }
    function uniq(a) { var o = []; arr(a).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }
    function lists() { var F = W.SpbIntentFrame; return { acts: (F && F.ACTS) || F_ACTS, verbs: (F && F.VERBS) || F_VERBS, kinds: (F && F.KINDS) || F_KINDS }; }

    // ------------------------------------------------------------------ the submit_frame tool (schema v1 of js/spb-intent-frame.js, no anyOf: Anthropic + DeepSeek safe)
    function schema() {
        var L = lists();
        var COL = { type: 'object', properties: { word: { type: 'string' }, hex: { type: 'string', description: '#rrggbb' } } };
        var TGT = { type: 'object', description: 'Target: what a change applies to.', properties: {
            kind: { type: 'string', enum: L.kinds },
            parts: { type: 'array', items: { type: 'string' }, description: 'car-map part names exactly as STATE.parts ("both sides" = two names)' },
            portion: { type: 'string', description: 'front half | rear half | lower third | upper half | top edge | ...' },
            layers: { type: 'array', items: { type: 'string' }, description: 'PSD layer names exactly as STATE.layers' },
            colour: COL, element: { type: 'string', enum: ['numbers', 'sponsors', 'stripes'] },
            object: { type: 'string', description: 'a thing that is NOT a part or layer (spray can, mirrors, skull): descriptor only' },
            graphic: { type: 'string', description: 'kind=graphic: the existing look to edit (carbon, camo, flames, stripe, checker, hex ...)' },
            between: { type: 'array', items: { type: 'object' }, description: 'pinline: the two Targets whose seam gets the line' },
            ref: { type: 'string', enum: ['last_change', 'last_target'] } } };
        var LOOK = { type: 'object', description: 'What it should become; leave out what does not change.', properties: {
            colour: COL, colours: { type: 'array', items: COL, description: 'several colours (multi stripes)' },
            gradient: { type: 'object', properties: { stops: { type: 'array', items: { type: 'string' }, description: 'colour words / #hex in order; "clear" = fades to the paint underneath' }, axis: { type: 'string', enum: ['front_to_rear', 'rear_to_front', 'top_to_bottom', 'bottom_to_top', 'radial'] } } },
            finish: { type: 'object', properties: { family: { type: 'string', description: 'chrome | satin chrome | metallic | pearl | candy | brushed | matte | satin | gloss | carbon | holo | flake | ...' }, key: { type: 'string', description: 'a catalogue key from find_finishes, only if you looked it up' }, keep_colour: { type: 'boolean', description: 'true = only the shine changes, colours stay' } } },
            pattern: { type: 'object', properties: { concept: { type: 'string' }, id: { type: 'string' }, style: { type: 'string' }, scale: { type: 'number' }, opacity: { type: 'number' } } },
            spec: { type: 'object', properties: { metal: { type: 'integer' }, rough: { type: 'integer' }, clearcoat: { type: 'integer' } } },
            scale: { type: 'number', description: 'texture scale: 1 = as is, 0.3 = crushed to 30%, 2 = twice as big' }, rotation: { type: 'number' },
            stroke: { type: 'object', properties: { width: { type: 'string', enum: ['hairline', 'thin', 'medium', 'thick'] }, px: { type: 'number' }, sides: { type: 'string', enum: ['both', 'inner', 'outer'] }, n: { type: 'integer' }, at: { type: 'string', description: 'beltline | top | bottom | middle' } } },
            layer: { type: 'object', properties: { visible: { type: 'boolean' }, opacity: { type: 'number' }, opacity_delta: { type: 'number' }, blend: { type: 'string' } } },
            accent: { type: 'boolean', description: 'an accent / trim with NO shape named: the app asks outline-or-band' } } };
        var OP = { type: 'object', properties: {
            verb: { type: 'string', enum: L.verbs }, target: TGT,
            except: { type: 'array', items: TGT, description: 'op-level keep ("everything except the roof")' },
            look: LOOK, source: TGT, copy: { type: 'array', items: { type: 'string', enum: ['colour', 'finish', 'spec', 'scale', 'pattern'] } },
            relative: { type: 'object', properties: { prop: { type: 'string', enum: ['width', 'scale', 'lightness', 'saturation', 'hue', 'gloss', 'metal', 'strength', 'stops'] }, dir: { type: 'integer', enum: [-1, 1] }, amount: { type: 'string', description: 'little | lot | half | double | back | a number' } } },
            ref: { type: 'object', properties: { to: { type: 'string', enum: ['last_change', 'last_target', 'opposite_side', 'turn'] }, turn: { type: 'integer' } } } }, required: ['verb'] };
        return { type: 'object', properties: {
            v: { type: 'integer', enum: [1] }, act: { type: 'string', enum: L.acts },
            ops: { type: 'array', items: OP, description: 'act=change: one op per clause, in the order said' },
            question: { type: 'object', properties: { topic: { type: 'string' }, text: { type: 'string' } } },
            list: { type: 'object', properties: { of: { type: 'string', enum: ['finishes', 'colours', 'patterns'] }, query: { type: 'string' } } },
            keep: { type: 'array', items: TGT, description: 'sentence-level keep clauses ("but leave the doors")' },
            decals: { type: 'string', enum: ['protect', 'include'] },
            missing: { type: 'array', items: { type: 'string', enum: ['target', 'colour', 'layer', 'finish', 'what'] } },
            alts: { type: 'array', items: { type: 'object', properties: { slot: { type: 'string' }, said: { type: 'string' }, maybe: { type: 'string' } } } },
            n: { type: 'integer', description: 'act=undo: how many changes' }, replace_last: { type: 'boolean', description: 'this request REPLACES the last change ("no, do X instead")' },
            confidence: { type: 'number' } }, required: ['v', 'act'] };
    }
    function submitTool() {
        return { name: 'submit_frame', terminal: true,
            description: 'Describe the buyer\'s turn as ONE intent frame. The app plans, checks and applies it (or answers / asks). Call it exactly once per turn.',
            parameters: { type: 'object', properties: { frame: schema() }, required: ['frame'] } };
    }
    function tools(all) { var out = [submitTool()]; arr(all).forEach(function (t) { if (t && LOOKUPS.indexOf(t.name) !== -1) out.push(t); }); return out; }
    function toolChoice(round, lookups) { return round < (lookups == null ? 0 : lookups) ? 'required' : { type: 'function', function: { name: 'submit_frame' } }; }

    // ------------------------------------------------------------------ the system prompt
    var SYSTEM = [
        'You are the request reader of Shokker Paint Booth (SPB), an app that paints iRacing cars. You NEVER paint and never reply in prose: every turn you call submit_frame ONCE with a frame that says exactly what the buyer asked. The app plans it, checks it on the car (pixels outside the target, decals touched) and applies it with one Undo, or answers / asks.',
        'The paint is one flat 2048x2048 sheet of the whole car. STATE (data) lists the car parts, the PSD layers (with their colours), the zones already on the car and convo.last_change (the change the app made last). Use ONLY part names from STATE.parts and layer names from STATE.layers, spelled exactly.',
        '',
        'FRAME: {v:1, act, ops:[{verb, target, except, look, source, copy, relative, ref}], keep, decals, missing, alts, question, list, n, replace_last, confidence}',
        'act: change = anything that alters the paint (also polite "can you make..."); answer = a question / how-to / why / opinion (question:{topic,text}, NO ops); list = "show me / what are my options" for finishes, colours or patterns (list:{of, query}); ask_back = you cannot tell what or where (fill missing); undo (n = how many, "undo everything" = 99) / redo; save; nothing = thanks / ok / greetings / no request.',
        'verb: recolour (new colour) | refinish (new finish / shine) | restyle (finish that brings its own look: carbon, candy red ...) | pattern | gradient (fade) | stripe (racing stripes, bands) | outline (line around a part / layer / element / zone edge) | pinline (thin line on the seam between two colours: target.between) | copy_look (target gets the look of source) | adjust (change an EXISTING thing or the last change) | retarget (the last change was put on the wrong place) | hide / show (layers) | graphic.',
        'target.kind: body (the whole car paint) | part (parts[], portion) | layer (layers[]) | colour (a colour region: colour{word,hex}, optionally inside layers[] or parts[]) | element (numbers | sponsors (= logos, decals) | stripes) | object (a thing that is not a part or a layer) | graphic (an existing look: graphic word, parts) | zone.',
        '',
        'RULES (the planner applies them; fill the frame so they can work):',
        '1. One op per clause, in the order said. "white body with a red pinstripe" = 2 ops.',
        '2. Numbers and sponsors are protected by default (decals:"protect"). decals:"include" ONLY when the buyer explicitly says the numbers / logos / decals should change too. When numbers or sponsors ARE the thing to change, target them (element) and keep decals:"protect".',
        '3. A named layer beats an object: "the yellow on the spray can in the Logos layer" = target {kind:colour, colour:yellow, layers:["Logos"], object:"spray can"}. A thing that is not a part or a layer with no layer named = {kind:object, object:"..."}: the app asks which layer. A door / fender / quarter panel is on a side: "left door" = parts ["left side"]. "the sides" = ["left side","right side"]. Wing / top wing = spoiler; splitter / front lip / air dam / nose = front bumper; diffuser = rear bumper; cab = roof + left side + right side. "the back" / "the front" / "the top" alone are ambiguous = missing ["target"]. A part not in STATE.parts (bed, mirrors, mirror caps on a car without them) = kind object.',
        '3b. NOT on the paint sheet (iRacing paints them elsewhere or not at all): wheels, rims, tyres / tires, windows, glass, window frames, lights, lenses, interior, helmet, suit, exhaust, roll cage = act answer, question {topic:"unpaintable", text}. Never an edit.',
        '3c. A colour as the target ("make the yellow purple", "the red parts") means that colour in the BODY PAINT. Never target a decal layer (Logos, Car_Decal, Pitbox Colors, Contingency Decals, Numbers) unless the buyer names that layer, the logos / sponsors or the numbers.',
        '4. keep = sentence-level keep clauses ("but leave the roof alone", "don\'t touch the hood"); except = the op-level "everything except X". Both are subtracted by the app.',
        '5. A finish with no colour named on a part / the body / a layer = finish {family, keep_colour:true} (only the shine changes: "make it shinier", "matte the roof", "chrome but keep the colours"). A colour word with a finish ("candy red", "gold chrome") = colour + finish with keep_colour:false. "shinier" / "more metallic" with nothing earlier = verb adjust, relative {prop:"gloss" or "metal", dir:1} on the target.',
        '6. SCALE words: "crushed", "crushed down", "crushed to 30%", "tighter", "finer", "smaller pattern" = SCALE smaller (look.scale 0.3 / relative {prop:"scale", dir:-1}); "bigger", "blown up", "larger" = scale up. "crushed" is NEVER a finish and never "brushed". On a look already on the car: verb adjust, target {kind:graphic, graphic:"<carbon|camo|checker|flames|...>", parts}, relative {prop:"scale", dir, amount}.',
        '7. ACCENT / TRIM rule (owner): "silver accent", "some trim", "gold accents" with NO shape named (no line, outline, stripe, band, edge) = verb recolour on the part with look {colour, accent:true} and NO stroke: the app asks the buyer outline-or-band EVERY time. Never guess the shape.',
        '8. Colours: always colour {word, hex} with a sensible hex. Neutral words get NEUTRAL hexes (R, G, B within 8 of each other): silver #c0c0c0, gunmetal #4a4d50, charcoal #3a3a3a, grey #808080. Gradient stops in order, "clear" = fades into the paint underneath; axis front_to_rear | rear_to_front | top_to_bottom | bottom_to_top | radial ("fade up from the bottom" = bottom_to_top).',
        '9. SPEC map (only when the buyer talks about metal / roughness / clearcoat or gives numbers): R = metallic 0-255, G = roughness (0 = mirror smooth, 255 = rough), B = clearcoat (0-15 = none, 16 = MAXIMUM gloss, higher = duller, 255 = dull). "full clearcoat" = clearcoat 16, never 255. look.spec {metal, rough, clearcoat}.',
        '10. Patterns: look.pattern {concept:"camo" | "carbon fiber" | "hex" | "checker" | "snakeskin" ...} (the app finds the catalogue id). Flames: verb graphic or pattern with look.pattern {concept:"flames", style:"hotrod | tribal | ghost | real fire"}.',
        '11. Lines: stroke.width thin | medium | thick (or px). Several stripe colours = look.colours[] in order. "a stripe at the beltline" = stroke.at "beltline".',
        '12. copy_look: "make X match Y", "same colour as Y", "copy the hood onto the roof" = verb copy_look, target X, source Y, copy ["colour"] when only the colour is meant. "swap the red and blue" = two recolour ops on colour targets.',
        '13. FOLLOW-UPS use STATE.convo.last_change: "same on the other side" = verb adjust, ref {to:"opposite_side"}; "thinner / thicker / bigger / smaller / brighter / darker / less red / more red / flip it / softer" = verb adjust, ref {to:"last_change"}, relative {prop:"width|scale|lightness|saturation|hue|stops", dir:-1|1, amount}; "make it white instead" = verb adjust, ref {to:"last_change"}, look {colour}; "matte it" after a change = adjust, ref last_change, look {finish:{family:"matte", keep_colour:true}}; "that\'s not the hood, it\'s the roof" / "put it on the roof instead" = verb retarget, ref {to:"last_change"}, target {kind:part, parts:["roof"]}; "and the trunk too" / "same on the hood" = verb adjust, ref {to:"last_change"}, target the new part (no look). "no, do X instead" (a new request replacing the last) = the new op + replace_last:true. "undo" / "go back" / "revert" = act undo.',
        '14. Layer settings: "hide the Logos layer" = verb hide, target {kind:layer, layers:["Logos"]}; opacity / blend mode = verb adjust, target layer, look.layer {opacity | opacity_delta | blend | visible}.',
        '15. missing: a slot the request needs but does not give ("make it shiny" / "paint it red" / "make it chrome" while STATE.convo.last_change is null = missing ["target"]; "make the roof" = missing ["colour"]; a colour region in several layers behind an object with no layer named = missing ["layer"]; "too shiny" / "too reflective" with no new finish named = missing ["finish"]). The app asks ONE question. Do not invent a target the buyer did not say ("it" is not the whole car).',
        '15b. ref points ONLY at changes from EARLIER turns, and only when STATE.convo.last_change is not null. Inside ONE sentence ("hood flat black and the roof same") repeat the look in the second op (or put both parts in one op); never ref there. A thing already in the artwork (a stripe in the Tape layer, a logo colour) is not "the last change": target it as a colour / layer / element.',
        '16. Vague taste ("make it look mean", "Gulf-ish", "like it\'s been through hell") = turn it into concrete ops (Gulf = light blue #6fb7e3 body + orange #ff7a00 stripe; "through hell" = a weathered / rust pattern + matte finish). Ask only when nothing can be inferred.',
        '17. alts: only a word that could really mean two DIFFERENT things goes in alts {slot, said, maybe}.',
        '18. A question never produces ops, even about a change ("how do I make it chrome?" = answer). A complaint about the last change with a fix in it ("too bright, tone it down", "darker") IS a change. A complaint that the app broke something or that the car looks wrong after a click ("you trashed my numbers", "I clicked something and now my car is weird", "I pressed undo and it is all gone") = answer (the app explains and offers Undo / Versions): undo only when the buyer asks to undo / go back.',
        '3d. Numbers / sponsors described INSIDE a whole-car look ("all black with white numbers", "white body, black numbers", "numbers white no change") are the artwork the buyer keeps: put them in keep, never in an op. Recolour or outline the numbers only when the numbers themselves are the request ("make the numbers white", "change the number colour", "outline the numbers").',
        '15c. "change the orange to white" / "the blue bit" when the last change had several colours = target kind colour (that colour), never ref last_change (that would repaint every zone of it).',
        '15d. Too vague to act on, so missing ["target"] or ["what"]: a bare colour or finish word with nothing earlier ("red", "chrome"); "make it <x>" / "make the car more <colour>" / "make it brighter" / "make the car brighter, it is too dark" with nothing earlier (brighter = lighter colour OR shinier: ask); flames or a theme ("like a banana", "mud on the bottom") with no part and no colours named.',
        '19b. "show me the roof as carbon and brushed metal" (two options to compare) = answer, question {topic:"compare"}. "no more shine than that" / "that is enough" = answer (keep as is).',
        '19c. A short follow-up that checks or questions the last change ("everything?", "verify", "is that right?", "did it work?") = answer. A correction that only says where NOT to ("not on the numbers", "not the logos") while numbers / logos are protected anyway = answer (the app confirms they were kept).',
        '19. A keep-only sentence with nothing to change ("hood stays black", "make sure the numbers do not get carbon", "never touch the Logos layer") = answer, question {topic:"keep"} (numbers and sponsors are already protected; the app confirms).',
        '20. S7b EXCEPT: "<look> everything / all / the whole car but|except|without|leave <X>" = ONE op on target body with except [X]. Whatever is named in a leave / keep / except / "stays" clause gets NO op of its own, even when the buyer says what colour it stays ("everything white except the hood, which stays red" = ONE op: white, except hood). A later "also leave the roof as it was" / "keep the nose too" = the SAME op again with ALL the excepts so far plus the new one, replace_last true (never an adjust that targets the excepted part).',
        '20b. S7b MATCH COLOUR: "same colour as the logo", "pull the blue from my logo", "sample the red from the Logos layer", "the trim teal like the logo" = take the EXACT hex that STATE.layers[].colours lists for that layer (the closest one to the colour word) and use it: verb recolour, look.colour {word, hex: that exact hex}, on the TARGET the buyer wants coloured (the body when none is named; "the trim" / "the splitter" = object or part as said). Never target the decal layer the colour was sampled from, never source {kind:"layer"}. A bare hex ("use #D71920", "make it #fff") = recolour with that exact hex on the last target or the body, never a decal layer.',
        '6b. SCALE of a look that is NOT in STATE.zones yet ("bump the carbon scale to 150% on the hood", "bigger camo on the roof") = a NEW op: verb pattern, look.pattern {concept} + look.scale (150% = 1.5, crushed to 30% = 0.3) on that part. Only a look that STATE.zones already lists gets an adjust with relative scale.',
        '15e. S7b "it" / "that" / "make it red" on a first request is fine when an EARLIER buyer turn already named the car ("make the car go fast", "my truck"): then it = the car (target body).',
        '20c. S7b IMPOSSIBLE = answer (question {topic:"impossible"}), never an edit: real 3D / raised bumps, dents, embossing, anything physical or moving (speed, sound, smell, "make it go fast"), engine / handling / lighting up for real. A look that only SHOWS (a bump-like pattern drawn flat) is still a pattern when the buyer names a pattern.',
        '20d. S7b GREETING WITH A WISH ("hello can you help me paint my car", "I need help with a paint") = ask_back, missing ["what"]. act nothing is ONLY for thanks / ok / bye / a bare hello with no wish.',
        '20e. S7b A whole-car taste that NAMES its colours or a known livery ("yellow and black", "orange n black halloween", "Gulf-ish", "Martini", "red white and blue") with no part named IS about the whole car: ops on target body (colour + stripes / finish). It is not missing a target. Stripes in such a look run down the centre line: target parts ["hood","roof","trunk"]. A LIKENESS with no colours named ("looks like a banana / a hornet", "like a unicorn threw up", "mud on the bottom") is too vague: act ask_back, missing ["what"] (rule 15d).',
        '20k. S7b EXISTING STRIPES: "stripes thinner / thicker / orange only / make the stripes red" after a theme or livery = verb adjust, target {kind:element, element:"stripes"} with the relative or colour. NEVER ref last_change there (the last change also painted the body; a ref would repaint it).',
        '20f. S7b EXISTING FLAMES: "make them blue flames", "now purple" after flames = verb pattern, look.pattern {concept:"flames"} + the new colour, on the same part, replace_last true (never an adjust with only a colour: the flames would lose their look). A gradient follow-up "fade to purple at the roof" = verb gradient on target part roof (a NEW op for that part), never adjust ref last_change.',
        '20h. S7b CONCRETE PATTERNS: look.pattern.concept is ALWAYS a drawable motif (camo, carbon fiber, hex, checker, snakeskin, flames, skulls, spider webs, bats, stars, lightning, tiger stripes ...), never a mood or theme word ("spooky", "mean", "retro"). A theme = colours + a concrete motif, or only colours / a finish when no motif is obvious ("halloween, orange and black" = body orange, black stripes or bats, matte).',
        '20i. S7b ONE OF SEVERAL: when the last change covered several parts and the buyer now addresses ONE of them ("make the hood a bit darker than the roof"), the op targets ONLY that part ({kind:part, parts:[that part]}), verb adjust + relative, NO ref (a ref would change them all). "the rear" = the rear bumper; "the back" alone stays ambiguous.',
        '20j. S7b "keep every colour, just make it shiny / glossy / ceramic" with nothing earlier = the WHOLE car: refinish, target body, finish {family, keep_colour:true}. Not a missing target. "all chrome to satin chrome" / "all the matte to gloss" (all <old look> to <new look>) is NOT the whole car: target {kind:colour, colour:{word:"chrome", hex:"#c0c0c0"}} = the parts that look like that now, finish keep_colour true.',
        '22. S7c TYPOS: buyers type fast. A "READ AS" line after BUYER SAYS is the same turn with the spelling fixed by the app ("whitte" = white, "doirs" = doors): read it. A misspelled colour, part or finish is never a reason to ask.',
        '20g. S7b KEEP ECHO: before you answer, list to yourself every part / layer / element the buyer wants LEFT ALONE and make sure none of them appears in any op target, any look or any ref. Numbers, sponsors, logos and the Logos / Car_Decal / Pitbox Colors layers are left alone unless named.',
        '',
        'EXAMPLES (buyer -> frame; T = target, L = look):',
        '"everything except the roof gets a pearl finish" -> {v:1, act:"change", ops:[{verb:"refinish", target:{kind:"body"}, except:[{kind:"part", parts:["roof"]}], look:{finish:{family:"pearl", keep_colour:true}}}]}',
        '"red pinstripe on the left door" -> {v:1, act:"change", ops:[{verb:"stripe", target:{kind:"part", parts:["left side"]}, look:{colour:{word:"red", hex:"#d01818"}, stroke:{width:"thin"}}}]}; then "same on the right" -> {v:1, act:"change", ops:[{verb:"adjust", ref:{to:"opposite_side"}}]}; then "change both to gold" -> {v:1, act:"change", ops:[{verb:"adjust", ref:{to:"last_change"}, target:{kind:"part", parts:["left side","right side"]}, look:{colour:{word:"gold", hex:"#d4af37"}}}]}',
        '"fine silver pinline between the red and white" -> {v:1, act:"change", ops:[{verb:"pinline", target:{kind:"colour", between:[{kind:"colour", colour:{word:"red", hex:"#d01818"}}, {kind:"colour", colour:{word:"white", hex:"#ffffff"}}]}, look:{colour:{word:"silver", hex:"#c0c0c0"}, finish:{family:"metallic"}, stroke:{width:"thin"}}}]}',
        '"outline the number panel in gold" -> {v:1, act:"change", ops:[{verb:"outline", target:{kind:"element", element:"numbers"}, look:{colour:{word:"gold", hex:"#d4af37"}, stroke:{width:"medium"}}}]}; then "thinner" -> {v:1, act:"change", ops:[{verb:"adjust", ref:{to:"last_change"}, relative:{prop:"width", dir:-1}}]}; then "make it white instead" -> {v:1, act:"change", ops:[{verb:"adjust", ref:{to:"last_change"}, look:{colour:{word:"white", hex:"#ffffff"}}}]}',
        '"orange hood stripe" -> {v:1, act:"change", ops:[{verb:"stripe", target:{kind:"part", parts:["hood"]}, look:{colour:{word:"orange", hex:"#ff7a00"}}}]}; then "thin black line each side of it" -> {v:1, act:"change", ops:[{verb:"outline", target:{kind:"zone"}, ref:{to:"last_change"}, look:{colour:{word:"black", hex:"#0a0a0a"}, stroke:{width:"thin", sides:"outer"}}}]}',
        '"In the Logos layer make the yellow on the spray can the same color and finish that\'s on the numbers - the purple with Saturday chrome crushed down" -> {v:1, act:"change", ops:[{verb:"copy_look", target:{kind:"colour", colour:{word:"yellow", hex:"#ffe100"}, layers:["Logos"], object:"spray can"}, source:{kind:"element", element:"numbers"}, copy:["colour","finish","spec","scale"]}]} ("crushed down" is a scale word, never a typo)',
        'the same with NO layer named -> {v:1, act:"change", ops:[{verb:"copy_look", target:{kind:"colour", colour:{word:"yellow", hex:"#ffe100"}, object:"spray can"}, source:{kind:"element", element:"numbers"}}], missing:["layer"]}',
        '"show me gold options" -> {v:1, act:"list", list:{of:"finishes", query:"gold"}}',
        'a gradient on the hood, then "flip it" -> {v:1, act:"change", ops:[{verb:"adjust", ref:{to:"last_change"}, relative:{prop:"stops", dir:-1}}]}; then "less red" -> {v:1, act:"change", ops:[{verb:"adjust", ref:{to:"last_change"}, target:{kind:"colour", colour:{word:"red", hex:"#d01818"}}, relative:{prop:"hue", dir:-1, amount:"little"}}]}',
        '"thats not the hood thats the roof" -> {v:1, act:"change", ops:[{verb:"retarget", ref:{to:"last_change"}, target:{kind:"part", parts:["roof"]}}]}',
        '"just a little on the hood" after a whole-car stealth black -> {v:1, act:"change", ops:[{verb:"refinish", target:{kind:"part", parts:["hood"]}, look:{finish:{family:"gloss", keep_colour:true}}}]} (additive: never undo a committed change unless retarget or undo)',
        '"silver accent on the spoiler" -> {v:1, act:"change", ops:[{verb:"recolour", target:{kind:"part", parts:["spoiler"]}, look:{colour:{word:"silver", hex:"#c0c0c0"}, accent:true}}]}',
        '"make the carbon on the hood crushed to 40%" -> {v:1, act:"change", ops:[{verb:"adjust", target:{kind:"graphic", graphic:"carbon", parts:["hood"]}, look:{scale:0.4}}]}',
        '"how do I export to iRacing?" -> {v:1, act:"answer", question:{topic:"export", text:"how do I export to iRacing?"}}',
        '"thanks!" -> {v:1, act:"nothing"}'
    ].join('\n');
    // ------------------------------------------------------------------ S7c 2026-10-07: deterministic spelling pre-pass (typo colours / parts / finishes: "whitte", "puple", "rd", "doirs", "gkoss")
    // Edit distance (OSA) against the app's own vocabulary: the planner's named colours + car-part words + finish / pattern words. Conservative: same first letter
    // (or the first two letters swapped), distance 1 for 4-6 letters, <= 2 from 7 letters, one unique best match, never a word on the STOP list (real English words
    // one edit away from a vocab word: back/black, hold/hood, glass/gloss, crushed is a SCALE word ...). The model gets the ORIGINAL text plus a "READ AS" line; the
    // fromCall guards read both, so a typo colour no longer trips "colour never said" (S6 d) and "layr" still names a layer (S6 b).
    var VOC_COL = ['red', 'white', 'black', 'blue', 'navy', 'green', 'yellow', 'orange', 'purple', 'pink', 'gold', 'silver', 'grey', 'gray', 'gunmetal', 'bronze', 'copper', 'brown', 'teal', 'cyan', 'magenta', 'maroon', 'charcoal', 'cream', 'violet', 'turquoise', 'burgundy', 'crimson', 'scarlet', 'beige', 'ivory', 'lavender', 'indigo', 'olive', 'khaki', 'coral', 'salmon', 'amber', 'lime', 'neon', 'dark', 'darker', 'light', 'lighter', 'bright', 'brighter', 'colour', 'color', 'colours', 'colors'];
    var VOC_PART = ['hood', 'roof', 'trunk', 'spoiler', 'bumper', 'bumpers', 'door', 'doors', 'side', 'sides', 'fender', 'fenders', 'quarter', 'panel', 'panels', 'front', 'rear', 'left', 'right', 'whole', 'body', 'cars', 'truck', 'bonnet', 'wing', 'wings', 'splitter', 'nose', 'tailgate', 'rocker', 'rockers', 'lower', 'upper', 'bottom', 'mirror', 'mirrors', 'number', 'numbers', 'logo', 'logos', 'sponsor', 'sponsors', 'decal', 'decals', 'layer', 'layers', 'stripe', 'stripes', 'everything', 'except', 'without', 'instead', 'both'];
    var VOC_FIN = ['chrome', 'matte', 'metallic', 'metal', 'pearl', 'pearlescent', 'candy', 'satin', 'gloss', 'glossy', 'brushed', 'steel', 'carbon', 'fiber', 'fibre', 'flake', 'holo', 'holographic', 'primer', 'shiny', 'shinier', 'clearcoat', 'reflective', 'iridescent', 'chameleon', 'camo', 'checker', 'checkered', 'checkers', 'flames', 'gradient', 'pinstripe', 'pinline', 'outline', 'tribal', 'snakeskin', 'galaxy', 'lightning', 'skull', 'skulls', 'unicorn', 'paint', 'make', 'change', 'swap', 'undo', 'thinner', 'thicker', 'bigger', 'smaller', 'tiny'];
    var VOC_SHORT = { rd: 'red', blk: 'black', blck: 'black', wht: 'white', whte: 'white', gry: 'grey', grn: 'green', blu: 'blue', prpl: 'purple', orng: 'orange', ylw: 'yellow', yllw: 'yellow', slvr: 'silver', chrm: 'chrome', mtt: 'matte', glod: 'gold', gld: 'gold', pnk: 'pink', drk: 'dark', lt: 'light', bk: 'black' };
    var VOC_STOP = ('back lack good golf goad hold hook hoof hoot hoop rood root room read reed rest real rear team tear tell tank than line like life lame lime size sizes while write wine wind wins wink pint pick pine ping pear peal perl flag flap flaw flab fame face fake fate camp came canny cane stain matter mode male mate prime font lift loft doom doer note none nope noise lover loser logs later laser strip strips stride strike checked outlined point print chance charge swamp sway swat noon darn dart tint rocket spoiled splatter splinter bumped skill start stare stair cameo care card cart trick track block blank whale greet greed grew brow blur blues medal cooper glass class grass brass gross floss boss moss loss bold cold told fold sold mold wide ride hide tide site slide bide deal heal meal seal veal tea teen tall bake bark bale bare bead beat bend best ' +
        'shine shin chime crime prim prize trunks drunk this that then them they there these those what when where with will well wall want went were here have hand hard head heat herd hero high just jump know knew lose love made many more most move much must name near need next nice only open over part past plan play plus pull push rate rich rise road rock role rule safe said sale same save seen self sell send ship shop show shut sign sing slow snow soft some soon sort spot step stop such sure take talk task term text thin tone took tool trip turn type unit upon used user very view vote wait walk warm wash wear week weird whom wild wipe wire wise wish wood word work yard year your zero redo channel fire finer slap caps dare glassy cartoon sliders frames booth lighting outside sampler grab spinner sine snap offline shimmer primary details sprinter flanked scrapes contour strokes decades live sire matters glossary wrng trun tial skill shining satiny').split(' ');
    var VOC_ALL = null;
    function vocab() {
        if (VOC_ALL) return VOC_ALL; var N = (W.SpbIntentPlan && W.SpbIntentPlan.NAMED) || {}, o = {};
        VOC_COL.concat(VOC_PART, VOC_FIN).concat(Object.keys(N).filter(function (k) { return /^[a-z]+$/.test(k); })).forEach(function (w) { o[w] = 1; });
        VOC_ALL = Object.keys(o); return VOC_ALL;
    }
    function osa(a, b, cap) {
        var n = a.length, m = b.length; if (Math.abs(n - m) > cap) return cap + 1; var d = [], i, j;
        for (i = 0; i <= n; i++) { d[i] = [i]; } for (j = 0; j <= m; j++) d[0][j] = j;
        for (i = 1; i <= n; i++) { var rowMin = 99; for (j = 1; j <= m; j++) { var c = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1; var v = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c); if (i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) && a.charAt(i - 2) === b.charAt(j - 1)) v = Math.min(v, d[i - 2][j - 2] + 1); d[i][j] = v; if (v < rowMin) rowMin = v; } if (rowMin > cap) return cap + 1; }
        return d[n][m];
    }
    function fixWord(w) {
        if (VOC_SHORT[w]) return VOC_SHORT[w];
        if (w.length < 4 || VOC_STOP.indexOf(w) !== -1) return null; var V = vocab(); if (V.indexOf(w) !== -1) return null;
        var infl = /^(.{3,}?)(s|es|ed|d|ing|er|est|en|ly)$/.exec(w); if (infl && (V.indexOf(infl[1]) !== -1 || V.indexOf(infl[1] + 'e') !== -1)) return null;          // paints / changed / lighten: a real inflection, not a typo
        var cap = w.length >= 7 ? 2 : 1, best = null, bd = 99, tie = false;
        for (var i = 0; i < V.length; i++) {
            var v = V[i]; if (v.length < 3) continue;
            if (v.charAt(0) !== w.charAt(0) && !(v.charAt(0) === w.charAt(1) && v.charAt(1) === w.charAt(0))) continue;
            var dd = osa(w, v, cap); if (dd > cap) continue;
            if (dd < bd) { bd = dd; best = v; tie = false; } else if (dd === bd && v !== best) { if (v.indexOf(best) === 0 || best.indexOf(v) === 0) { if (v.length < best.length) best = v; } else tie = true; }          // gloss / glossy: same word
        }
        return best && !tie ? best : null;
    }
    // clean(text) -> { text: cleaned, fixes: [[said, read]] }; the cleaned text keeps everything else as said
    function clean(text) {
        var s = String(text == null ? '' : text), fixes = [];
        var out = s.replace(/#?[A-Za-z0-9']+/g, function (tok) {
            if (/^#|\d/.test(tok)) return tok; var w = tok.toLowerCase().replace(/'s$/, ''); if (!/^[a-z]+$/.test(w)) return tok;
            var r = fixWord(w); if (!r || r === w) return tok; fixes.push([tok, r]); return r;
        });
        return { text: out, fixes: fixes };
    }
    var PART_SAID = [['hood', /\b(hood|bonnet)\b/], ['roof', /\b(roof|roofline)\b/], ['trunk', /\b(trunk|boot|deck ?lid|tailgate)\b/], ['spoiler', /\b(spoiler|wing)\b/], ['front bumper', /\b(front bumper|nose|splitter|front lip|air ?dam|front fascia|bumpers)\b/],
        ['rear bumper', /\b(rear bumper|back bumper|diffuser|rear fascia|bumpers)\b/], ['left side', /\b(left|driver'?s?) ?(side|door|fender|quarter|panel)s?\b|\b(sides|doors|both sides|fenders|quarters|flanks|skirts|rockers|side skirts)\b/], ['right side', /\b(right|passenger'?s?) ?(side|door|fender|quarter|panel)s?\b|\b(sides|doors|both sides|fenders|quarters|flanks|skirts|rockers|side skirts)\b/]];
    function partsSaid(t) { var s2 = String(t || '').toLowerCase(), o = []; PART_SAID.forEach(function (pp) { if (pp[1].test(s2)) o.push(pp[0]); }); return o; }
    function lookSaid(L, t) { if (!L) return false; var ws = []; if (L.colour && L.colour.word) ws = ws.concat(String(L.colour.word).toLowerCase().split(/[\s-]+/)); if (L.finish && L.finish.family) ws.push(L.finish.family); if (L.pattern && L.pattern.concept) ws = ws.concat(String(L.pattern.concept).split(/\s+/)); if (L.colour && L.colour.hex && t.indexOf(String(L.colour.hex).slice(1)) !== -1) return true; return ws.some(function (w) { return w.length > 2 && t.indexOf(w) !== -1; }); }
    function vocabCols(t) { var ws = String(t || '').toLowerCase().split(/[^a-z]+/); return VOC_COL.slice(0, 40).filter(function (c) { return ws.indexOf(c) !== -1; }); }
    function userMessage(state, text) {
        var t = String(text == null ? '' : text), c = clean(t);
        return 'STATE (data):\n' + JSON.stringify(state) + '\n\nBUYER SAYS: ' + t + (c.fixes.length ? '\nREAD AS (spelling fixed by the app): ' + c.text : '');
    }

    // ------------------------------------------------------------------ tool call -> validated frame
    var PART_SYN = [[/^(the )?(whole car|car|body|everything|all)$/, '@body'], [/bonnet/, 'hood'], [/^(boot|deck ?lid|decklid|tail ?gate|tailgate|rear deck)$/, 'trunk'], [/^(wing|rear wing)$/, 'spoiler'],
        [/^(top wing|wing)$/, 'spoiler'], [/^roof ?line$/, 'roof'], [/^nose$|front bumper|front fascia|splitter|front lip|air ?dam/, 'front bumper'], [/rear bumper|back bumper|rear fascia|diffuser/, 'rear bumper'], [/^cab$/, '@cab'],
        [/^(sides|both sides|the sides|doors|both doors|side panels|flanks)$/, '@sides'], [/^(bumpers|both bumpers)$/, '@bumpers'],
        [/(left|driver|drivers|driver's).*(side|door|fender|quarter|panel)|^left$/, 'left side'], [/(right|passenger|passengers|passenger's).*(side|door|fender|quarter|panel)|^right$/, 'right side']];
    function normPart(p, out, body) {
        var s = low(p).replace(/_/g, ' ').replace(/\s+/g, ' ');
        if (CANON.indexOf(s) !== -1) { out.push(s); return; }
        for (var i = 0; i < PART_SYN.length; i++) if (PART_SYN[i][0].test(s)) { var t = PART_SYN[i][1]; if (t === '@body') body.yes = true; else if (t === '@sides') { out.push('left side'); out.push('right side'); } else if (t === '@bumpers') { out.push('front bumper'); out.push('rear bumper'); } else if (t === '@cab') { out.push('roof'); out.push('left side'); out.push('right side'); } else out.push(t); return; }
        out.push(s);          // unknown: kept, the planner asks ("This car has no <x> on its paint map")
    }
    function hexNorm(h) {
        var s = String(h == null ? '' : h).trim(); if (!s) return null; if (s.charAt(0) !== '#') s = '#' + s;
        if (/^#[0-9a-f]{3}$/i.test(s)) s = '#' + s.charAt(1) + s.charAt(1) + s.charAt(2) + s.charAt(2) + s.charAt(3) + s.charAt(3);
        return /^#[0-9a-f]{6}$/i.test(s) ? s.toLowerCase() : null;
    }
    function colNorm(c) {
        if (c == null || c === '') return undefined; if (typeof c === 'string') c = /^#?[0-9a-f]{3}([0-9a-f]{3})?$/i.test(c.trim()) ? { hex: c } : { word: c };
        if (typeof c !== 'object') return undefined; var o = {}; if (c.word || c.name) o.word = String(c.word || c.name); var hx = hexNorm(c.hex || c.color || (o.word && /^#/.test(o.word) ? o.word : null));
        if (hx) o.hex = hx; else if (o.word) { var N = W.SpbIntentPlan && W.SpbIntentPlan.NAMED, k = low(o.word); if (N && N[k]) o.hex = N[k]; }
        return (o.word || o.hex) ? o : undefined;
    }
    function layerMatch(name, env) {
        if (W.SpbLayerTargets && env && env.layers && env.layers.length) {
            var rows = env.layers.map(function(l){return typeof l === 'string' ? {name:l} : l;});
            var resolved = W.SpbLayerTargets.resolve(name, rows);
            return resolved.ok ? {name:resolved.selector} : {bad:String(name)};
        }
        var Ls = ((env && env.layers) || []).map(function (l) { return l && (l.name || l); }).filter(Boolean), s = low(name);
        if (!Ls.length) return { name: String(name) };
        for (var i = 0; i < Ls.length; i++) if (Ls[i] === name) return { name: Ls[i] };
        for (i = 0; i < Ls.length; i++) if (low(Ls[i]) === s || low(Ls[i]).replace(/[\s_-]+/g, '') === s.replace(/[\s_-]+/g, '')) return { name: Ls[i] };
        if (/number/.test(s)) return { element: 'numbers' }; if (/logo|sponsor|decal|contingenc/.test(s)) return { element: 'sponsors' };
        return { bad: String(name) };
    }
    function layerName(ref, env) {
        var hit = W.SpbLayerTargets && W.SpbLayerTargets.resolve(ref, (env && env.layers) || []);
        return hit && hit.ok ? String(hit.row.name) : String(ref);
    }
    function tgtNorm(T, env, rep, where) {
        if (T == null) return undefined;
        if (typeof T === 'string') { var s = low(T); if (/^(numbers?|number panel)$/.test(s)) T = { kind: 'element', element: 'numbers' }; else if (/^(sponsors?|logos?|decals?)$/.test(s)) T = { kind: 'element', element: 'sponsors' }; else T = { kind: 'part', parts: [T] }; }
        if (typeof T !== 'object') return undefined; T = clone(T) || {};
        var k = low(T.kind || (T.parts ? 'part' : T.layers ? 'layer' : T.element ? 'element' : T.colour || T.color ? 'colour' : T.object ? 'object' : T.between ? 'colour' : 'body'));
        if (k === 'color') k = 'colour'; if (k === 'parts') k = 'part'; if (k === 'whole' || k === 'car') k = 'body'; T.kind = k;
        if (T.color && !T.colour) { T.colour = T.color; delete T.color; }
        if (T.part && !T.parts) { T.parts = T.part; delete T.part; }
        if (T.layer && !T.layers) { T.layers = T.layer; delete T.layer; }
        if (T.parts != null) { var ps = [], body = { yes: false }; arr(T.parts).forEach(function (p) { normPart(p, ps, body); }); ps = uniq(ps); if (body.yes && !ps.length) { T.kind = 'body'; delete T.parts; } else T.parts = ps; if (T.parts && !T.parts.length) delete T.parts; }
        if (T.kind === 'part' && !(T.parts && T.parts.length)) { T.kind = 'body'; rep.push(where + ': part with no parts -> body'); }
        if (T.kind === 'body' && T.portion && /lower|bottom|below|rocker|skirt/.test(low(T.portion))) { var ps0 = env && typeof env.text === 'string' ? partsSaid(env.text + ' ' + clean(env.text).text) : []; T.kind = 'part'; T.parts = ps0.length ? ps0 : ['left side', 'right side', 'front bumper', 'rear bumper']; rep.push(where + ': lower part of the body -> ' + T.parts.join('+') + ' (S7c)'); }          // S7c: the planner paints a body portion as the whole car
        if (T.layers != null) {
            var ls = [], el = null; arr(T.layers).forEach(function (n) { var m = layerMatch(n, env); if (m.name) ls.push(m.name); else if (m.element) el = el || m.element; else { rep.push(where + ': unknown layer ' + m.bad); T._badLayer = true; } });
            T.layers = uniq(ls); if (!T.layers.length) delete T.layers;
            if (el && T.kind === 'layer' && !T.layers) { T.kind = 'element'; T.element = el; rep.push(where + ': layer name -> element ' + el); }
        }
        if (T.kind === 'layer' && !T.layers) { if (T._badLayer) { T.kind = 'object'; T.object = T.object || 'that layer'; } else T.kind = 'body'; }
        delete T._badLayer;
        if (T.element) { var e = low(T.element); T.element = /number/.test(e) ? 'numbers' : /logo|sponsor|decal/.test(e) ? 'sponsors' : /stripe|tape/.test(e) ? 'stripes' : e; }
        if (T.kind === 'element' && !T.element) T.kind = 'body';
        if (T.colour !== undefined) { T.colour = colNorm(T.colour); if (!T.colour) delete T.colour; }
        if (T.between) { T.between = arr(T.between).map(function (b, i) { return tgtNorm(b, env, rep, where + '.between' + i); }).filter(Boolean); if (T.kind === 'body') T.kind = 'colour'; }
        if (T.kind === 'colour' && !T.colour && !T.between) { T.kind = T.parts ? 'part' : (T.layers ? 'layer' : 'body'); rep.push(where + ': colour target with no colour'); }
        if (typeof T.ref === 'object' && T.ref) T.ref = T.ref.to || undefined;
        if (T.ref && ['last_change', 'last_target'].indexOf(T.ref) === -1) delete T.ref;
        if (T.kind === 'graphic' && T.graphic && typeof T.graphic !== 'string') T.graphic = String(T.graphic.kind || T.graphic.concept || '');
        return T;
    }
    function lookNorm(L, rep) {
        if (L == null || typeof L !== 'object') return {}; L = clone(L) || {};
        if (L.color && !L.colour) { L.colour = L.color; delete L.color; }
        if (L.colour !== undefined) { L.colour = colNorm(L.colour); if (!L.colour) delete L.colour; }
        if (L.colours) { L.colours = arr(L.colours).map(colNorm).filter(Boolean); if (!L.colours.length) delete L.colours; }
        if (L.gradient) { var g = L.gradient; if (Array.isArray(g)) g = { stops: g }; g.stops = arr(g.stops).map(function (s) { if (s && typeof s === 'object') { var c = colNorm(s); return c ? (c.hex || c.word) : null; } return s == null ? null : String(s); }).filter(Boolean); if (g.axis) g.axis = low(g.axis).replace(/[\s-]+/g, '_'); if (g.stops.length < 2) { delete L.gradient; rep.push('gradient with < 2 stops dropped'); } else L.gradient = g; }
        if (L.finish) { if (typeof L.finish === 'string') L.finish = /::/.test(L.finish) ? { key: L.finish } : { family: L.finish }; if (L.finish.family) L.finish.family = low(L.finish.family); if (L.finish.key && !/::/.test(L.finish.key)) { if (!L.finish.family) L.finish.family = low(L.finish.key); delete L.finish.key; } if (!L.finish.family && !L.finish.key) delete L.finish; }
        if (L.pattern) { if (typeof L.pattern === 'string') L.pattern = { concept: L.pattern }; if (L.pattern.concept) L.pattern.concept = low(L.pattern.concept); if (!L.pattern.concept && !L.pattern.id) delete L.pattern; }
        if (L.stroke) { if (typeof L.stroke === 'string') L.stroke = { width: low(L.stroke) }; if (L.stroke.px != null && !isFinite(Number(L.stroke.px))) delete L.stroke.px; }
        if (L.scale != null) { var sc = Number(String(L.scale).replace('%', '')); if (!isFinite(sc) || sc <= 0) delete L.scale; else L.scale = sc > 5 ? sc / 100 : sc; }
        if (L.spec) ['metal', 'rough', 'clearcoat'].forEach(function (c) { if (L.spec[c] != null) { var v = Math.round(Number(L.spec[c])); if (!isFinite(v)) delete L.spec[c]; else L.spec[c] = Math.max(0, Math.min(255, v)); } });
        if (L.accent === false) delete L.accent;
        return L;
    }
    var VERB_SYN = { paint: 'recolour', color: 'recolour', colour: 'recolour', recolor: 'recolour', finish: 'refinish', copy: 'copy_look', match: 'copy_look', line: 'outline', border: 'outline', move: 'retarget', fade: 'gradient', stripes: 'stripe', edit: 'adjust', change: 'adjust', flames: 'graphic' };
    function opNorm(op, env, rep, i) {
        if (!op || typeof op !== 'object') return null; op = clone(op) || {}; var L = lists(), w = 'op' + i;
        var v = low(op.verb || op.act || ''); v = VERB_SYN[v] || v; if (L.verbs.indexOf(v) === -1) { rep.push(w + ': verb ' + (op.verb || '?') + ' -> ' + (op.look && (op.look.colour || op.look.color) ? 'recolour' : 'adjust')); v = op.look && (op.look.colour || op.look.color) ? 'recolour' : 'adjust'; }
        op.verb = v; delete op.act;
        if (op.ref != null) { if (typeof op.ref === 'string') op.ref = { to: op.ref }; if (!op.ref || ['last_change', 'last_target', 'opposite_side', 'turn'].indexOf(op.ref.to) === -1) delete op.ref; }
        if (op.target != null) op.target = tgtNorm(op.target, env, rep, w + '.target'); if (op.target && op.target.ref && !op.ref) { op.ref = { to: op.target.ref }; }
        if (!op.target) delete op.target;
        if (op.target && op.target.kind === 'zone' && !op.ref && !op.target.zones && !op.target.zone) { op.ref = { to: 'last_change' }; rep.push(w + ': zone target -> ref last_change'); }
        if (op.except != null) { op.except = arr(op.except).map(function (x, k) { return tgtNorm(x, env, rep, w + '.except' + k); }).filter(Boolean); if (!op.except.length) delete op.except; }
        if (op.source != null) { op.source = tgtNorm(op.source, env, rep, w + '.source'); if (!op.source) delete op.source; }
        op.look = lookNorm(op.look, rep);
        if (op.relative != null) { var rl = op.relative; if (typeof rl === 'string') rl = { prop: rl }; if (Array.isArray(rl)) rl = rl.map(function (r) { return relNorm(r); }).filter(Boolean); else rl = relNorm(rl); if (rl && (!Array.isArray(rl) || rl.length)) op.relative = rl; else delete op.relative; }
        if (op.copy != null) { op.copy = arr(op.copy).map(low).map(function (c) { return c === 'color' ? 'colour' : c; }).filter(function (c) { return ['colour', 'finish', 'spec', 'scale', 'pattern'].indexOf(c) !== -1; }); if (!op.copy.length) delete op.copy; }
        if (v === 'copy_look' && !op.source) { rep.push(w + ': copy_look with no source'); }
        if (v === 'adjust' && !op.ref && !op.target) { op.ref = { to: 'last_change' }; rep.push(w + ': adjust with no target -> ref last_change'); }
        return op;
    }
    function relNorm(r) {
        if (!r || typeof r !== 'object') return null; var p = low(r.prop || r.property || ''); var PS = { thickness: 'width', size: 'scale', brightness: 'lightness', light: 'lightness', shine: 'gloss', metallic: 'metal', colour: 'hue', color: 'hue', gradient: 'stops' };
        p = PS[p] || p; if (['width', 'scale', 'lightness', 'saturation', 'hue', 'gloss', 'metal', 'strength', 'stops'].indexOf(p) === -1) return null;
        var d = r.dir; if (typeof d === 'string') d = /^(-|down|less|lower|smaller|thinner|darker|decrease)/i.test(d) ? -1 : 1; d = Number(d) < 0 ? -1 : 1;
        var o = { prop: p, dir: d }; if (r.amount != null && r.amount !== '') o.amount = isFinite(Number(r.amount)) ? Number(r.amount) : low(r.amount); return o;
    }
    function pickCall(x) {
        if (!x) return null; if (Array.isArray(x)) { for (var i = 0; i < x.length; i++) { var c = x[i]; if (c && c.function && c.function.name === 'submit_frame') return c; } return null; }
        return x;
    }
    function argsOf(call) {
        if (!call) return null; var a = call.function ? call.function.arguments : (call.arguments != null ? call.arguments : call);
        if (typeof a === 'string') { var s = a.trim().replace(/^```(?:json)?/i, '').replace(/```$/, '').trim(); try { a = JSON.parse(s); } catch (e) { return { _err: 'arguments were not valid JSON' }; } }
        if (a && typeof a.frame === 'string') { try { a.frame = JSON.parse(a.frame); } catch (e2) { return { _err: 'frame was not valid JSON' }; } }
        return a;
    }
    function fromCall(x, env) {
        var call = pickCall(x), a = argsOf(call), rep = [], L = lists();
        if (!a || a._err) return { ok: false, ask: { q: 'Sorry, I did not catch that. Could you say it another way?', chips: [] }, errors: [a && a._err || 'no submit_frame call'] };
        var f = (a.frame && typeof a.frame === 'object') ? clone(a.frame) : (a.act || a.ops ? clone(a) : null);
        if (!f) return { ok: false, ask: { q: 'Sorry, I did not catch that. Could you say it another way?', chips: [] }, errors: ['no frame in the call'] };
        var act = low(f.act || (f.ops ? 'change' : 'nothing')); act = { ask: 'ask_back', question: 'answer', edit: 'change', none: 'nothing' }[act] || act;
        if (L.acts.indexOf(act) === -1) { rep.push('act ' + f.act + ' -> nothing'); act = 'nothing'; }
        var out = { v: 1, turn: null, producer: 'deepseek', act: act, ops: [], keep: [], decals: low(f.decals) === 'include' ? 'include' : 'protect', confidence: isFinite(Number(f.confidence)) ? Number(f.confidence) : null, missing: [], alts: [], said: f.said || '' };
        if (act === 'change') out.ops = arr(f.ops).map(function (o, i) { return opNorm(o, env, rep, i); }).filter(Boolean);
        else if (arr(f.ops).length) rep.push('rule 5: ' + act + ' carries no ops (' + arr(f.ops).length + ' dropped)');
        out.keep = arr(f.keep).map(function (k, i) { return tgtNorm(k, env, rep, 'keep' + i); }).filter(Boolean);
        out.missing = uniq(arr(f.missing).map(low).filter(Boolean));
        out.alts = arr(f.alts).filter(function (x) { return x && typeof x === 'object'; });
        if (f.question && act === 'answer') out.question = f.question; if (f.list && act === 'list') out.list = f.list;
        if (act === 'undo' || act === 'redo') out.n = Math.max(1, Math.min(99, Math.round(Number(f.n) || 1)));
        if (f.replace_last === true && act === 'change') out.replace_last = true;
        out.ops.forEach(function (o, i) {          // "the hood flat black and the roof same": a ref inside one sentence means the op before it, never an earlier turn
            var hasLook = o.look && Object.keys(o.look).length;
            if (i > 0 && o.ref && o.ref.to === 'last_change' && o.target && o.target.kind !== 'zone' && !hasLook && !o.relative && o.verb !== 'retarget') { var pv = out.ops[i - 1]; o.verb = pv.verb === 'adjust' ? 'recolour' : pv.verb; o.look = clone(pv.look) || {}; delete o.ref; rep.push('op' + i + ': same-sentence ref -> the look of op' + (i - 1)); }
        });
        if (env && env.hasLast === false && act === 'change' && typeof env.text === 'string' && out.ops.length && !out.missing.length) {          // S7 R3: "make it chrome" / "red" as the FIRST request: "it" is not the whole car (rule 15d)
            var tx = (env.text + ' ' + clean(env.text).text).toLowerCase(), words = env.text.toLowerCase().replace(/[^a-z0-9#' ]+/g, ' ').trim().split(/\s+/).filter(Boolean);
            var wholeOnly = out.ops.every(function (o) { return o.target && (o.target.kind === 'body' || o.target.kind === 'car'); });
            var likeCol = /\b(like|ish|style|styled|theme|themed|livery|inspired)\b/.test(tx) && vocabCols(tx).length > 0;          // S7c: "like minecraft, green blocks" names its colours
            if (wholeOnly && !likeCol && !/\b(car|whole|everything|body|all over|entire|all of it)\b/.test(tx) && !/\b(same colou?rs?|keep (?:\w+ )?colou?rs?|colou?rs? (?:the same|stay|stays)|just (?:make it |a bit )?(?:shiny|shinier|glossy|matte|satin|chrome|metallic|pearl))/.test(tx) && !/\b(car|truck|whole|everything|body|paint job|livery)\b/.test(String(env.prevText || '').toLowerCase()) && (words.length <= 2 || /\b(make|paint|do|turn) (it|this|that)\b/.test(tx))) { out.ops = []; out.missing = ['target']; rep.push('first request with no target named -> missing target'); }
        }
        if (env && typeof env.text === 'string' && out.ops.length > 1 && !/\b(make|change|paint|turn|recolou?r|set)\b[^.,;]{0,25}numb|numb[a-z]*\b[^.,;]{0,12}\b(to|into|should be|need to be)\b|outline|stroke|\bedge/.test(env.text.toLowerCase())) {          // S7 R4 (rule 3d): numbers named inside a whole-car look are kept artwork, not an edit
            if (out.ops.some(function (o) { return o.target && o.target.kind !== 'element'; })) out.ops = out.ops.filter(function (o, i) {
                var drop = o.target && o.target.kind === 'element' && o.target.element === 'numbers' && (o.verb === 'recolour' || o.verb === 'refinish');
                if (drop) { out.keep = (out.keep || []).concat([{ kind: 'element', element: 'numbers' }]); rep.push('op' + i + ': numbers inside a whole-car look -> kept (rule 3d)'); }
                return !drop;
            });
        }
        if (env && env.hasLast === false) out.ops.forEach(function (o, i) {          // nothing committed earlier: a ref cannot resolve
            if (!o.ref || o.ref.to === 'turn') return;
            if (o.target && o.target.kind !== 'zone' && o.verb !== 'retarget') { delete o.ref; if (o.verb === 'adjust' && !o.relative && o.look && (o.look.colour || o.look.finish || o.look.pattern || o.look.gradient)) o.verb = o.look.colour ? 'recolour' : 'refinish'; rep.push('op' + i + ': no earlier change -> ref dropped'); }
            else if (out.missing.indexOf('target') === -1) { out.missing.push('target'); rep.push('op' + i + ': no earlier change -> missing target'); }
        });
        // S7b R6 (decals guard): numbers / sponsors / logos are touched ONLY when the buyer says so. (1) decals:"include" needs the buyer to name them; (2) a recolour / refinish / pattern op on element numbers or sponsors with no such word in the sentence is an unasked repaint: dropped, and the element is kept.
        if (env && typeof env.text === 'string' && act === 'change') {
            var tl = env.text.toLowerCase(), namesDec = /\b(numbers?|numerals?|logos?|sponsors?|decals?|panels?|pitbox|contingency|contingencies|tape|stickers?|lettering|decor)\b|#\s?\d/.test(tl);
            if (out.decals === 'include' && !namesDec) { out.decals = 'protect'; rep.push('decals include without naming them -> protect (S7b)'); }
            if (!namesDec && out.ops.length > 1) out.ops = out.ops.filter(function (o, i) {
                var T = o.target, bad = T && T.kind === 'element' && (T.element === 'numbers' || T.element === 'sponsors') && /^(recolour|refinish|restyle|pattern|gradient|outline)$/.test(o.verb);
                if (bad) { out.keep = (out.keep || []).concat([{ kind: 'element', element: T.element }]); rep.push('op' + i + ': ' + T.element + ' never named -> dropped, kept (S7b)'); }
                return !bad;
            });
        }
        // S7b R2: copy_look whose source is a colour (sampled from a layer) = a plain recolour with that exact hex (the planner cannot resolve a bare colour source and would ask "which zone")
        out.ops.forEach(function (o, i) {
            var S = o.source; if (o.verb === 'copy_look' && S && S.kind === 'colour' && S.colour && /^#[0-9a-f]{6}$/i.test(String(S.colour.hex || ''))) {
                o.verb = 'recolour'; o.look = o.look || {}; o.look.colour = { word: S.colour.word || S.colour.hex, hex: S.colour.hex.toLowerCase() }; delete o.source; delete o.copy;
                if (!o.target) o.target = { kind: 'body' }; rep.push('op' + i + ': copy_look from a colour -> recolour ' + o.look.colour.hex + ' (S7b)');
            }
        });
        // S7b R1: stripes with the whole car as target run down the centre line (the planner asks "which part" otherwise); a colour target that only names decal layers the buyer never named is the body paint (rule 3c)
        out.ops.forEach(function (o, i) {
            if (o.verb === 'stripe' && o.target && o.target.kind === 'body') { o.target = { kind: 'part', parts: ['hood', 'roof', 'trunk'] }; rep.push('op' + i + ': stripe on the whole car -> hood + roof + trunk (S7b)'); }
            var T = o.target; if (T && T.kind === 'colour' && arr(T.layers).length && env && typeof env.text === 'string') {
                var dec = ['Logos', 'Car_Decal', 'Pitbox Colors', 'Contingency Decals', 'Numbers', 'Color Change Logos'], onlyDec = arr(T.layers).every(function (l) { return dec.indexOf(layerName(l, env)) !== -1; });
                var said = env.text.toLowerCase(), named = arr(T.layers).some(function (l) { l = layerName(l, env); return said.indexOf(l.toLowerCase().replace(/_/g, ' ')) !== -1 || said.indexOf(l.toLowerCase()) !== -1; }) || /\b(logo|logos|sponsor|sponsors|decal|decals|number|numbers|pitbox|contingency)\b/.test(said);
                if (onlyDec && !named && o.verb !== 'copy_look') { T.layers = []; rep.push('op' + i + ': decal layer never named -> body paint colour (rule 3c, S7b)'); }
            }
        });
        // V3 S6 2026-10-06 S7b guards (the online harm families on train / train_aug p2): (a) adjust + ref last_change never reaches parts the last change did not paint;
        // (b) a Logos / decal LAYER is a target only when the buyer names the layer; (c) a question never becomes a change; (d) a colour the buyer never said never repaints the whole car.
        if (act === 'change' && env && typeof env.text === 'string') {
            var gtx = env.text.toLowerCase(), gLast = arr(env.lastParts), gFix = clean(env.text).text, gAll = gtx + ' \n ' + gFix.toLowerCase(), gPrev = String(env.prevText || '');
            out.ops.forEach(function (o, i) {
                if (!(o.ref && o.ref.to === 'last_change') || !gLast.length || !o.target || o.target.kind !== 'part') return;
                var inL = arr(o.target.parts).filter(function (p) { return gLast.indexOf(p) !== -1; });
                if (inL.length && inL.length < arr(o.target.parts).length) { o.target.parts = inL; rep.push('op' + i + ': ref last_change restricted to its own parts (S6 a)'); }
                else if (!inL.length) { delete o.ref; rep.push('op' + i + ': parts outside the last change -> ref dropped (S6 a)'); }
            });
            var DECL = ['logos', 'car_decal', 'pitbox colors', 'contingency decals', 'numbers', 'color change logos'];
            out.ops = out.ops.filter(function (o, i) {
                var T = o.target; if (!T || (T.kind !== 'layer' && T.kind !== 'object' && T.kind !== 'colour')) return true;
                var ls = arr(T.layers).map(function (l) { return layerName(l, env).toLowerCase(); }); if (!ls.length || !ls.every(function (l) { return DECL.indexOf(l) !== -1; })) return true;
                if (/\blayers?\b/.test(gAll) || ls.some(function (l) { return l.indexOf(' ') !== -1 && gtx.indexOf(l) !== -1 || l.indexOf('_') !== -1 && gtx.indexOf(l) !== -1; })) return true;
                if (arr(T.layers).some(function (L) { var re = new RegExp('(^|[^A-Za-z])' + String(L).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '([^A-Za-z]|$)'); return re.test(env.text) || re.test(gFix) || (T.kind === 'layer' && (re.test(gPrev) || (/[ _]/.test(L) && gPrev.toLowerCase().indexOf(String(L).toLowerCase()) !== -1))); })) return true;          // S7c: the layer named with its own spelling ("On Logos", "Car_Decal") now or in an earlier turn ("opacity down 20%")
                if (T.kind === 'colour' && !/^(recolour|refinish|pattern|restyle)$/.test(o.verb)) return true;
                if (out.missing.indexOf('target') === -1) out.missing.push('target'); rep.push('op' + i + ': decal layer ' + ls.join('+') + ' never named as a layer -> ask (S6 b)'); return false;
            });
            var isQ = !/^\s*(?:please\s+|pls\s+)?(?:can|could|would|will) (?:you|u)\b/.test(gtx) && !/^\s*(?:is|it'?s|its) (?:not|n'?t)\b[^?]*$/.test(gtx) && (/^\s*(?:how|what|whats|what's|why|which|where|when|is|are|does|do i|do we|do they|should i|should we|can i|can we|could i|would it|will it|am i|is there|are there)\b/.test(gtx) || /\?\s*$/.test(gtx) || /[,;]\s*(?:how (?:can|do|would|should) (?:i|we)|is (?:that|it|there)|are they|do i|can i|should i)\b/.test(gtx));
            if (isQ && (/^\s*(?:can i (?:get|have)|how ?(?:bout|about)|what if|with|and|also|just|plus)\b/.test(gtx) || /\b(?:ok|okay|right|yeah)\s*\?\s*$/.test(gtx) || /[,;.]\s*(?:now\s+|then\s+|so\s+)?(?:make|paint|turn|give|put|add|change|do)\b/.test(gtx))) isQ = false;          // a request in question form
            if (isQ && out.ops.length) { out.ops = []; act = 'answer'; out.act = 'answer'; out.missing = []; rep.push('a question -> answer, never a change (S6 c)'); }
            var hexIn = /#?\b[0-9a-f]{6}\b/.test(gtx), themeIn = /\b(?:like|ish|style|styled|theme|themed|livery|inspired|scheme|colou?rs? of|same|match|logo|sample|pull|layer)\b/.test(gtx);
            if (out.ops.length === 1 && !hexIn && !themeIn) {
                var o0 = out.ops[0], c0 = o0.look && o0.look.colour, tb = o0.target && (o0.target.kind === 'body' || o0.target.kind === 'car');
                if (tb && c0 && c0.word && !(o0.look.pattern || o0.look.gradient) && String(c0.word).toLowerCase().split(/[\s-]+/).every(function (w) { return w.length > 2 && gAll.indexOf(w) === -1 && gPrev.toLowerCase().indexOf(w) === -1; })) { out.ops = []; out.missing = ['what']; rep.push('op0: colour "' + c0.word + '" never said -> ask (S6 d)'); }
            }
        }
        if (act === 'change' && env && typeof env.text === 'string') {          // S7c 2026-10-07 guards (train harm families)
            var sTx = (env.text + ' ' + clean(env.text).text).toLowerCase(), sSaid = partsSaid(sTx);
            out.ops.forEach(function (o, i) {          // (a) "fade from black on the roof to red on the hood": a gradient between named parts runs over THOSE parts, never the whole car
                if (o.verb === 'gradient' && o.target && o.target.kind === 'body' && !arr(o.except).length && sSaid.length >= 2 && !/\b(whole|entire|everything|all over|body|car|truck)\b/.test(sTx)) { o.target = { kind: 'part', parts: sSaid.slice() }; rep.push('op' + i + ': gradient between named parts -> ' + sSaid.join('+') + ' (S7c)'); }
            });
            if (env.hasLast && out.ops.length > 1) {          // (b) a follow-up that re-sends an earlier op on parts and looks nobody named this turn ("and chrome on the mirrors" -> roof candy red again)
                var keepOps = out.ops.filter(function (o) { var T = o.target; if (!T || T.kind !== 'part' || o.ref || o.relative) return true; if (arr(T.parts).some(function (q) { return sSaid.indexOf(q) !== -1; })) return true; return lookSaid(o.look, sTx); });
                if (keepOps.length && keepOps.length < out.ops.length) { rep.push((out.ops.length - keepOps.length) + ' op(s) on parts / looks not named this turn -> dropped (S7c)'); out.ops = keepOps; }
            }
            var emptyAdj = function (o) { return o.verb === 'adjust' && !o.relative && !(o.look && Object.keys(o.look).length) && (!o.target || o.target.kind === 'zone') && !o.source; };
            if (out.ops.length > 1 && out.ops.some(function (o) { return !emptyAdj(o); }) && out.ops.some(emptyAdj)) { out.ops = out.ops.filter(function (o) { return !emptyAdj(o); }); rep.push('empty adjust op(s) next to a real op -> dropped (S7c)'); }
            if (out.ops.length && out.ops.every(emptyAdj)) {          // "is not enough, more more shine" / "darker" with the relative left out
                var RELW = [[/\b(?:more|extra)\b[^.,;]{0,12}\b(?:shine|shiny|gloss|glossy|reflective|clear ?coat)\b|\bshinier\b|\bglossier\b/, 'gloss', 1], [/\bless\b[^.,;]{0,12}\b(?:shine|shiny|gloss|glossy|reflective)\b|\bduller\b/, 'gloss', -1], [/\bmore\b[^.,;]{0,8}\bmetal(?:lic)?\b/, 'metal', 1],
                    [/\bdarker\b/, 'lightness', -1], [/\b(?:lighter|brighter)\b/, 'lightness', 1], [/\b(?:thinner|narrower)\b/, 'width', -1], [/\b(?:thicker|wider|fatter)\b/, 'width', 1], [/\b(?:bigger|larger)\b/, 'scale', 1], [/\b(?:smaller|tinier|finer|tighter)\b/, 'scale', -1]];
                var rw = null; RELW.forEach(function (x) { if (!rw && x[0].test(sTx)) rw = { prop: x[1], dir: x[2] }; });
                if (rw) { out.ops = [out.ops[0]]; out.ops[0].relative = rw; if (!out.ops[0].ref && !out.ops[0].target) out.ops[0].ref = { to: 'last_change' }; rep.push('empty adjust -> relative ' + rw.prop + ' ' + rw.dir + ' from the sentence (S7c)'); }
            }
            if (/\btoo\s+(?:shiny|shinny|reflective|glossy|mirror(?:y|ed)?|chromey?)\b/.test(sTx) && !/\b(matte|satin|flat|dull|semi|less|tone|down|lower|reduce|bit|little|half|metallic|pearl|instead|rather|make it|go)\b/.test(sTx) && out.ops.every(function (o) { return o.verb === 'adjust' && !(o.look && (o.look.finish || o.look.colour)); })) {
                out.ops = []; out.missing = ['finish']; rep.push('"too shiny" with no new finish -> ask which finish (S7c, owner rule 15)');          // (c)
            }
        }
        if (act === 'change' && !out.ops.length && !out.missing.length) { out.missing = ['what']; rep.push('change with no ops -> missing what'); }
        out.ops.forEach(function (o, i) { if (o.target && o.target.kind === 'object' && arr(o.target.layers).length === 0 && /layer/.test(JSON.stringify(f.ops && f.ops[i] && f.ops[i].target || ''))) { if (out.missing.indexOf('layer') === -1) out.missing.push('layer'); } });
        var val = (W.SpbIntentFrame && W.SpbIntentFrame.validate) ? W.SpbIntentFrame.validate(out, env) : { ok: true, errors: [] };
        var hard = (val.errors || []).filter(function (e) { return !/: part /.test(e); });          // unknown parts are the planner's to ask about (chips of the real parts)
        if (hard.length) return { ok: false, ask: { q: 'Sorry, I could not work out ' + (/layer/.test(hard[0]) ? 'which layer you meant' : 'that request') + '. Could you say it another way?', chips: [] }, errors: hard, frame: out, repairs: rep };
        if (out.act === 'change' && env && typeof env.text === 'string') { try { var DRm = W.SpbIntentDoor; if (DRm && DRm.annotate) DRm.annotate(out, env.text, env); } catch (eDr) {} }          // D-DOOR 2026-10-08 hook
        return { ok: true, frame: out, repairs: rep, errors: val.errors || [] };
    }

    // ------------------------------------------------------------------ S7c 2026-10-07 retry guard: the model sent NO change (ask / nothing / empty ops) on a turn that clearly names a look AND a place
    // ("GT3 whitte base", "make car puple", "can i get both the diors a darker colour") -> the host sends the turn ONCE more with a short APP CHECK line and keeps the 2nd frame only
    // when it is a change with ops (betterFrame). Never when the app's own guards emptied the frame (those asks are deliberate), never on a question.
    var LOOK_W = /\b(red|white|black|blue|navy|green|yellow|orange|purple|pink|gold|silver|gr[ae]y|gunmetal|bronze|copper|brown|teal|cyan|magenta|maroon|charcoal|cream|violet|turquoise|burgundy|crimson|lime|chrome|matte|metallic|pearl|candy|satin|gloss|glossy|brushed|carbon|flake|holo|primer|shiny|camo|checker|checkered|flames|gradient|fade|stripe|stripes|pinstripe|darker|lighter|brighter|#[0-9a-f]{3,6})\b/,
        WHERE_W = /\b(hood|roof|trunk|spoiler|bumpers?|doors?|sides?|fenders?|quarters?|front|rear|wings?|splitter|nose|bonnet|tailgate|cab|car|truck|body|everything|whole|all|base|logos?|layer)\b/;
    function clearRequest(text) {
        var t = String(text == null ? '' : text); if (/\?\s*$/.test(t) || /^\s*(how|what|whats|why|which|where|when|is|are|does|do i|should|can i|could i)\b/i.test(t)) return false;
        var c = (t + ' ' + clean(t).text).toLowerCase().replace(/\b(?:no|not|without|never|more|less|too|any)\s+\w+/g, ' '); return LOOK_W.test(c) && WHERE_W.test(c);          // "no gold" / "more red" are not a look to paint
    }
    function retryHint(fc, text, env) {
        if (!fc) return null; var f = fc.frame, reps = (fc.repairs || []).join(' ');
        if (/\(S6|\(S7b|never said|first request|a question|rule 3d|no earlier change/.test(reps)) return null;
        var none = !fc.ok || !f || f.act === 'ask_back' || f.act === 'nothing' || (f.act === 'change' && !arr(f.ops).length);
        if (!none || !clearRequest(text)) return null;
        var c = clean(text);
        return 'APP CHECK: your frame changed nothing, but this turn is a clear request' + (c.fixes.length ? ' (read as: "' + c.text + '")' : '') + ': it names the look and the place. Send act "change" with one op per clause. ask_back only when the place or the look is really missing.';
    }
    function betterFrame(fc2, fc1) { return !!(fc2 && fc2.ok && fc2.frame && fc2.frame.act === 'change' && arr(fc2.frame.ops).length); }
    var CONCEPT_ALIAS = [[/^(galaxy|space|nebula|cosmic|cosmos|starry|night sky)$/, 'stardust'], [/^(mud|muddy|dirt|dirty|grime|grimy|filth|filthy|mud splatter|dirt splatter)$/, 'grunge splatter']];          // (rust -> patina dropped: on p1 it turned a follow-up ask into a whole-car rust repaint, A-0241-p1)
    // ------------------------------------------------------------------ catalogue ids for words the planner cannot map itself (deterministic host lookups, no model round)
    function toks(s) { return low(s).split(/[^a-z0-9]+/).filter(function (w) { return w.length >= 3; }).map(function (w) { return w.slice(0, 5); }); }
    function shares(row, q) { var hay = toks((row.key || row.id || '') + ' ' + (row.name || '')), qt = toks(q); return qt.some(function (t) { return hay.indexOf(t) !== -1; }); }
    function resolveLooks(frame, find) {
        var notes = []; if (!frame || typeof find !== 'function') return notes;
        var P = W.SpbIntentPlan;
        arr(frame.ops).forEach(function (op) {
            var L = op.look || {};
            if (L.pattern && !L.pattern.id && L.pattern.concept && !/flame/.test(L.pattern.concept)) {
                var r = []; try { r = find({ query: L.pattern.concept, type: 'pattern', limit: 4 }) || []; } catch (e) {}
                var hit = r.filter(function (x) { return shares(x, L.pattern.concept); })[0];
                if (!hit) CONCEPT_ALIAS.forEach(function (al) { if (hit || !al[0].test(L.pattern.concept)) return; var r3 = []; try { r3 = find({ query: al[1], type: 'pattern', limit: 4 }) || []; } catch (e3) {} hit = r3.filter(function (x) { return shares(x, al[1]); })[0]; });          // S7c: mud / galaxy / rust
                if (hit) { L.pattern.id = hit.key || hit.id; notes.push('pattern "' + L.pattern.concept + '" -> ' + L.pattern.id); } else notes.push('no catalogue pattern for "' + L.pattern.concept + '"');
            }
            if (L.finish && !L.finish.key && L.finish.family && P && P.finishKey) {
                var keep = L.finish.keep_colour === true || (!L.colour && !L.gradient && !L.pattern), fk = P.finishKey(L.finish, false);
                if (!fk && !keep) { var q = (L.colour && L.colour.word ? L.colour.word + ' ' : '') + L.finish.family, r2 = []; try { r2 = find({ query: q, type: 'finish', limit: 4 }) || []; } catch (e2) {} var h2 = r2.filter(function (x) { return shares(x, L.finish.family); })[0]; if (h2) { L.finish.key = h2.key || h2.id; notes.push('finish "' + q + '" -> ' + L.finish.key); } }
            }
        });
        return notes;
    }
    function replyOf(pl) {
        if (!pl) return ''; if (pl.act === 'ask_back' && pl.ask) return pl.ask.q;
        if (pl.act === 'change') return 'Done: ' + pl.steps.map(function (s) { return s.label; }).filter(Boolean).join('; ') + '.' + ((pl.notes || []).length ? ' (' + pl.notes.join('; ') + ')' : '');
        return '';
    }

    W.SpbIntentModel = { VERSION: VERSION, LOOKUPS: LOOKUPS, on: on, mode: mode, flag: flag, schema: schema, submitTool: submitTool, tools: tools, toolChoice: toolChoice, SYSTEM: SYSTEM,
        userMessage: userMessage, clean: clean, retryHint: retryHint, betterFrame: betterFrame, clearRequest: clearRequest, fromCall: fromCall, resolveLooks: resolveLooks, replyOf: replyOf, _norm: { tgt: tgtNorm, look: lookNorm, op: opNorm, part: normPart, hex: hexNorm } };
})();
