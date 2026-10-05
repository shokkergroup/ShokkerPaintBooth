/* ============================================================================
   SPB PRO FINISH ADVISOR   (owner 2026-10-02: "MOSTLY helping people identify finishes to use on existing schemes")
   The built-in (free, no key) brain used to EXECUTE every finish question as a design ("show me chrome finishes" repainted the whole car;
   "what finish for the stripes" added a red stripe) or answer with a random manual page. This is the missing ADVISOR:
     classify(text, prev)  -> null | { kind: recommend|find|compare|inspect|about|more, target, colour, goal, ... }   (null = not a finish question, leave it to the designer)
     answer(intent, env)   -> { text, cards[], target, colour, next[], shown[] }        cards = real catalogue finishes with swatch, one-line why, tag
     applyPlan(card, target, env) -> { steps:[{tool, args}], label } | { error }          "Use on the stripes" = edit the stripe zone(s) / add a zone on that part
   env = { zones:[{i,id,name,covers,muted,catchAll,finishKey,colour,colourMode}], paint:['#hex'..], prev:{kind,target,shown[],goal} }
   Facts come from the atlas (SpbAIAtlas: renders of every finish) and the design-sense rules in docs/ai_knowledge/02: contrast in colour OR shine,
   chrome is loud on big areas, 2-3 colours + one accent. Nothing here invents a finish key: every key is looked up in the atlas first.
   ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    var W = window;
    function AT() { return W.SpbAIAtlas; }
    function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9#' ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function has(a, x) { return a.indexOf(x) !== -1; }

    // ------------------------------------------------------------------ the parts of a livery a person names
    var TARGETS = [
        { id: 'numbers', label: 'the numbers', re: /\b(?:car |door )?numbers?\b|\bnumerals?\b/, zre: /number/i, thin: true, readable: true, element: 'numbers' },
        { id: 'lower band', label: 'the lower band', re: /\blower\s+(?:band|stripe|sides?|body|panel|part|section)\b|\brocker\b|\bside\s*skirts?\b|\bbottom\s+(?:band|stripe)\b/, zre: /lower|rocker|skirt/i, zre2: /band/i, thin: true, parts: ['left side', 'right side'] },
        { id: 'stripes', label: 'the stripes', re: /\b(?:pin)?stripes?\b|\bracing stripes?\b|\bbands?\b|\baccents?\b|\btrim\b|\bspeed lines?\b|\bpinlines?\b|\blines\b/, zre: /stripe/i, zre2: /accent|band|trim|pin|line|slash/i, thin: true, element: 'stripes' },
        { id: 'hood', label: 'the hood', re: /\bhood\b|\bbonnet\b/, zre: /hood/i, parts: ['hood'] },
        { id: 'roof', label: 'the roof', re: /\broof\b/, zre: /roof/i, parts: ['roof'] },
        { id: 'trunk', label: 'the trunk', re: /\b(?:trunk|deck ?lid|rear deck|boot)\b/, zre: /trunk|deck/i, parts: ['trunk'] },
        { id: 'spoiler', label: 'the spoiler', re: /\b(?:spoiler|wing)\b/, zre: /spoiler|wing/i, parts: ['spoiler'] },
        { id: 'front bumper', label: 'the front bumper', re: /\bfront\s+(?:bumper|splitter|lip)\b|\bsplitter\b/, zre: /front.*(?:bumper|splitter|lip)|(?:bumper|splitter).*front|splitter/i, parts: ['front bumper'] },
        { id: 'rear bumper', label: 'the rear bumper', re: /\brear\s+(?:bumper|diffuser)\b|\bdiffuser\b/, zre: /rear.*(?:bumper|diffuser)|(?:bumper|diffuser).*rear|diffuser/i, parts: ['rear bumper'] },
        { id: 'bumper', label: 'the bumpers', re: /\bbumpers\b|(?<!front )(?<!rear )\bbumper\b|\b(?:front\s+(?:and|&|\/)\s+rear|rear\s+(?:and|&|\/)\s+front|both)\s+bumpers?\b/, zre: /bumper|splitter|diffuser/i, parts: ['front bumper', 'rear bumper'] },
        { id: 'left side', label: 'the left side', re: /\b(?:left|driver)(?:'s)?\s+(?:side|door|flank)\b/, zre: /left side|driver.*(?:side|door|flank)/i, parts: ['left side'] },
        { id: 'right side', label: 'the right side', re: /\b(?:right|passenger)(?:'s)?\s+(?:side|door|flank)\b/, zre: /right side|passenger.*(?:side|door|flank)/i, parts: ['right side'] },
        { id: 'sides', label: 'the sides', re: /(?<!left )(?<!right )(?<!driver )(?<!passenger )\b(?:sides?|doors?|quarter panels?|rear quarters?|fenders?)\b/, zre: /side|door|quarter|fender/i, parts: ['left side', 'right side'] },
        { id: 'selected', label: 'the selected zone', re: /\b(?:selected|current|active|highlighted)\s+zone\b|\bthis\s+zone\b/, zre: /(?!)/, selected: true },
        { id: 'body', label: 'the body', re: /\b(?:body|whole car|entire car|all over|overall|base (?:colou?r|paint|coat)|main (?:colou?r|paint)|the car|my car|this car|a \w+ car|scheme|livery|paint job)\b/, zre: /body|base|main|paint|livery|everything|car/i, all: true }
    ];
    var BODY = TARGETS[TARGETS.length - 1];
    function targetOf(t) {
        t = String(t || '').toLowerCase()
            .replace(/\b(?:and\s+)?(?:leave|keep|preserve)\s+(?:(?:all|every|the|remaining|other)\s+)*(?:rest|other panels?|remaining panels?|other paint|every other panels?|all other paint)\b[^.;,]*/g, ' ')
            .replace(/\b(?:and\s+)?nothing else\b[^.;,]*/g, ' ')
            .replace(/\b(?:and\s+)?do not touch\b[^.;,]*/g, ' ')
            .replace(/\bkeep that base\b/g, ' ');
        var best = null, bestPos = -1, n = 0, i, pos;
        for (i = 0; i < TARGETS.length - 1; i++) { pos = t.search(TARGETS[i].re); if (pos !== -1) { n++; if (best === null || pos > bestPos) { best = TARGETS[i]; bestPos = pos; } } }      // the specific parts only: the body ("navy car") never beats a named part
        if (n > 1 && /,|;|\.\s|\bwhat\b|\bwhich\b|\bhow\b/.test(t)) return best;      // a scheme description first, the question last
        for (i = 0; i < TARGETS.length; i++) { if (TARGETS[i].re.test(t)) return TARGETS[i]; }
        return null;
    }
    var SPECIFIC_NAME = /stripe|number|accent|trim|pin|band|line|slash|hood|roof|trunk|spoiler|bumper|side|door|quarter|fender|logo|sponsor|decal|outline|shadow|glow/i;
    function isWhole(z) {            // a zone that paints the whole car (a stripe limited to a layer or a part is "everything" there: not whole; a name like "Hood paint" or "Main racing stripe" is not the body either)
        var cv = String(z.covers || ''), nm = String(z.name || '');
        if (/whole paintable|paintable area|whole car|not claimed by other zones/i.test(cv)) return true;
        if (/limited to (?:the |a )?(?:hood|roof|trunk|left|right|front|rear|bumper|spoiler|side|door|quarter|fender|drawn|box|layer)/i.test(cv)) return false;      // "limited to the hood" beats a name like "Body paint"
        if (!SPECIFIC_NAME.test(nm) && /(^|\s)(body|base|main|everything else|paint|livery|catch)\b/i.test(nm)) return true;
        return !!z.catchAll && !/limited to|only on layer/i.test(cv) && !SPECIFIC_NAME.test(nm);
    }
    var SEL_I = null;      // the zone index selected in the app (env.selected), set by answer() / applyPlan() / suggestTool()
    function zonesFor(tg, zs) {      // the zones the buyer would call "the stripes" / "the hood" (by their NAME: what "Use on ..." edits)
        var live = (zs || []).filter(function (z) { return !z.muted; });
        if (tg.selected) return SEL_I == null ? [] : live.filter(function (z) { return z.i === SEL_I; });
        if (tg.zones) return live.filter(function (z) { return tg.zones.indexOf(String(z.id)) !== -1; });      // ADVISOR-FIX: an explicit zone set (the zones painting "the pink", the zones of a layer ...)
        if (tg.all) { var wh = live.filter(isWhole), un = wh.filter(function (z) { return !afLayerScoped(z); }); return un.length ? un : wh.filter(function (z) { return /\b(?:body|main|paint|livery)\b/i.test(z.name || '') && !SPECIFIC_NAME.test(z.name || ''); }); }      // ADVISOR-FIX: "the body" is never an everything-zone restricted to a layer the user did not name (owner: "White Base 75% Chrome" turned pink)
        var broad = !tg.thin && !tg.all;      // hood / roof / sides ...: a zone named for a stripe, number or accent on that part is NOT "the hood"
        var a = live.filter(function (z) { return tg.zre.test(z.name || '') && !isWhole(z) && !(broad && /stripe|number|accent|trim|pin|line|slash|logo|sponsor|decal/i.test(z.name || '')); });
        if (!a.length && tg.zre2) a = live.filter(function (z) { return tg.zre2.test(z.name || '') && !isWhole(z); });
        return a;
    }
    function coversFor(tg, zs) {     // every zone that can SHOW on that area, top of the stack first (what "what is on my hood" lists)
        var seen = {}, out = [];
        var more = (zs || []).filter(function (z) { return !z.muted && tg.parts && tg.parts.some(function (p) { return new RegExp(p, 'i').test(z.covers || ''); }) && !isWhole(z); });
        zonesFor(tg, zs).concat(more, zonesFor(BODY, zs)).forEach(function (z) { if (!seen[z.i]) { seen[z.i] = 1; out.push(z); } });
        return out.sort(function (a, b) { return a.i - b.i; });
    }
    function whereText(z) {
        var cv = String(z.covers || ''), m = /limited to (?:the |layer )?([^;,]+)/i.exec(cv);
        if (isWhole(z)) return 'everywhere nothing above it claims';
        return m ? 'on ' + m[1].replace(/\s+/g, ' ').trim().slice(0, 48) : '';
    }

    // ------------------------------------------------------------------ colours people mention
    // the colour table = the Pro designer's own names first, then the extra names (js/spb-colours-ext.js: CSS keywords + racing / car-paint colours); built once, longest names first
    var COLTAB = null, COLTAB_FOR = null, COLNAMES = null;
    function colourTable() {
        var C = (W.SpbProDesign && W.SpbProDesign.COLOURS) || {}, X = W.SPB_COLOUR_EXT || null;
        if (COLTAB && COLTAB_FOR === C && (COLNAMES.ext === !!X)) return COLTAB;
        var T = {}, k; if (X) { for (k in X) T[k] = X[k]; } for (k in C) T[k] = C[k];
        COLTAB = T; COLTAB_FOR = C; COLNAMES = Object.keys(T).sort(function (a, b) { return b.length - a.length; }); COLNAMES.ext = !!X;
        return T;
    }
    function colourOf(t) {
        var C = colourTable(), names = COLNAMES;
        var s = ' ' + norm(t) + ' ';
        for (var i = 0; i < names.length; i++) {
            if (s.indexOf(' ' + names[i] + ' ') !== -1) {
                var k = s.indexOf(' ' + names[i] + ' '), after = s.slice(k + names[i].length + 2, k + names[i].length + 12);
                if (/^(flake|chrome|metal|candy|pearl)\b/.test(after) && /^(gold|silver|copper|bronze|platinum)$/.test(names[i])) continue;     // "gold flake" / "silver chrome" name a finish, not the car colour
                return { name: names[i], hex: C[names[i]] };
            }
        }
        return null;
    }
    function lightNeutral(h) { if (!/^#[0-9a-f]{6}$/i.test(String(h || ''))) return false; var r = parseInt(h.substr(1, 2), 16), g = parseInt(h.substr(3, 2), 16), b = parseInt(h.substr(5, 2), 16), mx = Math.max(r, g, b), mn = Math.min(r, g, b); return lum(h) > 0.7 && (mx ? (mx - mn) / mx : 0) < 0.25; }
    function lum(h) { var r = parseInt(h.substr(1, 2), 16), g = parseInt(h.substr(3, 2), 16), b = parseInt(h.substr(5, 2), 16); return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255; }

    // ------------------------------------------------------------------ what the person is after
    function goalOf(t) {
        var g = {};
        if (/\b(pop|pops|stand(?:s)? out|jump(?:s)? out|eye.?catching|stand out|more visible|noticeable|vivid|bolder|contrast|wild|wilder|crazy|crazier|outrageous|showy|loudest)\b/.test(t)) g.pop = 1;
        if (/\b(readable|legible|easy to read|read(?:s)? (?:well|clearly)|clear(?:ly)? visible|see(?:n)? (?:at speed|from far)|at speed|from the (?:grandstand|stands|tv))\b/.test(t)) g.readable = 1;
        if (/\b(premium|expensive|luxur\w*|classy|classier|high.?end|richer|rich look|elegant|professional|upscale|fancy|nicer|more polished)\b/.test(t)) g.premium = 1;
        if (/\b(shimmer\w*|sparkl\w*|glitter\w*|flakes?|glint\w*|twinkl\w*|glisten\w*|metal flake)\b/.test(t)) g.shimmer = 1;
        if (/\bnot (?:look |be |get |too |so )?(?:cheap|tacky|gaudy|cheesy|loud|much|over the top|flashy)\b|\bwithout (?:looking |being )?(?:cheap|tacky|gaudy|loud)\b|\bnot (?:too |so |that )?(?:wild|crazy|showy)\b|\b(?:calm|quiet|quietly|understated|restrained|subdued|subtle|low[- ]key|muted|gentle|soft(?:er)? sheen|soft quiet)\b/.test(t)) g.subtle = 1;
        if (/\b(deeper|depth|richer colou?rs?|more saturated|colou?rs? (?:look |to look )?deep|wet look|wet)\b/.test(t)) g.deep = 1;
        if (/\b(retro|vintage|70s|seventies|60s|80s|throwback|old.?school|classic)\b/.test(t)) g.retro = 1;
        if (/\b(stealth|modern|aggressive|menacing|murdered out|blacked out|sinister)\b/.test(t)) g.stealth = 1;
        if (/\b(?:solid|plain|nothing fancy|no effects?|just (?:a )?(?:solid |plain )?colou?r|simple colou?r|straight colou?r|smooth|clean|low[- ]clutter|polished enamel|enamel sheens?|non[- ]?metallic)\b/.test(t)) g.plain = 1;
        if (/\b(metallic|metal)\b/.test(t) && /\b(dark|darker|black|dull|muddy|flat)\b/.test(t) && /\b(sim|iracing|game|track)\b|\bwithout\b/.test(t)) g.metalbright = 1;
        if (/\b(render(?:s|ing)? (?:fast|fastest|quick|quickest)|fastest|quickest|lightest|least (?:cpu|gpu|load)|faster to render|render time)\b/.test(t)) g.fastest = 1;
        if (/\b(most|more|highest|biggest|best)\b.{0,12}\b(sparkle|glitter|flake|shimmer)\b|\b(sparkliest|glitteriest)\b/.test(t)) g.sparkleMost = 1;
        return g;
    }
    function goalKey(g) {
        var order = ['fastest', 'sparkleMost', 'metalbright', 'readable', 'subtle', 'plain', 'shimmer', 'premium', 'deep', 'retro', 'stealth', 'pop'];
        if (g.shimmer && g.subtle) return 'shimmer';
        for (var i = 0; i < order.length; i++) { if (g[order[i]]) return order[i]; }
        return null;
    }

    // ------------------------------------------------------------------ classify
    var IMPER = /^\s*(?:please\s+)?(?:(?:can|could|would|will) you\s+)?(?:make|put|paint|add|turn|change|set|apply|use|switch|wrap|cover|colou?r|fill|create|build|design|try|remove|delete|get rid|undo|redo|start|reset|swap|replace|move|rotate|flip|duplicate|copy|hide|mute|merge|zoom|do (?!you\b)|pick|choose|select|decide|give me a|i want|i need|i would like|i'd like|let's|lets)\b/;
    var ADVICE_WORDS = /\b(finishes|finish|options|ideas|suggestions?|choices|alternatives|looks?|shines?)\b/;
    var FINWORDS = /\b(gloss|glossy|matte|satin|chrome|pearl|pearlescent|candy|metallic|flake|glitter|sparkle|holographic|iridescent|chameleon|carbon|brushed|frosted|glass|liquid metal|oil slick|hammered|wet|mirror|ceramic|anodized|rough|rusty|patina|textured|velvet|suede|leather|marble|lava|galaxy|opal|prism|prismatic|shifts?|shifting|colou?r.?shift)\b/;
    var SUPER = [
        [/\b(shiniest|glossiest|most reflective|most mirror.?like|highest gloss|mirror.?like)\b/, 'shiny'],
        [/\b(flattest|mattest|dullest|least shiny|least glossy|most matte|lowest sheen)\b/, 'flat'],
        [/\b(darkest|blackest)\b/, 'dark'],
        [/\b(lightest|brightest|whitest|palest)\b/, 'light'],
        [/\b(most colou?rful|most vibrant|wildest|craziest|most rainbow|most extreme)\b/, 'wild'],
        [/\b(most metallic|most metal|metalliest)\b/, 'metal'],
        [/\b(most textured|roughest|most texture|grittiest|most grain\w*)\b/, 'textured']
    ];
    function superOf(t) { for (var i = 0; i < SUPER.length; i++) { if (SUPER[i][0].test(t)) return SUPER[i][1]; } return null; }
    // "how do I make the numbers matte": the finish word must be the thing being MADE ("...show up on a chrome hood" is not)
    function howtoOK(rest, tg) {
        var r = String(rest).replace(tg.re, ' ').replace(/\b(?:the|my|a|an|to|be|look|looks|more|so|very)\b/g, ' ').replace(/\s+/g, ' ').trim();
        return r.length > 0 && r.split(' ').length <= 3 && !/\b(?:on|with|that|show|up|behind|next|around|under|over|and|stripe|number|pattern)\b/.test(r) && FINWORDS.test(r);
    }
    var NEGQ = /\b(?:anything but|everything but|all but|anything except|everything except|anything besides|anything other than|no|not|without|except|never|minus|avoid|other than|besides|instead of|rather than|don'?t want|do not want|dont want)\s+(?:any\s+|too\s+much\s+|a\s+|the\s+)?[a-z]+(?:\s[a-z]+)?/gi;
    function posText(t) { return stripNeg(t); }
    function lexHas(t) { var L = W.SpbAICards && W.SpbAICards._lex; if (!L) return false; var w = norm(t).split(' '); for (var i = 0; i < w.length; i++) { if (L[w[i]]) return true; } return false; }
    function stripLead(t) { return t.replace(/^\s*(?:(?:hey|hi|ok|okay|so|also|and|well|um)[ ,]+)+/, '').trim(); }
    function sideClean(x) { return x.replace(/\s+(?:on|in|for|at|with)\s+.*$/, ' ').replace(/^\s*(?:explain|compare|describe|tell me about|what is|what's|whats|is|are)\s+/, '').replace(/\b(?:the|a|an|my|finish(?:es)?|look|paint)\b/g, ' ').replace(/\s+/g, ' ').trim(); }
    function pairOr(t) {             // "satin or gloss for the hood", "should I use matte or gloss": a pair of REAL finish names around "or"
        var w = t.replace(/[,?]/g, ' ').split(/\s+/), i, a, b;
        for (i = 1; i < w.length - 1; i++) {
            if (w[i] !== 'or') continue;
            var L = [w.slice(Math.max(0, i - 2), i).join(' '), w[i - 1]], R = [w.slice(i + 1, i + 3).join(' '), w[i + 1]];
            for (a = 0; a < L.length; a++) { for (b = 0; b < R.length; b++) { var ka = resolveName(L[a]), kb = resolveName(R[b]); if (ka && kb && ka !== kb) return [L[a], R[b]]; } }
        }
        return null;
    }

    // ------------------------------------------------------------------ CONVERSATION (2026-10-03 night): follow-ups that POINT AT what was just shown
    //   "tell me about the second one", "why did you pick that", "why not chrome", "what goes with candy red", "which of these is best for night racing",
    //   "something like Undertow but calmer", "more like this", "I like the second one but darker", bare "darker" / "less sparkle" after an answer.
    //   The advisor remembers the keys of its last answer (prev.last, in display order); every pointer resolves against it.
    var ORD = { first: 0, '1st': 0, top: 0, second: 1, '2nd': 1, third: 2, '3rd': 2, fourth: 3, '4th': 3, fifth: 4, '5th': 4, last: -1, bottom: -1 };
    var SUPPORT_RE = /\b(?:render\w*|preview|app|spec map|layers?|export\w*|slow|crash\w*|files?|folders?|iracing|tga|psd|lag\w*|bug\w*|glitch\w*|errors?|windows?|buttons?|screen|garbage|mess|install\w*|licen[cs]e|update|download\w*|upload\w*|save|saved|load\w*)\b/;
    var MODRE = [
        ['calm', /\b(?:calmer|quieter|subtler|subtle|softer|toned down|less (?:flashy|loud|wild|bold|intense)|more (?:subtle|understated)|too (?:flashy|loud|shiny|busy|bold|wild|bright|intense|gaudy))\b/],
        ['bold', /\b(?:bolder|louder|flashier|wilder|crazier|punchier|more (?:flashy|exciting|dramatic|extreme|bold|intense|pop)|too (?:plain|boring|dull|flat|quiet|tame|safe))\b/],
        ['darker', /\b(?:darker|deeper|blacker|moodier|more black|less bright)\b/],
        ['lighter', /\b(?:lighter|brighter|paler|whiter|more white|less dark)\b/],
        ['glossier', /\b(?:glossier|shinier|wetter|more (?:gloss|glossy|shine|shiny|wet)|less matte)\b/],
        ['flatter', /\b(?:flatter|duller|mattier|more (?:matte|flat)|less (?:gloss|glossy|shine|shiny))\b/],
        ['sparklier', /\b(?:sparklier|glitterier|more (?:sparkle|sparkly|glitter|glittery|flake|shimmer|shimmery)|with (?:more )?(?:sparkle|glitter|flake))\b/],
        ['smoother', /\b(?:smoother|less (?:sparkle|sparkly|glitter|glittery|flake|shimmer|grain|grainy)|no (?:sparkle|glitter|flake)|without (?:sparkle|glitter|flake))\b/],
        ['metalmore', /\b(?:more (?:metal|metallic|chrome)|chromier)\b/],
        ['metalless', /\b(?:less (?:metal|metallic|chrome)|non[- ]?metallic|no metal|without metal)\b/],
        ['warmer', /\bwarmer\b/], ['cooler', /\bcooler\b/],
        ['vivid', /\b(?:more (?:colou?rful|vivid|vibrant|saturated)|vivid|vibrant|colou?rful)\b/],
        ['muted', /\b(?:more muted|muted|less (?:colou?rful|saturated|vivid)|desaturated|earthier)\b/],
        ['simpler', /\b(?:simpler|plainer|cleaner|less (?:busy|detail|detailed|pattern|patterned))\b/],
        ['busier', /\b(?:busier|more (?:detail|detailed|pattern|patterned|texture|textured|busy))\b/],
        ['finer', /\b(?:finer|tighter|smaller|more fine|more subtle grain)\b/],
        ['coarser', /\b(?:coarser|bigger|larger|chunkier|broader|rougher|more coarse)\b/]
    ];
    function modOf(t) { var o = [], i; t = String(t || '').toLowerCase(); for (i = 0; i < MODRE.length; i++) { if (MODRE[i][1].test(t)) o.push(MODRE[i][0]); } return o; }
    var TEXIDX = null, TEXIDX_FOR = null;
    function resolveTexture(s) {
        var a = AT(); if (!a || !a.ready()) return null; var d = a._data(); if (!d) return null;
        if (TEXIDX_FOR !== d) { TEXIDX = {}; TEXIDX_FOR = d; for (var i = 0; i < d.items.length; i++) { var it = d.items[i]; if (it._type === 'spec' || it._type === 'pattern') { var nn = norm(it.n).replace(/^spec /, ''); (TEXIDX[nn] = TEXIDX[nn] || []).push(it.k); } } }
        var n = norm(s).replace(/\b(?:the|a|an|my|texture|pattern|spec|finish)\b/g, ' ').replace(/\s+/g, ' ').trim(); return n && TEXIDX[n] ? TEXIDX[n][0] : null;
    }
    function findTexturesIn(t, max) {
        var w = norm(t).split(' ').filter(Boolean).slice(0, 30), out = [], used = {}, n, i, k, g;
        for (n = 4; n >= 1; n--) { for (i = 0; i + n <= w.length; i++) { var clash = false; for (k = i; k < i + n; k++) { if (used[k]) clash = true; } if (clash) continue; g = w.slice(i, i + n).join(' '); var key = resolveTexture(g); if (key && !out.some(function (x) { return x.key === key; })) { out.push({ key: key, q: g, at: i }); for (k = i; k < i + n; k++) used[k] = 1; } } }
        out.sort(function (a, b) { return a.at - b.at; }); return out.slice(0, max || 2);
    }
    function refKeys(txt, prev, texPref) {          // the finish(es) a follow-up points at
        var t = String(txt || '').toLowerCase(), last = (prev && prev.last) || [], m;
        m = /\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|top|last|bottom)(?: one| option| finish| card)?\b/.exec(t);
        if (m && last.length) { var i = ORD[m[1]]; var k = last[i < 0 ? last.length - 1 : i]; return k ? [k] : []; }
        if (/\b(?:these|those|them|all of them|the list|everything you showed)\b/.test(t) && last.length) return last.slice(0, 3);
        if (texPref) { var tn = findTexturesIn(posText(t), 2); if (tn.length) return tn.map(function (x) { return x.key; }); }
        var named = findFinishesIn(posText(t), 2); if (named.length) return named.map(function (x) { return x.key; });
        if (!texPref) { var tn2 = findTexturesIn(posText(t), 2).filter(function (x) { return x.q.split(' ').length >= 2; }); if (tn2.length) return tn2.map(function (x) { return x.key; }); }
        if (/\b(?:this|that|it|this one|that one|the one you showed)\b/.test(t)) { if (prev && prev.focus) return [prev.focus]; if (last.length) return [last[0]]; }
        return [];
    }
    function convoIntent(t, raw, prev, base, tg, col) {
        var last = (prev && prev.last) || [], hasLast = last.length > 0, nwords = t.split(/\s+/).length, m, ref, md, i;
        if (nwords > 24) return null;
        var tgt = tg || (prev && prev.target) || null;
        // 1. tell me about the second one
        m = /^(?:tell me (?:more )?about|what(?:'s| is)|describe|explain|show me|(?:more )?(?:info|details?) (?:on|about))\s+(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|top|last)(?:\s+(?:one|option|finish|card))?(?:\s+like)?\??$/.exec(t);
        if (m && hasLast) { ref = refKeys(m[1], prev); if (ref.length) return { kind: 'about', key: ref[0], target: tgt, colour: prev.colour, text: raw, prev: prev }; }
        // 2. why did you pick that / why not chrome / why is satin good for the stripes
        if (/^(?:why|how come|what(?:'s| is) (?:the )?(?:reason|logic|thinking))\b/.test(t) && !SUPPORT_RE.test(t)) {
            var notM = /^why not\b/.test(t) || /\bwhy (?:didn't|did not|wouldn't|don't) you (?:pick|suggest|recommend|show|include)\b/.test(t);
            ref = refKeys(t.replace(/^(?:why|how come)\s+(?:not|did you|didn't you|would you|do you|is|are|does)\b/, ' '), prev);
            if (!ref.length && prev && prev.focus) ref = [prev.focus];
            if (!ref.length && hasLast) ref = last.slice(0, 3);
            if (ref.length) return { kind: 'why', prev: prev, keys: ref.slice(0, 3), not: notM, target: tgt, colour: col || (prev && prev.colour) || null, goal: base.goal || (prev && prev.goal) || null, text: raw };
        }
        // 3. what goes with X (a finish: accents that read next to it; a colour: finishes that suit it)
        m = /^(?:what|which)(?:'s| is| are)?\s+(?:(?:the )?(?:best|good|nice|great|some|other)\s+)?(?:colou?rs?|finish(?:es)?|stuff|things?|options?)?\s*(?:go(?:es)?|pair(?:s)?|work(?:s)?|look(?:s)?\s+(?:good|great|best|nice)|match(?:es)?|compliments?|complement(?:s)?)\s+(?:well |nicely |best |good )?(?:with|alongside|next to|beside)\s+(.+?)\??$/.exec(t) || /^(?:what|which)\s+(?:should|could|can|would)\s+i\s+(?:pair|match|combine)\s+(?:with|alongside)\s+(.+?)\??$/.exec(t) || /^(?:pairs|goes|works) (?:well )?with\s+(.+?)\??$/.exec(t);
        if (m && !SUPPORT_RE.test(t)) {
            var subj = m[1], sc = colourOf(subj), subjRest = sc && sc.name ? subj.replace(String(sc.name).toLowerCase(), ' ') : subj, sref = refKeys(subjRest, prev);
            if (sref.length) return { kind: 'pairs', key: sref[0], target: tgt, colour: null, text: raw, prev: prev };
            if (sc && !/^(?:what|which)(?:'s| is| are)?\s+(?:(?:the )?(?:best|good|nice|great|some|other)\s+)?colou?rs?\b/.test(t)) return { kind: 'recommend', colour: sc, target: null, goal: base.goal, text: raw, count: base.count, not: base.not, pairsColour: true };      // "what colours go with orange" is a colour-scheme question for the designer, not a finish question
        }
        // 4. which of these is best for ...
        m = /^which (?:one|of (?:these|those|them)|do you (?:think|recommend)|should i (?:pick|choose|use|go with))\b(.*)$/.exec(t) || /^(?:rank|order|sort) (?:these|those|them)\b(.*)$/.exec(t) || /^(?:what(?:'s| is) )?(?:the )?best (?:one|of (?:these|those|them))\b(.*)$/.exec(t);
        if (m && hasLast && !SUPPORT_RE.test(t)) return { kind: 'bestof', prev: prev, rest: m[1] || '', target: tg || (prev && prev.target) || null, colour: col || (prev && prev.colour) || null, goal: base.goal || (prev && prev.goal) || null, text: raw, count: base.count };
        if (prev && prev.kind === 'like' && prev.likeKeys && /^(?:(?:show me |give me |i want |can i have )?more(?: of)?(?: like)?|again|another)\s*(?:this|that|these|those|it|ones?|options?|finishes?)?\s*(?:like (?:this|that|these|those|it))?\??$/.test(t)) return { kind: 'like', keys: prev.likeKeys, mods: prev.likeMods || [], colour: prev.likeColour || null, target: tgt, prev: prev, text: raw, count: base.count };
        // 5. like X (but ...), more like this, I like the second one but darker, same but calmer
        var texAsk = /\b(?:textures?|patterns?|spec patterns?|weaves?)\b/.test(t), lk = /^(?:(?:show|give|find|get) me |i (?:want|need|'?d like|would like) |any |got any |do you have |have you got )?(?:some )?(?:something|anything|stuff|finishes?|ones?|options?|more|others?|(?:spec |paint )?textures?|(?:spec |paint )?patterns?)?\s*(?:like|similar to|along the lines of|in the (?:style|vein) of|reminiscent of|close to|kind of like|sort of like)\s+(.+)$/.exec(t), refTxt = null, modTxt = '';
        if (lk && !/^(?:a|an)\b/.test(lk[1])) { var sp = lk[1].split(/\b(?:but|except|only|though|however|just|and make it|make it)\b/); refTxt = sp[0]; modTxt = sp.slice(1).join(' '); }
        else {
            var lk2 = /^i (?:like|love|prefer|want|really like|kind of like)\s+(?:the\s+)?(.+?)\s+(?:but|except|though|only|just)\s+(.+)$/.exec(t) || /^(?:same|the same(?: one| thing)?|that|this|it|the (?:first|second|third|fourth|fifth|top|last)(?: one)?)\s+(?:but|except)\s+(.+)$/.exec(t);
            if (lk2 && lk2.length === 3 && lk2[1].split(/\s+/).length > 4) lk2 = null;
            if (lk2) { if (lk2.length === 3) { refTxt = lk2[1]; modTxt = lk2[2]; } else { refTxt = t.replace(/\s+(?:but|except)\s+.+$/, ''); modTxt = lk2[1]; } }
        }
        if (refTxt != null && !SUPPORT_RE.test(t)) {
            ref = refKeys(refTxt, prev, texAsk); md = modOf(modTxt || (/\b(?:but|except)\b/.test(t) ? t : ''));
            if (ref.length) return { kind: 'like', keys: ref.slice(0, 3), mods: md, colour: colourOf(modTxt) || null, target: tgt, prev: prev, text: raw, count: base.count, lane: null };
        }
        // 6. bare refinement of the last answer: "darker", "a bit shinier", "less sparkle", "more metallic" (calm / bold keep their ranked paging)
        if (hasLast && nwords <= 7 && !col && !targetOf(t)) {
            md = modOf(t).filter(function (x) { return x !== 'calm' && x !== 'bold'; });
            if (md.length) {
                var restT = t;
                MODRE.forEach(function (r) { restT = restT.replace(r[1], ' '); });      // the modifier phrases first (they contain more / less), then the filler words
                restT = restT.replace(/\b(?:make (?:it|them)|a bit|a little|a touch|bit|slightly|much|even|way|just|something|anything|please|more|less|show me|give me|try|go|with|it|them|that|those|these|again|and|but|than that|than these|i want|i'd like|can you|could you|how about|what about)\b/g, ' ');
                if (!/[a-z0-9]/.test(restT.replace(/[^a-z0-9]+/g, ' ').trim())) return { kind: 'like', keys: last.slice(0, 3), mods: md, colour: null, target: tgt, prev: prev, text: raw, refine: true, count: base.count };
            }
        }
        return null;
    }

    // ------------------------------------------------------------------ DISLIKES (2026-10-03 night): "no glitter", "nothing holographic or chameleon, I hate that", "don't make it look like a wrap"
    //   the negated phrases become a hard exclusion (SpbProRank.avoidSet), they never reach the keyword search, and they stay in force for the rest of the conversation (prev.dislikes)
    var NEG_CUE = /\b(?:(?:anything|everything|all|whatever)\s+(?:but|except|besides|other than)|(?:don'?t|do not|dont|never|please don'?t|i don'?t|i do not)\s+(?:want|like|need|make|let|have|give|use|add|put|do)(?:\s+(?:it|this|that|the car|them|me|us))?(?:\s+to)?(?:\s+(?:look|be|seem|feel|sound))?(?:\s+like)?|no more|none of the|none of|nothing|no|not|without|avoid|skip|hates?|dislike|can'?t stand|cannot stand|sick of|tired of|other than|instead of|rather than)\b/g;
    var NEG_STOP = /\b(?:for|on|in|at|under|over|please|with|because|since|looks?|looking|but|so|that|it|cuz|as|when|from|lol|though|anyway|thanks|really|just|only|simply|purely|instead)\b|[,.;!?()]/;
    var NEG_DEGREE = /^\s*(?:just|only|too|so|very|really|quite|that|exactly|necessarily|always|even|much|overly|super|a lot|all that)\b/;      // "not just purple sparkle", "not too shiny": a degree, not an exclusion
    var NEG_FILL = /^(?:any|a|an|the|too|so|very|super|overly|much|many|more|those|these|that|this|it|them|one|thing|things|anything|everything|all|of|real|really|at|all)$/;
    function negSpans(t) {
        var out = [], re = new RegExp(NEG_CUE.source, 'g'), m;
        while ((m = re.exec(t))) {
            var start = m.index, from = m.index + m[0].length, rest = t.slice(from), cut = rest.search(NEG_STOP);
            if (/^(?:no|not|nothing)$/.test(m[0]) && NEG_DEGREE.test(rest)) continue;
            if (cut === 0) { var lead = /^\s+/.exec(rest); if (!lead || rest.slice(lead[0].length).search(NEG_STOP) === 0) cut = 0; }
            var body = cut >= 0 ? rest.slice(0, cut) : rest, end = from + body.length;
            out.push({ start: start, end: end, body: body }); re.lastIndex = Math.max(re.lastIndex, end);
        }
        return out;
    }
    function negPhrases(t) {
        t = String(t || '').toLowerCase().replace(/[’`]/g, "'"); var out = [];
        negSpans(t).forEach(function (sp) {
            sp.body.replace(/\bat all\b/g, ' ').split(/\s*(?:\bor\b|\band\b|\bnor\b|\/|&)\s*/).forEach(function (ph) {
                var w = ph.replace(/\s+/g, ' ').trim().split(' ').filter(function (x) { return x && !NEG_FILL.test(x); });
                if (w.length && w.length <= 3 && w.join('').length >= 3) { var s1 = w.join(' '); if (out.indexOf(s1) === -1) out.push(s1); }
            });
        });
        // positive wishes that ARE exclusions: "nonmetal", "low-gloss", "low sheen", "no shine at all"
        if (/\bnon[- ]?metal(?:lic)?\b/.test(t) && out.indexOf('metallic') === -1) out.push('metallic');
        if (/\blow[- ]?(?:gloss|sheen|shine)\b|\bzero (?:gloss|shine|sheen)\b/.test(t) && out.indexOf('glossy') === -1) out.push('glossy');
        // "stay one color from every angle", "single hue", "doesn't shift": the colour-shifting family is excluded (L5 G22)
        if (/\b(?:stay|stays|remain|remains|keep|keeps)\s+(?:one|a single|the same)\s+colou?r\b|\bone\s+colou?r\s+from\s+(?:every|any|all)\s+angles?\b|\bsingle[- ]hue\b|\b(?:doesn'?t|does not|don'?t|won'?t)\s+(?:change|shift|flip)\s+colou?rs?\b/.test(t) && out.indexOf('chameleon') === -1) out.push('chameleon');
        // a COMPLAINT about too much shine ("everything too shiny", "too much gloss", "looks like plastic when it's glossy") excludes the shine; "not too shiny" is a degree (kept as a wish)
        if (/(?:^|[^a-z])(?:too|way too|overly)\s+(?:shiny|glossy|reflective|mirror[- ]?like)\b|\btoo much\s+(?:gloss|shine|shininess|reflection)\b|\bplastic(?:y)?\b.{0,24}\bglossy\b|\bglossy\b.{0,24}\bplastic(?:y)?\b|\blooks? (?:like )?plastic\b/.test(t) && !/\bnot\s+(?:too|so|that|overly)\b|\bnothing too\b/.test(t) && out.indexOf('glossy') === -1) out.push('glossy');
        return out;
    }
    function stripNeg(t) {
        t = String(t || '').toLowerCase().replace(/[’`]/g, "'"); var sp = negSpans(t), o = '', pos = 0;
        sp.forEach(function (x) { if (x.start >= pos) { o += t.slice(pos, x.start) + ' '; pos = x.end; } });
        return (o + t.slice(pos)).replace(/\s+/g, ' ').trim();
    }
    // A clause that only DESCRIBES the existing car ("body stays glossy blue", "white is already painted", "stripes already drawn") says what is there, not what is wanted: its words
    // ("glossy", "white") must not retrieve finishes. Clauses with a wish word / question are kept. (truth set: Codex L2)
    var STATE_CAR = /^\s*(?:my|the|our)\s+(?:car|truck|kart|racer|livery|scheme|paint(?: job)?|design|body|shell)\b.*\b(?:is|are|has|have|was|looks?)\b/;      // "my car is navy and orange"
    var STATE_CUE = /\b(?:already|stays?|staying|remains?|remaining|existing|elsewhere|is painted|are painted|drawn|laid out|locked)\b/;
    function stripState(t) {
        if (W.__noStripState) return t;
        t = String(t || '').replace(/\b(?:keep|keeping|leave|leaving|retain|retaining|preserve|preserving)\s+(?:my |the |all |all of |our )?(?:existing |current |original )?(?:paint|colou?rs?|scheme|livery|palette|artwork|design)(?: exactly| the same| as (?:it is|is|they are))?\b/g, ' ').replace(/\b(?:hides?|hiding|hid|doesn'?t show|does not show|won'?t show|resists?|repels?|forgives?|masks?)\s+(?:the\s+|any\s+)?(?:dirt|dust|mud|grime|scratches|fingerprints|swirls|stains?)\b/g, ' matte satin textured ');      // "hides dirt" = a finish that does not SHOW dirt, not one that pictures dirt
        var cl = String(t || '').split(/\s*[.;!?]\s*|\s*,\s*/), keep = cl.filter(function (c) { return !((STATE_CUE.test(c) || STATE_CAR.test(c)) && !WISH_RE.test(c)); });
        if (keep.length === cl.length) return t;
        var out = keep.join(', ').replace(/\s+/g, ' ').trim(); return out.split(/\s+/).length >= 3 ? out : t;
    }
    function stripPart(q, tg) {
        if (!tg || !tg.re || tg.all || W.__keepTgWords) return q;
        var out = String(q || '').replace(new RegExp('\\b(?:for|on|in|to|across|along|over|of|make|paint|turn|do|give|put|set|change|fix)\\s+(?:the\\s+|my\\s+|our\\s+)?(?:' + tg.re.source + ')', 'g'), ' ').replace(/\s+/g, ' ').trim();
        return out.split(' ').length >= 3 ? out : q;
    }
    function dislikedKey(k, it0) { try { if (it0 && it0.dislikes && it0.dislikes.length) { var av = W.SpbProRank.avoidSet(it0.dislikes); return !!av[k]; } } catch (e) {} return false; }
    function stripNegWhere(t, pred) {
        t = String(t || '').toLowerCase().replace(/[’`]/g, "'"); var sp = negSpans(t), o = '', pos = 0;
        sp.forEach(function (x) { if (x.start >= pos && pred(x.body)) { o += t.slice(pos, x.start) + ' '; pos = x.end; } });
        return (o + t.slice(pos)).replace(/\s+/g, ' ').trim();
    }
    function negTraitBody(b) { var R = W.SpbProRank; try { return !!(R && R.isTrait && R.isTrait(b)) || !!colourOf(b); } catch (e) { return false; } }
    var NEG_FILLER = /^(?:please|only|just|vibes?|lights?|under|finish(?:es)?|looks?|want|need|make|give|show|body|panel|panels|number|numbers|plain|solid|simple|real|really|very|thing|stuff|something|anything|ones?|bit|little|car|paint|nice|good|better|best|dont|like|thanks|thank|you|can|for|and|but|the|with|that|this|not|what|which|how|could|would|should|suggest|suggestions?|recommend|idea|ideas|advice|tell|your|have|think|pick|choose|use|put|get|any|else|do|does|are|is|was|kill|cut|lose|drop|reduce|tone|toned|plastic|plasticky|more|less|even|slightly|much|way|extra|also|still)$/;
    // "something more premium" is a bare refinement: nothing but goal words and filler. A colour / material / object word ("gold flake finish", "something expensive like a watch face") makes it a NEW ask
    function bareRefinement(t) {
        return norm(t).split(' ').filter(function (w) { return w.length >= 3 && !NEG_FILLER.test(w); }).every(function (w) { try { var g = goalOf(w); for (var k in g) return true; } catch (e) {} return false; });
    }
    function meaningfulLeft(t0, tg) {          // descriptive words left once the negated phrases, the part, colours, goal words and filler are gone
        var r = stripNeg(t0).replace(/,?\s*\b(?:looks?|feels?|seems?|is|are|because|since|cuz|as it|it looks?|from)\b.*$/, ' '); if (tg && tg.re) r = r.replace(tg.re, ' ');
        return cleanQuery(r).split(' ').filter(function (w) { if (w.length < 3 || NEG_FILLER.test(w)) return false; try { if (colourOf(w)) return false; var g = goalOf(w); for (var k in g) return false; if (wordsOf(MOOD_WORDS, w).length || wordsOf(ERA_WORDS, w).length || wordsOf(FIT_WORDS, w).length) return false; } catch (e) {} return true; });
    }
    // ------------------------------------------------------------------ SEMANTIC CLAIM (2026-10-03 night): a long, real-world ask about the finish of an EXISTING scheme
    //   "Navy and orange GT3, broad orange stripes already drawn. Make them polished nonmetal paint, no pattern."   (Codex L2 truth asks: only 5% were claimed before this)
    //   claimed only when it wishes for options / a material, shows a finish signal and is not a design order, a livery build or a support question
    var WISH_RE = /\b(?:want|need|give|show|choose|suggest|recommend|options?|choices?|ideas?|what|which|how|can (?:i|you|we)|could (?:i|you|we)|should|looking|prefer|try|pick|wish|would like|help|go|keep|let)\b|\?|\bplease\b/;
    var KEEP_RE = /\b(?:keep|existing|already|locked|retain|leave|stay|stays|untouched|preserve|laid out|painted|drawn|set)\b.{0,40}\b(?:colou?rs?|paint|scheme|palette|livery|artwork|decals?|lettering|numbers?|names?|sponsors?|logos?|stripes?|layout|ink|script|stars)\b|\b(?:no|not|without)\b.{0,12}\b(?:repaint|new palette|another palette|colou?r change|different colou?rs?)\b|\bonly (?:the )?(?:material|finish|sheen)\b|\bmaterial only\b|\bchange material only\b/;
    var TEXNOUN_RE = /\b(?:textures?|microtextures?|grain|weave|woven|lattice|knurl\w*|tool marks?|patterns?|houndstooth|plaid|checker\w*|mesh|grid|honeycomb|scales?|flecks?|specks?|peened|brushed|machined|fabric|cloth|leather|rubber)\b/;
    // ------------------------------------------------------------------ the INTENT MODEL decides between the finish advisor and the designer / support (js/spb-intent.js)
    //   precision: a rule-made claim of the lookup kinds is dropped when the model is confident the message is a design order, a support question or chit-chat
    //   recall:    when no rule claims the message and the model is confident it is a finish question, the intent is built from the label (named finishes found in the text feed about / compare / judge)
    var FINISH_LABELS = { recommend: 1, find: 1, compare: 1, about: 1, kit: 1, review: 1, taste: 1, judge: 1, inspect: 1, catalogue: 1 };
    var INTENT_CFG = { dropP: 0.65, claimP: 0.5, subP: 0.5, appP: 0.85, overP: 0.65 };
    var EXPLICIT_TEX = /\b(?:show me|give me|any|some|what|which|suggest|recommend|ideas?|options?|choices?)\b.{0,30}\b(?:textures?|patterns?)\b/;
    function semanticBuild(raw, t0) {
        var tg = targetOf(t0), pos = stripNeg(t0), gl = goalOf(stripNegWhere(t0, negTraitBody)), keep = KEEP_RE.test(t0), tex = TEXNOUN_RE.test(pos);
        var it = { kind: 'recommend', target: tg, colour: colourOf(stripNegWhere(t0, negTraitBody)), goal: goalKey(gl), goals: gl, text: raw, count: countOf(t0), not: notOf(t0), semantic: true, keepColours: keep };
        if (keep) it.lanes = tex ? [['keep', 3], ['texture', 2]] : [['keep', 5]];
        else if (tex) it.lanes = [['texture', 3], ['complete', 1], ['keep', 1]];
        if (tex && !keep && EXPLICIT_TEX.test(t0) && meaningfulLeft(t0, tg).length <= 1) { it.lane = 'texture'; it.lanes = null; }      // "show me some textures for the roof": the textures are the ASK (no further look words), not a look to be found among finishes
        return it;
    }
    function intentFromLabel(label, raw, t0) {
        var tg = targetOf(t0), gl = goalOf(stripNegWhere(t0, negTraitBody)), base = { target: tg, colour: colourOf(stripNegWhere(t0, negTraitBody)), goal: goalKey(gl), goals: gl, text: raw, count: countOf(t0), not: notOf(t0), modelClaim: label };
        var named = findFinishesIn(posText(t0), 4);
        if (label === 'recommend' || label === 'find') return semanticBuild(raw, t0);
        if (label === 'kit') { base.kind = 'kit'; return base; }
        if (label === 'review') { base.kind = 'review'; return base; }
        if (label === 'catalogue') { base.kind = 'catalogue'; return base; }
        if (label === 'taste') { base.kind = 'taste'; base.sub = /\b(?:popular|people|racers|drivers|users|pros|teams|everyone|most)\b/.test(t0) ? 'popular' : 'gold'; return base; }
        if (label === 'inspect') { var zm = /\bzone (\d{1,2})\b/.exec(t0); base.kind = 'inspect'; if (zm) base.zoneIdx = Number(zm[1]) - 1; else if (/\b(?:this|the selected|selected|current|active) zone\b/.test(t0)) base.zoneIdx = 'selected'; return base; }
        if (label === 'about') { if (!named.length) return null; base.kind = 'about'; base.name = named[0].q; base.key = named[0].key; return base; }
        if (label === 'judge') { if (!named.length) return null; base.kind = 'judge'; base.keys = named.map(function (x) { return x.key; }).slice(0, 3); return base; }
        if (label === 'compare') { if (named.length < 2) return null; base.kind = 'compare'; base.sides = named.slice(0, 3).map(function (x) { return x.q; }); return base; }
        return null;
    }
    // the model alone is not trusted for the SPECIFIC intents: the wording must carry a cue for them (it confuses "what finish do I put on the roof" with a state question)
    var LABEL_CUE = {
        inspect: /\b(?:current|currently|right now|at the moment|assigned?|selected|active zone|zone \d+|am i using|are we using|is using|used on|set to|already|which zones|what(?:'s| is) on)\b/,
        review: /\b(?:review|evaluate|critique|assess|audit|feedback|opinion|think of|balance|clash\w*|too (?:much|busy|loud|dull|shiny|random)|overdone|work(?:s)? together|fighting|at odds|restrained|random|simplify|mix)\b/,
        kit: /\b(?:kit|kits|combo|combos|package|combination|whole car|every part|each part|all (?:of )?the parts|set of|coordinated|plan)\b/,
        about: /\b(?:what is|what's|what are|explain|tell me about|describe|meaning|means?|construction|based on|made of|how does|what does|about)\b/,
        compare: /\b(?:or|vs\.?|versus|difference|differences|different|compare|compared|better than|between)\b/,
        judge: /\b(?:would|will|does|do|is|are|can|could|should)\b.{0,70}\b(?:work|clash|look|suit|fit|wrong|too|okay|ok|good|bad|right|complement)\b/,
        taste: /\b(?:popular|favou?rite|most people|everyone|pros|racers|coolest|sickest|best[- ]looking|prettiest|most (?:beautiful|impressive|unique|stunning)|surprise me)\b/,
        catalogue: /\b(?:how many|list|all the|every|inventory|categories|catalog|catalogue|types of|kinds of|browse|available|shelves)\b/
    };
    var APP_STRICT = /\b(?:project|relink|reload|backup|back up|unzip|corrupt\w*|cache|thumbnails?|slider|sliders|picker|import\w*|alpha|channel|folder|settings?|menu|button|click\w*|drag\w*|crash\w*|freez\w*|stuck|spinner|logs?|debug\w*|update|installer|version|permission|tga|psd|dds|export\w*|2048|4096|licen[cs]e|activation|account|login|upload\w*|download\w*|zones?|layers?|mask|undo|history|autosave|state|repro|request|server|browser)\b/;
    var DESIGN_ORDER_RE = /^(?:please |pls |ok |okay |now |just |go ahead and )?(?:recolou?r|crop|undo|reduce|enlarge|widen|narrow|resize|move|rotate|flip|delete|remove|erase|duplicate|copy|paste|mirror|extend|shrink|use .{1,25} on (?:the )?(?:zone|layer)|apply|set|change|swap|replace)\b|\b(?:go ahead|approved|final choice|do it now|change it now)\b/;
    function modelRoute(raw, t0, it, prev, mtext) {
        var M = W.SpbIntent; if (!M || !M.ready || !M.ready()) return it;
        var pr = null; try { pr = M.predict(mtext || raw); } catch (e) { return it; } if (!pr) return it;      // mtext = the message WITHOUT its negated phrases ("nothing glittery on the hood, what do you suggest" is a recommend question; the exclusion is handled separately)
        // "what finish should I put on the selected zone": the zone words made the model say INSPECT; advisory wording (should / put on / best / for) is a recommend (state questions say "what finish IS on ...")
        if (pr.label === 'inspect' && /\b(?:should|would|could|best|better|good|suit\w*|recommend|suggest|put on|go on|goes on)\b/.test(t0) && !/\bwhat (?:finish|material) (?:is|are)\b|\bwhich (?:finish|material) (?:is|are)\b/.test(t0)) pr = { label: 'recommend', p: pr.p };
        var finish = !!FINISH_LABELS[pr.label], explicit = /\b(?:options?|choices?|suggest|recommend|ideas?|which finish|what finish)\b/.test(t0);
        if (it) {
            var special = it.tryMode || it.howto || it.act || it.sup || it.avoid || it.lane || it.mod || it.goal === 'sparkleMost' || it.goal === 'fastest' || it.goal === 'super' || it.goal === 'metalbright';      // rules written for ONE specific question ("could the stripes be matte", "the most sparkle") are not second-guessed by the model
            if (!finish && !special && pr.p >= INTENT_CFG.dropP && /^(?:recommend|find|judge|inspect)$/.test(it.kind) && !(prev && prev.shown) && !(explicit && pr.label !== 'support') && (APP_STRICT.test(t0) || DESIGN_ORDER_RE.test(t0) || pr.p >= 0.9)) return null;
            // a generic rule claim (recommend / find) is corrected when the model is confident the message is a more specific finish question (inspect, review, kit, about, compare, judge, taste, catalogue)
            if (finish && !special && /^(?:recommend|find|kit|compare|taste|judge)$/.test(it.kind) && !it.keys && pr.label !== 'recommend' && pr.label !== 'find' && pr.label !== it.kind && LABEL_CUE[pr.label] && LABEL_CUE[pr.label].test(t0) && pr.p >= ((it.kind === 'recommend' || it.kind === 'find') ? INTENT_CFG.overP : INTENT_CFG.overP + 0.15)) { var alt = intentFromLabel(pr.label, raw, t0); if (alt) { if (it.dislikes) alt.dislikes = it.dislikes; return alt; } }
            return it;
        }
        if (!finish) return null;
        var need = APP_RE.test(t0) ? INTENT_CFG.appP : ((pr.label === 'recommend' || pr.label === 'find') ? INTENT_CFG.claimP : INTENT_CFG.subP);
        if (pr.p < need) return null;
        if (LABEL_CUE[pr.label] && !LABEL_CUE[pr.label].test(t0) && pr.p < 0.9) return null;      // a specific intent without its wording needs real confidence
        if (t0.split(/\s+/).length > 90 || raw.length > 700) return null;
        return intentFromLabel(pr.label, raw, t0);
    }
    // ------------------------------------------------------------------ TWO PARTS, TWO GOALS in one sentence: "I want the numbers plain but the stripes to really pop"
    function splitParts(t0) {
        var cl = String(t0).split(/\s*(?:\bbut\b|\bwhile\b|\bwhereas\b|\band\b(?=\s+(?:the|my|a|what|which|how)\b)|;|,|\bthen\b|\bplus\b)\s*/), out = [], seen = {};
        cl.forEach(function (c) {
            if (c.split(/\s+/).length < 2) return; var tg = null, i, pos = -1;
            for (i = 0; i < TARGETS.length - 1; i++) { var ps = c.search(TARGETS[i].re); if (ps !== -1 && (pos === -1 || ps < pos)) { tg = TARGETS[i]; pos = ps; } }
            if (!tg || seen[tg.id]) return; seen[tg.id] = 1;
            var gl = goalOf(c); out.push({ target: tg, goal: goalKey(gl), goals: gl, text: c });
        });
        return out.length >= 2 ? out : null;
    }
    function multiAnswer(it0, env) {
        var cards = [], texts = [], used = (it0.not || []).slice(), colour = null, skipped = [], i;
        it0.multi.forEach(function (sp) {
            // the numbers are a layer of their own: with no numbers zone on this car there is nothing to apply a finish to ("I want the numbers plain" = leave them alone)
            if (sp.target.id === 'numbers' && env && env.zones && env.zones.length && !zonesFor(sp.target, env.zones).length && !(env.elements && env.elements.numbers && env.elements.numbers.found)) { skipped.push(sp); return; }
            var sub = merge(it0, { multi: null, target: sp.target, goal: sp.goal || null, goals: sp.goals || {}, text: sp.text, count: 3, mod: null, prev: null, not: used.slice(), semantic: false, lanes: null, lane: null });
            var r = recommend(sub, env); if (!r || !r.cards || !r.cards.length) return; colour = colour || r.colour;
            r.cards.slice(0, 3).forEach(function (c) { c.target = { id: sp.target.id, label: sp.target.label }; cards.push(c); used.push(c.key); });
            texts.push(sp.target.label.replace(/^the /, 'the ') + (sp.goal ? ' (' + ({ pop: 'to pop', readable: 'readable', plain: 'plain', subtle: 'calm', premium: 'premium', shimmer: 'with shimmer', deep: 'deeper', retro: 'retro', stealth: 'stealth' }[sp.goal] || sp.goal) + ')' : ''));
        });
        if (cards.length < (skipped.length ? 1 : 2)) return null;
        var tg0 = it0.multi[0].target;
        if (skipped.length) tg0 = cards[0].target || tg0;
        return { text: (skipped.length ? 'The numbers have no zone of their own on this car, so they stay exactly as drawn. For ' + texts.join(' and ') + ': **Use** applies a card to that part only.' : 'Two parts, two answers: ' + texts.join(' and ') + '. Each card says which part it is for; **Use** applies it to that part only.') + (it0.dislikes && it0.dislikes.length ? ' I am leaving out anything ' + it0.dislikes.join(' / ') + '.' : ''), cards: cards, target: { id: tg0.id, label: tg0.label }, useLabel: tg0.label, colour: colour, shown: (it0.prev && it0.prev.shown ? it0.prev.shown : []).concat(cards.map(function (c) { return c.key; })), kind: 'recommend', goal: it0.goal, next: ['Show me more', 'Something calmer', 'Something bolder'] };
    }
    var FINNOUN_RE = /\b(?:sheens?|materials?|textures?|coatings?|options?|choices?|ideas?|treatments?|surfaces?|enamel|microtextures?)\b/;
    var APP_RE = /\b(?:project|projects|relink|reload|backup|back up|unzip|zip|corrupt\w*|cache|thumbnails?|slider|sliders|picker|import\w*|alpha|channel|path|drive|folder|setting|settings|menu|button|click\w*|drag\w*|right-click|help page|tooltip|panel opens|opens|crash\w*|freez\w*|stuck|spinner|log|logs|debug\w*|update|updating|installer|version|permission|tga|psd|dds|mip|spec map|export|exported|2048|4096|iracing|sim|replay|stream|obs|license|activation|register|account|login|sign in|upload|download|share|submit)\b/;
    var Q_OTHER = [/^(?:what is|what's|what are|what does|explain|tell me about|describe|define|how does|how do .+ work)\b/, /\b(?:currently|right now|at the moment|as of now|what am i (?:using|running)|what(?:'s| is) (?:on|used on) my|which (?:finish|material) (?:is|are) (?:on|used|set|assigned))\b/, /\b(?:review|evaluate|critique|audit|rate|assess)\b.{0,30}\b(?:my|the|this)\b.{0,20}\b(?:scheme|car|livery|finishes|combination|setup|materials?)\b/,
        /\b(?:vs\.?|versus|difference between|compared? (?:to|with)|better than|or)\b.{0,40}\b(?:vs\.?|versus|or|better|difference)\b|\bwhich (?:is|one is) (?:better|best|safer)\b/, /^(?:is|are|would|will|does|do|can|could|should)\b.{0,60}\b(?:good|ok|okay|fine|work|works|suit|suits|look|looks|right|safe|wise|bad|idea)\b/, /\b(?:how many|list (?:all|every)|every finish|all the finishes|what (?:categories|kinds|types|shelves)|inventory|catalogue|catalog)\b/,
        /\b(?:favou?rite|most popular|popular|trending|do (?:people|most|buyers|racers) (?:like|use|prefer|pick))\b/];
    function semanticClaim(raw, t0) {
        var n = t0.split(/\s+/).length; if (n < 5 || n > 70 || raw.length > 600 || SUPPORT_RE.test(t0) || APP_RE.test(t0)) return null;
        for (var qi = 0; qi < Q_OTHER.length; qi++) { if (Q_OTHER[qi].test(t0) && !/\b(?:options?|choices?|suggest|recommend|ideas?)\b/.test(t0)) return null; }      // definitions, current-state questions, reviews, comparisons, yes/no suitability, inventory and popularity are other intents
        if (!WISH_RE.test(t0) && !FINNOUN_RE.test(t0) && !(n >= 8 && /\bfinish(?:es)?\b/.test(t0) && /\b(?:that|which|but|not|without)\b|,/.test(t0))) return null;      // the last clause: a described finish ("galaxy finish that looks deep, not just purple sparkle"), never a short "gold flake finish on the hood" (an order)
        if (/\b(?:should be|has to be|have to be|must be|needs to be|need to be|will be|is going to be|gets? a)\b/.test(t0) && !/\b(?:finish(?:es)?|options?|choices?|which|what|suggest)\b/.test(t0)) return null;      // a statement of what the car should be is an instruction for the designer
        if (/^(?:please |pls |can you |could you |would you |just )?(?:make|paint|change|set|turn|put|add|remove|delete|move|rotate|flip|fill|apply|use)\b/.test(t0) && !/\b(?:options?|choices?|which|what|suggest)\b/.test(t0)) return null;       // orders belong to the designer
        if (/^how\b/.test(t0) && !/\b(?:which|what)\b/.test(t0)) return null;      // how-to questions are manual / support questions
        if (/\bcolou?rs?\b/.test(t0) && !/\b(?:finish(?:es)?|sheens?|materials?|textures?|coatings?|gloss\w*|matte|satin|metal\w*|pearl\w*|flake|sparkle|polish\w*|flat\w*|dull|soft|smooth|plain|rough|grain\w*|weave|woven|speck\w*|enamel|choices|options)\b/.test(t0)) return null;      // a colour question is a design question
        if (/\b(?:i want|i'd like|give me|make me|need)\b\s+(?:a|an)\s+(?:[\w\-]+\s+){0,3}(?:car|truck|kart|racer|livery|paint job|scheme)\b/.test(t0) && !/\b(?:existing|already|keep|locked|laid out|current|my)\b/.test(t0)) return null;      // "I want a pearl white car" builds a new look: the designer's job
        if (/\b(?:livery|scheme|design me|build me|throwback)\b/.test(t0) && !/\b(?:existing|already|keep|locked|laid out|current|my)\b/.test(t0)) return null;
        var C = W.SpbAICards, R = W.SpbProRank, tg = targetOf(t0), pos = stripNeg(t0), signal = false;
        try { if (lexHas(pos) || (R && R.isTrait && R.isTrait(pos)) || TEXNOUN_RE.test(pos)) signal = true; if (!signal && C && C.ready()) { var q0 = rankQuery({ kind: 'recommend', text: raw, target: tg }, tg); var rs0 = q0 ? C.search(q0, { limit: 2 }) : []; if (rs0.length && rs0[0].hits && rs0[0].hits.length >= 2) signal = true; } } catch (e) {}
        if (!signal) return null;
        var gl = goalOf(stripNegWhere(t0, negTraitBody)), keep = KEEP_RE.test(t0), tex = TEXNOUN_RE.test(pos), it = { kind: 'recommend', target: tg, colour: colourOf(stripNegWhere(t0, negTraitBody)), goal: goalKey(gl), goals: gl, text: raw, count: countOf(t0), not: notOf(t0), semantic: true };
        it.keepColours = keep;
        if (keep) it.lanes = tex ? [['keep', 3], ['texture', 2]] : [['keep', 5]];
        else if (tex) it.lanes = [['texture', 3], ['complete', 1], ['keep', 1]];
        if (tex && !keep && EXPLICIT_TEX.test(t0) && meaningfulLeft(t0, tg).length <= 1) { it.lane = 'texture'; it.lanes = null; }      // "show me some textures for the roof": the textures are the ASK (no further look words), not a look to be found among finishes
        return it;
    }

    function negValid(ph) { var R = W.SpbProRank; if (!R || !R.avoidSet) return false; try { return Object.keys(R.avoidSet([ph])).length >= 6; } catch (e) { return false; } }
    function unionList(a, b) { var o = (a || []).slice(); (b || []).forEach(function (x) { if (o.indexOf(x) === -1) o.push(x); }); return o; }
    // typo retry: when nothing claims the ask, snap unknown words to the nearest card word ("whats a good finsh for the strips") and ask again
    var CMD_WORDS = ['finish', 'finishes', 'something', 'anything', 'stripes', 'spoiler', 'bumper', 'bumpers', 'numbers', 'metallic', 'pearlescent', 'similar', 'instead', 'different', 'another', 'options', 'calmer', 'bolder', 'darker', 'lighter', 'shinier', 'glossier', 'flatter', 'sparkle', 'sparkly', 'glitter', 'chrome', 'candy', 'pearl', 'satin', 'carbon', 'texture', 'textures', 'pattern', 'patterns', 'suggest', 'recommend', 'holographic', 'hologram', 'chameleon', 'iridescent', 'weathered', 'gradient', 'sunburst', 'brushed', 'polished', 'mirror', 'whatever', 'colours', 'colors', 'looks', 'which', 'should', 'would', 'could', 'finish', 'combo', 'package', 'catalogue'];
    var CMD_SET = {}; CMD_WORDS.forEach(function (w) { CMD_SET[w] = 1; });
    function cmdNearest(w) {
        if (CMD_SET[w] || w.length < 5) return null; var maxd = w.length >= 9 ? 2 : 1, best = null, bd = 9, i, C = W.SpbAICards;
        for (i = 0; i < CMD_WORDS.length; i++) { var c = CMD_WORDS[i]; if (c.charAt(0) !== w.charAt(0) || Math.abs(c.length - w.length) > maxd) continue; var d = C.editDist(w, c, maxd); if (d <= maxd && d < bd) { best = c; bd = d; } }
        return best;
    }
    function spellFix(text) {
        var C = W.SpbAICards; if (!C || !C.ready() || !C.nearest) return text;
        return String(text || '').replace(/[A-Za-z][A-Za-z']{4,}/g, function (w) { var lw = w.toLowerCase(); if (/'/.test(lw)) return w; var n = null; try { n = cmdNearest(lw) || C.nearest(C.toks(lw)[0] || lw); } catch (e) {} return n && n !== lw ? n : w; });
    }
    // state questions ("which zones currently use Matte", "what metallic level is assigned to the hood", "which material did I put on the roof already"): the current state of the car, never a recommendation
    var STATE_RE = /\b(?:currently|right now|at the moment|as it stands|already (?:assigned|using|set|applied|on)|assigned|assignment|assign|which zones|current(?:ly)? (?:material|finish|setting|value|level|assignment|preset)|what(?:'s| is) (?:the )?(?:current|present)|present (?:material|finish)|did i (?:last )?(?:apply|assign|put|set|choose|pick|use)|have i (?:applied|assigned|set)|(?:put|set|applied|assigned) (?:on|to) (?:the )?(?:\w+ ){0,2}already)\b/;
    var INSPECT_Q = /^(?:what|which|is|are|did|do|does|have|read|show|check|list|tell|inspect|look|can you (?:tell|check|show|read)|please (?:tell|check|show|read|list))\b/;
    function inspectRule(raw, t0) {
        if (!STATE_RE.test(t0) || !INSPECT_Q.test(t0) || /\b(?:should|would|best|better|good|suggest|recommend|options?|choices?|ideas?|instead)\b/.test(t0)) return null;
        if (t0.split(/\s+/).length > 30) return null;
        var tg = targetOf(t0), zm = /\bzone (\d{1,2})\b/.exec(t0), it = { kind: 'inspect', target: tg, colour: null, goal: null, goals: {}, text: raw, count: 0, not: [], stateRule: true };
        if (zm) it.zoneIdx = Number(zm[1]) - 1; else if (/\b(?:this|the selected|selected|current|active) zone\b/.test(t0)) it.zoneIdx = 'selected';
        return it;
    }
    function classify(text, prev) {
        var it0 = classifyCore(text, prev);
        if ((!it0 || ((it0.kind === 'recommend' || it0.kind === 'find') && !it0.act && !it0.mod && !it0.lane && !it0.sup && !it0.avoid && !it0.tryMode && !it0.howto)) && !(prev && prev.shown && /^(?:more|show me more)\b/.test(String(text).toLowerCase()))) { var ir = inspectRule(String(text || ''), String(text || '').toLowerCase().replace(/[\u2019`]/g, "'")); if (ir) return ir; }
        if (!it0) { var fx = spellFix(text); if (fx !== text) { var it1 = classifyCore(fx, prev); if (it1) it0 = it1; } }
        return classifyFinish(text, prev, it0);
    }
    var REVERSE_CUE = /\b(?:actually|changed my mind|take (?:that|it) back|(?:i|we) (?:do |really |now |actually )?(?:want|like|love|need|prefer)|show me|bring back|give me|let'?s (?:see|try)|i'?d like|how about|what about)\b/;
    function classifyFinish(text, prev, itCore) {
        var raw = String(text || ''), it = itCore, t0 = raw.toLowerCase().replace(/[’`]/g, "'"), valid = [], dis;
        try { valid = negPhrases(t0).filter(negValid); } catch (e0) {}
        // R08 (Codex L6): "actually I do want chrome now, show me chrome finishes" lifts the remembered dislike of chrome (the trait must appear OUTSIDE the negated spans of this message)
        var revd = [], pd0 = (prev && prev.dislikes) || [];
        if (pd0.length && REVERSE_CUE.test(t0)) { var posR = ' ' + stripNeg(t0) + ' '; pd0.forEach(function (d) { var dr = String(d).toLowerCase().replace(/[^a-z0-9 ]/g, ' ').trim().replace(/\s+/g, '\\s+'); if (dr && new RegExp('\\b' + dr + '\\w*\\b').test(posR)) revd.push(d); }); }
        dis = unionList(pd0.filter(function (d) { return revd.indexOf(d) === -1; }), valid);
        if (!itCore || itCore.kind === 'recommend' || itCore.kind === 'find' || itCore.kind === 'like' || itCore.kind === 'more') { var afc = null; try { afc = afSpecClaim(raw, t0, prev, dis); } catch (eaf) {} if (afc) return afc; }      // ADVISOR-FIX (1): "a spec over the pink" = shine textures for exactly those zones
        if (prev && prev.kind === 'stack' && (!itCore || itCore.kind === 'more' || itCore.kind === 'recommend')) { var afw = afWideClaim(t0, prev); if (afw) return afw; }      // ADVISOR-FIX (2): "show these stacks on the whole body"
        var mt = null; try { if (valid.length) { var sn = stripNeg(t0); if (sn.split(/\s+/).length >= 3) mt = sn; } } catch (emt) {}
        if (!it) { try { var stc0 = stackClaim(raw, t0, null, dis); if (stc0) { stc0.semantic = true; it = stc0; } } catch (estc) {} }      // B2: a layered wish nobody else claimed (orders / schemes / support stay out)
        if (!it) {
            var R0 = W.SpbProRank, trait = valid.some(function (v) { return R0 && R0.isTrait && R0.isTrait(v); });
            if (valid.length && trait && t0.split(/\s+/).length <= 18 && raw.length <= 300 && !SUPPORT_RE.test(t0) && !/\bstripes?\b.*\b(?:on|for)\b/.test(t0) && meaningfulLeft(t0, targetOf(t0)).length <= 1) {
                var tw0 = stripNegWhere(t0, negTraitBody), gl = goalOf(tw0); it = { kind: 'recommend', target: targetOf(t0), colour: colourOf(tw0), goal: goalKey(gl), goals: gl, text: raw, count: countOf(t0), not: notOf(t0), negOnly: true };
            } else {
                var mp0 = null; try { mp0 = (t0.split(/\s+/).length <= 18 && !valid.length && !FINWORDS.test(t0) && !colourOf(t0) && !SUPPORT_RE.test(t0)) ? splitParts(t0) : null; } catch (emp) {}
                if (mp0 && mp0.every(function (q) { return !!q.goal; })) it = { kind: 'recommend', target: mp0[0].target, colour: null, goal: mp0[0].goal, goals: mp0[0].goals || {}, text: raw, count: 0, not: notOf(t0), semantic: true, multi: mp0.slice(0, 3) };
                else {
                    var modelReady = W.SpbIntent && W.SpbIntent.ready && W.SpbIntent.ready();
                    it = modelReady ? modelRoute(raw, t0, null, prev, mt) : semanticClaim(raw, t0);
                    if (!it) return null;
                }
            }
        } else if (valid.length && it.kind === 'find') {
            var posQ = cleanQuery(stripNeg(t0).replace(/\b(?:from|because|since|cuz|as it|it looks?|looks? (?:like|too|so)|they|that looks?)\b.*$/, ' ')).replace(/\b(?:dont|don't|make|it|look|looks|like|please|can|you|show|me|some|any|want|need|give|we|i|my|car|finish|finishes)\b/g, ' ').replace(/\s+/g, ' ').trim();
            if (!/[a-z]{3}/.test(posQ)) { it = { kind: 'recommend', target: it.target, colour: it.colour, goal: it.goal, goals: it.goals, text: raw, count: it.count, not: it.not, negOnly: true }; }
            else it.query = posQ;
        }
        if (it && !it.stack && (it.kind === 'recommend' || it.kind === 'find' || it.kind === 'like')) { try { if (stackClaim(raw, t0, it, it.dislikes || dis)) it.semantic = true; } catch (estk2) {} }      // B2p2: a rule-claimed layered ask is not vetoed by the intent model
        if (it && !it.modelClaim && !it.negOnly && !it.semantic) { var it2 = modelRoute(raw, t0, it, prev, mt); if (!it2) return null; it = it2; }
        if (it && it.kind === 'recommend' && !it.multi && !it.mod && !it.lane && !it.lanes && !it.sup && !it.act && !it.avoid && !it.negOnly && !it.pairsColour) { var mp = splitParts(t0); if (mp) it.multi = mp.slice(0, 3); }
        // "show me a shine texture for the stripes" named no finish: it is a request for TEXTURES (the texture lane), not a catalogue search for "glossy texture" that returned plain Gloss
        if (it && it.kind === 'find' && !it.tryMode && !it.howto && TEXNOUN_RE.test(t0) && it.target && !findFinishesIn(stripNeg(t0), 1).length) { it = { kind: 'recommend', target: it.target, colour: it.colour, goal: it.goal, goals: it.goals || {}, text: raw, count: it.count || 0, not: it.not || [], lane: 'texture', keepColours: /\b(?:shine|sheen|spec|matte|gloss|glossy)\b/.test(t0) }; }
        if (it && dis.length) it.dislikes = dis;
        if (it && revd.length) { it.reversed = revd; if (!dis.length) it.dislikes = []; }
        if (it && !it.stack && (it.kind === 'recommend' || it.kind === 'find')) { try { stackClaim(raw, t0, it, it.dislikes); } catch (estk) {} }      // B2: a claimed ask that names 2+ layers gets the stack slots
        return it;
    }

    function classifyCore(text, prev) {
        var raw = String(text || '').trim(); if (!raw || raw.length > 400) return null;
        var t = stripLead(raw.toLowerCase().replace(/[’`]/g, "'")).replace(/[.!]+$/, '').replace(/\bbtw\b/g, 'between').replace(/\bw\/o\b/g, 'without').replace(/\s(?:n|&)\s/g, ' and ').replace(/\bwh?a?ts\b|\bwat's\b/g, "what's").replace(/\bwat\b/g, 'what').replace(/\bfinn?ish(es)?\b/g, 'finish$1').replace(/\bfinishs\b/g, 'finishes').replace(/\bchorme\b/g, 'chrome').replace(/\bdiff\b/g, 'difference').replace(/\bpls\b|\bplz\b/g, 'please').replace(/\bwich\b/g, 'which').replace(/\bim\b/g, "i'm").replace(/\bcant\b/g, "can't");
        var words = t.split(/\s+/).length; if (words < 2 && !(prev && prev.shown && (/^(?:more|bolder|calmer|subtler|louder|shinier|flatter)\??$/.test(t) || (prev.last && modOf(t).length)))) return null;
        var tWish = stripNegWhere(t, negTraitBody), tg = targetOf(t), col = colourOf(tWish), goal = goalOf(tWish), gk = goalKey(goal);
        var base = { target: tg, colour: col, goal: gk, goals: goal, text: raw, count: countOf(t), not: notOf(t) };
        var finishQ = /\bfinish(?:es)?\b/.test(t);
        if (/\b(?:and|then)\s+(?:apply|do|use|put|set|make|change)\b|\bapply (?:it|them|that|those|the best)\b|\bdo it\b/.test(t)) return null;      // "pick the best finish and apply it" is an order for the designer / AI
        if (/\bhow (?:do|can|would|should) (?:i|you|we) (?:search|filter|browse|open|close|find the|use the|change the|switch)\b|\bwhat(?:'s| is) (?:a |the )?(?:default )?finish\??$|\bwhat finish is the default\b|\b(?:finish|finishes)\s+(?:tab|picker|menu|button|panel|list)\b|\bwhat (?:are|do) finishes\b|\bhow (?:do|can) i (?:use|apply|add|set) (?:a |the )?finish\b|\bspec(?:ular)? values?\b|\bwhat values\b|\bwhat does the .{0,24}\b(?:tab|button|picker|slider|panel|menu|toolbar)\b|\b(?:finish|finishes)\b.{0,12}\b(?:and|vs|versus)\b.{0,6}\b(?:a |an |the )?(?:pattern|patterns|zone|layer|spec pattern|monolithic|base)\b/.test(t)) return null;      // manual / support questions
        if (/^how (?:do|can|should) i (?:choose|pick|select|decide on)\b.{0,16}\bfinish/.test(t)) { base.kind = 'recommend'; return base; }
        // ---- "use the second one", "yes do it": apply a card of the last advice
        if (prev && prev.shown) {
            var om = /^(?:(?:yes|ok|okay|sure|yeah|yep|please)[ ,!]*)*(?:(?:use|apply|do|take|go with|go for|going with|pick|choose|put|try|want)\s+(?:the\s+)?(first|second|third|fourth|1st|2nd|3rd|4th|top|last|[1-4])(?:\s+(?:one|option|finish|card))?|i(?:'ll| will) (?:take|use|go with) (?:the\s+)?(first|second|third|fourth|1st|2nd|3rd|4th|top|last|[1-4])(?:\s+(?:one|option|finish|card))?)\b/.exec(t) || (/^(?:(?:yes|ok|okay|sure|yeah|yep|please)[ ,!]*)*(?:do it|apply it|go ahead|use it|that one|the first one)$/.test(t) ? [t, 'first'] : null);
            if (om) { var w1 = om[1] || om[2]; var ix = { first: 0, '1st': 0, top: 0, '1': 0, second: 1, '2nd': 1, '2': 1, third: 2, '3rd': 2, '3': 2, fourth: 3, '4th': 3, '4': 3, last: -1 }[w1]; if (ix != null) return { kind: 'pick', index: ix, text: raw }; }
        }
        // ---- "I like the third one": a reaction, not an order -> the finish's card with its details (and the Use button)
        if (prev && prev.last && prev.last.length) { var lk0 = /^(?:(?:oh|ok|okay|hmm|nice|yeah|yes)[ ,!]+)*(?:i )?(?:really )?(?:like|love|prefer|dig)\s+(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|top|last)(?:\s+(?:one|option|finish|card))?[.! ]*$/.exec(t); if (lk0) { var rk0 = refKeys(lk0[1], prev); if (rk0.length) return { kind: 'about', key: rk0[0], target: tg || prev.target, colour: prev.colour, text: raw, liked: true, prev: prev }; } }
        // ---- "use the second kit", "apply the classic kit"
        if (prev && prev.kind === 'kit') { var km = /^(?:(?:yes|ok|okay|sure|please)[ ,!]*)*(?:use|apply|go with|take|pick|choose|try|i(?:'ll| will) (?:take|use|go with))\s+(?:the\s+)?(first|second|third|1st|2nd|3rd|classic|premium|bold)\s+(?:one\s+|kit\s+|package\s+)?(?:kit|package)?\b/.exec(t); if (km && /\bkit|package\b/.test(t)) return { kind: 'pick', kit: { first: 0, '1st': 0, classic: 0, second: 1, '2nd': 1, premium: 1, third: 2, '3rd': 2, bold: 2 }[km[1]], text: raw }; }
        // ---- conversation about what was just shown (like X but ..., why that, what goes with ..., which is best, bare "darker")
        var cvi = convoIntent(t, raw, prev, base, tg, col); if (cvi) return cvi;
        // ---- explicit texture / spec-pattern asks open the TEXTURE lane ("what texture would look good on the stripes", "add a subtle pattern to the body", "any good patterns for the roof")
        if (words <= 16 && !SUPPORT_RE.test(t) && !/^how\b|\bhow (?:do|can|to)\b|\bwhat(?:'s| is| are) (?:a |an |the )?(?:spec |paint )?(?:textures?|patterns?)\b|\bdifference\b|\b(?:vs|versus)\b/.test(t) &&
            (/^(?:what|which)(?: (?:kind|sort|type)s? of| are some| is a)?\s+(?:good |nice |cool |subtle |fine )?(?:spec |paint )?(?:textures?|patterns?)\b/.test(t) || /^(?:add|put|layer|apply|try|use)\s+(?:a |an |some |the )?(?:\w+ ){0,2}(?:textures?|spec patterns?|patterns?)\b/.test(t) || /^(?:any|some|show me|give me|suggest|recommend|got any)\s+(?:good |nice |cool |subtle |fine |other )*(?:spec )?(?:textures?|patterns?)\b/.test(t) || /^(?:textures?|spec patterns?)\s+(?:for|on|to)\b/.test(t))) {
            base.kind = 'recommend'; base.lane = 'texture'; return base;
        }
        // ---- follow-ups on the last advice ("more", "something calmer", "show complete looks that suit my colours", "add a texture on top"): ONLY when nothing else is being asked (no colour, no design noun left over)
        if (prev && prev.shown && words <= 10) {
            var fillers = /\b(?:nah|nope|hmm|no|flashy|plain|boring|tame|safe|wild|bright|intense|gaudy|show|give|me|please|something|anything|any|some|a|an|the|one|of|these|those|it|them|that|bit|little|too|so|very|just|try|let'?s|make|go|with|more|other|another|different|else|next|again|options?|ideas?|finishes?|choices?|looks?|kits?|packages?|combos?|plans?|calmer|quieter|subtler|subtle|softer|simpler|louder|bolder|flashier|wilder|crazier|shinier|metallic|flashy|exciting|dramatic|extreme|sparkle|sparkly|shiny|less|loud|busy|understated|classic|toned|down|pop|none|not|feeling|loving|and)\b/g;
            var rest = t.replace(fillers, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
            var lane0 = /\b(?:complete|whole|full|special|exotic)\s+(?:looks?|finishes?)\b|\blooks? that (?:suit|match|go with)\b/.test(t) ? 'complete' : (/\b(?:textures?|spec patterns?)\b/.test(t) && /\b(?:add|layer|show|on top|some|any|with)\b/.test(t) ? 'texture' : (/\b(?:shine only|classics?|proven (?:choices|ones|finishes))\b/.test(t) ? 'keep' : null));
            if (gk && !col && !tg && !IMPER.test(t) && words <= 9 && bareRefinement(t) && !/^(?:is|are|do|does|did|will|would|can|could|should|why|how)\b/.test(t) && gk !== 'fastest' && gk !== 'sparkleMost' && gk !== 'metalbright') return { kind: 'more', mod: 'more', prev: prev, target: prev.target, colour: prev.colour, goal: gk, lane: prev.lane || null, text: raw + ' ' + (prev.text || '') };
            if (lane0 && !col) return { kind: 'more', mod: 'lane', lane: lane0, prev: prev, target: tg || prev.target, colour: prev.colour, goal: prev.goal, sup: prev.sup, text: raw + ' ' + (prev.text || '') };
            if (!col && !IMPER.test(t) && !(finishQ && /\b(?:what|which|how)\b/.test(t)) && !/^(?:is|are|do|does|did|will|would|can|could|should|am i|shall|might)\b/.test(t) && words <= 9 && rest === '') {
                var mod = null;
                if (/\b(calmer|quieter|subtler|subtle|softer|less (?:flashy|loud|shiny|busy)|more (?:subtle|understated|classic)|toned down|simpler|too (?:flashy|loud|shiny|busy|bold|wild|bright|intense|much|gaudy))\b/.test(t)) mod = 'calm';
                else if (/\b(louder|bolder|flashier|wilder|crazier|more (?:flashy|exciting|dramatic|metallic|shiny|sparkle|sparkly|extreme)|shinier|more pop|too (?:plain|boring|dull|flat|quiet|tame|safe|subtle))\b/.test(t)) mod = 'bold';
                else if (/^(?:show me |give me |any )?(?:more|other|another|different|something (?:else|different)|next|again)\b|\bmore (?:options|ideas|finishes|choices)\b|\bnone of (?:these|those)\b|\bnot (?:feeling|loving) (?:these|those|any)\b/.test(t)) mod = 'more';
                if (mod) return { kind: 'more', mod: mod, prev: prev, target: prev.target, colour: prev.colour, goal: prev.goal, sup: prev.sup, lane: prev.lane || null, text: raw + ' ' + (prev.text || '') };
            }
        }
        // ---- "what about satin instead", "how would pearl look on the hood", "what if the stripes were matte", "and the roof?": show THAT finish / that part (nothing changes until Use)
        if (words <= 12 && (/^(?:(?:and|so|ok|okay|hmm|well) )*(?:what|how) (?:about|if)\b/.test(t) || /^(?:what|how) (?:would|will|does|do)\b.{0,40}\blook\b/.test(t) || /^(?:could|can|would|might)\b.{0,30}\b(?:be|look|go|work)\b/.test(t) || /^(?:let'?s )?try\b/.test(t) || /^(?:(?:and|what about) )?(?:the |my )?(?:hood|roof|trunk|sides?|stripes?|numbers?|bumpers?|spoiler|body|lower band)\??$/.test(t)) && !/^(?:can|could|would|will) you\b/.test(t) && !/\b(?:or)\b/.test(t)) {
            var fk = findFinishesIn(t, 1)[0], tg2 = tg || (prev && prev.target) || null;
            if (fk && !/\bcan i have\b/.test(t)) { base.kind = 'find'; base.query = fk.q; base.target = tg2; base.tryMode = true; return base; }
            if (!fk && tg && !col && prev && prev.shown && words <= 6 && /^(?:(?:and|so|ok|okay|hmm|well|what about|how about) )*(?:the |my )?(?:hood|roof|trunk|sides?|stripes?|numbers?|bumpers?|spoiler|body|lower band)\??$/.test(t)) return { kind: 'more', mod: 'retarget', prev: prev, target: tg, colour: prev.colour, goal: prev.goal, sup: prev.sup, text: raw };
        }
        // ---- "is my hood matte", "is it chrome": a question about what is ON the car right now
        if (/^(?:is|are) (?:my |the |this |that )?(?:[a-z]+ )?(?:hood|roof|trunk|stripes?|numbers?|bumpers?|spoiler|sides?|body|car|paint|it)\b.{0,16}\b(?:matte|flat|gloss|glossy|shiny|satin|chrome|metallic|pearl|candy|carbon|brushed)\b\??$/.test(t) && !/\b(?:good|bad|too|better)\b/.test(t)) { base.kind = 'inspect'; return base; }
        // ---- yes/no: "do chrome stripes look good on a blue car", "will chrome numbers be readable", "is pearl too subtle", "can I have a matte hood with a glossy body"
        if (/^(?:is|are|do|does|did|will|would|can|could|should|am i|shall|might)\b/.test(t) && !/^(?:is|are) there\b|^do you have\b|^(?:can|could|would|will) you\b/.test(t) && /\b(?:good|bad|ok|okay|worth|readable|legible|look(?:s)? (?:good|great|nice|bad|right)|work(?:s)?|suit|fit|too (?:subtle|loud|shiny|flat|dull|much|bright)|better|possible|allowed|subtle|loud|safe|right|nice|fine|can i have|can i run|(?:hard|easy) to read|show(?:s)? up|want)\b|^should\b.{0,30}\bbe\b/.test(t) && !/\bor\b.*\b(?:better|which)\b/.test(t)) {
            var jk = findFinishesIn(t, 2);
            if (jk.length) { base.kind = 'judge'; base.keys = jk.map(function (x) { return x.key; }); return base; }
        }
        // ---- taste: "what is your favorite finish", "what's the coolest finish", "which finish is the most popular", "what do other people use on their stripes"
        if (!tg && /\b(?:favou?rite|coolest|best.?looking|most (?:beautiful|impressive|unique|stunning|gorgeous|amazing)|prettiest|rarest|rare|sickest|wow|nicest|surprise me)\b/.test(t) && /\b(?:finish(?:es)?|look|one|material)\b/.test(t)) { base.kind = 'taste'; base.sub = 'gold'; return base; }
        if (/\bmost popular\b|\bpopular (?:finish|choice)|\bwhat (?:do|does) (?:other |most |the )?(?:people|racers|drivers|users|pros|teams)\b|\bwhat do (?:the )?pros\b|\bwhat does everyone\b/.test(t) && /\b(?:finish|use|pick|choose|run|put)\b/.test(t)) { base.kind = 'taste'; base.sub = 'popular'; return base; }
        // ---- the catalogue itself: "how many finishes are there", "what finishes do you have", "list the finishes"
        if (/\bhow many\b.{0,16}\b(?:finishes|looks|options|materials|bases)\b|\bwhat finishes (?:do you|are there|are available|can i (?:use|choose|pick))\b|\blist (?:the |all |your |of )?(?:the )?finishes\b|\b(?:all|every) (?:the |of the |your )?finishes\b|\bwhat are my (?:finish )?options\b|\bwhat can i choose\b/.test(t) && !tg) { base.kind = 'catalogue'; return base; }
        // ---- "should my stripes be shinier than the body"
        var sh = /^should (?:my |the )?(.+?) be (shinier|glossier|brighter|flashier|matter|flatter|duller|calmer|subtler|louder|bolder) than\b/.exec(t);
        if (sh) { var shT = targetOf(sh[1]); if (shT) { base.kind = 'recommend'; base.target = shT; base.mod = /^(?:matter|flatter|duller|calmer|subtler)$/.test(sh[2]) ? 'calm' : 'bold'; base.goal = 'pop'; return base; } }
        // ---- goal ORDERS on a part ("make my stripes pop", "make the hood look more premium", "make the roof shimmer"): apply the first pick (Undo), show the alternatives
        if (/^(?:(?:can|could|would|will) you\s+)?(?:please\s+)?(?:make|get|give|turn|help)\b/.test(t) && gk && /^(?:pop|premium|shimmer|deep)$/.test(gk) && (tg || /^(?:(?:can|could) you )?(?:please )?make (?:it|this|everything|the whole thing)\b/.test(t)) && !FINWORDS.test(t.replace(/\b(?:shimmer\w*|sparkl\w*|flakes?|glitter\w*|glint\w*|twinkl\w*)\b/g, ' ')) && !/\b(?:numbers?|colou?rs?)\b/.test(t) && !col && !/\b(?:bigger|larger|thicker|wider|thinner|smaller|longer|shorter|taller|fatter|slimmer)\b/.test(t) && !/\b(?:and|with|by|plus|then|add\w*|less|instead|outline|graphic|gradient|logo|sponsor|flame|contrast)\b/.test(t) && !(/\bbolder\b/.test(t) && !/\b(?:pop|stand(?:s)? out)\b/.test(t)) && words <= 12) {
            base.kind = 'recommend'; base.act = true; if (!tg) base.target = (prev && prev.target) || BODY; return base;
        }
        // ---- "my chrome looks grey in the sim", "why is my hood so shiny", "my pearl does not shimmer in the game" (a finish complaint, not an edit order)
        var simW = /\b(?:sim|iracing|i racing|in game|in-game|the game|on track|on the track|in the preview)\b/.test(t), finW = /\b(?:chrome|metal|metallic|matte|candy|pearl|pearlescent|gloss|glossy|shiny|satin|carbon|brushed|flake|sparkle|shimmer|holographic|reflective)\b/.test(t);
        var adj1 = /\b(?:looks?|appears?|comes? out|came out|turns?|is|are|isn'?t|aren'?t|doesn'?t|don'?t|won'?t|not)\b[^.?!]{0,20}\b(?:dark|darker|grey|gray|dull|flat|black|muddy|washed|shiny|glossy|matte|too bright|different|wrong)\b/.test(t), adj2 = /\b(?:looks?|appears?|comes? out|came out|turns?|is|are|isn'?t|aren'?t|doesn'?t|don'?t|won'?t|not)\b[^.?!]{0,20}\b(?:metallic|shimmer\w*|sparkl\w*|chrome|reflective)\b|\bhow bright\b/.test(t), whyQ = /\b(?:why|how come|what'?s wrong|what is wrong|problem|issue)\b/.test(t);
        if (finW && (simW || /\bwhy\b/.test(t)) && (adj1 || (simW && (adj2 || whyQ))) && !/\b(?:better|best|versus|vs)\b/.test(t) && !/\b(?:tone it down|turn it down|make it|change it|fix it|reduce|lower|raise|increase|swap|replace)\b/.test(t) && !IMPER.test(t) && !/\b(?:render|export|folder|upload|deploy|trading ?paints?|spec map|template|tgas?|psd|png|debug\w*|bug|crash\w*|error|import|re-?save|saved)\b/.test(t.replace(/\bspec\b/, ''))) { base.kind = 'simlook'; return base; }
        // ---- a finish PLAN for the whole car: "suggest a finish combo for the whole car", "what finishes go together", "finish package for everything"
        if (/\b(?:combo|combos|combination|combinations|package|packages|kit|kits|set|collection|plan|mix)\b.{0,24}\bfinish(?:es)?\b|\bfinish(?:es)?\b.{0,16}\b(?:combo|combos|combination|package|kit|plan|scheme)\b|\bfinish(?:es)?\b.{0,40}\b(?:for (?:everything|each part|every part|all (?:of )?the parts|the whole car|the whole thing)|across the (?:whole )?car|together)\b|\bwhat finishes? (?:go|work|look good) together\b/.test(t) && !/\b(?:and|then)\s+(?:apply|do)\b|\bapply (?:it|them)\b/.test(t) && !/\bcan i have\b/.test(t) && !IMPER.test(t) && !/^(?:apply|set|use|put|mix|combine)\b/.test(t) && !/\bcolou?rs?\b/.test(t) && /\b(?:suggest|recommend|what|which|show me|give me|help me|ideas?|options?|advice)\b|\?\s*$/.test(t)) { base.kind = 'kit'; return base; }
        // ---- review: "review my finishes", "what would make this scheme look better"
        if (!/\b(?:numbers?|symmetr\w*|align\w*|fonts?|logos?|sponsors?|names?|text|layout|mirror\w*|cent(?:er|re)d?)\b/.test(t) && (/\b(?:review|critique|audit|rate|grade|evaluate|assess|improve|polish|upgrade|check|look over|analy[sz]e|feedback|thoughts|opinion)\b.{0,24}\b(?:finishes|finish choices|my finish|my scheme|my livery|my design|my paint job|my paint|the scheme|the livery|this scheme|this livery|this design|the finishes|the paint job)\b/.test(t) || /\b(?:what|how)\b.{0,26}\b(?:improve|make|change|upgrade|polish|fix)\b.{0,24}\b(?:this|my|the) (?:scheme|livery|design|paint job)\b/.test(t) || /\b(?:are|is) (?:my|the|this) (?:finishes|finish|scheme|livery|paint)\b.{0,12}\btoo\b/.test(t) || /\b(?:does|is|do) (?:my|this|the) (?:scheme|livery|design|paint job) (?:need|too|look)\b.{0,24}\b(?:flat|boring|plain|busy|loud|dull|anything|better)\b/.test(t) || /^(?:any |some )?(?:finish )?(?:suggestions|tips|advice|ideas) (?:for|on) (?:my|this|the) (?:scheme|livery|design|finishes)\b/.test(t) || (/\bfinish(?:es)?\b/.test(t) && /\b(?:good|great|bad|right|decent|nice)\s+combination\b|\bwork(?:s|ing)? (?:well )?together\b|\bgo(?:es)? together\b/.test(t) && !tg))) { base.kind = 'review'; return base; }
        // ---- "what finish is zone 3", "what finish does this zone use"
        var zmm = /\bzone (\d{1,2})\b/.exec(t);
        if ((zmm || /\b(?:this|the selected|selected|current) zone\b|\bwhat finish is selected\b/.test(t)) && /\b(?:what|which)\b.{0,16}\bfinish\b|\bfinish\b.{0,16}\b(?:on|of|is|does)\b/.test(t) && !/\b(?:should|would|best|good)\b/.test(t)) { base.kind = 'inspect'; base.zoneIdx = zmm ? Number(zmm[1]) - 1 : 'selected'; return base; }
        // ---- inspect: "what finish is on my hood right now"
        var noWould = !/\b(?:should|would|could|best|good|better|nice|right for|suit|goes?|pop|for)\b/.test(t);
        if (/\b(?:what|which)\b.{0,22}\b(?:finish(?:es)?|material|base|shine|look)\b.{0,28}\b(?:is|are)\b.{0,12}\b(?:currently |now |right now )?(?:on|used on|using on|applied to|in use|covering)\b|\b(?:what|which)\b.{0,22}\bfinish(?:es)?\b.{0,28}\b(?:am i using|do i have|have i got|did you (?:use|put|pick|choose|add|apply)|are we using|is this|is that|is it)\b|^what(?:'s| is) (?:on|covering|the finish (?:on|of)) (?:my|the) |\b(?:which|what) finish(?:es)? (?:is|are) (?:the |my )?(?:current|now)\b|\b(?:what|which)\b.{0,12}\b(?:am i|are we) using\b|\bwhat (?:finishes?|materials?)\b.{0,8}\b(?:i'?m|i am|we'?re) (?:using|running|got|have)\b/.test(t) ||
            (/\b(?:right now|currently|at the moment)\b/.test(t) && finishQ && /\b(?:what|which)\b/.test(t)) ||
            (tg && noWould && /^(?:what|which)\b.{0,6}\bfinish(?:es)?\s+(?:is|are)\s+(?:currently |now )?(?:the |my |on the |on my )?(?:[a-z]+\s*){0,3}$/.test(t))) { base.kind = 'inspect'; return base; }
        // ---- compare: "difference between A and B", "A vs B", "satin or gloss for the hood", "how is A different from B"
        var m = /\b(?:difference|differences|diff)s? between (.+?) and (.+?)(?:[,?]|$| (?:in|on|for|when|if|and which)\b)/.exec(t) || /\bcompare (.+?)(?: and | with | to | vs\.? | versus )(.+?)(?:[,?]|$| (?:in|on|for)\b)/.exec(t) || /\bhow (?:is|are|does|do) (.+?) (?:different|differ)(?:ent)? (?:from|to|than) (.+?)(?:[,?]|$)/.exec(t) || /\b(?:torn|decide|decision|choose|pick|choosing|picking|stuck)\b.{0,16}\bbetween (.+?) and (.+?)(?:[,?]|$| (?:for|on|in|which)\b)/.exec(t);
        var sides = null;
        if (m) sides = [m[1], m[2]];
        else if (/\b(?:vs\.?|versus)\b/.test(t) || /\bwhich (?:is|one is|looks?|would be) (?:better|best)\b|\bis .+ or .+ better\b/.test(t)) {
            var core = t.replace(/[,?]?\s*(?:which|what)\b.*$/, '').replace(/^\s*(?:is|are)\s+/, '').replace(/\s+(?:better|best)\s*(?:on|in|for)?.*$/, '').replace(/\b(?:on|in|for) (?:track|the sim|iracing|the car|my car).*$/, '');
            var parts = core.split(/\s+(?:vs\.?|versus|or)\s+|\s*[,\/]\s*/).map(function (x) { return x.trim(); }).filter(Boolean);
            if (parts.length >= 2) sides = parts;
        }
        if (!sides && /\bor\b/.test(t) && (/\b(?:better|best|which|should|prefer|rather|pick|choose|go with)\b/.test(t) || (tg && /\b(?:for|on)\b/.test(t)))) sides = pairOr(t);
        if (sides) {
            sides = sides.map(sideClean).filter(function (x) { return x && x.split(' ').length <= 4 && !/^(?:base|monolithic|pattern|spec|zone|layer|finish)$/.test(x); }).slice(0, 4);
            var okSides = sides.filter(function (x) { return resolveName(x); });
            if (okSides.length >= 2) { base.kind = 'compare'; base.sides = sides; return base; }
        }
        // ---- "tell me about X"
        var ab = /^(?:what(?:'s| is| are| does| do)|tell me about|explain|describe|how does|what does)\s+(?:the |a |an )?(.+?)(?: finish| look(?:s)? like| look| do| mean)?\??$/.exec(t);
        if (ab && ab[1] && ab[1].split(' ').length <= 5 && !/^(?:the )?(?:difference|best|good|better|my|your|this|that|it|iracing|shokker|a zone|zone|spec|clearcoat|roughness|metallic channel|pattern|layer|mask|base colou?r|most|least|[a-z]+est)\b/.test(ab[1]) && !/\b(?:on|for|in) (?:the|my) /.test(ab[1])) {
            var key = resolveName(ab[1]); if (key) { base.kind = 'about'; base.name = ab[1]; base.key = key; return base; }
        }
        // ---- the most / the -est: "what is the shiniest finish", "which finishes have the most sparkle"
        var sup = superOf(t); if (sup && gk !== 'fastest' && /\b(?:finish(?:es)?|look|looks|shine|material|base)\b/.test(t) && /\b(?:what|which|show|give|list|find|tell)\b|\?\s*$/.test(t)) { base.kind = 'recommend'; base.sup = sup; base.goal = 'super'; return base; }
        // ---- "I need a finish for the stripes", "help me pick a finish", "could you recommend something for the stripes"
        if (!FINWORDS.test(t) && (/^(?:(?:can|could|would|will) you\s+)?(?:please\s+)?help me\b.{0,14}\b(?:pick|choose|find|decide|select)\b.{0,16}\bfinish/.test(t) || /^(?:i|we)\s+(?:need|want|would like|'d like|am looking for|'m looking for)\s+(?:a |an |some |the )?(?:new |good |better |different )?finish(?:es)?\b/.test(t))) { base.kind = 'recommend'; return base; }
        if (/^(?:(?:can|could|would|will) you\s+)?(?:please\s+)?(?:recommend|suggest)\b/.test(t) && (!FINWORDS.test(t) || /\b(?:finish|shine|look)/.test(t)) && !/\b(?:colou?rs?|schemes?|designs?|fonts?|names?|sponsors?|logos?|patterns?|graphics?|livery|liveries|layouts?|themes?)\b/.test(t.replace(/\b(?:colour|color) of\b/, ''))) { base.kind = 'recommend'; return base; }
        // ---- design commands belong to the designer ("make the hood chrome")
        var adviceAsk = /^(?:show me|give me|find me|list|recommend|suggest)\b|\b(?:what|which)\b|\b(?:recommend|suggest|ideas?|options?|advice|advise)\b|\?\s*$/.test(t);
        if (IMPER.test(t) && !(/^(?:give me|show me)\b/.test(t) && ADVICE_WORDS.test(t))) {
            if (!/^(?:i want|i need|i would like|i'd like)\b/.test(t) || !tg || !(gk && gk !== 'fastest')) return null;      // "I want the stripes to shimmer but not look cheap" is advice; "I want the hood red" is a design
            if (!/\bto\s+(?:\w+\s+){0,3}(?:pop|shimmer|sparkle|glow|shine|stand|look|feel|be more|be less|read)\b/.test(t)) return null;
            base.kind = 'recommend'; return base;
        }
        var designish = /\b(?:livery|liveries|scheme|schemes|theme|themes|layout|colou?rs?|colou?red|paint job|contrast|ratio)\b/.test(t.replace(/\b(?:shift(?:s|ing)?|chang(?:e|es|ing)|flip(?:s|ping)?) colou?rs?\b|\bcolou?r.?(?:shift\w*|chang\w*|flip\w*)\b/g, ' ')) && !finishQ && !/\b(?:shine|material|texture|coating)\b/.test(t);
        if (designish) return null;
        if (/\b(?:avoid|never use|worst|bad for|bad on|shouldn'?t use|should not use|stay away from|not to use|don'?t use)\b/.test(t) && finishQ) { base.kind = 'recommend'; base.avoid = true; return base; }
        // ---- "how do I make the numbers matte": show the finish with a Use button (nothing changes until pressed)
        var hm = /^how (?:do|can|would|could|should) (?:i|you|we) (?:make|get|set|turn|change|do|put|add|apply|have)\b(.*)$/.exec(t);
        if (hm && tg && FINWORDS.test(hm[1]) && howtoOK(hm[1], tg)) { base.kind = 'find'; base.query = cleanQuery(hm[1].replace(tg.re, ' ')); base.howto = true; return base; }
        // ---- find: "show me chrome finishes", "something that looks like brushed aluminum", "a wet look black finish", "closest to real chrome"
        var cl = /\b(?:closest|nearest|most similar|similar|close|looks?|looking) (?:to|like) (?:a |an |the |real |actual )?(.+?)$/.exec(t);
        if (cl && cl[1] && (finishQ || FINWORDS.test(cl[1])) && !tg && !/^(?:me|you|it|that|this|my)\b/.test(cl[1]) || (cl && cl[1] && /^(?:what|which) finish(?:es)?\b/.test(t) && (!tg || tg.all) && !/^(?:me|you|it|that|this|my)\b/.test(cl[1]))) { base.kind = 'find'; base.query = cleanQuery(cl[1]); return base; }
        if (/^(?:show me|find me|find|list|search for|got any|any|do you have|have you got|is there|are there|looking for|i(?:'m| am) looking for|i need to find|where(?:'s| is) the|let me see|can i see|could i see|i want to see|gimme)\b/.test(t) && (ADVICE_WORDS.test(t) || FINWORDS.test(t) || findFinishesIn(posText(t), 1).length)) { base.kind = 'find'; base.query = cleanQuery(tg ? t.replace(tg.re, ' ') : t); return base; }
        // a described LOOK without an order ("whiskey amber candy like a bourbon barrel", "dusty dirt late model that looks like it raced all night"): meaning search over the finish cards, nothing applied
        var nCol = 0; try { var CC = (W.SpbProDesign && W.SpbProDesign.COLOURS) || {}; Object.keys(CC).forEach(function (n) { if (new RegExp('\\b' + n + '\\b').test(t)) nCol++; }); } catch (ecl) {}
        if (!tg && nCol < 2 && words >= 4 && words <= 22 && (FINWORDS.test(t) || lexHas(t)) && !/\b(?:render\w*|preview|app|spec map|layers?|export\w*|slow|crash\w*|files?|folders?|iracing|tga|psd|lag\w*|bug\w*|glitch\w*|errors?|windows?|buttons?|screen|garbage|mess)\b/.test(t) && /\b(?:looks?|looking|feels?|reminds? me of)\s+(?:like|of)\b|\blike (?:a|an|the)\b|\bvibe\b|\binspired by\b|\bthat (?:looks?|feels?|shines?|sparkles?|shifts?|glows?)\b/.test(t)) { base.kind = 'find'; base.query = cleanQuery(t); return base; }
        if (/^(?:something|anything)\b.{0,24}\b(?:like|that (?:looks?|feels?|shines?|sparkles?|shifts?)|with|in)\b/.test(t) || /^(?:a|an|some)\s+(?:\w+\s+){0,5}(?:finish(?:es)?|look)\s*$/.test(t) || /^(?:a|an|some)\s+finish\b/.test(t) || (/^something\s+\w+/.test(t) && tg && words <= 9) ||
            (!tg && words <= 6 && (/^(?:[\w'-]+\s+){1,5}finish(?:es)?$/.test(t) || (/^(?:[\w'-]+\s+){1,4}look$/.test(t) && FINWORDS.test(t)))) ||
            (/^(?:a|an|some|any)\s/.test(t) && FINWORDS.test(t) && /\b(?:that|which|with|style|type|kind)\b/.test(t) && words <= 9 && !tg)) {
            base.kind = 'find'; base.query = cleanQuery(tg ? t.replace(tg.re, ' ') : t); return base;
        }
        // ---- recommend
        var recWords = /\b(?:what|which)\b.{0,48}\b(?:finish(?:es)?|material|shine|texture|coating|effect)\b|\b(?:what|which)\b.{0,30}\blooks? (?:good|best|great|nice|right|better|cool|clean)\b(?=.{0,30}\b(?:finish|shine|material|texture|hood|roof|trunk|stripes?|numbers?|bumpers?|spoiler|sides?|band)\b)|\bwhat (?:would|do) you (?:put|use|choose|pick|run|do)\b.{0,16}\b(?:on|for)\b|\bbest\b.{0,20}\bfinish(?:es)?\b|\b(?:good|nice|right|perfect|ideal|great)\b.{0,12}\bfinish(?:es)?\b.{0,24}\b(?:for|on)\b|\b(?:recommend|suggest|advise|ideas?|options?)\b.{0,40}\b(?:finish(?:es)?|look|shine|material)\b|\bfinish(?:es)?\b.{0,24}\b(?:go(?:es)? (?:well |best )?with|match(?:es)?|complement|pair(?:s)?|suit|work(?:s)? (?:best |well )?(?:on|with|for))\b|\bwhat (?:would|could|can|will)\b.{0,16}\b(?:make|help)\b.{0,40}\b(?:premium|pop|stand out|richer|classier|expensive|deeper|better|cleaner|professional|shine|sparkle|look)\b|^(?:give me|show me) (?:\w+ ){0,3}(?:finishes|options|ideas|suggestions|choices|alternatives)\b/;
        if (recWords.test(t)) { base.kind = 'recommend'; return base; }
        if (gk && (tg || gk === 'fastest' || gk === 'sparkleMost' || gk === 'metalbright') && /\b(?:how|what|which)\b/.test(t)) { base.kind = 'recommend'; return base; }
        if (gk === 'fastest' || gk === 'sparkleMost') { if (/\b(?:what|which)\b.{0,16}\bfinish(?:es)?\b/.test(t) || /\bwhich\b/.test(t)) { base.kind = 'recommend'; return base; } }
        return null;
    }
    var NUMW = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6 };
    function countOf(t) { var m = /\b(one|two|three|four|five|six|[1-6])\s+(?:\w+\s+){0,2}(?:finish(?:es)?|options?|ideas?|suggestions?|choices|alternatives|looks)\b/.exec(t); return m ? NUMW[m[1]] : 0; }
    function notOf(t) {            // "not just gloss", "other than chrome", "without matte"
        var out = [], re = /\b(?:not(?: just| only)?|anything but|everything but|all but|other than|besides|except|without|instead of|no more)\s+(?:a |an |the )?([a-z][a-z ]{1,18}?)(?=$|[,.;?]| and | or | for | on | in )/g, m;
        while ((m = re.exec(t))) { var k = resolveName(m[1].trim()); if (k && out.indexOf(k) === -1) out.push(k); }
        return out;
    }
    var QSYN = { shiny: 'glossy', shine: 'glossy', shimmery: 'shimmer', sparkly: 'sparkle', glittery: 'glitter', dull: 'matte', flat: 'matte', 'color shifting': 'chameleon', 'colour shifting': 'chameleon', 'color shift': 'chameleon', 'colour shift': 'chameleon' };
    function cleanQuery(t) {
        t = String(t).replace(/\b(?:colou?r.?shifting|colou?r.?shift|shiny|shine|shimmery|sparkly|glittery|dull|flat)\b/g, function (w) { return QSYN[w.replace(/[-_]/g, ' ')] || w; });
        t = t.replace(/\b(?:top\s+)?(?:one|two|three|four|five|six|seven|eight|nine|ten|\d{1,2})\b(?=\s+(?:[a-z]+\s+){0,2}(?:finish(?:es)?|options?|ideas?|choices|looks?|suggestions?|matches)\b)/g, ' ');
        return t.replace(/\b(?:show me|find me|find|list|search for|got any|any|do you have|have you got|is there|are there|looking for|i'?m looking for|i need to find|something|that|looks?|like|feels?|some|a|an|the|finish(?:es)?|look|for me|please|can you|could you|i want|i'd like|options?|ideas?|suggestions?|choices|let me see|can i see|could i see|i want to see|gimme|see|me|for|on|of|to|my|your|our)\b/g, ' ').replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
    }

    // ------------------------------------------------------------------ naming: "candy", "satin chrome", "Abalone Nacre" -> one catalogue key
    var CONCEPT = {
        'gloss': ['base::gloss'], 'glossy': ['base::gloss'], 'high gloss': ['base::gloss'], 'matte': ['base::matte'], 'flat': ['base::matte'], 'satin': ['base::satin'], 'semi gloss': ['base::semi_gloss'], 'semigloss': ['base::semi_gloss'], 'eggshell': ['base::eggshell'],
        'wet look': ['base::wet_look'], 'wet': ['base::wet_look'], 'pearl': ['base::f_pearl', 'base::pearl'], 'pearlescent': ['base::f_pearl', 'base::pearl'], 'satin pearl': ['base::f_satin_pearl'], 'candy': ['base::f_candy', 'base::candy'],
        'metallic': ['base::f_metallic', 'base::metallic'], 'metal flake': ['base::f_metallic', 'base::metallic'], 'matte metallic': ['base::f_matte_metallic'], 'gunmetal': ['base::gunmetal'],
        'chrome': ['base::f_chrome', 'base::chrome'], 'mirror': ['base::f_chrome', 'base::chrome'], 'mirror chrome': ['base::f_chrome', 'base::chrome'], 'satin chrome': ['base::f_satin_chrome', 'base::satin_chrome'], 'dark chrome': ['base::f_dark_chrome'], 'black chrome': ['base::f_dark_chrome'],
        'brushed': ['base::f_brushed'], 'brushed metal': ['base::f_brushed'], 'brushed aluminum': ['base::brushed_aluminum', 'base::f_brushed'], 'brushed aluminium': ['base::brushed_aluminum', 'base::f_brushed'], 'anodized': ['base::f_anodized'], 'bead blast': ['base::f_bead_blast'],
        'carbon': ['base::f_carbon_fiber'], 'carbon fiber': ['base::f_carbon_fiber'], 'carbon fibre': ['base::f_carbon_fiber'], 'cerakote': ['base::cerakote'], 'ceramic': ['base::ceramic'], 'powder coat': ['base::f_powder_coat'], 'powder coated': ['base::f_powder_coat'],
        'vinyl': ['base::satin'], 'vinyl wrap': ['base::satin'], 'wrapped': ['base::satin'], 'wrap': ['base::satin'], 'wrapped car': ['base::satin'], 'primer': ['base::primer'], 'frozen': ['base::f_frozen'], 'gel coat': ['base::wet_look'], 'baked enamel': ['base::gloss'], 'enamel': ['base::gloss'], 'piano black': ['base::piano_black'], 'blackout': ['base::blackout']
    };
    var NAMEIDX = {}, NAMEIDX_FOR = null;
    function resolveName(s, taken) {
        var a = AT(), ready = !!(a && a.ready());
        var n = norm(s).replace(/\b(?:the|a|an|my|finish(?:es)?|look|paint|type)\b/g, ' ').replace(/\s+/g, ' ').trim(); if (!n) return null;
        var c = CONCEPT[n], i, k;
        if (c) { for (i = 0; i < c.length; i++) { if ((!ready || a.lookup(c[i])) && !(taken && has(taken, c[i]))) return c[i]; } }
        if (!ready) return null;
        var d = a._data(); if (!d) return null;
        if (NAMEIDX_FOR !== d) { NAMEIDX = {}; NAMEIDX_FOR = d; for (i = 0; i < d.items.length; i++) { var it0 = d.items[i]; if (it0._type === 'base' || it0._type === 'monolithic') { var nn = norm(it0.n); (NAMEIDX[nn] = NAMEIDX[nn] || []).push(it0.k); } } }
        var ks = NAMEIDX[n] || []; for (i = 0; i < ks.length; i++) { if (!(taken && has(taken, ks[i]))) return ks[i]; }
        var tx = resolveTexture(s); return (tx && !(taken && has(taken, tx))) ? tx : null;      // spec / paint pattern names ("Shot Peened", "Basket Weave") resolve too, after the finishes
    }

    // ------------------------------------------------------------------ cards
    function isFoundation(it) {
        var d = AT()._data(); if (!d || it._type !== 'base' || it.o !== 0) return false;
        for (var i = 0; i < (it.s || []).length; i++) { if (d.sections[it.s[i]] === 'Foundation') return true; }
        return false;
    }
    function tagOf(it) {
        if (it.o === 1) return 'brings its own colours';
        if (isFoundation(it)) return 'shine only: keeps your paint colours';
        return 'takes the zone colour';
    }
    function shineWord(it) { return it.shine ? it.shine + (it.metal && it.metal !== 'none' ? ', ' + it.metal + ' metal' : '') : ''; }
    function firstSentence(s, n) {         // one readable sentence, cut at a word boundary
        s = String(s || '').replace(/\s+/g, ' ').trim(); var m = /^(.+?[.!?])(?:\s|$)/.exec(s); if (m) s = m[1];
        if (s.length > n) { s = s.slice(0, n); var k = s.lastIndexOf(' '); s = (k > 40 ? s.slice(0, k) : s).replace(/[,;:\s-]+$/, '') + '…'; }
        return s;
    }
    function card(key, why, hex) {
        var a = AT(), it = a && a.lookup(key); if (!it) return null;
        var type = it.k.split('::')[0], id = it.k.replace(/^[a-z]+::/, ''), c = (hex && /^#[0-9a-f]{6}$/i.test(hex)) ? hex : '#888888';
        if (it._type === 'spec' || it._type === 'pattern') return { key: it.k, name: it.n, type: type, why: why || '', tag: it._type === 'spec' ? 'shine texture: keeps your colours' : 'paint pattern: adds colour on top', own: false, keep: false, look: '', sparkle: false, warn: '', lane: 'texture', thumb: it._type === 'spec' ? '/api/spec-pattern-preview/' + encodeURIComponent(id) : '/api/swatch/pattern/' + encodeURIComponent(id) + '?size=200&color=' + c.replace('#', '') };
        return { key: it.k, name: it.n, type: type, why: why || '', tag: tagOf(it), own: it.o === 1, keep: isFoundation(it), look: shineWord(it), sparkle: it.sk === 1, warn: (it.o === 0 && it.metal === 'full' && hex && !lightNeutral(hex) && lum(hex) >= 0.25 && !/dark|black/i.test(it.n)) ? 'Full metal on a coloured part can look darker in the sim (iRacing multiplies the paint colour by the metal).' : '', thumb: '/api/swatch/' + type + '/' + encodeURIComponent(id) + '?size=200&color=' + c.replace('#', '') };
    }
    function pick(keys, excl) {
        var a = AT();
        for (var i = 0; i < keys.length; i++) { if (has(excl, keys[i])) continue; var it = a.lookup(keys[i]); if (it && (it._type === 'base' || it._type === 'monolithic')) return keys[i]; }
        return null;
    }
    function merge(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
    function findPick(o, excl) {
        var a = AT(); o.exclude = (o.exclude || []).concat(excl); o.limit = o.limit || 4; o.type = 'finish';
        var rows = a.find(o) || []; return rows.length ? rows[0].key : null;
    }

    // ------------------------------------------------------------------ what the car looks like now
    function shineClass(it) { if (!it) return null; var s = it.shine || ''; if (s === 'matte' || s === 'semi-matte') return 'flat'; if (s === 'satin') return 'satin'; return 'glossy'; }
    function ctxOf(tg, env) {
        var zs = env.zones || [], body = zonesFor(BODY, zs), own = tg && !tg.all ? zonesFor(tg, zs) : [];
        var bodyIt = null, bodyKey = null, a = AT();
        body.forEach(function (z) { if (!bodyIt && z.finishKey && a.lookup(z.finishKey)) { bodyIt = a.lookup(z.finishKey); bodyKey = z.finishKey; } });
        var tIt = null; own.forEach(function (z) { if (!tIt && z.finishKey && a.lookup(z.finishKey)) tIt = a.lookup(z.finishKey); });
        var hex = null; own.concat(body).forEach(function (z) { if (!hex && z.colour && /^#[0-9a-f]{6}$/i.test(z.colour)) hex = z.colour; });
        return { zones: zs, own: own, body: body, bodyIt: bodyIt, bodyKey: bodyKey, bodyClass: shineClass(bodyIt), targetIt: tIt, hexZone: hex, paint: env.paint || [] };
    }
    function swatchHex(it, cx, userCol) {
        var c = []; if (userCol && userCol.hex) c.push(userCol.hex);
        (cx.own || []).concat(cx.body || []).forEach(function (z) { if (z.colour && /^#[0-9a-f]{6}$/i.test(z.colour)) c.push(z.colour); });
        (cx.paint || []).forEach(function (h) { c.push(h); });
        for (var i = 0; i < c.length; i++) { var l = lum(c[i]); if (l >= 0.16 && l <= 0.86) return c[i]; }
        return c[0] || '#3b82c4';
    }

    // ------------------------------------------------------------------ recipes: a few DIRECTIONS (not a list of ten similar things), each one a real finish
    // slot = { label, keys:[preferred...], find:{facets} | null, why: string | function(cx,it) }
    var SLOTS = {
        general: function (cx) {
            var flatBody = cx.bodyClass === 'flat';
            return [
                { keys: flatBody ? ['base::gloss', 'base::wet_look'] : ['base::satin', 'base::matte', 'base::satin'], why: flatBody ? 'Gloss against a flat body is the classic contrast: same colour, different shine.' : 'Satin or matte next to a glossy body reads as a deliberate two-tone: the shine difference does the work.' },
                { keys: ['base::f_pearl', 'base::pearl', 'base::f_satin_pearl'], why: 'A soft shimmer that moves with the light. Premium without shouting.' },
                { keys: ['base::f_candy', 'base::candy'], why: 'A deep, wet, see-through colour coat; strong colours look richer.' },
                { keys: ['base::f_metallic', 'base::gunmetal', 'base::f_matte_metallic'], why: 'Fine metal in the paint: sparkle in sun, calm in shade.' }
            ];
        },
        thin: function (cx) {
            var flatBody = cx.bodyClass === 'flat', coloured = (cx.own || []).some(function (z) { return z.colour && !lightNeutral(z.colour); });
            return [
                { keys: flatBody ? ['base::gloss', 'base::wet_look'] : ['base::matte', 'base::satin'], why: flatBody ? 'Gloss accents on a flat body: the shine difference is what makes a thin line read.' : 'Flat accents on a glossy body: the shine difference makes the stripe stand apart even in the same colour.' },
                coloured ? { keys: ['base::f_metallic', 'base::f_pearl', 'base::metallic'], why: 'A metallic glint that keeps the stripe colour (full chrome on a coloured stripe can go dark in the sim).' } : { keys: ['base::f_satin_chrome', 'base::satin_chrome', 'base::f_chrome', 'base::chrome'], why: 'A bright metal edge catches the light. Best on thin accents (loud on big areas).' },
                { keys: ['base::f_candy', 'base::candy', 'base::f_pearl'], why: 'Candy glows: a stripe looks lit from inside instead of just coloured.' },
                { keys: ['base::f_dark_chrome', 'base::f_brushed', 'base::f_anodized'], why: 'A darker metal accent: premium contrast on bright paint.' }
            ];
        },
        readable: function (cx) {
            return [
                { keys: ['base::gloss'], why: 'Plain gloss gives the cleanest edges. What makes numbers readable is the colour contrast behind them, not the finish.' },
                { keys: ['base::matte'], why: 'Flat: no glare in bright sun, so the shape of each digit stays crisp.' },
                { keys: ['base::satin', 'base::semi_gloss'], why: 'A little shine for depth, still no hot spots.' }
            ];
        },
        premium: function (cx) {
            return [
                { keys: ['base::f_pearl', 'base::pearl'], why: 'Pearl in your own colour is the quiet premium choice.' },
                { keys: ['base::f_candy', 'base::candy'], why: 'Candy gives depth you can see into; best on a strong, single colour.' },
                { keys: ['base::f_satin_chrome', 'base::gunmetal', 'base::f_brushed'], why: 'Satin metal on the trim and accents says "built, not painted".' },
                { keys: ['base::f_carbon_fiber', 'base::cerakote', 'base::ceramic'], why: 'A real material for one panel (hood, roof, splitter) lifts the whole car.' }
            ];
        },
        shimmer: function (cx) {
            return [
                { keys: ['base::f_pearl', 'base::pearl'], why: 'Pearl: the shimmer is fine and shifts with the angle. This is the not-cheap one.' },
                { keys: ['base::f_metallic', 'base::metallic'], why: 'Fine metal flake feel: sparkle in sun, calm in shade.' },
                { keys: ['base::f_satin_pearl'], why: 'Satin pearl: a softer, silkier shimmer for accents.' },
                { find: { sparkle: true, own: 'takes', min_quality: 80 }, why: 'Real glitter: keep it to one accent so it stays classy.' }
            ];
        },
        deep: function (cx) {
            return [
                { keys: ['base::f_candy', 'base::candy'], why: 'Candy is a coloured clear coat over metal, so the colour looks deep rather than flat.' },
                { keys: ['base::wet_look'], why: 'A thick wet clear coat: the colour looks deeper because the surface is so smooth.' },
                { keys: ['base::f_pearl', 'base::pearl'], why: 'Pearl adds a second tone under the colour.' },
                { keys: ['base::piano_black', 'base::gloss'], why: 'On dark colours, a perfect gloss looks bottomless.' }
            ];
        },
        retro: function (cx) {
            return [
                { keys: ['base::gloss', 'base::satin'], why: 'Baked enamel and satin are what old paint actually looked like: rich but not mirror-clean.' },
                { keys: ['base::matte', 'base::f_powder_coat'], why: 'Flat colour blocks, the 60s-70s way.' },
                { keys: ['base::f_metallic', 'base::metallic'], why: 'Metallic flake was THE 70s finish.' },
                { keys: ['base::satin'], why: 'A wrapped, satin look for the revival style.' }
            ];
        },
        stealth: function (cx) {
            return [
                { keys: ['base::matte'], why: 'The classic stealth look: no reflections at all.' },
                { keys: ['base::f_matte_metallic', 'base::cerakote'], why: 'Flat with a hint of metal, like a coated gun finish.' },
                { keys: ['base::f_dark_chrome', 'base::satin'], why: 'Dark mirror accents on a flat car: quiet menace.' }
            ];
        },
        metalbright: function (cx) {
            return [
                { keys: ['base::f_metallic', 'base::metallic'], why: 'Partial metal: keeps its colour in the sim because it is not a pure mirror.' },
                { keys: ['base::f_pearl', 'base::pearl'], why: 'Pearl looks metallic at an angle but stays bright.' },
                { keys: ['base::f_satin_chrome', 'base::satin_chrome'], why: 'Satin chrome reflects less, so it does not turn black.' },
                { keys: ['base::f_brushed', 'base::f_anodized'], why: 'Brushed or anodized metal keeps a visible colour and grain.' }
            ];
        },
        fastest: function (cx) {
            return [
                { keys: ['base::gloss'], why: 'A flat, plain spec: nothing extra to calculate.' },
                { keys: ['base::matte'], why: 'Same: a plain spec with no pattern layers.' },
                { keys: ['base::satin'], why: 'Plain, cheap to render.' },
                { keys: ['base::f_pearl', 'base::f_metallic'], why: 'Foundation metals are still plain flat specs: the look of metal without the cost of a texture.' }
            ];
        },
        pop: function (cx, big) { var s = big ? SLOTS.general(cx) : SLOTS.thin(cx); return [s[2], s[0], s[1], s[3]].filter(Boolean); }      // "pop" = intensity first (candy deepens the colour), then the shine contrast
    };
    var INTRO = {
        general: 'a few directions that work on an existing scheme',
        thin: 'for thin accents the finish has to read at a glance: a different shine or a metal edge does that',
        pop: 'pop usually comes from a difference in shine or colour with whatever is next to it',
        readable: 'you want clean edges and no glare',
        plain: 'for a plain, solid look the finish should add no effects at all: a smooth gloss, satin or matte in your own colour',
        premium: 'premium is mostly restraint: one real material or one rich colour coat, not many effects',
        shimmer: 'shimmer looks expensive when it is fine and in one place',
        deep: 'colour looks deeper when the surface looks thick and clear',
        retro: 'finishes that were actually around then',
        stealth: 'kill the reflections',
        metalbright: 'in the sim iRacing multiplies the paint colour by the metal level, so any normal colour turned fully metallic goes dark (a chrome part has to be painted white or nearly white). Partial-metal finishes keep their colour better',
        fastest: 'plain finishes are the cheapest to render: they are a flat spec with no texture or pattern layers. Heavy specials with patterns cost more',
        sparkleMost: 'these have the most sparkle in the whole catalogue'
    };

    // "the shiniest finish": ranked from the measured spec (roughness, metal, clearcoat) and the rendered palette of every finish, one per name family
    var SUPERS = {
        shiny: { label: 'the shiniest (lowest roughness, most metal)', keep: function (it) { return it.R && it.M; }, score: function (it) { return (255 - it.R[0]) / 255 + 0.6 * it.M[0] / 255 - (it.C && it.C[0] > 16 ? Math.min(0.3, (it.C[0] - 16) / 800) : 0); } },
        flat: { label: 'the flattest (highest roughness, no metal)', keep: function (it) { return it.R && it.M; }, score: function (it) { return it.R[0] / 255 - 0.5 * it.M[0] / 255 + (it.C ? it.C[0] / 1500 : 0); } },
        dark: { label: 'the darkest', keep: function (it) { return it.o === 1 && it.L != null; }, score: function (it) { return -it.L; } },
        light: { label: 'the lightest', keep: function (it) { return it.o === 1 && it.L != null; }, score: function (it) { return it.L; } },
        wild: { label: 'the most colourful (widest spread of hues)', keep: function (it) { return it.o === 1 && it.hs != null; }, score: function (it) { return (it.hs || 0) * Math.min(6, it.hc || 1); } },
        metal: { label: 'the most metallic', keep: function (it) { return it.M; }, score: function (it) { return it.M[0] + (it.M[1] || 0) * 0.1; } },
        textured: { label: 'the most textured', keep: function (it) { return it.fb && it.fb !== 'flat' && it.V != null; }, score: function (it) { return it.V + (it.fb === 'broad' ? 8 : 0); } }
    };
    function superCards(sup, excl, hex, n) {
        var a = AT(), d = a._data(), S = SUPERS[sup]; if (!S) return [];
        var pool = d.items.filter(function (it) { return (it._type === 'base' || it._type === 'monolithic') && !has(excl, it.k) && (it.q == null || it.q >= 60) && S.keep(it); });
        pool.sort(function (x, y) { return S.score(y) - S.score(x); });
        var seen = {}, out = [];
        pool.forEach(function (it) { var st = norm(it.n).split(' ')[0]; if (out.length >= n || seen[st]) return; seen[st] = 1; var c = card(it.k, (it.shine ? it.shine : '') + (it.metal && it.metal !== 'none' ? ', ' + it.metal + ' metal' : '') + (it.o === 1 ? '. Brings its own colours.' : '. Takes your colour.'), hex); if (c) out.push(c); });
        return out;
    }
    // "which finish should I avoid on the numbers": the honest list of what NOT to use (no Use buttons)
    function avoidAnswer(it0, cx, colour) {
        var a = AT(), tg = it0.target, label = tg ? tg.label : 'the car', keys = [], why = [];
        function add(k, w) { if (k && keys.indexOf(k) === -1 && a.lookup(k)) { keys.push(k); why.push(w); } }
        if (tg && tg.readable) { add(pick(['base::f_chrome', 'base::chrome'], []), 'Mirror: the digit edges disappear into reflections.'); add(findPick({ holo: true, multicolor: true, min_quality: 80 }, keys), 'Colour-shifting: the digit colour changes with the angle.'); add(findPick({ sparkle: true, own: 'takes', min_quality: 80 }, keys), 'Glitter: sparkle breaks the edges up at speed.'); }
        else if (!tg || tg.all || !tg.thin) { add(pick(['base::f_chrome', 'base::chrome'], []), 'Full mirror across a big area is loud and shows every flaw.'); add(findPick({ sparkle: true, own: 'takes', min_quality: 80 }, keys), 'Heavy glitter on a big area looks busy.'); add(findPick({ holo: true, multicolor: true, min_quality: 80 }, keys), 'Colour-shifting looks wild on a big area: keep it to a hero panel.'); }
        else { add(findPick({ holo: true, multicolor: true, min_quality: 80 }, keys), 'Colour-shifting fights the stripe colour.'); add(findPick({ sparkle: true, own: 'takes', min_quality: 80 }, keys), 'Heavy glitter makes thin lines look ragged.'); }
        var cards = keys.map(function (k, i) { var c = card(k, why[i], colour); if (c) c.noUse = true; return c; }).filter(Boolean);
        if (!cards.length) return null;
        return { text: 'Finishes I would avoid on ' + label + ' (shown on ' + (it0.colour ? it0.colour.name : 'your car\'s colour') + '):', cards: cards, target: tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : { id: 'body', label: 'the body' }, useLabel: label, colour: colour, shown: keys, kind: 'avoid', next: ['What finish should I use for ' + label, 'Review my finishes'] };
    }
    // ------------------------------------------------------------------ RANKED recommendations (2026-10-03): the WHOLE catalogue scored for this situation by SpbProRank, in three lanes
    //   keep      = shine-only finishes that keep the paint colours      complete = complete looks that bring their own palette, ranked by HARMONY with the buyer's colours
    //   texture   = spec patterns / paint patterns to layer on top
    // "Show me more" pages through the ranking (everything already shown is excluded), so there is always another option.
    function rankReady() { return !!(W.SpbProRank && W.SpbAICards && W.SpbAICards.ready()); }
    var MOOD_WORDS = [[/\b(?:aggressive|angry|menacing|mean|sinister|villain|evil)\b/, 'aggressive'], [/\b(?:luxury|luxurious|expensive|classy|posh|upscale|premium)\b/, 'luxury'], [/\b(?:elegant|refined|sophisticated)\b/, 'elegant'], [/\b(?:stealth|murdered|blacked|blackout|tactical)\b/, 'stealth'],
        [/\b(?:playful|fun|kids?|cute|cheerful)\b/, 'playful'], [/\b(?:rugged|dirt|dusty|muddy|tough|worn|weathered|gritty)\b/, 'rugged'], [/\b(?:techy|cyber\w*|futuristic|sci-?fi|digital)\b/, 'techy'], [/\b(?:natural|forest|earthy|organic|jungle)\b/, 'natural'],
        [/\b(?:spooky|halloween|haunted|creepy|ghost)\b/, 'spooky'], [/\b(?:cosmic|galaxy|space|nebula|stars?)\b/, 'cosmic'], [/\b(?:tropical|beach|island)\b/, 'tropical'], [/\b(?:icy|frozen|frost\w*|cold|arctic)\b/, 'icy'],
        [/\b(?:fiery|flames?|fire|lava|molten|hot)\b/, 'fiery'], [/\b(?:dreamy|pastel|soft)\b/, 'dreamy'], [/\b(?:industrial|raw|steel|factory)\b/, 'industrial'], [/\b(?:patriotic|american|flag|usa)\b/, 'patriotic'],
        [/\b(?:retro|vintage|throwback|old.?school)\b/, 'retro'], [/\b(?:clean|simple|minimal\w*|plain)\b/, 'clean'], [/\b(?:wild|crazy|insane|psychedelic|loud)\b/, 'wild']];
    var ERA_WORDS = [[/\b(?:50s|60s|fifties|sixties)\b/, '50s-60s'], [/\b(?:70s|seventies)\b/, '70s'], [/\b(?:80s|eighties)\b/, '80s'], [/\b(?:90s|nineties)\b/, '90s'], [/\b(?:futuristic|future|sci-?fi)\b/, 'futuristic']];
    var FIT_WORDS = [[/\bdirt\b|\blate model\b|\bsprint car\b/, 'dirt late model'], [/\bnascar\b|\bstock car\b|\bcup\b/, 'stock car'], [/\bgt3?\b|\bsports car\b|\btouring\b/, 'gt / sports car'], [/\bindy\w*\b|\bopen.?wheel\b|\bformula\b|\bf1\b/, 'open wheel'], [/\btruck\b|\boff.?road\b|\brally\b|\bpickup\b/, 'truck / off-road'], [/\bshow car\b|\bshowroom\b/, 'show car']];
    function wordsOf(table, t) { var o = []; table.forEach(function (r) { if (r[0].test(t)) o.push(r[1]); }); return o; }
    var GENERIC_FACET = /\b(?:aggressive|angry|mean|menacing|sinister|villain|evil|luxury|luxurious|expensive|classy|posh|upscale|premium|elegant|refined|sophisticated|stealth|murdered|blacked|blackout|tactical|playful|fun|kids?|cute|cheerful|clean|simple|minimal\w*|plain|wild|crazy|insane|loud|retro|vintage|throwback|old.?school|50s|60s|70s|80s|90s|fifties|sixties|seventies|eighties|nineties|nascar|stock car|gt3?|sports car|touring|indy\w*|open.?wheel|formula|f1|truck|pickup|show car|showroom|late model|sprint car)\b/g;
    var SITU_RE = /\b(?:tv|television|broadcast|stream(?:s|ing|ed)?|replays?|camera|cameras|photos?|photograph\w*|on track|the track|track|racing|races?|raceday|race day|pack|field|grid|eyes?|livery|liveries|sim|iracing|daylight|sunlight|readable|legible|reads?|clearly|visible|visibility|easy|easier|modern|contemporary|only|solely|exclusively|sponsors?|logos?|decals?|lettering|muscle|pony|hot ?rods?|rat ?rods?|dragsters?|lowriders?)\b/g;
    function rankQuery(it0, tg) {
        if (it0.negOnly) return '';      // a purely negative ask has no descriptive words to search with
        var t = stripState(stripNeg(String(it0.text || '').toLowerCase().replace(/[’`]/g, "'"))).replace(/\b(?:other than|rather than|instead of|besides)\b/g, 'not');      // one negation word the card search understands
        if (tg && tg.re) t = t.replace(tg.re, ' ');
        if (!W.__keepSituWords) { var glowAsk = /\b(?:glow\w*|neon|luminous|phosphor\w*|fluoresc\w*|reflective|blacklight)\b/.test(t); t = t.replace(SITU_RE, ' '); if (!glowAsk) t = t.replace(/\bnight\b/g, ' '); }      // situation words are facets, not looks
        if (!W.__keepClassWords) t = t.replace(/\b(?:dirt\s+)?(?:super\s+)?late\s+models?\b|\bdirt\s+(?:track\s+)?(?:car|racer|modified)s?\b|\bsprint\s+cars?\b|\bstreet\s+stocks?\b/g, ' ');      // a car CLASS is a facet (rankCtx fit), not a look
        try {
            var C = (W.SpbProDesign && W.SpbProDesign.COLOURS) || {}, partRe = '(?:stripes?|hood|roof|trunk|car|body|sides?|bumpers?|spoiler|numbers?|bands?|livery|scheme|paint|panel)';
            Object.keys(C).sort(function (x, y) { return y.length - x.length; }).forEach(function (n) { t = it0.kind !== 'find' ? t.replace(new RegExp('\\b' + n + '\\b', 'g'), ' ') : t.replace(new RegExp('\\b' + n + '(?=\\s+' + partRe + '\\b)', 'g'), ' '); });
        } catch (e) {}
        // goal / mood / era / car-class words are FACETS (rankCtx reads them from the raw text), not search words: only the leftover descriptive words ("watch", "bourbon barrel", "asphalt") retrieve
        if (it0.kind !== 'find') t = t.replace(GENERIC_FACET, ' ');      // only the GENERIC facet words are stripped: specific ones (halloween, tropical, dusty, dirt, galaxy ...) are what retrieves      // in a FIND those words ARE the search (dusty, dirt, weathered ...)
        if (it0.kind !== 'find') t = t.replace(/\b(?:pop|pops|stand(?:s)? out|premium|expensive|luxur\w*|shimmer\w*|sparkl\w*|glitter\w*|deeper|deep|depth|richer|rich|retro|stealth|readable|metallic|aggressive|clean|simple|subtle|subtler|calm|calmer|quiet|quieter|softer|louder|bold|bolder|flashy|flashier|wilder|crazier|shinier|shiny|simpler|understated|dramatic|exciting|extreme|toned|down|different|another|other|else|next|again|special|exotic|complete|textures?|patterns?|spec|layer|top|suit|suits|match|matches|nicer|better|best|good|great|cool|nice|classy|colou?rs?|colou?red|bit|little|touch|hint|some|look|looks|feel|finish|finishes|part|panel|paint)\b/g, ' ');
        var out = cleanQuery(t).replace(/\b(?:what|which|should|would|could|put|use|goes|well|work|works|looks?|make|them|they|it|my|please|recommend|suggest|ideas?|options?|and|but|so|that|is|are|be|to|too|very|really|with|for|at|if|then|than|this|these|those|can|will|do|does|i|a|an|the|of|in|on|more|less|much|way|lot|extra|even|still|just|also|now|ok|okay|yes|thanks|stripes?|hood|roof|sides?|body|about|how|choose|pick|makes?|stay|one|two|three|four|five|six|\d+)\b/g, ' ').replace(/\s+/g, ' ').trim();
        // "kill the shine", "too glossy", "looks like plastic": the shine is excluded (dislikes) and the retrieval pushes toward the low-sheen family instead of searching the complaint's own words
        if (it0.dislikes && it0.dislikes.indexOf('glossy') !== -1 && !/\b(?:matte|satin|eggshell|flat|silk|dull|velvet)\b/.test(out)) out = (out + ' matte satin soft').trim();
        var tk =W.SpbAICards && W.SpbAICards.toks ? W.SpbAICards.toks(out) : [out];
        return tk.length ? out : '';
    }
    function hexList(zs) { return zs.map(function (z) { return z.colour; }).filter(function (h) { return /^#[0-9a-f]{6}$/i.test(String(h || '')); }); }
    function rankCtx(it0, cx, kind) {
        var tg = it0.target, tc = hexList(cx.own), bc = hexList(cx.body), all = [], seen = {}, goal = it0.goal, nov = 1, t = String(it0.text || '').toLowerCase();
        tc.concat(bc, cx.paint || []).forEach(function (h) { if (!seen[h]) { seen[h] = 1; all.push(h); } });
        if (it0.colour && it0.colour.hex) all.unshift(it0.colour.hex);
        if (it0.mod === 'bold') { goal = 'pop'; nov = 2; } else if (it0.mod === 'calm') { goal = 'subtle'; nov = 0; }
        if (kind === 'general' || kind === 'thin') { if (goal === 'fastest' || goal === 'sparkleMost') goal = null; }
        var seed = 1; for (var i = 0; i < t.length; i++) seed = (seed * 31 + t.charCodeAt(i)) | 0;
        if (it0.mod === 'more') seed += 7;
        return { target: tg, goal: goal, query: rankQuery(it0, tg), mood: wordsOf(MOOD_WORDS, t), era: wordsOf(ERA_WORDS, t), fit: wordsOf(FIT_WORDS, t), novelty: nov, seed: seed,
            colours: { target: (it0.colour && it0.colour.hex) || tc[0] || null, body: bc[0] || (cx.paint && cx.paint[0]) || null, scheme: all }, bodyClass: cx.bodyClass, avoid: it0.dislikes || null };
    }
    function rankedCard(row, lane, colour) {
        var c = card(row.key, '', colour); if (!c) return null;
        var why = []; (row.why || []).forEach(function (w) { if (why.indexOf(w) === -1) why.push(w); });
        c.why = firstSentence(row.look || c.why, 104) + (why.length ? ' — ' + why.slice(0, 2).join('; ') : '');
        c.lane = lane; c.loud = row.loud; c.busy = row.busy;
        if (lane === 'complete') c.tag = 'complete look: brings its own colours';
        else if (lane === 'texture') c.tag = c.type === 'spec' ? 'shine texture: keeps your colours' : 'paint pattern: adds colour on top';
        return c;
    }
    function recommendRanked(it0, env, cx, colour, kind, excl) {
        var tg = it0.target, R = W.SpbProRank, maxc = it0.count ? Math.max(1, Math.min(6, it0.count)) : 5, ctx = rankCtx(it0, cx, kind), plan;
        if (it0.keepColours) ctx.specOnly = true;      // "keep my colours": textures only if they change the shine and nothing else
        // The FIRST answer to a plain "what finish for X" is the sensible, proven choices ranked for this part and goal (judged: exotic looks make a poor first answer). Wider lanes open
        // when they describe a look, ask for complete looks / textures, or press "show me more" (page by page, never repeating).
        var described = !!ctx.query, page = it0.prev ? (it0.prev.page != null ? it0.prev.page : (it0.prev.shown ? Math.floor(it0.prev.shown.length / 5) : 0)) : 0;
        // the part's CURRENT finish is never the suggestion ("Gloss" for stripes that are already gloss)
        (zonesFor(tg || BODY, env.zones || []) || []).forEach(function (z) { if (z.finishKey && excl.indexOf(z.finishKey) === -1) excl.push(z.finishKey); });
        if (tg && tg.readable) { plan = [['keep', 4]]; ctx.classic = true; }      // numbers / names stay plain shine-only finishes whatever lane was asked for
        else if (it0.lanes && !it0.mod) { plan = it0.lanes.map(function (l) { return [l[0], Math.min(l[1], maxc)]; }); ctx.classic = (it0.keepColours && (kind === 'plain' || kind === 'subtle') && !it0.lanes.some(function (l) { return l[0] === 'texture'; })) ? true : false; }      // a semantic claim chose its own lanes (colours kept -> shine-only + spec textures)
        else if (it0.lane) plan = [[it0.lane, maxc]];
        else if (described) plan = (tg && tg.thin) ? [['keep', 2], ['texture', 1], ['complete', 2]] : [['keep', 1], ['complete', 3], ['texture', 1]];
        else if (it0.mod === 'more' || it0.mod === 'bold') plan = page <= 1 ? [['keep', 3], ['complete', 2]] : [['keep', 2], ['complete', 2], ['texture', 1]];
        else plan = [['keep', 5]];
        if (page >= 3 || it0.mod === 'bold') ctx.novelty = 2;
        if ((page >= 2 || it0.lane || it0.mod === 'bold') && !(tg && tg.readable)) ctx.classic = false;      // later pages / a lane request widen to the takes-colour effects and every complete look
        var cards = [], used = excl.slice(), lanes = {}, sum = 0;
        // a DESCRIBED ask ("molten orange abstract panel, loops and flowing contours") leads with the best meaning matches of the whole sentence (negations removed): judged / truth-scored better than the ranked lanes alone
        if ((it0.semantic || it0.modelClaim) && ctx.query && !it0.mod && !(tg && tg.readable)) {
            // 2026-10-02 (overnight, Codex L2 truth set): for DESCRIBED asks with texture words ("mossy grain", "fine weave") the hand-labelled good answers are complete finishes
            // (384 of 385 good keys; none in the spec / pattern lanes) while this block used to search ONLY spec + pattern (526 texture cards served, 2 hits). Truth hit 48% -> 54% (dev 47 -> 52,
            // holdout 49 -> 56.5), picture-judged gold 0.80 -> 0.82. The best whole-sentence matches now come from the finishes; the plan's texture lane follows as the layer-on option.
            // (window.__texSearchFirst = true restores the old behaviour for A/B runs.)
            var lane0 = it0.lanes && it0.lanes[0] ? it0.lanes[0][0] : null, tex0 = lane0 === 'texture' && !!W.__texSearchFirst, sq = stripState(stripNeg(String(it0.text || '').toLowerCase()));
            // the PART the painter names ("...glows at night for the stripes") is where the look goes, not a word of the look: "for the stripes" must not retrieve Tiger Stripe Field (only the locative use is stripped: for / on / to the <part>; A/B flag: window.__keepTgWords)
            sq = stripPart(sq, tg);
            try {
                var srows = R.search(sq, { limit: 3, types: tex0 ? (it0.keepColours ? ['spec'] : ['spec', 'pattern']) : ['base', 'monolithic'], own: (it0.keepColours && !tex0) ? 'takes' : undefined, exclude: used.slice(), avoid: it0.dislikes });
                var addRow = function (row) { var ri = row.key ? AT().lookup(row.key) : null; if (!ri) return; var ln = (ri._type === 'spec' || ri._type === 'pattern') ? 'texture' : (ri.o === 1 ? 'complete' : 'keep'), c = rankedCard({ key: row.key, look: (W.SpbAICards.card(row.key) || {}).look, why: row.why }, ln, colour); if (c) { cards.push(c); used.push(row.key); lanes[ln] = (lanes[ln] || 0) + 1; } };
                srows.forEach(addRow);
                // the texture lane that follows is searched by the same words too (the ranked lane alone fills it with the canon carbon weaves whatever was asked)
                if (lane0 === 'texture' && !it0.keepColours && !tex0) R.search(sq, { limit: 2, types: ['spec', 'pattern'], exclude: used.slice(), avoid: it0.dislikes }).forEach(addRow);
            } catch (esr) {}
        }
        plan.forEach(function (p) { var n = Math.min(p[1], maxc - cards.length); if (n <= 0) return; ctx.lane = p[0]; ctx.limit = n; ctx.exclude = used; ctx.offset = 0;
            var r = R.suggest(ctx); r.rows.forEach(function (row) { var c = rankedCard(row, p[0], colour); if (c) { cards.push(c); used.push(row.key); lanes[p[0]] = (lanes[p[0]] || 0) + 1; } }); });
        if (cards.length < Math.min(maxc, 4)) { ctx.lane = 'keep'; ctx.limit = Math.min(maxc, 4) - cards.length; ctx.exclude = used; var r2 = R.suggest(ctx); r2.rows.forEach(function (row) { var c = rankedCard(row, 'keep', colour); if (c) { cards.push(c); used.push(row.key); } }); }
        try { var nm0 = findFinishesIn(stripState(posText(it0.text || '')), 1)[0]; if (nm0 && !dislikedKey(nm0.key, it0) && !it0.mod && it0.lane !== 'texture' && (it0.not || []).indexOf(nm0.key) === -1 && excl.indexOf(nm0.key) === -1 && !cards.some(function (c) { return c.key === nm0.key; })) { var nc = card(nm0.key, 'You named this one.', colour); if (nc) { nc.lane = 'keep'; cards.unshift(nc); if (cards.length > maxc) cards.pop(); } } } catch (enm) {}
        if (!cards.length) return null;
        var where = tg ? tg.label : 'the car', now = nowText(tg, cx), lead = INTRO[kind] || INTRO.general;
        var mixed = (lanes.keep ? 'shine-only options that keep your paint' : '') + (lanes.complete ? (lanes.keep ? ', ' : '') + 'complete looks whose palette suits your colours' : '') + (lanes.texture ? (lanes.keep || lanes.complete ? ' and ' : '') + 'a texture to layer on top' : '');
        var text = (it0.mod === 'more' ? 'More options for ' + where + ' (nothing repeated):' : it0.mod === 'calm' ? 'Calmer options for ' + where + ':' : it0.mod === 'bold' ? 'Bolder options for ' + where + ':' : (tg ? 'For ' + where : 'For your car') + ': ' + lead + '.') + (now ? ' ' + now : '');
        if (it0.mod !== 'more' && mixed && kind !== 'readable' && (lanes.complete || lanes.texture)) text += ' I searched the whole catalogue and picked ' + mixed + '.';
        else if (!it0.lane && lanes.keep && !lanes.complete && !lanes.texture && kind !== 'readable' && it0.mod !== 'more') text += ' These are the proven choices for that. Want something more special? Ask for complete looks that suit your colours, or a texture on top.';
        if (it0.not && it0.not.length) text += ' (Left out: ' + it0.not.map(function (k) { var x = AT().lookup(k); return x ? x.n : k; }).join(', ') + '.)';
        if (it0.dislikes && it0.dislikes.length) text += ' I am leaving out anything ' + it0.dislikes.join(' / ') + '.';
        if (CAP_RE.test(String(it0.text || ''))) text += ' Heads-up: ' + CAP_NOTE;
        if (kind === 'readable') text += ' Avoid chrome, glitter and colour-shifting finishes on numbers: they break up the digit edges at speed.';
        if (it0.colour) text += ' Swatches are shown on ' + it0.colour.name + '.'; else if (colour && (cx.hexZone || (cx.paint && cx.paint[0]))) text += ' Swatches are shown on your car\'s colour.';
        return pack(it0, cx, cards, text, colour);
    }

    function recommend(it0, env) {
        var a = AT(), tg = it0.target, cx = ctxOf(tg, env), gk = it0.goal, big = !tg || tg.all || !tg.thin;
        var colour = swatchHex(null, cx, it0.colour);
        if (it0.avoid) return avoidAnswer(it0, cx, colour);
        if (gk === 'super' && it0.sup) {
            var sc = superCards(it0.sup, (it0.prev && it0.prev.shown ? it0.prev.shown : []).concat(it0.not || []), colour, Math.max(1, Math.min(6, it0.count || 4)));
            if (!sc.length) return null;
            return pack(it0, cx, sc, 'These are ' + SUPERS[it0.sup].label + ' in the whole catalogue, one per family. Very extreme finishes are loud on big areas: try them on one panel or an accent first.', colour);
        }
        var excl = ((it0.mod === 'more' || it0.mod === 'calm' || it0.mod === 'bold' || it0.mod === 'lane') && it0.prev && it0.prev.shown ? it0.prev.shown.slice() : []).concat(it0.not || []), shown = [], maxc = Math.max(1, Math.min(4, it0.count || 4));
        var slots, kind = gk || (tg && tg.readable ? 'readable' : (big ? 'general' : 'thin'));
        if (it0.avoid) return avoidAnswer(it0, cx, colour);
        if (gk === 'sparkleMost') {
            var d = a._data(), pool = d.items.filter(function (it) { return (it._type === 'base' || it._type === 'monolithic') && it.sk === 1 && !has(excl, it.k) && (it.q == null || it.q >= 60); });
            pool.sort(function (x, y) { return (y.sp || 0) - (x.sp || 0) || (y.q || 0) - (x.q || 0); });
            var seenStem = {}, cards = [];
            pool.forEach(function (it) { var st = norm(it.n).split(' ')[0]; if (cards.length >= 4 || seenStem[st]) return; seenStem[st] = 1; cards.push(card(it.k, 'Sparkle ' + it.sp + '/100' + (it.o === 1 ? '; brings its own palette' : '; takes your colour'), colour)); });
            if (!cards.length) return null;
            return pack(it0, cx, cards.filter(Boolean), 'These have the most sparkle in the whole catalogue, shown on ' + (it0.colour ? it0.colour.name : 'your colour') + '. Very sparkly finishes are loud on big areas: use them on one panel or an accent.', colour);
        }
        if (rankReady()) { var rk = recommendRanked(it0, env, cx, colour, kind, excl.concat(it0.mod ? [] : [])); if (rk) return rk; }
        slots = (SLOTS[kind] || SLOTS.general)(cx, big);
        if (it0.mod === 'calm') slots = slots.filter(function (s) { return !s.find; }).slice(0, 3);
        if (it0.mod === 'bold') slots = [{ keys: ['base::f_chrome', 'base::chrome'], why: 'Mirror: the loudest shine there is. Best on accents.' }, { keys: ['base::f_candy', 'base::candy'], why: 'Candy: the deepest colour.' }, { find: { holo: true, multicolor: true, min_quality: 80 }, why: 'A colour-shifting special that changes with the angle.' }, { find: { sparkle: true, min_quality: 85 }, why: 'Real glitter.' }].concat(slots).slice(0, 4);
        var cards2 = [];
        slots.forEach(function (s) {
            if (cards2.length >= maxc) return;
            var key = s.keys ? pick(s.keys, excl.concat(shown)) : null;
            if (!key && s.find) key = findPick(JSON.parse(JSON.stringify(s.find)), excl.concat(shown));
            if (!key && s.keys && it0.mod === 'more') key = findPick({ query: s.keys[0].replace(/^base::(?:f_)?/, '').replace(/_/g, ' '), min_quality: 60 }, excl.concat(shown));
            if (!key) return; var c = card(key, typeof s.why === 'function' ? s.why(cx) : s.why, colour); if (c) { cards2.push(c); shown.push(key); }
        });
        try { var nm0 = findFinishesIn(stripState(posText(it0.text || '')), 1)[0]; if (nm0 && !dislikedKey(nm0.key, it0) && !it0.mod && it0.lane !== 'texture' && (it0.not || []).indexOf(nm0.key) === -1 && excl.indexOf(nm0.key) === -1 && !cards2.some(function (c) { return c.key === nm0.key; })) { var nc = card(nm0.key, 'You named this one.', colour); if (nc) { cards2.unshift(nc); if (cards2.length > maxc) cards2.pop(); shown.push(nm0.key); } } } catch (enm) {}
        if (!cards2.length) return null;
        var lead = INTRO[kind] || INTRO.general;
        var where = tg ? tg.label : 'the car';
        var now = nowText(tg, cx);
        var text = (it0.mod === 'more' ? 'Here are some different ones for ' + where + '.' : it0.mod === 'calm' ? 'Calmer options for ' + where + ':' : it0.mod === 'bold' ? 'Bolder options for ' + where + ':' : (tg ? 'For ' + where : 'For your car') + ': ' + lead + '.') + (now ? ' ' + now : '');
        if (it0.not && it0.not.length) text += ' (Left out: ' + it0.not.map(function (k) { var x = a.lookup(k); return x ? x.n : k; }).join(', ') + '.)';
        if (kind === 'readable') text += ' Avoid chrome, glitter and colour-shifting finishes on numbers: they break up the digit edges at speed.';
        if (it0.colour) text += ' Swatches are shown on ' + it0.colour.name + '.'; else if (colour && (cx.hexZone || (cx.paint && cx.paint[0]))) text += ' Swatches are shown on your car\'s colour.';
        return pack(it0, cx, cards2, text, colour);
    }
    function nowText(tg, cx) {
        var bits = [];
        if (cx.targetIt && tg) bits.push(tg.label.replace(/^the /, 'Your ') + ' ' + (/s$/.test(tg.label) ? 'are' : 'is') + ' ' + cx.targetIt.n + ' (' + (cx.targetIt.shine || 'unknown shine') + ')');
        if (cx.bodyIt && (!tg || !cx.targetIt || tg.all)) bits.push('Your body is ' + cx.bodyIt.n + ' (' + (cx.bodyIt.shine || 'unknown shine') + ')');
        return bits.length ? bits.join('; ') + '.' : '';
    }
    // ------------------------------------------------------------------ KITS (2026-10-03): a finish PLAN for the whole car, not one part: body + stripes + numbers (+ a hero panel), three styles, applied in ONE step
    // Each role is ranked on its own (SpbProRank) but the roles are chosen TOGETHER: the accents pick a different shine from the body, numbers are always plain, no kit repeats another's finishes.
    function kits(it0, env) {
        if (!rankReady()) return null;
        var R = W.SpbProRank, a = AT(), zs = (env.zones || []).filter(function (z) { return !z.muted; }), cx = ctxOf(BODY, env), prevShown = it0.prev && it0.prev.shown ? it0.prev.shown.slice() : [];
        var STRIPES = TARGETS[2], NUMS = TARGETS[0], HOOD = TARGETS[3], roles = [{ id: 'body', tg: BODY, label: 'Body' }];
        if (zonesFor(STRIPES, zs).length) roles.push({ id: 'stripes', tg: STRIPES, label: 'Stripes' });
        if (zonesFor(NUMS, zs).length) roles.push({ id: 'numbers', tg: NUMS, label: 'Numbers' });
        var ROOF = null; TARGETS.forEach(function (x) { if (x.id === 'roof') ROOF = x; });
        var VARS = [{ name: 'Classic', blurb: 'Proven finishes: calm, clean and easy to read.', goal: null, nov: 0, hero: false, tex: null }, { name: 'Premium', blurb: 'Richer materials: pearl, metal and candy depth, still tasteful, plus a fine shine texture on the hood.', goal: 'premium', nov: 1, hero: false, tex: HOOD },
            { name: 'Bold', blurb: 'A statement: stronger finishes, a complete-look hero panel on the hood and a texture on the roof.', goal: 'pop', nov: 2, hero: true, tex: ROOF }];
        var usedBy = {}, all = [], out = [], scheme = hexList(zs).concat(cx.paint || []);
        VARS.forEach(function (v) {
            if (it0.mod === 'bold') { v.nov = Math.min(2, v.nov + 1); v.goal = v.goal || 'pop'; } else if (it0.mod === 'calm') { v.nov = 0; v.goal = 'subtle'; v.hero = false; }
            var items = [], bodyClass = null, bodyKey = null, rl = roles.slice(); if (v.hero) rl.push({ id: 'hood', tg: HOOD, label: 'Hood (hero)', lane: 'complete' });
            if (v.tex && it0.mod !== 'calm') rl.push({ id: 'tex', tg: v.tex, label: 'Texture (' + v.tex.id + ')', lane: 'texture' });
            rl.forEach(function (r) {
                var tc = hexList(zonesFor(r.tg, zs)), colour = swatchHex(null, ctxOf(r.tg, env), null), ex = prevShown.concat(all, items.map(function (x) { return x.card.key; }), zonesFor(r.tg, zs).map(function (z) { return z.finishKey; }).filter(Boolean));
                var ctx = { avoid: it0.dislikes || null, target: r.tg, goal: r.id === 'numbers' ? 'readable' : v.goal, lane: r.lane || 'keep', novelty: v.nov, exclude: ex, limit: 1, offset: 0, seed: it0.prev ? 17 : 11,
                    colours: { target: tc[0] || null, body: hexList(zonesFor(BODY, zs))[0] || (cx.paint && cx.paint[0]) || null, scheme: scheme }, bodyClass: r.id === 'body' ? null : bodyClass };
                if (r.lane === 'complete' || r.lane === 'texture') ctx.classic = false; else if (r.id === 'numbers') ctx.classic = true;
                if (r.id === 'stripes' || r.id === 'hood') ctx.limit = 8;
                if (r.lane === 'texture') { ctx.goal = v.goal === 'pop' ? 'pop' : 'premium'; ctx.novelty = Math.min(v.nov, 1); ctx.limit = 14; }
                var rows = R.suggest(ctx).rows; if (r.lane === 'texture') rows = rows.filter(function (x) { var xi = a.lookup(x.key); return xi && xi._type === 'spec'; }); if (!rows.length) return;
                var pickRow = rows[0];
                if ((r.id === 'stripes') && bodyKey) { for (var qi = 0; qi < rows.length; qi++) { var qit = a.lookup(rows[qi].key); if (rows[qi].key !== bodyKey && qit && shineClass(qit) !== bodyClass) { pickRow = rows[qi]; break; } } }
                rows = [pickRow];
                var c = rankedCard(rows[0], ctx.lane, colour); if (!c) return; c.target = { id: r.tg.id, label: r.tg.label };
                (usedBy[r.id] = usedBy[r.id] || []).push(rows[0].key); all.push(rows[0].key);
                if (r.id === 'body') { var bi = a.lookup(rows[0].key); bodyClass = bi ? shineClass(bi) : null; bodyKey = rows[0].key; }
                items.push({ role: r.label, target: c.target, card: c });
            });
            if (items.length) out.push({ name: v.name, blurb: v.blurb, items: items });
        });
        if (!out.length) return null;
        var text = 'Here are ' + out.length + ' finish kits for your whole car (' + roles.map(function (r) { return r.label.toLowerCase(); }).join(' + ') + '). In each kit the accents have a different shine from the body, the numbers stay plain, and no finish is used twice across the kits. A texture only changes the shine pattern: your colours stay. **Use this kit** applies the whole kit in one step (one Undo).';
        out.forEach(function (k) { text += '\n- **' + k.name + '**: ' + k.items.map(function (i) { return i.role + ' ' + i.card.name; }).join(', ') + '. ' + k.blurb; });
        var cards = [], seenK = {}; out.forEach(function (k) { k.items.forEach(function (i) { if (!seenK[i.card.key]) { seenK[i.card.key] = 1; var c = JSON.parse(JSON.stringify(i.card)); c.noUse = true; cards.push(c); } }); });
        return { text: text, cards: cards, kits: out.map(function (k) { return { name: k.name, blurb: k.blurb, items: k.items.map(function (i) { return { role: i.role, target: i.target, card: i.card }; }) }; }), target: { id: 'body', label: 'the body' }, useLabel: 'the body', colour: null, shown: prevShown.concat(all), kind: 'kit', next: ['Show me different kits', 'Something bolder', 'Review my finishes'] };
    }

    function pack(it0, cx, cards, text, colour) {
        var shown = (it0.mod && it0.prev ? it0.prev.shown : []).concat(cards.map(function (c) { return c.key; })).filter(function (k, i, arr) { return arr.indexOf(k) === i; });
        var tg = it0.target;
        var useLabel = tg ? tg.label : 'the body';
        var out = { text: text, cards: cards, target: tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : { id: 'body', label: 'the body' }, useLabel: useLabel, colour: colour, shown: shown, kind: it0.kind, goal: it0.goal, sup: it0.sup, lane: it0.lane || null, page: it0.mod && it0.prev ? ((it0.prev.page != null ? it0.prev.page : Math.floor((it0.prev.shown || []).length / 5)) + 1) : 0,
            next: ['Show me more', 'Show complete looks that suit my colours', 'Add a texture on top'] };
        if (it0.act && cards.length) { out.autoApply = 0; out.text = text + ' You asked me to do it, so I am applying the first one on ' + useLabel + ' (Undo takes it back); the others are one click away.'; out.next = ['Something bolder', 'Something calmer', 'Show me more']; }
        return out;
    }

    // ------------------------------------------------------------------ find: "show me chrome finishes"
    function find(it0, env) {
        var a = AT(), q = it0.query || '', cx = ctxOf(it0.target, env), colour = swatchHex(null, cx, it0.colour);
        if (!q.replace(/\s+/g, '')) return recommend({ kind: 'recommend', target: it0.target, colour: it0.colour, goal: null, text: it0.text }, env);
        var skip = (it0.skip || []).concat(it0.not || []), rows = [];
        if (it0.dislikes && it0.dislikes.length && W.SpbProRank && W.SpbProRank.avoidSet) { var avs = W.SpbProRank.avoidSet(it0.dislikes); for (var avk in avs) skip.push(avk); }
        var kc = it0.keepColours != null ? !!it0.keepColours : KEEP_RE.test(String(it0.text || '').toLowerCase());      // R01: asked to keep the paint -> only finishes that take the zone colour
        if (rankReady()) {
            rows = W.SpbProRank.search(rankQuery(it0, it0.target) || q, { limit: 14, exclude: skip, types: ['base', 'monolithic'], own: kc ? 'takes' : undefined }).map(function (r) { return { key: r.key }; });
            try { var named = findFinishesIn(posText(it0.text || q), 3).map(function (x) { return x.key; }).filter(function (k) { return skip.indexOf(k) === -1; }); if (named.length) rows = named.map(function (k) { return { key: k }; }).concat(rows.filter(function (r) { return named.indexOf(r.key) === -1; })); } catch (efn) {}
        if (kc) rows = rows.filter(function (r) { var ri = a.lookup(r.key); return !(ri && ri.o === 1 && (ri._type === 'base' || ri._type === 'monolithic')); });
        }
        if (rows.length < 3) rows = a.find({ query: q, type: 'finish', limit: 20, diverse: true, min_quality: 40, exclude: skip, own: kc ? 'takes' : undefined }) || [];
        if (!rows.length) rows = a.find({ query: q, type: 'finish', limit: 20, diverse: true, exclude: skip, own: kc ? 'takes' : undefined }) || [];
        var first = resolveName(posText(q)); var fi0 = first ? a.lookup(first) : null; if (first && skip.indexOf(first) === -1 && !(kc && fi0 && fi0.o === 1 && (fi0._type === 'base' || fi0._type === 'monolithic'))) rows = [{ key: first }].concat(rows.filter(function (r) { return r.key !== first; }));
        if (!rows.length) return null;
        var cards = [], seen = {};
        var capF = it0.count ? Math.max(1, Math.min(6, it0.count)) : 6;
        rows.forEach(function (r) { if (cards.length >= capF || seen[r.key]) return; seen[r.key] = 1; var it = a.lookup(r.key); var why = firstSentence((it && it.d) || r.about || '', 118); if (why.length < 24) { try { var cd0 = W.SpbAICards && W.SpbAICards.ready() && W.SpbAICards.card(r.key); if (cd0 && cd0.look) why = firstSentence(cd0.look, 118); } catch (ecw) {} } var c = card(r.key, why, colour); if (c) cards.push(c); });
        if (!cards.length) return null;
        var qs = q || 'that';
        var qt = norm(q).split(' ').filter(function (w) { return w.length > 2; }), hit = cards.some(function (c) { var h = norm(c.name + ' ' + c.why + ' ' + c.look); return qt.length === 0 || qt.some(function (w) { return h.indexOf(w.replace(/(ing|ed|es|s)$/, '')) !== -1; }); });
        var text = (hit ? 'Here are the closest matches in the catalogue for “' + qs + '”, best first' : 'I do not have a finish that is clearly “' + qs + '”. These are the nearest in feel') + ' (swatches on ' + (it0.colour ? it0.colour.name : 'your car\'s colour') + '). Pick one to try it, or tell me what to change (“more sparkle”, “flatter”, “darker”).';
        var tgt = it0.target ? { id: it0.target.id, label: it0.target.label } : { id: 'body', label: 'the body' };
        if (it0.tryMode && hit) text = 'Here is ' + (cards[0] ? cards[0].name : qs) + ' for ' + tgt.label + ', with the closest alternatives (swatches on ' + (it0.colour ? it0.colour.name : 'your car\'s colour') + '). Press Use to try it: nothing changes until you do.';
        if (it0.howto) text = 'Pick the finish you want for ' + tgt.label + ' and press Use: nothing changes until you do. (You can also just say it as an order, for example “make ' + tgt.label + ' ' + (it0.query || 'matte') + '”, and I will do it straight away.)';
        return { text: text, cards: cards, target: tgt, useLabel: tgt.label, colour: colour, shown: cards.map(function (c) { return c.key; }), kind: 'find', next: ['Show me more', 'Something calmer', 'Something bolder'] };
    }

    // ------------------------------------------------------------------ plain-language definitions of the finishes people name (real-world meaning first, then the catalogue measurements)
    var NOTES = {
        'gloss': 'Standard shiny paint under a clear coat: sharp reflections, the safe default under numbers and sponsors.',
        'satin': 'A low-sheen finish between gloss and matte: soft highlights, hides small flaws, looks modern.',
        'matte': 'No clear-coat shine: light scatters, so there are no sharp reflections. Colours look softer and flatter. The stealth look.',
        'wet look': 'Gloss with a very thick, very smooth clear coat feel: deep, liquid reflections.',
        'pearl': 'Paint with tiny pearlescent (mica) particles: a soft shimmer and a slight colour shift as the angle changes. Subtle.',
        'metallic': 'Paint with fine aluminium flake: it sparkles in sun and looks richer than a plain colour.',
        'candy': 'A translucent, strongly tinted coat over a bright metallic base. The colour looks very deep and saturated, like boiled sweets.',
        'chrome': 'A mirror metal surface: it reflects everything around it, so it shows the environment more than a colour. Loud on big areas, great on trim.',
        'satin chrome': 'Chrome with a satin surface: still bright metal, but the reflections are soft instead of mirror-sharp.',
        'dark chrome': 'Mirror metal tinted dark: chrome reflections with a black cast.',
        'carbon fiber': 'The woven carbon pattern under clear coat: a technical, race-car texture.',
        'brushed': 'Fine parallel grain from brushing: reads as raw metal with streaky highlights.',
        'anodized': 'A coloured aluminium surface: fine, flat-ish metal like machined parts.',
        'cerakote': 'A thin ceramic coating used on race parts and firearms: flat, tough and slightly metallic.',
        'powder coat': 'A baked powder finish: thick, even and semi-matte.',
        'vinyl wrap': 'The look of a wrapped car: even satin colour with little depth.',
        'frozen': 'A frosted metal look: satin, cool and slightly metallic.'
    };
    function noteOfKey(key) {
        var best = null, names = Object.keys(CONCEPT);
        names.forEach(function (n) { if (NOTES[n] && CONCEPT[n].indexOf(key) !== -1 && (!best || n.length > best.length)) best = n; });
        return best ? NOTES[best] : null;
    }

    // ------------------------------------------------------------------ compare
    function compare(it0, env) {
        var a = AT(), keys = [], names = [], cx = ctxOf(it0.target, env), colour = swatchHex(null, cx, it0.colour);
        var same = [];
        it0.sides.forEach(function (s) { var k = resolveName(s, keys), ik = k && a.lookup(k); if (ik && keys.some(function (x) { return a.lookup(x).n === ik.n; })) { same.push(s); return; } if (k) { keys.push(k); names.push(s); } });
        if (keys.length === 1 && same.length) { var one = a.lookup(keys[0]); return { text: '“' + names[0] + '” and “' + same.join('”, “') + '” are the same finish here: **' + one.n + '**. ' + (noteOfKey(keys[0]) || ''), cards: [card(keys[0], '', colour)].filter(Boolean), target: { id: 'body', label: 'the body' }, useLabel: 'the body', colour: colour, shown: keys, kind: 'compare', next: ['Show me more finishes like this'] }; }
        if (keys.length < 2) return null;
        var its = keys.map(function (k) { return a.lookup(k); }), cards = [], lines = [];
        its.forEach(function (it, i) {
            var det = a.details(it.k) || {}, bf = (det.best_for || []).slice(0, 2).join('; '), nt = noteOfKey(it.k);
            cards.push(card(it.k, firstSentence(it.d || '', 118), colour));
            lines.push('- **' + it.n + '**: ' + (nt ? nt + ' In Shokker: ' : '') + [it.shine, (it.metal && it.metal !== 'none' ? it.metal + ' metal' : 'no metal'), (it.sk === 1 ? 'sparkles' : null), (it.o === 1 ? 'brings its own colours' : 'takes your colour')].filter(Boolean).join(', ') + (bf ? '. Best for: ' + bf : ''));
        });
        var diff = [], A = its[0], B = its[1];
        if (A.shine !== B.shine) diff.push(A.n + ' reads ' + (A.shine || '?') + ' and ' + B.n + ' reads ' + (B.shine || '?'));
        if (A.metal !== B.metal) diff.push('metal: ' + A.n + ' is ' + (A.metal || 'none') + ', ' + B.n + ' is ' + (B.metal || 'none'));
        if (A.sk !== B.sk) diff.push((A.sk === 1 ? A.n : B.n) + ' sparkles; ' + (A.sk === 1 ? B.n : A.n) + ' does not');
        if (A.o !== B.o) diff.push((A.o === 1 ? A.n : B.n) + ' brings its own colours; ' + (A.o === 1 ? B.n : A.n) + ' takes whatever colour you give it');
        if (A.fb !== B.fb && A.fb && B.fb) diff.push('texture: ' + A.n + ' is ' + A.fb + ', ' + B.n + ' is ' + B.fb);
        var tip = '';
        var onTrack = /\b(?:track|sim|iracing|race|racing|game)\b/.test(it0.text || '');
        if (onTrack) tip = '\nOn track: finish only changes how the paint looks, never how the car drives. Flat finishes cut glare so numbers and sponsor text stay readable at distance; shinier ones show more colour depth up close. Many racers go satin or gloss on the body and keep numbers plain.';
        var text = (same.length ? '(“' + same.join('”, “') + '” is the same finish as one of the others.) ' : '') + 'Here is how ' + its.map(function (x) { return x.n; }).join(' vs ') + ' compare:\n' + lines.join('\n') + (diff.length ? '\n\nThe difference: ' + diff.join('; ') + '.' : '\n\nThey are very close in the measurements; the difference is mostly in how they look under light.') + tip;
        return { text: text, cards: cards.filter(Boolean), target: it0.target ? { id: it0.target.id, label: it0.target.label } : { id: 'body', label: 'the body' }, useLabel: it0.target ? it0.target.label : 'the body', colour: colour, shown: keys, kind: 'compare', next: ['Show me more finishes like these', 'What finish should I put on the stripes'] };
    }

    // ------------------------------------------------------------------ about one finish
    function about(it0, env) {
        var a = AT(), det = a.details(it0.key); if (!det || det.error) return null;
        var cx = ctxOf(it0.target, env), colour = swatchHex(null, cx, it0.colour), it = a.lookup(it0.key);
        var bits = [];
        bits.push('**' + det.name + '** (' + det.kind + ')' + (det.shelves && det.shelves.length ? ' on the ' + det.shelves[0] + ' shelf' : '') + '.');
        var nt = noteOfKey(it0.key); if (nt) bits.push(nt); if (det.about) bits.push(String(det.about));
        var cdk = W.SpbAICards && W.SpbAICards.ready() ? W.SpbAICards.card(it0.key) : null;
        if (cdk) { bits.push('On a car: ' + cdk.look + (cdk.look && !/[.!?]$/.test(cdk.look) ? '.' : '')); if (cdk.analog.length) bits.push('Resembles: ' + cdk.analog.join(', ') + '.'); if (cdk.pair.length) bits.push('Pairs well with: ' + cdk.pair.join(', ') + '.'); if (cdk.avoid.length) bits.push('Watch out: ' + cdk.avoid.join('; ') + '.'); bits.push('Loudness ' + cdk.loud + '/5, busyness ' + cdk.busy + '/5' + (cdk.use.length ? '; works best on: ' + cdk.use.join(', ') : '') + '.'); }
        var look = [];
        if (it && it.shine) look.push('shine: ' + it.shine); if (it && it.metal && it.metal !== 'none') look.push('metal: ' + it.metal); if (det.sparkle) look.push('sparkle: ' + det.sparkle); if (det.colour_spread) look.push(det.colour_spread); if (det.texture && det.texture !== 'unknown') look.push('texture: ' + det.texture);
        if (look.length) bits.push('Looks like: ' + look.join('; ') + '.');
        bits.push(det.colour_behaviour ? det.colour_behaviour.replace(/color '/g, "colour '").replace(/#rrggbb/g, 'a hex colour') : '');
        if (det.best_for) bits.push('Best for: ' + det.best_for.join('; ') + '.');
        if (det.quality) bits.push('Quality score: ' + det.quality + '.');
        var c = card(it0.key, '', colour); if (c) c.why = (it0.name ? '' : '');
        var atg = it0.target ? { id: it0.target.id, label: it0.target.label } : { id: 'body', label: 'the body' };
        return { text: bits.filter(Boolean).join(' '), cards: c ? [c] : [], target: atg, useLabel: atg.label, colour: colour, shown: [it0.key], kind: 'about', next: ['Show me finishes like this', 'Compare it with Gloss'] };
    }

    // ------------------------------------------------------------------ what is on my car now
    function inspect(it0, env) {
        var a = AT(), tg = it0.target, zs = env.zones || [];
        if (it0.zoneIdx != null) { var zi = it0.zoneIdx === 'selected' ? (env.selected != null ? env.selected : -1) : it0.zoneIdx; var zz = zs[zi]; if (!zz) return { text: it0.zoneIdx === 'selected' ? 'No zone is selected right now. Click a zone in the zone list, then ask again.' : 'There is no zone ' + (zi + 1) + ' (you have ' + zs.length + ').', cards: [], target: null, shown: [], kind: 'inspect', next: ['What finishes am I using'] }; zs = [zz]; tg = null; }
        if (!zs.length) return { text: 'There are no zones on the car yet, so nothing is painted with a finish. Ask me for a design, or tell me what finish you want and where.', cards: [], target: null, shown: [], kind: 'inspect', next: ['Surprise me', 'Make the body gloss red'] };
        var all = tg ? coversFor(tg, zs) : zs.filter(function (z) { return !z.muted; }), list = all.slice(0, 6), extra = all.length - list.length;
        var bits = [], cards = [], seen = {};
        list.forEach(function (z) {
            var it = z.finishKey ? a.lookup(z.finishKey) : null;
            bits.push('- **' + z.name + '** (zone ' + (z.i + 1) + '): ' + (it ? it.n + (it.shine ? ', ' + it.shine : '') + (it.metal && it.metal !== 'none' ? ', ' + it.metal + ' metal' : '') : 'no catalogue finish') + (z.colour ? ', colour ' + z.colour : '') + (whereText(z) ? '; ' + whereText(z) : ''));
            if (it && !seen[it.k] && cards.length < 4) { seen[it.k] = 1; var c = card(it.k, 'Used on ' + z.name, z.colour || (env.paint && env.paint[0])); if (c) { c.noUse = true; cards.push(c); } }
        });
        var head = it0.zoneIdx != null ? 'Zone ' + (list[0] ? list[0].i + 1 : '') + ' uses:' : tg ? (list.length ? tg.label.replace(/^the /, 'The ') + ' ' + (/s$/.test(tg.label) ? 'are' : 'is') + ' shown by:' : 'No zone is aimed at ' + tg.label + ' yet. Whatever sits under it (usually the body) shows there.') : 'Here is every finish on your car right now (top of the list wins where zones overlap):';
        return { text: head + '\n' + bits.join('\n') + (extra > 0 ? '\n…and ' + extra + ' more zone' + (extra > 1 ? 's' : '') + ' lower down.' : '') + '\nZones higher in the list win where they overlap.', cards: cards, target: tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : null, useLabel: tg ? tg.label : 'the body', shown: cards.map(function (c) { return c.key; }), kind: 'inspect', next: tg ? ['What finish would look good on ' + tg.label.replace(/^the /, 'the '), 'Show me more options'] : ['What would make this scheme look more premium', 'Which finish should I put on the stripes'] };
    }

    // ------------------------------------------------------------------ review: "review my finishes" -> specific, one-click fixes for THIS scheme (each card carries its own target)
    // ------------------------------------------------------------------ "my chrome looks grey in the sim", "why is my hood so shiny": finish-specific causes (verified facts only) + finishes that fix it
    function simlook(it0, env) {
        var a = AT(), t = String(it0.text || '').toLowerCase(), tg = it0.target, cx = ctxOf(tg, env), colour = swatchHex(null, cx, it0.colour);
        var metal = /\b(?:chrome|metal|metallic|steel|aluminum|aluminium|silver|mirror)\b/.test(t), tooShiny = /\b(?:too|so|very|really) (?:shiny|glossy|reflective|bright)\b|\btoo much (?:shine|gloss)\b|\bwhy\b.{0,16}\b(?:shiny|glossy)\b/.test(t) || (/\bmatte|flat\b/.test(t) && /\b(?:shiny|glossy|gloss|reflect\w*)\b/.test(t)), shimmer = /\b(?:pearl|candy|shimmer\w*|sparkl\w*|flake|holographic|glitter\w*)\b/.test(t);
        var text, keys = [], why = [];
        if (metal && !tooShiny) {
            text = 'In the sim a metal finish takes its brightness from the paint colour underneath: iRacing multiplies the paint colour by the metal level in the spec, so a chrome part has to be painted white or nearly white; any normal colour turned metallic goes dark. Also check that the spec says metal about 255 with roughness near 0 (a clearcoat value of 255 makes it dull), that the render is newer than your last change (Ctrl+R in iRacing), and remember that overcast or dark tracks give metal little to reflect. Finishes that keep their colour better than full chrome:';
            keys = [['base::f_metallic', 'base::metallic'], ['base::f_pearl', 'base::pearl'], ['base::f_satin_chrome', 'base::satin_chrome'], ['base::f_brushed', 'base::f_anodized']];
            why = ['Partial metal: keeps its colour in the sim because it is not a pure mirror.', 'Pearl looks metallic at an angle but stays bright.', 'Satin chrome reflects less, so it does not turn black.', 'Brushed or anodized metal keeps a visible colour and grain.'];
        } else if (tooShiny) {
            text = (nowText(tg, cx) ? nowText(tg, cx) + ' ' : '') + 'A surface only looks flat when the spec has high roughness (green near 255) and no clearcoat (blue 255). A zone ABOVE it with a gloss, candy or chrome finish, or a spec pattern that adds shine, wins where they overlap, and low sun puts a sheen on any surface. Ask me “what finish is on my ' + (tg ? tg.label.replace(/^the /, '') : 'hood') + '” to see every zone that shows there. To tone it down, use a Foundation flat finish: it sets the right values and keeps your paint colours.';
            keys = [['base::matte'], ['base::satin'], ['base::f_matte_metallic', 'base::cerakote']];
            why = ['Flat: no clear-coat shine at all.', 'A soft sheen, much calmer than gloss.', 'Flat with a hint of metal.'];
        } else if (shimmer) {
            text = 'Pearl, candy and flake are spec effects: they come from the metal and roughness values, so flat light, a dark track or a low-contrast paint colour hides them. Open the Shine (spec) tab: if it is one flat grey, nothing is being sent; if it varies, the effect is there and needs light to show. These finishes show more at a distance:';
            keys = [['base::f_candy', 'base::candy'], ['base::f_pearl', 'base::pearl'], null];
            why = ['Candy: a deep tinted coat; the colour itself does the work.', 'Pearl in your own colour.', 'Real sparkle.'];
        } else {
            text = 'Open the Shine (spec) tab to see what the finish really sends to the sim, check that no zone above it covers the same area with a different finish (say “what finish is on my hood” to list them), then render and press Ctrl+R in iRacing. If it still looks wrong, say “it looks different in iRacing” and I will check your folder.';
        }
        var cards = [], used = [];
        keys.forEach(function (k, i) { var key = k ? pick(k, used) : findPick({ sparkle: true, own: 'takes', min_quality: 80 }, used); if (!key) return; used.push(key); var c = card(key, why[i] || '', colour); if (c) cards.push(c); });
        var tgt = tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : { id: 'body', label: 'the body' };
        return { text: text, cards: cards, target: tgt, useLabel: tgt.label, colour: colour, shown: used, kind: 'simlook', next: ['It looks different in iRacing', 'Check my setup'] };
    }

    function review(it0, env) {
        var a = AT(), zs = (env.zones || []).filter(function (z) { return !z.muted; });
        if (!zs.length) return { text: 'There is nothing on the car yet to review. Ask me for a design first (or press Surprise me), then ask again.', cards: [], target: null, shown: [], kind: 'review', next: ['Surprise me'] };
        var cx = ctxOf(BODY, env), colour = swatchHex(null, cx, null), STRIPES = TARGETS[2], NUMS = TARGETS[0];
        function its(list) { return list.map(function (z) { return z.finishKey && a.lookup(z.finishKey); }).filter(Boolean); }
        var bIt = its(zonesFor(BODY, zs))[0] || null, aIts = its(zonesFor(STRIPES, zs)), nIts = its(zonesFor(NUMS, zs));
        var finds = [], cards = [], used = [];
        function add(text, keys, why, tgt) { var k = pick(keys, used); if (!k) return; used.push(k); finds.push(text); var c = card(k, why, colour); if (c) { c.target = { id: tgt.id, label: tgt.label }; cards.push(c); } }
        if (bIt && aIts.length) {
            var bc = shineClass(bIt), same = aIts.every(function (x) { return shineClass(x) === bc; });
            if (same) add('Your body (' + bIt.n + ') and your stripes (' + aIts[0].n + ') have the same shine, so they differ only in colour.',
                bc === 'flat' ? ['base::gloss', 'base::wet_look'] : ['base::matte', 'base::satin'],
                bc === 'flat' ? 'Gloss stripes on a flat body: the shine difference makes them read.' : 'Flat stripes on a glossy body: same colour, different shine, and the stripe stands apart.', STRIPES);
        }
        var anyMetal = zs.some(function (z) { var it = z.finishKey && a.lookup(z.finishKey); return it && (it.metal === 'full' || it.metal === 'high'); });
        if (!anyMetal && aIts.length) { var lightStripes = zonesFor(STRIPES, zs).every(function (z) { return !z.colour || lightNeutral(z.colour); }); add('Nothing on the car has a bright metal accent.', lightStripes ? ['base::f_satin_chrome', 'base::satin_chrome', 'base::f_chrome'] : ['base::f_metallic', 'base::f_pearl', 'base::metallic'], lightStripes ? 'A thin satin-chrome line catches the light and makes the scheme look built, not just painted.' : 'A metallic glint on the stripes keeps their colour; full chrome on a coloured stripe can look dark in the sim.', STRIPES); }
        if (bIt && (bIt.metal === 'full' || bIt.shine === 'mirror') && bIt.o === 0) add('The whole body is ' + bIt.n + ': ' + (bIt.shine || 'very shiny') + ' metal across a large area is loud and shows every flaw.', ['base::f_pearl', 'base::f_metallic', 'base::pearl'], 'Pearl or fine metallic keeps the richness on a big area; keep chrome for accents.', BODY);
        if (nIts.some(function (x) { return x.sk === 1 || x.o === 1 || x.shine === 'mirror' || x.metal === 'full'; })) add('The numbers are ' + nIts[0].n + ', which breaks up the digit edges at speed.', ['base::gloss', 'base::matte'], 'Plain finishes keep the digits crisp. Colour contrast matters more than the finish.', NUMS);
        // ---- checks from the finish CARDS (loudness / busyness): competing loud finishes, a busy thin accent, too many different finishes
        try {
            var C = W.SpbAICards, R = W.SpbProRank;
            if (C && C.ready() && R && R.like) {
                var seenKeys = {}, rowsZ = [];
                zs.forEach(function (z) { var cd = z.finishKey && C.card(z.finishKey), tgz = targetOf(String(z.name || '')) || (isWhole(z) ? BODY : null); if (cd && !seenKeys[z.finishKey + '|' + (tgz ? tgz.id : '')]) { seenKeys[z.finishKey + '|' + (tgz ? tgz.id : '')] = 1; rowsZ.push({ z: z, key: z.finishKey, cd: cd, it: a.lookup(z.finishKey), tg: tgz }); } });
                function calmer(r, tgt, text, why) { var rr = R.like([r.key], { mods: ['calm'], limit: 1, exclude: used }); if (!rr.length) { finds.push(text); return; } finds.push(text); used.push(rr[0].key); var c = card(rr[0].key, why + ' (' + firstSentence(rr[0].look, 80).replace(/[.…]+$/, '') + ')', colour); if (c) { c.target = { id: tgt.id, label: tgt.label }; c.lane = rr[0].lane; cards.push(c); } }
                var loud = rowsZ.filter(function (r) { return r.cd.loud >= 4 && !(r.tg && r.tg.readable); });
                var distinctLoud = {}; loud.forEach(function (r) { distinctLoud[r.key] = r; });
                var loudKeys = Object.keys(distinctLoud);
                if (loudKeys.length >= 2) { var lead = distinctLoud[loudKeys[0]], other = distinctLoud[loudKeys[loudKeys.length - 1]]; calmer(other, other.tg || BODY, loudKeys.map(function (k) { return distinctLoud[k].it.n; }).join(' and ') + ' are all loud (4+/5): they compete for attention, so let one lead and calm the others.', 'A calmer look in the same family, so ' + lead.it.n + ' can lead'); }
                var thinBusy = rowsZ.filter(function (r) { return r.tg && r.tg.thin && r.cd.busy >= 4; })[0];
                if (thinBusy) calmer(thinBusy, thinBusy.tg, thinBusy.it.n + ' is very busy (' + thinBusy.cd.busy + '/5) for a thin accent: the detail gets lost on a narrow line.', 'A simpler finish that still reads on a thin line');
                var fam = {}; rowsZ.forEach(function (r) { fam[String(r.it.n).toLowerCase().split(/[ :\-—\/(]/)[0]] = 1; });
                if (Object.keys(fam).length >= 4) finds.push('You use ' + Object.keys(fam).length + ' different finish families (' + rowsZ.map(function (r) { return r.it.n; }).slice(0, 5).join(', ') + '): the scheme reads busier than it is. Two or three finishes, repeated, look more designed.');
                var busyBody = rowsZ.filter(function (r) { return r.tg === BODY && r.cd.busy >= 4; })[0];
                if (busyBody && rowsZ.some(function (r) { return r.tg && r.tg.readable; })) finds.push('The body (' + busyBody.it.n + ') is very busy (' + busyBody.cd.busy + '/5): numbers and sponsor logos on top of it lose contrast.');
            }
        } catch (ecr) {}
        var specials = zs.filter(function (z) { return z.finishKey && /^monolithic::/.test(z.finishKey); }).length;
        var extra = specials > 3 ? ' You use ' + specials + ' complete special looks; the scheme reads best with one hero special and calm finishes around it.' : '';
        var now = []; if (bIt) now.push('body ' + bIt.n); if (aIts.length) now.push('stripes ' + aIts[0].n); if (nIts.length) now.push('numbers ' + nIts[0].n);
        var text = (finds.length ? 'Here is what I would change about the finishes on this scheme' + (now.length ? ' (right now: ' + now.join(', ') + ')' : '') + ':\n' + finds.map(function (f, i) { return (i + 1) + '. ' + f; }).join('\n') + (cards.length ? '\nEach card below makes one of those changes; skip any you do not like.' : '') : 'I looked at every zone' + (now.length ? ' (' + now.join(', ') + ')' : '') + ' and the finishes already work together: there is a shine difference between the parts, nothing is overly loud and the numbers are plain.') + extra;
        return { text: text, cards: cards, target: { id: 'body', label: 'the body' }, useLabel: 'the body', colour: colour, shown: cards.map(function (c) { return c.key; }), kind: 'review', next: ['What finish should I put on the stripes to make them pop', 'Show me chrome finishes'] };
    }

    // ------------------------------------------------------------------ finish names inside a sentence ("how would pearl look on the hood", "can I have a matte hood with a glossy body")
    function findFinishesIn(t, max) {
        var w = norm(t).split(' ').filter(Boolean).slice(0, 30), out = [], used = {}, n, i, k, g;
        for (n = 3; n >= 1; n--) {
            for (i = 0; i + n <= w.length; i++) {
                var clash = false; for (k = i; k < i + n; k++) { if (used[k]) clash = true; } if (clash) continue;
                g = w.slice(i, i + n).join(' '); if (n > 1 && targetOf(g)) continue; var key = resolveName(g);
                if (key && !out.some(function (x) { return x.key === key; })) { out.push({ key: key, q: g, at: i }); for (k = i; k < i + n; k++) used[k] = 1; }
            }
        }
        out.sort(function (a, b) { return a.at - b.at; });
        return out.slice(0, max || 2);
    }

    // ------------------------------------------------------------------ yes / no: a verdict from the measured finish + the design-sense rules, then the finish itself
    function judge(it0, env) {
        var a = AT(), items = (it0.keys || []).map(function (k) { return a.lookup(k); }).filter(Boolean); if (!items.length) return null;
        var tg = it0.target, cx = ctxOf(tg, env), colour = swatchHex(null, cx, it0.colour), t = String(it0.text || '').toLowerCase(), A = items[0], label = tg ? tg.label : 'the car', verdict;
        var loud = A.shine === 'mirror' || A.metal === 'full' || A.sk === 1 || A.o === 1;
        if (items.length >= 2 && /\b(?:can i have|can the|can you have|mix|with)\b/.test(t)) verdict = 'Yes. Every part of the car can have its own finish: each zone is independent, so ' + A.n + (tg ? ' on ' + label : '') + ' next to ' + items[1].n + ' is just two zones. (Adjacent parts read best when they differ in colour or in shine.)';
        else if (tg && tg.readable) verdict = loud ? 'Probably not: ' + A.n + ' (' + shineWord(A) + (A.sk === 1 ? ', sparkles' : '') + ') breaks up the digit edges at speed. Plain gloss, satin or matte keep numbers crisp, and the colour contrast behind them matters most.' : 'Yes: ' + A.n + ' is a safe finish for numbers. What matters more is the colour contrast behind the digits.';
        else if (/\btoo (?:subtle|dull|flat)\b/.test(t)) verdict = (A.sk === 1 || A.metal === 'full' || A.shine === 'mirror') ? A.n + ' is not subtle: it is one of the louder finishes.' : A.n + ' is subtle by design: it shows in sunlight and at an angle and looks plain in flat light. For a stronger effect try Candy, Metallic or a real sparkle finish.';
        else if (/\btoo (?:loud|shiny|much|bright)\b/.test(t)) verdict = loud ? 'It can be: ' + A.n + ' is ' + shineWord(A) + (A.sk === 1 ? ', sparkly' : '') + '. Use it on one panel or an accent and keep the rest calm.' : 'Not really: ' + A.n + ' is a calm finish (' + shineWord(A) + ').';
        else if ((!tg || tg.all || !tg.thin) && (A.shine === 'mirror' || A.metal === 'full')) verdict = 'It works, but ' + shineWord(A) + ' across a large area is loud and shows every flaw. It shines on accents, trim and numbers; for a big area pearl, metallic or satin usually looks more expensive.';
        else verdict = 'Yes, ' + A.n + ' is a solid choice' + (tg ? ' for ' + label : '') + '.';
        var det = a.details(A.k) || {}, nt = noteOfKey(A.k), bf = (det.best_for || []).slice(0, 2).join('; ');
        var text = verdict + ' ' + (nt || '') + (bf ? ' Best for: ' + bf + '.' : '');
        var cards = items.map(function (it) { return card(it.k, firstSentence(it.d || '', 118), colour); }).filter(Boolean);
        var tgt = tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : { id: 'body', label: 'the body' };
        return { text: text, cards: cards, target: tgt, useLabel: tgt.label, colour: colour, shown: items.map(function (x) { return x.k; }), kind: 'judge', next: ['Show me more finishes like this', 'Review my finishes'] };
    }

    // ------------------------------------------------------------------ "your favourite finish", "what do other people use": honest, then the gold standards / the common choices
    function goldCards(n, colour, excl) {
        var d = AT()._data(), out = [];
        d.items.forEach(function (it) { if (out.length >= n || !(it._type === 'base' || it._type === 'monolithic') || !it.gold || has(excl || [], it.k)) return; var c = card(it.k, firstSentence(it.d || '', 118), colour); if (c) out.push(c); });
        return out;
    }
    function taste(it0, env) {
        var a = AT(), cx = ctxOf(it0.target, env), colour = swatchHex(null, cx, it0.colour);
        if (it0.sub === 'popular') {
            var tg = it0.target, base = recommend({ kind: 'recommend', target: tg, colour: it0.colour, goal: null, text: it0.text }, env);
            if (!base) return null;
            base.text = 'I do not have usage statistics for other drivers. What most race cars run is a gloss or satin body in the livery colour, flat or gloss accents and chrome or satin chrome trim. ' + base.text;
            return base;
        }
        var cards = goldCards(5, colour, []); if (!cards.length) return null;
        return { text: 'I do not have favourites, but the Shokker team marks a few finishes as GOLD STANDARDS: they set the bar for the catalogue and are never changed. If you want a wow finish, start with these (swatches on ' + (it0.colour ? it0.colour.name : 'your car\'s colour') + '):', cards: cards, target: { id: 'body', label: 'the body' }, useLabel: 'the body', colour: colour, shown: cards.map(function (c) { return c.key; }), kind: 'taste', next: ['Show me chrome finishes', 'What finish should I put on the stripes to make them pop', 'Which finishes have the most sparkle'] };
    }

    // ------------------------------------------------------------------ "how many finishes are there", "what finishes do you have"
    function catalogue(it0, env) {
        var a = AT(), d = a._data(), n = { base: 0, monolithic: 0, pattern: 0, spec: 0 }, cx = ctxOf(null, env), colour = swatchHex(null, cx, it0.colour);
        d.items.forEach(function (it) { if (n[it._type] != null) n[it._type]++; });
        var shelves = d.sections.map(function (s, i) { return { s: s, n: d.sectionSize[i] }; }).sort(function (x, y) { return y.n - x.n; }).slice(0, 7).map(function (x) { return x.s + ' (' + x.n + ')'; });
        var cards = goldCards(4, colour, []);
        var text = 'The catalogue has ' + (n.base + n.monolithic) + ' finishes: ' + n.base + ' base materials (gloss, matte, satin, pearl, candy, chrome, metallic ...) and ' + n.monolithic + ' complete special looks that bring their own colours, plus ' + n.pattern + ' paint patterns and ' + n.spec + ' spec patterns (textures that change only the shine), on ' + d.sections.length + ' shelves. Biggest shelves: ' + shelves.join(', ') + '. Ask by look ("show me chrome finishes", "something like brushed aluminum") or by place ("what finish for the stripes"). The gold standards are a good place to start:';
        return { text: text, cards: cards, target: { id: 'body', label: 'the body' }, useLabel: 'the body', colour: colour, shown: cards.map(function (c) { return c.key; }), kind: 'catalogue', next: ['Show me chrome finishes', 'Show me candy finishes', 'Review my finishes'] };
    }

    // ------------------------------------------------------------------ answers for the conversation intents
    function kindOfCtx(it0, tg) { return it0.goal || (tg && tg.readable ? 'readable' : (!tg || tg.all || !tg.thin ? 'general' : 'thin')); }
    function nameOf(k) { var it = AT().lookup(k); return it ? it.n : k; }
    function likeAnswer(it0, env) {
        var R = W.SpbProRank; if (!rankReady() || !R.like) return null;
        var a = AT(), tg = it0.target, cx = ctxOf(tg, env), colour = swatchHex(null, cx, it0.colour && it0.colour.hex ? it0.colour : null), maxc = it0.count ? Math.max(1, Math.min(6, it0.count)) : 5;
        var p = it0.prev || {}, same = p.kind === 'like' && p.likeKeys && p.likeKeys.join('|') === it0.keys.join('|') && !it0.refine, excl = same ? (p.shown || []).slice() : [];
        (zonesFor(tg || BODY, env.zones || []) || []).forEach(function (z) { if (z.finishKey && excl.indexOf(z.finishKey) === -1) excl.push(z.finishKey); });
        var rows = R.like(it0.keys, { mods: it0.mods, colour: it0.colour && it0.colour.hex, limit: maxc, exclude: excl, avoid: it0.dislikes });
        var names = it0.keys.map(nameOf), modNames = (it0.mods || []).map(function (m) { return ({ calm: 'calmer', bold: 'bolder', darker: 'darker', lighter: 'lighter', glossier: 'glossier', flatter: 'flatter', sparklier: 'with more sparkle', smoother: 'with less sparkle', metalmore: 'more metallic', metalless: 'less metallic', warmer: 'warmer', cooler: 'cooler', vivid: 'more vivid', muted: 'more muted', simpler: 'simpler', busier: 'with more detail', finer: 'finer', coarser: 'coarser' })[m] || m; });
        if (it0.colour && it0.colour.name) modNames.push('in ' + it0.colour.name);
        var head = it0.refine ? 'Same idea as ' + (names.length > 1 ? 'those' : '**' + names[0] + '**') + ', ' + modNames.join(' and ') : 'Finishes like ' + names.map(function (n) { return '**' + n + '**'; }).join(' and ') + (modNames.length ? ', but ' + modNames.join(' and ') : '');
        if (!rows.length) return { text: 'I could not find anything close to ' + names.join(' and ') + (modNames.length ? ' that is also ' + modNames.join(' and ') : '') + ' that I have not already shown. Try a different change (calmer, bolder, darker, glossier, more sparkle).', cards: [], target: tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : { id: 'body', label: 'the body' }, useLabel: tg ? tg.label : 'the body', colour: colour, shown: p.shown || [], kind: 'like', likeKeys: it0.keys, next: ['Something calmer', 'Something bolder', 'What finish should I put on the stripes'] };
        var cards = []; rows.forEach(function (r) { var c = rankedCard(r, r.lane, colour); if (c) cards.push(c); });
        var refIt = a.lookup(it0.keys[0]), note = (refIt && refIt.o === 0 && cards.some(function (c) { return c.own; })) ? ' Some of these bring their own colours (they replace the part\'s colour).' : '';
        return { text: head + ':' + note + ' Swatches are shown on ' + (it0.colour ? it0.colour.name : 'your car\'s colour') + '.', cards: cards, target: tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : { id: 'body', label: 'the body' }, useLabel: tg ? tg.label : 'the body', colour: colour,
            shown: excl.concat(cards.map(function (c) { return c.key; })).filter(function (k, i, arr) { return arr.indexOf(k) === i; }), kind: 'like', likeKeys: it0.keys, likeMods: it0.mods || [], likeColour: it0.colour || null, goal: it0.goal || p.goal,
            next: ['More like this', 'Something calmer', 'Something bolder', 'Why these?'] };
    }
    function whyAnswer(it0, env) {
        var R = W.SpbProRank, C = W.SpbAICards; if (!rankReady() || !C) return null;
        var a = AT(), tg = it0.target, cx = ctxOf(tg, env), colour = swatchHex(null, cx, it0.colour), keys = it0.keys, bits = [], cards = [];
        var ctx = rankCtx({ kind: 'recommend', target: tg, colour: it0.colour, goal: it0.goal, text: it0.text, mod: null }, cx, kindOfCtx(it0, tg)); ctx.only = keys; ctx.limit = keys.length; ctx.lane = 'any';
        var rows = {}; try { R.suggest(ctx).rows.forEach(function (r) { rows[r.key] = r; }); } catch (e) {}
        var label = tg ? tg.label : 'the car', thin = tg && tg.thin, readable = tg && tg.readable;
        keys.forEach(function (k) {
            var it = a.lookup(k), cd = C.card(k); if (!it || !cd) return;
            var why = (rows[k] && rows[k].why) || [], parts = [];
            if (it0.not) {
                if (cd.risk >= 4) parts.push('it is rated high-risk (' + cd.risk + '/5)');
                if (cd.avoid && cd.avoid.length) parts.push('watch out: ' + cd.avoid.join('; '));
                if (readable && (cd.busy > 2 || it.metal === 'full' || it.shine === 'mirror')) parts.push('numbers and names need plain, low-glare finishes');
                if (thin && cd.busy >= 4) parts.push('it is busy for a thin accent');
                if (it.o === 1) parts.push('it brings its own colours, so it replaces the part\'s colour');
                if (it.o === 0 && it.metal === 'full' && cx.hexZone && !lightNeutral(cx.hexZone) && lum(cx.hexZone) >= 0.25) parts.push('full metal on a coloured part can look darker in the sim');
                bits.push('**' + it.n + '**: ' + (parts.length ? 'I held it back because ' + parts.join(', and ') + '.' : 'there is no strong reason against it: it is a good option for ' + label + ' too, so here it is.') + ' Loudness ' + cd.loud + '/5, busyness ' + cd.busy + '/5.');
            } else {
                if (why.length) parts.push(why.join('; '));
                parts.push('it looks like this: ' + firstSentence(cd.look, 110).replace(/[.…]+$/, ''));
                var role = readable ? ['accent', 'a plain finish for numbers'] : (thin ? ['accent', 'an accent'] : (tg && !tg.all && tg.id !== 'body' ? ['hero', 'a panel'] : ['body', 'the whole car']));
                parts.push('rated ' + cd[role[0]] + '/5 for ' + role[1] + ' and ' + cd.appeal + '/5 overall');
                if (it0.goal && R.GOALS && R.GOALS[it0.goal]) parts.push('loudness ' + cd.loud + '/5 and busyness ' + cd.busy + '/5 against a target of ' + R.GOALS[it0.goal].loud + ' and ' + R.GOALS[it0.goal].busy + ' for that goal'); else parts.push('loudness ' + cd.loud + '/5, busyness ' + cd.busy + '/5');
                if (cd.avoid && cd.avoid.length) parts.push('watch out: ' + cd.avoid.join('; '));
                bits.push('**' + it.n + '** for ' + label + ': ' + parts.join('; ') + '.');
            }
            var c = card(k, '', colour); if (c) { c.why = firstSentence(cd.look, 104); c.lane = it.o === 1 ? 'complete' : 'keep'; c.loud = cd.loud; c.busy = cd.busy; cards.push(c); }
        });
        if (!bits.length) return null;
        return { text: (it0.not ? 'Fair question. ' : 'Here is my thinking. ') + bits.join('\n'), cards: cards, target: tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : { id: 'body', label: 'the body' }, useLabel: label, colour: colour, shown: (it0.prev && it0.prev.shown) || keys, kind: 'why', goal: it0.goal,
            next: ['Show me more', 'Something calmer', 'Something bolder'] };
    }
    function pairsAnswer(it0, env) {
        var R = W.SpbProRank, C = W.SpbAICards; if (!rankReady() || !C) return null;
        var a = AT(), it = a.lookup(it0.key), cd = C.card(it0.key); if (!it || !cd) return null;
        var cx = ctxOf(null, env), colour = swatchHex(null, cx, null), body = it.o === 1 && it.c && it.c[0] ? it.c[0] : null, stripes = null, i;
        for (i = 0; i < TARGETS.length; i++) { if (TARGETS[i].id === 'stripes') stripes = TARGETS[i]; }
        var ctx = { target: stripes, goal: null, colours: { target: null, body: body, scheme: body ? [body] : [] }, bodyClass: shineClass(it), novelty: 1, exclude: [it0.key], limit: 4, lane: 'keep', classic: true, seed: 3 };
        var rows = R.suggest(ctx).rows, cards = [];
        rows.forEach(function (r) { var c = rankedCard(r, 'keep', colour); if (c) cards.push(c); });
        var txt = '**' + it.n + '**' + (cd.pair && cd.pair.length ? ' pairs well with ' + cd.pair.join(', ') + '.' : ' has no special partners on its card.') + ' ' + (cards.length ? 'As stripes or trim next to it on the body, these read well because their shine differs from ' + it.n + ' (swatches on ' + (body ? 'its own palette colour' : 'your car\'s colour') + '):' : '');
        if (cd.avoid && cd.avoid.length) txt += ' Watch out: ' + cd.avoid.join('; ') + '.';
        return { text: txt, cards: cards, target: { id: 'stripes', label: 'the stripes' }, useLabel: 'the stripes', colour: colour, shown: [it0.key].concat(cards.map(function (c) { return c.key; })), kind: 'pairs', next: ['Tell me about ' + it.n, 'Show me more', 'Something bolder'] };
    }
    function bestofAnswer(it0, env) {
        var R = W.SpbProRank, C = W.SpbAICards, p = it0.prev || {}; if (!rankReady() || !C) return null;
        var a = AT(), tg = it0.target, cx = ctxOf(tg, env), colour = swatchHex(null, cx, it0.colour), keys = (p.last || []).slice(0, 8);
        if (keys.length < 2) return null;
        var ctx = rankCtx({ kind: 'recommend', target: tg, colour: it0.colour, goal: it0.goal, text: it0.text + ' ' + (it0.rest || ''), mod: null }, cx, kindOfCtx(it0, tg)); ctx.only = keys; ctx.limit = keys.length; ctx.lane = 'any';
        var rows = R.suggest(ctx).rows, cards = [];
        rows.forEach(function (r) { var ri = a.lookup(r.key), c = rankedCard(r, ri && (ri._type === 'spec' || ri._type === 'pattern') ? 'texture' : (ri && ri.o === 1 ? 'complete' : 'keep'), colour); if (c) cards.push(c); });
        if (!cards.length) return null;
        var best = rows[0], bc = C.card(best.key), forWhat = (it0.rest || '').replace(/^\s*(?:is|are|would be|will be)\s+(?:the\s+)?(?:best|better|safest|easiest|nicest)?\s*/, '').replace(/^\s*(?:for|on|in|at)\s+/, '').replace(/\?$/, '').trim();
        var txt = 'Ranked' + (forWhat ? ' for ' + forWhat : (tg ? ' for ' + tg.label : '')) + ': my pick is **' + best.name + '**' + (best.why && best.why.length ? ' (' + best.why.slice(0, 2).join('; ') + ')' : '') + (bc ? ' - ' + firstSentence(bc.look, 100).replace(/[.…]+$/, '') : '') + '. The rest follow in order.';
        return { text: txt, cards: cards, target: tg ? { id: tg.id, label: tg.label, region: tg.region, element: tg.element } : (p.target ? { id: p.target.id, label: p.target.label } : { id: 'body', label: 'the body' }), useLabel: tg ? tg.label : (p.target ? p.target.label : 'the body'), colour: colour, shown: p.shown || keys, kind: 'bestof', goal: it0.goal, next: ['Why did you pick that', 'Show me more', 'Something calmer'] };
    }

    // MSR-FIX-A (2026-10-03): two opposite wishes in one breath ("metal but also soft", "bright but dark", "quiet loud", "a snake but not really") -> answer, then ask which way to lean
    var ST_OPP = [[/\b(?:metal\w*|chrome\w*|shiny|shinier|gloss\w*|wet)\b/, /\b(?:soft|matte?|flat|velvet\w*|dull)\b/, 'more metal / shine', 'softer and flatter'], [/\bbright\w*\b/, /\bdark\w*\b/, 'bright', 'dark'],
        [/\bloud\w*\b|\bflashy\b|\bwild\b/, /\bquiet\w*\b|\bcalm\w*\b|\bsubtle\b|\btasteful\b|\bclassy\b/, 'loud', 'quiet']];
    function stAmbig(text) {
        var t = String(text || '').toLowerCase(); if (t.length > 160) return null;
        if (/\bbut not really\b|\bsort of but not\b/.test(t)) return 'Quick question so I get it right: how far should it lean toward that look: just a hint, or clearly there?';
        for (var i = 0; i < ST_OPP.length; i++) { var o = ST_OPP[i], ma = o[0].exec(t), mb = o[1].exec(t); if (!ma || !mb) continue;
            var between = t.slice(Math.min(ma.index, mb.index), Math.max(ma.index, mb.index));
            if (/\b(?:but|also|yet|and|while)\b|^\S+\s+$/.test(between) && !/\b(?:with|base|top|clear|on|over|under|pattern|texture|layer|spec|stripes?|hood|roof|sides?|numbers?)\b/.test(between)) return 'Quick question: which should win where they clash, ' + o[2] + ' or ' + o[3] + '? (The options above split the difference.)'; }
        return null;
    }
    function answer(it0, env) {
        SEL_I = (env && env.selected != null) ? env.selected : null;
        var r = answerCore(it0, env);
        try { afRegThumbs(r); } catch (eaf) {}      // ADVISOR-FIX (3)
        if (r && it0.dislikes) r.dislikes = it0.dislikes;
        if (r && r.text && !/\?/.test(r.text) && (r.kind === 'stack' || it0.kind === 'recommend' || it0.kind === 'find')) { var amb = stAmbig(it0.text || ''); if (amb) r.text += '\n' + amb; }      // MSR-FIX-A: a self-contradicting wish gets ONE question back
        if (r && r.cards) {
            if (r.kind === 'about' || r.kind === 'why' || r.kind === 'pairs' || r.kind === 'inspect' || r.kind === 'judge' || r.kind === 'review' || r.kind === 'taste' || r.kind === 'catalogue') {      // explanations: the list the buyer was looking at stays what "the second one" points at
                r.last = null; r.focus = it0.key || (it0.keys && it0.keys[0]) || null;
                if (it0.prev && it0.prev.shown) { var sh0 = it0.prev.shown.slice(); (r.shown || []).forEach(function (k) { if (sh0.indexOf(k) === -1) sh0.push(k); }); r.shown = sh0; }      // an explanation does not forget what was already shown ("more" never repeats it)
            } else if (!r.last) r.last = r.cards.map(function (c) { return c.key; });      // what the NEXT follow-up ("the second one", "that", "these") points at
        }
        return r;
    }
    function answerCore(it0, env) {
        try {
            var a = AT(); if (!a || !a.ready()) return null; env = env || {};
            if (it0.lane === 'specover' && (it0.kind === 'recommend' || it0.kind === 'find')) return specOverAnswer(it0, env);      // ADVISOR-FIX (1)
            if (it0.kind === 'more' && it0.prev && it0.prev.lane === 'specover' && it0.mod !== 'retarget' && it0.mod !== 'lane') return specOverAnswer({ kind: 'recommend', lane: 'specover', text: it0.prev.text || '', target: it0.prev.target, mod: (it0.mod === 'calm' || it0.mod === 'bold') ? it0.mod : 'more', prev: it0.prev, dislikes: it0.dislikes, not: it0.not }, env);
            if (it0.kind === 'more' && it0.mod === 'wide' && it0.prev && it0.prev.kind === 'stack') { var spw = stackParse(it0.prev.text || ''); if (spw) { var aw = stackAnswer({ stack: spw, target: null, dislikes: it0.dislikes, text: spw.text, wideFrom: it0.prev.target }, env, {}); if (aw) return aw; } }      // ADVISOR-FIX (2): the whole-body version, with its warnings
            if (it0.stack && (it0.kind === 'recommend' || it0.kind === 'find')) afStackTarget(it0, env);      // ADVISOR-FIX (2): a stack lands on the conversation target
            if (it0.stack && (it0.kind === 'recommend' || it0.kind === 'find')) { var sa0 = stackAnswer(it0, env); if (sa0) return sa0; }      // B2 stack planner
            if (it0.kind === 'more' && it0.prev && it0.prev.kind === 'stack' && it0.mod !== 'retarget' && it0.mod !== 'lane') { var sp0 = stackParse(it0.prev.text || ''); if (sp0) { if (it0.mod === 'calm') sp0.calm = true; var sm0 = stackAnswer({ stack: sp0, target: it0.prev.target, dislikes: it0.dislikes, text: sp0.text }, env, { exclude: it0.prev.shown || [] }); if (sm0) return sm0; } }
            if (it0.kind === 'recommend' && it0.multi) { var mr = multiAnswer(it0, env); if (mr) return mr; }
            if (it0.kind === 'like') return likeAnswer(it0, env);
            if (it0.kind === 'why') return whyAnswer(it0, env);
            if (it0.kind === 'pairs') return pairsAnswer(it0, env);
            if (it0.kind === 'bestof') return bestofAnswer(it0, env);
            if (it0.kind === 'review') return review(it0, env);
            if (it0.kind === 'kit') return kits(it0, env);
            if (it0.kind === 'simlook') return simlook(it0, env);
            if (it0.kind === 'judge') return judge(it0, env);
            if (it0.kind === 'taste') return taste(it0, env);
            if (it0.kind === 'catalogue') return catalogue(it0, env);
            if (it0.kind === 'inspect') return inspect(it0, env);
            if (it0.kind === 'compare') return compare(it0, env);
            if (it0.kind === 'about') return about(it0, env);
            if (it0.kind === 'find') return find(it0, env);
            if (it0.kind === 'more' && it0.prev && it0.prev.kind === 'kit') return kits({ kind: 'kit', prev: it0.prev, text: it0.text, mod: (it0.mod === 'bold' || it0.mod === 'calm') ? it0.mod : null }, env);
            if (it0.kind === 'more') { var p = it0.prev || {}; var base = { kind: p.kind === 'find' ? 'find' : 'recommend', lane: it0.lane, target: it0.mod === 'retarget' ? it0.target : p.target, colour: it0.colour, goal: it0.goal || p.goal, mod: it0.mod, prev: p, text: it0.text, query: p.query, dislikes: it0.dislikes, not: it0.not, lanes: p.lanes, keepColours: p.keepColours };
                if (it0.mod === 'retarget' && p.kind === 'find' && p.query) { var rt = find({ query: p.query, target: it0.target, colour: it0.colour }, env); if (rt) { rt.text = 'The same finishes for ' + it0.target.label + ':'; return rt; } }
                if (p.kind === 'find' && p.query && it0.mod === 'more') { var seen = p.shown || [], r = find({ query: p.query, target: p.target, colour: it0.colour, skip: seen }, env); if (r && r.cards.length) { r.shown = seen.concat(r.cards.map(function (c) { return c.key; })); r.text = 'More matches for “' + p.query + '”:'; return r; } }
                return recommend(base, env); }
            return recommend(it0, env);
        } catch (e) { try { console.warn('[ADVISOR]', e); } catch (x) {} return null; }
    }

    // ------------------------------------------------------------------ "Use on the stripes": which zone calls does that need?
    function stL(c, id) { var o = { id: id, opacity: (c && c.layerOpacity) || 70 }; if (c && c.layerScale != null && c.layerScale !== 1) o.scale = c.layerScale; return o; }      // B2: a planned layer keeps its strength + size
    function applyPlan(c, target, env) { var r = applyPlanStack(c, target, env); try { afChanged(r, target, env || {}); } catch (eaf) {} return r; }      // ADVISOR-FIX (2): changed / changedText = what a Use edits (zone names + share)
    function applyPlanStack(c, target, env) {
        if (c && c.stackPart) { var tl = (target && target.label) || 'the body'; return { steps: [], label: tl, texture: true, stackPart: true }; }      // B2: shown in the stack, applied by its base card
        var r = applyPlanCore(c, target, env); if (!c || !c.stackWith || !r || !r.steps) return r;
        var it = AT().lookup(c.key), sw = c.stackWith, ad = sw.adjust || {}, zs = (env && env.zones) || [];
        r.steps.forEach(function (st) {
            var g = st.args || {}, z = null; zs.forEach(function (q) { if ((g.zone_id != null && q.id === g.zone_id) || (g.zone_id == null && g.zone != null && q.i === g.zone)) z = q; });
            if (sw.pattern) g.pattern = merge({}, sw.pattern);
            if (sw.spec && sw.spec.length) { var ids = sw.spec.map(function (x) { return x.id; }), ex = z ? (z.specLayers && z.specLayers.length ? z.specLayers : (z.specStack || []).map(function (x) { return { id: x }; })) : []; g.spec_patterns = ex.filter(function (x) { return ids.indexOf(x.id) === -1; }).slice(-(5 - sw.spec.length)).map(function (x) { return merge({}, x); }).concat(sw.spec.map(function (x) { return merge({}, x); })); }
            if (ad.base_colour && it && it.o !== 1) g.color = ad.base_colour;
            if (ad.hue_shift_deg != null) g.hue = ad.hue_shift_deg; if (ad.saturation != null) g.saturation = ad.saturation; if (ad.brightness != null) g.brightness = ad.brightness;
            if (ad.spec_strength != null) g.spec_strength = ad.spec_strength; if (ad.scale != null && ad.scale !== 1) g.scale = ad.scale;
        });
        if (sw.lparts && r.steps.length) {      // PUSH2: the layer moves to its own zone on the named parts (same base look under it); the whole-car step keeps only the base
            var b0 = r.steps[0].args || {}, lay = {}, ln = (sw.pattern ? (AT().lookup('pattern::' + sw.pattern.id) || {}).n : '') || (sw.spec.length ? (AT().lookup('spec::' + sw.spec[0].id) || {}).n : '') || 'layer';
            ['finish', 'color', 'hue', 'saturation', 'brightness', 'spec_strength', 'scale', 'pattern', 'spec_patterns'].forEach(function (k) { if (b0[k] != null) lay[k] = JSON.parse(JSON.stringify(b0[k])); });
            if (!lay.finish) lay.finish = c.key;
            r.steps.forEach(function (st) { var g = st.args || {}; delete g.pattern; if (st.tool === 'edit_zone' && sw.pattern) g.pattern = { id: 'none' }; if (sw.spec && sw.spec.length) { var ids2 = sw.spec.map(function (x) { return x.id; }); g.spec_patterns = (g.spec_patterns || []).filter(function (x) { return ids2.indexOf(x.id) === -1; }); if (!g.spec_patterns.length) delete g.spec_patterns; } });
            var lp = sw.lparts, cap = function (x) { return x.charAt(0).toUpperCase() + x.slice(1); };
            if (lp.parts.length) { var a1 = merge({ name: cap(lp.ids.filter(function (x) { return x !== 'stripes'; }).join(' + ')) + ' ' + ln, region: { part: lp.parts.length === 1 ? lp.parts[0] : lp.parts.slice() } }, lay); r.steps.push({ tool: 'add_zone', args: a1, zone: a1.name }); }
            if (lp.element) { var a2 = merge({ name: cap(lp.element) + ' ' + ln, region: { element: lp.element } }, lay); r.steps.push({ tool: 'add_zone', args: a2, zone: a2.name }); }
            r.label = 'the body + ' + lp.label;
        }
        r.stack = true; return r;
    }
    function applyPlanCore(c, target, env) {
        var a = AT(), it = a && a.lookup(c.key); if (!it) return { error: 'that finish is not in the catalogue' };
        SEL_I = (env && env.selected != null) ? env.selected : null;
        if (target && target.region) {            // "what would look good on the black?": the finish goes on exactly the pixels of that colour (spec only unless the finish brings its own palette)
            var rn = String(target.label || 'that colour').replace(/^the /, ''), rnm = rn.charAt(0).toUpperCase() + rn.slice(1) + ' ' + it.n, ra = { name: rnm, region: JSON.parse(JSON.stringify(target.region)), finish: c.key, color: it.o === 1 ? 'finish' : 'source' };
            if (it._type === 'spec' || it._type === 'pattern') { var rid = it.k.replace(/^[a-z]+::/, ''); ra.finish = 'base::gloss'; ra.color = 'source'; if (it._type === 'spec') ra.spec_patterns = [stL(c, rid)]; else ra.pattern = stL(c, rid); }
            return { steps: [{ tool: 'add_zone', args: ra, zone: rnm }], label: target.label, texture: it._type === 'spec' || it._type === 'pattern' };
        }
        var tg = target && target.zones && target.zones.length ? target : target && target.id ? (function () { for (var i = 0; i < TARGETS.length; i++) { if (TARGETS[i].id === target.id) return TARGETS[i]; } return BODY; })() : BODY;
        var zs = env.zones || [], hit = afHit(tg, zs, target), steps = [], cx = ctxOf(tg, env), hex = cx.hexZone || (cx.paint && cx.paint[0]) || null;
        if (tg.selected && !hit.length) return { error: 'no zone is selected: click a zone in the zone list first, or name the part (hood, stripes, roof ...)' };
        if (it._type === 'spec' || it._type === 'pattern') {            // a texture layer goes ON the zones that already show that part (never replaces their finish or colour)
            var tid = it.k.replace(/^[a-z]+::/, ''), tz = hit.length ? hit : ((tg.all || tg.id === 'body') ? zonesFor(BODY, zs) : []);
            if (!tz.length && tg.parts && tg.parts.length) {      // no zone on that part yet: a neutral Foundation gloss zone (colours untouched) carries the texture
                var nid = it.k.replace(/^[a-z]+::/, ''), nargs = { name: tg.id.charAt(0).toUpperCase() + tg.id.slice(1) + ' ' + it.n, region: { part: tg.parts.length === 1 ? tg.parts[0] : tg.parts }, finish: 'base::gloss', color: 'source' };
                if (it._type === 'spec') nargs.spec_patterns = [stL(c, nid)]; else nargs.pattern = stL(c, nid);
                return { steps: [{ tool: 'add_zone', args: nargs, zone: nargs.name }], label: tg.label, texture: true };
            }
            if (!tz.length && tg.element && env.elements && env.elements[tg.element] && env.elements[tg.element].found) { var eid = it.k.replace(/^[a-z]+::/, ''), eargs = { name: tg.id.charAt(0).toUpperCase() + tg.id.slice(1) + ' ' + it.n, region: { element: tg.element }, finish: 'base::gloss', color: 'source' }; if (it._type === 'spec') eargs.spec_patterns = [stL(c, eid)]; else eargs.pattern = stL(c, eid); return { steps: [{ tool: 'add_zone', args: eargs, zone: eargs.name }], label: tg.label, texture: true }; }
            if (!tz.length) return { error: 'there is no ' + tg.label.replace(/^the /, '') + ' zone to put a texture on yet. Give it a finish first (use any finish card), then ask for the texture again.' };
            tz.forEach(function (z) {
                var zref = (z.id && z.id !== 'undefined' && z.id !== 'null') ? { zone_id: z.id } : { zone: z.i, expect_name: z.name };
                if (it._type === 'spec') { var st = (z.specLayers && z.specLayers.length ? z.specLayers : (z.specStack || []).map(function (x) { return { id: x }; })).filter(function (x) { return x.id !== tid; }).slice(-4); steps.push({ tool: 'edit_zone', args: merge(zref, { spec_patterns: st.map(function (x) { return merge({}, x); }).concat([stL(c, tid)]) }), zone: z.name }); }      // R05: the layers already on the zone keep their opacity / scale / rotation / channels
                else steps.push({ tool: 'edit_zone', args: merge(zref, { pattern: stL(c, tid) }), zone: z.name });
            });
            return { steps: steps, label: tg.label, texture: true };
        }
        if (hit.length) {
            hit.forEach(function (z) {
                var args = (z.id && z.id !== 'undefined' && z.id !== 'null') ? { zone_id: z.id, finish: c.key } : { zone: z.i, expect_name: z.name, finish: c.key };
                if (it.o === 1) args.color = 'finish'; else if (z.colourMode === 'finish') args.color = 'source'; else if (!z.colour) args.color = 'source';      // R04 (Codex L6): the old own-palette zone has no colour of its own: the source artwork stays, never paint[0] as a flat fill
                steps.push({ tool: 'edit_zone', args: args, zone: z.name });
            });
            return { steps: steps, label: tg.label };
        }
        if (tg.all || tg.id === 'body') {
            steps.push({ tool: 'add_zone', args: { name: it.n + ' body finish', region: { everything: true, paintable: true }, priority: 'bottom', finish: c.key, color: it.o === 1 ? 'finish' : (c.keep ? (cx.hexZone || 'source') : (hex || 'source')) }, zone: it.n + ' body finish' });
            return { steps: steps, label: tg.label };
        }
        if (tg.parts && tg.parts.length) {
            steps.push({ tool: 'add_zone', args: { name: tg.id.charAt(0).toUpperCase() + tg.id.slice(1) + ' ' + it.n, region: { part: tg.parts.length === 1 ? tg.parts[0] : tg.parts }, finish: c.key, color: it.o === 1 ? 'finish' : (c.keep ? (cx.hexZone || 'source') : (hex || 'source')) }, zone: tg.id });
            return { steps: steps, label: tg.label };
        }
        if (tg.element && env.elements && env.elements[tg.element] && env.elements[tg.element].found) { var enm = tg.id.charAt(0).toUpperCase() + tg.id.slice(1) + ' ' + it.n; return { steps: [{ tool: 'add_zone', args: { name: enm, region: { element: tg.element }, finish: c.key, color: it.o === 1 ? 'finish' : 'source' }, zone: enm }], label: tg.label }; }
        return { error: 'there is no ' + tg.label.replace(/^the /, '') + ' zone on this car yet. Add them first (for example “add racing stripes”), then ask me for the finish.' };
    }

    // ================================================================== B2 STACK PLANNER (2026-10-03, worker B2; docs/handoff_reports/B2_stack_planner.md)
    // One intricate sentence -> a LAYERED plan for ONE zone: BASE (colour + look) + PATTERN (paint art at a scale / strength) + SHINE (spec pattern), each layer with an
    // ADJUST block of the zone controls the kit really has (SpbProZone.SCHEMA / edit(): color, hue -180..180, saturation -100..100, brightness -100..200, spec_strength 0-200 %,
    // scale 0.05-5, rotation 0-359, pattern {opacity 0-100, scale, rotation}, spec_patterns [{opacity, scale}]). "a pink camo rattlesnake look" = a camo look + hue/colour to pink
    // + a snake-scale pattern layer. A single-layer ask returns null: the advisor then runs exactly as before (stack_test.js: 10 single asks byte-identical).
    var ST_C = [      // [id, words, catalogue-name regex, lanes allowed (p = paint pattern, s = spec / shine texture, b = base look), sparkle?]
        ['carbon', /\bcarbon(?:[- ]?fib(?:re|er))?\b|\bcf\b/, /carbon/i, 'psb'], ['kevlar', /\bkevlar\b|\baramid\b/, /kevlar/i, 'ps'], ['weave', /\bweaves?\b|\bwoven\b|\btwill\b|\bbasket ?weave\b/, /weave|twill|woven/i, 'ps'],
        ['camo', /\bcamo\w*|\bcamouflage\b|\bmulticam\b/, /camo|multicam/i, 'pb'], ['hex', /\bhex\w*|\bhoneycomb\w*/, /hex|honeycomb|graphene/i, 'ps'], ['mesh', /\bmesh\b|\bchain ?link\b/, /mesh/i, 'ps'],
        ['diamondplate', /\bdiamond ?plate\b|\btread ?plate\b|\bchecker ?plate\b/, /diamond plate|tread/i, 'ps'], ['diamond', /\bdiamonds?\b|\bargyle\b|\blozenges?\b/, /diamond|argyle|lozenge/i, 'ps'],
        ['checker', /\bcheck(?:er|ers|ered|erboard)\b|\bchequer\w*/, /checker|chequer/i, 'ps'], ['plaid', /\bplaid\b|\btartan\b/, /plaid|tartan/i, 'p'], ['houndstooth', /\bhoundstooth\b/, /houndstooth/i, 'ps'],
        ['chevron', /\bchevrons?\b|\bzig ?zags?\b/, /chevron|zigzag/i, 'ps'], ['pinstripe', /\bpin ?stripes?\b|\bstripes? pattern\b|\bstriped pattern\b|\bpattern of stripes\b/, /pinstripe|stripe/i, 'p'],
        ['tiger', /\btiger(?: ?stripes?)?\b/, /tiger/i, 'pb'], ['zebra', /\bzebra\b/, /zebra/i, 'pb'], ['leopard', /\bleopard\b|\bcheetah\b|\bjaguar\b/, /leopard|cheetah|jaguar/i, 'psb'],
        ['snake', /\b(?:rattle)?snakes?\w*|\bpython\b|\bcobra\b|\bviper\b|\breptil\w*|\bcroc\w*|\balligator\b|\blizard\b/, /snake|python|cobra|viper|reptile|croc|alligator|lizard/i, 'psb'],
        ['scales', /\b(?:dragon|fish|mermaid|koi)[- ]?scales?\b|\bscales\b|\bscale pattern\b|\bscaled\b/, /scale/i, 'psb'], ['marble', /\bmarbl\w*|\bveins?\b|\bveined\b|\bveining\b/, /marble|vein/i, 'psb'], ['wood', /\bwood(?: ?grain)?\b/, /wood/i, 'pb'],
        ['tessellation', /\btessellat\w*|\btiles?\b|\btiled\b|\bmosaic\b/, /tessellat|tile|mosaic/i, 'ps'], ['geometric', /\bgeometric\w*|\btriangles?\b|\bpolygon\w*|\blattice\b|\bfacets?\b/, /geometr|triang|polygon|lattice|tessellat/i, 'ps'],
        ['circuit', /\bcircuit\w*/, /circuit/i, 'ps'], ['splatter', /\bsplatter\w*|\bsplash\w*|\bdrips?\b|\bdripping\b/, /splatter|splash|drip/i, 'p'], ['tribal', /\btribal\b|\btattoo\w*/, /tribal|tattoo/i, 'p'],
        ['aztec', /\baztec\b/, /aztec/i, 'p'], ['celtic', /\bceltic\b|\bknots?\b|\btriskel\w*/, /celtic|knot|triskel/i, 'ps'], ['deco', /\bart ?deco\b|\bdeco\b/, /deco/i, 'ps'], ['paisley', /\bpaisley\b/, /paisley/i, 'p'],
        ['floral', /\bfloral\b|\bflowers?\b|\bhibiscus\b|\bsakura\b|\bblossoms?\b/, /floral|flower|hibiscus|sakura|blossom/i, 'psb'], ['swirl', /\bswirl\w*/, /swirl/i, 'pb'], ['wave', /\bwaves?\b|\bwavy\b|\bripples?\b/, /wave|ripple/i, 'ps'],
        ['topo', /\btopo\w*|\bcontours?\b|\bterrain\b/, /topograph|terrain|contour/i, 'ps'], ['pixel', /\bpixel\w*|\bdigital\b|\b8.?bit\b/, /pixel|digital/i, 'p'], ['graffiti', /\bgraffiti\b/, /graffiti/i, 'p'],
        ['damascus', /\bdamascus\b/, /damascus/i, 'psb'], ['feather', /\bfeathers?\b/, /feather/i, 'ps'], ['chainmail', /\bchain ?mail\b/, /chainmail|chain/i, 'p'], ['grid', /\bgrid\b|\bcrosshatch\w*/, /grid|hatch/i, 'ps'],
        ['dots', /\bpolka(?: ?dots?)?\b|\bdots\b|\bspots\b|\bdotted\b/, /dot|polka|spot/i, 'p'], ['stars', /\bstars\b|\bstar ?field\b|\bstarry\b/, /star/i, 'ps', 1], ['lightning', /\blightning\b/, /lightning|bolt/i, 'pb'],
        ['skull', /\bskulls?\b/, /skull/i, 'p'], ['flames', /\bflames?\b|\bhot ?rod flames\b/, /flame|fire|inferno|blaze/i, 'pb'],
        ['crack', /\bcracks?\b|\bcracked\b|\bfractur\w*|\bshatter\w*/, /crack|fractur|shatter/i, 'ps'], ['butterfly', /\bbutterfl\w*|\bmorpho\b/, /butterfl|morpho/i, 'psb'],      // MSR-FIX-A
        ['giraffe', /\bgiraffe\b/, /giraffe/i, 'p'], ['barbed', /\bbarbed(?: ?wire)?\b|\brazor ?wire\b/, /barbed/i, 'pb'], ['sunburst', /\bsun ?bursts?\b|\bsun ?rays?\b|\brising sun\b/, /sunburst|sun ?ray|rising sun/i, 'pb'], ['squiggle', /\bsquiggl\w*/, /squiggle/i, 'pb'],      // MSR-FIX-A
        ['flake', /\bmetal ?flakes?\b|\bflakes?\b|\bflaked\b|\bflakey\b|\bglitter\w*|\bsparkl\w*|\bstardust\b|\bmicro ?flake\b|\bdisco ?ball\b|\bmirror ?ball\b|\bsequin\w*/, /flake|stardust|sparkl|glitter|starlet|metallic sand/i, 's', 1],
        ['pearl', /\bpearl\w*|\bshimmer\w*|\bnacre\b|\bmother of pearl\b|\bmica\b/, /pearl|nacre|abalone|mica/i, 'sb', 1], ['holo', /\bholo\w*|\biridescen\w*|\bprism\w*|\brainbow\b|\bdiffraction\b|\boil ?slick\b/, /holo|iridescent|prism|diffraction|chameleon|rainbow/i, 'sb', 1],
        ['brushed', /\bbrushed\b|\bgrain\b|\bmachined\b/, /brush/i, 'sb'], ['hammered', /\bhammer\w*|\bpeen\w*|\bdimpl\w*/, /hammer|peen|dimple/i, 'ps'], ['frost', /\bfrost\w*|\bsandblast\w*|\bfrozen\b/, /frost|sandblast|dew|fog/i, 's'],
        ['peel', /\borange ?peel\b/, /orange peel/i, 's'], ['engine', /\bengine[- ]?turn\w*|\bguilloch\w*|\bjewel+ed\b/, /engine.?turn|guilloch/i, 's'], ['knurl', /\bknurl\w*/, /knurl/i, 's'], ['crackle', /\bcrackl\w*|\bcrazed\b|\bcrazing\b/, /crackle|craz/i, 's'],
        ['weathered', /\bweather\w*|\brusty\b|\brusted\b|\bcorrod\w*|\bcorrosion\b|\bpatina\b|\bpitted\b/, /corros|rust|oxide|patina|pitting|salt spray|scuff|chipping/i, 'sb'], ['anodized', /\banodi[sz]ed\b/, /anodi/i, 's']
    ];
    var ST_CUE_PAT = /\b(?:pattern|patterned|print|printed|graphic|design|art|motif)\b/, ST_CUE_SPEC = /\b(?:spec|textures?|textured|shine texture|sheen|shine|in the (?:sun|light)|catch(?:es)? the light|under (?:it|the (?:paint|clear|colou?r))|underneath|beneath|ghost\w*|only shows?|when the light hits|in the clear|in the shine)\b/;
    var ST_LOOK = /\b(?:stealth\w*|murdered out|blacked out|candy|pearl\w*|metallic|metal|chrome|satin|matte|matt|flat|gloss\w*|shiny|gunmetal|chameleon|anodi[sz]ed|ceramic|wet|deep|dark|neon|fluorescent|primer|raw|mirror|stealth|brushed metal|liquid metal)\b/;
    var ST_TOP = /\b(?:satin|matte?|flat|gloss(?:y)?|wet|high gloss|clear) (?:top|top ?coat|clear(?: ?coat)?|finish on top|on top)\b|\b(?:topped|finished) (?:off )?(?:with|in) (?:a )?(?:satin|matte|gloss\w*|wet)\b|\bwet clear\b|\bclear ?coat(?:ed)? (?:in )?(?:satin|matte|gloss)\b/;
    var ST_ITEM = /\b(?:one|look|finish|style|kind|vibe|effect)\b/, ST_CALM = /\b(?:subtle|subtly|classy|tasteful|understated|refined|elegant|quiet|not (?:too )?(?:loud|busy|flashy|crazy|much)|nothing (?:loud|crazy|flashy|too much)|toned down|low[- ]?key)\b/;
    var ST_ORDER = /^\s*(?:please\s+)?(?:(?:can|could|would|will) you\s+)?(?:make|put|paint|add|turn|change|set|apply|use|switch|wrap|cover|colou?r|fill|create|build|design|do|swap|replace|redo|spray|recolou?r|remove|delete)\b/;
    var ST_SCHEME = /\b(?:scheme|livery|liveries|throwback|tribute|replica|halloween|christmas|sponsor\w*|logos?|numbers?|decals?)\b/;
    var ST_CONN = /\s*(?:,|;|\bw\/|\bwith\b|\bover (?:it|that|the top|top|everything)\b|\bover\b|\bunder(?:neath)? (?:it|that|everything)\b|\bon top(?: of (?:it|that))?\b|\btopped (?:off )?with\b|\bplus\b|\band (?:then )?(?:a|an|some)\b|\band\b(?= (?:fine|subtle|big|bold|tiny|small|large|light|faint)\b)|\bbut (?:with |in |make it |more |less )?|\blayered (?:on top|over)?\b|\bfinished (?:in|with)\b|\bthen\b)\s*/;
    var ST_STOP = /\b(?:a|an|the|with|and|some|it|its|over|under|underneath|top|on|my|car|body|base|coat|layer|layers|layered|finish|look|looks|one|that|this|but|in|of|for|only|just|really|very|nice|cool|please|i|i'd|id|want|wants|would|like|love|something|kind|sort|maybe|plus|then|paint|painted|colou?r|colou?red|pattern|patterns|patterned|texture|textures|textured|spec|specular|style|vibe|effect|pairs?|pairing|goes|suits?|match|matches|works?|which|layer|kinda|bit|little|shows?|in|sun|light|all|whole|entire|thing|stuff|also|too|so|lot|lots|of|done|have|get|give|go|me|maybe|ish|thats|that's|which|what|how|could|can|should|do|does|is|are|be|look|looking|get|got|over|it|everything|clear|clearcoat)\b/g;
    var ST_MODS = [[/\b(?:toned? down|tone it down|calmer|softer|less (?:loud|flashy|bright|shiny|intense)|subtler|dialed back)\b/, { spec_strength: 75, saturation: -15 }, 'toned down = spec strength 75% and 15 less saturation'],
        [/\b(?:darker|deeper|dark(?:en)? it)\b/, { brightness: -25 }, 'darker = brightness -25'], [/\b(?:lighter|brighter)\b/, { brightness: 25 }, 'lighter = brightness +25'],
        [/\b(?:more vivid|punchier|more saturated|richer|more colou?r)\b/, { saturation: 30 }, 'more vivid = saturation +30'], [/\b(?:muted|faded|washed[- ]out|desaturated|less colou?r)\b/, { saturation: -40 }, 'muted = saturation -40'],
        [/\b(?:shinier|more shine|glossier|wetter)\b/, { spec_strength: 130 }, 'shinier = spec strength 130%'], [/\b(?:duller|less shine|less shiny|less gloss)\b/, { spec_strength: 70 }, 'duller = spec strength 70%']];
    function stHsl(h) { if (!/^#[0-9a-f]{6}$/i.test(String(h || ''))) return null; var r = parseInt(h.substr(1, 2), 16) / 255, g = parseInt(h.substr(3, 2), 16) / 255, b = parseInt(h.substr(5, 2), 16) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn, s = 0, hh = 0;
        if (d > 1e-6) { s = d / (1 - Math.abs(2 * l - 1)); hh = mx === r ? ((g - b) / d) % 6 : (mx === g ? (b - r) / d + 2 : (r - g) / d + 4); hh *= 60; if (hh < 0) hh += 360; } return { h: hh, s: s * 100, l: l * 100 }; }
    function stClamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
    function stScale(t) {          // size words of ONE clause -> a pattern / spec / base texture scale (1 = normal)
        var m = /\bcrushed (?:down )?to (\d{1,3})\s*%|\b(\d{1,3})\s*% (?:scale|size)\b|\bat (\d{1,3})\s*%(?! (?:opacity|strength|intensity))|\bscale (?:of )?(\d?\.\d+|\d{1,3}\s*%)/.exec(t);
        if (m) { var v = m[1] || m[2] || m[3] || m[4], n = /%/.test(v) || Number(v) > 5 ? parseFloat(v) / 100 : parseFloat(v); if (n > 0) return stClamp(Math.round(n * 100) / 100, 0.05, 5); }
        if (/\bhalf (?:the )?(?:size|scale)\b/.test(t)) return 0.5; if (/\bdouble (?:the )?(?:size|scale)\b|\btwice (?:as big|the size)\b/.test(t)) return 2;
        if (/\b(?:tiny|micro|very fine|super fine|crushed|pin ?point)\b/.test(t)) return 0.35;
        if (/\b(?:fine|finer|small|smaller|tight|tighter|thin|little|delicate)\b/.test(t)) return 0.5;
        if (/\b(?:huge|giant|massive|oversized|enormous)\b/.test(t)) return 2.2;
        if (/\b(?:big|bigger|large|larger|bold|wide|chunky|chunkier|coarse|coarser|sweeping)\b/.test(t)) return 1.6;
        return null;
    }
    function stScaleAbs(t) { var m = /\bcrushed (?:down )?to (\d{1,3})\s*%|\b(\d{1,3})\s*% (?:scale|size)\b|\bat (\d{1,3})\s*%(?! (?:opacity|strength|intensity))|\bscale (?:of )?(\d?\.\d+|\d{1,3}\s*%)/.exec(t); if (!m) return null; var v = m[1] || m[2] || m[3] || m[4], n = /%/.test(v) || Number(v) > 5 ? parseFloat(v) / 100 : parseFloat(v); return n > 0 ? stClamp(Math.round(n * 100) / 100, 0.05, 5) : null; }
    function stScaleRel(t) {      // PUSH2: [multiplier of the layer's default size, the word]
        var m;
        if ((m = /\bhalf (?:the )?(?:size|scale)\b/.exec(t))) return [0.5, m[0]]; if ((m = /\bdouble (?:the )?(?:size|scale)\b|\btwice (?:as big|the size)\b/.exec(t))) return [2, m[0]];
        if ((m = /\b(?:tiny|micro|very fine|super fine|pin ?point)\b/.exec(t))) return [0.4, m[0]];
        if ((m = /\b(?:fine|finer|small|smaller|tight|tighter|thin|little|delicate)\b/.exec(t))) return [0.6, m[0]];
        if ((m = /\b(?:huge|giant|massive|oversized|enormous)\b/.exec(t))) return [2, m[0]];
        if ((m = /\b(?:big|bigger|large|larger|bold|wide|chunky|chunkier|coarse|coarser|sweeping)\b/.exec(t))) return [1.4, m[0]];
        return null;
    }
    function stFineScale(cd) { var bz = cd && cd.busy != null ? Number(cd.busy) : 3; return bz >= 4 ? 0.7 : (bz <= 2 ? 1.1 : 0.85); }      // PUSH-VISIBLE: card busyness -> default pattern size (fine 0.7, bold 1.1)
    function stIntensity(t) {      // strength words of ONE clause -> pattern / spec opacity 0-100 (70 = the advisor's default)
        var m = /\b(\d{1,3})\s*% (?:opacity|strength|intensity|visible)\b/.exec(t); if (m) return stClamp(Number(m[1]), 5, 100);
        if (/\b(?:subtle|subtly|faint|faintly|ghost\w*|hint of|barely|whisper|tasteful|quiet|soft)\b/.test(t)) return 35;
        if (/\blight(?!\s+(?:blue|green|grey|gray|pink|purple|red|yellow|orange|brown|tan|teal|silver|gold|bronze))\b|\bsoft\b|\bslight\w*/.test(t)) return 50;
        if (/\b(?:bold|strong|loud|heavy|in your face|vivid|punchy|full)\b/.test(t)) return 90;
        return null;
    }
    function stConcepts(t) { var o = []; ST_C.forEach(function (c) { var m = c[1].exec(t); if (m) o.push({ c: c, pos: m.index }); }); o.sort(function (a, b) { return a.pos - b.pos; }); return o.map(function (x) { return x.c; }); }
    function stQuery(t, tg) { var q = String(t || '').toLowerCase(); TARGETS.forEach(function (x) { if (!x.all) q = q.replace(new RegExp(x.re.source, 'g'), ' '); }); return q.replace(/\d+\s*%|\b\d+(?:\.\d+)?\b/g, ' ').replace(/\b(?:crushed|scale|size|fine|finer|tiny|micro|small|big|bigger|large|huge|bold|subtle|faint|ghosted|light|strong|only|tasteful|not too busy|busy|loud)\b/g, ' ').replace(ST_STOP, ' ').replace(/[^a-z0-9' ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    // MSR-FIX-A (2026-10-03): "tiger stripes ON A SATIN BLACK CAR" = a layer over a base (never a part: "on the hood" stays a part binding)
    function stOnSplit(s) { return s.replace(/(?<!\b(?:work|works|go|goes|looks?|suits?|best|well|good|what|which))\s+on\s+(?!top\b|(?:the\s+)?(?:light|sun|angle|edges?)\b)((?:(?:a|an|the|my)\s+)?[^,;]+)/g, function (m0, rest) { var tc = null; try { tc = targetOf(rest); } catch (e) {} if (tc && !tc.all) return m0; return (colourOf(rest) || ST_LOOK.test(rest) || /\b(?:car|body|base)\b/.test(rest)) ? ' over ' + rest : m0; }); }
    // PUSH2-PLANNER (2026-10-03): "X under Y" / "X underneath Y" / "X beneath Y": X is the LOWER layer (the pattern), Y the base look -> "Y with X";
    // when Y is a coat / clear / top ("carbon under a candy coat") X stays the base and Y rides on it -> "X with a Y". "under it / the paint / the clear" is left alone.
    function stUnder(s) {
        var m = /^(.*?\S)\s+(?:under(?:neath)?|beneath|below)\s+(?!(?:it|that|this|everything|them|there|the (?:paint|clear\w*|colou?r|base|light|sun|hood|roof))\b)(?:(?:a|an|the|some|my)\s+)?([^,;?]+)(.*)$/.exec(s);
        if (!m || /[,;]|\b(?:what|which|how|goes|go|would|could|over|on top)\b/.test(m[1]) || !stConcepts(m[1]).length) return s;
        if (/\b(?:coat|coats|clear|clearcoat|top|topcoat|finish)\b/.test(m[2])) return m[1] + ' with a ' + m[2] + m[3];
        return m[2] + ' with ' + m[1] + m[3];
    }
    var ST_GEN = { dots: 1, scales: 1, pinstripe: 1 };      // MSR-FIX-A: "leopard spots", "snake scales", "zebra stripes" = ONE concept (the generic noun only names the animal's marks)
    function stMergeGen(t, cs) { if (cs.length < 2) return cs; return cs.filter(function (c) { if (!ST_GEN[c[0]]) return true; return !cs.some(function (d) { return d !== c && !ST_GEN[d[0]] && new RegExp('(?:' + d[1].source + ')\\s+(?:' + c[1].source + ')').test(t); }); }); }
    function stackParse(raw, prev) {
        var t = String(raw || '').toLowerCase().replace(/[’`]/g, "'").trim(); if (!t || t.length > 400 || t.split(/\s+/).length > 45) return null;
        var pos = t; try { pos = stripNeg(t); } catch (e) {}
        // Composition tails express preservation constraints, not additional paint targets.
        function stripScopeTail(s) { return String(s || '')
            .replace(/\b(?:and\s+)?(?:leave|keep|preserve)\s+(?:(?:all|every|the|remaining|other)\s+)*(?:rest|other panels?|remaining panels?|other paint|every other panels?|all other paint)\b[^.;,]*/g, ' ')
            .replace(/\b(?:and\s+)?nothing else\b[^.;,]*/g, ' ')
            .replace(/\b(?:and\s+)?do not touch\b[^.;,]*/g, ' ')
            .replace(/\bkeep that base\b/g, ' ')
            .replace(/\s+/g, ' ').trim(); }
        t = stripScopeTail(t); pos = stripScopeTail(pos);
        pos = pos.replace(/\b(?:just|only)\s+(?=(?:on\s+)?(?:the\s+)?(?:hood|roof|sides?|trunk|spoiler|stripes|bumpers?|doors?)\b)/g, '');      // PUSH2: "on just the sides" = on the sides
        pos = stOnSplit(stUnder(pos));      // MSR-FIX-A      // PUSH2: "marble under candy red" = candy red base + marble
        var parts = pos.split(ST_CONN).map(function (s) { return s.trim(); }), conns = [], mm, re = new RegExp(ST_CONN.source, 'g');
        while ((mm = re.exec(pos))) { conns.push(mm[0].trim()); if (mm[0].length === 0) re.lastIndex++; }
        var cl = [], i, P2 = [], C2 = [];      // B2p7: re-split at a plain "and" when both halves name a layer kind
        function layerish(x) { return stConcepts(x).length > 0 || ST_LOOK.test(x) || !!colourOf(x); }
        parts.forEach(function (pt, k) { var bits = pt.split(/\s+and\s+/); if (bits.length === 2 && layerish(bits[0]) && layerish(bits[1]) && (stConcepts(bits[0]).length || stConcepts(bits[1]).length)) { P2.push(bits[0], bits[1]); C2.push('and', conns[k]); } else { P2.push(pt); C2.push(conns[k]); } });
        if (P2.length !== parts.length) { parts = P2; conns = C2; }
        for (i = 0; i < parts.length; i++) { if (!parts[i]) continue; cl.push({ t: parts[i], conn: (conns[i - 1] || '') + ' ' + (conns[i] || ''), idx: cl.length, under: /^over\b/.test(conns[i - 1] || ''), over: /^over\b/.test(conns[i] || '') }); }      // MSR-FIX-A: under = this clause sits UNDER the previous one ("tiger stripes over a satin black car")
        if (!cl.length) return null;
        var slots = { base: [], pattern: [], spec: [] }, top = null, adj = {}, adjWhy = [], likeKey = null, colour = null, conceptBase = null;
        var lk = /\b(?:like|similar to)\s+(?:the\s+)?([a-z0-9' -]{3,40}?)\s+(?:but|with|and|except)\b/.exec(pos); if (lk) { var nk = resolveName(lk[1]) || ((findFinishesIn(lk[1], 1)[0] || {}).key); if (nk && AT().lookup(nk)) likeKey = AT().lookup(nk).k; }
        cl.forEach(function (c) {
            var ts = c.t, cs = stMergeGen(ts, stConcepts(ts)), col = stHexCol(ts, colourOf(ts.replace(/\b(?:not|no|nothing|without|less|never)\s+(?:so\s+|too\s+|very\s+|any\s+|that\s+|as\s+)?[a-z]+(?:\s+(?:or|and|nor)\s+[a-z]+)*/g, ' '))),      /* MSR-FIX-A: 'pink and not so brown' asks pink; a hex is exact */ look = ST_LOOK.test(ts), itemish = ST_ITEM.test(ts), isTop = ST_TOP.test(ts + ' ' + c.conn);
            c.colour = col; c.cs = cs;
            if (/\b(?:is|are|was|looks?) (?:way |far |a bit |kinda )?too (?:much|loud|bright|strong|busy|big|small|dark|light|flashy)\b|\btoo much\b/.test(ts) && c.idx > 0) { c.kind = 'filler'; c.colour = null; return; }      // MSR-FIX-A: "..., the pink is too much" is a complaint, never the base
            ST_MODS.forEach(function (m) { if (m[0].test(ts)) { for (var k in m[1]) adj[k] = m[1][k]; adjWhy.push(m[2]); } });
            if (likeKey && /\blike\b|\bsimilar to\b/.test(ts)) { c.kind = 'base'; c.like = true; return; }
            if (!cs.length) {
                if (isTop && !col && !/\b(?:candy|pearl|metallic|chrome)\b/.test(ts)) { top = /satin/.test(ts + ' ' + c.conn) ? 'satin' : (/matte?|flat/.test(ts + ' ' + c.conn) ? 'flat' : 'glossy'); c.kind = 'top'; return; }
                if (col && !look && /\bbut\b/.test(c.conn) && c.idx > 0) { c.kind = 'mod'; return; }      // B2p3: "the green flake one but blue and finer": the colour after but ADJUSTS the item
                if (/\bspec(?:ular)?\b/.test(ts) && c.idx > 0) { c.kind = 'spec'; c.cs = []; c.anyTex = true; c.specOnly = true; return; }      // MSR-FIX-A: "a neon spec pattern" is a shine layer, not a second base
                if (col || look) { c.kind = 'base'; return; }
                if (/\b(?:textures?|grain|pattern|patterns|spec|layer)\b/.test(ts) && !col) { c.kind = 'spec'; c.cs = []; c.anyTex = true; return; }      // B2p5: a texture with no named kind: both texture lanes compete
                c.kind = stScale(ts) != null || Object.keys(adj).length ? 'mod' : 'filler'; return;
            }
            var specWord = /\bspec(?:ular)?\b|\bin the shine\b/.test(ts), first = cs[0], specCue = (ST_CUE_SPEC.test(ts + ' ' + c.conn) && !ST_CUE_PAT.test(ts)) || specWord, patCue = ST_CUE_PAT.test(ts) && !specWord;      // B2p5
            c.specCue = specCue;
            if (cl.slice(0, c.idx).every(function (x) { return x.kind === 'filler'; }) && !c.over && cs.length === 1 && first[3] === 'sb' && !specCue && !patCue && cl.length >= 2 && !cl.some(function (x) { return x !== c && !stConcepts(x.t).length && (colourOf(x.t) || ST_LOOK.test(x.t)); })) { c.kind = 'base'; return; }      // MSR-FIX-A: "brushed titanium with a fine diamond pattern": the brushed metal is the base
            if (c.under && (col || look || first[3].indexOf('b') !== -1) && !specCue && !patCue && cs.length === 1 && (col || first[3].indexOf('p') === -1)) { c.kind = 'base'; return; }      // MSR-FIX-A: "what goes well over pearl white": the clause under "over" is the base
            if (c.idx === 0 && col && cs.length === 1 && first[3].indexOf('b') !== -1 && !specCue && !patCue && cl.length >= 2 && (first[3].indexOf('p') === -1 || /\b(?:body|base|paint(?:ed|job)?)\b/.test(ts))) { c.kind = 'base'; return; }      // MSR-FIX-A: "dragon scales in emerald green with a metallic shine" = scales are the PATTERN      // B2p2: "pearl blue body with ...": a colour + a look word is the base
            var matB = cs.length >= 2 ? cs.filter(function (x) { return x !== first && x[3].indexOf('b') !== -1 && new RegExp('\\b(?:in|made of|made out of|out of|from)\\s+(?:a\\s+|an\\s+|some\\s+)?(?:\\w+\\s+)?(?:' + x[1].source + ')').test(ts); })[0] : null;
            if (matB && !patCue && !specCue) { c.kind = 'conceptbase'; c.baseC = matB; c.rest = cs.filter(function (x) { return x !== matB; }); return; }      // MSR-FIX-A: "dragon scales in carbon fiber" = carbon base, scales on it
            if (cs.length >= 2 && first[3].indexOf('b') !== -1 && !patCue && !specCue) { c.kind = 'conceptbase'; c.baseC = first; c.rest = cs.slice(1); return; }      // "pink camo rattlesnake look": the first concept is the LOOK, the others are layers on it
            if (itemish && !patCue && !specCue && !specWord && cl.length >= 2 && (first[3].indexOf('b') !== -1 || /\b(?:one|finish)\b/.test(ts)) && !(first[3].indexOf('p') !== -1 && cl.some(function (x) { return x !== c && !stConcepts(x.t).length && (colourOf(x.t) || ST_LOOK.test(x.t)); }))) { c.kind = 'conceptbase'; c.baseC = first; c.rest = []; return; }      // "the green flake one", "a carbon look"      // MSR-FIX-A: "snow leopard look, grey and white with soft spots": another clause is the base, the animal is the pattern
            c.kind = (patCue && first[3].indexOf('p') !== -1) ? 'pattern' : ((specCue && first[3].indexOf('s') !== -1) ? 'spec' : (first[3].charAt(0) === 's' ? 'spec' : (first[3].charAt(0) === 'p' ? 'pattern' : 'base')));
        });
        // two looks for the base ("a carbon look but in candy purple"): the plain colour / look clause is the base, the concept look becomes a layer
        var plainBase = cl.filter(function (c) { return c.kind === 'base' && !c.like; }), cb = cl.filter(function (c) { return c.kind === 'conceptbase'; });
        if ((plainBase.length || likeKey) && cb.length) cb.forEach(function (c) { var allc = [c.baseC].concat(c.rest); if (likeKey || /\b(?:candy|pearl|chrome|metallic|matte|satin|gloss\w*)\b/.test(plainBase.map(function (x) { return x.t; }).join(' '))) { c.kind = (c.specCue && allc[0][3].indexOf('s') !== -1) || allc[0][3].indexOf('p') === -1 ? 'spec' : 'pattern'; c.cs = allc; /* B2: "carbon weave UNDER it" = a shine texture */ } });
        cl.forEach(function (c) {
            if (c.kind === 'base') { slots.base.push(c); if (c.colour && !colour) colour = c.colour; }
            else if (c.kind === 'conceptbase' && conceptBase) { [c.baseC].concat(c.rest || []).forEach(function (rc) { var k = rc[3].indexOf('p') !== -1 && !(c.specCue && rc[3].indexOf('s') !== -1) ? 'pattern' : 'spec'; if (rc[3].indexOf('p') === -1 && rc[3].indexOf('s') === -1) return; slots[k].push({ t: c.t, cs: [rc], conn: c.conn, sub: true }); }); }      // MSR-FIX-A: "pearl camo with holographic hex edges": the second concept look is layers
            else if (c.kind === 'conceptbase') { conceptBase = c; slots.base.push(c); if (c.colour && !colour) colour = c.colour; c.rest.forEach(function (rc) { var k = rc[3].indexOf('p') !== -1 ? 'pattern' : 'spec'; slots[k].push({ t: c.t, cs: [rc], conn: c.conn, sub: true }); }); }
            else if (c.kind === 'pattern' || c.kind === 'spec') { slots[c.kind].push(c); if (!slots.base.length && c.colour && c.idx > 0) { /* a colour inside a layer clause is the layer's colour */ } }
            else if (c.kind === 'mod' && c.colour && !colour) colour = c.colour;
        });
        var modCol = cl.filter(function (c) { return c.kind === 'mod' && c.colour; })[0]; if (modCol) colour = modCol.colour;      // B2p3: the asked colour beats the item's own colour word
        if (!colour) { cl.forEach(function (c) { if (!colour && c.colour && (c.kind === 'mod' || c.kind === 'filler' || c.kind === 'top')) colour = c.colour; }); }
        if (!colour && (slots.base.length || likeKey)) { var bc = slots.base.map(function (c) { return c.t; }).join(' '); colour = colourOf(bc); }
        if (!colour) cl.forEach(function (c) { if (!colour && c.colour && (c.kind === 'pattern' || c.kind === 'spec')) colour = c.colour; });      // MSR-FIX-A: "dragon scales in deep emerald green with a metallic shine": the colour leads the base
        var kmine = /\b(?:keep|leave) (?:my|the|it) ([a-z' ]{2,30})/.exec(t), keepMine = !!(kmine && colourOf(kmine[1].split(' ').slice(0, 3).join(' ')));      // B2p6: "keep my red"
        if ((KEEP_RE.test(t) || keepMine) && slots.base.length && !likeKey && !slots.base.some(function (c) { return ST_LOOK.test(c.t) || c.kind === 'conceptbase'; })) slots.base = [];      // B2p5: "keep my red but ...": the paint stays, the layers go on it
        if (KEEP_RE.test(t) || keepMine) slots.pattern = slots.pattern.filter(function (c) { var cs0 = c.cs || []; if (cs0.length === 1 && cs0[0][0] === 'hammered' && !ST_CUE_PAT.test(c.t)) { slots.spec.push(c); return false; } return true; });      // MSR-FIX-A: the paint stays -> shine textures only
        var isHam = function (c) { return (c.cs || []).length === 1 && c.cs[0][0] === 'hammered'; }, hamP = slots.pattern.filter(isHam);      // MSR-FIX-A: hammered metal = pattern + its shine; next to another pattern = the shine only
        if (hamP.length && slots.pattern.length > hamP.length) hamP.forEach(function (c) { slots.pattern.splice(slots.pattern.indexOf(c), 1); if (!slots.spec.some(isHam)) slots.spec.push(c); });
        else if (hamP.length && !slots.spec.some(isHam)) slots.spec.push({ t: hamP[0].t, cs: hamP[0].cs, conn: hamP[0].conn, sub: true, echo: true });
        if (!slots.spec.length && slots.pattern.length) slots.base.forEach(function (c) { if (c.kind !== 'base' || c.synth) return; var bc = stMergeGen(c.t, stConcepts(c.t)).filter(function (x) { return x[0] === 'brushed' || x[0] === 'pearl'; })[0]; if (bc && !slots.spec.length) slots.spec.push({ t: c.t, cs: [bc], conn: c.conn, sub: true, echo: true }); });      // MSR-FIX-A: "brushed titanium with a fine diamond pattern": the brushed grain is a shine texture on the metal base
        var synth = false;      // MSR-FIX-A: "carbon but gold", "giraffe patches in brown and cream": a layer + a colour and no base = a base in that colour under the layer
        if (!slots.base.length && !likeKey && colour && (slots.pattern.length || slots.spec.length) && !(KEEP_RE.test(t) || keepMine) && (cl.length >= 2 || /\bin (?:an? )?(?:[a-z]+ ){0,2}[a-z]+/.test(cl[0].t) && cl[0].colour)) { slots.base.push({ t: colour.name, kind: 'base', synth: true, colour: colour }); synth = true; }
        var tgs = {}; cl.forEach(function (c) { var tc = targetOf(c.t); if (tc && !tc.all) tgs[tc.id] = 1; }); if (Object.keys(tgs).length >= 2) return null;
        if (cl.some(function (c) { if (c.kind !== 'pattern' && c.kind !== 'spec') return false; var tc = targetOf(c.t); if (!tc || tc.all || !tc.re || !tc.parts) return false; var m = tc.re.exec(c.t); return !!m && !/\b(?:on|for|to|across|over|along|down)\s+(?:the\s+|my\s+|both\s+)?(?:\w+\s+)?$/.test(c.t.slice(0, m.index)); })) return null;      // B2p9: "a carbon fiber HOOD" = the hood is a second zone (the designer / two-part answer), never the whole stack's part      // B2p5: "carbon on the hood, gloss on the roof" = two parts (the two-part answer handles it)
        var kinds = (slots.base.length || likeKey ? 1 : 0) + (slots.pattern.length ? 1 : 0) + (slots.spec.length ? 1 : 0);
        var adjCue = (colour && cl.some(function (c) { return (c.kind === 'mod' || c.kind === 'filler') && c.colour; })) || Object.keys(adj).length > 0 || cl.some(function (c) { return c.kind === 'mod' && stScale(c.t) != null; });
        var layering = cl.length >= 2 || synth || !!(conceptBase && conceptBase.rest && conceptBase.rest.length);      // B2p3: "a pink camo rattlesnake look" is one clause with two layers
        var adjustOnly = kinds === 1 && layering && (conceptBase || likeKey) && adjCue && !slots.pattern.length && !slots.spec.length;
        if (!((kinds >= 2 && layering) || adjustOnly)) return null;
        var scaleBase = null; cl.forEach(function (c) { if (c.kind === 'mod' && stScale(c.t) != null) scaleBase = stScale(c.t); });
        function lay(arr) { if (!arr.length) return null; var txt = arr.map(function (c) { return c.t; }).join(' '), cs = [], anyT = arr.every(function (c) { return c.anyTex; }), spO = arr.some(function (c) { return c.specOnly; }); arr.forEach(function (c) { (c.cs || []).forEach(function (x) { if (cs.indexOf(x) === -1) cs.push(x); }); }); return { t: txt, cs: cs, any: anyT && !spO, scale: stScale(txt), abs: stScaleAbs(txt), rel: stScaleRel(txt), intensity: stIntensity(txt), conn: arr.map(function (c) { return c.conn; }).join(' ') }; }
        var baseTxt = slots.base.map(function (c) { return c.t; }).join(' ');
        return { text: raw, t: t, clauses: cl, like: likeKey, colour: colour, keep: KEEP_RE.test(t) || keepMine, calm: ST_CALM.test(t), top: top, adjust: adj, adjustWhy: adjWhy, scaleBase: scaleBase, adjustOnly: !!adjustOnly,
            base: (slots.base.length || likeKey) ? { t: baseTxt, concept: conceptBase ? conceptBase.baseC : null, look: ST_LOOK.test(baseTxt), shine: /\b(?:matte?|flat)\b/.test(baseTxt) ? 'flat' : (/\bsatin\b/.test(baseTxt) ? 'satin' : (/\b(?:gloss\w*|shiny|wet|chrome|mirror|candy)\b/.test(baseTxt) ? 'glossy' : null)), named: /\b(?:matte?|flat)\b/.test(baseTxt) } : null,
            pattern: lay(slots.pattern), spec: lay(slots.spec.length > 1 ? [slots.spec[0]] : slots.spec), spec2: slots.spec.length > 1 ? lay(slots.spec.slice(1)) : null, target: targetOf(t) };
    }
    function stHexCol(t, named) { var m = /#([0-9a-f]{6})\b/i.exec(String(t || '')); if (!m) return named || null; var hx = '#' + m[1].toLowerCase(), h = stHsl(hx), nm = named ? named.name : (h.l < 14 ? 'black' : (h.l > 90 ? 'white' : (h.s < 14 ? 'grey' : ['red', 'orange', 'yellow', 'green', 'green', 'teal', 'blue', 'blue', 'purple', 'pink', 'pink', 'red'][Math.floor(((h.h + 15) % 360) / 30)])));
        return { name: nm, hex: hx, exact: true }; }      // MSR-FIX-A: an exact hex in the wish
    function stSizeWant(p) { var v = p ? [p.pattern && p.pattern.scale, p.spec && p.spec.scale, p.scaleBase].filter(function (x) { return x != null; })[0] : null; return v == null ? null : (v < 1 ? 'fine' : (v > 1 ? 'coarse' : null)); }      // MSR-FIX-A
    function stSizeFit(fb, want, base) { if (!want || !fb) return 0; if (want === 'fine') return fb === 'micro' || fb === 'fine' ? 10 : (fb === 'broad' ? -10 : (fb === 'flat' ? (base ? 0 : -4) : -4)); return fb === 'broad' ? 12 : (fb === 'medium' ? 0 : (fb === 'flat' ? 0 : -8)); }
    function stackParseFix(raw) { var p = stackParse(raw); if (p) return p; var fx = raw; try { fx = spellFix(raw); } catch (e) {} if (!fx || fx === raw) return null; p = stackParse(fx); if (p) p.text = raw; return p; }      // MSR-FIX-A: typo'd layer words
    function stBad(it, dis) {      // B2p8: "no chrome" also drops an item that SAYS chrome in its name, one-liner or tags
        if (!it || !dis || !dis.length) return false; var hay = ' ' + String((it.n || '') + ' ' + (it.d || '') + ' ' + (it.t || []).join(' ')).toLowerCase().replace(/[^a-z0-9]+/g, ' ') + ' ';
        return dis.some(function (d) { var w = String(d).toLowerCase().replace(/^(?:no|not|without|any|anything|too)\s+/, '').replace(/[^a-z0-9 ]+/g, ' ').trim(); return w.length >= 3 && w.split(' ').length <= 2 && hay.indexOf(' ' + w) !== -1 && !colourOf(w); });
    }
    function stCard(k) { var C = W.SpbAICards; return (C && C.card(k)) || { look: '', loud: 3, busy: 3, pair: [], avoid: [], appeal: 3, syn: [] }; }
    function stLane(p, lane, o) {      // candidates for one texture layer: catalogue items whose NAME carries the concept first, then the meaning search over that lane
        var a = AT(), R = W.SpbProRank, out = [], seen = {}, ex = {}; (o.exclude || []).forEach(function (k) { ex[k] = 1; });
        var av = {}; try { if (o.avoid && o.avoid.length) av = R.avoidSet(o.avoid); } catch (e) {}
        var items = (a._data().items || []).filter(function (x) { return x._type === lane && !ex[x.k] && !av[x.k] && !stBad(x, o.avoid) && !/REJECTED|\bR\d DEV\b|— R\d DEV/i.test(x.n || ''); });
        var cs = p.cs || [];
        var qw = stQuery(p.t).split(' ').filter(function (w) { return w.length >= 4; });      // the painter's own words in the NAME ("dragon scale" -> Dragon Scale, "carbon weave" -> Carbon Weave)
        items.forEach(function (x) { var n = 0, nl = String(x.n || '').toLowerCase(); cs.forEach(function (c) { if (c[2].test(x.n || '')) n++; }); if (n) { var cd = stCard(x.k), nw = 0; qw.forEach(function (w) { if (nl.indexOf(w.replace(/(?:es|s)$/, '')) !== -1) nw++; }); out.push({ key: x.k, s: 60 + 12 * n + 9 * nw + 3 * (cd.appeal || 3) + (x.q ? x.q / 20 : 0) + stSizeFit(x.fb, o.size), canon: true }); seen[x.k] = 1; } });
        var q = stQuery(p.t) || cs.map(function (c) { return c[0]; }).join(' ');
        if (!q) {      // B2p6: no named texture kind: the ranker's own texture lane (goal / colours / part aware), this lane only
            try { R.suggest({ lane: 'texture', goal: o.calm ? 'subtle' : 'premium', novelty: 1, limit: 16, exclude: (o.exclude || []).slice(), avoid: o.avoid, target: o.target || null, colours: { target: o.hex || null, body: o.hex || null, scheme: o.hex ? [o.hex] : [] }, seed: 11 }).rows.forEach(function (r, i) { var xi = a.lookup(r.key); if (!xi || xi._type !== lane || seen[r.key] || av[r.key] || stBad(xi, o.avoid)) return; seen[r.key] = 1; var cdq = stCard(r.key); if (o.calm && (cdq.loud || 3) > 2) return; out.push({ key: r.key, s: 50 - 2 * i + (/\bfine|micro\b/.test(cdq.scale || '') ? 4 : 0) }); }); } catch (esg) {}
            out.sort(function (x, y) { return y.s - x.s; }); return out;
        }
        try { R.search(q, { types: [lane], limit: 14, exclude: o.exclude, avoid: o.avoid }).forEach(function (r, i) { if (!r.key || !a.lookup(r.key) || av[r.key] || stBad(a.lookup(r.key), o.avoid)) return; if (seen[r.key]) { out.forEach(function (x) { if (x.key === r.key) x.s += 14 - i; }); return; } seen[r.key] = 1; out.push({ key: r.key, s: 40 - 2 * i + (r.hits && r.hits.length ? 3 * r.hits.length : 0) + stSizeFit((a.lookup(r.key) || {}).fb, o.size) }); }); } catch (e2) {}
        out.sort(function (x, y) { return y.s - x.s; });
        return out;
    }
    function stBases(p, o) {          // base candidates: the meaning search on the base words, re-scored for the shine asked, the colour (takes-colour or a hue the sliders can reach) and loudness
        var a = AT(), R = W.SpbProRank, base = p.base, rows = [], colH = p.colour ? stHsl(p.colour.hex) : null, chroma = colH && colH.s > 18 && colH.l > 8 && colH.l < 92;
        var cw = base.concept ? (base.concept[1].exec(base.t) || [base.concept[0]])[0] : null;      // B2p10: the look word only ("camo"), plus the asked colour
        var q = base.concept ? (base.concept[0] === 'carbon' ? 'carbon fiber' : ((p.colour ? p.colour.name + ' ' : '') + cw).trim()) : stQuery(base.t);
        if (!q && p.colour) q = p.colour.name; if (!q) q = 'gloss';
        var want = p.top || base.shine;
        try { rows = R.search(q, { types: ['base', 'monolithic'], limit: 24, exclude: o.exclude, avoid: o.avoid, own: p.keep ? 'takes' : undefined }); } catch (e) { rows = []; }
        if (base.concept) { (a._data().items || []).forEach(function (x) { if ((x._type === 'base' || x._type === 'monolithic') && base.concept[2].test(x.n || '') && !/REJECTED|R\d DEV/.test(x.n || '') && (o.exclude || []).indexOf(x.k) === -1 && !rows.some(function (r) { return r.key === x.k; })) rows.push({ key: x.k, s: 0, why: [], late: true }); }); }
        var av = {}; try { if (o.avoid && o.avoid.length) av = R.avoidSet(o.avoid); } catch (e2) {}
        var out = [];
        rows.forEach(function (r, i) {
            var it = r.key && a.lookup(r.key); if (!it || av[r.key] || stBad(it, o.avoid)) return; var cd = stCard(r.key), s = r.late ? 30 : 100 - 3 * i, notes = [];
            if (base.concept) s += base.concept[2].test(it.n || '') ? 30 : -25;
            if (want) { var sc = shineClass(it); s += sc === want ? 18 : (want === 'glossy' && sc === 'satin' ? -6 : -35); }
            if (/\bcandy\b/.test(base.t)) s += /candy/i.test(it.n + ' ' + cd.look) ? 15 : -10;
            if (/\bpearl/.test(base.t) && !p.spec) s += /pearl/i.test(it.n + ' ' + cd.look) ? 12 : -6;
            if (/\b(?:chrome|mirror)\b/.test(base.t)) s += (it.shine === 'mirror' || it.metal === 'full' || /chrome/i.test(it.n)) ? 15 : -15;
            if (/\bmetallic|\bmetal\b|\bgunmetal\b/.test(base.t)) s += (it.metal && it.metal !== 'none') ? 10 : -10;
            if (p.colour && p.colour.exact) s += it.o !== 1 ? 25 : -15;      // MSR-FIX-A: a hex is exact -> a takes-colour base
            if (p.colour) {
                if (it.o !== 1) s += 8;
                else { var ih = it.c && it.c[0] ? stHsl(it.c[0]) : null; if (ih) { var dh = Math.abs(ih.h - colH.h) % 360; dh = dh > 180 ? 360 - dh : dh; if (chroma) { if (ih.s < 15) s -= 30; else s += dh < 30 ? 28 : (dh < 60 ? 6 : -14); } else s += ih.s < 25 ? 6 : -12; } }      // B2p10: already that hue >> a big hue rotation
            }
            if (p.calm && cd.loud > 3) s -= 20;
            if (cd.busy >= 4 && p.pattern) s -= 8;
            s += (cd.appeal || 3) * 1.5;
            s += stSizeFit(it.fb, o.size, true);      // MSR-FIX-A: a size word prefers right-sized bases
            out.push({ key: r.key, s: s, it: it, cd: cd });
        });
        out.sort(function (x, y) { return y.s - x.s; });
        return out;
    }
    var ST_MONO = /\b(?:black (?:and|&|n) white|b ?& ?w|gr[ae]y(?:scale)?|monochrome|mono|silver|charcoal|gunmetal|colou?rless)\b/;
    function stDomHsl(cs) { var x = 0, y = 0, w = 0, sl = 0, ss = 0; (cs || []).slice(0, 6).forEach(function (h) { var q = stHsl(h); if (!q) return; var wt = Math.max(q.s, 1) * (1 - Math.abs(q.l - 50) / 60); if (wt <= 0) wt = 0.1; x += Math.cos(q.h * Math.PI / 180) * wt; y += Math.sin(q.h * Math.PI / 180) * wt; w += wt; sl += q.l * wt; ss += q.s * wt; }); if (!w) return null; var hh = Math.atan2(y, x) * 180 / Math.PI; if (hh < 0) hh += 360; return { h: hh, s: ss / w, l: sl / w }; }      // PUSH-VISIBLE: the colour the eye sees = saturation-weighted mean hue of the palette
    function stAdjust(it, p, lay) {   // the zone controls that turn the chosen item into the asked look: base colour on a takes-colour item, hue / saturation / brightness on one that brings its own
        var adj = {}, why = [], k;
        if (p.colour && !p.keep) {
            var th = stHsl(p.colour.hex);
            if (it.o !== 1) { adj.base_colour = p.colour.hex; why.push('takes the zone colour, so the base colour is set to ' + p.colour.name + ' (' + p.colour.hex + ')'); }
            else if (th && it.c && it.c[0]) {
                var ih = stHsl(it.c[0]), cn = it.cn || 'its own colour';
                if (ih) {
                    var dh = th.h - ih.h; while (dh > 180) dh -= 360; while (dh < -180) dh += 360;
                    if (th.s > 18 && ih.s >= 15 && Math.abs(dh) >= 12) { adj.hue_shift_deg = Math.round(dh); why.push('brings its own ' + cn + ' colours, so the hue slider turns them ' + p.colour.name + ' (hue ' + (dh > 0 ? '+' : '') + Math.round(dh) + ')'); }
                    if (th.s <= 18 && ST_MONO.test(((p.text || '') + ' ' + p.colour.name).toLowerCase())) { adj.saturation = -100; why.push(p.colour.name + ' was asked as black-and-white / grey, so its own colours are desaturated (saturation -100)'); } else if (th.s <= 18) { adj.saturation = -40; why.push(p.colour.name + ' is a neutral, so its own colours are toned down (saturation -40; -100 only for a black-and-white / grey ask)'); }
                    else if (th.s - ih.s > 25) { adj.saturation = stClamp(Math.round((th.s - ih.s) * 0.8), -100, 100); why.push('saturation ' + (adj.saturation > 0 ? '+' : '') + adj.saturation + ' for a cleaner ' + p.colour.name); }
                    var dl = th.l - ih.l; if (Math.abs(dl) > 15) { adj.brightness = stClamp(Math.round(dl * 1.2), -60, 80); why.push('brightness ' + (adj.brightness > 0 ? '+' : '') + adj.brightness + ' toward ' + p.colour.name); }
                }
            }
        }
        if (lay === 'base') { for (k in p.adjust) adj[k] = p.adjust[k]; if (p.adjustWhy.length) why = why.concat(p.adjustWhy); if (p.scaleBase != null && it.fb && it.fb !== 'flat') { adj.scale = p.scaleBase; why.push('its own texture at x' + p.scaleBase); } }
        return { adjust: adj, why: why };
    }
    function stPick(cands, ok) { for (var i = 0; i < cands.length; i++) { var r = ok(cands[i]); if (r === true) return { c: cands[i], i: i }; } return cands.length ? { c: cands[0], i: 0, forced: true } : null; }
    function stackPlan(text, env, o) {
        o = o || {}; var a = AT(); if (!a || !a.ready() || !W.SpbProRank || !W.SpbAICards || !W.SpbAICards.ready()) return null;
        var p = o.parsed || stackParseFix(text); if (!p) return null;
        var tg = o.target || p.target || null; if (tg && tg.readable) return null;      // numbers stay plain shine-only finishes
        var dis = o.dislikes || null; if (!dis) { try { var np = negPhrases(String(text).toLowerCase()).filter(negValid); if (np.length) dis = np; } catch (e) {} }
        var used = (o.exclude || []).slice(), alts = Math.max(0, o.alts == null ? 2 : o.alts), plans = [], notes = [];
        var sz = stSizeWant(p), baseC = p.like ? [{ key: p.like, it: a.lookup(p.like), cd: stCard(p.like), s: 999 }] : (p.base ? stBases(p, { exclude: used, avoid: dis, size: sz }) : []);
        var patC = p.pattern ? stLane(p.pattern, 'pattern', { exclude: used, avoid: dis, size: sz }) : [], specC = p.spec ? (p.spec.any ? stLane(p.spec, 'spec', { exclude: used, avoid: dis, calm: p.calm, target: tg, hex: p.colour && p.colour.hex, size: sz }).concat(stLane(p.spec, 'pattern', { exclude: used, avoid: dis, calm: p.calm, target: tg, hex: p.colour && p.colour.hex, size: sz }).map(function (x) { if (/\bpatterns?\b|\bpatterned\b/.test(p.spec.t) && !/\b(?:texture|spec|shine)\b/.test(p.spec.t)) x.s += 10; return x; })).sort(function (x, y) { return y.s - x.s; }) : stLane(p.spec, 'spec', { exclude: used, avoid: dis })) : [], spec2C = p.spec2 ? stLane(p.spec2, 'spec', { exclude: used, avoid: dis }) : [];
        if ((p.base && !baseC.length) || (p.pattern && !patC.length) || (p.spec && !specC.length)) { if (!baseC.length && !patC.length && !specC.length) return null; }
        var colL = p.colour ? stHsl(p.colour.hex).l : null;
        for (var n = 0; n <= alts; n++) {
            var why = [], layers = [];
            var bPick = baseC.length ? stPick(baseC, function (b) {
                if (used.indexOf(b.key) !== -1 && !p.like) return false;
                if (p.spec && !p.base.named && /flake|sparkl|glitter|holo|prism|pearl|iridesc|star/i.test(p.spec.t) && (b.it.shine === 'matte' || b.it.shine === 'semi-matte')) return false;      // P1 sparkle needs a clearcoat that is not dead matte (unless matte was asked)
                return true; }) : null;
            var b = bPick ? bPick.c : null, bL = b ? (b.it.o === 1 ? (b.it.L != null ? b.it.L : 50) : (colL != null ? colL : (b.it.L != null ? b.it.L : 50))) : null;
            if (b && p.spec && p.base && p.base.named && /flake|sparkl|glitter|holo|prism|pearl|iridesc|star/i.test(p.spec.t) && (b.it.shine === 'matte' || b.it.shine === 'semi-matte') && n === 0) notes.push('On a matte base a flake only reads at an angle, in direct light: exactly the "only in the sun" look, never a glitter bomb.');
            var pPick = patC.length ? stPick(patC, function (x) {
                if (used.indexOf(x.key) !== -1) return false; var cd = stCard(x.key), av = (cd.avoid || []).join(' ').toLowerCase();
                if (bL != null && bL < 28 && /dark (?:base|background|colou?r)|on dark|vanish on dark|lost on dark/.test(av)) return false;      // P3 contrast vs base lightness
                if (bL != null && bL > 72 && /light (?:base|background|colou?r)|on light|lost on light|on white|pale base/.test(av)) return false;
                if (b && (b.cd.busy || 3) + (cd.busy || 3) > 7) return false;      // P4 two busy layers fight
                if (p.calm && (cd.loud || 3) > 2) return false;      // P5 loudness budget
                return true; }) : null;
            var sPick = specC.length ? stPick(specC, function (x) {
                if (used.indexOf(x.key) !== -1) return false; var cd = stCard(x.key), av = (cd.avoid || []).join(' ').toLowerCase(), sc = b ? shineClass(b.it) : null;
                if (sc === 'flat' && !(p.base && p.base.named) && /\bmatte\b/.test(av)) return false;      // P2 the texture's own "avoid" vs the base shine
                if (sc === 'glossy' && /\b(?:high )?gloss(?:y)? (?:base|bases|paint)\b/.test(av)) return false;
                if (b && b.it.shine === 'mirror' && /chrome|mirror/.test(av)) return false;
                if (p.calm && (cd.loud || 3) > 2) return false;
                if (pPick && pPick.c.key === x.key) return false;
                return true; }) : null;
            var s2Pick = spec2C.length ? stPick(spec2C, function (x) { return used.indexOf(x.key) === -1 && !(sPick && sPick.c.key === x.key) && !(p.calm && (stCard(x.key).loud || 3) > 2); }) : null;
            if (b) { var ad = stAdjust(b.it, p, 'base'), bcd = b.cd, sh = shineWord(b.it); layers.push({ layer: 'base', key: b.key, name: b.it.n, adjust: ad.adjust, scale: ad.adjust.scale != null ? ad.adjust.scale : 1, intensity: 100,
                why: firstSentence(bcd.look || b.it.d || '', 96) + (sh ? ' (' + sh + ')' : '') + (ad.why.length ? '; ' + ad.why.join('; ') : '') + (p.top ? '; ' + p.top + ' top as asked' : '') }); used.push(b.key); }
            [['pattern', pPick, p.pattern], ['spec', sPick, p.spec], ['spec', s2Pick, p.spec2]].forEach(function (L) {
                if (!L[1]) return; var x = L[1].c, it = a.lookup(x.key); if (it && it._type === 'pattern' && L[0] === 'spec') { if (layers.some(function (q) { return q.layer === 'pattern'; })) return; L = ['pattern', L[1], L[2]]; }      // B2p5: an any-texture pick that is a paint pattern
                var cd = stCard(x.key), dsc = L[0] === 'pattern' ? stFineScale(cd) : 1, szw = '', sc0 = L[2].abs != null ? L[2].abs : (L[2].rel ? stClamp(Math.max(Math.round(dsc * L[2].rel[0] * 100) / 100, L[2].rel[0] > 1 ? 1.1 : 0), 0.05, 5) : (L[2].scale != null ? L[2].scale : (p.scaleBase != null && !b ? p.scaleBase : dsc))), op0 = L[2].intensity != null ? L[2].intensity : (p.calm ? 40 : (L[0] === 'pattern' ? 65 : 70)); /* PUSH-VISIBLE 2026-10-03: a named pattern is the wish's main word -> 65% (40% read invisible in-app, MSR_VERIFY mode 2); 40 only for subtle/calm asks */ /* B2p11: a named colour leads, the pattern's own colours ride at 40% */
                if (L[2].abs != null) szw = 'size x' + sc0 + ' as asked'; else if (L[2].rel) szw = '"' + L[2].rel[1] + '" = x' + sc0 + ' (' + L[2].rel[0] + ' of its normal x' + dsc + ')';      // PUSH2: the reply says what the size word did
                var ex = []; if (L[1].forced && n === 0) ex.push('closest match in the catalogue');
                if (!x.canon && L[2].cs && L[2].cs.length && n === 0) { var nm = L[2].cs.map(function (c) { return c[0]; }).join(' / '); if (!(a._data().items || []).some(function (q) { return q._type === L[0] && L[2].cs[0][2].test(q.n || ''); })) notes.push('There is no ' + nm + ' ' + (L[0] === 'spec' ? 'shine texture' : 'pattern') + ' in the catalogue; ' + it.n + ' is the closest.'); }
                var pr = (cd.pair || []).slice(0, 2).join(', ');
                layers.push({ layer: L[0], key: x.key, name: it.n, scale: sc0, intensity: op0, adjust: { scale: sc0, intensity: op0 }, sizeWhy: szw || undefined,
                    why: (L[0] === 'spec' ? 'shine texture (colours stay): ' : 'paint pattern on top: ') + firstSentence(cd.look || it.d || '', 90) + ' — x' + sc0 + ' size, ' + op0 + '% strength' + (pr ? '; pairs with ' + pr : '') + (ex.length ? ' (' + ex.join('; ') + ')' : '') });
                used.push(x.key);
            });
            if (!layers.length) break;
            plans.push(layers);
            if (n === 0 && pPick && pPick.i > 0) notes.push('Skipped ' + a.lookup(patC[0].key).n + ': it would ' + (p.calm ? 'be louder than the subtle look you asked for' : 'clash with or vanish on that base') + '.');
            if (n === 0 && sPick && sPick.i > 0 && specC[0] && specC[0].key !== (pPick && pPick.c.key)) notes.push('Skipped ' + a.lookup(specC[0].key).n + ': its maker notes say it does not suit a ' + (b ? (shineClass(b.it) === 'flat' ? 'matte' : shineClass(b.it)) : '') + ' base.');
            if (n === 0 && bPick && bPick.i > 0 && p.spec && !p.like) notes.push('A dead-matte clear would hide the sparkle, so the base is a ' + shineClass(b.it) + ' one.');
            if (p.like) { baseC = baseC.slice(); }      // like X: the base stays X in every alternative
        }
        // MSR-FIX-A: "like Ghost Camo but in hot pink": one more stack = a base in the asked colour + the original's own pattern concept (the sliders cannot repaint a multi-colour look cleanly; K_app_controls)
        if (p.like && p.colour && !p.pattern && !p.spec) { try { plans = plans.filter(function (ls, i) { return i === 0 || !(ls.length === 1 && ls[0].key === p.like); });
            var lit = a.lookup(p.like), lc = lit ? ST_C.filter(function (c) { return c[3].indexOf('p') !== -1 && c[2].test(lit.n || ''); })[0] : null;
            if (lc) { var pb = { colour: p.colour, keep: false, top: p.top, calm: p.calm, adjust: {}, adjustWhy: [], scaleBase: null, pattern: { t: lc[0], cs: [lc] }, base: { t: p.colour.name, concept: null, look: false, shine: p.base ? p.base.shine : null, named: false } };
                var bc2 = stBases(pb, { exclude: used, avoid: dis }).filter(function (x) { return used.indexOf(x.key) === -1; })[0], pc2 = stLane(pb.pattern, 'pattern', { exclude: used, avoid: dis }).filter(function (x) { return used.indexOf(x.key) === -1; })[0];
                if (bc2 && pc2) { var ad2 = stAdjust(bc2.it, pb, 'base'), pit = a.lookup(pc2.key), pcd = stCard(pc2.key);
                    plans.push([{ layer: 'base', key: bc2.key, name: bc2.it.n, adjust: ad2.adjust, scale: 1, intensity: 100, why: firstSentence(bc2.cd.look || bc2.it.d || '', 96) + (ad2.why.length ? '; ' + ad2.why.join('; ') : '') + '; ' + p.colour.name + ' as the base' },
                        { layer: 'pattern', key: pc2.key, name: pit.n, scale: stFineScale(pcd), intensity: 65, adjust: { scale: stFineScale(pcd), intensity: 65 }, why: 'paint pattern on top: ' + firstSentence(pcd.look || pit.d || '', 90) + ' — the ' + lc[0] + ' of ' + lit.n + ' over a ' + p.colour.name + ' base, x' + stFineScale(pcd) + ' size, 65% strength' }]);
                    used.push(bc2.key, pc2.key); notes.push('Or build it: a ' + p.colour.name + ' base with a ' + lc[0] + ' pattern on top, since ' + lit.n + ' brings its own colours.'); } }
        } catch (elk) {} }
        if (!plans.length) return null;
        var part = tg && !tg.all ? [tg.id].concat(tg.parts || []).filter(function (x, i, all) { return all.indexOf(x) === i; }) : null, lparts = null;
        if (tg && !tg.all && !tg.selected && !tg.zones && plans[0].some(function (l) { return l.layer !== 'base'; }) && plans[0].some(function (l) { return l.layer === 'base'; })) {      // PUSH2: explicit whole-car base + part layer, or a stack scoped to named parts
            var tx = String(p.t || '').toLowerCase(), hit = TARGETS.filter(function (x) { return !x.all && !x.selected && x.re.test(tx); }), pp = [], el = null, ids = [];
            hit.forEach(function (x) { if (x.parts && !(x.id === 'lower band')) x.parts.forEach(function (q) { if (pp.indexOf(q) === -1) pp.push(q); }); else if (x.element && x.id !== 'numbers') el = x.element; else return; ids.push(x.id); });
            if (pp.length || el) { var baseText = String((p.base && p.base.t) || '').toLowerCase(), baseNamesPart = tg.re && tg.re.test(baseText), explicitWhole = /\b(?:body|whole\s+car|entire\s+car|full\s+(?:car|vehicle)|entire\s+vehicle|all\s+body\s+panels?|every\s+(?:body\s+)?panel|all\s+over|overall|all|whole|entire|main\s+(?:colou?r|paint)|the\s+car|my\s+car|this\s+car|scheme|livery|paint\s+job|\w+\s+car)\b/.test(baseText), exclusivePart = /\b(?:only|just|exclusively)\b/.test(tx), wholeBase = explicitWhole || (tg.id !== 'sides' && !exclusivePart && !baseNamesPart && (p.clauses || []).length > 1); lparts = { parts: pp, element: el, ids: ids, wholeBody: wholeBase, label: hit.filter(function (x) { return ids.indexOf(x.id) !== -1; }).map(function (x) { return x.label; }).join(' and ') }; part = ids.concat(pp); }
        }
        return { layers: plans[0], alts: plans.slice(1), notes: notes, part: part, lparts: lparts, target: tg, parsed: p, colour: p.colour, adjustOnly: p.adjustOnly };
    }
    var ST_ROLE = { base: 'Base', pattern: 'Pattern', spec: 'Shine' };
    function stackCards(layers, plan, colour) {      // kit items: the BASE card carries the whole stack (one zone, one Undo); the layer cards are shown and plan nothing themselves
        var lp = plan.lparts, tg = lp ? (lp.wholeBody ? BODY : { id: 'stack_scope', label: lp.label, region: lp.parts.length ? { part: lp.parts.length === 1 ? lp.parts[0] : lp.parts.slice() } : { element: lp.element } }) : plan.target, tgt = tg && !tg.all ? afTgt(tg) : (tg && tg.notFams ? afTgt(tg) : { id: 'body', label: 'the body' }), base = null, items = [];      // PUSH2-SCOPE: explicit body base + part layer, or one combined part-only zone
        layers.forEach(function (l) { var c = card(l.key, l.why, colour); if (!c) return; c.why = l.why; c.layer = l.layer; c.layerScale = l.scale; c.layerOpacity = l.intensity; c.target = tgt; if (l.layer === 'base') { base = c; c.adjust = l.adjust; } items.push({ role: ST_ROLE[l.layer] + (l.layer !== 'base' ? ' (x' + l.scale + ', ' + l.intensity + '%)' : ''), target: tgt, card: c }); });
        if (base) { var sw = { pattern: null, spec: [], adjust: base.adjust || {} }; layers.forEach(function (l) { var id = l.key.replace(/^[a-z]+::/, ''); if (l.layer === 'pattern') sw.pattern = { id: id, opacity: l.intensity, scale: l.scale }; if (l.layer === 'spec') sw.spec.push({ id: id, opacity: l.intensity, scale: l.scale }); });
            if (plan.lparts && plan.lparts.wholeBody) sw.lparts = plan.lparts;      // PUSH2-SCOPE: only an explicit body base is split from its part layer
            base.stackWith = sw; items.forEach(function (x) { if (x.card !== base) x.card.stackPart = true; }); }
        return items;
    }
    function stackAnswer(it0, env, o) { var r = stackAnswerCore(it0, env, o); try { afKitNotes(r, env || {}, it0); } catch (eaf) {} return r; }      // ADVISOR-FIX (2): where each kit lands + repaint warnings
    function stackAnswerCore(it0, env, o) {
        o = o || {}; var p = it0.stack && it0.stack.text ? it0.stack : null, txt = p ? p.text : it0.text;
        var plan = stackPlan(txt, env, { parsed: p, target: it0.target, dislikes: it0.dislikes, exclude: o.exclude, alts: 2 }); if (!plan) return null;
        var cx = ctxOf(plan.target || BODY, env), colour = plan.colour ? plan.colour.hex : swatchHex(null, cx, null), where = plan.lparts ? (plan.lparts.wholeBody ? 'the body + ' : '') + plan.lparts.label : (plan.target && !plan.target.all ? plan.target.label : 'the body');      // PUSH2-SCOPE
        var all = [plan.layers].concat(plan.alts), names = ['Stack', 'Alt stack 1', 'Alt stack 2'], kits = [], cards = [], seen = {}, shown = (o.exclude || []).slice();
        all.forEach(function (ls, i) { var items = stackCards(ls, plan, colour); if (!items.length) return; kits.push({ name: names[i] || ('Alt stack ' + i), blurb: i === 0 ? 'Your look as ' + ls.length + ' layer' + (ls.length > 1 ? 's' : '') + (plan.lparts && plan.lparts.wholeBody ? '' : ' in one zone') + ' on ' + where + '.' : 'Another way to build it.', items: items });
            items.forEach(function (x) { if (!seen[x.card.key]) { seen[x.card.key] = 1; var c = JSON.parse(JSON.stringify(x.card)); c.noUse = true; cards.push(c); shown.push(x.card.key); } }); });
        var L0 = plan.layers, text = (plan.adjustOnly ? 'That look, tuned with the zone sliders' : 'A layered look: ' + L0.length + ' layer' + (L0.length > 1 ? 's' : '') + (plan.lparts && plan.lparts.wholeBody ? '' : ' in one zone')) + ' on ' + where + ':';
        L0.forEach(function (l) { var ad = l.adjust || {}, ak = []; if (l.layer === 'base') { if (ad.base_colour) ak.push('base colour ' + ad.base_colour); if (ad.hue_shift_deg != null) ak.push('hue ' + (ad.hue_shift_deg > 0 ? '+' : '') + ad.hue_shift_deg); if (ad.saturation != null) ak.push('saturation ' + ad.saturation); if (ad.brightness != null) ak.push('brightness ' + ad.brightness); if (ad.spec_strength != null) ak.push('spec strength ' + ad.spec_strength + '%'); if (ad.scale != null) ak.push('scale x' + ad.scale); }
            text += '\n- **' + ST_ROLE[l.layer] + '**: ' + l.name + (ak.length ? ' [' + ak.join(', ') + ']' : '') + ' — ' + l.why; });
        L0.forEach(function (l) { if (l.sizeWhy) text += '\nSize: ' + l.name + ' at ' + l.sizeWhy + '.'; });      // PUSH2
        if (plan.lparts && plan.lparts.wholeBody) text += '\nPlacement: the base covers the whole car; the ' + L0.filter(function (l) { return l.layer !== 'base'; }).map(function (l) { return l.name; }).join(' + ') + ' layer goes only on ' + plan.lparts.label + '.';      // PUSH2-SCOPE
        if (plan.notes.length) text += '\nWhy this pairing: ' + plan.notes.join(' ');
        if (L0.some(function (l) { return l.layer === 'spec'; }) && !L0.some(function (l) { return l.layer === 'pattern'; })) text += '\nShine textures do not show in the flat preview - check the 3D view.';      // PUSH-VISIBLE: spec-only layers are invisible in the flat preview
        if (plan.alts.length) text += '\n' + plan.alts.length + ' alternative stack' + (plan.alts.length > 1 ? 's' : '') + ' below. **Use this kit** puts every layer on ' + where + ' in one step (one Undo); nothing changes until you press it.';
        return { text: text, cards: cards, kits: kits, target: plan.target && !plan.target.all ? afTgt(plan.target) : { id: 'body', label: 'the body' }, useLabel: where, colour: colour, shown: shown, kind: 'stack', stack: { layers: L0.map(function (l) { return { layer: l.layer, key: l.key, name: l.name, scale: l.scale, intensity: l.intensity, adjust: l.adjust }; }) }, next: ['Show me more', 'Something calmer', 'Review my finishes'] };
    }
    // the claim: a stack wish / question / description (never a scheme order, a support question or an imperative order: those stay with the designer and the support helper)
    function stackClaim(raw, t0, it, dis) {
        if (it && it.kind === 'like') { var pl0 = stackParse(raw); if (!(pl0 && pl0.like && (pl0.pattern || pl0.spec))) return null; it.kind = 'recommend'; }      // B2p2: like X but with a carbon weave = X + a layer
        if (it && !(it.kind === 'recommend' || it.kind === 'find')) return null;
        if (it && (it.act || it.tryMode || it.howto || it.pairsColour || it.sup || it.avoid || it.mod || it.multi || (it.target && it.target.readable))) return null;
        var tApp = t0.replace(/\b(?:(?:spec|pattern|shine|texture|paint|colou?r|base|top|clear) )?layers?\b|\blayered\b/g, ' '); ST_C.forEach(function (c) { tApp = tApp.replace(new RegExp(c[1].source, 'g'), ' '); });      // B2p7: "a sparkle spec layer" is a layer of the LOOK, not an app layer      // B2p3: layer words never count as app words ("dragon" is not "drag")
        if (!it && (ST_ORDER.test(t0) || ST_SCHEME.test(t0) || SUPPORT_RE.test(tApp) || APP_STRICT.test(tApp) || /\?\s*$/.test(t0) && /\b(?:why|how do|how can|where)\b/.test(t0))) return null;
        if (it && ST_SCHEME.test(t0) && !/\bfinish|look\b/.test(t0)) return null;
        if (!it) {      // B2p4: never claim a comparison, an edit order (DESIGN_ORDER_RE), a sequenced coat order ("pearl white base then pink pearl over it") or chatter the intent model calls none / support
            if (/\b(?:compare|compared|versus|vs\.?|difference|differences|or)\b/.test(t0) || /\bthen\b/.test(t0) || DESIGN_ORDER_RE.test(t0) || /^\s*(?:duplicate|copy|move|extend|mirror|rotate|flip|shrink|resize|widen|narrow|enlarge|reduce)\b/.test(t0)) return null;
            try { var pr0 = W.SpbIntent && W.SpbIntent.ready && W.SpbIntent.ready() ? W.SpbIntent.predict(raw) : null; if (pr0 && (pr0.label === 'none' || pr0.label === 'support') && pr0.p >= 0.8) return null; } catch (epr) {}
        }
        var p = stackParseFix(raw); if (!p) return null; if (p.target && p.target.readable) return null;
        var DSN = W.SpbProDesign, askQ = /\?|\b(?:what|which|how|should|could|would|suggest\w*|recommend\w*|ideas?|options?|thinking|looking for|any good|help me)\b/.test(t0);      // B2p9: compound DESIGN orders belong to the designer (WP C)
        var animalL = [p.pattern, p.spec].some(function (L) { return L && (L.cs || []).some(function (c) { return /^(?:tiger|zebra|leopard|snake|giraffe|scales|butterfly)$/.test(c[0]); }); });      // MSR-FIX-A: animal marks are a pattern, not stripe zones
        if (DSN && typeof DSN.compoundPlan === 'function' && !askQ && !p.like && !p.adjustOnly && !(p.base && p.base.concept) && !animalL) { var cpx = null; try { cpx = DSN.compoundPlan(raw); } catch (ecp) {} if (cpx) return null; }
        var out = it ? it : { kind: 'recommend', target: p.target, colour: p.colour, goal: null, goals: {}, text: raw, count: 0, not: notOf(t0) };
        out.stack = p; if (dis && dis.length) out.dislikes = dis; if (!out.target && p.target) out.target = p.target;
        return out;
    }
    function stackTool(a, env, tg, dis, exclude) {      // suggest_finishes: the same plan for every AI tier
        var plan = stackPlan(String(a.ask || ''), env, { target: tg, dislikes: dis, exclude: exclude, alts: 2 }); if (!plan) return null;
        var cx = ctxOf(plan.target || BODY, env), colour = plan.colour ? plan.colour.hex : swatchHex(null, cx, null), C = W.SpbAICards;
        function apply(ls) { var items = stackCards(ls, plan, colour), base = null, steps = []; items.forEach(function (x) { if (x.card.layer === 'base') base = x; }); (base ? [base] : items).forEach(function (x) { var pl = applyPlan(x.card, x.target, env); if (pl && pl.steps) pl.steps.forEach(function (s) { steps.push({ tool: s.tool, args: s.args }); }); }); return steps; }
        function out(ls) { return ls.map(function (l) { return { layer: l.layer, key: l.key, name: l.name, why: l.why, scale: l.scale, intensity: l.intensity, adjust: l.adjust }; }); }
        var rows = [], seen = {}; [plan.layers].concat(plan.alts).forEach(function (ls, i) { ls.forEach(function (l) { if (seen[l.key]) return; seen[l.key] = 1; var cd = (C && C.card(l.key)) || {}; rows.push({ key: l.key, name: l.name, lane: 'stack-' + l.layer, look: cd.look, why: l.why, loud: cd.loud, busy: cd.busy, mood: cd.mood, pair: cd.pair, avoid: cd.avoid, stack: i, apply: i === 0 ? 'part of stack 0: call the stack "apply" steps' : 'part of alternative stack ' + i }); }); });
        return { part: plan.lparts ? (plan.lparts.wholeBody ? 'the body + ' : '') + plan.lparts.label : (plan.target ? plan.target.label : 'the car'), stack: out(plan.layers), alternatives: plan.alts.map(out), apply: apply(plan.layers), pairing_notes: plan.notes.length ? plan.notes : undefined, rows: rows,
            note: 'The ask is a LAYERED look: stack = base + paint pattern + shine texture for the requested areas, each with adjust = the zone controls to set (base_colour = zone colour for items that take the zone colour; hue_shift_deg / saturation / brightness for items that bring their own colours; scale; intensity = layer opacity %). "apply" holds the exact add_zone / edit_zone calls for the scope shown in part. alternatives = 2 more stacks. Pass stack:false for plain single-finish rows.' };
    }
    // the situation-aware ranking as a TOOL result: same engine as the advisor, for any AI (in-app DeepSeek / OpenAI, Claude or Codex over MCP)
    var CAP_RE = /\b(?:animated|animation|moving|motion|flicker\w*|pulsing|pulses|invisible (?:by|in) (?:the )?day|uv[- ]?(?:reactive|active|only)|black ?light|glows? (?:in the dark|at night|by itself)|light[- ]?up|emissive|self[- ]?illuminated)\b/i;
    var CAP_NOTE = 'iRacing paint is static: nothing animates, flickers, glows by itself or turns invisible in daylight. These finishes can only LOOK the part in a still render (bright, saturated or reflective); tell the buyer so.';
    function suggestTool(a, env) {
        a = a || {}; var C = W.SpbAICards, R = W.SpbProRank; if (!R || !C || !C.ready()) return { error: 'the finish cards are still loading; use find_finishes for now' };
        var part = String(a.part || '').toLowerCase(), tg = part ? targetOf(part) : null; if (!tg && /body|car|whole|everything/.test(part)) tg = BODY;
        // a client that passes only the painter's words ("ask") still gets the part / colour / goal the words name (what the in-app pipeline reads from the sentence)
        var askL = String(a.ask || '').toLowerCase(), askP = askL; try { askP = stripNegWhere(askL, negTraitBody); } catch (eap) {}
        if (!tg && !part && askL) { try { tg = targetOf(askL) || null; } catch (etg) {} }
        var cx = ctxOf(tg, env || {}), col = a.colour ? colourOf(String(a.colour)) : (askL && !a.like ? colourOf(askP) : null), colour = swatchHex(null, cx, col);
        var nv = a.novelty; if (typeof nv === 'string') nv = { safe: 0, balanced: 1, wild: 2 }[nv.toLowerCase()]; if (nv == null || isNaN(nv)) nv = 1;
        var goal = /^(pop|premium|shimmer|deep|retro|stealth|readable|metalbright|subtle)$/.test(String(a.goal || '')) ? a.goal : null;
        if (!goal && !a.goal && askL && !a.like) { try { var gk1 = goalKey(goalOf(askP)); if (/^(pop|premium|shimmer|deep|retro|stealth|readable|metalbright|subtle)$/.test(gk1 || '')) goal = gk1; } catch (egk) {} }
        var lo = (Array.isArray(a.leave_out) ? a.leave_out : String(a.leave_out || '').split(/[,;]+/)).map(function (x) { return String(x).trim().toLowerCase(); }).filter(Boolean), dis = unionList(lo, negPhrases(String(a.ask || '')).filter(negValid));
        var it0 = { kind: 'recommend', target: tg, colour: col, goal: goal, text: String(a.ask || '') + ' ' + (goal || ''), mod: null, dislikes: dis.length ? dis : null };
        var kind = goal || (tg && tg.readable ? 'readable' : (!tg || tg.all || !tg.thin ? 'general' : 'thin'));
        var ctx = rankCtx(it0, cx, kind); ctx.novelty = nv; if (nv >= 2) ctx.classic = false; ctx.exclude = (Array.isArray(a.exclude) ? a.exclude : (a.exclude ? String(a.exclude).split(/[\s,]+/) : [])).slice(); var lim = Math.max(1, Math.min(10, a.limit || 6)), lane = a.lane && a.lane !== 'all' ? a.lane : null;
        if (tg && tg.readable && lane && lane !== 'keep') lane = 'keep';      // numbers / names stay plain shine-only finishes whatever lane was asked for
        if (!a.like && KEEP_RE.test(askL)) ctx.specOnly = true;      // L7: textures that only change the shine (no paint pattern) when the ask keeps the paint
        var plan = lane ? [[lane, lim]] : (tg && tg.readable ? [['keep', 4]] : (tg && tg.thin ? [['keep', 3], ['texture', 2], ['complete', 1]] : [['keep', 2], ['complete', 3], ['texture', 2]]));
        if (!lane && !a.like && KEEP_RE.test(askL)) plan = [['keep', Math.max(1, lim - 2)], ['texture', Math.min(2, lim)]];      // L7: the paint stays: no replacement-palette (complete) rows
        // R07 (Codex L6): the default lane counts (2 + 3 + 2) overshot a small limit: shrink the plan from the last lane up until it fits
        if (!lane) { var tot0 = 0; plan.forEach(function (pp) { tot0 += pp[1]; }); for (var pi = plan.length - 1; pi >= 0 && tot0 > lim; pi--) { var cut0 = Math.min(plan[pi][1], tot0 - lim); plan[pi][1] -= cut0; tot0 -= cut0; } plan = plan.filter(function (pp) { return pp[1] > 0; }); }
        var rows = [], used = ctx.exclude.slice();
        function rowOut(r) {
            var it = AT().lookup(r.key), how;
            if (r.lane === 'texture') how = it._type === 'spec' ? 'edit_zone spec_patterns: [...the zone\'s existing ids, {id: "' + r.key.replace(/^[a-z]+::/, '') + '"}] (adds a shine texture; colours unchanged)' : 'edit_zone pattern: {id: "' + r.key.replace(/^[a-z]+::/, '') + '", opacity: 70} (adds a paint pattern)';
            else if (r.lane === 'complete') how = 'edit_zone finish="' + r.key + '" color="finish" (it brings its own palette and REPLACES the zone colour)';
            else how = 'edit_zone finish="' + r.key + '" and leave color out on an existing zone (its colour stays). For a part with NO zone of its own use add_zone with the colour showing there (a solid hex), NOT "source": "source" is the original template art, not your composed scheme. Check the preview';
            var warn = (it && it.o === 0 && it.metal === 'full' && cx.hexZone && !lightNeutral(cx.hexZone) && lum(cx.hexZone) >= 0.25) ? 'full metal on a coloured part can look darker in the sim' : undefined;
            return { key: r.key, name: r.name, lane: r.lane, look: r.look, why: r.why, loud: r.loud, busy: r.busy, mood: r.mood, pair: r.pair, avoid: r.avoid, apply: how, warning: warn };
        }
        if (a.stack !== false && !a.like && !lane && String(a.ask || '').trim()) { var stk0 = null; try { stk0 = stackTool(a, env || {}, tg, it0.dislikes, ctx.exclude); } catch (estk) {} if (stk0) return stk0; }      // B2: a layered ask -> stack + alternatives + the one-zone apply calls
        if (a.like) {          // "like this finish but calmer / darker / glossier / with more sparkle": the nearest cards to ONE finish, bent by modifiers
            var lk0 = AT().lookup(String(a.like)), lk = lk0 ? lk0.k : (resolveName(String(a.like)) || (findFinishesIn(String(a.like), 1)[0] || {}).key);
            if (!lk || !AT().lookup(lk)) return { error: 'unknown finish for like: "' + a.like + '" (use find_finishes to get a key)' };
            var mods = (Array.isArray(a.mods) ? a.mods : String(a.mods || '').split(/[,;]+/)).map(function (m) { return String(m).trim().toLowerCase(); }).filter(Boolean), mk = [];
            var rejMods = [], MOD_ALIAS = { matte: 'flatter', matter: 'flatter', flat: 'flatter', dull: 'flatter', duller: 'flatter', shiny: 'glossier', shinier: 'glossier', gloss: 'glossier', glossy: 'glossier', sparkle: 'sparklier', sparkly: 'sparklier', metallic: 'metalmore', dark: 'darker', light: 'lighter', bright: 'lighter', brighter: 'lighter', calmer: 'calm', quiet: 'calm', quieter: 'calm', subtle: 'calm', bolder: 'bold', loud: 'bold', louder: 'bold', warm: 'warmer', cool: 'cooler', fine: 'finer', coarse: 'coarser', simple: 'simpler', busy: 'busier', smooth: 'smoother', vivid: 'vivid', muted: 'muted' };
            mods.forEach(function (m) { var ml = MOD_ALIAS[m] || m; if (R.MODS && R.MODS[ml]) { if (mk.indexOf(ml) === -1) mk.push(ml); } else { var mo = modOf(m); if (!mo.length) rejMods.push(m); mo.forEach(function (x) { if (mk.indexOf(x) === -1) mk.push(x); }); } });
            var lrows = R.like([lk], { mods: mk, colour: col && col.hex, lane: lane, exclude: ctx.exclude, limit: lim, offset: Math.max(0, (a.page || 0)) * lim, avoid: it0.dislikes });
            return { part: tg ? tg.label : 'the car', like: nameOf(lk), mods: mk, rejected_mods: rejMods.length ? rejMods : undefined, rows: lrows.map(rowOut), note: 'rows are the closest looks to ' + nameOf(lk) + (mk.length ? ', moved ' + mk.join(' + ') : '') + ' (shared words in why). Valid mods: ' + Object.keys(R.MODS || {}).join(', ') + '. Page with page / exclude. Describe a suggestion from its look/why fields; never invent properties.' };
        }
        // (6+ words = a described look; a short pure GOAL / mood ask ("quiet classy look for the hood": a goal, < 12 words, no descriptive word left) keeps the proven ranked choices - its lexicon expansions alone retrieve odd cards; truth set unchanged by this guard)
        // 2026-10-02 (overnight): a DESCRIBED ask ("molten orange abstract panel, loops and flowing contours, no drawn flames") leads with the best whole-sentence matches of the finishes
        // (negations removed), exactly like the in-app pipeline does; the lane plan fills the rest. Truth set (Codex L2, 400 asks) through this tool: hit 36.5% before -> see CHANGELOG.
        var askTxt = String(a.ask || '').toLowerCase().trim();
        if (!lane && !(tg && tg.readable) && askTxt.split(/\s+/).length >= 6 && !(W.__noToolSearchFirst) && !(goal && askTxt.split(/\s+/).length < 12 && meaningfulLeft(askTxt, tg).length === 0)) {
            var sq0 = askTxt; try { sq0 = stripState(stripNeg(askTxt)); } catch (esn) {}
            sq0 = stripPart(sq0, tg);
            if (tg && tg.re && !tg.all && sq0.split(' ').length <= 7) { var sq0b = sq0.replace(new RegExp(tg.re.source, 'g'), ' ').replace(/\s+/g, ' ').trim(); if (sq0b.split(' ').length >= 2) sq0 = sq0b; }
            var keepC = KEEP_RE.test(askTxt), nlead = Math.max(1, Math.min(lim - 1, Math.round(lim * 0.67)));
            try {
                R.search(sq0, { limit: nlead, types: ['base', 'monolithic'], own: keepC ? 'takes' : undefined, exclude: used.slice(), avoid: it0.dislikes }).forEach(function (row) {
                    var ri = row.key ? AT().lookup(row.key) : null, cd0 = row.key ? (C.card(row.key) || {}) : null; if (!ri || !cd0) return;
                    var r0 = { key: row.key, name: ri.n, lane: ri.o === 1 ? 'complete' : 'keep', look: cd0.look, why: row.why, loud: cd0.loud, busy: cd0.busy, mood: cd0.mood, pair: cd0.pair, avoid: cd0.avoid };
                    rows.push(rowOut(r0)); used.push(row.key);
                });
            } catch (esr) {}
            var skipN = rows.length; plan = plan.map(function (p) { var n = Math.max(0, p[1] - skipN); skipN = Math.max(0, skipN - p[1]); return [p[0], n]; }).filter(function (p) { return p[1] > 0; });
        }
        plan.forEach(function (p) {
            ctx.lane = p[0]; ctx.limit = p[1]; ctx.exclude = used; ctx.offset = lane ? Math.max(0, (a.page || 0)) * lim : 0;
            R.suggest(ctx).rows.forEach(function (r) { rows.push(rowOut(r)); used.push(r.key); });
        });
        if (rows.length > lim) rows = rows.slice(0, lim);
        return { part: tg ? tg.label : 'the car', capability_note: CAP_RE.test(askL) ? CAP_NOTE : undefined, rows: rows, note: 'lanes: keep = shine-only finishes that keep the paint colours; complete = complete looks ranked by palette harmony with the scheme; texture = spec / paint patterns to layer on. Page through with exclude (keys already shown) or lane + page. Describe a suggestion from its look/why fields; never invent properties.' };
    }
    // ================================================================== ADVISOR-FIX (2026-10-04, worker ADVISOR-FIX; docs/handoff_reports/ADVISOR_FIX.md)
    // Owner, 8-zone ARCA design (output/job_render_1791086800_*): "Suggest a really cool spec to apply over the pink now" got a WHOLE-BODY stack
    // (new base Pink Rose Spiral + hue sliders + a shine), and "Use" on its Alt stack 2 kit repainted "White Base 75% Chrome" (an everything-zone
    // restricted to the White Base layer) pink. Pink Rose Spiral's swatch was a broken image. Three fixes:
    // (1) SPEC-OVER-TARGET lane: "a spec / shine texture over <the pink | the numbers | a layer | a part | a zone>", "make the pink sparkle" = 3-5 SPEC
    //     PATTERNS ranked by the deep cards' stack.on_matte / on_metallic / on_chrome fit for those zones' finishes; Use adds the pattern to EXACTLY those
    //     zones (finish, colour, pattern and their spec layers kept; one Undo). "The pink" = the zones painting pink (COPILOT-FIX resolver SpbProEdit.compile).
    // (2) KIT TARGET: "the body" is never a layer-scoped everything-zone the user did not name; it is ONE zone (largest visible coverage). A stack asked
    //     for "the pink" / "on them" (after a targeted ask) lands on those zones only; every kit says where it lands; the whole-body version is a
    //     separate answer whose cards warn which zones of other colours it repaints. applyPlan returns changed / changedText (zone names + share).
    // (3) THUMBNAIL FALLBACK: a card / kit thumbnail that fails falls back to the picker's split swatch (/api/swatch/<type>/<id>?...&mode=split), then to a
    //     colour chip from the item's palette (data: URI): no broken-image icons.
    var AF_SPEC_W = /\bspecs?\b|\bspec(?:ular)? (?:patterns?|maps?|layers?|textures?)\b|\bspecular\b|\bshine (?:textures?|patterns?|layers?|effects?|overlays?)\b|\bsheen\b/;
    var AF_SPEC_STRICT = /\bspecs?\b|\bspec(?:ular)? (?:patterns?|maps?|layers?|textures?)\b|\bspecular\b/;
    var AF_TEX_W = /\b(?:textures?|finish(?:es)?|shine|sparkle|sparkly|flakes?|glitter|shimmer|effects?)\b/;
    var AF_LAYER_PREP = /\b(?:over|on top of|onto|overtop)\s+(?:all\s+(?:of\s+)?)?(?:the|my|those|these|that)\b/;
    var AF_MAKE = /\bmake (?:the |my |all (?:of )?the |those |these )([a-z#0-9' ()-]{2,48}?) (sparkle|sparkly|shimmer|shimmery|glitter|glittery|glint|flash|shine|shinier)\b/;
    var AF_NOT_TARGET = /^(?:top|it|base|base coat|basecoat|clear|clearcoat|clear coat|top coat|paint|colou?r|light|sun|sunlight|angle|edges?|whole thing|rest|same|other|one|ones|look|finish|spec|win|day|night|track)$/;
    var AF_CONCEPT = [[/\b(?:sparkl\w*|glitter\w*|flakes?|flaky|glint\w*|twinkl\w*|stardust)\b/, 'sparkle flake glitter'], [/\b(?:shimmer\w*|pearl\w*|nacre|mica|opal\w*)\b/, 'pearl shimmer'], [/\bbrush(?:ed)?\b|\bgrain\b/, 'brushed grain'],
        [/\b(?:holo\w*|rainbow|prism\w*|iridesc\w*|diffraction|oil slick)\b/, 'holographic prism'], [/\bhammer\w*|\bpeen\w*|\bdimpl\w*/, 'hammered'], [/\bfrost\w*|\bsandblast\w*|\betched\b/, 'frost etched'], [/\bcarbon\b|\bweave\b|\bkevlar\b/, 'carbon weave'],
        [/\bwet\b|\bdroplets?\b|\brain\b|\bwater\b/, 'wet droplets'], [/\b(?:camo|camouflage)\b/, 'camo'], [/\bhex\w*|\bhoneycomb\b/, 'hex honeycomb'], [/\b(?:scales?|snake|reptile|dragon)\b/, 'scales'], [/\b(?:lightning|veins?|cracks?|crackle)\b/, 'lightning veins crackle'], [/\bwaves?\b|\bripples?\b/, 'waves ripple'], [/\bstars?\b|\bgalaxy\b|\bcosmic\b/, 'stars galaxy']];
    function afLayerScoped(z) { return /\bonly on layers?:/i.test(String((z && z.covers) || '')); }
    function afLayersOf(z) { var m = /only on layers?:\s*([^;]+)/i.exec(String((z && z.covers) || '')); return m ? m[1].split(/\s*,\s*/).map(function (s) { return s.trim(); }).filter(Boolean) : []; }
    function afShare(z) {      // visible share of the car (%): env-provided, else the app's footprint (memoised in SpbProZone)
        if (!z) return null; if (z.share != null) return Number(z.share); if (z.visible_pct != null) return Number(z.visible_pct);
        try { var Zk = W.SpbProZone; if (Zk && Zk.footprint && z.i != null) { var fp = Zk.footprint(z.i); if (fp && fp.visible_pct != null) return Number(fp.visible_pct); } } catch (e) {}
        return null;
    }
    function afPct(v) { return v == null ? '' : (v < 1 ? 'under 1%' : Math.round(v) + '%'); }
    function afList(xs) { return xs.map(function (x) { var s = x.share_pct != null ? x.share_pct : afShare(x); return '“' + (x.zone || x.name) + '”' + (s != null && !x.isNew ? ' (' + afPct(s) + ')' : (x.isNew ? ' (a new zone)' : '')); }).join(', '); }
    function afFam(hex) { try { if (W.SpbProEdit && W.SpbProEdit.familyOf) return W.SpbProEdit.familyOf(hex); } catch (e) {} var h = stHsl(hex); if (!h) return null; if (h.l < 12) return 'black'; if (h.l > 88 && h.s < 30) return 'white'; if (h.s < 12) return 'grey'; return ['red', 'orange', 'yellow', 'green', 'green', 'teal', 'blue', 'blue', 'purple', 'pink', 'pink', 'red'][Math.floor(((h.h + 15) % 360) / 30)]; }
    function afZoneColours(env) {      // COPILOT-FIX's "colours on the car painted by zones" (ai.js editEnv().zoneColours when passed; else built from the advisor zones)
        if (env && env.zoneColours && env.zoneColours.length) return env.zoneColours;
        return ((env && env.zones) || []).filter(function (z) { return !z.muted && z.colourMode === 'solid' && /^#[0-9a-f]{6}$/i.test(String(z.colour || '')); }).map(function (z) { return { hex: String(z.colour).toLowerCase(), zone_id: String(z.id), zone: z.name, index: z.i, share_pct: afShare(z), layers: afLayersOf(z) }; });
    }
    function afColourZones(col, env) {      // "the pink" = the zones painting pink: the COPILOT-FIX resolver (SpbProEdit.compile on zone colours); a hue-family match only when edit.js is not loaded
        var zs = (env && env.zones) || [], zc = afZoneColours(env), ids = [], E = W.SpbProEdit;
        if (!zc.length || !col || !col.hex) return [];
        if (E && E.compile && E.lookById) { try { var c = E.compile({ ops: [{ target: { kind: 'colour', word: col.name, hex: col.hex }, look: E.lookById('matte') }], text: '' }, { palette: [], layers: [], zoneColours: zc }); (c.zones || []).forEach(function (q) { var ze = q._meta && q._meta.zoneEdit; if (ze && ids.indexOf(String(ze.zone_id)) === -1) ids.push(String(ze.zone_id)); }); } catch (e) {} }
        else { var f = afFam(col.hex); zc.forEach(function (q) { if (afFam(q.hex) === f && ids.indexOf(String(q.zone_id)) === -1) ids.push(String(q.zone_id)); }); }
        return zs.filter(function (z) { return !z.muted && ids.indexOf(String(z.id)) !== -1; });
    }
    function afZT(zs, label, col) { return { id: 'zones', label: label, zones: zs.map(function (z) { return String(z.id); }), names: zs.map(function (z) { return z.name; }), colourHex: col ? col.hex : null }; }
    function afTgt(tg) { if (!tg) return null; var o = { id: tg.id, label: tg.label }; ['region', 'element', 'zones', 'names', 'colourHex', 'notFams'].forEach(function (k) { if (tg[k] != null) o[k] = Array.isArray(tg[k]) ? tg[k].slice() : (typeof tg[k] === 'object' ? JSON.parse(JSON.stringify(tg[k])) : tg[k]); }); return o; }
    function afNotFams(t0) { var out = []; String(t0 || '').replace(/\b(?:not|except|but not|without|keep|leave|don'?t touch|do not touch|avoid|skip)\s+(?:on\s+)?(?:the\s+|my\s+|any\s+)?([a-z]+(?:\s+[a-z]+)?)/g, function (m0, w) { var c = colourOf(w); if (c) { var f = afFam(c.hex); if (f && out.indexOf(f) === -1) out.push(f); } return m0; }); return out; }
    function afHit(tg, zs, target) {      // the zones a Use edits; "the body" = ONE zone: the largest visible coverage (colours the user excluded skipped), else the named body zone over the catch-all
        var hit = zonesFor(tg, zs);
        if (!tg.all || hit.length < 2) return hit;
        var nf = (target && target.notFams) || []; if (nf.length) { var keep = hit.filter(function (z) { return !(z.colour && nf.indexOf(afFam(z.colour)) !== -1); }); if (keep.length) hit = keep; }
        var sc = hit.map(function (z) { return { z: z, s: afShare(z) }; });
        if (sc.some(function (x) { return x.s != null; })) { sc.sort(function (a, b) { return (b.s || 0) - (a.s || 0) || a.z.i - b.z.i; }); return [sc[0].z]; }
        var nc = hit.filter(function (z) { return !/not claimed by other zones/i.test(String(z.covers || '')); }); return [nc[0] || hit[0]];
    }
    function afLayerName(name) {      // a real layer of the open file named like that (PSD layers are a page global)
        var n = norm(name), L = []; try { L = (typeof _psdLayers !== 'undefined' && _psdLayers) ? _psdLayers : []; } catch (e) {}
        var hit = (L || []).filter(function (l) { var a = norm(l && l.name); return a && !l.hidden && (a === n || a.indexOf(n) !== -1 || (n.indexOf(a) !== -1 && a.length >= 4)); })[0];
        return hit ? hit.name : null;
    }
    function afTargetPhrase(t0) {      // the noun phrase after the LAST over / on / for / onto + the/my/those ("over the pink now" -> "pink")
        var re = /\b(?:over|on top of|onto|overtop|on|for|across|to)\s+(?:all\s+(?:of\s+)?)?(?:the|my|those|these|that)\s+([^,.;!?]+)/g, m, last = null;
        while ((m = re.exec(t0))) last = m[1];
        if (!last) return null;
        var ph = last.split(/\s+(?:that|which|so|to make|to give|with|and make|and give|but|because|since|please|now|too|as well|for me|right now|instead|again|if|when|so it|so they)\b/)[0];
        ph = ph.replace(/\b(?:now|please|too|again)\b/g, ' ').replace(/\s+/g, ' ').trim();
        return ph || null;
    }
    function afParseTarget(ph) {
        var p = String(ph || '').toLowerCase().replace(/[“”"]/g, '').replace(/\s+/g, ' ').trim(); if (!p || AF_NOT_TARGET.test(p)) return null;
        if (/\bzones?\s*$/.test(p)) return { kind: 'name', name: p.replace(/\s*\bzones?\s*$/, '').trim(), phrase: p };
        if (/\b(?:car )?numbers?\b|\bnumerals?\b/.test(p) && !/\blayer\b/.test(p)) return { kind: 'numbers', phrase: p };
        if (/\blayer\b/.test(p)) return { kind: 'layer', name: p.replace(/\s*\blayer\b\s*/, ' ').replace(/\s+/g, ' ').trim(), phrase: p };
        var col = colourOf(p), rest = col ? (' ' + norm(p) + ' ').replace(' ' + col.name + ' ', ' ').replace(/\b(?:the|my|all|of|parts?|areas?|bits?|sections?|zones?|paint(?:ed)?|colou?r(?:ed)?|ones?|stuff|on the car|car|bright|hot|light|dark|deep|neon)\b/g, ' ').trim() : null, tg = targetOf(p);
        if (col && !rest) return { kind: 'colour', colour: col, phrase: p };
        if (tg && !tg.all && !tg.selected) return { kind: 'part', tg: tg, phrase: p };
        if (col) return { kind: 'colour', colour: col, phrase: p };
        if (tg && tg.all) return { kind: 'body', phrase: p };
        return { kind: 'name', name: p, phrase: p };
    }
    function afSpecClaim(raw, t0, prev, dis) {      // the claim: a SHINE TEXTURE for a named target (never a stack with a base of its own, never a "what is a spec map" question)
        if (!t0 || t0.length > 240) return null;
        if (/\b(?:compare|compared|versus|vs\.?|difference)\b/.test(t0)) return null;
        if ((/\bwhat(?:'s| is| are| does)\s+(?:a |an |the )?spec(?:ular)?(?: maps?| patterns?)?\b/.test(t0) || /\bhow (?:do|does|can) (?:i|you) (?:make|edit|use|open|find|add|paint) (?:a |the )?spec/.test(t0)) && !/\b(?:suggest|recommend|cool|good|best|nice|ideas?)\b/.test(t0)) return null;
        var mk = AF_MAKE.exec(t0), specW = AF_SPEC_W.test(t0), prep = AF_LAYER_PREP.test(t0), ph = null, words = '';
        if (mk) { ph = mk[1]; words = mk[2]; }
        else { if (!(specW || (prep && AF_TEX_W.test(t0)))) return null; ph = afTargetPhrase(t0); }
        if (!ph) return null;
        var tp = afParseTarget(ph); if (!tp) return null;
        var tRest = t0.split(ph).join(' ').replace(/\b(?:(?:spec|pattern|shine|texture|paint|colou?r|base|top|clear) )?layers?\b/g, ' ');      // the target phrase itself ("the White Accent layer") is not an app word
        if (SUPPORT_RE.test(tRest) || APP_STRICT.test(tRest) || /\b(?:export\w*|filenames?|files?|save|saving|values?|steps|explain|workflow)\b/.test(tRest)) return null;      // support / export / how-to questions
        if (/^(?:what|which|show|tell me|is there)\b/.test(t0) && /\b(?:is|are|attached|applied|used|current(?:ly)?|right now|already)\b/.test(tRest) && !/\b(?:good|best|cool|nice|would|should|could|suggest|recommend|ideas?)\b/.test(t0)) return null;      // "what spec pattern is on the selected stripe right now" = inspect
        if (tp.kind === 'body' && !AF_SPEC_STRICT.test(t0)) return null;      // "finishes that won't add artwork over my scheme" is not a spec ask
        if ((tp.kind === 'part' || tp.kind === 'body') && (mk ? !AF_SPEC_STRICT.test(t0) : (!prep && !AF_SPEC_STRICT.test(t0)))) return null;      // "make the roof shimmer" stays a goal order on that part; "show me a shine texture for the stripes" stays in the texture lane      // "show me a shine texture for the stripes" stays in the texture lane
        if (tp.kind === 'name' && !specW && !mk) return null;      // "a flake over the top coat" is a layer of a look, not a zone
        try { var sp = stackParseFix(raw); if (sp && sp.base && sp.base.t) { var bt = (' ' + String(sp.base.t).toLowerCase() + ' ').split(ph).join(' '); if (tp.colour) bt = bt.replace(new RegExp('\\b' + tp.colour.name.replace(/[^a-z ]/g, '') + '\\b', 'g'), ' '); if (colourOf(bt) || ST_LOOK.test(bt)) return null; } } catch (e) {}      // "black base with a sparkle spec on the hood" has a base of its own: a stack
        var it = { kind: 'recommend', lane: 'specover', specOver: tp, target: tp.kind === 'part' ? tp.tg : (tp.kind === 'numbers' ? TARGETS[0] : null), colour: tp.colour || null, goal: null, goals: {}, text: raw, count: countOf(t0), not: notOf(t0), semantic: true, modelClaim: true, words: words };
        if (dis && dis.length) it.dislikes = dis;
        return it;
    }
    function afWideClaim(t0, prev) {      // "show these stacks on the whole body" after stacks that landed on a target
        if (!prev || prev.kind !== 'stack' || !prev.target || !prev.target.zones) return null;
        if (!/\b(?:whole|entire|full) (?:body|car)\b|\ball over\b|\beverywhere\b|\bthe body\b/.test(t0) || !/\b(?:show|use|put|apply|try|stacks?|kits?|these|them|it|those)\b/.test(t0)) return null;
        return { kind: 'more', mod: 'wide', prev: prev, target: BODY, colour: prev.colour || null, text: t0 };
    }
    function afResolve(so, it0, env) {      // the zones (or a region / a part / an element) the sentence names; null = ask which
        var zs = (env.zones || []).filter(function (z) { return !z.muted; }); if (!so) return null;
        if (so.kind === 'colour') {
            var hz = afColourZones(so.colour, env); if (hz.length) return afZT(hz, 'the ' + so.colour.name, so.colour);
            if (it0.target && it0.target.region) { var rt = afTgt(it0.target); rt.colourHex = so.colour.hex; return rt; }      // ai.js found that colour in the paint pixels (no zone paints it)
            return null;
        }
        if (so.kind === 'numbers') { var nz = zonesFor(TARGETS[0], zs); if (nz.length) return afZT(nz, 'the numbers'); return (env.elements && env.elements.numbers && env.elements.numbers.found) ? { id: 'numbers', label: 'the numbers' } : null; }
        if (so.kind === 'part') { var pz = zonesFor(so.tg, zs); if (pz.length) return afZT(pz, so.tg.label); return { id: so.tg.id, label: so.tg.label }; }      // no zone there yet: applyPlanCore adds a neutral gloss zone on that part to carry the texture
        if (so.kind === 'layer') {
            var ln = norm(so.name); if (ln.length < 2) return null;
            var lz = zs.filter(function (z) { return afLayersOf(z).some(function (l) { var a = norm(l); return a === ln || a.indexOf(ln) !== -1 || (ln.indexOf(a) !== -1 && a.length >= 3); }); });
            if (lz.length) return afZT(lz, 'the ' + so.name + ' layer');
            var L = afLayerName(so.name); return L ? { id: 'layer', label: 'the ' + L + ' layer', region: { layers: [L] } } : null;
        }
        if (so.kind === 'body') { var bz = afHit(BODY, zs, null); return bz.length ? afZT(bz, 'the body') : null; }
        if (so.kind === 'name') {
            var nm = norm(so.name); if (nm.length < 3) return null;
            var zz = zs.filter(function (z) { var n = norm(z.name); return n === nm || n.indexOf(nm) !== -1 || (nm.indexOf(n) !== -1 && n.length >= 4); });
            if (zz.length) return afZT(zz, zz.length === 1 ? '“' + zz[0].name + '”' : 'the ' + so.name);
            var L2 = afLayerName(so.name); return L2 ? { id: 'layer', label: 'the ' + L2 + ' layer', region: { layers: [L2] } } : null;
        }
        return null;
    }
    function afClass(z) { var it = z && z.finishKey ? AT().lookup(z.finishKey) : null; if (!it) return 'matte'; var m = String(it.metal || 'none'), sh = String(it.shine || '') + ' ' + String(it.n || '').toLowerCase(); if (m === 'full' && /gloss|mirror|chrome/.test(sh)) return 'chrome'; return (m && m !== 'none' && m !== 'low') ? 'metallic' : 'matte'; }
    function afFit(s) {      // how well a spec reads on a finish class, from the deep card's own words (best / strong / clear ... vs faint / easy to miss / lost)
        s = String(s || '').toLowerCase(); if (!s) return 0;
        if (/\b(?:almost nothing|almost no|a whisper|barely|invisible|lost|no visible|hardly|disappears?|vanish\w*|nothing shows?|practically nothing|nothing much|very little|washes? out|muddy)\b/.test(s)) return -2;
        if (/\beasy to miss\b|\bnot (?:much|really) visible\b/.test(s)) return -0.5;
        if (/^\s*(?:best|strongest|excellent|ideal)\b/.test(s)) return 3;
        var st = /\b(?:strong\w*|clear\w*|bright\w*|bold\w*|vivid|crisp|sharp\w*|dense|graphic|dramatic|true|best|striking|pops?)\b/.test(s), wk = /\b(?:faint|subtle|soft\w*|quiet|slight\w*|sparse|gentle|muted|dim)\b/.test(s);
        return st && !wk ? 2.5 : (st ? 1.5 : (wk ? 0.5 : 1));
    }
    function afQuery(it0) { var t = String(it0.text || '').toLowerCase(), q = []; AF_CONCEPT.forEach(function (c) { if (c[0].test(t) && q.indexOf(c[1]) === -1) q.push(c[1]); }); if (it0.words && /sparkl|glitter|glint|flash/.test(it0.words) && q.indexOf(AF_CONCEPT[0][1]) === -1) q.push(AF_CONCEPT[0][1]); return q.join(' ').trim(); }
    function afSpecRank(tg, it0, env, excl) {      // spec patterns ranked for the finishes UNDER them: the deep card's stack.on_<class> fit, weighted by each target zone's share
        var a = AT(), C = W.SpbAICards, R = W.SpbProRank, zs = env.zones || [], tz = tg.zones ? zs.filter(function (z) { return tg.zones.indexOf(String(z.id)) !== -1; }) : [];
        var w = { matte: 0, metallic: 0, chrome: 0 }; (tz.length ? tz : afHit(BODY, zs, null)).forEach(function (z) { var s = afShare(z); w[afClass(z)] += (s != null && s > 0 ? s : 1); });
        var tot = w.matte + w.metallic + w.chrome; if (!tot) { w.matte = 1; tot = 1; }
        var dom = ['matte', 'metallic', 'chrome'].sort(function (x, y) { return w[y] - w[x]; })[0];
        var on = {}; tz.forEach(function (z) { ((z.specLayers && z.specLayers.length) ? z.specLayers.map(function (x) { return x.id; }) : (z.specStack || [])).forEach(function (id) { on['spec::' + id] = 1; }); });
        var av = {}; try { if (it0.dislikes && it0.dislikes.length && R && R.avoidSet) av = R.avoidSet(it0.dislikes); } catch (e) {}
        var t = String(it0.text || '').toLowerCase(), calm = it0.mod === 'calm' || /\b(?:subtle|subtly|faint|quiet|classy|tasteful|understated|gentle|hint|not too loud)\b/.test(t), bold = !calm && (it0.mod === 'bold' || /\b(?:cool|wild|crazy|loud|bold|pop|insane|sick|awesome|flashy|epic|stand out|wow)\b/.test(t));
        var rel = {}, q = afQuery(it0), cre = AF_CONCEPT.filter(function (c) { return c[0].test(t); }).map(function (c) { return c[0]; });
        if (q && R && R.search) { try { R.search(q, { limit: 40, types: ['spec'], avoid: it0.dislikes }).forEach(function (r, i) { rel[r.key] = 40 - i; }); } catch (e) {} }
        var rows = [];
        a._data().items.forEach(function (it) {
            if (it._type !== 'spec' || on[it.k] || excl.indexOf(it.k) !== -1 || av[it.k] || (it.q != null && it.q < 55)) return;
            try { if (it0.dislikes && it0.dislikes.length && stBad(it, it0.dislikes)) return; } catch (e1) {}
            var dp = C && C.deep ? C.deep(it.k) : null, st = dp && dp.stack; if (!st || !(st.on_matte || st.on_metallic)) return;
            var cd = (C && C.card(it.k)) || {}, fit = (afFit(st.on_matte) * w.matte + afFit(st.on_metallic || st.on_matte) * w.metallic + afFit(st.on_chrome || st.on_metallic) * w.chrome) / tot;
            var vis = String(st.visibility || ''), vs = /strong|high|bold/.test(vis) ? 2 : (/moderate|medium|clear/.test(vis) ? 1 : (/subtle|low|faint/.test(vis) ? -1 : 0)), loud = cd.loud || 3;
            var fitV = calm ? (fit > 0 ? Math.min(fit, 1) : fit) : fit, s = fitV * (q ? 6 : 10) + (calm ? (-vs * 2 + (3 - loud) * 2.5) : (vs * 2 + (bold ? (loud - 3) * 1.5 : 0))) + (cd.appeal || 3) * 2 + (it.q || 60) / 25 + (q ? (rel[it.k] != null ? 15 + rel[it.k] * 0.8 : -15) : 0) + (cre.some(function (re) { return re.test(String(it.n || '').toLowerCase()); }) ? 20 : 0);      // calm: readable is enough, quiet wins; a described ask ("brushed") ranks its own matches first
            rows.push({ it: it, s: s, st: st, cd: cd });
        });
        rows.sort(function (x, y) { return y.s - x.s || (x.it.k < y.it.k ? -1 : 1); });
        var out = [], fam = {}, grp = {};
        rows.forEach(function (r) { if (out.length >= 4) return; var f = norm(r.it.n).split(' ')[0], g = r.it.g || ''; if (fam[f] || (g && grp[g] >= 2)) return; fam[f] = 1; if (g) grp[g] = (grp[g] || 0) + 1; out.push(r); });
        return { rows: out, dom: dom, w: w, zones: tz };
    }
    var AF_CLS = { matte: 'non-metal paint', metallic: 'metallic paint', chrome: 'chrome' };
    function afAsk(so, it0, env) {
        var zs = (env.zones || []).filter(function (z) { return !z.muted; }), what = so ? (so.kind === 'colour' ? 'any ' + so.colour.name + ' painted by your zones' : '“' + (so.name || so.phrase) + '”') : 'that part';
        var cand = zs.filter(function (z) { return z.colour || !isWhole(z); }).slice(0, 4); if (!cand.length) cand = zs.slice(0, 4);
        return { text: 'Which part should get the shine texture? I could not find ' + what + ' on this car' + (cand.length ? '. Your zones: ' + afList(cand) : '') + '. Nothing was changed.', cards: [], target: null, useLabel: 'that part', kind: 'recommend', lane: 'specover', shown: [], ask: true, next: cand.map(function (z) { return 'A cool spec over the ' + z.name + ' zone'; }) };
    }
    function specOverAnswer(it0, env) {
        var t0 = String(it0.text || '').toLowerCase().replace(/[’`]/g, "'"), so = it0.specOver || null;
        if (!so) { var c0 = null; try { c0 = afSpecClaim(it0.text || '', t0, null, it0.dislikes || []); } catch (e) {} so = c0 ? c0.specOver : null; if (c0 && c0.words && !it0.words) it0.words = c0.words; }
        var tg = null;
        if (it0.prev && it0.target && (it0.target.zones || it0.target.region)) tg = it0.target;      // "more" / "calmer": the same zones
        else if (so) tg = afResolve(so, it0, env);
        if (!tg && it0.target && (it0.target.region || (it0.target.id && it0.target.id !== 'body'))) tg = afTgt(it0.target);
        if (!tg) return afAsk(so, it0, env);
        it0.target = tg;      // ai.js stores it as the conversation target (_advLast.target): "show me more", "use the second one", a stack "on them" stay on these zones
        var excl = ((it0.mod && it0.prev && it0.prev.shown) ? it0.prev.shown.slice() : []).concat(it0.not || []);
        var rk = afSpecRank(tg, it0, env, excl); if (!rk.rows.length) return null;
        var hex = tg.colourHex || (it0.colour && it0.colour.hex) || null, tgt = afTgt(tg), zl = rk.zones.length ? afList(rk.zones) : '';
        var cards = rk.rows.map(function (r) {
            var on = String(r.st['on_' + rk.dom] || r.st.on_matte || r.st.on_metallic || ''), fm = /^\s*([a-z][a-z -]{2,18}?)\s*:\s*/.exec(on), body = fm ? on.slice(fm[0].length) : on;
            var fw = fm && /^(?:best(?: use| case)?|strongest|stronger|much stronger|clearly stronger|clearer|clearly visible|clearly better|bolder|sharper|good|clear|strong|softer|slightly stronger|noticeably stronger)$/.test(fm[1].trim()) ? fm[1].trim() : '', why = firstSentence(fm && !fw ? on : (body || r.cd.look || r.it.d || ''), 104).replace(/[.…]+$/, '') + ' (' + (fw ? fw + ' ' : '') + 'on ' + AF_CLS[rk.dom] + ')';
            var c = card(r.it.k, why, hex); if (!c) return null; c.why = why; c.lane = 'texture'; c.target = tgt; return c;
        }).filter(Boolean);
        var mix = ['matte', 'metallic', 'chrome'].filter(function (k) { return rk.w[k] > 0; }).map(function (k) { return AF_CLS[k]; });
        var text = (it0.mod === 'more' ? 'More shine textures for ' : it0.mod === 'calm' ? 'Subtler shine textures for ' : it0.mod === 'bold' ? 'Bolder shine textures for ' : 'Shine textures for ') + tg.label + (zl ? ' (' + (rk.zones.length === 1 ? 'zone ' : rk.zones.length + ' zones: ') + zl + ')' : '') + '. A shine texture changes only the spec (metal / roughness / clearcoat): every colour, finish and pattern stays, and nothing else on the car is touched.' +
            ' Ranked for how each one reads on ' + (mix.length ? mix.join(' + ') : 'that paint') + '.' +
            '\n**Use on ' + tg.label + '** adds it to exactly ' + (rk.zones.length > 1 ? 'those ' + rk.zones.length + ' zones' : (rk.zones.length ? 'that zone' : tg.label)) + ' (one Undo); their own spec layers stay.' +
            '\nShine textures do not show in the flat preview - check the 3D view.';
        if (it0.dislikes && it0.dislikes.length) text += '\nI am leaving out anything ' + it0.dislikes.join(' / ') + '.';
        var shown = ((it0.mod && it0.prev && it0.prev.shown) ? it0.prev.shown.slice() : []).concat(cards.map(function (c) { return c.key; }));
        return { text: text, cards: cards, target: tgt, useLabel: tg.label, colour: hex, shown: shown, kind: 'recommend', lane: 'specover', next: ['Show me more', 'Something subtler', 'Something bolder'] };
    }
    function afStackTarget(it0, env) {      // a stack applies to the target of the conversation: a colour the sentence names ("... for the pink") or the zones of the last targeted ask ("... on them")
        if (!it0 || (it0.target && !it0.target.all)) return;
        var t0 = String(it0.text || '').toLowerCase().replace(/[’`]/g, "'"), ph = afTargetPhrase(t0), tp = ph ? afParseTarget(ph) : null, tg = null;
        if (tp && tp.kind === 'colour') { var hz = afColourZones(tp.colour, env); if (hz.length) tg = afZT(hz, 'the ' + tp.colour.name, tp.colour); }
        else if (tp && tp.kind === 'name' && /\bzones?\b/.test(tp.phrase || '')) { var nt = afResolve(tp, it0, env); if (nt && nt.zones) tg = nt; }
        var pv = it0.prev || (env && env.prev) || null;
        if (!tg && pv && pv.target && pv.target.zones && pv.target.zones.length && /\b(?:for|on|to)\s+(?:it|them|those|these|that|there)\b|\bsame (?:zones?|parts?|areas?|spots?|places?)\b|\b(?:those|these|them) (?:zones?|parts?|areas?)\b/.test(t0)) tg = pv.target;
        if (!tg) { var nf = afNotFams(t0); if (nf.length) tg = { id: 'body', label: 'the body', all: true, notFams: nf }; }
        if (tg) it0.target = tg;
    }
    function afChanged(r, target, env) {      // what a Use changes, in plain words: zone names + approximate share ("“Spray Can Pink Holo (left side)” (3%), ...")
        if (!r || !r.steps || !r.steps.length) return;
        var zs = env.zones || [], out = [];
        r.steps.forEach(function (st) { var g = st.args || {}, z = null; if (st.tool === 'add_zone') { out.push({ zone: g.name || st.zone || 'new zone', isNew: true }); return; } zs.forEach(function (q) { if ((g.zone_id != null && String(q.id) === String(g.zone_id)) || (g.zone_id == null && g.zone != null && q.i === g.zone)) z = q; }); if (z && !out.some(function (x) { return x.id === String(z.id); })) out.push({ id: String(z.id), zone: z.name, share_pct: afShare(z) }); });
        r.changed = out; r.changedText = afList(out);
        if (target && target.zones && target.zones.length && out.length) r.label = target.label + ' (' + r.changedText + ')';
    }
    function afKitNotes(r, env, it0) {      // every kit says where it lands; a kit that repaints zones outside the conversation target says so (and which), before Use
        if (!r || !r.kits || !r.kits.length) return;
        var conv = it0 && it0.target && it0.target.zones && it0.target.zones.length ? it0.target : ((it0 && it0.wideFrom && it0.wideFrom.zones) ? it0.wideFrom : null), warnAny = false;
        r.kits.forEach(function (k) {
            var base = null; (k.items || []).forEach(function (x) { if (!base && !x.card.stackPart) base = x; }); if (!base) return;
            var pl = null; try { pl = applyPlan(base.card, base.target, env); } catch (e) {} if (!pl || !pl.changed || !pl.changed.length) return;
            k.lands = pl.changed; k.blurb = (k.blurb || '').replace(/\s+$/, '') + ' Lands on ' + afList(pl.changed) + '.'; if (conv && pl.changed.length > 1) k.blurb = k.blurb.split(' in one zone on ').join(' on ');
            var outside = conv ? pl.changed.filter(function (x) { return !x.id || conv.zones.indexOf(x.id) === -1; }) : [];
            if (outside.length && it0.wideFrom) { warnAny = true; k.warn = 'this repaints ' + afList(outside) + ': not ' + conv.label + '. Use it there anyway?'; k.blurb += ' Heads-up: ' + k.warn; }
        });
        if (conv && !it0.wideFrom) {
            if (conv.zones.length > 1) r.text = r.text.split(' in one zone on ' + conv.label).join(' on ' + conv.label + ' (' + conv.zones.length + ' zones)');
            r.text += '\nEvery kit here lands only on ' + conv.label + ': ' + afList((env.zones || []).filter(function (z) { return conv.zones.indexOf(String(z.id)) !== -1; })) + '. Nothing else on the car changes.';
            r.next = ['Show me more', 'Something calmer', 'Show these stacks on the whole body'];
        }
        if (it0.wideFrom && warnAny) { r.text += '\nHeads-up: on the whole body these kits repaint zones that are not ' + it0.wideFrom.label + ' (each card says which). The kits in my answer before this one stay on ' + it0.wideFrom.label + ' only.'; r.next = ['Show me more', 'Something calmer']; }
    }
    // (3) thumbnails: the advisor registers every card it hands out; a thumbnail that fails to load moves to the picker's split swatch, then to a colour chip
    var AF_REG = {}, AF_FB = {}, AF_N = 0;
    function afRegThumbs(r) {
        if (!r) return; function fin(u) { var n = 0; while (AF_FB[u] && n++ < 4) u = AF_FB[u]; return u; }
        function reg(c) { if (!c || !c.thumb) return; c.thumb = fin(c.thumb); (AF_REG[c.thumb] = AF_REG[c.thumb] || []).push(c); AF_N++; }
        (r.cards || []).forEach(reg); (r.kits || []).forEach(function (k) { (k.items || []).forEach(function (x) { reg(x.card); }); });
        if (AF_N > 800) { AF_REG = {}; AF_N = 0; }
    }
    function afChip(a, b) { a = /^#[0-9a-f]{6}$/i.test(String(a || '')) ? a : '#4a4f57'; b = /^#[0-9a-f]{6}$/i.test(String(b || '')) ? b : (a === '#4a4f57' ? '#c7ccd4' : a); return 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' + a + '"/><stop offset="1" stop-color="' + b + '"/></linearGradient></defs><rect width="200" height="200" rx="16" fill="url(#g)"/></svg>'); }
    function afThumbNext(src) {
        var s = String(src || ''), m = /\/api\/swatch\/(base|monolithic|pattern)\/([^?#\/]+)/.exec(s), col = (/[?&]color=([0-9a-f]{6})/i.exec(s) || [])[1] || null;
        if (m && !/[?&]mode=split/.test(s)) return s.slice(0, m.index) + '/api/swatch/' + m[1] + '/' + m[2] + '?color=' + (col || '888888') + '&size=200&mode=split&prefer=live&source=faithful-v1';
        var k = m ? m[1] + '::' + decodeURIComponent(m[2]) : null; if (!k) { var sp = /\/api\/spec-pattern-preview\/([^?#\/]+)/.exec(s); if (sp) k = 'spec::' + decodeURIComponent(sp[1]); }
        var it = null; try { it = k && AT() ? AT().lookup(k) : null; } catch (e) {}
        var cs = (it && it.c) || [], own = it && it.o === 1;
        if (cs.length && (own || !col)) return afChip(cs[0], cs[cs.length - 1]);
        return col ? afChip('#' + col, cs.length ? cs[0] : '#' + col) : afChip(null, null);
    }
    function afOnThumbError(ev) {
        var im = ev && ev.target; if (!im || im.tagName !== 'IMG') return;
        var src = im.getAttribute('src') || '', mine = !!AF_REG[src]; if (!mine) { try { mine = !!(im.closest && im.closest('#spbProAI, .spb-pai-fc, .spb-pai-kititem, .spb-pai-fcards, .spb-pai-kits')) && /\/api\/swatch\/|\/api\/spec-pattern-preview\//.test(src); } catch (e) {} }
        if (!mine) return;
        var nx = AF_FB[src] || afThumbNext(src); if (!nx || nx === src) return; AF_FB[src] = nx;
        (AF_REG[src] || []).forEach(function (c) { c.thumb = nx; (AF_REG[nx] = AF_REG[nx] || []).push(c); });
        im.setAttribute('src', nx);
    }
    try { if (W.document && typeof W.document.addEventListener === 'function' && !W.__spbAdvThumbFallback) { W.__spbAdvThumbFallback = true; W.document.addEventListener('error', afOnThumbError, true); } } catch (e) {}
    // cards for keys the AI named (picture identification): real catalogue keys only
    function cardsFor(keys, env, hex) {
        var a = AT(); if (!a || !a.ready()) return []; var cx = ctxOf(null, env || {}), colour = /^#[0-9a-f]{6}$/i.test(String(hex || '')) ? hex : swatchHex(null, cx, null), out = [], seen = {};
        (keys || []).forEach(function (k) { var it = a.lookup(String(k).replace(/[^a-z0-9_:]/gi, '')); if (!it || seen[it.k] || out.length >= 4 || (it._type !== 'base' && it._type !== 'monolithic')) return; seen[it.k] = 1; var c = card(it.k, firstSentence(it.d || '', 118), colour); if (c) out.push(c); });
        return out;
    }
    W.SpbProAdvisor = { stackPlan: function (text, env, o) { return stackPlan(text, env || {}, o); }, _stackParse: stackParse, suggestTool: suggestTool, cardsFor: cardsFor, version: '2026-10-02', classify: classify, answer: answer, applyPlan: applyPlan, targetOf: targetOf, colourOf: colourOf, resolveName: resolveName, TARGETS: TARGETS, _goalOf: goalOf, _cleanQuery: cleanQuery, _rankQuery: rankQuery, _meaningfulLeft: meaningfulLeft, _negPhrases: negPhrases, _esc: esc, _af: { specClaim: afSpecClaim, parseTarget: afParseTarget, resolve: afResolve, colourZones: afColourZones, thumbNext: afThumbNext, specAnswer: specOverAnswer } };
})();
