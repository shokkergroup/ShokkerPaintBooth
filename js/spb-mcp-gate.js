/* ============================================================================
   M2 2026-10-07 (lane M2, MCP CONNECTOR FIXES; eval in _easy_claude_work/eval/m2/REPORT.md): THE MCP ASK-FIRST GATE.
   M1 (Claude sonnet + this MCP, 30 TRAIN items): 6 of 8 HARM items were Claude ACTING on vague / mood / reference / complaint requests
   ("make it pop on TV", "looks plastic man", "pastel livery for a charity race", "Brazil colours", "like the car that won Daytona 2019",
   "mud on the bottom"): spb_apply_scheme / spb_add_zone / spb_edit_zone had no ask-gate. Owner rule: vague = offer 2-3 concrete options or ask
   ONE question first; never paint a whole scheme unasked (exception: "surprise me / just do it"); complaints = answer + offer a fix, never auto-apply.
   This file runs in the page BEFORE any MCP write tool (js/spb-pro-ai.js mcpCallCore) and decides from the buyer's own words (buyer_said, or
   spb_do text) plus the scope of the call:
     classify(text)              -> {cls: go|concrete|vague|complaint|question|trouble, why, topic}
     gate(tool, args, host)      -> null (go on) or an ask_back result {changed:false, ask_back:{why, question, options[]}, rule}
     partsCheck(parts, text)     -> null or {unnamed:[part], named:[part], ref:[part]}   (A-0597: "make the right door like the left" recoloured both)
     mcpSchema(name, schema)     -> the MCP-only buyer_said / confirm properties added to a write tool's schema (list_tools)
   Whole-car scope (apply_scheme always; add/edit_zone covering everything / remaining / the paintable area / only body layers / an edited zone that
   shows on >= 18% of the sheet (~30% of the car); refinish of the main colour; spb_do on the body) needs confirm:true as well as non-vague words.
   Global: window.SpbMcpGate (ES5; classify / partsCheck / gate run in Node too: _easy_claude_work/eval/m2/gate_unit.js).
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var VERSION = '2026-10-07-m3';          // M3 2026-10-07: typo-tolerant part words, short more/less follow-ups = correction
    function arr(x) { return Array.isArray(x) ? x : (x == null ? [] : [x]); }
    function low(t) { return String(t == null ? '' : t).toLowerCase().replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim(); }

    // ------------------------------------------------------------------ vocabulary
    var COLOUR_RE = /#[0-9a-f]{6}\b|#[0-9a-f]{3}\b|\b(red|blue|green|yellow|orange|purple|pink|black|white|gr[ae]y|silver|gold|golden|navy|teal|cyan|aqua|magenta|maroon|brown|tan|beige|cream|ivory|lime|mint|turquoise|bronze|copper|burgundy|crimson|scarlet|violet|lavender|lilac|indigo|cobalt|charcoal|graphite|olive|khaki|sand|peach|coral|salmon|ruby|emerald|sapphire|amber|mustard|fuchsia|ferrari red|gulf blue|british racing green|gr[ae]yscale|monochrome|black and white)\b/;
    var FINISH_RE = /\b(matte?|flat black|satin|gloss(y)?|chrome|pearl(escent)?|metallic|metal ?flake|flake|candy|carbon( fib(er|re))?|holo(graphic)?|brushed|glitter|sparkle|prizm|chameleon|iridescent|powder ?coat|plasti ?dip|cerakote|vinyl|wrap|frosted|anodi[sz]ed|camo|spec|shiny|shinier|shine|mirror|metal|metallic feel|wet look|dull(er)?)\b/;
    var TARGET_RE = /\b(hood|bonnet|roof|trunk|deck ?lid|spoiler|wing|bumpers?|sides?|doors?|fenders?|quarter( panels?)?|rockers?|skirts?|numbers?|digits?|sponsors?|logos?|decals?|stripes?|pin ?stripes?|pin ?lines?|bands?|base|body|whole car|entire car|everything|everywhere|all over|top|bottom|lower|upper|front|rear|nose|tail|two[- ]?tone|beltline|outline|gradient|fade|layer|zone|mirrors?|windows?|roof ?line)\b/;
    var VERB_RE = /\b(make|change|turn|paint|set|put|add|remove|delete|recolou?r|swap|replace|use|apply|give|switch|tint|darken|lighten|brighten|thin|thicken|move|copy|match|undo|redo|hide|show|outline|fill|drop|get rid of|take off|bring back|convert|desaturate|saturate|warm up|cool down|tone)\b/;
    var RELATIVE_RE = /\b(darker|lighter|brighter|duller|dimmer|softer|bolder|thinner|thicker|bigger|smaller|wider|narrower|less|more|glossier|shinier|flatter|tone (it|that|them|the \w+) down|turn (it|that) down|a (bit|touch|tad)|slightly|warmer|cooler|desaturate[d]?|more saturated)\b/;
    var GO_RE = /\b(surprise me|just do it|go ahead|go for it|do it|yes|yeah|yep|yup|sure|sounds good|looks good|ok(ay)?|that one|this one|the (first|second|third|last|1st|2nd|3rd|other) (one|option|idea|was|is|look|version)|(option|number|idea) ?[1-4a-c]\b|apply (it|that)|your call|up to you|you pick|you choose|whatever you (think|want|like)|dealer'?s choice|i trust you|send it|let'?s (do|go|see)|make it so|run with it|perfect)\b/;
    // mood / taste words: on their own they do not say WHAT to change
    var MOOD_RE = /\b(pop|pops|popping|stand out|stands out|cool|sick|fresh|dope|lit|fire|badass|aggressive|angry|kind|friendly|cute|happy|fun|classy|elegant|premium|expensive|luxur(y|ious)|rich|unique|different|special|original|nobody has|no one has|noone has|never seen|something (new|cool|kind|different|nice|special|unique|crazy|wild|fresh|clean|else)|vibes?|feel|on tv|on camera|on stream|on the broadcast|better|nicer|prettier|awesome|amazing|epic|wild|crazy|insane|stealthy|menacing|tough|sporty|pastel|earthy|moody|vintage|retro|old ?school|throwback|charity|tribute|memorial|theme|themed)\b/;
    // a reference: copy a real car / country / team / brand look (needs the buyer's colours + layout, or a question)
    var NAMED_LIVERY_RE = /\b(gulf|martini|repsol|j[aä]germeister|jager|jps|john player( special)?|marlboro|rothmans|castrol|red ?bull|monster( energy)?|pepsi|coca[- ]?cola|coke|stp|lucky strike|camel|valvoline|pennzoil|havoline|texaco|sunoco|kodak|mobil ?1?|shell|budweiser|miller lite|petty blue|tide|skittles|m ?& ?m'?s|dupont|goodwrench|interstate batteries|hooters)\b/;          // M2 2026-10-07
    var COUNTRY_VAGUE_RE = /\b(brazil(ian)?|brasil|ital(y|ian)|german(y)?|french|france|british|britain|english|england|american|usa|america|mexic(o|an)|japan(ese)?|dutch|netherlands|holland|swed(en|ish)|spain|spanish|irish|ireland|australia(n)?|aussie|canad(a|ian)|argentin(a|ian))\b[^.]{0,20}\b(colou?rs?|theme|look|scheme|style|vibe|paint)\b|\bpatriotic\b/;          // C-OFFVAGUE 2026-10-08
    var MOOD2_RE = /\b(fast|speed(y)?|quick|mean|menacing|scary|tough|fierce|brutal|savage|racy|sporty|powerful|pastel|soft|gentle|calm|retro|vintage|old ?school|throwback|moody|sinister|stealthy|modern|futuristic|sleek|fancy|posh|sophisticated|summery|dreamy|personality|flair|swag)\b/;          // C-OFFVAGUE 2026-10-08
    var REF_RE = /\b(the car that|car (that|which) won|that won|won (the|at|in)|winning car|winner'?s? car|champion(ship)? car|tribute|replica|inspired by|in the style of|based on (the|a|his|her|their)|like my country|my country|my flag|national team|team colou?rs|livery from|from (the )?(movie|film|game|show)|like (the|his|her|their) (car|livery|truck|scheme) (of|from|that|in)|like (\w+ )?(\w+)'s (car|livery|truck))\b/;
    // an effect that has no single built-in meaning (where? how much? which look?)
    var EFFECT_RE = /\b(mud|muddy|dirt|dirty|rust|rusty|weathered|worn|battle[- ]?scarred|scratch(es|ed)?|dent(s|ed)?|patina|grime|grimy|dust(y)?|bugs|tire marks|rubber marks|aged|beat ?up|used look|race worn)\b/;
    var COMPLAINT_RE = /\b(looks?|looking|feels?|seems?|is|are|it'?s|its|kinda|so|too) (so |too |kinda |kind of |very |really |a bit |a little |pretty |super )?(plastic|cheap|fake|flat|dull|boring|off|weird|wrong|bad|meh|bland|washed ?out|muddy|busy|cluttered|toy ?like|messy|ugly|plain|dark|bright|shiny|loud|dead|lifeless)\b|\bhard to (read|see|tell)\b|\bcan'?t (read|see|tell)\b|\b(ugly|hideous|garbage|trash|sucks|terrible|awful|hate it|don'?t like (it|this|that)|1 star|one star|refund|uninstall|still boring|so boring|this (looks|is) bad)\b/;
    var GENERIC_RE = /\b(idk|i don'?t know( what)?|not sure what|no idea what|help me|i need help|can you help|fix (it|this)|make (it|the car|my car) (look )?(good|better|nice|right|great)|look good|something like|pick (the |some )?colou?rs|choose (the |some )?colou?rs|i want (to )?change the colou?r|can i change the colou?r|change the colou?r)\b/;
    var TROUBLE_RE = /\b(render(ed|s|ing)?|iracing|in the sim|in sim|tga|\.mip|export(ed)?|save[ds]?|files?|folder|crash(ed|es)?|error|bug|updated?|won'?t|doesn'?t (show|load|work|appear)|not (showing|loading|working)|missing|disappeared|trading paints|rendr|after (i|the) updat\w*|old projects?|slow|lag(gy|s)?|preview (just )?shows|vanished|failed|fails|cannot do|can'?t do it|stuck|freez\w*|black screen|grey screen|gray screen)\b/;
    var IMPERATIVE_RE = /\b(make|paint|change|turn|put|give|set|recolou?r) (it|the|my|them|this|that|all|both|those|these)\b/;
    var QSTART_RE = /^(should|what|which|how|why|where|when|who|does|do i|do you|whats|what'?s|is (it|there|this|that|the|my|a|metallic|matte|gloss)|are (there|the|my|these)|any idea)\b/;
    var QUESTION_RE = /\?\s*$|^(should|what|which|how|why|where|when|who|does|do i|do you|whats|what'?s|is (it|there|this|that|the|my|a|metallic|matte|gloss)|are (there|the|my|these)|any idea)\b/;
    var SUGGEST_RE = /^(what if|how (about|bout)|can i get|could i get|can we|could we|let'?s)\b/;
    var REQUEST_Q_RE = /^(can|could|would|will) (you|u|ya)\b|^(please|pls)\b/;
    var WHOLE_WORD_RE = /\b(both|all|whole|entire|every|everywhere|everything|all over|sides|doors|bumpers|full car|the car|the body)\b/;

    // ------------------------------------------------------------------ classify the buyer's words
    var SPECIFIC_PART_RE = /\b(hood|bonnet|roof|trunk|deck ?lid|spoiler|wing|bumpers?|sides?|side panels?|doors?|fenders?|quarter( panels?)?|rockers?|skirts?|bed|tailgate|panels?)\b/;
    // M3 2026-10-07 (class OVER-ASKING on typos; train A-0445 "dirt on the lower doros", A-0097 "trunnk", A-0094 "rgiht door", A-0326 "bumpper"): a misspelt part word hid the part,
    // so "<effect> on the <part>" read as a vague effect and was refused. Words of 5+ letters one edit (Damerau) from a part word are read as that word; real words that sit one edit
    // from a part word (light, sight, sizes ...) are never touched.
    var TYPO_WORDS = ['doors', 'sides', 'bumper', 'bumpers', 'trunk', 'spoiler', 'fender', 'fenders', 'right', 'bonnet', 'mirrors', 'windows', 'bottom', 'lower', 'quarter', 'rocker', 'rockers', 'numbers', 'sponsors', 'stripes', 'chrome', 'matte', 'satin', 'glossy', 'metallic', 'pearl', 'carbon', 'purple', 'yellow', 'orange', 'silver', 'green'];
    var TYPO_KEEP = /^(coors|slower|flower|blower|glower|gloss|light|bright|fright|wright|alright|might|sight|fight|tight|eight|night|wight|bight|sizes|tides|rides|wides|aides|sider|bumped|bummer|lover|lowed|power|tower|mower|cower|bother|botton|motte|matter|mattes|satan|patin|pears|pearls|metal|carton|cartoon|silvery|greens|greene|orangy|stripe|strips|trunks|drunk|truck|spoilt|tender|render|lender|fenced|chrom|rocket|rockets|socket|docker|locker|rocky|quarters|quartet|window|mirror|number|sponsor|doers|odors|ripe)$/;
    function dam1(a, b) {          // Damerau-Levenshtein distance <= 1 ?
        if (a === b) return true; var la = a.length, lb = b.length; if (Math.abs(la - lb) > 1) return false;
        var i = 0; while (i < la && i < lb && a[i] === b[i]) i++;
        if (la === lb) return a.slice(i + 1) === b.slice(i + 1) || (a[i] === b[i + 1] && a[i + 1] === b[i] && a.slice(i + 2) === b.slice(i + 2));
        return la > lb ? a.slice(i + 1) === b.slice(i) : a.slice(i) === b.slice(i + 1);
    }
    function fixTypos(t) {
        return String(t || '').replace(/[a-z]{5,}/g, function (w) {
            if (TYPO_WORDS.indexOf(w) !== -1 || TYPO_KEEP.test(w)) return w;
            for (var i = 0; i < TYPO_WORDS.length; i++) if (dam1(w, TYPO_WORDS[i])) return TYPO_WORDS[i];
            return w;
        });
    }
    function classify(text, opts) {
        var t = fixTypos(low(text)); if (!t) return { cls: 'none', why: 'no buyer words' };
        var hasLook = COLOUR_RE.test(t) || FINISH_RE.test(t), hasTarget = TARGET_RE.test(t), hasVerb = VERB_RE.test(t) || RELATIVE_RE.test(t), go = GO_RE.test(t);
        var tNoPartRef = t.replace(/\b(like|same as|match(es|ing)?|as on|as)\s+(the\s+)?(left|right|other|hood|roof|trunk|spoiler|front|rear|driver|passenger)\b/g, ' ');
        if (/\b(surprise me|just do it|dealer'?s choice|you pick|you choose|up to you|your call|whatever you (think|want|like)|i trust you|go (crazy|wild|nuts)|do something (cool|crazy|wild|fun|nice|different|creative)|(pick|choose|decide|design) (a |the |one |something )?(colou?r scheme |scheme |look |one )?for me|(anything|whatever) (is )?(fine|goes|works))\b/.test(t)) return { cls: 'go', why: 'the buyer handed the choice to you', topic: 'go' };
        var qs = QSTART_RE.test(t), isQ = QUESTION_RE.test(t) && !REQUEST_Q_RE.test(t) && !SUGGEST_RE.test(t) && !IMPERATIVE_RE.test(t) && !(go && !qs);
        if (TROUBLE_RE.test(t) && !(hasLook && hasTarget && hasVerb)) return { cls: 'trouble', why: 'a render / iRacing / file problem, not a paint change', topic: 'trouble' };
        if (isQ) return { cls: 'question', why: 'the buyer asked a question', topic: 'question' };
        var corr = !!(opts && opts.recent) && /^(\w+[,.!]? )?(too|so|way too|a bit too|still too) \w+\.?$|^(nah|nope|no)[,.!]? (too|it'?s too|way too|still) \w+/.test(t);          // "nah too bright" right after a change = a relative correction of THAT change
        // M3 2026-10-07 (class OVER-ASKING on follow-ups; train A-0445 "more dirt" / "ok a bit less", A-0097 "smaller again" right after a change): a short MORE / LESS / SMALLER
        // follow-up of the last change is a correction of THAT change, not a new vague effect
        if (!corr && !!(opts && opts.recent) && t.split(' ').length <= 5 && /^(ok(ay)?[,.!]? |now |and |then |a (bit|little|touch) |bit |way |much |even )*(more|less|smaller|bigger|larger|tinier|lighter|darker|brighter|stronger|weaker|thinner|thicker|subtler)\b/.test(t) && !QUESTION_RE.test(t)) corr = true;
        if (!corr && !!(opts && opts.recent) && t.split(' ').length <= 5 && /^(ok(ay)?[,.!]? |now |and |then )*(again|another( one)?|different|something (else|different)|try again|new one|redo( it)?)\b/.test(t) && !QUESTION_RE.test(t)) corr = true;
        if (corr) return { cls: 'concrete', why: 'a short correction of the last change', topic: 'correction' };
        if (COMPLAINT_RE.test(t) && !(hasVerb && (hasLook || hasTarget)) && !go) return { cls: 'complaint', why: 'a complaint about how it looks, not a change request', topic: /read|see|tell/.test(t) ? 'readable' : (/plastic|cheap|fake|flat|dull|boring|bland|plain|dead|lifeless|toy/.test(t) ? 'plastic' : 'taste') };
        // M2 run 2 2026-10-07 (train A-0081 "make the car look like a Martini livery" = act): a NAMED classic livery has a known palette + layout (spb_design_recipes has them): concrete, not a mood
        if (NAMED_LIVERY_RE.test(t) && !REF_RE.test(tNoPartRef)) return { cls: 'concrete', why: 'a named classic livery (known palette and layout)', topic: 'named_livery' };
        if (GENERIC_RE.test(t) && !(hasLook && (hasTarget || hasVerb)) && !go) return { cls: 'vague', why: 'no colour, finish or place named yet', topic: 'mood' };
        if (EFFECT_RE.test(t) && !SPECIFIC_PART_RE.test(t) && !go) return { cls: 'vague', why: 'an effect with no single built-in look (which look, where, how strong?)', topic: 'effect' };
        var concreteLayout = hasLook && hasTarget, enough = (hasLook && (hasTarget || hasVerb)) || (RELATIVE_RE.test(t) && hasTarget);
        if (REF_RE.test(tNoPartRef) && !concreteLayout && !go) return { cls: 'vague', why: 'a reference to a real car / country / brand look: its colours and layout are a guess', topic: 'reference' };
        // C-OFFVAGUE 2026-10-08 (owner rule): a COUNTRY / flag-colour ask with no colour named ('Brazil colours', 'italian colours', 'a patriotic look') and a plain taste ask ('make it look fast') change nothing: vague
        if (COUNTRY_VAGUE_RE.test(t) && !hasLook && !concreteLayout && !go) return { cls: 'vague', why: 'a country / flag colour ask: which colours, where and what finish are a guess', topic: 'reference' };
        if (MOOD2_RE.test(t) && !hasLook && !hasTarget && !go && !/\b(undo|redo|render|export|save)\b/.test(t)) return { cls: 'vague', why: 'a taste word with no colour and place named', topic: 'mood' };
        if (MOOD_RE.test(t) && !enough && !go) return { cls: 'vague', why: 'a mood / taste word with no colour and place named', topic: /pop|stand out|tv|camera|stream|broadcast/.test(t) ? 'pop' : 'mood' };
        if (/\b(liver(y|ies)|scheme|design|paint ?job|redo (it|the car)|redesign)\b/.test(t) && !hasLook && !go) return { cls: 'vague', why: 'a whole livery with no colours named', topic: 'mood' };
        if (go) return { cls: 'go', why: 'the buyer approved / chose', topic: 'go' };
        return { cls: 'concrete', why: 'a concrete request', topic: 'concrete' };
    }

    // ------------------------------------------------------------------ the parts named in the words (unnamed-part check, A-0597)
    var PART_WORDS = {
        'left side': /\b(left|driver'?s?|drivers)( side| door| doors| panel| quarter| fender| flank)?\b/,
        'right side': /\b(right|passenger'?s?|passengers)( side| door| doors| panel| quarter| fender| flank)?\b/,
        'hood': /\b(hood|bonnet)\b/, 'roof': /\broof\b(?! ?line)/, 'trunk': /\b(trunk|deck ?lid|boot lid|rear deck)\b/, 'spoiler': /\b(spoiler|wing)\b/,
        'front bumper': /\b(front bumper|front fascia|nose|splitter|front end)\b/, 'rear bumper': /\b(rear bumper|rear fascia|diffuser|rear end|tail ?end)\b/
    };
    var BOTH_SIDES_RE = /\b(both|sides|doors|flanks|all|whole|entire|every|everywhere|everything|all over|the body|the car|each side|either side)\b/;
    function partsInText(text) {
        var t = fixTypos(low(text)), named = [], ref = [];          // M3 2026-10-07: typo-tolerant ("rgiht door")
        // a part that is only the REFERENCE ("same as the left", "like the hood", "left door is #FFD100", "the left already is yellow")
        Object.keys(PART_WORDS).forEach(function (p) {
            var re = PART_WORDS[p], g = new RegExp(re.source, 'g'), m, asTarget = false, asRef = false;
            while ((m = g.exec(t))) {
                var before = t.slice(Math.max(0, m.index - 22), m.index), after = t.slice(m.index + m[0].length, m.index + m[0].length + 30);
                var isRef = /(same as|like|match(es|ing)?|as on|copy( from)?|from|identical to|similar to|as)\s+(the\s+)?$/.test(before) || /^\s*(door|side|panel)?\s*(is|are|was|already is|already has|has|have)\s+(already\s+)?(#[0-9a-f]{3,6}|[a-z]+ ?(colou?r)?\b)/.test(after) && !/^\s*(door|side|panel)?\s*(is|are)\s+(the same|same|not|different|boring|ugly|plain|dull|bland|bad|meh|weak|lame|blank|empty|messy|too|so|kinda|kind of|really|very|pretty|a bit|looking|looks)/.test(after);
                if (isRef) asRef = true; else asTarget = true;
            }
            if (asTarget) named.push(p); else if (asRef) ref.push(p);
        });
        return { named: named, ref: ref, both: BOTH_SIDES_RE.test(t), text: t };
    }
    function partsCheck(parts, text) {
        var ps = arr(parts).map(function (p) { return low(p); }).filter(Boolean); if (ps.length < 1 || !low(text)) return null;
        var pi = partsInText(text); if (!pi.named.length && !pi.ref.length) return null;          // the words name no part at all: nothing to compare (the frame came from context)
        var unnamed = ps.filter(function (p) {
            if (pi.named.indexOf(p) !== -1) return false;
            if (pi.ref.indexOf(p) !== -1) return true;          // named only as the reference ("same as the left")
            if (pi.both && (p === 'left side' || p === 'right side') && (pi.named.indexOf('left side') !== -1 || pi.named.indexOf('right side') !== -1 || /\b(sides|doors|flanks|both)\b/.test(pi.text))) return false;
            if (pi.both && /\b(all|whole|entire|every|everywhere|everything|all over|the body|the car)\b/.test(pi.text)) return false;
            return pi.named.length > 0;          // other parts were named, this one was not
        });
        return unnamed.length ? { unnamed: unnamed, named: pi.named, ref: pi.ref } : null;
    }

    // ------------------------------------------------------------------ scope of a write call
    var WRITE = { reset_zones: 1, apply_scheme: 1, add_zone: 1, edit_zone: 1, duplicate_zone: 1, add_graphic: 1, refinish: 1, do: 1, mark_elements: 0, edit_layer: 0 };
    function regionWhole(r, host) {
        if (!r || typeof r !== 'object') return false;
        if (r.everything || r.remaining || r.paintable) return true;
        if (r.part || r.island || r.cells || r.rect || r.element || r.graphic || r.box || (r.colors && r.colors.length)) return false;
        var ls = arr(r.layers); if (!ls.length) return false;
        var body = []; try { body = (host && host.bodyLayers) ? host.bodyLayers() : []; } catch (e) {}
        return body.length > 0 && ls.every(function (l) { return body.indexOf(String(l)) !== -1; });
    }
    function wholeScope(tool, args, host) {
        args = args || {};
        if (tool === 'apply_scheme') return 'a whole paint scheme';
        if (tool === 'reset_zones') return 'removing zones for a fresh start';          // RESET-ZONES 2026-10-09
        if (tool === 'add_zone' && regionWhole(args.region, host)) return 'a new zone over the whole car';
        if (tool === 'edit_zone' || tool === 'duplicate_zone') {
            if (args.region && regionWhole(args.region, host)) return 'a zone re-aimed at the whole car';
            var pct = null; try { pct = host && host.zoneShare ? host.zoneShare(args) : null; } catch (e) {}
            if (pct != null && pct >= 18) return 'a zone that shows on ' + Math.round(pct) + '% of the paint sheet (whole-car size)';          // visible_pct is a share of the 2048 sheet; the car is ~55-60% of it
        }
        if (tool === 'refinish' && !args.part && !(args.boxes && args.boxes.length) && /^(main colou?r|body|car|everything|whole( car)?|all|paint)$/i.test(String(args.target || '').trim())) return 'the main colour of the whole car';
        if (tool === 'do') {
            var fr = args.frame; if (typeof fr === 'string') { try { fr = JSON.parse(fr); } catch (e2) { fr = null; } }
            var whole = fr && arr(fr.ops).some(function (o) { var t = o && o.target || {}; return t.kind === 'body' || (t.kind === 'colour' && !arr(t.parts).length && !arr(t.layers).length) || arr(t.parts).length >= 5; });
            if (whole) return 'a change to the whole car body';
        }
        return null;
    }

    // ------------------------------------------------------------------ concrete options to offer (the buyer picks; nothing is applied)
    function optionsFor(c, tool, args) {
        var tp = c && c.topic;
        if (tp === 'plastic') return ['Metal flake under the clearcoat on the body (shine only, colours stay)', 'Pearl body with gloss stripes (shine only)', 'Satin body + gloss trim so the shapes read (shine only)'];
        if (tp === 'readable') return ['A thick contrasting outline around the numbers', 'Recolour the numbers to contrast with the body behind them', 'Calm the body colour behind the numbers'];
        if (tp === 'pop') return ['One loud accent colour on the stripes / bumpers against a calm body', 'Chrome or candy trim on the accents (shine contrast)', 'A brighter body colour with dark contrast trim'];
        if (tp === 'effect') return ['A dirt / mud texture low on the sides and bumpers only', 'A light weathered spec (dull, rough) on the lower body, colours stay', 'Leave it clean'];
        if (tp === 'reference') return ['Tell me the 2-3 main colours and where they go (body, stripes, bumpers)', 'I propose a layout with those colours (for example white body, colour band low on the sides, colour bumpers) and you approve it', 'Only the colours, keep your current layout'];
        if (tool === 'apply_scheme') {
            var pal = args && args.palette ? Object.keys(args.palette).map(function (k) { return k + ' ' + args.palette[k]; }).join(', ') : (args && args.palette_id) || 'your colours';
            return ['The ' + (args && args.preset || 'scheme') + ' layout in ' + pal, 'A simpler two-tone (body + one band) in the same colours', 'Only the body colour, keep everything else'];
        }
        return ['Option A: a light-touch version on one part', 'Option B: the full change you described', 'Something else: tell me the colour / finish and the part'];
    }
    var LAST_BLOCK = null;          // M2 run 2: the last buyer words the gate refused (see gate())
    function norm(t) { return low(t).replace(/["'`\u201c\u201d]/g, '').replace(/[^a-z0-9#]+/g, ' ').trim(); }
    function askBack(kind, c, tool, args, scope) {
        var q, why = c ? c.why : '';
        if (kind === 'no_words') return { changed: false, ask_back: { why: 'buyer_said is missing', question: null, options: [] }, rule: 'NOTHING was changed. Pass buyer_said = the buyer\'s own words for this change (quote them; when they refer back, e.g. "make it so", include the earlier line). Then call again.' };
        if (kind === 'confirm') {
            q = 'This changes ' + scope + '. Did the buyer ask for exactly this?';
            return { changed: false, ask_back: { why: scope, question: q, options: optionsFor(c, tool, args) }, rule: 'NOTHING was changed. Whole-car changes need confirm:true. Set it ONLY when the buyer\'s own words (buyer_said) name the colours / finish and the whole car or layout, approved your proposal, or said "surprise me / just do it". Otherwise offer the buyer these 2-3 options in your own words and STOP.' };
        }
        var lead = { vague: 'The buyer\'s words do not say exactly what to change', complaint: 'This is a complaint, not a change request', question: 'The buyer asked a question', trouble: 'This is a render / iRacing / file problem, not a paint change' }[kind] || 'Not a clear change request';
        var rule = kind === 'question' ? 'NOTHING was changed. Answer the question (spb_encyclopedia for how-to), then offer to make the change and wait.'
            : kind === 'trouble' ? 'NOTHING was changed. Diagnose with spb_check_setup / spb_encyclopedia and answer; do not repaint.'
            : kind === 'complaint' ? 'NOTHING was changed. Answer the complaint in one or two sentences, offer these fixes, ask which one, and STOP. Apply only after the buyer picks.'
            : 'NOTHING was changed. Ask the buyer ONE short question or offer these 2-3 concrete options, then STOP. Apply only after they pick (or say "surprise me / just do it").';
        return { changed: false, ask_back: { why: lead + ' (' + why + ').', question: kind === 'question' ? null : 'Which of these would you like?', options: kind === 'question' || kind === 'trouble' ? [] : optionsFor(c, tool, args) }, rule: rule };
    }

    // lane R3-EDIT-2 2026-10-07 item 4 (MCP A-0192 'Ferrari red': Claude recoloured the catch-all AND the pink accent zone 'GTA Pink - Ocean Waves' with spb_edit_zone + confirm):
    // a whole-car colour request keeps the accent zones the buyer did not name (spb_do already does, plan J2W). Kill switch: window.SPB_MCP_NOACCENTKEEP
    var ALLART_RE = /\b(everything|every ?thing|all (the |of the )?colou?rs|every colou?r|all of it|solid|one colou?r|single colou?r|accents?|stripes?|trim|graphics?|art|details|including|whole livery)\b/;
    function accentKeep(tool, args, host, said) {
        if (tool !== 'edit_zone' || W.SPB_MCP_NOACCENTKEEP) return null;
        if (!(args.color || args.colour || args.gradient || args.base_color)) return null;
        var ai = null; try { ai = host && host.accentInfo ? host.accentInfo(args) : null; } catch (e) { ai = null; }
        if (!ai || !ai.accent) return null;
        var t = fixTypos(low(said)); if (!t || !COLOUR_RE.test(t)) return null;
        if (partsInText(t).named.length || ALLART_RE.test(t)) return null;
        if (ai.words.some(function (w) { return new RegExp('\\b' + w + 's?\\b').test(t); })) return null;
        return { changed: false, kept_accent: ai.name, rule: 'NOTHING was changed. Zone "' + ai.name + '" is ACCENT art (' + ai.pct + '% of the sheet' + (ai.family ? ', ' + ai.family : '') + ') and the buyer\'s words ("' + String(said).slice(0, 80) + '") ask for a whole-car colour without naming it: a whole-car colour change KEEPS the accents. Change only the main body zone' + (ai.main ? ' ("' + ai.main + '")' : '') + ', or call spb_do with the buyer\'s words. Recolour this zone only when the buyer names it (its colour, "the accents", "everything").' };
    }
    // ------------------------------------------------------------------ the gate
    function gate(tool, args, host) {
        tool = String(tool || ''); args = args || {};
        if (!WRITE[tool]) return null;
        try { if (W.SPB_MCP_GATE === '0' || W.SPB_MCP_GATE === 0 || W.SPB_MCP_GATE === false) return null; } catch (e0) {}
        var said = tool === 'do' ? (args.buyer_said || args.text) : args.buyer_said;
        var scope = wholeScope(tool, args, host);
        var recent = false; try { recent = !!(host && host.recent && host.recent()); } catch (eR) {}
        // M2 run 2 2026-10-07 (train B-0288 "everything you suggest is ugly. just give me ONE good design": after an ask_back Claude re-sent buyer_said as those words + "approving my proposal:
        // Gulf livery ... just do it", then muted six of the buyer's zones with "<words> - clearing the old ..."): buyer_said that CONTAINS words the gate just refused, plus more, is read as
        // the refused words alone (the additions are the caller's, not the buyer's) for 10 minutes or until different buyer words arrive.
        var nsaid = norm(said), padded = false;
        if (LAST_BLOCK && Date.now() - LAST_BLOCK.at < 600000 && nsaid !== LAST_BLOCK.said && nsaid.indexOf(LAST_BLOCK.said) !== -1) { said = LAST_BLOCK.raw; padded = true; }
        var c = classify(said, { recent: recent });
        if (c.cls === 'none') return askBack('no_words', c, tool, args, scope);
        if (c.cls === 'vague' || c.cls === 'complaint' || c.cls === 'question' || c.cls === 'trouble') {
            if (!padded && nsaid.length >= 6) LAST_BLOCK = { said: nsaid, raw: String(said), at: Date.now() };
            var ab = askBack(c.cls, c, tool, args, scope); if (padded && ab) ab.rule = 'NOTHING was changed. buyer_said must be the buyer\'s own latest words, verbatim: words you add to it (a proposal, "approving", "just do it") are not theirs and are ignored. Ask the buyer and wait for their answer. ' + (ab.rule || ''); return ab;
        }          // the buyer's NEXT words (their pick: "the chrome one", "yes", "option 2") pass
        var akp = accentKeep(tool, args, host, said); if (akp) return akp;          // lane R3-EDIT-2 2026-10-07 item 4: before the confirm check (confirm:true does not lift it)
        if (scope && c.cls !== 'go' && args.confirm !== true) return askBack('confirm', c, tool, args, scope);
        return null;
    }

    // ------------------------------------------------------------------ MCP-only schema additions (list_tools)
    var SAID_DESC = 'REQUIRED: the buyer\'s own words for this change, quoted (add the earlier line when they refer back: "make it so"). The app reads them: vague / mood / reference / complaint words return ask_back and change nothing.';
    var CONFIRM_DESC = 'true only when the buyer\'s words ask for exactly this whole-car change (colours/finish + layout named), approved your proposal, or said "surprise me / just do it".';
    function mcpSchema(name, schema) {
        var app = String(name || '').replace(/^spb_/, ''); if (!WRITE[app]) return schema;
        var s = JSON.parse(JSON.stringify(schema || { type: 'object', properties: {} })); s.type = 'object'; s.properties = s.properties || {};
        if (app === 'do') { if (s.properties.text) s.properties.text.description = SAID_DESC; }
        else s.properties.buyer_said = { type: 'string', description: SAID_DESC };
        s.properties.confirm = { type: 'boolean', description: CONFIRM_DESC };
        var req = arr(s.required).slice(); var k = app === 'do' ? 'text' : 'buyer_said'; if (req.indexOf(k) === -1) req.push(k); s.required = req;
        return s;
    }

    W.SpbMcpGate = { VERSION: VERSION, classify: classify, fixTypos: fixTypos, partsInText: partsInText, partsCheck: partsCheck, wholeScope: wholeScope, gate: gate, mcpSchema: mcpSchema, optionsFor: optionsFor, WRITE: WRITE };
})();
