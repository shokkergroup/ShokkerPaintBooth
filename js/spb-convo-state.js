/* js/spb-convo-state.js -- HELPER V3 S4 2026-10-05: ONE conversation store (window.SpbConvo).
 * docs/handoff_reports/HELPER_ARCHITECTURE_V3.md section 2.3 + stage S4. Owner-approved stage.
 *
 * WHY: multi-turn follow-ups were the bank's worst class (~10% of items passing). "make it white instead", "same on the right",
 * "the second one", "thinner", "change both to gold", "go back" lost their referent because every path kept its own memory:
 *   - js/spb-pro-ai.js        lastEditCtx() (log scan), _offlineLast, RECENT, HIST, _cmpAsk, entry.options, entry.elem
 *   - js/spb-offline-answer.js lastCtx() / ctxHistory() / lastUndone() (log scans) + CS {pending, topic, list, nopaint}
 *   - js/spb-pro-edit.js       env.last (= the pro-ai lastEditCtx) read by the editor's it/them/same/more/less rules
 *   - MCP (pro-ai mcpApply)   only the log entry; the model STATE had recent_changes strings and nothing else
 * This file is the single store all of them write (commit / offer / note / undone / redone) and read (resolve / view / legacy shims).
 * It owns NO pixels and applies nothing: the executor commits, the reporter offers, the producers resolve.
 *
 * Loaded BEFORE js/spb-pro-ai.js. Pure data; safe in Node (the harness _easy_claude_work/eval/convo_store/convo_test.js loads it with vm).
 * Off switch: SPB_CONVO = '0' (window var or localStorage key) -> SpbConvo.on() is false and every shim falls back to the legacy reader.
 */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var V = 1, KEEP_TURNS = 40, KEEP_CHANGES = 24, OFFER_TTL_MS = 600000, PENDING_TTL_MS = 600000;

    // ------------------------------------------------------------------ small helpers
    function flag(name, dflt) {
        try { if (W[name] !== undefined && W[name] !== null) return String(W[name]); } catch (e) {}
        try { if (W.localStorage) { var v = W.localStorage.getItem(name); if (v !== null && v !== undefined) return String(v); } } catch (e2) {}
        return dflt;
    }
    function on() { return flag('SPB_CONVO', '1') !== '0'; }
    function clone(o) { try { return o == null ? o : JSON.parse(JSON.stringify(o)); } catch (e) { return null; } }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && x !== '' && o.indexOf(x) === -1) o.push(x); }); return o; }
    function low(t) { return String(t || '').toLowerCase().replace(/[‘’]/g, "'"); }
    var CLOCK = function () { return Date.now(); };

    // ------------------------------------------------------------------ vocabulary (mirrors _easy_claude_work/eval/bank/normalise.py so the store and the grader name things alike)
    var SIDES = ['left side', 'right side'];
    var PARTS = ['hood', 'roof', 'trunk', 'bed', 'front bumper', 'rear bumper', 'spoiler', 'left side', 'right side'];
    var PART_WORDS = [
        [/\bleft (?:side )?(?:doors?|panels?|sides?|quarters?)\b|\bleft side\b|\bdriver'?s? side\b/g, ['left side']],
        [/\bright (?:side )?(?:doors?|panels?|sides?|quarters?)\b|\bright side\b|\bpassenger'?s? side\b/g, ['right side']],
        [/\bfront bumper\b|\bfront splitter\b|\bsplitter\b|\bnose(?: wing)?\b|\bfront end\b/g, ['front bumper']],
        [/\brear bumper\b|\bback bumper\b|\bbumper at the (?:bottom|back|rear)\b|\btail\b|\brear end\b|\bback end\b/g, ['rear bumper']],
        [/\b(?:both )?bumpers\b/g, ['front bumper', 'rear bumper']],
        [/\bbumper\b/g, 'BUMPER'],
        [/\bwing sides\b|\b(?:top |rear )?wings?\b|\bspoiler\b/g, ['spoiler']],
        [/\bhood\b|\bbonnet\b/g, ['hood']],
        [/\broof\b|\b(?:only |just )?the top\b(?! (?:of|half|edge|third))/g, ['roof']],
        [/\btrunk(?: lid)?\b|\bdeck ?lid\b|\bboot\b/g, ['trunk']],
        [/\bbed(?: rails?)?\b/g, ['bed']],
        [/\bcab sides\b/g, SIDES],
        [/\bcab\b/g, ['roof', 'left side', 'right side']],
        [/\b(?:both )?doors?\b|\bside ?panels?\b|\b(?:both )?sides\b|\bfenders?\b|\bbeltline\b/g, SIDES],
        [/\bside\b/g, 'SIDE']
    ];
    var OBJECT_WORDS = [[/\bmirrors?\b/g, 'mirrors'], [/\bwheels?\b|\brims?\b/g, 'wheels'], [/\bwindows?(?: frames?)?\b|\bwind ?shield\b|\bglass\b/g, 'windows'], [/\btrim\b/g, 'trim'], [/\bdiffuser\b/g, 'diffuser']];
    var ELEMENT_WORDS = [[/\bnumbers?\b|\bnumber (?:circle|panel)s?\b/g, 'numbers'], [/\bsponsors?\b|\bcontingenc\w*/g, 'sponsors'], [/\blogos?\b|\bbadges?\b/g, 'logos'], [/\bstripes\b/g, 'stripes'], [/\bdecals?\b|\bstickers?\b/g, 'decals']];
    var GRAPHIC_WORDS = [[/\bpin ?lines?\b|\bpinstripes?\b/g, 'pinline'], [/\boutlines?\b|\bstroke\b/g, 'outline'], [/\bstripe\b/g, 'stripe']];
    var DEFAULT_LAYERS = ['Yellow Base', 'Black Base', 'White Base', 'Logos', 'Numbers', 'Pitbox Colors', 'Car_Decal', 'Color Change Logos', 'Base Color', 'Base'];
    var WHOLE_RE = /\b(?:whole|entire|full) (?:car|thing|body|livery)\b|\beverything\b|\beverywhere\b|\ball over\b|\bthe body\b|\ball of it\b|\b(?:the|my|whole) car\b(?! (?:parts?|map))|^(?:make |do |paint )?car\b|\bmake car\b|\bthe car (?:is )?not all\b|\b(?:make|paint|do) (?:a|my|the) (?:\w+ )?car\b(?! (?:parts?|map))/;
    var NAMED = {
        'red': 'red', 'dark red': 'red', 'darker red': 'red', 'light red': 'red', 'burgundy': 'red', 'maroon': 'red', 'crimson': 'red', 'scarlet': 'red', 'red-orange': 'orange',
        'orange': 'orange', 'yellow': 'yellow', 'gold': 'gold', 'green': 'green', 'neon green': 'green', 'lime': 'green', 'olive': 'green', 'mint': 'green',
        'teal': 'teal', 'cyan': 'teal', 'turquoise': 'teal', 'blue': 'blue', 'dark blue': 'blue', 'light blue': 'blue', 'powder blue': 'blue', 'navy': 'blue', 'sky blue': 'blue', 'royal blue': 'blue',
        'purple': 'purple', 'violet': 'purple', 'magenta': 'pink', 'pink': 'pink', 'white': 'white', 'off-white': 'white', 'ivory': 'white', 'black': 'black', 'grey': 'grey', 'gray': 'grey',
        'charcoal': 'grey', 'gunmetal': 'grey', 'silver': 'silver', 'tan': 'brown', 'brown': 'brown', 'bronze': 'brown', 'copper': 'orange', 'rainbow': 'rainbow'
    };
    var NAMED_KEYS = Object.keys(NAMED).sort(function (a, b) { return b.length - a.length; });
    var FINISH_WORDS = [
        ['chrome', /\bchrome\b|\bmirror finish\b/], ['candy', /\bcandy\b/], ['pearl', /\bpearl\w*\b/], ['carbon', /\bcarbon\b|\bforged\b|\btwill\b/],
        ['matte', /\bmatte?\b|\bflat\b|\bprimer\b/], ['satin', /\bsatin\b/], ['gloss', /\bgloss(?:y)?\b|\bwet look\b/], ['metallic', /\bmetallic\b|\bmetal ?flake\b|\bbrushed\b/],
        ['camo', /\bcamo\b/], ['flames', /\bflames?\b/], ['holo', /\bholo\w*\b|\biridescent\b/]
    ];
    function hexFamily(h) {
        h = String(h || '').replace('#', ''); if (!/^[0-9a-f]{6}$/i.test(h)) return null;
        var r = parseInt(h.slice(0, 2), 16) / 255, g = parseInt(h.slice(2, 4), 16) / 255, b = parseInt(h.slice(4, 6), 16) / 255;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), v = mx, s = mx ? (mx - mn) / mx : 0, hh = 0, d = mx - mn;
        if (d) { if (mx === r) hh = ((g - b) / d) % 6; else if (mx === g) hh = (b - r) / d + 2; else hh = (r - g) / d + 4; hh *= 60; if (hh < 0) hh += 360; }
        if (v < 0.2) return 'black';
        if (s < 0.15) return v > 0.86 ? 'white' : (v > 0.6 ? 'silver' : 'grey');
        if (hh < 14 || hh >= 345) return 'red'; if (hh < 40) return v < 0.5 ? 'brown' : 'orange'; if (hh < 50) return 'gold'; if (hh < 66) return 'yellow';
        if (hh < 165) return 'green'; if (hh < 195) return 'teal'; if (hh < 255) return 'blue'; if (hh < 290) return 'purple'; return 'pink';
    }
    function coloursOf(t) {          // -> [{word, hex, families}] in the order said
        var s = low(t), out = [], m, hx = /#[0-9a-f]{6}\b/gi;
        while ((m = hx.exec(s))) out.push({ word: m[0], hex: m[0], families: uniq([hexFamily(m[0])]), at: m.index });
        var s2 = s.replace(/#[0-9a-f]{6}\b/gi, function (x) { return new Array(x.length + 1).join(' '); });
        NAMED_KEYS.forEach(function (k) {
            var re = new RegExp('(^|[^a-z-])(' + k.replace(/[-]/g, '\\-') + ')(?![a-z-])', 'g'), mm;
            while ((mm = re.exec(s2))) { var at = mm.index + mm[1].length; out.push({ word: k, hex: null, families: [NAMED[k]], at: at }); s2 = s2.slice(0, at) + new Array(k.length + 1).join(' ') + s2.slice(at + k.length); re.lastIndex = 0; }
        });
        out.sort(function (a, b) { return a.at - b.at; });
        return out.map(function (c) { return { word: c.word, hex: c.hex, families: c.families }; });
    }
    function finishOf(t) { var s = low(t), f = null; FINISH_WORDS.forEach(function (fw) { if (!f && fw[1].test(s)) f = fw[0]; }); return f; }

    // ------------------------------------------------------------------ typo tolerance (buyers type "insteda", "smakler", "doosr", "trunnk", "whtie", "chroem")
    var FUZZ_VOCAB = ['bumper', 'bumpers', 'spoiler', 'trunk', 'doors', 'sides', 'mirror', 'mirrors', 'splitter', 'numbers', 'number', 'sponsors', 'stripes', 'stripe', 'outline', 'pinline',
        'chrome', 'candy', 'pearl', 'matte', 'satin', 'gloss', 'glossy', 'metallic', 'carbon', 'forged', 'brushed', 'white', 'black', 'green', 'purple', 'yellow', 'orange', 'silver',
        'again', 'instead', 'thinner', 'thicker', 'bigger', 'smaller', 'darker', 'lighter', 'brighter', 'finer', 'softer', 'shinier', 'glossier', 'second', 'third', 'first', 'other',
        'opposite', 'right', 'front', 'whole', 'everything', 'gradient', 'redo', 'undo', 'better', 'sparkle', 'glitter', 'shine', 'shiny', 'flames', 'wheels', 'wheel', 'bottom', 'lower', 'roof', 'hood'];
    var FUZZ_COMMON = { good: 1, wood: 1, food: 1, mood: 1, hook: 1, look: 1, book: 1, took: 1, proof: 1, light: 1, night: 1, might: 1, sight: 1, fight: 1, tight: 1, eight: 1, frame: 1, frames: 1, order: 1, other: 1,
        sizes: 1, tides: 1, rides: 1, sites: 1, hides: 1, aside: 1, sided: 1, wider: 1, rider: 1, there: 1, these: 1, those: 1, where: 1, which: 1, while: 1, white: 1, write: 1, quite: 1, great: 1, green: 1,
        trunks: 1, drunk: 1, trick: 1, truck: 1, track: 1, block: 1, black: 1, blank: 1, about: 1, again: 1, agin: 0, gain: 1, hour: 1, offer: 1, after: 1, under: 1, never: 1, every: 1, cover: 1, lover: 1, power: 1,
        fine: 1, finer: 1, liner: 1, diner: 1, miner: 1, inner: 1, winner: 1, dinner: 1, thing: 1, things: 1, think: 1, first: 1, third: 1, second: 1, front: 1, right: 1, roof: 1, hood: 1, undo: 1, redo: 1,
        spoil: 1, number: 1, numbers: 1, lower: 1, slower: 1, flower: 1, tower: 1, mower: 1, power2: 1, shone: 1, phone: 1, shore: 1, store: 1, share: 1, shire: 1, spine: 1, swine: 1, satan: 1, salon: 1,
        bitter: 1, better: 1, butter: 1, letter: 1, setter: 1, matter: 1, latter: 1, water: 1, later: 1, faster: 1, master: 1, mister: 1, sister: 1, ladder: 1, harder: 1, wonder: 1, color: 1, colour: 1,
        bright: 1, fright: 1, wright: 1, brighten: 1, wheeled: 1, loser: 1, glows: 1, gloves: 1, handy: 1, sandy: 1, dandy: 1, randy: 1, latte: 1, stain: 1, glass: 1, floss: 1, gross: 1, greet: 1, greed: 1, slack: 1, whale: 1, whine: 1, fellow: 1, mellow: 1,
        thinker: 1, ticker: 1, digger: 1, fighter: 1, tighter: 1, thirds: 1, others: 1, spoiled: 1, bumped: 1, jumper: 1, frost: 1, forget: 1, forgot: 1, carton: 1, crushed: 1, rushed: 1, blushed: 1, flushed: 1 };          // "crushed" = SCALE in owner vocabulary, never brushed
    function dl1(a, b) {          // Damerau-Levenshtein <= 1 (fast path, no matrix)
        if (a === b) return 0; var la = a.length, lb = b.length; if (Math.abs(la - lb) > 1) return 2;
        var i = 0; while (i < la && i < lb && a[i] === b[i]) i++;
        if (la === lb) { if (a.slice(i + 1) === b.slice(i + 1)) return 1; if (i + 1 < la && a[i] === b[i + 1] && a[i + 1] === b[i] && a.slice(i + 2) === b.slice(i + 2)) return 1; return 2; }
        if (la > lb) return a.slice(i + 1) === b.slice(i) ? 1 : 2; return b.slice(i + 1) === a.slice(i) ? 1 : 2;
    }
    var FUZZ_MAP = { insteda: 'instead', isntead: 'instead', instad: 'instead', aain: 'again', agian: 'again', agin: 'again', tinner: 'thinner', smakler: 'smaller', bihger: 'bigger', ligher: 'lighter',
        darkrr: 'darker', lighht: 'light', mate: 'matte', marte: 'matte', matet: 'matte', mstte: 'matte', sain: 'satin', glods: 'gloss', gkoss: 'gloss', chrrome: 'chrome', chorme: 'chrome', chroem: 'chrome',
        chrone: 'chrome', crhome: 'chrome', chroome: 'chrome', chromme: 'chrome', cany: 'candy', canndy: 'candy', paerl: 'pearl', csrbon: 'carbon', cabon: 'carbon', carbpn: 'carbon', forgwd: 'forged', carbn: 'carbon',
        gren: 'green', geeen: 'green', geeen2: 'green', blak: 'black', blaack: 'black', bllack: 'black', blaxk: 'black', whtie: 'white', whire: 'white', whitte: 'white', whiite: 'white', wihte: 'white',
        puple: 'purple', pyrple: 'purple', puurple: 'purple', oeange: 'orange', orqnge: 'orange', yelolw: 'yellow', yelllow: 'yellow', gary: 'gray', doosr: 'doors', doirs: 'doors', dors: 'doors', doros: 'doors',
        trunnk: 'trunk', spiler: 'spoiler', mirrorrs: 'mirrors', bupmer: 'bumper', buper: 'bumper', bumpeers: 'bumpers', bumpper: 'bumper', bumprr: 'bumper', spliyter: 'splitter', frnot: 'front', rgiht: 'right',
        nunbers: 'numbers', numbres: 'numbers', sponosr: 'sponsors', sponsosr: 'sponsors', sponors: 'sponsors', strpes: 'stripes', sttripe: 'stripe', flaems: 'flames', flamees: 'flames', loower: 'lower', loer: 'lower',
        firdt: 'first', secnd: 'second', thougt: 'thought', beter: 'better', beforre: 'before', isntread: 'instead', shne: 'shine', siny: 'shiny', shniy: 'shiny', sparke: 'sparkle', sparlke: 'sparkle', wjole: 'whole', whhole: 'whole' };
    function fixWords(t) {
        return low(t).replace(/[a-z][a-z']+/g, function (w) {
            if (FUZZ_MAP[w]) return FUZZ_MAP[w];
            if (w.length < 5 || FUZZ_COMMON[w] || FUZZ_VOCAB.indexOf(w) !== -1 || NAMED[w]) return w;
            for (var i = 0; i < FUZZ_VOCAB.length; i++) { var v = FUZZ_VOCAB[i]; if (v.length >= 5 && dl1(w, v) === 1) return v; }
            return w;
        });
    }

    // ------------------------------------------------------------------ the sentence's own reading (explicit slots + reference words)
    var NTH = { first: 0, '1st': 0, second: 1, '2nd': 1, third: 2, '3rd': 2, fourth: 3, '4th': 3, last: -1 };
    var RX = {
        closer: /^(?:(?:ok(?:ay)?|good|great|perfect|nice|fine|thanks?|thank you|thx|ty|cool|yes|yep|yeah|better|done|lol|awesome|love it|looks? good|that'?s it|leave it|perfect levae it|perfect leave it|nice one)[\s.!,]*)+$/,
        save: /\b(?:send|export|upload|save|iracing|i racing|tga|to (?:my |the )?driver|trading paints|give (?:it )?to (?:my )?driver|get it (?:in|to)|ready to (?:give|race|go)|is (?:it|this) ready)\b/,
        undo: /\bundo\b|\bun-?do\b|\brevert\b|\btake (?:it|that|this|them) back\b|\btake (?:the )?\w+ off\b|\bremove (?:it|that|them|the \w+)\b|\bget rid of\b|\bcancel (?:it|that)\b|\bas it was\b|\bwhat it was\b|\bhow it was\b|\bput (?:it|them|\w+) back\b(?! to \d)|\bgo back one\b|\bone step back\b|\b(?:go|step) back\s*[.!]*$|\bgo back(?! to (?:edit|the (?:editor|paint|car)))(?= to (?:what|how|before|the (?:old|original|way)))|\bstep back\b|\bback one\b|\bclean (?:the|it|them)\b|\bno (?:outline|stripe|pinline|flames|glow)\b/,
        redo: /\bredo\b|\bget (?:it|them) back\b|\bbring (?:it|them) back\b(?! to \d)|\bput it back on\b/,
        again: /\bagain\b|\bone more time\b|\bdo it over\b/,
        better: /\b(\w+(?: \w+)?) (?:was|looked|is|were) (?:way )?better\b|\bgo back to (?:the )?(?:first|original|old|previous|earlier)\b|\bback to (?:the )?(first|original|old|previous|both|\w+)\b/,
        nth: /(?:^|\b(?:the|use|do|keep|pick|go|try|apply|want|take|with)\s+(?:the\s+)?)(first|1st|second|2nd|third|3rd|fourth|4th|last)(?:\s+(?:one|option|version|idea|look|pick|finish|choice))?\b(?!\s+(?:of|half|time|coat))|^(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th)(?:\s+one)?\s*[.!]*$/,
        otherOne: /\bthe other (?:one|option|version|idea|look|finish)\b|\bin the other\b|\bthe other\s*$/,
        otherSide: /\b(?:the )?other side\b|\bopposite side\b|\bother way (?:a+round|around|arond)\b|\bmirror (?:it|that)\b/,
        both: /\bboth\b|\ball (?:of )?(?:those|them|three|3)\b/,
        same: /\bsame\b|\btoo\b|\balso\b|\bas well\b|\bmatch(?:ing)?\b|\bcopy\b|\bextend\b|\bditto\b|\blike the \w+\b|^(?:and|now|then|plus)\b|\b\w+ 2$/,
        instead: /\binstead\b|\brather\b|\bactually\b|\bswitch (?:it |them )?to\b|\bchange (?:it|them|that|both) to\b|\bnot \w+ but\b|\bno,? \w+$/,
        pron: /\b(?:it|its|it's|that|this|them|those|these|em|'em|they|there|that one)\b/,
        only: /\b(?:only|just)\b/,
        correction: /^(?:no+|nope|nah|wrong|sorry|wait|oops|oh wait|actually|not)\b|\bi (?:said|meant|mean|wanted|asked for)\b|\bnot the \w+|\bthat'?s the\b|\bwrong\b|\bno wait\b/,
        keepClause: /\b(?:leave|keep|don'?t touch|do not touch|not on|except|but not|stays?)\b/,
        question: /^\s*(?:(?:ok|okay|so|and|but|hmm|um|then)[\s,]+)*(?:what|whats|what's|how|why|which|where|when|is|are|does|do|did|can|could|will|would|should)\b|\?\s*$/,
        offerAsk: /\bshow me (?:both|some|a few|the|options?|ideas?|\w+ (?:vs|versus|or|and|next to|as)\b)|\b(?:two|2|three|3|some|a few) (?:options|ideas|versions|looks)\b|\bideas? for\b|\boptions? for\b|\bgive me (?:some )?(?:ideas?|options?)\b|\bwhich (?:is|looks|one is) better\b|\bwhat (?:finishes|colou?rs|patterns|looks)\b|\b(?:vs|versus)\b|\bcompare\b|\bnext to it\b|\bwhich looks better\b/
    };
    var REL = [
        ['width', -1, /\bthinner\b|\bnarrower\b|\bslimmer\b|\bthiner\b/], ['width', 1, /\bthicker\b|\bwider\b|\bfatter\b/],
        ['scale', 1, /\bbigger\b|\blarger\b|\bscale (?:it )?up\b|\bcoarser\b|\bmore big\b|\b2x\b|\bx2\b|\bnot that big\b/], ['scale', -1, /\bsmaller\b|\bscale (?:it )?down\b|\bfiner\b|\btinier\b|\bcrush\b/],
        ['lightness', -1, /\bdarker\b|\bdeeper\b|\bmore dark\b|\bless bright\b|\btoo (?:light|bright|pale)\b|\bless light\b/], ['lightness', 1, /\blighter\b|\bbrighter\b|\bpaler\b|\bless dark\b|\btoo dark\b|\bmore (?:light|bright)\b|\bnot (?:that|so) dark\b/],
        ['gloss', 1, /\bshinier\b|\bglossier\b|\bmore (?:shine|shiny|gloss|glossy|wet)\b|\beven shinier\b/], ['gloss', -1, /\bless (?:shine|shiny|gloss|glossy|reflective)\b|\btoo (?:shiny|reflective|glossy)\b|\btone (?:it )?down\b|\bduller\b|\bno more (?:shine|gloss)\b/],
        ['metal', 1, /\bmore metal(?:lic)?\b/], ['metal', -1, /\bless metal(?:lic)?\b|\bless chrome\b|\breduce the chrome\b/],
        ['softness', 1, /\bsofter\b|\bfeather\b|\bsmoother\b/], ['softness', -1, /\bsharper\b|\bharder edge\b|\bcrisper\b/],
        ['stops', 0, /\breverse (?:the )?direction\b|\bflip (?:it|the gradient|the direction)\b/],
        ['hue', 0, /\b(?:more|less) (?:red|orange|yellow|green|blue|purple|magenta|pink|teal|gold|powder)\b/],
        ['strength', -1, /\bless\b|\btoo much\b|\bnot (?:that|so|too) much\b|\bsubtle\b|\bsubtler\b|\bhalf\b|\blower the\b|\breduce\b|\bdown \d+ ?%|\bnot much\b|\ba bit of\b|\bjust a bit\b/],
        ['strength', 1, /\bmore\b|\bstronger\b|\bbump\b|\bcrank\b|\bincrease\b|\bup \d+ ?%|\bnot enough\b/]
    ];
    function relOf(s) { for (var i = 0; i < REL.length; i++) if (REL[i][2].test(s)) return { prop: REL[i][0], dir: REL[i][1], amount: /\b(?:a (?:little|bit|touch|tad)|slight(?:ly)?|bit)\b/.test(s) ? 'little' : (/\b(?:way|much|lot|even|super)\b/.test(s) ? 'lot' : (/\bhalf\b/.test(s) ? 'half' : null)) }; return null; }
    function layerNames(env) { var L = (env && env.layers) || null; if (L && L.length) return L.map(function (x) { return typeof x === 'string' ? x : (x && (x.name || x.label)) || ''; }).filter(Boolean); return DEFAULT_LAYERS; }

    // explicit Targets said in this sentence (frame Target shape: docs/handoff_reports/HELPER_ARCHITECTURE_V3.md 2.1)
    function targetsIn(raw, s, env, ctx) {
        var out = [], t = ' ' + s + ' ', parts = [], amb = [];
        // layers: exact case ("Logos"), or "<name> layer", or "<name>:" at the start
        var layers = [];
        layerNames(env).slice().sort(function (a, b) { return b.length - a.length; }).forEach(function (L) {
            var esc = L.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), ci = new RegExp('\\b' + esc + '\\b', 'i'), cs = new RegExp('\\b' + esc + '\\b');
            var lay = new RegExp('\\b' + esc + ' ?(?:layer|layr|lyr)\\b|\\b(?:layer|on|in) ' + esc + '\\b|^\\s*' + esc + '\\s*:', 'i');
            if ((lay.test(raw) || (cs.test(raw) && /[A-Z]/.test(L.charAt(0)) && !/^(?:Base|Numbers)$/.test(L))) && layers.indexOf(L) === -1) { layers.push(L); t = t.replace(new RegExp(esc.toLowerCase() + '(?: ?(?:layer|layr|lyr))?', 'g'), ' '); }
            else if (ci.test(raw) && /\blayer\b/i.test(raw) && L.length > 5 && layers.indexOf(L) === -1) { layers.push(L); t = t.replace(new RegExp(esc.toLowerCase(), 'g'), ' '); }
        });
        if (/\bthe layer\b/.test(s) && ctx && ctx.lastLayers && ctx.lastLayers.length && !layers.length) layers = ctx.lastLayers.slice();
        if (layers.length) out.push({ kind: 'layer', layers: layers });
        PART_WORDS.forEach(function (pw) {
            pw[0].lastIndex = 0; if (!pw[0].test(t)) return; pw[0].lastIndex = 0;
            if (pw[1] === 'BUMPER') amb.push('bumper'); else if (pw[1] === 'SIDE') amb.push('side'); else pw[1].forEach(function (p) { if (parts.indexOf(p) === -1) parts.push(p); });
            t = t.replace(pw[0], ' ');
        });
        var objs = []; OBJECT_WORDS.forEach(function (ow) { ow[0].lastIndex = 0; if (ow[0].test(t)) { objs.push(ow[1]); t = t.replace(ow[0], ' '); } });
        var els = []; ELEMENT_WORDS.forEach(function (ew) { ew[0].lastIndex = 0; if (ew[0].test(t)) { els.push(ew[1]); t = t.replace(ew[0], ' '); } });
        var gfx = []; GRAPHIC_WORDS.forEach(function (gw) { gw[0].lastIndex = 0; if (gw[0].test(t)) { gfx.push(gw[1]); t = t.replace(gw[0], ' '); } });
        return { parts: parts, amb: amb, layers: layers, objects: objs, elements: els, graphics: gfx, whole: WHOLE_RE.test(s), rest: t };
    }
    function read(text, env) {
        var raw = String(text || ''), s = fixWords(raw).replace(/\s+/g, ' ').trim();
        // the words after "not" / "no" are what the buyer does NOT mean ("no the roof not the hood", "not the sponsors, undo that")
        // ... and the words after "than / like / same as / to match" are the SOURCE of a look, not a target ("trunk to match the hood", "a bit darker than the roof")
        var NEG_RE = /\b(?:not|never|without|except|but not|but leave|but keep|and leave|don'?t touch|do not touch)\s+(?:on\s+|onto\s+|inside\s+|in\s+)?(?:the |my |a |any )?((?:front |rear |back |left |right |side |top |cab |bed )?[a-z_]+(?: (?:layer|bumper|side|doors?|panels?))?)/gi;
        var SRC_RE = /\b(?:than|same as|same like|(?<!\b(?:would|i'?d|i|we|you|d) )like|to match|match(?:es|ing)?|as)\s+(?:the |my |on the )?((?:front |rear |back |left |right )?[a-z_]+(?: (?:bumper|side|doors?))?)/gi;
        var neg = [], negRaw = [], src = [];
        var pos = s.replace(SRC_RE, function (m, w) { src.push(w); return ' '; }).replace(NEG_RE, function (m, w) { neg.push(w); return ' '; });
        raw.replace(NEG_RE, function (m, w) { negRaw.push(w); return m; });
        var rawFree = raw.replace(SRC_RE, ' ').replace(NEG_RE, ' ');
        var all = targetsIn(raw, s, env, null), free = targetsIn(rawFree, pos, env, null);
        var negT = neg.length ? targetsIn(negRaw.join(' , '), neg.join(' , '), env, null) : null;
        var dir = null, sd = s.replace(/\b(?:go|step|come|get|bring|put|take|turn|set|send) (?:it |them |that |\w+ )?back\b|\bback to\b|\bback one\b|\blean back\b/g, ' ');
        if (/\b(?:the |to the |on the )?(right)\b(?! (?:side|door|panel|now|away|there|one|color|colour|red|blue|green|white|black))/.test(sd) && !/\bright side\b/.test(sd)) dir = 'right';
        else if (/\b(?:the |to the |on the )?(left)\b(?! (?:side|door|panel|over|alone|it|as))/.test(sd) && !/\bleft side\b/.test(sd) && !/\bleave\b/.test(sd)) dir = 'left';
        else if (/\b(?:the |on the )?(rear|back)\b(?! (?:bumper|half|third|end|wing))/.test(sd) && !free.parts.length) dir = 'rear';
        else if (/\b(?:the |on the )?front\b(?! (?:bumper|half|third|end|splitter))/.test(sd) && !free.parts.length) dir = 'front';
        var cols = coloursOf(raw), fin = finishOf(s), nm = s.match(RX.nth), bt = s.match(RX.better);
        return {
            said: raw.slice(0, 600), s: s, free: free, all: all, neg: neg, source: src, negT: negT, dir: dir, colours: cols, finish: fin,
            closer: RX.closer.test(s), save: RX.save.test(s), question: RX.question.test(s), offerAsk: RX.offerAsk.test(s),
            undo: RX.undo.test(s), redo: RX.redo.test(s), again: RX.again.test(s), better: bt ? (bt[1] || bt[2] || 'first') : null,
            nth: nm ? NTH[(nm[1] || nm[2])] : null, otherOne: RX.otherOne.test(s), otherSide: RX.otherSide.test(s), both: RX.both.test(s), same: RX.same.test(s), instead: RX.instead.test(s),
            pron: RX.pron.test(s), only: RX.only.test(s), correction: RX.correction.test(s), keepClause: RX.keepClause.test(s), rel: relOf(s), swap: /\bswap\b|\bother way (?:a+round|around|arond)\b|\bswitch them\b/.test(s)
        };
    }

    // ------------------------------------------------------------------ Targets: normalise any producer's shape -> frame Target; compare by atomic keys
    function normTarget(tg) {
        if (!tg) return null; if (typeof tg === 'string') return PARTS.indexOf(tg) !== -1 ? { kind: 'part', parts: [tg] } : { kind: 'object', object: tg };
        var k = tg.kind;
        if (k === 'part') return { kind: 'part', parts: uniq((tg.parts || []).concat(tg.part ? [tg.part] : [])), portion: tg.portion || undefined };
        if (k === 'numbers' || k === 'sponsors') return { kind: 'element', element: k };                 // js/spb-pro-edit.js ctxOf targets
        if (k === 'layerword' || k === 'accents') return { kind: 'object', object: tg.word || k };
        if (k === 'main') return { kind: 'colour', colour: { word: 'main colour' } };
        if (k === 'colour') return { kind: 'colour', colour: tg.colour || { word: tg.word, hex: tg.hex || null }, layers: tg.layers || undefined };
        if (k === 'body' || k === 'whole' || k === 'car') return { kind: 'body' };
        var c = clone(tg); return c;
    }
    function keysOf(tgs) {
        var out = [];
        (tgs || []).forEach(function (tg) {
            tg = normTarget(tg); if (!tg) return;
            if (tg.kind === 'part') (tg.parts || []).forEach(function (p) { out.push('part:' + p); });
            else if (tg.kind === 'body') out.push('body');
            else if (tg.kind === 'layer') (tg.layers || []).forEach(function (l) { out.push('layer:' + low(l)); });
            else if (tg.kind === 'element') out.push('element:' + tg.element);
            else if (tg.kind === 'object') out.push('object:' + low(tg.object));
            else if (tg.kind === 'graphic') { if (tg.parts && tg.parts.length) tg.parts.forEach(function (p) { out.push('graphic:' + tg.graphic + '@' + p); }); else out.push('graphic:' + tg.graphic); }
            else if (tg.kind === 'colour') out.push('colour:' + low((tg.colour && (tg.colour.hex || tg.colour.word)) || '') + (tg.layers && tg.layers.length ? '@' + low(tg.layers.join('+')) : ''));
            else if (tg.kind === 'zone') out.push('zone:' + tg.zone);
            else if (tg.kind === 'history') out.push('history');
            else out.push(tg.kind);
        });
        return uniq(out);
    }
    function partsOfKeys(keys) { return keys.filter(function (k) { return k.indexOf('part:') === 0; }).map(function (k) { return k.slice(5); }); }
    function touches(chKeys, keys) {          // does a change on chKeys cover anything named by keys? (a body change covers every part)
        if (!keys.length) return false;
        return keys.some(function (k) {
            if (chKeys.indexOf(k) !== -1) return true; if (k.indexOf('part:') === 0 && chKeys.indexOf('body') !== -1) return true;
            var p = k.split('@')[1]; if (p && chKeys.indexOf('part:' + p) !== -1) return true;
            if (k.indexOf('layer:') === 0) { var ln = k.slice(6); return chKeys.some(function (c) { return c.split('@')[1] === ln || (c.indexOf('@') !== -1 && c.split('@')[1].split('+').indexOf(ln) !== -1); }); }          // the Logos layer covers "the white in Logos"
            return false;
        });
    }
    var OPP = { 'left side': 'right side', 'right side': 'left side', 'front bumper': 'rear bumper', 'rear bumper': 'front bumper', hood: 'trunk', trunk: 'hood' };
    function mirrorTargets(tgs, dir) {          // "same on the right" / "the other side" / "rear too": the last target, moved
        var out = [];
        (tgs || []).forEach(function (tg) {
            tg = normTarget(tg); if (!tg) return; var ps = tg.parts || [];
            if (!ps.length) return;
            var np = ps.map(function (p) {
                if (dir === 'right' || dir === 'left') return (p === 'left side' || p === 'right side') ? dir + ' side' : (dir + ' side');
                if (dir === 'rear') return p === 'front bumper' ? 'rear bumper' : (p === 'hood' ? 'trunk' : 'rear bumper');
                if (dir === 'front') return p === 'rear bumper' ? 'front bumper' : (p === 'trunk' ? 'hood' : 'front bumper');
                return OPP[p] || p;
            });
            var c = clone(tg); c.parts = uniq(np); out.push(c);
        });
        return out;
    }
    function lookOfRead(rd) {
        var L = {}; if (rd.colours.length) L.colour = rd.colours.length === 1 ? rd.colours[0] : { word: rd.colours.map(function (c) { return c.word; }).join(' / '), families: uniq([].concat.apply([], rd.colours.map(function (c) { return c.families; }))), hex: rd.colours[0].hex };
        if (rd.finish) L.finish_class = rd.finish; if (rd.rel) L.relative = rd.rel; return L;
    }
    function mergeLook(base, over) {
        var L = clone(base || {}) || {}; over = over || {};
        if (over.colour) L.colour = clone(over.colour); if (over.finish_class) L.finish_class = over.finish_class; if (over.finish) L.finish = clone(over.finish);
        if (over.gradient) L.gradient = clone(over.gradient); if (over.stroke) L.stroke = clone(over.stroke); if (over.pattern) L.pattern = clone(over.pattern);
        if (over.relative) L.relative = clone(over.relative); else delete L.relative;
        return L;
    }
    function lookSame(a, b) {
        if (!a || !b) return false; var ca = a.colour && (a.colour.hex || a.colour.word), cb = b.colour && (b.colour.hex || b.colour.word);
        var fa = a.finish_class || (a.finish && a.finish.family) || null, fb = b.finish_class || (b.finish && b.finish.family) || null;
        if (!ca && !cb && !fa && !fb) return false;
        return low(ca || '') === low(cb || '') && (fa || null) === (fb || null);
    }
    function lookMentions(look, word) {
        if (!look || !word) return false; var w = low(word);
        var fam = (look.colour && look.colour.families) || [], cw = low((look.colour && look.colour.word) || ''), fc = low(look.finish_class || (look.finish && look.finish.family) || '');
        return (!!cw && (cw === w || cw.indexOf(w) !== -1)) || fam.indexOf(w) !== -1 || (!!fc && (fc === w || w.indexOf(fc) !== -1 || fc.indexOf(w) !== -1)) || (look.label && low(look.label).indexOf(w) !== -1);
    }

    // ------------------------------------------------------------------ the store
    var S = null;
    function reset() { S = { seq: 0, turns: [], changes: [], offer: null, pending: null, topic: null, colour_region: null, nopaint: null, lastRes: null, byEntry: {}, t: 0 }; return true; }
    reset();
    function turnRec(id) { for (var i = S.turns.length - 1; i >= 0; i--) if (S.turns[i].turn === id) return S.turns[i]; return null; }
    function curTurn() { return S.turns[S.turns.length - 1] || null; }
    function turn(text, meta) {          // a buyer sentence starts; every commit / offer / note until the next turn() belongs to it
        meta = meta || {};
        var said0 = String(text || '').slice(0, 300), cur0 = curTurn();
        if (!meta.turn && cur0 && cur0.said === said0 && CLOCK() - cur0.at < 3000) return cur0.turn;          // the offline reader and the copilot both start the same sentence: one turn
        var id = meta.turn || ('t-' + (++S.seq)); var tr = { turn: id, i: S.turns.length, said: String(text || '').slice(0, 300), at: CLOCK(), act: null, targets: [], look: null, producer: meta.producer || null, res: null, offer: false, change: null };
        S.turns.push(tr); if (S.turns.length > KEEP_TURNS) S.turns.splice(0, S.turns.length - KEEP_TURNS);
        S.t = tr.at; S.lastRes = null; return id;
    }
    function ensureTurn(rec) { var tr = rec && rec.turn ? turnRec(rec.turn) : curTurn(); if (!tr) { turn(rec && rec.said || '', { turn: rec && rec.turn }); tr = curTurn(); } return tr; }

    // commit(rec): the EXECUTOR calls this after a change really landed (offline Run, model applyQueue, element designer, MCP)
    //   rec = { turn, source:'offline'|'model'|'element'|'mcp'|'chip', said, verbs:[], targets:[Target|editCtx target], look:{colour, finish, finish_class, gradient, stroke, pattern},
    //           scope_mask_id, zone_ids:[], zone_names:[], layers:[], colours:['#hex'], finish:'base::x', stroke_px, gradient_stops:[], undo_id, editCtx (legacy), entry_id }
    function commit(rec) {
        rec = rec || {}; var tr = ensureTurn(rec);
        var tgs = (rec.targets || []).map(normTarget).filter(Boolean);
        var look = clone(rec.look || {}) || {};
        Object.keys(look).forEach(function (k) { if (look[k] == null) delete look[k]; });
        // an EDIT of a zone an earlier change made (in-app smoke 2026-10-06: "make it chrome instead" edited the roof zone and the record had no part):
        // the target and the untouched look slots come from that change
        var prevZ = null; (rec.edited_zone_ids || []).some(function (zid) { for (var pi = S.changes.length - 1; pi >= 0; pi--) if (S.changes[pi].zone_ids.indexOf(String(zid)) !== -1) { prevZ = S.changes[pi]; return true; } return false; });
        if (prevZ) { if (!tgs.length) tgs = clone(prevZ.targets); look = mergeLook(prevZ.look, look); if (look.finish && !(rec.look || {}).finish_class) delete look.finish_class; if (look.finish && look.finish.family && !look.finish_class) { var ffc = FINISH_WORDS.filter(function (fw) { return fw[1].test(String(look.finish.family).replace(/_/g, ' ')); })[0]; if (ffc) look.finish_class = ffc[0]; } }
        if (!look.colour && rec.colours && rec.colours.length) look.colour = { word: rec.colours[0], hex: rec.colours[0], families: uniq([hexFamily(rec.colours[0])]) };
        if (!look.finish && rec.finish) look.finish = { key: rec.finish, family: (String(rec.finish).split('::')[1] || '').replace(/^f_/, '') };
        if (rec.gradient_stops && rec.gradient_stops.length && !look.gradient) look.gradient = { stops: rec.gradient_stops.slice() };
        if (rec.stroke_px != null && !look.stroke) look.stroke = { px: rec.stroke_px };
        var res = S.lastRes && S.lastRes.turn === tr.turn ? S.lastRes : null, origin = null;
        // origin = the change this one COPIES (propagate / pick of an earlier version); edit_of = the change this one MODIFIES (relative / restyle / retarget / refer)
        var editOf = null;
        if (res && (res.op === 'propagate' || res.op === 'pick') && res.ref) { var src = changeOfTurn(res.ref); if (src) origin = src.origin || src.turn; }
        if (res && /^(?:relative|restyle|retarget|refer|again|keep|exclude)$/.test(res.op || '') && res.ref) { var src2 = changeOfTurn(res.ref); if (src2) editOf = src2.edit_of || src2.turn; }
        var ch = {
            id: 'c-' + (S.changes.length ? (+S.changes[S.changes.length - 1].id.slice(2) + 1) : 1), turn: tr.turn, i: tr.i, at: CLOCK(), source: rec.source || 'app', said: rec.said || tr.said,
            verbs: uniq(rec.verbs || []), targets: tgs, keys: keysOf(tgs), look: look, scope_mask_id: rec.scope_mask_id || null,
            zone_ids: uniq((rec.zone_ids || []).map(String)), zone_names: uniq(rec.zone_names || []), layers: uniq(rec.layers || []), colours: uniq(rec.colours || []),
            finish: rec.finish || null, stroke_px: rec.stroke_px != null ? rec.stroke_px : null, gradient_stops: rec.gradient_stops || null,
            undo_id: rec.undo_id != null ? String(rec.undo_id) : null, entry_id: rec.entry_id != null ? rec.entry_id : null, undone: false, live_turn: tr.turn,
            origin: origin, edit_of: editOf, op: res ? res.op : null, editCtx: rec.editCtx ? clone(rec.editCtx) : null
        };
        S.changes.push(ch); if (S.changes.length > KEEP_CHANGES) S.changes.splice(0, S.changes.length - KEEP_CHANGES);
        tr.act = 'change'; tr.change = ch.id; tr.targets = tgs; tr.look = look;
        if (look.colour && tgs.length) S.colour_region = { word: look.colour.word || look.colour.hex || '', hex: look.colour.hex || null, layers: ch.layers.slice(), targets: clone(tgs), turn: tr.turn };
        S.pending = null;
        if (rec.entry_id != null) S.byEntry[String(rec.entry_id)] = ch.id;
        return ch;
    }
    function changeById(id) { for (var i = S.changes.length - 1; i >= 0; i--) if (S.changes[i].id === id) return S.changes[i]; return null; }
    function changeOfTurn(turnId) { for (var i = S.changes.length - 1; i >= 0; i--) if (S.changes[i].turn === turnId) return S.changes[i]; return null; }
    function changeByUndo(uid) { uid = String(uid); for (var i = S.changes.length - 1; i >= 0; i--) if (S.changes[i].undo_id === uid || String(S.changes[i].entry_id) === uid) return S.changes[i]; return null; }
    // the app's Undo / Redo (button, chip, "undo" sentence, spb_undo) tells the store
    function undone(uid, meta) { var ch = changeByUndo(uid); if (!ch) return null; ch.undone = true; var tr = curTurn(); if (tr && (!meta || meta.asTurn !== false) && tr.act == null) { tr.act = 'undo'; tr.targets = ch.targets; tr.look = null; tr.change = ch.id; } return ch; }
    function redone(uid) { var ch = changeByUndo(uid); if (!ch) return null; ch.undone = false; var tr = curTurn(); if (tr && tr.act == null) { tr.act = 'redo'; tr.targets = ch.targets; tr.look = ch.look; tr.change = ch.id; ch.live_turn = tr.turn; } return ch; }

    // offer(rec): the REPORTER calls this whenever it shows a list, chips or options ("the second one" resolves against it)
    //   rec = { kind:'finishes'|'colours'|'chips'|'options'|'layers'|'changes', items:[{label, key, look, targets, change}], for:[Target], turn, legacy }
    function offer(rec) {
        rec = rec || {}; var tr = ensureTurn(rec);
        if ((rec.kind === 'chips' || rec.kind === 'options') && !rec.legacy && S.offer && S.offer.legacy && S.offer.kind === 'finishes' && tr && S.offer.turn === tr.turn) return S.offer;          // V3 S6b 2026-10-07 G12
        var items = (rec.items || []).map(function (it, i) { if (typeof it === 'string') it = { label: it }; var o = clone(it) || {}; o.label = String(o.label || o.name || o.key || ('option ' + (i + 1))); if (!o.look) { var rd = read(o.label); o.look = lookOfRead(rd); var tt = explicitTargets(rd, null); if (tt.length && !o.targets) o.targets = tt; } return o; });
        S.offer = { kind: rec.kind || 'options', items: items, for: (rec.for || []).map(normTarget).filter(Boolean), turn: tr.turn, at: CLOCK(), legacy: rec.legacy ? clone(rec.legacy) : null, picked: [] };
        if (!S.offer.for.length && RX.pron.test(fixWords(tr.said))) { var ps = lastSubject(tr.i - 1); if (ps) S.offer.for = clone(subjTargets(ps)); }          // "show me forged next to IT": the offer is about the last thing
        tr.offer = true; if (tr.act == null) tr.act = 'offer'; if (S.offer.for.length && !tr.targets.length) tr.targets = S.offer.for;
        return S.offer;
    }
    // note(rec): an answer, a question back, or nothing; keeps last_target (a question about a part), pending (the slot we asked for) and the topic
    //   rec = { act:'answer'|'ask'|'nothing', topic, targets, look, missing:[...], asked, legacyPending, turn }
    function note(rec) {
        rec = rec || {}; var tr = ensureTurn(rec), rd = read(tr.said);
        if (rec.act === 'nothing') { if (tr.act == null) tr.act = 'nothing'; return tr; }
        if (tr.act == null || tr.act === 'offer') tr.act = tr.act === 'offer' ? 'offer' : (rec.act || 'answer');
        var tgs = (rec.targets || explicitTargets(rd, null)).map(normTarget).filter(Boolean), look = rec.look || lookOfRead(rd);
        if (tgs.length && !tr.targets.length) tr.targets = tgs;
        if (!tr.look && look && (look.colour || look.finish_class)) tr.look = look;
        if (rec.topic) S.topic = { id: rec.topic, turn: tr.turn };
        var legPrev = S.pending && S.pending.turn === tr.turn && S.pending.legacy ? S.pending.legacy : null;          // HELPER V3 S3 2026-10-06: the app's own entry note comes AFTER the offline router's ask; it must not wipe the router's open question (in-app b3-159 "paint the bumper" -> "front" lost "which bumper"; b4-139 lost "orange")
        if (rec.act === 'ask' || rec.missing) S.pending = { turn: tr.turn, missing: rec.missing || [], asked: rec.asked || null, targets: tgs, look: look, at: CLOCK(), legacy: rec.legacyPending ? clone(rec.legacyPending) : legPrev };
        else if (rec.act === 'answer' && !legPrev && (tgs.length || (look && (look.colour || look.finish_class)))) S.pending = { turn: tr.turn, missing: tgs.length ? ['look'] : ['target'], asked: null, targets: tgs, look: look, at: CLOCK(), soft: true };
        if (rec.nopaint) S.nopaint = rec.nopaint.slice ? rec.nopaint.slice() : rec.nopaint;
        return tr;
    }

    // ------------------------------------------------------------------ resolution (deterministic)
    function explicitTargets(rd, ctx) {
        var f = rd.free, out = [], parts = f.parts.slice();
        f.amb.forEach(function (a) {
            var lp = (ctx && ctx.lastParts) || [];
            if (a === 'bumper') { if (lp.some(function (p) { return /trunk|rear|spoiler|bed/.test(p); })) parts.push('rear bumper'); else if (lp.some(function (p) { return /hood|front/.test(p); })) parts.push('front bumper'); else { parts.push('front bumper'); parts.push('rear bumper'); } }
            if (a === 'side') { if (rd.dir === 'right' || rd.dir === 'left') parts.push(rd.dir + ' side'); else { parts.push('left side'); parts.push('right side'); } }
        });
        parts = uniq(parts);
        if (f.layers.length) out.push({ kind: 'layer', layers: f.layers.slice() });
        if (f.graphics.length) f.graphics.forEach(function (g) { out.push(parts.length ? { kind: 'graphic', graphic: g, parts: parts.slice() } : { kind: 'graphic', graphic: g }); });
        else if (parts.length) out.push({ kind: 'part', parts: parts });
        f.elements.forEach(function (e) { if (e === 'logos' && f.layers.some(function (l) { return /logo/i.test(l); })) return; out.push({ kind: 'element', element: e }); });
        f.objects.forEach(function (o) { out.push({ kind: 'object', object: o }); });
        if (!out.length && f.whole) out.push({ kind: 'body' });
        return out;
    }
    function liveChanges() { return S.changes.filter(function (c) { return !c.undone; }); }
    function changedBefore(i) { return S.changes.some(function (c) { var tr = turnRec(c.turn); return tr && tr.i < i; }); }
    // a subject = a turn a follow-up can point at: a change / undo / redo, an offer, or a sentence that named a target.
    // A question or a complaint that only named a look ("what's the difference between matte and satin", "that's not the same red") is a subject only before any change.
    function isSubject(tr) { if (!tr) return false; if (tr.act === 'change' || tr.act === 'undo' || tr.act === 'redo' || tr.offer || (tr.targets && tr.targets.length > 0)) return true; return (tr.act === 'ask' || !!(tr.look && (tr.look.colour || tr.look.finish_class))) && !changedBefore(tr.i); }
    function lastSubject(beforeIdx) { var end = beforeIdx == null ? S.turns.length - 1 : beforeIdx; for (var i = end; i >= 0; i--) if (isSubject(S.turns[i])) return S.turns[i]; return null; }
    function lastSpoken(beforeIdx) { var end = beforeIdx == null ? S.turns.length - 1 : beforeIdx; for (var i = end; i >= 0; i--) { var tr = S.turns[i]; if (tr.act !== 'nothing') return tr; } return null; }
    function subjTargets(tr) { if (!tr) return []; if (tr.targets && tr.targets.length) return tr.targets; var ch = tr.change && changeById(tr.change); return ch ? ch.targets : []; }
    function subjLook(tr) { if (!tr) return null; var ch = tr.change && changeById(tr.change); return (ch && ch.look) || tr.look || null; }
    function originTurn(tr) { var ch = tr && tr.change && changeById(tr.change); return ch && ch.origin ? ch.origin : (tr ? tr.turn : null); }

    // resolve(text, frame?, env?): what the sentence refers to. Called by every producer BEFORE it builds ops (frame given = its explicit reading wins).
    //   -> { v, said, kinds:[...], op, ref (turn id), ref_index, change (id), targets:[Target], look, offer_item, relative, keep:[Target], from:[Target], undo_id, why }
    function resolve(text, frame, env, opts) {          // opts.dry = no side effects (view() uses it)
        var DRY = !!(opts && opts.dry);
        var rd = read(text, env), cur = curTurn();
        // the sentence being resolved is normally the newest turn (turn() was called); otherwise resolve against everything
        var before = (cur && cur.said === String(text || '').slice(0, 300) && cur.act == null) ? cur.i - 1 : S.turns.length - 1;
        var spoken = lastSpoken(before), topicSubj = lastSubject(before), subj = topicSubj || spoken, live = liveChanges();
        if (!S.changes.length && spoken) subj = spoken;          // a pure question chain (nothing changed yet): every follow-up builds on the sentence before it
        var lastCh = live.length ? live[live.length - 1] : null;
        var ctx = { lastParts: partsOfKeys(keysOf(subjTargets(subj))), lastLayers: [] };
        subjTargets(subj).forEach(function (t) { if (t.layers && t.layers.length) ctx.lastLayers = ctx.lastLayers.concat(t.layers); });
        if (/\bthe layer\b/.test(rd.s) && ctx.lastLayers.length && !rd.free.layers.length) rd.free.layers = ctx.lastLayers.slice();
        var exp = (frame && frame.ops && frame.ops.length) ? frame.ops.map(function (o) { return normTarget(o.target); }).filter(Boolean) : explicitTargets(rd, ctx);
        var expKeys = keysOf(exp), negKeys = rd.negT ? keysOf(explicitTargets({ free: rd.negT, dir: null }, ctx)) : [];
        var rLook = lookOfRead(rd);
        var R = { v: V, said: rd.said, kinds: [], op: null, ref: null, ref_index: null, change: null, targets: [], look: rLook, offer_item: null, relative: rd.rel, keep: [], from: null, undo_id: null, why: '' };
        function refTo(tr, why) { if (!tr) return; R.ref = tr.turn; R.ref_index = tr.i; var ch = tr.change && changeById(tr.change); if (ch) { R.change = ch.id; R.undo_id = ch.undo_id; } R.why = why || R.why; }
        function done() { R.explicit = expKeys.length > 0; R.inherited = !R.explicit && R.targets.length > 0; if (DRY) return R; S.lastRes = { turn: cur ? cur.turn : null, op: R.op, ref: R.ref }; if (cur && cur.act == null) cur.res = { op: R.op, ref: R.ref, kinds: R.kinds.slice() }; return R; }
        if (!S.turns.length || (!spoken && !lastCh)) { R.kinds.push('none'); R.targets = exp; R.why = 'first turn'; return done(); }
        // 0. closers and new topics carry no referent
        if (rd.closer || (rd.save && !rd.undo && !exp.length && S.changes.length) || (S.changes.length && !exp.length && /^(?:leave it|idk|i dunno|verify|report\b|is it done|(?:fine|ok|good)[.,]? (?:they'?re|it'?s|that'?s|looks?)\b)/.test(rd.s))) { R.kinds.push(rd.closer ? 'closer' : 'new_topic'); R.why = 'nothing to resolve'; return done(); }
        // 1. redo: the change undone most recently (that names the part, when one is named)
        if (rd.redo && !/\bto \d+\s*%/.test(rd.s)) {
            var und = S.changes.filter(function (c) { return c.undone && (!expKeys.length || touches(c.keys, expKeys)); });
            var rc = und.length ? und[und.length - 1] : null;
            R.kinds.push('redo'); R.op = 'redo';
            if (rc) { refTo(turnRec(rc.live_turn) || turnRec(rc.turn), 'redo the undone change'); R.targets = expKeys.length ? exp : clone(rc.targets); R.look = mergeLook(rc.look, rLook); return done(); }
            R.targets = exp.length ? exp : [{ kind: 'history', which: 'last undone change' }]; refTo(spoken, 'nothing undone in this chat: the app history'); return done();
        }
        // 2. undo / take off / as it was: the newest live change on the named thing (or the newest at all)
        if (rd.undo) {
            var nk = expKeys.length ? expKeys : negKeys, cand = live.filter(function (c) { return !nk.length || touches(c.keys, nk); });
            var uc = cand.length ? cand[cand.length - 1] : null;
            if (/\b(?:also|but) (?:leave|keep)\b/.test(rd.s) && lastCh) { R.kinds.push('keep'); R.op = 'keep'; refTo(turnRec(lastCh.live_turn) || turnRec(lastCh.turn), 'keep-clause on the last change'); R.targets = clone(lastCh.targets); R.keep = exp; R.look = clone(lastCh.look); return done(); }
            R.kinds.push('undo'); R.op = 'undo';
            if (uc) { refTo(turnRec(uc.live_turn) || turnRec(uc.turn), 'undo'); R.targets = nk.length ? (expKeys.length ? exp : explicitTargets({ free: rd.negT, dir: null }, ctx)) : clone(uc.targets); var prevL = null; for (var pj = live.indexOf(uc) - 1; pj >= 0; pj--) if (touches(live[pj].keys, uc.keys) || touches(uc.keys, live[pj].keys)) { prevL = live[pj].look; break; }          // what the undo returns to
                R.look = rLook.colour || rLook.finish_class ? mergeLook(prevL || {}, rLook) : (prevL ? clone(prevL) : null); R.restores = prevL ? clone(prevL) : null; if (rLook.colour || rLook.finish_class) { R.kinds.push('instead'); } return done(); }
            R.targets = exp.length ? exp : [{ kind: 'history', which: 'last change' }]; refTo(subj || spoken, 'nothing to undo in this chat: the app history'); return done();
        }
        // 3. a pick from what we offered ("the second one", "the other one", or a word that names an item, right after the list)
        var off = S.offer && (CLOCK() - S.offer.at < OFFER_TTL_MS) ? S.offer : null;
        if (off && off.items.length) {
            var item = null, idx = -1, offTr = turnRec(off.turn), fresh = offTr && spoken && offTr.i >= spoken.i - (spoken.offer ? 0 : 0) && offTr === spoken;
            if (rd.nth != null && (fresh || offTr && offTr.i >= (subj ? subj.i : 0))) { idx = rd.nth < 0 ? off.items.length - 1 : rd.nth; }
            else if (rd.otherOne && off.picked.length) { for (var oi = 0; oi < off.items.length; oi++) if (off.picked.indexOf(oi) === -1) { idx = oi; break; } }
            else if (fresh && (rLook.colour || rLook.finish_class)) {
                var w = rd.finish || (rd.colours[0] && rd.colours[0].word);
                for (var ii = 0; ii < off.items.length; ii++) if (lookMentions(off.items[ii].look, w) || low(off.items[ii].label).indexOf(low(w || '#')) !== -1) { idx = ii; break; }
            }
            if (idx >= 0 && idx < off.items.length) {
                item = off.items[idx]; if (!DRY && off.picked.indexOf(idx) === -1) off.picked.push(idx);
                R.kinds.push(rd.otherOne ? 'other_one' : (rd.nth != null ? 'nth_offer' : 'offer_word')); R.op = 'pick'; R.offer_item = { index: idx, label: item.label, key: item.key || null };
                var ich = item.change ? changeById(item.change) : null;
                if (ich) refTo(turnRec(ich.turn), 'picked a version'); else refTo(offTr, 'picked an offered item');
                R.targets = exp.length ? exp : (item.targets && item.targets.length ? clone(item.targets) : (off.for.length ? clone(off.for) : (ich ? clone(ich.targets) : subjTargets(lastSubject(offTr ? offTr.i - 1 : before)))));
                R.look = mergeLook(item.look || (ich && ich.look) || {}, rLook); return done();
            }
        }
        // 4. "the first one was better" / "go back to the first" / "<colour> was better": a version of the same thing, without a list
        var backTo = (rd.correction || rd.instead) && !expKeys.length && (rd.colours.length || rd.finish) && !rd.rel ? (rd.finish || rd.colours[0].word) : null;          // "no green" after green -> blue: back to the green version
        if ((rd.nth != null || rd.better || backTo) && subj) {
            var sk = keysOf(subjTargets(subj)), run = S.changes.filter(function (c) { return c.keys.length && sk.length && (touches(c.keys, sk) || touches(sk, c.keys)); });
            var pick = null;
            if (backTo && rd.nth == null && !rd.better) { for (var bj = run.length - 1; bj >= 0; bj--) if (run[bj].turn !== subj.turn && run[bj].id !== subj.change && lookMentions(run[bj].look, backTo)) { pick = run[bj]; break; } }
            else if (rd.better && rd.better !== 'first' && !/^(?:the )?first|original|old|previous|earlier/.test(rd.better)) {
                var bw = rd.better.replace(/^the /, '').split(' ').pop();
                for (var bi = run.length - 1; bi >= 0; bi--) if (run[bi].turn !== subj.turn && lookMentions(run[bi].look, bw)) { pick = run[bi]; break; }
                if (!pick && /^both$/.test(bw)) pick = null;
            } else if (run.length) pick = rd.nth != null && rd.nth > 0 && rd.nth < run.length ? run[rd.nth] : (rd.nth === -1 ? run[run.length - 1] : run[0]);
            if (pick) { R.kinds.push('nth_change'); R.op = 'pick'; refTo(turnRec(pick.turn), 'an earlier version'); R.targets = exp.length ? exp : clone(pick.targets); R.look = mergeLook(pick.look, rLook); return done(); }
        }
        var sT = subjTargets(subj); if (!sT.length && topicSubj) sT = subjTargets(topicSubj);
        var sKeys = keysOf(sT), sLook = subjLook(subj);
        // 5. "both" with nothing named: the last change's targets when it had two, else the last two things together
        if (rd.both && !expKeys.length) {
            R.kinds.push('both'); R.op = rLook.colour || rLook.finish_class || rd.rel ? 'restyle' : 'propagate';
            if (sKeys.length >= 2) { R.targets = clone(sT); refTo(subj, 'both = the last change'); }
            else { var prev = subj ? lastSubject(subj.i - 1) : null; R.targets = clone(sT).concat(clone(subjTargets(prev))); refTo(subj, 'both = the last two things'); }
            R.look = mergeLook(sLook, rLook); return done();
        }
        // 6. "same on the right" / "the other side" / "rear too": the last target moved
        if (!expKeys.length && rd.swap && /\bother way\b/.test(rd.s) && subj) { var pw = lastSubject(subj.i - 1); R.kinds.push('swap'); R.op = 'swap'; R.targets = sKeys.length >= 2 ? clone(sT) : clone(sT).concat(clone(subjTargets(pw))); refTo(subj, 'the other way around = swap the last two'); R.look = null; return done(); }
        if (!expKeys.length && (rd.otherSide || (rd.dir && (rd.same || !rd.rel))) && sT.length) {
            R.kinds.push(rd.otherSide ? 'other_side' : 'side_word'); R.op = rd.swap ? 'swap' : 'propagate';
            var mt = mirrorTargets(sT, rd.otherSide ? null : rd.dir);
            if (mt.length) { R.targets = mt; var otr = rd.same || !rd.swap ? turnRec(originTurn(subj)) || subj : subj; refTo(otr, 'opposite side of the last target'); R.look = mergeLook(subjLook(otr) || sLook, rLook); return done(); }
        }
        // 7. explicit targets
        if (expKeys.length) {
            var overlaps = sKeys.length && (touches(sKeys, expKeys) || touches(expKeys, sKeys));
            var subset = sKeys.length && expKeys.every(function (k) { return sKeys.indexOf(k) !== -1 || (k.indexOf('part:') === 0 && sKeys.indexOf('body') !== -1); });
            // a graphic / element kept, moved to the named part ("no the roof not the hood" after a hood stripe)
            var tgOut = exp;
            // "outline instead" after a Logos-layer change: the graphic is the look, the layer stays the target
            if (rd.free.graphics.length && !rd.free.parts.length && !rd.free.layers.length && !rd.free.elements.length && !rd.free.objects.length && sT.length && sT.every(function (t) { return t.kind === 'layer' || t.kind === 'element'; })) { tgOut = clone(sT); expKeys = keysOf(tgOut); }
            if (rd.free.parts.length && !rd.free.graphics.length && !rd.free.elements.length && sT.length && sT.every(function (t) { return t.kind === 'graphic' && t.parts && t.parts.length; })) tgOut = [{ kind: 'graphic', graphic: sT[0].graphic, parts: rd.free.parts.slice() }];
            if (rd.correction && !subset && subj && (rd.neg.length || /\bi (?:said|meant|mean|wanted)\b|\bthat'?s the\b|^no\b|\bwrong\b/.test(rd.s))) {
                R.kinds.push('retarget'); R.op = 'retarget'; R.targets = tgOut; R.from = clone(sT); refTo(subj.act === 'undo' && subj.change && changeById(subj.change) ? turnRec(changeById(subj.change).turn) || subj : subj, 'correction: the same change, another place'); R.look = mergeLook(sLook, rLook); return done();
            }
            var sameLook = sLook && lookSame(sLook, rLook);
            if (rd.same || rd.both || sameLook || (!rLook.colour && !rLook.finish_class && !rd.rel && !(rd.question && !rd.pron))) {
                if (rd.question && !rd.pron && !rd.same && !(subj && (subj.act === 'ask' || subj.act === 'answer'))) { R.kinds.push('question'); R.targets = tgOut; R.why = 'a new question'; return done(); }
                var isProp = !overlaps || rd.same;
                R.kinds.push(isProp ? 'propagate' : 'narrow'); R.op = isProp ? 'propagate' : 'restyle'; R.targets = tgOut;
                var rt = isProp && !(rLook.colour || rLook.finish_class || rd.rel) ? (turnRec(originTurn(subj)) || subj) : subj;
                if (subj && (subj.act === 'answer' || subj.act === 'ask' || subj.act === 'offer') && !(subj.change)) rt = subj;
                refTo(rt, isProp ? 'the same look on another part' : 'part of the last change');
                var pl = S.pending && S.pending.turn === (subj && subj.turn) ? S.pending.look : null;
                R.look = mergeLook(mergeLook(subjLook(rt) || pl || {}, pl && !subjLook(rt) ? pl : {}), rLook); return done();
            }
            if (overlaps || rd.only || rd.instead || rd.rel || rd.pron || rd.swap) { R.kinds.push(rd.instead ? 'instead' : (rd.rel ? 'relative' : 'narrow')); R.op = rd.rel ? 'relative' : 'restyle'; R.targets = tgOut; refTo(subj, 'the same thing, restyled'); R.look = mergeLook(sLook, rLook); return done(); }
            if (subj && !subj.change && (subj.act === 'ask' || subj.act === 'answer' || subj.act === 'offer')) { R.kinds.push('pending_fill'); R.targets = tgOut; refTo(subj, 'answers the open question'); R.look = mergeLook((S.pending && S.pending.look) || subj.look || {}, rLook); return done(); }
            R.kinds.push('explicit'); R.targets = tgOut; R.why = 'self-contained'; return done();
        }
        // 8. only "not X" said: X is excluded from (or put back in) the last change
        if (negKeys.length && subj) { R.kinds.push('exclude'); R.op = 'exclude'; R.targets = explicitTargets({ free: rd.negT, dir: null }, ctx); R.keep = clone(R.targets); refTo(subj, 'not X: an exclusion on the last change'); return done(); }
        // 9. nothing named: it / that / more / less / instead / again / swap / a fragment -> the last subject
        if (rd.question && !rd.pron && !rd.rel && subj && subj.change && !rd.instead && !rd.again && !rd.same) { R.kinds.push('question'); R.why = 'a new question'; return done(); }
        if (rd.again) { var ac = lastCh; R.kinds.push('again'); R.op = 'again'; if (ac && !(rd.rel)) { refTo(turnRec(ac.live_turn) || turnRec(ac.turn), 'the last change again'); R.targets = clone(ac.targets); R.look = mergeLook(ac.look, rLook); return done(); } }
        if (rd.swap && subj) { R.kinds.push('swap'); R.op = 'swap'; var p2 = lastSubject(subj.i - 1); R.targets = sKeys.length >= 2 ? clone(sT) : clone(sT).concat(clone(subjTargets(p2))); refTo(subj, 'swap the last two'); R.look = null; return done(); }
        var tgt = subj || spoken;
        R.kinds.push(rd.instead ? 'instead' : (rd.rel ? 'relative' : (rd.pron ? 'pronoun' : (rd.same ? 'same' : 'fragment'))));
        R.op = rd.rel ? 'relative' : (rd.instead || rLook.colour || rLook.finish_class ? 'restyle' : 'refer');
        refTo(tgt, 'the last thing we talked about');
        R.targets = clone(subjTargets(tgt)); if (!R.targets.length && S.pending && S.pending.targets.length) R.targets = clone(S.pending.targets);
        var pend = S.pending && tgt && S.pending.turn === tgt.turn ? S.pending.look : null;
        R.look = mergeLook(subjLook(tgt) || pend || {}, rLook);
        return done();
    }

    // ------------------------------------------------------------------ views
    function tgLabel(tgs) { return keysOf(tgs).map(function (k) { return k.replace(/^part:|^element:|^object:/, '').replace(/^layer:/, 'layer ').replace(/^graphic:/, ''); }).join(', '); }
    function lookLabel(L) { if (!L) return ''; var a = []; if (L.colour) a.push(L.colour.word || L.colour.hex || ''); if (L.finish_class) a.push(L.finish_class); else if (L.finish && (L.finish.family || L.finish.key)) a.push(L.finish.family || L.finish.key); if (L.gradient) a.push('gradient'); if (L.stroke && L.stroke.px) a.push(L.stroke.px + ' px'); return a.filter(Boolean).join(' '); }
    // STATE.convo for the model prompt (js/spb-pro-ai.js state()): small, recent, no masks
    function view(text) {
        var live = liveChanges(), lc = S.changes.length ? S.changes[S.changes.length - 1] : null, off = S.offer && (CLOCK() - S.offer.at < OFFER_TTL_MS) ? S.offer : null;
        var subj = lastSubject(null);
        var v = {
            last_change: lc ? { turn: lc.turn, said: lc.said.slice(0, 80), targets: tgLabel(lc.targets), look: lookLabel(lc.look) || undefined, zone_ids: lc.zone_ids.slice(0, 6), undo_id: lc.undo_id, undone: lc.undone || undefined, stroke_px: lc.stroke_px != null ? lc.stroke_px : undefined, gradient: lc.gradient_stops || undefined } : null,
            last_target: subj ? tgLabel(subjTargets(subj)) || null : null,
            last_offer: off ? { kind: off.kind, for: tgLabel(off.for) || undefined, items: off.items.slice(0, 6).map(function (x, i) { return (i + 1) + '. ' + x.label; }), turn: off.turn } : null,
            last_colour_region: S.colour_region ? { word: S.colour_region.word, hex: S.colour_region.hex || undefined, on: tgLabel(S.colour_region.targets) } : null,
            pending: S.pending && (CLOCK() - S.pending.at < PENDING_TTL_MS) ? { asked: S.pending.asked || undefined, missing: S.pending.missing, about: tgLabel(S.pending.targets) || undefined, look: lookLabel(S.pending.look) || undefined } : null,
            history: S.turns.slice(-6).map(function (tr) { var ch = tr.change && changeById(tr.change); return { turn: tr.turn, said: tr.said.slice(0, 60), act: tr.act || 'said', targets: tgLabel(tr.targets) || undefined, look: lookLabel(tr.look) || undefined, undone: ch && ch.undone ? true : undefined }; }),
            live_changes: live.length
        };
        if (text) { var r = resolve(text, null, null, { dry: true }); v.this_sentence = { refers_to: r.ref, op: r.op || undefined, targets: tgLabel(r.targets) || undefined, look: lookLabel(r.look) || undefined, offer_item: r.offer_item ? r.offer_item.label : undefined }; }
        return v;
    }

    // ------------------------------------------------------------------ adapters: the executors' own records -> commit / offer / note (the S6/S7 shims call these)
    function queueToRecord(queue, opts) {          // zone-kit queue (js/spb-pro-zone-kit.js SCHEMA) -> commit fields
        opts = opts || {}; var parts = [], layers = [], els = [], colours = [], finish = null, stops = null, stroke = null, verbs = [], tg = [], body = false, pattern = null;
        (queue || []).forEach(function (q) {
            if (!q) return; var sp = q.spec || q.args || {}, rg = sp.region || {};
            if (q.kind === 'layer') { if (q.layer || q.name) layers.push(String(q.layer || q.name)); verbs.push('layer'); return; }
            verbs.push(q.kind || 'add');
            [].concat(rg.part || [], rg.island || []).forEach(function (p) { if (p) parts.push(String(p)); });
            (rg.layers || []).forEach(function (l) { layers.push(String(l)); });
            if (rg.element) els.push(String(rg.element));
            if (rg.everything || rg.remaining) body = true;
            if (sp.color && /^#/.test(sp.color)) colours.push(String(sp.color).toLowerCase());
            if (sp.finish) finish = String(sp.finish);
            if (sp.gradient && sp.gradient.stops) { stops = sp.gradient.stops.map(function (s) { return s.color || s; }); verbs.push('gradient'); }
            if (sp.stroke_px != null) stroke = sp.stroke_px; else if (rg.stroke_px != null) stroke = rg.stroke_px;
            if (sp.pattern && sp.pattern.id && sp.pattern.id !== 'none') pattern = { id: sp.pattern.id, scale: sp.pattern.scale, opacity: sp.pattern.opacity };
        });
        if (parts.length) tg.push({ kind: 'part', parts: uniq(parts) });
        if (layers.length && !parts.length) tg.push({ kind: 'layer', layers: uniq(layers) });
        uniq(els).forEach(function (e) { tg.push({ kind: 'element', element: e }); });
        if (!tg.length && body) tg.push({ kind: 'body' });
        var fam = finish ? (finish.split('::')[1] || '').replace(/^f_/, '') : null;
        var look = { colour: colours.length ? { word: colours[0], hex: colours[0], families: uniq([hexFamily(colours[0])]) } : null, finish: finish ? { key: finish, family: fam } : null, finish_class: fam ? (FINISH_WORDS.filter(function (fw) { return fw[1].test(fam.replace(/_/g, ' ')); }).map(function (fw) { return fw[0]; })[0] || null) : null };
        if (stops) look.gradient = { stops: stops }; if (stroke != null) look.stroke = { px: stroke }; if (pattern) look.pattern = pattern;
        var zd = opts.zdiff || null, zids = (opts.zone_ids || []).slice(), znames = [];
        if (zd) { (zd.added || []).concat(zd.edited || []).forEach(function (z) { if (z && z.id != null) { zids.push(String(z.id)); if (z.name) znames.push(z.name); } }); }
        return { turn: opts.turn, source: opts.source || 'app', said: opts.said, verbs: uniq(verbs), targets: opts.targets || tg, look: look, scope_mask_id: opts.scope_mask_id || null, zone_ids: zids, zone_names: znames,
            layers: uniq(layers), colours: uniq(colours), finish: finish, stroke_px: stroke, gradient_stops: stops, edited_zone_ids: zd ? (zd.edited || []).map(function (z) { return String(z.id); }) : [], undo_id: opts.undo_id, entry_id: opts.entry_id, editCtx: opts.editCtx || null };
    }
    function commitQueue(queue, opts) { return commit(queueToRecord(queue, opts)); }
    // fromEntry: one call per js/spb-pro-ai.js log entry (idempotent by entry.id): a change, an offer of options, a question back, or an answer
    function fromEntry(entry, r, text) {
        if (!entry || entry.role !== 'ai') return null; var key = String(entry.id); S.wired = true;
        if (S.byEntry[key]) return changeById(S.byEntry[key]);
        var tr = curTurn(); if (!tr || (text && tr.said !== String(text).slice(0, 300) && tr.act != null)) turn(text || entry.request || '', { producer: entry.kind || null });
        if (entry.lines && entry.lines.length && (entry.zdiff || entry.undoable)) {
            var q = (r && r.queue) || entry.recipe || [];
            var frm = null; try { var IF = W.SpbIntentFrame; frm = IF && IF.last ? IF.last() : null; } catch (e) {}
            var tgs = null; if (frm && frm.ops && frm.ops.length) tgs = frm.ops.map(function (o) { return o.target; }).filter(Boolean);
            if ((!tgs || !tgs.length) && entry.editCtx && entry.editCtx.targets) tgs = entry.editCtx.targets;
            var ch = commitQueue(q, { source: entry.kind === 'mcp' ? 'mcp' : (r && r.offline ? 'offline' : (entry.elem ? 'element' : 'model')), said: entry.request || text, zdiff: entry.zdiff, undo_id: entry.id, entry_id: entry.id, editCtx: entry.editCtx || null, targets: tgs && tgs.length ? tgs : undefined, scope_mask_id: entry.verify && entry.verify.mask_id || null });
            S.byEntry[key] = ch.id; return ch;
        }
        if (entry.options && entry.options.length) { offer({ kind: 'options', items: entry.options.map(function (o) { return { label: o.label || o.name || String(o), key: o.key || null }; }) }); S.byEntry[key] = 'offer'; return null; }
        if (entry.opts && entry.opts.length) { offer({ kind: 'chips', items: entry.opts.map(function (o) { return { label: typeof o === 'string' ? o : (o.label || '') }; }) }); }
        note({ act: r && r.asked ? 'ask' : 'answer', topic: r && r.enc ? (r.enc.id || null) : null, asked: r && r.asked ? (r.asked.question || null) : null, missing: r && r.asked ? ['answer'] : undefined, editCtx: entry.editCtx });
        S.byEntry[key] = 'note'; return null;
    }
    // ChatGPT review proposal Oct10: completed factual material answers must
    // not infer one material/target from a comparison or leave a soft ask.
    // Caller is the local completed producer, after its actual entry was noted.
    // This retires conversation inference only; it grants no execution target.
    function completeReadOnly(text, entryId, topic) {
        var tr=curTurn();
        if(!on()||!tr||tr.act!=='answer'||tr.change||tr.offer||
            tr.said!==String(text||'').slice(0,300)||S.byEntry[String(entryId)]!=='note')return false;
        tr.targets=[];tr.look=null;S.pending=null;S.lastRes=null;
        if(topic)S.topic={id:String(topic).slice(0,200),turn:tr.turn};
        return true;
    }
    // noteRoute: js/spb-offline-answer.js claim() after nextState(): r.list = an offer, r.pend = a pending slot, r.topic = what an answer was about
    function noteRoute(r, text) {
        if (!r) return null; S.wired = true; var tr = curTurn(); if (!tr || tr.said !== String(text || '').slice(0, 300)) turn(text, { producer: 'offline' });
        if (r.list && r.list.items) offer({ kind: 'finishes', items: r.list.items.map(function (x) { return { label: x.label || x.name || x.key || String(x), key: x.key || x.id || null }; }), legacy: r.list });
        if (!r.pend && S.pending && !S.pending.soft) S.pending = null;          // legacy CS.pending lived one turn
        if (r.pend) note({ act: 'ask', missing: [r.pend.need || 'value'], targets: (r.pend.parts || r.pend.cands || []).map(function (p) { return { kind: 'part', parts: [p] }; }), legacyPending: r.pend, topic: r.topic || null });
        else if (r.cls === 'ANSWER' || r.cls === 'ASK') note({ act: r.cls === 'ASK' ? 'ask' : 'answer', topic: r.topic || null, nopaint: r.nopaint || null });
        return curTurn();
    }
    // a frame Target -> the js/spb-pro-edit.js target shape (S6: the editor's it / them / same rules read SpbConvo.resolve(text).targets through this)
    function toEditTarget(tg) {
        tg = normTarget(tg); if (!tg) return null;
        if (tg.kind === 'part') return (tg.parts || []).map(function (p) { return { kind: 'part', part: p }; });
        if (tg.kind === 'element' && (tg.element === 'numbers' || tg.element === 'sponsors')) return [{ kind: tg.element }];
        if (tg.kind === 'colour') return [{ kind: 'colour', word: (tg.colour && tg.colour.word) || '', hex: (tg.colour && tg.colour.hex) || null }];
        if (tg.kind === 'body') return [{ kind: 'car' }];
        return [{ kind: 'layerword', word: tg.object || tg.element || (tg.layers || []).join(' ') || tg.kind }];
    }
    // legacy reads (the shims return these instead of scanning the log)
    function lastEditCtx(opts) {          // the legacy editCtx of the last change. Default = js/spb-pro-ai.js lastEditCtx (any reply after it hides it); opts.skipTalk = js/spb-offline-answer.js lastCtx (a question back / answer / offer in between does not)
        var skip = !!(opts && opts.skipTalk), tr = null;
        for (var i = S.turns.length - 1; i >= 0; i--) { var a = S.turns[i].act; if (skip ? /^(?:change|undo|redo)$/.test(a || '') : (a && a !== 'nothing')) { tr = S.turns[i]; break; } }
        if (!tr) return null;
        if (skip && tr.act === 'undo') {          // HELPER V3 S4 wiring 2026-10-06 (R-036): after an Undo, "now make it satin" is about the change still on the car on the SAME part (never another part's change)
            var un = tr.change && changeById(tr.change), lv = liveChanges();
            for (var j = lv.length - 1; j >= 0; j--) if (lv[j].editCtx && un && (touches(lv[j].keys, un.keys) || touches(un.keys, lv[j].keys))) return clone(lv[j].editCtx);
            return null;
        }
        if (tr.act !== 'change' && tr.act !== 'redo') return null; var ch = changeById(tr.change); return ch && !ch.undone && ch.editCtx ? clone(ch.editCtx) : null;
    }
    function editCtxHistory(n) { var out = []; for (var i = S.changes.length - 1; i >= 0 && out.length < (n || 12); i--) { var c = S.changes[i]; if (!c.undone && c.editCtx) out.push(clone(c.editCtx)); } return out; }
    function lastUndoneEditCtx() { for (var i = S.changes.length - 1; i >= 0; i--) { var c = S.changes[i]; if (c.editCtx) return c.undone ? clone(c.editCtx) : null; } return null; }
    function legacyList() { var off = S.offer && (CLOCK() - S.offer.at < OFFER_TTL_MS) ? S.offer : null; return off ? (off.legacy || (off.kind === 'chips' ? null : { q: null, items: off.items })) : null; }          // HELPER V3 S3 2026-10-06: reply chips ("The roof", "The hood") are not a finish list: in-app b4-139 "orange" -> "just the roof" picked a finish called "The roof" and lost the orange
    function legacyPending() { return S.pending && (CLOCK() - S.pending.at < PENDING_TTL_MS) ? (S.pending.legacy || null) : null; }

    W.SpbConvo = {
        V: V, on: on, flag: flag, reset: reset, wired: function () { return !!(S && S.wired) && on(); }, read: read, fixWords: fixWords, targetsOf: function (t, env) { return explicitTargets(read(t, env), null); }, keysOf: keysOf, normTarget: normTarget, hexFamily: hexFamily, coloursOf: coloursOf,
        turn: turn, commit: commit, commitQueue: commitQueue, queueToRecord: queueToRecord, offer: offer, note: note, undone: undone, redone: redone,
        fromEntry: fromEntry, noteRoute: noteRoute, completeReadOnly: completeReadOnly, resolve: resolve, view: view,
        lastEditCtx: lastEditCtx, editCtxHistory: editCtxHistory, lastUndoneEditCtx: lastUndoneEditCtx, legacyList: legacyList, toEditTarget: toEditTarget, legacyPending: legacyPending,
        changes: function () { return clone(S.changes); }, turns: function () { return clone(S.turns); }, lastOffer: function () { return clone(S.offer); }, pending: function () { return clone(S.pending); },
        change: function (id) { return clone(changeById(id) || changeOfTurn(id) || changeByUndo(id)); }, _state: function () { return S; }, _clock: function (fn) { CLOCK = fn || function () { return Date.now(); }; return true; }
    };
})();
