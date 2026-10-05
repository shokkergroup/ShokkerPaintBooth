// HELPER_V2 2026-10-04 owner: keep improving the Offline Helper (not just the Encyclopedia).
// Owner decision: offline (no AI model) = guided builder + keyword encyclopedia; free chat is for online (DeepSeek via OpenRouter) or MCP.
// This file is the offline helper's FRONT DOOR for a typed sentence. route(text, env) picks ONE outcome:
//   DO       an exact change: builder steps, all closed (or the app's own undo / start-over path)
//   PREFILL  part understood: builder steps with an OPEN step that already offers choices (a look the parser cannot read is searched in the catalogue)
//   ASK      one clarifying question with chips (e.g. the colour asked for only exists UNDER a zone that paints over it)
//   ANSWER   a question / how-to / why: the encyclopedia (hand-written articles, quick answers, FAQ questions) answers it offline: short answer,
//            the article's first real screenshot, "Read the full article", and "Do it" buttons from its actions[] -> builder steps
//   ONLINE   free chat the built-in helper cannot do: says so honestly and offers DeepSeek
// Search = BM25 over title / aliases / summary / FAQ questions / body (stemmed, typo-tolerant), with a coverage test so an off-topic question is not "answered".
// Pure logic runs in node: _easy_claude_work/helper_eval.js (corpus _easy_claude_work/helper_corpus.json). Never changes the car by itself: DO / PREFILL go
// through the builder (Run = the copilot's undoable path); numbers / sponsors / logos are only touched when the buyer names them (the parser's body-paint rule).
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : this;
    function B() { return W.SpbOfflineBuilder || null; }
    function Ed() { return W.SpbProEdit || null; }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    var BASE = 'data/encyclopedia/';

    // ------------------------------------------------------------------ words
    var STOP = {}; ('a an the is are was were be been am do does did doing done i me my mine we our you your yours it its it s this that these those there here to of in on at for by from with and or but if so as ' +
        'what whats wat wht how hw why where wheres when which who whos whom can could would should will shall may might must im ive id dont doesnt didnt cant wont isnt arent wasnt ' +
        'about tell explain please pls plz just really very much many some any thing things one also too get got gets getting have has had having need want wanna gonna like know ' +
        'thanks thank hi hey hello ok okay yes no not nothing something anything difference differences between vs versus compared compare another').split(' ').forEach(function (w) { if (w) STOP[w] = 1; });
    STOP.id = 0;      // "user id" is a real word here
    var SYN = { colour: 'color', colours: 'colors', coloured: 'colored', colouring: 'coloring', recolour: 'recolor', grey: 'gray', metalic: 'metallic', metalics: 'metallic', aluminium: 'aluminum', licence: 'license',
        centre: 'center', favourite: 'favorite', fibre: 'fiber', liveries: 'livery', clearcoat: 'clearcoat', clear: 'clear', photoshop: 'photoshop', psds: 'psd', tgas: 'tga', ui: 'interface',
        game: 'iracing', sim: 'iracing', ingame: 'iracing', iracings: 'iracing', id: 'id', numbers: 'number', nums: 'number', num: 'number', sponsor: 'sponsor', decals: 'decal', logos: 'logo',
        chromed: 'chrome', shiny: 'shine', shinier: 'shine', shininess: 'shine', glossy: 'gloss', glossier: 'gloss', flat: 'matte', mat: 'matte', mate: 'matte', speccing: 'spec', specs: 'spec' };
    function norm(s) { return String(s || '').toLowerCase().replace(/['’]/g, '').replace(/clear[\s-]+coat/g, 'clearcoat').replace(/\bget rid of\b/g, 'remove').replace(/\btrading paints?\b/g, 'tradingpaints').replace(/\b(ctrl|control)\s*[-+ ]\s*r\b/g, 'reload').replace(/\br (channel|value|slider)/g, 'metallic $1').replace(/\bg (channel|value|slider)/g, 'roughness $1').replace(/\bb (channel|value|slider)/g, 'clearcoat $1').replace(/[^a-z0-9#]+/g, ' ').trim(); }          // HELPER_V2 blind: "get rid of" = remove, "ctrl r" = reload
    var EXPAND = { missing: ['vanished', 'disappear', 'gone', 'lost'], vanish: ['missing', 'disappear'], disappear: ['missing', 'vanished'], gone: ['missing', 'lost'], big: ['size', 'large', '2048'], large: ['size', 'big'],
        size: ['big', '2048'], shine: ['gloss', 'shiny', 'spec'], gloss: ['shine', 'glossy'], matte: ['flat', 'gloss'], save: ['saving', 'project'], open: ['load', 'opening'], load: ['open', 'loading'], broken: ['wrong', 'error'],
        slow: ['speed', 'performance'], crash: ['error', 'start'], start: ['begin', 'first'], begin: ['start', 'first'], new: ['beginner', 'first', 'start'], picture: ['image', 'photo', 'logo'], photo: ['picture', 'image'],
        stamped: ['sim', 'stamp'], stamp: ['stamped'], channel: ['channels'], sticker: ['decal', 'logo'], decal: ['logo', 'sponsor', 'sticker'], mirror: ['symmetry', 'flip'], flip: ['mirror'], wrong: ['different', 'broken'],
        rgb: ['channel'], userid: ['user', 'id'], customer: ['user'], delete: ['remove'], remove: ['delete'], erase: ['eraser', 'delete'], fade: ['gradient'], gradient: ['fade'], dark: ['flat', 'black'] };
    function stem(w) {
        if (w.length <= 3 || /^[0-9#]/.test(w)) return w;
        if (/ies$/.test(w) && w.length > 4) return w.slice(0, -3) + 'y';
        if (/(ss|us|is)$/.test(w)) return w;
        if (/(xes|ches|shes|sses)$/.test(w)) w = w.slice(0, -2);
        else if (/s$/.test(w)) w = w.slice(0, -1);
        if (/ing$/.test(w) && w.length > 5) { w = w.slice(0, -3); if (/([^aeioulsz])\1$/.test(w)) w = w.slice(0, -1); }
        else if (/ed$/.test(w) && w.length > 4) { w = w.slice(0, -2); if (/([^aeioulsz])\1$/.test(w)) w = w.slice(0, -1); }
        if (/[^aeiou]e$/.test(w) && w.length > 4) w = w.slice(0, -1);          // HELPER_V2: "update" / "updating" / "updated" -> one stem
        return w;
    }
    function toks(s, keepStop) {
        var out = []; norm(s).split(' ').forEach(function (w) { if (!w) return; w = SYN[w] || w; if (!keepStop && STOP[w]) return; if (w.length < 2 && !/[0-9]/.test(w)) return; out.push(stem(w)); });
        return out;
    }

    // ------------------------------------------------------------------ the article index (BM25F over fields; one doc per article)
    var IX = null, _load = null;
    var FW = { t: 3, a: 2.4, s: 1.2, q: 1.4, b: 0.35 };          // field weights: title, aliases, summary, FAQ questions, body (what + how, first 90 words)
    function hidden(id, text) {
        var R = W.SpbEncyclopedia; try { if (R && R.hiddenId && R.hiddenId(id)) return true; if (R && R.hiddenText && R.hiddenText(text)) return true; } catch (e) {}
        return /(^|[._:])easy([._:]|$)/i.test(String(id || '')) || /\beasy[\s-]*mode\b|\bpaint[\s-]*by[\s-]*numbers\b|\bEASY\b/.test(String(text || ''));   // OWNER RULE: Easy mode is hidden
    }
    function scrub(s) { return String(s || '').split(/(?<=[.!?])\s+/).filter(function (x) { return !hidden('', x); }).join(' '); }
    function build(list, screens) {
        var docs = [], df = {}, vocab = {}, scr = {};
        (screens || []).forEach(function (x) { if (x && x.id && x.file && !hidden('', [x.title, x.caption, x.alt].join(' '))) scr[x.id] = x; });
        var byArt = {}; (screens || []).forEach(function (x) { (x.article_ids || []).forEach(function (a) { (byArt[a] = byArt[a] || []).push(x.id); }); });
        list.forEach(function (a) {
            if (!a || !a.id || hidden(a.id, [a.title, (a.aliases || []).join(' | ')].join(' | '))) return;
            var f = { t: toks(a.title), a: toks((a.aliases || []).join(' ')), s: toks(a.summary), q: toks((a.faq || []).map(function (x) { return x.q; }).join(' ')), b: toks([a.what].concat(a.how || []).join(' ')).slice(0, 90) };
            var tf = {}, len = 0; Object.keys(FW).forEach(function (k) { f[k].forEach(function (w) { tf[w] = (tf[w] || 0) + FW[k]; len += FW[k]; }); });
            Object.keys(tf).forEach(function (w) { df[w] = (df[w] || 0) + 1; vocab[w] = 1; });
            var help = /^help_/.test(a.id), gen = !!a.generated && !help;
            docs.push({ id: a.id, a: a, tf: tf, len: len, prior: help ? 1.0 : (gen ? 0.8 : 1.12), tn: toks(a.title).join(' '), al: (a.aliases || []).map(function (x) { return toks(x).join(' '); }).filter(function (x) { return x.indexOf(' ') > 0; }),
                faq: (a.faq || []).filter(function (x) { return x && x.q && !hidden('', x.q + ' ' + x.a); }).map(function (x) { return { q: x.q, a: x.a, k: toks(x.q) }; }),
                shots: (a.screens || []).concat(byArt[a.id] || []).filter(function (id, i, L) { return scr[id] && L.indexOf(id) === i; }) });
        });
        var N = docs.length, avg = docs.reduce(function (s, d) { return s + d.len; }, 0) / Math.max(1, N), idf = {};
        Object.keys(df).forEach(function (w) { idf[w] = Math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)); });
        // typo tolerance: symmetric delete-1 neighbourhood of every indexed word ("yelow" / "chnage" / "clearcot")
        var del = {}; Object.keys(vocab).forEach(function (w) { if (w.length < 4) return; for (var i = 0; i < w.length; i++) { var k = w.slice(0, i) + w.slice(i + 1); if (!del[k] || df[w] > df[del[k]]) del[k] = w; } });
        IX = { docs: docs, idf: idf, avg: avg, N: N, del: del, df: df, scr: scr, maxIdf: Math.log(1 + (N - 0.5) / 1.5) };
        return IX;
    }
    function fix(w) {
        if (!IX || IX.idf[w] != null || w.length < 4 || /[0-9]/.test(w)) return w;
        if (IX.del[w]) return IX.del[w];
        for (var i = 0; i < w.length; i++) { var k = w.slice(0, i) + w.slice(i + 1); if (IX.idf[k] != null) return k; if (IX.del[k]) return IX.del[k]; }
        return w;
    }
    // load(get): get(path under data/encyclopedia/) -> Promise<json|null>. Hand-written domains (from the v2 index groups) + the quick-answer pages + screens.json.
    function load(get) {
        if (_load && !get) return _load;
        get = get || function (p) { return (typeof fetch === 'function' ? fetch(BASE + p, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }) : Promise.resolve(null)).catch(function () { return null; }); };
        var D = W.SPB_ENCYCLOPEDIA, files = [];
        (((D && D.v2) || {}).groups || []).forEach(function (g) { if (g.k === 0 && files.indexOf(g.f) === -1) files.push(g.f); });
        if (!files.length) files = ['ai_copilot.json', 'cars.json', 'concepts.json', 'finishes.json', 'history.json', 'layers.json', 'patterns.json', 'playbook.json', 'preview_render.json', 'recipes.json', 'settings.json', 'shokk_drop.json', 'spec.json', 'spec_sculpt.json', 'support.json', 'tools.json', 'ui_shell.json', 'workflows.json', 'zones.json'];
        function arts(x) { return !x ? [] : (Array.isArray(x) ? x : (x.articles || [])); }
        _load = Promise.all(files.map(get).concat([get('help_pages.json').then(function (m) { return Promise.all(((m && m.parts) || []).map(function (p) { return get(p.file); })); }), get('_alias_overlay.json'), get('screens.json')])).then(function (rs) {
            var scr = rs.pop(), ovl = rs.pop(), help = rs.pop() || [], list = [];
            rs.forEach(function (x) { list = list.concat(arts(x)); }); help.forEach(function (x) { list = list.concat(arts(x)); });
            list = overlay(list, ovl);          // HELPER_V2 fix pass 4: search aliases over the articles (data/encyclopedia/_alias_overlay.json; the server search reads the same file)
            build(list, Array.isArray(scr) ? scr : ((scr && scr.screens) || []));
            return IX;
        });
        return _load;
    }
    function overlay(list, o) {
        var ov = o && o.overlay; if (!ov) return list;
        return list.map(function (a) { var x = a && a.id && ov[a.id]; if (!x) return a; var drop = (x.drop || []).map(function (w) { return String(w).toLowerCase(); }), al = (a.aliases || []).filter(function (w) { return drop.indexOf(String(w).toLowerCase()) === -1; }); (x.add || []).forEach(function (w) { if (al.map(function (y) { return String(y).toLowerCase(); }).indexOf(String(w).toLowerCase()) === -1) al.push(w); }); return Object.assign({}, a, { aliases: al }); });
    }
    function ready() { return !!IX; }

    // search(text) -> [{id, score, cov, doc}] best first; cov = share of the question's word weight the doc covers (unknown words count against it)
    var EXS = null, TITLE_PROB = /\b(slow|fails?|failed|won'?t|wont|not|missing|vanished|error|broken|problems?|trouble|wrong|stuck|crash\w*)\b/i;
    function search(text, limit) {
        if (!IX) return [];
        // ENC_SEARCH_LAB 2026-10-05 owner ("needs to be MUCH smarter"): ranked by the ONE shared ranker (js/spb-enc-search.js) that the reader
        // and the server (online grounding + MCP) also use; same articles, same {id, score, cov, doc} shape. The BM25F below is only the fallback.
        var SX = W.SpbEncSearch;
        if (SX && SX.build) {
            if (!IX.sx) { IX.sx = SX.build(IX.docs.map(function (d) { return d.a; })); IX.sxBy = {}; IX.docs.forEach(function (d) { IX.sxBy[d.id] = d; }); }
            return SX.search(IX.sx, text, { limit: limit || 6 }).filter(function (h) { return !!IX.sxBy[h.id]; }).map(function (h) { return { id: h.id, score: h.score, cov: h.cov, doc: IX.sxBy[h.id] }; });
        }
        var q = toks(text).map(fix), seen = {}, qs = [];
        q.forEach(function (w) { if (!seen[w]) { seen[w] = 1; qs.push(w); } });
        if (!EXS) { EXS = {}; Object.keys(EXPAND).forEach(function (k) { var sk = stem(SYN[k] || k); EXS[sk] = (EXS[sk] || []).concat(EXPAND[k]); }); }          // query words arrive stemmed ("missing" -> "miss")
        var alt = {}; qs.forEach(function (w) { alt[w] = (EXS[w] || EXPAND[w] || []).map(stem).filter(function (x) { return IX.idf[x] != null; }); });
        if (!qs.length) return [];
        var qset = {}; qs.forEach(function (w) { qset[w] = 1; alt[w].forEach(function (x) { qset[x] = 1; }); });
        var qn = q.join(' '), mass = 0; qs.forEach(function (w) { mass += IX.idf[w] != null ? IX.idf[w] : IX.maxIdf; });
        var k1 = 1.2, b = 0.55, out = [], qHow = /^\s*(how|hw|where)\b|^\s*(can|do) i\b/i.test(String(text)), qProb = Q_PROBLEM.test(String(text)) || /^\s*why\b/i.test(String(text));
        IX.docs.forEach(function (d) {
            var s = 0, got = 0;
            qs.forEach(function (w) {
                var f = d.tf[w], idf = IX.idf[w], wt = 1;
                if (!f) { for (var j = 0; j < alt[w].length; j++) if (d.tf[alt[w][j]]) { f = d.tf[alt[w][j]]; idf = Math.max(idf || 0, IX.idf[alt[w][j]]) ; wt = 0.75; break; } }          // a near-synonym ("missing" ~ "vanished") counts a bit less
                if (!f) return; s += wt * idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * d.len / IX.avg)); got += wt * (IX.idf[w] != null ? IX.idf[w] : idf);
            });
            if (!s) return;
            if (d.tn && (' ' + qn + ' ').indexOf(' ' + d.tn + ' ') !== -1 && d.tn.length > 3) s += 3;          // the whole title is in the question
            d.al.forEach(function (al) {
                if ((' ' + qn + ' ').indexOf(' ' + al + ' ') !== -1) { s += 2.5; return; }     // a multi-word alias is in the question
                if (al.split(' ').every(function (w) { return qset[w]; })) s += 1.5;          // ... or all its words, allowing near-synonyms ("numbers missing" ~ "numbers vanished")
            });
            // HELPER_V2 blind: question INTENT picks between sibling articles ("how do i add a zone" -> the how-to, not "What a zone is";
            // "how do i render" -> the Render button, not "Render slow"; a symptom -> the troubleshooting article)
            var tw = d.tn ? d.tn.split(' ') : [], ov = qs.filter(function (w) { return tw.indexOf(w) !== -1; }).length / qs.length, at = String(d.a.title || '');
            s += 2 * ov * ov;
            if (qHow && /^\s*(what|why)\b/i.test(at)) s *= 0.75;
            if (!qProb && TITLE_PROB.test(at)) s *= 0.7;
            if (qProb && (/^support\./.test(d.id) || /^help_support/.test(d.id))) s *= 1.15;
            out.push({ id: d.id, score: s * d.prior, cov: got / mass, doc: d });
        });
        out.sort(function (x, y) { return y.score - x.score; });
        return out.slice(0, limit || 6);
    }
    var FAQ_PROB = /\b(why|wont|won['’]t|doesnt|doesn['’]t|dont|don['’]t|cant|can['’]t|isnt|isn['’]t|not|fails?|failed|broken|stuck|greyed|grayed|wrong|missing|gone|error|too (much|many|little|dark|bright))\b/i;
    function bestFaq(d, text) {
        var q = toks(text).map(fix), best = null, bs = 0;
        var yn = /^\s*(is|isnt|are|arent|does|doesnt|do|dont|can|cant|could|should|will|would|did|has|have|am|must)\b/i.test(String(text || '').replace(/['’]/g, ''));
        d.faq.forEach(function (f) {
            var s = 0, m = 0; q.forEach(function (w) { var i = IX.idf[w] || 0; m += i; if (f.k.indexOf(w) !== -1) s += i; }); var r = m ? s / m : 0;
            // the other way too: most of the FAQ question must be in what was asked ("what is a spec map" must not get "Do I set the four numbers myself? No. ...")
            var s2 = 0, m2 = 0; f.k.forEach(function (w) { var i = IX.idf[w] || 0; m2 += i; if (q.indexOf(w) !== -1) s2 += i; }); var r2 = m2 ? s2 / m2 : 0;
            if (/^\s*(yes|no)\b/i.test(f.a) && !yn) return;          // a yes/no answer only answers a yes/no question
            if (FAQ_PROB.test(f.q) && !FAQ_PROB.test(text)) return;
            if (/^\s*(what|whats|what's)\b/i.test(String(text)) && !/^\s*(what|which)\b/i.test(f.q)) return;          // "what is astra" gets the article's own summary, not a how-to FAQ          // "why won't merge work?" does not answer "how do i merge layers"
            if (r2 < 0.5) return;
            if (r > bs) { bs = r; best = f; }
        });
        return bs >= 0.6 ? best : null;
    }
    function shotOf(d) { var id = (d.shots || [])[0]; var x = id && IX.scr[id]; return x ? { id: x.id, src: /^(\/|https?:|data:)/.test(x.file) ? x.file : BASE + x.file, caption: x.caption || x.title || '' } : null; }
    // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- "Do it" buttons showed raw ids ("Show me rpTabLayers", "pro render copy tp desc", "candy / candy"):
    // a control takes the human label the UI audit wrote into the article (controls[].inv -> label, the same label the reader shows), a finish / pattern / spec its catalogue name
    function catName(kind, id) {
        var lists = [];          // the page's own catalogue arrays (global consts of paint-booth-0-finish-data.js; absent in Node)
        try { if (kind === 'finish') lists = [[typeof BASES !== 'undefined' ? BASES : null, 'base::'], [typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : null, 'monolithic::']]; else if (kind === 'pattern') lists = [[typeof PATTERNS !== 'undefined' ? PATTERNS : null, '']]; else if (kind === 'spec') lists = [[typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : null, '']]; } catch (e) { lists = []; }
        for (var i = 0; i < lists.length; i++) { var L = lists[i][0]; if (Array.isArray(L)) for (var j = 0; j < L.length; j++) { var x = L[j]; if (x && x.name && (lists[i][1] + x.id === id || x.id === id)) return String(x.name); } }
        return '';
    }
    function humanId(id) { return String(id).replace(/^.*::/, '').replace(/^(?:btn|rpTab|spb|vtMode|pro\.|zone\.)/, '').replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^f_/, '').replace(/[_.]+/g, ' ').replace(/\b(?:btn|checkbox|cb)\b/gi, '').replace(/\s+/g, ' ').trim().toLowerCase(); }
    function ctrlName(a, id) {
        var c = (a.controls || []).filter(function (c1) { return c1 && c1.inv === id && c1.label; })[0]; if (c) return String(c.label);
        try { var el = typeof document !== 'undefined' && document && document.getElementById ? document.getElementById(id) : null; var tx = el ? String(el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').replace(/\s+/g, ' ').trim() : ''; if (tx && tx.length <= 40) return tx; } catch (e) {}
        return 'the ' + humanId(id) + ' control';
    }
    function actionsOf(a) {
        var L = (a.actions || []).filter(function (x) { return x && x.do && x.id && !hidden(x.id, x.label); }).slice(0, 6).map(function (x) {
            var lab = x.label || ''; if (!lab) lab = x.do === 'control' ? ctrlName(a, x.id) : (catName(x.do, String(x.id)) || humanId(x.id));
            return { do: x.do, id: x.id, label: lab.charAt(0).toUpperCase() + lab.slice(1) };
        }), n = {};
        L.forEach(function (x) { var k = x.label.toLowerCase(); n[k] = (n[k] || 0) + 1; });
        L.forEach(function (x) { if (n[x.label.toLowerCase()] > 1) x.label += /::f_/.test(String(x.id)) ? ' (Foundation)' : (x.do === 'spec' ? ' (spec overlay)' : (x.do === 'pattern' ? ' (pattern)' : '')); });          // two "Candy" buttons: the Foundation one says so
        return L;
    }
    // the answer card's data
    function answerOf(hit, text) {
        var d = hit.doc, a = d.a, fq = bestFaq(d, text), help = /^help_/.test(a.id);
        var how = (a.how || []).filter(function (x) { return typeof x === 'string' && !hidden('', x); }).slice(0, help ? 4 : 3);
        var sum = scrub(a.summary || ''), txt = fq ? scrub(fq.a) : sum;
        if (!fq && help && how.length > 1 && how[0] && sum.indexOf(how[0].slice(0, 20)) === 0) txt = how.map(function (x, i) { return (i + 1) + '. ' + x.replace(/^\d+\.\s*/, ''); }).join(' ');
        if (String(txt || '').length < 20) txt = how.length ? how.map(function (x, i) { return (i + 1) + '. ' + String(x).replace(/^\d+\.\s*/, ''); }).join(' ') : scrub(String(a.what || '').split(/(?<=[.!?])\s+/).slice(0, 2).join(' '));
        return { id: a.id, title: a.title, level: a.level || null, text: txt, faq: fq ? fq.q : null, summary: sum, how: fq ? [] : how, shot: shotOf(d), actions: actionsOf(a), related: (a.related || []).slice(0, 4) };
    }

    // ------------------------------------------------------------------ what kind of sentence is it
    // HELPER FIX PASS 7 2026-10-05: "nah go back to how it was" / "actually go back" = undo (fillers before the undo words)
    var UNDO_RE = /^\s*(?:(?:nah|nope|no|yeah|yes|ok|okay|just|wait|please|pls|um+|uh+|hmm+|actually|ugh|sorry|oops)[\s,.!]+)*(undo|undo that|undo it|go back|back to how it was|back to (?:the )?(?:way|how) it was|put it back how it was|revert|take (that|it) back|put it back|start over|start again|reset everything)\b/i;
    var EDIT_START = /^\s*(please\s+|pls\s+)?(can|could|would|will) (you|u)\s+(please\s+)?(make|turn|change|paint|swap|give|add|put|set|recolou?r|switch|use|apply|do|remove|colou?r)\b|^\s*(please\s+|pls\s+)?(make|turn|change|paint|swap|give|add|put|set|recolou?r|switch|apply|remove|colou?r)\b/i;
    var Q_START = /^\s*(is|are|was|were|what|whats|what's|wat|wht|whta|how|hw|howd|why|whys|where|wheres|when|which|who|whos|is there|are there|is it|is this|is that|is my|are my|do i|does this|does it|do you|does|did|can i|can u|could i|should i|would i|am i|will it|explain|define|tell me (about|what|how|why|where)|help me (understand|with)|difference|diff|meaning of|whats the|im new|i'?m new|new here|where do i)\b/i;
    var Q_PROBLEM = /\b(doesn'?t|dont|don'?t|won'?t|wont|isn'?t|isnt|aren'?t|can'?t|cant|not (show|showing|work|working|load|loading|sav|open|opening|chang|changing|there|right|appear)\w*|missing|vanish\w*|disappear\w*|\blost\b|broken|stuck|slow|crash\w*|error|frozen|freez\w*|keeps|blank|black in|different in|look\w* different|wrong|blobby|smeared|tiny on|huge on|it says|got painted|nothing happen\w*|(?:does|do|did) nothing|not using|isnt using|isn'?t using|too (?:shiny|glossy|dull|matte|dark|bright|flat|big|small|blurry)|cant (?:find|see)|can'?t (?:find|see))\b/i;
    var LOOK_RE = /\b(look(s|ing)? like|look (mean|cool|clean|classy|aggressive|expensive|fast|evil|sick|tough|sinister|elegant|futuristic|retro)|something (like|with|aggressive|clean|classy|cool|mean|wild|crazy|different|fast|evil)|vibe|aesthetic|themed?)\b|^\s*something\b|^\s*i want something\b|^\s*make it (look|feel) \w+|^\s*make it (pop|sparkle|shine|glow|stand out)\s*$/i;
    // HELPER_V2 blind: maths, sim hardware and which iRacing content to buy are off-topic (they used to get the nearest app article)
    var OFFTOPIC_RE = /^\s*(?:what(?:'?s| is)|calculate|how much is)\s+[\d\s.]+(?:\+|-|\*|x|times|plus|minus|divided by)\s*[\d.]+\s*\??\s*$|\b(?:force feedback|ffb|pedals?|sim rig|steering wheel|wheel ?base|load cell|vr headset|frame ?rate|fps|graphics settings|refresh rate)\b|\b(?:what|which) (?:cars?|series|tracks?) (?:should|do|would|could) (?:i|you) (?:buy|get|race|drive|pick)\b|\bsafety rating\b|\birating\b/i;
    var CHAT_RE = /\b(poem|joke|weather|news|translate|email|essay|story|song|recipe for|code|python|javascript|horsepower|setup for|lap time|get faster|driving|sim rig|wheel base|meaning of life|favou?rite|who are you|your name|2\s*\+\s*2|sandwich|rain at|forecast|stock|bitcoin)\b/i;
    function kind(t) {
        if (UNDO_RE.test(t)) return 'undo';
        if ((CHAT_RE.test(t) && !EDIT_START.test(t)) || OFFTOPIC_RE.test(t)) return 'chat';
        if (EDIT_START.test(t)) return 'edit';
        if (Q_START.test(t) || /\?\s*$/.test(t) || /\b(vs\.?|versus|which is better|or should i|compared to|difference)\b/i.test(t)) return 'question';
        if (/\blooks? (too )?(dark|flat|wrong|weird|bad|off|different|blurry|pixelated|washed out|dull|grainy|smeared|blobby|tiny|huge)\b/i.test(t)) return 'question';
        var tooQ = /\btoo (\w+)\b/i.exec(t), tooReq = !!(tooQ && TOO_FIX[tooQ[1].toLowerCase()] && /\b(?:can|could|would|will) (?:you|u)\b[^?]{0,25}\b(?:fix|sort|help)\b/i.test(t));          // "the roof is too shiny, can you fix that" asks for a change
        if (Q_PROBLEM.test(t) && !EDIT_START.test(t) && !tooReq && !/\b(?:can|could|would|will) (?:you|u)\b[^?]{0,20}\b(?:make|tone|turn|change|darken|lighten|brighten|dull|calm)\b/i.test(t)) return 'question';          // "the yellow is too bright, can u tone it down" asks for a change          // HELPER_V2 blind: a symptom anywhere ("number missing", "car is too shiny in sim") is a question, never build steps
        if (/^\s*(the|my) [a-z ]{2,30} (should|needs to|must) be\b/i.test(t)) return 'edit';
        return 'other';
    }

    // a catalogue search for a look the parser cannot read ("like a rattlesnake", "something aggressive") -> builder choices (real ids, thumbnails)
    var LOOK_WORDS = /\b(make|it|look|looks|looking|like|a|an|the|some|something|with|give|car|whole|i|want|kind|of|sort|type|vibe|aesthetic|theme|themed|feel|really|more|very|please|and|style|my|paint|livery)\b/g;
    function lookQuery(t) { return norm(t).replace(LOOK_WORDS, ' ').replace(/\s+/g, ' ').trim(); }
    function catalogue(q, limit) {
        var R = W.SpbProRank, C = W.SpbAICards, out = [];
        if (R && R.search && C && C.ready && C.ready()) { try { (R.search(q, { limit: limit || 12 }) || []).forEach(function (r) { var k = String(r.key || ''); if (/^(base|monolithic)::/.test(k)) out.push({ kind: 'cat', key: k, id: k, label: r.name || k }); else if (/^pattern::/.test(k)) out.push({ kind: 'tex', mode: 'pattern', id: k.slice(9), label: r.name, name: r.name }); else if (/^spec::/.test(k)) out.push({ kind: 'tex', mode: 'spec', id: k.slice(6), label: r.name, name: r.name }); }); } catch (e) {} }
        if (out.length < 3 && B() && B().searchChoices) (B().searchChoices(q, null, limit || 12) || []).forEach(function (c) { var x = c.kind === 'finish' ? { kind: 'cat', key: c.id, id: c.id, label: c.label } : (c.kind === 'pattern' ? { kind: 'tex', mode: 'pattern', id: c.id, label: c.label, name: c.label } : { kind: 'tex', mode: 'spec', id: c.id, label: c.label, name: c.label }); if (!out.some(function (o) { return o.id === x.id; })) out.push(x); });
        return out;
    }
    function lookStep(t, env) {
        // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- "make the hood look mean" searched “hood mean” and put it on THE WHOLE CAR: a named part is the target, not a search word
        var pm = /\b(front bumper|rear bumper|left side|right side|bumpers|sides|doors|hood|roof|trunk|spoiler|wing)\b/i.exec(String(t || '')), tgs = pm ? onlyTarget(pm[1].toLowerCase()) : null;
        var Bb = B(), q = lookQuery(pm ? String(t).replace(pm[0], ' ') : t); if (!Bb || !q) return null;
        var found = catalogue(q, 12); if (found.length < 3) return null;
        var sts = (tgs || [null]).map(function (x) { var st = Bb.newStep({ what: x ? { k: 'part', part: x.part, tg: x } : { k: 'body' }, act: 'finish', search: q }); st.found = found; st.foundFor = q; return st; });
        sts[0].note = 'I searched the catalogue for “' + q + '”: pick a look below (or search again). It goes on ' + (tgs ? 'the ' + pm[1].toLowerCase() : 'the body paint') + '; your numbers and sponsors keep theirs.';
        return sts;
    }

    // ------------------------------------------------------------------ the router
    function steps(text, env) { var Bb = B(); if (!Bb) return null; var r = Bb.fromText(text, env); if (r.steps.length) Bb.check(r.steps, env); return r; }
    function stepsResult(st, extra) {
        st.forEach(function (s) {          // HELPER_V2 fix pass 4 2026-10-04 owner: keep improving the Offline Helper -- a look word the catalogue NAMES ("splatter") beats a loose encyclopedia term's first pick (Chain Link): the named items to pick from
            if (!s || !s.prefilled || !s.search || !s.termChoices) return;
            var wk = String(s.search).toLowerCase().split(/\s+/).filter(function (x) { return x.length > 3 && !/^(?:paint|look|style|finish|scheme|effect)$/.test(x); }).pop() || '', lab = String((s.tex && (s.tex.label || s.tex.name)) || (s.finish && (s.finish.label || s.finish.name)) || '').toLowerCase();
            if (!wk || lab.indexOf(wk) !== -1) return;
            var fd = catalogue(wk, 12).filter(function (x) { return String(x.label || '').toLowerCase().indexOf(wk) !== -1; }); if (fd.length < 2) return;
            s.tex = null; s.finish = null; s.act = 'finish'; s.found = fd; s.foundFor = wk; s.prefilled = false; s.termChoices = null; s.note = 'I searched the catalogue for “' + wk + '”: pick one below (nothing changes until ▶ Run).';
        });
        st.forEach(function (s) {          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: an open "which look" step shows the catalogue's own picks for its word ("tiger stripe orange" -> ② tiger stripe tiles, not an empty search)
            if (!s || s.act !== 'finish' || !s.search || s.finish || s.tex || (s.found && s.found.length) || (s.termChoices && s.termChoices.length)) return;
            var fq = String(s.search).toLowerCase().replace(/\btiger pattern\b/, 'tiger stripe').replace(/\b(?:pattern|look|finish|style|paint)\b/g, ' ').replace(/\s+/g, ' ').trim(); if (!fq) return;
            var fd2 = catalogue(fq, 12); if (fd2.length >= 2) { s.found = fd2; s.foundFor = fq; }
        });
        var ask = st.filter(function (s) { return s.ask; })[0], Bb = B(), o = { steps: st };
        if (ask) { o.cls = 'ASK'; o.ask = { text: ask.ask, chips: (ask.chips || []).map(function (c) { return typeof c === 'string' ? c : c.label; }).filter(function (c) { return c && c !== 'what' && c !== 'box'; }) }; if (o.ask.chips.length < 2) o.cls = st.some(Bb.stepOpen) ? 'PREFILL' : 'DO'; }
        else o.cls = st.some(Bb.stepOpen) ? 'PREFILL' : 'DO';
        if (extra) for (var k in extra) o[k] = extra[k];
        return o;
    }
    function wordsOf(t) { return norm(t).split(' ').filter(Boolean).length; }
    function confident(h, k) { return !!h && h.cov >= (k === 'question' ? 0.5 : 0.62) && h.score >= (k === 'question' ? 3.2 : 4.5); }
    function answered(hits, text) { var A = answerOf(hits[0], text); return { cls: 'ANSWER', hits: hits.slice(0, 3).map(function (h) { return { id: h.id, title: h.doc.a.title, score: Math.round(h.score * 10) / 10 }; }), answer: A }; }
    function online(text, why) { return { cls: 'ONLINE', why: why || 'chat', text: text }; }
    // ------------------------------------------------------------------ HELPER_V2 blind-eval PATTERNS (2026-10-04: an independent blind eval scored 76%; fix the patterns, not the sentences)
    // P4 honest decline: custom art the catalogue cannot make (faces, pets, photos, new logos, exact replicas, a whole livery from a brief) -> ONLINE, never build steps
    var ART_NOUN = '(?:face|faces|portrait|selfie|caricature|cartoon|anime|mascot|character|dog|dogs|cat|cats|puppy|kitten|horse|eagle|lion|tiger|wolf|bear|shark|bull|person|girl|guy|man|woman|wife|girlfriend|husband|boyfriend|kid|kids|son|daughter|family|baby|pet)';
    var DECLINE = [
        [/\b(?:draw|sketch|illustrate|airbrush|paint|put|add|place|generate|create|render|make)\b[^.]{0,20}\b(?:a|an|the|my) (?:\w+ ){0,2}(?:\w+) (?:riding|holding|eating|driving|flying|jumping|sitting on|standing on|fighting|chasing|breathing|playing|wearing|surfing)\b/i, 'custom-art'],          // HELPER_V2 fix pass 4: a scene (something doing something) is a picture
        [/\b(?:draw|sketch|illustrate|airbrush|paint|put|add|place|generate|create|render)\b[^.]{0,25}\b(?:a|an|my|the) (?:\w+ ){0,2}(?:unicorn|rocket ?ship|rocket|robot|alien|astronaut|spaceship|monster|knight|wizard|superhero|clown|mermaid|pirate|ninja|samurai|cowboy|zombie|vampire)s?\b(?!\s*(?:scales?|skin|print|pattern|camo|texture))/i, 'custom-art'],
        [new RegExp('\\b(?:draw|sketch|illustrate|airbrush|paint|put|add|place|stick|do|make)\\b[^.]{0,25}\\b(?:a|an|my|our|his|her|their|the) (?:\\w+ ){0,2}' + ART_NOUN + '\\b(?!\\s*(?:scales?|skin|print|pattern|camo|fur|spots?|stripes?|texture|tooth))', 'i'), 'custom-art'],
        [/\b(?:realistic|photo ?realistic|photoreal|hyper ?real)\b|\b(?:photo|photograph|picture|image|portrait|drawing|painting) of (?:a|an|my|the|our)\b/i, 'custom-art'],
        [/\b(?:make|design|create|draw|generate|come up with|build)\b(?: me| us)? (?:a|an|my|our|new|custom|the team'?s?)\b[^.]{0,20}\b(?:logo|emblem|crest|badge|monogram)\b/i, 'custom-logo'],
        [/\bmy (?:name|initials|nickname|signature)\b|\b(?:name|text|words|lettering|signature|quote) (?:in|written in) (?:script|cursive|graffiti|a font|gothic)\b/i, 'custom-text'],
        [/\b(?:exact(?:ly)?|replica|recreate|re-create|carbon copy|identical to)\b[^.]{0,40}\b(?:livery|car|scheme|paint|winner|champion|design)\b|\b(?:livery|car|scheme|paint|winner|design)\b[^.]{0,40}\bexact(?:ly)?\b|\bcopy (?:the |a |that )?(?:[a-z]+ ){0,2}(?:livery|scheme|paint ?job)\b|\b(?:19[4-9]\d|20[0-2]\d)\b[^.]{0,25}\b(?:winner|winning|livery|champion|daytona|indy|le mans|talladega)\b/i, 'replica'],
        [/\b(?:design|create|draw|build|come up with|make)\b(?: me| us)?(?: a| an| my)? (?:full|whole|complete|entire|custom|original|brand new|unique)\b[^.]{0,12}\b(?:livery|paint ?scheme|scheme|paint job|wrap|design)\b|\bfrom scratch\b|\b(?:[a-z-]+ ){1,3}(?:style|themed|inspired) (?:[a-z-]+ ){0,3}(?:livery|scheme|paint ?job|wrap)\b/i, 'custom-design']
    ];
    function decline(t) { var lk = /\blooks? (?:like|as if)\b|\b(?:themed?|vibe|inspired|style)\b/i.test(t); for (var i = 0; i < DECLINE.length; i++) if (!(lk && DECLINE[i][1] === 'custom-art') && DECLINE[i][0].test(t)) return DECLINE[i][1]; return null; }          // "look like a shark" = a look search; "look like the 1969 winner exactly" = a replica

    // P3 a small CURATED slang table: phrase -> what the app can do (never a free-text finish search)
    var SLANG = [
        [/\b(?:murdered|blacked|blackened) out\b|\ball black everything\b|\bstealth (?:look|mode|black|paint)\b/i, 'matte black'],
        [/\bchromed out\b|\bfull chrome\b|\bchrome everything\b|\ball chrome\b/i, 'chrome'],
        [/\bwhited out\b|\ball white everything\b/i, 'white'],
        [/\bflat black\b/i, 'matte black'], [/\bflat white\b/i, 'matte white'], [/\bflat grey\b|\bflat gray\b/i, 'matte grey'], [/\bprimer grey\b|\bprimer gray\b/i, 'matte grey']
    ];
    function slang(t) {
        var out = t, hit = false;
        SLANG.forEach(function (s) { if (s[0].test(out)) { out = out.replace(s[0], s[1]); hit = true; } });
        if (!hit) return null;
        if (!/\b(make|paint|turn|change|go|give|do|want|recolou?r|set)\b/i.test(out)) out = 'make the whole car ' + out.replace(/^\s*(?:go|going|get|i want|give me|it|the car|car|my car)\s+/i, '');
        return out;
    }

    // P0 negation is a CONSTRAINT, never a target: "don't touch / leave / keep the numbers" is removed from the request and remembered
    var PROT_NOUN = '(?:numbers?|sponsors?|logos?|decals?|stickers?|lettering|stripes?|pinstripes?|hood|roof|trunk|spoiler|wing|bumpers?|front bumper|rear bumper|(?:left|right) side|sides|doors?|wheels?|white|black|yellow|red|blue|green|orange|purple|pink|gr[ae]y|silver|gold|colou?rs?|paint ?job|design|livery|rest)';
    var PROT_RE = new RegExp('\\b(?:(?:do not|don\'?t|dont|never|without|no)\\s+(?:touch|touching|change|changing|paint|painting|cover|covering|recolou?r\\w*|mess(?:ing)? with|alter|modify|move|affect)|(?:keep(?:ing)?|leave|leaving|save|protect|preserve))\\s+(?:the |my |any |all (?:of )?(?:the |my )?|our |those )?((?:[a-z]+ ){0,2}?' + PROT_NOUN + '(?:\\s*(?:,|and|&|or)\\s*(?:the |my |all (?:the )?)?' + PROT_NOUN + ')*)\\b(?:\\s+(?:alone|(?:exactly |just )?(?:as|like) (?:is|they are|it is|they were|it was)|untouched|the same|intact|unchanged|how (?:it|they) (?:is|are)|where (?:it|they) (?:is|are)))?', 'gi');
    function protect(t) {
        var words = [], rest = String(t).replace(PROT_RE, function (m, w) { String(w).toLowerCase().split(/\s*(?:,|\band\b|&|\bor\b)\s*/).forEach(function (x) { x = x.replace(/^(?:the|my|all(?: the)?)\s+/, '').trim(); if (x && words.indexOf(x) === -1) words.push(x); }); return ' , '; });
        rest = rest.replace(/\s*,\s*(?:,\s*)+/g, ', ').replace(/^\s*[,.;]*\s*(?:(?:but|and|then|just|only|so|please)\b)?\s*[,.;]*\s*/i, '').replace(/\s*[,.;]*\s*(?:\b(?:but|and|then|please))?\s*[,.;]*\s*$/i, '').trim();
        return { words: words, rest: rest };
    }
    function protectedHit(w, words) {
        if (!w || !words.length) return false;
        var has = function (re) { return words.some(function (x) { return re.test(x); }); };
        if (w.k === 'numbers') return has(/number/);
        if (w.k === 'sponsors') return has(/sponsor|logo|decal|sticker|lettering/);
        if (w.k === 'layer') return has(/number|sponsor|logo|decal|sticker|lettering/) && /number|sponsor|logo|decal|sticker|letter/i.test(String(w.word || (w.layers || []).join(' ')));
        if (w.k === 'part') return words.some(function (x) { return String(w.part || '').indexOf(x.replace(/s$/, '')) !== -1 || (/bumpers/.test(x) && /bumper/.test(w.part)) || (/sides/.test(x) && /side/.test(w.part)); });
        if (w.k === 'colour' && w.tg) return words.indexOf(String(w.tg.word || '').toLowerCase()) !== -1;
        if (w.k === 'tg' && w.tg && w.tg.kind === 'accents') return has(/stripe/);
        return false;
    }
    function dropProtected(steps, words) {
        var gone = {}, out = [];
        steps.forEach(function (s) { var w = s.what; if ((w && w.k === 'step' && gone[w.ref]) || protectedHit(w, words)) { gone[s.id] = 1; return; } out.push(s); });
        return { steps: out, dropped: Object.keys(gone).length };
    }

    // P5 removal of numbers / sponsors is confirmed first; a vague edit ("change the color", "fix it") or a bare adjustment ("a little less saturated") asks WHICH
    var REMOVE_RE = /^\s*(?:please\s+|can you\s+|could you\s+)?(?:get rid of|remove|delete|hide|take off|take away|lose|erase)\s+(?:the |my |all (?:the |of the )?|those |these )?(?:car |sim )?(numbers?|sponsors?|logos?|decals?|stickers?|lettering)\b/i;
    var VAGUE_RE = /^\s*(?:please\s+|can you\s+|could you\s+|just\s+)?(?:change|fix|edit|update|improve|redo|tweak|adjust|modify|do something (?:with|to)|make|paint|spray|colou?r|recolou?r)\s+(?:it|this|that|the colou?rs?|the paint|the car|my car|my paint|the design|something|stuff|it better|it nicer|it look better|it cooler|it better looking|it different)\s*(?:please|pls|for me)?\s*[.!?]*$|^\s*i (?:dont|don'?t|do not) (?:like|love) (?:it|this|that|the (?:colou?rs?|paint|design|look|car))\b|^\s*(?:i'?m |i am )?not (?:feeling|loving|liking|into) (?:it|this|that)\b/i;
    var ADJ_RE = /\b((?:a (?:bit|little|touch|tad)|slightly|way|much|lot)?\s*(?:less|more)\s+(?:saturated|vivid|bright|dark|light|muted|warm|cool|intense|colou?rful)|(?:(?:a (?:bit|little|touch|tad)|slightly|way|much)\s+)?(?:brighter|darker|lighter|duller|warmer|cooler|deeper|paler|richer))\b/i;
    function palNames(env, n) { var out = []; try { (env && env.palette || []).slice().sort(function (a, b) { return (b.share || 0) - (a.share || 0); }).forEach(function (p) { var nm = p.name || (Ed() && Ed().familyOf ? Ed().familyOf(p.hex) : '') || ''; if (nm && out.indexOf(nm) === -1) out.push(nm); }); } catch (e) {} return out.slice(0, n || 3); }
    function asked(why, text, chips) { return { cls: 'ASK', why: why, ask: { text: text, chips: chips }, steps: [] }; }

    // shared clause helpers (phase 2)
    var WHOLE_RE = /\b(?:it all|all of it|(?:make|paint|turn|do|colou?r|spray) it|everything(?: else)?|the rest(?: of (?:it|the car))?|whole|entire|the car|my car|the body|body|all over|whole thing|car)\b/i;
    var NEG_START = /^\s*(?:please\s+)?(?:do not|don'?t|dont|never|keep|leave|save|protect)\b/i;
    var FADED_LOOK_RE = /\b(?:faded|fading|worn|weathered|aged|distressed|sun[- ]?(?:faded|bleached)|washed[- ]?out)\s+(?:carbon(?: ?fib(?:er|re))?|forged carbon|kevlar|chrome|camo(?:uflage)?|denim|leather|metal|steel|gold|copper|bronze|brass|rust|patina|paint|flames?|vintage|retro|race ?car|livery)\b/i;          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper
    var FADE_RE = /\b(?:fade|fades|faded|fading|gradient|ombre|blend(?:ed)? from|transition from)\b|\bblend(?:s|ed|ing)?\b[^.,;]{0,30}\b(?:into|from)\b/i;
    var ELEMENT_RE = /\b(?:stripes?|pinstripes?|stripe down|bands?|borders?|outlines?|checkers?|checkered|flags?|flames?|number plate|fades?|fading|gradients?|ombre|blend(?:ed)? from)\b/i;
    var COMMON = {}; ('racing race racer little bit nothing something anything team missing keep else rest fix make better nice cool good great new old big small more less color colour paint car please want need force ' +
        'feedback weak strong wheel fast slow simple layer layers wow original another lol thing stuff look looks kind sort type way lot really very just like maybe also mak mke pls plz the a an and or but my our it all over some both other one match base kinda sorta ' +
        'bring back put restore return again').split(' ').forEach(function (w) { if (w) COMMON[w] = 1; });          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "bring the yellow back on the roof" left "bring back" as a look to search
    function commonOnly(x) { return !!x && norm(x).split(' ').every(function (w) { return !w || COMMON[w]; }); }
    var COLOUR_WORDS = 'red|orange|yellow|gold|lime|green|teal|cyan|blue|navy|purple|violet|pink|magenta|white|silver|gr[ae]y|black|brown|maroon|bronze|copper|cream|tan|beige';
    function colourObj(name) { var E = Ed(), c = null; try { var pc = E.parseClause(E.fixText('make it ' + name)); c = pc && pc.colours && pc.colours[0]; } catch (e) { c = null; } return c && c.hex ? { name: c.name || name, hex: c.hex, at: 0, qual: c.qual || null, exact: false } : null; }          // a colour word -> the edit brain's own colour table
    function splitAll(t) {
        var E = Ed(), out = [];
        String(t).replace(/\s+with\s+(?=(?:a |an |the |some )?(?:[a-z]+ ){0,2}(?:hood|roof|trunk|spoiler|wing|bumpers?|sides?|nose|tail)\b)/gi, ', ').split(/\s*(?:[,;]|\.\s+|\bthen\b|\balso\b|\bplus\b)\s*/i).forEach(function (p) {
            p = p.replace(/^\s*(?:and|but|then|also|plus|with|&)\s+/i, '').trim(); if (!p) return;
            var cs = []; try { cs = E.splitClauses(E.fixText(p)); } catch (e) { cs = []; }
            (cs && cs.length > 1 ? cs : [p]).forEach(function (c) { c = String(c).trim(); if (c) out.push(c); });
        });
        return out;
    }
    var FILLER_RE = /^\s*(?:nothing (?:fancy|crazy|special|wild|too \w+)|keep it simple|simple|thanks?(?: a lot| so much)?|thank you|please|pls|ok(?:ay)?|cheers|lol|haha|oh|so|yeah|yes|cool|great|awesome|nice|(?:they|it|that|those|these)(?: are|'re| is|'s) (?:fine|good|ok|okay|great|perfect|alright)|(?:can you |could you )?take the whole thing|(?:my|the) car is (?:the |a |number |#)?\w+|another \w+(?: \w+)? (?:car|one|livery|paint ?job)|wow(?: so)? \w+)\s*[.!]*$/i;
    function targetKey(o) { var t = o.target || {}; return t.kind + ':' + (t.part || t.word || ''); }

    // P2/P3 a complaint word is the PROBLEM, never the look: "the yellow is too bright, can u tone it down" = make the yellow darker (not a finish called "bright" / "tone")
    var TOO_FIX = { bright: 'darker', light: 'darker', pale: 'darker', vivid: 'less saturated', saturated: 'less saturated', loud: 'less saturated', neon: 'less saturated', dark: 'lighter', shiny: 'satin', glossy: 'satin', dull: 'glossy', flat: 'glossy', matte: 'glossy', plain: 'pop', boring: 'pop' };
    function tooFix(t) {
        var m = /^\s*(?:the |my |this )?([a-z][a-z ]{1,30}?)\s+(?:is|looks|seems|are|feels)\s+(?:way |a bit |a little |kind of |kinda |just |really )?too (\w+)\b[\s,.;!]*(.*)$/i.exec(t), fx = m && TOO_FIX[m[2].toLowerCase()];
        if (!fx) return null;
        var subj = m[1].trim().replace(/^(?:paint|colou?r)$/i, 'car'), rest = m[3].replace(/^(?:so |and |but |pls |please )*(?:can|could|would|will) (?:you|u) (?:please |pls )?/i, '').replace(/[?.!]+$/, '').trim();
        if (!rest || /^(?:tone|calm|bring|turn|fix|change|sort|dial|knock|help)\b/i.test(rest)) return 'make the ' + subj + ' ' + fx;
        return rest.replace(/\bit\b/i, 'the ' + subj);
    }

    // ================================================================== HELPER_V2 FRAME PARSER (phase 3, 2026-10-04)
    // HELPER_V2 2026-10-04 owner: keep improving the Offline Helper. Blind round 2 (a fresh tester, 150 new inputs) scored 78% acceptable / 43% strict with 2 HARMFUL
    // ("reflective silver like a mirror but only the body not the numbers" painted the numbers; "hood matt black wiht a gold pinstripe" recoloured everything gold):
    // the round-1 sentence patterns did not generalise. Every message is now read STRUCTURALLY before a step is built:
    //   clean -> custom art / off-topic -> follow-ups (bound to the last change, or a question back when there is none) -> SCOPE (only / except / keep / colours kept,
    //   applied to EVERY clause) -> typed ENTITIES (numbers, sponsors / logos / brand names, text, pictures) that never reach the finish search -> CLAUSE FRAMES
    //   {targets, value} with "X with a Y stripe" = base X + a stripe to ADD -> the better of the frames and the edit brain's whole-sentence plan -> the builder
    //   -> the NEVER-TOUCH filter (numbers / sponsors / tape leave every step's scope unless that clause names them as its target).
    var TYPO = { teh: 'the', hte: 'the', wiht: 'with', wtih: 'with', wit: 'with', matt: 'matte', metalic: 'metallic', metalik: 'metallic', metallik: 'metallic', mettalic: 'metallic', fibr: 'fiber', fibre: 'fiber', u: 'you', ur: 'your', plz: 'please', pls: 'please', thx: 'thanks', kepp: 'keep', keeep: 'keep', colur: 'colour', colr: 'color', blak: 'black', blck: 'black', wite: 'white', silvr: 'silver', chrom: 'chrome', shinny: 'shiny', bumber: 'bumper', spoilor: 'spoiler', trunck: 'trunk', gimme: 'give me', wanna: 'want to', gonna: 'going to', n: 'and', abit: 'a bit', alittle: 'a little', pinstipe: 'pinstripe', purpel: 'purple', yelow: 'yellow', grean: 'green', oragne: 'orange' };
    function clean(t) {
        var s = String(t || '').replace(/[☀-➿️‍]|[\uD83C-\uDBFF][\uDC00-\uDFFF]/g, ' ');
        s = s.replace(/[A-Za-z]+/g, function (w) { var x = TYPO[w.toLowerCase()]; return x == null ? w : x; });
        s = s.replace(/\bgive me sum\b/gi, 'give me some').replace(/\b(?:umm*|uhh*|hmm+|erm)\b[,.]?/gi, ' ');
        s = s.replace(/^\s*(?:(?:omg|ok|okay|so|yo|hey|alright|lol|lmao|bro|dude)\b[\s,.!:]*)+/i, '');
        // whole filler / sarcasm sentences ("wow so original, another red car.") carry no edit: drop them when something else is left
        var sents = s.split(/(?<=[.!?])\s+/), keep = sents.filter(function (x) { return !x.split(/,\s*/).every(function (y) { return FILLER_RE.test(y.replace(/[.!?]+$/, '')); }); });
        if (sents.length > 1 && keep.length && keep.length < sents.length) s = keep.join(' ');
        return s.replace(/\s+/g, ' ').trim();
    }

    // ---- off-topic: a short polite LOCAL reply, never the online AI (owner 2026-10-04)
    var OFF_RE = /\b(?:weather|forecast|raining|rain at|who won|winner of the|won the (?:race|championship|cup|title)|poem|haiku|limerick|joke|riddle|lyrics|oil change|change (?:my|the) oil|tyre pressure|tire pressure|setup for|car setup|best setups?|lap ?times?|get faster|be faster|braking points?|racing line|stock market|stocks|bitcoin|crypto|ethereum|price of (?:gas|oil|bitcoin|gold)|the news|politics|president|election|movies?|netflix|homework|essay|translate|what time|the time is|what day is|today'?s date|how old are you|who are you|your name|are you (?:real|human|alive|a bot)|meaning of life|sandwich|pizza|recipe for chili|chili con carne|cook(?:ing)?|bake|baking|dinner|lunch|breakfast|soup|pasta|cookies|cake|horsepower|sim rig|pedals?|force feedback|python|javascript|an email|you suck|you(?:'re| are) (?:dumb|stupid|useless|trash|bad)|stupid bot|shut up|my driving|your favou?rite)\b/i;
    var APP_WORD_RE = /\b(?:shokker|spb|livery|liveries|paint(?:s|ed|ing| job| booth)?|finish(?:es)?|spec(?: map)?|render\w*|template|zones?|layers?|decals?|sponsors?|logos?|tga|mip|psd|trading ?paints|tradingpaints|clear ?coat|roughness|metallic|car ?folder|customer id|user id)\b/i;          // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- "whats the deal with clearcoat" is about the app, not off-topic
    var OFF_TEXT = 'I only know Shokker Paint Booth, so I cannot help with that one. Ask me to change your paint (“make the hood red”) or about the app (“how do I render?”).';
    function offtopic(t) { return (OFFTOPIC_RE.test(t) && !/\b(?:paint|livery|finish|colou?r)\b/i.test(t)) || (OFF_RE.test(t) && !APP_WORD_RE.test(t)); }
    function local(why, text) { var A = { id: 'local.' + why, title: why === 'offtopic' ? 'I only know Shokker Paint Booth' : 'I did not catch that', text: text || OFF_TEXT, actions: [], how: [], faq: '', level: '', shot: null }; return { cls: 'ANSWER', via: why, why: why, local: true, hits: [{ id: A.id, title: A.title, score: 0 }], answer: A }; }
    var START_CHIPS = ['Make the hood red', 'Show me looks for the body', 'How do I render?'];

    // ---- custom art: broader than the phase-2 list (scenes, creatures, tributes, "the picture I uploaded"); texture words ("tiger stripes", "dragon scales") stay looks
    var ART_THING = '(?:dragons?|skulls?|reapers?|grim reaper|demons?|devils?|angels?|phoenix|mermaids?|unicorns?|butterfl(?:y|ies)|roses|tigers?|panthers?|cobras?|scorpions?|spiders?|dinosaurs?|t-?rex|robots?|aliens?|clowns?|jokers?|warriors?|samurai|ninjas?|knights?|vikings?|pirates?|soldiers?|superheroe?s?|monsters?|creatures?|zombies?|eagles?|hawks?|wolves|wolf|lions?|bears?|sharks?|horses?|faces?|portraits?|murals?|scenes?|landscapes?|skylines?|cityscapes?|sunsets?|sunrises?|palm trees?|mountains?|beach)';
    var ART_AFTER = '(?!\\s*(?:scales?|skin|print|pattern|camo|stripes?|texture|fur pattern|gold|pink|red|gr[ae]y|green|blue|orange|white|black|yellow|purple|metallic|finish|look|colou?r|style))';
    var DECLINE2 = [
        [new RegExp('\\b(?:draw|sketch|illustrate|airbrush|paint|put|add|place|stick|do|make|give|want|need)\\b[^.,;]{0,30}?\\b(?:a|an|some|the|my|our|two|three)\\s+(?:[a-z-]+\\s+){0,2}?' + ART_THING + '\\b' + ART_AFTER, 'i'), 'custom-art', true],
        [new RegExp('^\\s*(?:a|an|some|two)\\s+(?:[a-z-]+\\s+){0,2}?' + ART_THING + '\\b' + ART_AFTER + '[^.]{0,40}\\b(?:on|across|over|down)\\b', 'i'), 'custom-art', true],
        [/\b(?:real|realistic|lifelike) (?:fur|feathers|skin|hair|detail)\b|\bbreathing fire\b/i, 'custom-art', false],
        [/\b(?:the |this |my |a )?(?:picture|photo|image|pic|screenshot) (?:i|we) (?:uploaded|sent|attached|gave you|posted|shared)\b|\b(?:trace|copy|match) (?:this|the|my|a) (?:photo|picture|image|pic)\b|\blike (?:this|the|my) (?:photo|picture|pic|image)\b/i, 'photo', false],
        [/\btribute\b|\bin memory of\b|\bmemorial\b|\b(?:inspired by|based on)\b[^.]{0,40}\b(?:with|and)\b[^.]{0,40}\b(?:palm trees?|sunsets?|skylines?|neon|scenery|characters?)\b/i, 'custom-design', false]
    ];
    function decline2(t) { var lk = /\blooks? (?:like|as if)\b|\bsomething like\b|\b(?:themed?|vibe|inspired|style)\b/i.test(t); for (var i = 0; i < DECLINE2.length; i++) if (!(lk && DECLINE2[i][2]) && DECLINE2[i][0].test(t)) return DECLINE2[i][1]; return null; }

    // ---- follow-ups: bound to the LAST change (env.last, the copilot's own edit memory); with no earlier change, a question back with chips, never a guess
    var NOPE_RE = /^\s*(?:no+|nope|nah)\b[\s,.!]*(?:(?:not|no) (?:that|this|like that|what i (?:meant|wanted|asked(?: for)?))(?: one)?|(?:that'?s |its |it'?s )?wrong(?: one)?|undo (?:that|it))?[\s.!]*$|^\s*not (?:that|this)(?: one)?[\s.!]*$|^\s*(?:that'?s|thats|it'?s|its) (?:not (?:it|right|what i (?:meant|wanted|asked for))|wrong)[\s.!]*$/i;
    var OTHER_RE = /^\s*(?:no,? )?(?:i meant |use |try |do |pick |go with |what about )?the (?:other|second|first|previous|next) (?:one|colou?r|look|finish)\b|^\s*(?:the )?other one\b/i;
    // HELPER FIX PASS 7 2026-10-05: the word before a colour in "X or Y" is never is / are / the (b5-058 "Make the car is gold")
    var CHOICE_RE = new RegExp('^\\s*(?:should i (?:go |do |use |pick )?|(?:maybe|either) )?((?:(?!(?:is|are|was|be|the|it|its|a|an|or|and) )[a-z]+ )?(?:' + COLOUR_WORDS + '|chrome|matte|gloss|satin|metallic|pearl|candy|carbon))\\s+or\\s+((?:[a-z]+ )?(?:' + COLOUR_WORDS + '|chrome|matte|gloss|satin|metallic|pearl|candy|carbon))\\b\\s*\\??', 'i');
    var BARE_ADJ_RE = /^\s*(?:(?:can you |could you )?(?:make it |go |just )?)?(?:(?:a )?(?:bit|little|touch|tad|smidge|lot|hair)(?: bit)? |slightly |much |way |even |bit )?(?:more|less|darker|lighter|brighter|duller|shinier|glossier|deeper|paler|bigger|smaller|stronger|weaker|softer|richer|warmer|cooler|redder|bluer|flatter)(?: please| than that| still| again)?\s*[.!?]*$/i;
    var SAME_RE2 = /\b(?:same|likewise|do that|copy (?:that|it)|mirror (?:that|it)|as well|too)\b/i, OTHER_SIDE_RE = /\b(?:the )?(?:other|opposite) side\b/i, THAT_PART_RE = /\b(?:that|this) (?:part|bit|area|panel|piece|section)\b/i;
    var REMOVE_IT_RE = /^\s*(?:please\s+)?(?:remove|delete|get rid of|take (?:it|that) off|take off|lose|erase|clear|kill|scrap|ditch)\s+(?:it|that|this|them|those)\s*(?:please)?[.!]*$/i;
    var MATCH_RE = /^\s*(?:make |have |get |can you make )?(?:the |my )?([a-z ]{2,24}?) match(?:es|ing)?\s*[.!?]*$/i;
    var SCALE_RE = /\b(?:crush(?:ed|ing)?|scale(?:d)?(?: it)?|shrink|shrunk)\b[^.,;]{0,25}?(?:\d{1,3}\s*(?:%|percent|per cent)|\bhalf\b|\bsmaller\b|\bbigger\b|\blarger\b|\bfiner\b|\btighter\b|\bdown\b)|\b\d{1,3}\s*(?:%|percent|per cent)\b[^.,;]{0,20}\b(?:scale|size)\b|\b(?:make|go) (?:the )?(?:pattern|texture|camo|flake|scales?|snakeskin|carbon)(?: pattern| texture)? (?:smaller|bigger|larger|finer|tighter)\b/i;
    function vagueChips(env) { return palNames(env, 2).map(function (n) { return 'Change the ' + n; }).concat(['Make it candy red', 'Show me looks for the body']).slice(0, 4); }
    function lastLabel(last) { return last.label || (last.targets || []).map(function (x) { return x.part || x.word || (x.kind === 'body' ? 'car' : x.kind); }).join(' and ') || 'car'; }
    function sideFlip(last) { var ps = (last.targets || []).map(function (x) { return x.part || ''; }); if (ps.indexOf('left side') !== -1 && ps.indexOf('right side') === -1) return 'right side'; if (ps.indexOf('right side') !== -1 && ps.indexOf('left side') === -1) return 'left side'; return null; }
    function followup(t, last, env) {
        var s = String(t).toLowerCase(), pn = palNames(env, 3), E = Ed();
        if (NOPE_RE.test(s)) {
            var ll = last ? lastLabel(last) : '';
            if (last && /\b(?:not|wrong|undo)\b/.test(s)) return { cls: 'ASK', why: 'nope', pass: 'undo-ask', ask: { text: 'OK, taking that back. What should the ' + ll + ' be instead?', chips: ['Make the ' + ll + ' black', 'Make the ' + ll + ' white', 'Change only the shine'] }, steps: [] };
            return asked('nope', 'What should I change instead?', vagueChips(env));
        }
        if (OTHER_RE.test(s)) return asked('other', 'Which one do you mean? Tap it, or type it with the colour or the part (for example “make the roof the other blue”).', vagueChips(env));
        var ch = CHOICE_RE.exec(s); if (ch && !/\b(?:hood|roof|trunk|spoiler|wing|bumpers?|sides?|doors?|numbers?|sponsors?)\b/.test(s)) return asked('choice', 'Try one: Undo puts it back, so you can try the other one next.', ['Make the car ' + ch[1].trim(), 'Make the car ' + ch[2].trim(), 'Show me looks for the body']);
        if (SCALE_RE.test(s)) return asked('scale', '“Crushed to 50%” is the texture SCALE: smaller means finer detail. Which texture? Select the zone or layer that has it, then set its Scale slider (50 = half size).', ['How do I scale a pattern?', 'Show me looks for the body']);
        var mt = MATCH_RE.exec(s); if (mt && !/\b(?:to|with|as)\b/.test(s)) { var who = mt[1].replace(/^(?:it|them|that)$/, 'car').trim(); return asked('match', 'Match what? Pick the colour the ' + who + ' should take.', pn.map(function (n) { return 'Make the ' + who + ' ' + n; }).concat(pn.length < 2 ? ['Make the ' + who + ' black', 'Make the ' + who + ' white'] : [])); }
        if (REMOVE_IT_RE.test(s)) return last ? asked('remove', 'Take back the last change (the ' + lastLabel(last) + ')?', ['Undo', 'How do I remove a pattern?']) : asked('remove', 'Remove what? Nothing has been changed in this chat yet. To hide the numbers or sponsors, say so; to take back a change, press Undo.', ['Hide the numbers layer', 'Hide the sponsors layer', 'How do I remove a pattern?']);
        var bare = BARE_ADJ_RE.test(s) && !/\b(?:make|turn) (?:it|the car|my car|everything)\b[^.]*\b(?:shinier|glossier|duller|flatter|more (?:shiny|glossy|matte))\b/.test(s), same = SAME_RE2.test(s), side = OTHER_SIDE_RE.test(s), tp = THAT_PART_RE.test(s);
        if (same && !side && /^\s*(?:will|would|does|do|is|are|can|could|why|how|what|should)\b/i.test(s) && !/\b(?:do|copy|mirror) (?:the )?same\b/i.test(s)) same = false;          // HELPER FIX PASS 7 2026-10-05 (blind5 b5-020): a question that says "the same" is not a copy request
        if (!(bare || same || side || tp)) return null;
        var pc = null; try { pc = E.parseClause(E.fixText(s)); } catch (e) { pc = null; }
        var hasVal = !!(pc && (pc.colours.length || pc.looks.length || pc.texture || pc.shade || pc.rel || pc.pop || (pc.ext && !commonOnly(pc.ext)))), hasTg = !!(pc && pc.targets.some(function (x) { return x.kind !== 'body'; }));
        if (last && !tp) {
            if (side) { var fl = sideFlip(last); if (!fl) return asked('side', 'Which side should get the same change?', ['Do the same on the left side', 'Do the same on the right side']); return { rewrite: s.replace(OTHER_SIDE_RE, 'the ' + fl) }; }
            return null;          // the edit brain binds "a bit darker" / "same on the roof" / "less" to the last change (env.last)
        }
        if (hasVal && hasTg && !tp && !side) return null;          // a complete change of its own ("make the roof red too")
        if (tp) return asked('which-part', 'Which part? Tap it (or say “the hood”, “the roof” …).', ['hood', 'roof', 'sides'].map(function (p) { return hasVal ? s.replace(THAT_PART_RE, 'the ' + p) : 'Show me looks for the ' + p; }).map(function (x) { return x.charAt(0).toUpperCase() + x.slice(1); }));
        if (same || side) return asked('same', 'Same as what? There is no earlier change in this chat to copy yet. Tell me the change (for example “make the roof red”).', vagueChips(env));
        if (ADJ_RE.test(s)) { var ph = ADJ_RE.exec(s)[1].trim(); return asked('adjust', 'Which colour should be ' + ph + '?', pn.map(function (n) { return 'Make the ' + n + ' ' + ph; })); }
        return asked('adjust', (/\bless\b/.test(s) ? 'Less of what?' : (/\bmore\b/.test(s) ? 'More of what?' : 'What should change?')) + ' Nothing has been changed in this chat yet, so tell me the part or colour.', ['Make the car less shiny', 'Make the colours less saturated', 'Make the car darker']);
    }

    // ---- SCOPE constraints (apply to EVERY clause): keep / don't touch, except / not, only, colours kept (= shine only)
    var SCOPE_NOUN = '(?:numbers?|sponsors?|logos?|decals?|stickers?|lettering|contingenc(?:y|ies)|tape|stripes?|pinstripes?|hood|roof|trunk|spoiler|wing|bumpers?|front bumper|rear bumper|(?:left|right) side|sides|doors?|wheels?|rest)';
    var EXCEPT_RE = new RegExp('\\b(?:except(?: for)?|but not|and not|not|apart from|other than|excluding|aside from|save for|leaving out)\\s+(?:on\\s+)?(?:the |my |any |our )?(' + SCOPE_NOUN + '(?:\\s*(?:,|and|&|or)\\s*(?:the |my )?' + SCOPE_NOUN + ')*)\\b', 'gi');
    var ONLY_RE = /\b(?:only|just)\s+(?:on\s+|do\s+|paint\s+|change\s+)?(?:the |my )?(body|hood|roof|trunk|spoiler|wing|front bumper|rear bumper|bumpers|left side|right side|sides|doors|numbers?|sponsors?|logos?)\b(?:\s+only)?|\b(?:the )?(body|hood|roof|trunk|spoiler|wing|bumpers|sides|doors) only\b/gi;
    var KEEPCOL_RE = /\b(?:(?:keep|leave|save|preserve|(?:do not|don'?t|dont|never|without) (?:change|changing|touch|touching|alter|altering))\s+(?:the |my |all (?:the |my )?|any )?(?:colou?rs?|paint ?job|design|livery)(?:\s+(?:the same|as (?:is|they are)|alone|untouched))?|(?:colou?rs?|design) (?:stay|stays|the same|unchanged|as they are)|only the (?:shine|spec|finish|gloss|sheen)|just the (?:shine|finish|spec)|spec only|shine only)\b/gi;
    function scope(t) {
        var sc = { keep: [], only: [], keepColours: false, rest: t };
        var s = String(t).replace(KEEPCOL_RE, function () { sc.keepColours = true; return ' , '; });
        var pr = protect(s); if (pr.words.length) { s = pr.rest; pr.words.forEach(function (w) { if (/^(?:colou?rs?|paint ?job|design|livery)$/.test(w)) sc.keepColours = true; else sc.keep.push(w); }); }
        s = s.replace(EXCEPT_RE, function (m, w) { String(w).toLowerCase().split(/\s*(?:,|\band\b|&|\bor\b)\s*/).forEach(function (x) { x = x.replace(/^(?:the|my)\s+/, '').trim(); if (x && sc.keep.indexOf(x) === -1) sc.keep.push(x); }); return ' , '; });
        s = s.replace(ONLY_RE, function (m, a, b) { var p = String(a || b).toLowerCase(); if (sc.only.indexOf(p) === -1) sc.only.push(p); return ' , '; });
        sc.rest = s.replace(/\s*,\s*(?:,\s*)+/g, ', ').replace(/^[\s,.;!]*(?:(?:but|and|then|just|so|please)\b[\s,.;!]*)*/i, '').replace(/[\s,.;!]*(?:\b(?:but|and|then|please))?[\s,.;!]*$/i, '').trim();
        return sc;
    }
    function onlyTarget(w) {
        if (w === 'body') return [{ kind: 'body' }];
        if (/^numbers?$/.test(w)) return [{ kind: 'numbers' }]; if (/^(?:sponsors?|logos?)$/.test(w)) return [{ kind: 'sponsors' }];
        if (w === 'sides' || w === 'doors') return [{ kind: 'part', part: 'left side' }, { kind: 'part', part: 'right side' }];
        if (w === 'bumpers') return [{ kind: 'part', part: 'front bumper' }, { kind: 'part', part: 'rear bumper' }];
        return [{ kind: 'part', part: w === 'wing' ? 'spoiler' : w }];
    }

    // ---- typed ENTITIES: numbers, sponsors / logos / brand names, text, pictures. Adding one is never a finish search ("I do not know a look called sunoco")
    var ENT_RE = { numbers: /\b(?:numbers?|number \d{1,3}|#\s?\d{1,3})\b/i, sponsors: /\b(?:sponsors?|logos?|decals?|stickers?|lettering|contingenc(?:y|ies))\b/i, stripes: /\b(?:stripes?|pin ?stripes?|tape)\b/i };
    var ADD_VERB = /\b(?:add|put|place|stick|slap|apply|import|upload|stamp|write|letter|print)\b/i;
    function isLook(w) { try { return !!(Ed() && Ed().lookFor && Ed().lookFor(w)); } catch (e) { return false; } }
    function entityAsk(t, raw) {
        var s = String(t).toLowerCase(), r0 = String(raw || t);
        if (/\b(?:make|turn|change|recolou?r|colou?r|set|switch|swap|darken|lighten|brighten|dull|tint)\b/.test(s) && !ADD_VERB.test(s)) return null;          // "make the number 24 gold": a change of what is already there
        var img = /\b(?:png|jpe?g|webp|gif|svg|image file|picture file|logo file|(?:i have|i'?ve got|i got) (?:a |my |the |our )?(?:own )?(?:logo|image|picture))\b/i.test(s);
        var bm = /\b([a-z][a-z'&.-]{2,}(?: [a-z][a-z'&.-]{2,})?) (?:logos?|stickers?|decals?)\b/i.exec(s), bw = bm ? bm[1].replace(/^(?:(?:a|an|the|my|our|some|big|small|new|old|main|add|put|place|their|his|her)\s+)+/, '') : null;
        if (bw && (new RegExp('^(?:(?:' + COLOUR_WORDS + '|a|an|the|my|our|some|big|small|new|old|main|primary|secondary|associate|add|put|place|all|any|team|car|own|custom|sponsor|race|the sponsor|contingency)\\s*)+$', 'i').test(bw) || isLook(bw))) bw = null;
        var listed = /\bsponsors?\s*:/.test(s) || /\b(?:primary|secondary|associate|main) sponsors?\b/.test(s);
        var sponsorAdd = img || !!bw || listed || (ENT_RE.sponsors.test(s) && ADD_VERB.test(s));
        var text = (/\b(?:team name|my name|our name|text|words|lettering|slogan|quote|letters)\b/.test(s) || /^\s*write\b/.test(s) || /["“][^"”]{2,}["”]/.test(r0) || (/\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b/.test(r0) && r0 !== r0.toUpperCase())) && (ADD_VERB.test(s) || /\bon (?:the|my|both|each) /.test(s));
        var numAdd = /\b(?:add|put|place|stick|stamp|paint|want|need)\s+(?:a |the |my |number |#)?(?:big |large |huge |small |giant |bold |white |black |gold |red )?(?:number\s*)?#?\d{1,3}\b(?!\s*(?:%|percent|per cent))/.test(s) || /\b(?:number|#)\s*\d{1,3}\b[^.,;]{0,25}\bon (?:the|both|each|my)\b/.test(s) || /\b(?:a|the) (?:big |large |huge |small |giant |bold )?\d{1,3} on (?:the|both|each|my)\b/.test(s);
        if (numAdd) return { kind: 'numbers', ids: ['preview_render.number_modes', 'help_howto_1.add_logo'], lead: 'There is no number tool in Shokker: iRacing draws the sim number for you, or you add your own number artwork as a picture layer (PNG). Here is how:' };
        if (text && !/\b(?:pattern|finish|look)\b/.test(s)) return { kind: 'text', ids: ['help_howto_1.add_text', 'help_howto_1.add_logo'], lead: 'Shokker has no text tool, so I cannot write that for you: lettering goes on as a picture layer (a transparent PNG). Here is how:' };
        if (sponsorAdd) return { kind: img ? 'image' : 'sponsors', ids: ['help_howto_1.add_logo', 'recipes.change_body_keep_numbers'], lead: bw ? 'I cannot draw the “' + bw + '” logo, but you can put it on as a picture layer (a PNG of the logo). Here is how:' : (img ? 'Your picture goes on as its own layer. Here is how:' : 'Logos and sponsors go on as picture layers (PNG). Here is how:') };
        return null;
    }
    // a few asks whose best answer is one known article (a recipe the helper cannot build in one step, what the helper can do, the catalogue size)
    var PIN = [
        [/\bnight (?:and|&|\/) day\b|\bday (?:and|&|\/) night\b/i, ['recipes.night_day'], 'Two versions = two renders: the recipe below shows the quickest way.'],
        [/\bwhat (?:can|do) (?:you|it|this|the helper|the built-in helper) (?:actually |really |even )?(?:do|make|help with)\b|\bwhat are you (?:able|good) (?:to|at|for)\b/i, ['ai_copilot.offline_vs_ai', 'ai_copilot.can_and_cannot'], 'Offline I build changes step by step (colours, finishes, textures, named parts; nothing changes until ▶ Run) and answer questions about Shokker from the encyclopedia.'],
        [/\bhow many (?:finishes|bases|patterns|spec patterns|colou?rs|looks|textures)\b/i, ['finishes.catalogue_overview'], ''],
        [/\b(?:matching |a |my )(?:helmet|suit|firesuit|race suit)\b|\bhelmet (?:and|&) suit\b/i, ['recipes.helmet_suit'], ''],
        [/^(?=.*\b(?:difference|diff|vs\.?|versus|compared?|or)\b)(?=.*\bcandy\b)(?=.*\bpearl\b)(?!.*\b(?:make|paint|turn|give)\b)/i, ['recipes.candy', 'finishes.foundation_shine_only'], ''],
        [/^(?:explain|what (?:are|do|is)|tell me about|how do)\b[^?]{0,30}\bspec(?: map)? channels?\b/i, ['spec.what_is_spec_map', 'spec.channel_sliders'], '']
    ];
    function pinned(ids, lead, via, text) {
        if (!IX) return null; if (!IX.byId) { IX.byId = {}; IX.docs.forEach(function (d) { IX.byId[d.id] = d; }); }
        var hits = ids.map(function (id) { var d = IX.byId[id]; return d ? { id: d.id, score: 10, cov: 1, doc: d } : null; }).filter(Boolean); if (!hits.length) return null;
        var r = answered(hits, text || ''); r.via = via || 'entity'; if (lead) r.lead = lead; return r;
    }

    // ---- elements to ADD ("X with a Y stripe"): base X is the change, the stripe is drawn with its own tool (a chip), never "recolour the Y things"
    var EL_NOUN = '(?:pin ?stripes?|racing stripes?|rally stripes?|stripes?|outlines?|borders?|flames|checkers|checkered flags?|chequered flags?|tape|bands?)';
    var EL_RE = new RegExp('(?:\\b(?:with|plus|add|including)|\\band (?=(?:a|an|some|two|twin|thin|thick)\\b))\\s+((?:(?:a|an|some|two|twin|thin|thick|skinny|wide|fat|double|dual|single|little|small|big|retro|racing)\\s+)*)((?:[a-z]+\\s+){0,2}?)(' + EL_NOUN + ')\\b([^,.;]*)', 'gi');
    function elements(t) {
        var els = [], rest = String(t).replace(EL_RE, function (m, adj, mid, noun, tail) { var cm = new RegExp('\\b(' + COLOUR_WORDS + ')\\b', 'i').exec(mid + ' ' + adj); tail = String(tail || '').replace(/\s+(?:and|then|but|so|or)\s+(?:make|the|i|paint|turn|put|add|give|keep|leave)\b.*$/i, '').replace(/\s*\b(?:and|but|then|so|oh|or|please)\s*$/i, ''); els.push({ raw: (adj + mid + noun + tail).replace(/\s+/g, ' ').trim(), kind: noun.toLowerCase(), colour: cm ? cm[1].toLowerCase() : null, tail: String(tail || '').trim() }); return ' , '; });
        return { els: els, rest: rest.replace(/\s*,\s*(?:,\s*)*$/, '').trim() };
    }
    // "with a little gold pearl": an accent look on the base (the look rides on the base step; a pearl's tint colour is not a separate finish)
    var ACC_RE = new RegExp('\\b(?:with|and) (?:(?:a (?:little|bit of|touch of|hint of|dash of|little bit of))|some|a|an|light|heavy)?\\s*(?:(' + COLOUR_WORDS + '|rose gold)\\s+)?(pearl|metal ?flake|flake|metallic|sparkle|glitter|shimmer)\\b', 'i');
    function accent(t) { var m = ACC_RE.exec(t); if (!m) return { text: t, note: '' }; return { text: (t.slice(0, m.index) + ' ' + m[2] + ' ' + t.slice(m.index + m[0].length)).replace(/\s+/g, ' ').trim(), note: m[1] ? 'The ' + m[1] + ' ' + m[2] + ' tint is not a separate finish: the ' + m[2] + ' uses the base colour.' : '' }; }

    // ---- CLAUSE FRAMES: own part lexicon (incl. parts the car map does not have), the edit brain reads the VALUE of the part-stripped clause
    var PARTS2 = [
        [/\b(?:front bumper|front fascia|nose|front end)\b/g, ['front bumper']],
        [/\b(?:rear bumper|back bumper|rear fascia|tail end|tail)\b/g, ['rear bumper']],
        [/\b(?:splitter|front lip|air ?dam|chin spoiler)\b/g, ['front bumper'], 'the splitter is part of the front bumper on this car map'],
        [/\bdiffuser\b/g, ['rear bumper'], 'the diffuser is part of the rear bumper on this car map'],
        [/\bbumpers?\b/g, ['front bumper', 'rear bumper']],
        [/\b(?:hood|bonnet)\b/g, ['hood']], [/\broof\b/g, ['roof']], [/\b(?:trunk|boot lid|deck ?lid|rear deck)\b/g, ['trunk']], [/\b(?:rear wing|spoiler|wing)\b/g, ['spoiler']],
        [/\b(?:left|driver'?s?) (?:side|doors?|flank|panels?|quarter ?panels?)\b/g, ['left side']], [/\b(?:right|passenger'?s?) (?:side|doors?|flank|panels?|quarter ?panels?)\b/g, ['right side']],
        [/\b(?:quarter ?panels?|quarters|fenders?|doors?)\b/g, ['left side', 'right side'], 'the doors, quarter panels and fenders are part of the left and right sides on this car map'],
        [/\b(?:both sides|sides|side|flanks?|body ?sides?)\b/g, ['left side', 'right side']]
    ];
    var OFFMAP_RE = /\b(side ?mirrors?|mirrors?|rockers?(?: panels?)?|side ?skirts?|skirts?|sills?|a-pillars?|pillars?|windows?|windshield|windscreen|glass|wheels?|rims?|tires?|tyres?|roll ?cage|interior|exhaust|grille|grill|headlights?|tail ?lights?|taillights?|antenna|cockpit|seats?)\b/g;
    function offmapWord(s) { var out = []; String(s).replace(OFFMAP_RE, function (m, w, at) { var pre = s.slice(Math.max(0, at - 8), at); if (w === 'mirror' && (/like a $|a $/.test(pre) || /^mirror[- ](?:finish|chrome|polish|like|shine|look)/.test(s.slice(at)))) return m; out.push(w); return m; }); return out; }
    function clauseFrame(c) {
        c = String(c).replace(/\b(?:a|an|the|my)\s+((?:[a-z]+\s+){1,3}?)base(?: colou?r| coat)?\b/i, 'the body $1');          // "a dark blue base" = the body in dark blue
        var E = Ed(), s = ' ' + String(c).toLowerCase() + ' ', f = { raw: c, targets: [], notes: [], offmap: [], ents: {} };
        Object.keys(ENT_RE).forEach(function (k) { if (ENT_RE[k].test(s)) f.ents[k] = true; });
        var ART = '(?:\\b(?:on |to |for |of )?(?:the |my |both |each |all (?:the )?|all )?)';          // "make the quarter panels metallic blue" -> "make metallic blue" (a dangling "the" would read "the blue" as a colour ON the car)
        f.offmap = offmapWord(s); f.offmap.forEach(function (w) { s = s.replace(new RegExp(ART + '\\b' + w.replace(/[-]/g, '\\-') + '\\b'), ' '); });
        var parts = [];
        PARTS2.forEach(function (p) { p[0].lastIndex = 0; if (p[0].test(s)) { p[0].lastIndex = 0; s = s.replace(new RegExp(ART + '(?:' + p[0].source + ')', 'g'), ' '); p[1].forEach(function (x) { if (parts.indexOf(x) === -1) parts.push(x); }); if (p[2] && f.notes.indexOf(p[2]) === -1) f.notes.push(p[2]); } });
        var pcF = null, pcS = null; try { pcF = E.parseClause(E.fixText(c)); } catch (e0) { pcF = null; }
        try { pcS = parts.length || f.offmap.length ? E.parseClause(E.fixText(s.replace(/\s+/g, ' ').trim() || c)) : pcF; } catch (e1) { pcS = pcF; }
        if (pcF && pcF.targets.some(function (x) { return x.kind === 'colour' && x.parts && x.parts.length; })) { parts = []; f.notes = []; pcS = pcF; }          // "the yellow on the hood": a colour ON a part is the target (the edit brain checks it is there)
        var pc = pcS || pcF || { targets: [], colours: [], looks: [] };
        parts.forEach(function (p) { f.targets.push({ kind: 'part', part: p }); });
        (pcF ? pcF.targets : []).forEach(function (x) { if (x.kind === 'numbers' || x.kind === 'sponsors' || x.kind === 'accents' || x.kind === 'layer') { if (f.ents[entOfTarget(x) || 'none'] || x.kind === 'layer') f.targets.push(x); }          /* "my car is the 88": a mention, not a target */ else if (x.kind === 'colour' && !parts.length) f.targets.push(x); else if (x.kind === 'body') f.whole = true; });
        if (WHOLE_RE.test(c)) f.whole = true;
        var strongWhole = /\b(?:make|paint|turn|do|spray|colou?r) it\b|\bwhole thing\b|\beverything\b|\bit all\b|\bthe whole car\b|\bthe body\b/i.test(c);
        if (strongWhole && !parts.length && f.targets.length && f.targets.every(function (x) { return x.kind === 'colour'; })) { var cw0 = f.targets.map(function (x) { return x.word; }).join(' '), cc0 = (pcF.colours || [])[0]; var cj = (/\bthe body\b/i.test(c) ? colourObj(cw0) : null) || colourObj(cw0 + (cc0 ? ' ' + cc0.name : '')) || colourObj(cw0); if (cj) { f.targets = []; f.forceColour = cj; } }
        var lk = (pc.looks || []).slice(-1)[0] || null, col = f.forceColour || (pc.colours || [])[0] || null, ext = pc.ext && !commonOnly(pc.ext) ? pc.ext : null;
        if (!col && (parts.length || f.offmap.length)) { var ctg = (pc.targets || []).filter(function (x) { return x.kind === 'colour'; })[0]; if (ctg) col = colourObj(ctg.word); }          // the part named, the colour is the NEW colour
        if (!ext && !pc.texture) { var pw = PAT_WORD_RE.exec(c); if (pw && !(lk && new RegExp('\\b' + lk.id + '\\b', 'i').test(pw[0]))) ext = pw[0].toLowerCase(); }          // "camo green and tan": the pattern word the edit brain skipped
        var ph = new RegExp('(' + PAT_WORD_RE.source.replace(/^\\b/, '') + ')(?: skin)?\\s+(?:pattern|print|texture)\\b', 'i').exec(c); if (ph) { pc = Object.assign({}, pc, { texture: null, ext: null }); lk = lk && lk.id === ph[1].toLowerCase() ? null : lk; } if (ph) ext = /snake/i.test(ph[0]) ? 'snakeskin' : ph[1].toLowerCase() + (/ skin\s/i.test(ph[0]) && !/skin/i.test(ph[1]) ? ' skin' : '');          // "rattlesnake skin pattern ... in pink camo colors": the word on "pattern" is the pattern, "camo colors" only the colours
        if (ext && col && !lk && !pc.texture && !knownTerm(ext)) ext = null;
        if (ext && col && /^(?:a |an )?(?:bit |little |touch )?(?:lighter|darker|brighter|deeper|paler|richer|softer|bolder|lite|light|dark)$/i.test(ext)) ext = null;          // "a lighter mint": a shade word on a colour is not a look (HELPER_V2 2026-10-04 owner: keep improving the Offline Helper)          // "lamborghini orange" / "british racing green": a brand colour name is the colour
        f.value = { colour: col, look: lk && ext && PAT_WORD_RE.test(ext) ? null : lk, texture: pc.texture || null, ext: lk && !(ext && PAT_WORD_RE.test(ext)) ? null : ext, look2: lk && ext && PAT_WORD_RE.test(ext) ? lk : null, rel: pc.rel || null, soft: !!pc.soft, strong: !!pc.strong, shade: pc.shade || null, keep: !!pc.keep, pop: !!pc.pop, sub: pc.sub || null };
        f.hasValue = !!(col || lk || pc.texture || (ext && !commonOnly(ext) && (f.targets.length || parts.length || (knownTerm(ext) && ext.split(' ').length <= 2) || PAT_WORD_RE.test(ext))) || pc.shade || pc.rel || pc.pop);          // an unknown word alone ("asdfghjkl") is not a look
        return f;
    }
    var PAT_WORD_RE = /\b(?:digital camo|camo(?:uflage)?|forged carbon|carbon(?: fiber| fibre)?|kevlar|honeycomb|hexagons?|checker(?:ed|board)|plaid|houndstooth|marble|damascus|leopard|zebra|cheetah|giraffe|tiger stripes?|snake ?skin|rattlesnake|croc(?:odile)?(?: skin)?|dragon scales?|tribal|hammered|crackle|rust(?:ed|y)?|patina|galaxy|nebula|holo(?:graphic)?|prism(?:atic)?|rainbow|chameleon|colou?r ?shift|flip ?flop)\b/i;
    function knownTerm(x) { var Bb = B(); try { return !!(Bb && Bb.flag && Bb.flag(x).some(function (f) { return !f.weak && f.kind !== 'info' && !commonOnly(f.alias || ''); })); } catch (e) { return false; } }
    function hasValueText(x) { var E = Ed(); try { var p = E.parseClause(E.fixText(x)); return !!(p.colours.length || p.looks.length || p.texture || p.shade || p.rel || (p.targets || []).some(function (x) { return x.kind === 'colour'; }) || HAS_COL_RE.test(x) || PAT_WORD_RE.test(x)); } catch (e) { return false; } }
    var HAS_COL_RE = new RegExp('\\b(?:' + COLOUR_WORDS + ')\\b', 'i');          // "the white roof and black wing": a colour word on a part is a value too
    var START_FRAME = /^(?:(?:i want|i'?d like|make|paint|turn|give|put|add|do|set|change|have|get)\b|(?:the |my |a |an )?(?:[a-z]+ ){0,2}?(?:hood|bonnet|roof|trunk|spoiler|wing|bumpers?|front bumper|rear bumper|left side|right side|sides|doors?|quarter ?panels?|fenders?|splitter|mirrors?|rockers?|body|numbers?|sponsors?|logos?)\b)/i;
    function splitFrames(t) {
        var out = [];
        // "yellow body with black hood" / "gloss black with a carbon hood": the part after "with" is its own job (a stripe / pinstripe after "with" stays an element)
        t = String(t).replace(/\s+with\s+(?:a |an |the )?(?=(?:[a-z-]+ ){1,3}(?:hood|roof|trunk|spoiler|wing|bumpers?|front bumper|rear bumper|doors|sides?|splitter|mirrors?|rocker|fenders|quarter panels)\b)/gi, function (m, off, all) { var L = all.slice(0, off), E = Ed(), pl = null; try { pl = E.parseClause(E.fixText(L)); } catch (e) { pl = null; } return hasValueText(L) || (pl && (pl.targets || []).some(function (x) { return x.kind === 'colour'; })) ? ', the ' : m; });
        String(t).split(/\s*(?:[,;!]|\.(?:\s+|$)|\?\s+|\band then\b|\bthen\b|\balso\b|\bplus\b|\bbut\b)\s*/i).forEach(function (p) {
            p = String(p || '').replace(/^\s*(?:(?:and|oh|also|plus|with|&|so|ok|okay|now)\s+)+/i, '').trim(); if (!p) return;
            var bits = p.split(/\s+and\s+/i), cur = bits[0];
            for (var i = 1; i < bits.length; i++) { if ((hasValueText(cur) || FILLER_RE.test(cur)) && START_FRAME.test(bits[i]) && (hasValueText(bits[i]) || /^(?:i want|i'?d like|make|paint|turn|give|put|add|do|set|change|have|get|keep|leave)\b/i.test(bits[i]) || FILLER_RE.test(cur))) { out.push(cur); cur = bits[i]; } else cur += ' and ' + bits[i]; }          // "lime green hood and roof": a bare part after "and" shares the value
            out.push(cur);
        });
        return out.filter(function (x) { return x && /[a-z]/i.test(x); });
    }
    function isElementClause(c) { return (ELEMENT_RE.test(c) || FADE_RE.test(c)) && !/\b(?:pattern|finish|texture|camo)\b/i.test(c) && !/\b(?:make|turn|change|recolou?r|colou?r|paint)\s+(?:the |my |all (?:the )?|those )?(?:[a-z]+ )?(?:stripes?|pinstripes?|bands?|borders?|outlines?|flames|flags?|checkers?)\b/i.test(c); }
    // a later whole-body step paints over parts named before it ("lime green hood and roof, black body" ran as a black car, seen in-app 2026-10-04): the body goes first, parts on top
    function bodyFirst(ops) { var isB = function (o) { return !!(o && o.target && /^(?:body|whole|car)$/.test(o.target.kind)); }; return ops.filter(isB).concat(ops.filter(function (o) { return !isB(o); })); }
    function frameOps(t, sc) {
        var out = { ops: [], notDone: [], notes: [], named: {}, offmap: [], els: [], clauses: 0, used: 0 }, pending = [];
        splitFrames(t).forEach(function (c) {
            if (FILLER_RE.test(c) || commonOnly(c)) return;
            out.clauses++;
            if (isElementClause(c)) { out.notDone.push(c); out.els.push(c); return; }          // "... and put a stripe on the hood": drawn with its own tool
            var f = clauseFrame(c);
            if (!f.hasValue) { if (f.targets.length && !f.offmap.length) { pending = pending.concat(f.targets); return; } if (!/^\s*(?:i want|i need|can you|could you|please)\s*$/i.test(c)) out.notDone.push(c); return; }
            Object.keys(f.ents).forEach(function (k) { if (f.targets.some(function (x) { return entOfTarget(x) === k; })) out.named[k] = 1; });
            var tgs = pending.concat(f.targets); pending = [];
            if (!tgs.length && !f.offmap.length && out.ops.length && !f.value.colour && !f.whole && (f.value.look || f.value.rel) && !/\b(?:it|them|that|those|this|these)\b/i.test(c)) { var prevOps = out.ops.filter(function (o) { return o._clause === out.used - 1; }); if (prevOps.length && prevOps.every(function (o) { return !o.look || (f.value.look && o.look.id === f.value.look.id); })) { prevOps.forEach(function (o) { if (f.value.look) o.look = f.value.look; if (f.value.rel && !o.rel) o.rel = f.value.rel; if (f.value.strong) o.strong = true; }); out.clauses--; return; } }
            if (!tgs.length && !f.offmap.length && out.ops.length && /\b(?:it|them|that|those|this|these)\b/i.test(c) && !/\b(?:make|paint|turn|do|spray) it all\b|\beverything\b|\bwhole\b/i.test(c)) tgs = out.ops.filter(function (o) { return o._clause === out.used - 1; }).map(function (o) { return o.target; });          // "... and give IT a snakeskin": it = the previous clause's target
            if (!tgs.length && !f.offmap.length) tgs = sc.only.length ? [].concat.apply([], sc.only.map(onlyTarget)) : [{ kind: 'body' }];
            var v = f.value;
            tgs.forEach(function (tg) { out.ops.push({ _clause: out.used, target: tg, colour: v.colour, look: v.look, texture: v.texture, ext: v.ext, rel: v.rel, soft: v.soft, strong: v.strong, shade: v.shade, keep: v.keep, pop: v.pop, recipe: null, sub: v.sub }); if (v.look2) out.ops.push({ _clause: out.used, target: tg, colour: null, look: v.look2, texture: null, ext: null, rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, recipe: null, sub: null }); });          // "camo green and tan matte": the pattern, then the shine on top
            f.offmap.forEach(function (w) { out.offmap.push({ word: w, value: v }); });
            f.notes.forEach(function (n) { if (out.notes.indexOf(n) === -1) out.notes.push(n); });
            out.used++;
        });
        if (pending.length) out.notDone.push(pending.map(function (x) { return x.part || x.word || x.kind; }).join(' and ') + ' (no change named)');
        out.ops = bodyFirst(out.ops);
        return out;
    }
    // the edit brain's whole-sentence plan wins (it binds "that pink" to an earlier step and reads colours already on the car) unless it misreads the sentence
    function entOfTarget(tg) { var k = tg && tg.kind; if (k === 'numbers' || k === 'sponsors') return k; if (k === 'accents') return 'stripes'; if (k === 'layer' || (k === 'colour' && tg.layers)) { var w = String(tg.word || '') + ' ' + (tg.layers || []).join(' '); if (/number/i.test(w)) return 'numbers'; if (/sponsor|logo|decal|sticker|letter/i.test(w)) return 'sponsors'; if (/stripe|tape/i.test(w)) return 'stripes'; } return null; }
    function planBad(ed, fr) {
        if (!ed || ed.kind !== 'ops' || !ed.ops.length) return 'none';
        if (ed.ops.some(function (o) { return o.ext && !o.look && (commonOnly(o.ext) || (o.colour && !knownTerm(o.ext)) || /\b(?:both|other|match|one|same)\b/.test(o.ext)); })) return 'junk';
        if (ed.ops.some(function (o) { var e = entOfTarget(o.target); return e && !fr.named[e]; })) return 'entity';
        var keys = ed.ops.map(targetKey), ents = ed.ops.map(function (o) { return entOfTarget(o.target); }); if (fr.ops.some(function (o) { return o.target && /^(?:part|numbers|sponsors)$/.test(o.target.kind) && keys.indexOf(targetKey(o)) === -1 && ents.indexOf(entOfTarget(o.target)) === -1; })) return 'lost';
        if (fr.offmap.length) return 'offmap';
        // "make the yellow purple with a black hood": the plan gave the hood the wrong colour; the clause frames read each part with its own colour
        if (fr.ops.some(function (o) { return o.target && o.target.kind === 'part' && o.colour && ed.ops.some(function (p) { return targetKey(p) === targetKey(o) && p.colour && p.colour.hex !== o.colour.hex; }); })) return 'conflict';
        // "make it emerald green": two colour words side by side are ONE colour, not "recolour the emerald"
        if (ed.ops.some(function (o) { return o.target && o.target.kind === 'colour' && !(o.target.parts && o.target.parts.length) && o.colour && o.target.word && o.colour.at === o.target.at + o.target.word.length + 1; }) && fr.ops.length && fr.ops.every(function (o) { return !o.target || o.target.kind !== 'colour'; })) return 'adjcolour';
        return '';
    }
    // ---- the NEVER-TOUCH filter: the last thing before steps leave the router
    function keepEnt(keep, e) { return keep.some(function (w) { return e === 'numbers' ? /number/.test(w) : (e === 'sponsors' ? /sponsor|logo|decal|sticker|letter|contingenc/.test(w) : /stripe|tape/.test(w)); }); }
    function never(steps, named, keep) {
        var gone = {}, out = [], touched = 0;
        steps.forEach(function (s) {
            var w = s.what || null, k = w && w.k;
            if (w && k === 'step' && gone[w.ref]) { gone[s.id] = 1; return; }
            var e = !w ? null : (k === 'numbers' || k === 'sponsors' ? k : (k === 'tg' && w.tg ? entOfTarget(w.tg) : (k === 'layer' ? entOfTarget({ kind: 'layer', word: w.word, layers: w.layers }) : (k === 'colour' && w.tg ? entOfTarget(w.tg) : null))));
            if (e && (!named[e] || keepEnt(keep, e))) { gone[s.id] = 1; return; }
            if (w && (k === 'part' || (k === 'colour' && !(w.tg && (w.tg.parts || w.tg.object || w.tg.layers))))) {
                var ex = ['numbers', 'sponsors', 'stripes'].filter(function (x) { return !named[x] || keepEnt(keep, x); });
                if (ex.length) { s.extra = s.extra || {}; var have = s.extra.exclude || []; ex.forEach(function (x) { if (have.indexOf(x) === -1) have.push(x); }); s.extra.exclude = have; touched++; }
            }
            out.push(s);
        });
        return { steps: out, dropped: Object.keys(gone).length, touched: touched };
    }
    // two-tone: "black on top, gold on bottom" = the roof, hood and trunk in one colour, the rest of the body in the other
    function twoTone(t) {
        if (!/\btwo[- ]?tone\b/i.test(t)) return null;
        var cw = new RegExp('\\b(' + COLOUR_WORDS + ')\\b', 'gi'), cs = [], m; while ((m = cw.exec(t))) { var n = m[1].toLowerCase().replace('gray', 'grey'); if (cs.indexOf(n) === -1) cs.push(n); }
        if (cs.length < 2) return null;
        var top = cs[0], bot = cs[1], tm = new RegExp('\\b(' + COLOUR_WORDS + ')\\s+(?:on\\s+)?(?:the\\s+)?(?:top|upper)\\b', 'i').exec(t), bm = new RegExp('\\b(' + COLOUR_WORDS + ')\\s+(?:on\\s+)?(?:the\\s+)?(?:bottom|lower)\\b', 'i').exec(t);
        if (tm) top = tm[1].toLowerCase().replace('gray', 'grey'); if (bm) bot = bm[1].toLowerCase().replace('gray', 'grey'); if (top === bot) bot = cs.filter(function (x) { return x !== top; })[0];
        var ct = colourObj(top), cb = colourObj(bot); if (!ct || !cb) return null;
        var blank = { look: null, texture: null, ext: null, rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, recipe: null, sub: null };
        return { ops: [Object.assign({ target: { kind: 'body' }, colour: cb }, blank)].concat(['roof', 'hood', 'trunk'].map(function (p) { return Object.assign({ target: { kind: 'part', part: p }, colour: ct }, blank); })), note: 'Two-tone read as: the roof, hood and trunk ' + top + ', the rest of the body ' + bot + '. For a split along the sides, use a gradient (ask “how do I make a two tone”).' };
    }
    var VAGUE2_RE = /^\s*(?:i (?:want|need) (?:a |an )?(?:race ?car|fast car|cool car|nice car|good car|new look|livery|paint ?job|something)\s*[.!]*$|(?:can you |please )?(?:do|make|give me|try) (?:something|anything)(?: (?:cool|nice|good|awesome|sick|different|new|fun|crazy|wild|special|fresh))?\s*[.!]*$|(?:can you |please )?make (?:it|my car|the car|this) (?:look )?(?:good|great|nice|better|cool|awesome|sick|pretty|not boring|less boring|interesting|nicer|cooler)\s*(?:please)?[.!]*$|(?:i don'?t know|idk|i dunno|dunno)?[ ,]*surprise me\b|^this (?:is|looks) (?:ugly|bad|boring|terrible|awful|meh|lame|plain|trash)\b|^(?:it'?s|its|it is) (?:ugly|boring|bland|plain|meh)\b)/i;
    var VAGUE_CHIPS = ['Make it candy red', 'Make it matte black', 'Make it chrome', 'Show me looks for the body'];
    // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- a vague ask ("make it look cool", "surprise me", "something aggressive") offers 4 recipe chips from the
    // encyclopedia's style menu (data/encyclopedia/ideas.json ideas.style_menu -> related); a chip ("Build: Aggressive and mean") becomes guided-builder steps, nothing changes until ▶ Run.
    // The step sentence follows each idea article's first worked example (examples[0]), on the whole car body + the hood / roof (parts every car has), so numbers and sponsors stay.
    var STYLES = [
        ['ideas.make_it_pop', 'Make it pop', 'make the car matte orange and the hood candy blue', /\b(?:pop|stand out|loud|bold|eye.?catching|flashy|bright)\b/],
        ['ideas.aggressive_mean', 'Aggressive and mean', 'make the car flat black and the hood gloss red', /\b(?:aggressive|mean|angry|evil|menacing|nasty|sinister|tough|badass|scary)\b/],
        ['ideas.clean_classy', 'Clean and classy', 'make the car gloss white and the roof red', /\b(?:classy|clean|elegant|simple|tasteful|subtle)\b/],
        ['ideas.stealth_murdered_out', 'Stealth and murdered-out', 'make the car flat black', /\b(?:stealth|murdered|blacked|sneaky|dark|ninja)\b/],
        ['ideas.neon_night', 'Neon night', 'make the car satin black and the hood neon cyan', /\b(?:neon|glow\w*|night|cyber\w*)\b/],
        ['ideas.retro_70s', 'Retro 70s', 'make the car cream and the hood orange', /\b(?:retro|vintage|old.?school|70s|seventies|classic|throwback)\b/],
        ['ideas.fighter_jet', 'Fighter jet', 'make the car matte grey and the roof dark grey', /\b(?:military|fighter|jet|army|tactical|stealth fighter)\b/],
        ['ideas.look_expensive', 'Make it look expensive', 'make the car oxblood red candy', /\b(?:expensive|luxury|luxurious|fancy|rich|premium|posh)\b/]
    ];
    var STYLE_ASK_RE = /^\s*(?:(?:please|can you|could you|just|ok|so)\s+)*(?:(?:make (?:it|my car|the car|this)|go|do|try|give me|i want|i'?d like|let'?s do|let'?s go|paint it)\s+)?(?:(?:look|something|anything|a|an|more|kinda|really|super|very)\s+)*(pop|stand out|loud|bold|flashy|cool|sick|good|great|nice|awesome|fast|sporty|racy|fresh|wild|crazy|different|better|interesting|aggressive|mean|angry|evil|menacing|nasty|sinister|tough|badass|scary|classy|elegant|tasteful|subtle|stealth|sneaky|ninja|neon|glowing|cyber(?:punk)?|retro|vintage|old.?school|70s|throwback|military|fighter jet|tactical|expensive|luxury|luxurious|fancy|premium|posh)(?:\s+(?:look(?:ing)?|style|vibe|livery|feel|theme|please))*\s*[.!?]*\s*$/i;
    function styleList() {          // the style menu's own order (ideas.style_menu.related), titles from the articles when the index is loaded
        var by = {}, ord = []; STYLES.forEach(function (s0) { by[s0[0]] = s0; });
        var menu = IX && IX.docs ? IX.docs.filter(function (d) { return d.id === 'ideas.style_menu'; })[0] : null;
        ((menu && menu.a.related) || STYLES.map(function (s0) { return s0[0]; })).forEach(function (id) { if (by[id] && ord.indexOf(by[id]) === -1) ord.push(by[id]); });
        STYLES.forEach(function (s0) { if (ord.indexOf(s0) === -1) ord.push(s0); });
        return ord.map(function (s0) { var d = IX && IX.docs ? IX.docs.filter(function (d1) { return d1.id === s0[0]; })[0] : null; return { id: s0[0], label: s0[1], say: s0[2], re: s0[3], title: d ? String(d.a.title) : s0[1], ex: d && d.a.examples && d.a.examples[0] ? String(d.a.examples[0].title || '') : '' }; });
    }
    function styleAsk(s) {
        var L = styleList(), hit = L.filter(function (x) { return x.re.test(s); }), rest = L.filter(function (x) { return hit.indexOf(x) === -1; });
        if (/surprise/i.test(s)) { var k = Math.floor(Date.now() / 60000) % rest.length; rest = rest.slice(k).concat(rest.slice(0, k)); }
        var pick = hit.concat(rest).slice(0, 4), r = asked('style', (hit.length ? 'Here are looks like that' : 'Here are 4 looks') + ' from the style menu. Tap one and I will set it up as steps you can check before you press ▶ Run, or describe your own.', pick.map(function (x) { return 'Build: ' + x.label; }));
        r.via = 'style-menu'; return r;
    }
    // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- casual / how-to questions answered offline: the chatty wrapper is dropped before the search
    // (the search itself is the SEARCH LAB's; this only changes the words handed to it) and a diluted-coverage top hit still answers when its title / aliases carry the asked word
    var CASUAL_LEAD_RE = /^\s*(?:(?:yo+|hey+|hi+|hello|so|ok(?:ay)?|um+|uh+|hmm+|btw|quick question|random question|dumb question|stupid question|noob question|question|real quick|sorry)\b(?:\s+(?:but|though|here))?[\s,:;!.?-]*)+/i;
    function casualCore(t) {
        var s = String(t || '').replace(CASUAL_LEAD_RE, '').replace(/\b(?:lol|lmao|pls|plz|please|thanks|thx|ty|bro|bruh|man|dude|mate|haha)\b[\s!.?]*$/i, '').replace(/\bu\b/gi, 'you').replace(/\bur\b/gi, 'your');
        s = s.replace(/^\s*(?:i (?:wanna|want to|would like to|was wondering|wonder)(?: know)?|i'?m wondering|wondering)\s+/i, '');
        s = s.replace(/^\s*(?:what'?s|what is|whats) the (?:deal|story|thing) with\s+/i, 'what is ').replace(/^\s*(?:what'?s|whats) up with\s+/i, 'what is ');
        var m = /^\s*(?:(?:can|could|would) you\s+)?(?:please\s+)?(?:tell me|explain(?: to me)?|teach me|help me understand)(?: about)?\s+(.+?)(?:\s+to me)?\s*[?.!]*$/i.exec(s);
        if (m) s =/^(?:how|what|why|where|when|which|who|if|whether)\b/i.test(m[1]) ? m[1] : 'what is ' + m[1];
        s = s.trim(); return s.length >= 3 ? s : String(t || '');
    }
    function titleOverlap(t, h) {
        var d = h && h.doc; if (!d) return false; var q = toks(casualCore(t)).filter(function (w) { return w.length >= 4; }); if (!q.length) return false;
        var bag = ' ' + [toks(d.a.title || '').join(' '), String(d.id).replace(/[._]/g, ' '), (d.a.aliases || []).map(function (x) { return toks(x).join(' '); }).join(' ')].join(' ') + ' ';
        return q.some(function (w) { return bag.indexOf(' ' + w) !== -1; });
    }
    function styleOf(text) { var m = /^\s*build(?: the)?\s*:?\s*(.+?)(?:\s+(?:look|style|recipe))?\s*[.!]*\s*$/i.exec(String(text || '')); if (!m) return null; var n = m[1].toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); return styleList().filter(function (x) { return x.label.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() === n || x.title.split(':')[0].toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() === n; })[0] || null; }

    // ------------------------------------------------------------------ HELPER_V2 fix pass 4 2026-10-04 owner: keep improving the Offline Helper
    // THE CONVERSATION LAYER. Blind round 3: "paint the bumper" > "front" > "white" painted the WHOLE car white; "roof black" > "make it matte" made the whole car matte.
    // Rules: a follow-up with no target inherits the last target; a bare answer to the helper's own question fills that question's slot;
    // "the hood too / same for the trunk / and the rear one / do that on the hood" copy the last look to the new part; "darker" > "a bit less" and
    // "smaller" adjust the zone just made; a follow-up never falls back to the whole car (only "the whole car / everything" says that).
    var CV_WHOLE_RE = /\b(?:whole|entire|all over|everything|everywhere|(?:the|my|this|your) (?:car|body)|full car|car-?wide)\b/i;
    var CV_COPY_RE = /\b(?:too|as well|also|same|likewise|do that|do it|do this|put (?:that|it|this)|try (?:that|it|this)|apply (?:that|it|this)|use (?:that|it|this)|copy (?:that|it)|that on|it on|this on)\b|^\s*(?:and|plus|then|now)\b/i;
    var CV_LESS_RE = /^\s*(?:(?:ok|okay|hmm+|now|actually|maybe|just|no|nah|wait|um+)[\s,]+)*(?:make it |go |tone it |take it )?(?:(?:a )?(?:bit|little|touch|tad|smidge|lot|hair)(?: bit)? |slightly |much |way |even |bit )?(less|more)(?: (?:than that|please|of (?:that|it)|so|still|then))?(?: down)?\s*[.!?]*$/i;
    var CV_SIZE_RE = /\b(smaller|bigger|larger|finer|tighter|coarser|chunkier|tinier|shrink|scale (?:it )?(?:up|down)|zoom (?:in|out))\b/i;
    var CV_FAM = { 'front bumper': ['front bumper', 'rear bumper'], 'rear bumper': ['front bumper', 'rear bumper'], 'left side': ['left side', 'right side'], 'right side': ['left side', 'right side'] };
    var CV_PICK_RE = /\b(?:front|rear|back|left|right|both|all|each|driver'?s?|passenger)\b/i;
    var CV_FILL_RE = /\b(?:and|the|one|ones|of|them|it|in|please|ok|okay|also|too|as|well|same|for|do|that|on|bumpers?|sides?|then|now|just|actually|no|wait|make|paint|colou?r|go|with|a|bit|one|then|both|all|each|front|rear|back|left|right|driver'?s?|passenger|side|thanks|yes|yeah|yep|sure)\b/gi;
    var CV_VAGUE = [
        [/^\s*(?:can you |could you |please |just )?(?:fix|sort(?: out)?|fix up|redo|change) (?:the |my |that |this )?(?:shine|shiny|shininess|gloss|glossy|sheen|reflections?|reflection)\s*[.!?]*$/i, 'shine'],
        [/^\s*(?:can you |could you |please |just |lets |let'?s )?(?:spice|jazz|liven|mix|switch|shake|change|pep|amp|kick|freshen|dress) (?:it|this|things|the car|my car|the paint)? ?up\b(?: a bit| a little| some)?\s*[.!?]*$/i, 'vague'],
        [/^\s*(?:can you |could you |please |just )?(?:make|let) (?:it|the car|my car|this|the paint) (?:pop|stand out|look (?:cool|sick|awesome|fast|mean|aggressive|faster))(?: more| a bit| a little)?\s*[.!?]*$/i, 'pop'],
        [/^\s*(?:can you |could you |please |just |now |ok |okay )?(?:apply|use|add|put on|do|load) (?:the|that|this|a|my|your) (?:finish|look|effect|style|one|thing)\s*(?:then|now|please)?\s*[.!?]*$/i, 'apply'],
        [/^\s*(?:can you |could you |please |just |now )?(?:put|place|move|stick|center|centre) (?:it|that|this|them|one)? ?(?:on|in|at|to|into) (?:the )?(?:middle|center|centre)\b(?: of (?:the )?(?:car|hood|side|door|roof))?\s*[.!?]*$/i, 'middle'],
        [/^\s*(?:and |now |what about |how about )?(?:the )?(back|front|rear|middle|top|bottom|other end)(?: of (?:the |my )?car)?\s*[.!?]*$/i, 'place'],
        [/^\s*(?:can you |please )?make (?:the )?(front|back|rear|top|side|sides|middle)(?: end)? (?:look )?(?:different|better|cooler|nicer|stand out|pop|more interesting)\s*[.!?]*$/i, 'place'],
        [/^\s*(?:the |my |that |those )?(?:stripe|stripes|pinstripe|pinstripes|racing stripes?) (?:should|needs to|need to|has to|must|could|gotta|ought to) (?:be|go|turn) ([a-z ]+?)\s*[.!?]*$/i, 'stripe']
    ];
    var CV_PLACE = { back: ['rear bumper', 'trunk'], rear: ['rear bumper', 'trunk'], 'other end': ['rear bumper', 'trunk'], front: ['front bumper', 'hood'], top: ['roof', 'hood'], middle: ['roof', 'left side'], side: ['left side', 'right side'], sides: ['left side', 'right side'], bottom: ['left side', 'right side'] };
    function cvParse(s) { var E = Ed(); try { return E.parseClause(E.fixText(s)); } catch (e) { return null; } }
    function cvVal(pc, noRel) { return !!(pc && (pc.colours.length || pc.looks.length || pc.texture || (!noRel && (pc.shade || pc.rel || pc.pop)) || (pc.ext && !commonOnly(pc.ext) && knownTerm(pc.ext)))); }
    function cvParts(pc) { return pc ? pc.targets.filter(function (x) { return x.kind !== 'body'; }) : []; }
    function cvTg(p) { return { kind: 'part', part: p }; }
    function cvName(ps) { return ps.length === 2 && /bumper/.test(ps[0]) && /bumper/.test(ps[1]) ? 'both bumpers' : (ps.length === 2 && /side/.test(ps[0]) && /side/.test(ps[1]) ? 'both sides' : ps.join(' and the ')); }
    function cvPartsOf(last) { return (last && last.targets || []).map(function (x) { return x.part || ''; }).filter(Boolean); }
    function cvPool(parts) { var out = []; parts.forEach(function (p) { (CV_FAM[p] || []).forEach(function (q) { if (out.indexOf(q) === -1) out.push(q); }); }); return out; }
    function cvPick(s, pool) {
        if (!pool.length) return [];
        if (/\b(?:both|all|each|them both|either)\b/i.test(s)) return pool.slice();
        return pool.filter(function (p) { return (/\bfront\b/i.test(s) && /front/.test(p)) || (/\b(?:rear|back)\b/i.test(s) && /rear/.test(p)) || (/\b(?:left|driver'?s?)\b/i.test(s) && /left/.test(p)) || (/\b(?:right|passenger)\b/i.test(s) && /right/.test(p)); });
    }
    function cvRest(s) { return String(s).replace(CV_FILL_RE, ' ').replace(/[^a-z0-9#' -]/gi, ' ').replace(/\s+/g, ' ').trim(); }
    function shadeOps(ops, env, text) {          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "a bit darker both" / "make both sides a bit darker" = each part's OWN colour, shaded (the convo + frame readings too)
        var mem = env && env.colMem, lc = env && env.last && env.last.act && env.last.act.colour && env.last.act.colour.hex ? env.last.act.colour : null; if (!mem && !lc) return ops;
        return (ops || []).map(function (o) {
            if (!o || o.colour || o.look || o.texture || !o.shade || !/^(?:darker|lighter|brighter|deeper|paler)$/.test(String(o.shade))) return o;
            var c0 = o.target && o.target.kind === 'part' && mem ? mem[o.target.part] : null; if (!c0 && (!o.target || (env.last.targets || []).some(function (x) { return JSON.stringify(x) === JSON.stringify(o.target); }))) c0 = lc;
            if (!c0 || !c0.hex) return o;
            var dk = /darker|deeper/.test(o.shade) ? -1 : 1, amt = /\b(?:a (?:bit|little|touch|tad)|slightly|little)\b/i.test(String(text || '')) ? 0.15 : 0.28;
            return Object.assign({}, o, { colour: { name: o.shade + ' ' + String(c0.name || 'colour').replace(/^(?:(?:a bit |slightly |even )?(?:darker|lighter|brighter|deeper|paler) )+/i, ''), hex: shadeHex(c0.hex, dk * amt), at: 0, qual: null, exact: true }, shade: null, shadeDir: dk });
        });
    }
    function cvDo(ops, env, text, extra) {
        var Bb = B(); if (!Bb || !ops || !ops.length) return null;
        ops = shadeOps(ops, env, text);
        ops = bodyFirst(ops.map(function (o) { o = Object.assign({}, o); if (o.ext && !o.look && (commonOnly(o.ext) || (o.colour && !knownTerm(o.ext)))) o.ext = null; return o; }));
        var rc = Bb.fromPlan({ kind: 'ops', ops: ops, unknown: [] }, env, text); Bb.check(rc.steps, env);
        var nv = never(rc.steps, {}, []); if (!nv.steps.length) return null;
        return stepsResult(nv.steps, Object.assign({ via: 'convo' }, extra || {}));
    }
    // a value said on its own ("white", "make it matte", "both of them in silver") onto the parts the conversation is about
    function cvPlan(val, tgs, env, extra) {
        var E = Ed(), ed = null, ok = function (e) { return e && e.kind === 'ops' && e.ops && e.ops.length && e.ops.every(function (o) { return o.target && o.target.kind === 'part'; }); };
        try { ed = E.plan(val, Object.assign({}, env, { last: { targets: tgs, act: (env && env.last && env.last.act) || {} } })); } catch (e) { ed = null; }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: the real last act
        if (!ok(ed)) { try { ed = E.plan('make the ' + tgs.map(function (x) { return x.part; }).join(' and the ') + ' ' + val.replace(/^\s*(?:make|paint|colou?r|turn|go|do)\s+(?:it|them|that)?\s*/i, ''), Object.assign({}, env, { last: null })); } catch (e2) { ed = null; } }
        if (!ok(ed)) return null;
        return cvDo(ed.ops, env, val, extra);
    }
    // the last change copied onto new parts ("on the roof too")
    function cvCopy(act, tgs, env, text, more) {
        var E = Ed(), cl = function (x) { return x ? JSON.parse(JSON.stringify(x)) : null; };
        var look = cl(act.lookObj) || (act.look ? (E.lookFor(act.look) || null) : null);
        if (!act.colour && !look && !act.texture && !act.shade && !act.pop) return null;
        return cvDo(tgs.map(function (tg) { var o = { target: tg, colour: cl(act.colour), look: cl(look), texture: cl(act.texture), rel: null, soft: !!act.soft, strong: !!act.strong, shade: act.colour ? null : (act.shade || null), keep: !!act.keep, pop: !!act.pop, ext: null }; if (act.scale) o.scaleMul = act.scale; if (act.shadeDir) o.shadeDir = act.shadeDir; return Object.assign(o, more || {}); }), env, text, { via: 'convo', convo: 'copy' });
    }
    function cvWhich(s, val, act) { return { cls: 'ASK', why: 'which-bumper', ask: { text: 'Which bumper: the front one or the rear one?', chips: ['The front bumper', 'The rear bumper', 'Both bumpers'] }, steps: [], pend: { need: 'which', cands: ['front bumper', 'rear bumper'], say: val || null, act: act || null } }; }
    function cvAskValue(ps) { ps = (ps || []).filter(function (x) { return x && String(x).trim(); }); if (!ps.length) return { cls: 'ASK', why: 'value', ask: { text: 'Which part should change? Tap one, or say a part and a colour.', chips: ['Make the hood black', 'Make the roof white', 'Make the sides blue'] }, steps: [] };          // HELPER FIX PASS 7 2026-10-05: no empty slot ("What should the  be?")
        var nm = cvName(ps); return { cls: 'ASK', why: 'value', ask: { text: 'What should the ' + nm + ' be? Tap one, or type a colour or a look.', chips: ['Make the ' + nm + ' black', 'Make the ' + nm + ' white', 'Make the ' + nm + ' chrome', 'Show me looks for the ' + (ps[0] === 'left side' || ps[0] === 'right side' ? 'sides' : (/bumper/.test(ps[0]) ? 'body' : ps[0]))] }, steps: [], pend: { need: 'value', parts: ps.slice() } }; }
    // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: the follow-up rules (blind round 4: relative edits / bare answers / "same on" / corrections hit the WHOLE car in the app)
    var REL_RE = /\b(?:darker|lighter|brighter|paler|deeper|richer|duller|shinier|glossier|less shiny|more shiny|bigger|smaller|larger|finer|tighter|coarser|less|more|even|too|toned? down|stronger|weaker|softer)\b/i;
    var RETARGET_RE = /^\s*(?:(?:no+|nope|nah|wait|oops|sorry|actually|hmm+)[\s,.!-]+)*(?:not|no) (?:on |to )?(?:the |my |that )?([a-z' ]+?)\s*[,;.!-]+\s*(?:i meant |i mean |do |do it on |put it on |on |make it |instead )?(?:the |my )?([a-z' ]+?)\s*(?:instead|please)?\s*[.!]*$/i;
    var CV_ONLY_RE = /^\s*(?:(?:no|ok|okay|actually|wait|um+|hmm+)[\s,.!]+)*(?:(?:only|just) (?:do |on |paint |the |my )*(.+?)|(?:the |my )?(.+?) only)\s*(?:please)?[.!]*$/i;
    var CHG_RE = /^\s*(?:can you |could you |please |just |i want to |id like to |i'd like to |lets |let'?s )?(?:change|switch|swap|pick|try|use|want|give me|new|another|different)\s+(?:the |a |my |another |some |new |different )*(?:colou?r|paint(?: colou?r)?|paint ?job)s?(?: (?:please|instead|now))?\s*[.!?]*$|^\s*(?:a )?(?:different|new|another) (?:colou?r|paint)(?: please)?\s*[.!?]*$/i;
    var CAR_RE = /^\s*(?:please )?(?:colou?r|paint|recolou?r|respray|re-?paint|redo) (?:the |my )?(?:car|whole car|whole thing|body|entire car)\s*(?:please)?[.!]*$/i;
    var FLAKE_RE = /^\s*(?:and |now |also )?(?:add|put|give (?:it|them)|throw in|with|plus)\s+(?:a |some |some more |a bit of )?(?:([a-z]+) )?(?:metal ?flake|flake|sparkle|glitter|metallic flake|shimmer)s?\b(?:\s+(?:to|on) (?:it|them|that))?\s*[.!]*$/i;
    var REMOVE_X_RE = /^\s*(?:please\s+)?(?:remove|take (?:off|away)|get rid of|lose|drop|no more|kill|ditch|scrap)\s+(?:the |that |this |all the |those )?([a-z ]+?)(?:\s+off)?\s*(?:please)?[.!]*$/i;
    var EFFECT_RE = /^\s*(?:make it |a bit |a little |slightly |way |much )*(less|more|not so|not as|tone down the|calm down the|turn down the|turn up the)\s+(rainbow\w*|sparkl\w*|flak\w*|shimmer\w*|glitter\w*|holo\w*|chrome\w*|metal\w*|effect|pattern|texture|busy|loud|strong|intense|crazy|wild|much|of (?:it|that|the effect)|colou?rful|psychedelic)\b[^.]{0,20}[.!]*$/i;
    var MORECOL_RE = /^\s*(?:(?:and |but |now )?(?:make (?:it|them|the [a-z]+(?: [a-z]+)?) |go |with |add )?)?(?:(?:a )?(?:bit|little|touch|tad|lot) |slightly |much |some |a lot )?(?:more|with more|extra)\s+([a-z]+(?: [a-z]+)?)\s*(?:please|in it|to it)?\s*[.!]*$|^\s*(?:and |but )?(?:with|in) (?:some |a bit of |more )?([a-z]+)\s*[.!]*$/i;
    // HELPER FIX PASS 7 2026-10-05: fillers (then / i guess / maybe ...) are not the value ("Which part should I make white then?")
    function cvAskPart(say, pre, chips0) {
        var v = say ? String(say).toLowerCase().replace(/\b(?:make|paint|colou?r|turn|it|them|that|this|please|go|the|a|an|now|just|then|i guess|guess|i think|i suppose|maybe|probably|perhaps|ok|okay|instead|lets|let'?s|how about|go with|i'?d say|id say)\b/g, ' ').replace(/\s+/g, ' ').trim() : '';
        if (v && (v.split(' ').length > 3 || /\b(?:no|not|nah|thats|that'?s|too|so|looks?|like|its|it'?s|been|is|are|was|wide|narrow|much|big|small)\b/.test(v))) v = '';          // HELPER FIX PASS 7 2026-10-05 (blind5 b5-029/050: 'Which part should I make no thats too wide?'): a leftover that is not a short colour/finish is not the value
        return { cls: 'ASK', why: 'which-part', ask: { text: (pre ? pre + ' ' : '') + (v ? 'Which part should I make ' + v + '? Tap one, or say it.' : 'Which part should change, and to what? Tap one, or say it (for example “the roof black”).'), chips: chips0 || (v ? ['The roof', 'The hood', 'The sides', 'The whole car'].concat(/^[a-z]+$/.test(v) && !REL_RE.test(v) ? ['A ' + v + ' stripe down the middle'] : []) : ['Make the roof black', 'Make the hood white', 'Make the whole car blue', 'Show me looks for the body']) }, steps: [], pend: { need: 'part', say: say || null } };
    }
    function cvWhole(val, env) {          // "the whole car" as the answer to the helper's own question
        var v = String(val || '').replace(/^\s*(?:make|paint|colou?r|turn)\s+(?:it|them|that)?\s*/i, ''); if (!v) return null;
        var fr = null; try { fr = frameOps('make the car ' + v, { keep: [], only: [], keepColours: false }); } catch (e) { fr = null; }
        return fr && fr.ops && fr.ops.length ? cvDo(fr.ops, env, 'make the car ' + v, { via: 'convo', convo: 'whole' }) : null;
    }
    function mixHex(a, b, f) { var pa = parseInt(String(a).replace('#', ''), 16), pb = parseInt(String(b).replace('#', ''), 16); if (isNaN(pa) || isNaN(pb)) return a; var c = [16, 8, 0].map(function (sh) { var x = pa >> sh & 255, y = pb >> sh & 255; return Math.round(x + (y - x) * f); }); return '#' + c.map(function (v) { return ('0' + v.toString(16)).slice(-2); }).join(''); }
    function hasLook(act) { return !!(act && (act.lookObj || act.look || act.texture)); }
    function lookWordsOf(act) { var w = []; if (!act) return w; if (act.lookObj) w.push(act.lookObj.id || '', act.lookObj.label || ''); if (act.look) w.push(act.look); if (act.texture) w.push(act.texture.label || '', act.texture.name || '', act.texture.id || ''); return w.join(' ').toLowerCase(); }
    function npFilter(r, env) {          // a part with nothing to paint on THIS car (the ARCA spoiler is decal art): say so, change nothing there
        var np = env && env.noPaint; if (!np || !np.length || !r || !(r.steps || []).length) return r;
        var drop = r.steps.filter(function (st) { var w = st.what || {}; return w.k === 'part' && np.indexOf(w.part) !== -1; }); if (!drop.length) return r;
        var gone = function (st) { var w = st.what || {}; return drop.indexOf(st) !== -1 || (w.k === 'step' && drop.some(function (d) { return d === w.ref || (d.id != null && d.id === w.ref); })); };
        var keep = r.steps.filter(function (st) { return !gone(st); }), names = []; drop.forEach(function (st) { if (names.indexOf(st.what.part) === -1) names.push(st.what.part); });
        var why = 'The ' + names.join(' and the ') + (names.length > 1 ? ' have' : ' has') + ' nothing to paint on this car (it is decal art, not body paint), so I left ' + (names.length > 1 ? 'them' : 'it') + ' alone.';
        if (!keep.length) { var a = asked('nopaint', why + ' Pick another part:', ['The rear bumper', 'The trunk', 'The roof', 'The hood']); var act0 = r.act0 || null; if (!act0) { try { var pl0 = B().toPlan(drop, ''), cx0 = pl0 && pl0.ok && pl0.ed && Ed() && Ed().ctxOf ? Ed().ctxOf(pl0.ed) : null; act0 = cx0 ? cx0.act : null; } catch (eA) { act0 = null; } } a.nopaint = names; a.pend = { need: 'part', say: null, act: act0 }; return a; }          // the wanted change waits for a part ("same for the rear bumper")
        r.steps = keep; r.notDone = (r.notDone || []).concat(names.map(function (n) { return 'the ' + n + ' (nothing to paint there)'; })); r.nopaint = names; return r;
    }
    function convo(t, env, k0) {
        var s = String(t).toLowerCase().trim(), last = env && env.last && env.last.targets && env.last.targets.length ? env.last : null, pend = env && env.pending, topic = env && env.topic, pn = palNames(env, 3);
        // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "no not the spoiler, the bumpers" = the same change on the parts named last (never a loop on the first one)
        var rtm = RETARGET_RE.exec(s);
        if (rtm && k0 !== 'question') {
            var npc = cvParse(rtm[1]), ypc = cvParse(rtm[2]), negP = cvParts(npc), newP = cvParts(ypc);
            if (negP.length && newP.length) {
                var act0 = last ? last.act : (pend && pend.act ? pend.act : null), negN = negP.map(function (x) { return x.part; });
                var rr = (ypc && cvVal(ypc, true)) ? cvPlan(rtm[2], newP, env) : (act0 ? cvCopy(act0, newP, env, s) : (pend && pend.say ? cvPlan(pend.say, newP, env) : null));
                if (rr) { rr.undoFirst = !!(last && cvPartsOf(last).some(function (q) { return negN.indexOf(q) !== -1; })); rr.via = 'convo'; rr.convo = 'retarget'; return rr; }
                return cvAskValue(newP.map(function (x) { return x.part; }));
            }
        }
        if (NOPE_RE.test(s) || OTHER_RE.test(s) || REMOVE_IT_RE.test(s) || /\b(?:undo|redo|take (?:it|that) back|put (?:it|that) back)\b/i.test(s)) return null;
        if (CHG_RE.test(s)) return cvAskPart(null);          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "change the color" = which part first
        if (CAR_RE.test(s)) { var ca = asked('car-value', 'What should the car be? Tap one, or type a colour or a look.', ['Make the car blue', 'Make the car red', 'Make the car matte black', 'Show me looks for the body']); ca.pend = { need: 'car' }; return ca; }
        // 1. vague asks: a question back with chips, never a car-wide guess or an unrelated card
        for (var vi = 0; vi < CV_VAGUE.length; vi++) {
            var vm = CV_VAGUE[vi][0].exec(s); if (!vm) continue; var vk = CV_VAGUE[vi][1], L = last ? lastLabel(last) : '';
            if (vk === 'shine') return asked('shine', 'Which way should the shine go' + (L ? ' on the ' + L : '') + '? Tap one.', L ? ['Make the ' + L + ' glossier', 'Make the ' + L + ' less shiny', 'Make the ' + L + ' matte', 'Make the ' + L + ' chrome'] : ['Make it glossier', 'Make it less shiny', 'Make it matte', 'Show me looks for the body']);
            if (vk === 'pop') return asked('vague', (/pop|stand out/.test(s) ? 'Pop how?' : 'What kind of look?') + ' Pick one to start' + (L ? ' (it goes on the ' + L + ')' : '') + ', or describe it.', L ? ['Make the ' + L + ' brighter', 'Make the ' + L + ' metallic', 'Make the ' + L + ' candy', 'Show me looks for the body'] : ['Make the colours brighter', 'Make it metallic', 'Make it candy red', 'Show me looks for the body']);
            if (vk === 'vague') return asked('vague', 'What kind of change? Pick one to start, or describe it (for example “candy red with a black hood”).', VAGUE_CHIPS);
            if (vk === 'apply') { if (topic && topic.say) return asked('apply', 'Where should the ' + topic.say + ' go?', ['Make the car ' + topic.say, 'Make the hood ' + topic.say, 'Make the roof ' + topic.say]); return asked('apply', 'Which finish, and where? Pick one, or say it (for example “make the hood chrome”).', ['Make the car chrome', 'Make the car candy red', 'Make the car matte black', 'Show me looks for the body']); }
            if (vk === 'middle') return asked('middle', 'Put what in the middle? Tap one, or say it.', ['Add a stripe down the middle', 'How do I add a number?', 'How do I add a logo?']);
            if (vk === 'place') { if (pend || (last && cvPick(s, cvPool(cvPartsOf(last))).length)) break; var pl = CV_PLACE[vm[1]] || ['hood', 'roof']; return asked('place', 'What should change on the ' + vm[1] + '? Tap one, or say it (for example “make the ' + pl[0] + ' black”).', pl.map(function (p) { return 'Make the ' + p + ' black'; }).concat(['Show me looks for the ' + (/side/.test(pl[1]) ? 'sides' : pl[1])])); }
            if (vk === 'stripe') { var sc0 = vm[1].replace(/\b(?:please|instead|now)\b/g, '').trim(); return asked('stripe', 'Which stripe? A stripe drawn with the stripe tool is its own zone: select it and set its colour. Or tell me the stripe’s colour now (for example “make the white stripe ' + sc0 + '”).', pn.slice(0, 2).map(function (n) { return 'Make the ' + n + ' stripe ' + sc0; }).concat(['How do I change a stripe colour?'])); }
        }
        if (k0 === 'question') return null;
        var pc = cvParse(s); if (!pc) return null;
        var parts = cvParts(pc), hasVal = cvVal(pc), whole = CV_WHOLE_RE.test(s);
        // 2. the helper's own open question
        if (pend && pend.need === 'which') {
            var pk = cvPick(s, pend.cands);
            if (pk.length && !parts.filter(function (x) { return pend.cands.indexOf(x.part) === -1; }).length) {
                var rest = cvRest(s), rpc = rest ? cvParse(rest) : null, tg1 = pk.map(cvTg);
                if (rpc && cvVal(rpc)) return cvPlan(rest, tg1, env) || cvAskValue(pk);
                if (pend.act) return cvCopy(pend.act, tg1, env, s) || cvAskValue(pk);
                if (pend.say) return cvPlan(pend.say, tg1, env) || cvAskValue(pk);
                return cvAskValue(pk);
            }
        }
        if (pend && pend.need === 'value' && pend.parts && pend.parts.length && hasVal && !parts.length && !whole) { var pv = cvPlan(s, pend.parts.map(cvTg), env); if (pv) return pv; }
        // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: the helper asked WHICH PART ("change the color" / "orange" / "make it lighter" with nothing to point at): the answer fills that slot
        if (pend && pend.need === 'car' && hasVal && !parts.length) { var cw = cvWhole(s, env); if (cw) return cw; }
        if (pend && pend.need === 'part') {
            if (parts.length) {
                if (!hasVal && pend.act) { var pa0 = cvCopy(pend.act, parts, env, s); if (pa0) return pa0; }
                if (!hasVal && pend.say) { var pp = cvPlan(pend.say, parts, env, { via: 'convo', convo: 'part' }); if (pp) return pp; }
                if (!hasVal) return cvAskValue(parts.map(function (x) { return x.part; }));
            } else if (whole && !pc.colours.length && !pc.looks.length && pend.say) { var pw = cvWhole(pend.say, env); if (pw) return pw; }
            else if (hasVal && !whole && !pc.targets.length) return cvAskPart(s);
            else if (pend.say && /\b(?:down the middle|in the middle|middle|centre|center|along the sides?|on the sides?)\b/i.test(s) && !REL_RE.test(String(pend.say))) return { cls: 'DO', pass: 'send', say: 'add a ' + cvRest(pend.say) + ' stripe ' + (/side/i.test(s) ? 'along the sides' : 'down the middle'), steps: [] };
        }
        // 3. one bumper named without saying which: ask (and keep the value / the copy for the answer)
        if (/\bbumper\b/i.test(s) && !/\bbumpers\b/i.test(s) && !/\b(?:front|rear|back|both|all|each)\b[^.,;]{0,14}\bbumper\b/i.test(s) && !whole) {
            var other = parts.filter(function (x) { return !/bumper/.test(x.part || ''); });
            if (!other.length && (hasVal || !last || !CV_COPY_RE.test(s))) return cvWhich(s, hasVal ? s : null, null);
            if (!other.length && last && CV_COPY_RE.test(s)) return cvWhich(s, null, last.act);
        }
        // 4. "both" = the pair the conversation is about
        if (last && /\bboth\b/i.test(s) && !parts.length && !whole) {
            var pool = cvPool(cvPartsOf(last)), bp = pool.length ? pool : cvPartsOf(last);
            if (bp.length >= 2) { var br = cvRest(s), bpc = br ? cvParse(br) : null; if (bpc && cvVal(bpc)) { var bv = cvPlan(br, bp.map(cvTg), env); if (bv) return bv; } else if (CV_COPY_RE.test(s) || !br) { var bc = cvCopy(last.act, bp.map(cvTg), env, s); if (bc) return bc; } }
        }
        if (topic && topic.say && parts.length && !hasVal && (CV_COPY_RE.test(s) || /\b(?:that|it|this)\b/i.test(s)) && !whole) { var tr = cvPlan('make it ' + topic.say, parts, env, { via: 'convo', convo: 'topic' }); if (tr) return tr; }
        // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "the sides only" / "just the roof" after a change = that change moved there (the first one taken back)
        var onm = last && !hasVal && parts.length && !whole ? CV_ONLY_RE.exec(s) : null;
        if (onm) { var lp0 = cvPartsOf(last), pN = parts.map(function (x) { return x.part; }), out0 = last.targets.some(function (x) { return x.kind !== 'part' || pN.indexOf(x.part) === -1; }); var oc = cvCopy(last.act || {}, parts, env, s); if (oc) { oc.undoFirst = out0 && !/\b(?:a little|a bit|a touch|a tad|some|also|too|as well|more|extra)\b/i.test(s); oc.convo = oc.undoFirst ? 'only' : 'add'; return oc; } }          // HELPER FIX PASS 7 2026-10-05: "just a little on the hood" ADDS to the last change (b5-060 took the whole-car change back)
        if (!last) {
            // a relative edit or a bare value with nothing to point at: ASK which part (never the whole car)
            if (!parts.length && !whole && !pc.targets.length && k0 !== 'question') {
                var relq = REL_RE.test(s) || CV_LESS_RE.test(s) || CV_SIZE_RE.test(s) || EFFECT_RE.test(s), bare = hasVal && s.split(/\s+/).length <= 3 && !/\b(?:make|paint|turn|colou?r|change|give|put|add|go|do|it|them|everything|car|look|finish|style)\b/i.test(s);
                var npl = env && env.nopaintLast && env.nopaintLast.length ? 'The ' + env.nopaintLast.join(' and the ') + ' has nothing to paint on this car, so nothing changed there.' : '';
                if (relq || (bare && env && env.inConvo) || (npl && hasVal)) return cvAskPart(s, npl);
            }
            if (env && env.undone && env.undone.targets && env.undone.targets.length && hasVal && !parts.length && !whole && !pc.targets.length && /\b(?:it|that|this|them)\b/i.test(s)) { var ul = lastLabel(env.undone), vv = cvRest(s.replace(/\b(?:make|paint|turn|it|that|this|them)\b/gi, ' ')) || 'that'; return asked('undone', 'Make what ' + vv + ': the ' + ul + ' again, or the whole car?', ['Make the ' + ul + ' ' + vv, 'Make the whole car ' + vv]); }
            return null;
        }
        var lp = cvPartsOf(last), la = last.act || {};
        // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "remove the flake" right after adding it = take that change back
        var rmx = REMOVE_X_RE.exec(s);
        if (rmx && !parts.length && !whole) { var xw = rmx[1].replace(/\b(?:effect|look|finish|stuff|bit|bits|one)\b/g, '').trim(); if (xw && (lookWordsOf(la).indexOf(xw.replace(/s$/, '')) !== -1 || (/flake|sparkle|glitter|shimmer|metal/.test(xw) && /metallic|flake/.test(lookWordsOf(la))) || /^(?:it|that|this|change|last change|colou?r)$/.test(xw))) return { cls: 'DO', pass: 'undo' }; }
        // "add gold flake": the flake goes onto what was just painted, the colour stays
        var flm = FLAKE_RE.exec(s);
        if (flm && !parts.length && !whole) { var mlook = Ed().lookFor('metallic'); if (mlook) { var fc = cvCopy(la.colour || hasLook(la) ? la : { colour: null, keep: true }, last.targets, env, s, { look: JSON.parse(JSON.stringify(mlook)) }); if (fc) { fc.convo = 'flake'; if (flm[1]) fc.steps[0].note = (fc.steps[0].note ? fc.steps[0].note + ' ' : '') + 'A ' + flm[1] + ' flake on top of the ' + ((la.colour && la.colour.name) || 'current') + ' colour.'; return fc; } } }
        // "less rainbow" / "tone down the sparkle" / "more": the same look, weaker / stronger
        var efm = EFFECT_RE.exec(s);
        if ((efm || (/^\s*(?:a (?:bit|little) )?(?:more|less)(?: please)?\s*[.!]*$/i.test(s) && hasLook(la))) && hasLook(la) && !parts.length && !whole) {
            var weaker = efm ? /less|not so|not as|tone down|calm down|turn down/i.test(efm[1]) : /less/i.test(s), cur = la.strength || 1, sm = Math.round(Math.max(0.2, Math.min(1, weaker ? cur * 0.6 : cur * 1.5)) * 100) / 100;
            if (!weaker && cur >= 1) return asked('stronger', 'The ' + lastLabel(last) + ' already has the full-strength look. Pick a bolder one, or keep it:', ['Make the ' + lastLabel(last) + ' chrome', 'Show me looks for the ' + lastLabel(last), 'Undo']);
            var ec = cvCopy(la, last.targets, env, s, { strengthMul: sm }); if (ec) { ec.convo = 'strength'; return ec; }
        }
        // "with more gold" on a look = the look in gold; "more yellow" on a colour = the colour moved toward yellow
        var mcm = MORECOL_RE.exec(s), mcol = mcm && pc.colours.length ? pc.colours[pc.colours.length - 1] : null;
        if (mcol && !pc.targets.some(function (x) { return x.kind === 'part'; }) && !whole && !pc.looks.length) {
            if (hasLook(la) && !(la.colour && la.colour.hex) && last.targets.some(function (x) { return x.kind === 'body'; })) {          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: in-app b4-145 "make it a rattlesnake look" -> "with more gold" repainted the WHOLE car flat gold under the snake shine; a whole-car look that kept the paint gets the catalogue's gold versions of that look to pick (nothing changes until Run)
                var lkn = String((la.texture && (la.texture.label || la.texture.name)) || (la.lookObj && (la.lookObj.label || la.lookObj.id)) || la.look || '').toLowerCase(), lsc = lkn ? lookStep(lkn + ' ' + String(mcol.name || ''), env) : null;
                if (lsc) { lsc[0].note = 'Your colours stay as they are: pick a ' + mcol.name + ' ' + lkn + ' look below (nothing changes until ▶ Run), or say “make the whole car ' + mcol.name + '” to repaint it.'; var lr = stepsResult(lsc, { look: true, via: 'convo' }); lr.convo = 'look+colour-pick'; return lr; }
            }
            if (hasLook(la)) { var lc = cvCopy(la, last.targets, env, s, { colour: JSON.parse(JSON.stringify(mcol)) }); if (lc) { lc.convo = 'look+colour'; return lc; } }
            else if (la.colour && la.colour.hex && mcol.hex) { var mx = { name: (la.colour.name || 'colour') + ' with more ' + (mcol.name || 'colour'), hex: mixHex(la.colour.hex, mcol.hex, 0.4), at: 0, qual: null, exact: true }; var mr = cvDo(last.targets.map(function (tg) { return { target: tg, colour: JSON.parse(JSON.stringify(mx)), look: null, texture: null, rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, ext: null }; }), env, s); if (mr) { mr.convo = 'mix'; return mr; } }
        }
        // 5. "a bit less" / "more" after a shade change: the same zone, a smaller / bigger step
        var lm = CV_LESS_RE.exec(s);
        if (lm) {
            var a0 = last.act || {};
            if (a0.shadeDir && a0.colour && a0.colour.hex) { var more = /more/i.test(lm[1]), d = more ? a0.shadeDir : -a0.shadeDir, base = String(a0.colour.name || 'colour').replace(/^(?:(?:a bit |slightly )?(?:darker|lighter|brighter|deeper|paler) )+/i, ''); var col = { name: (more ? (d < 0 ? 'even darker ' : 'even lighter ') : (d < 0 ? 'a bit darker ' : 'a bit lighter ')) + base, hex: shadeHex(a0.colour.hex, d * (more ? 0.15 : 0.12)), at: 0, qual: null, exact: true }; return cvDo(last.targets.map(function (tg) { return { target: tg, colour: JSON.parse(JSON.stringify(col)), look: null, texture: null, rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, ext: null, shadeDir: a0.shadeDir }; }), env, s); }
            if (!a0.dir) { var L2 = lastLabel(last); return asked('less', (/more/i.test(lm[1]) ? 'More of what' : 'Less of what') + ' on the ' + L2 + '? Tap one.', ['Make the ' + L2 + ' a bit lighter', 'Make the ' + L2 + ' a bit darker', 'Make the ' + L2 + ' less shiny', 'Undo']); }
            return null;
        }
        // 6. size: "smaller" / "make it bigger" = the pattern just made, at a new scale
        var szm = CV_SIZE_RE.exec(s);
        if (szm && !pc.colours.length && !pc.looks.length && !whole && (!parts.length || parts.every(function (x) { return lp.indexOf(x.part) !== -1; }))) {
            var a1 = last.act || {}, L3 = lastLabel(last);
            if (a1.texture || (a1.lookObj && a1.lookObj.id === 'ext')) { var dn = /smaller|finer|tighter|tinier|shrink|down|zoom out/i.test(szm[1]), bit = /\b(?:a (?:bit|little|touch|tad)|slightly|little)\b/i.test(s), cur = a1.scale || 1, mul = Math.round(cur * (dn ? (bit ? 0.8 : 0.6) : (bit ? 1.25 : 1.6)) * 100) / 100; mul = Math.max(0.2, Math.min(4, mul)); return cvCopy(a1, last.targets, env, s, { scaleMul: mul }); }
            return asked('scale', 'The ' + L3 + ' has no pattern to resize. To resize a pattern, select its zone and move its Scale slider (smaller = finer).', ['Put carbon fiber on the ' + L3, 'How do I scale a pattern?']);
        }
        // 8. copy: "the hood too", "same for the trunk", "and the rear one", "and the left"
        var pick = parts.length ? [] : cvPick(s, cvPool(lp).filter(function (p) { return lp.indexOf(p) === -1; }));
        var newTg = parts.length ? parts : pick.map(cvTg);
        if (newTg.length && !whole && !newTg.every(function (x) { return lp.indexOf(x.part) !== -1; })) {
            var rest2 = parts.length ? '' : cvRest(s), rpc2 = rest2 ? cvParse(rest2) : null;
            var hv8 = parts.length ? hasVal : !!(rpc2 && cvVal(rpc2));
            if (pick.length && hv8) { var pr = cvPlan(rest2, newTg, env); if (pr) return pr; }
            if (!hv8 && (CV_COPY_RE.test(s) || (pick.length && !rest2))) { var cp = cvCopy(last.act || {}, newTg, env, s); if (cp) return cp; }
        }
        // 9. a value with no part: the parts just changed ("make it matte", "actually glossy", "white"), never the whole car
        if (cvVal(pc, true) && !pc.targets.length && !whole && !/\b(?:and|but|with|except|not)\b/i.test(s)) { var fv = cvPlan(s, last.targets, env); if (fv) return fv; }
        return null;
    }
    var SYMPTOM_RE = /\b(?:is|are|got|went|keeps?|still|now)\s+(?:gone|missing|disappeared|vanished|showing|not showing|wrong|broken|blank|invisible|there)\b|\bshows? up\b|\b(?:gone|missing|disappeared|vanished)\b[^.]{0,40}\bafter\b|\bafter i\b[^.]{0,40}\b(?:gone|missing|disappeared|vanished|broke|wrong)\b/i;
    var EDIT_START_RE = /^\s*(?:please\s+|can you\s+|could you\s+)?(?:make|paint|colou?r|turn|put|add|give|change|set|apply|use|do|go|recolou?r|spray|wrap|swap|replace)\b/i;
    var NOISE_RE = /\b(camo\w*|camouflage|chameleon|carbon(?: fib(?:er|re))?|flake|splatter\w*|marble\w*|galaxy|snake ?skin|candy|chrome|holo\w*|pearl\w*|metal\w*|matte|satin|flames?|tiger|zebra|leopard|hex\w*|honeycomb|tie ?dye|psychedelic|neon|rainbow)\s+(?:paint ?job|paint|scheme|style|vibe|effect|look|finish|type|design|theme|thing)\b/gi;
    function denoise(t) { return String(t).replace(/\s+all over(?: the car| it)?\b/gi, ' on the whole car').replace(/\b(chameleon|flip ?flop|flip|pearl\w*|iridescent)\s+colou?r[- ]?(?:shift(?:ing|s)?|chang(?:ing|e|es))\b/gi, '$1').replace(NOISE_RE, '$1').replace(/\s{2,}/g, ' '); }
    var ACC2_RE = /^\s*(?:(?:make|paint|do|give me|i want|id like|i'd like)\s+(?:it|the car|my car|the body)?\s*)?(?:an? )?(.+?)\s+(?:car|body|base|paint ?job|livery)?\s*with\s+(?:some\s+|a few\s+)?([a-z]+(?: [a-z]+)?)\s+(accents?|trim|details?|highlights?|touches)\s*[.!]*$/i;
    function accents2(t, env) {          // HELPER_V2 fix pass 4: "matte black car with red accents" painted the car maroon (the accent colour read as a source colour)
        var m = ACC2_RE.exec(t); if (!m) return null;
        var base = m[1].replace(/^(?:the|my|a|an)\s+/i, ''), col = m[2], bpc = cvParse(base), cpc = cvParse(col);
        if (!bpc || !cvVal(bpc) || cvParts(bpc).length || !cpc || !cpc.colours.length) return null;
        var fr = null; try { fr = frameOps('make the car ' + base, { keep: [], only: [], keepColours: false }); } catch (e) { fr = null; }
        if (!(fr && fr.ops && fr.ops.length && !fr.notDone.length && fr.ops.every(function (o) { return o.target && /^(?:body|whole|car)$/.test(o.target.kind); }))) return null;
        var r = cvDo(fr.ops, env, t, { via: 'accents' }); if (!r) return null;
        var cn = cpc.colours[0].name || col, chips = ['Make the spoiler ' + cn, 'Make the front and rear bumpers ' + cn, 'Add a ' + cn + ' pinstripe'];
        r.notDone = [col + ' ' + m[3]]; r.chips = chips;
        r.steps[0].note = (r.steps[0].note ? r.steps[0].note + ' ' : '') + '“' + col + ' ' + m[3] + '” is not one part of the car: tap where the ' + cn + ' goes after this runs.';
        return r;
    }
    function kept0(t) { return NEG_START.test(t); }
    // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: everyday relative words -> the ones the edit brain knows ("thats too dark" = lighter, "kill the shine on the roof" = a matte roof)
    var TOO_MAP = { dark: 'lighter', deep: 'lighter', dull: 'brighter', light: 'darker', bright: 'darker', pale: 'darker', 'washed out': 'darker', shiny: 'less shiny', glossy: 'less shiny', matte: 'glossier', flat: 'glossier', big: 'smaller', small: 'bigger', busy: 'less busy', loud: 'less busy' };
    function relx(t) {
        var s = String(t);
        s = s.replace(/^\s*(?:perfect|great|nice|cool|awesome|good|love it|sweet|ok(?:ay)?|alright|thanks|thank you|yes|yeah|yep)[,.!]*\s+(?:now\s+|and\s+|then\s+)?(?=[a-z])/i, '');
        s = s.replace(/^\s*(?:(?:hmm+|um+|no|ok|actually)[\s,]+)*(?:that'?s|thats|it'?s|its|that is|it is|they'?re|theyre|looks|it looks|that looks)\s+(?:a (?:bit|little|touch|tad) |way |much |kinda |kind of |sort of |just )?too (dark|deep|dull|light|bright|pale|washed out|shiny|glossy|matte|flat|big|small|busy|loud)\b\s*[.!]*$/i, function (m, w) { return 'make it ' + TOO_MAP[w.toLowerCase()]; });
        var km = /^\s*(?:please\s+)?(?:kill|remove|take off|take away|lose|knock down|get rid of|drop|cut|lose)\s+(?:the |all the |its |that )?(?:shine|gloss|shininess|reflections?)(?:\s+off)?(?:\s+(?:on|of|from)\s+(?:the |my )?(.+?))?\s*[.!]*$/i.exec(s);
        if (km) s = km[1] ? 'make the ' + km[1] + ' matte' : 'make it matte';
        s = s.replace(/\bbrighter\b/gi, 'lighter').replace(/\bpaler\b/gi, 'lighter').replace(/\b(?:deeper|richer)\b/gi, 'darker');
        return s;
    }
    function topicOf(text) { var pc = cvParse(String(text || '').replace(/\b(?:how do i|how to|how can i|what is|whats|what's|make|get|do|a|an|the|finish|paint|look|effect)\b/gi, ' ')); if (!pc) return null; var w = pc.looks.length ? (pc.looks[0].id || '') : (pc.texture ? (pc.texture.label || '') : (pc.ext && knownTerm(pc.ext) ? pc.ext : '')); w = String(w).trim(); return w ? { say: w } : null; }

    // ================================================================== HELPER FIX PASS 7 2026-10-05 (blind round 5: 63% / 23% strict / 5 HARMFUL; owner: "Needs to be MUCH smarter")
    // Failure CLASSES, not items: (1) a thin line / trim / outline around a part became a whole-car fill, a part gradient became a whole-car solid, a refinement replaced
    // the change before it; (2) questions ran as edits; (3) "doors stay what they are" needed a pick; (5) garbled templates; (6) "something else" / "use the second one" /
    // "save it" were not remembered; (7) "looks plastic", "see me from across the track", "sponsors hard to read" got unrelated cards. Tuned on _easy_claude_work/eval/fix7/dev.jsonl.
    var P7_PART_RE = /\b(front bumper|rear bumper|back bumper|left side|right side|bumpers?|sides|side|doors?|hood|bonnet|roof|trunk|boot|deck ?lid|spoiler|wing)\b/gi;
    function p7PartsOf(t) {          // the parts a sentence NAMES (explicit words only: "the other side" names no part)
        var out = [], add = function (p) { if (out.indexOf(p) === -1) out.push(p); }, s = String(t || '').toLowerCase().replace(/\b(?:the )?other side\b/g, ' '), m;
        P7_PART_RE.lastIndex = 0;
        while ((m = P7_PART_RE.exec(s))) {
            var w = m[1];
            if (/^(?:sides|side|doors?)$/.test(w)) { add('left side'); add('right side'); }
            else if (/^bumpers?$/.test(w)) { add('front bumper'); add('rear bumper'); }
            else if (w === 'back bumper') add('rear bumper');
            else if (w === 'bonnet') add('hood'); else if (/^(?:boot|deck ?lid)$/.test(w)) add('trunk'); else if (w === 'wing') add('spoiler');
            else add(w);
        }
        return out;
    }
    var P7_WHOLE_RE = /\b(?:whole|entire|all over|everything|everywhere|full car|car-?wide|(?:the|my|this) (?:car|body|paint)|the rest)\b/i;
    function p7The(ps) { var n = cvName(ps); return /^both\b/.test(n) ? n : 'the ' + n; }
    function p7Hex(name) { var c = colourObj(name); return c && c.hex ? c : null; }
    function p7Colours(t) {          // the colour words in the order they are SAID ("from black into red" = black, then red)
        var out = [], re = new RegExp('\\b(?:(?:dark|light|deep|bright|pale|neon|candy|metallic)\\s+)?(?:' + COLOUR_WORDS + ')\\b', 'gi'), m;
        while ((m = re.exec(String(t || '')))) { var c = p7Hex(m[0].toLowerCase()); if (c) out.push({ name: m[0].toLowerCase(), hex: c.hex, at: m.index }); }
        return out;
    }
    function p7PartColour(part, env) {          // what the part shows now: the colour this chat painted on it, else nothing known
        var mem = env && env.colMem; if (mem && mem[part] && mem[part].hex) return { name: mem[part].name || 'current colour', hex: mem[part].hex };
        var la = env && env.last; if (la && la.act && la.act.colour && la.act.colour.hex && (la.targets || []).some(function (x) { return x.part === part || x.kind === 'body'; })) return { name: la.act.colour.name || 'current colour', hex: la.act.colour.hex };
        return null;
    }
    function p7Step(part, colour, extra, note) {
        var Bb = B(), st = Bb.newStep({ what: part === 'body' ? { k: 'body', tg: { kind: 'body' } } : { k: 'part', part: part, tg: { kind: 'part', part: part, at: 0 } }, act: 'recolour', colour: { name: colour.name, hex: colour.hex, at: 0, qual: null, exact: true } });
        if (extra) st.extra = JSON.parse(JSON.stringify(extra)); if (note) st.note = note; return st;
    }
    function p7Ask(why, text, chips, pend) { var a = asked(why, text, chips); if (pend) a.pend = pend; return a; }
    function p7LastParts(env) { var l = env && env.last; return l && l.targets ? l.targets.filter(function (x) { return x.kind === 'part' && x.part; }).map(function (x) { return x.part; }) : []; }
    var P7_REF_RE = /\b(?:it|its|it'?s|that|them|those|this|their)\b/i;

    // (1a) OUTLINE / TRIM / EDGE around a part = a real line along that part's edge (js/spb-pro-graphics.js kind "outline"), never a fill
    var P7_OUTLINE_RE = /\b(?:outlin(?:e|es|ed|ing)|border(?:s|ed)?|edg(?:e|es|ed|ing)|trim(?:med|s)?|rim|framed?|piping|perimeter)\b/i;
    var P7_LINE_RE = /\b(?:lines?|stripes?|pin ?stripes?|tape|band)\b/i;
    function p7Outline(t, env) {
        var s = String(t || '');
        if (!(P7_OUTLINE_RE.test(s) || (P7_LINE_RE.test(s) && /\b(?:around|round|all round|along the edges?|edges?|border|perimeter)\b/i.test(s)))) return null;
        if (/\b(?:numbers?|sponsors?|logos?|decals?|lettering|stripes? (?:colou?r|red|white|black))\b/i.test(s) && !/\b(?:hood|roof|trunk|spoiler|bumper|side|door)/i.test(s)) return null;          // "number outline white" = the number layer's own outline (the edit brain does that)
        if (/\bwith\b[^.]{0,30}\btrim\b/i.test(s) && (P7_WHOLE_RE.test(s) || !p7PartsOf(s).length)) return null;          // "black car with gold trim" = accents (accents2)
        var parts = p7PartsOf(s); if (!parts.length && P7_REF_RE.test(s)) parts = p7LastParts(env);
        var cols = p7Colours(s), w = /\b(?:thin|skinny|fine|narrow|hairline|pin|small|little|slim)\b/i.test(s) ? 0.012 : (/\b(?:thick|wide|fat|bold|big|heavy)\b/i.test(s) ? 0.035 : 0.02);
        var wn = w < 0.015 ? 'thin' : (w > 0.03 ? 'thick' : '');
        if (!parts.length && cols.length >= 2 && /\bor\b/i.test(s)) return p7Ask('outline-choice', 'Both ' + cols[0].name + ' and ' + cols[1].name + ' work as trim; ' + cols[0].name + ' reads cooler, ' + cols[1].name + ' warmer. Trim is a line around ONE part: tap one to try (Undo takes it off).', ['Add a ' + (wn ? wn + ' ' : '') + cols[0].name + ' outline around the hood', 'Add a ' + (wn ? wn + ' ' : '') + cols[1].name + ' outline around the hood', 'Add a ' + (wn ? wn + ' ' : '') + cols[0].name + ' outline around the roof', 'Add a ' + (wn ? wn + ' ' : '') + cols[1].name + ' outline around the roof']);
        if (!parts.length) return p7Ask('outline-part', 'An outline goes around one part of the car. Which part should get the ' + (wn ? wn + ' ' : '') + (cols[0] ? cols[0].name + ' ' : '') + 'line?', ['hood', 'roof', 'trunk'].map(function (p) { return 'Add a ' + (wn ? wn + ' ' : '') + (cols[0] ? cols[0].name : 'black') + ' outline around the ' + p; }));
        if (!cols.length) return p7Ask('outline-colour', 'What colour should the line around the ' + cvName(parts) + ' be?', ['black', 'white', 'gold'].map(function (c) { return 'Add a ' + (wn ? wn + ' ' : '') + c + ' outline around the ' + cvName(parts); }));
        var c = cols[cols.length - 1], note = 'A ' + (wn ? wn + ' ' : '') + c.name + ' line around the edge of ' + p7The(parts) + ' only: the rest of ' + p7The(parts) + ' keeps its paint, and your numbers and sponsors stay on top.';
        var sts = parts.map(function (p, i) { return p7Step(p, c, { outline: { w: w } }, i ? '' : note); }); B().check(sts, env);
        var nv = never(sts, {}, []); if (!nv.steps.length) return null;
        nv.steps.forEach(function (x) { if (x.extra) x.extra.outline = { w: w }; });
        var r = stepsResult(nv.steps, { via: 'outline' }); r.cls = nv.steps.some(B().stepOpen) ? 'PREFILL' : 'DO'; return r;
    }

    // (1b) a GRADIENT / FADE on a named part = a gradient zone on that part (zone-kit gradient, fitted to the part, oriented by the car map), never a solid fill
    var P7_GRAD_RE = /\b(?:gradients?|fad(?:e|es|ed|ing)|ombre|blend(?:s|ed|ing)?\s+(?:in)?to|melt(?:s|ing)?\s+into|transition(?:s|ing)?\s+(?:in)?to)\b/i;
    var P7_FROMTO_RE = new RegExp('\\bfrom\\s+(?:(?:dark|light|deep|bright|pale|neon)\\s+)?(?:' + COLOUR_WORDS + ')\\b.{0,40}\\b(?:to|into)\\b', 'i');
    function p7Grad(t, env) {
        var s = String(t || ''), pend = env && env.pending && env.pending.need === 'gradient' ? env.pending : null;
        if (!P7_GRAD_RE.test(s) && !P7_FROMTO_RE.test(s) && !(pend && p7Colours(s).length)) return null;
        if (/\b(?:numbers?|sponsors?|logos?)\b/i.test(s)) return null;
        var parts = p7PartsOf(s); if (!parts.length && pend) parts = pend.parts.slice(); if (!parts.length && P7_REF_RE.test(s)) parts = p7LastParts(env);
        if (!parts.length || (P7_WHOLE_RE.test(s) && !p7PartsOf(s).length)) return null;          // a whole-car fade: the app's own design path
        var cols = p7Colours(s), clear = /\b(?:nothing|clear|transparent|the paint|(?:its|the) (?:own|current|base) colou?r|what it is)\b/i.test(s);
        var axis = /\b(?:top|bottom|up|down|roof ?line|rocker|belt ?line|high|low)\b/i.test(s) ? 'height' : 'length';
        var start = axis === 'height' ? 'top' : 'front';
        if (axis === 'length' && /\bfrom the (?:back|rear|tail)\b|\b(?:back|rear) to (?:the )?front\b|\btoward(?:s)? the front\b/i.test(s)) start = 'rear';
        var lead = [];
        if (axis === 'height') {          // "blue at the bottom to nothing at the top" / "from the bottom up": which colour sits at which end
            if (/\bfrom the bottom\b|\bbottom to (?:the )?top\b|\bbottom up\b|\bat the bottom\b[^.]*\b(?:to|into)\b/i.test(s)) start = 'bottom';
        }
        var a = null, b = null;
        if (cols.length >= 2) { a = cols[0]; b = cols[1]; }
        else if (cols.length === 1) {
            var cur = p7PartColour(parts[0], env), towardEnd = /\b(?:to|into|toward(?:s)?)\s+(?:(?:dark|light|deep|bright|pale|neon)\s+)?(?:' + COLOUR_WORDS + ')/i;
            var one = cols[0], intoOne = new RegExp('\\b(?:to|into|toward(?:s)?)\\s+(?:(?:dark|light|deep|bright|pale|neon)\\s+)?' + one.name.split(' ').pop() + '\\b', 'i').test(s) && !/\bfrom\s/i.test(s.slice(0, one.at));
            if (clear || cur) { var other = cur || { name: 'the paint under it', hex: null }; if (intoOne && !clear) { a = other; b = one; } else { a = one; b = other; } }
            if (!cur) { a = null; b = null; }
        }
        if (!a || !b || !a.hex || !b.hex) {
            var nm = cvName(parts), c0 = cols[0] ? cols[0].name : 'blue';
            return p7Ask('gradient', 'A fade on the ' + nm + ' needs two colours' + (clear ? ' (a fade into “nothing” is not something the paint can do: pick the colour it fades into)' : (cols.length === 1 ? ': I know the ' + c0 + ', but not the colour the ' + nm + ' has now' : '')) + '. Which two?', ['Fade the ' + nm + ' from ' + c0 + ' to white', 'Fade the ' + nm + ' from ' + c0 + ' to black', 'Fade the ' + nm + ' from ' + c0 + ' to silver'], { need: 'gradient', parts: parts.slice() });
        }
        var g = { from: a.hex, to: b.hex, axis: axis, start: start, names: [a.name, b.name] }, ends = axis === 'height' ? (start === 'bottom' ? ['bottom', 'top'] : ['top', 'bottom']) : (start === 'rear' ? ['back', 'front'] : ['front', 'back']);
        var note = 'A fade on ' + p7The(parts) + ' only: ' + a.name + ' at the ' + ends[0] + ' into ' + b.name + ' at the ' + ends[1] + '. The rest of the car keeps its paint; numbers and sponsors stay on top.';
        var sts = parts.map(function (p, i) { return p7Step(p, { name: a.name + ' to ' + b.name + ' fade', hex: a.hex }, { gradient: g }, i ? '' : note); }); B().check(sts, env);
        var nv = never(sts, {}, []); if (!nv.steps.length) return null;
        nv.steps.forEach(function (x) { if (x.extra) x.extra.gradient = JSON.parse(JSON.stringify(g)); });
        var r = stepsResult(nv.steps, { via: 'gradient' }); r.cls = nv.steps.some(B().stepOpen) ? 'PREFILL' : 'DO'; return r;
    }

    // (2) QUESTIONS are answers first; "show me the matte ones" = a LIST of real catalogue finishes (nothing changes); "use the second one" picks from that list
    var P7_Q_RE = /^\s*(?:(?:hey|hi|so|ok|okay|um+|uh+|yo|quick question|question|and|but|also|wait)[\s,:!?]+)*(?:is|are|was|were|isnt|isn'?t|arent|aren'?t|does|doesnt|doesn'?t|which|whats|what'?s|what(?!\s+about\b)|wat|whats the difference|difference|how (?:is|are|does|do|much|many|come)|why)\b/i;
    var P7_Q2_RE = /\b(?:vs\.?|versus|difference between|whats? the difference|which (?:is|one is|looks?|one looks?) better|better (?:for|on|with) a?\s*\w+|or should i)\b/i;
    function p7IsQ(t) { var s = String(t || ''); return (P7_Q_RE.test(s) || P7_Q2_RE.test(s) || /\?\s*$/.test(s)) && !/^\s*(?:what about|how about)\b/i.test(s) && !EDIT_START_RE.test(s) && !/^\s*(?:make|paint|turn|put|add|give|change)\b/i.test(s); }
    var P7_LIST_RE = /^\s*(?:(?:ok|okay|so|and|now|then|hmm+|can (?:you|u)|could (?:you|u)|pls|please|just)[\s,]+)*(?:(?:show|list)(?: me| us)?|give (?:me|us))\s+(.+?)\s*[?.!]*$/i;
    var P7_LIST2_RE = /^\s*(?:(?:ok|okay|so|and|hey)[\s,]+)*(?:what|which|any)\s+(?:(?:other|good|nice|cool|kind of|kinds of|sort of)\s+)?(?:(.+?)\s+)?(?:finishes|looks|options|paints|shades|choices)\b(.*?)\s*[?.!]*$/i;
    var P7_LIST_STOP = /\b(?:me|us|some|the|all|a|an|few|your|any|more|other|different|ones?|finish(?:es)?|options?|looks?|choices?|paints?|shades?|kinds?|types?|of|for|on|in|to|with|that|which|would|could|look|good|great|nice|go|goes|do|you|u|have|got|there|are|is|it|my|car|cars|body|available|best|cool|please|pls|can|what|like|options|list|lists|catalog|catalogue|show)\b/gi;
    function p7ListQuery(t) {
        var s = String(t || ''), m = P7_LIST_RE.exec(s), m2 = !m && P7_LIST2_RE.exec(s), phrase = null;
        if (m) { if (!/\b(?:ones|finishes|options|looks|choices|paints|shades|kinds|types)\b/i.test(m[1]) || /\b(?:how|where|why|something|anything|else|spec ?map|layers?|history|me what|numbers?|sponsors?|logos?)\b/i.test(m[1])) return null; phrase = m[1]; }
        else if (m2) { if (/\b(?:what|which|any)\s+(?:\w+\s+)?looks?\s+(?:good|great|best|nice|cool|better|right|fast|sick|clean)\b/i.test(s)) return null; phrase = (m2[1] || '') + ' ' + (m2[2] || ''); }
        else return null;
        if (p7PartsOf(phrase).length) return null;          // "show me looks for the hood" = the open look step on that part (the app's picker)
        return phrase.toLowerCase().replace(/['’]/g, '').replace(P7_LIST_STOP, ' ').replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
    }
    function p7List(t, env) {
        var q = p7ListQuery(t); if (q == null) return null;
        if (!q && env && env.list && env.list.q) q = env.list.q;
        if (!q) return p7Ask('list-kind', 'Which kind of finish should I list? Tap one.', ['Show me the matte finishes', 'Show me the metallic finishes', 'Show me the pearl finishes', 'Show me the chrome finishes']);
        var words = q.split(' '), key = words[words.length - 1].replace(/s$/, ''), all = catalogue(q, 24), seen = {}, items = [];
        all.filter(function (x) { return String(x.label || '').toLowerCase().indexOf(key) !== -1; }).concat(all).forEach(function (x) { var k = String(x.label || '').toLowerCase(); if (!k || seen[k] || items.length >= 6) return; seen[k] = 1; items.push(x); });
        if (items.length < 2) return p7Ask('list-none', 'I found no ' + q + ' finishes in the catalogue. Try another word:', ['Show me the matte finishes', 'Show me the metallic finishes', 'Show me the pearl finishes']);
        var ord = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth'], title = q.charAt(0).toUpperCase() + q.slice(1);
        var text = title + ' finishes in the catalogue: ' + items.map(function (x, i) { return (i + 1) + '. ' + x.label; }).join(', ') + '. Say “use the ' + ord[1] + ' one” (it goes on the body) or “put the ' + ord[2] + ' one on the hood”. Nothing changes until you pick one.';
        var r = asked('list', text, items.slice(0, 4).map(function (x) { return 'Use ' + x.label + ' on the body'; })); r.via = 'list'; r.list = { q: q, items: items }; return r;
    }
    var P7_ORD = { first: 0, '1st': 0, one: 0, '1': 0, second: 1, '2nd': 1, two: 1, '2': 1, third: 2, '3rd': 2, three: 2, '3': 2, fourth: 3, '4th': 3, four: 3, '4': 3, fifth: 4, '5th': 4, five: 4, '5': 4, sixth: 5, '6th': 5, six: 5, '6': 5, last: -1 };
    var P7_PICK_RE = /\b(?:the\s+)?(first|second|third|fourth|fifth|sixth|last|1st|2nd|3rd|4th|5th|6th)(?:\s+(?:one|finish|look|option|choice))?\b|\b(?:number|no\.?|#|option)\s*([1-6])\b/i;
    function p7Pick(t, env) {
        var L = env && env.list; if (!L || !L.items || !L.items.length) return null;
        var s = String(t || ''), item = null, low = s.toLowerCase();
        L.items.forEach(function (x) { if (!item && x.label && low.indexOf(String(x.label).toLowerCase()) !== -1) item = x; });
        if (!item) {
            var m = P7_PICK_RE.exec(s); if (!m) return null;
            if (!/\b(?:use|try|pick|put|apply|go with|give|take|want|do|choose|select|that|the)\b/i.test(s) && s.split(/\s+/).length > 4) return null;
            var i = P7_ORD[String(m[1] || m[2]).toLowerCase()]; if (i == null) return null; item = i < 0 ? L.items[L.items.length - 1] : L.items[i];
            if (!item) return p7Ask('list-range', 'That list has ' + L.items.length + ' finishes. Which one?', L.items.slice(0, 4).map(function (x) { return 'Use ' + x.label + ' on the body'; }));
        }
        var parts = p7PartsOf(s), Bb = B(), tgs = parts.length && !/\b(?:body|whole car|the car|everything)\b/i.test(s) ? parts : ['body'];
        var sts = tgs.map(function (p) { var st = Bb.newStep({ what: p === 'body' ? { k: 'body', tg: { kind: 'body' } } : { k: 'part', part: p, tg: { kind: 'part', part: p, at: 0 } } }); Bb.pickChoice(st, item); return st; });
        sts[0].note = 'From the list: ' + item.label + ' on the ' + (tgs[0] === 'body' ? 'body paint' : cvName(tgs)) + '. Numbers and sponsors keep theirs.';
        Bb.check(sts, env); var nv = never(sts, {}, []); if (!nv.steps.length) return null;
        return stepsResult(nv.steps, { via: 'list-pick' });
    }

    // (3) KEEP-CLAUSES: "the sides stay as they are", "the roof stays white", "keep it shiny" = the kept parts are left out of every step (no extra pick)
    var P7_STAY_RE = new RegExp('(?:[,;]\\s*|\\b(?:but|and|while|with)\\s+)?(?:the |my )?(front bumper|rear bumper|left side|right side|bumpers?|sides|doors?|hood|roof|trunk|spoiler|wing|numbers?|sponsors?|logos?)\\s+(?:can |should |will |must )?(?:stay(?:s|ing)?|remain(?:s|ing)?|keep(?:s|ing)? (?:their|its) (?:colou?r|paint|look)|(?:is|are) fine|(?:is|are) good|(?:is|are) ok(?:ay)?|untouched)(?:\\s+(?:as (?:they|it) (?:are|is|were|was)|the same|what (?:they|it) (?:are|is)|how (?:they|it) (?:are|is)|alone|untouched|(?:' + COLOUR_WORDS + ')))?\\b', 'gi');
    var P7_KEEPSHINE_RE = /(?:[,;]\s*|\b(?:but|and)\s+)?\b(?:keep(?:ing)?|leave|leaving)\s+(?:it|the car|everything|them|the shine|the gloss|the finish)\s+(shiny|glossy|gloss|matte|satin|the same shine|as shiny|as glossy)\b\s*,?/i;
    var P7_KEEP2_RE = /(?:[,;]\s*|\b(?:but|and|just)\s+)?\b(?:leave|leaving|don'?t touch|dont touch|do not touch|without touching|never touch|except(?: for)?|apart from|other than|but not|not)\s+(?:the |my |both )?(front bumper|rear bumper|left side|right side|bumpers?|sides|doors?|hood|roof|trunk|spoiler|wing)(?:\s+(?:alone|as (?:they|it) (?:are|is)|untouched|the same))?\b/gi;
    var P7_KEEP3_RE = /(?:^|[,;]\s*|\b(?:but|and)\s+)\bkeep(?:ing)?\s+(?:the |my )?(front bumper|rear bumper|left side|right side|bumpers?|sides|doors?|hood|roof|trunk|spoiler|wing)\b(?:\s+(?:as (?:it|they) (?:is|are)|the same|how (?:it|they) (?:is|are)|untouched|alone))?\s*(?=[,;]|\band\b|\bbut\b|$)/gi;
    function p7Keep(t) {          // -> { text: the rest, keep: [part words], shine: 'glossy' | null }
        var keep = [], s = String(t || ''), shine = null;
        s = s.replace(P7_STAY_RE, function (m0, w) { w = String(w).toLowerCase(); if (keep.indexOf(w) === -1) keep.push(w); return ' , '; });
        s = s.replace(P7_KEEP3_RE, function (m0, w) { w = String(w).toLowerCase(); if (keep.indexOf(w) === -1) keep.push(w); return ' , '; });
        if (!/^\s*(?:not|no)\b/i.test(s)) s = s.replace(P7_KEEP2_RE, function (m0, w) { w = String(w).toLowerCase(); if (keep.indexOf(w) === -1) keep.push(w); return ' , '; });          // a leading "not the hood, the roof" is a correction (RETARGET), not a keep
        var ks = P7_KEEPSHINE_RE.exec(s); if (ks) { var rest = s.replace(P7_KEEPSHINE_RE, ' , '); if (/[a-z]{3,}/i.test(rest.replace(/\b(?:just|only|and|but|then|please|the|it)\b/gi, '')) && cvVal(cvParse(rest), false)) { shine = ks[1].toLowerCase(); s = rest; } }
        s = s.replace(/\s*,\s*(?:,\s*)+/g, ', ').replace(/^[\s,.;]*(?:(?:but|and|then|just|so|please)\b[\s,.;]*)*/i, '').replace(/[\s,.;]*(?:\b(?:but|and|then|please))?[\s,.;]*$/i, '').trim();
        return { text: s, keep: keep, shine: shine };
    }
    function p7KeepParts(words) { var out = []; (words || []).forEach(function (w) { onlyTarget(String(w).toLowerCase().replace(/^doors?$/, 'sides').replace(/^bumper$/, 'bumpers').replace(/^side$/, 'sides')).forEach(function (x) { if (x.kind === 'part' && out.indexOf(x.part) === -1) out.push(x.part); }); }); return out; }
    function p7Exclude(steps, words) {          // a whole-body / colour step leaves the kept parts out (zone region.exclude = those parts' masks: js/spb-pro-zone-kit.js excludedUnion)
        var ps = p7KeepParts(words); if (!ps.length) return 0; var n = 0;
        (steps || []).forEach(function (s) { var w = s.what; if (!w || !(w.k === 'body' || w.k === 'main' || (w.k === 'colour' && !(w.tg && (w.tg.parts || w.tg.layers))))) return; s.extra = s.extra || {}; var have = s.extra.exclude || []; ps.forEach(function (p) { if (have.indexOf(p) === -1) have.push(p); }); s.extra.exclude = have; n++; });
        return n;
    }

    // (6) memory: "something else" = another option for the last request; "save it" = render + where the files land
    var P7_ELSE_RE = /^\s*(?:(?:no|nah|nope|hmm+|meh|ok|okay|those|that|they|it|looks?|look)[\s,]+)*(?:(?:those|that|they|it)\s+(?:look|looks)\s+\w+[\s,]+)?(?:(?:show me|try|give me|do|got|any|lets? (?:try|see)|how about|maybe)\s+)?(?:something else|some ?thing different|another (?:one|option|look|idea|colou?r)|a different (?:one|look|option|idea|colou?r)|other options?|anything else|more options|a different style)\b/i;
    function p7Else(t, env) {
        if (!P7_ELSE_RE.test(String(t || ''))) return null;
        var last = env && env.last, la = last && last.act, L = last ? lastLabel(last) : '';
        if (env && env.list && env.list.items && env.list.items.length && !last) return p7Ask('else-list', 'Other picks from that list: tap one, or ask for another kind (for example “show me the satin finishes”).', env.list.items.slice(2, 6).map(function (x) { return 'Use ' + x.label + ' on the body'; }));
        if (last && hasLook(la)) {
            var lw = String((la.texture && (la.texture.label || la.texture.name)) || (la.lookObj && (la.lookObj.label || la.lookObj.id)) || la.look || '').toLowerCase().replace(/[^a-z ]+/g, ' ').trim(), ps = p7LastParts(env);
            var ls = lw ? lookStep(lw + (ps.length ? ' on the ' + ps[0] : ''), env) : null;
            if (ls) { var cur = lookWordsOf(la); ls.forEach(function (st) { st.found = (st.found || []).filter(function (x) { return cur.indexOf(String(x.label || '').toLowerCase()) === -1; }); }); ls[0].note = 'Other ' + lw + ' looks for the ' + L + ': pick one below (nothing changes until ▶ Run; Undo takes the last one off first if you want).'; var r = stepsResult(ls, { look: true, via: 'else' }); r.convo = 'else'; return r; }
        }
        if (last && la && la.colour && la.colour.hex) { var cn = String(la.colour.name || '').toLowerCase(), opts = ['black', 'white', 'silver', 'red', 'blue', 'gold'].filter(function (c) { return cn.indexOf(c) === -1; }).slice(0, 3); return p7Ask('else-colour', 'Something else for the ' + L + ': tap a colour, or a look.', opts.map(function (c) { return 'Make the ' + L + ' ' + c; }).concat(['Show me looks for the ' + (/side/.test(L) ? 'sides' : (/bumper/.test(L) ? 'body' : L))])); }
        var tp = env && env.topic && env.topic.say ? env.topic.say : '';
        return p7Ask('else', 'Something else: pick one to try (nothing changes until you pick and press ▶ Run).', ['Add a stripe down the middle', 'Fade the sides from black to red', 'Make it two tone', 'Show me looks for the body'].concat(tp ? [] : []));
    }
    var P7_SAVE_RE = /^\s*(?:(?:ok(?:ay)?|perfect|great|nice|cool|awesome|good|love it|sweet|thats? (?:it|perfect|good|great)|done|yes|yeah|alright|now|then|and|so)[\s,.!]+)*(?:(?:please|pls|can (?:you|u)|could (?:you|u))\s+)?(?:save|export|render|finish|send)\s+(?:it|this|that|the paint|my paint|the car|my car|the design|it out|it for iracing|out)?(?:\s+(?:for|to|into)\s+(?:iracing|the sim|the game))?\s*(?:now|please|pls)?\s*[.!]*$|\bhow (?:do|can|would) i (?:save|export)\b[^?]{0,40}\b(?:iracing|the sim|in game|the game)\b/i;
    function p7Save(t) {
        if (!P7_SAVE_RE.test(String(t || ''))) return null;
        var r = pinned(['preview_render.render_button', 'preview_render.output_files', 'preview_render.where_files_go'], 'To use it in iRacing, press RENDER (top bar). It writes two files named with your iRacing user ID into your iRacing paint folder for this car (Documents\\iRacing\\paint\\<car folder>): the paint, car_num_<ID>.tga (or car_<ID>.tga, depending on the number switch), and the shine, car_spec_<ID>.tga. In iRacing press Ctrl+R in the garage to reload. (File > Save project keeps the editable design for later.)', 'save', t);
        if (r) { r.why = 'save'; r.topic = null; } return r;
    }

    // (7) TOPIC routes: a symptom about the LOOK goes to the article that fixes it, never a random card
    function p7Topic(t, env) {
        var s = String(t || '');
        if (EDIT_START_RE.test(s) && !/\b(?:easier|easy|readable|stand out|visible|pop)\b/i.test(s)) return null;
        if (cvVal(cvParse(s), true) && p7PartsOf(s).length) return null;          // a real change on a named part
        if (/\b(?:plastic(?:ky|y)?|(?:like )?a toy|toy[- ]?like|fake|cheap|lifeless|looks? (?:flat|dead|dull)|spec (?:looks?|is) (?:flat|dead|boring|off)|no depth|looks? painted on)\b/i.test(s) && !/\bmake (?:it|the car) (?:look )?(?:flat|dead|matte)\b/i.test(s))
            return pinned(['support.flat_or_shiny', 'spec.paint_spec_marriage', 'recipes.flake_pearl'], 'A plastic look is almost always the SPEC, not the colour: one flat shine everywhere, no metal, no clearcoat change. Give the body real reflection (metallic, pearl or candy), or vary the roughness and clearcoat between parts (a satin roof on a gloss body). The card below shows how; Undo takes any change back.', 'topic', s);
        var vis = /\b(?:see|spot|notice|recogni[sz]e|pick out|find|track|follow)\s+(?:me|my car|it|the car|us)\b[^.]*\b(?:far|across|distance|away|pack|field|track|tv|stream|broadcast|mirror)\b|\bstand out\b[^.]*\b(?:far|distance|away|pack|field|track|grid)\b|\b(?:easy|easier|hard|harder) to (?:spot|see|find|pick out)\b|\bvisible (?:on|from|at)\b|\bfrom (?:far|a distance|across)\b/i.test(s);
        var rd = /\b(?:sponsors?|logos?|decals?|numbers?|lettering|names?)\b[^.]{0,40}\b(?:hard|tough|difficult|impossible|cant|can'?t|cannot|not easy)\s+(?:to )?(?:read|see|make out)\b|\b(?:cant|can'?t|cannot|hard to|unable to)\s+(?:read|see|make out)\s+(?:my |the |our )?(?:sponsors?|logos?|decals?|numbers?|lettering)\b|\b(?:sponsors?|logos?|decals?|numbers?)\b[^.]{0,30}\b(?:get|gets|got|are|is|look)\s+(?:lost|buried|drowned|hidden|washed out|swallowed)\b|\b(?:sponsors?|logos?|decals?|numbers?)\b[^.]{0,20}\bblend(?:s|ing)? in\b|\b(?:sponsors?|logos?|decals?|numbers?)\b[^.]{0,20}\b(?:easier|easy) to (?:read|see)\b|\b(?:easier|easy) to read\b|\bmore readable\b/i.test(s);
        if (rd) {
            var num = /\bnumbers?\b/i.test(s) && !/\b(?:sponsors?|logos?|decals?)\b/i.test(s), pn = palNames(env, 1)[0] || 'body colour';
            var rr = pinned(num ? ['ideas.numbers_match_body', 'ideas.readable_on_tv'] : ['ideas.sponsor_friendly_bases', 'ideas.readable_on_tv'], 'The fix is the paint BEHIND them, not the ' + (num ? 'numbers' : 'logos') + ': a calmer, plainer body colour with strong contrast to the ' + (num ? 'number' : 'logo') + ' colours makes them readable from a distance. Your ' + (num ? 'numbers' : 'sponsors') + ' stay exactly as they are.', 'topic', s);
            if (rr) { rr.chips = ['Make the whole car white', 'Make the whole car black', 'Make the whole car satin']; rr.why = 'readable'; } return rr;
        }
        if (vis) return pinned(['ideas.stand_out_in_pack', 'ideas.make_it_pop', 'ideas.readable_on_tv'], 'Seen from across the track, CONTRAST wins: big blocks of light against dark (a bright body with a dark roof or hood, or the other way round), one strong accent colour, and a shine change between parts. Fine detail and dark-on-dark disappear at a distance.', 'topic', s);
        return null;
    }

    // (1c) REFINEMENTS add to the last change, never replace it: "somewhere" asks where; "tone it down" = the same colour, calmer
    var P7_SOMEWHERE_RE = /\b(?:somewhere|some ?where|some places?|a few places|here and there|in places|some parts?)\b/i;
    function p7Somewhere(t, env) {
        var s = String(t || ''); if (!P7_SOMEWHERE_RE.test(s) || p7PartsOf(s).length) return null;
        var say = /\b(?:shine|shiny|gloss|glossy|wet|reflect\w*|pop)\b/i.test(s) ? 'glossy' : (/\b(?:sparkle|flake|glitter|metal\w*)\b/i.test(s) ? 'metallic' : (/\bchrome\b/i.test(s) ? 'chrome' : (/\bmatte|flat\b/i.test(s) ? 'matte' : null)));
        if (!say) { var pc = cvParse(s); if (!pc || !cvVal(pc)) return null; var c = pc.colours[0]; say = c ? (c.name || '') : (pc.looks[0] ? pc.looks[0].id : ''); if (!say) return null; }
        var r = p7Ask('where', 'Where should the ' + (say === 'glossy' ? 'shine' : say) + ' go? Tap a part (the rest stays as it is), or say one.', ['Make the hood ' + say, 'Make the roof ' + say, 'Make the trunk ' + say, 'Make the whole car ' + say], { need: 'part', say: 'make it ' + say });
        return r;
    }
    var P7_TONE_RE = /\b(?:tone|calm|dial|turn|bring|knock|take)\s+(?:it|that|this|them|the colou?r)?\s*(?:down|back)\b|\btoo (?:bright|loud|much|strong|saturated|vivid|intense|neon|in your face)\b|\b(?:less|not so) (?:bright|loud|saturated|vivid|intense)\b|\bsofter\b|\bmore (?:muted|subtle)\b/i;
    function p7Tone(t, env) {
        var s = String(t || ''), last = env && env.last, la = last && last.act; if (!P7_TONE_RE.test(s) || !last || p7PartsOf(s).length) return null;
        if (la && la.colour && la.colour.hex) {
            var bit = /\b(?:a (?:bit|little|touch|tad)|slightly|little)\b/i.test(s), h = mixHex(shadeHex(la.colour.hex, bit ? -0.08 : -0.14), '#7f7f7f', bit ? 0.15 : 0.28), base = String(la.colour.name || 'colour').replace(/^(?:toned[- ]down |(?:a bit |slightly |even )?(?:darker|lighter) )+/i, '');
            var col = { name: 'toned-down ' + base, hex: h, at: 0, qual: null, exact: true };
            var r = cvDo(last.targets.map(function (tg) { return { target: tg, colour: JSON.parse(JSON.stringify(col)), look: la.lookObj ? JSON.parse(JSON.stringify(la.lookObj)) : null, texture: la.texture ? JSON.parse(JSON.stringify(la.texture)) : null, rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, ext: null, shadeDir: -1 }; }), env, s, { via: 'convo' });
            if (r) { r.convo = 'tone'; r.steps[0].note = 'The same ' + base + ' on the ' + lastLabel(last) + ', calmer (less saturated, a touch darker). Say “a bit more” for calmer still, or Undo.'; } return r;
        }
        if (hasLook(la)) { var ec = cvCopy(la, last.targets, env, s, { strengthMul: Math.round(Math.max(0.2, (la.strength || 1) * 0.6) * 100) / 100 }); if (ec) { ec.convo = 'strength'; return ec; } }
        return null;
    }

    // (5) TEMPLATE SELF-CHECK: no sentence or chip with an empty slot, "undefined" / "null" or a doubled verb reaches the buyer
    function tidy(s) {
        var x = String(s == null ? '' : s);
        x = x.replace(/\b(?:the|a|an|for the|on the)\s+(?:undefined|null|NaN)\b/g, 'it').replace(/\b(?:undefined|null|NaN)\b/g, '');
        x = x.replace(/\b(make|paint|turn|colou?r)\s+(the \w+(?: \w+)?|it)\s+(?:is|are|was|be)\s+/gi, '$1 $2 ');
        x = x.replace(/\b(make|paint|turn|change)\s+(?:make|paint|turn|change)\b/gi, '$1');
        x = x.replace(/(^|[.!?]\s+)[Tt]he\s+(?:stays?|remains?)\b[^.!?]*[.!?]?/g, '$1').replace(/\bthe\s+(?=(?:be|is|are|go|get)\b)/gi, 'it ').replace(/\bthe\s+([?.!,])/g, 'it$1').replace(/\bthe\s*$/i, 'it');
        x = x.replace(/[ \t]{2,}/g, ' ').replace(/\s+([?.!,:;])/g, '$1').replace(/\bWhat should it be\b/, 'What should it be');
        return x.trim();
    }
    function chipOk(c) { var x = String(c || ''); return !!x.trim() && !/\b(?:undefined|null|NaN)\b/.test(x) && !/\s{2,}/.test(x) && !/\b(?:the|for the|on the|a)\s*$/i.test(x) && !/\b(?:make|paint|turn)\s+(?:the \w+(?: \w+)?|it)\s+(?:is|are)\b/i.test(x); }
    function tidyR(r) {          // applied to every routed result (asks, chips, notes, answers' lead)
        if (!r) return r;
        if (r.ask) { r.ask.text = tidy(r.ask.text); r.ask.chips = (r.ask.chips || []).map(tidy).filter(chipOk); }
        if (r.chips) r.chips = r.chips.map(tidy).filter(chipOk);
        if (r.lead) r.lead = tidy(r.lead);
        (r.steps || []).forEach(function (s) { if (s && s.note) s.note = tidy(s.note); if (s && s.ask) s.ask = tidy(s.ask); if (s && s.chips) s.chips = s.chips.filter(function (c) { return typeof c !== 'string' || chipOk(c); }); });
        return r;
    }

    var P7_OTHER_RE = /\b(?:the )?other side\b|\bopposite side\b|\bmirror (?:it|that)\b/i;
    function p7Other(t, env) {
        if (!P7_OTHER_RE.test(String(t || ''))) return null; var last = env && env.last; if (!last || !last.act) return null;
        var ps = p7LastParts(env), opp = ps.indexOf('left side') !== -1 && ps.indexOf('right side') === -1 ? 'right side' : (ps.indexOf('right side') !== -1 && ps.indexOf('left side') === -1 ? 'left side' : null);
        if (!opp) return p7Ask('other-side', 'Which side do you mean? The last change was on the ' + lastLabel(last) + '.', ['Do the same on the left side', 'Do the same on the right side']);
        var r = cvCopy(last.act, [{ kind: 'part', part: opp, at: 0 }], env, t); if (!r) return null; r.convo = 'other-side'; if (r.steps && r.steps[0]) r.steps[0].note = 'The same change on the ' + opp + ' only (the ' + (opp === 'right side' ? 'left' : 'right') + ' side already has it).'; return r;
    }
    // a COMPARISON question ("candy or metallic, whats the difference") is an answer, never a pick
    var P7_CMP_RE = /\b(?:difference|diff|vs\.?|versus|compared?(?: to| with)?|which (?:is|one is|looks?) better|better than)\b/i;
    function p7Compare(t) { if (!P7_CMP_RE.test(String(t || ''))) return null; var hits = search(casualCore(String(t)), 6); if (!hits[0] || hits[0].score < 2) return null; var a = answered(hits, t); a.via = 'compare'; return a; }
    // the pass-7 reader, before the older paths. Returns a result or null.
    function pre7(text, env) {
        var t = String(text || '').trim(); if (!t) return null;
        var sv = p7Save(t); if (sv) return sv;
        if (/^\s*(?:please\s+)?(?:paint|make|turn|colou?r|change)(?:\s+(?:the|my|a|an))?\s*[.!?]*$/i.test(t)) return p7Ask('unfinished', 'That sentence stopped early: what should change, and to what? Tap one, or say a part and a colour.', ['Make the hood black', 'Make the roof white', 'Make the whole car blue', 'Show me looks for the body']);
        var pk = p7Pick(t, env); if (pk) return pk;
        var ls = p7List(t, env); if (ls) return ls;
        var tp = p7Topic(t, env); if (tp) return tp;
        var cq = p7Compare(t); if (cq) return cq;
        var os2 = p7Other(t, env); if (os2) return os2;
        if (p7IsQ(t)) return null;          // questions: the question paths below (never steps; see the final guard in route)
        var el = p7Else(t, env); if (el) return el;
        var gr = p7Grad(t, env); if (gr) return gr;
        var ol = p7Outline(t, env); if (ol) return ol;
        var sw = p7Somewhere(t, env); if (sw) return sw;
        var tn = p7Tone(t, env); if (tn) return tn;
        return null;
    }
    // FINAL GUARD (questions): a question never comes back as steps that would run
    function qGuard(text, r) {
        if (!r || !p7IsQ(text) || !(r.steps || []).length || r.steps.every(B().stepOpen)) return r;
        var hits = search(casualCore(String(text)), 6);
        if (hits[0] && hits[0].score >= 2.4) { var a = answered(hits, text); a.via = 'qguard'; return a; }
        var said = B().readAs(r.steps);
        return asked('question', 'That sounds like a question, so nothing was changed. If you want this change, tap it: ' + said + '.', ['Do it: ' + String(text).replace(/\?+\s*$/, ''), 'Show me looks for the body']);
    }

    function route(text, env) {          // HELPER FIX PASS 7 2026-10-05: the pass-7 reader first, keep-clauses, the question guard and the template self-check on every result
        var p7 = null; try { p7 = pre7(text, env); } catch (e7) { p7 = null; }
        if (p7) return tidyR(npFilter(p7, env));
        var kp = p7Keep(text), r;
        if ((kp.keep.length || kp.shine) && kp.text && kp.text !== String(text).trim()) {
            r = route0(kp.text, env); var kps = p7KeepParts(kp.keep);
            if (r && r.steps && r.steps.length) {
                r.steps = r.steps.filter(function (x) { return !(x.what && x.what.k === 'part' && kps.indexOf(x.what.part) !== -1); });
                if (!r.steps.length) r = asked('keep', 'You asked to keep the ' + kp.keep.join(' and ') + ' as they are, so there is nothing left to change. What should change?', ['Make the whole car black', 'Show me looks for the body']);
                else { p7Exclude(r.steps, kp.keep); r.kept = (r.kept || []).concat(kp.keep); if (r.via === 'plan' || !r.via) r.via = 'keep';          // HELPER FIX PASS 7 2026-10-05: shown here (the app's own path re-reads the raw sentence and refuses the kept part)
                    if (r.steps[0] && !kp.keep.length) r.steps[0].note = (r.steps[0].note ? r.steps[0].note + ' ' : '') + 'The shine stays ' + kp.shine + '.'; else if (r.steps[0]) r.steps[0].note = (r.steps[0].note ? r.steps[0].note + ' ' : '') + 'The ' + kp.keep.join(' and ') + ' stay' + (kp.keep.length === 1 && !/s$/.test(kp.keep[0]) ? 's' : '') + ' exactly as ' + (kp.keep.length === 1 && !/s$/.test(kp.keep[0]) ? 'it is' : 'they are') + (kp.shine ? '; the shine stays ' + kp.shine : '') + '.'; }
            }
        } else r = route0(text, env);
        return tidyR(qGuard(text, r));
    }
    function route0(text, env) {
        var sty = styleOf(text); if (sty) { var rs = npFilter(route1(sty.say, env), env); if (rs && (rs.steps || []).length) { rs.via = 'style'; rs.style = sty.id; rs.steps[0].note = 'Style recipe “' + sty.title.split(':')[0] + '” from the encyclopedia: ' + sty.say.replace(/^make /, '') + '. Numbers and sponsors stay as they are; Undo takes it back.' + (rs.steps[0].note ? ' ' + rs.steps[0].note : ''); return rs; } }          // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- a style-menu chip = that recipe as guided-builder steps
        var r = npFilter(route1(text, env), env);          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper
        if (r && r.cls === 'ANSWER' && !r.topic) { var tp = topicOf(text); if (tp) r.topic = tp; }          // HELPER_V2 fix pass 4: "how do i make chrome" > "ok do that on the hood"
        return r;
    }
    // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- FINAL 5a (owner live failure: "Make the current black hexagon - Black Base layer - make it a
    // light blue with silver accent. And give the spec on it a holographic look" was read as "Yellow Base layer -> black" + "light blue -> silver" + an open "? finish").
    // A PSD layer NAMED in the sentence is the target: the colour words inside its name ("Black" Base) are part of the name, never a colour to pick; "the (current) black
    // hexagon / art / design" on it = ALL of that layer's art (the layer's own alpha: no colour-pick holes, no jagged edges, nothing else touched); "with (a) silver accent"
    // is not a second target; "give the spec (on it) a holographic look" = the colour-keeping holographic shine on the SAME zone. One target, one zone.
    var LAYER_SKIP_RE = /mask|wire|mandatory|licen[cs]e|guide|template/i;
    function layerSentence(t, env) {
        var E = Ed(), Bb = B(); if (!E || !E.plan || !Bb) return null;
        var L = ((env && env.layers) || []).filter(function (l) { return l && l.name && !LAYER_SKIP_RE.test(l.name + ' ' + (l.role || '')); }); if (!L.length) return null;
        var hit = null;
        L.slice().sort(function (a, b) { return b.name.length - a.name.length; }).some(function (l) {
            var nm = String(l.name).trim().replace(/[_\s]+/g, ' '), esc = nm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '[\\s_]+');
            var m = new RegExp('(?:\\b(?:on|over|in|inside|within|of|for|from)\\s+)?(?:\\b(?:the|my|that)\\s+)?\\b' + esc + '\\b(\\s+layers?\\b)?', 'i').exec(t);
            if (!m || (!m[1] && nm.split(' ').length < 2)) return false;          // a one-word name ("Numbers", "Logos") without "layer" is the everyday word: the normal paths read it
            hit = { layer: l, name: nm, m: m }; return true;
        });
        if (!hit) return null;
        if (!layerSentence._one) {          // two layers named ("the Black Base layer chrome and the Yellow Base layer red"): one clause per layer, each with its own job
            var names = L.filter(function (l) { return new RegExp('\\b' + String(l.name).trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[_\s]+/g, '[\\s_]+') + '\\b', 'i').test(t); });
            if (names.length > 1) {
                var parts = t.split(/(?:\s*[,;.]\s*|\s+)(?:and\s+then|then|and|also)\s+|\s*[;.]\s+/i), cl = [];
                parts.forEach(function (p) { var hasL = names.some(function (l) { return p.toLowerCase().indexOf(String(l.name).toLowerCase()) !== -1; }); if (hasL || !cl.length) cl.push(p); else cl[cl.length - 1] += ' and ' + p; });
                if (cl.length > 1) { var all = [], ok = true; layerSentence._one = true; try { cl.forEach(function (c) { var r1 = layerSentence(c, env); if (r1 && r1.steps && r1.steps.length) all = all.concat(r1.steps); else ok = false; }); } finally { layerSentence._one = false; }
                    if (ok && all.length) return stepsResult(all, { via: 'layer', rewritten: true }); }
            }
        }
        try { var cp = E.plan(t, env); if (cp && cp.kind === 'complaint') return null; } catch (eC) {}          // "you changed the white base" is a complaint, not a request
        var cw = new RegExp('\\b(' + COLOUR_WORDS + ')\\b', 'i'), nameCol = (cw.exec(hit.name) || [])[1], before = t.slice(0, hit.m.index), after = t.slice(hit.m.index + hit.m[0].length);
        var pick = new RegExp('\\bthe\\s+(' + COLOUR_WORDS + ')(?:\\s+(?:parts?|bits?|areas?|pixels?|bits))?\\s*$', 'i').exec(before), pickCol = pick ? pick[1] : null;          // "the yellow on the Yellow Base layer" = only that colour on it; "the black hexagon" (an art word) = all of the layer
        var rest = (before + ' ' + after).replace(/\s*[-\u2013\u2014:;]+\s*/g, ' ').replace(/\s+/g, ' ').trim(), accentCol = null;
        if (!pickCol) {
            rest = rest.replace(new RegExp('\\b(?:the|this|that|my)\\s+(?:current\\s+|existing\\s+|whole\\s+|entire\\s+)?(?:(?:' + COLOUR_WORDS + ')\\s+)?(?:hexagons?|hex(?:es)?|honeycomb|pattern|art(?:work)?|shapes?|design|graphics?|bits?|parts?|pieces?|areas?|stuff)\\b', 'gi'), 'it');
            if (pick) rest = rest.replace(new RegExp('\\bthe\\s+' + pick[1] + '\\s*$', 'i'), 'it');
        }
        rest = rest.replace(new RegExp('\\b(?:with|and)\\s+(?:a\\s+|some\\s+)?(' + COLOUR_WORDS + ')\\s+accents?\\b', 'i'), function (a0, c) { accentCol = c.toLowerCase(); return ' '; });
        rest = rest.replace(/\b(?:and\s+)?(?:give|make|put|set|add)\s+(?:the\s+)?spec(?:\s+map)?\s+(?:(?:on|of|for)\s+)?(?:it|that|them|this)?\s*(?:a|an)?\s*([a-z]+(?:\s+[a-z]+)?)\s+(?:look|finish|shine|effect|feel)\b/i, ' and make it $1 ')
            .replace(/\b(?:with\s+)?(?:a|an)?\s*([a-z]+)\s+spec\b/i, function (a0, w) { return /^(?:the|my|its|it|a|an|and|with|same)$/i.test(w) ? a0 : ' and make it ' + w + ' '; })
            .replace(/[.!]+\s*(?=\S)/g, ' ').replace(/[.!?]+\s*$/, '')
            .replace(/\b(?:make|turn|paint|colou?r|change)\s+it\s*(?:,\s*)?(?=(?:make|turn|paint|colou?r|change)\s+it\b)/gi, '')
            .replace(/\b(?:and\s+)+and\b/gi, 'and').replace(/\s+/g, ' ').trim();
        if (pickCol) rest = rest.replace(new RegExp('^(?:(?:please|make|turn|paint|change|colou?r|recolou?r)\\s+)*(?:it\\s+)?', 'i'), 'make the ' + pickCol + ' ');
        else if (!/^\s*(?:please\s+)?(?:make|turn|paint|change|colou?r|recolou?r|give|put|set|add)\b/i.test(rest)) rest = 'make it ' + rest.replace(/^\s*it\s+/i, '');
        var canon = hit.layer.name + ' layer: ' + rest, ed = null;
        try { ed = E.plan(canon, env); } catch (eP) { ed = null; }
        if (!ed || (ed.kind !== 'ops' && ed.kind !== 'ask')) return null;
        var tgL = { kind: 'layer', layers: [hit.layer.name], word: hit.layer.name }, named = {}, role = String(hit.layer.role || '').toLowerCase();
        if (/number/.test(role)) named.numbers = 1; if (/logo|sponsor|decal/.test(role)) named.sponsors = 1;
        if (ed.kind === 'ops') {
            var ops = [];
            ed.ops.forEach(function (o) {
                o = Object.assign({}, o);
                if (!o.target || o.target.kind === 'body' || o.target.kind === 'main' || o.target.kind === 'step' || (o.target.kind === 'layer' && !pickCol) || (o.target.kind === 'colour' && !pickCol)) o.target = tgL;
                var same = ops.filter(function (p) { return JSON.stringify(p.target) === JSON.stringify(o.target); })[0];
                if (same && (!same.colour || !o.colour) && (!same.look || !o.look) && (!same.texture || !o.texture)) { ['colour', 'look', 'texture', 'shade', 'rel', 'soft', 'strong', 'keep', 'pop'].forEach(function (k) { if (o[k] != null && same[k] == null) same[k] = o[k]; }); return; }
                ops.push(o);
            });
            ed = Object.assign({}, ed, { ops: ops });
        }
        var rc = Bb.fromPlan(ed, env, canon); Bb.check(rc.steps, env);
        var nv = never(rc.steps, named, []); if (!nv.steps.length) return null;
        var note = 'Only the ' + hit.layer.name + ' layer' + (pickCol ? '’s ' + pickCol : '') + ' changes (its own shape, so nothing else is touched).';
        if (accentCol) note += ' “' + accentCol.charAt(0).toUpperCase() + accentCol.slice(1) + ' accent”: ' + (/holo|chrome|metal|flake|pearl/i.test(rest) ? 'the ' + (/holo/i.test(rest) ? 'holographic' : 'metal') + ' shine already gives it a bright ' + accentCol + '-metal sparkle' : 'say “add ' + accentCol + ' flake” after this runs for a ' + accentCol + ' sparkle') + '.';
        nv.steps[0].note = (nv.steps[0].note ? nv.steps[0].note + ' ' : '') + note;
        return stepsResult(nv.steps, { via: 'layer', rewritten: true });
    }
    function route1(text, env) {
        var raw = String(text || '').trim(), Bb = B(), E = Ed(); if (!raw) return online(raw, 'empty');
        var t0 = clean(raw); try { if (E && E.fixParts) t0 = E.fixParts(t0); } catch (eFp) {}          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- part typos / everyday part words first
        t0 = t0.replace(/\btiger[- ]?stripes?(?:\s+(?:pattern|print|look))?\b/gi, 'tiger pattern');          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "tiger stripe orange" is the catalogue's tiger pattern, never a racing-stripe element (blind4 b4-046)
        if (!/[a-z0-9]/i.test(t0)) return asked('unclear', 'I did not catch that. Tell me what to change (for example “make the hood red”), or ask about the app.', START_CHIPS);
        var tcz = casualCore(t0); if (tcz !== t0 && kind(tcz) === 'question' && kind(t0) !== 'question') t0 = tcz;          // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- "hey quick question, what does roughness do" / "can you explain pearl to me" are questions, not edits
        var k0 = kind(t0), last = env && env.last && env.last.targets && env.last.targets.length ? env.last : null;
        if (k0 === 'undo') return { cls: 'DO', pass: 'undo' };
        if (/^\s*(?:(?:ok|okay|no|actually|hmm+)[\s,]+)*(?:(?:put|set|change|turn|make) (?:it|that|them|everything) )?back (?:to )?(?:how|the way|what) (?:it|they) (?:was|were)\b|^\s*(?:go|switch|change) (?:it )?back\b|^\s*revert(?: (?:it|that|the last change))?\s*[.!]*$|^\s*undo (?:the )?last(?: one| change)?\s*[.!]*$/i.test(t0)) return { cls: 'DO', pass: 'undo' };          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper
        if (k0 !== 'question' || last) { var t0r = relx(t0); if (t0r !== t0) { t0 = t0r; if (k0 === 'chat' || k0 === 'question') k0 = 'other'; } }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- "thats too dark" right after a change is about THAT change
        if (/^\s*(?:please\s+)?(?:redo|re-do)(?: (?:it|that|the last (?:change|one)))?\s*(?:please)?[.!]*$/i.test(t0)) return { cls: 'DO', pass: 'redo' };          // HELPER_V2 fix pass 4: the app's own redo
        var dc = decline(t0) || decline2(t0);
        if (dc && k0 !== 'question') return online(t0, dc);          // P4 custom art: the honest decline + the online offer
        if (offtopic(t0)) return local('offtopic');
        if (k0 === 'chat') { if (!APP_WORD_RE.test(t0) && !new RegExp('\\b(?:' + COLOUR_WORDS + ')\\b', 'i').test(t0)) return local('offtopic'); k0 = (Q_START.test(t0) || /\?\s*$/.test(t0)) ? 'question' : 'other'; }
        if (k0 !== 'question') { var lyr = layerSentence(t0, env); if (lyr) return lyr; }
        if (k0 !== 'question' && FADED_LOOK_RE.test(t0) && /\b(?:hood|bonnet|roof|trunk|spoiler|wing|bumpers?|sides?|doors?|fenders?|quarter ?panels?|mirrors?|splitter|rockers?)\b/i.test(t0)) t0 = t0.replace(/\b(?:faded|fading|worn|weathered|aged|distressed|sun[- ]?(?:faded|bleached)|washed[- ]?out)\s+/gi, '');          // a named part: the look itself on that part (the catalogue search below is whole-body only)
        if (k0 !== 'question' && FADED_LOOK_RE.test(t0) && !/\b(?:from|into|to)\b/i.test(t0)) { var lsF = lookStep(t0, env); if (lsF) return stepsResult(lsF, { look: true, via: 'look' }); }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "faded carbon" = a worn carbon LOOK from the catalogue, not a two-colour gradient (blind4 b4-042)          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- FINAL 5a: a named PSD layer is the target
        for (var pj = 0; pj < PIN.length; pj++) if (PIN[pj][0].test(t0)) { var pr1 = pinned(PIN[pj][1], PIN[pj][2], 'pin', t0); if (pr1) return pr1; }
        var lv = /^\s*(?:please\s+)?(lighten|darken|brighten|deepen)(?: up)?\s+(.+?)(?:\s+(a (?:bit|little|touch|tad|lot)|slightly|some))?\s*[.!]*$/i.exec(t0);          // HELPER_V2 fix pass 4: "lighten the whole car a bit" = make it a bit lighter
        if (lv && !/\b(?:how|why|what)\b/i.test(t0)) t0 = 'make ' + lv[2] + ' ' + (lv[3] ? lv[3] + ' ' : '') + ({ lighten: 'lighter', darken: 'darker', brighten: 'lighter', deepen: 'darker' })[lv[1].toLowerCase()];
        if (k0 !== 'question') { var dn0 = denoise(t0); if (dn0 !== t0) t0 = dn0; }          // HELPER_V2 fix pass 4: "a camo scheme" / "chameleon colour shifting paint" = the look word
        var wl = /^\s*make (?:the whole car|the entire car|the car|my car|everything|it all|the paint|the body|the whole thing) ((?:a (?:bit|little|touch|tad) |slightly )?)(lighter|darker|brighter|deeper|paler)\s*[.!]*$/i.exec(t0);          // HELPER_V2 fix pass 4: a whole-car shade = which colour (a shade moves one colour; the car has several)
        if (wl) { var wp = palNames(env, 3); if (wp.length) return asked('adjust', 'Which colour should be ' + wl[1] + wl[2] + '? Tap one (each colour keeps its own shading).', wp.map(function (n) { return 'Make the ' + n + ' ' + wl[1] + wl[2]; })); }
        if (k0 !== 'question' && !(last && /^\s*(?:make )?(?:it|that|them) /i.test(t0) && !/\b(?:car|look|something|anything)\b/i.test(t0)) && (STYLE_ASK_RE.test(t0) || (!last && VAGUE2_RE.test(t0)))) return styleAsk(t0);          // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- vague ask = 4 recipe chips from the style menu
        var cv = convo(t0, env, k0); if (cv) return cv;
        var acc2 = k0 !== 'question' ? accents2(t0, env) : null; if (acc2) return acc2;
        var shf = k0 !== 'question' ? new RegExp('\\b(?:shift(?:s|ing)?|flip(?:s|ping|ped)?|chang(?:es|ing)|go(?:es|ing)?|turn(?:s|ing)?|fad(?:es|ing))\\s+(?:from\\s+)?(' + COLOUR_WORDS + ')\\s+(?:to|into|and)\\s+(' + COLOUR_WORDS + ')\\b', 'i').exec(t0) : null;          // HELPER_V2 fix pass 4
        if (shf && /\b(?:pearl\w*|chameleon|flip|flop|shift\w*|iridescent|colou?r ?shift\w*|duo ?chrome|interference)\b/i.test(t0) && !new RegExp('\\b(?:make|turn|change|recolou?r) (?:the |my |all )?(?:' + COLOUR_WORDS + ')\\b', 'i').test(t0)) { var shq = shf[1] + ' ' + shf[2] + ' shift', shs = lookStep('a ' + shq + ' look', env); if (!shs) shs = lookStep('a ' + shf[1] + ' ' + shf[2] + ' chameleon look', env); if (shs) { shs[0].note = 'A colour-shift finish from ' + shf[1] + ' to ' + shf[2] + ': pick one below (it goes on the body; your numbers and sponsors keep theirs).'; return stepsResult(shs, { look: true, via: 'shift' }); } }
        if (k0 !== 'question' && !kept0(t0) && !slang(t0)) {          // HELPER_V2 fix pass 4: a symptom said as a statement ("the sponsors are gone after i applied that finish") or a how-to goal with a strong article ("try lots of finishes on the same colour") is a question
            var spc = cvParse(t0), sh0 = search(t0, 6), noEdit = !!spc && !cvVal(spc) && !spc.targets.filter(function (x) { return x.kind !== 'body' && !/^(?:numbers|sponsors|logos?)$/.test(x.kind); }).length;
            if (sh0[0] && SYMPTOM_RE.test(t0) && !EDIT_START_RE.test(t0) && confident(sh0[0], 'question')) return answered(sh0, t0);
            if (sh0[0] && noEdit && !EDIT_START_RE.test(t0) && sh0[0].score >= 15 && sh0[0].cov >= 0.9) return answered(sh0, t0);
        }          // HELPER_V2 fix pass 4: the conversation layer (pending question, last change, last answer) comes before any fresh reading
        var fu = k0 !== 'question' || CHOICE_RE.test(t0) ? followup(t0, last, env) : null;
        if (fu && !fu.rewrite) return fu;
        if (fu && fu.rewrite) t0 = fu.rewrite;
        // SCOPE first (a question keeps its words unless it opens with don't / keep), then the curated slang table (P3)
        var isQ0 = k0 === 'question' && !NEG_START.test(t0) && (Q_START.test(t0) || /\?\s*$/.test(t0)), sc = isQ0 ? { keep: [], only: [], keepColours: false, rest: t0 } : scope(t0), t = sc.rest, sl = slang(t); if (sl) t = sl;
        var kept = sc.keep.concat(sc.keepColours ? ['colours'] : []);
        if ((sc.keep.length || sc.keepColours || sc.only.length) && !/[a-z]{3,}/i.test(t.replace(/\b(?:but|and|please|just|only|the|it|ok|okay|so|alone|they|are|is|fine|good|as|that|those)\b/gi, ''))) {
            if (sc.only.length && !sc.keep.length && !sc.keepColours && sc.only.every(function (w) { return !/^(?:body|numbers?|sponsors?|logos?)$/.test(w); })) { var os = [].concat.apply([], sc.only.map(onlyTarget)).map(function (x) { var st = Bb.newStep({ what: { k: 'part', part: x.part, tg: x } }); st.note = 'What should the ' + x.part + ' get? Pick a colour or a look.'; return st; }); Bb.check(os, env); return stepsResult(os, { via: 'only' }); }          // "only the roof": the place is known, the change is the pick
            if (sc.keepColours) return asked('protect', 'Your colours stay as they are. Which shine should the paint get?', ['Make it metallic but keep the colours', 'Make it satin but keep the colours', 'Make it gloss but keep the colours']);
            return asked('protect', 'I will leave the ' + (sc.keep.length ? sc.keep : sc.only).join(' and the ') + (sc.keep.length ? ' alone' : ' as the only place') + '. What should I change?', palNames(env, 2).map(function (n) { return 'Change the ' + n; }).concat(['Change only the shine', 'Show me looks for the body']));
        }
        var tf = k0 !== 'question' ? tooFix(t) : null; if (tf) t = tf;
        var k = (t !== t0) ? kind(t) : k0; if (k === 'chat') k = 'other'; if ((sc.keep.length || sc.keepColours) && k === 'question' && NEG_START.test(t0)) k = 'edit';
        // P5 removal = confirm first; vague / bare-adjustment edits ask which
        if (/^\s*(?:hide|show|unhide)\s+(?:the |my )?(?:numbers?|sponsors?|logos?|decals?) layers?\b/i.test(t)) return { cls: 'DO', pass: 'layer', via: 'layer', steps: [] };          // the confirmed chip: the app's own (undoable) layer switch
        var mL = /^\s*show me (?:some |the )?(?:looks|finishes)(?: for the (hood|roof|trunk|spoiler|sides|body))?\b/i.exec(t);
        if (mL && !/\b(?:like|with|that)\b/i.test(t)) { var lp = (mL[1] || 'body').toLowerCase(), sb = Bb.newStep({ what: lp === 'body' ? { k: 'body' } : (lp === 'sides' ? { k: 'part', part: 'left side' } : { k: 'part', part: lp }), act: 'finish' }); sb.note = 'Pick a look below (or search). It goes on the ' + lp + ' paint; your numbers and sponsors keep theirs.'; return stepsResult([sb], { via: 'looks' }); }
        var rm = k !== 'question' && REMOVE_RE.exec(t); if (rm) { var what = rm[1].toLowerCase().replace(/s?$/, 's'); return asked('remove', 'Hide the ' + what + '? The layer stays in your file, so you can show it again. (A number the sim stamps on is set in iRacing, not in the paint.)', ['Hide the ' + what + ' layer', 'Keep the ' + what, 'How do I get rid of the car numbers?']); }
        if ((k !== 'question' || /^\s*i (?:dont|don'?t|do not) (?:like|love)\b/i.test(t)) && VAGUE_RE.test(t)) { var pn = palNames(env, 2); return asked('vague', 'What should I change? Pick one, or type it (for example “make the ' + (pn[0] || 'yellow') + ' blue”).', pn.map(function (n) { return 'Change the ' + n; }).concat(['Change only the shine', 'Show me looks for the body'])); }
        if (k !== 'question' && splitFrames(t).some(function (c) { return VAGUE2_RE.test(c); }) && !splitFrames(t).some(function (c) { return !VAGUE2_RE.test(c) && hasValueText(c); })) return asked('vague', 'What kind of look? Pick one to start, or describe it (for example “candy red with a black hood”).', VAGUE_CHIPS);
        if (k !== 'question' && /\bfavou?rite colou?r\b/i.test(t) && !new RegExp('\\b(' + COLOUR_WORDS + ')\\b', 'i').test(t)) return asked('colour', 'Which colour is that? Pick one or type it (for example “make the car purple”).', ['Make the car red', 'Make the car blue', 'Make the car purple', 'Make the car pink']);
        var adj = k !== 'question' && !last && ADJ_RE.exec(t); if (adj && !new RegExp('\\b(' + COLOUR_WORDS + '|hood|roof|trunk|bumpers?|sides?|spoiler|numbers?|sponsors?|body|car|everything)\\b', 'i').test(t)) { var pa = palNames(env, 3), ph = adj[1].trim(); return asked('adjust', 'Which colour should be ' + ph + '?', pa.map(function (n) { return 'Make the ' + n + ' ' + ph; })); }
        for (var pi = 0; pi < PIN.length; pi++) if (PIN[pi][0].test(t)) { var pr0 = pinned(PIN[pi][1], PIN[pi][2], 'pin', t); if (pr0) return pr0; }
        // P5 a question or a symptom gets the troubleshooting / how-to article first
        var tq = k === 'question' ? casualCore(t) : t, hits = search(tq, 6), top = hits[0];          // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- the chatty wrapper ("yo", "can u tell me", "whats the deal with") is not searched
        if (k === 'question' && confident(top, k)) return answered(hits, t);
        if (k === 'question' && dc) return online(t0, dc);
        // typed ENTITIES: adding a number / logo / sponsor / text / picture is the how-to (never a finish called "sunoco")
        var en = k !== 'question' ? entityAsk(t, raw) : null; if (en) { var ea0 = pinned(en.ids, en.lead, 'entity', t); if (ea0) { ea0.entity = en.kind; return ea0; } }
        // ---- the edit: stripes to ADD come out first, then the frames and the edit brain's plan of what is left
        var ex = k !== 'question' ? elements(t) : { els: [], rest: t }, baseT = t;
        if (ex.els.length && hasValueText(ex.rest)) baseT = ex.rest; else ex.els = [];
        var ac = accent(baseT); baseT = ac.text;
        var ed = null; try { ed = E && env && (env.palette || []).length ? E.plan(baseT, env) : null; } catch (e) { ed = null; }
        if (ed && ed.kind === 'ops' && ed.ops) ed.ops = bodyFirst(ed.ops);
        if (ed && ed.kind === 'ops' && ((ed.usedLast && last && last.act && last.act.colour && last.act.colour.hex) || (env && env.colMem))) ed.ops.forEach(function (o) { var lc0 = (ed.usedLast && last && last.act && last.act.colour && last.act.colour.hex) ? last.act.colour : (o.target && o.target.kind === 'part' && env && env.colMem ? env.colMem[o.target.part] : null); if (lc0 && lc0.hex && o.shade && !o.colour && !o.look && /^(?:darker|lighter|brighter|deeper|paler)$/.test(String(o.shade))) { var dk = /darker|deeper/.test(o.shade) ? -1 : 1, amt = /\b(?:a (?:bit|little|touch|tad)|slightly|little)\b/i.test(baseT) ? 0.15 : 0.28; o.colour = { name: o.shade + ' ' + String(lc0.name || 'colour').replace(/^(?:(?:a bit |slightly |even )?(?:darker|lighter|brighter|deeper|paler) )+/i, ''), hex: shadeHex(lc0.hex, dk * amt), at: 0, qual: null, exact: true }; o.shade = null; o.shadeDir = dk; } });          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: per-part colour memory; HELPER_V2 phase 3: a shade follow-up re-colours the last change
        if (ed && ed.kind === 'complaint') ed = null;          // "dont touch the numbers" is not a change (P0)
        var parsed = ed && (ed.kind === 'ops' || ed.kind === 'ask');
        if (k !== 'question' && FADE_RE.test(t) && !ex.els.length) { var dz = null; try { dz = W.SpbProDesign && W.SpbProDesign.offlinePart ? W.SpbProDesign.offlinePart(t) : null; } catch (eZ) { dz = null; } if (dz) return { cls: 'DO', pass: 'design', via: 'design', steps: [] }; }
        if (k !== 'question' && FADE_RE.test(t) && !ex.els.length) { var fh = search('how do i make a gradient fade', 6); if (fh.length) { var fa = answered(fh, t); fa.via = 'fade'; return fa; } }          // a fade is a gradient zone: the how-to with its Do-it, never a solid recolour
        if (k !== 'question' && /^\s*(?:(?:make it|do|give it|i want)\s+)?(?:a\s+)?two[- ]?tone(?:d)?(?:\s+(?:it|paint|paint ?job|look|livery|scheme|split|style))*(?:\s+(?:split\s+)?(?:down|along|across|on) the (?:side|sides|middle|car|length))?\s*[.!]*$/i.test(baseT)) return asked('two-tone', 'Which two colours? The first goes on top (roof, hood and trunk), the second on the rest of the body.', ['Two tone, black on top and white on the bottom', 'Two tone, black on top and red on the bottom', 'Two tone, white on top and blue on the bottom']);          // HELPER_V2 phase 3: a bare "two tone" asks for the colours
        var tt = k !== 'question' ? twoTone(baseT) : null, frE = k !== 'question' ? frameOps(baseT.replace(/\b(?:look|looks|looking) like (?:a |an )?/i, ' '), sc) : null, frRead = !!(frE && frE.ops.length && !frE.notDone.length && frE.ops.every(function (o) { return o.colour || o.look; }) && !/^\s*(?:something|i want something|make it (?:pop|sparkle|shine|glow|stand out))/i.test(baseT) && frE.ops.every(function (o) { return !o.ext; }));
        if (frRead && LOOK_RE.test(baseT) && /\blooks? like\b/i.test(baseT)) baseT = baseT.replace(/\b(?:look|looks|looking) like (?:a |an )?/i, ' ').replace(/\s+/g, ' ').trim();
        if (!tt && !frRead && k !== 'question' && LOOK_RE.test(baseT) && !(ed && ed.kind === 'ops' && !(ed.unknown || []).length && ed.ops.every(function (o) { return !o.ext && (o.look || o.colour || o.texture); }) && !/^\s*(something|i want something|make it (pop|sparkle|shine|glow|stand out))/i.test(baseT))) {
            var ls = lookStep(baseT, env); if (ls) return stepsResult(ls, { look: true, via: 'look' });
        }
        // stripes / fades / flags with no base colour are drawn by the app's own element designer (not zone recolours): hand them over, never recolour a part instead
        var elOnly = !ex.els.length && !tt && isElementClause(t) && (splitFrames(t).length < 2 || splitFrames(t).every(isElementClause)) && (!ed || (ed.kind === 'ops' && ed.ops.every(function (o) { return !o.colour && !o.look && !o.texture; })) || (ed.kind === 'ops' && ed.ops.some(function (o) { return entOfTarget(o.target) === 'stripes'; })));
        if (k !== 'question' && elOnly) { var el = null; try { el = W.SpbProDesign && W.SpbProDesign.offlineElement ? W.SpbProDesign.offlineElement(t) : null; } catch (eE) { el = null; } if (el) return { cls: 'PREFILL', pass: 'element', element: el.label || el.kind, via: 'element', steps: [] };
            if (/^\s*(?:please\s+)?(?:fix|change|edit|adjust|move|redo|tweak)\s+(?:the |my |that )?\w*\s*(?:stripes?|pinstripes?|flames|bands?)\s*[.!?]*$/i.test(t)) return asked('element-fix', 'What should change on it? Pick one, or say it (for example “make the stripes red”).', ['Make the stripes red', 'Make the stripes white', 'How do I add a stripe?']);
            var eh = search('how do i add ' + t, 6); if (eh[0] && eh[0].cov >= 0.5 && eh[0].score >= 6) { var ea = answered(eh, t); ea.via = 'element'; return ea; }
            var ep = pinned(/flame/i.test(t) ? ['recipes.flames_graphics'] : ['recipes.retro_stripes'], '', 'element', t); if (ep) return ep;
            return online(t0, 'element'); }
        if (k !== 'question') {
            var fr = frameOps(baseT, sc), bad = tt ? 'two-tone' : planBad(ed, fr), useFrame = !!tt || (fr.ops.length + fr.offmap.length > 0 && !!bad && !(ed && ed.kind === 'ask' && !fr.ops.length && !fr.offmap.length));
            if (fr.clauses >= 3 && fr.used / fr.clauses < 0.5 && !useFrame && !parsed) return online(t0, 'free-design');          // a free-form brief the frames cannot read: the online model's job
            var ops = useFrame ? (tt ? tt.ops : fr.ops) : (ed && ed.kind === 'ops' ? ed.ops : null);
            if (ops && ops.length || (useFrame && fr.offmap.length)) {
                ops = (ops || []).map(function (o) { o = Object.assign({}, o); if (o.ext && !o.look && (commonOnly(o.ext) || (o.colour && !knownTerm(o.ext)))) o.ext = null; return o; });
                // scope applies to EVERY clause: "only the X" moves whole-car jobs there; "colours kept" makes every job shine-only
                if (sc.only.length) { var ot = [].concat.apply([], sc.only.map(onlyTarget)); if (!(ot.length === 1 && ot[0].kind === 'body')) { var nops = []; ops.forEach(function (o) { if (o.target && o.target.kind === 'body') ot.forEach(function (x) { nops.push(Object.assign({}, o, { target: x })); }); else nops.push(o); }); ops = nops; } }
                var named = fr.named; sc.only.forEach(function (w) { if (/number/.test(w)) named.numbers = 1; if (/sponsor|logo/.test(w)) named.sponsors = 1; });
                var dropCol = [];
                if (sc.keepColours) ops = ops.filter(function (o) { if (o.colour && !(o.look || o.texture || o.rel || o.ext || o.pop)) { dropCol.push(o.colour.name); return false; } o.colour = null; o.keep = true; return true; });
                ops = shadeOps(ops, env, baseT);          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper
                var rc = Bb.fromPlan({ kind: 'ops', ops: ops, unknown: [] }, env, baseT);
                if (useFrame) fr.offmap.forEach(function (om) { var v = om.value, sts = Bb.fromPlan({ kind: 'ops', ops: [{ target: null, colour: sc.keepColours ? null : v.colour, look: v.look, texture: v.texture, ext: v.ext, rel: v.rel, soft: v.soft, strong: v.strong, shade: v.shade, keep: v.keep || sc.keepColours, pop: v.pop, recipe: null, sub: v.sub }], unknown: [] }, env, baseT).steps, st = sts[0] || Bb.newStep({}); sts.slice(1).forEach(function (x) { rc.steps.push(x); }); st.note = 'The ' + om.word + ' ' + (/s$/.test(om.word) ? 'are' : 'is') + ' not a separate part on this car map: pick ' + (/s$/.test(om.word) ? 'them' : 'it') + ' with Box select (or by colour) in this step.'; rc.steps.splice(rc.steps.length - (sts.length > 1 ? sts.length - 1 : 0), 0, st); });
                Bb.check(rc.steps, env);
                if (useFrame && !parsed && fr.clauses === 1 && !fr.notDone.length && !fr.offmap.length && rc.steps.some(Bb.stepOpen)) {          // one clause the encyclopedia words read completely ("rainbow flip on the hood"): those win over an open step
                    var rf = Bb.fromFlags(baseT, env); if (rf.steps.length) Bb.check(rf.steps, env);
                    if (rf.steps.length && rf.steps.every(function (s) { return s.what && !Bb.stepOpen(s); })) rc = rf;
                }
                var dp = dropProtected(rc.steps, sc.keep), nv = never(dp.steps, named, sc.keep);
                if (nv.steps.length) {
                    var notDone = (useFrame ? fr.notDone.slice() : []).concat(ex.els.map(function (e2) { return e2.raw; })), chips = (useFrame ? fr.els.map(function (c2) { return c2.replace(/^\s*(?:and |then |also )?/i, '').replace(/^\w/, function (x) { return x.toUpperCase(); }); }) : []).concat(ex.els.map(function (e2) { var where = /\b(?:hood|roof|trunk|spoiler|wing|bumper|side|sides|doors?|rocker|middle|center|centre)\b/i.test(e2.tail) ? '' : (function () { var p0 = ops.filter(function (o) { return o.target && o.target.kind === 'part'; })[0]; return p0 ? ' on the ' + p0.target.part : ''; })(); return 'Add ' + (/^(?:a|an|some|two|twin)\b/i.test(e2.raw) ? '' : 'a ') + e2.raw + where; }));
                    var notes = [];
                    if (tt) notes.push(tt.note);
                    if (useFrame) fr.notes.forEach(function (n) { notes.push(n.charAt(0).toUpperCase() + n.slice(1) + '.'); });
                    if (ac.note) notes.push(ac.note);
                    if (chips.length) notes.push('Stripes, flames and fades are drawn with their own tool, so “' + chips.join('”, “') + '” is not part of these steps: tap ' + (chips.length > 1 ? 'those chips' : 'that chip') + ' after this runs.');
                    if (dropCol.length) notes.push('Colours kept as you asked, so the ' + dropCol.join(' / ') + ' was not applied.');
                    var nd0 = useFrame ? fr.notDone.filter(function (x) { return fr.els.indexOf(x) === -1; }) : []; if (nd0.length) notes.push('Not done: ' + nd0.map(function (x) { return '“' + x + '”'; }).join(', ') + ' (I could not read ' + (nd0.length > 1 ? 'those' : 'that') + ': add it as another step).');
                    if (kept.length) notes.push('Kept as you asked: the ' + kept.join(', the ') + '.');
                    if (notes.length) nv.steps[0].note = (nv.steps[0].note ? nv.steps[0].note + ' ' : '') + notes.join(' ');
                    return stepsResult(nv.steps, { via: useFrame ? 'frame' : (kept.length || sl ? 'protect' : 'plan'), why: useFrame ? bad : undefined, notDone: notDone, kept: kept, chips: chips, dropped: nv.dropped + dp.dropped, rewritten: t !== raw.trim() });
                }
            }
            if (ed && ed.kind === 'ask') { var ra = Bb.fromPlan(ed, env, baseT); Bb.check(ra.steps, env); var na = never(dropProtected(ra.steps, sc.keep).steps, fr.named, sc.keep); if (na.steps.length) return stepsResult(na.steps, { via: 'plan', kept: kept }); }
        }
        var fl = Bb.flag(t), strong = fl.filter(function (f) { return !f.weak && !commonOnly(f.alias || ''); });
        if (!parsed && (k === 'edit' || k === 'other') && strong.length) {
            var r = Bb.fromFlags(t, env);          // nothing parsed: the encyclopedia words pre-fill
            if (r.steps.length) Bb.check(r.steps, env);
            var dr = never(dropProtected(r.steps, sc.keep).steps, {}, sc.keep); r.steps = dr.steps;
            if (r.steps.length && !r.steps.every(function (s) { return !s.what && !s.act && !s.colour && !s.finish && !s.tex && !s.termChoices; })) return stepsResult(r.steps, { via: 'flags', kept: kept });
        }
        if (k === 'question' && top && top.cov >= 0.34 && top.score >= 2.4) return answered(hits, t);
        if (k === 'question' && top && top.score >= 3 && titleOverlap(t, top)) return answered(hits, t);          // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- a chatty question ("whats the deal with clearcoat") dilutes coverage; the top article whose own title / aliases carry the question's word answers it offline instead of the online model
        if (k !== 'question' && confident(top, k)) return answered(hits, t);
        var ls2 = (k !== 'question' && LOOK_RE.test(t)) ? lookStep(t, env) : null; if (ls2) return stepsResult(ls2, { look: true, via: 'look' });
        if (last && k !== 'question' && (BARE_ADJ_RE.test(t) || SAME_RE2.test(t))) return asked('adjust', 'What should change on the ' + lastLabel(last) + '?', ['Make the ' + lastLabel(last) + ' darker', 'Make the ' + lastLabel(last) + ' lighter', 'Make the ' + lastLabel(last) + ' glossier']);
        if (!APP_WORD_RE.test(t) && !new RegExp('\\b(?:' + COLOUR_WORDS + '|hood|roof|trunk|spoiler|wing|bumpers?|sides?|doors?|car|chrome|matte|gloss|satin|metallic|pearl|candy|carbon|camo|flake|shine|pattern|texture|spec|colou?rs?)\\b', 'i').test(t)) return k === 'question' ? local('offtopic') : asked('unclear', 'I did not catch that. Tell me what to change (for example “make the hood red”), or ask about the app.', START_CHIPS);
        if (k === 'question' && /^\s*how (?:do|can|would|could|should) (?:i|you|we)\s+(?:make|get|do|create|add|put|paint|apply)\b/i.test(t)) {          // HELPER_V2 fix pass 4: "how do i make a snakeskin finish" = the look the catalogue knows, as steps
            var hq = t.replace(/^\s*how (?:do|can|would|could|should) (?:i|you|we)\s+(?:make|get|do|create|add|put|paint|apply)\s+/i, 'make it ').replace(/\?+\s*$/, ''), hed = null; try { hed = E && env && (env.palette || []).length ? E.plan(hq, env) : null; } catch (eH) { hed = null; }
            var hst = hed && hed.kind === 'ops' && hed.ops && hed.ops.length ? Bb.fromPlan(hed, env, hq).steps : []; if (!hst.length || hst.every(Bb.stepOpen)) { var hf = Bb.fromFlags(hq, env); if (hf.steps.length) hst = hf.steps; }
            if (hst.length) { Bb.check(hst, env); var hn = never(hst, {}, []); if (hn.steps.length && hn.steps.some(function (s) { return s.finish || s.tex || s.colour || (s.found && s.found.length); })) { hn.steps[0].note = 'There is no article for that, but the catalogue has the look: here it is as steps. Pick where it goes, then press Run.' + (hn.steps[0].note ? ' ' + hn.steps[0].note : ''); return stepsResult(hn.steps, { via: 'howto-steps' }); } }
        }
        return online(t0, k === 'question' ? 'no-article' : 'unknown');
    }

    // ------------------------------------------------------------------ in the app: claim a TYPED sentence (js/spb-pro-ai.js send(), offline mode only)
    function shadeHex(hex, f) { var h = String(hex).replace('#', ''); if (h.length === 3) h = h.replace(/./g, '$&$&'); var n = parseInt(h, 16); if (isNaN(n)) return hex; var c = [n >> 16 & 255, n >> 8 & 255, n & 255].map(function (v) { v = f < 0 ? v * (1 + f) : v + (255 - v) * f; return Math.max(0, Math.min(255, Math.round(v))); }); return '#' + c.map(function (v) { return ('0' + v.toString(16)).slice(-2); }).join(''); }
    // the last change in this chat: the copilot reads it from its LAST ai message, so a built-in reply in between ("a bit darker" -> steps) would hide it; skip the helper's own no-change replies
    function colMemOf(ctxs) {          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: { part: colour } from the change history, newest first
        var m = {}, n = 0; (ctxs || []).forEach(function (c) { if (!c || !c.act || !c.act.colour || !c.act.colour.hex) return; (c.targets || []).forEach(function (tg) { if (tg && tg.kind === 'part' && !m[tg.part]) { m[tg.part] = c.act.colour; n++; } }); }); return n ? m : null;
    }
    function inheritColour(ctx, mem) {          // a shine-only change keeps the colour the parts already had (so "a little brighter" after "less shiny" still knows the purple)
        if (!ctx || !ctx.act || (ctx.act.colour && ctx.act.colour.hex) || !mem) return ctx;
        var cs = (ctx.targets || []).map(function (tg) { return tg && tg.kind === 'part' ? mem[tg.part] : null; });
        if (!cs.length || !cs[0] || cs.some(function (c) { return !c || c.hex !== cs[0].hex; })) return ctx;
        return Object.assign({}, ctx, { act: Object.assign({}, ctx.act, { colour: cs[0] }) });
    }
    function ctxHistory() { var out = []; try { var L = W.spbProAI && W.spbProAI.log ? W.spbProAI.log() : []; for (var i = L.length - 1; i >= 0 && out.length < 12; i--) { var m = L[i]; if (m && m.role === 'ai' && m.editCtx && !m.undone) out.push(m.editCtx); } } catch (e) {} return out; }
    function lastCtx() { try { var L = W.spbProAI && W.spbProAI.log ? W.spbProAI.log() : []; for (var i = L.length - 1; i >= 0; i--) { var m = L[i]; if (!m || m.role !== 'ai') continue; if (m.editCtx) return m.undone ? null : m.editCtx; if (m.undoable && !m.undone) return null; if (!/built-in/i.test(String(m.metaText || m.meta || m.model || ''))) return null; } } catch (e) {} return null; }
    function claim(text, ctx) {
        var Bb = B(); if (!Bb || !Bb.state || typeof document === 'undefined') return null;
        if (!Bb.typedNow || !Bb.typedNow(text) || !Bb.offlineMode || !Bb.offlineMode()) return null;
        if (!IX) { load(); return null; }
        var env = (ctx && ctx.env) || Bb.envNow(); if (env && !env.last) { var lc = lastCtx(); if (lc) env = Object.assign({}, env, { last: lc }); }
        if (env) { var cm = colMemOf(ctxHistory()); if (cm) env = Object.assign({}, env, { colMem: cm, last: inheritColour(env.last, cm) }); }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper
        if (env) { var fresh = Date.now() - CS.t < 600000; env = Object.assign({}, env, { pending: fresh ? CS.pending : null, list: fresh ? CS.list : null, topic: fresh ? CS.topic : null, undone: env.last ? null : lastUndone(), nopaintLast: fresh ? CS.nopaint : null, noPaint: noPaintParts(env), inConvo: fresh && CS.t > 0 }); }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: parts with nothing to paint on this car          // HELPER_V2 fix pass 4: the conversation layer's memory
        var r = route(text, env); CS = nextState(CS, r, null); CS.t = Date.now();
        TRAIL = { text: String(text), cls: r.cls, via: r.via || null, pass: r.pass || null, why: r.why || null, steps: (r.steps || []).length, last: !!(env && env.last), pending: !!(env && env.pending), t: Date.now() };          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- which path read the turn (the in-app conversation gate reads it)
        var ART = { 'custom-art': 'drawing a picture (a face, an animal, a photo)', 'custom-logo': 'designing a new logo', 'custom-text': 'writing your own name or words', replica: 'copying an exact real livery', 'custom-design': 'designing a whole livery from a description', 'free-design': 'designing a whole livery from a description', element: 'drawing that graphic', photo: 'turning a photo into a paint' };
        if (r.pass === 'send' && r.say) { setTimeout(function () { try { if (W.spbProAI && W.spbProAI.send) W.spbProAI.send(r.say); } catch (eS) {} }, 600); var sd = reply(r, 'On it: “' + r.say + '”.'); sd.builder = true; return sd; }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: the composed request goes to the app's own element designer
        if (r.pass === 'undo' && !/^\s*(?:please\s+)?(?:undo|ctrl\s*\+?\s*z)\b/i.test(String(text || ''))) { var ulb = null; try { var UL = W.spbProAI && W.spbProAI.log ? W.spbProAI.log() : []; for (var ui = UL.length - 1; ui >= 0; ui--) { if (UL[ui] && UL[ui].role === 'ai' && UL[ui].undoable && !UL[ui].undone) { ulb = String(UL[ui].request || 'the last change').slice(0, 70); break; } } } catch (eL) { ulb = null; } var uok = false; if (ulb) { try { var uf3 = W.spbProAI && (W.spbProAI.undoLast || W.spbProAI._undoLast); uok = !!(uf3 && uf3()); } catch (eU3) { uok = false; } } if (uok) { var ur = reply(r, 'Undone: ' + ulb + '. Your paint is back the way it was.'); ur.howto = false; return ur; } }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: in-app gate b4-150 -- "back to how it was" fell to the online model (which once said it could not undo); a plain "undo" keeps the app's own path
        if (r.pass === 'redo') { var rdn = null; try { rdn = W.spbProAI && W.spbProAI._redoLast ? W.spbProAI._redoLast() : null; } catch (eR) { rdn = null; } if (rdn) { var rdr = reply(r, 'Redone: ' + rdn + '. It is back on the car (Undo takes it off again).'); rdr.howto = false; return rdr; } }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: in-app gate b3-160 -- a typed "redo" went to the online model, which could not redo; the copilot's own redo of the change undone last (nothing to redo: the app path as before)
        if (r.pass && !(r.steps || []).length && r.pass !== 'undo-ask') return null;          // the app's own offline designer / element / layer / undo paths do these (HELPER_V2 phase 3)
        // HELPER_V2 blind patterns own these first (a negation / removal / vague ask, a clause-by-clause reading, a custom-art decline): the setup checks would read "dont touch the numbers" as a numbers problem
        var mine = r.cls === 'ASK' || !!r.local || !!r.lead || (r.steps || []).length > 0 || !!(r.kept && r.kept.length) || /^(clauses|protect|looks|fade|element|frame|pin|entity)$/.test(r.via || '') || (r.cls === 'ONLINE' && !!ART[r.why]);          // HELPER_V2 phase 3: every reading with steps is shown here, so the never-touch filter always applies
        if (!mine) {
            var S0 = W.SpbSupport, sc = null; try { sc = S0 && S0.classify ? S0.classify(text) : null; } catch (e) {}
            if (sc && (sc.kind === 'diagnose' || sc.kind === 'error')) return null;          // the live setup checks (user ID, files, folder) answer these with the buyer's own data
            var SH = W.SpbSelfHelp, shk = null; try { shk = SH && SH.classify ? SH.classify(text) : null; } catch (e2) {}
            if (shk && shk.kind === 'explain_state') return null;          // "what is loaded / which layers": answered from the live state
        }
        // HELPER_V2 phase 3: off-topic / small talk = one short local line, no card, no online call
        if (r.local) { var lo = reply(r, r.answer.text); lo.howto = false; lo.asked = { question: '', options: START_CHIPS.slice() }; return lo; }
        // "no not that": take the last change back first, then ask what it should be
        if (r.pass === 'undo-ask') { var ok = false; try { var uf = W.spbProAI && (W.spbProAI.undoLast || W.spbProAI._undoLast); ok = !!(uf && uf()); } catch (eU) { ok = false; } /* HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: the app exports _undoLast only (no, undo that said nothing to take back) */ var ua = reply(r, (ok ? '' : 'There was nothing to take back. ') + (ok ? r.ask.text : r.ask.text.replace(/^OK, taking that back\.\s*/, ''))); ua.asked = { question: r.ask.text, options: (r.ask.chips || []).slice(0, 4) }; ua.builder = true; return ua; }
        // HELPER_V2 fix pass 6 2026-10-05 owner: keep improving the Offline Helper -- the answer was shown twice (chat bubble + answer card): the card carries it, the bubble only points there
        // ("What are layers?:" punctuation: a title that ends in ? / ! / . takes no extra stop)
        if (r.cls === 'ANSWER') { Bb.showAnswer(r, text); var at = String(r.answer.title || '').trim(); return reply(r, (r.lead ? r.lead + '\n' : '') + '📖 ' + at + (/[?!.…]$/.test(at) ? '' : '.') + ' The answer is in the card under the chat' + (r.answer.actions.length ? ', with “Do it” buttons' : '') + '.'); }
        if (r.cls === 'ONLINE') {
            var cf = Bb.configured && Bb.configured();
            if (ART[r.why]) {          // HELPER_V2 blind P4: an honest decline, no steps; with a model set, the copilot's own "Ask <model> instead" sends it there (the buyer chooses to spend)
                Bb.showOnline(r, text); var od = reply(r, 'That needs custom art: ' + ART[r.why] + '. The built-in helper only works with the finishes, colours and patterns already in Shokker, so it cannot make that. ' + (cf ? 'The online AI can: press “Ask ' + ((Bb.gearName && Bb.gearName()) || 'the online AI') + ' instead” below, or use Claude through MCP.' : 'The online AI can (DeepSeek, about a tenth of a cent per message: add a key in ⚙), or Claude through MCP.'));
                od.builder = !cf; return od;
            }
            if (cf) return null;          // a model is set: free chat goes to it as before
            Bb.showOnline(r, text);
            return reply(r, r.why === 'no-article' ? 'I do not have an article that answers that. The built-in helper answers questions about Shokker from its encyclopedia and builds changes step by step; free questions like this one need the online helper (DeepSeek, about a tenth of a cent per message: add a key in ⚙).' : 'That is free chat, which the built-in helper does not do: it builds changes step by step and answers questions about Shokker. The online helper (DeepSeek, about a tenth of a cent per message) can talk about anything: add a key in ⚙.');
        }
        if (r.look) { Bb.showSteps(r.steps, text); return reply(r, 'I could not read that as an exact change, so I searched the catalogue for “' + r.steps[0].foundFor + '”: pick a look in the builder under the chat (nothing changes until ▶ Run).'); }
        // HELPER_V2 blind patterns: a question back (negation, removal, vague, "a little less saturated") with clickable answers
        if (r.cls === 'ASK' && r.ask && !(r.steps || []).length) { var o = reply(r, r.ask.text); o.asked = { question: r.ask.text, options: (r.ask.chips || []).slice(0, 5) }; o.builder = true; return o; }
        // clause-by-clause / constraint / slang / complaint readings: shown here, because the app's own path would re-read the raw sentence
        if ((r.steps || []).length) {
            if (r.via === 'plan') { var ed0 = null; try { ed0 = Ed().plan(text, env); } catch (eP) { ed0 = null; } if (ed0 && (ed0.prohibited_edit || (ed0.protected_parts && ed0.protected_parts.length))) return null; }          // protected panels keep their own exact answer
            var tookBack = false; if (r.undoFirst) { try { var uf2 = W.spbProAI && (W.spbProAI.undoLast || W.spbProAI._undoLast); tookBack = !!(uf2 && uf2()); } catch (eU2) {} }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: a correction takes the last change back first
            Bb.showSteps(r.steps, text); var hq = r.steps.filter(function (s1) { return s1.ask && s1.hiddenInfo; })[0];
            if (hq) { var oh = reply(r, hq.ask + '\nPick one in the builder under the chat. Nothing is changed until you press ▶ Run.'); oh.builder = true; return oh; } var open = r.steps.filter(Bb.stepOpen).length, nd = (r.notDone || []).length ? '\nNot done: ' + r.notDone.map(function (x) { return '“' + x + '”'; }).join(', ') + (r.notDone.some(function (x) { return ELEMENT_RE.test(x) || FADE_RE.test(x); }) ? ' (stripes, flames and fades are drawn with their own tool: ask for that part on its own).' : ' (add it as another step, or ask the online AI).') : '', kp = (r.kept || []).length ? '\nKept as you asked: the ' + r.kept.join(', the ') + '.' : '';
            var o2 = reply(r, 'I read this as: ' + Bb.readAs(r.steps) + '.' + kp + nd + '\n' + (open ? 'Step' + (open > 1 ? 's' : '') + ' marked ⚠ need' + (open > 1 ? '' : 's') + ' a pick in the builder under the chat. Nothing is changed until you press ▶ Run.' : 'Check the steps in the builder under the chat, then press ▶ Run (or Edit any step). Nothing is changed until you do.')); o2.builder = true; o2.asked = { options: (r.chips || []).slice(0, 4) }; return o2;
        }
        return null;          // DO / PREFILL / ASK from a parser plan: the copilot's own edit path hands it to the builder (SpbOfflineBuilder.claim)
    }
    function clip(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1).replace(/\s+\S*$/, '') + '…' : s; }
    // builder:false keeps the copilot's own "✨ Ask <gear model> instead" under an offline answer / look search (shown only when a model is set); the ONLINE card carries its own buttons
    function reply(r, text) { return { offline: true, text: tidy(text), queue: [], usage: { cost: 0 }, calls: 0, model: 'built-in', tools: ['encyclopedia'], builder: r.cls === 'ONLINE', howto: r.cls === 'ANSWER', asked: { options: [] }, metaText: '✦ built-in helper · no AI used' }; }          // asked:{options:[]} hides "Look & refine" / "Another take" (nothing was painted to refine)

    // ------------------------------------------------------------------ the answer card (drawn in the builder dock)
    var ARTW = { 'custom-art': 'a face, an animal or a photo', 'custom-logo': 'a new logo', 'custom-text': 'your own name or words', replica: 'an exact copy of a real livery', 'custom-design': 'a whole livery from a description', 'free-design': 'a whole livery from a description', element: 'that graphic' };
    function cfg() { var Bb = B(); try { return !!(Bb && Bb.configured && Bb.configured()); } catch (e) { return false; } }
    function cardHtml(r) {
        if (!r) return '';
        if (r.cls === 'ONLINE') return '<div class="spb-ob-tcard spb-oa-card"><div class="spb-ob-hd"><b>💬 That needs the online helper</b><i>built-in helper · no AI</i><button type="button" class="spb-ob-x" data-ob="aclose">×</button></div><div class="spb-ob-art"><div class="spb-ob-tsum">' + (ARTW[r.why] ? 'This needs custom art (' + ARTW[r.why] + '). The built-in helper works only with the finishes, colours and patterns already in Shokker; the online AI or Claude through MCP can draw it.' : (r.why === 'no-article' ? 'I have no article that answers this.' : 'The built-in helper does not do free chat.') + ' It builds changes step by step and answers questions about Shokker.') + '</div><div class="spb-ob-row"><button type="button" class="spb-pai-act" data-ob="start">🧱 Build a change step by step</button><button type="button" class="spb-pai-act" data-ob="aenc">📖 Search the encyclopedia</button>' + (cfg() ? '' : '<button type="button" class="spb-pai-act hot" data-ob="gear">✨ Ask DeepSeek instead (add a key in ⚙)</button>') + '</div></div></div>';
        var A = r.answer, h = '<div class="spb-ob-tcard spb-oa-card"><div class="spb-ob-hd"><b>📖 ' + esc(A.title) + '</b>' + (A.level ? '<span class="spb-oa-lvl l-' + esc(A.level) + '">' + esc(A.level) + '</span>' : '') + '<i>answered offline · no AI</i><button type="button" class="spb-ob-x" data-ob="aclose" title="Close">×</button></div><div class="spb-ob-art">';
        if (A.faq) h += '<div class="spb-oa-q">“' + esc(A.faq) + '”</div>';
        h += '<div class="spb-ob-tsum">' + esc(A.text) + '</div>';
        if (A.how && A.how.length && A.text.indexOf('1. ') !== 0) h += '<ol class="spb-oa-how">' + A.how.map(function (x) { return '<li>' + esc(String(x).replace(/^\d+\.\s*/, '')) + '</li>'; }).join('') + '</ol>';
        if (A.shot) h += '<button type="button" class="spb-oa-shot" data-ob="aread" data-art="' + esc(A.id) + '" title="' + esc(A.shot.caption) + '"><img loading="lazy" alt="' + esc(A.shot.caption) + '" src="' + esc(A.shot.src) + '" onerror="this.parentNode.style.display=\'none\'"><span>' + esc(clip(A.shot.caption, 90)) + '</span></button>';
        h += '<div class="spb-ob-row"><button type="button" class="spb-ob-link" data-ob="aread" data-art="' + esc(A.id) + '">📖 Read the full article ›</button></div>';
        if (A.actions.length) h += '<div class="spb-ob-q">Do it</div><div class="spb-ob-row">' + A.actions.map(function (x, k) { return '<button type="button" class="spb-pai-act' + (k ? '' : ' hot') + '" data-ob="adoit" data-k="' + k + '" title="' + esc(x.do + ': ' + x.id) + '">' + (x.do === 'control' ? '👆 ' : '▶ ') + esc(x.label) + '</button>'; }).join('') + '</div>';
        if (r.hits.length > 1) h += '<div class="spb-ob-sec"><b>Also about this</b><div class="spb-ob-row">' + r.hits.slice(1, 3).map(function (x) { return '<button type="button" class="spb-ob-link" data-ob="aread" data-art="' + esc(x.id) + '">' + esc(x.title) + '</button>'; }).join('') + '</div></div>';
        return h + '</div></div>';
    }
    // a card button: returns true when it handled the click (the builder redraws after)
    function onAction(a, el, S) {
        var R = W.SpbEncyclopedia, Bb = B(), r = S.answer;
        if (a === 'aclose') { S.answer = null; return true; }
        if (a === 'aenc') { if (R && R.open) R.open(); return true; }
        if (a === 'aread') { if (R && R.open) R.open(el.getAttribute('data-art')); return true; }
        if (a === 'adoit' && r && r.answer) {
            var x = r.answer.actions[Number(el.getAttribute('data-k'))]; if (!x) return true;
            if (x.do === 'control') { if (R && R.showControl) R.showControl(x.id, x.label); return true; }
            S.answer = null; if (Bb && Bb.takeAction) Bb.takeAction({ do: x.do, id: x.id, label: x.label }); return true;
        }
        return false;
    }

    // HELPER_V2 blind P0/P5: with nothing to take back (js/spb-pro-ai.js complaintOf asks this), "dont touch / leave / keep the numbers" is a CONSTRAINT for the next change
    // and "my number disappeared" is a SYMPTOM with a troubleshooting article: neither is a complaint about a change
    function constraint(text) {
        var t = String(text || ''); if (NEG_START.test(t) && protect(t).words.length > 0) return true;
        if (!IX || !/\b(?:missing|disappear\w*|vanish\w*|gone|not (?:showing|there)|cant (?:find|see)|can'?t (?:find|see))\b/i.test(t) || kind(t) !== 'question') return false;
        return confident(search(t, 3)[0], 'question');
    }
    // HELPER_V2 fix pass 4: the conversation state the NEXT turn reads (env.pending = the helper's own open question, env.topic = what an answer was about)
    function nextState(st, r, ran) { return { list: r && r.list ? r.list : (st && st.list) || null, nopaint: r && r.nopaint ? r.nopaint : null, pending: r && r.pend ? r.pend : null, topic: r && r.cls === 'ANSWER' && r.topic ? r.topic : (r && r.cls === 'ASK' && st && st.topic && r.why === 'apply' ? st.topic : null) }; }
    var CS = { pending: null, topic: null, list: null, t: 0 };          // HELPER FIX PASS 7 2026-10-05: list = the last finish list ("use the second one")
    var TRAIL = null, NP = null;
    function noPaintParts(env) {          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: the parts that hold no body paint on THIS car (measured once per layer set)
        var Z = W.SpbProZone, C = W.SpbProCar; if (!Z || !Z.probeRegion || !C || !C.maskFor) return [];
        var bl = (env && env.bodyLayers) || [], key = bl.join('|') + '#' + ((W._psdLayers && W._psdLayers.length) || 0) + '#' + (typeof W.paintFileName !== 'undefined' ? W.paintFileName : '');
        if (NP && NP.key === key) return NP.list;
        var out = [];
        ['spoiler', 'trunk', 'hood', 'roof', 'front bumper', 'rear bumper', 'left side', 'right side'].forEach(function (p) { try { if (!C.maskFor(p)) return; var pr = Z.probeRegion(bl.length ? { island: p, layers: bl.slice() } : { island: p }); if (pr && ((!pr.note && pr.share_pct != null && Number(pr.share_pct) < 0.05) || /selects nothing/i.test(String(pr.note || '')))) out.push(p); } catch (e) {} });          // in-app gate b3-149: the owner ARCA spoiler probes as {share_pct: 0, note: "selects nothing on the paint"} -- the note IS the empty answer
        NP = { key: key, list: out }; return out;
    }          // the in-app conversation state (one chat); stale after 10 minutes
    function lastUndone() { try { var L = W.spbProAI && W.spbProAI.log ? W.spbProAI.log() : []; for (var i = L.length - 1; i >= 0; i--) { var m = L[i]; if (m && m.role === 'ai' && m.editCtx) return m.undone ? m.editCtx : null; } } catch (e) {} return null; }
    W.SpbOfflineAnswer = { _tidy: tidy, _chipOk: chipOk, _partsOf: p7PartsOf, colMemOf: colMemOf, inheritColour: inheritColour, _trail: function () { return TRAIL; }, _resetConvo: function () { CS = { pending: null, topic: null, list: null, t: 0 }; TRAIL = null; return true; }, load: load, nextState: nextState, ready: ready, build: build, search: search, route: route, kind: kind, claim: claim, constraint: constraint, cardHtml: cardHtml, onAction: onAction, _frame: function (t) { return { split: splitFrames(t), fr: frameOps(t, { keep: [], only: [], keepColours: false }), frames: splitFrames(t).map(clauseFrame) }; }, answerOf: answerOf, lookQuery: lookQuery, catalogue: catalogue, toks: toks, _ix: function () { return IX; } };
    if (typeof document !== 'undefined' && typeof fetch === 'function') { try { setTimeout(function () { load(); }, 4000); } catch (e) {} }          // warm the index after boot (about 2 MB, cached by the browser)
})();
