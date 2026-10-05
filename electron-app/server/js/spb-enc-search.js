/* SPB ENCYCLOPEDIA SEARCH (ENC_SEARCH_LAB 2026-10-05): ONE ranker for every encyclopedia search.
   Used by the offline helper (js/spb-offline-answer.js search()), the reader's search box (js/spb-encyclopedia.js search())
   and mirrored line for line in Python by server_routes/encyclopedia_routes.py (online grounding + MCP spb_encyclopedia).
   Parity is measured by _easy_claude_work/eval/online_ground/enc_parity.py; the benchmark lives in _easy_claude_work/search_lab/.
   Any change here MUST be made in the Python mirror too (same constants, same order of arithmetic, same tie-break).

   API (browser: window.SpbEncSearch, Node: require):
     build(docs, opts)  docs = [{ id, title, aliases[], summary, what, how[], when[], tips[], pitfalls[], controls[], faq[{q,a}], mistakes[], deep[],
                                  generated?, kind? ('article'|'help'|'control'|'term'|'finish'|'pattern'|'spec') }]
                        opts = { prefix: bool }   (prefix: the last word may be half typed - the reader's search-as-you-type)
     search(ix, text, opts) -> [{ id, i, score, cov, faq }] best first. i = index into docs, cov = share of the question's word weight
                        the article covers (unknown words count against it), faq = index of the best matching FAQ question or -1.
   Scoring = field-weighted BM25 (title, aliases, FAQ questions, summary, controls, body) + "nearest question" match against the
   title / each alias / each FAQ question + phrase and bigram boosts, then question INTENT (what is / how do I / where / why-broken)
   and the kind of article, with synonym expansion and typo repair (edit distance 1-2 against the index vocabulary).
   Easy mode is hidden (owner rule): docs that name it are never indexed. ES5, zero dependencies. */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.SpbEncSearch = factory();
})(typeof window !== 'undefined' ? window : this, function () {
    'use strict';
    var VERSION = '2026-10-05.8';
    // ------------------------------------------------------------------ words (shared with the Python mirror)
    var STOP = {};
    ('a an the is are was were be been am do does did doing done i me my mine we our you your yours it its this that these those there here to of in on at for by from with and or but if so as ' +
        'what whats wat wht how hw why where wheres when which who whos whom can could would should will shall may might must im ive id dont doesnt didnt cant wont isnt arent wasnt ' +
        'about tell explain please pls plz just really very much some any thing things one also too get got gets getting have has had having need want wanna gonna like know ' +
        'thanks thank hi hey hello ok okay yes no not nothing something anything difference differences between vs versus compared compare another u ur ya yo lol help ' +
        'way actually actualy kinda sorta still now then mean means meaning wtf omg bruh dude guys')
        .split(' ').forEach(function (w) { if (w) STOP[w] = 1; });
    STOP.id = 0;
    var SYN = { colour: 'color', colours: 'colors', coloured: 'colored', colouring: 'coloring', recolour: 'recolor', grey: 'gray', metalic: 'metallic', metalics: 'metallic', aluminium: 'aluminum', licence: 'license',
        centre: 'center', favourite: 'favorite', fibre: 'fiber', liveries: 'livery', photoshop: 'photoshop', psds: 'psd', tgas: 'tga', ui: 'interface',
        game: 'iracing', sim: 'iracing', ingame: 'iracing', iracings: 'iracing', numbers: 'number', nums: 'number', num: 'number', decals: 'decal', logos: 'logo',
        chromed: 'chrome', chrom: 'chrome', shiny: 'shine', shinier: 'shine', shininess: 'shine', glossy: 'gloss', glossier: 'gloss', flat: 'matte', mat: 'matte', mate: 'matte', speccing: 'spec', specs: 'spec',
        skin: 'paint', skins: 'paint', scheme: 'livery', schemes: 'livery', wrap: 'livery', tp: 'tradingpaints', 
        clearcoats: 'clearcoat', zones: 'zone', layers: 'layer', patterns: 'pattern', finishes: 'finish', renders: 'render', rendering: 'render',
        exprot: 'export', gradiant: 'gradient', rougness: 'roughness', zoen: 'zone', showin: 'showing', workin: 'working', randomize: 'randomise', randomise: 'randomise', rougher: 'roughness', roughest: 'roughness', smoother: 'smooth', darker: 'dark', brighter: 'bright', duller: 'dull', bigger: 'big', smaller: 'small',
        customer: 'user', cust: 'user', member: 'user', spb: 'shokker', delete: 'remove', deleting: 'remove', deleted: 'remove',
        undid: 'undo', undone: 'undo', undos: 'undo', redid: 'redo', wetter: 'wet', lit: 'lighting', pic: 'picture', pics: 'picture', pix: 'picture' };   // ROUND2: casual past tenses / slang (tune split)
    // near-synonyms: a query word also matches these (at EXP_W of its weight)
    var EXPAND = { missing: ['vanished', 'disappear', 'gone', 'lost'], vanish: ['missing', 'disappear'], disappear: ['missing', 'vanished'], gone: ['missing', 'lost', 'vanished'], wiped: ['missing', 'vanished'],
        big: ['size', 'large', 'scale'], large: ['size', 'big'], huge: ['big', 'scale', 'tiny'], tiny: ['small', 'scale', 'huge'], small: ['tiny', 'scale'], bigger: ['scale', 'size'], smaller: ['scale', 'finer', 'size'],
        size: ['big', '2048', 'scale'], shine: ['gloss', 'spec', 'shiny', 'reflective'], gloss: ['shine', 'glossy', 'clearcoat'], matte: ['flat', 'gloss', 'satin'], save: ['saving', 'project'], open: ['load', 'opening'],
        load: ['open', 'loading', 'import'], import: ['load', 'open'], broken: ['wrong', 'error'], slow: ['speed', 'performance', 'long'], crash: ['error', 'start'], start: ['begin', 'first'], begin: ['start', 'first'],
        new: ['beginner', 'first', 'start'], picture: ['image', 'photo', 'logo'], photo: ['picture', 'image'], image: ['picture', 'paint'], stamped: ['iracing', 'stamp'], stamp: ['stamped'], channel: ['channels'],
        sticker: ['decal', 'logo'], decal: ['logo', 'sponsor', 'sticker'], logo: ['sponsor', 'decal'], sponsor: ['logo', 'decal'], mirror: ['symmetry', 'flip'], flip: ['mirror'], wrong: ['different', 'broken'],
        userid: ['user', 'id'], delete: ['remove'], remove: ['delete'], erase: ['eraser', 'delete'], fade: ['gradient'], gradient: ['fade'], ombre: ['gradient', 'fade'], dark: ['black'], black: ['dark'],
        livery: ['paint', 'design'], paint: ['livery'], design: ['livery'], car: ['paint'], export: ['render', 'deploy', 'files'], install: ['export', 'deploy', 'folder'], upload: ['tradingpaints', 'upload'],
        put: ['add', 'place'], add: ['put'], place: ['put', 'add'], show: ['visible', 'appear', 'showing'], appear: ['show', 'showing'], visible: ['show', 'see'], see: ['visible', 'show', 'view'], view: ['see', 'show'],
        reload: ['refresh', 'restart'], refresh: ['reload', 'update'], restart: ['reload'], update: ['refresh', 'version'], folder: ['directory', 'path'], directory: ['folder'], path: ['folder'],
        reflective: ['shine', 'chrome', 'mirror'], polished: ['chrome', 'mirror'], rusty: ['weathered', 'wear', 'rust'], rust: ['weathered', 'wear'], worn: ['wear', 'weathered'], old: ['weathered', 'earlier', 'previous'],
        sparkle: ['flake', 'glitter', 'sparkl'], glitter: ['flake', 'sparkle'], flake: ['sparkle', 'pearl'], camouflage: ['camo'], camo: ['camouflage'], cf: ['carbon'],
        chameleon: ['shift', 'colorshoxx', 'flip'], blurry: ['smeared', 'blobby'], muddy: ['smeared', 'blobby'], blobby: ['smeared'], frozen: ['stuck'], stuck: ['frozen'], blank: ['black', 'empty'],
        hide: ['mute', 'off', 'visibility'], mute: ['hide', 'off'], disable: ['mute', 'off'], toggle: ['visibility', 'off'], copy: ['duplicate', 'clone'], duplicate: ['copy', 'clone'], clone: ['duplicate', 'copy'],
        hotkeys: ['shortcuts', 'keys'], hotkey: ['shortcut', 'keys'], keys: ['shortcuts'], picker: ['eyedropper', 'pick'], sample: ['eyedropper', 'pick'], eyedropper: ['pick', 'sample'],
        number: ['numbers'], beginner: ['first', 'start', 'new'], lost: ['missing', 'gone'], text: ['lettering', 'name'], lettering: ['text'], name: ['text'], words: ['text'], write: ['text'],
        friends: ['others', 'drivers'], others: ['drivers', 'other'], people: ['drivers', 'others'], everyone: ['others', 'drivers'], online: ['others', 'tradingpaints'], league: ['team', 'others'],
        cost: ['price', 'pay'], price: ['cost'], key: ['license', 'api'], activate: ['license', 'activation'], quick: ['fast'], faster: ['speed', 'slow'], speed: ['slow'],
        many: ['limit', 'max', 'count'], max: ['limit', 'many'], limit: ['max', 'many'], flop: ['shift', 'flip', 'chameleon'], down: ['less', 'lower', 'reduce'], lower: ['less', 'reduce'], reduce: ['less', 'lower'], less: ['reduce', 'lower'],
        sandpaper: ['rough', 'matte'], massive: ['big', 'huge', 'scale'], enormous: ['big', 'huge', 'scale'], giant: ['big', 'huge', 'scale'], gigantic: ['big', 'huge', 'scale'], reflection: ['shine', 'gloss', 'spec'], grainy: ['rough', 'grain'], lasso: ['select', 'shape', 'draw'], wet: ['gloss', 'clearcoat'], cheap: ['pop', 'boring', 'flat'], expensive: ['premium', 'pop', 'depth'] };
    function nul() { return Object.create(null); }
    function own(o) { var r = nul(); for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) r[k] = o[k]; return r; }
    STOP = own(STOP); SYN = own(SYN); EXPAND = own(EXPAND);          // no inherited keys ("constructor", "toString" are plain words here)
    var EXP_W = 0.6;
    var HID_ID = /(^|[._:])easy([._:]|$)/i, HID_TX = /\beasy[\s-]*mode\b|\bpaint[\s-]*by[\s-]*numbers\b|\bEASY\b/;
    function norm(s) {
        return String(s || '').toLowerCase().replace(/['’]/g, '').replace(/clear[\s-]+coat/g, 'clearcoat').replace(/\bget rid of\b/g, 'remove').replace(/\btrading ?paints?\b/g, 'tradingpaints')
            .replace(/\b(ctrl|control)\s*[-+ ]\s*r\b/g, 'reload').replace(/\b(ctrl|control)\s*[-+ ]\s*z\b/g, 'undo').replace(/\b(r|red) (channel|value|slider)/g, 'metallic $2').replace(/\b(g|green) (channel|value|slider)/g, 'roughness $2')
            .replace(/\b(b|blue) (channel|value|slider)/g, 'clearcoat $2').replace(/\b(a|alpha) (channel|value)/g, 'alpha $2').replace(/(\d)\s*x\s*(\d)/g, '$1 $2').replace(/\buser ?id\b/g, 'user id').replace(/\bspec ?map\b/g, 'spec map')
            .replace(/[^a-z0-9#]+/g, ' ').trim();
    }
    function stem(w) {
        if (w.length <= 3 || /^[0-9#]/.test(w)) return w;
        if (/ies$/.test(w) && w.length > 4) return w.slice(0, -3) + 'y';
        if (/(ss|us|is)$/.test(w)) return w;
        if (/(xes|ches|shes|sses)$/.test(w)) w = w.slice(0, -2);
        else if (/s$/.test(w)) w = w.slice(0, -1);
        if (/ing$/.test(w) && w.length > 5) { w = w.slice(0, -3); if (/([^aeioulsz])\1$/.test(w)) w = w.slice(0, -1); }
        else if (/ed$/.test(w) && w.length > 4) { w = w.slice(0, -2); if (/([^aeioulsz])\1$/.test(w)) w = w.slice(0, -1); }
        if (/[^aeiou]e$/.test(w) && w.length > 4) w = w.slice(0, -1);
        return w;
    }
    function word(w) { w = SYN[w] || w; return stem(w); }
    // toks(s) -> stemmed content words, stop words dropped, single letters dropped (digits kept)
    var WC = nul();          // word -> its token ('' = dropped); the same answer every time, so cache it (index build speed)
    function toks(s) {
        var out = [], L = norm(s).split(' ');
        for (var i = 0; i < L.length; i++) {
            var w = L[i]; if (!w) continue; var c = WC[w];
            if (c === undefined) { var x = SYN[w] || w; c = (STOP[x] || (x.length < 2 && !/[0-9]/.test(x))) ? '' : stem(x); WC[w] = c; }
            if (c) out.push(c);
        }
        return out;
    }
    // ------------------------------------------------------------------ fields
    // [key, weight, b]: t title, a aliases, q FAQ questions, s summary, c control labels, m mistake symptoms, b body (what, how, when, tips, pitfalls, FAQ answers, deep)
    var FIELDS = [['t', 1.8, 0.3], ['a', 3.075, 0.4], ['q', 2.326, 0.671], ['s', 0.984, 0.4], ['c', 0.938, 0.6], ['m', 0.708, 0.29], ['b', 0.28, 0.94], ['p', 1, 0.5]];   // p = the paraphrase bank's casual questions (ROUND 3; empty until js/spb-enc-qbank.js is loaded)   // tuned on DEV (search lab 2026-10-05); round 2: half-step (geometric mean) toward the DEV + casual-TUNE optimum, as are P, KIND_PRIOR and DOM_PRIOR
    var K1 = 1.2;
    var KIND_PRIOR = { article: 1, help: 1, control: 0.62, term: 0.7, finish: 0.55, pattern: 0.55, spec: 0.55 };
    // per-domain prior (id prefix before the first dot, trailing _N dropped); tuned on DEV only
    // ideas 0.7 (round 2): the 70 style-recipe cards carry ~790 broad aliases; at 1.0 they took plain how-to questions (dev 91.5 -> 87.6 top-1). 0.7 keeps 10/12 vague style asks on an ideas card (ideas_sweep.js)
    var DOM_PRIOR = { ai_copilot: 1, cars: 1.118, concepts: 0.894, finishes: 1, history: 0.894, layers: 1, patterns: 1.118, playbook: 1, preview_render: 1, recipes: 1, settings: 0.894, shokk_drop: 1.118, shortcuts: 1, spec: 0.894, spec_sculpt: 0.85, support: 1, tools: 0.894, ui_shell: 0.85, workflows: 1, zones: 1, help_howto: 1, help_topics: 1, help_support: 1, help_guide: 1, ideas: 0.7 };
    var P = {
        bm: 0.894,          // BM25 sum
        ut: 5.724,         // best title match (F of idf overlap)
        ua: 1.859,          // best alias match
        uq: 4.25,         // best FAQ question match
        beta: 1.875,      // F-beta of a unit match: recall of the question's words counts beta^2 times the unit's own precision
        ph: 1.6,          // query bigram found as a phrase in title / alias / FAQ question
        whole: 2.5,       // the whole title (>= 2 words) sits inside the question
        gen: 0.92,        // generated (help) pages
        exact: 1.007,       // multiplier when the question is exactly the title
        cg: 0,            // coverage exponent: score x cov^cg
        scale: 0.75,      // final score x 0.75: keeps the old search's score range, so the helper's answer thresholds mean the same (quantile-matched on the bench)
        xu: 5.0,          // bonus when the question and one title / alias / FAQ question are the same words
        xq: 1.265,          // share of that bonus when the identical words are a FAQ question
        iw: 1.475, ih: 1.12, iy: 1.364, ip: 0.82, iq: 1.063, iwh: 1.23,
        fk: 1, fw: 0.75,  // rank fusion with the plain channel: 1/(fk+rank) + fw/(fk+plain rank); fw 0 = main channel only
        // ROUND 3 (paraphrase bank, js/spb-enc-qbank.js): nearest casual question -> its article. key = 1/(qf+rank+1) + qw * sim^qg (sim >= qt);
        // qcw / qww / qbw = weight of char 3-4-grams / words / word pairs in the TF-IDF cosine; a top hit with sim >= qc lifts cov to sim; qs = score when only the bank matched
        qw: 0.1, qg: 1, qt: 0.3, qf: 3, qc: 0.6, qs: 4.5, qcw: 1, qww: 1, qbw: 1, qk: 0.3, qcs: 0,   // fitted on DEV + casual TUNE (qb_tune.jsonl); flat optimum, central point taken
        il: 0.6,          // ENC_READER_FIX: a tool page when the question names a look ('brushed aluminium')
        up: 2, xp: 0,     // bank questions as units: best F match x up; an identical bank question earns xp of the xu bonus
        // R4b (ENC_SEARCH_LAB): qlock = the paraphrase bank cannot move a main-channel winner whose score is >= qlock x the runner-up. The bank is a
        // tie-breaker; articles written after it have no bank questions and lost clear wins to it. Plateau 1.3-1.75 on DEV/HELD/held2/held3/casual
        // (no set drops); central 1.5 taken
        qlock: 1.5
    };
    var LFW = { t: 3, a: 2.4, s: 1.2, q: 1.4, b: 0.35, p: 0 };   // plain channel field weights (the old offline helper's)
    var LPROB = /\b(slow|fails?|failed|won'?t|wont|not|missing|vanished|error|broken|problems?|trouble|wrong|stuck|crash\w*)\b/i;
    function str(x) { return x == null ? '' : String(x); }
    function arr(x) { return Array.isArray(x) ? x : []; }
    function textOf(L, f) { var o = []; arr(L).forEach(function (x) { if (typeof x === 'string') o.push(x); else if (x && typeof x === 'object') o.push(f(x)); }); return o.join(' '); }
    function hiddenDoc(d) { return HID_ID.test(str(d.id)) || HID_TX.test(str(d.title)) || HID_TX.test(arr(d.aliases).join(' | ')); }
    function kindOf(d) {
        var id = str(d.id), t = str(d.title).toLowerCase(), k = d.kind || (/^help_/.test(id) ? 'help' : 'article');
        var trouble = /^support\./.test(id) || (/^help_support_/.test(id) && /\b(not|no|failed|gone|wrong|problem|missing|busy|off|limit|too|differ|dark|black|drift|error)\b/.test(t)) ||
            /\b(not|wont|won t|doesnt|does not|do not|did not|will not|fails?|failed|slow|vanished|missing|wrong|broken|error|errors|trouble|problems?|stuck|blank|lost|gone|blobby|smeared|dark)\b/.test(t) || /^why\b/.test(t);
        var howto = /^help_howto_|^help_topics_|^recipes\./.test(id) || /^how (do|to|a)\b/.test(t);
        var what = /^what\b/.test(t) || /^concepts\./.test(id) || /\bexplained\b|\bwhat (it|each|is|a)\b/.test(t);
        var where = /\b(where|folder|files?|output|save|saving|projects?|panel|tab|box|menu|bar|button|buttons|settings|index)\b/.test(t);
        return { k: k, trouble: trouble, howto: howto, what: what, where: where };
    }
    // intent of the question
    var RE_WHAT = /^\s*(what|whats|wat|wht)\s+(is|are|s|does|do|r)\b(?!\s+(i|we)\b)|^\s*(whats|wat s)\b(?!\s+(i|we)\b)|\b(meaning|mean|means|explained|explain|definition|define)\b|^\s*(what|whats)\s+(a|an|the)\b/i;
    var RE_HOW = /^\s*(how|hw|howto|howd)\b|\bhow (do|can|to|would|should)\b|^\s*(can|could) (i|you|u)\b|^\s*(make|turn|change|add|put|set|give|remove|delete|create|apply|use|get)\b/i;
    var RE_WHERE = /^\s*(where|wheres)\b|\bwhere (is|are|do|does|did|can)\b|\bwhich (file|folder)\b/i;
    var RE_PROB = /\b(doesn'?t|dont|don'?t|won'?t|wont|isn'?t|isnt|aren'?t|can'?t|cant|not (show|showing|work|working|load|loading|sav|open|opening|chang|changing|there|right|appear|apply|applying|using|updating|doing)\w*|missing|vanish\w*|disappear\w*|\blost\b|broken|stuck|slow|crash\w*|error|frozen|freez\w*|keeps|blank|different|wrong|blobby|smeared|blurry|muddy|nothing (happen|changed)\w*|does nothing|too (shiny|glossy|dull|dark|bright|flat|big|small|much|many)|gone|wiped|ignores?|failed|fails|turned|went black|washed out|(is|are|looks?|shows?|comes? out|went|turned) (all |just |completely )?(black|white|grey|gray|pink|blank|plain|default))\b|^\s*why\b/i;
    // ENC_READER_FIX 2026-10-05 (judge miss patterns, fitted on DEV only):
    //  look  - a tool name that is also a look word ('brushed aluminium', 'stamped metal') next to a finish / metal word and no canvas word: the look, not the tool
    //  bare  - a one-word question that is a verb ('export?') is a how-to; a file format ('tga?') asks about files
    //  SIMSYM - a colour symptom seen in the sim ('too saturated on track', 'red looks orange in iracing') reads as 'colours look different in iRacing'
    var RE_TOOLW = /\b(brush(ed|es)?|stamp(ed|s)?|mask(ed|s)?|fill(ed|s)?|smudg\w*|heal\w*|burn(ed|t)?)\b/i;
    var RE_LOOKW = /\b(metal\w*|alumin\w*|steel|titanium|chrome|gold|silver|copper|bronze|nickel|finish\w*|looks?|matte|gloss\w*|satin|pearl\w*|candy|spec|grain|texture|carbon|anodi[sz]ed|effect)\b/i;
    var RE_TOOLCTX = /\b(tool|tools|size|canvas|layers?|draw\w*|stroke\w*|hardness|opacity|selection|smoothing|eraser|cursor)\b/i;
    var RE_BAREV = /^\s*(export|render|import|load|save|undo|redo|deploy|upload|install|update|mirror|copy|merge|duplicate|share|print|reset|restore|recolou?r|flip|rotate|crop|resize)\s*[?!.]*\s*$/i;
    var RE_BAREF = /^\s*\.?(tga|psd|png|jpe?g|mip|dds|pdf|svg|json)s?\s*[?!.]*\s*$/i;
    var RE_SIMCTX = /\b(on (the )?track|in (the )?(sim|game|iracing|race)|ingame|in-game|iracing|on the grid|in the race)\b/i;
    var RE_SIMSYM = /\b(too (saturated|vivid|washed|pale|neon|orange|pink)|(over|under) ?saturated|washed out|faded|(looks?|looking|turns?|turned|comes? out|appears?|shows?( up)?) (\w+ )?(orange|pink|purple|brown|faded|different|saturated|neon|washed out))\b/i;
    var SIMSYM_ADD = ' colours look different in iracing';
    function intentOf(raw) {
        raw = String(raw || '').replace(/[’]/g, "'"); var bv = RE_BAREV.test(raw), bf = RE_BAREF.test(raw);
        return { what: RE_WHAT.test(raw) && !bv, how: RE_HOW.test(raw) || bv, where: RE_WHERE.test(raw) || bf, prob: RE_PROB.test(raw), look: RE_TOOLW.test(raw) && RE_LOOKW.test(raw) && !RE_TOOLCTX.test(raw), bare: bv || bf };
    }
    function cue(raw) { return RE_SIMSYM.test(raw) && RE_SIMCTX.test(raw) && !/colou?rs? look different in iracing/i.test(raw) ? raw + SIMSYM_ADD : raw; }
    // ROUND 4 (casual buyer phrasing, ENC_SEARCH_LAB): question rewrites, run on the spell-repaired question before tokens and intent.
    // ONE ROW PER LINE: [/regex/flags, 'replacement'] ('$&' keeps the match). The Python mirror reads these rows from this file.
    // Every row is a PHRASING CLASS (texting slang, filler openers, verb -> tool intent, symptom -> topic), never one test question.
    var REWRITE = [
        [/^\s*y\b/gi, 'why'],
        [/\bb4\b/gi, 'before'],
        [/\b(cuz|coz|bcuz|becuz|bcoz)\b/gi, 'because'],
        [/\b(idk|dunno)\b/gi, 'i dont know'],
        [/\b(smth|sth|somethin)\b/gi, 'something'],
        [/\b(teh|da)\b/gi, 'the'],
        [/\b(gotta|hafta)\b/gi, 'have to'],
        [/\blemme\b/gi, 'let me'],
        [/\b(is there (a|any|an easy) way to|is it possible to|any way to|anyway to|how would i go about|whats the (best|easiest|quickest|right) way to|what is the (best|easiest|quickest|right) way to|(the )?(best|easiest|quickest) way to)\b/gi, 'how to'],
        [/\b(does )?(any ?one|any ?body|some ?one|some ?body) (know|knows|got|have|has)\b/gi, ''],
        [/\b(i was wondering|i wonder|quick question|real quick|for some reason|out of nowhere|all of a sudden)\b/gi, ''],
        [/\b(sen[dt]|move|transfer|push|get|put|take|bring|load)\s+(it|this|that|them|the (paint|livery|design|skin|file)s?|my (paint|livery|design|skin)s?)\s+(to|into|in|onto|on)\s+(the |my )?(car|iracing|sim|game|race|track)\b/gi, '$& export to iracing'],
        [/\b(rac(e|ing)|driv(e|ing)) (with|in) (it|this|my (paint|livery|design|skin))\b|\b(finished|done)( designing| painting| with (it|the car|my design))?[ ,]+(now )?(what|whats next)\b/gi, '$& export to iracing'],
        [/\b(go|step|get|going) back (a |one )?(step|bit|move)\b|\bgo back\s*$|\bmessed (it |that |this )?up\b|\b(oops|whoops|oopsie)\b|\btake (it|that) back\b/gi, '$& undo'],
        [/\b(called|named)\s+\w+/gi, '$& search finishes by name'],
        [/\bbring (it )?in\b/gi, 'load'],
        [/^(?!.*\b(others|friends|other (drivers|people|racers|guys)|every ?one( else)?|no ?body( else)?|no one( else)?|my (buddy|buddies|friend|team ?mates?)|grid|for me but)\b)(.*\b(stock|default|old|original|plain) (paint|livery|car|skin|scheme)\b.*\b(sim|game|iracing|session|race|track)\b|.*\b(sim|game|iracing|session|race|track)\b.*\b(stock|default|old|original|plain) (paint|livery|car|skin|scheme)\b|.*\b(cant|dont|doesnt|wont|not|never|nothing)\b.*\b(see|seeing|shows?|showing|load|loading|appear\w*|chang\w*|updat\w*)\b.*\b(in|on|into) (the |a )?(sim|game|iracing|session|race|track)\b)/gi, '$& paint not showing in iracing'],
        [/\b(for me but not|only i can see|others (cant|dont|can not|do not) see|(nobody|no one|everyone) else|(not|never) on the grid|(my )?(buddy|buddies|friends?|team ?mates?) (cant|dont|can not|do not) see)\b/gi, '$& other drivers do not see your paint'],
        [/\b(looks?|is|comes? out|appears?)\s+(like\s+)?(a\s+)?(sandpaper|chalky|chalk|primer|lifeless)\b/gi, '$& finish looks flat'],
        [/\b(chrome|metal|metallic|silver|gold)\b[^.?!]{0,20}\b(looks?|is|goes|went|turns?|comes? out)\s+(\w+\s+)?(gr[ae]y|dark|dull|black|dirty|muddy)\b/gi, '$& chrome looks dark'],
        [/\b(in|on|with|for|inside|using) (this|the) (app|program|software|booth|thing)\b/gi, ''],
        [/\b(red)\b(?=[^.?!]*\bspec\b)|\bspec\b[^.?!]{0,20}\b(red)\b/gi, '$& metallic channel'],
        [/\b(green)\b(?=[^.?!]*\bspec\b)|\bspec\b[^.?!]{0,20}\b(green)\b/gi, '$& roughness channel'],
        [/\b(blue)\b(?=[^.?!]*\bspec\b)|\bspec\b[^.?!]{0,20}\b(blue)\b/gi, '$& clearcoat channel'],
        [/\b(only|just)\s+(change|touch|edit|affect|adjust|tweak|mess with)\s+(the\s+)?(shine|reflections?|gloss|spec|shininess)\b|\b(keep|leave|dont change|without changing|not change|wont change)\s+(my |the )?(colou?rs?|paint|design|artwork)\b/gi, '$& spec only keep paint'],
        [/\bpreview\b[^.?!]{0,25}\b(shows? nothing|is blank|went blank|blank|is black|went black|empty|not updating|not changing|wont update|doesnt update|stuck|frozen)\b/gi, '$& fix preview not changing'],
        [/\b(start|begin|create|make|add|open)\s+(a\s+)?(new|another|second|extra|separate)\s+(zone|layer)\b/gi, '$& add $4'],
        [/\b(turn|make|change|swap|switch|recolou?r)\b(?=[^.?!]*\b(red|blue|green|black|white|yellow|orange|purple|pink|gr[ae]y|silver|gold)\b[^.?!]*\b(red|blue|green|black|white|yellow|orange|purple|pink|gr[ae]y|silver|gold)\b)/gi, '$& change one colour'],
        [/\b(massive|huge|giant|gigantic|enormous|way too big|too big|oversized|blown up)\b(?=[^.?!]*\b(texture|pattern|carbon|weave|flake|camo|grain|checkers?|honeycomb)\b)|\b(texture|pattern|carbon|weave|flake|camo|grain|checkers?|honeycomb)\b[^.?!]{0,25}\b(massive|huge|giant|gigantic|enormous|way too big|too big|oversized|blown up)\b/gi, '$& tiny or huge scale'],
        [/\b(shrink|smaller|scale down|tighter|finer|zoom out)\b[^.?!]{0,20}\b(texture|pattern|carbon|weave|flake|camo|grain|checkers?|honeycomb)\b|\b(texture|pattern|carbon|weave|flake|camo|grain|checkers?|honeycomb)\b[^.?!]{0,20}\b(smaller|finer|tighter)\b/gi, '$& pattern finer size'],
        [/\b(zones?|finish(es)?|patterns?|spec)\b[^.?!]{0,25}\b(isnt|is not|not|wont|doesnt|does not|dont|didnt|did not|never|has no|have no)\s+(painting|working|doing anything|do anything|applying|apply|taking effect|take effect|changing anything|showing|show|appearing|any effect|effect)\b/gi, '$& does not show nothing changed'],
        // R4B-LEGIBILITY: numbers / sponsors / lettering + a visibility goal (stand out, pop, readable, more visible, easier to see, hard to read, blends in) -> the legibility topic. Not when a finish is named ('hard to read on chrome' = the finish covers the art: decal rescue), not 'not visible' / 'missing' (vanished numbers)
        [/^(?![^.?!]*\b(chrome|finish(es)?|metallic|candy|flake|spec|pattern)\b)[^.?!]*?(\b(numbers?|sponsors?|logos?|decals?|lettering)\b[^.?!]{0,30}\b(stand out|pop|readable|legible|more visible|easier to see|show up better|so they show up|hard to read|cant read|can t read|blends?( in| into)?|get(s|ting)? lost)\b|\b(stand out|pop|readable|legible|read)\b[^.?!]{0,20}\b(numbers?|sponsors?|lettering)\b)/gi, '$& readable number contrast'],
        // R4B-ADDELEM: make / create / draw / do / paint / put / want + a drawn design element (stripes, flames, checkers, chevrons, stars) = the add-it how-to. Not numbers / logos / sponsors: 'make my numbers chrome', 'paint my numbers red' edit art that is already there
        [/\b(make|making|create|draw|do|paint|put|want|need)\s+(a |an |some |two |twin |three |the |my )?(\w+ )?(stripes?|pinstripes?|flames?|checkers?|chevrons?|stars?)\b/gi, '$& add $4'],
    ];
    function rewrite(raw) { for (var i = 0; i < REWRITE.length; i++) { REWRITE[i][0].lastIndex = 0; raw = raw.replace(REWRITE[i][0], REWRITE[i][1]); } return raw.replace(/\s+/g, ' ').trim(); }
    function toolDoc(d) { return d.dom === 'tools' || d.dom === 'controls_tools'; }

    // ------------------------------------------------------------------ build
    function build(list, opts) {
        opts = opts || {};
        var docs = [], df = {}, vocab = [], avg = {}, cnt = 0, F = FIELDS.length, QM = opts.qbank === false ? null : qbMap(), upost = nul(), sw = nul();
        arr(list).forEach(function (a) {
            if (!a || !a.id || hiddenDoc(a)) return;
            var fl = {
                t: toks(a.title), a: toks(arr(a.aliases).join(' . ')), q: toks(arr(a.faq).map(function (x) { return x && x.q ? x.q : ''; }).join(' . ')), s: toks(a.summary),
                c: toks(arr(a.controls).map(function (x) { return x && typeof x === 'object' ? str(x.label) : ''; }).join(' . ')),
                m: toks(arr(a.mistakes).map(function (x) { return x && typeof x === 'object' ? str(x.symptom) : ''; }).join(' . ')),
                b: toks([str(a.what), textOf(a.how, function (x) { return str(x.text || x.step); }), textOf(a.when, function () { return ''; }), textOf(a.tips, function () { return ''; }), textOf(a.pitfalls, function () { return ''; }),
                    arr(a.faq).map(function (x) { return x && x.a ? str(x.a) : ''; }).join(' '), arr(a.controls).map(function (x) { return x && typeof x === 'object' ? str(x.effect) : ''; }).join(' '),
                    arr(a.mistakes).map(function (x) { return x && typeof x === 'object' ? str(x.cause) + ' ' + str(x.fix) : ''; }).join(' '),
                    arr(a.deep).map(function (x) { return x && typeof x === 'object' ? str(x.heading) + ' ' + str(x.body) : ''; }).join(' ')].join(' ')),
                p: toks(QM && QM[a.id] ? QM[a.id].join(' . ') : '')
            };
            var units = [], tt = toks(a.title);
            if (tt.length) { units.push({ k: 't', w: tt }); if (/^help_/.test(a.id) && /\?\s*$/.test(str(a.title))) units.push({ k: 'q', w: tt, j: -1 }); }
            arr(a.aliases).forEach(function (x) { var w = toks(x); if (w.length) units.push({ k: 'a', w: w }); });
            arr(a.faq).forEach(function (x, j) { if (x && x.q && !HID_TX.test(str(x.q) + ' ' + str(x.a))) { var w = toks(x.q); if (w.length) units.push({ k: 'q', w: w, j: j }); } });
            if (QM && QM[a.id]) QM[a.id].forEach(function (x) { var w = toks(x); if (w.length) units.push({ k: 'p', w: w }); });          // ROUND 3: each casual bank question is a 'nearest question' unit too
            units.forEach(function (U) { var uq = [], sn = nul(); for (var z = 0; z < U.w.length; z++) if (!sn[U.w[z]]) { sn[U.w[z]] = 1; uq.push(U.w[z]); } U.u = uq; U.s = ' ' + U.w.join(' ') + ' '; });
            for (var ui = 0; ui < units.length; ui++) for (var uz = 0; uz < units[ui].u.length; uz++) (upost[units[ui].u[uz]] || (upost[units[ui].u[uz]] = [])).push(docs.length, ui);   // word -> (doc, unit) pairs: search only visits units that share a word with the question
            var d = { id: a.id, i: docs.length, fl: fl, units: units, kind: kindOf(a), gen: !!a.generated && !/^help_/.test(a.id), help: /^help_/.test(a.id), dom: String(a.id).split('.')[0].replace(/_[0-9]+$/, ''), ntitle: tt.join(' ') };
            // second channel ("plain"): the simple one-bag BM25 the offline helper used before, with its title / alias bonuses. Fused by rank
            // (search below): it is blunter but generalises better to new phrasings (ENC_SEARCH_LAB held2: 72.1 vs 64.7 top-1)
            var lt = nul(), ll = 0, lf = { t: tt, a: toks(arr(a.aliases).join(' ')), s: fl.s, q: toks(arr(a.faq).map(function (x) { return x && x.q ? x.q : ''; }).join(' ')),
                b: toks([str(a.what), textOf(a.how, function (x) { return str(x.text || x.step); })].join(' ')).slice(0, 90), p: fl.p };
            for (var lk in LFW) { var LL = lf[lk]; for (var li = 0; li < LL.length; li++) { lt[LL[li]] = (lt[LL[li]] || 0) + LFW[lk]; ll += LFW[lk]; } }
            d.lt = lt; d.ll = ll; d.lpr = d.help ? 1.0 : (d.gen ? 0.8 : 1.12); d.tws = tt;
            d.lal = arr(a.aliases).map(function (x) { return toks(x).join(' '); }).filter(function (x) { return x.indexOf(' ') > 0; });
            d.tq = /^\s*(what|why)\b/i.test(str(a.title)); d.tp = LPROB.test(str(a.title));
            surf(sw, [str(a.title), arr(a.aliases).join(' '), arr(a.faq).map(function (x) { return x && x.q ? str(x.q) : ''; }).join(' '), str(a.summary)].join(' '));
            docs.push(d); cnt++;
            for (var f = 0; f < F; f++) avg[FIELDS[f][0]] = (avg[FIELDS[f][0]] || 0) + fl[FIELDS[f][0]].length;
        });
        for (var f0 = 0; f0 < F; f0++) avg[FIELDS[f0][0]] = Math.max(1, (avg[FIELDS[f0][0]] || 0) / Math.max(1, cnt));
        // postings: term -> [[doc index, weighted normalised tf], ...] in doc order
        var post = nul();
        docs.forEach(function (d) {
            var tf = nul(), terms = [];
            for (var f = 0; f < F; f++) {
                var key = FIELDS[f][0], w = FIELDS[f][1], b = FIELDS[f][2], L = d.fl[key], norm_ = 1 - b + b * L.length / avg[key], seen = nul();
                if (!w) continue;          // a weight-0 field is not indexed at all (ROUND 3: the bank's words stay out of the postings, so they do not widen every search)
                for (var i = 0; i < L.length; i++) { var t = L[i]; if (!seen[t]) seen[t] = 0; seen[t]++; }
                for (var i2 = 0; i2 < L.length; i2++) { var t2 = L[i2]; if (seen[t2] < 0) continue; if (!(t2 in tf)) { tf[t2] = 0; terms.push(t2); } tf[t2] += w * seen[t2] / norm_; seen[t2] = -1; }
            }
            terms.forEach(function (t) { if (!post[t]) { post[t] = []; vocab.push(t); } post[t].push([d.i, tf[t]]); });
            d.fl = null;
        });
        var N = docs.length, idf = nul();
        vocab.forEach(function (t) { var n = post[t].length; idf[t] = Math.log(1 + (N - n + 0.5) / (n + 0.5)); });
        docs.forEach(function (d) { d.units.forEach(function (U) { var m = 0; for (var z = 0; z < U.u.length; z++) { var v = idf[U.u[z]]; m += v == null ? 0 : v; } U.m = m; }); });
        var sorted = vocab.slice().sort();
        // plain-channel postings + idf (its own document frequencies, like the old helper)
        var lpost = nul(), lidf = nul(), lsum = 0;
        docs.forEach(function (d) { lsum += d.ll; for (var t in d.lt) { (lpost[t] || (lpost[t] = [])).push(d.i); } });
        for (var lt0 in lpost) lidf[lt0] = Math.log(1 + (N - lpost[lt0].length + 0.5) / (lpost[lt0].length + 0.5));
        var ix = { v: VERSION, docs: docs, post: post, idf: idf, del: null, vocab: sorted, N: N, maxIdf: Math.log(1 + (N - 0.5) / 1.5), prefix: !!opts.prefix, lpost: lpost, lidf: lidf, lavg: lsum / Math.max(1, N), upost: upost, sw: sw, swl: Object.keys(sw).sort(), spc: nul() };
        if (!QM && opts.qbank !== false && typeof document !== 'undefined') { ix.src = list; ix.opts = opts; IXS.push(ix); }          // built before the bank arrived: re-built in place when it does
        return ix;
    }
    // typo repair: delete-1 neighbourhood (and delete-2 for long words) of every indexed word -> its most frequent word. Built on the first
    // unknown word, not at boot (order-independent: ties go to the more frequent, then the alphabetically first word)
    function delMap(ix) {
        if (ix.del) return ix.del;
        var post = ix.post, del = nul();
        function addDel(k, t) { var c = del[k]; if (!c || post[t].length > post[c].length || (post[t].length === post[c].length && t < c)) del[k] = t; }
        ix.vocab.forEach(function (t) {
            if (t.length < 4 || /[0-9]/.test(t)) return;
            for (var i = 0; i < t.length; i++) { var k = t.slice(0, i) + t.slice(i + 1); addDel(k, t); if (t.length >= 7) for (var j = i; j < k.length; j++) addDel(k.slice(0, j) + k.slice(j + 1), t); }
        });
        ix.del = del; return del;
    }
    function idfOf(ix, t) { var v = ix.idf[t]; return v == null ? null : v; }
    // a word the index does not know -> the closest indexed word (edit distance 1, then 2 for long words), else itself
    function fix(ix, w) {
        if (idfOf(ix, w) != null || w.length < 4 || /[0-9]/.test(w)) return w;
        var D = delMap(ix), c = D[w]; if (c) return c;
        for (var i = 0; i < w.length; i++) { var k = w.slice(0, i) + w.slice(i + 1); if (idfOf(ix, k) != null) return k; c = D[k]; if (c) return c; }
        if (w.length >= 6) for (var i2 = 0; i2 < w.length; i2++) { var k1 = w.slice(0, i2) + w.slice(i2 + 1); for (var j = i2; j < k1.length; j++) { var k2 = k1.slice(0, j) + k1.slice(j + 1); if (idfOf(ix, k2) != null && k2.length >= 4) return k2; } }
        return w;
    }
    function prefixWords(ix, w) {
        var out = [], L = ix.vocab, lo = 0, hi = L.length;
        while (lo < hi) { var mid = (lo + hi) >> 1; if (L[mid] < w) lo = mid + 1; else hi = mid; }
        for (var i = lo; i < L.length && out.length < 6 && L[i].indexOf(w) === 0; i++) if (L[i] !== w) out.push(L[i]);
        return out;
    }
    // ------------------------------------------------------------------ did you mean (ENC_READER_FIX 2026-10-05)
    // The word-level typo repair above works on STEMMED index words, so a typo of a word the stemmer shortens ('tradng' vs 'trad',
    // 'iracng' vs 'irac') used to land on an unrelated word ('strang', 'rang'). spell() repairs the RAW words first, against the words
    // buyers can see (titles, aliases, FAQ questions, summaries): a word the index does not know -> the closest surface word by
    // edit distance (with swaps; 1 for short words, 2 from 7 letters), the more common word on a tie. search() runs on the repaired
    // text; callers show 'Showing results for ...' from spell(ix, text).fixes.
    var SURF_RE = /[^a-z0-9]+/;
    function surf(sw, text) {
        var seen = nul(), L = String(text || '').toLowerCase().replace(/['’]/g, '').split(SURF_RE);
        for (var i = 0; i < L.length; i++) { var w = L[i]; if (w.length >= 3 && /^[a-z]+$/.test(w) && !STOP[w] && !seen[w]) { seen[w] = 1; sw[w] = (sw[w] || 0) + 1; } }
    }
    function osa(a, b, mx) {          // optimal-string-alignment distance (insert, delete, change, swap of neighbours); > mx = mx + 1
        var la = a.length, lb = b.length; if (Math.abs(la - lb) > mx) return mx + 1;
        var p2 = [], p1 = [], c, j;
        for (j = 0; j <= lb; j++) p1.push(j);
        for (var i = 1; i <= la; i++) {
            c = [i]; var lo = i;
            for (j = 1; j <= lb; j++) {
                var v = Math.min(p1[j] + 1, c[j - 1] + 1, p1[j - 1] + (a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1));
                if (i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) && a.charAt(i - 2) === b.charAt(j - 1)) v = Math.min(v, p2[j - 2] + 1);
                c.push(v); if (v < lo) lo = v;
            }
            if (lo > mx) return mx + 1;
            p2 = p1; p1 = c;
        }
        return p1[lb];
    }
    function known(ix, w) { if (ix.sw[w] || STOP[w] || SYN[w]) return true; var t = toks(w); return !t.length || (t.length === 1 && idfOf(ix, t[0]) != null); }
    function nearest(ix, w) {          // the closest surface word, '' = none within reach
        if (ix.spc[w] != null) return ix.spc[w];
        var mx = w.length >= 7 ? 2 : 1, best = '', bd = mx + 1, bf = 0, L = ix.swl;
        for (var i = 0; i < L.length; i++) {
            var c = L[i]; if (Math.abs(c.length - w.length) > mx || c.length < 4) continue;
            var d = osa(w, c, Math.min(mx, bd)); if (d > mx) continue;
            var f = ix.sw[c]; if (d < bd || (d === bd && f > bf)) { best = c; bd = d; bf = f; }
        }
        ix.spc[w] = best; return best;
    }
    function startsAny(ix, w) { var L = ix.swl, lo = 0, hi = L.length; while (lo < hi) { var m = (lo + hi) >> 1; if (L[m] < w) lo = m + 1; else hi = m; } return lo < L.length && L[lo].indexOf(w) === 0; }
    // spell(ix, text, opts) -> { text: repaired text (same as text when nothing changed), fixes: [[typed, meant], ...] }
    function spell(ix, text, opts) {
        opts = opts || {}; var raw = String(text || ''), fixes = [];
        if (!ix || !ix.sw) return { text: raw, fixes: fixes };
        var parts = raw.split(/([^A-Za-z0-9'’]+)/), last = -1;
        for (var k = parts.length - 1; k >= 0; k -= 2) if (parts[k]) { last = k; break; }
        for (var i = 0; i < parts.length; i += 2) {
            var w = parts[i].toLowerCase().replace(/['’]/g, '');
            if (w.length < 4 || !/^[a-z]+$/.test(w) || known(ix, w)) continue;
            if (i === last && i === parts.length - 1 && ix.prefix && opts.prefix !== false && startsAny(ix, w)) continue;          // still being typed
            var c = nearest(ix, w); if (c && c !== w) { fixes.push([parts[i], c]); parts[i] = c; }
        }
        return { text: fixes.length ? parts.join('') : raw, fixes: fixes };
    }
    // ------------------------------------------------------------------ search
    function search(ix, text, opts) {
        opts = opts || {};
        if (!ix || !ix.N) return [];
        var raw = cue(rewrite(spell(ix, text, opts).text)), q0 = toks(raw), q = [], qn, seen = nul();
        for (var i = 0; i < q0.length; i++) { var w = fix(ix, q0[i]); q.push(w); }
        for (var cj = 0; cj + 1 < q.length; cj++) if (q[cj] === 'trad' && q[cj + 1] === 'paint') q.splice(cj, 2, 'tradingpaint');   // a typo'd 'trading panits' misses norm()'s compound; rejoin it after typo repair
        var qs = []; for (var i1 = 0; i1 < q.length; i1++) if (!seen[q[i1]]) { seen[q[i1]] = 1; qs.push(q[i1]); }
        if (!qs.length) return [];
        qn = ' ' + q.join(' ') + ' ';
        var it = intentOf(raw);
        // expansions per query word (stemmed, indexed only)
        var alt = [], mass = 0, qw = [];
        for (var a = 0; a < qs.length; a++) {
            var w0 = qs[a], ex = [], src = EXPAND[w0] || [];
            for (var e = 0; e < src.length; e++) { var x = word(src[e]); if (x !== w0 && idfOf(ix, x) != null && ex.indexOf(x) === -1) ex.push(x); }
            if (ix.prefix && opts.prefix !== false && a === qs.length - 1 && idfOf(ix, w0) == null && w0.length >= 2) { var pw = prefixWords(ix, w0); for (var p = 0; p < pw.length; p++) if (ex.indexOf(pw[p]) === -1) ex.push(pw[p]); }
            alt.push(ex);
            var wi = idfOf(ix, w0); qw.push(wi == null ? ix.maxIdf : wi); mass += qw[a];
        }
        // BM25 over postings
        var acc = {}, got = {}, cand = [];
        for (var b = 0; b < qs.length; b++) {
            var hit = nul(), L = ix.post[qs[b]] || [], idw = idfOf(ix, qs[b]);
            for (var j = 0; j < L.length; j++) { var di = L[j][0], tf = L[j][1]; if (acc[di] == null) { acc[di] = 0; got[di] = 0; cand.push(di); } acc[di] += idw * tf * (K1 + 1) / (tf + K1); got[di] += qw[b]; hit[di] = 1; }
            for (var k = 0; k < alt[b].length; k++) {
                var x2 = alt[b][k], L2 = ix.post[x2] || [], idx2 = idfOf(ix, x2);
                for (var j2 = 0; j2 < L2.length; j2++) {
                    var d2 = L2[j2][0], tf2 = L2[j2][1]; if (hit[d2]) continue; hit[d2] = 1;
                    if (acc[d2] == null) { acc[d2] = 0; got[d2] = 0; cand.push(d2); }
                    acc[d2] += EXP_W * Math.min(idx2, qw[b]) * tf2 * (K1 + 1) / (tf2 + K1); got[d2] += EXP_W * qw[b];
                }
            }
        }
        // query word -> weight lookup for unit matching (expansions count EXP_W)
        var qmap = nul(), qk = [];
        for (var c = 0; c < qs.length; c++) { if (qmap[qs[c]] == null) qk.push(qs[c]); qmap[qs[c]] = Math.max(qmap[qs[c]] || 0, qw[c]); for (var c2 = 0; c2 < alt[c].length; c2++) { var y = alt[c][c2]; if (qmap[y] == null) qk.push(y); qmap[y] = Math.max(qmap[y] || 0, EXP_W * qw[c]); } }
        // unit hits: per doc, per unit, the question-word weight it shares (summed in question-word order; the Python mirror does the same)
        var UH = nul(), UL = nul();
        for (var kq = 0; kq < qk.length; kq++) { var tq = qk[kq], LU = ix.upost[tq]; if (!LU || !qmap[tq]) continue; var vq = Math.min(qmap[tq], ix.idf[tq]);
            for (var lu = 0; lu < LU.length; lu += 2) { var dd = LU[lu], uix = LU[lu + 1], H = UH[dd]; if (!H) { H = UH[dd] = nul(); UL[dd] = []; } if (H[uix] == null) { H[uix] = 0; UL[dd].push(uix); } H[uix] += vq; } }
        var bigr = []; for (var g = 0; g + 1 < q.length; g++) if (q[g] !== q[g + 1]) bigr.push(q[g] + ' ' + q[g + 1]);
        var out = [], B2 = P.beta * P.beta, qj = q.join(' ');
        for (var n = 0; n < cand.length; n++) {
            var d = ix.docs[cand[n]], s = P.bm * acc[cand[n]], bt = 0, ba = 0, bq = 0, bp = 0, bj = -1, ph = 0, xu = 0;
            var Hd = UH[cand[n]], Ld = Hd ? UL[cand[n]].sort(function (x0, y0) { return x0 - y0; }) : [];
            for (var u0 = 0; u0 < Ld.length; u0++) {
                var U = d.units[Ld[u0]], hitw = Hd[Ld[u0]], um = U.m;
                if (!um || !hitw) continue;
                var r1 = hitw / mass, r2 = hitw / um, f1 = (1 + B2) * r1 * r2 / (B2 * r2 + r1);
                if (r1 >= 0.999 && r2 >= 0.999) xu = Math.max(xu, U.k === 'q' ? P.xq : (U.k === 'p' ? P.xp : 1));   // a curated alias / the title outranks a FAQ side question
                if (U.k === 't') { if (f1 > bt) bt = f1; } else if (U.k === 'a') { if (f1 > ba) ba = f1; } else if (U.k === 'p') { if (f1 > bp) bp = f1; continue; } else if (f1 > bq) { bq = f1; bj = U.j; }
                if (bigr.length) { for (var bg = 0; bg < bigr.length; bg++) if (U.s.indexOf(' ' + bigr[bg] + ' ') !== -1) { ph += 1; break; } }
            }
            s += P.ut * bt + P.ua * ba + P.uq * bq + P.up * bp + P.ph * Math.min(2, ph) + P.xu * xu;
            if (d.ntitle.indexOf(' ') > 0 && qn.indexOf(' ' + d.ntitle + ' ') !== -1) s += P.whole;
            var K = d.kind, m = KIND_PRIOR[K.k] || 1;
            if (d.help) m *= P.gen;
            if (Object.prototype.hasOwnProperty.call(DOM_PRIOR, d.dom)) m *= DOM_PRIOR[d.dom];
            if (it.prob) { if (K.trouble) m *= P.iy; } else if (K.trouble) m *= P.ip;
            if (it.what && !it.how && !it.prob) { if (K.what) m *= P.iw; if (K.howto) m *= P.iq; }
            else if (it.how && !it.what) { if (K.howto) m *= P.ih; if (K.what && !K.howto) m *= P.iq; }
            if (it.where && K.where) m *= P.iwh;
            if (it.look && toolDoc(d)) m *= P.il;
            if (d.ntitle && d.ntitle === qj) m = P.exact;          // the question IS the title (a finish or term name typed exactly): no kind discount
            var cv = mass ? Math.min(1, got[cand[n]] / mass) : 0;
            var o = { id: d.id, i: d.i, score: s * m * P.scale * (P.cg ? Math.pow(cv, P.cg) : 1), cov: cv, faq: bj, fs: bq };   // cg: a doc that covers more of the question's words wins
            if (opts.debug) o.dbg = { bm: acc[cand[n]], bt: bt, ba: ba, bq: bq, ph: ph, m: m, q: q.join(' ') };
            out.push(o);
        }
        out.sort(function (x, y) { return y.score - x.score || x.i - y.i; });
        var lock = P.qlock > 0 && out.length > 1 && out[0].score >= P.qlock * out[1].score ? out[0].i : -1;
        if (P.fw > 0 && out.length > 1) out = fuse(ix, out, q, qs, alt, raw, it);
        if (lock !== -1 && out[0].i !== lock) lock = -1;
        if (P.qw > 0) out = qbBlend(ix, out, raw, lock);          // ROUND 3: nearest question in the paraphrase bank
        return out.slice(0, opts.limit || 6);
    }
    // plain channel (the old offline helper's scorer) over the same words, then reciprocal-rank fusion with the main list. The main list's
    // scores are handed out again in the new order (rank 1 gets the best score), so callers' score thresholds keep their meaning
    function fuse(ix, out, q, qs, alt, raw, it) {
        var lk1 = 1.2, lb = 0.55, qset = nul(), qn = ' ' + q.join(' ') + ' ', mass = 0, ls = [], lc = nul(), cand = [];
        var qHow = /^\s*(how|hw|where)\b|^\s*(can|do) i\b/i.test(raw);
        for (var a = 0; a < qs.length; a++) { qset[qs[a]] = 1; for (var e = 0; e < alt[a].length; e++) qset[alt[a][e]] = 1; var iv = ix.lidf[qs[a]]; mass += iv == null ? ix.maxIdf : iv; }
        for (var a1 = 0; a1 < qs.length; a1++) { var L = ix.lpost[qs[a1]] || []; for (var j = 0; j < L.length; j++) if (!lc[L[j]]) { lc[L[j]] = 1; cand.push(L[j]); } for (var e1 = 0; e1 < alt[a1].length; e1++) { var L1 = ix.lpost[alt[a1][e1]] || []; for (var j1 = 0; j1 < L1.length; j1++) if (!lc[L1[j1]]) { lc[L1[j1]] = 1; cand.push(L1[j1]); } } }
        for (var n = 0; n < cand.length; n++) {
            var d = ix.docs[cand[n]], s = 0;
            for (var w = 0; w < qs.length; w++) {
                var f = d.lt[qs[w]], idf = ix.lidf[qs[w]], wt = 1;
                if (!f) { for (var k = 0; k < alt[w].length; k++) if (d.lt[alt[w][k]]) { f = d.lt[alt[w][k]]; idf = Math.max(idf || 0, ix.lidf[alt[w][k]]); wt = 0.75; break; } }
                if (f) s += wt * idf * (f * (lk1 + 1)) / (f + lk1 * (1 - lb + lb * d.ll / ix.lavg));
            }
            if (!s) continue;
            if (d.ntitle.length > 3 && qn.indexOf(' ' + d.ntitle + ' ') !== -1) s += 3;
            for (var x = 0; x < d.lal.length; x++) {
                var al = d.lal[x]; if (qn.indexOf(' ' + al + ' ') !== -1) { s += 2.5; continue; }
                var aw = al.split(' '), all = true; for (var y = 0; y < aw.length; y++) if (!qset[aw[y]]) { all = false; break; }
                if (all) s += 1.5;
            }
            var ov = 0; for (var o = 0; o < qs.length; o++) if (d.tws.indexOf(qs[o]) !== -1) ov++;
            ov /= qs.length; s += 2 * ov * ov;
            if (qHow && d.tq) s *= 0.75;
            if (!it.prob && d.tp) s *= 0.7;
            if (it.prob && (/^support\./.test(d.id) || /^help_support/.test(d.id))) s *= 1.15;
            if (it.look && toolDoc(d)) s *= P.il;
            ls.push({ i: d.i, s: s * d.lpr * (KIND_PRIOR[d.kind.k] || 1) });
        }
        ls.sort(function (x1, y1) { return y1.s - x1.s || x1.i - y1.i; });
        var rk = nul(), F = P.fk; for (var r = 0; r < ls.length && r < 50; r++) rk[ls[r].i] = r + 1;
        var sc = out.map(function (h) { return h.score; }), fused = out.map(function (h, r0) { var pr = rk[h.i]; return { h: h, f: 1 / (F + r0 + 1) + (pr ? P.fw / (F + pr) : 0), r: r0 }; });
        fused.sort(function (x2, y2) { return y2.f - x2.f || x2.r - y2.r; });
        return fused.map(function (z, r1) { var h = z.h; h.score = sc[r1]; return h; });
    }
    // ------------------------------------------------------------------ ROUND 3: the paraphrase bank (nearest casual question)
    // js/spb-enc-qbank.js = {v, bank: [[articleId, [casual questions]]]}, written blind (ENC_SEARCH_LAB round 3). It is a separate file, loaded
    // after the page is up (browser) or required on first use (Node); until it is there the ranker simply runs without it.
    // Each bank question and the asked question become TF-IDF vectors of char 3-4-grams + words + word pairs over the ranker's own tokens
    // (stemmed, synonyms, typo-repaired for the question); an article's similarity is its best question's cosine.
    var QBD = null, QB = null, QBM = null, QBMd = null, IXS = [];
    function qbank(d) {
        if (d && d.bank && d !== QBD) {
            QBD = d; QB = null;
            var L = IXS.splice(0, IXS.length);          // indexes built without the bank: rebuild them in place, off the current task (same object, so callers keep their reference)
            if (L.length) setTimeout(function () { L.forEach(function (ix) { var M = qbMap(), any = false; arr(ix.src).forEach(function (a) { if (a && M && M[a.id]) any = true; }); if (!any) return; var nx = build(ix.src, ix.opts), k; for (k in ix) if (Object.prototype.hasOwnProperty.call(ix, k)) delete ix[k]; for (k in nx) if (Object.prototype.hasOwnProperty.call(nx, k)) ix[k] = nx[k]; }); }, 0);
        }
        return !!QBD;
    }
    function qbMap() { var D = qbData(); if (!D || !D.bank || !D.bank.length) return null; if (QBMd !== D) { QBM = nul(); for (var i = 0; i < D.bank.length; i++) QBM[D.bank[i][0]] = D.bank[i][1]; QBMd = D; } return QBM; }
    function qbData() {
        if (QBD) return QBD;
        if (typeof window !== 'undefined' && window.SPB_ENC_QBANK) return qbank(window.SPB_ENC_QBANK) ? QBD : null;
        if (typeof module === 'object' && module.exports && typeof require === 'function') { try { qbank(require('./spb-enc-qbank.js')); } catch (e) { QBD = { bank: [] }; } }
        return QBD;
    }
    function qfeat(words) {          // feature names in first-seen order + counts ('w' word, 'b' word pair, '3'/'4' char gram)
        var f = [], c = nul(), s = ' ' + (P.qcs ? words.filter(function (w) { return !STOP[w]; }) : words).join(' ') + ' ';          // qcs: char grams from the content words only (the little words still count as words)
        function add(k) { if (c[k] == null) { c[k] = 0; f.push(k); } c[k]++; }
        for (var i = 0; i < words.length; i++) add('w' + words[i]);
        for (var j = 0; j + 1 < words.length; j++) add('b' + words[j] + ' ' + words[j + 1]);
        for (var n = 3; n <= 4; n++) for (var k = 0; k + n <= s.length; k++) add(n + s.substr(k, n));
        return { f: f, c: c };
    }
    // bank words keep the little words ("what is a zone" vs "zone not showing" differ only in them): synonyms + stems, no stop list;
    // the asked question's other words get the ranker's typo repair
    var QWC = nul();
    function qtoks(s, ix) {
        var out = [], L = norm(s).split(' ');
        for (var i = 0; i < L.length; i++) {
            var w = L[i]; if (!w) continue; var x = SYN[w] || w;
            if (STOP[x]) { out.push(x); continue; }
            var c = QWC[w]; if (c === undefined) { c = (x.length < 2 && !/[0-9]/.test(x)) ? '' : stem(x); QWC[w] = c; }
            if (c) out.push(ix ? fix(ix, c) : c);
        }
        return out;
    }
    function qgw(k) { var g = k.charAt(0); return g === 'w' ? P.qww : (g === 'b' ? P.qbw : P.qcw); }
    function qvec(F, df, N) {          // [[feature, weight]] (known features only), L2-normalised
        var v = [], ss = 0;
        for (var i = 0; i < F.f.length; i++) { var k = F.f[i], d = df[k]; if (!d) continue; var w = qgw(k) * (1 + Math.log(F.c[k])) * (Math.log((N + 1) / (d + 1)) + 1); if (w > 0) { v.push([k, w]); ss += w * w; } }
        var nr = Math.sqrt(ss); if (nr > 0) for (var j = 0; j < v.length; j++) v[j][1] = v[j][1] / nr;
        return v;
    }
    function qbBuild() {
        var D = qbData(), key = P.qcw + '|' + P.qww + '|' + P.qbw;
        if (!D || !D.bank || !D.bank.length) return null;
        if (QB && QB.key === key) return QB;
        var B = D.bank, qa = [], fs = [], df = nul(), post = nul();
        for (var a = 0; a < B.length; a++) { var L = B[a][1] || []; for (var j = 0; j < L.length; j++) { var t = qtoks(L[j], null); if (!t.length) continue; var F = qfeat(t); qa.push(a); fs.push(F); for (var x = 0; x < F.f.length; x++) df[F.f[x]] = (df[F.f[x]] || 0) + 1; } }
        var N = fs.length;
        for (var qi = 0; qi < N; qi++) { var v = qvec(fs[qi], df, N); for (var y = 0; y < v.length; y++) (post[v[y][0]] || (post[v[y][0]] = [])).push(qi, v[y][1]); }
        QB = { key: key, ids: B.map(function (r) { return r[0]; }), qa: qa, df: df, N: N, post: post };
        return QB;
    }
    function qbHits(ix, raw) {          // [{i, s}] best first: the ix docs whose bank questions are nearest to the (typo-repaired) question words
        var Q = qbBuild(), q = qtoks(raw, ix); if (!Q || !q.length) return [];
        if (!ix.qb || ix.qb.Q !== Q) { var by = nul(); for (var d = 0; d < ix.docs.length; d++) by[ix.docs[d].id] = d; ix.qb = { Q: Q, m: Q.ids.map(function (id) { return by[id] == null ? -1 : by[id]; }) }; }
        var v = qvec(qfeat(q), Q.df, Q.N), acc = new Float64Array(Q.N), ql = [];          // every product is > 0, so 0 = not reached yet
        for (var i = 0; i < v.length; i++) { var L = Q.post[v[i][0]], w = v[i][1]; for (var j = 0; j < L.length; j += 2) { var qi = L[j]; if (acc[qi] === 0) ql.push(qi); acc[qi] += w * L[j + 1]; } }
        var best = nul(), sec = nul(), al = [];          // an article's similarity = its nearest question (+ qk x its second nearest)
        for (var k = 0; k < ql.length; k++) { var di = ix.qb.m[Q.qa[ql[k]]], s = acc[ql[k]]; if (di < 0 || s < P.qt) continue; if (best[di] == null) { best[di] = s; sec[di] = 0; al.push(di); } else if (s > best[di]) { sec[di] = best[di]; best[di] = s; } else if (s > sec[di]) sec[di] = s; }
        var out = al.map(function (di) { return { i: di, s: best[di] + P.qk * sec[di] }; });
        out.sort(function (x, y) { return y.s - x.s || x.i - y.i; });
        return out.slice(0, 50);
    }
    function qbBlend(ix, out, raw, lock) {          // the main list keeps its scores by position (callers' thresholds keep their meaning)
        var hs = qbHits(ix, raw); if (!hs.length) return out;
        var sim = nul(), inm = nul(), sc = out.map(function (h) { return h.score; }), L = [];
        for (var a = 0; a < hs.length; a++) sim[hs[a].i] = hs[a].s;
        for (var r = 0; r < out.length; r++) { var h = out[r], sv = sim[h.i]; inm[h.i] = 1; L.push({ h: h, r: r, k: 1 / (P.qf + r + 1) + (sv != null ? P.qw * Math.pow(sv, P.qg) : 0) + (h.i === lock ? 1 : 0) }); }
        for (var b = 0; b < hs.length; b++) { if (inm[hs[b].i]) continue; var d = ix.docs[hs[b].i]; L.push({ h: { id: d.id, i: d.i, score: 0, cov: 0, faq: -1, fs: 0 }, r: out.length + b, k: P.qw * Math.pow(hs[b].s, P.qg) }); }
        L.sort(function (x, y) { return y.k - x.k || x.r - y.r; });
        var last = sc.length ? sc[sc.length - 1] : 0;
        return L.map(function (z, r1) { var h = z.h, s = sim[h.i] || 0; h.score = !sc.length ? P.qs * s : (r1 < sc.length ? sc[r1] : last); if (r1 === 0 && s >= P.qc && h.cov < s) h.cov = Math.min(1, s); return h; });
    }
    // browser: fetch the bank once the page has settled (it is not needed to open the helper or the reader; a search before it lands runs without it)
    if (typeof document !== 'undefined' && document.createElement) {
        var QB_SRC = (function () { var c = document.currentScript, s = c && c.src ? String(c.src) : ''; return (s ? s.replace(/[^\/]*$/, '') : 'js/') + 'spb-enc-qbank.js?v=20261005qb1'; })();
        var qbLoad = function () { if (QBD || (typeof window !== 'undefined' && window.SPB_ENC_QBANK)) return; var t = document.createElement('script'); t.src = QB_SRC; t.async = true; (document.head || document.documentElement).appendChild(t); };
        if (document.readyState === 'complete') setTimeout(qbLoad, 1500); else if (typeof window !== 'undefined' && window.addEventListener) window.addEventListener('load', function () { setTimeout(qbLoad, 1500); });
    }
    return { VERSION: VERSION, qbank: qbank, qbHits: qbHits, build: build, search: search, spell: spell, rewrite: rewrite, REWRITE: REWRITE, toks: toks, norm: norm, stem: stem, fix: fix, intent: intentOf, P: P, LFW: LFW, FIELDS: FIELDS, KIND_PRIOR: KIND_PRIOR, DOM_PRIOR: DOM_PRIOR, EXPAND: EXPAND, SYN: SYN, STOP: STOP };
});
