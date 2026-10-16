/* ============================================================================
   HELPER V4 lane V4-B 2026-10-07: the OFFLINE LEARNED READER (kNN over a labelled corpus).
   docs/handoff_reports/V4_KNN_READER.md has the design, the numbers and the hook hunks.
   The hand-written readers (js/spb-offline-answer.js route) are tuned to train wording. This module reads a turn by
   RETRIEVAL: the utterance is normalised (slang / typo map, part / colour / finish / pattern / element / layer words ->
   placeholder tokens: "gimme da bonnet in cherry red" -> "give me the PART in COL"), scored with BM25 over word
   unigrams + bigrams + char 3-5-grams against ~2k labelled turns (js/spb-intent-knn-data.js, built by
   _easy_claude_work/eval/knn/build_index.js), and the top-k neighbours VOTE on the turn's skeleton (act + shape).
   SLOTS (parts, colours, finishes, layers, keeps) always come from the CURRENT utterance: SpbIntentFrame.read() for parts /
   keeps / elements / layers, this module's vocab for colours / finishes / patterns. Nothing from a neighbour is applied.
   Global: window.SpbIntentKnn
     install(data)              index the data (done automatically from window.SPB_KNN_DATA on first use)
     norm(text, env)            -> { fixed, ph, slots }   fixed = slang / typo / synonym-fixed surface text, ph = placeholder text
     neighbours(text, opt)      -> [{ i, score, row }]    opt = { k, ctx, exclude: fn(row) -> bool }
     read(text, env, ctx)       -> { frame, want, confidence, margin, sim, neighbours, text, shape }
                                   want = change | answer | ask | nothing | undo | redo; text = a canonical rewrite (a neighbour's
                                   proven wording with this utterance's slots) or null; frame = an SpbIntentFrame v1 frame
     hybrid(text, env, r, route0)   the regex reader's result r is kept when it is confident; otherwise the kNN rewrite is
                                   re-read by route0 (the same reader) and used when it gives a change. Returns r or a new r.
   Settings: SPB_KNN = '0' (window var or localStorage) switches it off (hybrid returns r unchanged).
   ES5 only (old Electron).
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var VERSION = '2026-10-09-w8';

    function flag(name, dflt) {
        try { if (W[name] != null) return String(W[name]); } catch (e) {}
        try { if (W.localStorage) { var v = W.localStorage.getItem(name); if (v != null) return String(v); } } catch (e2) {}
        return dflt;
    }
    function on() { return flag('SPB_KNN', '1') !== '0'; }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }

    // ------------------------------------------------------------------ vocab (surface -> slot)
    // slang / shorthand words (whole tokens)
    var SLANG = { pls: 'please', plz: 'please', pleez: 'please', u: 'you', ya: 'you', yu: 'you', ur: 'your', r: 'are', gimme: 'give me', lemme: 'let me', wanna: 'want to', gonna: 'going to', gotta: 'got to', thx: 'thanks', ty: 'thanks', da: 'the', teh: 'the', hte: 'the', th: 'the', n: 'and', '&': 'and', abit: 'a bit', alil: 'a little', lil: 'little', kinda: 'kind of', sorta: 'sort of', abt: 'about', rn: 'now', yea: 'yes', yeah: 'yes', yep: 'yes', yup: 'yes', ye: 'yes', ok: 'ok', okay: 'ok', k: 'ok', kk: 'ok', nah: 'no', nope: 'no', dont: "don't", cant: "can't", wont: "won't", doesnt: "doesn't", isnt: "isn't", im: "i'm", ive: "i've", w: 'with', 'w/': 'with', wit: 'with', b4: 'before', 2: '2', pic: 'picture', color: 'colour', colors: 'colours', colored: 'coloured', gray: 'grey', fibre: 'fiber', chequered: 'checkered', chequer: 'checker', colour: 'colour', tho: 'though', thru: 'through', smth: 'something', sth: 'something', bc: 'because', cuz: 'because', coz: 'because', rly: 'really', v: 'very', prolly: 'probably', whats: "what's", hows: "how's" };
    // parts: [regex source over the fixed text, canonical surface the readers know, part names]
    var PARTS = [
        ['(?:front|fwd) (?:bumper|bumber|fascia|valance|lip|clip)|nose(?: cone)?|front ?end|chin(?: spoiler)?|front lip', 'front bumper', ['front bumper']],
        ['(?:rear|back) (?:bumper|bumber|fascia|valance|apron)|tail(?! ?lights?)(?! ?gate)|rear ?end|back ?end|butt', 'rear bumper', ['rear bumper']],
        ['bumpers|both bumpers|(?:front and (?:rear|back)|(?:rear|back) and front) bumpers?', 'bumpers', ['front bumper', 'rear bumper']],
        ['(?:left|driver(?:\'?s)?|drivers) (?:side|flank|doors?|panel|quarter)(?: panels?)?|driver ?side|lhs', 'left side', ['left side']],
        ['(?:right|passenger(?:\'?s)?|passengers) (?:side|flank|doors?|panel|quarter)(?: panels?)?|passenger ?side|rhs', 'right side', ['right side']],
        ['rockers?(?: panels?)?|side ?skirts?|skirts?|quarter ?panels?|quarters?|rocker ?panels?', 'sides', ['left side', 'right side']],
        ['cab', 'roof and the sides', ['roof', 'left side', 'right side']],
        ['(?:both |the |two )?(?:sides|flanks|doors)|both (?:side|door)s?', 'sides', ['left side', 'right side']],
        ['(?:rear |top |back )?wing|spoiler|spoilr|spioler|(?:rear )?(?:deck )?spoiler', 'spoiler', ['spoiler']],
        ['hood|bonnet|bonet|hod|hoodd|engine cover', 'hood', ['hood']],
        ['roof|rooftop|roof top|top(?= (?:of the car|of it)\\b)|lid(?! of)', 'roof', ['roof']],
        ['trunk|boot|deck ?lid|decklid|rear deck|tail ?gate|tailgate|trunk lid', 'trunk', ['trunk']],
        ['bumper', 'bumper', ['front bumper', 'rear bumper']],
        ['side|door', 'side', ['left side', 'right side']]
    ];
    // colours: surface word -> [the word the offline reader knows, family]
    var COL = {
        red: ['red', 'red'], crimson: ['red', 'red'], scarlet: ['red', 'red'], cherry: ['red', 'red'], ruby: ['red', 'red'], blood: ['dark red', 'red'], wine: ['maroon', 'red'], burgundy: ['maroon', 'red'], maroon: ['maroon', 'red'], oxblood: ['maroon', 'red'], rosso: ['red', 'red'], firetruck: ['red', 'red'],
        orange: ['orange', 'orange'], tangerine: ['orange', 'orange'], amber: ['orange', 'orange'], rust: ['dark orange', 'orange'], burnt: ['dark orange', 'orange'], coral: ['orange', 'orange'], peach: ['light orange', 'orange'], papaya: ['orange', 'orange'],
        yellow: ['yellow', 'yellow'], lemon: ['yellow', 'yellow'], canary: ['yellow', 'yellow'], mustard: ['dark yellow', 'yellow'], banana: ['yellow', 'yellow'], sunflower: ['yellow', 'yellow'],
        gold: ['gold', 'gold'], golden: ['gold', 'gold'], champagne: ['gold', 'gold'],
        green: ['green', 'green'], lime: ['lime', 'green'], olive: ['dark green', 'green'], mint: ['light green', 'green'], forest: ['dark green', 'green'], emerald: ['green', 'green'], kelly: ['green', 'green'], army: ['dark green', 'green'], sage: ['light green', 'green'], neon: null, jade: ['green', 'green'], hunter: ['dark green', 'green'], seafoam: ['light green', 'green'],
        teal: ['teal', 'teal'], cyan: ['cyan', 'teal'], turquoise: ['teal', 'teal'], aqua: ['teal', 'teal'], aquamarine: ['teal', 'teal'],
        blue: ['blue', 'blue'], navy: ['navy', 'blue'], cobalt: ['blue', 'blue'], royal: null, sky: ['light blue', 'blue'], baby: null, azure: ['blue', 'blue'], sapphire: ['blue', 'blue'], indigo: ['dark blue', 'blue'], denim: ['blue', 'blue'], cerulean: ['blue', 'blue'], gulf: ['light blue', 'blue'], petrol: ['dark blue', 'blue'],
        purple: ['purple', 'purple'], violet: ['violet', 'purple'], lavender: ['light purple', 'purple'], lilac: ['light purple', 'purple'], plum: ['dark purple', 'purple'], grape: ['purple', 'purple'], eggplant: ['dark purple', 'purple'], mauve: ['light purple', 'purple'],
        pink: ['pink', 'pink'], magenta: ['magenta', 'pink'], fuchsia: ['magenta', 'pink'], rose: ['pink', 'pink'], salmon: ['pink', 'pink'], bubblegum: ['pink', 'pink'],
        white: ['white', 'white'], ivory: ['white', 'white'], snow: ['white', 'white'], cream: ['cream', 'white'], offwhite: ['white', 'white'], pearl: null,
        silver: ['silver', 'silver'], aluminium: ['silver', 'silver'], aluminum: ['silver', 'silver'], platinum: ['silver', 'silver'], titanium: ['silver', 'silver'],
        grey: ['grey', 'grey'], charcoal: ['dark grey', 'grey'], gunmetal: ['dark grey', 'grey'], graphite: ['dark grey', 'grey'], slate: ['grey', 'grey'], ash: ['grey', 'grey'], primer: ['grey', 'grey'], smoke: null, cement: ['grey', 'grey'], nardo: ['grey', 'grey'],
        black: ['black', 'black'], jet: ['black', 'black'], onyx: ['black', 'black'], ebony: ['black', 'black'], blackout: ['black', 'black'], murdered: null,
        brown: ['brown', 'brown'], chocolate: ['brown', 'brown'], coffee: ['brown', 'brown'], mocha: ['brown', 'brown'], tan: ['tan', 'brown'], beige: ['beige', 'brown'], sand: ['beige', 'brown'], khaki: ['tan', 'brown'], bronze: ['bronze', 'brown'], copper: ['copper', 'orange'], caramel: ['tan', 'brown']
    };
    var COL_MOD = { dark: 'dark', darker: null, deep: 'dark', light: 'light', pale: 'light', bright: 'bright', neon: 'bright', fluro: 'bright', fluo: 'bright', fluorescent: 'bright', hot: 'bright', baby: 'light', sky: 'light', royal: '', midnight: 'dark', electric: 'bright', dayglo: 'bright', kelly: '', racing: '', safety: 'bright' };
    var COL_PAIR = { 'royal blue': ['blue', 'blue'], 'baby blue': ['light blue', 'blue'], 'sky blue': ['light blue', 'blue'], 'hot pink': ['pink', 'pink'], 'neon green': ['lime', 'green'], 'neon yellow': ['yellow', 'yellow'], 'neon pink': ['pink', 'pink'], 'neon orange': ['orange', 'orange'], 'neon blue': ['blue', 'blue'], 'british racing green': ['dark green', 'green'], 'racing green': ['dark green', 'green'], 'gulf blue': ['light blue', 'blue'], 'safety orange': ['orange', 'orange'], 'midnight blue': ['navy', 'blue'], 'pearl white': ['white', 'white'], 'off white': ['white', 'white'], 'fire engine red': ['red', 'red'], 'blood red': ['dark red', 'red'], 'burnt orange': ['dark orange', 'orange'], 'army green': ['dark green', 'green'], 'forest green': ['dark green', 'green'], 'smoke grey': ['grey', 'grey'], 'nardo grey': ['grey', 'grey'], 'jet black': ['black', 'black'] };
    // finishes (spec looks) and patterns (textures / graphics)
    var FIN = [['satin chrome', 'satin chrome', 'chrome'], ['chrome|chromed|chromey|mirrored|mirror (?:finish|chrome|polish(?:ed)?)|mirror like|like a mirror', 'chrome', 'chrome'], ['matte|matt|flat(?! paint\\b)(?= |$)|mat', 'matte', 'matte'], ['satin|semi ?gloss|eggshell', 'satin', 'satin'],
        ['high gloss|glossy|gloss|shiny|wet look|clear ?coat(?:ed)?', 'gloss', 'gloss'], ['candy|kandy|candied', 'candy', 'candy'], ['pearl|pearlescent|pearly', 'pearl', 'pearl'], ['metallic|metalic|metal flake|metalflake|flake|flaked|sparkle|glitter', 'metallic', 'metallic'],
        ['brushed(?: metal| aluminium| aluminum)?', 'brushed', 'metallic'], ['holo(?:graphic)?|iridescent|chameleon|colou?r ?shift(?:ing)?|spectra(?:flair)?|prism(?:atic)?|rainbow flake|oil ?slick', 'holographic', 'holo'], ['anodi[sz]ed', 'anodized', 'metallic'], ['frozen|velvet|suede|rubber(?:ized)?|plasti ?dip', 'matte', 'matte']];
    var PAT = [['carbon(?: ?fib(?:er|re))?|cf|forged carbon', 'carbon fiber', 'carbon'], ['digital camo|camo(?:uflage)?|camouflage', 'camo', 'camo'], ['flames?|flame ?job|fire', 'flames', 'flames'], ['hexagon(?:s|al)?|hex(?! code| value| colou?r| #| number)(?= \\w)|honeycomb', 'hex', 'other'], ['checker(?:ed|board|s)?|chequer(?:ed)?|checkers', 'checker', 'other'],
        ['tiger(?: stripes?)?|zebra|leopard|cheetah|snake ?skin|snakeskin|scales|dragon ?scales?', 'animal print', 'other'], ['splatter|paint splash|drip|marble|marbled|galaxy|nebula|lightning|tribal|geometric|triangles|stars|polka dots?|dots', 'pattern', 'other']];
    var REL = 'darker|lighter|brighter|duller|deeper|paler|richer|softer|shinier|glossier|flatter|matter|thinner|thicker|wider|narrower|skinnier|fatter|bigger|smaller|larger|finer|tighter|coarser|looser|less|more|stronger|weaker|bolder|subtler|warmer|cooler|redder|bluer|greener';
    var OBJ = 'mirrors?|side ?mirrors?|wheels?|rims?|tyres?|tires?|windows?|windshield|wind ?screen|glass|fenders?|splitter|diffuser|grilles?|grill|pillars?|a ?pillars?|roll ?cage|cage|intakes?|vents?|scoops?|hood ?scoop|headlights?|tail ?lights?|exhaust|interior|seats?|bed|mudflaps?|skull|spray ?can|logo on the \\w+|dragon|eagle|star|helmet';

    var SLOT_RES = null;
    function slotRes() {
        if (SLOT_RES) return SLOT_RES;
        var parts = PARTS.map(function (p) { return { re: new RegExp('^(?:' + p[0] + ')\\b'), canon: p[1], parts: p[2] }; });
        var colWords = Object.keys(COL).filter(function (k) { return COL[k]; }).sort(function (a, b) { return b.length - a.length; });
        var fins = FIN.map(function (f) { return { re: new RegExp('^(?:' + f[0] + ')\\b'), canon: f[1], cls: f[2] }; });
        var pats = PAT.map(function (f) { return { re: new RegExp('^(?:' + f[0] + ')\\b'), canon: f[1], cls: f[2] }; });
        SLOT_RES = { parts: parts, colWords: colWords, fins: fins, pats: pats, rel: new RegExp('^(?:a (?:bit|little|lot|touch|tad) |way |much |slightly |even |super )?(?:' + REL + ')\\b'), obj: new RegExp('^(?:' + OBJ + ')\\b'),
            num: /^(?:numbers?|digits?|race ?numbers?|car ?numbers?|#s)\b/, spon: /^(?:sponsors?|logos?|decals?|stickers?|contingenc(?:y|ies)(?: decals?)?)\b/, n: /^(?:\d+(?:\.\d+)?\s?(?:%|px|x|percent|pixels?)?|half|double|twice|triple)\b/, hex: /^#[0-9a-f]{6}\b|^#[0-9a-f]{3}\b/ };
        return SLOT_RES;
    }

    // ------------------------------------------------------------------ fuzzy typo repair (domain vocab only; never a word the corpus knows)
    var DOMAIN = ['hood', 'roof', 'trunk', 'spoiler', 'bumper', 'bumpers', 'front', 'rear', 'side', 'sides', 'left', 'right', 'door', 'doors', 'bonnet', 'wing', 'numbers', 'number', 'sponsors', 'sponsor', 'logos', 'logo', 'decals', 'decal', 'stripe', 'stripes', 'pinstripe', 'outline', 'gradient', 'fade', 'flames', 'chrome', 'matte', 'satin', 'gloss', 'glossy', 'candy', 'pearl', 'metallic', 'carbon', 'fiber', 'camo', 'pattern', 'checker', 'colour', 'purple', 'yellow', 'orange', 'green', 'white', 'black', 'silver', 'brown', 'maroon', 'violet', 'magenta', 'turquoise', 'burgundy', 'charcoal', 'make', 'paint', 'change', 'undo', 'redo', 'except', 'everything', 'whole', 'layer', 'mirrors', 'mirror', 'splitter', 'diffuser', 'little', 'darker', 'lighter', 'thinner', 'thicker', 'finer', 'bigger', 'smaller', 'shinier', 'brighter', 'please', 'instead', 'actually', 'leave', 'keep', 'same', 'match', 'copy', 'swap', 'between', 'pinline', 'spec', 'shine', 'shiny', 'texture', 'scale', 'crushed', 'holographic', 'iridescent', 'quarter', 'panel', 'fender', 'fenders', 'mirror', 'livery', 'scheme', 'theme', 'christmas', 'patriotic', 'previous', 'again', 'opacity', 'visible', 'hide', 'show', 'without', 'bottom', 'middle', 'stays', 'untouched', 'rainbow', 'blue', 'pink', 'teal', 'grey', 'gold', 'red', 'lime', 'navy', 'cyan', 'bronze', 'copper', 'beige', 'cream', 'flat', 'shade', 'tone', 'touch', 'dull', 'nose', 'tail', 'roof', 'trunk', 'hood', 'wheels', 'windows', 'bigger'];
    var DOM_SET = null, KNOWN = {};
    function dl(a, b, cap) {
        var n = a.length, m = b.length, i, j; if (Math.abs(n - m) > cap) return cap + 1;
        var d = []; for (i = 0; i <= n; i++) { d[i] = [i]; } for (j = 0; j <= m; j++) d[0][j] = j;
        for (i = 1; i <= n; i++) { var best = 99; for (j = 1; j <= m; j++) {
            var c = a[i - 1] === b[j - 1] ? 0 : 1; d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
            if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
            if (d[i][j] < best) best = d[i][j]; } if (best > cap) return cap + 1; }
        return d[n][m];
    }
    // W8-KNN 2026-10-09 (held-out reworded set: abbreviations / vowel-less typing were unread, 'blk', 'bmpr', 'cndy', 'orng', 'top'): whole-token shorthand -> the word the slot tables know.
    // Kill switch: window.SPB_KNN_NOW8 = '0' (or localStorage). Measured on a 1/3 held-out of Haiku rewordings of TRAIN: see _easy_claude_work/eval/w8knn/REPORT.md
    function now8() { return flag('SPB_KNN_NOW8', '0') === '1'; }          // W9ARB 2026-10-09: the NOW8 pass inside the kNN normaliser is OFF by default (W8-KNN: +1-2 harmful items on dev / blind6); frame-level abbr() below is the safe use of the same table
    function w9abbrOn() { return flag('SPB_KNN_W9ABBR', '1') !== '0'; }
    var ABBR = { blk: 'black', blck: 'black', blak: 'black', blac: 'black', wht: 'white', whte: 'white', wite: 'white', wyt: 'white', whit: 'white', orng: 'orange', orang: 'orange', orge: 'orange', ornge: 'orange', blu: 'blue', bleu: 'blue', grn: 'green', gren: 'green', grean: 'green', gld: 'gold', glod: 'gold',
        slvr: 'silver', silv: 'silver', silvr: 'silver', sliver: 'silver', gry: 'grey', gy: 'grey', yel: 'yellow', yllw: 'yellow', yelw: 'yellow', ylw: 'yellow', yelo: 'yellow', purp: 'purple', prpl: 'purple', prp: 'purple', purpl: 'purple', pnk: 'pink', brwn: 'brown', brn: 'brown',
        cndy: 'candy', candi: 'candy', cady: 'candy', mtlc: 'metallic', metlc: 'metallic', mtllc: 'metallic', brushd: 'brushed', brshd: 'brushed', glss: 'gloss', glos: 'gloss', chrm: 'chrome', chrom: 'chrome', crome: 'chrome', mate: 'matte', matt: 'matte', crbn: 'carbon', carbn: 'carbon', prl: 'pearl', perl: 'pearl',
        chkrboard: 'checkerboard', chkr: 'checker', chekered: 'checkered', chkrd: 'checkered', chckr: 'checker', chkd: 'checkered', nvy: 'navy', mrn: 'maroon',
        bmpr: 'bumper', bumpr: 'bumper', bmper: 'bumper', bumpar: 'bumper', bmpers: 'bumpers', bmprs: 'bumpers', bumprs: 'bumpers', fndr: 'fender', fendr: 'fender', fndrs: 'fenders', trnk: 'trunk', trunck: 'trunk', spoilr: 'spoiler', spoilar: 'spoiler', hoood: 'hood', bnet: 'bonnet', bonnt: 'bonnet', rf: 'roof', ruf: 'roof', rooof: 'roof',
        lft: 'left', rgt: 'right', rght: 'right', rite: 'right', frnt: 'front', fnt: 'front', drvr: 'driver', psngr: 'passenger', drs: 'doors', dor: 'door', mirrs: 'mirrors', mirr: 'mirror', sds: 'sides', pnl: 'panel', pnls: 'panels',
        nums: 'numbers', nmbr: 'number', nmbrs: 'numbers', spons: 'sponsors', sponsr: 'sponsor', strp: 'stripe', strps: 'stripes', gradnt: 'gradient', flms: 'flames', flmes: 'flames', wo: 'without', wout: 'without', plse: 'please', pleas: 'please', pleeze: 'please' };
    var SIDE_AFTER = /^(?:side|sides|door|doors|fender|fenders|quarter|flank|panel|panels|mirror|mirrors|wing|rocker|skirt|half|one)$/;
    var TOP_NOT_AFTER = /^(?:wing|spoiler|half|part|coat|layer|speed|tier|notch|three|ten|five|two|portion|edge|stripe|stripes|section|bit|of|view|down|dollar|left|right)$/;
    function now8Tokens(toks) {          // whole-token shorthand + "r door" / "l side" / "top" (= roof) / "lip" / "diffuser"; returns a new token list
        var out = [];
        for (var i = 0; i < toks.length; i++) {
            var w = toks[i], nx = toks[i + 1] || '', pv = toks[i - 1] || '';
            if ((w === 'are' || w === 'r' || w === 'rt') && SIDE_AFTER.test(nx)) { out.push('right'); continue; }
            if ((w === 'l' || w === 'lt') && SIDE_AFTER.test(nx)) { out.push('left'); continue; }
            if (w === 'top' && !TOP_NOT_AFTER.test(nx) && !/^(?:on|at|from|in|to|of|and|a|off|over|up|rear|front|back|bottom|left|right|upper|my|its|the|very)$/.test(pv) || (w === 'top' && /^(?:the|my|its)$/.test(pv) && !TOP_NOT_AFTER.test(nx) && !/^(?:half|part)$/.test(nx))) { out.push('roof'); continue; }
            if ((w === 'lip' || w === 'splitter') && pv !== 'front') { out.push('front'); out.push('bumper'); continue; }
            if (w === 'diffuser' && pv !== 'rear' && pv !== 'back') { out.push('rear'); out.push('bumper'); continue; }
            if (w === 'airfoil' || w === 'airfoils') { out.push('spoiler'); continue; }
            if ((w === 'hand' || w === 'handed') && /^(?:left|right)$/.test(pv) && SIDE_AFTER.test(nx)) continue;          // "left-hand side" -> "left side"
            if (w === 'port' && (SIDE_AFTER.test(nx) || /^(?:and|&)$/.test(nx) && toks[i + 2] === 'starboard')) { out.push(SIDE_AFTER.test(nx) ? 'left' : 'left side'); continue; }
            if (w === 'starboard') { out.push(SIDE_AFTER.test(nx) ? 'right' : 'right side'); continue; }
            if ((w === 'weave' || w === 'woven') && pv !== 'carbon') { out.push('carbon'); out.push('fiber'); continue; }
            if ((w === 'weave' || w === 'woven') && pv === 'carbon') { out.push('fiber'); continue; }
            if ((w === 'fiber' || w === 'fibre') && pv !== 'carbon' && pv !== 'glass') { out.push('carbon'); out.push('fiber'); continue; }
            if (/^[a-z]{3,8}ish$/.test(w) && COL[w.slice(0, -3)]) { out.push(w.slice(0, -3)); continue; }          // "pinkish" -> "pink"
            if (ABBR.hasOwnProperty(w)) { out.push(ABBR[w]); continue; }
            out.push(w);
        }
        return out;
    }
    var FIX_CACHE = {};
    function fixWord(w) {
        if (w.length < 5 || /[^a-z]/.test(w)) return w;
        if (!DOM_SET) { DOM_SET = {}; DOMAIN.forEach(function (x) { DOM_SET[x] = 1; }); Object.keys(COL).forEach(function (x) { if (x.length >= 4) DOM_SET[x] = 1; }); }
        if (DOM_SET[w] || KNOWN[w]) return w;
        if (FIX_CACHE[w] != null) return FIX_CACHE[w];
        var best = w, bd = 9, cap = w.length >= 8 ? 2 : 1;
        Object.keys(DOM_SET).forEach(function (v) { if (Math.abs(v.length - w.length) > cap || (v[0] !== w[0] && w.length < 7) || v.length < 5) return; var d = dl(w, v, cap); if (d <= cap && d < bd) { bd = d; best = v; } });
        FIX_CACHE[w] = best; return best;
    }

    // ------------------------------------------------------------------ normalise: surface fix + placeholder text + slots (in order)
    function prep(text) {
        var s = String(text == null ? '' : text).toLowerCase().replace(/[\u2018\u2019`]/g, "'").replace(/[\u201c\u201d]/g, '"');
        s = s.replace(/(^|[^&\w])#([0-9a-f])([0-9a-f])([0-9a-f])(?![0-9a-z])/gi, '$1#$2$2$3$3$4$4');
        s = s.replace(/(^|[^#a-f0-9])([a-z])\2{2,}/g, '$1$2$2');          // "sooooo" -> "soo"
        s = s.replace(/[^a-z0-9#%'&/\s-]+/g, ' ').replace(/(\w)-(\w)/g, '$1 $2').replace(/\s+/g, ' ').trim();
        var out = [];
        var tk0 = s.split(' '); if (now8()) tk0 = now8Tokens(tk0);
        tk0.forEach(function (w) { if (!w) return; var x = SLANG.hasOwnProperty(w) ? SLANG[w] : w; if (x === w && /^[a-z]+$/.test(w)) x = fixWord(w); out.push(x); });
        return out.join(' ');
    }
    // the buyer's own sentence with only typos / slang repaired (punctuation, part words and colours untouched)
    function spellFix(text) {
        var t = String(text == null ? '' : text).replace(/([a-z])\1{2,}/gi, '$1$1');
        return t.replace(/[A-Za-z]+/g, function (w) { var lw = w.toLowerCase(), x = SLANG.hasOwnProperty(lw) ? SLANG[lw] : fixWord(lw); return x === lw ? w : x; });
    }
    function layerRes(env) {
        var L = ((env && env.layers) || []).filter(function (l) { return l && l.name && !/mask|wire|mandatory|template/i.test(l.name + ' ' + (l.role || '')); });
        return L.map(function (l) { var nm = String(l.name).toLowerCase().replace(/_/g, ' ').trim(); return { name: l.name, re: new RegExp('^(?:the )?' + nm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '[ _]?') + '(?: layer)?\\b'), multi: nm.indexOf(' ') !== -1 || /layer/.test(nm), role: l.role || '' }; });
    }
    function norm(text, env) {
        var R = slotRes(), s = prep(text), toks = s ? s.split(' ') : [], slots = [], ph = [], fixed = [], i = 0, pos = 0, LR = layerRes(env);
        while (i < toks.length) {
            var rest = toks.slice(i).join(' '), m = null, adv = 0, sl = null;
            // layers named with "layer" (or a multi-word layer name)
            for (var a = 0; a < LR.length && !sl; a++) { m = LR[a].re.exec(rest); if (m && (LR[a].multi || /layer/.test(m[0]) || /^(?:in|on) the$/.test(toks.slice(Math.max(0, i - 2), i).join(' ')) && /layer/.test(toks.slice(i, i + 3).join(' ')))) { sl = { t: 'LAYER', s: m[0], v: LR[a].name }; adv = m[0].split(' ').length; } }
            if (!sl && (m = R.hex.exec(rest))) { sl = { t: 'COL', s: m[0], v: m[0], fam: null, hex: m[0] }; adv = 1; }
            if (!sl) { for (var c2 in COL_PAIR) { if (rest.indexOf(c2) === 0 && /^\b|\s|$/.test(rest.charAt(c2.length) || ' ')) { sl = { t: 'COL', s: c2, v: COL_PAIR[c2][0], fam: COL_PAIR[c2][1] }; adv = c2.split(' ').length; break; } } }
            if (!sl) {          // [modifier] colour [ish]
                var w0 = toks[i], w1 = toks[i + 1] || '', mod = COL_MOD.hasOwnProperty(w0) && COL[w1] ? w0 : null, cw = mod ? w1 : w0;
                if (COL[cw] && !(cw === 'gold' && /^(?:chrome|leaf|flake)/.test(toks[i + 1] || '')) && !(cw === 'black' && /^(?:base|layer)/.test(toks[i + 1] || '') ) && !(cw === 'white' && /^(?:base|layer)/.test(toks[i + 1] || '')) && !(cw === 'yellow' && /^(?:base|layer)/.test(toks[i + 1] || ''))) {
                    var cv = COL[cw][0], fam = COL[cw][1], md = mod ? COL_MOD[mod] : '', nx = toks[i + (mod ? 2 : 1)] || '', merged = false;
                    if (COL[nx] && COL[nx][0] === nx && nx !== cw) { if (COL[nx][1] !== fam) { cv = COL[nx][0]; fam = COL[nx][1]; } merged = true; }          // "cherry red", "lime green", "sky blue"
                    if (md && cv.indexOf(' ') === -1) cv = md + ' ' + cv;
                    sl = { t: 'COL', s: (mod ? mod + ' ' : '') + cw + (merged ? ' ' + nx : ''), v: cv, fam: fam }; adv = (mod ? 2 : 1) + (merged ? 1 : 0); if (/^ish$|^y$/.test(toks[i + adv] || '')) adv++;
                }
            }
            if (!sl) for (var p = 0; p < R.parts.length && !sl; p++) { m = R.parts[p].re.exec(rest); if (m) { sl = { t: 'PART', s: m[0], v: R.parts[p].canon, parts: R.parts[p].parts }; adv = m[0].split(' ').length; } }
            if (!sl) for (var f = 0; f < R.fins.length && !sl; f++) { m = R.fins[f].re.exec(rest); if (m) { sl = { t: 'FIN', s: m[0], v: R.fins[f].canon, cls: R.fins[f].cls }; adv = m[0].split(' ').length; } }
            if (!sl) for (var q = 0; q < R.pats.length && !sl; q++) { m = R.pats[q].re.exec(rest); if (m) { sl = { t: 'PAT', s: m[0], v: R.pats[q].canon, cls: R.pats[q].cls }; adv = m[0].split(' ').length; } }
            if (!sl && (m = R.num.exec(rest))) { sl = { t: 'NUMS', s: m[0], v: 'numbers' }; adv = m[0].split(' ').length; }
            if (!sl && (m = R.spon.exec(rest))) { sl = { t: 'SPON', s: m[0], v: 'sponsors' }; adv = m[0].split(' ').length; }
            if (!sl && (m = R.rel.exec(rest))) { sl = { t: 'REL', s: m[0], v: m[0] }; adv = m[0].split(' ').length; }
            if (!sl && (m = R.obj.exec(rest))) { sl = { t: 'OBJ', s: m[0], v: m[0] }; adv = m[0].split(' ').length; }
            if (!sl && (m = R.n.exec(rest))) { sl = { t: 'N', s: m[0], v: m[0] }; adv = m[0].split(' ').length; }
            if (sl) { var fv = sl.t === 'PART' || sl.t === 'COL' || sl.t === 'FIN' || sl.t === 'PAT' ? sl.v : sl.s; sl.at = pos + (fixed.length ? 1 : 0); sl.end = sl.at + fv.length; pos = sl.end; slots.push(sl); ph.push(sl.t); fixed.push(fv); i += Math.max(1, adv); continue; }
            pos += (fixed.length ? 1 : 0) + toks[i].length; ph.push(toks[i]); fixed.push(toks[i]); i++;
        }
        return { fixed: fixed.join(' '), ph: ph.join(' '), slots: slots, raw: String(text || '').toLowerCase() };
    }

    // ------------------------------------------------------------------ features + BM25
    var STOPW = { the: 1, a: 1, an: 1, my: 1, to: 1, of: 1, it: 1, is: 1, please: 1, can: 1, you: 1, i: 1, me: 1, ok: 1, and: 1, for: 1, on: 1, in: 1 };
    function shortSlots(ph) { return ' ' + ph.replace(/\b[A-Z]+\b/g, function (x) { return x.charAt(0) + x.charAt(x.length - 1); }) + ' '; }
    function cgrams(ph) {          // char 3-5 grams of the placeholder text (slot names shortened): typo / morphology tolerance
        var s = shortSlots(ph), G = {};
        for (var n = 3; n <= 5; n++) for (var j = 0; j + n <= s.length; j++) G[s.substr(j, n)] = 1;
        return G;
    }
    // every feature of a turn, as add(key, weight) calls (keys may repeat: weights add up)
    function featsEach(ph, ctx, noChar, add) {
        var ws = ph.split(' ').filter(Boolean), i;
        for (i = 0; i < ws.length; i++) { add('w:' + ws[i], STOPW[ws[i]] ? 0.3 : 1); if (i) add('b:' + ws[i - 1] + '_' + ws[i], 1); }
        if (ws.length) { add('b:^_' + ws[0], 1); add('b:' + ws[ws.length - 1] + '_$', 0.5); }
        if (!noChar) { var s = shortSlots(ph); for (var n = 3; n <= 5; n++) for (var j = 0; j + n <= s.length; j++) add('c:' + s.substr(j, n), 0.25); }
        if (ctx) { if (ctx.convo) add('x:convo', 1.5); if (ctx.last) add('x:last', 1.5); if (!ctx.convo) add('x:fresh', 1.0);
            if (ctx.pp) { var pw = ctx.pp.split(' ').filter(Boolean); for (i = 0; i < pw.length; i++) if (!STOPW[pw[i]]) add('p:' + pw[i], 0.35); if (pw.length) add('p:^' + pw[0], 0.5); } }
        var nw = ws.length; add('x:len' + (nw <= 2 ? 'S' : nw <= 6 ? 'M' : 'L'), 0.6);
    }
    function feats(ph, ctx, noChar) { var F = {}; featsEach(ph, ctx, noChar, function (k, w) { F[k] = (F[k] || 0) + w; }); return F; }
    var IX = null, SRCW = { g: 0.6, p: 0.9, c: 0.8 }, CHAR = { mode: 'rerank', lam: 0.6, m: 250 };          // char grams: 'index' = in the BM25 index (slow load), 'rerank' = Dice over the top m word candidates
    // data v3 is columnar (strings interned): expand to row objects { id?, o?, ph, pp, want, shape, s, k, ok?, text?, slots? }
    function unpack(d) {
        var C = d.cols, P = d.P, out = new Array(C.ph.length), X = d.x || {};
        for (var i = 0; i < out.length; i++) {
            var r = { ph: P[C.ph[i]], want: d.W[C.w.charCodeAt(i) - 97], shape: d.S[C.sh[i]] }, pp = C.pp[i], sc = C.s.charAt(i);
            if (pp) r.pp = P[pp]; if (C.k.charAt(i) === '1') r.k = 1; if (sc !== '-') r.s = sc;
            var x = X[i]; if (x) { for (var q in x) r[q] = x[q]; } if (!r.id) r.id = '#' + i; var gi = d.gd && d.gd[i]; if (gi) r.g = gi.map(function (n) { return d.G[n]; });
            out[i] = r;
        }
        return out;
    }
    // the index is built in steps so a page can warm it in idle slices (warm()); ready() finishes whatever is left synchronously
    var BUILD = null;
    function begin(data) {
        data = data || W.SPB_KNN_DATA; if (!data || !(data.rows || data.cols)) return false;
        (data.known || []).forEach(function (w) { KNOWN[w] = 1; }); try { var C0 = W.SPB_KNN_CFG || {}; if (C0.srcw) SRCW = C0.srcw; if (C0.char) CHAR = Object.assign({}, CHAR, C0.char); } catch (e) {}
        var rows = data.rows || unpack(data), N = rows.length;
        BUILD = { data: data, rows: rows, N: N, i: 0, noC: CHAR.mode !== 'index', TI: {}, terms: [], lists: [], dl: new Float32Array(N), xdf: { 'x:convo': 0, 'x:last': 0, 'x:fresh': 0, 'x:lenS': 0, 'x:lenM': 0, 'x:lenL': 0 } };
        return true;
    }
    function step(budgetMs) {          // index rows until the time budget is spent; true when every row is in
        var B = BUILD, t0 = Date.now(), tids = [], tws = [], L = 0, TI = B.TI, terms = B.terms, lists = B.lists, xdf = B.xdf;
        var addI = function (t, w) { L += w; if (t.charCodeAt(0) === 120) { if (xdf[t] != null && tids.indexOf(t) === -1) { tids.push(t); tws.push(0); xdf[t]++; } return; }
            var id = TI[t]; if (id === undefined) { id = TI[t] = terms.length; terms.push(t); lists.push([]); } var at = tids.indexOf(id); if (at === -1) { tids.push(id); tws.push(w); } else tws[at] += w; };
        while (B.i < B.N) {          // BM25 over integer term ids; the x: context features stay out of the postings (they touch every row) and score only the candidates
            var i = B.i++, r = B.rows[i]; tids.length = 0; tws.length = 0; L = 0;
            featsEach(r.ph, { convo: !!r.k, last: !!r.last, pp: r.pp || '' }, B.noC, addI);
            for (var z = 0; z < tids.length; z++) if (typeof tids[z] === 'number') lists[tids[z]].push(i, tws[z]);
            B.dl[i] = L;
            if (budgetMs && (i & 255) === 0 && Date.now() - t0 > budgetMs) return false;
        }
        return true;
    }
    function finish() {
        var B = BUILD, N = B.N, dl0 = B.dl, k1 = 1.2, b = 0.6, avg = 0, i;
        for (i = 0; i < N; i++) avg += dl0[i]; avg /= Math.max(1, N);
        var maxdf = N * (B.data.maxdf || 0.2), idf = {}, post = {};
        for (var a = 0; a < B.terms.length; a++) {
            var P = B.lists[a], df = P.length / 2; if (df > maxdf && B.terms[a].charCodeAt(0) === 99) continue;          // very common char grams (index mode only): ~0 idf
            var w = Math.log(1 + (N - df + 0.5) / (df + 0.5)), ids = new Int32Array(df), pw = new Float32Array(df);
            for (var q = 0; q < df; q++) { var ri = P[2 * q], tf = P[2 * q + 1]; ids[q] = ri; pw[q] = w * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl0[ri] / avg)); }
            idf[B.terms[a]] = w; post[B.terms[a]] = { ids: ids, w: pw };
        }
        Object.keys(B.xdf).forEach(function (t) { var df = B.xdf[t]; idf[t] = Math.log(1 + (N - df + 0.5) / (df + 0.5)); });
        IX = { rows: B.rows, post: post, idf: idf, dl: dl0, avg: avg, k1: k1, b: b, N: N, acc: new Float64Array(N), meta: B.data.meta || {} };
        BUILD = null; return true;
    }
    function install(data) { IX = null; if (!begin(data)) return false; step(0); return finish(); }
    // idle warm-up: ~sliceMs of indexing per tick, so no single task blocks the page; cb() when ready
    function warm(cb, sliceMs) {
        if (IX) { if (cb) cb(); return; } if (!BUILD && !begin()) return;
        var tick = function () { if (IX) { if (cb) cb(); return; } if (!BUILD) return; if (step(sliceMs || 25)) { finish(); if (cb) cb(); } else setTimeout(tick, 0); };
        setTimeout(tick, 0);
    }
    function xfeats(r) { var F = {}, nw = r.ph ? r.ph.split(' ').length : 0; if (r.k) F['x:convo'] = 1.5; if (r.last) F['x:last'] = 1.5; if (!r.k) F['x:fresh'] = 1.0; F['x:len' + (nw <= 2 ? 'S' : nw <= 6 ? 'M' : 'L')] = 0.6; return F; }
    function ready() { if (!IX) { if (BUILD) { step(0); finish(); } else install(); } return !!IX; }
    function scoreQ(F, ex, M) {          // -> the best M rows by the word / bigram / prev-turn postings, then + the x: context features
        var acc = IX.acc, touched = [], k1 = IX.k1, b = IX.b;
        for (var t in F) { var P = IX.post[t]; if (!P) continue; var qw = F[t], ids = P.ids, pw = P.w; for (var j = 0; j < ids.length; j++) { var i = ids[j]; if (acc[i] === 0) touched.push(i); acc[i] += qw * pw[j]; } }
        var cand = []; for (var c = 0; c < touched.length; c++) { var ri = touched[c]; if (!ex || !ex(IX.rows[ri])) cand.push(ri); }
        cand.sort(function (x, y) { return acc[y] - acc[x]; }); cand = cand.slice(0, M);
        var out = cand.map(function (ri) {
            var s = acc[ri], X = xfeats(IX.rows[ri]), nl = IX.dl[ri] / IX.avg;
            for (var xt in X) if (F[xt]) s += F[xt] * IX.idf[xt] * (X[xt] * (k1 + 1)) / (X[xt] + k1 * (1 - b + b * nl));
            return { i: ri, score: s, row: IX.rows[ri] };
        });
        for (c = 0; c < touched.length; c++) acc[touched[c]] = 0;
        return out;
    }
    function selfScore(F) { var s = 0; Object.keys(F).forEach(function (t) { var id = IX.idf[t]; if (id == null) id = Math.log(1 + IX.N); s += F[t] * id * (F[t] * (IX.k1 + 1)) / (F[t] + IX.k1); }); return s || 1; }
    function neighbours(text, opt) {
        opt = opt || {}; if (!ready()) return [];
        var rr = CHAR.mode === 'rerank', nm = opt.nm || norm(text, opt.env), F = feats(nm.ph, opt.ctx, CHAR.mode !== 'index'), out = scoreQ(F, opt.exclude, Math.max(rr ? CHAR.m : 0, 2 * (opt.k || 9), opt.keep || 0));
        out.sort(function (a, b) { return b.score - a.score; });
        var k = opt.k || 9, ss = selfScore(F);
        if (rr) {          // Dice of char grams over the best word candidates, scaled to the query's own word self-score
            out = out.slice(0, CHAR.m); var QG = cgrams(nm.ph), nq = Object.keys(QG).length, CG = IX.cg || (IX.cg = {});
            out.forEach(function (o) { var G = CG[o.i] || (CG[o.i] = cgrams(o.row.ph)), c = 0, ng = 0; for (var g in G) { ng++; if (QG[g]) c++; } o.score += CHAR.lam * ss * (2 * c / Math.max(1, nq + ng)); });
            out.sort(function (a, b) { return b.score - a.score; }); ss *= 1 + CHAR.lam;
        }
        out = out.slice(0, Math.max(k, opt.keep || 0));
        out.forEach(function (o) { o.sim = o.score / ss; });
        return out;
    }

    // ------------------------------------------------------------------ the reading
    function vote(nb, key, k) {
        var V = {}, tot = 0; nb.slice(0, k).forEach(function (o, r) { var w = o.score * (1 / (1 + 0.15 * r)) * (SRCW[o.row.s || 'x'] != null ? SRCW[o.row.s || 'x'] : 1), lab = key(o.row); if (lab == null) return; V[lab] = (V[lab] || 0) + w; tot += w; });
        var ks = Object.keys(V).sort(function (a, b) { return V[b] - V[a]; });
        return { top: ks[0] || null, second: ks[1] || null, share: ks.length ? V[ks[0]] / tot : 0, margin: ks.length ? (V[ks[0]] - (V[ks[1]] || 0)) / tot : 0, V: V };
    }
    // the encyclopedia articles the neighbours' answers point at (corpus gold_ids): [[id, share], ...] best first
    function goldVote(nb, k) {
        var V = {}, tot = 0; nb.slice(0, k).forEach(function (o, r) { if (!o.row.g) return; var w = o.score * (1 / (1 + 0.15 * r)); o.row.g.forEach(function (id, n) { var w2 = w / (1 + 0.5 * n); V[id] = (V[id] || 0) + w2; tot += w2; }); });
        return Object.keys(V).sort(function (a, b) { return V[b] - V[a]; }).slice(0, 5).map(function (id) { return [id, +(V[id] / tot).toFixed(3)]; });
    }
    function slotTypes(slots) { return slots.map(function (s) { return s.t; }); }
    // a neighbour's proven wording with THIS utterance's slots: the slot types must line up (same multiset; positional when same order)
    var SUB_TYPES = { PART: 1, COL: 1, FIN: 1, PAT: 1, NUMS: 1, SPON: 1, REL: 1, OBJ: 1, N: 1, LAYER: 1 };
    function rewrite(row, qslots) {
        var ns = row.slots || [], byT = {}, used = {}; if (!row.text) return null;
        var a = slotTypes(ns).filter(function (t) { return SUB_TYPES[t]; }).sort().join(','), b = slotTypes(qslots).filter(function (t) { return SUB_TYPES[t]; }).sort().join(',');
        if (a !== b) return null;
        qslots.forEach(function (s) { (byT[s.t] = byT[s.t] || []).push(s); });
        var out = row.text, ok = true;
        // row.slots carry [start, end) offsets into row.text (the neighbour's FIXED text)
        var reps = ns.map(function (s) { var q = (byT[s.t] || [])[used[s.t] = (used[s.t] || 0)]; used[s.t]++; if (!q) { ok = false; return null; } return { at: s.at, end: s.end, v: q.t === 'PART' || q.t === 'COL' || q.t === 'FIN' || q.t === 'PAT' ? q.v : q.s }; });
        if (!ok) return null;
        reps.sort(function (x, y) { return y.at - x.at; }).forEach(function (r) { out = out.slice(0, r.at) + r.v + out.slice(r.end); });
        return out;
    }
    var WANTS = ['change', 'answer', 'ask', 'nothing', 'undo', 'redo'];
    function read(text, env, ctx) {
        ctx = ctx || {}; if (!ready()) return null;
        var prev = ctx.prev != null ? ctx.prev : (env && env.inConvo ? PREV[PREV.length - 1] : null);
        var nm = norm(text, env), c2 = { convo: !!(ctx.convo || (env && env.inConvo) || prev), last: !!(ctx.last || (env && env.last)), pp: prev ? norm(prev, env).ph : '' };
        var nb = neighbours(text, { nm: nm, ctx: c2, k: ctx.k || 9, keep: 40, exclude: ctx.exclude });
        if (!nb.length) return { want: null, confidence: 0, neighbours: [], text: null, frame: null };
        var K = ctx.k || 9, va = vote(nb, function (r) { return r.want; }, K), vs = vote(nb, function (r) { return r.want === va.top ? r.shape : null; }, K);
        var sim = Math.min(1, nb[0].sim), conf = +(va.margin * Math.sqrt(sim)).toFixed(3);
        var txt = null, src = null;
        if (va.top === 'change' || va.top === 'undo' || va.top === 'redo') {
            for (var i = 0; i < nb.length && !txt; i++) { var r = nb[i].row; if (!r.ok || r.want !== va.top) continue; var t2 = rewrite(r, nm.slots); if (t2 && cuesOf(t2) === cuesOf(nm.raw || nm.fixed) && !/[nqr]/.test(cuesOf(nm.raw || nm.fixed))) { txt = t2; src = r.id; } }
        }
        var fr = toFrame(va.top, vs.top, nm, text, env), golds = goldVote(nb, 15);
        if (!txt && ctx.gen !== false) { txt = gen(fr, nm, vs.top, env); if (txt) src = 'gen'; }
        return { want: va.top, shape: vs.top, confidence: conf, margin: +va.margin.toFixed(3), share: +va.share.toFixed(3), sim: +sim.toFixed(3), text: txt, src: src, golds: golds, fixed: nm.fixed, raw: nm.raw, ph: nm.ph, slots: nm.slots,
            neighbours: nb.slice(0, 5).map(function (o) { return { id: o.row.id, want: o.row.want, shape: o.row.shape, score: +o.score.toFixed(2), sim: +o.sim.toFixed(3) }; }), frame: fr };
    }
    // a canonical sentence for a frame (the plainest wording the offline reader is known to read): used when no neighbour's wording fits the slots
    function whereOf(T) {
        if (!T) return null;
        if (T.kind === 'part') { var a = (T.parts || []).slice(); if (a.indexOf('left side') !== -1 && a.indexOf('right side') !== -1) { a = a.filter(function (p) { return p !== 'left side' && p !== 'right side'; }); a.push('both sides'); }
            if (a.indexOf('front bumper') !== -1 && a.indexOf('rear bumper') !== -1) { a = a.filter(function (p) { return !/bumper$/.test(p); }); a.push('both bumpers'); }
            return a.length ? 'the ' + (a.length > 1 ? a.slice(0, -1).join(', the ') + ' and the ' + a[a.length - 1] : a[0]) : null; }
        if (T.kind === 'layer') return 'the ' + (T.layers || []).join(' and ') + ' layer';
        if (T.kind === 'element') return T.element === 'numbers' ? 'the numbers' : T.element === 'sponsors' ? 'the logos' : 'the stripes';
        if (T.kind === 'body') return 'the whole car';
        if (T.kind === 'zone') return 'it';
        return null;
    }
    var NEG_CUE = /\b(?:don't|dont|do not|never|make sure|without|except|apart from|other than|besides|excluding|save for|but not|leave out)\b|\bnot (?:on|the|my|to|in|for)\b/, ADV_CUE = /\b(?:how (?:can|do|would|should|to|does)|if i|what if|steps to|brainstorm|ideas? (?:for|on)|suggest|should i|can i|could i|would it|is it|does it|will it|explain|tell me)\b/, PLACE_CUE = /\b(?:behind|under(?:neath)?|backing|background|around|panel|upper|lower|top half|bottom half|section|edge|line|band|stripe)\b/, Q_CUE = /\?|(?:^|[.!;:] ?)(?:is|are|does|do|can|could|would|will|should|why|what|how|which|where|when)\b/, REJ_CUE = /\bnot (?:that|this|quite|it|the right)\b|\bwrong\b|\b(?:everything|all) else\b/, SAMPLE_CUE = /\b(?:from (?:the|my|our|it|its|that)|sample|pull (?:the|it)|eyedrop|exact (?:same|match)|match(?:es|ing)? (?:the|my|our))\b/;
    function cuesOf(t) { t = String(t || ''); return (KEEP_CUE.test(t) ? 'k' : '') + (NEG_CUE.test(t) ? 'n' : '') + (Q_CUE.test(t) ? 'q' : '') + (REJ_CUE.test(t) ? 'r' : ''); }
    function gen(F, nm, shape, env) {
        if (!F) return null;
        var fx0 = nm.raw || nm.fixed || ''; if (NEG_CUE.test(fx0) || Q_CUE.test(fx0) || SAMPLE_CUE.test(fx0) || REJ_CUE.test(fx0) || ADV_CUE.test(fx0) || PLACE_CUE.test(fx0)) return null;          // a protect / question / sample-a-colour turn is never re-worded into a plain edit
        var ty = {}; nm.slots.forEach(function (s0) { ty[s0.t] = (ty[s0.t] || 0) + 1; }); if (ty.LAYER && ty.PART) return null; if (ty.PAT && ty.COL) return null; if (ty.OBJ) return null; if ((ty.COL || 0) >= 2 && !ty.PAT && !/gradient|stripe/.test(String(shape || ''))) return null;
        if (KEEP_CUE.test(fx0)) { var kr = null; try { kr = W.SpbIntentFrame ? W.SpbIntentFrame.read(fx0, env) : null; } catch (eK) {} if (!kr || !((kr.keep.parts || []).length || (kr.keep.elements || []).length)) return null; }          // a protect-something request whose protected thing the reader cannot name is not re-worded          // two colours over two parts: which goes where is not guessed          // an object the reader has no part for (bed, mirror, shield...) is never guessed onto a part
        if (F.act === 'undo') return 'undo that'; if (F.act === 'redo') return 'redo';
        if (F.act !== 'change' || !(F.ops || []).length) return null;
        var op = F.ops[0], L = op.look || {}, T = op.target || {}, where = whereOf(T), sp = String(shape || ''); if (!where) return null;
        var cols = nm.slots.filter(function (s) { return s.t === 'COL'; }).map(function (s) { return s.v; }), col = L.colour ? L.colour.word : null;
        var fin = L.finish && L.finish.family && L.finish.family !== 'carbon' ? L.finish.family : null, pat = L.pattern ? L.pattern.concept : null;
        var keepP = (F.keep || []).filter(function (k) { return k.kind === 'part'; }).map(function (k) { return k.parts[0]; }), keepTxt = keepP.length ? (T.kind === 'body' ? ' except ' : ' but leave ') + whereOf({ kind: 'part', parts: keepP }) : '';
        if (op.verb === 'gradient' && cols.length >= 2) return 'fade ' + where + ' from ' + cols[0] + ' to ' + cols[1];
        if (op.verb === 'stripe' && T.kind === 'part') return 'add a ' + (col ? col + ' ' : '') + 'stripe on ' + where;
        if (op.verb === 'outline' && T.kind !== 'body') return 'outline ' + where + (col ? ' in ' + col : '');
        if (op.relative && T.kind === 'zone') { var rs = nm.slots.filter(function (s) { return s.t === 'REL'; })[0]; if (!rs) return null; var tail = nm.fixed.slice(rs.at).split(' ').slice(0, rs.s.split(' ').length + (/(?:^| )(?:less|more)$/.test(rs.s) ? 1 : 0)).join(' '); return 'make it ' + tail; }
        if (T.kind === 'zone') { if (/propagat/.test(sp)) return null; if (col || fin) return 'make it ' + [fin, col].filter(Boolean).join(' '); return null; }
        if (/f_propagate/.test(sp) && T.kind === 'part' && !col && !fin && !pat) return 'do the same on ' + where;
        if (/f_correction/.test(sp) && T.kind === 'part' && !col && !fin && !pat) return 'no, ' + where + ' instead';
        if (pat && !col && !fin) return pat === 'carbon fiber' ? 'give ' + where + ' a carbon fiber look' + keepTxt : 'put ' + pat + ' on ' + where + keepTxt;
        if (L.finish && L.finish.keep_colour && fin && !col) return 'make ' + where + ' ' + fin + ' but keep the colour' + keepTxt;
        var look = [fin, col].filter(Boolean).join(' '); if (!look) return null;
        return 'make ' + where + ' ' + look + keepTxt;
    }

    // ------------------------------------------------------------------ skeleton + slots -> an SpbIntentFrame v1 frame
    var KEEP_CUE = /\b(?:keep|leave|leaving|except|apart from|other than|but not|not the|don't touch|do not touch|without touching|stays?|untouched|alone|as (?:it|they) (?:is|are))\b/;
    var SPEC_CUE = /\b(?:keep (?:the |my )?colou?rs?|same colou?rs?|colou?rs? (?:stay|the same)|only the (?:shine|finish|spec)|just the (?:shine|finish|spec)|spec only|no colou?r change|don't change the colou?r)\b/;
    var WHOLE_CUE = /\b(?:whole|entire|everything(?! else)|all over|the car|the body|my car|full car|all of it|base colou?r|the rest)\b/;
    function toFrame(want, shape, nm, text, env) {
        var F = { v: 1, act: 'nothing', ops: [], keep: [], decals: 'protect', missing: [], alts: [], said: String(text || '').slice(0, 600), producer: 'knn' };
        if (!want) return F;
        if (want === 'answer') { F.act = 'answer'; F.question = { text: F.said.slice(0, 200) }; return F; }
        if (want === 'ask') { F.act = 'ask_back'; F.missing = ['what']; return F; }
        if (want === 'nothing') return F;
        if (want === 'undo' || want === 'redo') { F.act = want; return F; }
        F.act = 'change';
        var IF = W.SpbIntentFrame, rd = null; try { rd = IF ? IF.read(nm.fixed, env) : null; } catch (e) { rd = null; }
        var fx = nm.fixed, keepParts = rd ? rd.keep.parts : [], keepEls = rd ? rd.keep.elements : [];
        var parts = [], cols = [], fin = null, pat = null, layers = [], els = [], rel = null, objs = [];
        nm.slots.forEach(function (s) {
            if (s.t === 'PART') { if (s.parts.some(function (p) { return keepParts.indexOf(p) !== -1; })) return; s.parts.forEach(function (p) { if (parts.indexOf(p) === -1) parts.push(p); }); }
            else if (s.t === 'COL') cols.push({ word: s.v, hex: s.hex || null });
            else if (s.t === 'FIN') fin = fin || s;
            else if (s.t === 'PAT') pat = pat || s;
            else if (s.t === 'LAYER') layers.push(s.v);
            else if (s.t === 'NUMS' && keepEls.indexOf('numbers') === -1) els.push('numbers');
            else if (s.t === 'SPON' && keepEls.indexOf('sponsors') === -1) els.push('sponsors');
            else if (s.t === 'REL') rel = rel || s.v;
            else if (s.t === 'OBJ') objs.push(s.v);
        });
        if (rd && rd.parts && rd.parts.length) rd.parts.forEach(function (p) { if (keepParts.indexOf(p) === -1 && parts.indexOf(p) === -1) parts.push(p); });
        var look = {}, sp = String(shape || '');
        if (cols.length > 1 && /grad/.test(sp)) look.gradient = { stops: cols.map(function (c) { return c.hex || c.word; }) };
        else if (cols.length) look.colour = cols[0];
        if (fin) look.finish = { family: fin.v, keep_colour: SPEC_CUE.test(fx) || (!cols.length && /spec/.test(sp)) || undefined };
        if (pat) { if (pat.cls === 'carbon') look.finish = look.finish || { family: 'carbon' }; look.pattern = { concept: pat.v }; }
        var verb = /grad/.test(sp) ? 'gradient' : /stripe/.test(sp) ? 'stripe' : /outline/.test(sp) ? 'outline' : /copy/.test(sp) ? 'copy_look' : (rel ? 'adjust' : (look.colour ? 'recolour' : (look.pattern ? 'pattern' : 'refinish')));
        var tgt;
        if (layers.length) tgt = { kind: 'layer', layers: layers };
        else if (parts.length) tgt = { kind: 'part', parts: parts };
        else if (els.length && !WHOLE_CUE.test(fx)) tgt = { kind: 'element', element: els[0] };
        else if (objs.length && !WHOLE_CUE.test(fx)) tgt = { kind: 'object', object: objs[0] };
        else if (/ref|follow/.test(sp) || (!WHOLE_CUE.test(fx) && env && env.last)) tgt = { kind: 'zone', ref: 'last_target' };
        else if (WHOLE_CUE.test(fx) || /:body/.test(sp)) tgt = { kind: 'body' };
        else { F.missing.push('target'); tgt = { kind: 'zone', ref: 'last_target' }; }
        var op = { verb: verb, target: tgt, look: look };
        if (rel) op.relative = { prop: /dark|light|bright|pale|deep|dull/.test(rel) ? 'lightness' : /thin|thick|wid|narrow|skinn|fat/.test(rel) ? 'width' : /fine|tight|coarse|loose|big|small|large/.test(rel) ? 'scale' : /shin|gloss|flat|matt/.test(rel) ? 'gloss' : 'strength', dir: /dark|deep|thick|wid|fat|big|large|coarse|loose|shin|gloss|more|strong|bold|rich/.test(rel) ? 1 : -1 };
        if (tgt.kind === 'body' && keepParts.length) op.except = [{ kind: 'part', parts: keepParts.slice() }];
        F.ops.push(op);
        F.keep = keepParts.map(function (p) { return { kind: 'part', parts: [p] }; }).concat(keepEls.map(function (e) { return { kind: 'element', element: e }; }));
        if (!look.colour && !look.finish && !look.pattern && !look.gradient && !rel) F.missing.push('what');
        return F;
    }

    // ------------------------------------------------------------------ hybrid: the regex reader keeps its confident answers
    function weak(r, text, env) {          // -> null (keep r) or the reason the kNN may take over
        if (!r) return 'none';
        if (r.cls === 'ASK' || r.cls === 'PREFILL') return r.list ? null : 'ask';
        if (r.cls === 'DECLINE' || r.cls === 'ONLINE') return 'decline';
        if (r.cls === 'DO' && !(r.steps || []).length) return 'nothing';
        if (r.cls === 'DO' && (r.steps || []).some(function (st) { return st && st.what && (st.what.k === 'body' || st.what.k === 'main'); }) && !WHOLE_CUE.test(String(text || '').toLowerCase())) return 'whole';
        if (r.cls === 'ANSWER' || r.cls === 'LOCAL' || r.cls === 'OFFTOPIC') return r.answer && r.score != null && r.score < 4 ? 'answer-weak' : 'answer';
        if (!r.cls) return 'none';
        return null;
    }
    var TH = { change: 0.30, answer_change: 2, whole: 0.45, decline: 0.40, nothing: 0.45, answer: 0.5, veto: 2, spell: 0.2, follow: 0.3, gold: 0.35, sim: 0.4 };          // veto >= 1 = off
    var PREV = [];          // the buyer's earlier turns in THIS chat (follow-ups are read with the turn before them)
    function note(text, env) { if (!(env && (env.inConvo || env.last))) PREV = []; var t = String(text || ''); if (PREV[PREV.length - 1] !== t) PREV.push(t); if (PREV.length > 6) PREV.shift(); }          // the helper may read one turn twice (claim + route): keep it once
    // the rewrite must not invent what the buyer did not say: its parts / elements / layers / colours come from this turn (or, for a follow-up, the turn before)
    function verify(r2, k, prev, env) {
        var nm = { slots: k.slots || [] }, fx = k.fixed || '', q = { parts: [], els: {}, fams: {}, layers: {} }, keepP = [];
        var keepE = []; try { var rd = W.SpbIntentFrame ? W.SpbIntentFrame.read(k.raw || fx, env) : null; if (rd) { keepP = rd.keep.parts || []; keepE = rd.keep.elements || []; } } catch (e) {}
        nm.slots.forEach(function (s) { if (s.t === 'PART') (s.parts || []).forEach(function (p) { if (q.parts.indexOf(p) === -1) q.parts.push(p); }); if (s.t === 'NUMS') q.els.numbers = 1; if (s.t === 'SPON') q.els.sponsors = 1; if (s.t === 'COL' && s.fam) q.fams[s.fam] = 1; if (s.t === 'LAYER') q.layers[s.v] = 1; });
        var pp = []; if (prev) { try { norm(prev, env).slots.forEach(function (s) { if (s.t === 'PART') (s.parts || []).forEach(function (p) { pp.push(p); }); }); } catch (e2) {} }
        var rel = nm.slots.some(function (s) { return s.t === 'REL'; }), whole = WHOLE_CUE.test(fx), anyCol = Object.keys(q.fams).length;
        var bad = null, wholeish = /\b(?:everything|entire|whole|the rest|all over|whole car|all of (?:it|the car))\b/.test(k.raw || fx), anyBody = (r2.steps || []).some(function (st) { return st && st.what && (st.what.k === 'body' || st.what.k === 'main'); });
        if (wholeish && !anyBody && q.parts.length) return 'whole-vs-parts';          // "everything ... (but X)" read as only some parts: the exception was lost
        (r2.steps || []).forEach(function (st) {
            if (bad || !st || !st.what) return; var w = st.what;
            if (w.k === 'part') { var p = String(w.part || '').split('@')[0]; if (keepP.indexOf(p) !== -1) bad = 'kept:' + p; else if (q.parts.length ? q.parts.indexOf(p) === -1 : (!whole && pp.indexOf(p) === -1)) bad = 'part:' + p; }          // a part the buyer protected is never touched
            else if (w.k === 'body' || w.k === 'main') { if (!whole && (q.parts.length || !prev)) bad = 'body'; }
            else if (w.k === 'numbers' || w.k === 'sponsors') { if (keepE.indexOf(w.k) !== -1) bad = 'kept:' + w.k; else if (!q.els[w.k] && !q.layers.Numbers && !q.layers.Logos) bad = w.k; }
            else if (w.k === 'layer') { if (!(w.layers || []).every(function (L) { return q.layers[L]; }) && !whole) bad = 'layer'; }
            if (!bad && st.colour && st.act === 'recolour' && anyCol) { var nmw = String(st.colour.name || '').toLowerCase().split(' ').pop(), f = COL[nmw] ? COL[nmw][1] : null; if (f && !q.fams[f]) bad = 'colour:' + nmw; }
            if (!bad && st.colour && !anyCol && !rel && st.act === 'recolour' && !(st.colour.hex && /^#/.test(String(st.colour.name || '')))) bad = 'colour-invented';
        });
        return bad;
    }
    // results this module builds itself (same shapes as js/spb-offline-answer.js local() / answered())
    function ack(text) { var A = { id: 'local.knn_ack', title: 'Okay', text: text || 'Okay, nothing changed. Tell me what to change next.', actions: [], how: [], faq: '', level: '', shot: null }; return { cls: 'ANSWER', via: 'knn', why: 'knn-ack', local: true, hits: [{ id: A.id, title: A.title, score: 0 }], answer: A }; }
    function searchAnswer(text, golds) {          // the encyclopedia search, re-ranked by the articles the kNN neighbours' answers used (golds)
        var OA = W.SpbOfflineAnswer; if (!OA || !OA.search || !OA.answerOf) return null;
        var hs = []; try { hs = OA.search(String(text), golds && golds.length ? 25 : 6) || []; } catch (e) { hs = []; } if (!hs.length || !(hs[0].score >= (golds && golds.length ? 3 : 6))) return null;
        if (golds && golds.length) { var GS = {}, top = hs[0].score; golds.forEach(function (g) { GS[g[0]] = g[1]; }); hs = hs.map(function (h) { return { h: h, s: h.score + 1.5 * top * (GS[h.id] || 0) }; }).sort(function (a, b) { return b.s - a.s; }).map(function (x) { return x.h; }); }
        var A = null; try { A = OA.answerOf(hs[0], String(text)); } catch (e2) { A = null; } if (!A) return null;
        return { cls: 'ANSWER', via: 'knn', why: 'knn-answer', hits: hs.slice(0, 3).map(function (h) { return { id: h.id, title: h.doc && h.doc.a ? h.doc.a.title : h.id, score: Math.round(h.score * 10) / 10 }; }), answer: A, qtext: String(text).slice(0, 200) };
    }
    function askBack(text) { return { cls: 'ASK', via: 'knn', why: 'knn-ask', ask: { text: 'I want to get this right: which part should change, and to what colour or finish?', chips: ['Show me the parts', 'Show colours'] }, steps: [] }; }
    // a short follow-up said in full, from the turn before: "and the spoiler" after "chrome roof" -> "chrome spoiler"; "darker" after "make the hood blue" -> "make the hood darker"
    var FILLER = /^(?:it|its|make|do|and|also|now|then|please|plz|a|an|the|bit|little|touch|tad|way|much|lot|slightly|more|less|too|same|instead|one|ok|okay|yes|yeah|but|just|go|try|that|this|on|to|with|in)$/;
    function followText(k, prev, env) {
        if (!prev) return null;
        var cur = k.slots || [], fx = k.fixed || '', pn = norm(prev, env), pfx = pn.fixed || '', pParts = pn.slots.filter(function (x) { return x.t === 'PART'; });
        var has = function (sl, t) { return sl.some(function (x) { return x.t === t; }); };
        if (!pParts.length || has(cur, 'OBJ') || has(cur, 'LAYER') || has(cur, 'NUMS') || has(cur, 'SPON')) return null;
        var rest = fx; cur.slice().sort(function (a, b) { return b.at - a.at; }).forEach(function (x) { rest = rest.slice(0, x.at) + ' ' + rest.slice(x.end); });
        if (rest.split(/\s+/).filter(Boolean).some(function (w) { return !FILLER.test(w); })) return null;          // only slots + filler words: anything else is not a bare follow-up
        var cParts = cur.filter(function (x) { return x.t === 'PART'; }), look = has(cur, 'COL') || has(cur, 'FIN') || has(cur, 'PAT'), rel = has(cur, 'REL');
        if (cParts.length && !look && !rel) {          // same look, other part
            if (!(has(pn.slots, 'COL') || has(pn.slots, 'FIN') || has(pn.slots, 'PAT'))) return null;
            var np = cParts.map(function (x) { return fx.slice(x.at, x.end); }).join(' and '), out = pfx;
            pParts.slice().sort(function (a, b) { return b.at - a.at; }).forEach(function (x, n) { out = out.slice(0, x.at) + (n === pParts.length - 1 ? np : '') + out.slice(x.end); });
            return out.replace(/\s+and\s+(?=and\b|$)/g, ' ').replace(/\s+/g, ' ').trim();
        }
        if (!cParts.length && (look || rel)) {          // other look, same part(s)
            var body = fx.replace(/^(?:(?:and|also|now|then|ok|okay|but|just|no)\s+)*(?:make it\s+|make\s+|do it\s+|it\s+)?/, '');
            return 'make the ' + pParts.map(function (x) { return pfx.slice(x.at, x.end).replace(/^the /, ''); }).join(' and ') + ' ' + body;
        }
        return null;
    }
    function hybrid(text, env, r, route0, opt) {
        if (!on() || !ready() || typeof route0 !== 'function') return r;
        opt = opt || {}; if (opt.prev == null) { opt.prev = null; if (env && (env.inConvo || env.last)) for (var pi = PREV.length - 1; pi >= 0 && !opt.prev; pi--) if (PREV[pi] !== String(text)) opt.prev = PREV[pi]; } note(text, env);
        var cfg = W.SPB_KNN_CFG || {}, th = Object.assign({}, TH, cfg.th || {}, opt.th || {});
        var dbg = function (o, res) { if (cfg.debug) { try { console.log('KNNDBG ' + JSON.stringify(o)); } catch (e) {} } return res || r; };
        var why = cfg.always ? (weak(r, text, env) || 'always') : weak(r, text, env);
        if (!why && !(r && r.cls === 'DO' && th.veto < 1)) return dbg({ t: String(text).slice(0, 60), keep: 1 });
        var k = read(text, env, { exclude: opt.exclude, prev: opt.prev }); if (!k || !k.want) return dbg({ t: String(text).slice(0, 60), why: why, k: null });
        var info = { t: String(text).slice(0, 60), why: why || 'do', want: k.want, conf: k.confidence, sim: k.sim, src: k.src, said: k.text, ph: k.ph, pp: opt.prev ? 1 : 0 }; if (cfg.debug && opt.prev) info.pv = String(opt.prev).slice(0, 50);
        if (!why) {          // the regex reader made a change: only a very sure "this is not an edit" stops it
            if (k.confidence < th.veto || k.want === 'change' || k.want === 'undo' || k.want === 'redo') return r;
            var rv = k.want === 'ask' ? askBack(text) : k.want === 'nothing' ? ack() : searchAnswer(text); if (!rv) return dbg(info);
            info.took = 'veto:' + k.want; rv.knn = info; return dbg(info, rv);
        }
        if (k.want === 'nothing' && (why === 'ask' || why === 'nothing' || why === 'decline') && k.confidence >= th.nothing) { var ra = ack(); info.took = 'ack'; ra.knn = info; return dbg(info, ra); }
        if ((k.want === 'answer' || k.want === 'decline') && why === 'answer' && r && r.cls === 'ANSWER' && k.golds && k.golds.length && k.golds[0][1] >= th.gold && k.confidence >= th.answer) {          // the regex reader answered: swap the article only when the neighbours clearly point elsewhere
            var have = [r.answer && r.answer.id].concat((r.hits || []).slice(0, 3).map(function (h) { return h.id; }));
            if (have.indexOf(k.golds[0][0]) === -1) { var rg = searchAnswer(text, k.golds); if (rg && rg.answer && rg.answer.id === k.golds[0][0]) { info.took = 'gold'; info.g = k.golds[0][0]; rg.knn = info; return dbg(info, rg); } }
            return dbg(info);
        }
        if ((k.want === 'answer' || k.want === 'decline') && why === 'ask' && k.confidence >= th.answer) { var rs = searchAnswer(text, k.golds); if (rs) { info.took = 'answer'; rs.knn = info; return dbg(info, rs); } return dbg(info); }
        var hist = k.want === 'undo' || k.want === 'redo', raw0 = String(text).toLowerCase();
        if (!hist && (ADV_CUE.test(raw0) || /\?\s*$/.test(raw0))) return dbg(info);          // a question / advice request is never turned into an edit here
        var t0 = why === 'whole' ? th.whole : why === 'answer' || why === 'answer-weak' ? th.answer_change : why === 'decline' ? th.decline : th.change;
        if (k.want !== 'change' && !hist) return dbg(info);
        var tryText = function (txt, how) {          // re-read a rewrite with the regex reader; keep it only when it is a real, verified edit
            if (!txt || txt === String(text).toLowerCase()) return null;
            var r2 = null; try { r2 = route0(txt, env); } catch (e) { r2 = null; }
            info[how] = (r2 ? r2.cls + (r2.pass ? ':' + r2.pass : '') + '/' + (r2.steps || []).length : 'null') + ' <' + String(txt).slice(0, 50);
            if (hist) return r2 && /^(?:undo|redo)/.test(r2.pass || '') ? r2 : null;
            if (!r2 || r2.cls !== 'DO' || !(r2.steps || []).length) return null;
            if (why !== 'whole' && weak(r2, txt, env) === 'whole' && !WHOLE_CUE.test(k.fixed)) { info[how] += ' whole'; return null; }
            var vf = verify(r2, k, opt.prev, env); if (vf) { info[how] += ' ' + vf; return null; }
            return r2;
        };
        var r2 = null, fx = k.fixed || '';
        // 1. the same words with the typos / slang fixed
        var sp0 = spellFix(text); if (!hist && k.confidence >= th.spell && sp0.toLowerCase() !== raw0 && !NEG_CUE.test(raw0) && !Q_CUE.test(raw0)) { r2 = tryText(sp0, 'spell'); if (r2) info.took = 'spell'; }
        // 2. a bare follow-up said in full from the turn before
        if (!r2 && !hist && opt.prev && k.confidence >= th.follow) { r2 = tryText(followText(k, opt.prev, env), 'follow'); if (r2) info.took = 'follow'; }
        // 3. the neighbours' wording (proven template or canonical sentence)
        if (!r2 && k.confidence >= t0 && (hist || k.sim >= th.sim)) { r2 = tryText(k.text, 'r2'); if (r2) info.took = 'rewrite'; }          // measured (train+p1+p2): rewrites below sim 0.4 were right 72% and held 1 of 3 new harms; 0.4-0.55 85%, above 94%
        if (!r2) return dbg(info);
        r2.knn = info; return dbg(info, r2);
    }

    // W9ARB-KNN 2026-10-09 (lane W9-ARB; kill: window.SPB_W9ARB_OFF or SPB_KNN_NOW8 = '0'): the NOW8 shorthand pass as a TEXT -> TEXT function so the frame reader (spb-intent-offline-frame.js frameOf / syn)
    // lexes "make r door yel", "pls chng car 2 grn", "bod #0B3D91", "carbon on lip n diffuser" the way the neighbours already read them. Only whole word tokens change; punctuation / spacing / hex codes are kept.
    var A9_EXTRA = { chng: 'change', chg: 'change', bod: 'body', bdy: 'body', lwr: 'lower', upr: 'upper', desat: 'desaturate', sat: 'saturation', mirrs: 'mirrors', wite: 'white', blak: 'black', pnk: 'pink', gld: 'gold', clr: 'colour', col: 'colour', colr: 'colour', veh: 'vehicle', btm: 'bottom', bttm: 'bottom' };
    function abbr(text) {
        try {
            if (W.SPB_W9ARB_OFF || !w9abbrOn() || typeof text !== 'string' || text.length > 500) return text;
            var parts = text.match(/[A-Za-z0-9#'_]+|[^A-Za-z0-9#'_\s]+|\s+/g) || [], idx = [], words = [], i;
            for (i = 0; i < parts.length; i++) if (/^[A-Za-z0-9#'_]+$/.test(parts[i])) { idx.push(i); words.push(parts[i]); }
            var low = words.map(function (w) { return /^#?[0-9a-f]{3,8}$/i.test(w) && /\d|^#/.test(w) ? w : w.toLowerCase(); }), out = [], changed = false;
            for (i = 0; i < low.length; i++) {
                var w = low[i], one = w;
                if (/^#/.test(w) || /^[0-9a-f]{6}$/i.test(w) && /\d/.test(w)) { out.push(words[i]); continue; }
                if (A9_EXTRA.hasOwnProperty(w) && !(w === 'n' && !(i > 0 && i < low.length - 1)) && !(w === 'col' || w === 'sat')) one = A9_EXTRA[w];
                else if (w === '2' && /^(?:be|the|a|an|my|our|black|white|red|blue|green|yellow|orange|pink|purple|gold|silver|grey|gray|grn|blk|wht|orng|yel|chrome|candy|matte|satin|gloss)$/.test(low[i + 1] || '') && /^(?:car|it|roof|hood|doors?|sides?|trunk|bumper|body|them|that|this|all|everything|\w+)$/.test(low[i - 1] || '')) one = 'to';
                else {
                    one = null;
                    var tk = now8Tokens([w]);
                    if (/^(?:r|l|rt|lt)$/.test(w) && /^(?:side|sides|door|doors|fender|fenders|quarter|flank|panel|panels|mirror|mirrors|wing|rocker|skirt|half|one)$/.test(low[i + 1] || '')) one = (w === 'r' || w === 'rt') ? 'right' : 'left';
                    else if (tk.length === 1 && tk[0] !== w && ABBR.hasOwnProperty(w)) one = tk[0];
                    else if ((w === 'lip' || w === 'splitter') && low[i - 1] !== 'front') one = 'front bumper';
                    else if (w === 'diffuser' && low[i - 1] !== 'rear' && low[i - 1] !== 'back') one = 'rear bumper';
                    else if (w === 'starboard') one = 'right side'; else if (w === 'port' && (/^(?:side|sides|door|doors|fender|fenders|mirror|mirrors)$/.test(low[i + 1] || '') || (/^(?:and|n)$/.test(low[i + 1] || '') && low[i + 2] === 'starboard'))) one = (/^(?:side|sides|door|doors|fender|fenders|mirror|mirrors)$/.test(low[i + 1] || '') ? 'left' : 'left side');
                    else one = w;
                }
                if (one !== w) { changed = true; out.push(one); } else out.push(words[i]);
            }
            if (!changed) return text;
            var r = parts.slice(); for (i = 0; i < idx.length; i++) r[idx[i]] = out[i];
            return r.join('');
        } catch (e) { return text; }
    }
    W.SpbIntentKnn = { abbr: abbr, VERSION: VERSION, warm: warm, _follow: followText, _reset: function () { IX = null; BUILD = null; }, gen: gen, note: note, _prev: function () { return PREV.slice(); }, on: on, install: install, ready: ready, norm: norm, prep: prep, feats: feats, neighbours: neighbours, read: read, rewrite: rewrite, toFrame: toFrame, hybrid: hybrid, weak: weak, TH: TH, _ix: function () { return IX; } };
    // in the app: warm the index in idle slices a moment after load (no long task on the main thread)
    try { if (W.document && W.SPB_KNN_DATA && on()) setTimeout(function () { warm(); }, 2500); } catch (eW) {}
})();
