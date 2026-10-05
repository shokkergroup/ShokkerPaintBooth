// OFFLINE_BUILDER 2026-10-04 owner: offline = guided builder + encyclopedia.
// Owner: the offline helper (no AI model) must stop pretending to be a human chat: "way too many variables people can just type in; that part is for online mode
// (DeepSeek via OpenRouter) or MCP through Claude/OpenAI". Offline becomes:
//   1. a GUIDED BUILDER inside the copilot panel: steps of WHAT (a colour found on the car with its %, a named part, a layer, numbers / sponsors, the whole car,
//      a box drawn on the paint, or "the result of step N" = the same pixels) -> DO WHAT (recolour / add finish / add pattern or texture / change shine only)
//      -> WHICH LOOK (real catalogue choices with thumbnails). Run / Undo. Every click has one exact meaning.
//   2. TYPING PRE-FILLS THE BUILDER: the offline parser (SpbProEdit.plan) turns a typed sentence into steps ("I read this as: (1) Yellow -> Pink (2) Holographic +
//      snakeskin shine on (1)"); what it could not understand becomes an OPEN step with choices, never "Nothing was changed".
//   3. ENCYCLOPEDIA FLAGGING: every known word / phrase in the typed text is highlighted (window.SPB_ENCYCLOPEDIA, leftmost-longest); a click opens its card:
//      info (summary + links), action (catalogue choices -> a builder step), flow (starts the matching step).
//   4. "Ask DeepSeek instead" sends the same text to the existing online path (unchanged; online + MCP stay free chat).
// Run goes through the copilot's own offline edit path (window.__spbOB bridge registered by js/spb-pro-ai.js next to offlineEditAsk), so every change keeps
// the copilot's exact before-state Undo (docs/handoff_reports/UNDO_FIX.md). Text sent through spbProAI.send (chips, harnesses) is NOT intercepted.
// The pure logic (flag / fromPlan / toPlan / readAs) runs in node (no DOM): _easy_claude_work/builder_test.js.
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : this;
    var CIRC = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩'];
    function Ed() { return W.SpbProEdit || null; }
    function ENC() { return W.SPB_ENCYCLOPEDIA || null; }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function cap(s) { s = String(s || ''); return s.charAt(0).toUpperCase() + s.slice(1); }
    function clone(o) { return o == null ? o : JSON.parse(JSON.stringify(o)); }
    function hex6(h) { h = String(h || '').replace('#', '').toLowerCase(); return /^[0-9a-f]{6}$/.test(h) ? h : '888888'; }
    function num(i) { return CIRC[i] || ('(' + (i + 1) + ')'); }

    // ------------------------------------------------------------------ ENCYCLOPEDIA: flagging (the documented matcher: normalise, leftmost-longest)
    var _byId = null, _weak = null, _allChoices = null;
    function termById(id) {
        var D = ENC(); if (!D) return null;
        if (!_byId) { _byId = {}; (D.terms || []).forEach(function (t) { _byId[t.id] = t; }); }
        if (!_byId[id] && /^compound:|\./.test(String(id || ''))) { var vt = v2Term(id); if (vt) _byId[id] = vt; }          // HELPER_V2: v2 article ids + compounds
        return _byId[id] || null;
    }
    function weakSet() { if (!_weak) { _weak = {}; ((ENC() || {}).weak || []).forEach(function (a) { _weak[a] = 1; }); } return _weak; }
    // words with their ORIGINAL character offsets (lowercase; ' and the curly apostrophe deleted; every other run outside a-z 0-9 # = a word break)
    function tokens(text) {
        var s = String(text || ''), out = [], cur = null, i, ch, lc;
        for (i = 0; i < s.length; i++) {
            ch = s.charAt(i); lc = ch.toLowerCase();
            if (/[a-z0-9#]/.test(lc)) { if (!cur) cur = { w: '', s: i, e: i }; cur.w += lc; cur.e = i + 1; }
            else if (ch === "'" || ch === '’') continue;
            else if (cur) { out.push(cur); cur = null; }
        }
        if (cur) out.push(cur);
        return out;
    }
    // OWNER RULE 2026-10-04: Easy mode is HIDDEN on purpose; no flag, card or browse entry may talk about it (list: scripts/ai_atlas/enc_hidden_features.json, applied by the reader too)
    function hiddenTerm(id) {
        var R0 = W.SpbEncyclopedia; if (R0 && R0.hiddenId && R0.hiddenId(id)) return true;
        var t = termById(id) || {}, tx = String(t.title || '') + ' | ' + (t.aliases || []).join(' | ');
        return /(^|[._:])easy([._:]|$)/i.test(String(id || '')) || /\beasy[\s-]*mode\b|\beasy\s+(vs|or|and)\s+pro\b|\bpaint[\s-]*by[\s-]*numbers\b/i.test(tx) || /\bEASY\b/.test(tx);
    }
    // HELPER_V2 2026-10-04 owner: keep improving the Offline Helper. Flagging uses the FULL index: the glossary terms (D.index) AND every v2/v3 article alias (D.v2.byAlias,
    // 2,500+ phrases), longest phrase first; a colour next to a finish word ("pink chrome", "matte black", "candy red") is ONE compound term (a new colour + that finish).
    var _v2max = 0, _v2common = null;
    function v2Max() { if (!_v2max) { var V = (ENC() || {}).v2; _v2max = 1; if (V && V.byAlias) Object.keys(V.byAlias).forEach(function (a) { var n = a.split(' ').length; if (n > _v2max) _v2max = Math.min(n, 9); }); } return _v2max; }
    // a single v2 alias word lights up only when it is a real app word, never plain English ("store", "activate" ...)
    function v2Ok(a) { if (a.indexOf(' ') > 0) return true; if (!_v2common) { _v2common = {}; 'about activate activation add again all also back best better big bigger blank change check clean clear close color colour copy cost cut default delete done down edit export fast fill find fix flat flip free full good help hide high history home import key keep light like load look lost low main make more move name new next off open order paint pick play price rename reset save select set setup share show size slow small start stop store swap test text time tip top undo update use view wide work'.split(' ').forEach(function (w) { _v2common[w] = 1; }); } return a.length >= 4 && !_v2common[a] && !weakSet()[a]; }
    function v2Hit(a) { var V = (ENC() || {}).v2; if (!V || !V.byAlias || !V.byAlias[a] || !v2Ok(a)) return null; var p = V.byAlias[a], g = V.groups[p[0]], r = g && g.r[p[1]]; return r ? g.d + '.' + r[0] : null; }
    var LOOK_WORD = /^(matte|matt|flat|satin|gloss|glossy|metallic|metal flake|pearl|pearlescent|candy|candy apple|chrome|satin chrome|dark chrome|brushed|holographic|holo|frosted|wet look|neon|glitter|sparkle|sparkly|chameleon|carbon|powder coat|anodized|anodised)$/;
    function flag(text) {
        var D = ENC(); if (!D || !D.index) return [];
        var tk = tokens(text), out = [], i = 0, mw = Math.max(D.maxWords || 6, v2Max()), wk = weakSet();
        while (i < tk.length) {
            var hit = null, n;
            for (n = Math.min(mw, tk.length - i); n >= 1; n--) {
                var a = tk.slice(i, i + n).map(function (x) { return x.w; }).join(' ');
                if (D.index[a]) { hit = { alias: a, id: D.index[a], n: n }; break; }
                var vid = v2Hit(a); if (vid) { hit = { alias: a, id: vid, n: n, v2: true }; break; }
            }
            if (hit && hiddenTerm(hit.id)) { i += hit.n; continue; }
            if (hit) { var t = termById(hit.id) || {}; out.push({ s: tk[i].s, e: tk[i + hit.n - 1].e, alias: hit.alias, id: hit.id, kind: t.kind || 'info', tier: t.tier || (hit.v2 ? 2 : 3), title: t.title || hit.alias, weak: !!wk[hit.alias], v2: !!hit.v2 }); i += hit.n; }
            else i++;
        }
        out = compounds(out, String(text || ''));
        var strong = out.some(function (f) { return !f.weak; });
        return out.filter(function (f) { return !f.weak || strong; });          // a weak word ("change", "car") only lights up next to a real term
    }
    // two neighbours (only spaces / a hyphen between them) = colour + finish, either order -> one compound flag
    function lookWordOf(f) { var a = String(f.alias || ''); if (LOOK_WORD.test(a)) return a; var t = termById(f.id); return t && /_look$|^chrome_family$|^holographic$|^candy$|^pearl$/.test(t.id) && LOOK_WORD.test(a.split(' ')[0]) ? a : null; }
    function colourOf(f) { return /^colour:/.test(f.id) ? f.id.slice(7) : null; }
    function compounds(fl, s) {
        var out = [];
        for (var i = 0; i < fl.length; i++) {
            var f = fl[i], g = fl[i + 1], sp = splitCompound(f.alias);
            if (sp) { out.push({ s: f.s, e: f.e, alias: f.alias, id: 'compound:' + sp.colour + '+' + sp.look, kind: 'action', tier: 1, title: cap(f.alias), weak: false, compound: sp }); continue; }          // one alias that IS colour + finish ("matte black")
            if (g && /^[\s-]*$/.test(s.slice(f.e, g.s))) {
                var c = colourOf(f) || colourOf(g), lk = colourOf(f) ? lookWordOf(g) : lookWordOf(f);
                if (c && lk && !(colourOf(f) && colourOf(g))) { out.push({ s: f.s, e: g.e, alias: f.alias + ' ' + g.alias, id: 'compound:' + c + '+' + lk, kind: 'action', tier: 1, title: cap(f.alias + ' ' + g.alias), weak: false, compound: { colour: c, look: lk } }); i++; continue; }
            }
            out.push(f);
        }
        return out;
    }
    function isColourWord(w) { return !!(COLOUR_FALLBACK[w] || termById('colour:' + w)); }
    function splitCompound(a) {
        var w = String(a || '').split(' '); if (w.length < 2 || w.length > 3) return null;
        for (var k = 1; k < w.length; k++) { var x = w.slice(0, k).join(' '), y = w.slice(k).join(' '); if (isColourWord(x) && LOOK_WORD.test(y)) return { colour: x, look: y }; if (LOOK_WORD.test(x) && isColourWord(y)) return { colour: y, look: x }; }
        return null;
    }
    // a pseudo-term for a v2 article id or a compound, so the card / browse code can treat every flag the same way
    function v2Term(id) {
        var m = /^compound:([^+]+)\+(.+)$/.exec(String(id || ''));
        if (m) { var hx = colourHex(m[1]); return { id: id, title: cap(m[1] + ' ' + m[2]), kind: 'action', tier: 1, compound: { colour: m[1], look: m[2] }, colour: hx ? { hex: hx } : null, summary: cap(m[1]) + ' with a ' + m[2] + ' finish: two steps in one. “Do it” makes a recolour step (to ' + m[1] + ') and a ' + m[2] + ' step on top of it; you pick WHAT it goes on.', aliases: [], related: [], links: [], choices: [] }; }
        var V = (ENC() || {}).v2; if (!V || !V.groups) return null;
        var dot = String(id || '').indexOf('.'); if (dot < 1) return null; var dom = id.slice(0, dot), slug = id.slice(dot + 1);
        for (var gi = 0; gi < V.groups.length; gi++) { var g = V.groups[gi]; if (g.d !== dom) continue; for (var ri = 0; ri < g.r.length; ri++) if (g.r[ri][0] === slug) return { id: id, title: g.r[ri][1], kind: 'info', tier: 2, summary: g.r[ri][2] || '', aliases: g.r[ri][3] || [], related: [], links: [], choices: [], v2: true, art: g.f + '#' + id }; }
        return null;
    }
    function flagHtml(text, flags) {
        var s = String(text || ''), h = '', at = 0;
        (flags || flag(s)).forEach(function (f) {
            h += esc(s.slice(at, f.s));
            h += '<mark class="spb-ob-term k-' + esc(f.kind) + (f.weak || f.tier >= 3 ? ' soft' : '') + '" data-ob="term" data-term="' + esc(f.id) + '" title="' + esc(f.title) + '">' + esc(s.slice(f.s, f.e)) + '</mark>';
            at = f.e;
        });
        return h + esc(s.slice(at));
    }
    // ------------------------------------------------------------------ SpbEnc: the ONLY way this file reads the encyclopedia (orchestrator 2026-10-04: v2 = small index
    // js/spb-encyclopedia-data.js for flagging + per-domain article JSON data/encyclopedia/<domain>.json loaded on demand, article schema
    // {id,title,domain,summary,what,when[],how[],controls[]{label,range,default,effect},tips[],pitfalls[],related[],actions[],sources[]}). No article file yet ->
    // the index entry is shaped as an article (summary / details / related / choices as actions), so v2 data drops in without UI changes.
    var _artCache = {}, _artFail = {};
    function domainOf(t) {
        if (!t) return 'general'; if (t.domain) return String(t.domain);
        var p = /^([a-z_]+):/.exec(String(t.id || '')); if (p) return { colour: 'colours', part: 'parts', element: 'graphics', word: 'vocabulary', palette: 'liveries', shelf: 'finishes', tag: 'finishes', mod: 'modifiers' }[p[1]] || p[1];
        return t.kind === 'info' ? 'help' : (t.kind === 'action' ? 'looks' : 'how to');
    }
    function articleFromTerm(t) {
        if (!t) return null;
        return { id: t.id, title: t.title, domain: domainOf(t), summary: t.summary || '', what: (t.details || []).join(' '), when: [], how: ((t.flow && t.flow.steps) || []).map(function (s) { return s.text || s.type; }), controls: [], tips: [], pitfalls: [], related: (t.related || []).slice(), actions: (t.choices || []).slice(0, 8).map(function (c) { return { label: c.label, choice: c }; }), sources: [], links: t.links || [], fromIndex: true };
    }
    var SpbEnc = {
        lookup: function (alias) { var D = ENC(); if (!D || !D.index) return null; var a = tokens(alias).map(function (x) { return x.w; }).join(' '); return D.index[a] || null; },
        term: function (id) { return termById(id); },
        terms: function () { return ((ENC() || {}).terms || []).filter(function (t) { return !hiddenTerm(t.id); }); },
        domainOf: domainOf,
        // OFFLINE_BUILDER 2026-10-04: v2 article ids and index terms with an `art` pointer resolve through the SPB Encyclopedia reader (js/spb-encyclopedia.js)
        article: function (id) {
            var R = W.SpbEncyclopedia, t0 = termById(id);
            if (t0 && t0.compound) return Promise.resolve(articleFromTerm(t0));
            // HELPER_V2: always through the reader (it maps a glossary term to its v2/v3 article by name; the index card otherwise)
            if (R && R.get) return R.get(id).then(function (a) { if (!a || !t0) return a; var fb = articleFromTerm(t0), o = {}, k; for (k in fb) o[k] = fb[k]; for (k in a) o[k] = a[k]; if (!o.links || !o.links.length) o.links = fb.links; o.id = t0.id; o.artId = a.id; return o; }, function () { return SpbEnc.indexArticle(id); });
            return SpbEnc.indexArticle(id);
        },
        indexArticle: function (id) {
            var t = termById(id); if (!t) return Promise.resolve(null);
            var dom = domainOf(t), fb = articleFromTerm(t);
            if (_artFail[dom] || typeof fetch !== 'function' || W.SpbEncyclopedia) return Promise.resolve(fb);      // the reader resolves v2 files itself (no guessed <domain>.json 404s)
            var p = _artCache[dom] || (_artCache[dom] = fetch('data/encyclopedia/' + encodeURIComponent(dom) + '.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error('no file'); return r.json(); }).catch(function () { _artFail[dom] = 1; return null; }));
            return p.then(function (data) {
                var list = !data ? [] : (Array.isArray(data) ? data : (data.articles || [])), a = list.filter(function (x) { return x && x.id === id; })[0];
                if (!a) return fb; var out = {}; for (var k in fb) out[k] = fb[k]; for (var k2 in a) out[k2] = a[k2]; out.fromIndex = false; if (!out.links || !out.links.length) out.links = fb.links; return out;
            }, function () { return fb; });
        }
    };
    // every catalogue choice any term offers (finish / pattern / spec), searchable by label and by the term's aliases
    function allChoices() {
        if (_allChoices) return _allChoices;
        var seen = {}, out = [];
        ((ENC() || {}).terms || []).forEach(function (t) {
            (t.choices || []).forEach(function (c) {
                var ch = choiceOf(c); if (!ch) return; var k = ch.kind + ':' + ch.id; if (seen[k]) { seen[k].words += ' ' + (t.aliases || []).join(' '); return; }
                ch.term = t.id; ch.tier = t.tier || 3; ch.words = (c.label + ' ' + t.title + ' ' + (t.aliases || []).join(' ')).toLowerCase(); seen[k] = ch; out.push(ch);
            });
        });
        _allChoices = out; return out;
    }
    function choiceOf(c) {
        if (!c) return null;
        if (c.finish_id) return { kind: 'finish', id: c.finish_id, label: c.label, hex: c.hex || null };
        if (c.pattern_id) return { kind: 'pattern', id: c.pattern_id, label: c.label, hex: c.hex || null };
        if (c.spec_id) return { kind: 'spec', id: c.spec_id, label: c.label };
        return null;
    }
    function searchChoices(q, kinds, limit) {
        var ws = String(q || '').toLowerCase().split(/[^a-z0-9]+/).filter(function (w) { return w.length > 1; }); if (!ws.length) return [];
        var rows = allChoices().filter(function (c) { return (!kinds || kinds.indexOf(c.kind) !== -1) && ws.every(function (w) { return c.words.indexOf(w) !== -1; }); });
        rows.sort(function (a, b) { var al = a.label.toLowerCase(), bl = b.label.toLowerCase(), as = ws.filter(function (w) { return al.indexOf(w) !== -1; }).length, bs = ws.filter(function (w) { return bl.indexOf(w) !== -1; }).length; return (bs - as) || (a.tier - b.tier) || al.length - bl.length; });
        return rows.slice(0, limit || 18);
    }

    // ------------------------------------------------------------------ the look lists (built-in looks = exact SpbProEdit looks, catalogue = real ids)
    var SHINE_IDS = ['gloss', 'satin', 'matte', 'metallic', 'pearl', 'candy', 'chrome', 'satin chrome', 'dark chrome', 'brushed', 'wet look', 'frosted'];
    var FINISH_IDS = ['gloss', 'matte', 'satin', 'metallic', 'pearl', 'candy', 'chrome', 'satin chrome', 'brushed', 'powder coat', 'vinyl', 'patina'];
    var HOLO = { id: 'holographic', label: 'holographic', words: [], found: 'base::efx_holographic_drift', about: 'a holographic diffraction shimmer in the shine (spec); the paint colour stays' };
    // the same textures the parser knows (SpbProEdit TEXTURES): one concept, a SHINE (spec) version and a PAINT pattern version
    var TEX = [
        { id: 'snake', label: 'snakeskin', spec: 'snake_scale_diamond', specName: 'Snake Scale Diamond', pattern: 'snake_skin', patternName: 'Snake Skin' },
        { id: 'croc', label: 'crocodile skin', spec: 'croc_delta_armor', specName: 'Croc Delta Armor', pattern: 'crocodile', patternName: 'Crocodile' },
        { id: 'dragon', label: 'dragon scales', spec: 'dragon_scale_macro', specName: 'Dragon Scale Macro', pattern: 'dragon_scale', patternName: 'Dragon Scale' },
        { id: 'scales', label: 'fish scales', spec: 'spec_fish_scales', specName: 'Fish Scales', pattern: 'seigaiha_scales', patternName: 'Seigaiha Scales' }
    ];
    var COLOUR_NAMES = ['red', 'orange', 'yellow', 'gold', 'lime', 'green', 'teal', 'cyan', 'blue', 'navy', 'purple', 'violet', 'pink', 'hot pink', 'magenta', 'white', 'silver', 'grey', 'black', 'brown'];
    var COLOUR_FALLBACK = { red: '#d01818', orange: '#ff7a00', yellow: '#ffd200', gold: '#d7a72b', lime: '#8fe000', green: '#1a9a2a', teal: '#108f8f', cyan: '#18c8e0', blue: '#1450d8', navy: '#14245a', purple: '#6a1b9a', violet: '#7f3fbf', pink: '#ff7eb6', 'hot pink': '#ff3fa4', magenta: '#e01ca8', white: '#ffffff', silver: '#c0c4c8', grey: '#808080', black: '#111113', brown: '#6b3e1e' };
    function colourHex(name) { var t = termById('colour:' + name); return (t && t.colour && t.colour.hex) || COLOUR_FALLBACK[name] || null; }
    function lookById(id) { if (id === 'holographic') return HOLO; var E = Ed(); var l = E && E.lookById ? E.lookById(id) : null; return l || null; }
    function lookChoice(id) { var l = lookById(id); return l ? { kind: 'look', id: id, label: l.label, key: l.found } : null; }
    function texById(id) { return TEX.filter(function (t) { return t.id === id; })[0] || null; }
    function isShineKey(key) { return /^base::(f_|efx_holographic)/.test(String(key || '')); }
    var TEX_BAKED = { snake_scale_diamond: 1, spec_snake_scales: 1, croc_delta_armor: 1, dragon_scale_macro: 1, spec_fish_scales: 1 };
    function thumbFor(c, hex) {
        var hx = hex6(hex);
        if (!c) return '';
        if (c.kind === 'colour') return '';
        // HELPER_V2 2026-10-04 owner: keep improving the Offline Helper. The M/R/Cc split preview averages these fine
        // 2048-scale fields to one flat grey at 160 px (all four textures looked like clones); the baked 1:1 detail
        // crops (scripts/bake_offline_tex_thumbs.py) show each texture's own shape. Others keep the live preview.
        if ((c.kind === 'spec' || (c.kind === 'tex' && c.mode === 'spec')) && TEX_BAKED[c.id]) return '/thumbnails/offline_builder_tex/' + encodeURIComponent(c.id) + '.png?v=hv1';
        if (c.kind === 'spec' || (c.kind === 'tex' && c.mode === 'spec')) return '/api/spec-pattern-preview/' + encodeURIComponent(c.id);
        if (c.kind === 'pattern' || (c.kind === 'tex' && c.mode === 'pattern')) return '/api/swatch/pattern/' + encodeURIComponent(c.id) + '?size=200&color=' + hx;
        var key = c.key || c.id, m = /^(base|monolithic)::(.+)$/.exec(String(key || ''));
        return m ? '/api/swatch/' + m[1] + '/' + encodeURIComponent(m[2]) + '?size=200&color=' + hx : '';
    }

    // ------------------------------------------------------------------ the step model
    var _sid = 0;
    function newStep(o) { var s = { id: 's' + (++_sid), what: null, act: null, colour: null, finish: null, tex: null, extra: null, note: '', unknown: null, ask: null, chips: null }; if (o) for (var k in o) s[k] = o[k]; return s; }
    function stepIndex(steps, id) { for (var i = 0; i < steps.length; i++) if (steps[i].id === id) return i; return -1; }
    function rootOf(steps, st) { var seen = 0; while (st && st.what && st.what.k === 'step' && seen++ < 20) { var i = stepIndex(steps, st.what.ref); st = i >= 0 ? steps[i] : null; } return st; }
    function objName(o) { var w = String(o || '').split(' '); return w.length > 2 ? w.filter(function (x) { return x !== 'paint'; }).join(' ') : String(o || ''); }
    function palOf(env) { var E = Ed(); try { return E && E.prepPalette ? E.prepPalette((env || {}).palette || []) : []; } catch (e) { return []; } }
    function shareOf(tg, env) {
        var E = Ed(); if (!E || !tg || tg.kind !== 'colour' || !env) return null;
        try { var pal = palOf(env), r = E.resolveColour(E.wantFor(tg.word, tg.hex, tg.qual), pal); return r && r.entries && r.entries.length ? Math.round(r.share) : null; } catch (e) { return null; }
    }
    function whatOfTarget(tg) {
        if (!tg) return null;
        if (tg.kind === 'colour') return { k: 'colour', tg: clone(tg) };
        if (tg.kind === 'part') return { k: 'part', part: tg.part, tg: clone(tg) };
        if (tg.kind === 'layer') return { k: 'layer', layers: (tg.layers || []).slice(), word: tg.word, tg: clone(tg) };
        if (tg.kind === 'numbers' || tg.kind === 'sponsors' || tg.kind === 'body' || tg.kind === 'main') return { k: tg.kind, tg: clone(tg) };
        return { k: 'tg', tg: clone(tg) };
    }
    function whatLabel(w, steps, short) {
        if (!w) return '?';
        var tg = w.tg || {};
        if (w.k === 'step') { var i = stepIndex(steps || [], w.ref); return short ? num(i) : 'the result of step ' + num(i); }
        if (w.k === 'colour') {
            var sc = [];
            if (tg.bodyNamed || (tg.artObjects && tg.artObjects.length)) sc.push('base paint'); (tg.artObjects || []).forEach(function (o) { sc.push(objName(o)); });
            if (tg.layers && tg.layers.length) sc = ['in ' + tg.layers.join(', ')];
            if (tg.parts && tg.parts.length) sc.push('on the ' + tg.parts.map(function (p) { return String(p).replace('@', ', '); }).join(' + '));
            if (tg.object) sc.push('on the ' + objName(tg.object));
            return cap(tg.word) + (sc.length ? ' (' + sc.join(' + ') + ')' : '');
        }
        if (w.k === 'part') return 'The ' + w.part;
        if (w.k === 'layer') return 'The ' + (w.word || (w.layers || [])[0]) + ' layer';
        if (w.k === 'numbers') return 'The numbers';
        if (w.k === 'sponsors') return 'The sponsors / logos';
        if (w.k === 'body') return 'The whole car';
        if (w.k === 'main') return 'The main colour';
        if (w.k === 'box') return (w.colour ? cap(w.colour.name) + ' inside your box' : 'Everything inside your box');
        var E = Ed(); try { if (E && E.targetPhrase) return cap(E.targetPhrase(tg, [])); } catch (e) {}
        return cap(tg.word || tg.kind || 'that');
    }
    function lookWords(st) {
        var b = [];
        if (st.finish) b.push(st.finish.label);
        if (st.tex) b.push(st.tex.label);
        if (st.extra) { if (st.extra.rel) b.push(st.extra.rel === 'up' ? 'glossier' : 'duller'); if (st.extra.pop) b.push('stand out'); if (st.extra.shade) b.push(String(st.extra.shade)); if (st.extra.recipe) b.push(String(st.extra.recipe)); if (st.extra.scaleMul) b.push('size ' + Math.round(st.extra.scaleMul * 100) + '%'); if (st.extra.strengthMul) b.push('strength ' + Math.round(Math.min(1, st.extra.strengthMul) * 100) + '%'); }
        return b;
    }
    function stepText(st, steps, short) {
        var W0 = whatLabel(st.what, steps, short), lw = lookWords(st);
        if (st.act && st.act !== 'recolour' && !lw.length) return W0 + ' → ? ' + ({ finish: 'finish', pattern: 'pattern', shine: 'shine' }[st.act]);
        if (st.act === 'recolour') return W0 + ' → ' + (st.colour ? cap(st.colour.name) : '?');
        if (st.act === 'pattern') return (lw.length ? cap(lw.join(' + ')) : '?') + ' pattern on ' + (short ? W0 : W0.charAt(0).toLowerCase() + W0.slice(1));
        if (st.act === 'shine') return (lw.length ? cap(lw.join(' + ')) : '?') + ' shine on ' + (short ? W0 : W0.charAt(0).toLowerCase() + W0.slice(1));
        if (st.act === 'finish') return (lw.length ? cap(lw.join(' + ')) : '?') + ' finish on ' + (short ? W0 : W0.charAt(0).toLowerCase() + W0.slice(1));
        return W0 + ' → ?';
    }
    function readAs(steps) { return (steps || []).map(function (st, i) { return num(i) + ' ' + stepText(st, steps, true); }).join('  '); }
    // a compact, test-friendly description of a step list
    function summary(steps) {
        return (steps || []).map(function (st) {
            var w = st.what, ws = !w ? '?' : (w.k === 'colour' ? 'colour:' + w.tg.word : (w.k === 'part' ? 'part:' + w.part : (w.k === 'step' ? 'step' + (stepIndex(steps, w.ref) + 1) : (w.k === 'layer' ? 'layer:' + (w.word || w.layers[0]) : (w.k === 'box' ? 'box' + (w.colour ? ':' + w.colour.name : '') : w.k)))));
            var a = st.act || '?', l = st.act === 'recolour' ? (st.colour ? st.colour.name : '?') : (lookWords(st).join('+') || '?');
            return ws + '>' + a + ':' + l + (stepOpen(st) ? '!' : '');
        });
    }
    function stepOpen(st) { return !st.what || !st.act || (st.act === 'recolour' && !st.colour) || (st.act !== 'recolour' && !st.finish && !st.tex && !(st.extra && (st.extra.rel || st.extra.pop || st.extra.shade || st.extra.recipe))) || !!st.ask; }
    function actFor(look, tex) {
        if (tex && tex.mode === 'pattern' && !look) return 'pattern';
        if ((look && isShineKey(look.key)) || (tex && tex.mode === 'spec')) return 'shine';
        return 'finish';
    }
    function finishOfLook(lk) { return lk ? { kind: 'raw', look: lk, label: lk.label || lk.id, key: lk.found || (lk.zone && lk.zone.finish) || null } : null; }
    function texOfOp(tx) { return tx ? { raw: tx, mode: tx.mode, id: tx.mode === 'pattern' ? tx.pattern : tx.spec, label: tx.label, name: tx.mode === 'pattern' ? tx.patternName : tx.specName } : null; }
    function extraOf(op) { var x = {}, any = false; ['rel', 'soft', 'strong', 'shade', 'keep', 'pop', 'recipe', 'sub', 'exclude', 'scaleMul', 'shadeDir', 'strengthMul'].forEach(function (k) { if (op[k] && !(Array.isArray(op[k]) && !op[k].length)) { x[k] = clone(op[k]); any = true; } }); return any ? x : null; }

    // ------------------------------------------------------------------ parser plan -> steps (TYPING PRE-FILLS THE BUILDER)
    function fromPlan(ed, env, text) {
        var steps = [], E = Ed();
        if (!ed) return { steps: steps };
        if (ed.kind === 'ops') {
            (ed.ops || []).forEach(function (op) {
                if (op.ext && commonLook(op.ext)) { op = Object.assign({}, op, { ext: null }); }          // HELPER_V2 blind 2026-10-04: "keep" / "racing" / "little" is never a look name
                var s1 = newStep({ what: whatOfTarget(op.target), extra: extraOf(op) }), s2 = null;
                var hasLook = !!(op.look || op.texture || (op.ext && !op.look) || (s1.extra && (s1.extra.rel || s1.extra.pop || s1.extra.shade || s1.extra.recipe)));
                if (op.colour) { s1.act = 'recolour'; s1.colour = clone(op.colour); steps.push(s1); if (hasLook) { s2 = newStep({ what: { k: 'step', ref: s1.id } }); if (s1.extra && !s1.extra.keep) { s2.extra = s1.extra; s1.extra = null; } steps.push(s2); } }
                else { s2 = s1; steps.push(s1); }
                if (s2) {
                    s2.finish = finishOfLook(op.look); s2.tex = texOfOp(op.texture); s2.act = actFor(s2.finish, s2.tex);
                    if (op.ext && !op.look) { s2.unknown = op.ext; s2.note = 'I do not know a look called “' + op.ext + '”. Pick one below (or search).'; s2.act = op.texture ? s2.act : 'finish'; s2.search = op.ext; }
                    if (op.ext && !op.look) { var et = termById(SpbEnc.lookup(op.ext) || ''); if (et && et.kind !== 'info') prefillFromTerm(s2, et, op.ext); }
                }
            });
            var covered = {}; (ed.ops || []).forEach(function (op) { if (op.ext) covered[op.ext] = 1; });
            (ed.unknown || []).filter(function (u) { return !covered[u]; }).forEach(function (u) { steps.push(newStep({ unknown: u, note: 'I did not understand “' + u + '”. Pick what it should change, then the look.', search: u })); });
        } else if (ed.kind === 'ask') {
            var t = String(text || ed.text || ''), cls = [];
            try { cls = E && E.splitClauses ? E.splitClauses(E.fixText ? E.fixText(t) : t) : []; } catch (e) { cls = []; }
            cls.forEach(function (c) {
                var pc = null; try { pc = E.parseClause(c); } catch (e2) { pc = null; } if (!pc) return;
                var tgs = (pc.targets || []).length ? pc.targets : (pc.colours && pc.colours.length || pc.looks && pc.looks.length ? [null] : []);
                tgs.forEach(function (tg) {
                    var s = newStep({ what: whatOfTarget(tg) });
                    if (tg && tg.kind === 'colour' && pc.colours && pc.colours.length) { s.act = 'recolour'; s.colour = clone(pc.colours[0]); }
                    else if (pc.colours && pc.colours.length && tg) { s.act = 'recolour'; s.colour = clone(pc.colours[0]); }
                    if (pc.looks && pc.looks.length) { var lk = pc.looks[0].look || pc.looks[0]; var f = finishOfLook(lk); if (f && f.key) { if (s.act === 'recolour') { steps.push(s); s = newStep({ what: { k: 'step', ref: s.id } }); } s.finish = f; s.act = actFor(f, null); } }
                    if (!s.act) s.note = (ed.text || 'What should I do with ' + whatLabel(s.what, steps).toLowerCase() + '?').replace(/Pick a look, or tell me a colour\./, 'Pick what to do, then the look.');
                    steps.push(s);
                });
            });
            if (!steps.length) steps.push(newStep({ note: ed.text || 'Pick what to change, then what to do.' }));
        }
        return { steps: steps };
    }
    // a sentence the parser cannot read at all: the encyclopedia words still pre-fill an open step (never an empty builder)
    // the encyclopedia knows a look the parser does not ("carbon fiber"): its FIRST catalogue choice is pre-filled (shown before Run), the others stay one click away
    // HELPER_V2 blind 2026-10-04 (owner: keep improving the Offline Helper): an everyday word ("racing", "little", "nothing", "team", "keep") never picks a finish;
    // the generic word:/tag: terms only count for a word that is not in this list
    var COMMON_LOOK = {}; ('racing race racer little bit nothing something anything everything team missing keep leave else rest fix make better best nice cool good great new old big small ' +
        'more less color colour paint car please want need fast slow simple thing things stuff look looks kind sort type way lot really very just like maybe also all some it my our the a an and or but ' +
        'touch change alone same number numbers sponsor sponsors logo logos side sides top bottom middle front back rear left right whole entire full part parts real actual proper').split(' ').forEach(function (w) { if (w) COMMON_LOOK[w] = 1; });
    function commonLook(word, id) {
        var ws = String(word || '').toLowerCase().replace(/[^a-z ]+/g, ' ').split(/\s+/).filter(Boolean);
        if (!ws.length) return true;
        if (ws.every(function (w) { return COMMON_LOOK[w]; })) return true;
        return !!id && /^(word|tag):/.test(id) && ws.length === 1 && ws[0].length < 5;
    }
    function prefillFromTerm(s, t, word) {
        if (!t || !t.choices || !t.choices.length) return false;
        var wl = String(word || '').toLowerCase(), c0 = t.choices.filter(function (c) { return wl && String(c.label).toLowerCase().indexOf(wl) !== -1; })[0] || null, ci = null;
        if (!c0 && wl) { var wk = wl.split(/\s+/).filter(function (x) { return x.length > 3 && !/^(?:paint|look|style|finish|scheme)$/.test(x); }).pop() || '', nm = wk ? searchChoices(wk, ['pattern', 'finish'], 8).filter(function (c) { return String(c.label).toLowerCase().indexOf(wk) !== -1; })[0] : null; if (nm) { ci = choiceItem(nm); if (ci) c0 = { label: nm.label }; } }          // HELPER_V2 fix pass 4 2026-10-04 owner: keep improving the Offline Helper -- "splatter" picks a catalogue item NAMED splatter, not the term's first choice (Chain Link)
        if (!c0) c0 = t.choices[0]; if (!ci) ci = choiceItem(choiceOf(c0)); if (!ci) return false;
        pickChoice(s, ci); s.termChoices = t.id; s.note = 'For “' + (word || t.title) + '” I picked ' + c0.label + ' (' + t.title + '); other ' + t.title + ' looks are below.'; s.prefilled = true; return true;
    }
    function fromFlags(text, env) {
        var steps = [], fl = flag(text), E = Ed(), pal = palOf(env), what = null, colour = null, look = null, built = null, tex = null;
        fl.forEach(function (f) {
            var t = termById(f.id); if (!t) return;
            if (f.compound) {          // HELPER_V2: "candy red" = the NEW colour red + a candy finish (never "the red on the car")
                var cx = colourHex(f.compound.colour); if (!colour && cx) colour = { name: f.compound.colour, hex: cx, at: 0, qual: null, exact: false };
                var cl = null; try { cl = /holo/.test(f.compound.look) ? HOLO : (E && E.lookFor ? E.lookFor(f.compound.look) : null); } catch (e0) { cl = null; }
                if (cl && cl.found && !built) built = cl; return;
            }
            if (!what && /^(the |my |whole|entire |all of the )?(whole car|entire car|car body|whole thing|everything|all of it)$/.test(f.alias)) what = { k: 'body' };
            if (/^part:/.test(t.id) && !what) what = { k: 'part', part: String((t.part && (t.part.name || t.part)) || t.title).toLowerCase() };
            if (/^number$|^numbers$/.test(t.id) && !what) what = { k: 'numbers' };
            if (/^colour:/.test(t.id) && t.colour && t.colour.hex) {
                var nm = t.id.slice(7), onCar = pal.filter(function (p) { return p.name === nm || (E && E.familyOf && E.familyOf(p.hex) === E.familyOf(t.colour.hex) && p.share >= 1); })[0];
                if (onCar && !what && !colour) what = { k: 'colour', tg: { kind: 'colour', word: onCar.name, hex: onCar.hex, qual: null, at: 0, parts: null } };
                else if (!colour) colour = { name: nm, hex: t.colour.hex, at: 0, qual: null, exact: false };
            }
            var tx = TEX.filter(function (x) { return x.id === ({ snakeskin: 'snake', crocodile: 'croc' }[t.id] || t.id); })[0];
            if (tx && !tex) { tex = tx; return; }
            var bl = null; try { bl = /holo/.test(f.alias) ? HOLO : (E && E.lookFor ? E.lookFor(f.alias) : null); } catch (e) { bl = null; }
            if (bl && bl.found && !built) { built = bl; return; }
            if (!look && t.kind !== 'info' && t.choices && t.choices.length && !/^colour:/.test(t.id) && !commonLook(f.alias, t.id)) look = { term: t, word: f.alias };
        });
        var s = newStep({ what: what });
        if (colour && what) { s.act = 'recolour'; s.colour = colour; steps.push(s); s = (look || built || tex) ? newStep({ what: { k: 'step', ref: s.id } }) : null; }
        else if (colour && !what) { s.act = 'recolour'; s.colour = colour; s.note = 'Pick WHAT should become ' + colour.name + '.'; steps.push(s); s = (look || built || tex) ? newStep({ what: { k: 'step', ref: s.id } }) : null; }
        if (s) {
            if (built || tex) { if (built) s.finish = { kind: 'raw', look: built, label: built.label, key: built.found }; if (tex) s.tex = { mode: 'spec', id: tex.spec, concept: tex.id, label: tex.label, name: tex.specName }; s.act = actFor(s.finish, s.tex); if (look) s.termChoices = look.term.id; }
            else if (look) prefillFromTerm(s, look.term, look.word);
            if (!s.what) s.note = (s.note ? s.note + ' ' : '') + 'Pick WHAT it goes on.';
            else if (!s.act) s.note = 'Pick what to do, then the look.';
            steps.push(s);
        }
        return { steps: steps };
    }
    function fromText(text, env) {
        var E = Ed(), ed = null; try { ed = E && env && (env.palette || []).length ? E.plan(text, env) : null; } catch (e) { ed = null; }
        var r = (ed && (ed.kind === 'ops' || ed.kind === 'ask')) ? fromPlan(ed, env, text) : { steps: [] };
        if (!r.steps.length) r = fromFlags(text, env);
        r.ed = ed; return r;
    }

    // ------------------------------------------------------------------ steps -> one SpbProEdit plan (Run)
    function targetOf(w) {
        if (!w) return null;
        if (w.k === 'colour') return clone(w.tg);
        if (w.k === 'part') return w.tg ? clone(w.tg) : { kind: 'part', part: w.part, at: 0 };
        if (w.k === 'layer') return w.tg ? clone(w.tg) : { kind: 'layer', layers: w.layers.slice(), word: w.word || w.layers[0] };
        if (w.k === 'numbers' || w.k === 'sponsors' || w.k === 'body' || w.k === 'main') return w.tg ? clone(w.tg) : { kind: w.k };
        if (w.k === 'box' && w.tg) return clone(w.tg);   // box + colour + optional Where layers (OFFLINE_BUILDER: the can only, not the body around it)
        if (w.k === 'box') return w.colour ? { kind: 'colour', word: w.colour.name, hex: w.colour.hex, qual: null, at: 0, parts: null } : { kind: 'body' };
        if (w.k === 'tg') return clone(w.tg);
        return null;
    }
    function lookOfFinish(f) {
        if (!f) return null;
        if (f.kind === 'raw') return clone(f.look);
        if (f.kind === 'look') return clone(lookById(f.id));
        var own = !!f.own; try { var AT = W.SpbAIAtlas, it = AT && AT.lookup ? AT.lookup(f.key) : null; if (it) own = it.o === 1; else if (/^monolithic::/.test(f.key)) own = true; } catch (e) {}
        if (isShineKey(f.key)) return { id: 'cat', label: f.label, words: [], found: f.key, about: '' };
        return { id: 'ext', label: f.label, found: f.key, zone: { finish: f.key }, colourFrom: own ? 'own' : 'zone', defaultColour: null, about: '' };
    }
    function texOf(t) {
        if (!t) return null; if (t.raw) return clone(t.raw);
        var c = texById(t.concept); if (c) return { id: c.id, label: c.label, mode: t.mode, word: c.label, spec: c.spec, specName: c.specName, specAlt: null, pattern: c.pattern, patternName: c.patternName };
        return { id: 'id', label: t.label, mode: t.mode, word: t.label, spec: t.id, specName: t.name || t.label, specAlt: null, pattern: t.id, patternName: t.name || t.label };
    }
    function blankOp(tg) { return { target: tg, look: null, colour: null, rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, recipe: null, sub: null, ext: null, texture: null }; }
    function applyStep(op, st) {
        if (st.extra) for (var k in st.extra) op[k] = clone(st.extra[k]);
        if (st.act === 'recolour' && st.colour) { op.colour = clone(st.colour); op.keep = false; }
        if (st.act !== 'recolour') { var lk = lookOfFinish(st.finish); if (lk) op.look = lk; var tx = texOf(st.tex); if (tx) op.texture = tx; }
    }
    function readyProblem(st, i, steps) {
        if (!st.what) return 'step ' + num(i) + ': pick WHAT to change';
        if (st.what.k === 'step' && stepIndex(steps, st.what.ref) < 0) return 'step ' + num(i) + ': the step it builds on was removed';
        if (st.what.k === 'step' && stepIndex(steps, st.what.ref) >= i) return 'step ' + num(i) + ': it can only build on an EARLIER step';
        if (!st.act) return 'step ' + num(i) + ': pick what to DO';
        if (st.act === 'recolour' && !st.colour) return 'step ' + num(i) + ': pick the new colour';
        if (st.act !== 'recolour' && !st.finish && !st.tex && !(st.extra && (st.extra.rel || st.extra.pop || st.extra.shade || st.extra.recipe))) return 'step ' + num(i) + ': pick WHICH LOOK';
        if (st.what.k === 'box' && st.what.rect) { var r = st.what.rect, a = Math.abs(r.x1 - r.x0) * Math.abs(r.y1 - r.y0); if (a > 0.12) return 'step ' + num(i) + ': that box covers ' + Math.round(a * 100) + '% of the sheet; draw it tighter (12% at most)'; }
        return null;
    }
    function toPlan(steps, text) {
        var ops = [], byStep = {}, problems = [], boxes = false, spec = true;
        (steps || []).forEach(function (st, i) {
            var pb = readyProblem(st, i, steps); if (pb) { problems.push(pb); return; }
            if (st.what.k === 'step') { var base = byStep[st.what.ref]; if (!base) { problems.push('step ' + num(i) + ': the step it builds on is not ready'); return; } applyStep(base, st); byStep[st.id] = base; }
            else { var op = blankOp(targetOf(st.what)); if (st.what.k === 'box') { op._box = clone(st.what.rect); boxes = true; } applyStep(op, st); ops.push(op); byStep[st.id] = op; }
            if (st.act === 'recolour' || st.act === 'pattern' || (st.finish && !/^base::f_/.test(String(st.finish.key || '')))) spec = false;          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: in-app gate b4-155 -- "hood holographic" ran as spec-only and the app's spec-only guard refused efx_holographic_drift (only Foundation f_* finishes pass it)
        });
        if (problems.length) return { ok: false, problems: problems };
        var raw = String(text || readAs(steps)), E = Ed(), norm = raw.toLowerCase().replace(/[^a-z0-9#' ]+/g, ' ').replace(/\s+/g, ' ').trim();
        var ed = { kind: 'ops', ops: ops, alt: [], unknown: [], text: norm, usedLast: false, usedSame: false, exclude: [], atomicScope: false, raw: raw, builder: true };
        if (boxes) ed.force = true;          // a box is the buyer's own pick: a small colour inside it is meant
        if ((steps || []).some(function (st) { return st.what && st.what.tg && st.what.tg.hiddenOk; })) ed.force = true;          // HELPER_V2: "the original yellow under it" = the hidden colour too
        return { ok: true, ed: ed, specOnly: spec, post: boxes ? postFor(ed) : null };
    }
    // the box steps: the SAME zone as compiled, limited to the drawn rectangle (zone-kit region.rect, 0-1 fractions; combines with the colour test)
    function postFor(ed) {
        return function (cm, env, compileFn) {
            if (!cm || !cm.zones || !cm.zones.length) return cm;
            var at = 0, cf = compileFn || (Ed() && Ed().compile);
            ed.ops.forEach(function (op) {
                var n = 1; try { n = cf({ ops: [op], text: ed.text, raw: ed.raw, force: ed.force }, env).zones.length; } catch (e) { n = 1; }
                if (op._box) for (var k = at; k < at + n && k < cm.zones.length; k++) {
                    var z = cm.zones[k], rect = { x0: op._box.x0, y0: op._box.y0, x1: op._box.x1, y1: op._box.y1 };
                    if (op.target && op.target.kind === 'colour') z.region.rect = rect; else z.region = { rect: rect };
                    z.name = String(z.name || '').replace(/^Whole car/, 'Inside your box') + (op.target && op.target.kind === 'colour' ? ' (inside your box)' : '');
                    z._meta = z._meta || {}; z._meta.box = true; z._meta.share = null;
                }
                at += n;
            });
            return cm;
        };
    }
    // preview check: every root op compiled ALONE; a step whose op cannot resolve shows the parser's own question (e.g. "I do not see any turquoise")
    function check(steps, env) {
        var E = Ed(); if (!E || !env || !(env.palette || []).length) return steps;
        steps.forEach(function (st) { st.ask = null; st.chips = null; });
        steps.forEach(function (st, i) {
            if (!st.what || st.what.k === 'step' || readyProblem(st, i, steps)) return;
            var grp = steps.filter(function (s2) { return s2 === st || rootOf(steps, s2) === st; }), pl = toPlan(grp);
            if (!pl.ok) return;
            var cm = null; try { cm = E.compile(pl.ed, env); if (pl.post) cm = pl.post(cm, env, E.compile); } catch (e) { cm = null; }
            if (!cm) return;
            if (cm.objects && cm.objects.length && !cm.zones.length) { st.ask = 'You named the ' + objName(cm.objects[0].object) + ': draw a box around it, or pick the layers it is in (Where).'; st.chips = ['box']; return; }
            if (!cm.zones.length && cm.hiddenAsk && st.what.k === 'colour') { hiddenAskFor(st, cm.hiddenAsk, env); return; }
            if (!cm.zones.length && cm.ask) { st.ask = String(cm.ask.text || '').replace(/^Nothing was changed[:.]?\s*/i, ''); st.chips = ['what']; }
        });
        return steps;
    }
    // HELPER_V2 2026-10-04 (FIRSTTEST open item, owner's 8-zone seafoam design): "the yellow" exists only in the SOURCE paint, under a zone that paints over it.
    // Ask FIRST, with two exact chips: change what the buyer SEES there (the zone's colour), or the original colour under it (= the parser's "anyway").
    function hiddenAskFor(st, hi, env) {
        var word = (st.what.tg && st.what.tg.word) || hi.word, zn = (hi.zones || [])[0] || 'one of your zones', zc = (((env || {}).zoneColours) || []).filter(function (z) { return z.zone === zn; })[0];
        var shows = hi.shows || 'another colour', sw = '“' + zn + '”';
        st.ask = 'Your body shows ' + sw + ' (' + shows + ') now, not ' + word + ': that zone paints over it. Change the ' + zn + ', or the original ' + word + ' under it?';
        st.chips = [];
        if (zc) st.chips.push({ label: 'Change the ' + zn, hid: 'shown', name: shows, hex: zc.hex });
        st.chips.push({ label: 'Change the original ' + word + ' under it', hid: 'hidden' });
        st.hiddenInfo = { word: word, zone: zn, shows: shows };
    }
    // a hidden-colour chip -> the step's WHAT (exact; Run stays the copilot's undoable path)
    function hiddenPick(st, ch) {
        if (!st || !ch) return st;
        if (ch.hid === 'shown') { st.what = { k: 'colour', tg: { kind: 'colour', word: ch.name, hex: ch.hex, qual: null, at: 0, parts: null } }; st.note = 'Changing what shows there now: the ' + (st.hiddenInfo ? st.hiddenInfo.zone : ch.name) + ' (' + ch.name + ').'; }
        else if (ch.hid === 'hidden') { st.what.tg.hiddenOk = true; st.note = 'Changing the original ' + st.what.tg.word + ' under your zone (it will show on top).'; }
        st.prefilled = true; st.ask = null; st.chips = null;
        return st;
    }

    // ------------------------------------------------------------------ choices offered in the step editor
    function whatChoices(env, steps, st) {
        var out = [], pal = palOf(env), i = stepIndex(steps, st.id);
        steps.slice(0, i < 0 ? steps.length : i).forEach(function (s0, j) { out.push({ grp: 'Same pixels', label: 'Result of ' + num(j), sub: stepText(s0, steps, true), what: { k: 'step', ref: s0.id } }); });
        pal.filter(function (p) { return p.share >= 0.5; }).slice(0, 10).forEach(function (p) { out.push({ grp: 'Colours on the car', label: cap(p.name), sub: Math.round(p.share) + '%', hex: p.hex, what: { k: 'colour', tg: { kind: 'colour', word: p.name, hex: p.hex, qual: null, at: 0, parts: null } } }); });
        (((env || {}).zoneColours) || []).slice(0, 4).forEach(function (z) { var nm = (Ed() && Ed().prepPalette) ? (Ed().prepPalette([{ hex: z.hex, share_pct: 1 }])[0] || {}).name : z.hex; out.push({ grp: 'Colours your zones paint', label: cap(nm), sub: z.zone, hex: z.hex, what: { k: 'colour', tg: { kind: 'colour', word: nm, hex: z.hex, qual: null, at: 0, parts: null } } }); });
        var parts = []; try { parts = (W.SpbProCar && W.SpbProCar.parts) ? W.SpbProCar.parts() : []; } catch (e) { parts = []; }
        if (!parts || !parts.length) parts = ['hood', 'roof', 'left side', 'right side', 'front bumper', 'rear bumper', 'trunk', 'spoiler'];
        parts.slice(0, 14).forEach(function (p) { out.push({ grp: 'Parts', label: cap(p), what: { k: 'part', part: String(p).toLowerCase() } }); });
        (((env || {}).layers) || []).filter(function (l) { return !l.hidden && !/^\s*(wire|mask|car[ _]*mandatory|template|guides?)\b/i.test(String(l.name || '')); }).slice(0, 16).forEach(function (l) { out.push({ grp: 'Layers', label: l.name, sub: l.role || '', what: { k: 'layer', layers: [l.name], word: l.name } }); });
        out.push({ grp: 'Other', label: 'Numbers', what: { k: 'numbers' } }); out.push({ grp: 'Other', label: 'Sponsors / logos', what: { k: 'sponsors' } }); out.push({ grp: 'Other', label: 'Whole car', what: { k: 'body' } });
        out.push({ grp: 'Other', label: '▭ Box-select an area', sub: 'for art that shares a layer', box: true });
        return out;
    }
    function lookChoices(st) {
        var out = [], hx = effHex(st);
        if (st.act === 'recolour') COLOUR_NAMES.forEach(function (n) { var h = colourHex(n); if (h) out.push({ kind: 'colour', label: cap(n), hex: h, name: n }); });
        else if (st.act === 'shine') {
            SHINE_IDS.concat(['holographic']).forEach(function (id) { var c = lookChoice(id); if (c) out.push(c); });
            TEX.forEach(function (t) { out.push({ kind: 'tex', mode: 'spec', id: t.spec, concept: t.id, label: t.label, name: t.specName, grp: 'Texture in the shine (optional)' }); });
            allChoices().filter(function (c) { return c.kind === 'spec' && !TEX.some(function (t) { return t.spec === c.id; }); }).forEach(function (c) { out.push({ kind: 'tex', mode: 'spec', id: c.id, label: c.label, name: c.label, grp: 'Texture in the shine (optional)' }); });
        } else if (st.act === 'finish') {
            FINISH_IDS.forEach(function (id) { var c = lookChoice(id); if (c) out.push(c); });
            ['carbon_fiber', 'holographic', 'camo', 'chrome_family', 'flames'].forEach(function (tid) { var t = termById(tid); ((t && t.choices) || []).filter(function (c) { return c.finish_id; }).slice(0, 2).forEach(function (c) { out.push({ kind: 'cat', key: c.finish_id, id: c.finish_id, label: c.label, grp: 'From the catalogue' }); }); });
        } else if (st.act === 'pattern') {
            TEX.forEach(function (t) { out.push({ kind: 'tex', mode: 'pattern', id: t.pattern, concept: t.id, label: t.label, name: t.patternName }); });
            ['carbon_fiber', 'camo', 'flames', 'snakeskin'].forEach(function (tid) { var t = termById(tid); ((t && t.choices) || []).filter(function (c) { return c.pattern_id; }).slice(0, 3).forEach(function (c) { if (!out.some(function (o) { return o.id === c.pattern_id; })) out.push({ kind: 'tex', mode: 'pattern', id: c.pattern_id, label: c.label, name: c.label, grp: 'From the catalogue' }); }); });
        }
        if (st.found && st.act !== 'recolour') st.found.slice().reverse().forEach(function (c) { var o = {}; for (var k0 in c) o[k0] = c[k0]; o.grp = 'Catalogue: ' + (st.foundFor || 'your words'); out.unshift(o); });          // HELPER_V2: a look searched in the catalogue
        if (st.termChoices) { var tt = termById(st.termChoices); ((tt && tt.choices) || []).forEach(function (c) { var ch = choiceItem(choiceOf(c)); if (ch && (!st.act || actOfChoice(ch) === st.act)) out.unshift(ch); }); }
        out.forEach(function (c) { c.thumb = thumbFor(c, c.hex || hx); });
        return out;
    }
    function choiceItem(c) {
        if (!c) return null;
        if (c.kind === 'finish') return { kind: 'cat', key: c.id, id: c.id, label: c.label, hex: c.hex || null };
        if (c.kind === 'pattern') return { kind: 'tex', mode: 'pattern', id: c.id, label: c.label, name: c.label, hex: c.hex || null };
        if (c.kind === 'spec') { var tx = TEX.filter(function (t) { return t.spec === c.id || t.id === c.id; })[0]; return { kind: 'tex', mode: 'spec', id: tx ? tx.spec : c.id, concept: tx ? tx.id : null, label: tx ? tx.label : c.label, name: tx ? tx.specName : c.label }; }
        return null;
    }
    function actOfChoice(ch) { if (ch.kind === 'colour') return 'recolour'; if (ch.kind === 'tex') return ch.mode === 'pattern' ? 'pattern' : 'shine'; if (ch.kind === 'look') return isShineKey(ch.key) ? 'shine' : 'finish'; return isShineKey(ch.key) ? 'shine' : 'finish'; }
    // put a clicked choice into a step (exact: one click = one field)
    function pickChoice(st, ch) {
        if (!st || !ch) return st;
        if (!st.act) st.act = actOfChoice(ch);
        if (ch.kind === 'colour') { st.act = 'recolour'; st.colour = { name: ch.name || String(ch.label).toLowerCase(), hex: ch.hex, at: 0, qual: null, exact: !!ch.exact }; st.finish = null; st.tex = null; }
        else if (ch.kind === 'tex') { if (st.act === 'recolour' || st.act === 'finish') st.act = ch.mode === 'pattern' ? 'pattern' : 'shine'; st.tex = (st.tex && st.tex.id === ch.id) ? null : { mode: ch.mode, id: ch.id, concept: ch.concept || null, label: ch.concept ? (texById(ch.concept) || {}).label || ch.label : ch.label, name: ch.name || ch.label }; if (st.act === 'pattern') st.finish = null; }
        else if (ch.kind === 'look') { st.finish = { kind: 'look', id: ch.id, label: ch.label, key: ch.key }; if (st.act === 'pattern' || st.act === 'recolour') st.act = actOfChoice(ch); }
        else if (ch.kind === 'cat') { st.finish = { kind: 'cat', key: ch.key, label: ch.label }; if (st.act !== 'finish' && !(st.act === 'shine' && isShineKey(ch.key))) st.act = actOfChoice(ch); }
        st.unknown = null; st.note = ''; st.ask = null; st.termChoices = st.termChoices || null;
        return st;
    }
    function setAct(st, act) { if (st.act === act) return st; st.act = act; if (act === 'recolour') { st.finish = null; st.tex = null; } else { st.colour = null; if (act === 'pattern') { st.finish = null; if (st.tex && st.tex.mode !== 'pattern') st.tex = null; } if (act !== 'pattern' && st.tex && st.tex.mode === 'pattern') st.tex = null; if (act === 'finish' && st.finish && isShineKey(st.finish.key) && st.finish.kind === 'cat') st.finish = null; } st.ask = null; return st; }
    function effHex(st) { if (!st) return null; if (st.colour) return st.colour.hex; var w = st.what; if (w && w.k === 'colour') return w.tg.hex; if (w && w.k === 'box' && w.colour) return w.colour.hex; return null; }
    // an encyclopedia card's choice -> a builder step (targets the result of the last step when there is one; otherwise WHAT stays open)
    function stepFromTerm(steps, term, ch) {
        var last = steps.length ? steps[steps.length - 1] : null, s = newStep({ what: last ? { k: 'step', ref: last.id } : null });
        if (ch) pickChoice(s, choiceItem(choiceOf(ch)) || ch);
        else if (term && term.colour && term.colour.hex) { s.act = 'recolour'; s.colour = { name: String(term.id).replace(/^colour:/, ''), hex: term.colour.hex, at: 0, qual: null, exact: false }; }
        else if (term && /^part:/.test(term.id)) { s.what = { k: 'part', part: String((term.part && (term.part.name || term.part)) || term.title).toLowerCase() }; }
        else if (term && (term.id === 'colour' || (term.flow && term.flow.name === 'colour'))) { s.act = 'recolour'; s.what = null; }
        else if (term && term.choices && term.choices.length) { s.termChoices = term.id; s.note = 'Pick a ' + term.title + ' look below.'; }
        if (!s.what) s.note = s.note || 'Pick WHAT it goes on.';
        return s;
    }

    // HELPER_V2: a compound card ("Candy red") -> recolour step + finish step on its result (WHAT = the last step's result, else open)
    function compoundSteps(steps, comp) {
        var last = steps.length ? steps[steps.length - 1] : null, hx = colourHex(comp.colour), E = Ed();
        var s1 = newStep({ what: last ? { k: 'step', ref: last.id } : null, act: 'recolour', colour: { name: comp.colour, hex: hx, at: 0, qual: null, exact: false } });
        var lk = null; try { lk = /holo/.test(comp.look) ? HOLO : (E && E.lookFor ? E.lookFor(comp.look) : null); } catch (e) { lk = null; }
        var s2 = newStep({ what: { k: 'step', ref: s1.id } }); if (lk && lk.found) { s2.finish = finishOfLook(lk); s2.act = actFor(s2.finish, null); } else { s2.act = 'finish'; s2.search = comp.look; }
        if (!s1.what) s1.note = 'Pick WHAT becomes ' + comp.colour + ' ' + comp.look + '.';
        return [s1, s2];
    }
    // ================================================================== UI (browser only)
    var S = { steps: [], text: '', flags: [], edit: null, term: null, termPin: false, msg: '', ran: null, typed: null, box: null, search: {}, mini: true, liveText: '' };
    var HAS_DOM = typeof document !== 'undefined' && !!document.createElement && typeof document.querySelector === 'function';
    function bridge() { return W.__spbOB || null; }
    function envNow() {
        var B = bridge(); if (B && B.env) { try { return B.env(); } catch (e) {} }
        var env = { palette: [], layers: [], zoneColours: [] };
        try { var Z = W.SpbProZone; if (Z && Z.paintColours) env.palette = Z.paintColours(18); } catch (e1) {}
        try { if (typeof W._psdLayers !== 'undefined' && W._psdLayers) env.layers = W._psdLayers.filter(function (l) { return l && l.img; }).map(function (l) { return { name: l.name, hidden: l.visible === false ? true : undefined }; }); } catch (e2) {}
        return env;
    }
    function configured() { var B = bridge(); try { if (B && B.configured) return !!B.configured(); } catch (e) {} try { return !!((W.SpbAI && W.SpbAI.cached && W.SpbAI.cached()) || {}).configured; } catch (e2) { return false; } }
    function offlineMode() { var off = true; try { off = W.localStorage.getItem('spb_pro_ai_offline_first') !== '0'; } catch (e) {} return !configured() || off; }
    function panel() { return HAS_DOM ? document.getElementById('spbProAI') : null; }
    function dock() {
        var p = panel(); if (!p) return null;
        var d = p.querySelector('.spb-ob'); if (d) return d;
        var bar = p.querySelector('.spb-pai-bar'); if (!bar) return null;
        d = document.createElement('div'); d.className = 'spb-ob'; bar.parentNode.insertBefore(d, bar);
        d.addEventListener('click', onClick); d.addEventListener('input', onInput); d.addEventListener('change', onChange);
        d.addEventListener('mouseover', onHover); d.addEventListener('mouseout', onOut); d.addEventListener('keydown', function (ev) { ev.stopPropagation(); });
        return d;
    }
    function stepById(id) { return S.steps.filter(function (s) { return s.id === id; })[0] || null; }
    function draw() {
        var d = dock(); if (!d) return;
        var on = offlineMode(); d.hidden = !on; if (!on) return;
        var h = '';
        if (S.browse) h += browseHtml(); else if (S.term) h += termCardHtml(termById(S.term));
        else if (S.answer && W.SpbOfflineAnswer && W.SpbOfflineAnswer.cardHtml) h += W.SpbOfflineAnswer.cardHtml(S.answer);          // HELPER_V2: a question answered offline
        if (S.steps.length) h += builderHtml();
        else h += '<div class="spb-ob-mini"><button type="button" class="spb-pai-act" data-ob="start" title="Build the change by clicking: what, do what, which look">🧱 Build it step by step</button>' + (S.liveText && S.flags.length ? '<button type="button" class="spb-pai-act" data-ob="fromlive" title="Turn what you typed into builder steps (nothing changes until Run)">Put this in the builder</button>' : '<span class="spb-ob-hint">or type below: words I know light up</span>') + '<button type="button" class="spb-pai-act" data-ob="browse" title="Browse everything about SPB">📖 Encyclopedia</button></div>';
        if (S.liveText) h += '<div class="spb-ob-flags" title="Words I know are highlighted: click one">' + flagHtml(S.liveText, S.flags) + '</div>';
        if (S.box) h = boxHtml() + h;   // box editor on top of the dock so the drag area is always in view
        d.innerHTML = h;
        if (S.box) { initBox(d); d.scrollTop = 0; }
        // HELPER_V2 2026-10-04: a NEW sentence's steps / answer / term start at the top of the dock (it kept the old scroll, so the
        // seafoam ask-first chips were drawn above the fold while the buyer looked at the previous look grid)
        else if (S._top0 !== S.steps || S._top1 !== S.answer || S._top2 !== S.term) { d.scrollTop = 0; }
        S._top0 = S.steps; S._top1 = S.answer; S._top2 = S.term;
    }
    function builderHtml() {
        var h = '<div class="spb-ob-card"><div class="spb-ob-hd"><b>🧱 Step builder</b><i>built-in, no AI · every click is exact</i><button type="button" class="spb-ob-x" data-ob="browse" title="Browse the encyclopedia">📖</button><button type="button" class="spb-ob-x" data-ob="close" title="Close the builder (nothing is changed)">×</button></div>';
        if (S.text) h += '<div class="spb-ob-said"><span>You typed:</span> ' + flagHtml(S.text, S.textFlags) + '</div>';
        h += '<div class="spb-ob-read"><span>' + (S.ran ? '✓ Done:' : 'I read this as:') + '</span> ' + esc(readAs(S.steps)) + '</div>';
        if (!S.ran) {
            h += '<div class="spb-ob-steps">' + S.steps.map(function (st, i) { return stepHtml(st, i); }).join('') + '</div>';
            var pl = toPlan(S.steps), why = pl.ok ? '' : pl.problems[0], blocked = S.steps.filter(function (s) { return s.ask; })[0];
            h += '<div class="spb-ob-foot"><button type="button" class="spb-pai-act" data-ob="add">+ Add another step</button><span class="spb-ob-sp"></span>' +
                '<button type="button" class="spb-pai-act hot spb-ob-run" data-ob="run"' + (pl.ok && !blocked ? '' : ' disabled') + ' title="' + esc(pl.ok ? (blocked ? blocked.ask : 'Do these steps on the car (one Undo takes them all back)') : why) + '">▶ Run</button></div>';
            if (!pl.ok || blocked || S.msg) h += '<div class="spb-ob-msg">' + esc(S.msg || (pl.ok ? blocked.ask : 'To run: ' + why + '.')) + '</div>';
        } else {
            h += '<div class="spb-ob-foot"><button type="button" class="spb-pai-act" data-ob="undo" title="Put the car back the way it was before Run">↶ Undo</button><button type="button" class="spb-pai-act" data-ob="reedit">Edit the steps</button><span class="spb-ob-sp"></span><button type="button" class="spb-pai-act" data-ob="new">New</button></div>';
            if (S.msg) h += '<div class="spb-ob-msg">' + esc(S.msg) + '</div>';
        }
        if (S.text && !S.ran) h += '<div class="spb-ob-alt">' + (configured() ? '<button type="button" class="spb-pai-act" data-ob="askai" title="Send what you typed to ' + esc(gearName()) + ' (online, free chat)">✨ Ask ' + esc(gearName()) + ' instead</button>' : '<button type="button" class="spb-pai-act" data-ob="gear" title="Online mode needs an OpenRouter key (⚙)">✨ Ask DeepSeek instead (add a key in ⚙)</button>') + '</div>';
        return h + '</div>';
    }
    function gearName() { try { var m = ((W.SpbAI && W.SpbAI.cached && W.SpbAI.cached()) || {}).model; return /deepseek/i.test(String(m || '')) || !m ? 'DeepSeek' : String(m).replace(/^.*\//, ''); } catch (e) { return 'DeepSeek'; } }
    function stepHtml(st, i) {
        var open = stepOpen(st), ed = S.edit === st.id || (open && S.edit == null), env = ed ? envNow() : null;
        var h = '<div class="spb-ob-step' + (open ? ' open' : '') + (ed ? ' editing' : '') + '" data-sid="' + st.id + '"><div class="spb-ob-sh"><b class="spb-ob-n">' + num(i) + '</b><span class="spb-ob-sum">' + esc(stepText(st, S.steps, false)) + '</span>' +
            (ed ? '' : '<button type="button" class="spb-ob-mini-b" data-ob="edit" data-sid="' + st.id + '">Edit</button>') + '<button type="button" class="spb-ob-mini-b" data-ob="del" data-sid="' + st.id + '" title="Remove this step">✕</button></div>';
        if (st.note || st.ask) h += '<div class="spb-ob-note' + (st.prefilled && !st.ask ? ' info' : '') + '">' + (st.prefilled && !st.ask ? 'ℹ ' : '⚠ ') + esc(st.ask || st.note) + '</div>';
        if (st.ask && st.chips && st.chips.some(function (c) { return c && c.hid; })) h += '<div class="spb-ob-row spb-ob-hchips">' + st.chips.map(function (c, k) { return c && c.hid ? '<button type="button" class="spb-pai-act' + (k ? '' : ' hot') + '" data-ob="hchip" data-sid="' + st.id + '" data-k="' + k + '">' + (c.hex ? '<i class="spb-ob-sw" style="background:' + esc(c.hex) + '"></i>' : '') + esc(c.label) + '</button>' : ''; }).join('') + '</div>';          // HELPER_V2: ask-first chips
        if (!ed) return h + '</div>';
        // 1 WHAT
        var wc = whatChoices(env, S.steps, st), grp = '';
        // HELPER_V2 2026-10-04 owner: keep improving the Offline Helper. Once WHAT and DO are both chosen, WHAT folds to the chosen chip + "Change":
        // on a car with 13 layers the full WHAT list pushed the looks (the part the buyer still has to pick) below the fold.
        var fold = st.what && st.act && !st.whatOpen && wc.some(function (c) { return c.what && whatSame(st.what, c.what); });
        h += '<div class="spb-ob-q"><b>1</b> What</div><div class="spb-ob-row">';
        if (fold) wc.forEach(function (c, k) { if (c.what && whatSame(st.what, c.what) && !fold.done) { fold = { done: true }; h += '<button type="button" class="spb-ob-chip on" data-ob="what" data-sid="' + st.id + '" data-k="' + k + '">' + (c.hex ? '<i class="spb-ob-sw" style="background:' + esc(c.hex) + '"></i>' : '') + esc(c.label) + (c.sub ? ' <em>' + esc(c.sub) + '</em>' : '') + '</button><button type="button" class="spb-ob-link" data-ob="whatopen" data-sid="' + st.id + '">Change…</button>'; } });
        else wc.forEach(function (c, k) {
            if (c.grp !== grp) { grp = c.grp; h += '<span class="spb-ob-grp">' + esc(grp) + '</span>'; }
            var sel = st.what && c.what && whatSame(st.what, c.what);
            h += '<button type="button" class="spb-ob-chip' + (sel ? ' on' : '') + '" data-ob="' + (c.box ? 'boxstart' : 'what') + '" data-sid="' + st.id + '" data-k="' + k + '">' + (c.hex ? '<i class="spb-ob-sw" style="background:' + esc(c.hex) + '"></i>' : '') + esc(c.label) + (c.sub ? ' <em>' + esc(c.sub) + '</em>' : '') + '</button>';
        });
        h += '</div>';
        if (st.what && (st.what.k === 'colour' || (st.what.k === 'box' && st.what.tg))) h += whereHtml(st, env);
        // 2 DO WHAT
        h += '<div class="spb-ob-q"><b>2</b> Do what</div><div class="spb-ob-row">' + [['recolour', 'Recolour'], ['finish', 'Add finish'], ['pattern', 'Add pattern / texture'], ['shine', 'Change shine only']].map(function (a) { return '<button type="button" class="spb-ob-chip act' + (st.act === a[0] ? ' on' : '') + '" data-ob="act" data-sid="' + st.id + '" data-act="' + a[0] + '">' + a[1] + '</button>'; }).join('') + '</div>';
        // 3 WHICH LOOK
        if (st.act || st.termChoices) {
            var q = S.search[st.id] != null ? S.search[st.id] : (st.search || ''), lc = lookChoices(st), extra = q && st.act !== 'recolour' ? searchChoices(q, st.act === 'pattern' ? ['pattern'] : (st.act === 'shine' ? ['spec', 'finish'] : ['finish'])).map(choiceItem).filter(Boolean) : [];
            extra.forEach(function (c) { c.thumb = thumbFor(c, c.hex || effHex(st)); c.grp = 'Search: ' + q; });
            var all = extra.concat(lc); st._choices = all; grp = null;
            h += '<div class="spb-ob-q"><b>3</b> Which look</div>';
            if (st.act !== 'recolour') h += '<input class="spb-ob-search" data-ob-search="' + st.id + '" placeholder="Search looks (e.g. carbon, camo, galaxy)" value="' + esc(q) + '">';
            h += '<div class="spb-ob-grid">';
            all.forEach(function (c, k) {
                var g = c.grp || (st.act === 'recolour' ? 'Colours' : (c.kind === 'tex' && st.act === 'shine' ? 'Texture in the shine (optional)' : 'Looks')); if (g !== grp) { grp = g; h += '<span class="spb-ob-grp wide">' + esc(g) + '</span>'; }
                var sel = (c.kind === 'colour' && st.colour && st.colour.hex === c.hex) || ((c.kind === 'look' || c.kind === 'cat') && st.finish && st.finish.key === (c.key || c.id)) || (c.kind === 'tex' && st.tex && st.tex.id === c.id);
                h += '<button type="button" class="spb-ob-look' + (sel ? ' on' : '') + '" data-ob="look" data-sid="' + st.id + '" data-k="' + k + '" title="' + esc(c.label + (c.key ? ' (' + c.key + ')' : (c.id && c.kind !== 'colour' ? ' (' + c.id + ')' : ''))) + '">' +
                    (c.kind === 'colour' ? '<i class="spb-ob-big" style="background:' + esc(c.hex) + '"></i>' : (c.thumb ? '<img loading="lazy" alt="" src="' + esc(c.thumb) + '" onerror="this.style.visibility=\'hidden\'">' : '<i class="spb-ob-big"></i>')) + '<span>' + esc(cap(c.label)) + '</span></button>';
            });
            if (st.act === 'recolour') h += '<label class="spb-ob-look spb-ob-exact" title="Any exact colour"><input type="color" data-ob-colour="' + st.id + '" value="#' + hex6(st.colour && st.colour.exact ? st.colour.hex : '#ff7eb6') + '"><span>Exact colour…</span></label>';
            h += '</div>';
        }
        h += '<div class="spb-ob-row end"><button type="button" class="spb-pai-act" data-ob="done" data-sid="' + st.id + '">Done with step ' + num(i) + '</button></div>';
        return h + '</div>';
    }
    function whatSame(a, b) {
        if (!a || !b || a.k !== b.k) return false;
        if (a.k === 'colour') return String(a.tg.hex).toLowerCase() === String(b.tg.hex).toLowerCase() || a.tg.word === b.tg.word;
        if (a.k === 'part') return a.part === b.part; if (a.k === 'layer') return (a.layers || [])[0] === (b.layers || [])[0]; if (a.k === 'step') return a.ref === b.ref;
        return true;
    }
    // a colour target: WHERE (default = the body paint only: the copilot keeps logos / numbers; or exactly the layers the buyer ticks)
    function whereHtml(st, env) {
        var tg = st.what.tg, ls = (((env || {}).layers) || []).filter(function (l) { return !l.hidden && !/^\s*(wire|mask|car[ _]*mandatory|template|guides?)\b/i.test(String(l.name || '')); }), sel = tg.layers || [];
        var auto = !sel.length;
        var h = '<div class="spb-ob-where"><span>Where:</span> <button type="button" class="spb-ob-chip' + (auto ? ' on' : '') + '" data-ob="whereauto" data-sid="' + st.id + '" title="The colour on the body paint; your logos and numbers keep theirs">' + (tg.artObjects && tg.artObjects.length ? 'Body paint + art you named' : 'Body paint (automatic)') + '</button>';
        ls.slice(0, 12).forEach(function (l, k) { h += '<button type="button" class="spb-ob-chip' + (sel.indexOf(l.name) !== -1 ? ' on' : '') + '" data-ob="wherelayer" data-sid="' + st.id + '" data-layer="' + esc(l.name) + '" title="' + esc(l.role || '') + '">' + (sel.indexOf(l.name) !== -1 ? '☑ ' : '☐ ') + esc(l.name) + '</button>'; });
        return h + '</div>';
    }
    // ---- the encyclopedia card = an ARTICLE view (v2 sections when data/encyclopedia/<domain>.json has it; the index entry otherwise)
    function openTerm(id, pin) {
        S.term = id; S.termPin = !!pin; S.linkOut = ''; S.browse = null;
        var want = id; S.article = null;
        SpbEnc.article(id).then(function (a) { if (S.term === want) { S.article = a; draw(); } });
    }
    function cardShot(A) {
        var R = W.SpbEncyclopedia, L = []; try { L = (R && R.screens) ? R.screens() : []; } catch (e) { L = []; } if (!L.length || !A) return null;
        var ids = (A.screens || []).slice(), aid = A.artId || A.id; L.forEach(function (x) { if ((x.article_ids || []).indexOf(aid) !== -1 && ids.indexOf(x.id) === -1) ids.push(x.id); });
        for (var i = 0; i < ids.length; i++) { var x = L.filter(function (s) { return s.id === ids[i]; })[0]; if (x && x.file) return { src: /^(\/|https?:|data:)/.test(x.file) ? x.file : 'data/encyclopedia/' + x.file, caption: x.caption || x.title || '' }; }
        return null;
    }
    function actionChoice(a) { if (!a) return null; if (a.choice) return a.choice; if (a.finish_id || a.pattern_id || a.spec_id) return a; if (a.do === 'finish') return { finish_id: a.id, label: a.label || a.id }; if (a.do === 'pattern') return { pattern_id: a.id, label: a.label || a.id }; if (a.do === 'spec') return { spec_id: a.id, label: a.label || a.id }; return null; }
    function termCardHtml(t) {
        if (!t) return '';
        var A = (S.article && S.article.id === t.id) ? S.article : articleFromTerm(t), hx = t.colour && t.colour.hex ? t.colour.hex : null;
        var h = '<div class="spb-ob-tcard k-' + esc(t.kind) + '"><div class="spb-ob-hd"><b>' + esc(A.title || t.title) + '</b><i>' + esc(A.domain) + ' · ' + esc(t.kind === 'info' ? 'good to know' : (t.kind === 'action' ? 'a look you can apply' : 'I can walk you through it')) + '</i><button type="button" class="spb-ob-x" data-ob="browse" title="Browse the encyclopedia">📖</button><button type="button" class="spb-ob-x" data-ob="tclose">×</button></div><div class="spb-ob-art">';
        if (W.SpbEncyclopedia) h += '<div class="spb-ob-row"><button type="button" class="spb-ob-link" data-ob="tread" data-term="' + esc(t.id) + '" title="Open the full SPB Encyclopedia at this topic">📖 Read the full article ›</button></div>';
        h += '<div class="spb-ob-tsum">' + (A.level ? '<span class="spb-oa-lvl l-' + esc(A.level) + '">' + esc(A.level) + '</span> ' : '') + esc(A.summary || '') + '</div>';
        // HELPER_V2 2026-10-04: the v3 depth on the card: level badge, the first REAL screenshot, the top FAQ (the full article is one click away)
        var shot = cardShot(A); if (shot) h += '<button type="button" class="spb-oa-shot" data-ob="tread" data-term="' + esc(t.id) + '" title="' + esc(shot.caption) + '"><img loading="lazy" alt="' + esc(shot.caption) + '" src="' + esc(shot.src) + '" onerror="this.parentNode.style.display=\'none\'"><span>' + esc(String(shot.caption).slice(0, 90)) + '</span></button>';
        var fq0 = (A.faq || [])[0]; if (fq0 && fq0.q) h += '<div class="spb-ob-sec spb-oa-faq"><b>' + esc(fq0.q) + '</b><p>' + esc(fq0.a || '') + '</p></div>';
        if (t.compound) h += '<div class="spb-ob-row"><button type="button" class="spb-pai-act hot" data-ob="tcompound" data-term="' + esc(t.id) + '">' + (t.colour ? '<i class="spb-ob-sw" style="background:' + esc(t.colour.hex) + '"></i> ' : '') + 'Do it: ' + esc(t.title) + ' (2 steps)</button></div>';
        if (A.what) h +='<div class="spb-ob-sec"><b>What it is</b><p>' + esc(A.what) + '</p></div>';
        [['when', 'When to use it'], ['how', 'How'], ['tips', 'Tips'], ['pitfalls', 'Watch out']].forEach(function (sx) { var L = A[sx[0]] || []; if (L.length) h += '<div class="spb-ob-sec"><b>' + sx[1] + '</b>' + (sx[0] === 'how' ? '<ol>' : '<ul>') + L.slice(0, 8).map(function (x) { return '<li>' + esc(typeof x === 'string' ? x : (x.text || x.label || '')) + '</li>'; }).join('') + (sx[0] === 'how' ? '</ol>' : '</ul>') + '</div>'; });
        if ((A.controls || []).length) h += '<div class="spb-ob-sec"><b>Controls</b><table class="spb-ob-ctl">' + A.controls.slice(0, 10).map(function (c) { return '<tr><td>' + esc(c.label) + '</td><td>' + esc([c.range, c.default != null ? 'default ' + c.default : ''].filter(Boolean).join(', ')) + '</td><td>' + esc(c.effect || '') + '</td></tr>'; }).join('') + '</table></div>';
        if (t.colour && t.colour.hex) h += '<div class="spb-ob-row"><button type="button" class="spb-pai-act hot" data-ob="tcolour" data-term="' + esc(t.id) + '"><i class="spb-ob-sw" style="background:' + esc(t.colour.hex) + '"></i> Use ' + esc(t.title) + ' as the new colour</button></div>';
        var acts = (A.actions || []).map(function (a) { return { a: a, ci: choiceItem(choiceOf(actionChoice(a))) }; }).filter(function (x) { return x.ci; });
        if (acts.length) {
            h += '<div class="spb-ob-q">' + esc(S.steps.length ? 'Do it: add a ' + t.title + ' step (on the result of the last step)?' : 'Do it: apply a ' + t.title + ' look to the car?') + '</div><div class="spb-ob-grid">';
            acts.slice(0, 8).forEach(function (x, k) { var c = actionChoice(x.a); h += '<button type="button" class="spb-ob-look" data-ob="tchoice" data-term="' + esc(t.id) + '" data-k="' + k + '" title="' + esc(x.a.label || c.label) + '"><img loading="lazy" alt="" src="' + esc(thumbFor(x.ci, c.hex || hx)) + '" onerror="this.style.visibility=\'hidden\'"><span>' + esc(x.a.label || c.label) + '</span></button>'; });
            h += '</div>';
        }
        if (t.kind === 'flow' && canStart(t)) h += '<div class="spb-ob-row"><button type="button" class="spb-pai-act hot" data-ob="tflow" data-term="' + esc(t.id) + '">' + esc(flowLabel(t)) + '</button></div>';
        if ((A.links || []).length) h += '<div class="spb-ob-links">' + A.links.slice(0, 5).map(function (l, k) { return '<button type="button" class="spb-ob-link" data-ob="tlink" data-term="' + esc(t.id) + '" data-k="' + k + '">' + esc(l.label) + ' ›</button>'; }).join('') + '</div>';
        if (S.linkOut) h += '<div class="spb-ob-lout">' + S.linkOut + '</div>';
        var rel = (A.related || []).map(function (r) { return termById(r); }).filter(Boolean);
        if (rel.length) h += '<div class="spb-ob-sec"><b>Related</b><div class="spb-ob-row">' + rel.slice(0, 8).map(function (r) { return '<button type="button" class="spb-ob-link" data-ob="tgo" data-term="' + esc(r.id) + '">' + esc(r.title) + '</button>'; }).join('') + '</div></div>';
        if ((A.sources || []).length) h += '<div class="spb-ob-meta">Sources: ' + A.sources.slice(0, 4).map(function (s) { return esc(typeof s === 'string' ? s : (s.label || s.target || '')); }).join(', ') + '</div>';
        return h + '</div></div>';
    }
    // ---- BROWSE: topics A-Z or by domain + search (renders from the index now; v2 articles open in the same card)
    function browseHtml() {
        var B0 = S.browse, q = String(B0.q || '').toLowerCase().trim(), all = SpbEnc.terms().filter(function (t) { return (t.tier || 3) <= (q ? 3 : 2); }), rows;
        if (q) { var ws = q.split(/\s+/); rows = all.filter(function (t) { var hay = (t.title + ' ' + (t.aliases || []).join(' ') + ' ' + (t.summary || '')).toLowerCase(); return ws.every(function (w) { return hay.indexOf(w) !== -1; }); }); }
        else rows = all;
        var h = '<div class="spb-ob-tcard"><div class="spb-ob-hd"><b>📖 Encyclopedia</b><i>' + SpbEnc.terms().length + ' topics · everything about SPB</i><button type="button" class="spb-ob-x" data-ob="bclose">×</button></div>';
        h += '<div class="spb-ob-row"><input class="spb-ob-search" data-ob-bsearch="1" placeholder="Search: holographic, user id, spec map, zones…" value="' + esc(B0.q || '') + '"></div>';
        h += '<div class="spb-ob-row">' + ['az', 'domain'].map(function (m) { return '<button type="button" class="spb-ob-chip' + (B0.by === m ? ' on' : '') + '" data-ob="bby" data-by="' + m + '">' + (m === 'az' ? 'A–Z' : 'By topic') + '</button>'; }).join('') + '</div><div class="spb-ob-blist">';
        var groups = {}; rows.forEach(function (t) { var g = B0.by === 'domain' ? domainOf(t) : String(t.title || '?').charAt(0).toUpperCase(); (groups[g] = groups[g] || []).push(t); });
        Object.keys(groups).sort().forEach(function (g) { var L = groups[g].sort(function (a, b) { return String(a.title).localeCompare(String(b.title)); }); h += '<div class="spb-ob-bgrp"><b>' + esc(g) + '</b> ' + L.slice(0, q ? 40 : 60).map(function (t) { return '<button type="button" class="spb-ob-link" data-ob="tgo" data-term="' + esc(t.id) + '" title="' + esc(t.summary || '') + '">' + esc(t.title) + '</button>'; }).join('') + '</div>'; });
        if (!rows.length) h += '<div class="spb-ob-meta">No topic matches “' + esc(B0.q) + '”.</div>';
        return h + '</div></div>';
    }
    function canStart(t) { return t.id === 'colour' || /^part:/.test(t.id) || (t.flow && /^(colour|paint_part|finish|pattern|spec)$/.test(t.flow.name || '')) || /^(finish|pattern|spec)$/.test(t.id); }
    function flowLabel(t) { if (t.id === 'colour' || (t.flow && t.flow.name === 'colour')) return 'Start: change a colour'; if (/^part:/.test(t.id)) return 'Start a step on the ' + t.title.toLowerCase(); return 'Start a ' + t.title.toLowerCase() + ' step'; }
    function mdHtml(s) { return esc(String(s || '')).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>'); }
    function linkOut(l) {
        var tg = String(l.target || ''), m = /^(support|help|control|doc):(.*)$/.exec(tg); if (!m) return null;
        if (m[1] === 'support') { var SP = W.SpbSupport, f = SP ? (SP.FAQS || []).concat(SP.ERRS || []).filter(function (x) { return x.id === m[2]; })[0] : null; var a = f ? (typeof f.answer === 'function' ? '' : f.answer) : ''; return a ? mdHtml(a) : 'Ask me: “' + esc(l.label) + '”.'; }
        if (m[1] === 'help') { var SH = W.SpbSelfHelp, tp = SH ? (SH.TOPICS || []).filter(function (x) { return x.id === m[2]; })[0] : null; return tp ? '<b>' + esc(tp.title) + '</b><ol>' + (tp.steps || []).map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>' : esc(l.label); }
        if (m[1] === 'control') { var el = HAS_DOM ? document.getElementById(m[2]) : null; if (el) { try { el.scrollIntoView({ block: 'center' }); el.classList.add('spb-ob-flash'); setTimeout(function () { el.classList.remove('spb-ob-flash'); }, 2600); } catch (e) {} return 'It is highlighted in the app now: <b>' + esc(l.label) + '</b>.'; } return 'Look for <b>' + esc(l.label) + '</b> in the app.'; }
        if (m[1] === 'doc') { try { W.open(m[2].replace(/#(.*)$/, function (x, hd) { return '#' + encodeURIComponent(hd); }), '_blank'); } catch (e2) {} return 'Opened the guide: <b>' + esc(l.label) + '</b>.'; }
        return null;
    }
    // ---- the box editor: drag a rectangle on the paint (0-1 fractions); then "only the <colour> inside" or everything inside
    function boxHtml() {
        var b = S.box, r = b.rect, a = r ? Math.abs(r.x1 - r.x0) * Math.abs(r.y1 - r.y0) : 0;
        var h = '<div class="spb-ob-box"><div class="spb-ob-hd"><b>▭ Box-select an area</b><i>drag a box around the thing (e.g. the spray can)</i><button type="button" class="spb-ob-x" data-ob="boxcancel">×</button></div><div class="spb-ob-boxwrap"><canvas class="spb-ob-boxcv"></canvas></div>';
        if (r) {
            h += '<div class="spb-ob-meta">' + Math.round(a * 1000) / 10 + '% of the sheet' + (a > 0.12 ? ' — too big: a box over 12% cuts across panels. Draw it tighter.' : '') + '</div>';
            if (a <= 0.12) { h += '<div class="spb-ob-row"><span class="spb-ob-grp">Inside the box, change:</span>' + (b.cols || []).map(function (c, k) { return '<button type="button" class="spb-ob-chip" data-ob="boxuse" data-k="' + k + '"><i class="spb-ob-sw" style="background:' + esc(c.hex) + '"></i>only the ' + esc(c.name) + ' <em>' + c.pct + '%</em></button>'; }).join('') + '<button type="button" class="spb-ob-chip" data-ob="boxuse" data-k="-1">everything in the box</button></div>'; }
        } else h += '<div class="spb-ob-meta">Drag on the picture.</div>';
        return h + '</div>';
    }
    function initBox(d) {
        var cv = d.querySelector('.spb-ob-boxcv'), src = document.getElementById('paintCanvas'); if (!cv) return;
        var Wd = Math.min(360, (d.clientWidth || 360) - 20); cv.width = Wd; cv.height = Wd; var cx = cv.getContext('2d');
        function paint() { cx.fillStyle = '#111'; cx.fillRect(0, 0, Wd, Wd); if (src) { try { cx.drawImage(src, 0, 0, Wd, Wd); } catch (e) {} } var r = S.box.rect; if (r) { cx.fillStyle = 'rgba(255,43,214,0.18)'; cx.strokeStyle = '#ff2bd6'; cx.lineWidth = 2; cx.fillRect(r.x0 * Wd, r.y0 * Wd, (r.x1 - r.x0) * Wd, (r.y1 - r.y0) * Wd); cx.strokeRect(r.x0 * Wd, r.y0 * Wd, (r.x1 - r.x0) * Wd, (r.y1 - r.y0) * Wd); } }
        paint();
        var down = null;
        function at(ev) { var bb = cv.getBoundingClientRect(); return { x: Math.max(0, Math.min(1, (ev.clientX - bb.left) / bb.width)), y: Math.max(0, Math.min(1, (ev.clientY - bb.top) / bb.height)) }; }
        cv.addEventListener('mousedown', function (ev) { down = at(ev); ev.preventDefault(); });
        cv.addEventListener('mousemove', function (ev) { if (!down) return; var p = at(ev); S.box.rect = { x0: Math.min(down.x, p.x), y0: Math.min(down.y, p.y), x1: Math.max(down.x, p.x), y1: Math.max(down.y, p.y) }; paint(); });
        cv.addEventListener('mouseup', function () { if (!down) return; down = null; var r = S.box.rect; if (!r || (r.x1 - r.x0) < 0.004 || (r.y1 - r.y0) < 0.004) { S.box.rect = null; draw(); return; } S.box.cols = boxColours(r); draw(); });
    }
    // the art layer the box is drawn around: the non-base layer holding the most of that colour inside the box (OFFLINE_BUILDER: box the can = recolour the CAN, not the body paint around it)
    function boxLayerFor(r, hex) {
        var Z = HAS_DOM && W.SpbProZone, env = envNow(), best = null, bs = 0; if (!Z || !Z.probeRegion || !r) return null;
        (((env || {}).layers) || []).forEach(function (l) {
            var nm = String(l.name || ''); if (l.hidden || /\bbase\b|^\s*(wire|mask|car[ _]*mandatory|template|guides?)\b/i.test(nm)) return;
            var p = null; try { p = Z.probeRegion({ colors: [hex], layers: [nm], rect: { x0: r.x0, y0: r.y0, x1: r.x1, y1: r.y1 } }); } catch (e) { p = null; }
            var sh = p && p.share_pct || 0; if (sh > bs) { bs = sh; best = nm; }
        });
        return bs >= 0.05 ? best : null;
    }
    // the car's colours inside the box (picture pixels, nearest palette colour)
    function boxColours(r) {
        var out = [], src = HAS_DOM ? document.getElementById('paintCanvas') : null, pal = palOf(envNow()).slice(0, 12); if (!src || !pal.length) return out;
        try {
            var n = 96, cv = document.createElement('canvas'); cv.width = n; cv.height = n; var cx = cv.getContext('2d'); var sw = src.width, sh = src.height;
            cx.drawImage(src, r.x0 * sw, r.y0 * sh, Math.max(1, (r.x1 - r.x0) * sw), Math.max(1, (r.y1 - r.y0) * sh), 0, 0, n, n);
            var d = cx.getImageData(0, 0, n, n).data, cnt = {}, tot = 0, i;
            var rgb = pal.map(function (p) { var h = hex6(p.hex); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; });
            for (i = 0; i < n * n; i++) { if (d[i * 4 + 3] < 8) continue; var best = -1, bd = 1e9; for (var k = 0; k < rgb.length; k++) { var dr = d[i * 4] - rgb[k][0], dg = d[i * 4 + 1] - rgb[k][1], db = d[i * 4 + 2] - rgb[k][2], dd = dr * dr + dg * dg + db * db; if (dd < bd) { bd = dd; best = k; } } if (best >= 0 && bd < 60 * 60) { cnt[best] = (cnt[best] || 0) + 1; } tot++; }
            Object.keys(cnt).forEach(function (k) { var pct = Math.round(cnt[k] / Math.max(1, tot) * 100); if (pct >= 3) out.push({ name: pal[k].name, hex: pal[k].hex, pct: pct }); });
            out.sort(function (a, b) { return b.pct - a.pct; });
        } catch (e) {}
        return out.slice(0, 4);
    }
    // ---- events
    function onClick(ev) {
        var b = ev.target && ev.target.closest ? ev.target.closest('[data-ob]') : null; if (!b) return;
        var a = b.getAttribute('data-ob'), sid = b.getAttribute('data-sid'), st = sid ? stepById(sid) : null, k = Number(b.getAttribute('data-k'));
        ev.preventDefault(); S.msg = '';
        if (/^a(close|enc|read|doit)$/.test(a) && W.SpbOfflineAnswer && W.SpbOfflineAnswer.onAction && W.SpbOfflineAnswer.onAction(a, b, S)) { draw(); return; }          // HELPER_V2 answer card
        if (a === 'hchip' && st) { hiddenPick(st, (st.chips || [])[k]); recheck(); draw(); return; }
        if (a === 'whatopen' && st) { st.whatOpen = true; draw(); return; }          // HELPER_V2: unfold the WHAT list
        if (a === 'tcompound') { var tc = termById(b.getAttribute('data-term')); if (tc && tc.compound) { var cs = compoundSteps(S.steps, tc.compound); cs.forEach(function (x) { S.steps.push(x); }); S.edit = cs[0].what ? null : cs[0].id; S.term = null; S.ran = null; recheck(); } draw(); return; }
        if (a === 'term' || a === 'tgo') openTerm(b.getAttribute('data-term'), true);
        else if (a === 'tclose') { S.term = null; S.termPin = false; S.linkOut = ''; S.article = null; }
        else if (a === 'browse') { if (W.SpbEncyclopedia && W.SpbEncyclopedia.open) { W.SpbEncyclopedia.open(); return; } S.browse = { by: 'az', q: '' }; S.term = null; }
        else if (a === 'tread') { if (W.SpbEncyclopedia) W.SpbEncyclopedia.open(b.getAttribute('data-term')); return; }
        else if (a === 'bclose') S.browse = null;
        else if (a === 'bby') S.browse.by = b.getAttribute('data-by');
        else if (a === 'tlink') { var t0 = termById(b.getAttribute('data-term')), A0 = (S.article && S.article.id === t0.id) ? S.article : articleFromTerm(t0); S.linkOut = linkOut((A0.links || [])[k]) || ''; }
        else if (a === 'tchoice') { var t1 = termById(b.getAttribute('data-term')), A1 = (S.article && S.article.id === t1.id) ? S.article : articleFromTerm(t1), acts1 = (A1.actions || []).filter(function (x) { return choiceItem(choiceOf(actionChoice(x))); }); var s1 = stepFromTerm(S.steps, t1, actionChoice(acts1[k])); S.steps.push(s1); S.edit = s1.what ? null : s1.id; S.term = null; S.ran = null; if (!s1.what && !S.steps.slice(0, -1).length) s1.what = { k: 'body' }; recheck(); }
        else if (a === 'tcolour' || a === 'tflow') { var t2 = termById(b.getAttribute('data-term')); var open = S.steps.filter(function (s) { return s.act === 'recolour' && !s.colour; })[0]; if (a === 'tcolour' && open) { open.colour = { name: t2.id.replace(/^colour:/, ''), hex: t2.colour.hex, at: 0, qual: null, exact: false }; } else { var s2 = stepFromTerm(S.steps, t2, null); if (a === 'tflow' && (t2.id === 'colour' || /^part:/.test(t2.id))) { if (t2.id === 'colour') s2.what = null; } S.steps.push(s2); S.edit = s2.id; } S.term = null; S.ran = null; recheck(); }
        else if (a === 'start') { S.answer = null; S.steps = [newStep()]; S.edit = S.steps[0].id; S.text = ''; S.ran = null; }
        else if (a === 'fromlive') { var fr = fromText(S.liveText, envNow()); S.steps = fr.steps; S.text = S.liveText; S.textFlags = flag(S.text); S.ran = null; S.edit = null; recheck(); }
        else if (a === 'close' || a === 'new') { S.steps = []; S.text = ''; S.ran = null; S.edit = null; }
        else if (a === 'add') { var last = S.steps[S.steps.length - 1]; var s3 = newStep({ what: last ? { k: 'step', ref: last.id } : null }); S.steps.push(s3); S.edit = s3.id; }
        else if (a === 'edit' && st) S.edit = st.id;
        else if (a === 'done' && st) { S.edit = '-'; recheck(); }
        else if (a === 'del' && st) { S.steps = S.steps.filter(function (s) { return s !== st; }); S.steps.forEach(function (s) { if (s.what && s.what.k === 'step' && s.what.ref === st.id) s.what = st.what && st.what.k === 'step' ? clone(st.what) : null; }); recheck(); }
        else if (a === 'what' && st) { var wc = whatChoices(envNow(), S.steps, st)[k]; if (wc && wc.what) { st.what = clone(wc.what); st.ask = null; st.note = ''; st.whatOpen = false; } recheck(); }
        else if (a === 'boxstart' && st) { S.box = { sid: st.id, rect: null, cols: [] }; }
        else if (a === 'boxcancel') S.box = null;
        else if (a === 'boxuse') { var sb = stepById(S.box && S.box.sid); if (sb && S.box.rect) { var col = k >= 0 ? S.box.cols[k] : null; sb.what = { k: 'box', rect: clone(S.box.rect), colour: col ? { name: col.name, hex: col.hex } : null }; if (col) sb.what.tg = { kind: 'colour', word: col.name, hex: col.hex, qual: null, at: 0, parts: null }; if (col) { var bl = boxLayerFor(S.box.rect, col.hex); if (bl) { sb.what.tg.layers = [bl]; } } sb.ask = null; sb.note = (sb.what.tg && sb.what.tg.layers) ? 'Only the ' + sb.what.colour.name + ' on the ' + sb.what.tg.layers[0] + ' layer inside your box (the art you boxed). Tap “Body paint (automatic)” under Where to take the body paint in the box too.' : ''; sb.prefilled = !!sb.note; } S.box = null; recheck(); }
        else if (a === 'whereauto' && st) { delete st.what.tg.layers; recheck(); }
        else if (a === 'wherelayer' && st) { var ln = b.getAttribute('data-layer'), L = st.what.tg.layers || []; var ix = L.indexOf(ln); if (ix === -1) L.push(ln); else L.splice(ix, 1); if (L.length) { st.what.tg.layers = L; delete st.what.tg.bodyNamed; delete st.what.tg.artObjects; } else delete st.what.tg.layers; recheck(); }
        else if (a === 'act' && st) { setAct(st, b.getAttribute('data-act')); }
        else if (a === 'look' && st) { var ch = (st._choices || [])[k]; if (ch) pickChoice(st, ch); recheck(); }
        else if (a === 'run') return run();
        else if (a === 'undo') { var B = bridge(); var ok = false; try { ok = B && B.undo ? B.undo() : (W.spbProAI && W.spbProAI._undoLast ? W.spbProAI._undoLast() : false); } catch (e) {} S.msg = ok ? 'Undone: the car is back to how it was before Run.' : 'Nothing of mine to undo.'; if (ok) S.ran = null; }
        else if (a === 'reedit') { S.ran = null; S.edit = null; }
        else if (a === 'askai') return askAI();
        else if (a === 'gear') { var p = panel(), g = p && p.querySelector('[data-act="gear"]'); if (g) g.click(); }
        draw();
    }
    function onInput(ev) { var t = ev.target; if (t && t.getAttribute && t.getAttribute('data-ob-bsearch') && S.browse) { S.browse.q = t.value; clearTimeout(S._bt); S._bt = setTimeout(function () { var pos = t.selectionStart; draw(); var n = dock() && dock().querySelector('[data-ob-bsearch]'); if (n) { n.focus(); try { n.setSelectionRange(pos, pos); } catch (e) {} } }, 220); return; } if (t && t.getAttribute && t.getAttribute('data-ob-search')) { var sid = t.getAttribute('data-ob-search'); S.search[sid] = t.value; clearTimeout(S._st); S._st = setTimeout(function () { var pos = t.selectionStart; draw(); var n = dock() && dock().querySelector('[data-ob-search="' + sid + '"]'); if (n) { n.focus(); try { n.setSelectionRange(pos, pos); } catch (e) {} } }, 260); } }
    function onChange(ev) { var t = ev.target; if (t && t.getAttribute && t.getAttribute('data-ob-colour')) { var st = stepById(t.getAttribute('data-ob-colour')); if (st) { st.act = 'recolour'; st.colour = { name: t.value, hex: t.value.toLowerCase(), at: 0, qual: null, exact: true }; st.finish = null; st.tex = null; recheck(); draw(); } } }
    // OWNTURN 2026-10-04 (owner screenshot: a "Purple - a colour" card sat open over the chat after a mouse pass over the word while typing a scale + spec request):
    // a card opened by HOVER is only a peek - it closes when the pointer leaves the word / card, and on Send. A clicked card stays (pinned).
    function onHover(ev) {
        var c = ev.target && ev.target.closest ? ev.target.closest('.spb-ob-tcard') : null; if (c) { clearTimeout(S._hx); return; }
        var m = ev.target && ev.target.closest ? ev.target.closest('mark.spb-ob-term') : null; if (m) clearTimeout(S._hx); if (!m || S.termPin) return;
        clearTimeout(S._hv); S._hv = setTimeout(function () { var id = m.getAttribute('data-term'); if (S.term !== id && !S.termPin && !S.browse) { openTerm(id, false); draw(); } }, 420);
    }
    function onOut(ev) {
        var from = ev.target && ev.target.closest ? ev.target.closest('mark.spb-ob-term, .spb-ob-tcard') : null, to = ev.relatedTarget && ev.relatedTarget.closest ? ev.relatedTarget.closest('mark.spb-ob-term, .spb-ob-tcard') : null;
        if (!from || to) return; clearTimeout(S._hv); if (S.termPin || !S.term) return;
        clearTimeout(S._hx); S._hx = setTimeout(function () { if (!S.termPin && S.term) { S.term = null; S.article = null; draw(); } }, 650);
    }
    function recheck() { try { check(S.steps, envNow()); } catch (e) {} }
    // HELPER FIX PASS 7 2026-10-05 (blind5 b5-047 / b5-057: "a thin red line around the roof" and "a gradient on the door" each repainted the WHOLE car). HARD INVARIANT, enforced
    // here in code, measured: when the buyer's sentence names a part (and no whole-car / keep words), every zone the plan would make is probed with those parts cut out
    // (js/spb-pro-zone-kit.js probeRegion + exclude); anything left over above 1% of the car = the plan reaches outside the named part -> NOT run, said plainly.
    var GUARD_WHOLE_RE = /\b(?:whole|entire|everything|everywhere|all over|the car|the body|my car|rest|other parts?|except|but not|not the|apart from|other than|stays?|keep|leave|dont|don'?t|without|same on|other side|too|as well|also)\b/i;
    function scopeGuard(text, ed) {
        var OA = W.SpbOfflineAnswer, Z = W.SpbProZone, E = Ed(), t = String(text || ''); if (!OA || !OA._partsOf || !Z || !Z.probeRegion || !E || !E.compile || !ed || ed.kind !== 'ops') return null;
        if (GUARD_WHOLE_RE.test(t)) return null; var named = OA._partsOf(t); if (!named.length) return null;
        if ((ed.ops || []).some(function (o) { return o._box || (o.target && (o.target.kind === 'numbers' || o.target.kind === 'sponsors' || o.target.kind === 'layer' || o.target.kind === 'element' || o.target.kind === 'step')); })) return null;
        var cz = null; try { cz = E.compile(JSON.parse(JSON.stringify(ed)), envNow()); } catch (e) { return null; }
        var worst = 0, wz = null;
        ((cz && cz.zones) || []).forEach(function (z) {
            var rg = JSON.parse(JSON.stringify(z.region || {})); if (rg.part) { rg.island = rg.part; delete rg.part; }
            rg.exclude = (rg.exclude || []).concat(named); var pr = null; try { pr = Z.probeRegion(rg); } catch (e2) { pr = null; }
            var sh = pr && pr.share_pct != null ? Number(pr.share_pct) : 0; if (sh > worst) { worst = sh; wz = z; }
        });
        try { if (W.console && W.console.debug) W.console.debug('[spb-guard] named=' + named.join('/') + ' outside=' + worst + '%'); } catch (e3) {}
        S.guard = { named: named.slice(), outside: worst, t: Date.now() };
        if (worst <= 1) return null;
        return 'Not run: this would change about ' + Math.round(worst) + '% of the car OUTSIDE the ' + named.join(' and ') + ' (' + ((wz && wz.name) || 'a whole-car zone') + '). Edit the step so it targets the ' + named[0] + ', or say “the whole car” if you meant everything.';
    }
    function run() {
        var B = bridge(); if (!B || !B.run) { S.msg = 'The copilot is still starting: try again in a moment.'; draw(); return; }
        if (B.busy && B.busy()) { S.msg = 'Still working on the last one.'; draw(); return; }
        recheck(); var pl = toPlan(S.steps, S.text && !S.edited ? S.text : ''); var blocked = S.steps.filter(function (s) { return s.ask; })[0];
        if (!pl.ok || blocked) { S.msg = pl.ok ? blocked.ask : 'To run: ' + pl.problems[0] + '.'; draw(); return; }
        var said = readAs(S.steps), p = null;
        var sg = S.text && !S.edited ? scopeGuard(S.text, pl.ed) : null; if (sg) { S.msg = sg; draw(); return; }          // HELPER FIX PASS 7 2026-10-05: the final guard before Run (a turn that names a part changes only that part)
        tlStart('▶ Run: ' + said, 'run');          // fix pass 5a turn log
        try { p = B.run(S.text && !S.edited ? S.text : said, pl.ed, { post: pl.post, specOnly: pl.specOnly, logText: '▶ Run: ' + said }); } catch (e) { S.msg = 'Could not run: ' + (e && e.message); draw(); return; }
        S.ran = { at: Date.now() }; S.edit = null; draw();
        if (p && p.then) p.then(function () { draw(); }, function () { S.ran = null; S.msg = 'Something went wrong; nothing was kept.'; draw(); });
    }
    function askAI() {
        var B = bridge(), t = S.text || S.liveText; if (!t) return;
        if (!configured()) { S.msg = 'Online mode needs a key: open ⚙ in the panel.'; draw(); return; }
        tlStart(t, 'askai'); S.steps = []; S.text = ''; draw();          // fix pass 5a turn log
        if (B && B.askAI) B.askAI(t); else if (W.spbProAI && W.spbProAI.ask) W.spbProAI.ask(t, { forceAI: true }).then(function (r) { return W.spbProAI.finish(r, t, 'ask'); });
    }
    // ---- the copilot hands a typed sentence's plan here (js/spb-pro-ai.js offlineEditAsk); null = the copilot's normal path
    function typedNow(text) { var ty = S.typed; return !!(ty && ty.text === String(text || '').trim() && Date.now() - ty.t < 20000); }
    function claim(text, ed) {
        if (!HAS_DOM || !ed || (ed.kind !== 'ops' && ed.kind !== 'ask') || ed.builder) return null;
        if (ed.prohibited_edit || (ed.protected_parts && ed.protected_parts.length)) return null;          // protected panels keep their own exact answer
        if (!typedNow(text) || !offlineMode()) return null;
        S.typed = null;
        var env = envNow(), r = fromPlan(ed, env, text); if (!r.steps.length) r = fromFlags(text, env); if (!r.steps.length) return null;
        S.steps = r.steps; S.answer = null; S.text = String(text); S.textFlags = flag(S.text); S.ran = null; S.edit = null; S.term = null; S.termPin = false; S.liveText = ''; S.flags = []; S.edited = false; S.msg = '';
        check(S.steps, env); draw();
        var open = S.steps.filter(stepOpen).length, hq = S.steps.filter(function (s) { return s.ask && s.hiddenInfo; })[0];
        if (hq) return { offline: true, text: hq.ask + '\nPick one in the builder under the chat. Nothing is changed until you press ▶ Run.', queue: [], usage: { cost: 0 }, calls: 0, model: 'built-in', tools: [], asked: { options: [] }, builder: true };          // HELPER_V2: ask first
        return { offline: true, text: 'I read this as: ' + readAs(S.steps) + '.\n' + (open ? 'Step' + (open > 1 ? 's' : '') + ' marked ⚠ need' + (open > 1 ? '' : 's') + ' a pick: the builder under the chat shows the choices. Nothing is changed until you press ▶ Run.' : 'Check the steps in the builder under the chat, then press ▶ Run (or Edit any step). Nothing is changed until you do.'), queue: [], usage: { cost: 0 }, calls: 0, model: 'built-in', tools: [], asked: { options: [] }, builder: true };
    }
    // ---- attach to the copilot panel: typed-text marker (capture phase, before the panel's own Enter / Send handlers) + live flagging
    // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- FINAL 5a owner MANDATE (binding): "anything I type into the AI helper boxes gets logged
    // somewhere at least temporarily where you can pull the chat logs and SEE what happened". One record per typed turn (Enter, Send, a tapped chip, Run, Ask-the-AI, Undo):
    // the text, offline/online mode, what the offline reader made of it (class, path, steps, open steps), which path answered, the copilot's replies and the zones that changed
    // (name, layers, colour, finish). Posted to the LOCAL server (/api/ai/turn-log -> output/ai_logs/copilot_turns.jsonl, 5 MB rotation); never sent anywhere else.
    // Read with: python scripts/ai_logs_tail.py [-n 20]. Fire-and-forget: a failed post never touches the copilot.
    var TL = { cur: null, seq: 0 };
    function tlZones() { var Z = null; try { Z = (typeof zones !== 'undefined') ? zones : W.zones; } catch (e) { Z = W.zones; } return (Z || []).map(function (z, i) { var c = z && z.color; return { i: i, id: z && (z.id || null), name: String(z && z.name || ''), base: z && (z.base || null), finish: z && (z.finish || null), pattern: z && z.pattern && z.pattern !== 'none' ? z.pattern : null, colour: typeof c === 'string' ? c.slice(0, 40) : (c ? JSON.stringify(c).slice(0, 120) : null), layers: z && (z.sourceLayers || z.sourceLayer) ? JSON.stringify(z.sourceLayers || z.sourceLayer).slice(0, 160) : null, region: z && (z.regionMask || z.spatialMask) ? 'mask' : null, hidden: !!(z && (z.hidden || z.muted || z.enabled === false)), intensity: z && z.intensity != null ? z.intensity : null }; }); }
    function tlDiff(a, b) {
        var out = [], key = function (z) { return z.id || z.name + '#' + z.i; }, A = {}, Bm = {};
        a.forEach(function (z) { A[key(z)] = z; }); b.forEach(function (z) { Bm[key(z)] = z; });
        b.forEach(function (z) { var o = A[key(z)]; if (!o) out.push(Object.assign({ change: 'added' }, z)); else if (JSON.stringify(Object.assign({}, o, { i: 0 })) !== JSON.stringify(Object.assign({}, z, { i: 0 }))) out.push(Object.assign({ change: 'changed' }, z)); });
        a.forEach(function (z) { if (!Bm[key(z)]) out.push({ change: 'removed', name: z.name, layers: z.layers }); });
        return out.slice(0, 24);
    }
    function tlLog() { try { return (W.spbProAI && W.spbProAI.log ? W.spbProAI.log() : []) || []; } catch (e) { return []; } }
    function tlStart(text, src) {
        if (!HAS_DOM) return; try {
            if (TL.cur) tlFlush(true);
            var t = String(text || '').trim(); if (!t) return;
            TL.cur = { seq: ++TL.seq, text: t.slice(0, 4000), src: src, mode: offlineMode() ? 'offline' : 'online', configured: configured(), t0: Date.now(), z0: tlZones(), n0: tlLog().length, stable: 0 };
            clearInterval(TL.iv); TL.iv = setInterval(tlPoll, 700);
        } catch (e) {}
    }
    function tlPoll() {
        var c = TL.cur; if (!c) { clearInterval(TL.iv); return; }
        var busy = false; try { busy = !!(W.spbProAI && W.spbProAI.busy && W.spbProAI.busy()); } catch (e) {}
        var age = Date.now() - c.t0; c.stable = (!busy && age > 1200) ? c.stable + 1 : 0;
        if (c.stable >= 3 || age > 240000) tlFlush(false);
    }
    function tlFlush(cut) {
        var c = TL.cur; TL.cur = null; clearInterval(TL.iv); if (!c) return;
        try {
            var L = tlLog().slice(c.n0).map(function (m) { return { role: m.role, text: String(m.text || '').slice(0, 1200), model: m.model || (m.usage && m.usage.model) || null, cost: m.usage && m.usage.cost != null ? m.usage.cost : null, calls: m.calls || null, offline: m.offline || null }; }).slice(-10);
            var tr = null; try { var T = W.SpbOfflineAnswer && W.SpbOfflineAnswer._trail ? W.SpbOfflineAnswer._trail() : null; if (T && T.text === c.text && Math.abs((T.t || 0) - c.t0) < 60000) tr = { cls: T.cls, via: T.via || null, pass: T.pass || null, why: T.why || null }; } catch (e1) {}
            var st = null; try { if (S.text === c.text || S.typed && S.typed.text === c.text) st = { read: S.steps.length ? readAs(S.steps).slice(0, 1500) : '', steps: S.steps.length, open: S.steps.filter(function (x) { return x.ask || stepOpen(x); }).length, asks: S.steps.filter(function (x) { return x.ask; }).map(function (x) { return String(x.ask).slice(0, 200); }).slice(0, 4) }; } catch (e2) {}
            var path = c.src === 'askai' ? 'online (Ask-the-AI button)' : (tr ? 'offline helper' : (st && st.steps ? 'offline builder' : (L.some(function (m) { return m.role === 'ai' && m.model && !m.offline; }) ? 'online model' : 'app')));
            var rec = { seq: c.seq, src: c.src, mode: c.mode, configured: c.configured, text: c.text, path: path, offline: tr, builder: st, replies: L, zones_changed: tlDiff(c.z0, tlZones()), ms: Date.now() - c.t0, cut_short: !!cut, page: String(W.location && W.location.pathname || '') };
            if (W.fetch) W.fetch('/api/ai/turn-log', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rec), keepalive: true }).catch(function () {});
            W.__spbTurnLog = rec;          // the last record, for the in-app harnesses
        } catch (e) {}
    }
    function attach() {
        var p = panel(); if (!p || p.__spbOB) { if (p) { var d0 = dock(); if (d0) { var on = offlineMode(); if (d0.hidden === on) draw(); } } return; }
        var inp = p.querySelector('.spb-pai-input'); if (!inp) return;
        p.__spbOB = true;
        p.addEventListener('keydown', function (ev) { if (ev.target === inp && (ev.key === 'Enter' || ev.keyCode === 13) && !ev.shiftKey) markTyped(inp.value, 'enter'); }, true);
        p.addEventListener('click', function (ev) { var b = ev.target && ev.target.closest ? ev.target.closest('[data-act="send"]') : null; if (b) markTyped(inp.value, 'send'); }, true);
        p.addEventListener('click', function (ev) { var c = ev.target && ev.target.closest ? ev.target.closest('.spb-pai-opt[data-say]') : null; if (c) markTyped(c.getAttribute('data-say'), 'chip'); }, true);          // HELPER_V2 fix pass 4 2026-10-04 owner: keep improving the Offline Helper -- a tapped answer chip is the buyer's own answer: the helper's conversation layer reads it (it fills the question it just asked)
        inp.addEventListener('input', function () { S.liveText = String(inp.value || '').trim() ? inp.value : ''; S.flags = S.liveText ? flag(S.liveText) : []; if (!S.termPin) S.term = null; clearTimeout(S._lt); S._lt = setTimeout(draw, 120); });
        draw();
    }
    function markTyped(v, src) { var t = String(v || '').trim(); if (t) { tlStart(t, src || 'typed'); S.typed = { text: t, t: Date.now() }; S.liveText = ''; S.flags = []; S.edited = false; clearTimeout(S._hv); if (!S.termPin && S.term) { S.term = null; S.article = null; try { draw(); } catch (e) {} } } }          // OWNTURN: Send closes a hover peek
    if (HAS_DOM) { var boot = function () { try { attach(); } catch (e) {} }; setInterval(boot, 1200); }

    W.SpbEnc = W.SpbEnc || SpbEnc;
    // OFFLINE_BUILDER 2026-10-04: SPB Encyclopedia "Do it" -> a builder step (finish / pattern / spec = WHICH LOOK on the whole car or on the last step's result; flow = an empty step)
    function takeAction(x) {
        if (!HAS_DOM || !x || !offlineMode()) return false;
        try { if (W.spbProAI && W.spbProAI.open) W.spbProAI.open(); } catch (e0) {}
        if (S.ran) { S.steps = []; S.ran = null; S.text = ''; }
        var ch = actionChoice(x), st;
        if (ch) { st = stepFromTerm(S.steps, null, ch); if (!S.steps.length) st.what = { k: 'body' }; if (st.what) st.note = ''; st.prefilled = true; st.note = 'From the encyclopedia: ' + (x.label || x.id) + '.'; }
        else if (x.do === 'flow' && /colou?r/.test(String(x.id))) st = newStep({ act: 'recolour' });
        else st = newStep();
        S.steps.push(st); S.edit = st.id; S.term = null; S.browse = null; recheck(); dock(); draw();
        setTimeout(function () { try { var n = document.querySelector('#spbProAI .spb-ob-step[data-sid="' + st.id + '"]'); if (n) { n.scrollIntoView({ block: 'nearest' }); n.classList.add('spb-ob-flash'); setTimeout(function () { n.classList.remove('spb-ob-flash'); }, 1800); } } catch (e1) {} }, 60);
        return true;
    }
    // HELPER_V2 2026-10-04: the offline front door (js/spb-offline-answer.js) shows its outcome in this dock
    function showAnswer(r, text) { S.answer = r; S.term = null; S.termPin = false; S.browse = null; if (S.ran) { S.steps = []; S.ran = null; } S.text = String(text || ''); S.liveText = ''; S.flags = []; S.msg = ''; draw(); }
    function showOnline(r, text) { showAnswer(r, text); }
    function showSteps(steps, text) { S.answer = null; S.steps = steps; S.text = String(text || ''); S.textFlags = flag(S.text); S.ran = null; S.edit = null; S.term = null; S.termPin = false; S.liveText = ''; S.flags = []; S.edited = false; S.msg = ''; check(S.steps, envNow()); draw(); }
    W.SpbOfflineBuilder = {
        typedNow: typedNow, offlineMode: offlineMode, envNow: envNow, configured: configured, showAnswer: showAnswer, showOnline: showOnline, showSteps: showSteps, hiddenPick: hiddenPick, compoundSteps: compoundSteps, v2Term: v2Term,
        // pure logic (node-testable)
        tokens: tokens, flag: flag, flagHtml: flagHtml, termById: termById, searchChoices: searchChoices, fromPlan: fromPlan, fromText: fromText, fromFlags: fromFlags, toPlan: toPlan, check: check,
        readAs: readAs, summary: summary, stepText: stepText, newStep: newStep, pickChoice: pickChoice, setAct: setAct, whatChoices: whatChoices, lookChoices: lookChoices, stepFromTerm: stepFromTerm, stepOpen: stepOpen, thumbFor: thumbFor, TEX: TEX,
        // app
        enc: SpbEnc, articleFromTerm: articleFromTerm,
        claim: claim, state: function () { return S; }, draw: draw, attach: attach, markTyped: markTyped, run: run, takeAction: takeAction, gearName: gearName,      // one label for both ask-the-AI buttons (OFFLINE_BUILDER FINAL 2)
        linkOut: function (l) { return HAS_DOM ? linkOut(l) : null; }
    };
})();
