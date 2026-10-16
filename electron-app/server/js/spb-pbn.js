// PBN 2026-10-08 owner: the OFFLINE helper is "paint by numbers" (lane B-PBN).
// It OPENS by asking what the buyer is trying to do, then walks a funnel of click questions: goal -> where (whole car / part / numbers / logos / a PSD LAYER)
// -> colour (solid, or colour with other colours = catalogue suggestions) -> finish look (matte / chrome / Fractured / candy ... from the real catalogue).
// Typed keywords narrow it at every step and the words it recognised are flagged ("all my numbers gold" = NUMBERS + GOLD fills those answers).
// The buyer can BACK UP any step. The end is DOING it (steps are handed to the existing offline builder = the existing planner / Run / Undo path)
// or SHOW ME (the Encyclopedia article that explains it). Builds ON js/spb-offline-builder.js (window.SpbOfflineBuilder); no parallel system.
// Kill switch: window.SPB_PBN_OFF = true (checked every tick). Free text typed into the panel + Enter is untouched (it still goes to the free-text path).
// Easy mode is hidden: nothing here mentions it.
// B2-PBN v2 2026-10-08 (buyer simulation, 62 goals x 3 cars): (a) a "I read your words as ..." shortcut strip from the planner (SpbOfflineBuilder.fromText: then-clauses, except-clauses),
// (b) a text router: how-to questions -> Encyclopedia articles (SpbEncyclopedia.search, public API); things the offline helper cannot do (new stripes, text, resizing, parts that are not on the paint, real
// liveries, areas) -> a clear "I can't do that offline" card with the part it CAN do + Show me how + Ask the online helper, (c) more finish families (flames in the pattern funnel, rust, animal print...),
// (d) both sides (doors), typo/slang words (sparkly, mate, flat), size + pattern-colour tweak chips on the plan, (e) an escape row on every question so nothing is a dead end.
(function () {
    'use strict';
    var W = window, D = document;
    function OB() { return W.SpbOfflineBuilder || null; }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function cap(s) { s = String(s || ''); return s.charAt(0).toUpperCase() + s.slice(1); }
    function clone(o) { return o == null ? o : JSON.parse(JSON.stringify(o)); }

    var COLOURS = ['red', 'orange', 'yellow', 'gold', 'lime', 'green', 'teal', 'cyan', 'blue', 'navy', 'purple', 'pink', 'hot pink', 'magenta', 'white', 'silver', 'grey', 'black', 'brown'];
    var FALLBACK = { red: '#d01818', orange: '#ff7a00', yellow: '#ffd200', gold: '#d7a72b', lime: '#8fe000', green: '#1a9a2a', teal: '#108f8f', cyan: '#18c8e0', blue: '#1450d8', navy: '#14245a', purple: '#6a1b9a', violet: '#7f3fbf', pink: '#ff7eb6', 'hot pink': '#ff3fa4', magenta: '#e01ca8', white: '#ffffff', silver: '#c0c4c8', grey: '#808080', gray: '#808080', black: '#111113', brown: '#6b3e1e' };
    var STOP = {}; 'a an the my our your me i we you want wanna need would like to make change changing turn paint colour color colours colors it its on of and or then please just all every each both with in for that this these those is are be can could should do does from into onto over under up out as at by so also too now car cars looks look finish finishes'.split(' ').forEach(function (w) { STOP[w] = 1; });
    // finish families shown in the "which look" question: [label, [encyclopedia term ids]] (only those that exist and have real catalogue choices are shown)
    var FAMILIES = [
        ['Fractured', ['shelf:fractured_elements', 'shelf:fractured_cosmos', 'shelf:fractured_nightshift', 'shelf:fractured_flames', 'shelf:fractured_minds', 'shelf:fractured_souls', 'shelf:fractured_forge', 'shelf:fractured_opalfire', 'shelf:fractured_foundry', 'shelf:fractured_tessera', 'shelf:fractured_shokk', 'shelf:fractured_wilds', 'shelf:fractured_relics']],
        ['Flames', ['flames', 'shelf:flames']], ['Candy', ['candy_look']], ['Carbon fibre', ['carbon_fiber']], ['Camo', ['camo']], ['Holographic', ['holographic']],
        ['Colour shift', ['colour_shift', 'iridescent']], ['Gradients', ['shelf:gradients', 'shelf:gradient_directional']], ['Neon', ['neon', 'shelf:neon_underground']],
        ['Metals', ['gunmetal', 'copper', 'gold_look', 'brushed_aluminum', 'hammered_metal']], ['Glass and ice', ['glass_look', 'ice']], ['Snakeskin and scales', ['crocodile', 'dragon_scales', 'fish_scales']],
        ['Lava and galaxy', ['lava', 'galaxy']], ['Stealth', ['stealth_look', 'look:stealth']], ['Wood and leather', ['wood_grain', 'leather_look']], ['Racing', ['tag:racing', 'checkered']]
    ];
    // slang / typos -> the plain look the buyer means
    var SYN = { sparkly: 'metallic', sparkle: 'metallic', sparkling: 'metallic', glitter: 'metallic', glittery: 'metallic', flake: 'metallic', flakes: 'metallic', shiny: 'gloss', glossy: 'gloss', mate: 'matte', matt: 'matte', flat: 'matte', dull: 'matte', satiny: 'satin', pearlescent: 'pearl', chrom: 'chrome', crome: 'chrome', chorme: 'chrome', cromed: 'chrome' };
    // families searched by word (no encyclopedia term of their own): [label, [search words]]
    var QFAMILIES = [['Rust and worn', ['rust', 'rusty', 'patina', 'weathered', 'worn', 'corroded']], ['Animal print', ['leopard', 'zebra', 'cheetah', 'tiger', 'giraffe', 'cow', 'animal']], ['Glitter and flake', ['glitter', 'sparkle', 'flake']],
        ['Marble and stone', ['marble', 'granite', 'stone', 'concrete']], ['Graffiti and splatter', ['splatter', 'graffiti', 'drip', 'spray']], ['Checker and plaid', ['checker', 'plaid', 'houndstooth', 'tartan']], ['Hex and honeycomb', ['hex', 'honeycomb', 'mesh']],
        ['Lightning and stars', ['lightning', 'bolt', 'star', 'stars']], ['Skulls and tribal', ['skull', 'skulls', 'tribal']]];
    var PATTERN_FAMS = ['Flames', 'Carbon fibre', 'Camo', 'Snakeskin and scales', 'Wood and leather', 'Racing', 'Lava and galaxy', 'Holographic'];
    var SIMPLE = ['matte', 'satin', 'gloss', 'metallic', 'pearl', 'chrome', 'satin chrome', 'brushed', 'frosted', 'wet look'];
    var MULTI = ['shelf:gradients', 'shelf:color_clash', 'colour_shift', 'shelf:spectrum_shift', 'holographic', 'iridescent', 'tag:multicolor'];

    var S = { text: '', picks: [], open: true, listAll: false, sig: '', msg: '', routeOff: null };

    // ------------------------------------------------------------------ small readers
    // "...except the stripes" / "but leave the numbers alone": the words the buyer wants LEFT ALONE -> the planner's exclude list
    var EXCEPT_RE = /\b(except(?: for)?|but not|but leave|but keep|but skip|apart from|other than|besides|excluding|without touching|but (?:don'?t|do not) touch|but)\b\s*(?:leave |keep |skip |touching |touch )?(?:the |my |all |all of the |all of my )?(numbers?|stripes?|pinstripes?|sponsors?|logos?|decals?)\b/i;
    // slang / typos the planner does not know: stickers/decals/badges = logos, "sponser" = sponsors
    function fixWords(text) { return String(text || '').replace(/\bsp[oa]n[sc][eo]rs?\b/gi, 'sponsors').replace(/\b(stickers?|decals?|badges?)\b/gi, 'logos').replace(/\bnumb(?:er|r)s?\b/gi, function (m) { return /s$/i.test(m) ? 'numbers' : 'number'; }); }
    function exceptOf(text) {
        var m = EXCEPT_RE.exec(String(text || '')); if (!m) return null;
        var w = m[2].toLowerCase(), k = /^number/.test(w) ? 'numbers' : (/stripe/.test(w) ? 'stripes' : 'sponsors');
        return { list: [k], word: w, s: m.index, e: m.index + m[0].length };
    }
    function sidesPair() {
        var B = OB(), wc = []; try { wc = B.whatChoices(env(), [], { id: 'pbn' }); } catch (x) {}
        var L = wc.filter(function (c) { return c.grp === 'Parts' && /^(left|right) side$/i.test(c.label); });
        return L.length >= 2 ? { label: 'Both sides (doors)', what: { k: 'multi', list: L.map(function (c) { return c.what; }) } } : null;
    }
    function famFromQ(w) { for (var i = 0; i < QFAMILIES.length; i++) if (QFAMILIES[i][1].indexOf(w) >= 0) return QFAMILIES[i]; return null; }
    function famChoices(f) {   // one family value -> [{c, term}] (encyclopedia term choices, plus a word search for the QFAMILIES)
        var B = OB(), out = termChoices(f.ids || (f.id ? [f.id] : [])), seen = {};
        out.forEach(function (r) { seen[r.c.finish_id || r.c.pattern_id || r.c.spec_id] = 1; });
        (f.qwords || []).forEach(function (w) {
            var hits = []; try { hits = B.searchChoices(w, ['finish', 'pattern'], 10); } catch (x) {}
            hits.forEach(function (h) { if (seen[h.id]) return; seen[h.id] = 1; out.push({ c: { label: h.label, finish_id: h.kind === 'finish' ? h.id : undefined, pattern_id: h.kind === 'pattern' ? h.id : undefined }, term: 'q' }); });
        });
        return rerank(out, f);
    }
    // W1-PBNDO 2026-10-09: the funnel used to offer / apply the catalogue's FIRST hit: wood grain -> Leather Grain, rust -> "Color Clash: Rust vs Ice" (b2pbn REPORT 'honest limits').
    // Best-meaning picks lead: curated ids per look word, then whole-word label matches on what the buyer typed or the family name, "vs" blends last. Kill switch: window.SPB_PBN_NO_RERANK.
    var PREFER = [[/\b(wood|woods|wooden|timber|oak|walnut|teak|burl|woodgrain)\b/, ['monolithic::ff_heartwood', 'monolithic::woc_teak_grain', 'wood_burl', 'monolithic::petrified_wood']],
        [/\b(rust|rusty|rusted|corroded|corrosion|weathered|patina|worn)\b/, ['base::efx_rust_through', 'monolithic::nsx_anchor_rust', 'base::cbp_scav_rust', 'monolithic::patina_truck']],
        [/\b(leather|hide|suede)\b/, ['monolithic::aged_leather', 'base::efx_leather_grain', 'monolithic::fc_coarse_hide']],
        [/\bfractur/, ['monolithic::ff_truchet_glass']], [/\bholo/, ['monolithic::xlab_hologram_metal', 'monolithic::impossible_hologram_noir']]];
    var PLABEL = { 'monolithic::ff_heartwood': 'Heartwood', 'monolithic::woc_teak_grain': 'Indonesia: Teak Grain', 'base::efx_rust_through': 'Rust-Through', 'monolithic::nsx_anchor_rust': 'Anchor Rust', 'monolithic::aged_leather': 'Aged Leather', 'monolithic::ff_truchet_glass': 'Truchet Glass' };
    // the planner ("I read your words") picks the first catalogue hit too: swap a clearly worse pick (wood grain -> Leather Grain, rust -> "Rust vs Ice") for the best-meaning one
    function fixPicks(st, text, hex) {
        if (W.SPB_PBN_NO_RERANK) return; var B = OB(), t = String(text || '').toLowerCase();
        st.forEach(function (s) {
            var f = s && s.finish; if (!f || f.kind !== 'cat') return;
            PREFER.slice(0, 3).forEach(function (p) {
                if (!p[0].test(t) || p[1].indexOf(f.key) >= 0) return; var id = p[1][0], lab = PLABEL[id]; if (!id || !lab || /^wood_burl$/.test(id)) return;
                var w = (p[0].exec(t) || [''])[0]; if (w && new RegExp('\\b' + w, 'i').test(String(f.label || '')) && !/\bvs\b/i.test(String(f.label || ''))) return;          // the pick already names the word the buyer used
                if (p[0].test('leather') && !/leather|hide|suede/.test(t)) return; if (/leather/.test(t) && p === PREFER[0]) return;
                var it = itemFor({ label: lab, finish_id: id }, hex); if (it) B.pickChoice(s, it);
            });
        });
    }
    function rerank(out, f) {
        if (W.SPB_PBN_NO_RERANK || !out || out.length < 2) return out;
        var txt = (String(S.text || '') + ' ' + String((f && (f.label || f.title)) || '')).toLowerCase(), lead = [], words = txt.split(/[^a-z]+/).filter(function (w) { return w.length > 3 && !STOP[w]; });
        PREFER.forEach(function (p) { if (p[0].test(txt)) p[1].forEach(function (id) { if (lead.indexOf(id) < 0) lead.push(id); }); });
        // W3-PBN2 2026-10-09: a curated pick the family list did not contain (fractured -> Truchet Glass; funnel g59 got 'Water: Glassy Swell') is added to the list, then ranked first. Kill switch: SPB_PBN2_NO_INJECT
        if (!W.SPB_PBN2_NO_INJECT) { var have = {}; out.forEach(function (r) { have[r.c.finish_id || r.c.pattern_id || r.c.spec_id || ''] = 1; }); out = out.slice(); lead.slice(0, 1).forEach(function (id) { var lab = PLABEL[id]; if (lab && !have[id] && /^monolithic::(ff_heartwood|ff_truchet_glass)$|^base::efx_rust_through$/.test(id)) out.unshift({ c: { label: lab, finish_id: id }, term: 'p' }); }); }
        function key(r) { return r.c.finish_id || r.c.pattern_id || r.c.spec_id || ''; }
        function score(r, i) {
            var k = key(r), li = lead.indexOf(k), lab = String(r.c.label || '').toLowerCase(), sc = 0;
            if (li >= 0) sc += (100 - li) * 10;          // W3-PBN2 2026-10-09: x10 so the curated order beats the whole-word label bonus ('Wood Burl' outranked Heartwood for the 'Wood and leather' family)
            words.forEach(function (w) { if (new RegExp('\\b' + w + '\\b').test(lab)) sc += 6; });
            if (/\bvs\b/.test(lab)) sc -= 3;
            return sc * 1000 - i;
        }
        return out.map(function (r, i) { return { r: r, s: score(r, i) }; }).sort(function (a, b) { return b.s - a.s; }).map(function (x) { return x.r; });
    }

    // ------------------------------------------------------------------ keywords -> slots
    function colourHexOf(name) { var B = OB(), t = B && B.termById('colour:' + name); return (t && t.colour && t.colour.hex) || FALLBACK[name] || null; }
    function infer(text) {
        text = fixWords(text);
        var B = OB(), out = { words: [], leftover: [] };
        if (!B || !String(text || '').trim()) return out;
        var tk = B.tokens(text), flags = B.flag(text), used = {}, fams = [], xr = exceptOf(text);
        if (xr) { out.exclude = xr.list; out.words.push({ label: 'except ' + xr.word, kind: 'topic' }); }
        function mark(s, e) { tk.forEach(function (t, i) { if (t.s >= s && t.e <= e) used[i] = 1; }); }
        function inX(s, e) { return xr && s >= xr.s && e <= xr.e; }
        flags.forEach(function (f) {
            if (inX(f.s, f.e)) { mark(f.s, f.e); return; }
            var t = B.termById(f.id) || {}, a = String(f.alias || '');
            if (f.comp || f.compound) { }
            var cname = /^colour:/.test(f.id) ? f.id.slice(7) : (FALLBACK[a] ? a : null);
            if (cname && colourHexOf(cname) && (/^colour:/.test(f.id) || a.indexOf(' ') < 0)) { out.colour = { name: cname, hex: colourHexOf(cname) }; out.words.push({ label: cname, kind: 'colour' }); mark(f.s, f.e); return; }
            if (/^part:/.test(f.id) && t.part) { var pn = String((t.part && (t.part.name || t.part)) || t.title).toLowerCase(); out.target = { label: cap(pn), what: { k: 'part', part: pn } }; out.words.push({ label: pn, kind: 'part' }); mark(f.s, f.e); return; }
            if (t.choices && t.choices.length && !f.weak && !/^(colour|part|element|palette|scheme):/.test(f.id)) { fams.push({ id: f.id, title: t.title || a, alias: a }); out.words.push({ label: a, kind: 'look' }); mark(f.s, f.e); }
            else if (!f.weak && f.tier !== 3) { out.words.push({ label: a, kind: 'topic' }); mark(f.s, f.e); }
        });
        // words the encyclopedia does not flag as such
        function drop(w) { out.words = out.words.filter(function (x) { return !(x.kind === 'topic' && String(x.label).split(' ').indexOf(w) >= 0); }); }
        tk.forEach(function (t, i) {
            var w = SYN[t.w] || t.w, w0 = t.w;
            if (inX(t.s, t.e)) { used[i] = 1; return; }
            if (/^(bigger|larger|huge|giant|large|chunky)$/.test(w0)) { out.size = 1.6; out.words.push({ label: w0, kind: 'look' }); used[i] = 1; }
            else if (/^(smaller|tiny|fine|small|micro|finer)$/.test(w0)) { out.size = 0.6; out.words.push({ label: w0, kind: 'look' }); used[i] = 1; }
            else if (/^(doors?|fenders?|quarters?)$/.test(w0) && !out.target) { var sp = sidesPair(); if (sp) { out.target = sp; out.words.push({ label: w0, kind: 'part' }); used[i] = 1; } }
            else if (/^(numbers?|numerals?)$/.test(w)) { out.target = { label: 'Numbers', what: { k: 'numbers' }, numbers: true }; drop(w); out.words.push({ label: 'numbers', kind: 'target' }); used[i] = 1; }
            else if (/^(logos?|sponsors?|decals?)$/.test(w)) { out.target = { label: 'Sponsors / logos', what: { k: 'sponsors' }, logos: true }; drop(w); out.words.push({ label: w, kind: 'target' }); used[i] = 1; }
            else if (/^(everything|entire|whole)$/.test(w)) { out.target = { label: 'Whole car', what: { k: 'body' } }; out.words.push({ label: w, kind: 'target' }); used[i] = 1; }
            else if (!out.colour && FALLBACK[w] && colourHexOf(w) && !used[i]) { out.colour = { name: w, hex: colourHexOf(w) }; out.words.push({ label: w, kind: 'colour' }); used[i] = 1; }
            else if (SIMPLE.indexOf(w) >= 0 && !out.simple) { out.simple = w; drop(w); out.words.push({ label: w0, kind: 'look' }); used[i] = 1; }
        });
        tk.forEach(function (t, i) { if (inX(t.s, t.e)) return; var qf = famFromQ(t.w); if (qf && !out.simple) { fams = [{ id: null, qwords: qf[1], title: qf[0], alias: t.w }]; out.words = out.words.filter(function (x) { return x.label !== t.w; }); out.words.push({ label: t.w, kind: 'look' }); used[i] = 1; } });
        if (!out.colour) tk.forEach(function (t) { if (!out.colour && !inX(t.s, t.e) && FALLBACK[t.w] && colourHexOf(t.w) && SYN[t.w] == null) { out.colour = { name: t.w, hex: colourHexOf(t.w) }; out.words.push({ label: t.w, kind: 'colour' }); } });      // "matte black": the encyclopedia flags the pair as one look; the colour is still a colour
        if (!out.simple) { var j; for (j = fams.length - 1; j >= 0; j--) if (SIMPLE.indexOf(fams[j].alias) >= 0) { out.simple = fams[j].alias; fams.splice(j, 1); } }
        if (fams.length && !out.simple) out.fam = fams[0];
        if (out.fam && out.fam.id === null) out.fam.id = undefined;
        tk.forEach(function (t, i) { if (!used[i] && !STOP[t.w] && t.w.length > 1) out.leftover.push(t.w); });
        if (out.colour && (out.fam || out.simple)) out.goal = 'both'; else if (out.colour) out.goal = 'colour'; else if (out.fam || out.simple) out.goal = 'finish';
        out.search = out.leftover.slice(); out.words.forEach(function (w) { if (w.kind === 'topic') String(w.label).split(' ').forEach(function (x) { if (x.length > 2 && !STOP[x] && out.search.indexOf(x) < 0) out.search.push(x); }); });
        if (out.fam && out.fam.id && !out.colour) { var ft = B.termById(out.fam.id), fc = (ft && ft.choices) || []; if (fc.length && fc.every(function (c) { return c.pattern_id; })) out.goal = 'pattern'; }
        return out;
    }

    // ------------------------------------------------------------------ effective slots = clicked picks over keyword inference
    function pick(slot) { for (var i = S.picks.length - 1; i >= 0; i--) if (S.picks[i].slot === slot) return S.picks[i]; return null; }
    function eff() {
        var inf = infer(S.text), e = { inf: inf }, p;
        e.goal = (p = pick('goal')) ? p.val : (inf.goal || null);
        e.target = (p = pick('target')) ? p.val : (inf.target || null);
        e.layer = (p = pick('layer')) ? p.val : null;
        e.layermore = !!pick('layermore');
        e.colour = (p = pick('colour')) ? p.val : (inf.colour || null);
        e.cmode = (p = pick('cmode')) ? p.val : null;
        e.fam = (p = pick('fam')) ? p.val : (inf.fam ? { id: inf.fam.id, qwords: inf.fam.qwords, label: inf.fam.title } : (inf.simple ? { simple: inf.simple, label: cap(inf.simple) } : null));
        e.size = (p = pick('size')) ? p.val : (inf.size || null);
        e.pcolour = (p = pick('pcolour')) ? p.val : null;
        e.exclude = inf.exclude || null;
        e.finish = (p = pick('finish')) ? p.val : null;
        e.question = (p = pick('question')) ? true : false;
        return e;
    }
    function env() { var B = OB(); try { return B.envNow(); } catch (x) { return { palette: [], layers: [], zoneColours: [] }; } }
    function layerCands(kind, layers) {
        var re = kind === 'numbers' ? /(^|[^a-z])(num|numbers?|numerals?|digits?|#)([^a-z]|$)/i : /logo|sponsor|decal|graphic|badge|brand/i;
        return layers.filter(function (l) { return !l.hidden && re.test(String(l.name || '')) && !/^\s*(wire|mask|car[ _]*mandatory|template|guides?)\b/i.test(String(l.name || '')); });
    }
    function realLayers(en) { return ((en.layers) || []).filter(function (l) { return !l.hidden && !/^\s*(wire|mask|car[ _]*mandatory|template|guides?)\b/i.test(String(l.name || '')); }); }
    function termChoices(ids) {
        var B = OB(), seen = {}, out = [];
        ids.forEach(function (id) { var t = B.termById(id); ((t && t.choices) || []).forEach(function (c) { var ch = (c.finish_id || c.pattern_id || c.spec_id) ? c : null; if (!ch) return; var k = (c.finish_id || c.pattern_id || c.spec_id); if (seen[k]) return; seen[k] = 1; out.push({ c: c, term: id }); }); });
        return out;
    }
    function itemFor(c, hex) {   // one catalogue choice -> a builder choice item (kind cat / tex)
        var B = OB(), it = null;
        if (c.finish_id) it = { kind: 'cat', key: c.finish_id, id: c.finish_id, label: c.label, hex: c.hex || null };
        else if (c.pattern_id) it = { kind: 'tex', mode: 'pattern', id: c.pattern_id, label: c.label, name: c.label, hex: c.hex || null };
        else if (c.spec_id) it = { kind: 'tex', mode: 'spec', id: c.spec_id, label: c.label, name: c.label };
        if (it) it.thumb = B.thumbFor(it, (hex || c.hex || '888888').replace('#', ''));
        return it;
    }
    function simpleItems(hex) {
        var B = OB(), got = {}, out = [];
        ['shine', 'finish'].forEach(function (act) { var l = []; try { l = B.lookChoices({ act: act, found: null, termChoices: null }); } catch (x) {} l.forEach(function (c) { if (c.kind === 'look' && SIMPLE.concat(['holographic']).indexOf(c.id) >= 0 && !got[c.id]) { got[c.id] = 1; c.thumb = ''; out.push(c); } }); });
        var order = SIMPLE.concat(['holographic']); out.sort(function (a, b) { return order.indexOf(a.id) - order.indexOf(b.id); });
        return out;
    }

    // ------------------------------------------------------------------ the question tree (data-driven: each node answers "do I still need to ask?")
    // node(e, en) -> null (satisfied / skipped) or { id, q, hint, opts:[{label, sub, hex, thumb, grp, pick:{slot,val,label}}], filterable }
    var NODES = [
        function goal(e) {
            if (e.goal) return null;
            return { id: 'goal', q: 'What are you trying to do?', hint: 'Click one, or type words below (e.g. “my numbers gold”): I flag what I recognise.', opts: [
                { label: 'Change a colour', sub: 'recolour part of the car', pick: { slot: 'goal', val: 'colour', label: 'Change a colour' } },
                { label: 'Give it a finish', sub: 'matte, chrome, candy, Fractured...', pick: { slot: 'goal', val: 'finish', label: 'Add a finish' } },
                { label: 'Colour and a finish', sub: 'gold chrome, red candy...', pick: { slot: 'goal', val: 'both', label: 'Colour + finish' } },
                { label: 'Add a pattern or texture', sub: 'carbon, camo, snakeskin...', pick: { slot: 'goal', val: 'pattern', label: 'Add a pattern' } },
                { label: 'I have a question', sub: 'show me how it works', pick: { slot: 'question', val: true, label: 'A question' } }
            ] };
        },
        function target(e, en) {
            if (e.target || e.question || e.layermore) return null;
            var B = OB(), opts = [{ label: 'The whole car', sub: 'every painted part', grp: 'Quick', pick: { slot: 'target', val: { label: 'Whole car', what: { k: 'body' } }, label: 'Whole car' } },
                { label: 'Numbers', grp: 'Quick', pick: { slot: 'target', val: { label: 'Numbers', what: { k: 'numbers' }, numbers: true }, label: 'Numbers' } },
                { label: 'Sponsors / logos', grp: 'Quick', pick: { slot: 'target', val: { label: 'Sponsors / logos', what: { k: 'sponsors' }, logos: true }, label: 'Logos' } }];
            var sp2 = sidesPair(); if (sp2) opts.splice(1, 0, { label: sp2.label, sub: 'left + right', grp: 'Quick', pick: { slot: 'target', val: sp2, label: sp2.label } });
            var lay = realLayers(en);
            if (lay.length) opts.push({ label: 'A layer of the file', sub: lay.length + ' layers', grp: 'Quick', pick: { slot: 'layermore', val: true, label: 'A layer' } });
            var wc = []; try { wc = B.whatChoices(en, [], { id: 'pbn' }); } catch (x) {}
            wc.forEach(function (c) { if (c.grp === 'Parts') opts.push({ label: c.label, grp: 'Parts', pick: { slot: 'target', val: { label: c.label, what: c.what }, label: c.label } }); else if (c.grp === 'Colours on the car') opts.push({ label: c.label, sub: c.sub, hex: c.hex, grp: 'A colour already on the car', pick: { slot: 'target', val: { label: c.label + ' areas', what: c.what }, label: c.label + ' areas' } }); });
            return { id: 'target', q: 'Where should it go?', hint: 'On the whole car, or just one place.', opts: opts, filterable: true };
        },
        function layerQ(e, en) {
            if (e.question || e.layer) return null;
            var lay = realLayers(en), isNum = e.target && e.target.numbers, isLogo = e.target && e.target.logos;
            if (e.layermore || (!e.target && !lay.length)) {
                if (!lay.length) return null;
                return { id: 'layer', q: 'Which layer?', hint: 'These are the layers in your file.', opts: lay.map(function (l) { return { label: l.name, grp: 'Layers', pick: { slot: 'layer', val: { label: 'Layer “' + l.name + '”', what: { k: 'layer', layers: [l.name], word: l.name } }, label: 'Layer ' + l.name } }; }), filterable: true };
            }
            if (!(isNum || isLogo) || !lay.length) return null;
            var cands = layerCands(isNum ? 'numbers' : 'logos', lay);
            if (!cands.length) return null;
            var nm = isNum ? 'numbers' : 'logos / sponsors', opts = cands.map(function (l) { return { label: l.name, sub: 'own layer', pick: { slot: 'layer', val: { label: 'Layer “' + l.name + '”', what: { k: 'layer', layers: [l.name], word: l.name } }, label: 'Layer ' + l.name } }; });
            opts.push({ label: 'No, they share a layer', sub: 'I will find them on the paint', pick: { slot: 'layer', val: { label: e.target.label, what: e.target.what }, label: 'Not on their own layer' } });
            opts.push({ label: 'Pick another layer', pick: { slot: 'layermore', val: true, label: 'Another layer' } });
            return { id: 'layer', q: 'Are the ' + nm + ' on their own layer?', hint: 'Your file has ' + lay.length + ' layers. Pick the layer, or say they share one.', opts: opts };
        },
        function colour(e) {
            if (e.question || e.goal === 'finish' || e.goal === 'pattern' || e.colour) return null;
            var B = OB(), opts = COLOURS.map(function (n) { return { label: cap(n), hex: colourHexOf(n), pick: { slot: 'colour', val: { name: n, hex: colourHexOf(n) }, label: cap(n) } }; });
            return { id: 'colour', q: 'Which colour?', hint: 'Click a swatch, or type a colour name.', opts: opts, filterable: true };
        },
        function cmode(e) {
            if (e.question || !e.colour || e.cmode || e.fam || e.finish || e.goal === 'finish' || e.goal === 'pattern') return null;
            var cn = cap(e.colour.name);
            return { id: 'cmode', q: 'Solid ' + e.colour.name + ', or ' + e.colour.name + ' with other colours?', hint: 'Solid is one flat colour. “With other colours” shows finishes that blend in more colours.', opts: [
                { label: 'Solid ' + cn, hex: e.colour.hex, sub: 'one colour', pick: { slot: 'cmode', val: 'solid', label: 'Solid' } },
                { label: cn + ' with other colours', hex: e.colour.hex, sub: 'see suggestions', pick: { slot: 'cmode', val: 'multi', label: 'With other colours' } }] };
        },
        function suggest(e) {
            if (e.question || e.cmode !== 'multi' || e.finish || e.fam) return null;
            var hx = e.colour ? e.colour.hex : null, ch = termChoices(MULTI).slice(0, 16), opts = ch.map(function (r) { var it = itemFor(r.c, hx); return it ? { label: r.c.label, thumb: it.thumb, pick: { slot: 'finish', val: it, label: r.c.label } } : null; }).filter(Boolean);
            return { id: 'suggest', q: 'Suggestions with more than one colour', hint: 'Real finishes from the catalogue, shown on your ' + (e.colour ? e.colour.name : 'colour') + '. Click one to use it.', opts: opts, filterable: true, none: { label: 'Never mind, solid colour', pick: { slot: 'cmode', val: 'solid', label: 'Solid' } } };
        },
        function fam(e) {
            if (e.question || e.fam || e.finish) return null;
            if (e.goal === 'colour' && e.cmode !== 'solid') return null;
            if (e.goal === 'colour' && pick('fam')) return null;
            if (e.cmode === 'multi') return null;
            if (!e.goal) return null;
            var B = OB(), hx = e.colour ? e.colour.hex : '#888888', opts = [];
            if (e.goal === 'pattern') {
                var pl = []; try { pl = B.lookChoices({ act: 'pattern' }); } catch (x) {}
                famOpts(opts, function (f) { return PATTERN_FAMS.indexOf(f[0]) >= 0; }, true);
                pl.forEach(function (c) { c.thumb = B.thumbFor(c, hx.replace('#', '')); opts.push({ label: c.label, thumb: c.thumb, grp: 'Patterns and textures', pick: { slot: 'finish', val: c, label: c.label } }); });
                return { id: 'fam', q: 'Which pattern or texture?', hint: 'Pick a family or a texture, or type a word like “flames” or “camo”.', opts: opts, filterable: true, search: true };
            }
            simpleItems(hx).forEach(function (c) { opts.push({ label: cap(c.label), thumb: c.thumb, grp: 'Plain looks', pick: { slot: 'finish', val: c, label: cap(c.label) } }); });
            famOpts(opts, function () { return true; }, false);
            return { id: 'fam', q: e.goal === 'colour' ? 'Add a finish on top of the ' + (e.colour ? e.colour.name : 'colour') + '?' : 'What look do you want?', hint: 'Plain looks apply right away. A family opens the real catalogue choices. Type a word (e.g. “carbon”) to search.', opts: opts, filterable: true, search: true,
                none: e.goal === 'colour' ? { label: 'No, just the colour', pick: { slot: 'fam', val: { none: true, label: 'No finish' }, label: 'No finish' } } : null };
        },
        function finishQ(e) {
            if (e.question || e.finish || !e.fam || e.fam.none || e.fam.simple) return null;
            var B = OB(), hx = e.colour ? e.colour.hex : '#888888', ch = famChoices(e.fam);
            if (!ch.length) return null;
            var opts = ch.slice(0, 36).map(function (r) { var it = itemFor(r.c, hx); return it ? { label: r.c.label, thumb: it.thumb, pick: { slot: 'finish', val: it, label: r.c.label } } : null; }).filter(Boolean);
            return { id: 'finish', q: 'Which ' + (e.fam.label || 'look') + '?', hint: ch.length + ' real choices from the catalogue.', opts: opts, filterable: true };
        }
    ];
    function famOpts(opts, keep, first) {   // the catalogue families (encyclopedia terms + word-search families) as options
        var B = OB();
        FAMILIES.forEach(function (f) { if (!keep(f)) return; var ids = f[1].filter(function (id) { return B.termById(id); }), n = termChoices(ids).length; if (n) opts.push({ label: f[0], sub: n + ' looks', grp: 'Catalogue families', pick: { slot: 'fam', val: { ids: ids, label: f[0] }, label: f[0] } }); });
        QFAMILIES.forEach(function (f) { if (!keep(f)) return; var v = { ids: [], qwords: f[1], label: f[0] }, n = famChoices(v).length; if (n) opts.push({ label: f[0], sub: n + ' looks', grp: 'Catalogue families', pick: { slot: 'fam', val: v, label: f[0] } }); });
    }
    function nextQ(e, en) { for (var i = 0; i < NODES.length; i++) { var q = NODES[i](e, en); if (q) return q; } return null; }

    // ------------------------------------------------------------------ ending: build builder steps
    function buildSteps(e, en) {
        var B = OB(), steps = [], t0 = e.layer ? e.layer.what : (e.target ? e.target.what : { k: 'body' });
        if (!t0) return null;
        var whats = t0.k === 'multi' ? t0.list : [t0], col = e.colour || e.pcolour;
        var hasColour = !!col && (e.pcolour || (e.goal !== 'finish' && e.goal !== 'pattern'));
        var fin0 = e.finish || (e.fam && e.fam.simple ? simpleFind(e.fam.simple) : null);
        if (!fin0 && e.fam && (e.fam.id || e.fam.ids || e.fam.qwords) && !e.fam.none) { var fc0 = famChoices(e.fam)[0]; fin0 = fc0 ? itemFor(fc0.c, col && col.hex) : null; }
        whats.forEach(function (what) {
            var lastRef = null;
            if (hasColour) { var s1 = B.newStep({ what: clone(what), act: 'recolour', colour: { name: col.name, hex: col.hex, at: 0, qual: null, exact: false } }); if (e.exclude && what.k !== 'numbers' && what.k !== 'sponsors') s1.extra = { exclude: e.exclude.slice() }; steps.push(s1); lastRef = s1; }
            if (fin0) {
                var s2 = B.newStep({ what: lastRef ? { k: 'step', ref: lastRef.id } : clone(what) }), fin = clone(fin0); B.pickChoice(s2, fin);
                var x2 = {}; if (e.size) x2.scaleMul = e.size; if (e.exclude && !lastRef && what.k !== 'numbers' && what.k !== 'sponsors') x2.exclude = e.exclude.slice();
                if (Object.keys(x2).length) s2.extra = x2;
                steps.push(s2);
            }
        });
        return steps.length ? steps : null;
    }
    function simpleFind(word) { var all = simpleItems('888888'); for (var i = 0; i < all.length; i++) if (all[i].id === word || String(all[i].label).toLowerCase() === word) return all[i]; return null; }
    function phrase(e, steps) { var B = OB(); try { return B.readAs(steps) + (e.exclude ? ' (not the ' + e.exclude.join(', ') + ')' : '') + (e.size ? (e.size < 1 ? ' - smaller' : ' - bigger') : ''); } catch (x) { return ''; } }
    function showArticleId(e, cheap) {
        var B = OB(), ids = [];
        if (!cheap) { var ar = articles(showQuery(e), 1); if (ar.length) return ar[0].id; }
        if (e.fam && e.fam.id) ids.push(e.fam.id);
        if (e.fam && e.fam.ids) ids.push(e.fam.ids[0]);
        if (e.fam && e.fam.simple) ids.push('look:' + e.fam.simple);
        if (e.goal === 'colour' || e.goal === 'both') ids.push('colour');
        if (e.target && e.target.numbers) ids.push('numbers');
        ids.push('finish');
        for (var i = 0; i < ids.length; i++) { if (B.termById(ids[i])) return ids[i]; var h = B.enc && B.enc.lookup ? B.enc.lookup(ids[i]) : null; if (h) return h; }
        return null;
    }

    // ------------------------------------------------------------------ the sentence reader (shortcut strip) = the planner on the buyer's whole sentence
    var RDM = {}, RDN = 0;
    function rdKey(text, en) { return fixWords(text).trim() + '|' + ((en.layers || []).length) + '|' + ((en.palette || []).length); }
    // the planner read costs up to ~1 s on a big file: draw the questions first, read the sentence a moment later (readPeek schedules it)
    function readPeek(text, en) {
        var k = rdKey(text, en); if (Object.prototype.hasOwnProperty.call(RDM, k)) return RDM[k];
        clearTimeout(S._rt); S._pend = true; S._rt = setTimeout(function () { try { readText(text, env()); } catch (x) {} S._pend = false; draw(); }, 220); return null;
    }
    function readText(text, en) {
        var B = OB(), t = fixWords(text).trim(); if (t.split(/\s+/).length < 2) return null;
        var key = rdKey(text, en); if (Object.prototype.hasOwnProperty.call(RDM, key)) return RDM[key];
        var out = null;
        try {
            var r = B.fromText(t, en), st = (r && r.steps) || [], ex = exceptOf(t);
            if (r && r.blocked) { out = {blocked:r.blocked}; RDM[key] = out; return out; }
            try { fixPicks(st, t, null); } catch (xp) { try { console.error('PBNFIX ' + xp.message); } catch (x2) { } }
            // "flat black": a colour word with a look and no "the/my" is ambiguous (the planner reads it as "the black areas, made matte"): let the questions ask WHERE
            if (st.length === 1 && st[0].what && st[0].what.k === 'colour' && st[0].act !== 'recolour' && !/\b(the|my|all|every)\b/i.test(t)) st = [];
            if (st.length && !st.some(function (s) { return B.stepOpen(s) || s.ask || s.unknown; })) {
                if (ex) st.forEach(function (s) { if (s.what && ['body', 'colour', 'part', 'main'].indexOf(s.what.k) >= 0) { s.extra = Object.assign({}, s.extra || {}, { exclude: ex.list.slice() }); } });
                var pl = B.toPlan(st); if (pl.ok) out = { steps: st, said: B.readAs(st) + (ex ? ' (not the ' + ex.list.join(', ') + ')' : '') };
            }
        } catch (x) { out = null; }
        if (RDN++ > 60) { RDM = {}; RDN = 0; } RDM[key] = out; return out;
    }
    // ------------------------------------------------------------------ the text router: how-to questions and things the offline helper cannot do
    function norm(text) { return ' ' + String(text || '').toLowerCase().replace(/[^a-z0-9#'? ]+/g, ' ').replace(/\s+/g, ' ').trim() + ' '; }
    var IMPERATIVE = /^ (?:(?:can|could|will|would) you |please |pls |i (?:want|need|would like|d like) (?:to |you to )?)?(?:make|paint|change|turn|put|add|give|set|colou?r|recolou?r|apply|use|show me (?:a |an |the )?(?:gold|red|blue|green|black|white|silver|carbon|chrome|matte|satin))\b/;
    function isQuestion(t, raw, inf) {
        if (!inf.colour && (/\b(add|put|use|set|change|give|make) (my |the )?(car )?number (to |is )?#?\d+\b/.test(t) || /\bmy (car )?number is #?\d+/.test(t))) return true;                       // "add my number 32" = how to put a number on
        if (/\b(import|upload|load|bring in|use my|add my) (own |my )?(logos?|image|picture|photo|file|decal|sponsor|psd)\b/.test(t) && !/\b(gold|silver|red|blue|chrome|matte)\b/.test(t)) return true;
        if (IMPERATIVE.test(t)) return false;
        if (/^ (how|what|whats|where|why|when|which|who|can i|can you|could i|could you|is it|is there|are there|does|do i|do you|will|should i|explain|tell me|help|where do)\b/.test(t) || /\?\s*$/.test(raw)) return true;
        if (/\bhow (do|can|to|would|should|come)\b/.test(t)) return true;
        if (/\b(undo|redo|revert|go back|take that back)\b/.test(t)) return true;
        if (/\b(spec map|spec sheet|specular|render|iracing|trading paints|export|save my|template|wireframe|tga|psd|mip)\b/.test(t) && !inf.colour && !inf.fam && !inf.simple) return true;
        return false;
    }
    function partsText(en) { var B = OB(), wc = []; try { wc = B.whatChoices(en, [], { id: 'pbn' }); } catch (x) {} return wc.filter(function (c) { return c.grp === 'Parts'; }).map(function (c) { return c.label.toLowerCase(); }).join(', '); }
    function layerHas(en, re) { return ((en.layers) || []).some(function (l) { return re.test(String(l.name || '')); }); }
    // each: fn(t, raw, en, inf) -> true | string (reason override); strip = the part of the sentence to drop before reading what the helper CAN do
    var CANT = [
        { id: 'newstripes', head: 'Drawing new stripes', why: 'Stripes are shapes drawn on the paint. I can recolour stripes that are already in your file, but I cannot draw new ones offline.', q: 'racing stripes',
          fn: function (t) { if (!window.SPB_PBN_NEWSTRIPES) return false; /* estripe 2026-10-08: planner draws stripes offline now; kill switch SPB_PBN_NEWSTRIPES=1 restores the old card */ return (/\b(add|put|draw|create|paint|give me|i want|want|need)\b/.test(t) && /\b(racing |pin ?|rally |centre |center |twin |dual |two )?stripes?\b/.test(t) && !/\b(the|my|existing|current|those|these) (\w+ )?stripes?\b/.test(t)) || /\bstripes? (down|across|along|over)\b/.test(t) || /\bwith (a |some |two )?(\w+ )?stripes?\b/.test(t); }, strip: /\b(with|and|add|put)\b.*$|\b(add|put)\b.*$/ },
        { id: 'text', head: 'Typing text onto the car', why: 'I cannot type words onto the car offline. Text is a graphic you add to your file or the Graphics panel.', q: 'add text lettering to the paint',
          fn: function (t) { return (/\b(text|lettering|words?|font|spell|write|writing|says?|saying)\b/.test(t) && /\b(on|across|windshield|banner|hood|door|roof|bumper|car|trunk)\b/.test(t)) || /\bput the text\b/.test(t); } },
        { id: 'resize', head: 'Resizing or moving a graphic', why: 'I recolour and re-finish numbers and logos offline, but I cannot make them bigger, smaller, or move them.', q: 'resize or move a graphic layer',
          fn: function (t) { return /\b(bigger|larger|smaller|resize|enlarge|shrink|scale (up|down)|move|rotate|slide|nudge|shift)\b/.test(t) && /\b(numbers?|logos?|sponsors?|decals?|graphics?|text|stripes?|banner)\b/.test(t); } },
        { id: 'outline', head: 'Adding an outline or shadow', why: 'I cannot add an outline, border or shadow offline.', q: 'outline or shadow around numbers', strip: /\b(with|and|plus)\b.*(outline|border|stroke|shadow|bevel).*$|\b(outline|border|stroke|shadow|bevel)\b.*$/,
          fn: function (t) { return /\b(outlines?|outlined|borders?|strokes?|shadows?|bevel)\b/.test(t); } },
        { id: 'livery', head: 'Copying a real livery', why: 'I cannot copy a real car or team livery offline. I can build the colours and finishes you tell me, one step at a time.', q: 'recreate a real livery colour scheme',
          fn: function (t) { return (/\b(looks? like|look as|same as|copy|clone|replica|replicate|inspired by|in the style of|style of|resembles?)\b/.test(t) && /\b(car|livery|truck|race|nascar|daytona|team|brand|scheme)\b|\b(gulf|martini|lamborghini|ferrari|porsche|mclaren|bmw|mustang|corvette|camaro|jgr|hendrick|penske|rainbow)\b/.test(t)) || /^ (gulf|martini|lamborghini|ferrari|mclaren|porsche|jgr|hendrick|penske|rainbow warriors)( livery| car| style| colou?rs| scheme)? $/.test(t); } },
        { id: 'areas', head: 'Painting part of a panel', why: 'I can paint named parts (hood, roof, sides...), but I cannot guess "the lower half" or "a fade" from words. In the step builder you can draw a box on the sheet.', q: 'box select an area',
          fn: function (t) { return /\b(lower|upper|top|bottom|front|back|rear|left|right|middle|center|centre)[ -]?(half|third|quarter|section|strip|portion)\b/.test(t) || /\b(fade|ombre|fades)\b/.test(t); } },
        { id: 'parts', head: 'That part', why: '', q: 'which parts of the car can I paint',
          fn: function (t, raw, en) {
              var m = /\b(wheels?|rims?|tires?|tyres?|mirrors?|windows?|windshield|glass|headlights?|taillights?|tail lights?|head lights?|lights?|grille|exhaust|interior|cockpit|seats?|wipers?|antenna|door handles?|splitter|diffuser)\b/.exec(t);
              if (!m) return false; var w = m[1].replace(/s$/, '').replace(/^(tyre)$/, 'tire'); if (layerHas(en, new RegExp(w.slice(0, 5), 'i'))) return false;
              var ps = partsText(en); return { why: 'I cannot find “' + m[1] + '” on the painted sheet.' + (ps ? ' Parts I can paint: ' + ps + '.' : ''), q: 'can I paint the ' + m[1] }; } },
        { id: 'vague', head: 'I need one concrete change', soft: true, why: 'Nice or better are matters of taste, so I will not change anything until you say what. Pick a place and a colour or look, and I will do it.', q: 'ideas to make the paint scheme stand out',
          fn: function (t, raw, en, inf) { return /\b(pop|stand out|nicer|better|cooler|prettier|sleek|improve|ugly|boring|plastic|cheap|weird|looks? (bad|off|wrong|dull|flat))\b/.test(t) && !inf.target && !inf.colour && !inf.fam && !inf.simple; } }
    ];
    var ROUTE_MEMO = { k: null, v: null };
    function route(text, en, inf) {
        var raw = String(text || '').trim(); if (raw.split(/\s+/).length < 2 && !/^\W*(undo|redo)\W*$/i.test(raw)) return null;
        var key = raw + '|' + (en.layers || []).length; if (ROUTE_MEMO.k === key) return ROUTE_MEMO.v;
        var t = norm(fixWords(raw)), out = null;
        if (isQuestion(t, raw, inf)) out = { kind: 'question', q: raw };
        else for (var i = 0; i < CANT.length && !out; i++) {
            var r = false; try { r = CANT[i].fn(t, raw, en, inf); } catch (x) { r = false; }
            if (r) { out = { kind: 'cant', id: CANT[i].id, head: CANT[i].head, soft: !!CANT[i].soft, why: typeof r === 'object' ? r.why : (typeof r === 'string' ? r : CANT[i].why), q: typeof r === 'object' && r.q ? r.q : CANT[i].q };
                if (CANT[i].strip) { var rest = raw.replace(CANT[i].strip, ' ').replace(/\s+/g, ' ').trim(); if (rest && rest !== raw) out.rest = rest; } }
        }
        ROUTE_MEMO.k = key; ROUTE_MEMO.v = out; return out;
    }
    // ------------------------------------------------------------------ Encyclopedia article picks (its public search) + the online helper
    var ART_MEMO = {};
    function articles(q, n) {
        var E = W.SpbEncyclopedia, hits = []; if (!E || !E.search || !String(q || '').trim()) return [];
        var mk = String(q).toLowerCase();
        if (ART_MEMO[mk]) hits = ART_MEMO[mk];
        else { try { hits = E.search(q, 30) || []; } catch (x) { hits = []; }
            hits = hits.slice(0, 30).map(function (h) { return {id:h.id,type:h.type,title:h.title,summary:String(h.summary || h.sm || '').slice(0,110)}; });
            if (hits.length) { if (Object.keys(ART_MEMO).length >= 40) ART_MEMO = {}; ART_MEMO[mk] = hits; }
        }
        // Cache raw bounded search hits; recheck current index scope on every use.
        if (W.SpbOfflineAnswer && W.SpbOfflineAnswer.filterReferenceArticles) hits = W.SpbOfflineAnswer.filterReferenceArticles(q, hits);
        var out = []; hits.forEach(function (h) { if (out.length < (n || 3) && /^(article|help|tool)$/.test(String(h.type || '')) && out.every(function (o) { return o.id !== h.id; })) out.push({ id: h.id, title: h.title || h.id, sm: String(h.summary || h.sm || '').slice(0, 110) }); });
        return out;
    }
    function showQuery(e) {
        var P = [];
        if (S.text && !e.goal) return S.text;
        if (e.target && e.target.numbers) P.push('change the colour of the numbers'); else if (e.target && e.target.logos) P.push('change sponsor logos'); else if (e.goal === 'colour') P.push('change the colour of a part of the car');
        if (e.fam && e.fam.label && !e.fam.none) P.push(e.fam.label + ' finish'); else if (e.finish && e.finish.label) P.push(e.finish.label);
        else if (e.goal === 'pattern') P.push('add a pattern');
        return P.join(' ') || S.text || 'how to use the paint booth';
    }
    function openArticle(id) { try { W.SpbEncyclopedia && W.SpbEncyclopedia.open(id || undefined); } catch (x) {} }
    // CX2 2026-10-09 (lane CODEX-INTEGRATE; Codex finding: "online helper" links must use the selected-provider experience, never an API-key prompt): OpenRouter is off in the product, so the "online helper"
    // IS Claude / ChatGPT through MCP on the buyer's own plan. The button opens the helper chooser (same as CX1's step-builder button) and leaves the question in the chat. Kill switch: window.SPB_CX2_OFF
    function cx2Online() { return !W.SPB_CX2_OFF && W.SPB_NO_OPENROUTER !== false && !!W.SpbAiConnect; }
    function onlineName() { return cx2Online() ? 'Claude or ChatGPT' : 'the online helper'; }
    function askOnline(text) {
        var B = OB(); text = String(text || S.text || '').trim();
        if (cx2Online()) {
            try { if (text && W.spbProAI && W.spbProAI._push) W.spbProAI._push({ role: 'note', text: 'Pick Claude or ChatGPT above (your own plan, no key), then send your question there: “' + text.slice(0, 160) + '”' }); W.SpbAiConnect.setMode(''); } catch (x) {}
            resetAll(); draw(); return;
        }
        if (!B || !B.configured || !B.configured() || !text) { S.msg = 'The online helper is not turned on. Open the gear in this panel to set it up, or use the Encyclopedia.'; draw(); return; }
        try { if (W.spbProAI && W.spbProAI.ask) W.spbProAI.ask(text, { forceAI: true }).then(function (r) { return W.spbProAI.finish(r, text, 'ask'); }); } catch (x) {}
        resetAll(); draw();
    }

    // ------------------------------------------------------------------ UI
    var dockEl = null;
    function panel() { return D.getElementById('spbProAI'); }
    function builderBusy() {
        var B = OB(); if (!B) return true; var st = B.state(); if (!st) return true;
        return !!((st.steps && st.steps.length) || st.answer || st.term || st.browse || st.box);
    }
    function ensureDock() {
        var p = panel(); if (!p) return null;
        var d = p.querySelector('.spb-pbn'); if (d) return d;
        var anchor = p.querySelector('.spb-ob') || p.querySelector('.spb-pai-bar'); if (!anchor) return null;
        d = D.createElement('div'); d.className = 'spb-pbn'; anchor.parentNode.insertBefore(d, anchor);
        d.addEventListener('click', onClick); d.addEventListener('input', onInput);
        d.addEventListener('keydown', function (ev) { ev.stopPropagation(); });
        d.addEventListener('keyup', function (ev) { ev.stopPropagation(); });
        return d;
    }
    function optHtml(o, k) {
        var h = '<button type="button" class="spb-pbn-opt' + (o.thumb ? ' th' : '') + '" data-pbn="opt" data-k="' + k + '" title="' + esc(o.label + (o.sub ? ' - ' + o.sub : '')) + '">';
        if (o.thumb) h += '<img alt="" data-src="' + esc(o.thumb) + '">';
        else if (o.hex) h += '<i class="spb-ob-sw" style="background:' + esc(o.hex) + '"></i>';
        return h + '<span>' + esc(o.label) + (o.sub ? ' <em>' + esc(o.sub) + '</em>' : '') + '</span></button>';
    }
    // thumbnails load through a queue (max 6 at once, in order) and show a shimmer until they arrive (36 live swatches at once left blank tiles)
    var QUEUE = [], ACTIVE = 0, GEN = 0;
    function pump() {
        while (ACTIVE < 6 && QUEUE.length) {
            var im = QUEUE.shift(); if (!im.isConnected || im.__g !== GEN) continue; ACTIVE++;
            (function (im) { var done = function (ok) { ACTIVE--; im.classList.add(ok ? 'ok' : 'bad'); pump(); }; im.onload = function () { done(true); }; im.onerror = function () { done(false); }; im.src = im.getAttribute('data-src'); })(im);
        }
    }
    function loadThumbs(d) { GEN++; ACTIVE = 0; QUEUE = []; [].forEach.call(d.querySelectorAll('img[data-src]'), function (im) { im.__g = GEN; QUEUE.push(im); }); pump(); }
    var CUR = null;   // the question currently drawn (options addressed by index)
    function draw() {
        var d = ensureDock(); if (!d) return;
        var composerPanel = panel(); if (composerPanel && composerPanel.getAttribute('data-spb-compose-hold') === '1') { d.hidden = true; return; }
        var B = OB(), off = W.SPB_PBN_OFF || !B || !B.offlineMode() || builderBusy();
        // CX3 2026-10-09 (Codex 'Shared input binding / chat vs Paint-by-Numbers one scope', owner: never offer a "Do it" the chat itself just declined): while the chat is asking WHICH
        // layer (repeated names such as ARCA's four "Base Paint"), showing a layer/inventory answer, or answering advice-only, the funnel stays out of the way instead of offering its
        // own complete-looking operation. Each check is inert until its producer exists; kill switch window.SPB_CX3_OFF.
        if (!off && !W.SPB_CX3_OFF) {
            try {
                var handledMaterial = B && B.state && B.state()._handledMaterial;
                if (W.SpbNamedZoneMaterial && (W.SpbNamedZoneMaterial.parse(S.text) || (handledMaterial && handledMaterial.text === S.text && W.SpbConversationScope && W.SpbConversationScope.current(handledMaterial.stamp)))) { CUR = null; off = true; }
                var handledPattern = B && B.state && B.state()._handledPattern;
                if (W.SpbNamedPatternRefinement && (W.SpbNamedPatternRefinement.parse(S.text) || (handledPattern && handledPattern.text === S.text && W.SpbConversationScope && W.SpbConversationScope.current(handledPattern.stamp)))) { CUR = null; off = true; }
                var readState3 = B && B.state ? B.state() : null, readAns3 = readState3 && readState3.answer && readState3.answer.answer;
                // W20 has a reviewed executable builder plan; do not contradict
                // it with the older generic "cannot resize" funnel card.
                if (readState3 && String(readState3.text || '').trim() === String(S.text || '').trim() && !(readState3.liveText || '').trim() && !readState3.msg && (readState3.steps || []).some(function (st) { return st.extra && st.extra.w20x; })) { CUR = null; off = true; }
                if (readAns3 && ((readAns3.id === 'assistant.template_layers' || readAns3.id === 'assistant.layer_pixels') || readAns3.chat_summary || readAns3.id === 'assistant.design_advice' || readAns3.id === 'assistant.live_editor_capabilities') && !String(readState3.liveText || '').trim() && !(readState3.steps || []).length) { CUR = null; off = true; }
                if (W.SpbDesignIntent && W.SpbDesignIntent.classify(S.text).mode === 'advice') { CUR = null; off = true; }
                var layerAsk3 = W.SpbLayerTargets && B && B.envNow ? W.SpbLayerTargets.scope(S.text, (B.envNow() || {}).layers) : null;
                if (layerAsk3 && layerAsk3.ask && layerAsk3.ask.layer_target_question) { CUR = null; off = true; }
            } catch (e3) { }
        }
        d.hidden = !!off; if (off) { d.innerHTML = ''; return; }
        var en = env(), e = eff(), q = null, endCard = false;
        if (!S.open) { d.innerHTML = '<div class="spb-pbn-mini"><button type="button" class="spb-pai-act" data-pbn="reopen">🎨 Guide me step by step</button></div>'; return; }
        var fresh = S.picks.every(function (p) { return p.slot === 'goal'; }), R = (fresh && S.text && S.routeOff !== S.text) ? route(S.text, en, e.inf) : null;
        if (R) endCard = R.kind; else if (e.question) endCard = 'question'; else { q = nextQ(e, en); if (!q) endCard = 'done'; }
        var h = '<div class="spb-pbn-card"><div class="spb-pbn-hd"><b>🎨 Paint by numbers</b><i>built-in, no AI</i><button type="button" class="spb-pbn-x" data-pbn="close" title="Hide the guide (the step builder and typing still work)">×</button></div>';
        // typed keywords: always available, narrow every step
        h += '<div class="spb-pbn-kw"><input type="text" class="spb-pbn-in" data-pbn-in="1" value="' + esc(S.text) + '" placeholder="Type words to narrow it down: “numbers gold”, “matte hood”..." autocomplete="off" spellcheck="false">' + (S.text ? '<button type="button" class="spb-pbn-clr" data-pbn="cleartext" title="Clear the words">✕</button>' : '') + '</div>';
        if (e.inf.words.length) h += '<div class="spb-pbn-seen"><span>I recognised:</span> ' + e.inf.words.map(function (w) { return '<mark class="k-' + esc(w.kind) + '">' + esc(String(w.label).toUpperCase()) + '</mark>'; }).join(' ') + '</div>';
        // breadcrumbs of the clicked answers (click one to go back to it)
        if (S.picks.length) h += '<div class="spb-pbn-crumbs">' + S.picks.map(function (p, i) { return '<button type="button" class="spb-pbn-crumb" data-pbn="crumb" data-i="' + i + '" title="Go back to here">' + esc(p.label) + '</button>'; }).join('<span>›</span>') + '</div>';
        if (S.msg) h += '<div class="spb-pbn-msg">' + esc(S.msg) + '</div>';
        CUR = null;
        var RDR = (!R && fresh && S.text && S.text.trim().split(/\s+/).length > 1) ? readPeek(S.text, en) : null;
        if (RDR && RDR.blocked) { CUR = null; d.innerHTML = h + '<div class="spb-pbn-msg">' + esc(RDR.blocked) + '</div></div>'; return; }
        if (RDR) h += '<div class="spb-pbn-read"><span>I read your words as</span> <b>' + esc(RDR.said) + '</b> <button type="button" class="spb-pai-act hot" data-pbn="rdo" title="Do it on the car now (one Undo takes it back)">▶ Do it</button><button type="button" class="spb-pai-act" data-pbn="rlook" title="Open these steps in the step builder first">🧱 Look it over</button></div>';
        var escRow = '<div class="spb-pbn-esc"><span>Not here?</span><button type="button" class="spb-pai-act" data-pbn="escenc">📖 Search the Encyclopedia</button><button type="button" class="spb-pai-act" data-pbn="online">✨ Ask ' + onlineName() + '</button></div>';
        if (q) {
            var opts = q.opts, lo = e.inf.search || e.inf.leftover, note = '';
            if (q.filterable && lo.length) {
                var f = opts.filter(function (o) { var hay = (o.label + ' ' + (o.sub || '') + ' ' + (o.grp || '')).toLowerCase(); return lo.some(function (w) { return hay.indexOf(w) >= 0; }); });
                if (f.length) { note = 'Showing choices that match “' + lo.join(' ') + '”.'; opts = f; }
                else note = 'No choice matches “' + lo.join(' ') + '”: showing all.';
                if (q.search && lo.length) {   // catalogue search: real finishes whose names/aliases contain the words
                    var hx = e.colour ? e.colour.hex : '#888888', hits = B.searchChoices(lo.join(' '), ['finish', 'pattern', 'spec'], 18).map(function (c) { var it = B.pickChoice ? itemFor({ label: c.label, finish_id: c.kind === 'finish' ? c.id : undefined, pattern_id: c.kind === 'pattern' ? c.id : undefined, spec_id: c.kind === 'spec' ? c.id : undefined }, hx) : null; return it ? { label: c.label, thumb: it.thumb, grp: 'Catalogue matches', pick: { slot: 'finish', val: it, label: c.label } } : null; }).filter(Boolean);
                    if (hits.length) { opts = hits.concat(f.length ? [] : []).concat(opts.filter(function (o) { return o.grp !== 'Catalogue matches'; })); note = 'Catalogue matches for “' + lo.join(' ') + '” first.'; }
                }
            }
            if (q.none) opts = opts.concat([q.none]);
            CUR = { q: q, opts: opts };
            h += '<div class="spb-pbn-q">' + esc(q.q) + '</div><div class="spb-pbn-hint">' + esc(note || q.hint || '') + '</div><div class="spb-pbn-grid">';
            var grp = null; opts.forEach(function (o, k) { if (o.grp !== grp) { grp = o.grp; if (grp) h += '<span class="spb-pbn-grp">' + esc(grp) + '</span>'; } h += optHtml(o, k); });
            h += '</div>' + escRow;
        } else if (endCard === 'cant') {
            var pa = R.rest ? readPeek(R.rest, en) : null, ar = articles(R.q, 1);
            h += '<div class="spb-pbn-cant"><b>' + (R.soft ? esc(R.head) : (R.id === 'parts' ? 'I can’t find that on your paint' : 'I can’t do that one offline: ' + esc(R.head.toLowerCase()))) + '.</b> ' + esc(R.why) + '</div>';
            if (pa) h += '<div class="spb-pbn-part"><span>What I can do offline</span> <b>' + esc(pa.said) + '</b></div>';
            h += '<div class="spb-pbn-row">' + (pa ? '<button type="button" class="spb-pai-act hot" data-pbn="pdo">▶ Do that part</button><button type="button" class="spb-pai-act" data-pbn="plook">🧱 Look it over</button>' : '') +
                (ar.length ? '<button type="button" class="spb-pai-act" data-pbn="art" data-id="' + esc(ar[0].id) + '" title="' + esc(ar[0].sm) + '">📖 Show me how: ' + esc(ar[0].title) + '</button>' : '<button type="button" class="spb-pai-act" data-pbn="enc">📖 Open the Encyclopedia</button>') +
                '<button type="button" class="spb-pai-act" data-pbn="online">✨ Ask ' + onlineName() + '</button><button type="button" class="spb-pai-act" data-pbn="steps">Ask me questions instead</button></div>';
        } else if (endCard === 'question' && (R || S.text)) {
            var as = articles(S.text, 3);
            h += '<div class="spb-pbn-q">That sounds like a how-to question</div><div class="spb-pbn-hint">' + (as.length ? 'These Encyclopedia pages answer it:' : 'I did not find a page for those words. Try the whole Encyclopedia, or ' + onlineName() + '.') + '</div>';
            h += '<div class="spb-pbn-qa">' + as.map(function (a, i) { return '<button type="button" class="spb-pai-act' + (i ? '' : ' hot') + '" data-pbn="art" data-id="' + esc(a.id) + '" title="' + esc(a.sm) + '">📖 ' + esc(a.title) + '</button>'; }).join('') + '</div>';
            h += '<div class="spb-pbn-row"><button type="button" class="spb-pai-act" data-pbn="enc">Open the Encyclopedia</button><button type="button" class="spb-pai-act" data-pbn="online">✨ Ask ' + onlineName() + '</button><button type="button" class="spb-pai-act" data-pbn="steps">Ask me questions instead</button></div>';
        } else if (endCard === 'question') {
            CUR = null;
            h += '<div class="spb-pbn-q">What would you like to know?</div><div class="spb-pbn-hint">Type your question above and I will find the page, or open the whole Encyclopedia.</div><div class="spb-pbn-row"><button type="button" class="spb-pai-act hot" data-pbn="enc">📖 Open the Encyclopedia</button>' + (e.inf.words.length ? '<button type="button" class="spb-pai-act" data-pbn="encterm">📖 Show me: ' + esc(e.inf.words[0].label) + '</button>' : '') + '</div>';
        } else {
            var steps = buildSteps(e, en), aid = showArticleId(e, true);
            h += '<div class="spb-pbn-q">Here is the plan</div>';
            h += '<div class="spb-pbn-plan">' + (steps ? esc(phrase(e, steps)) : 'I need one more answer.') + '</div><div class="spb-pbn-row">' +
                '<button type="button" class="spb-pai-act hot" data-pbn="do"' + (steps ? '' : ' disabled') + ' title="Do it on the car now (one Undo takes it back)">▶ Do it</button>' +
                '<button type="button" class="spb-pai-act" data-pbn="review"' + (steps ? '' : ' disabled') + ' title="Open these steps in the step builder to adjust them first">🧱 Look it over first</button>' +
                '<button type="button" class="spb-pai-act" data-pbn="show"' + (aid ? '' : ' disabled') + ' title="Open the Encyclopedia article that explains this">📖 Show me how</button></div>';
            var scal = steps && (e.finish || (e.fam && (e.fam.id || e.fam.ids || e.fam.qwords))) && !(e.fam && e.fam.simple);
            if (scal) {
                h += '<div class="spb-pbn-tw"><span>Size</span>' + [['Smaller', 0.6], ['Normal', 0], ['Bigger', 1.6]].map(function (z) { var on = (e.size || 0) === z[1]; return '<button type="button" class="spb-pbn-chip' + (on ? ' on' : '') + '" data-pbn="size" data-v="' + z[1] + '">' + z[0] + '</button>'; }).join('') + '</div>';
                if (!e.colour) h += '<div class="spb-pbn-tw"><span>Colour</span><button type="button" class="spb-pbn-chip' + (e.pcolour ? '' : ' on') + '" data-pbn="pcol" data-n="">As it comes</button>' + ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'white', 'black'].map(function (n) { return '<button type="button" class="spb-pbn-chip sw' + (e.pcolour && e.pcolour.name === n ? ' on' : '') + '" data-pbn="pcol" data-n="' + n + '" title="' + n + '" style="--c:' + colourHexOf(n) + '"></button>'; }).join('') + '</div>';
            }
        }
        h += '<div class="spb-pbn-foot">' + (S.picks.length ? '<button type="button" class="spb-pai-act" data-pbn="back">← Back</button>' : '') + (S.picks.length || S.text ? '<button type="button" class="spb-pai-act" data-pbn="reset">Start over</button>' : '') + '</div></div>';
        var keep = d.querySelector('.spb-pbn-in') && D.activeElement === d.querySelector('.spb-pbn-in'), pos = keep ? d.querySelector('.spb-pbn-in').selectionStart : 0, top = d.scrollTop;
        d.innerHTML = h;
        d.scrollTop = (S._lastQ === (q ? q.id : endCard)) ? top : 0; S._lastQ = q ? q.id : endCard;
        loadThumbs(d);
        if (keep) { var inp = d.querySelector('.spb-pbn-in'); inp.focus(); try { inp.setSelectionRange(pos, pos); } catch (x) {} }
    }
    function onInput(ev) {
        var t = ev.target; if (!t || !t.getAttribute || !t.getAttribute('data-pbn-in')) return;
        S.text = t.value; S.msg = ''; S.routeOff = null; clearTimeout(S._dt); S._dt = setTimeout(draw, 140);      // one redraw per pause in typing (the Encyclopedia search + planner reads are not free)
    }
    function resetAll() { S.text = ''; S.picks = []; S.msg = ''; S.listAll = false; S.routeOff = null; }
    function onClick(ev) {
        var b = ev.target && ev.target.closest ? ev.target.closest('[data-pbn]') : null; if (!b) return;
        var a = b.getAttribute('data-pbn'), B = OB(); ev.preventDefault();
        if (a === 'opt') { var o = CUR && CUR.opts[+b.getAttribute('data-k')]; if (!o) return; var p = o.pick; if (p.slot === 'cmode' && p.val === 'solid') S.picks = S.picks.filter(function (x) { return x.slot !== 'finish'; }); S.picks.push({ slot: p.slot, val: clone(p.val), label: p.label }); S.msg = ''; draw(); }
        else if (a === 'back') { S.picks.pop(); S.msg = ''; draw(); }
        else if (a === 'crumb') { S.picks = S.picks.slice(0, +b.getAttribute('data-i')); S.msg = ''; draw(); }
        else if (a === 'reset') { resetAll(); draw(); }
        else if (a === 'cleartext') { S.text = ''; draw(); }
        else if (a === 'close') { S.open = false; draw(); }
        else if (a === 'reopen') { S.open = true; draw(); }
        else if (a === 'enc') { try { W.SpbEncyclopedia && W.SpbEncyclopedia.open(); } catch (x) {} }
        else if (a === 'encterm') { var w = eff().inf.words[0], ar2 = articles(w.label, 1); try { var id = (ar2.length && ar2[0].id) || (B.enc && B.enc.lookup(w.label)) || null; W.SpbEncyclopedia && W.SpbEncyclopedia.open(id || undefined); } catch (x) {} }
        else if (a === 'show') { var e0 = eff(), id0 = showArticleId(e0); openArticle(id0); }
        else if (a === 'art') openArticle(b.getAttribute('data-id'));
        else if (a === 'escenc') { var e1 = eff(), qq = S.text || (CUR && CUR.q && CUR.q.q) || showQuery(e1), a1 = articles(qq, 1); openArticle(a1.length ? a1[0].id : undefined); }
        else if (a === 'online') askOnline(S.text);
        else if (a === 'steps') { S.routeOff = S.text; draw(); }
        else if (a === 'size') { var v = parseFloat(b.getAttribute('data-v')) || 0; S.picks = S.picks.filter(function (x) { return x.slot !== 'size'; }); if (v) S.picks.push({ slot: 'size', val: v, label: v < 1 ? 'Smaller' : 'Bigger' }); draw(); }
        else if (a === 'pcol') { var nm = b.getAttribute('data-n'); S.picks = S.picks.filter(function (x) { return x.slot !== 'pcolour'; }); if (nm) S.picks.push({ slot: 'pcolour', val: { name: nm, hex: colourHexOf(nm) }, label: cap(nm) + ' pattern' }); draw(); }
        else if (a === 'rdo' || a === 'rlook' || a === 'pdo' || a === 'plook') {
            var en2 = env(), rr = a.charAt(0) === 'r' ? readText(S.text, en2) : readText((route(S.text, en2, eff().inf) || {}).rest || '', en2); if (!rr) return;
            B.showSteps(rr.steps, S.text);
            if (a === 'rdo' || a === 'pdo') { var pl2 = B.toPlan(rr.steps), open2 = rr.steps.filter(function (s) { return B.stepOpen(s) || s.ask; }); if (pl2.ok && !open2.length) { try { B.run(); } catch (x) { } } }
            resetAll(); draw();
        }
        else if (a === 'review' || a === 'do') {
            var e = eff(), en = env(), steps = buildSteps(e, en); if (!steps) { S.msg = 'I need one more answer first.'; draw(); return; }
            var said = phrase(e, steps);
            B.showSteps(steps, S.text || said);
            if (a === 'do') {
                var pl = B.toPlan(steps), open = steps.filter(function (s) { return B.stepOpen(s) || s.ask; });
                if (pl.ok && !open.length) { try { B.run(); } catch (x) { } } else { /* the builder shows what is still missing */ }
            }
            resetAll(); draw();
        }
    }
    // mirror what is typed in the panel's own box so the funnel narrows from either place
    function mirrorPanelInput() {
        var p = panel(); if (!p || p.__pbnMirror) return; var ta = p.querySelector('.spb-pai-input'); if (!ta) return; p.__pbnMirror = 1;
        ta.addEventListener('input', function () { if (W.SPB_PBN_OFF) return; var v = String(ta.value || ''); if (v.trim() !== S.text.trim()) { S.text = v.trim(); draw(); } });
    }
    function sig() {
        var B = OB(), st = B && B.state ? B.state() : null, en = B ? env() : {};
        return [W.SPB_PBN_OFF ? 1 : 0, B && B.offlineMode() ? 1 : 0, st ? (st.steps || []).length + '|' + (st.answer ? 1 : 0) + '|' + (st.term || '') + '|' + (st.browse ? 1 : 0) + '|' + (st.box ? 1 : 0) : '', ((en.layers) || []).length, ((en.palette) || []).length, panel() ? (panel().querySelector('.spb-pbn') ? 1 : 0) : -1].join(',');
    }
    function tick() {
        try {
            if (W.SPB_PBN_OFF) { var p0 = panel(), d0 = p0 && p0.querySelector('.spb-pbn'); if (d0 && !d0.hidden) { d0.hidden = true; d0.innerHTML = ''; } return; }
            if (!OB() || !panel()) return;
            mirrorPanelInput();
            var s; try { W.__spbEnvLazy = true; s = sig(); } finally { W.__spbEnvLazy = false; } /* [SPB-PERF2 2026-10-10] sig() only needs layers.length / palette.length: editEnv() may answer from its previous environment and rebuild in the background (kill switch window.SPB_PERF2_OFF) */ if (s !== S.sig) { S.sig = s; draw(); }
        } catch (x) { }
    }
    setInterval(tick, 500);
    function sourceChanged() {
        clearTimeout(S._dt); clearTimeout(S._rt);
        var open = S.open;
        S = { text: '', picks: [], open: open, listAll: false, sig: '', msg: '', routeOff: null };
        RDM = {}; RDN = 0; CUR = null;
        draw();
    }
    W.SpbPbn = { _sourceChanged: sourceChanged, _fam: famChoices, _rr: rerank, state: function () { return S; }, eff: eff, infer: infer, nextQ: function () { var en = env(), e = eff(), R = (S.picks.every(function (p) { return p.slot === 'goal'; }) && S.text && S.routeOff !== S.text) ? route(S.text, en, e.inf) : null; return R ? { id: 'ROUTE_' + R.kind } : (e.question ? { id: 'ROUTE_question' } : nextQ(e, en)); }, route: function (t) { var en = env(); return route(t, en, infer(t)); }, readText: function (t) { return readText(t, env()); }, peek: function (t) { return readPeek(t, env()); }, articles: articles, buildSteps: function () { return buildSteps(eff(), env()); }, draw: draw, reset: function () { resetAll(); draw(); }, setText: function (t) { S.text = String(t || ''); draw(); } };
})();
