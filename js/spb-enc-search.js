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
    var VERSION = '2026-10-13.customer-topic-r11';
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
        bonnet: 'hood', boot: 'trunk', rims: 'wheels', rim: 'wheel', alloys: 'wheels', tyres: 'tires', tyre: 'tire', undid: 'undo', undone: 'undo', undos: 'undo', redid: 'redo', wetter: 'wet', lit: 'lighting', pic: 'picture', pics: 'picture', pix: 'picture' };   // ROUND2: casual past tenses / slang (tune split)
    // near-synonyms: a query word also matches these (at EXP_W of its weight)
    // W2-ANSWER 2026-10-09: 'by hand' / 'myself' ~ 'manually' ~ 'custom'; 'made / created' ~ output files
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
        sandpaper: ['rough', 'matte'], massive: ['big', 'huge', 'scale'], enormous: ['big', 'huge', 'scale'], giant: ['big', 'huge', 'scale'], gigantic: ['big', 'huge', 'scale'], reflection: ['shine', 'gloss', 'spec'], grainy: ['rough', 'grain'], lasso: ['select', 'shape', 'draw'], wet: ['gloss', 'clearcoat'], cheap: ['pop', 'boring', 'flat'], expensive: ['premium', 'pop', 'depth'],
         hand: ['manual', 'manually', 'custom', 'type'], manually: ['hand', 'custom', 'type'], manual: ['hand', 'custom'], myself: ['hand', 'manual', 'custom'], made: ['output', 'created', 'saved'], created: ['output', 'made', 'saved'], produced: ['output', 'created'] };
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
        qlock: 1.5,
        // R5 (ENC_SEARCH_LAB ROUND 5): a definition question ('what is X', 'explain X', 'X explained') x idef for the article whose summary opens
        // 'X is ...' (d.def). Plateau 2.5-4 on the r5 paraphrases with DEV/HELD/held2/held3/casual unchanged or up; 3 taken. 1 = off
        idef: 3,
        // R2 2026-10-07: learned re-rank (rrBlend) of the first rn entries; rr 0 = off
        rr: 0, rn: 3, ra: 2.362, rt: -0.474, rs: 2.644, rc: 1.131, rg: -2
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
    var W3_QLOW = 0.88, S3 = null, S3d = null;
    function syn3(w) { var D = null; try { D = qbData(); } catch (e) { D = null; } if (!D || !D.syn) return null; if (S3d !== D) { S3 = nul(); S3d = D; for (var k in D.syn) { var kk = word(k); S3[kk] = (S3[kk] || []).concat(D.syn[k]); if (kk !== k && !S3[k]) S3[k] = D.syn[k]; } } return S3[w] || S3[word(w)] || null; }
    // ---- W3-ANSWER 2026-10-09 (reworded question collapse: dev howto 83% -> hidden 30%): fold texting slang, ESL grammar and swearing BEFORE the typo repair + rewrite,
    // then REWRITE3 rows (phrasing class -> the article's own vocabulary). Kill switch: window.SPB_ENC_NOW3A = true.  Every row is a PHRASING CLASS, never one test question.
    function w3Off() { try { return typeof window !== 'undefined' && !!window.SPB_ENC_NOW3A; } catch (e) { return false; } }
    var W3_FOLD = [
        [/\b(?:jack|diddly) ?(?:shit|squat)\b/gi, 'nothing'],
        [/\bcheap[- ]?ass\b/gi, 'cheap'],
        [/\b(?:the |in the |on the |what the |why the |how the |who the )(?:f+u+c*k+\w*|fuk\w*|fck\w*|hell|heck|h3ll|fudge|freak|frick|shit|crap|damn|dang)\b/gi, ' '],
        [/\b(?:f+u+c*k+\w*|fuk\w*|fck\w*|fking|shit\w*|sh1t\w*|bullshit|crap\w*|damn\w*|dammit|goddamn\w*|bloody|freakin\w*|frickin\w*|friggin\w*|wtf|wth|tf|ffs|hell|heck)\b/gi, ' '],
        [/\b(?:u|yu|ya|yuo)\b/gi, 'you'],
        [/\bur\b/gi, 'your'],
        [/\bhw\b/gi, 'how'],
        [/\b(?:wat|wut|wht|waht|whut)\b/gi, 'what'],
        [/\b(?:wher|whre|whers|wheres)\b/gi, 'where'],
        [/\b(?:cn|cna|kan)\b/gi, 'can'],
        [/\b(?:cud|cld)\b/gi, 'could'],
        [/\b(?:shud|shld)\b/gi, 'should'],
        [/\b(?:pls|plz+|pleez|pleaze|plss)\b/gi, 'please'],
        [/\b(?:halp|hlp|helpp+)\b/gi, 'help'],
        [/\b(?:thx|thnx)\b/gi, 'thanks'],
        [/\babt\b/gi, 'about'],
        [/\b(?:bc|bcz)\b/gi, 'because'],
        [/\bw\/o\b/gi, 'without'],
        [/\bw\//gi, 'with '],
        [/\b(?:n|nd)\b/gi, 'and'],
        [/\b(in|on|up|out)2\b/gi, '$1to'],
        [/\b(how|hw|want|need|have|has|trying|try|going|gonna|able|wanna|way|me|us|used|like|ready|time)\s+2\b/gi, '$1 to'],
        [/\b(?:me|i) (want|need|wish|like|no|not|cant|cannot|dont)\b/gi, 'i $1'],
        [/\bi am (want|need|wish|like)\b/gi, 'i $1'],
        [/\bis possible\b/gi, 'is it possible'],
        [/\bhow i (make|do|put|add|change|get|set|use|turn|remove|delete|save|open|load|fix|stop|paint|apply|find|see|show|hide|move|copy|share|send|install|start|export|import)\b/gi, 'how do i $1'],
        [/\bno (work|working|show|showing|start|open|load|loading|appear|change|changing)\b/gi, 'not $1'],
        [/\bcannot\b/gi, 'cant'],
        [/\bnot know\b/gi, 'dont know'],
        [/\b(?:kill|nuke|axe|ditch|scrap|trash|toss|dump|bin|zap|wipe out|take out|lose|drop)\b(?=[^.?!]{0,14}\b(?:shine|shiny|gloss|glossy|glossiness|reflect\w*|sheen)\b)/gi, 'remove'],
        [/\b(?:kill|nuke|axe|ditch|scrap|trash|toss|dump|bin|zap|wipe out|take out)\b(?=[^.?!]{0,12}\b(?:zones?|layers?|patterns?|logos?|text|numbers?)\b)/gi, 'remove'],
        [/\b(?:slap|stick|throw|plop|stamp|glue|tack|bolt)(?:s|ed|ing)?\b(?=[^.?!]{0,20}\b(?:on|onto|over|across)\b)/gi, 'put'],
        [/\b(?:crank|bump|jack|boost|pump)\b(?= (?:it |the \w+ )?up\b)/gi, 'increase'],
        [/\b(?:steal|grab|snag|lift|sample)\b(?=[^.?!]{0,16}\b(?:colou?rs?|shade|hue)\b)/gi, 'pick'],
        [/\b(?:spit|spits|spat|churn|churns|belch)(?: out)?\b(?=[^.?!]{0,16}\b(?:files?|tga|images?|output)\b)/gi, 'create'],
    ];
    function fold3(raw) { raw = String(raw == null ? '' : raw); if (w3Off()) return raw; var o = raw; for (var i = 0; i < W3_FOLD.length; i++) { W3_FOLD[i][0].lastIndex = 0; o = o.replace(W3_FOLD[i][0], W3_FOLD[i][1]); } o = o.replace(/\s+/g, ' ').trim(); return o.length >= 2 ? o : raw; }
    var REWRITE3 = [
        [/\b(?:bonnet|boot lid|decklid)\b/gi, '$& hood trunk'],
        [/\b(?:rims?|alloys?|hubs?)\b/gi, '$& wheels'],
        [/\b(?:remove|kill|lose|stop|no more|without|get rid of|take off|reduce|less)\b[^.?!]{0,14}\b(?:shine|shiny|gloss|glossy|sheen|reflect\w*)\b|\b(?:not|isnt|no longer)\s+(?:be |so |too |very )?(?:shiny|glossy|reflective)\b|\b(?:dull|flat|dead)\s+(?:finish|look|paint)\b|\bnon[- ]?(?:shiny|gloss\w*|reflective)\b/gi, '$& matte flat no shine'],
        [/\b(?:colou?rs?|looks?|paint)\b[^.?!]{0,30}\b(?:not|isnt|arent|dont|doesnt|never)\b[^.?!]{0,10}\b(?:same|match\w*|equal|alike|like|right|true)\b|\b(?:differ\w*|different|off|wrong|washed|faded|dull|darker|lighter|brighter)\b[^.?!]{0,25}\b(?:iracing|sim|game|track|race|session)\b/gi, '$& colours look different in iracing'],
        [/\b(?:what|which) (?:files?|stuff|things?|images?|tgas?)\b[^.?!]{0,30}\b(?:come|comes|spit|spits|make|makes|produce\w*|output\w*|create\w*|generate\w*|give\w*|get)\b|\b(?:files?|tgas?) (?:it|the render|render) (?:make|makes|create\w*|produce\w*|spits?|gives?)\b/gi, '$& output files car tga car_num spec'],
        [/\b(?:tutorial|walk ?through|guided|step[- ]by[- ]step|training wheels?|hand ?hold\w*|onboarding|beginner guide|learn(?:ing)? the app)\b/gi, '$& tutorial training wheels first paint'],
        [/\bbrush\b[^.?!]{0,16}\b(?:bigger|larger|smaller|thicker|thinner|wider|size|big|small|softer|harder|hardness)\b|\b(?:bigger|larger|smaller|thicker|thinner|wider|resize)\b[^.?!]{0,10}\bbrush\b/gi, '$& brush size hardness opacity tool options'],
        [/\b(?:before|old|original|previous)\b[^.?!]{0,12}\b(?:vs|versus|and|or|to|against|with)\b[^.?!]{0,10}\b(?:after|new|current|edited)\b|\bflip(?:ping)? between\b[^.?!]{0,25}\b(?:old|new|before|after|original)\b|\bcompare\b[^.?!]{0,20}\b(?:old|new|before|after|original|version)\b/gi, '$& compare before after'],
        [/\b(?:two|2|second|double|multiple|several|more than one|extra|another)\b[^.?!]{0,12}\b(?:finish\w*|bases?|materials?|looks?)\b[^.?!]{0,30}\b(?:one|same|single|each|a)\b[^.?!]{0,8}\b(?:zone|area|part|spot|place|region|panel)\b|\b(?:stack\w*|layer\w*|combin\w*|mix\w*|blend\w*|put)\b[^.?!]{0,14}\b(?:finish\w*|bases?)\b[^.?!]{0,14}\b(?:on top|together|over|each other|both|one)\b/gi, '$& second base stack two finishes'],
        [/\b(?:every|all|each|whole|entire)\b[^.?!]{0,10}\b(?:zones?|areas?|parts?|panels?)\b[^.?!]{0,30}\b(?:same|one|single|identical)\b[^.?!]{0,10}\b(?:finish\w*|look|material|base)\b|\b(?:same|one|single)\b[^.?!]{0,10}\b(?:finish\w*|look)\b[^.?!]{0,25}\b(?:every\w*|all|each|whole)\b/gi, '$& same finish all zones'],
        [/\b(?:dont|do not|cant|cannot|dunno|no idea|not sure|unsure|stuck deciding|undecided)\b[^.?!]{0,14}\b(?:know|decide|choose|pick|name|think|which|what)\b[^.?!]{0,14}\b(?:finish\w*|look|style|material|paint)\b/gi, '$& finish ideas suggestions random'],
        [/\bwhat (?:cars?|vehicles?|models?|series|classes)\b[^.?!]{0,25}\b(?:can|could|do|does|are|is|will|support\w*|work\w*|paint\w*|available|included|covered)\b|\bwhich cars?\b/gi, '$& supported cars list'],
        [/\b(?:only|just|solely|limit\w*|restrict\w*|isolat\w*|single)\b[^.?!]{0,25}\b(?:hood|bonnet|roof|doors?|trunk|boot|fenders?|bumpers?|spoiler|wing|panels?|mirrors?|part|parts|area|section)\b/gi, '$& named parts one part zone'],
        [/\b(?:crash\w*|wreck\w*|dents?|dings?|dinged|bent|damage\w*|hit (?:a |the )?wall|collision|crumpl\w*)\b/gi, '$& crash damage'],
        [/\b(?:glow\w*|neon|light(?:s|ing)? up|lit up|luminous|fluorescent|phosphor\w*)\b/gi, '$& glow in the dark'],
        [/\b(?:what|which)\b[^.?!]{0,10}\b(?:g|green)\b[^.?!]{0,16}\b(?:do|does|mean|control\w*|for|is)\b|\b(?:g|green) (?:channel|value|slider)\b/gi, '$& roughness channel'],
        [/\b(?:copy|clone|duplicate|recreate|replicate|reproduce|imitate|match|steal|emulate|same as|look like|based on)\b[^.?!]{0,25}\b(?:livery|liveries|design|scheme|paint ?job|look)\b[^.?!]{0,30}\b(?:photo|picture|pic|image|screenshot|online|internet|real|reference|someone|another|other)\b|\b(?:photo|picture|pic|image|screenshot|reference)\b[^.?!]{0,25}\b(?:copy|clone|recreate|replicate|match|reproduce)\b/gi, '$& match photo reference livery copy picture'],
        [/\b(?:change|alter|switch|swap|edit|different|new|other|recolou?r)\b[^.?!]{0,12}\bcolou?rs?\b[^.?!]{0,12}\b(?:of )?(?:the |a |my )?(?:finish\w*|base|material)\b|\bfinish\b[^.?!]{0,25}\b(?:wont|doesnt|isnt|not)\b[^.?!]{0,12}\b(?:take|use|accept|show|apply)\b[^.?!]{0,10}\bcolou?r/gi, '$& finish colour change'],
        /* W3-ANSWER 2026-10-09: rotate-pattern row dropped (cost 1 sealed item, no probe gain) */
        [/\bzones?\b[^.?!]{0,30}\b(?:nothing|no change|not (?:changing|working|doing|showing|affect\w*|applying|do)|doesnt (?:do|change|work|show|apply)|same|unchanged|dead|useless)\b|\b(?:nothing|no change|unchanged)\b[^.?!]{0,20}\bzones?\b/gi, '$& zone not showing nothing changed'],
        [/\b(?:camo\w*|woodland|flecktarn)\b/gi, '$& camo pattern recipe'],
        [/\b(?:hide|show|unhide|switch|turn|toggle|disable|enable)\b[^.?!]{0,16}\blayers?\b|\blayers?\b[^.?!]{0,14}\b(?:hide|hidden|invisible|visible|on or off|toggle)\b/gi, '$& layer visibility eye on off'],
        [/\b(?:see[- ]?through|translucen\w*|fade (?:a |the |this )?layer|partly (?:transparent|visible)|half[- ]visible|less visible|blend mode)\b/gi, '$& layer opacity blend mode'],
        [/\biron rules?\b/gi, '$& spec iron rules three'],
    ];
    // ---- W3-ANSWER 2026-10-09: question canonicaliser + route wrapper (installed on window.SpbOfflineAnswer the moment js/spb-offline-answer.js assigns it; no edit to that file).
    // Terse / ESL / slang question shapes ("undo how", "zone is what", "lasso how use", "eyedropper where", "zone no change why", "left side red right blue can",
    // "The stripes go the wrong way, how can I turn them?") become "how do I ... / what is ... / where is ... / why ... / can I ..." so the answer router sees a QUESTION, never an edit.
    // Kill switch: window.SPB_ENC_NOW3A = true (also drops fold3 + REWRITE3).  Before -> after: see _easy_claude_work/eval/w3answer/REPORT.md.
    var W3_QW = /^(?:how|what|whats|where|wheres|why|when|which|who|whom|can|could|is|are|am|do|does|did|will|would|should|shall|may|might|has|have|any|anyone|anybody|is it possible|are there|is there)\b/i;
    var W3_IMP = /^(?:make|paint|turn|change|put|set|give|colou?r|recolou?r|swap|switch|add|remove|delete|apply|wrap|spray|fill|draw|create|do|use|try|keep|leave|dont|don't|never|also|then|now|and|but|ok|okay|yes|no|yeah|yep|nope|thanks|thank|hi|hey|hello)\b/i;
    var W3_VERB0 = /^(?:make|get|add|remove|change|put|set|use|turn|do|save|load|open|delete|undo|redo|fix|stop|paint|apply|find|see|show|hide|move|copy|share|send|install|start|export|import|rotate|resize|scale|mirror|duplicate|clone|flip|zoom|pick|select|draw|create|build|reset|restore|render|print|upload|download|update|activate|record|swap|merge|group|lock|unlock|mute|rename)\b/i;
    var W3_SYMV = /\b(?:(?:not|wont|won't|doesnt|doesn't|isnt|isn't|cant|can't|never|no)\s+(?:start\w*|open\w*|load\w*|show\w*|work\w*|appear\w*|render\w*|sav\w*|updat\w*|launch\w*|chang\w*|running)|crash\w*|freez\w*|froze|frozen|stuck|blank|missing|vanish\w*|disappear\w*|error\w*|broken|fails?|failed|dead)\b/i;
    var W3_SYMS = /\b(?:app|program|software|booth|shokker|render\w*|preview|zones?|files?|export|psd|tga|png|iracing|sim|game|update|install\w*|licen[cs]e|activation|folder|spec|numbers?|sponsors?|logos?|layers?)\b/i;
    function qcanon(text, env) {
        var t = String(text == null ? '' : text).trim(); if (!t || t.length > 220 || w3Off()) return null;
        var f = fold3(t), body = f.replace(/[\s?!.,;:]+$/, ''), mm, out = null;
        if (!body || body.split(/\s+/).length > 30) return null;
        if (env && env.pending && body.split(/\s+/).length <= 3) return null;          // a short answer to our own question stays an answer
        if (W3_QW.test(body)) return f !== t ? f : null;          // already a question: only the folded spelling goes on
        var isImp = W3_IMP.test(body);
        if ((mm = /^(.{3,}?)\s+how((?:\s+(?:do|does|can|could|would|should|to|you|i|we|it|is|use|fix|work|works|please|thanks|then|set|change|make|get|add|remove))*)$/i.exec(body)) && !W3_QW.test(mm[1])) {
            var tv = /\b(use|fix|set|change|make|get|add|remove)\b/i.exec(mm[2] || ''), hd = mm[1].trim();
            out = 'how do i ' + (W3_VERB0.test(hd) ? '' : (tv ? tv[1].toLowerCase() + ' ' : '')) + hd;
        } else if (isImp) {
            out = null;
        } else if ((mm = /^(.{2,}?)\s+(?:(is|are|mean|means|does|do)\s+)?(?:what|whats)(?:\s+(?:is|are|that|this|mean|means|for|exactly|even|actually|then))*$/i.exec(body)) && !W3_QW.test(mm[1])) {
            out = /^mean/i.test(mm[2] || '') ? 'what does ' + mm[1].trim() + ' mean' : 'what is ' + mm[1].trim();
        } else if ((mm = /^(.{2,}?)\s+(?:is\s+|are\s+)?where(?:\s+(?:is|are|do|can|i|to|find|located|at|put|go|it))*$/i.exec(body)) && !W3_QW.test(mm[1])) {
            out = 'where is ' + mm[1].trim();
        } else if ((mm = /^(.{3,}?)\s+why(?:\s+(?:is|does|do|tho|though|so|it))*$/i.exec(body)) && !W3_QW.test(mm[1])) {
            out = 'why ' + mm[1].trim();
        } else if ((mm = /^(.{3,}?)\s+(?:can|possible|is possible|can or not|can or no|can or cant|possible or not|doable|able)$/i.exec(body)) && !W3_QW.test(mm[1])) {
            out = 'can i ' + mm[1].trim();
        } else if ((mm = /^(.{8,}?)[,;.]\s+((?:how (?:do|can|could|would|should|to)|what (?:is|are|does|do)|where (?:is|are|do|can)|why (?:is|does|do|are)|is it possible|is there a way|do i need|am i able|can i)\b[^?.!]*)$/i.exec(body)) && !W3_QW.test(mm[1])) {
            out = mm[2].trim() + '? ' + mm[1].trim();
        }
        if (!out && !isImp && body.split(/\s+/).length <= 10 && W3_SYMV.test(body) && W3_SYMS.test(body) && !/\b(?:make|paint|turn|change|set|give|colou?r|recolou?r|swap|add|remove|delete|apply|wrap|fill)\b/i.test(body)) out = 'why ' + body;          // a terse app / file / render symptom ("app no start", "preview not showing") is a support question
        return out;
    }
    function w3Wrap(OA) {
        if (!OA || OA.__w3 || typeof OA.route !== 'function') return;
        var r0 = OA.route;
        OA.route = function (text, env) {
            // Owner recovery11: a verified factual reader must see the buyer's
            // original words before the legacy keyword expansion can replace
            // an Undo complaint with crash-damage advice. Preserve the complete
            // reader/caller pipeline, context and safety checks; no action is
            // accepted merely because a fact reader recognized the topic.
            if (!w3Off() && typeof OA.customerFact === 'function') {
                var factual = null;
                try { factual = OA.customerFact(text, env); } catch (eFact) { factual = null; }
                if (factual && factual.customerFact && factual.customerOriginalWords && !(factual.steps && factual.steps.length) && !factual.w27kitNow && (factual.cls === 'ANSWER' || factual.cls === 'ASK' || factual.cls === 'ONLINE'))
                    return r0.call(this, text, env);
            }
            if (!w3Off()) { var t2 = null; try { t2 = qcanon(text, env); } catch (e) { t2 = null; } if (t2 && t2 !== text) { var res = r0.call(this, t2, env); try { if (res && typeof res === 'object' && !res.w3canon) res.w3canon = t2; } catch (e2) {} return res; } }
            return r0.apply(this, arguments);
        };
        OA.__w3 = 1;
    }
    (function w3Install() {
        try {
            if (typeof window === 'undefined') return;
            var Wn = window, cur = Wn.SpbOfflineAnswer;
            if (cur && cur.route) { w3Wrap(cur); return; }
            Object.defineProperty(Wn, 'SpbOfflineAnswer', { configurable: true, enumerable: true, get: function () { return cur; }, set: function (v) { cur = v; try { w3Wrap(v); } catch (e) {} } });
        } catch (e) {}
    })();
    var REWRITE = [
        // Recovery11: customer topic wording shared with the Python ranker.
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=how\b)(?=.*\bsave\b)(?=.*\b(?:work|project|tomorrow|open|lose)\b).*$/i, 'Save, Open, Import Recipe and projects'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\b(?:tp|trading ?paints|league|viewers?|viewrs|other drivers|opponents)\b)(?=.*\b(?:custom number|default cars|half|others|other drivers|viewers?|viewrs)\b).*$/i, 'Trading Paints questions'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\b(?:skins|liveries|paints|drivers|roster)\b)(?=.*\b(?:different|each|every|multiple|20|twenty)\b)(?=.*\bnumbers?\b).*$/i, 'Team schemes: reuse settings without assuming layout transfer'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=how\b)(?=.*\b(?:mirror|super shiny)\b)(?=.*\b(?:shiny|car|chrome|material)\b).*$/i, 'Chrome with your source colours (spec only)'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=how\b)(?=.*\bundo\b)(?=.*\b(?:this|clicked|wreck\w*|wrong|everything|last)\b).*$/i, 'How do I undo?'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=how\b)(?=.*\b(?:hood|one part)\b)(?=.*\b(?:just|only|not everything)\b)(?=.*\b(?:change|colou?r|finish)\b).*$/i, 'Edit one thing without touching sponsors'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=how\b)(?=.*\bnumber\b)(?=.*\b(?:change|just|only)\b)(?!.*\b(?:customer|user|member)\s+id\b).*$/i, 'Put a race number on your car'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=how\b)(?=.*\b(?:fade|gradient)\b)(?=.*\bcolou?rs?\b).*$/i, 'Make a gradient'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\bhelper\b)(?=.*\b(?:do it|steps|everything|do (?:it |this |that )?for me)\b).*$/i, 'Offline helper, AI key or Claude: what each does'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\b(?:layered|layers)\b)(?=.*\b(?:write|export|file back|only tga|output)\b).*$/i, 'Photoshop round trip and other exports'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\b(?:million|many|finishes|pick|choose)\b)(?=.*\b(?:first|which one|start|pick first)\b).*$/i, 'The finish picker, library and browser'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\b(?:file|output)\b)(?=.*\b(?:cant find|can.t find|cannot find|where|lost|wher)\b)(?=.*\b(?:made|render|output)\b).*$/i, 'Where the files go: the iRacing car folder'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\b(?:tp|trading ?paints)\b)(?=.*\b(?:mip|spec|shine)\b)(?=.*\b(?:file type|filetype|wrong|upload|asking|make|tga)\b).*$/i, 'The .mip file'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?!.*\b(?:confirm\w*|reset)\b)(?=.*\b(?:hood|part|zone)\b)(?=.*\b(?:changed.*nothing|nothing changed|not showing|not working|no effect)\b).*$/i, 'My zone does not show   nothing changed'],
        [/^\s*(?=(?:how|what|why|where|which|does|do|is|are|can|could|i have|i changed|i rendered|i cant|i can.t|i cannot|my|the|it says|it looks|tp|half|carbon|preview)\b)(?!.*(?:[.;]|\bthen\b|\band\s+please\b)\s*(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo)\b)(?!(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:paint|apply|set|hide|show|merge|flatten|render|run|undo|redo|export|save)\b)(?=.*\b(?:carbon|finish|pattern|texture)\b)(?=.*\b(?:fishing net|too big|too large|huge|coarse)\b).*$/i, 'Everything looks tiny or huge (base scale)'],
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
        [/^(?![^.?!]*\b(chrome|finish(es)?|metallic|candy|flake|spec|pattern)\b)[^.?!]*?(\b(numbers?|sponsors?|logos?|decals?|lettering)\b[^.?!]{0,30}\b(stand out|pop|readable|legible|more visible|(easier|easy|harder) to (see|read|spot)|show up better|so they show up|hard to read|cant read|can t read|blends?( in| into)?|get(s|ting)? lost)\b|\b(stand out|pop|readable|legible|read)\b[^.?!]{0,20}\b(numbers?|sponsors?|lettering)\b)/gi, '$& readable number contrast'],
        // R4B-ADDELEM: make / create / draw / do / paint / put / want + a drawn design element (stripes, flames, checkers, chevrons, stars) = the add-it how-to. Not numbers / logos / sponsors: 'make my numbers chrome', 'paint my numbers red' edit art that is already there
        [/\b(make|making|create|draw|do|paint|put|want|need)\s+(a |an |some |two |twin |three |the |my )?(\w+ )?(stripes?|pinstripes?|flames?|checkers?|chevrons?|stars?)\b/gi, '$& add $4'],
        // R5 rows begin (ENC_SEARCH_LAB ROUND 5)
        // EXPLAIN
        [/^\s*(can|could|would|will) (you|u) (please )?explain\b|\btell me (more )?about\b/gi, 'what is'],
        // EXPORT
        [/^(?![^.?!]*\b(projects?|shokk|templates?|zip|psd|presets?|where|not|cant|wont|doesnt|isnt|dont)\b)[^.?!]*\b(save|saving|keep|store)\b[^.?!]*\b(iracing|sim|game|race|racing)\b/gi, '$& export to iracing'],
        // RESIZE
        [/\b(numbers?|logos?|sponsors?|decals?|stickers?|lettering)\b[^.?!]{0,30}\b(bigger|smaller|larger|resize|resized|scale up|scale down|shrink|enlarge|too big|too small|too large)\b|\b(bigger|smaller|larger|resize|scale up|scale down|shrink|enlarge)\b[^.?!]{0,25}\b(numbers?|logos?|sponsors?|decals?|stickers?|lettering)\b/gi, '$& move or resize a number or logo'],
        // WHERE
        [/^\s*(where|wheres)\b(?![^.?!]*\b(change|changes|edit|set|adjust|sliders?|save|saved|folder|files?)\b)[^.?!]*\b(spec( map)?|metallic|metal|roughness|rough|clearcoat|channels?)\b[^.?!]*/gi, '$& see view'],
        // VISIBLE
        [/^(?![^.?!]*\b(numbers?|sponsors?|logos?|decals?|lettering|cant|dont|doesnt|not|never|others|friends|buddy)\b)[^.?!]*(\b(see|spot|notice|find|recogni[sz]e|pick out)\s+(me|us|my car|our car|the car|it)\b[^.?!]*\b(across|far|distance|away|track|pack|field|traffic|stands|grid)\b|\b(visible|noticeable|easy to (see|spot|find)|seen|spotted)\b[^.?!]*\b(far|across|distance|away|track|pack|field|traffic)\b)/gi, '$& stand out in a pack be seen'],
        // CHECK
        [/^\s*(is|are)\s+(that|this|it|my (car|zone|paint|finish|spec))\b(?![^.?!]*\b(better|best|should|good|nicer|possible|too|why)\b)[^.?!]*\b(metallic|metal|flat|matte|shiny|glossy|gloss|chrome|satin|rough)\b|\b(tell|check|see|know|show)\s+(if|whether)\b[^.?!]*\b(metallic|metal|shiny|matte|flat|glossy|rough|clearcoat)\b/gi, '$& check spec channel view'],
        // CHOICE
        [/^(?!\s*(is|are) (that|this|it|my)\b)[^.?!]*?\b(gloss|glossy|satin|matte|flat|metallic|metal|pearl|candy|chrome)\s*(or|vs|versus|v|compared to)\s*(gloss|glossy|satin|matte|flat|metallic|metal|pearl|candy|chrome)\b/gi, '$& finishes compared'],
        // ONBODY
        [/\b(red|blue|green|black|white|yellow|orange|purple|pink|gr[ae]y|silver|gold|bronze|copper)\s*(or|vs|versus)\s*(red|blue|green|black|white|yellow|orange|purple|pink|gr[ae]y|silver|gold|bronze|copper)\b[^.?!]{0,25}\b(on|for|with)\s+(a |an |my |the )?(red|blue|green|black|white|yellow|orange|purple|pink|gr[ae]y|silver|gold|dark|light)\b/gi, '$& accent colours for a coloured car'],
        // DIFF
        [/(?:\b(?:whats|what is|what s|wats|what are)\s+(?:the\s+|a\s+)?)?\b(dif+e?r[ae]nces?|diff)\s+(between|from)\s+(a |an |the )?(\w+)\s+(and|vs|or)\s+(a |an |the )?(\w+)( layers?| ones?| things?| options?| types?)?\b/gi, '$4 vs $7 difference between $4 and $7'],
        // R5 rows end
        // R6 rows begin (HELPER QUESTIONS LANE 2026-10-06: troubleshooting / iRacing / edge phrasing classes)
        // FILLER
        [/\b(i am|im|i feel) (so |very |really |super |kinda )?(sad|angry|mad|upset|frustrated|annoyed|desperate)\b|\b(this is|its|it is) (so |really )?(dumb|stupid|annoying|ridiculous|frustrating)\b|\b(lol|lmao|smh|pls help|please help)\b/gi, ''],
        // COLDIFF
        [/^(?!\s*(please |pls |can you |could you )?(make|turn|set|change)\b)[^.?!]*\b(more|less|too|way|much|very|super)\s+(saturated|vivid|bright|brighter|dark|darker|dull|duller|washed out|faded|pale|neon)\b[^.?!]*\b(sim|iracing|game|track|ingame)\b|\b(colou?rs?|paint|it)\b[^.?!]{0,30}\bdifferent\b[^.?!]{0,30}\b(than|from|to)\b[^.?!]{0,30}\b(program|app|preview|shokker|photoshop|ps|editor|file|screen)\b/gi, '$& colours look different in iracing'],
        // WHITECAR
        [/\b(car|paint)\b[^.?!]{0,30}\b(is|shows|looks|turned|went|comes out|came out)\s+(just |all |completely |totally |plain )?(white|blank)\b[^.?!]*\b(iracing|sim|game|session|race|render|rendr)\b|\b(iracing|sim|game|session)\b[^.?!]*\b(car|paint)\b[^.?!]{0,30}\b(is|shows|looks|turned|went)\s+(just |all |completely |totally |plain )?(white|blank)\b/gi, '$& paint not showing in iracing'],
        // ZONESPLIT
        [/^(?!\s*(please |pls |can you |could you )?(make|turn|paint|change|give|put|add|set)\b)[^.?!]*(\bhalf (of )?(my|the) car\b[^.?!]*\bhalf\b|\b(hood|roof|top|front|sides?|rear|one panel|some panels)\b[^.?!]{0,40}\b(but|and|while)\b[^.?!]{0,30}\b(bottom|sides|rest|other panels|other parts|lower|rear|back)\b[^.?!]{0,30}\b(wrong|different|dull|old|another|other|gr[ae]y|not)\b|\bone colou?r\b[^.?!]{0,25}\banother\b)/gi, '$& two zones overlap zone priority everything else'],
        // SPECBLACK
        [/\bspec\b[^.?!]{0,25}\b(is |looks |comes out |came out |turned |went )?(all |completely |totally |just |pure )?(black|white|empty|blank|solid)\b/gi, '$& read spec map by colour'],
        // MIRRORED
        [/\b(numbers?|lettering|text|letters|logos?|sponsors?|decals?|writing)\b[^.?!]{0,30}\b(backwards|reversed|mirrored|upside down|reads wrong|wrong way round)\b|\b(backwards|reversed|mirrored|upside down)\b[^.?!]{0,20}\b(numbers?|lettering|text|logos?|sponsors?|decals?)\b/gi, '$& mirror flip symmetry'],
        // STALEPREV
        [/\b(still|keeps?)\s+(shows?|showing|has|having)\s+(the )?(old|previous|same|last)\s+(colou?r|paint|finish|look|version)\b[^.?!]*\bpreview\b|\bpreview\b[^.?!]*\b(still|keeps?)\s+(shows?|showing)\s+(the )?(old|previous|same)\b/gi, '$& preview not changing change did nothing stale preview'],
        // HALO
        [/\b(glowing|glow|bright|white|black|dark|light|weird|thin|jagged|coloured|colored)\s+(line|lines|edge|edges|outline|fringe|halo|seam|border|gap)\b[^.?!]{0,40}\b(where|between|around|along)\b/gi, '$& zone edge halo tolerance refine selection'],
        // WEARSIM
        [/\b(mud|dirt|grime|wear|scratches|scuffs|rust|weathering|weathered|dust)\b[^.?!]{0,40}\b(not showing|cant see|can t see|invisible|barely|doesnt show|does not show|gone)\b|\b(clean|spotless)\b[^.?!]{0,40}\b(mud|dirt|grime|scratches|rust|weathering)\b/gi, '$& wear weathering worn paint scuffed'],
        // GRIME
        [/\b(road grime|grime|tyre rubber|tire rubber|rubber marks|brake dust|scuffs?|scuffed|beat up|beaten up|battle scars|battle damage|dents)\b/gi, '$& wear weathered'],
        // DEPLOY
        [/\bdeploy(ed)?( now)?\b[^.?!]*\b(nothing|where|didnt|did not|doesnt|does not)\b|\b(where|nothing)\b[^.?!]*\bdeploy(ed)?\b/gi, '$& deploy now where files go'],
        // LOSTFILES
        [/\b(cant|can t|cannot|can not|couldnt|unable to)\s+find\s+(my |the )?(files?|paints?|renders?|work|projects?|tgas?|designs?)\b/gi, '$& where files go lost files'],
        // GREYPICK
        [/\b(everything|it|the car|whole car|my car|the zone)\b[^.?!]{0,20}?\b((is|turned|turns|went|goes|looks|stays|stayed|comes out)\s+)?(all )?(gr[ae]y|white|silver)\b.{0,40}\b(picked|chose|chosen|selected|set|wanted|asked for)\b/gi, '$& where does the colour come from finish ignores my colour'],
        // TPSPLIT
        [/\b(some|half|other|most|a few|the other)\s+(of my |of the )?(drivers|people|teammates|team ?mates|guys|racers|friends)\b[^.?!]{0,40}\b(see|get|have|show)\b[^.?!]{0,30}\b(gr[ae]y|white|default|plain|stock|nothing|wrong)\b/gi, '$& other drivers do not see your paint'],
        // PRICE
        [/^\s*(is (it|this|shokker|the app) free|how much (is it|does it cost|is shokker|is the app)|whats the price|what does it cost)\s*[?!.]*\s*$/gi, '$& how much does shokker cost'],
        // PIRACY
        [/\b(crack|keygen|pirate|pirated|torrent|serial key|free (licen[cs]e|key)|bypass (the )?(licen[cs]e|activation))\b(?![^.?!]*\b(paint|look|finish|pattern|effect|texture)\b)/gi, '$& licence activation'],
        // REALCAR
        [/\b(paint|wrap|design|do)\b[^.?!]{0,20}\b(my )?(real|actual|physical)\s+(car|vehicle|truck)\b|\bin my (garage|driveway)\b|\b3d (model|print\w*)\b/gi, '$& real car iracing only what shokker does not do'],
        // NEWCARS
        [/\bnew (iracing )?(season )?cars?\b|\bnext.?gen\b|\breleased cars?\b|\b(new|latest) season\b[^.?!]{0,30}\bcars?\b/gi, '$& which cars shokker knows teach the parts'],
        // PRIVACY
        [/\b(train|training) (ai|the ai|your ai|models?|on my)\b|\bprivacy\b|\b(designs?|paints?|pictures?|files?)\b[^.?!]{0,25}\b(going to|go to|sent to|uploaded to|stored on) (your|a|the) (server|cloud)\b/gi, '$& what the ai sees privacy'],
        // BOTQ
        [/\b(are|r) (you|u) (a )?(real )?(person|human|bot|robot|machine|chatgpt|gpt)\b/gi, '$& what the helper can and cannot do'],
        // BITDEPTH
        [/\b(bit ?depth|(8|16|24|32)[ -]?bits?|colou?r mode|alpha channel|with alpha)\b(?=[^.?!]*\b(tga|file|paint|spec|export|iracing)\b)|\b(tga|file)\b[^.?!]{0,30}\b(bit ?depth|(8|16|24|32)[ -]?bits?|alpha)\b/gi, '$& tga image files'],
        // FILENAME
        [/\b(drag|copy|put|move|drop|paste)\b[^.?!]{0,25}\b(tga|files?|paint)\b[^.?!]{0,30}\bfolder\b[^.?!]{0,20}\b(myself|manually|by hand)\b|\b(what|which)\s+(file ?)?name\b[^.?!]{0,30}\b(need|needs|should|must)\b/gi, '$& file names output files'],
        // TWOCARS
        [/\bsame (paint|livery|design|scheme|skin)\b[^.?!]{0,15}\b(on|for|to)\b[^.?!]{0,10}\b(two|2|another|different|second|both)\s+(cars?|models?)\b|\b(paint|livery|design|scheme|skin)\b[^.?!]{0,20}\b(another|a different) (car|model)\b/gi, '$& choose template each car'],
        // RES4K
        [/\b(4096|4k|8k|higher res(olution)?|bigger than 2048|more than 2048|above 2048)\b/gi, '$& render size 2048 template'],
        // SPECWHERE
        [/\bwhere\b[^.?!]{0,20}\b(put|place|copy|save)\b[^.?!]{0,20}\bspec\b/gi, '$& output files car folder'],
        // MATTEBLK
        [/\b(matte|flat|satin)\s+(flat\s+)?black\b/gi, '$& make the whole car matte black'],
        // SAVELOOK
        [/\b(save|keep|store|reuse)\b[^.?!]{0,30}\b(finish|look|zone setup|setup|style)\b[^.?!]{0,40}\b(again|later|next time|other cars?|another car|different car)\b/gi, '$& shokk library save a recipe'],
        // UISIZE
        [/^(?![^.?!]*\b(numbers?|logos?|sponsors?|decals?|car|hood|roof|doors?|sides?|patterns?|textures?|lettering|stripes?)\b)[^.?!]*(\b(buttons?|fonts?|panels?|ui|interface|menus?|icons?)\b[^.?!]{0,20}\b(too )?(big|large|huge|small|tiny)\b|\b(small|tiny|laptop)\s+(screen|monitor|display)\b)/gi, '$& ui size panels'],
        // SENDDRV
        [/\b(send|give|share)\b[^.?!]{0,25}\b(paint|livery|skin|design|files?)\b[^.?!]{0,20}\b(to )?(my |our |the )?(drivers?|teammates?|team ?mates?|friends?|buddy|buddies|league)\b/gi, '$& trading paints and mip files'],
        // SPECLOGO
        [/\b(stop|keep|prevent|protect|without)\b[^.?!]{0,30}\bspec\b[^.?!]{0,40}\b(logos?|sponsors?|numbers?|decals?)\b|\bspec\b[^.?!]{0,30}\b(over|covering|ruining|messing up)\b[^.?!]{0,15}\b(my )?(logos?|sponsors?|numbers?|decals?)\b/gi, '$& auto protect smart separate'],
        // WHEREGO
        [/\bwhere did (my |the )?(render|paint|file|tga|livery)s? go\b|\bwhere (do|does) (my |the )?(renders?|paints?|files?|tgas?) (go|end up|get saved)\b/gi, '$& where the files go car folder'],
        // ZONEPART
        [/\bpart\b[^.?!]{0,80}\b(and|but) (the )?(other )?part\b[^.?!]{0,15}\b(new|old|different|wrong|missing)\b|\b(old|original|source) (paint|colou?r)\b[^.?!]{0,30}\b(shows? through|peeks? through|still shows? (on|in) (some|parts|places|spots))\b/gi, '$& pixels no zone claimed everything else'],
        // SPECDEF
        [/^\s*(is|are) (the |a )?spec( map)?s? (like|just|a|an|the same as)\b|\bhow does (the sim|iracing|the game|it) use (the |my )?spec( map)?\b/gi, '$& what the spec map is'],
        // ANGLE
        [/\b(from|at) (different|other|another|an?|every) (angles?|views?)\b|\bdepending on (the )?(angle|view)\b|\bchanges? (colou?r )?(with|by) (the )?(angle|view)\b/gi, '$& colour shift and angle reveal'],
        // NUMDRV
        [/\b(change|swap|different|each|per|new)\b[^.?!]{0,30}\b(car )?numbers?\b[^.?!]{0,30}\b(for|per|on) (each|every|all|different)\b[^.?!]{0,10}\b(drivers?|cars?|teammates?)\b/gi, '$& put a race number custom number'],
        // TEAMPC
        [/\b(looks?|is|are)\s+different\s+(on|for|between)\s+(each|every|other|all|my|our)\b[^.?!]{0,20}\b(pcs?|computers?|drivers?|machines?|screens?|teammates?)\b/gi, '$& colours look different in iracing colours differ'],
        // WHATBASE
        [/^\s*what (is|are) (a |the )?bases?\b(?! (scale|colou?r|material|finish))/gi, '$& four kinds of finish base vs pattern'],
        // SPECSEE
        [/\b(where|what place|how)\b[^.?!]{0,20}\b(see|view|look at|check|find)\b[^.?!]{0,10}\b(the |my )?spec( map)?\b(?!\s+(value|values|number|numbers|of|at))/gi, '$& spec channel views preview'],
        // PAYALL
        [/\b(do|does|will|must) (all |every |the other |my )?(drivers?|teammates?|everyone|people|league|members)\b[^.?!]{0,30}\b(need|have|got) to (buy|pay|own|install|get|have)\b/gi, '$& other drivers do not need shokker trading paints'],
        // PAINTBOTH
        [/\bpaint (both|all (of )?(them|those|these|the cars)|any car|every car)\b|\bpaint (both|all) (cars?|series|classes)\b/gi, '$& which cars shokker knows supported cars'],
        // LOGIN
        [/\b(log ?in(to)?|sign ?in(to)?|access)\b[^.?!]{0,20}\b(my )?(iracing|trading paints|tp)\b( account)?/gi, '$& what the helper can and cannot do trading paints'],
        // WHOLEJOB
        [/\b(do|finish) (all of |my )?(entire|whole)\b[^.?!]{0,20}\b(work|psd|job|livery|project)\b|\b(go|going) (to|for) lunch\b|\bwhile i (am |m )?(away|gone|asleep|at lunch)\b/gi, '$& what the helper can and cannot do'],
        // REALTRACK
        [/\b(real|actual)\b[^.?!]{0,15}\b(track|map|circuit)\b|\btrack map\b/gi, '$& what shokker does not do iracing only'],
        // FIRSTPAINT
        [/\b(my )?(first|1st) (paint|livery|car paint|design)\b|\bno idea (where|how) to start\b|\bwhere (do i|to|should i) (even )?start\b/gi, '$& first paint getting started'],
        // SHEENVS
        [/\b(matte|satin|gloss|glossy|flat|semi.?gloss|eggshell)\b[^.?!]{0,12}\b(and|vs|versus|or)\b[^.?!]{0,6}\b(matte|satin|gloss|glossy|flat|semi.?gloss|eggshell)\b/gi, '$& gloss satin matte compared'],
        // SPECPAT
        [/\bwhat(s| is| does)? (a |the )?spec patterns? (do|does|mean|for)\b|\bwhat(s| is) (a |the )?spec pattern\b/gi, '$& what is a spec pattern'],
        // NOIDEA
        [/\b(i have |i ve |have |got )?no idea\b(?= (where|how|what) )/gi, 'not sure'],
        // ZONELAYER
        [/\bwhat(s| is) (a |the )?zone\b[^a-z]{0,4}(is )?(that|it|this)? ?(like|the same as|same as) (a )?layers?\b/gi, '$& what is a zone zones vs layers'],
        // RENAME
        [/\b(call|name|rename) it\b[^.?!]{0,20}\.tga\b|\b(need|needs|has to have|have to have) (my |the )?(number|id|customer id) in (the|its) (file ?)?name\b/gi, '$& file names customer id output files'],
        // RENDEREVERY
        [/\b(render|rendr)\b[^.?!]{0,10}\b(every|each) (time|change|tweak)\b|\bevery time i (change|tweak|edit)\b[^.?!]{0,40}\b(render|sim|iracing)\b/gi, '$& preview vs render reload in iracing'],
        // WHEREFILE
        [/^\s*(so |and |ok |but )?where (is|are|s) (my |the )?(files?|paints?|tgas?|renders?)\s*[?!.]*\s*$|^\s*(so |and |ok |but )?where (my |the )?(files?|paints?|tgas?) (is|are)\s*[?!.]*\s*$/gi, '$& where the files go car folder lost files'],
        // R6 rows end
    ];
    function rewrite(raw) { for (var i = 0; i < REWRITE.length; i++) { REWRITE[i][0].lastIndex = 0; raw = raw.replace(REWRITE[i][0], REWRITE[i][1]); } if (!w3Off()) for (var i3 = 0; i3 < REWRITE3.length; i3++) { REWRITE3[i3][0].lastIndex = 0; raw = raw.replace(REWRITE3[i3][0], REWRITE3[i3][1]); } return raw.replace(/\s+/g, ' ').trim(); }
    // R5 (ENC_SEARCH_LAB ROUND 5): a summary that opens with a definition of its subject: 'Pearl is ...', 'A rally car is ...' (subject <= 4 words)
    var RE_DEF = /^(?:a |an |the )?([a-z][a-z-]*(?: [a-z][a-z-]*){0,3}) (?:is|are|means) /i;
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
            var dm = RE_DEF.exec(str(a.summary)); d.def = dm ? toks(dm[1]) : [];          // R5: the summary opens by defining its subject ('Pearl is a gentle metallic glow ...')
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
    function known(ix, w) { if (ix.sw[w] || STOP[w] || SYN[w] || (!w3Off() && syn3(w))) return true; var t = toks(w); return !t.length || (t.length === 1 && idfOf(ix, t[0]) != null); }
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
        var raw = cue(rewrite(spell(ix, fold3(text), opts).text)), q0 = toks(raw), q = [], qn, seen = nul();
        for (var i = 0; i < q0.length; i++) { var w = fix(ix, q0[i]); q.push(w); }
        for (var cj = 0; cj + 1 < q.length; cj++) if (q[cj] === 'trad' && q[cj + 1] === 'paint') q.splice(cj, 2, 'tradingpaint');   // a typo'd 'trading panits' misses norm()'s compound; rejoin it after typo repair
        var qs = []; for (var i1 = 0; i1 < q.length; i1++) if (!seen[q[i1]]) { seen[q[i1]] = 1; qs.push(q[i1]); }
        if (!qs.length) return [];
        qn = ' ' + q.join(' ') + ' ';
        var it = intentOf(raw);
        // expansions per query word (stemmed, indexed only)
        var alt = [], mass = 0, qw = [];
        for (var a = 0; a < qs.length; a++) {
            var w0 = qs[a], ex = [], src = EXPAND[w0] || []; if (!w3Off() && idfOf(ix, w0) == null) { var s3 = syn3(w0); if (s3) src = src.concat(s3); }          /* W3-ANSWER 2026-10-09: out-of-vocabulary word -> corpus words (Haiku-drafted lexicon in the qbank data) */
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
            if (P.idef !== 1 && it.what && !it.prob && d.def.length && qs.length <= d.def.length + 1 && d.def.every(function (t) { return seen[t]; })) m *= P.idef;          // R5: 'what is X' / 'explain X' -> the article whose summary says 'X is ...'
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
        if (P.rr && !ix.prefix) out = rrBlend(ix, out);          // R2 2026-10-07: learned re-rank (sibling articles); helper / server indexes only, not the reader's search-as-you-type
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
    // W8QA-QPROB-BEGIN
    // ---- W8-QA 2026-10-09 (lane W8-QA; kill window.SPB_ENC_NOW8): P(this message is a buyer QUESTION / trouble report about the app, not an edit order). A small logistic model
    // (binary word, word-pair, char-3gram and first-word features; ~2k weights shipped as qcls in js/spb-enc-qbank.js, fitted by _easy_claude_work/eval/w8qa/clf2.py on the
    // TRAIN split + Haiku-written buyer questions; held-out AUC 0.95 on reworded questions vs dev edit orders). null = no model loaded yet / killed. Used by the offline
    // helper's w8qPost (js/spb-offline-answer.js): a question the edit readers turned into an ask / decline gets answered from the encyclopedia.
    function qprob(text) {
        try {
            if (typeof window !== 'undefined' && window.SPB_ENC_NOW8) return null;
            var D = qbData(), m = D && D.qcls; if (!m || !m.w) return null;
            var raw = String(text == null ? '' : text), s = raw.toLowerCase().replace(/['\u2019]/g, '').replace(/[^a-z0-9#]+/g, ' ').trim(), ws = s ? s.split(' ') : [], f = nul(), i, k, w, p, z = m.b || 0, W = m.w;
            for (i = 0; i < ws.length; i++) {
                w = ws[i]; f['w' + w] = 1; if (i + 1 < ws.length) f['b' + w + ' ' + ws[i + 1]] = 1;
                p = ' ' + w + ' '; for (k = 0; k + 3 <= p.length; k++) f['c' + p.substr(k, 3)] = 1;
            }
            if (ws.length) f['f' + ws[0]] = 1;
            f['n' + Math.min(ws.length, 20)] = 1;
            if (raw.indexOf('?') >= 0) f['q?'] = 1;
            for (k in f) if (W[k] !== undefined) z += W[k];
            return 1 / (1 + Math.exp(-z));
        } catch (e) { return null; }
    }
    // W8QA-QPROB-END
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
        var B = D.bank, qa = [], fs = [], qwt = [], df = nul(), post = nul();
        for (var a = 0; a < B.length; a++) { var L = (B[a][1] || []).concat(w3Off() ? [] : (B[a][2] || [])), nL = (B[a][1] || []).length; for (var j = 0; j < L.length; j++) { var t = qtoks(L[j], null); if (!t.length) continue; var F = qfeat(t); qa.push(a); fs.push(F); qwt.push(j < nL ? 1 : W3_QLOW);          /* W3-ANSWER 2026-10-09: drafted (Haiku) paraphrases weigh W3_QLOW so the hand-written bank wins ties */ for (var x = 0; x < F.f.length; x++) df[F.f[x]] = (df[F.f[x]] || 0) + 1; } }
        var N = fs.length;
        for (var qi = 0; qi < N; qi++) { var v = qvec(fs[qi], df, N); for (var y = 0; y < v.length; y++) (post[v[y][0]] || (post[v[y][0]] = [])).push(qi, v[y][1]); }
        QB = { key: key, qwt: qwt, ids: B.map(function (r) { return r[0]; }), qa: qa, df: df, N: N, post: post };
        return QB;
    }
    function qbHits(ix, raw) {          // [{i, s}] best first: the ix docs whose bank questions are nearest to the (typo-repaired) question words
        var Q = qbBuild(), q = qtoks(raw, ix); if (!Q || !q.length) return [];
        if (!ix.qb || ix.qb.Q !== Q) { var by = nul(); for (var d = 0; d < ix.docs.length; d++) by[ix.docs[d].id] = d; ix.qb = { Q: Q, m: Q.ids.map(function (id) { return by[id] == null ? -1 : by[id]; }) }; }
        var v = qvec(qfeat(q), Q.df, Q.N), acc = new Float64Array(Q.N), ql = [];          // every product is > 0, so 0 = not reached yet
        for (var i = 0; i < v.length; i++) { var L = Q.post[v[i][0]], w = v[i][1]; for (var j = 0; j < L.length; j += 2) { var qi = L[j]; if (acc[qi] === 0) ql.push(qi); acc[qi] += w * L[j + 1]; } }
        var best = nul(), sec = nul(), al = [];          // an article's similarity = its nearest question (+ qk x its second nearest)
        for (var k = 0; k < ql.length; k++) { var di = ix.qb.m[Q.qa[ql[k]]], s = acc[ql[k]] * (Q.qwt ? Q.qwt[ql[k]] : 1); if (di < 0 || s < P.qt) continue; if (best[di] == null) { best[di] = s; sec[di] = 0; al.push(di); } else if (s > best[di]) { sec[di] = best[di]; best[di] = s; } else if (s > sec[di]) sec[di] = s; }
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
    // R2 2026-10-07 (ARTICLE RANKER): LEARNED RE-RANK - picks the winner among the first rn (3) entries and promotes it; the old winner and
    // the rest keep their order, so the top 3 shown never changes. key = ra/(rank+1) + rt (rank 0) + rs x score/top score + rc x cov + rg for a
    // generated help_* / controls_* page. Weights = listwise softmax fit over the 8,051 labelled corpus answer rows (_easy_claude_work/eval/r2/fixg.py,
    // 5-fold GROUP cross-validation: a row's source FAQ / alias / template is never in its own training fold); rg -2 taken from a real-grader sweep.
    // Measured (R1 routing): corpus answer-id gold 67.1 -> 70.4 %, bank B-kind p2 160 -> 164, p1 193 -> 194, dev 82 -> 83, train =, harm =.
    // TRADE-OFF: the corpus never and the bank almost never (2 of 599 golds) name a generated page, but search_lab/bench.jsonl does
    // (helper-mode dev top-1 91.2 -> 83.4); the reader's prefix index is exempt (reader bench unchanged). P.rr = 0 turns it off.
    // A question-kNN vote over the same corpus was tried and adds nothing under strict leave-one-out (the corpus questions ARE the articles'
    // FAQs / aliases restyled, which the index already holds) - see _easy_claude_work/eval/r2/PROGRESS.md.
    function rrBlend(ix, out) {
        var n = Math.min(P.rn, out.length); if (n < 2) return out;
        var s0 = out[0].score || 1, sc = [], bj = 0, bk = -1e9, r;
        for (r = 0; r < n; r++) sc.push(out[r].score);
        for (r = 0; r < n; r++) { var h = out[r], d = ix.docs[h.i], k = P.ra / (r + 1) + (r === 0 ? P.rt : 0) + P.rs * sc[r] / s0 + P.rc * (h.cov || 0) + (d && (d.help || d.gen) ? P.rg : 0); if (k > bk) { bk = k; bj = r; } }
        if (!bj) return out;
        var top = out.splice(bj, 1)[0]; out.unshift(top);          // promote only: the old winner and the rest keep their order (it stays in the top 3)
        for (r = 0; r < n; r++) out[r].score = sc[r];
        return out;
    }
    // browser: fetch the bank once the page has settled (it is not needed to open the helper or the reader; a search before it lands runs without it)
    if (typeof document !== 'undefined' && document.createElement) {
        var QB_SRC = (function () { var c = document.currentScript, s = c && c.src ? String(c.src) : ''; return (s ? s.replace(/[^\/]*$/, '') : 'js/') + 'spb-enc-qbank.js?v=20261010k4'; })(); // [orchestrator 2026-10-10] token bumped for KNOW-REV pass 5 qbank; KNOW-2 2026-10-10: bumped again (qbank +82 questions for the new tools)
        var qbLoad = function () { if (QBD || (typeof window !== 'undefined' && window.SPB_ENC_QBANK)) return; var t = document.createElement('script'); t.src = QB_SRC; t.async = true; (document.head || document.documentElement).appendChild(t); };
        if (document.readyState === 'complete') setTimeout(qbLoad, 1500); else if (typeof window !== 'undefined' && window.addEventListener) window.addEventListener('load', function () { setTimeout(qbLoad, 1500); });
    }
    return { VERSION: VERSION, fold3: fold3, REWRITE3: REWRITE3, qcanon: qcanon, qbank: qbank, qprob: qprob, qbHits: qbHits, build: build, search: search, spell: spell, rewrite: rewrite, REWRITE: REWRITE, toks: toks, norm: norm, stem: stem, fix: fix, intent: intentOf, P: P, LFW: LFW, FIELDS: FIELDS, KIND_PRIOR: KIND_PRIOR, DOM_PRIOR: DOM_PRIOR, EXPAND: EXPAND, SYN: SYN, STOP: STOP };
});
