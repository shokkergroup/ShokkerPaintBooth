/* SPB Encyclopedia - the standalone full-window reader.
   OFFLINE_BUILDER 2026-10-04 owner: offline = guided builder + encyclopedia. Owner on this reader: "a true SPB Encyclopedia that explains how
   spec channels work, what different stuff in the app does... anything people could possibly want to know about the program... Thorough."
   Data (read-only here, written by the encyclopedia lanes): data/encyclopedia/<domain>.json (hand-written articles, schema in _schema.md),
   generated pages in data/encyclopedia/pages/*.json listed by the manifests *_pages.json, figures in figures.json + figures/.
   The small index js/spb-encyclopedia-data.js (terms, aliases) is read through window.SpbEnc (js/spb-offline-builder.js) only.
   Server: /data/encyclopedia/** is served by server_v5.py serve_encyclopedia_data; packaging: electron-app/copy-server-assets.js.
   API: window.SpbEncyclopedia = { open(id?), close(), get(id) -> Promise<article>, search(q), pageForKey(kind, key), boot() }.
   Deep links: SpbEncyclopedia.open('<article id>' | '<index term id>'), or a URL hash #enc:<id>. */
(function () {
    'use strict';
    var W = window, D = document, BASE = 'data/encyclopedia/';
    // ------------------------------------------------------------------ the table of contents: 16 Parts (docs/handoff_reports/ENCYCLOPEDIA_V2_PLAN.md section 2)
    var PARTS = [
        { n: 'I', t: 'Getting started', d: ['workflows', 'concepts'], x: [['paths', '🎓 Learning paths: guided courses']], ic: '🚀' },
        { n: 'II', t: 'The window, panel by panel', d: ['ui_shell', 'settings', 'history'], ic: '🪟' },
        { n: 'III', t: 'Tools', d: ['tools'], ic: '🛠' },
        { n: 'IV', t: 'Zones', d: ['zones'], ic: '🧩' },
        { n: 'V', t: 'Layers and PSD templates', d: ['layers'], ic: '📚' },
        { n: 'VI', t: 'Bases and finishes', d: ['finishes'], g: ['finish'], x: [['cmp', '⇄ Compare two finishes']], ic: '✨' },
        { n: 'VII', t: 'Patterns', d: ['patterns'], g: ['pattern', 'specpat'], ic: '🔷' },
        { n: 'VIII', t: 'The spec map', d: ['spec'], x: [['explorer', '🔬 Spec Explorer: drag R, G and B']], ic: '🔬' },
        { n: 'IX', t: 'Spec Sculpt Lab', d: ['spec_sculpt'], ic: '🗿' },
        { n: 'X', t: 'Preview, render and export', d: ['preview_render'], ic: '🖼' },
        { n: 'XI', t: 'Cars and templates', d: ['cars', 'car_pages'], ic: '🏁' },
        { n: 'XII', t: 'Shokk Drop and Fracture', d: ['shokk_drop'], ic: '💥' },
        { n: 'XIII', t: 'Chat and the AI helper', d: ['ai_copilot'], ic: '💬' },
        { n: 'XIV', t: 'Style ideas, recipes and workflows', d: ['ideas', 'recipes', 'playbook'], ic: '📋' }, // orchestrator 2026-10-05: ideas.json design-style recipes (ENC_IDEAS.md)
        { n: 'XV', t: 'Troubleshooting', d: ['support'], g: ['help'], ic: '🩺' },
        { n: 'XVI', t: 'Reference', d: ['shortcuts'], g: ['controls', 'glossary', 'figures'], ic: '📇' }
    ];
    var GEN = {
        finish: { man: 'finish_pages.json', label: 'Every finish, shelf by shelf', kind: 'finish', pre: 'finish_' },
        pattern: { man: 'pattern_pages.json', label: 'Every pattern', kind: 'pattern', pre: 'pattern_' },
        specpat: { man: 'spec_pattern_pages.json', label: 'Every spec pattern (shine overlays)', kind: 'spec', pre: 'specpat_' },
        controls: { man: 'controls_pages.json', label: 'Control index: every slider, button and switch', kind: 'control', pre: 'controls_' },
        help: { man: 'help_pages.json', label: 'Quick answers: how do I, support and topics', kind: 'help', pre: 'help_' },
        glossary: { label: 'Glossary: every word the helper knows' },
        figures: { label: 'All diagrams' }
    };
    // v3 (2026-10-04): REAL app screenshots from screens.json {id, title, caption, file, alt, article_ids[], kind}; SCRA = article id -> screen ids
    var SCR = {}, SCRL = [], SCRA = {};
    var A = {}, DOMS = {}, PFILE = {}, MAN = {}, FIG = {}, FIGL = [], EXTRA = [], _get = {}, _boot = null, _bg = null, CORPUS = null;
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function getJSON(p) { return _get[p] || (_get[p] = (typeof fetch === 'function' ? fetch(BASE + p, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }) : Promise.resolve(null)).catch(function () { return null; })); }
    // OWNER RULE 2026-10-04: hidden features (Easy mode) are never shown: no chapter, contents entry, link, search hit or button.
    // Built-in copy of scripts/ai_atlas/enc_hidden_features.json; the live list (served as data/encyclopedia/hidden_features.json) is merged at boot.
    var HID = { domains: ['easy_mode'], prefixes: ['easy_mode.', 'controls_easy_mode_'], ids: [/^easy\./, /^mode\.easy$/, /^spbModeEasyBtn$/, /^hdi\.easy_/, /^hdi\.use_easy$/, /^topic\.easy_pro$/, /^sculpt\.btnEasyMode$/, /(^|[._:])easy([._:]|$)/i],
        text: [/\beasy[\s-]*mode\b/i, /\bEASY\b/, /\beasy\s+(vs|or|and)\s+pro\b/i, /\bpro\s*[|\/,]\s*(?:chat\s*[|\/,]?\s*(?:and\s+)?)?easy\b/i, /\bpaint[\s-]*by[\s-]*numbers\b/i] };
    function loadHidden(h) {
        if (!h) return;
        try {
            (h.hidden_domains || []).concat(h.features || []).forEach(function (d) { if (HID.domains.indexOf(d) === -1) HID.domains.push(d); });
            (h.hidden_article_prefixes || []).forEach(function (x) { if (HID.prefixes.indexOf(x) === -1) HID.prefixes.push(x); });
            (h.hidden_record_ids || []).forEach(function (x) { try { HID.ids.push(new RegExp(x)); } catch (e) {} });
            (h.gate_text_patterns || []).forEach(function (x) { try { HID.text.push(new RegExp(x.re, x.flags || '')); } catch (e) {} });
        } catch (e) {}
    }
    function hidId(id) {
        id = String(id || ''); var dom = id.split('.')[0], key = id.indexOf('.') > 0 ? id.slice(id.indexOf('.') + 1) : id;
        if (HID.domains.indexOf(dom) !== -1) return true;
        for (var i = 0; i < HID.prefixes.length; i++) if (id.indexOf(HID.prefixes[i]) === 0 || (dom + '.').indexOf(HID.prefixes[i]) === 0) return true;
        return HID.ids.some(function (r) { return r.test(id) || r.test(key); });
    }
    function hidText(x) { x = String(x || ''); return !!x && HID.text.some(function (r) { return r.test(x); }); }
    function hidArt(a) { return !a || hidId(a.id) || hidText(a.title) || hidText((a.aliases || []).join(' | ')); }
    function hidTerm(t) { return !t || hidId(t.id) || hidText(t.title) || hidText((t.aliases || []).join(' | ')); }
    function terms() { var E = Enc(); return ((E && E.terms && E.terms()) || []).filter(function (t) { return !hidTerm(t); }); }
    // a sentence or list item about a hidden feature is dropped from the page (the rest of the article stays)
    function scrub(s) { return String(s || '').split(/\n{2,}/).map(function (p) { return p.split(/(?<=[.!?])\s+/).filter(function (x) { return !hidText(x); }).join(' '); }).filter(function (p) { return p.trim(); }).join('\n\n'); }
    function clean(a) {
        var o = {}, k; for (k in a) o[k] = a[k];
        o.summary = scrub(a.summary); o.what = scrub(a.what);
        ['when', 'how', 'tips', 'pitfalls'].forEach(function (f) { o[f] = (a[f] || []).filter(function (x) { return !hidText(typeof x === 'string' ? x : (x && (x.text || x.label))); }); });
        o.controls = (a.controls || []).filter(function (c) { return !hidText(c.label) && !hidText(c.effect) && !(c.inv && hidId(c.inv)); });
        o.related = (a.related || []).filter(function (r) { return !hidId(r) && !(A[r] && hidArt(A[r])); });
        o.actions = (a.actions || []).filter(function (x) { return !(x && ((x.id && hidId(x.id)) || hidText(x.label))); });
        o.links = (a.links || []).filter(function (l) { return !hidText(l.label) && !hidText(l.target); });
        o.figures = (a.figures || []).filter(function (f) { return !FIG[f] || !hidText(FIG[f].caption + ' ' + FIG[f].title); });
        o.deep = (a.deep || []).filter(function (d) { return d && !hidText(d.heading); }).map(function (d) { return { heading: d.heading, body: scrub(d.body) }; }).filter(function (d) { return d.body; });
        o.examples = (a.examples || []).filter(function (x) { return x && !hidText([x.title, x.goal, x.result, JSON.stringify(x.settings || {})].join(' | ')); });
        o.combos = (a.combos || []).filter(function (x) { return x && x.with && !hidId(x.with) && !hidText(x.why); });
        o.faq = (a.faq || []).filter(function (x) { return x && x.q && !hidText(x.q + ' ' + (x.a || '')); });
        o.mistakes = (a.mistakes || []).filter(function (x) { return x && !hidText([x.symptom, x.cause, x.fix].join(' ')); });
        o.protips = (a.protips || []).filter(function (x) { return x && !hidText(strip(x)); });
        return o;
    }
    function listOf(d) { return !d ? [] : (Array.isArray(d) ? d : (d.articles || [])); }
    function addFile(dom, data) { var ids = []; if (!hidId(dom + '.')) listOf(data).forEach(function (a) { if (a && a.id && !hidArt(a)) { A[a.id] = a; ids.push(a.id); } }); DOMS[dom] = ids; return ids; }
    function Enc() { return W.SpbEnc || null; }
    function partDomains() { var L = []; PARTS.forEach(function (p) { L = L.concat(p.d); }); return L; }
    function partOf(id) {
        var dom = String(id || '').split('.')[0];
        for (var i = 0; i < PARTS.length; i++) if (PARTS[i].d.indexOf(dom) !== -1) return PARTS[i];
        for (var g in GEN) if (GEN[g].pre && dom.indexOf(GEN[g].pre) === 0) return PARTS.filter(function (p) { return (p.g || []).indexOf(g) !== -1; })[0] || null;
        if (EXTRA.indexOf(dom) !== -1) return MORE;
        return PARTS[15];
    }
    var MORE = { n: '+', t: 'More articles', d: EXTRA, ic: '➕' };
    function genOf(dom) { for (var g in GEN) if (GEN[g].pre && String(dom).indexOf(GEN[g].pre) === 0) return g; return null; }
    // ------------------------------------------------------------------ loading
    function boot() {
        if (_boot) return _boot;
        var hand = partDomains();
        _boot = getJSON('hidden_features.json').then(function (hf) {
            loadHidden(hf); var more = [];
            terms().forEach(function (t) { var a = artPtr(t); if (a) more.push(a.dom); });
            more.forEach(function (d) { if (d && !hidId(d + '.') && hand.indexOf(d) === -1 && EXTRA.indexOf(d) === -1 && !genOf(d) && !/_pages$/.test(d) && d !== 'figures') EXTRA.push(d); });
            var jobs = hand.concat(EXTRA).map(function (d) { return getJSON(d + '.json').then(function (x) { addFile(d, x); }); });
            jobs.push(getJSON('screens.json').then(addScreens));
            jobs.push(getJSON('figures.json').then(function (f) { FIGL = listOf(f).filter(function (x) { return x && x.id; }); FIGL.forEach(function (x) { FIG[x.id] = x; }); }));
            Object.keys(GEN).forEach(function (g) { if (GEN[g].man) jobs.push(getJSON(GEN[g].man).then(function (mf) { MAN[g] = mf || { parts: [] }; MAN[g].parts = (MAN[g].parts || []).filter(function (p) { return !hidId(p.domain + '.') && HID.domains.indexOf(p.group) === -1; }); MAN[g].parts.forEach(function (p) { PFILE[p.domain] = { file: p.file, group: p.group, gen: g, count: p.count, firstKey: p.firstKey, lastKey: p.lastKey }; }); })); });
            return Promise.all(jobs);
        }).then(function () { CORPUS = null; return true; });
        return _boot;
    }
    // the control pages are small (19 files): load them in the background so search and A-Z cover every control
    function addScreens(f) {
        var L = Array.isArray(f) ? f : ((f && (f.screens || f.items || f.articles)) || []);
        L.forEach(function (x) {
            if (!x || !x.id || !x.file || SCR[x.id] || hidText([x.title, x.caption, x.alt].join(' | '))) return; SCR[x.id] = x; SCRL.push(x);
            (x.article_ids || []).forEach(function (aid) { (SCRA[aid] = SCRA[aid] || []).push(x.id); });
        });
        CORPUS = null; return SCRL.length;
    }
    function scrSrc(x) { var f = String(x.file || ''); return /^(\/|https?:|data:)/.test(f) ? f : BASE + f; }
    function screensOf(a) {
        var seen = {}, out = []; (a.screens || []).concat(SCRA[a.id] || [], a._term ? (SCRA[a._term] || []) : []).forEach(function (id) { if (SCR[id] && !seen[id]) { seen[id] = 1; out.push(SCR[id]); } }); return out;
    }
    // finish / pattern pages: the car render of this exact look (car_<key>), else of its shelf (cat_<shelf>)
    function carShot(a) {
        var la = lookAction(a); if (!la) return null; var key = String(la.id), bare = key.replace(/^.*::/, ''), C = ['car_' + key, 'car_' + key.replace(/::/g, '_'), 'car_' + bare];
        for (var i = 0; i < C.length; i++) if (SCR[C[i]]) return { s: SCR[C[i]], exact: true };
        var grp = PFILE[a.domain] ? PFILE[a.domain].group : ''; if (!grp) return null; var sl = norm(grp).replace(/ /g, '_'), G = ['cat_' + sl, 'cat_' + grp, 'cat_' + String(grp).toLowerCase()];
        for (var j = 0; j < G.length; j++) if (SCR[G[j]]) return { s: SCR[G[j]], exact: false, grp: grp };
        return null;
    }
    function bgLoad() { if (_bg) return _bg; _bg = boot().then(function () { return Promise.all(((MAN.controls || {}).parts || []).concat((MAN.help || {}).parts || []).map(function (p) { return getJSON(p.file).then(function (x) { addFile(p.domain, x); }); })); }).then(function () { CORPUS = null; if (S.open && S.q) drawNav(); }); return _bg; }
    function artPtr(t) {      // index term -> its v2 article: term.art = "<domain>#<id>" (plan section 4) or term.article / term.file
        if (!t) return null; var a = t.art || t.article || null; if (!a) return null; a = String(a);
        var m = /^([^#]+)#(.+)$/.exec(a); if (m) return { dom: m[1].replace(/\.json$/, '').replace(/^pages\//, ''), id: m[2] };
        return { dom: a.split('.')[0], id: a };
    }
    function loadDomain(dom) {
        if (DOMS[dom]) return Promise.resolve(DOMS[dom]);
        var pf = PFILE[dom], path = pf ? pf.file : (/_\d+$/.test(dom) ? 'pages/' + dom + '.json' : dom + '.json');
        return getJSON(path).then(function (x) { return x ? addFile(dom, x) : (DOMS[dom] = []); });
    }
    function get(id) {
        id = String(id || ''); if (!id) return Promise.resolve(null);
        return boot().then(function () {
            if (hidId(id)) return null;
            if (A[id]) return A[id];
            if (/^cat:/.test(id)) return catArticle(id);
            var E = Enc(), t = E && E.term ? E.term(id) : null;
            if (t && hidTerm(t)) return null;
            if (t) { var ap = artPtr(t); if (ap) return loadDomain(ap.dom).then(function () { return A[ap.id] ? merge(A[ap.id], t) : termArticle(t); }); var hid = byName(t); return hid ? merge(A[hid], t) : termArticle(t); }
            var dom = id.split('.')[0];
            return loadDomain(dom).then(function () { return A[id] || null; });
        });
    }
    function merge(a, t) {
        var o = {}; for (var k in a) o[k] = a[k]; o._term = t.id;
        var have = actsOf(a).map(function (x) { return x.do + ':' + x.id; }), extra = (t.choices || []).map(normAct).filter(function (x) { return x && have.indexOf(x.do + ':' + x.id) === -1; });
        if (extra.length) o.actions = (a.actions || []).concat(extra.slice(0, 8));
        return o;
    }
    var ALIAS = null;
    function byName(t) {
        if (!ALIAS) { ALIAS = {}; partDomains().concat(EXTRA).forEach(function (d) { (DOMS[d] || []).forEach(function (id) { var a = A[id]; [a.title].concat(a.aliases || []).forEach(function (x) { var k = norm(x); if (k && !ALIAS[k]) ALIAS[k] = id; }); }); }); }
        // HELPER_V2 2026-10-04 owner: keep improving the Offline Helper. Best candidate, not first alias hit: "Candy paint" used to open
        // "Colour scale, depth, flip and underglow" (it lists "candy paint" as an alias) instead of the candy article. Exact title > title that
        // carries the term's head word > the term's own title as an alias > any alias.
        var ks = [t.title].concat(t.aliases || []).map(norm), head = (norm(t.title).split(' ')[0] || ''), best = null, bs = -1;
        for (var i = 0; i < ks.length; i++) {
            var id = ALIAS[ks[i]]; if (!id) continue; var at = norm(A[id].title), s = 0;
            if (at === ks[0]) s += 3; if (head.length > 2 && (' ' + at + ' ').indexOf(' ' + head) !== -1) s += 2; if (i === 0) s += 1;
            if (s > bs) { bs = s; best = id; }
        }
        return best;
    }
    // every action shape -> {do, id, label}: v2 {do, id} and the index's {finish_id | pattern_id | spec_id, label}
    function normAct(x) {
        if (!x) return null; if (x.do && x.id) return { do: x.do, id: x.id, label: x.label || '' };
        if (x.finish_id) return { do: 'finish', id: x.finish_id, label: x.label || '' }; if (x.pattern_id) return { do: 'pattern', id: x.pattern_id, label: x.label || '' }; if (x.spec_id) return { do: 'spec', id: x.spec_id, label: x.label || '' };
        if (x.choice) return normAct(x.choice); return null;
    }
    function actsOf(a) { return ((a && a.actions) || []).map(normAct).filter(Boolean); }
    function termArticle(t) {
        var E = Enc(); var p = E && E.indexArticle ? E.indexArticle(t.id) : (E && E.article ? E.article(t.id) : Promise.resolve(null));
        return Promise.resolve(p).then(function (a) { if (!a) return null; var o = {}; for (var k in a) o[k] = a[k]; o._term = t.id; o._gloss = true; return o; });
    }
    // ------------------------------------------------------------------ the catalogue (finish / pattern / spec names) and its pages
    function cat() {
        if (cat._c) return cat._c; var out = [];
        function add(list, kind, pre) { (list || []).forEach(function (x) { if (x && x.id && x.name) out.push({ kind: kind, key: pre + x.id, id: x.id, name: String(x.name), desc: String(x.desc || '') }); }); }
        try { add(typeof BASES !== 'undefined' ? BASES : null, 'finish', 'base::'); } catch (e) {}
        try { add(typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : null, 'finish', 'monolithic::'); } catch (e) {}
        try { add(typeof PATTERNS !== 'undefined' ? PATTERNS : null, 'pattern', ''); } catch (e) {}
        try { add(typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : null, 'spec', ''); } catch (e) {}
        if (out.length) cat._c = out; return out;
    }
    function catItem(kind, key) { var L = cat(); for (var i = 0; i < L.length; i++) if (L[i].kind === kind && (L[i].key === key || L[i].id === key)) return L[i]; return null; }
    // finish / pattern / spec key -> its generated page id (the manifest parts are sorted by key inside a shelf)
    function pageForKey(kind, key) {
        return boot().then(function () {
            var g = kind === 'finish' ? 'finish' : (kind === 'pattern' ? 'pattern' : 'specpat'), full = kind === 'finish' ? key : (kind === 'pattern' ? 'pattern::' : 'spec::') + key;
            var parts = ((MAN[g] || {}).parts || []).filter(function (p) { return p.firstKey <= full && full <= p.lastKey; });
            var i = 0;
            function next() {
                if (i >= parts.length) return null; var p = parts[i++];
                return loadDomain(p.domain).then(function (ids) {
                    for (var j = 0; j < ids.length; j++) { var a = A[ids[j]]; if ((a.actions || []).some(function (x) { return x && x.do === kind && (x.id === key || x.id === full); })) return a.id; }
                    return next();
                });
            }
            return next();
        });
    }
    function catArticle(id) {
        var m = /^cat:(finish|pattern|spec):(.+)$/.exec(id); if (!m) return null; var c = catItem(m[1], m[2]); if (!c) return null;
        return pageForKey(c.kind, c.key).then(function (pid) {
            if (pid && A[pid]) return A[pid];
            return { id: id, title: c.name, domain: c.kind, summary: c.desc || ('A ' + c.kind + ' in the catalogue.'), what: '', when: [], how: [], controls: [], tips: [], pitfalls: [], related: [], actions: [{ do: c.kind, id: c.key }], figures: [], _cat: true };
        });
    }
    function thumbUrl(kind, key, size) {
        size = size || 240; key = String(key || '');
        if (kind === 'pattern') return '/api/swatch/pattern/' + encodeURIComponent(key.replace(/^pattern::/, '')) + '?size=' + size + '&color=9a9aa8';
        if (kind === 'spec') return '/api/spec-pattern-preview/' + encodeURIComponent(key.replace(/^spec::/, ''));
        var m = /^(base|monolithic)::(.+)$/.exec(key); return m ? '/api/swatch/' + m[1] + '/' + encodeURIComponent(m[2]) + '?size=' + size + (m[1] === 'base' ? '&color=b4b4be' : '') : '';      // bases tint by a colour: a light neutral reads as the material itself
    }
    function lookAction(a) { var L = actsOf(a).filter(function (x) { return /^(finish|pattern|spec)$/.test(x.do); }); return L.length === 1 || (a && a._cat) || (L.length && genOf(a.domain || '')) ? L[0] : null; }
    // ------------------------------------------------------------------ search (titles, aliases, summaries, body text; instant)
    function norm(s) { return String(s || '').toLowerCase().replace(/['’]/g, '').replace(/[^a-z0-9#]+/g, ' ').trim(); }
    function corpus() {
        if (CORPUS) return CORPUS; var C = [], seen = {};
        Object.keys(A).forEach(function (id) {
            var a = A[id]; if (!a || seen[id]) return; seen[id] = 1; var g = genOf(a.domain || id.split('.')[0]);
            C.push({ faq: (a.faq || []).filter(function (x) { return x && x.q && !hidText(x.q + ' ' + (x.a || '')); }).map(function (x) { return { q: x.q, a: x.a, n: norm(x.q) }; }), id: id, type: g ? (g === 'controls' ? 'control' : GEN[g].kind) : 'article', title: String(a.title || id), tn: norm(a.title), al: norm((a.aliases || []).join(' | ')), sm: norm(a.summary), body: norm([a.what].concat(a.how || [], a.tips || [], a.pitfalls || [], (a.controls || []).map(function (c) { return c.label + ' ' + (c.effect || ''); }), (a.deep || []).map(function (d) { return d.heading + ' ' + d.body; }), (a.faq || []).map(function (x) { return x.q + ' ' + x.a; }), (a.mistakes || []).map(function (x) { return x.symptom + ' ' + x.cause + ' ' + x.fix; }), (a.protips || []).map(strip), (a.examples || []).map(function (x) { return x.title + ' ' + (x.goal || ''); })).join(' ')), sub: a.summary || '' });
        });
        terms().forEach(function (t) {
            var ap = artPtr(t); if (ap && A[ap.id]) { var e = C.filter(function (x) { return x.id === ap.id; })[0]; if (e) e.al += ' | ' + norm((t.aliases || []).join(' | ')); return; }
            C.push({ id: t.id, type: 'term', title: String(t.title || t.id), tn: norm(t.title), al: norm((t.aliases || []).join(' | ')), sm: norm(t.summary), body: '', sub: t.summary || '' });
        });
        EXT.search.forEach(function (t) { if (!t || !t.id || hidText(t.title)) return; C.push({ id: t.id, type: 'tool', title: t.title, tn: norm(t.title), al: norm((t.aliases || []).join(' | ')), alist: t.aliases || [], cue: t.cue ? new RegExp(t.cue, 'i') : null, sm: norm(t.summary), body: '', sub: t.summary || '', view: t.view }); });
        cat().forEach(function (c) { if (hidText(c.name)) return; var cid = 'cat:' + c.kind + ':' + c.key; C.push({ id: cid, type: c.kind, title: c.name, tn: norm(c.name), al: '', sm: norm(c.desc), body: '', sub: c.desc, key: c.key }); });
        CORPUS = C; return C;
    }
    var TYPEW = { article: 60, help: 30, term: 10, control: 15, finish: 0, pattern: 0, spec: 0 };     // a written article beats a glossary card or a control page with the same words
    function search(q, limit) {
        // ENC_SEARCH_LAB 2026-10-05: ranked by the ONE shared ranker (js/spb-enc-search.js, also used by the offline helper and the server);
        // search-as-you-type (the last word may be half typed). Articles index their full text; glossary terms and catalogue names index what they have.
        // The substring filter below is only the fallback when the ranker is not loaded.
        var SX = W.SpbEncSearch;
        if (SX && SX.build) {
            if (!String(q || '').trim()) return [];
            // two indexes: the articles + how-to pages (the same set the offline helper answers from), and the catalogue
            // (glossary terms, control pages, finishes, patterns, spec patterns, cars). Articles answer questions, so they rank first;
            // a catalogue item whose name IS the query (a finish typed by name) goes on top; the other catalogue hits follow.
            var C = corpus(), L = limit || 80;
            var isArt = function (e) { return e.type === 'article' || e.type === 'help' || e.type === 'tool'; };
            var doc = function (e) { var a = isArt(e) || e.type === 'control' ? A[e.id] : null; return a ? { id: e.id, title: a.title, aliases: a.aliases, summary: a.summary, what: a.what, how: a.how, when: a.when, tips: a.tips, pitfalls: a.pitfalls, controls: a.controls, faq: a.faq, mistakes: a.mistakes, deep: a.deep, generated: a.generated, kind: e.type } : { id: e.id, title: e.title, aliases: e.alist || (e.al ? e.al.split(' | ') : []), summary: e.sub, kind: e.type === 'tool' ? 'article' : e.type }; };
            var buildCat = function () { if (!C._sxc) C._sxc = SX.build(C.filter(function (e) { return !isArt(e); }).map(doc), { prefix: true }); };
            if (!C._sxa) {     // first search: index the ~500 articles now; the ~5,000 catalogue names right after, off the keystroke
                C._sxa = SX.build(C.filter(isArt).map(doc), { prefix: true }); C._by = {}; C.forEach(function (e) { C._by[e.id] = e; });
                setTimeout(buildCat, 0);
            }
            var byId = C._by, qk = SX.norm(q).trim(), sp = SX.spell ? SX.spell(C._sxa, q) : { fixes: [] };
            S.dym = sp.fixes && sp.fixes.length ? sp.text : '';          // ENC_READER_FIX: 'Showing results for ...' (the ranker already searched the repaired words)
            var ha = SX.search(C._sxa, q, { limit: L }).filter(function (h, i) { return byId[h.id] && (i === 0 || h.cov >= 0.45); });
            S.weak = !ha.length || ha[0].cov < 0.5;          // the best page covers under half of the question: say so instead of a confident list
            var ct = SX.toks ? SX.toks(sp.text || q) : []; S.amb = !S.weak && ct.length === 1 && ha.length >= 3 && ha[2].score >= 0.85 * ha[0].score ? ct[0] : '';          // one word, three near-equal pages ('mask'): ask which one
            var hc = C._sxc ? SX.search(C._sxc, q, { limit: L }).filter(function (h, i) { return byId[h.id] && (i === 0 && !ha.length || h.cov >= 0.6); })
                : C.filter(function (e) { return !isArt(e) && qk && e.tn.indexOf(qk) === 0; }).slice(0, 20).map(function (e) { return { id: e.id, faq: -1, fs: 0 }; });   // until the catalogue index is ready: names that start with the query
            var named = hc.filter(function (h) { var e = byId[h.id]; return qk && !/^(term|control)$/.test(e.type) && SX.norm(e.title).trim() === qk; });   // a finish / pattern / car typed by its exact name
            var cued = ha.filter(function (h) { var e = byId[h.id]; return e.type === 'tool' && e.cue && e.cue.test(SX.norm(q)); });          // 'compare two chrome finishes' -> the Compare tool first
            if (cued.length) ha = cued.concat(ha.filter(function (h) { return cued.indexOf(h) === -1; }));
            var hits = named.concat(ha, hc.filter(function (h) { return named.indexOf(h) === -1; })).slice(0, L);
            return hits.map(function (h) {
                var e = byId[h.id], a = A[h.id], f = a && h.faq >= 0 && h.fs >= 0.6 ? (a.faq || [])[h.faq] : null;
                e._fq = f && f.q && !hidText(f.q + ' ' + (f.a || '')) ? { q: f.q, a: f.a } : null; return e;
            });
        }
        var nq = norm(q); if (!nq) return []; var ws = nq.split(' '), out = [];
        corpus().forEach(function (e) {
            var sc = 0, hay = e.tn + ' ' + e.al + ' ' + e.sm + ' ' + e.body;
            if (e.faq && e.faq.length) hay += ' ' + e.faq.map(function (x) { return x.n; }).join(' ');
            for (var i = 0; i < ws.length; i++) if (hay.indexOf(ws[i]) === -1) return;
            // FINAL 3: an exact title always beats an alias or a summary match; title tiers stay above any alias match
            if (e.tn === nq) sc += (e.type === 'term' ? 60 : (/^(finish|pattern|spec)$/.test(e.type) ? 220 : 200)); else if (e.tn.indexOf(nq) === 0) sc += 110; else if ((' ' + e.tn + ' ').indexOf(' ' + nq + ' ') !== -1) sc += 100; else if (ws.every(function (w) { return e.tn.indexOf(w) !== -1; })) sc += 60;
            if (e.al && (' | ' + e.al + ' | ').indexOf(' | ' + nq + ' | ') !== -1) sc += (e.type === 'article' ? 55 : 25); else if (e.al.indexOf(nq) !== -1) sc += (e.type === 'article' ? 22 : 10);      // exact title > alias > summary
            if (e.faq && e.faq.length && ws.length > 1) { var fq = e.faq.filter(function (x) { return ws.every(function (w) { return x.n.indexOf(w) !== -1; }); })[0]; if (fq) { sc += 25; e._fq = fq; } else e._fq = null; } else e._fq = null;
            sc += Math.min(24, (e.sm.split(nq).length - 1) * 6 + (e.body.split(nq).length - 1) * 2);
            if (e.sm.indexOf(nq) !== -1) sc += 12; else if (ws.every(function (w) { return e.sm.indexOf(w) !== -1; })) sc += 6;
            if (e.body.indexOf(nq) !== -1) sc += 4;
            sc += TYPEW[e.type] || 0; sc -= Math.min(10, e.title.length / 12);
            out.push({ e: e, s: sc });
        });
        out.sort(function (a, b) { return b.s - a.s; });
        return out.slice(0, limit || 80).map(function (x) { return x.e; });
    }
    // ------------------------------------------------------------------ the reader UI
    // OFFLINE_BUILDER FINAL 3: extensions (js/spb-encyclopedia-learn.js) register extra views, clicks and article/home blocks here
    var EXT = { views: {}, clicks: {}, home: [], artTop: [], artEnd: [], search: [] };          // search: [{id, title, aliases, summary, view}] (ENC_READER_FIX: tools are findable)
    function extHtml(L, a) { return L.map(function (f) { try { return f(a) || ''; } catch (e) { return ''; } }).join(''); }
    var S = { open: false, hist: [], at: -1, tab: 'toc', q: '', exp: {}, view: null, note: '', fig: null };
    try { S.exp = JSON.parse(localStorage.getItem('spb_enc_exp') || '{}') || {}; } catch (e) { S.exp = {}; }
    function saveExp() { try { localStorage.setItem('spb_enc_exp', JSON.stringify(S.exp)); } catch (e) {} }
    var root = null;
    function el() {
        if (root) return root;
        root = D.createElement('div'); root.id = 'spbEnc'; root.className = 'spb-enc'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-label', 'SPB Encyclopedia'); root.hidden = true;
        root.innerHTML = '<div class="spb-enc-top"><div class="spb-enc-brand" data-e="home" title="Encyclopedia home">📖 <b>SPB Encyclopedia</b></div>' +
            '<button type="button" class="spb-enc-nb" data-e="back" title="Back (Alt+Left)">‹</button><button type="button" class="spb-enc-nb" data-e="fwd" title="Forward (Alt+Right)">›</button>' +
            '<div class="spb-enc-sbox"><input type="search" class="spb-enc-q" placeholder="Search everything: spec map, clearcoat, user id, a finish name…   ( / )" aria-label="Search the encyclopedia"></div>' +
            '<button type="button" class="spb-enc-nb spb-enc-x" data-e="close" title="Close (Esc)">×</button></div>' +
            '<div class="spb-enc-body"><nav class="spb-enc-nav"></nav><main class="spb-enc-main" tabindex="-1"></main></div><div class="spb-enc-lb" hidden></div>';
        D.body.appendChild(root);
        root.addEventListener('click', onClick);
        root.querySelector('.spb-enc-q').addEventListener('input', function (ev) { S.q = ev.target.value; S.tab = S.q ? 'search' : (S.tab === 'search' ? 'toc' : S.tab); drawNav(); });
        root.querySelector('.spb-enc-q').addEventListener('keydown', function (ev) {
            if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') { var hs = root.querySelectorAll('.spb-enc-nav .spb-enc-hit'); if (!hs.length) return; ev.preventDefault(); var k = Math.max(0, Math.min(hs.length - 1, (S.hi == null ? -1 : S.hi) + (ev.key === 'ArrowDown' ? 1 : -1))); S.hi = k; for (var j = 0; j < hs.length; j++) hs[j].classList.toggle('kb', j === k); try { hs[k].scrollIntoView({ block: 'nearest' }); } catch (e) {} return; }
            if (ev.key === 'Enter' && S.hi != null) { var hk = root.querySelectorAll('.spb-enc-nav .spb-enc-hit')[S.hi]; if (hk) { ev.stopImmediatePropagation(); go({ v: 'art', id: hk.getAttribute('data-id') }); return; } }
        });
        root.querySelector('.spb-enc-q').addEventListener('input', function () { S.hi = null; });
        root.querySelector('.spb-enc-q').addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && S.hi == null) { var f = root.querySelector('.spb-enc-nav .spb-enc-hit'), id = f ? f.getAttribute('data-id') : ((search(S.q, 1)[0] || {}).id); if (id) go({ v: 'art', id: id }); } });      // Enter = the first hit on screen
        D.addEventListener('keydown', onKey, true);
        return root;
    }
    function onKey(ev) {
        if (!S.open) return; var t = ev.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
        if (ev.key === 'Escape') { ev.stopPropagation(); ev.preventDefault(); if (S.fig) { S.fig = null; drawLb(); } else if (S.q) { S.q = ''; root.querySelector('.spb-enc-q').value = ''; S.tab = 'toc'; drawNav(); } else close(); return; }
        if (ev.key === '/' && !typing) { ev.preventDefault(); root.querySelector('.spb-enc-q').focus(); return; }
        if (!typing && (ev.key === '[' || ev.key === ']')) { ev.preventDefault(); step(ev.key === ']' ? 1 : -1); return; }
        if (ev.altKey && ev.key === 'ArrowLeft') { ev.preventDefault(); nav(-1); } else if (ev.altKey && ev.key === 'ArrowRight') { ev.preventDefault(); nav(1); }
    }
    // previous / next article inside the current Part ([ and ]); an extension view may provide its own step (S.step)
    function step(d) {
        if (S.step) { try { if (S.step(d) !== false) return; } catch (e) {} }
        var id = curId(); if (!id) return; var p = partOf(id); if (!p) return; var ids = []; p.d.forEach(function (x) { ids = ids.concat(DOMS[x] || []); });
        var k = ids.indexOf(id); if (k === -1) return; var n = ids[k + d]; if (n) go({ v: 'art', id: n });
    }
    function open(id) {
        el(); root.hidden = false; S.open = true; try { D.body.classList.add('spb-enc-on'); var bp = D.getElementById('spbEncBack'); if (bp) bp.remove(); } catch (e) {}
        boot().then(function () { bgLoad(); if (id) go({ v: 'art', id: String(id) }); else if (!S.view) go({ v: 'home' }); else { drawNav(); drawMain(); } });
        drawNav(); return true;
    }
    function close() { if (!root) return; root.hidden = true; S.open = false; S.fig = null; try { D.body.classList.remove('spb-enc-on'); } catch (e) {} }
    function same(a, b) { try { return !!(a && b && JSON.stringify(a) === JSON.stringify(b)); } catch (e) { return false; } }
    function go(v) { if (!same(S.hist[S.at], v)) { S.hist = S.hist.slice(0, S.at + 1); S.hist.push(v); S.at = S.hist.length - 1; } show(v); }
    function nav(d) { var k = S.at + d; if (k < 0 || k >= S.hist.length) return; S.at = k; show(S.hist[k]); }
    function show(v) {
        S.view = v; S.note = ''; S.cur = null; S.step = null; S.hi = null;
        if (v.v === 'art') { var want = v.id; drawMain(true); get(v.id).then(function (a) { if (S.view !== v) return; S.cur = a; if (a) { var p = partOf(a.id); if (p) S.exp[p.n] = true; } drawMain(); drawNav(); }); }
        else { drawMain(); drawNav(); }
    }
    // ---- left: contents / A-Z / search results
    function drawNav() {
        if (!root) return; var n = root.querySelector('.spb-enc-nav'), h = '';
        h += '<div class="spb-enc-tabs">' + [['toc', 'Contents'], ['az', 'A–Z']].map(function (x) { return '<button type="button" class="spb-enc-tab' + ((S.tab === x[0] || (S.tab === 'search' && x[0] === 'toc' && !S.q)) ? ' on' : '') + '" data-e="tab" data-t="' + x[0] + '">' + x[1] + '</button>'; }).join('') + '</div>';
        if (S.q) h += searchHtml(); else if (S.tab === 'az') h += azHtml(); else h += tocHtml();
        n.innerHTML = h;
        var on = n.querySelector('.on-art'); if (on && on.scrollIntoView && !S.q) { try { on.scrollIntoView({ block: 'nearest' }); } catch (e) {} }
    }
    function curId() { return S.view && S.view.v === 'art' ? (S.cur ? S.cur.id : S.view.id) : null; }
    function tocHtml() {
        var h = '<div class="spb-enc-toc">', cid = curId(), parts = PARTS.concat(EXTRA.length ? [MORE] : []);
        parts.forEach(function (p) {
            var ids = [], ex = !!S.exp[p.n]; p.d.forEach(function (d) { ids = ids.concat(DOMS[d] || []); });
            var isCur = cid && partOf(cid) === p;
            h += '<div class="spb-enc-part' + (ex ? ' ex' : '') + (isCur ? ' cur' : '') + '"><button type="button" class="spb-enc-ph" data-e="part" data-n="' + p.n + '"><i>' + (ex ? '▾' : '▸') + '</i><em>' + p.n + '</em><span>' + esc(p.t) + '</span><small>' + (ids.length || '') + '</small></button>';
            if (ex) {
                h += '<div class="spb-enc-pl">';
                ids.forEach(function (id) { var a = A[id]; h += '<button type="button" class="spb-enc-li' + (id === cid ? ' on-art' : '') + '" data-e="art" data-id="' + esc(id) + '">' + esc(a.title) + (a.quick ? ' <b class="spb-enc-star" title="Quick card in the AI helper">★</b>' : '') + '</button>'; });
                (p.g || []).forEach(function (g) { h += '<button type="button" class="spb-enc-li gen' + (S.view && S.view.v === 'gen' && S.view.g === g ? ' on-art' : '') + '" data-e="gen" data-g="' + g + '">' + esc(GEN[g].label) + ' ›</button>'; });
                (p.x || []).forEach(function (x) { if (EXT.views[x[0]]) h += '<button type="button" class="spb-enc-li tool' + (S.view && S.view.v === x[0] ? ' on-art' : '') + '" data-e="view" data-v="' + x[0] + '">' + esc(x[1]) + '</button>'; });
                h += '</div>';
            }
            h += '</div>';
        });
        return h + '</div>';
    }
    function azRows() {
        var rows = [], seen = {};
        Object.keys(A).forEach(function (id) { var a = A[id], g = genOf(a.domain || id.split('.')[0]); if (g === 'finish' || g === 'pattern' || g === 'specpat') return; var k = String(a.title || '').toLowerCase(); if (seen[k]) return; seen[k] = 1; rows.push({ id: id, title: a.title, type: g ? (g === 'help' ? 'article' : 'control') : 'article' }); });
        terms().forEach(function (t) { if ((t.tier || 3) > 2 || artPtr(t)) return; var k = String(t.title || '').toLowerCase(); if (seen[k]) return; seen[k] = 1; rows.push({ id: t.id, title: t.title, type: 'term' }); });
        rows.sort(function (a, b) { return String(a.title).localeCompare(String(b.title)); }); return rows;
    }
    function azHtml() {
        var rows = azRows(), by = {}, L = []; rows.forEach(function (r) { var c = String(r.title || '?').charAt(0).toUpperCase(); if (!/[A-Z]/.test(c)) c = /[0-9]/.test(c) ? '0–9' : '#'; if (!by[c]) { by[c] = []; L.push(c); } by[c].push(r); });
        L.sort(); var h = '<div class="spb-enc-letters">' + L.map(function (c) { return '<button type="button" data-e="letter" data-c="' + c + '">' + c + '</button>'; }).join('') + '</div><div class="spb-enc-az">';
        L.forEach(function (c) { h += '<div class="spb-enc-azg" data-letter="' + c + '"><b>' + c + '</b>' + by[c].map(function (r) { return '<button type="button" class="spb-enc-li t-' + r.type + (r.id === curId() ? ' on-art' : '') + '" data-e="art" data-id="' + esc(r.id) + '">' + esc(r.title) + '</button>'; }).join('') + '</div>'; });
        return h + '</div>';
    }
    var TYPEL = { article: 'Article', help: 'Quick answer', term: 'Glossary', control: 'Control', finish: 'Finish', pattern: 'Pattern', spec: 'Spec pattern', tool: 'Interactive tool' };
    function searchHtml() {
        S.dym = ''; S.weak = false; S.amb = '';
        var R = search(S.q, 80), h = '<div class="spb-enc-sr">', seenQ = {};          // ENC_READER_FIX: one FAQ snippet is shown once, not under every hit
        if (S.dym) h += '<div class="spb-enc-dym">Showing results for <b>' + esc(S.dym) + '</b> <span>(you typed “' + esc(S.q) + '”)</span></div>';
        h += '<div class="spb-enc-meta">' + (!R.length ? 'Nothing found for “' + esc(S.q) + '”. Try fewer words.' : (S.weak ? 'No close match for “' + esc(S.dym || S.q) + '”. The nearest pages:' : S.amb ? 'Several things in Shokker are called “' + esc(S.dym || S.q) + '”. Pick the one you mean:' : R.length + (R.length === 80 ? '+' : '') + ' results for “' + esc(S.dym || S.q) + '”')) + '</div>';
        R.forEach(function (e) {
            if (e.type === 'tool' && e.view) { var va = ''; Object.keys(e.view).forEach(function (k) { if (k !== 'v') va += ' data-' + k + '="' + esc(e.view[k]) + '"'; });
                h += '<button type="button" class="spb-enc-hit t-tool" data-e="view" data-v="' + esc(e.view.v) + '"' + va + '><span><b>' + esc(e.title) + '</b><i>' + TYPEL.tool + '</i><small>' + esc(String(e.sub || '').slice(0, 110)) + '</small></span></button>'; return; }
            var th = (e.type === 'finish' || e.type === 'pattern' || e.type === 'spec') && e.key ? '<img loading="lazy" alt="" src="' + esc(thumbUrl(e.type, e.key, 96)) + '" onerror="this.style.visibility=\'hidden\'">' : '';
            h += '<button type="button" class="spb-enc-hit t-' + e.type + (e.id === curId() ? ' on-art' : '') + '" data-e="art" data-id="' + esc(e.id) + '">' + th + '<span><b>' + esc(e.title) + '</b><i>' + esc(TYPEL[e.type] || '') + '</i><small>' + esc(String(e.sub || '').slice(0, 110)) + '</small>' + (e._fq && !seenQ[e._fq.n] && (seenQ[e._fq.n] = 1) ? '<em class="spb-enc-hfaq"><b>Q: ' + esc(e._fq.q) + '</b> ' + esc(String(e._fq.a || '').slice(0, 220)) + '</em>' : '') + '</span></button>';
        });
        return h + '</div>';
    }
    // ---- centre
    function crumbs(items) { return '<div class="spb-enc-crumbs">' + items.map(function (c, i) { return (i ? '<span>›</span>' : '') + (c.v ? '<button type="button" data-e="crumb" data-k="' + i + '">' + esc(c.t) + '</button>' : '<b>' + esc(c.t) + '</b>'); }).join('') + '</div>'; }
    var _crumbs = [];
    function setCrumbs(L) { _crumbs = L; return crumbs(L); }
    function drawMain(loading) {
        if (!root) return; var m = root.querySelector('.spb-enc-main'), v = S.view || { v: 'home' }, h = '';
        if (v.v === 'home') h = homeHtml();
        else if (v.v === 'part') h = partHtml(v.n);
        else if (v.v === 'gen') h = genHtml(v.g, v.grp);
        else if (EXT.views[v.v]) { try { h = EXT.views[v.v].html(v) || ''; } catch (e) { h = '<div class="spb-enc-art"><p>That page could not open.</p></div>'; } }
        else if (v.v === 'art') h = loading ? '<div class="spb-enc-art"><div class="spb-enc-meta">Opening…</div></div>' : (S.cur ? artHtml(S.cur) : '<div class="spb-enc-art"><h1>Not found</h1><p>There is no article called “' + esc(v.id) + '” yet. Try the search box.</p></div>');
        m.innerHTML = h; if (!loading) try { m.scrollTop = 0; } catch (e) {}
        if (EXT.views[v.v] && EXT.views[v.v].after) { try { EXT.views[v.v].after(v, m); } catch (e) {} }
        if (v.v === 'art' && !loading) miniToc(m);
        if (v.v === 'gen' && GEN[v.g] && GEN[v.g].man) genFill(v);
        dykTimer(v.v === 'home');
    }
    // long articles get a sticky "On this page" list (right rail when there is room, a compact strip otherwise); the current section lights up while scrolling
    function miniToc(m) {
        var art = m && m.querySelector('article.spb-enc-art'); if (!art) return; var hs = art.querySelectorAll(':scope > section > h2'); if (hs.length < 5) return;
        var L = []; for (var i = 0; i < hs.length; i++) { hs[i].id = 'encs' + i; L.push('<button type="button" data-e="otp" data-k="' + i + '">' + esc(hs[i].textContent) + '</button>'); }
        var aside = D.createElement('aside'); aside.className = 'spb-enc-otp'; aside.innerHTML = '<b>On this page</b>' + L.join(''); art.insertBefore(aside, art.querySelector('h1').nextSibling);
        art.classList.add('has-otp');
        var tick = function () { var top = m.getBoundingClientRect().top + 90, cur = 0; for (var j = 0; j < hs.length; j++) if (hs[j].getBoundingClientRect().top <= top) cur = j; var bs = aside.querySelectorAll('button'); for (var k = 0; k < bs.length; k++) bs[k].classList.toggle('on', k === cur); };
        if (m._otp) m.removeEventListener('scroll', m._otp); m._otp = tick; m.addEventListener('scroll', tick, { passive: true }); tick();
    }
    function homeHtml() {
        var nArt = 0; partDomains().concat(EXTRA).forEach(function (d) { nArt += (DOMS[d] || []).length; });
        var nPages = 0; Object.keys(MAN).forEach(function (g) { nPages += (MAN[g] && MAN[g].pageCount) || 0; });
        var h = '<div class="spb-enc-home">' + setCrumbs([{ t: 'Encyclopedia' }]) + '<div class="spb-enc-hero"><h1>The SPB Encyclopedia</h1><p>How Shokker Paint Booth works, from your first paint to the last bit of the spec map. ' + nArt + ' articles, ' + nPages.toLocaleString() + ' reference pages for every finish, pattern and control, ' + FIGL.length + ' diagrams.</p><p class="spb-enc-tip">Press <kbd>/</kbd> to search. Every highlighted word in the AI helper opens here too.</p></div>';
        var first = (DOMS.workflows || []).slice(0, 4).map(function (id) { return A[id]; }).filter(Boolean);
        if (first.length) h += '<h2>Start here</h2><div class="spb-enc-cards">' + first.map(function (a) { return '<button type="button" class="spb-enc-card" data-e="art" data-id="' + esc(a.id) + '"><b>' + esc(a.title) + '</b><span>' + esc(a.summary) + '</span></button>'; }).join('') + '</div>';
        h += extHtml(EXT.home, null);
        h += '<div class="spb-enc-dyk" aria-live="polite">' + dykHtml() + '</div>';
        if (FIG.g01_spec_channels) h += figHtml(FIG.g01_spec_channels, true);
        h += '<h2>Contents</h2><div class="spb-enc-parts">' + PARTS.concat(EXTRA.length ? [MORE] : []).map(function (p) { var n = 0; p.d.forEach(function (d) { n += (DOMS[d] || []).length; }); return '<button type="button" class="spb-enc-pcard" data-e="partpage" data-n="' + p.n + '"><i>' + p.ic + '</i><em>Part ' + p.n + '</em><b>' + esc(p.t) + '</b><small>' + n + ' articles' + ((p.g || []).length ? ' + reference' : '') + '</small></button>'; }).join('') + '</div>';
        return h + '</div>';
    }
    // "Did you know?": the articles' pro tips (v3 protips[], else their tips), one at a time, rotating every 9 s (paused on hover)
    function dykList() {
        var P = [], T = []; partDomains().concat(EXTRA).forEach(function (d) { (DOMS[d] || []).forEach(function (id) { var a = A[id]; if (!a) return;
            (a.protips || []).forEach(function (x) { var t = strip(x); if (t && !hidText(t)) P.push({ t: t, id: id, title: a.title }); });
            (a.tips || []).forEach(function (x) { var t = strip(x); if (t && t.length > 50 && t.length < 260 && !hidText(t)) T.push({ t: t, id: id, title: a.title }); }); }); });
        return P.length ? P : T;
    }
    function dykHtml() {
        var L = dykList(); if (!L.length) return ''; if (S.dyk == null) S.dyk = Math.floor(Math.random() * L.length); var x = L[S.dyk % L.length];
        return '<div class="spb-enc-dykh">💡 Did you know?</div><p>' + txt(x.t) + '</p><div class="spb-enc-dykf"><button type="button" class="spb-enc-chip" data-e="art" data-id="' + esc(x.id) + '">From: ' + esc(x.title) + ' ›</button><button type="button" class="spb-enc-chip" data-e="dyk">Next tip ›</button><small>' + ((S.dyk % L.length) + 1) + ' / ' + L.length + '</small></div>';
    }
    var _dykT = null;
    function dykTimer(on) {
        if (!on) { if (_dykT) { clearInterval(_dykT); _dykT = null; } return; } if (_dykT) return;
        _dykT = setInterval(function () { var b = root && root.querySelector('.spb-enc-dyk'); if (!S.open || !b) { clearInterval(_dykT); _dykT = null; return; } if (b.matches && b.matches(':hover')) return; S.dyk = (S.dyk || 0) + 1; b.innerHTML = dykHtml(); }, 9000);
    }
    function partByN(n) { return PARTS.concat([MORE]).filter(function (p) { return p.n === n; })[0] || null; }
    function partHtml(n) {
        var p = partByN(n); if (!p) return ''; var ids = []; p.d.forEach(function (d) { ids = ids.concat(DOMS[d] || []); });
        var h = '<div class="spb-enc-art">' + setCrumbs([{ t: 'Encyclopedia', v: { v: 'home' } }, { t: 'Part ' + p.n + ' · ' + p.t }]) + '<div class="spb-enc-kick">' + p.ic + ' Part ' + p.n + '</div><h1>' + esc(p.t) + '</h1><div class="spb-enc-list">';
        ids.forEach(function (id) { var a = A[id]; h += '<button type="button" class="spb-enc-row" data-e="art" data-id="' + esc(id) + '"><b>' + esc(a.title) + (a.quick ? ' <i class="spb-enc-star">★</i>' : '') + '</b><span>' + esc(a.summary) + '</span></button>'; });
        (p.g || []).forEach(function (g) { h += '<button type="button" class="spb-enc-row gen" data-e="gen" data-g="' + g + '"><b>' + esc(GEN[g].label) + ' ›</b><span>' + esc(genBlurb(g)) + '</span></button>'; });
        (p.x || []).forEach(function (x) { var V = EXT.views[x[0]]; if (V) h += '<button type="button" class="spb-enc-row gen" data-e="view" data-v="' + x[0] + '"><b>' + esc(x[1]) + ' ›</b><span>' + esc(V.blurb || '') + '</span></button>'; });
        return h + '</div></div>';
    }
    function genBlurb(g) { var m = MAN[g]; if (g === 'glossary') return terms().length + ' words and phrases, each with a short card.'; if (g === 'figures') return FIGL.length + ' diagrams with captions.'; return m ? (m.pageCount || 0).toLocaleString() + ' pages in ' + groupsOf(g).length + ' groups.' : ''; }
    function groupsOf(g) { var by = {}, L = []; ((MAN[g] || {}).parts || []).forEach(function (p) { var k = p.group || p.domain; if (!by[k]) { by[k] = { name: k, parts: [], count: 0 }; L.push(by[k]); } by[k].parts.push(p); by[k].count += p.count || 0; }); return L; }
    function genHtml(g, grp) {
        var G = GEN[g], p = PARTS.filter(function (x) { return (x.g || []).indexOf(g) !== -1; })[0];
        var cr = [{ t: 'Encyclopedia', v: { v: 'home' } }, { t: 'Part ' + p.n + ' · ' + p.t, v: { v: 'part', n: p.n } }, grp ? { t: G.label, v: { v: 'gen', g: g } } : { t: G.label }]; if (grp) cr.push({ t: grp });
        var h = '<div class="spb-enc-art">' + setCrumbs(cr) + '<h1>' + esc(grp || G.label) + '</h1>';
        if (g === 'glossary') { var T = terms().sort(function (a, b) { return String(a.title).localeCompare(String(b.title)); }); h += '<p class="spb-enc-lead">' + esc(genBlurb(g)) + '</p><div class="spb-enc-chips">' + T.map(function (t) { return '<button type="button" class="spb-enc-chip" data-e="art" data-id="' + esc(t.id) + '" title="' + esc(t.summary || '') + '">' + esc(t.title) + '</button>'; }).join('') + '</div>'; return h + '</div>'; }
        if (g === 'figures') { h += '<div class="spb-enc-figs">' + FIGL.map(function (f) { return figHtml(f, false); }).join('') + '</div>'; return h + '</div>'; }
        if (!grp) { h += '<p class="spb-enc-lead">' + esc(genBlurb(g)) + '</p><div class="spb-enc-chips">' + groupsOf(g).map(function (x) { return '<button type="button" class="spb-enc-chip" data-e="gen" data-g="' + g + '" data-grp="' + esc(x.name) + '">' + esc(x.name) + ' <small>' + x.count + '</small></button>'; }).join('') + '</div>'; return h + '</div>'; }
        return h + '<div class="spb-enc-gfill"><div class="spb-enc-meta">Loading ' + esc(grp) + '…</div></div></div>';
    }
    function genFill(v) {
        if (!v.grp) return; var grp = groupsOf(v.g).filter(function (x) { return x.name === v.grp; })[0]; if (!grp) return;
        Promise.all(grp.parts.map(function (p) { return loadDomain(p.domain); })).then(function (lists) {
            if (S.view !== v) return; var ids = [].concat.apply([], lists), kind = GEN[v.g].kind, box = root.querySelector('.spb-enc-gfill'); if (!box) return;
            if (kind === 'control' || kind === 'help') { box.innerHTML = '<div class="spb-enc-list">' + ids.map(function (id) { var a = A[id]; return '<button type="button" class="spb-enc-row" data-e="art" data-id="' + esc(id) + '"><b>' + esc(a.title) + '</b><span>' + esc(a.summary) + '</span></button>'; }).join('') + '</div>'; return; }
            box.innerHTML = '<div class="spb-enc-grid">' + ids.map(function (id) { var a = A[id], la = lookAction(a); return '<button type="button" class="spb-enc-tile" data-e="art" data-id="' + esc(id) + '" title="' + esc(a.summary) + '">' + (la ? '<img loading="lazy" alt="" src="' + esc(thumbUrl(la.do, la.id, 160)) + '" onerror="this.style.visibility=\'hidden\'">' : '') + '<span>' + esc(a.title) + '</span></button>'; }).join('') + '</div>';
        });
    }
    function figHtml(f, wide) { if (!f) return ''; return '<figure class="spb-enc-fig' + (wide ? ' wide' : '') + '"><button type="button" data-e="fig" data-f="' + esc(f.id) + '" title="Enlarge"><img loading="lazy" src="' + esc(BASE + f.file) + '" alt="' + esc(f.alt || f.title || '') + '"></button><figcaption><b>' + esc(f.title || '') + '</b> ' + esc(f.caption || '') + '</figcaption></figure>'; }
    function shotHtml(x, cls, cap) { if (!x) return ''; return '<figure class="spb-enc-fig shot' + (cls ? ' ' + cls : '') + '"><button type="button" data-e="fig" data-f="s:' + esc(x.id) + '" title="Click to zoom"><img loading="lazy" src="' + esc(scrSrc(x)) + '" alt="' + esc(x.alt || x.title || '') + '" onerror="this.closest(\'figure\').style.display=\'none\'"></button><figcaption>' + (cap || '') + '<b>' + esc(x.title || '') + '</b> ' + esc(x.caption || '') + (cls === 'small' || !(x.callouts || []).length ? '' : '<ol class="spb-enc-callouts">' + x.callouts.map(function (c) { return '<li><i>' + esc(c.n) + '</i>' + esc(c.label) + '</li>'; }).join('') + '</ol>') + '</figcaption></figure>'; }
    function drawLb() { var lb = root && root.querySelector('.spb-enc-lb'); if (!lb) return; var sc = S.fig && /^s:/.test(S.fig) ? SCR[S.fig.slice(2)] : null, f = sc || (S.fig && FIG[S.fig]); lb.hidden = !f; lb.innerHTML = f ? '<div class="spb-enc-lbin"><img src="' + esc(sc ? scrSrc(sc) : BASE + f.file) + '" alt="' + esc(f.alt || '') + '"><p><b>' + esc(f.title || '') + '</b> ' + esc(f.caption || '') + '</p><button type="button" class="spb-enc-nb" data-e="lbclose">×</button></div>' : ''; }
    // inline text: paragraphs, **bold**, on-screen LABELS in caps get the UI style
    function txt(s) { return esc(String(s || '')).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\b([A-Z][A-Z0-9&+\/-]*(?: [A-Z][A-Z0-9&+\/-]*)*)\b/g, function (m0) { return m0.replace(/[^A-Z]/g, '').length >= 4 && /[A-Z]{3}/.test(m0) ? (m0.split(' ').every(function (w) { return EMPH.test(w); }) ? '<b>' + m0 + '</b>' : '<span class="spb-enc-ui">' + m0 + '</span>') : m0; }); }
    // ENC_READER_FIX 2026-10-05: capitals used for emphasis ('YOUR car', 'the SAME colour') are bold text, not a UI-control chip
    var EMPH = /^(YOUR|SAME|ONLY|NOT|NEVER|ALWAYS|MUST|EVERY|EACH|ALL|BOTH|THIS|THAT|THESE|THOSE|THEN|BEFORE|AFTER|WHOLE|EXACT|EXACTLY|DONT|WILL|WONT|CANT|CAN|NEW|ONE|TWO|FIRST|LAST|MORE|LESS|VERY|REAL|OWN|ANY|AND|THE|WITH|WITHOUT|FROM|INTO|OVER|UNDER|ABOVE|BELOW|INSIDE|OUTSIDE|STILL|ALSO|JUST|LIKE|WHEN|WHERE|WHAT|WHY|HOW|DOES|HAVE|MAKE|KEEP|STAY|STAYS|ZERO|NONE|NOTHING|EVERYTHING|SAME-|OTHER|BEST|WORST|FAST|SLOW|BIG|SMALL|HUGE|TINY|LOOK|SEE|STOP|WAIT|NOTE|TIP|WARNING|IMPORTANT)$/;
    // FINAL 3: an inline "1. ... 2. ... 3. ..." run inside one paragraph reads as a wall of text; render it as a real numbered list (needs 3+ in sequence).
    function listify(p) {
        if (/\n/.test(p)) return null;
        var s = ' ' + p, pos = [], k = 1, from = 0, re, mm;
        for (;;) { re = new RegExp('\\s' + k + '[.)]\\s+(?=[A-Z(\u201c"])', 'g'); re.lastIndex = from; mm = re.exec(s); if (!mm) break; pos.push([mm.index, mm[0].length]); from = mm.index + mm[0].length; k++; }
        if (pos.length < 3) return null;
        var head = s.slice(0, pos[0][0]).trim();
        return (head ? '<p>' + txt(head) + '</p>' : '') + '<ol class="spb-enc-il">' + pos.map(function (q, i) { return '<li>' + txt(s.slice(q[0] + q[1], i + 1 < pos.length ? pos[i + 1][0] : s.length).trim()) + '</li>'; }).join('') + '</ol>';
    }
    function paras(s) { return String(s || '').split(/\n{2,}/).filter(function (x) { return x.trim(); }).map(function (p) { return listify(p) || '<p>' + txt(p).replace(/\n/g, '<br>') + '</p>'; }).join(''); }
    function strip(s) { return String(typeof s === 'string' ? s : (s && (s.text || s.label)) || '').replace(/^\s*\d+[.)]\s+/, ''); }
    function relTitle(id) { var a = A[id]; if (a) return a.title; var E = Enc(), t = E && E.term ? E.term(id) : null; if (t) return t.title; var last = String(id).split('.').slice(1).join(' ') || id; return last.replace(/[_-]+/g, ' ').replace(/^\w/, function (c) { return c.toUpperCase(); }); }
    function artHtml(a) {
        a = clean(a);
        var p = a._cat ? null : partOf(a._gloss ? 'zz' : a.id), g = genOf(a.domain || String(a.id).split('.')[0]), cr = [{ t: 'Encyclopedia', v: { v: 'home' } }];
        if (a._gloss) cr.push({ t: 'Part XVI · Reference', v: { v: 'part', n: 'XVI' } }, { t: 'Glossary', v: { v: 'gen', g: 'glossary' } });
        else if (a._cat) cr.push({ t: a.domain === 'pattern' ? 'Patterns' : (a.domain === 'spec' ? 'Spec patterns' : 'Finishes') });
        else if (p) { cr.push({ t: 'Part ' + p.n + ' · ' + p.t, v: { v: 'part', n: p.n } }); if (g && PFILE[a.domain]) cr.push({ t: GEN[g].label, v: { v: 'gen', g: g } }, { t: PFILE[a.domain].group, v: { v: 'gen', g: g, grp: PFILE[a.domain].group } }); }
        cr.push({ t: a.title });
        var la = lookAction(a), h = '<article class="spb-enc-art">' + setCrumbs(cr) + '<div class="spb-enc-kick">' + (a._gloss ? '📇 Glossary' : (p ? p.ic + ' Part ' + p.n + ' · ' + esc(p.t) : '')) + (a.quick ? ' <span class="spb-enc-star" title="Also a quick card in the AI helper">★ quick card</span>' : '') + (LVL[a.level] ? ' <span class="spb-enc-lvl l-' + esc(a.level) + '" title="' + LVL[a.level][1] + '">' + LVL[a.level][0] + '</span>' : '') + '</div><h1>' + esc(a.title) + '</h1>';
        S.curC = a;
        if (la) h += '<div class="spb-enc-hero2"><img alt="" src="' + esc(thumbUrl(la.do, la.id, 320)) + '" onerror="this.parentNode.style.display=\'none\'"><div><p class="spb-enc-lead">' + txt(a.summary) + '</p>' + doItHtml(a, true) + '</div></div>';
        else h += '<p class="spb-enc-lead">' + txt(a.summary) + '</p>';
        h += extHtml(EXT.artTop, a);
        // ENC_READER_FIX 2026-10-05: only THIS look's own car render. A shelf hero beside another finish misled buyers (a tie-dye car on a chrome
        // page); the swatch above already shows the look itself.
        var car = carShot(a); if (car && !car.exact) car = null; if (car) h += shotHtml(car.s, 'car', '');
        if (S.note) h += '<div class="spb-enc-note">' + S.note + '</div>';
        if (a.what) h += '<section><h2>What it is</h2>' + paras(a.what) + '</section>';
        // real screenshots first (large); a diagram stays unless a screenshot says it replaces it
        var shots = screensOf(a).filter(function (x) { return !car || x.id !== car.s.id; }), gone = {}; shots.forEach(function (x) { gone[x.id] = 1; [].concat(x.replaces || []).forEach(function (r) { gone[r] = 1; }); });
        shots.forEach(function (x) { h += shotHtml(x, '', ''); });
        (a.figures || []).forEach(function (fid) { if (!gone[fid]) h += figHtml(FIG[fid], false); });
        if ((a.when || []).length) h += '<section><h2>When you need it</h2><ul>' + a.when.map(function (x) { return '<li>' + txt(strip(x)) + '</li>'; }).join('') + '</ul></section>';
        if ((a.how || []).length) h += '<section><h2>How to do it</h2><ol class="spb-enc-how">' + a.how.map(function (x) { return '<li>' + txt(strip(x)) + '</li>'; }).join('') + '</ol></section>';
        if ((a.deep || []).length) h += '<section class="spb-enc-deep"><h2>How it really works</h2>' + a.deep.map(function (d) { return (d.heading && !(a.deep.length === 1 && /^how it really works$/i.test(d.heading)) ?'<h3>' + esc(d.heading) + '</h3>' : '') + paras(d.body); }).join('') + '</section>';
        if ((a.controls || []).length) h += '<section><h2>Controls</h2><div class="spb-enc-tw"><table class="spb-enc-ctl"><thead><tr><th>Control</th><th>Range</th><th>Default</th><th>What it does</th></tr></thead><tbody>' + a.controls.map(function (c) { return '<tr><td><span class="spb-enc-ui">' + esc(c.label) + '</span></td><td>' + esc(c.range || '–') + '</td><td>' + esc(c.default != null && c.default !== '' ? c.default : '–') + '</td><td>' + txt(c.effect || '') + '</td></tr>'; }).join('') + '</tbody></table></div></section>';
        if ((a.examples || []).length) h += '<section><h2>Worked examples</h2><div class="spb-enc-exs">' + a.examples.map(function (x, k) { return exHtml(x, k); }).join('') + '</div></section>';
        if ((a.combos || []).length) h += '<section><h2>Works with</h2><div class="spb-enc-combos">' + a.combos.map(function (x) { var t = comboTarget(x.with); return '<div class="spb-enc-combo"><button type="button" class="spb-enc-chip rel" data-e="art" data-id="' + esc(t.id) + '">' + (t.thumb ? '<img loading="lazy" alt="" src="' + esc(t.thumb) + '" onerror="this.remove()">' : '') + esc(t.title) + '</button><span>' + txt(x.why || '') + '</span></div>'; }).join('') + '</div></section>';
        (a.protips || []).forEach(function (x) { h += '<aside class="spb-enc-pro"><b>⚡ Pro tip</b><p>' + txt(strip(x)) + '</p></aside>'; });
        if ((a.tips || []).length) h += '<section class="spb-enc-call tips"><h2>Tips</h2><ul>' + a.tips.map(function (x) { return '<li>' + txt(strip(x)) + '</li>'; }).join('') + '</ul></section>';
        if ((a.pitfalls || []).length) h += '<section class="spb-enc-call warn"><h2>Watch out</h2><ul>' + a.pitfalls.map(function (x) { return '<li>' + txt(strip(x)) + '</li>'; }).join('') + '</ul></section>';
        if ((a.mistakes || []).length) h += '<section><h2>Common mistakes</h2><div class="spb-enc-mis">' + a.mistakes.map(function (x) { return '<div class="spb-enc-misr"><div><i>You see</i>' + txt(x.symptom) + '</div><div><i>Why</i>' + txt(x.cause) + '</div><div><i>Fix</i>' + txt(x.fix) + '</div></div>'; }).join('') + '</div></section>';
        if ((a.faq || []).length) h += '<section><h2>Questions people ask</h2><div class="spb-enc-faq">' + a.faq.map(function (x, k) { return '<details' + (k === 0 ? ' open' : '') + '><summary>' + txt(x.q) + '</summary>' + paras(x.a) + '</details>'; }).join('') + '</div></section>';
        if (!la) { var di = doItHtml(a, false); if (di) h += '<section><h2>Do it</h2>' + di + '</section>'; }
        if ((a.links || []).length && a._gloss) h += '<section><h2>More help</h2><div class="spb-enc-chips">' + a.links.slice(0, 6).map(function (l, k) { return '<button type="button" class="spb-enc-chip" data-e="tlink" data-k="' + k + '">' + esc(l.label) + ' ›</button>'; }).join('') + '</div>' + (S.linkOut ? '<div class="spb-enc-note">' + S.linkOut + '</div>' : '') + '</section>';
        var rel = (a.related || []).filter(Boolean);
        if (rel.length) h += '<section><h2>Related</h2><div class="spb-enc-chips">' + rel.slice(0, 16).map(function (r) { return '<button type="button" class="spb-enc-chip rel" data-e="art" data-id="' + esc(r) + '">' + esc(relTitle(r)) + '</button>'; }).join('') + '</div></section>';
        h += extHtml(EXT.artEnd, a);
        h += '<div class="spb-enc-foot" data-art="' + esc(a.id) + '">' + (a.updated ? 'Updated ' + esc(a.updated) + ' · ' : '') + (devIds() ? 'id ' + esc(a.id) + ' · ' : '') + '<button type="button" class="spb-enc-print" data-e="print" title="Print this article (only the article is printed)">🖨 Print</button></div>';
        return h + '</article>';
    }
    var LVL = { beginner: ['Beginner', 'No experience needed'], intermediate: ['Intermediate', 'You know zones and finishes'], pro: ['Pro', 'Deep spec-map and engine detail'] };
    // a worked example: the exact settings, the result, and (when a value names a real finish / pattern) a button that starts it on the car
    var _byName = null;
    function lookByName(label, v) {
        v = String(v == null ? '' : v); var m = /^(base|monolithic)::\S+$/.exec(v) ? { do: 'finish', id: v } : (/^(pattern|spec)::(\S+)$/.exec(v) ? { do: v.split('::')[0], id: v.split('::')[1] } : null);
        if (m) { var c0 = catItem(m.do, m.id); return { do: m.do, id: c0 ? c0.key : m.id, label: c0 ? c0.name : m.id }; }
        if (!_byName) { _byName = {}; cat().forEach(function (c) { var k = c.kind + '|' + norm(c.name); if (!_byName[k]) _byName[k] = c; }); }
        var n = norm(v), lk = norm(label), order = /pattern/.test(lk) && !/spec/.test(lk) ? ['pattern', 'finish', 'spec'] : (/spec|shine overlay/.test(lk) ? ['spec', 'finish', 'pattern'] : ['finish', 'pattern', 'spec']);
        for (var i = 0; i < order.length; i++) { var c = _byName[order[i] + '|' + n]; if (c) return { do: c.kind, id: c.key, label: c.name }; }
        return null;
    }
    function exLook(x) { var st = x.settings || {}; for (var k in st) { var l = lookByName(k, st[k]); if (l) return l; } return null; }
    function exHtml(x, k) {
        var st = x.settings || {}, rows = Object.keys(st).map(function (l) { return '<tr><td><span class="spb-enc-ui">' + esc(l) + '</span></td><td>' + esc(st[l]) + '</td></tr>'; }).join(''), lk = exLook(x), sc = x.screen && SCR[x.screen];
        return '<div class="spb-enc-ex"><div class="spb-enc-exn">Example ' + (k + 1) + '</div><h3>' + esc(x.title || '') + '</h3>' + (x.goal ? '<p class="spb-enc-exg">Goal: ' + txt(x.goal) + '</p>' : '') +
            (rows ? '<table class="spb-enc-ctl ex"><tbody>' + rows + '</tbody></table>' : '') + (x.result ? '<p class="spb-enc-exr"><b>You get:</b> ' + txt(x.result) + '</p>' : '') + (sc ? shotHtml(sc, 'small', '') : '') +
            '<div class="spb-enc-acts">' + (lk ? '<button type="button" class="spb-enc-do hot" data-e="exdo" data-k="' + k + '">▶ Start this on my car (' + esc(lk.label) + ')</button>' : '') + (rows ? '<button type="button" class="spb-enc-do" data-e="excopy" data-k="' + k + '">⧉ Copy settings</button>' : '') + '</div></div>';
    }
    function comboTarget(w) {
        w = String(w || ''); var m = /^(base|monolithic)::/.test(w) ? ['finish', w] : (/^(pattern|spec)::/.test(w) ? [w.split('::')[0], w.split('::')[1]] : null);
        if (m) { var c = catItem(m[0], m[1]); return { id: 'cat:' + m[0] + ':' + (c ? c.key : m[1]), title: c ? c.name : m[1].replace(/^.*::/, '').replace(/_/g, ' '), thumb: thumbUrl(m[0], c ? c.key : m[1], 64) }; }
        return { id: w, title: relTitle(w), thumb: '' };
    }
    function actLabel(x) { if (x.label) return x.label; if (/^(finish|pattern|spec)$/.test(x.do)) { var c = catItem(x.do, x.id); return c ? c.name : humanId(String(x.id).replace(/^.*::/, '')); } return humanId(x.id); }
    // ENC_READER_FIX 2026-10-05: a buyer never sees an internal id ('btnRender', 'rpTabLayers'); ids stay in data-* attributes, and
    // localStorage spbEncDev=1 shows them for developers
    function humanId(id) {
        var s = String(id || '').replace(/^.*::/, '').replace(/^(btn|rp|tab|sel|inp|chk|cb|dd|pnl|panel|opt|lbl|txt|ui)(?=[A-Z_])/, '').replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/[._-]+/g, ' ').replace(/\s+/g, ' ').trim();
        s = s.replace(/\b(Tab|Btn|Rp)\b/g, '').replace(/\s+/g, ' ').trim(); return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : 'this control';
    }
    function devIds() { try { return W.localStorage && W.localStorage.getItem('spbEncDev') === '1'; } catch (e) { return false; } }
    function doItHtml(a, compact) {
        var acts = actsOf(a); if (!acts.length) return '';
        var looks = acts.filter(function (x) { return /^(finish|pattern|spec)$/.test(x.do); }), rest = acts.filter(function (x) { return !/^(finish|pattern|spec)$/.test(x.do); }), h = '';
        if (looks.length) h += (compact ? '' : '<div class="spb-enc-grid">') + looks.slice(0, 12).map(function (x) { var k = acts.indexOf(x); return compact ? '<button type="button" class="spb-enc-do hot" data-e="do" data-k="' + k + '">▶ Try ' + esc(actLabel(x)) + ' on my car</button>' : '<button type="button" class="spb-enc-tile do" data-e="do" data-k="' + k + '"><img loading="lazy" alt="" src="' + esc(thumbUrl(x.do, x.id, 160)) + '" onerror="this.style.visibility=\'hidden\'"><span>▶ ' + esc(actLabel(x)) + '</span></button>'; }).join('') + (compact ? '' : '</div>');
        if (rest.length) h += '<div class="spb-enc-acts">' + rest.map(function (x) { var k = acts.indexOf(x); return '<button type="button" class="spb-enc-do' + (x.do === 'flow' ? ' hot' : '') + '" data-e="do" data-k="' + k + '">' + (x.do === 'control' ? '👁 Show me in the app: ' + esc(controlLabel(a, x)) : '▶ Start: ' + esc(actLabel(x))) + '</button>'; }).join('') + '</div>';
        return h;
    }
    function controlLabel(a, x) { var c = (a.controls || []).filter(function (c) { return c.inv === x.id; })[0]; return c ? c.label : (x.label || (a.controls && a.controls.length === 1 ? a.controls[0].label : actLabel(x))); }
    // ---- "Do it": looks + flows go to the step builder, controls are pointed at in the real UI
    function runAction(a, x) {
        if (!x) return;
        if (x.do === 'control') { var lab = controlLabel(a, x); if (showControl(x.id, lab)) { close(); return; } var inStudio = false; try { inStudio = D.body.classList.contains('spb-chat-studio'); } catch (eC) {} S.note = inStudio ? 'The <b>' + esc(lab) + '</b> control lives in the full editor, which is hidden behind this chat window. Press <b>Full editor →</b> at the top, then press this button again. ' : 'I could not point at <b>' + esc(lab) + '</b> right now (its panel is closed). ' + (a.how && a.how[0] ? 'Where it is: ' + txt(strip(a.how[0])) : ''); drawMain(); return; }
        // ENC_READER_FIX 2026-10-05: a Do-it applies what the PAGE says. When the page pairs the look with a colour (stealth: Flat Black
        // + BASE COLOR #0a0a0c) the builder gets the helper's own two-step shape ('body>recolour', 'step1>finish'), the named look is
        // pre-selected in the grid, the step says what will change, and a 'Back to the article' pill re-opens the reader where it was.
        var B = W.SpbOfflineBuilder, act = { do: x.do, id: x.id, label: actLabel(x) }, hex = x.do === 'finish' ? lookColour(a, x) : null;
        close(); backPill(a);
        if (B && B.takeAction) {
            var two = !!(hex && B.newStep && B.pickChoice && B.showSteps && B.offlineMode && B.offlineMode());
            if (two) { try { if (W.spbProAI && W.spbProAI.open) W.spbProAI.open(); } catch (e0) {} var s1 = B.newStep({ what: { k: 'body' } }); B.pickChoice(s1, { kind: 'colour', hex: hex, name: hexName(hex), label: hexName(hex), exact: true }); s1.prefilled = true; s1.note = 'From the encyclopedia: the colour “' + a.title + '” uses.'; B.showSteps([s1], ''); }
            if (B.takeAction(act)) {
                try { var S0 = B.state(), ls = S0.steps[S0.steps.length - 1]; if (ls && x.do !== 'flow') { ls.search = act.label; ls.note = 'From the encyclopedia: ' + act.label + (two ? ' on ' + hexName(hex) + ' (step 1)' : '') + '. Press Run to put it on the car; Undo takes it back.'; if (B.draw) B.draw(); } } catch (e1) {}
                return;
            }
        }
        try { if (W.spbProAI && W.spbProAI.open) W.spbProAI.open(); var inp = D.querySelector('#spbProAI .spb-pai-input'); if (inp) { inp.value = x.do === 'flow' ? actLabel(x) : 'Use ' + act.label + (hex ? ' in ' + hex : '') + ' on the car'; inp.focus(); } } catch (e) {}
    }
    // the colour a page pairs with a look: a #hex in the same step / example setting as the look's name (within ~160 characters)
    function lookColour(a, x) {
        var nm = String(actLabel(x) || '').toLowerCase(); if (nm.length < 3) return null;
        var src = (a.how || []).map(strip).concat((a.examples || []).map(function (e) { var st = (e && e.settings) || {}; return Object.keys(st).map(function (k) { return k + ': ' + st[k]; }).join(' · '); }));
        for (var i = 0; i < src.length; i++) {
            var s = String(src[i] || ''), lo = s.toLowerCase(), p = lo.indexOf(nm); if (p < 0) continue;
            var re = /#([0-9a-f]{6})\b/gi, m, best = null; while ((m = re.exec(s))) { var d = Math.abs(m.index - p); if (d < 160 && (!best || d < best.d)) best = { d: d, h: '#' + m[1].toLowerCase() }; }
            if (best) return best.h;
        }
        return null;
    }
    function hexName(h) { var n = parseInt(String(h).slice(1), 16), r = n >> 16 & 255, g = n >> 8 & 255, b = n & 255, l = (Math.max(r, g, b) + Math.min(r, g, b)) / 510; return l < 0.08 ? 'near-black ' + h : (l > 0.94 ? 'near-white ' + h : h); }
    // after a Do-it closes the reader: one small pill brings the buyer back to the same article
    function backPill(a) {
        try {
            var old = D.getElementById('spbEncBack'); if (old) old.remove(); if (!a || !a.id) return;
            var b = D.createElement('button'); b.type = 'button'; b.id = 'spbEncBack'; b.className = 'spb-enc-back'; b.setAttribute('data-id', a.id);
            b.innerHTML = '📖 Back to the article: <b>' + esc(a.title) + '</b><i title="Hide">×</i>';
            b.addEventListener('click', function (ev) { b.remove(); if (ev.target && ev.target.tagName === 'I') return; open(a.id); });
            D.body.appendChild(b); setTimeout(function () { try { b.remove(); } catch (e) {} }, 180000);
        } catch (e) {}
    }
    function visible(e) { if (!e || !e.getBoundingClientRect) return false; var r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !(root && root.contains(e)); }
    function showControl(id, label) {
        var c = [], k = norm(String(label || '').replace(/\b(dropdown|slider|button|toggle|switch|checkbox|input|box)\b/gi, ''));
        try { c.push(D.getElementById(id)); c.push(D.querySelector('[data-testid="' + String(id).replace(/"/g, '') + '"]')); } catch (e) {}
        if (k) { var L = D.querySelectorAll('button,label,summary,h3,h4,h5,.section-title,[aria-label],[title]'); for (var i = 0; i < L.length && c.filter(Boolean).length < 6; i++) { var e2 = L[i], t = norm(e2.getAttribute('aria-label') || '') , tx = norm((e2.textContent || '').slice(0, 80)), ti = norm(e2.getAttribute('title') || ''); if (tx === k || t === k || (ti && ti.indexOf(k) === 0 && k.length > 4)) c.push(e2); } }
        var hit = c.filter(visible)[0]; if (!hit) return false;
        try { hit.scrollIntoView({ block: 'center', behavior: 'smooth' }); hit.classList.add('spb-ob-flash'); setTimeout(function () { hit.classList.remove('spb-ob-flash'); }, 3200); } catch (e) {}
        return true;
    }
    // ---- events
    function onClick(ev) {
        var b = ev.target && ev.target.closest ? ev.target.closest('[data-e]') : null; if (!b) { if (ev.target && ev.target.classList && ev.target.classList.contains('spb-enc-lb')) { S.fig = null; drawLb(); } return; }
        var e = b.getAttribute('data-e');
        if (e === 'close') close();
        else if (e === 'home') go({ v: 'home' });
        else if (e === 'back') nav(-1);
        else if (e === 'fwd') nav(1);
        else if (e === 'tab') { S.tab = b.getAttribute('data-t'); if (S.q) { S.q = ''; root.querySelector('.spb-enc-q').value = ''; } drawNav(); }
        else if (e === 'part') { var n = b.getAttribute('data-n'); S.exp[n] = !S.exp[n]; saveExp(); drawNav(); try { var ph = root.querySelector('.spb-enc-ph[data-n="' + n + '"]'); if (ph && S.exp[n]) ph.scrollIntoView({ block: 'start', behavior: 'smooth' }); } catch (eS) {} }          // ENC_READER_FIX: an opened Part lands in view
        else if (e === 'partpage') { S.exp[b.getAttribute('data-n')] = true; saveExp(); go({ v: 'part', n: b.getAttribute('data-n') }); }
        else if (e === 'art') go({ v: 'art', id: b.getAttribute('data-id') });
        else if (e === 'gen') go({ v: 'gen', g: b.getAttribute('data-g'), grp: b.getAttribute('data-grp') || undefined });
        else if (e === 'crumb') { var c = _crumbs[Number(b.getAttribute('data-k'))]; if (c && c.v) go(c.v); }
        else if (e === 'letter') { var g = root.querySelector('.spb-enc-azg[data-letter="' + b.getAttribute('data-c') + '"]'); if (g) g.scrollIntoView({ block: 'start' }); }
        else if (e === 'fig') { S.fig = b.getAttribute('data-f'); drawLb(); }
        else if (e === 'lbclose') { S.fig = null; drawLb(); }
        else if (e === 'view') { var vv = { v: b.getAttribute('data-v') }; ['p', 'a', 'b', 'm', 'r', 'c'].forEach(function (k) { var x = b.getAttribute('data-' + k); if (x != null) vv[k] = /^(m|r|c)$/.test(k) ? Number(x) : x; }); if (b.getAttribute('data-i') != null) vv.i = Number(b.getAttribute('data-i')); go(vv); }
        else if (e === 'print') { try { W.print(); } catch (er) {} }
        else if (e === 'otp') { var hh = root.querySelector('#encs' + b.getAttribute('data-k')); if (hh) hh.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
        else if (EXT.clicks[e]) { try { EXT.clicks[e](b, ev); } catch (er) {} }
        else if (e === 'dyk') { S.dyk = (S.dyk || 0) + 1; var db = root.querySelector('.spb-enc-dyk'); if (db) db.innerHTML = dykHtml(); }
        else if (e === 'exdo') { var ex = S.curC && (S.curC.examples || [])[Number(b.getAttribute('data-k'))], lk = ex && exLook(ex); if (lk) runAction(S.cur, lk); }
        else if (e === 'excopy') { var ex2 = S.curC && (S.curC.examples || [])[Number(b.getAttribute('data-k'))]; if (ex2) { var st = ex2.settings || {}, tx = (ex2.title || '') + '\n' + Object.keys(st).map(function (l) { return l + ': ' + st[l]; }).join('\n'); try { (navigator.clipboard && navigator.clipboard.writeText ? navigator.clipboard.writeText(tx) : Promise.reject()).then(function () { b.textContent = '✓ Copied'; }, function () { b.textContent = tx; }); } catch (er) { b.textContent = tx; } } }
        else if (e === 'do') { var a = S.cur; if (a) runAction(a, actsOf(a)[Number(b.getAttribute('data-k'))]); }
        else if (e === 'tlink') { var a2 = S.cur, l = a2 && (a2.links || [])[Number(b.getAttribute('data-k'))]; var B = W.SpbOfflineBuilder; S.linkOut = l && B && B.linkOut ? (B.linkOut(l) || '') : ''; drawMain(); }
    }
    // deep link from the address bar: #enc:<id>
    function fromHash() { var m = /^#enc:(.+)$/.exec(String(W.location && W.location.hash || '')); if (m) open(decodeURIComponent(m[1])); }
    try { W.addEventListener('hashchange', fromHash); if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', fromHash); else setTimeout(fromHash, 0); } catch (e) {}
    W.SpbEncyclopedia = { _x: { EXT: EXT, S: S, A: A, SCR: SCR, PFILE: PFILE, esc: esc, txt: txt, paras: paras, norm: norm, setCrumbs: setCrumbs, go: go, show: show, get: get, boot: boot, getJSON: getJSON, thumbUrl: thumbUrl, scrSrc: scrSrc, shotHtml: shotHtml,
        artHtml: artHtml, actsOf: actsOf, runAction: runAction, catItem: catItem, cat: cat, pageForKey: pageForKey, loadDomain: loadDomain, hidText: hidText, hidId: hidId, carShot: carShot, lookAction: lookAction, drawMain: drawMain, drawNav: drawNav, root: function () { return root; }, miniToc: miniToc, resetSearch: function () { CORPUS = null; } },
        hiddenId: function (id) { return hidId(id); }, hiddenText: hidText, addScreens: addScreens, screens: function () { return SCRL.slice(); }, open: open, close: close, get: get, search: search, pageForKey: pageForKey, boot: boot, thumbUrl: thumbUrl, showControl: showControl, isOpen: function () { return S.open; }, state: function () { return S; }, PARTS: PARTS };
})();
