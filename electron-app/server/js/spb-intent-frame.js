/* ============================================================================
   HELPER V3 S1 2026-10-05 (docs/handoff_reports/HELPER_ARCHITECTURE_V3.md section 2.1, stage S1): the INTENT FRAME.
   One shared description of "what this turn asked for / what the helper is about to do", written by every producer
   (offline helper route, guided builder, pro-edit plan, DeepSeek tool loop, MCP) and logged into the turn log
   (output/ai_logs/copilot_turns.jsonl, record field "frame"). S1 = schema + adapters + logging only: NOTHING here
   changes what the helper does. The verifier (js/spb-intent-verify.js, stage S2) reads the same frame.
   Global: window.SpbIntentFrame   (window.SpbIntent is the older finish-advisor intent model: a different module).
     read(text, env)            -> the sentence's own reading (named parts / layers / elements, keep-clauses, whole-car words,
                                   question form, unresolved region words, typo'd part words). Independent of every producer.
     stepsToFrame(steps, text, producer)   builder steps (js/spb-offline-builder.js) -> frame
     routeToFrame(r, text, env)            an offline route result (js/spb-offline-answer.js route) -> frame
     opsToFrame(ed, text, producer)        a pro-edit plan (js/spb-pro-edit.js plan / compile input) -> frame
     queueToFrame(queue, text, producer, tools)   an app queue (js/spb-pro-ai.js applyQueue input: DeepSeek, MCP, offline Run) -> frame
     validate(frame, env)       -> { ok, errors }
     note(frame) / since(t0) / last()      the in-page ring the turn log reads
   Settings: SPB_AI_FRAME = '0' (window var or localStorage key) switches frames AND the verifier off: the legacy helper exactly.
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var V = 1;
    var ACTS = ['change', 'answer', 'list', 'ask_back', 'undo', 'redo', 'save', 'nothing'];
    var VERBS = ['recolour', 'refinish', 'restyle', 'outline', 'pinline', 'stripe', 'gradient', 'pattern', 'graphic', 'copy_look', 'adjust', 'retarget', 'hide', 'show'];
    var KINDS = ['body', 'part', 'layer', 'colour', 'element', 'object', 'zone', 'box', 'graphic'];
    var CANON_PARTS = ['hood', 'roof', 'trunk', 'spoiler', 'front bumper', 'rear bumper', 'left side', 'right side'];

    function flag(name, dflt) {
        try { if (W[name] != null) return String(W[name]); } catch (e) {}
        try { if (W.localStorage) { var v = W.localStorage.getItem(name); if (v != null) return String(v); } } catch (e2) {}
        return dflt;
    }
    function on() { return flag('SPB_AI_FRAME', '1') !== '0'; }
    function clone(o) { try { return o == null ? o : JSON.parse(JSON.stringify(o)); } catch (e) { return null; } }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }
    function low(t) { return String(t || '').toLowerCase().replace(/[\u2018\u2019]/g, "'"); }

    // ------------------------------------------------------------------ the sentence's own reading (no producer involved)
    var PART_RE = /\b(front bumper|rear bumper|back bumper|left side|right side|bumpers?|sides|side|doors?|hood|bonnet|roof|trunk|boot|deck ?lid|spoiler|wing)\b/gi;          // = js/spb-offline-answer.js P7_PART_RE (the parts the app can mask)
    function partsOf(t) {
        try { var OA = W.SpbOfflineAnswer; if (OA && OA._partsOf) return OA._partsOf(t).slice(); } catch (e) {}
        var out = [], s = low(t).replace(/\b(?:the )?other side\b/g, ' '), m; PART_RE.lastIndex = 0;
        while ((m = PART_RE.exec(s))) {
            var w = m[1];
            if (/^(?:sides|side|doors?)$/.test(w)) { out.push('left side'); out.push('right side'); }
            else if (/^bumpers?$/.test(w)) { out.push('front bumper'); out.push('rear bumper'); }
            else if (w === 'back bumper') out.push('rear bumper'); else if (w === 'bonnet') out.push('hood'); else if (/^(?:boot|deck ?lid)$/.test(w)) out.push('trunk'); else if (w === 'wing') out.push('spoiler');
            else out.push(w);
        }
        return uniq(out);
    }
    // region words the car map cannot mask (a whole-car change is never what they mean)
    var UNRESOLVED_RE = /\b(mirrors?|fenders?|quarter ?panels?|quarters?|nose|tail ?gate|tail|bed|splitter|diffuser|rockers?|side ?skirts?|skirts?|pillars?|windows?|wind ?shield|glass|grilles?|grill|roll ?cage|cage|intakes?|vents?|scoops?|hatch|front end|back end|rear end|number panels?|(?:the|my) (?:back|front|rear|bottom)(?! (?:bumper|half|third|of the (?:car|body)))|(?:the )?top(?= (?:of the|black|white|red|blue|green|yellow|orange|purple|pink|gold|silver|grey|gray|chrome|matte|gloss)\b)|thing at the (?:back|front))\b/gi;
    // typo'd part words ("doosr", "sdes", "bumprr", "mirrorrs"): never applied, only asked about (architecture rule 6: alts are never applied silently)
    var FUZZ_VOCAB = { doors: 'doors', sides: 'sides', bumper: 'bumper', bumpers: 'bumpers', spoiler: 'spoiler', mirror: 'mirror', mirrors: 'mirrors', fender: 'fender', fenders: 'fenders', bonnet: 'bonnet', trunk: 'trunk', tailgate: 'tailgate' };
    var FUZZ_STOP = { sizes: 1, tides: 1, rides: 1, sites: 1, hides: 1, aside: 1, sided: 1, wider: 1, rider: 1, bumpy: 1, drunk: 1, spoilt: 1, spoiled: 1, codes: 1, nodes: 1, modes: 1, dodge: 1, doers: 1, doses: 1, dozes: 1, mirror: 1, mirrors: 1, fender: 1, fenders: 1, decor: 1, donor: 1, odors: 1, floors: 1, tender: 1, render: 1, lender: 1, sender: 1, bender: 1, member: 1, number: 1, numbers: 1, bumper: 1, bumpers: 1, slides: 1, guides: 1, brides: 1, prides: 1, besides: 1, insides: 1, outsides: 1, sidesa: 0, stripes: 1, spider: 1, spoilers: 1, trunks: 1, trucks: 1, truck: 1, track: 1, tracks: 1, mirrored: 1, mirroring: 1 };
    function dl(a, b) {          // Damerau-Levenshtein (optimal string alignment)
        var n = a.length, m = b.length, d = [], i, j; if (Math.abs(n - m) > 2) return 9;
        for (i = 0; i <= n; i++) { d[i] = [i]; } for (j = 0; j <= m; j++) d[0][j] = j;
        for (i = 1; i <= n; i++) for (j = 1; j <= m; j++) {
            var c = a[i - 1] === b[j - 1] ? 0 : 1; d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
            if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
        }
        return d[n][m];
    }
    function fuzzyParts(t) {
        var out = []; low(t).replace(/[^a-z ]+/g, ' ').split(/\s+/).forEach(function (w) {
            if (w.length < 4 || FUZZ_STOP[w] || FUZZ_VOCAB[w]) return;
            Object.keys(FUZZ_VOCAB).some(function (v) { var d = dl(w, v); if ((v.length >= 5 && d === 1) || (v.length >= 7 && d === 2 && w.length >= 6)) { out.push({ said: w, maybe: FUZZ_VOCAB[v] }); return true; } return false; });
        });
        return out;
    }
    // R6-READ3 R6d: the 'and the logos / numbers / sponsors' include cue does not count inside an except / keep list
    function r6Dec(t) {
        var re = /\b(?:including|even|also|too|and) (?:the )?(?:numbers|sponsors|decals|logos)\b|\b(?:numbers|sponsors|decals|logos) too\b|\ball layers\b/i, m = re.exec(t);
        if (!m) return 'protect';
        try { var c = (typeof window !== 'undefined' ? window : {}).SPB_OF_CFG; if (c && c.noR6d) return 'include'; } catch (e) {}
        if (/^and\b/i.test(m[0])) { var ex = /\b(?:except(?: for)?|excluding|besides|apart from|other than|but not|minus|leave|leaving|keep|keeping|not|without|don'?t touch|dont touch)\b/i.exec(t); if (ex && ex.index < m.index) return 'protect'; }
        return 'include';
    }
    var ELEM = [['numbers', /\b(numbers?|digits?|race ?numbers?)\b/i], ['sponsors', /\b(sponsors?|logos?|decals?|stickers?|contingenc\w*)\b/i], ['stripes', /\b(stripes?|pin ?stripes?|pinlines?|racing stripes?)\b/i]];
    var WHOLE_RE = /\b(whole|entire|every ?thing|everywhere|all over|all of it|the (?:whole )?car|the body|my car|all the car|full car|complete car|rest of (?:the )?(?:car|body)|the rest|all black|all white|all red|all blue|all one colou?r)\b/i;
    var COLOURS = 'red|white|black|blue|green|yellow|orange|purple|pink|gold|silver|grey|gray|brown|teal|cyan|magenta|maroon|navy|lime|charcoal|bronze|copper|violet|crimson|tan|beige|cream';
    function w1kOff() { try { var c = (typeof window !== 'undefined' ? window : {}).SPB_OF_CFG; return !!(c && c.noW1k); } catch (e) { return false; } }          // W1-PARSE 2026-10-08 kill switch for the 'sponsor decals' keep fix
    var KEEP_X = '(front bumper|rear bumper|back bumper|left side|right side|bumpers?|sides|side|doors?|door|hood|roof|trunk|spoiler|wing|numbers?|digits?|(?:sponsors?|logos?|decals?|stickers?)(?: (?:decals?|logos?|stickers?|art|graphics?|names?))?|stripes?|border|borders|outline|edges?|trim|shadow|paint around it|rest of the (?:logo|number|numbers|art)|everything else(?: in the (?:logo|logos|number|numbers|art))?)';
    var KEEP_RES = [
        new RegExp('\\b(?:leave|leaving|don\'?t touch|dont touch|do not touch|never touch|without touching|except(?: for)?|apart from|other than|but not|not)\\s+(?:the |my |both |any )?' + KEEP_X + '\\b', 'gi'),
        new RegExp('\\b(?:the |my )?' + KEEP_X + '\\s+(?:can |should |will |must |to )?(?:stays?|staying|remains?|untouched|unchanged|alone|(?:is|are) fine|(?:is|are) good|no change|not (?:changed|touched|(?:' + COLOURS + ')))\\b', 'gi'),
        new RegExp('\\bkeep(?:ing)?\\s+(?:the |my )?' + KEEP_X + '\\s+(?:as (?:it|they) (?:is|are|were|was)|the same|untouched|alone|unchanged|how (?:it|they) (?:is|are))', 'gi'),
        new RegExp('\\b' + KEEP_X + '\\s+(?:' + COLOURS + ')\\s+no change\\b', 'gi')
    ];
    // R6-READ3 2026-10-08 R6b ('whole car white except hood, roof and the sponsor panels' excluded only the hood): a keep / except lead names a LIST - 'the hood, roof and spoiler', 'hood roof and trunk'.
    // Walk the list after the first item; an item followed by its own colour / look ('leave the hood, roof black') starts a new order and ends the list. Kill: SPB_OF_CFG.noR6b.
    var R6_LIST = new RegExp('^\\s*(?:,\\s*(?:and\\s+|then\\s+)?|and\\s+|&\\s*|\\s+)(?:the |my )?' + KEEP_X + '\\b(?!\\s+(?:' + COLOURS + '|matte|gloss|glossy|satin|chrome|flat|metallic|pearl|candy|carbon|camo)\\b)', 'i');
    function r6Off() { try { var c = (typeof window !== 'undefined' ? window : {}).SPB_OF_CFG; return !!(c && c.noR6b); } catch (e) { return false; } }
    function keepOf(t) {
        var s = low(t), out = []; if (/^\s*(?:not|no)\b/.test(s)) return out;          // "not the hood, the roof" = a correction (retarget), never a keep
        KEEP_RES.forEach(function (re, ri) { re.lastIndex = 0; var m; while ((m = re.exec(s))) { var w = m[1]; if (out.indexOf(w) === -1) out.push(w);
            if (ri === 0 && !r6Off()) { var rest = s.slice(m.index + m[0].length), lm; while ((lm = R6_LIST.exec(rest))) { if (out.indexOf(lm[1]) === -1) out.push(lm[1]); rest = rest.slice(lm[0].length); } } } });
        return out;
    }
    function keepTargets(words) {
        var parts = [], elements = [], sub = [];
        words.forEach(function (w) {
            if (w1kOff()) w = String(w).split(' ')[0];
            if (/^(?:numbers?|digits?)$/.test(w)) elements.push('numbers');
            else if ((w1kOff() ? /^(?:sponsors?|logos?|decals?|stickers?)$/ : /^(?:sponsors?|logos?|decals?|stickers?)(?: (?:decals?|logos?|stickers?|art|graphics?|names?))?$/).test(w)) elements.push('sponsors');          // W1-PARSE 2026-10-08: 'do not touch the sponsor decals' = one keep (was 'sponsor' kept + 'decals' left as a named target -> the verifier asked)
            else if (/^stripes?$/.test(w)) elements.push('stripes');
            else if (/^(?:door|doors|side|sides)$/.test(w)) { parts.push('left side'); parts.push('right side'); }
            else if (/^(?:border|borders|outline|edges?|trim|shadow|paint around it|rest of|everything else)/.test(w)) sub.push(w);
            else partsOf(w).forEach(function (p) { parts.push(p); });
        });
        return { parts: uniq(parts), elements: uniq(elements), sub: uniq(sub) };
    }
    function layersOf(t, env) {
        var s = low(t).replace(/_/g, ' '), out = [];
        ((env && env.layers) || []).forEach(function (l) {
            if (!l || !l.name || /mask|wire|mandatory|template/i.test(l.name + ' ' + (l.role || ''))) return;
            var nm = low(l.name).replace(/_/g, ' ').trim(), esc = nm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '\\s+');
            var multi = nm.split(' ').length > 1, re = new RegExp('\\b' + esc + '\\b' + (multi ? '' : '\\s+(?:layers?|layr|lyr|laer|layer\\w*)\\b'), 'i'), re2 = multi ? null : new RegExp('\\b(?:layers?|layr|lyr)\\s*:?\\s+(?:called |named )?' + esc + '\\b', 'i');
            if (re.test(s) || (re2 && re2.test(s))) out.push(l.name);
        });
        return out;
    }
    function boundColours(t) {          // "white numbers", "w a white number", "numbers white" -> { numbers: ['white'] }
        var s = low(t), out = {}, m, re1 = new RegExp('\\b(' + COLOURS + ')\\s+(?:race\\s+)?(numbers?|digits?|logos?|sponsors?)\\b', 'g'), re2 = new RegExp('\\b(numbers?|digits?)\\s+(?:in\\s+|are\\s+|stay\\s+)?(' + COLOURS + ')\\b', 'g');
        var add = function (el, c) { el = /^(?:numbers?|digits?)$/.test(el) ? 'numbers' : 'sponsors'; (out[el] = out[el] || []).push(c === 'gray' ? 'grey' : c); };
        while ((m = re1.exec(s))) add(m[2], m[1]);
        while ((m = re2.exec(s))) add(m[1], m[2]);
        return out;
    }
    var Q_START_RE = /^\s*(?:(?:ok|okay|so|hey|hi|and|but|also|um+|hmm+)[\s,]+)*(?:if i|what if|in what|what|where|which|why|how|when|who|does|do i|do you|is it|is there|are there|will (?:my|it|the|that|this)|would (?:my|it|the|that|this)|should i|can i|could i)\b/i;
    var OPTIONS_RE = /\b(?:show (?:me )?both|two options|(?:some |a few )?options for|ideas? for|give me (?:some )?ideas|mood ?board|show me (?:the |my )?\w+(?: \w+)? as\b|what would .{1,40} look like|compare)\b/i;
    // W1-PARSE 2026-10-08: whole-car word BEFORE 'even / including / as well as <parts>' (and no look word right after) = the include-clause names parts the whole-car job already covers.
    var W1_INCL = /\s*,?\s*\b(?:and \s*)?(?:even|including|incl|as well as|along with)\s+(?:the |my )?(?:(?:front |rear |back |left |right )?(?:hood|bonnet|roof|trunk|boot|spoiler|wing|bumpers?|doors?|sides?|mirrors?|fenders?|splitter|diffuser)(?:\s*(?:,|and|&)\s*(?:the |my )?)?)+/i;
    function w1Incl(t) {
        try { var c = (typeof window !== 'undefined' ? window : {}).SPB_OF_CFG; if (c && c.noW1i) return t; } catch (e) {}
        var m = W1_INCL.exec(t); if (!m) return t; var before = t.slice(0, m.index), after = t.slice(m.index + m[0].length);
        if (!/\b(?:everything|every ?thing|all|whole|entire|every part|all parts|all panels|all of it|the (?:car|truck|body))\b/i.test(before)) return t;
        if (/^\s*(?:in |to |with |as )?(?:red|orange|yellow|green|blue|purple|violet|pink|white|black|silver|grey|gray|gold|teal|navy|chrome|matte|satin|gloss|carbon)\b/i.test(after) && !/[,;]\s*$/.test(m[0])) return t;          // 'even the roof blue' = a second job
        return (before.replace(/\s+$/, '') + (after && !/^\s*[.!?;,]/.test(after) ? ' ' : '') + after.replace(/^\s+/, '')).replace(/\s{2,}/g, ' ');
    }
    function read(text, env) {
        var t = String(text || ''), s = low(t), keepW = keepOf(t), kt = keepTargets(keepW);
        var named = partsOf(t), unresolved = [], m;
        UNRESOLVED_RE.lastIndex = 0; while ((m = UNRESOLVED_RE.exec(s))) unresolved.push(m[1].trim());
        var els = []; ELEM.forEach(function (e) { if (e[1].test(s)) els.push(e[0]); });
        // a part / element named ONLY inside a keep-clause is not a target
        var rest = s; KEEP_RES.forEach(function (re) { rest = rest.replace(re, ' '); });
        rest = w1Incl(rest);          // W1-PARSE 2026-10-08: 'everything black even the spoiler': the part in an include-clause is part of the whole car, not a narrower target (kill SPB_OF_CFG.noW1i)
        var namedFree = partsOf(rest), elsFree = []; ELEM.forEach(function (e) { if (e[1].test(rest)) elsFree.push(e[0]); });
        var r = {
            said: t.slice(0, 600), whole: WHOLE_RE.test(rest), parts: namedFree, partsAll: named, unresolved: uniq(unresolved), fuzzy: fuzzyParts(rest),
            layers: layersOf(t, env), elements: elsFree, elementsAll: els, keep: kt, keepWords: keepW, bound: boundColours(t),
            q: Q_START_RE.test(t) && !/^\s*(?:what about|how about)\b/i.test(t), qmark: /\?\s*$/.test(t), options: OPTIONS_RE.test(t),
            decals: r6Dec(t)          // R6-READ3 R6d: 'except the hood, the roof and the logos' is a KEEP list, not 'and the logos too' (was 'include' = the logos painted / an add-logo answer). Kill: SPB_OF_CFG.noR6d
        };
        r.fuzzy = r.fuzzy.filter(function (f) { return r.parts.indexOf(f.maybe) === -1; });
        return r;
    }

    // ------------------------------------------------------------------ adapters (every producer -> the same frame)
    function base(producer, act, text) { return { v: V, turn: null, producer: producer, act: act, ops: [], keep: [], decals: 'protect', confidence: null, missing: [], alts: [], said: String(text || '').slice(0, 600) }; }
    function targetOfWhat(w) {
        if (!w) return null; var tg = w.tg || {};
        if (w.k === 'part') { var p = String(w.part || tg.part || ''), pi = p.split('@'); return { kind: 'part', parts: [pi[0]], portion: pi[1] || undefined }; }
        if (w.k === 'body' || w.k === 'main') return { kind: 'body', main: w.k === 'main' || undefined };
        if (w.k === 'colour') return { kind: 'colour', colour: { word: tg.word || null, hex: tg.hex || null }, parts: tg.parts || undefined, layers: tg.layers || undefined, object: tg.object || undefined };
        if (w.k === 'layer') return { kind: 'layer', layers: (w.layers || tg.layers || []).slice() };
        if (w.k === 'numbers' || w.k === 'sponsors') return { kind: 'element', element: w.k };
        if (w.k === 'box') return { kind: 'box' };
        if (w.k === 'step') return { kind: 'zone', ref: w.ref };
        return tg.kind ? opTarget(tg) : { kind: KINDS.indexOf(w.k) !== -1 ? w.k : 'object', object: KINDS.indexOf(w.k) !== -1 ? undefined : String(w.k || '') };
    }
    function lookOfStep(st) {
        var L = {};
        if (st.colour) L.colour = { word: st.colour.name || null, hex: st.colour.hex || null };
        if (st.finish) L.finish = { key: st.finish.key || null, label: st.finish.label || null, keep_colour: st.act === 'shine' || /^base::f_/.test(String(st.finish.key || '')) || undefined, copy: st.finish.kind === 'copy' || undefined };
        if (st.tex) L.pattern = { id: st.tex.id || null, concept: st.tex.label || null, mode: st.tex.mode || null };
        var x = st.extra || {};
        if (x.gradient) L.gradient = clone(x.gradient);
        if (x.outline) L.stroke = clone(x.outline);
        if (x.scaleMul) L.scale = x.scaleMul;
        return L;
    }
    function verbOfStep(st) {
        var x = st.extra || {};
        if (x.outline) return 'outline'; if (x.gradient) return 'gradient'; if (st.finish && st.finish.kind === 'copy') return 'copy_look';
        if (x.rel || x.scaleMul || x.strengthMul || x.shade) return 'adjust';
        if (st.act === 'recolour') return 'recolour'; if (st.act === 'pattern') return 'pattern'; return 'refinish';
    }
    function exceptOf(list) {          // step / op excludes: part names, or the protected elements ('numbers', 'sponsors')
        var parts = [], out = [];
        (list || []).forEach(function (e) { var n = typeof e === 'string' ? e.split('@')[0] : (e && e.part) || null; if (!n) return; if (/^(?:numbers|sponsors|stripes|logos)$/.test(n)) out.push({ kind: 'element', element: n === 'logos' ? 'sponsors' : n }); else if (parts.indexOf(n) === -1) parts.push(n); });
        if (parts.length) out.unshift({ kind: 'part', parts: parts });
        return out;
    }
    function stepsToFrame(steps, text, producer) {
        var f = base(producer || 'offline', (steps || []).length ? 'change' : 'nothing', text), byId = {};
        (steps || []).forEach(function (st) {
            if (!st || !st.what) { f.missing.push('target'); return; }
            if (st.what.k === 'step' && byId[st.what.ref]) { var op0 = byId[st.what.ref], lk = lookOfStep(st); Object.keys(lk).forEach(function (k) { op0.look[k] = lk[k]; }); byId[st.id] = op0; return; }
            var op = { verb: verbOfStep(st), target: targetOfWhat(st.what), look: lookOfStep(st) };
            var cpF = st.finish && st.finish.kind === 'copy' && st.finish.copy, offF = false; try { offF = !!W.SPB_FRAME_NOCOPYSRC; } catch (eK) {}
            if (cpF && !offF) {          // lane R3-EDIT 2026-10-07 H1b (sealed "make the hood the same red as the logo" -> hood BLUE): the copy's source zone rode only on the step, so the planner copied the TARGET part's own zone; a sampled colour = a recolour. Kill switch: window.SPB_FRAME_NOCOPYSRC
                if (cpF.zone_id) op.source = { kind: 'zone', zones: [cpF.zone_id] };
                else if (cpF.sampled && cpF.color) { op.verb = 'recolour'; op.look = { colour: { word: cpF.word || null, hex: cpF.color } }; }
            }
            var ex = (st.extra && st.extra.exclude) || []; if (ex.length) op.except = exceptOf(ex);
            if (st.act === 'recolour' && !st.colour) f.missing.push('colour'); else if (st.act && st.act !== 'recolour' && !st.finish && !st.tex && !(st.extra && (st.extra.rel || st.extra.pop || st.extra.shade || st.extra.recipe))) f.missing.push('look');
            if (st.ask) f.missing.push('pick');
            f.ops.push(op); byId[st.id] = op;
        });
        f.missing = uniq(f.missing);
        return f;
    }
    function routeToFrame(r, text, env) {
        var act = 'nothing';
        if (r) {
            if (/^undo/.test(r.pass || '')) act = 'undo'; else if (r.pass === 'redo') act = 'redo';
            else if ((r.steps || []).length && (r.cls === 'DO' || r.cls === 'PREFILL')) act = 'change';
            else if (r.cls === 'ASK' || r.cls === 'PREFILL') act = r.list ? 'list' : 'ask_back';
            else if (r.cls === 'ANSWER' || r.cls === 'LOCAL' || r.cls === 'OFFTOPIC') act = 'answer';
        }
        var f = (act === 'change') ? stepsToFrame(r.steps, text, 'offline') : base('offline', act, text);
        if (act === 'change' && r.cls === 'PREFILL') f.missing = uniq(f.missing.concat(['confirm']));
        if (r && r.answer && r.answer.id) f.question = { topic: r.answer.id, text: String(text || '').slice(0, 200) };
        if (r && r.list && r.list.items) f.list = { of: 'finishes', items: r.list.items.slice(0, 6).map(function (x) { return x.label || x.key || null; }) };
        if (r && r.via) f.via = r.via; if (r && r.pass) f.pass = r.pass;
        var rd = read(text, env); f.keep = rd.keep.parts.map(function (p) { return { kind: 'part', parts: [p] }; }).concat(rd.keep.elements.map(function (e) { return { kind: 'element', element: e }; }));
        f.decals = rd.decals;
        f.alts = rd.fuzzy.map(function (x) { return { slot: 'target.parts', said: x.said, maybe: x.maybe }; });
        if (act === 'change') { try { var DRf = W.SpbIntentDoor; if (DRf && DRf.annotate) DRf.annotate(f, text, env); } catch (eDr) {} }          // D-DOOR 2026-10-08 hook: door / fender / quarter / rocker words -> portion of the side panel (or an ask)
        return f;
    }
    function opTarget(tg) {
        if (!tg) return null;
        if (tg.kind === 'part') { var pp = String(tg.part || '').split('@'); return { kind: 'part', parts: [pp[0]], portion: tg.portion || pp[1] || undefined }; }
        if (tg.kind === 'body' || tg.kind === 'main') return { kind: 'body' };
        if (tg.kind === 'colour') return { kind: 'colour', colour: { word: tg.word || null, hex: tg.hex || null }, parts: tg.parts || undefined, layers: tg.layers || undefined, object: tg.object || undefined };
        if (tg.kind === 'numbers' || tg.kind === 'sponsors') return { kind: 'element', element: tg.kind };
        if (tg.kind === 'layer' || tg.kind === 'layerword') return { kind: 'layer', layers: (tg.layers || [tg.word]).slice() };
        if (tg.kind === 'accents') return { kind: 'element', element: 'stripes' };
        if (tg.kind === 'box') return { kind: 'box' };
        return KINDS.indexOf(tg.kind) !== -1 ? { kind: tg.kind } : { kind: 'object', object: String(tg.word || tg.kind || '') };
    }
    function opsToFrame(ed, text, producer) {
        var f = base(producer || 'pro-edit', 'nothing', text); if (!ed) return f;
        if (ed.kind === 'ask') { f.act = 'ask_back'; return f; }
        if (ed.kind === 'complaint') { f.act = 'change'; f.ops.push({ verb: 'retarget', target: { kind: 'zone', ref: 'last_change' } }); return f; }
        if (ed.kind !== 'ops') return f;
        f.act = (ed.ops || []).length ? 'change' : 'nothing';
        (ed.ops || []).forEach(function (op) {
            var L = {};
            if (op.colour) L.colour = { word: op.colour.name || null, hex: op.colour.hex || null };
            if (op.look) L.finish = { key: op.look.found || (op.look.zone && op.look.zone.finish) || op.look.id || null, label: op.look.label || null };
            if (op.texture) L.pattern = { id: op.texture.pattern || op.texture.spec || null, concept: op.texture.label || null };
            if (op.gradient) L.gradient = clone(op.gradient); if (op.outline) L.stroke = clone(op.outline);
            var o2 = { verb: op.outline ? 'outline' : op.gradient ? 'gradient' : op.copy ? 'copy_look' : op.colour ? 'recolour' : op.texture && !op.look ? 'pattern' : (op.rel || op.scaleMul || op.shade) ? 'adjust' : 'refinish', target: opTarget(op.target), look: L };
            if (op.copy) o2.copy = Object.keys(op.copy).filter(function (k) { return op.copy[k]; });
            if ((op.exclude || []).length) o2.except = exceptOf(op.exclude);
            f.ops.push(o2);
        });
        if ((ed.exclude || []).length) f.keep = exceptOf(ed.exclude);
        if ((ed.unknown || []).length) f.missing = ed.unknown.slice(0, 4);
        return f;
    }
    function regionTarget(rg) {
        if (!rg) return { kind: 'zone' };
        if (rg.graphic) return { kind: 'graphic', graphic: typeof rg.graphic === 'string' ? rg.graphic : clone(rg.graphic) };
        if (rg.element) return { kind: 'element', element: String(rg.element).split(':')[0] };
        if (rg.rect || rg.cells) return { kind: 'box' };
        var isl = rg.island || rg.part, parts = isl ? [].concat(isl).map(String) : null, T;
        if (rg.colors && rg.colors.length) T = { kind: 'colour', colour: { word: null, hex: rg.colors[0] }, parts: parts || undefined, layers: rg.layers || undefined };
        else if (parts) T = { kind: 'part', parts: parts, portion: rg.portion || undefined, layers: rg.layers || undefined };
        else if (rg.layers && rg.layers.length) T = { kind: 'layer', layers: [].concat(rg.layers).map(String) };
        else T = { kind: 'body' };
        return T;
    }
    function queueToFrame(queue, text, producer, tools) {
        var f = base(producer || 'app', (queue || []).length ? 'change' : 'nothing', text);
        (queue || []).forEach(function (q) {
            if (!q) return;
            if (q.kind === 'layer') { f.ops.push({ verb: q.visible === false ? 'hide' : 'show', target: { kind: 'layer', layers: [q.name || q.layer] }, look: q.opacity != null ? { opacity: q.opacity } : {} }); return; }
            if (q.kind === 'restore' || q.kind === 'carve') { f.ops.push({ verb: 'retarget', target: { kind: 'zone', zone: q.id || null }, look: {} }); return; }
            var sp = q.spec || {}, L = {};
            var col = sp.color || sp.base_color; if (typeof col === 'string' && /^#?[0-9a-f]{6}$/i.test(col)) L.colour = { hex: col.charAt(0) === '#' ? col : '#' + col };
            if (sp.finish) L.finish = { key: sp.finish, keep_colour: /^base::f_/.test(String(sp.finish)) || undefined };
            if (sp.pattern && sp.pattern !== 'none') L.pattern = { id: sp.pattern };
            if (sp.gradient) L.gradient = { stops: (sp.gradient.stops || sp.gradient.colors || []).slice ? (sp.gradient.stops || sp.gradient.colors || []).slice(0, 6) : null };
            if (sp.copy_look_from != null) L.copy_from = sp.copy_look_from;
            var tg = sp.region ? regionTarget(sp.region) : { kind: 'zone', zone: q.zone };
            if (sp.region && sp.region.exclude && sp.region.exclude.length) tg.except = [].concat(sp.region.exclude).map(function (e) { return typeof e === 'string' ? e : (e && e.part) || 'area'; });
            f.ops.push({ verb: q.kind === 'edit' && !sp.region ? 'adjust' : (L.gradient ? 'gradient' : L.colour ? 'recolour' : L.pattern && !L.finish ? 'pattern' : 'refinish'), target: tg, look: L, zone: q.kind === 'edit' ? q.zone : undefined, name: sp.name || undefined });
        });
        if (tools && tools.length) f.tools = tools.slice(0, 12);
        return f;
    }
    function validate(frame, env) {
        var err = []; if (!frame || frame.v !== V) return { ok: false, errors: ['not a v1 frame'] };
        if (ACTS.indexOf(frame.act) === -1) err.push('act ' + frame.act);
        var layers = ((env && env.layers) || []).map(function (l) { return l && l.name; }), parts = CANON_PARTS.slice();
        try { var C = W.SpbProCar, d = C && C.describe ? C.describe() : null; ((d && d.parts) || []).forEach(function (p) { if (p && p.name) parts.push(String(C.canon ? C.canon(p.name) : p.name)); }); } catch (e) {}
        try { if (!(W.SPB_W26_OFF || (W.SPB_OF_CFG && (W.SPB_OF_CFG.noW26 || W.SPB_OF_CFG.noW26_truck)))) ((env && env.parts) || []).forEach(function (p) { if (typeof p === 'string' && parts.indexOf(p) === -1) parts.push(p); }); } catch (e2) {}          // W26U 2026-10-10 (class 2): the planner env's own part list is valid too (a truck map's 'bed'); in-app it equals SpbProCar.parts()
        var tgt = function (T, where) {
            if (!T) return; if (KINDS.indexOf(T.kind) === -1) err.push(where + ': kind ' + T.kind);
            (T.parts || []).forEach(function (p) { if (parts.indexOf(p) === -1) err.push(where + ': part ' + p); });
            if (layers.length) (T.layers || []).forEach(function (L) { if (W.SpbLayerTargets ? !W.SpbLayerTargets.resolve(L, (env && env.layers) || []).ok : layers.indexOf(L) === -1) err.push(where + ': layer ' + L); });
            var hx = T.colour && T.colour.hex; if (hx && !/^#[0-9a-f]{6}$/i.test(hx)) err.push(where + ': hex ' + hx);
        };
        (frame.ops || []).forEach(function (op, i) {
            if (VERBS.indexOf(op.verb) === -1) err.push('op' + i + ': verb ' + op.verb);
            tgt(op.target, 'op' + i); (op.except || []).forEach(function (x) { tgt(x, 'op' + i + '.except'); });
            var c = op.look && op.look.colour; if (c && c.hex && !/^#[0-9a-f]{6}$/i.test(c.hex)) err.push('op' + i + ': look hex ' + c.hex);
        });
        (frame.keep || []).forEach(function (x, i) { tgt(x, 'keep' + i); });
        return { ok: !err.length, errors: err };
    }

    // ------------------------------------------------------------------ the in-page ring (the turn log reads it)
    var RING = [], SEQ = 0;
    function note(frame, extra) {
        if (!frame || !on()) return null;
        try { frame.turn = 't-' + (++SEQ); frame.t = Date.now(); if (extra) Object.keys(extra).forEach(function (k) { frame[k] = extra[k]; }); RING.push(frame); if (RING.length > 40) RING.shift(); } catch (e) {}
        return frame;
    }
    function since(t0) { return RING.filter(function (f) { return (f.t || 0) >= (t0 || 0); }); }
    function slim(f) { var s = clone(f); if (!s) return null; if (s.ops && s.ops.length > 8) s.ops = s.ops.slice(0, 8); return s; }

    W.SpbIntentFrame = {
        V: V, ACTS: ACTS, VERBS: VERBS, KINDS: KINDS, on: on, flag: flag,
        read: read, partsOf: partsOf, keepOf: keepOf, fuzzyParts: fuzzyParts,
        stepsToFrame: stepsToFrame, routeToFrame: routeToFrame, opsToFrame: opsToFrame, queueToFrame: queueToFrame, validate: validate,
        note: note, since: since, last: function () { return RING[RING.length - 1] || null; }, slim: slim, _reset: function () { RING = []; return true; }
    };
})();
